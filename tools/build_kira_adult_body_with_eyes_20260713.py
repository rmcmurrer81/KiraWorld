"""Build Kira's active adult base body with seated eye meshes.

This is a concrete repair pass for the Avatar Builder state where Kira's
adjustment record said eyes were queued, but the active avatar.glb still had
only the adult base body. The script intentionally uses Kira's approved adult
base body and generates new eye parts instead of copying a reference model.
"""

from __future__ import annotations

import json
import subprocess
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.avatar_body_policy_gate import (  # noqa: E402
    activate_staged_model_if_approved,
    enforce_body_policy,
)

BLENDER_EXE = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
BASE_BODY = ROOT / "Avatar" / "avatar_builder" / "asset_library" / "base_body_reference" / "womenfemale_body_base_rigged_3ec62ba8d7.glb"
BASE_BODY_SHA256 = "3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e"
ACTIVE_MODEL = ROOT / "Avatar" / "models" / "temp_ai" / "kira" / "avatar.glb"
ADJUSTMENTS = ROOT / "Avatar" / "temp_ai" / "kira" / "avatar_builder_adjustments.json"
ARTIFACT_ROOT = ROOT / "Avatar" / "avatar_builder" / "kira_adult_body_eye_passes"
ACTIVATION_APPROVAL = ARTIFACT_ROOT / "kira_runtime_activation_approval.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path | str) -> str:
    path = Path(path)
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return dict(default) if isinstance(default, dict) else default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def validate_kira_body_input() -> dict:
    return enforce_body_policy(
        project_root=ROOT,
        candidate_id="kira",
        body_treatment="neutral_adult_anatomy",
        selected_asset_paths=[BASE_BODY],
        expected_maturity_classes={"adult"},
        required_asset_sha256=BASE_BODY_SHA256,
        require_asset_evidence=True,
    )


