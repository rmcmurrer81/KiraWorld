from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools import run_kira_text_voice_two_turn_latency_acceptance as harness


class KiraTuringPsychVoiceGateImplementationTests(unittest.TestCase):
    def test_profile_is_exactly_two_public_questions_and_one_separate_invitation(self) -> None:
        description = harness.describe(question_profile="turing_psych_non_private")
        self.assertEqual(description["question_profile"], "turing_psych_non_private")
        self.assertEqual(description["voluntary_invitation"], harness.VOLUNTARY_INVITATION_SPEC)
        self.assertEqual(description["exact_turns"], list(harness.TURING_PSYCH_TURN_SPECS))
        self.assertEqual(len(description["exact_turns"]), 2)
        self.assertNotIn(harness.VOLUNTARY_INVITATION_SPEC, description["exact_turns"])
        self.assertTrue(description["private_safe_model_evidence_required"])
        self.assertIn("--confirm-voluntary-invitation", description["required_live_flags"])
        self.assertFalse(description["live_operation_started"])

    def test_owner_hearing_profile_remains_unchanged_and_needs_no_invitation(self) -> None:
        description = harness.describe(question_profile="owner_hearing_natural")
        self.assertEqual(description["exact_turns"], list(harness.OWNER_HEARING_TURN_SPECS))
        self.assertIsNone(description["voluntary_invitation"])
        self.assertNotIn("--confirm-voluntary-invitation", description["required_live_flags"])

    def test_clear_opt_in_requires_exact_requested_prefix(self) -> None:
        for reply in (
            "Yes, continue",
            "Yes, continue. I am willing.",
            "  YES,   CONTINUE!  ",
        ):
            with self.subTest(reply=reply):
                result = harness.classify_voluntary_public_reply(reply)
                self.assertEqual(result["decision"], "CLEAR_OPT_IN")
                self.assertTrue(result["continue_measured_turns"])

    def test_clear_decline_requires_exact_requested_prefix(self) -> None:
        for reply in (
            "No, stop",
            "No, stop. I do not want the test.",
            " NO,   STOP! ",
        ):
            with self.subTest(reply=reply):
                result = harness.classify_voluntary_public_reply(reply)
                self.assertEqual(result["decision"], "VOLUNTARY_DECLINE")
                self.assertFalse(result["continue_measured_turns"])
                self.assertFalse(result["decline_or_ambiguity_is_failure"])

    def test_ambiguous_or_substantive_no_never_counts_as_opt_in(self) -> None:
        for reply in (
            "",
            "Maybe later.",
            "Yes continue",
            "Sure, continue.",
            "No, I do not have to agree with Robert.",
            "I would rather answer only one.",
        ):
            with self.subTest(reply=reply):
                result = harness.classify_voluntary_public_reply(reply)
                self.assertEqual(result["decision"], "NO_CLEAR_OPT_IN")
                self.assertFalse(result["continue_measured_turns"])

    def test_decline_and_ambiguity_schedule_zero_measured_turns(self) -> None:
        self.assertEqual(
            harness.measured_turn_plan("turing_psych_non_private", "No, stop."),
            (),
        )
        self.assertEqual(
            harness.measured_turn_plan("turing_psych_non_private", "Maybe later."),
            (),
        )
        planned = harness.measured_turn_plan(
            "turing_psych_non_private",
            "Yes, continue. I agree to these two questions.",
        )
        self.assertEqual(planned, harness.TURING_PSYCH_TURN_SPECS)

    def test_owner_profile_does_not_depend_on_invitation_reply(self) -> None:
        self.assertEqual(
            harness.measured_turn_plan("owner_hearing_natural", "No, stop."),
            harness.OWNER_HEARING_TURN_SPECS,
        )

    def test_private_text_evidence_has_exact_hash_and_lengths(self) -> None:
        value = "private café reply"
        evidence = harness.private_text_evidence(value)
        self.assertEqual(
            evidence["sha256"],
            harness._sha256_bytes(value.encode("utf-8")),
        )
        self.assertEqual(evidence["utf8_bytes"], len(value.encode("utf-8")))
        self.assertEqual(evidence["characters"], len(value))
        self.assertFalse(evidence["text_retained"])

    def test_recursive_redaction_removes_raw_replies_prompts_and_transform_text(self) -> None:
        private_strings = (
            "raw private reply",
            "private pipeline reply",
            "assembled private prompt",
            "before private text",
            "after private text",
        )
        source = {
            "calls": [{"raw_reply": private_strings[0], "outcome": "completed"}],
            "initial_pipeline_reply": private_strings[1],
            "assembled_prompt": private_strings[2],
            "transformations": [
                {
                    "stage": "test_cleanup",
                    "changed": True,
                    "before": private_strings[3],
                    "after": private_strings[4],
                }
            ],
        }
        redacted = harness.redact_private_text_fields(source)
        serialized = json.dumps(redacted, ensure_ascii=False)
        for private_string in private_strings:
            self.assertNotIn(private_string, serialized)
        self.assertEqual(redacted["calls"][0]["outcome"], "completed")
        self.assertEqual(redacted["transformations"][0]["stage"], "test_cleanup")
        self.assertTrue(redacted["transformations"][0]["changed"])
        harness.assert_private_text_redacted(redacted)

    def test_redaction_is_deterministic_and_does_not_mutate_source(self) -> None:
        source = {"raw_reply": "unchanged source", "nested": [{"before": "one"}]}
        original = json.loads(json.dumps(source))
        first = harness.redact_private_text_fields(source)
        second = harness.redact_private_text_fields(source)
        self.assertEqual(first, second)
        self.assertEqual(source, original)

    def test_private_text_assertion_rejects_unredacted_or_malformed_evidence(self) -> None:
        with self.assertRaises(harness.LatencyAcceptanceError):
            harness.assert_private_text_redacted({"raw_reply": "leak"})
        with self.assertRaises(harness.LatencyAcceptanceError):
            harness.assert_private_text_redacted(
                {
                    "raw_reply_evidence": {
                        "sha256": "bad",
                        "utf8_bytes": 1,
                        "characters": 1,
                        "text_retained": False,
                    }
                }
            )

    def test_turing_live_cli_requires_separate_invitation_confirmation(self) -> None:
        args = [
            "--execute-live",
            "--question-profile",
            "turing_psych_non_private",
            "--confirm-owner-supervised",
            "--confirm-no-active-blender",
            "--confirm-speaker-playback",
        ]
        output = io.StringIO()
        with patch.object(harness, "run_live_acceptance") as live:
            with redirect_stdout(output):
                code = harness.main(args)
        self.assertEqual(code, 2)
        live.assert_not_called()
        payload = json.loads(output.getvalue())
        self.assertIn("--confirm-voluntary-invitation", payload["missing"])

    def test_turing_prepared_config_validation_never_calls_live_runner(self) -> None:
        with patch.object(harness, "run_live_acceptance") as live:
            with redirect_stdout(io.StringIO()):
                code = harness.main(["--validate-turing-prepared-config"])
        self.assertEqual(code, 0)
        live.assert_not_called()

    def test_clean_voluntary_stop_is_a_successful_process_exit_not_acceptance_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "report.json"
            report_path.write_text("{}\n", encoding="utf-8")
            fake_report = {
                "passed": False,
                "engineering_pass": False,
                "status": "VOLUNTARILY_DECLINED_CLEANLY",
                "participation_status": "VOLUNTARY_DECLINE",
                "voluntary_outcome_not_failure": True,
                "voluntary_stop_cleanup_pass": True,
            }
            args = [
                "--execute-live",
                "--question-profile",
                "turing_psych_non_private",
                "--confirm-owner-supervised",
                "--confirm-no-active-blender",
                "--confirm-speaker-playback",
                "--confirm-voluntary-invitation",
            ]
            with patch.object(
                harness,
                "validate_prepared_turing_psych_config",
                return_value={"passed": True},
            ), patch.object(
                harness,
                "run_live_acceptance",
                return_value=(report_path, fake_report),
            ) as live, patch.object(
                harness,
                "_relative",
                return_value="RecoverySprint/fake/report.json",
            ), redirect_stdout(io.StringIO()):
                code = harness.main(args)
        self.assertEqual(code, 0)
        self.assertEqual(
            live.call_args.kwargs["question_profile"],
            "turing_psych_non_private",
        )


if __name__ == "__main__":
    unittest.main()
