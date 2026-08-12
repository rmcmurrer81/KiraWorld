#!/usr/bin/env python3
"""Attempt-03 controller for two locked, read-only AFES-v5 extractions.

This module uses only Python's standard library.  Before any project source is
compiled, imported, or launched it acquires deny-write/delete handles for the
complete contract graph.  Exact retained bytes then bootstrap the accepted
AFES-v5 private loader.  Locks remain live through both children, comparison,
and the fresh after-snapshot.
"""

from __future__ import annotations

import argparse
import builtins
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time
from types import ModuleType
from typing import Any, Callable, Iterable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v3.json"
)
OUTPUT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution/attempt_03"
)
CONTROLLER_AUDIT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution_static_preparation/"
    "attempt_03/INDEPENDENT_AUDIT.md"
)
MAX_FRAME_BYTES = 1_048_628
MAX_STDOUT_BYTES = 4 * 1024 * 1024
MAX_STDERR_BYTES = 4 * 1024 * 1024
ENVIRONMENT_ALLOWLIST = (
    "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERNAME", "USERPROFILE",
    "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA", "APPDATA", "Path",
)
FORCED_ENVIRONMENT_RELATIVE = {
    "PYTHONNOUSERSITE": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "BLENDER_USER_CONFIG": "RecoverySprint/runtime_cache/r25_blender/user_config",
    "BLENDER_USER_SCRIPTS": "RecoverySprint/runtime_cache/r25_blender/user_scripts",
    "BLENDER_USER_DATAFILES": "RecoverySprint/runtime_cache/r25_blender/user_datafiles",
}
BLENDER_COMMAND_TEMPLATE = [
    "<BLENDER_EXECUTABLE>", "--background", "--factory-startup",
    "--disable-autoexec", "<FOUNDATION_BLEND>", "--python-exit-code", "1",
    "--python", "<EXECUTION_WRAPPER>", "--", "--result-handle",
    "<INHERITED_WIN32_PIPE_HANDLE>", "--execution-contract-sha256",
    "<EXPECTED_CONTRACT_SHA256>", "--pair-session-nonce",
    "<FRESH_PAIR_64_HEX_NONCE>", "--run-nonce",
    "<FRESH_RUN_64_HEX_NONCE>", "--run-number", "<ONE_OR_TWO>",
]
HEX64 = re.compile(r"[0-9a-f]{64}")
FILE_TYPE_PIPE = 3


