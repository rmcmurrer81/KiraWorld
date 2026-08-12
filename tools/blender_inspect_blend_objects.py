import sys
from pathlib import Path
import bpy
from mathutils import Vector

source = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(source))
for obj in bpy.context.scene.objects:
    if obj.type in {"MESH", "CURVE", "CURVES"}:
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        xs, ys, zs = ([p[i] for p in points] for i in range(3))
        print(
            obj.name, obj.type, len(obj.data.vertices) if obj.type == "MESH" else "",
            [round(min(xs), 3), round(max(xs), 3)],
            [round(min(ys), 3), round(max(ys), 3)],
            [round(min(zs), 3), round(max(zs), 3)],
            "hide_render", obj.hide_render,
        )
