#!/usr/bin/env python3
"""Render each licensed BlackProject hair component for bounded groom repair."""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(r"C:\Users\robmc\Kira")
SOURCE = ROOT / "Avatar/avatar_builder/asset_library/base_body_reference/base_female_character_blackproject_cc_by_4.glb"
OUTPUT = ROOT / "Avatar/private_owner_review/kira_temporary_functional_body_20260730/source_inspection/blackproject_hair_components"
TARGETS = (
    "Hair_Hair Thin_0",
    "Hair_Hair Front_0",
    "Hair_Hair Mid_0",
    "Hair_Hair Long_0",
    "Hair_Hair Cap_0",
)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
by_mesh = {
    obj.data.name: obj
    for obj in bpy.context.scene.objects
    if obj.type == "MESH"
}
shade = bpy.data.materials.new("BlackProject_Hair_Component_Inspection")
shade.diffuse_color = (0.26, 0.29, 0.34, 1.0)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_shadows = False
scene.display.shading.show_cavity = False
scene.render.resolution_x = 800
scene.render.resolution_y = 900
scene.render.image_settings.file_format = "PNG"
if scene.world is None:
    scene.world = bpy.data.worlds.new("BlackProject_Hair_Inspection_World")
scene.world.color = (0.03, 0.04, 0.05)
camera_data = bpy.data.cameras.new("BlackProject_Hair_Inspection_Camera")
camera_data.type = "ORTHO"
camera = bpy.data.objects.new("BlackProject_Hair_Inspection_Camera", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
OUTPUT.mkdir(parents=True, exist_ok=True)
for target in TARGETS:
    for name, obj in by_mesh.items():
        obj.hide_render = name != target
    obj = by_mesh[target]
    obj.data.materials.clear()
    obj.data.materials.append(shade)
    low, high = bounds(obj)
    center = (low + high) * 0.5
    size = max(high.x - low.x, high.y - low.y, high.z - low.z)
    camera.data.ortho_scale = size * 1.18
    for view, location in {
        "front": Vector((center.x, center.y - size * 3.0, center.z)),
        "side": Vector((center.x + size * 3.0, center.y, center.z)),
        "top": Vector((center.x, center.y, center.z + size * 3.0)),
    }.items():
        camera.location = location
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(OUTPUT / f"{target.replace(' ', '_')}_{view}.png")
        bpy.ops.render.render(write_still=True)
