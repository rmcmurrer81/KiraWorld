from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest import mock

from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v2 as v2
from tools import run_qwen35_kira_turing_psych_voice_owner_evaluation as retained


class LongKiraTuringHealthBodyVoiceEvaluationV2Tests(unittest.TestCase):
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
        execution, base = v2.load_and_validate_v2_contract()
        v2.configure_retained_runner_v2(
            execution,
            base,
            unattended=unattended,
        )
        return execution, base

    @staticmethod
    def _synthetic_report(base: dict, count: int = 36) -> dict:
        rows = [
            {"turn_id": row["id"]}
            for row in base["turns"][: min(count, len(base["turns"]))]
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

    def test_v2_contract_loads_exact_sealed_36_turn_base(self) -> None:
        execution, base = v2.load_and_validate_v2_contract()
        self.assertEqual(execution["schema_version"], 2)
        self.assertEqual(len(base["turns"]), 36)
        self.assertEqual(base["model"]["name"], "qwen3.5:9b")
        self.assertEqual(base["model"]["maximum_generations"], 37)
        self.assertFalse(base["model"]["llama_allowed"])

    def test_v2_plan_hash_is_exact(self) -> None:
        self.assertEqual(
            v2._sha256_bytes(v2.V2_PLAN_PATH.read_bytes()),
            v2.V2_PLAN_SHA256,
        )

    def test_timeouts_are_ordered_and_within_sealed_90_minutes(self) -> None:
        self.assertLess(v2.CHILD_WATCHDOG_SECONDS, v2.PARENT_TIMEOUT_SECONDS)
        self.assertLessEqual(v2.PARENT_TIMEOUT_SECONDS, 5400)
        self.assertEqual(v2.CHILD_WATCHDOG_SECONDS, 5100)
        self.assertEqual(v2.PARENT_TIMEOUT_SECONDS, 5250)

    def test_truthful_unattended_flag_replaces_supervision_flag(self) -> None:
        flags = v2._unattended_required_flags()
        self.assertIn(v2.UNATTENDED_AUTHORIZATION_FLAG, flags)
        self.assertNotIn(v2.LEGACY_SUPERVISION_FLAG, flags)
        self.assertTrue(
            v2.classify_invocation_mode(
                [v2.UNATTENDED_MARKER, v2.UNATTENDED_AUTHORIZATION_FLAG]
            )
        )
        with self.assertRaises(v2.LongEvaluationV2Error):
            v2.classify_invocation_mode([v2.UNATTENDED_MARKER])
        with self.assertRaises(v2.LongEvaluationV2Error):
            v2.classify_invocation_mode([v2.UNATTENDED_AUTHORIZATION_FLAG])
        with self.assertRaises(v2.LongEvaluationV2Error):
            v2.classify_invocation_mode(
                [
                    v2.UNATTENDED_MARKER,
                    v2.UNATTENDED_AUTHORIZATION_FLAG,
                    v2.LEGACY_SUPERVISION_FLAG,
                ]
            )

    def test_unattended_child_inherits_truthful_authorization_without_marker(self) -> None:
        self.assertTrue(
            v2.classify_invocation_mode(
                ["--child-run", v2.UNATTENDED_AUTHORIZATION_FLAG]
            )
        )
        with self.assertRaises(v2.LongEvaluationV2Error):
            v2.classify_invocation_mode(
                [
                    "--child-run",
                    v2.UNATTENDED_AUTHORIZATION_FLAG,
                    v2.LEGACY_SUPERVISION_FLAG,
                ]
            )

    def test_interactive_configuration_preserves_supervision_requirement(self) -> None:
        self._configure(unattended=False)
        self.assertIn(v2.LEGACY_SUPERVISION_FLAG, retained.REQUIRED_PUBLIC_FLAGS)
        self.assertNotIn(
            v2.UNATTENDED_AUTHORIZATION_FLAG,
            retained.REQUIRED_PUBLIC_FLAGS,
        )
        self.assertIs(
            retained.collect_post_playback_owner_acknowledgment,
            v2._ORIGINAL_OWNER_ACKNOWLEDGMENT,
        )

    def test_unattended_configuration_never_claims_supervision_or_hearing(self) -> None:
        self._configure(unattended=True)
        self.assertNotIn(v2.LEGACY_SUPERVISION_FLAG, retained.REQUIRED_PUBLIC_FLAGS)
        acknowledgment = retained.collect_post_playback_owner_acknowledgment({})
        self.assertFalse(acknowledgment["requested"])
        self.assertFalse(acknowledgment["acknowledged"])
        self.assertFalse(acknowledgment["physical_supervision_claimed"])
        self.assertEqual(
            acknowledgment["reason"],
            "owner_not_present_owner_authorized_unattended_log_review",
        )

    def test_actual_post_configuration_validator_accepts_exact_36_count(self) -> None:
        _, base = self._configure()
        report = self._synthetic_report(base, 36)
        original = set(v2._ORIGINAL_FINAL_VALIDATOR(report))
        observed = set(retained.final_run_contract_issues(report))
        self.assertIn(v2.LEGACY_COUNT_ISSUE, original)
        self.assertNotIn(v2.LEGACY_COUNT_ISSUE, observed)
        self.assertNotIn(v2.V2_COUNT_ISSUE, observed)
        self.assertNotIn(v2.V2_CAP_ISSUE, observed)
        self.assertEqual(observed, original - {v2.LEGACY_COUNT_ISSUE})

    def test_actual_validator_rejects_6_35_and_37_turns(self) -> None:
        _, base = self._configure()
        for count in (6, 35, 37):
            with self.subTest(count=count):
                report = self._synthetic_report(base, count)
                issues = retained.final_run_contract_issues(report)
                self.assertIn(v2.V2_COUNT_ISSUE, issues)
                self.assertNotIn(v2.LEGACY_COUNT_ISSUE, issues)

    def test_actual_validator_rejects_missing_and_extra_identity_at_count_36(self) -> None:
        _, base = self._configure()
        report = self._synthetic_report(base, 36)
        report["turns"][0] = {"turn_id": "unexpected_extra_replacing_missing_id"}
        issues = retained.final_run_contract_issues(report)
        self.assertNotIn(v2.V2_COUNT_ISSUE, issues)
        self.assertIn("measured_turn_sequence_mismatch", issues)

    def test_actual_validator_rejects_generation_cap_drift(self) -> None:
        _, base = self._configure()
        report = self._synthetic_report(base, 36)
        retained.MAX_TOTAL_QWEN_REQUESTS = 36
        self.assertIn(
            v2.V2_CAP_ISSUE,
            retained.final_run_contract_issues(report),
        )

    def test_every_non_count_retained_issue_is_preserved(self) -> None:
        _, base = self._configure()
        report = self._synthetic_report(base, 36)
        original = set(v2._ORIGINAL_FINAL_VALIDATOR(report))
        observed = set(retained.final_run_contract_issues(report))
        self.assertTrue(original - {v2.LEGACY_COUNT_ISSUE} <= observed)
        self.assertIn("protected_state_changed", observed)
        self.assertIn("final_voice_worker_release_not_clean", observed)

    def test_unattended_mode_missing_authorization_is_inert_before_retained_main(self) -> None:
        with mock.patch.object(retained, "main") as retained_main:
            with self.assertRaises(v2.LongEvaluationV2Error):
                v2.main([v2.UNATTENDED_MARKER])
        retained_main.assert_not_called()

    def test_truthful_unattended_public_command_forwards_no_supervision_claim(self) -> None:
        incoming = [
            v2.UNATTENDED_MARKER,
            "--execute-live",
            "--attempt-label",
            "attempt_01",
            "--confirm-exact-qwen35",
            "--confirm-voluntary-invitation",
            "--confirm-speaker-playback",
            "--confirm-no-active-blender-or-heavy-gpu-workload",
            "--confirm-approved-blackwell-v2-route",
            v2.UNATTENDED_AUTHORIZATION_FLAG,
        ]
        with mock.patch.object(retained, "main", return_value=1) as retained_main:
            result = v2.main(incoming)
        self.assertEqual(result, 1)
        forwarded = retained_main.call_args.args[0]
        self.assertNotIn(v2.UNATTENDED_MARKER, forwarded)
        self.assertNotIn(v2.LEGACY_SUPERVISION_FLAG, forwarded)
        self.assertIn(v2.UNATTENDED_AUTHORIZATION_FLAG, forwarded)

    def test_only_attempt_01_is_permitted(self) -> None:
        v2.validate_attempt_binding([])
        v2.validate_attempt_binding(["--attempt-label", "attempt_01"])
        with self.assertRaises(v2.LongEvaluationV2Error):
            v2.validate_attempt_binding(["--attempt-label", "attempt_02"])
        with self.assertRaises(v2.LongEvaluationV2Error):
            v2.validate_attempt_binding(
                [
                    "--child-run",
                    "--attempt-path",
                    str(v2.EVIDENCE_ROOT / "attempt_02"),
                    "--generated-path",
                    str(v2.GENERATED_ROOT / "attempt_02"),
                ]
            )

    def test_attempt_01_roots_remain_absent_during_static_preparation(self) -> None:
        self.assertFalse((v2.EVIDENCE_ROOT / v2.ONLY_ATTEMPT_LABEL).exists())
        self.assertFalse((v2.GENERATED_ROOT / v2.ONLY_ATTEMPT_LABEL).exists())

    def test_duplicate_v2_json_key_is_rejected(self) -> None:
        with self.assertRaises(v2.LongEvaluationV2Error):
            json.loads('{"a":1,"a":2}', object_pairs_hook=v2._strict_object)

    def test_outer_technical_result_requires_no_owner_hearing_claim(self) -> None:
        source = Path(v2.__file__).read_text(encoding="utf-8")
        self.assertIn(
            'child_report.get("owner_post_playback_acknowledged") is False',
            source,
        )
        self.assertIn('parent_wrapper.get("process_gate_passed") is True', source)
        self.assertIn('parent_wrapper.get("parent_report_contract_issues") == []', source)
        self.assertIn('"physical_owner_supervision_claimed": False', source)
        self.assertIn('"owner_hearing_acknowledged": False', source)


if __name__ == "__main__":
    unittest.main()
