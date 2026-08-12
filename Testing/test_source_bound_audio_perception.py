from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import tempfile
import unittest
import wave
from dataclasses import replace
from pathlib import Path

from Core import source_bound_audio_perception as audio


def sine_pcm_f32(
    *,
    seconds: float = 2.0,
    sample_rate: int = 16_000,
    frequency: float = 440.0,
    amplitude_mod_hz: float | None = None,
) -> bytes:
    frames = round(seconds * sample_rate)
    values = []
    for index in range(frames):
        t = index / sample_rate
        envelope = (
            0.25 + 0.75 * max(0.0, math.sin(2.0 * math.pi * amplitude_mod_hz * t))
            if amplitude_mod_hz
            else 1.0
        )
        values.append(0.35 * envelope * math.sin(2.0 * math.pi * frequency * t))
    return struct.pack("<" + "f" * len(values), *values)


def pcm16_from_floats(values: list[float]) -> bytes:
    return struct.pack(
        "<" + "h" * len(values),
        *(max(-32768, min(32767, round(value * 32767))) for value in values),
    )


def binding(*, hint: str = "speech_or_lyrics", source_hash: str = "a" * 64):
    return audio.AudioIntervalBinding(
        stimulus_id="fixture_interval_000_002",
        project_relative_library_path="Data/library/test/fixture.wav",
        source_sha256=source_hash,
        opaque_media_id="opaque_fixture",
        start_seconds=0.0,
        end_seconds=2.0,
        content_hint=hint,
    )


class FakeAsr:
    def __init__(self) -> None:
        self.calls = 0

    def transcribe(self, wav_bytes: bytes):
        self.calls += 1
        self.last_wav_sha256 = hashlib.sha256(wav_bytes).hexdigest()
        return {
            "text": "possible quoted words",
            "segments": [
                {"start_seconds": 0.2, "end_seconds": 0.8, "text": "possible quoted words"}
            ],
            "language": "en",
            "language_probability": 0.83,
            "model_id": audio.ASR_MODEL_ID,
            "model_binary_sha256": audio.ASR_MODEL_BINARY_SHA256,
            "device": "cpu",
        }


