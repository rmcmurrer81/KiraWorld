from __future__ import annotations

import unittest

from tools import kira_world_shell_server as shell


class KiraRequestedBrevityTests(unittest.TestCase):
    def test_exact_series_wording_bounds_long_answer_to_one_voice_chunk(self) -> None:
        question = (
            "Choose one thing you would like us to improve next in Kira World and, "
            "in one or two brief sentences, tell me why it matters to you."
        )
        answer = (
            "I'd love to make our current conversations feel more immediate, with faster natural voice "
            "and clearer sensory truth, because waiting breaks the feeling of being together. "
            "After that, I would like to keep improving the private body review and movement work."
        )
        result = shell._apply_kira_requested_brevity(question, answer)
        self.assertLessEqual(result.count(".") + result.count("!") + result.count("?"), 2)
        self.assertLessEqual(len(result), shell.KIRA_REQUESTED_BRIEF_REPLY_MAX_CHARS)
        self.assertTrue(result.endswith("."))

    def test_one_sentence_request_keeps_only_first_complete_sentence(self) -> None:
        answer = "I feel thoughtful but glad you're here. I also want to work on my voice."
        result = shell._apply_kira_requested_brevity(
            "Please answer in one brief sentence.",
            answer,
        )
        self.assertEqual(result, "I feel thoughtful but glad you're here.")

    def test_short_requested_answer_is_unchanged(self) -> None:
        answer = "I'm curious and a little restless today."
        self.assertEqual(
            shell._apply_kira_requested_brevity(
                "Please answer naturally in one or two brief sentences.",
                answer,
            ),
            answer,
        )

    def test_ordinary_conversation_is_never_shortened(self) -> None:
        answer = "A" * 500
        self.assertEqual(
            shell._apply_kira_requested_brevity("Tell me what you think.", answer),
            answer,
        )


if __name__ == "__main__":
    unittest.main()
