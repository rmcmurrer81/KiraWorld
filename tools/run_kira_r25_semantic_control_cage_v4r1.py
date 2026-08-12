#!/usr/bin/env python3
from __future__ import annotations

"""Static-only controller-plan validator for semantic-cage Attempt 04r1.

There is no process, pipe, Blender, or persistence implementation here.
Direct invocation refuses.  The pure plan path nevertheless exact-parses the
future canonical independent audit and specifies the mandatory one-read
controller-owned capability that a later append-only sealed successor needs.
"""

import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_semantic_control_cage_diagnostic_v4r1.json"
)
WRAPPER_RELATIVE_PATH = "tools/blender_diagnose_kira_r25_semantic_control_cage_v4r1.py"
AUDIT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/"
    "attempt_04r1/INDEPENDENT_AUDIT.json"
)
OUTCOME_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/"
    "attempt_04r1/EXECUTION_OUTCOME.receipt.bin"
)
OUTPUT_RELATIVE_ROOT = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_execution/attempt_04r1"
)
PREPARATION_STATUS = "STATIC_PREPARATION_ONLY_ATTEMPT04_REPAIRS_UNSEALED_EXECUTION_FORBIDDEN"
SEALED_STATUS = "SEALED_ONLY_IN_NEW_APPEND_ONLY_SUCCESSOR_AFTER_ACCEPTED_04R1_AUDIT"
AUDIT_SCHEMA = "kira.avatar.r25.semantic_control_cage_independent_audit.v4r1"
AUDIT_DECISION = {
    "status": "ACCEPTED_STATIC_UNSEALED",
    "current_preparation_execution_authorized": False,
    "new_append_only_sealed_successor_plan_permitted": True,
}
AUDITOR_IDENTITY = {
    "independent_of_attempt04r1_authorship": True,
    "did_not_run_blender_afes_or_semantic_controller": True,
    "did_not_create_result_outcome_or_evidence": True,
}
AUDIT_TRUTH = [
    "STATIC_ACCEPTANCE_IS_NOT_EXECUTION_AUTHORITY",
    "ALL_04R1_SUBJECTS_HASH_BOUND",
    "ATTEMPT04_REJECTION_PRESERVED",
    "ONLY_NEW_APPEND_ONLY_SEALED_SUCCESSOR_MAY_PROCEED",
]
AUDIT_KEYS = {
    "schema", "authoritative_decision", "auditor", "subject_manifest",
    "findings", "truth_boundary",
}
SUBJECT_PATHS = {
    "attempt04r1_config": CONFIG_RELATIVE_PATH,
    "attempt04r1_adapter": "tools/kira_r25_semantic_control_cage_afes_v3r3_adapter_v4r1.py",
    "attempt04r1_wrapper": WRAPPER_RELATIVE_PATH,
    "attempt04r1_controller": "tools/run_kira_r25_semantic_control_cage_v4r1.py",
    "attempt04r1_test": "Testing/test_kira_r25_semantic_control_cage_attempt04r1.py",
    "attempt04r1_checkpoint": (
        "RecoverySprint/continuation_20260809/"
        "kira_r25_semantic_cage_correspondence_static_preparation/attempt_04r1/CHECKPOINT.md"
    ),
    "attempt04_rejection_audit": (
        "RecoverySprint/continuation_20260809/"
        "kira_r25_semantic_cage_correspondence_static_preparation/attempt_04/INDEPENDENT_AUDIT.md"
    ),
}
CAPABILITY_SCHEMA = "kira.avatar.r25.semantic_control_cage_execution_capability.v4r1"
CAPABILITY_STATUS = "INDEPENDENT_AUDIT_ACCEPTED_ONE_RUN_CAPABILITY"


class SemanticCageV4R1PlanError(RuntimeError):
    pass


class _DuplicateKey(ValueError):
    pass


def _sha256(value):
    return hashlib.sha256(value).hexdigest()


def _hex64(value):
    if type(value) is not str or len(value) != 64:
        return False
    for character in value:
        if not ("0" <= character <= "9" or "a" <= character <= "f"):
            return False
    return True


def _project_file(relative):
    if type(relative) is not str or not relative:
        raise SemanticCageV4R1PlanError("path_not_text")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise SemanticCageV4R1PlanError("unsafe_project_relative_path")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise SemanticCageV4R1PlanError("symlink_binding_refused")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise SemanticCageV4R1PlanError("path_escaped_project_root") from exc
    if not resolved.is_file():
        raise SemanticCageV4R1PlanError("bound_file_missing")
    return resolved


