from __future__ import annotations

import copy
import unittest

from Core.garment_capability import (
    REQUIRED_ROBE_PHASES,
    REQUIRED_ROBE_STATES,
    REQUIRED_ROBE_TRANSITIONS,
    canonical_sha256,
    evaluate_wearable_capability_manifest,
)


CANDIDATE_ID = "adult_test_candidate"
SUBJECT_ID = "adult_test_subject"
GARMENT_HASH = "a" * 64
BODY_HASH = "b" * 64
RIG_HASH = "c" * 64


def phase_payload(phase_id: str) -> dict:
    side = "left" if "left" in phase_id else "right"
    return {
        "phase_id": phase_id,
        "candidate_id": CANDIDATE_ID,
        "subject_id": SUBJECT_ID,
        "garment_sha256": GARMENT_HASH,
        "body_sha256": BODY_HASH,
        "rig_sha256": RIG_HASH,
        "item_instance_id": "robe_instance_001",
        "same_item_continuity": True,
        "duplicate_active_representations": 0,
        "physical_trace": True,
        "trace_frame_count": 8,
        "named_anchors_verified": True,
        "hook_anchor_id": "bathroom_hook_001",
        "supported_by_named_hook": True,
        "hand_contact_active": False,
        "stable_sample_count": 5,
        "storage_surface_anchor_id": "closet_shelf_001",
        "folded_geometry_observed": True,
        "supported_by_named_surface": True,
        "hand_anchor_id": "hand_right",
        "hand_contact": True,
        "held": True,
        "source_support_removed": True,
        "source_copy_visible_after": False,
        "sleeve_portal_anchor_id": f"{side}_sleeve_portal",
        "arm_side": side,
        "continuous_sleeve_crossing": True,
        "continuous_sleeve_exit": True,
        "teleported": False,
        "path_sample_count": 8,
        "sleeve_membership_physically_observed": True,
        "left_arm_threaded": True,
        "right_arm_threaded": True,
        "both_shoulders_supported": True,
        "garment_follows_verified_rig": True,
        "garment_detached": False,
        "both_belt_endpoints_continuous": True,
        "knot_formed": True,
        "knot_secured": True,
        "two_hand_path_sample_count": 8,
        "knot_released": True,
        "endpoints_separated": True,
        "garment_retained_by_other_arm_or_hand": True,
        "both_arms_out": True,
        "shoulder_attachment_removed": True,
        "hand_contact_before_support": True,
        "target_support_active": True,
        "hand_released_after_support": True,
        "source_hand_empty": True,
    }


def passing_manifest() -> dict:
    evidence = {}
    for phase_id in REQUIRED_ROBE_PHASES:
        payload = phase_payload(phase_id)
        evidence[phase_id] = {
            "status": "passed",
            "capture_basis": "verified_physics_trace",
            "timer_only": False,
            "evidence_payload": payload,
            "evidence_sha256": canonical_sha256(payload),
        }
    return {
        "candidate_id": CANDIDATE_ID,
        "subject_id": SUBJECT_ID,
        "capability_profile": "two_sleeve_tied_robe_v1",
        "garment_sha256": GARMENT_HASH,
        "body_sha256": BODY_HASH,
        "rig_sha256": RIG_HASH,
        "garment_is_separate_artifact": True,
        "skinned_to_exact_rig": True,
        "clothing_baked_into_body": False,
        "capability_only_not_runtime_claim": True,
        "state_inventory": list(REQUIRED_ROBE_STATES),
        "transition_inventory": list(REQUIRED_ROBE_TRANSITIONS),
        "phase_evidence": evidence,
    }


def evaluate(manifest: dict) -> dict:
    return evaluate_wearable_capability_manifest(
        manifest,
        candidate_id=CANDIDATE_ID,
        subject_id=SUBJECT_ID,
        garment_sha256=GARMENT_HASH,
        body_sha256=BODY_HASH,
        rig_sha256=RIG_HASH,
    )


class GarmentCapabilityTests(unittest.TestCase):
    def test_complete_exact_hash_capability_pack_passes_without_runtime_authority(self) -> None:
        result = evaluate(passing_manifest())
        self.assertTrue(result["capability_evidence_complete"], result["failures"])
        self.assertFalse(result["review_stage_allowed"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_hung_and_folded_storage_are_both_required(self) -> None:
        manifest = passing_manifest()
        manifest["state_inventory"].remove("stored_folded")
        del manifest["phase_evidence"]["stored_hung"]
        result = evaluate(manifest)
        self.assertIn("required_state_missing_stored_folded", result["failures"])
        self.assertIn("phase_stored_hung_evidence_missing", result["failures"])

    def test_both_arm_orders_and_reversible_undressing_are_required(self) -> None:
        manifest = passing_manifest()
        manifest["transition_inventory"].remove("dress_left_arm_first")
        manifest["transition_inventory"].remove("undress_right_arm_second")
        result = evaluate(manifest)
        self.assertIn("required_transition_missing_dress_left_arm_first", result["failures"])
        self.assertIn("required_transition_missing_undress_right_arm_second", result["failures"])

    def test_timer_or_state_name_only_evidence_fails_closed(self) -> None:
        manifest = passing_manifest()
        manifest["phase_evidence"]["worn_tied"]["capture_basis"] = "timer_only"
        manifest["phase_evidence"]["worn_tied"]["timer_only"] = True
        result = evaluate(manifest)
        self.assertIn("phase_worn_tied_capture_basis_not_physical", result["failures"])
        self.assertIn("phase_worn_tied_timer_only_forbidden", result["failures"])

    def test_payload_tamper_is_detected_by_recomputed_hash(self) -> None:
        manifest = passing_manifest()
        manifest["phase_evidence"]["release_to_hung"]["evidence_payload"][
            "target_support_active"
        ] = False
        result = evaluate(manifest)
        self.assertIn("phase_release_to_hung_evidence_sha256_mismatch", result["failures"])
        self.assertIn("phase_release_to_hung_target_support_not_active", result["failures"])

    def test_wrong_body_binding_blocks_every_phase_without_mutation(self) -> None:
        manifest = copy.deepcopy(passing_manifest())
        manifest["body_sha256"] = "d" * 64
        result = evaluate(manifest)
        self.assertIn("manifest_body_sha256_mismatch", result["failures"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_every_phase_must_trace_the_same_garment_instance(self) -> None:
        manifest = passing_manifest()
        phase = manifest["phase_evidence"]["release_to_folded"]
        phase["evidence_payload"]["item_instance_id"] = "different_robe_instance"
        phase["evidence_sha256"] = canonical_sha256(phase["evidence_payload"])
        result = evaluate(manifest)
        self.assertIn("phase_item_instance_ids_not_identical", result["failures"])
        self.assertFalse(result["runtime_activation_allowed"])


if __name__ == "__main__":
    unittest.main()
