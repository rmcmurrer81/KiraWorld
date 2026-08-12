#!/usr/bin/env python3
"""Read-only nail-to-digit alignment probe for the BlackProject source."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import deque
from pathlib import Path

import bpy
from mathutils import Vector


SOURCE_SHA256 = "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def components(obj: bpy.types.Object) -> list[list[int]]:
    adjacency: list[list[int]] = [[] for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = map(int, edge.vertices)
        adjacency[a].append(b)
        adjacency[b].append(a)
    unseen = set(range(len(obj.data.vertices)))
    result: list[list[int]] = []
    while unseen:
        start = unseen.pop()
        queue = deque([start])
        component = [start]
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
                    component.append(neighbor)
        result.append(component)
    return sorted(result, key=len, reverse=True)


def world_bounds(points: list[Vector]) -> dict[str, list[float]]:
    low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    return {
        "low": [round(float(value), 9) for value in low],
        "high": [round(float(value), 9) for value in high],
        "size": [round(float(value), 9) for value in high - low],
        "center": [round(float(value), 9) for value in (low + high) * 0.5],
    }


def dominant_group_name(obj: bpy.types.Object, indices: list[int]) -> str:
    totals: dict[int, float] = {}
    for index in indices:
        for assignment in obj.data.vertices[index].groups:
            totals[assignment.group] = totals.get(assignment.group, 0.0) + float(assignment.weight)
    if not totals:
        raise ValueError("nail component has no vertex-group assignments")
    return obj.vertex_groups[max(totals, key=totals.get)].name


def body_group_points(body: bpy.types.Object, group_name: str) -> list[Vector]:
    group = body.vertex_groups.get(group_name)
    if group is None:
        return []
    result = []
    for vertex in body.data.vertices:
        if any(
            assignment.group == group.index and assignment.weight >= 0.05
            for assignment in vertex.groups
        ):
            result.append(body.matrix_world @ vertex.co)
    return result


def main() -> None:
    args = parse_args()
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    if sha256_file(source) != SOURCE_SHA256:
        raise ValueError("source hash mismatch")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(source))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    meshes = {obj.data.name: obj for obj in imported if obj.type == "MESH"}
    records: dict[str, list[dict[str, object]]] = {}
    for nail_name, body_name in (
        ("Ariel_Mesh_Fingernails_0", "Ariel_Mesh_Arms_0"),
        ("Ariel_Mesh_Toenails_0", "Ariel_Mesh_Legs_0"),
    ):
        nail = meshes[nail_name]
        body = meshes[body_name]
        items = []
        for component in components(nail):
            group_name = dominant_group_name(nail, component)
            nail_points = [nail.matrix_world @ nail.data.vertices[index].co for index in component]
            digit_points = body_group_points(body, group_name)
            items.append(
                {
                    "component_vertex_count": len(component),
                    "dominant_group": group_name,
                    "nail_bounds_m": world_bounds(nail_points),
                    "digit_bounds_m": world_bounds(digit_points) if digit_points else None,
                }
            )
        records[nail_name] = items
    result = {
        "schema_version": 1,
        "mode": "READ_ONLY_NAIL_ALIGNMENT_PROBE",
        "source_sha256": SOURCE_SHA256,
        "records": records,
        "runtime_files_read_or_written": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["records"], indent=2))


if __name__ == "__main__":
    main()
