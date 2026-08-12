"""Dump the two measured R24 superior-pubic cut cycles for repair design.

This is diagnostic only.  It opens the preserved R24 engineering source,
removes the same measured 408-face window, orders both resulting local cycles,
and writes coordinates plus adjacent-face normals.  It does not save a blend.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import bmesh
import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_preserved_surface_trial_r24_raised_branches/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "PRESERVED_SURFACE_TRIAL_R24_RAISED_BRANCHES.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_r25g_coons_bridge_trial"
)
OUT.mkdir(parents=True, exist_ok=True)

WINDOW = {
    "half_x": 0.018,
    "min_y": -0.165,
    "max_y": -0.045,
    "min_z": 0.809,
    "max_z": 0.824,
}


def coordinate_key(vertex: bmesh.types.BMVert) -> tuple[float, float, float]:
    return tuple(round(value, 7) for value in vertex.co)


def edge_key(edge: bmesh.types.BMEdge):
    return tuple(sorted(coordinate_key(vertex) for vertex in edge.verts))


def components(edges):
    by_vertex = {}
    for edge in edges:
        for vertex in edge.verts:
            by_vertex.setdefault(vertex, []).append(edge)
    unseen = set(edges)
    result = []
    while unseen:
        seed = unseen.pop()
        current_component = [seed]
        stack = [seed]
        while stack:
            current = stack.pop()
            for vertex in current.verts:
                for neighbor in by_vertex[vertex]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        current_component.append(neighbor)
                        stack.append(neighbor)
        result.append(current_component)
    return result


def ordered_cycle_vertices(cycle):
    adjacency = {}
    for edge in cycle:
        a, b = edge.verts
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    if any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise RuntimeError("non-simple cycle")
    start = min(adjacency, key=lambda vertex: (vertex.co.x, vertex.co.z, vertex.co.y))
    result = [start]
    previous = None
    current = start
    while True:
        candidates = [v for v in adjacency[current] if v is not previous]
        if previous is None:
            next_vertex = max(candidates, key=lambda vertex: vertex.co.y)
        else:
            next_vertex = candidates[0]
        if next_vertex is start:
            break
        if next_vertex in result:
            raise RuntimeError("repeated vertex")
        result.append(next_vertex)
        previous, current = current, next_vertex
    return result


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = max(
    (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
baseline_boundaries = {
    edge_key(edge) for edge in bm.edges if len(edge.link_faces) == 1
}
cut_faces = [
    face
    for face in bm.faces
    if (
        abs(face.calc_center_median().x) <= WINDOW["half_x"]
        and WINDOW["min_y"] <= face.calc_center_median().y <= WINDOW["max_y"]
        and WINDOW["min_z"] <= face.calc_center_median().z <= WINDOW["max_z"]
    )
]
if len(cut_faces) != 408:
    raise RuntimeError(f"measured cut changed: {len(cut_faces)}")
bmesh.ops.delete(bm, geom=cut_faces, context="FACES")
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
new_boundary_edges = [
    edge
    for edge in bm.edges
    if (
        len(edge.link_faces) == 1
        and edge_key(edge) not in baseline_boundaries
        and all(
            abs(vertex.co.x) <= WINDOW["half_x"] + 0.012
            and WINDOW["min_y"] - 0.025
            <= vertex.co.y
            <= WINDOW["max_y"] + 0.025
            and WINDOW["min_z"] - 0.012
            <= vertex.co.z
            <= WINDOW["max_z"] + 0.012
            for vertex in edge.verts
        )
    )
]
cycles = components(new_boundary_edges)
cycles.sort(key=lambda cycle: min(v.co.y for e in cycle for v in e.verts))
payload = {"source": str(SOURCE), "window": WINDOW, "cut_faces": len(cut_faces), "cycles": []}
for cycle_index, cycle in enumerate(cycles):
    ordered = ordered_cycle_vertices(cycle)
    rows = []
    for index, vertex in enumerate(ordered):
        linked = [face.normal.copy() for face in vertex.link_faces]
        if linked:
            normal = sum(linked[1:], linked[0].copy()).normalized()
        else:
            normal = vertex.normal.copy()
        rows.append(
            {
                "index": index,
                "vertex_index": vertex.index,
                "x": float(vertex.co.x),
                "y": float(vertex.co.y),
                "z": float(vertex.co.z),
                "nx": float(normal.x),
                "ny": float(normal.y),
                "nz": float(normal.z),
            }
        )
    label = "outer" if cycle_index == 0 else "inner"
    payload["cycles"].append({"label": label, "edge_count": len(cycle), "rows": rows})
    with (OUT / f"{label}_cycle_coordinates.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

(OUT / "BRIDGE_CYCLE_COORDINATES.json").write_text(
    json.dumps(payload, indent=2) + "\n", encoding="utf-8"
)
bm.free()
print(OUT / "BRIDGE_CYCLE_COORDINATES.json")
