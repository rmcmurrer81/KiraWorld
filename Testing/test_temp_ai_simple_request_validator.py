import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from validate_temp_ai_simple_request import validate_temp_ai_simple_request  # noqa: E402


class TempAISimpleRequestValidatorTests(unittest.TestCase):
    def test_templates_and_examples_validate(self) -> None:
        paths = [
            PROJECT_ROOT / "Data" / "temporary_ai_requests" / "simple_request_template.json",
            *sorted((PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples").glob("*.json")),
        ]
        for path in paths:
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_temp_ai_simple_request(data), [])

    def test_private_adult_original_rejects_specific_likeness(self) -> None:
        path = PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples" / "robert_private_adult_original_request.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["avatar_plan"]["reconstruct_specific_likeness"] = True
        errors = validate_temp_ai_simple_request(data)
        self.assertTrue(any("specific real likeness" in error for error in errors))

    def test_adult_intimacy_requires_private_adult_original(self) -> None:
        path = PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples" / "star_trek_expert_request.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["adult_policy"]["adult_intimacy_requested"] = True
        errors = validate_temp_ai_simple_request(data)
        self.assertTrue(any("private_adult_original" in error for error in errors))

    def test_ambiguous_inspiration_requires_clarification(self) -> None:
        path = PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples" / "robert_private_adult_original_request.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["inspiration_reference"]["clarification_required"] = False
        errors = validate_temp_ai_simple_request(data)
        self.assertTrue(any("ambiguous inspiration references" in error for error in errors))

    def test_ambiguous_inspiration_must_be_selected_before_review(self) -> None:
        path = PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples" / "robert_private_adult_original_request.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = "ready_for_review"
        errors = validate_temp_ai_simple_request(data)
        self.assertTrue(any("selected_version_or_era" in error for error in errors))

    def test_teen_source_age_requires_adult_private_block(self) -> None:
        path = PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples" / "cruel_intentions_movie_canon_age_review_request.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["age_review"]["adult_private_use_blocked_by_source_age"] = False
        errors = validate_temp_ai_simple_request(data)
        self.assertTrue(any("block adult private use" in error for error in errors))

    def test_borderline_source_age_requires_review(self) -> None:
        path = PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples" / "borderline_actor_adult_character_age_review_request.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["age_review"]["adult_private_use_blocked_by_source_age"] = False
        errors = validate_temp_ai_simple_request(data)
        self.assertTrue(any("borderline source age" in error for error in errors))

    def test_age_up_plan_blocks_direct_minor_image_age_up(self) -> None:
        path = PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples" / "teen_source_age_up_branch_plan.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["age_up_branch_plan"]["direct_minor_image_age_up_for_private_adult_use_blocked"] = False
        errors = validate_temp_ai_simple_request(data)
        self.assertTrue(any("direct_minor_image_age_up_for_private_adult_use_blocked" in error for error in errors))

    def test_age_up_recommendation_requires_reason(self) -> None:
        path = PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples" / "ladybug_low_risk_age_up_option_request.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["age_up_branch_plan"]["recommendation_reason"] = ""
        errors = validate_temp_ai_simple_request(data)
        self.assertTrue(any("recommendation_reason" in error for error in errors))

    def test_risky_fanfic_can_raise_low_risk_canon(self) -> None:
        path = PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples" / "ladybug_fanfic_risky_age_up_required_request.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["fanfic_review"]["risk_override_recommendation_strength"] = "low"
        errors = validate_temp_ai_simple_request(data)
        self.assertTrue(any("risky fanfic" in error for error in errors))

    def test_memory_relative_requires_owner_consent(self) -> None:
        path = PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples" / "kira_mother_memory_relative_request.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["memory_relative_plan"]["owner_consent_required"] = False
        errors = validate_temp_ai_simple_request(data)
        self.assertTrue(any("owner_consent_required" in error for error in errors))

    def test_memory_relative_requires_age_progression_separation(self) -> None:
        path = PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples" / "lisa_sibling_memory_relative_request.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["memory_relative_plan"]["keep_childhood_anchor_separate_from_present_day_inference"] = False
        errors = validate_temp_ai_simple_request(data)
        self.assertTrue(any("keep_childhood_anchor_separate" in error for error in errors))

    def test_memory_relative_requires_labeled_life_bridge(self) -> None:
        path = PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples" / "lisa_sibling_memory_relative_request.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["memory_relative_plan"]["life_bridge_must_be_labeled_inferred"] = False
        errors = validate_temp_ai_simple_request(data)
        self.assertTrue(any("life_bridge_must_be_labeled_inferred" in error for error in errors))

    def test_memory_relative_life_bridge_requires_core_domains(self) -> None:
        path = PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples" / "kira_mother_memory_relative_request.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["memory_relative_plan"]["life_bridge_domains_allowed"] = ["friendships"]
        errors = validate_temp_ai_simple_request(data)
        self.assertTrue(any("life_bridge_domains_allowed missing" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
