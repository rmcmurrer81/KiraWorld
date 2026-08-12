"""Split and render the authorized local anatomy crop by connected component.

This is reference analysis only.  It helps identify which fragment contains
the useful adult-anatomy surface without copying the donor identity, body
proportions, skin, or finished surface into Biological Robert.
"""

from __future__ import annotations

import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/male_nude_2_object003_family_local_crop_probe/"
    "AUTHORIZED_REFERENCE_OBJECT003_LOCAL_CROP_PROBE.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/male_nude_2_object003_family_components"
)
OUT.mkdir(parents=True, exist_ok=True)


def look_at(obj: bpy.types.Object, point: Vector) -> None:
    obj.rotation_euler = (point - obj.location).to_track_quat("-Z", "Y").to_euler()


def bounds(obj: bpy.types.Object) -> dict[str, list[float]]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return {
        "min": [min(point[index] for point in points) for index in range(3)],
        "max": [max(point[index] for point in points) for index in range(3)],
    }


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
source = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
for obj in bpy.context.selected_objects:
    obj.select_set(False)
source.select_set(True)
bpy.context.view_layer.objects.active = source
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")

parts = sorted(
    [obj for obj in bpy.context.selected_objects if obj.type == "MESH"],
    key=lambda obj: len(obj.data.vertices),
    reverse=True,
)
material = bpy.data.materials.new("AuthorizedReferenceComponentNeutral")
material.use_nodes = True
bsdf = next(
    node
    for node in material.node_tree.nodes
    if node.type == "BSDF_PRINCIPLED"
)
bsdf.inputs["Base Color"].default_value = (0.58, 0.40, 0.34, 1.0)
bsdf.inputs["Roughness"].default_value = 0.72
for index, part in enumerate(parts):
    part.name = f"AUTHORIZED_REFERENCE_COMPONENT_{index:02d}"
    part.data.materials.clear()
    part.data.materials.append(material)
    part.hide_render = True
    for polygon in part.data.polygons:
        polygon.use_smooth = True

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
world = bpy.data.worlds.get("ReferenceProbeWorld") or bpy.data.worlds.new(
    "ReferenceProbeWorld"
)
world.color = (0.035, 0.038, 0.045)
scene.world = world

camera_data = bpy.data.cameras.new("ReferenceComponentCamera")
camera_data.type = "ORTHO"
camera = bpy.data.objects.new("ReferenceComponentCamera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera

for location, energy, size in [
    ((-0.35, -0.55, 1.05), 700, 0.55),
    ((0.42, -0.35, 0.88), 500, 0.40),
    ((0.00, 0.30, 0.82), 280, 0.35),
]:
    data = bpy.data.lights.new("ReferenceComponentArea", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new("ReferenceComponentArea", data)
    light.location = location
    look_at(light, Vector((0.0, -0.14, 0.742)))
    bpy.context.collection.objects.link(light)

rows = []
for index, part in enumerate(parts):
    part.hide_render = False
    box = bounds(part)
    center = Vector(
        tuple(
            (box["min"][axis] + box["max"][axis]) * 0.5
            for axis in range(3)
        )
    )
    extent = max(
        box["max"][axis] - box["min"][axis] for axis in range(3)
    )
    camera.data.ortho_scale = max(0.04, extent * 1.25)
    render_paths = {}
    for label, direction in {
        "front": Vector((0.0, -1.0, 0.0)),
        "side": Vector((1.0, 0.0, 0.0)),
        "three_quarter": Vector((0.7, -0.7, 0.15)),
    }.items():
        camera.location = center + direction * max(0.35, extent * 3.0)
        look_at(camera, center)
        destination = OUT / f"component_{index:02d}_{label}.png"
        scene.render.filepath = str(destination)
        bpy.ops.render.render(write_still=True)
        render_paths[label] = str(destination)
    rows.append(
        {
            "name": part.name,
            "vertices": len(part.data.vertices),
            "polygons": len(part.data.polygons),
            "bounds": box,
            "renders": render_paths,
            "status": "AUTHORIZED STRUCTURAL REFERENCE ONLY",
        }
    )
    part.hide_render = True

report = {
    "schema": "kira.avatar.authorized_reference.component_audit.v1",
    "source": str(SOURCE),
    "use": "STRUCTURAL GUIDANCE ONLY",
    "robert_geometry_modified": False,
    "components": rows,
}
(OUT / "COMPONENT_AUDIT.json").write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
bpy.ops.wm.save_as_mainfile(
    filepath=str(OUT / "AUTHORIZED_REFERENCE_COMPONENT_AUDIT.blend")
)
print(json.dumps(report, indent=2))
