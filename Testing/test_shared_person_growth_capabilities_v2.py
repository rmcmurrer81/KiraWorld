from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import Core.shared_person_growth_capabilities_v2 as core_v2
from Core.shared_person_growth_capabilities_v2 import (
    EvidenceReceiptHandle,
    GrowthAuthorityError,
    GrowthCapabilityError,
    GrowthLeaseError,
    GrowthLeaseHandle,
    GrowthReplayError,
    MaturityAuthorityHandle,
    PersonGrowthSession,
    ProtectedGrowthController,
    build_fresh_capability_profile,
    load_policy,
    validate_capability_profile,
)
from tools.create_temporary_ai_growth_profile_v2 import (
    build_fresh_creator_bundle,
    validate_creator_bundle,
    write_bundle_exclusive,
)


ROOT = Path(__file__).resolve().parents[1]
SECRET_A = b"controller-a-authority-secret!!" + b"A" * 8
SECRET_B = b"controller-b-authority-secret!!" + b"B" * 8
SHA_A = hashlib.sha256(b"a").hexdigest()
SHA_B = hashlib.sha256(b"b").hexdigest()
SHA_C = hashlib.sha256(b"c").hexdigest()
ZERO_SHA = "0" * 64

V1_PROTECTED = {
    "Data/foundation/shared_person_growth_capabilities_v1.json": (
        3030,
        "76cf318bef763acdfd06f417af90449aa72875267f60d1a62217f81ec61f1a4f",
    ),
    "Core/shared_person_growth_capabilities_v1.py": (
        29508,
        "2bda38a21409c46f6a2626925d7917dd1c778c58572cf04633828438777e9806",
    ),
    "tools/create_temporary_ai_growth_profile_v1.py": (
        8950,
        "ef307c784d6a80cd98530bc2d8cadef7bab736b23f268a6408c211e7dd766869",
    ),
    "TemporaryAI/config/shared_person_growth_capability_template_v1.json": (
        1404,
        "9146baabec5e433ae0e89f211c6944b182a6a6e9cf840073cdad548008116686",
    ),
    "Testing/test_shared_person_growth_capabilities_v1.py": (
        13815,
        "4476c5ed263e902cba97ac1e124e3b5972a46d463868db95112ecc7523bf2a11",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v1_static_implementation/attempt_01/CHECKPOINT.md": (
        3215,
        "35a4c28ec0263df842f1a9f302763cc63d7a29b12018771c4114318226196725",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v1_fresh_static_audit/attempt_01/INDEPENDENT_HOSTILE_PROBES.py": (
        11362,
        "13461f26a87b596444ec0b5279961bd9d16e4b3b60b996af13b08f94e341d3bd",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v1_fresh_static_audit/attempt_01/STATIC_AUDIT_RESULT.json": (
        7609,
        "4f0384e0af76710999443be906f81ac0d04898314676eed8aeb01f294b5843f5",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v1_fresh_static_audit/attempt_01/AUDIT_DECISION.json": (
        1008,
        "b6dd63618483298e144477218649764f996ba89aa2df6b9be94de0be6c75b298",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v1_fresh_static_audit/attempt_01/CHECKPOINT.md": (
        6182,
        "ebadc6bdc21247b2a75eb9798a6dfb4f9988477adddae3827080b42a191f0e04",
    ),
}


class CounterClock:
    def __init__(self) -> None:
        self.value = 10.0

    def __call__(self) -> float:
        self.value += 1.0
        return self.value


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def resign_profile(value: dict) -> dict:
    unsigned = copy.deepcopy(value)
    unsigned.pop("profile_fingerprint_sha256", None)
    value["profile_fingerprint_sha256"] = canonical_sha(unsigned)
    return value


def resign_attachment(value: dict) -> dict:
    unsigned = copy.deepcopy(value)
    unsigned.pop("attachment_sha256", None)
    value["attachment_sha256"] = canonical_sha(unsigned)
    return value


