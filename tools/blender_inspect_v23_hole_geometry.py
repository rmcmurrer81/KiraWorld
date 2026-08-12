"""Inspect geometry surrounding the visible anterior-pelvis teardrop."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


if "--" not in sys.argv:
    raise SystemExit("expected -- source.blend")
arguments = sys.argv[sys.argv.index("--") + 1 :]
source = Path(arguments[0]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(source))
body = max(
    (obj for obj in bpy.data.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
records = []
for polygon in body.data.polygons:
    center = polygon.center
    if (
        abs(center.x) < 0.035
        and -0.160 < center.y < 0.080
        and 0.775 < center.z < 0.835
    ):
        records.append(
            {
                "face_index": polygon.index,
                "center": [round(value, 6) for value in center],
                "normal": [round(value, 6) for value in polygon.normal],
                "material_index": polygon.material_index,
                "vertices": [
                    [
                        round(value, 6)
                        for value in body.data.vertices[index].co
                    ]
                    for index in polygon.vertices
                ],
            }
        )
records.sort(key=lambda item: (item["center"][2], item["center"][1], item["center"][0]))
y_values = [record["center"][1] for record in records]
front_facing = [
    record for record in records if Vector(record["normal"]).y < -0.2
]
print(
    json.dumps(
        {
            "source": str(source),
            "record_count": len(records),
            "min_center_y": min(y_values) if y_values else None,
            "max_center_y": max(y_values) if y_values else None,
            "front_facing_count": len(front_facing),
            "frontmost_80": sorted(
                records,
                key=lambda item: item["center"][1],
            )[:80],
        },
        indent=2,
    )
)
