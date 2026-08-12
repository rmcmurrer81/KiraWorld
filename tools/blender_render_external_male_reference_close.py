"""Render the coherent external male reference pelvis at useful close scale.

This corrects the earlier over-dark, full-torso framing.  The result is
structural guidance only; no donor body, proportions, skin, or identity
surface is copied into Biological Robert.
"""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/avatar_builder/asset_library/adult_anatomy_reference/"
    "male_reproductive_system_f5c19ef767.glb"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/external_male_pelvis_close"
)
OUT.mkdir(parents=True, exist_ok=True)


def look_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
body = max(
    (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
for obj in list(bpy.context.scene.objects):
    if obj is not body:
        bpy.data.objects.remove(obj, do_unlink=True)

material = bpy.data.materials.new("AuthorizedExternalPelvisClay")
material.use_nodes = True
bsdf = next(
    node
    for node in material.node_tree.nodes
    if node.type == "BSDF_PRINCIPLED"
)
bsdf.inputs["Base Color"].default_value = (0.48, 0.27, 0.21, 1.0)
bsdf.inputs["Roughness"].default_value = 0.72
body.data.materials.clear()
body.data.materials.append(material)
for polygon in body.data.polygons:
    polygon.use_smooth = True

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.look = "AgX - Medium High Contrast"
world = bpy.data.worlds.new("AuthorizedExternalPelvisWorld")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (
    0.018,
    0.022,
    0.030,
    1.0,
)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45
scene.world = world

target = Vector((0.522, -0.8, -3.6))
for name, location, energy, size in (
    ("Key", (-8.0, -13.0, 7.0), 780.0, 8.0),
    ("Fill", (10.0, -7.0, 1.0), 430.0, 7.0),
    ("Rear", (2.0, 8.0, 4.0), 300.0, 6.0),
):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new(name, data)
    light.location = location
    look_at(light, target)
    bpy.context.collection.objects.link(light)

camera_data = bpy.data.cameras.new("AuthorizedExternalPelvisCamera")
camera_data.type = "ORTHO"
camera_data.ortho_scale = 10.5
camera = bpy.data.objects.new("AuthorizedExternalPelvisCamera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera

views = {
    "front": Vector((0.522, -24.0, -3.6)),
    "side": Vector((22.0, -0.8, -3.6)),
    "three_quarter": Vector((16.0, -16.0, -3.3)),
}
render_paths = {}
for label, location in views.items():
    camera.location = location
    look_at(camera, target)
    destination = OUT / f"{label}.png"
    scene.render.filepath = str(destination)
    bpy.ops.render.render(write_still=True)
    render_paths[label] = str(destination)

bpy.ops.wm.save_as_mainfile(
    filepath=str(OUT / "AUTHORIZED_EXTERNAL_MALE_PELVIS_CLOSE.blend")
)
report = {
    "schema": "kira.avatar.authorized_reference.external_pelvis_close.v1",
    "source": str(SOURCE),
    "status": "STRUCTURAL RELATIONSHIP REFERENCE ONLY - NOT ROBERT GEOMETRY",
    "reference_object": body.name,
    "target": list(target),
    "orthographic_scale": camera.data.ortho_scale,
    "renders": render_paths,
    "allowed_use": [
        "root relationship",
        "shaft/body/glans relationship",
        "scrotal placement",
        "perineal continuity",
    ],
    "forbidden_use": [
        "donor body transfer",
        "donor proportions transfer",
        "donor skin or identity surface transfer",
    ],
    "robert_geometry_modified": False,
}
(OUT / "EXTERNAL_PELVIS_CLOSE_REPORT.json").write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(report, indent=2))
