import sys
import unittest
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from validate_memory_seed import validate_seed  # noqa: E402


class MemorySeedValidatorTests(unittest.TestCase):
    def test_safe_seed_passes(self) -> None:
        data = {
            "memory_id": "shared_001",
            "title": "Shared Event",
            "participants": ["kira", "lisa"],
            "privacy_level": "private_shared",
            "sharing_rule": "requires_all_participant_consent",
            "canon_anchors": ["Kira and Lisa attended the same event."],
            "known_unknowns": ["Exact dialogue is not defined."],
            "allowed_expansion": ["Different interpretations are allowed."],
            "forbidden_changes": ["Do not change participants."],
            "forbidden_inferences": ["Do not invent exact dialogue."],
        }

        self.assertEqual(validate_seed(data), [])

    def test_vague_seed_without_unknowns_fails(self) -> None:
        data = {
            "memory_id": "shared_002",
            "title": "Vague Event",
            "participants": ["kira", "lisa"],
            "privacy_level": "private_shared",
            "sharing_rule": "requires_all_participant_consent",
            "canon_anchors": ["Mostly something happened with stuff later."],
            "known_unknowns": [],
            "allowed_expansion": ["Tone may vary."],
            "forbidden_changes": ["Do not change participants."],
            "forbidden_inferences": ["Do not invent exact dialogue."],
        }

        errors = validate_seed(data)
        self.assertTrue(any("Vague wording" in error for error in errors))

    def test_private_seed_requires_consent_rule(self) -> None:
        data = {
            "memory_id": "shared_003",
            "title": "Private Event",
            "participants": ["kira", "lisa"],
            "privacy_level": "locked",
            "sharing_rule": "owner_only",
            "canon_anchors": ["A private event happened."],
            "known_unknowns": ["Exact dialogue is not defined."],
            "allowed_expansion": ["None."],
            "forbidden_changes": ["Do not change participants."],
            "forbidden_inferences": ["Do not infer private details."],
        }

        errors = validate_seed(data)
        self.assertTrue(any("consent" in error for error in errors))

    def test_named_ordinary_family_moment_seeds_validate(self) -> None:
        for relative in (
            "Data/memory_seeds/kira_core_006_ordinary_family_moments.draft.json",
            "Data/memory_seeds/lisa_core_006_ordinary_family_moments.draft.json",
        ):
            data = json.loads((PROJECT_ROOT / relative).read_text(encoding="utf-8"))
            self.assertEqual(validate_seed(data), [])


if __name__ == "__main__":
    unittest.main()
