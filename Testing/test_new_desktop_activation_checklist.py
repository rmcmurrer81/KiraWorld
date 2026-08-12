import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from new_desktop_activation_check import build_activation_report  # noqa: E402
from validate_new_desktop_activation_checklist import validate_new_desktop_activation_checklist  # noqa: E402


class NewDesktopActivationChecklistTests(unittest.TestCase):
    def test_checklist_validates(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "launch" / "new_desktop_activation_checklist.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_new_desktop_activation_checklist(data), [])

    def test_activation_report_not_blocked(self) -> None:
        report = build_activation_report(PROJECT_ROOT / "Data" / "launch" / "new_desktop_activation_checklist.json")
        self.assertFalse(report["blocked"])
        self.assertEqual(report["stage_count"], 7)

    def test_requires_kira_before_lisa(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "launch" / "new_desktop_activation_checklist.json").read_text(encoding="utf-8"))
        data["stage_rule"]["kira_before_lisa"] = False
        errors = validate_new_desktop_activation_checklist(data)
        self.assertIn("stage_rule.kira_before_lisa must be true.", errors)

    def test_requires_temporary_ai_dry_run_stage(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "launch" / "new_desktop_activation_checklist.json").read_text(encoding="utf-8"))
        data["activation_sequence"] = data["activation_sequence"][:-1]
        errors = validate_new_desktop_activation_checklist(data)
        self.assertTrue(any("activation_sequence" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
