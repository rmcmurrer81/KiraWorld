from __future__ import annotations

import io
import json
import tempfile
import unittest
import wave
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools import run_kira_text_voice_two_turn_latency_acceptance as harness


def _private_audit(*, buffered: bool, keep_alive: bool) -> dict:
    call = {
        "model_name": harness.EXPECTED_MODEL_NAME,
        "backend": "ollama",
        "outcome": "completed",
        "raw_reply": "I feel present and curious.",
        "llama_keep_alive_candidate_enabled": keep_alive,
        "requested_keep_alive": "5m" if keep_alive else 0,
        "stream": buffered,
        "buffered_until_complete": buffered,
        "unvalidated_stream_content_displayed": False,
    }
    if buffered:
        call.update(
            {
                "first_token_available": True,
                "first_content_chunk_seconds": 0.4,
            }
        )
    return {
        "shell_launch_id": "launch-1",
        "benchmark_request_id": "a" * 32,
        "completed": True,
        "configured_model_name": harness.EXPECTED_MODEL_NAME,
        "final_displayed_reply": "I feel present and curious.",
        "core_prompt_sha256": "b" * 64,
        "core_prompt_utf8_bytes": 1200,
        "one_turn_sensory_context_inserted": False,
        "sensory_cue_ids": [],
        "core_turn": {
            "model_name": harness.EXPECTED_MODEL_NAME,
            "response_route": "model",
            "model_calls": [call],
        },
    }


def _benchmark_records(route: str = "blackwell_gpu_persistent_candidate") -> list[dict]:
    persistent = "persistent_candidate" in route
    persistent_v2 = route.endswith("_v2")
    events = (
        "request_submitted",
        "chat_request_received",
        "text_ready",
        "voice_payload_ready",
        "voice_pipeline_start",
        "chunk_synthesis_start",
        "chunk_synthesis_end",
        "chunk_playback_start",
        "first_playback_proxy",
        "chunk_playback_end",
        "request_completed",
    )
    rows = []
    for index, event in enumerate(events, start=1):
        details: dict = {}
        if event == "chunk_synthesis_end":
            details = {
                "generated": True,
                "route_id": route,
                "approved_voice_path_used": "blackwell_gpu",
                "device": "cuda",
                "gpu_synthesis_attempted": True,
                "gpu_actual_allocation": True,
                "cpu_synthesis_attempted": False,
                "automatic_cpu_fallback_used": False,
                "persistent_worker_reused": persistent,
                "sidecar_lifecycle": (
                    "session_owned_persistent_candidate_v2"
                    if persistent_v2
                    else "session_owned_persistent_candidate"
                    if persistent
                    else "one_shot"
                ),
            }
            if persistent_v2:
                details.update(
                    {
                        "gpu_actual_execution": True,
                        "generic_voice_used": False,
                        "sapi_voice_used": False,
                        "fallback_used": False,
                        "test_only_injected_client": False,
                        "qwen_absence_proven_for_accepted_generation": True,
                        "production_route_promoted": False,
                        "production_routing_authorized": False,
                    }
                )
        if event == "request_completed":
            details = {
                "complete": True,
                "expected_vs_synthesized_exact": True,
                "expected_vs_playback_proxy_exact": True,
                "voice_identity_unchanged": True,
                "audio_generated": True,
                "audio_played": True,
            }
        rows.append(
            {
                "request_id": "c" * 32,
                "sequence": index,
                "event": event,
                "monotonic_ns": index * 1_000_000,
                "details": details,
                "privacy": {
                    "raw_prompt_recorded": False,
                    "raw_reply_recorded": False,
                },
            }
        )
    return rows


