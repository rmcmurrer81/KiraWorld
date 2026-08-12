"""Render a GLB reference asset from several angles for lesson review.

Run with Blender:
  blender --background --python tools/render_avatar_builder_reference_angles.py -- --asset path.glb --output-dir out
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clear_scene() -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for image in list(bpy.data.images):
        bpy.data.images.remove(image)


def scene_bounds() -> tuple[Vector, Vector]:
    points: list[Vector] = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    if not points:
        return Vector((0, 0, 0)), Vector((1, 1, 1))
    return (
        Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points))),
        Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points))),
    )


def look_at(camera: bpy.types.Object, target: Vector) -> None:
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_scene(asset: Path) -> tuple[Vector, float]:
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(asset))
    bpy.context.view_layer.update()

    low, high = scene_bounds()
    center = (low + high) * 0.5
    size = max((high - low).x, (high - low).y, (high - low).z, 0.1)

    light_data = bpy.data.lights.new("angle_review_key_light", "AREA")
    light_data.energy = 500
    light_data.size = max(size * 2.5, 2.0)
    light = bpy.data.objects.new("angle_review_key_light", light_data)
    bpy.context.collection.objects.link(light)
    light.location = center + Vector((size * 1.5, -size * 2.0, size * 2.0))

    camera_data = bpy.data.cameras.new("angle_review_camera")
    camera_data.lens = 55
    camera = bpy.data.objects.new("angle_review_camera", camera_data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera

    bpy.context.scene.render.resolution_x = 1200
    bpy.context.scene.render.resolution_y = 900
    bpy.context.scene.render.film_transparent = False
    bpy.context.scene.world.color = (0.03, 0.04, 0.05)
    return center, size


def render_angles(asset: Path, output_dir: Path) -> dict:
    center, size = setup_scene(asset)
    camera = bpy.context.scene.camera
    assert camera is not None
    distance = size * 2.8
    angles = {
        "front": Vector((0, -distance, size * 0.15)),
        "side": Vector((distance, 0, size * 0.15)),
        "top": Vector((0, -distance * 0.1, distance)),
        "three_quarter": Vector((distance * 0.75, -distance, distance * 0.35)),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    renders: dict[str, str] = {}
    for name, offset in angles.items():
        camera.location = center + offset
        look_at(camera, center)
        path = output_dir / f"{asset.stem}_{name}.png"
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        renders[name] = str(path)
    manifest = {
        "schema_version": 1,
        "created_at": now_iso(),
        "asset": str(asset),
        "review_purpose": "Avatar Builder eye lesson angle review; reference only, not a copied avatar body.",
        "renders": renders,
        "notes": [
            "Use front/side/top/three-quarter views to study eye parts, socket relationship, and movement/reference structure.",
            "This does not approve the current Marinette or Gwen eye placement.",
        ],
    }
    manifest_path = output_dir / f"{asset.stem}_angle_review.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", required=True)
    parser.add_argument("--output-dir", required=True)
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    args = parser.parse_args(argv)
    manifest = render_angles(Path(args.asset), Path(args.output_dir))
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
