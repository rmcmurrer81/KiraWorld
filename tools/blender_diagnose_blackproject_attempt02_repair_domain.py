"""Read-only local-domain audit for a deterministic Attempt 15 repair.

This worker finds the exact 28-pair collision island in the preserved
BlackProject Attempt 02 and measures concentric face-ring replacement domains.
It does not change geometry, render, save, or activate anything.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.blender_exact_mesh_intersections import (  # noqa: E402
    exact_nonadjacent_intersection_report,
)


SOURCE = ROOT / (
    "RecoverySprint/continuation_20260802/r19_blackproject_patch_reconstruction/"
    "attempt_02/r19_patch_reconstruction_probe.blend"
)
SOURCE_SHA256 = (
    "47cbf26279bc3b75076caf43f96c1c3441dd86e48ad0c404f7a45504985add4d"
)
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "r24_blackproject_patch_reconstruction_diagnostic/attempt_02"
)
ADULT_MESH_NAME = "Ariel_Mesh_Genitalia_0"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def vector_record(value: Vector) -> list[float]:
    return [round(float(component), 12) for component in value]


def cycles_from_edges(edges: set[tuple[int, int]]) -> list[list[int]] | None:
    adjacency: dict[int, set[int]] = {}
    for first, second in edges:
        adjacency.setdefault(first, set()).add(second)
        adjacency.setdefault(second, set()).add(first)
    if any(len(neighbors) != 2 for neighbors in adjacency.values()):
        return None
    cycles: list[list[int]] = []
    unseen = set(adjacency)
    while unseen:
        start = min(unseen)
        cycle = [start]
        previous = None
        current = start
        while True:
            candidates = sorted(value for value in adjacency[current] if value != previous)
            next_value = candidates[0]
            if next_value == start:
                break
            if next_value in cycle:
                return None
            cycle.append(next_value)
            previous, current = current, next_value
        unseen.difference_update(cycle)
        cycles.append(cycle)
    return cycles


def vertex_distances(adjacency: dict[int, set[int]], seeds: set[int]) -> dict[int, int]:
    distances = {value: 0 for value in seeds}
    queue = deque(sorted(seeds))
    while queue:
        current = queue.popleft()
        for neighbor in adjacency[current]:
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
    return distances


def main() -> None:
    if not SOURCE.is_file() or sha256_file(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("preserved Attempt 02 hash mismatch")
    if OUTPUT.exists():
        raise RuntimeError("append-only repair-domain output already exists")

    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    obj = next(
        (
            value
            for value in bpy.data.objects
            if value.type == "MESH" and value.data.name == ADULT_MESH_NAME
        ),
        None,
    )
    if obj is None:
        raise RuntimeError("Attempt 02 adult patch absent")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.index_update()
    bm.faces.index_update()
    exact = exact_nonadjacent_intersection_report(bm, include_pair_details=True)
    genuine = [
        record
        for record in exact["pairs"]
        if record["genuine_positive_area_or_segment_penetration"]
    ]
    seed_faces = {
        int(value) for record in genuine for value in record["face_indices"]
    }
    face_adjacency: dict[int, set[int]] = {
        int(face.index): {
            int(other.index)
            for edge in face.edges
            for other in edge.link_faces
            if other != face
        }
        for face in bm.faces
    }
    vertex_adjacency: dict[int, set[int]] = {
        int(vertex.index): {
            int(edge.other_vert(vertex).index) for edge in vertex.link_edges
        }
        for vertex in bm.verts
    }
    global_boundary = {
        int(vertex.index)
        for edge in bm.edges
        if len(edge.link_faces) == 1
        for vertex in edge.verts
    }
    distance_to_global_boundary = vertex_distances(vertex_adjacency, global_boundary)

    domains = []
    selected = set(seed_faces)
    for expansion in range(0, 7):
        vertices = {
            int(vertex.index)
            for face_index in selected
            for vertex in bm.faces[face_index].verts
        }
        edges = {
            tuple(sorted((int(edge.verts[0].index), int(edge.verts[1].index))))
            for face_index in selected
            for edge in bm.faces[face_index].edges
        }
        edge_face_count: dict[tuple[int, int], int] = {edge: 0 for edge in edges}
        for face_index in selected:
            for edge in bm.faces[face_index].edges:
                key = tuple(
                    sorted((int(edge.verts[0].index), int(edge.verts[1].index)))
                )
                edge_face_count[key] += 1
        boundary_edges = {edge for edge, count in edge_face_count.items() if count == 1}
        cycles = cycles_from_edges(boundary_edges)
        selected_components = 0
        unseen = set(selected)
        while unseen:
            selected_components += 1
            queue = deque([min(unseen)])
            unseen.remove(queue[0])
            while queue:
                current = queue.popleft()
                for neighbor in face_adjacency[current].intersection(selected):
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        queue.append(neighbor)
        world = [obj.matrix_world @ bm.verts[index].co for index in sorted(vertices)]
        coordinates = np.array([tuple(value) for value in world], dtype=np.float64)
        centroid = coordinates.mean(axis=0)
        _, singular, vh = np.linalg.svd(coordinates - centroid, full_matrices=False)
        normal = vh[-1]
        deviations = np.abs((coordinates - centroid) @ normal)
        domain = {
            "face_ring_expansion": expansion,
            "face_count": len(selected),
            "vertex_count": len(vertices),
            "edge_count": len(edges),
            "euler_characteristic": len(vertices) - len(edges) + len(selected),
            "face_component_count": selected_components,
            "boundary_edge_count": len(boundary_edges),
            "boundary_cycle_count": None if cycles is None else len(cycles),
            "boundary_cycle_lengths": None
            if cycles is None
            else [len(cycle) for cycle in cycles],
            "is_one_topological_disk": bool(
                selected_components == 1
                and cycles is not None
                and len(cycles) == 1
                and len(vertices) - len(edges) + len(selected) == 1
            ),
            "touches_global_34_vertex_seam": bool(vertices.intersection(global_boundary)),
            "minimum_vertex_ring_distance_from_global_seam": min(
                distance_to_global_boundary[index] for index in vertices
            ),
            "maximum_vertex_ring_distance_from_global_seam": max(
                distance_to_global_boundary[index] for index in vertices
            ),
            "face_indices": sorted(selected),
            "vertex_indices": sorted(vertices),
            "boundary_edges": [list(edge) for edge in sorted(boundary_edges)],
            "boundary_cycle_vertex_indices": None if cycles is None else cycles,
            "best_fit_plane_world_m": {
                "centroid": [float(value) for value in centroid],
                "normal": [float(value) for value in normal],
                "singular_values": [float(value) for value in singular],
                "maximum_absolute_deviation_m": float(deviations.max()),
                "rms_absolute_deviation_m": float(
                    np.sqrt(np.mean(np.square(deviations)))
                ),
            },
        }
        domains.append(domain)
        selected.update(
            neighbor
            for face_index in list(selected)
            for neighbor in face_adjacency[face_index]
        )

    candidates = [
        row
        for row in domains
        if row["is_one_topological_disk"]
        and not row["touches_global_34_vertex_seam"]
        and row["minimum_vertex_ring_distance_from_global_seam"] >= 3
    ]
    selected_candidate = min(candidates, key=lambda row: row["face_count"], default=None)
    report = {
        "schema": "kira.avatar.r24.blackproject_attempt02_repair_domain.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_NO_RENDER_NO_SAVE",
        "input": {
            "path": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
            "sha256": SOURCE_SHA256,
        },
        "exact_collision": {
            "pair_count": len(genuine),
            "seed_face_count": len(seed_faces),
            "seed_face_indices": sorted(seed_faces),
        },
        "global_interface": {
            "boundary_vertex_count": len(global_boundary),
            "boundary_vertex_indices": sorted(global_boundary),
        },
        "domains": domains,
        "smallest_qualified_replacement_domain": selected_candidate,
        "truth": {
            "geometry_changed": False,
            "rendered": False,
            "blend_saved": False,
            "runtime_changed": False,
            "visual_approval_claimed": False,
        },
    }
    bm.free()
    OUTPUT.mkdir(parents=True)
    report_path = OUTPUT / "BLACKPROJECT_ATTEMPT02_REPAIR_DOMAIN.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if sha256_file(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("preserved Attempt 02 changed during read-only diagnostic")
    print(json.dumps({"report": str(report_path), "sha256": sha256_file(report_path)}))


if __name__ == "__main__":
    main()
