import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from recommend_reading import (  # noqa: E402
    DEFAULT_OUTPUT,
    DEFAULT_PROFILE_PATH,
    build_recommendations,
    output_path_for_owner,
)
from validate_reading_interest_profile import validate_profile_file  # noqa: E402


class ReadingRecommendationsTests(unittest.TestCase):
    def test_profiles_validate(self) -> None:
        data = json.loads(DEFAULT_PROFILE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(validate_profile_file(data), [])

    def test_default_output_is_owner_specific(self) -> None:
        self.assertEqual(output_path_for_owner(DEFAULT_OUTPUT, "kira").name, "reading_recommendations_kira.json")
        self.assertEqual(output_path_for_owner(DEFAULT_OUTPUT, "lisa").name, "reading_recommendations_lisa.json")
        custom = Path("custom.json")
        self.assertEqual(output_path_for_owner(custom, "kira_lisa"), custom)

    def test_recommends_history_for_kira(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            library = root / "Data" / "library"
            history_file = library / "history" / "all_about_history_book_of_the_titanic_2014_uk.pdf"
            novel_file = library / "novels" / "frankenstein_mary_shelley.pdf"
            history_file.parent.mkdir(parents=True)
            novel_file.parent.mkdir(parents=True)
            history_file.write_text("x", encoding="utf-8")
            novel_file.write_text("x", encoding="utf-8")
            index_path = root / "index.json"
            profile_path = DEFAULT_PROFILE_PATH
            result = build_recommendations(
                owner="kira",
                index_path=index_path,
                profile_path=profile_path,
                library_root=library,
                update_check_path=root / "updates.json",
                limit=3,
            )
        paths = [item["source_path"].replace("\\", "/") for item in result["recommendations"]]
        self.assertTrue(any(path.endswith("Data/library/history/all_about_history_book_of_the_titanic_2014_uk.pdf") for path in paths))
        self.assertTrue(result["policy"]["new_arrivals_should_be_mentioned_to_owner"])

    def test_recommendations_are_advisory_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            library = root / "Data" / "library"
            book = library / "novels" / "pride_and_prejudice_jane_austen.pdf"
            other = library / "novels" / "the_great_gatsby_f_scott_fitzgerald.pdf"
            book.parent.mkdir(parents=True)
            book.write_text("x", encoding="utf-8")
            other.write_text("x", encoding="utf-8")
            result = build_recommendations(
                owner="lisa",
                index_path=root / "index.json",
                profile_path=DEFAULT_PROFILE_PATH,
                library_root=library,
                update_check_path=root / "updates.json",
            )
        self.assertTrue(result["policy"]["advisory_only"])
        self.assertTrue(result["recommendations"][0]["recommendation_policy"]["reader_may_decline"])

    def test_active_profile_paths_are_skipped_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            library = root / "Data" / "library"
            active = library / "novels" / "pride_and_prejudice_jane_austen.pdf"
            other = library / "novels" / "the_great_gatsby_f_scott_fitzgerald.pdf"
            active.parent.mkdir(parents=True)
            active.write_text("x", encoding="utf-8")
            other.write_text("x", encoding="utf-8")
            profiles = json.loads(DEFAULT_PROFILE_PATH.read_text(encoding="utf-8"))
            for profile in profiles:
                if profile.get("owner") == "lisa":
                    profile["current_interests"]["active_source_paths"] = [
                        "Data/library/novels/pride_and_prejudice_jane_austen.pdf"
                    ]
            profile_path = root / "profiles.json"
            profile_path.write_text(json.dumps(profiles), encoding="utf-8")
            result = build_recommendations(
                owner="lisa",
                index_path=root / "index.json",
                profile_path=profile_path,
                library_root=library,
                update_check_path=root / "updates.json",
            )
        paths = [item["source_path"].replace("\\", "/") for item in result["recommendations"]]
        self.assertFalse(any(path.endswith("pride_and_prejudice_jane_austen.pdf") for path in paths))

    def test_story_era_can_recommend_history_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            library = root / "Data" / "library"
            novel = library / "novels" / "the_great_gatsby_f_scott_fitzgerald.pdf"
            history = library / "history" / "all_about_history_book_of_prohibition_1st_edition_2019.pdf"
            novel.parent.mkdir(parents=True)
            history.parent.mkdir(parents=True)
            novel.write_text("x", encoding="utf-8")
            history.write_text("x", encoding="utf-8")
            profile_path = root / "profiles.json"
            profile = [
                {
                    "profile_id": "reading_interest_lisa_test",
                    "owner": "lisa",
                    "current_interests": {
                        "themes": ["relationship"],
                        "genres": ["classic_literature", "history"],
                        "questions": ["What was the world around Gatsby like?"],
                        "active_source_paths": ["Data/library/novels/the_great_gatsby_f_scott_fitzgerald.pdf"],
                        "favorite_source_paths": [],
                        "historical_context_source_paths": ["Data/library/novels/the_great_gatsby_f_scott_fitzgerald.pdf"],
                    },
                    "preferred_categories": ["novel", "history"],
                    "theme_weights": {"history": 3},
                    "avoid_when_mood": {},
                    "rotation_policy": {
                        "max_active_private_sessions": 2,
                        "max_active_shared_sessions": 1,
                        "include_new_arrivals": True,
                        "allow_rereading_favorites": True,
                        "reread_requires_reader_choice": True,
                        "mix_modes": ["curiosity", "historical_context"],
                        "do_not_force_recommendations": True,
                    },
                    "privacy": {
                        "default_visibility": "summary_if_chosen",
                        "private_preferences_require_owner_permission": True,
                    },
                    "status": "active",
                }
            ]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            result = build_recommendations(
                owner="lisa",
                index_path=root / "index.json",
                profile_path=profile_path,
                library_root=library,
                update_check_path=root / "updates.json",
            )
        self.assertTrue(result["policy"]["story_era_history_followups_allowed_by_choice"])
        reasons = [reason for item in result["recommendations"] for reason in item["reasons"]]
        self.assertIn("story_era_context:gatsby", reasons)

    def test_evolved_taste_can_suppress_old_favorite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            library = root / "Data" / "library"
            favorite = library / "novels" / "pride_and_prejudice_jane_austen.pdf"
            other = library / "novels" / "the_great_gatsby_f_scott_fitzgerald.pdf"
            favorite.parent.mkdir(parents=True)
            favorite.write_text("x", encoding="utf-8")
            other.write_text("x", encoding="utf-8")
            taste_dir = root / "tastes"
            taste_dir.mkdir()
            taste_dir.joinpath("reading_taste_profile_lisa.json").write_text(
                json.dumps(
                    {
                        "owner": "lisa",
                        "favorite_source_paths": [],
                        "cooling_or_outgrown_source_paths": [
                            "Data/library/novels/pride_and_prejudice_jane_austen.pdf"
                        ],
                        "source_tastes": {},
                    }
                ),
                encoding="utf-8",
            )
            result = build_recommendations(
                owner="lisa",
                index_path=root / "index.json",
                profile_path=DEFAULT_PROFILE_PATH,
                library_root=library,
                update_check_path=root / "updates.json",
                taste_dir=taste_dir,
                include_active=True,
            )
        old_favorite = [
            item
            for item in result["recommendations"]
            if item["source_path"].endswith("pride_and_prejudice_jane_austen.pdf")
        ]
        self.assertFalse(old_favorite)


if __name__ == "__main__":
    unittest.main()
