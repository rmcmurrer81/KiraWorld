"""Render focused source-only multiviews for selected hair-pack meshes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def _args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--objects", required=True)
    return parser.parse_args(argv)


def _bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[i] for point in points) for i in range(3))),
        Vector(tuple(max(point[i] for point in points) for i in range(3))),
    )


def _look(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def main() -> None:
    args = _args()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    requested = [value.strip() for value in args.objects.split(",") if value.strip()]
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(Path(args.input).resolve()))
    meshes = [
        obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"
    ]
    selected = {
        name: next(
            (
                obj
                for obj in meshes
                if obj.name == name or obj.name.split(".", 1)[0] == name
            ),
            None,
        )
        for name in requested
    }
    missing = [name for name, obj in selected.items() if obj is None]
    if missing:
        raise RuntimeError(f"missing requested hair objects: {missing}")

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 700
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.075, 0.085, 0.10)
    camera_data = bpy.data.cameras.new("HairCandidateCamera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("HairCandidateCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    records = []
    for requested_name, current in selected.items():
        assert current is not None
        for mesh in meshes:
            mesh.hide_render = mesh is not current
        low, high = _bounds(current)
        center = (low + high) * 0.5
        size = high - low
        span = max(size)
        camera.data.ortho_scale = span * 1.24
        for light in [obj for obj in bpy.data.objects if obj.type == "LIGHT"]:
            bpy.data.objects.remove(light, do_unlink=True)
        for label, energy, offset in (
            ("Key", 800.0, (span, -span, span)),
            ("Fill", 650.0, (-span, -span, span * 0.35)),
            ("Rear", 600.0, (0.0, span, span)),
        ):
            data = bpy.data.lights.new(f"{label}_{requested_name}", "AREA")
            data.energy = energy
            data.size = span
            light = bpy.data.objects.new(f"{label}_{requested_name}", data)
            light.location = center + Vector(offset)
            bpy.context.collection.objects.link(light)
            _look(light, center)
        distance = span * 2.5
        for view, location in (
            ("front", center + Vector((0.0, -distance, 0.0))),
            ("left", center + Vector((-distance, 0.0, 0.0))),
            ("rear", center + Vector((0.0, distance, 0.0))),
            ("crown", center + Vector((0.0, 0.0, distance))),
        ):
            camera.location = location
            _look(camera, center)
            path = output / f"{requested_name}_{view}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
        records.append(
            {
                "object": requested_name,
                "vertices": len(current.data.vertices),
                "bounds_low": [round(float(value), 6) for value in low],
                "bounds_high": [round(float(value), 6) for value in high],
            }
        )
    (output / "catalog.json").write_text(
        json.dumps(records, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
