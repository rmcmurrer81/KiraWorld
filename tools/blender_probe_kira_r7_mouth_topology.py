#!/usr/bin/env python3
"""Measure the exact disconnected Kira R7 lip island without editing it.

This Blender worker is intentionally read-only.  It records boundary-loop and
polygon facts for the one 207-vertex component already pinned by the R7 face
boundary audit.  It deliberately does not infer an oral fissure from geometry:
the source has no authored semantic edge map, and guessing that boundary could
change the existing single mouth that this workspace is required to preserve.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

import bpy


EXPECTED_VERTEX_COUNT = 207
EXPECTED_INDEX_SHA256 = (
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


def connected_components(mesh: bpy.types.Mesh) -> list[list[int]]:
    adjacency: dict[int, set[int]] = defaultdict(set)
    for edge in mesh.edges:
        first, second = (int(value) for value in edge.vertices)
        adjacency[first].add(second)
        adjacency[second].add(first)
    remaining = set(range(len(mesh.vertices)))
    components: list[list[int]] = []
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
        components.append(sorted(found))
    return sorted(components, key=lambda item: (-len(item), item[0]))


def boundary_loops(boundary_edges: list[tuple[int, int]]) -> list[list[int]]:
    adjacency: dict[int, list[int]] = defaultdict(list)
    for first, second in boundary_edges:
        adjacency[first].append(second)
        adjacency[second].append(first)
    remaining = {tuple(sorted(edge)) for edge in boundary_edges}
    loops: list[list[int]] = []
    while remaining:
        first, second = min(remaining)
        remaining.remove((first, second))
        loop = [first, second]
        previous, current = first, second
        while True:
            candidates = [
                candidate
                for candidate in adjacency[current]
                if candidate != previous
                and tuple(sorted((current, candidate))) in remaining
            ]
            if not candidates:
                break
            following = min(candidates)
            remaining.remove(tuple(sorted((current, following))))
            loop.append(following)
            previous, current = current, following
            if following == loop[0]:
                break
        loops.append(loop)
    return sorted(loops, key=lambda item: (-len(item), min(item)))


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
    matches = [
        component
        for component in connected_components(mesh)
        if len(component) == EXPECTED_VERTEX_COUNT
        and index_sha256(component) == EXPECTED_INDEX_SHA256
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one exact lip island, found {len(matches)}")
    indices = matches[0]
    index_set = set(indices)
    polygons = [
        polygon
        for polygon in mesh.polygons
        if all(int(vertex) in index_set for vertex in polygon.vertices)
    ]
    edge_use: dict[tuple[int, int], int] = defaultdict(int)
    for polygon in polygons:
        vertices = [int(vertex) for vertex in polygon.vertices]
        for ordinal, first in enumerate(vertices):
            second = vertices[(ordinal + 1) % len(vertices)]
            edge_use[tuple(sorted((first, second)))] += 1
    boundary_edges = sorted(edge for edge, count in edge_use.items() if count == 1)
    nonmanifold_edges = sorted(edge for edge, count in edge_use.items() if count != 2)
    loops = boundary_loops(boundary_edges)

    projected_vertices = {
        str(index): [
            round(float(mesh.vertices[index].co.x), 9),
            round(float(mesh.vertices[index].co.z), 9),
        ]
        for index in indices
    }
    component_edges = sorted(
        tuple(sorted((int(edge.vertices[0]), int(edge.vertices[1]))))
        for edge in mesh.edges
        if int(edge.vertices[0]) in index_set and int(edge.vertices[1]) in index_set
    )
    boundary_degree: dict[int, int] = defaultdict(int)
    for first, second in boundary_edges:
        boundary_degree[first] += 1
        boundary_degree[second] += 1
    degree_histogram: dict[str, int] = defaultdict(int)
    for degree in boundary_degree.values():
        degree_histogram[str(degree)] += 1

    records = []
    for ordinal, loop in enumerate(loops):
        unique = sorted(set(loop))
        coordinates = [mesh.vertices[index].co for index in unique]
        records.append(
            {
                "loop_id": f"boundary_{ordinal:02d}",
                "edge_count": max(0, len(loop) - (1 if loop and loop[-1] == loop[0] else 0)),
                "vertex_count": len(unique),
                "closed": bool(loop and len(loop) > 2 and loop[-1] == loop[0]),
                "vertex_index_sha256": index_sha256(unique),
                "ordered_vertex_indices": loop,
                "bounds": {
                    axis: [
                        round(min(float(getattr(point, axis)) for point in coordinates), 9),
                        round(max(float(getattr(point, axis)) for point in coordinates), 9),
                    ]
                    for axis in ("x", "y", "z")
                },
            }
        )

    result = {
        "schema_version": 1,
        "mode": "read_only_inactive_topology_probe",
        "workspace": str(Path(bpy.data.filepath).resolve()),
        "body_object": body.name,
        "body_mesh": mesh.name,
        "existing_mouth": {
            "vertex_count": len(indices),
            "vertex_index_sha256": index_sha256(indices),
            "polygon_count": len(polygons),
            "boundary_edge_count": len(boundary_edges),
            "nonmanifold_edge_count": len(nonmanifold_edges),
            "boundary_loop_count": len(loops),
            "boundary_loops": records,
            "boundary_vertex_degree_histogram": dict(sorted(degree_histogram.items())),
            "component_edge_count": len(component_edges),
            "euler_characteristic": len(indices) - len(component_edges) + len(polygons),
            "face_vertex_count_histogram": {
                str(size): sum(1 for polygon in polygons if len(polygon.vertices) == size)
                for size in sorted({len(polygon.vertices) for polygon in polygons})
            },
            "surface_classification": (
                "connected triangulated disk-like patch with one geometrically complex boundary"
            ),
            "semantic_edge_map_present": False,
            "central_oral_aperture_boundary_count": None,
            "central_oral_aperture_present": None,
            "central_oral_aperture_truth": (
                "unproven: one boundary loop cannot be partitioned into oral-fissure, "
                "attachment, and open-symmetry segments from topology alone"
            ),
            "shape_keys_preserve_topology": True,
            "interior_exposable_by_shape_keys_only": False,
            "non_destructive_real_mouth_authoring_feasible": False,
            "candidate_authoring_disposition": "stopped_before_edit",
            "exact_blocker": (
                "The exact 207-vertex mouth has one geometrically complex boundary loop but no "
                "authored semantic edge map. That loop contains visually lip-adjacent and open "
                "center/symmetry candidates, so topology cannot prove which edges are Kira's "
                "upper fissure, lower fissure, commissures, attachment rim, or symmetry seam. "
                "A symmetry or shortest-path selection would guess her lip seam and could "
                "damage the preserved existing mouth. Manual Blender selection of those edge "
                "roles is required before an isolated-copy cavity or viseme pass is safe."
            ),
        },
        "diagnostic_projection": {
            "axes": ["local_x", "local_z"],
            "vertices": projected_vertices,
            "local_xyz": {
                str(index): [
                    round(float(mesh.vertices[index].co.x), 9),
                    round(float(mesh.vertices[index].co.y), 9),
                    round(float(mesh.vertices[index].co.z), 9),
                ]
                for index in indices
            },
            "edges": [list(edge) for edge in component_edges],
            "boundary_edges": [list(edge) for edge in boundary_edges],
        },
        "safety": {
            "geometry_edited": False,
            "blend_saved": False,
            "model_exported": False,
            "runtime_binding_touched": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["existing_mouth"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
