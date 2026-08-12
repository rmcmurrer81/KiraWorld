from __future__ import annotations

import inspect
import unittest
from unittest.mock import patch

from Core.person_initiated_event_queue import PersonInitiatedEventQueue
from Core.shared_person_initiative import (
    ActivityContext,
    EmotionSignal,
    InitiativeSessionBoundaryError,
    OpportunityInputs,
    RobertBusyEvidence,
    SensoryCueRef,
    SharedPersonInitiativeSession,
    UnfinishedThread,
)
from Core.supervised_person_decision import (
    DecisionAdapterError,
    RESULT_SCHEMA_VERSION,
    SupervisedPersonDecisionEngine,
)
from tools import kira_world_shell_server as shell


class BoundFakeAdapter:
    def __init__(self, choice: str, *, public_text: str | None = None) -> None:
        self.choice = choice
        self.public_text = public_text
        self.requests: list[dict] = []

    def decide(self, request):
        self.requests.append(request)
        binding = request["exact_binding"]
        return {
            "schema_version": RESULT_SCHEMA_VERSION,
            "decision_id": binding["decision_id"],
            "person_id": binding["person_id"],
            "activation_revision": binding["activation_revision"],
            "pacing_profile_id": binding["pacing_profile_id"],
            "profile_revision": binding["profile_revision"],
            "context_id": binding["context_id"],
            "choice": self.choice,
            "confidence": 0.8,
            "spoken_text": self.public_text if self.choice == "speak" else None,
            "action_id": None,
            "action_description": None,
        }


def speaking_opportunity(cue_id: str) -> OpportunityInputs:
    return OpportunityInputs(
        sensory_cues=(SensoryCueRef(cue_id, "environment_derived"),),
        current_activity=ActivityContext("quiet_reading", 0.1, True),
        unfinished_thread=UnfinishedThread("unfinished_public_conversation", 0.7),
        emotion=EmotionSignal("calm_interest", 0.25, 0.45),
        boredom=0.25,
        urgency=0.55,
        robert_busy=RobertBusyEvidence(),
    )


class TextVoiceDecisionHostIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.saved = (
            shell.PERSON_INITIATIVE_SESSION,
            shell.PERSON_EVENT_QUEUE,
            shell.SUPERVISED_PERSON_DECISION_ENGINE,
            shell.PERSON_DECISION_ENGINE_OWNS_QUEUE,
            shell.PERSON_DECISION_ACTIVE_PROFILE,
            shell.PERSON_DECISION_SUPERVISED_DAYTIME_SCOPE,
            shell.SUPERVISED_PERSON_DECISIONS_FEATURE_ENABLED,
            shell.TEXT_VOICE_SUPERVISED_PERSON_DECISIONS_FEATURE_ENABLED,
            shell.TEXT_ONLY_CHAT_MODE,
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
        shell.SUPERVISED_PERSON_DECISIONS_FEATURE_ENABLED = False
        shell.TEXT_VOICE_SUPERVISED_PERSON_DECISIONS_FEATURE_ENABLED = True
        shell.TEXT_ONLY_CHAT_MODE = True

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
                shell.TEXT_VOICE_SUPERVISED_PERSON_DECISIONS_FEATURE_ENABLED,
                shell.TEXT_ONLY_CHAT_MODE,
            ) = self.saved

    @staticmethod
    def state(person_id: str, revision: str) -> dict:
        return {
            "active_candidate": person_id,
            "last_activation_at": revision,
        }

    def configured_activate(self, state: dict):
        scope = shell.supervised_person_decision_activation_scope({})
        status = shell.activate_person_initiative_runtime(
            state,
            supervised_decisions=bool(scope["supervised_decisions"]),
            daytime=bool(scope["daytime"]),
        )
        return scope, status, shell.current_person_initiative_lease(state)

    def test_absent_flag_preserves_exact_legacy_default(self) -> None:
        shell.TEXT_VOICE_SUPERVISED_PERSON_DECISIONS_FEATURE_ENABLED = False
        scope = shell.supervised_person_decision_activation_scope({})
        self.assertEqual("legacy_default_off", scope["gate_source"])
        self.assertFalse(scope["supervised_decisions"])
        self.assertFalse(scope["daytime"])

        state = self.state("kira", "text_voice_legacy_01")
        status = shell.activate_person_initiative_runtime(
            state,
            supervised_decisions=False,
            daytime=False,
        )
        self.assertFalse(status["private_decision_bridge_connected"])
        self.assertFalse(shell.PERSON_DECISION_ENGINE_OWNS_QUEUE)
        with self.assertRaises(InitiativeSessionBoundaryError):
            shell.run_supervised_person_decision_once(
                state,
                speaking_opportunity("legacy_derived_cue"),
                BoundFakeAdapter("continue"),
            )

    def test_text_voice_flag_does_not_change_world_shell(self) -> None:
        shell.TEXT_ONLY_CHAT_MODE = False
        scope = shell.supervised_person_decision_activation_scope({})
        self.assertEqual("legacy_default_off", scope["gate_source"])
        self.assertFalse(scope["text_voice_process_configured"])
        self.assertFalse(scope["supervised_decisions"])
        self.assertFalse(scope["daytime"])

    def test_process_flag_binds_every_selected_person_to_an_exact_fresh_lease(self) -> None:
        previous_lease = None
        people = (
            ("kira", "text_voice_selected_kira"),
            ("lisa", "text_voice_selected_lisa"),
            ("future_person_01", "text_voice_selected_future"),
        )
        with patch.object(shell, "temporary_ai_profile_for", return_value={}):
            for person_id, revision in people:
                scope, status, lease = self.configured_activate(
                    self.state(person_id, revision)
                )
                self.assertEqual("text_voice_process_config", scope["gate_source"])
                self.assertTrue(scope["text_voice_process_configured"])
                self.assertTrue(status["private_decision_bridge_connected"])
                self.assertTrue(status["text_voice_process_configured"])
                self.assertFalse(status["model_generator_connected"])
                self.assertFalse(status["live_model_adapter_connected"])
                self.assertEqual(person_id, lease.person_id)
                self.assertEqual(person_id, shell.PERSON_DECISION_ACTIVE_PROFILE.person_id)
                self.assertEqual((), shell.PERSON_EVENT_QUEUE.poll(lease))
                if previous_lease is not None:
                    with self.assertRaises(Exception):
                        shell.PERSON_EVENT_QUEUE.poll(previous_lease)
                previous_lease = lease

    def test_configured_bridge_retains_natural_public_or_quiet_choices(self) -> None:
        state = self.state("kira", "text_voice_choices_01")
        _, _, lease = self.configured_activate(state)

        speak = BoundFakeAdapter("speak", public_text="I want to say something in my own words.")
        spoken_receipt = shell.run_supervised_person_decision_once(
            state,
            speaking_opportunity("choice_cue_speak"),
            speak,
        )
        self.assertEqual({"continue", "ignore", "speak"}, set(speak.requests[0]["allowed_choices"]))
        self.assertEqual("speak", spoken_receipt["choice"])
        self.assertFalse(spoken_receipt["memory_persisted"])
        self.assertFalse(spoken_receipt["relationship_changed"])
        self.assertFalse(spoken_receipt["action_executed"])

        ignore = BoundFakeAdapter("ignore")
        ignored_receipt = shell.run_supervised_person_decision_once(
            state,
            speaking_opportunity("choice_cue_ignore"),
            ignore,
        )
        self.assertEqual("ignore", ignored_receipt["choice"])
        self.assertEqual("person_chose_ignore", ignored_receipt["quiet_reason"])
        self.assertEqual(1, len(shell.PERSON_EVENT_QUEUE.poll(lease)))

    def test_adapter_failure_emits_no_canned_or_crisis_substitute(self) -> None:
        state = self.state("kira", "text_voice_failure_01")
        _, _, lease = self.configured_activate(state)

        class FailingAdapter:
            @staticmethod
            def decide(_request):
                raise RuntimeError("bounded mock failure")

        with self.assertRaises(DecisionAdapterError) as caught:
            shell.run_supervised_person_decision_once(
                state,
                speaking_opportunity("failure_derived_cue"),
                FailingAdapter(),
            )
        self.assertIn("failed once", str(caught.exception))
        self.assertEqual((), shell.PERSON_EVENT_QUEUE.poll(lease))

    def test_scope_reports_no_scheduler_model_or_external_action(self) -> None:
        scope = shell.supervised_person_decision_activation_scope({})
        self.assertFalse(scope["live_model_adapter_connected"])
        self.assertFalse(scope["recurring_scheduler_connected"])
        source = shell.run_supervised_person_decision_once.__doc__ or ""
        self.assertIn("not a timer", source)

    def test_normal_activate_handler_uses_config_scope_for_both_person_lanes(self) -> None:
        source = inspect.getsource(shell.Handler.do_POST)
        activate_start = source.index('if path == "/api/activate":')
        activate_end = source.index('if path == "/api/deactivate":', activate_start)
        activate_source = source[activate_start:activate_end]
        scope_call = activate_source.index(
            "supervised_person_decision_activation_scope("
        )
        self.assertGreaterEqual(scope_call, 0)
        self.assertEqual(
            2,
            activate_source.count(
                'decision_activation_scope["supervised_decisions"]'
            ),
        )
        self.assertEqual(
            2,
            activate_source.count('decision_activation_scope["daytime"]'),
        )
        self.assertNotIn(
            b"KIRA_TEXT_VOICE_ENABLE_SUPERVISED_PERSON_DECISIONS",
            shell.html_shell(),
        )


if __name__ == "__main__":
    unittest.main()
