from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_reconstruction_contract import (  # noqa: E402
    evaluate_avatar_reconstruction_contract,
    maturity_base_contract,
)


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64


def picture(view: str, digest: str, *, subject_id: str = "kira", status: str = "approved") -> dict:
    return {
        "media_type": "image",
        "filename": f"{view}.jpg",
        "subject_id": subject_id,
        "status": status,
        "view": view,
        "sha256": digest,
        "artifact_hash_verified": True,
    }


class AvatarReconstructionContractTests(unittest.TestCase):
    def test_approved_multiview_pictures_can_stage_without_a_model_reference(self) -> None:
        result = evaluate_avatar_reconstruction_contract(
            candidate_id="kira",
            maturity_policy={"maturity_class": "adult"},
            references=[
                picture("head_front", HASH_A),
                picture("three_quarter_left", HASH_B),
                picture("full_body_front", HASH_C),
            ],
            measurements_reviewed=True,
            requested_eye_color="realistic warm brown",
            request_complete_adult_anatomy=True,
            adult_anatomy_reference_reviewed=True,
            base_body_artifact_reviewed=True,
            rig_topology_evidence_reviewed=True,
        )

        self.assertEqual(result["status"], "ready_for_private_staged_reconstruction")
        self.assertTrue(result["staging_allowed"])
        self.assertFalse(result["runtime_activation_allowed"])
        self.assertEqual(
            result["maturity_base_contract"]["base_treatment"],
            "neutral_adult_anatomy",
        )
        self.assertIn(
            "no_optional_model_reference_supplied_picture_only_path_remains_valid",
            result["warnings"],
        )

    def test_model_reference_cannot_replace_picture_identity_evidence(self) -> None:
        result = evaluate_avatar_reconstruction_contract(
            candidate_id="kira",
            maturity_policy={"maturity_class": "adult"},
            references=[
                {
                    "media_type": "3d_model",
                    "filename": "kira_reference.glb",
                    "subject_id": "kira",
                    "status": "approved_for_avatar_identity",
                    "sha256": HASH_D,
                    "artifact_hash_verified": True,
                    "reference_only": True,
                    "copy_as_avatar_body_allowed": False,
                }
            ],
            measurements_reviewed=True,
        )

        self.assertFalse(result["staging_allowed"])
        self.assertIn(
            "no_approved_exact_subject_picture_identity_evidence",
            result["failures"],
        )
        self.assertEqual(
            result["optional_model_evidence"]["optional_measurement_reference_count"],
            1,
        )
        self.assertFalse(
            result["optional_model_evidence"]["can_substitute_for_picture_identity_evidence"]
        )

    def test_unreviewed_or_wrong_subject_pictures_do_not_count(self) -> None:
        result = evaluate_avatar_reconstruction_contract(
            candidate_id="kira",
            maturity_policy={"maturity_class": "adult"},
            references=[
                picture("head_front", HASH_A, status="copied_for_review"),
                picture("three_quarter_left", HASH_B, subject_id="gwen"),
                picture("full_body_front", "not-a-hash"),
            ],
            measurements_reviewed=True,
        )

        self.assertEqual(
            result["picture_evidence"]["approved_exact_subject_hash_bound_count"],
            0,
        )
        self.assertEqual(result["status"], "blocked")

    def test_non_adult_is_forced_to_doll_safe_and_full_adult_request_fails(self) -> None:
        base = maturity_base_contract(
            {"maturity_class": "non_adult_doll_safe"},
            request_complete_adult_anatomy=True,
        )
        self.assertEqual(base["base_treatment"], "non_adult_doll_safe")
        self.assertFalse(base["complete_adult_anatomy_allowed"])

        result = evaluate_avatar_reconstruction_contract(
            candidate_id="normal_non_adult",
            maturity_policy={"maturity_class": "non_adult_doll_safe"},
            references=[
                picture("head_front", HASH_A, subject_id="normal_non_adult"),
                picture("profile", HASH_B, subject_id="normal_non_adult"),
                picture("full_body_front", HASH_C, subject_id="normal_non_adult"),
            ],
            measurements_reviewed=True,
            request_complete_adult_anatomy=True,
        )

        self.assertIn(
            "adult_complete_anatomy_forbidden_for_non_adult_or_uncertain_candidate",
            result["failures"],
        )

    def test_adult_maturity_alone_does_not_prove_complete_anatomy(self) -> None:
        result = evaluate_avatar_reconstruction_contract(
            candidate_id="kira",
            maturity_policy={"maturity_class": "adult"},
            references=[
                picture("head_front", HASH_A),
                picture("profile", HASH_B),
                picture("full_body_front", HASH_C),
            ],
            measurements_reviewed=True,
            request_complete_adult_anatomy=True,
            adult_anatomy_reference_reviewed=False,
        )

        self.assertIn(
            "adult_complete_anatomy_reference_and_topology_plan_not_reviewed",
            result["failures"],
        )
        self.assertFalse(
            result["maturity_base_contract"]["complete_adult_anatomy_allowed"]
        )

    def test_explicit_provisional_identity_waiver_still_requires_proven_body_and_rig(self) -> None:
        blocked = evaluate_avatar_reconstruction_contract(
            candidate_id="kira",
            maturity_policy={"maturity_class": "adult"},
            references=[],
            request_complete_adult_anatomy=True,
            adult_anatomy_reference_reviewed=True,
            base_body_artifact_reviewed=True,
            rig_topology_evidence_reviewed=False,
            allow_provisional_identity_unknown=True,
        )
        self.assertIn(
            "complete_adult_topology_not_proven_on_selected_rig",
            blocked["failures"],
        )
        self.assertNotIn(
            "no_approved_exact_subject_picture_identity_evidence",
            blocked["failures"],
        )

        ready = evaluate_avatar_reconstruction_contract(
            candidate_id="kira",
            maturity_policy={"maturity_class": "adult"},
            references=[],
            request_complete_adult_anatomy=True,
            adult_anatomy_reference_reviewed=True,
            base_body_artifact_reviewed=True,
            rig_topology_evidence_reviewed=True,
            allow_provisional_identity_unknown=True,
        )
        self.assertEqual(
            ready["status"], "ready_for_private_provisional_generic_stage"
        )
        self.assertEqual(
            ready["identity_fidelity"], "unknown_provisional_not_identity_matched"
        )
        self.assertTrue(ready["staging_allowed"])

    def test_clothing_is_always_separate_and_removable(self) -> None:
        result = evaluate_avatar_reconstruction_contract(
            candidate_id="kira",
            maturity_policy={"maturity_class": "adult"},
            references=[],
        )
        self.assertFalse(
            result["wardrobe_contract"]["clothing_baked_into_body_allowed"]
        )
        self.assertTrue(result["wardrobe_contract"]["separate_wearable_mesh_required"])
        self.assertIn(
            "undressing_one_arm_at_a_time",
            result["wardrobe_contract"]["required_lifecycle_states"],
        )
        self.assertIn(
            "stored_hung",
            result["wardrobe_contract"]["required_lifecycle_states"],
        )
        self.assertIn(
            "stored_folded",
            result["wardrobe_contract"]["required_lifecycle_states"],
        )
        self.assertTrue(
            result["wardrobe_contract"]["both_arm_orders_must_be_physically_evidenced"]
        )
        self.assertFalse(
            result["wardrobe_contract"]["timer_or_state_name_only_counts_as_proof"]
        )
        self.assertTrue(
            result["wardrobe_contract"][
                "same_size_sharing_supported_after_target_review"
            ]
        )
        self.assertFalse(
            result["wardrobe_contract"]["size_label_alone_counts_as_fit_proof"]
        )
        self.assertTrue(
            result["wardrobe_contract"][
                "sharing_requires_measurement_envelope_match"
            ]
        )
        self.assertTrue(
            result["wardrobe_contract"][
                "sharing_requires_exact_target_body_rig_binding"
            ]
        )
        self.assertTrue(
            result["wardrobe_contract"][
                "sharing_transfers_one_item_cloning_forbidden"
            ]
        )

    def test_privacy_contract_never_retains_intimate_review_images(self) -> None:
        result = evaluate_avatar_reconstruction_contract(
            candidate_id="kira",
            maturity_policy={"maturity_class": "adult"},
            references=[],
            request_complete_adult_anatomy=True,
        )
        self.assertFalse(result["privacy_contract"]["retain_intimate_review_images"])
        self.assertEqual(
            result["privacy_contract"]["normal_review_presentation"],
            "clothed_only",
        )


if __name__ == "__main__":
    unittest.main()
