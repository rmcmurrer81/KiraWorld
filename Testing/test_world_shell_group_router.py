from __future__ import annotations

import unittest
from contextlib import contextmanager
from unittest.mock import Mock

from Core.world_shell_group_router import (
    GroupTurnValidationError,
    run_sequential_group_turn,
)


class WorldShellGroupRouterTests(unittest.TestCase):
    def test_locked_replies_and_voice_callbacks_are_strictly_sequential(self) -> None:
        events: list[tuple[str, str]] = []

        @contextmanager
        def lock_for(candidate_id: str):
            events.append(("lock_enter", candidate_id))
            try:
                yield
            finally:
                events.append(("lock_exit", candidate_id))

        def reply_callback(participant: dict[str, object], text: str) -> str:
            candidate_id = str(participant["candidate_id"])
            events.append(("reply", candidate_id))
            return f"{participant['label']}: {text}"

        def voice_callback(participant: dict[str, object], reply: object) -> dict[str, object]:
            candidate_id = str(participant["candidate_id"])
            events.append(("voice", candidate_id))
            return {"candidate_id": candidate_id, "spoken": reply}

        result = run_sequential_group_turn(
            [
                {"candidate_id": "kira", "label": "Kira"},
                {"candidate_id": "lisa", "label": "Lisa"},
                {"candidate_id": "marinette", "label": "Marinette"},
            ],
            "  How is everyone?  ",
            max_participants=4,
            lock_for=lock_for,
            reply_callback=reply_callback,
            voice_callback=voice_callback,
        )

        self.assertEqual(
            events,
            [
                ("lock_enter", "kira"),
                ("reply", "kira"),
                ("lock_exit", "kira"),
                ("voice", "kira"),
                ("lock_enter", "lisa"),
                ("reply", "lisa"),
                ("lock_exit", "lisa"),
                ("voice", "lisa"),
                ("lock_enter", "marinette"),
                ("reply", "marinette"),
                ("lock_exit", "marinette"),
                ("voice", "marinette"),
            ],
        )
        self.assertEqual(result["participant_order"], ["kira", "lisa", "marinette"])
        self.assertEqual(result["reply_order"], ["kira", "lisa", "marinette"])
        self.assertEqual(result["voice_order"], ["kira", "lisa", "marinette"])
        self.assertEqual(result["replies"][0]["result"], "Kira: How is everyone?")
        self.assertEqual(result["voice"]["items"][1]["candidate_id"], "lisa")
        self.assertFalse(result["routing"]["parallel_reply_generation"])
        self.assertFalse(result["voice"]["parallel_callback_invocation"])

    def test_duplicate_candidates_are_rejected_before_callbacks(self) -> None:
        lock_for = Mock()
        reply_callback = Mock()
        voice_callback = Mock()

        with self.assertRaises(GroupTurnValidationError) as raised:
            run_sequential_group_turn(
                [
                    {"candidate_id": "kira", "label": "Kira"},
                    {"candidate_id": "kira", "label": "Kira again"},
                ],
                "Hello",
                max_participants=4,
                lock_for=lock_for,
                reply_callback=reply_callback,
                voice_callback=voice_callback,
            )

        self.assertEqual(raised.exception.code, "duplicate_candidate_id")
        lock_for.assert_not_called()
        reply_callback.assert_not_called()
        voice_callback.assert_not_called()

    def test_empty_or_over_capacity_participant_sets_are_rejected(self) -> None:
        no_op = Mock()
        cases = [
            ([], 4, "empty_participants"),
            (
                [
                    {"candidate_id": "kira"},
                    {"candidate_id": "lisa"},
                    {"candidate_id": "marinette"},
                ],
                2,
                "participant_capacity_exceeded",
            ),
        ]

        for participants, capacity, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(GroupTurnValidationError) as raised:
                    run_sequential_group_turn(
                        participants,
                        "Hello",
                        max_participants=capacity,
                        lock_for=no_op,
                        reply_callback=no_op,
                        voice_callback=no_op,
                    )
                self.assertEqual(raised.exception.code, expected_code)

        no_op.assert_not_called()

    def test_blank_text_and_candidate_id_are_rejected_before_callbacks(self) -> None:
        no_op = Mock()

        with self.assertRaises(GroupTurnValidationError) as blank_text:
            run_sequential_group_turn(
                [{"candidate_id": "kira"}],
                "   ",
                max_participants=1,
                lock_for=no_op,
                reply_callback=no_op,
                voice_callback=no_op,
            )
        with self.assertRaises(GroupTurnValidationError) as blank_candidate:
            run_sequential_group_turn(
                [{"candidate_id": "   "}],
                "Hello",
                max_participants=1,
                lock_for=no_op,
                reply_callback=no_op,
                voice_callback=no_op,
            )

        self.assertEqual(blank_text.exception.code, "empty_text")
        self.assertEqual(blank_candidate.exception.code, "empty_candidate_id")
        no_op.assert_not_called()

    def test_reply_failure_releases_current_lock_and_stops_later_participants(self) -> None:
        events: list[tuple[str, str]] = []

        @contextmanager
        def lock_for(candidate_id: str):
            events.append(("lock_enter", candidate_id))
            try:
                yield
            finally:
                events.append(("lock_exit", candidate_id))

        def reply_callback(participant: dict[str, object], _text: str) -> str:
            candidate_id = str(participant["candidate_id"])
            events.append(("reply", candidate_id))
            raise RuntimeError("model unavailable")

        voice_callback = Mock()

        with self.assertRaisesRegex(RuntimeError, "model unavailable"):
            run_sequential_group_turn(
                [{"candidate_id": "kira"}, {"candidate_id": "lisa"}],
                "Hello",
                max_participants=2,
                lock_for=lock_for,
                reply_callback=reply_callback,
                voice_callback=voice_callback,
            )

        self.assertEqual(
            events,
            [
                ("lock_enter", "kira"),
                ("reply", "kira"),
                ("lock_exit", "kira"),
            ],
        )
        voice_callback.assert_not_called()

    def test_voice_failure_happens_after_unlock_and_stops_later_participants(self) -> None:
        events: list[tuple[str, str]] = []

        @contextmanager
        def lock_for(candidate_id: str):
            events.append(("lock_enter", candidate_id))
            try:
                yield
            finally:
                events.append(("lock_exit", candidate_id))

        def reply_callback(participant: dict[str, object], _text: str) -> str:
            candidate_id = str(participant["candidate_id"])
            events.append(("reply", candidate_id))
            return "ready"

        def voice_callback(participant: dict[str, object], _reply: object) -> object:
            candidate_id = str(participant["candidate_id"])
            events.append(("voice", candidate_id))
            raise RuntimeError("voice stopped")

        with self.assertRaisesRegex(RuntimeError, "voice stopped"):
            run_sequential_group_turn(
                [{"candidate_id": "kira"}, {"candidate_id": "lisa"}],
                "Hello",
                max_participants=2,
                lock_for=lock_for,
                reply_callback=reply_callback,
                voice_callback=voice_callback,
            )

        self.assertEqual(
            events,
            [
                ("lock_enter", "kira"),
                ("reply", "kira"),
                ("lock_exit", "kira"),
                ("voice", "kira"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
