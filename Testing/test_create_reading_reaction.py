import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from create_reading_reaction import make_reading_reaction, write_reading_reaction  # noqa: E402
from validate_reading_reaction import validate_reading_reaction  # noqa: E402


class CreateReadingReactionTests(unittest.TestCase):
    def test_make_reading_reaction_validates_and_keeps_source_separate(self) -> None:
        reaction = make_reading_reaction(
            "kira",
            "Data/library/scripts/miraculous_ladybug/episode_0509.pdf",
            title="episode_0509",
            unit_label="pages_001_002",
            progress_percent=5,
            stance="like",
            favorite_moments=["the opening has a nervous, bright energy"],
            emotions=["curious"],
            reasons=["the script feels lively without needing me to invent scenes"],
        )

        self.assertEqual(validate_reading_reaction(reaction), [])
        self.assertTrue(reaction["source"]["source_material_remains_source"])
        self.assertTrue(reaction["memory_policy"]["does_not_become_lived_memory"])

    def test_write_reaction_updates_reading_taste_profile(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            reaction = make_reading_reaction(
                "lisa",
                "Data/library/novels/test_book.pdf",
                title="test_book",
                stance="love",
                reasons=["it hits harder on reread"],
            )

            reaction_path, profile_path = write_reading_reaction(
                reaction,
                reaction_dir=root / "reactions",
                output_dir=root / "tastes",
            )

            self.assertTrue(reaction_path.exists())
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            self.assertIn("Data/library/novels/test_book.pdf", profile["favorite_source_paths"])


if __name__ == "__main__":
    unittest.main()
