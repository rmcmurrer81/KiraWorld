#!/usr/bin/env python3
"""Read-only probe for the visible face-shell lip boundary on Kira R7."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

import bpy


HIDDEN_VERTEX_COUNT = 207
HIDDEN_INDEX_SHA256 = (
    "dee38f86b4bfbb732a3cbcc4ae2927f8ff50626d463dcdcfe4bca1f0b84edc3b"
)


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def index_sha256(indices: list[int]) -> str:
    digest = hashlib.sha256()
    for index in sorted(indices):
        digest.update(struct.pack("<I", index))
    return digest.hexdigest()


def mesh_components(mesh: bpy.types.Mesh) -> list[list[int]]:
    adjacency: dict[int, set[int]] = defaultdict(set)
    for edge in mesh.edges:
        first, second = (int(value) for value in edge.vertices)
        adjacency[first].add(second)
        adjacency[second].add(first)
    remaining = set(range(len(mesh.vertices)))
    result: list[list[int]] = []
    while remaining:
        seed = min(remaining)
        stack = [seed]
        found: set[int] = set()
        while stack:
            current = stack.pop()
            if current in found:
                continue
            found.add(current)
            stack.extend(adjacency[current] - found)
        remaining -= found
        result.append(sorted(found))
    return result


def edge_components(edges: list[tuple[int, int]]) -> list[dict[str, object]]:
    adjacency: dict[int, set[int]] = defaultdict(set)
    for first, second in edges:
        adjacency[first].add(second)
        adjacency[second].add(first)
    remaining = set(adjacency)
    result: list[dict[str, object]] = []
    while remaining:
        seed = min(remaining)
        stack = [seed]
        vertices: set[int] = set()
        while stack:
            current = stack.pop()
            if current in vertices:
                continue
            vertices.add(current)
            stack.extend(adjacency[current] - vertices)
        remaining -= vertices
        component_edges = [
            edge for edge in edges if edge[0] in vertices and edge[1] in vertices
        ]
        result.append(
            {
                "vertices": sorted(vertices),
                "edges": [list(edge) for edge in sorted(component_edges)],
                "degree_histogram": {
                    str(degree): sum(
                        1 for vertex in vertices if len(adjacency[vertex]) == degree
                    )
                    for degree in sorted({len(adjacency[vertex]) for vertex in vertices})
                },
            }
        )
    return sorted(result, key=lambda item: (-len(item["vertices"]), item["vertices"][0]))


def main() -> int:
    args = parse_args()
    output = Path(args.output).resolve()
    bodies = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.get("r7_role") == "working_body_unauthored"
    ]
    if len(bodies) != 1:
        raise ValueError(f"expected one R7 working body, found {len(bodies)}")
    body = bodies[0]
    mesh = body.data
    mesh.update()

    hidden_matches = [
        component
        for component in mesh_components(mesh)
        if len(component) == HIDDEN_VERTEX_COUNT
        and index_sha256(component) == HIDDEN_INDEX_SHA256
    ]
    if len(hidden_matches) != 1:
        raise ValueError(f"expected one exact hidden mouth patch, found {len(hidden_matches)}")
    hidden = set(hidden_matches[0])

    edge_use: dict[tuple[int, int], int] = defaultdict(int)
    for polygon in mesh.polygons:
        vertices = [int(value) for value in polygon.vertices]
        for ordinal, first in enumerate(vertices):
            second = vertices[(ordinal + 1) % len(vertices)]
            edge_use[tuple(sorted((first, second)))] += 1

    def in_roi(index: int) -> bool:
        point = mesh.vertices[index].co
        return (
            index not in hidden
            and abs(float(point.x)) <= 0.11
            and -0.405 <= float(point.y) <= -0.325
            and 6.545 <= float(point.z) <= 6.61
        )

    roi_boundary_edges = sorted(
        edge
        for edge, count in edge_use.items()
        if count == 1 and in_roi(edge[0]) and in_roi(edge[1])
    )
    components = edge_components(roi_boundary_edges)
    roi_vertices = sorted({index for edge in roi_boundary_edges for index in edge})
    vertex_records = {
        str(index): {
            "co": [round(float(value), 9) for value in mesh.vertices[index].co],
            "normal": [round(float(value), 9) for value in mesh.vertices[index].normal],
            "normal_z": round(float(mesh.vertices[index].normal.z), 9),
        }
        for index in roi_vertices
    }
    for component in components:
        component["records"] = {
            str(index): vertex_records[str(index)] for index in component["vertices"]
        }
        component["bounds"] = {
            axis: [
                round(
                    min(float(getattr(mesh.vertices[index].co, axis)) for index in component["vertices"]),
                    9,
                ),
                round(
                    max(float(getattr(mesh.vertices[index].co, axis)) for index in component["vertices"]),
                    9,
                ),
            ]
            for axis in ("x", "y", "z")
        }
    result = {
        "workspace": str(Path(bpy.data.filepath).resolve()),
        "body": body.name,
        "mesh": mesh.name,
        "hidden_component": {
            "vertex_count": len(hidden),
            "vertex_index_sha256": index_sha256(sorted(hidden)),
        },
        "roi_boundary_edge_count": len(roi_boundary_edges),
        "roi_boundary_vertex_count": len(roi_vertices),
        "components": components,
        "vertices": vertex_records,
        "safety": {"geometry_edited": False, "blend_saved": False},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "component_sizes": [len(item["vertices"]) for item in components],
        "edge_counts": [len(item["edges"]) for item in components],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
