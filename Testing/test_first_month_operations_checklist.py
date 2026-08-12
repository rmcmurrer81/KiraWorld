import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from validate_first_month_operations_checklist import validate_first_month_operations_checklist  # noqa: E402


class FirstMonthOperationsChecklistTests(unittest.TestCase):
    def _load(self) -> dict:
        path = PROJECT_ROOT / "Data" / "launch" / "first_month_operations_checklist.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_checklist_validates(self) -> None:
        self.assertEqual(validate_first_month_operations_checklist(self._load()), [])

    def test_first_week_must_have_seven_days(self) -> None:
        data = self._load()
        data["first_week"] = data["first_week"][:6]
        errors = validate_first_month_operations_checklist(data)
        self.assertTrue(any("exactly 7" in error for error in errors))

    def test_stage_rule_blocks_everything_at_once(self) -> None:
        data = self._load()
        data["stage_rule"]["do_not_enable_everything_at_once"] = False
        errors = validate_first_month_operations_checklist(data)
        self.assertTrue(any("do_not_enable_everything_at_once" in error for error in errors))

    def test_daily_checks_require_no_hallucination_promotion(self) -> None:
        data = self._load()
        data["daily_checks"] = [item for item in data["daily_checks"] if item != "no_hallucinations_promoted"]
        errors = validate_first_month_operations_checklist(data)
        self.assertTrue(any("no_hallucinations_promoted" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
