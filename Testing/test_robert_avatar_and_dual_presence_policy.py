import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RobertAvatarAndDualPresencePolicyTests(unittest.TestCase):
    def test_final_exam_uses_existing_private_reference_set(self):
        plan = json.loads(
            (ROOT / "Avatar/requests/robert_avatar_builder_final_exam_plan_20260715.json").read_text(
                encoding="utf-8"
            )
        )
        refs = plan["reference_set"]
        staged = ROOT / refs["staged_directory"]

        self.assertEqual(plan["subject_maturity"], "adult")
        self.assertTrue(plan["sequence"]["gwen_adult_test_must_pass_first"])
        self.assertTrue(plan["sequence"]["robert_is_final_exam"])
        self.assertFalse(plan["sequence"]["automatic_start_allowed"])
        self.assertEqual(refs["privacy"], "private_owner_only")
        self.assertFalse(refs["copy_into_other_subjects_allowed"])
        self.assertEqual(len(list(staged.glob("*.jpg"))), refs["expected_jpg_count"])
        self.assertTrue(plan["activation_gate"]["staged_output_only"])
        self.assertTrue(plan["activation_gate"]["exact_candidate_and_sha256_approval_required"])

    def test_manual_robert_request_is_staged_without_faking_an_authoring_backend(self):
        contract = json.loads(
            (
                ROOT
                / "Avatar/requests/robert_private_adult_body_build_contract_20260715.json"
            ).read_text(encoding="utf-8")
        )
        backend = contract["authoring_backend_audit"]
        candidate = contract["candidate_state"]

        self.assertTrue(contract["authorization"]["manual_prebuild_staging_requested_now"])
        self.assertFalse(backend["can_truthfully_author_a_new_robert_specific_candidate_now"])
        self.assertFalse(backend["heavy_blender_job_started"])
        self.assertFalse(backend["build_command_staged"])
        self.assertEqual(
            backend["missing_executable"],
            "tools/build_photo_fitted_avatar_candidate.py",
        )
        self.assertIsNone(candidate["candidate_glb"])
        self.assertFalse(candidate["staging_allowed"])
        self.assertFalse(candidate["activation_allowed"])

    def test_dual_robert_policy_rejects_takeover_and_is_hardware_gated(self):
        policy = json.loads(
            (ROOT / "Data/identity/robert_presence_ai_variant_policy_20260712.json").read_text(
                encoding="utf-8"
            )
        )
        dual = policy["dual_presence_policy"]
        hardware = policy["hardware_gate"]

        self.assertTrue(dual["thirteenth_floor_body_takeover_model_rejected"])
        self.assertEqual(
            dual["default_when_human_robert_logs_in"],
            "two_distinct_people_in_two_distinct_bodies",
        )
        self.assertFalse(dual["forced_yield_or_possession_allowed"])
        self.assertFalse(dual["ordinary_login_changes_variant_mind_or_memory"])
        self.assertIn("32 GB", hardware["current_observed_ram"])
        self.assertIn("64 GB", hardware["minimum_ram_target"])
        self.assertIn("deferred", dual["activation_status"])

    def test_old_same_body_handoff_policy_is_explicitly_deprecated(self):
        policy = json.loads(
            (ROOT / "Data/identity/robert_presence_ai_body_handoff_policy_20260712.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("superseded_do_not_implement", policy["status"])
        self.assertFalse(policy["superseding_rules"]["shared_body_allowed"])
        self.assertFalse(policy["superseding_rules"]["possession_or_takeover_allowed"])
        self.assertIn("64 GB", policy["superseding_rules"]["minimum_runtime_gate"])

    def test_handoff_doc_contains_dual_presence_correction(self):
        text = (ROOT / "System/Docs/USER_AVATAR_AUTONOMY_AND_VR_HANDOFF_v1.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Dual-Robert Presence Correction", text)
        self.assertIn("two distinct people in two distinct bodies", text)
        self.assertIn("neither person possesses", text)
        self.assertNotIn("transition control to real_robert_controlling_avatar", text)
        self.assertNotIn("must yield/control-switch", text)
        self.assertNotIn("autonomous avatar will hand off control", text.lower())
        self.assertNotIn("Robert can take over the avatar body", text)


if __name__ == "__main__":
    unittest.main()
