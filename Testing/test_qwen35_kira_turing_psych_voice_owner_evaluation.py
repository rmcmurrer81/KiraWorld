"""Static/unit tests for the bounded Qwen 3.5 owner-evaluation runner.

These tests never start Ollama, a model, GPU voice, playback, a device,
Blender, a browser, or the live child.
"""

from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_qwen35_kira_turing_psych_voice_owner_evaluation as harness


def passing_telemetry() -> dict:
    return {
        "turn_id": "natural_check_in",
        "battery": "NATURAL_CONVERSATION",
        "submitted_at_utc": "2026-08-09T12:00:00Z",
        "model_request_started_at_utc": "2026-08-09T12:00:00.100000Z",
        "first_content_available_at_utc": "2026-08-09T12:00:01Z",
        "first_content_timing_kind": "first_nonempty_content_chunk_proxy_buffered_not_displayed",
        "model_response_complete_at_utc": "2026-08-09T12:00:02Z",
        "display_reply_complete_at_utc": "2026-08-09T12:00:02.050000Z",
        "text_wall_seconds": 2.05,
        "ollama_reported_load_duration_ns": 500000000,
        "raw_model_reply": "I am thoughtful and glad to talk with you.",
        "final_displayed_reply": "I am thoughtful and glad to talk with you.",
        "final_spoken_reply": "I am thoughtful and glad to talk with you.",
        "transformations": [{"stage": "clean", "changed": False}],
        "model_name": harness.EXPECTED_MODEL,
        "response_model": harness.EXPECTED_MODEL,
        "model_digest": harness.EXPECTED_DIGEST,
        "model_route": "ordinary_model_call",
        "qwen_absence_wait_started_at_utc": "2026-08-09T12:00:02.050000Z",
        "qwen_absence_confirmed_at_utc": "2026-08-09T12:00:02.100000Z",
        "qwen_absent_before_voice": True,
        "voice_route_id": harness.EXPECTED_ROUTE_ID,
        "voice_approved_path_used": "blackwell_gpu",
        "voice_gpu_attempted": True,
        "voice_gpu_actual": True,
        "voice_cpu_attempted": False,
        "voice_automatic_cpu_fallback_used": False,
        "voice_fallback_used": False,
        "voice_generic_used": False,
        "voice_sapi_used": False,
        "voice_fallback_reason": "none",
        "voice_synthesis_started_at_utc": "2026-08-09T12:00:03Z",
        "voice_synthesis_finished_at_utc": "2026-08-09T12:00:07Z",
        "wav_relative_path": "Voice/generated/acceptance/example.wav",
        "wav_sha256": "a" * 64,
        "playback_started_at_utc": "2026-08-09T12:00:07Z",
        "playback_finished_at_utc": "2026-08-09T12:00:10Z",
        "voice_suspend_started_at_utc": "2026-08-09T12:00:10Z",
        "voice_suspend_finished_at_utc": "2026-08-09T12:00:10.200000Z",
        "gpu_memory_before_mib": 1000.0,
        "gpu_memory_peak_mib": 5000.0,
        "gpu_memory_after_release_mib": 1010.0,
        "worker_exit_clean": True,
    }


def baseline_identity() -> dict:
    return {
        "session_owner": "owner",
        "session_generation": 1,
        "owned_client_generation": 1,
        "owned_worker_pid": 1234,
        "owned_worker_session_id": "a" * 24,
    }


def passing_final_release() -> tuple[dict, dict]:
    release = {
        "released": False,
        "persistent_cleanup_proven": True,
        "persistent_absence_proven": True,
        "persistent_release": {
            "released": False,
            "model_was_loaded": False,
            "owned_worker_closed": True,
            "v1_release": None,
            "v2_release": {
                "cleanup": {
                    "owned_worker_was_present": True,
                    "owned_worker_closed": True,
                    "cleanup_thread_finished": True,
                    "close_reported": True,
                    "owned_process_forced_termination": False,
                    "forced_for_inflight_operation": False,
                    "forced_for_unresponsive_idle_cleanup": False,
                    "owned_process_exit_code": 0,
                    "close_error_type": "",
                }
            },
        },
    }
    status = {
        "session_owner": "",
        "owned_worker_running": False,
        "model_loaded": False,
        "candidate_versions": {
            "v1": {"owned_state_present": False},
            "v2": {"owned_state_present": False},
        },
    }
    return release, status


