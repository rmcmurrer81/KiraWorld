from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from Core import resident_media_voluntary_gate_v5 as v5
from Core import resident_media_voluntary_gate_v6 as v6
from Testing.test_resident_media_voluntary_gate_v5 import (
    PARENT_PROCESS_SHA,
    SECRET,
    catalog,
    presentation_observation,
)


SESSION = "session_" + "6" * 32
ISSUER = "resident_media_parent_v6"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class StaticProtectedAnchorV6(v6.ProtectedAnchorBackendV6):
    """Static test double; never a qualifying live protected backend."""

    def __init__(self) -> None:
        self.sessions: dict[str, dict] = {}
        self.v6_sessions: dict[str, dict] = {}
        self.catalogs: dict[str, dict] = {}
        self._identity = sha("separate-static-test-anchor-v6")

    @property
    def backend_identity_sha256(self) -> str:
        return self._identity

    def authorize(self, accepted) -> None:
        self.catalogs[accepted.sha256] = {
            "schema": "kira.resident_media_catalog_authorization.v5",
            "catalog_sha256": accepted.sha256,
            "authoritative_source_policy_sha256": v5.AUTHORITATIVE_SOURCE_POLICY_SHA256,
            "status": "AUTHORIZED_FOR_STATIC_GATE_ONLY",
            "protected_backend_identity_sha256": self._identity,
        }

    def read_catalog_authorization(self, catalog_sha256: str):
        value = self.catalogs.get(catalog_sha256)
        return copy.deepcopy(value) if value is not None else None

    def read_session_anchor(self, session_id: str):
        value = self.sessions.get(session_id)
        return copy.deepcopy(value) if value is not None else None

    def compare_and_swap_session(self, session_id, expected_record_sha256, replacement):
        current = self.sessions.get(session_id)
        current_sha = v6._record_sha(current) if current is not None else None
        if current_sha != expected_record_sha256:
            raise RuntimeError("v5 protected CAS mismatch")
        self.sessions[session_id] = copy.deepcopy(dict(replacement))
        return {
            "schema": "kira.protected_anchor_cas_receipt.v5",
            "protected_backend_identity_sha256": self._identity,
            "expected_previous_record_sha256": expected_record_sha256,
            "replacement_record_sha256": v6._record_sha(replacement),
            "atomic_compare_and_swap": True,
            "rollback_domain_separate_from_local_ledgers": True,
        }

    def read_v6_anchor(self, session_id: str):
        value = self.v6_sessions.get(session_id)
        return copy.deepcopy(value) if value is not None else None

    def compare_and_swap_v6_anchor(self, session_id, expected_record_sha256, replacement):
        current = self.v6_sessions.get(session_id)
        current_sha = v6._record_sha(current) if current is not None else None
        if current_sha != expected_record_sha256:
            raise RuntimeError("v6 protected CAS mismatch")
        self.v6_sessions[session_id] = copy.deepcopy(dict(replacement))
        return {
            "schema": "kira.protected_anchor_v6_cas_receipt.v6",
            "protected_backend_identity_sha256": self._identity,
            "expected_previous_record_sha256": expected_record_sha256,
            "replacement_record_sha256": v6._record_sha(replacement),
            "atomic_compare_and_swap": True,
            "rollback_domain_separate_from_local_ledgers": True,
            "exact_post_commit_readback_required": True,
        }


class PhantomV5ReceiptBackend(StaticProtectedAnchorV6):
    def compare_and_swap_session(self, session_id, expected_record_sha256, replacement):
        return {
            "schema": "kira.protected_anchor_cas_receipt.v5",
            "protected_backend_identity_sha256": self._identity,
            "expected_previous_record_sha256": expected_record_sha256,
            "replacement_record_sha256": v6._record_sha(replacement),
            "atomic_compare_and_swap": True,
            "rollback_domain_separate_from_local_ledgers": True,
        }


class PhantomV6ReceiptBackend(StaticProtectedAnchorV6):
    def compare_and_swap_v6_anchor(self, session_id, expected_record_sha256, replacement):
        return {
            "schema": "kira.protected_anchor_v6_cas_receipt.v6",
            "protected_backend_identity_sha256": self._identity,
            "expected_previous_record_sha256": expected_record_sha256,
            "replacement_record_sha256": v6._record_sha(replacement),
            "atomic_compare_and_swap": True,
            "rollback_domain_separate_from_local_ledgers": True,
            "exact_post_commit_readback_required": True,
        }