class KiraTextVoiceTwoTurnLatencyAcceptanceTests(unittest.TestCase):
    def test_default_description_is_inert_and_exactly_two_turns(self) -> None:
        result = harness.describe()
        self.assertTrue(result["default_inert"])
        self.assertFalse(result["live_operation_started"])
        self.assertFalse(result["browser_opened"])
        self.assertEqual(len(result["exact_turns"]), 2)
        self.assertEqual(result["exact_model"]["digest"], harness.EXPECTED_MODEL_DIGEST)
        self.assertEqual(result["voice_policy"]["only_automatic_fallback"], "sealed_cpu")
        self.assertFalse(result["voice_policy"]["sapi_allowed"])
        self.assertFalse(result["voice_policy"]["generic_voice_allowed"])

    def test_main_without_live_flag_never_calls_live_runner(self) -> None:
        with patch.object(harness, "run_live_acceptance") as live:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(harness.main([]), 0)
        live.assert_not_called()

    def test_owner_hearing_config_is_append_only_rebound_and_inert(self) -> None:
        result = harness.validate_prepared_owner_hearing_config()
        self.assertTrue(result["passed"])
        self.assertFalse(result["historical_snapshot_valid"])
        self.assertTrue(result["compatible_pre_v2_snapshot"])
        self.assertFalse(result["current_harness_matches"])
        self.assertEqual(result["mode"], "persistent_voice")
        self.assertEqual(result["exact_turn_count"], 2)
        self.assertFalse(result["live_execution_started"])
        self.assertEqual(
            result["persistent_prerequisite_status"],
            "PENDING_NEW_POST_REPAIR_STANDALONE_PASS",
        )
        with patch.object(harness, "run_live_acceptance") as live:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    harness.main(
                        [
                            "--validate-prepared-config",
                            str(harness.PREPARED_OWNER_HEARING_CONFIG),
                        ]
                    ),
                    0,
                )
        live.assert_not_called()

    def test_execute_live_still_requires_all_explicit_confirmations(self) -> None:
        with patch.object(harness, "run_live_acceptance") as live:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(harness.main(["--execute-live"]), 2)
        live.assert_not_called()

    def test_environment_modes_are_exact_and_do_not_mutate_base(self) -> None:
        base = {
            "KIRA_MODEL_NAME": "qwen3.5:9b",
            "KIRA_VOICE_FORCE_SAPI": "1",
            "UNRELATED": "preserved",
        }
        original = dict(base)
        with tempfile.TemporaryDirectory() as tmpdir:
            env = harness.build_environment(
                base,
                mode="persistent_voice_llama_keep_alive_buffered",
                runtime_dir=Path(tmpdir),
                shell_token="shell",
                asr_token="asr",
                visual_token="visual",
                launch_id="launch",
                keep_alive_duration="30s",
            )
        self.assertEqual(base, original)
        self.assertEqual(env["KIRA_MODEL_NAME"], harness.EXPECTED_MODEL_NAME)
        self.assertEqual(env["KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE"], "1")
        self.assertEqual(env["KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2"], "0")
        self.assertEqual(env["KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE"], "1")
        self.assertEqual(env["KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE"], "1")
        self.assertEqual(env["KIRA_LLAMA_KEEP_ALIVE_CANDIDATE_DURATION"], "30s")
        self.assertEqual(env["KIRA_ENABLE_QWEN_ONE_STILL"], "0")
        self.assertEqual(env["KIRA_VOICE_FORCE_SAPI"], "")
        self.assertEqual(env["UNRELATED"], "preserved")

        with tempfile.TemporaryDirectory() as tmpdir:
            baseline = harness.build_environment(
                {},
                mode="one_shot_baseline",
                runtime_dir=Path(tmpdir),
                shell_token="shell",
                asr_token="asr",
                visual_token="visual",
                launch_id="launch",
            )
        self.assertEqual(baseline["KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE"], "0")
        self.assertEqual(baseline["KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2"], "0")
        self.assertEqual(baseline["KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE"], "0")
        self.assertEqual(baseline["KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE"], "0")

        inherited = {
            harness.V1_PERSISTENT_FEATURE_FLAG: "1",
            harness.V2_PERSISTENT_FEATURE_FLAG: "1",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            v2 = harness.build_environment(
                inherited,
                mode="persistent_voice_v2_llama_keep_alive_buffered",
                runtime_dir=Path(tmpdir),
                shell_token="shell",
                asr_token="asr",
                visual_token="visual",
                launch_id="launch",
                keep_alive_duration="30s",
            )
        self.assertEqual(v2[harness.V1_PERSISTENT_FEATURE_FLAG], "0")
        self.assertEqual(v2[harness.V2_PERSISTENT_FEATURE_FLAG], "1")
        self.assertEqual(v2["KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE"], "1")
        self.assertEqual(v2["KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE"], "1")
        self.assertEqual(inherited[harness.V1_PERSISTENT_FEATURE_FLAG], "1")
        self.assertEqual(inherited[harness.V2_PERSISTENT_FEATURE_FLAG], "1")

    def test_keep_alive_duration_is_bounded(self) -> None:
        self.assertEqual(harness.normalized_keep_alive("5s"), "5s")
        self.assertEqual(harness.normalized_keep_alive("10m"), "10m")
        for invalid in ("", "4s", "11m", "forever", "0s"):
            with self.assertRaises(harness.LatencyAcceptanceError):
                harness.normalized_keep_alive(invalid)

    def test_v2_mode_and_protected_bindings_are_distinct_and_complete(self) -> None:
        mode = harness.describe(
            "persistent_voice_v2_llama_keep_alive_buffered"
        )
        self.assertTrue(mode["default_inert"])
        self.assertEqual(mode["mode_contract"]["persistent_version"], "v2")
        self.assertEqual(
            mode["voice_policy"]["preferred"],
            "blackwell_gpu_persistent_candidate_v2",
        )
        protected = {Path(path).resolve() for path in harness.PROTECTED_FILES}
        required = {
            harness.V2_APPLICATION_PASS_REPORT.resolve(),
            harness.V2_FULL_GPU_PASS_REPORT.resolve(),
            (harness.V2_CANDIDATE_ROOT / "candidate_config.json").resolve(),
            (harness.V2_CANDIDATE_ROOT / "candidate_contract.py").resolve(),
            (harness.V2_CANDIDATE_ROOT / "candidate_client.py").resolve(),
            (harness.V2_CANDIDATE_ROOT / "persistent_worker.py").resolve(),
            (harness.ROOT / "Core" / "persistent_blackwell_voice_integration_v2.py").resolve(),
            (harness.ROOT / "Core" / "voice_output.py").resolve(),
            (harness.ROOT / "Core" / "voice_benchmark_capture.py").resolve(),
            (harness.ROOT / "Tools" / "kira_world_shell_server.py").resolve(),
        }
        self.assertTrue(required.issubset(protected))

    def test_routing_contract_allows_only_blackwell_then_sealed_cpu(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifacts = {
                "profile.bin": b"profile",
                "reference.wav": b"reference",
                "gpu.json": b"gpu config",
                "gpu.py": b"gpu worker",
                "cpu.json": b"cpu config",
                "cpu.py": b"cpu worker",
            }
            for name, payload in artifacts.items():
                (root / name).write_bytes(payload)
            sha = {name: harness._sha256_file(root / name) for name in artifacts}
            routing = {
                "routing_id": "test",
                "approved_profile": "profile.bin",
                "approved_profile_sha256": sha["profile.bin"],
                "approved_reference": "reference.wav",
                "approved_reference_sha256": sha["reference.wav"],
                "policy": {
                    "preferred_route": "blackwell_gpu",
                    "automatic_fallback_routes": ["sealed_cpu"],
                    "gpu_requires_qwen_absence": True,
                    "public_spoken_only": True,
                    "playback_inside_sidecar": False,
                    "generic_voice_fallback_allowed": False,
                    "sapi_fallback_allowed": False,
                    "unsealed_in_process_fallback_allowed": False,
                    "unload_arbitrary_models_allowed": False,
                },
                "routes": [
                    {
                        "route_id": "blackwell_gpu",
                        "role": "preferred",
                        "compute_device": "cuda",
                        "config": "gpu.json",
                        "config_sha256": sha["gpu.json"],
                        "worker": "gpu.py",
                        "worker_sha256": sha["gpu.py"],
                    },
                    {
                        "route_id": "sealed_cpu",
                        "role": "automatic_fallback_only",
                        "compute_device": "cpu",
                        "config": "cpu.json",
                        "config_sha256": sha["cpu.json"],
                        "worker": "cpu.py",
                        "worker_sha256": sha["cpu.py"],
                    },
                ],
            }
            path = root / "routing.json"
            path.write_text(json.dumps(routing), encoding="utf-8")
            result = harness.validate_voice_routing_contract(path, root=root)
            self.assertTrue(result["passed"])
            self.assertEqual(result["only_automatic_fallback"], "sealed_cpu")

            routing["policy"]["sapi_fallback_allowed"] = True
            path.write_text(json.dumps(routing), encoding="utf-8")
            with self.assertRaises(harness.LatencyAcceptanceError):
                harness.validate_voice_routing_contract(path, root=root)

    def test_persistent_prerequisite_is_hash_bound_and_append_only(self) -> None:
        required = {
            key: True
            for key in (
                "model_loaded_once",
                "reference_conditioned_once",
                "two_wavs_generated",
                "two_attempts_without_false_host_return_retries",
                "load_model_and_core_components_cuda",
                "load_cuda_synchronization",
                "load_no_rejected_runtime_warning",
                "first_truthful_gpu_execution",
                "second_truthful_gpu_execution",
                "accepted_output_tensors_cuda_never_claimed",
                "first_wav_valid",
                "second_wav_valid",
                "explicit_unload",
                "torch_allocation_returned",
                "model_unloaded",
                "qwen_absent_before",
                "qwen_absent_after",
                "worker_exit_clean",
                "no_playback",
                "no_fallback",
            )
        }
        report = {
            "artifact_kind": "persistent_blackwell_voice_candidate_acceptance",
            "passed": True,
            "engineering_pass": True,
            "protected_files_unchanged": True,
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "candidate_config_sha256": "d" * 64,
            "checks": required,
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "attempt_01" / "PERSISTENT_BLACKWELL_ACCEPTANCE.json"
            path.parent.mkdir()
            path.write_text(json.dumps(report), encoding="utf-8")
            result = harness.validate_persistent_prerequisite(
                path,
                acceptance_root=root,
                expected_config_sha256="d" * 64,
            )
            self.assertTrue(result["passed"])
            self.assertEqual(result["sha256"], harness._sha256_file(path))

            report["generic_voice_used"] = True
            path.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaises(harness.LatencyAcceptanceError):
                harness.validate_persistent_prerequisite(
                    path,
                    acceptance_root=root,
                    expected_config_sha256="d" * 64,
                )

    def test_v2_prerequisite_is_exact_hash_bound_and_fail_closed(self) -> None:
        source = json.loads(
            harness.V2_APPLICATION_PASS_REPORT.read_text(encoding="utf-8")
        )
        for relative, path in harness.V2_CURRENT_HOST_BINDINGS.items():
            source["protected_before"][relative] = harness._sha256_file(path)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "attempt_03" / "FINAL_REPORT.json"
            path.parent.mkdir()

            def write(payload: dict) -> str:
                path.write_text(json.dumps(payload), encoding="utf-8")
                return harness._sha256_file(path)

            report_hash = write(source)
            result = harness.validate_persistent_v2_prerequisite(
                path,
                acceptance_root=root,
                expected_report_sha256=report_hash,
            )
            self.assertTrue(result["passed"])
            self.assertEqual(result["selected_candidate_version"], "v2")
            self.assertEqual(result["exact_turn_count"], 2)
            self.assertFalse(result["owner_heard_acceptance"])
            self.assertFalse(result["promotion_performed"])

            route_tamper = json.loads(json.dumps(source))
            route_tamper["turns"][0]["result"]["route_id"] = (
                "blackwell_gpu_persistent_candidate"
            )
            route_hash = write(route_tamper)
            with self.assertRaises(harness.LatencyAcceptanceError):
                harness.validate_persistent_v2_prerequisite(
                    path,
                    acceptance_root=root,
                    expected_report_sha256=route_hash,
                )

            gpu_tamper = json.loads(json.dumps(source))
            gpu_tamper["turns"][0]["result"]["gpu_proof"][
                "actual_gpu_execution"
            ] = False
            gpu_hash = write(gpu_tamper)
            with self.assertRaises(harness.LatencyAcceptanceError):
                harness.validate_persistent_v2_prerequisite(
                    path,
                    acceptance_root=root,
                    expected_report_sha256=gpu_hash,
                )

            clean_hash = write(source)
            with self.assertRaises(harness.LatencyAcceptanceError):
                harness.validate_persistent_v2_prerequisite(
                    path,
                    acceptance_root=root,
                    expected_report_sha256="0" * 64,
                )
            self.assertEqual(clean_hash, harness._sha256_file(path))

            escaped = root / "FINAL_REPORT.json"
            escaped.write_text(json.dumps(source), encoding="utf-8")
            with self.assertRaises(harness.LatencyAcceptanceError):
                harness.validate_persistent_v2_prerequisite(
                    escaped,
                    acceptance_root=root,
                    expected_report_sha256=harness._sha256_file(escaped),
                )

    def test_private_model_audit_enforces_each_candidate_mode(self) -> None:
        plain = harness.validate_private_model_audit(
            _private_audit(buffered=False, keep_alive=False),
            launch_id="launch-1",
            request_id="a" * 32,
            displayed_reply="I feel present and curious.",
            mode="persistent_voice",
            keep_alive_duration="5m",
        )
        self.assertEqual(plain["core_turn"]["model_calls"][0]["requested_keep_alive"], 0)

        buffered = harness.validate_private_model_audit(
            _private_audit(buffered=True, keep_alive=True),
            launch_id="launch-1",
            request_id="a" * 32,
            displayed_reply="I feel present and curious.",
            mode="persistent_voice_llama_keep_alive_buffered",
            keep_alive_duration="5m",
        )
        self.assertTrue(buffered["core_turn"]["model_calls"][0]["first_token_available"])

        v2_buffered = harness.validate_private_model_audit(
            _private_audit(buffered=True, keep_alive=True),
            launch_id="launch-1",
            request_id="a" * 32,
            displayed_reply="I feel present and curious.",
            mode="persistent_voice_v2_llama_keep_alive_buffered",
            keep_alive_duration="5m",
        )
        self.assertTrue(
            v2_buffered["core_turn"]["model_calls"][0]["first_token_available"]
        )

        mismatch = _private_audit(buffered=False, keep_alive=False)
        mismatch["core_turn"]["model_calls"][0]["model_name"] = "qwen3.5:9b"
        with self.assertRaises(Exception):
            harness.validate_private_model_audit(
                mismatch,
                launch_id="launch-1",
                request_id="a" * 32,
                displayed_reply="I feel present and curious.",
                mode="persistent_voice",
                keep_alive_duration="5m",
            )

    def test_benchmark_timeline_and_persistent_route_are_exact(self) -> None:
        records = _benchmark_records()
        timeline = harness.validate_benchmark_timeline(records)
        self.assertTrue(timeline["monotonic"])
        route = harness.classify_voice_route(harness._synthesis_rows(records), mode="persistent_voice")
        self.assertTrue(route["preferred_gpu_passed"])
        self.assertFalse(route["sealed_cpu_fallback_used"])

        stale_event_name = json.loads(json.dumps(records))
        stale_event_name[1]["event"] = "chat_received"
        with self.assertRaises(harness.LatencyAcceptanceError):
            harness.validate_benchmark_timeline(stale_event_name)

        records[2]["monotonic_ns"] = 0
        with self.assertRaises(harness.LatencyAcceptanceError):
            harness.validate_benchmark_timeline(records)

    def test_v2_benchmark_route_requires_exact_lifecycle_reuse_and_gpu_proof(self) -> None:
        records = _benchmark_records("blackwell_gpu_persistent_candidate_v2")
        rows = harness._synthesis_rows(records)
        result = harness.classify_voice_route(
            rows,
            mode="persistent_voice_v2_llama_keep_alive_buffered",
        )
        self.assertTrue(result["preferred_gpu_passed"])
        self.assertEqual(result["persistent_candidate_version"], "v2")
        self.assertEqual(
            result["expected_sidecar_lifecycle"],
            "session_owned_persistent_candidate_v2",
        )

        for key, bad_value in (
            ("persistent_worker_reused", False),
            ("sidecar_lifecycle", "session_owned_persistent_candidate"),
            ("gpu_actual_execution", False),
            ("generic_voice_used", True),
            ("sapi_voice_used", True),
            ("fallback_used", True),
            ("test_only_injected_client", True),
            ("qwen_absence_proven_for_accepted_generation", False),
            ("production_route_promoted", True),
            ("production_routing_authorized", True),
            ("cpu_synthesis_attempted", True),
        ):
            bad = dict(rows[0], **{key: bad_value})
            with self.assertRaises(harness.LatencyAcceptanceError):
                harness.classify_voice_route(
                    [bad],
                    mode="persistent_voice_v2_llama_keep_alive_buffered",
                )

        for missing_key in (
            "gpu_actual_execution",
            "generic_voice_used",
            "sapi_voice_used",
            "fallback_used",
            "test_only_injected_client",
            "qwen_absence_proven_for_accepted_generation",
            "production_route_promoted",
            "production_routing_authorized",
        ):
            missing = dict(rows[0])
            missing.pop(missing_key)
            with self.assertRaises(harness.LatencyAcceptanceError):
                harness.classify_voice_route(
                    [missing],
                    mode="persistent_voice_v2_llama_keep_alive_buffered",
                )

        wrong_route = dict(rows[0], route_id="blackwell_gpu_persistent_candidate")
        with self.assertRaises(harness.LatencyAcceptanceError):
            harness.classify_voice_route(
                [wrong_route],
                mode="persistent_voice_v2_llama_keep_alive_buffered",
            )

    def test_sealed_cpu_is_safe_fallback_but_not_candidate_pass(self) -> None:
        row = {
            "generated": True,
            "route_id": "sealed_cpu",
            "approved_voice_path_used": "sealed_cpu",
            "device": "cpu",
            "gpu_synthesis_attempted": True,
            "cpu_synthesis_attempted": True,
            "automatic_cpu_fallback_used": True,
            "preferred_failure_reason": "persistent_gpu_candidate_failed",
        }
        result = harness.classify_voice_route([row], mode="persistent_voice")
        self.assertTrue(result["approved_routes_only"])
        self.assertTrue(result["sealed_cpu_fallback_used"])
        self.assertFalse(result["preferred_gpu_passed"])

        for route in ("windows_sapi", "generic_voice"):
            bad = dict(row, route_id=route, approved_voice_path_used=route)
            with self.assertRaises(harness.LatencyAcceptanceError):
                harness.classify_voice_route([bad], mode="persistent_voice")

        for forbidden_flag in ("generic_voice_used", "sapi_voice_used"):
            bad = dict(row, **{forbidden_flag: True})
            with self.assertRaises(harness.LatencyAcceptanceError):
                harness.classify_voice_route([bad], mode="persistent_voice")

    def test_wav_evidence_is_exact_hashed_and_non_silent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "turn.wav"
            payload = io.BytesIO()
            with wave.open(payload, "wb") as writer:
                writer.setnchannels(1)
                writer.setsampwidth(2)
                writer.setframerate(24000)
                writer.writeframes(
                    b"".join(
                        value.to_bytes(2, "little", signed=True)
                        for value in (0, 12000, -12000, 0)
                    )
                )
            path.write_bytes(payload.getvalue())
            evidence = harness.wav_evidence(path, root=root)
            self.assertEqual(evidence["path"], "turn.wav")
            self.assertEqual(len(evidence["sha256"]), 64)
            self.assertTrue(evidence["readable_non_silent"])

    def test_gpu_summary_proves_peak_and_return_without_live_gpu(self) -> None:
        baseline = {"gpus": [{"index": 0, "memory_used_mib": 1000.0}]}
        final = {"gpus": [{"index": 0, "memory_used_mib": 1100.0}]}
        samples = [
            {"phase": "turn_1", "snapshot": {"gpus": [{"index": 0, "memory_used_mib": 5000.0}]}},
            {"phase": "turn_2", "snapshot": {"gpus": [{"index": 0, "memory_used_mib": 4700.0}]}},
        ]
        result = harness.summarize_gpu_samples(samples, baseline=baseline, final=final)
        self.assertEqual(result["peak_delta_mib"], 4000.0)
        self.assertTrue(result["vram_returned"])

    def test_gpu_sampler_queries_only_explicit_boundaries(self) -> None:
        snapshots = []

        def snapshot() -> dict:
            value = len(snapshots) + 1
            result = {
                "available": True,
                "gpus": [{"index": 0, "memory_used_mib": float(value)}],
            }
            snapshots.append(result)
            return result

        sampler = harness.GpuSampler(snapshot=snapshot)
        sampler.start()
        sampler.mark("server_start")
        sampler.mark("turn_1_text_and_voice")
        samples = sampler.stop()

        self.assertEqual(len(snapshots), 4)
        self.assertEqual(len(samples), 4)
        self.assertEqual(
            {item["sampling_mode"] for item in samples},
            {"explicit_phase_boundary_only"},
        )
        self.assertEqual(samples[1]["phase"], "server_start")
        self.assertEqual(samples[2]["phase"], "turn_1_text_and_voice")
        with self.assertRaises(harness.LatencyAcceptanceError):
            sampler.start()

    def test_residency_and_exact_unload_fail_closed(self) -> None:
        empty = {"resident_models": []}
        self.assertTrue(harness.validate_residency(empty, expect_llama=False)["qwen_absent"])
        self.assertFalse(harness.unload_exact_llama_if_owned(empty)["attempted"])

        qwen = {"resident_models": [{"name": "qwen3.5:9b", "digest": "x" * 64}]}
        with self.assertRaises(harness.LatencyAcceptanceError):
            harness.validate_residency(qwen, expect_llama=False)
        with self.assertRaises(harness.LatencyAcceptanceError):
            harness.unload_exact_llama_if_owned(qwen)

    def test_persistent_release_requires_exact_owned_worker_cleanup(self) -> None:
        event = {
            "event": "voice_model_release",
            "result": {
                "released": True,
                "reason": "persistent_model_released",
                "device": "cuda",
                "playback": False,
                "generated_audio": False,
                "persistent_release": {
                    "persistent_integration": True,
                    "cleanup": {
                        "owned_worker_was_present": True,
                        "owned_worker_closed": True,
                        "owned_process_exit_code": 0,
                        "owned_process_forced_termination": False,
                        "unload_error_type": "",
                        "close_error_type": "",
                    },
                },
            },
        }
        result = harness.validate_voice_release_event(event, persistent_expected=True)
        self.assertTrue(result["passed"])

        event["result"]["persistent_release"]["cleanup"]["owned_worker_closed"] = False
        with self.assertRaises(harness.LatencyAcceptanceError):
            harness.validate_voice_release_event(event, persistent_expected=True)

    def test_v2_release_requires_exact_owner_bound_cleanup(self) -> None:
        owner_release = {
            "released": True,
            "release_attempted": True,
            "owner_matched": True,
            "persistent_integration": True,
            "cleanup_debt": False,
            "cleanup": {
                "owned_worker_was_present": True,
                "owned_worker_closed": True,
                "owned_process_exit_code": 0,
                "owned_process_forced_termination": False,
                "cleanup_thread_finished": True,
                "unload_error_type": "",
                "close_error_type": "",
            },
            "playback": False,
            "generated_audio": False,
        }
        event = {
            "event": "voice_model_release",
            "result": {
                "released": True,
                "reason": "persistent_session_closed",
                "device": "cuda",
                "persistent_cleanup_proven": True,
                "persistent_release": None,
                "owner_bound_persistent_release": owner_release,
                "playback": False,
                "generated_audio": False,
            },
        }
        result = harness.validate_voice_release_event(
            event,
            persistent_expected=True,
            persistent_version="v2",
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["persistent_version"], "v2")
        self.assertTrue(
            result["owner_bound_persistent_release"]["cleanup"][
                "owned_worker_closed"
            ]
        )

        for key, bad_value in (
            ("owner_matched", False),
            ("cleanup_debt", True),
        ):
            bad_event = json.loads(json.dumps(event))
            bad_event["result"]["owner_bound_persistent_release"][key] = bad_value
            with self.assertRaises(harness.LatencyAcceptanceError):
                harness.validate_voice_release_event(
                    bad_event,
                    persistent_expected=True,
                    persistent_version="v2",
                )

        bad_cleanup = json.loads(json.dumps(event))
        bad_cleanup["result"]["owner_bound_persistent_release"]["cleanup"][
            "owned_worker_closed"
        ] = False
        with self.assertRaises(harness.LatencyAcceptanceError):
            harness.validate_voice_release_event(
                bad_cleanup,
                persistent_expected=True,
                persistent_version="v2",
            )

    def test_release_capture_records_absence_as_failure_instead_of_inference(self) -> None:
        with patch.object(
            harness,
            "wait_for_life_event",
            side_effect=harness.LatencyAcceptanceError("release row absent"),
        ):
            evidence = harness.capture_voice_release_cleanup_evidence(
                Path("unused.jsonl"),
                activation_started_at="2026-08-04T00:00:00Z",
                persistent_expected=True,
                persistent_version="v2",
                timeout_seconds=0,
            )
        self.assertIsNone(evidence["voice_model_release_event"])
        self.assertFalse(evidence["voice_model_release_contract"]["passed"])
        self.assertEqual(
            evidence["voice_model_release_contract"]["reason"],
            "voice_release_evidence_not_proven",
        )

        not_activated = harness.capture_voice_release_cleanup_evidence(
            Path("unused.jsonl"),
            activation_started_at="",
            persistent_expected=True,
            persistent_version="v2",
            timeout_seconds=0,
        )
        self.assertFalse(not_activated["voice_model_release_contract"]["passed"])

    def test_cleanup_port_measurement_requires_three_successful_closed_probes(self) -> None:
        with patch.object(harness.bounded, "port_is_open", return_value=False) as probe:
            closed = harness.measure_cleanup_ports(timeout_seconds=0)
        self.assertTrue(closed["ports_closed"])
        self.assertEqual(probe.call_count, 3)

        with patch.object(
            harness.bounded,
            "port_is_open",
            side_effect=lambda port: port == harness.bounded.SHELL_PORT,
        ):
            open_port = harness.measure_cleanup_ports(timeout_seconds=0)
        self.assertFalse(open_port["ports_closed"])

        with patch.object(
            harness.bounded,
            "port_is_open",
            side_effect=OSError("probe failed"),
        ):
            probe_failed = harness.measure_cleanup_ports(timeout_seconds=0)
        self.assertFalse(probe_failed["ports_closed"])
        self.assertTrue(probe_failed["port_probe_errors"])

    def test_exact_cleanup_validation_fails_closed_on_missing_or_false_evidence(self) -> None:
        valid = {
            "exact_owned_server_exited": True,
            "ports_closed": True,
            "voice_model_release_contract": {"passed": True},
        }
        self.assertTrue(harness.validate_exact_cleanup_evidence(valid)["passed"])

        missing = harness.validate_exact_cleanup_evidence({})
        self.assertFalse(missing["passed"])
        self.assertEqual(len(missing["issues"]), 3)

        for key in ("exact_owned_server_exited", "ports_closed"):
            contradictory = dict(valid, **{key: False})
            self.assertFalse(
                harness.validate_exact_cleanup_evidence(contradictory)["passed"]
            )
        bad_release = dict(valid, voice_model_release_contract={"passed": False})
        self.assertFalse(harness.validate_exact_cleanup_evidence(bad_release)["passed"])

    def test_attempt_directories_are_append_only_per_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first = harness.allocate_attempt_directory("persistent_voice", root=root)
            second = harness.allocate_attempt_directory("persistent_voice", root=root)
            other = harness.allocate_attempt_directory("one_shot_baseline", root=root)
            v2 = harness.allocate_attempt_directory(
                "persistent_voice_v2_llama_keep_alive_buffered",
                root=root,
            )
        self.assertEqual(first.name, "attempt_01")
        self.assertEqual(second.name, "attempt_02")
        self.assertEqual(other.name, "attempt_01")
        self.assertEqual(v2.name, "attempt_01")


if __name__ == "__main__":
    unittest.main()
