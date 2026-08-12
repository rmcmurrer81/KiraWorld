from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def world_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return low, high


def vector3(v: Vector) -> list[float]:
    return [round(float(v.x), 5), round(float(v.y), 5), round(float(v.z), 5)]


def mesh_vertex_total(meshes: list[bpy.types.Object]) -> int:
    total = 0
    for obj in meshes:
        if getattr(obj, "data", None) is not None and hasattr(obj.data, "vertices"):
            total += len(obj.data.vertices)
    return total


def summarize(path: Path) -> dict[str, object]:
    clear_scene()
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]

    lows: list[Vector] = []
    highs: list[Vector] = []
    mesh_summaries: list[dict[str, object]] = []
    for obj in meshes:
        low, high = world_bounds(obj)
        lows.append(low)
        highs.append(high)
        size = high - low
        mesh_summaries.append(
            {
                "name": obj.name,
                "vertices": len(obj.data.vertices) if getattr(obj, "data", None) and hasattr(obj.data, "vertices") else 0,
                "size": vector3(size),
                "materials": [slot.material.name for slot in obj.material_slots if slot.material][:8],
            }
        )

    if lows and highs:
        low = Vector((min(v.x for v in lows), min(v.y for v in lows), min(v.z for v in lows)))
        high = Vector((max(v.x for v in highs), max(v.y for v in highs), max(v.z for v in highs)))
        size = high - low
    else:
        low = high = size = Vector((0.0, 0.0, 0.0))

    bone_names: list[str] = []
    for armature in armatures:
        bone_names.extend([bone.name for bone in armature.data.bones])

    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "mesh_count": len(meshes),
        "armature_count": len(armatures),
        "bone_count": len(bone_names),
        "bone_sample": bone_names[:40],
        "animation_count": len(bpy.data.actions),
        "animations": [action.name for action in bpy.data.actions[:25]],
        "world_bounds": {"min": vector3(low), "max": vector3(high), "size": vector3(size)},
        "vertex_total": mesh_vertex_total(meshes),
        "mesh_sample": sorted(mesh_summaries, key=lambda item: int(item["vertices"]), reverse=True)[:12],
    }


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(argv) < 2:
        raise SystemExit("usage: blender --background --python tools/blender_inventory_glb_folder.py -- input_folder output_json")
    root = Path(argv[0])
    output = Path(argv[1])
    files = sorted(root.rglob("*.glb"))
    results: list[dict[str, object]] = []
    for index, path in enumerate(files, start=1):
        try:
            result = summarize(path)
            result["ok"] = True
        except Exception as exc:  # Blender import errors should not stop the whole inventory.
            result = {"path": str(path), "bytes": path.stat().st_size if path.exists() else 0, "ok": False, "error": str(exc)}
        result["index"] = index
        results.append(result)
        print(f"[{index}/{len(files)}] {path.name}: {'ok' if result.get('ok') else 'failed'}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"root": str(root), "count": len(files), "models": results}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
