"""No-save R24 feature-aligned parametric pelvic-surface simulation.

This worker opens the exact sealed R19 candidate, removes only the interior of
the qualified broad one-disk pelvic mask (the rejected patch plus eight face
rings), and constructs one connected replacement surface.  The replacement is
not copied from a donor and is not a scalar graph in the old fixed body frame.
It is a feature-aligned, three-dimensional centerline sweep with a rotating
local frame, paired fold topology, and three independent shallow capped recess
sets.  It renders private diagnostic evidence but never saves a Blend.

The result is an external visual/deformation simulation only.  It does not
create or prove internal urinary, vaginal, reproductive, rectal, pelvic-floor,
continence, elimination, pregnancy, sensation, or intimate-behavior systems.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
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

from tools import blender_exact_mesh_intersections as exact_intersections  # noqa: E402
from tools import blender_simulate_kira_r24_broad_inplace_surface as r24_base  # noqa: E402
from tools import blender_author_kira_r23_cc0_afes_attempt01 as r23_author  # noqa: E402
from tools import kira_r23_cc0_afes_author_core as r23_core  # noqa: E402
from tools import kira_r23_cc0_afes_preflight_core as topology_core  # noqa: E402


SOURCE = r24_base.SOURCE
SOURCE_SHA256 = r24_base.SOURCE_SHA256
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_feature_aligned_centerline_surface/attempt_04"
)
CHART_DIAGNOSTIC = ROOT / (
    "RecoverySprint/continuation_20260803/kira_r24_patch_chart_diagnostic/"
    "attempt_02/PATCH_CHART_DIAGNOSTIC.json"
)
CHART_DIAGNOSTIC_SHA256 = (
    "fac55acd2e980a16c87f0a82b709c6cb2f7016111d0fef41ce85acda32aaceef"
)

BODY_NAME = r24_base.BODY_NAME
RIG_NAME = r24_base.RIG_NAME
PATCH_MATERIAL_INDEX = r24_base.PATCH_MATERIAL_INDEX
EXTERIOR_FACE_RINGS = 8

GRID_WIDTH = 28
GRID_HEIGHT = 25
EXPECTED_OLD_PATCH_FACES = 376
EXPECTED_REGION_FACES = 828
EXPECTED_REGION_VERTICES = 466
EXPECTED_BOUNDARY_VERTICES = 102
EXPECTED_REMOVABLE_VERTICES = 364

U_COORDS = (
    -1.00,
    -0.86,
    -0.74,
    -0.64,
    -0.55,
    -0.47,
    -0.40,
    -0.34,
    -0.28,
    -0.22,
    -0.17,
    -0.12,
    -0.07,
    -0.025,
    0.025,
    0.07,
    0.12,
    0.17,
    0.22,
    0.28,
    0.34,
    0.40,
    0.47,
    0.55,
    0.64,
    0.74,
    0.86,
    1.00,
)

T_COORDS = (
    0.00,
    0.05,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.34,
    0.38,
    0.42,
    0.46,
    0.50,
    0.54,
    0.58,
    0.62,
    0.66,
    0.70,
    0.74,
    0.78,
    0.82,
    0.86,
    0.90,
    0.94,
    0.97,
    1.00,
)

if len(U_COORDS) != GRID_WIDTH or len(T_COORDS) != GRID_HEIGHT:
    raise RuntimeError("feature-aligned grid coordinate count drifted")


FEATURE_CODES = {
    "base": 1,
    "mons": 2,
    "labia_majora_left": 3,
    "labia_majora_right": 4,
    "labia_minora_left": 5,
    "labia_minora_right": 6,
    "vestibule": 7,
    "clitoral_hood_glans": 8,
    "urethral_meatus": 9,
    "vaginal_introitus": 10,
    "posterior_fourchette": 11,
    "external_perineum": 12,
    "anal_verge": 13,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def vector_record(value: Vector) -> list[float]:
    return [round(float(component), 12) for component in value]


def grid_id(column: int, row: int) -> int:
    return row * GRID_WIDTH + column


def grid_key(local_id: int) -> tuple[int, int]:
    return local_id % GRID_WIDTH, local_id // GRID_WIDTH


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, float(value)))
    return value * value * (3.0 - 2.0 * value)


def compact_bump(value: float, radius: float) -> float:
    normalized = abs(float(value)) / max(float(radius), 1.0e-12)
    if normalized >= 1.0:
        return 0.0
    return (1.0 - normalized * normalized) ** 3


def interval_window(value: float, start: float, end: float, feather: float) -> float:
    if value <= start - feather or value >= end + feather:
        return 0.0
    enter = smoothstep((value - (start - feather)) / max(feather, 1.0e-12))
    leave = smoothstep(((end + feather) - value) / max(feather, 1.0e-12))
    return min(enter, leave)


def perimeter_keys() -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    result.extend((column, 0) for column in range(GRID_WIDTH))
    result.extend((GRID_WIDTH - 1, row) for row in range(1, GRID_HEIGHT))
    result.extend(
        (column, GRID_HEIGHT - 1)
        for column in range(GRID_WIDTH - 2, -1, -1)
    )
    result.extend((0, row) for row in range(GRID_HEIGHT - 2, 0, -1))
    if len(result) != EXPECTED_BOUNDARY_VERTICES or len(set(result)) != len(result):
        raise RuntimeError("102-vertex rectangular perimeter construction drifted")
    return result


PERIMETER_KEYS = perimeter_keys()


def faces_of(body: bpy.types.Object) -> list[tuple[int, ...]]:
    return [tuple(map(int, polygon.vertices)) for polygon in body.data.polygons]


def original_weight_record(body: bpy.types.Object, vertex_index: int) -> dict[str, float]:
    return r23_author.source_weights(body, int(vertex_index))


def choose_boundary_alignment(
    cycle: Sequence[int], body: bpy.types.Object
) -> tuple[list[int], dict[str, Any]]:
    if len(cycle) != len(PERIMETER_KEYS):
        raise RuntimeError("boundary/perimeter cardinality mismatch")
    world = {
        int(index): body.matrix_world @ body.data.vertices[int(index)].co
        for index in cycle
    }
    chart = {int(index): r24_base.local_chart(point)[:2] for index, point in world.items()}
    u_values = [value[0] for value in chart.values()]
    v_values = [value[1] for value in chart.values()]
    u_mid = (min(u_values) + max(u_values)) * 0.5
    v_mid = (min(v_values) + max(v_values)) * 0.5
    u_scale = max((max(u_values) - min(u_values)) * 0.5, 1.0e-12)
    v_scale = max((max(v_values) - min(v_values)) * 0.5, 1.0e-12)

    target_uv: list[tuple[float, float]] = []
    for column, row in PERIMETER_KEYS:
        target_uv.append((float(U_COORDS[column]), 1.0 - 2.0 * float(T_COORDS[row])))

    best: tuple[float, list[int], bool, int] | None = None
    base_cycle = list(map(int, cycle))
    for reversed_order in (False, True):
        candidate = list(reversed(base_cycle)) if reversed_order else list(base_cycle)
        for shift in range(len(candidate)):
            aligned = candidate[shift:] + candidate[:shift]
            cost = 0.0
            for target, vertex_index in zip(target_uv, aligned):
                raw_u, raw_v = chart[vertex_index]
                normalized = ((raw_u - u_mid) / u_scale, (raw_v - v_mid) / v_scale)
                cost += (normalized[0] - target[0]) ** 2 + (normalized[1] - target[1]) ** 2
            cost /= len(aligned)
            if best is None or cost < best[0]:
                best = (cost, aligned, reversed_order, shift)
    if best is None:
        raise RuntimeError("failed to align outer boundary")
    return best[1], {
        "normalized_perimeter_fit_mse": float(best[0]),
        "source_cycle_reversed": bool(best[2]),
        "cyclic_shift": int(best[3]),
        "corner_original_vertex_indices": [
            int(best[1][offset]) for offset in (0, 27, 51, 78)
        ],
    }


def broad_mask_preflight(body: bpy.types.Object) -> dict[str, Any]:
    faces = faces_of(body)
    patch_faces = {
        int(polygon.index)
        for polygon in body.data.polygons
        if int(polygon.material_index) == PATCH_MATERIAL_INDEX
    }
    if len(patch_faces) != EXPECTED_OLD_PATCH_FACES:
        raise RuntimeError(f"old patch face count drifted: {len(patch_faces)}")
    adjacency = topology_core.face_adjacency(faces)
    region_faces = topology_core.expand_face_rings(
        patch_faces, adjacency, EXTERIOR_FACE_RINGS
    )
    topology = topology_core.topology_record(faces, region_faces)
    boundary_edges = topology_core.boundary_edges_for_region(faces, region_faces)
    cycles = topology_core.ordered_boundary_cycles(boundary_edges)
    if len(region_faces) != EXPECTED_REGION_FACES:
        raise RuntimeError(f"broad region face count drifted: {len(region_faces)}")
    if int(topology["vertex_count"]) != EXPECTED_REGION_VERTICES:
        raise RuntimeError(f"broad region vertex count drifted: {topology['vertex_count']}")
    if topology["component_count"] != 1 or topology["is_one_disk"] is not True:
        raise RuntimeError("broad region is not one connected disk")
    if len(cycles) != 1 or len(cycles[0]) != EXPECTED_BOUNDARY_VERTICES:
        raise RuntimeError("broad region does not expose the exact 102-vertex cycle")
    boundary_cycle, alignment = choose_boundary_alignment(cycles[0], body)
    region_vertices = {
        int(vertex) for face_index in region_faces for vertex in faces[face_index]
    }
    removable = region_vertices.difference(boundary_cycle)
    if len(removable) != EXPECTED_REMOVABLE_VERTICES:
        raise RuntimeError(f"removable broad-region vertex count drifted: {len(removable)}")
    boundary_world_position_sha256 = canonical_sha256(
        [
            vector_record(body.matrix_world @ body.data.vertices[index].co)
            for index in boundary_cycle
        ]
    )
    return {
        "faces": faces,
        "old_patch_faces": patch_faces,
        "region_faces": region_faces,
        "region_vertices": region_vertices,
        "removable_vertices": removable,
        "boundary_cycle": boundary_cycle,
        "boundary_edges": boundary_edges,
        "topology": topology,
        "alignment": alignment,
        "boundary_world_position_sha256": boundary_world_position_sha256,
    }


def boundary_inward_hints(
    body: bpy.types.Object,
    region_faces: set[int],
    boundary_cycle: Sequence[int],
) -> dict[int, Vector]:
    faces = faces_of(body)
    vertex_neighbors: dict[int, set[int]] = defaultdict(set)
    vertex_faces: dict[int, set[int]] = defaultdict(set)
    for face_index, face in enumerate(faces):
        for offset, first in enumerate(face):
            second = face[(offset + 1) % len(face)]
            vertex_neighbors[first].add(second)
            vertex_neighbors[second].add(first)
            vertex_faces[first].add(face_index)
    world = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    boundary_edges = [
        (world[boundary_cycle[index + 1]] - world[boundary_cycle[index]]).length
        for index in range(len(boundary_cycle) - 1)
    ] + [(world[boundary_cycle[0]] - world[boundary_cycle[-1]]).length]
    target_step = statistics.median(boundary_edges)
    hints: dict[int, Vector] = {}
    for vertex_index in boundary_cycle:
        outside_neighbors = [
            neighbor
            for neighbor in vertex_neighbors[vertex_index]
            if any(face not in region_faces for face in vertex_faces[neighbor])
            and neighbor not in boundary_cycle
        ]
        if not outside_neighbors:
            outside_neighbors = [
                neighbor
                for neighbor in vertex_neighbors[vertex_index]
                if neighbor not in boundary_cycle
            ]
        if not outside_neighbors:
            hints[vertex_index] = Vector()
            continue
        outside_average = sum((world[index] for index in outside_neighbors), Vector()) / len(
            outside_neighbors
        )
        direction = world[vertex_index] - outside_average
        if direction.length <= 1.0e-12:
            hints[vertex_index] = Vector()
        else:
            hints[vertex_index] = direction.normalized() * target_step
    return hints


def row_frames(
    boundary_positions: Mapping[tuple[int, int], Vector]
) -> tuple[list[Vector], list[Vector], list[Vector], list[Vector]]:
    left = [boundary_positions[(0, row)] for row in range(GRID_HEIGHT)]
    right = [
        boundary_positions[(GRID_WIDTH - 1, row)] for row in range(GRID_HEIGHT)
    ]
    centers = [(first + second) * 0.5 for first, second in zip(left, right)]
    laterals: list[Vector] = []
    normals: list[Vector] = []
    previous_normal: Vector | None = None
    for row in range(GRID_HEIGHT):
        if row == 0:
            tangent = centers[1] - centers[0]
        elif row == GRID_HEIGHT - 1:
            tangent = centers[-1] - centers[-2]
        else:
            tangent = centers[row + 1] - centers[row - 1]
        lateral = right[row] - left[row]
        if tangent.length <= 1.0e-12 or lateral.length <= 1.0e-12:
            raise RuntimeError("degenerate centerline-sweep frame")
        tangent.normalize()
        lateral.normalize()
        normal = lateral.cross(tangent)
        if normal.length <= 1.0e-12:
            raise RuntimeError("centerline-sweep frame collapsed")
        normal.normalize()
        if previous_normal is None:
            if normal.dot(r24_base.OUTWARD) < 0.0:
                normal.negate()
        elif normal.dot(previous_normal) < 0.0:
            normal.negate()
        laterals.append(lateral)
        normals.append(normal)
        previous_normal = normal.copy()
    return left, right, centers, normals


def paired_fold_displacement(u: float, t: float) -> tuple[float, set[str]]:
    tags: set[str] = set()
    value = 0.0
    interior = smoothstep((1.0 - abs(u)) / 0.18) * smoothstep(t / 0.10) * smoothstep(
        (1.0 - t) / 0.08
    )
    if interior <= 0.0:
        return 0.0, tags

    mons = 0.0042 * compact_bump(u, 0.62) * compact_bump(t - 0.16, 0.18)
    value += mons
    if mons > 0.00025:
        tags.add("mons")

    major_window = interval_window(t, 0.18, 0.72, 0.10)
    major_center = 0.33 - 0.035 * smoothstep((t - 0.52) / 0.20)
    major_left = 0.0082 * compact_bump(u + major_center, 0.15) * major_window
    major_right = 0.0075 * compact_bump(u - (major_center + 0.012), 0.16) * major_window
    value += major_left + major_right
    if major_left > 0.00030:
        tags.add("labia_majora_left")
    if major_right > 0.00030:
        tags.add("labia_majora_right")

    sulci = -0.0016 * major_window * (
        compact_bump(u + 0.205, 0.060) + compact_bump(u - 0.215, 0.064)
    )
    value += sulci

    minor_window = interval_window(t, 0.28, 0.66, 0.07)
    minor_left = 0.0046 * compact_bump(u + 0.090, 0.050) * minor_window
    minor_right = 0.0039 * compact_bump(u - 0.108, 0.055) * minor_window
    value += minor_left + minor_right
    if minor_left > 0.00020:
        tags.add("labia_minora_left")
    if minor_right > 0.00020:
        tags.add("labia_minora_right")

    vestibule = -0.0030 * compact_bump(u, 0.145) * interval_window(t, 0.31, 0.68, 0.06)
    value += vestibule
    if vestibule < -0.00020:
        tags.add("vestibule")

    hood = 0.0040 * compact_bump(u, 0.16) * compact_bump(t - 0.285, 0.085)
    glans = 0.0016 * compact_bump(u + 0.008, 0.055) * compact_bump(t - 0.315, 0.040)
    value += hood + glans
    if hood + glans > 0.00020:
        tags.add("clitoral_hood_glans")

    fourchette = 0.0022 * compact_bump(u, 0.17) * compact_bump(t - 0.695, 0.055)
    value += fourchette
    if fourchette > 0.00018:
        tags.add("posterior_fourchette")

    perineum = 0.0010 * compact_bump(u, 0.30) * interval_window(t, 0.72, 0.88, 0.05)
    value += perineum
    if perineum > 0.00012:
        tags.add("external_perineum")

    return max(-0.0040, min(0.0100, value * interior)), tags


def construct_grid_positions(
    body: bpy.types.Object,
    boundary_cycle: Sequence[int],
    region_faces: set[int],
) -> dict[str, Any]:
    faces = faces_of(body)
    region_vertices = sorted(
        {int(vertex) for face_index in region_faces for vertex in faces[face_index]}
    )
    boundary_by_key = {
        key: int(vertex_index) for key, vertex_index in zip(PERIMETER_KEYS, boundary_cycle)
    }
    boundary_parameters = {
        int(vertex_index): (
            (float(U_COORDS[key[0]]) + 1.0) * 0.5,
            float(T_COORDS[key[1]]),
        )
        for key, vertex_index in boundary_by_key.items()
    }
    boundary_vertices = set(boundary_parameters)
    interior_vertices = [index for index in region_vertices if index not in boundary_vertices]
    interior_lookup = {vertex: row for row, vertex in enumerate(interior_vertices)}
    neighbors: dict[int, set[int]] = defaultdict(set)
    for face_index in region_faces:
        face = faces[int(face_index)]
        for offset, first in enumerate(face):
            second = face[(offset + 1) % len(face)]
            neighbors[int(first)].add(int(second))
            neighbors[int(second)].add(int(first))
    matrix = np.zeros((len(interior_vertices), len(interior_vertices)), dtype=np.float64)
    rhs = np.zeros((len(interior_vertices), 2), dtype=np.float64)
    for vertex in interior_vertices:
        row = interior_lookup[vertex]
        linked = sorted(neighbors[vertex])
        if not linked:
            raise RuntimeError("isolated vertex in broad disk parameterization")
        matrix[row, row] = float(len(linked))
        for neighbor in linked:
            if neighbor in interior_lookup:
                matrix[row, interior_lookup[neighbor]] -= 1.0
            elif neighbor in boundary_parameters:
                rhs[row] += np.asarray(boundary_parameters[neighbor], dtype=np.float64)
            else:
                raise RuntimeError("broad disk adjacency escaped the qualified region")
    solved = np.linalg.solve(matrix, rhs)
    source_parameters: dict[int, tuple[float, float]] = dict(boundary_parameters)
    for vertex, row in interior_lookup.items():
        source_parameters[int(vertex)] = (
            float(solved[row, 0]),
            float(solved[row, 1]),
        )

    world_positions = {
        index: body.matrix_world @ body.data.vertices[index].co for index in region_vertices
    }
    normal_matrix = body.matrix_world.to_3x3().inverted().transposed()
    world_normals = {}
    for index in region_vertices:
        normal = normal_matrix @ body.data.vertices[index].normal
        if normal.length <= 1.0e-12:
            raise RuntimeError("zero source normal in qualified broad disk")
        normal.normalize()
        world_normals[index] = normal

    source_triangles: list[dict[str, Any]] = []
    signed_areas = []
    zero_area_boundary_triangle_count = 0
    for face_index in sorted(region_faces):
        face = list(map(int, faces[face_index]))
        for offset in range(1, len(face) - 1):
            indices = (face[0], face[offset], face[offset + 1])
            parameter = [source_parameters[index] for index in indices]
            signed_area = 0.5 * (
                (parameter[1][0] - parameter[0][0])
                * (parameter[2][1] - parameter[0][1])
                - (parameter[1][1] - parameter[0][1])
                * (parameter[2][0] - parameter[0][0])
            )
            if abs(signed_area) <= 1.0e-14:
                zero_area_boundary_triangle_count += 1
                continue
            signed_areas.append(float(signed_area))
            source_triangles.append(
                {
                    "face_index": int(face_index),
                    "indices": indices,
                    "parameter": parameter,
                    "signed_area": float(signed_area),
                }
            )

    def barycentric(
        point: tuple[float, float],
        triangle: Sequence[tuple[float, float]],
    ) -> tuple[float, float, float] | None:
        first, second, third = triangle
        denominator = (
            (second[1] - third[1]) * (first[0] - third[0])
            + (third[0] - second[0]) * (first[1] - third[1])
        )
        if abs(denominator) <= 1.0e-14:
            return None
        first_weight = (
            (second[1] - third[1]) * (point[0] - third[0])
            + (third[0] - second[0]) * (point[1] - third[1])
        ) / denominator
        second_weight = (
            (third[1] - first[1]) * (point[0] - third[0])
            + (first[0] - third[0]) * (point[1] - third[1])
        ) / denominator
        third_weight = 1.0 - first_weight - second_weight
        return float(first_weight), float(second_weight), float(third_weight)

    baseline: dict[int, Vector] = {}
    sampled_source_normals: dict[int, Vector] = {}
    sample_records = []
    boundary_local_to_original = {
        grid_id(*key): original for key, original in boundary_by_key.items()
    }
    for row in range(GRID_HEIGHT):
        for column in range(GRID_WIDTH):
            local_id = grid_id(column, row)
            if local_id in boundary_local_to_original:
                original = boundary_local_to_original[local_id]
                baseline[local_id] = world_positions[original].copy()
                sampled_source_normals[local_id] = world_normals[original].copy()
                sample_records.append(
                    {
                        "local_id": local_id,
                        "boundary_original_vertex": original,
                    }
                )
                continue
            target = (
                (float(U_COORDS[column]) + 1.0) * 0.5,
                float(T_COORDS[row]),
            )
            best = None
            for triangle in source_triangles:
                weights = barycentric(target, triangle["parameter"])
                if weights is None:
                    continue
                minimum_weight = min(weights)
                if minimum_weight < -2.0e-8:
                    continue
                if best is None or minimum_weight > best[0]:
                    best = (minimum_weight, triangle, weights)
            if best is None:
                raise RuntimeError(
                    f"target grid point {local_id} lies outside harmonic source triangulation"
                )
            _, triangle, weights = best
            indices = triangle["indices"]
            point = sum(
                (world_positions[index] * weight for index, weight in zip(indices, weights)),
                Vector(),
            )
            source_normal = sum(
                (world_normals[index] * weight for index, weight in zip(indices, weights)),
                Vector(),
            )
            if source_normal.length <= 1.0e-12:
                raise RuntimeError("barycentric source normal collapsed")
            source_normal.normalize()
            baseline[local_id] = point
            sampled_source_normals[local_id] = source_normal
            sample_records.append(
                {
                    "local_id": local_id,
                    "source_face_index": int(triangle["face_index"]),
                    "source_triangle_vertices": list(map(int, indices)),
                    "barycentric": [round(float(value), 12) for value in weights],
                }
            )

    normals: dict[int, Vector] = {}
    for row in range(GRID_HEIGHT):
        for column in range(GRID_WIDTH):
            local_id = grid_id(column, row)
            left_id = grid_id(max(0, column - 1), row)
            right_id = grid_id(min(GRID_WIDTH - 1, column + 1), row)
            top_id = grid_id(column, max(0, row - 1))
            bottom_id = grid_id(column, min(GRID_HEIGHT - 1, row + 1))
            lateral = baseline[right_id] - baseline[left_id]
            tangent = baseline[bottom_id] - baseline[top_id]
            normal = lateral.cross(tangent)
            if normal.length <= 1.0e-12:
                normal = sampled_source_normals[local_id].copy()
            else:
                normal.normalize()
                if normal.dot(sampled_source_normals[local_id]) < 0.0:
                    normal.negate()
                normal = normal.lerp(sampled_source_normals[local_id], 0.24)
                normal.normalize()
            normals[local_id] = normal

    positions: dict[int, Vector] = {}
    semantic: dict[str, set[int]] = defaultdict(set)
    t_parameter: dict[int, float] = {}
    displacement_values = []
    boundary_ids = set(boundary_local_to_original)
    for row in range(GRID_HEIGHT):
        t = float(T_COORDS[row])
        for column in range(GRID_WIDTH):
            local_id = grid_id(column, row)
            u = float(U_COORDS[column])
            displacement, tags = paired_fold_displacement(u, t)
            if local_id in boundary_ids:
                displacement = 0.0
                tags = set()
            positions[local_id] = baseline[local_id] + normals[local_id] * displacement
            displacement_values.append(abs(displacement))
            for tag in tags:
                semantic[tag].add(local_id)
            t_parameter[local_id] = t

    centers = [
        (baseline[grid_id(13, row)] + baseline[grid_id(14, row)]) * 0.5
        for row in range(GRID_HEIGHT)
    ]
    center_normals = [
        (normals[grid_id(13, row)] + normals[grid_id(14, row)]).normalized()
        for row in range(GRID_HEIGHT)
    ]
    frame_evidence = {
        "centerline_world": [vector_record(value) for value in centers],
        "normal_world": [vector_record(value) for value in center_normals],
        "normal_adjacent_minimum_dot": min(
            center_normals[index].dot(center_normals[index + 1])
            for index in range(len(center_normals) - 1)
        ),
        "maximum_centerline_step_m": max(
            (centers[index + 1] - centers[index]).length
            for index in range(len(centers) - 1)
        ),
        "maximum_feature_displacement_m": max(displacement_values, default=0.0),
    }
    return {
        "positions_world": positions,
        "semantic_local": semantic,
        "t_parameter": t_parameter,
        "normals": [
            (normals[grid_id(13, row)] + normals[grid_id(14, row)]).normalized()
            for row in range(GRID_HEIGHT)
        ],
        "boundary_positions": {
            key: world_positions[original] for key, original in boundary_by_key.items()
        },
        "frame_evidence": frame_evidence,
        "parameterization_evidence": {
            "method": "uniform_harmonic_convex_rectangle_plus_exact_source_triangle_barycentric_resampling",
            "source_region_vertex_count": len(region_vertices),
            "source_region_face_count": len(region_faces),
            "interior_solved_vertex_count": len(interior_vertices),
            "source_triangle_count": len(source_triangles),
            "zero_area_boundary_triangle_count_skipped": zero_area_boundary_triangle_count,
            "positive_parameter_triangle_count": sum(value > 0.0 for value in signed_areas),
            "negative_parameter_triangle_count": sum(value < 0.0 for value in signed_areas),
            "minimum_absolute_parameter_triangle_area": min(
                (abs(value) for value in signed_areas), default=0.0
            ),
            "source_parameter_sha256": canonical_sha256(
                {
                    str(index): [round(value[0], 12), round(value[1], 12)]
                    for index, value in sorted(source_parameters.items())
                }
            ),
            "grid_source_sample_sha256": canonical_sha256(sample_records),
            "straight_cross_row_baseline_used": False,
            "fixed_outward_direction_used": False,
            "central_lift_used": False,
            "boundary_inward_hint_used": False,
        },
    }


def harmonic_grid_weights(
    body: bpy.types.Object,
    boundary_cycle: Sequence[int],
) -> dict[int, dict[str, float]]:
    boundary_by_key = dict(zip(PERIMETER_KEYS, boundary_cycle))
    records: dict[int, dict[str, float]] = {
        grid_id(*key): original_weight_record(body, original)
        for key, original in boundary_by_key.items()
    }
    boundary_ids = set(records)
    interior_ids = [
        grid_id(column, row)
        for row in range(GRID_HEIGHT)
        for column in range(GRID_WIDTH)
        if grid_id(column, row) not in boundary_ids
    ]
    interior_lookup = {local_id: index for index, local_id in enumerate(interior_ids)}
    bone_names = sorted({name for record in records.values() for name in record})
    if not bone_names:
        raise RuntimeError("broad boundary has no native rig weights")
    bone_lookup = {name: index for index, name in enumerate(bone_names)}
    matrix = np.zeros((len(interior_ids), len(interior_ids)), dtype=np.float64)
    rhs = np.zeros((len(interior_ids), len(bone_names)), dtype=np.float64)
    for local_id in interior_ids:
        row_index = interior_lookup[local_id]
        column, row = grid_key(local_id)
        neighbors = []
        for delta_column, delta_row in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            other_column = column + delta_column
            other_row = row + delta_row
            if 0 <= other_column < GRID_WIDTH and 0 <= other_row < GRID_HEIGHT:
                neighbors.append(grid_id(other_column, other_row))
        matrix[row_index, row_index] = float(len(neighbors))
        for neighbor in neighbors:
            if neighbor in interior_lookup:
                matrix[row_index, interior_lookup[neighbor]] -= 1.0
            else:
                for name, weight in records[neighbor].items():
                    rhs[row_index, bone_lookup[name]] += float(weight)
    solved = np.linalg.solve(matrix, rhs)
    for local_id in interior_ids:
        values = {
            name: max(0.0, float(solved[interior_lookup[local_id], column]))
            for name, column in bone_lookup.items()
            if float(solved[interior_lookup[local_id], column]) > 1.0e-10
        }
        if not values:
            # This should not occur, but the nearest exact perimeter record is
            # a deterministic, native-rig-only fallback.
            column, row = grid_key(local_id)
            nearest_key = min(
                boundary_by_key,
                key=lambda key: (key[0] - column) ** 2 + (key[1] - row) ** 2,
            )
            values = dict(records[grid_id(*nearest_key)])
        records[local_id] = r23_core.top_four_normalized(values)
    return records


def block_outer_loop(
    start_column: int, start_row: int, width_cells: int, height_cells: int
) -> list[int]:
    result: list[int] = []
    result.extend(
        grid_id(column, start_row)
        for column in range(start_column, start_column + width_cells + 1)
    )
    result.extend(
        grid_id(start_column + width_cells, row)
        for row in range(start_row + 1, start_row + height_cells + 1)
    )
    result.extend(
        grid_id(column, start_row + height_cells)
        for column in range(start_column + width_cells - 1, start_column - 1, -1)
    )
    result.extend(
        grid_id(start_column, row)
        for row in range(start_row + height_cells - 1, start_row, -1)
    )
    expected = 2 * (width_cells + height_cells)
    if len(result) != expected or len(set(result)) != expected:
        raise RuntimeError("recess block perimeter drifted")
    return result


def average_weights(records: Sequence[Mapping[str, float]]) -> dict[str, float]:
    values: dict[str, float] = defaultdict(float)
    for record in records:
        for name, weight in record.items():
            values[name] += float(weight) / len(records)
    return r23_core.top_four_normalized(dict(values))


def prepare_patch(body: bpy.types.Object, preflight: Mapping[str, Any]) -> dict[str, Any]:
    geometry = construct_grid_positions(
        body,
        preflight["boundary_cycle"],
        preflight["region_faces"],
    )
    positions: dict[int, Vector] = geometry["positions_world"]
    weights = harmonic_grid_weights(body, preflight["boundary_cycle"])
    semantic: dict[str, set[int]] = defaultdict(set)
    for name, values in geometry["semantic_local"].items():
        semantic[name].update(values)
    t_parameter: dict[int, float] = dict(geometry["t_parameter"])
    uv: dict[int, tuple[float, float]] = {
        grid_id(column, row): (
            (float(U_COORDS[column]) + 1.0) * 0.5,
            1.0 - float(T_COORDS[row]),
        )
        for row in range(GRID_HEIGHT)
        for column in range(GRID_WIDTH)
    }

    recesses = (
        {
            "name": "urethral_meatus",
            "start_column": 13,
            "start_row": 9,
            "width_cells": 1,
            "height_cells": 1,
            "inner_scale": 0.34,
            "rim_height_m": 0.0013,
            "cap_depth_m": 0.0016,
            "t": 0.42,
        },
        {
            "name": "vaginal_introitus",
            "start_column": 12,
            "start_row": 12,
            "width_cells": 2,
            "height_cells": 2,
            "inner_scale": 0.46,
            "rim_height_m": 0.0020,
            "cap_depth_m": 0.0036,
            "t": 0.56,
        },
        {
            "name": "anal_verge",
            "start_column": 12,
            "start_row": 20,
            "width_cells": 2,
            "height_cells": 2,
            "inner_scale": 0.40,
            "rim_height_m": 0.0015,
            "cap_depth_m": 0.0026,
            "t": 0.90,
        },
    )
    skip_cells: set[tuple[int, int]] = set()
    recess_records = []
    next_local_id = GRID_WIDTH * GRID_HEIGHT
    faces: list[tuple[list[int], int]] = []

    for spec in recesses:
        for row in range(spec["start_row"], spec["start_row"] + spec["height_cells"]):
            for column in range(
                spec["start_column"], spec["start_column"] + spec["width_cells"]
            ):
                if (column, row) in skip_cells:
                    raise RuntimeError("recess blocks overlap")
                skip_cells.add((column, row))

    def base_face_tag(column: int, row: int) -> int:
        u = (float(U_COORDS[column]) + float(U_COORDS[column + 1])) * 0.5
        t = (float(T_COORDS[row]) + float(T_COORDS[row + 1])) * 0.5
        candidates = []
        for name, center_u, width_u, start_t, end_t in (
            ("labia_majora_left", -0.33, 0.13, 0.17, 0.73),
            ("labia_majora_right", 0.34, 0.14, 0.17, 0.73),
            ("labia_minora_left", -0.09, 0.055, 0.27, 0.67),
            ("labia_minora_right", 0.108, 0.060, 0.27, 0.67),
        ):
            if abs(u - center_u) <= width_u and start_t <= t <= end_t:
                candidates.append(name)
        if candidates:
            return FEATURE_CODES[candidates[-1]]
        if abs(u) < 0.20 and abs(t - 0.285) < 0.075:
            return FEATURE_CODES["clitoral_hood_glans"]
        if abs(u) < 0.17 and 0.32 <= t <= 0.68:
            return FEATURE_CODES["vestibule"]
        if abs(u) < 0.22 and abs(t - 0.695) < 0.055:
            return FEATURE_CODES["posterior_fourchette"]
        if abs(u) < 0.32 and 0.72 <= t <= 0.88:
            return FEATURE_CODES["external_perineum"]
        if abs(u) < 0.62 and t < 0.24:
            return FEATURE_CODES["mons"]
        return FEATURE_CODES["base"]

    for row in range(GRID_HEIGHT - 1):
        for column in range(GRID_WIDTH - 1):
            if (column, row) in skip_cells:
                continue
            faces.append(
                (
                    [
                        grid_id(column, row),
                        grid_id(column + 1, row),
                        grid_id(column + 1, row + 1),
                        grid_id(column, row + 1),
                    ],
                    base_face_tag(column, row),
                )
            )

    for spec in recesses:
        outer = block_outer_loop(
            spec["start_column"],
            spec["start_row"],
            spec["width_cells"],
            spec["height_cells"],
        )
        outer_points = [positions[index] for index in outer]
        center = sum(outer_points, Vector()) / len(outer_points)
        row_center = spec["start_row"] + spec["height_cells"] * 0.5
        frame_row = min(GRID_HEIGHT - 1, max(0, int(round(row_center))))
        normal = geometry["normals"][frame_row].copy()
        inner = []
        for outer_id, outer_point in zip(outer, outer_points):
            local_id = next_local_id
            next_local_id += 1
            radial = outer_point - center
            positions[local_id] = (
                center
                + radial * float(spec["inner_scale"])
                + normal * float(spec["rim_height_m"])
            )
            weights[local_id] = dict(weights[outer_id])
            uv[local_id] = tuple(
                (np.asarray(uv[outer_id]) * float(spec["inner_scale"])
                + np.asarray([0.5, 1.0 - float(spec["t"])])
                * (1.0 - float(spec["inner_scale"]))).tolist()
            )
            t_parameter[local_id] = float(spec["t"])
            semantic[f"{spec['name']}__rim"].add(local_id)
            inner.append(local_id)
        center_id = next_local_id
        next_local_id += 1
        positions[center_id] = center - normal * float(spec["cap_depth_m"])
        weights[center_id] = average_weights([weights[index] for index in outer])
        uv[center_id] = (0.5, 1.0 - float(spec["t"]))
        t_parameter[center_id] = float(spec["t"])
        semantic[f"{spec['name']}__cap"].add(center_id)
        tag = FEATURE_CODES[spec["name"]]
        for offset in range(len(outer)):
            following = (offset + 1) % len(outer)
            faces.append(
                ([outer[offset], outer[following], inner[following], inner[offset]], tag)
            )
            faces.append(([inner[offset], inner[following], center_id], tag))
        recess_records.append(
            {
                **dict(spec),
                "outer_local_ids": outer,
                "rim_local_ids": inner,
                "cap_local_id": center_id,
                "rim_count": len(inner),
                "outer_count": len(outer),
            }
        )

    # Exact disjointness is structural, not a centroid inference.
    rim_names = [
        "urethral_meatus__rim",
        "vaginal_introitus__rim",
        "anal_verge__rim",
    ]
    for index, first in enumerate(rim_names):
        for second in rim_names[index + 1 :]:
            if semantic[first].intersection(semantic[second]):
                raise RuntimeError("external endpoint rim sets overlap")

    inverse = body.matrix_world.inverted()
    positions_local = {
        local_id: inverse @ point for local_id, point in positions.items()
    }
    return {
        "positions_world": positions,
        "positions_local": positions_local,
        "weights": weights,
        "uv": uv,
        "faces": faces,
        "semantic_local": semantic,
        "t_parameter": t_parameter,
        "recesses": recess_records,
        "frame_evidence": geometry["frame_evidence"],
        "parameterization_evidence": geometry["parameterization_evidence"],
        "skip_cell_count": len(skip_cells),
        "local_vertex_count": len(positions_local),
        "local_face_count": len(faces),
    }


def apply_patch(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    preflight: Mapping[str, Any],
    prepared: Mapping[str, Any],
) -> dict[str, Any]:
    selected_faces = set(map(int, preflight["region_faces"]))
    removable = set(map(int, preflight["removable_vertices"]))
    boundary_cycle = list(map(int, preflight["boundary_cycle"]))
    boundary_by_local = {
        grid_id(*key): int(original)
        for key, original in zip(PERIMETER_KEYS, boundary_cycle)
    }
    bm = bmesh.new()
    try:
        bm.from_mesh(body.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        original_vertex_id = bm.verts.layers.int.new("__R24_ORIGINAL_VERTEX_ID")
        original_face_id = bm.faces.layers.int.new("__R24_ORIGINAL_FACE_ID")
        original_loop_id = bm.loops.layers.int.new("__R24_ORIGINAL_LOOP_ID")
        local_id_layer = bm.verts.layers.int.new("__R24_LOCAL_ID")
        feature_layer = bm.faces.layers.int.new("__R24_FEATURE_CODE")
        for vertex in bm.verts:
            vertex[original_vertex_id] = int(vertex.index)
            vertex[local_id_layer] = -1
        loop_counter = 0
        for face in bm.faces:
            face[original_face_id] = int(face.index)
            face[feature_layer] = 0
            for loop in face.loops:
                loop[original_loop_id] = loop_counter
                loop_counter += 1
        group_names = {int(group.index): group.name for group in body.vertex_groups}
        frozen_before = r23_author.bmesh_frozen_snapshot(
            bm,
            original_vertex_id,
            original_face_id,
            original_loop_id,
            removable,
            selected_faces,
            group_names,
        )
        original_vertices = {int(vertex[original_vertex_id]): vertex for vertex in bm.verts}
        original_faces = {int(face[original_face_id]): face for face in bm.faces}
        local_vertices: dict[int, bmesh.types.BMVert] = {}
        for local_id, original in boundary_by_local.items():
            vertex = original_vertices[original]
            vertex[local_id_layer] = int(local_id)
            local_vertices[int(local_id)] = vertex
        bmesh.ops.delete(
            bm,
            geom=[original_faces[index] for index in sorted(selected_faces)],
            context="FACES_ONLY",
        )
        bmesh.ops.delete(
            bm,
            geom=[original_vertices[index] for index in sorted(removable)],
            context="VERTS",
        )
        for local_id in sorted(prepared["positions_local"]):
            if local_id in local_vertices:
                continue
            vertex = bm.verts.new(Vector(prepared["positions_local"][local_id]))
            vertex[original_vertex_id] = -1
            vertex[local_id_layer] = int(local_id)
            local_vertices[int(local_id)] = vertex
        bm.verts.index_update()
        bm.verts.ensure_lookup_table()

        new_faces: list[bmesh.types.BMFace] = []
        for local_ids, feature_code in prepared["faces"]:
            face = bm.faces.new([local_vertices[int(index)] for index in local_ids])
            face[original_face_id] = -1
            face[feature_layer] = int(feature_code)
            face.material_index = 0
            face.smooth = True
            for loop in face.loops:
                loop[original_loop_id] = -1
            new_faces.append(face)

        deform = bm.verts.layers.deform.active
        if deform is None:
            raise RuntimeError("R19 primary surface lacks deform weights")
        group_indices = {group.name: int(group.index) for group in body.vertex_groups}
        rig_bones = {bone.name for bone in rig.data.bones}
        for local_id, record in prepared["weights"].items():
            if local_id in boundary_by_local:
                continue
            vertex = local_vertices[int(local_id)]
            for name, weight in record.items():
                if name not in group_indices or name not in rig_bones:
                    raise RuntimeError(f"new weight references non-native rig group: {name}")
                vertex[deform][group_indices[name]] = float(weight)

        for layer_name in bm.loops.layers.uv.keys():
            layer = bm.loops.layers.uv.get(layer_name)
            for face in new_faces:
                for loop in face.loops:
                    loop[layer].uv = prepared["uv"][int(loop.vert[local_id_layer])]

        bm.normal_update()

        def seam_dot_values() -> list[float]:
            new_face_set = set(new_faces)
            values = []
            for edge in bm.edges:
                linked = list(edge.link_faces)
                if len(linked) != 2:
                    continue
                first_new = linked[0] in new_face_set
                second_new = linked[1] in new_face_set
                if first_new != second_new:
                    values.append(float(linked[0].normal.dot(linked[1].normal)))
            return values

        seam_before = seam_dot_values()
        if seam_before and statistics.median(seam_before) < 0.0:
            for face in new_faces:
                face.normal_flip()
            bm.normal_update()
        seam_after = seam_dot_values()

        frozen_after = r23_author.bmesh_frozen_snapshot(
            bm,
            original_vertex_id,
            original_face_id,
            original_loop_id,
            removable,
            selected_faces,
            group_names,
        )
        if frozen_before != frozen_after:
            raise RuntimeError("out-of-mask R19 state changed during no-save simulation")

        bm.verts.index_update()
        bm.faces.index_update()
        local_to_global = {
            int(vertex[local_id_layer]): int(vertex.index)
            for vertex in bm.verts
            if int(vertex[local_id_layer]) >= 0
        }
        patch_face_indices = [int(face.index) for face in new_faces]
        feature_faces: dict[int, list[int]] = defaultdict(list)
        for face in new_faces:
            feature_faces[int(face[feature_layer])].append(int(face.index))

        bm.verts.layers.int.remove(original_vertex_id)
        bm.verts.layers.int.remove(local_id_layer)
        bm.faces.layers.int.remove(original_face_id)
        bm.faces.layers.int.remove(feature_layer)
        bm.loops.layers.int.remove(original_loop_id)
        bm.to_mesh(body.data)
    finally:
        bm.free()
    body.data.update(calc_edges=True, calc_edges_loose=True)
    semantic_global = {
        name: sorted(int(local_to_global[index]) for index in values)
        for name, values in prepared["semantic_local"].items()
    }
    t_global = {
        int(local_to_global[local_id]): float(value)
        for local_id, value in prepared["t_parameter"].items()
    }
    return {
        "frozen_surviving_sha256_before": frozen_before,
        "frozen_surviving_sha256_after": frozen_after,
        "frozen_surviving_exact": frozen_before == frozen_after,
        "local_to_global": local_to_global,
        "patch_face_indices": patch_face_indices,
        "feature_faces": {str(key): sorted(value) for key, value in feature_faces.items()},
        "semantic_global": semantic_global,
        "t_global": t_global,
        "seam_dot_before_orientation_fix": seam_before,
        "seam_dot_after_orientation_fix": seam_after,
    }


def topology_and_semantic_gates(
    body: bpy.types.Object,
    applied: Mapping[str, Any],
    prepared: Mapping[str, Any],
) -> dict[str, Any]:
    faces = faces_of(body)
    patch_faces = set(map(int, applied["patch_face_indices"]))
    patch_topology = topology_core.topology_record(faces, patch_faces)
    whole_topology = topology_core.topology_record(faces, range(len(faces)))
    edge_faces = topology_core.edge_face_map(faces)
    patch_vertices = {
        int(vertex) for face_index in patch_faces for vertex in faces[face_index]
    }
    patch_edges = {
        edge for face_index in patch_faces for edge in topology_core.face_edges(faces[face_index])
    }
    patch_nonmanifold = [
        list(edge) for edge in sorted(patch_edges) if len(edge_faces.get(edge, ())) != 2
    ]
    areas = []
    edge_ratios = []
    for face_index in patch_faces:
        polygon = body.data.polygons[face_index]
        areas.append(float(polygon.area))
        lengths = []
        vertices = list(map(int, polygon.vertices))
        for offset, first in enumerate(vertices):
            second = vertices[(offset + 1) % len(vertices)]
            lengths.append(
                (body.data.vertices[first].co - body.data.vertices[second].co).length
            )
        positive = [value for value in lengths if value > 1.0e-12]
        edge_ratios.append(max(positive) / min(positive) if positive else math.inf)

    seam_values = list(map(float, applied["seam_dot_after_orientation_fix"]))
    seam_minimum = min(seam_values, default=-1.0)
    seam_median = statistics.median(seam_values) if seam_values else -1.0
    seam_maximum_dihedral_degrees = math.degrees(
        math.acos(max(-1.0, min(1.0, seam_minimum)))
    )

    semantic = {
        name: set(map(int, values)) for name, values in applied["semantic_global"].items()
    }
    required = (
        "mons",
        "labia_majora_left",
        "labia_majora_right",
        "labia_minora_left",
        "labia_minora_right",
        "vestibule",
        "clitoral_hood_glans",
        "urethral_meatus__rim",
        "urethral_meatus__cap",
        "vaginal_introitus__rim",
        "vaginal_introitus__cap",
        "posterior_fourchette",
        "external_perineum",
        "anal_verge__rim",
        "anal_verge__cap",
    )
    nonempty = {name: bool(semantic.get(name)) for name in required}
    rim_names = (
        "urethral_meatus__rim",
        "vaginal_introitus__rim",
        "anal_verge__rim",
    )
    rim_disjoint = True
    rim_overlaps = []
    for index, first in enumerate(rim_names):
        for second in rim_names[index + 1 :]:
            overlap = semantic.get(first, set()).intersection(semantic.get(second, set()))
            if overlap:
                rim_disjoint = False
                rim_overlaps.append({"first": first, "second": second, "vertices": sorted(overlap)})

    t_global = {int(key): float(value) for key, value in applied["t_global"].items()}
    centroids_t = {
        name: float(sum(t_global[index] for index in semantic[name]) / len(semantic[name]))
        for name in required
        if semantic.get(name)
    }
    order_checks = {
        "hood_before_urethra": centroids_t["clitoral_hood_glans"]
        < centroids_t["urethral_meatus__rim"],
        "urethra_before_introitus": centroids_t["urethral_meatus__rim"]
        < centroids_t["vaginal_introitus__rim"],
        "introitus_before_fourchette": centroids_t["vaginal_introitus__rim"]
        < centroids_t["posterior_fourchette"],
        "fourchette_before_perineum": centroids_t["posterior_fourchette"]
        < centroids_t["external_perineum"],
        "perineum_before_anal_verge": centroids_t["external_perineum"]
        < centroids_t["anal_verge__rim"],
    }
    semantic_hashes = {
        name: topology_core.canonical_index_sha256(values)
        for name, values in semantic.items()
    }

    bm = bmesh.new()
    try:
        bm.from_mesh(body.data)
        exact_report = exact_intersections.exact_nonadjacent_intersection_report(
            bm, include_pair_details=True
        )
    finally:
        bm.free()
    patch_intersection_pairs = [
        record
        for record in exact_report["pairs"]
        if record.get("overlap_character") == "genuine_penetration"
        and any(int(index) in patch_faces for index in record["face_indices"])
    ]

    checks = {
        "one_patch_component": patch_topology["component_count"] == 1,
        "patch_is_one_disk": patch_topology["is_one_disk"] is True,
        "whole_body_component_count_preserved": whole_topology["component_count"] == 1,
        "patch_boundary_cycle_exact": patch_topology["boundary_cycle_count"] == 1
        and patch_topology["boundary_cycle_lengths"] == [EXPECTED_BOUNDARY_VERTICES],
        "patch_associated_nonmanifold_edges_zero": len(patch_nonmanifold) == 0,
        "degenerate_patch_faces_zero": min(areas, default=0.0) > 1.0e-10,
        "frozen_surviving_state_exact": applied["frozen_surviving_exact"] is True,
        "all_required_semantic_sets_nonempty": all(nonempty.values()),
        "three_endpoint_rim_sets_disjoint": rim_disjoint,
        "clinical_longitudinal_order": all(order_checks.values()),
        "patch_exact_intersections_zero": len(patch_intersection_pairs) == 0,
        "seam_minimum_normal_dot_at_least_0_70": seam_minimum >= 0.70,
        "seam_median_normal_dot_at_least_0_94": seam_median >= 0.94,
        "maximum_seam_dihedral_at_most_45_degrees": seam_maximum_dihedral_degrees <= 45.0,
        "maximum_patch_edge_ratio_at_most_8": max(edge_ratios, default=math.inf) <= 8.0,
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "patch_topology": patch_topology,
        "whole_topology": whole_topology,
        "patch_vertex_count": len(patch_vertices),
        "patch_face_count": len(patch_faces),
        "patch_associated_nonmanifold_edges": patch_nonmanifold,
        "minimum_patch_face_area_local_units_squared": min(areas, default=0.0),
        "maximum_patch_edge_ratio": max(edge_ratios, default=math.inf),
        "seam_normal_dot": {
            "count": len(seam_values),
            "minimum": seam_minimum,
            "median": seam_median,
            "maximum": max(seam_values, default=-1.0),
            "maximum_dihedral_degrees": seam_maximum_dihedral_degrees,
        },
        "semantic_nonempty": nonempty,
        "semantic_vertex_index_sha256": semantic_hashes,
        "semantic_centroid_centerline_parameter": centroids_t,
        "semantic_order_checks": order_checks,
        "rim_disjoint": rim_disjoint,
        "rim_overlaps": rim_overlaps,
        "exact_intersections": {
            "whole_exact_genuine_pair_count": exact_report[
                "exact_genuine_penetration_pair_count"
            ],
            "patch_related_exact_genuine_pair_count": len(patch_intersection_pairs),
            "patch_related_pairs": patch_intersection_pairs,
        },
    }


def clinical_material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = color
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.48
        bsdf.inputs["Specular IOR Level"].default_value = 0.28
    return material


def render_evidence(
    body: bpy.types.Object,
    applied: Mapping[str, Any],
    directory: Path,
) -> dict[str, Any]:
    directory.mkdir()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.008, 0.012, 0.018)
    scene.view_settings.look = "AgX - Medium High Contrast"
    for obj in list(scene.objects):
        if obj.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(obj, do_unlink=True)

    body.hide_render = True
    clinical = body.copy()
    clinical.data = body.data.copy()
    clinical.name = "R24_FeatureAligned_ClinicalDiagnostic"
    bpy.context.collection.objects.link(clinical)
    clinical.hide_render = False
    clinical.data.materials.clear()
    clay = clinical_material("R24_UniformClinicalClay", (0.46, 0.285, 0.235, 1.0))
    clinical.data.materials.append(clay)
    for polygon in clinical.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True
    modifier = clinical.modifiers.new("R24_ClinicalSubdivision", "SUBSURF")
    modifier.subdivision_type = "CATMULL_CLARK"
    modifier.levels = 1
    modifier.render_levels = 1

    points = [clinical.matrix_world @ vertex.co for vertex in clinical.data.vertices]
    minimum = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z
    patch_indices = sorted(
        {
            int(vertex)
            for face_index in applied["patch_face_indices"]
            for vertex in clinical.data.polygons[int(face_index)].vertices
        }
    )
    pelvis = sum(
        (clinical.matrix_world @ clinical.data.vertices[index].co for index in patch_indices),
        Vector(),
    ) / len(patch_indices)

    for name, location, energy, size in (
        ("R24_FA_Key", (2.2, -3.2, 2.8), 980.0, 3.8),
        ("R24_FA_Fill", (-2.5, -2.0, 1.5), 580.0, 3.0),
        ("R24_FA_Rim", (0.8, 2.8, 2.2), 760.0, 2.8),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        light.location = location
        bpy.context.collection.objects.link(light)
        r24_base.look_at(light, pelvis)

    camera_data = bpy.data.cameras.new("R24_FeatureAligned_Camera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R24_FeatureAligned_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera

    views = {
        "ordinary_full_front.png": (
            Vector((center.x, minimum.y - 3.0, center.z)),
            center,
            height * 1.08,
        ),
        "ordinary_left_three_quarter.png": (
            Vector((center.x - 2.0, minimum.y - 2.6, center.z)),
            center,
            height * 1.08,
        ),
        "ordinary_side_profile.png": (
            Vector((minimum.x - 3.0, center.y, center.z)),
            center,
            height * 1.08,
        ),
        "ordinary_rear.png": (
            Vector((center.x, maximum.y + 3.0, center.z)),
            center,
            height * 1.08,
        ),
        "protected_clinical_front.png": (
            Vector((pelvis.x, pelvis.y - 1.6, pelvis.z)),
            pelvis,
            0.34,
        ),
        "protected_clinical_left_three_quarter.png": (
            Vector((pelvis.x - 0.88, pelvis.y - 1.28, pelvis.z)),
            pelvis,
            0.34,
        ),
        "protected_clinical_profile.png": (
            Vector((pelvis.x - 1.6, pelvis.y, pelvis.z)),
            pelvis,
            0.34,
        ),
        "protected_clinical_inferior.png": (
            Vector((pelvis.x, pelvis.y - 0.72, pelvis.z - 0.72)),
            pelvis,
            0.32,
        ),
        "protected_clinical_rear.png": (
            Vector((pelvis.x, pelvis.y + 1.6, pelvis.z)),
            pelvis,
            0.34,
        ),
    }
    rendered = []
    for filename, (location, target, scale) in views.items():
        camera.location = location
        camera.data.ortho_scale = scale
        r24_base.look_at(camera, target)
        scene.render.filepath = str(directory / filename)
        bpy.ops.render.render(write_still=True)
        rendered.append(filename)

    wire = clinical.copy()
    wire.data = clinical.data.copy()
    wire.name = "R24_FeatureAligned_WireDiagnostic"
    bpy.context.collection.objects.link(wire)
    wire.hide_render = False
    for modifier in list(wire.modifiers):
        wire.modifiers.remove(modifier)
    wire.data.materials.clear()
    wire.data.materials.append(clinical_material("R24_Wire_Cyan", (0.0, 0.55, 0.72, 1.0)))
    wireframe = wire.modifiers.new("R24_FeatureAligned_Wireframe", "WIREFRAME")
    wireframe.thickness = 0.00042
    wireframe.offset = 1.0
    wireframe.use_replace = True
    clinical.hide_render = True
    camera.location = Vector((pelvis.x, pelvis.y - 1.6, pelvis.z))
    camera.data.ortho_scale = 0.34
    r24_base.look_at(camera, pelvis)
    scene.render.filepath = str(directory / "protected_clinical_wire.png")
    bpy.ops.render.render(write_still=True)
    rendered.append("protected_clinical_wire.png")
    wire.hide_render = True

    mask = clinical.copy()
    mask.data = clinical.data.copy()
    mask.name = "R24_FeatureAligned_SemanticMaskDiagnostic"
    bpy.context.collection.objects.link(mask)
    for modifier in list(mask.modifiers):
        mask.modifiers.remove(modifier)
    mask.data.materials.clear()
    palette = {
        0: (0.12, 0.12, 0.12, 1.0),
        1: (0.30, 0.30, 0.30, 1.0),
        2: (0.86, 0.58, 0.10, 1.0),
        3: (0.88, 0.12, 0.10, 1.0),
        4: (1.00, 0.38, 0.08, 1.0),
        5: (0.05, 0.70, 0.86, 1.0),
        6: (0.10, 0.28, 0.95, 1.0),
        7: (0.40, 0.12, 0.60, 1.0),
        8: (0.96, 0.92, 0.08, 1.0),
        9: (1.00, 0.05, 0.70, 1.0),
        10: (0.08, 0.82, 0.24, 1.0),
        11: (0.94, 0.50, 0.12, 1.0),
        12: (0.04, 0.72, 0.56, 1.0),
        13: (0.64, 0.12, 0.86, 1.0),
    }
    for code in sorted(palette):
        mask.data.materials.append(
            clinical_material(f"R24_FeatureMask_{code:02d}", palette[code])
        )
    for polygon in mask.data.polygons:
        polygon.material_index = 0
    for code, face_indices in applied["feature_faces"].items():
        for face_index in face_indices:
            mask.data.polygons[int(face_index)].material_index = int(code)
    mask.hide_render = False
    camera.location = Vector((pelvis.x, pelvis.y - 1.6, pelvis.z))
    camera.data.ortho_scale = 0.34
    r24_base.look_at(camera, pelvis)
    scene.render.filepath = str(directory / "protected_clinical_feature_mask.png")
    bpy.ops.render.render(write_still=True)
    rendered.append("protected_clinical_feature_mask.png")

    return {
        "directory": relative(directory),
        "rendered": rendered,
        "ordinary_views": [name for name in rendered if name.startswith("ordinary_")],
        "protected_clinical_views": [
            name for name in rendered if name.startswith("protected_clinical_")
        ],
        "uniform_clinical_material": clay.name,
        "body_texture_or_runtime_material_used_for_geometry_judgment": False,
        "feature_mask_palette": {str(key): list(value) for key, value in palette.items()},
    }


def main() -> None:
    worker = Path(__file__).resolve()
    if sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("immutable R19 source hash drifted")
    if not CHART_DIAGNOSTIC.is_file() or sha256(CHART_DIAGNOSTIC) != CHART_DIAGNOSTIC_SHA256:
        raise RuntimeError("bound chart-diagnostic evidence drifted")
    if OUTPUT.exists():
        raise RuntimeError("append-only R24 feature-aligned attempt already exists")
    OUTPUT.mkdir(parents=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    body = bpy.data.objects.get(BODY_NAME)
    rig = bpy.data.objects.get(RIG_NAME)
    if body is None or rig is None:
        raise RuntimeError("exact R19 body or rig absent")
    r24_base.clear_pose(rig)
    source_shape_key_count = len(body.data.shape_keys.key_blocks) if body.data.shape_keys else 0

    preflight = broad_mask_preflight(body)
    prepared = prepare_patch(body, preflight)
    applied = apply_patch(body, rig, preflight, prepared)
    gates = topology_and_semantic_gates(body, applied, prepared)
    render_dir = OUTPUT / "private_owner_review"
    renders = render_evidence(body, applied, render_dir)

    report = {
        "schema": "kira.avatar.r24_feature_aligned_centerline_surface_simulation.v1",
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
        "bound_failure_evidence": {
            "path": relative(CHART_DIAGNOSTIC),
            "sha256": CHART_DIAGNOSTIC_SHA256,
            "old_patch_chart_v_range": [-0.618241, 0.322545],
            "old_patch_chart_w_range_m": [-0.09755, 0.02401],
            "patch_normal_dot_fixed_outward_range": [-0.0447, 0.9947],
            "interpretation": (
                "The old patch cannot be represented or displaced reliably as one fixed-direction scalar chart."
            ),
        },
        "method": {
            "id": "R24_BROAD_FEATURE_ALIGNED_ROTATING_CENTERLINE_SWEEP_V1",
            "donor_coordinates_used": False,
            "donor_topology_used": False,
            "fixed_outward_scalar_displacement_used": False,
            "straight_cross_row_interior_baseline_used": False,
            "central_lift_used": False,
            "boundary_inward_hint_used": False,
            "harmonic_rectangle_parameterization_used": True,
            "exact_source_surface_barycentric_resampling_used": True,
            "boolean_used": False,
            "floating_or_separate_anatomy_object_created": False,
            "through_tract_created": False,
            "broad_region_exterior_face_rings": EXTERIOR_FACE_RINGS,
            "grid": {
                "width": GRID_WIDTH,
                "height": GRID_HEIGHT,
                "perimeter_vertices": len(PERIMETER_KEYS),
                "feature_aligned_u": list(U_COORDS),
                "centerline_t": list(T_COORDS),
            },
            "paired_fold_geometry": True,
            "three_distinct_shallow_capped_recess_sets": True,
            "uniform_clinical_material_first": True,
        },
        "preflight": {
            "old_patch_face_count": len(preflight["old_patch_faces"]),
            "broad_region_face_count": len(preflight["region_faces"]),
            "broad_region_vertex_count": len(preflight["region_vertices"]),
            "removable_interior_vertex_count": len(preflight["removable_vertices"]),
            "outer_boundary_vertex_count": len(preflight["boundary_cycle"]),
            "outer_boundary_original_index_sha256": topology_core.canonical_index_sha256(
                preflight["boundary_cycle"]
            ),
            "outer_boundary_world_position_sha256": preflight[
                "boundary_world_position_sha256"
            ],
            "topology": preflight["topology"],
            "alignment": preflight["alignment"],
        },
        "prepared": {
            "local_vertex_count_including_reused_boundary": prepared["local_vertex_count"],
            "local_face_count": prepared["local_face_count"],
            "skipped_grid_cell_count_for_explicit_recess_topology": prepared[
                "skip_cell_count"
            ],
            "frame": prepared["frame_evidence"],
            "parameterization": prepared["parameterization_evidence"],
            "recesses": prepared["recesses"],
        },
        "application": {
            "frozen_surviving_sha256_before": applied[
                "frozen_surviving_sha256_before"
            ],
            "frozen_surviving_sha256_after": applied[
                "frozen_surviving_sha256_after"
            ],
            "frozen_surviving_exact": applied["frozen_surviving_exact"],
            "patch_face_index_sha256": topology_core.canonical_index_sha256(
                applied["patch_face_indices"]
            ),
            "patch_face_count": len(applied["patch_face_indices"]),
        },
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
            "External private visual/deformation simulation only. No internal route, physiology, "
            "elimination, reproduction, pregnancy, sensation, owner approval, runtime readiness, "
            "or biological function is implemented or claimed."
        ),
    }
    (OUTPUT / "SIMULATION_REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": report["status"], "output": str(OUTPUT)}))


if __name__ == "__main__":
    main()
