from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools import kira_world_shell_server as shell


class KiraSpokenMetaCleanupTests(unittest.TestCase):
    def test_exact_july_17_process_parenthetical_is_not_public_speech(self) -> None:
        raw = (
            "I'm feeling pretty drained today, actually. I think it's because I was up late "
            "thinking about our conversation the other night. It still feels heavy on my mind. "
            "(The above reply is a fresh attempt at responding to you in a natural and human way, "
            "taking into account the given context and guidelines.)"
        )
        cleaned = shell._clean_kira_world_reply("How are you", raw)
        self.assertEqual(
            cleaned,
            "I'm feeling pretty drained today, actually. I think it's because I was up late "
            "thinking about our conversation the other night. It still feels heavy on my mind.",
        )
        self.assertNotIn("guidelines", cleaned.lower())
        self.assertNotIn("above reply", cleaned.lower())

    def test_natural_parenthetical_and_addressed_name_are_preserved(self) -> None:
        raw = "Robert, I want to stay here for a while (I really mean that)."
        self.assertEqual(shell._clean_kira_world_reply("Are you okay?", raw), raw)
        spoken, audit = shell._live_spoken_only_payload(raw)
        self.assertEqual(spoken, raw)
        self.assertTrue(audit["privacy_safe_for_speech"])
        self.assertTrue(audit["dialogue_names_spoken"])

    def test_bare_process_sentence_is_removed_at_voice_boundary(self) -> None:
        raw = (
            "I feel tired, but I'm glad you're here. "
            "This response takes into account the given context and guidelines."
        )
        spoken, audit = shell._live_spoken_only_payload(raw)
        self.assertEqual(spoken, "I feel tired, but I'm glad you're here.")
        self.assertTrue(audit["privacy_safe_for_speech"])

    def test_process_only_output_fails_empty_without_canned_public_speech(self) -> None:
        raw = "(The above response is a fresh attempt based on the given context and guidelines.)"
        cleaned = shell._clean_kira_world_reply("How are you?", raw)
        self.assertEqual(cleaned, "")
        self.assertNotIn("guidelines", cleaned.lower())

    def test_malformed_inline_private_channels_are_cut_from_public_words(self) -> None:
        raw = (
            "I would rather rest here, Robert. PRIVATE_MIND: I am afraid to explain why. "
            "TRUTH_FLAGS: location uncertain"
        )
        cleaned = shell._clean_kira_world_reply("What do you want?", raw)
        self.assertEqual(cleaned, "I would rather rest here, Robert.")
        spoken, audit = shell._live_spoken_only_payload(raw)
        self.assertEqual(spoken, cleaned)
        self.assertTrue(audit["privacy_safe_for_speech"])

    def test_parenthesized_private_note_is_removed(self) -> None:
        raw = "I'm okay. (Private mind: I do not believe that yet.)"
        self.assertEqual(shell._clean_kira_world_reply("How are you?", raw), "I'm okay.")

    def test_old_log_meta_is_not_seeded_back_into_model_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log = Path(tmpdir) / "chat.jsonl"
            entries = [
                {"speaker": "Robert", "to": "kira", "text": "How are you?"},
                {
                    "speaker": "Kira",
                    "speaker_id": "kira",
                    "to": "Robert",
                    "text": "I'm tired. (The above reply is a fresh attempt using the given context and guidelines.)",
                },
            ]
            log.write_text("\n".join(json.dumps(item) for item in entries), encoding="utf-8")
            loop = SimpleNamespace(conversation_history=[])
            with patch.object(shell, "CHAT_LOG", log):
                count = shell._seed_kira_public_history(loop)
        self.assertEqual(count, 1)
        self.assertEqual(loop.conversation_history[-1]["content"], "I'm tired.")

    def test_clean_public_reply_replaces_raw_short_term_history(self) -> None:
        loop = SimpleNamespace(
            conversation_history=[
                {"role": "user", "content": "How are you?"},
                {"role": "assistant", "content": "Public words. (This reply follows the given guidelines.)"},
            ]
        )
        shell._replace_last_kira_public_history(loop, "Public words.")
        self.assertEqual(loop.conversation_history[-1]["content"], "Public words.")

    def test_prompts_explicitly_require_public_words_only(self) -> None:
        prompt = shell._kira_world_core_prompt("How are you?", "home", {})
        self.assertIn("PUBLIC SPEECH OUTPUT CONTRACT", prompt)
        self.assertIn("Private thoughts and body truth", prompt)
        source = (shell.ROOT / "Core" / "conversation_loop.py").read_text(encoding="utf-8")
        self.assertIn("Output only the exact public words you choose to say aloud", source)


if __name__ == "__main__":
    unittest.main()
