"""Exact narrow-phase classification for Blender mesh self-intersections.

``BVHTree.overlap`` is used only as a broad phase.  Each non-topologically-
adjacent face candidate is covered by both Blender's geometry tessellation and
the deterministic polygon-fan tessellation used by the independent artifact
auditor, then classified with explicit triangle plane/interval tests (or a 2-D
convex clip for coplanar triangles).  Covering both diagonals of non-planar
quads avoids a triangulation-dependent false pass.  Touches and AABB-only
candidates remain separate from genuine crossing segments and positive-area
coplanar overlaps.

The module is read-only with respect to Blender data.
"""

from __future__ import annotations

from collections import deque
import math
from typing import Any, Iterable, Sequence

import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon


def _vector_record(value: Vector) -> list[float]:
    return [round(float(component), 9) for component in value]


def _bounds(points: Iterable[Vector]) -> dict[str, list[float]]:
    values = list(points)
    return {
        "min": [
            round(min(float(point[axis]) for point in values), 9)
            for axis in range(3)
        ],
        "max": [
            round(max(float(point[axis]) for point in values), 9)
            for axis in range(3)
        ],
    }


def _unique_points(points: Iterable[Vector], tolerance: float) -> list[Vector]:
    unique: list[Vector] = []
    for point in points:
        if all((point - existing).length > tolerance for existing in unique):
            unique.append(point)
    return unique


def _triangle_plane_intersection_points(
    triangle: Sequence[Vector],
    distances: Sequence[float],
    tolerance: float,
) -> list[Vector]:
    points: list[Vector] = [
        triangle[index].copy()
        for index, distance in enumerate(distances)
        if abs(float(distance)) <= tolerance
    ]
    for index in range(3):
        next_index = (index + 1) % 3
        first_distance = float(distances[index])
        second_distance = float(distances[next_index])
        if (
            first_distance < -tolerance
            and second_distance > tolerance
        ) or (
            first_distance > tolerance
            and second_distance < -tolerance
        ):
            alpha = first_distance / (first_distance - second_distance)
            points.append(
                triangle[index].lerp(triangle[next_index], float(alpha))
            )
    return _unique_points(points, tolerance)


def _project_2d(point: Vector, dropped_axis: int) -> tuple[float, float]:
    axes = [axis for axis in range(3) if axis != dropped_axis]
    return float(point[axes[0]]), float(point[axes[1]])


def _cross_2d(
    first: tuple[float, float],
    second: tuple[float, float],
    third: tuple[float, float],
) -> float:
    return (
        (second[0] - first[0]) * (third[1] - first[1])
        - (second[1] - first[1]) * (third[0] - first[0])
    )


def _polygon_area_2d(points: Sequence[tuple[float, float]]) -> float:
    return abs(
        sum(
            first[0] * second[1] - second[0] * first[1]
            for first, second in zip(points, points[1:] + points[:1])
        )
    ) * 0.5 if len(points) >= 3 else 0.0


def _line_intersection_2d(
    segment_start: tuple[float, float],
    segment_end: tuple[float, float],
    clip_start: tuple[float, float],
    clip_end: tuple[float, float],
    tolerance: float,
) -> tuple[float, float]:
    segment_x = segment_end[0] - segment_start[0]
    segment_y = segment_end[1] - segment_start[1]
    clip_x = clip_end[0] - clip_start[0]
    clip_y = clip_end[1] - clip_start[1]
    denominator = segment_x * clip_y - segment_y * clip_x
    if abs(denominator) <= tolerance:
        return segment_end
    offset_x = clip_start[0] - segment_start[0]
    offset_y = clip_start[1] - segment_start[1]
    alpha = (offset_x * clip_y - offset_y * clip_x) / denominator
    return (
        segment_start[0] + alpha * segment_x,
        segment_start[1] + alpha * segment_y,
    )


def _clip_triangle_2d(
    subject: Sequence[tuple[float, float]],
    clip: Sequence[tuple[float, float]],
    tolerance: float,
) -> list[tuple[float, float]]:
    output = list(subject)
    orientation = 1.0 if _cross_2d(clip[0], clip[1], clip[2]) >= 0.0 else -1.0
    for clip_start, clip_end in zip(clip, clip[1:] + clip[:1]):
        input_points = output
        output = []
        if not input_points:
            break
        previous = input_points[-1]
        previous_inside = (
            orientation * _cross_2d(clip_start, clip_end, previous)
            >= -tolerance
        )
        for current in input_points:
            current_inside = (
                orientation * _cross_2d(clip_start, clip_end, current)
                >= -tolerance
            )
            if current_inside != previous_inside:
                output.append(
                    _line_intersection_2d(
                        previous,
                        current,
                        clip_start,
                        clip_end,
                        tolerance,
                    )
                )
            if current_inside:
                output.append(current)
            previous = current
            previous_inside = current_inside
    return output


