import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from slow_reading import advance_session, build_session, readable_entries, set_status  # noqa: E402
from validate_slow_reading_session import validate_slow_reading_session  # noqa: E402


class SlowReadingToolTests(unittest.TestCase):
    def _index_path(self, tmpdir: str) -> Path:
        index = {
            "index_id": "test_index",
            "generated_at": "test",
            "entries": [
                {
                    "path": "Data/library/novels/frankenstein-mary-shelley.pdf",
                    "name": "frankenstein-mary-shelley.pdf",
                    "category": "novel",
                    "media_type": "document",
                    "library_use": {"can_create_slow_reading_session": True},
                },
                {
                    "path": "Data/library/movies/example.mp4",
                    "name": "example.mp4",
                    "category": "movie",
                    "media_type": "video",
                    "library_use": {"can_create_slow_reading_session": False},
                },
            ],
        }
        path = Path(tmpdir) / "index.json"
        path.write_text(json.dumps(index), encoding="utf-8")
        return path

    def test_readable_entries_filters_books(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            index = json.loads(self._index_path(tmpdir).read_text(encoding="utf-8"))
            rows = readable_entries(index)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["category"], "novel")

    def test_build_session_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path, session = build_session(
                "Data/library/novels/frankenstein-mary-shelley.pdf",
                "kira",
                index_path=self._index_path(tmpdir),
                output_dir=Path(tmpdir),
            )
        self.assertEqual(output_path.name, "slow_reading_kira_frankenstein_mary_shelley.json")
        self.assertEqual(validate_slow_reading_session(session), [])
        self.assertFalse(session["pacing"]["allow_instant_full_ingestion"])

    def test_advance_session_keeps_progress_paced(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _path, session = build_session(
                "Data/library/novels/frankenstein-mary-shelley.pdf",
                "kira",
                index_path=self._index_path(tmpdir),
                output_dir=Path(tmpdir),
            )
        session = advance_session(session, unit_label="chapter_001", summary="Kira read the opening frame.", percent=6.0)
        self.assertEqual(session["progress"]["completed_units"], ["chapter_001"])
        self.assertEqual(session["progress"]["percent_complete_estimate"], 6.0)
        self.assertEqual(validate_slow_reading_session(session), [])

    def test_complete_session_sets_percent_to_100(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _path, session = build_session(
                "Data/library/novels/frankenstein-mary-shelley.pdf",
                "lisa",
                index_path=self._index_path(tmpdir),
                output_dir=Path(tmpdir),
            )
        session = set_status(session, "completed", "Lisa finished the book.")
        self.assertEqual(session["progress"]["percent_complete_estimate"], 100.0)
        self.assertEqual(validate_slow_reading_session(session), [])


if __name__ == "__main__":
    unittest.main()
