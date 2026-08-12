from __future__ import annotations

import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_local_media_intake import (  # noqa: E402
    INTAKE_RELATIVE,
    build_intake_request,
    build_review_template,
    discover_queued_requests,
    extract_candidate_pack,
    promote_reviewed_evidence,
    request_payload_sha256,
    validate_intake_request,
)


class TempAILocalMediaIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.candidate_root = self.root / "TemporaryAI" / "candidates"
        self.library_root = self.root / "Data" / "library"
        self.candidate_id = "test_character"
        (self.candidate_root / self.candidate_id).mkdir(parents=True)
        self.source = self.library_root / "movies" / "test_movie.mp4"
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b"private-local-test-media" * 40)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def request(self, *, ranges=None, authorized=True):
        return build_intake_request(
            candidate_id=self.candidate_id,
            source_path=self.source,
            character_label="Test Character",
            variant_label="Movie Version",
            speaker_label="Test Character Movie Speaker",
            performer_label="Test Performer",
            evidence_types=["voice", "movement"],
            scene_ranges=ranges or [],
            private_local_use_authorized=authorized,
            authorized_by="real_robert" if authorized else "",
            authorization_note="Private local reference preparation authorized.",
            request_label="test_private_local_request",
            candidate_root=self.candidate_root,
            library_root=self.library_root,
        )

    @staticmethod
    def ranges():
        return [
            {
                "start_seconds": 10,
                "end_seconds": 22,
                "evidence_types": ["voice", "movement"],
                "scene_note": "Target scene selected for review.",
            }
        ]

    def test_request_without_ranges_is_draft_and_cannot_extract(self) -> None:
        request = self.request(ranges=[])
        self.assertEqual(request["status"], "draft_needs_bounded_scene_ranges")
        self.assertFalse(request["action_boundaries"]["bounded_candidate_clip_extraction_allowed"])
        with self.assertRaisesRegex(ValueError, "queued request"):
            extract_candidate_pack(
                request,
                candidate_root=self.candidate_root,
                library_root=self.library_root,
            )

    def test_source_must_remain_inside_private_library(self) -> None:
        outside = self.root / "outside.mp4"
        outside.write_bytes(b"outside")
        with self.assertRaisesRegex(ValueError, "under"):
            build_intake_request(
                candidate_id=self.candidate_id,
                source_path=outside,
                character_label="Test Character",
                variant_label="Movie Version",
                speaker_label="Test Speaker",
                performer_label="Test Performer",
                scene_ranges=self.ranges(),
                private_local_use_authorized=True,
                authorized_by="real_robert",
                candidate_root=self.candidate_root,
                library_root=self.library_root,
            )

    def test_long_or_open_ended_source_extraction_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "45-second"):
            self.request(ranges=[{"start_seconds": 0, "end_seconds": 46, "evidence_types": ["voice"]}])
        with self.assertRaisesRegex(ValueError, "shorter"):
            self.request(ranges=[{"start_seconds": 3, "end_seconds": 3, "evidence_types": ["voice"]}])

    def test_request_hash_and_source_hash_are_fail_closed(self) -> None:
        request = self.request(ranges=self.ranges())
        tampered = deepcopy(request)
        tampered["identity_target"]["speaker"]["label"] = "Wrong Speaker"
        with self.assertRaisesRegex(ValueError, "payload hash"):
            validate_intake_request(
                tampered,
                candidate_root=self.candidate_root,
                library_root=self.library_root,
                verify_source_hash=False,
            )
        self.source.write_bytes(b"changed-source")
        with self.assertRaisesRegex(ValueError, "size changed|SHA-256 changed"):
            validate_intake_request(
                request,
                candidate_root=self.candidate_root,
                library_root=self.library_root,
            )

    def test_bounded_extraction_outputs_unreviewed_candidates_only(self) -> None:
        request = self.request(ranges=self.ranges())

        def fake_extractor(source, segment, output_dir):
            segment_dir = output_dir / segment["segment_id"]
            segment_dir.mkdir()
            voice = segment_dir / "candidate.wav"
            movement = segment_dir / "candidate.mp4"
            voice.write_bytes(b"voice candidate")
            movement.write_bytes(b"movement candidate")
            return {"voice_wav": voice, "movement_review_mp4": movement}

        manifest = extract_candidate_pack(
            request,
            candidate_root=self.candidate_root,
            library_root=self.library_root,
            extractor=fake_extractor,
        )
        self.assertEqual(manifest["status"], "candidate_segments_extracted_pending_human_review")
        self.assertEqual(manifest["segments"][0]["evidence_status"], "unreviewed_candidate")
        self.assertFalse(manifest["outputs"]["voice_model_or_clone_created"])
        self.assertFalse(manifest["outputs"]["temporary_ai_activated"])

    def _pack_and_review(self):
        request = self.request(ranges=self.ranges())

        def fake_extractor(source, segment, output_dir):
            segment_dir = output_dir / segment["segment_id"]
            segment_dir.mkdir()
            voice = segment_dir / "candidate.wav"
            movement = segment_dir / "candidate.mp4"
            voice.write_bytes(b"voice candidate")
            movement.write_bytes(b"movement candidate")
            return {"voice_wav": voice, "movement_review_mp4": movement}

        manifest = extract_candidate_pack(
            request,
            candidate_root=self.candidate_root,
            library_root=self.library_root,
            extractor=fake_extractor,
        )
        pack_dir = self.candidate_root / self.candidate_id / INTAKE_RELATIVE / "packs" / request["request_id"]
        review = build_review_template(manifest)
        item = review["segments"][0]
        item["human_identity_review"].update(
            {
                "reviewed": True,
                "reviewer": "real_robert",
                "reviewed_at": "2026-07-16T12:00:00+00:00",
                "target_character_confirmed": True,
                "target_variant_confirmed": True,
                "target_speaker_confirmed": True,
                "target_performer_confirmed": True,
                "identity_basis": ["human_audio_visual_scene_review", "production_credit_or_cast_record"],
            }
        )
        item["diarization_aid"].update(
            {"status": "reviewed_group_consistent", "used_as_aid_only_not_identity_proof": True}
        )
        return pack_dir, review

    def test_overlap_or_music_cannot_be_promoted_as_voice_evidence(self) -> None:
        pack_dir, review = self._pack_and_review()
        voice = review["segments"][0]["voice_review"]
        voice.update(
            {
                "decision": "approve_voice_reference",
                "target_only_speech": True,
                "overlapping_speech": True,
                "music_present": False,
                "narration_present": False,
                "material_sound_effects_present": False,
                "stable_character_delivery": True,
            }
        )
        result = promote_reviewed_evidence(pack_dir, review, library_root=self.library_root)
        self.assertFalse(result["readiness"]["voice_reference_evidence_ready"])
        blockers = " ".join(result["decisions"][0]["voice_blockers"])
        self.assertIn("overlapping speech", blockers)

    def test_clean_human_identified_voice_and_movement_can_be_evidence(self) -> None:
        pack_dir, review = self._pack_and_review()
        review["segments"][0]["voice_review"].update(
            {
                "decision": "approve_voice_reference",
                "target_only_speech": True,
                "overlapping_speech": False,
                "music_present": False,
                "narration_present": False,
                "material_sound_effects_present": False,
                "stable_character_delivery": True,
            }
        )
        review["segments"][0]["movement_review"].update(
            {
                "decision": "approve_movement_reference",
                "target_visible": True,
                "target_track_confirmed": True,
                "material_occlusion": False,
                "shot_cuts_confuse_motion": False,
                "movement_is_performer_evidence_not_character_memory": True,
            }
        )
        result = promote_reviewed_evidence(pack_dir, review, library_root=self.library_root)
        self.assertTrue(result["readiness"]["voice_reference_evidence_ready"])
        self.assertTrue(result["readiness"]["movement_reference_evidence_ready"])
        self.assertFalse(result["readiness"]["voice_clone_or_training_performed"])
        self.assertFalse(result["readiness"]["temporary_ai_activation_performed"])

    def test_changed_extracted_artifact_cannot_be_promoted(self) -> None:
        pack_dir, review = self._pack_and_review()
        manifest = json.loads((pack_dir / "candidate_pack_manifest.json").read_text(encoding="utf-8"))
        artifact_path = Path(manifest["segments"][0]["artifacts"]["voice_wav"]["path"])
        artifact_path.write_bytes(b"tampered after extraction")
        with self.assertRaisesRegex(ValueError, "artifact is missing or changed"):
            promote_reviewed_evidence(pack_dir, review, library_root=self.library_root)

    def test_duplicate_segment_review_is_rejected(self) -> None:
        pack_dir, review = self._pack_and_review()
        review["segments"].append(deepcopy(review["segments"][0]))
        with self.assertRaisesRegex(ValueError, "every extracted segment exactly once"):
            promote_reviewed_evidence(pack_dir, review, library_root=self.library_root)

    def test_queue_is_bounded_and_skips_drafts(self) -> None:
        request = self.request(ranges=self.ranges())
        request_dir = self.candidate_root / self.candidate_id / INTAKE_RELATIVE / "requests"
        request_dir.mkdir(parents=True)
        (request_dir / "queued.json").write_text(json.dumps(request), encoding="utf-8")
        draft = deepcopy(request)
        draft["request_id"] = "draft_request"
        draft["status"] = "draft_needs_bounded_scene_ranges"
        draft["scene_ranges"] = []
        draft["limits"]["requested_total_seconds"] = 0
        draft["action_boundaries"]["bounded_candidate_clip_extraction_allowed"] = False
        draft["integrity"]["request_payload_sha256"] = request_payload_sha256(draft)
        (request_dir / "draft.json").write_text(json.dumps(draft), encoding="utf-8")
        selected = discover_queued_requests(candidate_root=self.candidate_root, max_requests=1)
        self.assertEqual(selected, [request_dir / "queued.json"])
        with self.assertRaisesRegex(ValueError, "between 1 and 3"):
            discover_queued_requests(candidate_root=self.candidate_root, max_requests=4)


if __name__ == "__main__":
    unittest.main()
