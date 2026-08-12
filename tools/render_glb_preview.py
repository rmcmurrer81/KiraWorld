import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def main() -> int:
    if len(sys.argv) < 3:
        raise SystemExit("usage: blender --background --python tools/render_glb_preview.py -- model.glb output.png")
    model_path = Path(sys.argv[-2])
    output_path = Path(sys.argv[-1])
    if not model_path.exists():
        raise SystemExit(f"missing model: {model_path}")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.import_scene.gltf(filepath=str(model_path))

    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            try:
                bpy.ops.object.shade_smooth()
            except RuntimeError:
                pass
            obj.select_set(False)

    bpy.ops.object.light_add(type="AREA", location=(0.0, -1.8, 2.6))
    key = bpy.context.object
    key.name = "preview key light"
    key.data.energy = 550
    key.data.size = 3.0

    bpy.ops.object.camera_add(location=(0.0, -3.2, 0.92))
    camera = bpy.context.object
    camera.name = "preview camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 1.55
    look_at(camera, Vector((0.0, -0.02, 0.72)))
    bpy.context.scene.camera = camera

    bpy.context.scene.render.resolution_x = 1000
    bpy.context.scene.render.resolution_y = 1400
    bpy.context.scene.render.film_transparent = False
    bpy.context.scene.world.color = (0.72, 0.78, 0.84)
    bpy.context.scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
