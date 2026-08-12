"""Dependency-free AFES-v3r3 validator for semantic-cage Attempt 04r1.

Exact validation in this module performs no imports and never consults the
ambient module registry. The Blender wrapper executes these bytes with an
importer that rejects every import request.
"""


class SemanticCageAfesV3R3R1Error(ValueError):
    pass


PAIR_SCHEMA = "kira.avatar.r25.foundation_afes_locked_pair_acceptance.v3r3"
PAIR_STATUS = "AFES_AND_TRANSITION_RINGS_EXTRACTED_READ_ONLY_PAIR_MATCHED"
RUN_SCHEMA = "kira.avatar.r25.foundation_afes_locked_extraction_run.v3r3"
RUN_STATUS = "READ_ONLY_EXTRACTION_COMPLETE_PENDING_PAIR_MATCH"
INNER_SCHEMA = "kira.avatar.r25.foundation_afes_transition_diagnostic.v5"
INNER_ARTIFACT_KIND = "READ_ONLY_PRIVATE_EXACT_BYTE_AFES_DIAGNOSTIC"
INNER_STATUS = "EXTRACTED_UNSEALED_REQUIRES_MATCHING_FRESH_LOCKED_RUN"

PAIR_TRUTH_BOUNDARY = [
    "READ_ONLY_DIAGNOSTIC_PAIR_ONLY", "NO_BLEND_MUTATION_OR_SAVE",
    "NO_RENDER_EXPORT_OR_PATH_RESULT", "NO_BODY_CANDIDATE",
    "NO_AUTHORING_OR_RUNTIME_AUTHORITY", "V3R1_REJECTED_AND_NOT_EXECUTED",
    "V3R2_REJECTED_AND_NOT_EXECUTED",
]
RUN_TRUTH_BOUNDARY = [
    "READ_ONLY_FOUNDATION_DIAGNOSTIC", "NO_BLEND_MUTATION_OR_SAVE",
    "NO_RENDER_OR_EXPORT", "NO_CANDIDATE_OR_BODY_AUTHORING",
    "THIS_SINGLE_RUN_IS_NOT_ACCEPTANCE", "V3R1_REJECTED_AND_NOT_EXECUTED",
    "V3R2_REJECTED_AND_NOT_EXECUTED",
]
INNER_TRUTH_BOUNDARY = {
    "static_preparation_is_not_execution": True,
    "attempts_01_through_04_rejected_and_preserved": True,
    "attempt_05_fresh_independent_audit_required": True,
    "attempt_05_self_authorization_forbidden": True,
    "controller_or_pipe_creation_implemented": False,
    "child_process_authentication_implemented": False,
    "replay_protection_implemented": False,
    "parent_binding_of_this_config_hash_implemented": False,
    "two_fresh_locked_matching_extractions_still_required": True,
    "blender_execution_authorized": False,
    "body_authoring_authorized": False,
}
PRIVATE_RECEIPT_RUNTIME = {
    "receipt_module_name": "_kira_private_canonical_receipt_attempt05",
    "decoded_receipt_class_module": "_kira_private_canonical_receipt_attempt05",
    "dataclass_shim_module_name": "_kira_private_dataclass_shim_attempt05",
    "receipt_or_shim_aliases_ambient_sys_modules": False,
}
READ_ONLY_GUARDS = {
    "blend_loaded_exactly": True,
    "blend_clean_before": True,
    "blend_clean_after": True,
    "data_block_inventory_unchanged": True,
    "operator_calls_by_this_extractor": 0,
    "edit_calls_by_this_extractor": 0,
    "persistence_calls_by_this_extractor": 0,
    "path_result_writes_by_this_extractor": 0,
}
AFES_V5_CONFIG_BINDING = {
    "path": "Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_read_only_extraction_v5.json",
    "bytes": 9972,
    "sha256": "0f51a937117912ef2863655a30d4e10da299042d4cfc975310ad18e5fa2c98ab",
}
AFES_V5_EXTRACTOR_BINDING = {
    "path": "tools/blender_extract_kira_r25_foundation_afes_transition_rings_v5.py",
    "bytes": 23834,
    "sha256": "333b17e064ae9cd681f309606076da17961eb738b1bbace462533bd30918959a",
}

