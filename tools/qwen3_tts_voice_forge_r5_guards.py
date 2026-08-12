"""Stdlib-only R5 trust, provenance, finalization, and evidence guards.

R5 is an append-only successor to the rejected R4 acceptance harness.  This
module performs no model import, environment creation, network access, GPU
work, synthesis, or playback.  It deliberately keeps the immutable payload
manifest separate from a one-use execution authorization whose *exact bytes*
must be pinned by the invoking authority.
"""

from __future__ import annotations

import contextlib
import ctypes
import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator


HASH = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")
R5_PAYLOAD_MANIFEST_REL = Path(
    "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v5.json"
)
R4_REJECTED_AUDIT_REL = Path(
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R4_INDEPENDENT_AUDIT_20260809.md"
)
R4_REJECTED_AUDIT_SHA256 = (
    "04073b96cd4d514aaa5e60b75783d0e2a1c024782fce591fc83fcfe3e2befe9b"
)
FINAL_ARTIFACT_PATHS = {
    "reference_wav": "original_design_reference.wav",
    "clone_test_wav": "runtime_clone_test.wav",
    "runtime_clone_prompt": "runtime_clone_prompt.pt",
}
ACCEPTANCE_CRITICAL_JSON_NAMES = {
    "parent_reservation_v5.json",
    "worker_manifest_v5.json",
    "voice_profile_candidate_v5.json",
    "worker_manifest_v4.json",
    "voice_profile_candidate_v4.json",
    "parent_acceptance_v5.json",
}


class R5GuardError(RuntimeError):
    """An R5 trust, provenance, artifact, or evidence check failed closed."""


class R5EvidenceError(R5GuardError):
    """Failure evidence could not be preserved unambiguously."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_hash(value: Any, label: str) -> str:
    text = str(value or "")
    if not HASH.fullmatch(text):
        raise R5GuardError(f"{label} is not one lowercase SHA-256")
    return text


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise R5GuardError(f"duplicate JSON object key rejected: {key}")
        result[key] = value
    return result


def strict_json_bytes(payload: bytes, label: str) -> Any:
    """Decode UTF-8 JSON while rejecting duplicate keys at every depth."""

    try:
        text = payload.decode("utf-8")
    except UnicodeError as exc:
        raise R5GuardError(f"{label} is not UTF-8") from exc
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
    except R5GuardError:
        raise
    except json.JSONDecodeError as exc:
        raise R5GuardError(f"{label} is not exact JSON") from exc


def strict_read_json(
    path: Path, *, expected_sha256: str | None = None, label: str | None = None
) -> dict[str, Any]:
    label = label or path.as_posix()
    if not path.is_file() or path.is_symlink():
        raise R5GuardError(f"{label} is missing, non-regular, or a symlink")
    payload = path.read_bytes()
    if expected_sha256 is not None:
        expected = require_hash(expected_sha256, f"{label} expected hash")
        if sha256_bytes(payload) != expected:
            raise R5GuardError(f"{label} differs from its external hash binding")
    value = strict_json_bytes(payload, label)
    if not isinstance(value, dict):
        raise R5GuardError(f"{label} is not an object")
    return value


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise R5EvidenceError(f"append-only evidence already exists: {path}") from exc


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    write_new(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n",
    )


def inside(root: Path, value: str | Path, label: str) -> Path:
    root = root.resolve()
    candidate = Path(str(value))
    result = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        result.relative_to(root)
    except ValueError as exc:
        raise R5GuardError(f"{label} escaped its exact root") from exc
    return result


def verify_payload_manifest(
    *,
    project_root: Path,
    expected_manifest_sha256: str,
    required_payloads: set[str],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Verify an immutable inventory from a hash supplied outside the file.

    The manifest is intentionally never allowed to authorize execution.  Its
    bytes are useful only when the caller supplies the exact independently
    published SHA-256 and a separate one-use authorization verifies it again.
    """

    project_root = project_root.resolve()
    expected = require_hash(expected_manifest_sha256, "R5 payload manifest hash")
    path = (project_root / R5_PAYLOAD_MANIFEST_REL).resolve()
    manifest = strict_read_json(
        path, expected_sha256=expected, label="R5 immutable payload manifest"
    )
    if (
        manifest.get("schema") != "qwen3_tts_voice_forge_payload_manifest_v5"
        or manifest.get("status") != "IMMUTABLE_PAYLOAD_REQUIRES_EXTERNAL_AUTHORIZATION"
        or manifest.get("execution_allowed") is not False
        or manifest.get("self_authorization_allowed") is not False
    ):
        raise R5GuardError("R5 payload manifest attempted to authorize itself")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise R5GuardError("R5 payload manifest files are not an exact list")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
            raise R5GuardError("R5 payload manifest row shape is not exact")
        rel = str(row.get("path") or "")
        if not rel or rel in indexed or rel == R5_PAYLOAD_MANIFEST_REL.as_posix():
            raise R5GuardError("R5 payload path is empty, duplicated, or self-referential")
        target = inside(project_root, rel, "R5 payload")
        if (
            not target.is_file()
            or target.is_symlink()
            or not isinstance(row.get("bytes"), int)
            or row["bytes"] < 0
            or target.stat().st_size != row["bytes"]
            or sha256_file(target) != require_hash(row.get("sha256"), f"R5 {rel}")
        ):
            raise R5GuardError(f"R5 immutable payload drift: {rel}")
        indexed[rel] = row
    if set(indexed) != set(required_payloads):
        missing = sorted(set(required_payloads) - set(indexed))
        extra = sorted(set(indexed) - set(required_payloads))
        raise R5GuardError(
            f"R5 immutable payload inventory is not exact; missing={missing}, extra={extra}"
        )
    return manifest, indexed


