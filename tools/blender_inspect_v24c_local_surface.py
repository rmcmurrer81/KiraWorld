"""Inspect the raw V24C pelvis patch without modifying the private avatar.

This utility records the compact center-front vertex/face neighborhood used to
design an explicit, connected graft.  It deliberately does not render, alter,
or save the source blend.
"""

from __future__ import annotations

import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24c_superior_bridge_refinement/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_SUPERIOR_BRIDGE_REFINEMENT.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24c_superior_bridge_refinement/"
    "V24C_LOCAL_SURFACE_INSPECTION.json"
)
BODY = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_SUPERIOR_BRIDGE_REFINEMENT"


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get(BODY)
if body is None:
    raise RuntimeError("V24C body not found")

selected_vertices = {
    vertex.index
    for vertex in body.data.vertices
    if abs(vertex.co.x) <= 0.090
    and -0.170 <= vertex.co.y <= 0.030
    and 0.650 <= vertex.co.z <= 0.860
}
selected_faces = [
    polygon
    for polygon in body.data.polygons
    if all(index in selected_vertices for index in polygon.vertices)
]
used_vertices = sorted(
    {index for polygon in selected_faces for index in polygon.vertices}
)

report = {
    "schema": "kira.avatar.v24c.local_surface_inspection.v1",
    "status": "READ-ONLY ENGINEERING INSPECTION",
    "source": str(SOURCE),
    "selection_bounds_m": {
        "x": [-0.090, 0.090],
        "y": [-0.170, 0.030],
        "z": [0.650, 0.860],
    },
    "vertices": [
        {
            "index": index,
            "coordinate": [
                round(float(value), 8)
                for value in body.data.vertices[index].co
            ],
        }
        for index in used_vertices
    ],
    "faces": [
        {
            "index": polygon.index,
            "vertices": list(polygon.vertices),
            "center": [
                round(float(value), 8) for value in polygon.center
            ],
            "normal": [
                round(float(value), 8) for value in polygon.normal
            ],
        }
        for polygon in selected_faces
    ],
}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(OUT)
print(json.dumps(report, indent=2))
