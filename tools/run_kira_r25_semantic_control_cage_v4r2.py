#!/usr/bin/env python3
from __future__ import annotations

"""Inert plan validator for semantic-cage Attempt 04r2.

This module cannot create a controller, pipe, process, secret, receipt, or
file.  It only exact-parses a future independent static audit and describes
the already-sealed native-controller contract as data.  Direct invocation is
always a refusal and is never execution authority.
"""

import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_semantic_control_cage_diagnostic_v4r2.json"
)
WRAPPER_RELATIVE_PATH = "tools/blender_diagnose_kira_r25_semantic_control_cage_v4r2.py"
AUDIT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/"
    "attempt_04r2/INDEPENDENT_AUDIT.json"
)
OUTCOME_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/"
    "attempt_04r2/EXECUTION_OUTCOME.receipt.bin"
)
OUTPUT_RELATIVE_ROOT = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_execution/attempt_04r2"
)
PREPARATION_STATUS = (
    "STATIC_PREPARATION_ONLY_NATIVE_CONTROLLER_BINDING_UNRESOLVED_EXECUTION_FORBIDDEN"
)
SEALED_STATUS = "SEALED_EXACT_NATIVE_CONTROLLER_ONE_SHOT_AFTER_ACCEPTED_04R2_AUDIT"
NATIVE_BINDING_STATE = "SEALED_EXACT_NATIVE_SEMANTIC_CONTROLLER_ONE_SHOT"
AUDIT_SCHEMA = "kira.avatar.r25.semantic_control_cage_independent_audit.v4r2"
AUDIT_DECISION = {
    "status": "ACCEPTED_STATIC_UNSEALED_NATIVE_BOUNDARY",
    "current_preparation_execution_authorized": False,
    "new_append_only_sealed_successor_plan_permitted": True,
}
AUDITOR_IDENTITY = {
    "independent_of_attempt04r2_authorship": True,
    "did_not_run_blender_afes_semantic_or_native_controller": True,
    "did_not_create_result_outcome_or_evidence": True,
}
AUDIT_TRUTH = [
    "STATIC_ACCEPTANCE_IS_NOT_EXECUTION_AUTHORITY",
    "ALL_04R2_SUBJECTS_AND_04R1_REJECTION_AUDIT_ARE_HASH_BOUND",
    "NATIVE_CONTROLLER_EXACT_IMAGE_AND_PROCESS_BINDING_REVIEWED",
    "ONLY_NEW_APPEND_ONLY_SEALED_SUCCESSOR_MAY_PROCEED",
]
AUDIT_KEYS = {
    "schema", "authoritative_decision", "auditor", "subject_manifest",
    "native_controller_binding", "findings", "truth_boundary",
}
SUBJECT_PATHS = {
    "attempt04r2_config": CONFIG_RELATIVE_PATH,
    "attempt04r1_adapter_dependency": (
        "tools/kira_r25_semantic_control_cage_afes_v3r3_adapter_v4r1.py"
    ),
    "attempt04r2_wrapper": WRAPPER_RELATIVE_PATH,
    "attempt04r2_controller_planner": (
        "tools/run_kira_r25_semantic_control_cage_v4r2.py"
    ),
    "attempt04r2_test": "Testing/test_kira_r25_semantic_control_cage_attempt04r2.py",
    "attempt04r2_checkpoint": (
        "RecoverySprint/continuation_20260809/"
        "kira_r25_semantic_cage_correspondence_static_preparation/"
        "attempt_04r2/CHECKPOINT.md"
    ),
    "attempt04r1_rejection_audit": (
        "RecoverySprint/continuation_20260809/"
        "kira_r25_semantic_cage_correspondence_static_preparation/"
        "attempt_04r1/INDEPENDENT_AUDIT.md"
    ),
}
CAPABILITY_SCHEMA = (
    "kira.avatar.r25.semantic_control_cage_native_execution_capability.v4r2"
)
CAPABILITY_STATUS = "EXACT_NATIVE_CONTROLLER_AUDIT_ACCEPTED_ONE_SHOT"
NATIVE_BINDING_KEYS = {
    "state", "final_image_path", "bytes", "sha256", "volume_serial_number",
    "file_id_128_hex", "image_file_creation_time_100ns",
    "parent_process_creation_time_100ns", "windows_session_id",
    "authorized_one_shot_run_nonce_sha256",
}


class SemanticCageV4R2PlanError(RuntimeError):
    pass


class _DuplicateKey(ValueError):
    pass


def _sha256(value):
    return hashlib.sha256(value).hexdigest()


def _hex(value, length):
    return type(value) is str and len(value) == length and all(
        "0" <= character <= "9" or "a" <= character <= "f"
        for character in value
    )


def _hex64(value):
    return _hex(value, 64)


def _project_file(relative):
    if type(relative) is not str or not relative:
        raise SemanticCageV4R2PlanError("path_not_text")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise SemanticCageV4R2PlanError("unsafe_project_relative_path")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise SemanticCageV4R2PlanError("symlink_binding_refused")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise SemanticCageV4R2PlanError("path_escaped_project_root") from exc
    if not resolved.is_file():
        raise SemanticCageV4R2PlanError("bound_file_missing")
    return resolved


