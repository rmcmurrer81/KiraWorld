import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from validate_autobiographical_memory_seed import validate_autobiographical_seed  # noqa: E402


class AutobiographicalMemorySeedValidatorTests(unittest.TestCase):
    def test_kira_autobiographical_seed_validates(self) -> None:
        data = json.loads(
            (PROJECT_ROOT / "Data/memory_seeds/kira_autobiographical_memory_seed.draft.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(validate_autobiographical_seed(data), [])

    def test_rejects_seed_without_gap_growth_policy(self) -> None:
        data = {
            "seed_id": "bad_seed",
            "owner": "kira",
            "status": "draft",
            "purpose": "Bad seed.",
            "memory_philosophy": {
                "hard_anchor_rule": "Hard anchors are hard canon.",
                "soft_memory_rule": "Soft memory is allowed.",
                "disputed_memory_rule": "Disputed details can differ.",
                "growth_rule": "Growth exists.",
            },
            "growth_policy": {
                "may_fill_gaps_between_memories": False,
                "gap_fills_start_as": "hard_anchor",
                "promotion_to_hard_anchor_requires": "nothing",
            },
            "identity_timeline": [{"phase": "one"}],
            "autobiographical_memories": [],
            "cross_memory_gap_filling": {"allowed": False},
            "forbidden_uses": ["Do not punish low scores."],
        }

        errors = validate_autobiographical_seed(data)
        self.assertTrue(any("may_fill_gaps_between_memories" in error for error in errors))
        self.assertTrue(any("gap_fills_start_as" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