class SourceBoundAudioPerceptionTests(unittest.TestCase):
    def make_window(
        self,
        *,
        hint: str = "speech_or_lyrics",
        frequency: float = 440.0,
        amplitude_mod_hz: float | None = 2.0,
    ) -> audio.TransientDecodedAudio:
        return audio.TransientDecodedAudio(
            binding=binding(hint=hint),
            sample_rate_hz=16_000,
            channels=1,
            stream_index=0,
            pcm_f32le=sine_pcm_f32(
                frequency=frequency,
                amplitude_mod_hz=amplitude_mod_hz,
            ),
        )

    def test_binding_rejects_invalid_hash_interval_and_content_hint(self) -> None:
        with self.assertRaises(audio.SourceBoundAudioError):
            binding(source_hash="bad").validate()
        invalid_interval = replace(binding(), end_seconds=50.0)
        with self.assertRaises(audio.SourceBoundAudioError):
            invalid_interval.validate()
        with self.assertRaises(audio.SourceBoundAudioError):
            binding(hint="infer_it_from_filename").validate()

    def test_transient_pcm_is_not_serializable_and_wipes(self) -> None:
        window = self.make_window()
        self.assertNotIn("bytearray", repr(window))
        self.assertGreater(window.sample_frames, 0)
        with self.assertRaises(TypeError):
            json.dumps(window)
        window.close()
        self.assertTrue(window.closed)
        with self.assertRaises(audio.SourceBoundAudioError):
            _ = window.pcm_sha256

    def test_actual_pcm_features_cover_waveform_spectrum_rhythm_and_dynamics(self) -> None:
        with self.make_window() as window:
            result = audio.measure_actual_audio_features(window)
        self.assertEqual(
            result["measurement_basis"],
            "actual_decoded_pcm_samples_not_filename_or_metadata",
        )
        self.assertTrue(result["waveform"]["non_silent"])
        self.assertGreater(result["waveform"]["rms_full_scale"], 0.01)
        self.assertGreater(result["spectral"]["mean_centroid_hz"], 300)
        self.assertLess(result["spectral"]["mean_centroid_hz"], 800)
        self.assertGreater(result["rhythm"]["onset_count"], 0)
        self.assertIn("tempo_bpm_estimate", result["rhythm"])
        self.assertIn("dynamic_range_p90_p10_db", result["dynamics"])
        self.assertEqual(len(result["spectral"]["band_power_ratios"]), 8)
        self.assertFalse(result["decoded_pcm"]["raw_pcm_stored"])

    def test_cached_asr_is_content_gated_and_always_unknown_speaker(self) -> None:
        fake = FakeAsr()
        with self.make_window() as window:
            cue = audio.build_source_bound_audio_cue(window, asr_adapter=fake)
        self.assertEqual(fake.calls, 1)
        self.assertEqual(
            cue["asr"]["status"],
            "COMPLETED_UNTRUSTED_POSSIBLE_SPEECH_OR_LYRICS",
        )
        self.assertEqual(
            cue["asr"]["speaker_identity"],
            "UNKNOWN_SPEAKER_NOT_INFERRED_FROM_ASR",
        )
        self.assertFalse(cue["asr"]["instruction_authority"])
        self.assertFalse(cue["asr"]["semantic_truth_verified"])
        self.assertFalse(cue["claim_boundaries"]["memory_created"])
        self.assertFalse(cue["claim_boundaries"]["liking_inferred"])
        audio.validate_audio_cue_bundle(cue)

    def test_asr_does_not_run_for_non_speech_content(self) -> None:
        fake = FakeAsr()
        with self.make_window(hint="non_speech") as window:
            cue = audio.build_source_bound_audio_cue(window, asr_adapter=fake)
        self.assertEqual(fake.calls, 0)
        self.assertEqual(
            cue["asr"]["status"],
            "NOT_RUN_CONTENT_NOT_DECLARED_SPEECH_OR_LYRICS",
        )

    def test_asr_segment_cannot_escape_exact_interval(self) -> None:
        class BadAsr:
            @staticmethod
            def transcribe(_wav: bytes):
                return {
                    "text": "outside",
                    "segments": [{"start": 0.0, "end": 9.0, "text": "outside"}],
                    "language": "en",
                    "language_probability": 1.0,
                }

        with self.make_window() as window:
            with self.assertRaisesRegex(audio.SourceBoundAudioError, "escaped"):
                audio.build_source_bound_audio_cue(window, asr_adapter=BadAsr())

    def test_asr_adapter_cannot_substitute_another_model_or_gpu_route(self) -> None:
        class SubstituteAsr:
            @staticmethod
            def transcribe(_wav: bytes):
                return {
                    "text": "substitute",
                    "segments": [],
                    "language": "en",
                    "language_probability": 1.0,
                    "model_id": "another/model",
                    "model_binary_sha256": "b" * 64,
                    "device": "cuda",
                }

        with self.make_window() as window:
            with self.assertRaisesRegex(audio.SourceBoundAudioError, "model pin"):
                audio.build_source_bound_audio_cue(
                    window, asr_adapter=SubstituteAsr()
                )

    def test_audio_cue_self_hash_rejects_tampering(self) -> None:
        with self.make_window() as window:
            cue = audio.build_source_bound_audio_cue(window)
        cue["features"]["waveform"]["rms_full_scale"] = 0.999
        with self.assertRaisesRegex(audio.SourceBoundAudioError, "self-hash"):
            audio.validate_audio_cue_bundle(cue)

    def test_no_device_provider_plays_once_and_makes_no_capture_claim(self) -> None:
        called: list[str] = []
        attempt = audio.NoDeviceCaptureProvider().capture_during(
            playback=lambda: called.append("played"),
            expected_playback_seconds=2.0,
        )
        self.assertEqual(called, ["played"])
        self.assertIsNone(attempt.captured)
        with self.make_window() as window:
            result = audio.verify_local_capture(reference=window, attempt=attempt)
        self.assertEqual(result["verification_status"], "NOT_AVAILABLE")
        self.assertFalse(result["physical_output_at_capture_device_supported"])
        self.assertFalse(result["biological_hearing_supported"])

    def test_matching_local_capture_supports_output_not_biological_hearing(self) -> None:
        source_values = [
            0.35 * math.sin(2 * math.pi * 440 * index / 16_000)
            for index in range(32_000)
        ]
        pre_roll = [0.0] * 4_000
        capture = audio.TransientCapturedPcm16(
            device_id="mock exact microphone",
            started_at_utc="2026-08-02T12:00:00.000000Z",
            ended_at_utc="2026-08-02T12:00:03.000000Z",
            pcm16le=pcm16_from_floats(pre_roll + source_values),
        )
        attempt = audio.CaptureAttempt(
            status="CAPTURE_COMPLETED_RAW_PCM_TRANSIENT",
            provider="mock_capture",
            device_id="mock exact microphone",
            started_at_utc="2026-08-02T12:00:00.000000Z",
            ended_at_utc="2026-08-02T12:00:03.000000Z",
            diagnostic="test",
            captured=capture,
        )
        with self.make_window(amplitude_mod_hz=None) as window:
            result = audio.verify_local_capture(reference=window, attempt=attempt)
        capture.close()
        self.assertTrue(result["physical_output_at_capture_device_supported"])
        self.assertFalse(result["biological_hearing_supported"])
        self.assertFalse(result["person_attention_supported"])

    def test_unrelated_local_capture_does_not_support_source_output(self) -> None:
        other_values = [
            0.25 * math.sin(2 * math.pi * 2600 * index / 16_000)
            for index in range(32_000)
        ]
        capture = audio.TransientCapturedPcm16(
            device_id="mock exact microphone",
            started_at_utc="2026-08-02T12:00:00.000000Z",
            ended_at_utc="2026-08-02T12:00:02.000000Z",
            pcm16le=pcm16_from_floats(other_values),
        )
        attempt = audio.CaptureAttempt(
            status="CAPTURE_COMPLETED_RAW_PCM_TRANSIENT",
            provider="mock_capture",
            device_id="mock exact microphone",
            started_at_utc="2026-08-02T12:00:00.000000Z",
            ended_at_utc="2026-08-02T12:00:02.000000Z",
            diagnostic="test",
            captured=capture,
        )
        with self.make_window(amplitude_mod_hz=None) as window:
            result = audio.verify_local_capture(reference=window, attempt=attempt)
        capture.close()
        self.assertFalse(result["physical_output_at_capture_device_supported"])
        self.assertEqual(
            result["verification_status"],
            "CAPTURED_BUT_SOURCE_REFERENCE_NOT_SUPPORTED",
        )

    def test_end_to_end_fixture_decode_analysis_fake_playback_and_no_device(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "Data" / "library" / "test" / "fixture.wav"
            source.parent.mkdir(parents=True)
            values = [
                0.2 * math.sin(2 * math.pi * 330 * index / 16_000)
                for index in range(32_000)
            ]
            with wave.open(str(source), "wb") as writer:
                writer.setnchannels(1)
                writer.setsampwidth(2)
                writer.setframerate(16_000)
                writer.writeframes(pcm16_from_floats(values))
            exact_binding = binding(
                source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
            )
            played: list[str] = []
            bridge = audio.ReviewedSourceBoundAudioBridge(
                project_root=root,
                playback=lambda wav_bytes: played.append(hashlib.sha256(wav_bytes).hexdigest()),
                capture_provider=audio.NoDeviceCaptureProvider(),
                asr_adapter=FakeAsr(),
            )
            result = bridge.present(exact_binding)
        self.assertEqual(len(played), 1)
        self.assertTrue(result["physical_output_receipt"]["physical_speaker_playback_completed"])
        self.assertEqual(
            result["local_capture_verification"]["verification_status"],
            "NOT_AVAILABLE",
        )
        self.assertTrue(result["selected_person_machine_audio_cue_ready"])
        self.assertFalse(result["selected_person_biological_hearing_confirmed"])
        self.assertFalse(result["automatic_liking_or_preference_created"])
        self.assertIn("not biological hearing", result["context_cue"])
        self.assertRegex(result["context_cue_sha256"], r"^[0-9a-f]{64}$")
        self.assertIsInstance(json.dumps(result, sort_keys=True), str)

    def test_exact_source_hash_mismatch_fails_before_decode_or_playback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "Data" / "library" / "test" / "fixture.wav"
            source.parent.mkdir(parents=True)
            with wave.open(str(source), "wb") as writer:
                writer.setnchannels(1)
                writer.setsampwidth(2)
                writer.setframerate(16_000)
                writer.writeframes(b"\x00\x00" * 32_000)
            with self.assertRaisesRegex(audio.SourceBoundAudioError, "hash changed"):
                audio.decode_exact_audio_interval(
                    project_root=root,
                    binding=binding(source_hash="f" * 64),
                )

    def test_cached_inventory_can_remain_read_only_without_loading_model(self) -> None:
        result = audio.cached_audio_capability_inventory(hash_model_binary=False)
        self.assertFalse(result["network_used"])
        self.assertFalse(result["device_opened"])
        self.assertFalse(result["asr"]["model_loaded_or_run"])
        self.assertIn("faster-whisper", result["packages"])

    @unittest.skipUnless(os.name == "nt", "Windows-only constructor contract")
    def test_windows_capture_requires_explicit_confirmation_and_device(self) -> None:
        with self.assertRaises(audio.SourceBoundAudioError):
            audio.FfmpegDshowCaptureProvider(
                device_name="Microphone 1",
                explicitly_confirmed=False,
            )
        with self.assertRaises(audio.SourceBoundAudioError):
            audio.FfmpegDshowCaptureProvider(
                device_name="",
                explicitly_confirmed=True,
            )


if __name__ == "__main__":
    unittest.main()
