from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from Core.media_classification_corrections import (
    EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT,
    GENERAL_LIBRARY_MEDIA,
    MediaClassificationCorrectionStore,
)
from Core.shared_person_media_access import media_id_for_path
from Core.source_bound_media_experience import (
    EVIDENCE_SCHEMA,
    PRESENTATION_RECEIPT_SCHEMA,
    MediaPresentationAuthorizationRequired,
    SourceBoundMediaExperienceError,
    SourceBoundResidentMediaExperience,
    _ffmpeg_executable,
    sha256_file,
    validate_evidence_document,
)


class SourceBoundResidentMediaExperienceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.library = self.root / "Data" / "library"
        self.library.mkdir(parents=True)
        (self.root / "Data" / "indexes").mkdir(parents=True)
        (self.root / "config").mkdir(parents=True)
        (self.root / "Avatar" / "avatar_builder" / "policies").mkdir(
            parents=True
        )
        self.pdf_path = self.library / "magazines" / "illustrated_issue.pdf"
        self.video_path = self.library / "video" / "bounded_clip.mp4"
        self.music_path = self.library / "music" / "bounded_tone.wav"
        self.pdf_path.parent.mkdir(parents=True)
        self.video_path.parent.mkdir(parents=True)
        self.music_path.parent.mkdir(parents=True)
        self._create_pdf()
        self._create_music()
        self._create_video()
        self.pdf_rel = "Data/library/magazines/illustrated_issue.pdf"
        self.video_rel = "Data/library/video/bounded_clip.mp4"
        self.music_rel = "Data/library/music/bounded_tone.wav"
        self._write_policy_files()
        self.evidence_root = self.root / "RecoverySprint" / "media_evidence"
        self.runner = SourceBoundResidentMediaExperience(
            project_root=self.root,
            evidence_root=self.evidence_root,
            utc_clock=lambda: "2026-08-02T12:00:00.000000Z",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _create_pdf(self) -> None:
        import fitz

        document = fitz.open()
        page = document.new_page(width=240, height=160)
        page.draw_rect(fitz.Rect(10, 10, 230, 150), color=(0.1, 0.2, 0.7))
        page.insert_text((25, 55), "Exact illustrated page one", fontsize=16)
        page = document.new_page(width=240, height=160)
        page.insert_text((25, 55), "Exact illustrated page two", fontsize=16)
        document.save(self.pdf_path)
        document.close()

    def _create_music(self) -> None:
        sample_rate = 8_000
        duration = 2.0
        timeline = np.arange(int(sample_rate * duration), dtype=np.float64) / sample_rate
        left = 0.30 * np.sin(2 * math.pi * 220 * timeline)
        right = 0.20 * np.sin(2 * math.pi * 330 * timeline)
        stereo = np.column_stack((left, right))
        pcm = np.clip(stereo * 32767, -32768, 32767).astype("<i2")
        with wave.open(str(self.music_path), "wb") as handle:
            handle.setnchannels(2)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            handle.writeframes(pcm.tobytes())

    def _create_video(self) -> None:
        ffmpeg = _ffmpeg_executable()
        caption_path = self.root / "fixture_caption.srt"
        caption_path.write_text(
            "1\n00:00:00,000 --> 00:00:01,800\nExact fixture caption\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                str(ffmpeg),
                "-hide_banner",
                "-nostdin",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=96x64:rate=4:duration=2",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=8000:duration=2",
                "-i",
                str(caption_path),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-map",
                "2:s:0",
                "-shortest",
                "-c:v",
                "mpeg4",
                "-q:v",
                "5",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-c:s",
                "mov_text",
                "-metadata:s:a:0",
                "language=eng",
                "-metadata:s:s:0",
                "language=eng",
                "-n",
                str(self.video_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if result.returncode != 0:
            self.fail(f"could not create the local no-GPU video fixture: {result.stderr}")

    def _write_policy_files(self) -> None:
        config = {
            "schema_version": 1,
            "explicit_adult_only_path_prefixes": ["Data/library/adult/"],
            "explicit_adult_only_exact_paths": [],
            "mature_mainstream_path_prefixes": [],
            "mature_mainstream_exact_paths": [],
            "mature_mainstream_metadata_ratings": ["R", "TV-MA"],
            "explicit_non_adult_candidate_ids": ["marinette"],
            "explicit_adult_candidate_ids": ["kira"],
        }
        (self.root / "config" / "shared_person_media_access.json").write_text(
            json.dumps(config), encoding="utf-8"
        )
        entries = [
            {
                "path": self.pdf_rel,
                "name": self.pdf_path.name,
                "extension": ".pdf",
                "media_type": "document",
                "category": "magazines",
                "size_bytes": self.pdf_path.stat().st_size,
            },
            {
                "path": self.video_rel,
                "name": self.video_path.name,
                "extension": ".mp4",
                "media_type": "video",
                "category": "tv_clip",
                "content_rating": "R",
                "size_bytes": self.video_path.stat().st_size,
            },
            {
                "path": self.music_rel,
                "name": self.music_path.name,
                "extension": ".wav",
                "media_type": "audio",
                "category": "music",
                "size_bytes": self.music_path.stat().st_size,
            },
        ]
        (self.root / "Data" / "indexes" / "media_library_index.json").write_text(
            json.dumps({"entries": entries}), encoding="utf-8"
        )
        (
            self.root
            / "Avatar"
            / "avatar_builder"
            / "policies"
            / "candidate_identity_variant_registry.json"
        ).write_text(json.dumps({"candidates": []}), encoding="utf-8")

    @staticmethod
    def receipt(
        *,
        visual: bool,
        audio: bool,
        modalities: list[str],
        page_presented: float | None = None,
        page_observed: float | None = None,
    ) -> dict[str, object]:
        return {
            "schema": PRESENTATION_RECEIPT_SCHEMA,
            "receipt_id": "reviewed_test_receipt_1",
            "surface_id": "isolated_test_surface",
            "issued_at_utc": "2026-08-02T12:00:00.000000Z",
            "actual_visual_output": visual,
            "actual_audio_output": audio,
            "person_attention_confirmed": bool(modalities),
            "observed_modalities": modalities,
            "page_presented_duration_seconds": page_presented,
            "page_observed_duration_seconds": page_observed,
        }

    @staticmethod
    def read_evidence(attempt: Path) -> dict[str, object]:
        return json.loads((attempt / "EVIDENCE.json").read_text(encoding="utf-8"))

    def test_pdf_page_raster_and_ocr_are_exact_separate_and_append_only(self) -> None:
        def ocr_adapter(_raster: Path) -> dict[str, str]:
            return {
                "text": "OCR saw different textual evidence",
                "engine": "fixture_ocr",
                "engine_version": "1.0",
                "language": "en",
            }

        first = self.runner.prepare_pdf_page(
            self.pdf_rel,
            viewer="kira",
            activation_revision="test_activation_1",
            page_number=1,
            crop=(0.1, 0.1, 0.8, 0.8),
            zoom=1.25,
            ocr_provider=ocr_adapter,
        )
        evidence = self.read_evidence(first)
        self.assertEqual(first.name, "attempt_01")
        self.assertEqual(evidence["schema"], EVIDENCE_SCHEMA)
        self.assertEqual(
            evidence["source"]["sha256"], sha256_file(self.pdf_path)
        )
        page = evidence["preparation"]
        self.assertEqual(page["page_number"], 1)
        self.assertEqual(page["page_index_zero_based"], 0)
        raster_path = self.root / Path(page["raster"]["project_relative_path"])
        self.assertEqual(page["raster"]["sha256"], sha256_file(raster_path))
        self.assertEqual(
            page["ocr"]["source_raster_sha256"], page["raster"]["sha256"]
        )
        self.assertNotEqual(
            page["ocr"]["text_sha256"], page["pdf_text_layer"]["content_sha256"]
        )
        self.assertFalse(page["ocr"]["counts_as_visual_page_observation"])
        self.assertEqual(evidence["experience_session"]["page_observations"], [])

        second = self.runner.prepare_pdf_page(
            self.pdf_rel,
            viewer="kira",
            activation_revision="test_activation_1",
            page_number=2,
            presentation_receipt=self.receipt(
                visual=True,
                audio=False,
                modalities=["visual"],
                page_presented=5.0,
                page_observed=3.0,
            ),
        )
        self.assertEqual(second.name, "attempt_02")
        second_evidence = self.read_evidence(second)
        self.assertEqual(
            second_evidence["experience_session"]["page_observations"][0][
                "page_number"
            ],
            2,
        )
        self.assertTrue((first / "MANIFEST.json").is_file())
        self.assertTrue((second / "MANIFEST.json").is_file())

    def test_video_real_decode_tracks_timestamped_frames_audio_and_session_trace(self) -> None:
        attempt = self.runner.prepare_video_interval(
            self.video_rel,
            viewer="kira",
            activation_revision="test_activation_video",
            start_seconds=0.25,
            end_seconds=1.50,
            frame_count=3,
            pause_at_seconds=0.75,
            presentation_receipt=self.receipt(
                visual=True,
                audio=True,
                modalities=["audiovisual"],
            ),
        )
        evidence = self.read_evidence(attempt)
        preparation = evidence["preparation"]
        self.assertEqual(
            preparation["coverage"],
            "BOUNDED_VIDEO_INTERVAL_WITH_SAMPLED_VISUAL_FRAMES",
        )
        self.assertFalse(preparation["sampled_frames_equal_full_viewing"])
        self.assertFalse(preparation["full_source_watched_claim"])
        self.assertEqual(len(preparation["embedded_caption_streams"]), 1)
        self.assertEqual(
            preparation["embedded_caption_streams"][0]["language"], "eng"
        )
        self.assertIn(
            "mov_text",
            preparation["embedded_caption_streams"][0]["codec_description"],
        )
        self.assertEqual(len(preparation["video_frames"]), 3)
        for frame in preparation["video_frames"]:
            local = self.root / Path(frame["project_relative_path"])
            self.assertEqual(frame["sha256"], sha256_file(local))
            self.assertGreaterEqual(frame["decoded_pts_seconds"], 0.25)
            self.assertLessEqual(frame["decoded_pts_seconds"], 1.75)
        audio = preparation["audio_decode"]
        self.assertEqual(audio["status"], "DECODED_ACTUAL_PCM_SAMPLES")
        self.assertGreater(audio["decoded_sample_frames"], 0)
        self.assertTrue(audio["non_silent"])
        self.assertFalse(audio["raw_audio_stored"])
        events = [
            item["event_type"] for item in evidence["experience_session"]["events"]
        ]
        self.assertEqual(
            events,
            [
                "session_started",
                "playback_seeked",
                "playback_resumed",
                "playback_paused",
                "playback_resumed",
                "playback_paused",
                "media_interval_observed",
                "playback_finished",
                "session_closed",
            ],
        )
        observed = evidence["experience_session"]["playback"]["observed_intervals"]
        self.assertEqual(observed[0]["start_seconds"], 0.25)
        self.assertEqual(observed[0]["end_seconds"], 1.5)
        self.assertEqual(observed[0]["modality"], "audiovisual")

    def test_music_measurements_come_from_actual_samples_not_filename_metadata(self) -> None:
        attempt = self.runner.prepare_music_interval(
            self.music_rel,
            viewer="kira",
            activation_revision="test_activation_music",
            start_seconds=0.20,
            end_seconds=1.20,
            pause_at_seconds=0.70,
            presentation_receipt=self.receipt(
                visual=False,
                audio=True,
                modalities=["audio"],
            ),
        )
        evidence = self.read_evidence(attempt)
        preparation = evidence["preparation"]
        audio = preparation["audio_decode"]
        self.assertEqual(audio["decoded_sample_rate_hz"], 8000)
        self.assertEqual(audio["decoded_channels"], 2)
        self.assertAlmostEqual(audio["decoded_duration_seconds"], 1.0, places=3)
        self.assertGreater(audio["rms_full_scale"], 0.1)
        self.assertGreater(audio["peak_full_scale"], 0.2)
        self.assertEqual(len(audio["per_channel_rms_full_scale"]), 2)
        self.assertFalse(preparation["filename_or_metadata_counts_as_listening"])
        self.assertFalse(preparation["lyrics_counts_as_listening"])
        self.assertFalse(preparation["full_track_listened_claim"])
        observed = evidence["experience_session"]["playback"]["observed_intervals"]
        self.assertEqual(observed[0]["modality"], "audio")
        self.assertEqual(observed[0]["duration_seconds"], 1.0)

    def test_exact_correction_ledger_applies_latest_hash_bound_record(self) -> None:
        ledger = (
            self.root
            / "Data"
            / "owner_corrections"
            / "media_classification_corrections.jsonl"
        )
        store = MediaClassificationCorrectionStore(ledger)
        media_id = media_id_for_path(self.pdf_rel)
        source_hash = sha256_file(self.pdf_path)
        store.append_correction(
            media_id=media_id,
            file_sha256=source_hash,
            project_relative_library_path=self.pdf_rel,
            title="Illustrated issue",
            version="fixture",
            previous_access_category=GENERAL_LIBRARY_MEDIA,
            previous_classification_source="index_default_general_library",
            robert_exact_correction_text=(
                "This was marked general by mistake; it is explicit adult-only material."
            ),
            current_content_rating="UNRATED",
        )
        with self.assertRaisesRegex(Exception, "adult-scoped"):
            self.runner.prepare_pdf_page(
                self.pdf_rel,
                viewer="marinette",
                activation_revision="test_nonadult",
                page_number=1,
            )
        adult_attempt = self.runner.prepare_pdf_page(
            self.pdf_rel,
            viewer="kira",
            activation_revision="test_adult",
            page_number=1,
        )
        evidence = self.read_evidence(adult_attempt)
        binding = evidence["access_binding"]
        self.assertTrue(binding["exact_owner_correction_applied"])
        self.assertEqual(binding["owner_correction_append_sequence"], 1)
        self.assertEqual(
            binding["access_category"],
            EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT,
        )
        self.assertRegex(binding["owner_correction_record_sha256"], r"^[0-9a-f]{64}$")

    def test_nonadult_mature_video_requires_fresh_coview_not_prepare_bypass(self) -> None:
        with self.assertRaises(MediaPresentationAuthorizationRequired):
            self.runner.prepare_video_interval(
                self.video_rel,
                viewer="marinette",
                activation_revision="test_nonadult",
                start_seconds=0.0,
                end_seconds=1.0,
            )

    def test_schema_rejects_full_viewing_and_prepare_only_observation_claims(self) -> None:
        attempt = self.runner.prepare_music_interval(
            self.music_rel,
            viewer="kira",
            activation_revision="test_schema",
            start_seconds=0.0,
            end_seconds=0.5,
        )
        evidence = self.read_evidence(attempt)
        invalid = copy.deepcopy(evidence)
        invalid["preparation"]["full_track_listened_claim"] = True
        with self.assertRaises(SourceBoundMediaExperienceError):
            validate_evidence_document(invalid)
        invalid = copy.deepcopy(evidence)
        invalid["experience_session"]["playback"]["observed_intervals"] = [
            {
                "start_seconds": 0.0,
                "end_seconds": 0.5,
                "duration_seconds": 0.5,
                "modality": "audio",
            }
        ]
        with self.assertRaises(SourceBoundMediaExperienceError):
            validate_evidence_document(invalid)


if __name__ == "__main__":
    unittest.main()
