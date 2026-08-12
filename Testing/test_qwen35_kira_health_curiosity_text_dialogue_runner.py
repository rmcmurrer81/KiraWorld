from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools/run_qwen35_kira_health_curiosity_text_dialogue.py"


class Qwen35KiraHealthCuriosityTextDialogueRunnerTest(unittest.TestCase):
    def test_single_generation_eval_flag_is_set_before_loop_import(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        flag = 'os.environ["KIRA_QWEN_SINGLE_GENERATION_EVAL_ACTIVE"] = "1"'
        imported = "from conversation_loop import ConversationLoop"
        self.assertIn(flag, source)
        self.assertIn(imported, source)
        self.assertLess(source.index(flag), source.index(imported))

    def test_evidence_records_every_call_and_end_to_end_time(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        for required in (
            '"model_call_count": len(model_calls)',
            '"model_call_wall_seconds": call_wall_seconds',
            '"model_call_wall_seconds_sum": round(sum(call_wall_seconds), 6)',
            '"turn_end_to_end_wall_seconds": round(turn_wall_seconds, 6)',
            '"single_generation_required": True',
            '"single_generation_passed": single_generation_passed',
        ):
            self.assertIn(required, source)

    def test_success_requires_exactly_one_real_generation(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn("len(model_calls) == 1", source)
        self.assertIn(
            'first_call.get("single_generation_per_turn_required") is True',
            source,
        )
        self.assertIn(
            'first_call.get("generation_request_count") == 1',
            source,
        )
        self.assertIn("return 0 if single_generation_passed else 1", source)


if __name__ == "__main__":
    unittest.main()
