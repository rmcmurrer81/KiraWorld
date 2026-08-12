"""Render one append-only, in-memory v4 hair diagnostic against immutable R15.

This script deliberately does not save a blend, export geometry, build a new
candidate, activate an avatar, or mutate the source R15 files.  Blender must be
started with the R15 blend and this script; only PNGs and diagnostic evidence
are written to a new isolated-review directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

import bpy
from mathutils import Matrix, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.blender_author_responsive_avatar_hair_v4 import (
    VISUAL_QUALITY_VERSION,
    author_responsive_wavy_black_hair,
)


IMMUTABLE_R15_BLEND = (
    PROJECT_ROOT
    / "Avatar"
    / "private_owner_review"
    / "kira_profiled_adult_candidate_r15_20260801_114658"
    / "kira_profiled_adult_candidate_r15_20260801_114658.blend"
)
IMMUTABLE_R15_BLEND_SHA256 = (
    "5e28a760ac0c44d20944771d3a7da0caf8f04ff6019d644d57d9ad8d7dc65e88"
)
IMMUTABLE_R15_BUILD_EVIDENCE = IMMUTABLE_R15_BLEND.with_name("BUILD_EVIDENCE.json")
IMMUTABLE_R15_BUILD_EVIDENCE_SHA256 = (
    "b3cc8906d8e443ef57706bbf2f3e3e3dd75f62e56ecbb9055d06608cbb25c403"
)
IMMUTABLE_V3_PROVIDER = PROJECT_ROOT / "tools" / "blender_author_responsive_avatar_hair.py"
IMMUTABLE_V3_PROVIDER_SHA256 = (
    "b5b1faa284978c5df1e5ecd09b9f800bbc9be4b28fca49d995b6df13b02a110e"
)
V4_PROVIDER = PROJECT_ROOT / "tools" / "blender_author_responsive_avatar_hair_v4.py"
V4_SMOKE = PROJECT_ROOT / "tools" / "blender_test_responsive_avatar_hair_v4.py"
PROFILE = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "style_profiles"
    / "natural_athletic_warm_asymmetric_waves_v1.json"
)
PROFILE_SHA256 = "2cc411d0d2ac63a13969f9a427e9f3b26b8488bae7539f4c26e0a1a81ee07d5c"
R15_REVIEW_DIR = IMMUTABLE_R15_BLEND.parent


class V4HairDiagnosticError(RuntimeError):
    """Raised before diagnostic output can be represented as complete."""


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--only-label",
        help="Render one named state as an append-only continuation after a runner timeout.",
    )
    return parser.parse_args(argv)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_hash(path: Path, expected: str, label: str) -> None:
    actual = _sha256(path)
    if actual != expected:
        raise V4HairDiagnosticError(
            f"{label}_hash_mismatch:expected={expected};actual={actual};path={path}"
        )


def _world_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def _look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def _reset_pose(armature: bpy.types.Object) -> None:
    for bone in armature.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    armature.update_tag()
    bpy.context.view_layer.update()


def _sampled_image_metrics(path: Path) -> dict[str, Any]:
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        width, height = (int(value) for value in image.size)
        pixels = image.pixels
        # Sample a deterministic 6 px grid.  The central upper 76% excludes
        # most empty frame while covering the scalp, face, shoulders and tips.
        step = 6
        x_low = int(width * 0.12)
        x_high = int(width * 0.88)
        y_low = int(height * 0.20)
        y_high = int(height * 0.96)
        luminances: list[float] = []
        dark = 0
        near_black = 0
        for y in range(y_low, y_high, step):
            for x in range(x_low, x_high, step):
                index = (y * width + x) * 4
                red = float(pixels[index])
                green = float(pixels[index + 1])
                blue = float(pixels[index + 2])
                luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
                luminances.append(luminance)
                dark += int(luminance < 0.08)
                near_black += int(luminance < 0.025)
        mean = sum(luminances) / len(luminances)
        variance = sum((value - mean) ** 2 for value in luminances) / len(luminances)
        return {
            "width_px": width,
            "height_px": height,
            "sample_count": len(luminances),
            "central_upper_roi_mean_linear_luminance": mean,
            "central_upper_roi_luminance_standard_deviation": variance ** 0.5,
            "central_upper_roi_dark_fraction_below_0_08": dark / len(luminances),
            "central_upper_roi_near_black_fraction_below_0_025": near_black
            / len(luminances),
        }
    finally:
        bpy.data.images.remove(image)


def main() -> None:
    args = _arguments()
    output_dir = (PROJECT_ROOT / args.output_dir).resolve()
    allowed_parent = (PROJECT_ROOT / "Avatar" / "private_owner_review").resolve()
    if output_dir.parent != allowed_parent:
        raise V4HairDiagnosticError("output_must_be_direct_child_of_private_owner_review")
    if "isolated_diagnostic" not in output_dir.name or "candidate" in output_dir.name:
        raise V4HairDiagnosticError("output_name_must_be_non_candidate_isolated_diagnostic")
    if output_dir.exists():
        raise V4HairDiagnosticError("append_only_output_directory_already_exists")

    _require_hash(IMMUTABLE_R15_BLEND, IMMUTABLE_R15_BLEND_SHA256, "r15_blend")
    _require_hash(
        IMMUTABLE_R15_BUILD_EVIDENCE,
        IMMUTABLE_R15_BUILD_EVIDENCE_SHA256,
        "r15_build_evidence",
    )
    _require_hash(IMMUTABLE_V3_PROVIDER, IMMUTABLE_V3_PROVIDER_SHA256, "v3_provider")
    _require_hash(PROFILE, PROFILE_SHA256, "hair_profile")
    loaded_path = Path(bpy.data.filepath).resolve()
    if loaded_path != IMMUTABLE_R15_BLEND.resolve():
        raise V4HairDiagnosticError(f"wrong_loaded_blend:{loaded_path}")

    bodies = [obj for obj in bpy.data.objects if obj.get("primary_surface") is True]
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    old_grooms = [
        obj
        for obj in bpy.data.objects
        if obj.type == "CURVE" and obj.get("responsive_avatar_hair") is True
    ]
    if len(bodies) != 1 or len(armatures) != 1 or len(old_grooms) != 1:
        raise V4HairDiagnosticError(
            f"r15_object_contract_failed:bodies={len(bodies)};"
            f"armatures={len(armatures)};grooms={len(old_grooms)}"
        )
    body, armature, old_groom = bodies[0], armatures[0], old_grooms[0]
    if old_groom.get("dynamic_hair_provider_sha256") != IMMUTABLE_V3_PROVIDER_SHA256:
        raise V4HairDiagnosticError("r15_groom_provider_binding_mismatch")

    output_dir.mkdir(parents=False)
    old_groom.hide_render = True
    _reset_pose(armature)
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    started = time.perf_counter()
    groom, report = author_responsive_wavy_black_hair(
        body,
        armature,
        profile["hair_profile"],
        name="Kira_R15_Isolated_Responsive_Hair_V4_Diagnostic",
        strand_count=3600,
        controls_per_strand=13,
    )
    authoring_seconds = time.perf_counter() - started
    groom["diagnostic_only"] = True
    groom["candidate_build_performed"] = False
    groom["runtime_activation_allowed"] = False

    scene = bpy.context.scene
    camera = bpy.data.objects.get("Kira_Profiled_Private_Review_Camera")
    if camera is None or camera.type != "CAMERA":
        raise V4HairDiagnosticError("r15_review_camera_missing")
    scene.camera = camera
    render_engine = None
    for candidate in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = candidate
        except TypeError:
            continue
        render_engine = candidate
        break
    if render_engine is None:
        raise V4HairDiagnosticError("no_supported_eevee_render_engine")
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    low, high = _world_bounds(body)
    target_height = float(high.z - low.z)
    distance = target_height * 3.0
    hair_target = Vector(
        (0.0, (low.y + high.y) * 0.5, high.z - target_height * 0.16)
    )
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = target_height * 0.52
    states = (
        ("hair_dry_front", 0.0, 0.0, Vector((0.0, -1.0, 0.02))),
        ("hair_dry_rear", 0.0, 0.0, Vector((0.0, 1.0, 0.02))),
        ("hair_wind_left_front", -1.0, 0.0, Vector((0.0, -1.0, 0.02))),
        ("hair_wind_right_front", 1.0, 0.0, Vector((0.0, -1.0, 0.02))),
        ("hair_wet_front", 0.0, 1.0, Vector((0.0, -1.0, 0.02))),
        ("hair_wet_rear", 0.0, 1.0, Vector((0.0, 1.0, 0.02))),
        ("hair_wet_wind_left_front", -1.0, 1.0, Vector((0.0, -1.0, 0.02))),
        ("hair_wet_wind_right_front", 1.0, 1.0, Vector((0.0, -1.0, 0.02))),
    )
    if args.only_label is not None:
        states = tuple(state for state in states if state[0] == args.only_label)
        if not states:
            raise V4HairDiagnosticError(f"unknown_only_label:{args.only_label}")
    renders: list[dict[str, Any]] = []
    for label, wind, wetness, direction in states:
        _reset_pose(armature)
        groom["hair_wind_direction_minus1_1"] = wind
        groom["hair_wetness_0_1"] = wetness
        groom.update_tag()
        if groom.data.shape_keys is not None:
            groom.data.shape_keys.update_tag()
        scene.frame_set(scene.frame_current)
        bpy.context.view_layer.update()
        camera.location = hair_target + direction.normalized() * distance
        _look_at(camera, hair_target)
        path = output_dir / f"{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        baseline = R15_REVIEW_DIR / f"{label}.png"
        renders.append(
            {
                "label": label,
                "path": path.name,
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
                "signed_wind_input": wind,
                "wetness_input": wetness,
                "v4_sampled_pixel_metrics": _sampled_image_metrics(path),
                "r15_v3_baseline_sha256": _sha256(baseline),
                "r15_v3_baseline_sampled_pixel_metrics": _sampled_image_metrics(
                    baseline
                ),
                "proof_scope": "ISOLATED_PRIVATE_BLEND_RENDERED_TARGET_NOT_WORLD_RUNTIME",
            }
        )

    groom["hair_wind_direction_minus1_1"] = 0.0
    groom["hair_wetness_0_1"] = 0.0
    _reset_pose(armature)
    total_seconds = time.perf_counter() - started
    evidence = {
        "schema_version": 1,
        "evidence_type": "responsive_avatar_hair_v4_isolated_visual_diagnostic",
        "status": (
            "DIAGNOSTIC_RENDER_CONTINUATION_COMPLETE_OWNER_VISUAL_DECISION_REQUIRED"
            if args.only_label is not None
            else "DIAGNOSTIC_RENDER_COMPLETE_OWNER_VISUAL_DECISION_REQUIRED"
        ),
        "only_label": args.only_label,
        "visual_quality_version": VISUAL_QUALITY_VERSION,
        "source_r15_blend": str(IMMUTABLE_R15_BLEND.relative_to(PROJECT_ROOT)).replace(
            "\\", "/"
        ),
        "source_r15_blend_sha256": IMMUTABLE_R15_BLEND_SHA256,
        "source_r15_build_evidence_sha256": IMMUTABLE_R15_BUILD_EVIDENCE_SHA256,
        "immutable_v3_provider_sha256": IMMUTABLE_V3_PROVIDER_SHA256,
        "v4_provider_path": str(V4_PROVIDER.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "v4_provider_sha256": _sha256(V4_PROVIDER),
        "v4_smoke_path": str(V4_SMOKE.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "v4_smoke_sha256": _sha256(V4_SMOKE),
        "hair_profile_sha256": PROFILE_SHA256,
        "authoring_seconds": authoring_seconds,
        "total_seconds": total_seconds,
        "render_count": len(renders),
        "render_engine": render_engine,
        "renders": renders,
        "hair_report": report,
        "candidate_build_performed": False,
        "blend_saved": False,
        "export_performed": False,
        "runtime_world_driver_proven": False,
        "glb_material_driver_morph_fidelity_proven": False,
        "activation_performed": False,
        "publication_performed": False,
        "source_r15_files_modified": False,
        "owner_visual_acceptance_claimed": False,
    }
    evidence_path = output_dir / "DIAGNOSTIC_EVIDENCE.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Recheck immutable inputs after all renders.  No save call occurs.
    _require_hash(IMMUTABLE_R15_BLEND, IMMUTABLE_R15_BLEND_SHA256, "r15_blend_post")
    _require_hash(
        IMMUTABLE_R15_BUILD_EVIDENCE,
        IMMUTABLE_R15_BUILD_EVIDENCE_SHA256,
        "r15_build_evidence_post",
    )
    _require_hash(IMMUTABLE_V3_PROVIDER, IMMUTABLE_V3_PROVIDER_SHA256, "v3_provider_post")
    print(
        "RESPONSIVE_HAIR_V4_DIAGNOSTIC_COMPLETE "
        + json.dumps(
            {
                "evidence": str(evidence_path),
                "evidence_sha256": _sha256(evidence_path),
                "render_count": len(renders),
                "render_sha256": {item["label"]: item["sha256"] for item in renders},
                "authoring_seconds": authoring_seconds,
                "total_seconds": total_seconds,
                "blend_saved": False,
                "candidate_build_performed": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
