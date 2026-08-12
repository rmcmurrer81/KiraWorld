"""Host-only routing tests for the persistent Blackwell v2 voice candidate.

These tests use mocks exclusively.  They never start a model, GPU worker,
audio device, Ollama, or Blender process and never write a WAV.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

import voice_output  # noqa: E402


class PersistentBlackwellV2DispatchTests(unittest.TestCase):
    def _config(self) -> voice_output.VoiceOutputConfig:
        return voice_output.VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio=voice_output.KIRA_APPROVED_REFERENCE_RELATIVE,
            play_audio=False,
        )

    def _routing(self) -> dict:
        return {
            "valid": True,
            "routing_id": "host-only-unit-routing",
            "routing_config_sha256": "a" * 64,
            "routes": [
                {
                    "route_id": "blackwell_gpu",
                    "role": "preferred",
                    "valid": True,
                },
                {
                    "route_id": "sealed_cpu",
                    "role": "automatic_fallback_only",
                    "valid": True,
                },
            ],
        }

    def _target(self) -> Path:
        # The synthesis calls are mocked; this path is never created.
        return PROJECT_ROOT / "RecoverySprint" / "verification_scratch" / "mock.wav"

    @staticmethod
    def _ready_self_check(_route: dict) -> dict:
        return {"ready": True, "reason": "host_only_mock_ready"}

    @staticmethod
    def _qwen_absent() -> dict:
        return {"query_succeeded": True, "qwen_absent_proven": True}

    def test_safe_benchmark_projects_v2_actual_gpu_execution_truth(self) -> None:
        result = {
            "route_id": "blackwell_gpu_persistent_candidate_v2",
            "approved_voice_path_used": "blackwell_gpu",
            "device": "cuda",
            "gpu_proof": {
                "actual_gpu_execution": True,
                "qwen_absence_proven_for_accepted_generation": True,
                "peak_allocated_bytes": 3_657_100_288,
            },
            "gpu_synthesis_attempted": True,
            "cpu_synthesis_attempted": False,
            "automatic_cpu_fallback_used": False,
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "test_only_injected_client": False,
            "production_route_promoted": False,
            "production_routing_authorized": False,
        }
        evidence = voice_output._safe_approved_voice_route_evidence(result)
        self.assertTrue(evidence["gpu_actual_execution"])
        self.assertNotIn("gpu_actual_allocation", evidence)
        self.assertFalse(evidence["generic_voice_used"])
        self.assertFalse(evidence["sapi_voice_used"])
        self.assertFalse(evidence["fallback_used"])
        self.assertFalse(evidence["test_only_injected_client"])
        self.assertTrue(evidence["qwen_absence_proven_for_accepted_generation"])
        self.assertFalse(evidence["production_route_promoted"])
        self.assertFalse(evidence["production_routing_authorized"])
        self.assertEqual(evidence["peak_allocated_bytes"], 3_657_100_288)

    def test_safe_benchmark_keeps_allocation_and_execution_as_distinct_truths(self) -> None:
        explicit_legacy = voice_output._safe_approved_voice_route_evidence(
            {
                "gpu_proof": {
                    "actual_gpu_allocation": False,
                    "actual_gpu_execution": True,
                }
            }
        )
        self.assertFalse(explicit_legacy["gpu_actual_allocation"])
        self.assertTrue(explicit_legacy["gpu_actual_execution"])

        explicit_v2_false = voice_output._safe_approved_voice_route_evidence(
            {"gpu_proof": {"actual_gpu_execution": False}}
        )
        self.assertFalse(explicit_v2_false["gpu_actual_execution"])
        self.assertNotIn("gpu_actual_allocation", explicit_v2_false)

        absent = voice_output._safe_approved_voice_route_evidence({})
        self.assertNotIn("gpu_actual_allocation", absent)
        self.assertNotIn("gpu_actual_execution", absent)
        self.assertNotIn("generic_voice_used", absent)
        self.assertNotIn("sapi_voice_used", absent)
        self.assertNotIn("fallback_used", absent)
        self.assertNotIn("test_only_injected_client", absent)
        self.assertNotIn("qwen_absence_proven_for_accepted_generation", absent)
        self.assertNotIn("production_route_promoted", absent)
        self.assertNotIn("production_routing_authorized", absent)

    def test_both_flags_off_preserves_one_shot_gpu_route_without_v2_call(self) -> None:
        def one_shot(_text, _target, _cfg, route):
            self.assertEqual(route["route_id"], "blackwell_gpu")
            return {
                "generated": True,
                "reason": "ok",
                "engine": "chatterbox_tts",
                "device": "cuda",
                "playback": False,
                "generic_voice_used": False,
            }

        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=False,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=False,
            ),
            patch.object(
                voice_output, "_synthesize_with_persistent_blackwell_voice_v1"
            ) as persistent_v1,
            patch.object(
                voice_output, "_synthesize_with_persistent_blackwell_voice_v2"
            ) as persistent_v2,
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value=self._routing(),
            ),
            patch.object(
                voice_output,
                "_qwen_residency_evidence",
                side_effect=lambda: self._qwen_absent(),
            ),
            patch.object(
                voice_output,
                "_run_approved_sidecar_self_check",
                side_effect=self._ready_self_check,
            ),
            patch.object(
                voice_output,
                "_synthesize_with_approved_sidecar",
                side_effect=one_shot,
            ) as one_shot_call,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Exact public text.", self._target(), self._config()
            )

        self.assertTrue(result["generated"], result)
        self.assertEqual(result["approved_voice_path_used"], "blackwell_gpu")
        self.assertTrue(result["approved_voice_routing"]["one_shot_gpu_rollback_invoked"])
        self.assertFalse(result["automatic_cpu_fallback_used"])
        self.assertFalse(result["generic_voice_used"])
        self.assertFalse(result["playback"])
        persistent_v1.assert_not_called()
        persistent_v2.assert_not_called()
        one_shot_call.assert_called_once()

    def test_v2_flag_wins_over_v1_and_success_is_connected_not_promoted(self) -> None:
        v2_result = {
            "generated": True,
            "reason": "ok",
            "persistent_route_eligible": True,
            "selected_candidate_version": "v2",
            "test_only_injected_client": False,
            "route_id": "blackwell_gpu_persistent_candidate_v2_inactive",
            "approved_voice_path_used": "blackwell_gpu",
            "engine": "chatterbox_tts",
            "device": "cuda",
            "playback": False,
            "generic_voice_used": False,
        }
        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=True,
            ),
            patch.object(
                voice_output, "_synthesize_with_persistent_blackwell_voice_v1"
            ) as persistent_v1,
            patch.object(
                voice_output,
                "_synthesize_with_persistent_blackwell_voice_v2",
                return_value=v2_result,
            ) as persistent_v2,
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value=self._routing(),
            ),
            patch.object(voice_output, "_synthesize_with_approved_sidecar") as one_shot,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Exact public text.", self._target(), self._config()
            )

        self.assertTrue(result["generated"], result)
        self.assertEqual(result["route_id"], "blackwell_gpu_persistent_candidate_v2")
        self.assertEqual(result["approved_voice_path_used"], "blackwell_gpu")
        self.assertEqual(
            result["approved_voice_routing"]["preferred_path"],
            "blackwell_gpu_persistent_candidate_v2",
        )
        self.assertTrue(result["application_route_connected"])
        self.assertFalse(result["production_route_promoted"])
        self.assertTrue(result["gpu_synthesis_attempted"])
        self.assertFalse(result["cpu_synthesis_attempted"])
        self.assertFalse(result["automatic_cpu_fallback_used"])
        self.assertFalse(result["generic_voice_used"])
        self.assertFalse(result["playback"])
        persistent_v2.assert_called_once()
        persistent_v1.assert_not_called()
        one_shot.assert_not_called()

    def test_v2_injected_generated_result_is_never_relabelled_or_fallback_routed(self) -> None:
        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=False,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_synthesize_with_persistent_blackwell_voice_v2",
                return_value={
                    "generated": True,
                    "reason": "ok",
                    "selected_candidate_version": "v2",
                    "persistent_route_eligible": False,
                    "test_only_injected_client": True,
                    "route_id": "blackwell_gpu_persistent_candidate_v2_test_only",
                    "approved_voice_path_used": None,
                    "playback": False,
                    "generic_voice_used": False,
                },
            ),
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value=self._routing(),
            ),
            patch.object(voice_output, "_qwen_residency_evidence") as qwen,
            patch.object(voice_output, "_run_approved_sidecar_self_check") as self_check,
            patch.object(voice_output, "_synthesize_with_approved_sidecar") as fallback,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Never relabel injected output.", self._target(), self._config()
            )

        self.assertFalse(result["generated"], result)
        self.assertEqual(
            result["reason"],
            "persistent_blackwell_unapproved_generated_result_blocked",
        )
        self.assertIsNone(result["approved_voice_path_used"])
        self.assertTrue(result["route_blocked"])
        self.assertFalse(result["fallback_allowed"])
        qwen.assert_not_called()
        self_check.assert_not_called()
        fallback.assert_not_called()

    def test_status_top_level_is_bound_only_to_selected_v2_candidate(self) -> None:
        v1_status = {
            "feature_enabled": False,
            "session_owner": "stale-v1-owner",
            "owned_worker_running": True,
            "model_loaded": True,
        }
        v2_status = {
            "feature_enabled": True,
            "session_owner": "",
            "owned_worker_running": False,
            "model_loaded": False,
        }
        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=False,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_status_v1",
                return_value=v1_status,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_status_v2",
                return_value=v2_status,
            ),
        ):
            status = voice_output.persistent_blackwell_voice_status()

        self.assertEqual(status["selected_candidate_version"], "v2")
        self.assertEqual(status["session_owner"], "")
        self.assertFalse(status["owned_worker_running"])
        self.assertFalse(status["model_loaded"])
        self.assertEqual(status["any_owned_session_owner"], "stale-v1-owner")
        self.assertTrue(status["any_owned_worker_running"])
        self.assertTrue(status["any_model_loaded"])

    def test_invalid_routing_releases_exact_persistent_worker_before_return(self) -> None:
        cleanup = {
            "released": True,
            "owned_worker_closed": True,
            "playback": False,
            "generated_audio": False,
        }
        with (
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value={"valid": False, "reason": "hash_mismatch", "issues": ["x"]},
            ),
            patch.object(
                voice_output,
                "release_persistent_blackwell_voice",
                return_value=cleanup,
            ) as release,
            patch.object(
                voice_output, "synthesize_with_persistent_blackwell_voice"
            ) as synthesize,
            patch.object(voice_output, "_synthesize_with_approved_sidecar") as fallback,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Routing changed.", self._target(), self._config()
            )

        self.assertFalse(result["generated"], result)
        self.assertEqual(result["reason"], "hash_mismatch")
        self.assertTrue(result["persistent_cleanup_proven"])
        release.assert_called_once_with("approved_voice_routing_invalid")
        synthesize.assert_not_called()
        fallback.assert_not_called()

    def test_v2_owned_cleanup_failure_skips_one_shot_gpu_and_uses_only_sealed_cpu(self) -> None:
        called_routes: list[str] = []

        def sealed_cpu_only(_text, _target, _cfg, route):
            called_routes.append(route["route_id"])
            self.assertEqual(route["route_id"], "sealed_cpu")
            return {
                "generated": True,
                "reason": "ok",
                "engine": "chatterbox_tts",
                "device": "cpu",
                "playback": False,
                "generic_voice_used": False,
            }

        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_synthesize_with_persistent_blackwell_voice_v2",
                return_value={
                    "generated": False,
                    "reason": "bounded_v2_failure",
                    "persistent_route_eligible": True,
                    "candidate_attempted": True,
                    "fallback_allowed": True,
                    "route_blocked": False,
                    "target_cleanup_proven": True,
                    "owned_worker_cleanup": {"owned_worker_closed": True},
                    "playback": False,
                },
            ),
            patch.object(
                voice_output, "_synthesize_with_persistent_blackwell_voice_v1"
            ) as persistent_v1,
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value=self._routing(),
            ),
            patch.object(
                voice_output,
                "_qwen_residency_evidence",
                side_effect=lambda: self._qwen_absent(),
            ),
            patch.object(
                voice_output,
                "_run_approved_sidecar_self_check",
                side_effect=self._ready_self_check,
            ),
            patch.object(
                voice_output,
                "_synthesize_with_approved_sidecar",
                side_effect=sealed_cpu_only,
            ),
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Exact public text.", self._target(), self._config()
            )

        self.assertTrue(result["generated"], result)
        self.assertEqual(called_routes, ["sealed_cpu"])
        self.assertEqual(result["approved_voice_path_used"], "sealed_cpu")
        self.assertTrue(result["gpu_synthesis_attempted"])
        self.assertTrue(result["cpu_synthesis_attempted"])
        self.assertTrue(result["automatic_cpu_fallback_used"])
        self.assertFalse(result["generic_voice_used"])
        self.assertFalse(result["playback"])
        self.assertFalse(
            result["approved_voice_routing"]["one_shot_gpu_rollback_invoked"]
        )
        statuses = {
            item["route_id"]: item["status"]
            for item in result["approved_voice_attempts"]
        }
        self.assertEqual(
            statuses,
            {
                "blackwell_gpu_persistent_candidate_v2": "synthesis_failed",
                "blackwell_gpu": "rollback_route_not_automatic",
                "sealed_cpu": "used",
            },
        )
        persistent_v1.assert_not_called()

    def test_v2_missing_cleanup_proof_blocks_every_fallback(self) -> None:
        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_synthesize_with_persistent_blackwell_voice_v2",
                return_value={
                    "generated": False,
                    "reason": "v2_cleanup_unproven",
                    "persistent_route_eligible": True,
                    "candidate_attempted": True,
                    "fallback_allowed": True,
                    "route_blocked": False,
                    "target_cleanup_proven": True,
                    # Deliberately absent: no cleanup evidence is not proof.
                    "playback": False,
                },
            ),
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value=self._routing(),
            ),
            patch.object(
                voice_output,
                "_qwen_residency_evidence",
                side_effect=lambda: self._qwen_absent(),
            ) as qwen,
            patch.object(voice_output, "_run_approved_sidecar_self_check") as self_check,
            patch.object(voice_output, "_synthesize_with_approved_sidecar") as one_shot,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Exact public text.", self._target(), self._config()
            )

        self.assertFalse(result["generated"], result)
        self.assertEqual(
            result["reason"],
            "persistent_blackwell_owned_worker_cleanup_not_proven",
        )
        self.assertTrue(result["gpu_synthesis_attempted"])
        self.assertFalse(result["cpu_synthesis_attempted"])
        self.assertFalse(result["automatic_cpu_fallback_used"])
        self.assertFalse(result["generic_voice_used"])
        self.assertFalse(result["playback"])
        qwen.assert_not_called()
        self_check.assert_not_called()
        one_shot.assert_not_called()

    def test_v2_no_owned_session_without_explicit_cleanup_blocks_all_routes(self) -> None:
        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=False,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_synthesize_with_persistent_blackwell_voice_v2",
                return_value={
                    "generated": False,
                    "reason": "persistent_blackwell_v2_no_owned_voice_session",
                    "persistent_route_eligible": False,
                    "candidate_attempted": False,
                    "fallback_allowed": True,
                    "route_blocked": False,
                    "cancelled": False,
                    "target_cleanup_proven": True,
                    "owned_worker_cleanup": None,
                    "playback": False,
                },
            ),
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value=self._routing(),
            ),
            patch.object(
                voice_output,
                "_qwen_residency_evidence",
            ) as qwen,
            patch.object(voice_output, "_run_approved_sidecar_self_check") as self_check,
            patch.object(voice_output, "_synthesize_with_approved_sidecar") as synthesize,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Do not infer cleanup from no owned session.",
                self._target(),
                self._config(),
            )

        self.assertFalse(result["generated"], result)
        self.assertEqual(
            result["reason"],
            "persistent_blackwell_v2_fallback_contract_not_proven",
        )
        self.assertTrue(result["route_blocked"])
        self.assertFalse(result["fallback_allowed"])
        self.assertFalse(result["gpu_synthesis_attempted"])
        self.assertFalse(result["cpu_synthesis_attempted"])
        self.assertFalse(result["automatic_cpu_fallback_used"])
        qwen.assert_not_called()
        self_check.assert_not_called()
        synthesize.assert_not_called()

    def test_v2_empty_pre_attempt_result_blocks_all_routes(self) -> None:
        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=False,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_synthesize_with_persistent_blackwell_voice_v2",
                return_value={},
            ),
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value=self._routing(),
            ),
            patch.object(voice_output, "_qwen_residency_evidence") as qwen,
            patch.object(voice_output, "_run_approved_sidecar_self_check") as self_check,
            patch.object(voice_output, "_synthesize_with_approved_sidecar") as synthesize,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "An empty integration result proves no cleanup.",
                self._target(),
                self._config(),
            )

        self.assertFalse(result["generated"], result)
        self.assertEqual(
            result["reason"],
            "persistent_blackwell_v2_fallback_contract_not_proven",
        )
        self.assertTrue(result["route_blocked"])
        self.assertFalse(result["fallback_allowed"])
        self.assertFalse(result["gpu_synthesis_attempted"])
        self.assertFalse(result["cpu_synthesis_attempted"])
        qwen.assert_not_called()
        self_check.assert_not_called()
        synthesize.assert_not_called()

    def test_v2_binding_pre_attempt_with_explicit_cleanup_uses_only_sealed_cpu(self) -> None:
        checked_routes: list[str] = []
        synthesized_routes: list[str] = []

        def checked(route: dict) -> dict:
            checked_routes.append(str(route["route_id"]))
            return self._ready_self_check(route)

        def synthesize(_text, _target, _cfg, route):
            synthesized_routes.append(str(route["route_id"]))
            self.assertEqual(route["route_id"], "sealed_cpu")
            return {
                "generated": True,
                "reason": "ok",
                "engine": "chatterbox_tts",
                "device": "cpu",
                "playback": False,
                "generic_voice_used": False,
            }

        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=False,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_synthesize_with_persistent_blackwell_voice_v2",
                return_value={
                    "generated": False,
                    "reason": "persistent_blackwell_v2_binding_failed",
                    "persistent_route_eligible": False,
                    "candidate_attempted": False,
                    "fallback_allowed": True,
                    "route_blocked": False,
                    "cancelled": False,
                    "target_cleanup_proven": True,
                    "owned_worker_cleanup": {
                        "owned_worker_was_present": True,
                        "owned_worker_closed": True,
                    },
                    "playback": False,
                },
            ),
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value=self._routing(),
            ),
            patch.object(
                voice_output,
                "_qwen_residency_evidence",
                side_effect=lambda: self._qwen_absent(),
            ),
            patch.object(
                voice_output,
                "_run_approved_sidecar_self_check",
                side_effect=checked,
            ),
            patch.object(
                voice_output,
                "_synthesize_with_approved_sidecar",
                side_effect=synthesize,
            ),
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Binding failed before GPU synthesis.", self._target(), self._config()
            )

        self.assertTrue(result["generated"], result)
        self.assertEqual(checked_routes, ["sealed_cpu"])
        self.assertEqual(synthesized_routes, ["sealed_cpu"])
        self.assertEqual(result["approved_voice_path_used"], "sealed_cpu")
        self.assertFalse(result["gpu_synthesis_attempted"])
        self.assertFalse(
            result["approved_voice_routing"]["one_shot_gpu_rollback_invoked"]
        )

    def test_v2_binding_pre_attempt_without_cleanup_evidence_blocks_all_routes(self) -> None:
        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=False,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_synthesize_with_persistent_blackwell_voice_v2",
                return_value={
                    "generated": False,
                    "reason": "persistent_blackwell_v2_binding_failed",
                    "persistent_route_eligible": False,
                    "candidate_attempted": False,
                    "fallback_allowed": True,
                    "route_blocked": False,
                    "cancelled": False,
                    "target_cleanup_proven": True,
                    "playback": False,
                },
            ),
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value=self._routing(),
            ),
            patch.object(voice_output, "_qwen_residency_evidence") as qwen,
            patch.object(voice_output, "_run_approved_sidecar_self_check") as self_check,
            patch.object(voice_output, "_synthesize_with_approved_sidecar") as synthesize,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Binding failure has no explicit worker closure proof.",
                self._target(),
                self._config(),
            )

        self.assertFalse(result["generated"], result)
        self.assertEqual(
            result["reason"],
            "persistent_blackwell_v2_fallback_contract_not_proven",
        )
        self.assertTrue(result["route_blocked"])
        self.assertFalse(result["fallback_allowed"])
        self.assertFalse(result["gpu_synthesis_attempted"])
        self.assertFalse(result["cpu_synthesis_attempted"])
        qwen.assert_not_called()
        self_check.assert_not_called()
        synthesize.assert_not_called()

    def test_v2_pre_attempt_cleanup_debt_blocks_all_fallback_routes(self) -> None:
        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=False,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_synthesize_with_persistent_blackwell_voice_v2",
                return_value={
                    "generated": False,
                    "reason": "persistent_blackwell_v2_binding_failed",
                    "persistent_route_eligible": False,
                    "candidate_attempted": False,
                    "fallback_allowed": True,
                    "route_blocked": False,
                    "cancelled": False,
                    "target_cleanup_proven": True,
                    "owned_worker_cleanup": {
                        "owned_worker_was_present": True,
                        "owned_worker_closed": False,
                    },
                    "playback": False,
                },
            ),
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value=self._routing(),
            ),
            patch.object(voice_output, "_qwen_residency_evidence") as qwen,
            patch.object(voice_output, "_run_approved_sidecar_self_check") as self_check,
            patch.object(voice_output, "_synthesize_with_approved_sidecar") as synthesize,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Do not fall through with cleanup debt.",
                self._target(),
                self._config(),
            )

        self.assertFalse(result["generated"], result)
        self.assertEqual(
            result["reason"],
            "persistent_blackwell_v2_fallback_contract_not_proven",
        )
        self.assertTrue(result["route_blocked"])
        self.assertFalse(result["fallback_allowed"])
        self.assertFalse(result["gpu_synthesis_attempted"])
        self.assertFalse(result["cpu_synthesis_attempted"])
        qwen.assert_not_called()
        self_check.assert_not_called()
        synthesize.assert_not_called()

    def test_v2_cancelled_old_reply_never_falls_through_to_any_other_route(self) -> None:
        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=False,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_synthesize_with_persistent_blackwell_voice_v2",
                return_value={
                    "generated": False,
                    "reason": "persistent_blackwell_v2_synthesis_cancelled",
                    "candidate_attempted": True,
                    "fallback_allowed": False,
                    "route_blocked": True,
                    "cancelled": True,
                    "target_cleanup_proven": True,
                    "owned_worker_cleanup": {"owned_worker_closed": True},
                    "playback": False,
                },
            ),
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value=self._routing(),
            ),
            patch.object(voice_output, "_qwen_residency_evidence") as qwen,
            patch.object(voice_output, "_run_approved_sidecar_self_check") as self_check,
            patch.object(voice_output, "_synthesize_with_approved_sidecar") as one_shot,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Cancelled old public text.", self._target(), self._config()
            )

        self.assertFalse(result["generated"], result)
        self.assertTrue(result["cancelled"])
        self.assertFalse(result["automatic_cpu_fallback_used"])
        self.assertEqual(result["approved_voice_attempts"][0]["status"], "cancelled")
        qwen.assert_not_called()
        self_check.assert_not_called()
        one_shot.assert_not_called()

    def test_v2_unproven_target_cleanup_blocks_one_shot_and_cpu_fallback(self) -> None:
        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=False,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_synthesize_with_persistent_blackwell_voice_v2",
                return_value={
                    "generated": False,
                    "reason": "linked_target_cleanup_not_proven",
                    "candidate_attempted": True,
                    "fallback_allowed": False,
                    "route_blocked": True,
                    "cancelled": False,
                    "target_cleanup_proven": False,
                    "owned_worker_cleanup": {"owned_worker_closed": True},
                    "playback": False,
                },
            ),
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value=self._routing(),
            ),
            patch.object(voice_output, "_qwen_residency_evidence") as qwen,
            patch.object(voice_output, "_run_approved_sidecar_self_check") as self_check,
            patch.object(voice_output, "_synthesize_with_approved_sidecar") as one_shot,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Do not regenerate this text.", self._target(), self._config()
            )

        self.assertFalse(result["generated"], result)
        self.assertFalse(result["target_cleanup_proven"])
        self.assertFalse(result["automatic_cpu_fallback_used"])
        qwen.assert_not_called()
        self_check.assert_not_called()
        one_shot.assert_not_called()

    def test_flags_off_releases_stale_exact_v2_worker_before_one_shot_route(self) -> None:
        stale_status = {
            "session_owner": "stale-v2-owner",
            "owned_worker_running": True,
            "model_loaded": True,
        }

        def one_shot(_text, _target, _cfg, route):
            self.assertEqual(route["route_id"], "blackwell_gpu")
            return {
                "generated": True,
                "reason": "ok",
                "engine": "chatterbox_tts",
                "device": "cuda",
                "playback": False,
                "generic_voice_used": False,
            }

        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=False,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=False,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_status_v1",
                return_value={},
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_status_v2",
                return_value=stale_status,
            ),
            patch.object(
                voice_output,
                "_release_persistent_blackwell_voice_v2",
                return_value={"released": True, "cleanup": {"owned_worker_closed": True}},
            ) as release_v2,
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value=self._routing(),
            ),
            patch.object(
                voice_output,
                "_qwen_residency_evidence",
                side_effect=lambda: self._qwen_absent(),
            ),
            patch.object(
                voice_output,
                "_run_approved_sidecar_self_check",
                side_effect=self._ready_self_check,
            ),
            patch.object(
                voice_output,
                "_synthesize_with_approved_sidecar",
                side_effect=one_shot,
            ),
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Exact public text.", self._target(), self._config()
            )

        self.assertTrue(result["generated"], result)
        release_v2.assert_called_once_with("persistent_candidate_selection_changed")

    def test_unselected_worker_cleanup_unproven_blocks_loading_every_other_route(self) -> None:
        stale_status = {
            "session_owner": "stale-v2-owner",
            "owned_worker_running": True,
            "model_loaded": True,
        }
        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=False,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=False,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_status_v1",
                return_value={},
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_status_v2",
                return_value=stale_status,
            ),
            patch.object(
                voice_output,
                "_release_persistent_blackwell_voice_v2",
                return_value={
                    "released": False,
                    "cleanup": {"owned_worker_closed": False},
                },
            ),
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value=self._routing(),
            ),
            patch.object(voice_output, "_qwen_residency_evidence") as qwen,
            patch.object(voice_output, "_run_approved_sidecar_self_check") as self_check,
            patch.object(voice_output, "_synthesize_with_approved_sidecar") as one_shot,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Do not load another route.", self._target(), self._config()
            )

        self.assertFalse(result["generated"], result)
        self.assertEqual(
            result["reason"], "unselected_persistent_worker_cleanup_not_proven"
        )
        qwen.assert_not_called()
        self_check.assert_not_called()
        one_shot.assert_not_called()

    def test_combined_release_closes_exact_owned_v1_and_v2_integrations(self) -> None:
        v1_status = {
            "session_owner": "unit-owner-v1",
            "owned_worker_running": True,
            "model_loaded": True,
            "feature_enabled": True,
        }
        v2_status = {
            "session_owner": "unit-owner-v2",
            "owned_worker_running": True,
            "model_loaded": True,
            "feature_enabled": True,
        }
        with (
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v1",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_feature_enabled_v2",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_status_v1",
                return_value=v1_status,
            ),
            patch.object(
                voice_output,
                "_persistent_blackwell_voice_status_v2",
                return_value=v2_status,
            ),
            patch.object(
                voice_output,
                "_release_persistent_blackwell_voice_v1",
                return_value={
                    "released": True,
                    "cleanup": {
                        "owned_worker_closed": True,
                        "model_was_loaded": True,
                    },
                },
            ) as release_v1,
            patch.object(
                voice_output,
                "_release_persistent_blackwell_voice_v2",
                return_value={
                    "released": True,
                    "cleanup": {
                        "owned_worker_closed": True,
                        "model_was_loaded": True,
                    },
                },
            ) as release_v2,
            # Avoid even importing Torch in this host-only release test.
            patch.object(voice_output, "_cancel_chatterbox_idle_timer_locked"),
            patch.object(voice_output, "_release_chatterbox_model_locked"),
            patch.object(voice_output, "_CHATTERBOX_MODEL", None),
            patch.object(voice_output, "_CHATTERBOX_DEVICE", None),
        ):
            result = voice_output.release_voice_output("host_only_combined_release")

        self.assertTrue(result["released"], result)
        self.assertEqual(result["reason"], "persistent_model_released")
        self.assertFalse(result["playback"])
        self.assertFalse(result["generated_audio"])
        release_v1.assert_called_once_with("host_only_combined_release")
        release_v2.assert_called_once_with("host_only_combined_release")
        combined = result["persistent_release"]
        self.assertTrue(combined["owned_worker_closed"])
        self.assertTrue(combined["v1_release"]["cleanup"]["owned_worker_closed"])
        self.assertTrue(combined["v2_release"]["cleanup"]["owned_worker_closed"])

    def test_release_voice_output_detects_stale_unselected_worker_via_aggregate_state(self) -> None:
        with (
            patch.object(
                voice_output,
                "persistent_blackwell_voice_status",
                return_value={
                    "session_owner": "",
                    "owned_worker_running": False,
                    "model_loaded": False,
                    "any_owned_session_owner": "stale-v1-owner",
                    "any_owned_worker_running": True,
                    "any_model_loaded": True,
                    "candidate_versions": {
                        "v1": {"owned_state_present": True},
                        "v2": {"owned_state_present": False},
                    },
                },
            ),
            patch.object(
                voice_output,
                "release_persistent_blackwell_voice",
                return_value={
                    "released": True,
                    "owned_worker_closed": True,
                    "model_was_loaded": True,
                },
            ) as persistent_release,
            patch.object(voice_output, "_cancel_chatterbox_idle_timer_locked"),
            patch.object(voice_output, "_release_chatterbox_model_locked"),
            patch.object(voice_output, "_CHATTERBOX_MODEL", None),
            patch.object(voice_output, "_CHATTERBOX_DEVICE", None),
        ):
            result = voice_output.release_voice_output("aggregate_release_test")

        self.assertTrue(result["released"], result)
        self.assertTrue(result["persistent_cleanup_proven"])
        self.assertEqual(result["reason"], "persistent_model_released")
        persistent_release.assert_called_once_with("aggregate_release_test")

    def test_release_voice_output_never_claims_release_when_worker_cleanup_unproven(self) -> None:
        with (
            patch.object(
                voice_output,
                "persistent_blackwell_voice_status",
                return_value={
                    "any_owned_session_owner": "kira:broken",
                    "any_owned_worker_running": True,
                    "any_model_loaded": True,
                    "candidate_versions": {
                        "v1": {"owned_state_present": False},
                        "v2": {"owned_state_present": True},
                    },
                },
            ),
            patch.object(
                voice_output,
                "release_persistent_blackwell_voice",
                return_value={
                    "released": True,
                    "owned_worker_closed": False,
                    "model_was_loaded": True,
                },
            ),
            patch.object(voice_output, "_cancel_chatterbox_idle_timer_locked"),
            patch.object(voice_output, "_release_chatterbox_model_locked"),
            patch.object(voice_output, "_CHATTERBOX_MODEL", None),
            patch.object(voice_output, "_CHATTERBOX_DEVICE", None),
        ):
            result = voice_output.release_voice_output("unproven_cleanup_test")

        self.assertFalse(result["released"], result)
        self.assertFalse(result["persistent_cleanup_proven"])
        self.assertEqual(result["reason"], "persistent_worker_cleanup_not_proven")
        self.assertEqual(result["device"], "")


if __name__ == "__main__":
    unittest.main()
