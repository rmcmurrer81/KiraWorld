"""Render an owner-authorized adult anatomy GLB for local topology inspection."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy
from mathutils import Vector


source = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
out = Path(sys.argv[sys.argv.index("--") + 2]).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source))
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
mins = Vector((float("inf"),) * 3)
maxs = Vector((float("-inf"),) * 3)
for obj in meshes:
    for corner in obj.bound_box:
        world = obj.matrix_world @ Vector(corner)
        mins.x, mins.y, mins.z = min(mins.x, world.x), min(mins.y, world.y), min(mins.z, world.z)
        maxs.x, maxs.y, maxs.z = max(maxs.x, world.x), max(maxs.y, world.y), max(maxs.z, world.z)
center = (mins + maxs) * 0.5
height = maxs.z - mins.z
for location in ((center.x + height, center.y - height * 1.8, center.z + height * 0.2),
                 (center.x - height, center.y - height * 1.8, center.z + height * 0.2)):
    data = bpy.data.lights.new("Area", "AREA")
    data.energy, data.size = 900, height
    light = bpy.data.objects.new("Area", data)
    light.location = location
    bpy.context.collection.objects.link(light)
    light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
cam_data = bpy.data.cameras.new("Camera")
camera = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(camera)
bpy.context.scene.camera = camera
camera.data.lens = 70
bpy.context.scene.render.engine = "BLENDER_EEVEE"
bpy.context.scene.render.resolution_x = 800
bpy.context.scene.render.resolution_y = 1000
bpy.context.scene.render.resolution_percentage = 100
bpy.context.scene.render.image_settings.file_format = "PNG"
bpy.context.scene.world.color = (0.04, 0.04, 0.05)
for label, location in (
    ("front", (center.x, maxs.y + height * 1.7, center.z)),
    ("rear", (center.x, mins.y - height * 1.7, center.z)),
    ("side", (maxs.x + height * 1.5, center.y, center.z)),
):
    camera.location = location
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.render.filepath = str(out / f"{label}.png")
    bpy.ops.render.render(write_still=True)
print({"source": source.name, "mesh_count": len(meshes), "bounds": [list(mins), list(maxs)]})
