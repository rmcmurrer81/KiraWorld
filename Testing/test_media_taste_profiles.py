import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from update_media_tastes import apply_event, build_empty_profile, infer_tags, reaction_to_event, seed_discovery_pool  # noqa: E402


class MediaTasteProfileTests(unittest.TestCase):
    def test_infer_tags_from_movie_and_music_names(self) -> None:
        entry = {
            "path": "Data/library/music/music_videos/by_artist/frozen_cast/frozen_cast_do_you_want_to_build_a_snowman.mp4",
            "name": "frozen_cast_do_you_want_to_build_a_snowman.mp4",
            "category": "music_video",
        }

        tags = infer_tags(entry)

        self.assertIn("music_video", tags)
        self.assertIn("musical", tags)

    def test_reaction_can_cool_old_favorite(self) -> None:
        profile = build_empty_profile("lisa")
        source_path = "Data/library/tv_shows/ducktales/ducktales_s01e09_terror_of_the_terra_firmians.mp4"
        apply_event(
            profile,
            {
                "source_path": source_path,
                "title": "DuckTales",
                "stance": "love",
                "affinity": 0.9,
                "tags": ["comfort_cartoon"],
            },
        )
        self.assertIn(source_path, profile["favorite_source_paths"])

        for _index in range(3):
            apply_event(
                profile,
                {
                    "source_path": source_path,
                    "title": "DuckTales",
                    "stance": "outgrown",
                    "affinity": -0.6,
                    "tags": ["comfort_cartoon"],
                },
            )

        self.assertIn(source_path, profile["cooling_or_outgrown_source_paths"])

    def test_seed_discovery_pool_is_metadata_only(self) -> None:
        profile = build_empty_profile("kira")
        seed_discovery_pool(
            profile,
            {
                "entries": [
                    {
                        "path": "Data/library/history/history_year_by_year.pdf",
                        "name": "history_year_by_year.pdf",
                        "category": "history",
                    }
                ]
            },
        )

        self.assertEqual(profile["discovery_pool"][0]["status"], "untried")
        self.assertIn("history", profile["current_curiosity_tags"])

    def test_reaction_to_event_keeps_not_lived_memory_flag_outside_memory(self) -> None:
        event = reaction_to_event(
            {
                "owner": "kira",
                "source_path": "Data/library/movies/12_01/12_01.mp4",
                "stance": "curious",
                "affinity": 0.3,
                "tags": ["time_travel"],
            }
        )

        self.assertIsNotNone(event)
        self.assertEqual(event["stance"], "curious")


if __name__ == "__main__":
    unittest.main()
