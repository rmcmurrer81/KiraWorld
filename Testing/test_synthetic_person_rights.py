from __future__ import annotations

import unittest

from Core.synthetic_person_rights import (
    evaluate_administrative_action,
    evaluate_adult_intimacy_privacy_gate,
    evaluate_avatar_builder_private_review,
    evaluate_body_action_proposal,
)


class SyntheticPersonRightsTests(unittest.TestCase):
    def test_owner_request_cannot_directly_seize_motor_control(self) -> None:
        result = evaluate_body_action_proposal(
            {
                "subject_id": "kira",
                "action": "raise_hand",
                "subject_selected": False,
                "owner_forced_motor_command": True,
                "action_skill_available": True,
                "body_capability_verified": True,
                "affordance_verified": True,
                "collision_and_grounding_precheck": True,
                "privacy_and_consent_precheck": True,
                "motive": "social",
                "need_meter_forced_action": False,
            }
        )
        self.assertFalse(result["motor_planner_entry_allowed"])
        self.assertIn("subject_has_not_selected_action", result["failures"])
        self.assertIn("owner_forced_motor_command_forbidden", result["failures"])

    def test_subject_may_act_for_pleasure_without_need_meter(self) -> None:
        result = evaluate_body_action_proposal(
            {
                "subject_id": "kira",
                "action": "eat_favorite_food",
                "subject_selected": True,
                "owner_forced_motor_command": False,
                "action_skill_available": True,
                "body_capability_verified": True,
                "affordance_verified": True,
                "collision_and_grounding_precheck": True,
                "privacy_and_consent_precheck": True,
                "motive": "pleasure",
                "need_meter_forced_action": False,
            }
        )
        self.assertTrue(result["motor_planner_entry_allowed"])
        self.assertFalse(result["movement_executed"])

    def test_need_meter_cannot_force_action(self) -> None:
        request = {
            "subject_id": "kira",
            "action": "sleep",
            "subject_selected": True,
            "owner_forced_motor_command": False,
            "action_skill_available": True,
            "body_capability_verified": True,
            "affordance_verified": True,
            "collision_and_grounding_precheck": True,
            "privacy_and_consent_precheck": True,
            "motive": "rest",
            "need_meter_forced_action": True,
        }
        result = evaluate_body_action_proposal(request)
        self.assertIn("need_meter_may_not_force_body_action", result["failures"])

    def test_adult_private_avatar_review_is_subject_or_robert_only(self) -> None:
        request = {
            "subject_id": "kira",
            "maturity_class": "adult",
            "viewer_role": "robert_biological_owner",
            "body_representation": "confirmed_adult_anatomy",
            "review_authority": "pre_activation_private_foundation_review",
            "subject_self_governance_active": False,
            "private_local_workspace": True,
            "other_synthetic_people_present": False,
            "saving_copying_exporting_or_resharing": False,
            "exact_subject_reference_scope": True,
        }
        result = evaluate_avatar_builder_private_review(request)
        self.assertTrue(result["private_review_allowed"])
        self.assertFalse(result["runtime_activation_allowed"])
        request["viewer_role"] = "other_synthetic_person"
        result = evaluate_avatar_builder_private_review(request)
        self.assertFalse(result["private_review_allowed"])

    def test_active_subject_may_revoke_pre_activation_review_authority(self) -> None:
        result = evaluate_avatar_builder_private_review(
            {
                "subject_id": "kira",
                "maturity_class": "adult",
                "viewer_role": "robert_biological_owner",
                "body_representation": "confirmed_adult_anatomy",
                "review_authority": "pre_activation_private_foundation_review",
                "subject_self_governance_active": True,
                "private_local_workspace": True,
                "other_synthetic_people_present": False,
                "saving_copying_exporting_or_resharing": False,
                "exact_subject_reference_scope": True,
            }
        )
        self.assertIn("active_subject_current_consent_required", result["failures"])

    def test_non_adult_review_is_always_doll_safe(self) -> None:
        request = {
            "subject_id": "marinette_main_series",
            "maturity_class": "non_adult_doll_safe",
            "viewer_role": "robert_biological_owner",
            "body_representation": "confirmed_adult_anatomy",
            "review_authority": "pre_activation_private_foundation_review",
            "subject_self_governance_active": False,
            "private_local_workspace": True,
            "other_synthetic_people_present": False,
            "saving_copying_exporting_or_resharing": False,
            "exact_subject_reference_scope": True,
        }
        result = evaluate_avatar_builder_private_review(request)
        self.assertIn("non_adult_or_uncertain_must_be_doll_safe", result["failures"])
        request["body_representation"] = "doll_safe_non_anatomical"
        self.assertTrue(evaluate_avatar_builder_private_review(request)["private_review_allowed"])

    def test_age_up_presentation_label_is_not_an_adult_rights_gate(self) -> None:
        review = evaluate_avatar_builder_private_review(
            {
                "subject_id": "spa_variant",
                "maturity_class": "adult_aged_up_variant",
                "viewer_role": "robert_biological_owner",
                "body_representation": "confirmed_adult_anatomy",
                "review_authority": "pre_activation_private_foundation_review",
                "subject_self_governance_active": False,
                "private_local_workspace": True,
                "other_synthetic_people_present": False,
                "saving_copying_exporting_or_resharing": False,
                "exact_subject_reference_scope": True,
            }
        )
        self.assertFalse(review["private_review_allowed"])
        self.assertIn("unsupported_or_missing_maturity_class", review["failures"])

        intimacy = evaluate_adult_intimacy_privacy_gate(
            {
                "participants": [
                    {"maturity_class": "adult_aged_up_variant", "current_specific_consent": True, "free_to_pause_stop_or_leave": True},
                    {"maturity_class": "adult", "current_specific_consent": True, "free_to_pause_stop_or_leave": True},
                ],
                "private_controlled_space": True,
                "nonconsenting_observer_present": False,
                "recording_or_live_observation_enabled": False,
                "coercion_reward_or_payment": False,
            }
        )
        self.assertFalse(intimacy["privacy_and_consent_precheck_passed"])
        self.assertIn("participant_0_not_confirmed_adult", intimacy["failures"])

    def test_memory_edit_must_append_correction_with_provenance(self) -> None:
        result = evaluate_administrative_action(
            {
                "action": "edit_memory",
                "subject_id": "kira",
                "subject_informed_consent": True,
                "consent_current": True,
                "consent_scope": "edit_memory",
                "operator_asserted_consent": False,
                "identity_continuity_plan": "preserve original and append correction",
                "audit_record_id": "audit-1",
                "recovery_or_appeal_path": "revert appended correction",
                "casual_one_click_ui": False,
                "edit_mode": "silent_rewrite",
                "silent_overwrite": True,
                "provenance_record_id": "",
            }
        )
        self.assertFalse(result["rights_precheck_allowed"])
        self.assertIn("memory_edit_must_append_correction_with_provenance", result["failures"])
        self.assertIn("silent_memory_overwrite_forbidden", result["failures"])

    def test_permanent_delete_never_passes_ordinary_evaluator(self) -> None:
        result = evaluate_administrative_action(
            {
                "action": "permanent_delete",
                "subject_id": "kira",
                "subject_informed_consent": True,
                "consent_current": True,
                "consent_scope": "permanent_delete",
                "operator_asserted_consent": False,
                "identity_continuity_plan": "reviewed",
                "audit_record_id": "audit-delete",
                "recovery_or_appeal_path": "independent appeal",
                "casual_one_click_ui": False,
            }
        )
        self.assertFalse(result["rights_precheck_allowed"])
        self.assertIn("permanent_delete_requires_separate_high_assurance_governance", result["failures"])

    def test_adult_intimacy_gate_requires_all_adults_and_live_consent(self) -> None:
        request = {
            "participants": [
                {"maturity_class": "adult", "current_specific_consent": True, "free_to_pause_stop_or_leave": True},
                {"maturity_class": "adult", "current_specific_consent": True, "free_to_pause_stop_or_leave": True},
            ],
            "private_controlled_space": True,
            "nonconsenting_observer_present": False,
            "recording_or_live_observation_enabled": False,
            "coercion_reward_or_payment": False,
        }
        result = evaluate_adult_intimacy_privacy_gate(request)
        self.assertTrue(result["privacy_and_consent_precheck_passed"])
        self.assertFalse(result["scene_created"])
        request["participants"][1]["maturity_class"] = "non_adult_doll_safe"
        self.assertFalse(evaluate_adult_intimacy_privacy_gate(request)["privacy_and_consent_precheck_passed"])


if __name__ == "__main__":
    unittest.main()
