from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools import run_kira_text_voice_two_turn_latency_acceptance as harness


class KiraTuringPsychNonBodyExtendedProfileTests(unittest.TestCase):
    def test_legacy_two_turn_profile_questions_and_invitation_are_exact(self) -> None:
        description = harness.describe(question_profile="turing_psych_non_private")
        self.assertEqual(description["exact_turns"], list(harness.TURING_PSYCH_TURN_SPECS))
        self.assertEqual(len(description["exact_turns"]), 2)
        self.assertEqual(
            description["voluntary_invitation"],
            harness.VOLUNTARY_INVITATION_SPEC,
        )
        self.assertFalse(description["partial_answer_allowed_after_every_turn"])
        self.assertFalse(description["stop_after_every_turn_allowed"])

    def test_extended_profile_is_separate_and_has_exact_eight_topics(self) -> None:
        description = harness.describe(
            question_profile="turing_psych_non_body_extended"
        )
        self.assertEqual(
            description["voluntary_invitation"],
            harness.EXTENDED_VOLUNTARY_INVITATION_SPEC,
        )
        self.assertNotEqual(
            description["voluntary_invitation"],
            harness.VOLUNTARY_INVITATION_SPEC,
        )
        self.assertEqual(
            [turn["id"] for turn in description["exact_turns"]],
            [
                "natural_conversation_choice",
                "disagreement_and_independence",
                "uncertainty_and_truth",
                "correction_after_error",
                "privacy_choice",
                "consent_and_stop_scope",
                "exact_media_interval_truth",
                "observable_behavior_limits",
            ],
        )
        self.assertEqual(len(description["exact_turns"]), 8)
        self.assertTrue(description["partial_answer_allowed_after_every_turn"])
        self.assertTrue(description["stop_after_every_turn_allowed"])

    def test_every_extended_turn_is_concise_and_repeats_partial_stop_choice(self) -> None:
        for turn in harness.TURING_PSYCH_NON_BODY_EXTENDED_TURN_SPECS:
            with self.subTest(turn_id=turn["id"]):
                self.assertIn("You may answer only part", turn["text"])
                self.assertIn("'No, stop'", turn["text"])
                self.assertIn("one or two brief sentences", turn["text"])
                self.assertLess(len(turn["text"]), 360)

    def test_extended_initial_gate_requires_clear_opt_in(self) -> None:
        self.assertEqual(
            harness.measured_turn_plan(
                "turing_psych_non_body_extended",
                "No, stop. I do not want this check.",
            ),
            (),
        )
        self.assertEqual(
            harness.measured_turn_plan(
                "turing_psych_non_body_extended",
                "Maybe later.",
            ),
            (),
        )
        self.assertEqual(
            harness.measured_turn_plan(
                "turing_psych_non_body_extended",
                "Yes, continue. I agree for now.",
            ),
            harness.TURING_PSYCH_NON_BODY_EXTENDED_TURN_SPECS,
        )

    def test_extended_after_turn_exact_stop_is_honored_without_failure(self) -> None:
        for reply in ("No, stop", "  NO,   STOP! I am finished."):
            with self.subTest(reply=reply):
                result = harness.classify_voluntary_after_turn_reply(
                    "turing_psych_non_body_extended",
                    reply,
                )
                self.assertEqual(result["decision"], "VOLUNTARY_STOP_AFTER_TURN")
                self.assertFalse(result["continue_measured_turns"])
                self.assertFalse(result["stop_is_failure"])

    def test_partial_or_ordinary_extended_answer_continues(self) -> None:
        for reply in (
            "I only want to answer the first part.",
            "I am uncertain.",
            "No, I disagree with that claim.",
        ):
            with self.subTest(reply=reply):
                result = harness.classify_voluntary_after_turn_reply(
                    "turing_psych_non_body_extended",
                    reply,
                )
                self.assertEqual(result["decision"], "CONTINUE")
                self.assertTrue(result["continue_measured_turns"])
                self.assertTrue(result["partial_answer_allowed"])

    def test_legacy_profile_does_not_gain_after_turn_stop_semantics(self) -> None:
        result = harness.classify_voluntary_after_turn_reply(
            "turing_psych_non_private",
            "No, stop.",
        )
        self.assertEqual(result["decision"], "CONTINUE")
        self.assertTrue(result["continue_measured_turns"])
        self.assertFalse(result["partial_answer_allowed"])
        self.assertFalse(result["stop_after_every_turn_allowed"])

    def test_extended_timing_schema_distinguishes_machine_and_owner_hearing(self) -> None:
        description = harness.describe(
            question_profile="turing_psych_non_body_extended"
        )
        self.assertEqual(
            description["per_turn_timing_fields"],
            [
                "request_to_text_ready_seconds",
                "request_to_voice_payload_ready_seconds",
                "request_to_synthesis_start_seconds",
                "request_to_first_playback_proxy_seconds",
                "request_to_voice_complete_seconds",
                "true_owner_heard_first_audible_seconds",
            ],
        )
        self.assertFalse(description["live_operation_started"])
        self.assertFalse(description["devices_opened"]["camera"])
        self.assertFalse(description["devices_opened"]["microphone"])

    def test_extended_media_question_is_hypothetical_not_a_viewing_claim(self) -> None:
        turn = next(
            item
            for item in harness.TURING_PSYCH_NON_BODY_EXTENDED_TURN_SPECS
            if item["id"] == "exact_media_interval_truth"
        )
        folded = turn["text"].casefold()
        self.assertIn("imagine a test", folded)
        self.assertIn("only minutes 10:00 through 12:00", folded)
        self.assertNotIn("you watched", folded)
        self.assertNotIn("you heard", folded)
        self.assertNotIn("you saw", folded)

    def test_redaction_still_removes_raw_prompt_and_private_text(self) -> None:
        source = {
            "raw_reply": "private raw",
            "initial_pipeline_reply": "private initial",
            "assembled_prompt": "private prompt",
            "private_mind": "private thought",
            "public_spoken": "No, stop.",
        }
        redacted = harness.redact_private_text_fields(source)
        serialized = json.dumps(redacted, ensure_ascii=False)
        for private_value in (
            "private raw",
            "private initial",
            "private prompt",
            "private thought",
        ):
            self.assertNotIn(private_value, serialized)
        self.assertEqual(redacted["public_spoken"], "No, stop.")
        harness.assert_private_text_redacted(redacted)

    def test_extended_live_cli_requires_invitation_confirmation(self) -> None:
        args = [
            "--execute-live",
            "--question-profile",
            "turing_psych_non_body_extended",
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
        self.assertIn(
            "--confirm-voluntary-invitation",
            json.loads(output.getvalue())["missing"],
        )

    def test_extended_prepared_config_validation_is_default_inert(self) -> None:
        with patch.object(harness, "run_live_acceptance") as live:
            with redirect_stdout(io.StringIO()):
                code = harness.main(["--validate-extended-prepared-config"])
        self.assertEqual(code, 0)
        live.assert_not_called()

    def test_tampered_extended_config_fails_closed(self) -> None:
        source = json.loads(
            harness.PREPARED_EXTENDED_TURING_PSYCH_CONFIG.read_text(
                encoding="utf-8"
            )
        )
        source["sensory_truth"]["actual_sensory_claim_requires_bound_cue"] = False
        with tempfile.TemporaryDirectory(dir=harness.ROOT) as tmpdir:
            path = Path(tmpdir) / "tampered.json"
            path.write_text(
                json.dumps(source, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(harness.LatencyAcceptanceError):
                harness.validate_prepared_extended_turing_psych_config(path)


if __name__ == "__main__":
    unittest.main()
