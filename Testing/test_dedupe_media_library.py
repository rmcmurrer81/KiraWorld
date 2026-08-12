import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from dedupe_media_library import apply_duplicate_plan, build_duplicate_plan  # noqa: E402


class DedupeMediaLibraryTests(unittest.TestCase):
    def test_moves_exact_duplicates_and_keeps_named_variant(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Data" / "library"
            trash = Path(tmpdir) / "trash"
            keep = root / "music" / "artist" / "song.mp4"
            duplicate = root / "music" / "artist" / "song_duplicate_2.mp4"
            variant = root / "music" / "artist" / "song_live.mp4"
            keep.parent.mkdir(parents=True)
            keep.write_bytes(b"same")
            duplicate.write_bytes(b"same")
            variant.write_bytes(b"different")

            plan = build_duplicate_plan(root)
            result = apply_duplicate_plan(plan, trash)

            self.assertEqual(plan["duplicate_group_count"], 1)
            self.assertEqual(result["moved_count"], 1)
            self.assertTrue(keep.exists())
            self.assertFalse(duplicate.exists())
            self.assertTrue(variant.exists())
            self.assertTrue(any(trash.rglob("song_duplicate_2.mp4")))


if __name__ == "__main__":
    unittest.main()
