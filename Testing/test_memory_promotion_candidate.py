import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from validate_memory_promotion_candidate import validate_candidate  # noqa: E402


class MemoryPromotionCandidateTests(unittest.TestCase):
    def test_ready_candidate_passes(self) -> None:
        candidate = {
            "candidate_id": "cand_001",
            "owner": "kira",
            "memory_type": "conversation",
            "summary": "Kira and Robert agreed to keep first local testing text-only.",
            "detail": "Robert approved starting with text-only Kira before voice, avatar, world, internet, or webcam features.",
            "core_facts": [
                "First local testing should start text-only.",
                "Voice, avatar, world, internet, and webcam stay disabled at first."
            ],
            "known_unknowns": [
                "The final desktop model is not chosen in this memory."
            ],
            "forbidden_inferences": [
                "Do not claim the 3D home exists yet."
            ],
            "privacy": {
                "level": "private",
                "sharing_rule": "owner_only"
            },
            "approval": {
                "approved_by": "robert",
                "approval_reason": "Robert explicitly approved this first-test plan.",
                "approved_at": ""
            },
            "status": "ready_for_promotion"
        }

        self.assertEqual(validate_candidate(candidate), [])

    def test_vague_candidate_without_unknowns_fails(self) -> None:
        candidate = {
            "candidate_id": "cand_002",
            "owner": "kira",
            "memory_type": "conversation",
            "summary": "Something important probably happened.",
            "detail": "Kira mostly understood stuff.",
            "core_facts": ["Something happened."],
            "known_unknowns": [],
            "forbidden_inferences": ["Do not invent details."],
            "privacy": {
                "level": "private",
                "sharing_rule": "owner_only"
            },
            "approval": {},
            "status": "draft"
        }

        errors = validate_candidate(candidate)
        self.assertTrue(any("Vague wording" in error for error in errors))

    def test_ready_candidate_requires_approval(self) -> None:
        candidate = {
            "candidate_id": "cand_003",
            "owner": "lisa",
            "memory_type": "conversation",
            "summary": "Lisa made a choice.",
            "detail": "Lisa chose to wait before sharing a private feeling.",
            "core_facts": ["Lisa chose not to share yet."],
            "known_unknowns": ["The private feeling is not recorded."],
            "forbidden_inferences": ["Do not infer the private feeling."],
            "privacy": {
                "level": "locked",
                "sharing_rule": "requires_all_participant_consent"
            },
            "approval": {},
            "status": "ready_for_promotion"
        }

        errors = validate_candidate(candidate)
        self.assertTrue(any("approved_by" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
