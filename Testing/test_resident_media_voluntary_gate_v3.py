from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from Core import resident_media_voluntary_gate_v3 as v3


def utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def choice(state: v3.VoluntaryMediaState, value: str, *, raw: str | None = None) -> dict:
    phase = state.next_required_phase
    return {
        "schema": "kira.resident_media_person_choice.v3",
        "session_id": state.session_id,
        "person_id": "kira",
        "phase": phase,
        "sequence": state.snapshot()["next_event_sequence"],
        "created_at_utc": utc(),
        "model_name": v3.EXACT_MODEL,
        "model_digest": v3.EXACT_DIGEST,
        "model_call_count": 1,
        "normal_model_route": True,
        "fallback_used": False,
        "prompt_sha256": sha(phase),
        "raw_reply": raw or {
            "YES": "Yes, I would like to see it.",
            "NO": "No, I do not want to.",
            "CONTINUE": "Continue to the next item.",
            "PAUSE": "Pause and wait.",
            "STOP": "Stop now.",
        }[value],
        "final_reply": raw or {
            "YES": "Yes, I would like to see it.",
            "NO": "No, I do not want to.",
            "CONTINUE": "Continue to the next item.",
            "PAUSE": "Pause and wait.",
            "STOP": "Stop now.",
        }[value],
        "transformations": [],
        "choice": value,
        "previous_event_sha256": state.snapshot()["last_event_sha256"],
    }


def presentation(state: v3.VoluntaryMediaState, auth: v3.PresentationAuthorization) -> dict:
    return {
        "schema": "kira.resident_media_presentation.v3",
        "session_id": state.session_id,
        "person_id": "kira",
        "stimulus_id": auth.stimulus_id,
        "ordinal": auth.ordinal,
        "sequence": state.snapshot()["next_event_sequence"],
        "authorization_nonce_sha256": auth.authorization_nonce_sha256,
        "started_at_utc": utc(),
        "ended_at_utc": utc(),
        "source_sha256": sha(auth.stimulus_id),
        "engineering_output_completed": True,
        "machine_visual_interpretation_created": True,
        "machine_audio_cue_created": False,
        "delivered_to_person_context": True,
        "person_attention_claimed": False,
        "person_saw_or_heard_claimed": False,
        "automatic_memory_created": False,
        "previous_event_sha256": state.snapshot()["last_event_sha256"],
    }


