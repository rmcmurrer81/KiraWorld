"""Inspect the authorized adult reference model's world-space pelvis region."""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/avatar_builder/asset_library/adult_anatomy_reference/male_nude_2_1_f117148577.glb"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))

for obj in sorted((o for o in bpy.context.scene.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices), reverse=True):
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    if not points:
        continue
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    zs = [p.z for p in points]
    print(
        f"OBJECT {obj.name} vertices={len(points)} "
        f"x={min(xs):.3f}..{max(xs):.3f} y={min(ys):.3f}..{max(ys):.3f} "
        f"z={min(zs):.3f}..{max(zs):.3f} "
        f"materials={[slot.material.name if slot.material else None for slot in obj.material_slots]}"
    )
    if not (min(zs) < 5 and max(zs) > 65):
        continue
    for low in range(25, 46, 2):
        band = [p for p in points if low <= p.z < low + 2]
        if not band:
            print(f"  z={low}..{low + 2}: empty")
            continue
        bx = [p.x for p in band]
        by = [p.y for p in band]
        print(
            f"  z={low}..{low + 2}: n={len(band)} "
            f"x={min(bx):.3f}..{max(bx):.3f} "
            f"y={min(by):.3f}..{max(by):.3f}"
        )
        central = [p for p in band if -2.5 <= p.x <= 3.5]
        if central:
            cy = [p.y for p in central]
            print(
                f"    central x=-2.5..3.5: n={len(central)} "
                f"y={min(cy):.3f}..{max(cy):.3f}"
            )
