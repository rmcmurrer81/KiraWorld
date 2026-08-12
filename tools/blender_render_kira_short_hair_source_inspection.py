#!/usr/bin/env python3
"""Render the enrolled short layered hair reference without its scale sphere."""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(r"C:\Users\robmc\Kira")
SOURCE = ROOT / "Avatar/avatar_builder/asset_library/hair_reference/short_hair_cut_in_layers_with_bones_90fd798a2e.glb"
OUTPUT = ROOT / "Avatar/private_owner_review/kira_temporary_functional_body_20260730/source_inspection/short_hair_cut_layers_90fd798a2e_visible"


def material() -> bpy.types.Material:
    value = bpy.data.materials.new("Neutral_Hair_Inspection")
    value.diffuse_color = (0.22, 0.24, 0.28, 1.0)
    return value


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
for obj in list(bpy.context.scene.objects):
    if obj.type == "MESH" and obj.name == "Icosphere":
        bpy.data.objects.remove(obj, do_unlink=True)
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
shade = material()
for obj in meshes:
    obj.data.materials.clear()
    obj.data.materials.append(shade)
points = [
    obj.matrix_world @ Vector(corner)
    for obj in meshes
    for corner in obj.bound_box
]
low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
center = (low + high) * 0.5
size = max(high.x - low.x, high.y - low.y, high.z - low.z)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_shadows = False
scene.display.shading.show_cavity = False
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.image_settings.file_format = "PNG"
if scene.world is None:
    scene.world = bpy.data.worlds.new("Hair_Inspection_World")
scene.world.color = (0.03, 0.04, 0.05)
camera_data = bpy.data.cameras.new("Hair_Inspection_Camera")
camera_data.type = "ORTHO"
camera_data.ortho_scale = size * 1.22
camera_data.clip_start = max(size * 0.001, 0.000001)
camera_data.clip_end = max(size * 20.0, 1.0)
camera = bpy.data.objects.new("Hair_Inspection_Camera", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
OUTPUT.mkdir(parents=True, exist_ok=True)
views = {
    "front": Vector((center.x, center.y - size * 3.0, center.z)),
    "side": Vector((center.x + size * 3.0, center.y, center.z)),
    "rear": Vector((center.x, center.y + size * 3.0, center.z)),
    "top": Vector((center.x, center.y, center.z + size * 3.0)),
}
for name, location in views.items():
    camera.location = location
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUTPUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
