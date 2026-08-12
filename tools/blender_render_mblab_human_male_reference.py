"""Render the bundled MB-Lab human male base for licensed-reference audit.

The source database and base mesh are AGPL-3.0.  These renders are read-only
engineering evidence.  The mesh must not be copied into Biological Robert or
promoted as a proprietary Avatar Builder foundation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/avatar_builder/tooling/mb_lab_official/data/"
    "humanoid_library.blend"
)
LICENSE = (
    ROOT / "Avatar/avatar_builder/tooling/mb_lab_official/license.txt"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/mblab_human_male_base"
)
OUT.mkdir(parents=True, exist_ok=True)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects["MBLab_human_male"]
for obj in list(bpy.data.objects):
    if obj is body:
        continue
    bpy.data.objects.remove(obj, do_unlink=True)
body.hide_viewport = False
body.hide_render = False

material = bpy.data.materials.new("MBLabLicensedReferenceNeutral")
material.diffuse_color = (0.57, 0.59, 0.62, 1.0)
body.data.materials.clear()
body.data.materials.append(material)
for polygon in body.data.polygons:
    polygon.use_smooth = True

minimum = Vector(
    (
        min((body.matrix_world @ vertex.co).x for vertex in body.data.vertices),
        min((body.matrix_world @ vertex.co).y for vertex in body.data.vertices),
        min((body.matrix_world @ vertex.co).z for vertex in body.data.vertices),
    )
)
maximum = Vector(
    (
        max((body.matrix_world @ vertex.co).x for vertex in body.data.vertices),
        max((body.matrix_world @ vertex.co).y for vertex in body.data.vertices),
        max((body.matrix_world @ vertex.co).z for vertex in body.data.vertices),
    )
)
height = maximum.z - minimum.z
pelvis_z = minimum.z + height * 0.402

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "SINGLE"
scene.display.shading.single_color = (0.57, 0.59, 0.62)
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = False
scene.display.shading.show_specular_highlight = False
scene.world.color = (0.035, 0.038, 0.045)

camera_data = bpy.data.cameras.new("MBLabReferenceCamera")
camera = bpy.data.objects.new("MBLabReferenceCamera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera
views = {
    "front": (
        (0.0, -0.69 * height, pelvis_z + 0.01 * height),
        (0.0, -0.015 * height, pelvis_z),
    ),
    "side": (
        (0.56 * height, -0.34 * height, pelvis_z + 0.01 * height),
        (0.0, -0.045 * height, pelvis_z),
    ),
    "three_quarter": (
        (0.47 * height, -0.52 * height, pelvis_z + 0.02 * height),
        (0.0, -0.02 * height, pelvis_z),
    ),
}
renders = {}
for name, (location, target) in views.items():
    camera.location = location
    camera.rotation_euler = (
        Vector(target) - camera.location
    ).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 72
    path = OUT / f"{name}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    renders[name] = str(path)

report = {
    "schema": "kira.avatar.reference_audit.mblab_human_male.v1",
    "status": (
        "READ-ONLY AGPL-3.0 STRUCTURAL REFERENCE — "
        "NOT AN AVATAR BUILDER FOUNDATION"
    ),
    "source": str(SOURCE),
    "source_sha256": sha256(SOURCE),
    "license_file": str(LICENSE),
    "license_sha256": sha256(LICENSE),
    "license_facts": {
        "code": "GPL-3.0",
        "database_and_base_meshes": "AGPL-3.0",
        "generated_3d_models": (
            "AGPL-3.0 derived products according to bundled license"
        ),
        "two_dimensional_renders": (
            "separately licensed by render author under bundled license terms"
        ),
    },
    "object": body.name,
    "vertices": len(body.data.vertices),
    "faces": len(body.data.polygons),
    "bounds": {
        "minimum": list(minimum),
        "maximum": list(maximum),
    },
    "renders": renders,
    "allowed_current_use": [
        "read-only visual relationship comparison",
        "independent normalized anatomy constraints",
    ],
    "blocked_use": [
        "copying base topology into Biological Robert",
        "copying an AGPL base into a proprietary Avatar Builder foundation",
        "donor identity, body, skin, or proportion transfer",
    ],
    "robert_geometry_modified": False,
}
(OUT / "MBLAB_HUMAN_MALE_BASE_REFERENCE_REPORT.json").write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(report, indent=2))
