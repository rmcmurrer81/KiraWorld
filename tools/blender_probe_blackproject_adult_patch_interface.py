#!/usr/bin/env python3
"""Measure the BlackProject adult replacement patch against its base surface.

This is a read-only geometry probe for the isolated Kira temporary-body work.
It does not author a candidate or touch any runtime file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import deque
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree


SOURCE_SHA256 = "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df"
ADULT_NAME = "Ariel_Mesh_Genitalia_0"
BASE_NAMES = (
    "Ariel_Mesh_Torso_0",
    "Ariel_Mesh_Arms_0",
    "Ariel_Mesh_Legs_0",
    "Ariel_Mesh_Face_0",
    "Ariel_Mesh_Ears_0",
)


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


def import_glb(path: Path) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [obj for obj in bpy.data.objects if obj not in before]


def boundary_loops(obj: bpy.types.Object) -> list[list[int]]:
    counts: dict[tuple[int, int], int] = {}
    for polygon in obj.data.polygons:
        vertices = list(map(int, polygon.vertices))
        for index, a in enumerate(vertices):
            b = vertices[(index + 1) % len(vertices)]
            edge = tuple(sorted((a, b)))
            counts[edge] = counts.get(edge, 0) + 1
    boundary = [edge for edge, count in counts.items() if count == 1]
    adjacency: dict[int, list[int]] = {}
    for a, b in boundary:
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    loops: list[list[int]] = []
    unseen = set(adjacency)
    while unseen:
        start = min(unseen)
        queue = deque([start])
        component: list[int] = []
        unseen.remove(start)
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
        loops.append(component)
    return sorted(loops, key=len, reverse=True)


def mesh_world_data(
    obj: bpy.types.Object,
) -> tuple[list[Vector], list[tuple[int, ...]]]:
    vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    polygons = [tuple(map(int, polygon.vertices)) for polygon in obj.data.polygons]
    return vertices, polygons


def bounds(points: list[Vector]) -> dict[str, list[float]]:
    low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    return {
        "low": [round(float(value), 9) for value in low],
        "high": [round(float(value), 9) for value in high],
        "size": [round(float(value), 9) for value in high - low],
    }


def main() -> None:
    args = parse_args()
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    if sha256_file(source) != SOURCE_SHA256:
        raise ValueError("source hash mismatch")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    imported = import_glb(source)
    meshes = {obj.data.name: obj for obj in imported if obj.type == "MESH"}
    missing = sorted(set((*BASE_NAMES, ADULT_NAME)) - set(meshes))
    if missing:
        raise ValueError(f"required meshes missing: {missing}")

    adult = meshes[ADULT_NAME]
    adult_vertices, adult_polygons = mesh_world_data(adult)
    adult_loops = boundary_loops(adult)
    adult_boundary_indices = sorted({index for loop in adult_loops for index in loop})

    base_points: list[Vector] = []
    base_polygons_world: list[tuple[Vector, ...]] = []
    base_records: list[dict[str, object]] = []
    vertex_offset = 0
    for name in BASE_NAMES:
        obj = meshes[name]
        vertices, polygons = mesh_world_data(obj)
        base_points.extend(vertices)
        base_polygons_world.extend(tuple(vertices[index] for index in face) for face in polygons)
        base_records.append(
            {
                "mesh": name,
                "vertex_offset": vertex_offset,
                "vertices": len(vertices),
                "polygons": len(polygons),
                "boundary_loop_sizes": [len(loop) for loop in boundary_loops(obj)],
            }
        )
        vertex_offset += len(vertices)

    base_tree = KDTree(len(base_points))
    for index, point in enumerate(base_points):
        base_tree.insert(point, index)
    base_tree.balance()
    boundary_nearest = []
    for index in adult_boundary_indices:
        point = adult_vertices[index]
        nearest, base_index, distance = base_tree.find(point)
        boundary_nearest.append(
            {
                "adult_vertex": index,
                "base_vertex": int(base_index),
                "distance_m": float(distance),
                "adult_world": [float(value) for value in point],
                "base_world": [float(value) for value in nearest],
            }
        )

    # Triangulate only for closest-surface measurements.  This remains
    # read-only and does not alter the imported source objects.
    base_bvh_vertices: list[tuple[float, float, float]] = []
    base_bvh_polygons: list[tuple[int, int, int]] = []
    for polygon in base_polygons_world:
        start = len(base_bvh_vertices)
        base_bvh_vertices.extend(tuple(point) for point in polygon)
        for index in range(1, len(polygon) - 1):
            base_bvh_polygons.append((start, start + index, start + index + 1))
    base_bvh = BVHTree.FromPolygons(base_bvh_vertices, base_bvh_polygons, all_triangles=True)
    adult_to_base_surface = []
    for point in adult_vertices:
        nearest, _normal, _face_index, distance = base_bvh.find_nearest(point)
        if nearest is not None and distance is not None:
            adult_to_base_surface.append(float(distance))
    adult_to_base_surface.sort()

    result = {
        "schema_version": 1,
        "mode": "READ_ONLY_INTERFACE_PROBE",
        "source": {
            "path": str(source),
            "sha256": SOURCE_SHA256,
        },
        "adult_patch": {
            "mesh": ADULT_NAME,
            "vertices": len(adult_vertices),
            "polygons": len(adult_polygons),
            "bounds_m": bounds(adult_vertices),
            "boundary_loop_count": len(adult_loops),
            "boundary_loop_sizes": [len(loop) for loop in adult_loops],
            "boundary_vertex_count": len(adult_boundary_indices),
            "ordered_boundary_cycles_world_m": [
                [
                    [
                        round(float(value), 9)
                        for value in adult_vertices[index]
                    ]
                    for index in loop
                ]
                for loop in adult_loops
            ],
        },
        "base_meshes": base_records,
        "adult_boundary_to_base_vertices": {
            "minimum_m": min(item["distance_m"] for item in boundary_nearest),
            "maximum_m": max(item["distance_m"] for item in boundary_nearest),
            "count_under_1e_8_m": sum(item["distance_m"] <= 1e-8 for item in boundary_nearest),
            "count_under_1e_6_m": sum(item["distance_m"] <= 1e-6 for item in boundary_nearest),
            "count_under_1e_4_m": sum(item["distance_m"] <= 1e-4 for item in boundary_nearest),
            "records": boundary_nearest,
        },
        "all_adult_vertices_to_base_surface": {
            "minimum_m": adult_to_base_surface[0],
            "p05_m": adult_to_base_surface[round((len(adult_to_base_surface) - 1) * 0.05)],
            "median_m": adult_to_base_surface[round((len(adult_to_base_surface) - 1) * 0.50)],
            "p95_m": adult_to_base_surface[round((len(adult_to_base_surface) - 1) * 0.95)],
            "maximum_m": adult_to_base_surface[-1],
            "count_under_1e_6_m": sum(value <= 1e-6 for value in adult_to_base_surface),
            "count_under_1e_4_m": sum(value <= 1e-4 for value in adult_to_base_surface),
        },
        "conclusion_gate": (
            "DIRECT_BOUNDARY_REPLACEMENT_POSSIBLE"
            if all(item["distance_m"] <= 1e-6 for item in boundary_nearest)
            else "BOUNDARY_REQUIRES_EXPLICIT_BRIDGE_OR_RETOPOLOGY"
        ),
        "truth_note": "No candidate or runtime file was authored by this read-only probe.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("adult_patch", "adult_boundary_to_base_vertices", "all_adult_vertices_to_base_surface", "conclusion_gate")}, indent=2))


if __name__ == "__main__":
    main()
