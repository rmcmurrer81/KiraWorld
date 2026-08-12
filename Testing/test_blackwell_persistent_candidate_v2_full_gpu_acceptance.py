from __future__ import annotations

import ast
import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "Tools" / "run_persistent_blackwell_voice_candidate_v2_acceptance.py"
SPEC = importlib.util.spec_from_file_location("persistent_v2_full_gpu_harness_for_test", HARNESS_PATH)
assert SPEC is not None and SPEC.loader is not None
harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness)


def _qwen_absent() -> dict:
    return {
        "query_succeeded": True,
        "qwen_absent_proven": True,
        "qwen_records": [],
        "model_state_changed": False,
    }


def _flags() -> dict:
    return {
        "production_routing_authorized": False,
        "playback": False,
        "generic_voice_used": False,
        "sapi_voice_used": False,
        "fallback_used": False,
    }


def _resources() -> dict:
    return {
        "sample_count": 5,
        "peak_process_rss_mib": 4200.0,
        "peak_system_ram_used_mib": 16000.0,
        "peak_total_gpu_used_mib": 5000.0,
        "gpu_sampling_mode": "boundary_only_external_nvidia_smi",
        "background_external_gpu_polling": False,
        "gpu_peak_measurement_scope": "operation_boundary_snapshots_not_continuous_peak",
        "sampling_errors": [],
    }


def _nvidia() -> dict:
    return {
        "returncode": 0,
        "rows": [
            {
                "name": "NVIDIA GeForce RTX 5060 Ti",
                "driver_version": "999.99",
                "total_mib": 16384,
                "free_mib": 15000,
                "used_mib": 1384,
            }
        ],
        "stderr": "",
    }


def _valid_readiness(config: dict) -> dict:
    return {
        "schema_version": 1,
        "python": {
            "version": "3.11.9",
            "executable": str(harness.project_file(config["python"]).resolve()),
        },
        "nvidia_before": _nvidia(),
        "nvidia_after": _nvidia(),
        "versions": {
            "torch": "2.11.0+cu130",
            "torchaudio": "2.11.0+cu130",
            "torch_cuda_runtime": "13.0",
        },
        "cuda": {
            "available": True,
            "device_name": "NVIDIA GeForce RTX 5060 Ti",
            "device_capability": [12, 0],
            "compiled_architectures": ["sm_120"],
            "sm_120_compiled": True,
        },
        "cuda_operation": {
            "kind": "float32_cuda_matmul",
            "left_shape": [4096, 4096],
            "right_shape": [4096, 64],
            "result_shape": [4096, 64],
            "sample": [[8192.0, 8192.0], [8192.0, 8192.0]],
            "expected_value": 8192.0,
            "expected_result": True,
            "allocated_before_bytes": 0,
            "allocated_during_bytes": 70000000,
            "allocated_after_release_bytes": 0,
            "reserved_before_bytes": 0,
            "reserved_during_bytes": 80000000,
            "reserved_after_release_bytes": 0,
            "peak_allocated_bytes": 71000000,
            "peak_reserved_bytes": 81000000,
            "free_before_bytes": 15000000000,
            "free_during_bytes": 14900000000,
            "free_after_release_bytes": 15000000000,
            "total_before_bytes": 16000000000,
            "total_during_bytes": 16000000000,
            "total_after_bytes": 16000000000,
            "allocation_measurable": True,
            "release_measurable": True,
        },
        "checks": {"every_reviewed_gate": True},
        "issues": [],
        "errors": [],
        "captured_warnings": [],
        "rejected_warning_matches": [],
        "elapsed_seconds": 2.5,
        "status": "PASS",
    }


