from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Core.voice_benchmark_capture import VoiceBenchmarkRecorder, resource_snapshot
from tools import kira_world_shell_server as shell
from tools import run_kira_text_voice_two_turn_latency_acceptance as latency_harness


def read_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class VoiceBenchmarkRecorderTests(unittest.TestCase):
    def test_resource_snapshot_reports_ram_and_defers_gpu_on_latency_events(self) -> None:
        snapshot = resource_snapshot(include_gpu=False)

        self.assertIn("ram", snapshot)
        self.assertIn("available", snapshot["ram"])
        self.assertEqual(snapshot["gpu"]["source"], "not_sampled_at_latency_sensitive_event")

    def test_disabled_recorder_is_inert(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recorder = VoiceBenchmarkRecorder(root / "capture", enabled=False, project_root=root)
            request_id = recorder.start_request(candidate="kira", candidate_label="Kira", interface="test")
            recorder.flush()

            self.assertEqual(request_id, "")
            self.assertFalse((root / "capture").exists())

    def test_timeline_is_monotonic_public_only_and_owner_audible_stays_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recorder = VoiceBenchmarkRecorder(root / "capture", enabled=True, project_root=root)
            with patch("Core.voice_benchmark_capture.resource_snapshot", return_value={"ram": {"available": True}, "gpu": {"available": False}}):
                request_id = recorder.start_request(
                    candidate="kira",
                    candidate_label="Kira",
                    interface="test",
                    monotonic_ns=1_000_000,
                )
                recorder.record_event(
                    request_id,
                    "text_ready",
                    {
                        "raw_reply_text": "must never persist",
                        "private_mind": "must never persist",
                        "expected_public_words": ["hello", "world"],
                    },
                    monotonic_ns=2_000_000,
                )
                recorder.record_event(
                    request_id,
                    "first_playback_proxy",
                    {
                        "public_words": ["hello", "world"],
                        "first_audible_proxy_kind": "playback_api_call_start_not_owner_observed_audible",
                        "owner_true_first_audible_monotonic_ms": None,
                        "owner_observation_required": True,
                    },
                    monotonic_ns=3_000_000,
                )
                recorder.finish_request(
                    request_id,
                    {
                        "complete": True,
                        "expected_public_words": ["hello", "world"],
                        "synthesized_public_words": ["hello", "world"],
                        "playback_proxy_public_words": ["hello", "world"],
                        "owner_observed_public_words": None,
                        "owner_observed_exact": None,
                        "owner_true_first_audible_monotonic_ms": None,
                        "expected_vs_playback_proxy_exact": True,
                    },
                    monotonic_ns=4_000_000,
                    include_gpu=False,
                )

            events = read_events(recorder.request_path(request_id))

        self.assertEqual([event["monotonic_ms"] for event in events], [1.0, 2.0, 3.0, 4.0])
        self.assertEqual([event["event"] for event in events], [
            "request_submitted",
            "text_ready",
            "first_playback_proxy",
            "request_completed",
        ])
        serialized = json.dumps(events).lower()
        self.assertNotIn("must never persist", serialized)
        self.assertFalse(any(event["privacy"]["private_mind_recorded"] for event in events))
        self.assertEqual(events[1]["details"]["expected_public_words"], ["hello", "world"])
        self.assertIsNone(events[2]["details"]["owner_true_first_audible_monotonic_ms"])
        self.assertIsNone(events[-1]["details"]["owner_observed_public_words"])
        self.assertTrue(events[-1]["details"]["expected_vs_playback_proxy_exact"])

    def test_capture_root_must_stay_inside_declared_project(self) -> None:
        with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as outside:
            with self.assertRaises(ValueError):
                VoiceBenchmarkRecorder(outside, enabled=True, project_root=project)

    def test_route_proof_is_flat_allowlisted_and_free_form_diagnostics_are_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recorder = VoiceBenchmarkRecorder(root / "capture", enabled=True, project_root=root)
            with patch(
                "Core.voice_benchmark_capture.resource_snapshot",
                return_value={"ram": {"available": True}, "gpu": {"available": False}},
            ):
                request_id = recorder.start_request(
                    candidate="kira",
                    candidate_label="Kira",
                    interface="test",
                    monotonic_ns=1_000_000,
                )
                recorder.record_event(
                    request_id,
                    "chunk_synthesis_end",
                    {
                        "chunk_index": 0,
                        "generated": True,
                        "generation_reason": "ok",
                        "route_id": "blackwell_gpu_persistent_candidate_v2",
                        "approved_voice_path_used": "blackwell_gpu",
                        "device": "cuda",
                        "route_attempt_summary": (
                            "blackwell_gpu_persistent_candidate_v2:used:ok"
                        ),
                        "preferred_failure_reason": "",
                        "gpu_synthesis_attempted": True,
                        "cpu_synthesis_attempted": False,
                        "automatic_cpu_fallback_used": False,
                        "blackwell_self_check_cache_status": "hit",
                        "blackwell_self_check_cache_scope": "current_python_process",
                        "blackwell_self_check_cache_key_sha256": "a" * 64,
                        "gpu_actual_allocation": True,
                        "gpu_actual_execution": True,
                        "gpu_utilization_observed": True,
                        "peak_allocated_bytes": 2_000_000_000,
                        "peak_reserved_bytes": 2_500_000_000,
                        "peak_process_rss_mib": 4096.5,
                        "peak_sidecar_gpu_delta_mib": 3500.0,
                        "sidecar_process_seconds": 8.25,
                        "sidecar_lifecycle": "session_owned_persistent_candidate_v2",
                        "persistent_worker_reused": True,
                        "staging_promoted_to_caller_target": True,
                        "generic_voice_used": False,
                        "sapi_voice_used": False,
                        "fallback_used": False,
                        "test_only_injected_client": False,
                        "production_route_promoted": False,
                        "production_routing_authorized": False,
                        "qwen_absence_proven_for_accepted_generation": True,
                        "approved_voice_attempts": [
                            {"route_id": "blackwell_gpu", "status": "used"}
                        ],
                        "gpu_proof": {
                            "actual_gpu_execution": True,
                            "private_diagnostic": "MUST NOT PERSIST",
                        },
                        "traceback": "PRIVATE TRACEBACK MUST NOT PERSIST",
                        "captured_warnings": "PRIVATE WARNING MUST NOT PERSIST",
                        "raw_reply_text": "PRIVATE RAW REPLY MUST NOT PERSIST",
                    },
                    monotonic_ns=2_000_000,
                )
                recorder.flush()

            events = read_events(recorder.request_path(request_id))

        details = events[-1]["details"]
        self.assertEqual(details["approved_voice_path_used"], "blackwell_gpu")
        self.assertEqual(details["device"], "cuda")
        self.assertTrue(details["gpu_actual_allocation"])
        self.assertTrue(details["gpu_actual_execution"])
        self.assertEqual(details["peak_allocated_bytes"], 2_000_000_000)
        self.assertEqual(
            details["sidecar_lifecycle"],
            "session_owned_persistent_candidate_v2",
        )
        for key in (
            "persistent_worker_reused",
            "staging_promoted_to_caller_target",
            "gpu_actual_execution",
            "qwen_absence_proven_for_accepted_generation",
        ):
            self.assertIs(details[key], True)
        for key in (
            "generic_voice_used",
            "sapi_voice_used",
            "fallback_used",
            "test_only_injected_client",
            "production_route_promoted",
            "production_routing_authorized",
        ):
            self.assertIs(details[key], False)
        self.assertEqual(details["blackwell_self_check_cache_status"], "hit")
        self.assertEqual(
            details["blackwell_self_check_cache_scope"],
            "current_python_process",
        )
        self.assertEqual(details["blackwell_self_check_cache_key_sha256"], "a" * 64)
        self.assertNotIn("approved_voice_attempts", details)
        self.assertNotIn("gpu_proof", details)
        serialized = json.dumps(events).casefold()
        self.assertNotIn("private traceback", serialized)
        self.assertNotIn("private warning", serialized)
        self.assertNotIn("private diagnostic", serialized)
        self.assertNotIn("private raw reply", serialized)
        classified = latency_harness.classify_voice_route(
            [details],
            mode="persistent_voice_v2_llama_keep_alive_buffered",
        )
        self.assertTrue(classified["preferred_gpu_passed"])


class ShellVoiceBenchmarkIntegrationTests(unittest.TestCase):
    def test_public_words_and_pipeline_events_are_captured_without_private_channels(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recorder = VoiceBenchmarkRecorder(root / "capture", enabled=True, project_root=root)
            with patch("Core.voice_benchmark_capture.resource_snapshot", return_value={"ram": {"available": True}, "gpu": {"available": False}}):
                request_id = recorder.start_request(
                    candidate="kira",
                    candidate_label="Kira",
                    interface="test",
                    monotonic_ns=1_000_000,
                )

                def fake_pipeline(chunks, _cfg, *, event_callback=None, **_kwargs):
                    assert event_callback is not None
                    for index, chunk in enumerate(chunks):
                        words = shell.spoken_words(chunk)
                        event_callback("chunk_synthesis_start", {"chunk_index": index, "public_words": words, "monotonic_ns": 2_000_000 + index * 4_000_000})
                        event_callback("chunk_synthesis_end", {"chunk_index": index, "public_words": words, "generated": True, "monotonic_ns": 3_000_000 + index * 4_000_000})
                        event_callback("chunk_playback_start", {"chunk_index": index, "public_words": words, "monotonic_ns": 4_000_000 + index * 4_000_000})
                        if index == 0:
                            event_callback(
                                "first_playback_proxy",
                                {
                                    "chunk_index": 0,
                                    "public_words": words,
                                    "first_audible_proxy_kind": "playback_api_call_start_not_owner_observed_audible",
                                    "owner_true_first_audible_monotonic_ms": None,
                                    "owner_observation_required": True,
                                    "monotonic_ns": 4_000_000,
                                },
                            )
                        event_callback("chunk_playback_end", {"chunk_index": index, "public_words": words, "played": True, "monotonic_ns": 5_000_000 + index * 4_000_000})
                    return {
                        "spoken": True,
                        "complete": True,
                        "reason": "ok",
                        "pipeline": "bounded_chunk_prefetch_v1",
                        "voice_identity_unchanged": True,
                        "first_audio_elapsed_seconds": 0.003,
                        "max_continuation_gap_seconds": 0.0,
                        "chunk_results": [
                            {
                                "chunk_index": index,
                                "text": chunk,
                                "generated": True,
                                "played": True,
                                "generation_reason": "ok",
                                "playback_reason": "ok",
                            }
                            for index, chunk in enumerate(chunks)
                        ],
                    }

                cfg = type("Cfg", (), {"engine": "chatterbox_tts", "max_chars": 120, "play_audio": True, "chatterbox_device": "cpu"})()
                raw = (
                    "SPOKEN:\nHello Robert, every public word remains.\n\n"
                    "PRIVATE_MIND:\nThis private sentence must never enter capture.\n\n"
                    "TRUTH_FLAGS:\nPrivate truth also stays excluded."
                )
                with (
                    patch.object(shell, "VOICE_BENCHMARK_CAPTURE", recorder),
                    patch.object(shell, "load_candidate_voice_config", return_value=cfg),
                    patch.object(shell, "speak_text_chunks_streaming", side_effect=fake_pipeline),
                    patch.object(shell, "append_jsonl"),
                ):
                    result = shell.speak_active_reply(
                        "kira",
                        "Kira",
                        raw,
                        benchmark_request_id=request_id,
                    )

            events = read_events(recorder.request_path(request_id))

        self.assertTrue(result["complete"])
        self.assertIn("chunk_synthesis_start", [event["event"] for event in events])
        self.assertIn("chunk_playback_end", [event["event"] for event in events])
        completed = events[-1]["details"]
        self.assertEqual(completed["expected_public_words"], ["hello", "robert", "every", "public", "word", "remains"])
        self.assertEqual(completed["playback_proxy_public_words"], completed["expected_public_words"])
        self.assertTrue(completed["expected_vs_playback_proxy_exact"])
        self.assertIsNone(completed["owner_observed_exact"])
        serialized = json.dumps(events).lower()
        self.assertNotIn("private sentence", serialized)
        self.assertNotIn("private truth", serialized)
        self.assertIn('"robert"', json.dumps(completed["expected_public_words"]).lower())

    def test_cancelled_queued_request_records_interruption_and_zero_playback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            recorder = VoiceBenchmarkRecorder(root / "capture", enabled=True, project_root=root)
            with patch("Core.voice_benchmark_capture.resource_snapshot", return_value={"ram": {"available": True}, "gpu": {"available": False}}):
                request_id = recorder.start_request(candidate="kira", candidate_label="Kira", interface="test")
                item = {
                    "benchmark_request_id": request_id,
                    "benchmark_expected_public_words": ["hello", "world"],
                }
                with patch.object(shell, "VOICE_BENCHMARK_CAPTURE", recorder):
                    shell._cancel_queued_voice_benchmark(item, "test_cancel")

            events = read_events(recorder.request_path(request_id))

        self.assertEqual([event["event"] for event in events][-2:], ["interruption_requested", "request_completed"])
        completed = events[-1]["details"]
        self.assertTrue(completed["cancelled"])
        self.assertEqual(completed["playback_proxy_public_word_count"], 0)
        self.assertFalse(completed["expected_vs_playback_proxy_exact"])


if __name__ == "__main__":
    unittest.main()
