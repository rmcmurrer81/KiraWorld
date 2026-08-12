#!/usr/bin/env python3
"""Build an append-only, private BlackProject natural-nail component probe.

The probe imports the exact enrolled CC BY 4.0 BlackProject adult-female
foundation, removes its source fingernail and toenail objects, and adapts the
existing natural-nail-v3 conformal projection method to the source's native
188-joint rig.  It creates twenty detachable, short, rounded nail plates, runs
neutral-pose clearance and exact-terminal-bone attachment checks, and renders
close evidence.  It never saves back to the source, creates a body candidate,
or changes runtime/roster state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import blender_avatar_natural_nail_delivery_v3 as nail_v3  # noqa: E402
from tools import blender_profiled_adult_candidate_components as component_v1  # noqa: E402
from tools.blender_exact_mesh_intersections import classify_triangle_pair  # noqa: E402
from Core.avatar_natural_nail_delivery_v3 import (  # noqa: E402
    MINIMUM_SURFACE_CLEARANCE_M,
    validate_attachment_measurement,
    validate_clearance_measurement,
)


SOURCE_SHA256 = "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df"
ALIGNMENT_SHA256 = "c62ebfd8badc43ea98561f4eacbeb127942eeefe2d476bace1f0e22e24d6d9a2"
TARGET_HEIGHT_M = 1.651
SOURCE_CENTER_OFFSET_FRACTIONS = (0.0, -0.16, 0.16, -0.32, 0.32)
SOURCE_LATERAL_OFFSET_FRACTIONS = (0.0, -0.25, 0.25, -0.50, 0.50, -0.75, 0.75)
BLACKPROJECT_PROJECTION_GRID_SIZE = 17
BLACKPROJECT_LOCAL_LIFT_MAXIMUM_ITERATIONS = 14
BLACKPROJECT_FOOTPRINT_SCALE_CANDIDATES = (
    1.00,
    0.96,
    0.92,
    0.88,
    0.84,
    0.80,
    0.76,
    0.72,
    0.68,
    0.64,
    0.60,
    0.56,
)
BLACKPROJECT_MINIMUM_RETAINED_FOOTPRINT_SCALE = 0.56
BLACKPROJECT_BIG_TOE_FOOTPRINT_SCALE_CANDIDATES = (
    0.72,
    0.68,
    0.64,
    0.60,
    0.56,
    0.52,
    0.50,
)
BLACKPROJECT_EDGE_BEVEL_WIDTH_M = 0.000045
BLACKPROJECT_EDGE_BEVEL_SEGMENTS = 4
BLACKPROJECT_PLATE_THICKNESS_M = 0.000140
BLACKPROJECT_BEVEL_CLEARANCE_COMPENSATION_M = 0.000025
BLACKPROJECT_DIGIT_BOUND_PADDING_M = 0.0015
BLACKPROJECT_NAIL_BED_MATERIAL: dict[str, Any] = {
    "srgb_hex": "#C27F82",
    "alpha": 1.0,
    "roughness": 0.31,
    "transmission_weight": 0.012,
    "subsurface_weight": 0.040,
    "coat_weight": 0.16,
    "description": (
        "contrast-safe natural translucent warm-pink nail bed; opaque alpha "
        "prevents false disconnected patches in review renders"
    ),
}
BLACKPROJECT_FREE_EDGE_MATERIAL: dict[str, Any] = {
    "srgb_hex": "#D8B7B3",
    "alpha": 1.0,
    "roughness": 0.34,
    "transmission_weight": 0.018,
    "subsurface_weight": 0.028,
    "coat_weight": 0.12,
    "description": "short softly paler translucent free edge, never white polish",
}
ANALYTIC_FOOTPRINT_SCALE_CANDIDATES = (0.70, 0.64, 0.58, 0.54, 0.50)
ANALYTIC_LONGITUDINAL_RADIUS_M = (
    0.0035,
    0.0045,
    0.006,
    0.008,
    0.012,
    0.018,
    0.030,
    0.060,
    1.0e6,
)
ANALYTIC_LATERAL_RADIUS_M = (
    0.0025,
    0.0035,
    0.0045,
    0.005,
    0.0075,
    0.011,
    0.018,
    0.035,
    1.0e6,
)
ANALYTIC_CLEARANCE_LIFT_M = tuple(
    0.000040 + index * 0.000025 for index in range(17)
)
SOURCE_NAIL_MESHES = (
    "Ariel_Mesh_Fingernails_0",
    "Ariel_Mesh_Toenails_0",
)
HAND_SURFACE_MESH = "Ariel_Mesh_Arms_0"
FOOT_SURFACE_MESH = "Ariel_Mesh_Legs_0"
BLACKPROJECT_RECESS_MINIMUM_CLEARANCE_M = 0.000040
BLACKPROJECT_RECESS_TOP_MINIMUM_CLEARANCE_M = (
    BLACKPROJECT_RECESS_MINIMUM_CLEARANCE_M
    + BLACKPROJECT_BEVEL_CLEARANCE_COMPENSATION_M
)
BLACKPROJECT_RECESS_MAXIMUM_PERIMETER_CLEARANCE_M = 0.0030
BLACKPROJECT_RECESS_MAXIMUM_CENTER_GAP_M = 0.0045
BLACKPROJECT_RECESS_CLOSE_PERIMETER_THRESHOLD_M = 0.00125
BLACKPROJECT_RECESS_MINIMUM_CLOSE_PERIMETER_FRACTION = 0.20
BLACKPROJECT_RECESS_LIFT_CANDIDATES_M = tuple(
    -0.00030 + index * 0.00005 for index in range(37)
)
BLACKPROJECT_SOURCE_SPAN_SCALE_CANDIDATES = (
    0.88,
    0.84,
    0.80,
    0.76,
    0.72,
    0.68,
    0.64,
    0.60,
)


def _smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, float(value)))
    return value * value * (3.0 - 2.0 * value)


def _rounded_outline_coordinates(
    *,
    row: int,
    column: int,
    grid: int,
    length_m: float,
    width_m: float,
    footprint_scale: float,
) -> tuple[float, float, float]:
    """Return a short rounded nail-bed point in its local tangent plane.

    The proximal and distal ends retain useful width but their corners sweep
    inward smoothly.  The sidewalls taper mildly toward both ends instead of
    producing the hard trapezoid/chip silhouette seen in attempt 25.
    """

    t = row / (grid - 1)
    across_fraction = (column / (grid - 1)) - 0.5
    if t <= 0.28:
        row_width_scale = 0.76 + 0.24 * _smoothstep(t / 0.28)
    elif t >= 0.68:
        row_width_scale = 1.0 - 0.16 * _smoothstep((t - 0.68) / 0.32)
    else:
        row_width_scale = 1.0
    along = (t - 0.5) * length_m * footprint_scale
    corner_fraction = min(1.0, abs(across_fraction) * 2.0) ** 2
    proximal_weight = _smoothstep(max(0.0, (0.24 - t) / 0.24))
    distal_weight = _smoothstep(max(0.0, (t - 0.76) / 0.24))
    along += (
        length_m
        * footprint_scale
        * corner_fraction
        * (0.060 * proximal_weight - 0.050 * distal_weight)
    )
    across = (
        across_fraction
        * width_m
        * footprint_scale
        * row_width_scale
    )
    return along, across, across_fraction


def _grid_locality_record(
    *,
    points: list[Vector],
    nominal_center: Vector,
    longitudinal: Vector,
    lateral: Vector,
    length_m: float,
    width_m: float,
    footprint_scale: float,
    grid: int,
) -> dict[str, Any]:
    if len(points) != grid * grid:
        return {
            "grid_sample_count": len(points),
            "expected_grid_sample_count": grid * grid,
            "one_connected_grid_shell_by_construction": False,
            "locality_gate_passed": False,
            "failure_reason": "incomplete_grid",
        }
    longitudinal_edges: list[float] = []
    lateral_edges: list[float] = []
    for row in range(grid):
        for column in range(grid):
            index = row * grid + column
            if row + 1 < grid:
                longitudinal_edges.append(
                    float((points[index] - points[index + grid]).length)
                )
            if column + 1 < grid:
                lateral_edges.append(
                    float((points[index] - points[index + 1]).length)
                )
    all_edges = longitudinal_edges + lateral_edges
    ordered = sorted(all_edges)
    expected_longitudinal_step = length_m * footprint_scale / (grid - 1)
    expected_lateral_step = width_m * footprint_scale / (grid - 1)
    maximum_allowed_neighbor_edge = max(
        0.00075,
        expected_longitudinal_step * 2.8,
        expected_lateral_step * 3.5,
    )
    centroid = sum(points, Vector()) / len(points)
    relative = [point - nominal_center for point in points]
    longitudinal_values = [float(value.dot(longitudinal)) for value in relative]
    lateral_values = [float(value.dot(lateral)) for value in relative]
    maximum_neighbor_edge = max(all_edges)
    return {
        "grid_sample_count": len(points),
        "expected_grid_sample_count": grid * grid,
        "one_connected_grid_shell_by_construction": True,
        "maximum_longitudinal_neighbor_edge_m": max(longitudinal_edges),
        "maximum_lateral_neighbor_edge_m": max(lateral_edges),
        "maximum_neighbor_edge_m": maximum_neighbor_edge,
        "median_neighbor_edge_m": ordered[len(ordered) // 2],
        "maximum_allowed_neighbor_edge_m": maximum_allowed_neighbor_edge,
        "centroid_to_nominal_center_m": float((centroid - nominal_center).length),
        "longitudinal_span_m": max(longitudinal_values) - min(longitudinal_values),
        "lateral_span_m": max(lateral_values) - min(lateral_values),
        "locality_gate_passed": maximum_neighbor_edge <= maximum_allowed_neighbor_edge,
        "failure_reason": (
            ""
            if maximum_neighbor_edge <= maximum_allowed_neighbor_edge
            else "discontinuous_or_wrong_surface_grid_neighbor"
        ),
    }


def _top_surface_winding_record(nail: Any, outward: Vector) -> dict[str, Any]:
    nail.data.update(calc_edges=True)
    alignments = [
        float((nail.matrix_world.to_3x3() @ polygon.normal).normalized().dot(outward))
        for polygon in nail.data.polygons
    ]
    non_outward = sum(value <= 0.0 for value in alignments)
    return {
        "minimum_outward_face_normal_alignment": min(alignments),
        "maximum_outward_face_normal_alignment": max(alignments),
        "non_outward_face_count": int(non_outward),
        "all_top_surface_faces_outward": non_outward == 0,
    }


def _inventory() -> tuple[dict[str, Any], ...]:
    """Exact BlackProject distal-bone mapping, confirmed by alignment probe."""

    finger_bones = {
        "L": ("lThumb3_049", "lIndex3_053", "lMid3_057", "lRing3_061", "lPinky3_065"),
        "R": ("rThumb3_074", "rIndex3_078", "rMid3_082", "rRing3_01", "rPinky3_088"),
    }
    toe_bones = {
        "L": (
            "lBigToe_2_020",
            "lSmallToe1_2_018",
            "lSmallToe2_2_016",
            "lSmallToe3_2_014",
            "lSmallToe4_2_012",
        ),
        "R": (
            "rBigToe_2_036",
            "rSmallToe1_2_034",
            "rSmallToe2_2_032",
            "rSmallToe3_2_030",
            "rSmallToe4_2_028",
        ),
    }
    rows: list[dict[str, Any]] = []
    for side in ("L", "R"):
        for digit, bone in enumerate(finger_bones[side], start=1):
            rows.append(
                {
                    "nail_id": f"fingernail_{digit}_{side}",
                    "kind": "fingernail",
                    "side": side,
                    "digit": digit,
                    "bone": bone,
                    "surface_mesh": HAND_SURFACE_MESH,
                    "outward_hint": (0.0, -1.0, 0.0),
                    "length_height_fraction": 0.0046 if digit == 1 else 0.0038,
                    "width_height_fraction": 0.0030 if digit == 1 else 0.0023,
                }
            )
        for digit, bone in enumerate(toe_bones[side], start=1):
            rows.append(
                {
                    "nail_id": f"toenail_{digit}_{side}",
                    "kind": "toenail",
                    "side": side,
                    "digit": digit,
                    "bone": bone,
                    "surface_mesh": FOOT_SURFACE_MESH,
                    "outward_hint": (0.0, -0.10, 1.0),
                    "length_height_fraction": 0.0048 if digit == 1 else 0.0031,
                    "width_height_fraction": 0.0041 if digit == 1 else 0.0024,
                }
            )
    return tuple(rows)


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.users == 0:
            bpy.data.collections.remove(collection)


def _mesh_map(objects: Iterable[Any]) -> dict[str, Any]:
    return {obj.data.name: obj for obj in objects if obj.type == "MESH"}


def _alignment_bones(record: Mapping[str, Any]) -> set[str]:
    return {
        str(item["dominant_group"])
        for rows in record["records"].values()
        for item in rows
    }


def _alignment_rows_by_bone(record: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["dominant_group"]): dict(item)
        for rows in record["records"].values()
        for item in rows
    }


def _connected_vertex_components(mesh: Any) -> list[list[int]]:
    adjacency: list[set[int]] = [set() for _vertex in mesh.vertices]
    for edge in mesh.edges:
        first, second = (int(value) for value in edge.vertices)
        adjacency[first].add(second)
        adjacency[second].add(first)
    remaining = set(range(len(mesh.vertices)))
    components: list[list[int]] = []
    while remaining:
        start = remaining.pop()
        stack = [start]
        component = [start]
        while stack:
            current = stack.pop()
            neighbors = adjacency[current] & remaining
            remaining.difference_update(neighbors)
            stack.extend(neighbors)
            component.extend(neighbors)
        components.append(sorted(component))
    return components


def _measure_excluded_source_nail_frames(
    *,
    source_objects: Mapping[str, Any],
    alignment_rows: Mapping[str, Mapping[str, Any]],
    body_trees: Mapping[str, BVHTree],
) -> dict[str, dict[str, Any]]:
    """Measure only component center/frame/spans before source-nail exclusion.

    The returned scalar/vector measurements guide a newly generated parametric
    shell. No source vertex position, face, UV, material, or weight is retained
    in the generated mesh or saved probe.
    """

    result: dict[str, dict[str, Any]] = {}
    for source_mesh_name in SOURCE_NAIL_MESHES:
        source_obj = source_objects[source_mesh_name]
        components = _connected_vertex_components(source_obj.data)
        if len(components) != 10:
            raise ValueError(
                f"source nail mesh must have ten connected components: "
                f"{source_mesh_name}={len(components)}"
            )
        for component in components:
            group_weights: dict[str, float] = {}
            for vertex_index in component:
                vertex = source_obj.data.vertices[vertex_index]
                for assignment in vertex.groups:
                    group_name = source_obj.vertex_groups[int(assignment.group)].name
                    group_weights[group_name] = group_weights.get(group_name, 0.0) + float(
                        assignment.weight
                    )
            if not group_weights:
                raise ValueError(
                    f"source nail component lacks a distal-bone group: {source_mesh_name}"
                )
            dominant_bone = max(group_weights.items(), key=lambda item: item[1])[0]
            if dominant_bone not in alignment_rows:
                raise ValueError(
                    f"source nail component has unexpected dominant group: {dominant_bone}"
                )
            if dominant_bone in result:
                raise ValueError(f"duplicate source nail component: {dominant_bone}")
            alignment_row = alignment_rows[dominant_bone]
            if len(component) != int(alignment_row["component_vertex_count"]):
                raise ValueError(
                    f"source component vertex-count mismatch: {dominant_bone}"
                )
            world_points = [
                source_obj.matrix_world @ source_obj.data.vertices[index].co
                for index in component
            ]
            array = np.asarray(
                [[float(value) for value in point] for point in world_points],
                dtype=np.float64,
            )
            centroid_array = array.mean(axis=0)
            centered = array - centroid_array
            covariance = centered.T @ centered / max(1, len(array) - 1)
            eigenvalues, eigenvectors = np.linalg.eigh(covariance)
            order = np.argsort(eigenvalues)
            eigenvalues = eigenvalues[order]
            eigenvectors = eigenvectors[:, order]
            normal = Vector(tuple(float(value) for value in eigenvectors[:, 0]))
            preferred = (
                Vector((0.0, -1.0, 0.0))
                if source_mesh_name == "Ariel_Mesh_Fingernails_0"
                else Vector((0.0, 0.0, 1.0))
            )
            if normal.dot(preferred) < 0.0:
                normal = -normal
            normal.normalize()
            anchor = Vector(tuple(float(value) for value in centroid_array))
            digit_center = Vector(alignment_row["digit_bounds_m"]["center"])
            distal_hint = anchor - digit_center
            longitudinal = distal_hint - normal * distal_hint.dot(normal)
            if longitudinal.length <= 1.0e-7:
                principal = Vector(
                    tuple(float(value) for value in eigenvectors[:, -1])
                )
                longitudinal = principal - normal * principal.dot(normal)
            if longitudinal.length <= 1.0e-7:
                raise ValueError(f"source PCA tangent degenerate: {dominant_bone}")
            longitudinal.normalize()
            if longitudinal.dot(distal_hint) < 0.0:
                longitudinal = -longitudinal
            lateral = normal.cross(longitudinal)
            if lateral.length <= 1.0e-7:
                raise ValueError(f"source PCA lateral degenerate: {dominant_bone}")
            lateral.normalize()
            longitudinal = lateral.cross(normal).normalized()
            longitudinal_values = [
                float((point - anchor).dot(longitudinal)) for point in world_points
            ]
            lateral_values = [
                float((point - anchor).dot(lateral)) for point in world_points
            ]
            normal_values = [
                float((point - anchor).dot(normal)) for point in world_points
            ]
            surface_mesh = (
                HAND_SURFACE_MESH
                if source_mesh_name == "Ariel_Mesh_Fingernails_0"
                else FOOT_SURFACE_MESH
            )
            body_tree = body_trees[surface_mesh]
            body_distances: list[float] = []
            for point in world_points:
                nearest = body_tree.find_nearest(point, 0.020)
                if nearest[0] is None:
                    raise ValueError(
                        f"source component body-distance query failed: {dominant_bone}"
                    )
                body_distances.append(float(nearest[3]))
            ordered_body_distances = sorted(body_distances)
            source_close_count = sum(
                value <= BLACKPROJECT_RECESS_CLOSE_PERIMETER_THRESHOLD_M
                for value in body_distances
            )
            aligned_center = Vector(alignment_row["nail_bounds_m"]["center"])
            result[dominant_bone] = {
                "source_mesh": source_mesh_name,
                "dominant_bone": dominant_bone,
                "component_vertex_count": len(component),
                "component_centroid_world_m": [float(value) for value in anchor],
                "alignment_aabb_center_world_m": [
                    float(value) for value in aligned_center
                ],
                "component_centroid_to_alignment_aabb_center_m": float(
                    (anchor - aligned_center).length
                ),
                "pca_eigenvalues_m2": [float(value) for value in eigenvalues],
                "outward_world": [float(value) for value in normal],
                "longitudinal_world": [float(value) for value in longitudinal],
                "lateral_world": [float(value) for value in lateral],
                "measured_longitudinal_span_m": max(longitudinal_values)
                - min(longitudinal_values),
                "measured_lateral_span_m": max(lateral_values)
                - min(lateral_values),
                "measured_normal_span_m": max(normal_values) - min(normal_values),
                "source_component_to_body_distance_m": {
                    "surface_mesh": surface_mesh,
                    "sample_count": len(body_distances),
                    "minimum": min(body_distances),
                    "median": ordered_body_distances[
                        len(ordered_body_distances) // 2
                    ],
                    "percentile_90": float(
                        np.percentile(np.asarray(body_distances), 90.0)
                    ),
                    "maximum": max(body_distances),
                    "close_threshold_m": (
                        BLACKPROJECT_RECESS_CLOSE_PERIMETER_THRESHOLD_M
                    ),
                    "close_sample_count": source_close_count,
                    "close_sample_fraction": source_close_count
                    / len(body_distances),
                },
                "measurement_only_no_source_geometry_copied": True,
            }
    if set(result) != set(alignment_rows):
        raise ValueError("measured source components do not match exact 20-bone set")
    return result


def _source_fit_outward_hint(
    *,
    armature: Any,
    bone_name: str,
    alignment_row: Mapping[str, Any],
    kind: str,
) -> tuple[float, float, float]:
    """Derive only a fit frame from source bounds; no source vertices are copied.

    BlackProject's T-pose hands are rolled so several nail beds face mostly
    downward rather than global -Y.  The generic MakeHuman outward hints are
    therefore insufficient.  The source nail-center minus digit-center vector,
    projected perpendicular to the exact distal bone, supplies a deterministic
    dorsal hint while the new shell still comes entirely from v3 raycasts.
    """

    bone = armature.data.bones.get(str(bone_name))
    if bone is None:
        raise ValueError(f"distal bone missing while deriving fit frame: {bone_name}")
    direction = (
        armature.matrix_world.to_3x3() @ (bone.tail_local - bone.head_local)
    ).normalized()
    nail_center = Vector(alignment_row["nail_bounds_m"]["center"])
    digit_center = Vector(alignment_row["digit_bounds_m"]["center"])
    raw = nail_center - digit_center
    projected = raw - direction * raw.dot(direction)
    preferred = Vector((0.0, 0.0, -1.0)) if kind == "fingernail" else Vector((0.0, -0.25, 1.0))
    preferred.normalize()
    if projected.length <= 1.0e-7:
        projected = preferred - direction * preferred.dot(direction)
    if projected.length <= 1.0e-7:
        raise ValueError(f"degenerate source-fit outward frame: {bone_name}")
    projected.normalize()
    if projected.dot(preferred) < 0.0:
        projected = -projected
    return tuple(float(value) for value in projected)


def _local_surface_outward_hint(
    *,
    body_tree: BVHTree,
    armature: Any,
    bone_name: str,
    source_center_world: Vector,
    fallback_hint: tuple[float, float, float],
) -> tuple[float, float, float]:
    hit, normal, _face, _distance = body_tree.find_nearest(
        source_center_world,
        0.020,
    )
    if hit is None or normal is None:
        raise ValueError(f"no local nail-bed surface for {bone_name}")
    normal.normalize()
    toward_source = source_center_world - hit
    if toward_source.length > 1.0e-8 and normal.dot(toward_source) < 0.0:
        normal = -normal
    bone = armature.data.bones.get(bone_name)
    if bone is None:
        raise ValueError(f"distal bone missing: {bone_name}")
    direction = (
        armature.matrix_world.to_3x3() @ (bone.tail_local - bone.head_local)
    ).normalized()
    projected = normal - direction * normal.dot(direction)
    fallback = Vector(fallback_hint).normalized()
    if projected.length <= 1.0e-7:
        projected = fallback - direction * fallback.dot(direction)
    if projected.length <= 1.0e-7:
        raise ValueError(f"local nail-bed frame degenerate: {bone_name}")
    projected.normalize()
    if projected.dot(fallback) < 0.0:
        projected = -projected
    return tuple(float(value) for value in projected)


def _source_local_fit_frame(
    *,
    body_tree: BVHTree,
    armature: Any,
    bone_name: str,
    alignment_row: Mapping[str, Any],
    fallback_hint: tuple[float, float, float],
) -> dict[str, Any]:
    """Build a local tangent frame at the enrolled source nail-bed center.

    The GLB's imported rest-bone axes are not reliable spatial nail-center
    anchors.  The hashed alignment record remains a location-only reference;
    no source nail vertex, topology, UV, material, or weight is copied.
    """

    source_center = Vector(alignment_row["nail_bounds_m"]["center"])
    digit_center = Vector(alignment_row["digit_bounds_m"]["center"])
    hit, normal, face, distance = body_tree.find_nearest(source_center, 0.020)
    if hit is None or normal is None:
        raise ValueError(f"no local source-center surface for {bone_name}")
    normal.normalize()
    toward_source = source_center - hit
    fallback = Vector(fallback_hint).normalized()
    if toward_source.length > 1.0e-8:
        if normal.dot(toward_source) < 0.0:
            normal = -normal
    elif normal.dot(fallback) < 0.0:
        normal = -normal

    distal_hint = source_center - digit_center
    longitudinal = distal_hint - normal * distal_hint.dot(normal)
    if longitudinal.length <= 1.0e-7:
        bone = armature.data.bones.get(bone_name)
        if bone is None:
            raise ValueError(f"distal bone missing: {bone_name}")
        bone_direction = armature.matrix_world.to_3x3() @ (
            bone.tail_local - bone.head_local
        )
        longitudinal = bone_direction - normal * bone_direction.dot(normal)
    if longitudinal.length <= 1.0e-7:
        raise ValueError(f"source-center longitudinal frame degenerate: {bone_name}")
    longitudinal.normalize()
    if longitudinal.dot(distal_hint) < 0.0:
        longitudinal = -longitudinal
    lateral = normal.cross(longitudinal)
    if lateral.length <= 1.0e-7:
        raise ValueError(f"source-center lateral frame degenerate: {bone_name}")
    lateral.normalize()
    longitudinal = lateral.cross(normal).normalized()
    return {
        "source_center_world_m": [float(value) for value in source_center],
        "digit_center_world_m": [float(value) for value in digit_center],
        "surface_hit_world_m": [float(value) for value in hit],
        "surface_face_index": int(face),
        "source_center_to_surface_distance_m": float(distance),
        "outward_world": [float(value) for value in normal],
        "longitudinal_world": [float(value) for value in longitudinal],
        "lateral_world": [float(value) for value in lateral],
        "frame_source": (
            "hashed_source_nail_center_plus_digit_center_and_nearest_body_normal;"
            "location/frame only; no source nail geometry copied"
        ),
    }


def _distance_to_aabb(point: Vector, low: Vector, high: Vector) -> float:
    delta = Vector(
        tuple(
            max(float(low[axis] - point[axis]), 0.0, float(point[axis] - high[axis]))
            for axis in range(3)
        )
    )
    return float(delta.length)


def _mesh_connected_component_count(mesh: Any) -> int:
    if not mesh.vertices:
        return 0
    adjacency: list[set[int]] = [set() for _vertex in mesh.vertices]
    for edge in mesh.edges:
        first, second = (int(value) for value in edge.vertices)
        adjacency[first].add(second)
        adjacency[second].add(first)
    remaining = set(range(len(mesh.vertices)))
    count = 0
    while remaining:
        count += 1
        stack = [remaining.pop()]
        while stack:
            current = stack.pop()
            neighbors = adjacency[current] & remaining
            remaining.difference_update(neighbors)
            stack.extend(neighbors)
    return count


def _evaluated_digit_binding_record(
    *,
    nail: Any,
    bone_name: str,
    alignment_row: Mapping[str, Any],
    alignment_rows: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = nail.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()
    if not points:
        raise ValueError(f"evaluated shell has no vertices: {nail.name}")
    centroid = sum(points, Vector()) / len(points)
    digit_bounds = alignment_row["digit_bounds_m"]
    low = Vector(digit_bounds["low"])
    high = Vector(digit_bounds["high"])
    padded_low = low - Vector((1.0, 1.0, 1.0)) * BLACKPROJECT_DIGIT_BOUND_PADDING_M
    padded_high = high + Vector((1.0, 1.0, 1.0)) * BLACKPROJECT_DIGIT_BOUND_PADDING_M
    distance_to_digit_bounds = _distance_to_aabb(centroid, low, high)
    inside_padded = all(
        float(padded_low[axis]) <= float(centroid[axis]) <= float(padded_high[axis])
        for axis in range(3)
    )
    center_distances = sorted(
        (
            float(
                (
                    centroid
                    - Vector(other_row["nail_bounds_m"]["center"])
                ).length
            ),
            str(other_bone),
        )
        for other_bone, other_row in alignment_rows.items()
    )
    nearest_center_distance, nearest_center_bone = center_distances[0]
    expected_center = Vector(alignment_row["nail_bounds_m"]["center"])
    expected_center_distance = float((centroid - expected_center).length)
    expected_is_nearest = nearest_center_bone == bone_name
    connected_components = _mesh_connected_component_count(nail.data)
    passed = inside_padded and expected_is_nearest and connected_components == 1
    return {
        "evaluated_shell_centroid_world_m": [float(value) for value in centroid],
        "exact_bound_terminal_bone": bone_name,
        "exact_digit_bounds_low_world_m": [float(value) for value in low],
        "exact_digit_bounds_high_world_m": [float(value) for value in high],
        "digit_bound_padding_m": BLACKPROJECT_DIGIT_BOUND_PADDING_M,
        "evaluated_centroid_distance_to_exact_digit_aabb_m": distance_to_digit_bounds,
        "evaluated_centroid_inside_padded_exact_digit_bounds": inside_padded,
        "evaluated_centroid_to_expected_source_nail_center_m": expected_center_distance,
        "nearest_enrolled_source_nail_center_bone": nearest_center_bone,
        "nearest_enrolled_source_nail_center_distance_m": nearest_center_distance,
        "expected_digit_source_center_is_nearest": expected_is_nearest,
        "generated_top_mesh_connected_component_count": connected_components,
        "exactly_one_connected_generated_shell_for_digit": connected_components == 1,
        "evaluated_centroid_exact_digit_binding_gate_passed": passed,
    }


def _world_bounds(objects: Iterable[Any]) -> dict[str, list[float]]:
    points = [
        obj.matrix_world @ vertex.co
        for obj in objects
        if obj.type == "MESH"
        for vertex in obj.data.vertices
    ]
    if not points:
        raise ValueError("world-bounds input is empty")
    low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    return {
        "low": [float(value) for value in low],
        "high": [float(value) for value in high],
        "size": [float(value) for value in high - low],
        "center": [float(value) for value in (low + high) * 0.5],
    }


def _assign_grid_uvs(mesh: Any, grid: int) -> None:
    uv_layer = mesh.uv_layers.new(name="NaturalNailGridUV")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex_index = int(mesh.loops[loop_index].vertex_index)
            row, column = divmod(vertex_index, grid)
            uv_layer.data[loop_index].uv = (
                column / (grid - 1),
                row / (grid - 1),
            )


def _add_proximal_fade_to_bed_material(material: Any) -> None:
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    principled = nodes.get("Principled BSDF")
    if principled is None:
        raise ValueError("proximal fade requires Principled BSDF")
    base = nail_v3._principled_input(principled, "Base Color")  # noqa: SLF001
    if base is None:
        raise ValueError("proximal fade requires Base Color input")
    texture = nodes.new("ShaderNodeTexCoord")
    texture.name = "Natural_Nail_Grid_UV"
    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.name = "Natural_Nail_Proximal_V"
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.name = "Natural_Nail_Proximal_Fade"
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    proximal = ramp.color_ramp.elements[0]
    proximal.position = 0.0
    proximal.color = component_v1.srgb_hex_to_linear_rgba("#B98280")
    transition = ramp.color_ramp.elements.new(0.24)
    transition.color = component_v1.srgb_hex_to_linear_rgba("#BF7D80")
    bed = ramp.color_ramp.elements.new(0.42)
    bed.color = component_v1.srgb_hex_to_linear_rgba(
        str(BLACKPROJECT_NAIL_BED_MATERIAL["srgb_hex"])
    )
    links.new(texture.outputs["UV"], separate.inputs["Vector"])
    links.new(separate.outputs["Y"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], base)
    material["generated_uv_proximal_fade"] = True


def _evaluated_world_bvh(obj: Any) -> tuple[BVHTree, int, int]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        triangles = [
            tuple(int(value) for value in triangle.vertices)
            for triangle in mesh.loop_triangles
        ]
        return (
            BVHTree.FromPolygons(points, triangles, all_triangles=True),
            len(points),
            len(triangles),
        )
    finally:
        evaluated.to_mesh_clear()


def _world_triangle_data(
    obj: Any,
    *,
    evaluated: bool,
) -> tuple[list[Vector], list[tuple[int, int, int]]]:
    if evaluated:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated_obj = obj.evaluated_get(depsgraph)
        mesh = evaluated_obj.to_mesh()
        matrix = evaluated_obj.matrix_world
    else:
        evaluated_obj = None
        mesh = obj.data
        matrix = obj.matrix_world
    try:
        mesh.calc_loop_triangles()
        return (
            [matrix @ vertex.co for vertex in mesh.vertices],
            [
                tuple(int(value) for value in triangle.vertices)
                for triangle in mesh.loop_triangles
            ],
        )
    finally:
        if evaluated_obj is not None:
            evaluated_obj.to_mesh_clear()


def _exact_mesh_pair_intersections(
    body: Any,
    nail: Any,
    *,
    evaluated: bool,
) -> dict[str, Any]:
    body_points, body_triangles = _world_triangle_data(body, evaluated=evaluated)
    nail_points, nail_triangles = _world_triangle_data(nail, evaluated=evaluated)
    body_bvh = BVHTree.FromPolygons(
        body_points,
        body_triangles,
        all_triangles=True,
        epsilon=0.0,
    )
    nail_bvh = BVHTree.FromPolygons(
        nail_points,
        nail_triangles,
        all_triangles=True,
        epsilon=0.0,
    )
    broad_pairs = sorted(body_bvh.overlap(nail_bvh))
    all_points = body_points + nail_points
    low = Vector(tuple(min(point[axis] for point in all_points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in all_points) for axis in range(3)))
    tolerance = max(1.0e-10, float((high - low).length) * 1.0e-8)
    counts: dict[str, int] = {}
    genuine_pairs = []
    for body_index, nail_index in broad_pairs:
        first = [body_points[index] for index in body_triangles[body_index]]
        second = [nail_points[index] for index in nail_triangles[nail_index]]
        result = classify_triangle_pair(
            first,
            second,
            linear_tolerance=tolerance,
        )
        classification = str(result["classification"])
        counts[classification] = counts.get(classification, 0) + 1
        if result.get("genuine_penetration") is True:
            genuine_pairs.append([int(body_index), int(nail_index)])
    return {
        "broad_phase_candidate_pair_count": len(broad_pairs),
        "narrow_phase_classification_counts": counts,
        "exact_genuine_penetration_pair_count": len(genuine_pairs),
        "exact_genuine_penetration_pairs": genuine_pairs,
        "linear_tolerance_m": tolerance,
        "broad_phase_is_not_used_as_the_pass_gate": True,
    }


def _evaluated_clearance_and_overlap(
    body: Any,
    body_tree: BVHTree,
    nail: Any,
) -> dict[str, Any]:
    del body_tree  # Evaluated geometry must be compared in one evaluated space.
    evaluated_body_tree, evaluated_body_vertex_count, evaluated_body_triangle_count = (
        _evaluated_world_bvh(body)
    )
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = nail.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        triangles = [
            tuple(int(value) for value in triangle.vertices)
            for triangle in mesh.loop_triangles
        ]
        nail_tree = BVHTree.FromPolygons(points, triangles, all_triangles=True)
        distances = []
        for point in points:
            nearest = evaluated_body_tree.find_nearest(point)
            if nearest[0] is None:
                raise ValueError(f"evaluated clearance query failed: {nail.name}")
            distances.append(float(nearest[3]))
        broad_overlaps = evaluated_body_tree.overlap(nail_tree)
        exact = _exact_mesh_pair_intersections(body, nail, evaluated=True)
        return {
            "evaluated_vertex_count": len(points),
            "evaluated_triangle_count": len(triangles),
            "evaluated_body_vertex_count": evaluated_body_vertex_count,
            "evaluated_body_triangle_count": evaluated_body_triangle_count,
            "evaluated_distance_comparison_space": (
                "evaluated_nail_against_evaluated_body"
            ),
            "evaluated_minimum_unsigned_body_surface_clearance_m": min(distances),
            "evaluated_maximum_unsigned_body_surface_clearance_m": max(distances),
            "evaluated_broad_phase_candidate_pair_count": len(broad_overlaps),
            "evaluated_exact_intersections": exact,
            "evaluated_body_surface_triangle_overlap_count": int(
                exact["exact_genuine_penetration_pair_count"]
            ),
            "evaluated_solidified_plate_has_no_body_overlap": (
                int(exact["exact_genuine_penetration_pair_count"]) == 0
            ),
        }
    finally:
        evaluated.to_mesh_clear()


def _evaluated_top_source_recess_clearance(
    *,
    body: Any,
    nail: Any,
    grid: int,
    source_component_frame: Mapping[str, Any],
) -> dict[str, Any]:
    """Measure the armature-evaluated top shell before thickness/bevel."""

    disabled: list[tuple[Any, bool, bool]] = []
    for modifier in nail.modifiers:
        if modifier.type in {"SOLIDIFY", "BEVEL"}:
            disabled.append(
                (
                    modifier,
                    bool(modifier.show_viewport),
                    bool(modifier.show_render),
                )
            )
            modifier.show_viewport = False
            modifier.show_render = False
    try:
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        depsgraph.update()
        body_tree, _body_vertices, _body_triangles = _evaluated_world_bvh(body)
        evaluated = nail.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        finally:
            evaluated.to_mesh_clear()
        if len(points) != grid * grid:
            raise ValueError(
                f"evaluated top shell vertex count mismatch: {nail.name}={len(points)}"
            )
        distances: list[float] = []
        for point in points:
            nearest = body_tree.find_nearest(point, 0.010)
            if nearest[0] is None:
                raise ValueError(
                    f"evaluated top source-recess query failed: {nail.name}"
                )
            distances.append(float(nearest[3]))
        perimeter_indices = _perimeter_vertex_indices(grid)
        perimeter = [distances[index] for index in perimeter_indices]
        close_count = sum(
            value <= BLACKPROJECT_RECESS_CLOSE_PERIMETER_THRESHOLD_M
            for value in perimeter
        )
        source_baseline = source_component_frame[
            "source_component_to_body_distance_m"
        ]
        source_maximum = float(source_baseline["maximum"])
        maximum_allowed_gap = max(
            BLACKPROJECT_RECESS_MAXIMUM_CENTER_GAP_M,
            source_maximum + 0.00075,
        )
        minimum_close_fraction = max(
            0.08,
            min(
                BLACKPROJECT_RECESS_MINIMUM_CLOSE_PERIMETER_FRACTION,
                float(source_baseline["close_sample_fraction"]) * 0.50,
            ),
        )
        record = {
            "clearance_contract": (
                "evaluated_blackproject_open_nail_recess_perimeter_attachment_v1"
            ),
            "evaluated_top_vertex_count": len(points),
            "minimum_unsigned_body_surface_clearance_m": min(distances),
            "maximum_unsigned_body_surface_clearance_m": max(distances),
            "perimeter_vertex_count": len(perimeter_indices),
            "minimum_perimeter_clearance_m": min(perimeter),
            "maximum_perimeter_clearance_m": max(perimeter),
            "mean_perimeter_clearance_m": sum(perimeter) / len(perimeter),
            "close_perimeter_vertex_count": close_count,
            "close_perimeter_fraction": close_count / len(perimeter),
            "close_perimeter_threshold_m": (
                BLACKPROJECT_RECESS_CLOSE_PERIMETER_THRESHOLD_M
            ),
            "minimum_required_close_perimeter_fraction": minimum_close_fraction,
            "maximum_allowed_perimeter_clearance_m": maximum_allowed_gap,
            "maximum_allowed_center_recess_gap_m": maximum_allowed_gap,
            "source_component_body_distance_baseline": dict(source_baseline),
            "source_native_maximum_gap_margin_m": 0.00075,
            "whole_surface_v3_maximum_not_used_because_source_has_open_recess": True,
        }
        record["evaluated_top_source_recess_clearance_gate_passed"] = (
            _source_recess_clearance_passed(record)
        )
        return record
    finally:
        for modifier, show_viewport, show_render in disabled:
            modifier.show_viewport = show_viewport
            modifier.show_render = show_render
        bpy.context.view_layer.update()
        bpy.context.evaluated_depsgraph_get().update()


def _analytic_curved_oval_fallback(
    *,
    name: str,
    body: Any,
    body_tree: BVHTree,
    source_center_world: Vector,
    longitudinal_hint: Vector,
    outward_hint: Vector,
    length_m: float,
    width_m: float,
    grid: int,
    faces: list[tuple[int, int, int, int]],
    bed_material: Any,
    free_edge_material: Any,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Fit a bounded generated curved oval when coherent rays miss a rolled digit.

    This fallback uses the hashed source component only as a center anchor.  It
    creates every vertex analytically from the nearest body-surface point and
    a local tangent frame; no source nail vertex, face, UV, material, weight,
    or shape is copied.
    """

    center_hit, center_normal, center_face, center_distance = body_tree.find_nearest(
        source_center_world,
        0.020,
    )
    if center_hit is None or center_normal is None:
        return None, [
            {
                "method": "analytic_curved_oval_from_local_body_surface",
                "fit_passed": False,
                "failure_reason": "local_surface_anchor_missing",
            }
        ]
    center_normal.normalize()
    toward_source = source_center_world - center_hit
    if toward_source.length > 1.0e-8 and center_normal.dot(toward_source) < 0.0:
        center_normal = -center_normal
    if center_normal.dot(outward_hint) < 0.0:
        center_normal = -center_normal

    longitudinal = longitudinal_hint - center_normal * longitudinal_hint.dot(
        center_normal
    )
    if longitudinal.length <= 1.0e-8:
        return None, [
            {
                "method": "analytic_curved_oval_from_local_body_surface",
                "fit_passed": False,
                "failure_reason": "local_longitudinal_tangent_degenerate",
            }
        ]
    longitudinal.normalize()
    if longitudinal.dot(longitudinal_hint) < 0.0:
        longitudinal = -longitudinal
    lateral = center_normal.cross(longitudinal)
    if lateral.length <= 1.0e-8:
        return None, [
            {
                "method": "analytic_curved_oval_from_local_body_surface",
                "fit_passed": False,
                "failure_reason": "local_lateral_tangent_degenerate",
            }
        ]
    lateral.normalize()

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(0.0, 0.0, 0.0)] * (grid * grid), [], faces)
    mesh.update(calc_edges=True)
    _assign_grid_uvs(mesh, grid)
    nail = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(nail)
    mesh.materials.append(bed_material)
    mesh.materials.append(free_edge_material)
    free_edge_face_count = 0
    for polygon in mesh.polygons:
        polygon.use_smooth = True
        face_row = int(polygon.index) // (grid - 1)
        polygon.material_index = (
            1 if nail_v3.is_free_edge_face_row(face_row, grid) else 0
        )
        free_edge_face_count += int(polygon.material_index == 1)

    trials: list[dict[str, Any]] = []
    accepted: dict[str, Any] | None = None
    for footprint_scale in ANALYTIC_FOOTPRINT_SCALE_CANDIDATES:
        if accepted is not None:
            break
        for longitudinal_radius in ANALYTIC_LONGITUDINAL_RADIUS_M:
            if accepted is not None:
                break
            for lateral_radius in ANALYTIC_LATERAL_RADIUS_M:
                if accepted is not None:
                    break
                base_points: list[Vector] = []
                for row in range(grid):
                    for column in range(grid):
                        along, across, _across_fraction = (
                            _rounded_outline_coordinates(
                                row=row,
                                column=column,
                                grid=grid,
                                length_m=length_m,
                                width_m=width_m,
                                footprint_scale=footprint_scale,
                            )
                        )
                        inward_curve = (
                            (along * along) / (2.0 * longitudinal_radius)
                            + (across * across) / (2.0 * lateral_radius)
                        )
                        base_points.append(
                            center_hit
                            + longitudinal * along
                            + lateral * across
                            - center_normal * inward_curve
                        )
                locality = _grid_locality_record(
                    points=base_points,
                    nominal_center=center_hit,
                    longitudinal=longitudinal,
                    lateral=lateral,
                    length_m=length_m,
                    width_m=width_m,
                    footprint_scale=footprint_scale,
                    grid=grid,
                )
                if locality["locality_gate_passed"] is not True:
                    trials.append(
                        {
                            "method": "analytic_curved_oval_from_local_body_surface",
                            "footprint_scale": float(footprint_scale),
                            "longitudinal_radius_m": float(longitudinal_radius),
                            "lateral_radius_m": float(lateral_radius),
                            "fit_passed": False,
                            "failure_reason": "generated_grid_locality_failed",
                            "grid_locality": locality,
                        }
                    )
                    continue
                for lift in ANALYTIC_CLEARANCE_LIFT_M:
                    points = [point + center_normal * lift for point in base_points]
                    distances: list[float] = []
                    nearest_failed = False
                    for point in points:
                        nearest = body_tree.find_nearest(point, 0.004)
                        if nearest[0] is None:
                            nearest_failed = True
                            break
                        distances.append(float(nearest[3]))
                    trial: dict[str, Any] = {
                        "method": "analytic_curved_oval_from_local_body_surface",
                        "footprint_scale": float(footprint_scale),
                        "longitudinal_radius_m": float(longitudinal_radius),
                        "lateral_radius_m": float(lateral_radius),
                        "uniform_outward_lift_m": float(lift),
                        "nearest_query_complete": not nearest_failed,
                        "grid_locality": locality,
                    }
                    if nearest_failed:
                        trial["fit_passed"] = False
                        trial["failure_reason"] = "nearest_surface_query_failed"
                        trials.append(trial)
                        continue
                    minimum_clearance = min(distances)
                    maximum_clearance = max(distances)
                    trial.update(
                        {
                            "minimum_unsigned_body_surface_clearance_m": minimum_clearance,
                            "maximum_unsigned_body_surface_clearance_m": maximum_clearance,
                        }
                    )
                    if (
                        minimum_clearance < MINIMUM_SURFACE_CLEARANCE_M
                        or maximum_clearance > nail_v3.MAXIMUM_SURFACE_CLEARANCE_M
                    ):
                        trial["fit_passed"] = False
                        trial["failure_reason"] = "strict_v3_clearance_window_failed"
                        trials.append(trial)
                        continue
                    for vertex, point in zip(nail.data.vertices, points):
                        vertex.co = point
                    nail.data.update()
                    winding = _top_surface_winding_record(nail, center_normal)
                    trial["top_surface_winding"] = winding
                    if winding["all_top_surface_faces_outward"] is not True:
                        trial["fit_passed"] = False
                        trial["failure_reason"] = "non_outward_or_folded_top_surface"
                        trials.append(trial)
                        continue
                    exact_intersections = _exact_mesh_pair_intersections(
                        body,
                        nail,
                        evaluated=False,
                    )
                    overlap_count = int(
                        exact_intersections["exact_genuine_penetration_pair_count"]
                    )
                    trial.update(
                        {
                            "exact_intersections": exact_intersections,
                            "body_surface_triangle_overlap_count": overlap_count,
                            "fit_passed": overlap_count == 0,
                            "failure_reason": (
                                "" if overlap_count == 0 else "exact_surface_intersection"
                            ),
                        }
                    )
                    trials.append(trial)
                    if overlap_count != 0:
                        continue
                    clearance = {
                        "minimum_unsigned_body_surface_clearance_m": minimum_clearance,
                        "maximum_unsigned_body_surface_clearance_m": maximum_clearance,
                        "body_surface_triangle_overlap_count": 0,
                    }
                    validate_clearance_measurement(
                        minimum_m=minimum_clearance,
                        maximum_m=maximum_clearance,
                        overlap_count=0,
                    )
                    accepted = {
                        "nail": nail,
                        "clearance": clearance,
                        "overlap_count": 0,
                        "footprint_scale": float(footprint_scale),
                        "center_offset_fraction": 0.0,
                        "lateral_offset_fraction": 0.0,
                        "minimum_alignment": float(center_normal.dot(outward_hint)),
                        "lift_iteration": 0,
                        "changed_vertex_count": 0,
                        "maximum_local_lift": float(lift),
                        "free_edge_face_count": free_edge_face_count,
                        "initial_clearance": dict(clearance),
                        "initial_overlap_count": 0,
                        "broad_overlap_count": int(
                            exact_intersections["broad_phase_candidate_pair_count"]
                        ),
                        "exact_intersections": exact_intersections,
                        "projection_query_mode": (
                            "analytic_curved_oval_from_nearest_local_body_surface"
                        ),
                        "center_mode": "analytic_local_surface_anchor",
                        "center_fraction_from_terminal": None,
                        "analytic_surface_anchor": {
                            "center_hit_world_m": [float(value) for value in center_hit],
                            "center_normal_world": [
                                float(value) for value in center_normal
                            ],
                            "center_face_index": int(center_face),
                            "source_center_to_surface_distance_m": float(
                                center_distance
                            ),
                        },
                        "analytic_curvature": {
                            "longitudinal_radius_m": float(longitudinal_radius),
                            "lateral_radius_m": float(lateral_radius),
                            "uniform_outward_lift_m": float(lift),
                        },
                        "measurement_longitudinal_world": [
                            float(value) for value in longitudinal
                        ],
                        "measurement_lateral_world": [
                            float(value) for value in lateral
                        ],
                        "grid_locality": locality,
                        "top_surface_winding": winding,
                    }
                    break
    if accepted is None:
        nail_v3._remove_object_and_mesh(nail)  # noqa: SLF001
    return accepted, trials


