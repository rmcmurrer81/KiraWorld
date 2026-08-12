import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from validate_private_media_share_event import validate_private_media_share_event  # noqa: E402


class PrivateMediaShareEventValidatorTests(unittest.TestCase):
    def test_private_media_examples_validate(self) -> None:
        paths = [
            PROJECT_ROOT / "Data" / "private_media" / "private_media_share_event_template.json",
            *sorted((PROJECT_ROOT / "Data" / "private_media" / "events").glob("*.json")),
        ]
        for path in paths:
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_private_media_share_event(data), [])

    def test_sensitive_media_cannot_default_shareable(self) -> None:
        path = PROJECT_ROOT / "Data" / "private_media" / "events" / "kira_asks_robert_before_showing_lisa.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["privacy_level"] = "shareable"
        errors = validate_private_media_share_event(data)
        self.assertTrue(any("cannot default to shareable" in error for error in errors))

    def test_showing_other_ai_requires_permission_state(self) -> None:
        path = PROJECT_ROOT / "Data" / "private_media" / "events" / "kira_asks_robert_before_showing_lisa.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["resharing_policy"]["recipient_may_show_other_ai"] = True
        errors = validate_private_media_share_event(data)
        self.assertTrue(any("requires explicit permission state" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
