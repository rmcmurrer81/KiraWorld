"""Render bounded, private, clothed source-quality diagnostics from a rigged GLB.

This is an inspection renderer, not an Avatar Builder candidate pack. It removes
only unskinned preview primitives from the imported in-memory scene and never
writes back to the supplied model.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


def _look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def _bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def _setup(asset: Path) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.import_scene.gltf(filepath=str(asset))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one armature, found {len(armatures)}")
    armature = armatures[0]
    skinned = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and any(modifier.type == "ARMATURE" and modifier.object == armature for modifier in obj.modifiers)
    ]
    if not skinned:
        raise RuntimeError("no meshes are skinned to the source armature")
    for obj in [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj not in skinned]:
        bpy.data.objects.remove(obj, do_unlink=True)
    for obj in skinned:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    return armature, skinned


def _lights(target: Vector, height: float) -> None:
    world = bpy.context.scene.world or bpy.data.worlds.new("source_audit_world")
    bpy.context.scene.world = world
    world.color = (0.035, 0.045, 0.065)
    for name, location, energy, size in (
        ("key", target + Vector((height * 0.65, -height * 0.9, height * 0.8)), 1000.0, height * 0.65),
        ("fill", target + Vector((-height * 0.7, -height * 0.25, height * 0.3)), 650.0, height * 0.55),
        ("rim", target + Vector((0.0, height * 0.7, height * 0.7)), 850.0, height * 0.45),
    ):
        data = bpy.data.lights.new(f"source_audit_{name}", "AREA")
        data.energy = energy
        data.size = max(size, 1.0)
        light = bpy.data.objects.new(f"source_audit_{name}", data)
        bpy.context.collection.objects.link(light)
        light.location = location
        _look_at(light, target)


def _set_action(armature: bpy.types.Object, name: str | None, frame: float) -> str:
    armature.animation_data_create()
    action = bpy.data.actions.get(name) if name else None
    armature.animation_data.action = action
    bpy.context.scene.frame_set(int(frame))
    bpy.context.view_layer.update()
    return action.name if action else "rest_pose"


def _render(
    output: Path,
    armature: bpy.types.Object,
    skinned: list[bpy.types.Object],
    *,
    action: str | None,
    frame: float,
    view: Vector,
    face: bool = False,
    full: bool = False,
) -> dict[str, object]:
    action_name = _set_action(armature, action, frame)
    skin_like = [
        obj
        for obj in skinned
        if any("skin" in material.name.lower() for material in obj.data.materials if material)
    ]
    low, high = _bounds(skinned if full else (skin_like or skinned))
    body_center = (low + high) * 0.5
    body_height = max(float(high.z - low.z), 0.1)
    if face:
        target = Vector((body_center.x, body_center.y, high.z - body_height * 0.12))
        ortho_scale = body_height * 0.38
    else:
        target = body_center
        ortho_scale = body_height * 1.18
    camera = bpy.data.objects.get("source_audit_camera")
    if camera is None:
        camera_data = bpy.data.cameras.new("source_audit_camera")
        camera_data.type = "ORTHO"
        camera_data.lens = 55
        camera = bpy.data.objects.new("source_audit_camera", camera_data)
        bpy.context.collection.objects.link(camera)
        bpy.context.scene.camera = camera
    camera.data.ortho_scale = ortho_scale
    direction = view.normalized()
    camera.location = target + direction * body_height * 2.5
    _look_at(camera, target)
    bpy.context.scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    return {
        "path": str(output),
        "action": action_name,
        "frame": int(frame),
        "face_closeup": face,
        "full_source_bounds": full,
    }


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(argv) != 2:
        raise SystemExit("usage: blender --background --python tools/render_glb_source_quality_audit.py -- model.glb output_dir")
    asset, output_dir = Path(argv[0]), Path(argv[1])
    output_dir.mkdir(parents=True, exist_ok=True)
    armature, skinned = _setup(asset)
    low, high = _bounds(skinned)
    _lights((low + high) * 0.5, max(float(high.z - low.z), 1.0))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    specs = [
        ("rest_front", None, 0, Vector((0, -1, 0)), False, False),
        ("rest_three_quarter", None, 0, Vector((0.72, -1, 0.12)), False, False),
        ("rest_back", None, 0, Vector((0, 1, 0)), False, False),
        ("rest_full_source_bounds", None, 0, Vector((0, -1, 0)), False, True),
        ("face_front", None, 0, Vector((0, -1, 0)), True, False),
        ("idle_mid", "level_idle_01", 28, Vector((0, -1, 0)), False, False),
        ("bestmove_mid", "level_bestmove_01", 36, Vector((0.72, -1, 0.12)), False, False),
        ("bestmove_full_source_bounds", "level_bestmove_01", 36, Vector((0.72, -1, 0.12)), False, True),
        ("thinking_mid", "level_thinking_01", 52, Vector((0.72, -1, 0.12)), False, False),
        ("win_mid", "level_win_01", 52, Vector((0, -1, 0)), False, False),
    ]
    renders = [
        _render(
            output_dir / f"{name}.png",
            armature,
            skinned,
            action=action,
            frame=frame,
            view=view,
            face=face,
            full=full,
        )
        for name, action, frame, view, face, full in specs
    ]
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifact_type": "private_clothed_owner_source_quality_audit",
        "source_path": str(asset),
        "source_not_modified": True,
        "candidate_created": False,
        "runtime_activation_allowed": False,
        "renders": renders,
    }
    (output_dir / "source_quality_audit_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