def _nearest_surface_conformal_fallback(
    *,
    name: str,
    body: Any,
    body_tree: BVHTree,
    anchor_world: Vector,
    longitudinal_hint: Vector,
    outward_hint: Vector,
    length_m: float,
    width_m: float,
    grid: int,
    faces: list[tuple[int, int, int, int]],
    bed_material: Any,
    free_edge_material: Any,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Generate a dense oval directly from one coherent local body surface."""

    center_hit, center_normal, center_face, center_distance = body_tree.find_nearest(
        anchor_world,
        0.020,
    )
    if center_hit is None or center_normal is None:
        return None, [
            {
                "method": "nearest_local_surface_conformal_oval",
                "fit_passed": False,
                "failure_reason": "local_surface_anchor_missing",
            }
        ]
    center_normal.normalize()
    toward_anchor = anchor_world - center_hit
    if toward_anchor.length > 1.0e-8 and center_normal.dot(toward_anchor) < 0.0:
        center_normal = -center_normal
    if center_normal.dot(outward_hint) < 0.0:
        center_normal = -center_normal
    longitudinal = longitudinal_hint - center_normal * longitudinal_hint.dot(
        center_normal
    )
    if longitudinal.length <= 1.0e-8:
        return None, [
            {
                "method": "nearest_local_surface_conformal_oval",
                "fit_passed": False,
                "failure_reason": "local_longitudinal_tangent_degenerate",
            }
        ]
    longitudinal.normalize()
    if longitudinal.dot(longitudinal_hint) < 0.0:
        longitudinal = -longitudinal
    lateral = center_normal.cross(longitudinal).normalized()
    attempts: list[dict[str, Any]] = []
    for footprint_scale in (0.88, 0.80, 0.72, 0.64, 0.58, 0.54, 0.50):
        hits: list[Vector] = []
        normals: list[Vector] = []
        base_clearances: list[float] = []
        complete = True
        failure_reason = ""
        minimum_alignment = 1.0
        maximum_query_distance = 0.0
        for row in range(grid):
            for column in range(grid):
                along, across, across_fraction = _rounded_outline_coordinates(
                    row=row,
                    column=column,
                    grid=grid,
                    length_m=length_m,
                    width_m=width_m,
                    footprint_scale=footprint_scale,
                )
                expected = center_hit + longitudinal * along + lateral * across
                hit, normal, _face, distance = body_tree.find_nearest(
                    expected,
                    0.004,
                )
                if hit is None or normal is None:
                    complete = False
                    failure_reason = f"nearest_surface_miss_{row}_{column}"
                    break
                maximum_query_distance = max(maximum_query_distance, float(distance))
                if normal.dot(center_normal) < 0.0:
                    normal = -normal
                normal.normalize()
                alignment = float(normal.dot(center_normal))
                minimum_alignment = min(minimum_alignment, alignment)
                if alignment < nail_v3.MINIMUM_OUTWARD_NORMAL_ALIGNMENT:
                    complete = False
                    failure_reason = f"local_surface_discontinuity_{row}_{column}"
                    break
                transverse_arch = 1.0 - min(1.0, abs(across_fraction) * 2.0) ** 2
                hits.append(hit.copy())
                normals.append(normal.copy())
                base_clearances.append(
                    0.000055
                    + BLACKPROJECT_BEVEL_CLEARANCE_COMPENSATION_M
                    + 0.000055 * transverse_arch
                )
            if not complete:
                break
        attempt: dict[str, Any] = {
            "method": "nearest_local_surface_conformal_oval",
            "footprint_scale": float(footprint_scale),
            "projection_complete": complete,
            "projected_sample_count": len(hits),
            "minimum_local_normal_alignment": minimum_alignment,
            "maximum_nearest_query_distance_m": maximum_query_distance,
            "failure_reason": failure_reason,
        }
        if not complete:
            attempt["fit_passed"] = False
            attempts.append(attempt)
            continue

        locality = _grid_locality_record(
            points=hits,
            nominal_center=center_hit,
            longitudinal=longitudinal,
            lateral=lateral,
            length_m=length_m,
            width_m=width_m,
            footprint_scale=footprint_scale,
            grid=grid,
        )
        attempt["grid_locality"] = locality
        if locality["locality_gate_passed"] is not True:
            attempt["fit_passed"] = False
            attempt["failure_reason"] = "generated_grid_locality_failed"
            attempts.append(attempt)
            continue

        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(
            [
                tuple(hit + normal * clearance)
                for hit, normal, clearance in zip(hits, normals, base_clearances)
            ],
            [],
            faces,
        )
        mesh.update(calc_edges=True)
        _assign_grid_uvs(mesh, grid)
        nail = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(nail)
        mesh.materials.append(bed_material)
        mesh.materials.append(free_edge_material)
        free_edge_face_count = 0
        for polygon in mesh.polygons:
            polygon.use_smooth = True
            face_row = int(polygon.index) // (grid - 1)
            polygon.material_index = (
                1 if nail_v3.is_free_edge_face_row(face_row, grid) else 0
            )
            free_edge_face_count += int(polygon.material_index == 1)

        winding = _top_surface_winding_record(nail, center_normal)
        attempt["top_surface_winding"] = winding
        if winding["all_top_surface_faces_outward"] is not True:
            attempt["fit_passed"] = False
            attempt["failure_reason"] = "non_outward_or_folded_top_surface"
            attempts.append(attempt)
            nail_v3._remove_object_and_mesh(nail)  # noqa: SLF001
            continue

        accepted_lift = -1
        final_clearance: dict[str, Any] | None = None
        final_exact: dict[str, Any] | None = None
        final_broad = -1
        initial_clearance: dict[str, Any] | None = None
        initial_overlap_count = -1
        for lift_iteration in range(BLACKPROJECT_LOCAL_LIFT_MAXIMUM_ITERATIONS + 1):
            additional_lift = lift_iteration * nail_v3.NORMAL_LIFT_STEP_M
            for vertex, hit, normal, base_clearance in zip(
                nail.data.vertices,
                hits,
                normals,
                base_clearances,
            ):
                vertex.co = hit + normal * (base_clearance + additional_lift)
            nail.data.update()
            final_clearance = component_v1._body_clearance_record(  # noqa: SLF001
                body_tree,
                [nail],
            )
            if (
                float(final_clearance["maximum_unsigned_body_surface_clearance_m"])
                > nail_v3.MAXIMUM_SURFACE_CLEARANCE_M
            ):
                break
            final_exact = _exact_mesh_pair_intersections(
                body,
                nail,
                evaluated=False,
            )
            final_broad = int(final_exact["broad_phase_candidate_pair_count"])
            overlap_count = int(
                final_exact["exact_genuine_penetration_pair_count"]
            )
            if lift_iteration == 0:
                initial_clearance = dict(final_clearance)
                initial_overlap_count = overlap_count
            try:
                validate_clearance_measurement(
                    minimum_m=float(
                        final_clearance[
                            "minimum_unsigned_body_surface_clearance_m"
                        ]
                    ),
                    maximum_m=float(
                        final_clearance[
                            "maximum_unsigned_body_surface_clearance_m"
                        ]
                    ),
                    overlap_count=overlap_count,
                )
            except ValueError:
                continue
            accepted_lift = lift_iteration
            break
        attempt.update(
            {
                "final_clearance": final_clearance,
                "exact_intersections": final_exact,
                "adaptive_uniform_lift_iteration_count": max(0, accepted_lift),
                "fit_passed": accepted_lift >= 0,
            }
        )
        attempts.append(attempt)
        if accepted_lift >= 0 and final_clearance is not None and final_exact is not None:
            return (
                {
                    "nail": nail,
                    "clearance": final_clearance,
                    "overlap_count": 0,
                    "footprint_scale": float(footprint_scale),
                    "center_mode": "nearest_local_surface_terminal_anchor",
                    "center_fraction_from_terminal": 0.64,
                    "center_offset_fraction": 0.0,
                    "lateral_offset_fraction": 0.0,
                    "minimum_alignment": minimum_alignment,
                    "lift_iteration": accepted_lift,
                    "changed_vertex_count": 0,
                    "maximum_local_lift": accepted_lift
                    * nail_v3.NORMAL_LIFT_STEP_M,
                    "free_edge_face_count": free_edge_face_count,
                    "initial_clearance": initial_clearance,
                    "initial_overlap_count": initial_overlap_count,
                    "broad_overlap_count": final_broad,
                    "exact_intersections": final_exact,
                    "projection_query_mode": (
                        "nearest_local_body_surface_conformal_oval"
                    ),
                    "analytic_surface_anchor": {
                        "center_hit_world_m": [float(value) for value in center_hit],
                        "center_normal_world": [
                            float(value) for value in center_normal
                        ],
                        "center_face_index": int(center_face),
                        "anchor_to_surface_distance_m": float(center_distance),
                    },
                    "analytic_curvature": None,
                    "measurement_longitudinal_world": [
                        float(value) for value in longitudinal
                    ],
                    "measurement_lateral_world": [
                        float(value) for value in lateral
                    ],
                    "grid_locality": locality,
                    "top_surface_winding": winding,
                },
                attempts,
            )
        nail_v3._remove_object_and_mesh(nail)  # noqa: SLF001
    return None, attempts


def _perimeter_vertex_indices(grid: int) -> list[int]:
    return sorted(
        {
            row * grid + column
            for row in range(grid)
            for column in range(grid)
            if row in {0, grid - 1} or column in {0, grid - 1}
        }
    )


def _source_recess_clearance_record(
    *,
    body_tree: BVHTree,
    nail: Any,
    grid: int,
    source_component_frame: Mapping[str, Any],
) -> dict[str, Any]:
    points = [nail.matrix_world @ vertex.co for vertex in nail.data.vertices]
    distances: list[float] = []
    for point in points:
        nearest = body_tree.find_nearest(point, 0.010)
        if nearest[0] is None:
            raise ValueError(f"source-recess clearance query failed: {nail.name}")
        distances.append(float(nearest[3]))
    perimeter_indices = _perimeter_vertex_indices(grid)
    perimeter = [distances[index] for index in perimeter_indices]
    close_count = sum(
        value <= BLACKPROJECT_RECESS_CLOSE_PERIMETER_THRESHOLD_M
        for value in perimeter
    )
    close_fraction = close_count / len(perimeter)
    source_baseline = source_component_frame["source_component_to_body_distance_m"]
    source_maximum = float(source_baseline["maximum"])
    maximum_allowed_gap = max(
        BLACKPROJECT_RECESS_MAXIMUM_CENTER_GAP_M,
        source_maximum + 0.00075,
    )
    minimum_close_fraction = max(
        0.08,
        min(
            BLACKPROJECT_RECESS_MINIMUM_CLOSE_PERIMETER_FRACTION,
            float(source_baseline["close_sample_fraction"]) * 0.50,
        ),
    )
    return {
        "clearance_contract": "blackproject_open_nail_recess_perimeter_attachment_v1",
        "minimum_unsigned_body_surface_clearance_m": min(distances),
        "maximum_unsigned_body_surface_clearance_m": max(distances),
        "perimeter_vertex_count": len(perimeter_indices),
        "minimum_perimeter_clearance_m": min(perimeter),
        "maximum_perimeter_clearance_m": max(perimeter),
        "mean_perimeter_clearance_m": sum(perimeter) / len(perimeter),
        "close_perimeter_vertex_count": close_count,
        "close_perimeter_fraction": close_fraction,
        "close_perimeter_threshold_m": BLACKPROJECT_RECESS_CLOSE_PERIMETER_THRESHOLD_M,
        "minimum_required_close_perimeter_fraction": minimum_close_fraction,
        "maximum_allowed_perimeter_clearance_m": maximum_allowed_gap,
        "maximum_allowed_center_recess_gap_m": maximum_allowed_gap,
        "source_component_body_distance_baseline": dict(source_baseline),
        "source_native_maximum_gap_margin_m": 0.00075,
        "whole_surface_v3_maximum_not_used_because_source_has_open_recess": True,
        "top_surface_minimum_clearance_includes_bevel_compensation_m": (
            BLACKPROJECT_RECESS_TOP_MINIMUM_CLEARANCE_M
        ),
    }


def _source_recess_clearance_passed(record: Mapping[str, Any]) -> bool:
    return (
        float(record["minimum_unsigned_body_surface_clearance_m"])
        >= BLACKPROJECT_RECESS_TOP_MINIMUM_CLEARANCE_M
        and float(record["maximum_unsigned_body_surface_clearance_m"])
        <= float(record["maximum_allowed_center_recess_gap_m"])
        and float(record["maximum_perimeter_clearance_m"])
        <= float(record["maximum_allowed_perimeter_clearance_m"])
        and float(record["close_perimeter_fraction"])
        >= float(record["minimum_required_close_perimeter_fraction"])
    )


def _source_component_recess_shell(
    *,
    name: str,
    body: Any,
    body_tree: BVHTree,
    source_component_frame: Mapping[str, Any],
    nominal_length_m: float,
    nominal_width_m: float,
    grid: int,
    faces: list[tuple[int, int, int, int]],
    bed_material: Any,
    free_edge_material: Any,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Generate one rounded shell across a source-native open nail recess."""

    anchor = Vector(source_component_frame["component_centroid_world_m"])
    outward = Vector(source_component_frame["outward_world"]).normalized()
    longitudinal = Vector(
        source_component_frame["longitudinal_world"]
    ).normalized()
    lateral = Vector(source_component_frame["lateral_world"]).normalized()
    measured_length = float(source_component_frame["measured_longitudinal_span_m"])
    measured_width = float(source_component_frame["measured_lateral_span_m"])
    target_length = max(nominal_length_m, measured_length * 0.86)
    target_width = max(nominal_width_m, measured_width * 0.90)

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(0.0, 0.0, 0.0)] * (grid * grid), [], faces)
    mesh.update(calc_edges=True)
    _assign_grid_uvs(mesh, grid)
    nail = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(nail)
    mesh.materials.append(bed_material)
    mesh.materials.append(free_edge_material)
    free_edge_face_count = 0
    for polygon in mesh.polygons:
        polygon.use_smooth = True
        face_row = int(polygon.index) // (grid - 1)
        polygon.material_index = (
            1 if nail_v3.is_free_edge_face_row(face_row, grid) else 0
        )
        free_edge_face_count += int(polygon.material_index == 1)

    attempts: list[dict[str, Any]] = []
    for footprint_scale in BLACKPROJECT_SOURCE_SPAN_SCALE_CANDIDATES:
        base_points: list[Vector] = []
        for row in range(grid):
            row_fraction = row / (grid - 1)
            longitudinal_arch = 1.0 - min(1.0, abs(row_fraction - 0.5) * 2.0) ** 2
            for column in range(grid):
                along, across, across_fraction = _rounded_outline_coordinates(
                    row=row,
                    column=column,
                    grid=grid,
                    length_m=target_length,
                    width_m=target_width,
                    footprint_scale=footprint_scale,
                )
                transverse_arch = 1.0 - min(
                    1.0, abs(across_fraction) * 2.0
                ) ** 2
                arch = 0.000055 * longitudinal_arch + 0.000220 * transverse_arch
                base_points.append(
                    anchor
                    + longitudinal * along
                    + lateral * across
                    + outward * arch
                )
        locality = _grid_locality_record(
            points=base_points,
            nominal_center=anchor,
            longitudinal=longitudinal,
            lateral=lateral,
            length_m=target_length,
            width_m=target_width,
            footprint_scale=footprint_scale,
            grid=grid,
        )
        if locality["locality_gate_passed"] is not True:
            attempts.append(
                {
                    "method": "source_component_pca_parametric_recess_shell",
                    "footprint_scale": float(footprint_scale),
                    "fit_passed": False,
                    "failure_reason": "generated_grid_locality_failed",
                    "grid_locality": locality,
                }
            )
            continue
        for lift_index, uniform_lift in enumerate(
            BLACKPROJECT_RECESS_LIFT_CANDIDATES_M
        ):
            points = [point + outward * uniform_lift for point in base_points]
            for vertex, point in zip(nail.data.vertices, points):
                vertex.co = point
            nail.data.update()
            winding = _top_surface_winding_record(nail, outward)
            clearance = _source_recess_clearance_record(
                body_tree=body_tree,
                nail=nail,
                grid=grid,
                source_component_frame=source_component_frame,
            )
            attempt: dict[str, Any] = {
                "method": "source_component_pca_parametric_recess_shell",
                "footprint_scale": float(footprint_scale),
                "uniform_outward_lift_m": float(uniform_lift),
                "lift_candidate_index": int(lift_index),
                "generated_target_length_m": target_length,
                "generated_target_width_m": target_width,
                "grid_locality": locality,
                "top_surface_winding": winding,
                "source_recess_clearance": clearance,
            }
            if winding["all_top_surface_faces_outward"] is not True:
                attempt["fit_passed"] = False
                attempt["failure_reason"] = "non_outward_or_folded_top_surface"
                attempts.append(attempt)
                continue
            if not _source_recess_clearance_passed(clearance):
                attempt["fit_passed"] = False
                attempt["failure_reason"] = "source_recess_perimeter_clearance_failed"
                attempts.append(attempt)
                continue
            exact = _exact_mesh_pair_intersections(body, nail, evaluated=False)
            overlap_count = int(exact["exact_genuine_penetration_pair_count"])
            attempt["exact_intersections"] = exact
            attempt["body_surface_triangle_overlap_count"] = overlap_count
            attempt["fit_passed"] = overlap_count == 0
            attempt["failure_reason"] = (
                "" if overlap_count == 0 else "exact_surface_intersection"
            )
            attempts.append(attempt)
            if overlap_count != 0:
                continue
            return (
                {
                    "nail": nail,
                    "clearance": {
                        "minimum_unsigned_body_surface_clearance_m": float(
                            clearance["minimum_unsigned_body_surface_clearance_m"]
                        ),
                        "maximum_unsigned_body_surface_clearance_m": float(
                            clearance["maximum_unsigned_body_surface_clearance_m"]
                        ),
                        "body_surface_triangle_overlap_count": 0,
                    },
                    "overlap_count": 0,
                    "footprint_scale": float(footprint_scale),
                    "center_mode": "excluded_source_component_pca_centroid_measurement",
                    "center_fraction_from_terminal": None,
                    "center_offset_fraction": 0.0,
                    "lateral_offset_fraction": 0.0,
                    "minimum_alignment": float(
                        winding["minimum_outward_face_normal_alignment"]
                    ),
                    "lift_iteration": int(lift_index),
                    "changed_vertex_count": 0,
                    "maximum_local_lift": float(uniform_lift),
                    "free_edge_face_count": free_edge_face_count,
                    "initial_clearance": dict(clearance),
                    "initial_overlap_count": 0,
                    "broad_overlap_count": int(
                        exact["broad_phase_candidate_pair_count"]
                    ),
                    "exact_intersections": exact,
                    "grid_locality": locality,
                    "top_surface_winding": winding,
                    "source_recess_clearance": clearance,
                    "projection_query_mode": (
                        "source_component_pca_parametric_open_recess_shell"
                    ),
                    "analytic_surface_anchor": {
                        "component_centroid_world_m": [
                            float(value) for value in anchor
                        ],
                        "source_measurement_only": True,
                    },
                    "analytic_curvature": {
                        "maximum_transverse_arch_m": 0.000220,
                        "maximum_longitudinal_arch_m": 0.000055,
                        "uniform_outward_lift_m": float(uniform_lift),
                    },
                    "measurement_longitudinal_world": [
                        float(value) for value in longitudinal
                    ],
                    "measurement_lateral_world": [
                        float(value) for value in lateral
                    ],
                    "generated_target_length_m": target_length,
                    "generated_target_width_m": target_width,
                },
                attempts,
            )
    nail_v3._remove_object_and_mesh(nail)  # noqa: SLF001
    return None, attempts


