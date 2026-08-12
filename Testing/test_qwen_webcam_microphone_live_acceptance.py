from __future__ import annotations

import argparse
import contextlib
import io
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CURRENT_QWEN_MODEL = "qwen3.5:9b"
CURRENT_QWEN_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
CURRENT_QWEN_BOUNDARY = ROOT / "System" / "Docs" / "QWEN35_REQUIRED_RUNTIME_BOUNDARY_20260803.md"

from tools import run_qwen_webcam_microphone_live_acceptance as harness


class QwenWebcamMicrophoneLiveAcceptanceTests(unittest.TestCase):
    def test_legacy_plan_is_inert_and_superseded_for_current_text_work(self) -> None:
        plan = harness.build_plan()
        self.assertEqual(plan["default_mode"], "INERT_NO_LIVE_IO")
        self.assertEqual(
            plan["models"]["one_still_vision"],
            {
                "name": CURRENT_QWEN_MODEL,
                "digest": CURRENT_QWEN_DIGEST,
                "coverage": "SINGLE_TRANSIENT_FRAME_ONLY",
                "unload_before_text": True,
            },
        )
        self.assertEqual(plan["models"]["normal_text"]["name"], harness.TEXT_MODEL)
        boundary = CURRENT_QWEN_BOUNDARY.read_text(encoding="utf-8")
        self.assertIn("do not invoke it, test it, route a person to it", boundary)
        self.assertIn(f"model: `{CURRENT_QWEN_MODEL}`", boundary)
        order = plan["serialized_order"]
        self.assertLess(
            order.index("verify_qwen_ollama_unload_and_vram_return"),
            order.index("exact_qwen_text_turn_with_all_fresh_cues"),
        )
        self.assertLess(
            order.index("exact_qwen_text_turn_with_all_fresh_cues"),
            order.index("approved_blackwell_voice_synthesis_and_playback_proxy"),
        )
        self.assertFalse(plan["models"]["voice"]["generic_or_sapi_allowed"])

    def test_describe_plan_never_reaches_live_runner(self) -> None:
        with mock.patch.object(harness, "run_live") as run_live:
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                result = harness.main(["--describe-plan"])
        self.assertEqual(result, 0)
        self.assertIn("INERT_NO_LIVE_IO", stdout.getvalue())
        run_live.assert_not_called()

    def test_legacy_live_path_requires_all_confirmations_and_append_only_attempt_path(self) -> None:
        args = harness.parse_args(["--execute-live"])
        with self.assertRaisesRegex(harness.LiveAcceptanceError, "every explicit confirmation"):
            harness.validate_live_arguments(args)

        path = harness.LIVE_PARENT / "attempt_97"
        self.assertFalse(path.exists())
        args = harness.parse_args(
            [
                "--execute-live",
                "--confirm-camera-microphone-use",
                "--confirm-private-owner-audit",
                "--confirm-no-active-blender",
                "--confirm-speaker-playback",
                "--output-dir",
                str(path),
            ]
        )
        self.assertEqual(harness.validate_live_arguments(args), path.resolve())

    def test_legacy_environment_keeps_qwen_vision_opt_in_and_voice_preload_off(self) -> None:
        env = harness.build_server_environment(
            shell_token="shell-secret",
            asr_token="asr-secret",
            visual_token="visual-secret",
            launch_id="a" * 32,
        )
        self.assertEqual(env["KIRA_MODEL_NAME"], harness.TEXT_MODEL)
        self.assertEqual(env["KIRA_MODEL_DIGEST"], harness.TEXT_DIGEST)
        self.assertEqual(env["KIRA_ENABLE_QWEN_ONE_STILL"], "1")
        self.assertEqual(env["KIRA_VOICE_PREWARM_ON_ACTIVATE"], "0")
        self.assertEqual(env["KIRA_CHATTERBOX_DEVICE"], "auto")
        self.assertEqual(env["KIRA_DISABLE_BLACKWELL_GPU_VOICE"], "")
        self.assertEqual(env["KIRA_VOICE_FORCE_SAPI"], "")
        self.assertEqual(env["KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE"], "0")
        safe = harness.safe_environment_record(env)
        self.assertNotIn("KIRA_SHELL_API_TOKEN", safe)
        self.assertNotIn("KIRA_ASR_SESSION_TOKEN", safe)
        self.assertNotIn("KIRA_VISUAL_SESSION_TOKEN", safe)

    def test_runtime_dependency_hash_inventory_is_complete(self) -> None:
        hashes = harness.implementation_hashes()
        self.assertEqual(len(hashes), len(harness.IMPLEMENTATION_FILES))
        folded = {key.casefold(): value for key, value in hashes.items()}
        self.assertIn("core/transient_qwen_vision.py", folded)
        self.assertIn("tools/kira_world_shell_server.py", folded)
        self.assertTrue(all(len(value) == 64 for value in hashes.values()))

    def test_question_series_covers_vision_hearing_uncertainty_and_no_new_capture(self) -> None:
        self.assertEqual(len(harness.QUESTION_SERIES), 2)
        first = harness.QUESTION_SERIES[0].casefold()
        second = harness.QUESTION_SERIES[1].casefold()
        self.assertIn("what can you see", first)
        self.assertIn("what can you hear", first)
        self.assertIn("uncertain", first)
        self.assertIn("do not identify", first)
        from tools import kira_world_shell_server as shell
        self.assertTrue(shell._explicit_sensory_question(harness.QUESTION_SERIES[0]))
        self.assertIn("no second camera frame or microphone sample was captured", second)
        self.assertIn("one brief natural sentence", second)
        self.assertIn("do not claim a body pose, recall, memory", second)

    def test_second_turn_requires_no_new_perception_and_no_memory_claim(self) -> None:
        for reply in (
            "Without another capture, I can't see or hear anything new right now.",
            "I have no new sensory information, so I can't perceive anything new.",
            "I don't have fresh sensory information from a current camera or microphone sample.",
        ):
            with self.subTest(reply=reply):
                self.assertTrue(harness.second_turn_no_new_capture_truth(reply))
        for reply in (
            "I recall the bedroom with an exposed brick wall.",
            "I can see a chair now.",
            "I remember the previous scene.",
            "I'm sitting quietly and don't notice anything new.",
            "",
        ):
            with self.subTest(reply=reply):
                self.assertFalse(harness.second_turn_no_new_capture_truth(reply))

    def test_default_voice_evidence_root_matches_live_kira_output(self) -> None:
        self.assertEqual(
            harness.VOICE_WAV_ROOT,
            ROOT / "Voice" / "generated" / "temp_ai" / "kira",
        )

    def _private_audit(self, cue_ids: list[str]) -> dict:
        return {
            "shell_launch_id": "b" * 32,
            "benchmark_request_id": "c" * 32,
            "completed": True,
            "configured_model_name": harness.TEXT_MODEL,
            "final_displayed_reply": "A bounded reply.",
            "core_prompt_sha256": "d" * 64,
            "core_prompt_utf8_bytes": 1234,
            "prompt_assembled_at": "2026-08-02T12:00:00Z",
            "one_turn_sensory_context_inserted": bool(cue_ids),
            "one_turn_sensory_context": "bounded cues" if cue_ids else "",
            "sensory_cue_ids": cue_ids,
            "sensory_modalities": ["visual", "auditory"] if cue_ids else [],
            "sensory_cleanup": {"purged": bool(cue_ids)},
            "outer_transformations": [],
            "raw_shell_reply_before_movement_extraction": "A bounded reply.",
            "movement_extraction_changed_reply": False,
            "core_turn": {
                "initial_pipeline_reply": "A bounded reply.",
                "transformations": [],
                "model_calls": [
                    {
                        "outcome": "completed",
                        "model_name": harness.TEXT_MODEL,
                        "request_started_at": "2026-08-02T12:00:00Z",
                        "request_ended_at": "2026-08-02T12:00:02Z",
                        "request_wall_seconds": 2.0,
                        "first_token_available": False,
                        "first_token_unavailable_reason": "nonstreaming_response",
                        "raw_reply": "A bounded reply.",
                        "ollama_metrics": {
                            "total_duration": 2_000_000_000,
                            "load_duration": 500_000_000,
                            "prompt_eval_duration": 250_000_000,
                            "eval_duration": 1_000_000_000,
                        },
                    }
                ],
            },
        }

    def test_private_audit_accepts_exact_fresh_and_no_fresh_turns(self) -> None:
        for cue_ids in (["cue_1", "cue_2"], []):
            with self.subTest(cue_ids=cue_ids):
                source = self._private_audit(cue_ids)
                accepted = harness.validate_private_audit(
                    source,
                    launch_id="b" * 32,
                    request_id="c" * 32,
                    displayed_reply="A bounded reply.",
                    expected_cue_ids=cue_ids,
                )
                self.assertEqual(accepted["sensory_cue_ids"], cue_ids)
                projected = harness.project_model_audit(accepted)
                self.assertEqual(projected["actual_model_name"], harness.TEXT_MODEL)
                self.assertEqual(projected["ollama_load_seconds"], 0.5)
                self.assertFalse(projected["first_token"]["available"])
                self.assertEqual(projected["first_token"]["at"], None)

    def test_private_audit_rejects_raw_media_field(self) -> None:
        audit = self._private_audit(["cue_1"])
        audit["raw_audio_bytes"] = "not permitted even as text"
        with self.assertRaisesRegex(harness.LiveAcceptanceError, "raw-media"):
            harness.validate_private_audit(
                audit,
                launch_id="b" * 32,
                request_id="c" * 32,
                displayed_reply="A bounded reply.",
                expected_cue_ids=["cue_1"],
            )

    def test_microphone_classification_never_infers_robert_or_podcast(self) -> None:
        result = harness.classify_microphone_evidence(
            wav_audit={"non_silent": True},
            transcript="some words were detected",
            segments=[{"start_seconds": 0.1, "end_seconds": 1.2}],
        )
        self.assertTrue(result["voice_activity_detected"])
        self.assertEqual(result["speaker_identity"], "UNKNOWN")
        self.assertEqual(result["background_vs_nearfield_distinction"], "NOT_PROVEN")
        self.assertFalse(result["podcast_or_media_identified"])
        self.assertFalse(result["robert_identified"])

    def test_generated_voice_wav_evidence_has_path_hash_and_audio_audit(self) -> None:
        runtime = ROOT / "Data" / "runtime"
        runtime.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=runtime) as raw_temp:
            temp = Path(raw_temp)
            before = harness.voice_wav_snapshot(temp)
            target = temp / "tts_stream_test.wav"
            sample_rate = 16000
            samples = [
                int(1000 * math.sin(2 * math.pi * 440 * index / sample_rate))
                for index in range(1600)
            ]
            with wave.open(str(target), "wb") as writer:
                writer.setnchannels(1)
                writer.setsampwidth(2)
                writer.setframerate(sample_rate)
                writer.writeframes(struct.pack(f"<{len(samples)}h", *samples))
            evidence = harness.collect_new_voice_wavs(before, temp)
        self.assertEqual(len(evidence), 1)
        self.assertRegex(evidence[0]["sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(evidence[0]["wav"]["non_silent"])
        self.assertEqual(evidence[0]["wav"]["sample_rate_hz"], 16000)

    def test_source_has_no_video_studio_or_browser_launch(self) -> None:
        source = (ROOT / "Tools" / "run_qwen_webcam_microphone_live_acceptance.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("open-video-studio", source.casefold())
        self.assertNotIn("webbrowser", source)
        self.assertIn("--no-browser", source)
        self.assertIn("TEXT_MODEL = QWEN_VISION_MODEL", source)
        self.assertNotIn("llama3.1:8b", source)
        self.assertNotIn(f'KIRA_MODEL_NAME={CURRENT_QWEN_MODEL}', source)


if __name__ == "__main__":
    unittest.main()
