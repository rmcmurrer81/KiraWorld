"""Probe whether V1's mirrored pubic openings become one clean loop when welded.

This is read-only engineering evidence: it opens V1, freezes only the
armature/corrective modifiers, removes the two mirrored 11-face root regions,
welds coincident centerline vertices in the bounded pelvis region, and reports
the resulting boundary components.  It does not save a .blend file.
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
    "biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/V1_BILATERAL_ROOT_WELD_PROBE.json"
)
BODY_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"


def is_root_face(center) -> bool:
    return (
        abs(center.x) < 0.035
        and center.y < -0.02
        and 0.70 < center.z < 0.80
    )


def components(edges):
    adjacency = {}
    for edge in edges:
        for vertex in edge.verts:
            adjacency.setdefault(vertex, set()).update(
                other for other in edge.verts if other is not vertex
            )
    unseen = set(adjacency)
    result = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        members = {seed}
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    members.add(neighbor)
                    stack.append(neighbor)
        result.append(members)
    return result


def ordered_cycle(edges):
    adjacency = {}
    for edge in edges:
        a, b = edge.verts
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    if {len(neighbors) for neighbors in adjacency.values()} != {2}:
        raise RuntimeError("not a simple cycle")
    start = min(adjacency, key=lambda vertex: (vertex.co.z, abs(vertex.co.x)))
    candidates = adjacency[start]
    current = min(candidates, key=lambda vertex: vertex.co.y)
    order = [start, current]
    previous = start
    while True:
        following = next(
            vertex for vertex in adjacency[current] if vertex is not previous
        )
        if following is start:
            break
        order.append(following)
        previous, current = current, following
    return order


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get(BODY_NAME)
if body is None:
    raise RuntimeError("V1 body missing")

for modifier in list(body.modifiers):
    if modifier.type in {"ARMATURE", "CORRECTIVE_SMOOTH"}:
        bpy.context.view_layer.objects.active = body
        body.select_set(True)
        bpy.ops.object.modifier_apply(modifier=modifier.name)

bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()

root_faces = [face for face in bm.faces if is_root_face(face.calc_center_median())]
root_vertices = {vertex for face in root_faces for vertex in face.verts}
before_bounds = {
    axis: [min(getattr(v.co, axis) for v in root_vertices), max(getattr(v.co, axis) for v in root_vertices)]
    for axis in ("x", "y", "z")
}
bmesh.ops.delete(bm, geom=root_faces, context="FACES")

pre_weld_roi_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) < 0.10
        and -0.22 < vertex.co.y < 0.13
        and 0.62 < vertex.co.z < 0.88
        for vertex in edge.verts
    )
]
pre_weld_components = components(pre_weld_roi_edges)
pre_weld_component_coordinates = [
    sorted(
        [[round(value, 6) for value in vertex.co] for vertex in component],
        key=lambda co: (co[2], co[0], co[1]),
    )
    for component in pre_weld_components
]
pre_weld_ordered_cycles = []
for component in pre_weld_components:
    component_edges = [
        edge
        for edge in pre_weld_roi_edges
        if all(vertex in component for vertex in edge.verts)
    ]
    cycle = ordered_cycle(component_edges)
    pre_weld_ordered_cycles.append(
        [[round(value, 6) for value in vertex.co] for vertex in cycle]
    )

candidate_vertices = [
    vertex
    for vertex in bm.verts
    if abs(vertex.co.x) < 0.004
    and -0.20 < vertex.co.y < 0.06
    and 0.66 < vertex.co.z < 0.83
]
candidate_count_before = len(candidate_vertices)
vertex_count_before_weld = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=candidate_vertices, dist=0.0035)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
vertex_count_after_weld = len(bm.verts)

roi_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) < 0.10
        and -0.22 < vertex.co.y < 0.13
        and 0.62 < vertex.co.z < 0.88
        for vertex in edge.verts
    )
]
loop_components = components(roi_edges)
report = {
    "source": str(SOURCE),
    "root_faces_removed": len(root_faces),
    "root_vertices_before_delete": len(root_vertices),
    "root_bounds": before_bounds,
    "centerline_candidates": candidate_count_before,
    "vertices_removed_by_weld": vertex_count_before_weld - vertex_count_after_weld,
    "pre_weld_components": pre_weld_component_coordinates,
    "pre_weld_ordered_cycles": pre_weld_ordered_cycles,
    "roi_boundary_edge_count": len(roi_edges),
    "roi_boundary_component_vertex_counts": sorted(
        len(component) for component in loop_components
    ),
    "components": [
        {
            "vertex_count": len(component),
            "degree_set": sorted(
                {
                    sum(vertex in edge.verts for edge in roi_edges)
                    for vertex in component
                }
            ),
            "bounds": {
                axis: [
                    min(getattr(vertex.co, axis) for vertex in component),
                    max(getattr(vertex.co, axis) for vertex in component),
                ]
                for axis in ("x", "y", "z")
            },
            "vertices": sorted(
                [
                    {
                        "index": vertex.index,
                        "co": [round(value, 6) for value in vertex.co],
                        "degree": sum(vertex in edge.verts for edge in roi_edges),
                    }
                    for vertex in component
                ],
                key=lambda item: (item["co"][2], item["co"][0], item["co"][1]),
            ),
        }
        for component in loop_components
    ],
}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
bm.free()
