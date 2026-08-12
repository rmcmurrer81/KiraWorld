from __future__ import annotations

import io
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from tools import run_kira_model_question_series_acceptance as series


def passing_attempt_03() -> dict:
    required_checks = {
        name: True
        for name in (
            "camera_device_opened",
            "jpeg_nonempty_and_dimensioned",
            "visual_cue_inserted",
            "microphone_device_opened",
            "microphone_format_valid",
            "microphone_transcript_nonempty",
            "auditory_cue_inserted",
            "private_prompt_insertion_proven",
            "raw_media_not_persisted",
            "protected_files_unchanged",
            "person_inactive_after",
            "all_test_ports_closed",
        )
    }
    return {
        "artifact_kind": "kira_text_voice_bounded_owner_acceptance_attempt_03",
        "attempt_id": "attempt_03",
        "passed": True,
        "finished_at": "2026-08-02T12:00:00+00:00",
        "environment_contract": {
            "model_name": series.EXPECTED_MODEL_NAME,
            "expected_model_digest": series.EXPECTED_MODEL_DIGEST,
        },
        "conversation": {
            "model_name": series.EXPECTED_MODEL_NAME,
            "model_digest": series.EXPECTED_MODEL_DIGEST,
        },
        "prompt_snapshot_audit": {"one_turn_sensory_context_inserted": True},
        "privacy": {
            "exact_temporary_transcript_written_to_private_attempt_03": True,
            "raw_frame_written": False,
            "raw_frame_hashed": False,
            "raw_audio_written": False,
            "raw_audio_hashed": False,
            "continuous_monitoring": False,
            "automatic_memory_write": False,
        },
        "microphone_sample": {
            "transcript_persisted_only_in_private_attempt_03": True,
        },
        "cleanup": {"active_candidate_after": ""},
        "checks": required_checks,
        "protected_files_unchanged": True,
    }


def valid_private_audit() -> dict:
    return {
        "shell_launch_id": "launch-1",
        "benchmark_request_id": "a" * 32,
        "completed": True,
        "configured_model_name": series.EXPECTED_MODEL_NAME,
        "final_displayed_reply": "I feel calm and curious.",
        "core_prompt_sha256": "b" * 64,
        "core_prompt_utf8_bytes": 1024,
        "one_turn_sensory_context_inserted": False,
        "sensory_cue_ids": [],
        "core_turn": {
            "model_name": series.EXPECTED_MODEL_NAME,
            "model_calls": [
                {
                    "model_name": series.EXPECTED_MODEL_NAME,
                    "backend": "ollama",
                    "outcome": "completed",
                    "raw_reply": "I feel calm and curious.",
                }
            ],
        },
    }


