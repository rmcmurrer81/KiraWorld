from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
bpy.ops.wm.open_mainfile(filepath=str(source))
for obj in bpy.context.scene.objects:
    if obj.type != "MESH":
        continue
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    xs, ys, zs = ([p[i] for p in points] for i in range(3))
    print(obj.name, len(obj.data.vertices), [round(min(xs),3),round(max(xs),3)], [round(min(ys),3),round(max(ys),3)], [round(min(zs),3),round(max(zs),3)], [m.name if m else None for m in obj.data.materials])
