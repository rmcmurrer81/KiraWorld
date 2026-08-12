"""Record V1 object, material, and central-pelvis geometry facts."""

from __future__ import annotations

import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/V1_OBJECT_AND_PELVIS_GEOMETRY_REPORT.json"
)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rows = []
for obj in bpy.context.scene.objects:
    row = {
        "name": obj.name,
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "hidden_render": obj.hide_render,
    }
    if obj.type == "MESH":
        bounds = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        row.update(
            {
                "vertices": len(obj.data.vertices),
                "edges": len(obj.data.edges),
                "polygons": len(obj.data.polygons),
                "materials": [
                    material.name if material else None
                    for material in obj.data.materials
                ],
                "bounds_min": [
                    min(co[axis] for co in bounds) for axis in range(3)
                ],
                "bounds_max": [
                    max(co[axis] for co in bounds) for axis in range(3)
                ],
            }
        )
        if "BIOLOGICAL_ROBERT" in obj.name:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            central = [
                vertex
                for vertex in bm.verts
                if (
                    abs(vertex.co.x) < 0.080
                    and -0.180 < vertex.co.y < 0.120
                    and 0.640 < vertex.co.z < 0.840
                )
            ]
            row["central_pelvis"] = {
                "vertices": len(central),
                "min": [
                    min(vertex.co[axis] for vertex in central)
                    for axis in range(3)
                ]
                if central
                else None,
                "max": [
                    max(vertex.co[axis] for vertex in central)
                    for axis in range(3)
                ]
                if central
                else None,
                "boundary_vertex_count": sum(
                    any(len(edge.link_faces) == 1 for edge in vertex.link_edges)
                    for vertex in central
                ),
            }
            bm.free()
    rows.append(row)

OUT.write_text(
    json.dumps({"source": str(SOURCE), "objects": rows}, indent=2) + "\n",
    encoding="utf-8",
)
print(OUT)
