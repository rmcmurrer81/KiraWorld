"""Bounded in-memory visual probe for the targeted R17 Kira corrections.

The exact R16 owner-review blend is opened read-only.  This probe replaces only
the components rejected in the owner's R16 review: qualitative face direction,
organic adult-surface relief, regional appearance/continuous brows, natural
nails, and seated-contact pose logic.  It writes diagnostic PNG/JSON evidence
under RecoverySprint, but never saves a blend, exports an avatar, or mutates the
live Kira selection.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tools.blender_build_profiled_kira_bald_delivery_candidate as r16
from Core.avatar_adult_female_surface_delivery_v4 import (
    parameters_from_mapping as organic_parameters_from_mapping,
)
from Core.avatar_profiled_adult_candidate_contract import (
    capture_live_kira_state_hashes,
)
from tools.blender_author_adult_female_external_surface_delivery_v4 import (
    refine_existing_continuous_adult_female_surface_delivery_v4,
)
from tools.blender_avatar_human_pose_clearance_v1 import (
    apply_pose_foundation_v1,
    reset_pose_v1,
)
from tools.blender_avatar_natural_nail_delivery_v3 import add_natural_nails_v3
from tools.blender_kira_appearance_delivery_v3 import (
    apply_kira_appearance_delivery_v3,
)
from tools.blender_kira_face_delivery_v3 import (
    apply_kira_face_direction_to_source_v3,
)
from tools.blender_profiled_adult_candidate_components_v2 import (
    component_bone_frame_v2,
)


class KiraR17IntegratedProbeError(RuntimeError):
    """Raised when a bounded probe invariant fails."""


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-blend", required=True)
    parser.add_argument("--output-dir", required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _scaled_parameters(
    config: Mapping[str, Any], body_height_m: float
) -> Any:
    ratio = float(body_height_m) / float(config["baseline_height_m"])
    values = dict(config["parameters"])
    for name in (
        "front_prominence_scale_m",
        "rear_prominence_scale_m",
        "fairing_max_step_m",
        "maximum_total_correction_m",
    ):
        values[name] = float(values[name]) * ratio
    values["degeneracy_area_m2"] = float(values["degeneracy_area_m2"]) * ratio * ratio
    return organic_parameters_from_mapping(values)


def _apply_face_delta(body: Any, body_height_m: float) -> dict[str, Any]:
    config, _report = r16.load_validated_profiled_candidate_builder_config(PROJECT_ROOT)
    profile = r16._read_json(PROJECT_ROOT / config["style_profile"]["path"])
    resolved_style = [dict(row, verified=True) for row in profile["shape_targets"]]
    source = r16.prepare_profiled_body_source(
        base_path=PROJECT_ROOT / config["makehuman_source_set"]["base_body"]["path"],
        female_macros=config["makehuman_source_set"]["female_macros"],
        resolved_style_targets=resolved_style,
        project_root=PROJECT_ROOT,
        target_height_m=float(body_height_m),
    )
    baseline = [point.copy() for point in source["body_vertices"]]
    report = apply_kira_face_direction_to_source_v3(
        source,
        project_root=PROJECT_ROOT,
        target_height_m=float(body_height_m),
    )
    if len(body.data.vertices) < len(baseline):
        raise KiraR17IntegratedProbeError("R16 body lost source-stable face vertices")
    changed = 0
    maximum = 0.0
    for index, (before, after) in enumerate(zip(baseline, source["body_vertices"])):
        delta = after - before
        if delta.length > 1.0e-12:
            body.data.vertices[index].co += delta
            changed += 1
            maximum = max(maximum, float(delta.length))
    reported_vertices = int(report["changed_vertex_count"])
    if changed <= 0 or changed > reported_vertices:
        raise KiraR17IntegratedProbeError(
            "face source/body nonzero changed-vertex subset is invalid"
        )
    body.data.update()
    bpy.context.view_layer.update()
    report["applied_to_existing_body_vertex_count"] = changed
    report["reported_accumulated_target_vertex_count"] = reported_vertices
    report["zero_or_cancelling_net_delta_vertex_count"] = reported_vertices - changed
    report["maximum_applied_body_delta_m"] = maximum
    report["identity_match_claim_allowed"] = False
    return report


def _apply_organic_surface(body: Any, body_height_m: float) -> dict[str, Any]:
    config_v4 = _read_json(
        PROJECT_ROOT
        / "Avatar/avatar_builder/tooling/adult_female_surface_delivery_v4_inactive_refinement.json"
    )
    config_v3 = _read_json(
        PROJECT_ROOT
        / "Avatar/avatar_builder/tooling/adult_female_surface_v3_inactive_refinement.json"
    )
    ratio_v4 = float(body_height_m) / float(config_v4["baseline_height_m"])
    ratio_v3 = float(body_height_m) / float(config_v3["baseline_height_m"])
    return refine_existing_continuous_adult_female_surface_delivery_v4(
        body,
        front_frame=r16._scaled_frame(config_v4["front_visible_sheet_frame"], ratio_v4),
        rear_frame=r16._scaled_frame(config_v4["rear_anal_sheet_frame"], ratio_v4),
        parameters=_scaled_parameters(config_v4, body_height_m),
        legacy_v3_front_prominence_scale_m=float(
            config_v3["parameters"]["front_prominence_scale_m"]
        )
        * ratio_v3,
        legacy_v3_rear_prominence_scale_m=float(
            config_v3["parameters"]["rear_prominence_scale_m"]
        )
        * ratio_v3,
        legacy_v3_minimum_front_normal_alignment=float(
            config_v3["parameters"]["minimum_front_normal_alignment"]
        ),
        legacy_v3_minimum_rear_normal_alignment=float(
            config_v3["parameters"]["minimum_rear_normal_alignment"]
        ),
        front_visible_sheet_minimum_outward_depth_m=float(
            config_v4["surface_selection"][
                "front_visible_sheet_minimum_outward_depth_m"
            ]
        )
        * ratio_v4,
        rear_visible_sheet_minimum_outward_depth_m=float(
            config_v4["surface_selection"][
                "rear_visible_sheet_minimum_outward_depth_m"
            ]
        )
        * ratio_v4,
        project_root=PROJECT_ROOT,
    )


def _remove_old_nails() -> list[str]:
    removed: list[str] = []
    for obj in list(bpy.data.objects):
        if not bool(obj.get("nail_component")):
            continue
        removed.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)
    if len(removed) != 20:
        raise KiraR17IntegratedProbeError(
            f"expected 20 superseded R16 nails, found {len(removed)}"
        )
    return sorted(removed)


def _bounds(objects: Sequence[Any]) -> tuple[Vector, Vector]:
    return r16.r15._world_bounds(objects)


def _seat_top_z(seat: Any) -> float:
    return max(float((seat.matrix_world @ Vector(corner)).z) for corner in seat.bound_box)


def _render(
    *,
    scene: Any,
    camera: Any,
    path: Path,
    target: Vector,
    direction: Vector,
    ortho_scale: float,
    portrait: bool,
) -> dict[str, Any]:
    camera.location = target + direction.normalized() * max(3.0, ortho_scale * 3.2)
    r16.r15._look_at(camera, target)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = float(ortho_scale)
    scene.render.resolution_x = 720
    scene.render.resolution_y = 880 if portrait else 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {"path": path.name, "sha256": r16.r15.sha256_file(path)}


def _render_probe_views(
    *,
    output_dir: Path,
    scene: Any,
    body: Any,
    armature: Any,
    eye_objects: Sequence[Any],
    nail_objects: Sequence[Any],
    body_height_m: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    camera = scene.camera or next(obj for obj in bpy.data.objects if obj.type == "CAMERA")
    seat = bpy.data.objects.get("Kira_Private_Seat_Contact_Diagnostic")
    if seat is None:
        seat = r16._add_private_seat_prop(body_height_m)
    seat.hide_render = True
    low, high = _bounds([body])
    mid_y = (low.y + high.y) * 0.5
    body_target = Vector((0.0, mid_y, low.z + body_height_m * 0.51))
    face_target = Vector((0.0, mid_y, high.z - body_height_m * 0.085))
    protected_target = Vector((0.0, -0.07 * body_height_m / 1.7, 0.79 * body_height_m / 1.7))
    renders: list[dict[str, Any]] = []

    reset_pose_v1(armature)
    for label, target, direction, scale, portrait in (
        ("corrected_full_front", body_target, Vector((0.0, -1.0, 0.03)), body_height_m * 1.12, True),
        ("corrected_full_rear", body_target, Vector((0.0, 1.0, 0.03)), body_height_m * 1.12, True),
        ("corrected_full_left_three_quarter", body_target, Vector((-0.68, -0.73, 0.03)), body_height_m * 1.12, True),
        ("corrected_face_front", face_target, Vector((0.0, -1.0, 0.01)), body_height_m * 0.33, False),
        ("corrected_face_left_three_quarter", face_target, Vector((-0.68, -0.73, 0.01)), body_height_m * 0.33, False),
        ("corrected_crown_top_scalp", Vector((0.0, mid_y, high.z - body_height_m * 0.08)), Vector((0.0, -0.10, 1.0)), body_height_m * 0.36, False),
        ("corrected_rear_scalp_hairline", face_target, Vector((0.0, 1.0, 0.01)), body_height_m * 0.36, False),
        ("corrected_surface_front", protected_target, Vector((0.0, -1.0, 0.02)), body_height_m * 0.29, False),
        ("corrected_surface_three_quarter", protected_target, Vector((0.72, -0.70, 0.02)), body_height_m * 0.29, False),
    ):
        row = _render(
            scene=scene,
            camera=camera,
            path=output_dir / f"{label}.png",
            target=target,
            direction=direction,
            ortho_scale=scale,
            portrait=portrait,
        )
        renders.append({"label": label, **row})

    nail_frames = {
        "corrected_left_hand_nails": component_bone_frame_v2(
            armature,
            side="L",
            kind="hand",
            view_direction=r16.r15._named_review_normal(
                nail_objects, "fingernail_3_L", Vector((0.0, -1.0, 0.25))
            ),
            target_height_m=body_height_m,
        ),
        "corrected_left_foot_nails": component_bone_frame_v2(
            armature,
            side="L",
            kind="foot",
            view_direction=r16.r15._named_review_normal(
                nail_objects, "toenail_1_L", Vector((0.0, -0.35, 1.0))
            ),
            target_height_m=body_height_m,
        ),
    }
    for label, frame in nail_frames.items():
        row = _render(
            scene=scene,
            camera=camera,
            path=output_dir / f"{label}.png",
            target=Vector(tuple(frame["target"])),
            direction=Vector(tuple(frame["view_direction"])),
            ortho_scale=float(frame["ortho_scale_m"]),
            portrait=False,
        )
        renders.append({"label": label, **row})

    knee_report = r16.solve_bilateral_knee_axes_and_actions(armature, body)
    r16._apply_bilateral_knee_pose(armature, knee_report)
    knee_left = armature.matrix_world @ armature.data.bones["lowerleg01.L"].head_local
    knee_right = armature.matrix_world @ armature.data.bones["lowerleg01.R"].head_local
    knee_center = (knee_left + knee_right) * 0.5
    row = _render(
        scene=scene,
        camera=camera,
        path=output_dir / "corrected_bilateral_knee_bend.png",
        target=knee_center,
        direction=Vector((0.0, -1.0, 0.08)),
        ortho_scale=body_height_m * 0.62,
        portrait=False,
    )
    renders.append({"label": "corrected_bilateral_knee_bend", **row})

    seat.hide_render = False
    seated_report = apply_pose_foundation_v1(
        armature=armature,
        body=body,
        pose_name="seated",
        body_height_m=body_height_m,
        seat_top_z_m=_seat_top_z(seat),
    )
    for label, direction in (
        ("corrected_seated_front_three_quarter", Vector((0.68, -1.0, 0.07))),
        ("corrected_seated_side_contact", Vector((1.0, 0.0, 0.035))),
    ):
        row = _render(
            scene=scene,
            camera=camera,
            path=output_dir / f"{label}.png",
            target=Vector((0.0, 0.0, body_height_m * 0.43)),
            direction=direction,
            ortho_scale=body_height_m * 0.98,
            portrait=True,
        )
        renders.append({"label": label, **row})
    seat.hide_render = True
    reset_pose_v1(armature)
    return renders, {
        "knee_axis_report": knee_report,
        "seated_pose_report": seated_report,
        "seat_object": seat.name,
        "seat_top_z_m": _seat_top_z(seat),
        "neutral_pose_restored_after_render": True,
    }


def main() -> int:
    args = _args()
    source_path = (PROJECT_ROOT / args.source_blend).resolve(strict=True)
    output_dir = (PROJECT_ROOT / args.output_dir).resolve()
    output_dir.relative_to(PROJECT_ROOT)
    if output_dir.exists():
        raise KiraR17IntegratedProbeError("probe output already exists")
    output_dir.mkdir(parents=True, exist_ok=False)
    source_hash_before = r16.r15.sha256_file(source_path)
    live_before = capture_live_kira_state_hashes(PROJECT_ROOT)

    bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)
    scene = bpy.context.scene
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    body = max(
        (obj for obj in bpy.data.objects if obj.type == "MESH" and obj.get("primary_surface")),
        key=lambda obj: len(obj.data.vertices),
    )
    body_height_m = 1.651
    preview_id = f"kira_r17_integrated_visual_probe_{output_dir.name}"
    reset_pose_v1(armature)

    face_report = _apply_face_delta(body, body_height_m)
    surface_report = _apply_organic_surface(body, body_height_m)
    eye_objects = [
        obj
        for obj in bpy.data.objects
        if obj.get("candidate_id") and any(
            token in obj.name.casefold()
            for token in ("sclera", "iris", "cornea")
        )
    ]
    old_facial = [
        obj for obj in bpy.data.objects if obj.get("facial_presentation_role")
    ]
    superseded_candidate_ids = sorted(
        {str(obj.get("candidate_id") or "") for obj in old_facial}
    )
    for obj in old_facial:
        obj["superseded_from_candidate_id"] = str(obj.get("candidate_id") or "")
        obj["candidate_id"] = preview_id
    facial_objects, appearance_report = apply_kira_appearance_delivery_v3(
        body=body,
        armature=armature,
        eye_objects=eye_objects,
        candidate_id=preview_id,
        project_root=PROJECT_ROOT,
        superseded_facial_objects=old_facial,
    )
    appearance_report["explicit_superseded_candidate_ids"] = superseded_candidate_ids
    removed_nails = _remove_old_nails()
    nail_objects, nail_report = add_natural_nails_v3(
        body=body,
        armature=armature,
        target_height_m=body_height_m,
        candidate_id=preview_id,
    )
    reset_pose_v1(armature)
    staging_path = output_dir / "r17_corrected_components_private_staging.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(staging_path), check_existing=False)
    staging_record = {
        "path": staging_path.name,
        "sha256": r16.r15.sha256_file(staging_path),
        "purpose": "private neutral component checkpoint only; not an owner-review candidate",
        "candidate_created": False,
        "runtime_activation_allowed": False,
    }
    renders, pose_report = _render_probe_views(
        output_dir=output_dir,
        scene=scene,
        body=body,
        armature=armature,
        eye_objects=eye_objects,
        nail_objects=nail_objects,
        body_height_m=body_height_m,
    )

    live_after = capture_live_kira_state_hashes(PROJECT_ROOT)
    source_hash_after = r16.r15.sha256_file(source_path)
    evidence = {
        "schema_version": 1,
        "status": "IN_MEMORY_TARGETED_R17_CORRECTIONS_RENDERED_FOR_FINAL_BOUNDED_VISUAL_CHECK",
        "source_blend": args.source_blend,
        "source_blend_sha256_before": source_hash_before,
        "source_blend_sha256_after": source_hash_after,
        "source_blend_unchanged": source_hash_after == source_hash_before,
        "face": face_report,
        "organic_surface": surface_report,
        "appearance": appearance_report,
        "facial_objects": [obj.name for obj in facial_objects],
        "superseded_r16_nails_removed": removed_nails,
        "natural_nails": nail_report,
        "poses": pose_report,
        "renders": renders,
        "staging_checkpoint": staging_record,
        "blend_saved": True,
        "owner_review_candidate_blend_saved": False,
        "glb_exported": False,
        "candidate_created": False,
        "runtime_activation_allowed": False,
        "live_state_before": live_before,
        "live_state_after": live_after,
        "live_state_unchanged": live_before == live_after,
        "scalp_hair_objects_created": False,
        "identity_match_claim_allowed": False,
        "owner_visual_review_required": True,
    }
    if not evidence["source_blend_unchanged"] or not evidence["live_state_unchanged"]:
        raise KiraR17IntegratedProbeError("source blend or live Kira state changed")
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
                "render_count": len(renders),
                "evidence_sha256": r16.r15.sha256_file(evidence_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
