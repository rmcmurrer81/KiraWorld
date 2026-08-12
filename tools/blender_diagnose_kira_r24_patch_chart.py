#!/usr/bin/env python3
"""Read-only chart and surface-normal audit for the exact sealed R19 patch.

This diagnostic exists to decide whether the rejected pelvic insert can be
re-authored as a single-valued local surface.  It never saves a Blend, changes
runtime state, or creates an owner-review candidate.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_simulate_kira_r24_broad_inplace_surface as base  # noqa: E402


OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_patch_chart_diagnostic/attempt_02"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def adjacency(mesh: bpy.types.Mesh):
    vertex_neighbors = [set() for _ in mesh.vertices]
    vertex_faces = [[] for _ in mesh.vertices]
    edge_faces: defaultdict[tuple[int, int], list[int]] = defaultdict(list)
    for polygon in mesh.polygons:
        vertices = [int(value) for value in polygon.vertices]
        for vertex in vertices:
            vertex_faces[vertex].append(int(polygon.index))
        for offset, first in enumerate(vertices):
            second = vertices[(offset + 1) % len(vertices)]
            edge = tuple(sorted((first, second)))
            edge_faces[edge].append(int(polygon.index))
            vertex_neighbors[first].add(second)
            vertex_neighbors[second].add(first)
    return vertex_neighbors, vertex_faces, edge_faces


def ordered_cycle(edges: set[tuple[int, int]]) -> list[int]:
    neighbors: defaultdict[int, list[int]] = defaultdict(list)
    for first, second in edges:
        neighbors[first].append(second)
        neighbors[second].append(first)
    if not neighbors or any(len(values) != 2 for values in neighbors.values()):
        raise RuntimeError("patch seam is not one simple degree-two cycle")
    start = min(neighbors)
    cycle = [start]
    previous = None
    current = start
    while True:
        choices = sorted(value for value in neighbors[current] if value != previous)
        following = choices[0]
        if following == start:
            break
        if following in cycle:
            raise RuntimeError("patch seam repeats before closure")
        cycle.append(following)
        previous, current = current, following
    if len(cycle) != len(neighbors):
        raise RuntimeError("patch seam contains more than one cycle")
    return cycle


def stats(values: list[float]) -> dict[str, float]:
    ordered = sorted(float(value) for value in values)
    return {
        "minimum": ordered[0],
        "maximum": ordered[-1],
        "mean": sum(ordered) / len(ordered),
        "median": ordered[len(ordered) // 2],
    }


def main() -> None:
    if sha256(base.SOURCE) != base.SOURCE_SHA256:
        raise RuntimeError("immutable R19 source hash drifted")
    if OUTPUT.exists():
        raise RuntimeError(f"append-only diagnostic exists: {OUTPUT}")
    OUTPUT.mkdir(parents=True)
    bpy.ops.wm.open_mainfile(filepath=str(base.SOURCE), load_ui=False)
    body = bpy.data.objects.get(base.BODY_NAME)
    if body is None:
        raise RuntimeError("exact R19 primary surface is absent")
    mesh = body.data
    mesh.update()
    vertex_neighbors, vertex_faces, edge_faces = adjacency(mesh)
    patch_faces = {
        int(face.index)
        for face in mesh.polygons
        if int(face.material_index) == base.PATCH_MATERIAL_INDEX
    }
    patch_vertices = {
        int(vertex)
        for face in patch_faces
        for vertex in mesh.polygons[face].vertices
    }
    seam_edges = {
        edge
        for edge, faces in edge_faces.items()
        if any(face in patch_faces for face in faces)
        and any(face not in patch_faces for face in faces)
    }
    cycle = ordered_cycle(seam_edges)
    seam = set(cycle)
    distances = {vertex: 0 for vertex in seam}
    queue = deque(sorted(seam))
    while queue:
        current = queue.popleft()
        for neighbor in vertex_neighbors[current]:
            if neighbor not in patch_vertices or neighbor in distances:
                continue
            distances[neighbor] = distances[current] + 1
            queue.append(neighbor)
    records = []
    normal_matrix = body.matrix_world.to_3x3()
    for vertex in sorted(patch_vertices):
        world = body.matrix_world @ mesh.vertices[vertex].co
        normal = (normal_matrix @ mesh.vertices[vertex].normal).normalized()
        u, v, w = base.local_chart(world)
        records.append(
            {
                "vertex": vertex,
                "seam": vertex in seam,
                "graph_distance_from_seam": distances.get(vertex),
                "world": [float(value) for value in world],
                "chart": {"u": u, "v": v, "w_m": w},
                "normal_world": [float(value) for value in normal],
                "normal_dot_fixed_outward": float(normal.dot(base.OUTWARD)),
            }
        )
    seam_uv = [(row["chart"]["u"], row["chart"]["v"]) for row in records if row["seam"]]
    polygon_area = 0.0
    cycle_rows = {row["vertex"]: row for row in records}
    for index, vertex in enumerate(cycle):
        following = cycle[(index + 1) % len(cycle)]
        a = cycle_rows[vertex]["chart"]
        b = cycle_rows[following]["chart"]
        polygon_area += a["u"] * b["v"] - b["u"] * a["v"]
    report = {
        "schema": "kira.avatar.r24_patch_chart_diagnostic.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "READ_ONLY_NO_BLEND_SAVE_NO_CANDIDATE",
        "source": base.SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256_before": base.SOURCE_SHA256,
        "body": base.BODY_NAME,
        "patch_material_index": base.PATCH_MATERIAL_INDEX,
        "patch_face_count": len(patch_faces),
        "patch_vertex_count": len(patch_vertices),
        "seam_edge_count": len(seam_edges),
        "seam_vertex_count": len(seam),
        "ordered_seam_cycle": cycle,
        "ordered_seam_cycle_sha256": hashlib.sha256(
            json.dumps(cycle, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "chart_basis": {
            "origin": list(base.ORIGIN),
            "lateral": list(base.LATERAL),
            "longitudinal": list(base.LONGITUDINAL),
            "fixed_outward": list(base.OUTWARD),
            "half_width_m": base.HALF_WIDTH,
            "half_length_m": base.HALF_LENGTH,
        },
        "chart_stats": {
            axis: stats([row["chart"][axis] for row in records])
            for axis in ("u", "v", "w_m")
        },
        "seam_chart_stats": {
            axis: stats([row["chart"][axis] for row in records if row["seam"]])
            for axis in ("u", "v", "w_m")
        },
        "normal_dot_fixed_outward_stats": stats(
            [row["normal_dot_fixed_outward"] for row in records]
        ),
        "normal_dot_fixed_outward_negative_count": sum(
            row["normal_dot_fixed_outward"] < 0.0 for row in records
        ),
        "seam_uv_signed_area": polygon_area * 0.5,
        "seam_uv_absolute_area": abs(polygon_area) * 0.5,
        "seam_uv_unique_count": len(set(seam_uv)),
        "vertex_records": records,
        "operations": {
            "blend_saved": False,
            "mesh_mutated": False,
            "runtime_or_person_state_changed": False,
        },
    }
    path = OUTPUT / "PATCH_CHART_DIAGNOSTIC.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if sha256(base.SOURCE) != base.SOURCE_SHA256:
        raise RuntimeError("immutable R19 source changed during read-only diagnostic")
    print(json.dumps({"ok": True, "report": str(path), "sha256": sha256(path)}, indent=2))


if __name__ == "__main__":
    main()