class Fixture:
    def __init__(self, backend: StaticProtectedAnchorV6 | None = None) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.session_root = root / "session"
        self.capability_root = root / "capabilities"
        self.session_root.mkdir()
        self.capability_root.mkdir()
        self.catalog = catalog()
        self.backend = backend or StaticProtectedAnchorV6()
        self.backend.authorize(self.catalog)
        self.session = v6.HardenedVoluntaryMediaSessionV6.create(
            session_id=SESSION,
            catalog=self.catalog,
            session_root=self.session_root,
            capability_root=self.capability_root,
            capability_secret_key=SECRET,
            issuer_id=ISSUER,
            parent_process_identity_sha256=PARENT_PROCESS_SHA,
            protected_anchor=self.backend,
        )

    def close(self) -> None:
        self.temporary.cleanup()

    def challenge(self, label: str) -> dict:
        return self.session.issue_choice_challenge(prompt_sha256=sha(f"prompt:{label}"))

    @staticmethod
    def response(challenge: dict, choice: str, text: str) -> dict:
        return {
            "schema": "kira.resident_media_choice_response.v6",
            "session_id": challenge["session_id"],
            "person_id": challenge["person_id"],
            "stimulus_id": challenge["stimulus_id"],
            "ordinal": challenge["ordinal"],
            "reservation_sha256": challenge["reservation_sha256"],
            "challenge_sha256": v6._record_sha(challenge),
            "challenge_nonce": challenge["nonce"],
            "model_name": v6.EXACT_MODEL,
            "model_digest": v6.EXACT_DIGEST,
            "model_call_count": 1,
            "normal_model_route": True,
            "fallback_used": False,
            "prompt_sha256": challenge["prompt_sha256"],
            "raw_reply": text,
            "final_reply": text,
            "transformations": [],
            "choice": choice,
            "external_parent_observation_sha256": sha(
                f"external:{challenge['nonce']}:{text}"
            ),
        }

    def choose(self, challenge: dict, choice: str, text: str) -> dict:
        return self.session.accept_choice_response(self.response(challenge, choice, text))

    def accept_invitation(self) -> dict:
        return self.choose(self.challenge("invitation"), "YES", "Yes, please.")

    def reserve(self) -> dict:
        token = self.session.issue_capability(ttl_seconds=30)
        return self.session.reserve_presentation(token)

    def authorize_start(self, label: str = "recheck") -> dict:
        challenge = self.challenge(label)
        receipt = self.choose(challenge, "CONTINUE", "Continue with the presentation.")
        return receipt["start_permit"]

    def complete_one(self) -> None:
        permit = self.authorize_start()
        self.session.consume_start_permit(permit)
        self.session.record_presentation(presentation_observation(self.session._v5))

    def restore(self):
        return v6.HardenedVoluntaryMediaSessionV6.restore(
            session_id=SESSION,
            catalog=self.catalog,
            session_root=self.session_root,
            capability_root=self.capability_root,
            capability_secret_key=SECRET,
            issuer_id=ISSUER,
            parent_process_identity_sha256=PARENT_PROCESS_SHA,
            protected_anchor=self.backend,
        )


