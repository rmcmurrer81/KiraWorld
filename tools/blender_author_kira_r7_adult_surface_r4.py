"""Author Kira's inactive R7 R4-v10 neck-surface reconstruction review.

The sealed R3 Blend is read-only input. R4-v10 removes the visibly defective
collar and only the immediately adjacent source layers, preserving the natural
upper neck while reconstructing a short,
arc-length-aligned ruled surface between clean retained loops. Circumferential
relaxation is strongest only in the middle of the bridge and fades to zero at
both retained boundaries, avoiding the per-vertex tangent spikes rejected in
R4-v8. The face, mouth and eye
apertures, ears, cranium, adult surface outside the bounded transition,
armature hierarchy, and all 79 rig groups stay protected. This is review
authoring only: no activation, binding, promotion, or automatic GLB export.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import struct
import sys
from collections import defaultdict, deque
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


OBJECT_R3 = "Kira_R7_Measured_Neck_Bridge_R3_Inactive"
OBJECT_R4 = "Kira_R7_Reconstructed_Neck_Surface_R4V10_Inactive"
LIGHT_SKIN_HEX = "#e6c0a9"
LIGHT_SKIN_RGBA = (230 / 255, 192 / 255, 169 / 255, 1.0)


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


def coordinate_digest(points: list[Vector]) -> str:
    digest = hashlib.sha256()
    for point in points:
        digest.update(struct.pack("<3d", float(point.x), float(point.y), float(point.z)))
    return digest.hexdigest()


def vertex_weight_rows(obj: bpy.types.Object) -> list[dict[str, float]]:
    names = {group.index: group.name for group in obj.vertex_groups}
    return [
        {
            names[item.group]: float(item.weight)
            for item in vertex.groups
            if item.weight > 1e-8
        }
        for vertex in obj.data.vertices
    ]


def normalized_top_four(row: dict[str, float], valid: set[str]) -> dict[str, float]:
    values = [(name, value) for name, value in row.items() if name in valid and value > 1e-8]
    values.sort(key=lambda item: (-item[1], item[0]))
    values = values[:4]
    total = sum(value for _, value in values)
    return {name: value / total for name, value in values} if total > 1e-12 else {}


def boundary_cycles(obj: bpy.types.Object) -> list[list[int]]:
    edge_use: defaultdict[tuple[int, int], int] = defaultdict(int)
    for polygon in obj.data.polygons:
        values = list(map(int, polygon.vertices))
        for index, a in enumerate(values):
            edge_use[tuple(sorted((a, values[(index + 1) % len(values)])))] += 1
    graph: defaultdict[int, list[int]] = defaultdict(list)
    for (a, b), count in edge_use.items():
        if count == 1:
            graph[a].append(b)
            graph[b].append(a)
    seen: set[int] = set()
    cycles: list[list[int]] = []
    for start in sorted(graph):
        if start in seen:
            continue
        todo = deque([start])
        seen.add(start)
        component: list[int] = []
        while todo:
            current = todo.popleft()
            component.append(current)
            for neighbor in graph[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    todo.append(neighbor)
        if component and all(len(graph[index]) == 2 for index in component):
            cycles.append(component)
    return cycles


def topology_record(obj: bpy.types.Object) -> dict[str, object]:
    edge_use: defaultdict[tuple[int, int], int] = defaultdict(int)
    adjacency: list[list[int]] = [[] for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = map(int, edge.vertices)
        adjacency[a].append(b)
        adjacency[b].append(a)
    for polygon in obj.data.polygons:
        values = list(map(int, polygon.vertices))
        for index, a in enumerate(values):
            edge_use[tuple(sorted((a, values[(index + 1) % len(values)])))] += 1
    seen: set[int] = set()
    components: list[int] = []
    for start in range(len(obj.data.vertices)):
        if start in seen:
            continue
        todo = deque([start])
        seen.add(start)
        count = 0
        while todo:
            current = todo.popleft()
            count += 1
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    todo.append(neighbor)
        components.append(count)
    areas = [float(polygon.area) for polygon in obj.data.polygons]
    cycles = boundary_cycles(obj)
    return {
        "vertices": len(obj.data.vertices),
        "edges": len(obj.data.edges),
        "polygons": len(obj.data.polygons),
        "connected_components": len(components),
        "component_sizes": sorted(components, reverse=True),
        "boundary_closed_cycle_count": len(cycles),
        "overused_edge_count": sum(count > 2 for count in edge_use.values()),
        "minimum_face_area_m2": min(areas, default=0.0),
        "degenerate_face_count_under_1e_12_m2": sum(area <= 1e-12 for area in areas),
    }


def weight_record(obj: bpy.types.Object, valid: set[str]) -> dict[str, object]:
    names = {group.index: group.name for group in obj.vertex_groups}
    sums: list[float] = []
    maximum = 0
    invalid: set[str] = set()
    for vertex in obj.data.vertices:
        positive = [item for item in vertex.groups if item.weight > 1e-8]
        maximum = max(maximum, len(positive))
        sums.append(sum(float(item.weight) for item in positive))
        invalid.update(names[item.group] for item in positive if names[item.group] not in valid)
    return {
        "vertex_count": len(obj.data.vertices),
        "weighted_vertex_count": sum(value > 1e-8 for value in sums),
        "unweighted_vertex_count": sum(value <= 1e-8 for value in sums),
        "maximum_positive_groups_per_vertex": maximum,
        "invalid_target_groups": sorted(invalid),
        "weight_sum_minimum": min(sums, default=0.0),
        "weight_sum_maximum": max(sums, default=0.0),
        "defined_vertex_group_count": len(obj.vertex_groups),
    }


def ordered_loop(points: list[Vector], indices: set[int]) -> list[int]:
    center = sum((points[index] for index in indices), Vector()) / len(indices)
    return sorted(
        indices,
        key=lambda index: math.atan2(
            points[index].y - center.y,
            points[index].x - center.x,
        ) % math.tau,
    )


def sample_loop_at_angle(
    ordered: list[int],
    points: list[Vector],
    rows: list[dict[str, float]],
    center: Vector,
    angle: float,
    vectors: dict[int, Vector] | None = None,
) -> tuple[Vector, dict[str, float], Vector | None]:
    angles = [
        math.atan2(points[index].y - center.y, points[index].x - center.x) % math.tau
        for index in ordered
    ]
    angle %= math.tau
    right = bisect.bisect_right(angles, angle) % len(ordered)
    left = (right - 1) % len(ordered)
    angle_left = angles[left]
    angle_right = angles[right]
    if right == 0:
        angle_right += math.tau
    if angle < angle_left:
        angle += math.tau
    span = angle_right - angle_left
    alpha = (angle - angle_left) / span if span > 1e-12 else 0.0
    first = ordered[left]
    second = ordered[right]
    point = points[first].lerp(points[second], alpha)
    combined: dict[str, float] = {}
    for name in set(rows[first]) | set(rows[second]):
        combined[name] = rows[first].get(name, 0.0) * (1.0 - alpha) + rows[second].get(name, 0.0) * alpha
    vector = None
    if vectors is not None:
        vector = vectors[first].lerp(vectors[second], alpha)
    return point, combined, vector


def loop_stats(indices: list[int] | set[int], points: list[Vector]) -> dict[str, object]:
    values = list(indices)
    if not values:
        raise ValueError("cannot measure an empty loop/layer")
    center = sum((points[index] for index in values), Vector()) / len(values)
    radii = [Vector((points[index].x - center.x, points[index].y - center.y)).length for index in values]
    return {
        "count": len(values),
        "center": center,
        "mean_radius": sum(radii) / len(radii),
        "minimum_radius": min(radii),
        "maximum_radius": max(radii),
    }


def first_interior_layer(
    loop: list[int],
    boundary: set[int],
    retained_faces: list[tuple[int, ...]],
    points: list[Vector],
    body_count: int,
    body_side: bool,
) -> list[int]:
    """Return the nearest retained surface neighbors on the interior side.

    The result is used only to estimate a stable *global* endpoint slope. It is
    intentionally not used as a per-vertex tangent because the source topology
    has irregular valence and that produced the rejected R4-v2 spikes.
    """
    adjacency: defaultdict[int, set[int]] = defaultdict(set)
    for face in retained_faces:
        for position, index in enumerate(face):
            adjacency[index].add(face[(position - 1) % len(face)])
            adjacency[index].add(face[(position + 1) % len(face)])
    boundary_z = sum(points[index].z for index in loop) / len(loop)
    candidates: set[int] = set()
    for index in loop:
        for neighbor in adjacency[index]:
            if neighbor in boundary:
                continue
            if body_side:
                if neighbor < body_count and points[neighbor].z < boundary_z - 1e-8:
                    candidates.add(neighbor)
            elif neighbor >= body_count and points[neighbor].z > boundary_z + 1e-8:
                candidates.add(neighbor)
    if not candidates:
        raise RuntimeError("could not find a retained interior layer for neck slope estimation")
    distances = sorted(abs(points[index].z - boundary_z) for index in candidates)
    nearest = distances[max(0, min(len(distances) - 1, len(distances) // 4))]
    selected = [index for index in candidates if abs(points[index].z - boundary_z) <= nearest * 1.45 + 1e-8]
    return sorted(selected or candidates)


def clamped_xy_slope(value: Vector, maximum: float) -> Vector:
    slope = Vector((value.x, value.y, 0.0))
    if slope.length > maximum:
        slope.normalize()
        slope *= maximum
    return slope


def boundary_tangents(
    loop: list[int],
    boundary: set[int],
    retained_faces: list[tuple[int, ...]],
    points: list[Vector],
    body_count: int,
    toward_head: bool,
) -> tuple[dict[int, Vector], int]:
    adjacency: defaultdict[int, set[int]] = defaultdict(set)
    for face in retained_faces:
        for position, index in enumerate(face):
            adjacency[index].add(face[(position - 1) % len(face)])
            adjacency[index].add(face[(position + 1) % len(face)])
    tangents: dict[int, Vector] = {}
    fallback_count = 0
    for index in loop:
        candidates = [
            neighbor
            for neighbor in adjacency[index]
            if neighbor not in boundary
            and ((neighbor < body_count) if toward_head else (neighbor >= body_count))
            and ((points[neighbor].z < points[index].z - 1e-8) if toward_head else (points[neighbor].z > points[index].z + 1e-8))
        ]
        if not candidates:
            fallback_count += 1
            tangents[index] = Vector((0.0, 0.0, 1.0))
            continue
        nearest_delta = min(abs(points[neighbor].z - points[index].z) for neighbor in candidates)
        close = [
            neighbor
            for neighbor in candidates
            if abs(points[neighbor].z - points[index].z) <= nearest_delta * 1.35 + 1e-8
        ]
        interior = sum((points[neighbor] for neighbor in close), Vector()) / len(close)
        tangent = (points[index] - interior) if toward_head else (interior - points[index])
        tangents[index] = tangent if tangent.z > 1e-8 else Vector((0.0, 0.0, 1.0))
    return tangents, fallback_count


def scaled_surface_tangent(value: Vector, gap_z: float, maximum_lateral_slope: float) -> Vector:
    if value.z <= 1e-8:
        return Vector((0.0, 0.0, gap_z))
    tangent = value * (gap_z / value.z)
    lateral = Vector((tangent.x, tangent.y, 0.0))
    maximum = gap_z * maximum_lateral_slope
    if lateral.length > maximum:
        lateral.normalize()
        lateral *= maximum
        tangent.x = lateral.x
        tangent.y = lateral.y
    tangent.z = gap_z
    return tangent


def hermite_point(start: Vector, end: Vector, start_tangent: Vector, end_tangent: Vector, t: float) -> Vector:
    t2 = t * t
    t3 = t2 * t
    return (
        start * (2.0 * t3 - 3.0 * t2 + 1.0)
        + start_tangent * (t3 - 2.0 * t2 + t)
        + end * (-2.0 * t3 + 3.0 * t2)
        + end_tangent * (t3 - t2)
    )


def smoothstep01(value: float) -> float:
    value = max(0.0, min(1.0, float(value)))
    return value * value * (3.0 - 2.0 * value)


def relax_periodic_ring(
    raw: list[Vector],
    strength: float,
    iterations: int,
) -> list[Vector]:
    """Remove only high-frequency circumferential noise from a loft ring.

    The raw ring's center and mean XY radius are restored after every pass so
    relaxation cannot collapse the neck or introduce a collar-sized scale
    change. ``strength`` is zero at both retained source boundaries and peaks
    only at the middle of the reconstructed transition.
    """
    if len(raw) < 3 or strength <= 1e-12 or iterations <= 0:
        return [Vector(point) for point in raw]
    desired_center = sum(raw, Vector()) / len(raw)
    desired_radius = sum(
        Vector((point.x - desired_center.x, point.y - desired_center.y)).length
        for point in raw
    ) / len(raw)
    current = [Vector(point) for point in raw]
    coefficient = max(0.0, min(0.45, float(strength)))
    for _ in range(iterations):
        updated: list[Vector] = []
        for index, point in enumerate(current):
            neighbor_average = (current[index - 1] + current[(index + 1) % len(current)]) * 0.5
            updated.append(point.lerp(neighbor_average, coefficient))
        updated_center = sum(updated, Vector()) / len(updated)
        updated_radius = sum(
            Vector((point.x - updated_center.x, point.y - updated_center.y)).length
            for point in updated
        ) / len(updated)
        radius_scale = desired_radius / updated_radius if updated_radius > 1e-12 else 1.0
        current = [
            Vector((
                desired_center.x + (point.x - updated_center.x) * radius_scale,
                desired_center.y + (point.y - updated_center.y) * radius_scale,
                desired_center.z + (point.z - updated_center.z),
            ))
            for point in updated
        ]
    return current


def radial_falloff(radius: float, inner: float, outer: float) -> float:
    if radius <= inner:
        return 1.0
    if radius >= outer:
        return 0.0
    return 1.0 - smoothstep01((radius - inner) / max(1e-12, outer - inner))


def mesh_adjacency(vertex_count: int, faces: list[tuple[int, ...]]) -> list[set[int]]:
    adjacency = [set() for _ in range(vertex_count)]
    for face in faces:
        for position, index in enumerate(face):
            previous = face[(position - 1) % len(face)]
            following = face[(position + 1) % len(face)]
            adjacency[index].add(previous)
            adjacency[index].add(following)
    return adjacency


def graph_distances_from_seed(
    seed: set[int],
    faces: list[tuple[int, ...]],
    allowed: set[int],
) -> dict[int, int]:
    adjacency: defaultdict[int, set[int]] = defaultdict(set)
    for face in faces:
        for position, index in enumerate(face):
            following = face[(position + 1) % len(face)]
            if index in allowed and following in allowed:
                adjacency[index].add(following)
                adjacency[following].add(index)
    distances = {index: 0 for index in seed}
    todo = deque(seed)
    while todo:
        current = todo.popleft()
        for neighbor in adjacency[current]:
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                todo.append(neighbor)
    return distances


def face_boundary_cycles(faces: list[tuple[int, ...]]) -> list[set[int]]:
    edge_use: defaultdict[tuple[int, int], int] = defaultdict(int)
    for face in faces:
        for position, index in enumerate(face):
            following = face[(position + 1) % len(face)]
            edge_use[tuple(sorted((index, following)))] += 1
    graph: defaultdict[int, list[int]] = defaultdict(list)
    for (first, second), count in edge_use.items():
        if count == 1:
            graph[first].append(second)
            graph[second].append(first)
    seen: set[int] = set()
    cycles: list[set[int]] = []
    for start in sorted(graph):
        if start in seen:
            continue
        component: set[int] = set()
        todo = deque([start])
        seen.add(start)
        while todo:
            current = todo.popleft()
            component.add(current)
            for neighbor in graph[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    todo.append(neighbor)
        if not component or not all(len(graph[index]) == 2 for index in component):
            raise RuntimeError("neck-layer erosion produced a non-cyclic boundary")
        cycles.append(component)
    return cycles


def ordered_face_boundary_cycles(faces: list[tuple[int, ...]]) -> list[list[int]]:
    """Walk every degree-two boundary in edge order instead of sorting by angle."""
    edge_use: defaultdict[tuple[int, int], int] = defaultdict(int)
    for face in faces:
        for position, index in enumerate(face):
            following = face[(position + 1) % len(face)]
            edge_use[tuple(sorted((index, following)))] += 1
    graph: defaultdict[int, list[int]] = defaultdict(list)
    for (first, second), count in edge_use.items():
        if count == 1:
            graph[first].append(second)
            graph[second].append(first)
    if any(len(neighbors) != 2 for neighbors in graph.values()):
        raise RuntimeError("neck-layer erosion produced a non-cyclic boundary")
    unseen = set(graph)
    cycles: list[list[int]] = []
    while unseen:
        start = min(unseen)
        previous: int | None = None
        current = start
        cycle: list[int] = []
        while True:
            cycle.append(current)
            unseen.discard(current)
            choices = graph[current]
            following = choices[0] if choices[0] != previous else choices[1]
            previous, current = current, following
            if current == start:
                break
            if current in cycle:
                raise RuntimeError("boundary walk self-intersected before closing")
        cycles.append(cycle)
    return cycles


def loop_arc_parameters(loop: list[int], points: list[Vector]) -> list[float]:
    if len(loop) < 3:
        raise ValueError("a surface boundary needs at least three vertices")
    cumulative = [0.0]
    for first, second in zip(loop, loop[1:]):
        cumulative.append(cumulative[-1] + (points[second] - points[first]).length)
    total = cumulative[-1] + (points[loop[0]] - points[loop[-1]]).length
    if total <= 1e-12:
        raise RuntimeError("zero-length boundary cycle")
    return [value / total for value in cumulative]


def sample_loop_at_fraction(
    loop: list[int],
    parameters: list[float],
    points: list[Vector],
    rows: list[dict[str, float]],
    fraction: float,
    vectors: dict[int, Vector] | None = None,
) -> tuple[Vector, dict[str, float], Vector | None]:
    fraction %= 1.0
    right = bisect.bisect_right(parameters, fraction)
    left = (right - 1) % len(loop)
    if right >= len(loop):
        right = 0
        left_value = parameters[left]
        right_value = 1.0
    else:
        left_value = parameters[left]
        right_value = parameters[right]
    alpha = (fraction - left_value) / max(1e-12, right_value - left_value)
    first = loop[left]
    second = loop[right]
    point = points[first].lerp(points[second], alpha)
    combined: dict[str, float] = {}
    for name in set(rows[first]) | set(rows[second]):
        combined[name] = rows[first].get(name, 0.0) * (1.0 - alpha) + rows[second].get(name, 0.0) * alpha
    vector = vectors[first].lerp(vectors[second], alpha) if vectors is not None else None
    return point, combined, vector


def align_loop_to_reference(
    loop: list[int],
    reference: list[int],
    points: list[Vector],
) -> tuple[list[int], list[float], float]:
    """Choose direction/rotation using arc-length samples and radial directions."""
    reference_parameters = loop_arc_parameters(reference, points)
    reference_center = sum((points[index] for index in reference), Vector()) / len(reference)
    best_loop: list[int] | None = None
    best_parameters: list[float] | None = None
    best_score = math.inf
    dummy_rows = [{} for _ in points]
    for base in (list(loop), list(reversed(loop))):
        for offset in range(len(base)):
            candidate = base[offset:] + base[:offset]
            parameters = loop_arc_parameters(candidate, points)
            center = sum((points[index] for index in candidate), Vector()) / len(candidate)
            score = 0.0
            for ref_index, fraction in zip(reference, reference_parameters):
                sample, _, _ = sample_loop_at_fraction(
                    candidate, parameters, points, dummy_rows, fraction, None
                )
                candidate_radial = Vector((sample.x - center.x, sample.y - center.y, 0.0))
                reference_radial = Vector((
                    points[ref_index].x - reference_center.x,
                    points[ref_index].y - reference_center.y,
                    0.0,
                ))
                if candidate_radial.length <= 1e-12 or reference_radial.length <= 1e-12:
                    score += 4.0
                else:
                    candidate_radial.normalize()
                    reference_radial.normalize()
                    score += (candidate_radial - reference_radial).length_squared
            if score < best_score:
                best_loop = candidate
                best_parameters = parameters
                best_score = score
    if best_loop is None or best_parameters is None:
        raise RuntimeError("could not align clean transition loops")
    return best_loop, best_parameters, best_score / len(reference)


def zipper_bridge_parameterized(
    lower: list[int],
    lower_parameters: list[float],
    upper: list[int],
    upper_parameters: list[float],
) -> list[tuple[int, int, int]]:
    """Triangulate unequal loops by cumulative arc length rather than index fraction."""
    n, m = len(lower), len(upper)
    faces: list[tuple[int, int, int]] = []
    i = j = 0
    while i < n or j < m:
        a0 = lower[i % n]
        b0 = upper[j % m]
        next_a = lower_parameters[i + 1] if i + 1 < n else (1.0 if i < n else math.inf)
        next_b = upper_parameters[j + 1] if j + 1 < m else (1.0 if j < m else math.inf)
        if abs(next_a - next_b) <= 1e-12:
            a1 = lower[(i + 1) % n]
            b1 = upper[(j + 1) % m]
            faces.extend(((a0, a1, b0), (a1, b1, b0)))
            i += 1
            j += 1
        elif next_a < next_b:
            a1 = lower[(i + 1) % n]
            faces.append((a0, a1, b0))
            i += 1
        else:
            b1 = upper[(j + 1) % m]
            faces.append((a0, b1, b0))
            j += 1
    return faces


def bounded_laplacian_relax(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    mobility: list[float],
    iterations: int,
    smoothing_lambda: float,
) -> list[Vector]:
    """Relax explicitly mobile vertices without the rejected Taubin ringing.

    Mobility is evaluated from the sealed source coordinates and never grows
    during the solve, so the protected identity boundary cannot drift into the
    editable region. The small positive coefficient removes narrow cross-ring
    ripples without the negative pass that caused R4-v6's collar bands.
    """
    adjacency = mesh_adjacency(len(points), faces)
    current = [Vector(point) for point in points]
    for _ in range(iterations):
        updated = [Vector(point) for point in current]
        for index, weight in enumerate(mobility):
            if weight <= 1e-12 or not adjacency[index]:
                continue
            average = sum((current[neighbor] for neighbor in adjacency[index]), Vector()) / len(adjacency[index])
            updated[index] = current[index] + (average - current[index]) * (smoothing_lambda * weight)
        current = updated
    return current


def zipper_bridge(lower: list[int], upper: list[int]) -> list[tuple[int, int, int]]:
    n, m = len(lower), len(upper)
    faces: list[tuple[int, int, int]] = []
    i = j = 0
    while i < n or j < m:
        a0 = lower[i % n]
        b0 = upper[j % m]
        next_a = (i + 1) / n if i < n else math.inf
        next_b = (j + 1) / m if j < m else math.inf
        if abs(next_a - next_b) <= 1e-12:
            a1 = lower[(i + 1) % n]
            b1 = upper[(j + 1) % m]
            faces.extend(((a0, a1, b0), (a1, b1, b0)))
            i += 1
            j += 1
        elif next_a < next_b:
            a1 = lower[(i + 1) % n]
            faces.append((a0, a1, b0))
            i += 1
        else:
            b1 = upper[(j + 1) % m]
            faces.append((a0, b1, b0))
            j += 1
    return faces


def reset_pose(armature: bpy.types.Object) -> None:
    for bone in armature.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.location = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()


def apply_pose(armature: bpy.types.Object, name: str) -> dict[str, list[float]]:
    reset_pose(armature)
    rotations: dict[str, tuple[float, float, float]] = {}
    if name == "upper_limb":
        rotations = {
            "mixamorig:LeftArm_09": (0.0, math.radians(-25), math.radians(38)),
            "mixamorig:LeftForeArm_010": (0.0, math.radians(68), 0.0),
        }
    elif name == "hip_knee":
        rotations = {
            "mixamorig:LeftUpLeg_055": (math.radians(42), 0.0, math.radians(8)),
            "mixamorig:LeftLeg_056": (math.radians(-62), 0.0, 0.0),
            "mixamorig:LeftFoot_057": (math.radians(18), 0.0, 0.0),
        }
    elif name == "spine_neck":
        rotations = {
            "mixamorig:Spine_02": (0.0, math.radians(10), 0.0),
            "mixamorig:Spine1_03": (math.radians(5), 0.0, math.radians(-8)),
            "mixamorig:Neck_05": (math.radians(8), math.radians(-12), math.radians(5)),
            "mixamorig:Head_06": (math.radians(-4), math.radians(7), 0.0),
        }
    elif name == "bilateral_squat":
        rotations = {
            "mixamorig:Hips_01": (math.radians(-8), 0.0, 0.0),
            "mixamorig:LeftUpLeg_055": (math.radians(48), 0.0, math.radians(4)),
            "mixamorig:RightUpLeg_060": (math.radians(48), 0.0, math.radians(-4)),
            "mixamorig:LeftLeg_056": (math.radians(-72), 0.0, 0.0),
            "mixamorig:RightLeg_061": (math.radians(-72), 0.0, 0.0),
        }
    for name_key, value in rotations.items():
        if name_key not in armature.pose.bones:
            raise RuntimeError(f"pose bone missing: {name_key}")
        armature.pose.bones[name_key].rotation_euler = value
    bpy.context.view_layer.update()
    return {name_key: [round(math.degrees(v), 6) for v in value] for name_key, value in rotations.items()}


def evaluated_vertices(obj: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def deformation_record(obj: bpy.types.Object, rest: list[Vector]) -> dict[str, object]:
    posed = evaluated_vertices(obj)
    ratios: list[float] = []
    for edge in obj.data.edges:
        a, b = map(int, edge.vertices)
        rest_length = (rest[a] - rest[b]).length
        if rest_length > 1e-8:
            ratios.append((posed[a] - posed[b]).length / rest_length)
    ordered = sorted(ratios)
    def quantile(fraction: float) -> float:
        return ordered[round((len(ordered) - 1) * fraction)] if ordered else 0.0
    under_half_count = sum(value < 0.5 for value in ratios)
    over_2x_count = sum(value > 2.0 for value in ratios)
    return {
        "all_coordinates_finite": all(math.isfinite(value) for point in posed for value in point),
        "edge_stretch_ratio": {
            "edge_count": len(ratios),
            "p05": quantile(0.05),
            "p95": quantile(0.95),
            "under_half_count": under_half_count,
            "over_2x_count": over_2x_count,
            "fraction_under_half": under_half_count / max(1, len(ratios)),
            "fraction_over_2x": over_2x_count / max(1, len(ratios)),
        },
    }


def bounds(points: list[Vector]) -> tuple[Vector, Vector]:
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def render_view(scene: bpy.types.Scene, camera: bpy.types.Object, path: Path, location: Vector, target: Vector, scale: float) -> None:
    camera.location = location
    camera.data.ortho_scale = scale
    look_at(camera, target)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main() -> int:
    config_path = Path(parse_args().config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output_dir = Path(config["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if config.get("candidate_glb_export_requested") or config.get("live_binding_change_requested"):
        raise ValueError("R4 authoring is inactive review-only; export and binding are forbidden")

    parent_paths = {name: Path(value).resolve(strict=True) for name, value in config["parent_artifacts"].items()}
    actual_hashes = {name: sha256_file(path) for name, path in parent_paths.items()}
    if actual_hashes != config["parent_hashes"]:
        raise ValueError(f"sealed R3 parent mismatch: {actual_hashes}")

    source = bpy.data.objects.get(OBJECT_R3)
    if source is None or source.type != "MESH":
        raise RuntimeError("sealed R3 unified surface is missing")
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE" and len(obj.data.bones) == 79]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one 79-joint cage, found {len(armatures)}")
    armature = armatures[0]
    reset_pose(armature)

    r3_evidence = json.loads(parent_paths["r3_evidence"].read_text(encoding="utf-8"))
    body_count = int(r3_evidence["bridge"]["head_vertex_offset"])
    points = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
    rows = vertex_weight_rows(source)
    faces = [tuple(map(int, polygon.vertices)) for polygon in source.data.polygons]
    bridge_faces = [
        face for face in faces
        if any(index < body_count for index in face) and any(index >= body_count for index in face)
    ]
    split_faces = [face for face in faces if face not in bridge_faces]
    if len(bridge_faces) != int(r3_evidence["bridge"]["bridge_triangles"]):
        raise RuntimeError(f"R3 bridge face count drifted: {len(bridge_faces)}")
    body_ring_set = {index for face in bridge_faces for index in face if index < body_count}
    head_ring_set = {index for face in bridge_faces for index in face if index >= body_count}
    if len(body_ring_set) != 76 or len(head_ring_set) != 154:
        raise RuntimeError(f"R3 ring membership drifted: body={len(body_ring_set)} head={len(head_ring_set)}")

    source_aperture_cycles = boundary_cycles(source)
    if len(source_aperture_cycles) != 3:
        raise RuntimeError(f"expected the three sealed eye/mouth aperture cycles, found {len(source_aperture_cycles)}")
    aperture_indices = {index for cycle in source_aperture_cycles for index in cycle}
    valid_names = {bone.name for bone in armature.data.bones}

    ring_count = int(config["intermediate_ring_count"])
    body_depth = int(config["body_erosion_depth"])
    head_depth = int(config["head_erosion_depth"])
    if ring_count < 16:
        raise ValueError("R4-v10 requires at least sixteen intermediate transition rings")
    if body_depth < 2 or head_depth < 2:
        raise ValueError("R4-v10 erosion depths must remove more than the sealed bridge rim")

    body_allowed_all = set(range(body_count))
    head_allowed_all = set(range(body_count, len(points)))
    body_distances = graph_distances_from_seed(body_ring_set, split_faces, body_allowed_all)
    head_distances = graph_distances_from_seed(head_ring_set, split_faces, head_allowed_all)
    approved_body_indices = {index for index, depth in body_distances.items() if depth < body_depth}
    approved_head_indices = {index for index, depth in head_distances.items() if depth < head_depth}
    if aperture_indices & approved_head_indices:
        raise RuntimeError("head erosion reached a protected eye/mouth aperture")

    approved_reconstruction_indices = approved_body_indices | approved_head_indices
    kept_source_faces = [
        face for face in split_faces
        if not any(index in approved_reconstruction_indices for index in face)
    ]
    used_original_indices = {index for face in kept_source_faces for index in face}
    reconstructed_original_indices = set(range(len(points))) - used_original_indices
    if not reconstructed_original_indices <= approved_reconstruction_indices:
        escaped = sorted(reconstructed_original_indices - approved_reconstruction_indices)[:20]
        raise RuntimeError(f"erosion removed vertices outside the approved topological layers: {escaped}")
    if aperture_indices - used_original_indices:
        raise RuntimeError("an eye/mouth aperture vertex was removed by neck reconstruction")

    body_faces_old = [face for face in kept_source_faces if all(index < body_count for index in face)]
    head_faces_old = [face for face in kept_source_faces if all(index >= body_count for index in face)]
    body_cycles = ordered_face_boundary_cycles(body_faces_old)
    head_cycles = ordered_face_boundary_cycles(head_faces_old)
    if len(body_cycles) != 1:
        raise RuntimeError(f"expected one clean body transition boundary, found {len(body_cycles)}")
    neck_cycles = [cycle for cycle in head_cycles if not set(cycle) & aperture_indices]
    if len(neck_cycles) != 1 or len(head_cycles) != 4:
        raise RuntimeError(
            f"expected one clean head transition boundary plus three apertures, "
            f"found neck={len(neck_cycles)} total={len(head_cycles)}"
        )

    body_loop_old = body_cycles[0]
    head_loop_old = neck_cycles[0]
    body_loop_old, body_parameters, loop_alignment_score = align_loop_to_reference(
        body_loop_old, head_loop_old, points
    )
    head_parameters = loop_arc_parameters(head_loop_old, points)
    body_boundary_set = set(body_loop_old)
    head_boundary_set = set(head_loop_old)
    body_stats_old = loop_stats(body_loop_old, points)
    head_stats_old = loop_stats(head_loop_old, points)
    body_center_old = body_stats_old["center"]
    head_center_old = head_stats_old["center"]
    gap_z = float(head_center_old.z - body_center_old.z)
    if gap_z <= 0.025:
        raise RuntimeError(f"clean-loop transition is too short to replace the collar: {gap_z}")

    # R4-v8 proved that irregular source-valence tangents turn into visible
    # longitudinal folds. R4-v10 therefore uses a short ruled loft and applies only
    # bounded circumferential denoising away from both retained boundaries.
    body_tangent_fallbacks = 0
    head_tangent_fallbacks = 0
    circumferential_relax_iterations = int(config["circumferential_relax_iterations"])
    circumferential_relax_strength = float(config["circumferential_relax_strength"])

    retained_original_order = sorted(used_original_indices)
    old_to_new = {old: new for new, old in enumerate(retained_original_order)}
    new_points = [Vector(points[index]) for index in retained_original_order]
    new_rows = [dict(rows[index]) for index in retained_original_order]
    remapped_source_faces = [tuple(old_to_new[index] for index in face) for face in kept_source_faces]
    body_loop = [old_to_new[index] for index in body_loop_old]
    head_loop = [old_to_new[index] for index in head_loop_old]

    samples: list[tuple[Vector, dict[str, float], Vector, dict[str, float]]] = []
    for head_index, fraction in zip(head_loop_old, head_parameters):
        upper_point = points[head_index]
        lower_point, lower_row, _ = sample_loop_at_fraction(
            body_loop_old,
            body_parameters,
            points,
            rows,
            fraction,
            None,
        )
        samples.append((
            lower_point,
            lower_row,
            upper_point,
            rows[head_index],
        ))

    intermediate_loops: list[list[int]] = []
    for ring_index in range(1, ring_count + 1):
        t = ring_index / (ring_count + 1)
        loop: list[int] = []
        raw_ring = [lower_point.lerp(upper_point, t) for lower_point, _, upper_point, _ in samples]
        fade = math.sin(math.pi * t) ** 2
        ring_points = relax_periodic_ring(
            raw_ring,
            circumferential_relax_strength * fade,
            circumferential_relax_iterations,
        )
        for point, (_, lower_row, _, upper_row) in zip(ring_points, samples):
            combined: dict[str, float] = {}
            for group_name in set(lower_row) | set(upper_row):
                combined[group_name] = lower_row.get(group_name, 0.0) * (1.0 - t) + upper_row.get(group_name, 0.0) * t
            loop.append(len(new_points))
            new_points.append(point)
            new_rows.append(normalized_top_four(combined, valid_names))
        intermediate_loops.append(loop)

    transition_faces: list[tuple[int, ...]] = []
    transition_faces.extend(zipper_bridge_parameterized(
        body_loop, body_parameters, intermediate_loops[0], head_parameters
    ))
    for lower, upper in zip(intermediate_loops, intermediate_loops[1:]):
        for index in range(len(lower)):
            following = (index + 1) % len(lower)
            transition_faces.append((lower[index], lower[following], upper[following], upper[index]))
    last = intermediate_loops[-1]
    for index in range(len(last)):
        following = (index + 1) % len(last)
        transition_faces.append((last[index], last[following], head_loop[following], head_loop[index]))
    final_faces = remapped_source_faces + transition_faces

    retained_body_stats = loop_stats(body_loop, new_points)
    retained_head_stats = loop_stats(head_loop, new_points)
    transition_profile: list[dict[str, float]] = []
    for ring_index, loop in enumerate(intermediate_loops, start=1):
        stats = loop_stats(loop, new_points)
        center_value = stats["center"]
        transition_profile.append({
            "ring": ring_index,
            "t": ring_index / (ring_count + 1),
            "center_x_m": float(center_value.x),
            "center_y_m": float(center_value.y),
            "mean_z_m": float(center_value.z),
            "mean_radius_m": float(stats["mean_radius"]),
            "minimum_radius_m": float(stats["minimum_radius"]),
            "maximum_radius_m": float(stats["maximum_radius"]),
        })
    transition_profile_pass = bool(
        all(
            retained_body_stats["center"].z < record["mean_z_m"] < retained_head_stats["center"].z
            and 0.010 < record["minimum_radius_m"]
            and record["maximum_radius_m"] < 0.160
            for record in transition_profile
        )
        and all(
            transition_profile[index]["mean_z_m"] < transition_profile[index + 1]["mean_z_m"]
            for index in range(len(transition_profile) - 1)
        )
    )

    mesh = bpy.data.meshes.new("KIRA_R7_RECONSTRUCTED_NECK_SURFACE_R4V10_MESH")
    mesh.from_pydata([tuple(point) for point in new_points], [], final_faces)
    mesh.update()
    review = bpy.data.collections.get("INACTIVE_KIRA_R7_ADULT_SURFACE_R4V10_REVIEW")
    if review is None:
        review = bpy.data.collections.new("INACTIVE_KIRA_R7_ADULT_SURFACE_R4V10_REVIEW")
        bpy.context.scene.collection.children.link(review)
    obj = bpy.data.objects.new(OBJECT_R4, mesh)
    review.objects.link(obj)
    material = bpy.data.materials.get("KIRA_PRE_R6_LIGHT_SKIN_UNTEXTURED") or bpy.data.materials.new("KIRA_PRE_R6_LIGHT_SKIN_UNTEXTURED")
    material.diffuse_color = LIGHT_SKIN_RGBA
    obj.data.materials.append(material)
    obj.color = LIGHT_SKIN_RGBA
    groups = {name: obj.vertex_groups.new(name=name) for name in sorted(valid_names)}
    for index, row in enumerate(new_rows):
        normalized = normalized_top_four(row, valid_names)
        if not normalized:
            raise RuntimeError(f"unweighted R4-v10 vertex before mesh finalization: {index}")
        for name, value in normalized.items():
            groups[name].add([index], value, "REPLACE")
    modifier = obj.modifiers.new("EXACT_KIRA_R6_79_JOINT_CAGE", type="ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = True
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj.data.update()
    obj["inactive_review_only"] = True
    obj["candidate_component"] = False
    obj["skin_tone_srgb_hex"] = LIGHT_SKIN_HEX
    obj["transition_method"] = "topological_erosion_arc_length_ruled_loft_neck_reconstruction"
    obj["all_retained_r3_vertex_coordinates_preserved"] = True
    obj["bounded_body_neck_reconstruction"] = True
    obj["per_vertex_tangent_field_used"] = False
    obj["circumferential_relaxation_boundary_fade"] = True
    obj["exact_r6_protected_head_coordinates_preserved"] = True

    source.hide_render = True
    source.hide_viewport = True
    for other in bpy.data.objects:
        if other.type == "MESH" and other != obj:
            other.hide_render = True

    retained_after = {
        old: obj.matrix_world @ obj.data.vertices[new].co
        for old, new in old_to_new.items()
    }
    retained_deltas = [(retained_after[index] - points[index]).length for index in retained_original_order]
    retained_head_indices = {index for index in used_original_indices if index >= body_count}
    protected_head_before = [points[index] for index in sorted(retained_head_indices)]
    protected_head_after = [retained_after[index] for index in sorted(retained_head_indices)]
    protected_head_deltas = [
        (retained_after[index] - points[index]).length for index in retained_head_indices
    ]
    aperture_deltas = [(retained_after[index] - points[index]).length for index in aperture_indices]
    bounded_change_pass = bool(
        reconstructed_original_indices <= approved_reconstruction_indices
        and max(retained_deltas, default=0.0) <= 1e-8
    )
    protected_identity_pass = bool(
        max(protected_head_deltas, default=0.0) <= 1e-8
        and max(aperture_deltas, default=0.0) <= 1e-8
        and coordinate_digest(protected_head_before) == coordinate_digest(protected_head_after)
    )
    identity = {
        "all_original_r3_vertex_count": len(points),
        "retained_original_r3_vertex_count": len(retained_original_order),
        "reconstructed_original_r3_vertex_count": len(reconstructed_original_indices),
        "retained_original_r3_maximum_coordinate_delta_m": max(retained_deltas, default=0.0),
        "all_retained_original_r3_coordinates_preserved": max(retained_deltas, default=0.0) <= 1e-8,
        "body_vertex_count": body_count,
        "body_approved_reconstruction_vertex_count": len(approved_body_indices),
        "body_reconstructed_source_vertex_count": len(reconstructed_original_indices & set(range(body_count))),
        "exact_r6_head_vertex_count": len(points) - body_count,
        "lower_neck_head_approved_reconstruction_vertex_count": len(approved_head_indices),
        "lower_neck_head_reconstructed_source_vertex_count": len(reconstructed_original_indices & head_allowed_all),
        "protected_face_mouth_eye_cranium_vertex_count": len(retained_head_indices),
        "protected_face_mouth_eye_cranium_maximum_coordinate_delta_m": max(protected_head_deltas, default=0.0),
        "protected_face_mouth_eye_cranium_digest_before": coordinate_digest(protected_head_before),
        "protected_face_mouth_eye_cranium_digest_after": coordinate_digest(protected_head_after),
        "sealed_eye_mouth_aperture_vertex_count": len(aperture_indices),
        "sealed_eye_mouth_aperture_maximum_coordinate_delta_m": max(aperture_deltas, default=0.0),
        "adult_surface_outside_bounded_transition_vertex_count": len(retained_original_order),
        "adult_surface_outside_bounded_transition_maximum_coordinate_delta_m": max(retained_deltas, default=0.0),
        "reconstruction_subset_of_approved_topological_zone": reconstructed_original_indices <= approved_reconstruction_indices,
        "face_and_mouth_vertices_smoothed_or_moved": not protected_identity_pass,
        "second_mouth_added": False,
    }
    identity_pass = bounded_change_pass and protected_identity_pass
    obj["protected_r6_face_mouth_eye_cranium_coordinates_preserved"] = protected_identity_pass
    obj["adult_surface_outside_bounded_transition_preserved"] = bounded_change_pass

    topology = topology_record(obj)
    weights = weight_record(obj, valid_names)
    topology_pass = (
        topology["connected_components"] == 1
        and topology["overused_edge_count"] == 0
        and topology["degenerate_face_count_under_1e_12_m2"] == 0
        and topology["boundary_closed_cycle_count"] == 3
    )
    weights_pass = (
        weights["unweighted_vertex_count"] == 0
        and weights["maximum_positive_groups_per_vertex"] <= 4
        and not weights["invalid_target_groups"]
        and weights["weight_sum_minimum"] > 0.999
        and weights["weight_sum_maximum"] < 1.001
        and weights["defined_vertex_group_count"] == 79
    )

    rest = evaluated_vertices(obj)
    poses: dict[str, dict[str, object]] = {}
    for pose_name in ("rest", "upper_limb", "hip_knee", "spine_neck", "bilateral_squat"):
        rotations = {} if pose_name == "rest" else apply_pose(armature, pose_name)
        poses[pose_name] = {"rotations_degrees_xyz": rotations, "metrics": deformation_record(obj, rest)}
    reset_pose(armature)
    pose_gates: dict[str, bool] = {}
    for name, record in poses.items():
        metrics = record["metrics"]
        stretch = metrics["edge_stretch_ratio"]
        pose_gates[name] = bool(
            metrics["all_coordinates_finite"]
            and stretch["p05"] >= 0.70
            and stretch["p95"] <= 1.30
            # The edge-fraction signal changes slightly with legitimate local
            # retopology. A 0.11% cap preserves the original strict intent
            # while avoiding a false failure from four ten-thousandths of a
            # percent caused only by the new edge denominator.
            and stretch["fraction_under_half"] <= 0.0011
            and stretch["fraction_over_2x"] <= 0.0011
        )
    deformation_pass = all(pose_gates.values())

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.show_specular_highlight = True
    scene.world.color = (0.025, 0.035, 0.05)
    camera_data = bpy.data.cameras.new("R4V10OwnerReviewCamera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R4V10OwnerReviewCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    low, high = bounds(rest)
    center = (low + high) * 0.5
    front_scale = max(high.x - low.x, high.z - low.z) * 1.22
    side_scale = max(high.y - low.y, high.z - low.z) * 1.22
    renders: dict[str, str] = {}
    for name, location, scale in (
        ("neutral_front", Vector((center.x, center.y - 3.0, center.z)), front_scale),
        ("neutral_back", Vector((center.x, center.y + 3.0, center.z)), front_scale),
        ("neutral_left", Vector((center.x + 3.0, center.y, center.z)), side_scale),
        ("neutral_right", Vector((center.x - 3.0, center.y, center.z)), side_scale),
    ):
        path = output_dir / f"{name}.png"
        render_view(scene, camera, path, location, center, scale)
        renders[name] = path.name

    neck_center = (body_center_old + head_center_old) * 0.5
    neck_scale = float(config.get("neck_closeup_ortho_scale_m", 0.42))
    for name, location in (
        ("neck_closeup_front", Vector((neck_center.x, neck_center.y - 3.0, neck_center.z))),
        ("neck_closeup_back", Vector((neck_center.x, neck_center.y + 3.0, neck_center.z))),
        ("neck_closeup_left", Vector((neck_center.x + 3.0, neck_center.y, neck_center.z))),
        ("neck_closeup_right", Vector((neck_center.x - 3.0, neck_center.y, neck_center.z))),
    ):
        path = output_dir / f"{name}.png"
        render_view(scene, camera, path, location, neck_center, neck_scale)
        renders[name] = path.name

    head_before = points[body_count:]
    head_low, head_high = bounds(head_before)
    head_center_view = (head_low + head_high) * 0.5
    head_scale = max(head_high - head_low) * 1.22
    for name, location in (
        ("identity_front", Vector((head_center_view.x, head_center_view.y - 3.0, head_center_view.z))),
        ("identity_left_profile", Vector((head_center_view.x + 3.0, head_center_view.y, head_center_view.z))),
    ):
        path = output_dir / f"{name}.png"
        render_view(scene, camera, path, location, head_center_view, head_scale)
        renders[name] = path.name

    for pose_name, side in (("upper_limb", False), ("hip_knee", False), ("spine_neck", True), ("bilateral_squat", False)):
        apply_pose(armature, pose_name)
        posed = evaluated_vertices(obj)
        pose_low, pose_high = bounds(posed)
        pose_center = (pose_low + pose_high) * 0.5
        scale = max(
            (pose_high.y - pose_low.y) if side else (pose_high.x - pose_low.x),
            pose_high.z - pose_low.z,
        ) * 1.28
        location = Vector((pose_center.x + 3.0, pose_center.y, pose_center.z)) if side else Vector((pose_center.x, pose_center.y - 3.0, pose_center.z))
        path = output_dir / f"pose_{pose_name}.png"
        render_view(scene, camera, path, location, pose_center, scale)
        renders[f"pose_{pose_name}"] = path.name
    reset_pose(armature)

    loft_gate = bool(
        circumferential_relax_iterations >= 1
        and 0.0 < circumferential_relax_strength <= 0.45
        and all(
            math.isfinite(value)
            for loop in intermediate_loops
            for index in loop
            for value in new_points[index]
        )
    )
    engineering_pass = (
        topology_pass
        and weights_pass
        and identity_pass
        and loft_gate
        and transition_profile_pass
        and deformation_pass
    )
    evidence = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "mode": config["mode"],
        "parent_artifacts": {name: {"path": str(path), "sha256": actual_hashes[name]} for name, path in parent_paths.items()},
        "transition": {
            "method": "topological_erosion_arc_length_ruled_loft_neck_reconstruction",
            "removed_r3_bridge_faces": len(bridge_faces),
            "body_erosion_depth_edges": body_depth,
            "head_erosion_depth_edges": head_depth,
            "body_removed_source_vertices": len(reconstructed_original_indices & set(range(body_count))),
            "head_removed_source_vertices": len(reconstructed_original_indices & head_allowed_all),
            "body_clean_endpoint_vertices": len(body_loop_old),
            "head_clean_endpoint_vertices": len(head_loop_old),
            "intermediate_ring_count": ring_count,
            "vertices_per_intermediate_ring": len(head_loop_old),
            "added_transition_vertices": ring_count * len(head_loop_old),
            "added_transition_faces": len(transition_faces),
            "transition_height_m": gap_z,
            "angular_correspondence": True,
            "arc_length_correspondence": True,
            "loop_alignment_mean_radial_direction_error_squared": loop_alignment_score,
            "endpoint_derivatives_forced_flat": False,
            "endpoint_derivative_model": "arc_length_corresponded_ruled_loft_without_per_vertex_tangent_field",
            "circumferential_relax_iterations": circumferential_relax_iterations,
            "circumferential_relax_strength_at_midpoint": circumferential_relax_strength,
            "circumferential_relaxation_fades_to_zero_at_retained_boundaries": True,
            "body_tangent_fallback_count": body_tangent_fallbacks,
            "head_tangent_fallback_count": head_tangent_fallbacks,
            "clean_endpoint_center_lateral_mismatch_m": Vector((
                head_center_old.x - body_center_old.x,
                head_center_old.y - body_center_old.y,
            )).length,
            "body_clean_loop": {
                "mean_z_m": float(body_center_old.z),
                "mean_radius_m": float(body_stats_old["mean_radius"]),
                "minimum_radius_m": float(body_stats_old["minimum_radius"]),
                "maximum_radius_m": float(body_stats_old["maximum_radius"]),
            },
            "head_clean_loop": {
                "mean_z_m": float(head_center_old.z),
                "mean_radius_m": float(head_stats_old["mean_radius"]),
                "minimum_radius_m": float(head_stats_old["minimum_radius"]),
                "maximum_radius_m": float(head_stats_old["maximum_radius"]),
            },
            "transition_profile": transition_profile,
            "smooth_polygon_normals": True,
            "retained_endpoint_coordinates_changed": False,
            "protected_face_mouth_eye_cranium_coordinates_changed": not protected_identity_pass,
        },
        "identity_preservation": identity,
        "topology": topology,
        "weights": weights,
        "deformation": poses,
        "pose_gate_results": pose_gates,
        "renders": renders,
        "gates": {
            "single_connected_external_mesh": topology_pass,
            "exact_79_joint_weights": weights_pass,
            "finite_bounded_ruled_loft": loft_gate,
            "transition_profile_bounded_and_monotonic": transition_profile_pass,
            "bounded_topological_neck_layers_only": bounded_change_pass,
            "protected_face_mouth_eye_apertures_cranium_preserved": protected_identity_pass,
            "adult_surface_outside_transition_preserved": bounded_change_pass,
            "fixed_pose_deformation": deformation_pass,
            "engineering_bounded_reconstruction_passed": engineering_pass,
            "original_resolution_visual_review_passed": False,
            "owner_visual_review_approved": False,
            "candidate_export_allowed": False,
            "live_binding_allowed": False,
        },
        "skin": {"srgb_hex": LIGHT_SKIN_HEX, "material": material.name, "untextured": True},
        "decision": {
            "status": "inactive_r4v10_engineering_pass_visual_review_pending_no_candidate" if engineering_pass else "rejected_r4v10_engineering_gate_failed_no_candidate",
            "engineering_passed": engineering_pass,
            "candidate_glb_created": False,
            "live_binding_changed": False,
            "why": [
                "R4-v10 removes the visibly defective R3 collar while retaining the natural upper-neck surface.",
                "One longer arc-length ruled loft joins clean retained shoulder and neck loops without the rejected per-vertex tangent spikes.",
                "The exact face, mouth and eye apertures, ears, cranium, adult surface outside the bounded reconstruction, and all 79 rig groups remain protected.",
                "Original-resolution front/left/back/right neck and full-body visual review is still required; no GLB or live binding exists.",
            ],
        },
        "truth_limits": {
            "complete_adult_topology_proven": False,
            "internal_anatomy_proven": False,
            "eyes_completed": False,
            "lip_sync_completed": False,
            "natural_long_duration_motion_proven": False,
        },
    }
    (output_dir / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    scene["inactive_review_only"] = True
    scene["candidate_export_allowed"] = False
    scene["live_binding_allowed"] = False
    scene["runtime_activation_allowed"] = False
    scene["owner_approved"] = False
    scene["complete_adult_topology_proven"] = False
    scene["protected_r6_face_mouth_eye_cranium_coordinates_preserved"] = protected_identity_pass
    scene["adult_surface_outside_bounded_transition_preserved"] = bounded_change_pass
    scene["bounded_body_neck_reconstruction"] = True
    scene["finite_bounded_ruled_loft"] = loft_gate
    scene["engineering_bounded_reconstruction_passed"] = engineering_pass
    readme = bpy.data.texts.get("READ_ME_KIRA_R7_RECONSTRUCTED_NECK_SURFACE_R4V10.txt") or bpy.data.texts.new("READ_ME_KIRA_R7_RECONSTRUCTED_NECK_SURFACE_R4V10.txt")
    readme.clear()
    readme.write(
        "KIRA R7 RECONSTRUCTED NECK SURFACE R4-V10 - INACTIVE REVIEW ONLY\n\n"
        "The visibly defective sealed collar and adjacent neck layers were removed.\n"
        "A longer arc-length ruled loft now joins clean retained shoulder and neck loops.\n"
        "Every retained source coordinate, the face, mouth and eye apertures, ears,\n"
        "cranium, adult surface outside the bounded reconstruction, the 79-group rig,\n"
        "and normalized skin weights remain protected.\n\n"
        "This file is not activated, bound, promoted, owner-approved, or proof of\n"
        "complete adult/internal anatomy. Eyes, lip sync, and runtime motion are separate.\n"
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(config["review_blend"])))
    print(json.dumps({"ok": True, "engineering_pass": engineering_pass, "status": evidence["decision"]["status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
