"""Render one authorized reference mesh at a time for structural inspection."""

import sys
from pathlib import Path

import bpy
from mathutils import Vector


source = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
object_name = sys.argv[sys.argv.index("--") + 2]
out = Path(sys.argv[sys.argv.index("--") + 3]).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
target_object = bpy.data.objects.get(object_name)
if target_object is None:
    raise RuntimeError(f"missing object {object_name}")
for obj in bpy.context.scene.objects:
    if obj.type == "MESH":
        obj.hide_render = obj != target_object
material = bpy.data.materials.new("ReferenceClay")
material.diffuse_color = (0.55, 0.33, 0.27, 1.0)
target_object.data.materials.clear()
target_object.data.materials.append(material)
for polygon in target_object.data.polygons:
    polygon.material_index = 0
    polygon.use_smooth = True

world = bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.color = (0.035, 0.035, 0.035)
target = Vector((1.6, 0.5, 31.0))
for location, energy, size in (
    ((-18, -24, 45), 1100, 10),
    ((18, -12, 35), 800, 8),
    ((0, 22, 40), 850, 9),
):
    data = bpy.data.lights.new("Area", "AREA")
    data.energy = energy
    data.size = size
    light = bpy.data.objects.new("Area", data)
    bpy.context.collection.objects.link(light)
    light.location = Vector(location)
    light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()
camera_data = bpy.data.cameras.new("Camera")
camera = bpy.data.objects.new("Camera", camera_data)
bpy.context.collection.objects.link(camera)
bpy.context.scene.camera = camera
camera.data.type = "ORTHO"
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 700
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
for label, position, aim, scale in (
    ("full_front", (1.6, -120, 35), (1.6, 0.5, 35), 78),
    ("pelvis_front", (1.6, -55, 31), (1.6, 0.5, 31), 16),
    ("pelvis_side", (-55, 0.5, 31), (1.6, 0.5, 31), 16),
    ("pelvis_three_quarter", (-38, -38, 31), (1.6, 0.5, 31), 16),
):
    camera.location = position
    camera.rotation_euler = (
        Vector(aim) - camera.location
    ).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = scale
    scene.render.filepath = str(out / f"{label}.png")
    bpy.ops.render.render(write_still=True)
print(out)
