import hashlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from media_experience_session import (  # noqa: E402
    MediaExperienceError,
    MediaExperienceLease,
    MediaExperienceLeaseError,
    MediaExperienceSession,
)


class StepClock:
    def __init__(self, start: float = 100.0, step: float = 0.25) -> None:
        self.value = start
        self.step = step

    def __call__(self) -> float:
        current = self.value
        self.value += self.step
        return current


class MediaExperienceSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.library = self.root / "Data" / "library"
        self.library.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def source(self, relative: str, content: bytes) -> Path:
        path = self.library / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def session(self, source: Path, kind: str, **overrides) -> MediaExperienceSession:
        arguments = {
            "project_root": self.root,
            "source_path": source,
            "kind": kind,
            "person_id": "any_approved_person_47",
            "activation_revision": "activation-r9",
            "session_id": "media-session-1",
            "session_nonce": "private-nonce-1",
            "clock": StepClock(),
        }
        arguments.update(overrides)
        return MediaExperienceSession(**arguments)

    def test_exact_library_source_hash_and_all_person_lease(self) -> None:
        source = self.source("movies/example.mkv", b"exact movie bytes")
        session = self.session(source, "movie", media_duration_seconds=90)
        snapshot = session.snapshot()

        self.assertEqual(snapshot["person_id"], "any_approved_person_47")
        self.assertEqual(snapshot["source"]["project_relative_path"], "Data/library/movies/example.mkv")
        self.assertEqual(
            snapshot["source"]["sha256"], hashlib.sha256(b"exact movie bytes").hexdigest()
        )
        self.assertFalse(snapshot["source"]["raw_media_copied"])
        self.assertNotIn("private-nonce-1", session.snapshot_json())

        wrong_person = MediaExperienceLease(
            session_id=session.lease.session_id,
            person_id="different_person",
            activation_revision=session.lease.activation_revision,
            nonce=session.lease.nonce,
        )
        with self.assertRaises(MediaExperienceLeaseError):
            session.resume(wrong_person)

    def test_exact_playback_grant_hash_can_be_reused_without_second_file_hash(self) -> None:
        content = b"grant-validated movie bytes"
        source = self.source("movies/grant.mp4", content)
        validated = {
            "project_relative_path": "Data/library/movies/grant.mp4",
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
            "validation_kind": "ephemeral_playback_grant_full_sha256",
        }
        with mock.patch(
            "media_experience_session._sha256_file",
            side_effect=AssertionError("a second whole-file hash is forbidden"),
        ):
            session = self.session(source, "movie", validated_source=validated)
        snapshot = session.snapshot()
        self.assertEqual(snapshot["source"]["sha256"], validated["sha256"])
        self.assertEqual(
            snapshot["source"]["validation_kind"],
            "ephemeral_playback_grant_full_sha256",
        )

    def test_rejects_source_outside_project_library(self) -> None:
        outside = self.root / "outside.mp4"
        outside.write_bytes(b"outside")
        with self.assertRaisesRegex(MediaExperienceError, "Data/library"):
            self.session(outside, "video")

    def test_pdf_page_visual_and_ocr_evidence_stay_separate(self) -> None:
        source = self.source("magazines/issue.pdf", b"pdf")
        session = self.session(source, "magazine")
        lease = session.lease

        presentation = session.present_page(
            lease,
            page_number=12,
            crop={"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.6},
            zoom=1.75,
            duration_seconds=20,
        )
        session.observe_page(
            lease, presentation_id=presentation["presentation_id"], duration_seconds=7
        )
        ocr = session.add_text_provenance(
            lease,
            provenance_kind="ocr",
            content_sha256=hashlib.sha256(b"ocr text").hexdigest(),
            page_number=12,
            language="en",
        )
        summary = session.add_text_provenance(
            lease,
            provenance_kind="summary",
            content_sha256=hashlib.sha256(b"summary").hexdigest(),
            label="publisher summary",
        )

        snapshot = session.snapshot()
        self.assertEqual(presentation["channel"], "visual_page")
        self.assertFalse(presentation["ocr_included"])
        self.assertEqual(snapshot["page_observations"][0]["duration_seconds"], 7.0)
        self.assertFalse(snapshot["page_observations"][0]["based_on_ocr"])
        self.assertEqual(ocr["provenance_kind"], "ocr")
        self.assertFalse(ocr["counts_as_page_seen"])
        self.assertFalse(summary["counts_as_watched"])
        self.assertEqual(len(snapshot["page_observations"]), 1)

        with self.assertRaisesRegex(MediaExperienceError, "cannot exceed"):
            session.observe_page(
                lease,
                presentation_id=presentation["presentation_id"],
                duration_seconds=14,
            )

    def test_video_clock_pause_seek_resume_finish_and_observation_bounds(self) -> None:
        source = self.source("tv/episode.mp4", b"episode")
        session = self.session(source, "tv", media_duration_seconds=60)
        lease = session.lease

        session.resume(lease)
        session.pause(lease, at_media_seconds=10)
        session.seek(lease, to_media_seconds=20)
        session.resume(lease)
        session.pause(lease, at_media_seconds=30)
        session.observe_interval(
            lease, start_seconds=2, end_seconds=8, modality="audiovisual"
        )
        session.observe_interval(
            lease, start_seconds=21, end_seconds=29, modality="visual"
        )
        with self.assertRaisesRegex(MediaExperienceError, "wholly covered"):
            session.observe_interval(
                lease, start_seconds=8, end_seconds=22, modality="audiovisual"
            )
        session.finish(lease, at_media_seconds=30)

        snapshot = session.snapshot()
        self.assertEqual(
            [(item["start_seconds"], item["end_seconds"]) for item in snapshot["playback"]["presented_intervals"]],
            [(0.0, 10.0), (20.0, 30.0)],
        )
        self.assertEqual(snapshot["playback"]["media_clock_seconds"], 30.0)
        self.assertEqual(snapshot["playback"]["state"], "finished")
        self.assertEqual(
            [event["event_type"] for event in snapshot["events"]],
            [
                "session_started",
                "playback_resumed",
                "playback_paused",
                "playback_seeked",
                "playback_resumed",
                "playback_paused",
                "media_interval_observed",
                "media_interval_observed",
                "playback_finished",
            ],
        )
        self.assertEqual(snapshot["events"][0]["event_clock_seconds"], 100.0)
        self.assertEqual(snapshot["events"][1]["event_clock_seconds"], 100.25)

    def test_captions_scripts_and_metadata_are_provenance_not_watching(self) -> None:
        source = self.source("videos/clip.mp4", b"clip")
        captions = self.source("videos/clip.en.vtt", b"captions")
        session = self.session(source, "video", media_duration_seconds=20)
        lease = session.lease

        caption_record = session.add_text_provenance(
            lease,
            provenance_kind="captions",
            source_path=captions,
            interval_seconds=(0, 20),
            language="en",
        )
        session.add_text_provenance(
            lease,
            provenance_kind="script",
            content_sha256=hashlib.sha256(b"script").hexdigest(),
            interval_seconds=(0, 20),
        )
        session.add_text_provenance(
            lease,
            provenance_kind="metadata",
            content_sha256=hashlib.sha256(b"metadata").hexdigest(),
        )

        snapshot = session.snapshot()
        self.assertEqual(snapshot["playback"]["presented_intervals"], [])
        self.assertEqual(snapshot["playback"]["observed_intervals"], [])
        self.assertFalse(caption_record["counts_as_watched"])
        self.assertFalse(snapshot["truth_boundaries"]["captions_or_script_counts_as_watched"])

    def test_music_lyrics_do_not_count_as_listening(self) -> None:
        source = self.source("music/song.flac", b"song")
        session = self.session(source, "music", media_duration_seconds=15)
        lease = session.lease

        lyrics = session.add_text_provenance(
            lease,
            provenance_kind="lyrics",
            content_sha256=hashlib.sha256(b"licensed supplied lyrics").hexdigest(),
        )
        self.assertFalse(lyrics["counts_as_listened"])
        self.assertEqual(session.snapshot()["playback"]["observed_intervals"], [])

        session.resume(lease)
        session.pause(lease, at_media_seconds=5)
        observed = session.observe_interval(
            lease, start_seconds=1, end_seconds=4, modality="audio"
        )
        self.assertEqual(observed["duration_seconds"], 3.0)
        with self.assertRaisesRegex(MediaExperienceError, "modality"):
            session.observe_interval(
                lease, start_seconds=1, end_seconds=2, modality="visual"
            )

    def test_private_reactions_are_bounded_redacted_and_non_promoting(self) -> None:
        source = self.source("music/short.wav", b"wave")
        session = self.session(
            source,
            "music",
            media_duration_seconds=5,
            max_private_reactions=2,
            max_private_reaction_characters=12,
        )
        lease = session.lease
        session.add_private_reaction(lease, reaction="I like this")
        session.add_private_reaction(lease, reaction="Not for me")
        with self.assertRaisesRegex(MediaExperienceError, "count limit"):
            session.add_private_reaction(lease, reaction="third")

        default_snapshot = session.snapshot()
        private_snapshot = session.snapshot(include_private_reactions=True)
        self.assertEqual(default_snapshot["private_reactions"]["count"], 2)
        self.assertEqual(default_snapshot["private_reactions"]["items"], [])
        self.assertEqual(len(private_snapshot["private_reactions"]["items"]), 2)
        for item in private_snapshot["private_reactions"]["items"]:
            self.assertFalse(item["durable_memory_created"])
            self.assertFalse(item["canon_created"])
            self.assertFalse(item["temporary_ai_evidence_created"])
            self.assertFalse(item["publication_authorized"])

    def test_snapshot_is_json_only_nonpersistent_and_lease_can_be_revoked(self) -> None:
        source = self.source("magazines/private.pdf", b"pages")
        session = self.session(source, "pdf")
        lease = session.lease
        session.finish(lease)
        session.add_private_reaction(lease, reaction="A private thought")
        session.close(lease)

        parsed = json.loads(session.snapshot_json(include_private_reactions=True))
        self.assertFalse(parsed["storage"]["automatic_persistence"])
        self.assertFalse(parsed["storage"]["raw_media_copied"])
        self.assertFalse(parsed["implications"]["lived_memory_created"])
        self.assertFalse(parsed["implications"]["canon_created"])
        self.assertFalse(parsed["implications"]["temporary_ai_evidence_created"])
        self.assertFalse(parsed["implications"]["publication_authorized"])
        self.assertFalse(parsed["lease"]["active"])
        with self.assertRaises(MediaExperienceLeaseError):
            session.add_private_reaction(lease, reaction="too late")


if __name__ == "__main__":
    unittest.main()