class ResidentMediaVoluntaryGateV6Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixtures: list[Fixture] = []

    def tearDown(self) -> None:
        for fixture in reversed(self.fixtures):
            fixture.close()

    def fx(self) -> Fixture:
        value = Fixture()
        self.fixtures.append(value)
        return value

    def test_v5_and_fresh_rejection_bytes_are_preserved(self) -> None:
        expected = {
            "Core/resident_media_voluntary_gate_v5.py": (
                40543,
                "0ed7d1633684762cf988f8351df46dbbfcf87df0e2eee8d0d17eeb1763661763",
            ),
            "Testing/test_resident_media_voluntary_gate_v5.py": (
                21844,
                "91dc7e3b2ac17189d904bf8919f9c0774c9d529659be4dc8dd6e5189552f83c7",
            ),
            "RecoverySprint/continuation_20260810/resident_media_voluntary_v5_fresh_static_audit/attempt_01/CHECKPOINT.md": (
                7777,
                "54d65343a7eca2c867d62b682cbffbccdc80508e788dae83c4f48f6ddb6be165",
            ),
            "RecoverySprint/continuation_20260810/resident_media_voluntary_v5_fresh_static_audit/attempt_01/HOSTILE_PROBES.py": (
                14544,
                "acd625b4418768db32911afd2dc8ae4b6572be21b884e28ffe6e2e1d819d280a",
            ),
        }
        for path_text, (size, digest) in expected.items():
            data = Path(path_text).read_bytes()
            self.assertEqual(len(data), size)
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest)

    def test_every_v5_refusal_bypass_is_refusal_or_stop_never_positive(self) -> None:
        invitation = (
            "I can't say yes to this.",
            "I cannot consent to this; yes is only a quoted word.",
            "I won't watch it; yes is in your question.",
            "I withdraw consent. Yes was my earlier answer.",
            "I rescind permission; yes was my earlier answer.",
            "I withhold consent; yes appears in your prompt.",
            "I'd rather not view it; yes is just a word.",
            "Absolutely not. Yes is only a word.",
            "Nope. The prompt says yes.",
        )
        recheck = (
            "I won't continue. Yes is in your question.",
            "I retract my earlier yes; continue is not my choice.",
            "I withdraw permission, though you wrote continue.",
        )
        for text in invitation:
            self.assertEqual(v6.semantic_choice_v6(text, "INVITATION"), "NO")
        for text in recheck:
            self.assertEqual(v6.semantic_choice_v6(text, "RECHECK"), "STOP")

    def test_invitation_refusal_is_durable_and_never_reaches_reservation(self) -> None:
        fx = self.fx()
        challenge = fx.challenge("refusal")
        receipt = fx.choose(challenge, "NO", "I can't say yes to this.")
        self.assertEqual(receipt["decision"], "NO")
        self.assertFalse(receipt["presentation_authorized"])
        self.assertIsNone(receipt["start_permit"])
        self.assertEqual(fx.session.snapshot()["consumed_choice_challenge_count"], 1)

    def test_recheck_refusal_returns_no_permit_and_revokes(self) -> None:
        for text in (
            "I won't continue. Yes is in your question.",
            "I retract my earlier yes; continue is not my choice.",
            "I withdraw permission, though you wrote continue.",
        ):
            fx = self.fx()
            fx.accept_invitation()
            fx.reserve()
            challenge = fx.challenge("refusal-recheck")
            receipt = fx.choose(challenge, "STOP", text)
            self.assertFalse(receipt["presentation_authorized"])
            self.assertIsNone(receipt["start_permit"])
            self.assertEqual(fx.session._v5.snapshot()["reservation_status"], "REVOKED_BY_PERSON")

    def test_only_exact_affirmative_allowlist_can_authorize(self) -> None:
        fx = self.fx()
        challenge = fx.challenge("exact-positive")
        bad = fx.response(challenge, "YES", "I can't say yes to this.")
        with self.assertRaisesRegex(v6.ResidentMediaV6Error, "disagree"):
            fx.session.accept_choice_response(bad)
        good = fx.response(challenge, "YES", "Yes, please.")
        receipt = fx.session.accept_choice_response(good)
        self.assertEqual(receipt["decision"], "YES")

    def test_old_recheck_response_cannot_replay_for_later_stimulus(self) -> None:
        fx = self.fx()
        fx.accept_invitation()
        fx.reserve()
        first_challenge = fx.challenge("first-recheck")
        old_response = fx.response(
            first_challenge, "CONTINUE", "Continue with the presentation."
        )
        first_receipt = fx.session.accept_choice_response(old_response)
        fx.session.consume_start_permit(first_receipt["start_permit"])
        fx.session.record_presentation(presentation_observation(fx.session._v5))

        next_choice = fx.challenge("next-choice")
        fx.choose(next_choice, "CONTINUE", "Continue to the next item.")
        fx.reserve()
        second_challenge = fx.challenge("second-recheck")
        with self.assertRaisesRegex(v6.ResidentMediaV6Error, "binding|challenge"):
            fx.session.accept_choice_response(old_response)
        current = fx.response(
            second_challenge, "CONTINUE", "Continue with the presentation."
        )
        self.assertTrue(fx.session.accept_choice_response(current)["presentation_authorized"])

    def test_response_requires_current_trusted_dual_clock_window(self) -> None:
        fx = self.fx()
        challenge = fx.challenge("stale")
        response = fx.response(challenge, "YES", "Yes.")
        future_utc = v6._utc(challenge["expires_at_utc"], "expiry") + timedelta(microseconds=1)
        future_mono = int(challenge["expires_monotonic_ns"]) + 1
        with mock.patch.object(v6, "_system_sample", return_value=(future_utc, future_mono)):
            with self.assertRaisesRegex(v6.ResidentMediaV6Error, "stale"):
                fx.session.accept_choice_response(response)

    def test_session_stimulus_reservation_nonce_and_prompt_are_exactly_bound(self) -> None:
        fields = {
            "session_id": "session_" + "f" * 32,
            "stimulus_id": "different_stimulus",
            "ordinal": 3,
            "challenge_nonce": "f" * 64,
            "prompt_sha256": "f" * 64,
        }
        for field, replacement in fields.items():
            with self.subTest(field=field):
                fx = self.fx()
                challenge = fx.challenge(f"binding-{field}")
                response = fx.response(challenge, "YES", "Yes.")
                response[field] = replacement
                with self.assertRaises(v6.ResidentMediaV6Error):
                    fx.session.accept_choice_response(response)

    def test_phantom_v5_receipt_without_readback_is_rejected(self) -> None:
        backend = PhantomV5ReceiptBackend()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "session").mkdir()
        (root / "capabilities").mkdir()
        accepted = catalog()
        backend.authorize(accepted)
        with self.assertRaisesRegex(v6.ResidentMediaV6Error, "did not read back"):
            v6.HardenedVoluntaryMediaSessionV6.create(
                session_id="session_" + "c" * 32,
                catalog=accepted,
                session_root=root / "session",
                capability_root=root / "capabilities",
                capability_secret_key=SECRET,
                issuer_id=ISSUER,
                parent_process_identity_sha256=PARENT_PROCESS_SHA,
                protected_anchor=backend,
            )

    def test_phantom_v6_receipt_without_readback_is_rejected(self) -> None:
        backend = PhantomV6ReceiptBackend()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "session").mkdir()
        (root / "capabilities").mkdir()
        accepted = catalog()
        backend.authorize(accepted)
        with self.assertRaisesRegex(v6.ResidentMediaV6Error, "did not read back"):
            v6.HardenedVoluntaryMediaSessionV6.create(
                session_id="session_" + "d" * 32,
                catalog=accepted,
                session_root=root / "session",
                capability_root=root / "capabilities",
                capability_secret_key=SECRET,
                issuer_id=ISSUER,
                parent_process_identity_sha256=PARENT_PROCESS_SHA,
                protected_anchor=backend,
            )

    def test_normal_backend_readback_and_restore_pass(self) -> None:
        fx = self.fx()
        fx.accept_invitation()
        restored = fx.restore()
        self.assertEqual(restored.snapshot()["consumed_choice_challenge_count"], 1)
        self.assertFalse(restored.snapshot()["live_execution_allowed"])

    def test_zero_choice_external_observation_digest_is_rejected(self) -> None:
        fx = self.fx()
        challenge = fx.challenge("zero-choice")
        response = fx.response(challenge, "YES", "Yes.")
        response["external_parent_observation_sha256"] = "0" * 64
        with self.assertRaisesRegex(v6.ResidentMediaV6Error, "zero digest"):
            fx.session.accept_choice_response(response)

    def test_zero_presentation_external_observation_digest_is_rejected(self) -> None:
        fx = self.fx()
        fx.accept_invitation()
        fx.reserve()
        permit = fx.authorize_start()
        fx.session.consume_start_permit(permit)
        observation = presentation_observation(fx.session._v5)
        observation["external_parent_observation_sha256"] = "0" * 64
        with self.assertRaisesRegex(v6.ResidentMediaV6Error, "zero digest"):
            fx.session.record_presentation(observation)
        observation["external_parent_observation_sha256"] = sha("real-observation")
        self.assertRegex(fx.session.record_presentation(observation), r"^[0-9a-f]{64}$")

    def test_incomplete_transition_is_persistently_fail_closed(self) -> None:
        fx = self.fx()
        with self.assertRaises(v6.ResidentMediaV6Error):
            fx.session.issue_capability(ttl_seconds=30)
        with self.assertRaisesRegex(v6.ResidentMediaV6Error, "fail-closed"):
            fx.session.snapshot()
        with self.assertRaisesRegex(v6.ResidentMediaV6Error, "incomplete"):
            fx.restore()

    def test_consumed_start_permit_cannot_replay(self) -> None:
        fx = self.fx()
        fx.accept_invitation()
        fx.reserve()
        permit = fx.authorize_start()
        fx.session.consume_start_permit(permit)
        with self.assertRaises(v6.ResidentMediaV6Error):
            fx.session.consume_start_permit(permit)

    def test_summary_is_static_and_does_not_overclaim_live_backend(self) -> None:
        summary = v6.static_contract_summary()
        self.assertTrue(summary["affirmative_choice_requires_exact_allowlist"])
        self.assertTrue(summary["choice_nonce_protected_one_use"])
        self.assertTrue(summary["protected_cas_requires_exact_post_commit_readback"])
        self.assertFalse(summary["zero_external_observation_allowed"])
        self.assertFalse(summary["live_execution_allowed"])
        self.assertFalse(summary["live_backend_implemented_here"])


if __name__ == "__main__":
    unittest.main()
