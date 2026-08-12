"""Render three fast neutral pelvis views for a private static candidate.

Usage:
    blender --background --python tools/blender_render_static_pelvis_quick.py \
      -- candidate.blend output_directory

This is an iteration aid only.  Full diagnostic, topology, intersection, and
owner-review renders remain mandatory before promotion.
"""

from __future__ import annotations

import sys
from pathlib import Path

import bpy
from mathutils import Vector


if "--" not in sys.argv:
    raise SystemExit("Expected -- candidate.blend output_directory")
arguments = sys.argv[sys.argv.index("--") + 1 :]
if len(arguments) != 2:
    raise SystemExit("Expected exactly two arguments")
SOURCE = Path(arguments[0]).resolve()
OUTPUT = Path(arguments[1]).resolve()
OUTPUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
body = max(mesh_objects, key=lambda obj: len(obj.data.vertices))
body_min = min(
    (body.matrix_world @ Vector(corner)).z for corner in body.bound_box
)
body_max = max(
    (body.matrix_world @ Vector(corner)).z for corner in body.bound_box
)
unit = body_max - body_min
pelvis_z = body_min + unit * 0.402

for obj in list(bpy.data.objects):
    if obj.type in {"CAMERA", "LIGHT"}:
        bpy.data.objects.remove(obj, do_unlink=True)

scene = bpy.context.scene
scene.frame_set(1)
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "SINGLE"
scene.display.shading.single_color = (0.56, 0.58, 0.61)
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = False
scene.display.shading.show_specular_highlight = False
scene.world.color = (0.035, 0.038, 0.045)

camera_data = bpy.data.cameras.new("QuickPelvisCamera")
camera = bpy.data.objects.new("QuickPelvisCamera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera

views = {
    "front": (
        (0.0, -0.69 * unit, pelvis_z + 0.01 * unit),
        (0.0, -0.015 * unit, pelvis_z),
    ),
    "side": (
        (0.56 * unit, -0.34 * unit, pelvis_z + 0.01 * unit),
        (0.0, -0.045 * unit, pelvis_z),
    ),
    "three_quarter": (
        (0.47 * unit, -0.52 * unit, pelvis_z + 0.02 * unit),
        (0.0, -0.02 * unit, pelvis_z),
    ),
}
for name, (location, target) in views.items():
    camera.location = location
    camera.rotation_euler = (
        Vector(target) - camera.location
    ).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 72
    scene.render.filepath = str(OUTPUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)

print(OUTPUT)
