"""No-save A09 internal-midpoint and coupled fair-surface simulation.

This worker leaves the exact sealed R19 body and the A08 worker untouched.  It
replaces only the experimental poke-centroid refinement with deterministic
midpoints on original patch-internal edges.  The exact 34 boundary vertices and
edges and every out-of-patch state remain frozen.  A coupled screened
biharmonic displacement field distributes bounded outside-tangent constraints
before the unchanged A06 local-normal anatomical relief is reapplied.

This is external private visual/topology work only.  It creates no internal
tract, physiology, elimination, reproduction, pregnancy, sensation, or
subjective experience, and it never saves a Blend.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any, Iterable, Mapping, Sequence

import bmesh
import bpy
from mathutils import Vector
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_simulate_kira_r24_direct_subdivision_surface as a08  # noqa: E402


SOURCE = a08.SOURCE
SOURCE_SHA256 = a08.SOURCE_SHA256
BODY_NAME = a08.BODY_NAME
RIG_NAME = a08.RIG_NAME
PATCH_MATERIAL_INDEX = a08.PATCH_MATERIAL_INDEX
A08_WORKER = ROOT / "tools/blender_simulate_kira_r24_direct_subdivision_surface.py"
A08_WORKER_SHA256 = "6a75233d53fabebb9afc61e46184d3dbe5718a648317a93f8b2b2792fab7ab1c"
A08_REPORT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_direct_subdivision_surface/attempt_08/SIMULATION_REPORT.json"
)
A08_REPORT_SHA256 = "8f9a63f93ceb082896c55d81b43f86a91f5bec5150427e126f20460a04012fd4"
A06_REPORT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_direct_subdivision_surface/attempt_06/SIMULATION_REPORT.json"
)
A06_REPORT_SHA256 = "e6e0a490855c0c80465517bffd2c38fdec69f00a8b0500c67ad9764654aabfe8"

OUTPUT_ROOT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface"
)
EXPECTED_INTERNAL_EDGES = 547
EXPECTED_PATCH_VERTICES = 753
EXPECTED_PATCH_FACES = 1470
EXPECTED_PATCH_EDGES = 2222
EXPECTED_BOUNDARY_EDGES = 34
EXPECTED_BOUNDARY_VERTICES = 34

RING_1_CAP_M = 0.00150
RING_2_CAP_M = 0.00090
DEEP_INTERIOR_CAP_M = 0.00060
FIT_P95_CAP_M = 0.00090
FIT_RMS_CAP_M = 0.00045
TOTAL_BASE_FIT_CAP_M = 0.00150
RELIEF_CAP_M = 0.00300
COMBINED_CAP_M = 0.00450
MOVEMENT_EPSILON_M = 1.0e-8
TARGET_LOW_DOT = 0.715
TARGET_MEDIAN_EDGE_DOT = 0.945
MAXIMUM_EDGE_RATIO = 8.0
INHERITED_WHOLE_INTERSECTIONS = 29
BACKTRACK_SCALES = (1.0, 0.75, 0.5, 0.375, 0.25, 0.125)

ACTIVE_OUTPUT: Path | None = None


def sha256(path: Path) -> str:
    return a08.sha256(path)


def relative(path: Path) -> str:
    return a08.relative(path)


def allocate_output() -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    indexes = []
    for child in OUTPUT_ROOT.iterdir():
        if child.is_dir() and child.name.startswith("attempt_"):
            try:
                indexes.append(int(child.name.split("_")[-1]))
            except ValueError:
                continue
    output = OUTPUT_ROOT / f"attempt_{max(indexes, default=0) + 1:02d}"
    output.mkdir()
    return output


def edge_id(first: bmesh.types.BMVert, second: bmesh.types.BMVert) -> tuple[int, int]:
    return tuple(sorted((int(first.index), int(second.index))))


def triangle_minimum_angle_world(
    body: bpy.types.Object,
    vertices: Sequence[bmesh.types.BMVert],
) -> float:
    points = [body.matrix_world @ vertex.co for vertex in vertices]
    angles = []
    for index in range(3):
        center = points[index]
        first = points[(index + 1) % 3] - center
        second = points[(index + 2) % 3] - center
        if first.length <= 1.0e-12 or second.length <= 1.0e-12:
            return 0.0
        cosine = max(-1.0, min(1.0, float(first.normalized().dot(second.normalized()))))
        angles.append(math.acos(cosine))
    return min(angles)


def choose_two_split_triangulation(
    body: bpy.types.Object,
    first: bmesh.types.BMVert,
    second: bmesh.types.BMVert,
    opposite: bmesh.types.BMVert,
    midpoint_second_opposite: bmesh.types.BMVert,
    midpoint_opposite_first: bmesh.types.BMVert,
    original_ids: Mapping[bmesh.types.BMVert, int],
) -> tuple[list[tuple[bmesh.types.BMVert, ...]], dict[str, Any]]:
    option_a = [
        (first, second, midpoint_second_opposite),
        (first, midpoint_second_opposite, midpoint_opposite_first),
        (midpoint_opposite_first, midpoint_second_opposite, opposite),
    ]
    option_b = [
        (first, second, midpoint_opposite_first),
        (second, midpoint_second_opposite, midpoint_opposite_first),
        (midpoint_opposite_first, midpoint_second_opposite, opposite),
    ]
    score_a = min(triangle_minimum_angle_world(body, face) for face in option_a)
    score_b = min(triangle_minimum_angle_world(body, face) for face in option_b)
    if abs(score_a - score_b) <= 1.0e-12:
        canonical_a = tuple(
            sorted(
                tuple(sorted(int(original_ids.get(vertex, -1)) for vertex in face))
                for face in option_a
            )
        )
        canonical_b = tuple(
            sorted(
                tuple(sorted(int(original_ids.get(vertex, -1)) for vertex in face))
                for face in option_b
            )
        )
        selected = option_a if canonical_a <= canonical_b else option_b
        reason = "canonical_vertex_id_tie_break"
    elif score_a > score_b:
        selected = option_a
        reason = "maximum_minimum_world_angle_option_a"
    else:
        selected = option_b
        reason = "maximum_minimum_world_angle_option_b"
    return selected, {
        "option_a_minimum_angle_degrees": math.degrees(score_a),
        "option_b_minimum_angle_degrees": math.degrees(score_b),
        "selection_reason": reason,
    }


def interpolated_midpoint_weights(
    first: bmesh.types.BMVert,
    second: bmesh.types.BMVert,
    deform_layer: Any,
) -> dict[int, float]:
    values: dict[int, float] = defaultdict(float)
    for vertex in (first, second):
        for group_index, weight in vertex[deform_layer].items():
            values[int(group_index)] += 0.5 * float(weight)
    return a08.normalized_top_four(values)


def midpoint_uv(
    uv_by_vertex: Mapping[int, Sequence[float]],
    first_id: int,
    second_id: int,
) -> tuple[float, float]:
    first = uv_by_vertex[first_id]
    second = uv_by_vertex[second_id]
    return (
        (float(first[0]) + float(second[0])) * 0.5,
        (float(first[1]) + float(second[1])) * 0.5,
    )


def face_refinement_templates(
    body: bpy.types.Object,
    record: Mapping[str, Any],
    midpoint_by_edge: Mapping[tuple[int, int], bmesh.types.BMVert],
    original_ids: Mapping[bmesh.types.BMVert, int],
) -> tuple[list[tuple[bmesh.types.BMVert, ...]], dict[str, Any]]:
    vertices = list(record["vertices"])
    split = {
        index: midpoint_by_edge.get(
            tuple(
                sorted(
                    (
                        int(original_ids[vertices[index]]),
                        int(original_ids[vertices[(index + 1) % 3]]),
                    )
                )
            )
        )
        for index in range(3)
    }
    count = sum(value is not None for value in split.values())
    if count == 3:
        first, second, third = vertices
        midpoint_first_second = split[0]
        midpoint_second_third = split[1]
        midpoint_third_first = split[2]
        templates = [
            (first, midpoint_first_second, midpoint_third_first),
            (midpoint_first_second, second, midpoint_second_third),
            (midpoint_third_first, midpoint_second_third, third),
            (midpoint_first_second, midpoint_second_third, midpoint_third_first),
        ]
        evidence = {"split_internal_edge_count": 3, "selection_reason": "standard_1_to_4"}
    elif count == 2:
        unsplit_index = next(index for index, value in split.items() if value is None)
        first = vertices[unsplit_index]
        second = vertices[(unsplit_index + 1) % 3]
        opposite = vertices[(unsplit_index + 2) % 3]
        midpoint_second_opposite = split[(unsplit_index + 1) % 3]
        midpoint_opposite_first = split[(unsplit_index + 2) % 3]
        templates, evidence = choose_two_split_triangulation(
            body,
            first,
            second,
            opposite,
            midpoint_second_opposite,
            midpoint_opposite_first,
            original_ids,
        )
        evidence["split_internal_edge_count"] = 2
    elif count == 1:
        split_index = next(index for index, value in split.items() if value is not None)
        first = vertices[split_index]
        second = vertices[(split_index + 1) % 3]
        opposite = vertices[(split_index + 2) % 3]
        midpoint = split[split_index]
        templates = [
            (first, midpoint, opposite),
            (midpoint, second, opposite),
        ]
        evidence = {"split_internal_edge_count": 1, "selection_reason": "one_edge_bisection"}
    elif count == 0:
        templates = [tuple(vertices)]
        evidence = {"split_internal_edge_count": 0, "selection_reason": "unchanged_triangle"}
    else:
        raise RuntimeError("invalid internal-edge split count")
    return templates, evidence


def patch_neighbors(
    patch_vertices: Iterable[bmesh.types.BMVert],
    patch_edges: Iterable[bmesh.types.BMEdge],
) -> dict[bmesh.types.BMVert, set[bmesh.types.BMVert]]:
    vertices = set(patch_vertices)
    neighbors: dict[bmesh.types.BMVert, set[bmesh.types.BMVert]] = defaultdict(set)
    for edge in patch_edges:
        first, second = edge.verts
        if first in vertices and second in vertices:
            neighbors[first].add(second)
            neighbors[second].add(first)
    return neighbors


def candidate_face_dot(
    body: bpy.types.Object,
    patch_face: bmesh.types.BMFace,
    support: bmesh.types.BMVert,
    candidate_world: Vector,
    outside_normal: Vector,
) -> float:
    points = [
        candidate_world if vertex is support else body.matrix_world @ vertex.co
        for vertex in patch_face.verts
    ]
    normal = (points[1] - points[0]).cross(points[2] - points[0])
    if normal.length <= 1.0e-12:
        raise RuntimeError("seam support candidate collapsed a triangle")
    normal.normalize()
    return max(-1.0, min(1.0, float(normal.dot(outside_normal))))


def minimum_projection_for_dot(
    body: bpy.types.Object,
    patch_face: bmesh.types.BMFace,
    outside_face: bmesh.types.BMFace,
    edge: bmesh.types.BMEdge,
    support: bmesh.types.BMVert,
    target_dot: float,
) -> tuple[Vector, dict[str, Any]]:
    first_world = body.matrix_world @ edge.verts[0].co
    support_world = body.matrix_world @ support.co
    outside_normal = a08.world_face_normal(body, outside_face)
    full_target = support_world - outside_normal * (
        (support_world - first_world).dot(outside_normal)
    )
    full_delta = full_target - support_world
    baseline_dot = candidate_face_dot(
        body, patch_face, support, support_world, outside_normal
    )
    full_dot = candidate_face_dot(
        body, patch_face, support, full_target, outside_normal
    )
    if baseline_dot >= target_dot:
        alpha = 0.0
    else:
        if full_dot < target_dot:
            raise RuntimeError("outside tangent-plane projection cannot meet seam target")
        lower = 0.0
        upper = 1.0
        for _iteration in range(64):
            middle = (lower + upper) * 0.5
            dot = candidate_face_dot(
                body,
                patch_face,
                support,
                support_world + full_delta * middle,
                outside_normal,
            )
            if dot >= target_dot:
                upper = middle
            else:
                lower = middle
        alpha = upper
    requested = full_delta * alpha
    return requested, {
        "baseline_dot": baseline_dot,
        "target_dot": target_dot,
        "full_projection_dot": full_dot,
        "full_projection_world_m": float(full_delta.length),
        "minimum_alpha": float(alpha),
        "requested_world_m": float(requested.length),
    }


def seam_plane_records(
    body: bpy.types.Object,
    patch_faces: set[bmesh.types.BMFace],
    seam_edges: set[bmesh.types.BMEdge],
    original_ids: Mapping[bmesh.types.BMVert, int],
) -> list[dict[str, Any]]:
    records = []
    for edge in sorted(
        seam_edges,
        key=lambda item: tuple(sorted(int(original_ids[vertex]) for vertex in item.verts)),
    ):
        patch_face = next(face for face in edge.link_faces if face in patch_faces)
        outside_face = next(face for face in edge.link_faces if face not in patch_faces)
        supports = [vertex for vertex in patch_face.verts if vertex not in edge.verts]
        if len(supports) != 1:
            raise RuntimeError("refined seam face does not have exactly one child support")
        first = body.matrix_world @ edge.verts[0].co
        second = body.matrix_world @ edge.verts[1].co
        support = supports[0]
        support_world = body.matrix_world @ support.co
        outside_normal = a08.world_face_normal(body, outside_face)
        projected = support_world - outside_normal * (
            (support_world - first).dot(outside_normal)
        )
        edge_ids = tuple(sorted(int(original_ids[vertex]) for vertex in edge.verts))
        records.append(
            {
                "edge": edge,
                "edge_ids": edge_ids,
                "patch_face": patch_face,
                "outside_face": outside_face,
                "support": support,
                "first": first,
                "second": second,
                "normal": outside_normal,
                "support_world": support_world,
                "full_projection_delta": projected - support_world,
                "baseline_dot": candidate_face_dot(
                    body, patch_face, support, support_world, outside_normal
                ),
            }
        )
    return records


def select_minimum_seam_constraints(
    body: bpy.types.Object,
    planes: Sequence[Mapping[str, Any]],
) -> tuple[dict[bmesh.types.BMVert, Vector], list[dict[str, Any]]]:
    below_low = [record for record in planes if float(record["baseline_dot"]) < 0.70]
    below_median = [record for record in planes if float(record["baseline_dot"]) < 0.94]
    low_ids = {record["edge_ids"] for record in below_low}
    additional_count = max(0, len(below_median) - 16 - len(low_ids))
    additional = sorted(
        (record for record in below_median if record["edge_ids"] not in low_ids),
        key=lambda record: (-float(record["baseline_dot"]), record["edge_ids"]),
    )[:additional_count]
    selected = [(record, TARGET_LOW_DOT) for record in below_low]
    selected.extend((record, TARGET_MEDIAN_EDGE_DOT) for record in additional)
    targets: dict[bmesh.types.BMVert, Vector] = {}
    evidence = []
    for record, target_dot in sorted(selected, key=lambda item: item[0]["edge_ids"]):
        requested, calculation = minimum_projection_for_dot(
            body,
            record["patch_face"],
            record["outside_face"],
            record["edge"],
            record["support"],
            target_dot,
        )
        if requested.length > RING_1_CAP_M + MOVEMENT_EPSILON_M:
            raise RuntimeError(
                f"minimum seam constraint {record['edge_ids']} exceeds ring-1 cap"
            )
        if record["support"] in targets:
            raise RuntimeError("one seam child support received multiple hard constraints")
        targets[record["support"]] = requested
        evidence.append(
            {
                "boundary_vertex_ids": list(record["edge_ids"]),
                "support_vertex_index_before_final_reindex": int(record["support"].index),
                "reason": (
                    "minimum_below_0_70" if record["edge_ids"] in low_ids else "minimum_for_median_0_94"
                ),
                **calculation,
            }
        )
    return targets, evidence


def weighted_plane_target(
    point: Vector,
    planes: Sequence[Mapping[str, Any]],
    limit: int = 3,
) -> Vector:
    nearest = sorted(
        planes,
        key=lambda record: a08.point_segment_distance(
            point, record["first"], record["second"]
        ),
    )[:limit]
    weighted = Vector()
    total = 0.0
    for record in nearest:
        projected = point - record["normal"] * (
            (point - record["first"]).dot(record["normal"])
        )
        separation = a08.point_segment_distance(point, record["first"], record["second"])
        weight = 1.0 / max(separation, 1.0e-6) ** 2
        weighted += (projected - point) * weight
        total += weight
    if total <= 0.0:
        return Vector()
    return weighted / total


def exact_patch_intersection_summary(
    bm: bmesh.types.BMesh,
    patch_faces: set[bmesh.types.BMFace],
) -> dict[str, Any]:
    bm.faces.index_update()
    patch_indices = {int(face.index) for face in patch_faces}
    report = a08.exact_intersections.exact_nonadjacent_intersection_report(
        bm, include_pair_details=True
    )
    patch_pairs = [
        record
        for record in report["pairs"]
        if record.get("overlap_character") == "genuine_penetration"
        and any(int(index) in patch_indices for index in record["face_indices"])
    ]
    return {
        "whole_genuine_pair_count": int(report["exact_genuine_penetration_pair_count"]),
        "patch_genuine_pair_count": len(patch_pairs),
        "patch_pairs": patch_pairs,
    }


def local_shape_quality(
    body: bpy.types.Object,
    patch_faces: set[bmesh.types.BMFace],
    baseline_normals: Mapping[bmesh.types.BMFace, Vector],
) -> dict[str, Any]:
    minimum_dot = 1.0
    minimum_area = math.inf
    maximum_ratio = 0.0
    for face in patch_faces:
        points = [body.matrix_world @ vertex.co for vertex in face.verts]
        normal = (points[1] - points[0]).cross(points[2] - points[0])
        area = normal.length * 0.5
        minimum_area = min(minimum_area, area)
        if normal.length > 1.0e-12:
            normal.normalize()
        minimum_dot = min(minimum_dot, float(normal.dot(baseline_normals[face])))
        lengths = [
            (points[(index + 1) % 3] - points[index]).length for index in range(3)
        ]
        positive = [value for value in lengths if value > 1.0e-12]
        ratio = max(positive) / min(positive) if positive else math.inf
        maximum_ratio = max(maximum_ratio, ratio)
    return {
        "minimum_baseline_normal_dot": minimum_dot,
        "minimum_face_area_world_m2": minimum_area,
        "maximum_edge_ratio": maximum_ratio,
        "orientations_preserved": minimum_dot > 0.0,
    }


def displacement_distribution(
    values: Sequence[float],
) -> dict[str, float | list[float]]:
    ordered = sorted(map(float, values))
    if not ordered:
        return {"values_m": [], "maximum_m": 0.0, "p95_m": 0.0, "rms_m": 0.0}
    p95_index = max(0, min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1))
    return {
        "values_m": ordered,
        "maximum_m": max(ordered),
        "p95_m": ordered[p95_index],
        "rms_m": math.sqrt(sum(value * value for value in ordered) / len(ordered)),
    }


def capped_vector(value: Vector, maximum_length: float) -> Vector:
    result = value.copy()
    if result.length > maximum_length and result.length > 1.0e-12:
        result *= maximum_length / result.length
    return result


def ring_cap(distance: int) -> float:
    if distance <= 0:
        return 0.0
    if distance == 1:
        return RING_1_CAP_M
    if distance == 2:
        return RING_2_CAP_M
    return DEEP_INTERIOR_CAP_M


def solve_coupled_fair_fit(
    body: bpy.types.Object,
    bm: bmesh.types.BMesh,
    patch_faces: set[bmesh.types.BMFace],
    patch_vertices: set[bmesh.types.BMVert],
    patch_edges: Sequence[bmesh.types.BMEdge],
    seam_edges: set[bmesh.types.BMEdge],
    seam_vertices: set[bmesh.types.BMVert],
    distances: Mapping[bmesh.types.BMVert, int],
    original_ids: Mapping[bmesh.types.BMVert, int],
    parameters: Mapping[bmesh.types.BMVert, tuple[float, float]],
) -> dict[str, Any]:
    """Solve one coupled, screened differential-coordinate displacement field.

    The solve operates only on the refined patch.  It minimizes a screened
    displacement-Laplacian energy, with exact zero boundary displacement,
    selected high-weight seam goals, and lower-weight outside-plane goals in
    rings one and two.  It never solves ``Lx = 0`` for absolute positions.
    """
    vertices = sorted(patch_vertices, key=lambda vertex: int(vertex.index))
    vertex_index = {vertex: index for index, vertex in enumerate(vertices)}
    neighbors = patch_neighbors(patch_vertices, patch_edges)
    if any(not neighbors.get(vertex) for vertex in vertices):
        raise RuntimeError("coupled fair-fit graph contains an isolated patch vertex")

    base_local = {vertex: vertex.co.copy() for vertex in vertices}
    base_world = {vertex: body.matrix_world @ vertex.co for vertex in vertices}
    baseline_normals = {
        face: a08.world_face_normal(body, face).copy() for face in patch_faces
    }
    planes = seam_plane_records(body, patch_faces, seam_edges, original_ids)
    hard_targets, hard_records = select_minimum_seam_constraints(body, planes)

    count = len(vertices)
    laplacian = np.zeros((count, count), dtype=np.float64)
    for vertex in vertices:
        row = vertex_index[vertex]
        linked = sorted(neighbors[vertex], key=lambda item: int(item.index))
        laplacian[row, row] = 1.0
        reciprocal = 1.0 / len(linked)
        for neighbor in linked:
            laplacian[row, vertex_index[neighbor]] -= reciprocal
    biharmonic = laplacian.T @ laplacian

    # Identity screening preserves the exact source surface; the coupled
    # differential term spreads only the small requested tangent corrections.
    fidelity_weight = 18.0
    differential_weight = 1.0
    matrix = fidelity_weight * np.eye(count, dtype=np.float64)
    matrix += differential_weight * biharmonic
    target = np.zeros((count, 3), dtype=np.float64)
    constraint_records = []
    for vertex in vertices:
        row = vertex_index[vertex]
        distance = int(distances[vertex])
        weight = 0.0
        requested = Vector()
        kind = "screened_source_fidelity_only"
        if vertex in seam_vertices:
            weight = 1.0e9
            kind = "exact_zero_boundary"
        elif vertex in hard_targets:
            weight = 2.5e5
            requested = hard_targets[vertex].copy()
            kind = "selected_minimum_seam_constraint"
        elif distance == 1:
            weight = 420.0
            requested = capped_vector(
                weighted_plane_target(base_world[vertex], planes), RING_1_CAP_M
            )
            kind = "ring_1_outside_plane_soft_constraint_full_weight"
        elif distance == 2:
            weight = 147.0
            requested = capped_vector(
                weighted_plane_target(base_world[vertex], planes), RING_2_CAP_M
            )
            kind = "ring_2_outside_plane_soft_constraint_0_35_weight"
        if weight > 0.0:
            matrix[row, row] += weight
            target[row, :] += weight * np.asarray(tuple(requested), dtype=np.float64)
            constraint_records.append(
                {
                    "vertex_index_before_final_reindex": int(vertex.index),
                    "original_vertex_id": int(original_ids.get(vertex, -1)),
                    "graph_ring": distance,
                    "kind": kind,
                    "weight": weight,
                    "requested_world_m": a08.vector_record(requested),
                    "requested_length_m": float(requested.length),
                }
            )

    try:
        solved_array = np.linalg.solve(matrix, target)
    except np.linalg.LinAlgError as exc:
        raise RuntimeError(f"coupled screened fair-fit solve failed: {exc}") from exc
    solved_world = {
        vertex: Vector(tuple(float(value) for value in solved_array[vertex_index[vertex], :]))
        for vertex in vertices
    }
    for vertex in seam_vertices:
        solved_world[vertex] = Vector()
    # The selected seam goals are exact within the coupled field; their
    # neighbors are still supplied by the single global solve.
    for vertex, requested in hard_targets.items():
        solved_world[vertex] = requested.copy()

    cap_scale = 1.0
    for vertex, displacement in solved_world.items():
        maximum = ring_cap(int(distances[vertex]))
        if displacement.length > maximum + MOVEMENT_EPSILON_M:
            cap_scale = min(cap_scale, maximum / displacement.length)
    raw_distribution = displacement_distribution(
        [displacement.length for displacement in solved_world.values()]
    )
    if float(raw_distribution["maximum_m"]) > TOTAL_BASE_FIT_CAP_M:
        cap_scale = min(
            cap_scale,
            TOTAL_BASE_FIT_CAP_M / float(raw_distribution["maximum_m"]),
        )
    if float(raw_distribution["p95_m"]) > FIT_P95_CAP_M:
        cap_scale = min(cap_scale, FIT_P95_CAP_M / float(raw_distribution["p95_m"]))
    if float(raw_distribution["rms_m"]) > FIT_RMS_CAP_M:
        cap_scale = min(cap_scale, FIT_RMS_CAP_M / float(raw_distribution["rms_m"]))

    world_to_local = body.matrix_world.inverted().to_3x3()

    def evaluate(scale: float) -> dict[str, Any]:
        for vertex in vertices:
            vertex.co = base_local[vertex] + world_to_local @ (
                solved_world[vertex] * float(scale)
            )
        for vertex in seam_vertices:
            vertex.co = base_local[vertex].copy()
        bm.normal_update()
        shape = local_shape_quality(body, patch_faces, baseline_normals)
        seam = a08.seam_edge_records(
            body, patch_faces, seam_edges, original_ids, parameters
        )
        seam_values = [float(record["normal_dot"]) for record in seam["records"]]
        seam_minimum = min(seam_values, default=-1.0)
        seam_median = statistics.median(seam_values) if seam_values else -1.0
        seam_dihedral = math.degrees(
            math.acos(max(-1.0, min(1.0, seam_minimum)))
        )
        intersections = exact_patch_intersection_summary(bm, patch_faces)
        movements = [
            float((body.matrix_world @ vertex.co - base_world[vertex]).length)
            for vertex in vertices
        ]
        distribution = displacement_distribution(movements)
        ring_maxima = {
            str(ring): max(
                (
                    movements[vertex_index[vertex]]
                    for vertex in vertices
                    if int(distances[vertex]) == ring
                ),
                default=0.0,
            )
            for ring in (0, 1, 2)
        }
        ring_maxima["deep"] = max(
            (
                movements[vertex_index[vertex]]
                for vertex in vertices
                if int(distances[vertex]) >= 3
            ),
            default=0.0,
        )
        checks = {
            "orientation_preserved": bool(shape["orientations_preserved"]),
            "nondegenerate": float(shape["minimum_face_area_world_m2"]) > 1.0e-10,
            "edge_ratio_at_most_8": float(shape["maximum_edge_ratio"])
            <= MAXIMUM_EDGE_RATIO,
            "patch_exact_intersections_zero": intersections[
                "patch_genuine_pair_count"
            ]
            == 0,
            "whole_exact_intersections_29": intersections[
                "whole_genuine_pair_count"
            ]
            == INHERITED_WHOLE_INTERSECTIONS,
            "seam_minimum_at_least_0_70": seam_minimum >= 0.70,
            "seam_median_at_least_0_94": seam_median >= 0.94,
            "seam_dihedral_at_most_45": seam_dihedral <= 45.0,
            "ring_0_exact_zero": ring_maxima["0"] <= MOVEMENT_EPSILON_M,
            "ring_1_cap": ring_maxima["1"] <= RING_1_CAP_M + MOVEMENT_EPSILON_M,
            "ring_2_cap": ring_maxima["2"] <= RING_2_CAP_M + MOVEMENT_EPSILON_M,
            "deep_cap": ring_maxima["deep"]
            <= DEEP_INTERIOR_CAP_M + MOVEMENT_EPSILON_M,
            "overall_cap": float(distribution["maximum_m"])
            <= TOTAL_BASE_FIT_CAP_M + MOVEMENT_EPSILON_M,
            "p95_cap": float(distribution["p95_m"])
            <= FIT_P95_CAP_M + MOVEMENT_EPSILON_M,
            "rms_cap": float(distribution["rms_m"])
            <= FIT_RMS_CAP_M + MOVEMENT_EPSILON_M,
        }
        return {
            "scale": float(scale),
            "passed": all(checks.values()),
            "checks": checks,
            "shape": shape,
            "seam_minimum_dot": seam_minimum,
            "seam_median_dot": seam_median,
            "maximum_seam_dihedral_degrees": seam_dihedral,
            "intersections": intersections,
            "distribution": distribution,
            "ring_maxima_m": ring_maxima,
        }

    trials = []
    accepted: dict[str, Any] | None = None
    failed_above: float | None = None
    for multiplier in BACKTRACK_SCALES:
        trial = evaluate(cap_scale * multiplier)
        trials.append(trial)
        if trial["passed"]:
            accepted = trial
            break
        failed_above = float(trial["scale"])
    if accepted is None:
        for vertex in vertices:
            vertex.co = base_local[vertex].copy()
        bm.normal_update()
        raise RuntimeError(
            "coupled fair-fit could not meet seam, topology, intersection, and movement gates"
        )

    # If backtracking found a lower passing scale, recover the largest bounded
    # passing scale with six deterministic bisection probes.
    if failed_above is not None and failed_above > float(accepted["scale"]):
        lower = float(accepted["scale"])
        upper = failed_above
        for _iteration in range(6):
            middle = (lower + upper) * 0.5
            trial = evaluate(middle)
            trials.append(trial)
            if trial["passed"]:
                accepted = trial
                lower = middle
            else:
                upper = middle
    accepted = evaluate(float(accepted["scale"]))
    if not accepted["passed"]:
        raise RuntimeError("accepted fair-fit scale was not reproducible")

    selected_by_vertex = {
        record["support_vertex_index_before_final_reindex"]: record
        for record in hard_records
    }
    movement_records = []
    for vertex in vertices:
        displacement = body.matrix_world @ vertex.co - base_world[vertex]
        if displacement.length <= MOVEMENT_EPSILON_M:
            continue
        selected_record = selected_by_vertex.get(int(vertex.index))
        movement_records.append(
            {
                "vertex_index_before_final_reindex": int(vertex.index),
                "original_vertex_id": int(original_ids.get(vertex, -1)),
                "graph_ring": int(distances[vertex]),
                "boundary_vertex_ids": (
                    list(selected_record["boundary_vertex_ids"])
                    if selected_record is not None
                    else []
                ),
                "selected_hard_seam_support": selected_record is not None,
                "applied_world_vector_m": a08.vector_record(displacement),
                "applied_world_m": float(displacement.length),
            }
        )
    ring_distributions = {}
    for label, predicate in (
        ("ring_0", lambda distance: distance == 0),
        ("ring_1", lambda distance: distance == 1),
        ("ring_2", lambda distance: distance == 2),
        ("deep_interior", lambda distance: distance >= 3),
    ):
        ring_distributions[label] = displacement_distribution(
            [
                float((body.matrix_world @ vertex.co - base_world[vertex]).length)
                for vertex in vertices
                if predicate(int(distances[vertex]))
            ]
        )

    return {
        "method": "COUPLED_SCREENED_DISPLACEMENT_BIHARMONIC_V1",
        "absolute_position_minimal_surface_solve_used": False,
        "laplacian_shape": list(map(int, laplacian.shape)),
        "fidelity_weight": fidelity_weight,
        "differential_weight": differential_weight,
        "ring_1_soft_constraint_weight": 420.0,
        "ring_2_soft_constraint_weight": 147.0,
        "ring_2_relative_weight": 0.35,
        "hard_constraint_weight": 2.5e5,
        "boundary_constraint_weight": 1.0e9,
        "selected_hard_constraint_count": len(hard_targets),
        "selected_hard_constraints": hard_records,
        "constraint_records": constraint_records,
        "raw_solution_distribution": raw_distribution,
        "cap_prefactor": float(cap_scale),
        "backtracking_trials": trials,
        "accepted_trial": accepted,
        "movement_records": movement_records,
        "movement_distribution": accepted["distribution"],
        "ring_distributions": ring_distributions,
        "targeted_support_vertex_count": len(hard_targets),
        "all_other_fairing_displacement_zero": len(movement_records)
        == len(hard_targets),
        "maximum_support_movement_m": max(
            (
                float(record["applied_world_m"])
                for record in movement_records
                if record["selected_hard_seam_support"]
            ),
            default=0.0,
        ),
        "maximum_ring_2_applied_world_m": float(
            ring_distributions["ring_2"]["maximum_m"]
        ),
        "sharp_boundary_edges_cleared": False,
        "boundary_displacement_exact_zero": float(
            ring_distributions["ring_0"]["maximum_m"]
        )
        <= MOVEMENT_EPSILON_M,
        "caps_m": {
            "ring_1": RING_1_CAP_M,
            "ring_2": RING_2_CAP_M,
            "deep_interior": DEEP_INTERIOR_CAP_M,
            "overall": TOTAL_BASE_FIT_CAP_M,
            "p95": FIT_P95_CAP_M,
            "rms": FIT_RMS_CAP_M,
        },
    }


def refine_and_shape(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    preflight: Mapping[str, Any],
) -> dict[str, Any]:
    mesh_shading_before = a08.mesh_shading_state(body)
    boundary_corner_normals_before = a08.mesh_boundary_corner_normal_audit(
        body, preflight["patch_faces"], preflight["boundary_edges"]
    )
    bm = bmesh.new()
    try:
        bm.from_mesh(body.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        original_vertex_id = bm.verts.layers.int.new("__R24_A09_ORIGINAL_VERTEX_ID")
        original_face_id = bm.faces.layers.int.new("__R24_A09_ORIGINAL_FACE_ID")
        original_loop_id = bm.loops.layers.int.new("__R24_A09_ORIGINAL_LOOP_ID")
        feature_layer = bm.faces.layers.int.new("__R24_A09_FEATURE_CODE")
        for vertex in bm.verts:
            vertex[original_vertex_id] = int(vertex.index)
        loop_counter = 0
        for face in bm.faces:
            face[original_face_id] = int(face.index)
            face[feature_layer] = 0
            for loop in face.loops:
                loop[original_loop_id] = loop_counter
                loop_counter += 1

        group_names = {int(group.index): group.name for group in body.vertex_groups}
        frozen_before = a08.r23_author.bmesh_frozen_snapshot(
            bm,
            original_vertex_id,
            original_face_id,
            original_loop_id,
            set(map(int, preflight["interior_vertices"])),
            set(map(int, preflight["patch_faces"])),
            group_names,
        )
        original_vertices = set(bm.verts)
        original_faces = set(bm.faces)
        original_ids: dict[bmesh.types.BMVert, int] = {
            vertex: int(vertex.index) for vertex in bm.verts
        }
        patch_faces_before = {
            face
            for face in bm.faces
            if int(face[original_face_id]) in preflight["patch_faces"]
        }
        if len(patch_faces_before) != a08.EXPECTED_PATCH_FACES:
            raise RuntimeError("exact R19 source patch face count drifted before A09")
        if any(len(face.verts) != 3 for face in patch_faces_before):
            raise RuntimeError("A09 source patch is no longer triangular")

        uv_layers = {
            name: bm.loops.layers.uv.get(name) for name in bm.loops.layers.uv.keys()
        }
        source_records = []
        for face in sorted(
            patch_faces_before, key=lambda item: int(item[original_face_id])
        ):
            vertices = tuple(face.verts)
            ids = [int(original_ids[vertex]) for vertex in vertices]
            source_records.append(
                {
                    "source_face_id": int(face[original_face_id]),
                    "vertices": vertices,
                    "vertex_ids": ids,
                    "material_index": int(face.material_index),
                    "smooth": bool(face.smooth),
                    "uv_by_layer": {
                        name: {
                            int(original_ids[loop.vert]): (
                                float(loop[layer].uv.x),
                                float(loop[layer].uv.y),
                            )
                            for loop in face.loops
                        }
                        for name, layer in uv_layers.items()
                        if layer is not None
                    },
                }
            )

        original_patch_edges = {
            edge for face in patch_faces_before for edge in face.edges
        }
        internal_edges = {
            edge
            for edge in original_patch_edges
            if len(edge.link_faces) == 2
            and all(face in patch_faces_before for face in edge.link_faces)
        }
        source_boundary_edges = original_patch_edges.difference(internal_edges)
        if len(internal_edges) != EXPECTED_INTERNAL_EDGES:
            raise RuntimeError(
                f"expected {EXPECTED_INTERNAL_EDGES} original internal edges, "
                f"found {len(internal_edges)}"
            )
        if len(source_boundary_edges) != EXPECTED_BOUNDARY_EDGES:
            raise RuntimeError("A09 source boundary is not the exact 34-edge seam")

        deform = bm.verts.layers.deform.active
        if deform is None:
            raise RuntimeError("R19 primary surface lacks deform weights")
        rig_bones = {bone.name for bone in rig.data.bones}
        group_index_to_name = {
            int(group.index): group.name for group in body.vertex_groups
        }

        sorted_internal_edges = sorted(
            internal_edges,
            key=lambda edge: tuple(sorted(original_ids[vertex] for vertex in edge.verts)),
        )
        midpoint_by_edge: dict[tuple[int, int], bmesh.types.BMVert] = {}
        midpoint_endpoints: dict[bmesh.types.BMVert, tuple[int, int]] = {}
        midpoint_weight_records = []
        for rank, edge in enumerate(sorted_internal_edges):
            first, second = edge.verts
            endpoint_ids = tuple(sorted((original_ids[first], original_ids[second])))
            midpoint = bm.verts.new((first.co + second.co) * 0.5)
            midpoint[original_vertex_id] = -1
            original_ids[midpoint] = -(rank + 2)
            midpoint_by_edge[endpoint_ids] = midpoint
            midpoint_endpoints[midpoint] = endpoint_ids
            weights = interpolated_midpoint_weights(first, second, deform)
            midpoint[deform].clear()
            for group_index, weight in weights.items():
                group_name = group_index_to_name.get(group_index)
                if group_name is None or group_name not in rig_bones:
                    raise RuntimeError(
                        "A09 midpoint interpolation produced a non-native rig group"
                    )
                midpoint[deform][group_index] = float(weight)
            midpoint_weight_records.append(
                {
                    "source_edge_vertex_ids": list(endpoint_ids),
                    "canonical_midpoint_id": int(original_ids[midpoint]),
                    "native_group_count": len(weights),
                    "weight_sum": float(sum(weights.values())),
                }
            )
        bm.verts.index_update()
        bm.verts.ensure_lookup_table()

        # Preserve exact boundary edge objects.  Only the original patch faces
        # and now-loose original internal edges are removed.
        bmesh.ops.delete(
            bm,
            geom=sorted(patch_faces_before, key=lambda face: int(face.index)),
            context="FACES_ONLY",
        )
        for edge in sorted_internal_edges:
            if edge.is_valid:
                if edge.link_faces:
                    raise RuntimeError("original internal edge retained a linked face")
                bm.edges.remove(edge)

        new_faces: set[bmesh.types.BMFace] = set()
        refinement_records = []
        for record in source_records:
            templates, selection = face_refinement_templates(
                body, record, midpoint_by_edge, original_ids
            )
            child_indices = []
            for template in templates:
                child = bm.faces.new(template)
                child.material_index = int(record["material_index"])
                child.smooth = bool(record["smooth"])
                child[original_face_id] = -1
                child[feature_layer] = 0
                for loop in child.loops:
                    loop[original_loop_id] = -1
                    for name, layer in uv_layers.items():
                        if layer is None:
                            continue
                        source_uv = record["uv_by_layer"][name]
                        vertex = loop.vert
                        if vertex in midpoint_endpoints:
                            first_id, second_id = midpoint_endpoints[vertex]
                            value = midpoint_uv(source_uv, first_id, second_id)
                        else:
                            value = source_uv[int(original_ids[vertex])]
                        loop[layer].uv = value
                new_faces.add(child)
                child_indices.append(int(child.index))
            refinement_records.append(
                {
                    "source_face_id": int(record["source_face_id"]),
                    "child_face_count": len(templates),
                    **selection,
                }
            )

        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.verts.index_update()
        bm.edges.index_update()
        bm.faces.index_update()
        patch_faces = set(new_faces)
        patch_vertices = {vertex for face in patch_faces for vertex in face.verts}
        patch_edges = list({edge for face in patch_faces for edge in face.edges})
        seam_edges = {
            edge
            for edge in patch_edges
            if len(edge.link_faces) == 2
            and sum(face in patch_faces for face in edge.link_faces) == 1
        }
        seam_vertices = {vertex for edge in seam_edges for vertex in edge.verts}
        if len(patch_vertices) != EXPECTED_PATCH_VERTICES:
            raise RuntimeError(
                f"A09 refined patch vertex count {len(patch_vertices)} != "
                f"{EXPECTED_PATCH_VERTICES}"
            )
        if len(patch_faces) != EXPECTED_PATCH_FACES:
            raise RuntimeError(
                f"A09 refined patch face count {len(patch_faces)} != "
                f"{EXPECTED_PATCH_FACES}"
            )
        if len(patch_edges) != EXPECTED_PATCH_EDGES:
            raise RuntimeError(
                f"A09 refined patch edge count {len(patch_edges)} != "
                f"{EXPECTED_PATCH_EDGES}"
            )
        if (
            len(seam_edges) != EXPECTED_BOUNDARY_EDGES
            or len(seam_vertices) != EXPECTED_BOUNDARY_VERTICES
        ):
            raise RuntimeError("A09 midpoint refinement changed the exact boundary")
        if len(patch_vertices) - len(patch_edges) + len(patch_faces) != 1:
            raise RuntimeError("A09 refined patch Euler characteristic is not one")

        current_boundary_edges = {
            a08.edge_key(
                int(vertex[original_vertex_id]), int(other[original_vertex_id])
            )
            for edge in seam_edges
            for vertex, other in [(edge.verts[0], edge.verts[1])]
        }
        if current_boundary_edges != preflight["boundary_edges"]:
            raise RuntimeError("A09 changed an exact R19 boundary edge identity")

        bm.normal_update()
        base_world = {vertex: body.matrix_world @ vertex.co for vertex in patch_vertices}
        parameters, coordinate_evidence = a08.direct_source_3d_parameters(
            patch_vertices, base_world
        )
        distances = a08.graph_distance_from_seam(
            patch_vertices, patch_edges, seam_vertices
        )
        seam_shading_before = a08.seam_edge_records(
            body, patch_faces, seam_edges, original_ids, parameters
        )
        seam_before_values = [
            float(record["normal_dot"])
            for record in seam_shading_before["records"]
        ]
        fairing_evidence = solve_coupled_fair_fit(
            body,
            bm,
            patch_faces,
            patch_vertices,
            patch_edges,
            seam_edges,
            seam_vertices,
            distances,
            original_ids,
            parameters,
        )
        bm.normal_update()

        normal_matrix = body.matrix_world.to_3x3().inverted().transposed()
        world_to_local = body.matrix_world.inverted().to_3x3()
        interpolated_world_normals: dict[bmesh.types.BMVert, Vector] = {}
        for vertex in patch_vertices:
            normal = normal_matrix @ vertex.normal
            if normal.length <= 1.0e-12:
                raise RuntimeError("A09 refined patch contains a zero surface normal")
            normal.normalize()
            interpolated_world_normals[vertex] = normal
        smoothed_world_normals: dict[bmesh.types.BMVert, Vector] = {}
        for vertex in patch_vertices:
            adjacent = [
                edge.other_vert(vertex)
                for edge in vertex.link_edges
                if edge.other_vert(vertex) in patch_vertices
            ]
            reference = interpolated_world_normals[vertex]
            accumulated = reference * 2.0
            for neighbor in adjacent:
                candidate = interpolated_world_normals[neighbor].copy()
                if candidate.dot(reference) < 0.0:
                    candidate.negate()
                accumulated += candidate
            if accumulated.length <= 1.0e-12:
                accumulated = reference.copy()
            accumulated.normalize()
            smoothed_world_normals[vertex] = accumulated

        # This block is intentionally identical in formula and caps to A06/A08:
        # no anatomy relief amplitude or feature definition changes in A09.
        semantic: dict[str, set[bmesh.types.BMVert]] = defaultdict(set)
        displacements: dict[bmesh.types.BMVert, float] = {}
        for vertex in sorted(patch_vertices, key=lambda item: int(item.index)):
            u, t = parameters[vertex]
            offset, tags = a08.feature_offset_and_tags(u, t)
            distance = int(distances[vertex])
            seam_fade = a08.smoothstep((float(distance) - 1.0) / 2.5)
            lateral_fade = a08.smoothstep((1.0 - abs(u)) / 0.16)
            applied_offset = offset * seam_fade * lateral_fade
            if vertex in seam_vertices:
                applied_offset = 0.0
            vertex.co += world_to_local @ (
                smoothed_world_normals[vertex] * applied_offset
            )
            displacements[vertex] = float(applied_offset)
            for tag in tags:
                semantic[tag].add(vertex)

        a08.ensure_semantic_samples(semantic, parameters, distances)
        deoverlap_evidence = a08.enforce_opening_semantic_disjointness(
            semantic, parameters
        )
        vertex_tags: dict[bmesh.types.BMVert, set[str]] = defaultdict(set)
        for name, vertices in semantic.items():
            for vertex in vertices:
                vertex_tags[vertex].add(name)

        midpoint_weight_gate_records = []
        for midpoint in midpoint_endpoints:
            normalized = a08.normalized_top_four(midpoint[deform])
            midpoint[deform].clear()
            for group_index, weight in normalized.items():
                group_name = group_index_to_name.get(group_index)
                if group_name is None or group_name not in rig_bones:
                    raise RuntimeError("A09 midpoint retained a non-native rig weight")
                midpoint[deform][group_index] = float(weight)
            midpoint_weight_gate_records.append(
                {
                    "source_edge_vertex_ids": list(midpoint_endpoints[midpoint]),
                    "native_group_count": len(normalized),
                    "weight_sum": float(sum(normalized.values())),
                }
            )

        bm.normal_update()
        seam_shading_after = a08.seam_edge_records(
            body, patch_faces, seam_edges, original_ids, parameters
        )
        seam_after_values = [
            float(record["normal_dot"]) for record in seam_shading_after["records"]
        ]

        semantic_world = {}
        for name, vertices in semantic.items():
            if not vertices:
                continue
            centroid = sum(
                (body.matrix_world @ vertex.co for vertex in vertices), Vector()
            ) / len(vertices)
            average_normal = Vector()
            for vertex in vertices:
                normal = normal_matrix @ vertex.normal
                if normal.length > 1.0e-12:
                    normal.normalize()
                    average_normal += normal
            if average_normal.length > 1.0e-12:
                average_normal.normalize()
            semantic_world[name] = {
                "vertex_count": len(vertices),
                "centroid_world_m": a08.vector_record(centroid),
                "average_surface_normal_world": a08.vector_record(average_normal),
            }
        for face in patch_faces:
            face[feature_layer] = a08.feature_code_for_vertices(
                face.verts, vertex_tags
            )

        frozen_after = a08.r23_author.bmesh_frozen_snapshot(
            bm,
            original_vertex_id,
            original_face_id,
            original_loop_id,
            set(map(int, preflight["interior_vertices"])),
            set(map(int, preflight["patch_faces"])),
            group_names,
        )
        if frozen_before != frozen_after:
            raise RuntimeError("A09 changed out-of-patch R19 mesh/UV/weight state")

        boundary_positions_after = [
            a08.vector_record(
                body.matrix_world
                @ next(
                    vertex.co
                    for vertex in seam_vertices
                    if int(vertex[original_vertex_id]) == original_index
                )
            )
            for original_index in sorted(preflight["boundary_vertices"])
        ]
        boundary_position_sha256_after = a08.canonical_sha256(
            boundary_positions_after
        )
        if boundary_position_sha256_after != preflight["boundary_position_sha256"]:
            raise RuntimeError("A09 changed an exact R19 boundary vertex position")

        combined_movements = {
            vertex: float((body.matrix_world @ vertex.co - base_world[vertex]).length)
            for vertex in patch_vertices
        }
        combined_distribution = displacement_distribution(
            list(combined_movements.values())
        )
        maximum_relief = max(
            (abs(value) for value in displacements.values()), default=0.0
        )
        if maximum_relief > RELIEF_CAP_M + 1.0e-12:
            raise RuntimeError("unchanged A06 relief exceeded its exact 3mm cap")
        if float(combined_distribution["maximum_m"]) > COMBINED_CAP_M + 1.0e-8:
            raise RuntimeError("A09 combined base-fit and relief exceeded 4.5mm")

        bm.verts.index_update()
        bm.faces.index_update()
        semantic_global = {
            name: sorted(int(vertex.index) for vertex in vertices)
            for name, vertices in semantic.items()
        }
        t_global = {
            int(vertex.index): float(parameters[vertex][1])
            for vertex in patch_vertices
        }
        patch_face_indices = sorted(int(face.index) for face in patch_faces)
        feature_faces: dict[str, list[int]] = defaultdict(list)
        for face in patch_faces:
            feature_faces[str(int(face[feature_layer]))].append(int(face.index))

        displacement_hash = a08.canonical_sha256(
            sorted(
                [int(vertex.index), round(float(value), 12)]
                for vertex, value in displacements.items()
            )
        )
        patch_baseline_hash = a08.canonical_sha256(
            sorted(
                [int(vertex.index), *a08.vector_record(base_world[vertex])]
                for vertex in patch_vertices
            )
        )
        face_split_histogram = {
            str(split_count): sum(
                1
                for record in refinement_records
                if int(record["split_internal_edge_count"]) == split_count
            )
            for split_count in range(4)
        }
        tie_break_count = sum(
            1
            for record in refinement_records
            if record.get("selection_reason") == "canonical_vertex_id_tie_break"
        )

        bm.verts.layers.int.remove(original_vertex_id)
        bm.faces.layers.int.remove(original_face_id)
        bm.faces.layers.int.remove(feature_layer)
        bm.loops.layers.int.remove(original_loop_id)
        bm.to_mesh(body.data)
    finally:
        bm.free()

    body.data.update(calc_edges=True, calc_edges_loose=True)
    mesh_shading_after = a08.mesh_shading_state(body)
    boundary_corner_normals_after = a08.mesh_boundary_corner_normal_audit(
        body, patch_face_indices, current_boundary_edges
    )
    return {
        "frozen_surviving_sha256_before": frozen_before,
        "frozen_surviving_sha256_after": frozen_after,
        "frozen_surviving_exact": frozen_before == frozen_after,
        "boundary_position_sha256_before": preflight["boundary_position_sha256"],
        "boundary_position_sha256_after": boundary_position_sha256_after,
        "boundary_position_exact": boundary_position_sha256_after
        == preflight["boundary_position_sha256"],
        "boundary_edge_sha256_before": preflight["boundary_edge_sha256"],
        "boundary_edge_sha256_after": a08.canonical_sha256(
            [list(edge) for edge in sorted(current_boundary_edges)]
        ),
        "boundary_edges_exact": current_boundary_edges == preflight["boundary_edges"],
        "original_vertex_count": len(original_vertices),
        "original_face_count": len(original_faces),
        "new_vertex_count": len(midpoint_endpoints),
        "internal_edge_midpoint_count": len(midpoint_endpoints),
        "patch_face_indices": patch_face_indices,
        "feature_faces": {
            key: sorted(value) for key, value in feature_faces.items()
        },
        "semantic_global": semantic_global,
        "semantic_world": semantic_world,
        "t_global": t_global,
        "seam_dot_before": seam_before_values,
        "seam_dot_after": seam_after_values,
        "seam_shading_audit": {
            "mesh_before": mesh_shading_before,
            "mesh_after_exact_boundary_custom_clear": mesh_shading_before,
            "mesh_after": mesh_shading_after,
            "boundary_corner_normals_before": boundary_corner_normals_before,
            "boundary_corner_normals_after_custom_clear": boundary_corner_normals_before,
            "boundary_corner_normals_after": boundary_corner_normals_after,
            "boundary_before": seam_shading_before,
            "boundary_after": seam_shading_after,
            "custom_boundary_normal_change": {
                "applied": False,
                "reason": "A09 changes no custom normals",
                "changes": [],
            },
            "custom_boundary_normal_change_applied": False,
            "face_smooth_change_applied": False,
            "boundary_sharpness_change_applied": False,
        },
        "maximum_absolute_offset_m": maximum_relief,
        "seam_support_fairing": fairing_evidence,
        "base_fit": fairing_evidence,
        "combined_displacement": combined_distribution,
        "opening_semantic_deoverlap": deoverlap_evidence,
        "displacement_sha256": displacement_hash,
        "patch_baseline_world_position_sha256": patch_baseline_hash,
        "topology_refinement": {
            "method": "ONE_MIDPOINT_PER_ORIGINAL_PATCH_INTERNAL_EDGE",
            "source_patch_vertex_count": a08.EXPECTED_PATCH_VERTICES,
            "source_patch_face_count": a08.EXPECTED_PATCH_FACES,
            "source_internal_edge_count": len(internal_edges),
            "source_boundary_edge_count": len(source_boundary_edges),
            "created_midpoint_count": len(midpoint_endpoints),
            "result_patch_vertex_count": EXPECTED_PATCH_VERTICES,
            "result_patch_face_count": EXPECTED_PATCH_FACES,
            "result_patch_edge_count": EXPECTED_PATCH_EDGES,
            "result_boundary_edge_count": len(seam_edges),
            "result_euler_characteristic": 1,
            "face_split_histogram": face_split_histogram,
            "canonical_tie_break_count": tie_break_count,
            "source_face_records": refinement_records,
            "midpoint_weight_interpolation": midpoint_weight_records,
            "midpoint_weight_gate_records": midpoint_weight_gate_records,
            "midpoint_world_position": "exact arithmetic mean of original source-edge endpoints",
            "boundary_edges_split": False,
            "uv_interpolation": "per-source-face endpoint midpoint for every native UV layer",
            "material_and_smooth_inheritance": "exact source-face values",
        },
        "anatomical_frame": {
            "coordinate_evidence": coordinate_evidence,
            "u_definition": "normalized existing source-bound lateral chart coordinate",
            "t_definition": "nearest exact-source 13-control 3D centerline arc-length coordinate",
            "offset_direction": "per-vertex interpolated and one-ring-smoothed local surface normal",
            "surface_position_remap_used": False,
        },
    }


def topology_and_semantic_gates(
    body: bpy.types.Object,
    applied: Mapping[str, Any],
) -> dict[str, Any]:
    result = a08.topology_and_semantic_gates(body, applied)
    checks = dict(result["checks"])
    for obsolete in (
        "maximum_patch_edge_ratio_not_above_attempt06",
        "targeted_four_support_edges_exact",
        "targeted_support_count_exactly_four",
        "all_other_fairing_displacement_zero",
        "all_four_targeted_seam_dots_at_least_0_715",
        "untargeted_seam_dots_not_regressed",
        "maximum_targeted_support_fairing_at_most_1_25mm",
        "second_ring_fairing_exactly_zero",
    ):
        checks.pop(obsolete, None)

    faces = a08.faces_of(body)
    patch_faces = set(map(int, applied["patch_face_indices"]))
    patch_vertices = {
        int(vertex) for face_index in patch_faces for vertex in faces[face_index]
    }
    patch_edges = {
        edge
        for face_index in patch_faces
        for edge in a08.topology_core.face_edges(faces[face_index])
    }
    refinement = applied["topology_refinement"]
    weights = refinement["midpoint_weight_gate_records"]
    base_fit = applied["base_fit"]
    base_distribution = base_fit["movement_distribution"]
    rings = base_fit["ring_distributions"]
    combined = applied["combined_displacement"]
    accepted = base_fit["accepted_trial"]
    checks.update(
        {
            "refined_patch_vertex_count_exact_753": len(patch_vertices)
            == EXPECTED_PATCH_VERTICES,
            "refined_patch_face_count_exact_1470": len(patch_faces)
            == EXPECTED_PATCH_FACES,
            "refined_patch_edge_count_exact_2222": len(patch_edges)
            == EXPECTED_PATCH_EDGES,
            "internal_midpoint_count_exact_547": refinement[
                "created_midpoint_count"
            ]
            == EXPECTED_INTERNAL_EDGES,
            "exact_boundary_not_split": refinement["boundary_edges_split"] is False,
            "refined_patch_euler_characteristic_one": refinement[
                "result_euler_characteristic"
            ]
            == 1,
            "all_midpoint_weights_native_top4_normalized": len(weights)
            == EXPECTED_INTERNAL_EDGES
            and all(
                1 <= int(record["native_group_count"]) <= 4
                and abs(float(record["weight_sum"]) - 1.0) <= 1.0e-6
                for record in weights
            ),
            "coupled_fair_fit_accepted": accepted["passed"] is True,
            "coupled_fair_fit_no_face_flip": accepted["shape"][
                "orientations_preserved"
            ]
            is True,
            "base_fit_boundary_exact_zero": base_fit[
                "boundary_displacement_exact_zero"
            ]
            is True,
            "base_fit_ring1_at_most_1_50mm": float(
                rings["ring_1"]["maximum_m"]
            )
            <= RING_1_CAP_M + MOVEMENT_EPSILON_M,
            "base_fit_ring2_at_most_0_90mm": float(
                rings["ring_2"]["maximum_m"]
            )
            <= RING_2_CAP_M + MOVEMENT_EPSILON_M,
            "base_fit_deep_at_most_0_60mm": float(
                rings["deep_interior"]["maximum_m"]
            )
            <= DEEP_INTERIOR_CAP_M + MOVEMENT_EPSILON_M,
            "base_fit_overall_at_most_1_50mm": float(
                base_distribution["maximum_m"]
            )
            <= TOTAL_BASE_FIT_CAP_M + MOVEMENT_EPSILON_M,
            "base_fit_p95_at_most_0_90mm": float(base_distribution["p95_m"])
            <= FIT_P95_CAP_M + MOVEMENT_EPSILON_M,
            "base_fit_rms_at_most_0_45mm": float(base_distribution["rms_m"])
            <= FIT_RMS_CAP_M + MOVEMENT_EPSILON_M,
            "unchanged_a06_relief_at_most_3mm": float(
                applied["maximum_absolute_offset_m"]
            )
            <= RELIEF_CAP_M + 1.0e-12,
            "combined_base_fit_and_relief_at_most_4_5mm": float(
                combined["maximum_m"]
            )
            <= COMBINED_CAP_M + MOVEMENT_EPSILON_M,
            "absolute_position_minimal_surface_solve_not_used": base_fit[
                "absolute_position_minimal_surface_solve_used"
            ]
            is False,
        }
    )
    result["checks"] = checks
    result["passed"] = all(checks.values())
    result["a09_refinement"] = {
        "patch_vertex_count": len(patch_vertices),
        "patch_face_count": len(patch_faces),
        "patch_edge_count": len(patch_edges),
        "internal_midpoint_count": refinement["created_midpoint_count"],
        "combined_displacement": combined,
        "base_fit_displacement": base_distribution,
    }
    return result


def render_uniform_clay_pairs_without_subdivision(
    directory: Path,
    applied: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Pair three protected views with Catmull-Clark disabled temporarily."""
    scene = bpy.context.scene
    clinical = bpy.data.objects.get("R24_FeatureAligned_ClinicalDiagnostic")
    camera = bpy.data.objects.get("R24_FeatureAligned_Camera")
    if clinical is None or camera is None:
        raise RuntimeError("A09 paired diagnostic objects are missing")
    modifier = clinical.modifiers.get("R24_ClinicalSubdivision")
    if modifier is None:
        raise RuntimeError("A09 clinical diagnostic subdivision modifier is missing")
    patch_indices = sorted(
        {
            int(vertex)
            for face_index in applied["patch_face_indices"]
            for vertex in clinical.data.polygons[int(face_index)].vertices
        }
    )
    pelvis = sum(
        (
            clinical.matrix_world @ clinical.data.vertices[index].co
            for index in patch_indices
        ),
        Vector(),
    ) / len(patch_indices)
    views = {
        "protected_clinical_front_no_diagnostic_subdivision.png": (
            Vector((pelvis.x, pelvis.y - 1.6, pelvis.z)),
            pelvis,
            0.34,
            "protected_clinical_front.png",
        ),
        "protected_clinical_left_three_quarter_no_diagnostic_subdivision.png": (
            Vector((pelvis.x - 0.88, pelvis.y - 1.28, pelvis.z)),
            pelvis,
            0.34,
            "protected_clinical_left_three_quarter.png",
        ),
        "protected_clinical_inferior_no_diagnostic_subdivision.png": (
            Vector((pelvis.x, pelvis.y - 0.72, pelvis.z - 0.72)),
            pelvis,
            0.32,
            "protected_clinical_inferior.png",
        ),
    }
    prior_scene_camera = scene.camera
    prior_filepath = scene.render.filepath
    prior_clinical_hidden = bool(clinical.hide_render)
    prior_show_render = bool(modifier.show_render)
    prior_show_viewport = bool(modifier.show_viewport)
    visibility = {
        obj.name: bool(obj.hide_render)
        for obj in scene.objects
        if obj is not clinical and obj.type == "MESH"
    }
    records = []
    try:
        for obj in scene.objects:
            if obj is not clinical and obj.type == "MESH":
                obj.hide_render = True
        clinical.hide_render = False
        modifier.show_render = False
        modifier.show_viewport = False
        scene.camera = camera
        for filename, (location, target, scale, paired_with) in views.items():
            camera.location = location
            camera.data.ortho_scale = scale
            a08.r24_base.look_at(camera, target)
            scene.render.filepath = str(directory / filename)
            bpy.ops.render.render(write_still=True)
            path = directory / filename
            records.append(
                {
                    "filename": filename,
                    "path": relative(path),
                    "sha256": sha256(path),
                    "paired_subdivided_view": paired_with,
                    "uniform_clay_retained": True,
                    "clinical_subdivision_disabled_for_this_render_only": True,
                    "camera_light_material_match": True,
                }
            )
    finally:
        clinical.hide_render = prior_clinical_hidden
        modifier.show_render = prior_show_render
        modifier.show_viewport = prior_show_viewport
        scene.camera = prior_scene_camera
        scene.render.filepath = prior_filepath
        for name, hidden in visibility.items():
            obj = bpy.data.objects.get(name)
            if obj is not None:
                obj.hide_render = hidden
    return records