BLENDER_WORKER = r'''
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy  # type: ignore
import mathutils  # type: ignore


def read_config() -> dict:
    import sys

    args = sys.argv
    if "--" not in args:
        raise SystemExit("Missing -- config path.")
    config_path = Path(args[args.index("--") + 1])
    return json.loads(config_path.read_text(encoding="utf-8"))


CONFIG = read_config()
PROJECT_ROOT = Path(CONFIG["project_root"])
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from tools.avatar_body_policy_gate import enforce_body_policy

SOURCE_BODY = Path(CONFIG["source_body"])
MODEL_OUT = Path(CONFIG["model_out"])
RENDER_DIR = Path(CONFIG["render_dir"])
MANIFEST_OUT = Path(CONFIG["manifest_out"])
TARGET_HEIGHT_M = float(CONFIG.get("target_height_m", 1.68))
CREATED_AT = CONFIG["created_at"]
BODY_POLICY_GATE = enforce_body_policy(
    project_root=PROJECT_ROOT,
    candidate_id="kira",
    body_treatment="neutral_adult_anatomy",
    selected_asset_paths=[SOURCE_BODY],
    expected_maturity_classes={"adult"},
    required_asset_sha256=CONFIG["source_body_sha256"],
    require_asset_evidence=True,
)


def clear_scene() -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)


def make_material(name: str, color, roughness: float = 0.55):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


def object_bounds(obj):
    points = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    return (
        mathutils.Vector(min(point[index] for point in points) for index in range(3)),
        mathutils.Vector(max(point[index] for point in points) for index in range(3)),
    )


def scene_bounds(ignore_generated: bool = True):
    points = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        if ignore_generated and obj.name.lower().startswith("kira_"):
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ mathutils.Vector(corner))
    if not points:
        zero = mathutils.Vector((0, 0, 0))
        return zero, zero
    return (
        mathutils.Vector(min(point[index] for point in points) for index in range(3)),
        mathutils.Vector(max(point[index] for point in points) for index in range(3)),
    )


def normalize_scene(target_height: float) -> None:
    low, high = scene_bounds()
    height = max(high.z - low.z, 0.001)
    center = mathutils.Vector(((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, low.z))
    scale = target_height / height
    if 0.05 <= scale <= 25.0:
        for obj in list(bpy.context.scene.objects):
            if obj.parent is None:
                obj.location = (obj.location - center) * scale
                obj.scale *= scale
    bpy.context.view_layer.update()


def primary_body_object():
    meshes = [
        obj
        for obj in bpy.context.scene.objects
        if (
            obj.type == "MESH"
            and not obj.name.lower().startswith("kira_")
            and len(obj.data.vertices) > 1000
            and obj.name.lower() not in {"cube", "icosphere", "sphere"}
        )
    ]
    if not meshes:
        raise RuntimeError("No body mesh was imported.")
    return max(meshes, key=lambda obj: len(obj.data.vertices))


def mesh_world_vertices(obj) -> list:
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def points_bounds(points):
    if not points:
        zero = mathutils.Vector((0, 0, 0))
        return zero, zero
    return (
        mathutils.Vector(min(point[index] for point in points) for index in range(3)),
        mathutils.Vector(max(point[index] for point in points) for index in range(3)),
    )


def percentile(values: list[float], ratio: float, fallback: float) -> float:
    if not values:
        return fallback
    values = sorted(values)
    index = min(len(values) - 1, max(0, int(round((len(values) - 1) * ratio))))
    return float(values[index])


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def vector_list(value) -> list[float]:
    return [round(float(value[0]), 6), round(float(value[1]), 6), round(float(value[2]), 6)]


def remove_previous_generated_parts() -> list[str]:
    removed = []
    prefixes = (
        "kira_left_",
        "kira_right_",
        "kira_adult_eye_",
        "kira_eye_",
        "kira_head_look_",
        "kira_body_control_",
    )
    for obj in list(bpy.context.scene.objects):
        lowered = obj.name.lower()
        low_vertex_helper = (
            obj.type == "MESH"
            and lowered in {"cube", "icosphere", "sphere"}
            and len(obj.data.vertices) <= 128
        )
        if obj.name.lower().startswith(prefixes) or low_vertex_helper:
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    return removed


def measure_landmarks(body_obj) -> dict:
    verts = mesh_world_vertices(body_obj)
    low, high = points_bounds(verts)
    height = max(high.z - low.z, 0.001)
    body_center_x = (low.x + high.x) * 0.5
    body_center_y = (low.y + high.y) * 0.5
    head_floor = high.z - height * 0.20
    head_points = [
        point
        for point in verts
        if (
            point.z >= head_floor
            and abs(point.x - body_center_x) <= height * 0.14
            and abs(point.y - body_center_y) <= height * 0.12
        )
    ]
    if len(head_points) < 200:
        head_floor = high.z - height * 0.24
        head_points = [
            point
            for point in verts
            if (
                point.z >= head_floor
                and abs(point.x - body_center_x) <= height * 0.18
                and abs(point.y - body_center_y) <= height * 0.16
            )
        ]
    if len(head_points) < 24:
        head_points = [point for point in verts if point.z >= high.z - height * 0.22]
    head_low, head_high = points_bounds(head_points)
    head_height = max(head_high.z - head_low.z, height * 0.13)
    head_width = max(head_high.x - head_low.x, height * 0.09)
    head_depth = max(head_high.y - head_low.y, height * 0.08)
    center_x = body_center_x
    center_y = (head_low.y + head_high.y) * 0.5
    eye_band = [
        point
        for point in verts
        if (
            low.z + height * 0.885 <= point.z <= low.z + height * 0.955
            and abs(point.x - center_x) <= max(head_width * 0.62, height * 0.055)
            and abs(point.y - body_center_y) <= max(head_depth * 0.75, height * 0.065)
        )
    ]
    face_front_y = percentile([point.y for point in (eye_band or head_points)], 0.05, body_center_y - head_depth * 0.48)

    face_width = clamp(head_width * 0.62, height * 0.095, height * 0.135)
    eye_z = head_low.z + head_height * 0.73
    eye_x_offset = clamp(face_width * 0.18, height * 0.020, height * 0.029)
    eye_radius = clamp(height * 0.0066, 0.0070, 0.0089)
    x_window = max(face_width * 0.15, eye_radius * 2.6)
    z_window = max(height * 0.030, eye_radius * 2.8)

    eyes = {}
    warnings = []
    for side, x_sign in (("left", -1.0), ("right", 1.0)):
        target_x = center_x + eye_x_offset * x_sign
        samples = [
            point
            for point in head_points
            if abs(point.x - target_x) <= x_window and abs(point.z - eye_z) <= z_window
        ]
        if samples:
            surface_y = percentile([point.y for point in samples], 0.08, face_front_y)
            sampled_eye_z = sum(point.z for point in samples) / len(samples)
            center_z = eye_z * 0.78 + sampled_eye_z * 0.22
        else:
            surface_y = face_front_y
            center_z = eye_z
            warnings.append(f"{side} eye used ratio fallback; socket samples were sparse.")
        center = mathutils.Vector((target_x, surface_y + eye_radius * 1.92, center_z))
        eyes[side] = {
            "center": vector_list(center),
            "socket_surface_y": round(float(surface_y), 6),
            "radius": round(float(eye_radius), 6),
            "sample_count": len(samples),
            "look_target": vector_list((center.x, center.y - eye_radius * 15.0, center.z)),
            "front_surface_clearance": round(float((center.y - eye_radius) - surface_y), 6),
            "iris_radius": round(float(eye_radius * 0.40), 6),
            "pupil_radius": round(float(eye_radius * 0.18), 6),
        }

    mouth_z = head_low.z + head_height * 0.405
    mouth_samples = [
        point
        for point in head_points
        if abs(point.x - center_x) <= head_width * 0.18 and abs(point.z - mouth_z) <= head_height * 0.09
    ]
    mouth_surface_y = percentile([point.y for point in mouth_samples], 0.06, face_front_y)
    return {
        "created_at": CREATED_AT,
        "candidate_id": "kira",
        "method": "Measured Kira's active adult base body/head bounds and seated generated eyes from head/eye-band landmarks.",
        "front_axis": "negative_y",
        "body": {
            "bounds_low": vector_list(low),
            "bounds_high": vector_list(high),
            "height": round(float(height), 6),
        },
        "head": {
            "bounds_low": vector_list(head_low),
            "bounds_high": vector_list(head_high),
            "center": vector_list((center_x, center_y, (head_low.z + head_high.z) * 0.5)),
            "width": round(float(head_width), 6),
            "face_width_estimate": round(float(face_width), 6),
            "depth": round(float(head_depth), 6),
            "height": round(float(head_height), 6),
            "face_front_y": round(float(face_front_y), 6),
            "eye_band_sample_count": len(eye_band),
            "sample_count": len(head_points),
        },
        "eyes": eyes,
        "eye_measurements": {
            "center_spacing": round(float(abs(eyes["right"]["center"][0] - eyes["left"]["center"][0])), 6),
            "diameter": round(float(eye_radius * 2.0), 6),
            "diameter_to_head_width": round(float((eye_radius * 2.0) / head_width), 6),
            "placement_rule": "Round eye spheres are set behind the sampled face front so they sit inside sockets instead of floating ahead of the head.",
        },
        "mouth": {
            "surface_y": round(float(mouth_surface_y), 6),
            "estimated_center": vector_list((center_x, mouth_surface_y + eye_radius * 0.30, mouth_z)),
            "single_mouth_rule": "No visible second/debug mouth was generated in this Kira eye/body pass.",
        },
        "warnings": warnings,
    }


def add_anchor(name: str, location, size: float) -> None:
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "SPHERE"
    empty.empty_display_size = size
    empty.location = location
    bpy.context.collection.objects.link(empty)


def add_uv_ellipsoid(name: str, location, scale, material, segments: int = 32):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=max(8, segments // 2),
        radius=1.0,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_mesh"
    obj.scale = scale
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def add_eye_system(landmarks: dict) -> list[str]:
    sclera = make_material("kira_warm_white_round_sclera_adult_base", (0.94, 0.925, 0.89, 1), 0.36)
    iris = make_material("kira_realistic_warm_brown_iris_adult_base", (0.24, 0.125, 0.055, 1), 0.30)
    pupil = make_material("kira_round_black_pupil_adult_base", (0.002, 0.002, 0.002, 1), 0.22)
    catchlight = make_material("kira_eye_soft_catchlight_adult_base", (1.0, 0.98, 0.92, 1), 0.18)
    names = []
    for side in ("left", "right"):
        eye = landmarks["eyes"][side]
        loc = tuple(eye["center"])
        radius = float(eye["radius"])
        look = tuple(eye["look_target"])
        add_anchor(f"kira_{side}_eye_socket_anchor_adult_base", loc, 0.010)
        add_anchor(f"kira_{side}_eye_look_target_adult_base", look, 0.010)
        sclera_obj = add_uv_ellipsoid(
            f"kira_{side}_round_eye_sclera_adult_base",
            loc,
            (radius, radius, radius),
            sclera,
            48,
        )
        iris_obj = add_uv_ellipsoid(
            f"kira_{side}_warm_brown_iris_adult_base",
            (loc[0], loc[1] - radius * 1.018, loc[2]),
            (radius * 0.40, radius * 0.018, radius * 0.40),
            iris,
            32,
        )
        pupil_obj = add_uv_ellipsoid(
            f"kira_{side}_round_pupil_adult_base",
            (loc[0], loc[1] - radius * 1.036, loc[2]),
            (radius * 0.18, radius * 0.010, radius * 0.18),
            pupil,
            24,
        )
        add_uv_ellipsoid(
            f"kira_{side}_eye_catchlight_adult_base",
            (loc[0] - radius * 0.18, loc[1] - radius * 1.046, loc[2] + radius * 0.22),
            (radius * 0.060, radius * 0.006, radius * 0.060),
            catchlight,
            12,
        )
        names.extend(
            [
                f"kira_{side}_eye_socket_anchor_adult_base",
                f"kira_{side}_eye_look_target_adult_base",
                sclera_obj.name,
                iris_obj.name,
                pupil_obj.name,
                f"kira_{side}_eye_catchlight_adult_base",
            ]
        )
    return names


def add_body_metadata(body_obj, landmarks: dict) -> None:
    body_obj.name = "kira_adult_base_body_with_generated_eyes"
    body_obj.data.name = "kira_adult_base_body_with_generated_eyes_mesh"
    body_obj["candidate_id"] = "kira"
    body_obj["maturity_policy"] = "adult"
    body_obj["adult_base_body_preserved"] = True
    body_obj["eye_system"] = "generated round brown eyes seated from measured head landmarks"
    body_obj["single_mouth_rule"] = "no second visible mouth generated"
    body_obj["landmark_report"] = json.dumps(landmarks)


def look_at(obj, target) -> None:
    direction = mathutils.Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_lights_and_camera():
    bpy.ops.object.light_add(type="AREA", location=(0, -3.0, 3.0))
    key = bpy.context.object
    key.name = "kira_eye_pass_key_light"
    key.data.energy = 450
    key.data.size = 5
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "kira_eye_pass_camera"
    bpy.context.scene.camera = camera
    return camera


def set_camera(camera, location, target, ortho_scale):
    camera.location = location
    look_at(camera, target)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho_scale


def render_view(name: str, camera, location, target, ortho_scale) -> str:
    set_camera(camera, location, target, ortho_scale)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / f"{name}.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return str(path)


def main() -> None:
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(SOURCE_BODY))
    removed = remove_previous_generated_parts()
    # Keep the base in its native coordinate space. The first Kira eye pass
    # normalized through an imported parent transform and produced bad landmark
    # axes, which put an eye outside the head. The runtime already uses this
    # base body successfully, so this pass preserves scale and fits eyes in the
    # measured native head/eye band.
    body_obj = primary_body_object()
    skin = make_material("kira_adult_base_neutral_skin", (0.80, 0.66, 0.58, 1), 0.58)
    body_obj.data.materials.clear()
    body_obj.data.materials.append(skin)
    bpy.context.view_layer.update()
    landmarks = measure_landmarks(body_obj)
    eye_parts = add_eye_system(landmarks)
    add_body_metadata(body_obj, landmarks)

    low, high = scene_bounds(ignore_generated=False)
    body_center = (
        (landmarks["body"]["bounds_low"][0] + landmarks["body"]["bounds_high"][0]) * 0.5,
        (landmarks["body"]["bounds_low"][1] + landmarks["body"]["bounds_high"][1]) * 0.5,
        (landmarks["body"]["bounds_low"][2] + landmarks["body"]["bounds_high"][2]) * 0.54,
    )
    head_center = tuple(landmarks["head"]["center"])
    eye_mid = (
        (landmarks["eyes"]["left"]["center"][0] + landmarks["eyes"]["right"]["center"][0]) * 0.5,
        (landmarks["eyes"]["left"]["center"][1] + landmarks["eyes"]["right"]["center"][1]) * 0.5,
        (landmarks["eyes"]["left"]["center"][2] + landmarks["eyes"]["right"]["center"][2]) * 0.5,
    )
    add_anchor("kira_body_control_root_adult_base", body_center, 0.035)
    add_anchor("kira_head_look_control_adult_base", (head_center[0], head_center[1] - 0.16, eye_mid[2]), 0.022)

    camera = add_lights_and_camera()
    try:
        bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        bpy.context.scene.render.engine = "BLENDER_EEVEE"
    bpy.context.scene.render.resolution_x = 1000
    bpy.context.scene.render.resolution_y = 1300
    if hasattr(bpy.context.scene, "eevee"):
        bpy.context.scene.eevee.taa_render_samples = 32
    bpy.context.scene.world.color = (0.025, 0.03, 0.035)

    views = {
        "front_body": render_view("front_body", camera, (body_center[0], -4.0, body_center[2]), body_center, 1.85),
        "side_body": render_view("side_body", camera, (4.0, body_center[1], body_center[2]), body_center, 1.85),
        "head_front": render_view("head_front", camera, (head_center[0], -2.0, eye_mid[2]), (head_center[0], head_center[1], eye_mid[2]), 0.48),
        "eye_front": render_view("eye_front", camera, (eye_mid[0], -1.1, eye_mid[2]), eye_mid, 0.18),
        "eye_side": render_view("eye_side", camera, (0.65, -0.95, eye_mid[2]), eye_mid, 0.20),
    }

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(MODEL_OUT),
        export_format="GLB",
        export_apply=True,
        export_yup=True,
        export_animations=False,
        export_morph=True,
    )
    manifest = {
        "schema_version": 1,
        "created_at": CREATED_AT,
        "candidate_id": "kira",
        "status": "adult_base_body_with_generated_eyes_staged_needs_robert_review",
        "model": str(MODEL_OUT),
        "source_body": str(SOURCE_BODY),
        "body_policy_validation": BODY_POLICY_GATE,
        "maturity_policy": "adult",
        "adult_body_preserved": True,
        "generated_eye_parts": eye_parts,
        "removed_previous_generated_parts": removed,
        "landmark_report": landmarks,
        "views": views,
        "scene_bounds": {"low": vector_list(low), "high": vector_list(high)},
        "known_limits": [
            "This gives Kira generated eye meshes on the adult base; it is not a final likeness sculpt or approved body.",
            "Robert's 2026-07-14 review rejected the previous pass because the eyes were too small/not seated enough and the body still read as Barbie/generic.",
            "The adult body still needs the Avatar Builder adult anatomy masterclass and movement self-training curriculum before approval.",
            "Hair, clothing, and detailed expression rigging are separate later passes.",
            "No copied reference body or reference eye model was used as Kira's body.",
        ],
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


main()
'''


