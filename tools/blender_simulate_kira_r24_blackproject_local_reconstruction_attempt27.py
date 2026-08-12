"""Hash-bound Attempt 27 no-admissible-candidate numerical diagnostic.

This wrapper derives sealed Attempt 26 without changing its candidate policy,
then adds one append-only diagnostic stop at the existing
NO_ADMISSIBLE_CANDIDATE boundary. Blender is not imported during static use.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260808"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT27_CONFIG.json"
)
ATTEMPT26_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt26.py"
EXPECTED_CONFIG_SHA256 = "d4e07928bec4879f01b1441d9ec0afb0511d430a79cd59ad933d576af26ce51c"
EXPECTED_ATTEMPT26_WORKER_SHA256 = "eeddd3be64e58253c15d73c2920b6ccdc6a7fbd47a1b549ad00daf83cdd0e14a"


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
        raise RuntimeError(f"Attempt 27 binding escapes project: {value}")
    return path


def verify_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(record["path"]))
    actual_bytes = path.stat().st_size
    actual_sha256 = sha256_file(path)
    if actual_bytes != int(record["bytes"]):
        raise RuntimeError(f"Attempt 27 bound byte count drifted: {name}")
    if actual_sha256 != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 27 bound hash drifted: {name}: {actual_sha256}")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": actual_bytes,
        "sha256": actual_sha256,
    }


def load_attempt26_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "attempt27_sealed_attempt26_provider", ATTEMPT26_WORKER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Attempt 27 could not load sealed Attempt 26")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_overlay(config_path: Path) -> dict[str, Any]:
    config_path = config_path.resolve(strict=True)
    if config_path != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 27 requires the exact sealed overlay config path")
    actual = sha256_file(config_path)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 27 overlay config hash drifted: {actual}")
    overlay = json.loads(config_path.read_text(encoding="utf-8"))
    if (
        overlay.get("attempt_id") != "attempt_27"
        or overlay.get("status") != "STATIC_DIAGNOSTIC_PREPARED_NOT_RUN"
        or overlay.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 27 overlay identity drifted")
    required_true = (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "diagnostic_only",
        "cdt_refinement_replay_allowed_during_later_reviewed_run",
    )
    if not all(bool(overlay["scope"][name]) for name in required_true):
        raise RuntimeError("Attempt 27 lost a required diagnostic scope gate")
    forbidden = (
        "candidate_seed_policy_change_allowed",
        "in_memory_local_body_reconstruction_allowed",
        "body_geometry_mutation_allowed",
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
        raise RuntimeError("Attempt 27 scope permits a forbidden operation")
    return overlay


def verify_overlay_bindings(overlay: Mapping[str, Any]) -> dict[str, Any]:
    verified = {
        name: verify_record(name, record)
        for name, record in overlay["bindings"].items()
    }
    verified["proposal"] = verify_record("proposal", overlay["proposal"])
    if verified["attempt26_worker"]["sha256"] != EXPECTED_ATTEMPT26_WORKER_SHA256:
        raise RuntimeError("Attempt 27 provider constant and binding disagree")
    preserved = overlay["preserved_attempt26_package"]
    rows = [verified[name] for name in preserved["binding_names"]]
    if len(rows) != int(preserved["file_count"]):
        raise RuntimeError("Attempt 26 preserved package file count drifted")
    if sum(int(row["bytes"]) for row in rows) != int(preserved["total_bytes"]):
        raise RuntimeError("Attempt 26 preserved package byte total drifted")
    return verified


def validate_contract(overlay: Mapping[str, Any]) -> None:
    diagnosis = overlay["diagnosis"]
    if diagnosis["attempt26_terminal_reason"] != "NO_ADMISSIBLE_CANDIDATE":
        raise RuntimeError("Attempt 27 is not bound to the exact terminal reason")
    if int(diagnosis["accepted_seed_count"]) != 36:
        raise RuntimeError("Attempt 27 accepted-seed diagnosis drifted")
    if float(diagnosis["required_minimum_angle_degrees"]) != 12.0:
        raise RuntimeError("Attempt 27 required-angle diagnosis drifted")
    feasibility = overlay["feasibility_contract"]
    if feasibility["global_infeasibility_rule"] != "only_if_fixed_boundary_interior_angle_is_below_target":
        raise RuntimeError("Attempt 27 global-feasibility truth boundary drifted")
    if not bool(feasibility["no_feasibility_claim_from_candidate_rejection_alone"]):
        raise RuntimeError("Attempt 27 permits unsupported global feasibility claims")


def load_attempt27_config(config_path: Path) -> dict[str, Any]:
    overlay = load_overlay(config_path)
    validate_contract(overlay)
    verified = verify_overlay_bindings(overlay)
    provider = load_attempt26_module()
    base_path = project_path(overlay["bindings"]["attempt26_config"]["path"])
    merged = provider.load_attempt26_config(base_path)
    if merged.get("attempt_id") != overlay["base"]["expected_config_attempt_id"]:
        raise RuntimeError("Attempt 26 materialized base identity drifted")
    merged = copy.deepcopy(merged)
    merged["schema"] = "kira.avatar.r24.blackproject_local_reconstruction_attempt27.config.v1"
    merged["attempt_id"] = "attempt_27"
    merged["output"] = copy.deepcopy(overlay["output"])
    diagnostic_contract = overlay["diagnostic_path_contract"]
    expected_diagnostic = (
        f'{overlay["output"]["root"]}/'
        f'{overlay["output"]["no_admissible_candidate_diagnostic"]}'
    )
    if diagnostic_contract["project_relative_path"] != expected_diagnostic:
        raise RuntimeError("Attempt 27 diagnostic path contract disagrees with output")
    merged["replacement"][diagnostic_contract["replacement_key"]] = expected_diagnostic
    boundary_contract = overlay["boundary_failure_path_contract"]
    expected_boundary = (
        f'{overlay["output"]["root"]}/'
        f'{overlay["output"]["cdt_candidate_repair_failure"]}'
    )
    if boundary_contract["project_relative_path"] != expected_boundary:
        raise RuntimeError("Attempt 27 boundary path contract disagrees with output")
    merged["replacement"][boundary_contract["replacement_key"]] = expected_boundary
    merged["attempt27_diagnosis"] = copy.deepcopy(overlay["diagnosis"])
    merged["attempt27_capture_contract"] = copy.deepcopy(overlay["capture_contract"])
    merged["attempt27_feasibility_contract"] = copy.deepcopy(
        overlay["feasibility_contract"]
    )
    merged["attempt27_unchanged_hard_gates"] = copy.deepcopy(
        overlay["unchanged_hard_gates"]
    )
    merged["attempt27_evidence_label_contract"] = copy.deepcopy(
        overlay["evidence_label_contract"]
    )
    merged["attempt27_truth"] = copy.deepcopy(overlay["truth"])
    merged["inputs"].update(
        {
            f"attempt27_bound_{name}": {
                "path": row["path"],
                "bytes": row["bytes"],
                "sha256": row["sha256"],
            }
            for name, row in verified.items()
        }
    )
    unchanged = overlay["unchanged_hard_gates"]
    for location in ("replacement", "hard_gates"):
        if float(merged[location]["minimum_new_triangle_angle_degrees"]) != float(
            unchanged["minimum_new_triangle_angle_degrees"]
        ):
            raise RuntimeError(f"Attempt 27 {location} minimum-angle gate drifted")
    if float(merged["replacement"]["minimum_new_triangle_world_area_m2"]) != float(
        unchanged["minimum_new_triangle_world_area_m2"]
    ):
        raise RuntimeError("Attempt 27 minimum-area gate drifted")
    return merged


ATTEMPT27_DIAGNOSTIC_HELPERS = r'''
def attempt27_xy(value: Vector) -> list[float]:
    return [float(value.x), float(value.y)]


def attempt27_edge_length(first: Vector, second: Vector) -> float:
    return float((first - second).length)


def attempt27_point_segment_diagnostic(
    point: Vector, first: Vector, second: Vector
) -> dict[str, Any]:
    dx = float(second.x) - float(first.x)
    dy = float(second.y) - float(first.y)
    denominator = dx * dx + dy * dy
    if denominator <= 0.0:
        projection = 0.0
    else:
        projection = (
            (float(point.x) - float(first.x)) * dx
            + (float(point.y) - float(first.y)) * dy
        ) / denominator
    clamped = max(0.0, min(1.0, projection))
    closest_x = float(first.x) + clamped * dx
    closest_y = float(first.y) + clamped * dy
    distance = math.hypot(float(point.x) - closest_x, float(point.y) - closest_y)
    return {
        "distance_m": float(distance),
        "unclamped_projection_parameter": float(projection),
        "clamped_projection_parameter": float(clamped),
        "closest_xy": [float(closest_x), float(closest_y)],
    }


def attempt27_nearest_boundary_segment(
    point: Vector, boundary: Sequence[Vector]
) -> dict[str, Any]:
    rows = []
    for index, first in enumerate(boundary):
        second_index = (index + 1) % len(boundary)
        second = boundary[second_index]
        row = attempt27_point_segment_diagnostic(point, first, second)
        row.update(
            {
                "boundary_source_indices": [int(index), int(second_index)],
                "endpoint_coordinates": [attempt27_xy(first), attempt27_xy(second)],
                "segment_length_m": attempt27_edge_length(first, second),
            }
        )
        rows.append(row)
    return min(
        rows,
        key=lambda value: (
            value["distance_m"],
            value["boundary_source_indices"][0],
        ),
    )


def attempt27_boundary_angle_diagnostics(
    boundary: Sequence[Vector], target_degrees: float
) -> dict[str, Any]:
    signed_twice_area = sum(
        float(boundary[index].x) * float(boundary[(index + 1) % len(boundary)].y)
        - float(boundary[(index + 1) % len(boundary)].x) * float(boundary[index].y)
        for index in range(len(boundary))
    )
    orientation_sign = 1.0 if signed_twice_area >= 0.0 else -1.0
    rows = []
    for index, current in enumerate(boundary):
        previous = boundary[(index - 1) % len(boundary)]
        following = boundary[(index + 1) % len(boundary)]
        ax = float(previous.x) - float(current.x)
        ay = float(previous.y) - float(current.y)
        bx = float(following.x) - float(current.x)
        by = float(following.y) - float(current.y)
        first_length = math.hypot(ax, ay)
        second_length = math.hypot(bx, by)
        if first_length <= 0.0 or second_length <= 0.0:
            smaller = 0.0
            cross = 0.0
            interior = 0.0
        else:
            cosine = max(
                -1.0,
                min(1.0, (ax * bx + ay * by) / (first_length * second_length)),
            )
            smaller = math.degrees(math.acos(cosine))
            cross = ax * by - ay * bx
            interior = (
                smaller if cross * orientation_sign <= 0.0 else 360.0 - smaller
            )
        rows.append(
            {
                "boundary_source_index": int(index),
                "interior_angle_degrees": float(interior),
                "smaller_vector_angle_degrees": float(smaller),
                "cross": float(cross),
                "previous_edge_length_m": float(first_length),
                "next_edge_length_m": float(second_length),
            }
        )
    minimum_row = min(rows, key=lambda value: value["interior_angle_degrees"])
    necessary_pass = bool(
        minimum_row["interior_angle_degrees"] + 1.0e-12 >= target_degrees
    )
    return {
        "polygon_signed_twice_area_m2": float(signed_twice_area),
        "polygon_orientation": "COUNTERCLOCKWISE"
        if orientation_sign > 0.0
        else "CLOCKWISE",
        "corner_rows": rows,
        "minimum_boundary_interior_angle_degrees": float(
            minimum_row["interior_angle_degrees"]
        ),
        "minimum_boundary_interior_angle_source_index": int(
            minimum_row["boundary_source_index"]
        ),
        "target_degrees": float(target_degrees),
        "necessary_fixed_boundary_corner_condition_passes": necessary_pass,
    }


def attempt27_candidate_child_split(
    points: Sequence[Vector], candidate: Vector
) -> dict[str, Any]:
    child_points = (
        (points[0], points[1], candidate),
        (points[1], points[2], candidate),
        (points[2], points[0], candidate),
    )
    rows = []
    for index, values in enumerate(child_points):
        angles = triangle_angles(values)
        lengths = [
            attempt27_edge_length(values[first], values[second])
            for first, second in ((0, 1), (1, 2), (2, 0))
        ]
        rows.append(
            {
                "child_index": int(index),
                "coordinates": [attempt27_xy(value) for value in values],
                "angles_degrees": [float(value) for value in angles],
                "edge_lengths_m": lengths,
                "minimum_angle_degrees": float(min(angles)),
            }
        )
    return {
        "children": rows,
        "minimum_child_angle_degrees": float(
            min(row["minimum_angle_degrees"] for row in rows)
        ),
    }


def attempt27_seed_rows(
    seeds: Sequence[Vector],
    initial_seed_count: int,
    candidate_history: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refinement_origins = []
    for record in candidate_history:
        selected = record.get("selected_candidate_index")
        if selected is None:
            continue
        candidate = record["candidate_diagnostics"][int(selected)]
        refinement_origins.append(
            {
                "origin": "selected_refinement_candidate",
                "source_iteration": int(record["source_iteration"]),
                "method": str(candidate["method"]),
            }
        )
    if len(refinement_origins) != len(seeds) - int(initial_seed_count):
        raise RuntimeError("Attempt 27 cannot map accepted seeds to their origins")
    rows = []
    for index, seed in enumerate(seeds):
        origin = (
            {
                "origin": "initial_sanitized_face_centroid",
                "initial_seed_index": int(index),
            }
            if index < int(initial_seed_count)
            else refinement_origins[index - int(initial_seed_count)]
        )
        rows.append(
            {
                "accepted_seed_index": int(index),
                "xy": attempt27_xy(seed),
                **origin,
            }
        )
    return rows


def attempt27_resolve_diagnostic_path(config: Mapping[str, Any]) -> Path:
    relative = Path(
        str(config["attempt27_no_admissible_candidate_diagnostic_project_path"])
    )
    if relative.is_absolute():
        raise RuntimeError("Attempt 27 diagnostic path must be project-relative")
    root = ROOT.resolve()
    resolved = (root / relative).resolve()
    if root != resolved and root not in resolved.parents:
        raise RuntimeError("Attempt 27 diagnostic path escapes project")
    return resolved


def attempt27_atomic_write_once(path: Path, payload: Mapping[str, Any]) -> None:
    if path.exists():
        raise RuntimeError("Attempt 27 diagnostic exists; refusing overwrite")
    atomic_write_json(path, payload)


def attempt27_build_no_candidate_diagnostic(
    boundary: Sequence[Vector],
    config: Mapping[str, Any],
    iteration: int,
    result: Mapping[str, Any],
    seeds: Sequence[Vector],
    initial_seed_count: int,
    initial_seed_sanitation: Mapping[str, Any],
    candidate_history: Sequence[Mapping[str, Any]],
    minimum: float,
    worst_face_index: int,
    worst_face: Sequence[int],
    points: Sequence[Vector],
    worst_angles: Sequence[float],
    candidate_values: Sequence[tuple[str, Vector]],
    candidate_rows: Sequence[Mapping[str, Any]],
    rejected_incenter_count: int,
    centroid_fallback_selection_count: int,
) -> dict[str, Any]:
    target = float(config["minimum_new_triangle_angle_degrees"])
    edge_pairs = ((0, 1), (1, 2), (2, 0))
    local_edges = [
        {
            "local_indices": [int(first), int(second)],
            "output_indices": [int(worst_face[first]), int(worst_face[second])],
            "endpoint_coordinates": [
                attempt27_xy(points[first]),
                attempt27_xy(points[second]),
            ],
            "length_m": attempt27_edge_length(points[first], points[second]),
        }
        for first, second in edge_pairs
    ]
    boundary_state = result["boundary_diagnostic"]
    constrained_rows = list(boundary_state["constrained_boundary_edges"])
    constrained_keys = {
        tuple(sorted(int(value) for value in row["output_indices"]))
        for row in constrained_rows
    }
    for row in local_edges:
        row["is_fixed_constrained_boundary_edge"] = bool(
            tuple(sorted(row["output_indices"])) in constrained_keys
        )
    worst_indices = {int(value) for value in worst_face}
    incident_constrained = [
        row
        for row in constrained_rows
        if worst_indices.intersection(int(value) for value in row["output_indices"])
    ]
    candidate_payload = []
    for (method, candidate), diagnostics in zip(candidate_values, candidate_rows):
        row = dict(diagnostics)
        row["method"] = str(method)
        row["xy"] = attempt27_xy(candidate)
        row["nearest_fixed_boundary_segment"] = attempt27_nearest_boundary_segment(
            candidate, boundary
        )
        row["three_child_split"] = attempt27_candidate_child_split(points, candidate)
        candidate_payload.append(row)
    local_area_twice = abs(float(orient2d(points[0], points[1], points[2])))
    smallest_local_index = min(
        range(3), key=lambda index: (float(worst_angles[index]), index)
    )
    incident_local_edges = [
        row for row in local_edges if smallest_local_index in row["local_indices"]
    ]
    local_upper_bound = float(worst_angles[smallest_local_index]) / 2.0
    boundary_angles = attempt27_boundary_angle_diagnostics(boundary, target)
    if not boundary_angles["necessary_fixed_boundary_corner_condition_passes"]:
        global_conclusion = (
            "PROVEN_INFEASIBLE_UNDER_FIXED_PSLG_BOUNDARY_CORNER_BELOW_TARGET"
        )
    else:
        global_conclusion = "UNRESOLVED_BY_BOUNDED_NUMERICAL_DIAGNOSTIC"
    neighbor_faces = []
    for face_index, face in enumerate(result["faces"]):
        if not worst_indices.intersection(int(value) for value in face):
            continue
        face_points = [result["coordinates"][int(value)] for value in face]
        neighbor_faces.append(
            {
                "face_index": int(face_index),
                "output_indices": [int(value) for value in face],
                "coordinates": [attempt27_xy(value) for value in face_points],
                "angles_degrees": [
                    float(value) for value in triangle_angles(face_points)
                ],
            }
        )
    return {
        "schema": "kira.avatar.r24.blackproject_attempt27.no_admissible_candidate_diagnostic.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "CAPTURED_NO_ADMISSIBLE_CANDIDATE_NUMERICAL_STATE_NO_REPAIR",
        "attempt_id": "attempt_27",
        "terminal_reason": "NO_ADMISSIBLE_CANDIDATE",
        "refinement_iteration": int(iteration),
        "accepted_seed_count": len(seeds),
        "rejected_incenter_count": int(rejected_incenter_count),
        "centroid_fallback_selection_count": int(
            centroid_fallback_selection_count
        ),
        "required_minimum_angle_degrees": float(target),
        "achieved_minimum_angle_degrees": float(minimum),
        "worst_face": {
            "face_index": int(worst_face_index),
            "output_indices": [int(value) for value in worst_face],
            "coordinates": [attempt27_xy(value) for value in points],
            "angles_degrees": [float(value) for value in worst_angles],
            "edge_rows": local_edges,
            "signed_twice_area_m2": float(
                orient2d(points[0], points[1], points[2])
            ),
            "absolute_twice_area_m2": float(local_area_twice),
            "area_m2": float(local_area_twice / 2.0),
            "smallest_angle_local_vertex_index": int(smallest_local_index),
            "smallest_angle_output_vertex_index": int(
                worst_face[smallest_local_index]
            ),
        },
        "candidate_diagnostics": candidate_payload,
        "accepted_seeds": attempt27_seed_rows(
            seeds, initial_seed_count, candidate_history
        ),
        "initial_seed_sanitation": dict(initial_seed_sanitation),
        "candidate_history": list(candidate_history),
        "fixed_pslg": {
            "boundary_coordinates": [
                {
                    "boundary_source_index": int(index),
                    "xy": attempt27_xy(value),
                }
                for index, value in enumerate(boundary)
            ],
            "ordered_boundary_segments": [
                {
                    "boundary_source_indices": [
                        int(index),
                        int((index + 1) % len(boundary)),
                    ],
                    "endpoint_coordinates": [
                        attempt27_xy(value),
                        attempt27_xy(boundary[(index + 1) % len(boundary)]),
                    ],
                    "length_m": attempt27_edge_length(
                        value, boundary[(index + 1) % len(boundary)]
                    ),
                }
                for index, value in enumerate(boundary)
            ],
            "boundary_source_to_output": list(
                boundary_state["boundary_source_to_output"]
            ),
            "constrained_boundary_edges": constrained_rows,
            "worst_face_incident_constrained_boundary_edges": incident_constrained,
            "missing_boundary_edge_count": int(
                boundary_state["missing_boundary_edge_count"]
            ),
            "extra_open_edge_count": int(boundary_state["extra_open_edge_count"]),
            "disk_topology": dict(result["disk_topology"]),
        },
        "worst_face_neighbor_faces": neighbor_faces,
        "bounded_12_degree_feasibility": {
            "analysis_scope": (
                "fixed_32_segment_pslg_necessary_corner_test_and_current_"
                "worst_face_single_interior_point_split_only"
            ),
            "boundary_corner_analysis": boundary_angles,
            "local_single_point_split": {
                "smallest_existing_angle_degrees": float(
                    worst_angles[smallest_local_index]
                ),
                "upper_bound_on_one_of_two_split_angles_degrees": float(
                    local_upper_bound
                ),
                "target_degrees": float(target),
                "can_all_child_angles_reach_target_while_retaining_both_"
                "incident_edges": bool(local_upper_bound + 1.0e-12 >= target),
                "incident_worst_face_edges": incident_local_edges,
                "proof_basis": (
                    "an interior ray splits the existing vertex angle into two "
                    "positive angles, so at least one is no greater than half"
                ),
            },
            "global_fixed_pslg_conclusion": global_conclusion,
            "candidate_rejection_alone_used_as_global_proof": False,
            "new_candidate_or_repair_proposed": False,
        },
        "current_cdt_counts": {
            "coordinate_count": len(result["coordinates"]),
            "face_count": len(result["faces"]),
            "boundary_count": len(boundary),
        },
        "candidate_policy_id": (
            "minimum_area_angle_local_edge_and_nearest_seed_pair_altitude_v2"
        ),
        "quality_gate_changed": False,
        "candidate_algorithm_changed": False,
        "repair_applied": False,
        "body_geometry_mutation_reached": False,
        "reconstruction_reached": False,
        "render_reached": False,
        "blend_saved": False,
        "runtime_changed": False,
    }
'''


def exact_replace(source: str, old: str, new: str, name: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Attempt 27 replacement drifted: {name}: {count}")
    return source.replace(old, new, 1)


def materialize_attempt26_source(provider: Any) -> str:
    provider25 = provider.load_attempt25_module()
    source25 = provider.materialize_attempt25_source(provider25)
    return provider.derive_attempt26_source(source25)


def derive_attempt27_source(source26: str) -> str:
    source = exact_replace(
        source26,
        "def quality_refined_cdt(\n",
        ATTEMPT27_DIAGNOSTIC_HELPERS + "\n\ndef quality_refined_cdt(\n",
        "insert numerical diagnostic helpers",
    )
    source = exact_replace(
        source,
        "    seeds, initial_seed_sanitation = sanitize_cdt_seed_points(\n"
        "        boundary, seeds, epsilon, config\n"
        "    )\n"
        "    seen = {\n",
        "    seeds, initial_seed_sanitation = sanitize_cdt_seed_points(\n"
        "        boundary, seeds, epsilon, config\n"
        "    )\n"
        "    initial_seed_count = len(seeds)\n"
        "    seen = {\n",
        "record initial accepted seed count",
    )
    source = exact_replace(
        source,
        "        if selected_index is None:\n"
        "            terminal_reason = \"NO_ADMISSIBLE_CANDIDATE\"\n"
        "            break\n",
        "        if selected_index is None:\n"
        "            terminal_reason = \"NO_ADMISSIBLE_CANDIDATE\"\n"
        "            diagnostic = attempt27_build_no_candidate_diagnostic(\n"
        "                boundary, config, iteration, result, seeds,\n"
        "                initial_seed_count, initial_seed_sanitation,\n"
        "                candidate_history, minimum, worst_face_index,\n"
        "                worst_face, points, worst_angles, candidate_values,\n"
        "                candidate_rows, rejected_incenter_count,\n"
        "                centroid_fallback_selection_count,\n"
        "            )\n"
        "            attempt27_atomic_write_once(\n"
        "                attempt27_resolve_diagnostic_path(config), diagnostic\n"
        "            )\n"
        "            raise RuntimeError(\n"
        "                \"Attempt 27 captured no-admissible-candidate numerical \"\n"
        "                \"state; diagnostic-only stop before reconstruction\"\n"
        "            )\n",
        "capture no-admissible-candidate terminal",
    )
    for old, new in (
        ("attempt_26", "attempt_27"),
        ("attempt26", "attempt27"),
        ("Attempt 26", "Attempt 27"),
        ("ATTEMPT26", "ATTEMPT27"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 26 identity token disappeared: {old}")
        source = source.replace(old, new)
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "attempt27_build_no_candidate_diagnostic",
        "attempt27_boundary_angle_diagnostics",
        "attempt27_candidate_separation_diagnostics",
        "attempt27_assert_exact_boundary_and_disk",
        "quality_refined_cdt",
    }
    if not required.issubset(names):
        raise RuntimeError("Attempt 27 diagnostic functions are absent")
    for stale in ("ATTEMPT26", "attempt_26", "attempt26", "Attempt 26"):
        if stale in source:
            raise RuntimeError(f"Attempt 27 derived source retained stale token: {stale}")
    return source


def main() -> None:
    if sha256_file(ATTEMPT26_WORKER) != EXPECTED_ATTEMPT26_WORKER_SHA256:
        raise RuntimeError("Attempt 26 worker changed before Attempt 27 derivation")
    overlay = load_overlay(DEFAULT_CONFIG)
    verify_overlay_bindings(overlay)
    provider = load_attempt26_module()
    source26 = materialize_attempt26_source(provider)
    source27 = derive_attempt27_source(source26)
    preserved_paths = [
        project_path(record["path"]) for record in overlay["bindings"].values()
    ] + [project_path(overlay["proposal"]["path"])]
    before = {path: path.read_bytes() for path in preserved_paths}
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "load_attempt27_config": load_attempt27_config,
    }
    try:
        exec(
            compile(source27, str(Path(__file__).resolve()) + "::derived", "exec"),
            namespace,
            namespace,
        )
    finally:
        for path in preserved_paths:
            if path.read_bytes() != before[path]:
                raise RuntimeError(f"{path.name} changed during Attempt 27 execution")


if __name__ == "__main__":
    main()