PAIR_KEYS = {
    "schema", "status", "execution_contract_sha256", "execution_contract_bytes",
    "bound_inputs_unchanged_under_native_locks", "input_snapshot_sha256", "runs",
    "matching_inner_payload_sha256", "full_normalized_topology_sha256", "truth_boundary",
}
RUN_KEYS = {
    "schema", "status", "execution_contract", "accepted_afes_v5_config",
    "accepted_afes_v5_extractor", "pair_session_nonce", "run_nonce", "run_number",
    "result_pipe_handle", "child_pid", "parent_pid", "inner_attempt05_payload",
    "truth_boundary",
}
INNER_KEYS = {
    "schema", "artifact_kind", "status", "config_observed_unsealed_by_parent",
    "private_execution_dependencies", "private_source_physical_reads",
    "ambient_project_modules_consumed", "ambient_dataclasses_decorator_consumed",
    "private_modules_inserted_into_sys_modules", "private_receipt_runtime",
    "foundation_object", "foundation_mesh", "analysis", "topology_sealing",
    "read_only_guards", "truth_boundary",
}
RUN_METADATA_KEYS = {
    "run_number", "pair_session_nonce", "run_nonce", "pid", "exit_code",
    "frame_bytes", "frame_sha256", "payload_sha256", "inner_payload_sha256",
    "topology_sha256", "stdout_bytes", "stdout_sha256", "stderr_bytes", "stderr_sha256",
}
EXPECTED_KEYS = {
    "pair_schema", "pair_status", "pair_truth_boundary",
    "pair_acceptance_frame_sha256", "execution_contract_binding",
    "input_snapshot_sha256", "matching_inner_payload_sha256",
    "run_schema", "run_status", "run_truth_boundary", "run_01_frame_sha256",
    "run_02_frame_sha256", "run_01_payload_sha256", "run_02_payload_sha256",
    "pair_session_nonce", "run_01_nonce", "run_02_nonce", "exact_run_metadata",
    "accepted_afes_v5_config", "accepted_afes_v5_extractor", "inner_schema",
    "inner_artifact_kind", "inner_status", "inner_truth_boundary",
    "exact_extraction_verified_inputs", "private_receipt_runtime",
    "exact_read_only_guards", "foundation_object", "foundation_mesh",
    "foundation_vertex_count", "foundation_edge_count", "foundation_face_count",
    "foundation_topology_sha256", "required_afes_group_names", "afes_union_count",
    "afes_union_sha256", "ring_1_count", "ring_1_sha256", "ring_2_count",
    "ring_2_sha256", "combined_ring_count", "combined_ring_sha256",
    "locked_vertex_count", "locked_vertex_sha256", "exact_topology_structure",
    "exact_afes_bounds_object_nm",
}


def _hex64(value, label):
    if type(value) is not str or len(value) != 64:
        raise SemanticCageAfesV3R3R1Error(label + "_must_be_64_lowercase_hex")
    for character in value:
        if not ("0" <= character <= "9" or "a" <= character <= "f"):
            raise SemanticCageAfesV3R3R1Error(label + "_must_be_64_lowercase_hex")
    return value


def _integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise SemanticCageAfesV3R3R1Error(label + "_invalid")
    return value


def _exact_row(value, label):
    if type(value) is not dict or set(value) != {"path", "bytes", "sha256"}:
        raise SemanticCageAfesV3R3R1Error(label + "_row_shape")
    path = value.get("path")
    if type(path) is not str or not path or "\\" in path or path.startswith("/") or ".." in path.split("/"):
        raise SemanticCageAfesV3R3R1Error(label + "_path_invalid")
    _integer(value.get("bytes"), label + "_bytes", 1)
    _hex64(value.get("sha256"), label + "_sha256")
    return dict(value)


def _contains_unresolved(value):
    stack = [value]
    while stack:
        current = stack.pop()
        if current is None:
            return True
        if type(current) is str and current.startswith("FINAL_"):
            return True
        if type(current) is dict:
            stack.extend(current.values())
        elif type(current) in (list, tuple):
            stack.extend(current)
    return False


