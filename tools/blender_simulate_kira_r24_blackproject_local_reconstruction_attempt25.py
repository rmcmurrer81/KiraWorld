"""Hash-bound Attempt 25 refinement-candidate admissibility repair.

The wrapper derives sealed Attempt 24, rejects geometrically near-duplicate
refinement candidates with an area/angle/local-edge scale, tries the centroid
after a rejected incenter, and retains every existing quality and no-save gate.
Blender is not imported during static inspection.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260807"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT25_CONFIG.json"
)
ATTEMPT24_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt24.py"
ATTEMPT23_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt23.py"
ATTEMPT22_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt22.py"
ATTEMPT21_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt21.py"
ATTEMPT20_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt20.py"
ATTEMPT19_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt19.py"
ATTEMPT18_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt18.py"
EXPECTED_CONFIG_SHA256 = "f758b3ec3bd2e8add0e1acf9eb66f03dd745278353b9f836d712c90a60867e7b"
EXPECTED_ATTEMPT24_WORKER_SHA256 = "adb636ad672882ebaecfd705eb9e029efca9000a005c19ac0f8085a2b64de611"


def load_attempt24_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "attempt25_sealed_attempt24_provider", ATTEMPT24_WORKER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Attempt 25 could not load the sealed Attempt 24 provider")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = (ROOT / value).resolve(strict=True)
    root = ROOT.resolve()
    if root != path and root not in path.parents:
        raise RuntimeError(f"Attempt 25 binding escapes project: {value}")
    return path


def verify_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(record["path"]))
    actual_bytes = path.stat().st_size
    actual_sha256 = sha256_file(path)
    if actual_bytes != int(record["bytes"]):
        raise RuntimeError(f"Attempt 25 bound byte count drifted: {name}")
    if actual_sha256 != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 25 bound hash drifted: {name}: {actual_sha256}")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": actual_bytes,
        "sha256": actual_sha256,
    }


def load_overlay(config_path: Path) -> dict[str, Any]:
    config_path = config_path.resolve(strict=True)
    if config_path != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 25 requires the exact sealed overlay config path")
    actual = sha256_file(config_path)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 25 overlay config hash drifted: {actual}")
    overlay = json.loads(config_path.read_text(encoding="utf-8"))
    if (
        overlay.get("attempt_id") != "attempt_25"
        or overlay.get("status") != "STATIC_ACTUAL_REPAIR_PREPARED_NOT_RUN"
        or overlay.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 25 overlay identity drifted")
    required_true = (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "repair_simulation_only",
        "candidate_seed_policy_change_allowed",
        "in_memory_local_body_reconstruction_allowed_during_later_reviewed_run",
    )
    if not all(bool(overlay["scope"][name]) for name in required_true):
        raise RuntimeError("Attempt 25 repair scope lost a required private gate")
    forbidden = (
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "boundary_or_seam_movement_allowed",
        "quality_gate_reduction_allowed",
        "render_allowed",
        "boundary_repair_allowed",
        "generic_hole_fill_allowed",
        "sanitation_weakening_allowed",
        "whole_polygon_retriangulation_allowed",
    )
    if any(bool(overlay["scope"][name]) for name in forbidden):
        raise RuntimeError("Attempt 25 scope permits a forbidden operation")
    return overlay


def verify_overlay_bindings(overlay: Mapping[str, Any]) -> dict[str, Any]:
    verified = {
        name: verify_record(name, record)
        for name, record in overlay["bindings"].items()
    }
    verified["proposal"] = verify_record("proposal", overlay["proposal"])
    if verified["attempt24_worker"]["sha256"] != EXPECTED_ATTEMPT24_WORKER_SHA256:
        raise RuntimeError("Attempt 25 provider constant and binding disagree")
    preserved = overlay["preserved_attempt24_package"]
    rows = [verified[name] for name in preserved["binding_names"]]
    if len(rows) != int(preserved["file_count"]):
        raise RuntimeError("Attempt 24 preserved package file count drifted")
    if sum(int(row["bytes"]) for row in rows) != int(preserved["total_bytes"]):
        raise RuntimeError("Attempt 24 preserved package byte total drifted")
    return verified


def validate_policy_contract(overlay: Mapping[str, Any]) -> None:
    policy = overlay["candidate_admissibility_policy"]
    captured = policy["captured_case"]
    area_floor = (
        2.0
        * float(captured["minimum_world_area_m2"])
        / float(captured["local_longest_edge_m"])
    )
    angle_floor = float(captured["local_shortest_edge_m"]) * math.sin(
        math.radians(float(captured["target_angle_degrees"]))
    )
    required = max(float(captured["point_floor_m"]), min(area_floor, angle_floor))
    checks = {
        "area_altitude_floor_m": area_floor,
        "angle_altitude_floor_m": angle_floor,
        "required_separation_m": required,
        "required_separation_relative_to_boundary_diagonal": required
        / float(captured["boundary_diagonal_m"]),
    }
    for name, actual in checks.items():
        expected = float(captured[name])
        if not math.isclose(actual, expected, rel_tol=1.0e-12, abs_tol=1.0e-18):
            raise RuntimeError(f"Attempt 25 captured policy derivation drifted: {name}")
    if policy["candidate_order"] != ["triangle_incenter", "triangle_centroid"]:
        raise RuntimeError("Attempt 25 candidate order drifted")
    if bool(policy["new_arbitrary_length_constant"]):
        raise RuntimeError("Attempt 25 introduced an arbitrary length constant")


def load_attempt25_config(config_path: Path) -> dict[str, Any]:
    overlay = load_overlay(config_path)
    validate_policy_contract(overlay)
    verified = verify_overlay_bindings(overlay)
    provider = load_attempt24_module()
    base_config_path = project_path(overlay["bindings"]["attempt24_config"]["path"])
    merged = provider.load_attempt24_config(base_config_path)
    if merged.get("attempt_id") != overlay["base"]["expected_config_attempt_id"]:
        raise RuntimeError("Attempt 24 materialized base identity drifted")
    merged = copy.deepcopy(merged)
    merged["schema"] = "kira.avatar.r24.blackproject_local_reconstruction_attempt25.config.v1"
    merged["attempt_id"] = "attempt_25"
    merged["output"] = copy.deepcopy(overlay["output"])
    path_contract = overlay["failure_capture_path_contract"]
    expected_relative = (
        f'{overlay["output"]["root"]}/'
        f'{overlay["output"]["cdt_candidate_repair_failure"]}'
    )
    if path_contract["project_relative_path"] != expected_relative:
        raise RuntimeError("Attempt 25 failure path contract disagrees with output")
    merged["replacement"][path_contract["replacement_key"]] = expected_relative
    merged["attempt25_diagnosis"] = copy.deepcopy(overlay["diagnosis"])
    merged["attempt25_candidate_admissibility_policy"] = copy.deepcopy(
        overlay["candidate_admissibility_policy"]
    )
    merged["attempt25_repair_contract"] = copy.deepcopy(overlay["repair_contract"])
    merged["attempt25_unchanged_hard_gates"] = copy.deepcopy(
        overlay["unchanged_hard_gates"]
    )
    merged["attempt25_evidence_label_contract"] = copy.deepcopy(
        overlay["evidence_label_contract"]
    )
    merged["attempt25_truth"] = copy.deepcopy(overlay["truth"])
    merged["inputs"].update(
        {
            f"attempt25_bound_{name}": {
                "path": record["path"],
                "bytes": record["bytes"],
                "sha256": record["sha256"],
            }
            for name, record in verified.items()
        }
    )
    unchanged = overlay["unchanged_hard_gates"]
    for location in ("replacement", "hard_gates"):
        if float(merged[location]["minimum_new_triangle_angle_degrees"]) != float(
            unchanged["minimum_new_triangle_angle_degrees"]
        ):
            raise RuntimeError(f"Attempt 25 {location} minimum-angle gate drifted")
    if float(merged["replacement"]["minimum_new_triangle_world_area_m2"]) != float(
        unchanged["minimum_new_triangle_world_area_m2"]
    ):
        raise RuntimeError("Attempt 25 minimum-area gate drifted")
    return merged


REPAIRED_QUALITY_REFINEMENT = r'''def attempt25_candidate_separation_diagnostics(
    candidate: Vector,
    method: str,
    local_points: Sequence[Vector],
    boundary: Sequence[Vector],
    seeds: Sequence[Vector],
    epsilon: float,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    if len(local_points) != 3:
        raise RuntimeError("Attempt 25 candidate policy requires one triangle")
    tolerances = cdt_tolerances(boundary, epsilon, config)
    edge_lengths = [
        float((local_points[first] - local_points[second]).length)
        for first, second in ((0, 1), (1, 2), (2, 0))
    ]
    if any(not math.isfinite(value) or value <= 0.0 for value in edge_lengths):
        raise RuntimeError("Attempt 25 candidate policy received a degenerate local edge")
    local_shortest = min(edge_lengths)
    local_longest = max(edge_lengths)
    minimum_area = float(config["minimum_new_triangle_world_area_m2"])
    target_angle = float(config["minimum_new_triangle_angle_degrees"])
    if not math.isfinite(minimum_area) or minimum_area <= 0.0:
        raise RuntimeError("Attempt 25 minimum-area gate is not positive and finite")
    if not math.isfinite(target_angle) or not 0.0 < target_angle < 180.0:
        raise RuntimeError("Attempt 25 minimum-angle gate is outside (0,180)")
    area_altitude_floor = 2.0 * minimum_area / local_longest
    angle_altitude_floor = local_shortest * math.sin(math.radians(target_angle))
    point_floor = float(tolerances["point_tolerance_m"])
    required = max(point_floor, min(area_altitude_floor, angle_altitude_floor))
    references = [
        ("boundary", int(index), value)
        for index, value in enumerate(boundary)
    ] + [
        ("seed", int(index), value)
        for index, value in enumerate(seeds)
    ]
    if not references:
        raise RuntimeError("Attempt 25 candidate policy has no reference coordinates")
    distances = [
        (float((candidate - value).length), source, index)
        for source, index, value in references
    ]
    nearest_distance, nearest_source, nearest_index = min(
        distances, key=lambda value: (value[0], value[1], value[2])
    )
    separated = bool(nearest_distance > required)
    return {
        "policy_id": "minimum_area_angle_local_edge_separation_v1",
        "method": str(method),
        "local_edge_lengths_m": edge_lengths,
        "local_shortest_edge_m": float(local_shortest),
        "local_longest_edge_m": float(local_longest),
        "point_floor_m": point_floor,
        "area_altitude_floor_m": float(area_altitude_floor),
        "angle_altitude_floor_m": float(angle_altitude_floor),
        "required_separation_m": float(required),
        "boundary_diagonal_m": float(tolerances["boundary_diagonal_m"]),
        "required_separation_relative_to_boundary_diagonal": float(
            required / tolerances["boundary_diagonal_m"]
        ),
        "nearest_reference_distance_m": float(nearest_distance),
        "nearest_reference_type": nearest_source,
        "nearest_reference_index": int(nearest_index),
        "separated_from_boundary_and_seeds": separated,
        "rejection_reason": None
        if separated
        else "BELOW_AREA_ANGLE_LOCAL_EDGE_SEPARATION_FLOOR",
    }


def attempt25_assert_exact_boundary_and_disk(result: Mapping[str, Any]) -> dict[str, Any]:
    boundary = result["boundary_diagnostic"]
    disk = result["disk_topology"]
    if bool(boundary["mismatch_detected"]):
        raise RuntimeError("Attempt 25 success gate retained a CDT boundary mismatch")
    if int(boundary["missing_boundary_edge_count"]) != 0:
        raise RuntimeError("Attempt 25 success gate has a missing boundary edge")
    if int(boundary["extra_open_edge_count"]) != 0:
        raise RuntimeError("Attempt 25 success gate has an extra open edge")
    if int(boundary["open_edge_count"]) != int(
        boundary["constrained_boundary_edge_count"]
    ):
        raise RuntimeError("Attempt 25 exact boundary is not the complete open edge set")
    if not bool(disk["exact_boundary_is_complete_open_edge_set"]):
        raise RuntimeError("Attempt 25 disk gate rejected the exact open boundary")
    if int(disk["face_component_count"]) != 1:
        raise RuntimeError("Attempt 25 result has multiple face components")
    if int(disk["euler_characteristic"]) != 1:
        raise RuntimeError("Attempt 25 result is not a topological disk")
    return {
        "missing_boundary_edge_count": 0,
        "extra_open_edge_count": 0,
        "exact_boundary_is_complete_open_edge_set": True,
        "face_component_count": 1,
        "euler_characteristic": 1,
    }


def quality_refined_cdt(
    boundary: Sequence[Vector], config: Mapping[str, Any]
) -> dict[str, Any]:
    epsilon = float(config["cdt_epsilon_m"])
    threshold = float(config["minimum_new_triangle_angle_degrees"])
    maximum_vertices = int(config["maximum_new_interior_vertex_count"])
    maximum_iterations = int(config["maximum_quality_refinement_iterations"])
    base_context = {
        "phase": "initial_zero_seed",
        "refinement_iteration": None,
        "requested_seed_count": 0,
        "candidate_policy_id": "minimum_area_angle_local_edge_separation_v1",
    }
    base = run_cdt(boundary, [], epsilon, config, base_context)
    seeds = [
        dimension_safe_vector_mean([base["coordinates"][index] for index in face])
        for face in base["faces"]
    ]
    seeds, initial_seed_sanitation = sanitize_cdt_seed_points(
        boundary, seeds, epsilon, config
    )
    seen = {
        (round(float(value.x), 14), round(float(value.y), 14)) for value in seeds
    }
    candidate_history = []
    rejected_incenter_count = 0
    centroid_fallback_selection_count = 0
    result = None
    terminal_reason = "ITERATION_CAP_EXHAUSTED"

    for iteration in range(maximum_iterations + 1):
        run_context = {
            "phase": "quality_refinement",
            "refinement_iteration": int(iteration),
            "requested_seed_count": len(seeds),
            "candidate_policy_id": "minimum_area_angle_local_edge_separation_v1",
            "previous_candidate_record": candidate_history[-1]
            if candidate_history
            else None,
        }
        result = run_cdt(boundary, seeds, epsilon, config, run_context)
        quality = []
        for face_index, face in enumerate(result["faces"]):
            points = [result["coordinates"][index] for index in face]
            angles = triangle_angles(points)
            quality.append((min(angles), face_index, face, points, angles))
        minimum, worst_face_index, worst_face, points, worst_angles = min(
            quality, key=lambda value: value[0]
        )
        if minimum >= threshold:
            exact_disk = attempt25_assert_exact_boundary_and_disk(result)
            result["quality_refinement_iterations"] = int(iteration)
            result["seed_count"] = len(seeds)
            result["minimum_2d_triangle_angle_degrees"] = float(minimum)
            result["initial_seed_sanitation"] = initial_seed_sanitation
            result["attempt25_candidate_admissibility_policy"] = (
                "minimum_area_angle_local_edge_separation_v1"
            )
            result["attempt25_candidate_history"] = candidate_history
            result["attempt25_rejected_incenter_count"] = rejected_incenter_count
            result["attempt25_centroid_fallback_selection_count"] = (
                centroid_fallback_selection_count
            )
            result["attempt25_exact_boundary_and_disk_gate"] = exact_disk
            return result
        if len(seeds) >= maximum_vertices:
            terminal_reason = "SEED_CAP_REACHED"
            break

        candidate_values = [
            ("triangle_incenter", triangle_incenter(points)),
            ("triangle_centroid", dimension_safe_vector_mean(points)),
        ]
        candidate_rows = []
        selected_index = None
        for candidate_index, (method, candidate) in enumerate(candidate_values):
            key = (round(float(candidate.x), 14), round(float(candidate.y), 14))
            duplicate = key in seen
            separation = attempt25_candidate_separation_diagnostics(
                candidate, method, points, boundary, seeds, epsilon, config
            )
            eligible = bool(not duplicate and separation["separated_from_boundary_and_seeds"])
            if selected_index is None and eligible:
                selected_index = candidate_index
            candidate_rows.append(
                {
                    "candidate_index": int(candidate_index),
                    "method": method,
                    "xy": [float(candidate.x), float(candidate.y)],
                    "rounded_key": [float(key[0]), float(key[1])],
                    "already_seen": duplicate,
                    **separation,
                    "admissible": eligible,
                    "selected": False,
                }
            )
        if selected_index is not None:
            candidate_rows[selected_index]["selected"] = True
        candidate_record = {
            "source_iteration": int(iteration),
            "minimum_2d_triangle_angle_degrees": float(minimum),
            "worst_face_index": int(worst_face_index),
            "worst_face_output_indices": [int(value) for value in worst_face],
            "worst_face_angles_degrees": [float(value) for value in worst_angles],
            "candidate_diagnostics": candidate_rows,
            "selected_candidate_index": selected_index,
        }
        candidate_history.append(candidate_record)
        if (
            candidate_rows[0]["method"] == "triangle_incenter"
            and not candidate_rows[0]["admissible"]
        ):
            rejected_incenter_count += 1
        if selected_index is None:
            terminal_reason = "NO_ADMISSIBLE_CANDIDATE"
            break
        if candidate_rows[selected_index]["method"] == "triangle_centroid":
            centroid_fallback_selection_count += 1
        selected = candidate_values[selected_index][1]
        selected_key = (
            round(float(selected.x), 14),
            round(float(selected.y), 14),
        )
        seeds.append(selected)
        seen.add(selected_key)
    else:
        terminal_reason = "ITERATION_CAP_EXHAUSTED"

    minimum = (
        min(
            min(
                triangle_angles(
                    [result["coordinates"][index] for index in face]
                )
            )
            for face in result["faces"]
        )
        if result
        else 0.0
    )
    raise RuntimeError(
        "attempt25_quality_refined_cdt_failed_minimum_angle:"
        f"reason={terminal_reason}:achieved={minimum}:required={threshold}:"
        f"seeds={len(seeds)}:rejected_incenters={rejected_incenter_count}:"
        f"centroid_fallbacks={centroid_fallback_selection_count}"
    )
'''


def exact_replace(source: str, old: str, new: str, name: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Attempt 25 replacement drifted: {name}: {count}")
    return source.replace(old, new, 1)


def replace_top_level_function(source: str, name: str, replacement: str) -> str:
    tree = ast.parse(source)
    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Attempt 25 function replacement drifted: {name}: {len(matches)}")
    node = matches[0]
    lines = source.splitlines(keepends=True)
    return "".join(lines[: node.lineno - 1]) + replacement.rstrip() + "\n\n" + "".join(lines[node.end_lineno :])


def derive_attempt25_source(source24: str) -> str:
    source = replace_top_level_function(
        source24, "quality_refined_cdt", REPAIRED_QUALITY_REFINEMENT
    )
    source = exact_replace(
        source,
        '"kira.avatar.r24.blackproject_attempt24.cdt_refinement_terminal.v1"',
        '"kira.avatar.r24.blackproject_attempt24.cdt_candidate_repair_failure.v1"',
        "candidate repair failure schema",
    )
    source = exact_replace(
        source,
        '"status": "CAPTURED_FIRST_CDT_REFINEMENT_TERMINAL_NO_REPAIR",',
        '"status": "CAPTURED_ATTEMPT24_CANDIDATE_REPAIR_FAILURE_NO_SAVE",',
        "candidate repair failure status",
    )
    source = exact_replace(
        source,
        '        "repair_applied": False,\n'
        '        "body_geometry_mutation_reached": False,',
        '        "repair_applied": False,\n'
        '        "candidate_admissibility_repair_applied": True,\n'
        '        "body_geometry_mutation_reached": False,',
        "terminal candidate repair truth",
    )
    source = exact_replace(
        source,
        '"CAPTURED_EXACT_SANITIZED_CDT_BOUNDARY_STATE_NO_REPAIR"',
        '"CAPTURED_POST_ATTEMPT24_CANDIDATE_POLICY_CDT_BOUNDARY_STATE"',
        "post-policy boundary status",
    )
    source = exact_replace(
        source,
        '        "repair_decision": "DEFER_UNTIL_EXACT_CAPTURE_REVIEWED",',
        '        "candidate_admissibility_policy_active": True,\n'
        '        "repair_decision": "PREVENT_DEGENERATE_REFINEMENT_CANDIDATE;FAIL_IF_MISMATCH_REMAINS",',
        "post-policy boundary decision",
    )
    source = exact_replace(
        source,
        '            "Attempt 24 captured first actual CDT boundary mismatch; "\n'
        '            "diagnostic-only stop before reconstruction"',
        '            "Attempt 24 candidate-admissibility repair still produced a CDT "\n'
        '            "mismatch; no-save stop before reconstruction"',
        "actual repair mismatch error",
    )
    source = exact_replace(
        source,
        '        "Attempt 24 captured exact CDT refinement terminal; "\n'
        '        "diagnostic-only stop before reconstruction"',
        '        "Attempt 24 reached an unexpected exact diagnostic terminal after "\n'
        '        "candidate repair; no-save stop before reconstruction"',
        "unexpected exact terminal error",
    )
    source = exact_replace(
        source,
        '        "initial_seed_sanitation": cdt["initial_seed_sanitation"],\n'
        '        "uv_reconstructed_from_exact_local_boundary": True,',
        '        "initial_seed_sanitation": cdt["initial_seed_sanitation"],\n'
        '        "candidate_admissibility_policy": cdt[\n'
        '            "attempt25_candidate_admissibility_policy"\n'
        '        ],\n'
        '        "rejected_incenter_count": cdt["attempt25_rejected_incenter_count"],\n'
        '        "centroid_fallback_selection_count": cdt[\n'
        '            "attempt25_centroid_fallback_selection_count"\n'
        '        ],\n'
        '        "exact_boundary_and_disk_gate": cdt[\n'
        '            "attempt25_exact_boundary_and_disk_gate"\n'
        '        ],\n'
        '        "uv_reconstructed_from_exact_local_boundary": True,',
        "surface candidate policy evidence",
    )
    for old, new in (
        ("attempt_24", "attempt_25"),
        ("attempt24", "attempt25"),
        ("Attempt 24", "Attempt 25"),
        ("ATTEMPT24", "ATTEMPT25"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 24 identity token disappeared: {old}")
        source = source.replace(old, new)
    stale = ("ATTEMPT24", "attempt_24", "attempt24", "Attempt 24")
    if any(token in source for token in stale):
        raise RuntimeError("Attempt 25 derived source retained stale evidence identity")
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "attempt25_candidate_separation_diagnostics",
        "attempt25_assert_exact_boundary_and_disk",
        "quality_refined_cdt",
        "capture_attempt25_terminal_and_stop",
    }
    if not required.issubset(names):
        raise RuntimeError("Attempt 25 candidate repair functions are absent")
    return source


def materialize_attempt24_source(provider: Any) -> str:
    provider23 = provider.load_attempt23_module()
    source23 = provider.materialize_attempt23_source(provider23)
    return provider.derive_attempt24_source(source23)


def main() -> None:
    if sha256_file(ATTEMPT24_WORKER) != EXPECTED_ATTEMPT24_WORKER_SHA256:
        raise RuntimeError("Attempt 24 worker changed before Attempt 25 derivation")
    provider = load_attempt24_module()
    preserved_paths = (
        ATTEMPT24_WORKER,
        ATTEMPT23_WORKER,
        ATTEMPT22_WORKER,
        ATTEMPT21_WORKER,
        ATTEMPT20_WORKER,
        ATTEMPT19_WORKER,
        ATTEMPT18_WORKER,
    )
    before = {path: path.read_bytes() for path in preserved_paths}
    source24 = materialize_attempt24_source(provider)
    source25 = derive_attempt25_source(source24)
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "load_attempt25_config": load_attempt25_config,
    }
    try:
        exec(
            compile(source25, str(Path(__file__).resolve()) + "::derived", "exec"),
            namespace,
            namespace,
        )
    finally:
        for path in preserved_paths:
            if path.read_bytes() != before[path]:
                raise RuntimeError(f"{path.name} changed during Attempt 25 execution")


if __name__ == "__main__":
    main()
