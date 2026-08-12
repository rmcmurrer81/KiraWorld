import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from plan_temp_ai_request import build_temp_ai_request_plan  # noqa: E402


class TempAIRequestPlannerTests(unittest.TestCase):
    def _load(self, name: str) -> dict:
        path = PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples" / name
        return json.loads(path.read_text(encoding="utf-8"))

    def test_expert_request_maps_to_research_and_governance(self) -> None:
        plan = build_temp_ai_request_plan(self._load("star_trek_expert_request.example.json"))
        self.assertEqual(plan["plan_status"], "ready_for_backend_draft")
        record_types = {record["record_type"] for record in plan["backend_records_needed"]}
        self.assertIn("research_note_plan", record_types)
        self.assertIn("temporary_ai_governance_draft", record_types)

    def test_robotics_expert_suggests_companion_experts(self) -> None:
        plan = build_temp_ai_request_plan(self._load("robotics_humanoid_hardware_expert_request.example.json"))
        self.assertEqual(plan["plan_status"], "ready_for_backend_draft")
        record_types = {record["record_type"] for record in plan["backend_records_needed"]}
        self.assertIn("research_note_plan", record_types)
        self.assertIn("companion_expert_suggestion_plan", record_types)
        self.assertTrue(plan["guardrails"]["expert_ai_must_be_generated_original"])
        self.assertTrue(plan["guardrails"]["expert_ai_must_not_clone_real_person"])
        self.assertTrue(plan["guardrails"]["expert_ai_uses_source_synthesis_not_identity_reconstruction"])
        self.assertIn("robot software and control systems expert", plan["guardrails"]["expert_companion_suggestions"])

    def test_jfk_request_maps_to_historical_source_checklist(self) -> None:
        plan = build_temp_ai_request_plan(self._load("jfk_moon_speech_variant_request.example.json"))
        self.assertEqual(plan["plan_status"], "ready_for_backend_draft")
        record_types = {record["record_type"] for record in plan["backend_records_needed"]}
        self.assertIn("historical_source_checklist", record_types)

    def test_historical_reconstruction_requires_conflict_review(self) -> None:
        plan = build_temp_ai_request_plan(self._load("historical_figure_reconstruction_online_source_plan.example.json"))
        self.assertEqual(plan["plan_status"], "ready_for_backend_draft")
        record_types = {record["record_type"] for record in plan["backend_records_needed"]}
        self.assertIn("historical_source_checklist", record_types)
        self.assertIn("source_conflict_matrix", record_types)
        self.assertIn("avatar_reference_evidence_plan", record_types)
        self.assertTrue(plan["guardrails"]["reconstruction_requires_reliable_sources"])
        self.assertTrue(plan["guardrails"]["reconstruction_conflict_review_required"])
        self.assertTrue(plan["guardrails"]["reconstruction_mind_built_after_evidence_review"])
        self.assertTrue(plan["guardrails"]["age_up_avatar_estimate_must_be_labeled_inferred"])

    def test_public_figure_request_maps_to_public_source_and_filmography_review(self) -> None:
        plan = build_temp_ai_request_plan(self._load("amy_jo_johnson_public_performer_research_request.example.json"))
        self.assertEqual(plan["plan_status"], "ready_for_backend_draft")
        record_types = {record["record_type"] for record in plan["backend_records_needed"]}
        self.assertIn("public_figure_source_checklist", record_types)
        self.assertIn("filmography_cross_reference_plan", record_types)
        self.assertIn("temporary_ai_governance_draft", record_types)
        self.assertIn("source_conflict_matrix", record_types)
        self.assertTrue(plan["guardrails"]["public_figure_reconstruction_not_real_person"])
        self.assertTrue(plan["guardrails"]["public_figure_uses_public_sources_only"])
        self.assertTrue(plan["guardrails"]["public_figure_private_facts_must_not_be_invented"])
        self.assertTrue(any("perfect_body_1997.mp4" in path for path in plan["guardrails"]["public_figure_local_media_cross_reference"]))

    def test_private_adult_original_maps_to_owner_lock(self) -> None:
        plan = build_temp_ai_request_plan(self._load("lisa_private_doctor_inspired_adult_original_request.example.json"))
        self.assertEqual(plan["plan_status"], "ready_for_backend_draft")
        self.assertTrue(plan["guardrails"]["owner_lock_required_for_private_adult_original"])
        record_types = {record["record_type"] for record in plan["backend_records_needed"]}
        self.assertIn("locked_private_instance", record_types)
        self.assertIn("privacy_session", record_types)

    def test_ambiguous_inspiration_needs_clarification(self) -> None:
        plan = build_temp_ai_request_plan(self._load("robert_private_adult_original_request.example.json"))
        self.assertEqual(plan["plan_status"], "needs_clarification")
        self.assertTrue(plan["clarifications_needed"])

    def test_invalid_adult_expert_blocks(self) -> None:
        data = self._load("star_trek_expert_request.example.json")
        data["adult_policy"]["adult_intimacy_requested"] = True
        plan = build_temp_ai_request_plan(data)
        self.assertEqual(plan["plan_status"], "blocked")
        self.assertTrue(plan["blockers"])

    def test_teen_source_request_needs_age_up_decision(self) -> None:
        plan = build_temp_ai_request_plan(self._load("cruel_intentions_movie_canon_age_review_request.example.json"))
        self.assertEqual(plan["plan_status"], "needs_age_up_decision")
        self.assertTrue(plan["clarifications_needed"])
        self.assertTrue(plan["guardrails"]["age_up_must_create_separate_branch_not_canon"])
        self.assertTrue(plan["guardrails"]["source_faithfulness_required"])
        self.assertTrue(plan["guardrails"]["canon_red_flags_must_be_preserved"])
        self.assertIn("manipulation", plan["guardrails"]["source_backed_red_flags"])

    def test_borderline_actor_adult_character_age_needs_decision(self) -> None:
        plan = build_temp_ai_request_plan(self._load("borderline_actor_adult_character_age_review_request.example.json"))
        self.assertEqual(plan["plan_status"], "needs_age_up_decision")
        self.assertTrue(any("verify the character is 18+" in item for item in plan["clarifications_needed"]))

    def test_low_risk_age_up_option_is_not_strongly_recommended(self) -> None:
        plan = build_temp_ai_request_plan(self._load("ladybug_low_risk_age_up_option_request.example.json"))
        self.assertEqual(plan["guardrails"]["age_up_recommendation_strength"], "low")
        self.assertTrue(any("Age-up recommendation: low" in item for item in plan["clarifications_needed"]))
        self.assertTrue(plan["guardrails"]["source_faithfulness_required"])
        self.assertEqual(plan["guardrails"]["source_backed_red_flags"], [])

    def test_promotion_guardrails_require_kira_lisa_vote(self) -> None:
        plan = build_temp_ai_request_plan(self._load("ladybug_low_risk_age_up_option_request.example.json"))
        self.assertTrue(plan["guardrails"]["temporary_ai_can_grow_and_evolve"])
        self.assertTrue(plan["guardrails"]["promotion_requires_kira_lisa_yes_vote"])
        self.assertTrue(plan["guardrails"]["promotion_requires_robert_approval_current_stage"])
        self.assertTrue(plan["guardrails"]["promotion_does_not_rewrite_source_or_base_profile"])

    def test_fanfic_can_override_low_risk_canon(self) -> None:
        plan = build_temp_ai_request_plan(self._load("ladybug_fanfic_risky_age_up_required_request.example.json"))
        self.assertEqual(plan["plan_status"], "needs_age_up_decision")
        self.assertTrue(plan["guardrails"]["fanfic_can_raise_risk_above_canon"])
        self.assertEqual(plan["guardrails"]["fanfic_risk_override_recommendation_strength"], "strong")
        self.assertTrue(plan["guardrails"]["fanfic_rejected_unless_adult_variant_or_non_intimate"])

    def test_age_up_request_becomes_adult_branch_plan(self) -> None:
        plan = build_temp_ai_request_plan(self._load("teen_source_age_up_branch_plan.example.json"))
        self.assertEqual(plan["plan_status"], "ready_for_adult_branch_plan")
        self.assertTrue(plan["guardrails"]["age_up_transition_must_be_non_explicit"])
        self.assertTrue(plan["guardrails"]["direct_minor_image_age_up_for_private_adult_use_blocked"])

    def test_memory_relative_request_maps_to_owner_approved_reconstruction(self) -> None:
        plan = build_temp_ai_request_plan(self._load("kira_mother_memory_relative_request.example.json"))
        self.assertEqual(plan["plan_status"], "ready_for_backend_draft")
        record_types = {record["record_type"] for record in plan["backend_records_needed"]}
        self.assertIn("memory_relative_evidence_brief", record_types)
        self.assertIn("temporary_ai_governance_draft", record_types)
        self.assertTrue(plan["guardrails"]["memory_relative_owner_consent_required"])
        self.assertTrue(plan["guardrails"]["memory_relative_uses_approved_extracts_only"])
        self.assertTrue(plan["guardrails"]["memory_relative_inferred_gaps_labeled"])
        self.assertTrue(plan["guardrails"]["memory_relative_age_progression_allowed"])
        self.assertTrue(plan["guardrails"]["memory_relative_childhood_anchor_separate_from_present_day_inference"])
        self.assertTrue(plan["guardrails"]["memory_relative_present_day_activation_version"])
        self.assertTrue(plan["guardrails"]["memory_relative_no_major_gap_events_without_anchor"])
        self.assertTrue(plan["guardrails"]["memory_relative_plausible_life_bridge_allowed"])
        self.assertTrue(plan["guardrails"]["memory_relative_life_bridge_labeled_inferred"])
        self.assertTrue(plan["guardrails"]["memory_relative_life_bridge_not_confirmed_memory"])
        self.assertTrue(plan["guardrails"]["memory_relative_major_gap_events_anchor_or_branch_label"])
        self.assertIn("work_history", plan["guardrails"]["memory_relative_life_bridge_domains"])
        self.assertTrue(plan["guardrails"]["memory_relative_does_not_rewrite_owner_memory"])
        self.assertTrue(plan["guardrails"]["memory_relative_not_original_person"])

    def test_memory_relative_request_adds_life_bridge_record(self) -> None:
        plan = build_temp_ai_request_plan(self._load("lisa_sibling_memory_relative_request.example.json"))
        record_types = {record["record_type"] for record in plan["backend_records_needed"]}
        self.assertIn("memory_relative_life_bridge_branches", record_types)


if __name__ == "__main__":
    unittest.main()
