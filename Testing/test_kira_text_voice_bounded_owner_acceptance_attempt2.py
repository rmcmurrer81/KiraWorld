from __future__ import annotations

import io
import math
import subprocess
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from tools import run_kira_text_voice_bounded_owner_acceptance as acceptance


class BoundedOwnerAcceptanceAttempt2Tests(unittest.TestCase):
    def test_attempt_02_and_attempt_03_have_separate_append_only_contracts(self) -> None:
        for attempt_id in ("attempt_02", "attempt_03"):
            normalized = acceptance.normalize_private_attempt_id(attempt_id.upper())
            self.assertEqual(normalized, attempt_id)
            acceptance.validate_private_attempt_output_name(
                normalized,
                Path("private") / normalized,
            )
            self.assertEqual(
                acceptance.private_attempt_evidence_key(
                    "exact_temporary_transcript_written_to_private",
                    normalized,
                ),
                f"exact_temporary_transcript_written_to_private_{attempt_id}",
            )
            self.assertEqual(
                acceptance.private_attempt_evidence_key(
                    "transcript_persisted_only_in_private",
                    normalized,
                ),
                f"transcript_persisted_only_in_private_{attempt_id}",
            )

        with self.assertRaises(acceptance.AcceptanceError):
            acceptance.normalize_private_attempt_id("attempt_04")
        with self.assertRaises(acceptance.AcceptanceError):
            acceptance.validate_private_attempt_output_name(
                "attempt_03",
                Path("private") / "attempt_02",
            )

    def test_camera_command_holds_live_device_and_returns_exactly_one_jpeg(self) -> None:
        command = acceptance.camera_capture_command(
            Path("ffmpeg.exe"),
            "USB CAMERA",
            hold_seconds=3.0,
        )

        self.assertIn("video=USB CAMERA", command)
        self.assertIn("trim=start=3.000,scale=640:-2", command)
        frame_index = command.index("-frames:v")
        self.assertEqual(command[frame_index + 1], "1")
        self.assertEqual(command[-3:], ["-vcodec", "mjpeg", "pipe:1"])
        self.assertEqual(command.count("pipe:1"), 1)

    def test_microphone_command_is_bounded_pcm_s16le_mono_16khz(self) -> None:
        command = acceptance.microphone_capture_command(
            Path("ffmpeg.exe"),
            "Microphone (USB CAMERA)",
            duration_seconds=8.0,
        )

        self.assertIn("audio=Microphone (USB CAMERA)", command)
        self.assertEqual(command[command.index("-t") + 1], "8.000")
        self.assertEqual(command[command.index("-ac") + 1], "1")
        self.assertEqual(command[command.index("-ar") + 1], "16000")
        self.assertEqual(command[command.index("-c:a") + 1], "pcm_s16le")

    def test_jpeg_dimensions_reads_sof_without_decoding_pixels(self) -> None:
        # Minimal structural JPEG containing a one-component SOF0 segment.
        jpeg = (
            b"\xff\xd8"
            b"\xff\xc0\x00\x0b\x08\x00\x40\x00\x60\x01\x01\x11\x00"
            b"\xff\xd9"
        )
        self.assertEqual(acceptance.jpeg_dimensions(jpeg), (96, 64))
        with self.assertRaises(acceptance.AcceptanceError):
            acceptance.jpeg_dimensions(b"not a jpeg")

    def test_pcm_wav_audit_reports_format_rms_peak_without_sample_payload(self) -> None:
        samples = (0, 16384, -16384, 0)
        stream = io.BytesIO()
        with wave.open(stream, "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(16000)
            writer.writeframes(b"".join(value.to_bytes(2, "little", signed=True) for value in samples))

        audit = acceptance.pcm_wav_audit(stream.getvalue())

        self.assertEqual(audit["codec"], "pcm_s16le")
        self.assertEqual(audit["channels"], 1)
        self.assertEqual(audit["sample_rate_hz"], 16000)
        self.assertEqual(audit["frame_count"], 4)
        self.assertEqual(audit["peak_linear"], 0.5)
        self.assertAlmostEqual(audit["rms_linear"], math.sqrt(0.125), places=6)
        self.assertTrue(audit["non_silent"])
        self.assertNotIn("samples", audit)
        self.assertNotIn("payload", audit)

    def test_capture_metadata_never_copies_transient_payload(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["ffmpeg"],
            returncode=0,
            stdout=b"encoded-only",
            stderr=b"",
        )
        with patch.object(acceptance.subprocess, "run", return_value=completed):
            result = acceptance.run_ffmpeg_capture(["ffmpeg"], timeout=1.0)

        metadata = acceptance.capture_metadata(result)
        self.assertTrue(result.device_opened)
        self.assertTrue(metadata["encoded_output_nonempty"])
        self.assertFalse(metadata["raw_payload_persisted"])
        self.assertNotIn("payload", metadata)
        self.assertNotIn("encoded-only", str(metadata))

    def test_benchmark_phase_audit_preserves_detailed_voice_boundaries(self) -> None:
        names = (
            "request_submitted",
            "chat_request_received",
            "text_ready",
            "voice_payload_ready",
            "voice_pipeline_start",
            "chunk_synthesis_start",
            "chunk_synthesis_end",
            "chunk_playback_start",
            "chunk_playback_end",
            "request_completed",
        )
        records = []
        for sequence, name in enumerate(names, 1):
            details = {"chunk_index": 0} if name.startswith("chunk_") else {}
            if name == "chunk_synthesis_end":
                details.update({"route_id": "blackwell_gpu", "device": "cuda"})
            records.append(
                {
                    "sequence": sequence,
                    "event": name,
                    "monotonic_ns": sequence * 1_000_000_000,
                    "wall_time_utc": f"2026-08-02T06:00:{sequence:02d}+00:00",
                    "details": details,
                }
            )

        audit = acceptance.benchmark_phase_audit(records)

        self.assertEqual(audit["submit_to_chat_receive_seconds"], 1.0)
        self.assertEqual(audit["chat_receive_to_text_ready_seconds"], 1.0)
        self.assertEqual(audit["request_total_seconds"], 9.0)
        self.assertEqual(audit["chunks"][0]["synthesis_seconds"], 1.0)
        self.assertEqual(audit["chunks"][0]["playback_seconds"], 1.0)
        self.assertEqual(
            audit["chunks"][0]["synthesis_end_details"]["route_id"],
            "blackwell_gpu",
        )
        self.assertEqual(len(audit["event_timeline"]), len(names))

    def test_exact_asr_segments_are_bounded_and_keep_private_text(self) -> None:
        rows = acceptance.exact_asr_segments(
            [{"start": 0.1234, "end": 1.2345, "text": "exact podcast words"}]
        )
        self.assertEqual(
            rows,
            [
                {
                    "start_seconds": 0.123,
                    "end_seconds": 1.234,
                    "text": "exact podcast words",
                }
            ],
        )

    def test_private_model_audit_requires_exact_bindings_and_no_raw_media(self) -> None:
        value = {
            "shell_launch_id": "launch-1",
            "benchmark_request_id": "a" * 32,
            "completed": True,
            "final_displayed_reply": "I can see a bright frame.",
            "core_prompt_sha256": "b" * 64,
            "core_prompt_utf8_bytes": 1234,
            "one_turn_sensory_context_inserted": True,
            "sensory_cue_ids": ["cue_visual", "cue_audio"],
            "core_turn": {
                "model_calls": [
                    {
                        "model_name": "llama3.1:8b",
                        "raw_reply": "I can see a bright frame.",
                        "first_token_available": False,
                    }
                ]
            },
            "outer_transformations": [],
        }

        detached = acceptance.validate_private_model_audit(
            value,
            expected_launch_id="launch-1",
            expected_request_id="a" * 32,
            expected_reply="I can see a bright frame.",
            expected_cue_ids=["cue_audio", "cue_visual"],
        )
        self.assertEqual(detached, value)
        self.assertIsNot(detached, value)

        contaminated = {**value, "raw_audio_bytes": "forbidden"}
        with self.assertRaises(acceptance.AcceptanceError):
            acceptance.validate_private_model_audit(
                contaminated,
                expected_launch_id="launch-1",
                expected_request_id="a" * 32,
                expected_reply="I can see a bright frame.",
                expected_cue_ids=["cue_audio", "cue_visual"],
            )


if __name__ == "__main__":
    unittest.main()