def _projected_blackproject_oval_nail_plate(
    *,
    name: str,
    nail_id: str,
    body: Any,
    body_tree: BVHTree,
    armature: Any,
    bone_name: str,
    outward_hint: tuple[float, float, float],
    longitudinal_hint: tuple[float, float, float],
    source_center_world: Vector,
    source_component_frame: Mapping[str, Any],
    length_m: float,
    width_m: float,
    target_height_m: float,
    bed_material: Any,
    free_edge_material: Any,
) -> tuple[Any, dict[str, Any]]:
    """Use the v3 shell method with a hashed BlackProject fit-center anchor."""

    bone = armature.data.bones.get(bone_name)
    if bone is None:
        raise nail_v3.NaturalNailDeliveryV3Error(
            f"terminal nail bone missing: {bone_name}"
        )
    outward = Vector(outward_hint).normalized()
    longitudinal = Vector(longitudinal_hint)
    longitudinal = longitudinal - outward * longitudinal.dot(outward)
    if longitudinal.length <= 1.0e-8:
        raise nail_v3.NaturalNailDeliveryV3Error(
            f"source-local nail tangent degenerate: {bone_name}"
        )
    longitudinal.normalize()
    lateral = outward.cross(longitudinal)
    if lateral.length <= 1.0e-8:
        raise nail_v3.NaturalNailDeliveryV3Error(
            f"source-local nail lateral frame degenerate: {bone_name}"
        )
    lateral.normalize()
    longitudinal = lateral.cross(outward).normalized()
    # The source fingers are substantially rounder than the MakeHuman test
    # surface.  A denser odd grid retains the same v3 raycast/squoval method
    # while preventing broad quads from becoming chords through curved skin.
    grid = BLACKPROJECT_PROJECTION_GRID_SIZE
    faces = nail_v3._outward_grid_faces(grid)  # noqa: SLF001
    attempts: list[dict[str, Any]] = []
    total_raycast_count = 0
    accepted, source_recess_attempts = _source_component_recess_shell(
        name=name,
        body=body,
        body_tree=body_tree,
        source_component_frame=source_component_frame,
        nominal_length_m=length_m,
        nominal_width_m=width_m,
        grid=grid,
        faces=faces,
        bed_material=bed_material,
        free_edge_material=free_edge_material,
    )
    attempts.extend(source_recess_attempts)
    center_trials = [
        (
            "hashed_source_center_offset_fraction",
            float(center_offset_fraction),
            source_center_world
            + longitudinal * (length_m * center_offset_fraction),
        )
        for center_offset_fraction in SOURCE_CENTER_OFFSET_FRACTIONS
    ]
    footprint_scale_candidates = (
        BLACKPROJECT_BIG_TOE_FOOTPRINT_SCALE_CANDIDATES
        if nail_id.startswith("toenail_1_")
        else BLACKPROJECT_FOOTPRINT_SCALE_CANDIDATES
    )
    for footprint_scale in (
        () if accepted is not None else footprint_scale_candidates
    ):
        if accepted is not None:
            break
        for center_mode, center_value, center_base in center_trials:
          if accepted is not None:
            break
          for lateral_offset_fraction in SOURCE_LATERAL_OFFSET_FRACTIONS:
            nominal_center = (
                center_base
                + lateral * (width_m * lateral_offset_fraction)
            )
            hits: list[Vector] = []
            normals: list[Vector] = []
            base_clearances: list[float] = []
            complete = True
            failure_reason = ""
            minimum_alignment = 1.0
            for row in range(grid):
                for column in range(grid):
                    along, across, across_fraction = _rounded_outline_coordinates(
                        row=row,
                        column=column,
                        grid=grid,
                        length_m=length_m,
                        width_m=width_m,
                        footprint_scale=footprint_scale,
                    )
                    expected = nominal_center + longitudinal * along + lateral * across
                    total_raycast_count += 1
                    # The outward direction is derived from the local surface
                    # directly under the hashed source nail center.  Casting
                    # from that exterior side makes the first hit the intended
                    # nail bed, even on a rolled thumb.
                    origin = expected + outward * 0.012
                    hit, normal, _face, _distance = body_tree.ray_cast(
                        origin,
                        -outward,
                        0.024,
                    )
                    if hit is None or normal is None:
                        complete = False
                        failure_reason = f"surface_projection_miss_{row}_{column}"
                        break
                    if normal.dot(outward) < 0.0:
                        normal = -normal
                    normal.normalize()
                    alignment = float(normal.dot(outward))
                    minimum_alignment = min(minimum_alignment, alignment)
                    if alignment < nail_v3.MINIMUM_OUTWARD_NORMAL_ALIGNMENT:
                        complete = False
                        failure_reason = f"outward_normal_alignment_{row}_{column}"
                        break
                    transverse_arch = 1.0 - min(1.0, abs(across_fraction) * 2.0) ** 2
                    hits.append(hit.copy())
                    normals.append(normal.copy())
                    base_clearances.append(
                        0.000055
                        + BLACKPROJECT_BEVEL_CLEARANCE_COMPENSATION_M
                        + 0.000055 * transverse_arch
                    )
                if not complete:
                    break
            attempt: dict[str, Any] = {
                "footprint_scale": float(footprint_scale),
                "projection_center_mode": center_mode,
                "center_fraction_or_offset": center_value,
                "center_fraction_from_terminal": (
                    None
                ),
                "center_offset_fraction_from_hashed_source_center": (
                    center_value
                ),
                "lateral_offset_fraction_from_hashed_source_center": float(
                    lateral_offset_fraction
                ),
                "projection_complete": complete,
                "projected_sample_count": len(hits),
                "minimum_outward_normal_alignment": minimum_alignment,
                "failure_reason": failure_reason,
            }
            if not complete:
                attempts.append(attempt)
                continue

            locality = _grid_locality_record(
                points=hits,
                nominal_center=nominal_center,
                longitudinal=longitudinal,
                lateral=lateral,
                length_m=length_m,
                width_m=width_m,
                footprint_scale=footprint_scale,
                grid=grid,
            )
            attempt["grid_locality"] = locality
            if locality["locality_gate_passed"] is not True:
                attempt["fit_passed"] = False
                attempt["failure_reason"] = "generated_grid_locality_failed"
                attempts.append(attempt)
                continue

            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata(
                [
                    tuple(hit + normal * clearance)
                    for hit, normal, clearance in zip(hits, normals, base_clearances)
                ],
                [],
                faces,
            )
            mesh.update(calc_edges=True)
            _assign_grid_uvs(mesh, grid)
            nail = bpy.data.objects.new(name, mesh)
            bpy.context.collection.objects.link(nail)
            mesh.materials.append(bed_material)
            mesh.materials.append(free_edge_material)
            free_edge_face_count = 0
            for polygon in mesh.polygons:
                polygon.use_smooth = True
                face_row = int(polygon.index) // (grid - 1)
                polygon.material_index = (
                    1 if nail_v3.is_free_edge_face_row(face_row, grid) else 0
                )
                free_edge_face_count += int(polygon.material_index == 1)

            winding = _top_surface_winding_record(nail, outward)
            attempt["top_surface_winding"] = winding
            if winding["all_top_surface_faces_outward"] is not True:
                attempt["fit_passed"] = False
                attempt["failure_reason"] = "non_outward_or_folded_top_surface"
                attempts.append(attempt)
                nail_v3._remove_object_and_mesh(nail)  # noqa: SLF001
                continue

            initial_clearance: dict[str, Any] | None = None
            clearance: dict[str, Any] | None = None
            initial_overlap_count = -1
            overlap_count = -1
            accepted_lift = -1
            vertex_lifts = [0.0 for _vertex in nail.data.vertices]
            changed_vertex_indices: set[int] = set()
            maximum_local_lift = 0.0
            for lift_iteration in range(
                BLACKPROJECT_LOCAL_LIFT_MAXIMUM_ITERATIONS + 1
            ):
                for vertex, hit, normal, base_clearance in zip(
                    nail.data.vertices,
                    hits,
                    normals,
                    base_clearances,
                ):
                    vertex.co = hit + normal * (
                        base_clearance + vertex_lifts[int(vertex.index)]
                    )
                nail.data.update()
                clearance = component_v1._body_clearance_record(  # noqa: SLF001
                    body_tree,
                    [nail],
                )
                broad_overlap_count = len(
                    body_tree.overlap(component_v1._world_surface_bvh(nail))  # noqa: SLF001
                )
                exact_intersections = _exact_mesh_pair_intersections(
                    body,
                    nail,
                    evaluated=False,
                )
                overlap_count = int(
                    exact_intersections["exact_genuine_penetration_pair_count"]
                )
                if lift_iteration == 0:
                    initial_clearance = dict(clearance)
                    initial_overlap_count = overlap_count
                try:
                    validate_clearance_measurement(
                        minimum_m=float(
                            clearance["minimum_unsigned_body_surface_clearance_m"]
                        ),
                        maximum_m=float(
                            clearance["maximum_unsigned_body_surface_clearance_m"]
                        ),
                        overlap_count=overlap_count,
                    )
                except ValueError:
                    if (
                        float(
                            clearance["maximum_unsigned_body_surface_clearance_m"]
                        )
                        > nail_v3.MAXIMUM_SURFACE_CLEARANCE_M
                    ):
                        break
                    if overlap_count > 0 and lift_iteration < BLACKPROJECT_LOCAL_LIFT_MAXIMUM_ITERATIONS:
                        nail.data.calc_loop_triangles()
                        triangle_vertices = [
                            tuple(int(value) for value in triangle.vertices)
                            for triangle in nail.data.loop_triangles
                        ]
                        affected = {
                            vertex_index
                            for _body_index, nail_triangle_index in exact_intersections[
                                "exact_genuine_penetration_pairs"
                            ]
                            for vertex_index in triangle_vertices[int(nail_triangle_index)]
                        }
                        if not affected:
                            break
                        for vertex_index in affected:
                            vertex_lifts[vertex_index] += nail_v3.NORMAL_LIFT_STEP_M
                        changed_vertex_indices.update(affected)
                        maximum_local_lift = max(vertex_lifts)
                        continue
                    continue
                accepted_lift = lift_iteration
                break
            attempt.update(
                {
                    "initial_clearance": initial_clearance,
                    "initial_body_surface_triangle_overlap_count": initial_overlap_count,
                    "broad_phase_candidate_pair_count": broad_overlap_count,
                    "exact_intersections": exact_intersections,
                    "final_clearance": clearance,
                    "final_body_surface_triangle_overlap_count": overlap_count,
                    "adaptive_normal_lift_iteration_count": max(0, accepted_lift),
                    "adaptive_local_lift_changed_vertex_count": len(changed_vertex_indices),
                    "adaptive_local_lift_maximum_m": maximum_local_lift,
                    "fit_passed": accepted_lift >= 0,
                }
            )
            attempts.append(attempt)
            if accepted_lift >= 0:
                accepted = {
                    "nail": nail,
                    "clearance": clearance,
                    "overlap_count": overlap_count,
                    "footprint_scale": float(footprint_scale),
                    "center_mode": center_mode,
                    "center_fraction_from_terminal": None,
                    "center_offset_fraction": center_value,
                    "lateral_offset_fraction": float(lateral_offset_fraction),
                    "minimum_alignment": minimum_alignment,
                    "lift_iteration": accepted_lift,
                    "changed_vertex_count": len(changed_vertex_indices),
                    "maximum_local_lift": maximum_local_lift,
                    "free_edge_face_count": free_edge_face_count,
                    "initial_clearance": initial_clearance,
                    "initial_overlap_count": initial_overlap_count,
                    "broad_overlap_count": broad_overlap_count,
                    "exact_intersections": exact_intersections,
                    "grid_locality": locality,
                    "top_surface_winding": winding,
                }
                break
            nail_v3._remove_object_and_mesh(nail)  # noqa: SLF001

    if accepted is None:
        analytic_anchor = source_center_world
        conformal_accepted, conformal_attempts = _nearest_surface_conformal_fallback(
            name=name,
            body=body,
            body_tree=body_tree,
            anchor_world=analytic_anchor,
            longitudinal_hint=longitudinal,
            outward_hint=outward,
            length_m=length_m,
            width_m=width_m,
            grid=grid,
            faces=faces,
            bed_material=bed_material,
            free_edge_material=free_edge_material,
        )
        attempts.extend(conformal_attempts)
        accepted = conformal_accepted
    if accepted is None:
        analytic_anchor = source_center_world
        analytic_accepted, analytic_attempts = _analytic_curved_oval_fallback(
            name=name,
            body=body,
            body_tree=body_tree,
            source_center_world=analytic_anchor,
            longitudinal_hint=longitudinal,
            outward_hint=outward,
            length_m=length_m,
            width_m=width_m,
            grid=grid,
            faces=faces,
            bed_material=bed_material,
            free_edge_material=free_edge_material,
        )
        attempts.extend(analytic_attempts)
        accepted = analytic_accepted
    if accepted is None:
        raise nail_v3.NaturalNailDeliveryV3Error(
            f"bounded BlackProject v3 nail projection and analytic fallback failed:"
            f" {bone_name};attempts={json.dumps(attempts, sort_keys=True)}"
        )
    nail = accepted["nail"]
    points = [nail.matrix_world @ vertex.co for vertex in nail.data.vertices]
    finite = nail_v3.validate_finite_points(
        tuple(tuple(point) for point in points)
    )
    measurement_longitudinal = Vector(
        accepted.get("measurement_longitudinal_world", tuple(longitudinal))
    ).normalized()
    measurement_lateral = Vector(
        accepted.get("measurement_lateral_world", tuple(lateral))
    ).normalized()
    longitudinal_values = [
        float(point.dot(measurement_longitudinal)) for point in points
    ]
    lateral_values = [float(point.dot(measurement_lateral)) for point in points]
    plate_length = max(longitudinal_values) - min(longitudinal_values)
    plate_width = max(lateral_values) - min(lateral_values)
    face_normal_alignments = [
        float((nail.matrix_world.to_3x3() @ polygon.normal).normalized().dot(outward))
        for polygon in nail.data.polygons
    ]
    minimum_face_normal_alignment = min(face_normal_alignments)
    if minimum_face_normal_alignment <= 0.0:
        nail_v3._remove_object_and_mesh(nail)  # noqa: SLF001
        raise nail_v3.NaturalNailDeliveryV3Error(
            f"BlackProject nail top-surface winding is not outward: {bone_name}"
        )
    component_v1.assign_rigid_bone(nail, armature, bone_name)
    solidify = nail.modifiers.new("Natural_Nail_Plate_Thickness_V3", "SOLIDIFY")
    solidify.thickness = BLACKPROJECT_PLATE_THICKNESS_M
    solidify.offset = 1.0
    if hasattr(solidify, "use_even_offset"):
        solidify.use_even_offset = True
    if hasattr(solidify, "use_rim"):
        solidify.use_rim = True
    bevel = nail.modifiers.new("Natural_Nail_Edge_Soften_V3", "BEVEL")
    bevel.width = BLACKPROJECT_EDGE_BEVEL_WIDTH_M
    bevel.segments = BLACKPROJECT_EDGE_BEVEL_SEGMENTS
    bevel.limit_method = "ANGLE"
    bevel.angle_limit = math.radians(12.0)
    attachment = nail_v3._attachment_report(nail, armature, bone_name)  # noqa: SLF001
    clearance = accepted["clearance"]
    if clearance is None:
        raise nail_v3.NaturalNailDeliveryV3Error(
            "accepted BlackProject nail lost clearance evidence"
        )
    return nail, {
        "nail_id": nail_id,
        "object": nail.name,
        "bone": bone_name,
        "target_height_m": float(target_height_m),
        "projection_grid_dimensions": [grid, grid],
        "vertex_count": len(nail.data.vertices),
        "polygon_count": len(nail.data.polygons),
        "projection_raycast_count": total_raycast_count,
        "projection_query_mode": accepted.get(
            "projection_query_mode",
            "first_hit_raycast_from_local_surface_outward_frame",
        ),
        "projection_attempt_count": len(attempts),
        "projection_attempts": attempts,
        "projection_center_source": accepted.get(
            "center_mode",
            "analytic_local_surface_anchor",
        ),
        "source_nail_geometry_copied": False,
        "source_center_world_m": [float(value) for value in source_center_world],
        "retained_footprint_scale": accepted["footprint_scale"],
        "projection_center_offset_fraction": accepted["center_offset_fraction"],
        "projection_center_mode": accepted.get(
            "center_mode",
            "analytic_local_surface_anchor",
        ),
        "projection_center_fraction_from_terminal": accepted.get(
            "center_fraction_from_terminal"
        ),
        "projection_lateral_offset_fraction": accepted["lateral_offset_fraction"],
        "minimum_outward_projection_normal_alignment": accepted["minimum_alignment"],
        "minimum_outward_face_normal_alignment": minimum_face_normal_alignment,
        "adaptive_normal_lift_iteration_count": accepted["lift_iteration"],
        "adaptive_local_lift_changed_vertex_count": accepted[
            "changed_vertex_count"
        ],
        "additional_normal_lift_m": accepted["maximum_local_lift"],
        "minimum_clearance_m": float(
            clearance["minimum_unsigned_body_surface_clearance_m"]
        ),
        "maximum_clearance_m": float(
            clearance["maximum_unsigned_body_surface_clearance_m"]
        ),
        "body_surface_triangle_overlap_count": int(accepted["overlap_count"]),
        "broad_phase_candidate_pair_count": int(accepted["broad_overlap_count"]),
        "exact_intersections": accepted["exact_intersections"],
        "initial_clearance": accepted["initial_clearance"],
        "initial_body_surface_triangle_overlap_count": accepted[
            "initial_overlap_count"
        ],
        "analytic_surface_anchor": accepted.get("analytic_surface_anchor"),
        "analytic_curvature": accepted.get("analytic_curvature"),
        "plate_length_m": plate_length,
        "plate_width_m": plate_width,
        "dimension_measurement_longitudinal_world": [
            float(value) for value in measurement_longitudinal
        ],
        "dimension_measurement_lateral_world": [
            float(value) for value in measurement_lateral
        ],
        "plate_aspect_ratio": plate_length / plate_width,
        "rounded_oval_silhouette": True,
        "rounded_proximal_corners": True,
        "mild_distal_and_bilateral_side_taper": True,
        "grid_locality": accepted.get("grid_locality"),
        "source_recess_clearance": accepted.get("source_recess_clearance"),
        "clearance_contract": (
            "blackproject_open_nail_recess_perimeter_attachment_v1"
            if accepted.get("source_recess_clearance") is not None
            else "generic_v3_continuous_body_surface"
        ),
        "generated_target_length_m": accepted.get(
            "generated_target_length_m", length_m
        ),
        "generated_target_width_m": accepted.get(
            "generated_target_width_m", width_m
        ),
        "free_edge_face_count": int(accepted["free_edge_face_count"]),
        "nail_bed_face_count": len(nail.data.polygons)
        - int(accepted["free_edge_face_count"]),
        "outward_only_plate_thickness_m": BLACKPROJECT_PLATE_THICKNESS_M,
        "rounded_edge_bevel_width_m": BLACKPROJECT_EDGE_BEVEL_WIDTH_M,
        "rounded_edge_bevel_segments": BLACKPROJECT_EDGE_BEVEL_SEGMENTS,
        "tapered_rounded_sidewall_intent": True,
        "generated_uv_proximal_fade": True,
        **finite,
        **attachment,
    }