class LockedPairV3Error(RuntimeError):
    """An exact static or bounded execution gate failed closed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_file(relative: object) -> Path:
    text = str(relative or "")
    candidate = Path(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts:
        raise LockedPairV3Error(f"unsafe_project_relative_path:{text}")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise LockedPairV3Error(f"symlink_path_refused:{text}")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise LockedPairV3Error(f"path_escaped_project_root:{text}") from exc
    if not resolved.is_file():
        raise LockedPairV3Error(f"bound_path_is_not_file:{text}")
    return resolved


def _row_path(label: str, row: Mapping[str, object]) -> Path:
    if label == "blender_executable":
        path = Path(str(row.get("path", ""))).resolve(strict=True)
        if not path.is_file():
            raise LockedPairV3Error("blender_binding_is_not_file")
        return path
    return _project_file(row.get("path"))


def _parse_object(value: bytes, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value.decode("utf-8-sig"))
    except Exception as exc:
        raise LockedPairV3Error(f"invalid_json:{label}") from exc
    if not isinstance(parsed, dict):
        raise LockedPairV3Error(f"json_root_not_object:{label}")
    return parsed


def _iter_contract_rows(contract: Mapping[str, Any]) -> Iterable[tuple[str, Mapping[str, object]]]:
    tables = [
        ("bindings", contract.get("bindings")),
        ("afes_v5_transitive_rows", contract.get("afes_v5_transitive_rows")),
        ("locked_pair_attempt_01_preservation", contract.get("locked_pair_attempt_01_preservation")),
        ("locked_pair_attempt_02_preservation", contract.get("locked_pair_attempt_02_preservation")),
    ]
    for table_name, table in tables:
        if not isinstance(table, Mapping) or not table:
            raise LockedPairV3Error(f"discovery_table_missing:{table_name}")
        if table_name == "afes_v5_transitive_rows":
            for nested_name, nested in table.items():
                if not isinstance(nested, Mapping) or not nested:
                    raise LockedPairV3Error(
                        f"discovery_nested_table_missing:{table_name}.{nested_name}"
                    )
                for label, row in nested.items():
                    if not isinstance(row, Mapping) or "path" not in row:
                        raise LockedPairV3Error(
                            f"discovery_row_invalid:{table_name}.{nested_name}.{label}"
                        )
                    yield f"{table_name}.{nested_name}.{label}", row
        else:
            for label, row in table.items():
                if not isinstance(row, Mapping) or "path" not in row:
                    raise LockedPairV3Error(f"discovery_row_invalid:{table_name}.{label}")
                yield f"{table_name}.{label}", row


def _untrusted_discovery(*, include_controller_audit: bool = False) -> tuple[Path, list[Path]]:
    """Discover path spellings only; no untrusted digest authorizes a byte."""

    contract_path = _project_file(CONTRACT_RELATIVE_PATH)
    contract = _parse_object(contract_path.read_bytes(), "discovery_contract")
    paths = [contract_path]
    for compound_label, row in _iter_contract_rows(contract):
        terminal = compound_label.rsplit(".", 1)[-1]
        paths.append(_row_path(terminal, row))
    if include_controller_audit:
        paths.append(_project_file(CONTROLLER_AUDIT_RELATIVE_PATH))
    return contract_path, sorted(
        set(path.resolve(strict=True) for path in paths),
        key=lambda value: str(value).casefold(),
    )


class WindowsReadLockSet:
    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 0x00000001
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x00000080

    def __init__(self) -> None:
        if os.name != "nt":
            raise LockedPairV3Error("locked Blender pair is Windows-only")
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
        ]
        self.kernel32.CreateFileW.restype = wintypes.HANDLE
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.handles: list[int] = []
        self.locked_paths: list[Path] = []
        self.active = False

    def add(self, path: Path) -> None:
        handle = self.kernel32.CreateFileW(
            str(path), self.GENERIC_READ, self.FILE_SHARE_READ, None,
            self.OPEN_EXISTING, self.FILE_ATTRIBUTE_NORMAL, None,
        )
        invalid = ctypes.c_void_p(-1).value
        if handle in (None, invalid):
            raise LockedPairV3Error(
                f"cannot_lock_bound_input:{path}:winerror={ctypes.get_last_error()}"
            )
        self.handles.append(int(handle))
        self.locked_paths.append(path.resolve(strict=True))

    def close(self) -> None:
        first_error: LockedPairV3Error | None = None
        while self.handles:
            handle = self.handles.pop()
            if not self.kernel32.CloseHandle(handle) and first_error is None:
                first_error = LockedPairV3Error(
                    f"input_lock_close_failed:winerror={ctypes.get_last_error()}"
                )
        self.active = False
        if first_error is not None:
            raise first_error

    def __enter__(self) -> "WindowsReadLockSet":
        self.active = True
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


def _with_complete_lock_set(
    paths: Iterable[Path], body: Callable[[Any], Any], *,
    lock_factory: Callable[[], Any] = WindowsReadLockSet,
) -> Any:
    """Invoke no verifier, compiler, importer, or launcher until every add succeeds."""

    with lock_factory() as locks:
        for path in paths:
            locks.add(path)
        return body(locks)


class LockedByteLedger:
    """Retain the single authoritative under-lock read of every input."""

    def __init__(self, locks: Any, paths: Iterable[Path]) -> None:
        exact = {Path(path).resolve(strict=True) for path in paths}
        observed = {
            Path(path).resolve(strict=True)
            for path in getattr(locks, "locked_paths", ())
        }
        if not getattr(locks, "active", False):
            raise LockedPairV3Error("ledger_refused_without_active_lock_set")
        if observed != exact:
            raise LockedPairV3Error("ledger_refused_without_complete_lock_set")
        self.allowed = exact
        self._values: dict[Path, bytes] = {}
        self._reads: dict[Path, int] = {}

    def read_path(self, path: Path) -> bytes:
        exact = Path(path).resolve(strict=True)
        if exact not in self.allowed:
            raise LockedPairV3Error(f"unlocked_path_read_refused:{exact}")
        if exact not in self._values:
            self._values[exact] = exact.read_bytes()
            self._reads[exact] = 1
        return self._values[exact]

    def read_exact(self, row: object, *, label: str = "bound_row") -> tuple[Path, bytes]:
        if not isinstance(row, Mapping) or set(row) != {"path", "bytes", "sha256"}:
            raise LockedPairV3Error(f"invalid_locked_binding:{label}")
        if type(row["bytes"]) is not int or row["bytes"] < 0:
            raise LockedPairV3Error(f"invalid_locked_binding_bytes:{label}")
        if not isinstance(row["sha256"], str) or HEX64.fullmatch(row["sha256"]) is None:
            raise LockedPairV3Error(f"invalid_locked_binding_sha256:{label}")
        path = _row_path(label.rsplit(".", 1)[-1], row)
        value = self.read_path(path)
        if len(value) != row["bytes"] or _sha256_bytes(value) != row["sha256"]:
            raise LockedPairV3Error(f"locked_binding_drift:{label}")
        return path, value

    def before_snapshot(self) -> dict[str, dict[str, object]]:
        if set(self._values) != self.allowed:
            raise LockedPairV3Error("before_snapshot_missing_locked_inputs")
        return {
            str(path): {
                "bytes": len(self._values[path]),
                "sha256": _sha256_bytes(self._values[path]),
                "authoritative_physical_reads": self._reads[path],
            }
            for path in sorted(self.allowed, key=lambda value: str(value).casefold())
        }


def _exact_scope() -> dict[str, bool]:
    return {
        "body_work_only": True,
        "read_only_blender_diagnostic": True,
        "blend_mutation_allowed": False,
        "blend_save_allowed": False,
        "render_allowed": False,
        "candidate_creation_allowed": False,
        "body_authoring_allowed": False,
        "runtime_activation_allowed": False,
        "assignment_allowed": False,
        "export_allowed": False,
        "publication_allowed": False,
    }


def _expected_process_contract() -> dict[str, object]:
    return {
        "factory_startup": True,
        "background": True,
        "autoexec_disabled": True,
        "python_exit_code": 1,
        "stdin": "DEVNULL",
        "restricted_environment": True,
        "least_handle_inheritance": True,
        "result_handle_must_be_win32_pipe": True,
        "concurrent_bounded_pipe_drain": True,
        "exactly_one_frame_and_eof": True,
        "maximum_frame_bytes": MAX_FRAME_BYTES,
        "maximum_stdout_bytes": MAX_STDOUT_BYTES,
        "maximum_stderr_bytes": MAX_STDERR_BYTES,
        "fresh_pair_64_hex_nonce": True,
        "fresh_distinct_run_64_hex_nonce_per_run": True,
        "process_timeout_seconds": 180,
        "windows_job_kill_on_close": True,
        "create_suspended_assign_job_then_resume": True,
        "terminate_exact_job_tree_on_timeout_or_output_limit": True,
        "project_modules_imported": False,
        "private_graph_load_only_after_locked_verification": True,
        "retained_exact_bytes_used_for_private_execution": True,
        "shell": False,
        "close_fds": True,
        "working_directory": ".",
        "environment_allowlist": list(ENVIRONMENT_ALLOWLIST),
        "forced_environment_relative_to_project": dict(FORCED_ENVIRONMENT_RELATIVE),
        "exact_command_template": list(BLENDER_COMMAND_TEMPLATE),
    }


def _expected_pair_contract() -> dict[str, bool]:
    return {
        "distinct_pair_and_run_nonces": True,
        "exact_authenticated_inner_payload_match": True,
        "exact_full_normalized_topology_digest_match": True,
        "compact_afes_evidence_validation": True,
        "all_bound_inputs_locked_before_verification": True,
        "all_bound_inputs_locked_through_after_snapshot": True,
        "all_bound_inputs_unchanged_after_pair": True,
        "each_raw_frame_persisted_append_only": True,
        "canonical_outcome_for_every_post_root_exception": True,
        "no_empty_orphan_root_on_reservation_failure": True,
        "fixed_root_second_use_is_rejected": True,
        "fresh_independent_audit_required_before_execution": True,
    }


def _expected_truth_boundary() -> dict[str, bool]:
    return {
        "pair_pass_would_only_satisfy_foundation_afes_plus_transition_vertex_set_audit": True,
        "semantic_cage_still_required": True,
        "positive_jacobian_and_intersection_fixtures_still_required": True,
        "body_authoring_not_granted": True,
        "candidate_not_created": True,
        "owner_review_not_implied": True,
        "runtime_authority_not_implied": True,
        "static_package_is_not_execution_authority_until_fresh_independent_audit": True,
    }


def _verify_everything_under_locks(
    *, expected_contract_sha256: str, contract_path: Path,
    expected_locked_paths: set[Path], locks: Any,
    accepted_controller_audit_sha256: str,
) -> tuple[dict[str, Any], list[Path], LockedByteLedger, dict[str, Any]]:
    ledger = LockedByteLedger(locks, expected_locked_paths)
    contract_bytes = ledger.read_path(contract_path)
    if _sha256_bytes(contract_bytes) != expected_contract_sha256:
        raise LockedPairV3Error("locked_contract_hash_mismatch")
    contract = _parse_object(contract_bytes, "locked_contract")
    if set(contract) != {
        "schema", "attempt_id", "status", "scope", "authorization_basis",
        "bindings", "afes_v5_transitive_rows", "afes_v5_exact_contract_sections",
        "accepted_afes_v5_audit", "locked_pair_attempt_01_preservation",
        "locked_pair_attempt_02_preservation", "process_contract",
        "controller_audit_gate",
        "required_fresh_run_count", "pair_acceptance", "append_only_output_root",
        "truth_boundary",
    }:
        raise LockedPairV3Error("locked_contract_top_level_schema_drift")
    if contract["schema"] != "kira.avatar.r25.foundation_afes_locked_pair_execution.v3":
        raise LockedPairV3Error("locked_contract_schema_drift")
    if contract["attempt_id"] != "attempt_03" or contract["status"] != (
        "PENDING_FRESH_INDEPENDENT_AUDIT_READ_ONLY_DIAGNOSTIC_PAIR_ONLY"
    ):
        raise LockedPairV3Error("locked_contract_identity_drift")
    if contract["scope"] != _exact_scope():
        raise LockedPairV3Error("locked_contract_scope_drift")
    if contract["authorization_basis"] != {
        "owner_requested_body_progress": True,
        "owner_authorized_blender_problem_repair": True,
        "bounded_operation": (
            "extract_existing_foundation_afes_and_two_transition_rings_without_mutation"
        ),
        "does_not_authorize_candidate_or_runtime_change": True,
        "fresh_independent_attempt03_audit_required_before_execution": True,
    }:
        raise LockedPairV3Error("locked_authorization_basis_drift")
    if contract["process_contract"] != _expected_process_contract():
        raise LockedPairV3Error("locked_process_contract_drift")
    if contract["required_fresh_run_count"] != 2 or contract["pair_acceptance"] != (
        _expected_pair_contract()
    ):
        raise LockedPairV3Error("locked_pair_acceptance_contract_drift")
    if contract["append_only_output_root"] != OUTPUT_RELATIVE_PATH:
        raise LockedPairV3Error("locked_output_root_drift")
    if contract["truth_boundary"] != _expected_truth_boundary():
        raise LockedPairV3Error("locked_truth_boundary_drift")

    bindings = contract["bindings"]
    required_bindings = {
        "blender_executable", "foundation_blend", "afes_v5_config",
        "afes_v5_private_loader", "afes_v5_extractor",
        "afes_v5_test", "afes_v5_checkpoint", "afes_v5_independent_audit",
        "canonical_receipt", "execution_wrapper", "parent_controller",
        "locked_pair_attempt01_contract", "locked_pair_attempt01_wrapper",
        "locked_pair_attempt01_controller", "locked_pair_attempt01_test",
        "locked_pair_attempt01_checkpoint",
        "locked_pair_attempt01_independent_audit",
        "locked_pair_attempt02_contract", "locked_pair_attempt02_wrapper",
        "locked_pair_attempt02_controller", "locked_pair_attempt02_test",
        "locked_pair_attempt02_checkpoint", "locked_pair_attempt02_supersession",
        "locked_pair_attempt03_rebase_plan",
    }
    if not isinstance(bindings, Mapping) or set(bindings) != required_bindings:
        raise LockedPairV3Error("locked_binding_table_drift")
    exact_paths: list[Path] = []
    for compound_label, row in _iter_contract_rows(contract):
        exact_paths.append(ledger.read_exact(row, label=compound_label)[0])
    exact_paths.append(contract_path)
    exact_paths.append(_project_file(CONTROLLER_AUDIT_RELATIVE_PATH))
    exact_paths = sorted(
        set(path.resolve(strict=True) for path in exact_paths),
        key=lambda value: str(value).casefold(),
    )
    if set(exact_paths) != expected_locked_paths:
        raise LockedPairV3Error("locked_path_set_differs_from_verified_binding_set")
    if _project_file(bindings["parent_controller"]["path"]) != Path(__file__).resolve(
        strict=True
    ):
        raise LockedPairV3Error("locked_controller_path_mismatch")

    _, v5_bytes = ledger.read_exact(bindings["afes_v5_config"], label="afes_v5_config")
    v5 = _parse_object(v5_bytes, "afes_v5_config")
    transitive = contract["afes_v5_transitive_rows"]
    if set(transitive) != {
        "bindings", "attempt_01_preservation", "attempt_02_preservation",
        "attempt_03_preservation", "attempt_04_preservation",
    }:
        raise LockedPairV3Error("afes_v5_transitive_table_drift")
    for table_name, table in transitive.items():
        if v5.get(table_name) != table:
            raise LockedPairV3Error(f"afes_v5_transitive_content_drift:{table_name}")
    observed_sections = {
        key: v5.get(key) for key in (
            "schema", "attempt_id", "status", "scope", "attempt_04_baseline_config",
            "private_exact_byte_execution_contract", "topology_sealing_contract",
            "truth_boundary",
        )
    }
    if observed_sections != contract["afes_v5_exact_contract_sections"]:
        raise LockedPairV3Error("afes_v5_exact_contract_sections_drift")
    accepted = contract["accepted_afes_v5_audit"]
    if accepted != {
        "decision": "ACCEPTED_FOR_STATIC_PREPARATION_ONLY",
        "audit_sha256": bindings["afes_v5_independent_audit"]["sha256"],
        "audit_required_again_for_locked_pair_attempt03": True,
    }:
        raise LockedPairV3Error("accepted_afes_v5_audit_binding_drift")
    gate = contract.get("controller_audit_gate")
    expected_gate = {
        "path": CONTROLLER_AUDIT_RELATIVE_PATH,
        "sha256_supplied_out_of_band": True,
        "decision_marker": (
            "Decision: **ACCEPTED FOR ONE BOUNDED READ-ONLY PAIR ONLY**"
        ),
        "must_bind_contract_controller_and_wrapper_hashes": True,
    }
    if gate != expected_gate:
        raise LockedPairV3Error("controller_audit_gate_drift")
    audit_path = _project_file(CONTROLLER_AUDIT_RELATIVE_PATH)
    audit_bytes = ledger.read_path(audit_path)
    if _sha256_bytes(audit_bytes) != accepted_controller_audit_sha256:
        raise LockedPairV3Error("controller_audit_hash_mismatch")
    try:
        audit_text = audit_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LockedPairV3Error("controller_audit_not_utf8") from exc
    required_audit_tokens = {
        expected_gate["decision_marker"], expected_contract_sha256,
        str(bindings["parent_controller"]["sha256"]),
        str(bindings["execution_wrapper"]["sha256"]),
    }
    if any(token not in audit_text for token in required_audit_tokens):
        raise LockedPairV3Error("controller_audit_does_not_bind_exact_graph")
    ledger.before_snapshot()
    return contract, exact_paths, ledger, v5


def _load_private_parent_graph(
    contract: Mapping[str, Any], v5: Mapping[str, Any], ledger: LockedByteLedger,
    pair_session_nonce: str,
) -> tuple[ModuleType, ModuleType]:
    """Compile exact retained v5 loader bytes; never import an ambient project module."""

    binding = contract["bindings"]["afes_v5_private_loader"]
    path, source = ledger.read_exact(binding, label="afes_v5_private_loader")
    real_import = builtins.__import__

    def guarded_import(
        name: str, globals: object = None, locals: object = None,
        fromlist: Sequence[str] = (), level: int = 0,
    ) -> object:
        if name == "tools" or name.startswith("tools.") or name == "dataclasses":
            raise LockedPairV3Error(f"ambient_security_import_forbidden:{name}")
        return real_import(name, globals, locals, fromlist, level)

    private = ModuleType(f"_kira_private_afes_v5_loader_locked_parent_{pair_session_nonce}")
    private.__file__ = str(path)
    private.__package__ = ""
    private.__spec__ = None
    private.__loader__ = None
    private_builtins = dict(vars(builtins))
    private_builtins["__import__"] = guarded_import
    private.__dict__["__builtins__"] = private_builtins
    try:
        exec(compile(source, str(path), "exec", dont_inherit=True), private.__dict__, private.__dict__)
    except Exception as exc:
        raise LockedPairV3Error(
            f"private_v5_loader_execution_failed:{type(exc).__name__}:{exc}"
        ) from exc
    if any(private is value for value in sys.modules.values()):
        raise LockedPairV3Error("private_v5_loader_entered_sys_modules")
    loader = getattr(private, "load_private_dependency_graph", None)
    if not callable(loader) or Path(loader.__code__.co_filename).resolve(strict=True) != path:
        raise LockedPairV3Error("private_v5_loader_symbol_drift")
    graph_rows = {
        key: v5["bindings"][key] for key in (
            "attempt_01_topology_core_execution_dependency",
            "attempt_02_hardening_core_execution_dependency",
            "attempt_03_hardening_core_execution_dependency",
            "canonical_receipt_helper",
        )
    }
    try:
        graph = loader(bindings=graph_rows, read_exact=ledger.read_exact)
    except Exception as exc:
        raise LockedPairV3Error(
            f"private_v5_dependency_graph_failed:{type(exc).__name__}:{exc}"
        ) from exc
    receipt = graph.get("canonical_receipt")
    attempt03 = graph.get("attempt03_core")
    if not isinstance(receipt, ModuleType) or not isinstance(attempt03, ModuleType):
        raise LockedPairV3Error("private_parent_graph_shape_drift")
    if any(receipt is value or attempt03 is value for value in sys.modules.values()):
        raise LockedPairV3Error("private_parent_graph_entered_sys_modules")
    if getattr(receipt, "MAX_RECEIPT_FRAME_BYTES", None) != MAX_FRAME_BYTES:
        raise LockedPairV3Error("private_receipt_frame_limit_drift")
    validator = getattr(attempt03, "validate_compact_afes_analysis", None)
    if not callable(validator):
        raise LockedPairV3Error("private_attempt03_validator_missing")
    return receipt, attempt03


def _restricted_environment() -> dict[str, str]:
    environment = {
        name: os.environ[name]
        for name in ENVIRONMENT_ALLOWLIST
        if os.environ.get(name)
    }
    for name, value in FORCED_ENVIRONMENT_RELATIVE.items():
        environment[name] = value if name.startswith("PYTHON") else str(PROJECT_ROOT / value)
    return environment


def _require_pipe_handle(raw_handle: int) -> None:
    if (
        os.name != "nt" or type(raw_handle) is not int
        or raw_handle <= 0 or raw_handle > (1 << 63) - 1
    ):
        raise LockedPairV3Error("result_handle_invalid")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetFileType.argtypes = [ctypes.c_void_p]
    kernel32.GetFileType.restype = ctypes.c_uint32
    if int(kernel32.GetFileType(ctypes.c_void_p(raw_handle))) != FILE_TYPE_PIPE:
        raise LockedPairV3Error("result_handle_is_not_pipe")


def _drain_bounded(
    stream: Any, limit: int, result: list[object],
    overflow_event: threading.Event | None = None,
) -> None:
    digest = hashlib.sha256()
    captured = bytearray()
    total = 0
    try:
        while True:
            block = stream.read(64 * 1024)
            if not block:
                break
            total += len(block)
            digest.update(block)
            if total > limit and overflow_event is not None:
                overflow_event.set()
            remaining = max(0, limit - len(captured))
            if remaining:
                captured.extend(block[:remaining])
        result.append({
            "captured": bytes(captured), "total_bytes": total,
            "sha256": digest.hexdigest(), "limit_bytes": limit,
            "overflow": total > limit,
        })
    except BaseException as exc:
        result.append(exc)


class _JobIoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
    )]


class _JobBasicLimit(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _JobExtendedLimit(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JobBasicLimit),
        ("IoInfo", _JobIoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class WindowsKillOnCloseJob:
    """Contain one controller-created Blender process tree."""

    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    JobObjectExtendedLimitInformation = 9

    def __init__(self) -> None:
        if os.name != "nt":
            raise LockedPairV3Error("job containment is Windows-only")
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
        self.kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        self.kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ]
        self.kernel32.SetInformationJobObject.restype = wintypes.BOOL
        self.kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        self.kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.kernel32.TerminateJobObject.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
        self.ntdll.NtResumeProcess.restype = ctypes.c_long
        self.handle = self.kernel32.CreateJobObjectW(None, None)
        if not self.handle:
            raise LockedPairV3Error(f"job_create_failed:{ctypes.get_last_error()}")
        info = _JobExtendedLimit()
        info.BasicLimitInformation.LimitFlags = self.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel32.SetInformationJobObject(
            self.handle, self.JobObjectExtendedLimitInformation,
            ctypes.byref(info), ctypes.sizeof(info),
        ):
            error = ctypes.get_last_error()
            self.kernel32.CloseHandle(self.handle)
            raise LockedPairV3Error(f"job_limit_failed:{error}")
        self.closed = False
        self.assigned_pid: int | None = None

    def assign_and_resume(self, process: subprocess.Popen[bytes]) -> None:
        process_handle = int(process._handle)  # type: ignore[attr-defined]
        if not self.kernel32.AssignProcessToJobObject(self.handle, process_handle):
            raise LockedPairV3Error(f"job_assignment_failed:{ctypes.get_last_error()}")
        self.assigned_pid = process.pid
        status = int(self.ntdll.NtResumeProcess(process_handle))
        if status < 0:
            raise LockedPairV3Error(f"suspended_process_resume_failed:{status}")

    def terminate_tree(self) -> None:
        if not self.closed and not self.kernel32.TerminateJobObject(self.handle, 1):
            raise LockedPairV3Error(f"job_termination_failed:{ctypes.get_last_error()}")

    def close(self) -> None:
        if self.closed:
            return
        if not self.kernel32.CloseHandle(self.handle):
            raise LockedPairV3Error(f"job_close_failed:{ctypes.get_last_error()}")
        self.closed = True


def _terminate_exact_child(
    process: subprocess.Popen[bytes], job: WindowsKillOnCloseJob,
) -> None:
    """Stop this controller's exact assigned job tree, never an ambient process."""

    if process.poll() is not None:
        return
    if job.assigned_pid == process.pid:
        job.terminate_tree()
    else:
        process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        if job.assigned_pid == process.pid:
            job.close()
        else:
            process.kill()
        process.wait(timeout=15)


