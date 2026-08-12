from __future__ import annotations

import json
import pickle
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO

from Core.person_initiated_event_queue import PersonInitiatedEventQueue
from Core.shared_person_initiative import (
    DecisionOpportunity,
    InitiativeLease,
    TurnTakingState,
)
from Core.supervised_person_decision import (
    DecisionActivationError,
    DecisionAdapterError,
    DecisionBindingError,
    DecisionContextItem,
    DecisionLimitError,
    DecisionSchemaError,
    ExactDecisionContext,
    PersonDecisionProfile,
    RESULT_SCHEMA_VERSION,
    SupervisedPersonDecisionEngine,
)
from tools.run_supervised_person_decision_acceptance import (
    build_inert_acceptance_plan,
    main as acceptance_main,
)


def lease(person: str = "kira", revision: str = "activation_1") -> InitiativeLease:
    return InitiativeLease(person, revision, (person + "_lease_nonce_").ljust(40, "x"))


def profile(
    person: str = "kira",
    pacing: str = "person_pacing_kira",
    **changes,
) -> PersonDecisionProfile:
    values = {
        "person_id": person,
        "pacing_profile_id": pacing,
        "profile_revision": f"{person}_profile_r1",
        "decision_style_facts": (
            f"{person} decides in an individual, context-sensitive way.",
            "Silence, continuing, refusing, and leaving remain valid choices.",
        ),
        "allowed_action_ids": (
            "continue_reading",
            "pause_media",
            "leave_conversation",
        ),
        "max_model_calls_per_activation": 16,
        "max_public_events_per_activation": 8,
        "max_consecutive_public_events_without_external_input": 2,
    }
    values.update(changes)
    return PersonDecisionProfile(**values)


def opportunity(
    person: str = "kira",
    revision: str = "activation_1",
    pacing: str = "person_pacing_kira",
    outcome: str = "consider_speaking",
    number: int = 1,
) -> DecisionOpportunity:
    return DecisionOpportunity(
        decision_id=f"initiative_{number:04d}",
        person_id=person,
        activation_revision=revision,
        pacing_profile_id=pacing,
        outcome=outcome,
        initiative_score=0.77,
        speaking_pull=0.81,
        action_pull=0.35,
        reason_codes=("separate_input_available", "speaking_opportunity_only"),
        considered_cue_ids=(f"cue_{number:04d}",),
        excluded_own_tts_cue_ids=(f"own_tts_{number:04d}",),
        separate_input_turn_ids=(f"turn_{number:04d}",),
        turn_taking=TurnTakingState(person_has_floor=True),
    )


def context(op: DecisionOpportunity, *, secret: str = "private concern") -> ExactDecisionContext:
    return ExactDecisionContext(
        context_id=f"context_{op.decision_id}",
        person_id=op.person_id,
        activation_revision=op.activation_revision,
        decision_id=op.decision_id,
        considered_cue_ids=op.considered_cue_ids,
        excluded_own_tts_cue_ids=op.excluded_own_tts_cue_ids,
        separate_input_turn_ids=op.separate_input_turn_ids,
        external_turn_id="",
        items=(
            DecisionContextItem(
                item_id=f"fact_{op.decision_id}",
                channel="factual_runtime_truth",
                text="A fresh owner-derived presence cue exists, with uncertainty.",
                certainty=0.72,
                source_ref_ids=op.considered_cue_ids,
            ),
            DecisionContextItem(
                item_id=f"mind_{op.decision_id}",
                channel="private_mind",
                text=secret,
                certainty=0.65,
            ),
        ),
    )


def result(
    op: DecisionOpportunity,
    prof: PersonDecisionProfile,
    ctx: ExactDecisionContext,
    choice: str,
    *,
    spoken_text=None,
    action_id=None,
    action_description=None,
    confidence=0.8,
):
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "decision_id": op.decision_id,
        "person_id": op.person_id,
        "activation_revision": op.activation_revision,
        "pacing_profile_id": prof.pacing_profile_id,
        "profile_revision": prof.profile_revision,
        "context_id": ctx.context_id,
        "choice": choice,
        "confidence": confidence,
        "spoken_text": spoken_text,
        "action_id": action_id,
        "action_description": action_description,
    }


