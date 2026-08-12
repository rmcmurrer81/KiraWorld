from __future__ import annotations

import unittest
import json
import tempfile
import wave
from pathlib import Path

from Core.temp_ai_online_voice_nomination import (
    build_nomination_request,
    build_owner_attested_range_review,
    evaluate_machine_evidence,
    run_online_voice_nomination,
    validate_nomination_request,
)


KATHRYN_ID = "kathryn_merteuil_kathryn_merteuil_20260605_213017"
KATHRYN_URL = "https://youtu.be/yPPzi-TjE94?si=pptX5sL0Ei1x8t-p"


def request(**overrides):
    values = {
        "candidate_id": KATHRYN_ID,
        "target_name": "Kathryn Merteuil",
        "version": "Adult Kathryn continuation at the 2016 NBC unaired-pilot period",
        "speaker": "Kathryn Merteuil, 1999 English movie performance",
        "performer": "Sarah Michelle Gellar",
        "urls": [KATHRYN_URL],
        "start_seconds": 3.0,
        "owner_nominated_target_only": True,
        "owner_note": "Robert states everything after 3 seconds is Kathryn speaking.",
    }
    values.update(overrides)
    return build_nomination_request(**values)


def metadata(_url: str):
    return {
        "url": "https://www.youtube.com/watch?v=yPPzi-TjE94",
        "title": "Kathryn’s Monologue",
        "publisher": "Lesa",
        "publisher_url": "https://www.youtube.com/@iamlesa",
        "duration_seconds": 38,
        "discovery_provider": "youtube_metadata_via_yt_dlp",
    }


def passing_evidence():
    return {
        "source_url": "https://www.youtube.com/watch?v=yPPzi-TjE94",
        "range": {"start_seconds": 3.0, "end_seconds": 38.0},
        "provenance": {
            "media_sha256": "a" * 64,
            "analyzer": "test_active_speaker_pipeline",
            "analyzer_version": "1.0",
        },
        "face_identity": {
            "status": "matched_owner_approved_target_reference",
            "confidence": 0.98,
            "visible_ratio": 0.93,
            "reference_bundle_id": "kathryn_owner_approved_face_refs_v1",
            "reference_bundle_sha256": "b" * 64,
        },
        "active_speaker": {
            "status": "target_face_is_active_speaker",
            "confidence": 0.96,
            "coverage_ratio": 0.91,
        },
        "speaker_separation": {
            "max_simultaneous_speakers": 1,
            "overlap_ratio": 0.01,
            "confidence": 0.97,
        },
        "audio_quality": {
            "speech_ratio": 0.9,
            "music_probability": 0.01,
            "noise_probability": 0.04,
            "snr_db": 25.0,
            "clipping_ratio": 0.0001,
        },
    }


