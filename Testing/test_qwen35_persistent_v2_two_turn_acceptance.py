from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_qwen35_persistent_v2_two_turn_acceptance as harness


WORKER_SESSION_ID = "a" * 24


def worker_status(*, model_loaded: bool) -> dict:
    return {
        "selected_candidate_version": "v2",
        "session_owner": "kira:qwen35-v2-two-turn:attempt_04:test",
        "session_generation": 1,
        "owned_client_generation": 1,
        "owned_worker_running": True,
        "owned_worker_pid": 12345,
        "owned_worker_session_id": WORKER_SESSION_ID,
        "model_loaded": model_loaded,
    }


def passing_turn() -> dict:
    reply = "I feel thoughtful and glad to talk with you."
    return {
        "turn": 1,
        "turn_id": "natural_check_in",
        "question": harness.TURN_SPECS[0]["text"],
        "requests": [
            {
                "model": harness.EXPECTED_MODEL,
                "endpoint": "http://127.0.0.1:11434/api/chat",
                "think": False,
                "keep_alive": 0,
                "stream": True,
                "forbidden_media_key_present": False,
            }
        ],
        "public_reply": reply,
        "spoken_text": reply,
        "speech_audit": {
            "privacy_safe_for_speech": True,
            "reason": "ok",
            "non_name_word_coverage_exact": True,
        },
        "core_turn_audit": {
            "response_route": "ordinary_model_call",
            "model_name": harness.EXPECTED_MODEL,
            "initial_pipeline_reply": reply,
            "final_core_reply": reply,
            "model_calls": [
                {
                    "model_name": harness.EXPECTED_MODEL,
                    "response_model": harness.EXPECTED_MODEL,
                    "backend": "ollama",
                    "outcome": "completed",
                    "requested_keep_alive": 0,
                    "single_generation_per_turn_required": True,
                    "qwen_buffered_stream_timing_candidate_enabled": True,
                    "first_token_available": True,
                    "first_content_chunk_seconds": 0.25,
                    "buffered_until_complete": True,
                    "stream_done_observed": True,
                    "unvalidated_stream_content_displayed": False,
                    "raw_reply": reply,
                }
            ],
            "transformations": [
                {
                    "stage": "suppress_private_emotion_context_leakage",
                    "changed": False,
                    "privacy_boundary_applied_without_model_generation": True,
                },
                {
                    "stage": "suppress_hypothetical_current_person_invention",
                    "changed": False,
                    "privacy_boundary_applied_without_model_generation": True,
                },
                {
                    "stage": "remove_stage_directions",
                    "changed": False,
                    "skipped": True,
                    "reason": "qwen_single_generation_preserves_completed_reply",
                }
            ],
        },
        "shell_reply_audit": {
            "completed": True,
            "qwen_single_generation_per_turn": True,
            "final_shell_reply": reply,
            "outer_model_repair_budget": {
                "maximum_extra_model_calls": 0,
                "extra_model_calls_consumed": 0,
            },
            "outer_transformations": [
                {"stage": "clean_kira_world_reply", "changed": False}
            ],
        },
        "qwen_absence_before_voice": {"passed": True},
        "voice_result": {
            "route_id": harness.v2.EXPECTED_ROUTE_ID,
            "cpu_synthesis_attempted": False,
            "automatic_cpu_fallback_used": False,
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "production_route_promoted": False,
            "playback": False,
            "gpu_proof": {"actual_gpu_execution": True},
        },
        "wav_validation": {"passed": True},
    }


def passing_serialized_turn(expected_turn: int = 1) -> dict:
    value = passing_turn()
    call = value["core_turn_audit"]["model_calls"][0]
    call.update(
        {
            "resource_serialization_required": True,
            "resource_route_confirmed": True,
            "resource_lock_acquired": True,
            "resource_lock_released": True,
            "voice_model_absence_before_generation_proven": True,
            "voice_resource_suspend_before_generation": {
                "voice_model_absence_proven": True,
                "v2_model_absent_after": True,
                "session_owner_preserved": True,
                "session_generation_preserved": True,
                "owned_worker_preserved": True,
                "owned_worker_running_after": True,
                "arbitrary_process_termination_performed": False,
                "suspend": {
                    "model_release_proven": True,
                    "model_was_loaded": True,
                    "session_owner_preserved": True,
                    "session_generation_preserved": True,
                    "owned_worker_preserved": True,
                    "owned_worker_running_after": True,
                    "exact_owned_worker_closed_for_recovery": False,
                },
            },
        }
    )
    value.update(
        {
            "voice_status_before_qwen": worker_status(model_loaded=True),
            "voice_status_after_text_before_voice": worker_status(model_loaded=False),
            "voice_status_after_voice": worker_status(model_loaded=True),
            "voice_external_elapsed_seconds": 7.5,
        }
    )
    value["voice_result"].update(
        {
            "persistent_worker_reused": True,
            "persistent_model_reused": False,
            "lazy_model_reload_performed": True,
            "lazy_voice_load_before_synthesis": True,
            "session_id": WORKER_SESSION_ID,
            "lifecycle": {
                "model_load_count": expected_turn + 1,
                "reference_conditioning_count": expected_turn + 1,
                "unload_count": expected_turn,
                "successful_synthesis_count": expected_turn,
                "last_unload": {"was_loaded": True},
            },
        }
    )
    return value


