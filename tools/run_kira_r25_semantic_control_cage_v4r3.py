#!/usr/bin/env python3
from __future__ import annotations

"""Inert out-of-band audit/lease plan validator for Attempt 04r3.

No process, controller, pipe, secret, native API, Blender API, or persistence
exists here.  A future exact native controller receives the canonical audit
path and digest out of band.  This module can only validate equivalent bytes
and return a plan description; direct invocation always refuses.
"""

import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_semantic_control_cage_diagnostic_v4r3.json"
)
WRAPPER_RELATIVE_PATH = "tools/blender_diagnose_kira_r25_semantic_control_cage_v4r3.py"
AUDIT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/"
    "attempt_04r3/INDEPENDENT_AUDIT.json"
)
OUTCOME_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/"
    "attempt_04r3/EXECUTION_OUTCOME.receipt.bin"
)
OUTPUT_RELATIVE_ROOT = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_execution/attempt_04r3"
)
PREPARATION_STATUS = (
    "STATIC_PREPARATION_ONLY_IMMUTABLE_NATIVE_IMAGE_UNRESOLVED_EXECUTION_FORBIDDEN"
)
SEALED_STATUS = "SEALED_IMMUTABLE_NATIVE_IMAGE_ONLY_AFTER_ACCEPTED_04R3_STATIC_AUDIT"
STATIC_NATIVE_STATE = "SEALED_IMMUTABLE_NATIVE_EXECUTABLE_IDENTITY"
STATIC_NATIVE_KEYS = {
    "state", "final_image_path", "bytes", "sha256", "volume_serial_number",
    "file_id_128_hex", "image_file_creation_time_100ns",
}
AUDIT_SCHEMA = "kira.avatar.r25.semantic_control_cage_independent_audit.v4r3"
AUDIT_DECISION = {
    "status": "ACCEPTED_STATIC_IMMUTABLE_IMAGE_AND_RUNTIME_LEASE_SPLIT",
    "current_preparation_execution_authorized": False,
    "new_append_only_sealed_successor_plan_permitted": True,
}
AUDITOR_IDENTITY = {
    "independent_of_attempt04r3_authorship": True,
    "did_not_run_native_controller_blender_afes_or_semantic_wrapper": True,
    "did_not_create_result_outcome_or_evidence": True,
}
AUDIT_TRUTH = [
    "STATIC_CONFIG_HAS_ONLY_IMMUTABLE_NATIVE_EXECUTABLE_IDENTITY",
    "AUDIT_HASH_AND_RUNTIME_INSTANCE_STATE_ARE_OUT_OF_BAND",
    "EXACT_NATIVE_CONTROLLER_PERSISTENT_LEASE_IMPLEMENTATION_REVIEWED",
    "MAPPED_MAIN_IMAGE_PROOF_REQUIRED_BEFORE_RUNTIME_INPUT_OR_BLEND",
    "STATIC_ACCEPTANCE_IS_NOT_EXECUTION_AUTHORITY",
]
AUDIT_LEASE_REVIEW = {
    "authority_owner": "EXACT_INDEPENDENTLY_AUDITED_NATIVE_CONTROLLER_EXECUTABLE",
    "persistent_exclusive_state_required": True,
    "fresh_lease_id_and_nonce_per_reserved_child_required": True,
    "reservation_persisted_before_child_resume_required": True,
    "lease_and_nonce_marked_consumed_before_capability_write_required": True,
    "second_issue_or_replay_refused_by_native_authority_required": True,
    "cross_child_reissue_refused_by_native_authority_required": True,
    "child_local_replay_ledger_is_not_authority": True,
}
AUDIT_KEYS = {
    "schema", "authoritative_decision", "auditor", "subject_manifest",
    "native_controller_executable_binding", "native_runtime_lease_review",
    "findings", "truth_boundary",
}
SUBJECT_PATHS = {
    "attempt04r3_config": CONFIG_RELATIVE_PATH,
    "attempt04r1_adapter_dependency": (
        "tools/kira_r25_semantic_control_cage_afes_v3r3_adapter_v4r1.py"
    ),
    "attempt04r3_wrapper": WRAPPER_RELATIVE_PATH,
    "attempt04r3_controller_planner": "tools/run_kira_r25_semantic_control_cage_v4r3.py",
    "attempt04r3_test": "Testing/test_kira_r25_semantic_control_cage_attempt04r3.py",
    "attempt04r3_checkpoint": (
        "RecoverySprint/continuation_20260809/"
        "kira_r25_semantic_cage_correspondence_static_preparation/"
        "attempt_04r3/CHECKPOINT.md"
    ),
    "attempt04r2_rejection_audit": (
        "RecoverySprint/continuation_20260809/"
        "kira_r25_semantic_cage_correspondence_static_preparation/"
        "attempt_04r2/INDEPENDENT_AUDIT.md"
    ),
}
RUNTIME_LEASE_REQUIREMENTS = {
    "owner": "EXACT_AUDITED_NATIVE_CONTROLLER_PERSISTENT_STATE",
    "parent_runtime_fields": [
        "process_id", "process_creation_time_100ns", "windows_session_id",
        "process_image_device_path", "mapped_image_device_path",
    ],
    "child_runtime_fields": ["process_id", "process_creation_time_100ns"],
    "fresh_fields": ["lease_id", "one_shot_nonce", "capability_pipe_instance_id"],
    "hash_bindings": [
        "config_sha256", "wrapper_sha256", "native_controller_sha256",
        "accepted_audit_sha256",
    ],
    "audit_binding": "OUT_OF_BAND_PATH_HASH_AND_EXACT_CANONICAL_SUBJECT",
    "native_persistent_consume_before_child_resume": True,
    "native_refuses_second_issue_and_cross_child_reissue": True,
    "wrapper_reads_one_frame_then_eof": True,
    "child_local_cross_process_replay_authority": False,
}


