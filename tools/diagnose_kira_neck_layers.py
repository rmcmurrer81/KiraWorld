from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "Data/avatar_builder_workspace_tests/kira_r7_adult_surface_trial_20260722/measured_neck_bridge_r3/evidence.json"
OBJECT_NAME = "Kira_R7_Measured_Neck_Bridge_R3_Inactive"


def boundary_components(faces: list[tuple[int, ...]], points: list[Vector]) -> list[dict[str, object]]:
    edge_use: defaultdict[tuple[int, int], int] = defaultdict(int)
    for face in faces:
        for position, a in enumerate(face):
            b = face[(position + 1) % len(face)]
            edge_use[tuple(sorted((a, b)))] += 1
    graph: defaultdict[int, list[int]] = defaultdict(list)
    for (a, b), count in edge_use.items():
        if count == 1:
            graph[a].append(b)
            graph[b].append(a)
    seen: set[int] = set()
    records: list[dict[str, object]] = []
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
        values = [points[index] for index in component]
        center = sum(values, Vector()) / len(values)
        records.append({
            "count": len(component),
            "all_degree_two": all(len(graph[index]) == 2 for index in component),
            "mean": [float(value) for value in center],
            "minimum": [min(float(point[axis]) for point in values) for axis in range(3)],
            "maximum": [max(float(point[axis]) for point in values) for axis in range(3)],
        })
    return records


def distances(seed: set[int], faces: list[tuple[int, ...]], allowed: set[int]) -> dict[int, int]:
    adjacency: defaultdict[int, set[int]] = defaultdict(set)
    for face in faces:
        for position, a in enumerate(face):
            b = face[(position + 1) % len(face)]
            if a in allowed and b in allowed:
                adjacency[a].add(b)
                adjacency[b].add(a)
    result = {index: 0 for index in seed}
    todo = deque(seed)
    while todo:
        current = todo.popleft()
        for neighbor in adjacency[current]:
            if neighbor not in result:
                result[neighbor] = result[current] + 1
                todo.append(neighbor)
    return result


evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
obj = bpy.data.objects[OBJECT_NAME]
body_count = int(evidence["bridge"]["head_vertex_offset"])
points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
faces = [tuple(map(int, polygon.vertices)) for polygon in obj.data.polygons]
bridge = [face for face in faces if any(index < body_count for index in face) and any(index >= body_count for index in face)]
retained = [face for face in faces if face not in bridge]
body_seed = {index for face in bridge for index in face if index < body_count}
head_seed = {index for face in bridge for index in face if index >= body_count}
body_allowed = set(range(body_count))
head_allowed = set(range(body_count, len(points)))
body_dist = distances(body_seed, retained, body_allowed)
head_dist = distances(head_seed, retained, head_allowed)

records: dict[str, object] = {"layers": {"body": {}, "head": {}}, "erosions": {"body": {}, "head": {}}}
for label, mapping in (("body", body_dist), ("head", head_dist)):
    for distance in range(0, 13):
        indices = [index for index, value in mapping.items() if value == distance]
        if not indices:
            continue
        values = [points[index] for index in indices]
        center = sum(values, Vector()) / len(values)
        records["layers"][label][str(distance)] = {
            "count": len(indices),
            "mean": [float(value) for value in center],
            "minimum": [min(float(point[axis]) for point in values) for axis in range(3)],
            "maximum": [max(float(point[axis]) for point in values) for axis in range(3)],
        }

for label, mapping, allowed in (
    ("body", body_dist, body_allowed),
    ("head", head_dist, head_allowed),
):
    other_allowed = head_allowed if label == "body" else body_allowed
    for depth in range(1, 11):
        removed = {index for index, value in mapping.items() if value < depth}
        kept_faces = [
            face for face in retained
            if all(index not in removed for index in face)
            and (all(index in allowed for index in face) or all(index in other_allowed for index in face))
        ]
        target_faces = [face for face in kept_faces if all(index in allowed for index in face)]
        records["erosions"][label][str(depth)] = boundary_components(target_faces, points)

print("NECK_LAYER_DIAGNOSTIC=" + json.dumps(records, sort_keys=True))
