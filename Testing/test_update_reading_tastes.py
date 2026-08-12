import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from update_reading_tastes import apply_event, build_empty_profile, reaction_to_event  # noqa: E402


class UpdateReadingTastesTests(unittest.TestCase):
    def test_newer_cooling_reaction_can_retire_old_favorite(self) -> None:
        profile = build_empty_profile("kira")
        source_path = "Data/library/novels/frankenstein_mary_shelley.pdf"
        apply_event(
            profile,
            {
                "reaction_id": "old_love",
                "source_path": source_path,
                "title": "Frankenstein",
                "stance": "love",
                "affinity": 0.9,
                "reasons": ["felt seen"],
            },
        )
        self.assertIn(source_path, profile["favorite_source_paths"])

        for index in range(3):
            apply_event(
                profile,
                {
                    "reaction_id": f"cooling_{index}",
                    "source_path": source_path,
                    "title": "Frankenstein",
                    "stance": "outgrown",
                    "affinity": -0.6,
                    "reasons": ["does not fit current mood"],
                },
            )

        self.assertNotIn(source_path, profile["favorite_source_paths"])
        self.assertIn(source_path, profile["cooling_or_outgrown_source_paths"])
        self.assertEqual(profile["source_tastes"][source_path]["current_status"], "outgrown_or_disliked")

    def test_reaction_preference_signal_becomes_event(self) -> None:
        reaction = {
            "reaction_id": "reaction_1",
            "reader": "lisa",
            "source": {
                "title": "Pride and Prejudice",
                "source_path": "Data/library/novels/pride_and_prejudice_jane_austen.pdf",
            },
            "preference_signal": {
                "stance": "mixed",
                "current_affinity": 0.1,
                "interest_delta": -0.4,
                "reasons": ["liked the tension less today"],
                "may_change_later": True,
                "older_reactions_can_be_reinterpreted": True,
            },
        }
        event = reaction_to_event(reaction)
        self.assertIsNotNone(event)
        self.assertLess(event["affinity"], 0)
        self.assertEqual(event["stance"], "mixed")


if __name__ == "__main__":
    unittest.main()
