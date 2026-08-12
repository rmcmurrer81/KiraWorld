"""Print bounded V23 root-surface samples for engineering diagnosis."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


source = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(source))
body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_MEDICAL_LOCAL_REBUILD")
if body is None:
    raise SystemExit("missing V23 body")

vertices = [vertex.co for vertex in body.data.vertices]
for step in range(23):
    center_z = 0.735 + step * 0.004
    points = [
        point
        for point in vertices
        if abs(point.z - center_z) <= 0.002
        and abs(point.x) <= 0.080
        and point.y <= -0.035
    ]
    central = [point for point in points if abs(point.x) <= 0.018]
    print(
        f"z={center_z:.3f}",
        f"points={len(points)}",
        f"min_abs_x={min((abs(point.x) for point in points), default=9):.5f}",
        f"central={len(central)}",
        f"central_y={min((point.y for point in central), default=9):.5f}"
        f"..{max((point.y for point in central), default=-9):.5f}",
    )
