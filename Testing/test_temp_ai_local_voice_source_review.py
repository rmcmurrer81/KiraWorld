from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_local_voice_source_review import (  # noqa: E402
    build_clean_range_review_queue,
    build_local_voice_source_review_manifest,
    resolve_library_voice_source,
)


class TempAILocalVoiceSourceReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.library = self.root / "Data" / "library"
        (self.library / "movies").mkdir(parents=True)
        self.primary = self.library / "movies" / "adult_present_pilot.mp4"
        self.supplement = self.library / "movies" / "earlier_movie.mp4"
        self.young_song = self.library / "movies" / "young_elsa_song.mp4"
        self.primary.write_bytes(b"primary adult present source")
        self.supplement.write_bytes(b"earlier supplement source")
        self.young_song.write_bytes(b"young song source")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def request(self) -> dict:
        return {
            "candidate_id": "test_character",
            "identity_target": {
                "character": {"character_id": "test_character", "label": "Test Character"},
                "variant": {"variant_id": "adult_present", "label": "Adult present"},
                "speaker": {"speaker_id": "adult_speaker", "label": "Adult speaker"},
                "performer": {"performer_id": "living_performer", "name": "Living Performer"},
            },
            "private_local_source_candidates": [
                {
                    "source_id": "adult_present_primary",
                    "path": str(self.primary),
                    "role": "primary adult-present voice source",
                    "selected_title": "Adult-present pilot",
                    "continuity_binding_status": "project_owner_selected_exact_continuity",
                },
                {
                    "source_id": "earlier_supplement",
                    "path": str(self.supplement),
                    "role": "earlier same-performer character delivery supplement",
                    "selected_title": "Earlier movie",
                },
                {
                    "source_id": "young_song",
                    "path": str(self.young_song),
                    "role": "selected continuity clip",
                    "selected_title": "Young Elsa childhood song",
                    "known_content_risks": ["mixed_speaker_risk"],
                },
            ],
        }

    @staticmethod
    def fake_probe(path: Path) -> dict:
        duration = 2700.0 if "pilot" in path.name else 300.0
        return {
            "status": "test_container_metadata",
            "duration_seconds": duration,
            "video_streams": [{"codec": "h264", "width": 640, "height": 360, "fps": 24.0}],
            "audio_streams": [{"codec": "aac", "sample_rate_hz": 44100, "channel_layout": "stereo"}],
        }

    def test_primary_adult_present_source_ranks_first_without_auto_selecting_speaker(self) -> None:
        with patch("Core.temp_ai_local_voice_source_review.PROJECT_ROOT", self.root), patch(
            "Core.temp_ai_local_voice_source_review.LIBRARY_ROOT", self.library
        ):
            manifest = build_local_voice_source_review_manifest(self.request(), probe=self.fake_probe)
        self.assertEqual(manifest["sources"][0]["source_id"], "adult_present_primary")
        self.assertGreater(
            manifest["sources"][0]["review_ranking"]["score"],
            manifest["sources"][1]["review_ranking"]["score"],
        )
        self.assertFalse(manifest["selection"]["source_auto_selected"])
        self.assertFalse(manifest["selection"]["speaker_or_acoustic_group_auto_selected"])
        self.assertFalse(manifest["operation_evidence"]["audio_played"])
        self.assertFalse(manifest["operation_evidence"]["voice_model_or_clone_run"])

    def test_song_and_young_variant_risks_are_explicit_and_lower_priority(self) -> None:
        with patch("Core.temp_ai_local_voice_source_review.PROJECT_ROOT", self.root), patch(
            "Core.temp_ai_local_voice_source_review.LIBRARY_ROOT", self.library
        ):
            manifest = build_local_voice_source_review_manifest(self.request(), probe=self.fake_probe)
        item = next(source for source in manifest["sources"] if source["source_id"] == "young_song")
        self.assertIn("song_or_music_dominant_source", item["known_content_risks"])
        self.assertIn("young_character_variant_risk", item["known_content_risks"])
        earlier = next(source for source in manifest["sources"] if source["source_id"] == "earlier_supplement")
        self.assertLess(
            item["review_ranking"]["raw_score_before_0_100_clamp"],
            earlier["review_ranking"]["raw_score_before_0_100_clamp"],
        )
        self.assertFalse(item["review_ranking"]["auto_select_speaker_or_acoustic_group"])
        contract = item["clean_range_review"]["speaker_selection_contract"]
        self.assertFalse(contract["diarization_or_acoustic_grouping_identifies_a_person"])
        self.assertTrue(contract["wrong_or_uncertain_group_must_remain_unselected"])

    def test_manifest_is_hash_bound_and_has_empty_bounded_range_queue(self) -> None:
        with patch("Core.temp_ai_local_voice_source_review.PROJECT_ROOT", self.root), patch(
            "Core.temp_ai_local_voice_source_review.LIBRARY_ROOT", self.library
        ):
            manifest = build_local_voice_source_review_manifest(self.request(), probe=self.fake_probe)
        item = manifest["sources"][0]
        self.assertRegex(item["integrity"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(item["clean_range_review"]["selected_ranges"], [])
        self.assertEqual(
            item["clean_range_review"]["status"],
            "needs_exact_bounded_ranges_and_human_audiovisual_review",
        )
        self.assertFalse(item["readiness"]["voice_reference_ready"])
        self.assertFalse(item["readiness"]["activation_ready"])
        queue = build_clean_range_review_queue(manifest)
        self.assertEqual(queue["selection"]["selected_ranges"], [])
        self.assertEqual(queue["selection"]["selected_speaker_or_acoustic_group"], "")
        self.assertFalse(queue["selection"]["automatic_selection_allowed"])
        self.assertFalse(queue["operations"]["diarization_run"])

    def test_declared_hash_mismatch_fails_closed(self) -> None:
        request = self.request()
        request["private_local_source_candidates"][0]["sha256"] = "0" * 64
        with patch("Core.temp_ai_local_voice_source_review.PROJECT_ROOT", self.root), patch(
            "Core.temp_ai_local_voice_source_review.LIBRARY_ROOT", self.library
        ):
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                build_local_voice_source_review_manifest(request, probe=self.fake_probe)

    def test_path_outside_library_is_rejected(self) -> None:
        outside = self.root / "outside.mp4"
        outside.write_bytes(b"outside")
        with patch("Core.temp_ai_local_voice_source_review.PROJECT_ROOT", self.root), patch(
            "Core.temp_ai_local_voice_source_review.LIBRARY_ROOT", self.library
        ):
            with self.assertRaisesRegex(ValueError, "confined"):
                resolve_library_voice_source(outside)


if __name__ == "__main__":
    unittest.main()