def _row_for(relative):
    path = _project_file(relative)
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "sha256": _sha256(raw)}


def _exact_row(value, expected_path, label):
    if type(value) is not dict or set(value) != {"path", "bytes", "sha256"}:
        raise SemanticCageV4R1PlanError(label + "_row_shape")
    if value["path"] != expected_path or type(value["bytes"]) is not int or value["bytes"] <= 0 or not _hex64(value["sha256"]):
        raise SemanticCageV4R1PlanError(label + "_row_value")
    actual = _row_for(expected_path)
    if value != actual:
        raise SemanticCageV4R1PlanError(label + "_subject_hash_drift")
    return actual


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("nonfinite_constant:" + value)


def _canonical_json_bytes(value):
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _parse_canonical_object(raw, label):
    if type(raw) is not bytes or len(raw) == 0 or len(raw) > 1024 * 1024:
        raise SemanticCageV4R1PlanError(label + "_byte_length")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text, object_pairs_hook=_unique_object, parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise SemanticCageV4R1PlanError(label + "_duplicate_key:" + str(exc)) from exc
    except Exception as exc:
        raise SemanticCageV4R1PlanError(label + "_invalid_json") from exc
    if type(value) is not dict or _canonical_json_bytes(value) != raw:
        raise SemanticCageV4R1PlanError(label + "_not_canonical_object")
    return value


def _parse_independent_audit(audit_raw, expected_audit_sha256, expected_config_sha256, config):
    if not _hex64(expected_audit_sha256) or _sha256(audit_raw) != expected_audit_sha256:
        raise SemanticCageV4R1PlanError("independent_audit_sha256_mismatch")
    audit = _parse_canonical_object(audit_raw, "independent_audit")
    if set(audit) != AUDIT_KEYS or audit["schema"] != AUDIT_SCHEMA:
        raise SemanticCageV4R1PlanError("independent_audit_schema_or_shape_drift")
    if audit["authoritative_decision"] != AUDIT_DECISION:
        raise SemanticCageV4R1PlanError("independent_audit_decision_not_accepted")
    if audit["auditor"] != AUDITOR_IDENTITY:
        raise SemanticCageV4R1PlanError("independent_auditor_identity_drift")
    if audit["findings"] != {"blocking": []} or audit["truth_boundary"] != AUDIT_TRUTH:
        raise SemanticCageV4R1PlanError("independent_audit_findings_or_truth_drift")
    manifest = audit["subject_manifest"]
    if type(manifest) is not dict or set(manifest) != set(SUBJECT_PATHS):
        raise SemanticCageV4R1PlanError("independent_audit_subject_manifest_shape")
    for label, relative in SUBJECT_PATHS.items():
        _exact_row(manifest[label], relative, label)
    if manifest["attempt04r1_config"]["sha256"] != expected_config_sha256:
        raise SemanticCageV4R1PlanError("independent_audit_sealed_config_digest_mismatch")
    gate = config.get("future_independent_audit_gate")
    if type(gate) is not dict or gate.get("schema") != AUDIT_SCHEMA or gate.get("required_decision") != AUDIT_DECISION:
        raise SemanticCageV4R1PlanError("configured_audit_gate_protocol_drift")
    if gate.get("must_bind_exact_subject_labels") != sorted(SUBJECT_PATHS):
        raise SemanticCageV4R1PlanError("configured_audit_subject_labels_drift")
    return audit


def _load_config(expected_sha256):
    if not _hex64(expected_sha256):
        raise SemanticCageV4R1PlanError("config_sha256_invalid")
    raw = _project_file(CONFIG_RELATIVE_PATH).read_bytes()
    if _sha256(raw) != expected_sha256:
        raise SemanticCageV4R1PlanError("config_sha256_mismatch")
    try:
        config = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object, parse_constant=_reject_constant,
        )
    except Exception as exc:
        raise SemanticCageV4R1PlanError("config_invalid_json") from exc
    if type(config) is not dict:
        raise SemanticCageV4R1PlanError("config_not_object")
    if config.get("schema") != "kira.avatar.r25.semantic_control_cage_diagnostic.v4r1":
        raise SemanticCageV4R1PlanError("config_schema_drift")
    return config, raw


