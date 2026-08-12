"""Measure the broader pubic-to-anatomy root transition on R25B.

This diagnostic is intentionally read-only.  It inventories the retained skin
surface and authored anatomy zones through the full attachment height so the
next repair does not repeat the failed 0.809--0.824 m window-only bridge.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_r25b_anatomy_branch_prototype/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "R25B_ANATOMY_BRANCH_PROTOTYPE.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_r25b_anatomy_branch_prototype/"
    "BROAD_ROOT_TRANSITION_PROBE.json"
)


def rounded_range(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "max": None}
    return {
        "min": round(min(values), 7),
        "max": round(max(values), 7),
    }


def edge_components(
    edges: list[bmesh.types.BMEdge],
) -> list[list[bmesh.types.BMEdge]]:
    by_vertex: dict[bmesh.types.BMVert, list[bmesh.types.BMEdge]] = {}
    for edge in edges:
        for vertex in edge.verts:
            by_vertex.setdefault(vertex, []).append(edge)
    unseen = set(edges)
    result: list[list[bmesh.types.BMEdge]] = []
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
                        stack.append(neighbor)
                        component.append(neighbor)
        result.append(component)
    return result


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = next(
    obj
    for obj in bpy.context.scene.objects
    if obj.type == "MESH"
    and "BIOLOGICAL_ROBERT_STATIC_LIKENESS" in obj.name
)

bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
surface_layer = bm.verts.layers.int.get("V23_Surface_Class")
zone_layer = bm.verts.layers.int.get("Adult_Anatomy_Zone")
if surface_layer is None or zone_layer is None:
    raise RuntimeError("R25B semantic layers are missing")

samples: dict[str, list[dict[str, object]]] = defaultdict(list)
z_bins: dict[str, dict[str, object]] = {}
centerline_z_bins: dict[str, dict[str, object]] = {}
for lower_mm in range(760, 826, 2):
    lower = lower_mm / 1000.0
    upper = lower + 0.002
    vertices = [
        vertex
        for vertex in bm.verts
        if (
            abs(vertex.co.x) <= 0.045
            and -0.180 <= vertex.co.y <= -0.025
            and lower <= vertex.co.z < upper
        )
    ]
    key = f"{lower:.3f}_{upper:.3f}"
    z_bins[key] = {
        "vertex_count": len(vertices),
        "x": rounded_range([vertex.co.x for vertex in vertices]),
        "y": rounded_range([vertex.co.y for vertex in vertices]),
        "z": rounded_range([vertex.co.z for vertex in vertices]),
        "surface_class_counts": {
            str(code): sum(vertex[surface_layer] == code for vertex in vertices)
            for code in sorted({vertex[surface_layer] for vertex in vertices})
        },
        "anatomy_zone_counts": {
            str(code): sum(vertex[zone_layer] == code for vertex in vertices)
            for code in sorted({vertex[zone_layer] for vertex in vertices})
        },
    }
    center_vertices = [
        vertex for vertex in vertices if abs(vertex.co.x) <= 0.008
    ]
    centerline_z_bins[key] = {
        "vertex_count": len(center_vertices),
        "x": rounded_range([vertex.co.x for vertex in center_vertices]),
        "y": rounded_range([vertex.co.y for vertex in center_vertices]),
        "z": rounded_range([vertex.co.z for vertex in center_vertices]),
        "frontmost_vertices": [
            {
                "index": vertex.index,
                "coordinate": [round(value, 7) for value in vertex.co],
                "zone": vertex[zone_layer],
                "surface_class": vertex[surface_layer],
                "normal": [
                    round(value, 7)
                    for value in (
                        sum(
                            (face.normal for face in vertex.link_faces),
                            vertex.normal.copy() * 0.0,
                        ).normalized()
                        if vertex.link_faces
                        else vertex.normal
                    )
                ],
            }
            for vertex in sorted(center_vertices, key=lambda item: item.co.y)[:16]
        ],
    }

for vertex in bm.verts:
    if not (
        abs(vertex.co.x) <= 0.045
        and -0.180 <= vertex.co.y <= -0.025
        and 0.760 <= vertex.co.z <= 0.826
    ):
        continue
    samples[f"zone_{vertex[zone_layer]}"].append(
        {
            "index": vertex.index,
            "coordinate": [round(value, 7) for value in vertex.co],
            "surface_class": vertex[surface_layer],
            "boundary_edge_count": sum(
                len(edge.link_faces) == 1 for edge in vertex.link_edges
            ),
        }
    )

local_boundary_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) <= 0.060
        and -0.190 <= vertex.co.y <= 0.005
        and 0.650 <= vertex.co.z <= 0.850
        for vertex in edge.verts
    )
]
boundary_components = []
for component in edge_components(local_boundary_edges):
    vertices = {vertex for edge in component for vertex in edge.verts}
    boundary_components.append(
        {
            "edge_count": len(component),
            "vertex_count": len(vertices),
            "x": rounded_range([vertex.co.x for vertex in vertices]),
            "y": rounded_range([vertex.co.y for vertex in vertices]),
            "z": rounded_range([vertex.co.z for vertex in vertices]),
            "zone_counts": {
                str(code): sum(vertex[zone_layer] == code for vertex in vertices)
                for code in sorted({vertex[zone_layer] for vertex in vertices})
            },
        }
    )
boundary_components.sort(key=lambda item: item["edge_count"], reverse=True)

report = {
    "schema": "kira.avatar.v23.r25b.broad_root_transition_probe.v1",
    "diagnostic_only": True,
    "source": str(SOURCE),
    "body_object": body.name,
    "coordinate_convention": "z_up_negative_y_front",
    "probe_bounds": {
        "abs_x_max": 0.045,
        "y": [-0.180, -0.025],
        "z": [0.760, 0.826],
    },
    "z_bins": z_bins,
    "centerline_z_bins": centerline_z_bins,
    "zone_sample_counts": {
        key: len(values) for key, values in samples.items()
    },
    "zone_samples": {
        key: sorted(
            values,
            key=lambda item: (
                -item["coordinate"][2],
                item["coordinate"][0],
                item["coordinate"][1],
            ),
        )[:400]
        for key, values in samples.items()
    },
    "local_boundary_components": boundary_components,
    "repair_scope_truth": (
        "The next repair must include the true authored shaft/scrotal roots "
        "below 0.809 m; the former window-only bridge cannot prove a natural "
        "continuous attachment."
    ),
}
OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
bm.free()
print(OUT)
print(json.dumps({"zone_sample_counts": report["zone_sample_counts"]}, indent=2))