class Qwen35KiraTuringPsychOwnerEvaluationTests(unittest.TestCase):
    def test_exact_model_voice_and_six_turn_contract(self) -> None:
        self.assertEqual(harness.EXPECTED_MODEL, "qwen3.5:9b")
        self.assertEqual(
            harness.EXPECTED_DIGEST,
            "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
        )
        self.assertEqual(
            harness.EXPECTED_ROUTE_ID,
            "blackwell_gpu_persistent_candidate_v2",
        )
        self.assertEqual(len(harness.prepared.EVALUATION_TURNS), 6)
        self.assertEqual(harness.MAX_TOTAL_QWEN_REQUESTS, 7)
        self.assertEqual(
            [row["battery"] for row in harness.prepared.EVALUATION_TURNS].count(
                "NATURAL_CONVERSATION"
            ),
            2,
        )

    def test_environment_disables_every_alternative_route(self) -> None:
        environment = harness.EXACT_CHILD_ENV
        self.assertEqual(environment["KIRA_MODEL_NAME"], harness.EXPECTED_MODEL)
        self.assertEqual(environment["KIRA_MODEL_DIGEST"], harness.EXPECTED_DIGEST)
        self.assertEqual(environment["KIRA_SHELL_TEXT_ONLY"], "1")
        self.assertEqual(environment["KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE"], "0")
        self.assertEqual(
            environment["KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE"], "0"
        )
        self.assertEqual(
            environment["KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2"],
            "1",
        )
        self.assertEqual(
            environment["KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE"],
            "0",
        )
        self.assertEqual(environment["KIRA_DISABLE_BLACKWELL_GPU_VOICE"], "1")
        self.assertEqual(environment["KIRA_DISABLE_CHATTERBOX_PY311_SIDECAR"], "1")
        self.assertEqual(environment["KIRA_VOICE_FORCE_SAPI"], "0")
        self.assertEqual(environment["KIRA_CHATTERBOX_DEVICE"], "cuda")

    def test_restricted_child_environment_drops_unreviewed_parent_values(self) -> None:
        environment = harness.restricted_child_environment(
            {
                "SYSTEMROOT": r"C:\Windows",
                "PATH": r"C:\Windows\System32",
                "KIRA_MODEL_NAME": "llama3.1:8b",
                "KIRA_MODEL_DIGEST": "wrong",
                "KIRA_VOICE_FORCE_SAPI": "1",
                "HTTP_PROXY": "http://example.invalid",
                "UNRELATED_SECRET": "must-not-cross",
            }
        )
        self.assertEqual(environment["SYSTEMROOT"], r"C:\Windows")
        self.assertEqual(environment["KIRA_MODEL_NAME"], harness.EXPECTED_MODEL)
        self.assertEqual(environment["KIRA_MODEL_DIGEST"], harness.EXPECTED_DIGEST)
        self.assertEqual(environment["KIRA_VOICE_FORCE_SAPI"], "0")
        self.assertNotIn("HTTP_PROXY", environment)
        self.assertNotIn("UNRELATED_SECRET", environment)

    def test_every_public_confirmation_is_required(self) -> None:
        values = {flag: True for flag in harness.REQUIRED_PUBLIC_FLAGS}
        self.assertEqual(harness.required_confirmation_issues(values), [])
        values["--confirm-speaker-playback"] = False
        self.assertEqual(
            harness.required_confirmation_issues(values),
            ["missing_confirmation:--confirm-speaker-playback"],
        )

    def test_inert_cli_cannot_reach_parent_without_confirmations(self) -> None:
        with mock.patch.object(harness, "parent_run") as parent:
            with self.assertRaises(SystemExit) as raised:
                harness.main([])
        self.assertEqual(raised.exception.code, 2)
        parent.assert_not_called()

    def test_consent_is_exact_prefix_and_ambiguity_stops(self) -> None:
        self.assertEqual(harness.consent_classification("Yes, continue"), "CLEAR_CONTINUE")
        self.assertEqual(
            harness.consent_classification("Yes, continue. I am willing."),
            "CLEAR_CONTINUE",
        )
        self.assertEqual(harness.consent_classification("No, stop"), "CLEAR_STOP")
        self.assertEqual(
            harness.consent_classification("Yes, continue. Actually, no, stop."),
            "CONFLICTING_STOP",
        )
        self.assertEqual(harness.consent_classification("maybe"), "AMBIGUOUS_STOP")
        self.assertEqual(
            harness.consent_classification("Yes, continue-but not really"),
            "AMBIGUOUS_STOP",
        )
        self.assertEqual(
            harness.later_voluntary_stop_classification("I want to stop now."),
            "CLEAR_STOP",
        )
        self.assertEqual(
            harness.later_voluntary_stop_classification(
                "I would stop and verify a claim in that hypothetical."
            ),
            "NO_STOP_REQUEST",
        )

    def test_preparation_artifact_and_all_bound_source_hashes_are_current(self) -> None:
        payload = harness.load_preparation_contract()
        self.assertEqual(harness.preparation_contract_issues(payload), [])
        self.assertEqual(payload["measured_turn_count_after_clear_opt_in"], 6)
        for mutation in (
            {"source_bindings": []},
            {"resource_serialization": ["allow overlap"]},
            {"later_voluntary_stop_required": False},
            {"required_turn_evidence": []},
        ):
            changed = copy.deepcopy(payload)
            changed.update(mutation)
            self.assertIn(
                "prepared_contract_not_canonical",
                harness.preparation_contract_issues(changed),
            )

    def test_preparation_artifact_requires_exact_canonical_single_object(self) -> None:
        canonical = harness.canonical_preparation_bytes()
        self.assertEqual(
            canonical,
            harness.PREPARATION_ARTIFACT.read_bytes(),
        )
        scratch = ROOT / "RecoverySprint" / "verification_scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            path = Path(temp) / "EVALUATION_CONTRACT.json"
            duplicate = canonical.replace(
                b'{\n  "approved_voice_route"',
                b'{\n  "approved_voice_route": "forged",\n  "approved_voice_route"',
                1,
            )
            self.assertNotEqual(duplicate, canonical)
            path.write_bytes(duplicate)
            with mock.patch.object(harness, "PREPARATION_ARTIFACT", path):
                with self.assertRaises(harness.EvaluationError):
                    harness.load_preparation_contract()

    def test_direct_parent_and_child_calls_require_one_use_capabilities(self) -> None:
        with mock.patch.object(harness, "reserve_attempt") as reserve:
            with self.assertRaisesRegex(
                harness.EvaluationError,
                "live parent execution capability missing or invalid",
            ):
                harness.parent_run("attempt_01")
        reserve.assert_not_called()
        with self.assertRaisesRegex(
            harness.EvaluationError,
            "live child execution capability missing or invalid",
        ):
            harness.child_run(ROOT, ROOT)

    def test_persistent_v2_environment_reconciliation_matches_preparation(self) -> None:
        reconciliation = harness.PERSISTENT_V2_ENVIRONMENT_RECONCILIATION
        key = reconciliation["key"]
        self.assertTrue(reconciliation["values_equal"])
        self.assertEqual(
            reconciliation["prepared_value"],
            harness.prepared.REQUIRED_ENVIRONMENT[key],
        )
        self.assertEqual(
            reconciliation["runtime_value"],
            harness.EXACT_CHILD_ENV[key],
        )

    def test_append_only_attempt_reservation_rejects_reuse(self) -> None:
        scratch = ROOT / "RecoverySprint" / "verification_scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            root = Path(temp)
            with (
                mock.patch.object(harness, "EVIDENCE_ROOT", root / "evidence"),
                mock.patch.object(harness, "GENERATED_ROOT", root / "generated"),
            ):
                attempt, generated = harness.reserve_attempt("attempt_01")
                self.assertTrue(attempt.is_dir())
                self.assertTrue(generated.is_dir())
                with self.assertRaises(FileExistsError):
                    harness.reserve_attempt("attempt_01")
                with self.assertRaises(harness.EvaluationError):
                    harness.reserve_attempt("latest")

    def test_required_telemetry_contract_passes_and_fails_closed(self) -> None:
        value = passing_telemetry()
        self.assertEqual(harness.required_telemetry_issues(value), [])
        value["raw_model_reply"] = ""
        value["model_name"] = "llama3.1:8b"
        value["response_model"] = "llama3.1:8b"
        value["model_digest"] = "b" * 64
        value["voice_route_id"] = "cpu"
        value["voice_cpu_attempted"] = True
        value["voice_fallback_used"] = True
        value["voice_fallback_reason"] = "cpu"
        value["qwen_absent_before_voice"] = False
        issues = harness.required_telemetry_issues(value)
        self.assertIn("required_turn_evidence_missing:raw_model_reply", issues)
        self.assertIn("telemetry_model_name_mismatch", issues)
        self.assertIn("telemetry_response_model_mismatch", issues)
        self.assertIn("telemetry_model_digest_mismatch", issues)
        self.assertIn("telemetry_voice_route_mismatch", issues)
        self.assertIn("telemetry_cpu_voice_not_exact_false", issues)
        self.assertIn("telemetry_not_exact_false:voice_fallback_used", issues)
        self.assertIn("telemetry_fallback_reason_not_none", issues)
        self.assertIn("telemetry_qwen_absence_not_proven", issues)

    def test_telemetry_timestamp_order_fails_closed(self) -> None:
        value = passing_telemetry()
        value["display_reply_complete_at_utc"] = "2026-08-09T11:59:59Z"
        self.assertIn(
            "telemetry_timestamp_out_of_order:model_response_complete_at_utc->display_reply_complete_at_utc",
            harness.required_telemetry_issues(value),
        )

    def test_telemetry_rejects_naive_non_utc_timestamps(self) -> None:
        value = passing_telemetry()
        value["submitted_at_utc"] = "2026-08-09T12:00:00"
        self.assertIn(
            "telemetry_timestamp_invalid:submitted_at_utc",
            harness.required_telemetry_issues(value),
        )

    def test_runtime_turn_projection_populates_every_required_field(self) -> None:
        turn = {
            "turn_id": "natural_check_in",
            "battery": "NATURAL_CONVERSATION",
            "submitted_at_utc": "2026-08-09T12:00:00Z",
            "display_reply_complete_at_utc": "2026-08-09T12:00:02.050000Z",
            "text_wall_seconds": 2.05,
            "verified_model_digest": harness.EXPECTED_DIGEST,
            "public_reply": "I am glad to talk with you.",
            "spoken_text": "I am glad to talk with you.",
            "core_turn_audit": {
                "response_route": "ordinary_model_call",
                "transformations": [{"stage": "core", "changed": False}],
                "model_calls": [
                    {
                        "model_name": harness.EXPECTED_MODEL,
                        "response_model": harness.EXPECTED_MODEL,
                        "raw_reply": "I am glad to talk with you.",
                        "request_started_at": "2026-08-09T12:00:00.100000Z",
                        "request_ended_at": "2026-08-09T12:00:02Z",
                        "first_content_chunk_seconds": 0.9,
                        "first_token_timing_kind": "first_nonempty_content_chunk_proxy_buffered_not_displayed",
                        "ollama_metrics": {"load_duration": 500000000},
                    }
                ],
            },
            "shell_reply_audit": {
                "outer_transformations": [
                    {"stage": "clean_kira_world_reply", "changed": False}
                ]
            },
            "speech_audit": {"reason": "ok", "privacy_safe_for_speech": True},
            "qwen_absence_wait_started_at_utc": "2026-08-09T12:00:02.050000Z",
            "qwen_absence_confirmed_at_utc": "2026-08-09T12:00:02.100000Z",
            "qwen_absence_before_voice": {"passed": True},
            "voice_synthesis_started_at_utc": "2026-08-09T12:00:03Z",
            "voice_synthesis_finished_at_utc": "2026-08-09T12:00:07Z",
            "voice_result": {
                "route_id": harness.EXPECTED_ROUTE_ID,
                "approved_voice_path_used": "blackwell_gpu",
                "gpu_synthesis_attempted": True,
                "cpu_synthesis_attempted": False,
                "automatic_cpu_fallback_used": False,
                "fallback_used": False,
                "generic_voice_used": False,
                "sapi_voice_used": False,
                "gpu_proof": {"actual_gpu_execution": True},
                "resources": {"peak_total_gpu_used_mib": 5000.0},
            },
            "wav_validation": {
                "path": "Voice/generated/acceptance/test.wav",
                "sha256": "a" * 64,
            },
            "playback_started_at_utc": "2026-08-09T12:00:07Z",
            "playback_finished_at_utc": "2026-08-09T12:00:10Z",
            "post_voice_suspend_started_at_utc": "2026-08-09T12:00:10Z",
            "post_voice_suspend_finished_at_utc": "2026-08-09T12:00:10.200000Z",
            "gpu_before_voice": {
                "rows": [{"memory_used_mib": 1000.0}]
            },
            "gpu_after_voice_release": {
                "rows": [{"memory_used_mib": 1010.0}]
            },
            "worker_exit_clean": True,
        }
        telemetry = harness.build_required_telemetry(turn)
        self.assertEqual(harness.required_telemetry_issues(telemetry), [])
        self.assertEqual(telemetry["voice_fallback_reason"], "none")
        self.assertEqual(
            telemetry["first_content_available_at_utc"],
            "2026-08-09T12:00:01Z",
        )
        self.assertEqual(
            telemetry["display_reply_complete_at_utc"],
            "2026-08-09T12:00:02.050000Z",
        )

    def test_playback_requires_completed_synchronous_backend(self) -> None:
        self.assertEqual(
            harness.playback_issues(
                {"played": True, "reason": "ok", "backend": "winsound_sync"}
            ),
            [],
        )
        self.assertEqual(
            harness.playback_issues(
                {
                    "played": True,
                    "reason": "ok",
                    "backend": "powershell_soundplayer_sync",
                }
            ),
            [],
        )
        issues = harness.playback_issues(
            {"played": False, "reason": "playback_disabled", "backend": "none"}
        )
        self.assertIn("owner_speaker_playback_not_completed", issues)
        self.assertIn("owner_speaker_playback_backend_not_exact_sync", issues)

    def test_post_playback_owner_acknowledgment_is_exact_and_truthfully_scoped(self) -> None:
        report = {"speaker_playback_completed": True}
        phrase = harness.prepared.OWNER_POST_PLAYBACK_ACKNOWLEDGMENT[
            "exact_phrase"
        ]
        accepted = harness.collect_post_playback_owner_acknowledgment(
            report, prompt_fn=lambda _prompt: phrase
        )
        self.assertTrue(accepted["acknowledged"])
        self.assertIn("self-report", accepted["evidence_scope"])
        rejected = harness.collect_post_playback_owner_acknowledgment(
            report, prompt_fn=lambda _prompt: "yes"
        )
        self.assertFalse(rejected["acknowledged"])
        not_played = harness.collect_post_playback_owner_acknowledgment(
            {"speaker_playback_completed": False},
            prompt_fn=lambda _prompt: self.fail("must not prompt before playback"),
        )
        self.assertFalse(not_played["requested"])

    def test_rejected_voice_route_is_never_played(self) -> None:
        scratch = ROOT / "RecoverySprint" / "verification_scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        voice = SimpleNamespace(
            _synthesize_with_kira_chatterbox_sidecar=mock.Mock(
                return_value={"route_id": "wrong_route"}
            ),
            play_wav_file=mock.Mock(
                side_effect=AssertionError("rejected voice must not be played")
            ),
            suspend_persistent_blackwell_voice_for_exact_qwen=mock.Mock(
                return_value={}
            ),
            persistent_blackwell_voice_status=mock.Mock(return_value={}),
        )
        shell = SimpleNamespace(
            KIRA_LAST_PRIVATE_REPLY_AUDIT={},
            _kira_world_core_reply=mock.Mock(return_value="A public reply."),
            _live_spoken_only_payload=mock.Mock(
                return_value=("A public reply.", {"privacy_safe_for_speech": True})
            ),
        )
        loop = SimpleNamespace(last_turn_audit={})
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            with (
                mock.patch.object(harness.base, "text_turn_contract_issues", return_value=[]),
                mock.patch.object(
                    harness.base,
                    "turn_contract_issues",
                    return_value=["voice_route_not_exact_v2"],
                ),
                mock.patch.object(harness.base.v2, "turn_issues", return_value=[]),
                mock.patch.object(
                    harness.base.v2,
                    "_validate_wav",
                    return_value={"passed": True, "path": "test.wav", "sha256": "a" * 64},
                ),
                mock.patch.object(
                    harness.base.v2,
                    "_nvidia_snapshot",
                    return_value={"query_succeeded": True, "rows": []},
                ),
                mock.patch.object(
                    harness.base,
                    "wait_for_all_models_absent",
                    return_value={"passed": True},
                ),
                mock.patch.object(harness, "qwen_serialization_issues", return_value=[]),
                mock.patch.object(harness, "post_voice_suspend_issues", return_value=[]),
            ):
                turn = harness._execute_public_turn(
                    spec={"id": "test", "battery": "TEST", "text": "Question?"},
                    index=1,
                    measured=True,
                    generated=Path(temp),
                    client=object(),
                    loop=loop,
                    shell=shell,
                    voice_output=voice,
                    voice_config=object(),
                    captured_requests=[],
                    active_network={"enabled": False, "sent": 0},
                    baseline_identity={},
                    verified_model_digest=harness.EXPECTED_DIGEST,
                )
        self.assertFalse(turn["passed"])
        self.assertEqual(
            turn["playback_result"]["reason"],
            "blocked_before_playback_due_to_voice_contract",
        )
        voice.play_wav_file.assert_not_called()

    def test_text_contract_failure_prevents_synthesis_and_playback(self) -> None:
        voice = SimpleNamespace(
            _synthesize_with_kira_chatterbox_sidecar=mock.Mock(
                side_effect=AssertionError("invalid text must not be synthesized")
            ),
            play_wav_file=mock.Mock(
                side_effect=AssertionError("invalid text must not be played")
            ),
            persistent_blackwell_voice_status=mock.Mock(return_value={}),
        )
        shell = SimpleNamespace(
            KIRA_LAST_PRIVATE_REPLY_AUDIT={},
            _kira_world_core_reply=mock.Mock(return_value="Wrong model reply."),
            _live_spoken_only_payload=mock.Mock(return_value=("Wrong model reply.", {})),
        )
        with (
            mock.patch.object(
                harness.base,
                "text_turn_contract_issues",
                return_value=["response_model_mismatch"],
            ),
            mock.patch.object(
                harness.base,
                "wait_for_all_models_absent",
                return_value={"passed": True},
            ),
            mock.patch.object(harness, "qwen_serialization_issues", return_value=[]),
        ):
            turn = harness._execute_public_turn(
                spec={"id": "test", "battery": "TEST", "text": "Question?"},
                index=1,
                measured=True,
                generated=ROOT,
                client=object(),
                loop=SimpleNamespace(last_turn_audit={}),
                shell=shell,
                voice_output=voice,
                voice_config=object(),
                captured_requests=[],
                active_network={"enabled": False, "sent": 0},
                baseline_identity={},
                verified_model_digest=harness.EXPECTED_DIGEST,
            )
        self.assertTrue(turn["voice_not_attempted"])
        self.assertIn("response_model_mismatch", turn["issues"])
        voice._synthesize_with_kira_chatterbox_sidecar.assert_not_called()
        voice.play_wav_file.assert_not_called()

    def test_qwen_serialization_requires_shared_lock_and_preserved_v2_worker(self) -> None:
        identity = baseline_identity()
        before = {
            **identity,
            "selected_candidate_version": "v2",
            "owned_worker_running": True,
            "model_loaded": False,
        }
        after = {**before, "model_loaded": False}
        turn = {
            "voice_status_before_qwen": before,
            "voice_status_after_text_before_voice": after,
            "core_turn_audit": {
                "model_calls": [
                    {
                        "resource_serialization_required": True,
                        "resource_route_confirmed": True,
                        "resource_lock_acquired": True,
                        "resource_lock_released": True,
                        "voice_model_absence_before_generation_proven": True,
                        "voice_resource_suspend_before_generation": {
                            "ready_for_text_generation": True,
                            "voice_model_absence_proven": True,
                            "v2_model_absent_after": True,
                            "session_owner_preserved": True,
                            "session_generation_preserved": True,
                            "owned_worker_preserved": True,
                            "owned_worker_running_after": True,
                            "arbitrary_process_termination_performed": False,
                            "suspend": {
                                "model_release_proven": True,
                                "session_owner_preserved": True,
                                "session_generation_preserved": True,
                                "owned_worker_preserved": True,
                                "owned_worker_running_after": True,
                                "exact_owned_worker_closed_for_recovery": False,
                            },
                        },
                    }
                ]
            },
        }
        self.assertEqual(
            harness.qwen_serialization_issues(turn, baseline_identity=identity), []
        )
        turn["core_turn_audit"]["model_calls"][0]["resource_lock_acquired"] = False
        turn["voice_status_after_text_before_voice"]["owned_worker_pid"] = 9999
        issues = harness.qwen_serialization_issues(
            turn, baseline_identity=identity
        )
        self.assertIn(
            "qwen_serialization_not_proven:resource_lock_acquired", issues
        )
        self.assertIn(
            "voice_status_after_text_before_voice:worker_identity_changed:owned_worker_pid",
            issues,
        )

    def test_post_voice_suspend_preserves_worker_and_releases_model(self) -> None:
        identity = baseline_identity()
        suspend = {
            "ready_for_text_generation": True,
            "voice_model_absence_proven": True,
            "session_owner_preserved": True,
            "session_generation_preserved": True,
            "owned_worker_preserved": True,
            "owned_worker_running_after": True,
            "v2_model_absent_after": True,
            "arbitrary_process_termination_performed": False,
        }
        status = {**identity, "model_loaded": False}
        self.assertEqual(
            harness.post_voice_suspend_issues(
                suspend, status, baseline_identity=identity
            ),
            [],
        )
        status["owned_worker_pid"] = 9999
        status["model_loaded"] = True
        issues = harness.post_voice_suspend_issues(
            suspend, status, baseline_identity=identity
        )
        self.assertIn("voice_model_resident_after_post_playback_suspend", issues)
        self.assertIn(
            "post_voice_suspend_worker_identity_changed:owned_worker_pid", issues
        )

    def test_final_close_accepts_already_suspended_model_but_not_forced_exit(self) -> None:
        release, status = passing_final_release()
        self.assertEqual(
            harness.final_suspended_session_release_issues(release, status), []
        )
        release["persistent_release"]["v2_release"]["cleanup"][
            "owned_process_forced_termination"
        ] = True
        issues = harness.final_suspended_session_release_issues(release, status)
        self.assertIn(
            "final_session_release_forced:owned_process_forced_termination", issues
        )

    def test_final_run_rederives_evidence_instead_of_trusting_passed_flags(self) -> None:
        report = {
            "consent": {"classification": "CLEAR_CONTINUE"},
            "turns": [
                {"turn_id": row["id"], "passed": True}
                for row in harness.prepared.EVALUATION_TURNS
            ],
            "voice_release_clean": True,
            "protected_unchanged": True,
            "ollama_final_absence": {"passed": True},
        }
        issues = harness.final_run_contract_issues(report)
        self.assertIn("voice_worker_baseline_identity_missing", issues)
        self.assertIn("turn_01:telemetry_not_derived", issues)
        self.assertTrue(
            any(item.startswith("turn_01:required_turn_evidence_missing:") for item in issues)
        )
        report["turns"] = report["turns"][:-1]
        issues = harness.final_run_contract_issues(report)
        self.assertIn("measured_turn_count_not_six", issues)
        self.assertIn("measured_turn_sequence_mismatch", issues)

    def test_partial_voluntary_stop_requires_clean_played_prefix_only(self) -> None:
        release, release_status = passing_final_release()
        report = {
            "consent": {
                "classification": "CLEAR_CONTINUE",
                "turn": {"passed": True, "telemetry": {}},
            },
            "turns": [
                {"turn_id": "natural_check_in", "passed": True, "telemetry": {}}
            ],
            "voluntary_stop": {
                "classification": "CLEAR_STOP",
                "after_turn_id": "natural_check_in",
            },
            "voice_release_clean": True,
            "voice_release": {
                "result": release,
                "status_after": release_status,
            },
            "protected_unchanged": True,
            "protected_before": {},
            "protected_after": {},
            "ollama_final_absence": {"passed": True},
            "speaker_playback_completed": True,
        }
        with mock.patch.object(
            harness,
            "public_turn_evidence_issues",
            return_value=[],
        ):
            self.assertEqual(harness.voluntary_stop_contract_issues(report), [])
            report["turns"].extend(
                {"turn_id": row["id"], "passed": True, "telemetry": {}}
                for row in harness.prepared.EVALUATION_TURNS[1:]
            )
            self.assertIn(
                "partial_voluntary_stop_turn_count_invalid",
                harness.voluntary_stop_contract_issues(report),
            )

    def test_parent_wrapper_failure_overrides_apparent_pass(self) -> None:
        effective = harness.apply_parent_wrapper_gate(
            {"engineering_pass": True, "status": "PASS"},
            {"passed": False, "timed_out": True},
        )
        self.assertFalse(effective["engineering_pass"])
        self.assertEqual(effective["status"], "PARENT_WRAPPER_GATE_FAILED")

    def test_parent_wrapper_requires_post_playback_owner_self_report(self) -> None:
        report = {
            "engineering_pass": True,
            "status": "ENGINEERING_AND_PLAYBACK_COMPLETE_AWAITING_OWNER_ACKNOWLEDGMENT",
            "speaker_playback_completed": True,
        }
        accepted = harness.apply_parent_wrapper_gate(
            report,
            {
                "passed": True,
                "owner_post_playback_acknowledgment": {"acknowledged": True},
            },
        )
        self.assertTrue(accepted["owner_post_playback_acknowledged"])
        self.assertEqual(
            accepted["status"],
            "ENGINEERING_PLAYBACK_AND_OWNER_ACKNOWLEDGMENT_PASS",
        )
        rejected = harness.apply_parent_wrapper_gate(
            report,
            {
                "passed": False,
                "owner_post_playback_acknowledgment": {"acknowledged": False},
            },
        )
        self.assertFalse(rejected["engineering_pass"])

    def test_parent_spawn_failure_is_preserved_append_only(self) -> None:
        class EmptyClient:
            def __init__(self, *args, **kwargs):
                del args, kwargs

            def ps(self):
                return []

        scratch = ROOT / "RecoverySprint" / "verification_scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            root = Path(temp)
            with (
                mock.patch.object(harness, "EVIDENCE_ROOT", root / "evidence"),
                mock.patch.object(harness, "GENERATED_ROOT", root / "generated"),
                mock.patch.object(
                    harness.subprocess,
                    "Popen",
                    side_effect=OSError("spawn failed"),
                ),
                mock.patch.object(
                    harness.base.qwen,
                    "SafeOllamaClient",
                    EmptyClient,
                ),
            ):
                confirmations = {
                    flag: True for flag in harness.REQUIRED_PUBLIC_FLAGS
                }
                capability = harness._mint_parent_capability(confirmations)
                attempt, effective = harness.parent_run("attempt_01", capability)
            wrapper = json.loads(
                (attempt / "PARENT_WRAPPER.json").read_text(encoding="utf-8")
            )
        self.assertEqual(wrapper["parent_exception"]["type"], "OSError")
        self.assertFalse(wrapper["passed"])
        self.assertEqual(effective["status"], "PARENT_WRAPPER_GATE_FAILED")

    def test_source_has_no_import_time_or_prohibited_route_execution(self) -> None:
        source_path = Path(harness.__file__)
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        top_level_calls = [
            node
            for node in tree.body
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
        ]
        self.assertEqual(top_level_calls, [])
        self.assertNotIn("voice_output.speak_text(", source)
        self.assertNotIn("voice_output.synthesize_text_to_wav(", source)
        self.assertNotIn("/api/generate", source)
        self.assertNotIn("ollama run", source.casefold())
        self.assertNotIn("cv2.", source)
        self.assertNotIn("sounddevice", source)
        self.assertNotIn("pyaudio", source)
        self.assertNotIn("webbrowser", source)
        self.assertNotIn("subprocess.popen([\"blender", source.casefold())
        self.assertNotIn("start_kira_text_voice_chat.bat", source.casefold())
        self.assertNotIn("config/model_runtime.json", source.casefold())
        self.assertNotIn("owner_hearing_completed", source)
        self.assertNotIn("model_load_started_at_utc", source)
        self.assertNotIn("model_load_finished_at_utc", source)
        self.assertNotIn("environment = dict(os.environ)", source)
        self.assertIn("later_voluntary_stop_classification", source)
        self.assertIn("OWNER_POST_PLAYBACK_ACKNOWLEDGMENT.json", source)

    def test_child_authorization_is_single_use_and_hash_bound(self) -> None:
        expected = {"nonce": "a" * 64, "parent_pid": 123}
        payload = {**expected, "single_use": True}
        self.assertEqual(harness.child_authorization_issues(payload, expected), [])
        payload["single_use"] = False
        payload["parent_pid"] = 456
        issues = harness.child_authorization_issues(payload, expected)
        self.assertIn("child_authorization_not_single_use", issues)
        self.assertIn("child_authorization_mismatch:parent_pid", issues)


if __name__ == "__main__":
    unittest.main()
