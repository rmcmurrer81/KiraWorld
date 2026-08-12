#!/usr/bin/env python3
"""External trust-boundary launcher for R25 AFES locked pair Attempt 04.

This deliberately small launcher is the package's explicit trust root.  Python
has already begun executing it before it can lock/hash its own on-disk path, so
it does *not* claim cryptographic self-provenance.  A fresh independent auditor
must review and bind this exact file.  The launcher does close the controller
self-execution gap: it locks the complete declared graph, retains exact bytes,
verifies the structured audit, then compiles the locked controller bytes in a
private module.  The controller refuses direct execution.
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
import sys
from types import ModuleType
from typing import Any, Callable, Iterable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v4.json"
)
AUDIT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution_static_preparation/"
    "attempt_04/INDEPENDENT_AUDIT.json"
)
HEX64 = re.compile(r"[0-9a-f]{64}")
REQUIRED_MISSING_V2_PATHS = {
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask_preparation/"
    "KIRA_R23_CC0_AFES_EXPANDED_MASK_PREFLIGHT_CONFIG.json",
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask/preflight_attempt_04/PREFLIGHT.json",
    "Avatar/avatar_builder/workspaces/inactive_adult_female_foundations/"
    "generic_makehuman_adult_female_foundation_inactive_v1_20260801/"
    "ADULT_FOUNDATION_QUALIFICATION_RESULT.json",
    "Avatar/avatar_builder/workspaces/inactive_adult_female_foundations/"
    "generic_makehuman_adult_female_foundation_inactive_v1_20260801/"
    "INDEPENDENT_ADULT_FOUNDATION_TOPOLOGY_AUDIT_V2.json",
    "Avatar/avatar_builder/workspaces/inactive_adult_female_foundations/"
    "generic_makehuman_adult_female_foundation_inactive_v1_20260801/"
    "INDEPENDENT_ADULT_FEMALE_RELATIONSHIP_REVIEW_V2.json",
}


class LockedPairBootstrapV4Error(RuntimeError):
    """The external launch boundary failed closed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def _exact_typed_equal(observed: object, expected: object) -> bool:
    if type(observed) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(observed) == set(expected) and all(
            _exact_typed_equal(observed[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(observed) == len(expected) and all(
            _exact_typed_equal(left, right) for left, right in zip(observed, expected)
        )
    return observed == expected


def _project_file(relative: object) -> Path:
    text = str(relative or "")
    candidate = Path(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts:
        raise LockedPairBootstrapV4Error(f"unsafe_project_relative_path:{text}")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise LockedPairBootstrapV4Error(f"symlink_path_refused:{text}")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise LockedPairBootstrapV4Error(f"path_escaped_project_root:{text}") from exc
    if not resolved.is_file():
        raise LockedPairBootstrapV4Error(f"project_input_not_file:{text}")
    return resolved


def _row_path(label: str, row: Mapping[str, object]) -> Path:
    if label == "blender_executable":
        path = Path(str(row.get("path", ""))).resolve(strict=True)
        if not path.is_file():
            raise LockedPairBootstrapV4Error("blender_executable_not_file")
        return path
    return _project_file(row.get("path"))


def _parse_json(value: bytes, label: str) -> dict[str, Any]:
    def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, item in pairs:
            if key in result:
                raise LockedPairBootstrapV4Error(f"duplicate_json_key:{label}:{key}")
            result[key] = item
        return result

    def reject_constant(raw: str) -> object:
        raise LockedPairBootstrapV4Error(f"non_finite_json_value:{label}:{raw}")

    try:
        parsed = json.loads(
            value.decode("utf-8-sig"), object_pairs_hook=strict_object,
            parse_constant=reject_constant,
        )
    except LockedPairBootstrapV4Error:
        raise
    except Exception as exc:
        raise LockedPairBootstrapV4Error(f"invalid_json:{label}") from exc
    if not isinstance(parsed, dict):
        raise LockedPairBootstrapV4Error(f"json_root_not_object:{label}")
    return parsed


def _read_contract_untrusted() -> tuple[Path, dict[str, Any]]:
    path = _project_file(CONTRACT_RELATIVE_PATH)
    return path, _parse_json(path.read_bytes(), "untrusted_discovery_contract")


def _iter_declared_rows(contract: Mapping[str, Any]) -> Iterable[tuple[str, Mapping[str, object]]]:
    for table_name in ("execution_sources", "child_project_read_closure"):
        table = contract.get(table_name)
        if not isinstance(table, Mapping) or not table:
            raise LockedPairBootstrapV4Error(f"discovery_table_missing:{table_name}")
        for label, row in table.items():
            if not isinstance(row, Mapping):
                raise LockedPairBootstrapV4Error(f"discovery_row_invalid:{table_name}.{label}")
            yield str(label), row


def _untrusted_discovery(*, require_audit: bool) -> tuple[Path, list[Path]]:
    contract_path, contract = _read_contract_untrusted()
    paths = [contract_path]
    for label, row in _iter_declared_rows(contract):
        paths.append(_row_path(label, row))
    if require_audit:
        paths.append(_project_file(AUDIT_RELATIVE_PATH))
    return contract_path, sorted(
        {path.resolve(strict=True) for path in paths},
        key=lambda path: str(path).casefold(),
    )


class WindowsReadLockSet:
    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 0x00000001
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x00000080

    def __init__(self) -> None:
        if os.name != "nt":
            raise LockedPairBootstrapV4Error("locked_pair_is_windows_only")
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
            raise LockedPairBootstrapV4Error(
                f"cannot_lock_input:{path}:winerror={ctypes.get_last_error()}"
            )
        self.handles.append(int(handle))
        self.locked_paths.append(path.resolve(strict=True))

    def close(self) -> None:
        first: Exception | None = None
        while self.handles:
            handle = self.handles.pop()
            if not self.kernel32.CloseHandle(handle) and first is None:
                first = LockedPairBootstrapV4Error(
                    f"input_lock_close_failed:{ctypes.get_last_error()}"
                )
        self.active = False
        if first is not None:
            raise first

    def __enter__(self) -> "WindowsReadLockSet":
        self.active = True
        return self

    def __exit__(self, _type: Any, _value: Any, _traceback: Any) -> None:
        self.close()


class LockedByteLedger:
    """One authoritative retained read per path after all locks are held."""

    def __init__(self, locks: Any, paths: Iterable[Path]) -> None:
        allowed = {Path(path).resolve(strict=True) for path in paths}
        observed = {Path(path).resolve(strict=True) for path in locks.locked_paths}
        if not locks.active or observed != allowed:
            raise LockedPairBootstrapV4Error("ledger_requires_complete_active_lock_set")
        self.allowed = allowed
        self.values: dict[Path, bytes] = {}
        self.reads: dict[Path, int] = {}

    def read_path(self, path: Path) -> bytes:
        exact = Path(path).resolve(strict=True)
        if exact not in self.allowed:
            raise LockedPairBootstrapV4Error(f"unlocked_read_refused:{exact}")
        if exact not in self.values:
            self.values[exact] = exact.read_bytes()
            self.reads[exact] = 1
        return self.values[exact]

    def read_exact(self, row: object, *, label: str = "bound_row") -> tuple[Path, bytes]:
        if not isinstance(row, Mapping) or set(row) != {"path", "bytes", "sha256"}:
            raise LockedPairBootstrapV4Error(f"invalid_binding:{label}")
        if type(row["bytes"]) is not int or row["bytes"] < 0:
            raise LockedPairBootstrapV4Error(f"invalid_binding_bytes:{label}")
        if not isinstance(row["sha256"], str) or HEX64.fullmatch(row["sha256"]) is None:
            raise LockedPairBootstrapV4Error(f"invalid_binding_sha256:{label}")
        path = _row_path(label.rsplit(".", 1)[-1], row)
        value = self.read_path(path)
        if len(value) != row["bytes"] or _sha256_bytes(value) != row["sha256"]:
            raise LockedPairBootstrapV4Error(f"binding_drift:{label}")
        return path, value

    def complete_snapshot(self) -> dict[str, dict[str, object]]:
        if set(self.values) != self.allowed:
            missing = sorted(str(path) for path in self.allowed - set(self.values))
            raise LockedPairBootstrapV4Error(f"snapshot_missing_locked_values:{missing}")
        return {
            str(path): {
                "bytes": len(self.values[path]),
                "sha256": _sha256_bytes(self.values[path]),
            }
            for path in sorted(self.allowed, key=lambda path: str(path).casefold())
        }


def _collect_rows(table: object, label: str, rows: dict[str, dict[str, object]]) -> None:
    if not isinstance(table, Mapping) or not table:
        raise LockedPairBootstrapV4Error(f"recursive_table_missing:{label}")
    for row_label, row in table.items():
        if not isinstance(row, Mapping) or set(row) != {"path", "bytes", "sha256"}:
            raise LockedPairBootstrapV4Error(f"recursive_row_invalid:{label}.{row_label}")
        path = str(row["path"])
        normalized = {"path": path, "bytes": row["bytes"], "sha256": row["sha256"]}
        existing = rows.get(path)
        if existing is not None and existing != normalized:
            raise LockedPairBootstrapV4Error(f"recursive_duplicate_row_conflict:{path}")
        rows[path] = normalized


def _derive_recursive_child_rows(v5: Mapping[str, Any], ledger: LockedByteLedger) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    v5_path = CONTRACT_V5_PATH = (
        "Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_read_only_extraction_v5.json"
    )
    v5_file = _project_file(v5_path)
    v5_value = ledger.read_path(v5_file)
    rows[v5_path] = {
        "path": v5_path, "bytes": len(v5_value), "sha256": _sha256_bytes(v5_value),
    }
    for name in (
        "bindings", "attempt_01_preservation", "attempt_02_preservation",
        "attempt_03_preservation", "attempt_04_preservation",
    ):
        _collect_rows(v5.get(name), f"v5.{name}", rows)
    _, v4_bytes = ledger.read_exact(v5["attempt_04_baseline_config"], label="v4_config")
    v4 = _parse_json(v4_bytes, "v4_config")
    for name in (
        "bindings", "attempt_01_preservation", "attempt_02_preservation",
        "attempt_03_preservation",
    ):
        _collect_rows(v4.get(name), f"v4.{name}", rows)
    _, v3_bytes = ledger.read_exact(v4["attempt_03_baseline_config"], label="v3_config")
    v3 = _parse_json(v3_bytes, "v3_config")
    for name in ("bindings", "attempt_01_preservation", "attempt_02_preservation"):
        _collect_rows(v3.get(name), f"v3.{name}", rows)
    _, v2_bytes = ledger.read_exact(v3["attempt_02_baseline_config"], label="v2_config")
    v2 = _parse_json(v2_bytes, "v2_config")
    for name in ("bindings", "attempt_01_preservation"):
        _collect_rows(v2.get(name), f"v2.{name}", rows)
    return rows


def _expected_process_contract() -> dict[str, object]:
    return {
        "factory_startup": True,
        "background": True,
        "autoexec_disabled": True,
        "python_exit_code": 1,
        "stdin": "DEVNULL",
        "shell": False,
        "close_fds": True,
        "least_handle_inheritance": True,
        "result_handle_must_be_win32_pipe": True,
        "concurrent_bounded_pipe_drain": True,
        "exactly_one_frame_and_eof": True,
        "maximum_frame_bytes": 1_048_628,
        "maximum_stdout_bytes": 4 * 1024 * 1024,
        "maximum_stderr_bytes": 4 * 1024 * 1024,
        "process_timeout_seconds": 180,
        "windows_job_kill_on_close": True,
        "create_suspended_assign_job_start_drains_then_resume": True,
        "exception_safe_post_creation_finally_cleanup": True,
        "fresh_pair_64_hex_nonce": True,
        "fresh_distinct_run_64_hex_nonce_per_run": True,
        "environment_passthrough_if_present": [
            "SYSTEMROOT", "WINDIR", "USERNAME", "USERPROFILE", "HOMEDRIVE",
            "HOMEPATH", "LOCALAPPDATA", "APPDATA",
        ],
        "forced_environment": {
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        },
        "controlled_runtime_directories": {
            "TEMP": "RecoverySprint/runtime_cache/r25_blender_v4/temp",
            "TMP": "RecoverySprint/runtime_cache/r25_blender_v4/temp",
            "BLENDER_USER_CONFIG": "RecoverySprint/runtime_cache/r25_blender_v4/user_config",
            "BLENDER_USER_SCRIPTS": "RecoverySprint/runtime_cache/r25_blender_v4/user_scripts",
            "BLENDER_USER_DATAFILES": "RecoverySprint/runtime_cache/r25_blender_v4/user_datafiles",
        },
        "path_rule": "exact_blender_directory_then_system32_then_windows_directory",
        "working_directory": ".",
        "exact_command_template": [
            "<BLENDER_EXECUTABLE>", "--background", "--factory-startup",
            "--disable-autoexec", "<FOUNDATION_BLEND>", "--python-exit-code", "1",
            "--python", "<CHILD_WRAPPER>", "--", "--result-handle",
            "<INHERITED_WIN32_PIPE_HANDLE>", "--execution-contract-sha256",
            "<EXPECTED_CONTRACT_SHA256>", "--pair-session-nonce",
            "<FRESH_PAIR_64_HEX_NONCE>", "--run-nonce",
            "<FRESH_RUN_64_HEX_NONCE>", "--run-number", "<ONE_OR_TWO>",
        ],
    }


def _validate_exact_contract_sections(contract: Mapping[str, Any]) -> None:
    expected_top = {
        "schema", "attempt_id", "status", "scope", "authorization_basis",
        "execution_sources", "child_project_read_closure",
        "recursive_closure_contract", "process_contract", "audit_gate",
        "required_fresh_run_count", "pair_acceptance", "append_only_output_root",
        "preserved_rejected_attempt03", "runtime_dependency_truth", "truth_boundary",
    }
    if set(contract) != expected_top:
        raise LockedPairBootstrapV4Error("locked_contract_top_level_schema_mismatch")
    if not _exact_typed_equal(contract["scope"], {
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
    }):
        raise LockedPairBootstrapV4Error("locked_scope_mismatch")
    if not _exact_typed_equal(contract["authorization_basis"], {
        "owner_requested_body_progress": True,
        "owner_authorized_blender_problem_repair": True,
        "bounded_operation": "extract_existing_foundation_afes_and_two_transition_rings_without_mutation",
        "does_not_authorize_candidate_or_runtime_change": True,
        "fresh_independent_attempt04_audit_required_before_execution": True,
    }):
        raise LockedPairBootstrapV4Error("locked_authorization_basis_mismatch")
    if not isinstance(contract["execution_sources"], Mapping) or set(
        contract["execution_sources"]
    ) != {
        "external_bootstrap", "private_controller", "child_wrapper",
        "blender_executable", "static_hostile_test",
    }:
        raise LockedPairBootstrapV4Error("execution_source_table_mismatch")
    if not _exact_typed_equal(contract["process_contract"], _expected_process_contract()):
        raise LockedPairBootstrapV4Error("locked_process_contract_mismatch")
    if not _exact_typed_equal(contract["audit_gate"], {
        "path": AUDIT_RELATIVE_PATH,
        "sha256_supplied_out_of_band": True,
        "document_schema": "kira.avatar.r25.foundation_afes_locked_pair_independent_audit.v4",
        "authoritative_decision_code": "ACCEPTED_FOR_ONE_BOUNDED_READ_ONLY_PAIR_ONLY",
        "exact_key_and_value_schema_required": True,
        "extra_or_contradictory_decision_fields_rejected": True,
        "quoted_substrings_are_not_authority": True,
    }):
        raise LockedPairBootstrapV4Error("locked_audit_gate_mismatch")
    if contract["required_fresh_run_count"] != 2:
        raise LockedPairBootstrapV4Error("locked_run_count_mismatch")
    if not _exact_typed_equal(contract["pair_acceptance"], {
        "distinct_pair_and_run_nonces": True,
        "exact_authenticated_outer_and_inner_payload_schema": True,
        "exact_full_normalized_topology_digest_match": True,
        "compact_afes_evidence_validation": True,
        "complete_recursive_child_project_inputs_locked_before_verification": True,
        "all_declared_inputs_locked_through_after_snapshot": True,
        "all_declared_inputs_unchanged_after_pair": True,
        "each_raw_frame_and_log_created_exclusively": True,
        "fixed_root_second_use_is_rejected": True,
        "post_outcome_reservation_failures_attempt_canonical_failure_receipt": True,
        "abrupt_process_or_storage_failure_can_prevent_failure_receipt": True,
        "pre_reservation_failure_has_no_receipt": True,
        "fresh_independent_audit_required_before_execution": True,
    }):
        raise LockedPairBootstrapV4Error("locked_pair_acceptance_mismatch")
    if contract["append_only_output_root"] != (
        "RecoverySprint/continuation_20260809/"
        "kira_r25_foundation_afes_locked_pair_execution/attempt_04"
    ):
        raise LockedPairBootstrapV4Error("locked_output_root_mismatch")
    if not isinstance(contract["preserved_rejected_attempt03"], Mapping) or len(
        contract["preserved_rejected_attempt03"]
    ) != 10:
        raise LockedPairBootstrapV4Error("attempt03_preservation_table_mismatch")
    if not _exact_typed_equal(contract["runtime_dependency_truth"], {
        "complete_recursive_project_file_reads_of_bound_v5_extractor": True,
        "complete_recursive_project_file_count": 35,
        "blender_executable_locked_and_hashed": True,
        "controller_compiled_from_retained_locked_bytes": True,
        "structured_audit_parsed_before_private_controller_compile": True,
        "external_bootstrap_already_executing_bytes_cannot_self_prove": True,
        "external_bootstrap_is_explicit_independent_audit_trust_root": True,
        "windows_system_dlls_and_blender_bundled_dynamic_runtime_files_individually_sealed": False,
        "windows_system_dlls_and_blender_bundled_dynamic_runtime_files_are_platform_dependencies": True,
        "network_dependency_expected": False,
        "model_dependency_expected": False,
        "unlisted_project_file_read_authorized": False,
    }):
        raise LockedPairBootstrapV4Error("runtime_dependency_truth_mismatch")
    if not _exact_typed_equal(contract["truth_boundary"], {
        "pair_pass_would_only_satisfy_foundation_afes_plus_transition_vertex_set_audit": True,
        "semantic_cage_still_required": True,
        "positive_jacobian_and_intersection_fixtures_still_required": True,
        "body_authoring_not_granted": True,
        "candidate_not_created": True,
        "owner_review_not_implied": True,
        "runtime_authority_not_implied": True,
        "static_package_is_not_execution_authority_until_fresh_independent_audit": True,
        "attempts_01_02_03_and_v3r1_preserved": True,
    }):
        raise LockedPairBootstrapV4Error("locked_truth_boundary_mismatch")


def _validate_structured_audit(
    *, audit_bytes: bytes, contract: Mapping[str, Any],
    expected_contract_sha256: str, retained_contract_bytes: bytes,
) -> dict[str, Any]:
    audit = _parse_json(audit_bytes, "independent_audit")
    if set(audit) != {
        "schema", "attempt_id", "decision", "reviewed_execution_artifacts",
        "recursive_closure_sha256", "truth_boundary",
    }:
        raise LockedPairBootstrapV4Error("audit_top_level_schema_mismatch")
    if audit["schema"] != "kira.avatar.r25.foundation_afes_locked_pair_independent_audit.v4":
        raise LockedPairBootstrapV4Error("audit_schema_mismatch")
    if audit["attempt_id"] != "attempt_04":
        raise LockedPairBootstrapV4Error("audit_attempt_mismatch")
    if not _exact_typed_equal(audit["decision"], {
        "accepted": True,
        "code": "ACCEPTED_FOR_ONE_BOUNDED_READ_ONLY_PAIR_ONLY",
        "scope": "ONE_FRESH_LOCKED_AFES_DIAGNOSTIC_PAIR",
    }):
        raise LockedPairBootstrapV4Error("audit_authoritative_decision_not_acceptance")
    expected_artifacts = {
        "contract": {
            "path": CONTRACT_RELATIVE_PATH,
            "bytes": len(retained_contract_bytes),
            "sha256": expected_contract_sha256,
        },
        "external_bootstrap": contract["execution_sources"]["external_bootstrap"],
        "private_controller": contract["execution_sources"]["private_controller"],
        "child_wrapper": contract["execution_sources"]["child_wrapper"],
        "static_hostile_test": contract["execution_sources"]["static_hostile_test"],
        "blender_executable": contract["execution_sources"]["blender_executable"],
    }
    if _sha256_bytes(retained_contract_bytes) != expected_contract_sha256:
        raise LockedPairBootstrapV4Error("audit_contract_bytes_changed")
    if not _exact_typed_equal(audit["reviewed_execution_artifacts"], expected_artifacts):
        raise LockedPairBootstrapV4Error("audit_artifact_binding_mismatch")
    if audit["recursive_closure_sha256"] != contract[
        "recursive_closure_contract"
    ]["canonical_closure_sha256"]:
        raise LockedPairBootstrapV4Error("audit_recursive_closure_binding_mismatch")
    if not _exact_typed_equal(audit["truth_boundary"], {
        "body_authoring_authorized": False,
        "one_bounded_pair_authorized": True,
        "owner_body_approval": False,
        "static_review_did_not_run_blender": True,
    }):
        raise LockedPairBootstrapV4Error("audit_truth_boundary_mismatch")
    return audit


def _verify_locked_graph(
    *, contract_path: Path, ledger: LockedByteLedger,
    expected_contract_sha256: str, accepted_audit_sha256: str,
) -> tuple[dict[str, Any], dict[str, dict[str, object]]]:
    contract_bytes = ledger.read_path(contract_path)
    if _sha256_bytes(contract_bytes) != expected_contract_sha256:
        raise LockedPairBootstrapV4Error("locked_contract_digest_mismatch")
    contract = _parse_json(contract_bytes, "locked_contract")
    if contract.get("schema") != "kira.avatar.r25.foundation_afes_locked_pair_execution.v4":
        raise LockedPairBootstrapV4Error("locked_contract_schema_mismatch")
    if contract.get("attempt_id") != "attempt_04" or contract.get("status") != (
        "PENDING_FRESH_INDEPENDENT_AUDIT_READ_ONLY_DIAGNOSTIC_PAIR_ONLY"
    ):
        raise LockedPairBootstrapV4Error("locked_contract_identity_mismatch")
    _validate_exact_contract_sections(contract)
    for label, row in _iter_declared_rows(contract):
        path, _ = ledger.read_exact(row, label=label)
        if label == "external_bootstrap" and path != Path(__file__).resolve(strict=True):
            raise LockedPairBootstrapV4Error("external_bootstrap_path_mismatch")
    closure = contract["child_project_read_closure"]
    if len(closure) != 35:
        raise LockedPairBootstrapV4Error("declared_child_closure_count_mismatch")
    _, v5_bytes = ledger.read_exact(closure["afes_v5_config"], label="afes_v5_config")
    v5 = _parse_json(v5_bytes, "afes_v5_config")
    derived = _derive_recursive_child_rows(v5, ledger)
    declared_by_path = {str(row["path"]): dict(row) for row in closure.values()}
    if len(declared_by_path) != len(closure) or declared_by_path != derived:
        raise LockedPairBootstrapV4Error("recursive_child_read_closure_mismatch")
    if not REQUIRED_MISSING_V2_PATHS.issubset(declared_by_path):
        raise LockedPairBootstrapV4Error("five_previously_missing_v2_inputs_absent")
    expected_closure_hash = _sha256_bytes(_canonical_json_bytes(declared_by_path))
    closure_contract = contract.get("recursive_closure_contract")
    if closure_contract != {
        "algorithm": "explicit_v5_v4_v3_v2_table_walk_matching_bound_v5_extractor",
        "unique_project_file_count": 35,
        "canonical_closure_sha256": expected_closure_hash,
        "includes_all_five_attempt03_audit_omissions": True,
        "verified_under_complete_parent_lock_set": True,
    }:
        raise LockedPairBootstrapV4Error("recursive_closure_contract_mismatch")
    audit_path = _project_file(AUDIT_RELATIVE_PATH)
    audit_bytes = ledger.read_path(audit_path)
    if _sha256_bytes(audit_bytes) != accepted_audit_sha256:
        raise LockedPairBootstrapV4Error("independent_audit_digest_mismatch")
    _validate_structured_audit(
        audit_bytes=audit_bytes, contract=contract,
        expected_contract_sha256=expected_contract_sha256,
        retained_contract_bytes=contract_bytes,
    )
    return contract, declared_by_path


class BootstrapContext:
    def __init__(
        self, *, locks: Any, ledger: LockedByteLedger, contract: dict[str, Any],
        contract_path: Path, expected_contract_sha256: str,
        accepted_audit_sha256: str,
    ) -> None:
        self._locks = locks
        self.ledger = ledger
        self.contract = contract
        self.contract_path = contract_path
        self.expected_contract_sha256 = expected_contract_sha256
        self.accepted_audit_sha256 = accepted_audit_sha256
        self.controller_private_execution = True
        self.external_bootstrap_provenance_truth = (
            "trusted_by_fresh_independent_static_review; cannot self-prove already "
            "executing launcher bytes"
        )
        self.before_snapshot = ledger.complete_snapshot()

    @property
    def locks_active(self) -> bool:
        return bool(self._locks.active)

    def snapshot_locked_files(self) -> dict[str, dict[str, object]]:
        if not self._locks.active:
            raise LockedPairBootstrapV4Error("snapshot_without_active_locks")
        observed = {Path(path).resolve(strict=True) for path in self._locks.locked_paths}
        if observed != self.ledger.allowed:
            raise LockedPairBootstrapV4Error("snapshot_without_complete_lock_set")
        return {
            str(path): {"bytes": path.stat().st_size, "sha256": _sha256_file(path)}
            for path in sorted(observed, key=lambda path: str(path).casefold())
        }


def _load_private_controller(
    contract: Mapping[str, Any], ledger: LockedByteLedger,
) -> ModuleType:
    row = contract["execution_sources"]["private_controller"]
    path, source = ledger.read_exact(row, label="private_controller")
    real_import = builtins.__import__

    def guarded_import(
        name: str, globals: object = None, locals: object = None,
        fromlist: Sequence[str] = (), level: int = 0,
    ) -> object:
        if name == "tools" or name.startswith("tools."):
            raise LockedPairBootstrapV4Error(f"ambient_project_import_forbidden:{name}")
        return real_import(name, globals, locals, fromlist, level)

    private = ModuleType("_kira_private_afes_locked_pair_controller_v4")
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
        raise LockedPairBootstrapV4Error(
            f"private_controller_execution_failed:{type(exc).__name__}:{exc}"
        ) from exc
    if any(private is module for module in sys.modules.values()):
        raise LockedPairBootstrapV4Error("private_controller_entered_sys_modules")
    entry = getattr(private, "run_locked_pair", None)
    if not callable(entry) or Path(entry.__code__.co_filename).resolve(strict=True) != path:
        raise LockedPairBootstrapV4Error("private_controller_entrypoint_drift")
    return private


def _with_complete_locks(
    paths: Iterable[Path], body: Callable[[Any], Any],
    *, lock_factory: Callable[[], Any] = WindowsReadLockSet,
) -> Any:
    with lock_factory() as locks:
        for path in paths:
            locks.add(path)
        return body(locks)


def launch_pair(expected_contract_sha256: str, accepted_audit_sha256: str) -> Path:
    for label, value in (
        ("expected_contract_sha256", expected_contract_sha256),
        ("accepted_audit_sha256", accepted_audit_sha256),
    ):
        if not isinstance(value, str) or HEX64.fullmatch(value) is None:
            raise LockedPairBootstrapV4Error(f"{label}_must_be_64_lowercase_hex")
    contract_path, paths = _untrusted_discovery(require_audit=True)
    expected = {path.resolve(strict=True) for path in paths}

    def locked_body(locks: Any) -> Path:
        observed = {Path(path).resolve(strict=True) for path in locks.locked_paths}
        if not locks.active or observed != expected:
            raise LockedPairBootstrapV4Error("complete_lock_set_not_held")
        ledger = LockedByteLedger(locks, expected)
        contract, _closure = _verify_locked_graph(
            contract_path=contract_path, ledger=ledger,
            expected_contract_sha256=expected_contract_sha256,
            accepted_audit_sha256=accepted_audit_sha256,
        )
        # Read every locked path exactly once before private compilation.
        for path in sorted(expected, key=lambda path: str(path).casefold()):
            ledger.read_path(path)
        context = BootstrapContext(
            locks=locks, ledger=ledger, contract=contract,
            contract_path=contract_path,
            expected_contract_sha256=expected_contract_sha256,
            accepted_audit_sha256=accepted_audit_sha256,
        )
        controller = _load_private_controller(contract, ledger)
        return controller.run_locked_pair(
            bootstrap_context=context,
            expected_contract_sha256=expected_contract_sha256,
            accepted_audit_sha256=accepted_audit_sha256,
        )

    return _with_complete_locks(paths, locked_body)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-contract-sha256", required=True)
    parser.add_argument("--accepted-audit-sha256", required=True)
    return parser.parse_args()


def main() -> int:
    values = _arguments()
    try:
        launch_pair(values.expected_contract_sha256, values.accepted_audit_sha256)
    except Exception as exc:
        print(
            f"R25_AFES_LOCKED_PAIR_V4_FAILED:{type(exc).__name__}:{exc}",
            file=sys.stderr,
        )
        return 1
    print("R25_AFES_LOCKED_PAIR_V4_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
