import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from validate_remote_contact_event import validate_remote_contact_event  # noqa: E402


class RemoteContactEventValidatorTests(unittest.TestCase):
    def test_remote_contact_examples_validate(self) -> None:
        paths = [
            PROJECT_ROOT / "Data" / "remote_contact" / "remote_contact_event_template.json",
            *sorted((PROJECT_ROOT / "Data" / "remote_contact" / "events").glob("*.json")),
        ]
        for path in paths:
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_remote_contact_event(data), [])

    def test_recipient_may_decline_or_delay_required(self) -> None:
        path = PROJECT_ROOT / "Data" / "remote_contact" / "events" / "kira_misses_robert_trip_text.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["privacy_context"]["recipient_may_decline_or_delay"] = False
        errors = validate_remote_contact_event(data)
        self.assertTrue(any("recipient_may_decline_or_delay" in error for error in errors))

    def test_future_video_cannot_claim_camera_now(self) -> None:
        path = PROJECT_ROOT / "Data" / "remote_contact" / "events" / "robert_video_call_future_request.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["privacy_context"]["camera_view_allowed_now"] = True
        errors = validate_remote_contact_event(data)
        self.assertTrue(any("must not claim voice/video/camera" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