def main() -> None:
    global ACTIVE_OUTPUT
    worker = Path(__file__).resolve()
    bound_r19 = a08.BOUND_R19_EVIDENCE
    if sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("immutable R19 source hash drifted")
    for path, expected, label in (
        (A08_WORKER, A08_WORKER_SHA256, "preserved A08 worker"),
        (A08_REPORT, A08_REPORT_SHA256, "preserved A08 report"),
        (A06_REPORT, A06_REPORT_SHA256, "preserved A06 report"),
        (bound_r19, a08.BOUND_R19_EVIDENCE_SHA256, "bound R19 evidence"),
    ):
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"{label} hash drifted")

    ACTIVE_OUTPUT = allocate_output()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    body = bpy.data.objects.get(BODY_NAME)
    rig = bpy.data.objects.get(RIG_NAME)
    if body is None or rig is None:
        raise RuntimeError("exact R19 body or native rig is absent")
    a08.r24_base.clear_pose(rig)
    source_shape_key_count = (
        len(body.data.shape_keys.key_blocks) if body.data.shape_keys else 0
    )
    preflight = a08.original_patch_preflight(body)
    applied = refine_and_shape(body, rig, preflight)
    gates = topology_and_semantic_gates(body, applied)
    render_directory = ACTIVE_OUTPUT / "private_owner_review"
    renders = a08.r24_render.render_evidence(body, applied, render_directory)
    paired_no_subdivision = render_uniform_clay_pairs_without_subdivision(
        render_directory, applied
    )
    renders["rendered"].extend(
        record["filename"] for record in paired_no_subdivision
    )
    renders["paired_subdivision_diagnostics"] = paired_no_subdivision

    report = {
        "schema": "kira.avatar.r24_internal_midpoint_fair_surface_simulation.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "NO_SAVE_STRUCTURAL_GATES_PASS_VISUAL_OWNER_REVIEW_REQUIRED"
            if gates["passed"]
            else "NO_SAVE_STRUCTURAL_OR_SEMANTIC_GATE_FAILURE_RETAINED_FOR_DIAGNOSIS"
        ),
        "source": {
            "path": relative(SOURCE),
            "bytes": SOURCE.stat().st_size,
            "sha256": sha256(SOURCE),
            "unchanged": sha256(SOURCE) == SOURCE_SHA256,
            "body": BODY_NAME,
            "rig": RIG_NAME,
            "source_shape_key_count": source_shape_key_count,
        },
        "worker": {
            "path": relative(worker),
            "bytes": worker.stat().st_size,
            "sha256": sha256(worker),
        },
        "preserved_evidence": {
            "attempt_08_worker": {
                "path": relative(A08_WORKER),
                "sha256": A08_WORKER_SHA256,
                "unchanged": sha256(A08_WORKER) == A08_WORKER_SHA256,
            },
            "attempt_08_report": {
                "path": relative(A08_REPORT),
                "sha256": A08_REPORT_SHA256,
            },
            "attempt_06_report": {
                "path": relative(A06_REPORT),
                "sha256": A06_REPORT_SHA256,
                "anatomical_relief_reused_unchanged": True,
            },
            "bound_r19_evidence": {
                "path": relative(bound_r19),
                "sha256": a08.BOUND_R19_EVIDENCE_SHA256,
            },
        },
        "method": {
            "id": "R19_INTERNAL_EDGE_MIDPOINT_REFINEMENT_COUPLED_SCREENED_FAIR_FIT_V1",
            "new_body_created": False,
            "source_body_saved": False,
            "one_midpoint_per_original_patch_internal_edge": True,
            "original_boundary_edges_split": False,
            "deterministic_two_split_diagonal": "maximum minimum world-space triangle angle; canonical ID tie-break",
            "deform_weights": "50/50 endpoint interpolation, normalized native top four",
            "uvs": "per-source-face endpoint midpoint interpolation",
            "material_and_smooth": "source-face inheritance",
            "coupled_screened_displacement_biharmonic": True,
            "independent_per_edge_projection": False,
            "absolute_minimal_surface_solve": False,
            "boundary_displacement": "exact zero",
            "outside_plane_soft_constraints": {
                "ring_1_relative_weight": 1.0,
                "ring_2_relative_weight": 0.35,
                "deeper_direct_target": False,
            },
            "unchanged_a06_anatomical_relief": True,
            "shading_material_or_custom_normal_change": False,
            "paired_catmull_clark_diagnostics": [
                "front",
                "left_three_quarter",
                "inferior",
            ],
        },
        "preflight": {
            "patch_face_count": len(preflight["patch_faces"]),
            "patch_vertex_count": len(preflight["patch_vertices"]),
            "interior_vertex_count": len(preflight["interior_vertices"]),
            "boundary_vertex_count": len(preflight["boundary_vertices"]),
            "boundary_edge_count": len(preflight["boundary_edges"]),
            "boundary_position_sha256": preflight["boundary_position_sha256"],
            "boundary_edge_sha256": preflight["boundary_edge_sha256"],
            "topology": preflight["topology"],
        },
        "application": applied,
        "gates": gates,
        "renders": renders,
        "operations": {
            "blend_saved": False,
            "source_overwritten": False,
            "runtime_or_person_state_changed": False,
            "voice_model_device_files_touched": False,
            "activation_assignment_export_publication": False,
        },
        "truth": (
            "External private visual/topology simulation only. No internal tract, "
            "physiology, elimination, reproduction, pregnancy, sensation, subjective "
            "state, owner approval, runtime readiness, or biological function is "
            "implemented or claimed."
        ),
    }
    report_path = ACTIVE_OUTPUT / "SIMULATION_REPORT.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(ACTIVE_OUTPUT)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback

        trace = traceback.format_exc()
        if ACTIVE_OUTPUT is not None:
            failure = {
                "schema": "kira.avatar.r24_internal_midpoint_fair_surface_failure.v1",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "status": "NO_SAVE_FAILURE_PRESERVED",
                "exception_type": type(exc).__name__,
                "exception": str(exc),
                "traceback": trace,
                "source": {
                    "path": relative(SOURCE),
                    "sha256": sha256(SOURCE) if SOURCE.is_file() else None,
                },
                "operations": {
                    "blend_saved": False,
                    "source_overwritten": False,
                    "runtime_or_person_state_changed": False,
                },
            }
            (ACTIVE_OUTPUT / "FAILURE.json").write_text(
                json.dumps(failure, indent=2) + "\n", encoding="utf-8"
            )
        print(trace, file=sys.stderr)
        raise
