"""Read-only in-memory visual probe for the isolated non-anatomy v2 adapter."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for entry in (PROJECT_ROOT, PROJECT_ROOT / "tools"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import blender_profiled_adult_candidate_components as v1  # noqa: E402
from blender_profiled_adult_candidate_components_v2 import (  # noqa: E402
    add_feminine_eye_surrounds_v2,
    add_subtle_lip_material_v2,
    apply_qualitative_face_geometry_v2,
    calibrate_warm_non_pale_skin_v2,
    component_bone_frame_v2,
    evaluated_knee_profile,
    install_knee_corrective_smoothing_v2,
    install_shadow_controlled_review_rig_v2,
    round_existing_nail_silhouettes_v2,
)


CANDIDATE_ID = "kira_profiled_adult_candidate_r15_20260801_114658"
CANDIDATE_DIR = PROJECT_ROOT / "Avatar" / "private_owner_review" / CANDIDATE_ID
BLEND_PATH = CANDIDATE_DIR / f"{CANDIDATE_ID}.blend"
EVIDENCE_PATH = CANDIDATE_DIR / "BUILD_EVIDENCE.json"
CONFIG_PATH = PROJECT_ROOT / "Avatar" / "avatar_builder" / "tooling" / "profiled_adult_candidate_builder_v1.json"
OUTPUT_DIR = (
    PROJECT_ROOT
    / "RecoverySprint"
    / "continuation_20260801"
    / "kira_nonanatomy_presentation_v2_probe"
    / "attempt_01"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON root is not object: {path}")
    return payload


def _bounds(objects: Sequence[Any]) -> tuple[Vector, Vector]:
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        for corner in obj.bound_box
        if obj.type in {"MESH", "CURVE"}
    ]
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def _center(objects: Sequence[Any]) -> Vector:
    low, high = _bounds(objects)
    return (low + high) * 0.5


def _render(
    scene: Any,
    camera: Any,
    label: str,
    target: Vector,
    direction: Vector,
    ortho_scale: float,
) -> dict[str, Any]:
    camera.location = target + direction.normalized() * 4.5
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = float(ortho_scale)
    path = OUTPUT_DIR / f"{label}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {
        "label": label,
        "path": path.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": _sha256(path),
        "target": [float(value) for value in target],
        "direction": [float(value) for value in direction.normalized()],
        "ortho_scale_m": float(ortho_scale),
    }


def _profile_improvement(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for side_name in ("anterior", "posterior"):
        pre = before[f"{side_name}_roughness"]
        post = after[f"{side_name}_roughness"]
        rows[side_name] = {
            "maximum_second_difference_ratio": (
                float(post["maximum_absolute_second_difference"])
                / float(pre["maximum_absolute_second_difference"])
            ),
            "mean_second_difference_ratio": (
                float(post["mean_absolute_second_difference"])
                / float(pre["mean_absolute_second_difference"])
            ),
        }
    depth_ratio = float(after["minimum_depth_m"]) / float(before["minimum_depth_m"])
    passed = (
        min(
            rows["anterior"]["maximum_second_difference_ratio"],
            rows["posterior"]["maximum_second_difference_ratio"],
        )
        <= 0.96
        and min(
            rows["anterior"]["mean_second_difference_ratio"],
            rows["posterior"]["mean_second_difference_ratio"],
        )
        <= 0.96
        and depth_ratio >= 0.85
    )
    return {
        "profiles": rows,
        "minimum_depth_ratio": depth_ratio,
        "at_least_one_silhouette_side_smoothed_four_percent": passed,
        "hard_silhouette_gate_passed": passed,
    }


def main() -> int:
    started = time.perf_counter()
    if OUTPUT_DIR.exists():
        raise RuntimeError(f"append-only output already exists: {OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    input_before = {"blend": _sha256(BLEND_PATH), "evidence": _sha256(EVIDENCE_PATH)}
    evidence = _read(EVIDENCE_PATH)
    config = _read(CONFIG_PATH)
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    body = next(
        obj for obj in scene.objects
        if obj.type == "MESH" and obj.get("primary_surface") is True
    )
    armature = next(obj for obj in scene.objects if obj.type == "ARMATURE")
    eye_objects = [obj for obj in scene.objects if obj.get("eye_component") is True]
    nail_objects = [obj for obj in scene.objects if obj.get("nail_component") is True]
    hair_objects = [obj for obj in scene.objects if obj.get("responsive_avatar_hair") is True]
    if len(eye_objects) != 6 or len(nail_objects) != 20:
        raise RuntimeError("R15 component inventory changed")
    for obj in hair_objects:
        obj.hide_render = True

    target_height = float(evidence["source"]["target_height_m"])
    camera, lighting = install_shadow_controlled_review_rig_v2(scene, target_height)
    low, high = _bounds([body])
    face_target = Vector((0.0, (low.y + high.y) * 0.5, high.z - target_height * 0.092))
    eye_target = _center([obj for obj in eye_objects if "brown_iris" in obj.name])
    renders: list[dict[str, Any]] = []
    v1.reset_pose(armature)
    renders.append(_render(scene, camera, "face_before_same_rig", face_target, Vector((0, -1, 0.01)), target_height * 0.34))
    renders.append(_render(scene, camera, "eyes_before_same_rig", eye_target, Vector((0, -1, 0.01)), target_height * 0.17))
    v1.apply_relaxed_hand_pose(armature, "L", target_height_m=target_height)
    hand_frame_before = component_bone_frame_v2(
        armature, side="L", kind="hand", view_direction=Vector((-0.12, -1.0, 0.18)), target_height_m=target_height
    )
    renders.append(_render(
        scene, camera, "left_hand_before_same_rig", Vector(hand_frame_before["target"]),
        Vector(hand_frame_before["view_direction"]), float(hand_frame_before["ortho_scale_m"]),
    ))
    v1.reset_pose(armature)
    foot_frame_before = component_bone_frame_v2(
        armature, side="L", kind="foot", view_direction=Vector((-0.08, -0.62, 0.78)), target_height_m=target_height
    )
    renders.append(_render(
        scene, camera, "left_foot_before_same_rig", Vector(foot_frame_before["target"]),
        Vector(foot_frame_before["view_direction"]), float(foot_frame_before["ortho_scale_m"]),
    ))
    v1.apply_knee_solution(armature, evidence["knees"]["solutions"]["left"])
    knee_center_left = armature.matrix_world @ armature.data.bones["lowerleg01.L"].head_local
    knee_before = evaluated_knee_profile(body, armature, "L", target_height)
    renders.append(_render(
        scene, camera, "left_knee_before_same_rig", knee_center_left,
        Vector((-0.55, -1.0, 0.10)), target_height * 0.43,
    ))
    v1.reset_pose(armature)

    base_path = PROJECT_ROOT / config["makehuman_source_set"]["base_body"]["path"]
    baseline_source = v1.prepare_profiled_body_source(
        base_path=base_path,
        female_macros=config["makehuman_source_set"]["female_macros"],
        resolved_style_targets=evidence["preflight"]["style_profile"]["resolved_targets"],
        project_root=PROJECT_ROOT,
        target_height_m=target_height,
    )
    face_geometry = apply_qualitative_face_geometry_v2(
        body=body,
        project_root=PROJECT_ROOT,
        base_body_path=base_path,
        baseline_source=baseline_source,
        target_height_m=target_height,
    )
    skin = calibrate_warm_non_pale_skin_v2(body)
    lips = add_subtle_lip_material_v2(body, face_geometry["lip_compact_vertex_indices"])
    facial_objects, eye_surrounds = add_feminine_eye_surrounds_v2(
        body=body,
        armature=armature,
        eye_objects=eye_objects,
        candidate_id=f"{CANDIDATE_ID}_presentation_v2_probe",
    )
    nails = round_existing_nail_silhouettes_v2(body, nail_objects)
    knee_correctives = install_knee_corrective_smoothing_v2(body, armature, target_height)
    bpy.context.view_layer.update()

    low_after, high_after = _bounds([body])
    face_target_after = Vector((0.0, (low_after.y + high_after.y) * 0.5, high_after.z - target_height * 0.092))
    eye_target_after = _center([obj for obj in eye_objects if "brown_iris" in obj.name])
    v1.reset_pose(armature)
    renders.append(_render(scene, camera, "face_after_v2", face_target_after, Vector((0, -1, 0.01)), target_height * 0.34))
    renders.append(_render(scene, camera, "face_after_v2_three_quarter", face_target_after, Vector((0.55, -1.0, 0.03)), target_height * 0.34))
    renders.append(_render(scene, camera, "eyes_after_v2", eye_target_after, Vector((0, -1, 0.01)), target_height * 0.17))
    v1.apply_relaxed_hand_pose(armature, "L", target_height_m=target_height)
    hand_frame_after = component_bone_frame_v2(
        armature, side="L", kind="hand", view_direction=Vector((-0.12, -1.0, 0.18)), target_height_m=target_height
    )
    renders.append(_render(
        scene, camera, "left_hand_after_v2_full_component", Vector(hand_frame_after["target"]),
        Vector(hand_frame_after["view_direction"]), float(hand_frame_after["ortho_scale_m"]),
    ))
    v1.reset_pose(armature)
    foot_frame_after = component_bone_frame_v2(
        armature, side="L", kind="foot", view_direction=Vector((-0.08, -0.62, 0.78)), target_height_m=target_height
    )
    renders.append(_render(
        scene, camera, "left_foot_after_v2_full_component", Vector(foot_frame_after["target"]),
        Vector(foot_frame_after["view_direction"]), float(foot_frame_after["ortho_scale_m"]),
    ))
    v1.apply_knee_solution(armature, evidence["knees"]["solutions"]["left"])
    knee_after = evaluated_knee_profile(body, armature, "L", target_height)
    renders.append(_render(
        scene, camera, "left_knee_after_v2", knee_center_left,
        Vector((-0.55, -1.0, 0.10)), target_height * 0.43,
    ))
    v1.reset_pose(armature)
    v1.apply_knee_solution(armature, evidence["knees"]["solutions"]["right"])
    knee_center_right = armature.matrix_world @ armature.data.bones["lowerleg01.R"].head_local
    knee_after_right = evaluated_knee_profile(body, armature, "R", target_height)
    renders.append(_render(
        scene, camera, "right_knee_after_v2", knee_center_right,
        Vector((0.55, -1.0, 0.10)), target_height * 0.43,
    ))
    v1.reset_pose(armature)

    knee_improvement = _profile_improvement(knee_before, knee_after)
    input_after = {"blend": _sha256(BLEND_PATH), "evidence": _sha256(EVIDENCE_PATH)}
    report = {
        "schema_version": 1,
        "probe": "profiled_adult_nonanatomy_presentation_v2_read_only_r15_probe",
        "status": "PROBE_COMPLETED_VISUAL_REVIEW_REQUIRED",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_input": CANDIDATE_ID,
        "input_before": input_before,
        "input_after": input_after,
        "input_bytes_unchanged": input_after == input_before,
        "blend_saved": False,
        "candidate_directory_written": False,
        "runtime_activation_allowed": False,
        "publication_allowed": False,
        "hair_scope": "HIDDEN_UNCHANGED_NOT_PART_OF_THIS_PROBE",
        "adult_surface_scope": "UNMODIFIED_EXCEPT_FACE_REGION_OFFICIAL_TARGET_DELTAS_IN_MEMORY",
        "lighting": lighting,
        "face_geometry": {key: value for key, value in face_geometry.items() if key != "lip_compact_vertex_indices"},
        "skin": skin,
        "lips": lips,
        "eye_surrounds": eye_surrounds,
        "facial_presentation_object_names": [obj.name for obj in facial_objects],
        "nails": nails,
        "component_frames": {
            "hand_before": hand_frame_before,
            "hand_after": hand_frame_after,
            "foot_before": foot_frame_before,
            "foot_after": foot_frame_after,
        },
        "knee_correctives": knee_correctives,
        "knee_profiles": {
            "left_before": knee_before,
            "left_after": knee_after,
            "right_after": knee_after_right,
            "left_improvement_gate": knee_improvement,
        },
        "renders": renders,
        "render_count": len(renders),
        "elapsed_seconds": time.perf_counter() - started,
        "truth_boundaries": {
            "owner_visual_acceptance": False,
            "identity_match_claim": False,
            "qualitative_face_target_direction_only": True,
            "runtime_or_export_survival_proven": False,
            "future_builder_integration_performed": False,
        },
    }
    report_path = OUTPUT_DIR / "PRESENTATION_V2_PROBE_REPORT.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "report": report_path.relative_to(PROJECT_ROOT).as_posix(),
        "report_sha256": _sha256(report_path),
        "render_count": len(renders),
        "input_bytes_unchanged": report["input_bytes_unchanged"],
        "hard_face_geometry_gate_passed": face_geometry["hard_face_geometry_gate_passed"],
        "knee_silhouette_gate_passed": knee_improvement["hard_silhouette_gate_passed"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
