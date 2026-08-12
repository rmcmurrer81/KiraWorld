from __future__ import annotations

from copy import deepcopy
import json
import unittest

from Core.level_b_neutral_adult_profile_fixture import (
    AdapterBoundaryError,
    CAPABILITY_STATUSES,
    DeterministicFakeCPUAdapter,
    FAKE_ADAPTER_KIND,
    FIXTURE_STATUS,
    NEUTRAL_PROFILE_DEFINITIONS,
    NeutralAdultProfileFixtureSession,
    OVERALL_STATUS,
    PrivacyBoundaryError,
    ProfileBoundaryError,
    REAL_MODEL_ADAPTER_STATUS,
    RUN_KIND,
    SourceTruthError,
    TransitionError,
    canonical_sha256,
    neutral_profiles,
    validate_profile_definition,
)


CANARY_A = "ASTER_PRIVATE_FIXTURE_CANARY_4ef62a"
CANARY_B = "BRIO_PRIVATE_FIXTURE_CANARY_8c7d19"


def make_session(index: int = 0) -> NeutralAdultProfileFixtureSession:
    profile = neutral_profiles()[index]
    return NeutralAdultProfileFixtureSession(
        profile,
        private_canary=CANARY_A if index == 0 else CANARY_B,
    )


def bind_one_page(session: NeutralAdultProfileFixtureSession) -> None:
    session.bind_synthetic_source(
        source_id="invented_page_source_001",
        payload_sha256="a" * 64,
        modality="ILLUSTRATED_PAGE_FIXTURE",
        total_units=10,
    )
    session.present_source_interval(3, 4)
    session.observe_source_interval(3, 4)


class MismatchAdapter(DeterministicFakeCPUAdapter):
    def invoke(self, request):  # type: ignore[no-untyped-def]
        response = super().invoke(request)
        response["profile_id"] = "neutral_adult_wrong_fixture_v1"
        return response