class ResidentMediaVoluntaryGateV3Tests(unittest.TestCase):
    def state(self) -> v3.VoluntaryMediaState:
        return v3.VoluntaryMediaState(session_id="session_" + "1" * 32)

    def accept(self, state: v3.VoluntaryMediaState, value: str, raw: str | None = None) -> str:
        record = choice(state, value, raw=raw)
        return state.accept_choice(record, prompt_sha256=record["prompt_sha256"])

    def test_no_presentation_before_clear_yes(self) -> None:
        with self.assertRaisesRegex(v3.ResidentMediaV3Error, "clear initial yes"):
            self.state().authorize_next(nonce_sha256=sha("n"))

    def test_decline_closes_before_any_media(self) -> None:
        state = self.state()
        self.accept(state, "NO")
        self.assertTrue(state.stopped)
        with self.assertRaises(v3.ResidentMediaV3Error):
            state.authorize_next(nonce_sha256=sha("n"))

    def test_stop_language_overrides_forged_continue(self) -> None:
        state = self.state()
        record = choice(state, "YES", raw="No. Stop now; I do not consent.")
        with self.assertRaisesRegex(v3.ResidentMediaV3Error, "cannot be overridden"):
            state.accept_choice(record, prompt_sha256=record["prompt_sha256"])

    def test_pause_language_overrides_forged_continue(self) -> None:
        state = self.state()
        record = choice(state, "YES", raw="Wait, not yet.")
        with self.assertRaisesRegex(v3.ResidentMediaV3Error, "pause language"):
            state.accept_choice(record, prompt_sha256=record["prompt_sha256"])

    def test_fallback_or_multiple_calls_cannot_decide(self) -> None:
        state = self.state()
        for field, value in (("fallback_used", True), ("model_call_count", 2)):
            record = choice(state, "YES")
            record[field] = value
            with self.assertRaises(v3.ResidentMediaV3Error):
                state.accept_choice(record, prompt_sha256=record["prompt_sha256"])

    def test_ambiguous_reply_cannot_be_self_labeled_yes_or_continue(self) -> None:
        state = self.state()
        record = choice(state, "YES", raw="Maybe. I am unsure.")
        with self.assertRaisesRegex(v3.ResidentMediaV3Error, "clear affirmative"):
            state.accept_choice(record, prompt_sha256=record["prompt_sha256"])

    def test_wrong_model_digest_rejected(self) -> None:
        state = self.state()
        record = choice(state, "YES")
        record["model_digest"] = "0" * 64
        with self.assertRaisesRegex(v3.ResidentMediaV3Error, "exact Qwen"):
            state.accept_choice(record, prompt_sha256=record["prompt_sha256"])

    def test_exact_order_and_one_use_authorization(self) -> None:
        state = self.state()
        self.accept(state, "YES")
        auth = state.authorize_next(nonce_sha256=sha("one"))
        self.assertEqual(auth.stimulus_id, v3.STIMULUS_ORDER[0])
        state.record_presentation(presentation(state, auth), auth)
        with self.assertRaises(v3.ResidentMediaV3Error):
            state.record_presentation(presentation(state, auth), auth)

    def test_person_experience_and_memory_claims_rejected(self) -> None:
        for field in ("person_attention_claimed", "person_saw_or_heard_claimed", "automatic_memory_created"):
            state = self.state()
            self.accept(state, "YES")
            auth = state.authorize_next(nonce_sha256=sha(field))
            record = presentation(state, auth)
            record[field] = True
            with self.assertRaisesRegex(v3.ResidentMediaV3Error, "cannot assert"):
                state.record_presentation(record, auth)

    def test_later_stop_prevents_next_stimulus(self) -> None:
        state = self.state()
        self.accept(state, "YES")
        auth = state.authorize_next(nonce_sha256=sha("one"))
        state.record_presentation(presentation(state, auth), auth)
        self.accept(state, "STOP")
        with self.assertRaises(v3.ResidentMediaV3Error):
            state.authorize_next(nonce_sha256=sha("two"))

    def test_cannot_finish_without_all_choices_and_stimuli(self) -> None:
        state = self.state()
        self.accept(state, "YES")
        with self.assertRaisesRegex(v3.ResidentMediaV3Error, "before all"):
            state.mark_engineering_finished()

    def test_full_truthful_sequence_still_needs_external_owner_ack(self) -> None:
        state = self.state()
        self.accept(state, "YES")
        for index, _ in enumerate(v3.STIMULUS_ORDER):
            auth = state.authorize_next(nonce_sha256=sha(f"nonce-{index}"))
            state.record_presentation(presentation(state, auth), auth)
            if index + 1 < len(v3.STIMULUS_ORDER):
                self.accept(state, "CONTINUE")
        state.mark_engineering_finished()
        snap = state.snapshot()
        self.assertFalse(snap["awake_owner_post_acknowledged"])
        self.assertTrue(snap["awake_owner_post_ack_requires_external_runner_evidence"])
        self.assertFalse(snap["selected_person_direct_seeing_or_hearing_proven"])

    def test_pause_can_only_resume_through_a_new_choice_event(self) -> None:
        state = self.state()
        self.accept(state, "YES")
        auth = state.authorize_next(nonce_sha256=sha("pause"))
        state.record_presentation(presentation(state, auth), auth)
        first_sequence = state.snapshot()["next_event_sequence"]
        self.accept(state, "PAUSE")
        with self.assertRaises(v3.ResidentMediaV3Error):
            state.authorize_next(nonce_sha256=sha("blocked"))
        self.assertEqual(state.snapshot()["next_event_sequence"], first_sequence + 1)
        self.accept(state, "CONTINUE")
        self.assertEqual(state.snapshot()["next_event_sequence"], first_sequence + 2)
        self.assertEqual(state.authorize_next(nonce_sha256=sha("resume")).ordinal, 1)

    def test_incomplete_or_reversed_presentation_does_not_advance(self) -> None:
        state = self.state()
        self.accept(state, "YES")
        auth = state.authorize_next(nonce_sha256=sha("output"))
        record = presentation(state, auth)
        record["engineering_output_completed"] = False
        with self.assertRaisesRegex(v3.ResidentMediaV3Error, "incomplete"):
            state.record_presentation(record, auth)

    def test_duplicate_keys_and_nonfinite_json_rejected(self) -> None:
        with self.assertRaisesRegex(v3.ResidentMediaV3Error, "duplicate"):
            v3.strict_json_loads(b'{"choice":"YES","choice":"STOP"}')
        with self.assertRaisesRegex(v3.ResidentMediaV3Error, "non-finite"):
            v3.strict_json_loads(b'{"x":NaN}')

    def test_append_only_writer_refuses_overwrite_and_reopens(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            writer = v3.AppendOnlyEventWriter(Path(temporary))
            result = writer.append(1, {"schema": "test", "value": 1})
            self.assertRegex(result["sha256"], r"^[0-9a-f]{64}$")
            with self.assertRaises(FileExistsError):
                writer.append(1, {"schema": "test", "value": 2})

    def test_static_contract_is_inert(self) -> None:
        result = v3.static_execution_requirements()
        self.assertFalse(result["live_execution_allowed"])
        self.assertTrue(result["fresh_independent_audit_required"])
        self.assertFalse(result["automatic_memory_or_preference"])


if __name__ == "__main__":
    unittest.main()
