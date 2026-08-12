"""Inspect the clean V24C pubic bridge without changing it."""

from __future__ import annotations

import json
from pathlib import Path

import bmesh
import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24c_superior_bridge_refinement/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_SUPERIOR_BRIDGE_REFINEMENT.blend"
)
OUTPUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/V24C_CENTRAL_PATCH_PROBE.json"
)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects[
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_SUPERIOR_BRIDGE_REFINEMENT"
]
bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
rows = []
for face in bm.faces:
    coordinates = [vertex.co for vertex in face.verts]
    center = face.calc_center_median()
    if not (
        max(abs(point.x) for point in coordinates) <= 0.085
        and max(point.y for point in coordinates) <= 0.060
        and min(point.y for point in coordinates) >= -0.170
        and max(point.z for point in coordinates) <= 0.850
        and min(point.z for point in coordinates) >= 0.660
    ):
        continue
    crosses_midline = (
        min(point.x for point in coordinates) <= 0.0
        <= max(point.x for point in coordinates)
    )
    has_medial_vertex = any(abs(point.x) <= 0.002 for point in coordinates)
    if not (crosses_midline or has_medial_vertex):
        continue
    rows.append(
        {
            "index": face.index,
            "vertex_indices": [vertex.index for vertex in face.verts],
            "coordinates": [
                [round(float(value), 7) for value in point]
                for point in coordinates
            ],
            "center": [round(float(value), 7) for value in center],
            "area": float(face.calc_area()),
            "normal": [round(float(value), 7) for value in face.normal],
            "material_index": face.material_index,
            "crosses_midline": crosses_midline,
            "has_medial_vertex": has_medial_vertex,
        }
    )
bm.free()
report = {
    "schema": "kira.avatar.v24c.central_patch_probe.v1",
    "source": str(SOURCE),
    "face_count": len(rows),
    "faces": sorted(rows, key=lambda row: row["center"][2], reverse=True),
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
