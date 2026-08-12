#!/usr/bin/env python3
"""Localize exact nonadjacent intersections on an inactive body candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mesh-name", default="")
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    source = Path(args.input).resolve()
    output = Path(args.output).resolve()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(source))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    bodies = (
        [
            obj
            for obj in imported
            if obj.type == "MESH" and obj.data.name == args.mesh_name
        ]
        if args.mesh_name
        else [
            obj
            for obj in imported
            if obj.type == "MESH" and bool(obj.get("rapid_body_primary_surface", False))
        ]
    )
    if len(bodies) != 1:
        raise ValueError(f"expected one marked primary surface, found {len(bodies)}")
    body = bodies[0]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        low = Vector(tuple(min(point[axis] for point in vertices) for axis in range(3)))
        high = Vector(tuple(max(point[axis] for point in vertices) for axis in range(3)))
        weld_tolerance = max(max(float(value) for value in high - low) * 1e-6, 1e-9)
        positional_keys = [
            tuple(int(round(float(point[axis]) / weld_tolerance)) for axis in range(3))
            for point in vertices
        ]
        triangles: list[tuple[int, int, int]] = []
        index_sets: list[set[int]] = []
        key_sets: list[set[tuple[int, int, int]]] = []
        for polygon in mesh.polygons:
            indices = list(map(int, polygon.vertices))
            for offset in range(1, len(indices) - 1):
                triangle = (indices[0], indices[offset], indices[offset + 1])
                triangles.append(triangle)
                index_sets.append(set(triangle))
                key_sets.append({positional_keys[index] for index in triangle})
        bvh = BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
        pairs: list[tuple[int, int]] = []
        involved: set[int] = set()
        centroids: list[Vector] = []
        for left, right in bvh.overlap(bvh):
            if left >= right:
                continue
            if index_sets[left] & index_sets[right]:
                continue
            if key_sets[left] & key_sets[right]:
                continue
            pairs.append((left, right))
            involved.update(triangles[left])
            involved.update(triangles[right])
            first = sum((vertices[index] for index in triangles[left]), Vector()) / 3.0
            second = sum((vertices[index] for index in triangles[right]), Vector()) / 3.0
            centroids.append((first + second) * 0.5)
        group_names = {group.index: group.name for group in body.vertex_groups}
        records = []
        for index in sorted(involved):
            source_vertex = body.data.vertices[index]
            weights = sorted(
                (
                    (group_names.get(assignment.group, f"group_{assignment.group}"), float(assignment.weight))
                    for assignment in source_vertex.groups
                    if assignment.weight > 1e-5
                ),
                key=lambda item: item[1],
                reverse=True,
            )
            point = vertices[index]
            records.append(
                {
                    "vertex": index,
                    "world_m": [round(float(value), 9) for value in point],
                    "groups": [[name, round(weight, 6)] for name, weight in weights],
                }
            )
        result = {
            "schema_version": 1,
            "mode": "READ_ONLY_EXACT_SHA_INTERSECTION_LOCALIZATION",
            "candidate_sha256": sha256_file(source),
            "pair_count": len(pairs),
            "involved_vertex_count": len(involved),
            "involved_bounds_m": (
                {
                    "low": [
                        min(record["world_m"][axis] for record in records)
                        for axis in range(3)
                    ],
                    "high": [
                        max(record["world_m"][axis] for record in records)
                        for axis in range(3)
                    ],
                }
                if records
                else None
            ),
            "centroid_bounds_m": (
                {
                    "low": [
                        round(min(point[axis] for point in centroids), 9)
                        for axis in range(3)
                    ],
                    "high": [
                        round(max(point[axis] for point in centroids), 9)
                        for axis in range(3)
                    ],
                }
                if centroids
                else None
            ),
            "x_sign_counts": {
                "negative": sum(record["world_m"][0] < -1e-6 for record in records),
                "near_zero": sum(abs(record["world_m"][0]) <= 1e-6 for record in records),
                "positive": sum(record["world_m"][0] > 1e-6 for record in records),
            },
            "first_pairs": [list(pair) for pair in pairs[:100]],
            "involved_vertices": records,
            "input_modified": False,
            "runtime_files_read_or_written": False,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "candidate_sha256": result["candidate_sha256"],
                    "pair_count": result["pair_count"],
                    "involved_vertex_count": result["involved_vertex_count"],
                    "involved_bounds_m": result["involved_bounds_m"],
                    "centroid_bounds_m": result["centroid_bounds_m"],
                    "x_sign_counts": result["x_sign_counts"],
                },
                indent=2,
            )
        )
    finally:
        evaluated.to_mesh_clear()


if __name__ == "__main__":
    main()
