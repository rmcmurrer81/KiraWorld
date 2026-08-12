"""Attempt 40 read-only wider source-domain feasibility proof.

Static validation binds the exact Attempt 39 terminal fixed-ear failure and
proves that all seven Attempt 30 eligible boundaries fail a stronger necessary
12-degree condition.  A later independently reviewed Blender run may map one
source-aligned wider domain.  It cannot triangulate, reconstruct, mutate, save,
render, export, activate, assign, publish, or retry.

Importing this module is Blender-free.
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
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT40_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = (
    "26bdb0f8a7eb6651260eb84f37d7714453e2620f3add3f864f89051732a17493"
)
ATTEMPT30_WORKER = (
    ROOT / "tools/blender_diagnose_kira_r24_blackproject_ordered_topology_attempt30.py"
)
EXPECTED_ATTEMPT30_WORKER_SHA256 = (
    "204a386b90db731ce6d4d83ceb59afb79ec6ceeb23d3384ea300f0b3e5f6f31b"
)
EXPECTED_ATTEMPT30_CONFIG_SHA256 = (
    "f040e298af2158391d9818139f5a861d36d3ef121c91d168adce3a10b499743c"
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
        raise RuntimeError(f"Attempt 40 path escapes project: {value}")
    return path


def _load_static_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Attempt 40 cannot load bound module: {path.name}")
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
        raise RuntimeError(f"Attempt 40 binding byte count drifted: {name}")
    if actual["sha256"] != str(record["sha256"]).lower():
        raise RuntimeError(
            f"Attempt 40 binding hash drifted: {name}: {actual['sha256']}"
        )
    return actual


def _triangle_angle(
    first: Sequence[float], center: Sequence[float], third: Sequence[float]
) -> float:
    ux = float(first[0]) - float(center[0])
    uy = float(first[1]) - float(center[1])
    vx = float(third[0]) - float(center[0])
    vy = float(third[1]) - float(center[1])
    first_length = math.hypot(ux, uy)
    second_length = math.hypot(vx, vy)
    if first_length <= 0.0 or second_length <= 0.0:
        return 0.0
    cosine = max(
        -1.0,
        min(1.0, (ux * vx + uy * vy) / (first_length * second_length)),
    )
    return float(math.degrees(math.acos(cosine)))


def forced_ear_feasibility(
    row: Mapping[str, Any], target_degrees: float = 12.0, tolerance: float = 1.0e-12
) -> dict[str, Any]:
    """Return the necessary fixed-ear result for a projected source boundary."""

    points = list(row["projected_boundary_xy_m"])
    corner_rows = list(row["boundary_angle_analysis"]["corner_rows"])
    if len(points) != len(corner_rows) or len(points) < 3:
        raise RuntimeError("Attempt 40 boundary/corner cardinality drifted")
    tested = []
    obstructions = []
    for corner in corner_rows:
        index = int(corner["boundary_index"])
        interior = float(corner["interior_angle_degrees"])
        if interior >= 180.0:
            continue
        if interior + tolerance < target_degrees:
            continue
        if interior + tolerance >= 2.0 * target_degrees:
            continue
        previous = points[(index - 1) % len(points)]
        current = points[index]
        following = points[(index + 1) % len(points)]
        angles = [
            _triangle_angle(current, previous, following),
            _triangle_angle(previous, current, following),
            _triangle_angle(previous, following, current),
        ]
        minimum = min(angles)
        record = {
            "boundary_index": index,
            "interior_angle_degrees": interior,
            "fixed_ear_angles_degrees": angles,
            "fixed_ear_minimum_angle_degrees": float(minimum),
            "target_degrees": float(target_degrees),
            "passes": minimum + tolerance >= target_degrees,
        }
        tested.append(record)
        if not record["passes"]:
            obstructions.append(record)
    return {
        "rule": (
            "convex_corner_alpha_in_[T,2T)_requires_one_fixed_"
            "prev-current-next_ear_with_all_angles_at_least_T"
        ),
        "target_degrees": float(target_degrees),
        "tolerance_degrees": float(tolerance),
        "tested_corner_count": len(tested),
        "tested_corners": tested,
        "obstruction_count": len(obstructions),
        "obstructions": obstructions,
        "passes": not obstructions,
    }


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 40 requires the exact sealed config path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 40 config hash drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_40"
        or config.get("status")
        != "STATIC_READ_ONLY_DOMAIN_PROOF_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 40 identity drifted")
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
        "exact_one_wider_source_domain_mapping_allowed",
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
        "automatic_alternate_candidate_allowed",
        "automatic_retry_allowed",
    )
    if not all(bool(scope[name]) for name in required_true):
        raise RuntimeError("Attempt 40 lost a required read-only scope")
    if any(bool(scope[name]) for name in forbidden):
        raise RuntimeError("Attempt 40 permits a forbidden operation")
    output = config["output"]
    if output != {
        "root": (
            "RecoverySprint/continuation_20260803/"
            "kira_r24_internal_midpoint_fair_surface/attempt_40"
        ),
        "started": "ATTEMPT_STARTED.json",
        "diagnostic": "WIDER_SOURCE_DOMAIN_FEASIBILITY_DIAGNOSTIC.json",
        "failure": "FAILURE.json",
        "blend_save_permitted": False,
        "render_permitted": False,
    }:
        raise RuntimeError("Attempt 40 output contract drifted")
    if project_path(str(output["root"]), must_exist=False).exists():
        raise RuntimeError("Attempt 40 output already exists")
    hard = config["unchanged_hard_gates"]
    if (
        float(hard["minimum_new_triangle_angle_degrees"]) != 12.0
        or float(hard["minimum_new_triangle_world_area_m2"]) != 1.0e-10
        or int(hard["maximum_new_interior_vertex_count"]) != 160
        or int(hard["maximum_quality_refinement_iterations"]) != 192
        or int(hard["global_seam_vertex_count"]) != 34
        or float(hard["global_seam_coordinate_delta_m"]) != 0.0
        or bool(hard["save_allowed_without_owner_visual_acceptance"])
    ):
        raise RuntimeError("Attempt 40 hard gate drifted")
    probe = config["one_wider_source_domain_probe"]
    if (
        probe["candidate"]
        != "targeted_complete_vertex_stars_2_6_9_19_20_28"
        or probe["capture_source_indices"] != [2, 6, 9, 19, 20, 28]
        or probe["source_mesh_vertex_indices"] != [90, 418, 504, 534, 407, 91]
        or probe["added_exact_obstructing_capture_source_indices"] != [9, 19]
        or probe["added_exact_obstructing_mesh_vertex_indices"] != [504, 534]
        or not bool(probe["complete_source_vertex_stars_only"])
        or bool(probe["uniform_face_ring_candidates_allowed"])
        or bool(probe["alternate_target_sets_allowed"])
    ):
        raise RuntimeError("Attempt 40 one-candidate probe drifted")
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
        or launch["worker"]
        != "tools/blender_diagnose_kira_r24_blackproject_wider_source_domain_attempt40.py"
        or launch["config"]
        != "RecoverySprint/continuation_20260808/R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT40_CONFIG.json"
        or not bool(launch["wrapper_owns_stdout_stderr_and_integrity"])
        or not bool(launch["worker_checks_only_runtime_output_root_absent"])
        or bool(launch["worker_writes_external_targets"])
        or not bool(launch["exactly_one_blender_invocation_required"])
        or not bool(launch["refuse_any_overwrite"])
        or bool(launch["executed_during_static_preparation"])
    ):
        raise RuntimeError("Attempt 40 launch contract drifted")
    truth = config["truth"]
    forbidden_truth = (
        "attempt40_blender_execution_performed",
        "attempt40_source_domain_mapping_performed",
        "attempt40_candidate_feasibility_proven",
        "attempt40_triangulation_performed",
        "attempt40_reconstruction_performed",
        "attempt40_body_mutation_performed",
        "attempt40_render_reached",
        "attempt40_blend_saved",
        "runtime_changed",
        "executable_body_repair_justified",
        "body_repair_proven",
        "owner_approval_claimed",
    )
    if any(bool(truth[name]) for name in forbidden_truth):
        raise RuntimeError("Attempt 40 static truth overclaims execution or repair")


def _simplified_obstructions(result: Mapping[str, Any]) -> list[dict[str, float]]:
    return [
        {
            "boundary_index": int(row["boundary_index"]),
            "interior_angle_degrees": float(row["interior_angle_degrees"]),
            "fixed_ear_minimum_angle_degrees": float(
                row["fixed_ear_minimum_angle_degrees"]
            ),
        }
        for row in result["obstructions"]
    ]


def _obstructions_match(
    actual: Sequence[Mapping[str, Any]], expected: Sequence[Mapping[str, Any]]
) -> bool:
    if len(actual) != len(expected):
        return False
    for first, second in zip(actual, expected):
        if int(first["boundary_index"]) != int(second["boundary_index"]):
            return False
        for name in (
            "interior_angle_degrees",
            "fixed_ear_minimum_angle_degrees",
        ):
            if not math.isclose(
                float(first[name]), float(second[name]), rel_tol=0.0, abs_tol=1.0e-12
            ):
                return False
    return True


def verify_package(config: Mapping[str, Any]) -> dict[str, Any]:
    records = {
        str(name): require_record(str(name), record)
        for name, record in config["bindings"].items()
    }
    records["proposal"] = require_record("proposal", config["proposal"])
    if records["attempt30_worker"]["sha256"] != EXPECTED_ATTEMPT30_WORKER_SHA256:
        raise RuntimeError("Attempt 40 bound Attempt 30 worker disagrees")
    if records["attempt30_config"]["sha256"] != EXPECTED_ATTEMPT30_CONFIG_SHA256:
        raise RuntimeError("Attempt 40 bound Attempt 30 config disagrees")

    trials = json.loads(
        project_path(records["attempt39_trials"]["path"]).read_text(encoding="utf-8")
    )
    failure = json.loads(
        project_path(records["attempt39_failure"]["path"]).read_text(encoding="utf-8")
    )
    blocker = config["attempt39_terminal_blocker"]
    terminal = trials["iterations"][-1]
    if (
        trials.get("attempt_id") != "attempt_39"
        or trials["error"] != blocker["error"]
        or failure["error"] != blocker["error"]
        or trials["iteration_count"] != 6
        or terminal["iteration"] != 5
        or terminal["accepted_seed_count_before"] != 33
        or terminal["worst_face"] != [24, 22, 23]
        or [row["output_indices"] for row in terminal["constrained_face_edges"]]
        != [[22, 23], [23, 24]]
        or terminal["nonboundary_face_outputs"]
        or terminal["matched_seed_rows"]
        or terminal["trials"]
        or failure["render_reached"]
        or failure["blend_saved"]
        or failure["runtime_changed"]
    ):
        raise RuntimeError("Attempt 40 bound Attempt 39 terminal truth drifted")
    integrity = json.loads(
        project_path(records["attempt39_external_integrity"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    if (
        integrity["blender_exit_code"] != 1
        or integrity["native_invocation_error"] is not None
        or integrity["pre_post_exact"] is not True
        or integrity["before"] != integrity["after"]
        or len(integrity["before"]) != 252
    ):
        raise RuntimeError("Attempt 40 bound Attempt 39 integrity drifted")

    diagnostic = json.loads(
        project_path(records["attempt30_diagnostic"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    if (
        diagnostic.get("attempt_id") != "attempt_30"
        or diagnostic.get("necessary_eligible_candidate_count") != 7
        or diagnostic["truth"]["mesh_mutated"]
        or diagnostic["truth"]["body_mutated"]
        or diagnostic["truth"]["render_reached"]
        or diagnostic["truth"]["blend_saved"]
        or diagnostic["truth"]["runtime_changed"]
    ):
        raise RuntimeError("Attempt 40 bound Attempt 30 diagnostic drifted")
    candidates = list(diagnostic["targeted_complete_vertex_star_candidates"]) + list(
        diagnostic["uniform_face_ring_candidates"]
    )
    eligible = [
        row for row in candidates if bool(row["necessary_candidate_eligibility_passes"])
    ]
    eligible.sort(key=lambda row: (int(row["face_count"]), str(row["candidate"])))
    expected_rows = config["forced_ear_contract"]["previous_candidate_obstructions"]
    by_name = {str(row["candidate"]): row for row in eligible}
    if set(by_name) != {str(row["candidate"]) for row in expected_rows}:
        raise RuntimeError("Attempt 40 seven-candidate identity drifted")
    forced_rows = []
    for expected in expected_rows:
        name = str(expected["candidate"])
        result = forced_ear_feasibility(by_name[name])
        actual = _simplified_obstructions(result)
        if result["passes"] or not _obstructions_match(actual, expected["obstructions"]):
            raise RuntimeError(f"Attempt 40 forced-ear proof drifted: {name}")
        forced_rows.append(
            {
                "candidate": name,
                "candidate_face_count": int(by_name[name]["face_count"]),
                "candidate_boundary_edge_count": int(
                    by_name[name]["boundary_edge_count"]
                ),
                "result": result,
            }
        )
    if len(forced_rows) != 7 or any(row["result"]["passes"] for row in forced_rows):
        raise RuntimeError("Attempt 40 did not prove all seven boundaries infeasible")

    selected = diagnostic["smallest_necessary_eligible_existing_source_candidate"]
    alignment = diagnostic["capture_to_source_mesh_alignment"][
        "capture_source_index_to_mesh_vertex_index"
    ]
    selected_cycle = selected["boundary_cycle_mesh_vertex_indices"]
    if (
        int(selected_cycle[13]) != 504
        or int(selected_cycle[23]) != 534
        or int(alignment[9]) != 504
        or int(alignment[19]) != 534
    ):
        raise RuntimeError("Attempt 40 exact obstructing source identity drifted")
    probe = config["one_wider_source_domain_probe"]
    if [int(alignment[index]) for index in probe["capture_source_indices"]] != probe[
        "source_mesh_vertex_indices"
    ]:
        raise RuntimeError("Attempt 40 wider source-domain mapping drifted")

    attempt30 = _load_static_module("attempt40_bound_attempt30", ATTEMPT30_WORKER)
    attempt30_overlay = attempt30.load_overlay(
        project_path(records["attempt30_config"]["path"])
    )
    attempt30.verify_overlay_bindings(attempt30_overlay)
    runtime = build_runtime_config(config, attempt30, attempt30_overlay, diagnostic)
    source = derive_attempt40_source(config, attempt30)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    derived_namespace = {
        "__name__": "attempt40_static_runtime_contract",
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
        "attempt39_trials": trials,
        "attempt39_failure": failure,
        "attempt39_integrity": integrity,
        "attempt30_diagnostic": diagnostic,
        "forced_rows": forced_rows,
        "attempt30": attempt30,
        "attempt30_overlay": attempt30_overlay,
        "runtime_config": runtime,
        "derived_source": source,
        "derived_source_sha256": sha256_text(source),
    }


ATTEMPT40_FORCED_HELPER = r'''
def attempt40_triangle_angle(first, center, third):
    ux = float(first[0]) - float(center[0])
    uy = float(first[1]) - float(center[1])
    vx = float(third[0]) - float(center[0])
    vy = float(third[1]) - float(center[1])
    first_length = math.hypot(ux, uy)
    second_length = math.hypot(vx, vy)
    if first_length <= 0.0 or second_length <= 0.0:
        return 0.0
    cosine = max(-1.0, min(1.0, (ux * vx + uy * vy) / (first_length * second_length)))
    return float(math.degrees(math.acos(cosine)))


def attempt40_forced_ear_feasibility(row, target_degrees=12.0, tolerance=1.0e-12):
    points = list(row["projected_boundary_xy_m"])
    tested = []
    obstructions = []
    for corner in row["boundary_angle_analysis"]["corner_rows"]:
        index = int(corner["boundary_index"])
        interior = float(corner["interior_angle_degrees"])
        if interior >= 180.0 or interior + tolerance < target_degrees or interior + tolerance >= 2.0 * target_degrees:
            continue
        previous = points[(index - 1) % len(points)]
        current = points[index]
        following = points[(index + 1) % len(points)]
        angles = [
            attempt40_triangle_angle(current, previous, following),
            attempt40_triangle_angle(previous, current, following),
            attempt40_triangle_angle(previous, following, current),
        ]
        minimum = min(angles)
        record = {
            "boundary_index": index,
            "interior_angle_degrees": interior,
            "fixed_ear_angles_degrees": angles,
            "fixed_ear_minimum_angle_degrees": float(minimum),
            "target_degrees": float(target_degrees),
            "passes": minimum + tolerance >= target_degrees,
        }
        tested.append(record)
        if not record["passes"]:
            obstructions.append(record)
    return {
        "rule": "convex_corner_alpha_in_[T,2T)_requires_one_fixed_prev-current-next_ear_with_all_angles_at_least_T",
        "target_degrees": float(target_degrees),
        "tolerance_degrees": float(tolerance),
        "tested_corner_count": len(tested),
        "tested_corners": tested,
        "obstruction_count": len(obstructions),
        "obstructions": obstructions,
        "passes": not obstructions,
    }
'''


def exact_replace(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Attempt 40 source replacement drifted: {label}: {count}")
    return source.replace(old, new, 1)


def derive_attempt40_source(config: Mapping[str, Any], attempt30: Any) -> str:
    if sha256_file(ATTEMPT30_WORKER) != EXPECTED_ATTEMPT30_WORKER_SHA256:
        raise RuntimeError("Attempt 30 worker changed before Attempt 40 derivation")
    source28 = attempt30.ATTEMPT28_WORKER.read_text(encoding="utf-8")
    source = attempt30.derive_attempt30_source(source28)
    source = exact_replace(
        source,
        "STATIC_DIAGNOSTIC_PREPARED_NOT_RUN",
        "STATIC_READ_ONLY_DOMAIN_PROOF_PREPARED_NOT_RUN",
        "bind Attempt 40 runtime status",
    )
    source = exact_replace(
        source,
        EXPECTED_ATTEMPT30_CONFIG_SHA256,
        EXPECTED_CONFIG_SHA256,
        "bind Attempt 40 config hash",
    )
    source = exact_replace(
        source,
        "def run_blender_diagnostic(",
        ATTEMPT40_FORCED_HELPER + "\n\ndef run_blender_diagnostic(",
        "insert forced-ear helper",
    )
    old_target = (
        '            row["added_complete_vertex_star_face_indices"] = sorted(added_faces)\n'
        "            targeted.append(row)\n"
    )
    new_target = (
        '            row["added_complete_vertex_star_face_indices"] = sorted(added_faces)\n'
        "            forced_ear = attempt40_forced_ear_feasibility(\n"
        '                row, float(config["diagnosis"]["required_minimum_angle_degrees"])\n'
        "            )\n"
        '            row["forced_ear_feasibility"] = forced_ear\n'
        '            if not forced_ear["passes"]:\n'
        '                row["necessary_candidate_eligibility_passes"] = False\n'
        '                row["eligibility_failures"] = list(row["eligibility_failures"]) + [\n'
        '                    "forced_prev_current_next_ear_all_angles_at_least_12_degrees"\n'
        "                ]\n"
        "            targeted.append(row)\n"
    )
    source = exact_replace(
        source, old_target, new_target, "apply forced-ear candidate eligibility"
    )
    old_coordinate = (
        "        coordinate_only = analyze_coordinate_suppressions(\n"
        "            capture,\n"
        '            int(config["coordinate_only_analysis"]["first_passing_suppression_cardinality"]),\n'
        '            float(config["diagnosis"]["required_minimum_angle_degrees"]),\n'
        "        )\n"
    )
    source = exact_replace(
        source,
        old_coordinate,
        "        coordinate_only = ATTEMPT40_BOUND_COORDINATE_ONLY\n",
        "reuse bound coordinate-only analysis",
    )
    old_diagnostic = (
        '            "source_identity_contract_evidence": source_identity_evidence,\n'
        '            "targeted_complete_vertex_star_candidates": targeted,\n'
    )
    new_diagnostic = (
        '            "source_identity_contract_evidence": source_identity_evidence,\n'
        '            "attempt39_fixed_ear_blocker": ATTEMPT40_RUNTIME_BLOCKER,\n'
        '            "one_wider_source_domain_probe": ATTEMPT40_RUNTIME_PROBE,\n'
        '            "targeted_complete_vertex_star_candidates": targeted,\n'
    )
    source = exact_replace(
        source, old_diagnostic, new_diagnostic, "record Attempt 40 proof provenance"
    )
    source = exact_replace(
        source,
        '                "necessary_candidate_is_sufficient_repair_proof": False,\n',
        '                "necessary_candidate_is_sufficient_repair_proof": False,\n'
        '                "executable_body_repair_justified": False,\n',
        "record no executable repair claim",
    )
    for old, new in (
        ("attempt_30", "attempt_40"),
        ("attempt30", "attempt40"),
        ("Attempt 30", "Attempt 40"),
        ("ATTEMPT30", "ATTEMPT40"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 40 source identity token disappeared: {old}")
        source = source.replace(old, new)
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "attempt40_source_identity_evidence",
        "attempt40_forced_ear_feasibility",
        "run_blender_diagnostic",
        "_domain_diagnostic",
    }
    if not required.issubset(names):
        raise RuntimeError("Attempt 40 derived read-only helpers are absent")
    for stale in ("attempt_30", "attempt30", "Attempt 30", "ATTEMPT30"):
        if stale in source:
            raise RuntimeError(f"Attempt 40 derived source retained stale token: {stale}")
    forbidden_calls = (
        "bpy.ops.wm.save",
        "bpy.ops.render",
        "bpy.ops.export",
        "bpy.ops.object.join",
        "bmesh.ops.delete",
        "to_mesh(",
    )
    if any(value in source for value in forbidden_calls):
        raise RuntimeError("Attempt 40 derived source contains a forbidden operation")
    return source


def build_runtime_config(
    config: Mapping[str, Any],
    attempt30: Any,
    attempt30_overlay: Mapping[str, Any],
    attempt30_diagnostic: Mapping[str, Any],
) -> dict[str, Any]:
    runtime = attempt30.build_runtime_config(attempt30_overlay)
    for key in ("attempt_id", "status", "mode", "scope", "output", "proposal", "truth"):
        runtime[key] = json.loads(json.dumps(config[key]))
    runtime["unchanged_hard_gates"] = json.loads(
        json.dumps(config["unchanged_hard_gates"])
    )
    runtime["source_identity_contract"] = json.loads(
        json.dumps(config["source_identity_contract"])
    )
    runtime["bindings"].update(json.loads(json.dumps(config["bindings"])))
    runtime["source_mesh_diagnostic"]["targeted_vertex_star_suppression_sets"] = [
        list(config["one_wider_source_domain_probe"]["capture_source_indices"])
    ]
    runtime["source_mesh_diagnostic"]["uniform_face_ring_expansions_to_map"] = [0]
    runtime["source_mesh_diagnostic"]["eligible_candidate_requires"] = list(
        runtime["source_mesh_diagnostic"]["eligible_candidate_requires"]
    ) + ["forced_prev_current_next_ear_all_angles_at_least_12_degrees"]
    runtime["attempt39_terminal_blocker"] = json.loads(
        json.dumps(config["attempt39_terminal_blocker"])
    )
    runtime["one_wider_source_domain_probe"] = json.loads(
        json.dumps(config["one_wider_source_domain_probe"])
    )
    runtime["coordinate_only_analysis"] = json.loads(
        json.dumps(attempt30_diagnostic["coordinate_only_analysis"])
    )
    return runtime


def run_blender(config_path: Path, config: Mapping[str, Any]) -> None:
    verified = verify_package(config)
    source = verified["derived_source"]
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "ATTEMPT40_RUNTIME_CONFIG": verified["runtime_config"],
        "ATTEMPT40_RUNTIME_BLOCKER": json.loads(
            json.dumps(config["attempt39_terminal_blocker"])
        ),
        "ATTEMPT40_RUNTIME_PROBE": json.loads(
            json.dumps(config["one_wider_source_domain_probe"])
        ),
        "ATTEMPT40_BOUND_COORDINATE_ONLY": json.loads(
            json.dumps(verified["attempt30_diagnostic"]["coordinate_only_analysis"])
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
