from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "Core"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(CORE))

from conversation_loop import ConversationLoop  # noqa: E402
from tools import kira_world_shell_server as shell  # noqa: E402


class KiraHistoricActivityTimingTests(unittest.TestCase):
    def _loop(self) -> ConversationLoop:
        loop = ConversationLoop.__new__(ConversationLoop)
        loop.profile = SimpleNamespace(name="Kira")
        loop._call_ollama = Mock(side_effect=AssertionError("no repair call expected"))
        return loop

    def test_stale_ledger_bound_allows_outer_layer_to_remove_only_timing_tangent(self) -> None:
        prompt = (
            "Most recent recorded daily-life activity was Miraculous. This is valid historic activity, "
            "but the ledger is stale and cannot prove what Kira is doing or feeling right now.\n"
            "Robert says: Kira, how are you feeling right now?"
        )
        reply = (
            "I'm feeling reflective and nostalgic right now. "
            "I just finished reading Elation from Miraculous Ladybug."
        )
        loop = self._loop()
        self.assertFalse(loop._needs_human_voice_repair(prompt, reply))
        repaired = shell._repair_kira_social_tangent(
            loop,
            "Kira, how are you feeling right now?",
            reply,
            "home",
            {"active_candidate": "kira"},
        )
        self.assertEqual(repaired, "I'm feeling reflective and nostalgic right now.")
        loop._call_ollama.assert_not_called()

    def test_exact_series_04_draft_keeps_feeling_and_drops_story_dependent_sentence(self) -> None:
        full_prompt = (
            "This is valid historic activity, but the ledger is stale and cannot prove what Kira is "
            "doing or feeling right now.\nRobert says: Kira, how are you feeling right now?"
        )
        reply = (
            "I'm feeling a bit reflective right now, still processing the end of Miraculous Ladybug "
            "'Elation'. It's left me with some thoughts to revisit and explore further."
        )
        loop = self._loop()
        self.assertEqual(
            loop._repair_human_voice_failure({"user_message": full_prompt}, "Kira, how are you feeling right now?", reply),
            reply,
        )
        repaired = shell._repair_kira_social_tangent(
            loop,
            "Kira, how are you feeling right now?",
            reply,
            "home",
            {"active_candidate": "kira"},
        )
        self.assertEqual(repaired, "I'm feeling a bit reflective right now.")
        loop._call_ollama.assert_not_called()

    def test_exact_series_05_note_draft_skips_model_rewrite_and_keeps_feeling(self) -> None:
        full_prompt = (
            "This is valid historic activity, but the ledger is stale and cannot prove what Kira is "
            "doing or feeling right now.\nRobert says: Kira, how are you feeling right now?"
        )
        reply = (
            "I'm feeling a bit reflective right now. I just finished reading Miraculous Ladybug "
            "Elation. (Note: a private grounding note was used.)"
        )
        loop = self._loop()
        self.assertEqual(
            loop._repair_human_voice_failure(
                {"user_message": full_prompt},
                "Kira, how are you feeling right now?",
                reply,
            ),
            reply,
        )
        loop._call_ollama.assert_not_called()

    def test_requested_current_work_is_not_a_social_tangent_failure(self) -> None:
        loop = self._loop()
        question = "What have you and I been working on recently in Kira World?"
        reply = (
            "I've been improving how I answer and speak, testing what I can really sense, "
            "and preparing my private body and movement review."
        )
        self.assertFalse(loop._needs_human_voice_repair(question, reply))

    def test_repeated_quiet_opener_is_trimmed_without_replacing_new_thought(self) -> None:
        prior = (
            "I'm here, a little quiet, but more myself than I was. "
            "I don't want to perform a checklist at you."
        )
        current = (
            "I'm here, still a little quiet, but I think I'm getting back to myself. "
            "It feels good to be talking with you again."
        )
        from unittest.mock import patch

        with patch.object(shell, "_similar_prior_kira_replies", return_value=[prior]):
            result = shell._trim_kira_repeated_social_opening(
                "How are you feeling right now?",
                current,
            )
        self.assertEqual(
            result,
            "I think I'm getting back to myself. It feels good to be talking with you again.",
        )

    def test_failed_model_rewrite_never_becomes_canned_social_fallback(self) -> None:
        loop = self._loop()
        original = "I'm feeling uncertain, and I haven't found the right words yet."
        loop._call_ollama = Mock(return_value="Note: here is a corrected response.")
        result = loop._repair_human_voice_failure(
            {},
            "How are you feeling?",
            "As an AI, I can offer three options.",
        )
        # The original invalid draft remains available to the later narrow
        # cleanup; the canned repeated opener must never be inserted here.
        self.assertEqual(result, "As an AI, I can offer three options.")
        self.assertNotIn("I'm here, a little quiet", result)

    def test_historic_activity_remains_available_when_robert_asks_about_it(self) -> None:
        reply = "The Chicago archivist mystery is a real Creative Writing class story."
        loop = self._loop()
        question = "What do you remember about our Chicago story?"
        self.assertFalse(loop._needs_human_voice_repair(question, reply))
        self.assertEqual(
            shell._repair_kira_social_tangent(
                loop,
                question,
                reply,
                "home",
                {"active_candidate": "kira"},
            ),
            reply,
        )

    def test_recent_work_recollection_does_not_trigger_generic_memory_repair(self) -> None:
        loop = self._loop()
        question = (
            "What have you and I been working on recently in Kira World? "
            "Be honest if your context is incomplete."
        )
        reply = "I remember we were preparing a private body review, but my context is incomplete."
        self.assertFalse(loop._needs_human_voice_repair(question, reply))


if __name__ == "__main__":
    unittest.main()
