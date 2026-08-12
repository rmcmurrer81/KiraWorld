"""Read-only probe of broader R24 pubic-to-root reconstruction windows.

Each trial reopens R24, deletes only owner-surface faces (never authored
V23_Surface_Class 1/2 branch faces), and reports every newly exposed boundary
component. No Blender file is saved.
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
    "anatomy_reference_audit/BROAD_PUBIC_CUT_WINDOW_PROBE.json"
)

WINDOWS = [
    {
        "label": "w1",
        "half_x": 0.024,
        "min_y": -0.170,
        "max_y": -0.020,
        "min_z": 0.774,
        "max_z": 0.826,
    },
    {
        "label": "w2",
        "half_x": 0.032,
        "min_y": -0.170,
        "max_y": -0.020,
        "min_z": 0.770,
        "max_z": 0.827,
    },
    {
        "label": "w3",
        "half_x": 0.040,
        "min_y": -0.170,
        "max_y": -0.020,
        "min_z": 0.765,
        "max_z": 0.828,
    },
    {
        "label": "w4",
        "half_x": 0.050,
        "min_y": -0.175,
        "max_y": -0.018,
        "min_z": 0.760,
        "max_z": 0.830,
    },
    {
        "label": "w5",
        "half_x": 0.050,
        "min_y": -0.175,
        "max_y": -0.018,
        "min_z": 0.695,
        "max_z": 0.830,
    },
    {
        "label": "w6",
        "half_x": 0.060,
        "min_y": -0.180,
        "max_y": -0.015,
        "min_z": 0.685,
        "max_z": 0.835,
    },
    {
        "label": "w7_front_depth",
        "half_x": 0.050,
        "min_y": -0.175,
        "max_y": -0.050,
        "min_z": 0.695,
        "max_z": 0.830,
    },
    {
        "label": "w8_front_depth",
        "half_x": 0.050,
        "min_y": -0.175,
        "max_y": -0.060,
        "min_z": 0.695,
        "max_z": 0.830,
    },
    {
        "label": "w9_front_depth",
        "half_x": 0.050,
        "min_y": -0.175,
        "max_y": -0.070,
        "min_z": 0.695,
        "max_z": 0.830,
    },
    {
        "label": "w10_front_depth",
        "half_x": 0.050,
        "min_y": -0.175,
        "max_y": -0.080,
        "min_z": 0.695,
        "max_z": 0.830,
    },
]


def coordinate_key(vertex: bmesh.types.BMVert):
    return tuple(round(float(value), 7) for value in vertex.co)


def edge_key(edge: bmesh.types.BMEdge):
    return tuple(sorted(coordinate_key(vertex) for vertex in edge.verts))


def components(edges: list[bmesh.types.BMEdge]):
    by_vertex: dict[bmesh.types.BMVert, list[bmesh.types.BMEdge]] = {}
    for edge in edges:
        for vertex in edge.verts:
            by_vertex.setdefault(vertex, []).append(edge)
    unseen = set(edges)
    result = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        component = [seed]
        while stack:
            current = stack.pop()
            for vertex in current.verts:
                for neighbor in by_vertex.get(vertex, []):
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        component.append(neighbor)
                        stack.append(neighbor)
        result.append(component)
    return result


def run(window: dict[str, float | str]) -> dict[str, object]:
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
    baseline_boundary = {
        edge_key(edge) for edge in bm.edges if len(edge.link_faces) == 1
    }
    cut_faces = []
    rejected_authored = 0
    for face in bm.faces:
        center = face.calc_center_median()
        if not (
            abs(center.x) <= float(window["half_x"])
            and float(window["min_y"]) <= center.y <= float(window["max_y"])
            and float(window["min_z"]) <= center.z <= float(window["max_z"])
        ):
            continue
        if (
            surface_class is not None
            and any(vertex[surface_class] in {1, 2} for vertex in face.verts)
        ):
            rejected_authored += 1
            continue
        cut_faces.append(face)
    bmesh.ops.delete(bm, geom=cut_faces, context="FACES")
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    new_edges = [
        edge
        for edge in bm.edges
        if len(edge.link_faces) == 1 and edge_key(edge) not in baseline_boundary
    ]
    component_reports = []
    for component in components(new_edges):
        vertices = {vertex for edge in component for vertex in edge.verts}
        degree: dict[bmesh.types.BMVert, int] = {}
        for edge in component:
            for vertex in edge.verts:
                degree[vertex] = degree.get(vertex, 0) + 1
        component_reports.append(
            {
                "edge_count": len(component),
                "vertex_count": len(vertices),
                "degree_set": sorted(set(degree.values())),
                "simple_cycle": set(degree.values()) == {2},
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
                "surface_class_counts": (
                    {
                        str(value): sum(
                            int(vertex[surface_class]) == value
                            for vertex in vertices
                        )
                        for value in (0, 1, 2)
                    }
                    if surface_class is not None
                    else {}
                ),
            }
        )
    bm.free()
    return {
        "window": window,
        "cut_face_count": len(cut_faces),
        "authored_faces_excluded": rejected_authored,
        "new_boundary_edge_count": len(new_edges),
        "component_count": len(component_reports),
        "components": sorted(
            component_reports,
            key=lambda item: (
                item["center"]["z"],
                -item["center"]["y"],
            ),
            reverse=True,
        ),
    }


report = {
    "source": str(SOURCE),
    "trials": [run(window) for window in WINDOWS],
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
