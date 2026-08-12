"""Final append-only private visual probe for adult-surface delivery v5.

This script consumes the exact R17 attempt-05 staging checkpoint, applies only
the v5 coordinate repair, saves a new private staging checkpoint, and renders
exactly two diagnostic views (front and three-quarter).  It never creates an
owner-review candidate, exports a runtime asset, assigns or activates a body,
adds hair/clothing, or mutates the source checkpoint or live Kira selection.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tools.blender_build_profiled_kira_bald_delivery_candidate as r16
from Core.avatar_adult_female_surface_delivery_v5 import parameters_from_mapping
from Core.avatar_profiled_adult_candidate_contract import (
    capture_live_kira_state_hashes,
)
from tools.blender_author_adult_female_external_surface_delivery_v5 import (
    repair_existing_continuous_adult_female_surface_delivery_v5,
)
from tools.blender_avatar_human_pose_clearance_v1 import reset_pose_v1


EXPECTED_SOURCE_SHA256 = (
    "6ecb8703d2a670e0cfec253c061a578f052667cb0db2519690fd1a2f190533f6"
)


class AdultFemaleSurfaceDeliveryV5ProbeError(RuntimeError):
    """Raised when the final bounded private probe loses an invariant."""


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-blend", required=True)
    parser.add_argument("--output-dir", required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _scaled_parameters(
    config: Mapping[str, Any],
    body_height_m: float,
) -> Any:
    ratio = float(body_height_m) / float(config["baseline_height_m"])
    values = dict(config["parameters"])
    for name in (
        "harmonic_tolerance_m",
        "front_prominence_scale_m",
        "maximum_total_correction_m",
    ):
        values[name] = float(values[name]) * ratio
    values["degeneracy_area_m2"] = (
        float(values["degeneracy_area_m2"]) * ratio * ratio
    )
    return parameters_from_mapping(values)


def _neutral_profiled_positions(body_height_m: float) -> tuple[list[Vector], dict[str, Any]]:
    config, config_report = r16.load_validated_profiled_candidate_builder_config(
        PROJECT_ROOT
    )
    profile = r16._read_json(PROJECT_ROOT / config["style_profile"]["path"])
    prepared = r16.prepare_profiled_body_source(
        base_path=PROJECT_ROOT / config["makehuman_source_set"]["base_body"]["path"],
        female_macros=config["makehuman_source_set"]["female_macros"],
        resolved_style_targets=[
            dict(row, verified=True) for row in profile["shape_targets"]
        ],
        project_root=PROJECT_ROOT,
        target_height_m=float(body_height_m),
    )
    positions = [Vector(point) for point in prepared["body_vertices"]]
    return positions, {
        "vertex_count": len(positions),
        "target_height_m": float(body_height_m),
        "style_target_ids_in_application_order": prepared[
            "style_target_ids_in_application_order"
        ],
        "style_target_count": prepared["style_target_count"],
        "body_face_group_only": prepared["body_face_group_only"],
        "copied_anatomy_geometry_used": prepared["copied_anatomy_geometry_used"],
        "male_helper_groups_used": prepared["male_helper_groups_used"],
        "builder_config_sha256": config_report["config_sha256"],
        "style_profile_path": config["style_profile"]["path"],
        "style_profile_sha256": config["style_profile"]["sha256"],
        "face_v3_overlap_expected": False,
        "reason": "bounded face-v3 edits are head-only; pelvic anchor indices retain the exact profiled source correspondence",
    }


def _render(
    *,
    scene: Any,
    camera: Any,
    path: Path,
    target: Vector,
    direction: Vector,
    ortho_scale: float,
) -> dict[str, Any]:
    camera.location = target + direction.normalized() * max(3.0, ortho_scale * 3.2)
    r16.r15._look_at(camera, target)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = float(ortho_scale)
    scene.render.resolution_x = 720
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {"path": path.name, "sha256": r16.r15.sha256_file(path)}


def _run(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    source_path = (PROJECT_ROOT / args.source_blend).resolve(strict=True)
    source_hash_before = r16.r15.sha256_file(source_path)
    if source_hash_before != EXPECTED_SOURCE_SHA256:
        raise AdultFemaleSurfaceDeliveryV5ProbeError(
            "exact attempt-05 staging checkpoint hash mismatch"
        )
    live_before = capture_live_kira_state_hashes(PROJECT_ROOT)
    bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)
    scene = bpy.context.scene
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    body = max(
        (
            obj
            for obj in bpy.data.objects
            if obj.type == "MESH" and bool(obj.get("primary_surface"))
        ),
        key=lambda obj: len(obj.data.vertices),
    )
    body_height_m = 1.651
    reset_pose_v1(armature)

    neutral_positions, neutral_report = _neutral_profiled_positions(body_height_m)
    config_path = (
        PROJECT_ROOT
        / "Avatar/avatar_builder/tooling/adult_female_surface_delivery_v5_final_bounded_repair.json"
    )
    component_config = _read_json(config_path)
    ratio = body_height_m / float(component_config["baseline_height_m"])
    parameters = _scaled_parameters(component_config, body_height_m)
    repair_report = repair_existing_continuous_adult_female_surface_delivery_v5(
        body,
        neutral_original_positions=neutral_positions,
        front_frame=r16._scaled_frame(
            component_config["front_visible_sheet_frame"],
            ratio,
        ),
        parameters=parameters,
        project_root=PROJECT_ROOT,
    )
    if repair_report["selected_front_component_vertex_count"] != 5478:
        raise AdultFemaleSurfaceDeliveryV5ProbeError(
            "front component count drifted from inspected staging"
        )
    if repair_report["selected_front_anchor_neighbor_count"] != 134:
        raise AdultFemaleSurfaceDeliveryV5ProbeError(
            "front anchor-neighbor count drifted from inspected staging"
        )
    if repair_report["rear_component_vertex_count_preserved"] != 339:
        raise AdultFemaleSurfaceDeliveryV5ProbeError(
            "rear component count drifted from inspected staging"
        )
    if repair_report["new_global_nonadjacent_self_intersection_pairs"] != 0:
        raise AdultFemaleSurfaceDeliveryV5ProbeError(
            "v5 repair created a new global intersection"
        )
    if repair_report["changed_vertex_count_outside_front_component"] != 0:
        raise AdultFemaleSurfaceDeliveryV5ProbeError(
            "v5 repair changed coordinates outside the front component"
        )

    staging_path = output_dir / "r17_surface_v5_final_private_staging.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(staging_path), check_existing=False)
    staging_record = {
        "path": staging_path.name,
        "sha256": r16.r15.sha256_file(staging_path),
        "private_component_checkpoint_only": True,
        "owner_review_candidate": False,
        "runtime_activation_allowed": False,
    }

    for obj in bpy.data.objects:
        if "seat" in obj.name.casefold():
            obj.hide_render = True
    camera = scene.camera or next(
        obj for obj in bpy.data.objects if obj.type == "CAMERA"
    )
    protected_target = Vector(
        (0.0, -0.07 * body_height_m / 1.7, 0.79 * body_height_m / 1.7)
    )
    renders: list[dict[str, Any]] = []
    for label, direction in (
        ("surface_v5_front", Vector((0.0, -1.0, 0.02))),
        ("surface_v5_three_quarter", Vector((0.72, -0.70, 0.02))),
    ):
        row = _render(
            scene=scene,
            camera=camera,
            path=output_dir / f"{label}.png",
            target=protected_target,
            direction=direction,
            ortho_scale=body_height_m * 0.29,
        )
        renders.append({"label": label, **row})

    source_hash_after = r16.r15.sha256_file(source_path)
    live_after = capture_live_kira_state_hashes(PROJECT_ROOT)
    evidence = {
        "schema_version": 1,
        "status": "FINAL_BOUNDED_SURFACE_V5_VISUAL_ATTEMPT_2_RENDERED",
        "source_blend": args.source_blend,
        "expected_source_blend_sha256": EXPECTED_SOURCE_SHA256,
        "source_blend_sha256_before": source_hash_before,
        "source_blend_sha256_after": source_hash_after,
        "source_blend_unchanged": source_hash_after == source_hash_before,
        "neutral_anchor_reconstruction": neutral_report,
        "component_config": config_path.relative_to(PROJECT_ROOT).as_posix(),
        "component_config_sha256": r16.r15.sha256_file(config_path),
        "repair": repair_report,
        "staging_checkpoint": staging_record,
        "renders": renders,
        "render_count": len(renders),
        "render_scope": ["front", "three_quarter"],
        "visual_attempt_number": 2,
        "prior_pre_render_failure_preserved": {
            "path": "RecoverySprint/continuation_20260801/kira_r17_surface_v5_final_visual_probe/attempt_02/FAILURE.json",
            "reason": "the original 0.1-micrometre solver threshold was stricter than required; no staging save or render occurred",
            "visual_attempt_consumed": False
        },
        "v6_allowed_after_this_attempt": False,
        "owner_review_candidate_created": False,
        "candidate_created": False,
        "glb_exported": False,
        "runtime_activation_allowed": False,
        "assignment_performed": False,
        "publication_performed": False,
        "hair_created_or_loaded": False,
        "source_anatomy_geometry_copied": False,
        "live_state_before": live_before,
        "live_state_after": live_after,
        "live_state_unchanged": live_before == live_after,
        "owner_visual_review_required": True,
    }
    if not evidence["source_blend_unchanged"] or not evidence["live_state_unchanged"]:
        raise AdultFemaleSurfaceDeliveryV5ProbeError(
            "source staging checkpoint or live Kira state changed"
        )
    return evidence


def main() -> int:
    args = _args()
    output_dir = (PROJECT_ROOT / args.output_dir).resolve()
    output_dir.relative_to(PROJECT_ROOT)
    if output_dir.exists():
        raise AdultFemaleSurfaceDeliveryV5ProbeError(
            "append-only v5 probe output already exists"
        )
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        evidence = _run(args, output_dir)
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "status": "FINAL_BOUNDED_SURFACE_V5_VISUAL_ATTEMPT_2_FAILED",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "candidate_created": False,
            "runtime_activation_allowed": False,
            "v6_allowed_after_this_attempt": False,
        }
        (output_dir / "FAILURE.json").write_text(
            json.dumps(failure, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        raise
    evidence_path = output_dir / "PROBE_EVIDENCE.json"
    evidence_path.write_text(
        json.dumps(r16.r15._json_safe(evidence), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "output": args.output_dir,
                "render_count": evidence["render_count"],
                "staging_sha256": evidence["staging_checkpoint"]["sha256"],
                "evidence_sha256": r16.r15.sha256_file(evidence_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