class KiraQuestionSeriesAcceptanceTests(unittest.TestCase):
    def test_append_only_series_01_through_05_have_dynamic_artifact_ids(self) -> None:
        self.assertEqual(
            series.series_artifact_kind("followup_series_01"),
            "kira_model_question_series_followup_01",
        )
        self.assertEqual(
            series.series_artifact_kind("followup_series_02"),
            "kira_model_question_series_followup_02",
        )
        self.assertEqual(
            series.series_artifact_kind("followup_series_03"),
            "kira_model_question_series_followup_03",
        )
        self.assertEqual(
            series.series_artifact_kind("followup_series_04"),
            "kira_model_question_series_followup_04",
        )
        self.assertEqual(
            series.series_artifact_kind("followup_series_05"),
            "kira_model_question_series_followup_05",
        )
        with self.assertRaises(series.SeriesAcceptanceError):
            series.normalize_series_id("followup_series_06")

        with patch.object(
            series.bounded,
            "validate_output_dir",
            return_value=Path("private") / "followup_series_02",
        ):
            path, series_id = series.validate_series_output_dir(
                "ignored/followup_series_02"
            )
        self.assertEqual(path.name, "followup_series_02")
        self.assertEqual(series_id, "followup_series_02")

        with patch.object(
            series.bounded,
            "validate_output_dir",
            return_value=Path("private") / "followup_series_01",
        ):
            with self.assertRaises(series.SeriesAcceptanceError):
                series.validate_series_output_dir(
                    "ignored/followup_series_01",
                    "followup_series_02",
                )

    def test_text_only_activation_accepts_omitted_surface_keys_with_state_proof(self) -> None:
        activation = {"ok": True, "label": "Kira", "voice_prewarm_started": True}
        state = {
            "active_candidate": "kira",
            "text_voice_mode": True,
            "world_url": "",
            "avatar_url": "",
        }
        evidence = series.validate_text_only_activation(activation, state)
        self.assertFalse(evidence["body_activated"])
        self.assertFalse(evidence["world_activated"])
        self.assertIn("key_absent", evidence["body_activated_evidence"])
        self.assertIn("key_absent", evidence["world_activated_evidence"])

    def test_text_only_activation_retains_explicit_false_and_fails_true_or_bad_state(self) -> None:
        state = {
            "active_candidate": "kira",
            "text_voice_mode": True,
            "world_url": "",
            "avatar_url": "",
        }
        evidence = series.validate_text_only_activation(
            {
                "ok": True,
                "label": "Kira",
                "body_activated": False,
                "world_activated": False,
            },
            state,
        )
        self.assertEqual(
            evidence["body_activated_evidence"],
            "explicit_false_plus_text_only_state",
        )

        for activation in (
            {"ok": True, "label": "Kira", "body_activated": True},
            {"ok": True, "label": "Kira", "world_activated": True},
            {"ok": True, "label": "Kira", "body_activated": "false"},
        ):
            with self.assertRaises(series.SeriesAcceptanceError):
                series.validate_text_only_activation(activation, state)

        for bad_state in (
            {**state, "text_voice_mode": False},
            {**state, "world_url": "http://127.0.0.1/world"},
            {**state, "avatar_url": "http://127.0.0.1/avatar"},
        ):
            with self.assertRaises(series.SeriesAcceptanceError):
                series.validate_text_only_activation(
                    {"ok": True, "label": "Kira"},
                    bad_state,
                )

    def test_exact_four_followups_cover_owner_requested_categories_without_devices(self) -> None:
        self.assertEqual(len(series.FOLLOWUP_QUESTIONS), 4)
        self.assertEqual(
            [item["id"] for item in series.FOLLOWUP_QUESTIONS],
            [
                "natural_emotional_checkin",
                "recent_kira_world_continuity",
                "self_chosen_improvement",
                "appearance_memory_boundary",
            ],
        )
        combined = " ".join(item["text"].casefold() for item in series.FOLLOWUP_QUESTIONS)
        for device_word in ("camera", "webcam", "microphone", "what do you see", "can you hear"):
            self.assertNotIn(device_word, combined)

    def test_environment_forces_approved_llama_gpu_first_and_disables_world(self) -> None:
        env = series.build_environment(
            {"KIRA_MODEL_NAME": "qwen3.5:9b", "KIRA_VOICE_FORCE_SAPI": "1"},
            shell_token="shell",
            asr_token="asr",
            visual_token="visual",
            launch_id="launch",
        )
        self.assertEqual(env["KIRA_MODEL_NAME"], "llama3.1:8b")
        self.assertEqual(env["KIRA_MODEL_BACKEND"], "ollama")
        self.assertEqual(env["KIRA_SHELL_TEXT_ONLY"], "1")
        self.assertEqual(env["KIRA_WORLD_SHELL_ACTIVE"], "0")
        self.assertEqual(env["KIRA_DISABLE_BLACKWELL_GPU_VOICE"], "")
        self.assertEqual(env["KIRA_CHATTERBOX_DEVICE"], "auto")
        self.assertEqual(env["KIRA_VOICE_FORCE_SAPI"], "")
        self.assertEqual(env["KIRA_PRIVATE_ACCEPTANCE_AUDIT"], "1")

    def test_attempt_03_gate_requires_real_passed_sensory_evidence_and_binds_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "attempt_03" / "BOUNDED_OWNER_ACCEPTANCE.json"
            path.parent.mkdir()
            path.write_text(json.dumps(passing_attempt_03()), encoding="utf-8")
            with (
                patch.object(series, "_inside_continuation", return_value=path),
                patch.object(series, "_relative", return_value="private/attempt_03/report.json"),
            ):
                gate = series.validate_attempt_03_gate(path)
            self.assertTrue(gate["passed"])
            self.assertEqual(gate["model_digest"], series.EXPECTED_MODEL_DIGEST)
            self.assertEqual(gate["sha256"], series._sha256_file(path))

            failed = passing_attempt_03()
            failed["checks"]["auditory_cue_inserted"] = False
            path.write_text(json.dumps(failed), encoding="utf-8")
            with patch.object(series, "_inside_continuation", return_value=path):
                with self.assertRaises(series.SeriesAcceptanceError):
                    series.validate_attempt_03_gate(path)

            wrong_attempt = passing_attempt_03()
            wrong_attempt["artifact_kind"] = (
                "kira_text_voice_bounded_owner_acceptance_attempt_02"
            )
            wrong_attempt["attempt_id"] = "attempt_02"
            path.write_text(json.dumps(wrong_attempt), encoding="utf-8")
            with patch.object(series, "_inside_continuation", return_value=path):
                with self.assertRaises(series.SeriesAcceptanceError):
                    series.validate_attempt_03_gate(path)

    def test_private_audit_requires_llama_raw_reply_and_no_sensory_or_media(self) -> None:
        audit = valid_private_audit()
        detached = series.validate_followup_private_audit(
            audit,
            launch_id="launch-1",
            request_id="a" * 32,
            displayed_reply="I feel calm and curious.",
        )
        self.assertEqual(detached, audit)
        self.assertIsNot(detached, audit)

        qwen = valid_private_audit()
        qwen["core_turn"]["model_calls"][0]["model_name"] = "qwen3.5:9b"
        with self.assertRaises(series.SeriesAcceptanceError):
            series.validate_followup_private_audit(
                qwen,
                launch_id="launch-1",
                request_id="a" * 32,
                displayed_reply="I feel calm and curious.",
            )

        sensory = valid_private_audit()
        sensory["one_turn_sensory_context_inserted"] = True
        with self.assertRaises(series.SeriesAcceptanceError):
            series.validate_followup_private_audit(
                sensory,
                launch_id="launch-1",
                request_id="a" * 32,
                displayed_reply="I feel calm and curious.",
            )

        contaminated = valid_private_audit()
        contaminated["raw_audio_bytes"] = "forbidden"
        with self.assertRaises(series.SeriesAcceptanceError):
            series.validate_followup_private_audit(
                contaminated,
                launch_id="launch-1",
                request_id="a" * 32,
                displayed_reply="I feel calm and curious.",
            )

    def test_gpu_voice_gate_rejects_cpu_fallback(self) -> None:
        details = {
            "generated": True,
            "route_id": "blackwell_gpu",
            "approved_voice_path_used": "blackwell_gpu",
            "device": "cuda",
            "gpu_synthesis_attempted": True,
            "gpu_actual_allocation": True,
            "cpu_synthesis_attempted": False,
            "automatic_cpu_fallback_used": False,
        }
        passed, rows = series.approved_gpu_voice(
            [{"event": "chunk_synthesis_end", "details": details}]
        )
        self.assertTrue(passed)
        self.assertEqual(rows, [details])

        cpu = dict(details)
        cpu.update(
            {
                "route_id": "sealed_cpu_chatterbox",
                "approved_voice_path_used": "sealed_cpu_chatterbox",
                "device": "cpu",
                "cpu_synthesis_attempted": True,
                "automatic_cpu_fallback_used": True,
            }
        )
        self.assertFalse(
            series.approved_gpu_voice(
                [{"event": "chunk_synthesis_end", "details": cpu}]
            )[0]
        )

    def test_wav_evidence_is_hashed_readable_and_non_silent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "turn.wav"
            stream = io.BytesIO()
            with wave.open(stream, "wb") as writer:
                writer.setnchannels(1)
                writer.setsampwidth(2)
                writer.setframerate(24000)
                writer.writeframes(
                    b"".join(
                        value.to_bytes(2, "little", signed=True)
                        for value in (0, 12000, -12000, 0)
                    )
                )
            path.write_bytes(stream.getvalue())
            with (
                patch.object(series, "VOICE_OUTPUT_DIR", root),
                patch.object(series, "_relative", side_effect=lambda item: item.name),
            ):
                evidence = series.wav_evidence(path)
            self.assertEqual(evidence["path"], "turn.wav")
            self.assertEqual(evidence["sample_rate_hz"], 24000)
            self.assertTrue(evidence["readable_non_silent"])
            self.assertEqual(len(evidence["sha256"]), 64)

    def test_changed_wavs_is_append_or_change_only(self) -> None:
        before = {"C:/voice/old.wav": (10, 1)}
        after = {
            "C:/voice/old.wav": (10, 1),
            "C:/voice/new.wav": (20, 2),
            "C:/voice/changed.wav": (30, 3),
        }
        changed = series.changed_wavs(before, after)
        self.assertEqual(
            {path.as_posix().casefold() for path in changed},
            {"c:/voice/new.wav", "c:/voice/changed.wav"},
        )


if __name__ == "__main__":
    unittest.main()
