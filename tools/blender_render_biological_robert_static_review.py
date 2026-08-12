"""Render the seven protected static-likeness views requested by the owner."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


arguments = sys.argv[sys.argv.index("--") + 1 :]
source = Path(arguments[0]).resolve()
requested_views = set(arguments[1:])
out = source.parent / "private_review"
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source))

for obj in list(bpy.data.objects):
    if obj.type in {"CAMERA", "LIGHT"}:
        bpy.data.objects.remove(obj, do_unlink=True)

scene = bpy.context.scene
scene.frame_set(1)
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 720
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False

world = scene.world or bpy.data.worlds.new("StaticReviewWorld")
scene.world = world
world.color = (0.035, 0.038, 0.045)

floor_mat = bpy.data.materials.new("NeutralFloor")
floor_mat.diffuse_color = (0.12, 0.13, 0.15, 1)
bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.012))
bpy.context.object.data.materials.append(floor_mat)

for location, energy, size in (
    ((3.2, -4.0, 4.2), 1050, 4.0),
    ((-3.0, -2.0, 2.8), 700, 3.0),
    ((0.0, 3.0, 4.0), 850, 3.0),
    # Neutral lower fills keep underside/pelvis/butt form readable without
    # baking cast shadow into a false "muddy skin" impression.
    ((0.0, -2.4, 0.55), 140, 2.8),
    ((0.0, 2.2, 0.70), 120, 2.6),
):
    light_data = bpy.data.lights.new("StaticReviewArea", "AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light = bpy.data.objects.new("StaticReviewArea", light_data)
    light.location = location
    bpy.context.collection.objects.link(light)
    light.rotation_euler = (Vector((0, 0, 1.0)) - light.location).to_track_quat("-Z", "Y").to_euler()

camera_data = bpy.data.cameras.new("StaticReviewCamera")
camera = bpy.data.objects.new("StaticReviewCamera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera
camera.data.lens = 58

views = {
    "front": ((0, -4.4, 1.05), (0, 0, 0.98)),
    "left_profile": ((-4.4, 0, 1.05), (0, 0, 0.98)),
    "right_profile": ((4.4, 0, 1.05), (0, 0, 0.98)),
    "rear": ((0, 4.4, 1.05), (0, 0, 0.98)),
    "left_three_quarter": ((-3.15, -3.15, 1.08), (0, 0, 1.0)),
    "right_three_quarter": ((3.15, -3.15, 1.08), (0, 0, 1.0)),
    "close_face": ((0, -1.55, 1.67), (0, -0.02, 1.68)),
    "close_pelvis_front": ((0, -1.25, 0.73), (0, -0.02, 0.73)),
    "close_pelvis_left_three_quarter": ((-0.85, -0.95, 0.75), (0, -0.02, 0.73)),
    "close_pelvis_right_three_quarter": ((0.85, -0.95, 0.75), (0, -0.02, 0.73)),
    "close_pelvis_side": ((1.00, -0.62, 0.75), (0, -0.08, 0.72)),
    "close_hand_left": ((-0.235, -1.00, 0.84), (-0.235, -0.02, 0.84)),
    "close_hand_right": ((0.235, -1.00, 0.84), (0.235, -0.02, 0.84)),
    "close_hand_right_side": ((1.10, 0.0, 0.84), (0.235, 0.0, 0.84)),
    "close_upper_legs": ((0, -1.30, 0.67), (0, -0.02, 0.67)),
}
for label, (position, target) in views.items():
    if requested_views and label not in requested_views:
        continue
    camera.location = position
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    if label.startswith("close_"):
        scene.render.resolution_x = 900
        scene.render.resolution_y = 900
        camera.data.lens = 72
    else:
        scene.render.resolution_x = 720
        scene.render.resolution_y = 960
        camera.data.lens = 58
    scene.render.filepath = str(out / f"{label}.png")
    bpy.ops.render.render(write_still=True)
print(out)
