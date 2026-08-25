"""Static build-and-audit closure for the inactive MakeHuman carrier.

This module performs no Blender or process operation.  It closes a specific
gap between the verified pre-import controller and a future reviewed native
provider: one carrier attempt is a two-stage build *and* audit transaction,
and every source/code file plus every reserved output must be bound together
before either stage may start.

The returned record deliberately grants no execution authority.  It contains
only project-relative paths or path digests; machine-private absolute paths
remain in memory.
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from Core import avatar_blender_native_provider_contract as native_contract
from Core import avatar_blender_preimport_controller as preimport
from Core import avatar_makehuman_rigged_carrier as carrier


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLOSURE_SCHEMA = "kira.avatar_builder.blender_carrier_transaction_closure.v1"
CLOSURE_STATUS = (
    "STATIC_TWO_STAGE_CLOSURE_VERIFIED_NATIVE_TRANSACTION_PROVIDER_REQUIRED"
)
MAX_CLOSURE_FILES = 24
MAX_CLOSURE_FILE_BYTES = 256 * 1024 * 1024
ROLE_RE = re.compile(r"^[a-z][a-z0-9_]{2,47}$")

PROJECT_FIXED_INPUTS = MappingProxyType(
    {
        "carrier_controller": carrier.CONTROLLER_RELATIVE_PATH,
        "build_worker": carrier.BUILDER_RELATIVE_PATH,
        "audit_worker": carrier.AUDITOR_RELATIVE_PATH,
        "intersection_auditor": carrier.INTERSECTION_AUDITOR_RELATIVE_PATH,
        "preimport_controller": "Core/avatar_blender_preimport_controller.py",
        "native_provider_contract": "Core/avatar_blender_native_provider_contract.py",
        "transaction_closure_controller": (
            "Core/avatar_blender_carrier_transaction_closure.py"
        ),
    }
)

EXPECTED_PROJECT_ROLES = frozenset(
    {
        "config",
        "source_blend",
        "source_qualification",
        "base_obj",
        "female_macro_target_0",
        "female_macro_target_1",
        "asset_license",
        "skeleton_definition",
        "skeleton_weights",
        *PROJECT_FIXED_INPUTS.keys(),
    }
)
EXPECTED_INSTALLED_ROLES = frozenset(
    {"blender_executable", "bundled_interpreter"}
)
EXPECTED_OUTPUT_ROLES = frozenset(
    {
        "one_run_authorization",
        "candidate_blend",
        "build_report",
        "audit_report",
    }
)
TRANSACTION_STAGES = (
    "native_claim_create_new_and_flush",
    "hold_complete_input_and_ancestor_closure",
    "launch_build_suspended_assign_job_verify_image_resume_once",
    "hold_and_validate_new_candidate_and_build_report",
    "launch_audit_suspended_assign_job_verify_image_resume_once",
    "hold_and_validate_new_audit_report",
    "terminalize_exactly_once_and_flush",
)
AUTHORITY_KEYS = (
    "native_provider_reviewed",
    "native_transaction_interface_available",
    "operating_system_evidence_verified",
    "blender_execution_authorized",
    "body_build_authorized",
    "body_created",
    "candidate_assignment_authorized",
    "anatomy_authoring_authorized",
    "runtime_activation_authorized",
    "public_export_authorized",
)


class CarrierTransactionClosureError(ValueError):
    """The exact static carrier transaction closure is not satisfied."""


def _sha256_file_descriptor(fd: int) -> tuple[int, str, int, int, int]:
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode):
        raise CarrierTransactionClosureError("closure input is not a regular file")
    if before.st_size <= 0 or before.st_size > MAX_CLOSURE_FILE_BYTES:
        raise CarrierTransactionClosureError("closure input size is outside the limit")
    link_count = int(getattr(before, "st_nlink", 1))
    if link_count != 1:
        raise CarrierTransactionClosureError("closure input must be singly linked")
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
        link_count,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        int(getattr(after, "st_nlink", 1)),
    )
    if identity_before != identity_after:
        raise CarrierTransactionClosureError("closure input changed during hashing")
    return (
        int(before.st_size),
        digest.hexdigest(),
        int(before.st_dev),
        int(before.st_ino),
        link_count,
    )


def _relative_project_path(root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise CarrierTransactionClosureError("project input escapes the project root") from exc
    parts = PurePosixPath(relative).parts
    if not parts or ".." in parts or relative.startswith("/"):
        raise CarrierTransactionClosureError("project-relative input path differs")
    return relative


@dataclass(frozen=True)
class ClosureInput:
    role: str
    scope: str
    path: Path = field(repr=False)
    safe_relative_path: str
    bytes: int
    sha256: str
    path_sha256: str
    canonical_path_sha256: str
    device: int = field(repr=False)
    inode: int = field(repr=False)
    link_count: int

    def __post_init__(self) -> None:
        if ROLE_RE.fullmatch(self.role) is None:
            raise CarrierTransactionClosureError("closure input role differs")
        if self.scope not in {"project", "blender_installation"}:
            raise CarrierTransactionClosureError("closure input scope differs")
        if not isinstance(self.path, Path) or not self.path.is_absolute():
            raise CarrierTransactionClosureError("closure input private path differs")
        if (
            not isinstance(self.safe_relative_path, str)
            or not self.safe_relative_path
            or "\\" in self.safe_relative_path
            or self.safe_relative_path.startswith("/")
            or ".." in PurePosixPath(self.safe_relative_path).parts
        ):
            raise CarrierTransactionClosureError("closure safe relative path differs")
        if type(self.bytes) is not int or self.bytes <= 0:
            raise CarrierTransactionClosureError("closure byte count differs")
        for label, value in (
            ("sha256", self.sha256),
            ("path_sha256", self.path_sha256),
            ("canonical_path_sha256", self.canonical_path_sha256),
        ):
            if type(value) is not str or preimport.SHA256_RE.fullmatch(value) is None:
                raise CarrierTransactionClosureError(f"closure {label} differs")
        if self.link_count != 1:
            raise CarrierTransactionClosureError("closure link count differs")

    def safe_record(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "scope": self.scope,
            "relative_path": self.safe_relative_path,
            "bytes": self.bytes,
            "sha256": self.sha256,
            "path_sha256": self.path_sha256,
            "canonical_path_sha256": self.canonical_path_sha256,
            "link_count": 1,
        }


def _acquire_closure_input(
    *,
    role: str,
    scope: str,
    path: Path,
    safe_relative_path: str,
    expected_bytes: int | None,
    expected_sha256: str | None,
) -> tuple[ClosureInput, int]:
    try:
        absolute = path.absolute()
        if not absolute.is_absolute() or preimport._is_unc(absolute):  # noqa: SLF001
            raise CarrierTransactionClosureError("closure input path is not local absolute")
        if carrier._is_reparse(absolute):  # noqa: SLF001
            raise CarrierTransactionClosureError("closure input is a reparse point")
        native_path = carrier.native_filesystem_path(absolute)
        if not native_path.is_file():
            raise CarrierTransactionClosureError("closure input is absent")
        fd = preimport._open_held_read(native_path)  # noqa: SLF001
    except (OSError, preimport.BlenderControllerError, carrier.RiggedCarrierError) as exc:
        raise CarrierTransactionClosureError("closure input cannot be held") from exc
    try:
        size, digest, device, inode, link_count = _sha256_file_descriptor(fd)
        if expected_bytes is not None and size != expected_bytes:
            raise CarrierTransactionClosureError(f"{role} byte count differs")
        if expected_sha256 is not None and digest != expected_sha256:
            raise CarrierTransactionClosureError(f"{role} SHA-256 differs")
        private_path = str(native_path)
        return (
            ClosureInput(
                role=role,
                scope=scope,
                path=absolute,
                safe_relative_path=safe_relative_path,
                bytes=size,
                sha256=digest,
                path_sha256=native_contract.private_windows_path_sha256(private_path),
                canonical_path_sha256=(
                    native_contract.canonical_windows_path_sha256(private_path)
                ),
                device=device,
                inode=inode,
                link_count=link_count,
            ),
            fd,
        )
    except Exception:
        os.close(fd)
        raise


def _binding_record(value: Mapping[str, Any], label: str) -> tuple[str, int, str]:
    if set(value) != {"path", "bytes", "sha256"}:
        raise CarrierTransactionClosureError(f"{label} binding keys differ")
    path = value.get("path")
    byte_count = value.get("bytes")
    digest = value.get("sha256")
    if (
        type(path) is not str
        or not path
        or type(byte_count) is not int
        or byte_count <= 0
        or type(digest) is not str
        or preimport.SHA256_RE.fullmatch(digest) is None
    ):
        raise CarrierTransactionClosureError(f"{label} binding differs")
    return path, byte_count, digest


def _collect_project_expectations(
    *,
    project_root: Path,
    config_path: Path,
) -> tuple[dict[str, tuple[Path, int | None, str | None]], Mapping[str, Any]]:
    root = project_root.resolve(strict=True)
    config_absolute = config_path.resolve(strict=True)
    config = carrier.read_json(config_absolute, "carrier transaction config")
    carrier._validate_config_shape(config)  # noqa: SLF001

    expectations: dict[str, tuple[Path, int | None, str | None]] = {
        "config": (
            config_absolute,
            config_absolute.stat().st_size,
            carrier.sha256_file(config_absolute),
        )
    }

    source = config["source"]
    raw_path, byte_count, digest = _binding_record(
        {key: source[key] for key in ("path", "bytes", "sha256")},
        "source",
    )
    expectations["source_blend"] = (
        carrier.project_path(root, raw_path, "source", must_exist=True),
        byte_count,
        digest,
    )
    qualification_path, qualification_bytes, qualification_sha = _binding_record(
        source["qualification"],
        "source qualification",
    )
    expectations["source_qualification"] = (
        carrier.project_path(
            root,
            qualification_path,
            "source qualification",
            must_exist=True,
        ),
        qualification_bytes,
        qualification_sha,
    )

    build_inputs = config["source_build_inputs"]
    for role, label, value in (
        ("base_obj", "base OBJ", build_inputs["base_obj"]),
        ("asset_license", "asset license", build_inputs["license"]),
        ("skeleton_definition", "skeleton definition", config["skeleton"]["definition"]),
        ("skeleton_weights", "skeleton weights", config["skeleton"]["weights"]),
    ):
        if not isinstance(value, Mapping) or not {"path", "bytes", "sha256"}.issubset(value):
            raise CarrierTransactionClosureError(f"{label} binding differs")
        raw_path, byte_count, digest = _binding_record(
            {key: value[key] for key in ("path", "bytes", "sha256")},
            label,
        )
        expectations[role] = (
            carrier.project_path(root, raw_path, label, must_exist=True),
            byte_count,
            digest,
        )

    targets = build_inputs["female_macro_targets"]
    if type(targets) is not list or len(targets) != 2:
        raise CarrierTransactionClosureError("exactly two macro targets are required")
    for index, target in enumerate(targets):
        if set(target) != {"path", "bytes", "sha256", "weight"}:
            raise CarrierTransactionClosureError("macro-target keys differ")
        if type(target["weight"]) not in {int, float} or float(target["weight"]) != 1.0:
            raise CarrierTransactionClosureError("macro-target weight differs")
        raw_path, byte_count, digest = _binding_record(
            {key: target[key] for key in ("path", "bytes", "sha256")},
            f"macro target {index}",
        )
        expectations[f"female_macro_target_{index}"] = (
            carrier.project_path(
                root,
                raw_path,
                f"macro target {index}",
                must_exist=True,
            ),
            byte_count,
            digest,
        )

    for role, relative in PROJECT_FIXED_INPUTS.items():
        path = carrier.project_path(root, relative, role, must_exist=True)
        expectations[role] = (path, None, None)
    if set(expectations) != EXPECTED_PROJECT_ROLES:
        raise CarrierTransactionClosureError("project input role closure differs")
    return expectations, config


def _validate_policy_pair(
    build_policy: preimport.ControllerPolicy,
    audit_policy: preimport.ControllerPolicy,
    *,
    config_path: Path,
) -> None:
    if build_policy.operation != "build" or audit_policy.operation != "audit":
        raise CarrierTransactionClosureError("build/audit policy order differs")
    build = build_policy.by_role
    audit = audit_policy.by_role
    for role in ("blender_executable", "bundled_interpreter", "config"):
        left = build[role]
        right = audit[role]
        if (
            left.path.resolve(strict=True) != right.path.resolve(strict=True)
            or left.sha256 != right.sha256
        ):
            raise CarrierTransactionClosureError(f"{role} differs across stages")
    if build["config"].path.resolve(strict=True) != config_path.resolve(strict=True):
        raise CarrierTransactionClosureError("policy config differs from transaction config")
    if build["worker_script"].path.name != preimport.BUILD_WORKER_NAME:
        raise CarrierTransactionClosureError("build worker differs")
    if audit["worker_script"].path.name != preimport.AUDIT_WORKER_NAME:
        raise CarrierTransactionClosureError("audit worker differs")


def _output_records(
    *,
    project_root: Path,
    config: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Path]]:
    root = project_root.resolve(strict=True)
    output = config["output"]
    if set(output) != EXPECTED_OUTPUT_ROLES | {"allowed_root"}:
        raise CarrierTransactionClosureError("carrier output keys differ")
    paths = carrier._output_paths(root, output)  # noqa: SLF001
    if set(paths) != EXPECTED_OUTPUT_ROLES:
        raise CarrierTransactionClosureError("carrier output path closure differs")
    records: dict[str, dict[str, Any]] = {}
    for role, path in sorted(paths.items()):
        relative = _relative_project_path(root, path)
        exists = path.exists() or path.is_symlink()
        records[role] = {
            "role": role,
            "relative_path": relative,
            "path_sha256": native_contract.private_windows_path_sha256(str(path)),
            "canonical_path_sha256": native_contract.canonical_windows_path_sha256(
                str(path)
            ),
            "must_be_create_new": True,
            "currently_absent": not exists,
        }
    return records, paths


def _command_for_stage(
    *,
    policy: preimport.ControllerPolicy,
    authorization_path: Path,
) -> tuple[str, ...]:
    by_role = policy.by_role
    command = (
        str(by_role["blender_executable"].path.resolve(strict=True)),
        *preimport.REQUIRED_BLENDER_FLAGS,
        "--python",
        str(by_role["worker_script"].path.resolve(strict=True)),
        "--",
        "--config",
        str(by_role["config"].path.resolve(strict=True)),
        "--authorization",
        str(authorization_path.absolute()),
    )
    if len(command) != 11 or command[1:4] != preimport.REQUIRED_BLENDER_FLAGS:
        raise CarrierTransactionClosureError("stage command grammar differs")
    return command


def build_static_transaction_closure(
    *,
    build_policy: preimport.ControllerPolicy,
    audit_policy: preimport.ControllerPolicy,
    project_root: Path = PROJECT_ROOT,
) -> Mapping[str, Any]:
    """Return a private-path-free, two-stage closure record.

    The function holds every discovered input simultaneously while hashing.
    It never creates an authorization, claim, output, directory, process, or
    Blender state.  A successful return is static evidence only.
    """

    root = project_root.resolve(strict=True)
    config_path = build_policy.by_role["config"].path
    _validate_policy_pair(
        build_policy,
        audit_policy,
        config_path=config_path,
    )
    project_expectations, config = _collect_project_expectations(
        project_root=root,
        config_path=config_path,
    )
    output_records, output_paths = _output_records(project_root=root, config=config)
    authorization_path = output_paths["one_run_authorization"]

    installed_expectations = {
        "blender_executable": build_policy.by_role["blender_executable"],
        "bundled_interpreter": build_policy.by_role["bundled_interpreter"],
    }
    if set(installed_expectations) != EXPECTED_INSTALLED_ROLES:
        raise CarrierTransactionClosureError("installed input role closure differs")

    inputs: list[ClosureInput] = []
    identities: set[tuple[int, int]] = set()
    held_fds: dict[str, int] = {}
    with ExitStack() as stack:
        for role, (path, expected_bytes, expected_sha256) in sorted(
            project_expectations.items()
        ):
            item, fd = _acquire_closure_input(
                role=role,
                scope="project",
                path=path,
                safe_relative_path=_relative_project_path(root, path),
                expected_bytes=expected_bytes,
                expected_sha256=expected_sha256,
            )
            stack.callback(os.close, fd)
            held_fds[role] = fd
            if (item.device, item.inode) in identities:
                raise CarrierTransactionClosureError("closure input file identity aliases")
            identities.add((item.device, item.inode))
            inputs.append(item)

        blender_root = installed_expectations["blender_executable"].path.parent.resolve(
            strict=True
        )
        for role, binding in sorted(installed_expectations.items()):
            path = binding.path.resolve(strict=True)
            try:
                relative = path.relative_to(blender_root).as_posix()
            except ValueError as exc:
                raise CarrierTransactionClosureError(
                    "installed artifact escapes the Blender installation"
                ) from exc
            item, fd = _acquire_closure_input(
                role=role,
                scope="blender_installation",
                path=path,
                safe_relative_path=relative,
                expected_bytes=None,
                expected_sha256=binding.sha256,
            )
            stack.callback(os.close, fd)
            held_fds[role] = fd
            if (item.device, item.inode) in identities:
                raise CarrierTransactionClosureError("closure input file identity aliases")
            identities.add((item.device, item.inode))
            inputs.append(item)

        if len(inputs) > MAX_CLOSURE_FILES:
            raise CarrierTransactionClosureError("closure input count exceeds the limit")
        for item in inputs:
            current = os.fstat(held_fds[item.role])
            if (
                int(current.st_dev),
                int(current.st_ino),
                int(current.st_size),
                int(getattr(current, "st_nlink", 1)),
            ) != (item.device, item.inode, item.bytes, item.link_count):
                raise CarrierTransactionClosureError(
                    "closure input identity changed while the complete set was held"
                )
        input_records = [item.safe_record() for item in sorted(inputs, key=lambda row: row.role)]
        if {record["role"] for record in input_records} != (
            EXPECTED_PROJECT_ROLES | EXPECTED_INSTALLED_ROLES
        ):
            raise CarrierTransactionClosureError("complete input role closure differs")

        build_command = _command_for_stage(
            policy=build_policy,
            authorization_path=authorization_path,
        )
        audit_command = _command_for_stage(
            policy=audit_policy,
            authorization_path=authorization_path,
        )
        if build_command == audit_command:
            raise CarrierTransactionClosureError("build and audit commands alias")

        record: dict[str, Any] = {
            "schema": CLOSURE_SCHEMA,
            "status": CLOSURE_STATUS,
            "candidate_id": config["candidate"]["candidate_id"],
            "native_provider_interface": native_contract.NATIVE_PROVIDER_INTERFACE,
            "native_provider_interface_is_single_launch_only": True,
            "native_transaction_interface_available": False,
            "two_stage_transaction_required": True,
            "input_count": len(input_records),
            "inputs": input_records,
            "input_closure_sha256": native_contract.canonical_sha256(input_records),
            "outputs": [output_records[role] for role in sorted(output_records)],
            "output_closure_sha256": native_contract.canonical_sha256(
                [output_records[role] for role in sorted(output_records)]
            ),
            "build_argv_sha256": native_contract.canonical_sha256(list(build_command)),
            "build_command_line_sha256": native_contract.windows_command_line_sha256(
                build_command
            ),
            "audit_argv_sha256": native_contract.canonical_sha256(list(audit_command)),
            "audit_command_line_sha256": native_contract.windows_command_line_sha256(
                audit_command
            ),
            "commands_share_exact_blender_config_and_authorization": True,
            "commands_use_distinct_bound_workers": True,
            "transaction_stages": list(TRANSACTION_STAGES),
            "authorization_present": output_paths["one_run_authorization"].is_file(),
            "all_reserved_outputs_absent": all(
                value["currently_absent"] for value in output_records.values()
            ),
            "native_claim_root_selected": False,
            "native_claim_created": False,
            "operating_system_handle_evidence_verified": False,
            "authority": {key: False for key in AUTHORITY_KEYS},
        }
        validate_static_transaction_closure_record(record)
        return MappingProxyType(record)

def validate_static_transaction_closure_record(record: Mapping[str, Any]) -> None:
    expected_keys = {
        "schema",
        "status",
        "candidate_id",
        "native_provider_interface",
        "native_provider_interface_is_single_launch_only",
        "native_transaction_interface_available",
        "two_stage_transaction_required",
        "input_count",
        "inputs",
        "input_closure_sha256",
        "outputs",
        "output_closure_sha256",
        "build_argv_sha256",
        "build_command_line_sha256",
        "audit_argv_sha256",
        "audit_command_line_sha256",
        "commands_share_exact_blender_config_and_authorization",
        "commands_use_distinct_bound_workers",
        "transaction_stages",
        "authorization_present",
        "all_reserved_outputs_absent",
        "native_claim_root_selected",
        "native_claim_created",
        "operating_system_handle_evidence_verified",
        "authority",
    }
    if set(record) != expected_keys:
        raise CarrierTransactionClosureError("closure record keys differ")
    if record.get("schema") != CLOSURE_SCHEMA or record.get("status") != CLOSURE_STATUS:
        raise CarrierTransactionClosureError("closure record identity differs")
    if record.get("native_provider_interface") != native_contract.NATIVE_PROVIDER_INTERFACE:
        raise CarrierTransactionClosureError("closure provider interface differs")
    required_true = (
        "native_provider_interface_is_single_launch_only",
        "two_stage_transaction_required",
        "commands_share_exact_blender_config_and_authorization",
        "commands_use_distinct_bound_workers",
    )
    for key in required_true:
        if record.get(key) is not True:
            raise CarrierTransactionClosureError(f"closure {key} must remain true")
    required_false = (
        "native_transaction_interface_available",
        "authorization_present",
        "native_claim_root_selected",
        "native_claim_created",
        "operating_system_handle_evidence_verified",
    )
    for key in required_false:
        if record.get(key) is not False:
            raise CarrierTransactionClosureError(f"closure {key} must remain false")
    if record.get("all_reserved_outputs_absent") is not True:
        raise CarrierTransactionClosureError("reserved outputs are not all absent")
    inputs = record.get("inputs")
    if type(inputs) is not list or len(inputs) != len(
        EXPECTED_PROJECT_ROLES | EXPECTED_INSTALLED_ROLES
    ):
        raise CarrierTransactionClosureError("closure input record count differs")
    if record.get("input_count") != len(inputs):
        raise CarrierTransactionClosureError("closure input_count differs")
    if {value.get("role") for value in inputs if isinstance(value, dict)} != (
        EXPECTED_PROJECT_ROLES | EXPECTED_INSTALLED_ROLES
    ):
        raise CarrierTransactionClosureError("closure input roles differ")
    for value in inputs:
        if type(value) is not dict or set(value) != {
            "role",
            "scope",
            "relative_path",
            "bytes",
            "sha256",
            "path_sha256",
            "canonical_path_sha256",
            "link_count",
        }:
            raise CarrierTransactionClosureError("closure input record shape differs")
        role = value["role"]
        expected_scope = (
            "project" if role in EXPECTED_PROJECT_ROLES else "blender_installation"
        )
        if value["scope"] != expected_scope:
            raise CarrierTransactionClosureError("closure input scope differs")
        relative = value["relative_path"]
        if (
            type(relative) is not str
            or not relative
            or "\\" in relative
            or relative.startswith("/")
            or ".." in PurePosixPath(relative).parts
        ):
            raise CarrierTransactionClosureError("closure input relative path differs")
        if type(value["bytes"]) is not int or value["bytes"] <= 0:
            raise CarrierTransactionClosureError("closure input byte count differs")
        if value["link_count"] != 1:
            raise CarrierTransactionClosureError("closure input link count differs")
        for digest_key in ("sha256", "path_sha256", "canonical_path_sha256"):
            digest = value[digest_key]
            if type(digest) is not str or preimport.SHA256_RE.fullmatch(digest) is None:
                raise CarrierTransactionClosureError(
                    f"closure input {digest_key} differs"
                )
    if record.get("input_closure_sha256") != native_contract.canonical_sha256(inputs):
        raise CarrierTransactionClosureError("closure input digest differs")
    outputs = record.get("outputs")
    if type(outputs) is not list or len(outputs) != len(EXPECTED_OUTPUT_ROLES):
        raise CarrierTransactionClosureError("closure outputs differ")
    if {value.get("role") for value in outputs if isinstance(value, dict)} != EXPECTED_OUTPUT_ROLES:
        raise CarrierTransactionClosureError("closure output roles differ")
    for value in outputs:
        if type(value) is not dict or set(value) != {
            "role",
            "relative_path",
            "path_sha256",
            "canonical_path_sha256",
            "must_be_create_new",
            "currently_absent",
        }:
            raise CarrierTransactionClosureError("closure output record shape differs")
        relative = value["relative_path"]
        if (
            type(relative) is not str
            or not relative
            or "\\" in relative
            or relative.startswith("/")
            or ".." in PurePosixPath(relative).parts
        ):
            raise CarrierTransactionClosureError("closure output relative path differs")
        if value["must_be_create_new"] is not True or value["currently_absent"] is not True:
            raise CarrierTransactionClosureError("closure output reservation differs")
        for digest_key in ("path_sha256", "canonical_path_sha256"):
            digest = value[digest_key]
            if type(digest) is not str or preimport.SHA256_RE.fullmatch(digest) is None:
                raise CarrierTransactionClosureError(
                    f"closure output {digest_key} differs"
                )
    if record.get("output_closure_sha256") != native_contract.canonical_sha256(outputs):
        raise CarrierTransactionClosureError("closure output digest differs")
    for key in (
        "input_closure_sha256",
        "output_closure_sha256",
        "build_argv_sha256",
        "build_command_line_sha256",
        "audit_argv_sha256",
        "audit_command_line_sha256",
    ):
        if type(record.get(key)) is not str or preimport.SHA256_RE.fullmatch(record[key]) is None:
            raise CarrierTransactionClosureError(f"closure {key} differs")
    if record["build_argv_sha256"] == record["audit_argv_sha256"]:
        raise CarrierTransactionClosureError("closure build and audit argv alias")
    if record.get("transaction_stages") != list(TRANSACTION_STAGES):
        raise CarrierTransactionClosureError("closure transaction stages differ")
    authority = record.get("authority")
    if type(authority) is not dict or set(authority) != set(AUTHORITY_KEYS):
        raise CarrierTransactionClosureError("closure authority shape differs")
    if any(value is not False for value in authority.values()):
        raise CarrierTransactionClosureError("closure authority must remain false")


def load_machine_static_transaction_closure() -> Mapping[str, Any]:
    """Validate the installed Blender and tracked carrier closure read-only."""

    return build_static_transaction_closure(
        build_policy=preimport.load_machine_policy(operation="build"),
        audit_policy=preimport.load_machine_policy(operation="audit"),
    )


__all__ = [
    "AUTHORITY_KEYS",
    "CLOSURE_SCHEMA",
    "CLOSURE_STATUS",
    "CarrierTransactionClosureError",
    "ClosureInput",
    "EXPECTED_INSTALLED_ROLES",
    "EXPECTED_OUTPUT_ROLES",
    "EXPECTED_PROJECT_ROLES",
    "TRANSACTION_STAGES",
    "build_static_transaction_closure",
    "load_machine_static_transaction_closure",
    "validate_static_transaction_closure_record",
]
