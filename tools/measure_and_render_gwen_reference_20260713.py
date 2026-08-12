"""Measure and render the saved unmasked Gwen reference model.

This is a reference-only tool. It does not copy reference meshes into the
Avatar Builder candidate. It records proportions and renders views so the
builder can compare the generated base-body sculpt against a local reference.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy  # type: ignore
from mathutils import Vector  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSET = ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "spider_gwen" / "spider_gwen_low_poly_unmasked_reference.glb"
DEFAULT_OUT = ROOT / "Avatar" / "avatar_builder" / "reference_measurements" / "gwen_unmasked_reference_20260713"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def object_bounds(obj) -> tuple[Vector, Vector]:
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    low = Vector(min(corner[index] for corner in corners) for index in range(3))
    high = Vector(max(corner[index] for corner in corners) for index in range(3))
    return low, high


def scene_bounds(meshes) -> tuple[Vector, Vector]:
    lows = []
    highs = []
    for obj in meshes:
        low, high = object_bounds(obj)
        lows.append(low)
        highs.append(high)
    low = Vector(min(point[index] for point in lows) for index in range(3))
    high = Vector(max(point[index] for point in highs) for index in range(3))
    return low, high


def look_at(obj, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def set_camera(camera, location: Vector, target: Vector, ortho_scale: float) -> None:
    camera.location = location
    look_at(camera, target)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho_scale


def render_view(out: Path, camera, location: Vector, target: Vector, ortho_scale: float) -> str:
    set_camera(camera, location, target, ortho_scale)
    bpy.context.scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    return rel(out)


def mesh_world_vertices(obj) -> list[Vector]:
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def points_bounds(points: list[Vector]) -> tuple[Vector, Vector]:
    low = Vector(min(point[index] for point in points) for index in range(3))
    high = Vector(max(point[index] for point in points) for index in range(3))
    return low, high


def band_width(points: list[Vector], low_z: float, high_z: float, center_x: float, max_half_width: float) -> float:
    band = [point for point in points if low_z <= point.z <= high_z and abs(point.x - center_x) <= max_half_width]
    if len(band) < 6:
        return 0.0
    low, high = points_bounds(band)
    return float(high.x - low.x)


def measure_reference(meshes) -> dict:
    low, high = scene_bounds(meshes)
    height = max(float(high.z - low.z), 0.001)
    center = (low + high) * 0.5
    body_mesh = max(meshes, key=lambda obj: len(obj.data.vertices))
    hair_meshes = [obj for obj in meshes if "hair" in obj.name.lower() or any("hair" in slot.material.name.lower() for slot in obj.material_slots if slot.material)]
    body_points = mesh_world_vertices(body_mesh)
    body_low, body_high = object_bounds(body_mesh)
    core_half_width = height * 0.20
    bands = {}
    for name, z0, z1 in (
        ("shoulder", 0.70, 0.82),
        ("chest", 0.57, 0.69),
        ("waist", 0.45, 0.55),
        ("hip", 0.34, 0.46),
        ("thigh", 0.20, 0.34),
        ("calf", 0.08, 0.22),
    ):
        width = band_width(body_points, low.z + height * z0, low.z + height * z1, center.x, core_half_width)
        bands[name] = {
            "z_norm": [z0, z1],
            "core_width": round(width, 5),
            "width_to_height": round(width / height, 5) if width else 0,
        }

    hair_rows = []
    for obj in hair_meshes:
        hair_low, hair_high = object_bounds(obj)
        hair_rows.append({
            "name": obj.name,
            "dims": [round(float(hair_high[index] - hair_low[index]), 5) for index in range(3)],
            "center": [round(float((hair_high[index] + hair_low[index]) * 0.5), 5) for index in range(3)],
        })

    return {
        "schema_version": 1,
        "created_at": now_iso(),
        "source_asset": rel(DEFAULT_ASSET),
        "reference_only_no_mesh_copying": True,
        "scene_bounds": {
            "low": [round(float(value), 5) for value in low],
            "high": [round(float(value), 5) for value in high],
            "height": round(height, 5),
            "center": [round(float(value), 5) for value in center],
        },
        "body_mesh": {
            "name": body_mesh.name,
            "vertices": len(body_mesh.data.vertices),
            "bounds_low": [round(float(value), 5) for value in body_low],
            "bounds_high": [round(float(value), 5) for value in body_high],
        },
        "body_core_band_widths": bands,
        "hair_meshes": hair_rows,
    }


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    asset = Path(argv[0]) if argv else DEFAULT_ASSET
    out_dir = Path(argv[1]) if len(argv) > 1 else DEFAULT_OUT
    if not asset.is_absolute():
        asset = ROOT / asset
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    if not asset.exists():
        raise SystemExit(f"missing asset: {asset}")
    out_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.import_scene.gltf(filepath=str(asset))

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise SystemExit("reference imported with no meshes")
    for obj in meshes:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        try:
            bpy.ops.object.shade_smooth()
        except RuntimeError:
            pass
        obj.select_set(False)

    low, high = scene_bounds(meshes)
    height = max(float(high.z - low.z), 0.001)
    center = (low + high) * 0.5
    head_center = Vector((center.x, center.y, high.z - height * 0.09))

    bpy.ops.object.light_add(type="AREA", location=(center.x, low.y - height * 1.2, high.z + height * 0.35))
    light = bpy.context.object
    light.name = "gwen_reference_measurement_light"
    light.data.energy = 700
    light.data.size = height * 1.6
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    bpy.context.scene.camera = camera

    try:
        bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        bpy.context.scene.render.engine = "BLENDER_EEVEE"
    bpy.context.scene.render.resolution_x = 1200
    bpy.context.scene.render.resolution_y = 1600
    bpy.context.scene.world.color = (0.18, 0.18, 0.18)

    views = {
        "front": render_view(out_dir / "reference_front.png", camera, Vector((center.x, low.y - height * 2.1, center.z)), center, height * 1.08),
        "side": render_view(out_dir / "reference_side.png", camera, Vector((high.x + height * 1.8, center.y, center.z)), center, height * 1.08),
        "back": render_view(out_dir / "reference_back.png", camera, Vector((center.x, high.y + height * 2.1, center.z)), center, height * 1.08),
        "head_front": render_view(out_dir / "reference_head_front.png", camera, Vector((center.x, low.y - height * 1.25, head_center.z)), head_center, height * 0.31),
        "head_side": render_view(out_dir / "reference_head_side.png", camera, Vector((high.x + height * 0.90, center.y, head_center.z)), head_center, height * 0.31),
    }
    report = measure_reference(meshes)
    report["views"] = views
    report_path = out_dir / "reference_measurements.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "report": rel(report_path), "views": views}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
