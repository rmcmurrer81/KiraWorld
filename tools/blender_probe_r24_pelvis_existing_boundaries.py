"""Read-only audit of pre-existing R24 pelvis boundary components.

This distinguishes the visible superior tunnel from cut-window artifacts.  It
never changes or saves the source blend.
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
OUTPUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/R24_PELVIS_EXISTING_BOUNDARY_AUDIT.json"
)


def components(edges):
    by_vertex = {}
    for edge in edges:
        for vertex in edge.verts:
            by_vertex.setdefault(vertex, []).append(edge)
    unseen = set(edges)
    result = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        current = [seed]
        while stack:
            edge = stack.pop()
            for vertex in edge.verts:
                for neighbor in by_vertex[vertex]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        current.append(neighbor)
                        stack.append(neighbor)
        result.append(current)
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
surface_class = bm.verts.layers.int.get("V23_Surface_Class")
zone = bm.verts.layers.int.get("Adult_Anatomy_Zone")
boundary = [edge for edge in bm.edges if len(edge.link_faces) == 1]
reports = []
for component in components(boundary):
    vertices = {vertex for edge in component for vertex in edge.verts}
    bounds = {
        axis: [
            min(getattr(vertex.co, axis) for vertex in vertices),
            max(getattr(vertex.co, axis) for vertex in vertices),
        ]
        for axis in ("x", "y", "z")
    }
    if (
        bounds["x"][1] < -0.10
        or bounds["x"][0] > 0.10
        or bounds["y"][1] < -0.22
        or bounds["y"][0] > 0.08
        or bounds["z"][1] < 0.62
        or bounds["z"][0] > 0.90
    ):
        continue
    degree = {}
    for edge in component:
        for vertex in edge.verts:
            degree[vertex] = degree.get(vertex, 0) + 1
    reports.append(
        {
            "edge_count": len(component),
            "vertex_count": len(vertices),
            "degree_set": sorted(set(degree.values())),
            "simple_cycle": set(degree.values()) == {2},
            "bounds": bounds,
            "center": {
                axis: sum(getattr(vertex.co, axis) for vertex in vertices)
                / len(vertices)
                for axis in ("x", "y", "z")
            },
            "surface_class_counts": (
                {
                    str(value): sum(int(vertex[surface_class]) == value for vertex in vertices)
                    for value in (0, 1, 2)
                }
                if surface_class is not None
                else {}
            ),
            "zone_counts": (
                {
                    str(value): sum(int(vertex[zone]) == value for vertex in vertices)
                    for value in sorted({int(vertex[zone]) for vertex in vertices})
                }
                if zone is not None
                else {}
            ),
        }
    )
bm.free()
report = {
    "schema": "kira.avatar.v23.r24.pelvis_existing_boundary_audit.v1",
    "source": str(SOURCE),
    "total_boundary_edges": len(boundary),
    "pelvis_components": sorted(reports, key=lambda item: item["edge_count"]),
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
