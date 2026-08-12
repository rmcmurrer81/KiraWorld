#!/usr/bin/env python3
from __future__ import annotations

"""Pure static controller-plan validator for semantic-cage Attempt 04.

This preparation intentionally contains no process launcher and no persistence
operation.  Direct execution always refuses.  A later append-only sealed
revision must bind real AFES-v3r3 evidence, pass a fresh independent audit, and
add the native execution step without changing this frozen source.
"""

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_semantic_control_cage_diagnostic_v4.json"
)
WRAPPER_RELATIVE_PATH = "tools/blender_diagnose_kira_r25_semantic_control_cage_v4.py"
STATIC_AUDIT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/"
    "attempt_04/INDEPENDENT_AUDIT.json"
)
OUTCOME_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/"
    "attempt_04/EXECUTION_OUTCOME.receipt.bin"
)
OUTPUT_RELATIVE_ROOT = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_execution/attempt_04"
)
PREPARATION_STATUS = "STATIC_PREPARATION_ONLY_V3R3_EVIDENCE_NOT_SEALED_EXECUTION_FORBIDDEN"
SEALED_STATUS = "SEALED_IN_APPEND_ONLY_SUCCESSOR_TO_INDEPENDENTLY_ACCEPTED_AFES_V3R3_PAIR"
HEX64 = re.compile(r"[0-9a-f]{64}")


class SemanticCageV4PlanError(RuntimeError):
    pass


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _project_file(relative: object) -> Path:
    if not isinstance(relative, str) or not relative:
        raise SemanticCageV4PlanError("path_not_text")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise SemanticCageV4PlanError("unsafe_project_relative_path")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise SemanticCageV4PlanError("symlink_binding_refused")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise SemanticCageV4PlanError("path_escaped_project_root") from exc
    if not resolved.is_file():
        raise SemanticCageV4PlanError("bound_file_missing")
    return resolved


def _exact_row(value: object, label: str) -> tuple[Path, bytes]:
    if not isinstance(value, Mapping) or not {"path", "bytes", "sha256"}.issubset(value):
        raise SemanticCageV4PlanError(f"{label}_row_shape")
    path = _project_file(value["path"])
    raw = path.read_bytes()
    if len(raw) != value["bytes"] or _sha256(raw) != value["sha256"]:
        raise SemanticCageV4PlanError(f"{label}_binding_drift")
    return path, raw


def _load_config(expected_sha256: str) -> tuple[dict[str, Any], bytes]:
    if HEX64.fullmatch(expected_sha256 or "") is None:
        raise SemanticCageV4PlanError("config_sha256_invalid")
    raw = _project_file(CONFIG_RELATIVE_PATH).read_bytes()
    if _sha256(raw) != expected_sha256:
        raise SemanticCageV4PlanError("config_sha256_mismatch")
    try:
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise SemanticCageV4PlanError("config_invalid_json") from exc
    if not isinstance(value, dict) or value.get("schema") != "kira.avatar.r25.semantic_control_cage_diagnostic.v4":
        raise SemanticCageV4PlanError("config_schema_drift")
    return value, raw


def _unresolved(value: object) -> bool:
    stack = [value]
    while stack:
        current = stack.pop()
        if current is None or (isinstance(current, str) and current.startswith("FINAL_")):
            return True
        if isinstance(current, Mapping):
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return False


def build_sealed_execution_plan(expected_config_sha256: str, accepted_audit_sha256: str) -> dict[str, object]:
    """Validate a future sealed successor and return data only; launch nothing."""

    config, raw = _load_config(expected_config_sha256)
    if config.get("status") == PREPARATION_STATUS:
        raise SemanticCageV4PlanError("static_v4_preparation_is_not_execution_authority")
    if config.get("status") != SEALED_STATUS:
        raise SemanticCageV4PlanError("sealed_successor_status_missing")
    pair = config.get("afes_v3r3_pair_binding")
    if not isinstance(pair, Mapping) or pair.get("seal_status") != "SEALED_FINAL_INDEPENDENTLY_ACCEPTED_V3R3_PAIR":
        raise SemanticCageV4PlanError("v3r3_pair_not_sealed")
    if pair.get("required_final_placeholders") or _unresolved(pair.get("expected_pair_and_analysis")):
        raise SemanticCageV4PlanError("unresolved_v3r3_evidence")
    if HEX64.fullmatch(accepted_audit_sha256 or "") is None:
        raise SemanticCageV4PlanError("accepted_audit_sha256_invalid")
    audit = config.get("future_independent_audit_gate")
    if not isinstance(audit, Mapping) or audit.get("path") != STATIC_AUDIT_RELATIVE_PATH:
        raise SemanticCageV4PlanError("independent_audit_path_drift")
    audit_path = _project_file(audit["path"])
    audit_raw = audit_path.read_bytes()
    if _sha256(audit_raw) != accepted_audit_sha256:
        raise SemanticCageV4PlanError("independent_audit_sha256_mismatch")
    bindings = config.get("bindings")
    if not isinstance(bindings, Mapping):
        raise SemanticCageV4PlanError("bindings_missing")
    for label, row in sorted(bindings.items()):
        _exact_row(row, label)
    for label in (
        "final_locked_pair_execution_contract_binding",
        "final_locked_pair_independent_audit_binding",
        "final_locked_pair_native_manifest_binding",
        "final_locked_pair_execution_outcome_binding",
        "final_run_01_receipt_binding", "final_run_02_receipt_binding",
    ):
        _exact_row(pair.get(label), label)
    if config.get("append_only_execution_paths") != {
        "independent_audit": STATIC_AUDIT_RELATIVE_PATH,
        "outcome_receipt": OUTCOME_RELATIVE_PATH,
        "evidence_root": OUTPUT_RELATIVE_ROOT,
        "all_paths_must_not_exist_before_reservation": True,
    }:
        raise SemanticCageV4PlanError("append_only_execution_paths_drift")
    return {
        "schema": "kira.avatar.r25.semantic_control_cage_execution_plan.v4",
        "config_path": CONFIG_RELATIVE_PATH,
        "config_bytes": len(raw),
        "config_sha256": expected_config_sha256,
        "accepted_independent_audit_sha256": accepted_audit_sha256,
        "input_frame_order": [
            pair["final_locked_pair_execution_outcome_binding"]["path"],
            pair["final_run_01_receipt_binding"]["path"],
            pair["final_run_02_receipt_binding"]["path"],
        ],
        "wrapper_command_template": [
            "<BOUND_BLENDER>", "--background", "--factory-startup", "--python",
            WRAPPER_RELATIVE_PATH, "--", "--config-sha256", expected_config_sha256,
            "--lock-handle", "<INHERITED_INPUT_PIPE>",
            "--result-handle", "<DISTINCT_INHERITED_RESULT_PIPE>",
        ],
        "outcome_relative_path": OUTCOME_RELATIVE_PATH,
        "evidence_relative_root": OUTPUT_RELATIVE_ROOT,
        "authority": "READ_ONLY_DIAGNOSTIC_ONLY_NO_BODY_OR_RUNTIME_AUTHORITY",
    }


def main() -> int:
    print(
        "R25 semantic-cage v4 is frozen static preparation only; direct execution "
        "is refused until a new append-only sealed successor and audit exist."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
