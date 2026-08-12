#!/usr/bin/env python3
"""Append-only Attempt 02 for the R22 external-anatomy module.

Attempt 01 failed before save because its ray bound was specified in world
meters while ``Object.ray_cast`` receives body-local coordinates.  This worker
changes only that query distance and attempt-specific output/evidence labels.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


ROOT = Path(r"C:\Users\robmc\Kira")
TOOLS = ROOT / "Tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import blender_author_kira_r22_external_anatomy_attempt01 as base  # noqa: E402


OUTPUT_DIR = ROOT / "Avatar/private_owner_review/kira_r22_external_anatomy_attempt_02"
EVIDENCE_DIR = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r22_external_anatomy/attempt_02"
)
OUTPUT_BLEND = OUTPUT_DIR / "KIRA_R22_BALD_PRIVATE_INACTIVE_EXTERNAL_ANATOMY_ATTEMPT02.blend"


def ray_surface_y_fixed(
    body: bpy.types.Object,
    x: float,
    z: float,
    *,
    front: bool = True,
) -> float:
    inverse = body.matrix_world.inverted()
    origin_world = Vector((x, -0.35 if front else 0.35, z))
    direction_world = Vector((0.0, 1.0 if front else -1.0, 0.0))
    origin_local = inverse @ origin_world
    direction_local = (inverse.to_3x3() @ direction_world).normalized()
    hit, location, _normal, _face = body.ray_cast(
        origin_local,
        direction_local,
        distance=100.0,
    )
    if not hit:
        raise RuntimeError(
            f"body ray missed after local-scale correction at x={x:.6f}, "
            f"z={z:.6f}, front={front}"
        )
    return float((body.matrix_world @ location).y)


base.ray_surface_y = ray_surface_y_fixed
base.OUTPUT_DIR = OUTPUT_DIR
base.EVIDENCE_DIR = EVIDENCE_DIR
base.OUTPUT_BLEND = OUTPUT_BLEND


def main() -> int:
    if OUTPUT_DIR.exists() or EVIDENCE_DIR.exists():
        raise FileExistsError("append-only R22 external anatomy Attempt 02 already exists")
    if Path(bpy.data.filepath).resolve() != base.SOURCE.resolve():
        raise RuntimeError("exact R21 Attempt 08 source is not loaded")
    if base.sha256_file(base.SOURCE) != base.EXPECTED_SOURCE_SHA:
        raise RuntimeError("R21 Attempt 08 source hash drifted")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=False)
    body = base.find_body()
    rig = bpy.data.objects.get(base.RIG_NAME)
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError("exact inherited rig is absent")
    base.r21.clear_pose(rig)
    nonpatch_before = base.r21.nonpatch_snapshot(body)
    inherited = [obj for obj in bpy.data.objects if obj != body]
    protected_before = {obj.name: base.r21.object_digest(obj) for obj in inherited}
    rig_before = base.r21.object_digest(rig)
    topology = base.patch_topology(body)
    relaxation = base.relax_rejected_center(body, topology)
    if relaxation["seam_maximum_delta"] != 0.0:
        raise RuntimeError("localized relaxation moved the preserved interface")
    nonpatch_after_relaxation = base.r21.nonpatch_snapshot(body)
    if nonpatch_after_relaxation != nonpatch_before:
        raise RuntimeError("approved body outside the exact pelvic mask changed")
    objects, module = base.create_module(body, rig)
    protected_after = {obj.name: base.r21.object_digest(obj) for obj in inherited}
    if protected_after != protected_before or base.r21.object_digest(rig) != rig_before:
        raise RuntimeError("an inherited nonbody object or rig changed")
    body.name = "Kira_R22_Bald_Private_Inactive_ApprovedBody_ExternalAnatomyA02"
    body["candidate_id"] = "kira_r22_external_anatomy_attempt_02"
    body["private_review_only"] = True
    body["owner_approved"] = False
    body["runtime_assignment_allowed"] = False
    body["runtime_activation_allowed"] = False
    body["approved_face_preserved"] = True
    body["approved_general_body_preserved"] = True
    body["external_anatomy_owner_acceptance"] = False
    body["internal_physiology_implemented"] = False
    body["anatomy_module_objects_json"] = json.dumps(module["objects"], separators=(",", ":"))

    old_states = {
        obj.name: bool(obj.hide_render)
        for obj in bpy.data.objects
        if obj.type in {"LIGHT", "CAMERA"}
    }
    base.r21.OUTPUT_DIR = OUTPUT_DIR
    renders = base.r21.render_review(body)
    for name, state in old_states.items():
        if bpy.data.objects.get(name) is not None:
            bpy.data.objects[name].hide_render = state
    body["render_evidence_json"] = json.dumps(renders, separators=(",", ":"))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND), check_existing=False)
    blend_sha = base.sha256_file(OUTPUT_BLEND)
    intersection = base.r21.exact_audit(body)
    evidence = {
        "schema_version": 1,
        "artifact_kind": "KIRA_R22_EXTERNAL_ANATOMY_ATTEMPT02_BUILD_EVIDENCE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PRIVATE_INACTIVE_CLINICAL_EXTERNAL_ANATOMY_REVIEW_CANDIDATE",
        "source": {
            "blend": str(base.SOURCE.relative_to(ROOT)).replace("\\", "/"),
            "sha256": base.EXPECTED_SOURCE_SHA,
        },
        "attempt_01_preserved": {
            "failure_evidence": "RecoverySprint/continuation_20260802/kira_r22_external_anatomy/attempt_01/FAILURE_EVIDENCE.json",
            "repair": "body-local ray query distance 0.7 -> 100.0 only",
        },
        "owner_visual_decision_applied": {
            "approved_face_preserved": True,
            "approved_general_body_preserved": True,
            "rejected_pelvic_region_targeted": True,
            "eyebrows_pending_separate_worker": True,
            "nails_pending_separate_worker": True,
        },
        "localized_base_relaxation": relaxation,
        "external_anatomy_module": module,
        "preservation": {
            "nonpatch_body_exactly_preserved": nonpatch_after_relaxation == nonpatch_before,
            "inherited_nonbody_objects_exactly_preserved": protected_after == protected_before,
            "rig_exactly_preserved": base.r21.object_digest(rig) == rig_before,
        },
        "body_exact_intersection_audit": intersection,
        "medical_boundary": {
            "external_surface_only": True,
            "continuous_visible_order_implemented": module["component_order_anterior_to_posterior"],
            "normal_human_variation_retained": True,
            "sources": [
                "https://www.acog.org/womens-health/faqs/vulvovaginal-health",
                "https://www.ncbi.nlm.nih.gov/books/NBK547703/",
                "https://www.ncbi.nlm.nih.gov/books/NBK537132/",
            ],
        },
        "functional_truth": {
            "external_appearance_and_rig_binding_candidate": True,
            "bladder_urethra_bowel_rectum_reproductive_organs_implemented": False,
            "urination_defecation_reproduction_pregnancy_proven": False,
            "movement_and_contact_validation_pending": True,
            "separate_internal_simulation_and_state_system_required": True,
        },
        "outputs": {
            "blend": str(OUTPUT_BLEND.relative_to(ROOT)).replace("\\", "/"),
            "blend_sha256": blend_sha,
            "renders": renders,
        },
        "private": True,
        "inactive": True,
        "unassigned": True,
        "unpublished": True,
        "activation_or_export_performed": False,
    }
    evidence_path = EVIDENCE_DIR / "BUILD_EVIDENCE.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "OWNER_REVIEW_README.md").write_text(
        "# Kira R22 external anatomy Attempt 02\n\n"
        "Private, inactive, clinical review only. The owner-approved face and general body "
        "outside the exact pelvic mask are preserved. The external module is detachable and "
        "rig-bound. It is not proof of urinary, bowel, reproductive, pregnancy, or childbirth "
        "physiology. Eyebrows and nails remain separate correction stages.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": evidence["status"],
        "blend": str(OUTPUT_BLEND),
        "blend_sha256": blend_sha,
        "renders": renders,
        "module_component_count": len(objects),
        "body_exact_pairs": intersection["exact_genuine_penetration_pair_count"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
