"""Print compact GLB structure details for avatar builder work."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
import mathutils


def scene_bounds() -> tuple[list[float], list[float]]:
    points: list[mathutils.Vector] = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ mathutils.Vector(corner))
    if not points:
        return [], []
    return (
        [min(point[index] for point in points) for index in range(3)],
        [max(point[index] for point in points) for index in range(3)],
    )


def inspect(path: Path) -> dict:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(path))

    mesh_names: list[str] = []
    material_names: list[str] = []
    armature_names: list[str] = []
    eye_names: list[str] = []
    hair_names: list[str] = []
    object_details: list[dict] = []

    for obj in bpy.context.scene.objects:
        lowered = obj.name.lower()
        if obj.type == "MESH":
            mesh_names.append(obj.name)
            material_names.extend(mat.name for mat in obj.data.materials if mat)
            points = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
            object_details.append(
                {
                    "name": obj.name,
                    "bounds": [
                        [min(point[index] for point in points) for index in range(3)],
                        [max(point[index] for point in points) for index in range(3)],
                    ],
                    "materials": [mat.name for mat in obj.data.materials if mat],
                }
            )
        if obj.type == "ARMATURE":
            armature_names.append(obj.name)
        if any(key in lowered for key in ("eye", "iris", "pupil", "socket", "lid")):
            eye_names.append(obj.name)
        if any(key in lowered for key in ("hair", "bang", "pigtail", "ponytail")):
            hair_names.append(obj.name)

    low, high = scene_bounds()
    return {
        "path": str(path),
        "mesh_count": len(mesh_names),
        "armature_count": len(armature_names),
        "bounds": [low, high],
        "meshes": mesh_names[:80],
        "materials": sorted(set(material_names))[:80],
        "armatures": armature_names[:20],
        "eye_names": eye_names[:60],
        "hair_names": hair_names[:60],
        "object_details": object_details[:80],
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: blender --background --python tools/inspect_glb_model.py -- file.glb [...]")
        return 2
    paths = [Path(arg) for arg in sys.argv[sys.argv.index("--") + 1 :]] if "--" in sys.argv else [Path(arg) for arg in sys.argv[1:]]
    print(json.dumps([inspect(path) for path in paths], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
