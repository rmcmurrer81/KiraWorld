"""Build a bounded quad Hermite/Coons superior-pubic bridge from R24.

R25D--R25F proved that radial fills and a center/cross-grid construction can
close topology while creating visible spikes, teeth, or a flat panel.  This
independent trial keeps every real cut-window boundary vertex pinned:

* the exterior loop is split at the two true upper/lower surface transitions;
* its upper and lower boundary chains are arc-length resampled to equal counts
  by subdividing the existing upper boundary edges in place;
* the two short transition edges become the left/right Coons side boundaries;
* a compact all-quad Hermite/Coons strip is created between those four real
  boundaries, with no center vertex, radial fan, grid_fill, Boolean, or remesh;
* the hidden inner cut cycle is closed separately.

This is static, private engineering evidence only.  A closed mesh is not a
visual pass; encoded flat/wire/normal/silhouette diagnostics remain mandatory.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_preserved_surface_trial_r24_raised_branches/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "PRESERVED_SURFACE_TRIAL_R24_RAISED_BRANCHES.blend"
)
TRIAL_LABEL = os.environ.get("KIRA_COONS_TRIAL_LABEL", "R25G").upper()
TRIAL_SLUG = TRIAL_LABEL.lower()
ANTERIOR_BULGE_METERS = float(
    os.environ.get("KIRA_COONS_ANTERIOR_BULGE_METERS", "0.0")
)
SUPERIOR_BULGE_METERS = float(
    os.environ.get("KIRA_COONS_SUPERIOR_BULGE_METERS", "0.0")
)
RELAX_ITERATIONS = int(os.environ.get("KIRA_COONS_RELAX_ITERATIONS", "0"))
RELAX_FACTOR = float(os.environ.get("KIRA_COONS_RELAX_FACTOR", "0.35"))
BOUNDARY_MODE = os.environ.get(
    "KIRA_COONS_BOUNDARY_MODE", "transition_edges"
).strip().lower()
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    f"biological_static_likeness_v23_{TRIAL_SLUG}_coons_bridge_trial"
)
OUT.mkdir(parents=True, exist_ok=True)
BLEND_PATH = (
    OUT
    / f"BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_{TRIAL_LABEL}_"
    "COONS_BRIDGE_TRIAL.blend"
)

WINDOW = {
    "half_x": 0.018,
    "min_y": -0.165,
    "max_y": -0.045,
    "min_z": 0.809,
    "max_z": 0.824,
}
SIDE_SEGMENTS = int(os.environ.get("KIRA_COONS_SIDE_SEGMENTS", "6"))


def coordinate_key(vertex: bmesh.types.BMVert) -> tuple[float, float, float]:
    return tuple(round(value, 7) for value in vertex.co)


def edge_key(
    edge: bmesh.types.BMEdge,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    return tuple(sorted(coordinate_key(vertex) for vertex in edge.verts))


def components(
    edges: list[bmesh.types.BMEdge],
) -> list[list[bmesh.types.BMEdge]]:
    by_vertex: dict[bmesh.types.BMVert, list[bmesh.types.BMEdge]] = {}
    for edge in edges:
        for vertex in edge.verts:
            by_vertex.setdefault(vertex, []).append(edge)
    unseen = set(edges)
    result = []
    while unseen:
        seed = unseen.pop()
        current_component = [seed]
        stack = [seed]
        while stack:
            current = stack.pop()
            for vertex in current.verts:
                for neighbor in by_vertex[vertex]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        current_component.append(neighbor)
                        stack.append(neighbor)
        result.append(current_component)
    return result


def ordered_cycle_vertices(
    cycle: list[bmesh.types.BMEdge],
) -> list[bmesh.types.BMVert]:
    adjacency: dict[bmesh.types.BMVert, list[bmesh.types.BMVert]] = {}
    for edge in cycle:
        a, b = edge.verts
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    if any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise RuntimeError("cannot order non-simple bridge cycle")
    start = min(
        adjacency,
        key=lambda vertex: (vertex.co.x, vertex.co.z, vertex.co.y),
    )
    result = [start]
    previous = None
    current = start
    while True:
        candidates = [
            vertex for vertex in adjacency[current] if vertex is not previous
        ]
        if not candidates:
            raise RuntimeError("bridge cycle traversal stopped early")
        if previous is None:
            next_vertex = max(candidates, key=lambda vertex: vertex.co.y)
        else:
            next_vertex = candidates[0]
        if next_vertex is start:
            break
        if next_vertex in result:
            raise RuntimeError("bridge cycle traversal repeated a vertex")
        result.append(next_vertex)
        previous, current = current, next_vertex
    if len(result) != len(adjacency):
        raise RuntimeError("bridge cycle traversal missed vertices")
    return result


def topology_counts(bm: bmesh.types.BMesh) -> dict[str, int]:
    return {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": sum(len(edge.link_faces) == 1 for edge in bm.edges),
        "wire_edges": sum(len(edge.link_faces) == 0 for edge in bm.edges),
        "nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2 for edge in bm.edges
        ),
    }


def vertex_surface_normal(vertex: bmesh.types.BMVert) -> Vector:
    normals = [face.normal.copy() for face in vertex.link_faces]
    if not normals:
        return vertex.normal.copy().normalized()
    total = Vector((0.0, 0.0, 0.0))
    for normal in normals:
        total += normal
    if total.length < 1e-10:
        return vertex.normal.copy().normalized()
    return total.normalized()


def smooth_vectors(vectors: list[Vector], radius: int = 3) -> list[Vector]:
    result = []
    for index in range(len(vectors)):
        total = Vector((0.0, 0.0, 0.0))
        count = 0
        for offset in range(-radius, radius + 1):
            candidate = index + offset
            if 0 <= candidate < len(vectors):
                total += vectors[candidate]
                count += 1
        if count and total.length > 1e-10:
            result.append(total.normalized())
        else:
            result.append(vectors[index].copy())
    return result


def path_between(
    ordered: list[bmesh.types.BMVert],
    start_index: int,
    end_index: int,
    step: int,
) -> list[bmesh.types.BMVert]:
    result = [ordered[start_index]]
    current = start_index
    while current != end_index:
        current = (current + step) % len(ordered)
        result.append(ordered[current])
        if len(result) > len(ordered) + 1:
            raise RuntimeError("cycle path traversal overflow")
    return result


def segment_allocations(
    path: list[bmesh.types.BMVert],
    target_segments: int,
) -> list[int]:
    lengths = [
        (path[index + 1].co - path[index].co).length
        for index in range(len(path) - 1)
    ]
    if target_segments < len(lengths):
        raise RuntimeError("target cannot remove pinned boundary vertices")
    remaining = target_segments - len(lengths)
    total = sum(lengths)
    exact_extras = [
        (remaining * length / total) if total else 0.0 for length in lengths
    ]
    extras = [math.floor(value) for value in exact_extras]
    missing = remaining - sum(extras)
    order = sorted(
        range(len(lengths)),
        key=lambda index: exact_extras[index] - extras[index],
        reverse=True,
    )
    for index in order[:missing]:
        extras[index] += 1
    allocations = [1 + value for value in extras]
    if sum(allocations) != target_segments:
        raise RuntimeError("segment allocation did not reach target")
    return allocations


def subdivide_path_to_segments(
    bm: bmesh.types.BMesh,
    path: list[bmesh.types.BMVert],
    allocations: list[int],
) -> list[bmesh.types.BMVert]:
    if len(allocations) != len(path) - 1:
        raise RuntimeError("allocation/path mismatch")
    # Blender 5.1 may rebuild the wrapper for an endpoint when a boundary
    # triangle is split.  Keep immutable coordinates across operations and
    # resolve the current BMesh vertex again after all cuts.
    path_coordinates = [vertex.co.copy() for vertex in path]
    result_coordinates = [path_coordinates[0]]
    for index, segment_count in enumerate(allocations):
        start_coordinate = path_coordinates[index]
        end_coordinate = path_coordinates[index + 1]
        coordinate_map = {
            coordinate_key(vertex): vertex
            for vertex in bm.verts
            if vertex.is_valid
        }
        start = coordinate_map.get(
            tuple(round(value, 7) for value in start_coordinate)
        )
        end = coordinate_map.get(
            tuple(round(value, 7) for value in end_coordinate)
        )
        if start is None or end is None:
            raise RuntimeError(f"could not resolve segment endpoints {index}")
        if segment_count == 1:
            result_coordinates.append(end_coordinate)
            continue
        edge = bm.edges.get((start, end))
        if edge is None:
            raise RuntimeError(f"missing boundary edge at segment {index}")
        direction = end_coordinate - start_coordinate
        length_squared = direction.length_squared
        operation = bmesh.ops.subdivide_edges(
            bm,
            edges=[edge],
            cuts=segment_count - 1,
            use_grid_fill=False,
        )
        new_vertices = [
            element
            for element in operation.get("geom_inner", [])
            if isinstance(element, bmesh.types.BMVert)
        ]
        if len(new_vertices) != segment_count - 1:
            raise RuntimeError(
                f"edge subdivision produced {len(new_vertices)} vertices, "
                f"expected {segment_count - 1}"
            )
        new_vertices.sort(
            key=lambda vertex: (
                (vertex.co - start_coordinate).dot(direction) / length_squared
                if length_squared
                else 0.0
            )
        )
        result_coordinates.extend(vertex.co.copy() for vertex in new_vertices)
        result_coordinates.append(end_coordinate)
    coordinate_map = {
        coordinate_key(vertex): vertex
        for vertex in bm.verts
        if vertex.is_valid
    }
    result = []
    for coordinate in result_coordinates:
        vertex = coordinate_map.get(
            tuple(round(value, 7) for value in coordinate)
        )
        if vertex is None:
            raise RuntimeError("could not resolve subdivided path vertex")
        result.append(vertex)
    return result


def subdivide_single_edge(
    bm: bmesh.types.BMesh,
    start: bmesh.types.BMVert,
    end: bmesh.types.BMVert,
    segments: int,
) -> list[bmesh.types.BMVert]:
    return subdivide_path_to_segments(bm, [start, end], [segments])


def vertex_uv(vertex: bmesh.types.BMVert, uv_layer) -> Vector:
    values = []
    for face in vertex.link_faces:
        for loop in face.loops:
            if loop.vert is vertex:
                values.append(loop[uv_layer].uv.copy())
    if not values:
        return Vector((0.52, 0.38))
    total = Vector((0.0, 0.0))
    for value in values:
        total += value
    return total / len(values)


def cubic_hermite(
    p0: Vector,
    p1: Vector,
    n0: Vector,
    n1: Vector,
    factor: float,
) -> Vector:
    chord = p1 - p0
    length = chord.length
    if length < 1e-10:
        return p0.copy()
    tangent0 = chord - n0 * chord.dot(n0)
    tangent1 = chord - n1 * chord.dot(n1)
    if tangent0.length < 1e-8:
        tangent0 = chord.copy()
    if tangent1.length < 1e-8:
        tangent1 = chord.copy()
    tangent0.normalize()
    tangent1.normalize()
    if tangent0.dot(chord) < 0.0:
        tangent0.negate()
    if tangent1.dot(chord) < 0.0:
        tangent1.negate()
    # Preserve the real lateral correspondence and suppress a normal-estimate
    # induced sideways hook.  The bridge is a superior/inferior surface
    # transition, not a lateral projection.
    tangent0.x = chord.x / length
    tangent1.x = chord.x / length
    if tangent0.length:
        tangent0.normalize()
    if tangent1.length:
        tangent1.normalize()
    derivative0 = tangent0 * min(length * 0.42, 0.034)
    derivative1 = tangent1 * min(length * 0.34, 0.028)
    t = factor
    t2 = t * t
    t3 = t2 * t
    h00 = 2.0 * t3 - 3.0 * t2 + 1.0
    h10 = t3 - 2.0 * t2 + t
    h01 = -2.0 * t3 + 3.0 * t2
    h11 = t3 - t2
    return (
        p0 * h00
        + derivative0 * h10
        + p1 * h01
        + derivative1 * h11
    )


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = max(
    (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
body.name = (
    f"BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_{TRIAL_LABEL}_"
    "COONS_BRIDGE_TRIAL"
)
skin_index = next(
    (
        index
        for index, material in enumerate(body.data.materials)
        if material and material.name == "MBLab_skin3"
    ),
    1,
)

bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
uv_layer = bm.loops.layers.uv.active
baseline = topology_counts(bm)
baseline_boundary_keys = {
    edge_key(edge) for edge in bm.edges if len(edge.link_faces) == 1
}

cut_faces = [
    face
    for face in bm.faces
    if (
        abs(face.calc_center_median().x) <= WINDOW["half_x"]
        and WINDOW["min_y"]
        <= face.calc_center_median().y
        <= WINDOW["max_y"]
        and WINDOW["min_z"]
        <= face.calc_center_median().z
        <= WINDOW["max_z"]
    )
]
if len(cut_faces) != 408:
    raise RuntimeError(f"measured R24 cut changed: {len(cut_faces)} != 408")
bmesh.ops.delete(bm, geom=cut_faces, context="FACES")
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

new_boundary_edges = [
    edge
    for edge in bm.edges
    if (
        len(edge.link_faces) == 1
        and edge_key(edge) not in baseline_boundary_keys
        and all(
            abs(vertex.co.x) <= WINDOW["half_x"] + 0.012
            and WINDOW["min_y"] - 0.025
            <= vertex.co.y
            <= WINDOW["max_y"] + 0.025
            and WINDOW["min_z"] - 0.012
            <= vertex.co.z
            <= WINDOW["max_z"] + 0.012
            for vertex in edge.verts
        )
    )
]
cycles = components(new_boundary_edges)
if len(cycles) != 2:
    raise RuntimeError(f"expected two bridge cycles, found {len(cycles)}")
cycles.sort(
    key=lambda cycle: min(
        vertex.co.y for edge in cycle for vertex in edge.verts
    )
)
outer_cycle, inner_cycle = cycles
ordered = ordered_cycle_vertices(outer_cycle)

boundary_reshape_max_meters = 0.0
if BOUNDARY_MODE == "true_four_sided":
    # The 116-edge outline is not a two-chain slit.  It contains four actual
    # sides: a short lower-abdomen chain, two depth-running side chains, and a
    # longer pubic chain.  R25G/I incorrectly folded those side chains into the
    # "upper" curve, producing a dark panel.  Find the four true corners.
    upper_candidates = [
        (index, vertex)
        for index, vertex in enumerate(ordered)
        if vertex.co.y <= -0.14 and vertex.co.z >= 0.821
    ]
    if len(upper_candidates) < 4:
        raise RuntimeError("could not identify true upper boundary")
    upper_left_index, upper_left = min(
        upper_candidates, key=lambda item: item[1].co.x
    )
    upper_right_index, upper_right = max(
        upper_candidates, key=lambda item: item[1].co.x
    )
    lower_left_index, lower_left = max(
        (
            (index, vertex)
            for index, vertex in enumerate(ordered)
            if vertex.co.x < 0.0 and vertex.co.y > -0.053
        ),
        key=lambda item: item[1].co.y,
    )
    lower_right_index, lower_right = max(
        (
            (index, vertex)
            for index, vertex in enumerate(ordered)
            if vertex.co.x > 0.0 and vertex.co.y > -0.053
        ),
        key=lambda item: item[1].co.y,
    )

    upper_options = (
        path_between(ordered, upper_left_index, upper_right_index, +1),
        path_between(ordered, upper_left_index, upper_right_index, -1),
    )
    upper_path = min(upper_options, key=len)
    lower_options = (
        path_between(ordered, lower_left_index, lower_right_index, +1),
        path_between(ordered, lower_left_index, lower_right_index, -1),
    )
    lower_path = min(
        lower_options,
        key=lambda path: min(vertex.co.z for vertex in path),
    )
    left_side_options = (
        path_between(ordered, upper_left_index, lower_left_index, +1),
        path_between(ordered, upper_left_index, lower_left_index, -1),
    )
    left_side = min(left_side_options, key=len)
    right_side_options = (
        path_between(ordered, upper_right_index, lower_right_index, +1),
        path_between(ordered, upper_right_index, lower_right_index, -1),
    )
    right_side = min(right_side_options, key=len)
    if upper_path[0] is not upper_left:
        upper_path.reverse()
    if lower_path[0] is not lower_left:
        lower_path.reverse()
    if left_side[0] is not upper_left:
        left_side.reverse()
    if right_side[0] is not upper_right:
        right_side.reverse()
    if len(left_side) != len(right_side):
        raise RuntimeError("true side-chain counts differ")
    SIDE_SEGMENTS = len(left_side) - 1

    original_coordinates = {
        vertex: vertex.co.copy()
        for vertex in {
            *upper_path,
            *lower_path,
            *left_side,
            *right_side,
        }
    }

    # Replace only high-frequency cut-edge corrugation.  Endpoints remain the
    # real corners.  The center targets are measured from the retained upper
    # underside and pubic surface, not invented forward cups.
    upper_left_coordinate = upper_path[0].co.copy()
    upper_right_coordinate = upper_path[-1].co.copy()
    for index, vertex in enumerate(upper_path):
        factor = index / (len(upper_path) - 1)
        signed = 2.0 * factor - 1.0
        edge_weight = abs(signed) ** 1.55
        vertex.co.x = (
            upper_left_coordinate.x * (1.0 - factor)
            + upper_right_coordinate.x * factor
        )
        edge_y = (
            upper_left_coordinate.y * (1.0 - factor)
            + upper_right_coordinate.y * factor
        )
        edge_z = (
            upper_left_coordinate.z * (1.0 - factor)
            + upper_right_coordinate.z * factor
        )
        vertex.co.y = -0.148 + (edge_y + 0.148) * edge_weight
        vertex.co.z = 0.822 + (edge_z - 0.822) * edge_weight

    lower_left_coordinate = lower_path[0].co.copy()
    lower_right_coordinate = lower_path[-1].co.copy()
    for index, vertex in enumerate(lower_path):
        factor = index / (len(lower_path) - 1)
        signed = 2.0 * factor - 1.0
        edge_weight = abs(signed) ** 1.60
        vertex.co.x = (
            lower_left_coordinate.x * (1.0 - factor)
            + lower_right_coordinate.x * factor
        )
        edge_y = (
            lower_left_coordinate.y * (1.0 - factor)
            + lower_right_coordinate.y * factor
        )
        edge_z = (
            lower_left_coordinate.z * (1.0 - factor)
            + lower_right_coordinate.z * factor
        )
        vertex.co.y = -0.081 + (edge_y + 0.081) * edge_weight
        vertex.co.z = 0.809 + (edge_z - 0.809) * edge_weight

    # Fair each side independently, then enforce the source's bilateral
    # symmetry.  The shared four corners stay pinned to the just-authored
    # monotone upper/lower chains.
    for _iteration in range(18):
        left_old = [vertex.co.copy() for vertex in left_side]
        right_old = [vertex.co.copy() for vertex in right_side]
        for index in range(1, len(left_side) - 1):
            left_side[index].co = (
                left_old[index] * 0.55
                + (left_old[index - 1] + left_old[index + 1]) * 0.225
            )
            right_side[index].co = (
                right_old[index] * 0.55
                + (right_old[index - 1] + right_old[index + 1]) * 0.225
            )
    for index in range(1, len(left_side) - 1):
        magnitude_x = (
            abs(left_side[index].co.x) + abs(right_side[index].co.x)
        ) * 0.5
        average_y = (left_side[index].co.y + right_side[index].co.y) * 0.5
        average_z = (left_side[index].co.z + right_side[index].co.z) * 0.5
        left_side[index].co = Vector((-magnitude_x, average_y, average_z))
        right_side[index].co = Vector((magnitude_x, average_y, average_z))

    boundary_reshape_max_meters = max(
        (vertex.co - coordinate).length
        for vertex, coordinate in original_coordinates.items()
    )
    bm.normal_update()
    left_upper_coordinate = upper_path[0].co.copy()
    right_upper_coordinate = upper_path[-1].co.copy()
    left_lower_coordinate = lower_path[0].co.copy()
    right_lower_coordinate = lower_path[-1].co.copy()

    target_segments = len(lower_path) - 1
    allocations = segment_allocations(upper_path, target_segments)
    lower_path_coordinates = [vertex.co.copy() for vertex in lower_path]
    left_side_coordinates = [vertex.co.copy() for vertex in left_side]
    right_side_coordinates = [vertex.co.copy() for vertex in right_side]
    upper_path = subdivide_path_to_segments(bm, upper_path, allocations)
    coordinate_map = {
        coordinate_key(vertex): vertex
        for vertex in bm.verts
        if vertex.is_valid
    }
    lower_path = [
        coordinate_map[tuple(round(value, 7) for value in coordinate)]
        for coordinate in lower_path_coordinates
    ]
    left_side = [
        coordinate_map[tuple(round(value, 7) for value in coordinate)]
        for coordinate in left_side_coordinates
    ]
    right_side = [
        coordinate_map[tuple(round(value, 7) for value in coordinate)]
        for coordinate in right_side_coordinates
    ]
else:
    # Historical R25G mode retained for reproducibility of rejected evidence.
    cycle_normals = [vertex_surface_normal(vertex) for vertex in ordered]
    transitions = []
    for index, vertex in enumerate(ordered):
        following_index = (index + 1) % len(ordered)
        normal_a = cycle_normals[index]
        normal_b = cycle_normals[following_index]
        if (
            min(normal_a.z, normal_b.z) < -0.55
            and max(normal_a.z, normal_b.z) > 0.20
        ):
            transitions.append((index, following_index))
    if len(transitions) != 2:
        raise RuntimeError(
            f"expected two upper/lower transitions, got {transitions}"
        )
    corner_pairs = []
    for index_a, index_b in transitions:
        if cycle_normals[index_a].z > cycle_normals[index_b].z:
            lower_index, upper_index = index_a, index_b
        else:
            lower_index, upper_index = index_b, index_a
        corner_pairs.append(
            {
                "lower_index": lower_index,
                "upper_index": upper_index,
                "lower": ordered[lower_index],
                "upper": ordered[upper_index],
            }
        )
    corner_pairs.sort(key=lambda item: item["lower"].co.x)
    left, right = corner_pairs
    path_positive = path_between(
        ordered, left["lower_index"], right["lower_index"], +1
    )
    path_negative = path_between(
        ordered, left["lower_index"], right["lower_index"], -1
    )
    lower_path = max(
        (path_positive, path_negative),
        key=lambda path: sum(vertex_surface_normal(v).z for v in path)
        / len(path),
    )
    if lower_path[0] is not left["lower"]:
        lower_path.reverse()
    upper_positive = path_between(
        ordered, left["upper_index"], right["upper_index"], +1
    )
    upper_negative = path_between(
        ordered, left["upper_index"], right["upper_index"], -1
    )
    upper_path = min(
        (upper_positive, upper_negative),
        key=lambda path: sum(vertex_surface_normal(v).z for v in path)
        / len(path),
    )
    if upper_path[0] is not left["upper"]:
        upper_path.reverse()
    target_segments = len(lower_path) - 1
    allocations = segment_allocations(upper_path, target_segments)
    lower_path_coordinates = [vertex.co.copy() for vertex in lower_path]
    left_upper_coordinate = left["upper"].co.copy()
    left_lower_coordinate = left["lower"].co.copy()
    right_upper_coordinate = right["upper"].co.copy()
    right_lower_coordinate = right["lower"].co.copy()
    upper_path = subdivide_path_to_segments(bm, upper_path, allocations)
    coordinate_map = {
        coordinate_key(vertex): vertex
        for vertex in bm.verts
        if vertex.is_valid
    }
    lower_path = [
        coordinate_map[tuple(round(value, 7) for value in coordinate)]
        for coordinate in lower_path_coordinates
    ]
    upper_path_coordinates = [vertex.co.copy() for vertex in upper_path]
    lower_path_coordinates = [vertex.co.copy() for vertex in lower_path]
    left_upper = coordinate_map[
        tuple(round(value, 7) for value in left_upper_coordinate)
    ]
    left_lower = coordinate_map[
        tuple(round(value, 7) for value in left_lower_coordinate)
    ]
    right_upper = coordinate_map[
        tuple(round(value, 7) for value in right_upper_coordinate)
    ]
    right_lower = coordinate_map[
        tuple(round(value, 7) for value in right_lower_coordinate)
    ]
    left_side = subdivide_single_edge(
        bm, left_upper, left_lower, SIDE_SEGMENTS
    )
    left_side_coordinates = [vertex.co.copy() for vertex in left_side]
    coordinate_map = {
        coordinate_key(vertex): vertex
        for vertex in bm.verts
        if vertex.is_valid
    }
    right_upper = coordinate_map[
        tuple(round(value, 7) for value in right_upper_coordinate)
    ]
    right_lower = coordinate_map[
        tuple(round(value, 7) for value in right_lower_coordinate)
    ]
    right_side = subdivide_single_edge(
        bm, right_upper, right_lower, SIDE_SEGMENTS
    )
    right_side_coordinates = [vertex.co.copy() for vertex in right_side]
    coordinate_map = {
        coordinate_key(vertex): vertex
        for vertex in bm.verts
        if vertex.is_valid
    }
    left_side = [
        coordinate_map[tuple(round(value, 7) for value in coordinate)]
        for coordinate in left_side_coordinates
    ]
    right_side = [
        coordinate_map[tuple(round(value, 7) for value in coordinate)]
        for coordinate in right_side_coordinates
    ]
    upper_path = [
        coordinate_map[tuple(round(value, 7) for value in coordinate)]
        for coordinate in upper_path_coordinates
    ]
    lower_path = [
        coordinate_map[tuple(round(value, 7) for value in coordinate)]
        for coordinate in lower_path_coordinates
    ]
    if (left_side[0].co - left_upper_coordinate).length > 1e-8:
        left_side.reverse()
    if (right_side[0].co - right_upper_coordinate).length > 1e-8:
        right_side.reverse()

if len(upper_path) != len(lower_path):
    raise RuntimeError("resampled upper/lower path counts differ")

# Capture retained-surface normals and UVs only after in-place boundary
# subdivision and before any new patch faces exist.
upper_normals = smooth_vectors(
    [vertex_surface_normal(vertex) for vertex in upper_path],
    radius=3,
)
lower_normals = smooth_vectors(
    [vertex_surface_normal(vertex) for vertex in lower_path],
    radius=3,
)
upper_uvs = (
    [vertex_uv(vertex, uv_layer) for vertex in upper_path]
    if uv_layer is not None
    else [Vector((0.52, 0.38)) for _ in upper_path]
)
lower_uvs = (
    [vertex_uv(vertex, uv_layer) for vertex in lower_path]
    if uv_layer is not None
    else [Vector((0.52, 0.38)) for _ in lower_path]
)
left_uvs = (
    [vertex_uv(vertex, uv_layer) for vertex in left_side]
    if uv_layer is not None
    else [Vector((0.52, 0.38)) for _ in left_side]
)
right_uvs = (
    [vertex_uv(vertex, uv_layer) for vertex in right_side]
    if uv_layer is not None
    else [Vector((0.52, 0.38)) for _ in right_side]
)

column_count = len(lower_path)
rows: list[list[bmesh.types.BMVert]] = [upper_path]
row_uvs: list[list[Vector]] = [upper_uvs]


def base_row(factor: float) -> list[Vector]:
    return [
        cubic_hermite(
            upper_path[index].co,
            lower_path[index].co,
            upper_normals[index],
            lower_normals[index],
            factor,
        )
        for index in range(column_count)
    ]


for row_index in range(1, SIDE_SEGMENTS):
    factor = row_index / SIDE_SEGMENTS
    base = base_row(factor)
    desired_left = left_side[row_index].co.copy()
    desired_right = right_side[row_index].co.copy()
    left_delta = desired_left - base[0]
    right_delta = desired_right - base[-1]
    row = [left_side[row_index]]
    uv_row = [left_uvs[row_index]]
    for column in range(1, column_count - 1):
        horizontal = column / (column_count - 1)
        coordinate = (
            base[column]
            + left_delta * (1.0 - horizontal)
            + right_delta * horizontal
        )
        # An optional bounded center-weighted mound tests whether the deeply
        # recessed retained lower boundary can be hidden by a natural convex
        # pubic transition without moving any true boundary vertex.  It is
        # zero on all four boundaries, so the Coons patch remains pinned.
        lateral_weight = math.sin(math.pi * horizontal) ** 0.65
        vertical_weight = math.sin(math.pi * factor)
        coordinate.y -= (
            ANTERIOR_BULGE_METERS * lateral_weight * vertical_weight
        )
        coordinate.z += (
            SUPERIOR_BULGE_METERS * lateral_weight * vertical_weight
        )
        vertex = bm.verts.new(coordinate)
        row.append(vertex)
        uv = (
            upper_uvs[column] * (1.0 - factor)
            + lower_uvs[column] * factor
        )
        uv += (
            left_uvs[row_index]
            - (
                upper_uvs[0] * (1.0 - factor)
                + lower_uvs[0] * factor
            )
        ) * (1.0 - horizontal)
        uv += (
            right_uvs[row_index]
            - (
                upper_uvs[-1] * (1.0 - factor)
                + lower_uvs[-1] * factor
            )
        ) * horizontal
        uv_row.append(uv)
    row.append(right_side[row_index])
    uv_row.append(right_uvs[row_index])
    rows.append(row)
    row_uvs.append(uv_row)
rows.append(lower_path)
row_uvs.append(lower_uvs)

# Optional bounded harmonic cleanup operates only on newly authored interior
# vertices.  Every real upper/lower/side boundary remains pinned.  This is
# useful for proving whether residual teeth come from noisy retained boundary
# sampling rather than from the four-sided patch topology itself.
for _iteration in range(RELAX_ITERATIONS):
    old = [[vertex.co.copy() for vertex in row] for row in rows]
    updates = []
    for row_index in range(1, SIDE_SEGMENTS):
        for column in range(1, column_count - 1):
            neighbor_average = (
                old[row_index - 1][column]
                + old[row_index + 1][column]
                + old[row_index][column - 1]
                + old[row_index][column + 1]
            ) * 0.25
            coordinate = (
                old[row_index][column] * (1.0 - RELAX_FACTOR)
                + neighbor_average * RELAX_FACTOR
            )
            updates.append((rows[row_index][column], coordinate))
    for vertex, coordinate in updates:
        vertex.co = coordinate

outer_faces: list[bmesh.types.BMFace] = []
face_uv_maps = []
for row_index in range(SIDE_SEGMENTS):
    for column in range(column_count - 1):
        vertices = (
            rows[row_index][column],
            rows[row_index][column + 1],
            rows[row_index + 1][column + 1],
            rows[row_index + 1][column],
        )
        if len(set(vertices)) != 4:
            raise RuntimeError("Coons strip produced a degenerate quad")
        face = bm.faces.new(vertices)
        face.material_index = skin_index
        face.smooth = True
        outer_faces.append(face)
        face_uv_maps.append(
            (
                row_uvs[row_index][column],
                row_uvs[row_index][column + 1],
                row_uvs[row_index + 1][column + 1],
                row_uvs[row_index + 1][column],
            )
        )

if uv_layer is not None:
    for face, values in zip(outer_faces, face_uv_maps):
        for loop, value in zip(face.loops, values):
            loop[uv_layer].uv = value

# The inner cycle is the hidden back wall of the old fold.  Close it
# independently; it does not participate in the visible Hermite/Coons strip.
before_inner_faces = set(bm.faces)
bmesh.ops.triangle_fill(
    bm,
    edges=inner_cycle,
    use_beauty=True,
    use_dissolve=False,
)
inner_faces = [face for face in bm.faces if face not in before_inner_faces]
for face in inner_faces:
    face.material_index = skin_index
    face.smooth = True
    if uv_layer is not None:
        for loop in face.loops:
            loop[uv_layer].uv = Vector((0.52, 0.38))

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.normal_update()
final = topology_counts(bm)

new_vertices = {
    vertex
    for row in rows[1:-1]
    for vertex in row[1:-1]
}
new_edges = {
    edge
    for face in outer_faces
    for edge in face.edges
}
new_face_areas = [face.calc_area() for face in outer_faces]
new_edge_lengths = [(edge.verts[1].co - edge.verts[0].co).length for edge in new_edges]
bridge_bounds = {
    axis: {
        "min": min(getattr(vertex.co, axis) for vertex in new_vertices),
        "max": max(getattr(vertex.co, axis) for vertex in new_vertices),
    }
    for axis in ("x", "y", "z")
}

if (
    final["boundary_edges"] != baseline["boundary_edges"]
    or final["wire_edges"] != baseline["wire_edges"]
    or final["nonmanifold_gt2_edges"]
    != baseline["nonmanifold_gt2_edges"]
):
    raise RuntimeError(
        f"topology gate failed: baseline={baseline}, final={final}"
    )
if min(new_face_areas) <= 1e-10:
    raise RuntimeError(f"near-zero Coons quad area: {min(new_face_areas)}")
if max(new_edge_lengths) > 0.025:
    raise RuntimeError(
        f"Coons bridge edge too long/spike-prone: {max(new_edge_lengths)}"
    )

bm.to_mesh(body.data)
bm.free()
body.data.update()
mesh_validation_changed = body.data.validate(clean_customdata=False)
for polygon in body.data.polygons:
    polygon.use_smooth = True

body["status"] = "REJECTED ENGINEERING TRIAL - RENDERED VISUAL REVIEW REQUIRED"
body["method"] = (
    "MEASURED 408-FACE CUT + PINNED REAL FOUR-SIDED BOUNDARY + "
    "ARC-LENGTH RESAMPLED ALL-QUAD HERMITE/COONS STRIP + HIDDEN INNER CAP"
)
body["trial_label"] = TRIAL_LABEL
body["boundary_mode"] = BOUNDARY_MODE
body["anterior_bulge_meters"] = ANTERIOR_BULGE_METERS
body["superior_bulge_meters"] = SUPERIOR_BULGE_METERS
body["interior_relax_iterations"] = RELAX_ITERATIONS
body["interior_relax_factor"] = RELAX_FACTOR
body["boolean_used"] = False
body["global_remesh_used"] = False
body["grid_fill_used"] = False
body["radial_fan_used"] = False
body["donor_surface_transferred"] = False
body["runtime_activation_allowed"] = False
body["movement_started"] = False

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
report = {
    "schema": f"kira.avatar.v23.{TRIAL_SLUG}.coons_bridge_trial.v1",
    "trial_label": TRIAL_LABEL,
    "boundary_mode": BOUNDARY_MODE,
    "status": body["status"],
    "source": str(SOURCE),
    "output": str(BLEND_PATH),
    "window": WINDOW,
    "cut_faces": len(cut_faces),
    "outer_cycle_edges": len(outer_cycle),
    "inner_cycle_edges": len(inner_cycle),
    "upper_boundary_original_vertices": len(allocations) + 1,
    "upper_boundary_resampled_vertices": len(upper_path),
    "lower_boundary_vertices": len(lower_path),
    "side_segments": SIDE_SEGMENTS,
    "maximum_boundary_reshape_meters": boundary_reshape_max_meters,
    "anterior_bulge_meters": ANTERIOR_BULGE_METERS,
    "superior_bulge_meters": SUPERIOR_BULGE_METERS,
    "interior_relax_iterations": RELAX_ITERATIONS,
    "interior_relax_factor": RELAX_FACTOR,
    "outer_quad_faces": len(outer_faces),
    "inner_faces_created": len(inner_faces),
    "created_interior_vertices": len(new_vertices),
    "bridge_bounds": bridge_bounds,
    "minimum_outer_quad_area_m2": min(new_face_areas),
    "maximum_bridge_edge_length_m": max(new_edge_lengths),
    "mesh_validate_changed_data": bool(mesh_validation_changed),
    "baseline_topology": baseline,
    "final_topology": final,
    "boundary_edge_delta": final["boundary_edges"] - baseline["boundary_edges"],
    "wire_edge_delta": final["wire_edges"] - baseline["wire_edges"],
    "nonmanifold_gt2_delta": (
        final["nonmanifold_gt2_edges"]
        - baseline["nonmanifold_gt2_edges"]
    ),
    "prohibited_methods": {
        "boolean": False,
        "global_remesh": False,
        "grid_fill": False,
        "center_or_radial_fan": False,
        "donor_surface_transfer": False,
    },
    "visual_promotion": (
        "BLOCKED UNTIL FLAT, WIRE, NORMAL, FRONT/SIDE/THREE-QUARTER "
        "SILHOUETTE AND GAP AUDITS PASS"
    ),
    "scope": {
        "static_review_only": True,
        "movement": False,
        "activation": False,
        "runtime_attachment": False,
        "synthetic_robert": False,
        "kira": False,
        "clothing": False,
    },
}
(OUT / f"{TRIAL_LABEL}_COONS_BRIDGE_BUILD_REPORT.json").write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
print(BLEND_PATH)
print(json.dumps(report, indent=2))
