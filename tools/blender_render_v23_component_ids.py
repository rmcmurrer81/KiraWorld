"""Render connected face components in the pelvis with distinct colors."""

from __future__ import annotations

import colorsys
import sys
from pathlib import Path

import bpy
from mathutils import Vector


if "--" not in sys.argv:
    raise SystemExit("expected -- source.blend output.png")
arguments = sys.argv[sys.argv.index("--") + 1 :]
if len(arguments) != 2:
    raise SystemExit("expected source.blend output.png")
source = Path(arguments[0]).resolve()
output = Path(arguments[1]).resolve()
output.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source))
body = max(
    (obj for obj in bpy.data.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
vertex_faces: dict[int, set[int]] = {}
for polygon in body.data.polygons:
    for vertex_index in polygon.vertices:
        vertex_faces.setdefault(int(vertex_index), set()).add(polygon.index)
remaining = set(range(len(body.data.polygons)))
components = []
while remaining:
    seed = remaining.pop()
    members = {seed}
    stack = [seed]
    while stack:
        face_index = stack.pop()
        for vertex_index in body.data.polygons[face_index].vertices:
            for neighbor in vertex_faces.get(int(vertex_index), ()):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    members.add(neighbor)
                    stack.append(neighbor)
    components.append(members)
components.sort(key=len, reverse=True)

for index, component in enumerate(components):
    hue = (index * 0.61803398875) % 1.0
    red, green, blue = colorsys.hsv_to_rgb(hue, 0.72, 0.92)
    material = bpy.data.materials.new(f"V23_Component_{index:03d}")
    material.diffuse_color = (red, green, blue, 1.0)
    body.data.materials.append(material)
    material_index = len(body.data.materials) - 1
    for face_index in component:
        body.data.polygons[face_index].material_index = material_index

scene = bpy.context.scene
for obj in list(scene.objects):
    if obj.type in {"CAMERA", "LIGHT"}:
        bpy.data.objects.remove(obj, do_unlink=True)
camera_data = bpy.data.cameras.new("V23ComponentCamera")
camera = bpy.data.objects.new("V23ComponentCamera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera
body_min = min((body.matrix_world @ Vector(corner)).z for corner in body.bound_box)
body_max = max((body.matrix_world @ Vector(corner)).z for corner in body.bound_box)
height = body_max - body_min
pelvis_z = body_min + height * 0.402
camera.location = (0.0, -0.69 * height, pelvis_z + 0.01 * height)
target = Vector((0.0, -0.015 * height, pelvis_z))
camera.rotation_euler = (target - camera.location).to_track_quat(
    "-Z", "Y"
).to_euler()
camera.data.lens = 72
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.light = "FLAT"
scene.display.shading.show_shadows = False
scene.display.shading.show_cavity = False
scene.display.shading.show_specular_highlight = False
scene.render.filepath = str(output)
bpy.ops.render.render(write_still=True)
print(output)