def verify_execution_authorization(
    *,
    project_root: Path,
    authorization_path: Path,
    expected_authorization_sha256: str,
    expected_manifest_sha256: str,
    bundle_id: str,
    run_id: str,
    now: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify exact externally hash-pinned, bundle/run-scoped one-use authority."""

    project_root = project_root.resolve()
    authorization_path = authorization_path.resolve()
    try:
        rel = authorization_path.relative_to(project_root).as_posix()
    except ValueError as exc:
        raise R5GuardError("R5 authorization escaped the project") from exc
    if not rel.startswith("Data/voice/authorizations/qwen3_tts_voice_forge_v5/"):
        raise R5GuardError("R5 authorization is outside its append-only authority root")
    expected_auth = require_hash(
        expected_authorization_sha256, "R5 execution authorization hash"
    )
    authorization = strict_read_json(
        authorization_path,
        expected_sha256=expected_auth,
        label="R5 execution authorization",
    )
    exact_keys = {
        "schema",
        "status",
        "execution_allowed",
        "one_use",
        "payload_manifest_path",
        "payload_manifest_sha256",
        "independent_audit_path",
        "independent_audit_sha256",
        "rejected_r4_audit_path",
        "rejected_r4_audit_sha256",
        "bundle_id",
        "run_id",
        "authorization_nonce_sha256",
        "issued_utc",
        "expires_utc",
    }
    if set(authorization) != exact_keys:
        raise R5GuardError("R5 authorization fields are incomplete or unexpected")
    if (
        authorization.get("schema") != "qwen3_tts_voice_forge_execution_authorization_v5"
        or authorization.get("status") != "INDEPENDENT_AUDIT_ACCEPTED_ONE_BOUNDED_RUN"
        or authorization.get("execution_allowed") is not True
        or authorization.get("one_use") is not True
        or authorization.get("payload_manifest_path")
        != R5_PAYLOAD_MANIFEST_REL.as_posix()
        or authorization.get("payload_manifest_sha256")
        != require_hash(expected_manifest_sha256, "R5 expected payload hash")
        or authorization.get("bundle_id") != bundle_id
        or authorization.get("run_id") != run_id
    ):
        raise R5GuardError("R5 authorization scope or immutable payload binding mismatch")
    require_hash(authorization.get("authorization_nonce_sha256"), "R5 authorization nonce")
    if (
        authorization.get("rejected_r4_audit_path") != R4_REJECTED_AUDIT_REL.as_posix()
        or authorization.get("rejected_r4_audit_sha256") != R4_REJECTED_AUDIT_SHA256
        or sha256_file(project_root / R4_REJECTED_AUDIT_REL) != R4_REJECTED_AUDIT_SHA256
    ):
        raise R5GuardError("R5 authorization does not preserve the exact rejected R4 audit")
    audit_rel = str(authorization.get("independent_audit_path") or "")
    if (
        not audit_rel.startswith("System/Docs/")
        or "TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R5_INDEPENDENT_AUDIT_"
        not in audit_rel
    ):
        raise R5GuardError("R5 authorization names no exact independent R5 audit")
    audit_path = inside(project_root, audit_rel, "R5 independent audit")
    audit_hash = require_hash(
        authorization.get("independent_audit_sha256"), "R5 independent audit hash"
    )
    if not audit_path.is_file() or audit_path.is_symlink() or sha256_file(audit_path) != audit_hash:
        raise R5GuardError("R5 independent audit file/hash mismatch")
    try:
        issued = datetime.fromisoformat(str(authorization["issued_utc"]).replace("Z", "+00:00"))
        expires = datetime.fromisoformat(str(authorization["expires_utc"]).replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise R5GuardError("R5 authorization timestamps are invalid") from exc
    current = now or datetime.now(timezone.utc)
    if issued.tzinfo is None or expires.tzinfo is None or issued > current or current > expires:
        raise R5GuardError("R5 authorization is future-dated or expired")
    return authorization, {
        "path": rel,
        "bytes": authorization_path.stat().st_size,
        "sha256": expected_auth,
        "payload_manifest_sha256": authorization["payload_manifest_sha256"],
        "independent_audit_path": audit_rel,
        "independent_audit_sha256": audit_hash,
    }


def parse_canonical_child_result(
    stdout: bytes,
    *,
    expected_schema: str,
    exact_keys: set[str],
) -> dict[str, Any]:
    """Accept one canonical object and exactly one trailing LF."""

    if not stdout.endswith(b"\n") or stdout.endswith(b"\n\n"):
        raise R5GuardError("R5 child stdout newline policy is not exact")
    payload = stdout[:-1]
    if not payload or b"\r" in payload or b"\n" in payload:
        raise R5GuardError("R5 child stdout is not one compact JSON object")
    value = strict_json_bytes(payload, "R5 child stdout")
    if not isinstance(value, dict) or set(value) != exact_keys:
        raise R5GuardError("R5 child stdout fields are incomplete or unexpected")
    if value.get("schema") != expected_schema:
        raise R5GuardError("R5 child stdout schema mismatch")
    if payload != canonical_bytes(value):
        raise R5GuardError("R5 child stdout is not the one canonical serialization")
    return value


def _find_forbidden_package_payload(value: Any, trail: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _find_forbidden_package_payload(child, f"{trail}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _find_forbidden_package_payload(child, f"{trail}[{index}]")
        return
    if isinstance(value, str):
        normalized = value.replace("\\", "/").lower()
        if normalized.startswith(("torch/", "torchaudio/")) and normalized.endswith(
            (".pyd", ".dll", ".exe", ".py", ".pyc", ".pth")
        ):
            raise R5GuardError(f"unbound executable/package payload in provenance: {trail}")


def require_strict_provenance_map(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"torch", "torchaudio"}:
        raise R5GuardError(f"{label} lacks exact Torch/Torchaudio provenance")
    _find_forbidden_package_payload(value)
    for package in ("torch", "torchaudio"):
        _require_strict_provenance_row(package, value[package], label)
    return value


def _require_strict_provenance_row(
    package: str, row: Any, label: str
) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise R5GuardError(f"{label} {package} is not an object")
    _find_forbidden_package_payload(row, f"{label}.{package}")
    bounded = row.get("bounded_non_executable_installer_metadata_differences")
    legacy = row.get("installer_generated_differences")
    if (
        row.get("exact_wheel_to_installed_files_bound_r4") is not True
        or row.get("exact_wheel_to_installed_record_and_files_bound") is not True
        or row.get("unbound_installer_generated_package_bytes_allowed") is not False
        or not isinstance(bounded, list)
        or not isinstance(legacy, list)
        or sorted(bounded) != sorted(legacy)
        or not isinstance(row.get("wheel_members_bound_to_installed_files"), int)
        or row["wheel_members_bound_to_installed_files"] <= 0
        or not isinstance(row.get("installed_real_package_payload_count"), int)
        or row["installed_real_package_payload_count"] <= 0
    ):
        raise R5GuardError(f"{label} {package} is not strict derived R4 evidence")
    for path in bounded:
        normalized = str(path).replace("\\", "/")
        if normalized.startswith(package + "/") or not normalized.endswith(
            (".dist-info/INSTALLER", ".dist-info/direct_url.json", ".dist-info/REQUESTED")
        ):
            raise R5GuardError(f"{label} {package} contains an unbounded extra")
    require_hash(row.get("exact_wheel_sha256"), f"{label} {package} wheel")
    require_hash(row.get("installed_record_sha256"), f"{label} {package} RECORD")
    return row


def reconcile_provenance_maps(
    *,
    parent_preflight: Any,
    reservation: Any,
    worker_pre_model: Any,
    worker_post_execution: Any,
    parent_postflight: Any,
) -> dict[str, Any]:
    maps = {
        "parent_preflight": require_strict_provenance_map(
            parent_preflight, "parent preflight"
        ),
        "reservation": require_strict_provenance_map(reservation, "parent reservation"),
        "worker_pre_model": require_strict_provenance_map(
            worker_pre_model, "worker pre-model"
        ),
        "worker_post_execution": require_strict_provenance_map(
            worker_post_execution, "worker post-execution"
        ),
        "parent_postflight": require_strict_provenance_map(
            parent_postflight, "fresh parent postflight"
        ),
    }
    canonical = {name: canonical_bytes(value) for name, value in maps.items()}
    if len(set(canonical.values())) != 1:
        raise R5GuardError("Torch/Torchaudio provenance differs across R5 trust phases")
    exact = maps["parent_preflight"]
    return {
        "canonical_provenance_sha256": canonical_sha256(exact),
        "all_five_maps_strictly_equal": True,
        "parent_preflight_derived": True,
        "parent_postflight_freshly_recomputed": True,
        "unbound_package_payloads_rejected": True,
        "exact_provenance": exact,
    }


def require_full_provenance_capsule(value: Any, label: str) -> dict[str, Any]:
    """Validate complete installed RECORD and exact wheel-member file maps."""

    if not isinstance(value, dict) or set(value) != {"torch", "torchaudio"}:
        raise R5GuardError(f"{label} lacks exact full Torch/Torchaudio capsules")
    for package in ("torch", "torchaudio"):
        capsule = value[package]
        if not isinstance(capsule, dict) or set(capsule) != {
            "environment_distribution_spec_sha256",
            "installed_record_evidence",
            "wheel_archive_evidence",
            "strict_binding",
        }:
            raise R5GuardError(f"{label} {package} capsule shape is not exact")
        require_hash(
            capsule["environment_distribution_spec_sha256"],
            f"{label} {package} environment distribution spec",
        )
        installed = capsule["installed_record_evidence"]
        wheel = capsule["wheel_archive_evidence"]
        binding = _require_strict_provenance_row(
            package, capsule["strict_binding"], f"{label} strict binding"
        )
        if not isinstance(installed, dict) or not isinstance(wheel, dict):
            raise R5GuardError(f"{label} {package} file evidence is not an object")
        files = installed.get("installed_files")
        if (
            not isinstance(files, list)
            or not files
            or installed.get("record_rows_verified") != len(files)
            or installed.get("record_sha256") != binding["installed_record_sha256"]
        ):
            raise R5GuardError(f"{label} {package} installed RECORD map is incomplete")
        seen_files: set[str] = set()
        for row in files:
            if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
                raise R5GuardError(f"{label} {package} installed file row is not exact")
            path = str(row.get("path") or "")
            if (
                not path
                or path in seen_files
                or not isinstance(row.get("bytes"), int)
                or row["bytes"] < 0
            ):
                raise R5GuardError(f"{label} {package} installed file row is invalid")
            seen_files.add(path)
            require_hash(row.get("sha256"), f"{label} {package} installed file")
        members = wheel.get("members")
        if (
            not isinstance(members, dict)
            or not members
            or wheel.get("sha256") != binding["exact_wheel_sha256"]
            or wheel.get("package") != package
            or wheel.get("real_importable_payload_proven") is not True
        ):
            raise R5GuardError(f"{label} {package} exact wheel member map is incomplete")
        for path, row in members.items():
            if (
                not isinstance(path, str)
                or not path
                or not isinstance(row, dict)
                or set(row) != {"bytes", "sha256", "record_self"}
                or not isinstance(row.get("bytes"), int)
                or row["bytes"] < 0
                or not isinstance(row.get("record_self"), bool)
            ):
                raise R5GuardError(f"{label} {package} wheel member row is invalid")
            require_hash(row.get("sha256"), f"{label} {package} wheel member")
        if wheel.get("record_path") not in members:
            raise R5GuardError(f"{label} {package} wheel RECORD is absent from member map")
        installed_paths = {
            str(Path(row["path"]).as_posix()).split("Lib/site-packages/", 1)[-1]
            for row in files
        }
        wheel_paths = set(members)
        allowed_extras = set(binding["installer_generated_differences"])
        if installed_paths - wheel_paths != allowed_extras:
            raise R5GuardError(
                f"{label} {package} installed/wheel file-map difference is not exact"
            )
        package_prefix = package + "/"
        if any(
            path.startswith(package_prefix)
            and path not in wheel_paths
            for path in installed_paths
        ):
            raise R5GuardError(f"{label} {package} contains an injected package payload")
    return value


def reconcile_full_provenance_capsules(
    *,
    parent_preflight: Any,
    reservation: Any,
    worker_pre_model: Any,
    worker_post_execution: Any,
    parent_postflight: Any,
) -> dict[str, Any]:
    capsules = {
        "parent_preflight": require_full_provenance_capsule(
            parent_preflight, "parent full preflight"
        ),
        "reservation": require_full_provenance_capsule(
            reservation, "parent full reservation"
        ),
        "worker_pre_model": require_full_provenance_capsule(
            worker_pre_model, "worker full pre-model"
        ),
        "worker_post_execution": require_full_provenance_capsule(
            worker_post_execution, "worker full post-execution"
        ),
        "parent_postflight": require_full_provenance_capsule(
            parent_postflight, "fresh parent full postflight"
        ),
    }
    serialized = {name: canonical_bytes(value) for name, value in capsules.items()}
    if len(set(serialized.values())) != 1:
        raise R5GuardError(
            "complete Torch/Torchaudio installed/wheel file maps differ across phases"
        )
    exact = capsules["parent_preflight"]
    return {
        "canonical_full_provenance_sha256": canonical_sha256(exact),
        "all_five_complete_capsules_strictly_equal": True,
        "installed_record_file_maps_parent_derived": True,
        "wheel_archive_member_maps_parent_derived": True,
        "fresh_parent_postflight_recomputed": True,
        "injected_package_extras_rejected": True,
        "exact_full_provenance": exact,
    }


def reserve_incident(root: Path, bundle_id: str, run_id: str) -> Path:
    if not SAFE_ID.fullmatch(bundle_id) or not SAFE_ID.fullmatch(run_id):
        raise R5EvidenceError("unsafe bundle or run ID cannot reserve incident evidence")
    incident_root = root.resolve() / "failure_journal" / bundle_id / run_id
    incident_root.mkdir(parents=True, exist_ok=True)
    for _ in range(128):
        incident = incident_root / f"incident_{secrets.token_hex(16)}"
        try:
            incident.mkdir(exist_ok=False)
        except FileExistsError:
            continue
        write_new_json(
            incident / "failure_slot_reserved.json",
            {
                "schema": "qwen3_tts_voice_forge_failure_slot_v5",
                "status": "RESERVED_BEFORE_ATTEMPT_ALLOCATION",
                "utc": utc_now(),
                "bundle_id": bundle_id,
                "run_id": run_id,
                "incident_id": incident.name,
            },
        )
        return incident
    raise R5EvidenceError("could not reserve one collision-safe R5 incident directory")


def preserve_failure_or_raise(
    incident: Path,
    *,
    exc: BaseException,
    stage: str,
    attempt: str | None,
    worker_started: bool,
    traceback_text: str,
) -> Path:
    evidence = {
        "schema": "qwen3_tts_voice_forge_parent_failure_v5",
        "status": "FAILED_TEXT_PLUS_SILENCE_ONLY",
        "utc": utc_now(),
        "stage": stage,
        "attempt": attempt,
        "worker_started": worker_started,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "traceback": traceback_text,
        "fallback": "TEXT_PLUS_SILENCE_ONLY_NO_GENERIC_SAPI_OR_OTHER_PERSON",
        "preservation_is_append_only": True,
    }
    errors: list[str] = []
    for index in range(1, 1000):
        path = incident / f"failure_{index:03d}.json"
        try:
            write_new_json(path, evidence)
        except BaseException as write_exc:
            errors.append(f"{type(write_exc).__name__}:{write_exc}")
            continue
        reopened = strict_read_json(path, label="R5 preserved failure")
        if reopened != evidence:
            raise R5EvidenceError("R5 failure evidence changed after durable write")
        return path
    raise R5EvidenceError(
        "R5 failure evidence could not be preserved; " + " | ".join(errors[-3:])
    )


def finalize_pending_tree(pending: Path, finalized: Path) -> Path:
    """Move a stopped-child tree into a new parent-owned finalization path."""

    pending = pending.resolve()
    finalized = finalized.resolve()
    if not pending.is_dir() or pending.is_symlink():
        raise R5GuardError("R5 pending output tree is missing or unsafe")
    if finalized.exists() or finalized.is_symlink():
        raise R5GuardError("R5 finalization target is preoccupied")
    if pending.parent != finalized.parent:
        raise R5GuardError("R5 finalization must be one same-volume sibling rename")
    pending.rename(finalized)
    if not finalized.is_dir() or pending.exists():
        raise R5GuardError("R5 parent-owned atomic finalization did not complete")
    return finalized


def artifact_snapshot(root: Path, relative_paths: list[str]) -> dict[str, dict[str, Any]]:
    root = root.resolve()
    result: dict[str, dict[str, Any]] = {}
    for rel in relative_paths:
        path = inside(root, rel, "R5 finalized artifact")
        if not path.is_file() or path.is_symlink():
            raise R5GuardError(f"R5 finalized artifact is unsafe: {rel}")
        result[rel] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return result


@contextlib.contextmanager
def hold_read_only_windows_handles(paths: list[Path]) -> Iterator[list[int]]:
    """Deny write/delete opens while acceptance is durably written on Windows."""

    if os.name != "nt":
        raise R5GuardError("R5 real artifact acceptance requires Windows share locks")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    create_file.restype = ctypes.c_void_p
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    close_handle.restype = ctypes.c_int
    generic_read = 0x80000000
    share_read = 0x00000001
    open_existing = 3
    normal = 0x00000080
    invalid = ctypes.c_void_p(-1).value
    handles: list[int] = []
    try:
        for path in paths:
            handle = create_file(
                str(path.resolve()),
                generic_read,
                share_read,
                None,
                open_existing,
                normal,
                None,
            )
            if handle in (None, invalid):
                raise R5GuardError(
                    f"cannot hold R5 artifact against mutation: {path}; "
                    f"winerror={ctypes.get_last_error()}"
                )
            handles.append(int(handle))
        yield handles
    finally:
        for handle in reversed(handles):
            close_handle(ctypes.c_void_p(handle))


def durable_acceptance_with_held_artifacts(
    *,
    finalized_root: Path,
    relative_paths: list[str],
    acceptance_path: Path,
    acceptance: dict[str, Any],
    semantic_validator: Callable[[], None],
    handle_context: Callable[[list[Path]], Any] = hold_read_only_windows_handles,
    additional_held_paths: list[Path] | None = None,
) -> dict[str, Any]:
    paths = [inside(finalized_root, rel, "R5 acceptance artifact") for rel in relative_paths]
    paths.extend(path.resolve() for path in (additional_held_paths or []))
    before = artifact_snapshot(finalized_root, relative_paths)
    with handle_context(paths):
        semantic_validator()
        locked = artifact_snapshot(finalized_root, relative_paths)
        if locked != before:
            raise R5GuardError("R5 artifact changed before held acceptance")
        write_new_json(acceptance_path, acceptance)
        acceptance_bytes = acceptance_path.read_bytes()
        reopened = strict_json_bytes(acceptance_bytes, "R5 durable acceptance")
        if reopened != acceptance:
            raise R5GuardError("R5 durable acceptance changed after write")
        semantic_validator()
        after = artifact_snapshot(finalized_root, relative_paths)
        if after != before:
            raise R5GuardError("R5 artifact changed across durable acceptance")
    return {
        "artifact_snapshot": before,
        "acceptance_bytes": len(acceptance_bytes),
        "acceptance_sha256": sha256_bytes(acceptance_bytes),
        "write_delete_denied_while_acceptance_committed": True,
        "post_acceptance_reopen_passed": True,
        "later_use_must_reopen_acceptance_and_exact_seals": True,
    }
