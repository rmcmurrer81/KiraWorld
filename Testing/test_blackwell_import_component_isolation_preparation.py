from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = ROOT / "tools" / "run_blackwell_import_component_isolation_probe.py"
V2_PATH = (
    ROOT
    / "tools"
    / "run_persistent_blackwell_protocol_import_only_control_pending_defender_state_v2.py"
)
PREDECESSOR_PATH = (
    ROOT
    / "tools"
    / "run_persistent_blackwell_protocol_import_only_control_pending_defender_state.py"
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


probe = load_module("blackwell_component_isolation_test_module", PROBE_PATH)
v2 = load_module("blackwell_pending_defender_v2_test_module", V2_PATH)


class BlackwellImportComponentIsolationPreparationTests(unittest.TestCase):
    def test_failed_attempt_is_exact_and_unchanged(self) -> None:
        evidence = probe.validate_failed_evidence()
        self.assertEqual(evidence["report_status"], "failed_preserved")
        self.assertFalse(evidence["failed_attempt_changed"])
        self.assertEqual(
            evidence["files"]["PROTOCOL_IMPORT_ONLY_PENDING_DEFENDER_STATE.json"][
                "sha256"
            ],
            "9bf47ced167c1d6733277516207426d1f5a4dc699caa900cbfd4228730349884",
        )
        self.assertEqual(
            evidence["files"]["POST_FAILURE_PROCESS_CHECK.json"]["sha256"],
            "c87cc5a66a05c274dec280505c3f474459b1cf64df2672cd0958661f06bada7a",
        )

    def test_probe_static_self_check_is_inert(self) -> None:
        result = probe.static_self_check()
        self.assertTrue(result["passed"], result)
        for key in (
            "blackwell_runtime_started",
            "torch_imported",
            "cuda_api_invoked",
            "model_loaded",
            "audio_generated",
            "playback_performed",
            "ollama_invoked",
            "defender_queried",
            "defender_changed",
            "blender_started",
            "candidate_promoted",
            "production_routing_changed",
        ):
            self.assertFalse(result[key], key)

    def test_each_single_component_arm_changes_only_one_primary_factor(self) -> None:
        worker = probe.ARM_SPECS["worker_context_only"]
        primary = (
            "worker_module_context",
            "nvidia_smi_boundary_call",
            "resource_sampler",
            "stdin_reader",
            "parent_pipe_drains_and_phase_fsync",
        )
        expected_differences = {
            "nvidia_boundary_only": {"nvidia_smi_boundary_call"},
            "resource_sampler_host_only": {"resource_sampler"},
            "stdin_reader_only": {"stdin_reader"},
            "pipe_drains_fsync_only": {"parent_pipe_drains_and_phase_fsync"},
        }
        for arm, expected in expected_differences.items():
            differences = {
                key
                for key in primary
                if probe.ARM_SPECS[arm][key] != worker[key]
            }
            self.assertEqual(differences, expected, arm)

    def test_worker_context_isolated_from_minimal_baseline(self) -> None:
        minimal = probe.ARM_SPECS["minimal_direct"]
        worker = probe.ARM_SPECS["worker_context_only"]
        primary = (
            "worker_module_context",
            "nvidia_smi_boundary_call",
            "resource_sampler",
            "stdin_reader",
            "parent_pipe_drains_and_phase_fsync",
        )
        differences = {key for key in primary if minimal[key] != worker[key]}
        self.assertEqual(differences, {"worker_module_context"})

    def test_combined_arm_contains_every_real_shape_component(self) -> None:
        combined = probe.ARM_SPECS["combined_real_shape"]
        self.assertTrue(combined["worker_module_context"])
        self.assertTrue(combined["nvidia_smi_boundary_call"])
        self.assertEqual(
            combined["resource_sampler"],
            "real_class_full_boundary_gpu_and_host",
        )
        self.assertTrue(combined["stdin_reader"])
        self.assertTrue(combined["parent_pipe_drains_and_phase_fsync"])

    def test_probe_runs_only_one_named_arm_and_caps_it_at_180_seconds(self) -> None:
        source = PROBE_PATH.read_text(encoding="utf-8")
        self.assertEqual(probe.MAX_ARM_TIMEOUT_SECONDS, 180.0)
        self.assertNotIn("for arm " + "in ARM_SPECS", source)
        self.assertIn("--arm", source)
        self.assertIn("run_one_arm(", source)

    def test_probe_contains_no_forbidden_runtime_path(self) -> None:
        source = PROBE_PATH.read_text(encoding="utf-8")
        child = source[source.index("\ndef child_arm") : source.index("\ndef _drain_stdout")]
        for marker in (
            "torch.cuda",
            'import_module("torchaudio")',
            'import_module("chatterbox")',
            "from_pretrained(",
            "winsound.PlaySound(",
            "sounddevice.play(",
            "sd.play(",
        ):
            self.assertNotIn(marker, child)

    def test_predecessor_wrapper_is_preserved(self) -> None:
        self.assertEqual(probe.sha256_file(PREDECESSOR_PATH), probe.PREDECESSOR_WRAPPER_SHA256)
        self.assertEqual(v2.sha256_file(PREDECESSOR_PATH), v2.PREDECESSOR_SHA256)

    def test_v2_missing_cleanup_evidence_is_unknown_not_false(self) -> None:
        result = v2.classify_cleanup(None, 0)
        self.assertIsNone(result["cleanup_clean"])
        self.assertEqual(result["cleanup_status"], "UNKNOWN_NO_VALIDATED_SHUTDOWN_RESPONSE")

    def test_v2_cleanup_requires_acknowledged_clean_owned_exit(self) -> None:
        clean = v2.classify_cleanup(
            {
                "operation": "shutdown",
                "shutdown": True,
                "owned_process_forced_termination": False,
            },
            0,
        )
        self.assertTrue(clean["cleanup_clean"])
        failed = v2.classify_cleanup(
            {"owned_process_forced_termination": True},
            1,
        )
        self.assertFalse(failed["cleanup_clean"])

    def test_v2_incomplete_outcome_evidence_is_unknown_not_false(self) -> None:
        result = v2.classify_prohibited_outcomes({"cuda_api_invoked": False})
        self.assertFalse(result["prohibited_outcomes_observed"])
        self.assertFalse(result["prohibited_outcomes_evidence_complete"])
        self.assertIsNone(result["prohibited_outcomes_absent"])

    def test_v2_complete_false_outcome_evidence_proves_absence(self) -> None:
        result = v2.classify_prohibited_outcomes(
            {
                "load_import_only": {
                    "cuda_api_invoked": False,
                    "torchaudio_imported": False,
                    "chatterbox_imported": False,
                    "model_loaded": False,
                    "audio_generated": False,
                    "playback_performed": False,
                    "ollama_invoked": False,
                }
            }
        )
        self.assertTrue(result["prohibited_outcomes_evidence_complete"])
        self.assertTrue(result["prohibited_outcomes_absent"])

    def test_v2_observed_prohibited_outcome_fails_closed(self) -> None:
        result = v2.classify_prohibited_outcomes(
            {"load_import_only": {"cuda_api_invoked": True}}
        )
        self.assertTrue(result["prohibited_outcomes_observed"])
        self.assertFalse(result["prohibited_outcomes_absent"])

    def test_v2_static_self_check_is_inert(self) -> None:
        result = v2.static_self_check()
        self.assertTrue(result["passed"], result)
        self.assertFalse(result["blackwell_runtime_started"])
        self.assertFalse(result["torch_imported"])
        self.assertFalse(result["cuda_api_invoked"])
        self.assertFalse(result["model_loaded"])
        self.assertFalse(result["audio_generated"])
        self.assertFalse(result["playback_performed"])
        self.assertFalse(result["ollama_invoked"])
        self.assertFalse(result["defender_queried"])
        self.assertFalse(result["defender_changed"])
        self.assertFalse(result["candidate_promoted"])
        self.assertFalse(result["production_routing_changed"])


if __name__ == "__main__":
    unittest.main()
