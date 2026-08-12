#!/usr/bin/env python3
"""Pure retained-byte planner/validator for R25 locked-pair Attempt 03r5.

This source has no filesystem, process, handle, lock, Job, outcome, or Blender
authority.  The separately compiled native Windows launcher owns the complete
retained-handle graph and every side effect.  Its retained bootstrap loads this
module privately into one exact restricted globals dictionary, captures the
five pure exports, and then asks the native broker to consume its one-shot authority.
Direct execution is deliberately inert.
"""

CONTRACT_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v3r5.json"
)
AUDIT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution_static_preparation/"
    "attempt_03r5/INDEPENDENT_AUDIT.json"
)
OUTPUT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution/attempt_03r5"
)
OUTCOME_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution_static_preparation/"
    "attempt_03r5/EXECUTION_OUTCOME.receipt.bin"
)
MANIFEST_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution_static_preparation/"
    "attempt_03r5/RETAINED_NATIVE_LOCK_MANIFEST.tsv"
)
CHECKPOINT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution_static_preparation/"
    "attempt_03r5/CHECKPOINT.md"
)
MAX_FRAME_BYTES = 1_048_628
MAX_STDOUT_BYTES = 4 * 1024 * 1024
MAX_STDERR_BYTES = 4 * 1024 * 1024
UINT32_MAX = 4_294_967_295
SIGNED64_MIN = -9_223_372_036_854_775_808
SIGNED64_MAX = 9_223_372_036_854_775_807
NANOMETERS_PER_METER = 1_000_000_000
BLOB_CODEC = "uint32_big_endian_v1"
INDEX_SEMANTIC = "sorted_unique_index_json_sha256_v1"
EDGE_SEMANTIC = "sorted_unique_undirected_edge_pair_json_sha256_v1"
ROUNDING_RULE = "decimal_from_shortest_roundtrip_float_then_half_even_to_integer"
ENVIRONMENT_INHERITED_EXACT_KEYS = ("SYSTEMROOT", "WINDIR", "USERNAME")
MUTABLE_ENVIRONMENT_UNDER_UNIQUE_RUN_ROOT = {
    "TEMP": "temp",
    "TMP": "temp",
    "BLENDER_USER_CONFIG": "blender_config",
    "BLENDER_USER_SCRIPTS": "blender_scripts",
    "BLENDER_USER_DATAFILES": "blender_datafiles",
    "PYTHONPYCACHEPREFIX": "python_pycache",
}
CONSTANT_ENVIRONMENT = {
    "PYTHONNOUSERSITE": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
}
BLENDER_COMMAND_TEMPLATE = [
    "<BLENDER_EXECUTABLE>", "--background", "--factory-startup",
    "--disable-autoexec", "<FOUNDATION_BLEND>", "--python-exit-code", "1",
    "--python", "<EXECUTION_WRAPPER>", "--", "--result-pipe-name",
    "<NATIVE_BROKER_ROOT_PID_AUTHENTICATED_NAMED_PIPE>", "--execution-contract-sha256",
    "<EXPECTED_CONTRACT_SHA256>", "--pair-session-nonce",
    "<FRESH_PAIR_64_HEX_NONCE>", "--run-nonce",
    "<FRESH_RUN_64_HEX_NONCE>", "--run-number", "<ONE_OR_TWO>",
]


class LockedPairV3R5PlanError(RuntimeError):
    """A pure exact-byte planning or validation gate failed closed."""


def _sha256_bytes(value: bytes) -> str:
    return _native_sha256_hex(value)


def _strict_object(value: bytes, label: str) -> dict[str, Any]:
    parsed = _native_parse_strict_json_object(value, label)
    if not isinstance(parsed, dict):
        raise LockedPairV3R5PlanError(f"json_root_not_object:{label}")
    return parsed


def _signed64(value: object, label: str) -> int:
    if type(value) is not int or value < SIGNED64_MIN or value > SIGNED64_MAX:
        raise LockedPairV3R5PlanError("compact_signed64_invalid:" + label)
    return value


def _u32(value: object, label: str) -> int:
    if type(value) is not int or value < 0 or value > UINT32_MAX:
        raise LockedPairV3R5PlanError("compact_u32_invalid:" + label)
    return value


def _normalize_indices(values: object, label: str) -> tuple[int, ...]:
    if type(values) is not tuple:
        raise LockedPairV3R5PlanError("compact_index_tuple_invalid:" + label)
    normalized = tuple(_u32(value, label) for value in values)
    if tuple(sorted(set(normalized))) != normalized:
        raise LockedPairV3R5PlanError("compact_index_order_invalid:" + label)
    return normalized


def _decode_blob(reference: object, record: object) -> tuple[int, ...]:
    if not isinstance(reference, str) or not isinstance(record, dict):
        raise LockedPairV3R5PlanError("compact_blob_identity_invalid")
    values = _native_decode_u32_blob(reference, record)
    if type(values) is not tuple:
        raise LockedPairV3R5PlanError("compact_blob_native_decode_type")
    return tuple(_u32(value, "decoded_blob_value") for value in values)


