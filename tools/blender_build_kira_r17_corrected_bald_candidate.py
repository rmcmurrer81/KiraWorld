"""Build the append-only, inactive R17 Kira bald owner-review candidate.

This is a surgical successor to R16.  It opens the exact rejected R16 blend,
reuses the accepted body/rig/eyes/knee-smoothing foundation, and replaces only
the owner-rejected face direction, adult-surface relief, skin/face appearance,
nails, and contact-pose presentation.  It creates no hair, GLB, clothing,
runtime assignment, activation, publication, or upload.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tools.blender_build_profiled_kira_bald_delivery_candidate as r16
import tools.blender_probe_kira_r17_integrated_corrections as integrated
from Core.avatar_profiled_adult_candidate_contract import (
    capture_live_kira_state_hashes,
)
from tools.blender_avatar_human_pose_clearance_v1 import (
    apply_pose_foundation_v1,
    reset_pose_v1,
)
from tools.blender_avatar_natural_nail_delivery_v3 import add_natural_nails_v3
from tools.blender_kira_appearance_delivery_v3 import (
    apply_kira_appearance_delivery_v3,
)


class KiraR17BuildError(RuntimeError):
    """Raised before an R17 result may be called reviewable."""


R16_SOURCE_RELATIVE = Path(
    "Avatar/private_owner_review/"
    "kira_profiled_adult_candidate_r16_bald_delivery_20260801_134650/"
    "kira_profiled_adult_candidate_r16_bald_delivery_20260801_134650.blend"
)
R16_SOURCE_SHA256 = "2d1f967564fc8218c42751330706816bdbdbdb459e9f7d97e5f964e2491f4ec3"
R16_EVIDENCE_RELATIVE = R16_SOURCE_RELATIVE.parent / "BUILD_EVIDENCE.json"
R16_EVIDENCE_SHA256 = "3bfd9132085dd9ed05b1e01fd2b2d43cd904ca663f161cdb8023b7c6277e3d28"
TARGET_HEIGHT_M = 1.651
IMPLEMENTATION_PATHS = (
    Path("tools/blender_build_kira_r17_corrected_bald_candidate.py"),
    Path("tools/blender_probe_kira_r17_integrated_corrections.py"),
    Path("Core/avatar_kira_face_delivery_v3.py"),
    Path("tools/blender_kira_face_delivery_v3.py"),
    Path("Core/avatar_adult_female_surface_delivery_v4.py"),
    Path("tools/blender_author_adult_female_external_surface_delivery_v4.py"),
    Path("Avatar/avatar_builder/tooling/adult_female_surface_delivery_v4_inactive_refinement.json"),
    Path("Core/avatar_kira_appearance_delivery_v3.py"),
    Path("tools/blender_kira_appearance_delivery_v3.py"),
    Path("Avatar/avatar_builder/tooling/kira_appearance_delivery_v3.json"),
    Path("Core/avatar_natural_nail_delivery_v3.py"),
    Path("tools/blender_avatar_natural_nail_delivery_v3.py"),
    Path("Avatar/avatar_builder/tooling/natural_nail_delivery_v3.json"),
    Path("Core/avatar_human_pose_clearance_v1.py"),
    Path("tools/blender_avatar_human_pose_clearance_v1.py"),
    Path("Avatar/avatar_builder/tooling/human_pose_clearance_contact_v1.json"),
)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-blend", default=R16_SOURCE_RELATIVE.as_posix())
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--acknowledge-inactive-private-candidate", action="store_true"
    )
    parser.add_argument("--render-owner-review", action="store_true")
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def _hash_bindings() -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in IMPLEMENTATION_PATHS:
        path = PROJECT_ROOT / relative
        if not path.is_file():
            raise KiraR17BuildError(f"required implementation file missing: {relative}")
        result[relative.as_posix()] = r16.r15.sha256_file(path)
    return result


def _remove_private_pose_props() -> list[str]:
    removed: list[str] = []
    for obj in list(bpy.data.objects):
        if bool(obj.get("private_review_prop_only")) or obj.name.startswith(
            "Kira_Private_Seat_Contact_Diagnostic"
        ):
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    return sorted(removed)


def _candidate_inventory(body: Any, armature: Any) -> tuple[list[Any], list[Any]]:
    eye_objects = [
        obj
        for obj in bpy.data.objects
        if obj not in {body, armature}
        and any(token in obj.name.casefold() for token in ("sclera", "iris", "cornea"))
    ]
    old_facial = [
        obj for obj in bpy.data.objects if obj.get("facial_presentation_role")
    ]
    if len(eye_objects) != 6 or len(old_facial) != 6:
        raise KiraR17BuildError(
            f"R16 reusable inventory drifted: eyes={len(eye_objects)} facial={len(old_facial)}"
        )
    return eye_objects, old_facial


def _retag_reused_objects(
    objects: Sequence[Any], *, old_id: str, candidate_id: str
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for obj in objects:
        old_name = obj.name
        if old_name.startswith(old_id):
            obj.name = candidate_id + old_name[len(old_id) :]
        obj["candidate_id"] = candidate_id
        obj["inactive_candidate"] = True
        obj["private_owner_review_only"] = True
        obj["runtime_activation_allowed"] = False
        obj["reused_from_r16"] = True
        records.append({"old_name": old_name, "new_name": obj.name})
    return records


def _seat_top_z(seat: Any) -> float:
    return max(float((seat.matrix_world @ Vector(corner)).z) for corner in seat.bound_box)


def _core_owner_review(
    *,
    scene: Any,
    output_dir: Path,
    body: Any,
    armature: Any,
    candidate_objects: Sequence[Any],
    protected_target: Vector,
) -> tuple[dict[str, Any], dict[str, Any]]:
    engineering_knees = r16.solve_bilateral_knee_axes_and_actions(armature, body)
    review_knees = deepcopy(engineering_knees)
    for solution in review_knees["solutions"].values():
        solution["signed_angle_degrees"] = 30.0 * float(solution.get("sign", 1.0))
        solution["owner_review_angle_reason"] = (
            "30 degrees is the validated smooth moderate-bend gate; deep flexion is "
            "shown separately by the measured-target seated pose"
        )

    original_seated = r16._apply_seated_pose

    def corrected_seated(
        target_armature: Any,
        _knee_report: Mapping[str, Any],
        target_height_m: float,
    ) -> dict[str, Any]:
        seat = bpy.data.objects.get("Kira_Private_Seat_Contact_Diagnostic")
        if seat is None:
            raise KiraR17BuildError("private seated-contact prop missing")
        return apply_pose_foundation_v1(
            armature=target_armature,
            body=body,
            pose_name="seated",
            body_height_m=target_height_m,
            seat_top_z_m=_seat_top_z(seat),
        )

    r16._apply_seated_pose = corrected_seated
    try:
        report = r16._render_owner_review_views(
            scene=scene,
            output_dir=output_dir,
            body=body,
            armature=armature,
            candidate_objects=candidate_objects,
            knee_report=review_knees,
            protected_target=protected_target,
            target_height_m=TARGET_HEIGHT_M,
        )
    finally:
        r16._apply_seated_pose = original_seated
    seated = list(report.get("seated_pose_reports") or [])
    if len(seated) != 2 or not all(
        row.get("bilateral_leg_clearance", {}).get("passed") is True
        and row.get("support_contact", {}).get("contact_residual_within_2mm") is True
        for row in seated
    ):
        raise KiraR17BuildError("measured seated contact/clearance evidence failed")
    report["seated_contact_claimed"] = True
    report["seated_contact_claim_scope"] = (
        "measured buttock support residual within 2 mm plus conservative bilateral "
        "leg-capsule clearance; owner visual mesh-contact review still required"
    )
    report["isolated_knee_review_angle_degrees"] = 30.0
    report["deep_bend_shown_by_corrected_seated_pose"] = True
    return report, engineering_knees


def _evaluated_bounds(body: Any) -> tuple[Vector, Vector]:
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    points = [evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box]
    return (
        Vector(tuple(min(float(point[axis]) for point in points) for axis in range(3))),
        Vector(tuple(max(float(point[axis]) for point in points) for axis in range(3))),
    )


def _render_supplemental(
    *, scene: Any, camera: Any, path: Path, target: Vector, direction: Vector, scale: float
) -> dict[str, Any]:
    camera.location = target + direction.normalized() * TARGET_HEIGHT_M * 3.0
    r16.r15._look_at(camera, target)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = float(scale)
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {"path": path.name, "sha256": r16.r15.sha256_file(path)}


def _add_private_support_slab() -> Any:
    material = bpy.data.materials.new("Kira_Private_Lying_Support_Material")
    material.diffuse_color = (0.025, 0.045, 0.070, 1.0)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = material.diffuse_color
        principled.inputs["Roughness"].default_value = 0.62
    bpy.ops.mesh.primitive_cube_add(
        location=(0.0, 0.0, -0.018), scale=(0.48, 1.05, 0.018)
    )
    slab = bpy.context.object
    slab.name = "Kira_Private_Lying_Contact_Diagnostic"
    slab.data.materials.append(material)
    slab["private_review_prop_only"] = True
    slab["runtime_activation_allowed"] = False
    slab["publication_allowed"] = False
    return slab


def _supplemental_activity_review(
    *, scene: Any, output_dir: Path, body: Any, armature: Any, seat_name: str
) -> dict[str, Any]:
    camera = scene.camera or next(obj for obj in bpy.data.objects if obj.type == "CAMERA")
    seat = bpy.data.objects.get(seat_name)
    if seat is None:
        raise KiraR17BuildError("core review seat missing before activity review")
    support = _add_private_support_slab()
    seat.hide_render = True
    support.hide_render = False
    lying = apply_pose_foundation_v1(
        armature=armature,
        body=body,
        pose_name="lying_supine",
        body_height_m=TARGET_HEIGHT_M,
        support_plane_z_m=0.0,
    )
    low, high = _evaluated_bounds(body)
    target = (low + high) * 0.5
    lying_views = []
    for label, direction in (
        ("lying_supine_side_contact", Vector((1.0, 0.0, 0.18))),
        ("lying_supine_top_contact", Vector((0.0, 0.0, 1.0))),
    ):
        row = _render_supplemental(
            scene=scene,
            camera=camera,
            path=output_dir / f"{label}.png",
            target=target,
            direction=direction,
            scale=max(float(high.x - low.x), float(high.y - low.y)) * 1.18,
        )
        lying_views.append({"label": label, **row})

    reset_pose_v1(armature)
    support.hide_render = True
    seat.hide_render = False
    eating = apply_pose_foundation_v1(
        armature=armature,
        body=body,
        pose_name="eating_ready",
        body_height_m=TARGET_HEIGHT_M,
        seat_top_z_m=_seat_top_z(seat),
    )
    low, high = _evaluated_bounds(body)
    target = (low + high) * 0.5
    eating_row = _render_supplemental(
        scene=scene,
        camera=camera,
        path=output_dir / "eating_ready_seated_contact.png",
        target=target,
        direction=Vector((0.70, -1.0, 0.08)),
        scale=TARGET_HEIGHT_M * 1.02,
    )
    seat.hide_render = True
    support.hide_render = True
    reset_pose_v1(armature)
    return {
        "views": [*lying_views, {"label": "eating_ready_seated_contact", **eating_row}],
        "lying_supine_pose": lying,
        "eating_ready_pose": eating,
        "static_pose_foundation_only": True,
        "animation_or_full_activity_capability_claimed": False,
        "visual_mesh_contact_review_required": True,
        "neutral_pose_restored_after_review": True,
        "private_support_objects": [seat.name, support.name],
    }


def _build(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    if not args.acknowledge_inactive_private_candidate:
        raise KiraR17BuildError("--acknowledge-inactive-private-candidate is required")
    if not args.render_owner_review:
        raise KiraR17BuildError("--render-owner-review is required")
    source_path = (PROJECT_ROOT / args.source_blend).resolve(strict=True)
    if source_path != (PROJECT_ROOT / R16_SOURCE_RELATIVE).resolve():
        raise KiraR17BuildError("only the exact bound R16 source is permitted")
    if r16.r15.sha256_file(source_path) != R16_SOURCE_SHA256:
        raise KiraR17BuildError("R16 source blend hash mismatch")
    evidence_path = PROJECT_ROOT / R16_EVIDENCE_RELATIVE
    if r16.r15.sha256_file(evidence_path) != R16_EVIDENCE_SHA256:
        raise KiraR17BuildError("R16 source evidence hash mismatch")
    output_relative = Path(args.output_dir)
    output_dir = (PROJECT_ROOT / output_relative).resolve()
    allowed_parent = (PROJECT_ROOT / "Avatar/private_owner_review").resolve()
    if output_dir.parent != allowed_parent or not output_dir.name.startswith(
        "kira_profiled_adult_candidate_r17_bald_corrected_"
    ):
        raise KiraR17BuildError("output must be a direct append-only R17 private review child")
    if output_dir.exists():
        raise KiraR17BuildError("output directory already exists")
    live_before = capture_live_kira_state_hashes(PROJECT_ROOT)
    bindings_before = _hash_bindings()

    bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)
    scene = bpy.context.scene
    body = next(
        obj for obj in bpy.data.objects if obj.type == "MESH" and obj.get("primary_surface")
    )
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    old_id = str(scene.get("candidate_id") or body.get("candidate_id") or "")
    if old_id != R16_SOURCE_RELATIVE.parent.name:
        raise KiraR17BuildError("R16 in-blend candidate identity drifted")
    reset_pose_v1(armature)
    removed_props = _remove_private_pose_props()
    eye_objects, old_facial = _candidate_inventory(body, armature)

    face_report = integrated._apply_face_delta(body, TARGET_HEIGHT_M)
    surface_report = integrated._apply_organic_surface(body, TARGET_HEIGHT_M)
    for obj in old_facial:
        obj["superseded_from_candidate_id"] = str(obj.get("candidate_id") or "")
        obj["candidate_id"] = output_dir.name
    facial_objects, appearance_report = apply_kira_appearance_delivery_v3(
        body=body,
        armature=armature,
        eye_objects=eye_objects,
        candidate_id=output_dir.name,
        project_root=PROJECT_ROOT,
        superseded_facial_objects=old_facial,
    )
    removed_nails = integrated._remove_old_nails()
    nail_objects, nail_report = add_natural_nails_v3(
        body=body,
        armature=armature,
        target_height_m=TARGET_HEIGHT_M,
        candidate_id=output_dir.name,
    )
    reused_objects = [body, armature, *eye_objects]
    reuse_records = _retag_reused_objects(
        reused_objects, old_id=old_id, candidate_id=output_dir.name
    )
    candidate_objects = [*reused_objects, *facial_objects, *nail_objects]
    r16.r15._mark_inactive_private(candidate_objects, scene, output_dir.name)
    scene["candidate_author_id"] = "kira_r17_targeted_correction_from_exact_r16"
    scene["candidate_asset_id"] = "KIRA_BALD_LOW_RESOURCE_BODY"
    scene["complete_natural_bald_scalp"] = True
    scene["scalp_hair_dependency_allowed"] = False
    body["candidate_asset_id"] = "KIRA_BALD_LOW_RESOURCE_BODY"
    body["complete_natural_bald_scalp"] = True
    body["scalp_hair_dependency_allowed"] = False
    body["adult_relationship_surface_detail_method"] = str(
        surface_report["detail_method_id"]
    )
    body["identity_match_claim_allowed"] = False
    body["owner_visual_review_required"] = True

    policy, policy_report = r16._validate_delivery_policy()
    zero_hair = r16._zero_scalp_hair_inventory(
        body=body, candidate_objects=candidate_objects, policy_report=policy_report
    )
    if zero_hair.get("passed") is not True:
        raise KiraR17BuildError(
            "zero scalp-hair dependency failed: " + "; ".join(zero_hair["blockers"])
        )
    topology = r16.r15._mesh_topology_counts(body)
    if (
        topology["surface_components"] != 1
        or topology["boundary_edges"] != 0
        or topology["nonmanifold_edges"] != 0
    ):
        raise KiraR17BuildError("R17 primary surface is not one closed manifold")
    if capture_live_kira_state_hashes(PROJECT_ROOT) != live_before:
        raise KiraR17BuildError("live Kira state changed before output")
    if _hash_bindings() != bindings_before:
        raise KiraR17BuildError("implementation binding changed during build")

    output_dir.mkdir(parents=False, exist_ok=False)
    protected_target = Vector(tuple(surface_report["front_frame"]["origin"]))
    core_review, knee_report = _core_owner_review(
        scene=scene,
        output_dir=output_dir,
        body=body,
        armature=armature,
        candidate_objects=candidate_objects,
        protected_target=protected_target,
    )
    activity_review = _supplemental_activity_review(
        scene=scene,
        output_dir=output_dir,
        body=body,
        armature=armature,
        seat_name=str(core_review["private_seat_review_prop"]),
    )
    reset_pose_v1(armature)
    blend_path = output_dir / f"{output_dir.name}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    blend_record = {"path": blend_path.name, "sha256": r16.r15.sha256_file(blend_path)}
    live_after = capture_live_kira_state_hashes(PROJECT_ROOT)
    bindings_after = _hash_bindings()
    source_hash_after = r16.r15.sha256_file(source_path)
    if live_after != live_before:
        raise KiraR17BuildError("live Kira state changed before evidence commit")
    if bindings_after != bindings_before or source_hash_after != R16_SOURCE_SHA256:
        raise KiraR17BuildError("source or implementation binding changed at commit")

    evidence = {
        "schema_version": 1,
        "evidence_type": "inactive_complete_kira_bald_targeted_correction_candidate_v2",
        "candidate_id": output_dir.name,
        "candidate_asset_id": "KIRA_BALD_LOW_RESOURCE_BODY",
        "status": "INACTIVE_PRIVATE_COMPLETE_BODY_AWAITING_OWNER_VISUAL_DECISION",
        "owner_visual_status": "UNDECIDED_TARGETED_R17_CORRECTION",
        "source": {
            "candidate_id": old_id,
            "blend_path": R16_SOURCE_RELATIVE.as_posix(),
            "blend_sha256_before_after": [R16_SOURCE_SHA256, source_hash_after],
            "build_evidence_path": R16_EVIDENCE_RELATIVE.as_posix(),
            "build_evidence_sha256": R16_EVIDENCE_SHA256,
            "reuse_policy": "preserve accepted R16 components; replace only rejected components",
        },
        "targeted_corrections": {
            "face_direction_v3": face_report,
            "organic_adult_surface_v4": surface_report,
            "appearance_v3": appearance_report,
            "natural_nails_v3": nail_report,
            "superseded_r16_nails_removed": removed_nails,
            "superseded_r16_private_pose_props_removed": removed_props,
            "reused_component_retagging": reuse_records,
        },
        "complete_body_boundary": {
            "complete_body": True,
            "adult_female_lane": True,
            "bald_low_resource_body": True,
            "natural_primary_skin_scalp": True,
            "eyebrows_and_eyelashes_retained": True,
            "scalp_hair_dependency": False,
            "hair_master_is_separate_inactive_asset": True,
        },
        "rig_and_movement_foundation": {
            "official_r16_rig_reused_unchanged": True,
            "knee_smoothing_v2_reused": True,
            "knee_axis_engineering_report": knee_report,
            "human_pose_clearance_contact_v1": True,
            "static_pose_foundations_present": [
                "neutral", "single_knee_bend", "bilateral_knee_bend", "seated",
                "lying_supine", "eating_ready"
            ],
            "full_animation_capability_claimed": False,
            "future_normal_activity_validation_required": True,
        },
        "owner_review": core_review,
        "supplemental_activity_review": activity_review,
        "zero_scalp_hair_dependency": zero_hair,
        "final_primary_surface_topology": topology,
        "implementation_bindings": bindings_after,
        "outputs": {
            "blend": blend_record,
            "private_glb": {"exported": False, "path": None},
        },
        "known_limits_for_honest_owner_review": [
            "The face is a bounded Kira-directed qualitative correction, not a measured identity match.",
            "Static seated, lying, and eating-ready poses do not prove complete animation or environment interaction.",
            "No relationship, intimate-behavior, pregnancy, reproductive-internal, or family simulation is implemented or claimed by this body candidate.",
            "The detachable realistic hair master remains unfinished, inactive, and excluded from this 32 GB bald body."
        ],
        "future_lifecycle_design_constraints": {
            "relationships_require_consenting_adults": True,
            "friendship_to_intimacy_progression_not_implemented_here": True,
            "pregnancy_and_family_systems_not_implemented_here": True,
            "adult_classification_gate_required_before_adult_anatomy": True,
        },
        "safety": {
            "inactive": True,
            "private_owner_review_only": True,
            "assigned": False,
            "activated": False,
            "clothed": False,
            "published": False,
            "uploaded": False,
            "runtime_activation_allowed": False,
            "live_kira_state_unchanged": live_after == live_before,
            "live_state_before": live_before,
            "live_state_after": live_after,
        },
        "rollback": {
            "required": False,
            "instruction": (
                "Delete or quarantine only this new R17 directory if Robert rejects it. "
                "R16 and all live Kira files remain unchanged; do not alter the runtime selection."
            ),
        },
        "build_elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    evidence_path = output_dir / "BUILD_EVIDENCE.json"
    evidence_path.write_text(
        json.dumps(r16.r15._json_safe(evidence), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "status": evidence["status"],
        "candidate_id": output_dir.name,
        "output_dir": output_relative.as_posix(),
        "blend_sha256": blend_record["sha256"],
        "evidence_sha256": r16.r15.sha256_file(evidence_path),
        "core_review_view_count": int(core_review["view_count"]),
        "supplemental_activity_view_count": len(activity_review["views"]),
        "live_state_unchanged": True,
    }


def main() -> int:
    args = _args()
    try:
        result = _build(args)
    except Exception as exc:
        output = (PROJECT_ROOT / Path(args.output_dir)).resolve()
        allowed_parent = (PROJECT_ROOT / "Avatar/private_owner_review").resolve()
        if output.parent == allowed_parent and output.is_dir():
            failure = {
                "schema_version": 1,
                "status": "R17_BUILD_FAILED_INACTIVE_NO_ACTIVATION",
                "exception_type": type(exc).__name__,
                "message": str(exc),
                "runtime_activation_performed": False,
                "glb_exported": False,
                "rollback": "Preserve this failed append-only directory for diagnosis; live selection was never targeted.",
            }
            (output / "BUILD_FAILURE.json").write_text(
                json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        raise
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
