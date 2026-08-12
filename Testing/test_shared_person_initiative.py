from __future__ import annotations

import pickle
import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "Core"
sys.path.insert(0, str(CORE))

from shared_person_initiative import (  # noqa: E402
    ActivityContext,
    EmotionSignal,
    InitiativeLeaseError,
    InitiativeSessionBoundaryError,
    InterruptionEvent,
    OpportunityInputs,
    PacingProfile,
    RecentBid,
    RecentTurn,
    RobertBusyEvidence,
    SensoryCueRef,
    SharedPersonInitiativeSession,
    UnfinishedThread,
)


def outgoing_profile() -> PacingProfile:
    return PacingProfile(
        profile_id="outgoing_measured_v1",
        initiative_threshold=0.42,
        initiative_bias=0.35,
        speech_preference=0.85,
        action_preference=0.25,
        boredom_weight=0.55,
        urgency_weight=0.7,
        unfinished_thread_weight=0.6,
        busy_deference_weight=0.45,
        activity_continuation_weight=0.2,
        minimum_bid_interval_seconds=18,
        deliberation_margin=0.02,
        urgent_pacing_override=0.8,
        leave_valence_threshold=-0.8,
        leave_arousal_threshold=0.75,
    )


def reserved_profile() -> PacingProfile:
    return PacingProfile(
        profile_id="reserved_slow_v1",
        initiative_threshold=0.78,
        initiative_bias=0.08,
        speech_preference=0.35,
        action_preference=0.45,
        boredom_weight=0.15,
        urgency_weight=0.45,
        unfinished_thread_weight=0.3,
        busy_deference_weight=0.8,
        activity_continuation_weight=0.7,
        minimum_bid_interval_seconds=150,
        deliberation_margin=0.03,
        urgent_pacing_override=0.92,
        leave_valence_threshold=-0.65,
        leave_arousal_threshold=0.6,
    )


def shared_facts(*, cues: tuple[SensoryCueRef, ...] | None = None) -> OpportunityInputs:
    return OpportunityInputs(
        sensory_cues=cues or (
            SensoryCueRef("cue_presence_1", "robert_live_input", "robert"),
        ),
        current_activity=ActivityContext("reading_session", engagement=0.45, interruptible=True),
        unfinished_thread=UnfinishedThread("thread_shared_1", salience=0.55),
        emotion=EmotionSignal("settled", valence=0.2, arousal=0.35),
        boredom=0.35,
        urgency=0.2,
        robert_busy=RobertBusyEvidence(),
    )


