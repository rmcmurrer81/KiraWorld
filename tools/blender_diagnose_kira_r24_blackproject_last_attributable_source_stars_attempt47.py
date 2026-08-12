"""Static-first R24 Attempt 47 last attributable source-star diagnostic.

Importing this module is Blender-free.  It binds the preserved Attempt 46
rejection, derives exactly one read-only candidate, and never creates runtime
evidence during static verification.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

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
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT47_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = (
    "f0d116cdb64b4c813e25214de87dcf0a660938f4393f5b2ab12421bc6b53a3b4"
)
ATTEMPT46_WORKER = ROOT / (
    "tools/blender_diagnose_kira_r24_blackproject_"
    "compound_local_blocker_stars_attempt46.py"
)
EXPECTED_ATTEMPT46_WORKER_SHA256 = (
    "1da1962a11233f5c6247d90ebd085f3b61e04d5048828e0cbebf2fc03c6502c3"
)
EXPECTED_ATTEMPT46_CONFIG_SHA256 = (
    "c9b2db89e58726b82a22146c1af2eacb7a3c121156f0f1336951792131881780"
)
EXPECTED_ATTEMPT46_DERIVED_SHA256 = (
    "82d2332c4a39fea67a968c3d1ed31abd3e06a209e903161741db54121741c066"
)
EXPECTED_ATTEMPT46_MAPPING_BLOCK_SHA256 = (
    "e0736717e2d1f0882c85ccf618be0427fd34a4d96c04cb5c113899b48d06ecd6"
)
EXPECTED_CACHE_SHA256 = (
    "340ddf1fcbb97d8bd309280061f05dd6a914b79c1e36abce69134501902c162f"
)
EXPECTED_DERIVED_SHA256 = (
    "2f6fbea317c01a8bbe5c9e9d1a9aea39d896b17c178b084942343d2a6a48115a"
)

ATTEMPT46_CHANGED_LOGS = {
    "RecoverySprint/continuation_20260808/attempt46_blender_stdout.log",
    "RecoverySprint/continuation_20260808/attempt46_blender_stderr.log",
}


CANDIDATE_MAPPING_REPLACEMENT = r'''        selected = set(previous_selected)
        candidate_base_star_rows = []
        for blocker_vertex in probe["__BASE_ATTEMPT___base_source_mesh_vertex_stars"]:
            blocker_vertex = int(blocker_vertex)
            complete_star = {
                int(face.index) for face in bm.verts[blocker_vertex].link_faces
            }
            added = complete_star.difference(selected)
            if not added:
                raise RuntimeError(
                    f"Attempt 47 base source star adds no face: {blocker_vertex}"
                )
            candidate_base_star_rows.append(
                {
                    "mesh_vertex_index": blocker_vertex,
                    "complete_source_mesh_vertex_star_face_count": len(complete_star),
                    "complete_source_mesh_vertex_star_face_indices": sorted(complete_star),
                    "added_source_face_count_at_union_step": len(added),
                    "added_source_face_indices_at_union_step": sorted(added),
                }
            )
            selected.update(complete_star)
        candidate_base_selected = set(selected)
        candidate_base_row = _domain_diagnostic(
            "reverified_complete___BASE_ATTEMPT___candidate",
            candidate_base_selected,
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
        candidate_base_forced = attempt46_forced_ear_feasibility(
            candidate_base_row,
            float(config["diagnosis"]["required_minimum_angle_degrees"]),
        )
        candidate_base_row["forced_ear_feasibility"] = candidate_base_forced
        if not candidate_base_forced["passes"]:
            candidate_base_row["necessary_candidate_eligibility_passes"] = False
            candidate_base_row["eligibility_failures"] = list(
                candidate_base_row["eligibility_failures"]
            ) + ["forced_prev_current_next_ear_all_angles_at_least_12_degrees"]
        candidate_base_contract = config["__BASE_ATTEMPT___base_contract"]
        candidate_base_attribution = candidate_base_row["chart"][
            "boundary_deviation_attribution"
        ]
        candidate_base_obstruction = candidate_base_forced["obstructions"][0]
        candidate_base_checks = (
            int(candidate_base_row["face_count"])
            == int(candidate_base_contract["face_count"]),
            candidate_base_row["face_indices_sha256"]
            == candidate_base_contract["face_indices_sha256"],
            int(candidate_base_row["vertex_count"])
            == int(candidate_base_contract["vertex_count"]),
            candidate_base_row["vertex_indices_sha256"]
            == candidate_base_contract["vertex_indices_sha256"],
            int(candidate_base_row["edge_count"])
            == int(candidate_base_contract["edge_count"]),
            int(candidate_base_row["boundary_edge_count"])
            == int(candidate_base_contract["boundary_edge_count"]),
            candidate_base_row["boundary_edge_indices_sha256"]
            == candidate_base_contract["boundary_edge_indices_sha256"],
            candidate_base_row["boundary_cycle_mesh_vertex_indices"]
            == candidate_base_contract["boundary_cycle_mesh_vertex_indices"],
            candidate_base_row["boundary_cycle_mesh_vertex_indices_sha256"]
            == candidate_base_contract["boundary_cycle_mesh_vertex_indices_sha256"],
            candidate_base_row["simple_projected_boundary"] is False,
            candidate_base_row["global_seam_relation"] == "DISJOINT",
            int(candidate_base_row["boundary_angle_analysis"]["minimum_boundary_index"])
            == int(candidate_base_contract["minimum_boundary_index"]),
            float(candidate_base_row["boundary_angle_analysis"]["minimum_boundary_interior_angle_degrees"])
            == float(candidate_base_contract["minimum_boundary_interior_angle_degrees"]),
            candidate_base_attribution["maximum_contributor_boundary_indices"]
            == candidate_base_contract["chart_maximum_contributor_boundary_indices"],
            candidate_base_attribution["maximum_contributor_mesh_vertex_indices"]
            == candidate_base_contract["chart_maximum_contributor_mesh_vertex_indices"],
            int(candidate_base_attribution["exceeding_row_count"])
            == int(candidate_base_contract["chart_exceeding_row_count"]),
            int(candidate_base_obstruction["boundary_index"])
            == int(candidate_base_contract["forced_ear_obstruction_boundary_index"]),
            int(candidate_base_row["boundary_cycle_mesh_vertex_indices"][
                int(candidate_base_obstruction["boundary_index"])
            ]) == int(candidate_base_contract["forced_ear_obstruction_mesh_vertex_index"]),
            candidate_base_row["eligibility_failures"]
            == candidate_base_contract["eligibility_failures"],
        )
        expected_base_star_rows = candidate_base_contract["complete_source_star_rows"]
        actual_base_star_rows = [
            {
                "mesh_vertex_index": row["mesh_vertex_index"],
                "complete_source_mesh_vertex_star_face_indices": row[
                    "complete_source_mesh_vertex_star_face_indices"
                ],
                "added_source_face_indices_at_union_step": row[
                    "added_source_face_indices_at_union_step"
                ],
            }
            for row in candidate_base_star_rows
        ]
        if not all(candidate_base_checks) or actual_base_star_rows != expected_base_star_rows:
            raise RuntimeError("Attempt 47 exact __BASE_ATTEMPT_TITLE__ base domain drifted")

        compound_star_rows = []
        for blocker_vertex in probe["new_compound_blocker_source_mesh_vertex_stars"]:
            blocker_vertex = int(blocker_vertex)
            complete_star = {
                int(face.index) for face in bm.verts[blocker_vertex].link_faces
            }
            added = complete_star.difference(selected)
            if not added:
                raise RuntimeError(
                    f"Attempt 47 attributable blocker star adds no face: {blocker_vertex}"
                )
            compound_star_rows.append(
                {
                    "mesh_vertex_index": blocker_vertex,
                    "complete_source_mesh_vertex_star_face_count": len(complete_star),
                    "complete_source_mesh_vertex_star_face_indices": sorted(complete_star),
                    "added_source_face_count_at_union_step": len(added),
                    "added_source_face_indices_at_union_step": sorted(added),
                }
            )
            selected.update(complete_star)
        row = _domain_diagnostic(
            "complete___BASE_ATTEMPT___domain_plus_complete_mesh_vertex_stars_351_248_676",
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
        forced_ear = attempt46_forced_ear_feasibility(
            row, float(config["diagnosis"]["required_minimum_angle_degrees"])
        )
        row["forced_ear_feasibility"] = forced_ear
        if not forced_ear["passes"]:
            row["necessary_candidate_eligibility_passes"] = False
            row["eligibility_failures"] = list(row["eligibility_failures"]) + [
                "forced_prev_current_next_ear_all_angles_at_least_12_degrees"
            ]
        row["base_candidate"] = probe["base_candidate"]
        row["base_face_count"] = len(candidate_base_selected)
        row["base_face_indices_sha256"] = canonical_sha256(
            sorted(candidate_base_selected)
        )
        row["one_indivisible_compound_candidate"] = True
        row["compound_blocker_source_mesh_vertex_indices"] = list(
            probe["new_compound_blocker_source_mesh_vertex_stars"]
        )
        row["__BASE_ATTEMPT___base_source_star_rows"] = candidate_base_star_rows
        row["compound_source_star_rows"] = compound_star_rows
        row["terminal_source_star_rule"] = config["terminal_source_star_rule"]
        targeted.append(row)'''


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def project_path(value: str, *, must_exist: bool = True) -> Path:
    path = (ROOT / value).resolve(strict=must_exist)
    root = ROOT.resolve()
    if root != path and root not in path.parents:
        raise RuntimeError(f"Attempt 47 path escapes project: {value}")
    return path


def file_record(path: Path) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    return {
        "path": str(exact.relative_to(ROOT)).replace("\\", "/"),
        "bytes": exact.stat().st_size,
        "sha256": sha256_file(exact),
    }


def require_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    actual = file_record(project_path(str(record["path"])))
    if actual["bytes"] != int(record["bytes"]):
        raise RuntimeError(f"Attempt 47 binding byte count drifted: {name}")
    if actual["sha256"] != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 47 binding hash drifted: {name}")
    return actual


def load_static_module(name: str, path: Path) -> Any:
    if sys.dont_write_bytecode is not True:
        raise RuntimeError("Attempt 47 bytecode containment was disabled")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Attempt 47 cannot load bound module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 47 requires the exact sealed config path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 47 config hash drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_47"
        or config.get("status")
        != "STATIC_READ_ONLY_LAST_ATTRIBUTABLE_SOURCE_STARS_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 47 identity drifted")
    scope = config["scope"]
    required_true = (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "diagnostic_only",
        "later_independently_reviewed_blender_launch_required",
        "ordered_topology_identity_required_before_mapping",
        "exact_attempt44_candidate_reverification_required",
        "exact_attempt46_base_domain_reverification_required",
        "exact_one_compound_blocker_vertex_star_mapping_allowed",
        "exact_runtime_probe_key_contract_required_before_blender",
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
        "uniform_face_ring_allowed",
        "separate_blocker_star_candidates_allowed",
        "automatic_alternate_candidate_allowed",
        "automatic_retry_allowed",
    )
    if not all(bool(scope[name]) for name in required_true):
        raise RuntimeError("Attempt 47 lost a required read-only scope")
    if any(bool(scope[name]) for name in forbidden):
        raise RuntimeError("Attempt 47 permits a forbidden operation")
    output = config["output"]
    expected_root = (
        "RecoverySprint/continuation_20260803/"
        "kira_r24_internal_midpoint_fair_surface/attempt_47"
    )
    if (
        output["root"] != expected_root
        or output["diagnostic"] != "LAST_ATTRIBUTABLE_SOURCE_STARS_DIAGNOSTIC.json"
        or bool(output["blend_save_permitted"])
        or bool(output["render_permitted"])
    ):
        raise RuntimeError("Attempt 47 output contract drifted")
    external = (
        "RecoverySprint/continuation_20260808/attempt47_blender_stdout.log",
        "RecoverySprint/continuation_20260808/attempt47_blender_stderr.log",
        "RecoverySprint/continuation_20260808/attempt47_external_pre_post_integrity.json",
    )
    if project_path(expected_root, must_exist=False).exists() or any(
        project_path(path, must_exist=False).exists() for path in external
    ):
        raise RuntimeError("Attempt 47 static output already exists")
    candidate = config["one_candidate_contract"]
    if (
        candidate["candidate"]
        != "complete_attempt46_domain_plus_complete_mesh_vertex_stars_351_248_676"
        or candidate["base_candidate"]
        != "complete_attempt44_domain_plus_complete_mesh_vertex_stars_218_508"
        or candidate["attempt46_base_source_mesh_vertex_stars"] != [218, 508]
        or candidate["new_compound_blocker_source_mesh_vertex_stars"]
        != [351, 248, 676]
        or candidate["all_source_mesh_vertex_stars_after_attempt44"]
        != [218, 508, 351, 248, 676]
        or not bool(candidate["one_indivisible_compound_candidate"])
        or bool(candidate["separate_star_candidates_allowed"])
        or bool(candidate["uniform_face_ring_candidates_allowed"])
        or bool(candidate["alternate_target_sets_allowed"])
        or bool(candidate["coordinate_suppression_allowed"])
    ):
        raise RuntimeError("Attempt 47 one-candidate contract drifted")
    hard = config["unchanged_hard_gates"]
    if (
        float(hard["required_minimum_angle_degrees"]) != 12.0
        or float(hard["maximum_local_chart_boundary_deviation_m"]) != 0.0011
        or float(hard["minimum_new_triangle_area_m2"]) != 1.0e-10
        or not bool(hard["simple_projected_boundary_required"])
        or int(hard["global_seam_vertex_count"]) != 34
        or float(hard["global_seam_coordinate_delta_m"]) != 0.0
    ):
        raise RuntimeError("Attempt 47 changed a hard gate")
    terminal = config["terminal_source_star_rule"]
    if (
        not bool(terminal["this_is_last_attributable_source_star_candidate"])
        or not bool(terminal["if_any_necessary_gate_fails_stop_source_star_expansion"])
        or bool(terminal["attempt48_source_star_followup_allowed"])
        or bool(terminal["shifted_blocker_chasing_allowed"])
    ):
        raise RuntimeError("Attempt 47 terminal source-star rule drifted")
    launch = config["launch_contract"]
    if (
        bool(launch["wrapper_prepared_in_this_package"])
        or not bool(launch["wrapper_builds_fresh_protected_inventory"])
        or not bool(launch["wrapper_includes_attempt46_343_stable_records"])
        or not bool(launch["wrapper_protects_final_attempt46_logs_and_integrity_as_inputs"])
        or not bool(
            launch[
                "wrapper_excludes_its_own_stdout_stderr_and_integrity_from_immutable_before_after"
            ]
        )
        or not bool(launch["exactly_one_blender_invocation_required"])
        or bool(launch["executed_during_static_preparation"])
    ):
        raise RuntimeError("Attempt 47 future launch contract drifted")
    forbidden_truth = (
        "attempt47_wrapper_prepared",
        "attempt47_blender_execution_performed",
        "attempt47_source_domain_mapping_performed",
        "attempt47_candidate_feasibility_proven",
        "attempt47_triangulation_performed",
        "attempt47_reconstruction_performed",
        "attempt47_body_mutation_performed",
        "attempt47_render_reached",
        "attempt47_blend_saved",
        "runtime_changed",
        "executable_body_repair_justified",
        "body_repair_proven",
        "owner_approval_claimed",
    )
    if any(bool(config["truth"][name]) for name in forbidden_truth):
        raise RuntimeError("Attempt 47 static truth overclaims work")


def _relative_record_path(value: str) -> str:
    path = Path(value).resolve(strict=True)
    if ROOT.resolve() != path and ROOT.resolve() not in path.parents:
        raise RuntimeError(f"Attempt 47 inventory path escapes project: {path}")
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _orientation(a: Sequence[float], b: Sequence[float], c: Sequence[float]) -> float:
    return float((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))


def nonadjacent_intersections(
    points: Sequence[Sequence[float]], vertex_ids: Sequence[int], epsilon: float
) -> list[dict[str, Any]]:
    count = len(points)
    rows: list[dict[str, Any]] = []
    for first_index in range(count):
        a = points[first_index]
        b = points[(first_index + 1) % count]
        for second_index in range(first_index + 1, count):
            if (
                second_index == first_index
                or second_index == (first_index + 1) % count
                or first_index == (second_index + 1) % count
            ):
                continue
            c = points[second_index]
            d = points[(second_index + 1) % count]
            o1, o2 = _orientation(a, b, c), _orientation(a, b, d)
            o3, o4 = _orientation(c, d, a), _orientation(c, d, b)
            proper = (
                ((o1 > epsilon and o2 < -epsilon) or (o1 < -epsilon and o2 > epsilon))
                and ((o3 > epsilon and o4 < -epsilon) or (o3 < -epsilon and o4 > epsilon))
            )
            if not proper:
                continue
            rx, ry = b[0] - a[0], b[1] - a[1]
            sx, sy = d[0] - c[0], d[1] - c[1]
            denominator = rx * sy - ry * sx
            qx, qy = c[0] - a[0], c[1] - a[1]
            first_parameter = (qx * sy - qy * sx) / denominator
            second_parameter = (qx * ry - qy * rx) / denominator
            rows.append(
                {
                    "kind": "proper",
                    "first_boundary_edge_index": first_index,
                    "first_edge_mesh_vertices": [
                        int(vertex_ids[first_index]),
                        int(vertex_ids[(first_index + 1) % count]),
                    ],
                    "second_boundary_edge_index": second_index,
                    "second_edge_mesh_vertices": [
                        int(vertex_ids[second_index]),
                        int(vertex_ids[(second_index + 1) % count]),
                    ],
                    "first_edge_parameter": float(first_parameter),
                    "second_edge_parameter": float(second_parameter),
                    "intersection_xy_m": [
                        float(a[0] + first_parameter * rx),
                        float(a[1] + first_parameter * ry),
                    ],
                }
            )
    return rows


def verify_attempt46_runtime(
    config: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    def read(name: str) -> Any:
        return json.loads(project_path(str(config["bindings"][name]["path"])).read_text(encoding="utf-8"))

    started, failure = read("attempt46_started"), read("attempt46_failure")
    diagnostic, integrity = read("attempt46_diagnostic"), read("attempt46_external_integrity")
    if (
        started.get("status") != "READ_ONLY_SOURCE_BOUNDARY_DIAGNOSTIC_STARTED"
        or started.get("worker_sha256") != EXPECTED_ATTEMPT46_WORKER_SHA256
        or started.get("config_sha256") != EXPECTED_ATTEMPT46_CONFIG_SHA256
    ):
        raise RuntimeError("Attempt 47 bound Attempt 46 start drifted")
    if (
        failure.get("status") != "NO_SAVE_ATTEMPT46_DIAGNOSTIC_STOP_PRESERVED"
        or failure.get("diagnostic_exists") is not True
        or any(bool(failure.get(name)) for name in ("mesh_mutated", "body_mutated", "render_reached", "blend_saved", "runtime_changed"))
    ):
        raise RuntimeError("Attempt 47 bound Attempt 46 failure drifted")
    if (
        int(diagnostic["necessary_eligible_candidate_count"]) != 0
        or diagnostic["smallest_necessary_eligible_existing_source_candidate"] is not None
        or len(diagnostic["targeted_complete_vertex_star_candidates"]) != 1
        or bool(diagnostic["truth"]["executable_body_repair_justified"])
    ):
        raise RuntimeError("Attempt 47 bound Attempt 46 outcome drifted")
    row = diagnostic["targeted_complete_vertex_star_candidates"][0]
    base = config["attempt46_base_contract"]
    attribution = row["chart"]["boundary_deviation_attribution"]
    obstruction = row["forced_ear_feasibility"]["obstructions"][0]
    checks = (
        row["candidate"] == base["candidate"],
        int(row["face_count"]) == int(base["face_count"]),
        row["face_indices_sha256"] == base["face_indices_sha256"],
        int(row["vertex_count"]) == int(base["vertex_count"]),
        row["vertex_indices_sha256"] == base["vertex_indices_sha256"],
        int(row["edge_count"]) == int(base["edge_count"]),
        int(row["boundary_edge_count"]) == int(base["boundary_edge_count"]),
        row["boundary_edge_indices_sha256"] == base["boundary_edge_indices_sha256"],
        row["boundary_cycle_mesh_vertex_indices"] == base["boundary_cycle_mesh_vertex_indices"],
        row["boundary_cycle_mesh_vertex_indices_sha256"] == base["boundary_cycle_mesh_vertex_indices_sha256"],
        row["simple_projected_boundary"] is False,
        row["global_seam_relation"] == "DISJOINT",
        float(row["boundary_angle_analysis"]["minimum_boundary_interior_angle_degrees"])
        == float(base["minimum_boundary_interior_angle_degrees"]),
        int(row["boundary_angle_analysis"]["minimum_boundary_index"])
        == int(base["minimum_boundary_index"]),
        float(row["chart"]["maximum_absolute_boundary_deviation_m"])
        == float(base["maximum_chart_boundary_deviation_m"]),
        int(attribution["exceeding_row_count"]) == int(base["chart_exceeding_row_count"]),
        attribution["maximum_contributor_boundary_indices"] == base["chart_maximum_contributor_boundary_indices"],
        attribution["maximum_contributor_mesh_vertex_indices"] == base["chart_maximum_contributor_mesh_vertex_indices"],
        int(obstruction["boundary_index"]) == int(base["forced_ear_obstruction_boundary_index"]),
        row["boundary_cycle_mesh_vertex_indices"][int(obstruction["boundary_index"])]
        == int(base["forced_ear_obstruction_mesh_vertex_index"]),
        obstruction["fixed_ear_angles_degrees"] == base["forced_ear_obstruction_angles_degrees"],
        row["eligibility_failures"] == base["eligibility_failures"],
    )
    if not all(checks):
        raise RuntimeError("Attempt 47 exact Attempt 46 candidate evidence drifted")
    crossings = nonadjacent_intersections(
        row["projected_boundary_xy_m"], row["boundary_cycle_mesh_vertex_indices"], 1.0e-12
    )
    expected_crossing = config["attempt46_crossing_evidence"]
    if len(crossings) != 1:
        raise RuntimeError("Attempt 47 Attempt 46 crossing count drifted")
    for key in (
        "kind",
        "first_boundary_edge_index",
        "first_edge_mesh_vertices",
        "second_boundary_edge_index",
        "second_edge_mesh_vertices",
    ):
        if crossings[0][key] != expected_crossing[key]:
            raise RuntimeError(f"Attempt 47 crossing identity drifted: {key}")
    for actual, expected in zip(crossings[0]["intersection_xy_m"], expected_crossing["intersection_xy_m"]):
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1.0e-18):
            raise RuntimeError("Attempt 47 crossing coordinate drifted")
    before, after = integrity.get("before", []), integrity.get("after", [])
    if (
        len(before) != 345
        or len(after) != 345
        or integrity.get("pre_post_exact") is not False
        or integrity.get("relevant_bytecode_cache_inventory_exact") is not True
        or integrity.get("blender_exit_code") != 1
        or integrity.get("native_invocation_error") is not None
    ):
        raise RuntimeError("Attempt 47 bound Attempt 46 wrapper truth drifted")
    before_by_path = {str(item["path"]): item for item in before}
    after_by_path = {str(item["path"]): item for item in after}
    if set(before_by_path) != set(after_by_path):
        raise RuntimeError("Attempt 47 Attempt 46 inventory path set drifted")
    changed: set[str] = set()
    stable_count = 0
    for absolute, before_row in before_by_path.items():
        after_row = after_by_path[absolute]
        relative = _relative_record_path(absolute)
        if before_row != after_row:
            changed.add(relative)
            continue
        current = file_record(Path(absolute))
        if current["bytes"] != int(before_row["bytes"]) or current["sha256"] != before_row["sha256"]:
            raise RuntimeError(f"Attempt 47 stable Attempt 46 input drifted: {relative}")
        stable_count += 1
    if changed != ATTEMPT46_CHANGED_LOGS or stable_count != 343:
        raise RuntimeError("Attempt 47 Attempt 46 log-bookkeeping diagnosis drifted")
    if records["attempt46_stdout"]["sha256"] != after_by_path[str(project_path("RecoverySprint/continuation_20260808/attempt46_blender_stdout.log"))]["sha256"]:
        raise RuntimeError("Attempt 47 final Attempt 46 stdout drifted")
    if records["attempt46_stderr"]["sha256"] != after_by_path[str(project_path("RecoverySprint/continuation_20260808/attempt46_blender_stderr.log"))]["sha256"]:
        raise RuntimeError("Attempt 47 final Attempt 46 stderr drifted")
    cache = project_path(str(config["preserved_existing_bytecode_cache"]["path"]))
    if cache.stat().st_size != 36680 or sha256_file(cache) != EXPECTED_CACHE_SHA256:
        raise RuntimeError("Attempt 47 preserved Attempt 40 cache drifted")
    return {
        "started": started,
        "failure": failure,
        "diagnostic": diagnostic,
        "candidate": row,
        "crossings": crossings,
        "integrity": integrity,
        "stable_inventory_count": stable_count,
        "changed_inventory_paths": sorted(changed),
    }


def reconstruct_attempt46_static(attempt46: Any) -> dict[str, Any]:
    config46 = json.loads(project_path("RecoverySprint/continuation_20260808/R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT46_CONFIG.json").read_text(encoding="utf-8"))
    attempt45 = attempt46.load_static_module("attempt47_bound_attempt45", attempt46.ATTEMPT45_WORKER)
    config45 = json.loads(project_path(str(config46["bindings"]["attempt45_config"]["path"])).read_text(encoding="utf-8"))
    records45 = {str(name): attempt45.require_record(str(name), record) for name, record in config45["bindings"].items()}
    records45["proposal"] = attempt45.require_record("proposal", config45["proposal"])
    evidence44 = attempt45.verify_attempt44_runtime(config45, records45)
    attempt44 = attempt45.load_static_module("attempt47_bound_attempt44", attempt45.ATTEMPT44_WORKER)
    config44 = json.loads(project_path(str(config45["bindings"]["attempt44_config"]["path"])).read_text(encoding="utf-8"))
    context = attempt45.derive_attempt44_context(attempt44, config44)
    source45 = attempt45.derive_attempt45_source(context["source44"])
    source46 = attempt46.derive_attempt46_source(source45)
    if sha256_text(source46) != EXPECTED_ATTEMPT46_DERIVED_SHA256:
        raise RuntimeError("Attempt 47 reproduced a different Attempt 46 source")
    runtime45 = attempt45.build_runtime_config(config45, context["runtime44"], evidence44["diagnostic"])
    runtime46 = attempt46.build_runtime_config(config46, runtime45)
    attempt46.validate_probe_key_contract(source46, runtime46["one_candidate_probe"])
    return {
        "attempt45": attempt45,
        "attempt44": attempt44,
        "config45": config45,
        "evidence44": evidence44,
        "context": context,
        "source46": source46,
        "runtime46": runtime46,
    }


def exact_count_replace(source: str, old: str, new: str, count: int, label: str) -> str:
    actual = source.count(old)
    if actual != count:
        raise RuntimeError(f"Attempt 47 source replacement drifted: {label}: {actual}")
    return source.replace(old, new)


def exact_span_replace(source: str, start: str, end: str, expected_hash: str, replacement: str) -> str:
    start_index = source.index(start)
    end_index = source.index(end, start_index) + len(end)
    existing = source[start_index:end_index]
    if sha256_text(existing) != expected_hash:
        raise RuntimeError("Attempt 47 exact Attempt 46 mapping block drifted")
    return source[:start_index] + replacement + source[end_index:]


def probe_literal_key_counts(source: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Subscript):
            continue
        if not isinstance(node.value, ast.Name) or node.value.id != "probe":
            continue
        key = node.slice
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            raise RuntimeError("Attempt 47 derived AST has a dynamic probe subscript")
        counts[key.value] = counts.get(key.value, 0) + 1
    return dict(sorted(counts.items()))


def validate_probe_key_contract(source: str, probe: Mapping[str, Any]) -> dict[str, int]:
    counts = probe_literal_key_counts(source)
    missing = sorted(set(counts).difference(str(key) for key in probe))
    if missing:
        raise RuntimeError(f"Attempt 47 derived probe keys are absent: {missing}")
    required = {
        "attempt44_chart_maximum_boundary_index",
        "attempt44_chart_maximum_mesh_vertex_index",
        "attempt44_forced_ear_obstruction_boundary_index",
        "attempt44_forced_ear_obstruction_mesh_vertex_index",
        "attempt46_base_source_mesh_vertex_stars",
        "new_compound_blocker_source_mesh_vertex_stars",
    }
    if not required.issubset(counts):
        raise RuntimeError("Attempt 47 derived probe coverage is incomplete")
    return counts


def derive_attempt47_source(source46: str) -> str:
    if sha256_text(source46) != EXPECTED_ATTEMPT46_DERIVED_SHA256:
        raise RuntimeError("Attempt 47 base source drifted")
    source = exact_count_replace(source46, EXPECTED_ATTEMPT46_CONFIG_SHA256, EXPECTED_CONFIG_SHA256, 1, "bind config")
    source = exact_count_replace(
        source,
        "STATIC_READ_ONLY_PROBE_KEY_CONTRACT_REPAIR_PREPARED_NOT_RUN",
        "STATIC_READ_ONLY_LAST_ATTRIBUTABLE_SOURCE_STARS_PREPARED_NOT_RUN",
        1,
        "bind status",
    )
    source = exact_span_replace(
        source,
        "        selected = set(previous_selected)",
        "        targeted.append(row)",
        EXPECTED_ATTEMPT46_MAPPING_BLOCK_SHA256,
        CANDIDATE_MAPPING_REPLACEMENT,
    )
    for old, new in (
        ("attempt_46", "attempt_47"),
        ("attempt46", "attempt47"),
        ("Attempt 46", "Attempt 47"),
        ("ATTEMPT46", "ATTEMPT47"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 47 identity token disappeared: {old}")
        source = source.replace(old, new)
    source = source.replace("__BASE_ATTEMPT__", "attempt46")
    source = source.replace("__BASE_ATTEMPT_TITLE__", "Attempt 46")
    source = exact_count_replace(
        source,
        '            "attempt44_complete_candidate_reverified": previous_row,\n',
        '            "attempt44_complete_candidate_reverified": previous_row,\n'
        '            "attempt46_complete_candidate_reverified": candidate_base_row,\n',
        1,
        "record Attempt 46 base provenance",
    )
    source = exact_count_replace(
        source,
        '                "attempt44_complete_candidate_used_only_as_read_only_base": True,\n',
        '                "attempt44_complete_candidate_used_only_as_read_only_base": True,\n'
        '                "attempt46_complete_candidate_used_only_as_read_only_base": True,\n'
        '                "source_star_expansion_terminal_if_candidate_fails": True,\n',
        1,
        "record terminal provenance",
    )
    ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    for token in (
        '"complete_attempt46_domain_plus_complete_mesh_vertex_stars_351_248_676"',
        '"attempt46_complete_candidate_reverified"',
        '"attempt46_base_source_star_rows"',
        '"terminal_source_star_rule"',
        '"source_star_expansion_terminal_if_candidate_fails"',
        '"boundary_deviation_attribution"',
    ):
        if token not in source:
            raise RuntimeError(f"Attempt 47 derived evidence is absent: {token}")
    for token in (
        "bpy.ops.wm.save",
        "bpy.ops.render",
        "bpy.ops.export",
        "bpy.ops.object.join",
        "bmesh.ops.delete",
        "to_mesh(",
    ):
        if token in source:
            raise RuntimeError(f"Attempt 47 derived source is forbidden: {token}")
    return source


def build_runtime_config(config: Mapping[str, Any], runtime46: Mapping[str, Any]) -> dict[str, Any]:
    runtime = json.loads(json.dumps(runtime46))
    for key in ("attempt_id", "status", "mode", "scope", "output", "proposal", "truth"):
        runtime[key] = json.loads(json.dumps(config[key]))
    runtime["bindings"].update(json.loads(json.dumps(config["bindings"])))
    probe = json.loads(json.dumps(runtime46["one_candidate_probe"]))
    probe.update(json.loads(json.dumps(config["one_candidate_probe"])))
    probe["required_complete_source_mesh_vertex_stars"] = [241, 218, 508, 351, 248, 676]
    runtime["one_candidate_probe"] = probe
    runtime["attempt46_base_contract"] = json.loads(json.dumps(config["attempt46_base_contract"]))
    runtime["terminal_source_star_rule"] = json.loads(json.dumps(config["terminal_source_star_rule"]))
    return runtime


def verify_package(config: Mapping[str, Any]) -> dict[str, Any]:
    records = {str(name): require_record(str(name), record) for name, record in config["bindings"].items()}
    records["proposal"] = require_record("proposal", config["proposal"])
    evidence46 = verify_attempt46_runtime(config, records)
    attempt46 = load_static_module("attempt47_bound_attempt46", ATTEMPT46_WORKER)
    reconstructed = reconstruct_attempt46_static(attempt46)
    runtime = build_runtime_config(config, reconstructed["runtime46"])
    source = derive_attempt47_source(reconstructed["source46"])
    probe_counts = validate_probe_key_contract(source, runtime["one_candidate_probe"])
    namespace = {
        "__name__": "attempt47_static_runtime_contract",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
    }
    exec(compile(source, str(Path(__file__).resolve()) + "::derived-contract", "exec"), namespace, namespace)
    namespace["validate_config"](runtime)
    derived_hash = sha256_text(source)
    if EXPECTED_DERIVED_SHA256 != "TO_BE_BOUND_AFTER_STATIC_DERIVATION" and derived_hash != EXPECTED_DERIVED_SHA256:
        raise RuntimeError(f"Attempt 47 derived source hash drifted: {derived_hash}")
    return {
        "records": records,
        "attempt46_evidence": evidence46,
        "attempt46": attempt46,
        "reconstructed": reconstructed,
        "runtime_config": runtime,
        "derived_source": source,
        "derived_source_sha256": derived_hash,
        "probe_literal_key_counts": probe_counts,
    }


def run_blender(config: Mapping[str, Any], verified: Mapping[str, Any]) -> None:
    validate_probe_key_contract(str(verified["derived_source"]), verified["runtime_config"]["one_candidate_probe"])
    context = verified["reconstructed"]
    config45 = context["config45"]
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "ATTEMPT47_RUNTIME_CONFIG": verified["runtime_config"],
        "ATTEMPT47_RUNTIME_RESULT": json.loads(json.dumps(config45["attempt44_runtime_result"])),
        "ATTEMPT47_RUNTIME_BASE_DOMAIN": json.loads(json.dumps(config45["attempt43_base_domain"])),
        "ATTEMPT47_RUNTIME_PROBE": json.loads(json.dumps(verified["runtime_config"]["one_candidate_probe"])),
        "ATTEMPT47_BOUND_COORDINATE_ONLY": json.loads(json.dumps(context["evidence44"]["diagnostic"]["coordinate_only_analysis"])),
    }
    exec(compile(str(verified["derived_source"]), str(Path(__file__).resolve()) + "::derived", "exec"), namespace, namespace)


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    values = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args(values)


def main() -> None:
    args = parse_args()
    config = load_config(Path(args.config).resolve(strict=True))
    verified = verify_package(config)
    run_blender(config, verified)


if __name__ == "__main__":
    main()