def _decode_index_reference(
    reference: object, blobs: dict[str, object], referenced: set[str], label: str,
) -> tuple[int, ...]:
    if not isinstance(reference, dict) or set(reference) != {
        "blob_ref", "semantic", "item_count", "semantic_sha256",
    }:
        raise LockedPairV3R5PlanError("compact_index_reference_shape:" + label)
    if reference["semantic"] != INDEX_SEMANTIC:
        raise LockedPairV3R5PlanError("compact_index_semantic:" + label)
    blob_ref = reference["blob_ref"]
    if not isinstance(blob_ref, str) or blob_ref not in blobs:
        raise LockedPairV3R5PlanError("compact_index_blob_absent:" + label)
    values = _normalize_indices(_decode_blob(blob_ref, blobs[blob_ref]), label)
    if _u32(reference["item_count"], label + ".item_count") != len(values):
        raise LockedPairV3R5PlanError("compact_index_count:" + label)
    digest = reference["semantic_sha256"]
    if (
        not isinstance(digest, str)
        or not _native_is_lower_hex64(digest)
        or _native_canonical_json_sha256(list(values)) != digest
    ):
        raise LockedPairV3R5PlanError("compact_index_digest:" + label)
    referenced.add(blob_ref)
    return values


def _decode_edge_reference(
    reference: object, blobs: dict[str, object], referenced: set[str], label: str,
) -> tuple[tuple[int, int], ...]:
    if not isinstance(reference, dict) or set(reference) != {
        "blob_ref", "semantic", "item_count", "semantic_sha256",
    }:
        raise LockedPairV3R5PlanError("compact_edge_reference_shape:" + label)
    if reference["semantic"] != EDGE_SEMANTIC:
        raise LockedPairV3R5PlanError("compact_edge_semantic:" + label)
    blob_ref = reference["blob_ref"]
    if not isinstance(blob_ref, str) or blob_ref not in blobs:
        raise LockedPairV3R5PlanError("compact_edge_blob_absent:" + label)
    flat = _decode_blob(blob_ref, blobs[blob_ref])
    if len(flat) % 2:
        raise LockedPairV3R5PlanError("compact_edge_odd_count:" + label)
    edges = []
    position = 0
    while position < len(flat):
        first = _u32(flat[position], label + ".first")
        second = _u32(flat[position + 1], label + ".second")
        if first >= second:
            raise LockedPairV3R5PlanError("compact_edge_endpoint_order:" + label)
        edges.append((first, second))
        position += 2
    normalized = tuple(edges)
    if tuple(sorted(set(normalized))) != normalized:
        raise LockedPairV3R5PlanError("compact_edge_order:" + label)
    if _u32(reference["item_count"], label + ".item_count") != len(normalized):
        raise LockedPairV3R5PlanError("compact_edge_count:" + label)
    digest = reference["semantic_sha256"]
    if (
        not isinstance(digest, str)
        or not _native_is_lower_hex64(digest)
        or _native_canonical_json_sha256(
            [[edge[0], edge[1]] for edge in normalized]
        ) != digest
    ):
        raise LockedPairV3R5PlanError("compact_edge_digest:" + label)
    referenced.add(blob_ref)
    return normalized


