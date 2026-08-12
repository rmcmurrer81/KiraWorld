"""Render one front thumbnail per substantial mesh in a local hair-pack GLB."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parsed_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--minimum-vertices", type=int, default=5000)
    return parser.parse_args(argv)


def bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    low = Vector(tuple(min(point[i] for point in points) for i in range(3)))
    high = Vector(tuple(max(point[i] for point in points) for i in range(3)))
    return low, high


def look(camera, target):
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def main() -> None:
    args = parsed_args()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(Path(args.input).resolve()))
    imported_meshes = [
        obj
        for obj in bpy.data.objects
        if obj not in before and obj.type == "MESH"
    ]
    candidates = [
        obj
        for obj in imported_meshes
        if len(obj.data.vertices) >= args.minimum_vertices
    ]
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 500
    scene.render.resolution_y = 500
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.09, 0.10, 0.12)
    camera_data = bpy.data.cameras.new("HairPackCamera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("HairPackCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    records = []
    for index, current in enumerate(candidates):
        for obj in imported_meshes:
            obj.hide_render = obj is not current
        low, high = bounds(current)
        center = (low + high) * 0.5
        size = high - low
        span = max(size)
        camera.data.ortho_scale = span * 1.25
        camera.location = center + Vector((0.0, -span * 2.5, 0.0))
        look(camera, center)
        for light in [obj for obj in bpy.data.objects if obj.type == "LIGHT"]:
            bpy.data.objects.remove(light, do_unlink=True)
        for name, energy, offset in (
            ("Key", 700.0, (span, -span, span)),
            ("Fill", 550.0, (-span, -span, span * 0.3)),
            ("Rear", 500.0, (0.0, span, span)),
        ):
            data = bpy.data.lights.new(f"{name}_{index}", "AREA")
            data.energy = energy
            data.size = span
            light = bpy.data.objects.new(f"{name}_{index}", data)
            light.location = center + Vector(offset)
            bpy.context.collection.objects.link(light)
            light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
        filename = f"{index:02d}_{current.name}.png"
        scene.render.filepath = str(output / filename)
        bpy.ops.render.render(write_still=True)
        records.append(
            {
                "index": index,
                "object": current.name,
                "vertices": len(current.data.vertices),
                "file": filename,
                "low": [round(float(value), 6) for value in low],
                "high": [round(float(value), 6) for value in high],
            }
        )
    (output / "catalog.json").write_text(
        json.dumps(records, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
