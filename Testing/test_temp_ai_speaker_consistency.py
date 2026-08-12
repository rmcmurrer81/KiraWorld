from __future__ import annotations

import math
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_speaker_consistency import (  # noqa: E402
    AudioQualityPolicy,
    AudioRejectedError,
    BoundedWav,
    ConsistencyEvidenceError,
    analyze_speaker_consistency,
    capability_report,
    segment_on_silence,
)


class QueueEmbeddingBackend:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = list(vectors)
        self.calls = 0

    def embed(self, samples, sample_rate):
        self.calls += 1
        if sample_rate != 16_000:
            raise AssertionError("analyzer did not resample to 16 kHz")
        return self.vectors.pop(0)

    def metadata(self):
        return {
            "backend": "unit_test_mock",
            "model_id": "mock/speaker-vector",
            "requested_revision": "test-revision",
            "resolved_revision": "mock-commit-123",
            "local_files_only": True,
            "loaded": self.calls > 0,
            "embedding_dimension": 3,
        }


class TempAISpeakerConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_wav(self, name: str, *, seconds: float = 3.0, amplitude: float = 0.20) -> Path:
        path = self.root / name
        rate = 24_000
        values = [
            int(32767 * amplitude * math.sin(2 * math.pi * 220 * index / rate))
            for index in range(round(seconds * rate))
        ]
        with wave.open(str(path), "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(rate)
            writer.writeframes(struct.pack(f"<{len(values)}h", *values))
        return path

    def test_mocked_cross_source_comparison_emits_hashes_revision_and_no_actions(self) -> None:
        anchor_path = self.make_wav("anchor.wav")
        candidate_path = self.make_wav("candidate.wav", amplitude=0.18)
        backend = QueueEmbeddingBackend([[1.0, 0.0, 0.0], [0.98, 0.20, 0.0]])
        output_path = self.root / "evidence.json"

        result = analyze_speaker_consistency(
            anchor=BoundedWav(
                anchor_path, "movie_scene_a", owner_confirmed_target_only=True
            ),
            candidates=[BoundedWav(candidate_path, "interview_scene_b")],
            backend=backend,
            split_on_silence=False,
            output_path=output_path,
        )

        self.assertTrue(output_path.exists())
        self.assertRegex(result["anchor"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(result["model"]["resolved_revision"], "mock-commit-123")
        evidence = result["candidates"][0]["consistency_evidence"]
        self.assertEqual(evidence["status"], "computed")
        self.assertGreater(evidence["median_cosine_similarity"], 0.97)
        self.assertEqual(
            evidence["decision"], "speaker_consistency_supported_not_identity_proof"
        )
        self.assertRegex(
            evidence["candidate_embedding_hashes"][0]["embedding_sha256"],
            r"^[0-9a-f]{64}$",
        )
        limits = result["limits_and_actions"]
        self.assertFalse(limits["consistency_is_identity_proof"])
        self.assertFalse(limits["may_auto_approve_or_select_a_speaker"])
        self.assertFalse(limits["voice_assignment_performed"])
        self.assertFalse(limits["voice_clone_or_training_performed"])
        self.assertFalse(limits["temporary_ai_activation_performed"])

    def test_owner_confirmation_is_mandatory_before_model_is_called(self) -> None:
        anchor_path = self.make_wav("anchor.wav")
        candidate_path = self.make_wav("candidate.wav")
        backend = QueueEmbeddingBackend([[1.0, 0.0, 0.0]])
        with self.assertRaisesRegex(ConsistencyEvidenceError, "owner-confirmed"):
            analyze_speaker_consistency(
                anchor=BoundedWav(anchor_path, "a"),
                candidates=[BoundedWav(candidate_path, "b")],
                backend=backend,
                split_on_silence=False,
            )
        self.assertEqual(backend.calls, 0)

    def test_same_underlying_source_fails_closed(self) -> None:
        anchor_path = self.make_wav("anchor.wav")
        candidate_path = self.make_wav("candidate.wav")
        backend = QueueEmbeddingBackend([[1.0, 0.0, 0.0]])
        with self.assertRaisesRegex(ConsistencyEvidenceError, "different underlying"):
            analyze_speaker_consistency(
                anchor=BoundedWav(
                    anchor_path, "same_recording", owner_confirmed_target_only=True
                ),
                candidates=[BoundedWav(candidate_path, "same_recording")],
                backend=backend,
                split_on_silence=False,
            )
        self.assertEqual(backend.calls, 0)

    def test_short_anchor_is_rejected_before_model_is_called(self) -> None:
        anchor_path = self.make_wav("short.wav", seconds=0.5)
        candidate_path = self.make_wav("candidate.wav")
        backend = QueueEmbeddingBackend([[1.0, 0.0, 0.0]])
        with self.assertRaisesRegex(AudioRejectedError, "file_too_short"):
            analyze_speaker_consistency(
                anchor=BoundedWav(
                    anchor_path, "short_source", owner_confirmed_target_only=True
                ),
                candidates=[BoundedWav(candidate_path, "other_source")],
                backend=backend,
                split_on_silence=False,
            )
        self.assertEqual(backend.calls, 0)

    def test_quiet_candidate_is_recorded_as_rejected_without_embedding(self) -> None:
        anchor_path = self.make_wav("anchor.wav")
        quiet_path = self.make_wav("quiet.wav", amplitude=0.0001)
        backend = QueueEmbeddingBackend([[1.0, 0.0, 0.0]])
        result = analyze_speaker_consistency(
            anchor=BoundedWav(anchor_path, "a", owner_confirmed_target_only=True),
            candidates=[BoundedWav(quiet_path, "b")],
            backend=backend,
            split_on_silence=False,
        )
        self.assertEqual(backend.calls, 0)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["quality"]["status"], "rejected")
        self.assertIn("audio_too_quiet", candidate["quality"]["rejection_reasons"])
        self.assertEqual(
            candidate["consistency_evidence"]["status"], "rejected_before_embedding"
        )

    def test_identical_audio_with_different_source_labels_is_not_independent(self) -> None:
        shared_path = self.make_wav("same.wav")
        backend = QueueEmbeddingBackend([[1.0, 0.0, 0.0]])
        result = analyze_speaker_consistency(
            anchor=BoundedWav(shared_path, "declared_a", owner_confirmed_target_only=True),
            candidates=[BoundedWav(shared_path, "declared_b")],
            backend=backend,
            split_on_silence=False,
        )
        self.assertEqual(backend.calls, 0)
        candidate = result["candidates"][0]
        self.assertFalse(candidate["independent_source_from_anchor"])
        self.assertEqual(
            candidate["source_independence"]["status"],
            "rejected_same_audio_or_underlying_media",
        )
        self.assertEqual(candidate["consistency_evidence"]["decision"], "no_consistency_evidence")
        self.assertEqual(
            result["anchor"]["embedding_evidence"]["status"],
            "not_computed_no_eligible_independent_candidate",
        )

    def test_capability_check_does_not_load_or_download_model(self) -> None:
        report = capability_report(model_id="model/that-is-not-cached", revision="abc123")
        self.assertEqual(report["operation"], "speaker_consistency_capability_check")
        self.assertEqual(report["requested_revision"], "abc123")
        self.assertFalse(report["cache_ready"])
        self.assertEqual(report["safe_default"], "cache_only_no_download")
        self.assertFalse(report["voice_assignment_performed"])
        self.assertFalse(report["voice_clone_or_training_performed"])
        self.assertFalse(report["activation_performed"])

    def test_silence_segmentation_finds_two_long_regions(self) -> None:
        rate = 16_000
        tone = [0.2 * math.sin(2 * math.pi * 220 * index / rate) for index in range(2 * rate)]
        samples = tone + [0.0] * rate + tone
        ranges = segment_on_silence(samples, rate, AudioQualityPolicy())
        self.assertEqual(len(ranges), 2)
        self.assertGreater((ranges[0][1] - ranges[0][0]) / rate, 1.8)
        self.assertGreater((ranges[1][1] - ranges[1][0]) / rate, 1.8)

    def test_invalid_declared_source_hash_fails_before_embedding(self) -> None:
        anchor_path = self.make_wav("anchor.wav")
        candidate_path = self.make_wav("candidate.wav", amplitude=0.18)
        backend = QueueEmbeddingBackend([[1.0, 0.0, 0.0]])
        with self.assertRaisesRegex(ConsistencyEvidenceError, "64 hexadecimal"):
            analyze_speaker_consistency(
                anchor=BoundedWav(
                    anchor_path,
                    "a",
                    owner_confirmed_target_only=True,
                    source_media_sha256="not-a-hash",
                ),
                candidates=[BoundedWav(candidate_path, "b")],
                backend=backend,
                split_on_silence=False,
            )
        self.assertEqual(backend.calls, 0)


if __name__ == "__main__":
    unittest.main()
