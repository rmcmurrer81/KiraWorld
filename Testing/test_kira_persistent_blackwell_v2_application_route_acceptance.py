from __future__ import annotations

import importlib.util
import ast
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = (
    ROOT / "Tools" / "run_kira_persistent_blackwell_v2_application_route_acceptance.py"
)
SPEC = importlib.util.spec_from_file_location(
    "kira_persistent_v2_application_route_acceptance_harness",
    HARNESS_PATH,
)
assert SPEC is not None and SPEC.loader is not None
harness = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = harness
SPEC.loader.exec_module(harness)


def _qwen_absent() -> dict:
    return {
        "query_succeeded": True,
        "qwen_absent_proven": True,
        "qwen_records": [],
        "model_state_changed": False,
    }


def _safe_load_qwen_absent() -> dict:
    return {
        "query_succeeded": True,
        "qwen_absent_proven": True,
        "qwen_record_count": 0,
        "model_state_changed": False,
    }


class PersistentV2ApplicationRouteAcceptancePreparationTests(unittest.TestCase):
    def test_exact_public_sentences_and_identity_hashes_are_pinned(self) -> None:
        self.assertEqual(len(harness.PUBLIC_SPOKEN_SENTENCES), 2)
        self.assertEqual(
            harness.PUBLIC_SPOKEN_SENTENCES[0],
            "I don't see anything and I don't hear anything.",
        )
        self.assertNotEqual(
            harness.PUBLIC_SPOKEN_SENTENCES[0], harness.PUBLIC_SPOKEN_SENTENCES[1]
        )
        self.assertEqual(
            harness.PUBLIC_SPOKEN_SHA256,
            tuple(
                harness.hashlib.sha256(value.encode("utf-8")).hexdigest()
                for value in harness.PUBLIC_SPOKEN_SENTENCES
            ),
        )
        self.assertEqual(
            harness.sha256_file(ROOT / harness.APPROVED_PROFILE_RELATIVE),
            harness.APPROVED_PROFILE_SHA256,
        )
        self.assertEqual(
            harness.sha256_file(ROOT / harness.APPROVED_REFERENCE_RELATIVE),
            harness.APPROVED_REFERENCE_SHA256,
        )
        self.assertEqual(
            harness.sha256_file(ROOT / harness.FULL_GPU_PASS_RELATIVE),
            harness.FULL_GPU_PASS_SHA256,
        )

    def test_v2_only_environment_disables_every_other_synthesis_route(self) -> None:
        parent = {
            harness.V2_FEATURE_FLAG: "0",
            harness.V1_FEATURE_FLAG: "1",
            "KIRA_VOICE_FORCE_SAPI": "1",
            "UNRELATED_OWNER_VALUE": "preserved",
        }
        child = harness._build_child_environment(parent)
        for key, expected in harness.EXACT_CHILD_ENVIRONMENT.items():
            self.assertEqual(child[key], expected)
        self.assertEqual(child["UNRELATED_OWNER_VALUE"], "preserved")
        self.assertEqual(child[harness.V2_FEATURE_FLAG], "1")
        self.assertEqual(child[harness.V1_FEATURE_FLAG], "0")
        self.assertEqual(child["KIRA_DISABLE_BLACKWELL_GPU_VOICE"], "1")
        self.assertEqual(child["KIRA_DISABLE_CHATTERBOX_PY311_SIDECAR"], "1")
        self.assertEqual(child["KIRA_VOICE_FORCE_SAPI"], "0")

    def test_production_routing_and_all_sealed_v1_hashes_match(self) -> None:
        observed = harness.protected_hashes()
        self.assertEqual(harness.pinned_hash_issues(observed), [])
        for relative, expected in harness.PINNED_PROTECTED_HASHES.items():
            self.assertEqual(observed[relative], expected)

    def test_real_load_telemetry_contract_requires_qwen_and_cuda_proof(self) -> None:
        prewarm = {
            "warmed": True,
            "device": "cuda",
            "selected_candidate_version": "v2",
            "test_only_injected_client": False,
            "load_telemetry": {
                "telemetry_scope": "initial_worker_start_and_model_load",
                "ready": True,
                "model_reused": False,
                "operation_seconds": 25.0,
                "worker_start": {
                    "ready": True,
                    "model_loaded_before_explicit_load": False,
                    "worker_sha256": harness.V2_WORKER_SHA256,
                    "config_sha256": harness.V2_CONFIG_SHA256,
                    "elapsed_seconds": 0.105,
                },
                "parent_transport_timing": {"elapsed_seconds": 25.1},
                "qwen_residency_before_load": _safe_load_qwen_absent(),
                "gpu_proof": {
                    "actual_gpu_allocation": True,
                    "persistent_model_allocation_present": True,
                    "cuda_synchronize_before_model_load_succeeded": True,
                    "cuda_synchronize_after_conditioning_succeeded": True,
                    "model_and_core_components_cuda": True,
                    "no_rejected_runtime_warnings": True,
                    "allocated_before_bytes": 0,
                    "allocated_after_bytes": 3_500_000_000,
                    "reserved_before_bytes": 0,
                    "reserved_after_bytes": 3_700_000_000,
                    "peak_allocated_bytes": 3_600_000_000,
                    "peak_reserved_bytes": 3_800_000_000,
                },
                "identity": {
                    "profile_sha256": harness.APPROVED_PROFILE_SHA256,
                    "reference_sha256": harness.APPROVED_REFERENCE_SHA256,
                },
                "runtime_versions": dict(harness.EXPECTED_RUNTIME_VERSIONS),
                "runtime_cuda_checks": {
                    key: True for key in harness.EXPECTED_RUNTIME_CUDA_CHECKS
                },
                "resources": {
                    "peak_process_rss_mib": 4_944.3,
                    "peak_system_ram_used_mib": 21_070.3,
                    "baseline_total_gpu_used_mib": 1_191.0,
                    "peak_total_gpu_used_mib": 4_816.0,
                    "peak_total_gpu_delta_mib": 3_625.0,
                    "host_sample_count": 99,
                    "external_gpu_sample_count": 2,
                },
                "phase_timings": [
                    {"phase": name, "elapsed_seconds": 0.01, "status": "passed"}
                    for name in harness.EXPECTED_LOAD_PHASES
                ],
                "lifecycle": {
                    "model_loaded": True,
                    "model_load_count": 1,
                    "reference_conditioning_count": 1,
                    "conditioned_reference_sha256": harness.APPROVED_REFERENCE_SHA256,
                },
            },
        }
        self.assertEqual(harness.load_telemetry_issues(prewarm), [])
        self.assertNotIn(
            "qwen_records",
            prewarm["load_telemetry"]["qwen_residency_before_load"],
        )
        prewarm["load_telemetry"]["qwen_residency_before_load"] = {
            **_safe_load_qwen_absent(),
            "qwen_absent_proven": False,
        }
        self.assertIn(
            "qwen_absence_not_proven_before_load",
            harness.load_telemetry_issues(prewarm),
        )
        prewarm["load_telemetry"]["qwen_residency_before_load"] = {
            **_safe_load_qwen_absent(),
            "qwen_records": [],
        }
        self.assertIn(
            "raw_qwen_records_exposed_in_safe_load_telemetry",
            harness.load_telemetry_issues(prewarm),
        )

    def test_turn_contract_is_exact_v2_gpu_no_fallback_and_no_playback(self) -> None:
        sentence = harness.PUBLIC_SPOKEN_SENTENCES[0]
        target = harness.GENERATED_ROOT / "unit_only" / "turn.wav"
        wav = {"passed": True, "sha256": "a" * 64}
        result = {
            "generated": True,
            "route_id": harness.EXPECTED_ROUTE_ID,
            "selected_candidate_version": "v2",
            "application_route_connected": True,
            "production_route_promoted": False,
            "approved_voice_path_used": "blackwell_gpu",
            "gpu_synthesis_attempted": True,
            "cpu_synthesis_attempted": False,
            "automatic_cpu_fallback_used": False,
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "playback": False,
            "channel": "public_spoken_only",
            "requested_text_bound": True,
            "device": "cuda",
            "profile_sha256": harness.APPROVED_PROFILE_SHA256,
            "reference_sha256": harness.APPROVED_REFERENCE_SHA256,
            "text_sha256": harness.hashlib.sha256(sentence.encode("utf-8")).hexdigest(),
            "test_only_injected_client": False,
            "full_gpu_acceptance_sha256": harness.FULL_GPU_PASS_SHA256,
            "conditioning_reused": True,
            "persistent_worker_reused": True,
            "sidecar_lifecycle": "session_owned_persistent_candidate_v2",
            "audio_path": str(target),
            "wav_validation": {"sha256": wav["sha256"]},
            "parent_qwen_residency_before_synthesis": _qwen_absent(),
            "gpu_proof": {
                "actual_gpu_execution": True,
                "persistent_model_allocation_present": True,
                "model_and_core_components_cuda": True,
                "cuda_synchronize_before_generation_succeeded": True,
                "cuda_synchronize_after_generation_succeeded": True,
                "generation_peak_exceeded_baseline": True,
                "no_rejected_runtime_warnings": True,
                "qwen_absence_proven_for_accepted_generation": True,
                "official_host_return_contract_satisfied": True,
                "accepted_output_tensors_host_cpu": True,
                "accepted_output_tensors_cuda": False,
            },
            "approved_voice_routing": {
                "actual_approved_path_used": "blackwell_gpu",
                "preferred_path": harness.EXPECTED_ROUTE_ID,
                "preferred_path_used": True,
                "automatic_cpu_fallback_used": False,
                "generic_voice_fallback_used": False,
                "sapi_fallback_used": False,
                "unsealed_in_process_fallback_used": False,
                "one_shot_gpu_rollback_invoked": False,
                "arbitrary_model_unload_performed": False,
            },
            "integration_elapsed_seconds": 2.1,
            "operation_seconds": 2.0,
            "parent_transport_timing": {"elapsed_seconds": 2.01},
        }
        self.assertEqual(
            harness.turn_issues(
                result,
                sentence=sentence,
                expected_path=target,
                wav_validation=wav,
            ),
            [],
        )
        result["cpu_synthesis_attempted"] = True
        self.assertIn(
            "turn_contract_mismatch:cpu_synthesis_attempted",
            harness.turn_issues(
                result,
                sentence=sentence,
                expected_path=target,
                wav_validation=wav,
            ),
        )

    def test_release_requires_exact_clean_owned_exit_and_vram_return(self) -> None:
        release = {
            "released": True,
            "persistent_cleanup_proven": True,
            "persistent_release": {
                "released": True,
                "owned_worker_closed": True,
                "model_was_loaded": True,
                "v1_release": None,
                "v2_release": {
                    "cleanup": {
                        "owned_worker_was_present": True,
                        "owned_worker_closed": True,
                        "owned_process_forced_termination": False,
                        "forced_for_inflight_operation": False,
                        "forced_for_unresponsive_idle_cleanup": False,
                        "cleanup_thread_finished": True,
                        "graceful_cleanup_bound_seconds": 20.0,
                        "owned_process_exit_code": 0,
                        "unload_reported": True,
                        "close_reported": True,
                        "unload_error_type": "",
                        "close_error_type": "",
                        "unload_telemetry": {
                            "reported": True,
                            "unloaded": True,
                            "model_was_loaded": True,
                            "operation_seconds": 0.15,
                            "parent_transport_timing": {"elapsed_seconds": 0.16},
                            "lifecycle_model_loaded_after": False,
                            "last_unload": {
                                "was_loaded": True,
                                "allocated_before_bytes": 3_510_000_000,
                                "allocated_after_bytes": 10_000_000,
                                "allocated_returned_bytes": 3_500_000_000,
                                "reserved_before_bytes": 3_730_000_000,
                                "reserved_after_bytes": 30_000_000,
                                "reserved_returned_bytes": 3_700_000_000,
                            },
                        },
                    }
                },
            }
        }
        after = {
            "session_owner": "",
            "owned_worker_running": False,
            "model_loaded": False,
            "candidate_versions": {
                "v1": {"owned_state_present": False},
                "v2": {"owned_state_present": False},
            },
        }
        self.assertEqual(harness.release_issues(release, after), [])
        release["persistent_release"]["v2_release"]["cleanup"][
            "owned_process_forced_termination"
        ] = True
        self.assertIn(
            "owned_v2_worker_forced_termination",
            harness.release_issues(release, after),
        )
        release["persistent_release"]["v2_release"]["cleanup"][
            "owned_process_forced_termination"
        ] = False
        release["persistent_release"]["v2_release"]["cleanup"][
            "forced_for_unresponsive_idle_cleanup"
        ] = True
        self.assertIn(
            "release_forced_unresponsive_idle_cleanup",
            harness.release_issues(release, after),
        )
        release["persistent_release"]["v2_release"]["cleanup"][
            "forced_for_unresponsive_idle_cleanup"
        ] = False
        release["persistent_release"]["v2_release"]["cleanup"][
            "unload_telemetry"
        ]["last_unload"]["allocated_after_bytes"] = 800_000_000
        self.assertIn(
            "owned_v2_unload_residual_too_large:allocated",
            harness.release_issues(release, after),
        )

    def test_external_gpu_boundary_must_return_near_preload_state(self) -> None:
        before = {
            "query_succeeded": True,
            "rows": [
                {"index": 0, "name": "NVIDIA GeForce RTX 5060 Ti", "memory_used_mib": 1200.0}
            ],
        }
        after = {
            "query_succeeded": True,
            "rows": [
                {"index": 0, "name": "NVIDIA GeForce RTX 5060 Ti", "memory_used_mib": 1300.0}
            ],
        }
        self.assertEqual(harness.gpu_release_boundary_issues(before, after), [])
        after["rows"][0]["memory_used_mib"] = 1600.0
        self.assertIn(
            "gpu_release_external_residual_over_256_mib:0",
            harness.gpu_release_boundary_issues(before, after),
        )

    def test_parent_wrapper_protected_change_and_exception_are_failures(self) -> None:
        protected = harness.protected_hashes()
        started = {"protected_before_parent": protected}
        wrapper = {
            "parent_exception": None,
            "timed_out": False,
            "child_exit_code": 0,
            "final_report_present": True,
            "protected_unchanged_from_attempt_start": True,
            "protected_after_parent": protected,
        }
        self.assertEqual(harness.parent_wrapper_issues(started, wrapper), [])
        wrapper["protected_unchanged_from_attempt_start"] = False
        self.assertIn(
            "parent_protected_files_changed",
            harness.parent_wrapper_issues(started, wrapper),
        )
        wrapper["protected_unchanged_from_attempt_start"] = True
        wrapper["parent_exception"] = {"type": "OSError"}
        self.assertIn("parent_exception", harness.parent_wrapper_issues(started, wrapper))

    def test_parent_spawn_exception_is_preserved_append_only(self) -> None:
        scratch = ROOT / "RecoverySprint" / "verification_scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temp_dir:
            temp_root = Path(temp_dir)
            evidence = temp_root / "evidence"
            generated = temp_root / "generated"
            with (
                patch.object(harness, "EVIDENCE_ROOT", evidence),
                patch.object(harness, "GENERATED_ROOT", generated),
                patch.object(harness.subprocess, "Popen", side_effect=OSError("spawn failed")),
            ):
                code = harness._parent_run("attempt_01")
            wrapper = json.loads(
                (evidence / "attempt_01" / "PARENT_WRAPPER.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(code, 1)
        self.assertEqual(wrapper["parent_exception"]["type"], "OSError")
        self.assertIn("parent_exception", wrapper["issues"])
        self.assertFalse(wrapper["child_spawned"])
        self.assertTrue(wrapper["exact_child_cleanup_proven"])

    def test_harness_is_bounded_append_only_and_has_no_live_test_side_effect(self) -> None:
        source = HARNESS_PATH.read_text(encoding="utf-8")
        self.assertIn("sys.path.insert(0, str(ROOT))", source)
        self.assertLess(harness.CHILD_WATCHDOG_SECONDS, harness.PARENT_CHILD_TIMEOUT_SECONDS)
        self.assertGreaterEqual(
            harness.PARENT_CHILD_TIMEOUT_SECONDS - harness.CHILD_WATCHDOG_SECONDS,
            60.0,
        )
        self.assertGreater(harness.PARENT_CHILD_TIMEOUT_SECONDS, 0)
        self.assertIn("exist_ok=False", source)
        self.assertIn("application_route_v2", source)
        self.assertIn("_synthesize_with_kira_chatterbox_sidecar", source)
        self.assertNotIn("voice_output.speak_text(", source)
        self.assertNotIn("voice_output.synthesize_text_to_wav(", source)
        self.assertNotIn("/api/generate", source)
        self.assertNotIn("ollama run", source.casefold())
        self.assertNotIn("blender.exe", source.casefold())
        self.assertNotIn("start-process", source.casefold())
        # The live voice host is imported only inside child/watchdog functions,
        # never as an import-time side effect of test discovery.
        tree = ast.parse(source)
        top_level_imports = [
            node
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        self.assertFalse(
            any(
                isinstance(node, ast.ImportFrom)
                and node.module == "Core"
                and any(alias.name == "voice_output" for alias in node.names)
                for node in top_level_imports
            )
        )


if __name__ == "__main__":
    unittest.main()