def _validate_custom_inventory(records: list[dict[str, Any]]) -> dict[str, Any]:
    expected = {row["nail_id"]: row for row in _inventory()}
    ids = [str(row["nail_id"]) for row in records]
    if len(records) != 20 or len(set(ids)) != 20 or set(ids) != set(expected):
        raise ValueError("BlackProject natural-nail inventory is not exact")
    for row in records:
        definition = expected[str(row["nail_id"])]
        for key in ("kind", "side", "digit", "bone"):
            if row.get(key) != definition[key]:
                raise ValueError(f"identity drift for {row['nail_id']}: {key}")
        if row.get("finite_geometry") is not True:
            raise ValueError(f"non-finite nail geometry: {row['nail_id']}")
        source_recess = row.get("source_recess_clearance")
        if isinstance(source_recess, Mapping):
            if not _source_recess_clearance_passed(source_recess):
                raise ValueError(
                    f"source-recess perimeter clearance failed: {row['nail_id']}"
                )
            if int(row["body_surface_triangle_overlap_count"]) != 0:
                raise ValueError(
                    f"source-recess top shell intersects body: {row['nail_id']}"
                )
        else:
            validate_clearance_measurement(
                minimum_m=float(row["minimum_clearance_m"]),
                maximum_m=float(row["maximum_clearance_m"]),
                overlap_count=int(row["body_surface_triangle_overlap_count"]),
            )
        validate_attachment_measurement(
            expected_bone=str(definition["bone"]),
            actual_bone=str(row["bone"]),
            parent_is_exact_armature=row["parent_is_exact_armature"] is True,
            armature_modifier_targets_exact_rig=(
                row["armature_modifier_targets_exact_rig"] is True
            ),
            every_vertex_has_unit_terminal_bone_weight=(
                row["every_vertex_has_unit_terminal_bone_weight"] is True
            ),
        )
        if row["evaluated_solidified_plate_has_no_body_overlap"] is not True:
            raise ValueError(f"solidified neutral nail overlaps body: {row['nail_id']}")
        if row.get("evaluated_centroid_exact_digit_binding_gate_passed") is not True:
            raise ValueError(
                f"evaluated nail centroid is not bound to its exact digit: {row['nail_id']}"
            )
        if row.get("exactly_one_connected_generated_shell_for_digit") is not True:
            raise ValueError(
                f"generated nail is not one connected shell: {row['nail_id']}"
            )
        locality = row.get("grid_locality")
        if not isinstance(locality, Mapping) or locality.get("locality_gate_passed") is not True:
            raise ValueError(f"generated nail grid locality failed: {row['nail_id']}")
        if isinstance(source_recess, Mapping):
            evaluated_top = row.get("evaluated_top_source_recess_clearance")
            if (
                not isinstance(evaluated_top, Mapping)
                or evaluated_top.get(
                    "evaluated_top_source_recess_clearance_gate_passed"
                )
                is not True
            ):
                raise ValueError(
                    f"evaluated source-recess rim clearance failed: {row['nail_id']}"
                )
            if (
                float(row["evaluated_minimum_unsigned_body_surface_clearance_m"])
                < BLACKPROJECT_RECESS_MINIMUM_CLEARANCE_M
                or float(row["evaluated_maximum_unsigned_body_surface_clearance_m"])
                > float(evaluated_top["maximum_allowed_center_recess_gap_m"])
                or int(row["evaluated_body_surface_triangle_overlap_count"]) != 0
            ):
                raise ValueError(
                    f"evaluated solidified source-recess clearance failed: {row['nail_id']}"
                )
        else:
            try:
                validate_clearance_measurement(
                    minimum_m=float(
                        row["evaluated_minimum_unsigned_body_surface_clearance_m"]
                    ),
                    maximum_m=float(
                        row["evaluated_maximum_unsigned_body_surface_clearance_m"]
                    ),
                    overlap_count=int(
                        row["evaluated_body_surface_triangle_overlap_count"]
                    ),
                )
            except ValueError as exc:
                raise ValueError(
                    "evaluated solidified clearance failed for "
                    f"{row['nail_id']}: min="
                    f"{row['evaluated_minimum_unsigned_body_surface_clearance_m']};"
                    "max="
                    f"{row['evaluated_maximum_unsigned_body_surface_clearance_m']};"
                    "overlap="
                    f"{row['evaluated_body_surface_triangle_overlap_count']};"
                    f"reason={exc}"
                ) from exc
        length = float(row["plate_length_m"])
        width = float(row["plate_width_m"])
        nominal_length = float(
            row.get(
                "generated_target_length_m",
                TARGET_HEIGHT_M * float(definition["length_height_fraction"]),
            )
        )
        nominal_width = float(
            row.get(
                "generated_target_width_m",
                TARGET_HEIGHT_M * float(definition["width_height_fraction"]),
            )
        )
        compact_small_toe = (
            definition["kind"] == "toenail" and int(definition["digit"]) > 1
        )
        minimum_length_fraction = 0.55 if isinstance(source_recess, Mapping) else (
            0.38 if compact_small_toe else 0.50
        )
        minimum_width_fraction = 0.55 if isinstance(source_recess, Mapping) else (
            0.36 if compact_small_toe else 0.45
        )
        if not minimum_length_fraction * nominal_length <= length <= 1.08 * nominal_length:
            raise ValueError(f"nail length outside v3 bound: {row['nail_id']}")
        if not minimum_width_fraction * nominal_width <= width <= 1.08 * nominal_width:
            raise ValueError(f"nail width outside v3 bound: {row['nail_id']}")
        minimum_aspect_ratio = 0.78 if compact_small_toe else 0.95
        if not minimum_aspect_ratio <= length / width <= 2.15:
            raise ValueError(f"nail aspect ratio outside ordinary bound: {row['nail_id']}")
    return {
        "component_count": 20,
        "fingernail_count": 10,
        "toenail_count": 10,
        "all_twenty_present": True,
        "all_exact_blackproject_distal_bones_used": True,
        "all_top_surface_clearance_gates_passed": True,
        "all_evaluated_solidified_neutral_overlap_gates_passed": True,
        "all_evaluated_solidified_neutral_clearance_gates_passed": True,
        "all_exact_terminal_bone_attachment_gates_passed": True,
        "all_evaluated_centroids_bound_to_exact_recorded_digits": True,
        "all_twenty_are_single_connected_generated_shells": True,
        "all_grid_locality_gates_passed": True,
        "all_source_native_open_recess_perimeter_attachment_gates_passed": True,
        "all_source_native_center_recess_gaps_separately_reported": True,
        "blackproject_compact_small_toe_dimension_adaptation": {
            "applies_only_to_toenails_2_through_5": True,
            "minimum_nominal_length_fraction": 0.38,
            "minimum_nominal_width_fraction": 0.36,
            "minimum_aspect_ratio": 0.78,
            "exact_intersection_and_attachment_gates_unchanged": True,
            "whole_surface_maximum_clearance_replaced_only_for_documented_open_recess": True,
        },
    }


