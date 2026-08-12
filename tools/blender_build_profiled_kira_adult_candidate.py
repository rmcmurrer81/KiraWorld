"""Build one inactive, private, profile-driven Kira adult-body candidate.

Run only through Blender with ``--`` followed by the arguments defined below.
The script is deliberately append-only at its output boundary: the destination
must be a new direct child of ``Avatar/private_owner_review``.  All pure gates,
including the separately qualified generic adult foundation and the exact
style profile, run before the first Blender scene mutation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import time
from typing import Any, Mapping, Sequence

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_adult_female_surface_authoring import (
    LANDMARK_GROUP_PREFIX,
    frame_from_mapping,
    parameters_from_mapping,
)
from Core.avatar_adult_foundation_qualification import POLICY_PATH, REGISTRY_PATH
from Core.avatar_profiled_adult_candidate_contract import (
    OWNER_REVIEW_VIEW_LABELS,
    ProfiledAdultCandidateContractError,
    evaluate_profiled_candidate_preflight,
    load_validated_profiled_candidate_builder_config,
    scaled_adult_surface_settings,
    verify_live_kira_state_unchanged,
)
from tools.blender_author_adult_female_external_surface import (
    author_continuous_adult_female_surface,
)
from tools.blender_author_adult_female_external_surface_v2 import (
    refine_existing_continuous_adult_female_surface_v2,
)
from tools.blender_profiled_adult_candidate_components import (
    add_natural_helper_eyes,
    add_natural_nails,
    apply_relaxed_hand_pose,
    apply_knee_solution,
    build_body_object,
    build_official_rig_and_normalized_weights,
    build_warm_skin_material,
    invoke_hash_bound_hair_provider,
    prepare_profiled_body_source,
    reset_pose,
    sha256_file,
    solve_bilateral_knee_axes_and_actions,
)
from tools.blender_repair_bounded_self_intersections import (
    repair_bounded_self_intersections,
)


class ProfiledKiraAdultCandidateBuildError(RuntimeError):
    """Raised before an incomplete candidate can be represented as accepted."""


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IMPLEMENTATION_PATHS = (
    Path("tools/blender_build_profiled_kira_adult_candidate.py"),
    Path("tools/blender_profiled_adult_candidate_components.py"),
    Path("tools/blender_author_adult_female_external_surface.py"),
    Path("tools/blender_author_adult_female_external_surface_v2.py"),
    Path("tools/blender_repair_bounded_self_intersections.py"),
    Path("tools/blender_exact_mesh_intersections.py"),
    Path("Core/avatar_profiled_adult_candidate_contract.py"),
    Path("Core/avatar_adult_female_surface_authoring.py"),
    Path("Core/avatar_adult_female_surface_authoring_v2.py"),
    Path("Core/avatar_adult_foundation_qualification.py"),
    Path("Core/avatar_body_style_profile.py"),
)
VALIDATION_INPUT_PATHS = (
    Path("Avatar/avatar_builder/style_profiles/adult_body_style_profile_v1.schema.json"),
)


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(
        description="Build a new inactive private profiled Kira adult candidate."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help=(
            "New project-relative Avatar/private_owner_review/"
            "kira_profiled_adult_candidate_* directory."
        ),
    )
    parser.add_argument(
        "--acknowledge-inactive-private-candidate",
        action="store_true",
        help="Required acknowledgement; does not authorize runtime activation.",
    )
    parser.add_argument(
        "--render-owner-review",
        action="store_true",
        help="Render the exact private owner-review view list, including protected views.",
    )
    parser.add_argument(
        "--export-private-glb",
        action="store_true",
        help="Also export a private GLB; never assigns or activates it.",
    )
    parser.add_argument(
        "--hair-provider-path",
        help="Optional project-relative Python provider exposing build_dynamic_hair.",
    )
    parser.add_argument(
        "--hair-provider-sha256",
        help="Required exact SHA-256 when --hair-provider-path is supplied.",
    )
    parser.add_argument(
        "--hairless-engineering-candidate",
        action="store_true",
        help=(
            "Explicitly omit the default responsive groom and label the output "
            "as a hairless engineering candidate."
        ),
    )
    parser.add_argument(
        "--hair-strand-count",
        type=int,
        default=3600,
        help="Bounded provider hint; the provider validates its own range.",
    )
    parser.add_argument(
        "--hair-controls-per-strand",
        type=int,
        default=13,
        help="Bounded provider hint; the provider validates its own range.",
    )
    return parser.parse_args(argv)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ProfiledKiraAdultCandidateBuildError(f"JSON root not object: {path}")
    return payload


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Vector):
        return [float(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _project_file(raw: Any, label: str) -> Path:
    relative = Path(str(raw or "").strip())
    if not str(raw or "").strip() or relative.is_absolute() or ".." in relative.parts:
        raise ProfiledKiraAdultCandidateBuildError(f"unsafe hash binding path: {label}")
    path = (PROJECT_ROOT / relative).resolve(strict=True)
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ProfiledKiraAdultCandidateBuildError(
            f"hash binding escaped project: {label}"
        ) from exc
    if not path.is_file():
        raise ProfiledKiraAdultCandidateBuildError(f"hash binding is not a file: {label}")
    return path


def _declared_hash_bindings(value: Any, role: str) -> list[tuple[str, str, str]]:
    """Collect every path/SHA pair recursively from a validated input record."""

    result: list[tuple[str, str, str]] = []
    if isinstance(value, Mapping):
        for key, raw_path in value.items():
            if key == "path":
                sha_key = "sha256"
            elif key.endswith("_path"):
                sha_key = f"{key[:-5]}_sha256"
            else:
                continue
            if sha_key in value:
                result.append(
                    (
                        str(raw_path or ""),
                        str(value.get(sha_key) or "").strip().lower(),
                        f"{role}:{key}",
                    )
                )
        for key, child in value.items():
            result.extend(_declared_hash_bindings(child, f"{role}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            result.extend(_declared_hash_bindings(child, f"{role}[{index}]"))
    return result


def _record_hash_binding(
    records: dict[str, dict[str, Any]],
    *,
    raw_path: Any,
    expected_sha256: str | None,
    role: str,
) -> None:
    path = _project_file(raw_path, role)
    relative = path.relative_to(PROJECT_ROOT.resolve()).as_posix()
    actual = sha256_file(path)
    expected = str(expected_sha256 or "").strip().lower()
    if expected and not SHA256_RE.fullmatch(expected):
        raise ProfiledKiraAdultCandidateBuildError(
            f"invalid expected SHA-256 for build binding: {role}"
        )
    if expected and actual != expected:
        raise ProfiledKiraAdultCandidateBuildError(
            f"point-of-use SHA-256 mismatch for build binding: {relative}"
        )
    prior = records.get(relative)
    if prior is not None and prior["sha256"] != actual:
        raise ProfiledKiraAdultCandidateBuildError(
            f"conflicting build hash binding: {relative}"
        )
    if prior is None:
        records[relative] = {"sha256": actual, "roles": [role]}
    elif role not in prior["roles"]:
        prior["roles"].append(role)


def _capture_build_hash_snapshot(
    *,
    config: Mapping[str, Any],
    config_report: Mapping[str, Any],
    profile: Mapping[str, Any],
    preflight: Mapping[str, Any],
    provider_path: str | None,
    provider_sha256: str | None,
) -> dict[str, Any]:
    """Bind every input and implementation file before scene mutation."""

    records: dict[str, dict[str, Any]] = {}
    _record_hash_binding(
        records,
        raw_path=config_report["config_path"],
        expected_sha256=str(config_report["config_sha256"]),
        role="builder_config",
    )
    for raw_path, expected, role in _declared_hash_bindings(config, "builder_config"):
        _record_hash_binding(
            records,
            raw_path=raw_path,
            expected_sha256=expected,
            role=role,
        )
    for raw_path, expected, role in _declared_hash_bindings(profile, "style_profile"):
        _record_hash_binding(
            records,
            raw_path=raw_path,
            expected_sha256=expected,
            role=role,
        )
    registry = _read_json(PROJECT_ROOT / REGISTRY_PATH)
    matches = [
        row
        for row in registry.get("entries", [])
        if isinstance(row, Mapping)
        and row.get("foundation_id")
        == "generic_makehuman_adult_female_foundation_v1_20260801"
    ]
    if len(matches) != 1:
        raise ProfiledKiraAdultCandidateBuildError(
            "qualified foundation registry binding not unique at build capture"
        )
    for raw_path, expected, role in _declared_hash_bindings(
        matches[0], "qualified_foundation_registry_entry"
    ):
        _record_hash_binding(
            records,
            raw_path=raw_path,
            expected_sha256=expected,
            role=role,
        )
    for relative, role in (
        (POLICY_PATH, "adult_foundation_policy"),
        (REGISTRY_PATH, "adult_foundation_registry"),
    ):
        expected_gate_hash = str(
            preflight.get("foundation_gate_files", {}).get(relative.as_posix()) or ""
        )
        _record_hash_binding(
            records,
            raw_path=relative.as_posix(),
            expected_sha256=expected_gate_hash,
            role=role,
        )
    for relative in IMPLEMENTATION_PATHS:
        _record_hash_binding(
            records,
            raw_path=relative.as_posix(),
            expected_sha256=None,
            role="executed_implementation",
        )
    for relative in VALIDATION_INPUT_PATHS:
        _record_hash_binding(
            records,
            raw_path=relative.as_posix(),
            expected_sha256=None,
            role="validation_input",
        )
    if provider_path is not None:
        _record_hash_binding(
            records,
            raw_path=provider_path,
            expected_sha256=provider_sha256,
            role="dynamic_hair_provider",
        )
    return {
        "captured_before_scene_mutation": True,
        "record_count": len(records),
        "records": dict(sorted(records.items())),
    }


def _verify_build_hash_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    records = snapshot.get("records")
    if not isinstance(records, Mapping) or not records:
        blockers.append("build_hash_snapshot_missing")
        records = {}
    after: dict[str, str] = {}
    for relative, record in records.items():
        expected = str(record.get("sha256") or "").strip().lower()
        try:
            path = _project_file(relative, f"commit:{relative}")
            actual = sha256_file(path)
        except (OSError, ProfiledKiraAdultCandidateBuildError) as exc:
            actual = ""
            blockers.append(f"build_binding_unavailable:{relative}:{type(exc).__name__}")
        after[str(relative)] = actual
        if not SHA256_RE.fullmatch(expected):
            blockers.append(f"build_binding_snapshot_sha256_invalid:{relative}")
        elif actual != expected:
            blockers.append(f"build_binding_changed:{relative}")
    return {
        "passed": not blockers,
        "checked_count": len(records),
        "after": after,
        "blockers": list(dict.fromkeys(blockers)),
    }


def _assert_exact_bound_file(path: Path, expected_sha256: Any, label: str) -> None:
    expected = str(expected_sha256 or "").strip().lower()
    if not SHA256_RE.fullmatch(expected) or sha256_file(path) != expected:
        raise ProfiledKiraAdultCandidateBuildError(
            f"point-of-use exact binding failed: {label}"
        )


def _assert_background_factory_startup_safe_scene() -> None:
    if not bpy.app.background:
        raise ProfiledKiraAdultCandidateBuildError(
            "candidate builder requires a dedicated background Blender process"
        )
    if str(bpy.data.filepath or "").strip():
        raise ProfiledKiraAdultCandidateBuildError(
            "candidate builder refuses to clear a loaded Blend; use --factory-startup"
        )
    factory_objects = sorted(
        (obj.name, obj.type) for obj in bpy.data.objects
    )
    expected_factory_objects = [
        ("Camera", "CAMERA"),
        ("Cube", "MESH"),
        ("Light", "LIGHT"),
    ]
    if (
        factory_objects != expected_factory_objects
        or len(bpy.data.scenes) != 1
        or len(bpy.data.libraries) != 0
    ):
        raise ProfiledKiraAdultCandidateBuildError(
            "candidate builder requires the untouched factory-startup scene fingerprint"
        )


def _clear_scene_after_preflight() -> None:
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.armatures,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.materials,
    ):
        for datablock in list(collection):
            if datablock.users == 0:
                collection.remove(datablock)


def _mesh_topology_counts(obj: Any) -> dict[str, int]:
    mesh = obj.data
    edge_face_counts = [0] * len(mesh.edges)
    edge_by_key = {
        tuple(sorted((int(edge.vertices[0]), int(edge.vertices[1])))): edge.index
        for edge in mesh.edges
    }
    for polygon in mesh.polygons:
        values = [int(value) for value in polygon.vertices]
        for index, first in enumerate(values):
            second = values[(index + 1) % len(values)]
            edge_face_counts[edge_by_key[tuple(sorted((first, second)))]] += 1
    adjacency: dict[int, set[int]] = {vertex.index: set() for vertex in mesh.vertices}
    for edge in mesh.edges:
        first, second = (int(value) for value in edge.vertices)
        adjacency[first].add(second)
        adjacency[second].add(first)
    unseen = set(adjacency)
    components = 0
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
    return {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "faces": len(mesh.polygons),
        "surface_components": components,
        "boundary_edges": sum(count == 1 for count in edge_face_counts),
        "nonmanifold_edges": sum(count != 2 for count in edge_face_counts),
    }


def _world_bounds(objects: Sequence[Any]) -> tuple[Vector, Vector]:
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        if obj.type in {"MESH", "CURVE"}
        for corner in obj.bound_box
    ]
    if not points:
        raise ProfiledKiraAdultCandidateBuildError("review bounds contain no geometry")
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def _look_at(camera: Any, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def _review_camera_and_lights(scene: Any, target_height_m: float) -> tuple[Any, dict[str, Any]]:
    camera_data = bpy.data.cameras.new("Kira_Profiled_Private_Review_Camera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("Kira_Profiled_Private_Review_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    world = bpy.data.worlds.new("Kira_Profiled_Private_Review_World")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Color"].default_value = (0.025, 0.031, 0.040, 1.0)
        background.inputs["Strength"].default_value = 0.18
    scene.world = world
    lights: list[dict[str, Any]] = []
    for name, location, energy, size in (
        ("Key", (-2.2, -3.0, target_height_m * 1.45), 325.0, 2.2),
        ("Fill", (2.5, -1.5, target_height_m * 1.10), 135.0, 2.0),
        ("Rim", (0.0, 2.8, target_height_m * 1.55), 240.0, 1.8),
    ):
        light_data = bpy.data.lights.new(f"Kira_Private_{name}", "AREA")
        light_data.energy = energy
        light_data.color = (1.0, 1.0, 1.0)
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(f"Kira_Private_{name}", light_data)
        bpy.context.collection.objects.link(light)
        light.location = location
        _look_at(light, Vector((0.0, 0.0, target_height_m * 0.78)))
        lights.append(
            {
                "name": name,
                "energy_w": energy,
                "size_m": size,
                "color_linear_rgb": [1.0, 1.0, 1.0],
            }
        )
    render_engine = None
    for candidate in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = candidate
        except TypeError:
            continue
        render_engine = candidate
        break
    if render_engine is None:
        raise ProfiledKiraAdultCandidateBuildError(
            "no supported Eevee private-review render engine is available"
        )
    scene["private_review_render_engine"] = render_engine
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.display_settings.display_device = "sRGB"
    except TypeError as exc:
        raise ProfiledKiraAdultCandidateBuildError(
            "neutral review display device unavailable"
        ) from exc
    try:
        scene.view_settings.view_transform = "AgX"
    except TypeError as exc:
        raise ProfiledKiraAdultCandidateBuildError(
            "AgX neutral review transform unavailable"
        ) from exc
    selected_look = None
    for look in ("AgX - Medium High Contrast", "Medium High Contrast", "None"):
        try:
            scene.view_settings.look = look
        except TypeError:
            continue
        selected_look = look
        break
    if selected_look is None:
        raise ProfiledKiraAdultCandidateBuildError("neutral review look unavailable")
    scene.view_settings.exposure = -0.65
    scene.view_settings.gamma = 1.0
    report = {
        "method": "bounded_neutral_warm_skin_review_rig_v2",
        "render_engine": render_engine,
        "world_strength": 0.18,
        "lights": lights,
        "display_device": "sRGB",
        "view_transform": "AgX",
        "look": selected_look,
        "exposure": -0.65,
        "gamma": 1.0,
        "total_area_light_energy_w": sum(float(row["energy_w"]) for row in lights),
        "legacy_overbright_1050_650_900_w_rig_used": False,
    }
    scene["private_review_lighting_report_json"] = json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
    )
    return camera, report


def _named_center(objects: Sequence[Any], token: str, fallback: Vector) -> Vector:
    matches = [obj for obj in objects if token.lower() in obj.name.lower()]
    if not matches:
        return fallback
    low, high = _world_bounds(matches)
    return (low + high) * 0.5


def _named_review_normal(objects: Sequence[Any], token: str, fallback: Vector) -> Vector:
    values = [
        Vector(tuple(obj["review_surface_normal"]))
        for obj in objects
        if token.lower() in obj.name.lower() and "review_surface_normal" in obj
    ]
    if not values:
        return fallback.normalized()
    average = sum(values, Vector()) / len(values)
    return average.normalized() if average.length > 1.0e-8 else fallback.normalized()


def _render_owner_review_views(
    *,
    scene: Any,
    output_dir: Path,
    body: Any,
    armature: Any,
    candidate_objects: Sequence[Any],
    knee_report: Mapping[str, Any],
    protected_target: Vector,
    target_height_m: float,
) -> dict[str, Any]:
    camera, lighting_report = _review_camera_and_lights(scene, target_height_m)
    low, high = _world_bounds([body])
    body_target = Vector((0.0, (low.y + high.y) * 0.5, target_height_m * 0.51))
    face_target = Vector((0.0, (low.y + high.y) * 0.5, high.z - target_height_m * 0.085))
    eye_target = _named_center(candidate_objects, "brown_iris", face_target)
    left_hand_normal = _named_review_normal(
        candidate_objects, "fingernail_3_L", Vector((0.0, -1.0, 0.0))
    )
    right_hand_normal = _named_review_normal(
        candidate_objects, "fingernail_3_R", Vector((0.0, -1.0, 0.0))
    )
    left_foot_normal = _named_review_normal(
        candidate_objects, "toenail_1_L", Vector((0.0, -0.12, 1.0))
    )
    right_foot_normal = _named_review_normal(
        candidate_objects, "toenail_1_R", Vector((0.0, -0.12, 1.0))
    )
    distance = target_height_m * 3.0
    directions = {
        "front": Vector((0.0, -1.0, 0.03)),
        "rear": Vector((0.0, 1.0, 0.03)),
        "left_profile": Vector((-1.0, 0.0, 0.03)),
        "right_profile": Vector((1.0, 0.0, 0.03)),
        "left_three_quarter": Vector((-0.68, -0.73, 0.03)),
        "right_three_quarter": Vector((0.68, -0.73, 0.03)),
        "face_close": Vector((0.0, -1.0, 0.01)),
        "eyes_close": Vector((0.0, -1.0, 0.01)),
        "left_hand_nails_close": left_hand_normal + Vector((-0.10, 0.0, 0.30)),
        "right_hand_nails_close": right_hand_normal + Vector((0.10, 0.0, 0.30)),
        "left_foot_nails_close": left_foot_normal + Vector((-0.08, -0.35, 0.0)),
        "right_foot_nails_close": right_foot_normal + Vector((0.08, -0.35, 0.0)),
        "left_knee_flexion": Vector((-0.55, -1.0, 0.10)),
        "right_knee_flexion": Vector((0.55, -1.0, 0.10)),
        "protected_adult_relationship_front": Vector((0.0, -1.0, 0.02)),
        "protected_adult_relationship_side": Vector((1.0, 0.0, 0.02)),
        "protected_adult_relationship_three_quarter": Vector((0.72, -0.70, 0.02)),
    }
    close_targets = {
        "face_close": face_target,
        "eyes_close": eye_target,
        "left_hand_nails_close": _named_center(candidate_objects, "fingernail_3_L", body_target),
        "right_hand_nails_close": _named_center(candidate_objects, "fingernail_3_R", body_target),
        "left_foot_nails_close": _named_center(candidate_objects, "toenail_1_L", body_target),
        "right_foot_nails_close": _named_center(candidate_objects, "toenail_1_R", body_target),
        "left_knee_flexion": armature.matrix_world @ armature.data.bones["lowerleg01.L"].head_local,
        "right_knee_flexion": armature.matrix_world @ armature.data.bones["lowerleg01.R"].head_local,
        "protected_adult_relationship_front": protected_target,
        "protected_adult_relationship_side": protected_target,
        "protected_adult_relationship_three_quarter": protected_target,
    }
    close_scales = {
        "face_close": target_height_m * 0.33,
        "eyes_close": target_height_m * 0.13,
        "left_hand_nails_close": target_height_m * 0.12,
        "right_hand_nails_close": target_height_m * 0.12,
        "left_foot_nails_close": target_height_m * 0.13,
        "right_foot_nails_close": target_height_m * 0.13,
        "left_knee_flexion": target_height_m * 0.43,
        "right_knee_flexion": target_height_m * 0.43,
        "protected_adult_relationship_front": target_height_m * 0.25,
        "protected_adult_relationship_side": target_height_m * 0.25,
        "protected_adult_relationship_three_quarter": target_height_m * 0.25,
    }
    rendered: list[dict[str, Any]] = []
    relaxed_hand_poses: list[dict[str, Any]] = []
    responsive_grooms = [
        obj
        for obj in candidate_objects
        if obj.type == "CURVE" and obj.get("responsive_avatar_hair") is True
    ]
    for label in OWNER_REVIEW_VIEW_LABELS:
        reset_pose(armature)
        if label == "left_knee_flexion":
            apply_knee_solution(armature, knee_report["solutions"]["left"])
        elif label == "right_knee_flexion":
            apply_knee_solution(armature, knee_report["solutions"]["right"])
        elif label == "left_hand_nails_close":
            relaxed_hand_poses.append(
                apply_relaxed_hand_pose(armature, "L", target_height_m=target_height_m)
            )
        elif label == "right_hand_nails_close":
            relaxed_hand_poses.append(
                apply_relaxed_hand_pose(armature, "R", target_height_m=target_height_m)
            )
        isolate_eyes = label == "eyes_close"
        for groom in responsive_grooms:
            groom.hide_render = isolate_eyes
        target = close_targets.get(label, body_target)
        direction = directions[label].normalized()
        camera.location = target + direction * distance
        _look_at(camera, target)
        camera.data.ortho_scale = close_scales.get(label, target_height_m * 1.12)
        path = output_dir / f"{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        for groom in responsive_grooms:
            groom.hide_render = False
        rendered.append(
            {
                "label": label,
                "path": path.name,
                "sha256": sha256_file(path),
                "protected_view": label.startswith("protected_adult_relationship_"),
            }
        )
    supplemental_hair: list[dict[str, Any]] = []
    if len(responsive_grooms) > 1:
        raise ProfiledKiraAdultCandidateBuildError(
            "owner review found more than one responsive groom"
        )
    if responsive_grooms:
        groom = responsive_grooms[0]
        required_controls = (
            "hair_wind_direction_minus1_1",
            "hair_wetness_0_1",
        )
        if any(name not in groom for name in required_controls):
            raise ProfiledKiraAdultCandidateBuildError(
                "responsive groom review controls missing"
            )
        hair_target = Vector(
            (
                0.0,
                (low.y + high.y) * 0.5,
                high.z - target_height_m * 0.16,
            )
        )
        supplemental_states = (
            ("hair_dry_front", 0.0, 0.0, Vector((0.0, -1.0, 0.02))),
            ("hair_dry_rear", 0.0, 0.0, Vector((0.0, 1.0, 0.02))),
            ("hair_wind_left_front", -1.0, 0.0, Vector((0.0, -1.0, 0.02))),
            ("hair_wind_right_front", 1.0, 0.0, Vector((0.0, -1.0, 0.02))),
            ("hair_wet_front", 0.0, 1.0, Vector((0.0, -1.0, 0.02))),
            ("hair_wet_rear", 0.0, 1.0, Vector((0.0, 1.0, 0.02))),
            ("hair_wet_wind_left_front", -1.0, 1.0, Vector((0.0, -1.0, 0.02))),
            ("hair_wet_wind_right_front", 1.0, 1.0, Vector((0.0, -1.0, 0.02))),
        )
        for label, wind, wetness, direction in supplemental_states:
            reset_pose(armature)
            groom["hair_wind_direction_minus1_1"] = wind
            groom["hair_wetness_0_1"] = wetness
            groom.update_tag()
            if groom.data.shape_keys is not None:
                groom.data.shape_keys.update_tag()
            scene.frame_set(scene.frame_current)
            bpy.context.view_layer.update()
            camera.location = hair_target + direction.normalized() * distance
            _look_at(camera, hair_target)
            camera.data.ortho_scale = target_height_m * 0.52
            path = output_dir / f"{label}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            supplemental_hair.append(
                {
                    "label": label,
                    "path": path.name,
                    "sha256": sha256_file(path),
                    "signed_wind_input": wind,
                    "wetness_input": wetness,
                    "proof_scope": "PRIVATE_BLEND_RENDERED_TARGET_STATE_NOT_WORLD_RUNTIME",
                }
            )
        groom["hair_wind_direction_minus1_1"] = 0.0
        groom["hair_wetness_0_1"] = 0.0
        groom.update_tag()
        if groom.data.shape_keys is not None:
            groom.data.shape_keys.update_tag()
        scene.frame_set(scene.frame_current)
        bpy.context.view_layer.update()
    reset_pose(armature)
    return {
        "render_performed": True,
        "view_count": len(rendered),
        "exact_required_labels": list(OWNER_REVIEW_VIEW_LABELS),
        "views": rendered,
        "supplemental_hair_response_view_count": len(supplemental_hair),
        "supplemental_hair_response_views": supplemental_hair,
        "neutral_review_lighting": lighting_report,
        "eye_close_hair_isolated": True,
        "relaxed_hand_pose_count": len(relaxed_hand_poses),
        "relaxed_hand_poses": relaxed_hand_poses,
        "private_blend_hair_target_states_rendered": bool(supplemental_hair),
        "world_runtime_hair_response_proven": False,
        "private_owner_review_only": True,
    }


def _mark_inactive_private(objects: Sequence[Any], scene: Any, candidate_id: str) -> None:
    for obj in objects:
        obj["candidate_id"] = candidate_id
        obj["private_owner_review_only"] = True
        obj["inactive_candidate"] = True
        obj["runtime_activation_allowed"] = False
        obj["roster_registration_allowed"] = False
        obj["publication_allowed"] = False
        obj["clothing_included"] = False
    scene["candidate_id"] = candidate_id
    scene["candidate_author_id"] = (
        "profiled_confirmed_adult_female_candidate_builder_v1"
    )
    scene["body_class"] = "adult_female"
    scene["confirmed_adult"] = True
    scene["kira_styling_applied"] = True
    scene["private_owner_review_only"] = True
    scene["candidate_status"] = "INACTIVE_UNASSIGNED_AWAITING_OWNER_AND_INDEPENDENT_REVIEW"
    scene["runtime_activation_allowed"] = False
    scene["roster_registration_allowed"] = False
    scene["publication_allowed"] = False
    scene["clothing_included"] = False


def _export_private_glb(output_path: Path, candidate_objects: Sequence[Any]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in candidate_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = next(
        obj for obj in candidate_objects if obj.type == "ARMATURE"
    )
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_skins=True,
        export_morph=True,
        export_extras=True,
    )


def build(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    if args.acknowledge_inactive_private_candidate is not True:
        raise ProfiledKiraAdultCandidateBuildError(
            "--acknowledge-inactive-private-candidate is required"
        )
    if bool(args.hair_provider_path) != bool(args.hair_provider_sha256):
        raise ProfiledKiraAdultCandidateBuildError(
            "hair provider path and SHA-256 must be supplied together"
        )
    if args.hairless_engineering_candidate and args.hair_provider_path:
        raise ProfiledKiraAdultCandidateBuildError(
            "hairless mode cannot be combined with a hair provider override"
        )
    if not args.hairless_engineering_candidate and not args.hair_provider_path:
        raise ProfiledKiraAdultCandidateBuildError(
            "full candidate requires an independently reviewed exact hair provider; "
            "otherwise pass --hairless-engineering-candidate"
        )
    output_relative = Path(args.output_dir)
    preflight = evaluate_profiled_candidate_preflight(PROJECT_ROOT, output_relative)
    if preflight["ready"] is not True:
        raise ProfiledAdultCandidateContractError(
            "candidate preflight blocked: " + "; ".join(preflight["blockers"])
        )
    # Everything above this line is pure/read-only.  Scene mutation begins only
    # after the actual foundation, exact style, output, and live-state gates pass.
    config, config_report = load_validated_profiled_candidate_builder_config(PROJECT_ROOT)
    if args.hairless_engineering_candidate:
        provider_path = None
        provider_sha256 = None
    else:
        provider_path = args.hair_provider_path
        provider_sha256 = args.hair_provider_sha256
    profile_relative = Path(config["style_profile"]["path"])
    profile_path = PROJECT_ROOT / profile_relative
    if sha256_file(profile_path) != config["style_profile"]["sha256"]:
        raise ProfiledKiraAdultCandidateBuildError("profile changed after preflight")
    profile = _read_json(profile_path)
    target_height_m = float(profile["dimensions"]["target_height_m"])
    candidate_id = output_relative.name
    output_dir = PROJECT_ROOT / output_relative
    if output_dir.exists():
        raise ProfiledKiraAdultCandidateBuildError("output appeared after preflight")

    build_hash_snapshot = _capture_build_hash_snapshot(
        config=config,
        config_report=config_report,
        profile=profile,
        preflight=preflight,
        provider_path=provider_path,
        provider_sha256=provider_sha256,
    )
    _assert_background_factory_startup_safe_scene()
    _clear_scene_after_preflight()
    scene = bpy.context.scene
    base_path = PROJECT_ROOT / config["makehuman_source_set"]["base_body"]["path"]
    _assert_exact_bound_file(
        base_path,
        config["makehuman_source_set"]["base_body"]["sha256"],
        "official base body before source preparation",
    )
    source = prepare_profiled_body_source(
        base_path=base_path,
        female_macros=config["makehuman_source_set"]["female_macros"],
        resolved_style_targets=preflight["style_profile"]["resolved_targets"],
        project_root=PROJECT_ROOT,
        target_height_m=target_height_m,
    )
    expected_style_order = [row["target_id"] for row in profile["shape_targets"]]
    if source["style_target_ids_in_application_order"] != expected_style_order:
        raise ProfiledKiraAdultCandidateBuildError("style target application order drifted")
    if source["style_target_count"] != 12:
        raise ProfiledKiraAdultCandidateBuildError("exact twelve style targets not applied")

    skin_material, skin_report = build_warm_skin_material(profile)
    body = build_body_object(source, candidate_id, skin_material)
    skeleton_path = PROJECT_ROOT / config["official_rig"]["skeleton"]["path"]
    weights_path = PROJECT_ROOT / config["official_rig"]["weights"]["path"]
    _assert_exact_bound_file(
        skeleton_path,
        config["official_rig"]["skeleton"]["sha256"],
        "official skeleton before rig construction",
    )
    _assert_exact_bound_file(
        weights_path,
        config["official_rig"]["weights"]["sha256"],
        "official weights before skin construction",
    )
    armature, rig_report = build_official_rig_and_normalized_weights(
        body=body,
        source=source,
        skeleton_path=skeleton_path,
        weights_path=weights_path,
        candidate_id=candidate_id,
        maximum_influences=4,
    )

    cleanup_report = repair_bounded_self_intersections(body)
    cleanup_after = cleanup_report.get("after", {})
    if int(cleanup_after.get("exact_genuine_penetration_pair_count", -1)) != 0:
        raise ProfiledKiraAdultCandidateBuildError("bounded exact source cleanup did not reach zero")
    scaled_frame, scaled_parameters = scaled_adult_surface_settings(
        config["adult_surface_authoring"], target_height_m
    )
    frame = frame_from_mapping(scaled_frame)
    parameters = parameters_from_mapping(scaled_parameters)
    adult_surface_report = author_continuous_adult_female_surface(
        body,
        frame=frame,
        parameters=parameters,
        project_root=PROJECT_ROOT,
    )
    if adult_surface_report.get("global_topology_ready_for_qualification") is not True:
        raise ProfiledKiraAdultCandidateBuildError("authored surface global topology not ready")
    detail_config = config["adult_surface_authoring"]["structured_detail_refinement"]
    detail_relief_scale_m = float(detail_config["baseline_relief_scale_m"]) * (
        target_height_m / float(config["adult_surface_authoring"]["baseline_height_m"])
    )
    detail_ratio = target_height_m / float(
        config["adult_surface_authoring"]["baseline_height_m"]
    )
    posterior_frame_payload = dict(detail_config["posterior_frame"])
    posterior_frame_payload["origin"] = [
        float(value) * detail_ratio for value in posterior_frame_payload["origin"]
    ]
    for metric_name in ("half_width_m", "half_length_m", "max_surface_offset_m"):
        posterior_frame_payload[metric_name] = (
            float(posterior_frame_payload[metric_name]) * detail_ratio
        )
    posterior_frame = frame_from_mapping(posterior_frame_payload)
    adult_detail_report = refine_existing_continuous_adult_female_surface_v2(
        body,
        frame=frame,
        base_parameters=parameters,
        posterior_frame=posterior_frame,
        target_relief_scale_m=detail_relief_scale_m,
        target_taper_power=int(detail_config["boundary_taper_power"]),
    )
    if (
        adult_detail_report.get("new_global_nonadjacent_self_intersection_pairs") != 0
        or adult_detail_report.get("topology_changed") is not False
        or adult_detail_report.get("rig_weights_changed") is not False
        or adult_detail_report.get("landmark_group_names_changed") is not False
        or adult_detail_report.get(
            "posterior_landmark_memberships_rebound_to_curved_frame"
        )
        is not True
    ):
        raise ProfiledKiraAdultCandidateBuildError(
            "structured adult detail refinement failed topology or rig invariants"
        )
    adult_surface_report["structured_detail_refinement"] = adult_detail_report
    landmark_names = list(adult_surface_report.get("landmark_groups", {}).values())
    retained = sorted(
        group.name for group in body.vertex_groups if group.name.startswith(LANDMARK_GROUP_PREFIX)
    )
    if not landmark_names or sorted(landmark_names) != retained:
        raise ProfiledKiraAdultCandidateBuildError("adult landmark groups were not retained exactly")
    body["adult_relationship_surface_method"] = str(
        adult_surface_report.get("method_id") or ""
    )
    body["adult_relationship_surface_detail_method"] = str(
        adult_detail_report.get("detail_method_id") or ""
    )
    body["adult_relationship_landmark_group_count"] = len(retained)
    body["adult_relationships_require_independent_requalification"] = True

    _assert_exact_bound_file(
        base_path,
        config["makehuman_source_set"]["base_body"]["sha256"],
        "official base body before helper-eye construction",
    )
    eye_objects, eye_report = add_natural_helper_eyes(
        base_path=base_path,
        source=source,
        body=body,
        armature=armature,
        eye_profile=profile["eye_profile"],
        candidate_id=candidate_id,
    )
    nail_objects, nail_report = add_natural_nails(
        body=body,
        armature=armature,
        target_height_m=target_height_m,
        candidate_id=candidate_id,
    )
    knee_report = solve_bilateral_knee_axes_and_actions(armature, body)
    if (
        knee_report.get("skeleton_kinematic_objective_pass") is not True
        or knee_report.get("knee_mesh_deformation_quality_proven") is not True
    ):
        raise ProfiledKiraAdultCandidateBuildError(
            "bilateral measured skeleton or evaluated-mesh knee gate failed"
        )
    hair_objects, hair_report = invoke_hash_bound_hair_provider(
        project_root=PROJECT_ROOT,
        provider_path=provider_path,
        provider_sha256=provider_sha256,
        body=body,
        armature=armature,
        context={
            "candidate_id": candidate_id,
            "project_root": PROJECT_ROOT.as_posix(),
            "style_profile": profile,
            "hair_profile": profile["hair_profile"],
            "strand_count": int(args.hair_strand_count),
            "controls_per_strand": int(args.hair_controls_per_strand),
            "private_owner_review_only": True,
            "runtime_activation_allowed": False,
        },
    )
    candidate_objects = [body, armature, *eye_objects, *nail_objects, *hair_objects]
    _mark_inactive_private(candidate_objects, scene, candidate_id)
    topology = _mesh_topology_counts(body)
    if topology["surface_components"] != 1 or topology["boundary_edges"] != 0:
        raise ProfiledKiraAdultCandidateBuildError("final primary surface is not one closed component")
    live_before_output = verify_live_kira_state_unchanged(
        PROJECT_ROOT, preflight["live_kira_state_before"]
    )
    if live_before_output["passed"] is not True:
        raise ProfiledKiraAdultCandidateBuildError("live Kira state changed during build")
    hashes_before_output = _verify_build_hash_snapshot(build_hash_snapshot)
    if hashes_before_output["passed"] is not True:
        raise ProfiledKiraAdultCandidateBuildError(
            "build input or implementation changed before output creation: "
            + "; ".join(hashes_before_output["blockers"])
        )

    output_dir.mkdir(parents=False, exist_ok=False)
    protected_target = Vector(tuple(scaled_frame["origin"]))
    if args.render_owner_review:
        render_report = _render_owner_review_views(
            scene=scene,
            output_dir=output_dir,
            body=body,
            armature=armature,
            candidate_objects=candidate_objects,
            knee_report=knee_report,
            protected_target=protected_target,
            target_height_m=target_height_m,
        )
    else:
        render_report = {
            "render_performed": False,
            "view_count": 0,
            "exact_required_labels": list(OWNER_REVIEW_VIEW_LABELS),
            "status": "OWNER_REVIEW_RENDERING_NOT_REQUESTED",
        }
    reset_pose(armature)
    blend_path = output_dir / f"{candidate_id}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    blend_record = {"path": blend_path.name, "sha256": sha256_file(blend_path)}
    if args.export_private_glb:
        glb_path = output_dir / f"{candidate_id}.private.glb"
        _export_private_glb(glb_path, candidate_objects)
        glb_record: dict[str, Any] = {
            "exported": True,
            "path": glb_path.name,
            "sha256": sha256_file(glb_path),
            "private_owner_review_only": True,
            "runtime_activation_allowed": False,
            "validation_status": "UNVALIDATED_PENDING_FRESH_IMPORT",
            "fresh_import_validation_performed": False,
            "hair_curve_and_morph_runtime_survival_proven": False,
        }
    else:
        glb_record = {"exported": False, "status": "PRIVATE_GLB_NOT_REQUESTED"}
    live_after = verify_live_kira_state_unchanged(
        PROJECT_ROOT, preflight["live_kira_state_before"]
    )
    if live_after["passed"] is not True:
        raise ProfiledKiraAdultCandidateBuildError("live Kira state changed before evidence commit")
    hashes_at_commit = _verify_build_hash_snapshot(build_hash_snapshot)
    if hashes_at_commit["passed"] is not True:
        raise ProfiledKiraAdultCandidateBuildError(
            "build input or implementation changed before evidence commit: "
            + "; ".join(hashes_at_commit["blockers"])
        )
    evidence = {
        "schema_version": 1,
        "evidence_type": "inactive_profiled_kira_adult_candidate_build_v1",
        "candidate_id": candidate_id,
        "status": "INACTIVE_PRIVATE_CANDIDATE_AWAITING_OWNER_AND_INDEPENDENT_REVIEW",
        "adult_confirmation": {
            "body_class": "adult_female",
            "required_foundation_id": preflight["required_foundation_id"],
            "foundation_qualified_at_preflight": True,
            "post_style_exact_hash_independent_requalification_required": True,
            "pose_space_pelvic_patch_deformation_audit_status": "NOT_PERFORMED",
            "knee_mesh_deformation_quality_status": "PENDING_VISUAL_AND_POSE_REVIEW",
            "current_candidate_qualified_for_activation": False,
        },
        "preflight": preflight,
        "builder_config": config_report,
        "source": {
            key: value
            for key, value in source.items()
            if key not in {"source_vertices_after_all_targets", "body_vertices", "body_faces", "source_to_body"}
        },
        "application_order": [
            "official_base_body_group",
            "official_female_macros",
            "validator_resolved_style_targets_as_listed",
            "uniform_scale_to_1.651m",
            "official_rig_and_normalized_weights",
            "bounded_exact_source_cleanup",
            "generic_continuous_adult_female_surface_authoring",
            "retain_adult_landmark_groups",
            "natural_helper_eyes",
            "natural_nails",
            "axis_solved_bilateral_knee_actions",
            "optional_hash_bound_dynamic_hair_provider",
        ],
        "skin": skin_report,
        "rig": rig_report,
        "bounded_source_cleanup": cleanup_report,
        "adult_surface_authoring": adult_surface_report,
        "retained_adult_landmark_groups": retained,
        "eyes": eye_report,
        "nails": nail_report,
        "knees": knee_report,
        "hair": hair_report,
        "final_primary_surface_topology": topology,
        "owner_review": render_report,
        "outputs": {"blend": blend_record, "private_glb": glb_record},
        "protected_live_kira_state": live_after,
        "build_hash_bindings": {
            "snapshot": build_hash_snapshot,
            "verified_before_output_creation": hashes_before_output,
            "verified_at_evidence_commit": hashes_at_commit,
        },
        "safety": {
            "private_owner_review_only": True,
            "inactive": True,
            "assigned": False,
            "clothing_included": False,
            "publication_allowed": False,
            "runtime_activation_allowed": False,
            "live_kira_state_mutated": False,
            "primary_body_copied_anatomy_geometry_used": False,
            "legacy_body_geometry_used": False,
            "hair_provider_geometry_provenance_independent_review_required": bool(
                hair_report.get("provider_invoked")
            ),
        },
        "implementation": {
            "hashes_captured_before_scene_mutation": True,
            "hashes_unchanged_at_evidence_commit": True,
            "records": {
                path: record
                for path, record in build_hash_snapshot["records"].items()
                if "executed_implementation" in record["roles"]
            },
        },
        "build_elapsed_seconds": time.perf_counter() - started,
    }
    evidence_path = output_dir / "BUILD_EVIDENCE.json"
    evidence_path.write_text(
        json.dumps(_json_safe(evidence), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result = {
        "status": evidence["status"],
        "candidate_id": candidate_id,
        "output_directory": output_relative.as_posix(),
        "blend": blend_record,
        "private_glb": glb_record,
        "render_performed": render_report["render_performed"],
        "evidence_path": evidence_path.relative_to(PROJECT_ROOT).as_posix(),
        "evidence_sha256": sha256_file(evidence_path),
        "runtime_activation_allowed": False,
        "live_kira_state_mutated": False,
    }
    return result


def main() -> int:
    try:
        result = build(_arguments())
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "BLOCKED_OR_FAILED_WITHOUT_ACTIVATION",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "runtime_activation_allowed": False,
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
