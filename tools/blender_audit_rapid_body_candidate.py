#!/usr/bin/env python3
"""Independent exact-artifact topology and deformation audit.

Run in a fresh Blender process after a rapid-body candidate has been exported.
The candidate is imported read-only.  This auditor is deliberately separate
from the authoring worker and never saves or re-exports the input.

Example:

    blender --background --python tools/blender_audit_rapid_body_candidate.py -- \
      --input candidate.glb \
      --topology-output independent_topology_intersection_audit.json \
      --deformation-output independent_bounded_deformation_audit.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import bpy  # type: ignore
from mathutils import Vector  # type: ignore
from mathutils.bvhtree import BVHTree  # type: ignore
from mathutils.kdtree import KDTree  # type: ignore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.blender_exact_mesh_intersections import (  # noqa: E402
    classify_triangle_pair,
)


REQUIRED_POSE_LABELS = (
    "reach",
    "stride",
    "seated",
    "hip_flexion",
    "hand",
    "knee_flexion",
    "knee_flexion_right",
)
MINIMUM_LOCAL_EDGE_RATIO = 0.25
MAXIMUM_LOCAL_EDGE_RATIO = 4.0
MINIMUM_P01_EDGE_RATIO = 0.70
MAXIMUM_P99_EDGE_RATIO = 1.60
MINIMUM_KNEE_FLEXION_DEGREES = 20.0
MAXIMUM_KNEE_FLEXION_DEGREES = 155.0
MINIMUM_POSTERIOR_SHIN_RATIO = 0.12
MINIMUM_POSTERIOR_SHIN_METERS = 0.015
MAXIMUM_KNEE_JOINT_GAP_METERS = 0.025


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--topology-output", required=True)
    parser.add_argument("--deformation-output", required=True)
    parser.add_argument(
        "--reviewed-intentional-boundary-loops",
        type=int,
        default=0,
    )
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (
        bpy.data.meshes,
        bpy.data.armatures,
        bpy.data.actions,
        bpy.data.materials,
        bpy.data.images,
    ):
        for block in list(collection):
            collection.remove(block)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def connected_components(
    vertex_count: int,
    polygons: list[list[int]],
) -> tuple[int, set[int]]:
    parent = list(range(vertex_count))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    used: set[int] = set()
    for polygon in polygons:
        if not polygon:
            continue
        used.update(polygon)
        for index in polygon[1:]:
            union(polygon[0], index)
    return len({find(index) for index in used}), used


def topology_counts(
    vertex_count: int,
    polygons: list[list[int]],
) -> dict[str, int]:
    edge_use: dict[tuple[int, int], int] = {}
    collapsed_faces = 0
    for polygon in polygons:
        if len(set(polygon)) < 3:
            collapsed_faces += 1
            continue
        for position, left in enumerate(polygon):
            edge = tuple(
                sorted((left, polygon[(position + 1) % len(polygon)]))
            )
            edge_use[edge] = edge_use.get(edge, 0) + 1
    boundary_edges = [edge for edge, count in edge_use.items() if count == 1]
    adjacency: dict[int, set[int]] = {}
    for left, right in boundary_edges:
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)
    seen: set[int] = set()
    boundary_loops = 0
    open_chains = 0
    for seed in adjacency:
        if seed in seen:
            continue
        stack = [seed]
        component: set[int] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(adjacency.get(current, ()))
        seen.update(component)
        if component and all(
            len(adjacency.get(index, ())) == 2 for index in component
        ):
            boundary_loops += 1
        else:
            open_chains += 1
    islands, used = connected_components(vertex_count, polygons)
    return {
        "surface_island_count": islands,
        "unused_vertex_count": vertex_count - len(used),
        "boundary_edge_count": len(boundary_edges),
        "boundary_loop_count": boundary_loops,
        "open_boundary_chain_count": open_chains,
        "non_manifold_edge_count": sum(
            1 for count in edge_use.values() if count > 2
        ),
        "collapsed_face_count": collapsed_faces,
    }


def region_for_point(
    point: Vector,
    low: Vector,
    high: Vector,
) -> str:
    height = max(float(high.z - low.z), 1e-9)
    width = max(float(high.x - low.x), 1e-9)
    z_fraction = (float(point.z) - float(low.z)) / height
    center_x = float((low.x + high.x) * 0.5)
    x_fraction = abs(float(point.x) - center_x) / width
    if z_fraction >= 0.80:
        return "head_face"
    if z_fraction >= 0.55 and x_fraction >= 0.28:
        return "arms_hands"
    if z_fraction >= 0.58:
        return "upper_torso"
    if z_fraction >= 0.40:
        return "pelvis_hips"
    if z_fraction >= 0.10:
        return "legs"
    return "feet"


def welded_topology(obj: bpy.types.Object) -> dict[str, object]:
    polygons = [
        [int(value) for value in polygon.vertices]
        for polygon in obj.data.polygons
    ]
    raw = topology_counts(len(obj.data.vertices), polygons)
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    if not points:
        raise ValueError("primary surface has no vertices")
    low = Vector(
        tuple(min(point[axis] for point in points) for axis in range(3))
    )
    high = Vector(
        tuple(max(point[axis] for point in points) for axis in range(3))
    )
    tolerance = max(max(float(value) for value in high - low) * 1e-6, 1e-9)
    representative_by_key: dict[tuple[int, int, int], int] = {}
    representative_points: list[Vector] = []
    welded_index: dict[int, int] = {}
    for index, point in enumerate(points):
        key = tuple(
            int(round(float(point[axis]) / tolerance))
            for axis in range(3)
        )
        if key not in representative_by_key:
            representative_by_key[key] = len(representative_by_key)
            representative_points.append(point.copy())
        welded_index[index] = representative_by_key[key]
    welded_polygons = [
        [welded_index[index] for index in polygon]
        for polygon in polygons
    ]
    welded = topology_counts(len(representative_by_key), welded_polygons)
    edge_use: dict[tuple[int, int], int] = {}
    for polygon in welded_polygons:
        if len(set(polygon)) < 3:
            continue
        for position, left in enumerate(polygon):
            edge = tuple(
                sorted((left, polygon[(position + 1) % len(polygon)]))
            )
            edge_use[edge] = edge_use.get(edge, 0) + 1
    boundary_adjacency: dict[int, set[int]] = {}
    for (left, right), count in edge_use.items():
        if count != 1:
            continue
        boundary_adjacency.setdefault(left, set()).add(right)
        boundary_adjacency.setdefault(right, set()).add(left)
    boundary_components: list[dict[str, object]] = []
    seen_boundary: set[int] = set()
    for seed in boundary_adjacency:
        if seed in seen_boundary:
            continue
        stack = [seed]
        component: set[int] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(boundary_adjacency.get(current, ()))
        seen_boundary.update(component)
        component_points = [
            representative_points[index] for index in sorted(component)
        ]
        component_low = Vector(
            tuple(
                min(point[axis] for point in component_points)
                for axis in range(3)
            )
        )
        component_high = Vector(
            tuple(
                max(point[axis] for point in component_points)
                for axis in range(3)
            )
        )
        centroid = sum(component_points, Vector()) / len(component_points)
        boundary_components.append(
            {
                "vertex_count": len(component),
                "closed_cycle": all(
                    len(boundary_adjacency.get(index, ())) == 2
                    for index in component
                ),
                "centroid_world_m": [
                    round(float(value), 7) for value in centroid
                ],
                "bounds_low_world_m": [
                    round(float(value), 7) for value in component_low
                ],
                "bounds_high_world_m": [
                    round(float(value), 7) for value in component_high
                ],
                "region": region_for_point(centroid, low, high),
                "boundary_points_world_m": [
                    [float(value) for value in point]
                    for point in component_points
                ],
            }
        )
    boundary_components.sort(
        key=lambda item: (
            str(item["region"]),
            item["centroid_world_m"][2],
            item["centroid_world_m"][0],
        )
    )
    degenerates = sum(
        1
        for polygon in obj.data.polygons
        if len(set(int(value) for value in polygon.vertices)) < 3
        or float(polygon.area) <= 1e-12
    )
    return {
        "vertex_count": len(obj.data.vertices),
        "polygon_count": len(obj.data.polygons),
        "raw_index_surface_island_count": raw["surface_island_count"],
        "raw_index_boundary_edge_count": raw["boundary_edge_count"],
        "positional_weld_tolerance_m": round(tolerance, 10),
        "positional_weld_vertex_count": len(representative_by_key),
        **welded,
        "degenerate_face_count": degenerates,
        "boundary_components": boundary_components,
    }


def boundary_component_role(name: str) -> str:
    value = normalized(name)
    if "fingernail" in value:
        return "fingernail"
    if "toenail" in value:
        return "toenail"
    if any(
        token in value
        for token in (
            "iris",
            "sclera",
            "cornea",
            "pupil",
            "eyesocket",
            "eye_socket",
            "eyemoisture",
            "eye_moisture",
        )
    ):
        return "eye"
    if any(token in value for token in ("lip", "mouth", "teeth")):
        return "mouth"
    return ""


def boundary_support_audit(
    body: bpy.types.Object,
    meshes: list[bpy.types.Object],
    topology: dict[str, object],
) -> dict[str, object]:
    """Bind each body boundary loop to a supported adjacent component.

    This prevents a manually supplied loop count from laundering an arbitrary
    body hole. Only separate eye, mouth, fingernail, and toenail components
    can support a retained interface opening.
    """

    role_points: dict[str, list[Vector]] = {}
    component_objects: list[dict[str, object]] = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in meshes:
        if obj is body:
            continue
        role = (
            boundary_component_role(obj.name)
            or boundary_component_role(obj.data.name)
        )
        if not role:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            points = [
                evaluated.matrix_world @ vertex.co
                for vertex in mesh.vertices
            ]
            role_points.setdefault(role, []).extend(points)
            component_objects.append(
                {
                    "object_name": obj.name,
                    "mesh_name": obj.data.name,
                    "role": role,
                    "evaluated_vertex_count": len(points),
                }
            )
        finally:
            evaluated.to_mesh_clear()
    trees: dict[str, KDTree] = {}
    for role, points in role_points.items():
        if not points:
            continue
        tree = KDTree(len(points))
        for index, point in enumerate(points):
            tree.insert(point, index)
        tree.balance()
        trees[role] = tree

    body_points = [
        body.matrix_world @ vertex.co for vertex in body.data.vertices
    ]
    body_height = (
        max(point.z for point in body_points)
        - min(point.z for point in body_points)
        if body_points
        else 0.0
    )
    tolerance = max(body_height * 0.004, 0.002)
    records: list[dict[str, object]] = []
    role_counts: dict[str, int] = {}
    unsupported = 0
    components = topology.get("boundary_components")
    if not isinstance(components, list):
        components = []
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            continue
        raw_points = component.get("boundary_points_world_m")
        points = (
            [
                Vector(tuple(float(value) for value in raw))
                for raw in raw_points
                if isinstance(raw, list) and len(raw) == 3
            ]
            if isinstance(raw_points, list)
            else []
        )
        nearest_role = ""
        nearest_distance = float("inf")
        for role, tree in trees.items():
            role_distance = min(
                (
                    float(tree.find(point)[2])
                    for point in points
                ),
                default=float("inf"),
            )
            if role_distance < nearest_distance:
                nearest_distance = role_distance
                nearest_role = role
        supported = bool(
            nearest_role
            and math.isfinite(nearest_distance)
            and nearest_distance <= tolerance
        )
        if supported:
            role_counts[nearest_role] = role_counts.get(nearest_role, 0) + 1
        else:
            unsupported += 1
        records.append(
            {
                "boundary_component_index": index,
                "vertex_count": component.get("vertex_count"),
                "region": component.get("region"),
                "nearest_supported_component_role": nearest_role,
                "nearest_distance_m": (
                    round(nearest_distance, 8)
                    if math.isfinite(nearest_distance)
                    else None
                ),
                "within_contact_tolerance": supported,
            }
        )
    return {
        "method": (
            "exact_import_boundary_vertices_to_supported_component_"
            "vertex_kdtree"
        ),
        "supported_roles": [
            "eye",
            "mouth",
            "fingernail",
            "toenail",
        ],
        "supported_component_objects": component_objects,
        "contact_tolerance_m": round(tolerance, 8),
        "boundary_loop_count": len(records),
        "supported_boundary_loop_count": len(records) - unsupported,
        "unsupported_boundary_loop_count": unsupported,
        "role_counts": dict(sorted(role_counts.items())),
        "component_records": records,
        "coverage_complete": bool(records and unsupported == 0),
    }


def self_intersection_audit(obj: bpy.types.Object) -> dict[str, object]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        vertices = [
            evaluated.matrix_world @ vertex.co for vertex in mesh.vertices
        ]
        if not vertices:
            raise ValueError("primary surface has no evaluated vertices")
        low = Vector(
            tuple(
                min(point[axis] for point in vertices)
                for axis in range(3)
            )
        )
        high = Vector(
            tuple(
                max(point[axis] for point in vertices)
                for axis in range(3)
            )
        )
        weld_tolerance = max(
            max(float(value) for value in high - low) * 1e-6,
            1e-9,
        )
        exact_linear_tolerance = max(
            float((high - low).length) * 1e-8,
            1e-10,
        )
        positional_keys = [
            tuple(
                int(round(float(point[axis]) / weld_tolerance))
                for axis in range(3)
            )
            for point in vertices
        ]
        triangles: list[tuple[int, int, int]] = []
        face_vertex_sets: list[set[int]] = []
        face_positional_key_sets: list[set[tuple[int, int, int]]] = []
        source_face_indices: list[int] = []
        for polygon in mesh.polygons:
            indices = [int(value) for value in polygon.vertices]
            for offset in range(1, len(indices) - 1):
                triangle = (indices[0], indices[offset], indices[offset + 1])
                triangles.append(triangle)
                face_vertex_sets.append(set(triangle))
                face_positional_key_sets.append(
                    {positional_keys[index] for index in triangle}
                )
                source_face_indices.append(int(polygon.index))
        signature_counts: dict[
            tuple[tuple[int, int, int], ...],
            int,
        ] = {}
        for keys in face_positional_key_sets:
            signature = tuple(sorted(keys))
            signature_counts[signature] = (
                signature_counts.get(signature, 0) + 1
            )
        coincident_duplicate_pairs = sum(
            count * (count - 1) // 2
            for count in signature_counts.values()
            if count > 1
        )
        bvh = BVHTree.FromPolygons(
            vertices,
            triangles,
            all_triangles=True,
        )
        pairs: set[tuple[int, int]] = set()
        source_face_pairs: set[tuple[int, int]] = set()
        source_pair_midpoints: dict[tuple[int, int], Vector] = {}
        pair_centroids: list[Vector] = []
        exact_triangle_pair_records: list[dict[str, object]] = []
        raw_index_adjacent_pairs_excluded = 0
        positional_weld_adjacent_pairs_excluded = 0
        for left, right in bvh.overlap(bvh):
            if left >= right:
                continue
            if face_vertex_sets[left] & face_vertex_sets[right]:
                raw_index_adjacent_pairs_excluded += 1
                continue
            if (
                face_positional_key_sets[left]
                & face_positional_key_sets[right]
            ):
                positional_weld_adjacent_pairs_excluded += 1
                continue
            source_left = source_face_indices[left]
            source_right = source_face_indices[right]
            if source_left == source_right:
                continue
            pair = (left, right)
            pairs.add(pair)
            source_pair = tuple(sorted((source_left, source_right)))
            source_face_pairs.add(source_pair)
            exact_result = classify_triangle_pair(
                tuple(vertices[index] for index in triangles[left]),
                tuple(vertices[index] for index in triangles[right]),
                linear_tolerance=exact_linear_tolerance,
            )
            exact_triangle_pair_records.append(
                {
                    "triangle_pair": [int(left), int(right)],
                    "source_face_pair": [
                        int(source_pair[0]),
                        int(source_pair[1]),
                    ],
                    **exact_result,
                }
            )
            first_centroid = sum(
                (vertices[index] for index in triangles[left]),
                Vector(),
            ) / 3.0
            second_centroid = sum(
                (vertices[index] for index in triangles[right]),
                Vector(),
            ) / 3.0
            pair_midpoint = (first_centroid + second_centroid) * 0.5
            pair_centroids.append(pair_midpoint)
            source_pair_midpoints.setdefault(source_pair, pair_midpoint)
        region_counts: dict[str, int] = {}
        for centroid in pair_centroids:
            region = region_for_point(centroid, low, high)
            region_counts[region] = region_counts.get(region, 0) + 1
        midline_threshold_m = 0.05
        midline_pair_count = sum(
            1
            for centroid in pair_centroids
            if abs(float(centroid.x)) <= midline_threshold_m
        )
        if pair_centroids:
            centroid_low = [
                min(float(centroid[axis]) for centroid in pair_centroids)
                for axis in range(3)
            ]
            centroid_high = [
                max(float(centroid[axis]) for centroid in pair_centroids)
                for axis in range(3)
            ]
        else:
            centroid_low = [0.0, 0.0, 0.0]
            centroid_high = [0.0, 0.0, 0.0]
        source_face_frequency: dict[int, int] = {}
        for left, right in source_face_pairs:
            source_face_frequency[left] = source_face_frequency.get(left, 0) + 1
            source_face_frequency[right] = (
                source_face_frequency.get(right, 0) + 1
            )
        frequency_top = sorted(
            source_face_frequency.items(),
            key=lambda item: (-item[1], item[0]),
        )[:30]
        exact_genuine_records = [
            record
            for record in exact_triangle_pair_records
            if record.get("genuine_penetration") is True
        ]
        exact_genuine_source_face_pairs = {
            tuple(record["source_face_pair"])
            for record in exact_genuine_records
        }
        exact_classification_counts: dict[str, int] = {}
        for record in exact_triangle_pair_records:
            classification = str(record.get("classification"))
            exact_classification_counts[classification] = (
                exact_classification_counts.get(classification, 0) + 1
            )
        exact_touch_classes = {
            "coplanar_touch_or_numerical_contact",
            "noncoplanar_point_or_edge_touch",
        }
        exact_aabb_classes = {
            "bvh_aabb_only",
            "parallel_bvh_aabb_only",
        }
        return {
            "evaluated_triangle_count": len(triangles),
            # These two legacy fields intentionally remain the raw BVH broad-
            # phase measurements for backward-compatible diagnostics.  The
            # exact fields below are the qualification signal.
            "nonadjacent_intersecting_triangle_pair_count": len(pairs),
            "nonadjacent_intersecting_source_face_pair_count": len(
                source_face_pairs
            ),
            "exact_genuine_nonadjacent_triangle_pair_count": len(
                exact_genuine_records
            ),
            "exact_genuine_nonadjacent_source_face_pair_count": len(
                exact_genuine_source_face_pairs
            ),
            "exact_touch_or_numerical_triangle_pair_count": sum(
                int(record.get("classification") in exact_touch_classes)
                for record in exact_triangle_pair_records
            ),
            "exact_bvh_aabb_false_positive_triangle_pair_count": sum(
                int(record.get("classification") in exact_aabb_classes)
                for record in exact_triangle_pair_records
            ),
            "exact_degenerate_triangle_pair_count": sum(
                int(record.get("classification") == "degenerate_triangle")
                for record in exact_triangle_pair_records
            ),
            "exact_classification_counts": dict(
                sorted(exact_classification_counts.items())
            ),
            "exact_first_triangle_pair_records": (
                exact_triangle_pair_records[:30]
            ),
            "exact_linear_tolerance_m": exact_linear_tolerance,
            "exact_narrow_phase_gate_passed": (
                len(exact_genuine_source_face_pairs) == 0
            ),
            "legacy_bvh_candidate_fields_preserved": True,
            "qualification_intersection_field": (
                "exact_genuine_nonadjacent_source_face_pair_count"
            ),
            "intersection_semantics_note": (
                "Legacy nonadjacent_intersecting_* counts are BVH broad-phase "
                "candidates; only exact_genuine_nonadjacent_* counts represent "
                "positive-length or positive-area penetrations."
            ),
            "first_triangle_pairs": [
                list(pair) for pair in sorted(pairs)[:30]
            ],
            "source_face_pair_records": [
                {
                    "source_face_pair": list(pair),
                    "midpoint_world_m": [
                        round(float(value), 7)
                        for value in source_pair_midpoints[pair]
                    ],
                    "midline_within_0_05m": (
                        abs(float(source_pair_midpoints[pair].x))
                        <= midline_threshold_m
                    ),
                    "region": region_for_point(
                        source_pair_midpoints[pair],
                        low,
                        high,
                    ),
                }
                for pair in sorted(source_face_pairs)
            ],
            "intersecting_source_face_frequency_top": [
                {
                    "source_face_index": int(face_index),
                    "intersection_pair_count": int(count),
                }
                for face_index, count in frequency_top
            ],
            "region_pair_counts": dict(sorted(region_counts.items())),
            "intersection_midpoint_localization": {
                "bounds_low_world_m": [
                    round(value, 7) for value in centroid_low
                ],
                "bounds_high_world_m": [
                    round(value, 7) for value in centroid_high
                ],
                "midline_abs_x_threshold_m": midline_threshold_m,
                "midline_pair_count": midline_pair_count,
                "midline_pair_fraction": round(
                    midline_pair_count / max(1, len(pair_centroids)),
                    7,
                ),
            },
            "first_pair_centroids_world_m": [
                [round(float(value), 7) for value in centroid]
                for centroid in pair_centroids[:30]
            ],
            "complete_bvh_overlap_scan": True,
            "adjacent_shared_vertex_pairs_excluded": True,
            "adjacency_method": (
                "raw_index_or_positional_weld_key_shared_vertex"
            ),
            "positional_weld_tolerance_m": round(weld_tolerance, 10),
            "raw_index_adjacent_triangle_pairs_excluded": (
                raw_index_adjacent_pairs_excluded
            ),
            "positional_weld_adjacent_triangle_pairs_excluded": (
                positional_weld_adjacent_pairs_excluded
            ),
            "coincident_duplicate_triangle_pair_count": (
                coincident_duplicate_pairs
            ),
        }
    finally:
        evaluated.to_mesh_clear()


def weight_audit(obj: bpy.types.Object) -> dict[str, int]:
    unweighted = 0
    bad_sums = 0
    maximum = 0
    for vertex in obj.data.vertices:
        weights = [
            float(item.weight)
            for item in vertex.groups
            if float(item.weight) > 1e-7
        ]
        if not weights:
            unweighted += 1
            continue
        maximum = max(maximum, len(weights))
        if abs(sum(weights) - 1.0) > 1e-3:
            bad_sums += 1
    return {
        "unweighted_vertex_count": unweighted,
        "weight_sum_out_of_tolerance_count": bad_sums,
        "maximum_positive_influences_per_vertex": maximum,
    }


def primary_surface(
    meshes: list[bpy.types.Object],
) -> tuple[bpy.types.Object | None, int, str]:
    marked = [
        obj
        for obj in meshes
        if obj.get("rapid_body_primary_surface") is True
    ]
    if len(marked) == 1:
        return marked[0], 1, "exact_exported_boolean_marker"
    # Diagnostic fallback only.  It allows the failed candidate to be measured
    # so the next build can be repaired, but marker_count remains nonpassing.
    exact_names = [
        obj
        for obj in meshes
        if normalized(obj.name)
        in {
            "kira_temporary_functional_body_primary_surface",
            "kira_hart_temporary_functional_body_primary_surface",
        }
    ]
    if len(exact_names) == 1:
        return exact_names[0], len(marked), "diagnostic_exact_name_fallback"
    return None, len(marked), "unavailable"


def armature_for_body(
    body: bpy.types.Object,
) -> bpy.types.Object | None:
    for modifier in body.modifiers:
        if modifier.type == "ARMATURE" and modifier.object is not None:
            return modifier.object
    current = body.parent
    while current is not None:
        if current.type == "ARMATURE":
            return current
        current = current.parent
    return None


def evaluated_world_points(
    obj: bpy.types.Object,
    sample_indices: list[int],
) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        if max(sample_indices, default=-1) >= len(mesh.vertices):
            raise ValueError("evaluated vertex domain changed")
        return [
            evaluated.matrix_world @ mesh.vertices[index].co
            for index in sample_indices
        ]
    finally:
        evaluated.to_mesh_clear()


def quantile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def anatomical_axis_vector(value: object) -> Vector | None:
    key = str(value or "").strip().upper().replace(" ", "")
    return {
        "+X": Vector((1.0, 0.0, 0.0)),
        "X": Vector((1.0, 0.0, 0.0)),
        "-X": Vector((-1.0, 0.0, 0.0)),
        "+Y": Vector((0.0, 1.0, 0.0)),
        "Y": Vector((0.0, 1.0, 0.0)),
        "-Y": Vector((0.0, -1.0, 0.0)),
    }.get(key)


def knee_direction_audit(
    body: bpy.types.Object,
    armature: bpy.types.Object,
    label: str,
) -> dict[str, object]:
    """Measure the posed knee from the exact imported skeleton.

    A changing file, a large deformation, and even a plausible joint angle do
    not prove that a knee bends in the anatomically useful direction.  The
    body therefore declares its forward axis and the exact knee/ankle chain
    bones. At the action's final sampled frame, the independent auditor
    verifies that the ankle travels behind the knee and that the thigh/shin
    angle is a real flexion rather than a straight or hyperextended leg.
    """

    side = "right" if label == "knee_flexion_right" else "left"
    forward_value = body.get("anatomical_forward_axis")
    upper_name = body.get(f"{side}_knee_upper_bone")
    lower_name = body.get(f"{side}_knee_lower_bone")
    ankle_name = body.get(f"{side}_ankle_bone")
    forward = anatomical_axis_vector(forward_value)
    metadata_present = bool(
        forward is not None
        and isinstance(upper_name, str)
        and upper_name.strip()
        and isinstance(lower_name, str)
        and lower_name.strip()
        and isinstance(ankle_name, str)
        and ankle_name.strip()
    )
    if not metadata_present:
        return {
            "passed": False,
            "side": side,
            "failure": "anatomical_axis_or_knee_bone_binding_missing",
            "anatomical_forward_axis": str(forward_value or ""),
            "upper_leg_bone": str(upper_name or ""),
            "lower_leg_bone": str(lower_name or ""),
            "ankle_bone": str(ankle_name or ""),
            "measured_from_exact_imported_skeleton": False,
        }

    upper = armature.pose.bones.get(str(upper_name))
    lower = armature.pose.bones.get(str(lower_name))
    ankle_bone = armature.pose.bones.get(str(ankle_name))
    if upper is None or lower is None or ankle_bone is None:
        return {
            "passed": False,
            "side": side,
            "failure": "declared_knee_bone_not_found",
            "anatomical_forward_axis": str(forward_value),
            "upper_leg_bone": str(upper_name),
            "lower_leg_bone": str(lower_name),
            "ankle_bone": str(ankle_name),
            "measured_from_exact_imported_skeleton": False,
        }

    matrix = armature.matrix_world
    hip = matrix @ upper.head
    upper_knee = matrix @ upper.tail
    lower_knee = matrix @ lower.head
    knee = (upper_knee + lower_knee) * 0.5
    lower_ankle = matrix @ lower.tail
    ankle_head = matrix @ ankle_bone.head
    ankle = matrix @ ankle_bone.tail
    thigh = knee - hip
    shin = ankle - knee
    joint_gap = (upper_knee - lower_knee).length
    ankle_joint_gap = (lower_ankle - ankle_head).length
    flexion_degrees = (
        math.degrees(thigh.angle(shin))
        if thigh.length > 1e-8 and shin.length > 1e-8
        else 0.0
    )
    posterior = -forward
    posterior_displacement = shin.dot(posterior)
    posterior_ratio = (
        posterior_displacement / shin.length if shin.length > 1e-8 else 0.0
    )
    minimum_displacement = max(
        MINIMUM_POSTERIOR_SHIN_METERS,
        shin.length * MINIMUM_POSTERIOR_SHIN_RATIO,
    )
    passed = bool(
        joint_gap <= MAXIMUM_KNEE_JOINT_GAP_METERS
        and ankle_joint_gap <= MAXIMUM_KNEE_JOINT_GAP_METERS
        and MINIMUM_KNEE_FLEXION_DEGREES
        <= flexion_degrees
        <= MAXIMUM_KNEE_FLEXION_DEGREES
        and posterior_displacement >= minimum_displacement
    )
    failures = []
    if joint_gap > MAXIMUM_KNEE_JOINT_GAP_METERS:
        failures.append("upper_and_lower_leg_knee_heads_are_disconnected")
    if ankle_joint_gap > MAXIMUM_KNEE_JOINT_GAP_METERS:
        failures.append("lower_leg_and_ankle_chain_are_disconnected")
    if not (
        MINIMUM_KNEE_FLEXION_DEGREES
        <= flexion_degrees
        <= MAXIMUM_KNEE_FLEXION_DEGREES
    ):
        failures.append("knee_flexion_angle_out_of_policy")
    if posterior_displacement < minimum_displacement:
        failures.append("ankle_did_not_travel_posterior_of_knee")
    return {
        "passed": passed,
        "side": side,
        "failure": ";".join(failures),
        "anatomical_forward_axis": str(forward_value),
        "upper_leg_bone": str(upper_name),
        "lower_leg_bone": str(lower_name),
        "ankle_bone": str(ankle_name),
        "measured_from_exact_imported_skeleton": True,
        "sampled_at_current_action_frame": int(
            bpy.context.scene.frame_current
        ),
        "hip_world_m": [round(float(value), 7) for value in hip],
        "knee_world_m": [round(float(value), 7) for value in knee],
        "ankle_world_m": [round(float(value), 7) for value in ankle],
        "knee_joint_gap_m": round(float(joint_gap), 8),
        "ankle_chain_joint_gap_m": round(float(ankle_joint_gap), 8),
        "flexion_degrees": round(float(flexion_degrees), 5),
        "posterior_ankle_displacement_m": round(
            float(posterior_displacement),
            7,
        ),
        "posterior_shin_ratio": round(float(posterior_ratio), 6),
        "minimum_required_posterior_displacement_m": round(
            float(minimum_displacement),
            7,
        ),
    }


def action_label(action: bpy.types.Action) -> str:
    value = normalized(action.name)
    if (
        "knee" in value
        and "right" in value
        and any(token in value for token in ("flex", "bend", "test"))
    ):
        return "knee_flexion_right"
    if "knee" in value and any(
        token in value for token in ("flex", "bend", "test")
    ):
        return "knee_flexion"
    if "hip" in value and any(
        token in value for token in ("flex", "bend", "pelvis")
    ):
        return "hip_flexion"
    if any(token in value for token in ("hand", "finger", "grip")):
        return "hand"
    if any(token in value for token in ("seated", "sitting", "sit")):
        return "seated"
    if any(token in value for token in ("stride", "walk", "step")):
        return "stride"
    if any(token in value for token in ("reach", "arm_raise")):
        return "reach"
    if any(token in value for token in ("neutral", "rest")):
        return "neutral"
    return ""


def reset_pose_to_rest(armature: bpy.types.Object) -> None:
    for bone in armature.pose.bones:
        bone.matrix_basis.identity()


def action_deformation_audit(
    body: bpy.types.Object,
    armature: bpy.types.Object,
) -> dict[str, object]:
    if armature.animation_data is None:
        armature.animation_data_create()
    original_action = armature.animation_data.action
    original_track_mutes = [
        bool(track.mute) for track in armature.animation_data.nla_tracks
    ]
    for track in armature.animation_data.nla_tracks:
        track.mute = True
    scene = bpy.context.scene
    original_frame = scene.frame_current
    vertex_stride = max(1, len(body.data.vertices) // 6000)
    vertex_indices = list(range(0, len(body.data.vertices), vertex_stride))
    edge_stride = max(1, len(body.data.edges) // 20000)
    source_edges = list(body.data.edges)
    sampled_edges = [
        (int(edge.vertices[0]), int(edge.vertices[1]))
        for edge in source_edges[::edge_stride]
    ]
    edge_vertex_indices = sorted(
        {index for edge in sampled_edges for index in edge}
    )
    combined_indices = sorted(set(vertex_indices) | set(edge_vertex_indices))
    lookup = {value: index for index, value in enumerate(combined_indices)}

    armature.animation_data.action = None
    reset_pose_to_rest(armature)
    scene.frame_set(0)
    bpy.context.view_layer.update()
    baseline = evaluated_world_points(body, combined_indices)
    records_by_label: dict[str, list[dict[str, object]]] = {}
    assignment_failures = 0
    try:
        for action in list(bpy.data.actions):
            label = action_label(action)
            if not label or label == "neutral":
                continue
            try:
                reset_pose_to_rest(armature)
                armature.animation_data.action = action
            except (RuntimeError, TypeError):
                assignment_failures += 1
                continue
            start = float(action.frame_range[0])
            end = float(action.frame_range[1])
            sample_frames = sorted(
                {
                    int(round(start)),
                    int(round((start + end) * 0.5)),
                    int(round(end)),
                }
            )
            maximum_displacement = 0.0
            all_finite = True
            ratios: list[float] = []
            sampled_frames: list[dict[str, object]] = []
            for frame in sample_frames:
                scene.frame_set(frame)
                bpy.context.view_layer.update()
                current = evaluated_world_points(body, combined_indices)
                displacements = [
                    (current[lookup[index]] - baseline[lookup[index]]).length
                    for index in vertex_indices
                ]
                maximum_displacement = max(
                    maximum_displacement,
                    max(displacements, default=0.0),
                )
                all_finite = bool(
                    all_finite
                    and all(
                        math.isfinite(float(component))
                        for point in current
                        for component in point
                    )
                )
                frame_ratios: list[float] = []
                for left, right in sampled_edges:
                    before = (
                        baseline[lookup[left]] - baseline[lookup[right]]
                    ).length
                    after = (
                        current[lookup[left]] - current[lookup[right]]
                    ).length
                    if before > 1e-8:
                        frame_ratios.append(after / before)
                ratios.extend(frame_ratios)
                sampled_frames.append(
                    {
                        "frame": frame,
                        "maximum_sampled_vertex_displacement_m": round(
                            max(displacements, default=0.0),
                            8,
                        ),
                    }
                )
            record = {
                "action_name": str(action.name),
                "encoded": maximum_displacement > 0.002,
                "all_coordinates_finite": all_finite,
                "sampled_vertex_count": len(vertex_indices),
                "sampled_edge_count_across_frames": len(ratios),
                "sampled_frames": sampled_frames,
                "maximum_sampled_vertex_displacement_m": round(
                    maximum_displacement,
                    8,
                ),
                "edge_stretch_ratio": {
                    "minimum": round(min(ratios, default=0.0), 7),
                    "p01": round(quantile(ratios, 0.01), 7),
                    "median": round(quantile(ratios, 0.50), 7),
                    "p99": round(quantile(ratios, 0.99), 7),
                    "maximum": round(max(ratios, default=0.0), 7),
                },
            }
            knee_direction = None
            if label in {"knee_flexion", "knee_flexion_right"}:
                knee_direction = knee_direction_audit(
                    body,
                    armature,
                    label,
                )
                record["anatomical_knee_direction"] = knee_direction
                record["anatomical_knee_direction_passed"] = (
                    knee_direction["passed"] is True
                )
            record["bounded_structural_deformation_passed"] = bool(
                record["encoded"]
                and all_finite
                and len(ratios) >= 50
                and float(record["edge_stretch_ratio"]["minimum"])
                >= MINIMUM_LOCAL_EDGE_RATIO
                and float(record["edge_stretch_ratio"]["maximum"])
                <= MAXIMUM_LOCAL_EDGE_RATIO
                and float(record["edge_stretch_ratio"]["p01"])
                >= MINIMUM_P01_EDGE_RATIO
                and float(record["edge_stretch_ratio"]["p99"])
                <= MAXIMUM_P99_EDGE_RATIO
                and (
                    label
                    not in {"knee_flexion", "knee_flexion_right"}
                    or (
                        knee_direction is not None
                        and knee_direction["passed"] is True
                    )
                )
            )
            records_by_label.setdefault(label, []).append(record)
    finally:
        armature.animation_data.action = None
        reset_pose_to_rest(armature)
        scene.frame_set(0)
        bpy.context.view_layer.update()
        restored = evaluated_world_points(body, combined_indices)
        restoration_maximum = max(
            (
                (after - before).length
                for before, after in zip(baseline, restored)
            ),
            default=0.0,
        )
        armature.animation_data.action = original_action
        for track, muted in zip(
            armature.animation_data.nla_tracks,
            original_track_mutes,
        ):
            track.mute = muted
        scene.frame_set(original_frame)
        bpy.context.view_layer.update()

    records: dict[str, dict[str, object]] = {}
    for label, action_records in records_by_label.items():
        if len(action_records) == 1:
            records[label] = {
                **action_records[0],
                "action_count": 1,
                "all_action_records": action_records,
            }
            continue
        ratio_records = [
            record["edge_stretch_ratio"] for record in action_records
        ]
        records[label] = {
            "action_name": "",
            "action_names": [
                str(record["action_name"]) for record in action_records
            ],
            "action_count": len(action_records),
            "all_action_records": action_records,
            "encoded": all(
                record["encoded"] is True for record in action_records
            ),
            "all_coordinates_finite": all(
                record["all_coordinates_finite"] is True
                for record in action_records
            ),
            "sampled_vertex_count": max(
                int(record["sampled_vertex_count"])
                for record in action_records
            ),
            "sampled_edge_count_across_frames": sum(
                int(record["sampled_edge_count_across_frames"])
                for record in action_records
            ),
            "sampled_frames": [],
            "maximum_sampled_vertex_displacement_m": max(
                float(record["maximum_sampled_vertex_displacement_m"])
                for record in action_records
            ),
            "edge_stretch_ratio": {
                "minimum": min(
                    float(ratios["minimum"]) for ratios in ratio_records
                ),
                "p01": min(
                    float(ratios["p01"]) for ratios in ratio_records
                ),
                "median": quantile(
                    [
                        float(ratios["median"])
                        for ratios in ratio_records
                    ],
                    0.50,
                ),
                "p99": max(
                    float(ratios["p99"]) for ratios in ratio_records
                ),
                "maximum": max(
                    float(ratios["maximum"]) for ratios in ratio_records
                ),
            },
            "bounded_structural_deformation_passed": all(
                record["bounded_structural_deformation_passed"] is True
                for record in action_records
            ),
        }
        if label in {"knee_flexion", "knee_flexion_right"}:
            records[label]["anatomical_knee_direction_passed"] = all(
                record.get("anatomical_knee_direction_passed") is True
                for record in action_records
            )
            records[label]["anatomical_knee_direction_records"] = [
                record.get("anatomical_knee_direction", {})
                for record in action_records
            ]

    missing = [label for label in REQUIRED_POSE_LABELS if label not in records]
    failed = [
        label
        for label in REQUIRED_POSE_LABELS
        if label in records
        and records[label]["bounded_structural_deformation_passed"] is not True
    ]
    return {
        "required_pose_labels": list(REQUIRED_POSE_LABELS),
        "edge_deformation_policy": {
            "minimum_local_edge_ratio": MINIMUM_LOCAL_EDGE_RATIO,
            "maximum_local_edge_ratio": MAXIMUM_LOCAL_EDGE_RATIO,
            "minimum_p01_edge_ratio": MINIMUM_P01_EDGE_RATIO,
            "maximum_p99_edge_ratio": MAXIMUM_P99_EDGE_RATIO,
        },
        "anatomical_knee_direction_policy": {
            "minimum_flexion_degrees": MINIMUM_KNEE_FLEXION_DEGREES,
            "maximum_flexion_degrees": MAXIMUM_KNEE_FLEXION_DEGREES,
            "minimum_posterior_shin_ratio": (
                MINIMUM_POSTERIOR_SHIN_RATIO
            ),
            "minimum_posterior_shin_meters": (
                MINIMUM_POSTERIOR_SHIN_METERS
            ),
            "maximum_knee_joint_gap_meters": (
                MAXIMUM_KNEE_JOINT_GAP_METERS
            ),
            "requires_declared_body_forward_axis_and_leg_bones": True,
            "measurement": (
                "exact imported final-frame skeleton hip/knee/ankle"
            ),
        },
        "pose_records": records,
        "missing_pose_labels": missing,
        "failed_pose_labels": failed,
        "action_assignment_failure_count": assignment_failures,
        "restoration": {
            "maximum_sampled_vertex_delta_m": round(
                restoration_maximum,
                9,
            ),
            "restored_within_1e_6_m": restoration_maximum <= 1e-6,
        },
        "bounded_pose_deformation_gate_passed": bool(
            not missing
            and not failed
            and assignment_failures == 0
            and restoration_maximum <= 1e-6
        ),
        "truth_note": (
            "This proves that exact encoded actions deform sampled vertices "
            "within broad structural bounds. Visual naturalness, soft tissue, "
            "contact, locomotion quality, and runtime compatibility remain "
            "separate review gates."
        ),
    }


def main() -> int:
    args = parse_args()
    source = Path(args.input).resolve(strict=True)
    topology_output = Path(args.topology_output).resolve()
    deformation_output = Path(args.deformation_output).resolve()
    if source.suffix.casefold() != ".glb":
        raise SystemExit("input must be GLB")
    if args.reviewed_intentional_boundary_loops < 0:
        raise SystemExit("reviewed boundary-loop count cannot be negative")
    candidate_sha256 = sha256_file(source)

    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(source))
    bpy.context.view_layer.update()
    objects = list(bpy.context.scene.objects)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    body, primary_marker_count, primary_selection_mode = primary_surface(
        meshes
    )
    if body is None:
        topology_report = {
            "schema_version": 1,
            "audit_mode": "independent_blender_rapid_body_topology_v1",
            "producer": "tools/blender_audit_rapid_body_candidate.py",
            "candidate_sha256": candidate_sha256,
            "input_modified": False,
            "primary_marker_count": primary_marker_count,
            "primary_selection_mode": primary_selection_mode,
            "primary_body": {"present": False},
            "self_intersection": {
                "complete_bvh_overlap_scan": False,
            },
            "topology_intersection_gate_passed": False,
            "failure": "exactly_one_rapid_body_primary_surface_marker_required",
        }
        deformation_report = {
            "schema_version": 1,
            "audit_mode": "independent_blender_rapid_body_deformation_v1",
            "producer": "tools/blender_audit_rapid_body_candidate.py",
            "candidate_sha256": candidate_sha256,
            "input_modified": False,
            "bounded_pose_deformation_gate_passed": False,
            "failure": "primary_surface_unavailable",
        }
        write_json(topology_output, topology_report)
        write_json(deformation_output, deformation_report)
        return 4

    topology = welded_topology(body)
    boundary_support = boundary_support_audit(body, meshes, topology)
    intersections = self_intersection_audit(body)
    weights = weight_audit(body)
    reviewed_loops = int(args.reviewed_intentional_boundary_loops)
    topology_gate = bool(
        topology["surface_island_count"] == 1
        and primary_marker_count == 1
        and topology["boundary_loop_count"] == reviewed_loops
        and boundary_support["coverage_complete"] is True
        and boundary_support["boundary_loop_count"]
        == topology["boundary_loop_count"]
        and boundary_support["unsupported_boundary_loop_count"] == 0
        and topology["open_boundary_chain_count"] == 0
        and topology["non_manifold_edge_count"] == 0
        and topology["degenerate_face_count"] == 0
        and intersections[
            "exact_genuine_nonadjacent_source_face_pair_count"
        ]
        == 0
        and intersections["coincident_duplicate_triangle_pair_count"] == 0
        and weights["unweighted_vertex_count"] == 0
        and weights["weight_sum_out_of_tolerance_count"] == 0
    )
    topology_report = {
        "schema_version": 1,
        "audit_mode": "independent_blender_rapid_body_topology_v1",
        "producer": "tools/blender_audit_rapid_body_candidate.py",
        "candidate_sha256": candidate_sha256,
        "blender_version": bpy.app.version_string,
        "input_modified": False,
        "render_created": False,
        "primary_marker_count": primary_marker_count,
        "primary_selection_mode": primary_selection_mode,
        "primary_body": {
            "present": True,
            **topology,
            **weights,
            "reviewed_intentional_boundary_loop_count": reviewed_loops,
            "boundary_component_support": boundary_support,
        },
        "self_intersection": intersections,
        "topology_intersection_gate_passed": topology_gate,
        "owner_approved": False,
        "runtime_assignment_allowed": False,
        "truth_note": (
            "This independent import measures the exact exported primary "
            "surface. It does not prove visual anatomy, likeness, natural "
            "motion, owner approval, or runtime eligibility."
        ),
    }

    armature = armature_for_body(body)
    if armature is None:
        deformation = {
            "required_pose_labels": list(REQUIRED_POSE_LABELS),
            "pose_records": {},
            "missing_pose_labels": list(REQUIRED_POSE_LABELS),
            "failed_pose_labels": [],
            "bounded_pose_deformation_gate_passed": False,
            "failure": "primary_surface_armature_unavailable",
        }
        joint_count = 0
    else:
        deformation = action_deformation_audit(body, armature)
        joint_count = len(armature.data.bones)
    deformation_report = {
        "schema_version": 1,
        "audit_mode": "independent_blender_rapid_body_deformation_v1",
        "producer": "tools/blender_audit_rapid_body_candidate.py",
        "candidate_sha256": candidate_sha256,
        "blender_version": bpy.app.version_string,
        "input_modified": False,
        "render_created": False,
        "skeleton_profile": {
            "joint_count": joint_count,
            "runtime_compatibility_claimed": False,
            "future_adapter_or_eligibility_proof_required": True,
        },
        **deformation,
        "owner_approved": False,
        "runtime_assignment_allowed": False,
    }
    write_json(topology_output, topology_report)
    write_json(deformation_output, deformation_report)
    print(
        json.dumps(
            {
                "ok": bool(
                    topology_report["topology_intersection_gate_passed"]
                    and deformation_report[
                        "bounded_pose_deformation_gate_passed"
                    ]
                ),
                "candidate_sha256": candidate_sha256,
                "topology_output": str(topology_output),
                "deformation_output": str(deformation_output),
                "topology_intersection_gate_passed": topology_report[
                    "topology_intersection_gate_passed"
                ],
                "bounded_pose_deformation_gate_passed": deformation_report[
                    "bounded_pose_deformation_gate_passed"
                ],
                "runtime_assignment_allowed": False,
            },
            indent=2,
        )
    )
    return 0 if (
        topology_report["topology_intersection_gate_passed"]
        and deformation_report["bounded_pose_deformation_gate_passed"]
    ) else 5


if __name__ == "__main__":
    raise SystemExit(main())