def classify_triangle_pair(
    first: Sequence[Vector],
    second: Sequence[Vector],
    *,
    linear_tolerance: float,
) -> dict[str, Any]:
    """Classify one triangle pair after a BVH broad-phase hit."""

    first_normal_raw = (first[1] - first[0]).cross(first[2] - first[0])
    second_normal_raw = (second[1] - second[0]).cross(second[2] - second[0])
    first_area = first_normal_raw.length * 0.5
    second_area = second_normal_raw.length * 0.5
    area_tolerance = linear_tolerance * linear_tolerance * 16.0
    if first_area <= area_tolerance or second_area <= area_tolerance:
        return {
            "classification": "degenerate_triangle",
            "genuine_penetration": False,
        }
    first_normal = first_normal_raw.normalized()
    second_normal = second_normal_raw.normalized()
    first_distances = [
        first_normal.dot(point - first[0]) for point in second
    ]
    second_distances = [
        second_normal.dot(point - second[0]) for point in first
    ]
    if (
        min(first_distances) > linear_tolerance
        or max(first_distances) < -linear_tolerance
        or min(second_distances) > linear_tolerance
        or max(second_distances) < -linear_tolerance
    ):
        return {
            "classification": "bvh_aabb_only",
            "genuine_penetration": False,
        }

    line_direction = first_normal.cross(second_normal)
    if line_direction.length <= linear_tolerance:
        plane_separation = max(abs(value) for value in first_distances)
        if plane_separation > linear_tolerance:
            return {
                "classification": "parallel_bvh_aabb_only",
                "genuine_penetration": False,
                "plane_separation_m": float(plane_separation),
            }
        dropped_axis = max(
            range(3),
            key=lambda axis: abs(float(first_normal[axis])),
        )
        first_2d = [_project_2d(point, dropped_axis) for point in first]
        second_2d = [_project_2d(point, dropped_axis) for point in second]
        clipped = _clip_triangle_2d(
            first_2d,
            second_2d,
            linear_tolerance,
        )
        projected_area = _polygon_area_2d(clipped)
        normal_component = abs(float(first_normal[dropped_axis]))
        surface_area = (
            projected_area / normal_component
            if normal_component > linear_tolerance
            else 0.0
        )
        if surface_area > area_tolerance:
            return {
                "classification": "coplanar_positive_area_overlap",
                "genuine_penetration": True,
                "coplanar_overlap_area_m2": float(surface_area),
            }
        return {
            "classification": "coplanar_touch_or_numerical_contact",
            "genuine_penetration": False,
            "coplanar_overlap_area_m2": float(surface_area),
        }

    direction = line_direction.normalized()
    first_points = _triangle_plane_intersection_points(
        first,
        second_distances,
        linear_tolerance,
    )
    second_points = _triangle_plane_intersection_points(
        second,
        first_distances,
        linear_tolerance,
    )
    if not first_points or not second_points:
        return {
            "classification": "bvh_aabb_only",
            "genuine_penetration": False,
        }
    first_interval = [direction.dot(point) for point in first_points]
    second_interval = [direction.dot(point) for point in second_points]
    overlap_min = max(min(first_interval), min(second_interval))
    overlap_max = min(max(first_interval), max(second_interval))
    overlap_length = float(overlap_max - overlap_min)
    if overlap_length > linear_tolerance:
        return {
            "classification": "noncoplanar_crossing_segment",
            "genuine_penetration": True,
            "intersection_segment_length_m": overlap_length,
        }
    if overlap_length >= -linear_tolerance:
        return {
            "classification": "noncoplanar_point_or_edge_touch",
            "genuine_penetration": False,
            "intersection_segment_length_m": max(0.0, overlap_length),
        }
    return {
        "classification": "bvh_aabb_only",
        "genuine_penetration": False,
        "interval_separation_m": -overlap_length,
    }