def _validate_compact_afes_analysis(compact: object) -> None:
    if not isinstance(compact, dict) or set(compact) != {
        "whole_mesh", "topology_structure", "groups", "afes_union",
        "transition_rings", "bounds_object_nm", "binary_arrays",
    }:
        raise LockedPairV3R5PlanError("compact_top_level_shape")
    whole = compact["whole_mesh"]
    if not isinstance(whole, dict) or set(whole) != {
        "vertex_count", "edge_count", "face_count", "topology_sha256",
    }:
        raise LockedPairV3R5PlanError("compact_whole_mesh_shape")
    vertex_count = _signed64(whole["vertex_count"], "vertex_count")
    edge_count = _signed64(whole["edge_count"], "edge_count")
    face_count = _signed64(whole["face_count"], "face_count")
    if vertex_count <= 0 or edge_count <= 0 or face_count <= 0:
        raise LockedPairV3R5PlanError("compact_whole_mesh_nonpositive")
    topology_digest = whole["topology_sha256"]
    if not isinstance(topology_digest, str) or not _native_is_lower_hex64(
        topology_digest
    ):
        raise LockedPairV3R5PlanError("compact_topology_digest")
    metric_keys = {
        "connected_component_count", "isolated_vertex_count",
        "boundary_edge_count", "nonmanifold_edge_count", "loose_edge_count",
        "face_boundary_edge_missing_from_mesh_count", "duplicate_face_record_count",
        "transition_ring_loose_edge_incidence_count",
    }
    structure = compact["topology_structure"]
    if not isinstance(structure, dict) or set(structure) != metric_keys | {
        "full_normalized_topology_sha256"
    } or structure["full_normalized_topology_sha256"] != topology_digest:
        raise LockedPairV3R5PlanError("compact_structure_shape_or_digest")
    metrics = {
        key: _signed64(structure[key], "structural_metric." + key)
        for key in metric_keys
    }
    if metrics["connected_component_count"] != 1 or any(
        metrics[key] != 0 for key in metric_keys
        if key != "connected_component_count"
    ):
        raise LockedPairV3R5PlanError("compact_structure_acceptance")

    blobs = compact["binary_arrays"]
    if not isinstance(blobs, dict):
        raise LockedPairV3R5PlanError("compact_blob_table_shape")
    raw_hashes = set()
    for blob_ref in sorted(blobs):
        values = _decode_blob(blob_ref, blobs[blob_ref])
        record = blobs[blob_ref]
        raw_hash = record["raw_sha256"]
        if raw_hash in raw_hashes:
            raise LockedPairV3R5PlanError("compact_duplicate_raw_blob")
        raw_hashes.add(raw_hash)
        if type(values) is not tuple:
            raise LockedPairV3R5PlanError("compact_blob_decode_type")
    referenced = set()
    groups = compact["groups"]
    if not isinstance(groups, dict) or not groups:
        raise LockedPairV3R5PlanError("compact_groups_absent")
    decoded_groups = {}
    for name, row in sorted(groups.items()):
        if not isinstance(name, str) or not name or not isinstance(row, dict) or set(row) != {
            "vertex_indices"
        }:
            raise LockedPairV3R5PlanError("compact_group_shape")
        decoded_groups[name] = _decode_index_reference(
            row["vertex_indices"], blobs, referenced, "group." + name
        )
    union_row = compact["afes_union"]
    if not isinstance(union_row, dict) or set(union_row) != {
        "vertex_indices", "incident_face_indices", "internal_face_indices",
        "primary_connection_edges",
    }:
        raise LockedPairV3R5PlanError("compact_union_shape")
    union = _decode_index_reference(
        union_row["vertex_indices"], blobs, referenced, "afes_union.vertices"
    )
    incident = _decode_index_reference(
        union_row["incident_face_indices"], blobs, referenced, "afes_union.incident_faces"
    )
    internal = _decode_index_reference(
        union_row["internal_face_indices"], blobs, referenced, "afes_union.internal_faces"
    )
    edges = _decode_edge_reference(
        union_row["primary_connection_edges"], blobs, referenced, "afes_union.edges"
    )
    reconstructed_union = tuple(sorted({
        value for values in decoded_groups.values() for value in values
    }))
    if reconstructed_union != union:
        raise LockedPairV3R5PlanError("compact_group_union_mismatch")
    if union and union[-1] >= vertex_count:
        raise LockedPairV3R5PlanError("compact_union_vertex_bound")
    if incident and incident[-1] >= face_count:
        raise LockedPairV3R5PlanError("compact_incident_face_bound")
    if internal and internal[-1] >= face_count:
        raise LockedPairV3R5PlanError("compact_internal_face_bound")
    for edge in edges:
        if edge[0] >= vertex_count or edge[1] >= vertex_count:
            raise LockedPairV3R5PlanError("compact_edge_vertex_bound")

    rings_row = compact["transition_rings"]
    if not isinstance(rings_row, dict) or set(rings_row) != {
        "ring_count", "rings", "combined_vertex_indices", "disjoint_from_afes_union",
    }:
        raise LockedPairV3R5PlanError("compact_rings_shape")
    ring_rows = rings_row["rings"]
    if (
        _u32(rings_row["ring_count"], "transition_ring_count") != 2
        or not isinstance(ring_rows, list) or len(ring_rows) != 2
    ):
        raise LockedPairV3R5PlanError("compact_ring_count")
    rings = []
    for ring_number in (1, 2):
        row = ring_rows[ring_number - 1]
        if not isinstance(row, dict) or set(row) != {"ring_number", "vertex_indices"}:
            raise LockedPairV3R5PlanError("compact_ring_row_shape")
        if _u32(row["ring_number"], "ring_number") != ring_number:
            raise LockedPairV3R5PlanError("compact_ring_order")
        ring = _decode_index_reference(
            row["vertex_indices"], blobs, referenced, "ring." + str(ring_number)
        )
        if ring and ring[-1] >= vertex_count:
            raise LockedPairV3R5PlanError("compact_ring_vertex_bound")
        rings.append(ring)
    if set(rings[0]).intersection(rings[1]):
        raise LockedPairV3R5PlanError("compact_rings_overlap")
    combined = _decode_index_reference(
        rings_row["combined_vertex_indices"], blobs, referenced, "rings.combined"
    )
    if combined != tuple(sorted({value for ring in rings for value in ring})):
        raise LockedPairV3R5PlanError("compact_combined_ring_mismatch")
    if set(union).intersection(combined) or rings_row["disjoint_from_afes_union"] is not True:
        raise LockedPairV3R5PlanError("compact_ring_union_overlap")
    if referenced != set(blobs):
        raise LockedPairV3R5PlanError("compact_unreferenced_blob")

    bounds = compact["bounds_object_nm"]
    if not isinstance(bounds, dict) or set(bounds) != {
        "unit", "integer_units_per_meter", "rounding", "minimum", "maximum",
    } or bounds["unit"] != "nanometer" or bounds[
        "integer_units_per_meter"
    ] != NANOMETERS_PER_METER or bounds["rounding"] != ROUNDING_RULE:
        raise LockedPairV3R5PlanError("compact_bounds_codec")
    for side in ("minimum", "maximum"):
        values = bounds[side]
        if not isinstance(values, list) or len(values) != 3:
            raise LockedPairV3R5PlanError("compact_bounds_shape:" + side)
        for value in values:
            _signed64(value, "bounds." + side)


def _exact_row(row: object, label: str) -> dict[str, object]:
    if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
        raise LockedPairV3R5PlanError(f"invalid_binding:{label}")
    if not isinstance(row["path"], str) or not row["path"]:
        raise LockedPairV3R5PlanError(f"invalid_binding_path:{label}")
    if type(row["bytes"]) is not int or row["bytes"] < 0:
        raise LockedPairV3R5PlanError(f"invalid_binding_bytes:{label}")
    if not isinstance(row["sha256"], str) or not _native_is_lower_hex64(row["sha256"]):
        raise LockedPairV3R5PlanError(f"invalid_binding_sha256:{label}")
    return dict(row)


