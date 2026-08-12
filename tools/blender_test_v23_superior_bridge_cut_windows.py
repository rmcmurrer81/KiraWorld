"""Test bounded face-cut windows around the V23 superior pubic gap.

The script is read-only and never saves a candidate.  It reports which local
coordinate window produces a clean, simple boundary that a hand-authored
replacement surface can stitch without Boolean or global remesh operations.

Usage:
    blender --background --python \
      tools/blender_test_v23_superior_bridge_cut_windows.py -- \
      candidate.blend output.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bmesh
import bpy


if "--" not in sys.argv:
    raise SystemExit("expected -- candidate.blend output.json")
arguments = sys.argv[sys.argv.index("--") + 1 :]
if len(arguments) not in {2, 3}:
    raise SystemExit(
        "expected candidate.blend output.json [prepare-v1]"
    )
source = Path(arguments[0]).resolve()
output = Path(arguments[1]).resolve()
prepare_v1 = len(arguments) == 3 and arguments[2] == "prepare-v1"
output.parent.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(source))
body = max(
    (obj for obj in bpy.data.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
if prepare_v1:
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    for modifier in list(body.modifiers):
        if modifier.type in {"ARMATURE", "CORRECTIVE_SMOOTH"}:
            bpy.ops.object.modifier_apply(modifier=modifier.name)
base = bmesh.new()
base.from_mesh(body.data)
base.verts.ensure_lookup_table()
base.edges.ensure_lookup_table()
base.faces.ensure_lookup_table()
if prepare_v1:
    true_medial_pairs = (
        (10342, 5694),
        (10620, 5972),
        (10626, 5978),
        (10622, 5974),
        (10739, 6091),
        (10763, 6115),
        (10748, 6100),
        (10724, 6076),
    )
    medial_vertices = []
    for left_index, right_index in true_medial_pairs:
        left = base.verts[left_index]
        right = base.verts[right_index]
        midpoint = (left.co + right.co) * 0.5
        midpoint.x = 0.0
        if midpoint.y > -0.050:
            midpoint.y = max(-0.054, midpoint.y - 0.004)
        left.co = midpoint
        right.co = midpoint
        medial_vertices.extend((left, right))
    bmesh.ops.remove_doubles(
        base,
        verts=medial_vertices,
        dist=0.00005,
    )
    bmesh.ops.dissolve_degenerate(
        base,
        dist=0.00001,
        edges=base.edges,
    )
    bmesh.ops.recalc_face_normals(base, faces=base.faces)
    base.verts.index_update()
    base.edges.index_update()
    base.faces.index_update()
    base.verts.ensure_lookup_table()
    base.edges.ensure_lookup_table()
    base.faces.ensure_lookup_table()


def coordinate_key(vertex: bmesh.types.BMVert) -> tuple[float, float, float]:
    return tuple(round(value, 7) for value in vertex.co)


def edge_key(edge: bmesh.types.BMEdge) -> tuple[tuple[float, ...], ...]:
    return tuple(sorted(coordinate_key(vertex) for vertex in edge.verts))


base_boundary_keys = {
    edge_key(edge) for edge in base.edges if len(edge.link_faces) == 1
}


def components(
    edges: list[bmesh.types.BMEdge],
) -> list[list[bmesh.types.BMEdge]]:
    by_vertex: dict[bmesh.types.BMVert, list[bmesh.types.BMEdge]] = {}
    for edge in edges:
        for vertex in edge.verts:
            by_vertex.setdefault(vertex, []).append(edge)
    unseen = set(edges)
    results = []
    while unseen:
        seed = unseen.pop()
        result = [seed]
        stack = [seed]
        while stack:
            current = stack.pop()
            for vertex in current.verts:
                for neighbor in by_vertex[vertex]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        result.append(neighbor)
                        stack.append(neighbor)
        results.append(result)
    return results


windows = []
for half_x in (0.018, 0.022, 0.026, 0.030, 0.034):
    for min_z in (0.805, 0.807, 0.809):
        for max_z in (0.822, 0.824, 0.826):
            windows.append(
                {
                    "half_x": half_x,
                    "min_z": min_z,
                    "max_z": max_z,
                    "min_y": -0.165,
                    "max_y": -0.045,
                }
            )

reports = []
for window in windows:
    bm = base.copy()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    cut_faces = [
        face
        for face in bm.faces
        if (
            abs(face.calc_center_median().x) <= window["half_x"]
            and window["min_y"]
            <= face.calc_center_median().y
            <= window["max_y"]
            and window["min_z"]
            <= face.calc_center_median().z
            <= window["max_z"]
        )
    ]
    cut_face_indices = sorted(face.index for face in cut_faces)
    bmesh.ops.delete(bm, geom=cut_faces, context="FACES")
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    new_edges = [
        edge
        for edge in bm.edges
        if (
            len(edge.link_faces) == 1
            and edge_key(edge) not in base_boundary_keys
            and all(
                abs(vertex.co.x) <= window["half_x"] + 0.012
                and window["min_y"] - 0.025
                <= vertex.co.y
                <= window["max_y"] + 0.025
                and window["min_z"] - 0.012
                <= vertex.co.z
                <= window["max_z"] + 0.012
                for vertex in edge.verts
            )
        )
    ]
    component_reports = []
    for component in components(new_edges):
        vertices = {
            vertex for edge in component for vertex in edge.verts
        }
        degree: dict[bmesh.types.BMVert, int] = {}
        for edge in component:
            for vertex in edge.verts:
                degree[vertex] = degree.get(vertex, 0) + 1
        component_reports.append(
            {
                "edge_count": len(component),
                "vertex_count": len(vertices),
                "degree_set": sorted(set(degree.values())),
                "closed_simple_cycle": set(degree.values()) == {2},
                "bounds": {
                    "min_x": min(vertex.co.x for vertex in vertices),
                    "max_x": max(vertex.co.x for vertex in vertices),
                    "min_y": min(vertex.co.y for vertex in vertices),
                    "max_y": max(vertex.co.y for vertex in vertices),
                    "min_z": min(vertex.co.z for vertex in vertices),
                    "max_z": max(vertex.co.z for vertex in vertices),
                },
                "vertex_indices": sorted(vertex.index for vertex in vertices),
                "vertices": [
                    {
                        "vertex_index": vertex.index,
                        "coordinate": [
                            round(value, 7) for value in vertex.co
                        ],
                        "boundary_degree": degree[vertex],
                    }
                    for vertex in sorted(
                        vertices,
                        key=lambda item: (
                            item.co.z,
                            item.co.x,
                            item.co.y,
                        ),
                    )
                ],
                "vertex_coordinates": [
                    [
                        round(value, 7)
                        for value in vertex.co
                    ]
                    for vertex in sorted(
                        vertices,
                        key=lambda item: (item.co.z, item.co.x, item.co.y),
                    )
                ],
            }
        )
    reports.append(
        {
            "window": window,
            "cut_face_count": len(cut_faces),
            "cut_face_indices": cut_face_indices,
            "new_boundary_edge_count": len(new_edges),
            "component_count": len(component_reports),
            "simple_cycle_count": sum(
                component["closed_simple_cycle"]
                for component in component_reports
            ),
            "components": component_reports,
        }
    )
    bm.free()

reports.sort(
    key=lambda item: (
        item["component_count"] != 1,
        item["simple_cycle_count"] != 1,
        item["cut_face_count"],
    )
)
result = {
    "schema": "kira.avatar.v23.superior_bridge_cut_window_trials.v1",
    "source_blend": str(source),
    "diagnostic_only": True,
    "candidate_saved_or_modified": False,
    "prepare_v1_applied": prepare_v1,
    "trial_count": len(reports),
    "trials": reports,
}
output.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(output)
print(
    json.dumps(
        [
            {
                "window": trial["window"],
                "cut_face_count": trial["cut_face_count"],
                "component_count": trial["component_count"],
                "simple_cycle_count": trial["simple_cycle_count"],
                "component_edge_counts": [
                    component["edge_count"]
                    for component in trial["components"]
                ],
            }
            for trial in reports[:10]
        ],
        indent=2,
    )
)
base.free()
