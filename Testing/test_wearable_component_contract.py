from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Core.wearable_component_contract import (  # noqa: E402
    evaluate_shareable_wearable_component,
    required_lifecycle_capabilities,
)


GARMENT_HASH = "a" * 64
BODY_HASH = "b" * 64
RIG_HASH = "c" * 64
BINDING_HASH = "d" * 64
FIT_HASH = "e" * 64


def passing_manifest() -> dict:
    return {
        "schema_version": 1,
        "component_id": "synthetic_test_robe_medium",
        "component_artifact": {
            "artifact_type": "separate_wearable_component",
            "sha256": GARMENT_HASH,
            "separate_from_body": True,
            "clothing_baked_into_body": False,
            "contains_body_surface_copy": False,
        },
        "maturity_class": "adult",
        "size_profile": {
            "scheme": "body_measurement_envelope_v1",
            "measurement_unit": "metre",
            "size_label": "adult medium test envelope",
            "ease_allowance_reviewed": True,
            "measurement_envelope": {
                "chest_circumference": {"minimum_m": 0.88, "maximum_m": 1.02},
                "waist_circumference": {"minimum_m": 0.70, "maximum_m": 0.88},
                "hip_circumference": {"minimum_m": 0.90, "maximum_m": 1.06},
                "sleeve_length": {"minimum_m": 0.57, "maximum_m": 0.66},
            },
        },
        "share_policy": {
            "same_size_sharing_allowed": True,
            "single_physical_instance": True,
            "clone_on_transfer_allowed": False,
            "owner_consent_required": True,
            "wearer_consent_required": True,
            "transfer_record_required": True,
            "size_label_alone_counts_as_fit_proof": False,
        },
        "lifecycle_contract": {
            "capabilities": list(required_lifecycle_capabilities()),
            "physical_transition_evidence_required": True,
            "timer_or_state_name_only_counts_as_proof": False,
            "put_on_evidence_reviewed": True,
            "take_off_evidence_reviewed": True,
            "transfer_evidence_reviewed": True,
        },
        "target_bindings": [
            {
                "subject_id": "adult_target_b",
                "body_sha256": BODY_HASH,
                "rig_sha256": RIG_HASH,
                "garment_sha256": GARMENT_HASH,
                "binding_sha256": BINDING_HASH,
                "fit_evidence_sha256": FIT_HASH,
                "measurement_fit_reviewed": True,
                "deformation_reviewed": True,
                "penetration_reviewed": True,
                "put_on_take_off_reviewed": True,
                "owner_visual_reviewed": True,
                "runtime_activation_approved": False,
            }
        ],
    }


def passing_target() -> dict:
    return {
        "subject_id": "adult_target_b",
        "maturity_class": "adult",
        "body_sha256": BODY_HASH,
        "rig_sha256": RIG_HASH,
        "measurements_m": {
            "chest_circumference": 0.95,
            "waist_circumference": 0.79,
            "hip_circumference": 0.98,
            "sleeve_length": 0.61,
        },
    }


class WearableComponentContractTests(unittest.TestCase):
    def test_matching_size_and_exact_target_binding_only_enters_private_review(self) -> None:
        result = evaluate_shareable_wearable_component(
            passing_manifest(), passing_target()
        )

        self.assertEqual(result["status"], "compatible_for_private_share_fit_review")
        self.assertTrue(result["contract_compatible_for_private_share_fit_review"])
        self.assertEqual(len(result["matched_measurements"]), 4)
        self.assertFalse(result["runtime_transfer_allowed"])
        self.assertFalse(result["runtime_activation_allowed"])
        self.assertFalse(result["public_export_allowed"])
        self.assertFalse(result["positive_proof_autobuild_released"])

    def test_size_label_without_measurements_never_proves_fit(self) -> None:
        target = passing_target()
        target.pop("measurements_m")
        result = evaluate_shareable_wearable_component(passing_manifest(), target)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("target_measurements_missing", result["failures"])

    def test_out_of_envelope_measurement_blocks_same_label(self) -> None:
        target = passing_target()
        target["measurements_m"]["hip_circumference"] = 1.20
        result = evaluate_shareable_wearable_component(passing_manifest(), target)

        self.assertIn(
            "target_outside_measurement_envelope:hip_circumference",
            result["failures"],
        )

    def test_exact_target_body_and_rig_binding_is_required(self) -> None:
        target = passing_target()
        target["rig_sha256"] = "f" * 64
        result = evaluate_shareable_wearable_component(passing_manifest(), target)

        self.assertIn(
            "exact_target_body_rig_garment_binding_missing_or_ambiguous",
            result["failures"],
        )

    def test_baked_or_cloned_clothing_is_rejected(self) -> None:
        manifest = passing_manifest()
        manifest["component_artifact"]["clothing_baked_into_body"] = True
        manifest["share_policy"]["clone_on_transfer_allowed"] = True
        result = evaluate_shareable_wearable_component(manifest, passing_target())

        self.assertIn("clothing_baked_into_body", result["failures"])
        self.assertIn("clone_on_transfer_allowed", result["failures"])

    def test_adult_and_non_adult_lanes_do_not_silently_share(self) -> None:
        target = passing_target()
        target["maturity_class"] = "non_adult_doll_safe"
        result = evaluate_shareable_wearable_component(passing_manifest(), target)

        self.assertIn(
            "garment_and_target_maturity_lane_mismatch", result["failures"]
        )

    def test_age_up_presentation_label_alone_is_not_an_adult_lane(self) -> None:
        target = passing_target()
        target["maturity_class"] = "adult_aged_up_variant"
        result = evaluate_shareable_wearable_component(passing_manifest(), target)

        self.assertFalse(result["contract_compatible_for_private_share_fit_review"])
        self.assertIn("target_maturity_class_invalid", result["failures"])

    def test_target_review_flags_are_evidence_not_self_authority(self) -> None:
        manifest = passing_manifest()
        binding = manifest["target_bindings"][0]
        binding["penetration_reviewed"] = False
        binding["put_on_take_off_reviewed"] = False
        result = evaluate_shareable_wearable_component(manifest, passing_target())

        self.assertIn("target_penetration_not_reviewed", result["failures"])
        self.assertIn("target_put_on_take_off_not_reviewed", result["failures"])

    def test_policy_explicitly_preserves_positive_proof_gate(self) -> None:
        policy = json.loads(
            (
                ROOT
                / "Avatar/avatar_builder/policies/separate_shareable_wearable_components_v1.json"
            ).read_text(encoding="utf-8")
        )
        positive = json.loads(
            (
                ROOT
                / "Avatar/avatar_builder/policies/positive_proof_autobuild_gate_v1.json"
            ).read_text(encoding="utf-8")
        )

        self.assertFalse(policy["release_limits"]["may_release_positive_proof_autobuild"])
        self.assertEqual(
            policy["release_limits"]["positive_proof_policy_remains"],
            "Avatar/avatar_builder/policies/positive_proof_autobuild_gate_v1.json",
        )
        self.assertEqual(
            positive["status"], "locked_awaiting_owner_approved_positive_proof"
        )


if __name__ == "__main__":
    unittest.main()