def _iter_contract_rows(contract: Mapping[str, Any]) -> list[tuple[str, dict[str, object]]]:
    tables: tuple[tuple[str, object, bool], ...] = (
        ("bindings", contract.get("bindings"), False),
        ("afes_v5_transitive_rows", contract.get("afes_v5_transitive_rows"), True),
        (
            "child_runtime_read_closure_completion",
            contract.get("child_runtime_read_closure_completion"), False,
        ),
        (
            "locked_pair_attempt_01_preservation",
            contract.get("locked_pair_attempt_01_preservation"), False,
        ),
        (
            "locked_pair_attempt_02_preservation",
            contract.get("locked_pair_attempt_02_preservation"), False,
        ),
        ("locked_pair_v3r1_preservation", contract.get("locked_pair_v3r1_preservation"), False),
        ("locked_pair_v3r2_preservation", contract.get("locked_pair_v3r2_preservation"), False),
        ("locked_pair_v3r3_preservation", contract.get("locked_pair_v3r3_preservation"), False),
        ("locked_pair_v3r4_preservation", contract.get("locked_pair_v3r4_preservation"), False),
    )
    rows: list[tuple[str, dict[str, object]]] = []
    for table_name, table, nested in tables:
        if not isinstance(table, dict) or not table:
            raise LockedPairV3R5PlanError(f"missing_binding_table:{table_name}")
        if nested:
            for nested_name, nested_table in table.items():
                if not isinstance(nested_table, dict) or not nested_table:
                    raise LockedPairV3R5PlanError(
                        f"missing_nested_binding_table:{table_name}.{nested_name}"
                    )
                for label, row in nested_table.items():
                    compound = f"{table_name}.{nested_name}.{label}"
                    rows.append((compound, _exact_row(row, compound)))
        else:
            for label, row in table.items():
                compound = f"{table_name}.{label}"
                rows.append((compound, _exact_row(row, compound)))
    return rows


def _scope() -> dict[str, bool]:
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


def _process_contract() -> dict[str, object]:
    return {
        "native_launcher_owns_every_side_effect": True,
        "python_controller_is_side_effect_free": True,
        "background": True,
        "factory_startup": True,
        "autoexec_disabled": True,
        "python_exit_code": 1,
        "stdin": "DEVNULL",
        "restricted_environment": True,
        "least_handle_inheritance": True,
        "result_named_pipe_writer_root_pid_authenticated": True,
        "concurrent_bounded_pipe_drain": True,
        "exactly_one_frame_and_eof": True,
        "maximum_frame_bytes": MAX_FRAME_BYTES,
        "maximum_stdout_bytes": MAX_STDOUT_BYTES,
        "maximum_stderr_bytes": MAX_STDERR_BYTES,
        "fresh_pair_64_hex_nonce": True,
        "fresh_distinct_run_64_hex_nonce_per_run": True,
        "process_timeout_seconds": 180,
        "create_suspended": True,
        "job_list_assigned_at_process_creation": True,
        "kill_on_job_close": True,
        "resume_only_after_job_containment": True,
        "terminate_entire_owned_job_on_failure": True,
        "zero_live_owned_processes_before_job_close": True,
        "primary_and_cleanup_failures_recorded_together": True,
        "non_daemon_drains_joined": True,
        "project_modules_imported": False,
        "native_retained_handle_manifest_required": True,
        "retained_exact_bytes_used_for_private_execution": True,
        "shell": False,
        "working_directory": ".",
        "environment_inherited_exact_keys": list(ENVIRONMENT_INHERITED_EXACT_KEYS),
        "environment_exact_key_count": 12,
        "path_omitted_by_design": True,
        "unique_nonce_cache_root_per_run": True,
        "mutable_environment_under_unique_run_root": dict(
            MUTABLE_ENVIRONMENT_UNDER_UNIQUE_RUN_ROOT
        ),
        "constant_environment": dict(CONSTANT_ENVIRONMENT),
        "exact_command_template": list(BLENDER_COMMAND_TEMPLATE),
    }


def _pair_contract() -> dict[str, bool]:
    return {
        "distinct_pair_and_run_nonces": True,
        "exact_authenticated_inner_payload_match": True,
        "exact_full_normalized_topology_digest_match": True,
        "compact_afes_evidence_validation": True,
        "all_bound_inputs_native_locked_before_project_python": True,
        "all_bound_inputs_locked_through_after_snapshot": True,
        "all_bound_inputs_unchanged_after_pair": True,
        "each_raw_frame_persisted_append_only": True,
        "canonical_outcome_reserved_before_any_output_root_operation": True,
        "failure_boundary_enters_immediately_after_reservation": True,
        "canonical_outcome_for_every_supported_post_reservation_exception": True,
        "exactly_one_outcome_slot_consumed": True,
        "fixed_root_second_use_is_rejected": True,
        "fresh_independent_audit_required_before_execution": True,
    }


def _truth_boundary() -> dict[str, bool]:
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


def _bootstrap_contract() -> dict[str, object]:
    return {
        "entrypoint": "tools/run_kira_r25_foundation_afes_locked_pair_bootstrap_v3r5.py",
        "executed_only_from_native_retained_bytes": True,
        "direct_project_file_execution_refused": True,
        "native_broker_module_not_installable_or_importable_outside_launcher": True,
        "native_one_shot_state_consumed_before_first_side_effect": True,
        "controller_receives_no_lock_capability_or_handle": True,
        "controller_exports_retain_one_exact_restricted_globals_dict": True,
        "controller_globals_contain_no_broker_or_module_objects": True,
        "locks_held_through_final_after_snapshot": True,
    }


def _native_launcher_contract() -> dict[str, object]:
    return {
        "trust_root": "OS_MAPPED_PE_FILE_ID_PLUS_OUT_OF_BAND_IMAGE_AND_GRAPH_DIGESTS",
        "source_alone_is_not_an_immutable_trust_root": True,
        "manifest_format": "KIRA_R25_AFES_RETAINED_MANIFEST_V3R5_TAB_V1",
        "manifest_sha256_supplied_out_of_band": True,
        "contract_sha256_supplied_out_of_band": True,
        "audit_sha256_supplied_out_of_band": True,
        "self_image_verified_from_os_module_path": True,
        "all_manifest_rows_opened_with_file_share_read_only": True,
        "all_hashes_computed_from_retained_handles": True,
        "python_lock_or_capability_object_exposed": False,
        "capability_state_machine": [
            "NEW", "GRAPH_LOCKED", "AUDIT_ACCEPTED", "ARMED",
            "CONSUMED", "CLOSED_OR_FAILED",
        ],
    }


