import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from sort_unsorted_music_videos import apply_plan, build_plan, infer_artist_title  # noqa: E402


class SortUnsortedMusicVideosTests(unittest.TestCase):
    def test_infers_dash_artist_title(self) -> None:
        artist, title = infer_artist_title(Path("Kelly Clarkson - Breakaway.mp4"))
        self.assertEqual(artist, "kelly_clarkson")
        self.assertEqual(title, "breakaway")

    def test_known_soundtrack_override(self) -> None:
        artist, title = infer_artist_title(Path("Wildside (From Adventures in Babysitting (Official Lyric Video)).mp4"))
        self.assertEqual(artist, "sabrina_carpenter_and_sofia_carson")
        self.assertEqual(title, "wildside_from_adventures_in_babysitting")

    def test_live_performance_overrides_keep_artist_metadata(self) -> None:
        artist, title = infer_artist_title(Path("ariana_debose_this_wish_live_from_disneyland_paris.mp4"))
        self.assertEqual(artist, "ariana_debose")
        self.assertEqual(title, "this_wish_live_from_disneyland_paris")

        artist, title = infer_artist_title(Path("ray_parker_jr_ghostbusters_1984.mp4"))
        self.assertEqual(artist, "ray_parker_jr")
        self.assertEqual(title, "ghostbusters_1984")

    def test_applies_moves_without_overwriting_duplicates(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "music" / "unsorted"
            target = root / "music" / "music_videos" / "by_artist"
            source.mkdir(parents=True)
            existing = target / "kelly_clarkson" / "kelly_clarkson_breakaway.mp4"
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b"existing")
            source.joinpath("Kelly Clarkson - Breakaway.mp4").write_bytes(b"new")

            plan = build_plan(source, target)
            result = apply_plan(plan)

            self.assertEqual(result["applied_count"], 1)
            self.assertTrue(target.joinpath("kelly_clarkson", "kelly_clarkson_breakaway_duplicate_2.mp4").exists())
            self.assertFalse(source.joinpath("Kelly Clarkson - Breakaway.mp4").exists())


if __name__ == "__main__":
    unittest.main()
