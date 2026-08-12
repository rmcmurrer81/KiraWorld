import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from sort_unsorted_soundtracks import apply_plan, build_plan  # noqa: E402


class SortUnsortedSoundtracksTests(unittest.TestCase):
    def test_plans_mamma_mia_soundtrack_album(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "music" / "unsorted" / "Mamma Mia! The Movie Soundtrack"
            source.mkdir(parents=True)
            source.joinpath("01 Honey, Honey.mp3").write_bytes(b"fake")
            target = root / "music" / "soundtracks"

            plan = build_plan(source.parent, target)

            self.assertEqual(plan["operation_count"], 1)
            operation = plan["operations"][0]
            self.assertEqual(operation["album"], "mamma_mia_the_movie_2008")
            self.assertTrue(operation["target"].endswith("mamma_mia_the_movie_2008/01_honey_honey.mp3"))

    def test_apply_moves_tracks_and_removes_empty_folder(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_root = root / "music" / "unsorted"
            album_dir = source_root / "Mamma Mia! The Movie Soundtrack"
            album_dir.mkdir(parents=True)
            album_dir.joinpath("14 The Winner Takes It All.mp3").write_bytes(b"fake")
            target = root / "music" / "soundtracks"
            plan = build_plan(source_root, target)

            result = apply_plan(plan)

            self.assertEqual(result["applied_count"], 1)
            self.assertTrue((target / "mamma_mia_the_movie_2008" / "14_the_winner_takes_it_all.mp3").exists())
            self.assertFalse(album_dir.exists())

    def test_regular_artist_album_is_ignored(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_root = root / "music" / "unsorted"
            album_dir = source_root / "bad-blood-all-this-bad-blood"
            album_dir.mkdir(parents=True)
            album_dir.joinpath("01 Pompeii.mp3").write_bytes(b"fake")
            target = root / "music" / "soundtracks"

            plan = build_plan(source_root, target)

            self.assertEqual(plan["operation_count"], 0)

    def test_kidz_bop_folder_is_ignored(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_root = root / "music" / "unsorted"
            album_dir = source_root / "kidz_bop_vol_17_with_2_bonus_tracks"
            album_dir.mkdir(parents=True)
            album_dir.joinpath("01 Song.mp3").write_bytes(b"fake")
            target = root / "music" / "soundtracks"

            plan = build_plan(source_root, target)

            self.assertEqual(plan["operation_count"], 0)

    def test_mamma_mia_here_we_go_again_override(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_root = root / "music" / "unsorted"
            album_dir = source_root / "Mamma Mia! Here We Go Again! The Movie Soundtrack"
            album_dir.mkdir(parents=True)
            album_dir.joinpath("01 When I Kissed The Teacher.mp3").write_bytes(b"fake")
            target = root / "music" / "soundtracks"

            plan = build_plan(source_root, target)

            self.assertEqual(plan["operation_count"], 1)
            self.assertEqual(plan["operations"][0]["album"], "mamma_mia_here_we_go_again_2018")


if __name__ == "__main__":
    unittest.main()