def require_sealed_expected(expected, trusted_afes_v5_config, trusted_afes_v5_extractor):
    if type(expected) is not dict or set(expected) != EXPECTED_KEYS:
        raise SemanticCageAfesV3R3R1Error("expected_pair_and_analysis_shape_drift")
    if _contains_unresolved(expected):
        raise SemanticCageAfesV3R3R1Error("expected_pair_and_analysis_still_unsealed")
    literal_fields = {
        "pair_schema": PAIR_SCHEMA, "pair_status": PAIR_STATUS,
        "pair_truth_boundary": PAIR_TRUTH_BOUNDARY,
        "run_schema": RUN_SCHEMA, "run_status": RUN_STATUS,
        "run_truth_boundary": RUN_TRUTH_BOUNDARY,
        "inner_schema": INNER_SCHEMA, "inner_artifact_kind": INNER_ARTIFACT_KIND,
        "inner_status": INNER_STATUS, "inner_truth_boundary": INNER_TRUTH_BOUNDARY,
        "private_receipt_runtime": PRIVATE_RECEIPT_RUNTIME,
        "exact_read_only_guards": READ_ONLY_GUARDS,
        "accepted_afes_v5_config": AFES_V5_CONFIG_BINDING,
        "accepted_afes_v5_extractor": AFES_V5_EXTRACTOR_BINDING,
    }
    for key, literal in literal_fields.items():
        if expected.get(key) != literal:
            raise SemanticCageAfesV3R3R1Error(key + "_not_frozen_literal")
    if _exact_row(trusted_afes_v5_config, "trusted_afes_v5_config") != AFES_V5_CONFIG_BINDING:
        raise SemanticCageAfesV3R3R1Error("trusted_afes_v5_config_not_frozen_binding")
    if _exact_row(trusted_afes_v5_extractor, "trusted_afes_v5_extractor") != AFES_V5_EXTRACTOR_BINDING:
        raise SemanticCageAfesV3R3R1Error("trusted_afes_v5_extractor_not_frozen_binding")
    _exact_row(expected["execution_contract_binding"], "execution_contract_binding")
    for key in (
        "pair_acceptance_frame_sha256", "input_snapshot_sha256",
        "matching_inner_payload_sha256", "run_01_frame_sha256", "run_02_frame_sha256",
        "run_01_payload_sha256", "run_02_payload_sha256", "pair_session_nonce",
        "run_01_nonce", "run_02_nonce", "foundation_topology_sha256",
        "afes_union_sha256", "ring_1_sha256", "ring_2_sha256",
        "combined_ring_sha256", "locked_vertex_sha256",
    ):
        _hex64(expected[key], key)
    metadata = expected["exact_run_metadata"]
    if type(metadata) is not list or len(metadata) != 2:
        raise SemanticCageAfesV3R3R1Error("exact_run_metadata_requires_two_rows")
    for number, row in enumerate(metadata, start=1):
        if type(row) is not dict or set(row) != RUN_METADATA_KEYS or row.get("run_number") != number:
            raise SemanticCageAfesV3R3R1Error("exact_run_metadata_shape")
    inputs = expected["exact_extraction_verified_inputs"]
    if type(inputs) is not dict or set(inputs) != {
        "private_execution_dependencies", "private_source_physical_reads"
    }:
        raise SemanticCageAfesV3R3R1Error("exact_extraction_verified_inputs_shape")
    return expected


