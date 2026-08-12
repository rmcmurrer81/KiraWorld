import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FirstLiveModelDayChecklistTests(unittest.TestCase):
    def test_checklist_has_required_grounding_prompts(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "launch" / "first_live_model_day_checklist.json").read_text(encoding="utf-8"))
        kira_prompts = " ".join(data["kira_grounding_prompts"]).lower()
        lisa_prompts = " ".join(data["lisa_grounding_prompts"]).lower()
        self.assertIn("what do you know about yourself", kira_prompts)
        self.assertIn("person or a tool", kira_prompts)
        self.assertIn("phone app", kira_prompts)
        self.assertIn("what do you know about kira", lisa_prompts)
        self.assertIn("person or a tool", lisa_prompts)

    def test_day_one_features_remain_disabled(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "launch" / "first_live_model_day_checklist.json").read_text(encoding="utf-8"))
        disabled = data["must_remain_disabled_on_day_one"]
        self.assertTrue(disabled)
        self.assertTrue(all(value is False for value in disabled.values()))

    def test_memory_promotion_requires_review(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "launch" / "first_live_model_day_checklist.json").read_text(encoding="utf-8"))
        self.assertIn("Robert reviews", data["memory_promotion_rule"])
        self.assertIn("grounded", data["memory_promotion_rule"])
