from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools import validate_kira_turing_psych_voice_gate_preparation as gate


ROOT = Path(__file__).resolve().parents[1]


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class KiraTuringPsychVoiceGatePreparationTests(unittest.TestCase):
    def test_prepared_gate_is_hash_bound_inert_and_blocked(self) -> None:
        result = gate.validate_prepared_gate()
        self.assertTrue(result["passed"])
        self.assertFalse(result["historical_snapshot_valid"])
        self.assertEqual(result["superseded_source_bindings"], [])
        self.assertEqual(result["status"], "PREPARED_BLOCKED_NOT_EXECUTED")
        self.assertEqual(result["evidence_ceiling"], "CONTRACT_ONLY")
        self.assertEqual(result["measured_turn_count"], 2)
        self.assertFalse(result["live_operation_started"])
        self.assertEqual(set(result["blockers"]), gate.REQUIRED_BLOCKERS)

    def test_validator_has_no_live_process_device_network_or_audio_api(self) -> None:
        source = Path(gate.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(str(node.module or "").split(".")[0])
        self.assertTrue(
            {
                "subprocess",
                "urllib",
                "requests",
                "torch",
                "ollama",
                "cv2",
                "sounddevice",
                "pyaudio",
                "webbrowser",
            }.isdisjoint(imported)
        )
        description = gate.describe()
        self.assertTrue(description["default_inert"])
        self.assertFalse(description["live_operation_started"])

    def test_historical_failed_attempt_cannot_satisfy_new_prerequisite(self) -> None:
        historical = (
            ROOT
            / "RecoverySprint"
            / "continuation_20260802"
            / "persistent_blackwell_voice_candidate_acceptance"
            / "attempt_03"
            / gate.PERSISTENT_REPORT_NAME
        )
        with self.assertRaises(gate.PreparationError):
            gate.validate_persistent_report(historical)

    def test_deep_persistent_report_validator_accepts_only_exact_two_wav_evidence(self) -> None:
        config_hash = "1" * 64
        harness_hash = "2" * 64
        worker_hash = "3" * 64
        profile_hash = "4" * 64
        reference_hash = "5" * 64
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            acceptance_root = project_root / "evidence"
            attempt = acceptance_root / "attempt_04"
            attempt.mkdir(parents=True)
            first_audio = attempt / "kira_persistent_cold_first_request.wav"
            second_audio = attempt / "kira_persistent_warm_second_request.wav"
            first_audio.write_bytes(b"RIFF-fake-one")
            second_audio.write_bytes(b"RIFF-fake-two")

            def synthesis(audio: Path) -> dict:
                return {
                    "generated": True,
                    "engine": "chatterbox_tts",
                    "channel": "public_spoken_only",
                    "text_sha256": gate.sha256_text(gate.APPROVED_PUBLIC_SENTENCE),
                    "profile_sha256": profile_hash,
                    "reference_sha256": reference_hash,
                    "conditioning_reused": True,
                    "generic_voice_used": False,
                    "sapi_voice_used": False,
                    "fallback_used": False,
                    "playback": False,
                    "device": "cuda",
                    "gpu_proof": {
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
                    },
                    "wav_validation": {
                        "passed": True,
                        "sha256": _sha(audio.read_bytes()),
                    },
                    "audio_relative": audio.relative_to(project_root).as_posix(),
                }

            report = {
                "schema_version": 1,
                "artifact_kind": "persistent_blackwell_voice_candidate_acceptance",
                "status": "engineering_pass_pending_owner_heard_acceptance",
                "passed": True,
                "engineering_pass": True,
                "candidate_status": "inactive_private_candidate_not_production",
                "production_routing_authorized": False,
                "promotion_performed": False,
                "playback_performed": False,
                "generic_voice_used": False,
                "sapi_voice_used": False,
                "fallback_used": False,
                "candidate_config_sha256": config_hash,
                "operator_expected_candidate_config_sha256": config_hash,
                "acceptance_harness_sha256": harness_hash,
                "approved_public_sentence": gate.APPROVED_PUBLIC_SENTENCE,
                "approved_public_sentence_sha256": gate.sha256_text(
                    gate.APPROVED_PUBLIC_SENTENCE
                ),
                "protected_files_unchanged": True,
                "protected_before": {"protected": "same"},
                "protected_after": {"protected": "same"},
                "worker_exit_clean": True,
                "cache_deleted_automatically": False,
                "sealed_artifact_hashes": {
                    "candidate_worker": worker_hash,
                    "approved_profile": profile_hash,
                    "approved_reference": reference_hash,
                },
                "qwen_before": {"query_succeeded": True, "qwen_absent_proven": True},
                "qwen_after": {"query_succeeded": True, "qwen_absent_proven": True},
                "ollama_before": {
                    "query_succeeded": True,
                    "all_models_absent_proven": True,
                    "resident_models": [],
                },
                "ollama_after": {
                    "query_succeeded": True,
                    "all_models_absent_proven": True,
                    "resident_models": [],
                },
                "hello": {
                    "config_sha256": config_hash,
                    "worker_sha256": worker_hash,
                    "model_loaded": False,
                    "production_routing_authorized": False,
                },
                "load": {
                    "ready": True,
                    "model_reused": False,
                    "identity": {
                        "profile_sha256": profile_hash,
                        "reference_sha256": reference_hash,
                    },
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
                    "gpu_proof": {
                        "actual_gpu_allocation": True,
                        "persistent_model_allocation_present": True,
                        "model_and_core_components_cuda": True,
                        "cuda_synchronize_before_model_load_succeeded": True,
                        "cuda_synchronize_after_conditioning_succeeded": True,
                        "no_rejected_runtime_warnings": True,
                    },
                },
                "first_synthesis": synthesis(first_audio),
                "second_synthesis": synthesis(second_audio),
                "checks": {key: True for key in gate.REQUIRED_PERSISTENT_CHECKS},
            }
            report_path = attempt / gate.PERSISTENT_REPORT_NAME
            report_path.write_text(json.dumps(report), encoding="utf-8")
            result = gate.validate_persistent_report(
                report_path,
                project_root=project_root,
                acceptance_root=acceptance_root,
                expected_config_sha256=config_hash,
                expected_harness_sha256=harness_hash,
                expected_worker_sha256=worker_hash,
                expected_profile_sha256=profile_hash,
                expected_reference_sha256=reference_hash,
            )
            self.assertTrue(result["passed"])
            self.assertTrue(result["two_wavs_verified"])

            report["second_synthesis"]["text_sha256"] = "0" * 64
            report_path.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaises(gate.PreparationError):
                gate.validate_persistent_report(
                    report_path,
                    project_root=project_root,
                    acceptance_root=acceptance_root,
                    expected_config_sha256=config_hash,
                    expected_harness_sha256=harness_hash,
                    expected_worker_sha256=worker_hash,
                    expected_profile_sha256=profile_hash,
                    expected_reference_sha256=reference_hash,
                )


if __name__ == "__main__":
    unittest.main()