class SemanticCageV4R3PlanError(RuntimeError):
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
        raise SemanticCageV4R3PlanError("path_not_text")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise SemanticCageV4R3PlanError("unsafe_project_relative_path")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise SemanticCageV4R3PlanError("symlink_binding_refused")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise SemanticCageV4R3PlanError("path_escaped_project_root") from exc
    if not resolved.is_file():
        raise SemanticCageV4R3PlanError("bound_file_missing")
    return resolved


def _row_for(relative):
    path = _project_file(relative)
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "sha256": _sha256(raw)}


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
        raise SemanticCageV4R3PlanError(label + "_byte_length")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise SemanticCageV4R3PlanError(label + "_duplicate_key:" + str(exc)) from exc
    except Exception as exc:
        raise SemanticCageV4R3PlanError(label + "_invalid_json") from exc
    if type(value) is not dict or _canonical_json_bytes(value) != raw:
        raise SemanticCageV4R3PlanError(label + "_not_canonical_object")
    return value


def _require_static_native_binding(binding):
    if type(binding) is not dict or set(binding) != STATIC_NATIVE_KEYS:
        raise SemanticCageV4R3PlanError("static_native_executable_binding_shape_drift")
    if binding["state"] != STATIC_NATIVE_STATE:
        raise SemanticCageV4R3PlanError("static_native_executable_binding_not_sealed")
    if any(type(value) is str and value.startswith("UNRESOLVED_") for value in binding.values()):
        raise SemanticCageV4R3PlanError("static_native_executable_binding_contains_sentinel")
    if type(binding["final_image_path"]) is not str or not binding["final_image_path"]:
        raise SemanticCageV4R3PlanError("static_native_path_invalid")
    if type(binding["bytes"]) is not int or binding["bytes"] <= 0 or not _hex64(binding["sha256"]):
        raise SemanticCageV4R3PlanError("static_native_image_binding_invalid")
    if type(binding["volume_serial_number"]) is not int or binding["volume_serial_number"] < 0:
        raise SemanticCageV4R3PlanError("static_native_volume_invalid")
    if not _hex(binding["file_id_128_hex"], 32):
        raise SemanticCageV4R3PlanError("static_native_file_id_invalid")
    if type(binding["image_file_creation_time_100ns"]) is not int or binding["image_file_creation_time_100ns"] <= 0:
        raise SemanticCageV4R3PlanError("static_native_creation_time_invalid")
    return binding


def _validate_audit_subject(audit, expected_audit_sha256, expected_config_sha256, config):
    canonical = _canonical_json_bytes(audit)
    if not _hex64(expected_audit_sha256) or _sha256(canonical) != expected_audit_sha256:
        raise SemanticCageV4R3PlanError("independent_audit_sha256_mismatch")
    if type(audit) is not dict or set(audit) != AUDIT_KEYS or audit["schema"] != AUDIT_SCHEMA:
        raise SemanticCageV4R3PlanError("independent_audit_schema_or_shape_drift")
    if audit["authoritative_decision"] != AUDIT_DECISION:
        raise SemanticCageV4R3PlanError("independent_audit_decision_not_accepted")
    if audit["auditor"] != AUDITOR_IDENTITY:
        raise SemanticCageV4R3PlanError("independent_auditor_identity_drift")
    if audit["findings"] != {"blocking": []} or audit["truth_boundary"] != AUDIT_TRUTH:
        raise SemanticCageV4R3PlanError("independent_audit_findings_or_truth_drift")
    if audit["native_controller_executable_binding"] != config["native_semantic_controller_executable_binding"]:
        raise SemanticCageV4R3PlanError("independent_audit_native_binding_drift")
    if audit["native_runtime_lease_review"] != AUDIT_LEASE_REVIEW:
        raise SemanticCageV4R3PlanError("independent_audit_native_lease_review_drift")
    manifest = audit["subject_manifest"]
    if type(manifest) is not dict or set(manifest) != set(SUBJECT_PATHS):
        raise SemanticCageV4R3PlanError("independent_audit_subject_manifest_shape")
    for label, relative in SUBJECT_PATHS.items():
        if manifest[label] != _row_for(relative):
            raise SemanticCageV4R3PlanError(label + "_subject_hash_drift")
    if manifest["attempt04r3_config"]["sha256"] != expected_config_sha256:
        raise SemanticCageV4R3PlanError("independent_audit_config_digest_mismatch")
    return audit


