"""Read-only probe for the authored R24 anatomy branch attachment cycles.

This opens the preserved-surface R24 engineering trial, removes only vertices
tagged as authored shaft/scrotal geometry in an in-memory BMesh, and reports
the exposed attachment cycles.  It never writes a Blender file.
"""

from __future__ import annotations

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


def edge_components(edges: list[bmesh.types.BMEdge]):
    vertex_edges: dict[bmesh.types.BMVert, list[bmesh.types.BMEdge]] = {}
    for edge in edges:
        for vertex in edge.verts:
            vertex_edges.setdefault(vertex, []).append(edge)
    unseen = set(edges)
    components = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        component = [seed]
        while stack:
            current = stack.pop()
            for vertex in current.verts:
                for neighbor in vertex_edges.get(vertex, []):
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        component.append(neighbor)
                        stack.append(neighbor)
        components.append(component)
    return components


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = next(
    obj
    for obj in bpy.context.scene.objects
    if obj.type == "MESH" and "BIOLOGICAL_ROBERT_STATIC_LIKENESS" in obj.name
)
bm = bmesh.new()
bm.from_mesh(body.data)
surface_class = bm.verts.layers.int.get("V23_Surface_Class")
if surface_class is None:
    raise RuntimeError("R24 is missing V23_Surface_Class")

authored = [vertex for vertex in bm.verts if vertex[surface_class] in {1, 2}]
authored_counts = {
    str(value): sum(vertex[surface_class] == value for vertex in authored)
    for value in (1, 2)
}
bmesh.ops.delete(bm, geom=authored, context="VERTS")
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

candidate_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) < 0.055
        and -0.180 < vertex.co.y < -0.005
        and 0.640 < vertex.co.z < 0.825
        for vertex in edge.verts
    )
]
components = []
for component in edge_components(candidate_edges):
    vertices = {vertex for edge in component for vertex in edge.verts}
    degree: dict[bmesh.types.BMVert, int] = {}
    for edge in component:
        for vertex in edge.verts:
            degree[vertex] = degree.get(vertex, 0) + 1
    components.append(
        {
            "edge_count": len(component),
            "vertex_count": len(vertices),
            "degree_set": sorted(set(degree.values())),
            "bounds": {
                "min_x": min(vertex.co.x for vertex in vertices),
                "max_x": max(vertex.co.x for vertex in vertices),
                "min_y": min(vertex.co.y for vertex in vertices),
                "max_y": max(vertex.co.y for vertex in vertices),
                "min_z": min(vertex.co.z for vertex in vertices),
                "max_z": max(vertex.co.z for vertex in vertices),
            },
            "center": {
                axis: sum(getattr(vertex.co, axis) for vertex in vertices)
                / len(vertices)
                for axis in ("x", "y", "z")
            },
        }
    )

report = {
    "source": str(SOURCE),
    "authored_vertex_count": len(authored),
    "authored_counts": authored_counts,
    "candidate_boundary_edge_count": len(candidate_edges),
    "components": sorted(
        components,
        key=lambda item: item["center"]["z"],
        reverse=True,
    ),
}
print(json.dumps(report, indent=2))
bm.free()
