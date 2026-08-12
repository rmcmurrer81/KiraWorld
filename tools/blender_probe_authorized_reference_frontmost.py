"""Measure front-most authorized-reference pelvis vertices in Robert space."""

from __future__ import annotations

import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/authorized_reference_robert_frame/"
    "AUTHORIZED_REFERENCE_ROBERT_FRAME.blend"
)
OUT = SOURCE.parent / "FRONTMOST_PELVIS_VERTEX_PROBE.json"

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
points = []
for obj in bpy.context.scene.objects:
    if obj.type != "MESH":
        continue
    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        if 0.68 <= point.z <= 0.86 and abs(point.x) <= 0.18:
            points.append((float(point.x), float(point.y), float(point.z), obj.name))

points.sort(key=lambda row: row[1])
threshold_rows = {}
for threshold in (-0.20, -0.18, -0.16, -0.14, -0.12, -0.10):
    chosen = [row for row in points if row[1] <= threshold]
    threshold_rows[str(threshold)] = {
        "count": len(chosen),
        "x_min": min((row[0] for row in chosen), default=None),
        "x_max": max((row[0] for row in chosen), default=None),
        "z_min": min((row[2] for row in chosen), default=None),
        "z_max": max((row[2] for row in chosen), default=None),
        "objects": sorted(set(row[3] for row in chosen)),
    }

report = {
    "source": str(SOURCE),
    "status": "AUTHORIZED STRUCTURAL REFERENCE ONLY",
    "pelvis_vertex_count": len(points),
    "frontmost_200": [
        {"x": row[0], "y": row[1], "z": row[2], "object": row[3]}
        for row in points[:200]
    ],
    "thresholds": threshold_rows,
}
OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report["thresholds"], indent=2))
