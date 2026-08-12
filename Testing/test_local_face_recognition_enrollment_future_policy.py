from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "Data" / "governance" / "local_face_recognition_enrollment_future_policy_v1.json"
DEVICE_CONFIG_PATH = ROOT / "config" / "kira_text_voice_device_capture.json"
POLICY_SHA256 = "ff0f98eacbf6c99bed967a84705fb60b079869e4618245cff959904c3917cd29"


def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise ValueError(f"nonfinite number: {value}")


class LocalFaceRecognitionEnrollmentFuturePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = POLICY_PATH.read_bytes()
        cls.policy = json.loads(
            cls.raw,
            object_pairs_hook=strict_object,
            parse_constant=reject_constant,
        )

    def test_exact_policy_identity_and_current_runtime_remain_off(self) -> None:
        self.assertEqual(len(self.raw), 4370)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), POLICY_SHA256)
        current = self.policy["current_runtime"]
        self.assertIs(current["identity_recognition_enabled"], False)
        self.assertIs(current["biometric_template_creation_enabled"], False)
        self.assertIs(current["unknown_face_image_persistence_enabled"], False)
        self.assertIs(current["background_surveillance_enabled"], False)
        live_config = json.loads(DEVICE_CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertIs(live_config["camera"]["identity_recognition_enabled"], False)

    def test_owner_discussion_must_precede_any_design_freeze_or_implementation(self) -> None:
        self.assertEqual(
            self.policy["status"],
            "future_discussion_draft_current_runtime_identity_recognition_off",
        )
        discussion = self.policy["owner_discussion"]
        for key in (
            "required_before_design_freeze",
            "natural_social_memory_and_privacy_interaction_unresolved",
            "simple_permission_prompt_is_not_an_accepted_final_design",
            "implementation_must_wait",
        ):
            self.assertIs(discussion[key], True)

    def test_biological_and_synthetic_robert_are_exactly_separate(self) -> None:
        identity = self.policy["identity_separation"]
        self.assertEqual(identity["owner_subject_id"], "biological_robert")
        self.assertIs(identity["synthetic_robert_is_separate_person"], True)
        self.assertIs(identity["account_owner_avatar_or_name_equivalence_allowed"], False)

    def test_unknown_person_cannot_be_silently_saved_or_enrolled(self) -> None:
        visitor = self.policy["unknown_visitor"]
        self.assertEqual(visitor["initial_label"], "unknown_person")
        for key in (
            "identity_guessing_allowed",
            "automatic_image_save_allowed",
            "automatic_template_creation_allowed",
        ):
            self.assertIs(visitor[key], False)
        for key in (
            "camera_and_purpose_notice_required_before_request",
            "exact_visitor_explicit_informed_consent_required",
            "owner_consent_cannot_substitute_for_visitor_consent",
            "decline_ignore_or_no_response_means_no_enrollment",
            "multi_angle_profile_may_be_offered_only_after_consent",
        ):
            self.assertIs(visitor[key], True)

    def test_storage_is_local_revocable_and_reference_images_need_extra_opt_in(self) -> None:
        storage = self.policy["capture_and_storage"]
        self.assertIs(storage["local_only"], True)
        self.assertIs(storage["network_transmission_allowed"], False)
        self.assertIs(storage["cloud_lookup_allowed"], False)
        self.assertIs(storage["raw_burst_retained_by_default"], False)
        self.assertIs(storage["raw_burst_deleted_after_template_derivation"], True)
        self.assertIs(
            storage["selected_reference_image_retention_requires_separate_person_opt_in"],
            True,
        )
        self.assertIs(storage["subject_revocation_and_deletion_required"], True)
        self.assertIs(storage["revocation_wipes_template_and_retained_reference_images"], True)

    def test_private_acquaintance_memory_is_kira_accessible_not_owner_browsable(self) -> None:
        memory = self.policy["private_acquaintance_memory"]
        self.assertEqual(
            memory["purpose"],
            "allow_kira_to_remember_and_recognize_a_consented_acquaintance_next_time",
        )
        for key in (
            "visitor_may_offer_chosen_name_or_nickname",
            "visitor_consent_and_kira_choice_are_both_required",
            "person_chosen_name_may_link_to_local_face_template_after_consent",
            "ordinary_kira_runtime_recognition_access_allowed",
            "kira_may_withhold_private_acquaintance_details",
            "conversation_memory_permission_is_separate_from_face_enrollment",
            "application_level_kira_only_privacy_required",
        ):
            self.assertIs(memory[key], True)
        for key in (
            "ordinary_owner_creator_or_other_person_browse_access_allowed",
            "contact_sheet_gallery_or_bulk_export_allowed",
            "windows_administrator_absolute_exclusion_claim_allowed",
        ):
            self.assertIs(memory[key], False)

    def test_face_result_has_no_authority_or_sensitive_attribute_inference(self) -> None:
        matching = self.policy["matching"]
        self.assertEqual(matching["uncertain_result"], "unknown_person")
        self.assertIs(
            matching["identity_result_cannot_authorize_commands_payments_locks_or_private_access"],
            True,
        )
        prohibited = set(self.policy["prohibited_inferences"])
        self.assertEqual(len(prohibited), 8)
        self.assertIn("emotion_or_mental_state", prohibited)
        self.assertIn("relationship_or_consent", prohibited)

    def test_policy_is_not_live_authority(self) -> None:
        boundary = self.policy["acceptance_boundary"]
        for key in (
            "separate_append_only_implementation_required",
            "different_independent_static_review_required",
            "supervised_live_owner_acceptance_required",
            "visitor_enrollment_live_test_requires_that_visitor_consent",
            "current_policy_does_not_authorize_capture_enrollment_matching_or_persistence",
        ):
            self.assertIs(boundary[key], True)


if __name__ == "__main__":
    unittest.main()
