"""Measure the sealed R3 body/head neck boundaries and nearby body topology."""

from __future__ import annotations

import argparse
import bisect
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


def ordered_loop(points: list[Vector], indices: set[int]) -> tuple[list[int], Vector, list[float]]:
    center = sum((points[index] for index in indices), Vector()) / len(indices)
    ordered = sorted(
        indices,
        key=lambda index: math.atan2(points[index].y - center.y, points[index].x - center.x) % math.tau,
    )
    angles = [math.atan2(points[index].y - center.y, points[index].x - center.x) % math.tau for index in ordered]
    return ordered, center, angles


def sample_at_angle(ordered: list[int], center: Vector, angles: list[float], points: list[Vector], angle: float) -> Vector:
    angle %= math.tau
    right = bisect.bisect_right(angles, angle) % len(ordered)
    left = (right - 1) % len(ordered)
    angle_left = angles[left]
    angle_right = angles[right] + (math.tau if right == 0 else 0.0)
    if angle < angle_left:
        angle += math.tau
    alpha = (angle - angle_left) / max(1e-12, angle_right - angle_left)
    return points[ordered[left]].lerp(points[ordered[right]], alpha)


def stats(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {
        "minimum": min(values, default=0.0),
        "median": ordered[len(ordered) // 2] if ordered else 0.0,
        "mean": sum(values) / len(values) if values else 0.0,
        "maximum": max(values, default=0.0),
    }


def main() -> int:
    args = parse_args()
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    body_count = int(evidence["bridge"]["head_vertex_offset"])
    source = bpy.data.objects.get(OBJECT_R3)
    if source is None:
        raise RuntimeError("sealed R3 object not found")
    points = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
    faces = [tuple(map(int, polygon.vertices)) for polygon in source.data.polygons]
    bridge_faces = [face for face in faces if any(index < body_count for index in face) and any(index >= body_count for index in face)]
    retained_body_faces = [face for face in faces if all(index < body_count for index in face)]
    body_boundary = {index for face in bridge_faces for index in face if index < body_count}
    head_boundary = {index for face in bridge_faces for index in face if index >= body_count}
    body_loop, body_center, body_angles = ordered_loop(points, body_boundary)
    head_loop, head_center, head_angles = ordered_loop(points, head_boundary)

    body_radii = [(Vector((points[index].x - body_center.x, points[index].y - body_center.y))).length for index in body_loop]
    head_radii = [(Vector((points[index].x - head_center.x, points[index].y - head_center.y))).length for index in head_loop]
    boundary_displacements: list[float] = []
    boundary_lateral_displacements: list[float] = []
    for index in body_loop:
        angle = math.atan2(points[index].y - body_center.y, points[index].x - body_center.x) % math.tau
        target = sample_at_angle(head_loop, head_center, head_angles, points, angle)
        boundary_displacements.append((target - points[index]).length)
        boundary_lateral_displacements.append(Vector((target.x - points[index].x, target.y - points[index].y)).length)

    adjacency: defaultdict[int, set[int]] = defaultdict(set)
    for face in retained_body_faces:
        for position, index in enumerate(face):
            adjacency[index].add(face[(position - 1) % len(face)])
            adjacency[index].add(face[(position + 1) % len(face)])
    layers: list[dict[str, object]] = []
    visited = set(body_boundary)
    frontier = set(body_boundary)
    for layer_number in range(13):
        values = sorted(frontier)
        zs = [points[index].z for index in values]
        radii = [Vector((points[index].x - body_center.x, points[index].y - body_center.y)).length for index in values]
        layers.append({
            "layer": layer_number,
            "vertex_count": len(values),
            "z": stats(zs),
            "radius_from_body_boundary_center_xy": stats(radii),
        })
        nxt = {neighbor for index in frontier for neighbor in adjacency[index] if neighbor not in visited}
        visited.update(nxt)
        frontier = nxt
        if not frontier:
            break

    neck_candidates = [
        index
        for index in range(body_count)
        if points[index].z >= body_center.z - 0.18
        and Vector((points[index].x - body_center.x, points[index].y - body_center.y)).length <= max(body_radii) + 0.10
    ]
    result = {
        "body_count": body_count,
        "body_boundary": {
            "count": len(body_loop),
            "center": list(body_center),
            "z": stats([points[index].z for index in body_loop]),
            "radius": stats(body_radii),
        },
        "head_boundary": {
            "count": len(head_loop),
            "center": list(head_center),
            "z": stats([points[index].z for index in head_loop]),
            "radius": stats(head_radii),
        },
        "body_to_head_boundary_displacement": stats(boundary_displacements),
        "body_to_head_boundary_lateral_displacement": stats(boundary_lateral_displacements),
        "body_adjacency_layers": layers,
        "spatial_neck_candidate_count": len(neck_candidates),
        "spatial_neck_candidate_z": stats([points[index].z for index in neck_candidates]),
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
