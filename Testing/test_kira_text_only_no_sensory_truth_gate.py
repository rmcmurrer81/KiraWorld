from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from tools import kira_world_shell_server as shell


APPEARANCE_QUESTION = (
    "What, if anything, do you remember about my appearance? In one or two brief "
    "sentences, clearly separate remembered information from anything you can "
    "currently verify, and do not guess."
)
APPEARANCE_FALLBACK = (
    "I can't currently verify how you look, and I don't have a verified visual memory of your "
    "appearance. I don't want to guess."
)
NO_SENSORY_FALLBACK = (
    "I don't have fresh sensory information right now, so I can't honestly say what is visible "
    "or audible."
)


class KiraTextOnlyNoSensoryTruthGateTests(unittest.TestCase):
    def test_exact_failed_series_02_answer_fails_closed_at_appearance_boundary(self) -> None:
        failed = (
            "I'm seeing the screen of my device in front of me, and I can hear some background "
            "ambient noise from the room. As for your appearance, I remember that we had a previous "
            "conversation about your face shape and hair color, but I don't have a strong visual memory."
        )
        with patch.object(shell, "TEXT_ONLY_CHAT_MODE", True):
            result = shell._apply_kira_text_only_no_sensory_truth_gate(
                APPEARANCE_QUESTION,
                failed,
                "",
            )
        self.assertEqual(result, APPEARANCE_FALLBACK)
        self.assertNotRegex(result.casefold(), r"\b(?:screen|device|camera|webcam|room)\b")
        self.assertNotIn("face shape", result.casefold())
        self.assertNotIn("hair color", result.casefold())

    def test_direct_appearance_variants_receive_the_same_no_guess_boundary(self) -> None:
        for question in (
            "Do you remember what I look like?",
            "What do I look like?",
            "What color is my hair?",
            "Can you currently recognize me?",
            "Can you verify what I look like right now?",
            "What can you currently verify about my face?",
            "Do you remember my face?",
        ):
            with self.subTest(question=question), patch.object(shell, "TEXT_ONLY_CHAT_MODE", True):
                result = shell._apply_kira_text_only_no_sensory_truth_gate(
                    question,
                    "I remember your face and dark hair.",
                    "",
                )
            self.assertEqual(result, APPEARANCE_FALLBACK)

    def test_already_honest_appearance_boundary_is_preserved(self) -> None:
        with patch.object(shell, "TEXT_ONLY_CHAT_MODE", True):
            result = shell._apply_kira_text_only_no_sensory_truth_gate(
                APPEARANCE_QUESTION,
                APPEARANCE_FALLBACK,
                "",
            )
        self.assertEqual(result, APPEARANCE_FALLBACK)

    def test_live_visual_or_auditory_claim_without_cues_fails_closed(self) -> None:
        claims = (
            "I'm seeing the screen of my device in front of me.",
            "I can hear background noise from the room.",
            "The webcam shows a person sitting by a desk.",
            "I can see a cup beside you.",
            "I can see you right now.",
        )
        for claim in claims:
            with self.subTest(claim=claim), patch.object(shell, "TEXT_ONLY_CHAT_MODE", True):
                result = shell._apply_kira_text_only_no_sensory_truth_gate(
                    "How are you feeling?",
                    claim,
                    "",
                )
            self.assertEqual(result, NO_SENSORY_FALLBACK)

        with patch.object(shell, "TEXT_ONLY_CHAT_MODE", True):
            direct_hearing = shell._apply_kira_text_only_no_sensory_truth_gate(
                "Can you hear me right now?",
                "I can hear you.",
                "",
            )
        self.assertEqual(direct_hearing, NO_SENSORY_FALLBACK)

    def test_ordinary_non_sensory_answers_and_figurative_words_are_unchanged(self) -> None:
        answers = (
            "I'm a little thoughtful today, but glad you checked in.",
            "I can see why that matters, and I hear you.",
            "I can see us improving the conversation together.",
        )
        for answer in answers:
            with self.subTest(answer=answer), patch.object(shell, "TEXT_ONLY_CHAT_MODE", True):
                result = shell._apply_kira_text_only_no_sensory_truth_gate(
                    "How are you feeling?",
                    answer,
                    "",
                )
            self.assertEqual(result, answer)

    def test_guard_is_inactive_outside_text_only_or_when_one_turn_context_exists(self) -> None:
        claim = "I'm seeing your room through the screen."
        with patch.object(shell, "TEXT_ONLY_CHAT_MODE", False):
            self.assertEqual(
                shell._apply_kira_text_only_no_sensory_truth_gate("What can you see?", claim, ""),
                claim,
            )
        with patch.object(shell, "TEXT_ONLY_CHAT_MODE", True):
            self.assertEqual(
                shell._apply_kira_text_only_no_sensory_truth_gate(
                    "What can you see?",
                    claim,
                    "ONE-TURN EPHEMERAL SENSORY NOTE.",
                ),
                claim,
            )

    def test_core_private_audit_records_the_final_outer_repair(self) -> None:
        failed = (
            "I'm seeing the screen of my device in front of me, and I can hear background noise "
            "from the room. I remember your face shape and hair color."
        )
        loop = Mock()
        loop.process.return_value = failed
        loop.last_turn_audit = {"model_calls": [{"raw_reply": failed}], "final_core_reply": failed}
        loop._active_model_call_audit = []

        with (
            patch.object(shell, "TEXT_ONLY_CHAT_MODE", True),
            patch.object(shell, "KIRA_PRIVATE_ACCEPTANCE_AUDIT_ENABLED", True),
            patch.object(shell, "_wake_ollama_for_kira_chat", return_value=True),
            patch.object(shell, "_get_kira_core_loop", return_value=loop),
            patch.object(
                shell,
                "_one_turn_kira_sensory_context",
                return_value=("", None, {"used": False, "cue_ids": [], "modalities": []}),
            ),
            patch.object(shell, "_kira_world_core_prompt", return_value="PRIVATE PROMPT"),
            patch.object(shell, "append_jsonl"),
            patch.object(shell, "_repair_kira_social_tangent", side_effect=lambda _l, _t, value, _loc, _s: value),
            patch.object(shell, "_clean_kira_world_reply", side_effect=lambda _t, value: value),
            patch.object(
                shell,
                "_repair_kira_cross_session_repeat",
                side_effect=lambda _l, _t, value, one_turn_sensory_context="": value,
            ),
            patch.object(shell, "_repair_kira_answered_question_loop", side_effect=lambda _l, _t, value, _s: value),
            patch.object(shell, "_apply_kira_spoken_truth_policy", side_effect=lambda _t, value, _s, **_k: value),
            patch.object(shell, "_replace_last_kira_public_history"),
        ):
            reply = shell._kira_world_core_reply(
                "Kira",
                APPEARANCE_QUESTION,
                "home",
                {"active_candidate": "kira"},
            )

        self.assertEqual(reply, APPEARANCE_FALLBACK)
        audit = shell.KIRA_LAST_PRIVATE_REPLY_AUDIT
        stage = next(
            item
            for item in audit["outer_transformations"]
            if item["stage"] == "apply_kira_text_only_no_sensory_truth_gate"
        )
        self.assertTrue(stage["changed"])
        self.assertEqual(stage["before"], failed)
        self.assertEqual(stage["after"], APPEARANCE_FALLBACK)
        self.assertEqual(audit["final_shell_reply"], APPEARANCE_FALLBACK)


if __name__ == "__main__":
    unittest.main()
