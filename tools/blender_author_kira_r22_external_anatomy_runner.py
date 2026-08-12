#!/usr/bin/env python3
"""Shared append-only runner for later R22 external-anatomy attempts."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import bpy


def run_attempt(
    base: Any,
    *,
    root: Path,
    attempt_number: int,
    output_dir: Path,
    evidence_dir: Path,
    output_blend: Path,
    prior_attempt_truth: dict[str, Any],
    repair_summary: str,
) -> int:
    label = f"attempt_{attempt_number:02d}"
    if output_dir.exists() or evidence_dir.exists():
        raise FileExistsError(f"append-only R22 external anatomy {label} already exists")
    if Path(bpy.data.filepath).resolve() != base.SOURCE.resolve():
        raise RuntimeError("exact R21 Attempt 08 source is not loaded")
    if base.sha256_file(base.SOURCE) != base.EXPECTED_SOURCE_SHA:
        raise RuntimeError("R21 Attempt 08 source hash drifted")
    output_dir.mkdir(parents=True, exist_ok=False)
    evidence_dir.mkdir(parents=True, exist_ok=False)
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
    nonpatch_after = base.r21.nonpatch_snapshot(body)
    if nonpatch_after != nonpatch_before:
        raise RuntimeError("approved body outside the exact pelvic mask changed")
    objects, module = base.create_module(body, rig)
    protected_after = {obj.name: base.r21.object_digest(obj) for obj in inherited}
    if protected_after != protected_before or base.r21.object_digest(rig) != rig_before:
        raise RuntimeError("an inherited nonbody object or rig changed")
    candidate_id = f"kira_r22_external_anatomy_{label}"
    body.name = f"Kira_R22_Bald_Private_Inactive_ApprovedBody_ExternalAnatomyA{attempt_number:02d}"
    body["candidate_id"] = candidate_id
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
    base.r21.OUTPUT_DIR = output_dir
    renders = base.r21.render_review(body)
    for name, state in old_states.items():
        if bpy.data.objects.get(name) is not None:
            bpy.data.objects[name].hide_render = state
    body["render_evidence_json"] = json.dumps(renders, separators=(",", ":"))
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend), check_existing=False)
    blend_sha = base.sha256_file(output_blend)
    intersection = base.r21.exact_audit(body)
    evidence = {
        "schema_version": 1,
        "artifact_kind": f"KIRA_R22_EXTERNAL_ANATOMY_ATTEMPT{attempt_number:02d}_BUILD_EVIDENCE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PRIVATE_INACTIVE_CLINICAL_EXTERNAL_ANATOMY_REVIEW_CANDIDATE",
        "candidate_id": candidate_id,
        "source": {
            "blend": str(base.SOURCE.relative_to(root)).replace("\\", "/"),
            "sha256": base.EXPECTED_SOURCE_SHA,
        },
        "prior_attempt_truth": prior_attempt_truth,
        "bounded_repair": repair_summary,
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
            "nonpatch_body_exactly_preserved": nonpatch_after == nonpatch_before,
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
            "blend": str(output_blend.relative_to(root)).replace("\\", "/"),
            "blend_sha256": blend_sha,
            "renders": renders,
        },
        "private": True,
        "inactive": True,
        "unassigned": True,
        "unpublished": True,
        "activation_or_export_performed": False,
    }
    (evidence_dir / "BUILD_EVIDENCE.json").write_text(
        json.dumps(evidence, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "OWNER_REVIEW_README.md").write_text(
        f"# Kira R22 external anatomy Attempt {attempt_number:02d}\n\n"
        "Private, inactive, clinical review only. The owner-approved face and general body "
        "outside the exact pelvic mask are preserved. The external module is detachable and "
        "rig-bound. It is not proof of urinary, bowel, reproductive, pregnancy, or childbirth "
        "physiology. Eyebrows and nails remain separate correction stages.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": evidence["status"],
        "candidate_id": candidate_id,
        "blend": str(output_blend),
        "blend_sha256": blend_sha,
        "renders": renders,
        "module_component_count": len(objects),
        "body_exact_pairs": intersection["exact_genuine_penetration_pair_count"],
    }, indent=2))
    return 0
