"""Render a neutral four-angle preview of a local hair-reference GLB."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def bounds(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    low = Vector(tuple(min(point[i] for point in points) for i in range(3)))
    high = Vector(tuple(max(point[i] for point in points) for i in range(3)))
    return low, high


def look(camera, target):
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def main() -> None:
    parsed = args()
    output = Path(parsed.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(Path(parsed.input).resolve()))
    meshes = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("hair source has no meshes")
    low, high = bounds(meshes)
    center = (low + high) * 0.5
    size = high - low
    span = max(size)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 800
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.08, 0.09, 0.11)
    for name, energy, location in (
        ("Key", 900.0, center + Vector((span, -span, span))),
        ("Fill", 700.0, center + Vector((-span, -span, span * 0.5))),
        ("Rear", 650.0, center + Vector((0.0, span, span))),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.size = span
        light = bpy.data.objects.new(name, data)
        light.location = location
        bpy.context.collection.objects.link(light)
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    camera_data = bpy.data.cameras.new("PreviewCamera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = span * 1.25
    camera = bpy.data.objects.new("PreviewCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    distance = span * 2.4
    for filename, location in (
        ("front.png", center + Vector((0.0, -distance, 0.0))),
        ("rear.png", center + Vector((0.0, distance, 0.0))),
        ("left.png", center + Vector((-distance, 0.0, 0.0))),
        ("crown.png", center + Vector((0.0, 0.0, distance))),
    ):
        camera.location = location
        look(camera, center)
        scene.render.filepath = str(output / filename)
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
