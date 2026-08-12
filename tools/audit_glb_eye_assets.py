"""Blender-side structural audit for Kira eye/body GLB assets.

Run with Blender, for example:
  blender --background --python tools/audit_glb_eye_assets.py -- report.json model.glb [...]

The script never edits an input asset.  It imports one file at a time into an
empty scene, records mesh/material/armature metadata and world-space bounds,
then clears the scene before the next input.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy  # type: ignore
from mathutils import Vector  # type: ignore


def script_args() -> tuple[Path, list[Path]]:
    if "--" not in sys.argv:
        raise SystemExit("Expected: -- OUTPUT_JSON INPUT_GLB [INPUT_GLB ...]")
    args = sys.argv[sys.argv.index("--") + 1 :]
    if len(args) < 2:
        raise SystemExit("Expected: -- OUTPUT_JSON INPUT_GLB [INPUT_GLB ...]")
    return Path(args[0]), [Path(value) for value in args[1:]]


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (
        bpy.data.meshes,
        bpy.data.armatures,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(collection):
            collection.remove(block)


def rounded(values) -> list[float]:
    return [round(float(value), 6) for value in values]


def object_world_bounds(obj) -> tuple[Vector, Vector] | None:
    if obj.type != "MESH" or not obj.bound_box:
        return None
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(min(point[index] for point in points) for index in range(3)),
        Vector(max(point[index] for point in points) for index in range(3)),
    )


def material_record(material) -> dict:
    record = {
        "name": material.name,
        "blend_method": getattr(material, "surface_render_method", None),
        "use_nodes": bool(material.use_nodes),
    }
    if material.use_nodes and material.node_tree:
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            for socket_name in (
                "Base Color",
                "Roughness",
                "Metallic",
                "IOR",
                "Alpha",
                "Transmission Weight",
                "Coat Weight",
            ):
                socket = bsdf.inputs.get(socket_name)
                if socket is not None:
                    value = socket.default_value
                    record[socket_name] = rounded(value) if hasattr(value, "__len__") else round(float(value), 6)
    return record


def audit(path: Path) -> dict:
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.view_layer.update()

    objects = []
    lows: list[Vector] = []
    highs: list[Vector] = []
    for obj in sorted(bpy.context.scene.objects, key=lambda item: item.name.lower()):
        record = {
            "name": obj.name,
            "type": obj.type,
            "parent": obj.parent.name if obj.parent else None,
            "location": rounded(obj.location),
            "rotation_euler": rounded(obj.rotation_euler),
            "scale": rounded(obj.scale),
        }
        bounds = object_world_bounds(obj)
        if bounds:
            low, high = bounds
            lows.append(low)
            highs.append(high)
            record.update(
                {
                    "bounds_low": rounded(low),
                    "bounds_high": rounded(high),
                    "dimensions": rounded(high - low),
                    "vertices": len(obj.data.vertices),
                    "polygons": len(obj.data.polygons),
                    "materials": [slot.material.name for slot in obj.material_slots if slot.material],
                    "shape_keys": (
                        [key.name for key in obj.data.shape_keys.key_blocks]
                        if obj.data.shape_keys
                        else []
                    ),
                }
            )
        if obj.type == "ARMATURE":
            record["bones"] = [bone.name for bone in obj.data.bones]
        objects.append(record)

    if lows:
        scene_low = Vector(min(point[index] for point in lows) for index in range(3))
        scene_high = Vector(max(point[index] for point in highs) for index in range(3))
    else:
        scene_low = Vector((0, 0, 0))
        scene_high = Vector((0, 0, 0))

    animations = []
    for action in bpy.data.actions:
        animations.append(
            {
                "name": action.name,
                "frame_range": rounded(action.frame_range),
                "slots": len(getattr(action, "slots", [])),
            }
        )
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "scene_bounds_low": rounded(scene_low),
        "scene_bounds_high": rounded(scene_high),
        "scene_dimensions": rounded(scene_high - scene_low),
        "object_count": len(objects),
        "objects": objects,
        "materials": [material_record(material) for material in bpy.data.materials],
        "animations": animations,
    }


def main() -> None:
    output_path, input_paths = script_args()
    report = {
        "schema_version": 1,
        "blender_version": bpy.app.version_string,
        "assets": [audit(path.resolve()) for path in input_paths],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output_path), "assets": len(input_paths)}))


if __name__ == "__main__":
    main()