def _wait_bounded_child(
    process: subprocess.Popen[bytes], job: WindowsKillOnCloseJob, *, timeout_seconds: int,
    overflow_event: threading.Event,
) -> str | None:
    deadline = time.monotonic() + timeout_seconds
    while process.poll() is None:
        if overflow_event.wait(timeout=0.05):
            _terminate_exact_child(process, job)
            return "bounded_stream_limit_exceeded"
        if time.monotonic() >= deadline:
            _terminate_exact_child(process, job)
            return "process_timeout"
    return None


def _write_exclusive_bytes(path: Path, data: bytes) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600
    )
    try:
        view = memoryview(data)
        total = 0
        while total < len(view):
            written = os.write(descriptor, view[total:])
            if written <= 0:
                raise LockedPairV3Error(f"exclusive_write_failed:{path.name}")
            total += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _snapshot_under_complete_locks(
    paths: Iterable[Path], locks: Any,
) -> dict[str, dict[str, object]]:
    exact_paths = [Path(path).resolve(strict=True) for path in paths]
    observed = {
        Path(path).resolve(strict=True)
        for path in getattr(locks, "locked_paths", ())
    }
    if not getattr(locks, "active", False):
        raise LockedPairV3Error("snapshot_refused_without_active_lock_set")
    if observed != set(exact_paths):
        raise LockedPairV3Error("snapshot_refused_without_complete_lock_set")
    return {
        str(path): {"bytes": path.stat().st_size, "sha256": _sha256_file(path)}
        for path in sorted(exact_paths, key=lambda value: str(value).casefold())
    }


