#!/usr/bin/env python3
"""Read-only geometry probe for Kira R19's rejected pelvic insert.

The script is intended for Blender background mode with the exact sealed R19
Blend already opened.  It writes only a JSON diagnostic in RecoverySprint and
never saves the Blend.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(r"C:\Users\robmc\Kira")
SOURCE = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/"
    "attempt_06/kira_r19_bald_targeted_material_movement_correction.blend"
)
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_localized_repair/"
    "pelvis_geometry_probe_01/GEOMETRY_PROBE.json"
)
BODY_NAME = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
PATCH_SLOT = 5
EXPECTED_SHA = "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def vec(value: Vector) -> list[float]:
    return [float(value.x), float(value.y), float(value.z)]


def ordered_cycle(edges: set[tuple[int, int]]) -> list[int]:
    neighbors: dict[int, list[int]] = defaultdict(list)
    for first, second in edges:
        neighbors[first].append(second)
        neighbors[second].append(first)
    if any(len(values) != 2 for values in neighbors.values()):
        raise RuntimeError("interface is not one closed degree-two cycle")
    start = min(neighbors)
    options = sorted(neighbors[start])
    cycles = []
    for following in options:
        cycle = [start, following]
        previous, current = start, following
        while True:
            candidates = [value for value in neighbors[current] if value != previous]
            if len(candidates) != 1:
                raise RuntimeError("interface traversal became ambiguous")
            nxt = candidates[0]
            if nxt == start:
                break
            if nxt in cycle:
                raise RuntimeError("interface cycle self-repeated")
            cycle.append(nxt)
            previous, current = current, nxt
        cycles.append(cycle)
    return min(cycles)


def main() -> int:
    if Path(bpy.data.filepath).resolve() != SOURCE.resolve():
        raise RuntimeError("exact source Blend is not loaded")
    if sha256_file(SOURCE) != EXPECTED_SHA:
        raise RuntimeError("source Blend hash drifted")
    body = bpy.data.objects.get(BODY_NAME)
    if body is None or body.type != "MESH":
        raise RuntimeError("body mesh is absent")
    patch_faces = {
        int(poly.index)
        for poly in body.data.polygons
        if int(poly.material_index) == PATCH_SLOT
    }
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    neighbors: dict[int, set[int]] = defaultdict(set)
    for poly in body.data.polygons:
        ids = list(map(int, poly.vertices))
        for offset, first in enumerate(ids):
            second = ids[(offset + 1) % len(ids)]
            edge = tuple(sorted((first, second)))
            edge_faces[edge].append(int(poly.index))
            neighbors[first].add(second)
            neighbors[second].add(first)
    interface_edges = {
        edge
        for edge, faces in edge_faces.items()
        if len(faces) == 2 and sum(face in patch_faces for face in faces) == 1
    }
    cycle = ordered_cycle(interface_edges)
    incident = {int(v) for face in patch_faces for v in body.data.polygons[face].vertices}
    points_local = {index: body.data.vertices[index].co.copy() for index in incident}
    points_world = {index: body.matrix_world @ point for index, point in points_local.items()}
    minimum = Vector(tuple(min(point[axis] for point in points_world.values()) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in points_world.values()) for axis in range(3)))
    seam_points = [points_world[index] for index in cycle]
    seam_center = sum(seam_points, Vector()) / len(seam_points)
    patch_center = sum(points_world.values(), Vector()) / len(points_world)
    records = []
    for index in cycle:
        outside_faces = [
            face
            for edge, faces in edge_faces.items()
            if index in edge
            for face in faces
            if face not in patch_faces
        ]
        normal = sum((body.data.polygons[face].normal.copy() for face in outside_faces), Vector())
        if normal.length:
            normal.normalize()
        records.append({
            "vertex_index": index,
            "local": vec(points_local[index]),
            "world_m": vec(points_world[index]),
            "outside_average_normal_local": vec(normal),
            "outside_average_normal_world": vec((body.matrix_world.to_3x3() @ normal).normalized()),
        })
    payload = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "source": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": EXPECTED_SHA,
        "body": BODY_NAME,
        "body_matrix_world": [[float(v) for v in row] for row in body.matrix_world],
        "patch_face_count": len(patch_faces),
        "patch_incident_vertex_count": len(incident),
        "interface_edge_count": len(interface_edges),
        "interface_vertex_count": len(cycle),
        "interface_cycle": records,
        "patch_world_bounds_m": {"minimum": vec(minimum), "maximum": vec(maximum)},
        "patch_world_center_m": vec(patch_center),
        "seam_world_center_m": vec(seam_center),
        "patch_vertices": [
            {"vertex_index": index, "local": vec(points_local[index]), "world_m": vec(points_world[index])}
            for index in sorted(incident)
        ],
        "source_blend_saved": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "bounds": payload["patch_world_bounds_m"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
