"""Sample V1 central pubic geometry in front-projection bins."""

from __future__ import annotations

import json
from pathlib import Path

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
    "anatomy_reference_audit/V1_PUBIC_SURFACE_SAMPLES.json"
)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects["BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"]

rows = []
for z_center in [0.83 - index * 0.005 for index in range(35)]:
    for x_center in [index * 0.005 for index in range(0, 13)]:
        vertices = [
            vertex
            for vertex in body.data.vertices
            if (
                abs(abs(vertex.co.x) - x_center) <= 0.003
                and abs(vertex.co.z - z_center) <= 0.003
                and -0.200 < vertex.co.y < 0.130
            )
        ]
        if not vertices:
            continue
        frontmost = min(vertices, key=lambda vertex: vertex.co.y)
        rearmost = max(vertices, key=lambda vertex: vertex.co.y)
        rows.append(
            {
                "x_bin": round(x_center, 4),
                "z_bin": round(z_center, 4),
                "count": len(vertices),
                "frontmost": [
                    round(value, 6) for value in frontmost.co
                ],
                "rearmost": [
                    round(value, 6) for value in rearmost.co
                ],
            }
        )

OUT.write_text(
    json.dumps({"source": str(SOURCE), "samples": rows}, indent=2) + "\n",
    encoding="utf-8",
)
print(OUT)