class SharedPersonInitiativeTests(unittest.TestCase):
    def activate(
        self,
        profile: PacingProfile | None = None,
        person_id: str = "kira",
        revision: str = "activation_r1",
    ):
        session = SharedPersonInitiativeSession(max_decisions=4)
        lease = session.activate(
            person_id,
            revision,
            pacing_profile=profile or outgoing_profile(),
            supervised=True,
            daytime=True,
        )
        return session, lease

    def test_same_facts_can_produce_different_opportunities_by_person_profile(self) -> None:
        facts = shared_facts()
        outgoing, outgoing_lease = self.activate(outgoing_profile())
        outgoing_decision = outgoing.evaluate(outgoing_lease, facts)

        reserved, reserved_lease = self.activate(reserved_profile())
        reserved_decision = reserved.evaluate(reserved_lease, facts)

        self.assertEqual(outgoing_decision.outcome, "consider_speaking")
        self.assertEqual(reserved_decision.outcome, "continue_activity")
        self.assertNotEqual(outgoing_decision.initiative_score, reserved_decision.initiative_score)
        self.assertNotEqual(
            outgoing_decision.pacing_profile_id,
            reserved_decision.pacing_profile_id,
        )

    def test_lease_is_exact_and_switch_or_deactivation_purges_every_state(self) -> None:
        session, lease = self.activate()
        session.record_interruption_event(
            lease,
            InterruptionEvent(
                "turn_event_1",
                "person_seeking_floor",
                "supervised_owner_input",
            ),
        )
        session.evaluate(lease, shared_facts())
        for bad_lease in (
            replace(lease, person_id="lisa"),
            replace(lease, activation_revision="activation_r2"),
            replace(lease, session_nonce=lease.session_nonce + "x"),
        ):
            with self.subTest(bad_lease=bad_lease):
                with self.assertRaises(InitiativeLeaseError):
                    session.snapshot(bad_lease)

        next_lease = session.switch_person(
            lease,
            "lisa",
            "activation_r9",
            pacing_profile=reserved_profile(),
            supervised=True,
            daytime=True,
        )
        fresh = session.snapshot(next_lease)
        self.assertEqual(fresh["decision_count"], 0)
        self.assertEqual(fresh["turn_event_count"], 0)
        self.assertFalse(fresh["turn_taking"]["person_seeking_floor"])
        with self.assertRaises(InitiativeLeaseError):
            session.snapshot(lease)

        removed = session.deactivate(next_lease)
        self.assertEqual(removed, {"decisions_purged": 0, "turn_events_purged": 0})
        self.assertIsNone(session.current_lease)
        with self.assertRaises(InitiativeLeaseError):
            session.snapshot(next_lease)

    def test_session_requires_explicit_supervised_daytime_scope(self) -> None:
        for supervised, daytime in ((False, True), (True, False), (False, False)):
            with self.subTest(supervised=supervised, daytime=daytime):
                with self.assertRaises(InitiativeSessionBoundaryError):
                    SharedPersonInitiativeSession().activate(
                        "kira",
                        "r1",
                        pacing_profile=outgoing_profile(),
                        supervised=supervised,
                        daytime=daytime,
                    )

    def test_own_tts_is_excluded_and_separate_input_remains_distinct(self) -> None:
        session, lease = self.activate()
        own_only = OpportunityInputs(
            sensory_cues=(
                SensoryCueRef("cue_tts_1", "own_tts_playback", "kira"),
            ),
            current_activity=ActivityContext("quiet_idle", 0.0, True),
            unfinished_thread=None,
            emotion=EmotionSignal("neutral", 0.0, 0.0),
            boredom=0.0,
            urgency=0.0,
            robert_busy=RobertBusyEvidence(),
            recent_turns=(RecentTurn("turn_tts_1", "kira", 1.0, "own_tts_playback"),),
        )
        ignored = session.evaluate(lease, own_only)
        self.assertEqual(ignored.outcome, "ignore")
        self.assertEqual(ignored.excluded_own_tts_cue_ids, ("cue_tts_1",))
        self.assertEqual(ignored.considered_cue_ids, ())
        self.assertEqual(ignored.separate_input_turn_ids, ())

        separate = replace(
            own_only,
            sensory_cues=(
                SensoryCueRef("cue_input_1", "robert_live_input", "robert"),
            ),
            recent_turns=(RecentTurn("turn_input_1", "robert", 1.0, "robert_live_input"),),
            boredom=0.5,
        )
        considered = session.evaluate(lease, separate)
        self.assertEqual(considered.considered_cue_ids, ("cue_input_1",))
        self.assertEqual(considered.separate_input_turn_ids, ("turn_input_1",))

    def test_robert_busy_camera_evidence_is_advisory_not_command_or_motive(self) -> None:
        session, lease = self.activate()
        cue = SensoryCueRef("cue_busy_1", "environment_derived")
        facts = replace(
            shared_facts(cues=(cue,)),
            robert_busy=RobertBusyEvidence(
                observed=True,
                confidence=0.95,
                provenance="camera_derived",
                cue_ids=(cue.cue_id,),
            ),
        )
        decision = session.evaluate(lease, facts).as_dict()
        self.assertIn("robert_busy_evidence_advisory_only", decision["reason_codes"])
        self.assertFalse(decision["robert_busy_is_command"])
        self.assertFalse(decision["robert_busy_proves_motive"])
        self.assertFalse(decision["camera_evidence_is_command"])
        self.assertFalse(decision["camera_evidence_proves_attention_or_motive"])
        self.assertFalse(decision["relationship_changed"])

    def test_interruption_and_floor_seeking_are_state_not_speech(self) -> None:
        session, lease = self.activate()
        interrupt = session.record_interruption_event(
            lease,
            InterruptionEvent(
                "interrupt_1",
                "robert_interrupting_person",
                "robert_live_input",
                "cue_interrupt_1",
            ),
        )
        self.assertTrue(interrupt["turn_taking"]["robert_interrupting_person"])
        decision = session.evaluate(lease, shared_facts())
        self.assertEqual(decision.outcome, "defer")
        self.assertFalse(decision.as_dict()["words_generated"])

        session.record_interruption_event(
            lease,
            InterruptionEvent(
                "interrupt_2",
                "robert_interruption_ended",
                "robert_live_input",
            ),
        )
        seeking = session.record_interruption_event(
            lease,
            InterruptionEvent(
                "floor_1",
                "person_seeking_floor",
                "supervised_owner_input",
            ),
        )
        self.assertTrue(seeking["turn_taking"]["person_seeking_floor"])
        self.assertFalse(seeking["turn_taking"]["person_has_floor"])

        before = session.snapshot(lease)["turn_taking"]
        rejected_feedback = session.record_interruption_event(
            lease,
            InterruptionEvent(
                "feedback_1",
                "robert_interrupting_person",
                "own_tts_playback",
            ),
        )
        self.assertFalse(rejected_feedback["accepted"])
        self.assertEqual(session.snapshot(lease)["turn_taking"], before)

        rejected_derived = session.record_interruption_event(
            lease,
            InterruptionEvent(
                "derived_interrupt_1",
                "robert_interrupting_person",
                "environment_derived",
            ),
        )
        self.assertFalse(rejected_derived["accepted"])
        self.assertEqual(
            rejected_derived["reason"],
            "direct_or_supervised_interruption_evidence_required",
        )
        self.assertEqual(session.snapshot(lease)["turn_taking"], before)

    def test_recent_bid_spacing_is_individual_and_has_urgent_override(self) -> None:
        facts = replace(
            shared_facts(),
            recent_bids=(RecentBid("bid_1", "kira", 30.0),),
        )
        outgoing, outgoing_lease = self.activate(outgoing_profile())
        reserved, reserved_lease = self.activate(reserved_profile())
        self.assertNotEqual(
            outgoing.evaluate(outgoing_lease, facts).outcome,
            reserved.evaluate(reserved_lease, facts).outcome,
        )
        urgent = replace(facts, urgency=1.0)
        self.assertNotEqual(reserved.evaluate(reserved_lease, urgent).outcome, "defer")

    def test_profile_values_are_bounded_and_no_universal_cooldown_exists(self) -> None:
        with self.assertRaises(ValueError):
            replace(outgoing_profile(), initiative_threshold=1.01)
        with self.assertRaises(ValueError):
            replace(outgoing_profile(), minimum_bid_interval_seconds=3600.01)
        self.assertNotEqual(
            outgoing_profile().minimum_bid_interval_seconds,
            reserved_profile().minimum_bid_interval_seconds,
        )

    def test_outputs_have_no_words_actions_memory_or_relationship_mutation(self) -> None:
        session, lease = self.activate()
        decision = session.evaluate(lease, shared_facts()).as_dict()
        for prohibited_key in ("text", "utterance", "speech", "message"):
            self.assertNotIn(prohibited_key, decision)
        self.assertFalse(decision["words_generated"])
        self.assertFalse(decision["action_executed"])
        self.assertFalse(decision["memory_persisted"])
        self.assertFalse(decision["relationship_changed"])
        with self.assertRaises(TypeError):
            pickle.dumps(session)

        source = (CORE / "shared_person_initiative.py").read_text(encoding="utf-8").lower()
        for canned_wording in (
            "how are you",
            "what are you up to",
            "i'm here",
            "hello robert",
            "good morning",
        ):
            self.assertNotIn(canned_wording, source)
        for forbidden_runtime in (
            "memory_manager",
            "relationship_manager",
            "subprocess",
            "requests.",
            "asyncio",
        ):
            self.assertNotIn(forbidden_runtime, source)


if __name__ == "__main__":
    unittest.main()
