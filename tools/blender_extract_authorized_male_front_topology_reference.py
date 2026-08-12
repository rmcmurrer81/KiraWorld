"""Extract and render only the authorized male reference's front pelvis region.

The crop is local construction evidence.  It excludes the reference person's
face, skin, identity material, and whole-body proportions and is never an owner
deliverable or a donor surface for Biological Robert.
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
    "male_nude_2_1_f117148577.glb"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/front_local_topology_reference"
)
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
source = bpy.data.objects.get("Object003_Object003_mtl_0")
if source is None:
    raise RuntimeError("authorized high-resolution body reference mesh missing")

world_points = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
selected_faces = []
selected_indices = set()
for polygon in source.data.polygons:
    points = [world_points[index] for index in polygon.vertices]
    if all(
        -3.6 <= point.x <= 4.8
        and -5.7 <= point.y <= -2.0
        and 24.5 <= point.z <= 35.0
        for point in points
    ):
        selected_faces.append(tuple(polygon.vertices))
        selected_indices.update(polygon.vertices)

if not selected_faces:
    raise RuntimeError("front pelvis topology crop selected no faces")

old_indices = sorted(selected_indices)
index_map = {old: new for new, old in enumerate(old_indices)}
vertices = [world_points[index] for index in old_indices]
faces = [tuple(index_map[index] for index in face) for face in selected_faces]
mesh = bpy.data.meshes.new("Authorized_Male_Front_Local_Topology_Reference")
mesh.from_pydata(vertices, [], faces)
mesh.update()
patch = bpy.data.objects.new(
    "Authorized_Male_Front_Local_Topology_Reference",
    mesh,
)
bpy.context.collection.objects.link(patch)

for obj in list(bpy.context.scene.objects):
    if obj is not patch:
        bpy.data.objects.remove(obj, do_unlink=True)

material = bpy.data.materials.new("NeutralTopologyInspection")
material.diffuse_color = (0.46, 0.24, 0.16, 1.0)
material.roughness = 0.72
patch.data.materials.append(material)
for polygon in patch.data.polygons:
    polygon.use_smooth = True

xs = [vertex.co.x for vertex in patch.data.vertices]
ys = [vertex.co.y for vertex in patch.data.vertices]
zs = [vertex.co.z for vertex in patch.data.vertices]
minimum = Vector((min(xs), min(ys), min(zs)))
maximum = Vector((max(xs), max(ys), max(zs)))
center = (minimum + maximum) * 0.5
extent = max(maximum - minimum)

world = bpy.data.worlds.new("NeutralReferenceWorld")
bpy.context.scene.world = world
world.color = (0.035, 0.035, 0.04)
for offset, energy, size in (
    (Vector((-extent, -extent, extent)), 850.0, extent * 1.4),
    (Vector((extent, -extent * 0.5, extent * 0.5)), 550.0, extent),
    (Vector((0.0, extent, extent)), 650.0, extent),
):
    data = bpy.data.lights.new("ReferenceArea", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new("ReferenceArea", data)
    light.location = center + offset
    light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.collection.objects.link(light)

camera_data = bpy.data.cameras.new("ReferenceCamera")
camera = bpy.data.objects.new("ReferenceCamera", camera_data)
bpy.context.collection.objects.link(camera)
bpy.context.scene.camera = camera
camera.data.type = "ORTHO"
camera.data.ortho_scale = extent * 1.22

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
for label, location in (
    ("front", center + Vector((0.0, -extent * 2.0, 0.0))),
    ("rear", center + Vector((0.0, extent * 2.0, 0.0))),
    ("left", center + Vector((-extent * 2.0, 0.0, 0.0))),
    ("right", center + Vector((extent * 2.0, 0.0, 0.0))),
    (
        "front_three_quarter",
        center + Vector((extent * 1.5, -extent * 1.5, extent * 0.08)),
    ),
):
    camera.location = location
    camera.rotation_euler = (center - location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"{label}.png")
    bpy.ops.render.render(write_still=True)

blend_path = OUT / "AUTHORIZED_MALE_FRONT_LOCAL_TOPOLOGY_REFERENCE.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
report = {
    "status": "PRIVATE STRUCTURAL REFERENCE ONLY",
    "source_class": "AUTHORIZED ADULT MALE ANATOMY REFERENCE",
    "identity_surface_transfer_allowed": False,
    "owner_deliverable": False,
    "vertices": len(vertices),
    "faces": len(faces),
    "bounds": [list(minimum), list(maximum)],
    "output": str(blend_path),
}
(OUT / "REFERENCE_CROP_REPORT.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)
print(json.dumps(report, indent=2))