def resign_bundle(value: dict) -> dict:
    unsigned = copy.deepcopy(value)
    unsigned.pop("bundle_sha256", None)
    value["bundle_sha256"] = canonical_sha(unsigned)
    return value


def controller_a() -> ProtectedGrowthController:
    return ProtectedGrowthController(
        controller_id="controller_growth_v2_a",
        authority_secret=SECRET_A,
    )


def controller_b() -> ProtectedGrowthController:
    return ProtectedGrowthController(
        controller_id="controller_growth_v2_b",
        authority_secret=SECRET_B,
    )


def binding(suffix: str = "a") -> dict[str, str]:
    return {
        "person_id": f"person_growth_v2_{suffix}",
        "candidate_id": f"candidate_growth_v2_{suffix}",
        "profile_id": f"profile_growth_v2_{suffix}",
    }


def unresolved_profile(
    controller: ProtectedGrowthController,
    suffix: str = "a",
    nonce: str = SHA_A,
) -> dict:
    row = binding(suffix)
    return build_fresh_capability_profile(
        **row,
        root_nonce_sha256=nonce,
        authority_controller=controller,
    )


def issue_evidence(
    controller: ProtectedGrowthController,
    secret: bytes,
    *,
    row: dict[str, str],
    operation: str,
    purpose: str,
    source_kind: str = "owner_statement",
    artifact: str = SHA_A,
) -> EvidenceReceiptHandle:
    return controller.issue_evidence_receipt(
        authority_secret=secret,
        operation_id=operation,
        **row,
        purpose=purpose,
        source_kind=source_kind,
        source_artifact_sha256=artifact,
        source_revision=f"revision_{operation.replace(':', '_')}",
    )


def issue_maturity(
    controller: ProtectedGrowthController,
    secret: bytes,
    *,
    row: dict[str, str],
    status: str,
    suffix: str,
) -> MaturityAuthorityHandle:
    source = issue_evidence(
        controller,
        secret,
        row=row,
        operation=f"maturity_source_{suffix}",
        purpose="maturity_classification_source",
        source_kind="classification_receipt",
        artifact=SHA_C,
    )
    return controller.issue_maturity_classification(
        authority_secret=secret,
        operation_id=f"maturity_issue_{suffix}",
        **row,
        status=status,
        source_evidence=source,
        classification_revision=f"classification_{suffix}",
    )


def open_session(
    controller: ProtectedGrowthController,
    secret: bytes,
    profile: dict,
    *,
    suffix: str,
    nonce: str = SHA_B,
) -> PersonGrowthSession:
    return controller.open_session(
        authority_secret=secret,
        profile=profile,
        activation_revision=f"activation_{suffix}",
        session_nonce_sha256=nonce,
        session_open_operation_id=f"session_open_{suffix}",
        clock=CounterClock(),
    )


