"""Render neutral close views of the authorized adult male anatomy reference.

This is private structural guidance only.  It does not transfer the reference
person's identity, proportions, skin, face, or finished surface into Robert.
"""

from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/avatar_builder/asset_library/adult_anatomy_reference/"
    "male_nude_2_1_f117148577.glb"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/male_nude_2_neutral_detail"
)
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))

body = bpy.data.objects.get("Object003_Object003_mtl_0")
if body is None:
    raise RuntimeError("authorized male anatomy reference body mesh is missing")

material = bpy.data.materials.new("AuthorizedReferenceNeutralClay")
material.use_nodes = True
bsdf = next(
    node
    for node in material.node_tree.nodes
    if node.type == "BSDF_PRINCIPLED"
)
bsdf.inputs["Base Color"].default_value = (0.34, 0.20, 0.16, 1.0)
bsdf.inputs["Roughness"].default_value = 0.76
for obj in (item for item in bpy.context.scene.objects if item.type == "MESH"):
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True

target = Vector((1.69, 0.44, 31.0))

world = bpy.data.worlds.new("NeutralReferenceWorld")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (
    0.12,
    0.12,
    0.12,
    1.0,
)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.65

for name, location, energy, size in (
    ("Key", (-10.0, -18.0, 42.0), 900.0, 8.0),
    ("Fill", (12.0, -10.0, 35.0), 600.0, 7.0),
    ("Rear", (2.0, 16.0, 39.0), 700.0, 7.0),
):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(light)
    light.location = Vector(location)
    light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()

camera_data = bpy.data.cameras.new("Camera")
camera = bpy.data.objects.new("Camera", camera_data)
bpy.context.collection.objects.link(camera)
bpy.context.scene.camera = camera
camera.data.type = "ORTHO"
camera.data.ortho_scale = 14.5

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1100
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.look = "AgX - Medium High Contrast"

views = {
    "front_negative_y": Vector((target.x, -26.0, target.z)),
    "front_positive_y": Vector((target.x, 26.0, target.z)),
    "left": Vector((-24.0, target.y, target.z)),
    "right": Vector((27.0, target.y, target.z)),
    "front_three_quarter": Vector((-16.0, -20.0, target.z + 0.5)),
}
for label, location in views.items():
    camera.location = location
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"{label}.png")
    bpy.ops.render.render(write_still=True)

print(OUT)