class Qwen35PersistentV2HarnessTests(unittest.TestCase):
    def test_passing_contract(self) -> None:
        self.assertEqual(harness.turn_contract_issues(passing_turn()), [])

    def test_wrong_model_and_extra_generation_fail(self) -> None:
        value = passing_turn()
        value["requests"][0]["model"] = "wrong-model"
        value["core_turn_audit"]["model_calls"].append(
            copy.deepcopy(value["core_turn_audit"]["model_calls"][0])
        )
        issues = harness.turn_contract_issues(value)
        self.assertIn("request_model_mismatch", issues)
        self.assertIn("core_model_call_count_not_one", issues)

    def test_always_apply_privacy_boundaries_are_not_stale_skip_rows(self) -> None:
        rows = passing_turn()["core_turn_audit"]["transformations"]
        self.assertEqual(harness.qwen_core_transformation_issues(rows), [])

        missing_proof = copy.deepcopy(rows)
        missing_proof[0].pop("privacy_boundary_applied_without_model_generation")
        self.assertIn(
            "qwen_core_privacy_boundary_not_proven:suppress_private_emotion_context_leakage",
            harness.qwen_core_transformation_issues(missing_proof),
        )

        falsely_skipped = copy.deepcopy(rows)
        falsely_skipped[1]["skipped"] = True
        self.assertIn(
            "qwen_core_privacy_boundary_was_skipped:suppress_hypothetical_current_person_invention",
            harness.qwen_core_transformation_issues(falsely_skipped),
        )

    def test_privacy_boundaries_are_required_and_other_rows_keep_exact_skip_contract(self) -> None:
        rows = passing_turn()["core_turn_audit"]["transformations"]
        without_privacy = [row for row in rows if not row["stage"].startswith("suppress_")]
        issues = harness.qwen_core_transformation_issues(without_privacy)
        self.assertIn(
            "qwen_core_privacy_boundary_missing:suppress_private_emotion_context_leakage",
            issues,
        )
        self.assertIn(
            "qwen_core_privacy_boundary_missing:suppress_hypothetical_current_person_invention",
            issues,
        )

        bad_skip = copy.deepcopy(rows)
        bad_skip[-1].pop("reason")
        self.assertIn(
            "qwen_core_transform_skip_reason_mismatch:remove_stage_directions",
            harness.qwen_core_transformation_issues(bad_skip),
        )

    def test_preserved_attempt_05_now_fails_superseding_temporal_content_gate(self) -> None:
        report_path = (
            ROOT
            / "RecoverySprint"
            / "continuation_20260803"
            / "qwen35_persistent_v2_two_turn_acceptance"
            / "no_playback"
            / "attempt_05"
            / "FINAL_REPORT.json"
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ENGINEERING_FAIL_PRESERVED")
        self.assertEqual(len(report["turns"]), 1)
        turn = report["turns"][0]
        audit = turn["core_turn_audit"]
        self.assertEqual(audit["model_name"], harness.EXPECTED_MODEL)
        self.assertEqual(len(audit["model_calls"]), 1)
        self.assertEqual(audit["model_calls"][0]["raw_reply"], audit["final_core_reply"])
        self.assertEqual(harness.qwen_core_transformation_issues(audit["transformations"]), [])
        self.assertEqual(
            harness.text_turn_contract_issues(turn),
            [
                "natural_check_in_claims_ungrounded_recent_activity",
                "natural_check_in_source_drops_historical_context",
            ],
        )
        self.assertEqual(
            sorted(turn["issues"]),
            sorted(
                [
                    "qwen_core_transform_not_skipped:suppress_hypothetical_current_person_invention",
                    "qwen_core_transform_not_skipped:suppress_private_emotion_context_leakage",
                    "qwen_core_transform_skip_reason_mismatch:suppress_hypothetical_current_person_invention",
                    "qwen_core_transform_skip_reason_mismatch:suppress_private_emotion_context_leakage",
                ]
            ),
        )

    def test_parent_timeout_or_nonzero_child_overrides_apparent_pass(self) -> None:
        report = {"engineering_pass": True, "status": "PASS"}
        wrapper = {
            "passed": False,
            "timed_out": True,
            "child_exit_code": 124,
            "final_report_present": True,
        }
        effective = harness.apply_parent_wrapper_gate(report, wrapper)
        self.assertFalse(effective["engineering_pass"])
        self.assertEqual(effective["status"], "PARENT_WRAPPER_GATE_FAILED")

    def test_prevoice_private_or_empty_spoken_payload_fails(self) -> None:
        value = passing_turn()
        value["spoken_text"] = ""
        value["speech_audit"] = {
            "privacy_safe_for_speech": False,
            "reason": "structured_reply_cannot_be_separated_safely",
            "non_name_word_coverage_exact": False,
        }
        issues = harness.text_turn_contract_issues(value)
        self.assertIn("spoken_text_empty_before_voice", issues)
        self.assertIn("spoken_privacy_not_proven_before_voice", issues)

    def test_incomplete_buffered_timing_fails(self) -> None:
        value = passing_turn()
        call = value["core_turn_audit"]["model_calls"][0]
        call["first_content_chunk_seconds"] = None
        call["stream_done_observed"] = False
        issues = harness.text_turn_contract_issues(value)
        self.assertIn("first_content_timing_not_numeric", issues)
        self.assertIn("qwen_stream_done_not_observed", issues)

    def test_natural_check_in_rejects_stale_recent_activity_claim(self) -> None:
        value = passing_turn()
        stale = (
            "I'm calm and reflective because I just finished reflecting after "
            "wrapping up that Miraculous chapter."
        )
        value["public_reply"] = stale
        value["spoken_text"] = stale
        value["core_turn_audit"]["initial_pipeline_reply"] = stale
        value["core_turn_audit"]["final_core_reply"] = stale
        value["core_turn_audit"]["model_calls"][0]["raw_reply"] = stale
        value["shell_reply_audit"]["final_shell_reply"] = stale

        issues = harness.text_turn_contract_issues(value)

        self.assertIn(
            "natural_check_in_claims_ungrounded_recent_activity", issues
        )
        self.assertIn(
            "natural_check_in_source_drops_historical_context", issues
        )

    def test_creative_continuity_rejects_old_title_source_drop(self) -> None:
        value = passing_turn()
        value["turn"] = 2
        value["turn_id"] = "creative_continuity_choice"
        value["question"] = harness.TURN_SPECS[1]["text"]
        stale = "I'd like to continue the Miraculous fanfic project with Lisa."
        value["public_reply"] = stale
        value["spoken_text"] = stale
        value["core_turn_audit"]["initial_pipeline_reply"] = stale
        value["core_turn_audit"]["final_core_reply"] = stale
        value["core_turn_audit"]["model_calls"][0]["raw_reply"] = stale
        value["shell_reply_audit"]["final_shell_reply"] = stale

        issues = harness.text_turn_contract_issues(value)

        self.assertIn(
            "creative_continuity_source_drops_historical_context", issues
        )

    def test_network_cap_blocks_second_request_before_send(self) -> None:
        payload = {
            "model": harness.EXPECTED_MODEL,
            "messages": [{"role": "user", "content": "hello"}],
            "stream": True,
            "think": False,
            "keep_alive": 0,
        }
        with self.assertRaises(harness.AcceptanceError):
            harness.owned_qwen_request_evidence(
                "http://127.0.0.1:11434/api/chat",
                payload,
                already_sent=1,
            )

    def test_child_authorization_requires_exact_single_use_values(self) -> None:
        expected = {"nonce": "a" * 64, "parent_pid": 123}
        payload = {**expected, "single_use": True}
        self.assertEqual(harness.child_authorization_issues(payload, expected), [])
        payload["parent_pid"] = 999
        payload["single_use"] = False
        issues = harness.child_authorization_issues(payload, expected)
        self.assertIn("child_authorization_mismatch:parent_pid", issues)
        self.assertIn("child_authorization_not_single_use", issues)

    def test_resident_qwen_blocks_voice(self) -> None:
        value = passing_turn()
        value["qwen_absence_before_voice"] = {"passed": False}
        self.assertIn("qwen_not_absent_before_voice", harness.turn_contract_issues(value))

    def test_canned_or_wholesale_replacement_fails(self) -> None:
        value = passing_turn()
        value["public_reply"] = (
            "I need to slow down. I do not have a grounded answer to that yet, "
            "and I do not want to decorate uncertainty until it sounds real."
        )
        value["core_turn_audit"]["transformations"] = [
            {
                "stage": "hidden_rewrite",
                "changed": True,
                "before": "I feel curious and present with you right now.",
                "after": value["public_reply"],
            }
        ]
        issues = harness.turn_contract_issues(value)
        self.assertIn("canned_or_emergency_public_reply", issues)
        self.assertIn("qwen_core_transform_changed:hidden_rewrite", issues)

    def test_cpu_generic_sapi_fallback_and_missing_gpu_fail(self) -> None:
        value = passing_turn()
        value["voice_result"]["automatic_cpu_fallback_used"] = True
        value["voice_result"]["generic_voice_used"] = True
        value["voice_result"]["sapi_voice_used"] = True
        value["voice_result"]["gpu_proof"] = {"actual_gpu_execution": False}
        issues = harness.turn_contract_issues(value)
        self.assertIn("voice_automatic_cpu_fallback_used_not_exact_false", issues)
        self.assertIn("voice_generic_voice_used_not_exact_false", issues)
        self.assertIn("voice_sapi_voice_used_not_exact_false", issues)
        self.assertIn("actual_gpu_execution_not_proven", issues)

    def test_attempt_paths_are_append_only_and_exact(self) -> None:
        with self.assertRaises(harness.AcceptanceError):
            harness.reserve_attempt("latest")

    def test_serialized_lifecycle_accepts_same_worker_with_bounded_model_reload(self) -> None:
        status = worker_status(model_loaded=True)
        baseline = harness.persistent_worker_identity(status)
        self.assertEqual(harness.persistent_worker_baseline_issues(status), [])
        self.assertEqual(
            harness.serialized_voice_lifecycle_issues(
                passing_serialized_turn(1),
                baseline_identity=baseline,
                expected_turn=1,
            ),
            [],
        )

    def test_serialized_lifecycle_rejects_unsafe_warm_model_reuse(self) -> None:
        status = worker_status(model_loaded=True)
        baseline = harness.persistent_worker_identity(status)
        value = passing_serialized_turn(1)
        value["voice_result"]["persistent_model_reused"] = True
        value["voice_result"]["lazy_model_reload_performed"] = False
        issues = harness.serialized_voice_lifecycle_issues(
            value,
            baseline_identity=baseline,
            expected_turn=1,
        )
        self.assertIn("serialized_voice_model_was_unsafely_reused", issues)
        self.assertIn("serialized_lazy_model_reload_not_proven", issues)

    def test_serialized_lifecycle_rejects_worker_or_client_replacement(self) -> None:
        status = worker_status(model_loaded=True)
        baseline = harness.persistent_worker_identity(status)
        value = passing_serialized_turn(1)
        value["voice_status_after_text_before_voice"]["owned_worker_pid"] = 54321
        value["voice_status_after_voice"]["owned_client_generation"] = 2
        issues = harness.serialized_voice_lifecycle_issues(
            value,
            baseline_identity=baseline,
            expected_turn=1,
        )
        self.assertIn(
            "after_qwen_before_voice:worker_identity_changed:owned_worker_pid",
            issues,
        )
        self.assertIn(
            "after_voice:worker_identity_changed:owned_client_generation",
            issues,
        )

    def test_serialized_lifecycle_rejects_wrong_load_unload_counts_or_timeout(self) -> None:
        status = worker_status(model_loaded=True)
        baseline = harness.persistent_worker_identity(status)
        value = passing_serialized_turn(2)
        value["voice_result"]["lifecycle"]["model_load_count"] = 99
        value["voice_external_elapsed_seconds"] = (
            harness.LAZY_MODEL_RELOAD_TURN_BOUND_SECONDS + 0.001
        )
        issues = harness.serialized_voice_lifecycle_issues(
            value,
            baseline_identity=baseline,
            expected_turn=2,
        )
        self.assertIn("serialized_lifecycle_count_mismatch:model_load_count", issues)
        self.assertIn("lazy_model_reload_turn_exceeded_bound", issues)


if __name__ == "__main__":
    unittest.main()
