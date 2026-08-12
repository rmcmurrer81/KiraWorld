"""Render the authorized adult reference in Biological Robert coordinates.

The output is structural reference evidence only.  It validates scale,
orientation, and local anatomy placement before any hand-authored Robert mesh
is changed.  No donor identity surface is copied into Robert.
"""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/avatar_builder/asset_library/adult_anatomy_reference/"
    "male_nude_2_1_f117148577.glb"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/authorized_reference_anatomy_close"
)
OUT.mkdir(parents=True, exist_ok=True)

SCALE = 1.813 / 71.688
SOURCE_CENTER_X = 1.690873
SOURCE_CENTER_Y = 0.435622
SOURCE_FLOOR_Z = -0.092019


def mapped(point: Vector) -> Vector:
    return Vector(
        (
            -(point.x - SOURCE_CENTER_X) * SCALE,
            -(point.y - SOURCE_CENTER_Y) * SCALE,
            (point.z - SOURCE_FLOOR_Z) * SCALE,
        )
    )


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if not meshes:
    raise RuntimeError("authorized reference did not import")

for obj in meshes:
    # Several imported scan chunks can share mesh datablocks.  Make each
    # instance single-user before baking its own world transform; otherwise a
    # later chunk transforms geometry that an earlier chunk already changed.
    obj.data = obj.data.copy()
    world = obj.matrix_world.copy()
    for vertex in obj.data.vertices:
        vertex.co = mapped(world @ vertex.co)
    obj.parent = None
    obj.matrix_world = Matrix.Identity(4)
    obj.data.update()

material = bpy.data.materials.new("AuthorizedReferenceRobertFrameClay")
material.use_nodes = True
bsdf = next(
    node
    for node in material.node_tree.nodes
    if node.type == "BSDF_PRINCIPLED"
)
bsdf.inputs["Base Color"].default_value = (0.44, 0.27, 0.21, 1.0)
bsdf.inputs["Roughness"].default_value = 0.74
for obj in meshes:
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
world = bpy.data.worlds.new("AuthorizedReferenceRobertFrameWorld")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (
    0.025,
    0.028,
    0.034,
    1.0,
)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55
scene.world = world

target = Vector((-0.075, -0.115, 0.780))
for name, location, energy, size in (
    ("Key", (-0.38, -0.62, 1.08), 65.0, 0.45),
    ("Fill", (0.42, -0.38, 0.90), 42.0, 0.38),
    ("Rear", (0.0, 0.30, 0.92), 26.0, 0.32),
):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new(name, data)
    light.location = location
    look_at(light, target)
    bpy.context.collection.objects.link(light)

camera_data = bpy.data.cameras.new("AuthorizedReferenceRobertFrameCamera")
camera_data.type = "ORTHO"
camera_data.ortho_scale = 0.20
camera = bpy.data.objects.new(
    "AuthorizedReferenceRobertFrameCamera", camera_data
)
bpy.context.collection.objects.link(camera)
scene.camera = camera
scene.view_settings.look = "AgX - Medium High Contrast"

views = {
    "front": Vector((-0.075, -0.65, 0.780)),
    "side": Vector((0.50, -0.115, 0.780)),
    "three_quarter": Vector((0.36, -0.50, 0.790)),
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
    filepath=str(OUT / "AUTHORIZED_REFERENCE_ROBERT_FRAME.blend")
)
report = {
    "schema": "kira.avatar.authorized_reference.robert_frame.v1",
    "source": str(SOURCE),
    "status": "STRUCTURAL REFERENCE ONLY - NOT ROBERT GEOMETRY",
    "mapping": {
        "scale": SCALE,
        "source_center_x": SOURCE_CENTER_X,
        "source_center_y": SOURCE_CENTER_Y,
        "source_floor_z": SOURCE_FLOOR_Z,
    },
    "render_paths": render_paths,
    "mesh_bounds": [
        {
            "name": obj.name,
            "min": [
                min((obj.matrix_world @ vertex.co)[axis] for vertex in obj.data.vertices)
                for axis in range(3)
            ],
            "max": [
                max((obj.matrix_world @ vertex.co)[axis] for vertex in obj.data.vertices)
                for axis in range(3)
            ],
        }
        for obj in meshes
    ],
    "robert_geometry_modified": False,
    "full_donor_body_transfer_allowed": False,
}
(OUT / "REFERENCE_FRAME_REPORT.json").write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(report, indent=2))