def _add_lights(scene: Any) -> None:
    for name, location, energy, size in (
        ("R19_NAIL_KEY", (1.8, -2.2, 2.3), 350.0, 2.4),
        ("R19_NAIL_FILL", (-1.6, -1.6, 1.5), 220.0, 2.2),
        ("R19_NAIL_TOP", (0.0, 0.0, 3.0), 260.0, 2.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (
            Vector((0.0, 0.0, 0.85)) - obj.location
        ).to_track_quat("-Z", "Y").to_euler()


def _render(
    scene: Any,
    camera: Any,
    path: Path,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = scale
    camera.rotation_euler = (
        Vector(target) - camera.location
    ).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def _render_close_set(
    scene: Any,
    output_dir: Path,
    definitions: Iterable[Mapping[str, Any]],
    outward_hints: Mapping[str, tuple[float, float, float]],
) -> dict[str, str]:
    camera_data = bpy.data.cameras.new("R19_BLACKPROJECT_NAIL_CAMERA")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R19_BLACKPROJECT_NAIL_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    rows = list(definitions)
    views: dict[str, tuple[tuple[float, float, float], tuple[float, float, float], float]] = {}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for kind, label, full_scale, macro_scale in (
        ("fingernail", "hand", 0.19, 0.155),
        ("toenail", "foot", 0.27, 0.150),
    ):
        for side, side_label in (("L", "left"), ("R", "right")):
            selected = [row for row in rows if row["kind"] == kind and row["side"] == side]
            evaluated_points: list[Vector] = []
            for row in selected:
                nail = bpy.data.objects[
                    f"R19_BlackProject_{row['nail_id']}_natural_v3"
                ]
                evaluated = nail.evaluated_get(depsgraph)
                mesh = evaluated.to_mesh()
                try:
                    evaluated_points.extend(
                        evaluated.matrix_world @ vertex.co for vertex in mesh.vertices
                    )
                finally:
                    evaluated.to_mesh_clear()
            low = Vector(
                tuple(min(point[axis] for point in evaluated_points) for axis in range(3))
            )
            high = Vector(
                tuple(max(point[axis] for point in evaluated_points) for axis in range(3))
            )
            nail_target = (low + high) * 0.5
            if kind == "fingernail":
                full_target = nail_target + Vector(
                    (0.018 if side == "L" else -0.018, 0.0, 0.003)
                )
            else:
                full_target = nail_target + Vector((0.0, 0.072, 0.010))
            outward = sum(
                (Vector(outward_hints[str(row["bone"])]) for row in selected),
                Vector(),
            )
            outward.normalize()
            if kind == "fingernail":
                oblique_bias = Vector(
                    (0.20 if side == "L" else -0.20, -0.05, 0.55)
                )
            else:
                oblique_bias = Vector((0.15 if side == "L" else -0.15, -0.55, 0.18))
            oblique_direction = outward + oblique_bias
            oblique_direction.normalize()
            views[f"{side_label}_{label}_dorsal_full"] = (
                tuple(full_target + outward * 0.55),
                tuple(full_target),
                full_scale,
            )
            views[f"{side_label}_{label}_oblique_full"] = (
                tuple(full_target + oblique_direction * 0.55),
                tuple(full_target),
                full_scale,
            )
            views[f"{side_label}_{label}_dorsal_nail_macro"] = (
                tuple(nail_target + outward * 0.45),
                tuple(nail_target),
                macro_scale,
            )
            views[f"{side_label}_{label}_oblique_nail_macro"] = (
                tuple(nail_target + oblique_direction * 0.45),
                tuple(nail_target),
                macro_scale,
            )
    result: dict[str, str] = {}
    for name, (location, target, scale) in views.items():
        path = output_dir / f"{name}.png"
        _render(scene, camera, path, location, target, scale)
        result[name] = path.name
    return result


def _write_manifest(
    output_dir: Path,
    project_root: Path,
    extra_paths: Iterable[Path],
) -> Path:
    manifest_path = output_dir / "FILE_MANIFEST.json"
    paths = sorted(
        {path.resolve() for path in [*output_dir.iterdir(), *extra_paths] if path.resolve() != manifest_path.resolve()},
        key=lambda path: str(path).lower(),
    )
    rows = []
    for path in paths:
        try:
            relative = path.relative_to(project_root)
            label = str(relative).replace("\\", "/")
        except ValueError:
            label = str(path)
        rows.append({"path": label, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "append_only_probe": True,
                "files": rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = Path(config["project_root"]).resolve(strict=True)
    source = (root / config["source_path"]).resolve(strict=True)
    alignment_path = (root / config["alignment_path"]).resolve(strict=True)
    output_dir = (root / config["output_dir"]).resolve()
    if sha256_file(source) != SOURCE_SHA256:
        raise ValueError("BlackProject source hash mismatch")
    if sha256_file(alignment_path) != ALIGNMENT_SHA256:
        raise ValueError("BlackProject nail-alignment evidence hash mismatch")
    if output_dir.exists():
        raise FileExistsError(f"append-only attempt already exists: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)

    definitions = _inventory()
    if len(definitions) != 20:
        raise ValueError("internal BlackProject inventory must have 20 entries")
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    alignment_rows = _alignment_rows_by_bone(alignment)
    expected_bones = {str(row["bone"]) for row in definitions}
    if _alignment_bones(alignment) != expected_bones:
        raise ValueError("alignment evidence does not match exact 20-bone inventory")

    _clear_scene()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(source))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    meshes = _mesh_map(imported)
    missing = sorted(
        {HAND_SURFACE_MESH, FOOT_SURFACE_MESH, *SOURCE_NAIL_MESHES} - set(meshes)
    )
    if missing:
        raise ValueError(f"required BlackProject meshes missing: {missing}")
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    if len(armatures) != 1 or len(armatures[0].data.bones) != 188:
        raise ValueError("source must expose exact single native 188-joint rig")
    armature = armatures[0]
    imported_armature_pose_position = str(armature.data.pose_position)
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get().update()
    if not expected_bones.issubset({bone.name for bone in armature.data.bones}):
        raise ValueError("one or more exact distal nail bones is missing")
    body_parts = [meshes[HAND_SURFACE_MESH], meshes[FOOT_SURFACE_MESH]]
    body_signatures_before = {
        obj.data.name: nail_v3._mesh_signature(obj) for obj in body_parts  # noqa: SLF001
    }
    rig_signature_before = nail_v3._rig_signature(armature)  # noqa: SLF001
    surface_trees = {
        HAND_SURFACE_MESH: component_v1._world_surface_bvh(  # noqa: SLF001
            meshes[HAND_SURFACE_MESH]
        ),
        FOOT_SURFACE_MESH: component_v1._world_surface_bvh(  # noqa: SLF001
            meshes[FOOT_SURFACE_MESH]
        ),
    }
    source_nail_evidence = {
        name: {
            "object": meshes[name].name,
            "mesh_signature_sha256": nail_v3._mesh_signature(meshes[name]),  # noqa: SLF001
            "vertex_count": len(meshes[name].data.vertices),
            "polygon_count": len(meshes[name].data.polygons),
        }
        for name in SOURCE_NAIL_MESHES
    }
    source_component_frames = _measure_excluded_source_nail_frames(
        source_objects={name: meshes[name] for name in SOURCE_NAIL_MESHES},
        alignment_rows=alignment_rows,
        body_trees=surface_trees,
    )
    for name in SOURCE_NAIL_MESHES:
        bpy.data.objects.remove(meshes[name], do_unlink=True)
    source_nail_objects_remaining = [
        obj.name
        for obj in bpy.data.objects
        if obj.type == "MESH" and obj.data.name in SOURCE_NAIL_MESHES
    ]
    if source_nail_objects_remaining:
        raise ValueError("source nail geometry was not fully excluded")

    # Hair is unrelated to this isolated nail proof and is intentionally absent
    # from its private low-resource renders.  This does not modify the GLB.
    removed_hair = []
    for obj in list(bpy.data.objects):
        if obj.type == "MESH" and obj.data.name.startswith("Hair_"):
            removed_hair.append(obj.data.name)
            bpy.data.objects.remove(obj, do_unlink=True)

    local_fit_frames = source_component_frames
    outward_hints = {
        bone_name: tuple(float(value) for value in frame["outward_world"])
        for bone_name, frame in local_fit_frames.items()
    }
    bed_material = nail_v3._natural_nail_material(  # noqa: SLF001
        "R19_BlackProject_Natural_Nail_Bed_V3",
        BLACKPROJECT_NAIL_BED_MATERIAL,
    )
    _add_proximal_fade_to_bed_material(bed_material)
    free_edge_material = nail_v3._natural_nail_material(  # noqa: SLF001
        "R19_BlackProject_Natural_Nail_Free_Edge_V3",
        BLACKPROJECT_FREE_EDGE_MATERIAL,
    )
    nail_objects: list[Any] = []
    records: list[dict[str, Any]] = []
    for definition in definitions:
        surface_name = str(definition["surface_mesh"])
        nail, record = _projected_blackproject_oval_nail_plate(
            name=f"R19_BlackProject_{definition['nail_id']}_natural_v3",
            nail_id=str(definition["nail_id"]),
            body=meshes[surface_name],
            body_tree=surface_trees[surface_name],
            armature=armature,
            bone_name=str(definition["bone"]),
            outward_hint=outward_hints[str(definition["bone"])],
            longitudinal_hint=tuple(
                float(value)
                for value in local_fit_frames[str(definition["bone"])][
                    "longitudinal_world"
                ]
            ),
            source_center_world=Vector(
                local_fit_frames[str(definition["bone"])][
                    "component_centroid_world_m"
                ]
            ),
            source_component_frame=local_fit_frames[str(definition["bone"])],
            length_m=TARGET_HEIGHT_M * float(definition["length_height_fraction"]),
            width_m=TARGET_HEIGHT_M * float(definition["width_height_fraction"]),
            target_height_m=TARGET_HEIGHT_M,
            bed_material=bed_material,
            free_edge_material=free_edge_material,
        )
        nail["private_owner_review_only"] = True
        nail["inactive_probe"] = True
        nail["runtime_activation_allowed"] = False
        nail["blackproject_native_188_rig"] = True
        nail["source_nail_geometry_copied"] = False
        evaluated = _evaluated_clearance_and_overlap(
            meshes[surface_name],
            surface_trees[surface_name],
            nail,
        )
        evaluated_top_recess = _evaluated_top_source_recess_clearance(
            body=meshes[surface_name],
            nail=nail,
            grid=BLACKPROJECT_PROJECTION_GRID_SIZE,
            source_component_frame=local_fit_frames[str(definition["bone"])],
        )
        digit_binding = _evaluated_digit_binding_record(
            nail=nail,
            bone_name=str(definition["bone"]),
            alignment_row=alignment_rows[str(definition["bone"])],
            alignment_rows=alignment_rows,
        )
        records.append(
            {
                **record,
                **evaluated,
                "evaluated_top_source_recess_clearance": evaluated_top_recess,
                **digit_binding,
                "kind": str(definition["kind"]),
                "side": str(definition["side"]),
                "digit": int(definition["digit"]),
                "surface_mesh": surface_name,
                "source_fit_outward_hint": list(outward_hints[str(definition["bone"])]),
                "source_local_fit_frame": local_fit_frames[str(definition["bone"])],
            }
        )
        nail_objects.append(nail)

    generated_names = [obj.name for obj in nail_objects]
    expected_generated_names = [
        f"R19_BlackProject_{row['nail_id']}_natural_v3" for row in definitions
    ]
    other_nail_mesh_objects = sorted(
        f"{obj.name}|{obj.data.name}"
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and obj not in nail_objects
        and ("nail" in obj.name.lower() or "nail" in obj.data.name.lower())
    )
    generated_inventory = {
        "generated_shell_object_count": len(nail_objects),
        "generated_shell_object_names": sorted(generated_names),
        "expected_generated_shell_object_names": sorted(expected_generated_names),
        "exactly_one_generated_shell_object_per_digit": (
            len(nail_objects) == 20
            and len(set(generated_names)) == 20
            and set(generated_names) == set(expected_generated_names)
        ),
        "other_or_source_nail_mesh_objects": other_nail_mesh_objects,
        "no_source_or_other_nail_mesh_object_present": not other_nail_mesh_objects,
    }
    if generated_inventory["exactly_one_generated_shell_object_per_digit"] is not True:
        raise ValueError("generated nail-shell object inventory is not exact")
    if generated_inventory["no_source_or_other_nail_mesh_object_present"] is not True:
        raise ValueError("source or unbound nail mesh object remains in probe")

    validation = _validate_custom_inventory(records)
    body_signatures_after = {
        obj.data.name: nail_v3._mesh_signature(obj) for obj in body_parts  # noqa: SLF001
    }
    rig_signature_after = nail_v3._rig_signature(armature)  # noqa: SLF001
    if body_signatures_after != body_signatures_before:
        raise ValueError("hand or foot source body mesh changed during nail probe")
    if rig_signature_after != rig_signature_before:
        raise ValueError("native 188-joint rig changed during nail probe")

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.010, 0.016, 0.024)
    if hasattr(scene.view_settings, "look"):
        try:
            scene.view_settings.look = "AgX - Medium High Contrast"
        except TypeError:
            pass
    if hasattr(scene.view_settings, "exposure"):
        scene.view_settings.exposure = -0.7
    _add_lights(scene)
    renders = _render_close_set(
        scene,
        output_dir,
        definitions,
        outward_hints,
    )

    blend_path = output_dir / "r19_blackproject_natural_nail_probe.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    bounds = _world_bounds(
        [obj for obj in bpy.data.objects if obj.type == "MESH"]
    )
    report = {
        "schema_version": 1,
        "mode": "R19_BLACKPROJECT_NATURAL_NAIL_V3_PRIVATE_INACTIVE_PROBE",
        "source": {
            "path": str(source.relative_to(root)).replace("\\", "/"),
            "sha256": SOURCE_SHA256,
            "source_unchanged": sha256_file(source) == SOURCE_SHA256,
            "license": "CC BY 4.0",
        },
        "alignment_evidence": {
            "path": str(alignment_path.relative_to(root)).replace("\\", "/"),
            "sha256": ALIGNMENT_SHA256,
            "exact_20_bone_set_matched": True,
        },
        "source_nail_geometry": {
            "excluded_from_probe": True,
            "copied_into_generated_components": False,
            "objects_remaining": source_nail_objects_remaining,
            "preserved_pre_exclusion_evidence": source_nail_evidence,
            "measurement_only_component_frames_before_exclusion": (
                source_component_frames
            ),
            "post_generation_object_inventory": generated_inventory,
        },
        "adapter": {
            "method": nail_v3.METHOD_ID,
            "adaptation": (
                "exact BlackProject distal-bone attachment inventory plus separate "
                "arm/leg surface BVHs and hashed source-center local fit frames"
            ),
            "blackproject_projection_grid_size": BLACKPROJECT_PROJECTION_GRID_SIZE,
            "blackproject_local_lift_maximum_iterations": BLACKPROJECT_LOCAL_LIFT_MAXIMUM_ITERATIONS,
            "blackproject_footprint_scale_candidates": list(BLACKPROJECT_FOOTPRINT_SCALE_CANDIDATES),
            "blackproject_minimum_retained_footprint_scale": BLACKPROJECT_MINIMUM_RETAINED_FOOTPRINT_SCALE,
            "blackproject_big_toe_footprint_scale_candidates": list(
                BLACKPROJECT_BIG_TOE_FOOTPRINT_SCALE_CANDIDATES
            ),
            "intersection_gate": "exact narrow-phase triangle classification; BVH overlap retained as broad-phase evidence only",
            "generated_short_conformal_curved_shell_count": len(nail_objects),
            "source_components_used_only_for_center_pca_frame_and_span_measurements": True,
            "source_nail_geometry_topology_uv_material_or_weight_copied": False,
            "projection_query_adaptation": (
                "primary generated shells use excluded source-component center/PCA "
                "frame/span measurements to bridge the source-native open nail "
                "recess; they copy no source geometry. Exact nonintersection, "
                "bounded close rim clearance, center-gap reporting, grid locality, "
                "and evaluated digit binding are mandatory"
            ),
            "local_fit_frames": local_fit_frames,
            "records": records,
            "validation": validation,
            "base_v3_material_contract": nail_v3.material_contract(),
            "contrast_safe_review_material_contract": {
                "nail_bed": BLACKPROJECT_NAIL_BED_MATERIAL,
                "free_edge": BLACKPROJECT_FREE_EDGE_MATERIAL,
                "generated_uv_proximal_fade": True,
            },
            "rounded_outline_contract": {
                "rounded_proximal_corners": True,
                "mild_bilateral_side_taper": True,
                "short_rounded_distal_edge": True,
                "hard_trapezoid_outline_rejected": True,
            },
            "outward_only_plate_thickness_m": BLACKPROJECT_PLATE_THICKNESS_M,
            "edge_bevel_width_m": BLACKPROJECT_EDGE_BEVEL_WIDTH_M,
            "edge_bevel_segments": BLACKPROJECT_EDGE_BEVEL_SEGMENTS,
        },
        "preservation": {
            "hand_and_foot_mesh_signatures_before": body_signatures_before,
            "hand_and_foot_mesh_signatures_after": body_signatures_after,
            "hand_and_foot_meshes_unchanged": body_signatures_after == body_signatures_before,
            "native_rig_signature_before": rig_signature_before,
            "native_rig_signature_after": rig_signature_after,
            "native_rig_unchanged": rig_signature_after == rig_signature_before,
            "native_joint_count": len(armature.data.bones),
            "imported_armature_pose_position": imported_armature_pose_position,
            "probe_armature_pose_position": str(armature.data.pose_position),
            "rest_pose_applies_to_private_probe_scene_only": True,
            "unrelated_hair_removed_from_probe_only": sorted(removed_hair),
        },
        "neutral_probe_bounds_m": bounds,
        "renders": renders,
        "blend": {
            "path": blend_path.name,
            "sha256": sha256_file(blend_path),
        },
        "private_inactive_append_only_probe": True,
        "complete_body_candidate_built": False,
        "body_identity_anatomy_or_movement_changed": False,
        "runtime_roster_assignment_or_activation_changed": False,
        "dynamic_pose_clearance_still_requires_candidate_level_requalification": True,
    }
    report_path = output_dir / "BLACKPROJECT_NATURAL_NAIL_V3_PROBE.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    manifest_path = _write_manifest(
        output_dir,
        root,
        [Path(__file__).resolve(), config_path, source, alignment_path],
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "component_count": len(nail_objects),
                "report": str(report_path),
                "report_sha256": sha256_file(report_path),
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