def _validate_child_payload(
    *, payload: object, run_number: int, pair_session_nonce: str,
    run_nonce: str, result_handle: int, child_pid: int, parent_pid: int,
    contract_sha256: str, contract: Mapping[str, Any],
    v5: Mapping[str, Any], attempt03: ModuleType,
) -> tuple[Mapping[str, Any], str]:
    if not isinstance(payload, Mapping) or set(payload) != {
        "schema", "status", "execution_contract", "accepted_afes_v5_config",
        "accepted_afes_v5_extractor", "pair_session_nonce", "run_nonce",
        "run_number", "result_pipe_handle", "child_pid", "parent_pid",
        "inner_attempt05_payload", "truth_boundary",
    }:
        raise LockedPairV3Error(f"run_{run_number:02d}_payload_shape_mismatch")
    if payload["schema"] != "kira.avatar.r25.foundation_afes_locked_extraction_run.v3":
        raise LockedPairV3Error(f"run_{run_number:02d}_schema_mismatch")
    if payload["status"] != "READ_ONLY_EXTRACTION_COMPLETE_PENDING_PAIR_MATCH":
        raise LockedPairV3Error(f"run_{run_number:02d}_status_mismatch")
    identities = (
        payload["pair_session_nonce"] == pair_session_nonce,
        payload["run_nonce"] == run_nonce,
        payload["run_number"] == run_number,
        payload["result_pipe_handle"] == result_handle,
        payload["child_pid"] == child_pid,
        payload["parent_pid"] == parent_pid,
    )
    if not all(identities):
        raise LockedPairV3Error(f"run_{run_number:02d}_authenticated_identity_mismatch")
    observed_contract = payload["execution_contract"]
    if not isinstance(observed_contract, Mapping) or observed_contract.get("sha256") != (
        contract_sha256
    ) or observed_contract.get("path") != CONTRACT_RELATIVE_PATH:
        raise LockedPairV3Error(f"run_{run_number:02d}_contract_mismatch")
    if payload["accepted_afes_v5_config"] != contract["bindings"]["afes_v5_config"] or payload[
        "accepted_afes_v5_extractor"
    ] != contract["bindings"]["afes_v5_extractor"]:
        raise LockedPairV3Error(f"run_{run_number:02d}_accepted_graph_mismatch")
    inner = payload["inner_attempt05_payload"]
    if not isinstance(inner, Mapping) or inner.get("schema") != (
        "kira.avatar.r25.foundation_afes_transition_diagnostic.v5"
    ) or inner.get("status") != (
        "EXTRACTED_UNSEALED_REQUIRES_MATCHING_FRESH_LOCKED_RUN"
    ):
        raise LockedPairV3Error(f"run_{run_number:02d}_inner_status_mismatch")
    if inner.get("config_observed_unsealed_by_parent") != contract["bindings"]["afes_v5_config"]:
        raise LockedPairV3Error(f"run_{run_number:02d}_inner_config_mismatch")
    expected_graph = {
        key: v5["bindings"][key] for key in (
            "attempt_01_topology_core_execution_dependency",
            "attempt_02_hardening_core_execution_dependency",
            "attempt_03_hardening_core_execution_dependency",
            "canonical_receipt_helper",
        )
    }
    if inner.get("private_execution_dependencies") != expected_graph:
        raise LockedPairV3Error(f"run_{run_number:02d}_private_graph_mismatch")
    if inner.get("ambient_project_modules_consumed") != 0 or inner.get(
        "ambient_dataclasses_decorator_consumed"
    ) != 0 or inner.get("private_modules_inserted_into_sys_modules") != 0:
        raise LockedPairV3Error(f"run_{run_number:02d}_private_execution_truth_mismatch")
    analysis = inner.get("analysis")
    if not isinstance(analysis, Mapping):
        raise LockedPairV3Error(f"run_{run_number:02d}_analysis_missing")
    attempt03.validate_compact_afes_analysis(analysis)
    topology_sha256 = analysis["topology_structure"]["full_normalized_topology_sha256"]
    sealing = inner.get("topology_sealing")
    if not isinstance(sealing, Mapping) or sealing.get(
        "measured_full_normalized_topology_sha256"
    ) != topology_sha256 or sealing.get("this_receipt_alone_is_acceptance") is not False:
        raise LockedPairV3Error(f"run_{run_number:02d}_topology_sealing_mismatch")
    guards = inner.get("read_only_guards")
    if guards != {
        "blend_loaded_exactly": True, "blend_clean_before": True,
        "blend_clean_after": True, "data_block_inventory_unchanged": True,
        "operator_calls_by_this_extractor": 0, "edit_calls_by_this_extractor": 0,
        "persistence_calls_by_this_extractor": 0,
        "path_result_writes_by_this_extractor": 0,
    }:
        raise LockedPairV3Error(f"run_{run_number:02d}_read_only_guard_mismatch")
    return inner, str(topology_sha256)


