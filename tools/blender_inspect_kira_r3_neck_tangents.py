"""Inspect sealed R3 neck endpoint neighborhoods without changing the Blend."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector


OBJECT_R3 = "Kira_R7_Measured_Neck_Bridge_R3_Inactive"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def stats(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {
        "minimum": min(values, default=0.0),
        "median": ordered[len(ordered) // 2] if ordered else 0.0,
        "mean": sum(values) / len(values) if values else 0.0,
        "maximum": max(values, default=0.0),
    }


def layer_records(
    points: list[Vector],
    faces: list[tuple[int, ...]],
    boundary: set[int],
    allowed: set[int],
    count: int,
) -> list[dict[str, object]]:
    adjacency: defaultdict[int, set[int]] = defaultdict(set)
    for face in faces:
        if not all(index in allowed for index in face):
            continue
        for position, index in enumerate(face):
            adjacency[index].add(face[(position - 1) % len(face)])
            adjacency[index].add(face[(position + 1) % len(face)])
    records: list[dict[str, object]] = []
    visited = set(boundary)
    frontier = set(boundary)
    for layer in range(count):
        indices = sorted(frontier)
        center = sum((points[index] for index in indices), Vector()) / max(1, len(indices))
        radii = [Vector((points[index].x - center.x, points[index].y - center.y)).length for index in indices]
        records.append({
            "layer": layer,
            "vertex_count": len(indices),
            "center": [float(center.x), float(center.y), float(center.z)],
            "z": stats([float(points[index].z) for index in indices]),
            "radius_from_layer_center_xy": stats(radii),
        })
        nxt = {
            neighbor
            for index in frontier
            for neighbor in adjacency[index]
            if neighbor not in visited
        }
        visited.update(nxt)
        frontier = nxt
        if not frontier:
            break
    return records


def main() -> int:
    args = parse_args()
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    body_count = int(evidence["bridge"]["head_vertex_offset"])
    source = bpy.data.objects.get(OBJECT_R3)
    if source is None or source.type != "MESH":
        raise RuntimeError("sealed R3 surface missing")
    points = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
    faces = [tuple(map(int, polygon.vertices)) for polygon in source.data.polygons]
    mixed = [face for face in faces if any(i < body_count for i in face) and any(i >= body_count for i in face)]
    body_boundary = {i for face in mixed for i in face if i < body_count}
    head_boundary = {i for face in mixed for i in face if i >= body_count}
    result = {
        "body_layers": layer_records(points, faces, body_boundary, set(range(body_count)), 20),
        "head_layers": layer_records(points, faces, head_boundary, set(range(body_count, len(points))), 20),
        "bridge_height_m": float(
            sum(points[i].z for i in head_boundary) / len(head_boundary)
            - sum(points[i].z for i in body_boundary) / len(body_boundary)
        ),
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
