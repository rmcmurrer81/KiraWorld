"""Print imported eye-mesh geometry facts for renderer compatibility checks.

Run with Blender in background mode.  This is deliberately read-only: it never
saves the imported scene or edits the source GLB.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import bpy


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("glb", type=Path)
    script_args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(script_args)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.glb.resolve()))
    for obj in sorted(bpy.context.scene.objects, key=lambda item: item.name):
        if obj.type != "MESH":
            continue
        mesh = obj.data
        mesh.calc_loop_triangles()
        area_total = 0.0
        normal_sum = [0.0, 0.0, 0.0]
        for polygon in mesh.polygons:
            area_total += polygon.area
            for axis in range(3):
                normal_sum[axis] += polygon.normal[axis] * polygon.area
        average = tuple(value / area_total if area_total else 0.0 for value in normal_sum)
        materials = [slot.material.name if slot.material else "<none>" for slot in obj.material_slots]
        bounds = [tuple(round(value, 7) for value in corner) for corner in obj.bound_box]
        print(
            f"EYE_GEOMETRY name={obj.name!r} vertices={len(mesh.vertices)} "
            f"polygons={len(mesh.polygons)} avg_local_normal={tuple(round(v, 6) for v in average)} "
            f"materials={materials!r} bounds={bounds!r} parent={obj.parent.name if obj.parent else None!r} "
            f"local_location={tuple(round(v, 7) for v in obj.location)!r} "
            f"world_location={tuple(round(v, 7) for v in obj.matrix_world.translation)!r}"
        )


if __name__ == "__main__":
    main()