class OnlineVoiceNominationTests(unittest.TestCase):
    def test_search_only_request_can_start_without_owner_seed_url(self):
        value = request(
            urls=[],
            owner_nominated_target_only=False,
            search_queries=["Kathryn Merteuil Sarah Michelle Gellar official spoken dialogue"],
        )
        validate_nomination_request(value, expected_candidate_id=KATHRYN_ID)

        def search(_query: str, _limit: int):
            return [
                {
                    "url": "https://www.youtube.com/watch?v=abcdefghijk",
                    "title": "Kathryn Merteuil dialogue scene",
                    "publisher": "Official Studio",
                    "duration_seconds": 30,
                    "discovery_provider": "youtube_metadata_via_yt_dlp",
                }
            ]

        result = run_online_voice_nomination(value, metadata_search=True, video_search=search)
        self.assertEqual(1, len(result["ranked_target_only_candidate_ranges"]))
        self.assertEqual(
            "https://www.youtube.com/watch?v=abcdefghijk",
            result["ranked_target_only_candidate_ranges"][0]["exact_url"],
        )
        self.assertFalse(result["selection"]["source_approved"])

    def test_search_only_request_fails_without_metadata_search(self):
        value = request(
            urls=[],
            owner_nominated_target_only=False,
            search_queries=["Kathryn official dialogue"],
        )
        with self.assertRaisesRegex(ValueError, "metadata_search is required"):
            run_online_voice_nomination(value, metadata_search=False)

    def test_request_canonicalizes_youtube_url_and_preserves_exact_identity(self):
        value = request()
        self.assertEqual(value["sources"][0]["url"], "https://www.youtube.com/watch?v=yPPzi-TjE94")
        self.assertEqual(value["identity_target"]["target_name"], "Kathryn Merteuil")
        self.assertEqual(value["sources"][0]["nominated_start_seconds"], 3.0)
        validate_nomination_request(value, expected_candidate_id=KATHRYN_ID)

    def test_owner_source_becomes_top_candidate_but_fails_closed_without_machine_evidence(self):
        result = run_online_voice_nomination(request(), metadata_search=True, direct_metadata=metadata)
        top = result["ranked_target_only_candidate_ranges"][0]
        self.assertEqual(top["candidate_range"]["start_seconds"], 3.0)
        self.assertEqual(top["candidate_range"]["end_seconds"], 38.0)
        self.assertFalse(top["machine_evidence_gate"]["passed"])
        self.assertFalse(top["target_only_approved"])
        self.assertFalse(result["selection"]["voice_assigned"])
        self.assertFalse(result["operation_evidence"]["media_downloaded"])

    def test_complete_exact_bound_machine_evidence_can_pass_candidate_gate_only(self):
        result = run_online_voice_nomination(
            request(), metadata_search=True, direct_metadata=metadata, machine_evidence=[passing_evidence()]
        )
        top = result["ranked_target_only_candidate_ranges"][0]
        self.assertTrue(top["machine_evidence_gate"]["passed"])
        self.assertEqual(top["status"], "machine_target_only_candidate_not_human_approved")
        self.assertFalse(top["target_only_approved"])
        self.assertFalse(result["selection"]["voice_trained_or_cloned"])
        self.assertFalse(result["selection"]["candidate_activated"])

    def test_music_or_overlap_fails_machine_gate(self):
        evidence = passing_evidence()
        evidence["audio_quality"]["music_probability"] = 0.4
        evidence["speaker_separation"]["overlap_ratio"] = 0.3
        gate = evaluate_machine_evidence(evidence)
        self.assertFalse(gate["passed"])
        self.assertIn("single-speaker and overlap rejection", gate["failed_gates"])
        self.assertIn("music/noise/clipping quality", gate["failed_gates"])

    def test_mismatched_range_evidence_is_not_applied(self):
        evidence = passing_evidence()
        evidence["range"]["start_seconds"] = 4.0
        result = run_online_voice_nomination(
            request(), metadata_search=True, direct_metadata=metadata, machine_evidence=[evidence]
        )
        self.assertFalse(result["ranked_target_only_candidate_ranges"][0]["machine_evidence_gate"]["passed"])

    def test_request_rejects_forbidden_download_or_assignment_flags(self):
        value = request()
        value["policy"]["allow_media_download"] = True
        with self.assertRaisesRegex(ValueError, "cannot enable"):
            validate_nomination_request(value)

    def test_explicit_range_over_45_seconds_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            request(end_seconds=60.0)

    def test_search_result_music_title_is_penalized(self):
        def search(_query: str, _limit: int):
            return [
                {
                    "url": "https://www.youtube.com/watch?v=abcdefghijk",
                    "title": "Kathryn Merteuil Official Song Karaoke Lyrics",
                    "publisher": "fan upload",
                    "duration_seconds": 30,
                    "discovery_provider": "youtube_metadata_via_yt_dlp",
                }
            ]

        value = request(search_queries=["Kathryn Merteuil dialogue"])
        result = run_online_voice_nomination(
            value, metadata_search=True, direct_metadata=metadata, video_search=search
        )
        candidates = result["ranked_target_only_candidate_ranges"]
        self.assertEqual(candidates[0]["exact_url"], "https://www.youtube.com/watch?v=yPPzi-TjE94")
        music = next(item for item in candidates if "abcdefghijk" in item["exact_url"])
        self.assertTrue(music["metadata_checks"]["music_terms"])
        self.assertLess(music["ranking"]["score"], candidates[0]["ranking"]["score"])

    def test_explicit_seed_outranks_unreviewed_parody_search_noise(self):
        value = request(owner_nominated_target_only=False, search_queries=["Kathryn dialogue"])

        def search(_query: str, _limit: int):
            return [
                {
                    "url": "https://www.youtube.com/watch?v=abcdefghijk",
                    "title": "Kathryn Sarah Performer #WITHOUTMUSIC Parody",
                    "publisher": "fan upload",
                    "duration_seconds": 30,
                    "discovery_provider": "youtube_metadata_via_yt_dlp",
                }
            ]

        result = run_online_voice_nomination(
            value, metadata_search=True, direct_metadata=metadata, video_search=search
        )
        candidates = result["ranked_target_only_candidate_ranges"]
        self.assertEqual(candidates[0]["exact_url"], "https://www.youtube.com/watch?v=yPPzi-TjE94")
        parody = next(item for item in candidates if "abcdefghijk" in item["exact_url"])
        self.assertIn("parody", parody["metadata_checks"]["music_terms"])
        self.assertIn("withoutmusic", parody["metadata_checks"]["music_terms"])

    def test_explicit_seed_outranks_plausible_official_search_lead_without_machine_evidence(self):
        value = request(owner_nominated_target_only=False, search_queries=["Kathryn dialogue"])

        def sparse_seed_metadata(_url: str):
            return {
                "url": "https://www.youtube.com/watch?v=yPPzi-TjE94",
                "title": "Dressing Room Deleted Scene",
                "publisher": "Official Studio",
                "duration_seconds": 5,
                "discovery_provider": "youtube_metadata_via_yt_dlp",
            }

        def search(_query: str, _limit: int):
            return [
                {
                    "url": "https://www.youtube.com/watch?v=abcdefghijk",
                    "title": "Kathryn Merteuil Sarah Michelle Gellar Monologue",
                    "publisher": "Official Studio",
                    "duration_seconds": 30,
                    "discovery_provider": "youtube_metadata_via_yt_dlp",
                }
            ]

        result = run_online_voice_nomination(
            value,
            metadata_search=True,
            direct_metadata=sparse_seed_metadata,
            video_search=search,
        )
        candidates = result["ranked_target_only_candidate_ranges"]
        self.assertEqual("https://www.youtube.com/watch?v=yPPzi-TjE94", candidates[0]["exact_url"])
        self.assertIn("explicit source seed", " ".join(candidates[0]["ranking"]["reasons"]))

    def test_pcm_quality_and_owner_attestation_can_replace_clip_box_for_exact_range(self):
        result = run_online_voice_nomination(request(), metadata_search=True, direct_metadata=metadata)
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=project_root) as temp:
            root = Path(temp)
            media = root / "source.mp4"
            media.write_bytes(b"bounded test media bytes")
            wav = root / "range.wav"
            rate = 24000
            with wave.open(str(wav), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(rate)
                # Six seconds of non-clipping tone/noise variation is sufficient
                # for the diagnostics contract; the range is overridden below.
                samples = bytearray()
                import math
                import struct
                for index in range(rate * 6):
                    amplitude = 50 if index < rate else 3000
                    value = int(amplitude * math.sin(2 * math.pi * 190 * index / rate))
                    samples.extend(struct.pack("<h", value))
                output.writeframes(bytes(samples))
            attestation = root / "attestation.json"
            attestation.write_text(
                json.dumps(
                    {
                        "authorized_by": "real_robert",
                        "source_url": "https://www.youtube.com/watch?v=yPPzi-TjE94",
                        "range": {"start_seconds": 3.0, "end_seconds": 9.0},
                        "audiovisual_source_reviewed": True,
                        "target_identity_confirmed": True,
                        "target_only_speech_confirmed": True,
                        "no_other_speaker_confirmed": True,
                        "no_overlap_confirmed": True,
                        "no_music_confirmed": True,
                        "scope": "private_source_review_evidence_only_no_model_or_runtime_authority",
                    }
                ),
                encoding="utf-8",
            )
            from Core.temp_ai_online_voice_nomination import file_sha256
            contamination = root / "contamination.json"
            contamination.write_text(
                json.dumps(
                    {
                        "source_url": "https://www.youtube.com/watch?v=yPPzi-TjE94",
                        "range": {"start_seconds": 3.0, "end_seconds": 9.0},
                        "wav_sha256": file_sha256(wav),
                        "analyzer": "test_contamination_analyzer",
                        "analyzer_version": "1.0",
                        "background_tonal_or_music_residue_detected": False,
                        "material_noise_detected": False,
                        "overlap_detected": False,
                        "clean_for_direct_model_input": True,
                    }
                ),
                encoding="utf-8",
            )
            # Rebind the nomination to the six-second fixture range.
            result["ranked_target_only_candidate_ranges"][0]["candidate_range"]["end_seconds"] = 9.0
            result["ranked_target_only_candidate_ranges"][0]["candidate_range"]["duration_seconds"] = 6.0
            review = build_owner_attested_range_review(
                result,
                source_url="https://www.youtube.com/watch?v=yPPzi-TjE94",
                start_seconds=3.0,
                end_seconds=9.0,
                local_media_path=media,
                local_wav_path=wav,
                owner_attestation_path=attestation,
                contamination_evidence_path=contamination,
            )
            self.assertTrue(review["owner_attestation"]["passed"])
            self.assertTrue(review["automatic_audio_diagnostics"]["quality_gate"]["passed"])
            self.assertTrue(review["eligible_for_private_reference_pack_input"])
            self.assertFalse(review["manual_clip_by_clip_box_required_for_this_exact_range"])
            self.assertFalse(review["model_or_runtime_authority"]["voice_assignment_allowed"])

            contaminated = json.loads(contamination.read_text(encoding="utf-8"))
            contaminated["background_tonal_or_music_residue_detected"] = True
            contaminated["clean_for_direct_model_input"] = False
            contaminated["findings"] = ["faint tonal/background-score residue"]
            contamination.write_text(json.dumps(contaminated), encoding="utf-8")
            blocked = build_owner_attested_range_review(
                result,
                source_url="https://www.youtube.com/watch?v=yPPzi-TjE94",
                start_seconds=3.0,
                end_seconds=9.0,
                local_media_path=media,
                local_wav_path=wav,
                owner_attestation_path=attestation,
                contamination_evidence_path=contamination,
            )
            self.assertTrue(blocked["candidate_reference_evidence_ready"])
            self.assertTrue(blocked["eligible_for_cleanup_and_qc_workbench"])
            self.assertFalse(blocked["eligible_for_private_reference_pack_input"])
            self.assertIn("cleanup_and_qc_required", blocked["status"])


if __name__ == "__main__":
    unittest.main()
