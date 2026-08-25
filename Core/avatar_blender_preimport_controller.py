"""Fail-closed pre-import controller for bounded Blender workers.

The controller implements the parts of a trustworthy launch boundary that can
be proven without starting Blender:

* strict request, path, argument, and environment grammar;
* exact SHA-256 bindings for Blender, its bundled interpreter, the worker,
  configuration, and per-run authorization;
* read handles held without write/delete sharing on Windows;
* an atomic, file-flushed one-run claim and terminal outcome; and
* a process-image query helper for a future reviewed native launch provider.

No native launch provider is reviewed in this release.  ``submit`` therefore
always records a terminal blocked outcome after a valid preflight and never
starts Blender.  This module grants no body, person, anatomy, runtime,
activation, save, render, or publication authority.
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime, timezone
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_SCHEMA = "kira.avatar_builder.blender_preimport_controller.v1"
CLAIM_SCHEMA = "kira.avatar_builder.blender_one_run_claim.v1"
OUTCOME_SCHEMA = "kira.avatar_builder.blender_one_run_outcome.v1"
NATIVE_PROVIDER_INTERFACE = "kira.blender_native_launch_provider.v1"
MACHINE_EVIDENCE_RELATIVE_PATH = (
    "Avatar/avatar_builder/tooling/blender_5_1_preimport_controller_boundary_v1.json"
)
EXECUTION_TRUST_BOUNDARY_CLOSED = False
REVIEWED_NATIVE_PROVIDER_IDS: frozenset[str] = frozenset()

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{7,63}$")
ROLE_RE = re.compile(r"^[a-z][a-z0-9_]{2,47}$")
MAX_CLAIM_BYTES = 16 * 1024
MAX_OUTCOME_BYTES = 32 * 1024
MAX_JSON_DEPTH = 12
MAX_TEXT_LENGTH = 512
MAX_ARTIFACT_BYTES = {
    "blender_executable": 512 * 1024 * 1024,
    "bundled_interpreter": 64 * 1024 * 1024,
    "worker_script": 2 * 1024 * 1024,
    "config": 2 * 1024 * 1024,
    "authorization": 512 * 1024,
}
REQUIRED_BLENDER_FLAGS = ("--background", "--factory-startup", "--disable-autoexec")
BUILD_WORKER_NAME = "blender_build_makehuman_adult_female_rigged_carrier_inactive.py"
AUDIT_WORKER_NAME = "blender_audit_makehuman_adult_female_rigged_carrier.py"
CARRIER_CONFIG_NAME = "makehuman_adult_female_rigged_carrier_v1.json"
AUTHORIZATION_NAME = "ONE_RUN_AUTHORIZATION.json"
AUTHORIZATION_SCHEMA = "kira.avatar.makehuman_rigged_carrier.one_run_authorization.v1"
AUTHORIZATION_STATUS = "AUTHORIZED_ONE_INACTIVE_CARRIER_BUILD_AND_AUDIT"
AUTHORIZATION_KEYS = frozenset(
    {
        "schema",
        "status",
        "one_run_id",
        "issued_at_utc",
        "config_sha256",
        "source_sha256",
        "candidate_blend_path",
        "build_report_path",
        "audit_report_path",
        "blender_executable_sha256",
        "preflight_receipt_sha256",
        "controller_sha256",
        "builder_sha256",
        "auditor_sha256",
        "intersection_auditor_sha256",
        "build_allowed",
        "audit_allowed",
        "background_required",
        "factory_startup_required",
        "autoexec_disabled_required",
        "overwrite_allowed",
        "source_mutation_allowed",
        "hair_allowed",
        "clothing_allowed",
        "internal_anatomy_allowed",
        "identity_styling_allowed",
        "runtime_activation_allowed",
        "public_export_allowed",
    }
)
RFC3339_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)


class BlenderControllerError(ValueError):
    """Base class for stable fail-closed controller errors."""

    code = "CONTROLLER_REJECTED"


class InvalidRequest(BlenderControllerError):
    code = "INVALID_REQUEST"


class ArtifactBindingError(BlenderControllerError):
    code = "ARTIFACT_BINDING_REJECTED"


class ClaimAlreadyExists(BlenderControllerError):
    code = "ONE_RUN_ALREADY_CLAIMED"


class OutcomeAlreadyExists(BlenderControllerError):
    code = "TERMINAL_OUTCOME_ALREADY_EXISTS"


class NativeBoundaryRequired(BlenderControllerError):
    code = "REVIEWED_NATIVE_BOUNDARY_REQUIRED"


def _strict_json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidRequest(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _validate_json_value(value: Any, *, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise InvalidRequest("JSON nesting exceeds the limit")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, float):
        if not (value == value and abs(value) != float("inf")):
            raise InvalidRequest("JSON contains a non-finite number")
        return
    if isinstance(value, str):
        if len(value) > MAX_TEXT_LENGTH:
            raise InvalidRequest("JSON text exceeds the limit")
        return
    if isinstance(value, list):
        if len(value) > 128:
            raise InvalidRequest("JSON list exceeds the limit")
        for item in value:
            _validate_json_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > 128:
            raise InvalidRequest("JSON object exceeds the limit")
        for key, item in value.items():
            if not isinstance(key, str) or not key or len(key) > 96:
                raise InvalidRequest("JSON keys must be bounded nonempty text")
            _validate_json_value(item, depth=depth + 1)
        return
    raise InvalidRequest("JSON contains an unsupported type")


def read_strict_json(path: Path, *, max_bytes: int) -> dict[str, Any]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise InvalidRequest("JSON artifact cannot be inspected") from exc
    if size <= 0 or size > max_bytes:
        raise InvalidRequest("JSON artifact size is outside the limit")
    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(
            raw,
            object_pairs_hook=_strict_json_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                InvalidRequest(f"non-finite JSON number: {token}")
            ),
        )
    except InvalidRequest:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InvalidRequest("JSON artifact is invalid") from exc
    if not isinstance(value, dict):
        raise InvalidRequest("JSON artifact must be an object")
    _validate_json_value(value)
    return value


def canonical_json_bytes(value: Any) -> bytes:
    _validate_json_value(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_sha256(value: str, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise InvalidRequest(f"{label} must be lowercase SHA-256")
    return value


def _is_unc(path: Path) -> bool:
    text = str(path.absolute())
    return text.startswith("\\\\") or text.startswith("//")


def _is_reparse(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise InvalidRequest("path cannot be inspected") from exc
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


def _validate_local_absolute_path(path: Path, label: str, *, directory: bool) -> Path:
    if not isinstance(path, Path) or not path.is_absolute() or _is_unc(path):
        raise InvalidRequest(f"{label} must be an absolute local path")
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise InvalidRequest(f"{label} is absent") from exc
    if _is_unc(resolved):
        raise InvalidRequest(f"{label} must not be UNC")
    if _is_reparse(path):
        raise InvalidRequest(f"{label} must not be a reparse point")
    if directory and not resolved.is_dir():
        raise InvalidRequest(f"{label} must be a directory")
    if not directory and not resolved.is_file():
        raise InvalidRequest(f"{label} must be a regular file")
    return resolved


@dataclass(frozen=True)
class ArtifactBinding:
    role: str
    path: Path
    sha256: str

    def __post_init__(self) -> None:
        if ROLE_RE.fullmatch(self.role) is None or self.role not in MAX_ARTIFACT_BYTES:
            raise InvalidRequest("artifact role is not allowed")
        _validate_sha256(self.sha256, f"{self.role}.sha256")
        if not isinstance(self.path, Path):
            raise InvalidRequest(f"{self.role}.path must be a Path")


@dataclass(frozen=True)
class ControllerPolicy:
    policy_id: str
    operation: str
    artifacts: tuple[ArtifactBinding, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, str) or ROLE_RE.fullmatch(self.policy_id) is None:
            raise InvalidRequest("policy_id is invalid")
        if self.operation not in {"build", "audit"}:
            raise InvalidRequest("operation must be build or audit")
        roles = [binding.role for binding in self.artifacts]
        required = {
            "blender_executable",
            "bundled_interpreter",
            "worker_script",
            "config",
        }
        if set(roles) != required or len(roles) != len(required):
            raise InvalidRequest("policy must bind each required artifact exactly once")
        by_role = {binding.role: binding for binding in self.artifacts}
        blender = by_role["blender_executable"].path
        interpreter = by_role["bundled_interpreter"].path
        worker = by_role["worker_script"].path
        config = by_role["config"].path
        if blender.name.lower() not in {"blender", "blender.exe"}:
            raise InvalidRequest("Blender executable name differs")
        if interpreter.name.lower() not in {"python", "python.exe"}:
            raise InvalidRequest("bundled interpreter name differs")
        try:
            interpreter_relative = interpreter.relative_to(blender.parent)
        except ValueError as exc:
            raise InvalidRequest("bundled interpreter is outside Blender installation") from exc
        interpreter_parts = tuple(part.lower() for part in interpreter_relative.parts)
        if (
            len(interpreter_parts) != 4
            or re.fullmatch(r"\d+\.\d+(?:\.\d+)?", interpreter_parts[0]) is None
            or interpreter_parts[1:3] != ("python", "bin")
        ):
            raise InvalidRequest("bundled interpreter layout differs")
        expected_worker = BUILD_WORKER_NAME if self.operation == "build" else AUDIT_WORKER_NAME
        if worker.name != expected_worker:
            raise InvalidRequest("worker name differs from operation")
        if config.name != CARRIER_CONFIG_NAME:
            raise InvalidRequest("carrier config name differs")

    @property
    def by_role(self) -> Mapping[str, ArtifactBinding]:
        return MappingProxyType({binding.role: binding for binding in self.artifacts})


@dataclass(frozen=True)
class LaunchRequest:
    run_id: str
    operation: str
    authorization: ArtifactBinding
    claim_root: Path
    temp_root: Path
    system_root: Path

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, str) or RUN_ID_RE.fullmatch(self.run_id) is None:
            raise InvalidRequest("run_id grammar is invalid")
        if self.operation not in {"build", "audit"}:
            raise InvalidRequest("operation must be build or audit")
        if self.authorization.role != "authorization":
            raise InvalidRequest("authorization binding role differs")
        if self.authorization.path.name != AUTHORIZATION_NAME:
            raise InvalidRequest("authorization filename differs")
        for field_name in ("claim_root", "temp_root", "system_root"):
            if not isinstance(getattr(self, field_name), Path):
                raise InvalidRequest(f"{field_name} must be a Path")


@dataclass(frozen=True)
class HeldArtifact:
    role: str
    path: Path
    fd: int
    size: int
    sha256: str
    device: int
    inode: int
    link_count: int
    _closed: bool = field(default=False, compare=False, repr=False)

    def close(self) -> None:
        if self._closed:
            return
        try:
            os.close(self.fd)
        except OSError:
            pass
        finally:
            object.__setattr__(self, "_closed", True)


def _open_held_read(path: Path) -> int:
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    if os.name != "nt" and hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if os.name != "nt":
        return os.open(path, flags)

    # Python's os.open does not expose Windows share-mode selection.  Open the
    # file with read sharing only so new write/delete opens are rejected while
    # the descriptor remains alive.
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    handle = create_file(
        str(path),
        0x80000000,  # GENERIC_READ
        0x00000001,  # FILE_SHARE_READ; intentionally no WRITE or DELETE
        None,
        3,  # OPEN_EXISTING
        0x00200000 | 0x08000000,  # OPEN_REPARSE_POINT | SEQUENTIAL_SCAN
        None,
    )
    invalid = wintypes.HANDLE(-1).value
    if handle == invalid:
        error = ctypes.get_last_error()
        raise ArtifactBindingError(f"held open failed with Windows error {error}")
    import msvcrt

    try:
        return msvcrt.open_osfhandle(handle, flags)
    except Exception:
        kernel32.CloseHandle(handle)
        raise


def acquire_held_artifact(binding: ArtifactBinding) -> HeldArtifact:
    path = _validate_local_absolute_path(binding.path, binding.role, directory=False)
    fd = _open_held_read(path)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ArtifactBindingError(f"{binding.role} is not regular")
        max_bytes = MAX_ARTIFACT_BYTES[binding.role]
        if before.st_size <= 0 or before.st_size > max_bytes:
            raise ArtifactBindingError(f"{binding.role} size is outside the limit")
        if int(getattr(before, "st_nlink", 1)) != 1:
            raise ArtifactBindingError(f"{binding.role} must not be multiply linked")
        digest = hashlib.sha256()
        os.lseek(fd, 0, os.SEEK_SET)
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            digest.update(block)
        os.lseek(fd, 0, os.SEEK_SET)
        after = os.fstat(fd)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            int(getattr(before, "st_nlink", 1)),
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            int(getattr(after, "st_nlink", 1)),
        )
        if identity_before != identity_after:
            raise ArtifactBindingError(f"{binding.role} changed during hashing")
        observed = digest.hexdigest()
        if observed != binding.sha256:
            raise ArtifactBindingError(f"{binding.role} hash differs")
        return HeldArtifact(
            role=binding.role,
            path=path,
            fd=fd,
            size=before.st_size,
            sha256=observed,
            device=before.st_dev,
            inode=before.st_ino,
            link_count=int(getattr(before, "st_nlink", 1)),
        )
    except Exception:
        os.close(fd)
        raise


def _strict_json_from_held(artifact: HeldArtifact, *, max_bytes: int) -> dict[str, Any]:
    if artifact.size <= 0 or artifact.size > max_bytes:
        raise InvalidRequest("held JSON size is outside the limit")
    os.lseek(artifact.fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = artifact.size
    while remaining:
        block = os.read(artifact.fd, min(remaining, 64 * 1024))
        if not block:
            raise InvalidRequest("held JSON ended early")
        chunks.append(block)
        remaining -= len(block)
    os.lseek(artifact.fd, 0, os.SEEK_SET)
    try:
        value = json.loads(
            b"".join(chunks).decode("utf-8"),
            object_pairs_hook=_strict_json_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                InvalidRequest(f"non-finite JSON number: {token}")
            ),
        )
    except InvalidRequest:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise InvalidRequest("held JSON is invalid") from exc
    if not isinstance(value, dict):
        raise InvalidRequest("held JSON must be an object")
    _validate_json_value(value)
    return value


def validate_held_authorization(
    authorization: HeldArtifact,
    *,
    policy: ControllerPolicy,
    run_id: str,
) -> None:
    value = _strict_json_from_held(authorization, max_bytes=MAX_ARTIFACT_BYTES["authorization"])
    if set(value) != AUTHORIZATION_KEYS:
        raise InvalidRequest("authorization keys differ")
    if value.get("schema") != AUTHORIZATION_SCHEMA:
        raise InvalidRequest("authorization schema differs")
    if value.get("status") != AUTHORIZATION_STATUS:
        raise InvalidRequest("authorization status differs")
    if value.get("one_run_id") != run_id:
        raise InvalidRequest("authorization one_run_id differs")
    issued_at = value.get("issued_at_utc")
    if not isinstance(issued_at, str) or RFC3339_UTC_RE.fullmatch(issued_at) is None:
        raise InvalidRequest("authorization issued_at_utc differs")
    by_role = policy.by_role
    exact = {
        "config_sha256": by_role["config"].sha256,
        "blender_executable_sha256": by_role["blender_executable"].sha256,
    }
    for key, expected in exact.items():
        if value.get(key) != expected:
            raise InvalidRequest(f"authorization {key} differs")
    operation_worker_key = "builder_sha256" if policy.operation == "build" else "auditor_sha256"
    if value.get(operation_worker_key) != by_role["worker_script"].sha256:
        raise InvalidRequest(f"authorization {operation_worker_key} differs")
    for key in (
        "source_sha256",
        "preflight_receipt_sha256",
        "controller_sha256",
        "builder_sha256",
        "auditor_sha256",
        "intersection_auditor_sha256",
    ):
        _validate_sha256(value.get(key), f"authorization.{key}")
    for key in ("candidate_blend_path", "build_report_path", "audit_report_path"):
        path_value = value.get(key)
        if (
            not isinstance(path_value, str)
            or not path_value
            or "\\" in path_value
            or path_value.startswith("/")
            or ".." in Path(path_value).parts
        ):
            raise InvalidRequest(f"authorization {key} is not project-relative")
    required_true = {
        "build_allowed",
        "audit_allowed",
        "background_required",
        "factory_startup_required",
        "autoexec_disabled_required",
    }
    for key in required_true:
        if value.get(key) is not True:
            raise InvalidRequest(f"authorization {key} must be true")
    required_false = {
        "overwrite_allowed",
        "source_mutation_allowed",
        "hair_allowed",
        "clothing_allowed",
        "internal_anatomy_allowed",
        "identity_styling_allowed",
        "runtime_activation_allowed",
        "public_export_allowed",
    }
    for key in required_false:
        if value.get(key) is not False:
            raise InvalidRequest(f"authorization {key} must be false")


def build_exact_command(
    policy: ControllerPolicy,
    authorization_path: Path,
) -> tuple[str, ...]:
    by_role = policy.by_role
    try:
        blender = by_role["blender_executable"].path.resolve(strict=True)
        worker = by_role["worker_script"].path.resolve(strict=True)
        config = by_role["config"].path.resolve(strict=True)
        authorization = authorization_path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise InvalidRequest("command artifact is unavailable") from exc
    command = (
        str(blender),
        *REQUIRED_BLENDER_FLAGS,
        "--python",
        str(worker),
        "--",
        "--config",
        str(config),
        "--authorization",
        str(authorization),
    )
    if len(command) != 11 or command.count("--") != 1:
        raise InvalidRequest("internal command grammar differs")
    if command[1:4] != REQUIRED_BLENDER_FLAGS:
        raise InvalidRequest("Blender safety flags differ")
    return command


def build_sanitized_environment(
    *,
    system_root: Path,
    temp_root: Path,
) -> Mapping[str, str]:
    system = _validate_local_absolute_path(system_root, "system_root", directory=True)
    temp = _validate_local_absolute_path(temp_root, "temp_root", directory=True)
    system32 = _validate_local_absolute_path(system / "System32", "System32", directory=True)
    comspec = _validate_local_absolute_path(system32 / "cmd.exe", "ComSpec", directory=False)
    environment = {
        "SystemRoot": str(system),
        "WINDIR": str(system),
        "ComSpec": str(comspec),
        "PATH": str(system32),
        "TEMP": str(temp),
        "TMP": str(temp),
    }
    forbidden = {
        "PYTHONPATH",
        "PYTHONHOME",
        "BLENDER_USER_SCRIPTS",
        "BLENDER_SYSTEM_SCRIPTS",
        "BLENDER_USER_CONFIG",
        "BLENDER_USER_DATAFILES",
        "BLENDER_SYSTEM_DATAFILES",
    }
    if forbidden.intersection(environment):
        raise InvalidRequest("unsafe environment entry present")
    return MappingProxyType(environment)


def _write_new_durable(path: Path, record: Mapping[str, Any], *, max_bytes: int) -> str:
    payload = canonical_json_bytes(dict(record)) + b"\n"
    if len(payload) > max_bytes:
        raise InvalidRequest("durable record exceeds the limit")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | int(getattr(os, "O_BINARY", 0))
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        raise
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short durable write")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class OneRunClaim:
    run_id: str
    claim_path: Path
    outcome_path: Path
    claim_sha256: str
    request_sha256: str


class OneRunClaimStore:
    """Create-new replay markers for one stable, untampered claim root.

    Same-principal deletion protection is a native-boundary responsibility and
    is deliberately not claimed here.
    """

    def __init__(self, root: Path):
        self.root = _validate_local_absolute_path(root, "claim_root", directory=True)
        if _is_reparse(self.root):
            raise InvalidRequest("claim_root must not be a reparse point")
        metadata = self.root.stat()
        self._root_identity = (metadata.st_dev, metadata.st_ino)

    def _assert_root_identity(self) -> None:
        try:
            metadata = self.root.stat()
        except OSError as exc:
            raise InvalidRequest("claim_root identity is unavailable") from exc
        if (metadata.st_dev, metadata.st_ino) != self._root_identity or _is_reparse(self.root):
            raise InvalidRequest("claim_root identity changed")

    def reserve(self, *, run_id: str, request_record: Mapping[str, Any]) -> OneRunClaim:
        if not isinstance(run_id, str) or RUN_ID_RE.fullmatch(run_id) is None:
            raise InvalidRequest("run_id grammar is invalid")
        request_sha256 = canonical_sha256(dict(request_record))
        self._assert_root_identity()
        claim_path = self.root / f"{run_id}.claim.json"
        outcome_path = self.root / f"{run_id}.outcome.json"
        claim_record = {
            "schema": CLAIM_SCHEMA,
            "status": "CLAIMED_ONCE",
            "run_id": run_id,
            "request_sha256": request_sha256,
            "claimed_at_utc": utc_now(),
            "replay_allowed": False,
        }
        try:
            claim_sha256 = _write_new_durable(
                claim_path,
                claim_record,
                max_bytes=MAX_CLAIM_BYTES,
            )
        except FileExistsError as exc:
            raise ClaimAlreadyExists("one-run claim already exists") from exc
        self._assert_root_identity()
        return OneRunClaim(
            run_id=run_id,
            claim_path=claim_path,
            outcome_path=outcome_path,
            claim_sha256=claim_sha256,
            request_sha256=request_sha256,
        )

    def terminalize(
        self,
        claim: OneRunClaim,
        *,
        status: str,
        reason_code: str,
        binding_sha256: str | None,
    ) -> str:
        self._assert_root_identity()
        if not isinstance(claim.run_id, str) or RUN_ID_RE.fullmatch(claim.run_id) is None:
            raise InvalidRequest("terminal claim run_id grammar is invalid")
        expected_claim_path = self.root / f"{claim.run_id}.claim.json"
        expected_outcome_path = self.root / f"{claim.run_id}.outcome.json"
        root_resolved = self.root.resolve(strict=True)
        for expected in (expected_claim_path, expected_outcome_path):
            try:
                expected.resolve(strict=False).relative_to(root_resolved)
            except (OSError, RuntimeError, ValueError) as exc:
                raise InvalidRequest("terminal record escapes claim root") from exc
        if claim.claim_path.absolute() != expected_claim_path.absolute():
            raise InvalidRequest("claim path differs from claim root")
        if claim.outcome_path.absolute() != expected_outcome_path.absolute():
            raise InvalidRequest("outcome path differs from claim root")
        try:
            claim_payload = claim.claim_path.read_bytes()
        except OSError as exc:
            raise InvalidRequest("claim record is unavailable") from exc
        if not claim_payload or len(claim_payload) > MAX_CLAIM_BYTES:
            raise InvalidRequest("claim record size differs")
        if hashlib.sha256(claim_payload).hexdigest() != claim.claim_sha256:
            raise InvalidRequest("claim record hash differs")
        claim_record = read_strict_json(claim.claim_path, max_bytes=MAX_CLAIM_BYTES)
        if set(claim_record) != {
            "schema",
            "status",
            "run_id",
            "request_sha256",
            "claimed_at_utc",
            "replay_allowed",
        }:
            raise InvalidRequest("claim record keys differ")
        if (
            claim_record.get("schema") != CLAIM_SCHEMA
            or claim_record.get("status") != "CLAIMED_ONCE"
            or claim_record.get("run_id") != claim.run_id
            or claim_record.get("request_sha256") != claim.request_sha256
            or claim_record.get("replay_allowed") is not False
        ):
            raise InvalidRequest("claim record binding differs")
        allowed_statuses = {
            "PREFLIGHT_REJECTED",
            "BLOCKED_NATIVE_BOUNDARY_REQUIRED",
            "NATIVE_PROVIDER_REJECTED",
        }
        if status not in allowed_statuses:
            raise InvalidRequest("terminal status is not allowed")
        if not isinstance(reason_code, str) or ROLE_RE.fullmatch(reason_code) is None:
            raise InvalidRequest("reason_code grammar is invalid")
        if binding_sha256 is not None:
            _validate_sha256(binding_sha256, "binding_sha256")
        record = {
            "schema": OUTCOME_SCHEMA,
            "status": status,
            "reason_code": reason_code,
            "run_id": claim.run_id,
            "claim_sha256": claim.claim_sha256,
            "request_sha256": claim.request_sha256,
            "binding_sha256": binding_sha256,
            "terminal_at_utc": utc_now(),
            "body_created": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        }
        self._assert_root_identity()
        try:
            digest = _write_new_durable(
                claim.outcome_path,
                record,
                max_bytes=MAX_OUTCOME_BYTES,
            )
        except FileExistsError as exc:
            raise OutcomeAlreadyExists("terminal outcome already exists") from exc
        self._assert_root_identity()
        return digest


class NativeLaunchProvider(Protocol):
    provider_id: str
    interface_version: str

    def launch_held_suspended_and_verify(
        self,
        *,
        command: Sequence[str],
        environment: Mapping[str, str],
        held_artifacts: Mapping[str, HeldArtifact],
        expected_process_image: HeldArtifact,
    ) -> Mapping[str, Any]:
        """Launch through an OS-enforced boundary and return exact attestation."""


@dataclass(frozen=True)
class ControllerResult:
    run_id: str
    status: str
    reason_code: str
    claim_sha256: str
    outcome_sha256: str
    binding_sha256: str | None
    process_started: bool


def _request_record(policy: ControllerPolicy, request: LaunchRequest) -> dict[str, Any]:
    return {
        "schema": BOUNDARY_SCHEMA,
        "policy_id": policy.policy_id,
        "operation": request.operation,
        "run_id": request.run_id,
        "policy_artifacts": {
            role: binding.sha256 for role, binding in sorted(policy.by_role.items())
        },
        "authorization_sha256": request.authorization.sha256,
        "native_provider_required": True,
    }


def _binding_record(held: Mapping[str, HeldArtifact], command: Sequence[str], environment: Mapping[str, str]) -> dict[str, Any]:
    return {
        "artifacts": {
            role: {
                "bytes": artifact.size,
                "sha256": artifact.sha256,
                "link_count": artifact.link_count,
            }
            for role, artifact in sorted(held.items())
        },
        "command_sha256": canonical_sha256(list(command)),
        "environment_sha256": canonical_sha256(dict(environment)),
        "held_until_terminal": True,
    }


class BlenderPreImportController:
    """Validate and terminalize a request without launching in this release."""

    def __init__(self, policy: ControllerPolicy):
        self.policy = policy

    def submit(
        self,
        request: LaunchRequest,
        *,
        provider: NativeLaunchProvider | None = None,
    ) -> ControllerResult:
        if request.operation != self.policy.operation:
            raise InvalidRequest("request operation differs from policy")
        store = OneRunClaimStore(request.claim_root)
        claim = store.reserve(
            run_id=request.run_id,
            request_record=_request_record(self.policy, request),
        )
        binding_sha256: str | None = None
        try:
            command = build_exact_command(self.policy, request.authorization.path)
            environment = build_sanitized_environment(
                system_root=request.system_root,
                temp_root=request.temp_root,
            )
            bindings = (*self.policy.artifacts, request.authorization)
            with ExitStack() as stack:
                held: dict[str, HeldArtifact] = {}
                for binding in bindings:
                    artifact = acquire_held_artifact(binding)
                    stack.callback(artifact.close)
                    held[binding.role] = artifact
                validate_held_authorization(
                    held["authorization"],
                    policy=self.policy,
                    run_id=request.run_id,
                )
                binding_sha256 = canonical_sha256(
                    _binding_record(held, command, environment)
                )

                try:
                    provider_id = getattr(provider, "provider_id", None)
                    provider_interface = getattr(provider, "interface_version", None)
                except Exception:
                    provider_id = None
                    provider_interface = None
                if (
                    EXECUTION_TRUST_BOUNDARY_CLOSED is not True
                    or provider is None
                    or type(provider_id) is not str
                    or type(provider_interface) is not str
                    or provider_id not in REVIEWED_NATIVE_PROVIDER_IDS
                    or provider_interface != NATIVE_PROVIDER_INTERFACE
                ):
                    outcome_sha256 = store.terminalize(
                        claim,
                        status="BLOCKED_NATIVE_BOUNDARY_REQUIRED",
                        reason_code="native_boundary_required",
                        binding_sha256=binding_sha256,
                    )
                    return ControllerResult(
                        run_id=request.run_id,
                        status="BLOCKED_NATIVE_BOUNDARY_REQUIRED",
                        reason_code="native_boundary_required",
                        claim_sha256=claim.claim_sha256,
                        outcome_sha256=outcome_sha256,
                        binding_sha256=binding_sha256,
                        process_started=False,
                    )

                # There is intentionally no call to the provider in this
                # release. Enabling it requires a separately reviewed native
                # implementation plus an exact authorization update.
                raise NativeBoundaryRequired("native provider execution is sealed")
        except BlenderControllerError as exc:
            if claim.outcome_path.exists():
                raise
            outcome_sha256 = store.terminalize(
                claim,
                status="PREFLIGHT_REJECTED",
                reason_code=exc.code.lower(),
                binding_sha256=binding_sha256,
            )
            return ControllerResult(
                run_id=request.run_id,
                status="PREFLIGHT_REJECTED",
                reason_code=exc.code.lower(),
                claim_sha256=claim.claim_sha256,
                outcome_sha256=outcome_sha256,
                binding_sha256=binding_sha256,
                process_started=False,
            )
        except (OSError, RuntimeError):
            if claim.outcome_path.exists():
                raise
            outcome_sha256 = store.terminalize(
                claim,
                status="PREFLIGHT_REJECTED",
                reason_code="bounded_io_failure",
                binding_sha256=binding_sha256,
            )
            return ControllerResult(
                run_id=request.run_id,
                status="PREFLIGHT_REJECTED",
                reason_code="bounded_io_failure",
                claim_sha256=claim.claim_sha256,
                outcome_sha256=outcome_sha256,
                binding_sha256=binding_sha256,
                process_started=False,
            )


def query_windows_process_image(pid: int) -> Path:
    """Return the OS-reported process image where Windows supports the query."""

    if os.name != "nt":
        raise NativeBoundaryRequired("process-image query is Windows-only")
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        raise InvalidRequest("pid must be a positive integer")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE
    query_image = kernel32.QueryFullProcessImageNameW
    query_image.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    query_image.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    handle = open_process(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        raise NativeBoundaryRequired("process image cannot be opened")
    try:
        capacity = 32768
        buffer = ctypes.create_unicode_buffer(capacity)
        length = wintypes.DWORD(capacity)
        if not query_image(handle, 0, buffer, ctypes.byref(length)):
            raise NativeBoundaryRequired("process image cannot be queried")
        return Path(buffer.value)
    finally:
        close_handle(handle)


def verify_windows_process_image(pid: int, expected: HeldArtifact) -> Mapping[str, Any]:
    """Compare the OS-reported process image to one already-held file identity.

    This helper is meaningful only while ``expected`` remains open. It does not
    create a suspended process and therefore cannot close the native launch
    boundary by itself.
    """

    if expected.role != "blender_executable":
        raise InvalidRequest("expected process image role differs")
    image_path = query_windows_process_image(pid)
    observed = acquire_held_artifact(
        ArtifactBinding(
            role="blender_executable",
            path=image_path,
            sha256=expected.sha256,
        )
    )
    try:
        if (
            observed.device != expected.device
            or observed.inode != expected.inode
            or observed.size != expected.size
            or observed.sha256 != expected.sha256
        ):
            raise NativeBoundaryRequired("OS process image identity differs")
        return MappingProxyType(
            {
                "process_image_verified": True,
                "bytes": observed.size,
                "sha256": observed.sha256,
                "path_published": False,
            }
        )
    finally:
        observed.close()


def load_machine_policy(*, operation: str) -> ControllerPolicy:
    evidence_path = PROJECT_ROOT / MACHINE_EVIDENCE_RELATIVE_PATH
    evidence = read_strict_json(evidence_path, max_bytes=512 * 1024)
    validate_machine_evidence(evidence)
    if evidence.get("schema") != BOUNDARY_SCHEMA:
        raise InvalidRequest("machine evidence schema differs")
    if evidence.get("execution_trust_boundary_closed") is not False:
        raise InvalidRequest("machine evidence must remain fail-closed")
    artifacts = evidence.get("artifact_bindings")
    if not isinstance(artifacts, dict):
        raise InvalidRequest("machine evidence artifact bindings are invalid")
    selected_roles = {
        "blender_executable": artifacts.get("blender_executable"),
        "bundled_interpreter": artifacts.get("bundled_interpreter"),
        "worker_script": artifacts.get(f"{operation}_worker"),
        "config": artifacts.get("carrier_config"),
    }
    bindings: list[ArtifactBinding] = []
    for role, record in selected_roles.items():
        if not isinstance(record, dict):
            raise InvalidRequest(f"machine evidence {role} is missing")
        if role in {"blender_executable", "bundled_interpreter"}:
            relative = record.get("installation_relative_path")
            program_files = os.environ.get("ProgramFiles")
            if not isinstance(relative, str) or not program_files:
                raise InvalidRequest("Blender installation binding is unavailable")
            path = Path(program_files) / Path(relative)
        else:
            relative = record.get("project_relative_path")
            if not isinstance(relative, str):
                raise InvalidRequest("project artifact binding path is invalid")
            path = PROJECT_ROOT / Path(relative)
        bindings.append(
            ArtifactBinding(
                role=role,
                path=path,
                sha256=_validate_sha256(record.get("sha256"), f"{role}.sha256"),
            )
        )
    return ControllerPolicy(
        policy_id=f"blender_5_1_{operation}_blocked_v1",
        operation=operation,
        artifacts=tuple(bindings),
    )


def validate_machine_evidence(evidence: Mapping[str, Any]) -> None:
    if not isinstance(evidence, Mapping) or evidence.get("schema") != BOUNDARY_SCHEMA:
        raise InvalidRequest("machine evidence schema differs")
    expected_top_level = {
        "schema",
        "evidence_id",
        "status",
        "recorded_at_utc",
        "platform",
        "artifact_bindings",
        "verified_static_capabilities",
        "native_boundary",
        "execution_trust_boundary_closed",
        "blender_execution_authorized",
        "body_build_authorized",
        "body_created",
        "candidate_assignment_authorized",
        "anatomy_authoring_authorized",
        "runtime_activation_authorized",
        "public_export_authorized",
    }
    if set(evidence) != expected_top_level:
        raise InvalidRequest("machine evidence top-level keys differ")
    if evidence.get("evidence_id") != "blender_5_1_preimport_controller_boundary_v1_20260825":
        raise InvalidRequest("machine evidence identity differs")
    if evidence.get("status") != "STATIC_CONTROLLER_VERIFIED_NATIVE_EXECUTION_BOUNDARY_OPEN":
        raise InvalidRequest("machine evidence status differs")
    if evidence.get("recorded_at_utc") != "2026-08-25T00:00:00Z":
        raise InvalidRequest("machine evidence timestamp differs")
    platform = evidence.get("platform")
    if platform != {
        "os": "Windows",
        "architecture": "x86_64",
        "blender_release_lane": "5.1",
        "machine_specific_paths_published": False,
    }:
        raise InvalidRequest("machine evidence platform differs")
    expected_capabilities = {
        "strict_request_types",
        "exact_argument_grammar",
        "sanitized_environment_grammar",
        "exact_file_hashes",
        "single_open_hash_and_identity",
        "windows_no_write_delete_share_hold",
        "atomic_create_new_claim",
        "durable_claim_flush",
        "create_new_replay_marker_with_claim_hash_revalidation",
        "atomic_terminal_outcome",
        "windows_process_image_query_and_held_identity_helper",
    }
    capabilities = evidence.get("verified_static_capabilities")
    if (
        not isinstance(capabilities, dict)
        or set(capabilities) != expected_capabilities
        or any(value is not True for value in capabilities.values())
    ):
        raise InvalidRequest("machine evidence static capabilities differ")
    if evidence.get("execution_trust_boundary_closed") is not False:
        raise InvalidRequest("machine evidence must remain fail-closed")
    for authority_key in (
        "blender_execution_authorized",
        "body_build_authorized",
        "body_created",
        "candidate_assignment_authorized",
        "anatomy_authoring_authorized",
        "runtime_activation_authorized",
        "public_export_authorized",
    ):
        if evidence.get(authority_key) is not False:
            raise InvalidRequest(f"machine evidence {authority_key} must remain false")
    native = evidence.get("native_boundary")
    expected_native_keys = {
        "interface",
        "reviewed_provider_ids",
        "execution_trust_boundary_closed",
        "process_start_allowed",
        "required_unproven_controls",
    }
    if (
        not isinstance(native, dict)
        or set(native) != expected_native_keys
        or native.get("interface") != NATIVE_PROVIDER_INTERFACE
        or native.get("reviewed_provider_ids") != []
        or native.get("execution_trust_boundary_closed") is not False
        or native.get("process_start_allowed") is not False
    ):
        raise InvalidRequest("machine evidence native boundary differs")
    unproven = native.get("required_unproven_controls")
    required_unproven = {
        "native held-handle launch without pathname replacement window",
        "held ancestor directory identities and junction defense",
        "CREATE_SUSPENDED exact lpApplicationName launch",
        "kill-on-close job and bounded descendant termination",
        "OS process-image identity comparison before resume",
        "real hostile hard-link and staging-name race closure",
        "durable two-phase build-and-audit transaction",
        "same-principal deletion and rewrite denial for claim and outcome records",
    }
    if not isinstance(unproven, list) or set(unproven) != required_unproven or len(unproven) != len(required_unproven):
        raise InvalidRequest("machine evidence native blockers differ")
    bindings = evidence.get("artifact_bindings")
    required = {
        "blender_executable",
        "bundled_interpreter",
        "controller",
        "build_worker",
        "audit_worker",
        "carrier_config",
        "worker_identity_authority",
    }
    if not isinstance(bindings, dict) or set(bindings) != required:
        raise InvalidRequest("machine evidence bindings differ")
    program_files = os.environ.get("ProgramFiles")
    if not program_files:
        raise InvalidRequest("ProgramFiles is unavailable")
    for binding_id, record in bindings.items():
        if not isinstance(record, dict):
            raise InvalidRequest(f"machine evidence {binding_id} is invalid")
        if binding_id in {"blender_executable", "bundled_interpreter"}:
            if set(record) != {"installation_relative_path", "bytes", "sha256"}:
                raise InvalidRequest(f"machine evidence {binding_id} keys differ")
            relative = record["installation_relative_path"]
            if not isinstance(relative, str) or not relative:
                raise InvalidRequest(f"machine evidence {binding_id} path differs")
            path = Path(program_files) / Path(relative)
        else:
            if set(record) != {"project_relative_path", "bytes", "sha256"}:
                raise InvalidRequest(f"machine evidence {binding_id} keys differ")
            relative = record["project_relative_path"]
            if not isinstance(relative, str) or not relative:
                raise InvalidRequest(f"machine evidence {binding_id} path differs")
            path = PROJECT_ROOT / Path(relative)
            try:
                path.resolve(strict=True).relative_to(PROJECT_ROOT.resolve(strict=True))
            except (OSError, RuntimeError, ValueError) as exc:
                raise InvalidRequest(f"machine evidence {binding_id} escapes project") from exc
        path = _validate_local_absolute_path(path, binding_id, directory=False)
        observed_bytes = path.stat().st_size
        expected_bytes = record.get("bytes")
        if (
            not isinstance(expected_bytes, int)
            or isinstance(expected_bytes, bool)
            or expected_bytes <= 0
            or observed_bytes != expected_bytes
        ):
            raise InvalidRequest(f"machine evidence {binding_id} bytes differ")
        expected_hash = _validate_sha256(record.get("sha256"), f"{binding_id}.sha256")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected_hash:
            raise InvalidRequest(f"machine evidence {binding_id} hash differs")


__all__ = [
    "ArtifactBinding",
    "ArtifactBindingError",
    "BlenderControllerError",
    "BlenderPreImportController",
    "BOUNDARY_SCHEMA",
    "CLAIM_SCHEMA",
    "ClaimAlreadyExists",
    "ControllerPolicy",
    "ControllerResult",
    "EXECUTION_TRUST_BOUNDARY_CLOSED",
    "InvalidRequest",
    "LaunchRequest",
    "MACHINE_EVIDENCE_RELATIVE_PATH",
    "NATIVE_PROVIDER_INTERFACE",
    "NativeBoundaryRequired",
    "OneRunClaim",
    "OneRunClaimStore",
    "OutcomeAlreadyExists",
    "OUTCOME_SCHEMA",
    "REVIEWED_NATIVE_PROVIDER_IDS",
    "acquire_held_artifact",
    "build_exact_command",
    "build_sanitized_environment",
    "canonical_sha256",
    "load_machine_policy",
    "query_windows_process_image",
    "read_strict_json",
    "validate_held_authorization",
    "validate_machine_evidence",
    "verify_windows_process_image",
]
