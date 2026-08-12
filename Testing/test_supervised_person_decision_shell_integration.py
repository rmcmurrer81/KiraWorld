from __future__ import annotations

import json
import inspect
import threading
import unittest

from Core.person_initiated_event_queue import PersonInitiatedEventQueue
from Core.shared_person_initiative import (
    ActivityContext,
    EmotionSignal,
    InitiativeSessionBoundaryError,
    InterruptionEvent,
    OpportunityInputs,
    RecentTurn,
    RobertBusyEvidence,
    SensoryCueRef,
    SharedPersonInitiativeSession,
    UnfinishedThread,
)
from Core.supervised_person_decision import (
    DecisionActivationError,
    DecisionContextItem,
    RESULT_SCHEMA_VERSION,
    SupervisedPersonDecisionEngine,
)
from tools import kira_world_shell_server as shell


class FakeChoiceAdapter:
    def __init__(self, chooser):
        self.chooser = chooser
        self.requests = []

    def decide(self, request):
        self.requests.append(request)
        selection = self.chooser(request)
        choice = selection[0]
        spoken_text = selection[1] if len(selection) > 1 else None
        action_id = selection[2] if len(selection) > 2 else None
        action_description = selection[3] if len(selection) > 3 else None
        binding = request["exact_binding"]
        return {
            "schema_version": RESULT_SCHEMA_VERSION,
            "decision_id": binding["decision_id"],
            "person_id": binding["person_id"],
            "activation_revision": binding["activation_revision"],
            "pacing_profile_id": binding["pacing_profile_id"],
            "profile_revision": binding["profile_revision"],
            "context_id": binding["context_id"],
            "choice": choice,
            "confidence": 0.82,
            "spoken_text": spoken_text,
            "action_id": action_id,
            "action_description": action_description,
        }


def speaking_facts(
    *,
    cue_id: str = "derived_cue_0001",
    turn_id: str = "",
    busy: bool = False,
) -> OpportunityInputs:
    recent_turns = (
        RecentTurn(turn_id, "robert_owner", 0.1, "supervised_owner_input"),
    ) if turn_id else ()
    return OpportunityInputs(
        sensory_cues=(SensoryCueRef(cue_id, "environment_derived"),),
        current_activity=ActivityContext("quiet_reading", 0.1, True),
        unfinished_thread=UnfinishedThread("conversation_thread", 0.7),
        emotion=EmotionSignal("calm_interest", 0.25, 0.45),
        boredom=0.25,
        urgency=0.55,
        robert_busy=RobertBusyEvidence(
            observed=busy,
            confidence=0.75 if busy else 0.0,
            provenance="owner_status" if busy else "unknown_derived",
            cue_ids=(cue_id,) if busy else (),
        ),
        recent_turns=recent_turns,
    )


def action_facts() -> OpportunityInputs:
    return OpportunityInputs(
        sensory_cues=(SensoryCueRef("media_cue_0001", "environment_derived"),),
        current_activity=ActivityContext("source_bound_media", 0.0, True),
        unfinished_thread=None,
        emotion=EmotionSignal("media_interest", 0.2, 0.4),
        boredom=1.0,
        urgency=0.75,
        robert_busy=RobertBusyEvidence(),
    )


class SupervisedDecisionShellIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.saved = (
            shell.PERSON_INITIATIVE_SESSION,
            shell.PERSON_EVENT_QUEUE,
            shell.SUPERVISED_PERSON_DECISION_ENGINE,
            shell.PERSON_DECISION_ENGINE_OWNS_QUEUE,
            shell.PERSON_DECISION_ACTIVE_PROFILE,
            shell.PERSON_DECISION_SUPERVISED_DAYTIME_SCOPE,
            shell.SUPERVISED_PERSON_DECISIONS_FEATURE_ENABLED,
        )
        shell.PERSON_INITIATIVE_SESSION = SharedPersonInitiativeSession(max_decisions=64)
        shell.PERSON_EVENT_QUEUE = PersonInitiatedEventQueue(
            max_events=32,
            max_decisions=128,
            event_ttl_seconds=300.0,
            decision_ttl_seconds=300.0,
        )
        shell.SUPERVISED_PERSON_DECISION_ENGINE = SupervisedPersonDecisionEngine(
            shell.PERSON_EVENT_QUEUE
        )
        shell.PERSON_DECISION_ENGINE_OWNS_QUEUE = False
        shell.PERSON_DECISION_ACTIVE_PROFILE = None
        shell.PERSON_DECISION_SUPERVISED_DAYTIME_SCOPE = False
        shell.SUPERVISED_PERSON_DECISIONS_FEATURE_ENABLED = True

    def tearDown(self) -> None:
        try:
            shell.purge_person_initiative_runtime()
        finally:
            (
                shell.PERSON_INITIATIVE_SESSION,
                shell.PERSON_EVENT_QUEUE,
                shell.SUPERVISED_PERSON_DECISION_ENGINE,
                shell.PERSON_DECISION_ENGINE_OWNS_QUEUE,
                shell.PERSON_DECISION_ACTIVE_PROFILE,
                shell.PERSON_DECISION_SUPERVISED_DAYTIME_SCOPE,
                shell.SUPERVISED_PERSON_DECISIONS_FEATURE_ENABLED,
            ) = self.saved

    @staticmethod
    def state(person_id: str = "kira", revision: str = "shell_activation_1") -> dict:
        return {"active_candidate": person_id, "last_activation_at": revision}

    def activate(self, state: dict | None = None):
        exact_state = state or self.state()
        status = shell.activate_person_initiative_runtime(
            exact_state,
            supervised_decisions=True,
            daytime=True,
        )
        return exact_state, status, shell.current_person_initiative_lease(exact_state)

    def test_default_off_and_each_explicit_gate_are_required(self) -> None:
        state = self.state()
        shell.SUPERVISED_PERSON_DECISIONS_FEATURE_ENABLED = False
        status = shell.activate_person_initiative_runtime(
            state,
            supervised_decisions=True,
            daytime=True,
        )
        self.assertFalse(status["private_decision_bridge_connected"])
        with self.assertRaises(InitiativeSessionBoundaryError):
            shell.run_supervised_person_decision_once(
                state,
                speaking_facts(),
                FakeChoiceAdapter(lambda _: ("continue",)),
            )

        shell.SUPERVISED_PERSON_DECISIONS_FEATURE_ENABLED = True
        for supervised, daytime in ((False, True), (True, False)):
            status = shell.activate_person_initiative_runtime(
                state,
                supervised_decisions=supervised,
                daytime=daytime,
            )
            self.assertFalse(status["private_decision_bridge_connected"])

    def test_owner_enters_view_fake_choice_reaches_public_queue_only(self) -> None:
        state, status, lease = self.activate()
        adapter = FakeChoiceAdapter(lambda _: ("speak", "I noticed you came in."))
        receipt = shell.run_supervised_person_decision_once(
            state,
            speaking_facts(),
            adapter,
        )
        self.assertTrue(status["private_decision_bridge_connected"])
        self.assertFalse(status["model_generator_connected"])
        self.assertEqual("person_initiated_event_queue_only", receipt["public_delivery_route"])
        self.assertEqual(1, len(adapter.requests))
        events = shell.PERSON_EVENT_QUEUE.poll(lease)
        self.assertEqual(["I noticed you came in."], [event.spoken_text for event in events])
        encoded = json.dumps(receipt)
        self.assertNotIn(shell.KIRA_PROFILE.core_identity, encoded)
        self.assertNotIn("Current explicit emotion signal", encoded)
        self.assertFalse(receipt["private_profile_exposed"])
        self.assertFalse(receipt["private_context_exposed"])
        self.assertFalse(receipt["memory_persisted"])
        self.assertFalse(receipt["relationship_changed"])
        self.assertFalse(receipt["action_executed"])

    def test_second_move_is_bounded_and_new_owner_turn_resets_only_consecutive_bound(self) -> None:
        state, _, lease = self.activate()
        speak = FakeChoiceAdapter(lambda _: ("speak", "A voluntary public turn."))
        shell.run_supervised_person_decision_once(state, speaking_facts(cue_id="cue_a"), speak)
        shell.run_supervised_person_decision_once(state, speaking_facts(cue_id="cue_b"), speak)

        third = FakeChoiceAdapter(
            lambda request: (
                "continue",
            ) if "speak" not in request["allowed_choices"] else ("speak", "Unexpected."),
        )
        quiet = shell.run_supervised_person_decision_once(
            state,
            speaking_facts(cue_id="cue_c"),
            third,
        )
        self.assertEqual("continue", quiet["choice"])
        self.assertNotIn("speak", third.requests[0]["allowed_choices"])

        noted = shell.note_supervised_person_external_turn(
            state,
            "owner_turn_after_two_bids",
            accepted=True,
        )
        self.assertTrue(noted["registered"])
        fourth = FakeChoiceAdapter(lambda _: ("speak", "I can choose again after your turn."))
        shell.run_supervised_person_decision_once(
            state,
            speaking_facts(
                cue_id="cue_d",
                turn_id="owner_turn_after_two_bids",
            ),
            fourth,
        )
        self.assertEqual(3, len(shell.PERSON_EVENT_QUEUE.poll(lease)))
        snapshot = shell.SUPERVISED_PERSON_DECISION_ENGINE.snapshot(lease)
        self.assertEqual("owner_turn_after_two_bids", snapshot["last_external_turn_id"])
        self.assertFalse(snapshot["universal_cooldown_present"])

    def test_busy_evidence_is_advisory_context_not_a_motive_or_command(self) -> None:
        state, _, _ = self.activate()
        adapter = FakeChoiceAdapter(lambda request: ("continue",))
        receipt = shell.run_supervised_person_decision_once(
            state,
            speaking_facts(busy=True),
            adapter,
        )
        private_items = adapter.requests[0]["private_context"]["items"]
        busy = next(item for item in private_items if item["item_id"].startswith("busy_"))
        self.assertIn("does not prove motive", busy["text"])
        self.assertIn(receipt["choice"], {"continue", "ignore"})
        self.assertEqual((), shell.PERSON_EVENT_QUEUE.poll(shell.current_person_initiative_lease(state)))

    def test_media_choice_is_only_a_public_intent_and_exact_receipt_stays_private(self) -> None:
        state, _, lease = self.activate(self.state("lisa", "shell_media_1"))
        media_context = DecisionContextItem(
            item_id="media_receipt_page_003",
            channel="factual_runtime_truth",
            text=(
                "Exact source-bound receipt: opaque media id media_42; page 3 was "
                "presented; the publication was not completed."
            ),
            certainty=1.0,
            source_ref_ids=("media_receipt_42",),
        )
        adapter = FakeChoiceAdapter(
            lambda _: (
                "action",
                None,
                "request_pause_current_media",
                "Request that the current exact media session pause.",
            )
        )
        receipt = shell.run_supervised_person_decision_once(
            state,
            action_facts(),
            adapter,
            extra_context_items=(media_context,),
        )
        self.assertEqual("action", receipt["choice"])
        self.assertFalse(receipt["action_executed"])
        event = shell.PERSON_EVENT_QUEUE.poll(lease)[0]
        self.assertEqual("request_pause_current_media", event.action_id)
        self.assertFalse(event.as_public_dict()["action_executed"])
        self.assertNotIn("page 3 was presented", json.dumps(receipt))
        self.assertEqual(
            "pending_live_media_executor_acceptance",
            receipt["real_self_directed_media_acceptance"],
        )

    def test_turn_state_supports_floor_seeking_but_real_overlap_remains_pending(self) -> None:
        state, _, lease = self.activate()
        recorded = shell.PERSON_INITIATIVE_SESSION.record_interruption_event(
            lease,
            InterruptionEvent(
                "person_floor_request_1",
                "person_seeking_floor",
                "private_person_decision",
            ),
        )
        self.assertTrue(recorded["accepted"])
        adapter = FakeChoiceAdapter(lambda _: ("speak", "May I say something?"))
        receipt = shell.run_supervised_person_decision_once(
            state,
            speaking_facts(cue_id="separate_owner_audio_1"),
            adapter,
        )
        self.assertEqual("speak", receipt["choice"])
        self.assertEqual(
            "pending_echo_aware_live_device_acceptance",
            receipt["real_overlap_interruption_acceptance"],
        )
        self.assertFalse(receipt["full_duplex_echo_subtraction_accepted"])

    def test_distinct_authored_profiles_are_hash_bound_without_canned_speech(self) -> None:
        kira = shell.supervised_person_decision_profile("kira")
        lisa = shell.supervised_person_decision_profile("lisa")
        self.assertNotEqual(kira.profile_revision, lisa.profile_revision)
        self.assertNotEqual(kira.pacing_profile_id, lisa.pacing_profile_id)
        self.assertNotEqual(kira.decision_style_facts, lisa.decision_style_facts)
        self.assertIn(shell.KIRA_PROFILE.core_identity, kira.decision_style_facts)
        self.assertIn(shell.LISA_PROFILE.core_identity, lisa.decision_style_facts)
        self.assertFalse(any("Robert:" in fact for fact in kira.decision_style_facts))

        same_scenario = OpportunityInputs(
            sensory_cues=(SensoryCueRef("same_scenario_cue", "environment_derived"),),
            current_activity=ActivityContext("same_quiet_activity", 0.1, True),
            unfinished_thread=UnfinishedThread("same_thread", 0.7),
            emotion=EmotionSignal("same_interest", 0.2, 0.4),
            boredom=0.0,
            urgency=0.55,
            robert_busy=RobertBusyEvidence(),
        )

        def profile_driven_choice(request):
            facts = request["private_profile"]["decision_style_facts"]
            # The fake applies one content rule to either profile. It does not
            # branch on person ID or supply canned fallback words.
            return (
                ("speak", "A profile-derived test choice.")
                if "observe first" in facts
                else ("continue",)
            )

        kira_state, _, kira_lease = self.activate(self.state("kira", "same_case_kira"))
        kira_adapter = FakeChoiceAdapter(profile_driven_choice)
        kira_receipt = shell.run_supervised_person_decision_once(
            kira_state,
            same_scenario,
            kira_adapter,
        )
        self.assertEqual("speak", kira_receipt["choice"])
        self.assertEqual(1, len(shell.PERSON_EVENT_QUEUE.poll(kira_lease)))

        lisa_state, _, lisa_lease = self.activate(self.state("lisa", "same_case_lisa"))
        lisa_adapter = FakeChoiceAdapter(profile_driven_choice)
        lisa_receipt = shell.run_supervised_person_decision_once(
            lisa_state,
            same_scenario,
            lisa_adapter,
        )
        self.assertEqual("continue", lisa_receipt["choice"])
        self.assertEqual((), shell.PERSON_EVENT_QUEUE.poll(lisa_lease))
        self.assertNotEqual(
            kira_adapter.requests[0]["private_profile"]["profile_revision"],
            lisa_adapter.requests[0]["private_profile"]["profile_revision"],
        )

    def test_atomic_switch_purges_old_event_and_rejects_in_flight_result(self) -> None:
        state, _, old_lease = self.activate()
        started = threading.Event()
        release = threading.Event()
        failures = []

        class BlockingAdapter:
            def decide(self, request):
                started.set()
                release.wait(2.0)
                binding = request["exact_binding"]
                return {
                    "schema_version": RESULT_SCHEMA_VERSION,
                    "decision_id": binding["decision_id"],
                    "person_id": binding["person_id"],
                    "activation_revision": binding["activation_revision"],
                    "pacing_profile_id": binding["pacing_profile_id"],
                    "profile_revision": binding["profile_revision"],
                    "context_id": binding["context_id"],
                    "choice": "speak",
                    "confidence": 0.8,
                    "spoken_text": "These stale words must not publish.",
                    "action_id": None,
                    "action_description": None,
                }

        def worker():
            try:
                shell.run_supervised_person_decision_once(
                    state,
                    speaking_facts(),
                    BlockingAdapter(),
                )
            except Exception as exc:  # The exact stale-lease failure is asserted below.
                failures.append(exc)

        thread = threading.Thread(target=worker)
        thread.start()
        self.assertTrue(started.wait(1.0))
        new_state = self.state("lisa", "shell_activation_2")
        _, _, new_lease = self.activate(new_state)
        release.set()
        thread.join(2.0)
        self.assertFalse(thread.is_alive())
        self.assertTrue(any(isinstance(exc, DecisionActivationError) for exc in failures))
        self.assertEqual((), shell.PERSON_EVENT_QUEUE.poll(new_lease))
        with self.assertRaises(Exception):
            shell.PERSON_EVENT_QUEUE.poll(old_lease)

    def test_deactivate_purges_engine_counters_and_shutdown_uses_same_hook(self) -> None:
        state, _, lease = self.activate()
        shell.run_supervised_person_decision_once(
            state,
            speaking_facts(),
            FakeChoiceAdapter(lambda _: ("speak", "One bounded event.")),
        )
        removed = shell.purge_person_initiative_runtime()
        self.assertGreaterEqual(removed["person_events_purged"], 1)
        self.assertGreaterEqual(removed["supervised_decision_ids_purged"], 1)
        self.assertIsNone(shell.PERSON_INITIATIVE_SESSION.current_lease)
        self.assertFalse(shell.PERSON_DECISION_ENGINE_OWNS_QUEUE)
        with self.assertRaises(DecisionActivationError):
            shell.SUPERVISED_PERSON_DECISION_ENGINE.snapshot(lease)

    def test_chat_registers_exact_external_turn_only_after_public_log_append(self) -> None:
        source = inspect.getsource(shell.Handler.do_POST)
        turn_created = source.index(
            'owner_external_turn_id = f"owner_chat_{uuid.uuid4().hex}"'
        )
        turn_logged = source.index('"turn_id": owner_external_turn_id', turn_created)
        turn_noted = source.index(
            "note_supervised_person_external_turn(",
            turn_logged,
        )
        self.assertLess(turn_created, turn_logged)
        self.assertLess(turn_logged, turn_noted)
        self.assertIn("accepted=True", source[turn_noted:turn_noted + 240])

    def test_feasible_owner_case_coverage_and_live_boundaries_are_truthful(self) -> None:
        status = shell.person_initiative_public_status({})
        feasible_fake_cases = {
            "01_owner_enters_view",
            "02_no_owner_reply_second_move",
            "03_owner_busy",
            "06_person_interrupts_owner_floor_state",
            "07_different_people_same_scenario",
            "08_no_automatic_mutation",
            "09_media_experience_truth_context",
            "10_person_switch_isolation",
        }
        self.assertEqual(8, len(feasible_fake_cases))
        self.assertEqual(
            "pending_echo_aware_live_device_acceptance",
            status["real_overlap_interruption_acceptance"],
        )
        self.assertEqual(
            "pending_live_media_executor_acceptance",
            status["real_self_directed_media_acceptance"],
        )
        self.assertFalse(status["model_generator_connected"])


if __name__ == "__main__":
    unittest.main()
