"""Render the rejected R23 Attempt 05 for engineering diagnosis only.

The exact saved candidate is opened read-only.  This script never saves a
Blend, changes runtime selection, or labels the rejected mesh as reviewable.
It exists only to make the already-recorded transition failures visible before
a materially different repair is authored.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "RecoverySprint/continuation_20260803/kira_r23_cc0_afes_author/attempt_05/"
    "kira_r23_cc0_afes_core_transfer_attempt_05.blend"
)
SOURCE_SHA256 = "394cba65c2ec1fefa22981079c3b53486a4dfd6037e89caf1504990a7cbbce4e"
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_attempt05_visual_diagnostic/attempt_01"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def render(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    filename: str,
    location: Vector,
    target: Vector,
    scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = scale
    look_at(camera, target)
    scene.render.filepath = str(OUTPUT / filename)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    if sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("rejected R23 source hash drifted")
    if OUTPUT.exists():
        raise RuntimeError("append-only diagnostic output already exists")
    OUTPUT.mkdir(parents=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    bodies = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and bool(obj.get("r23_candidate_id"))
    ]
    if len(bodies) != 1:
        raise RuntimeError(f"expected one R23 body, found {[obj.name for obj in bodies]}")
    body = bodies[0]
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    for rig in rigs:
        if rig.animation_data:
            rig.animation_data.action = None
        for bone in rig.pose.bones:
            bone.rotation_mode = "XYZ"
            bone.rotation_euler = (0.0, 0.0, 0.0)
            bone.location = (0.0, 0.0, 0.0)
            bone.scale = (1.0, 1.0, 1.0)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    for obj in list(bpy.context.scene.objects):
        if obj.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(obj, do_unlink=True)

    points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    minimum = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z
    pelvis = Vector((center.x, center.y - 0.025, minimum.z + height * 0.49))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.006, 0.011, 0.018)
    scene.view_settings.look = "AgX - Medium High Contrast"

    for name, location, energy, size in (
        ("Key", (2.2, -3.2, 2.8), 900.0, 4.0),
        ("Fill", (-2.4, -2.2, 1.7), 520.0, 3.2),
        ("Rear", (1.0, 2.8, 2.5), 700.0, 3.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        light.location = location
        bpy.context.collection.objects.link(light)
        look_at(light, pelvis)

    camera_data = bpy.data.cameras.new("R23DiagnosticCamera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R23DiagnosticCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera

    distance = 1.6
    views = {
        "full_front.png": (Vector((center.x, minimum.y - 3.0, center.z)), center, height * 1.08),
        "pelvis_front.png": (Vector((pelvis.x, pelvis.y - distance, pelvis.z)), pelvis, 0.31),
        "pelvis_left_three_quarter.png": (Vector((pelvis.x - 0.85, pelvis.y - 1.25, pelvis.z)), pelvis, 0.31),
        "pelvis_side.png": (Vector((pelvis.x - distance, pelvis.y, pelvis.z)), pelvis, 0.31),
        "pelvis_rear.png": (Vector((pelvis.x, pelvis.y + distance, pelvis.z)), pelvis, 0.31),
        "pelvis_inferior_front.png": (Vector((pelvis.x, pelvis.y - 0.72, pelvis.z - 0.72)), pelvis, 0.28),
    }
    for filename, (location, target, scale) in views.items():
        render(scene, camera, filename, location, target, scale)

    report = {
        "schema": "kira.avatar.r23_attempt05_visual_diagnostic.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "REJECTED_ENGINEERING_VISUAL_DIAGNOSTIC_ONLY",
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": SOURCE_SHA256,
        "source_unchanged": sha256(SOURCE) == SOURCE_SHA256,
        "blend_saved": False,
        "runtime_mutation": False,
        "rendered_views": sorted(views),
        "truth": "Images do not make Attempt 05 safe, accepted, or owner-reviewable.",
    }
    (OUTPUT / "DIAGNOSTIC_REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
