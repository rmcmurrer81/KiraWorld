import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools import run_kira_life_day as life_day  # noqa: E402


class KiraLifeDayTabletMessageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.args = argparse.Namespace(subject="kira")

    def test_creative_writing_is_linked_into_local_tablet_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with (
                patch.object(life_day, "PROJECT_ROOT", root),
                patch.object(life_day, "call_ollama", return_value="STORY PROGRESS: A choice.\nNEXT STEP: revise."),
            ):
                result = life_day.creative_write_action(self.args, [])

            tablet_path = root / result["tablet_note_path"]
            tablet = json.loads(tablet_path.read_text(encoding="utf-8"))
            self.assertEqual(tablet["kind"], "creative_writing")
            self.assertFalse(tablet["tablet_state"]["physical_tablet_use_proven"])
            self.assertTrue(tablet["linked_artifact"].endswith(".json"))
            self.assertTrue(tablet["memory_policy"]["creative_work_not_lived_memory"])
            self.assertFalse(tablet["authorship_provenance"]["authorship_claim_allowed"])
            self.assertEqual("local_model_for_kira", tablet["author"])
            self.assertEqual("kira", tablet["authorship_provenance"]["claimed_author"])

    def test_life_message_defers_audio_until_robert_requests_playback(self) -> None:
        payload = json.dumps(
            {
                "message": "I left you a short thought.",
                "reason": "I wanted to share it later.",
                "urgency": "normal",
                "privacy": "shareable",
            }
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with (
                patch.object(life_day, "PROJECT_ROOT", root),
                patch.object(life_day, "call_ollama", return_value=payload),
            ):
                result = life_day.leave_message_for_robert_action(
                    self.args,
                    {"run_id": "test_run", "cycles": []},
                    {"reason": "share later"},
                )
                second = life_day.leave_message_for_robert_action(
                    self.args,
                    {"run_id": "test_run", "cycles": []},
                    {"reason": "share later"},
                )

            message_path = root / result["message_path"]
            message = json.loads(message_path.read_text(encoding="utf-8"))
            self.assertEqual(message["status"], "unread")
            self.assertEqual(message["message"]["message"], "I left you a short thought.")
            self.assertEqual(result["message_audio_status"], "pending_user_prepare")
            self.assertEqual(result["message_audio_reason"], "deferred_until_robert_clicks_play_audio_draft")
            self.assertEqual(result["message_audio_path"], "")
            self.assertNotIn("audio", message)
            self.assertNotEqual(result["message_path"], second["message_path"])
            self.assertFalse(message["authorship_provenance"]["authorship_claim_allowed"])
            self.assertEqual("local_model_for_kira", message["sender"])
            self.assertTrue(message["kind"].startswith("unapproved_voice_message_draft"))

    def test_model_failure_does_not_fabricate_kira_writing_or_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with (
                patch.object(life_day, "PROJECT_ROOT", root),
                patch.object(life_day, "call_ollama", side_effect=RuntimeError("offline")),
            ):
                creative = life_day.creative_write_action(self.args, [])
                message = life_day.leave_message_for_robert_action(
                    self.args,
                    {"run_id": "test_run", "cycles": []},
                    {"reason": "share later"},
                )
            self.assertFalse(creative["generation_succeeded"])
            self.assertEqual("", creative["tablet_note_path"])
            self.assertEqual("", message["message_path"])
            self.assertIn("generation_failed_no_subject_message", message["message_audio_reason"])


if __name__ == "__main__":
    unittest.main()