def _synthesis(config: dict, wav_hash: str) -> dict:
    qwen = _qwen_absent()
    attempt = {
        "attempt": 1,
        "passed": True,
        "output_tensor_device_type": "cpu",
        "output_tensor_returned_to_host": True,
        "official_host_return_contract_satisfied": True,
        "output_tensor_was_cuda": False,
        "rejected_warning_matches": [],
        "qwen_residency": qwen,
    }
    gpu = {
        "actual_gpu_execution": True,
        "model_and_core_components_cuda": True,
        "cuda_synchronize_before_generation_succeeded": True,
        "cuda_synchronize_after_generation_succeeded": True,
        "persistent_model_allocation_present": True,
        "generation_peak_exceeded_baseline": True,
        "no_rejected_runtime_warnings": True,
        "qwen_absence_proven_for_accepted_generation": True,
        "official_host_return_contract_satisfied": True,
        "accepted_output_tensors_host_cpu": True,
        "accepted_output_tensors_cuda": False,
        "allocated_before_bytes": 4000000000,
        "peak_allocated_bytes": 4100000000,
        "peak_reserved_bytes": 4300000000,
        "generation_peak_delta_bytes": 100000000,
    }
    return {
        **_flags(),
        "generated": True,
        "engine": "chatterbox_tts",
        "channel": "public_spoken_only",
        "text_sha256": harness.APPROVED_PUBLIC_SENTENCE_SHA256,
        "profile_sha256": config["approved_profile_sha256"],
        "reference_sha256": config["approved_reference_sha256"],
        "device": "cuda",
        "conditioning_reused": True,
        "wav_validation": {
            "passed": True,
            "non_silent": True,
            "duration_seconds": 2.0,
            "sha256": wav_hash,
        },
        "gpu_proof": gpu,
        "chunk_checks": [{"accepted_attempt": 1, "attempts": [attempt]}],
        "resources": _resources(),
        "generation_seconds": 3.0,
        "operation_seconds": 3.1,
        "phase_timings": [{"phase": "synthesis", "status": "passed"}],
        "parent_qwen_residency_before_synthesis": qwen,
    }


def _valid_full_report(config: dict) -> dict:
    qwen = _qwen_absent()
    hashes = {
        "Voice/sidecars/kira_approved_voice_routing.json": harness.PRODUCTION_ROUTING_SHA256,
        "another/protected/file": "a" * 64,
    }
    load_gpu = {
        "actual_gpu_allocation": True,
        "persistent_model_allocation_present": True,
        "model_and_core_components_cuda": True,
        "cuda_synchronize_before_model_load_succeeded": True,
        "cuda_synchronize_after_conditioning_succeeded": True,
        "no_rejected_runtime_warnings": True,
        "rejected_warning_matches": [],
        "peak_allocated_bytes": 4200000000,
        "peak_reserved_bytes": 4400000000,
    }
    load = {
        **_flags(),
        "identity": {
            "profile_sha256": config["approved_profile_sha256"],
            "reference_sha256": config["approved_reference_sha256"],
        },
        "model_reused": False,
        "runtime_cuda_checks": {
            key: True
            for key in (
                "torch_runtime",
                "torchaudio_runtime",
                "cuda_runtime",
                "cuda_available",
                "device",
                "capability",
                "sm_120",
            )
        },
        "gpu_proof": load_gpu,
        "resources": _resources(),
        "operation_seconds": 12.0,
        "phase_timings": [{"phase": "load", "status": "passed"}],
        "parent_qwen_residency_before_load": qwen,
        "qwen_residency": qwen,
    }
    report = {
        "import_only_prerequisite": {"sha256": harness.IMPORT_ONLY_REPORT_SHA256},
        "operator_bound_exact_harness": True,
        "operator_bound_exact_candidate_config": True,
        "promotion_performed": False,
        "routing_change_performed": False,
        "eager_cuda_preflight": {"passed": True, "wall_seconds": 2.0},
        "hello": {
            **_flags(),
            "ready": True,
            "model_loaded": False,
            "parent_process_start_timing": {"elapsed_seconds": 0.3},
        },
        "status_before_load": {
            **_flags(),
            "lifecycle": {"model_loaded": False, "model_load_count": 0},
        },
        "load": load,
        "first_synthesis": _synthesis(config, "1" * 64),
        "second_synthesis": _synthesis(config, "2" * 64),
        "status_before_unload": {
            **_flags(),
            "lifecycle": {
                "model_load_count": 1,
                "reference_conditioning_count": 1,
                "successful_synthesis_count": 2,
                "generation_attempt_count": 2,
            },
        },
        "unload": {
            **_flags(),
            "unloaded": True,
            "lifecycle": {
                "last_unload": {
                    "allocated_before_bytes": 4000000000,
                    "allocated_after_bytes": 0,
                    "allocated_returned_bytes": 4000000000,
                    "reserved_before_bytes": 4300000000,
                    "reserved_after_bytes": 0,
                    "reserved_returned_bytes": 4300000000,
                    "phase_timings": [
                        {
                            "phase": "unload.cuda_empty_cache_and_synchronize",
                            "status": "passed",
                        }
                    ],
                }
            },
        },
        "status_after_unload": {**_flags(), "lifecycle": {"model_loaded": False}},
        "worker_shutdown": {
            "clean_exit": True,
            "exact_owned_cleanup_only": True,
            "drains_finalized": True,
            "owned_process_exit_code": 0,
            "forced_termination": False,
            "close_response": {**_flags()},
        },
        "qwen_boundaries": {
            key: _qwen_absent()
            for key in ("before_eager", "before_load", "before_first", "before_second", "after_unload")
        },
        "protected_before": hashes,
        "protected_after": copy.deepcopy(hashes),
        "diagnostic_evidence": {
            "phase_events": {"present": True, "sha256": "3" * 64},
            "stderr": {"present": True, "sha256": "4" * 64},
        },
        "total_wall_seconds": 25.0,
    }
    report["performance_summary"] = harness.performance_summary(report)
    return report


