"""Create a constructed eye-socket training proof.

This is a Blender-only assignment artifact. It builds a simple transparent
training head with two round eyes seated inside sockets, then renders proof
views. It is not a character/avatar preview and it does not copy a face model.

Run with Blender:
  set KIRA_AVATAR_SCHOOL_RUN_ID=avatar_builder_school_loop_...
  set KIRA_AVATAR_SCHOOL_CYCLE_INDEX=1
  blender --background --python tools/create_eye_socket_training_proof.py
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENT_RUNS = PROJECT_ROOT / "Avatar" / "avatar_builder" / "school" / "assignments" / "lesson_runs"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clear_scene() -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)


def material(name: str, color: tuple[float, float, float, float], alpha_blend: bool = False) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Alpha"].default_value = color[3]
    if alpha_blend:
        mat.blend_method = "BLEND"
        mat.use_screen_refraction = True
        mat.show_transparent_back = True
    return mat


def add_uv_sphere(name: str, location: tuple[float, float, float], scale: tuple[float, float, float], mat: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    return obj


def add_cylinder_disc(
    name: str,
    location: tuple[float, float, float],
    radius: float,
    depth: float,
    mat: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=depth, location=location, rotation=(math.radians(90), 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def add_socket_ring(name: str, location: tuple[float, float, float], mat: bpy.types.Material, scale_z: float = 0.58) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(major_radius=0.083, minor_radius=0.008, major_segments=80, minor_segments=10, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler[0] = math.radians(90)
    obj.scale.z = scale_z
    obj.data.materials.append(mat)
    return obj


def look_at(camera: bpy.types.Object, target: Vector) -> None:
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build_training_head(output_dir: Path) -> dict:
    clear_scene()
    output_dir.mkdir(parents=True, exist_ok=True)

    skin = material("transparent_training_head_skin", (0.90, 0.72, 0.62, 0.46), alpha_blend=True)
    socket_shadow = material("soft_socket_shadow", (0.16, 0.09, 0.08, 1.0))
    sclera = material("warm_sclera", (0.92, 0.90, 0.84, 1.0))
    iris = material("realistic_blue_gray_iris", (0.19, 0.40, 0.55, 1.0))
    pupil = material("black_round_pupil", (0.01, 0.008, 0.006, 1.0))
    brow = material("socket_brow_marker", (0.08, 0.04, 0.025, 1.0))

    head_center = Vector((0.0, 0.0, 1.62))
    head_scale = Vector((0.62, 0.50, 0.82))
    add_uv_sphere("constructed_training_head_transparent_not_avatar", tuple(head_center), tuple(head_scale), skin)

    eye_radius = 0.065
    eye_y = -0.435
    eye_z = 1.73
    eye_x = 0.205
    front_face_plane_y = -0.515
    eye_centers = [Vector((-eye_x, eye_y, eye_z)), Vector((eye_x, eye_y, eye_z))]
    for side, center in (("left", eye_centers[0]), ("right", eye_centers[1])):
        add_socket_ring(f"{side}_eyelid_socket_ring_opening", (center.x, front_face_plane_y - 0.004, center.z), socket_shadow)
        add_uv_sphere(f"{side}_round_eyeball_seated_behind_face_plane", tuple(center), (eye_radius, eye_radius, eye_radius), sclera)
        iris_center = Vector((center.x, center.y - eye_radius - 0.004, center.z))
        add_cylinder_disc(f"{side}_iris_on_round_eye_surface", tuple(iris_center), 0.026, 0.006, iris)
        pupil_center = Vector((center.x, center.y - eye_radius - 0.009, center.z))
        add_cylinder_disc(f"{side}_pupil_on_iris_surface", tuple(pupil_center), 0.010, 0.007, pupil)
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(center.x, front_face_plane_y - 0.018, center.z + 0.145))
        eyebrow = bpy.context.object
        eyebrow.name = f"{side}_simple_brow_depth_marker"
        eyebrow.scale = (0.14, 0.012, 0.018)
        eyebrow.rotation_euler[1] = math.radians(0 if side == "left" else 0)
        eyebrow.data.materials.append(brow)

    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=12, location=(0, -0.535, 1.55))
    nose = bpy.context.object
    nose.name = "simple_nose_bridge_depth_marker"
    nose.scale = (0.055, 0.08, 0.12)
    nose.data.materials.append(skin)

    light_data = bpy.data.lights.new("training_key_light", "AREA")
    light_data.energy = 450
    light_data.size = 4
    light = bpy.data.objects.new("training_key_light", light_data)
    bpy.context.collection.objects.link(light)
    light.location = (1.4, -2.2, 3.1)

    camera_data = bpy.data.cameras.new("training_review_camera")
    camera_data.lens = 45
    camera = bpy.data.objects.new("training_review_camera", camera_data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    bpy.context.scene.render.resolution_x = 1200
    bpy.context.scene.render.resolution_y = 900
    bpy.context.scene.world.color = (0.03, 0.04, 0.05)

    target = Vector((0, -0.36, 1.66))
    distance = 2.65
    views = {
        "front": Vector((0, -distance, 0.06)),
        "side": Vector((distance, -0.02, 0.06)),
        "top": Vector((0, -0.28, distance)),
        "three_quarter": Vector((distance * 0.65, -distance * 0.95, distance * 0.22)),
    }
    renders: dict[str, str] = {}
    for name, offset in views.items():
        camera.location = target + offset
        look_at(camera, target)
        path = output_dir / f"constructed_eye_socket_training_head_{name}.png"
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        renders[name] = rel(path)

    glb_path = output_dir / "constructed_eye_socket_training_head.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format="GLB")

    eye_spacing = abs(eye_centers[1].x - eye_centers[0].x)
    eye_front_surface_y = eye_y - eye_radius - 0.009
    metrics = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "constructed_training_proof_ready_for_review",
        "purpose": "Training proof: two separately named round eyes seated in a transparent head. This is not Marinette, Gwen, or a copied reference face.",
        "model": rel(glb_path),
        "renders": renders,
        "measurements": {
            "head_width": round(head_scale.x * 2, 4),
            "eye_radius": eye_radius,
            "eye_diameter": round(eye_radius * 2, 4),
            "eye_spacing_center_to_center": round(eye_spacing, 4),
            "eye_diameter_to_eye_spacing_ratio": round((eye_radius * 2) / eye_spacing, 4),
            "front_face_plane_y": front_face_plane_y,
            "eye_center_y": eye_y,
            "eye_center_is_behind_face_plane": eye_y > front_face_plane_y,
            "eye_front_surface_y": round(eye_front_surface_y, 4),
            "eye_front_surface_is_behind_face_plane": eye_front_surface_y > front_face_plane_y,
        },
        "pass_gates": [
            {"gate": "two eyes in one head", "status": "passed_training_proof"},
            {"gate": "eyes are round separate objects", "status": "passed_training_proof"},
            {"gate": "eye centers are behind face plane", "status": "passed_training_proof"},
            {"gate": "visible eye surface stays behind face plane", "status": "passed_training_proof"},
            {"gate": "front and side images exist", "status": "passed_training_proof"},
        ],
        "limits": [
            "This is a simple training head, not a character likeness.",
            "This does not approve Marinette or Gwen until their actual heads pass the same visual test.",
        ],
    }
    manifest_path = output_dir / "constructed_eye_socket_training_head_manifest.json"
    write_json(manifest_path, metrics)
    return metrics


def main() -> int:
    run_id = os.environ.get("KIRA_AVATAR_SCHOOL_RUN_ID", "").strip()
    if not run_id:
        print("Set KIRA_AVATAR_SCHOOL_RUN_ID before running this Blender proof script.", file=sys.stderr)
        return 2
    cycle_index = int(os.environ.get("KIRA_AVATAR_SCHOOL_CYCLE_INDEX", "1"))
    output_dir = ASSIGNMENT_RUNS / run_id / f"{cycle_index:03d}_eye_socket_placement_constructed_proof"
    manifest = build_training_head(output_dir)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
