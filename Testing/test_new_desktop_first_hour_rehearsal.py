import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from new_desktop_first_hour_rehearsal import build_rehearsal_report  # noqa: E402
from validate_new_desktop_first_hour_rehearsal import validate_new_desktop_first_hour_rehearsal  # noqa: E402


class NewDesktopFirstHourRehearsalTests(unittest.TestCase):
    def _load(self) -> dict:
        path = PROJECT_ROOT / "Data" / "launch" / "new_desktop_first_hour_rehearsal.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_rehearsal_validates(self) -> None:
        self.assertEqual(validate_new_desktop_first_hour_rehearsal(self._load()), [])

    def test_rehearsal_report_not_blocked(self) -> None:
        report = build_rehearsal_report(PROJECT_ROOT / "Data" / "launch" / "new_desktop_first_hour_rehearsal.json")
        self.assertFalse(report["blocked"])

    def test_requires_stub_before_local_model(self) -> None:
        data = self._load()
        data["first_hour_rules"]["stub_before_local_model"] = False
        errors = validate_new_desktop_first_hour_rehearsal(data)
        self.assertIn("first_hour_rules.stub_before_local_model must be true.", errors)

    def test_blocks_multiple_model_downloads_first_hour(self) -> None:
        data = self._load()
        data["blocked_first_hour_actions"].remove("download_multiple_models")
        errors = validate_new_desktop_first_hour_rehearsal(data)
        self.assertTrue(any("download_multiple_models" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