def _audit_gate() -> dict[str, object]:
    return {
        "path": AUDIT_RELATIVE_PATH,
        "sha256_supplied_out_of_band": True,
        "schema": "kira.avatar.r25.foundation_afes_locked_pair_independent_audit.v3r5",
        "authoritative_decision_field": "authoritative_decision.decision",
        "required_decision": "ACCEPTED_FOR_ONE_BOUNDED_READ_ONLY_PAIR_ONLY",
        "reject_contradictory_decisions": True,
        "must_bind_exact_subjects": [
            "contract", "native_launcher", "native_launcher_source",
            "retained_manifest", "bootstrap", "controller", "wrapper",
            "static_test", "checkpoint",
        ],
    }


def _outer_truth() -> list[str]:
    return [
        "READ_ONLY_FOUNDATION_DIAGNOSTIC",
        "NO_BLEND_MUTATION_OR_SAVE",
        "NO_RENDER_OR_EXPORT",
        "NO_CANDIDATE_OR_BODY_AUTHORING",
        "THIS_SINGLE_RUN_IS_NOT_ACCEPTANCE",
        "V3R1_REJECTED_AND_NOT_EXECUTED",
        "V3R2_REJECTED_AND_NOT_EXECUTED",
        "V3R3_REJECTED_AND_NOT_EXECUTED",
        "V3R4_REJECTED_AND_NOT_EXECUTED",
    ]


def _verify_retained_rows(
    contract: Mapping[str, Any], retained_by_path: Mapping[str, bytes],
) -> None:
    for compound, row in _iter_contract_rows(contract):
        value = retained_by_path.get(str(row["path"]))
        if not isinstance(value, bytes):
            raise LockedPairV3R5PlanError(f"retained_row_missing:{compound}")
        if len(value) != row["bytes"] or _sha256_bytes(value) != row["sha256"]:
            raise LockedPairV3R5PlanError(f"retained_row_drift:{compound}")


def _validate_audit(
    *, audit_bytes: bytes, contract_bytes: bytes, contract_sha256: str,
    manifest_row: Mapping[str, object], bindings: Mapping[str, Any],
) -> dict[str, Any]:
    audit = _strict_object(audit_bytes, "controller_audit")
    if set(audit) != {"schema", "authoritative_decision", "exact_subjects"}:
        raise LockedPairV3R5PlanError("audit_top_level_schema_drift")
    if audit["schema"] != "kira.avatar.r25.foundation_afes_locked_pair_independent_audit.v3r5":
        raise LockedPairV3R5PlanError("audit_schema_drift")
    if audit["authoritative_decision"] != {
        "decision": "ACCEPTED_FOR_ONE_BOUNDED_READ_ONLY_PAIR_ONLY",
    }:
        raise LockedPairV3R5PlanError("audit_authoritative_decision_rejected")
    if _sha256_bytes(contract_bytes) != contract_sha256:
        raise LockedPairV3R5PlanError("audit_contract_subject_drift")
    retained_manifest = _exact_row(manifest_row, "retained_manifest")
    expected_subjects = {
        "contract": contract_sha256,
        "checkpoint": str(bindings["v3r5_checkpoint"]["sha256"]),
        "retained_manifest": str(retained_manifest["sha256"]),
        "native_launcher": str(bindings["native_launcher_executable"]["sha256"]),
        "native_launcher_source": str(bindings["native_launcher_source"]["sha256"]),
        "static_test": str(bindings["v3r5_static_test"]["sha256"]),
        "bootstrap": str(bindings["trusted_bootstrap"]["sha256"]),
        "controller": str(bindings["parent_controller"]["sha256"]),
        "wrapper": str(bindings["execution_wrapper"]["sha256"]),
    }
    if audit["exact_subjects"] != expected_subjects or any(
        not _native_is_lower_hex64(value) for value in expected_subjects.values()
    ):
        raise LockedPairV3R5PlanError("audit_subject_hash_binding_drift")
    return audit


