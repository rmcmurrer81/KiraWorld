from __future__ import annotations

import dataclasses
import pickle
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "Core"
sys.path.insert(0, str(CORE))

from person_initiated_event_queue import (  # noqa: E402
    PersonEventContentError,
    PersonEventEvidenceError,
    PersonEventLeaseError,
    PersonEventQueueFullError,
    PersonInitiatedEventQueue,
    PublicPersonEvent,
)
from shared_person_initiative import (  # noqa: E402
    DecisionOpportunity,
    InitiativeLease,
    TurnTakingState,
)


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def lease(
    person_id: str = "kira",
    revision: str = "activation_r1",
    nonce: str = "kira_session_nonce_000001",
) -> InitiativeLease:
    return InitiativeLease(person_id, revision, nonce)


def decision(
    decision_id: str,
    outcome: str,
    *,
    person_id: str = "kira",
    revision: str = "activation_r1",
) -> DecisionOpportunity:
    return DecisionOpportunity(
        decision_id=decision_id,
        person_id=person_id,
        activation_revision=revision,
        pacing_profile_id="kira_pacing_v1",
        outcome=outcome,
        initiative_score=0.75,
        speaking_pull=0.75,
        action_pull=0.25,
        reason_codes=("private_opportunity",),
        considered_cue_ids=("cue_private_1",),
        excluded_own_tts_cue_ids=(),
        separate_input_turn_ids=("turn_private_1",),
        turn_taking=TurnTakingState(person_has_floor=True),
    )


