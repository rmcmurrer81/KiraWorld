"""Attempt 28 existing-source replacement-boundary feasibility diagnostic.

Static helpers prove only coordinate-level necessary conditions.  The optional
Blender entry point reads the sealed patch mesh and maps existing-source repair
domains without changing or saving any mesh.  Blender is never imported at
module import time.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260808"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT28_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = "08ab7d73637d41accc10a3e52058e9a1e0b3b3bafcd8b009649881d0e0af7a11"


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


def project_existing_path(value: str) -> Path:
    path = (ROOT / value).resolve(strict=True)
    root = ROOT.resolve()
    if root != path and root not in path.parents:
        raise RuntimeError(f"Attempt 28 binding escapes project: {value}")
    return path


def project_output_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    root = ROOT.resolve()
    if root != path and root not in path.parents:
        raise RuntimeError(f"Attempt 28 output escapes project: {value}")
    return path


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 28 requires the exact sealed config path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 28 config hash drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_28"
        or config.get("status") != "STATIC_DIAGNOSTIC_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 28 identity drifted")
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
    )
    forbidden = (
        "body_geometry_mutation_allowed",
        "patch_geometry_mutation_allowed",
        "triangulation_allowed",
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
        raise RuntimeError("Attempt 28 lost a required read-only scope gate")
    if any(bool(scope[name]) for name in forbidden):
        raise RuntimeError("Attempt 28 permits a forbidden operation")
    diagnosis = config["diagnosis"]
    if float(diagnosis["required_minimum_angle_degrees"]) != 12.0:
        raise RuntimeError("Attempt 28 lowered the 12-degree target")
    if diagnosis["convex_boundary_source_indices_below_target"] != [2, 7, 21, 28]:
        raise RuntimeError("Attempt 28 fixed-boundary diagnosis drifted")
    if diagnosis["global_fixed_pslg_conclusion"] != (
        "PROVEN_INFEASIBLE_UNDER_FIXED_PSLG_BOUNDARY_CORNER_BELOW_TARGET"
    ):
        raise RuntimeError("Attempt 28 fixed-PSLG conclusion drifted")
    if bool(diagnosis["another_interior_seed_can_repair_fixed_boundary"]):
        raise RuntimeError("Attempt 28 incorrectly permits another interior seed")
    hard = config["unchanged_hard_gates"]
    if (
        float(hard["minimum_new_triangle_angle_degrees"]) != 12.0
        or float(hard["minimum_new_triangle_world_area_m2"]) != 1.0e-10
        or int(hard["global_seam_vertex_count"]) != 34
        or float(hard["global_seam_coordinate_delta_m"]) != 0.0
    ):
        raise RuntimeError("Attempt 28 hard gate drifted")
    if bool(config["coordinate_only_analysis"]["direct_suppression_authorized"]):
        raise RuntimeError("Attempt 28 authorizes an unproven direct simplification")


def verify_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    path = project_existing_path(str(record["path"]))
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(record["bytes"]):
        raise RuntimeError(f"Attempt 28 bound byte count drifted: {name}")
    if digest != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 28 bound hash drifted: {name}: {digest}")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": size,
        "sha256": digest,
    }


def verify_bindings(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    records = {
        name: verify_record(name, record)
        for name, record in config["bindings"].items()
    }
    records["proposal"] = verify_record("proposal", config["proposal"])
    preserved = config["preserved_attempt27_package"]
    rows = [records[name] for name in preserved["binding_names"]]
    if len(rows) != int(preserved["file_count"]):
        raise RuntimeError("Attempt 27 preserved package file count drifted")
    if sum(int(row["bytes"]) for row in rows) != int(preserved["total_bytes"]):
        raise RuntimeError("Attempt 27 preserved package byte total drifted")
    capture = json.loads(
        project_existing_path(config["bindings"]["attempt27_capture"]["path"])
        .read_text(encoding="utf-8")
    )
    if capture.get("attempt_id") != "attempt_27" or capture.get("blend_saved"):
        raise RuntimeError("Attempt 28 is not bound to the exact no-save capture")
    return records


def signed_twice_area(points: Sequence[Sequence[float]]) -> float:
    return float(
        sum(
            float(points[index][0]) * float(points[(index + 1) % len(points)][1])
            - float(points[(index + 1) % len(points)][0]) * float(points[index][1])
            for index in range(len(points))
        )
    )


def boundary_angle_rows(
    points: Sequence[Sequence[float]], target_degrees: float
) -> dict[str, Any]:
    if len(points) < 3:
        raise RuntimeError("Attempt 28 boundary needs at least three coordinates")
    twice_area = signed_twice_area(points)
    if twice_area == 0.0:
        raise RuntimeError("Attempt 28 boundary has zero signed area")
    orientation_sign = 1.0 if twice_area > 0.0 else -1.0
    rows = []
    for index, current in enumerate(points):
        previous = points[(index - 1) % len(points)]
        following = points[(index + 1) % len(points)]
        ax = float(previous[0]) - float(current[0])
        ay = float(previous[1]) - float(current[1])
        bx = float(following[0]) - float(current[0])
        by = float(following[1]) - float(current[1])
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
            interior = smaller if cross * orientation_sign <= 0.0 else 360.0 - smaller
        rows.append(
            {
                "boundary_index": int(index),
                "interior_angle_degrees": float(interior),
                "smaller_vector_angle_degrees": float(smaller),
                "cross": float(cross),
                "previous_edge_length_m": float(first_length),
                "next_edge_length_m": float(second_length),
            }
        )
    minimum = min(rows, key=lambda row: row["interior_angle_degrees"])
    violating = [
        row
        for row in rows
        if row["interior_angle_degrees"] < 180.0
        and row["interior_angle_degrees"] + 1.0e-12 < target_degrees
    ]
    return {
        "polygon_signed_twice_area_m2": twice_area,
        "polygon_orientation": "COUNTERCLOCKWISE"
        if twice_area > 0.0
        else "CLOCKWISE",
        "corner_rows": rows,
        "minimum_boundary_interior_angle_degrees": float(
            minimum["interior_angle_degrees"]
        ),
        "minimum_boundary_index": int(minimum["boundary_index"]),
        "convex_corner_indices_below_target": [
            int(row["boundary_index"]) for row in violating
        ],
        "target_degrees": float(target_degrees),
        "necessary_fixed_boundary_corner_condition_passes": not violating,
    }


def _orientation(
    first: Sequence[float], second: Sequence[float], third: Sequence[float]
) -> float:
    return float(
        (float(second[0]) - float(first[0]))
        * (float(third[1]) - float(first[1]))
        - (float(second[1]) - float(first[1]))
        * (float(third[0]) - float(first[0]))
    )


def polygon_is_simple(
    points: Sequence[Sequence[float]], epsilon: float = 1.0e-12
) -> bool:
    count = len(points)
    for first_index in range(count):
        first_a = points[first_index]
        first_b = points[(first_index + 1) % count]
        for second_index in range(first_index + 1, count):
            if (
                second_index == first_index
                or second_index == (first_index + 1) % count
                or first_index == (second_index + 1) % count
            ):
                continue
            second_a = points[second_index]
            second_b = points[(second_index + 1) % count]
            o1 = _orientation(first_a, first_b, second_a)
            o2 = _orientation(first_a, first_b, second_b)
            o3 = _orientation(second_a, second_b, first_a)
            o4 = _orientation(second_a, second_b, first_b)
            if (
                ((o1 > epsilon and o2 < -epsilon) or (o1 < -epsilon and o2 > epsilon))
                and ((o3 > epsilon and o4 < -epsilon) or (o3 < -epsilon and o4 > epsilon))
            ):
                return False
            if min(abs(o1), abs(o2), abs(o3), abs(o4)) <= epsilon:
                # A nonadjacent collinear/touching case is not a simple PSLG.
                def within(value: float, first: float, second: float) -> bool:
                    return min(first, second) - epsilon <= value <= max(first, second) + epsilon

                tests = (
                    (abs(o1) <= epsilon, second_a, first_a, first_b),
                    (abs(o2) <= epsilon, second_b, first_a, first_b),
                    (abs(o3) <= epsilon, first_a, second_a, second_b),
                    (abs(o4) <= epsilon, first_b, second_a, second_b),
                )
                for collinear, point, edge_a, edge_b in tests:
                    if collinear and within(point[0], edge_a[0], edge_b[0]) and within(
                        point[1], edge_a[1], edge_b[1]
                    ):
                        return False
    return True


def point_segment_distance(
    point: Sequence[float], first: Sequence[float], second: Sequence[float]
) -> float:
    dx = float(second[0]) - float(first[0])
    dy = float(second[1]) - float(first[1])
    denominator = dx * dx + dy * dy
    if denominator <= 0.0:
        return math.hypot(
            float(point[0]) - float(first[0]),
            float(point[1]) - float(first[1]),
        )
    projection = (
        (float(point[0]) - float(first[0])) * dx
        + (float(point[1]) - float(first[1])) * dy
    ) / denominator
    projection = max(0.0, min(1.0, projection))
    nearest_x = float(first[0]) + projection * dx
    nearest_y = float(first[1]) + projection * dy
    return math.hypot(float(point[0]) - nearest_x, float(point[1]) - nearest_y)


def coordinate_suppression_row(
    points: Sequence[Sequence[float]],
    suppressed: Sequence[int],
    target_degrees: float,
) -> dict[str, Any]:
    removed = {int(value) for value in suppressed}
    kept_indices = [index for index in range(len(points)) if index not in removed]
    kept = [points[index] for index in kept_indices]
    original_area = signed_twice_area(points)
    metrics = boundary_angle_rows(kept, target_degrees)
    chord_rows = []
    for source_index in sorted(removed):
        previous = (source_index - 1) % len(points)
        while previous in removed:
            previous = (previous - 1) % len(points)
        following = (source_index + 1) % len(points)
        while following in removed:
            following = (following + 1) % len(points)
        chord_rows.append(
            {
                "suppressed_source_index": source_index,
                "retained_neighbor_source_indices": [previous, following],
                "chord_length_m": math.dist(points[previous], points[following]),
                "suppressed_point_distance_to_chord_m": point_segment_distance(
                    points[source_index], points[previous], points[following]
                ),
            }
        )
    return {
        "suppressed_source_indices": sorted(removed),
        "retained_source_indices": kept_indices,
        "simple_polygon": polygon_is_simple(kept),
        "orientation_preserved": signed_twice_area(kept) * original_area > 0.0,
        "retained_projected_area_ratio": abs(signed_twice_area(kept) / original_area),
        "boundary_angle_analysis": metrics,
        "chords": chord_rows,
        "necessary_corner_condition_passes": bool(
            metrics["necessary_fixed_boundary_corner_condition_passes"]
        ),
        "source_mesh_topology_compatibility_proven": False,
        "repair_authorized": False,
    }


def analyze_coordinate_suppressions(
    capture: Mapping[str, Any], max_cardinality: int, target_degrees: float
) -> dict[str, Any]:
    points = [
        [float(value) for value in row["xy"]]
        for row in capture["fixed_pslg"]["boundary_coordinates"]
    ]
    fixed = boundary_angle_rows(points, target_degrees)
    first_cardinality = None
    passing: list[dict[str, Any]] = []
    for cardinality in range(1, int(max_cardinality) + 1):
        for suppressed in itertools.combinations(range(len(points)), cardinality):
            row = coordinate_suppression_row(points, suppressed, target_degrees)
            if (
                row["simple_polygon"]
                and row["orientation_preserved"]
                and row["necessary_corner_condition_passes"]
            ):
                passing.append(row)
        if passing:
            first_cardinality = cardinality
            break
    return {
        "analysis": "COORDINATE_ONLY_NECESSARY_CONDITION_NOT_SOURCE_TOPOLOGY",
        "fixed_boundary": fixed,
        "first_passing_suppression_cardinality": first_cardinality,
        "passing_variant_count": len(passing),
        "passing_variants": passing,
        "direct_suppression_authorized": False,
        "repair_proven": False,
    }


def _atomic_write_once(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists():
        raise RuntimeError(f"Attempt 28 refuses to overwrite {path.name}")
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise RuntimeError(f"Attempt 28 temporary path already exists: {temporary.name}")
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with temporary.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
        stream.flush()
    temporary.replace(path)


def _ordered_cycle_from_edge_keys(
    edge_keys: Iterable[tuple[int, int]]
) -> list[int] | None:
    edges = {tuple(sorted((int(a), int(b)))) for a, b in edge_keys}
    adjacency: dict[int, list[int]] = {}
    for first, second in edges:
        adjacency.setdefault(first, []).append(second)
        adjacency.setdefault(second, []).append(first)
    if not adjacency or any(len(values) != 2 for values in adjacency.values()):
        return None
    start = min(adjacency)
    candidates = []
    for first_next in sorted(adjacency[start]):
        cycle = [start]
        previous = None
        current = start
        following = first_next
        while True:
            previous, current = current, following
            if current == start:
                break
            if current in cycle:
                cycle = []
                break
            cycle.append(current)
            options = [value for value in adjacency[current] if value != previous]
            if len(options) != 1:
                cycle = []
                break
            following = options[0]
            if len(cycle) > len(adjacency):
                cycle = []
                break
        if cycle and len(cycle) == len(adjacency):
            candidates.append(cycle)
    return min(candidates) if candidates else None


def _face_components(selected: set[int], faces_by_index: Mapping[int, Any]) -> int:
    remaining = set(selected)
    components = 0
    while remaining:
        components += 1
        stack = [remaining.pop()]
        while stack:
            face = faces_by_index[stack.pop()]
            for edge in face.edges:
                for other in edge.link_faces:
                    index = int(other.index)
                    if index in remaining:
                        remaining.remove(index)
                        stack.append(index)
    return components


def _expand_faces(selected: set[int], faces_by_index: Mapping[int, Any]) -> set[int]:
    expanded = set(selected)
    for face_index in selected:
        for edge in faces_by_index[face_index].edges:
            expanded.update(int(face.index) for face in edge.link_faces)
    return expanded


def _chart_for_cycle(
    obj: Any,
    bm: Any,
    cycle_ids: Sequence[int],
    selected: set[int],
    np: Any,
    Vector: Any,
) -> dict[str, Any]:
    lateral = Vector((0.9999999403953552, 0.0, 0.0)).normalized()
    longitudinal = Vector((0.0, -0.3000001609325409, 0.9539390802383423)).normalized()
    vertices = [bm.verts[int(index)] for index in cycle_ids]
    world = [obj.matrix_world @ vertex.co for vertex in vertices]
    centroid_array = np.mean(np.asarray([tuple(value) for value in world]), axis=0)
    centroid = Vector(tuple(float(value) for value in centroid_array))
    centered = np.asarray([tuple(value - centroid) for value in world])
    _u, singular_values, vh = np.linalg.svd(centered, full_matrices=False)
    normal = Vector(tuple(float(value) for value in vh[-1])).normalized()
    surrounding = []
    for vertex in vertices:
        for face in vertex.link_faces:
            if int(face.index) not in selected:
                transformed = obj.matrix_world.to_3x3() @ face.normal
                if transformed.length:
                    surrounding.append(transformed.normalized())
    if surrounding:
        average = sum(surrounding, Vector()).normalized()
        if normal.dot(average) < 0.0:
            normal.negate()
    elif normal.dot(longitudinal) < 0.0:
        normal.negate()
    u_axis = lateral - normal * lateral.dot(normal)
    if u_axis.length < 1.0e-8:
        u_axis = Vector(tuple(float(value) for value in vh[0]))
    u_axis.normalize()
    v_axis = normal.cross(u_axis).normalized()
    if v_axis.dot(longitudinal) < 0.0:
        u_axis.negate()
        v_axis.negate()
    coordinates = [
        [float((value - centroid).dot(u_axis)), float((value - centroid).dot(v_axis))]
        for value in world
    ]
    heights = [float((value - centroid).dot(normal)) for value in world]
    if signed_twice_area(coordinates) < 0.0:
        cycle_ids = list(reversed(cycle_ids))
        coordinates.reverse()
        heights.reverse()
    return {
        "cycle_mesh_vertex_indices": [int(value) for value in cycle_ids],
        "coordinates_xy_m": coordinates,
        "centroid_world_m": [float(value) for value in centroid],
        "normal_world": [float(value) for value in normal],
        "singular_values": [float(value) for value in singular_values],
        "maximum_absolute_boundary_deviation_m": max(abs(value) for value in heights),
        "rms_absolute_boundary_deviation_m": math.sqrt(
            sum(value * value for value in heights) / len(heights)
        ),
    }


def _align_capture_to_current(
    captured_xy: Sequence[Sequence[float]], chart: Mapping[str, Any]
) -> dict[str, Any]:
    current_xy = chart["coordinates_xy_m"]
    current_ids = chart["cycle_mesh_vertex_indices"]
    if len(captured_xy) != len(current_xy):
        raise RuntimeError("Attempt 28 current boundary count disagrees with capture")
    best = None
    count = len(current_xy)
    orientations = [
        ("forward", list(range(count))),
        ("reversed", [0] + list(range(count - 1, 0, -1))),
    ]
    for orientation_name, order in orientations:
        ordered_xy = [current_xy[index] for index in order]
        ordered_ids = [current_ids[index] for index in order]
        for rotation in range(count):
            candidate_xy = ordered_xy[rotation:] + ordered_xy[:rotation]
            candidate_ids = ordered_ids[rotation:] + ordered_ids[:rotation]
            distances = [
                math.dist(captured_xy[index], candidate_xy[index])
                for index in range(count)
            ]
            row = {
                "orientation": orientation_name,
                "rotation": rotation,
                "maximum_xy_distance_m": max(distances),
                "rms_xy_distance_m": math.sqrt(
                    sum(value * value for value in distances) / count
                ),
                "capture_source_index_to_mesh_vertex_index": candidate_ids,
            }
            if best is None or row["maximum_xy_distance_m"] < best["maximum_xy_distance_m"]:
                best = row
    if best is None:
        raise RuntimeError("Attempt 28 could not align captured boundary")
    return best


def _domain_diagnostic(
    name: str,
    selected: set[int],
    obj: Any,
    bm: Any,
    faces_by_index: Mapping[int, Any],
    global_seam_vertices: set[int],
    global_seam_edges: set[tuple[int, int]],
    target_degrees: float,
    maximum_deviation_m: float,
    np: Any,
    Vector: Any,
) -> dict[str, Any]:
    selected_faces = [faces_by_index[index] for index in sorted(selected)]
    vertices = {int(vertex.index) for face in selected_faces for vertex in face.verts}
    edges = {edge for face in selected_faces for edge in face.edges}
    boundary_edges = {
        tuple(sorted((int(edge.verts[0].index), int(edge.verts[1].index))))
        for edge in edges
        if sum(int(face.index) in selected for face in edge.link_faces) == 1
    }
    boundary_vertices = {value for edge in boundary_edges for value in edge}
    seam_edge_intersection = boundary_edges.intersection(global_seam_edges)
    seam_vertex_intersection = boundary_vertices.intersection(global_seam_vertices)
    if not seam_edge_intersection and not seam_vertex_intersection:
        global_seam_relation = "DISJOINT"
    elif boundary_edges == global_seam_edges:
        global_seam_relation = "EXACT_COMPLETE_GLOBAL_SEAM_BOUNDARY"
    else:
        global_seam_relation = "PARTIAL_GLOBAL_SEAM_CONTACT"
    cycle = _ordered_cycle_from_edge_keys(boundary_edges)
    components = _face_components(selected, faces_by_index)
    euler = len(vertices) - len(edges) + len(selected)
    row: dict[str, Any] = {
        "candidate": name,
        "face_count": len(selected),
        "face_indices_sha256": canonical_sha256(sorted(selected)),
        "vertex_count": len(vertices),
        "vertex_indices_sha256": canonical_sha256(sorted(vertices)),
        "edge_count": len(edges),
        "boundary_edge_count": len(boundary_edges),
        "boundary_edge_indices_sha256": canonical_sha256(sorted(boundary_edges)),
        "face_component_count": components,
        "euler_characteristic": euler,
        "single_boundary_cycle": cycle is not None,
        "touches_global_seam": global_seam_relation != "DISJOINT",
        "global_seam_relation": global_seam_relation,
        "outside_face_count": len(faces_by_index) - len(selected),
        "outside_face_indices_sha256": canonical_sha256(
            sorted(set(faces_by_index).difference(selected))
        ),
        "mesh_mutated": False,
    }
    if cycle is None:
        row["necessary_candidate_eligibility_passes"] = False
        row["eligibility_failures"] = ["single_boundary_cycle"]
        return row
    chart = _chart_for_cycle(obj, bm, cycle, selected, np, Vector)
    angles = boundary_angle_rows(chart["coordinates_xy_m"], target_degrees)
    simple = polygon_is_simple(chart["coordinates_xy_m"])
    checks = {
        "single_face_component": components == 1,
        "disk_euler_characteristic_1": euler == 1,
        "single_boundary_cycle": True,
        "simple_projected_boundary": simple,
        "minimum_boundary_interior_angle_at_least_12_degrees": bool(
            angles["necessary_fixed_boundary_corner_condition_passes"]
        ),
        "maximum_chart_boundary_deviation_at_most_0.0011_m": float(
            chart["maximum_absolute_boundary_deviation_m"]
        )
        <= maximum_deviation_m,
        "global_seam_relation_is_disjoint_or_exact_complete_boundary": (
            global_seam_relation
            in {"DISJOINT", "EXACT_COMPLETE_GLOBAL_SEAM_BOUNDARY"}
        ),
    }
    row.update(
        {
            "boundary_cycle_mesh_vertex_indices": chart[
                "cycle_mesh_vertex_indices"
            ],
            "boundary_cycle_mesh_vertex_indices_sha256": canonical_sha256(
                chart["cycle_mesh_vertex_indices"]
            ),
            "projected_boundary_xy_m": chart["coordinates_xy_m"],
            "chart": {
                key: value
                for key, value in chart.items()
                if key not in {"cycle_mesh_vertex_indices", "coordinates_xy_m"}
            },
            "boundary_angle_analysis": angles,
            "simple_projected_boundary": simple,
            "necessary_candidate_checks": checks,
            "necessary_candidate_eligibility_passes": all(checks.values()),
            "eligibility_failures": [name for name, passed in checks.items() if not passed],
            "eligibility_is_sufficient_for_reconstruction": False,
        }
    )
    return row


def run_blender_diagnostic(config: Mapping[str, Any], verified: Mapping[str, Any]) -> None:
    import bmesh  # type: ignore
    import bpy  # type: ignore
    import numpy as np  # type: ignore
    from mathutils import Vector  # type: ignore

    output = project_output_path(config["output"]["root"])
    if output.exists():
        raise RuntimeError("append-only Attempt 28 output already exists")
    output.mkdir(parents=True)
    started = {
        "schema": "kira.avatar.r24.blackproject_attempt28.started.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "READ_ONLY_SOURCE_BOUNDARY_DIAGNOSTIC_STARTED",
        "worker": str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"),
        "worker_sha256": sha256_file(Path(__file__).resolve()),
        "config": str(DEFAULT_CONFIG.relative_to(ROOT)).replace("\\", "/"),
        "config_sha256": sha256_file(DEFAULT_CONFIG),
        "blend_save_permitted": False,
    }
    _atomic_write_once(output / config["output"]["started"], started)
    try:
        patch_path = project_existing_path(
            config["bindings"]["preserved_patch_blend"]["path"]
        )
        bpy.ops.wm.open_mainfile(filepath=str(patch_path), load_ui=False)
        obj = bpy.data.objects.get(config["source_mesh_diagnostic"]["object_name"])
        if obj is None or obj.type != "MESH":
            raise RuntimeError("Attempt 28 exact preserved patch object is absent")
        if obj.data.name != config["source_mesh_diagnostic"]["mesh_name"]:
            raise RuntimeError("Attempt 28 preserved patch mesh identity drifted")
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.verts.index_update()
        bm.edges.index_update()
        bm.faces.index_update()
        faces_by_index = {int(face.index): face for face in bm.faces}

        domain_record = json.loads(
            project_existing_path(
                config["bindings"]["repair_domain_diagnostic"]["path"]
            ).read_text(encoding="utf-8")
        )
        initial_record = next(
            row for row in domain_record["domains"] if int(row["face_ring_expansion"]) == 0
        )
        current_record = domain_record["smallest_qualified_replacement_domain"]
        initial = {int(value) for value in initial_record["face_indices"]}
        current = {int(value) for value in current_record["face_indices"]}
        source_contract = config["source_mesh_diagnostic"]
        if (
            len(initial) != int(source_contract["initial_involved_face_count"])
            or canonical_sha256(sorted(initial))
            != source_contract["initial_involved_face_sha256"]
            or len(current) != int(source_contract["current_domain_face_count"])
            or canonical_sha256(sorted(current))
            != source_contract["current_domain_face_sha256"]
        ):
            raise RuntimeError("Attempt 28 inherited repair-domain identity drifted")

        global_seam_edges = {
            tuple(sorted((int(edge.verts[0].index), int(edge.verts[1].index))))
            for edge in bm.edges
            if len(edge.link_faces) == 1
        }
        global_seam_vertices = {value for edge in global_seam_edges for value in edge}
        if len(global_seam_vertices) != int(source_contract["global_seam_vertex_count"]):
            raise RuntimeError("Attempt 28 global 34-point seam drifted")
        global_seam_world = sorted(
            [
                [float(value) for value in (obj.matrix_world @ bm.verts[index].co)]
                for index in global_seam_vertices
            ]
        )

        current_row = _domain_diagnostic(
            "current_ring_2_fixed_boundary",
            current,
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
            int(current_row["vertex_count"])
            != int(source_contract["current_domain_vertex_count"])
            or current_row["vertex_indices_sha256"]
            != source_contract["current_domain_vertex_sha256"]
            or int(current_row["boundary_edge_count"])
            != int(source_contract["current_boundary_edge_count"])
            or current_row["boundary_edge_indices_sha256"]
            != source_contract["current_boundary_edge_sha256"]
        ):
            raise RuntimeError("Attempt 28 current domain topology drifted")
        expected_cycle_set = set(source_contract["current_boundary_cycle_mesh_vertex_indices"])
        if set(current_row["boundary_cycle_mesh_vertex_indices"]) != expected_cycle_set:
            raise RuntimeError("Attempt 28 current boundary mesh-vertex identity drifted")
        capture = json.loads(
            project_existing_path(config["bindings"]["attempt27_capture"]["path"])
            .read_text(encoding="utf-8")
        )
        captured_xy = [row["xy"] for row in capture["fixed_pslg"]["boundary_coordinates"]]
        alignment = _align_capture_to_current(
            captured_xy,
            {
                "coordinates_xy_m": current_row["projected_boundary_xy_m"],
                "cycle_mesh_vertex_indices": current_row[
                    "boundary_cycle_mesh_vertex_indices"
                ],
            },
        )
        if alignment["maximum_xy_distance_m"] > float(
            source_contract["captured_xy_match_tolerance_m"]
        ):
            raise RuntimeError("Attempt 28 source chart does not match Attempt 27 capture")
        capture_to_mesh = alignment["capture_source_index_to_mesh_vertex_index"]

        targeted = []
        for source_indices in source_contract["targeted_vertex_star_suppression_sets"]:
            selected = set(current)
            mesh_vertices = [capture_to_mesh[int(index)] for index in source_indices]
            added_faces = {
                int(face.index)
                for vertex_index in mesh_vertices
                for face in bm.verts[int(vertex_index)].link_faces
            }.difference(selected)
            selected.update(added_faces)
            row = _domain_diagnostic(
                "targeted_complete_vertex_stars_" + "_".join(str(v) for v in source_indices),
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
            row["capture_source_indices"] = list(source_indices)
            row["source_mesh_vertex_indices"] = mesh_vertices
            row["added_complete_vertex_star_face_count"] = len(added_faces)
            row["added_complete_vertex_star_face_indices"] = sorted(added_faces)
            targeted.append(row)

        ring_rows = []
        selected = set(initial)
        requested = set(int(value) for value in source_contract["uniform_face_ring_expansions_to_map"])
        for ring in range(1, max(requested) + 1):
            selected = _expand_faces(selected, faces_by_index)
            if ring not in requested:
                continue
            row = _domain_diagnostic(
                f"uniform_face_ring_{ring}",
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
            row["face_ring_expansion"] = ring
            ring_rows.append(row)

        coordinate_only = analyze_coordinate_suppressions(
            capture,
            int(config["coordinate_only_analysis"]["first_passing_suppression_cardinality"]),
            float(config["diagnosis"]["required_minimum_angle_degrees"]),
        )
        all_candidates = targeted + ring_rows
        eligible = [
            row for row in all_candidates if row["necessary_candidate_eligibility_passes"]
        ]
        eligible.sort(
            key=lambda row: (
                row["global_seam_relation"]
                == "EXACT_COMPLETE_GLOBAL_SEAM_BOUNDARY",
                row["face_count"],
                row["candidate"],
            )
        )
        diagnostic = {
            "schema": "kira.avatar.r24.blackproject_attempt28.local_boundary_feasibility_diagnostic.v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "CAPTURED_EXISTING_SOURCE_BOUNDARY_OPTIONS_NO_REPAIR",
            "attempt_id": "attempt_28",
            "inputs": verified,
            "fixed_pslg_proof": config["diagnosis"],
            "coordinate_only_analysis": coordinate_only,
            "current_domain": current_row,
            "capture_to_source_mesh_alignment": alignment,
            "targeted_complete_vertex_star_candidates": targeted,
            "uniform_face_ring_candidates": ring_rows,
            "smallest_necessary_eligible_existing_source_candidate": eligible[0]
            if eligible
            else None,
            "necessary_eligible_candidate_count": len(eligible),
            "global_seam": {
                "vertex_count": len(global_seam_vertices),
                "edge_count": len(global_seam_edges),
                "world_coordinates_sha256": canonical_sha256(global_seam_world),
                "coordinates_mutated": False,
            },
            "truth": {
                "source_mesh_read_only": True,
                "fixed_32_edge_boundary_globally_infeasible_at_12_degrees": True,
                "replacement_boundary_repair_applied": False,
                "triangulation_performed": False,
                "mesh_mutated": False,
                "body_mutated": False,
                "render_reached": False,
                "blend_saved": False,
                "runtime_changed": False,
                "necessary_candidate_is_sufficient_repair_proof": False,
            },
        }
        _atomic_write_once(output / config["output"]["diagnostic"], diagnostic)
        raise RuntimeError(
            "Attempt 28 captured existing-source replacement-boundary feasibility; "
            "diagnostic-only stop before triangulation or mesh mutation"
        )
    except Exception as exc:
        failure = {
            "schema": "kira.avatar.r24.blackproject_attempt28.failure.v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "NO_SAVE_ATTEMPT28_DIAGNOSTIC_STOP_PRESERVED",
            "attempt_id": "attempt_28",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "diagnostic_exists": (output / config["output"]["diagnostic"]).is_file(),
            "mesh_mutated": False,
            "body_mutated": False,
            "render_reached": False,
            "blend_saved": False,
            "runtime_changed": False,
        }
        _atomic_write_once(output / config["output"]["failure"], failure)
        raise
    finally:
        if "bm" in locals():
            bm.free()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    argv = []
    if "--" in __import__("sys").argv:
        argv = __import__("sys").argv[__import__("sys").argv.index("--") + 1 :]
    else:
        argv = __import__("sys").argv[1:]
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = load_config(config_path)
    verified = verify_bindings(config)
    run_blender_diagnostic(config, verified)


if __name__ == "__main__":
    main()
