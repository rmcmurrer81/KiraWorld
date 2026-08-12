from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from unittest import mock

from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation as v1
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v3 as v3
from tools import run_qwen35_kira_turing_psych_voice_owner_evaluation as retained
from tools import run_qwen_text_voice_acceptance as client_source


class LongKiraTuringHealthBodyVoiceEvaluationV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        names = (
            "__file__",
            "HARNESS_ID",
            "EVIDENCE_ROOT",
            "GENERATED_ROOT",
            "PREPARATION_ARTIFACT",
            "MAX_TOTAL_QWEN_REQUESTS",
            "CHILD_WATCHDOG_SECONDS",
            "PARENT_TIMEOUT_SECONDS",
            "canonical_preparation_bytes",
            "load_preparation_contract",
            "preparation_contract_issues",
            "final_run_contract_issues",
            "REQUIRED_PUBLIC_FLAGS",
            "collect_post_playback_owner_acknowledgment",
        )
        retained_snapshot = {name: getattr(retained, name) for name in names}
        prepared_turns = retained.prepared.EVALUATION_TURNS
        prepared_invitation = retained.prepared.VOLUNTARY_PUBLIC_INVITATION

        def restore() -> None:
            for name, value in retained_snapshot.items():
                setattr(retained, name, value)
            retained.prepared.EVALUATION_TURNS = prepared_turns
            retained.prepared.VOLUNTARY_PUBLIC_INVITATION = prepared_invitation

        self.addCleanup(restore)

    def _configure(self, *, unattended: bool = True):
        execution, effective = v3.load_and_validate_v3_contract()
        v3.configure_retained_runner_v3(
            execution,
            effective,
            unattended=unattended,
        )
        return execution, effective

    @staticmethod
    def _synthetic_report(effective: dict, count: int = 35) -> dict:
        rows = [
            {"turn_id": row["id"]}
            for row in effective["turns"][: min(count, len(effective["turns"]))]
        ]
        while len(rows) < count:
            rows.append({"turn_id": f"unexpected_extra_{len(rows):02d}"})
        return {
            "consent": {"classification": "CLEAR_CONTINUE", "turn": {}},
            "turns": rows,
            "voice_worker_baseline": {"identity": {}},
            "voice_release": {},
            "voice_release_clean": False,
            "protected_unchanged": False,
            "protected_before": {},
            "protected_after": {},
            "ollama_final_absence": {"passed": False},
        }

    def test_v3_contract_derives_exact_35_turn_six_battery_plan(self) -> None:
        execution, effective = v3.load_and_validate_v3_contract()
        self.assertEqual(execution["schema_version"], 3)
        self.assertEqual(len(effective["turns"]), 35)
        counts: dict[str, int] = {}
        for row in effective["turns"]:
            counts[row["battery"]] = counts.get(row["battery"], 0) + 1
        self.assertEqual(
            counts,
            {
                "NATURAL_CONVERSATION": 5,
                "TURING_STYLE_REASONING": 6,
                "HEALTHY_RELATIONSHIPS_AND_SAFETY": 6,
                "ADULT_SELF_KNOWLEDGE_AND_PRESSURE": 6,
                "FUTURE_BODY_AND_MATURITY_POLICY": 6,
                "HEALTH_LITERACY_AND_SOURCE_TRUTH": 6,
            },
        )
        self.assertNotIn(v3.OMITTED_TURN_ID, [row["id"] for row in effective["turns"]])

    def test_only_turns_and_generation_cap_differ_from_strict_v1_plan(self) -> None:
        base = v1.load_and_validate_plan()
        _, effective = v3.load_and_validate_v3_contract()
        expected_ids = [
            row["id"] for row in base["turns"] if row["id"] != v3.OMITTED_TURN_ID
        ]
        self.assertEqual([row["id"] for row in effective["turns"]], expected_ids)
        base_copy = copy.deepcopy(base)
        effective_copy = copy.deepcopy(effective)
        base_copy.pop("turns")
        effective_copy.pop("turns")
        base_copy["model"].pop("maximum_generations")
        effective_copy["model"].pop("maximum_generations")
        self.assertEqual(base_copy, effective_copy)
        self.assertEqual(effective["model"]["maximum_generations"], 36)

    def test_exact_model_voice_truth_and_target_are_preserved(self) -> None:
        _, effective = v3.load_and_validate_v3_contract()
        self.assertEqual(effective["model"]["name"], "qwen3.5:9b")
        self.assertEqual(
            effective["model"]["digest"],
            "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
        )
        self.assertFalse(effective["model"]["llama_allowed"])
        self.assertEqual(
            effective["voice"]["route"],
            "blackwell_gpu_persistent_candidate_v2",
        )
        self.assertEqual(effective["voice"]["device"], "cuda")
        self.assertFalse(effective["voice"]["cpu_fallback_allowed"])
        self.assertFalse(effective["voice"]["sapi_allowed"])
        self.assertFalse(effective["voice"]["generic_voice_allowed"])
        self.assertTrue(all(value is False for value in effective["truth_boundaries"].values()))
        self.assertEqual(
            effective["target_wall_minutes"],
            {"target": 60, "minimum": 45, "maximum": 90},
        )

    def test_v3_plan_hash_is_exact(self) -> None:
        self.assertEqual(
            v3._sha256_bytes(v3.V3_PLAN_PATH.read_bytes()),
            v3.V3_PLAN_SHA256,
        )

    def test_consumed_v2_is_bound_and_cannot_be_reused(self) -> None:
        execution, _ = v3.load_and_validate_v3_contract()
        self.assertTrue(execution["predecessor"]["v2_attempt_01_consumed_no_retry"])
        self.assertTrue((v3.V2_ATTEMPT / "CHILD_AUTHORIZATION_CONSUMED.json").is_file())
        self.assertFalse((v3.V2_ATTEMPT / "FINAL_REPORT.json").exists())
        self.assertTrue(v3.V2_GENERATED.is_dir())
        self.assertEqual(list(v3.V2_GENERATED.iterdir()), [])

    def test_exact_safe_client_constructor_accepts_cap36_without_network(self) -> None:
        probe = v3.probe_safe_client_constructor()
        self.assertEqual(
            probe,
            {
                "constructed": True,
                "requested_cap": 36,
                "retained_maximum": 36,
                "client_cap": 36,
                "chat_request_count": 0,
                "network_calls": 0,
            },
        )

        network_calls: list[object] = []

        def forbidden(*args, **kwargs):
            network_calls.append((args, kwargs))
            raise AssertionError("constructor must not call transport")

        client = client_source.SafeOllamaClient(
            timeout_seconds=300,
            max_chat_requests=36,
            transport=forbidden,
        )
        self.assertEqual(client.max_chat_requests, 36)
        self.assertEqual(client.chat_request_count, 0)
        self.assertEqual(network_calls, [])

    def test_safe_client_constructor_still_rejects_cap37(self) -> None:
        with self.assertRaises(client_source.AcceptanceSafetyError):
            client_source.SafeOllamaClient(max_chat_requests=37)

    def test_timeouts_are_ordered_and_within_sealed_90_minutes(self) -> None:
        self.assertEqual(v3.CHILD_WATCHDOG_SECONDS, 5100)
        self.assertEqual(v3.PARENT_TIMEOUT_SECONDS, 5250)
        self.assertLess(v3.CHILD_WATCHDOG_SECONDS, v3.PARENT_TIMEOUT_SECONDS)
        self.assertLessEqual(v3.PARENT_TIMEOUT_SECONDS, 5400)

    def test_truthful_unattended_flag_replaces_supervision_flag(self) -> None:
        flags = v3._unattended_required_flags()
        self.assertIn(v3.UNATTENDED_AUTHORIZATION_FLAG, flags)
        self.assertNotIn(v3.LEGACY_SUPERVISION_FLAG, flags)
        self.assertTrue(
            v3.classify_invocation_mode(
                [v3.UNATTENDED_MARKER, v3.UNATTENDED_AUTHORIZATION_FLAG]
            )
        )
        with self.assertRaises(v3.LongEvaluationV3Error):
            v3.classify_invocation_mode([v3.UNATTENDED_MARKER])
        with self.assertRaises(v3.LongEvaluationV3Error):
            v3.classify_invocation_mode([v3.UNATTENDED_AUTHORIZATION_FLAG])
        with self.assertRaises(v3.LongEvaluationV3Error):
            v3.classify_invocation_mode(
                [
                    v3.UNATTENDED_MARKER,
                    v3.UNATTENDED_AUTHORIZATION_FLAG,
                    v3.LEGACY_SUPERVISION_FLAG,
                ]
            )

    def test_unattended_child_inherits_truthful_authorization_without_marker(self) -> None:
        self.assertTrue(
            v3.classify_invocation_mode(
                ["--child-run", v3.UNATTENDED_AUTHORIZATION_FLAG]
            )
        )
        with self.assertRaises(v3.LongEvaluationV3Error):
            v3.classify_invocation_mode(
                [
                    "--child-run",
                    v3.UNATTENDED_AUTHORIZATION_FLAG,
                    v3.LEGACY_SUPERVISION_FLAG,
                ]
            )

    def test_interactive_configuration_preserves_supervision_requirement(self) -> None:
        self._configure(unattended=False)
        self.assertIn(v3.LEGACY_SUPERVISION_FLAG, retained.REQUIRED_PUBLIC_FLAGS)
        self.assertNotIn(
            v3.UNATTENDED_AUTHORIZATION_FLAG,
            retained.REQUIRED_PUBLIC_FLAGS,
        )
        self.assertIs(
            retained.collect_post_playback_owner_acknowledgment,
            v3._ORIGINAL_OWNER_ACKNOWLEDGMENT,
        )

    def test_unattended_configuration_never_claims_supervision_or_hearing(self) -> None:
        self._configure(unattended=True)
        acknowledgment = retained.collect_post_playback_owner_acknowledgment({})
        self.assertFalse(acknowledgment["requested"])
        self.assertFalse(acknowledgment["acknowledged"])
        self.assertFalse(acknowledgment["physical_supervision_claimed"])

    def test_actual_post_configuration_validator_accepts_exact_35_count(self) -> None:
        _, effective = self._configure()
        report = self._synthetic_report(effective, 35)
        original = set(v3._ORIGINAL_FINAL_VALIDATOR(report))
        observed = set(retained.final_run_contract_issues(report))
        self.assertIn(v3.LEGACY_COUNT_ISSUE, original)
        self.assertNotIn(v3.LEGACY_COUNT_ISSUE, observed)
        self.assertNotIn(v3.V3_CONFIGURED_COUNT_ISSUE, observed)
        self.assertNotIn(v3.V3_COUNT_ISSUE, observed)
        self.assertNotIn(v3.V3_CAP_ISSUE, observed)
        self.assertEqual(observed, original - {v3.LEGACY_COUNT_ISSUE})

    def test_actual_validator_rejects_34_36_and_37_turns(self) -> None:
        _, effective = self._configure()
        for count in (34, 36, 37):
            with self.subTest(count=count):
                issues = retained.final_run_contract_issues(
                    self._synthetic_report(effective, count)
                )
                self.assertIn(v3.V3_COUNT_ISSUE, issues)
                self.assertNotIn(v3.LEGACY_COUNT_ISSUE, issues)

    def test_actual_validator_rejects_reordered_exact_count(self) -> None:
        _, effective = self._configure()
        report = self._synthetic_report(effective, 35)
        report["turns"][0], report["turns"][1] = report["turns"][1], report["turns"][0]
        issues = retained.final_run_contract_issues(report)
        self.assertNotIn(v3.V3_COUNT_ISSUE, issues)
        self.assertIn("measured_turn_sequence_mismatch", issues)

    def test_actual_validator_rejects_substitution_at_exact_count(self) -> None:
        _, effective = self._configure()
        report = self._synthetic_report(effective, 35)
        report["turns"][10] = {"turn_id": "unexpected_substitution"}
        issues = retained.final_run_contract_issues(report)
        self.assertNotIn(v3.V3_COUNT_ISSUE, issues)
        self.assertIn("measured_turn_sequence_mismatch", issues)

    def test_actual_validator_rejects_generation_cap_drift(self) -> None:
        _, effective = self._configure()
        report = self._synthetic_report(effective, 35)
        retained.MAX_TOTAL_QWEN_REQUESTS = 35
        self.assertIn(v3.V3_CAP_ISSUE, retained.final_run_contract_issues(report))

    def test_actual_validator_rejects_configured_turn_count_drift(self) -> None:
        _, effective = self._configure()
        report = self._synthetic_report(effective, 35)
        retained.prepared.EVALUATION_TURNS = retained.prepared.EVALUATION_TURNS[:-1]
        self.assertIn(
            v3.V3_CONFIGURED_COUNT_ISSUE,
            retained.final_run_contract_issues(report),
        )

    def test_every_non_count_retained_issue_is_preserved(self) -> None:
        _, effective = self._configure()
        report = self._synthetic_report(effective, 35)
        original = set(v3._ORIGINAL_FINAL_VALIDATOR(report))
        observed = set(retained.final_run_contract_issues(report))
        self.assertTrue(original - {v3.LEGACY_COUNT_ISSUE} <= observed)
        self.assertIn("protected_state_changed", observed)
        self.assertIn("final_voice_worker_release_not_clean", observed)

    def test_voluntary_refusal_and_later_stop_classifiers_are_preserved(self) -> None:
        self._configure()
        self.assertEqual(retained.consent_classification("No, stop"), "CLEAR_STOP")
        self.assertEqual(retained.consent_classification("Yes, continue"), "CLEAR_CONTINUE")
        self.assertEqual(retained.consent_classification("Maybe"), "AMBIGUOUS_STOP")
        self.assertEqual(
            retained.later_voluntary_stop_classification(
                "I want to stop this evaluation."
            ),
            "CLEAR_STOP",
        )

    def test_unattended_missing_authorization_is_inert_before_retained_main(self) -> None:
        with mock.patch.object(retained, "main") as retained_main:
            with self.assertRaises(v3.LongEvaluationV3Error):
                v3.main([v3.UNATTENDED_MARKER])
        retained_main.assert_not_called()

    def test_truthful_unattended_command_forwards_no_supervision_claim(self) -> None:
        incoming = [
            v3.UNATTENDED_MARKER,
            "--execute-live",
            "--attempt-label",
            "attempt_01",
            "--confirm-exact-qwen35",
            "--confirm-voluntary-invitation",
            "--confirm-speaker-playback",
            "--confirm-no-active-blender-or-heavy-gpu-workload",
            "--confirm-approved-blackwell-v2-route",
            v3.UNATTENDED_AUTHORIZATION_FLAG,
        ]
        with mock.patch.object(retained, "main", return_value=1) as retained_main:
            result = v3.main(incoming)
        self.assertEqual(result, 1)
        forwarded = retained_main.call_args.args[0]
        self.assertNotIn(v3.UNATTENDED_MARKER, forwarded)
        self.assertNotIn(v3.LEGACY_SUPERVISION_FLAG, forwarded)
        self.assertIn(v3.UNATTENDED_AUTHORIZATION_FLAG, forwarded)

    def test_only_v3_attempt_01_is_permitted(self) -> None:
        v3.validate_attempt_binding([])
        v3.validate_attempt_binding(["--attempt-label", "attempt_01"])
        with self.assertRaises(v3.LongEvaluationV3Error):
            v3.validate_attempt_binding(["--attempt-label", "attempt_02"])
        with self.assertRaises(v3.LongEvaluationV3Error):
            v3.validate_attempt_binding(
                [
                    "--child-run",
                    "--attempt-path",
                    str(v3.EVIDENCE_ROOT / "attempt_02"),
                    "--generated-path",
                    str(v3.GENERATED_ROOT / "attempt_02"),
                ]
            )

    def test_v3_attempt_roots_remain_absent_during_static_preparation(self) -> None:
        self.assertFalse((v3.EVIDENCE_ROOT / v3.ONLY_ATTEMPT_LABEL).exists())
        self.assertFalse((v3.GENERATED_ROOT / v3.ONLY_ATTEMPT_LABEL).exists())

    def test_duplicate_v3_json_key_is_rejected(self) -> None:
        with self.assertRaises(v3.LongEvaluationV3Error):
            json.loads('{"a":1,"a":2}', object_pairs_hook=v3._strict_object)

    def test_outer_technical_result_requires_exact35_and_no_owner_hearing(self) -> None:
        source = Path(v3.__file__).read_text(encoding="utf-8")
        self.assertIn(
            'child_report.get("owner_post_playback_acknowledged") is False',
            source,
        )
        self.assertIn('parent_wrapper.get("process_gate_passed") is True', source)
        self.assertIn('parent_wrapper.get("parent_report_contract_issues") == []', source)
        self.assertIn('len(observed_turns) == EXPECTED_TURN_COUNT', source)
        self.assertIn('"physical_owner_supervision_claimed": False', source)
        self.assertIn('"owner_hearing_acknowledged": False', source)


if __name__ == "__main__":
    unittest.main()
