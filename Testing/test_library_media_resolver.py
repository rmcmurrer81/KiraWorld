import hashlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from library_media_resolver import (  # noqa: E402
    LibraryMediaResolutionError,
    LibraryMediaResolver,
)
from media_experience_session import MediaExperienceSession  # noqa: E402


class FixedStepClock:
    def __init__(self) -> None:
        self.value = 1.0

    def __call__(self) -> float:
        result = self.value
        self.value += 1.0
        return result


class LibraryMediaResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.library = self.root / "Data" / "library"
        self.library.mkdir(parents=True)
        self.resolver = LibraryMediaResolver(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def add(self, relative: str, content: bytes = b"fixture") -> Path:
        path = self.library / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_classifies_page_video_audio_and_distinct_sidecar_families(self) -> None:
        expected = {
            "magazines/issue.pdf": ("page_media", "magazine_pdf", "magazine", None),
            "magazines/issue_pages/page_001.jpg": (
                "page_media",
                "magazine_page_image",
                "magazine",
                None,
            ),
            "documents/manual.pdf": ("page_media", "document_pdf", "pdf", None),
            "documents/manual_pages/page_001.png": (
                "page_media",
                "document_page_image",
                "pdf",
                None,
            ),
            "movies/feature.mkv": ("timed_video", "movie_video", "movie", None),
            "tv_shows/series/s01e01.mp4": ("timed_video", "tv_video", "tv", None),
            "personal_videos/clip.webm": ("timed_video", "general_video", "video", None),
            "music/artist/song.flac": ("timed_audio", "music_audio", "music", None),
            "tv_shows/series/s01e01.en.srt": (
                "text_sidecar",
                "subtitle_sidecar",
                None,
                "subtitles",
            ),
            "tv_shows/series/s01e01.transcript.txt": (
                "text_sidecar",
                "transcript_sidecar",
                None,
                "transcript",
            ),
            "music/artist/song.lyrics.txt": (
                "text_sidecar",
                "lyrics_sidecar",
                None,
                "lyrics",
            ),
        }
        for relative, wanted in expected.items():
            with self.subTest(relative=relative):
                path = self.add(relative, relative.encode("utf-8"))
                classification = self.resolver.resolve(path)["classification"]
                actual = (
                    classification["family"],
                    classification["role"],
                    classification["experience_kind"],
                    classification["session_provenance_kind"],
                )
                self.assertEqual(actual, wanted)

    def test_descriptor_is_exact_hash_bound_read_only_and_non_promoting(self) -> None:
        content = b"exact owner-selected bytes"
        source = self.add("movies/example.mp4", content)
        before = source.read_bytes()
        descriptor = self.resolver.resolve("Data/library/movies/example.mp4")
        after = source.read_bytes()

        self.assertEqual(before, after)
        self.assertEqual(descriptor["project_relative_path"], "Data/library/movies/example.mp4")
        self.assertEqual(descriptor["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(descriptor["source_identity"]["size_bytes"], len(content))
        self.assertEqual(
            self.resolver.source_identity(source)["source_identity"],
            descriptor["source_identity"],
        )
        self.assertTrue(descriptor["selection"]["owner_selected"])
        self.assertFalse(descriptor["selection"]["auto_play"])
        self.assertFalse(descriptor["selection"]["auto_open"])
        self.assertFalse(descriptor["selection"]["raw_media_copied"])
        self.assertTrue(all(value is False for value in descriptor["implications"].values()))

    def test_rejects_traversal_absolute_outside_directory_and_unknown_extension(self) -> None:
        outside = self.root / "outside.mp4"
        outside.write_bytes(b"outside")
        self.add("movies/safe.mp4")
        self.add("objects/unsafe.exe")

        with self.assertRaisesRegex(LibraryMediaResolutionError, "traversal"):
            self.resolver.resolve("movies/../movies/safe.mp4")
        with self.assertRaisesRegex(LibraryMediaResolutionError, "inside"):
            self.resolver.resolve(outside)
        with self.assertRaisesRegex(LibraryMediaResolutionError, "regular file"):
            self.resolver.resolve("movies")
        with self.assertRaisesRegex(LibraryMediaResolutionError, "unsupported"):
            self.resolver.resolve("objects/unsafe.exe")

    def test_rejects_a_link_like_component_before_hashing(self) -> None:
        source = self.add("movies/linked.mp4", b"not actually read")
        original = Path.is_symlink

        def pretend_one_file_is_a_link(path: Path) -> bool:
            if path == source:
                return True
            return original(path)

        with patch("library_media_resolver.Path.is_symlink", autospec=True, side_effect=pretend_one_file_is_a_link):
            with self.assertRaisesRegex(LibraryMediaResolutionError, "symlinks"):
                self.resolver.resolve(source)

    def test_catalog_contains_only_explicit_selections_and_is_deterministic(self) -> None:
        selected_movie = self.add("movies/zeta.mp4", b"z")
        selected_music = self.add("music/alpha.flac", b"a")
        self.add("movies/not_selected.mp4", b"not selected")

        first = self.resolver.catalog([selected_movie, selected_music])
        second = self.resolver.catalog([selected_music, selected_movie])
        self.assertEqual(first, second)
        self.assertEqual(first["selection_count"], 2)
        self.assertEqual(
            [entry["project_relative_path"] for entry in first["entries"]],
            ["Data/library/movies/zeta.mp4", "Data/library/music/alpha.flac"],
        )
        self.assertNotIn("not_selected", json.dumps(first))
        self.assertTrue(first["behavior"]["owner_selected_files_only"])
        self.assertFalse(first["behavior"]["recursive_discovery_performed"])
        self.assertTrue(first["behavior"]["source_opened_for_hashing_only"])
        self.assertFalse(first["behavior"]["media_decoded_or_played"])
        self.assertFalse(first["behavior"]["external_application_opened"])
        self.assertFalse(first["behavior"]["video_studio_invoked"])
        self.assertFalse(first["behavior"]["automatic_persistence"])
        self.assertEqual(json.loads(self.resolver.catalog_json(first)), first)

        with self.assertRaisesRegex(LibraryMediaResolutionError, "twice"):
            self.resolver.catalog([selected_movie, selected_movie])

    def test_resolved_primary_and_transcript_feed_session_without_claiming_experience(self) -> None:
        video = self.add("tv_shows/demo/episode.mp4", b"video")
        transcript = self.add("tv_shows/demo/episode.transcript.txt", b"transcript")
        video_descriptor = self.resolver.resolve(video)
        transcript_descriptor = self.resolver.resolve(transcript)

        session = MediaExperienceSession(
            project_root=self.root,
            source_path=video_descriptor["project_relative_path"],
            kind=video_descriptor["classification"]["experience_kind"],
            person_id="owner_selected_person",
            activation_revision="activation-1",
            session_id="session-1",
            session_nonce="nonce-1",
            media_duration_seconds=30,
            clock=FixedStepClock(),
        )
        provenance = session.add_text_provenance(
            session.lease,
            provenance_kind=transcript_descriptor["classification"]["session_provenance_kind"],
            source_path=transcript_descriptor["project_relative_path"],
            content_sha256=transcript_descriptor["sha256"],
            interval_seconds=(0, 30),
        )
        snapshot = session.snapshot()
        self.assertEqual(provenance["provenance_kind"], "transcript")
        self.assertFalse(provenance["counts_as_watched"])
        self.assertFalse(provenance["counts_as_listened"])
        self.assertEqual(snapshot["playback"]["presented_intervals"], [])
        self.assertEqual(snapshot["playback"]["observed_intervals"], [])

    def test_audio_transcript_is_provenance_and_not_listening(self) -> None:
        audio = self.add("radio_shows/demo/episode.opus", b"audio")
        transcript = self.add("radio_shows/demo/episode.transcript.txt", b"words")
        audio_descriptor = self.resolver.resolve(audio)
        transcript_descriptor = self.resolver.resolve(transcript)
        session = MediaExperienceSession(
            project_root=self.root,
            source_path=audio_descriptor["project_relative_path"],
            kind=audio_descriptor["classification"]["experience_kind"],
            person_id="listener",
            activation_revision="activation-audio",
            session_id="session-audio",
            session_nonce="nonce-audio",
            media_duration_seconds=10,
            clock=FixedStepClock(),
        )
        provenance = session.add_text_provenance(
            session.lease,
            provenance_kind=transcript_descriptor["classification"]["session_provenance_kind"],
            source_path=transcript_descriptor["project_relative_path"],
            content_sha256=transcript_descriptor["sha256"],
            interval_seconds=(0, 10),
        )
        self.assertEqual(provenance["provenance_kind"], "transcript")
        self.assertFalse(provenance["counts_as_listened"])
        self.assertEqual(session.snapshot()["playback"]["observed_intervals"], [])


if __name__ == "__main__":
    unittest.main()