def _face_triangle_vertex_indices(
    face: bmesh.types.BMFace,
) -> list[tuple[int, int, int]]:
    vertices = list(face.verts)
    polygon = [vert.co.copy() for vert in vertices]
    tessellated = tessellate_polygon([polygon])
    triangles: set[tuple[int, int, int]] = set()
    for triangle in tessellated:
        if triangle and isinstance(triangle[0], int):
            local_indices = tuple(int(index) for index in triangle)
        else:
            local_indices = tuple(
                min(
                    range(len(polygon)),
                    key=lambda index: (
                        polygon[index] - point
                    ).length_squared,
                )
                for point in triangle
            )
        triangles.add(
            tuple(int(vertices[index].index) for index in local_indices)
        )
    # The independent exact-artifact auditor intentionally uses a stable fan.
    # Include it as a second coverage path because a non-planar polygon has no
    # unique continuous surface until its diagonal is made explicit.
    for offset in range(1, len(vertices) - 1):
        triangles.add(
            (
                int(vertices[0].index),
                int(vertices[offset].index),
                int(vertices[offset + 1].index),
            )
        )
    return sorted(triangles)


def _triangulated_bvh_candidates(
    bm: bmesh.types.BMesh,
) -> tuple[
    list[Vector],
    list[tuple[int, int, int]],
    list[int],
    dict[tuple[int, int], list[tuple[int, int]]],
]:
    points = [vert.co.copy() for vert in bm.verts]
    triangles: list[tuple[int, int, int]] = []
    source_faces: list[int] = []
    for face in bm.faces:
        face_triangles = _face_triangle_vertex_indices(face)
        triangles.extend(face_triangles)
        source_faces.extend([int(face.index)] * len(face_triangles))
    tree = BVHTree.FromPolygons(points, triangles, all_triangles=True, epsilon=0.0)
    grouped: dict[tuple[int, int], list[tuple[int, int]]] = {}
    triangle_vertex_sets = [set(triangle) for triangle in triangles]
    source_face_vertex_sets = [
        {int(vert.index) for vert in face.verts}
        for face in bm.faces
    ]
    for raw_first, raw_second in tree.overlap(tree):
        if raw_first == raw_second:
            continue
        first, second = (
            (raw_first, raw_second)
            if raw_first < raw_second
            else (raw_second, raw_first)
        )
        if triangle_vertex_sets[first].intersection(triangle_vertex_sets[second]):
            continue
        first_face = source_faces[first]
        second_face = source_faces[second]
        if first_face == second_face:
            continue
        # Nonadjacency belongs to the original source faces, not merely to a
        # particular pair of triangles produced while tessellating them.  Two
        # source faces that share any original vertex (and therefore also any
        # original edge) are topology-adjacent even when the overlapping
        # tessellation triangles happen to use disjoint triangle vertices.
        if source_face_vertex_sets[first_face].intersection(
            source_face_vertex_sets[second_face]
        ):
            continue
        face_pair = (
            (first_face, second_face)
            if first_face < second_face
            else (second_face, first_face)
        )
        grouped.setdefault(face_pair, []).append((first, second))
    for pair in grouped:
        grouped[pair] = sorted(set(grouped[pair]))
    return points, triangles, source_faces, grouped


def _face_adjacency(bm: bmesh.types.BMesh) -> list[set[int]]:
    adjacency = [set() for _face in bm.faces]
    for edge in bm.edges:
        linked = [int(face.index) for face in edge.link_faces]
        for first in linked:
            adjacency[first].update(second for second in linked if second != first)
    return adjacency


def _topology_distance(
    adjacency: Sequence[set[int]],
    start: int,
    target: int,
) -> int | None:
    todo = deque([(start, 0)])
    seen = {start}
    while todo:
        current, distance = todo.popleft()
        if current == target:
            return distance
        for neighbor in adjacency[current]:
            if neighbor not in seen:
                seen.add(neighbor)
                todo.append((neighbor, distance + 1))
    return None


def _body_region(
    center: Vector,
    mesh_min: Vector,
    mesh_max: Vector,
) -> str:
    height = max(float(mesh_max.z - mesh_min.z), 1.0e-12)
    fraction = float((center.z - mesh_min.z) / height)
    if fraction >= 0.84:
        return "head_face"
    if fraction >= 0.58:
        return "torso_upper_limbs"
    if fraction >= 0.40:
        return "pelvis_upper_legs"
    if fraction >= 0.12:
        return "lower_legs"
    return "feet_floor"


def bvh_nonadjacent_face_pairs(
    bm: bmesh.types.BMesh,
) -> set[tuple[int, int]]:
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.faces.index_update()
    _points, _triangles, _source_faces, grouped = (
        _triangulated_bvh_candidates(bm)
    )
    return set(grouped)


