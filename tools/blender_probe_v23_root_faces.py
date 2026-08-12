"""Inspect final V23 central-root face normals/materials/UVs."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


source = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(source))
body = bpy.data.objects["BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_MEDICAL_LOCAL_REBUILD"]
mesh = body.data
uv = mesh.uv_layers.active
for polygon in mesh.polygons:
    center = polygon.center
    if (
        abs(center.x) < 0.028
        and -0.105 < center.y < -0.025
        and 0.800 < center.z < 0.832
    ):
        values = []
        if uv is not None:
            values = [
                tuple(round(value, 4) for value in uv.data[index].uv)
                for index in polygon.loop_indices
            ]
        print(
            polygon.index,
            "center",
            tuple(round(value, 5) for value in center),
            "normal",
            tuple(round(value, 4) for value in polygon.normal),
            "material",
            polygon.material_index,
            "uv",
            values,
        )
