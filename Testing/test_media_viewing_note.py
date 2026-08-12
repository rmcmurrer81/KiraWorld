import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from build_media_library_index import build_index  # noqa: E402
from create_media_viewing_note import build_note  # noqa: E402
from validate_media_viewing_note import validate_media_viewing_note  # noqa: E402


class MediaViewingNoteTests(unittest.TestCase):
    def test_template_validates(self) -> None:
        path = PROJECT_ROOT / "Data" / "media" / "viewing_notes" / "media_viewing_note_template.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(validate_media_viewing_note(data), [])

    def test_rejects_note_that_creates_memory(self) -> None:
        note = {
            "note_id": "bad_note",
            "viewer": "kira",
            "media_title": "Demo",
            "media_type": "movie",
            "source_path_or_service": "Data/library/movies/demo.mp4",
            "access_mode": "watched",
            "reaction_summary": "Kira watched a movie.",
            "memory_policy": {
                "does_not_become_lived_memory": False,
                "does_not_create_temporary_ai_automatically": True,
                "source_material_remains_source": True,
            },
            "privacy": {
                "default_visibility": "owner_only",
                "may_share_summary": True,
                "public_export_allowed_without_review": False,
            },
            "status": "draft",
        }
        errors = validate_media_viewing_note(note)
        self.assertIn("memory_policy.does_not_become_lived_memory must be true.", errors)

    def test_builds_note_from_media_index_entry(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Data" / "library"
            movie = root / "movies" / "power_rangers" / "mighty_morphin_power_rangers_the_movie_1995.mp4"
            movie.parent.mkdir(parents=True)
            movie.write_bytes(b"movie")

            index_path = Path(tmpdir) / "Data" / "indexes" / "media_library_index.json"
            index_path.parent.mkdir(parents=True)
            index_path.write_text(json.dumps(build_index(root), indent=2), encoding="utf-8")

            source_path = build_index(root)["entries"][0]["path"]
            note = build_note(
                source_path,
                "lisa",
                "Lisa watched the movie and saved a draft reaction note.",
                index_path=index_path,
            )
            self.assertEqual(validate_media_viewing_note(note), [])
            self.assertEqual(note["viewer"], "lisa")
            self.assertEqual(note["media_type"], "movie")
            self.assertEqual(note["access_mode"], "watched")
            self.assertTrue(note["memory_policy"]["does_not_create_temporary_ai_automatically"])


if __name__ == "__main__":
    unittest.main()