def exact_nonadjacent_intersection_report(
    bm: bmesh.types.BMesh,
    *,
    include_pair_details: bool = True,
) -> dict[str, Any]:
    """Return broad candidates and exact, topology-aware classifications."""

    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.faces.index_update()
    bm.normal_update()
    all_points = [vert.co for vert in bm.verts]
    mesh_min = Vector(
        tuple(min(float(point[axis]) for point in all_points) for axis in range(3))
    )
    mesh_max = Vector(
        tuple(max(float(point[axis]) for point in all_points) for axis in range(3))
    )
    diagonal = (mesh_max - mesh_min).length
    tolerance = max(1.0e-10, float(diagonal) * 1.0e-8)
    points, triangles, _source_faces, grouped_candidates = (
        _triangulated_bvh_candidates(bm)
    )
    broad_pairs = sorted(grouped_candidates)
    adjacency = _face_adjacency(bm)
    records: list[dict[str, Any]] = []
    for first_index, second_index in broad_pairs:
        first_face = bm.faces[first_index]
        second_face = bm.faces[second_index]
        triangle_results: list[dict[str, Any]] = []
        for first_triangle_index, second_triangle_index in grouped_candidates[
            (first_index, second_index)
        ]:
            first_triangle = tuple(
                points[index] for index in triangles[first_triangle_index]
            )
            second_triangle = tuple(
                points[index] for index in triangles[second_triangle_index]
            )
            result = classify_triangle_pair(
                first_triangle,
                second_triangle,
                linear_tolerance=tolerance,
            )
            result["triangle_indices"] = [
                first_triangle_index,
                second_triangle_index,
            ]
            if result["classification"] != "bvh_aabb_only":
                triangle_results.append(result)
        genuine = [
            result
            for result in triangle_results
            if result.get("genuine_penetration") is True
        ]
        touches = [
            result
            for result in triangle_results
            if result.get("genuine_penetration") is not True
        ]
        if genuine:
            character = "genuine_penetration"
        elif touches:
            character = "touch_or_coplanar_false_positive"
        else:
            character = "bvh_aabb_false_positive"
        centers = [first_face.calc_center_median(), second_face.calc_center_median()]
        combined_center = (centers[0] + centers[1]) * 0.5
        record: dict[str, Any] = {
            "face_indices": [first_index, second_index],
            "shared_vertex_count": len(
                set(first_face.verts).intersection(second_face.verts)
            ),
            "shared_edge_count": len(
                set(first_face.edges).intersection(second_face.edges)
            ),
            "topology_edge_hops": _topology_distance(
                adjacency,
                first_index,
                second_index,
            ),
            "face_centers": [_vector_record(center) for center in centers],
            "center_distance_m": float((centers[0] - centers[1]).length),
            "combined_bounds": _bounds(
                [vert.co for face in (first_face, second_face) for vert in face.verts]
            ),
            "body_region": _body_region(combined_center, mesh_min, mesh_max),
            "overlap_character": character,
            "genuine_positive_area_or_segment_penetration": bool(genuine),
            "triangle_pair_classifications": triangle_results,
        }
        records.append(record)
    genuine_records = [
        record
        for record in records
        if record["genuine_positive_area_or_segment_penetration"]
    ]
    touch_records = [
        record
        for record in records
        if record["overlap_character"] == "touch_or_coplanar_false_positive"
    ]
    aabb_records = [
        record
        for record in records
        if record["overlap_character"] == "bvh_aabb_false_positive"
    ]
    return {
        "schema_version": 1,
        "audit": "exact_nonadjacent_mesh_intersections_v1",
        "triangulation_coverage": (
            "blender_geometry_tessellation_plus_deterministic_polygon_fan"
        ),
        "linear_tolerance_m": tolerance,
        "mesh_bounds": {
            "min": _vector_record(mesh_min),
            "max": _vector_record(mesh_max),
            "diagonal_m": float(diagonal),
        },
        "bvh_nonadjacent_candidate_pair_count": len(broad_pairs),
        "bvh_nonadjacent_candidate_triangle_pair_count": sum(
            len(values) for values in grouped_candidates.values()
        ),
        "exact_genuine_penetration_pair_count": len(genuine_records),
        "touch_or_coplanar_false_positive_pair_count": len(touch_records),
        "bvh_aabb_false_positive_pair_count": len(aabb_records),
        "pairs": records if include_pair_details else [],
        "read_only": True,
    }


__all__ = [
    "bvh_nonadjacent_face_pairs",
    "classify_triangle_pair",
    "exact_nonadjacent_intersection_report",
]