def _build_execution_plan(
    *, contract_bytes: bytes, audit_bytes: bytes,
    retained_by_path: Mapping[str, bytes], expected_contract_sha256: str,
    accepted_audit_sha256: str, manifest_row: Mapping[str, object],
) -> dict[str, Any]:
    """Build a pure immutable plan from already native-retained byte snapshots."""

    if not _native_is_lower_hex64(expected_contract_sha256 or ""):
        raise LockedPairV3R5PlanError("contract_sha256_invalid")
    if not _native_is_lower_hex64(accepted_audit_sha256 or ""):
        raise LockedPairV3R5PlanError("audit_sha256_invalid")
    if _sha256_bytes(contract_bytes) != expected_contract_sha256:
        raise LockedPairV3R5PlanError("contract_sha256_mismatch")
    if _sha256_bytes(audit_bytes) != accepted_audit_sha256:
        raise LockedPairV3R5PlanError("audit_sha256_mismatch")
    contract = _strict_object(contract_bytes, "execution_contract")
    expected_keys = {
        "schema", "attempt_id", "status", "scope", "authorization_basis",
        "repair_boundaries", "bindings", "afes_v5_transitive_rows",
        "child_runtime_read_closure_completion",
        "afes_v5_exact_contract_sections", "accepted_afes_v5_audit",
        "locked_pair_attempt_01_preservation", "locked_pair_attempt_02_preservation",
        "locked_pair_v3r1_preservation", "locked_pair_v3r2_preservation",
        "locked_pair_v3r3_preservation", "locked_pair_v3r4_preservation",
        "process_contract", "trusted_bootstrap_contract", "native_launcher_contract",
        "controller_audit_gate", "external_native_manifest_gate",
        "required_fresh_run_count", "pair_acceptance", "append_only_output_root",
        "execution_outcome_relative_path", "truth_boundary",
    }
    if set(contract) != expected_keys:
        raise LockedPairV3R5PlanError("contract_top_level_schema_drift")
    if contract["schema"] != "kira.avatar.r25.foundation_afes_locked_pair_execution.v3r5":
        raise LockedPairV3R5PlanError("contract_schema_drift")
    if contract["attempt_id"] != "attempt_03r5" or contract["status"] != (
        "PENDING_FRESH_INDEPENDENT_AUDIT_READ_ONLY_DIAGNOSTIC_PAIR_ONLY"
    ):
        raise LockedPairV3R5PlanError("contract_identity_drift")
    if contract["scope"] != _scope():
        raise LockedPairV3R5PlanError("contract_scope_drift")
    if contract["process_contract"] != _process_contract():
        raise LockedPairV3R5PlanError("process_contract_drift")
    if contract["pair_acceptance"] != _pair_contract() or contract[
        "required_fresh_run_count"
    ] != 2:
        raise LockedPairV3R5PlanError("pair_contract_drift")
    if contract["truth_boundary"] != _truth_boundary():
        raise LockedPairV3R5PlanError("truth_boundary_drift")
    if contract["trusted_bootstrap_contract"] != _bootstrap_contract():
        raise LockedPairV3R5PlanError("bootstrap_contract_drift")
    if contract["native_launcher_contract"] != _native_launcher_contract():
        raise LockedPairV3R5PlanError("native_launcher_contract_drift")
    if contract["controller_audit_gate"] != _audit_gate():
        raise LockedPairV3R5PlanError("audit_gate_drift")
    if contract["append_only_output_root"] != OUTPUT_RELATIVE_PATH or contract[
        "execution_outcome_relative_path"
    ] != OUTCOME_RELATIVE_PATH:
        raise LockedPairV3R5PlanError("append_only_path_drift")
    gate = contract["external_native_manifest_gate"]
    if gate != {
        "path": MANIFEST_RELATIVE_PATH,
        "sha256_supplied_out_of_band": True,
        "manifest_not_self_bound_by_contract_to_avoid_hash_cycle": True,
        "fresh_audit_must_bind_exact_manifest": True,
    }:
        raise LockedPairV3R5PlanError("manifest_gate_drift")
    bindings = contract["bindings"]
    required_new = {
        "python_runtime_dll", "retained_stdlib_zip",
        "native_launcher_executable", "native_launcher_source", "trusted_bootstrap",
        "parent_controller", "execution_wrapper", "v3r5_static_test", "v3r5_checkpoint",
        "locked_pair_v3r2_contract", "locked_pair_v3r2_wrapper",
        "locked_pair_v3r2_controller", "locked_pair_v3r2_bootstrap",
        "locked_pair_v3r2_test", "locked_pair_v3r2_checkpoint",
        "locked_pair_v3r2_rejection_audit",
        "locked_pair_v3r4_contract", "locked_pair_v3r4_wrapper",
        "locked_pair_v3r4_controller", "locked_pair_v3r4_bootstrap",
        "locked_pair_v3r4_test", "locked_pair_v3r4_checkpoint",
        "locked_pair_v3r4_retained_manifest", "locked_pair_v3r4_native_launcher",
        "locked_pair_v3r4_native_source", "locked_pair_v3r4_rejection_audit",
    }
    if not isinstance(bindings, dict) or not required_new.issubset(bindings):
        raise LockedPairV3R5PlanError("required_v3r5_binding_missing")
    _verify_retained_rows(contract, retained_by_path)
    v5 = _strict_object(
        retained_by_path[str(bindings["afes_v5_config"]["path"])], "afes_v5_config"
    )
    transitive = contract["afes_v5_transitive_rows"]
    if set(transitive) != {
        "bindings", "attempt_01_preservation", "attempt_02_preservation",
        "attempt_03_preservation", "attempt_04_preservation",
    } or any(v5.get(key) != value for key, value in transitive.items()):
        raise LockedPairV3R5PlanError("afes_v5_transitive_content_drift")
    v2_row = transitive["attempt_02_preservation"]["config"]
    v2 = _strict_object(retained_by_path[str(v2_row["path"])], "recursive_v2_config")
    completion_labels = (
        "r23_preflight_config", "r23_preflight_attempt_04", "foundation_qualification",
        "foundation_topology_audit", "foundation_relationship_audit",
    )
    if contract["child_runtime_read_closure_completion"] != {
        label: v2["bindings"][label] for label in completion_labels
    }:
        raise LockedPairV3R5PlanError("recursive_v2_closure_drift")
    if contract["locked_pair_v3r2_preservation"] != {
        "contract": bindings["locked_pair_v3r2_contract"],
        "wrapper": bindings["locked_pair_v3r2_wrapper"],
        "controller": bindings["locked_pair_v3r2_controller"],
        "bootstrap": bindings["locked_pair_v3r2_bootstrap"],
        "test": bindings["locked_pair_v3r2_test"],
        "checkpoint": bindings["locked_pair_v3r2_checkpoint"],
        "rejection_audit": bindings["locked_pair_v3r2_rejection_audit"],
    }:
        raise LockedPairV3R5PlanError("v3r2_preservation_drift")
    if contract["locked_pair_v3r4_preservation"] != {
        "contract": bindings["locked_pair_v3r4_contract"],
        "wrapper": bindings["locked_pair_v3r4_wrapper"],
        "controller": bindings["locked_pair_v3r4_controller"],
        "bootstrap": bindings["locked_pair_v3r4_bootstrap"],
        "test": bindings["locked_pair_v3r4_test"],
        "checkpoint": bindings["locked_pair_v3r4_checkpoint"],
        "retained_manifest": bindings["locked_pair_v3r4_retained_manifest"],
        "native_launcher": bindings["locked_pair_v3r4_native_launcher"],
        "native_launcher_source": bindings["locked_pair_v3r4_native_source"],
        "rejection_audit": bindings["locked_pair_v3r4_rejection_audit"],
    }:
        raise LockedPairV3R5PlanError("v3r4_preservation_drift")
    accepted = contract["accepted_afes_v5_audit"]
    if accepted != {
        "decision": "ACCEPTED_FOR_STATIC_PREPARATION_ONLY",
        "audit_sha256": bindings["afes_v5_independent_audit"]["sha256"],
        "audit_required_again_for_locked_pair_attempt03r5": True,
    }:
        raise LockedPairV3R5PlanError("accepted_afes_v5_audit_drift")
    _validate_audit(
        audit_bytes=audit_bytes, contract_bytes=contract_bytes,
        contract_sha256=expected_contract_sha256, manifest_row=manifest_row,
        bindings=bindings,
    )
    return {
        "schema": "kira.avatar.r25.foundation_afes_locked_pair_native_plan.v3r5",
        "contract_sha256": expected_contract_sha256,
        "contract_bytes": len(contract_bytes),
        "blender_executable": bindings["blender_executable"]["path"],
        "foundation_blend": bindings["foundation_blend"]["path"],
        "execution_wrapper": bindings["execution_wrapper"]["path"],
        "output_relative_path": OUTPUT_RELATIVE_PATH,
        "outcome_relative_path": OUTCOME_RELATIVE_PATH,
        "process_contract": _process_contract(),
        "outer_truth_boundary": _outer_truth(),
        "contract": contract,
        "v5": v5,
        "v2": v2,
    }


