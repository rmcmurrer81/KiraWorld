from __future__ import annotations

from copy import deepcopy
import hashlib
import unittest

from Core.kira_lisa_reconstruction_access_v2 import (
    AuthenticatedParticipantOrigin,
    CapabilityError,
    DecisionError,
    EXACT_PARTICIPANTS,
    IntegrityError,
    KiraLisaReconstructionAccessControllerV2,
    NonparticipantViewLeaseV2,
    ParticipantDecision,
    ParticipantPrivateLeaseV2,
    PinnedAuthorityError,
    RECONSTRUCTION_ID,
    ReconstructionWriteOrigin,
    ReconstructionAccessRequestV2,
    ReconstructionScope,
    SOURCE_MEMORY_ID,
    SOURCE_MEMORY_SHA256,
)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class MutableClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.value = start

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class ReconstructionAccessV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = MutableClock()
        self.controller = KiraLisaReconstructionAccessControllerV2.load_pinned(
            clock=self.clock
        )
        self.kira = self.controller.activate_participant_private_session(
            participant_id="kira",
            activation_revision="kira_activation_1",
            session_id="kira_private_session_1",
            origin=AuthenticatedParticipantOrigin.PRIVATE_PERSON_UI,
            ttl_seconds=500,
        )
        self.lisa = self.controller.activate_participant_private_session(
            participant_id="lisa",
            activation_revision="lisa_activation_1",
            session_id="lisa_private_session_1",
            origin=AuthenticatedParticipantOrigin.SUPERVISED_PERSON_SESSION,
            ttl_seconds=500,
        )
        self.material_digest = digest("material_context_v1")

    def binding(self) -> dict:
        return self.controller.current_reconstruction_binding()

    def make_request(
        self,
        *,
        request_id: str = "request_1",
        scope: ReconstructionScope = ReconstructionScope.SUMMARY,
        zones: tuple[str, ...] = (),
        ttl: float = 120,
        viewer: str = "real_robert",
        viewer_session: str = "robert_session_1",
    ) -> tuple[ReconstructionAccessRequestV2, str]:
        reconstruction_digest = self.binding()["reconstruction_digest"]
        request = self.controller.create_nonparticipant_request(
            request_id=request_id,
            intended_viewer=viewer,
            viewer_session_id=viewer_session,
            requested_scope=scope,
            requested_zones=zones,
            reconstruction_id=RECONSTRUCTION_ID,
            reconstruction_digest=reconstruction_digest,
            material_context_digest=self.material_digest,
            ttl_seconds=ttl,
        )
        return request, reconstruction_digest

    def decide(
        self,
        request: ReconstructionAccessRequestV2,
        reconstruction_digest: str,
        *,
        person: str,
        decision: ParticipantDecision = ParticipantDecision.APPROVE,
        requested_scope: ReconstructionScope = ReconstructionScope.SUMMARY,
        approved_scope: ReconstructionScope | None = ReconstructionScope.SUMMARY,
        requested_zones: tuple[str, ...] = (),
        approved_zones: tuple[str, ...] = (),
        visual: bool = False,
        request_id: str = "request_1",
        viewer: str = "real_robert",
        viewer_session: str = "robert_session_1",
    ) -> dict:
        del requested_zones
        capability = self.kira if person == "kira" else self.lisa
        participant_session = (
            "kira_private_session_1" if person == "kira" else "lisa_private_session_1"
        )
        return self.controller.record_participant_decision(
            capability,
            request,
            participant_id=person,
            participant_session_id=participant_session,
            request_id=request_id,
            intended_viewer=viewer,
            viewer_session_id=viewer_session,
            requested_scope=requested_scope,
            reconstruction_digest=reconstruction_digest,
            material_context_digest=self.material_digest,
            decision=decision,
            approved_scope=approved_scope,
            approved_zones=approved_zones,
            visual_body_exposure_allowed=visual,
        )

    def approve_both(
        self,
        request: ReconstructionAccessRequestV2,
        reconstruction_digest: str,
        *,
        requested_scope: ReconstructionScope,
        approved_scope: ReconstructionScope | None = None,
        approved_zones: tuple[str, ...] = (),
        request_id: str = "request_1",
        viewer: str = "real_robert",
        viewer_session: str = "robert_session_1",
    ) -> None:
        scope = approved_scope or requested_scope
        visual = scope in {
            ReconstructionScope.NON_INTIMATE_LEAD_IN,
            ReconstructionScope.SELECTED_ZONES,
            ReconstructionScope.ONE_TIME_FULL_REPLAY,
            ReconstructionScope.FULL_REPLAY,
        }
        for person in EXACT_PARTICIPANTS:
            self.decide(
                request,
                reconstruction_digest,
                person=person,
                requested_scope=requested_scope,
                approved_scope=scope,
                approved_zones=approved_zones,
                visual=visual,
                request_id=request_id,
                viewer=viewer,
                viewer_session=viewer_session,
            )

    def issue(
        self,
        request: ReconstructionAccessRequestV2,
        reconstruction_digest: str,
        *,
        requested_scope: ReconstructionScope,
        request_id: str = "request_1",
        viewer: str = "real_robert",
        viewer_session: str = "robert_session_1",
    ) -> NonparticipantViewLeaseV2:
        return self.controller.issue_nonparticipant_view_lease(
            request,
            request_id=request_id,
            intended_viewer=viewer,
            viewer_session_id=viewer_session,
            requested_scope=requested_scope,
            reconstruction_digest=reconstruction_digest,
            material_context_digest=self.material_digest,
        )

    def consume(
        self,
        lease: NonparticipantViewLeaseV2,
        reconstruction_digest: str,
        *,
        approved_scope: ReconstructionScope,
        approved_zones: tuple[str, ...] = (),
        request_id: str = "request_1",
        viewer: str = "real_robert",
        viewer_session: str = "robert_session_1",
        material_digest: str | None = None,
    ) -> dict:
        return self.controller.consume_nonparticipant_view(
            lease,
            request_id=request_id,
            intended_viewer=viewer,
            viewer_session_id=viewer_session,
            approved_scope=approved_scope,
            approved_zones=approved_zones,
            reconstruction_digest=reconstruction_digest,
            material_context_digest=material_digest or self.material_digest,
        )

    def test_pinned_source_participants_and_public_constructor_boundary(self) -> None:
        binding = self.binding()
        self.assertEqual(binding["source_memory_id"], SOURCE_MEMORY_ID)
        self.assertEqual(binding["source_memory_sha256"], SOURCE_MEMORY_SHA256)
        self.assertEqual(binding["exact_participants"], ["kira", "lisa"])
        with self.assertRaises(PinnedAuthorityError):
            KiraLisaReconstructionAccessControllerV2()
        with self.assertRaises(TypeError):
            KiraLisaReconstructionAccessControllerV2.load_pinned(policy={})
        with self.assertRaises(TypeError):
            KiraLisaReconstructionAccessControllerV2.load_pinned(
                classification={"marinette": "confirmed_adult"}
            )
        with self.assertRaises(TypeError):
            ParticipantPrivateLeaseV2()
        with self.assertRaises(TypeError):
            self.controller.create_nonparticipant_request(
                request_id="caller_source_override",
                intended_viewer="real_robert",
                viewer_session_id="viewer_session",
                requested_scope=ReconstructionScope.SUMMARY,
                reconstruction_id=RECONSTRUCTION_ID,
                reconstruction_digest=binding["reconstruction_digest"],
                material_context_digest=self.material_digest,
                ttl_seconds=30,
                source_memory_sha256=digest("caller supplied source"),
            )

    def test_participant_private_snapshot_requires_live_exact_identity_capability(self) -> None:
        self.controller.append_person_reconstruction(
            self.kira,
            participant_id="kira",
            participant_session_id="kira_private_session_1",
            reflection_text="Kira private detail sentinel.",
            source_label="selected_person_private_recall",
            confidence=0.5,
            recall_strength_delta=0.1,
            write_origin=ReconstructionWriteOrigin.PRIVATE_PERSON_SELECTION,
        )
        snapshot = self.controller.participant_private_snapshot(
            self.kira,
            participant_id="kira",
            participant_session_id="kira_private_session_1",
            reconstruction_id=RECONSTRUCTION_ID,
        )
        self.assertIn("private detail sentinel", snapshot["records"][0]["reflection_text"])
        self.assertFalse(snapshot["other_person_ledger_included"])
        with self.assertRaises(CapabilityError):
            self.controller.participant_private_snapshot(
                self.lisa,
                participant_id="kira",
                participant_session_id="lisa_private_session_1",
                reconstruction_id=RECONSTRUCTION_ID,
            )
        clone = deepcopy(self.kira)
        with self.assertRaises(CapabilityError):
            self.controller.participant_private_snapshot(
                clone,
                participant_id="kira",
                participant_session_id="kira_private_session_1",
                reconstruction_id=RECONSTRUCTION_ID,
            )
        self.controller.close_participant_private_session(self.kira)
        with self.assertRaises(CapabilityError):
            self.controller.participant_private_snapshot(
                self.kira,
                participant_id="kira",
                participant_session_id="kira_private_session_1",
                reconstruction_id=RECONSTRUCTION_ID,
            )

    def test_own_perspective_verbal_permit_never_grants_visual_or_other_person(self) -> None:
        self.controller.append_person_reconstruction(
            self.kira,
            participant_id="kira",
            participant_session_id="kira_private_session_1",
            reflection_text="Kira may choose this own-perspective statement.",
            source_label="current_interpretation",
            confidence=0.7,
            recall_strength_delta=0,
            write_origin=ReconstructionWriteOrigin.PRIVATE_PERSON_SELECTION,
        )
        self.controller.append_person_reconstruction(
            self.lisa,
            participant_id="lisa",
            participant_session_id="lisa_private_session_1",
            reflection_text="Lisa separate private perspective.",
            source_label="current_interpretation",
            confidence=0.7,
            recall_strength_delta=0,
            write_origin=ReconstructionWriteOrigin.PRIVATE_PERSON_SELECTION,
        )
        permit = self.controller.create_own_perspective_verbal_permit(
            self.kira,
            participant_id="kira",
            participant_session_id="kira_private_session_1",
            intended_listener="real_robert",
            listener_session_id="robert_listener_1",
            record_sequences=(1,),
            ttl_seconds=60,
        )
        receipt = self.controller.consume_own_perspective_verbal_permit(
            permit,
            participant_id="kira",
            intended_listener="real_robert",
            listener_session_id="robert_listener_1",
        )
        self.assertFalse(receipt["visual_replay_authorized"])
        self.assertFalse(receipt["locked_zone_access_authorized"])
        self.assertFalse(receipt["other_participant_perspective_authorized"])
        self.assertFalse(receipt["private_text_in_receipt"])
        with self.assertRaises(CapabilityError):
            self.controller.consume_own_perspective_verbal_permit(
                permit,
                participant_id="kira",
                intended_listener="real_robert",
                listener_session_id="robert_listener_1",
            )
        with self.assertRaises(CapabilityError):
            self.controller.create_own_perspective_verbal_permit(
                self.kira,
                participant_id="lisa",
                participant_session_id="kira_private_session_1",
                intended_listener="real_robert",
                listener_session_id="robert_listener_1",
                record_sequences=(1,),
                ttl_seconds=60,
            )

    def test_every_nonparticipant_scope_requires_both_exact_participants(self) -> None:
        scopes = list(ReconstructionScope)
        for index, scope in enumerate(scopes, start=1):
            with self.subTest(scope=scope.value):
                clock = MutableClock()
                controller = KiraLisaReconstructionAccessControllerV2.load_pinned(
                    clock=clock
                )
                kira = controller.activate_participant_private_session(
                    participant_id="kira",
                    activation_revision="kira_activation",
                    session_id="kira_session",
                    origin=AuthenticatedParticipantOrigin.PRIVATE_PERSON_UI,
                    ttl_seconds=200,
                )
                lisa = controller.activate_participant_private_session(
                    participant_id="lisa",
                    activation_revision="lisa_activation",
                    session_id="lisa_session",
                    origin=AuthenticatedParticipantOrigin.PRIVATE_PERSON_UI,
                    ttl_seconds=200,
                )
                reconstruction_digest = controller.current_reconstruction_binding()[
                    "reconstruction_digest"
                ]
                zones = ("locked_zone_a",) if scope is ReconstructionScope.SELECTED_ZONES else ()
                request_id = f"scope_request_{index}"
                request = controller.create_nonparticipant_request(
                    request_id=request_id,
                    intended_viewer="real_robert",
                    viewer_session_id=f"viewer_session_{index}",
                    requested_scope=scope,
                    requested_zones=zones,
                    reconstruction_id=RECONSTRUCTION_ID,
                    reconstruction_digest=reconstruction_digest,
                    material_context_digest=self.material_digest,
                    ttl_seconds=100,
                )
                visual = scope in {
                    ReconstructionScope.NON_INTIMATE_LEAD_IN,
                    ReconstructionScope.SELECTED_ZONES,
                    ReconstructionScope.ONE_TIME_FULL_REPLAY,
                    ReconstructionScope.FULL_REPLAY,
                }
                controller.record_participant_decision(
                    kira,
                    request,
                    participant_id="kira",
                    participant_session_id="kira_session",
                    request_id=request_id,
                    intended_viewer="real_robert",
                    viewer_session_id=f"viewer_session_{index}",
                    requested_scope=scope,
                    reconstruction_digest=reconstruction_digest,
                    material_context_digest=self.material_digest,
                    decision=ParticipantDecision.APPROVE,
                    approved_scope=scope,
                    approved_zones=zones,
                    visual_body_exposure_allowed=visual,
                )
                with self.assertRaises(DecisionError):
                    controller.issue_nonparticipant_view_lease(
                        request,
                        request_id=request_id,
                        intended_viewer="real_robert",
                        viewer_session_id=f"viewer_session_{index}",
                        requested_scope=scope,
                        reconstruction_digest=reconstruction_digest,
                        material_context_digest=self.material_digest,
                    )
                controller.record_participant_decision(
                    lisa,
                    request,
                    participant_id="lisa",
                    participant_session_id="lisa_session",
                    request_id=request_id,
                    intended_viewer="real_robert",
                    viewer_session_id=f"viewer_session_{index}",
                    requested_scope=scope,
                    reconstruction_digest=reconstruction_digest,
                    material_context_digest=self.material_digest,
                    decision=ParticipantDecision.APPROVE,
                    approved_scope=scope,
                    approved_zones=zones,
                    visual_body_exposure_allowed=visual,
                )
                lease = controller.issue_nonparticipant_view_lease(
                    request,
                    request_id=request_id,
                    intended_viewer="real_robert",
                    viewer_session_id=f"viewer_session_{index}",
                    requested_scope=scope,
                    reconstruction_digest=reconstruction_digest,
                    material_context_digest=self.material_digest,
                )
                receipt = controller.consume_nonparticipant_view(
                    lease,
                    request_id=request_id,
                    intended_viewer="real_robert",
                    viewer_session_id=f"viewer_session_{index}",
                    approved_scope=scope,
                    approved_zones=zones,
                    reconstruction_digest=reconstruction_digest,
                    material_context_digest=self.material_digest,
                )
                self.assertEqual(receipt["approved_scope"], scope.value)

    def test_duplicate_missing_and_extra_responses_fail_closed(self) -> None:
        request, reconstruction_digest = self.make_request()
        self.decide(request, reconstruction_digest, person="kira")
        with self.assertRaises(DecisionError):
            self.decide(request, reconstruction_digest, person="kira")
        with self.assertRaises(DecisionError):
            self.issue(
                request,
                reconstruction_digest,
                requested_scope=ReconstructionScope.SUMMARY,
            )
        with self.assertRaises(CapabilityError):
            self.controller.activate_participant_private_session(
                participant_id="mallory",
                activation_revision="mallory_activation",
                session_id="mallory_session",
                origin=AuthenticatedParticipantOrigin.PRIVATE_PERSON_UI,
                ttl_seconds=100,
            )

    def test_requested_summary_cannot_escalate_to_full_replay(self) -> None:
        request, reconstruction_digest = self.make_request()
        with self.assertRaises(DecisionError):
            self.decide(
                request,
                reconstruction_digest,
                person="kira",
                requested_scope=ReconstructionScope.SUMMARY,
                approved_scope=ReconstructionScope.FULL_REPLAY,
                visual=True,
            )

    def test_one_summary_only_response_cannot_authorize_one_time_full(self) -> None:
        request, reconstruction_digest = self.make_request(
            scope=ReconstructionScope.ONE_TIME_FULL_REPLAY
        )
        self.decide(
            request,
            reconstruction_digest,
            person="kira",
            requested_scope=ReconstructionScope.ONE_TIME_FULL_REPLAY,
            approved_scope=ReconstructionScope.ONE_TIME_FULL_REPLAY,
            visual=True,
        )
        self.decide(
            request,
            reconstruction_digest,
            person="lisa",
            requested_scope=ReconstructionScope.ONE_TIME_FULL_REPLAY,
            approved_scope=ReconstructionScope.SUMMARY,
            visual=False,
        )
        with self.assertRaises(DecisionError):
            self.issue(
                request,
                reconstruction_digest,
                requested_scope=ReconstructionScope.ONE_TIME_FULL_REPLAY,
            )

    def test_summary_and_verbal_never_grant_visual_access(self) -> None:
        request, reconstruction_digest = self.make_request()
        with self.assertRaises(DecisionError):
            self.decide(
                request,
                reconstruction_digest,
                person="kira",
                visual=True,
            )
        request2, reconstruction_digest2 = self.make_request(
            request_id="verbal_request",
            scope=ReconstructionScope.VERBAL_DETAILS_ONLY,
        )
        self.approve_both(
            request2,
            reconstruction_digest2,
            requested_scope=ReconstructionScope.VERBAL_DETAILS_ONLY,
            request_id="verbal_request",
        )
        lease = self.issue(
            request2,
            reconstruction_digest2,
            requested_scope=ReconstructionScope.VERBAL_DETAILS_ONLY,
            request_id="verbal_request",
        )
        receipt = self.consume(
            lease,
            reconstruction_digest2,
            approved_scope=ReconstructionScope.VERBAL_DETAILS_ONLY,
            request_id="verbal_request",
        )
        self.assertFalse(receipt["visual_body_exposure_allowed"])
        self.assertFalse(receipt["locked_zone_access_allowed"])
        self.assertFalse(receipt["full_replay_allowed"])

    def test_wrong_viewer_session_scope_source_and_reconstruction_are_rejected(self) -> None:
        reconstruction_digest = self.binding()["reconstruction_digest"]
        with self.assertRaises(DecisionError):
            self.controller.create_nonparticipant_request(
                request_id="bad_source",
                intended_viewer="real_robert",
                viewer_session_id="robert_session",
                requested_scope=ReconstructionScope.SUMMARY,
                reconstruction_id=RECONSTRUCTION_ID,
                reconstruction_digest=digest("wrong source"),
                material_context_digest=self.material_digest,
                ttl_seconds=30,
            )
        with self.assertRaises(DecisionError):
            self.controller.create_nonparticipant_request(
                request_id="bad_reconstruction",
                intended_viewer="real_robert",
                viewer_session_id="robert_session",
                requested_scope=ReconstructionScope.SUMMARY,
                reconstruction_id="other_reconstruction",
                reconstruction_digest=reconstruction_digest,
                material_context_digest=self.material_digest,
                ttl_seconds=30,
            )
        request, reconstruction_digest = self.make_request()
        self.approve_both(
            request,
            reconstruction_digest,
            requested_scope=ReconstructionScope.SUMMARY,
        )
        lease = self.issue(
            request,
            reconstruction_digest,
            requested_scope=ReconstructionScope.SUMMARY,
        )
        for kwargs in (
            {"viewer": "mallory"},
            {"viewer_session": "wrong_session"},
            {"approved_scope": ReconstructionScope.EMOTIONAL_MEANING},
            {"material_digest": digest("changed")},
        ):
            values = {
                "approved_scope": ReconstructionScope.SUMMARY,
                "viewer": "real_robert",
                "viewer_session": "robert_session_1",
            }
            values.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(CapabilityError):
                self.consume(lease, reconstruction_digest, **values)

    def test_request_and_view_expiry_are_fresh_and_bounded(self) -> None:
        with self.assertRaises(DecisionError):
            self.make_request(ttl=301)
        request, reconstruction_digest = self.make_request(ttl=5)
        self.approve_both(
            request,
            reconstruction_digest,
            requested_scope=ReconstructionScope.SUMMARY,
        )
        lease = self.issue(
            request,
            reconstruction_digest,
            requested_scope=ReconstructionScope.SUMMARY,
        )
        self.clock.advance(5)
        with self.assertRaises(CapabilityError):
            self.consume(
                lease,
                reconstruction_digest,
                approved_scope=ReconstructionScope.SUMMARY,
            )

    def test_participant_private_lease_expiry_blocks_reads_and_decisions(self) -> None:
        clock = MutableClock()
        controller = KiraLisaReconstructionAccessControllerV2.load_pinned(clock=clock)
        lease = controller.activate_participant_private_session(
            participant_id="kira",
            activation_revision="kira_expiring_activation",
            session_id="kira_expiring_session",
            origin=AuthenticatedParticipantOrigin.PRIVATE_PERSON_UI,
            ttl_seconds=2,
        )
        clock.advance(2)
        with self.assertRaises(CapabilityError):
            controller.participant_private_snapshot(
                lease,
                participant_id="kira",
                participant_session_id="kira_expiring_session",
                reconstruction_id=RECONSTRUCTION_ID,
            )

    def test_revocation_and_uncertainty_immediately_invalidate_issued_lease(self) -> None:
        for uncertain in (False, True):
            with self.subTest(uncertain=uncertain):
                self.setUp()
                request, reconstruction_digest = self.make_request()
                self.approve_both(
                    request,
                    reconstruction_digest,
                    requested_scope=ReconstructionScope.SUMMARY,
                )
                lease = self.issue(
                    request,
                    reconstruction_digest,
                    requested_scope=ReconstructionScope.SUMMARY,
                )
                self.controller.revoke_or_mark_uncertain(
                    self.lisa,
                    request,
                    participant_id="lisa",
                    participant_session_id="lisa_private_session_1",
                    request_id="request_1",
                    reason="Lisa changed her current decision.",
                    uncertain=uncertain,
                )
                with self.assertRaises(CapabilityError):
                    self.consume(
                        lease,
                        reconstruction_digest,
                        approved_scope=ReconstructionScope.SUMMARY,
                    )

    def test_one_request_one_lease_and_one_consumption_prevent_replay(self) -> None:
        request, reconstruction_digest = self.make_request(
            scope=ReconstructionScope.ONE_TIME_FULL_REPLAY
        )
        self.approve_both(
            request,
            reconstruction_digest,
            requested_scope=ReconstructionScope.ONE_TIME_FULL_REPLAY,
        )
        lease = self.issue(
            request,
            reconstruction_digest,
            requested_scope=ReconstructionScope.ONE_TIME_FULL_REPLAY,
        )
        with self.assertRaises(DecisionError):
            self.issue(
                request,
                reconstruction_digest,
                requested_scope=ReconstructionScope.ONE_TIME_FULL_REPLAY,
            )
        receipt = self.consume(
            lease,
            reconstruction_digest,
            approved_scope=ReconstructionScope.ONE_TIME_FULL_REPLAY,
        )
        self.assertFalse(receipt["lease_reusable"])
        with self.assertRaises(CapabilityError):
            self.consume(
                lease,
                reconstruction_digest,
                approved_scope=ReconstructionScope.ONE_TIME_FULL_REPLAY,
            )

    def test_value_clones_and_wrong_controller_are_rejected(self) -> None:
        request, reconstruction_digest = self.make_request()
        request_clone = deepcopy(request)
        with self.assertRaises(CapabilityError):
            self.controller.issue_nonparticipant_view_lease(
                request_clone,
                request_id="request_1",
                intended_viewer="real_robert",
                viewer_session_id="robert_session_1",
                requested_scope=ReconstructionScope.SUMMARY,
                reconstruction_digest=reconstruction_digest,
                material_context_digest=self.material_digest,
            )
        self.approve_both(
            request,
            reconstruction_digest,
            requested_scope=ReconstructionScope.SUMMARY,
        )
        lease = self.issue(
            request,
            reconstruction_digest,
            requested_scope=ReconstructionScope.SUMMARY,
        )
        lease_clone = deepcopy(lease)
        with self.assertRaises(CapabilityError):
            self.consume(
                lease_clone,
                reconstruction_digest,
                approved_scope=ReconstructionScope.SUMMARY,
            )
        other = KiraLisaReconstructionAccessControllerV2.load_pinned(
            clock=MutableClock()
        )
        with self.assertRaises(CapabilityError):
            other.consume_nonparticipant_view(
                lease,
                request_id="request_1",
                intended_viewer="real_robert",
                viewer_session_id="robert_session_1",
                approved_scope=ReconstructionScope.SUMMARY,
                reconstruction_digest=reconstruction_digest,
                material_context_digest=self.material_digest,
            )

    def test_material_context_change_invalidates_request_and_lease(self) -> None:
        request, reconstruction_digest = self.make_request()
        self.approve_both(
            request,
            reconstruction_digest,
            requested_scope=ReconstructionScope.SUMMARY,
        )
        lease = self.issue(
            request,
            reconstruction_digest,
            requested_scope=ReconstructionScope.SUMMARY,
        )
        changed = digest("material_context_v2")
        result = self.controller.note_material_context_change(
            previous_material_context_digest=self.material_digest,
            new_material_context_digest=changed,
        )
        self.assertEqual(result["requests_invalidated"], 1)
        with self.assertRaises(CapabilityError):
            self.consume(
                lease,
                reconstruction_digest,
                approved_scope=ReconstructionScope.SUMMARY,
            )

    def test_clock_rollback_invalidates_all_capabilities(self) -> None:
        request, reconstruction_digest = self.make_request()
        self.approve_both(
            request,
            reconstruction_digest,
            requested_scope=ReconstructionScope.SUMMARY,
        )
        lease = self.issue(
            request,
            reconstruction_digest,
            requested_scope=ReconstructionScope.SUMMARY,
        )
        self.clock.value -= 1
        with self.assertRaises(IntegrityError):
            self.consume(
                lease,
                reconstruction_digest,
                approved_scope=ReconstructionScope.SUMMARY,
            )
        # Read-only audit evidence remains inspectable, but every capability
        # operation stays invalidated after the rollback fault.
        self.assertTrue(self.controller.audit_snapshot()["verification"]["verified"])
        with self.assertRaises(IntegrityError):
            self.controller.participant_private_snapshot(
                self.kira,
                participant_id="kira",
                participant_session_id="kira_private_session_1",
                reconstruction_id=RECONSTRUCTION_ID,
            )

    def test_reconstruction_change_invalidates_old_request(self) -> None:
        request, reconstruction_digest = self.make_request()
        self.approve_both(
            request,
            reconstruction_digest,
            requested_scope=ReconstructionScope.SUMMARY,
        )
        self.controller.append_person_reconstruction(
            self.kira,
            participant_id="kira",
            participant_session_id="kira_private_session_1",
            reflection_text="A newly selected private interpretation.",
            source_label="current_interpretation",
            confidence=0.5,
            recall_strength_delta=0,
            write_origin=ReconstructionWriteOrigin.PRIVATE_PERSON_SELECTION,
        )
        with self.assertRaises(CapabilityError):
            self.issue(
                request,
                reconstruction_digest,
                requested_scope=ReconstructionScope.SUMMARY,
            )

    def test_audit_and_private_ledger_tampering_are_detected(self) -> None:
        controller = KiraLisaReconstructionAccessControllerV2.load_pinned(
            clock=MutableClock()
        )
        controller._audit_records[0]["details"]["custom_policy_accepted"] = True
        with self.assertRaises(IntegrityError):
            controller.verify_audit_chain()

        self.controller.append_person_reconstruction(
            self.kira,
            participant_id="kira",
            participant_session_id="kira_private_session_1",
            reflection_text="Private ledger integrity sentinel.",
            source_label="current_interpretation",
            confidence=0.5,
            recall_strength_delta=0,
            write_origin=ReconstructionWriteOrigin.PRIVATE_PERSON_SELECTION,
        )
        self.controller._ledgers["kira"][0]["reflection_text"] = "tampered"
        with self.assertRaises(IntegrityError):
            self.controller.participant_private_snapshot(
                self.kira,
                participant_id="kira",
                participant_session_id="kira_private_session_1",
                reconstruction_id=RECONSTRUCTION_ID,
            )

    def test_chain_truncation_and_decision_state_rewrite_are_detected(self) -> None:
        controller = KiraLisaReconstructionAccessControllerV2.load_pinned(
            clock=MutableClock()
        )
        controller._audit_records.pop()
        with self.assertRaises(IntegrityError):
            controller.verify_audit_chain()

        self.controller.append_person_reconstruction(
            self.kira,
            participant_id="kira",
            participant_session_id="kira_private_session_1",
            reflection_text="Ledger head seal sentinel.",
            source_label="current_interpretation",
            confidence=0.5,
            recall_strength_delta=0,
            write_origin=ReconstructionWriteOrigin.PRIVATE_PERSON_SELECTION,
        )
        self.controller._ledgers["kira"].pop()
        with self.assertRaises(IntegrityError):
            self.controller.participant_private_snapshot(
                self.kira,
                participant_id="kira",
                participant_session_id="kira_private_session_1",
                reconstruction_id=RECONSTRUCTION_ID,
            )

        # A fresh controller proves a denial cannot be rewritten in private
        # process state while retaining the hash of the denial event.
        self.setUp()
        request, reconstruction_digest = self.make_request()
        self.decide(request, reconstruction_digest, person="kira")
        self.decide(
            request,
            reconstruction_digest,
            person="lisa",
            decision=ParticipantDecision.DENY,
            approved_scope=None,
        )
        response = self.controller._requests[request].responses["lisa"]
        response.decision = ParticipantDecision.APPROVE
        response.approved_scope = ReconstructionScope.SUMMARY
        with self.assertRaises(IntegrityError):
            self.issue(
                request,
                reconstruction_digest,
                requested_scope=ReconstructionScope.SUMMARY,
            )

    def test_model_output_strings_or_mappings_cannot_grant_permission(self) -> None:
        request, reconstruction_digest = self.make_request()
        base = dict(
            participant_id="kira",
            participant_session_id="kira_private_session_1",
            request_id="request_1",
            intended_viewer="real_robert",
            viewer_session_id="robert_session_1",
            requested_scope=ReconstructionScope.SUMMARY,
            reconstruction_digest=reconstruction_digest,
            material_context_digest=self.material_digest,
            approved_scope=ReconstructionScope.SUMMARY,
            approved_zones=(),
            visual_body_exposure_allowed=False,
        )
        with self.assertRaises(DecisionError):
            self.controller.record_participant_decision(
                self.kira, request, decision="approve", **base
            )
        with self.assertRaises(DecisionError):
            self.controller.record_participant_decision(
                self.kira, request, decision={"decision": "approve"}, **base
            )

    def test_direct_model_output_cannot_write_private_reconstruction(self) -> None:
        with self.assertRaises(DecisionError):
            self.controller.append_person_reconstruction(
                self.kira,
                participant_id="kira",
                participant_session_id="kira_private_session_1",
                reflection_text="A model tried to write this directly.",
                source_label="current_interpretation",
                confidence=0.5,
                recall_strength_delta=0,
                write_origin="model_output",
            )
        snapshot = self.controller.participant_private_snapshot(
            self.kira,
            participant_id="kira",
            participant_session_id="kira_private_session_1",
            reconstruction_id=RECONSTRUCTION_ID,
        )
        self.assertEqual(snapshot["records"], [])

    def test_denial_never_issues_a_lease(self) -> None:
        request, reconstruction_digest = self.make_request()
        self.decide(request, reconstruction_digest, person="kira")
        self.decide(
            request,
            reconstruction_digest,
            person="lisa",
            decision=ParticipantDecision.DENY,
            approved_scope=None,
        )
        with self.assertRaises(DecisionError):
            self.issue(
                request,
                reconstruction_digest,
                requested_scope=ReconstructionScope.SUMMARY,
            )

    def test_audit_chain_contains_no_private_reconstruction_text(self) -> None:
        private_text = "PRIVATE_TEXT_MUST_NOT_ENTER_AUDIT"
        self.controller.append_person_reconstruction(
            self.kira,
            participant_id="kira",
            participant_session_id="kira_private_session_1",
            reflection_text=private_text,
            source_label="selected_person_private_recall",
            confidence=0.5,
            recall_strength_delta=0,
            write_origin=ReconstructionWriteOrigin.PRIVATE_PERSON_SELECTION,
        )
        snapshot = self.controller.audit_snapshot()
        self.assertTrue(snapshot["verification"]["verified"])
        self.assertNotIn(private_text, str(snapshot))
        self.assertFalse(snapshot["durable_storage_claimed"])


if __name__ == "__main__":
    unittest.main()
