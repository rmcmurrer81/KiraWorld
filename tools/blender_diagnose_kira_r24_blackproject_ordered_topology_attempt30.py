"""Hash-bound Attempt 30 ordered-topology source-ring diagnostic wrapper.

This wrapper derives the sealed Attempt 28 read-only mapper. It replaces only
the over-strict coordinate-coincidence identity boundary with exact ordered
mesh/topology identity plus a bounded numerical sanity check. Blender remains
lazy and is never imported during static validation.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260808"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT30_CONFIG.json"
)
ATTEMPT28_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260808"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT28_CONFIG.json"
)
ATTEMPT28_WORKER = (
    ROOT
    / "tools"
    / "blender_diagnose_kira_r24_blackproject_replacement_boundary_attempt28.py"
)
EXPECTED_CONFIG_SHA256 = "f040e298af2158391d9818139f5a861d36d3ef121c91d168adce3a10b499743c"
EXPECTED_ATTEMPT28_CONFIG_SHA256 = "08ab7d73637d41accc10a3e52058e9a1e0b3b3bafcd8b009649881d0e0af7a11"
EXPECTED_ATTEMPT28_WORKER_SHA256 = "ea2b14773a56f955b7e68e756d11519f8abb8653e983b70285e5fd416af6e521"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def project_path(value: str) -> Path:
    path = (ROOT / value).resolve(strict=True)
    root = ROOT.resolve()
    if root != path and root not in path.parents:
        raise RuntimeError(f"Attempt 30 binding escapes project: {value}")
    return path


def load_overlay(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 30 requires the exact sealed overlay path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 30 config hash drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_overlay(config)
    return config


def validate_overlay(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_30"
        or config.get("status") != "STATIC_DIAGNOSTIC_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 30 identity drifted")
    scope = config["scope"]
    required_true = (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "diagnostic_only",
        "read_existing_source_mesh_allowed_during_later_reviewed_run",
        "in_memory_scene_open_allowed_during_later_reviewed_run",
        "ordered_topology_identity_required_before_mapping",
        "bounded_numeric_sanity_required_before_mapping",
        "boundary_candidate_mapping_allowed",
    )
    forbidden = (
        "body_geometry_mutation_allowed",
        "patch_geometry_mutation_allowed",
        "blender_datablock_transform_assignment_allowed",
        "triangulation_allowed",
        "reconstruction_allowed",
        "render_allowed",
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "assignment_allowed",
        "publication_allowed",
        "boundary_or_seam_movement_allowed",
        "arbitrary_new_coordinate_allowed",
        "quality_gate_reduction_allowed",
        "generic_hole_fill_allowed",
        "sanitation_weakening_allowed",
    )
    if not all(bool(scope[name]) for name in required_true):
        raise RuntimeError("Attempt 30 lost a required read-only mapping gate")
    if any(bool(scope[name]) for name in forbidden):
        raise RuntimeError("Attempt 30 permits a forbidden operation")

    hard = config["unchanged_hard_gates"]
    if (
        float(hard["minimum_new_triangle_angle_degrees"]) != 12.0
        or float(hard["minimum_new_triangle_world_area_m2"]) != 1.0e-10
        or int(hard["global_seam_vertex_count"]) != 34
        or float(hard["global_seam_coordinate_delta_m"]) != 0.0
        or bool(hard["save_allowed_without_owner_visual_acceptance"])
    ):
        raise RuntimeError("Attempt 30 hard gate drifted")

    contract = config["source_identity_contract"]
    expected_ids = [
        4, 7, 90, 426, 422, 419, 418, 508,
        506, 504, 525, 529, 530, 531, 676, 689,
        690, 687, 535, 534, 407, 429, 428, 425,
        421, 420, 423, 427, 91, 86, 5, 85,
    ]
    if list(contract["ordered_cycle_mesh_vertex_indices"]) != expected_ids:
        raise RuntimeError("Attempt 30 ordered source cycle drifted")
    if canonical_sha256(expected_ids) != contract["ordered_cycle_mesh_vertex_indices_sha256"]:
        raise RuntimeError("Attempt 30 ordered source cycle hash drifted")
    topology_record = {
        key: contract[key]
        for key in (
            "object_name",
            "mesh_name",
            "current_domain_face_count",
            "current_domain_face_sha256",
            "current_domain_vertex_count",
            "current_domain_vertex_sha256",
            "current_boundary_edge_count",
            "current_boundary_edge_sha256",
            "ordered_cycle_mesh_vertex_indices",
            "ordered_cycle_mesh_vertex_indices_sha256",
        )
    }
    if canonical_sha256(topology_record) != contract["composite_topology_record_sha256"]:
        raise RuntimeError("Attempt 30 composite topology contract drifted")
    if (
        bool(contract["coordinate_coincidence_is_primary_identity"])
        or contract["required_alignment_orientation"] != "forward"
        or int(contract["required_alignment_rotation"]) != 0
        or int(contract["expected_coordinate_count"]) != 32
        or float(contract["maximum_numeric_sanity_xy_distance_m"]) != 5.0e-10
        or float(contract["maximum_numeric_sanity_rms_xy_distance_m"]) != 2.0e-10
        or float(contract["maximum_local_chart_boundary_deviation_m"]) != 0.0011
        or bool(contract["numeric_sanity_is_geometry_quality_gate"])
    ):
        raise RuntimeError("Attempt 30 identity or sanity boundary drifted")
    diagnosis = config["attempt29_diagnosis"]
    if (
        not bool(diagnosis["direct_chart_order_is_exact_forward_rotation_zero"])
        or float(diagnosis["direct_chart_maximum_xy_distance_m"])
        != 2.404035467760971e-10
        or float(diagnosis["direct_chart_rms_xy_distance_m"])
        != 6.953615659543396e-11
        or diagnosis["alternate_body_matrix_classification"]
        != "CHART_MISMATCH_NOT_EXPLAINED_BY_BODY_MATRIX_ALONE"
        or bool(diagnosis["alternate_body_matrix_is_valid_source_contract"])
    ):
        raise RuntimeError("Attempt 30 preserved Attempt 29 diagnosis drifted")


def verify_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(record["path"]))
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(record["bytes"]):
        raise RuntimeError(f"Attempt 30 bound byte count drifted: {name}")
    if digest != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 30 bound hash drifted: {name}: {digest}")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": size,
        "sha256": digest,
    }


def verify_overlay_bindings(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    records = {
        name: verify_record(name, record)
        for name, record in config["bindings"].items()
    }
    records["proposal"] = verify_record("proposal", config["proposal"])
    for key in ("preserved_attempt28_package", "preserved_attempt29_package"):
        preserved = config[key]
        rows = [records[name] for name in preserved["binding_names"]]
        if len(rows) != int(preserved["file_count"]):
            raise RuntimeError(f"Attempt 30 {key} file count drifted")
        if sum(int(row["bytes"]) for row in rows) != int(preserved["total_bytes"]):
            raise RuntimeError(f"Attempt 30 {key} byte total drifted")
    if records["attempt28_worker"]["sha256"] != EXPECTED_ATTEMPT28_WORKER_SHA256:
        raise RuntimeError("Attempt 30 provider worker binding disagrees")
    if records["attempt28_config"]["sha256"] != EXPECTED_ATTEMPT28_CONFIG_SHA256:
        raise RuntimeError("Attempt 30 provider config binding disagrees")

    diagnostic = json.loads(
        project_path(config["bindings"]["attempt29_diagnostic"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    direct = diagnostic["attempt29_direct_chart"]
    alignment = direct["alignment"]
    contract = config["source_identity_contract"]
    truth = diagnostic["truth"]
    if (
        diagnostic.get("attempt_id") != "attempt_29"
        or diagnostic.get("classification")
        != "CHART_MISMATCH_NOT_EXPLAINED_BY_BODY_MATRIX_ALONE"
        or list(diagnostic["boundary_cycle_mesh_vertex_indices"])
        != list(contract["ordered_cycle_mesh_vertex_indices"])
        or diagnostic["boundary_cycle_mesh_vertex_indices_sha256"]
        != contract["ordered_cycle_mesh_vertex_indices_sha256"]
        or alignment["orientation"] != "forward"
        or int(alignment["rotation"]) != 0
        or list(alignment["capture_source_index_to_mesh_vertex_index"])
        != list(contract["ordered_cycle_mesh_vertex_indices"])
        or float(direct["maximum_distance_m"])
        != float(contract["attempt29_observed_maximum_xy_distance_m"])
        or float(direct["rms_distance_m"])
        != float(contract["attempt29_observed_rms_xy_distance_m"])
        or diagnostic["expected_attempt27_xy_sha256"]
        != contract["expected_attempt27_xy_sha256"]
        or any(bool(truth[name]) for name in (
            "boundary_candidate_mapping_reached",
            "triangulation_performed",
            "mesh_mutated",
            "body_mutated",
            "blender_datablock_transform_assigned",
            "render_reached",
            "blend_saved",
            "runtime_changed",
            "repair_applied",
        ))
    ):
        raise RuntimeError("Attempt 30 is not bound to the exact Attempt 29 evidence")
    return records


def build_runtime_config(overlay: Mapping[str, Any]) -> dict[str, Any]:
    if sha256_file(ATTEMPT28_CONFIG) != EXPECTED_ATTEMPT28_CONFIG_SHA256:
        raise RuntimeError("Attempt 28 config changed before Attempt 30 derivation")
    base = json.loads(ATTEMPT28_CONFIG.read_text(encoding="utf-8"))
    runtime = json.loads(json.dumps(base))
    for key in ("attempt_id", "status", "mode", "scope", "output", "proposal", "truth"):
        runtime[key] = json.loads(json.dumps(overlay[key]))
    runtime["unchanged_hard_gates"] = json.loads(
        json.dumps(overlay["unchanged_hard_gates"])
    )
    runtime["source_identity_contract"] = json.loads(
        json.dumps(overlay["source_identity_contract"])
    )
    runtime["attempt29_diagnosis"] = json.loads(
        json.dumps(overlay["attempt29_diagnosis"])
    )
    runtime["bindings"].update(json.loads(json.dumps(overlay["bindings"])))
    return runtime


ATTEMPT30_IDENTITY_HELPER = r'''
def attempt30_source_identity_evidence(
    config: Mapping[str, Any],
    obj: Any,
    current_row: Mapping[str, Any],
    capture: Mapping[str, Any],
    captured_xy: Sequence[Sequence[float]],
    alignment: Mapping[str, Any],
) -> dict[str, Any]:
    contract = config["source_identity_contract"]
    expected_ids = [int(value) for value in contract["ordered_cycle_mesh_vertex_indices"]]
    current_ids = [int(value) for value in current_row["boundary_cycle_mesh_vertex_indices"]]
    aligned_ids = [
        int(value) for value in alignment["capture_source_index_to_mesh_vertex_index"]
    ]
    capture_indices = [
        int(row["boundary_source_index"])
        for row in capture["fixed_pslg"]["boundary_coordinates"]
    ]
    current_xy = current_row["projected_boundary_xy_m"]
    topology_record = {
        "object_name": str(obj.name),
        "mesh_name": str(obj.data.name),
        "current_domain_face_count": int(current_row["face_count"]),
        "current_domain_face_sha256": current_row["face_indices_sha256"],
        "current_domain_vertex_count": int(current_row["vertex_count"]),
        "current_domain_vertex_sha256": current_row["vertex_indices_sha256"],
        "current_boundary_edge_count": int(current_row["boundary_edge_count"]),
        "current_boundary_edge_sha256": current_row["boundary_edge_indices_sha256"],
        "ordered_cycle_mesh_vertex_indices": current_ids,
        "ordered_cycle_mesh_vertex_indices_sha256": canonical_sha256(current_ids),
    }
    finite_coordinates = all(
        math.isfinite(float(value))
        for points in (captured_xy, current_xy)
        for point in points
        for value in point
    )
    checks = {
        "exact_object_name": topology_record["object_name"] == contract["object_name"],
        "exact_mesh_name": topology_record["mesh_name"] == contract["mesh_name"],
        "exact_domain_face_count": topology_record["current_domain_face_count"] == int(contract["current_domain_face_count"]),
        "exact_domain_face_hash": topology_record["current_domain_face_sha256"] == contract["current_domain_face_sha256"],
        "exact_domain_vertex_count": topology_record["current_domain_vertex_count"] == int(contract["current_domain_vertex_count"]),
        "exact_domain_vertex_hash": topology_record["current_domain_vertex_sha256"] == contract["current_domain_vertex_sha256"],
        "exact_boundary_edge_count": topology_record["current_boundary_edge_count"] == int(contract["current_boundary_edge_count"]),
        "exact_boundary_edge_hash": topology_record["current_boundary_edge_sha256"] == contract["current_boundary_edge_sha256"],
        "exact_ordered_boundary_cycle": current_ids == expected_ids,
        "exact_ordered_boundary_cycle_hash": topology_record["ordered_cycle_mesh_vertex_indices_sha256"] == contract["ordered_cycle_mesh_vertex_indices_sha256"],
        "exact_composite_topology_hash": canonical_sha256(topology_record) == contract["composite_topology_record_sha256"],
        "exact_forward_alignment": alignment["orientation"] == contract["required_alignment_orientation"],
        "exact_zero_rotation": int(alignment["rotation"]) == int(contract["required_alignment_rotation"]),
        "exact_capture_to_mesh_order": aligned_ids == expected_ids,
        "exact_capture_source_indices": capture_indices == list(range(int(contract["expected_coordinate_count"]))),
        "exact_coordinate_counts": len(captured_xy) == len(current_xy) == int(contract["expected_coordinate_count"]),
        "exact_expected_coordinate_hash": canonical_sha256(captured_xy) == contract["expected_attempt27_xy_sha256"],
        "all_coordinates_finite": finite_coordinates,
        "maximum_xy_numeric_sanity": float(alignment["maximum_xy_distance_m"]) <= float(contract["maximum_numeric_sanity_xy_distance_m"]),
        "rms_xy_numeric_sanity": float(alignment["rms_xy_distance_m"]) <= float(contract["maximum_numeric_sanity_rms_xy_distance_m"]),
        "unchanged_local_chart_quality_gate": float(current_row["chart"]["maximum_absolute_boundary_deviation_m"]) <= float(contract["maximum_local_chart_boundary_deviation_m"]),
    }
    evidence = {
        "identity_basis": contract["identity_basis"],
        "topology_record": topology_record,
        "composite_topology_record_sha256": canonical_sha256(topology_record),
        "capture_source_indices": capture_indices,
        "capture_to_mesh_order": aligned_ids,
        "expected_coordinate_sha256": canonical_sha256(captured_xy),
        "computed_coordinate_sha256": canonical_sha256(current_xy),
        "alignment": dict(alignment),
        "numeric_sanity_bounds_m": {
            "maximum_xy": float(contract["maximum_numeric_sanity_xy_distance_m"]),
            "rms_xy": float(contract["maximum_numeric_sanity_rms_xy_distance_m"]),
        },
        "checks": checks,
        "all_identity_and_sanity_checks_pass": all(checks.values()),
        "coordinate_coincidence_used_as_identity": False,
        "geometry_mutated": False,
    }
    if not evidence["all_identity_and_sanity_checks_pass"]:
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise RuntimeError(
            "Attempt 30 ordered topology identity or numeric sanity failed: "
            + ",".join(failed)
        )
    return evidence
'''


def exact_replace(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Attempt 30 source replacement drifted: {label}: {count}")
    return source.replace(old, new, 1)


def derive_attempt30_source(source28: str) -> str:
    source = exact_replace(
        source28,
        EXPECTED_ATTEMPT28_CONFIG_SHA256,
        EXPECTED_CONFIG_SHA256,
        "config hash",
    )
    source = exact_replace(
        source,
        "def run_blender_diagnostic(",
        ATTEMPT30_IDENTITY_HELPER + "\n\ndef run_blender_diagnostic(",
        "insert ordered topology identity helper",
    )
    old_terminal = (
        '        if alignment["maximum_xy_distance_m"] > float(\n'
        '            source_contract["captured_xy_match_tolerance_m"]\n'
        '        ):\n'
        '            raise RuntimeError("Attempt 28 source chart does not match Attempt 27 capture")\n'
        '        capture_to_mesh = alignment["capture_source_index_to_mesh_vertex_index"]\n'
    )
    new_terminal = (
        "        source_identity_evidence = attempt30_source_identity_evidence(\n"
        "            config, obj, current_row, capture, captured_xy, alignment\n"
        "        )\n"
        "        capture_to_mesh = source_identity_evidence[\"capture_to_mesh_order\"]\n"
    )
    source = exact_replace(
        source, old_terminal, new_terminal, "replace coordinate-coincidence identity"
    )
    source = exact_replace(
        source,
        '            "capture_to_source_mesh_alignment": alignment,\n',
        '            "capture_to_source_mesh_alignment": alignment,\n'
        '            "source_identity_contract_evidence": source_identity_evidence,\n',
        "record ordered topology identity evidence",
    )
    old_load = "    config = load_config(config_path)\n"
    new_load = (
        "    if config_path != DEFAULT_CONFIG.resolve(strict=True):\n"
        "        raise RuntimeError(\"Attempt 30 requires the exact sealed config path\")\n"
        "    if sha256_file(config_path) != EXPECTED_CONFIG_SHA256:\n"
        "        raise RuntimeError(\"Attempt 30 sealed config hash drifted\")\n"
        "    config = json.loads(json.dumps(ATTEMPT30_RUNTIME_CONFIG))\n"
        "    validate_config(config)\n"
    )
    source = exact_replace(source, old_load, new_load, "inject verified runtime overlay")
    for old, new in (
        ("attempt_28", "attempt_30"),
        ("attempt28", "attempt30"),
        ("Attempt 28", "Attempt 30"),
        ("ATTEMPT28", "ATTEMPT30"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 30 source identity token disappeared: {old}")
        source = source.replace(old, new)
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "attempt30_source_identity_evidence",
        "run_blender_diagnostic",
        "_domain_diagnostic",
    }
    if not required.issubset(names):
        raise RuntimeError("Attempt 30 derived mapping helpers are absent")
    for stale in ("attempt_28", "attempt28", "Attempt 28", "ATTEMPT28"):
        if stale in source:
            raise RuntimeError(f"Attempt 30 derived source retained stale token: {stale}")
    return source


def main() -> None:
    if sha256_file(ATTEMPT28_WORKER) != EXPECTED_ATTEMPT28_WORKER_SHA256:
        raise RuntimeError("Attempt 28 worker changed before Attempt 30 derivation")
    overlay = load_overlay(DEFAULT_CONFIG)
    verify_overlay_bindings(overlay)
    runtime_config = build_runtime_config(overlay)
    source28 = ATTEMPT28_WORKER.read_text(encoding="utf-8")
    source30 = derive_attempt30_source(source28)
    preserved_paths = [
        project_path(overlay["bindings"][name]["path"])
        for package in ("preserved_attempt28_package", "preserved_attempt29_package")
        for name in overlay[package]["binding_names"]
    ]
    before = {path: path.read_bytes() for path in preserved_paths}
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "ATTEMPT30_RUNTIME_CONFIG": runtime_config,
    }
    try:
        exec(
            compile(source30, str(Path(__file__).resolve()) + "::derived", "exec"),
            namespace,
            namespace,
        )
    finally:
        for path in preserved_paths:
            if path.read_bytes() != before[path]:
                raise RuntimeError(f"{path.name} changed during Attempt 30 execution")


if __name__ == "__main__":
    main()