def _parse_out_of_band_audit(
    audit_raw, expected_audit_sha256, expected_config_sha256, config,
):
    audit = _parse_canonical_object(audit_raw, "independent_audit")
    return _validate_audit_subject(
        audit, expected_audit_sha256, expected_config_sha256, config
    )


def _load_config(expected_sha256):
    if not _hex64(expected_sha256):
        raise SemanticCageV4R3PlanError("config_sha256_invalid")
    raw = _project_file(CONFIG_RELATIVE_PATH).read_bytes()
    if _sha256(raw) != expected_sha256:
        raise SemanticCageV4R3PlanError("config_sha256_mismatch")
    try:
        config = json.loads(
            raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except Exception as exc:
        raise SemanticCageV4R3PlanError("config_invalid_json") from exc
    if type(config) is not dict or config.get("schema") != "kira.avatar.r25.semantic_control_cage_diagnostic.v4r3":
        raise SemanticCageV4R3PlanError("config_schema_drift")
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


def build_sealed_execution_plan(
    expected_config_sha256, accepted_audit_relative_path,
    accepted_audit_sha256,
):
    """Validate out-of-band audit bytes and return inert plan data only."""

    config, raw = _load_config(expected_config_sha256)
    if config.get("status") == PREPARATION_STATUS:
        raise SemanticCageV4R3PlanError("static_v4r3_preparation_is_not_execution_authority")
    if config.get("status") != SEALED_STATUS:
        raise SemanticCageV4R3PlanError("sealed_successor_status_missing")
    native = _require_static_native_binding(
        config.get("native_semantic_controller_executable_binding")
    )
    pair = config.get("afes_v3r3_pair_binding")
    if type(pair) is not dict or pair.get("seal_status") != "SEALED_FINAL_INDEPENDENTLY_ACCEPTED_V3R3_PAIR":
        raise SemanticCageV4R3PlanError("v3r3_pair_not_sealed")
    if pair.get("required_final_placeholders") or _unresolved(pair.get("expected_pair_and_analysis")):
        raise SemanticCageV4R3PlanError("v3r3_pair_evidence_unresolved")
    if accepted_audit_relative_path != AUDIT_RELATIVE_PATH:
        raise SemanticCageV4R3PlanError("out_of_band_audit_path_drift")
    audit_raw = _project_file(accepted_audit_relative_path).read_bytes()
    audit = _parse_out_of_band_audit(
        audit_raw, accepted_audit_sha256, expected_config_sha256, config
    )
    expected = pair["expected_pair_and_analysis"]
    return {
        "schema": "kira.avatar.r25.semantic_control_cage_execution_plan.v4r3",
        "authority": "INERT_PLAN_ONLY_EXACT_NATIVE_CONTROLLER_OWNS_RUNTIME_LEASE",
        "config_path": CONFIG_RELATIVE_PATH,
        "config_bytes": len(raw), "config_sha256": expected_config_sha256,
        "out_of_band_accepted_audit": {
            "path": accepted_audit_relative_path,
            "sha256": accepted_audit_sha256,
            "canonical_subject": audit,
        },
        "native_controller_executable_binding": native,
        "runtime_lease_requirements": RUNTIME_LEASE_REQUIREMENTS,
        "input_frame_sha256_order": [
            expected["pair_acceptance_frame_sha256"],
            expected["run_01_frame_sha256"], expected["run_02_frame_sha256"],
        ],
        "wrapper_relative_path": WRAPPER_RELATIVE_PATH,
        "outcome_relative_path": OUTCOME_RELATIVE_PATH,
        "evidence_relative_root": OUTPUT_RELATIVE_ROOT,
    }


def main():
    print(
        "R25 semantic-cage Attempt 04r3 is static-only and unsealed; the native "
        "image identity and out-of-band runtime lease do not exist."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