def _row_for(relative):
    path = _project_file(relative)
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "sha256": _sha256(raw)}


def _exact_row(value, expected_path, label):
    if type(value) is not dict or set(value) != {"path", "bytes", "sha256"}:
        raise SemanticCageV4R2PlanError(label + "_row_shape")
    if value["path"] != expected_path or type(value["bytes"]) is not int or value["bytes"] <= 0 or not _hex64(value["sha256"]):
        raise SemanticCageV4R2PlanError(label + "_row_value")
    actual = _row_for(expected_path)
    if value != actual:
        raise SemanticCageV4R2PlanError(label + "_subject_hash_drift")
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
        raise SemanticCageV4R2PlanError(label + "_byte_length")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise SemanticCageV4R2PlanError(label + "_duplicate_key:" + str(exc)) from exc
    except Exception as exc:
        raise SemanticCageV4R2PlanError(label + "_invalid_json") from exc
    if type(value) is not dict or _canonical_json_bytes(value) != raw:
        raise SemanticCageV4R2PlanError(label + "_not_canonical_object")
    return value


def _require_native_binding(binding):
    if type(binding) is not dict or set(binding) != NATIVE_BINDING_KEYS:
        raise SemanticCageV4R2PlanError("native_controller_binding_shape_drift")
    if binding["state"] != NATIVE_BINDING_STATE:
        raise SemanticCageV4R2PlanError("native_controller_binding_not_sealed")
    if any(type(value) is str and value.startswith("UNRESOLVED_") for value in binding.values()):
        raise SemanticCageV4R2PlanError("native_controller_binding_contains_sentinel")
    if type(binding["final_image_path"]) is not str or not binding["final_image_path"]:
        raise SemanticCageV4R2PlanError("native_controller_path_invalid")
    if type(binding["bytes"]) is not int or binding["bytes"] <= 0 or not _hex64(binding["sha256"]):
        raise SemanticCageV4R2PlanError("native_controller_image_binding_invalid")
    if type(binding["volume_serial_number"]) is not int or binding["volume_serial_number"] < 0:
        raise SemanticCageV4R2PlanError("native_controller_volume_invalid")
    if not _hex(binding["file_id_128_hex"], 32):
        raise SemanticCageV4R2PlanError("native_controller_file_id_invalid")
    for key in ("image_file_creation_time_100ns", "parent_process_creation_time_100ns"):
        if type(binding[key]) is not int or binding[key] <= 0:
            raise SemanticCageV4R2PlanError("native_controller_time_invalid:" + key)
    if type(binding["windows_session_id"]) is not int or binding["windows_session_id"] < 0:
        raise SemanticCageV4R2PlanError("native_controller_session_invalid")
    if not _hex64(binding["authorized_one_shot_run_nonce_sha256"]):
        raise SemanticCageV4R2PlanError("native_controller_nonce_digest_invalid")
    return binding


def _parse_independent_audit(
    audit_raw, expected_audit_sha256, expected_config_sha256, config,
):
    if not _hex64(expected_audit_sha256) or _sha256(audit_raw) != expected_audit_sha256:
        raise SemanticCageV4R2PlanError("independent_audit_sha256_mismatch")
    audit = _parse_canonical_object(audit_raw, "independent_audit")
    if set(audit) != AUDIT_KEYS or audit["schema"] != AUDIT_SCHEMA:
        raise SemanticCageV4R2PlanError("independent_audit_schema_or_shape_drift")
    if audit["authoritative_decision"] != AUDIT_DECISION:
        raise SemanticCageV4R2PlanError("independent_audit_decision_not_accepted")
    if audit["auditor"] != AUDITOR_IDENTITY:
        raise SemanticCageV4R2PlanError("independent_auditor_identity_drift")
    if audit["findings"] != {"blocking": []} or audit["truth_boundary"] != AUDIT_TRUTH:
        raise SemanticCageV4R2PlanError("independent_audit_findings_or_truth_drift")
    if audit["native_controller_binding"] != config["native_semantic_controller_binding"]:
        raise SemanticCageV4R2PlanError("independent_audit_native_controller_binding_drift")
    manifest = audit["subject_manifest"]
    if type(manifest) is not dict or set(manifest) != set(SUBJECT_PATHS):
        raise SemanticCageV4R2PlanError("independent_audit_subject_manifest_shape")
    for label, relative in SUBJECT_PATHS.items():
        _exact_row(manifest[label], relative, label)
    if manifest["attempt04r2_config"]["sha256"] != expected_config_sha256:
        raise SemanticCageV4R2PlanError("independent_audit_sealed_config_digest_mismatch")
    gate = config.get("future_independent_audit_gate")
    if type(gate) is not dict or gate.get("schema") != AUDIT_SCHEMA or gate.get("required_decision") != AUDIT_DECISION:
        raise SemanticCageV4R2PlanError("configured_audit_gate_protocol_drift")
    if gate.get("must_bind_exact_subject_labels") != sorted(SUBJECT_PATHS):
        raise SemanticCageV4R2PlanError("configured_audit_subject_labels_drift")
    return audit


