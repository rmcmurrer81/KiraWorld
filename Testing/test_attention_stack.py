import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(CORE_ROOT))
sys.path.insert(0, str(TOOLS_ROOT))

from attention_decision_engine import build_attention_event  # noqa: E402
from attention_state_manager import AttentionStateManager, validate_attention_state  # noqa: E402
from source_confidence_model import classify_source  # noqa: E402
from validate_attention_event import validate_attention_event  # noqa: E402


class AttentionStackTests(unittest.TestCase):
    def test_source_confidence_classifies_direct_robert_speech(self) -> None:
        result = classify_source(
            {
                "addressed_ai": True,
                "robert_voice_match": True,
                "confidence_hint": "medium",
            }
        )
        self.assertEqual(result["source_label"], "robert_direct_speech")
        self.assertEqual(result["category_guess"], "direct_request")
        self.assertEqual(result["source_confidence"], "high")

    def test_source_confidence_keeps_phone_media_separate_from_robert_speech(self) -> None:
        result = classify_source(
            {
                "phone_audio_detected": True,
                "music_detected": True,
                "confidence_hint": "medium",
            }
        )
        self.assertEqual(result["source_label"], "robert_phone_media")
        self.assertEqual(result["category_guess"], "music")
        self.assertEqual(result["source_confidence"], "medium")

    def test_private_media_with_unspoken_feelings_becomes_private_reflection(self) -> None:
        event = build_attention_event(
            owner="lisa",
            source_label="robert_phone_media",
            source_confidence="medium",
            category_guess="adult_or_private_media",
            relationship_stage="unspoken_romantic_tension",
            unspoken_feeling_possible=True,
            mutual_intimate_context_established=False,
        )
        self.assertEqual(event["recommended_action"], "private_reflection_only")
        self.assertFalse(event["privacy_context"]["teasing_allowed"])
        self.assertFalse(event["privacy_context"]["should_disclose_to_other_ai"])
        self.assertEqual(validate_attention_event(event), [])

    def test_private_media_without_mutual_context_gives_privacy(self) -> None:
        event = build_attention_event(
            owner="kira",
            source_label="robert_phone_media",
            source_confidence="medium",
            category_guess="adult_or_private_media",
            relationship_stage="friendship",
        )
        self.assertEqual(event["recommended_action"], "stay_quiet_give_privacy")
        self.assertFalse(event["privacy_context"]["teasing_allowed"])
        self.assertEqual(validate_attention_event(event), [])

    def test_other_person_present_reserves_response(self) -> None:
        event = build_attention_event(
            owner="kira",
            source_label="visitor_voice",
            source_confidence="medium",
            category_guess="video_dialogue",
            other_person_present=True,
        )
        self.assertEqual(event["recommended_action"], "reserve_response_due_to_other_person")
        self.assertEqual(validate_attention_event(event), [])

    def test_attention_state_file_validates(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "attention" / "attention_state.json").read_text(encoding="utf-8"))
        for state in data:
            with self.subTest(owner=state["owner"]):
                self.assertEqual(validate_attention_state(state), [])

    def test_attention_state_manager_blocks_direct_response_while_private(self) -> None:
        with TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "attention_state.json"
            state_file.write_text((PROJECT_ROOT / "Data" / "attention" / "attention_state.json").read_text(encoding="utf-8"), encoding="utf-8")
            manager = AttentionStateManager(state_file)
            manager.set_focus(
                "kira",
                "private_activity",
                activity_type="reading",
                activity_summary="Kira is privately reading to cool off.",
                privacy_level="private",
                interruptibility="low",
            )
            self.assertFalse(manager.should_respond_to_direct_speech("kira", "high"))

    def test_attention_state_manager_allows_direct_response_when_focused(self) -> None:
        with TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "attention_state.json"
            manager = AttentionStateManager(state_file)
            manager.set_focus("kira", "user", activity_type="chat", privacy_level="personal")
            self.assertTrue(manager.should_respond_to_direct_speech("kira", "high"))


if __name__ == "__main__":
    unittest.main()
