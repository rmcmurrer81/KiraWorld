"""Find a compact connected bilateral V1 front-pelvis replacement region."""

from __future__ import annotations

import heapq
import math
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects["BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"]
mesh = body.data

patch_faces = {
    polygon.index: polygon
    for polygon in mesh.polygons
    if (
        abs(polygon.center.x) <= 0.10
        and 0.62 <= polygon.center.z <= 0.88
        and -0.22 <= polygon.center.y <= 0.13
    )
}
edge_to_faces = {}
for polygon in patch_faces.values():
    for edge_key in polygon.edge_keys:
        edge_to_faces.setdefault(edge_key, []).append(polygon.index)
adjacency = {index: set() for index in patch_faces}
for members in edge_to_faces.values():
    for first in members:
        adjacency[first].update(index for index in members if index != first)


def components(face_indices):
    unseen = set(face_indices)
    result = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        member = {seed}
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    member.add(neighbor)
                    stack.append(neighbor)
        result.append(member)
    return result


def boundary_loops(face_indices):
    counts = {}
    for index in face_indices:
        for edge_key in patch_faces[index].edge_keys:
            counts[edge_key] = counts.get(edge_key, 0) + 1
    edges = [edge_key for edge_key, count in counts.items() if count == 1]
    vertex_to_edges = {}
    for edge_key in edges:
        for vertex in edge_key:
            vertex_to_edges.setdefault(vertex, []).append(edge_key)
    unseen = set(edges)
    result = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        component_edges = [seed]
        while stack:
            current = stack.pop()
            for vertex in current:
                for neighbor_edge in vertex_to_edges[vertex]:
                    if neighbor_edge in unseen:
                        unseen.remove(neighbor_edge)
                        component_edges.append(neighbor_edge)
                        stack.append(neighbor_edge)
        result.append(component_edges)
    return result


def ordered_loop(edge_keys):
    adjacency_map = {}
    for first, second in edge_keys:
        adjacency_map.setdefault(first, []).append(second)
        adjacency_map.setdefault(second, []).append(first)
    start = max(adjacency_map, key=lambda index: mesh.vertices[index].co.x)
    following = max(adjacency_map[start], key=lambda index: mesh.vertices[index].co.z)
    result = [start, following]
    previous = start
    current = following
    while True:
        candidate = next(index for index in adjacency_map[current] if index != previous)
        if candidate == start:
            break
        result.append(candidate)
        previous, current = current, candidate
    return result


def cheapest_connection(left, right):
    allowed = {
        index
        for index, polygon in patch_faces.items()
        if (
            abs(polygon.center.x) < 0.075
            and polygon.center.y < 0.035
            and 0.65 < polygon.center.z < 0.855
        )
    }
    queue = []
    predecessor = {}
    cost = {}
    for index in left:
        cost[index] = 0.0
        heapq.heappush(queue, (0.0, index))
    target = None
    while queue:
        current_cost, current = heapq.heappop(queue)
        if current_cost != cost[current]:
            continue
        if current in right:
            target = current
            break
        for neighbor in adjacency[current]:
            if neighbor not in allowed:
                continue
            center = patch_faces[neighbor].center
            step = (
                1.0
                + abs(center.x) * 4.0
                + max(0.0, center.y + 0.02) * 12.0
                + abs(center.z - 0.81) * 1.5
            )
            candidate = current_cost + step
            if candidate < cost.get(neighbor, float("inf")):
                cost[neighbor] = candidate
                predecessor[neighbor] = current
                heapq.heappush(queue, (candidate, neighbor))
    if target is None:
        raise RuntimeError("no bounded bilateral connector path found")
    path = [target]
    while path[-1] not in left:
        path.append(predecessor[path[-1]])
    path.reverse()
    return path


for name, predicate in {
    "seed_narrow": lambda c: abs(c.x) < 0.040 and c.y < -0.020 and 0.665 < c.z < 0.805,
    "seed_medium": lambda c: abs(c.x) < 0.048 and c.y < -0.020 and 0.650 < c.z < 0.815,
    "seed_upper": lambda c: abs(c.x) < 0.042 and c.y < -0.015 and 0.690 < c.z < 0.815,
}.items():
    seed = {index for index, polygon in patch_faces.items() if predicate(polygon.center)}
    seed_components = sorted(components(seed), key=len, reverse=True)
    print(name, "seed_faces", len(seed), "components", [len(value) for value in seed_components])
    if len(seed_components) != 2:
        continue
    path = cheapest_connection(seed_components[0], seed_components[1])
    connected = seed | set(path)
    loops = boundary_loops(connected)
    vertices = {
        vertex
        for index in connected
        for vertex in patch_faces[index].vertices
    }
    points = [mesh.vertices[index].co for index in vertices]
    print(
        name,
        "path",
        path,
        "path_centers",
        [tuple(round(value, 5) for value in patch_faces[index].center) for index in path],
    )
    print(
        name,
        "connected_faces",
        len(connected),
        "face_components",
        [len(value) for value in components(connected)],
        "boundary_loops",
        [len(value) for value in loops],
        "bounds",
        (min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)),
        (max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)),
    )
    if name == "seed_narrow" and len(loops) == 1:
        order = ordered_loop(loops[0])
        ordered_points = [mesh.vertices[index].co for index in order]
        center_x = sum(point.x for point in ordered_points) / len(ordered_points)
        center_z = sum(point.z for point in ordered_points) / len(ordered_points)
        first_raw = math.atan2(
            ordered_points[0].z - center_z, ordered_points[0].x - center_x
        )
        raw_values = [
            (math.atan2(point.z - center_z, point.x - center_x) - first_raw)
            % (2.0 * math.pi)
            for point in ordered_points
        ]
        decreases = [
            (index, raw_values[index - 1], raw_values[index])
            for index in range(1, len(raw_values))
            if raw_values[index] + 1e-6 < raw_values[index - 1]
        ]
        print(
            "seed_narrow projected_angle",
            "center",
            (center_x, center_z),
            "first_raw",
            first_raw,
            "decreases",
            decreases,
            "sample",
            [round(value, 3) for value in raw_values],
        )

for label, face_indices in {
    "connector_center_2": {10979, 10980},
    "connector_center_4": {10973, 10979, 10980, 6400},
    "connector_center_6": {10619, 10973, 10979, 10980, 6400, 6047},
    "connector_path_10": {10608, 10619, 10973, 10979, 10980, 6400, 6047, 6036, 10571, 5999},
}.items():
    loops = boundary_loops(face_indices)
    vertices = {
        vertex
        for index in face_indices
        for vertex in patch_faces[index].vertices
    }
    points = [mesh.vertices[index].co for index in vertices]
    print(
        label,
        "components",
        [len(value) for value in components(face_indices)],
        "loops",
        [len(value) for value in loops],
        "bounds",
        (min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)),
        (max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)),
    )
