import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

import timed_input as timed_input_module  # noqa: E402
from chat_kira import _idle_step  # noqa: E402
from conversation_loop import ConversationLoop  # noqa: E402
from daily_life_manager import DailyLifeManager  # noqa: E402
from idle_rhythm import IdleRhythm  # noqa: E402


class IdleChatBehaviorTests(unittest.TestCase):
    @staticmethod
    def _isolated_loop(root: Path) -> ConversationLoop:
        loop = ConversationLoop(
            speaker="Kira",
            daily_life_state_dir=root / "states",
            conversation_log_file=root / "conversation_log.jsonl",
            decision_log_file=root / "decision_log.jsonl",
            relationship_state_file=root / "relationships.json",
            privacy_session_file=root / "privacy.json",
            attention_state_file=root / "attention.json",
            memory_candidate_dir=root / "memory_candidates",
        )
        loop.daily_life = DailyLifeManager(
            state_dir=root / "states",
            log_dir=root / "daily_life_logs",
            reading_session_dir=root / "reading" / "sessions",
            reading_recommendation_dir=root / "reading",
        )
        return loop

    def test_timed_input_uses_normal_input_off_windows(self) -> None:
        with patch.object(timed_input_module.sys, "platform", "linux"), patch("builtins.input", return_value="hi"):
            text, timed_out = timed_input_module.timed_input("Robert> ", 1)

        self.assertEqual(text, "hi")
        self.assertFalse(timed_out)

    def test_idle_step_advances_daily_life_state(self) -> None:
        with TemporaryDirectory() as tmpdir:
            loop = self._isolated_loop(Path(tmpdir))
            with patch("builtins.print") as mocked_print:
                _idle_step(loop)

            state = loop.daily_life.get_state("kira")
            self.assertNotEqual(state["current_activity"]["activity_type"], "none")
            self.assertTrue(mocked_print.called)

    def test_idle_step_does_not_print_internal_slow_reading_phrase(self) -> None:
        with TemporaryDirectory() as tmpdir:
            loop = self._isolated_loop(Path(tmpdir))
            loop.daily_life.set_state(
                "kira",
                cycle_state="quiet",
                mood="curious",
                intensity=0.35,
                activity_type="reading",
                public_summary="Kira may continue a slow reading session.",
                private_summary="There is already an active slow reading session.",
                source_path="Data/library/language_learning/french/french_grammar_for_dummies.pdf",
            )
            with patch("builtins.print") as mocked_print:
                _idle_step(loop)

            printed = " ".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
            self.assertNotIn("may continue a slow reading session", printed.lower())
            self.assertIn("[idle]", printed)

    def test_idle_rhythm_varies_wait_times(self) -> None:
        rhythm = IdleRhythm(min_seconds=2, max_seconds=20)

        waits = {rhythm.next_wait_seconds() for _ in range(20)}

        self.assertGreater(len(waits), 1)
        self.assertTrue(all(2 <= wait <= 20 for wait in waits))

    def test_idle_rhythm_can_be_fixed_for_testing(self) -> None:
        rhythm = IdleRhythm(min_seconds=3, max_seconds=3)

        waits = [rhythm.next_wait_seconds() for _ in range(5)]

        self.assertEqual(waits, [3, 3, 3, 3, 3])


if __name__ == "__main__":
    unittest.main()
