"""Audit every component in the authorized male reproductive GLB.

The earlier audit rendered only the smallest mesh and therefore did not show
which objects provide useful external structural guidance.  This diagnostic
lists and renders each mesh independently.  It is reference evidence only and
never copies a donor body or identity surface into Biological Robert.
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
    "anatomy_reference_audit/male_reproductive_system_components"
)
OUT.mkdir(parents=True, exist_ok=True)


def look_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def world_points(obj):
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
meshes = sorted(
    [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and len(obj.data.vertices) > 3
    ],
    key=lambda obj: len(obj.data.vertices),
    reverse=True,
)
if not meshes:
    raise RuntimeError("authorized reproductive reference has no mesh objects")

material = bpy.data.materials.new("AuthorizedComponentNeutral")
material.use_nodes = True
bsdf = next(
    node
    for node in material.node_tree.nodes
    if node.type == "BSDF_PRINCIPLED"
)
bsdf.inputs["Base Color"].default_value = (0.50, 0.29, 0.22, 1.0)
bsdf.inputs["Roughness"].default_value = 0.74
for obj in meshes:
    obj.data.materials.clear()
    obj.data.materials.append(material)
    obj.hide_render = True
    for polygon in obj.data.polygons:
        polygon.use_smooth = True

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.look = "AgX - Medium High Contrast"
world = bpy.data.worlds.new("AuthorizedComponentWorld")
world.color = (0.025, 0.028, 0.034)
scene.world = world

camera_data = bpy.data.cameras.new("AuthorizedComponentCamera")
camera_data.type = "ORTHO"
camera = bpy.data.objects.new("AuthorizedComponentCamera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera

rows = []
for index, obj in enumerate(meshes):
    points = world_points(obj)
    minimum = Vector(
        tuple(min(point[axis] for point in points) for axis in range(3))
    )
    maximum = Vector(
        tuple(max(point[axis] for point in points) for axis in range(3))
    )
    center = (minimum + maximum) * 0.5
    extent = max(maximum[axis] - minimum[axis] for axis in range(3))
    camera.data.ortho_scale = max(0.02, extent * 1.22)
    lights = []
    for label, offset, energy in (
        ("Key", Vector((-1.0, -1.4, 1.2)), 320.0),
        ("Fill", Vector((1.2, -0.7, 0.5)), 180.0),
        ("Rear", Vector((0.0, 1.2, 0.8)), 120.0),
    ):
        data = bpy.data.lights.new(f"{label}_{index:02d}", "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = extent * 1.4
        light = bpy.data.objects.new(f"{label}_{index:02d}", data)
        light.location = center + offset * extent
        look_at(light, center)
        bpy.context.collection.objects.link(light)
        lights.append(light)
    obj.hide_render = False
    render_paths = {}
    for label, direction in {
        "front": Vector((0.0, -1.0, 0.0)),
        "rear": Vector((0.0, 1.0, 0.0)),
        "side": Vector((1.0, 0.0, 0.0)),
        "three_quarter": Vector((0.7, -0.7, 0.12)),
    }.items():
        camera.location = center + direction * extent * 2.6
        look_at(camera, center)
        destination = OUT / f"component_{index:02d}_{label}.png"
        scene.render.filepath = str(destination)
        bpy.ops.render.render(write_still=True)
        render_paths[label] = str(destination)
    obj.hide_render = True
    for light in lights:
        bpy.data.objects.remove(light, do_unlink=True)
    rows.append(
        {
            "index": index,
            "name": obj.name,
            "vertices": len(obj.data.vertices),
            "faces": len(obj.data.polygons),
            "bounds": {
                "min": list(minimum),
                "max": list(maximum),
            },
            "materials_before_neutral_override": [
                slot.material.name if slot.material else None
                for slot in obj.material_slots
            ],
            "renders": render_paths,
        }
    )

bpy.ops.wm.save_as_mainfile(
    filepath=str(OUT / "AUTHORIZED_REPRODUCTIVE_COMPONENT_AUDIT.blend")
)
report = {
    "schema": "kira.avatar.authorized_reference.reproductive_components.v1",
    "source": str(SOURCE),
    "status": "STRUCTURAL REFERENCE ONLY - NOT ROBERT GEOMETRY",
    "component_count": len(rows),
    "components": rows,
    "robert_geometry_modified": False,
    "donor_identity_surface_transfer_allowed": False,
}
(OUT / "COMPONENT_AUDIT.json").write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(report, indent=2))
