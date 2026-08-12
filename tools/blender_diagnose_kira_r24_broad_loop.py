#!/usr/bin/env python3
"""Read-only ordered-loop audit for the R24 eight-ring broad pelvic disk."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_simulate_kira_r24_broad_inplace_surface as base  # noqa: E402
from tools import blender_simulate_kira_r24_cross_boundary_fairing as fair  # noqa: E402


OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_broad_loop_diagnostic/attempt_02"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ordered_cycle(edges: set[tuple[int, int]]) -> list[int]:
    neighbors: defaultdict[int, list[int]] = defaultdict(list)
    for first, second in edges:
        neighbors[first].append(second)
        neighbors[second].append(first)
    if not neighbors or any(len(values) != 2 for values in neighbors.values()):
        raise RuntimeError("broad boundary is not one degree-two cycle")
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
            raise RuntimeError("broad boundary repeats before closure")
        cycle.append(following)
        previous, current = current, following
    if len(cycle) != len(neighbors):
        raise RuntimeError("broad boundary has multiple cycles")
    return cycle


def rotate(values: list[int], offset: int) -> list[int]:
    index = int(offset) % len(values)
    return values[index:] + values[:index]


def expanded_faces_from_patch(
    mesh: bpy.types.Mesh, patch_faces: set[int], rings: int
) -> tuple[set[int], dict[int, int]]:
    _vertex_neighbors, _edge_faces, face_neighbors, _vertex_faces = fair.mesh_adjacency(mesh)
    distance = {int(face): 0 for face in patch_faces}
    queue = deque(sorted(patch_faces))
    while queue:
        current = queue.popleft()
        if distance[current] >= rings:
            continue
        for neighbor in face_neighbors[current]:
            if neighbor in distance:
                continue
            distance[neighbor] = distance[current] + 1
            queue.append(neighbor)
    return set(distance), distance


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
    _neighbors, edge_faces, _face_neighbors, _vertex_faces = fair.mesh_adjacency(mesh)
    old_patch = {
        int(face.index)
        for face in mesh.polygons
        if int(face.material_index) == base.PATCH_MATERIAL_INDEX
    }
    broad_faces, distance = expanded_faces_from_patch(mesh, old_patch, 8)
    broad_edges = {
        edge
        for edge, faces in edge_faces.items()
        if any(face in broad_faces for face in faces)
        and (len(faces) == 1 or any(face not in broad_faces for face in faces))
    }
    cycle = ordered_cycle(broad_edges)
    normal_matrix = body.matrix_world.to_3x3()
    records = []
    for order, vertex_index in enumerate(cycle):
        vertex = mesh.vertices[vertex_index]
        world = body.matrix_world @ vertex.co
        normal = (normal_matrix @ vertex.normal).normalized()
        u, v, w = base.local_chart(world)
        records.append(
            {
                "order": order,
                "vertex": int(vertex_index),
                "world": [float(value) for value in world],
                "chart": {"u": u, "v": v, "w_m": w},
                "normal_world": [float(value) for value in normal],
            }
        )
    extrema = {
        "left": min(records, key=lambda row: (row["chart"]["u"], row["order"])),
        "right": max(records, key=lambda row: (row["chart"]["u"], -row["order"])),
        "posterior": min(records, key=lambda row: (row["chart"]["v"], row["order"])),
        "anterior": max(records, key=lambda row: (row["chart"]["v"], -row["order"])),
    }
    # A 28 x 25 rectangular perimeter has exactly 102 vertices. Enumerate each
    # cyclic start and direction so later authoring can choose by geometric
    # corner score rather than silently assuming an orientation.
    partitions = []
    segment_lengths = [27, 24, 27, 24]
    for direction in (1, -1):
        directed = cycle if direction == 1 else list(reversed(cycle))
        for start in range(len(directed)):
            ordered = rotate(directed, start)
            corner_offsets = [0]
            for length in segment_lengths[:-1]:
                corner_offsets.append(corner_offsets[-1] + length)
            corners = [ordered[offset] for offset in corner_offsets]
            rows = {row["vertex"]: row for row in records}
            charts = [rows[index]["chart"] for index in corners]
            # Desired perimeter order is anterior-left, anterior-right,
            # posterior-right, posterior-left. Lower score is better.
            desired = [(-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)]
            u_extent = max(abs(row["chart"]["u"]) for row in records) or 1.0
            v_center = sum(row["chart"]["v"] for row in records) / len(records)
            v_extent = max(abs(row["chart"]["v"] - v_center) for row in records) or 1.0
            score = sum(
                (chart["u"] / u_extent - target_u) ** 2
                + ((chart["v"] - v_center) / v_extent - target_v) ** 2
                for chart, (target_u, target_v) in zip(charts, desired)
            )
            partitions.append(
                {
                    "direction": direction,
                    "start_in_directed_cycle": start,
                    "score": score,
                    "corner_vertices": corners,
                    "corner_charts": charts,
                    "ordered_cycle": ordered,
                }
            )
    partitions.sort(key=lambda row: (row["score"], -row["direction"], row["start_in_directed_cycle"]))
    best = partitions[0]
    report = {
        "schema": "kira.avatar.r24_broad_loop_diagnostic.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "READ_ONLY_NO_BLEND_SAVE_NO_CANDIDATE",
        "source": base.SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": base.SOURCE_SHA256,
        "body": base.BODY_NAME,
        "old_patch_face_count": len(old_patch),
        "broad_face_count": len(broad_faces),
        "broad_vertex_count": len(
            {int(vertex) for face in broad_faces for vertex in mesh.polygons[face].vertices}
        ),
        "broad_boundary_edge_count": len(broad_edges),
        "broad_boundary_vertex_count": len(cycle),
        "face_ring_histogram": {
            str(ring): sum(value == ring for value in distance.values())
            for ring in range(9)
        },
        "ordered_boundary": records,
        "ordered_boundary_vertex_sha256": hashlib.sha256(
            json.dumps(cycle, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "chart_extrema_records": extrema,
        "rectangular_28_by_25_perimeter": {
            "vertex_count": 102,
            "segment_edge_lengths": segment_lengths,
            "partition_count_evaluated": len(partitions),
            "best_partition": best,
            "next_four_scores": [row["score"] for row in partitions[1:5]],
        },
        "operations": {
            "blend_saved": False,
            "mesh_mutated": False,
            "runtime_or_person_state_changed": False,
        },
    }
    path = OUTPUT / "BROAD_LOOP_DIAGNOSTIC.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if sha256(base.SOURCE) != base.SOURCE_SHA256:
        raise RuntimeError("immutable R19 source changed during read-only diagnostic")
    print(json.dumps({"ok": True, "report": str(path), "sha256": sha256(path)}, indent=2))


if __name__ == "__main__":
    main()