def validate_afes_v3r3_pair_bundle(
    *, pair_payload, pair_frame_sha256, run_payloads, run_frame_sha256s,
    run_frame_bytes, run_payload_sha256s, source_edges, source_faces, expected,
    legacy_control, trusted_afes_v5_config, trusted_afes_v5_extractor,
):
    expected = require_sealed_expected(
        expected, trusted_afes_v5_config, trusted_afes_v5_extractor
    )
    if type(pair_payload) is not dict or set(pair_payload) != PAIR_KEYS:
        raise SemanticCageAfesV3R3R1Error("pair_payload_shape_drift")
    if pair_frame_sha256 != expected["pair_acceptance_frame_sha256"]:
        raise SemanticCageAfesV3R3R1Error("pair_acceptance_frame_sha256_mismatch")
    if pair_payload["schema"] != PAIR_SCHEMA or pair_payload["status"] != PAIR_STATUS:
        raise SemanticCageAfesV3R3R1Error("pair_literal_identity_or_status_mismatch")
    if pair_payload["truth_boundary"] != PAIR_TRUTH_BOUNDARY:
        raise SemanticCageAfesV3R3R1Error("pair_literal_truth_boundary_mismatch")
    contract = _exact_row(expected["execution_contract_binding"], "execution_contract_binding")
    if pair_payload["execution_contract_sha256"] != contract["sha256"] or pair_payload["execution_contract_bytes"] != contract["bytes"]:
        raise SemanticCageAfesV3R3R1Error("pair_execution_contract_mismatch")
    if pair_payload["bound_inputs_unchanged_under_native_locks"] is not True:
        raise SemanticCageAfesV3R3R1Error("pair_locked_inputs_not_unchanged")
    if pair_payload["input_snapshot_sha256"] != expected["input_snapshot_sha256"]:
        raise SemanticCageAfesV3R3R1Error("pair_input_snapshot_mismatch")
    pair_runs = pair_payload["runs"]
    if pair_runs != expected["exact_run_metadata"]:
        raise SemanticCageAfesV3R3R1Error("pair_exact_run_metadata_mismatch")
    if len(run_payloads) != 2 or len(run_frame_sha256s) != 2 or len(run_frame_bytes) != 2 or len(run_payload_sha256s) != 2:
        raise SemanticCageAfesV3R3R1Error("pair_requires_exactly_two_runs")
    nonces = (expected["pair_session_nonce"], expected["run_01_nonce"], expected["run_02_nonce"])
    if len(set(nonces)) != 3:
        raise SemanticCageAfesV3R3R1Error("pair_and_run_nonces_not_distinct")

    first_inner = first_inner_sha = first_analysis = topology_digest = None
    for offset, run in enumerate(run_payloads, start=1):
        if type(run) is not dict or set(run) != RUN_KEYS:
            raise SemanticCageAfesV3R3R1Error("run_payload_shape_drift")
        if run["schema"] != RUN_SCHEMA or run["status"] != RUN_STATUS or run["run_number"] != offset:
            raise SemanticCageAfesV3R3R1Error("run_literal_identity_or_status_mismatch")
        if run["truth_boundary"] != RUN_TRUTH_BOUNDARY:
            raise SemanticCageAfesV3R3R1Error("run_literal_truth_boundary_mismatch")
        frame_sha = expected["run_%02d_frame_sha256" % offset]
        payload_sha = expected["run_%02d_payload_sha256" % offset]
        if run_frame_sha256s[offset - 1] != frame_sha or run_payload_sha256s[offset - 1] != payload_sha:
            raise SemanticCageAfesV3R3R1Error("run_canonical_digest_mismatch")
        metadata = pair_runs[offset - 1]
        if type(metadata) is not dict or set(metadata) != RUN_METADATA_KEYS:
            raise SemanticCageAfesV3R3R1Error("run_metadata_shape_drift")
        if metadata["frame_sha256"] != frame_sha or metadata["payload_sha256"] != payload_sha or metadata["frame_bytes"] != run_frame_bytes[offset - 1]:
            raise SemanticCageAfesV3R3R1Error("run_metadata_frame_mismatch")
        run_nonce = expected["run_%02d_nonce" % offset]
        if run["pair_session_nonce"] != expected["pair_session_nonce"] or run["run_nonce"] != run_nonce:
            raise SemanticCageAfesV3R3R1Error("run_nonce_mismatch")
        if metadata["pair_session_nonce"] != run["pair_session_nonce"] or metadata["run_nonce"] != run["run_nonce"]:
            raise SemanticCageAfesV3R3R1Error("run_metadata_nonce_mismatch")
        for key in ("result_pipe_handle", "child_pid", "parent_pid"):
            _integer(run[key], "run_" + key, 1)
        if metadata["pid"] != run["child_pid"] or metadata["exit_code"] != 0:
            raise SemanticCageAfesV3R3R1Error("run_process_metadata_mismatch")
        if run["execution_contract"] != contract:
            raise SemanticCageAfesV3R3R1Error("run_execution_contract_mismatch")
        if run["accepted_afes_v5_config"] != AFES_V5_CONFIG_BINDING or run["accepted_afes_v5_extractor"] != AFES_V5_EXTRACTOR_BINDING:
            raise SemanticCageAfesV3R3R1Error("run_afes_binding_not_frozen_literal")
        inner = run["inner_attempt05_payload"]
        if type(inner) is not dict or set(inner) != INNER_KEYS:
            raise SemanticCageAfesV3R3R1Error("inner_shape_drift")
        if inner["schema"] != INNER_SCHEMA or inner["artifact_kind"] != INNER_ARTIFACT_KIND or inner["status"] != INNER_STATUS:
            raise SemanticCageAfesV3R3R1Error("inner_literal_identity_or_status_mismatch")
        if inner["truth_boundary"] != INNER_TRUTH_BOUNDARY:
            raise SemanticCageAfesV3R3R1Error("inner_literal_truth_boundary_mismatch")
        if inner["config_observed_unsealed_by_parent"] != AFES_V5_CONFIG_BINDING:
            raise SemanticCageAfesV3R3R1Error("inner_config_binding_not_frozen_literal")
        verified = expected["exact_extraction_verified_inputs"]
        if inner["private_execution_dependencies"] != verified["private_execution_dependencies"] or inner["private_source_physical_reads"] != verified["private_source_physical_reads"]:
            raise SemanticCageAfesV3R3R1Error("inner_verified_inputs_mismatch")
        for key in (
            "ambient_project_modules_consumed", "ambient_dataclasses_decorator_consumed",
            "private_modules_inserted_into_sys_modules",
        ):
            if inner[key] != 0:
                raise SemanticCageAfesV3R3R1Error(key + "_not_zero")
        if inner["private_receipt_runtime"] != PRIVATE_RECEIPT_RUNTIME or inner["read_only_guards"] != READ_ONLY_GUARDS:
            raise SemanticCageAfesV3R3R1Error("inner_private_or_read_only_literal_mismatch")
        if inner["foundation_object"] != expected["foundation_object"] or inner["foundation_mesh"] != expected["foundation_mesh"]:
            raise SemanticCageAfesV3R3R1Error("inner_foundation_identity_mismatch")
        analysis = legacy_control.validate_compact_afes_analysis_against_mesh(
            inner["analysis"], source_edges=source_edges, source_faces=source_faces,
            expected=expected,
        )
        current_topology = analysis["topology_sha256"]
        if inner["topology_sealing"] != {
            "prior_sealed_expected_full_normalized_topology_digest_available": False,
            "required_matching_fresh_locked_extractions": 2,
            "this_receipt_alone_is_acceptance": False,
            "measured_full_normalized_topology_sha256": current_topology,
        }:
            raise SemanticCageAfesV3R3R1Error("inner_topology_sealing_mismatch")
        inner_sha = legacy_control.canonical_sha256(dict(inner))
        if metadata["inner_payload_sha256"] != inner_sha or metadata["topology_sha256"] != current_topology:
            raise SemanticCageAfesV3R3R1Error("inner_metadata_mismatch")
        if first_inner is None:
            first_inner, first_inner_sha, first_analysis, topology_digest = inner, inner_sha, analysis, current_topology
        elif inner != first_inner or inner_sha != first_inner_sha or analysis != first_analysis or current_topology != topology_digest:
            raise SemanticCageAfesV3R3R1Error("two_fresh_inner_payloads_do_not_match")
    if pair_payload["matching_inner_payload_sha256"] != first_inner_sha or first_inner_sha != expected["matching_inner_payload_sha256"]:
        raise SemanticCageAfesV3R3R1Error("pair_matching_inner_sha_mismatch")
    if pair_payload["full_normalized_topology_sha256"] != topology_digest or topology_digest != expected["foundation_topology_sha256"]:
        raise SemanticCageAfesV3R3R1Error("pair_topology_sha_mismatch")
    locked = set(first_analysis["locked_vertices"])
    return locked, {
        "pair_schema": PAIR_SCHEMA, "pair_status": PAIR_STATUS,
        "pair_acceptance_frame_sha256": pair_frame_sha256,
        "execution_contract_sha256": contract["sha256"],
        "input_snapshot_sha256": expected["input_snapshot_sha256"],
        "matching_inner_payload_sha256": first_inner_sha,
        "full_normalized_topology_sha256": topology_digest,
        "afes_union_vertex_count": expected["afes_union_count"],
        "afes_union_vertex_sha256": expected["afes_union_sha256"],
        "ring_1_vertex_count": expected["ring_1_count"],
        "ring_1_vertex_sha256": expected["ring_1_sha256"],
        "ring_2_vertex_count": expected["ring_2_count"],
        "ring_2_vertex_sha256": expected["ring_2_sha256"],
        "combined_ring_vertex_count": expected["combined_ring_count"],
        "combined_ring_vertex_sha256": expected["combined_ring_sha256"],
        "locked_vertex_count": expected["locked_vertex_count"],
        "locked_vertex_sha256": expected["locked_vertex_sha256"],
        "fresh_run_count": 2, "three_distinct_pair_and_run_nonces": "YES",
    }


__all__ = [
    "AFES_V5_CONFIG_BINDING", "AFES_V5_EXTRACTOR_BINDING", "EXPECTED_KEYS",
    "INNER_ARTIFACT_KIND", "INNER_KEYS", "INNER_SCHEMA", "INNER_STATUS",
    "INNER_TRUTH_BOUNDARY", "PAIR_KEYS", "PAIR_SCHEMA", "PAIR_STATUS",
    "PAIR_TRUTH_BOUNDARY", "PRIVATE_RECEIPT_RUNTIME", "READ_ONLY_GUARDS",
    "RUN_KEYS", "RUN_METADATA_KEYS", "RUN_SCHEMA", "RUN_STATUS",
    "RUN_TRUTH_BOUNDARY", "SemanticCageAfesV3R3R1Error",
    "require_sealed_expected", "validate_afes_v3r3_pair_bundle",
]