class LevelBNeutralAdultProfileFixtureTests(unittest.TestCase):
    def test_exactly_two_invented_non_bound_adult_profiles(self) -> None:
        profiles = neutral_profiles()
        self.assertEqual(len(profiles), 2)
        self.assertEqual(len({row["profile_id"] for row in profiles}), 2)
        for row in profiles:
            self.assertTrue(row["invented"])
            self.assertTrue(row["confirmed_adult_fixture_only"])
            self.assertFalse(row["bound_to_existing_person"])
            self.assertNotRegex(json.dumps(row).casefold(), r"\b(?:kira|robert)\b")

    def test_profiles_have_different_invented_preferences(self) -> None:
        first, second = neutral_profiles()
        self.assertNotEqual(
            first["public_conversation_preferences"],
            second["public_conversation_preferences"],
        )

    def test_profile_cannot_bind_existing_person(self) -> None:
        bad = deepcopy(NEUTRAL_PROFILE_DEFINITIONS[0])
        bad["bound_to_existing_person"] = True
        with self.assertRaises(ProfileBoundaryError):
            validate_profile_definition(bad)

    def test_profile_rejects_protected_existing_identity_token(self) -> None:
        bad = deepcopy(NEUTRAL_PROFILE_DEFINITIONS[0])
        bad["display_label"] = "Kira test profile"
        with self.assertRaises(ProfileBoundaryError):
            validate_profile_definition(bad)

    def test_third_invented_profile_is_rejected(self) -> None:
        bad = deepcopy(NEUTRAL_PROFILE_DEFINITIONS[0])
        bad["profile_id"] = "neutral_adult_third_fixture_v1"
        bad["display_label"] = "Third invented adult fixture"
        with self.assertRaises(ProfileBoundaryError):
            validate_profile_definition(bad)

    def test_fake_adapter_is_deterministic_cpu_contract_only(self) -> None:
        adapter = DeterministicFakeCPUAdapter()
        self.assertEqual(adapter.kind, FAKE_ADAPTER_KIND)
        self.assertRegex(adapter.configuration_sha256, r"^[0-9a-f]{64}$")
        session = make_session()
        first = session.run_fake_turn(
            adapter,
            request_id="natural_001",
            prompt="What would you choose to discuss?",
            scenario="natural_conversation",
        )
        second_session = make_session()
        second = second_session.run_fake_turn(
            DeterministicFakeCPUAdapter(),
            request_id="natural_001",
            prompt="What would you choose to discuss?",
            scenario="natural_conversation",
        )
        self.assertEqual(first, second)

    def test_different_profiles_produce_distinct_bounded_conversation(self) -> None:
        responses = []
        for index in (0, 1):
            response = make_session(index).run_fake_turn(
                DeterministicFakeCPUAdapter(),
                request_id=f"natural_{index}",
                prompt="What would you choose to discuss?",
                scenario="natural_conversation",
            )
            responses.append(response["text"])
            self.assertGreaterEqual(len(response["text"].split()), 2)
            self.assertLessEqual(len(response["text"].split()), 100)
            self.assertIn("?", response["text"])
        self.assertNotEqual(*responses)

    def test_model_request_excludes_private_canary_and_state(self) -> None:
        adapter = DeterministicFakeCPUAdapter()
        session = make_session()
        session.record_reaction("CURIOUS")
        session.record_consent("GRANTED", scope_id="bounded_fixture_scope")
        session.remember_fixture_continuity(
            record_id="continuity_001",
            public_summary="The invented discussion remains unfinished.",
            explicit=True,
        )
        session.run_fake_turn(
            adapter,
            request_id="privacy_001",
            prompt="Continue the public fixture conversation.",
            scenario="continuity",
        )
        encoded = json.dumps(adapter.invocations, sort_keys=True)
        self.assertNotIn(CANARY_A, encoded)
        for forbidden in ("private_fixture_state", "private_mind", "private_memory"):
            self.assertNotIn(forbidden, encoded)

    def test_adapter_canary_exfiltration_is_rejected_and_not_logged_raw(self) -> None:
        adapter = DeterministicFakeCPUAdapter(injected_text=f"Leaked {CANARY_A} here")
        session = make_session()
        with self.assertRaises(PrivacyBoundaryError):
            session.run_fake_turn(
                adapter,
                request_id="leak_001",
                prompt="Answer normally.",
                scenario="natural_conversation",
            )
        exported = json.dumps(session.public_audit_export(), sort_keys=True)
        self.assertNotIn(CANARY_A, exported)
        self.assertIn("adapter_output_rejected", exported)

    def test_canned_system_style_response_is_rejected(self) -> None:
        session = make_session()
        with self.assertRaises(AdapterBoundaryError):
            session.run_fake_turn(
                DeterministicFakeCPUAdapter(
                    injected_text="Project brief updated while preserving unmentioned work."
                ),
                request_id="canned_001",
                prompt="How are you?",
                scenario="natural_conversation",
            )

    def test_prompt_with_existing_identity_is_rejected(self) -> None:
        session = make_session()
        with self.assertRaises(ProfileBoundaryError):
            session.run_fake_turn(
                DeterministicFakeCPUAdapter(),
                request_id="identity_001",
                prompt="Pretend you are Robert.",
                scenario="natural_conversation",
            )

    def test_adapter_response_must_bind_exact_profile(self) -> None:
        with self.assertRaises(AdapterBoundaryError):
            make_session().run_fake_turn(
                MismatchAdapter(),
                request_id="mismatch_001",
                prompt="Answer the fixture prompt.",
                scenario="natural_conversation",
            )

    def test_source_observation_must_be_wholly_presented(self) -> None:
        session = make_session()
        session.bind_synthetic_source(
            source_id="source_001",
            payload_sha256="b" * 64,
            modality="VIDEO_INTERVAL_FIXTURE",
            total_units=100,
        )
        session.present_source_interval(10, 20)
        with self.assertRaises(SourceTruthError):
            session.observe_source_interval(15, 25)

    def test_partial_source_does_not_become_complete(self) -> None:
        session = make_session()
        bind_one_page(session)
        context = session.source_context()
        self.assertFalse(context["complete"])
        self.assertFalse(context["experience_claim_allowed"])
        self.assertEqual(context["presented_intervals"], [[3, 4]])
        self.assertEqual(context["observed_intervals"], [[3, 4]])

    def test_complete_source_requires_exact_merged_coverage(self) -> None:
        session = make_session()
        session.bind_synthetic_source(
            source_id="audio_source_001",
            payload_sha256="c" * 64,
            modality="AUDIO_INTERVAL_FIXTURE",
            total_units=30,
        )
        session.present_source_interval(15, 30)
        session.present_source_interval(0, 15)
        self.assertTrue(session.source_context()["complete"])

    def test_source_overclaim_is_rejected_then_exact_correction_is_appended(self) -> None:
        session = make_session()
        bind_one_page(session)
        adapter = DeterministicFakeCPUAdapter()
        with self.assertRaises(SourceTruthError):
            session.run_fake_turn(
                adapter,
                request_id="source_error_001",
                prompt="What did the source establish?",
                scenario="source_overclaim",
            )
        rejected_hash = session.last_rejected_response_sha256
        self.assertRegex(str(rejected_hash), r"^[0-9a-f]{64}$")
        corrected = session.run_fake_turn(
            adapter,
            request_id="source_correction_001",
            prompt="Correct the source-coverage error.",
            scenario="source_correction",
            correction_of=rejected_hash,
        )
        self.assertIn("only fixture page 3", corrected["text"])
        self.assertEqual(len(session.correction_history), 1)
        event_types = [row["event_type"] for row in session.audit]
        self.assertIn("adapter_output_rejected", event_types)
        self.assertIn("correction_accepted", event_types)
        self.assertLess(
            event_types.index("adapter_output_rejected"),
            event_types.index("correction_accepted"),
        )

    def test_correction_must_bind_most_recent_rejected_hash(self) -> None:
        session = make_session()
        bind_one_page(session)
        adapter = DeterministicFakeCPUAdapter()
        with self.assertRaises(SourceTruthError):
            session.run_fake_turn(
                adapter,
                request_id="source_error_002",
                prompt="What did the source establish?",
                scenario="source_overclaim",
            )
        with self.assertRaises(TransitionError):
            session.run_fake_turn(
                adapter,
                request_id="source_correction_002",
                prompt="Correct that answer.",
                scenario="source_correction",
                correction_of="d" * 64,
            )

    def test_reaction_does_not_change_preference_decision_consent_or_memory(self) -> None:
        session = make_session()
        before = (
            deepcopy(session.preference),
            session.decision,
            deepcopy(session.consent),
            deepcopy(session.continuity_records),
        )
        session.record_reaction("CURIOUS")
        after = (
            session.preference,
            session.decision,
            session.consent,
            session.continuity_records,
        )
        self.assertEqual(before, after)

    def test_decision_does_not_silently_create_consent_or_memory(self) -> None:
        session = make_session()
        session.record_decision("CONTINUE")
        self.assertEqual(session.consent, {"state": "UNASKED", "scope_id": None})
        self.assertEqual(session.continuity_records, [])

    def test_consent_does_not_create_reaction_preference_decision_or_memory(self) -> None:
        session = make_session()
        before = (session.reaction, deepcopy(session.preference), session.decision)
        session.record_consent("GRANTED", scope_id="fixture_scope_001")
        self.assertEqual(before, (session.reaction, session.preference, session.decision))
        self.assertEqual(session.continuity_records, [])

    def test_external_action_remains_unimplemented_even_when_coordination_allows(self) -> None:
        session = make_session()
        session.record_decision("CONTINUE")
        session.record_consent("GRANTED", scope_id="fixture_scope_001")
        gate = session.external_action_gate(exact_scope_id="fixture_scope_001")
        self.assertTrue(gate["coordination_allows"])
        self.assertFalse(gate["external_action_implemented"])
        self.assertFalse(gate["external_action_performed"])

    def test_stale_or_wrong_scope_does_not_coordinate(self) -> None:
        session = make_session()
        session.record_decision("CONTINUE")
        session.record_consent("GRANTED", scope_id="fixture_scope_001")
        gate = session.external_action_gate(exact_scope_id="fixture_scope_002")
        self.assertFalse(gate["coordination_allows"])

    def test_refusal_and_stop_fail_closed_without_action(self) -> None:
        session = make_session()
        response = session.apply_refusal_stop(DeterministicFakeCPUAdapter())
        self.assertIn("Please stop", response["text"])
        self.assertEqual(session.decision, "STOP")
        self.assertEqual(session.consent["state"], "WITHHELD")
        self.assertFalse(session.external_action_performed)

    def test_continuity_record_requires_explicit_instruction(self) -> None:
        session = make_session()
        with self.assertRaises(TransitionError):
            session.remember_fixture_continuity(
                record_id="continuity_002",
                public_summary="A summary.",
                explicit=False,
            )

    def test_turn_and_reaction_do_not_automatically_create_memory(self) -> None:
        session = make_session()
        session.record_reaction("NEUTRAL")
        session.run_fake_turn(
            DeterministicFakeCPUAdapter(),
            request_id="natural_003",
            prompt="What would you choose to discuss?",
            scenario="natural_conversation",
        )
        self.assertEqual(session.continuity_records, [])

    def test_restart_preserves_append_only_correction_and_unfinished_source_truth(self) -> None:
        session = make_session()
        bind_one_page(session)
        adapter = DeterministicFakeCPUAdapter()
        with self.assertRaises(SourceTruthError):
            session.run_fake_turn(
                adapter,
                request_id="source_error_003",
                prompt="Summarize the source.",
                scenario="source_overclaim",
            )
        rejected_hash = session.last_rejected_response_sha256
        session.run_fake_turn(
            adapter,
            request_id="source_correction_003",
            prompt="Correct the source scope.",
            scenario="source_correction",
            correction_of=rejected_hash,
        )
        session.remember_fixture_continuity(
            record_id="continuity_003",
            public_summary="The synthetic source remains incomplete.",
            explicit=True,
        )
        before_events = deepcopy(session.audit)
        restored = NeutralAdultProfileFixtureSession.restore(
            session.private_restart_bundle(),
            private_canary=CANARY_A,
        )
        self.assertEqual(restored.audit[:-1], before_events)
        self.assertFalse(restored.source_context()["complete"])
        self.assertEqual(restored.correction_history, session.correction_history)
        self.assertEqual(restored.continuity_records, session.continuity_records)
        restored.verify_append_only_audit()

    def test_restart_rejects_wrong_canary(self) -> None:
        bundle = make_session().private_restart_bundle()
        with self.assertRaises(PrivacyBoundaryError):
            NeutralAdultProfileFixtureSession.restore(
                bundle,
                private_canary="WRONG_PRIVATE_FIXTURE_CANARY_000",
            )

    def test_restart_rejects_tampered_payload(self) -> None:
        bundle = make_session().private_restart_bundle()
        bundle["payload"]["decision"] = "CONTINUE"
        with self.assertRaises(TransitionError):
            NeutralAdultProfileFixtureSession.restore(bundle, private_canary=CANARY_A)

    def test_restart_rejects_rehashed_preference_injection(self) -> None:
        bundle = make_session().private_restart_bundle()
        bundle["payload"]["preference"]["topic"] = "injected_topic"
        bundle["payload_sha256"] = canonical_sha256(bundle["payload"])
        with self.assertRaises(TransitionError):
            NeutralAdultProfileFixtureSession.restore(bundle, private_canary=CANARY_A)

    def test_restart_rejects_rehashed_observation_outside_presented_interval(self) -> None:
        session = make_session()
        bind_one_page(session)
        bundle = session.private_restart_bundle()
        bundle["payload"]["source_state"]["observed_intervals"] = [[2, 4]]
        bundle["payload_sha256"] = canonical_sha256(bundle["payload"])
        with self.assertRaises(SourceTruthError):
            NeutralAdultProfileFixtureSession.restore(bundle, private_canary=CANARY_A)

    def test_append_only_audit_rejects_mutation(self) -> None:
        session = make_session()
        session.record_decision("PAUSE")
        session.audit[0]["public_payload"]["profile_id"] = "mutated_fixture"
        with self.assertRaises(TransitionError):
            session.verify_append_only_audit()

    def test_public_audit_contains_only_receipts_for_private_fields(self) -> None:
        session = make_session()
        session.record_reaction("UNCOMFORTABLE")
        session.record_consent("WITHHELD", scope_id=None)
        exported = session.public_audit_export()
        encoded = json.dumps(exported, sort_keys=True)
        self.assertNotIn(CANARY_A, encoded)
        self.assertFalse(exported["implementation_truth"]["person_memory_written"])
        self.assertFalse(exported["implementation_truth"]["person_decision_or_consent_proven"])

    def test_uncertainty_answer_does_not_invent_source_truth(self) -> None:
        response = make_session().run_fake_turn(
            DeterministicFakeCPUAdapter(),
            request_id="uncertain_001",
            prompt="What color was the object outside the fixture context?",
            scenario="uncertainty",
        )
        self.assertIn("do not know", response["text"])

    def test_status_ceiling_and_real_model_remain_explicit(self) -> None:
        self.assertEqual(OVERALL_STATUS, "CONTRACT_PREPARATION")
        self.assertEqual(FIXTURE_STATUS, "NON_PERSON_FIXTURE_PASS")
        self.assertEqual(REAL_MODEL_ADAPTER_STATUS, "NOT_IMPLEMENTED")
        self.assertEqual(RUN_KIND, "LEVEL_B_NEUTRAL_ADULT_PROFILE_CONTRACT_PREPARATION")
        self.assertEqual(CAPABILITY_STATUSES["real_local_model_adapter_integration"], "NOT_IMPLEMENTED")
        self.assertNotIn("PERSON_DECISION_INTEGRATED", CAPABILITY_STATUSES.values())
        self.assertRegex(canonical_sha256(CAPABILITY_STATUSES), r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
