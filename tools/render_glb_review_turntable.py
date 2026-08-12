"""Render an exact-hash, private clothed-avatar diagnostic turntable in Blender.

This is a review/proof helper, not a readiness or activation authority.  It
renders only a supplied GLB already inside the project and records the exact
model/render hashes plus explicit unproven capability flags.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INACTIVE_CANDIDATE_ROOTS = (
    PROJECT_ROOT / "Avatar" / "temp_ai",
    PROJECT_ROOT / "Avatar" / "models" / "temp_ai",
    PROJECT_ROOT / "Avatar" / "avatar_builder" / "candidate_sources",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_file(value: str, *, must_exist: bool) -> Path:
    raw = Path(value)
    path = raw.resolve() if raw.is_absolute() else (PROJECT_ROOT / raw).resolve()
    path.relative_to(PROJECT_ROOT.resolve())
    if must_exist and (not path.is_file() or path.is_symlink()):
        raise ValueError(f"missing or symlinked project file: {path.name}")
    return path


def inactive_candidate_root(model_path: Path) -> Path:
    for allowed_root in INACTIVE_CANDIDATE_ROOTS:
        try:
            relative = model_path.relative_to(allowed_root.resolve())
        except ValueError:
            continue
        if not relative.parts:
            break
        return allowed_root.resolve() / relative.parts[0]
    raise ValueError("review model must be inside an inactive Avatar candidate root")


def project_directory(value: str, *, candidate_root: Path) -> Path:
    raw = Path(value)
    path = raw.resolve() if raw.is_absolute() else (PROJECT_ROOT / raw).resolve()
    path.relative_to(PROJECT_ROOT.resolve())
    relative = path.relative_to(candidate_root.resolve())
    if not relative.parts or relative.parts[0].lower() != "private_review":
        raise ValueError("review output must be under the candidate private_review directory")
    if path.exists():
        raise ValueError("review output directory already exists; evidence is append-only")
    return path


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def scene_bounds(*, name_tokens: tuple[str, ...] = ()) -> tuple[Vector, Vector]:
    points: list[Vector] = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or obj.get("private_diagnostic_helper") is True:
            continue
        if name_tokens and not any(token in obj.name.lower() for token in name_tokens):
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    if not points:
        raise ValueError("imported GLB has no mesh bounds")
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def helper_material() -> bpy.types.Material:
    material = bpy.data.materials.get("private_diagnostic_helper_material")
    if material is None:
        material = bpy.data.materials.new("private_diagnostic_helper_material")
        material.diffuse_color = (0.22, 0.25, 0.30, 1.0)
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = material.diffuse_color
            bsdf.inputs["Roughness"].default_value = 0.82
    return material


def add_helper_box(
    name: str,
    *,
    center: Vector,
    size: Vector,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=center)
    obj = bpy.context.object
    obj.name = name
    obj.scale = tuple(max(0.001, float(value) * 0.5) for value in size)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(helper_material())
    obj["private_diagnostic_helper"] = True
    obj["runtime_artifact"] = False
    return obj


def remove_diagnostic_helpers() -> None:
    for obj in list(bpy.context.scene.objects):
        if obj.get("private_diagnostic_helper") is True:
            bpy.data.objects.remove(obj, do_unlink=True)


def add_ground_helper(
    bounds_min: Vector,
    bounds_max: Vector,
    *,
    ground_z: float,
) -> dict[str, object]:
    height = max(0.5, bounds_max.z - bounds_min.z)
    center = (bounds_min + bounds_max) * 0.5
    thickness = height * 0.012
    add_helper_box(
        "private_diagnostic_ground_plane",
        center=Vector((center.x, center.y, ground_z - thickness * 0.5)),
        size=Vector((height * 1.25, height * 1.25, thickness)),
    )
    return {
        "ground_plane_present": True,
        "ground_top_z_m": round(float(ground_z), 6),
        "ground_placement": "aligned_to_current_posed_shoe_minimum_only",
        "foot_contact_proven": False,
    }


def add_supported_seat_helper(
    bounds_min: Vector,
    bounds_max: Vector,
    *,
    ground_z: float,
) -> dict[str, object]:
    height = max(0.5, bounds_max.z - bounds_min.z)
    center = (bounds_min + bounds_max) * 0.5
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    pelvis_z = bounds_min.z + height * 0.56
    if armatures:
        pelvis = armatures[0].pose.bones.get("pelvis")
        if pelvis is not None:
            pelvis_z = float((armatures[0].matrix_world @ pelvis.head).z)
    seat_width = height * 0.32
    seat_depth = height * 0.21
    seat_thickness = height * 0.035
    seat_top = pelvis_z - height * 0.105
    seat_center_y = center.y + height * 0.105
    add_helper_box(
        "private_diagnostic_seat",
        center=Vector((center.x, seat_center_y, seat_top - seat_thickness * 0.5)),
        size=Vector((seat_width, seat_depth, seat_thickness)),
    )
    back_height = height * 0.34
    add_helper_box(
        "private_diagnostic_seat_back",
        center=Vector(
            (
                center.x,
                seat_center_y + seat_depth * 0.48,
                seat_top + back_height * 0.46,
            )
        ),
        size=Vector((seat_width, height * 0.025, back_height)),
    )
    leg_height = max(height * 0.04, seat_top - ground_z)
    for x_sign in (-1.0, 1.0):
        for y_sign in (-1.0, 1.0):
            add_helper_box(
                f"private_diagnostic_seat_leg_{x_sign:+.0f}_{y_sign:+.0f}",
                center=Vector(
                    (
                        center.x + x_sign * seat_width * 0.38,
                        seat_center_y + y_sign * seat_depth * 0.34,
                        ground_z + leg_height * 0.5,
                    )
                ),
                size=Vector((height * 0.025, height * 0.025, leg_height)),
            )
    return {
        "supported_seat_present": True,
        "seat_top_z_m": round(float(seat_top), 6),
        "seat_placement": "pelvis-relative_visual_diagnostic_helper",
        "seat_contact_proven": False,
        "load_bearing_or_collision_proven": False,
    }


def add_lighting(center: Vector, span: float) -> None:
    specs = [
        ((-0.7, -1.2, 1.2), 850.0, 3.2),
        ((0.9, -0.5, 0.8), 520.0, 2.6),
        ((0.2, 1.0, 1.4), 650.0, 3.0),
    ]
    for index, (direction, energy, size) in enumerate(specs, start=1):
        location = center + Vector(direction) * span
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = f"private_review_light_{index}"
        light.data.energy = energy
        light.data.size = size
        look_at(light, center)


def render_view(
    *,
    camera: bpy.types.Object,
    center: Vector,
    span: float,
    direction: Vector,
    output_path: Path,
) -> None:
    camera.location = center + direction.normalized() * span * 2.8
    look_at(camera, center)
    bpy.context.scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)


def select_action(action_token: str | None) -> dict[str, object]:
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if not armatures or not action_token:
        for armature in armatures:
            if armature.animation_data:
                armature.animation_data.action = None
        bpy.context.scene.frame_set(1)
        return {"action": "rest", "frame": 1}
    matches = [action for action in bpy.data.actions if action_token in action.name.lower()]
    if not matches:
        return {"action": action_token, "frame": None, "available": False}
    action = sorted(matches, key=lambda item: item.name)[0]
    armature = armatures[0]
    armature.animation_data_create()
    armature.animation_data.action = action
    start, end = (float(value) for value in action.frame_range)
    # Reach actions commonly return to rest at their final keyframe.  Walk is
    # more informative at the opposite-stride midpoint.  Sit is intentionally
    # sampled at its final seated pose.
    frame = int(round(end if action_token == "sit" else (start + end) * 0.5))
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return {"action": action.name, "frame": frame, "available": True}


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(argv) != 3:
        raise SystemExit(
            "usage: blender --background --python tools/render_glb_review_turntable.py "
            "-- model.glb output_directory file_prefix"
        )
    model_path = project_file(argv[0], must_exist=True)
    if model_path.suffix.lower() != ".glb":
        raise ValueError("review model must be a GLB")
    if "clothed" not in model_path.stem.lower() or "review" not in model_path.stem.lower():
        raise ValueError("private diagnostic input must be an explicitly named clothed-review assembly")
    candidate_root = inactive_candidate_root(model_path)
    prefix = argv[2].strip().lower()
    if not prefix or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789_" for character in prefix):
        raise ValueError("review prefix must be a safe lowercase identifier")
    output_dir = project_directory(argv[1], candidate_root=candidate_root)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(model_path))
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            for polygon in obj.data.polygons:
                polygon.use_smooth = True

    mesh_names = sorted(obj.name for obj in bpy.context.scene.objects if obj.type == "MESH")
    normalized_names = [name.lower() for name in mesh_names]
    body_meshes = [name for name in mesh_names if "body_surface" in name.lower()]
    clothing_tokens = (
        "clothes",
        "garment",
        "outfit",
        "top",
        "shirt",
        "pants",
        "trouser",
        "skirt",
        "dress",
        "robe",
        "shoe",
        "collar",
    )
    clothing_meshes = [
        name
        for name, normalized in zip(mesh_names, normalized_names)
        if any(token in normalized for token in clothing_tokens)
    ]
    armatures = sorted(obj.name for obj in bpy.context.scene.objects if obj.type == "ARMATURE")
    if not body_meshes:
        raise ValueError("clothed-review assembly has no explicit body-surface mesh")
    if not clothing_meshes:
        raise ValueError("clothed-review assembly has no explicit clothing mesh")
    if not armatures:
        raise ValueError("clothed-review assembly has no armature")
    output_dir.mkdir(parents=True, exist_ok=False)
    snapshot_path = output_dir / f"{prefix}_clothed_review_model_snapshot.glb"
    with model_path.open("rb") as source, snapshot_path.open("xb") as destination:
        shutil.copyfileobj(source, destination, length=1024 * 1024)
    input_model_sha256 = sha256_file(model_path)
    if sha256_file(snapshot_path) != input_model_sha256:
        raise ValueError("private review model snapshot hash mismatch")

    bounds_min, bounds_max = scene_bounds()
    center = (bounds_min + bounds_max) * 0.5
    extents = bounds_max - bounds_min
    span = max(extents.x, extents.y, extents.z, 0.5)
    add_lighting(center, span)
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "private_review_camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(extents.z * 1.08, extents.x * 1.08)
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    # Blender 5.1 exposes the Eevee engine under the stable BLENDER_EEVEE enum.
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.055, 0.065, 0.08)

    views = {
        "front": Vector((0.0, -1.0, 0.0)),
        "front_three_quarter": Vector((0.72, -1.0, 0.12)),
        "left_profile": Vector((1.0, 0.0, 0.0)),
        "back": Vector((0.0, 1.0, 0.0)),
    }
    renders: list[dict[str, object]] = []
    select_action(None)
    for label, direction in views.items():
        remove_diagnostic_helpers()
        posed_min, posed_max = scene_bounds()
        shoe_min, _shoe_max = scene_bounds(name_tokens=("shoe",))
        helpers = add_ground_helper(posed_min, posed_max, ground_z=float(shoe_min.z))
        path = output_dir / f"{prefix}_{label}.png"
        render_view(camera=camera, center=center, span=span, direction=direction, output_path=path)
        renders.append(
            {
                "view": label,
                "pose": "rest",
                "path": path.name,
                "sha256": sha256_file(path),
                "diagnostic_helpers": helpers,
            }
        )

    for token in ("walk", "sit", "reach"):
        remove_diagnostic_helpers()
        pose = select_action(token)
        if pose.get("available") is not True:
            continue
        posed_min, posed_max = scene_bounds()
        shoe_min, _shoe_max = scene_bounds(name_tokens=("shoe",))
        ground_z = float(shoe_min.z)
        helpers = add_ground_helper(posed_min, posed_max, ground_z=ground_z)
        if token == "sit":
            helpers.update(
                add_supported_seat_helper(
                    posed_min,
                    posed_max,
                    ground_z=ground_z,
                )
            )
        path = output_dir / f"{prefix}_{token}_diagnostic.png"
        render_view(
            camera=camera,
            center=center,
            span=span,
            direction=views["front_three_quarter"],
            output_path=path,
        )
        renders.append(
            {
                "view": "front_three_quarter",
                "pose": token,
                "action": pose["action"],
                "frame": pose["frame"],
                "path": path.name,
                "sha256": sha256_file(path),
                "diagnostic_helpers": helpers,
            }
        )

    proof = {
        "schema_version": 1,
        "artifact_type": "private_clothed_avatar_visual_diagnostic",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": {
            "project_path": snapshot_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": input_model_sha256,
            "byte_identical_private_snapshot": True,
        },
        "input_model": {
            "project_path": model_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256_at_render_time": input_model_sha256,
        },
        "import_inventory": {
            "mesh_object_count": len(mesh_names),
            "body_mesh_count": len(body_meshes),
            "clothing_mesh_count": len(clothing_meshes),
            "armature_count": len(armatures),
            "action_names": sorted(action.name for action in bpy.data.actions),
        },
        "bounds_m": {
            "minimum": [round(float(value), 6) for value in bounds_min],
            "maximum": [round(float(value), 6) for value in bounds_max],
        },
        "renders": renders,
        "diagnostic_helper_policy": {
            "helpers_are_render_time_only": True,
            "helpers_are_not_part_of_model_snapshot": True,
            "ground_alignment_is_visual_context_not_contact_proof": True,
            "seat_is_visual_support_context_not_collision_or_load_proof": True,
        },
        "truth": {
            "private_clothed_diagnostic_only": True,
            "garment_coverage_owner_reviewed": False,
            "garment_penetration_proven_absent": False,
            "stable_visual_deformation_proven": False,
            "grounded_foot_contact_proven": False,
            "supported_seat_contact_proven": False,
            "identity_likeness_owner_approved": False,
            "wearable_dressing_behavior_proven": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        },
    }
    proof_path = output_dir / f"{prefix}_visual_diagnostic.json"
    with proof_path.open("x", encoding="utf-8") as handle:
        json.dump(proof, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"status": "private_visual_diagnostic_created", "proof": str(proof_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