def _validate_child_payload(
    *, payload: object, run_number: int, pair_session_nonce: str,
    run_nonce: str, result_pipe_name: str, child_pid: int, parent_pid: int,
    plan: Mapping[str, Any],
) -> tuple[Mapping[str, Any], str]:
    contract = plan["contract"]
    v5 = plan["v5"]
    v2 = plan["v2"]
    if not isinstance(payload, dict) or set(payload) != {
        "schema", "status", "execution_contract", "accepted_afes_v5_config",
        "accepted_afes_v5_extractor", "pair_session_nonce", "run_nonce",
        "run_number", "result_pipe_name", "child_pid", "parent_pid",
        "inner_attempt05_payload", "truth_boundary",
    }:
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_payload_shape_mismatch")
    if payload["schema"] != "kira.avatar.r25.foundation_afes_locked_extraction_run.v3r5":
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_schema_mismatch")
    if payload["status"] != "READ_ONLY_EXTRACTION_COMPLETE_PENDING_PAIR_MATCH":
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_status_mismatch")
    if (
        payload["pair_session_nonce"] != pair_session_nonce
        or payload["run_nonce"] != run_nonce
        or payload["run_number"] != run_number
        or payload["result_pipe_name"] != result_pipe_name
        or payload["child_pid"] != child_pid
        or payload["parent_pid"] != parent_pid
    ):
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_session_mismatch")
    if payload["execution_contract"] != {
        "path": CONTRACT_RELATIVE_PATH,
        "bytes": plan["contract_bytes"],
        "sha256": plan["contract_sha256"],
    }:
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_contract_mismatch")
    if payload["accepted_afes_v5_config"] != contract["bindings"]["afes_v5_config"]:
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_accepted_config_mismatch")
    if payload["accepted_afes_v5_extractor"] != contract["bindings"]["afes_v5_extractor"]:
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_accepted_extractor_mismatch")
    if payload["truth_boundary"] != _outer_truth():
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_outer_truth_mismatch")
    inner = payload["inner_attempt05_payload"]
    if not isinstance(inner, dict) or set(inner) != {
        "schema", "artifact_kind", "status", "config_observed_unsealed_by_parent",
        "private_execution_dependencies", "private_source_physical_reads",
        "ambient_project_modules_consumed", "ambient_dataclasses_decorator_consumed",
        "private_modules_inserted_into_sys_modules", "private_receipt_runtime",
        "foundation_object", "foundation_mesh", "analysis", "topology_sealing",
        "read_only_guards", "truth_boundary",
    }:
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_inner_shape_mismatch")
    if inner["schema"] != "kira.avatar.r25.foundation_afes_transition_diagnostic.v5" or (
        inner["artifact_kind"] != "READ_ONLY_PRIVATE_EXACT_BYTE_AFES_DIAGNOSTIC"
    ) or inner["status"] != "EXTRACTED_UNSEALED_REQUIRES_MATCHING_FRESH_LOCKED_RUN":
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_inner_status_mismatch")
    if inner["config_observed_unsealed_by_parent"] != contract["bindings"]["afes_v5_config"]:
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_inner_config_mismatch")
    expected_graph = {
        key: v5["bindings"][key] for key in (
            "attempt_01_topology_core_execution_dependency",
            "attempt_02_hardening_core_execution_dependency",
            "attempt_03_hardening_core_execution_dependency",
            "canonical_receipt_helper",
        )
    }
    if inner["private_execution_dependencies"] != expected_graph:
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_private_graph_mismatch")
    source_keys = (
        "attempt_05_private_loader_core",
        "attempt_01_topology_core_execution_dependency",
        "attempt_02_hardening_core_execution_dependency",
        "attempt_03_hardening_core_execution_dependency",
        "canonical_receipt_helper", "attempt_05_extractor",
    )
    expected_reads = [
        {
            "path": v5["bindings"][key]["path"], "physical_read_count": 1,
            "bytes": v5["bindings"][key]["bytes"],
            "sha256": v5["bindings"][key]["sha256"],
        }
        for key in sorted(source_keys, key=lambda item: v5["bindings"][item]["path"])
    ]
    if inner["private_source_physical_reads"] != expected_reads:
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_private_reads_mismatch")
    if any(inner[key] != 0 for key in (
        "ambient_project_modules_consumed", "ambient_dataclasses_decorator_consumed",
        "private_modules_inserted_into_sys_modules",
    )):
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_private_truth_mismatch")
    if inner["private_receipt_runtime"] != {
        "receipt_module_name": "_kira_private_canonical_receipt_attempt05",
        "decoded_receipt_class_module": "_kira_private_canonical_receipt_attempt05",
        "dataclass_shim_module_name": "_kira_private_dataclass_shim_attempt05",
        "receipt_or_shim_aliases_ambient_sys_modules": False,
    }:
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_receipt_runtime_mismatch")
    foundation = v2["foundation_contract"]
    if inner["foundation_object"] != foundation["object_name"] or inner[
        "foundation_mesh"
    ] != foundation["mesh_name"]:
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_foundation_mismatch")
    analysis = inner["analysis"]
    _validate_compact_afes_analysis(analysis)
    topology_sha256 = analysis["topology_structure"]["full_normalized_topology_sha256"]
    if inner["topology_sealing"] != {
        "prior_sealed_expected_full_normalized_topology_digest_available": False,
        "required_matching_fresh_locked_extractions": 2,
        "this_receipt_alone_is_acceptance": False,
        "measured_full_normalized_topology_sha256": topology_sha256,
    }:
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_topology_sealing_mismatch")
    if inner["read_only_guards"] != {
        "blend_loaded_exactly": True, "blend_clean_before": True,
        "blend_clean_after": True, "data_block_inventory_unchanged": True,
        "operator_calls_by_this_extractor": 0, "edit_calls_by_this_extractor": 0,
        "persistence_calls_by_this_extractor": 0,
        "path_result_writes_by_this_extractor": 0,
    } or inner["truth_boundary"] != v5["truth_boundary"]:
        raise LockedPairV3R5PlanError(f"run_{run_number:02d}_read_only_truth_mismatch")
    return inner, str(topology_sha256)