class _FinishedDrain:
    def __init__(self) -> None:
        self.joined = False

    def join(self, timeout: float) -> None:
        self.joined = timeout == harness.CLEANUP_DRAIN_TIMEOUT_SECONDS

    def is_alive(self) -> bool:
        return not self.joined


class _Process:
    pid = 1234
    returncode = 0


class _Client:
    def __init__(self) -> None:
        self.process = _Process()
        self._stdout_thread = _FinishedDrain()
        self._stderr_thread = _FinishedDrain()

    def close(self) -> dict:
        self.process = None
        return {
            "owned_process_exit_code": 0,
            "owned_process_forced_termination": False,
        }


class PersistentV2FullGpuHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = harness.load_candidate_config(harness.CONFIG_PATH)

    def test_describe_and_static_self_check_are_inert(self) -> None:
        before = harness._attempt_names()
        torch_before = "torch" in sys.modules
        description = harness.describe()
        checked = harness.static_self_check()
        self.assertEqual(before, harness._attempt_names())
        self.assertFalse(description["live_execution_performed"])
        self.assertFalse(description["promotion_authorized"])
        self.assertFalse(description["playback_authorized"])
        self.assertTrue(checked["passed"], checked)
        self.assertEqual(torch_before, "torch" in sys.modules)

    def test_cli_without_all_bindings_refuses_before_attempt(self) -> None:
        before = harness._attempt_names()
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [sys.executable, "-B", str(HARNESS_PATH), "--run-full-gpu-v2"],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertEqual(before, harness._attempt_names())
        self.assertFalse(json.loads(completed.stdout)["attempt_created"])

    def test_wrong_harness_binding_rejects_without_live_probe(self) -> None:
        with patch.object(
            harness,
            "active_blender_evidence",
            side_effect=AssertionError("live probe must not run"),
        ):
            with self.assertRaisesRegex(ValueError, "harness SHA-256"):
                harness._validate_live_bindings(
                    expected_harness_sha256="0" * 64,
                    expected_candidate_config_sha256=harness.V2_CONFIG_SHA256,
                    expected_import_only_report_sha256=harness.IMPORT_ONLY_REPORT_SHA256,
                )

    def test_exact_import_only_report_and_semantic_mutations(self) -> None:
        path = ROOT / harness.IMPORT_ONLY_REPORT_RELATIVE
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(harness.validate_import_only_report_payload(payload), [])
        for path_parts, value in (
            (("status",), "failed"),
            (("trusted_child_result",), 1),
            (("cleanup", "drains_finalized"), False),
            (("outcomes", "generic_voice_used"), True),
            (("routing_change_performed",), True),
            (("child_result_evidence", "payload", "v2_worker_sha256"), "0" * 64),
        ):
            changed = copy.deepcopy(payload)
            target = changed
            for part in path_parts[:-1]:
                target = target[part]
            target[path_parts[-1]] = value
            self.assertTrue(
                harness.validate_import_only_report_payload(changed),
                (path_parts, value),
            )

    def test_eager_matrix_payload_is_strict(self) -> None:
        payload = _valid_readiness(self.config)
        self.assertEqual(
            harness.validate_eager_cuda_payload(payload, config=self.config),
            [],
        )
        mutations = []
        for mutate in (
            lambda value: value["python"].update(version="3.11.8"),
            lambda value: value["cuda_operation"].update(left_shape=[2, 2]),
            lambda value: value["cuda_operation"].update(sample=[[0.0, 0.0], [0.0, 0.0]]),
            lambda value: value["cuda_operation"].update(allocated_during_bytes=0),
            lambda value: value.update(rejected_warning_matches=["no kernel image"]),
            lambda value: value["nvidia_before"].update(returncode=1),
        ):
            changed = copy.deepcopy(payload)
            mutate(changed)
            mutations.append(harness.validate_eager_cuda_payload(changed, config=self.config))
        self.assertTrue(all(mutations), mutations)

    def test_full_synthetic_acceptance_checks_and_regressions(self) -> None:
        report = _valid_full_report(self.config)
        checks = harness.build_acceptance_checks(report, self.config)
        self.assertTrue(all(checks.values()), checks)
        changed = copy.deepcopy(report)
        changed["second_synthesis"]["fallback_used"] = True
        self.assertFalse(
            harness.build_acceptance_checks(changed, self.config)[
                "second_warm_wav_exact_readable_non_silent_cuda"
            ]
        )
        changed = copy.deepcopy(report)
        changed["qwen_boundaries"]["before_second"]["qwen_absent_proven"] = False
        self.assertFalse(
            harness.build_acceptance_checks(changed, self.config)[
                "qwen_absent_at_every_harness_boundary"
            ]
        )

    def test_resource_summary_does_not_mislabel_boundary_gpu_snapshot(self) -> None:
        summary = harness.performance_summary(_valid_full_report(self.config))
        self.assertEqual(summary["authoritative_vram_peak_source"], "torch_allocator_per_operation")
        self.assertFalse(summary["boundary_total_gpu_is_continuous_peak"])
        self.assertEqual(summary["max_authoritative_torch_peak_allocated_bytes"], 4200000000)
        self.assertEqual(summary["max_boundary_total_gpu_used_mib"], 5000.0)

    def test_close_joins_both_drains_after_exact_owned_child(self) -> None:
        client = _Client()
        result = harness.close_exact_client(client)
        self.assertTrue(result["clean_exit"], result)
        self.assertTrue(result["drains_finalized"])
        self.assertTrue(result["exact_owned_cleanup_only"])
        self.assertIs(client.process, None)

    def test_failure_outcomes_remain_unknown_without_evidence(self) -> None:
        outcomes = harness._observed_outcomes(
            {
                "promotion_performed": False,
                "routing_change_performed": False,
                "protected_files_unchanged": None,
            }
        )
        self.assertIsNone(outcomes["audio_generated"])
        self.assertIsNone(outcomes["playback"])
        self.assertIsNone(outcomes["generic_voice_used"])
        self.assertIsNone(outcomes["worker_clean_exit"])

    def test_atomic_append_only_write_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kira_v2_atomic_") as value:
            target = Path(value) / "REPORT.json"
            digest = harness.atomic_json_exclusive(target, {"one": 1})
            self.assertEqual(digest, harness.sha256_file(target))
            with self.assertRaises(FileExistsError):
                harness.atomic_json_exclusive(target, {"two": 2})
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"one": 1})

    def test_attempt_allocator_is_append_only_and_gap_safe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kira_v2_attempts_") as value:
            root = Path(value)
            with patch.object(harness, "ACCEPTANCE_ROOT", root):
                first = harness.allocate_attempt_directory()
                (root / "attempt_03").mkdir()
                second = harness.allocate_attempt_directory()
            self.assertEqual(first.name, "attempt_01")
            self.assertEqual(second.name, "attempt_02")

    def test_harness_has_no_direct_torch_or_triton_import(self) -> None:
        tree = ast.parse(HARNESS_PATH.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        self.assertNotIn("torch", imported)
        self.assertNotIn("torchaudio", imported)
        self.assertNotIn("triton", imported)


if __name__ == "__main__":
    unittest.main()
