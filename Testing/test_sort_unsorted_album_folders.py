import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from sort_unsorted_album_folders import build_plan  # noqa: E402


class SortUnsortedAlbumFoldersTests(unittest.TestCase):
    def test_artist_album_folder_moves_to_music_albums(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "unsorted"
            target = root / "albums"
            album = source / "bad-blood-all-this-bad-blood"
            album.mkdir(parents=True)
            album.joinpath("01 Pompeii.mp3").write_text("demo", encoding="utf-8")

            plan = build_plan(source, target)

            self.assertEqual(plan["operation_count"], 1)
            self.assertIn("bastille_bad_blood_all_this_bad_blood_2013", plan["operations"][0]["target"])
            self.assertIn("01_pompeii.mp3", plan["operations"][0]["target"])

    def test_soundtrack_folder_is_ignored_by_artist_album_sorter(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "unsorted"
            target = root / "albums"
            album = source / "Mamma Mia! Here We Go Again! The Movie Soundtrack"
            album.mkdir(parents=True)
            album.joinpath("01 When I Kissed The Teacher.mp3").write_text("demo", encoding="utf-8")

            plan = build_plan(source, target)

            self.assertEqual(plan["operation_count"], 0)

    def test_kidz_bop_is_treated_as_album_not_soundtrack(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "unsorted"
            target = root / "albums"
            album = source / "kidz_bop_vol_17_with_2_bonus_tracks"
            album.mkdir(parents=True)
            album.joinpath("01 Song.mp3").write_text("demo", encoding="utf-8")

            plan = build_plan(source, target)

            self.assertEqual(plan["operation_count"], 1)
            self.assertIn("kidz_bop_vol_17_2010", plan["operations"][0]["target"])

    def test_bob_seger_collection_folder_moves_to_albums(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "unsorted"
            target = root / "albums"
            album = source / "Bob Seger & The Silver Bullet Band"
            album.mkdir(parents=True)
            album.joinpath("01 Makin' Thunderbirds.mp3").write_text("demo", encoding="utf-8")

            plan = build_plan(source, target)

            self.assertEqual(plan["operation_count"], 1)
            self.assertIn("bob_seger_and_the_silver_bullet_band_collection", plan["operations"][0]["target"])


if __name__ == "__main__":
    unittest.main()
