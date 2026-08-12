"""Attempt 41 static-first obstruction-star and chart-attribution proof.

The outer module binds the exact no-save Attempt 40 runtime result.  Static
verification derives one later Blender mapper that can reverify the complete
Attempt 40 domain, add the complete existing-source vertex star of mesh vertex
459, and record per-boundary chart attribution.  Importing this module is
Blender-free.  No static operation creates Attempt 41 evidence.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT41_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = (
    "eb9f92a2e7bc4d97494394b5e90e49dfb527b192b290e4cd96d0b3716152535d"
)
ATTEMPT40_WORKER = (
    ROOT / "tools/blender_diagnose_kira_r24_blackproject_wider_source_domain_attempt40.py"
)
EXPECTED_ATTEMPT40_WORKER_SHA256 = (
    "faaf1259e408f7d547743940c0be11e0cd3c3e256ff7f221c5a2c7f570d38eb1"
)
EXPECTED_ATTEMPT40_CONFIG_SHA256 = (
    "26bdb0f8a7eb6651260eb84f37d7714453e2620f3add3f864f89051732a17493"
)
EXPECTED_ATTEMPT40_DERIVED_SHA256 = (
    "0361b8551d078a9039927bd6676b68c42029f089b964fd30c46d560d8bf96603"
)
EXPECTED_ATTEMPT40_CANDIDATE_BLOCK_SHA256 = (
    "ee7f671086987af8dced05ab9280f279f9e21ec2a4158ecf54d477e37a2f6b81"
)
EXPECTED_ATTEMPT40_CHART_RETURN_BLOCK_SHA256 = (
    "7b50cf7ab37014374b31d5f29b681a2c190739dbb4df459daa95782e4c19abc0"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def project_path(value: str, *, must_exist: bool = True) -> Path:
    path = (ROOT / value).resolve(strict=must_exist)
    root = ROOT.resolve()
    if root != path and root not in path.parents:
        raise RuntimeError(f"Attempt 41 path escapes project: {value}")
    return path


def load_static_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Attempt 41 cannot load bound module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_record(path: Path) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    return {
        "path": str(exact.relative_to(ROOT)).replace("\\", "/"),
        "bytes": exact.stat().st_size,
        "sha256": sha256_file(exact),
    }


def require_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(record["path"]))
    actual = file_record(path)
    if actual["bytes"] != int(record["bytes"]):
        raise RuntimeError(f"Attempt 41 binding byte count drifted: {name}")
    if actual["sha256"] != str(record["sha256"]).lower():
        raise RuntimeError(
            f"Attempt 41 binding hash drifted: {name}: {actual['sha256']}"
        )
    return actual


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 41 requires the exact sealed config path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 41 config hash drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_41"
        or config.get("status")
        != "STATIC_READ_ONLY_DOMAIN_ATTRIBUTION_PROOF_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 41 identity drifted")
    scope = config["scope"]
    required_true = (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "diagnostic_only",
        "later_independently_reviewed_blender_launch_required",
        "read_existing_source_mesh_allowed_during_later_reviewed_run",
        "in_memory_scene_open_allowed_during_later_reviewed_run",
        "ordered_topology_identity_required_before_mapping",
        "bounded_numeric_sanity_required_before_mapping",
        "exact_attempt40_base_domain_reverification_required",
        "exact_one_obstruction_vertex_star_mapping_allowed",
        "per_boundary_chart_deviation_attribution_required",
        "forced_ear_necessary_feasibility_test_required",
        "append_only_json_evidence_allowed_during_later_run",
    )
    forbidden = (
        "source_file_mutation_allowed",
        "prior_evidence_mutation_allowed",
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
        "uniform_face_ring_allowed",
        "automatic_alternate_candidate_allowed",
        "automatic_retry_allowed",
    )
    if not all(bool(scope[name]) for name in required_true):
        raise RuntimeError("Attempt 41 lost a required read-only scope")
    if any(bool(scope[name]) for name in forbidden):
        raise RuntimeError("Attempt 41 permits a forbidden operation")
    output = config["output"]
    if output != {
        "root": (
            "RecoverySprint/continuation_20260803/"
            "kira_r24_internal_midpoint_fair_surface/attempt_41"
        ),
        "started": "ATTEMPT_STARTED.json",
        "diagnostic": "OBSTRUCTION_STAR_CHART_ATTRIBUTION_DIAGNOSTIC.json",
        "failure": "FAILURE.json",
        "blend_save_permitted": False,
        "render_permitted": False,
    }:
        raise RuntimeError("Attempt 41 output contract drifted")
    if project_path(str(output["root"]), must_exist=False).exists():
        raise RuntimeError("Attempt 41 output already exists")
    hard = config["unchanged_hard_gates"]
    if (
        float(hard["minimum_new_triangle_angle_degrees"]) != 12.0
        or float(hard["minimum_new_triangle_world_area_m2"]) != 1.0e-10
        or int(hard["maximum_new_interior_vertex_count"]) != 160
        or int(hard["maximum_quality_refinement_iterations"]) != 192
        or int(hard["global_seam_vertex_count"]) != 34
        or float(hard["global_seam_coordinate_delta_m"]) != 0.0
        or float(hard["maximum_local_chart_boundary_deviation_m"]) != 0.0011
        or bool(hard["save_allowed_without_owner_visual_acceptance"])
    ):
        raise RuntimeError("Attempt 41 hard gate drifted")
    probe = config["one_candidate_probe"]
    if (
        probe["candidate"]
        != "complete_attempt40_domain_plus_complete_mesh_vertex_star_459"
        or probe["exact_obstruction_boundary_index_before_expansion"] != 14
        or probe["exact_obstruction_mesh_vertex_index"] != 459
        or not bool(probe["complete_source_mesh_vertex_star_only"])
        or bool(probe["uniform_face_ring_candidates_allowed"])
        or bool(probe["alternate_target_sets_allowed"])
        or bool(probe["coordinate_suppression_allowed"])
    ):
        raise RuntimeError("Attempt 41 one-candidate probe drifted")
    attribution = config["chart_attribution_contract"]
    if (
        float(attribution["maximum_allowed_boundary_deviation_m"]) != 0.0011
        or not bool(attribution["required_for_base_and_candidate"])
        or not bool(attribution["one_row_per_ordered_boundary_vertex"])
        or bool(attribution["attribution_authorizes_vertex_movement"])
        or bool(attribution["attribution_authorizes_gate_change"])
    ):
        raise RuntimeError("Attempt 41 chart attribution contract drifted")
    launch = config["launch_contract"]
    if (
        launch["arguments_before_python"]
        != [
            "--background",
            "--factory-startup",
            "--disable-autoexec",
            "--python-exit-code",
            "1",
        ]
        or not bool(launch["wrapper_unions_attempt40_265_entry_inventory"])
        or not bool(launch["wrapper_verifies_all_attempt40_records_before_blender"])
        or not bool(launch["exactly_one_blender_invocation_required"])
        or not bool(launch["refuse_any_overwrite"])
        or bool(launch["executed_during_static_preparation"])
    ):
        raise RuntimeError("Attempt 41 launch contract drifted")
    truth = config["truth"]
    forbidden_truth = (
        "attempt41_blender_execution_performed",
        "attempt41_source_domain_mapping_performed",
        "attempt41_candidate_feasibility_proven",
        "attempt41_triangulation_performed",
        "attempt41_reconstruction_performed",
        "attempt41_body_mutation_performed",
        "attempt41_render_reached",
        "attempt41_blend_saved",
        "runtime_changed",
        "executable_body_repair_justified",
        "body_repair_proven",
        "owner_approval_claimed",
    )
    if any(bool(truth[name]) for name in forbidden_truth):
        raise RuntimeError("Attempt 41 static truth overclaims execution or repair")


def _float_exact(first: Any, second: Any, tolerance: float = 1.0e-15) -> bool:
    return math.isclose(float(first), float(second), rel_tol=0.0, abs_tol=tolerance)


def verify_attempt40_runtime(
    config: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    started = json.loads(
        project_path(records["attempt40_started"]["path"]).read_text(encoding="utf-8")
    )
    diagnostic = json.loads(
        project_path(records["attempt40_diagnostic"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    failure = json.loads(
        project_path(records["attempt40_failure"]["path"]).read_text(encoding="utf-8")
    )
    integrity = json.loads(
        project_path(records["attempt40_external_integrity"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    if (
        started.get("status") != "READ_ONLY_SOURCE_BOUNDARY_DIAGNOSTIC_STARTED"
        or started.get("worker_sha256") != EXPECTED_ATTEMPT40_WORKER_SHA256
        or started.get("config_sha256") != EXPECTED_ATTEMPT40_CONFIG_SHA256
    ):
        raise RuntimeError("Attempt 41 bound Attempt 40 start identity drifted")
    if (
        failure.get("status") != "NO_SAVE_ATTEMPT40_DIAGNOSTIC_STOP_PRESERVED"
        or not failure.get("diagnostic_exists")
        or failure.get("mesh_mutated")
        or failure.get("body_mutated")
        or failure.get("render_reached")
        or failure.get("blend_saved")
        or failure.get("runtime_changed")
    ):
        raise RuntimeError("Attempt 41 bound Attempt 40 failure truth drifted")
    if (
        integrity.get("blender_exit_code") != 1
        or integrity.get("native_invocation_error") is not None
        or integrity.get("pre_post_exact") is not True
        or integrity.get("before") != integrity.get("after")
        or len(integrity.get("before", [])) != 265
    ):
        raise RuntimeError("Attempt 41 bound Attempt 40 integrity drifted")
    protected = []
    seen: set[Path] = set()
    for row in integrity["before"]:
        path = Path(str(row["path"])).resolve(strict=True)
        root = ROOT.resolve()
        if root != path and root not in path.parents:
            raise RuntimeError(f"Attempt 41 protected path escapes project: {path}")
        if path in seen:
            raise RuntimeError(f"Attempt 41 duplicate protected path: {path}")
        seen.add(path)
        actual = file_record(path)
        if (
            int(actual["bytes"]) != int(row["bytes"])
            or actual["sha256"] != str(row["sha256"]).lower()
        ):
            raise RuntimeError(f"Attempt 41 protected file drifted: {path}")
        protected.append(actual)
    if len(protected) != 265:
        raise RuntimeError("Attempt 41 did not verify all 265 protected records")

    if (
        diagnostic.get("attempt_id") != "attempt_40"
        or len(diagnostic.get("targeted_complete_vertex_star_candidates", [])) != 1
        or diagnostic.get("uniform_face_ring_candidates") != []
        or diagnostic.get("necessary_eligible_candidate_count") != 0
        or diagnostic.get("smallest_necessary_eligible_existing_source_candidate")
        is not None
    ):
        raise RuntimeError("Attempt 41 bound Attempt 40 candidate count drifted")
    candidate = diagnostic["targeted_complete_vertex_star_candidates"][0]
    expected = config["attempt40_runtime_result"]
    base = config["attempt40_base_domain"]
    if (
        candidate.get("candidate") != expected["candidate"]
        or int(candidate["face_count"]) != int(expected["face_count"])
        or candidate["face_indices_sha256"] != expected["face_indices_sha256"]
        or int(candidate["vertex_count"]) != int(expected["vertex_count"])
        or candidate["vertex_indices_sha256"] != expected["vertex_indices_sha256"]
        or int(candidate["edge_count"]) != int(expected["edge_count"])
        or int(candidate["boundary_edge_count"])
        != int(expected["boundary_edge_count"])
        or candidate["boundary_edge_indices_sha256"]
        != expected["boundary_edge_indices_sha256"]
        or candidate["boundary_cycle_mesh_vertex_indices"]
        != expected["boundary_cycle_mesh_vertex_indices"]
        or candidate["boundary_cycle_mesh_vertex_indices_sha256"]
        != expected["boundary_cycle_mesh_vertex_indices_sha256"]
        or candidate["eligibility_failures"] != expected["eligibility_failures"]
        or candidate["necessary_candidate_eligibility_passes"]
    ):
        raise RuntimeError("Attempt 41 bound Attempt 40 candidate identity drifted")
    if (
        candidate["added_complete_vertex_star_face_indices"]
        != base["added_complete_vertex_star_face_indices"]
        or int(candidate["added_complete_vertex_star_face_count"])
        != int(base["added_complete_vertex_star_face_count"])
    ):
        raise RuntimeError("Attempt 41 bound Attempt 40 base faces drifted")
    chart = candidate["chart"]
    forced = candidate["forced_ear_feasibility"]
    obstructions = forced["obstructions"]
    boundary_index = int(expected["forced_ear_boundary_index"])
    if (
        not _float_exact(
            chart["maximum_absolute_boundary_deviation_m"],
            expected["maximum_chart_boundary_deviation_m"],
        )
        or not _float_exact(
            chart["rms_absolute_boundary_deviation_m"],
            expected["rms_chart_boundary_deviation_m"],
        )
        or forced.get("passes")
        or len(obstructions) != 1
        or int(obstructions[0]["boundary_index"]) != boundary_index
        or int(candidate["boundary_cycle_mesh_vertex_indices"][boundary_index])
        != int(expected["forced_ear_mesh_vertex_index"])
        or not _float_exact(
            obstructions[0]["fixed_ear_minimum_angle_degrees"],
            expected["forced_ear_minimum_angle_degrees"],
        )
    ):
        raise RuntimeError("Attempt 41 bound Attempt 40 blocker drifted")
    truth = diagnostic["truth"]
    for name in (
        "replacement_boundary_repair_applied",
        "triangulation_performed",
        "mesh_mutated",
        "body_mutated",
        "render_reached",
        "blend_saved",
        "runtime_changed",
        "necessary_candidate_is_sufficient_repair_proof",
        "executable_body_repair_justified",
    ):
        if bool(truth[name]):
            raise RuntimeError(f"Attempt 41 bound Attempt 40 overclaims: {name}")
    return {
        "started": started,
        "diagnostic": diagnostic,
        "failure": failure,
        "integrity": integrity,
        "protected_records": protected,
        "candidate": candidate,
    }


def exact_replace(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Attempt 41 source replacement drifted: {label}: {count}")
    return source.replace(old, new, 1)


def exact_span_replace(
    source: str,
    start_anchor: str,
    end_anchor: str,
    expected_sha256: str,
    replacement: str,
    label: str,
) -> str:
    if source.count(start_anchor) != 1 or source.count(end_anchor) != 1:
        raise RuntimeError(f"Attempt 41 span anchors drifted: {label}")
    start = source.index(start_anchor)
    end = source.index(end_anchor, start)
    old = source[start:end]
    if sha256_text(old) != expected_sha256:
        raise RuntimeError(f"Attempt 41 span hash drifted: {label}: {sha256_text(old)}")
    return source[:start] + replacement + source[end:]


CHART_RETURN_REPLACEMENT = '''    absolute_heights = [abs(float(value)) for value in heights]
    maximum_height = max(absolute_heights)
    ranked_indices = sorted(
        range(len(heights)), key=lambda index: (-absolute_heights[index], index)
    )
    rank_by_index = {index: rank + 1 for rank, index in enumerate(ranked_indices)}
    deviation_rows = [
        {
            "boundary_index": int(index),
            "mesh_vertex_index": int(cycle_ids[index]),
            "signed_deviation_m": float(heights[index]),
            "absolute_deviation_m": float(absolute_heights[index]),
            "absolute_deviation_rank": int(rank_by_index[index]),
            "is_maximum_contributor": bool(
                math.isclose(
                    absolute_heights[index], maximum_height, rel_tol=0.0, abs_tol=1.0e-15
                )
            ),
        }
        for index in range(len(heights))
    ]
    maximum_rows = [row for row in deviation_rows if row["is_maximum_contributor"]]
    return {
        "cycle_mesh_vertex_indices": [int(value) for value in cycle_ids],
        "coordinates_xy_m": coordinates,
        "centroid_world_m": [float(value) for value in centroid],
        "normal_world": [float(value) for value in normal],
        "singular_values": [float(value) for value in singular_values],
        "maximum_absolute_boundary_deviation_m": float(maximum_height),
        "rms_absolute_boundary_deviation_m": math.sqrt(
            sum(value * value for value in heights) / len(heights)
        ),
        "boundary_deviation_attribution": {
            "row_count": len(deviation_rows),
            "rows": deviation_rows,
            "maximum_contributor_boundary_indices": [
                int(row["boundary_index"]) for row in maximum_rows
            ],
            "maximum_contributor_mesh_vertex_indices": [
                int(row["mesh_vertex_index"]) for row in maximum_rows
            ],
        },
    }
'''


ATTRIBUTION_GATE_INSERT = '''    chart = _chart_for_cycle(obj, bm, cycle, selected, np, Vector)
    attribution = chart["boundary_deviation_attribution"]
    attribution_rows = attribution["rows"]
    for attribution_row in attribution_rows:
        attribution_row["maximum_allowed_deviation_m"] = float(maximum_deviation_m)
        attribution_row["exceeds_maximum_allowed_deviation"] = bool(
            float(attribution_row["absolute_deviation_m"]) > float(maximum_deviation_m)
        )
    attribution["maximum_allowed_deviation_m"] = float(maximum_deviation_m)
    attribution["exceeding_row_count"] = sum(
        1 for row in attribution_rows if row["exceeds_maximum_allowed_deviation"]
    )
    attribution["exceeding_rows"] = [
        dict(row)
        for row in attribution_rows
        if row["exceeds_maximum_allowed_deviation"]
    ]
    attribution["all_boundary_vertices_at_or_below_limit"] = not bool(
        attribution["exceeding_rows"]
    )
    angles = boundary_angle_rows(chart["coordinates_xy_m"], target_degrees)
'''


CANDIDATE_MAPPING_REPLACEMENT = '''        targeted = []
        base_contract = ATTEMPT41_RUNTIME_BASE_DOMAIN
        base_selected = set(current)
        base_added_faces = {
            int(value) for value in base_contract["added_complete_vertex_star_face_indices"]
        }
        base_selected.update(base_added_faces)
        if (
            len(base_selected) != int(base_contract["complete_face_count"])
            or canonical_sha256(sorted(base_selected))
            != base_contract["complete_face_indices_sha256"]
        ):
            raise RuntimeError("Attempt 41 exact complete Attempt 40 base domain drifted")
        base_row = _domain_diagnostic(
            "reverified_complete___PREVIOUS_BASE_NAME__",
            base_selected,
            obj,
            bm,
            faces_by_index,
            global_seam_vertices,
            global_seam_edges,
            float(config["diagnosis"]["required_minimum_angle_degrees"]),
            float(source_contract["maximum_local_chart_boundary_deviation_m"]),
            np,
            Vector,
        )
        if (
            int(base_row["face_count"]) != int(base_contract["complete_face_count"])
            or base_row["face_indices_sha256"]
            != base_contract["complete_face_indices_sha256"]
            or int(base_row["vertex_count"]) != int(base_contract["complete_vertex_count"])
            or base_row["vertex_indices_sha256"]
            != base_contract["complete_vertex_indices_sha256"]
            or int(base_row["boundary_edge_count"])
            != int(base_contract["complete_boundary_edge_count"])
            or base_row["boundary_edge_indices_sha256"]
            != base_contract["complete_boundary_edge_indices_sha256"]
            or base_row["boundary_cycle_mesh_vertex_indices"]
            != base_contract["complete_boundary_cycle_mesh_vertex_indices"]
            or base_row["boundary_cycle_mesh_vertex_indices_sha256"]
            != base_contract["complete_boundary_cycle_mesh_vertex_indices_sha256"]
        ):
            raise RuntimeError("Attempt 41 reverified Attempt 40 base topology drifted")
        probe = ATTEMPT41_RUNTIME_PROBE
        obstruction_boundary_index = int(
            probe["exact_obstruction_boundary_index_before_expansion"]
        )
        obstruction_vertex_index = int(probe["exact_obstruction_mesh_vertex_index"])
        if (
            int(base_row["boundary_cycle_mesh_vertex_indices"][obstruction_boundary_index])
            != obstruction_vertex_index
        ):
            raise RuntimeError("Attempt 41 exact obstruction boundary identity drifted")
        complete_star_faces = {
            int(face.index) for face in bm.verts[obstruction_vertex_index].link_faces
        }
        added_faces = complete_star_faces.difference(base_selected)
        if not added_faces:
            raise RuntimeError("Attempt 41 obstruction vertex star adds no source face")
        selected = set(base_selected)
        selected.update(added_faces)
        row = _domain_diagnostic(
            "complete___PREVIOUS_BASE_NAME___plus_complete_mesh_vertex_star_459",
            selected,
            obj,
            bm,
            faces_by_index,
            global_seam_vertices,
            global_seam_edges,
            float(config["diagnosis"]["required_minimum_angle_degrees"]),
            float(source_contract["maximum_local_chart_boundary_deviation_m"]),
            np,
            Vector,
        )
        row["base_candidate"] = probe["base_candidate"]
        row["base_face_count"] = len(base_selected)
        row["base_face_indices_sha256"] = canonical_sha256(sorted(base_selected))
        row["exact_obstruction_boundary_index_before_expansion"] = obstruction_boundary_index
        row["exact_obstruction_mesh_vertex_index"] = obstruction_vertex_index
        row["complete_source_mesh_vertex_star_face_count"] = len(complete_star_faces)
        row["complete_source_mesh_vertex_star_face_indices"] = sorted(complete_star_faces)
        row["added_complete_source_mesh_vertex_star_face_count"] = len(added_faces)
        row["added_complete_source_mesh_vertex_star_face_indices"] = sorted(added_faces)
        forced_ear = attempt41_forced_ear_feasibility(
            row, float(config["diagnosis"]["required_minimum_angle_degrees"])
        )
        row["forced_ear_feasibility"] = forced_ear
        if not forced_ear["passes"]:
            row["necessary_candidate_eligibility_passes"] = False
            row["eligibility_failures"] = list(row["eligibility_failures"]) + [
                "forced_prev_current_next_ear_all_angles_at_least_12_degrees"
            ]
        targeted.append(row)
        ring_rows = []

'''


def derive_attempt41_source(
    config: Mapping[str, Any], attempt40_source: str
) -> str:
    if sha256_text(attempt40_source) != EXPECTED_ATTEMPT40_DERIVED_SHA256:
        raise RuntimeError("Attempt 41 base derived source drifted")
    source = exact_replace(
        attempt40_source,
        "STATIC_READ_ONLY_DOMAIN_PROOF_PREPARED_NOT_RUN",
        "STATIC_READ_ONLY_DOMAIN_ATTRIBUTION_PROOF_PREPARED_NOT_RUN",
        "bind Attempt 41 runtime status",
    )
    source = exact_replace(
        source,
        EXPECTED_ATTEMPT40_CONFIG_SHA256,
        EXPECTED_CONFIG_SHA256,
        "bind Attempt 41 config hash",
    )
    source = exact_span_replace(
        source,
        '    return {\n        "cycle_mesh_vertex_indices"',
        "\n\n\ndef _align_capture_to_current",
        EXPECTED_ATTEMPT40_CHART_RETURN_BLOCK_SHA256,
        CHART_RETURN_REPLACEMENT,
        "add per-boundary chart rows",
    )
    source = exact_replace(
        source,
        '    chart = _chart_for_cycle(obj, bm, cycle, selected, np, Vector)\n'
        '    angles = boundary_angle_rows(chart["coordinates_xy_m"], target_degrees)\n',
        ATTRIBUTION_GATE_INSERT,
        "add chart gate attribution",
    )
    source = exact_span_replace(
        source,
        "        targeted = []\n",
        "        coordinate_only = ATTEMPT40_BOUND_COORDINATE_ONLY\n",
        EXPECTED_ATTEMPT40_CANDIDATE_BLOCK_SHA256,
        CANDIDATE_MAPPING_REPLACEMENT,
        "replace mapping with exact obstruction star",
    )
    old_provenance = (
        '            "attempt39_fixed_ear_blocker": ATTEMPT40_RUNTIME_BLOCKER,\n'
        '            "one_wider_source_domain_probe": ATTEMPT40_RUNTIME_PROBE,\n'
        '            "targeted_complete_vertex_star_candidates": targeted,\n'
    )
    new_provenance = (
        '            "__PREVIOUS_RUNTIME_RESULT__": ATTEMPT41_RUNTIME_RESULT,\n'
        '            "__PREVIOUS_BASE_REVERIFIED__": base_row,\n'
        '            "one_candidate_probe": ATTEMPT41_RUNTIME_PROBE,\n'
        '            "targeted_complete_vertex_star_candidates": targeted,\n'
    )
    source = exact_replace(
        source, old_provenance, new_provenance, "record Attempt 41 provenance"
    )
    source = exact_replace(
        source,
        '                "executable_body_repair_justified": False,\n',
        '                "executable_body_repair_justified": False,\n'
        '                "per_boundary_chart_deviation_attribution_recorded": True,\n'
        '                "__PREVIOUS_COMPLETE_DOMAIN_USED_ONLY_AS_READ_ONLY_BASE__": True,\n',
        "record attribution truth",
    )
    for old, new in (
        ("attempt_40", "attempt_41"),
        ("attempt40", "attempt41"),
        ("Attempt 40", "Attempt 41"),
        ("ATTEMPT40", "ATTEMPT41"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 41 source identity token disappeared: {old}")
        source = source.replace(old, new)
    source = source.replace(
        "__PREVIOUS_RUNTIME_RESULT__", "attempt40_runtime_result"
    )
    source = source.replace(
        "__PREVIOUS_BASE_REVERIFIED__",
        "attempt40_complete_candidate_reverified",
    )
    source = source.replace(
        "__PREVIOUS_COMPLETE_DOMAIN_USED_ONLY_AS_READ_ONLY_BASE__",
        "attempt40_complete_domain_used_only_as_read_only_base",
    )
    source = source.replace("__PREVIOUS_BASE_NAME__", "attempt40_domain")
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "attempt41_source_identity_evidence",
        "attempt41_forced_ear_feasibility",
        "run_blender_diagnostic",
        "_domain_diagnostic",
    }
    if not required.issubset(names):
        raise RuntimeError("Attempt 41 derived read-only helpers are absent")
    for stale in ("attempt_40", "ATTEMPT40_"):
        if stale in source:
            raise RuntimeError(f"Attempt 41 derived source retained stale token: {stale}")
    required_tokens = (
        '"boundary_deviation_attribution"',
        '"absolute_deviation_rank"',
        '"exceeds_maximum_allowed_deviation"',
        '"exact_obstruction_mesh_vertex_index"',
        '"attempt40_runtime_result"',
        '"attempt40_complete_candidate_reverified"',
        '"attempt40_complete_domain_used_only_as_read_only_base"',
    )
    if any(token not in source for token in required_tokens):
        raise RuntimeError("Attempt 41 derived attribution or provenance is absent")
    forbidden_calls = (
        "bpy.ops.wm.save",
        "bpy.ops.render",
        "bpy.ops.export",
        "bpy.ops.object.join",
        "bmesh.ops.delete",
        "to_mesh(",
    )
    if any(value in source for value in forbidden_calls):
        raise RuntimeError("Attempt 41 derived source contains a forbidden operation")
    return source


def build_runtime_config(
    config: Mapping[str, Any],
    attempt40: Any,
    attempt40_config: Mapping[str, Any],
    attempt30: Any,
    attempt30_overlay: Mapping[str, Any],
    attempt30_diagnostic: Mapping[str, Any],
    attempt40_diagnostic: Mapping[str, Any],
) -> dict[str, Any]:
    runtime = attempt40.build_runtime_config(
        attempt40_config, attempt30, attempt30_overlay, attempt30_diagnostic
    )
    for key in ("attempt_id", "status", "mode", "scope", "output", "proposal", "truth"):
        runtime[key] = json.loads(json.dumps(config[key]))
    runtime["unchanged_hard_gates"] = json.loads(
        json.dumps(config["unchanged_hard_gates"])
    )
    runtime["source_identity_contract"] = json.loads(
        json.dumps(config["source_identity_contract"])
    )
    runtime["bindings"].update(json.loads(json.dumps(config["bindings"])))
    runtime["source_mesh_diagnostic"]["targeted_vertex_star_suppression_sets"] = []
    runtime["source_mesh_diagnostic"]["uniform_face_ring_expansions_to_map"] = []
    runtime["source_mesh_diagnostic"]["eligible_candidate_requires"] = list(
        runtime["source_mesh_diagnostic"]["eligible_candidate_requires"]
    ) + [
        "per_boundary_chart_deviation_attribution",
        "exact_complete_attempt40_base_plus_complete_mesh_vertex_star_459",
    ]
    runtime["attempt40_runtime_result"] = json.loads(
        json.dumps(config["attempt40_runtime_result"])
    )
    runtime["attempt40_base_domain"] = json.loads(
        json.dumps(config["attempt40_base_domain"])
    )
    runtime["one_candidate_probe"] = json.loads(
        json.dumps(config["one_candidate_probe"])
    )
    runtime["chart_attribution_contract"] = json.loads(
        json.dumps(config["chart_attribution_contract"])
    )
    runtime["coordinate_only_analysis"] = json.loads(
        json.dumps(attempt40_diagnostic["coordinate_only_analysis"])
    )
    return runtime


def verify_package(config: Mapping[str, Any]) -> dict[str, Any]:
    records = {
        str(name): require_record(str(name), record)
        for name, record in config["bindings"].items()
    }
    records["proposal"] = require_record("proposal", config["proposal"])
    if records["attempt40_worker"]["sha256"] != EXPECTED_ATTEMPT40_WORKER_SHA256:
        raise RuntimeError("Attempt 41 bound Attempt 40 worker disagrees")
    if records["attempt40_config"]["sha256"] != EXPECTED_ATTEMPT40_CONFIG_SHA256:
        raise RuntimeError("Attempt 41 bound Attempt 40 config disagrees")
    evidence = verify_attempt40_runtime(config, records)

    attempt40 = load_static_module("attempt41_bound_attempt40", ATTEMPT40_WORKER)
    attempt40_config = json.loads(
        project_path(records["attempt40_config"]["path"]).read_text(encoding="utf-8")
    )
    for name, record in attempt40_config["bindings"].items():
        attempt40.require_record(str(name), record)
    attempt40.require_record("attempt40_proposal", attempt40_config["proposal"])
    attempt30 = load_static_module("attempt41_bound_attempt30", attempt40.ATTEMPT30_WORKER)
    attempt30_config_path = project_path(
        attempt40_config["bindings"]["attempt30_config"]["path"]
    )
    attempt30_overlay = attempt30.load_overlay(attempt30_config_path)
    attempt30.verify_overlay_bindings(attempt30_overlay)
    attempt30_diagnostic = json.loads(
        project_path(
            attempt40_config["bindings"]["attempt30_diagnostic"]["path"]
        ).read_text(encoding="utf-8")
    )
    attempt40_source = attempt40.derive_attempt40_source(attempt40_config, attempt30)
    if sha256_text(attempt40_source) != EXPECTED_ATTEMPT40_DERIVED_SHA256:
        raise RuntimeError("Attempt 41 exact Attempt 40 derived source drifted")
    runtime = build_runtime_config(
        config,
        attempt40,
        attempt40_config,
        attempt30,
        attempt30_overlay,
        attempt30_diagnostic,
        evidence["diagnostic"],
    )
    source = derive_attempt41_source(config, attempt40_source)
    derived_namespace = {
        "__name__": "attempt41_static_runtime_contract",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
    }
    exec(
        compile(source, str(Path(__file__).resolve()) + "::derived-contract", "exec"),
        derived_namespace,
        derived_namespace,
    )
    derived_namespace["validate_config"](runtime)
    return {
        "records": records,
        "attempt40_evidence": evidence,
        "attempt40": attempt40,
        "attempt40_config": attempt40_config,
        "attempt30": attempt30,
        "attempt30_overlay": attempt30_overlay,
        "attempt30_diagnostic": attempt30_diagnostic,
        "attempt40_derived_source": attempt40_source,
        "runtime_config": runtime,
        "derived_source": source,
        "derived_source_sha256": sha256_text(source),
    }


def run_blender(config_path: Path, config: Mapping[str, Any]) -> None:
    verified = verify_package(config)
    source = verified["derived_source"]
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "ATTEMPT41_RUNTIME_CONFIG": verified["runtime_config"],
        "ATTEMPT41_RUNTIME_RESULT": json.loads(
            json.dumps(config["attempt40_runtime_result"])
        ),
        "ATTEMPT41_RUNTIME_BASE_DOMAIN": json.loads(
            json.dumps(config["attempt40_base_domain"])
        ),
        "ATTEMPT41_RUNTIME_PROBE": json.loads(
            json.dumps(config["one_candidate_probe"])
        ),
        "ATTEMPT41_BOUND_COORDINATE_ONLY": json.loads(
            json.dumps(
                verified["attempt40_evidence"]["diagnostic"]["coordinate_only_analysis"]
            )
        ),
    }
    exec(
        compile(source, str(Path(__file__).resolve()) + "::derived", "exec"),
        namespace,
        namespace,
    )


def parse_args() -> argparse.Namespace:
    argv = __import__("sys").argv
    values = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args(values)


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = load_config(config_path)
    verify_package(config)
    run_blender(config_path, config)


if __name__ == "__main__":
    main()
