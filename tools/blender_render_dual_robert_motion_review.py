"""Render private body-only stills and MP4 movement proof for one candidate."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


source = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
output = source.parent / "private_review"
output.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source))

for obj in list(bpy.data.objects):
    if obj.type in {"CAMERA", "LIGHT"}:
        bpy.data.objects.remove(obj, do_unlink=True)

rig = next(obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE")
body = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.name.endswith("_Body"))

gray = bpy.data.materials.new("ReviewSupportGray")
gray.diffuse_color = (0.09, 0.11, 0.14, 1)
bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.015))
floor = bpy.context.object
floor.data.materials.append(gray)
bpy.ops.mesh.primitive_cube_add(location=(0, 0.38, 0.25), scale=(0.42, 0.42, 0.25))
chair = bpy.context.object
chair.name = "ReviewChair"
chair.data.materials.append(gray)
bpy.ops.mesh.primitive_cube_add(location=(0, 1.05, 0.28), scale=(0.62, 1.0, 0.28))
bed = bpy.context.object
bed.name = "ReviewBed"
bed.data.materials.append(gray)

world = bpy.context.scene.world or bpy.data.worlds.new("PrivateReviewWorld")
bpy.context.scene.world = world
world.color = (0.025, 0.025, 0.035)
for location, energy, size in (((3, -4, 4), 1000, 4), ((-3, -2, 2.4), 650, 3), ((0, 3, 4), 800, 3)):
    data = bpy.data.lights.new("Area", "AREA")
    data.energy, data.shape, data.size = energy, "DISK", size
    light = bpy.data.objects.new("Area", data)
    light.location = location
    bpy.context.collection.objects.link(light)
    light.rotation_euler = (Vector((0, 0, 0.95)) - light.location).to_track_quat("-Z", "Y").to_euler()

camera_data = bpy.data.cameras.new("ReviewCamera")
camera = bpy.data.objects.new("ReviewCamera", camera_data)
bpy.context.collection.objects.link(camera)
bpy.context.scene.camera = camera
camera.location = (2.8, -4.5, 1.35)
camera.rotation_euler = (Vector((0, 0.1, 0.9)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.lens = 52

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 480
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.frame_start = 1
scene.frame_end = 328
scene.render.fps = 24

for label, frame in (("neutral", 1), ("walk", 44), ("turn", 88), ("sit", 188), ("lie", 288), ("get_up", 328)):
    scene.frame_set(frame)
    scene.render.filepath = str(output / f"{label}_{frame:03d}.png")
    bpy.ops.render.render(write_still=True)

if "--stills-only" in sys.argv:
    print(f"STILLS={output}")
    raise SystemExit(0)

scene.render.resolution_x = 320
scene.render.resolution_y = 480
scene.render.image_settings.file_format = "PNG"
sequence = output / "movement_frames"
sequence.mkdir(parents=True, exist_ok=True)
scene.render.filepath = str(sequence / "frame_")
bpy.ops.render.render(animation=True)
print(f"PNG_SEQUENCE={sequence}")
