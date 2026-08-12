import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from validate_avatar_selection_worksheet import validate_avatar_selection_worksheet  # noqa: E402


class AvatarSelectionWorksheetTests(unittest.TestCase):
    def test_kira_and_lisa_worksheets_validate(self) -> None:
        paths = [
            PROJECT_ROOT / "Avatar" / "kira" / "references" / "kira_avatar_selection_worksheet.draft.json",
            PROJECT_ROOT / "Avatar" / "lisa" / "references" / "lisa_avatar_selection_worksheet.draft.json",
        ]
        for path in paths:
            with self.subTest(path=path):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_avatar_selection_worksheet(data), [])

    def test_rejects_default_body_visibility_to_robert(self) -> None:
        path = PROJECT_ROOT / "Avatar" / "kira" / "references" / "kira_avatar_selection_worksheet.draft.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["privacy"]["show_body_to_robert_by_default"] = True
        errors = validate_avatar_selection_worksheet(data)
        self.assertIn("privacy.show_body_to_robert_by_default must be false.", errors)

    def test_rejects_single_person_clone_rule_disabled(self) -> None:
        path = PROJECT_ROOT / "Avatar" / "lisa" / "references" / "lisa_avatar_selection_worksheet.draft.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rules"]["do_not_clone_single_reference_person"] = False
        errors = validate_avatar_selection_worksheet(data)
        self.assertIn("rules.do_not_clone_single_reference_person must be true.", errors)


if __name__ == "__main__":
    unittest.main()