def _load_config(expected_sha256):
    if not _hex64(expected_sha256):
        raise SemanticCageV4R2PlanError("config_sha256_invalid")
    raw = _project_file(CONFIG_RELATIVE_PATH).read_bytes()
    if _sha256(raw) != expected_sha256:
        raise SemanticCageV4R2PlanError("config_sha256_mismatch")
    try:
        config = json.loads(
            raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except Exception as exc:
        raise SemanticCageV4R2PlanError("config_invalid_json") from exc
    if type(config) is not dict or config.get("schema") != "kira.avatar.r25.semantic_control_cage_diagnostic.v4r2":
        raise SemanticCageV4R2PlanError("config_schema_drift")
    return config, raw


def _unresolved(value):
    stack = [value]
    while stack:
        current = stack.pop()
        if current is None or (
            type(current) is str and (
                current.startswith("FINAL_") or current.startswith("UNRESOLVED_")
            )
        ):
            return True
        if type(current) is dict:
            stack.extend(current.values())
        elif type(current) is list:
            stack.extend(current)
    return False


def build_sealed_execution_plan(expected_config_sha256, accepted_audit_sha256):
    """Validate and return a future plan as data; perform no action."""

    config, raw = _load_config(expected_config_sha256)
    if config.get("status") == PREPARATION_STATUS:
        raise SemanticCageV4R2PlanError("static_v4r2_preparation_is_not_execution_authority")
    if config.get("status") != SEALED_STATUS:
        raise SemanticCageV4R2PlanError("sealed_successor_status_missing")
    native = _require_native_binding(config.get("native_semantic_controller_binding"))
    pair = config.get("afes_v3r3_pair_binding")
    if type(pair) is not dict or pair.get("seal_status") != "SEALED_FINAL_INDEPENDENTLY_ACCEPTED_V3R3_PAIR":
        raise SemanticCageV4R2PlanError("v3r3_pair_not_sealed")
    if pair.get("required_final_placeholders") or _unresolved(pair.get("expected_pair_and_analysis")):
        raise SemanticCageV4R2PlanError("v3r3_pair_evidence_unresolved")
    gate = config.get("future_independent_audit_gate")
    if type(gate) is not dict or gate.get("path") != AUDIT_RELATIVE_PATH:
        raise SemanticCageV4R2PlanError("independent_audit_path_drift")
    audit_raw = _project_file(AUDIT_RELATIVE_PATH).read_bytes()
    _parse_independent_audit(
        audit_raw, accepted_audit_sha256, expected_config_sha256, config
    )
    if gate.get("accepted_audit_sha256") != accepted_audit_sha256:
        raise SemanticCageV4R2PlanError("sealed_config_audit_digest_mismatch")
    paths = config.get("append_only_execution_paths")
    if paths != {
        "independent_audit": AUDIT_RELATIVE_PATH,
        "outcome_receipt": OUTCOME_RELATIVE_PATH,
        "evidence_root": OUTPUT_RELATIVE_ROOT,
        "all_paths_must_not_exist_before_reservation": True,
    }:
        raise SemanticCageV4R2PlanError("append_only_paths_drift")
    expected = pair["expected_pair_and_analysis"]
    return {
        "schema": "kira.avatar.r25.semantic_control_cage_execution_plan.v4r2",
        "authority": "INERT_VALIDATED_PLAN_ONLY_NATIVE_CONTROLLER_REMAINS_SOLE_LAUNCH_AUTHORITY",
        "config_path": CONFIG_RELATIVE_PATH,
        "config_bytes": len(raw), "config_sha256": expected_config_sha256,
        "accepted_independent_audit_sha256": accepted_audit_sha256,
        "native_controller_binding": native,
        "input_frame_sha256_order": [
            expected["pair_acceptance_frame_sha256"],
            expected["run_01_frame_sha256"], expected["run_02_frame_sha256"],
        ],
        "mandatory_capability": {
            "schema": CAPABILITY_SCHEMA, "status": CAPABILITY_STATUS,
            "pipe_server_pid_must_equal_os_parent_pid": True,
            "parent_process_and_exact_image_handles_held_until_diagnostic_end": True,
            "must_match_all_native_image_process_session_fields": True,
            "fresh_nonce_preimage_must_match_sealed_sha256": True,
            "must_bind_exact_config_wrapper_audit_native_and_input_hashes": True,
            "must_bind_child_pid_and_process_creation_time": True,
            "single_read_nonreusable": True,
        },
        "wrapper_relative_path": WRAPPER_RELATIVE_PATH,
        "outcome_relative_path": OUTCOME_RELATIVE_PATH,
        "evidence_relative_root": OUTPUT_RELATIVE_ROOT,
    }


def main():
    print(
        "R25 semantic-cage Attempt 04r2 is static-only and unsealed; no native "
        "controller binding exists and execution is forbidden."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