def create_contact_sheet(run_dir: Path, manifest: dict) -> Path | None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None

    views = manifest.get("views", {})
    keys = ["front_body", "side_body", "head_front", "eye_front", "eye_side"]
    tile_w, tile_h = 330, 390
    header_h = 52
    sheet = Image.new("RGB", (tile_w * 3, tile_h * 2 + header_h), (10, 20, 30))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 18)
        small = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font = ImageFont.load_default()
        small = ImageFont.load_default()
    draw.text((16, 16), "Kira adult base body + generated brown eyes", fill=(232, 244, 250), font=font)
    for index, key in enumerate(keys):
        source = Path(views.get(key, ""))
        x = (index % 3) * tile_w
        y = header_h + (index // 3) * tile_h
        draw.rectangle((x + 8, y + 8, x + tile_w - 8, y + tile_h - 8), outline=(48, 90, 125), width=2)
        if source.exists():
            with Image.open(source) as img:
                img = img.convert("RGB")
                img.thumbnail((tile_w - 28, tile_h - 58))
                sheet.paste(img, (x + (tile_w - img.width) // 2, y + 18))
        draw.text((x + 16, y + tile_h - 28), key, fill=(210, 230, 240), font=small)
    out = run_dir / "kira_adult_body_eyes_contact_sheet.png"
    sheet.save(out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Kira's adult-body eye pass.")
    activation_group = parser.add_mutually_exclusive_group()
    activation_group.add_argument(
        "--activate",
        action="store_true",
        help="Deprecated fail-closed flag; use --activate-staged with an exact approval artifact.",
    )
    activation_group.add_argument(
        "--activate-staged",
        type=Path,
        help="Activate an already reviewed staged GLB without rebuilding it.",
    )
    parser.add_argument(
        "--approval-artifact",
        type=Path,
        default=ACTIVATION_APPROVAL,
        help="Approval JSON tied to the exact staged model path and SHA-256.",
    )
    args = parser.parse_args()

    if args.activate:
        raise SystemExit(
            "The legacy --activate path is disabled. Build a staged review pass first, "
            "then use --activate-staged PATH with an exact-hash approval artifact."
        )

    body_policy_gate = validate_kira_body_input()
    if not BASE_BODY.exists():
        raise SystemExit(f"Missing adult base body: {BASE_BODY}")
    if args.activate_staged:
        staged_model = args.activate_staged
        if not staged_model.is_absolute():
            staged_model = ROOT / staged_model
        staged_model = staged_model.resolve()
        try:
            staged_model.relative_to(ARTIFACT_ROOT.resolve())
        except ValueError as exc:
            raise SystemExit(
                f"Kira activation is limited to staged builder output under {ARTIFACT_ROOT}."
            ) from exc
        if staged_model.suffix.lower() != ".glb" or not staged_model.is_file():
            raise SystemExit(f"Missing staged Kira GLB: {staged_model}")
        approval_artifact = args.approval_artifact
        if not approval_artifact.is_absolute():
            approval_artifact = ROOT / approval_artifact
        backup_path = ACTIVE_MODEL.with_name(
            f"avatar_before_kira_approved_activation_{stamp()}.glb"
        )
        activation = activate_staged_model_if_approved(
            project_root=ROOT,
            candidate_id="kira",
            staged_model=staged_model,
            live_model=ACTIVE_MODEL,
            approval_artifact=approval_artifact,
            activation_requested=True,
            backup_path=backup_path,
        )
        write_json(
            ARTIFACT_ROOT / "kira_runtime_activation_last.json",
            {
                **activation,
                "body_policy_validation": body_policy_gate,
                "activated_at": now_iso(),
            },
        )
        print(json.dumps(activation, indent=2))
        return 0
    if not BLENDER_EXE.exists():
        raise SystemExit(f"Missing Blender: {BLENDER_EXE}")

    run_id = f"kira_adult_body_eyes_{stamp()}"
    run_dir = ARTIFACT_ROOT / run_id
    render_dir = run_dir / "renders"
    model_out = run_dir / "kira_adult_body_with_eyes.glb"
    manifest_out = run_dir / "kira_adult_body_eyes_manifest.json"
    config_path = run_dir / "kira_adult_body_eyes_blender_config.json"
    worker_path = run_dir / "_kira_adult_body_eyes_blender_worker.py"
    run_dir.mkdir(parents=True, exist_ok=True)

    created_at = now_iso()
    write_json(
        config_path,
        {
            "project_root": str(ROOT),
            "source_body": str(BASE_BODY),
            "source_body_sha256": BASE_BODY_SHA256,
            "model_out": str(model_out),
            "render_dir": str(render_dir),
            "manifest_out": str(manifest_out),
            "target_height_m": 1.68,
            "created_at": created_at,
        },
    )
    worker_path.write_text(BLENDER_WORKER, encoding="utf-8")

    subprocess.run(
        [str(BLENDER_EXE), "-b", "--python", str(worker_path), "--", str(config_path)],
        cwd=str(ROOT),
        check=True,
    )
    # Re-check after Blender finishes and before any optional live replacement.
    body_policy_gate = validate_kira_body_input()

    manifest = read_json(manifest_out, {})
    contact_sheet = create_contact_sheet(run_dir, manifest)

    activation = activate_staged_model_if_approved(
        project_root=ROOT,
        candidate_id="kira",
        staged_model=model_out,
        live_model=ACTIVE_MODEL,
        approval_artifact=args.approval_artifact,
        activation_requested=False,
    )

    active_manifest = {
        "schema_version": 1,
        "created_at": created_at,
        "active_model": rel(ACTIVE_MODEL),
        "active_model_replaced": bool(activation["active_model_replaced"]),
        "backup_model": "",
        "review_model": rel(model_out),
        "manifest": rel(manifest_out),
        "contact_sheet": rel(contact_sheet) if contact_sheet else "",
        "maturity_policy": "adult",
        "body_policy_validation": body_policy_gate,
        "adult_body_preserved": True,
        "eye_color": "warm brown",
        "single_mouth_rule": "no second visible/debug mouth generated",
        "approval_status": "staged_not_approved_until_robert_reviews_eye_socket_fit_and_adult_body",
        "activation": activation,
        "activation_instructions": "Use --activate-staged with a separate exact-path/exact-SHA approval artifact only after the visual pass is approved.",
    }
    write_json(run_dir / "kira_active_model_replacement.json", active_manifest)

    adjustments = read_json(ADJUSTMENTS, {})
    adjustments.setdefault("candidate_id", "kira")
    adjustments["label"] = adjustments.get("label") or "Kira"
    adjustments["maturity_policy"] = "adult"
    adjustments["anatomy_assets"] = "adult anatomy allowed"
    adjustments["runtime_body"] = "rigged_adult_body_clean_runtime_ready_eye_pass_staged"
    adjustments["builder_status"] = "kira_runtime_stable_eye_pass_staged_for_review_not_activated"
    adjustments["eye_plan"] = rel(manifest_out)
    adjustments["adult_body_fit_plan"] = adjustments.get("adult_body_fit_plan") or "Avatar/avatar_builder/body_training/body_fit_plans/kira_adult_body_fit_plan.json"
    adjustments["latest_kira_adult_body_eye_pass"] = active_manifest
    adjustments["updated_at"] = created_at
    adjustments["review_notes"] = [
        "Kira's active avatar.glb was not replaced; this eye/body pass is staged for review.",
        "The active runtime model remains the clean adult base so live sessions do not pick up broken eye attempts.",
        "Runtime activation requires a separate approval artifact matching the exact staged path and SHA-256.",
        "This is an adult-body eye pass, not a final Kira likeness/clothing/hair pass.",
    ]
    write_json(ADJUSTMENTS, adjustments)

    print(
        json.dumps(
            {
                "ok": True,
                "active_model": rel(ACTIVE_MODEL),
                "active_model_replaced": bool(activation["active_model_replaced"]),
                "backup_model": "",
                "manifest": rel(manifest_out),
                "contact_sheet": rel(contact_sheet) if contact_sheet else "",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
