import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from audit_media_library_names import audit_directory, audit_file, build_audit  # noqa: E402


class MediaLibraryNameAuditTests(unittest.TestCase):
    def test_flags_download_style_name(self) -> None:
        result = audit_file(Path("Data/library/tv_shows/demo/SHOW   Full Episode ▶.mp4"))
        self.assertIn("multiple_spaces", result["issues"])
        self.assertIn("download_label:full episode", result["issues"])
        self.assertIn("non_ascii_or_emoji", result["issues"])

    def test_build_audit_has_no_rename_side_effect(self) -> None:
        audit = build_audit(PROJECT_ROOT / "Data" / "library")
        self.assertTrue(audit["rules"]["do_not_rename_automatically"])
        self.assertIn("flagged", audit)
        self.assertIn("flagged_directories", audit)

    def test_flags_directory_name(self) -> None:
        result = audit_directory(Path("Data/library/movies/Not Quite Human"))
        self.assertEqual(result["item_type"], "directory")
        self.assertIn("multiple_words_without_underscores", result["issues"])


if __name__ == "__main__":
    unittest.main()
