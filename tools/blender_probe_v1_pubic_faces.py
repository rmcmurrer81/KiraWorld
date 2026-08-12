"""Print nearest low-cage V1 pubic/perineal faces for V23 authoring."""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
bpy.ops.wm.open_mainfile(filepath=str(SRC))
obj = bpy.data.objects["BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"]
for target in (
    Vector((0.0, -0.090, 0.805)),
    Vector((0.0, -0.065, 0.730)),
    Vector((0.0, -0.020, 0.700)),
):
    ranked = sorted(
        obj.data.polygons,
        key=lambda polygon: (polygon.center - target).length,
    )
    print("TARGET", tuple(round(value, 6) for value in target))
    for polygon in ranked[:12]:
        print(
            polygon.index,
            "center",
            tuple(round(value, 6) for value in polygon.center),
            "normal",
            tuple(round(value, 6) for value in polygon.normal),
            "verts",
            tuple(polygon.vertices),
            "mat",
            polygon.material_index,
        )
