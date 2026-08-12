from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

from Core.candidate_movement_intents import (
    extract_candidate_owned_movement_intents,
    movement_intent_state_path,
    record_candidate_owned_movement_intents,
)
from tools import kira_world_shell_server as shell


class CandidateOwnedMovementIntentTests(unittest.TestCase):
    def test_kathryn_stage_directions_are_recorded_but_not_spoken(self) -> None:
        raw = (
            "*raises an eyebrow* Ah, how... fascinating. "
            "What exactly did you have in mind? *leans forward slightly*"
        )
        result = extract_candidate_owned_movement_intents(raw)
        self.assertEqual(
            [item["action"] for item in result["movement_intents"]],
            ["raise_eyebrow", "lean_forward"],
        )
        self.assertEqual(
            result["spoken_text"],
            "Ah, how... fascinating. What exactly did you have in mind?",
        )
        self.assertNotIn("eyebrow", result["spoken_text"].lower())
        self.assertNotIn("leans", result["spoken_text"].lower())

    def test_smirk_is_future_body_expression_not_audio(self) -> None:
        result = extract_candidate_owned_movement_intents(
            "*smirks slightly* That's an interesting question."
        )
        self.assertEqual(result["spoken_text"], "That's an interesting question.")
        self.assertEqual(result["movement_intents"][0]["action"], "smirk")
        self.assertEqual(result["movement_intents"][0]["modifiers"], ["slightly"])

    def test_ordinary_markdown_emphasis_is_preserved(self) -> None:
        raw = "That is *very* different from what I chose."
        result = extract_candidate_owned_movement_intents(raw)
        self.assertEqual(result["spoken_text"], raw)
        self.assertEqual(result["movement_intents"], [])

    def test_parser_has_no_user_message_input(self) -> None:
        parameters = inspect.signature(extract_candidate_owned_movement_intents).parameters
        self.assertEqual(list(parameters), ["candidate_reply"])

    def test_candidate_scoped_record_never_dispatches_or_claims_completion(self) -> None:
        parsed = extract_candidate_owned_movement_intents("*waves gently* Hello.")
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            state_dir = root / "state"
            audit_path = root / "audit.jsonl"
            result = record_candidate_owned_movement_intents(
                "kathryn_merteuil",
                "Kathryn Merteuil",
                parsed["movement_intents"],
                source_turn_id="turn-1",
                state_dir=state_dir,
                audit_path=audit_path,
            )
            payload = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))
            record = payload["records"][0]
            self.assertTrue(record["ownership"]["authored_by_candidate"])
            self.assertFalse(record["ownership"]["user_message_parsed_as_motor_command"])
            self.assertEqual(record["execution"]["status"], "recorded_for_future_body")
            self.assertFalse(record["execution"]["dispatched_to_live_body"])
            self.assertFalse(record["execution"]["physical_completion_claimed"])
            self.assertTrue(record["execution"]["requires_candidate_choice_at_execution"])

            second = record_candidate_owned_movement_intents(
                "kathryn_merteuil",
                "Kathryn Merteuil",
                parsed["movement_intents"],
                source_turn_id="turn-1",
                state_dir=state_dir,
                audit_path=audit_path,
            )
            self.assertEqual(second["recorded_count"], 0)
            self.assertEqual(second["deduplicated_count"], 1)

    def test_people_have_separate_movement_ledgers(self) -> None:
        parsed = extract_candidate_owned_movement_intents("*smiles* Hello.")
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            audit_path = Path(tmpdir) / "audit.jsonl"
            for candidate in ("kira", "elsa"):
                record_candidate_owned_movement_intents(
                    candidate,
                    candidate.title(),
                    parsed["movement_intents"],
                    source_turn_id=f"turn-{candidate}",
                    state_dir=state_dir,
                    audit_path=audit_path,
                )
            self.assertTrue(movement_intent_state_path("kira", state_dir).exists())
            self.assertTrue(movement_intent_state_path("elsa", state_dir).exists())
            self.assertNotEqual(
                movement_intent_state_path("kira", state_dir),
                movement_intent_state_path("elsa", state_dir),
            )

    def test_voice_boundary_removes_recognized_stage_direction(self) -> None:
        spoken, audit = shell._live_spoken_only_payload(
            "*raises an eyebrow* What exactly did you have in mind? *leans forward slightly*"
        )
        self.assertEqual(spoken, "What exactly did you have in mind?")
        self.assertEqual(audit["removed_candidate_movement_stage_directions"], 2)

    def test_logged_quoted_reply_keeps_only_words_and_records_narrated_actions(self) -> None:
        raw = (
            '"I\'m glad we can finally work together in person," Kira said, smiling at '
            "Robert's invitation. She stood up from her chair and walked towards the living "
            "room with him, feeling the warmth of the evening and the comfort of their private space."
        )
        result = extract_candidate_owned_movement_intents(raw)
        self.assertEqual(
            result["spoken_text"],
            "I'm glad we can finally work together in person.",
        )
        self.assertEqual(
            [item["action"] for item in result["movement_intents"]],
            ["smile", "stand", "walk_or_step"],
        )
        self.assertEqual(result["recognized_narration_count"], 1)
        self.assertNotIn("Kira said", result["spoken_text"])
        self.assertNotIn("stood", result["spoken_text"])

    def test_voice_boundary_does_not_speak_logged_third_person_narration(self) -> None:
        raw = (
            '"I\'m glad we can finally work together in person," Kira said, smiling. '
            "She stood up and walked towards the living room."
        )
        spoken, audit = shell._live_spoken_only_payload(raw)
        self.assertEqual(spoken, "I'm glad we can finally work together in person.")
        self.assertEqual(audit["removed_candidate_movement_stage_directions"], 1)
        self.assertNotIn("Kira said", spoken)
        self.assertNotIn("walked", spoken)

    def test_logged_narration_is_labeled_separately_from_asterisk_stage_text(self) -> None:
        parsed = extract_candidate_owned_movement_intents(
            '"I would like that," Kira said, smiling. She stood and walked toward the couch.'
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = record_candidate_owned_movement_intents(
                "kira",
                "Kira",
                parsed["movement_intents"],
                source_turn_id="narrated-turn",
                state_dir=root / "state",
                audit_path=root / "audit.jsonl",
            )
            payload = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))
            self.assertTrue(payload["records"])
            for record in payload["records"]:
                self.assertEqual(
                    record["source"]["kind"],
                    "candidate_generated_third_person_narration",
                )
                self.assertEqual(
                    record["source"]["style"],
                    "third_person_narration_after_quoted_kira_speech",
                )

    def test_ordinary_quote_and_other_person_attribution_are_preserved(self) -> None:
        ordinary = 'I called the chapter "A Quiet Evening" because it fits.'
        attributed_to_robert = '"I agree," Robert said.'
        self.assertEqual(
            extract_candidate_owned_movement_intents(ordinary)["spoken_text"],
            ordinary,
        )
        self.assertEqual(
            extract_candidate_owned_movement_intents(attributed_to_robert)["spoken_text"],
            attributed_to_robert,
        )

    def test_roberts_request_is_not_enough_for_motor_or_future_intent(self) -> None:
        user_text = "Raise your hand now."
        candidate_reply = "I don't want to do that right now."
        parsed = extract_candidate_owned_movement_intents(candidate_reply)
        self.assertEqual(parsed["movement_intents"], [])
        self.assertIsNone(shell._infer_kira_spoken_self_body_intent(user_text, candidate_reply))

    def test_voluntary_gesture_is_stored_only_and_not_live_motor_intent(self) -> None:
        candidate_reply = "*waves* I'm glad to see you."
        parsed = extract_candidate_owned_movement_intents(candidate_reply)
        self.assertEqual(parsed["movement_intents"][0]["action"], "wave")
        # The live body bridge understands only explicit spoken route choices;
        # the private stage record is never fed to it.
        self.assertIsNone(
            shell._infer_kira_spoken_self_body_intent(
                "Wave at me.",
                parsed["spoken_text"],
            )
        )

    def test_excluded_couch_alternative_does_not_route_kira_to_couch(self) -> None:
        reply = (
            "You can use the bathroom, but I'll just head downstairs to my bedroom "
            "for some quiet time instead of sitting on the couch right now."
        )
        self.assertIsNone(
            shell._infer_kira_spoken_self_body_intent(
                "I am fine with that; may I use your bathroom?",
                reply,
            )
        )


if __name__ == "__main__":
    unittest.main()
