from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from Core.shared_person_growth_capabilities_v1 import (
    GrowthCapabilityError,
    GrowthLeaseError,
    PersonGrowthSession,
    build_fresh_capability_profile,
    build_temporary_creator_attachment,
    load_policy,
    validate_capability_profile,
    validate_temporary_creator_attachment,
)
from tools.create_temporary_ai_growth_profile_v1 import (
    build_fresh_creator_bundle,
    validate_creator_bundle,
    write_bundle_exclusive,
)


SHA_A = hashlib.sha256(b"a").hexdigest()
SHA_B = hashlib.sha256(b"b").hexdigest()
SHA_C = hashlib.sha256(b"c").hexdigest()


class CounterClock:
    def __init__(self) -> None:
        self.value = 10.0

    def __call__(self) -> float:
        self.value += 1.0
        return self.value


def profile(
    person: str = "person_kira_test",
    candidate: str = "candidate_kira_test",
    profile_id: str = "growth_kira_test",
    nonce: str = SHA_A,
    maturity: str = "confirmed_adult",
) -> dict:
    return build_fresh_capability_profile(
        person_id=person,
        candidate_id=candidate,
        profile_id=profile_id,
        root_nonce_sha256=nonce,
        maturity_status=maturity,
    )


def session_for(value: dict | None = None) -> PersonGrowthSession:
    return PersonGrowthSession(
        profile=value or profile(),
        activation_revision="activation_0001",
        session_nonce_sha256=SHA_B,
        clock=CounterClock(),
    )


