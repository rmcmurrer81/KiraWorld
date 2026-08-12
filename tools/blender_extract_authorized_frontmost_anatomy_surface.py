"""Extract the front-most local adult-anatomy surface as reference evidence.

The imported scan is fragmented.  This script selects only polygons in the
bounded front-most pelvis region, recenters that structural sample for visual
study, and renders it.  It never modifies or supplies Robert geometry.
"""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/authorized_reference_robert_frame/"
    "AUTHORIZED_REFERENCE_ROBERT_FRAME.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/authorized_frontmost_anatomy_surface"
)
OUT.mkdir(parents=True, exist_ok=True)

X_CENTER = -0.075


def look_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
vertices = []
faces = []
sources = []
for obj in [item for item in bpy.context.scene.objects if item.type == "MESH"]:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    selected_faces = []
    selected_indices = set()
    for polygon in obj.data.polygons:
        polygon_points = [points[index] for index in polygon.vertices]
        center = sum(polygon_points, Vector()) / len(polygon_points)
        if (
            -0.115 <= center.x <= -0.035
            and center.y <= -0.112
            and 0.700 <= center.z <= 0.850
            and all(
                -0.130 <= point.x <= -0.020
                and point.y <= -0.098
                and 0.685 <= point.z <= 0.865
                for point in polygon_points
            )
        ):
            selected_faces.append(tuple(polygon.vertices))
            selected_indices.update(polygon.vertices)
    if not selected_faces:
        continue
    ordered = sorted(selected_indices)
    mapping = {
        old_index: len(vertices) + new_index
        for new_index, old_index in enumerate(ordered)
    }
    vertices.extend(
        Vector((points[index].x - X_CENTER, points[index].y, points[index].z))
        for index in ordered
    )
    faces.extend(
        tuple(mapping[index] for index in polygon)
        for polygon in selected_faces
    )
    sources.append(
        {
            "name": obj.name,
            "selected_vertices": len(ordered),
            "selected_faces": len(selected_faces),
        }
    )

if len(faces) < 50:
    raise RuntimeError(f"front-most crop too small: {len(faces)} faces")

for obj in list(bpy.context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

mesh = bpy.data.meshes.new("AuthorizedFrontmostAnatomySurface")
mesh.from_pydata(vertices, [], faces)
mesh.update()
surface = bpy.data.objects.new("AUTHORIZED_FRONTMOST_ANATOMY_SURFACE", mesh)
bpy.context.collection.objects.link(surface)
for polygon in surface.data.polygons:
    polygon.use_smooth = True

material = bpy.data.materials.new("AuthorizedFrontmostNeutral")
material.use_nodes = True
bsdf = next(
    node
    for node in material.node_tree.nodes
    if node.type == "BSDF_PRINCIPLED"
)
bsdf.inputs["Base Color"].default_value = (0.42, 0.23, 0.18, 1.0)
bsdf.inputs["Roughness"].default_value = 0.76
surface.data.materials.append(material)

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.look = "AgX - Medium High Contrast"
world = bpy.data.worlds.new("AuthorizedFrontmostWorld")
world.color = (0.025, 0.028, 0.034)
scene.world = world

target = Vector((0.0, -0.125, 0.775))
for name, location, energy, size in (
    ("Key", (-0.30, -0.50, 1.00), 90.0, 0.40),
    ("Fill", (0.34, -0.35, 0.88), 55.0, 0.34),
    ("Rear", (0.0, 0.20, 0.90), 35.0, 0.30),
):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new(name, data)
    light.location = location
    look_at(light, target)
    bpy.context.collection.objects.link(light)

camera_data = bpy.data.cameras.new("AuthorizedFrontmostCamera")
camera_data.type = "ORTHO"
camera_data.ortho_scale = 0.19
camera = bpy.data.objects.new("AuthorizedFrontmostCamera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera
views = {
    "front": Vector((0.0, -0.60, 0.775)),
    "side": Vector((0.50, -0.125, 0.775)),
    "three_quarter": Vector((0.36, -0.48, 0.785)),
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
    filepath=str(OUT / "AUTHORIZED_FRONTMOST_ANATOMY_SURFACE.blend")
)
report = {
    "schema": "kira.avatar.authorized_reference.frontmost_surface.v1",
    "source": str(SOURCE),
    "status": "STRUCTURAL REFERENCE ONLY - NOT ROBERT GEOMETRY",
    "crop": {
        "original_x_center": X_CENTER,
        "recentering_only_for_diagnostic_view": True,
        "vertices": len(vertices),
        "faces": len(faces),
        "source_objects": sources,
    },
    "renders": render_paths,
    "robert_geometry_modified": False,
}
(OUT / "FRONTMOST_SURFACE_REPORT.json").write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(report, indent=2))
