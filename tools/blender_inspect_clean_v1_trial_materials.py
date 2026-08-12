"""Read-only material/topology inspection for a clean-V1 implicit trial."""

import sys
from collections import Counter, defaultdict
from pathlib import Path

import bpy


source = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(source))
body = max(
    (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
print("body", body.name)
print(
    "slots",
    [
        (index, material.name if material else None)
        for index, material in enumerate(body.data.materials)
    ],
)
total = Counter(polygon.material_index for polygon in body.data.polygons)
roi = Counter()
areas = defaultdict(list)
bounds = defaultdict(
    lambda: {
        "min": [float("inf")] * 3,
        "max": [float("-inf")] * 3,
    }
)
for polygon in body.data.polygons:
    center = polygon.center
    index = polygon.material_index
    areas[index].append(float(polygon.area))
    for axis in range(3):
        bounds[index]["min"][axis] = min(bounds[index]["min"][axis], center[axis])
        bounds[index]["max"][axis] = max(bounds[index]["max"][axis], center[axis])
    if (
        abs(center.x) < 0.40
        and -0.40 < center.y < 0.20
        and 0.50 < center.z < 0.95
    ):
        roi[index] += 1
print("total", dict(total))
print("roi", dict(roi))
print("bounds", dict(bounds))
for index, values in sorted(areas.items()):
    values.sort()
    print(
        "area",
        index,
        "min",
        values[0],
        "p10",
        values[len(values) // 10],
        "median",
        values[len(values) // 2],
        "p90",
        values[(len(values) * 9) // 10],
        "max",
        values[-1],
    )
