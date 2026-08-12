from __future__ import annotations

"""Pure AFES-v3r3 evidence adapter for the R25 semantic-cage v4 preparation.

The module has no Blender, filesystem, process, or persistence authority.  It
only authenticates the three already-produced canonical receipt payloads and
reconstructs the AFES/ring lock against caller-supplied live foundation
topology through the frozen Attempt-03 semantic core.
"""

import re
from typing import Any, Mapping, Sequence


class SemanticCageAfesV3R3Error(ValueError):
    pass


HEX64 = re.compile(r"[0-9a-f]{64}")
PLACEHOLDER_PREFIX = "FINAL_"

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


def _hex64(value: object, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise SemanticCageAfesV3R3Error(f"{label}_must_be_64_lowercase_hex")
    return value


def _integer(value: object, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise SemanticCageAfesV3R3Error(f"{label}_invalid")
    return value


def _exact_row(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != {"path", "bytes", "sha256"}:
        raise SemanticCageAfesV3R3Error(f"{label}_row_shape")
    path = value.get("path")
    if not isinstance(path, str) or not path or "\\" in path or path.startswith("/") or ".." in path.split("/"):
        raise SemanticCageAfesV3R3Error(f"{label}_path_invalid")
    _integer(value.get("bytes"), f"{label}_bytes", 1)
    _hex64(value.get("sha256"), f"{label}_sha256")
    return dict(value)


def _contains_unresolved(value: object) -> bool:
    stack = [value]
    while stack:
        current = stack.pop()
        if current is None:
            return True
        if isinstance(current, str) and current.startswith(PLACEHOLDER_PREFIX):
            return True
        if isinstance(current, Mapping):
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return False


def require_sealed_expected(expected: object) -> Mapping[str, Any]:
    if not isinstance(expected, Mapping) or set(expected) != EXPECTED_KEYS:
        raise SemanticCageAfesV3R3Error("expected_pair_and_analysis_shape_drift")
    if _contains_unresolved(expected):
        raise SemanticCageAfesV3R3Error("expected_pair_and_analysis_still_unsealed")
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
    if not isinstance(metadata, list) or len(metadata) != 2:
        raise SemanticCageAfesV3R3Error("exact_run_metadata_requires_two_rows")
    for number, row in enumerate(metadata, start=1):
        if not isinstance(row, Mapping) or set(row) != RUN_METADATA_KEYS or row.get("run_number") != number:
            raise SemanticCageAfesV3R3Error(f"exact_run_metadata_{number:02d}_shape")
    inputs = expected["exact_extraction_verified_inputs"]
    if not isinstance(inputs, Mapping) or set(inputs) != {
        "private_execution_dependencies", "private_source_physical_reads"
    }:
        raise SemanticCageAfesV3R3Error("exact_extraction_verified_inputs_shape")
    return expected


def validate_afes_v3r3_pair_bundle(
    *, pair_payload: Mapping[str, Any], pair_frame_sha256: str,
    run_payloads: Sequence[Mapping[str, Any]], run_frame_sha256s: Sequence[str],
    run_frame_bytes: Sequence[int], run_payload_sha256s: Sequence[str],
    source_edges: Sequence[Sequence[int]], source_faces: Sequence[Sequence[int]],
    expected: Mapping[str, Any], legacy_control: Any,
) -> tuple[set[int], dict[str, object]]:
    """Authenticate one v3r3 pair frame and its two exact fresh run frames."""

    expected = require_sealed_expected(expected)
    if len(run_payloads) != 2 or len(run_frame_sha256s) != 2 or len(run_frame_bytes) != 2 or len(run_payload_sha256s) != 2:
        raise SemanticCageAfesV3R3Error("afes_v3r3_pair_requires_exactly_two_runs")
    if pair_frame_sha256 != expected["pair_acceptance_frame_sha256"]:
        raise SemanticCageAfesV3R3Error("pair_acceptance_frame_sha256_mismatch")
    if not isinstance(pair_payload, Mapping) or set(pair_payload) != PAIR_KEYS:
        raise SemanticCageAfesV3R3Error("pair_payload_shape_drift")
    if pair_payload["schema"] != expected["pair_schema"] or pair_payload["status"] != expected["pair_status"]:
        raise SemanticCageAfesV3R3Error("pair_identity_or_status_mismatch")
    contract = _exact_row(expected["execution_contract_binding"], "execution_contract_binding")
    if pair_payload["execution_contract_sha256"] != contract["sha256"] or pair_payload["execution_contract_bytes"] != contract["bytes"]:
        raise SemanticCageAfesV3R3Error("pair_execution_contract_mismatch")
    if pair_payload["bound_inputs_unchanged_under_native_locks"] is not True:
        raise SemanticCageAfesV3R3Error("pair_did_not_prove_locked_inputs_unchanged")
    if pair_payload["input_snapshot_sha256"] != expected["input_snapshot_sha256"]:
        raise SemanticCageAfesV3R3Error("pair_input_snapshot_mismatch")
    if pair_payload["truth_boundary"] != expected["pair_truth_boundary"]:
        raise SemanticCageAfesV3R3Error("pair_truth_boundary_mismatch")
    pair_runs = pair_payload["runs"]
    if pair_runs != expected["exact_run_metadata"]:
        raise SemanticCageAfesV3R3Error("pair_exact_run_metadata_mismatch")

    expected_nonces = (
        expected["pair_session_nonce"], expected["run_01_nonce"], expected["run_02_nonce"]
    )
    if len(set(expected_nonces)) != 3:
        raise SemanticCageAfesV3R3Error("pair_and_run_nonces_not_three_distinct_values")

    first_inner: Mapping[str, Any] | None = None
    first_inner_sha: str | None = None
    first_analysis: dict[str, object] | None = None
    topology_digest: str | None = None
    for offset, run in enumerate(run_payloads, start=1):
        if not isinstance(run, Mapping) or set(run) != RUN_KEYS:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_payload_shape_drift")
        if run["schema"] != expected["run_schema"] or run["status"] != expected["run_status"] or run["run_number"] != offset:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_identity_or_status_mismatch")
        frame_sha = expected[f"run_{offset:02d}_frame_sha256"]
        payload_sha = expected[f"run_{offset:02d}_payload_sha256"]
        if run_frame_sha256s[offset - 1] != frame_sha or run_payload_sha256s[offset - 1] != payload_sha:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_canonical_digest_mismatch")
        metadata = pair_runs[offset - 1]
        if not isinstance(metadata, Mapping) or set(metadata) != RUN_METADATA_KEYS:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_metadata_shape_drift")
        if metadata["frame_sha256"] != frame_sha or metadata["payload_sha256"] != payload_sha or metadata["frame_bytes"] != run_frame_bytes[offset - 1]:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_metadata_frame_mismatch")
        run_nonce = expected[f"run_{offset:02d}_nonce"]
        if run["pair_session_nonce"] != expected["pair_session_nonce"] or run["run_nonce"] != run_nonce:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_nonce_mismatch")
        if metadata["pair_session_nonce"] != run["pair_session_nonce"] or metadata["run_nonce"] != run["run_nonce"]:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_metadata_nonce_mismatch")
        for key in ("result_pipe_handle", "child_pid", "parent_pid"):
            _integer(run[key], f"run_{offset:02d}_{key}", 1)
        if metadata["pid"] != run["child_pid"] or metadata["exit_code"] != 0:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_process_metadata_mismatch")
        if run["execution_contract"] != contract:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_execution_contract_mismatch")
        if run["accepted_afes_v5_config"] != expected["accepted_afes_v5_config"] or run["accepted_afes_v5_extractor"] != expected["accepted_afes_v5_extractor"]:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_accepted_afes_binding_mismatch")
        if run["truth_boundary"] != expected["run_truth_boundary"]:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_truth_boundary_mismatch")

        inner = run["inner_attempt05_payload"]
        if not isinstance(inner, Mapping) or set(inner) != INNER_KEYS:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_inner_shape_drift")
        if inner["schema"] != expected["inner_schema"] or inner["artifact_kind"] != expected["inner_artifact_kind"] or inner["status"] != expected["inner_status"]:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_inner_identity_or_status_mismatch")
        if inner["config_observed_unsealed_by_parent"] != expected["accepted_afes_v5_config"]:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_inner_config_observation_mismatch")
        verified = expected["exact_extraction_verified_inputs"]
        if inner["private_execution_dependencies"] != verified["private_execution_dependencies"] or inner["private_source_physical_reads"] != verified["private_source_physical_reads"]:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_verified_extraction_inputs_mismatch")
        for key in (
            "ambient_project_modules_consumed", "ambient_dataclasses_decorator_consumed",
            "private_modules_inserted_into_sys_modules",
        ):
            if inner[key] != 0:
                raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_{key}_not_zero")
        if inner["private_receipt_runtime"] != expected["private_receipt_runtime"]:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_private_receipt_runtime_mismatch")
        if inner["foundation_object"] != expected["foundation_object"] or inner["foundation_mesh"] != expected["foundation_mesh"]:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_foundation_identity_mismatch")
        if inner["read_only_guards"] != expected["exact_read_only_guards"] or inner["truth_boundary"] != expected["inner_truth_boundary"]:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_read_only_truth_mismatch")
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
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_topology_sealing_mismatch")
        inner_sha = legacy_control.canonical_sha256(dict(inner))
        if metadata["inner_payload_sha256"] != inner_sha or metadata["topology_sha256"] != current_topology:
            raise SemanticCageAfesV3R3Error(f"run_{offset:02d}_inner_metadata_mismatch")
        if first_inner is None:
            first_inner, first_inner_sha, first_analysis, topology_digest = inner, inner_sha, analysis, current_topology
        elif inner != first_inner or inner_sha != first_inner_sha or analysis != first_analysis or current_topology != topology_digest:
            raise SemanticCageAfesV3R3Error("two_fresh_v3r3_inner_payloads_do_not_match")

    if pair_payload["matching_inner_payload_sha256"] != first_inner_sha or first_inner_sha != expected["matching_inner_payload_sha256"]:
        raise SemanticCageAfesV3R3Error("pair_matching_inner_payload_sha256_mismatch")
    if pair_payload["full_normalized_topology_sha256"] != topology_digest or topology_digest != expected["foundation_topology_sha256"]:
        raise SemanticCageAfesV3R3Error("pair_full_topology_sha256_mismatch")
    if first_analysis is None:
        raise SemanticCageAfesV3R3Error("pair_analysis_missing")
    locked = set(first_analysis["locked_vertices"])
    return locked, {
        "pair_schema": expected["pair_schema"],
        "pair_status": expected["pair_status"],
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
        "fresh_run_count": 2,
        "three_distinct_pair_and_run_nonces": "YES",
    }


__all__ = [
    "EXPECTED_KEYS", "INNER_KEYS", "PAIR_KEYS", "RUN_KEYS", "RUN_METADATA_KEYS",
    "SemanticCageAfesV3R3Error", "require_sealed_expected",
    "validate_afes_v3r3_pair_bundle",
]
