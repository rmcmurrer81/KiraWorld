import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools import kira_world_shell_server as shell  # noqa: E402
from Core.dialogue_tts import spoken_words  # noqa: E402


class KiraWorldShellMessageTests(unittest.TestCase):
    def test_shell_has_flashing_inbox_and_browser_audio_read_flow(self) -> None:
        state = {**shell.DEFAULT_STATE, "location": "home"}
        inbox = {
            "total": 1,
            "unread": 1,
            "has_unread": True,
            "latest_created_at": "2026-07-15T00:00:00+00:00",
            "messages": [],
        }
        with (
            patch.object(shell, "load_state", return_value=state),
            patch.object(shell, "voice_message_inbox", return_value=inbox),
            patch.object(shell, "tablet_workspace_summary", return_value={"notes": 2, "pending_requests": 1}),
        ):
            html = shell.html_shell().decode("utf-8")

        self.assertIn("@keyframes unreadPulse", html)
        self.assertIn('id="messageButton"', html)
        self.assertIn("/api/messages/prepare", html)
        self.assertIn("/api/messages/status", html)
        self.assertIn('new Audio(', html)
        self.assertIn('audio.addEventListener("ended"', html)
        self.assertIn("Saved voice messages and drafts", html)
        self.assertIn("unapproved draft", html)
        self.assertNotIn("Kira's messages to Robert", html)

    def test_tablet_grounding_requires_held_tablet_and_matching_action(self) -> None:
        state = {
            "last_avatar_positions": {
                "kira": {
                    "updated_at": "2026-07-15T00:00:00+00:00",
                    "location": "home",
                    "position": {"x": -20.0, "y": 0.55, "z": 3.0},
                    "action": "creative_write",
                    "activeHeldProp": {
                        "kind": "tablet",
                        "grounded": True,
                        "syntheticPreview": False,
                        "sourcePropId": "one_bedroom_coffee_table_temporary_tablet",
                        "sourceRemovedOrHidden": True,
                        "handContact": {"touching": True, "distance": 0.08},
                    },
                    "activeSkillInteraction": {"id": "home_tablet_creative_write"},
                }
            }
        }
        grounded = shell.tablet_body_grounding(state)
        self.assertTrue(grounded["physical_tablet_use_proven"])

        state["last_avatar_positions"]["kira"]["activeHeldProp"] = None
        not_grounded = shell.tablet_body_grounding(state)
        self.assertFalse(not_grounded["physical_tablet_use_proven"])

    def test_full_reply_setting_never_substitutes_compact_summary(self) -> None:
        text = "First complete sentence. " + ("Every spoken word must remain present. " * 20)
        cfg = SimpleNamespace(engine="chatterbox_tts")
        with patch.object(shell, "SPEAK_FULL_REPLY", True):
            spoken, mode, full_chars = shell.voice_text_for_reply(text, cfg)
        self.assertEqual(spoken, text.strip())
        self.assertEqual(full_chars, len(text.strip()))
        self.assertEqual(mode, "full_reply_chunked")

    def test_live_chatterbox_chunk_cap_preserves_every_word(self) -> None:
        text = "One complete sentence with all its words. " + (
            "The next thought must also survive exact chunking without a cutoff. " * 12
        )
        cfg = SimpleNamespace(engine="chatterbox_tts", max_chars=450)
        with patch.object(shell, "LIVE_WORLD_VOICE_MAX_CHARS", 180):
            limit = shell._live_voice_chunk_limit(cfg)
            chunks = shell._split_for_voice(text, limit)

        self.assertEqual(limit, 180)
        self.assertTrue(all(len(chunk) <= 180 for chunk in chunks))
        self.assertEqual(spoken_words(text), spoken_words(" ".join(chunks)))


if __name__ == "__main__":
    unittest.main()