class SharedPersonGrowthCapabilityTests(unittest.TestCase):
    def test_policy_is_static_and_never_inherits_person_state(self) -> None:
        policy = load_policy()
        self.assertTrue(policy["capabilities"])
        self.assertTrue(all(not row["live_enabled"] for row in policy["capabilities"].values()))
        forbidden = set(policy["never_inherited_from_another_person"])
        self.assertTrue({"identity", "memories", "private_emotion_state", "maturity_classification", "capability_lease"}.issubset(forbidden))

    def test_fresh_profiles_have_distinct_private_roots_and_no_copied_state(self) -> None:
        first = profile()
        second = profile(
            person="person_lisa_test",
            candidate="candidate_lisa_test",
            profile_id="growth_lisa_test",
            nonce=SHA_B,
        )
        self.assertNotEqual(
            set(first["private_state_roots"].values()),
            set(second["private_state_roots"].values()),
        )
        self.assertEqual(first["inheritance"]["copied_private_records"], 0)
        self.assertIsNone(first["inheritance"]["source_person_id"])
        self.assertFalse(any(first["runtime"].values()))

    def test_maturity_fails_closed_and_never_adds_anatomy_or_consent(self) -> None:
        for maturity in ("unresolved", "non_adult"):
            value = profile(maturity=maturity)
            self.assertFalse(value["maturity"]["full_adult_curriculum_eligible"])
            self.assertEqual(value["maturity"]["default_body_lane"], "doll_safe_non_anatomical")
            self.assertFalse(value["maturity"]["adult_anatomy_added"])
            self.assertFalse(value["maturity"]["consent_granted"])
        adult = profile()
        self.assertTrue(adult["maturity"]["full_adult_curriculum_eligible"])
        self.assertFalse(adult["maturity"]["full_adult_curriculum_delivered"])
        self.assertFalse(adult["maturity"]["adult_anatomy_added"])
        self.assertFalse(adult["maturity"]["consent_granted"])

    def test_profile_tampering_and_cross_namespace_roots_fail(self) -> None:
        value = profile()
        value["runtime"]["model_connected"] = True
        with self.assertRaisesRegex(GrowthCapabilityError, "runtime"):
            validate_capability_profile(value)
        value = profile()
        value["private_state_roots"]["emotion"] = "Data/person_private/" + "f" * 32 + "/emotion"
        unsigned = copy.deepcopy(value)
        unsigned.pop("profile_fingerprint_sha256")
        value["profile_fingerprint_sha256"] = hashlib.sha256(
            json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        with self.assertRaisesRegex(GrowthCapabilityError, "cross person"):
            validate_capability_profile(value)

    def test_present_fact_learning_review_and_emotion_are_separate_truths(self) -> None:
        growth = session_for()
        lease = growth.lease
        present = growth.record_present_fact(
            lease,
            present_event_id="present_0001",
            factual_summary="Robert said the current test is unattended.",
            source_kind="owner_statement",
            source_receipt_sha256=SHA_A,
            observed_at_utc="2026-08-10T20:00:00Z",
            expires_at_utc="2026-08-10T21:00:00Z",
        )
        proposal = growth.propose_learning(
            lease,
            proposal_id="proposal_0001",
            proposed_claim="Robert authorized unattended log review for this exact test.",
            source_present_event_ids=("present_0001",),
            privacy_class="person_private",
            contradiction_state="no_conflict_found",
        )
        review = growth.review_learning_proposal(
            lease,
            proposal_id="proposal_0001",
            decision="accept_for_separate_memory_review",
            review_authority_receipt_sha256=SHA_B,
        )
        emotion = growth.record_causal_emotion(
            lease,
            emotion_event_id="emotion_0001",
            cause_present_event_ids=("present_0001",),
            possible_interpretations=("The test may help improve future conversations.",),
            selected_appraisal="This is useful but still needs verification.",
            emotion_label="cautious_hope",
            intensity=0.4,
            confidence=0.7,
            unresolved=True,
        )
        self.assertTrue(present["present_context_only"])
        self.assertEqual(proposal["proposal_state"], "PROPOSED_NOT_MEMORY")
        self.assertFalse(review["memory_written_by_this_review"])
        self.assertEqual(emotion["visibility"], "person_private")
        for field in ("physiological_response_recorded", "private_desire_recorded", "preference_recorded", "consent_recorded", "health_state_recorded"):
            self.assertFalse(emotion[field])
        self.assertTrue(all(not event["durable_memory_mutated"] for event in growth.private_records(lease)))

    def test_event_chain_is_append_only_and_public_snapshot_hides_payload(self) -> None:
        growth = session_for()
        lease = growth.lease
        growth.record_present_fact(
            lease,
            present_event_id="present_0001",
            factual_summary="private marker never appears in public snapshot",
            source_kind="reviewed_memory",
            source_receipt_sha256=SHA_A,
            observed_at_utc="2026-08-10T20:00:00Z",
            expires_at_utc="2026-08-10T20:05:00Z",
        )
        records = growth.private_records(lease)
        self.assertEqual(records[0]["previous_event_sha256"], "0" * 64)
        snapshot = growth.public_snapshot(lease)
        self.assertFalse(snapshot["private_payload_exposed"])
        self.assertNotIn("private marker", json.dumps(snapshot))
        self.assertEqual(snapshot["head_event_sha256"], records[-1]["event_sha256"])

    def test_wrong_lease_replay_duplicate_and_unknown_sources_fail(self) -> None:
        first = session_for()
        second = session_for(
            profile("person_other_test", "candidate_other_test", "growth_other_test", SHA_C)
        )
        with self.assertRaises(GrowthLeaseError):
            first.public_snapshot(second.lease)
        first.record_present_fact(
            first.lease,
            present_event_id="present_0001",
            factual_summary="one fact",
            source_kind="tool_receipt",
            source_receipt_sha256=SHA_A,
            observed_at_utc="2026-08-10T20:00:00Z",
            expires_at_utc="2026-08-10T20:10:00Z",
        )
        with self.assertRaisesRegex(GrowthCapabilityError, "already used"):
            first.record_present_fact(
                first.lease,
                present_event_id="present_0001",
                factual_summary="duplicate",
                source_kind="tool_receipt",
                source_receipt_sha256=SHA_A,
                observed_at_utc="2026-08-10T20:00:00Z",
                expires_at_utc="2026-08-10T20:10:00Z",
            )
        with self.assertRaisesRegex(GrowthCapabilityError, "unknown present"):
            first.propose_learning(
                first.lease,
                proposal_id="proposal_bad",
                proposed_claim="unsupported",
                source_present_event_ids=("present_missing",),
                privacy_class="person_private",
                contradiction_state="not_checked",
            )

    def test_deactivation_purges_only_memory_session_and_revokes_lease(self) -> None:
        growth = session_for()
        lease = growth.lease
        growth.record_present_fact(
            lease,
            present_event_id="present_0001",
            factual_summary="temporary fact",
            source_kind="owner_statement",
            source_receipt_sha256=SHA_A,
            observed_at_utc="2026-08-10T20:00:00Z",
            expires_at_utc="2026-08-10T20:10:00Z",
        )
        result = growth.deactivate(lease)
        self.assertEqual(result["purged_memory_only_event_count"], 1)
        self.assertFalse(result["durable_memory_deleted"])
        self.assertFalse(result["identity_changed"])
        with self.assertRaises(GrowthLeaseError):
            growth.public_snapshot(lease)

    def test_creator_attachment_is_inert_and_exactly_bound(self) -> None:
        attachment = build_temporary_creator_attachment(
            candidate_id="new_person_test",
            display_name="New Person",
            person_id="person_new_person_test",
            profile_id="growth_new_person_test",
            root_nonce_sha256=SHA_A,
            maturity_status="unresolved",
        )
        checked = validate_temporary_creator_attachment(attachment)
        self.assertEqual(checked["candidate_id"], "new_person_test")
        self.assertFalse(checked["creator_truth"]["existing_person_profile_copied"])
        self.assertFalse(checked["creator_truth"]["activation_allowed"])
        tampered = copy.deepcopy(attachment)
        tampered["candidate_id"] = "other_candidate"
        with self.assertRaises(GrowthCapabilityError):
            validate_temporary_creator_attachment(tampered)

    def test_creator_bundle_requires_classification_receipt_or_unresolved(self) -> None:
        unresolved = build_fresh_creator_bundle(
            candidate_id="new_person_test",
            display_name="New Person",
            person_id="person_new_person_test",
            profile_id="growth_new_person_test",
            root_nonce_sha256=SHA_A,
        )
        self.assertTrue(validate_creator_bundle(unresolved))
        with self.assertRaisesRegex(GrowthCapabilityError, "classification_receipt"):
            build_fresh_creator_bundle(
                candidate_id="new_adult_test",
                display_name="New Adult",
                maturity_status="confirmed_adult",
                person_id="person_new_adult_test",
                profile_id="growth_new_adult_test",
                root_nonce_sha256=SHA_A,
            )
        adult = build_fresh_creator_bundle(
            candidate_id="new_adult_test",
            display_name="New Adult",
            maturity_status="confirmed_adult",
            maturity_classification_receipt_sha256=SHA_C,
            person_id="person_new_adult_test",
            profile_id="growth_new_adult_test",
            root_nonce_sha256=SHA_A,
        )
        self.assertTrue(adult["attachment"]["growth_profile"]["maturity"]["full_adult_curriculum_eligible"])
        self.assertFalse(adult["attachment"]["growth_profile"]["maturity"]["full_adult_curriculum_delivered"])

    def test_creator_exclusive_write_never_modifies_existing_candidate_files(self) -> None:
        bundle = build_fresh_creator_bundle(
            candidate_id="new_person_test",
            display_name="New Person",
            person_id="person_new_person_test",
            profile_id="growth_new_person_test",
            root_nonce_sha256=SHA_A,
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            candidate = root / "TemporaryAI" / "candidates" / "new_person_test"
            candidate.mkdir(parents=True)
            existing = candidate / "temporary_ai_profile.json"
            existing.write_text('{"preserved":true}\n', encoding="utf-8")
            before = existing.read_bytes()
            output = write_bundle_exclusive(bundle, project_root=root)
            self.assertTrue(output.is_file())
            self.assertEqual(existing.read_bytes(), before)
            with self.assertRaises(FileExistsError):
                write_bundle_exclusive(bundle, project_root=root)

    def test_private_strings_are_not_inherited_into_fresh_creator_document(self) -> None:
        marker = "private_kira_memory_that_must_not_copy"
        bundle = build_fresh_creator_bundle(
            candidate_id="new_person_test",
            display_name="New Person",
            person_id="person_new_person_test",
            profile_id="growth_new_person_test",
            root_nonce_sha256=SHA_A,
        )
        self.assertNotIn(marker, json.dumps(bundle, ensure_ascii=False))
        self.assertEqual(bundle["attachment"]["growth_profile"]["inheritance"]["copied_private_records"], 0)


if __name__ == "__main__":
    unittest.main()

