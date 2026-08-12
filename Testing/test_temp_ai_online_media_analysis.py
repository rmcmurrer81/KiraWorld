from __future__ import annotations

import json
import math
import shutil
import tempfile
import unittest
import wave
from array import array
from pathlib import Path

from Core.temp_ai_online_media_analysis import (
    MAX_RANGE_SECONDS,
    SAMPLE_RATE,
    analyze_pcm_wav,
    build_analysis_request,
    file_sha256,
    run_private_online_analysis,
    validate_analysis_request,
)


def write_test_wav(path: Path, *, tonal_background: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = array("h")
    duration = 5.0
    for index in range(round(SAMPLE_RATE * duration)):
        second = index / SAMPLE_RATE
        background = 500 * math.sin(2 * math.pi * 330 * second) if tonal_background else 0.0
        if 0.55 <= second < 2.15:
            speech = 7000 * math.sin(2 * math.pi * (190 + 25 * math.sin(second * 4)) * second)
        elif 2.75 <= second < 4.45:
            speech = 5800 * math.sin(2 * math.pi * (235 + 32 * math.sin(second * 3)) * second)
        else:
            speech = 0.0
        samples.append(round(max(-32767, min(32767, speech + background))))
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(SAMPLE_RATE)
        writer.writeframes(samples.tobytes())


class OnlineMediaAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.candidates = self.root / "candidates"
        self.candidate_id = "elsa_test_candidate"
        (self.candidates / self.candidate_id).mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def request(self, **changes):
        values = {
            "candidate_id": self.candidate_id,
            "source_url": "https://www.youtube.com/watch?v=U3J3gO9p7LM",
            "start_seconds": 0.0,
            "end_seconds": 5.0,
            "owner_authorized_private_analysis": True,
        }
        values.update(changes)
        return build_analysis_request(**values)

    @staticmethod
    def acquirer(request, output_dir):
        output_dir.mkdir(parents=True, exist_ok=False)
        media = output_dir / "bounded_source.mock"
        media.write_bytes(b"bounded mocked source/video bytes")
        metadata = output_dir / "bounded_source.info.json"
        metadata.write_text(
            json.dumps({"title": "Objective test source", "channel": "Test", "duration": 100}),
            encoding="utf-8",
        )
        return {
            "media_path": media,
            "metadata_path": metadata,
            "provider": "offline_mock_acquirer",
            "command_policy": {"no_playlist": True, "download_sections": "*0.000-5.000"},
        }

    @staticmethod
    def preparer(source, review_video, pcm_wav, duration):
        review_video.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, review_video)
        write_test_wav(pcm_wav)

    def test_explicit_owner_authority_is_required(self):
        with self.assertRaises(PermissionError):
            self.request(owner_authorized_private_analysis=False)

    def test_open_or_overlong_range_is_rejected(self):
        with self.assertRaises(ValueError):
            self.request(end_seconds=MAX_RANGE_SECONDS + 0.1)
        with self.assertRaises(ValueError):
            self.request(end_seconds=0.5)

    def test_forbidden_identity_or_runtime_authority_is_rejected(self):
        request = self.request()
        request["policy"]["voice_assignment_allowed"] = True
        with self.assertRaises(ValueError):
            validate_analysis_request(request, candidate_root=self.candidates)

    def test_offline_mock_run_hashes_source_video_audio_and_segments(self):
        result = run_private_online_analysis(
            self.request(),
            candidate_root=self.candidates,
            acquirer=self.acquirer,
            preparer=self.preparer,
        )
        self.assertEqual("objective_audio_preparation_complete_identity_unverified", result["status"])
        self.assertGreaterEqual(result["artifacts"]["segment_count"], 2)
        self.assertEqual(SAMPLE_RATE, result["artifacts"]["mono_16khz_pcm"]["sample_rate_hz"])
        for item in (
            result["source"]["bounded_media"],
            result["artifacts"]["bounded_review_video"],
            result["artifacts"]["mono_16khz_pcm"],
        ):
            path = Path(item["path"])
            self.assertTrue(path.is_file())
            self.assertEqual(item["sha256"], file_sha256(path))
        for segment in result["artifacts"]["segments"]:
            path = Path(segment["path"])
            self.assertTrue(path.is_file())
            self.assertEqual(segment["sha256"], file_sha256(path))
            self.assertEqual("unverified_no_identity_claim", segment["identity_status"])
            self.assertFalse(segment["model_input_allowed"])
        self.assertFalse(result["objective_review"]["speaker_identity_verified"])
        self.assertFalse(result["objective_review"]["overlap_cleared"])
        self.assertFalse(result["objective_review"]["eligible_for_direct_model_input"])
        self.assertFalse(result["authority_boundary"]["voice_training_or_cloning_performed"])
        self.assertFalse(result["authority_boundary"]["voice_assigned"])
        self.assertFalse(result["authority_boundary"]["voice_synthesized"])
        self.assertFalse(result["authority_boundary"]["candidate_activated"])
        self.assertFalse(result["authority_boundary"]["manual_400_clip_review_box_opened"])

    def test_acquirer_cannot_return_a_file_outside_private_run(self):
        escaped = self.root / "escape.mock"
        escaped.write_bytes(b"not allowed")

        def bad_acquirer(request, output_dir):
            output_dir.mkdir(parents=True, exist_ok=False)
            return {"media_path": escaped}

        with self.assertRaisesRegex(ValueError, "escaped"):
            run_private_online_analysis(
                self.request(),
                candidate_root=self.candidates,
                acquirer=bad_acquirer,
                preparer=self.preparer,
            )

    def test_tonality_is_only_a_contamination_proxy_not_identity_or_clearance(self):
        wav = self.root / "tonal.wav"
        write_test_wav(wav, tonal_background=True)
        diagnostics = analyze_pcm_wav(wav)
        pause = diagnostics["contamination_heuristics"]["pause_tonality"]
        self.assertEqual("possible_tonal_or_music_residue", pause["status"])
        self.assertFalse(pause["can_prove_no_music"])
        self.assertFalse(diagnostics["contamination_heuristics"]["overlap_proxy"]["can_clear_overlap"])


if __name__ == "__main__":
    unittest.main()
