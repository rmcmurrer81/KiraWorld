"""Commit the exact best-safe R17 staging as a private owner-review candidate.

The large v4 surface plate remains visibly unresolved.  The one final bounded
v5 repair looked worse and is frozen as rejected, so this script does not
author or regenerate any body component.  It opens the exact v4 staging
checkpoint, installs only the separately validated rear-scalp custom-normal
repair, retags the already-built components, renders the complete review set,
and saves a new append-only, bald, inactive candidate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any, Sequence

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tools.blender_build_kira_r17_corrected_bald_candidate as r17
import tools.blender_build_profiled_kira_bald_delivery_candidate as r16
from Core.avatar_profiled_adult_candidate_contract import (
    capture_live_kira_state_hashes,
)
from tools.blender_avatar_human_pose_clearance_v1 import reset_pose_v1
from tools.blender_avatar_shading_normal_repair_v2 import (
    install_rear_scalp_custom_normal_repair_v2,
)


class KiraR17BestSafeCommitError(RuntimeError):
    """Raised before the frozen staging may be represented as a candidate."""


R16_ID = "kira_profiled_adult_candidate_r16_bald_delivery_20260801_134650"
PROBE_ID = "kira_r17_integrated_visual_probe_attempt_05"
STAGING_RELATIVE = Path(
    "RecoverySprint/continuation_20260801/kira_r17_integrated_visual_probe/"
    "attempt_05/r17_corrected_components_private_staging.blend"
)
STAGING_SHA256 = "6ecb8703d2a670e0cfec253c061a578f052667cb0db2519690fd1a2f190533f6"
PROBE_EVIDENCE_RELATIVE = STAGING_RELATIVE.parent / "PROBE_EVIDENCE.json"
PROBE_EVIDENCE_SHA256 = "bdfe2e560a986963e9d4921677e90a915072854e74435c39011cf626e2d129e7"
PROBE_VISUAL_RELATIVE = STAGING_RELATIVE.parent / "VISUAL_REVIEW_RESULT.json"
PROBE_VISUAL_SHA256 = "e2f4562b56a5a79284df0efb6f463d1c56d96d44ff52a792462ed8792b5f7929"
SCALP_EVIDENCE_RELATIVE = Path(
    "RecoverySprint/continuation_20260801/kira_r17_shading_normal_repair_v2_probe/"
    "attempt_02/SHADING_NORMAL_REPAIR_V2_EVIDENCE.json"
)
SCALP_EVIDENCE_SHA256 = "e83ef718d0ef7510fcd63320c4123044f3de0d821dc2f2bd747664c9c16474fb"
SCALP_VISUAL_RELATIVE = SCALP_EVIDENCE_RELATIVE.parent / "VISUAL_REVIEW_PARTIAL_NOT_COMPLETE.json"
SCALP_VISUAL_SHA256 = "2a417307328219cf7e7c012c015a3752b80414e9a0641357a2160d0da49aa752"
V5_FAILURE_RELATIVE = Path(
    "RecoverySprint/continuation_20260801/kira_r17_surface_v5_final_visual_probe/"
    "attempt_02/FAILURE.json"
)
V5_FAILURE_SHA256 = "d6d0c66844f46d7bc7bbf702f74aad05ea176ba9e42dec22b9cfd817c0cb24db"
V5_EVIDENCE_RELATIVE = Path(
    "RecoverySprint/continuation_20260801/kira_r17_surface_v5_final_visual_probe/"
    "attempt_02_retry_after_pre_render_solver_tolerance/PROBE_EVIDENCE.json"
)
V5_EVIDENCE_SHA256 = "535881bfd26687bb53e74b24e6b35dc3ccfa46fd8f290c6316482363d93be3b8"
V5_VISUAL_RELATIVE = V5_EVIDENCE_RELATIVE.parent / "VISUAL_REVIEW_RESULT.json"
V5_VISUAL_SHA256 = "d836e5936dba04f59973a847f92dcdc6ecd918779145fcee518cd01034d76848"
TARGET_HEIGHT_M = 1.651

IMPLEMENTATION_PATHS = (
    Path("tools/blender_commit_kira_r17_best_safe_bald_candidate.py"),
    Path("tools/blender_build_kira_r17_corrected_bald_candidate.py"),
    Path("tools/blender_build_profiled_kira_bald_delivery_candidate.py"),
    Path("Core/avatar_kira_face_delivery_v3.py"),
    Path("Core/avatar_adult_female_surface_delivery_v4.py"),
    Path("Core/avatar_kira_appearance_delivery_v3.py"),
    Path("Core/avatar_natural_nail_delivery_v3.py"),
    Path("Core/avatar_human_pose_clearance_v1.py"),
    Path("Core/avatar_shading_normal_repair_v2.py"),
    Path("tools/blender_avatar_shading_normal_repair_v2.py"),
    Path("Avatar/avatar_builder/tooling/avatar_shading_normal_repair_v2.json"),
)

BOUND_EVIDENCE = (
    (PROBE_EVIDENCE_RELATIVE, PROBE_EVIDENCE_SHA256),
    (PROBE_VISUAL_RELATIVE, PROBE_VISUAL_SHA256),
    (SCALP_EVIDENCE_RELATIVE, SCALP_EVIDENCE_SHA256),
    (SCALP_VISUAL_RELATIVE, SCALP_VISUAL_SHA256),
    (V5_FAILURE_RELATIVE, V5_FAILURE_SHA256),
    (V5_EVIDENCE_RELATIVE, V5_EVIDENCE_SHA256),
    (V5_VISUAL_RELATIVE, V5_VISUAL_SHA256),
)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--acknowledge-inactive-private-candidate", action="store_true")
    parser.add_argument("--render-owner-review", action="store_true")
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def _sha(path: Path) -> str:
    return r16.r15.sha256_file(path)


def _load_bound_json(relative: Path, expected_sha256: str) -> dict[str, Any]:
    path = (PROJECT_ROOT / relative).resolve(strict=True)
    actual = _sha(path)
    if actual != expected_sha256:
        raise KiraR17BestSafeCommitError(
            f"bound evidence hash drifted: {relative.as_posix()} {actual}"
        )
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _implementation_hashes() -> dict[str, str]:
    records: dict[str, str] = {}
    for relative in IMPLEMENTATION_PATHS:
        path = (PROJECT_ROOT / relative).resolve(strict=True)
        records[relative.as_posix()] = _sha(path)
    return records


def _retag_candidate_objects(
    objects: Sequence[Any], *, candidate_id: str
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for obj in objects:
        prior_id = str(obj.get("candidate_id") or "")
        old_name = obj.name
        for prefix in (R16_ID, PROBE_ID):
            if old_name.startswith(prefix):
                obj.name = candidate_id + old_name[len(prefix) :]
                break
        obj["superseded_from_candidate_id"] = prior_id
        obj["candidate_id"] = candidate_id
        obj["inactive_candidate"] = True
        obj["private_owner_review_only"] = True
        obj["runtime_activation_allowed"] = False
        obj["publication_allowed"] = False
        obj["reused_from_exact_r17_v4_staging"] = True
        records.append(
            {
                "old_name": old_name,
                "new_name": obj.name,
                "prior_candidate_id": prior_id,
            }
        )
    return records


def _inventory() -> tuple[Any, Any, list[Any], list[Any], list[Any], list[Any]]:
    body = next(
        (obj for obj in bpy.data.objects if obj.type == "MESH" and obj.get("primary_surface")),
        None,
    )
    armature = next((obj for obj in bpy.data.objects if obj.type == "ARMATURE"), None)
    tagged = [
        obj for obj in bpy.data.objects if str(obj.get("candidate_id") or "") in {R16_ID, PROBE_ID}
    ]
    eyes = [
        obj
        for obj in tagged
        if any(token in obj.name.casefold() for token in ("sclera", "iris", "cornea"))
    ]
    facial = [obj for obj in tagged if obj.get("facial_presentation_role")]
    nails = [obj for obj in tagged if "natural_v3" in obj.name.casefold()]
    if body is None or armature is None:
        raise KiraR17BestSafeCommitError("staging body or armature missing")
    if len(tagged) != 36 or len(eyes) != 6 or len(facial) != 8 or len(nails) != 20:
        raise KiraR17BestSafeCommitError(
            f"staging inventory drifted: tagged={len(tagged)} eyes={len(eyes)} "
            f"facial={len(facial)} nails={len(nails)}"
        )
    return body, armature, tagged, eyes, facial, nails


def _bound_records() -> list[dict[str, str]]:
    return [
        {"path": relative.as_posix(), "sha256": expected}
        for relative, expected in BOUND_EVIDENCE
    ]


def _build(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    if not args.acknowledge_inactive_private_candidate:
        raise KiraR17BestSafeCommitError(
            "--acknowledge-inactive-private-candidate is required"
        )
    if not args.render_owner_review:
        raise KiraR17BestSafeCommitError("--render-owner-review is required")

    output_relative = Path(args.output_dir)
    output_dir = (PROJECT_ROOT / output_relative).resolve()
    allowed_parent = (PROJECT_ROOT / "Avatar/private_owner_review").resolve()
    if output_dir.parent != allowed_parent or not output_dir.name.startswith(
        "kira_profiled_adult_candidate_r17_bald_corrected_"
    ):
        raise KiraR17BestSafeCommitError(
            "output must be a direct append-only R17 private owner-review child"
        )
    if output_dir.exists():
        raise KiraR17BestSafeCommitError("append-only output directory already exists")

    staging_path = (PROJECT_ROOT / STAGING_RELATIVE).resolve(strict=True)
    if _sha(staging_path) != STAGING_SHA256:
        raise KiraR17BestSafeCommitError("exact v4 staging hash drifted")
    probe = _load_bound_json(PROBE_EVIDENCE_RELATIVE, PROBE_EVIDENCE_SHA256)
    probe_visual = _load_bound_json(PROBE_VISUAL_RELATIVE, PROBE_VISUAL_SHA256)
    scalp_visual = _load_bound_json(SCALP_VISUAL_RELATIVE, SCALP_VISUAL_SHA256)
    v5_visual = _load_bound_json(V5_VISUAL_RELATIVE, V5_VISUAL_SHA256)
    for relative, expected in BOUND_EVIDENCE:
        _load_bound_json(relative, expected)
    if probe_visual.get("overall_status") != "ENGINEERING_PASS_WITH_TARGETED_VISUAL_REJECTION":
        raise KiraR17BestSafeCommitError("attempt-05 visual decision drifted")
    if v5_visual.get("status") != "FINAL_BOUNDED_V5_VISUAL_REJECTED_NO_FURTHER_SURFACE_ATTEMPT_ALLOWED":
        raise KiraR17BestSafeCommitError("final v5 rejection boundary drifted")

    live_before = capture_live_kira_state_hashes(PROJECT_ROOT)
    implementation_before = _implementation_hashes()
    bpy.ops.wm.open_mainfile(filepath=str(staging_path), load_ui=False)
    scene = bpy.context.scene
    if str(scene.get("candidate_id") or "") != R16_ID:
        raise KiraR17BestSafeCommitError("staging scene identity drifted")
    body, armature, candidate_objects, eyes, facial, nails = _inventory()
    reset_pose_v1(armature)
    removed_props = r17._remove_private_pose_props()

    scalp_report = install_rear_scalp_custom_normal_repair_v2(
        body=body,
        armature=armature,
        project_root=PROJECT_ROOT,
    )
    retagging = _retag_candidate_objects(candidate_objects, candidate_id=output_dir.name)
    r16.r15._mark_inactive_private(candidate_objects, scene, output_dir.name)
    scene["candidate_author_id"] = "kira_r17_best_safe_commit_from_exact_v4_staging"
    scene["candidate_asset_id"] = "KIRA_BALD_LOW_RESOURCE_BODY"
    scene["candidate_status"] = "INACTIVE_PRIVATE_AWAITING_OWNER_VISUAL_DECISION"
    scene["complete_natural_bald_scalp"] = True
    scene["scalp_hair_dependency_allowed"] = False
    scene["surface_v5_visual_rejected"] = True
    scene["owner_visual_approval_granted"] = False
    body["candidate_asset_id"] = "KIRA_BALD_LOW_RESOURCE_BODY"
    body["complete_natural_bald_scalp"] = True
    body["scalp_hair_dependency_allowed"] = False
    body["identity_match_claim_allowed"] = False
    body["owner_visual_review_required"] = True
    body["known_unresolved_surface_v4_plate_defect"] = True

    policy, policy_report = r16._validate_delivery_policy()
    zero_hair = r16._zero_scalp_hair_inventory(
        body=body,
        candidate_objects=candidate_objects,
        policy_report=policy_report,
    )
    if zero_hair.get("passed") is not True:
        raise KiraR17BestSafeCommitError(
            "zero scalp-hair dependency failed: " + "; ".join(zero_hair["blockers"])
        )
    topology = r16.r15._mesh_topology_counts(body)
    if (
        topology["surface_components"] != 1
        or topology["boundary_edges"] != 0
        or topology["nonmanifold_edges"] != 0
    ):
        raise KiraR17BestSafeCommitError("primary surface is not one closed manifold")
    if capture_live_kira_state_hashes(PROJECT_ROOT) != live_before:
        raise KiraR17BestSafeCommitError("live Kira state changed before render")
    if _implementation_hashes() != implementation_before or _sha(staging_path) != STAGING_SHA256:
        raise KiraR17BestSafeCommitError("source or implementation binding changed before render")

    output_dir.mkdir(parents=False, exist_ok=False)
    protected_target = Vector(tuple(probe["organic_surface"]["front_frame"]["origin"]))
    core_review, knee_report = r17._core_owner_review(
        scene=scene,
        output_dir=output_dir,
        body=body,
        armature=armature,
        candidate_objects=candidate_objects,
        protected_target=protected_target,
    )
    activity_review = r17._supplemental_activity_review(
        scene=scene,
        output_dir=output_dir,
        body=body,
        armature=armature,
        seat_name=str(core_review["private_seat_review_prop"]),
    )
    reset_pose_v1(armature)
    blend_path = output_dir / f"{output_dir.name}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    blend_record = {"path": blend_path.name, "sha256": _sha(blend_path)}

    live_after = capture_live_kira_state_hashes(PROJECT_ROOT)
    implementation_after = _implementation_hashes()
    if live_after != live_before:
        raise KiraR17BestSafeCommitError("live Kira state changed before evidence commit")
    if implementation_after != implementation_before or _sha(staging_path) != STAGING_SHA256:
        raise KiraR17BestSafeCommitError("source or implementation binding changed at commit")

    evidence = {
        "schema_version": 1,
        "evidence_type": "inactive_complete_kira_r17_best_safe_bald_owner_review_candidate",
        "candidate_id": output_dir.name,
        "candidate_asset_id": "KIRA_BALD_LOW_RESOURCE_BODY",
        "status": "INACTIVE_PRIVATE_COMPLETE_BODY_AWAITING_OWNER_VISUAL_DECISION",
        "owner_visual_status": "UNDECIDED_BEST_SAFE_R17_WITH_DISCLOSED_DEFECTS",
        "source": {
            "exact_v4_staging_path": STAGING_RELATIVE.as_posix(),
            "exact_v4_staging_sha256_before_after": [STAGING_SHA256, _sha(staging_path)],
            "rejected_r16_source_path": r17.R16_SOURCE_RELATIVE.as_posix(),
            "rejected_r16_source_sha256": r17.R16_SOURCE_SHA256,
            "attempt_05_probe_evidence": {
                "path": PROBE_EVIDENCE_RELATIVE.as_posix(),
                "sha256": PROBE_EVIDENCE_SHA256,
            },
            "reuse_policy": "commit the best safe complete staging; regenerate no accepted component",
        },
        "component_inventory": {
            "primary_body": body.name,
            "armature": armature.name,
            "eyes": [obj.name for obj in eyes],
            "facial_presentation_objects": [obj.name for obj in facial],
            "natural_nails": [obj.name for obj in nails],
            "candidate_object_count": len(candidate_objects),
            "retagging": retagging,
            "removed_staging_private_pose_props": removed_props,
        },
        "accepted_attempt_05_components": {
            "face_direction_v3": probe["face"],
            "adult_surface_v4": probe["organic_surface"],
            "appearance_v3": probe["appearance"],
            "natural_nails_v3": probe["natural_nails"],
            "measured_seated_pose_v1": probe["poses"]["seated_pose_report"],
        },
        "bounded_surface_decision": {
            "v4_visual_result": probe_visual,
            "v5_final_visual_result": v5_visual,
            "v5_promoted": False,
            "v6_allowed": False,
            "best_safe_baseline": "v4 attempt_05",
            "unresolved_defect": (
                "The protected front surface still has a large protruding "
                "trapezoidal/rectangular plate and dark lower wedge."
            ),
        },
        "rear_scalp_custom_normal_v2": {
            "repair": scalp_report,
            "prior_probe_visual_decision": scalp_visual,
            "status": "PARTIAL_IMPROVEMENT_NOT_A_COMPLETE_BAND_REMOVAL",
        },
        "complete_body_boundary": {
            "structurally_complete_body": True,
            "adult_female_lane": True,
            "bald_low_resource_body": True,
            "natural_primary_skin_scalp": True,
            "eyebrows_and_eyelashes_retained": True,
            "scalp_hair_dependency": False,
            "hair_master_is_separate_inactive_asset": True,
        },
        "rig_and_movement_foundation": {
            "official_r16_rig_reused": True,
            "knee_smoothing_v2_reused": True,
            "knee_axis_engineering_report": knee_report,
            "human_pose_clearance_contact_v1": True,
            "static_pose_foundations_present": [
                "neutral",
                "single_knee_bend",
                "bilateral_knee_bend",
                "seated",
                "lying_supine",
                "eating_ready",
            ],
            "isolated_knee_review_angle_degrees": 30.0,
            "full_animation_capability_claimed": False,
            "future_normal_activity_validation_required": True,
        },
        "owner_review": core_review,
        "supplemental_activity_review": activity_review,
        "zero_scalp_hair_dependency": zero_hair,
        "final_primary_surface_topology": topology,
        "bound_external_evidence": _bound_records(),
        "implementation_bindings": implementation_after,
        "outputs": {
            "blend": blend_record,
            "private_glb": {"exported": False, "path": None},
        },
        "known_limits_for_honest_owner_review": [
            "The protected adult front surface retains a conspicuous v4 plate and dark lower wedge.",
            "The face is the best bounded Kira-directed qualitative correction, not a measured identity match.",
            "The rear-scalp custom-normal repair improves the dark band but does not fully remove it.",
            "The nails are improved but remain low-detail presentation components.",
            "The 30-degree isolated knee views and deep seated pose do not prove all movement or animation.",
            "Static seated, lying, and eating-ready poses do not prove full environment interaction.",
            "The detachable realistic hair master remains unfinished, inactive, and excluded from this 32 GB bald body.",
        ],
        "future_lifecycle_design_constraints": {
            "relationships_require_consenting_adults": True,
            "friendship_to_intimacy_progression_not_implemented_here": True,
            "pregnancy_and_family_systems_not_implemented_here": True,
            "adult_classification_gate_required_before_adult_anatomy": True,
            "owner_offline_continuity_correction_is_durable_builder_authority": True,
            "spa_age_progression_requires_separate_age_then_adult_anatomy_stages": True,
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
                "Quarantine or remove only this new R17 directory if Robert rejects it. "
                "The exact v4 staging, R16 source, rejected v5 evidence, and all live "
                "Kira selection/runtime files remain unchanged."
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
        "evidence_sha256": _sha(evidence_path),
        "core_review_view_count": int(core_review["view_count"]),
        "supplemental_activity_view_count": len(activity_review["views"]),
        "live_state_unchanged": True,
        "unresolved_surface_defect_disclosed": True,
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
                "status": "R17_BEST_SAFE_COMMIT_FAILED_INACTIVE_NO_ACTIVATION",
                "exception_type": type(exc).__name__,
                "message": str(exc),
                "runtime_activation_performed": False,
                "glb_exported": False,
                "rollback": "Preserve this append-only failure directory; no live file was targeted.",
            }
            (output / "BUILD_FAILURE.json").write_text(
                json.dumps(failure, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        raise
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