def _unresolved(value):
    stack = [value]
    while stack:
        current = stack.pop()
        if current is None or (type(current) is str and current.startswith("FINAL_")):
            return True
        if type(current) is dict:
            stack.extend(current.values())
        elif type(current) is list:
            stack.extend(current)
    return False


def build_sealed_execution_plan(expected_config_sha256, accepted_audit_sha256):
    """Return an authenticated future plan as data; execute and persist nothing."""

    config, raw = _load_config(expected_config_sha256)
    if config.get("status") == PREPARATION_STATUS:
        raise SemanticCageV4R1PlanError("static_v4r1_preparation_is_not_execution_authority")
    if config.get("status") != SEALED_STATUS:
        raise SemanticCageV4R1PlanError("sealed_successor_status_missing")
    pair = config.get("afes_v3r3_pair_binding")
    if type(pair) is not dict or pair.get("seal_status") != "SEALED_FINAL_INDEPENDENTLY_ACCEPTED_V3R3_PAIR":
        raise SemanticCageV4R1PlanError("v3r3_pair_not_sealed")
    if pair.get("required_final_placeholders") or _unresolved(pair.get("expected_pair_and_analysis")):
        raise SemanticCageV4R1PlanError("v3r3_pair_evidence_unresolved")
    gate = config.get("future_independent_audit_gate")
    if type(gate) is not dict or gate.get("path") != AUDIT_RELATIVE_PATH:
        raise SemanticCageV4R1PlanError("independent_audit_path_drift")
    audit_path = _project_file(AUDIT_RELATIVE_PATH)
    audit_raw = audit_path.read_bytes()
    _parse_independent_audit(
        audit_raw, accepted_audit_sha256, expected_config_sha256, config
    )
    if gate.get("accepted_audit_sha256") != accepted_audit_sha256:
        raise SemanticCageV4R1PlanError("sealed_config_audit_digest_mismatch")
    paths = config.get("append_only_execution_paths")
    if paths != {
        "independent_audit": AUDIT_RELATIVE_PATH,
        "outcome_receipt": OUTCOME_RELATIVE_PATH,
        "evidence_root": OUTPUT_RELATIVE_ROOT,
        "all_paths_must_not_exist_before_reservation": True,
    }:
        raise SemanticCageV4R1PlanError("append_only_paths_drift")
    expected = pair["expected_pair_and_analysis"]
    return {
        "schema": "kira.avatar.r25.semantic_control_cage_execution_plan.v4r1",
        "config_path": CONFIG_RELATIVE_PATH,
        "config_bytes": len(raw), "config_sha256": expected_config_sha256,
        "accepted_independent_audit_sha256": accepted_audit_sha256,
        "input_frame_order": [
            pair["final_locked_pair_execution_outcome_binding"]["path"],
            pair["final_run_01_receipt_binding"]["path"],
            pair["final_run_02_receipt_binding"]["path"],
        ],
        "input_frame_sha256_order": [
            expected["pair_acceptance_frame_sha256"],
            expected["run_01_frame_sha256"], expected["run_02_frame_sha256"],
        ],
        "mandatory_capability": {
            "schema": CAPABILITY_SCHEMA, "status": CAPABILITY_STATUS,
            "transport": "one_controller_server_owned_inherited_pipe_one_frame_then_eof",
            "nonce_source": "fresh_256_bit_controller_secret_not_command_line_or_path",
            "must_bind_parent_and_intended_child_process_ids": True,
            "must_bind_three_distinct_inherited_handles": True,
            "must_bind_config_audit_wrapper_controller_and_input_frame_hashes": True,
            "single_read_nonreusable": True,
        },
        "wrapper_command_template": [
            "<BOUND_BLENDER>", "--background", "--factory-startup", "--python",
            WRAPPER_RELATIVE_PATH, "--", "--config-sha256", expected_config_sha256,
            "--capability-handle", "<INHERITED_ONE_READ_CAPABILITY_PIPE>",
            "--lock-handle", "<INHERITED_INPUT_PIPE>",
            "--result-handle", "<DISTINCT_INHERITED_RESULT_PIPE>",
        ],
        "outcome_relative_path": OUTCOME_RELATIVE_PATH,
        "evidence_relative_root": OUTPUT_RELATIVE_ROOT,
        "authority": "READ_ONLY_DIAGNOSTIC_ONLY_NO_BODY_OR_RUNTIME_AUTHORITY",
    }


def main():
    print(
        "R25 semantic-cage Attempt 04r1 is static-only; controller execution "
        "is forbidden until a new append-only sealed successor is audited."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
