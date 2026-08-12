import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from create_first_talk_memory_candidate import build_candidate  # noqa: E402
from validate_memory_promotion_candidate import validate_candidate  # noqa: E402


class FirstTalkMemoryCandidateToolTests(unittest.TestCase):
    def test_builds_valid_draft_candidate(self) -> None:
        candidate = build_candidate(
            summary="Kira and Robert completed a grounded first local text test.",
            detail="Robert talked with Kira in text-only mode and confirmed she should not claim voice, avatar, world, internet, or webcam access as active.",
            core_facts=[
                "The first local Kira test was text-only.",
                "Kira should not claim inactive future systems are active.",
            ],
            known_unknowns=[
                "The long-term model choice was not decided in this memory.",
            ],
            allowed_interpretation=[
                "This was a cautious grounding milestone.",
            ],
            primary_emotion="grounded",
            intensity=0.4,
            residue=0.2,
            importance_weight="medium",
            importance_score=0.5,
            source_log_path="Data/logs/conversation_log.jsonl",
        )
        self.assertEqual(validate_candidate(candidate), [])
        self.assertEqual(candidate["status"], "draft")
        self.assertEqual(candidate["approval"]["approved_by"], "")
        self.assertIn("Do not treat conversation logs as trusted memory.", candidate["forbidden_inferences"])

    def test_candidate_requires_specific_core_facts(self) -> None:
        candidate = build_candidate(
            summary="Kira and Robert talked.",
            detail="They had a first talk.",
            core_facts=[],
            known_unknowns=["No details should be inferred."],
            allowed_interpretation=[],
            primary_emotion="neutral",
            intensity=0.2,
            residue=0.1,
            importance_weight="low",
            importance_score=0.2,
            source_log_path="Data/logs/conversation_log.jsonl",
        )
        errors = validate_candidate(candidate)
        self.assertIn("core_facts must be a non-empty list.", errors)


if __name__ == "__main__":
    unittest.main()