class CapturingAdapter:
    def __init__(self, response_factory):
        self.response_factory = response_factory
        self.calls = []

    def decide(self, request):
        self.calls.append(request)
        return self.response_factory(request)


class SupervisedPersonDecisionTests(unittest.TestCase):
    def setUp(self):
        self.queue = PersonInitiatedEventQueue()
        self.engine = SupervisedPersonDecisionEngine(self.queue)
        self.lease = lease()
        self.profile = profile()
        self.engine.activate(
            self.lease,
            self.profile,
            supervised=True,
            enabled=True,
        )

    def test_speech_publishes_only_public_content_once(self):
        op = opportunity()
        ctx = context(op, secret="Kira privately wonders whether Robert wants company.")
        adapter = CapturingAdapter(
            lambda _: result(op, self.profile, ctx, "speak", spoken_text="Hey, Robert.")
        )

        receipt = self.engine.decide_once(
            self.lease, op, self.profile, ctx, adapter
        )

        self.assertEqual(1, len(adapter.calls))
        self.assertEqual("speak", receipt.choice)
        queued = self.queue.poll(self.lease)
        self.assertEqual(1, len(queued))
        self.assertEqual("Hey, Robert.", queued[0].spoken_text)
        public = receipt.as_public_dict()
        encoded = json.dumps(public)
        self.assertNotIn("privately wonders", encoded)
        self.assertNotIn("decision_style_facts", encoded)
        self.assertNotIn(self.lease.session_nonce, encoded)
        self.assertFalse(public["memory_persisted"])
        self.assertFalse(public["relationship_changed"])
        self.assertFalse(public["action_executed"])

    def test_action_and_leave_use_exact_queue_channels(self):
        action_op = opportunity(outcome="consider_action")
        action_ctx = context(action_op)
        action_receipt = self.engine.decide_once(
            self.lease,
            action_op,
            self.profile,
            action_ctx,
            lambda _: result(
                action_op,
                self.profile,
                action_ctx,
                "action",
                action_id="continue_reading",
                action_description="Continue the current book.",
            ),
        )
        leave_op = opportunity(outcome="leave", number=2)
        leave_ctx = context(leave_op)
        leave_receipt = self.engine.decide_once(
            self.lease,
            leave_op,
            self.profile,
            leave_ctx,
            lambda _: result(
                leave_op,
                self.profile,
                leave_ctx,
                "leave",
                action_id="leave_conversation",
                action_description="Leave the conversation.",
            ),
        )
        events = self.queue.poll(self.lease)
        self.assertEqual(["action", "leave"], [event.event_kind for event in events])
        self.assertFalse(action_receipt.public_event.as_public_dict()["action_executed"])
        self.assertFalse(leave_receipt.public_event.as_public_dict()["action_executed"])

    def test_continue_and_ignore_create_no_public_event(self):
        first = opportunity(outcome="continue_activity")
        first_context = context(first)
        continued = self.engine.decide_once(
            self.lease,
            first,
            self.profile,
            first_context,
            lambda _: result(first, self.profile, first_context, "continue"),
        )
        second = opportunity(outcome="ignore", number=2)
        second_context = context(second)
        ignored = self.engine.decide_once(
            self.lease,
            second,
            self.profile,
            second_context,
            lambda _: result(second, self.profile, second_context, "ignore"),
        )
        self.assertEqual((), self.queue.poll(self.lease))
        self.assertEqual("person_chose_continue_current_activity", continued.quiet_reason)
        self.assertEqual("person_chose_ignore", ignored.quiet_reason)

    def test_strict_schema_rejects_reasoning_field_and_does_not_retry(self):
        op = opportunity()
        ctx = context(op)
        bad = result(op, self.profile, ctx, "speak", spoken_text="Hello.")
        bad["private_thought"] = "secret chain of thought"
        adapter = CapturingAdapter(lambda _: bad)
        with self.assertRaises(DecisionSchemaError):
            self.engine.decide_once(self.lease, op, self.profile, ctx, adapter)
        self.assertEqual(1, len(adapter.calls))
        self.assertEqual((), self.queue.poll(self.lease))

    def test_incompatible_choice_and_unlisted_action_fail_closed(self):
        op = opportunity()
        ctx = context(op)
        with self.assertRaises(DecisionSchemaError):
            self.engine.decide_once(
                self.lease,
                op,
                self.profile,
                ctx,
                lambda _: result(
                    op,
                    self.profile,
                    ctx,
                    "action",
                    action_id="continue_reading",
                ),
            )
        op2 = opportunity(outcome="consider_action", number=2)
        ctx2 = context(op2)
        with self.assertRaises(DecisionSchemaError):
            self.engine.decide_once(
                self.lease,
                op2,
                self.profile,
                ctx2,
                lambda _: result(
                    op2,
                    self.profile,
                    ctx2,
                    "action",
                    action_id="delete_owner_files",
                ),
            )
        self.assertEqual((), self.queue.poll(self.lease))

    def test_non_string_choice_and_private_marker_action_id_fail_closed(self):
        op = opportunity()
        ctx = context(op)
        malformed = result(op, self.profile, ctx, "continue")
        malformed["choice"] = ["speak"]
        with self.assertRaises(DecisionSchemaError):
            self.engine.decide_once(
                self.lease, op, self.profile, ctx, lambda _: malformed
            )
        with self.assertRaises(ValueError):
            replace(
                self.profile,
                allowed_action_ids=("private_thought_action",),
            )

    def test_mismatched_profile_context_and_lease_fail_before_adapter(self):
        op = opportunity()
        ctx = context(op)
        adapter = CapturingAdapter(
            lambda _: result(op, self.profile, ctx, "speak", spoken_text="Hello.")
        )
        with self.assertRaises(DecisionBindingError):
            self.engine.decide_once(
                self.lease,
                op,
                replace(self.profile, profile_revision="kira_profile_r2"),
                ctx,
                adapter,
            )
        with self.assertRaises(DecisionBindingError):
            self.engine.decide_once(
                self.lease,
                op,
                self.profile,
                replace(ctx, considered_cue_ids=("different_cue",)),
                adapter,
            )
        with self.assertRaises(DecisionActivationError):
            self.engine.decide_once(
                lease("lisa", "activation_2"),
                op,
                self.profile,
                ctx,
                adapter,
            )
        self.assertEqual(0, len(adapter.calls))

    def test_person_switch_purges_and_rejects_old_lease(self):
        first = opportunity()
        first_context = context(first)
        self.engine.decide_once(
            self.lease,
            first,
            self.profile,
            first_context,
            lambda _: result(
                first, self.profile, first_context, "speak", spoken_text="Kira's turn."
            ),
        )
        lisa_lease = lease("lisa", "activation_2")
        lisa_profile = profile("lisa", "person_pacing_lisa")
        self.engine.switch_person(
            self.lease,
            lisa_lease,
            lisa_profile,
            supervised=True,
            enabled=True,
        )
        self.assertEqual((), self.queue.poll(lisa_lease))
        with self.assertRaises(DecisionActivationError):
            self.engine.snapshot(self.lease)
        snapshot = self.engine.snapshot(lisa_lease)
        self.assertEqual("lisa", snapshot["lease_binding"]["person_id"])
        self.assertEqual(0, snapshot["model_calls"])

    def test_switch_during_adapter_discards_stale_result(self):
        op = opportunity()
        ctx = context(op)
        lisa_lease = lease("lisa", "activation_2")
        lisa_profile = profile("lisa", "person_pacing_lisa")

        def switches_person(_request):
            self.engine.switch_person(
                self.lease,
                lisa_lease,
                lisa_profile,
                supervised=True,
                enabled=True,
            )
            return result(op, self.profile, ctx, "speak", spoken_text="Stale words.")

        with self.assertRaises(DecisionActivationError):
            self.engine.decide_once(
                self.lease, op, self.profile, ctx, switches_person
            )
        self.assertEqual((), self.queue.poll(lisa_lease))

    def test_different_people_receive_different_exact_profiles(self):
        op = opportunity()
        ctx = context(op)
        captured = []

        def kira_adapter(request):
            captured.append(request["private_profile"])
            return result(op, self.profile, ctx, "speak", spoken_text="I want to talk.")

        self.engine.decide_once(self.lease, op, self.profile, ctx, kira_adapter)
        lisa_lease = lease("lisa", "activation_2")
        lisa_profile = profile(
            "lisa",
            "person_pacing_lisa",
            decision_style_facts=(
                "Lisa often keeps working when the same low-urgency cue appears.",
            ),
        )
        self.engine.switch_person(
            self.lease,
            lisa_lease,
            lisa_profile,
            supervised=True,
            enabled=True,
        )
        lisa_op = opportunity("lisa", "activation_2", "person_pacing_lisa")
        lisa_ctx = context(lisa_op)

        def lisa_adapter(request):
            captured.append(request["private_profile"])
            return result(lisa_op, lisa_profile, lisa_ctx, "continue")

        lisa_receipt = self.engine.decide_once(
            lisa_lease, lisa_op, lisa_profile, lisa_ctx, lisa_adapter
        )
        self.assertNotEqual(captured[0]["decision_style_facts"], captured[1]["decision_style_facts"])
        self.assertEqual("continue", lisa_receipt.choice)
        self.assertEqual((), self.queue.poll(lisa_lease))

    def test_consecutive_bound_is_not_a_time_cooldown_and_external_turn_resets_it(self):
        limited = replace(
            self.profile,
            max_consecutive_public_events_without_external_input=1,
        )
        # Rebind the exact changed profile before using it.
        self.engine.deactivate(self.lease)
        self.engine.activate(self.lease, limited, supervised=True, enabled=True)
        first = opportunity(number=1)
        first_ctx = context(first)
        self.engine.decide_once(
            self.lease,
            first,
            limited,
            first_ctx,
            lambda _: result(first, limited, first_ctx, "speak", spoken_text="First."),
        )
        second = opportunity(number=2)
        second_ctx = context(second)
        seen_allowed = []

        def quiet_adapter(request):
            seen_allowed.extend(request["allowed_choices"])
            return result(second, limited, second_ctx, "continue")

        second_receipt = self.engine.decide_once(
            self.lease, second, limited, second_ctx, quiet_adapter
        )
        self.assertNotIn("speak", seen_allowed)
        self.assertEqual("continue", second_receipt.choice)
        self.assertFalse(self.engine.snapshot(self.lease)["universal_cooldown_present"])

        self.engine.note_external_turn(self.lease, "owner_turn_0001")
        third = opportunity(number=3)
        third_ctx = replace(context(third), external_turn_id="owner_turn_0001")
        third_receipt = self.engine.decide_once(
            self.lease,
            third,
            limited,
            third_ctx,
            lambda request: result(
                third,
                limited,
                third_ctx,
                "speak",
                spoken_text="A new grounded turn.",
            ),
        )
        self.assertEqual("speak", third_receipt.choice)

    def test_per_activation_call_bound_stops_before_adapter(self):
        limited = replace(self.profile, max_model_calls_per_activation=1)
        self.engine.deactivate(self.lease)
        self.engine.activate(self.lease, limited, supervised=True, enabled=True)
        first = opportunity(outcome="continue_activity")
        first_ctx = context(first)
        self.engine.decide_once(
            self.lease,
            first,
            limited,
            first_ctx,
            lambda _: result(first, limited, first_ctx, "continue"),
        )
        second = opportunity(outcome="continue_activity", number=2)
        second_ctx = context(second)
        adapter = CapturingAdapter(
            lambda _: result(second, limited, second_ctx, "continue")
        )
        with self.assertRaises(DecisionLimitError):
            self.engine.decide_once(
                self.lease, second, limited, second_ctx, adapter
            )
        self.assertEqual(0, len(adapter.calls))

    def test_adapter_exception_has_no_retry_or_fallback_words(self):
        op = opportunity()
        ctx = context(op)
        calls = []

        def failing_adapter(request):
            calls.append(request)
            raise RuntimeError("mock failure")

        with self.assertRaises(DecisionAdapterError):
            self.engine.decide_once(
                self.lease, op, self.profile, ctx, failing_adapter
            )
        self.assertEqual(1, len(calls))
        self.assertEqual((), self.queue.poll(self.lease))

    def test_json_result_supported_but_raw_and_private_public_content_rejected(self):
        op = opportunity()
        ctx = context(op)
        good = json.dumps(
            result(op, self.profile, ctx, "speak", spoken_text="Natural public words.")
        )
        receipt = self.engine.decide_once(
            self.lease, op, self.profile, ctx, lambda _: good
        )
        self.assertEqual("speak", receipt.choice)

        op2 = opportunity(number=2)
        ctx2 = context(op2)
        with self.assertRaises(DecisionSchemaError):
            self.engine.decide_once(
                self.lease,
                op2,
                self.profile,
                ctx2,
                lambda _: result(
                    op2,
                    self.profile,
                    ctx2,
                    "speak",
                    spoken_text="Here is my hidden_reasoning: private.",
                ),
            )

    def test_raw_context_payload_is_rejected_at_construction(self):
        with self.assertRaises(ValueError):
            DecisionContextItem(
                item_id="bad_context",
                channel="factual_runtime_truth",
                text="data:image/png;base64," + "A" * 200,
                certainty=1.0,
            )

    def test_activation_requires_explicit_default_off_gate(self):
        queue = PersonInitiatedEventQueue()
        engine = SupervisedPersonDecisionEngine(queue)
        with self.assertRaises(DecisionActivationError):
            engine.activate(self.lease, self.profile, supervised=True, enabled=False)
        with self.assertRaises(DecisionActivationError):
            engine.activate(self.lease, self.profile, supervised=False, enabled=True)

    def test_engine_is_memory_only_and_not_pickleable(self):
        with self.assertRaises(TypeError):
            pickle.dumps(self.engine)

    def test_acceptance_harness_is_inert_and_covers_all_owner_cases(self):
        plan = build_inert_acceptance_plan()
        self.assertEqual("INERT_NO_EXECUTE_LIVE_ACCEPTANCE_NOT_RUN", plan["status"])
        self.assertFalse(plan["default_enabled"])
        self.assertFalse(plan["live_execution_supported_by_this_harness"])
        self.assertEqual(0, plan["model_calls_performed"])
        self.assertEqual(0, plan["device_calls_performed"])
        self.assertEqual(10, len(plan["cases"]))
        self.assertEqual(
            [f"{index:02d}" for index in range(1, 11)],
            [case["case_id"].split("_", 1)[0] for case in plan["cases"]],
        )

    def test_acceptance_harness_refuses_live_flag(self):
        output = StringIO()
        with redirect_stdout(output):
            code = acceptance_main(["--execute-live"])
        self.assertEqual(2, code)
        payload = json.loads(output.getvalue())
        self.assertEqual(
            "REFUSED_LIVE_EXECUTION_NOT_CONNECTED_OR_AUTHORIZED_HERE",
            payload["status"],
        )
        self.assertEqual(0, payload["model_calls_performed"])


if __name__ == "__main__":
    unittest.main()
