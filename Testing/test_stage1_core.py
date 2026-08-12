import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
sys.path.insert(0, str(CORE_ROOT))

from conversation_loop import ConversationLoop  # noqa: E402


class Stage1CoreTests(unittest.TestCase):
    def test_conversation_log_is_not_promoted_to_memory(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")

                before = loop.memory.count_memories(owner="kira")
                response = loop.process("Do you remember our first trip?")
                after = loop.memory.count_memories(owner="kira")

                self.assertEqual(before, 0)
                self.assertEqual(after, 0)
                self.assertIn("don't have a stored memory", response)

                log_path = Path("Data/logs/conversation_log.jsonl")
                self.assertTrue(log_path.exists())
                entry = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
                self.assertFalse(entry["trusted_memory"])
                self.assertEqual(entry["promotion_status"], "not_promoted")
            finally:
                os.chdir(old_cwd)

    def test_explicit_memory_promotion_is_retrievable(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                loop.promote_exchange_to_memory(
                    summary="Robert prefers careful staged builds.",
                    detail="Robert wants Kira built in stable stages before advanced features.",
                    tags=["build_plan", "stability"],
                    importance_weight="high",
                    importance_score=0.9,
                )

                memories = loop.memory.retrieve_relevant_memories(
                    "careful staged builds",
                    owner="kira",
                )

                self.assertEqual(len(memories), 1)
                self.assertEqual(memories[0]["owner"], "kira")
                self.assertIn("explicitly_promoted", memories[0]["tags"])
            finally:
                os.chdir(old_cwd)

    def test_decision_log_is_not_memory(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)
                loop = ConversationLoop(speaker="Kira")
                before = loop.memory.count_memories(owner="kira")
                entry = loop.log_decision(
                    decision_type="privacy",
                    summary="Kira chose not to disclose a private feeling.",
                    reason="Sharing too early could affect the relationship.",
                    outcome="The feeling stayed private.",
                    privacy_impact="sealed_details",
                    visibility="participants_only",
                )
                after = loop.memory.count_memories(owner="kira")

                self.assertEqual(before, 0)
                self.assertEqual(after, 0)
                self.assertTrue(entry["decision_id"].startswith("decision_"))
                self.assertTrue(Path("Data/logs/decision_log.jsonl").exists())
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