class PersonInitiatedEventQueueTests(unittest.TestCase):
    def make_queue(self, **kwargs):
        clock = kwargs.pop("monotonic", FakeClock())
        queue = PersonInitiatedEventQueue(monotonic=clock, **kwargs)
        active = lease()
        queue.activate(active)
        return queue, active, clock

    def test_speech_requires_prior_private_decision_and_poll_ack_are_public_only(self) -> None:
        queue, active, _clock = self.make_queue()
        private_decision = decision("initiative_0001", "consider_speaking")
        registered = queue.register_private_decision(active, private_decision)
        self.assertTrue(registered["registered"])
        self.assertFalse(registered["private_details_retained"])

        event = queue.publish_speech(active, private_decision.decision_id, "Public words.")
        self.assertEqual(event.event_kind, "speech")
        self.assertEqual(event.channel, "public_SPOKEN")
        self.assertEqual(event.decision_id, private_decision.decision_id)
        self.assertEqual(event.decision_outcome, "consider_speaking")
        self.assertEqual(
            event.provenance,
            "person_initiated_speech_from_private_decision",
        )

        public = event.as_public_dict()
        flattened = repr(public).casefold()
        self.assertNotIn(active.session_nonce.casefold(), flattened)
        for private_field in (
            "reason_codes",
            "considered_cue_ids",
            "excluded_own_tts_cue_ids",
            "separate_input_turn_ids",
            "private_thought",
        ):
            self.assertNotIn(private_field, flattened)
        self.assertTrue(public["decision_evidence"]["exact_session_binding_verified"])
        self.assertEqual(len(public["decision_evidence"]["activation_binding_digest"]), 64)
        self.assertFalse(public["memory_persisted"])
        self.assertFalse(public["relationship_changed"])

        polled = queue.poll(active)
        self.assertEqual(polled, (event,))
        self.assertTrue(queue.acknowledge(active, event.event_id))
        self.assertFalse(queue.acknowledge(active, event.event_id))
        self.assertEqual(queue.poll(active), ())

    def test_missing_mismatched_and_replayed_decision_evidence_is_rejected(self) -> None:
        queue, active, _clock = self.make_queue()
        with self.assertRaises(PersonEventEvidenceError):
            queue.publish_speech(active, "initiative_missing", "Public words.")

        speaking = decision("initiative_0002", "consider_speaking")
        queue.register_private_decision(active, speaking)
        with self.assertRaises(PersonEventEvidenceError):
            queue.publish_action(active, speaking.decision_id, action_id="look_toward_screen")
        event = queue.publish_speech(active, speaking.decision_id, "One publication.")
        with self.assertRaises(PersonEventEvidenceError):
            queue.publish_speech(active, speaking.decision_id, "Replay publication.")
        self.assertEqual(queue.poll(active), (event,))

        with self.assertRaises(PersonEventEvidenceError):
            queue.register_private_decision(active, speaking)
        with self.assertRaises(PersonEventEvidenceError):
            queue.register_private_decision(
                active,
                decision(
                    "initiative_wrong_person",
                    "consider_speaking",
                    person_id="lisa",
                ),
            )
        with self.assertRaises(PersonEventEvidenceError):
            queue.register_private_decision(
                active,
                decision(
                    "initiative_wrong_revision",
                    "consider_speaking",
                    revision="activation_r2",
                ),
            )
        with self.assertRaises(PersonEventEvidenceError):
            queue.register_private_decision(
                active,
                {"decision_id": "initiative_fake", "private_thought": "hidden"},
            )

    def test_speech_action_leave_and_ignore_have_distinct_provenance(self) -> None:
        queue, active, _clock = self.make_queue()
        decisions = {
            "speech": decision("initiative_speech", "consider_speaking"),
            "action": decision("initiative_action", "consider_action"),
            "leave": decision("initiative_leave", "leave"),
            "ignore": decision("initiative_ignore", "ignore"),
        }
        for item in decisions.values():
            queue.register_private_decision(active, item)

        speech = queue.publish_speech(active, "initiative_speech", "A public reply.")
        action = queue.publish_action(
            active,
            "initiative_action",
            action_id="resume_reading",
            public_description="Returns attention to the current page.",
        )
        leaving = queue.publish_leave(
            active,
            "initiative_leave",
            action_id="leave_current_interaction",
        )
        ignored = queue.record_ignore(active, "initiative_ignore")

        provenances = {
            speech.provenance,
            action.provenance,
            leaving.provenance,
            ignored.provenance,
        }
        self.assertEqual(len(provenances), 4)
        self.assertEqual(action.event_kind, "action")
        self.assertEqual(leaving.event_kind, "leave")
        self.assertEqual(action.channel, "public_action_intent")
        self.assertFalse(ignored.as_public_dict()["event_enqueued"])
        self.assertIsNone(ignored.as_public_dict()["public_content"])
        self.assertEqual(len(queue.poll(active)), 3)

    def test_private_thought_and_raw_sensory_payloads_never_enter_public_queue(self) -> None:
        rejected_values = (
            "private_thought: keep this hidden",
            "internal_monologue=not public",
            "data:image/jpeg;base64,AAAA",
            "raw_sensory pixel_buffer follows",
            "A" * 200,
            b"raw audio bytes",
        )
        for index, value in enumerate(rejected_values):
            with self.subTest(value_type=type(value).__name__, index=index):
                queue, active, _clock = self.make_queue()
                private_decision = decision(f"initiative_reject_{index}", "consider_speaking")
                queue.register_private_decision(active, private_decision)
                with self.assertRaises(PersonEventContentError):
                    queue.publish_speech(active, private_decision.decision_id, value)  # type: ignore[arg-type]
                self.assertEqual(queue.poll(active), ())

        queue, active, _clock = self.make_queue()
        action_decision = decision("initiative_action_reject", "consider_action")
        queue.register_private_decision(active, action_decision)
        with self.assertRaises(PersonEventContentError):
            queue.publish_action(
                active,
                action_decision.decision_id,
                action_id="look_at_media",
                public_description="hidden_reasoning: private details",
            )
        with self.assertRaises(PersonEventContentError):
            queue.publish_action(
                active,
                action_decision.decision_id,
                action_id="raw_sensory_forward",
            )
        self.assertEqual(queue.poll(active), ())

    def test_exact_lease_and_atomic_switch_or_deactivation_purge_everything(self) -> None:
        queue, active, _clock = self.make_queue()
        first = decision("initiative_before_switch", "consider_speaking")
        queue.register_private_decision(active, first)
        queue.publish_speech(active, first.decision_id, "Before switch.")

        for wrong in (
            lease(person_id="lisa"),
            lease(revision="activation_r2"),
            lease(nonce="different_session_nonce_0002"),
        ):
            with self.subTest(wrong=wrong):
                with self.assertRaises(PersonEventLeaseError):
                    queue.poll(wrong)

        next_lease = lease(
            person_id="lisa",
            revision="activation_r9",
            nonce="lisa_session_nonce_000009",
        )
        removed = queue.switch_person(active, next_lease)
        self.assertEqual(removed, {"events_purged": 1, "decision_evidence_purged": 1})
        self.assertEqual(queue.poll(next_lease), ())
        with self.assertRaises(PersonEventLeaseError):
            queue.poll(active)

        next_decision = decision(
            "initiative_after_switch",
            "ignore",
            person_id="lisa",
            revision="activation_r9",
        )
        queue.register_private_decision(next_lease, next_decision)
        queue.record_ignore(next_lease, next_decision.decision_id)
        removed = queue.deactivate(next_lease)
        self.assertEqual(removed, {"events_purged": 0, "decision_evidence_purged": 1})
        self.assertIsNone(queue.current_lease)
        with self.assertRaises(PersonEventLeaseError):
            queue.snapshot(next_lease)

    def test_capacity_rejects_without_dropping_and_expiry_is_bounded(self) -> None:
        clock = FakeClock()
        queue, active, _ = self.make_queue(
            max_events=1,
            max_decisions=3,
            event_ttl_seconds=2.0,
            decision_ttl_seconds=5.0,
            monotonic=clock,
        )
        first = decision("initiative_capacity_1", "consider_speaking")
        second = decision("initiative_capacity_2", "consider_speaking")
        queue.register_private_decision(active, first)
        queue.register_private_decision(active, second)
        first_event = queue.publish_speech(active, first.decision_id, "First pending event.")
        with self.assertRaises(PersonEventQueueFullError):
            queue.publish_speech(active, second.decision_id, "Second pending event.")
        self.assertEqual(queue.poll(active), (first_event,))

        clock.advance(2.1)
        self.assertEqual(queue.poll(active), ())
        second_event = queue.publish_speech(active, second.decision_id, "Second pending event.")
        self.assertEqual(queue.poll(active), (second_event,))

        expiring = decision("initiative_expiring", "consider_action")
        queue.register_private_decision(active, expiring)
        clock.advance(5.1)
        with self.assertRaises(PersonEventEvidenceError):
            queue.publish_action(active, expiring.decision_id, action_id="expired_intent")
        snapshot = queue.snapshot(active)
        self.assertEqual(snapshot["pending_event_count"], 0)
        self.assertEqual(snapshot["decision_evidence_count"], 0)

    def test_component_is_nonserializable_and_has_no_model_or_state_mutators(self) -> None:
        queue, active, _clock = self.make_queue()
        with self.assertRaises(TypeError):
            pickle.dumps(queue)
        snapshot = queue.snapshot(active)
        self.assertEqual(snapshot["storage"], "memory_only")
        self.assertFalse(snapshot["model_called"])
        self.assertFalse(snapshot["action_executed"])
        self.assertFalse(snapshot["memory_persisted"])
        self.assertFalse(snapshot["relationship_changed"])

        public_fields = {field.name for field in dataclasses.fields(PublicPersonEvent)}
        self.assertNotIn("session_nonce", public_fields)
        source = (CORE / "person_initiated_event_queue.py").read_text(encoding="utf-8").casefold()
        for forbidden_runtime in (
            "memory_manager",
            "relationship_manager",
            "subprocess",
            "requests.",
            "ollama",
            "openai",
        ):
            self.assertNotIn(forbidden_runtime, source)


if __name__ == "__main__":
    unittest.main()