def _run_child(
    *, contract: Mapping[str, Any], v5: Mapping[str, Any],
    contract_sha256: str, run_number: int, pair_session_nonce: str,
    run_nonce: str, evidence_root: Path,
    receipt: ModuleType, attempt03: ModuleType,
) -> tuple[Any, dict[str, Any]]:
    if os.name != "nt":
        raise LockedPairV3Error("locked Blender pair is Windows-only")
    import msvcrt

    bindings = contract["bindings"]
    blender = Path(str(bindings["blender_executable"]["path"])).resolve(strict=True)
    foundation = _project_file(bindings["foundation_blend"]["path"])
    wrapper = _project_file(bindings["execution_wrapper"]["path"])
    read_fd, write_fd = os.pipe()
    write_handle = int(msvcrt.get_osfhandle(write_fd))
    try:
        _require_pipe_handle(write_handle)
    except BaseException:
        os.close(read_fd)
        os.close(write_fd)
        raise
    os.set_inheritable(write_fd, True)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    startup.lpAttributeList = {"handle_list": [write_handle]}
    command = [
        str(blender), "--background", "--factory-startup", "--disable-autoexec",
        str(foundation), "--python-exit-code", "1", "--python", str(wrapper), "--",
        "--result-handle", str(write_handle),
        "--execution-contract-sha256", contract_sha256,
        "--pair-session-nonce", pair_session_nonce,
        "--run-nonce", run_nonce, "--run-number", str(run_number),
    ]
    if command != [
        str(blender), "--background", "--factory-startup", "--disable-autoexec",
        str(foundation), "--python-exit-code", "1", "--python", str(wrapper), "--",
        "--result-handle", str(write_handle),
        "--execution-contract-sha256", contract_sha256,
        "--pair-session-nonce", pair_session_nonce,
        "--run-nonce", run_nonce, "--run-number", str(run_number),
    ]:
        raise LockedPairV3Error("exact_command_construction_drift")

    overflow_event = threading.Event()
    frame_result: list[object] = []
    frame_stream = os.fdopen(read_fd, "rb", buffering=0, closefd=True)
    frame_thread = threading.Thread(
        target=_drain_bounded,
        args=(frame_stream, MAX_FRAME_BYTES, frame_result, overflow_event),
        daemon=True,
    )
    frame_thread.start()
    process: subprocess.Popen[bytes] | None = None
    job: WindowsKillOnCloseJob | None = None
    try:
        job = WindowsKillOnCloseJob()
        process = subprocess.Popen(
            command, cwd=str(PROJECT_ROOT), env=_restricted_environment(),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            startupinfo=startup,
            creationflags=(
                getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "CREATE_SUSPENDED", 0x00000004)
            ),
            close_fds=True, shell=False,
        )
        job.assign_and_resume(process)
    except BaseException:
        if process is not None and job is not None:
            try:
                _terminate_exact_child(process, job)
            finally:
                if not job.closed:
                    job.close()
        elif process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=15)
        elif job is not None and not job.closed:
            job.close()
        os.close(write_fd)
        frame_thread.join(timeout=15)
        frame_stream.close()
        raise
    else:
        os.close(write_fd)
    if process.stdout is None or process.stderr is None or job is None:
        if job is not None:
            _terminate_exact_child(process, job)
            job.close()
        raise LockedPairV3Error(f"run_{run_number:02d}_stdio_or_job_missing")
    stdout_result: list[object] = []
    stderr_result: list[object] = []
    stdout_thread = threading.Thread(
        target=_drain_bounded,
        args=(process.stdout, MAX_STDOUT_BYTES, stdout_result, overflow_event),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_drain_bounded,
        args=(process.stderr, MAX_STDERR_BYTES, stderr_result, overflow_event),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    termination_reason = _wait_bounded_child(
        process, job,
        timeout_seconds=int(contract["process_contract"]["process_timeout_seconds"]),
        overflow_event=overflow_event,
    )
    for thread in (frame_thread, stdout_thread, stderr_thread):
        thread.join(timeout=15)
    if any(thread.is_alive() for thread in (frame_thread, stdout_thread, stderr_thread)):
        _terminate_exact_child(process, job)
        job.close()
        raise LockedPairV3Error(f"run_{run_number:02d}_drain_thread_did_not_finish")
    job.close()
    for label, values in (
        ("frame", frame_result), ("stdout", stdout_result), ("stderr", stderr_result)
    ):
        if len(values) != 1 or isinstance(values[0], BaseException):
            raise LockedPairV3Error(f"run_{run_number:02d}_{label}_drain_failed")
    frame_info = frame_result[0]
    stdout_info = stdout_result[0]
    stderr_info = stderr_result[0]
    _write_exclusive_bytes(
        evidence_root / f"run_{run_number:02d}_stdout.log", stdout_info["captured"]
    )
    _write_exclusive_bytes(
        evidence_root / f"run_{run_number:02d}_stderr.log", stderr_info["captured"]
    )
    frame = frame_info["captured"]
    _write_exclusive_bytes(evidence_root / f"run_{run_number:02d}_raw_frame.bin", frame)
    if termination_reason == "process_timeout":
        raise LockedPairV3Error(f"run_{run_number:02d}_timed_out")
    if frame_info["overflow"]:
        raise LockedPairV3Error(f"run_{run_number:02d}_frame_limit_exceeded")
    if termination_reason == "bounded_stream_limit_exceeded" or stdout_info[
        "overflow"
    ] or stderr_info["overflow"]:
        raise LockedPairV3Error(
            f"run_{run_number:02d}_log_limit_exceeded:"
            f"stdout={stdout_info['total_bytes']}:stderr={stderr_info['total_bytes']}"
        )
    if process.returncode != 0:
        raise LockedPairV3Error(f"run_{run_number:02d}_blender_exit:{process.returncode}")
    decoded = receipt.decode_receipt_frame(frame)
    inner, topology_sha256 = _validate_child_payload(
        payload=decoded.payload, run_number=run_number,
        pair_session_nonce=pair_session_nonce, run_nonce=run_nonce,
        result_handle=write_handle, child_pid=process.pid, parent_pid=os.getpid(),
        contract_sha256=contract_sha256, contract=contract, v5=v5,
        attempt03=attempt03,
    )
    with receipt.WindowsExclusiveReceiptReservation.reserve(
        evidence_root / f"run_{run_number:02d}_receipt.bin"
    ) as reservation:
        reservation.accept_child_frame(frame)
    return decoded, {
        "run_number": run_number, "pair_session_nonce": pair_session_nonce,
        "run_nonce": run_nonce, "pid": process.pid, "parent_pid": os.getpid(),
        "result_pipe_handle": write_handle,
        "exit_code": process.returncode, "frame_bytes": len(frame),
        "frame_sha256": decoded.frame_sha256,
        "payload_sha256": decoded.payload_sha256,
        "inner_payload_sha256": _sha256_bytes(receipt.canonical_json_bytes(dict(inner))),
        "topology_sha256": topology_sha256,
        "stdout_bytes": stdout_info["total_bytes"], "stdout_sha256": stdout_info["sha256"],
        "stderr_bytes": stderr_info["total_bytes"], "stderr_sha256": stderr_info["sha256"],
        "process_tree_containment": "WINDOWS_JOB_KILL_ON_CLOSE",
    }


def _reserve_outcome_without_empty_orphan(
    output_root: Path, receipt: ModuleType,
) -> Any:
    output_root.mkdir(parents=False, exist_ok=False)
    try:
        return receipt.WindowsExclusiveReceiptReservation.reserve(
            output_root / "CONTROLLER_OUTCOME.receipt.bin"
        )
    except BaseException:
        try:
            output_root.rmdir()
        except OSError:
            pass
        raise


def run_pair(
    expected_contract_sha256: str, accepted_controller_audit_sha256: str,
) -> Path:
    for label, value in (
        ("expected_contract_sha256", expected_contract_sha256),
        ("accepted_controller_audit_sha256", accepted_controller_audit_sha256),
    ):
        if not isinstance(value, str) or HEX64.fullmatch(value) is None:
            raise LockedPairV3Error(f"{label}_must_be_64_lowercase_hex")
    contract_path, discovered_paths = _untrusted_discovery(
        include_controller_audit=True
    )
    expected_set = {path.resolve(strict=True) for path in discovered_paths}

    def locked_body(locks: Any) -> Path:
        observed = {
            Path(path).resolve(strict=True)
            for path in getattr(locks, "locked_paths", ())
        }
        if not getattr(locks, "active", False):
            raise LockedPairV3Error("lock_set_not_active_before_verification")
        if observed != expected_set:
            raise LockedPairV3Error("complete_lock_set_not_held_before_verification")
        contract, exact_paths, ledger, v5 = _verify_everything_under_locks(
            expected_contract_sha256=expected_contract_sha256,
            contract_path=contract_path,
            expected_locked_paths=expected_set,
            locks=locks,
            accepted_controller_audit_sha256=accepted_controller_audit_sha256,
        )
        before = ledger.before_snapshot()
        pair_session_nonce = secrets.token_hex(32)
        receipt, attempt03 = _load_private_parent_graph(
            contract, v5, ledger, pair_session_nonce
        )
        output_root = (PROJECT_ROOT / OUTPUT_RELATIVE_PATH).resolve()
        output_root.relative_to(PROJECT_ROOT.resolve(strict=True))
        output_root.parent.mkdir(parents=True, exist_ok=True)
        if not output_root.parent.is_dir():
            raise LockedPairV3Error("fixed_output_parent_unavailable")
        outcome = _reserve_outcome_without_empty_orphan(output_root, receipt)
        stage = "post_root_reservation"
        try:
            decoded_runs: list[Any] = []
            run_metadata: list[dict[str, Any]] = []
            run_nonces = [secrets.token_hex(32), secrets.token_hex(32)]
            if len({pair_session_nonce, *run_nonces}) != 3:
                raise LockedPairV3Error("fresh_nonce_collision")
            stage = "children"
            for run_number, run_nonce in enumerate(run_nonces, 1):
                decoded, metadata = _run_child(
                    contract=contract, v5=v5,
                    contract_sha256=expected_contract_sha256,
                    run_number=run_number,
                    pair_session_nonce=pair_session_nonce,
                    run_nonce=run_nonce,
                    evidence_root=output_root, receipt=receipt, attempt03=attempt03,
                )
                decoded_runs.append(decoded)
                run_metadata.append(metadata)
            stage = "pair_comparison"
            if run_metadata[0]["run_nonce"] == run_metadata[1]["run_nonce"]:
                raise LockedPairV3Error("fresh_run_nonces_not_distinct")
            first_inner = decoded_runs[0].payload["inner_attempt05_payload"]
            second_inner = decoded_runs[1].payload["inner_attempt05_payload"]
            if first_inner != second_inner:
                raise LockedPairV3Error("fresh_locked_inner_payloads_do_not_match")
            if run_metadata[0]["inner_payload_sha256"] != run_metadata[1]["inner_payload_sha256"]:
                raise LockedPairV3Error("authenticated_evidence_digests_do_not_match")
            if run_metadata[0]["topology_sha256"] != run_metadata[1]["topology_sha256"]:
                raise LockedPairV3Error("fresh_locked_topology_digests_do_not_match")
            stage = "locked_after_snapshot"
            after_raw = _snapshot_under_complete_locks(exact_paths, locks)
            before_comparable = {
                path: {"bytes": row["bytes"], "sha256": row["sha256"]}
                for path, row in before.items()
            }
            if before_comparable != after_raw:
                raise LockedPairV3Error("bound_input_changed_while_locks_held")
            summary = {
                "schema": "kira.avatar.r25.foundation_afes_locked_pair_acceptance.v3",
                "status": "AFES_AND_TRANSITION_RINGS_EXTRACTED_READ_ONLY_PAIR_MATCHED",
                "execution_contract_sha256": expected_contract_sha256,
                "accepted_controller_audit_sha256": accepted_controller_audit_sha256,
                "pair_session_nonce": pair_session_nonce,
                "execution_contract_bytes": len(ledger.read_path(contract_path)),
                "bound_inputs_unchanged_under_locks": True,
                "input_snapshot_sha256": _sha256_bytes(
                    receipt.canonical_json_bytes(before_comparable)
                ),
                "runs": run_metadata,
                "matching_inner_payload_sha256": run_metadata[0]["inner_payload_sha256"],
                "full_normalized_topology_sha256": run_metadata[0]["topology_sha256"],
                "truth_boundary": [
                    "READ_ONLY_DIAGNOSTIC_PAIR_ONLY",
                    "NO_BLEND_MUTATION_OR_SAVE",
                    "NO_RENDER_EXPORT_OR_PATH_RESULT",
                    "NO_BODY_CANDIDATE",
                    "NO_AUTHORING_OR_RUNTIME_AUTHORITY",
                ],
            }
            outcome.accept_child_frame(receipt.encode_receipt_frame(summary))
            outcome.close()
            return output_root
        except BaseException as exc:
            failure = {
                "schema": "kira.avatar.r25.foundation_afes_locked_pair_failure.v3",
                "status": "FAILED_APPEND_ONLY_NO_BODY_AUTHORITY",
                "stage": stage, "failure_type": type(exc).__name__,
                "failure": str(exc),
                "execution_contract_sha256": expected_contract_sha256,
                "accepted_controller_audit_sha256": accepted_controller_audit_sha256,
                "pair_session_nonce": pair_session_nonce,
            }
            try:
                outcome.accept_child_frame(receipt.encode_receipt_frame(failure))
            finally:
                outcome.close()
            raise

    return _with_complete_lock_set(discovered_paths, locked_body)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-contract-sha256", required=True)
    parser.add_argument("--accepted-controller-audit-sha256", required=True)
    return parser.parse_args()


def main() -> int:
    values = _arguments()
    try:
        run_pair(
            values.expected_contract_sha256,
            values.accepted_controller_audit_sha256,
        )
    except Exception as exc:
        print(
            f"R25_AFES_LOCKED_PAIR_V3_FAILED: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    print("R25_AFES_LOCKED_PAIR_V3_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
