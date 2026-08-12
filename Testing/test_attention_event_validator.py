import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from validate_attention_event import validate_attention_event  # noqa: E402


class AttentionEventValidatorTests(unittest.TestCase):
    def test_attention_event_examples_validate(self) -> None:
        paths = [
            PROJECT_ROOT / "Data" / "attention" / "attention_event_template.json",
            *sorted((PROJECT_ROOT / "Data" / "attention" / "events").glob("*.json")),
        ]
        for path in paths:
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_attention_event(data), [])

    def test_private_media_cannot_default_to_questioning(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "attention" / "events" / "private_media_kira_silence.example.json").read_text(encoding="utf-8"))
        data["recommended_action"] = "ask_soft_clarifying_question"
        errors = validate_attention_event(data)
        self.assertTrue(any("adult_or_private_media should not default" in error for error in errors))

    def test_other_person_blocks_teasing(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "attention" / "events" / "unknown_voice_reserve_response.example.json").read_text(encoding="utf-8"))
        data["privacy_context"]["teasing_allowed"] = True
        errors = validate_attention_event(data)
        self.assertTrue(any("teasing_allowed must be false" in error for error in errors))

    def test_unspoken_feeling_does_not_disclose_to_other_ai_by_default(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "attention" / "events" / "lisa_unspoken_feeling_private_media_notice.example.json").read_text(encoding="utf-8"))
        data["privacy_context"]["should_disclose_to_other_ai"] = True
        errors = validate_attention_event(data)
        self.assertTrue(any("should not disclose to the other AI" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
