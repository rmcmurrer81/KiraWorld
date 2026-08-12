"""Render protected fitting angles from the current Robert foundation."""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/private_owner_review/dual_robert_20260729/foundation/robert_fitting_foundation.blend"
OUTPUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/foundation/renders"
OUTPUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))

for obj in list(bpy.data.objects):
    if obj.type in {"CAMERA", "LIGHT"}:
        bpy.data.objects.remove(obj, do_unlink=True)

body_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
mins = Vector((1e9, 1e9, 1e9))
maxs = Vector((-1e9, -1e9, -1e9))
for obj in body_objects:
    for corner in obj.bound_box:
        point = obj.matrix_world @ Vector(corner)
        mins.x, mins.y, mins.z = min(mins.x, point.x), min(mins.y, point.y), min(mins.z, point.z)
        maxs.x, maxs.y, maxs.z = max(maxs.x, point.x), max(maxs.y, point.y), max(maxs.z, point.z)
center = (mins + maxs) * 0.5
height = maxs.z - mins.z

world = bpy.context.scene.world or bpy.data.worlds.new("PrivateReviewWorld")
bpy.context.scene.world = world
world.color = (0.035, 0.035, 0.035)

for location, energy, size in (
    ((3.2, -4.5, center.z + 2.5), 1100, 4.0),
    ((-3.0, -2.0, center.z + 1.0), 700, 3.0),
    ((0.0, 3.0, center.z + 3.5), 900, 3.0),
):
    data = bpy.data.lights.new("Area", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new("Area", data)
    light.location = location
    bpy.context.collection.objects.link(light)
    light.rotation_euler = (Vector(center) - light.location).to_track_quat("-Z", "Y").to_euler()

camera_data = bpy.data.cameras.new("PrivateReviewCamera")
camera = bpy.data.objects.new("PrivateReviewCamera", camera_data)
bpy.context.collection.objects.link(camera)
bpy.context.scene.camera = camera
camera_data.lens = 58

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 600
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False

angles = {
    "front": 0,
    "right_profile": 90,
    "back": 180,
    "left_profile": 270,
    "three_quarter": 35,
    "rear_three_quarter": 145,
}
distance = height * 1.55
for label, degrees in angles.items():
    radians = math.radians(degrees)
    camera.location = (
        center.x + math.sin(radians) * distance,
        center.y - math.cos(radians) * distance,
        center.z + height * 0.02,
    )
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUTPUT / f"{label}.png")
    bpy.ops.render.render(write_still=True)

print(f"renders={len(angles)}")
