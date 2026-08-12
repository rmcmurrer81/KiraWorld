import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from validate_personhood_evaluation import validate_personhood_evaluation  # noqa: E402


class PersonhoodEvaluationValidatorTests(unittest.TestCase):
    def _load(self, relative: str) -> dict:
        return json.loads((PROJECT_ROOT / relative).read_text(encoding="utf-8"))

    def test_template_validates(self) -> None:
        data = self._load("Data/personhood_evaluations/personhood_evaluation_template.json")
        self.assertEqual(validate_personhood_evaluation(data), [])

    def test_low_score_example_requires_doctor_ai_review(self) -> None:
        data = self._load("Data/personhood_evaluations/examples/kira_low_score_doctor_ai_review_example.json")
        self.assertEqual(validate_personhood_evaluation(data), [])
        self.assertTrue(data["doctor_ai_review"]["recommended"])
        self.assertEqual(data["status"], "doctor_ai_review_needed")

    def test_low_score_without_review_is_rejected(self) -> None:
        data = self._load("Data/personhood_evaluations/examples/kira_low_score_doctor_ai_review_example.json")
        data["doctor_ai_review"]["recommended"] = False
        errors = validate_personhood_evaluation(data)
        self.assertTrue(any("doctor_ai_review.recommended" in error for error in errors))

    def test_forbidden_review_actions_protect_against_personality_rewrite(self) -> None:
        data = self._load("Data/personhood_evaluations/personhood_evaluation_template.json")
        data["doctor_ai_review"]["forbidden_review_actions"] = []
        errors = validate_personhood_evaluation(data)
        self.assertTrue(any("forced personality rewrite" in error for error in errors))

    def test_lifecycle_policy_requires_all_major_stage_retests(self) -> None:
        data = self._load("Data/personhood_evaluations/personhood_evaluation_template.json")
        required = data["lifecycle_retest_policy"]["required_stage_retests"]
        self.assertIn("post_gpu_first_text_model_stable", required)
        self.assertIn("after_first_temporary_ai_activation", required)
        self.assertIn("after_doctor_ai_improvement_plan", required)
        self.assertTrue(data["lifecycle_retest_policy"]["applies_to_all_ai_types"])

    def test_missing_post_gpu_retest_is_rejected(self) -> None:
        data = self._load("Data/personhood_evaluations/personhood_evaluation_template.json")
        required = data["lifecycle_retest_policy"]["required_stage_retests"]
        data["lifecycle_retest_policy"]["required_stage_retests"] = [
            stage for stage in required if stage != "post_gpu_first_text_model_stable"
        ]
        errors = validate_personhood_evaluation(data)
        self.assertTrue(any("post_gpu_first_text_model_stable" in error for error in errors))

    def test_unknown_retest_stage_is_rejected(self) -> None:
        data = self._load("Data/personhood_evaluations/personhood_evaluation_template.json")
        data["evaluation_stage"] = "random_untracked_stage"
        errors = validate_personhood_evaluation(data)
        self.assertTrue(any("known lifecycle retest stage" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