class SharedPersonGrowthCapabilitiesV2Tests(unittest.TestCase):
    def test_00_v1_and_rejection_audit_are_exactly_preserved(self) -> None:
        for relative, (size, digest) in V1_PROTECTED.items():
            path = ROOT / relative
            self.assertEqual(path.stat().st_size, size, relative)
            self.assertEqual(sha_file(path), digest, relative)

    def test_01_policy_is_closed_static_and_truthful_about_initiative(self) -> None:
        policy = load_policy()
        self.assertTrue(all(not row["live_enabled"] for row in policy["capabilities"].values()))
        initiative = policy["capabilities"]["bounded_initiative"]
        self.assertEqual(initiative["stage"], "DESIGN_ONLY")
        self.assertFalse(initiative["implemented_by_core"])
        self.assertFalse(hasattr(PersonGrowthSession, "propose_initiative"))
        self.assertFalse(hasattr(PersonGrowthSession, "record_initiative"))
        tampered = json.loads((ROOT / "Data/foundation/shared_person_growth_capabilities_v2.json").read_text(encoding="utf-8"))
        tampered["unknown_private_policy"] = True
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "policy.json"
            path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaisesRegex(GrowthCapabilityError, "schema mismatch"):
                load_policy(path)
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "duplicate_policy.json"
            original = (ROOT / "Data/foundation/shared_person_growth_capabilities_v2.json").read_text(
                encoding="utf-8"
            )
            duplicate = original.replace(
                '  "schema": "kira.shared_person_growth_capabilities_policy.v2",',
                '  "schema": "kira.shared_person_growth_capabilities_policy.v2",\n'
                '  "schema": "kira.shared_person_growth_capabilities_policy.v2",',
                1,
            )
            path.write_text(duplicate, encoding="utf-8")
            with self.assertRaisesRegex(GrowthCapabilityError, "duplicate JSON key"):
                load_policy(path)

    def test_02_lease_is_controller_owned_identity_and_cross_session_replay_fails(self) -> None:
        controller = controller_a()
        profile = unresolved_profile(controller)
        first = open_session(controller, SECRET_A, profile, suffix="lease_first", nonce=SHA_A)
        second = open_session(controller, SECRET_A, profile, suffix="lease_second", nonce=SHA_B)
        self.assertIsNot(first.lease, second.lease)
        with self.assertRaises(GrowthLeaseError):
            first.public_snapshot(second.lease)
        forged = object.__new__(GrowthLeaseHandle)
        with self.assertRaises(GrowthLeaseError):
            first.public_snapshot(forged)
        with self.assertRaises(TypeError):
            GrowthLeaseHandle()
        with self.assertRaises(TypeError):
            copy.copy(first.lease)
        with self.assertRaises(GrowthReplayError):
            controller.open_session(
                authority_secret=SECRET_A,
                profile=profile,
                activation_revision="activation_lease_first",
                session_nonce_sha256=SHA_A,
                session_open_operation_id="session_open_duplicate_binding",
                clock=CounterClock(),
            )
        with self.assertRaises(GrowthAuthorityError):
            PersonGrowthSession(
                _construction_key=object(),
                controller=controller,
                lease=forged,
                profile=profile,
                activation_revision="activation_forged",
                session_nonce_sha256=SHA_A,
                clock=CounterClock(),
                max_events=4,
            )

    def test_03_zero_phantom_and_wrong_secret_evidence_are_rejected(self) -> None:
        controller = controller_a()
        row = binding()
        with self.assertRaisesRegex(GrowthCapabilityError, "zero SHA"):
            issue_evidence(
                controller,
                SECRET_A,
                row=row,
                operation="zero_receipt_issue",
                purpose="present_source",
                artifact=ZERO_SHA,
            )
        with self.assertRaises(GrowthAuthorityError):
            issue_evidence(
                controller,
                SECRET_B,
                row=row,
                operation="wrong_secret_issue",
                purpose="present_source",
            )
        profile = unresolved_profile(controller, "plain_digest")
        session = open_session(
            controller,
            SECRET_A,
            profile,
            suffix="plain_digest",
            nonce=SHA_A,
        )
        with self.assertRaises(GrowthAuthorityError):
            session.record_present_fact(
                session.lease,
                present_event_id="present_plain_zero_digest",
                factual_summary="A plain digest is not a receipt capability.",
                source_kind="owner_statement",
                source_receipt=ZERO_SHA,  # type: ignore[arg-type]
                observed_at_utc="2026-08-10T20:00:00Z",
                expires_at_utc="2026-08-10T20:10:00Z",
            )

    def test_04_evidence_is_exact_bound_single_use_and_cross_person_safe(self) -> None:
        controller = controller_a()
        profile_a = unresolved_profile(controller, "a", SHA_A)
        profile_b = unresolved_profile(controller, "b", SHA_B)
        session_a = open_session(controller, SECRET_A, profile_a, suffix="evidence_a", nonce=SHA_A)
        session_b = open_session(controller, SECRET_A, profile_b, suffix="evidence_b", nonce=SHA_B)
        receipt = issue_evidence(
            controller,
            SECRET_A,
            row=binding("a"),
            operation="present_receipt_exact_a",
            purpose="present_source",
            source_kind="tool_receipt",
        )
        with self.assertRaises(GrowthAuthorityError):
            session_b.record_present_fact(
                session_b.lease,
                present_event_id="present_cross_person",
                factual_summary="must fail",
                source_kind="tool_receipt",
                source_receipt=receipt,
                observed_at_utc="2026-08-10T20:00:00Z",
                expires_at_utc="2026-08-10T20:10:00Z",
            )
        event = session_a.record_present_fact(
            session_a.lease,
            present_event_id="present_exact_a",
            factual_summary="exact source binding",
            source_kind="tool_receipt",
            source_receipt=receipt,
            observed_at_utc="2026-08-10T20:00:00Z",
            expires_at_utc="2026-08-10T20:10:00Z",
        )
        self.assertEqual(event["source_artifact_sha256"], SHA_A)
        with self.assertRaises(GrowthReplayError):
            session_a.record_present_fact(
                session_a.lease,
                present_event_id="present_reused_receipt",
                factual_summary="must fail",
                source_kind="tool_receipt",
                source_receipt=receipt,
                observed_at_utc="2026-08-10T20:00:00Z",
                expires_at_utc="2026-08-10T20:10:00Z",
            )
        other_controller_receipt = issue_evidence(
            controller_b(),
            SECRET_B,
            row=binding("a"),
            operation="other_controller_receipt",
            purpose="present_source",
            source_kind="tool_receipt",
        )
        with self.assertRaises(GrowthAuthorityError):
            session_a.record_present_fact(
                session_a.lease,
                present_event_id="present_other_controller",
                factual_summary="must fail",
                source_kind="tool_receipt",
                source_receipt=other_controller_receipt,
                observed_at_utc="2026-08-10T20:00:00Z",
                expires_at_utc="2026-08-10T20:10:00Z",
            )

    def test_05_direct_caller_cannot_unlock_classified_maturity(self) -> None:
        controller = controller_a()
        row = binding("direct")
        with self.assertRaises(TypeError):
            build_fresh_capability_profile(
                **row,
                root_nonce_sha256=SHA_A,
                authority_controller=controller,
                maturity_status="confirmed_adult",
            )
        fake = object.__new__(MaturityAuthorityHandle)
        with self.assertRaises(GrowthAuthorityError):
            build_fresh_capability_profile(
                **row,
                root_nonce_sha256=SHA_A,
                authority_controller=controller,
                maturity_authority=fake,
            )
        unresolved = build_fresh_capability_profile(
            **row,
            root_nonce_sha256=SHA_A,
            authority_controller=controller,
        )
        forged = copy.deepcopy(unresolved)
        forged["maturity"].update(
            {
                "status": "confirmed_adult",
                "classification_receipt_sha256": SHA_C,
                "classification_controller_id": controller.controller_id,
                "full_adult_curriculum_eligible": True,
                "default_body_lane": "separately_selected_adult_body_pending",
            }
        )
        resign_profile(forged)
        with self.assertRaises(GrowthAuthorityError):
            validate_capability_profile(forged)
        with self.assertRaises(GrowthAuthorityError):
            validate_capability_profile(forged, authority_controller=controller)

    def test_06_protected_maturity_is_nonzero_exact_bound_and_single_use(self) -> None:
        controller = controller_a()
        row = binding("adult")
        maturity = issue_maturity(
            controller,
            SECRET_A,
            row=row,
            status="confirmed_adult",
            suffix="adult",
        )
        profile = build_fresh_capability_profile(
            **row,
            root_nonce_sha256=SHA_A,
            authority_controller=controller,
            maturity_authority=maturity,
        )
        self.assertTrue(profile["maturity"]["full_adult_curriculum_eligible"])
        self.assertFalse(profile["maturity"]["consent_granted"])
        self.assertFalse(profile["maturity"]["adult_anatomy_added"])
        self.assertNotEqual(profile["maturity"]["classification_receipt_sha256"], ZERO_SHA)
        with self.assertRaises(GrowthReplayError):
            build_fresh_capability_profile(
                **row,
                root_nonce_sha256=SHA_B,
                authority_controller=controller,
                maturity_authority=maturity,
            )
        with self.assertRaises(GrowthAuthorityError):
            validate_capability_profile(profile)
        with self.assertRaises(GrowthAuthorityError):
            validate_capability_profile(profile, authority_controller=controller_b())

    def test_07_truth_maturity_and_private_profile_schemas_are_closed(self) -> None:
        controller = controller_a()
        value = unresolved_profile(controller, "closed")
        extra = copy.deepcopy(value)
        extra["copied_private_payload"] = {"source_person_id": "person_other"}
        resign_profile(extra)
        with self.assertRaisesRegex(GrowthCapabilityError, "schema mismatch"):
            validate_capability_profile(extra)
        truth = copy.deepcopy(value)
        truth["truth_boundaries"]["body_response_is_not_desire_or_consent"] = False
        resign_profile(truth)
        with self.assertRaisesRegex(GrowthCapabilityError, "closed truth"):
            validate_capability_profile(truth)
        inferred = copy.deepcopy(value)
        inferred["maturity"]["classification_inferred_by_this_module"] = True
        resign_profile(inferred)
        with self.assertRaisesRegex(GrowthCapabilityError, "must not infer"):
            validate_capability_profile(inferred)
        numeric_boolean = copy.deepcopy(value)
        numeric_boolean["truth_boundaries"]["body_response_is_not_desire_or_consent"] = 1
        resign_profile(numeric_boolean)
        with self.assertRaisesRegex(GrowthCapabilityError, "closed truth"):
            validate_capability_profile(numeric_boolean)
        with self.assertRaises(AttributeError):
            controller.controller_id = "controller_rebound_by_caller"

    def test_08_creator_rejects_unknown_private_payload_at_every_layer(self) -> None:
        controller = controller_a()
        bundle = build_fresh_creator_bundle(
            candidate_id="creator_closed_v2",
            display_name="Creator Closed",
            authority_controller=controller,
            person_id="person_creator_closed_v2",
            profile_id="profile_creator_closed_v2",
            root_nonce_sha256=SHA_A,
        )
        top = copy.deepcopy(bundle)
        top["copied_private_payload"] = {"source_person_id": "person_other"}
        resign_bundle(top)
        with self.assertRaisesRegex(GrowthCapabilityError, "exact schema"):
            validate_creator_bundle(top)
        attachment = copy.deepcopy(bundle)
        attachment["attachment"]["copied_private_payload"] = {"memory": "private"}
        resign_attachment(attachment["attachment"])
        resign_bundle(attachment)
        with self.assertRaisesRegex(GrowthCapabilityError, "schema mismatch"):
            validate_creator_bundle(attachment)
        nested = copy.deepcopy(bundle)
        nested["attachment"]["growth_profile"]["copied_private_payload"] = {
            "memory": "private"
        }
        resign_profile(nested["attachment"]["growth_profile"])
        resign_attachment(nested["attachment"])
        resign_bundle(nested)
        with self.assertRaisesRegex(GrowthCapabilityError, "schema mismatch"):
            validate_creator_bundle(nested)
        numeric_boolean = copy.deepcopy(bundle)
        numeric_boolean["write_contract"]["exclusive_new_file_only"] = 1
        resign_bundle(numeric_boolean)
        with self.assertRaisesRegex(GrowthCapabilityError, "boundary drifted"):
            validate_creator_bundle(numeric_boolean)

    def test_09_creator_exclusive_write_readback_and_inactive_truth(self) -> None:
        controller = controller_a()
        bundle = build_fresh_creator_bundle(
            candidate_id="creator_write_v2",
            display_name="Creator Write",
            authority_controller=controller,
            person_id="person_creator_write_v2",
            profile_id="profile_creator_write_v2",
            root_nonce_sha256=SHA_A,
        )
        self.assertEqual(bundle["maturity_authority"]["status"], "unresolved")
        self.assertFalse(bundle["write_contract"]["private_person_data_copied"])
        self.assertFalse(bundle["attachment"]["growth_profile"]["runtime"]["activated"])
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            candidate = root / "TemporaryAI" / "candidates" / "creator_write_v2"
            candidate.mkdir(parents=True)
            existing = candidate / "temporary_ai_profile.json"
            existing.write_bytes(b'{"preserved":true}\n')
            before = existing.read_bytes()
            output = write_bundle_exclusive(
                bundle,
                project_root=root,
                authority_controller=controller,
            )
            self.assertEqual(existing.read_bytes(), before)
            observed = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(observed, bundle)
            with self.assertRaises(FileExistsError):
                write_bundle_exclusive(
                    bundle,
                    project_root=root,
                    authority_controller=controller,
                )

    def test_10_duplicate_emotion_and_controller_operation_replay_are_rejected(self) -> None:
        controller = controller_a()
        profile = unresolved_profile(controller, "emotion")
        session = open_session(controller, SECRET_A, profile, suffix="emotion", nonce=SHA_A)
        receipt = issue_evidence(
            controller,
            SECRET_A,
            row=binding("emotion"),
            operation="emotion_present_receipt",
            purpose="present_source",
        )
        session.record_present_fact(
            session.lease,
            present_event_id="present_emotion_v2",
            factual_summary="one bounded cause",
            source_kind="owner_statement",
            source_receipt=receipt,
            observed_at_utc="2026-08-10T20:00:00Z",
            expires_at_utc="2026-08-10T20:10:00Z",
        )
        kwargs = {
            "emotion_event_id": "emotion_unique_v2",
            "cause_present_event_ids": ("present_emotion_v2",),
            "possible_interpretations": ("One possible interpretation.",),
            "selected_appraisal": "A bounded appraisal.",
            "emotion_label": "curiosity",
            "intensity": 0.3,
            "confidence": 0.6,
            "unresolved": True,
        }
        session.record_causal_emotion(session.lease, **kwargs)
        with self.assertRaises(GrowthReplayError):
            session.record_causal_emotion(session.lease, **kwargs)
        with self.assertRaises(GrowthReplayError):
            issue_evidence(
                controller,
                SECRET_A,
                row=binding("emotion"),
                operation="emotion_present_receipt",
                purpose="present_source",
            )

    def test_11_learning_review_remains_not_memory_and_consent_is_separate(self) -> None:
        controller = controller_a()
        row = binding("learning")
        profile = unresolved_profile(controller, "learning")
        session = open_session(controller, SECRET_A, profile, suffix="learning", nonce=SHA_A)
        present_receipt = issue_evidence(
            controller,
            SECRET_A,
            row=row,
            operation="learning_present_receipt",
            purpose="present_source",
            source_kind="reviewed_memory",
        )
        session.record_present_fact(
            session.lease,
            present_event_id="present_learning_v2",
            factual_summary="A source-bound temporary fact.",
            source_kind="reviewed_memory",
            source_receipt=present_receipt,
            observed_at_utc="2026-08-10T20:00:00Z",
            expires_at_utc="2026-08-10T20:10:00Z",
        )
        proposal = session.propose_learning(
            session.lease,
            proposal_id="proposal_learning_v2",
            proposed_claim="A proposal that is not memory.",
            source_present_event_ids=("present_learning_v2",),
            privacy_class="person_private",
            contradiction_state="not_checked",
        )
        review_receipt = issue_evidence(
            controller,
            SECRET_A,
            row=row,
            operation="learning_review_receipt",
            purpose="learning_review",
            source_kind="correction_receipt",
            artifact=SHA_B,
        )
        review = session.review_learning_proposal(
            session.lease,
            review_event_id="review_learning_v2",
            proposal_id="proposal_learning_v2",
            decision="accept_for_separate_memory_review",
            review_authority_receipt=review_receipt,
        )
        self.assertEqual(proposal["proposal_state"], "PROPOSED_NOT_MEMORY")
        self.assertFalse(review["memory_written_by_this_review"])
        self.assertTrue(review["separate_memory_writer_still_required"])
        self.assertTrue(all(not row["durable_memory_mutated"] for row in session.private_records(session.lease)))
        self.assertFalse(profile["maturity"]["consent_granted"])

    def test_12_cas_readback_is_monotonic_digest_only_and_deactivation_revokes(self) -> None:
        controller = controller_a()
        profile = unresolved_profile(controller, "cas")
        session = open_session(controller, SECRET_A, profile, suffix="cas", nonce=SHA_A)
        before = session.public_snapshot(session.lease)
        self.assertEqual(before["controller_revision"], 0)
        receipt = issue_evidence(
            controller,
            SECRET_A,
            row=binding("cas"),
            operation="cas_present_receipt",
            purpose="present_source",
            source_kind="tool_receipt",
        )
        event = session.record_present_fact(
            session.lease,
            present_event_id="present_cas_v2",
            factual_summary="CAS readback fact.",
            source_kind="tool_receipt",
            source_receipt=receipt,
            observed_at_utc="2026-08-10T20:00:00Z",
            expires_at_utc="2026-08-10T20:10:00Z",
        )
        after = session.public_snapshot(session.lease)
        self.assertEqual(after["controller_revision"], 1)
        self.assertEqual(after["controller_head_sha256"], event["controller_commit_sha256"])
        protected = controller.protected_audit_snapshot(authority_secret=SECRET_A)
        self.assertFalse(protected["private_payload_exposed"])
        result = session.deactivate(
            session.lease,
            close_operation_id="session_close_cas",
        )
        self.assertEqual(result["purged_memory_only_event_count"], 1)
        with self.assertRaises(GrowthLeaseError):
            session.public_snapshot(session.lease)
        with self.assertRaises(GrowthAuthorityError):
            controller.protected_audit_snapshot(authority_secret=SECRET_B)

    def test_13_creator_classified_path_requires_exact_connected_controller(self) -> None:
        controller = controller_a()
        row = {
            "person_id": "person_creator_adult_v2",
            "candidate_id": "creator_adult_v2",
            "profile_id": "profile_creator_adult_v2",
        }
        maturity = issue_maturity(
            controller,
            SECRET_A,
            row=row,
            status="confirmed_adult",
            suffix="creator_adult",
        )
        bundle = build_fresh_creator_bundle(
            candidate_id=row["candidate_id"],
            display_name="Creator Adult",
            authority_controller=controller,
            maturity_authority=maturity,
            person_id=row["person_id"],
            profile_id=row["profile_id"],
            root_nonce_sha256=SHA_A,
        )
        self.assertTrue(bundle["attachment"]["growth_profile"]["maturity"]["full_adult_curriculum_eligible"])
        self.assertFalse(bundle["attachment"]["growth_profile"]["maturity"]["consent_granted"])
        with self.assertRaises(GrowthAuthorityError):
            validate_creator_bundle(bundle)
        with self.assertRaises(GrowthAuthorityError):
            validate_creator_bundle(bundle, authority_controller=controller_b())
        with self.assertRaises(TypeError):
            build_fresh_creator_bundle(
                candidate_id="creator_plain_digest_v2",
                display_name="Plain Digest",
                authority_controller=controller,
                maturity_status="confirmed_adult",
                maturity_classification_receipt_sha256=SHA_C,
            )

    def test_14_template_is_static_closed_and_has_no_private_payload_lane(self) -> None:
        template = json.loads(
            (ROOT / "TemporaryAI/config/shared_person_growth_capability_template_v2.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            set(template),
            {
                "schema",
                "status",
                "policy_path",
                "core_path",
                "creator_successor_path",
                "output_name",
                "new_person_defaults",
                "protected_authority",
                "fresh_per_person_values",
                "never_copy",
                "promotion_gate",
            },
        )
        self.assertFalse(template["promotion_gate"]["current_shared_enablement_allowed"])
        self.assertIn("unknown_private_payload", template["never_copy"])
        self.assertTrue(template["protected_authority"]["plain_digest_is_not_authority"])


if __name__ == "__main__":
    unittest.main()
