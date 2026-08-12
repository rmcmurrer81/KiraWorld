import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from build_media_library_index import build_index  # noqa: E402
from check_media_library_updates import check_updates  # noqa: E402


class MediaLibraryUpdateCheckTests(unittest.TestCase):
    def test_detects_added_file_without_modifying_library(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Data" / "library"
            movie = root / "movies" / "demo" / "demo_movie_1995.mp4"
            movie.parent.mkdir(parents=True)
            movie.write_bytes(b"old")

            index_path = Path(tmpdir) / "Data" / "indexes" / "media_library_index.json"
            index_path.parent.mkdir(parents=True)
            index_path.write_text(
                __import__("json").dumps(build_index(root), indent=2),
                encoding="utf-8",
            )

            added = root / "tv_shows" / "demo" / "season_01" / "s01e01_pilot.mp4"
            added.parent.mkdir(parents=True)
            added.write_bytes(b"new")

            result = check_updates(root, index_path)
            self.assertEqual(result["added_count"], 1)
            self.assertEqual(result["removed_count"], 0)
            self.assertEqual(result["changed_count"], 0)
            self.assertTrue(result["needs_index_refresh"])
            self.assertTrue(result["rules"]["does_not_modify_library"])
            self.assertTrue(added.exists())

    def test_detects_changed_size(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Data" / "library"
            song = root / "music" / "artists" / "demo" / "singles" / "demo_-_song.mp3"
            song.parent.mkdir(parents=True)
            song.write_bytes(b"one")

            index_path = Path(tmpdir) / "Data" / "indexes" / "media_library_index.json"
            index_path.parent.mkdir(parents=True)
            index_path.write_text(
                __import__("json").dumps(build_index(root), indent=2),
                encoding="utf-8",
            )

            song.write_bytes(b"one-two")
            result = check_updates(root, index_path)
            self.assertEqual(result["changed_count"], 1)
            self.assertIn("size_bytes", result["changed"][0]["changes"])


if __name__ == "__main__":
    unittest.main()