def _compare_pair(
    first_inner: Mapping[str, Any], first_topology: str,
    second_inner: Mapping[str, Any], second_topology: str,
) -> None:
    if first_inner != second_inner:
        raise LockedPairV3R5PlanError("fresh_locked_inner_payloads_do_not_match")
    if first_topology != second_topology:
        raise LockedPairV3R5PlanError("fresh_locked_topology_digests_do_not_match")


def _success_payload(
    *, plan: Mapping[str, Any], run_metadata: Sequence[Mapping[str, Any]],
    snapshot_sha256: str,
) -> dict[str, Any]:
    if len(run_metadata) != 2:
        raise LockedPairV3R5PlanError("success_requires_exact_pair")
    return {
        "schema": "kira.avatar.r25.foundation_afes_locked_pair_acceptance.v3r5",
        "status": "AFES_AND_TRANSITION_RINGS_EXTRACTED_READ_ONLY_PAIR_MATCHED",
        "execution_contract_sha256": plan["contract_sha256"],
        "execution_contract_bytes": plan["contract_bytes"],
        "bound_inputs_unchanged_under_native_locks": True,
        "input_snapshot_sha256": snapshot_sha256,
        "runs": list(run_metadata),
        "matching_inner_payload_sha256": run_metadata[0]["inner_payload_sha256"],
        "full_normalized_topology_sha256": run_metadata[0]["topology_sha256"],
        "truth_boundary": [
            "READ_ONLY_DIAGNOSTIC_PAIR_ONLY", "NO_BLEND_MUTATION_OR_SAVE",
            "NO_RENDER_EXPORT_OR_PATH_RESULT", "NO_BODY_CANDIDATE",
            "NO_AUTHORING_OR_RUNTIME_AUTHORITY", "V3R1_REJECTED_AND_NOT_EXECUTED",
            "V3R2_REJECTED_AND_NOT_EXECUTED", "V3R3_REJECTED_AND_NOT_EXECUTED",
            "V3R4_REJECTED_AND_NOT_EXECUTED",
        ],
    }


def _failure_payload(
    *, contract_sha256: str, stage: str, primary: BaseException,
    cleanup_errors: Sequence[str],
) -> dict[str, Any]:
    return {
        "schema": "kira.avatar.r25.foundation_afes_locked_pair_failure.v3r5",
        "status": "FAILED_APPEND_ONLY_NO_BODY_AUTHORITY",
        "stage": stage,
        "primary_failure_type": type(primary).__name__,
        "primary_failure": str(primary),
        "cleanup_errors": list(cleanup_errors),
        "execution_contract_sha256": contract_sha256,
    }


CONTROLLER_EXPORTED_CALLS = (
    "_build_execution_plan", "_validate_child_payload", "_compare_pair",
    "_success_payload", "_failure_payload",
)
