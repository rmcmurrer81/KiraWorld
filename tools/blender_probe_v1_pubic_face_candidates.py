"""List V1 low-cage pubic faces for explicit root/scrotal extrusion design."""

from __future__ import annotations

from pathlib import Path

import bpy


root = Path(__file__).resolve().parents[1]
source = (
    root
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
)
bpy.ops.wm.open_mainfile(filepath=str(source))
body = bpy.data.objects["BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"]
for polygon in body.data.polygons:
    center = polygon.center
    if (
        abs(center.x) < 0.070
        and -0.210 < center.y < -0.060
        and 0.640 < center.z < 0.850
    ):
        print(
            polygon.index,
            "center",
            tuple(round(value, 5) for value in center),
            "normal",
            tuple(round(value, 4) for value in polygon.normal),
            "verts",
            list(polygon.vertices),
        )
