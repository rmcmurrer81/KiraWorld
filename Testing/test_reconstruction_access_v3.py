from __future__ import annotations

from dataclasses import replace
import hashlib
import hmac
import inspect
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import time
import unittest
from unittest import mock

from Core import reconstruction_access_v3 as access


_MOCK_PERSON_KEY = b"person-authority-static-test-key-0001"
_MOCK_BINDING_KEY = b"binding-authority-static-test-key-01"
_MOCK_CONTENT_KEY = b"content-authority-static-test-key-01"
_MOCK_LEDGER_KEY = b"ledger-integrity-static-test-key-001"
_MOCK_ANCHOR_KEY = b"external-anchor-static-test-key-001"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


class _MockDurableTrustedAnchor:
    """Test-only stand-in for a protected external monotonic anchor service."""

    def __init__(self, path: Path, key: bytes, *, initialize: bool = True) -> None:
        self.path = path
        self._key = key
        self._lock = threading.RLock()
        if initialize and not path.exists():
            self._write(0, "")

    def _record(self, sequence: int, head: str) -> dict[str, object]:
        base = {
            "schema": "mock.trusted_external_reconstruction_anchor.v1",
            "sequence": sequence,
            "head_event_sha256": head,
        }
        signature = hmac.new(
            self._key,
            b"mock.trusted.anchor\0" + _canonical(base),
            hashlib.sha256,
        ).hexdigest()
        return {**base, "anchor_hmac_sha256": signature}

    def _write(self, sequence: int, head: str) -> None:
        encoded = _canonical(self._record(sequence, head)) + b"\n"
        temporary = self.path.with_name(f".{self.path.name}.{os.urandom(8).hex()}.tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            os.close(descriptor)
        try:
            os.replace(temporary, self.path)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def read_anchor(self) -> tuple[int, str]:
        with self._lock:
            raw = self.path.read_bytes()
            value = json.loads(raw.decode("utf-8"))
            if raw != _canonical(value) + b"\n":
                raise RuntimeError("mock anchor is not canonical")
            supplied = value.pop("anchor_hmac_sha256")
            expected = hmac.new(
                self._key,
                b"mock.trusted.anchor\0" + _canonical(value),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(supplied, expected):
                raise RuntimeError("mock anchor HMAC mismatch")
            return int(value["sequence"]), str(value["head_event_sha256"])

    def advance_anchor(
        self,
        *,
        expected_sequence: int,
        expected_head: str,
        new_sequence: int,
        new_head: str,
    ) -> None:
        with self._lock:
            current = self.read_anchor()
            if current != (expected_sequence, expected_head):
                raise RuntimeError("mock anchor compare-and-set mismatch")
            if new_sequence != expected_sequence + 1 or len(new_head) != 64:
                raise RuntimeError("mock anchor refused nonmonotonic advance")
            self._write(new_sequence, new_head)


class ReconstructionAccessV3HostileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.ledger = self.root / "ledger"
        self.anchor_path = self.root / "trusted_anchor.json"
        self.anchor = _MockDurableTrustedAnchor(self.anchor_path, _MOCK_ANCHOR_KEY)
        self.person_verifier = access._HmacExactPersonCapabilityVerifierV3(
            issuer_id="person_authority",
            key_id="person_key_v1",
            verification_key=_MOCK_PERSON_KEY,
        )
        self.binding_verifier = access._HmacReconstructionBindingVerifierV3(
            issuer_id="reconstruction_authority",
            key_id="binding_key_v1",
            verification_key=_MOCK_BINDING_KEY,
        )
        self.content_verifier = access._HmacOwnPerspectiveContentVerifierV3(
            issuer_id="content_authority",
            key_id="content_key_v1",
            verification_key=_MOCK_CONTENT_KEY,
        )
        self.controller = self._open()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _open(
        self,
        *,
        anchor: _MockDurableTrustedAnchor | None = None,
        person_verifier: access._HmacExactPersonCapabilityVerifierV3 | None = None,
    ) -> access.ReconstructionAccessControllerV3:
        return access.ReconstructionAccessControllerV3._open_for_static_tests(
            ledger_directory=self.ledger,
            ledger_integrity_key=_MOCK_LEDGER_KEY,
            person_verifier=person_verifier or self.person_verifier,
            reconstruction_verifier=self.binding_verifier,
            content_verifier=self.content_verifier,
            trusted_anti_rollback_anchor=anchor or self.anchor,
        )

    def _person(
        self,
        person_id: str,
        *,
        session_id: str | None = None,
        now: float | None = None,
        lifetime: float = 600.0,
        key: bytes = _MOCK_PERSON_KEY,
    ) -> access.SignedExactPersonCapabilityV3:
        current = time.monotonic() if now is None else now
        unsigned = access.SignedExactPersonCapabilityV3(
            issuer_id="person_authority",
            key_id="person_key_v1",
            person_id=person_id,
            session_id=session_id or f"session_{person_id}",
            activation_revision="activation_r1",
            issued_monotonic=current - 0.1,
            expires_monotonic=current + lifetime,
            nonce=f"nonce_{person_id}_{os.urandom(4).hex()}",
            signature="0" * 64,
        )
        signature = access._hmac_hex(
            key,
            access._PERSON_DOMAIN,
            access._person_payload(unsigned),
        )
        return replace(unsigned, signature=signature)

    def _binding(
        self,
        participants: tuple[str, ...] = ("kira", "synthetic_robert"),
        *,
        binding_id: str = "binding_shared_001",
        revision_byte: str = "b",
        context_byte: str = "c",
    ) -> access.SignedReconstructionBindingV3:
        participants = tuple(sorted(participants))
        unsigned = access.SignedReconstructionBindingV3(
            issuer_id="reconstruction_authority",
            key_id="binding_key_v1",
            binding_id=binding_id,
            reconstruction_id="shared_reconstruction_001",
            source_sha256="a" * 64,
            reconstruction_revision_sha256=revision_byte * 64,
            material_context_sha256=context_byte * 64,
            participant_ids=participants,
            signature="0" * 64,
        )
        signature = access._hmac_hex(
            _MOCK_BINDING_KEY,
            access._BINDING_DOMAIN,
            access._binding_payload(unsigned),
        )
        return replace(unsigned, signature=signature)

    def _content_envelope(
        self,
        *,
        content: str,
        speaker: str,
        listener: str,
        binding: access.SignedReconstructionBindingV3,
        **flag_overrides: bool,
    ) -> access.SignedOwnPerspectiveContentEnvelopeV3:
        verified_binding = self.binding_verifier.verify(binding)
        encoded = content.encode("utf-8")
        flags = {
            "contains_visual_replay": False,
            "contains_locked_zone_details": False,
            "contains_other_participant_private_perspective": False,
            "contains_other_participant_private_body_details": False,
            "contains_other_participant_private_words": False,
            "permission_inferred_from_relationship": False,
            "permission_inferred_from_intimacy": False,
        }
        flags.update(flag_overrides)
        unsigned = access.SignedOwnPerspectiveContentEnvelopeV3(
            issuer_id="content_authority",
            key_id="content_key_v1",
            envelope_id=f"envelope_{os.urandom(5).hex()}",
            speaker_id=speaker,
            intended_listener_id=listener,
            binding_digest=verified_binding.binding_digest,
            participant_ids=verified_binding.participant_ids,
            content_sha256=hashlib.sha256(encoded).hexdigest(),
            content_utf8_bytes=len(encoded),
            content_class="own_perspective_verbal",
            signature="0" * 64,
            **flags,
        )
        signature = access._hmac_hex(
            _MOCK_CONTENT_KEY,
            access._CONTENT_DOMAIN,
            access._content_payload(unsigned),
        )
        return replace(unsigned, signature=signature)

    def _request(
        self,
        *,
        viewer: str = "biological_robert",
        binding: access.SignedReconstructionBindingV3 | None = None,
        mode: access.GrantModeV3 = access.GrantModeV3.ONE_USE,
        request_id: str | None = None,
        scope: access.ReconstructionScopeV3 = access.ReconstructionScopeV3.SELECTED_ZONES,
        zones: tuple[str, ...] = ("face", "hands"),
        visual: bool = True,
    ) -> tuple[access.AccessRequestCapabilityV3, access.SignedReconstructionBindingV3]:
        selected_binding = binding or self._binding()
        capability = self.controller.create_access_request(
            viewer_capability=self._person(viewer),
            reconstruction_binding=selected_binding,
            request_id=request_id or f"request_{os.urandom(5).hex()}",
            mode=mode,
            requested_scope=scope,
            requested_zones=zones,
            visual_body_exposure_allowed=visual,
        )
        return capability, selected_binding

    def _approve_all(
        self,
        request: access.AccessRequestCapabilityV3,
        binding: access.SignedReconstructionBindingV3,
        *,
        controller: access.ReconstructionAccessControllerV3 | None = None,
        scope: access.ReconstructionScopeV3 = access.ReconstructionScopeV3.SELECTED_ZONES,
        zones: tuple[str, ...] = ("face", "hands"),
        visual: bool = True,
    ) -> None:
        selected = controller or self.controller
        for participant in binding.participant_ids:
            selected.record_participant_decision(
                request,
                participant_capability=self._person(participant),
                decision=access.ParticipantDecisionV3.APPROVE,
                approved_scope=scope,
                approved_zones=zones,
                visual_body_exposure_allowed=visual,
            )

    def _blanket(self) -> tuple[str, access.SignedReconstructionBindingV3]:
        request, binding = self._request(mode=access.GrantModeV3.EXACT_REVOCABLE_BLANKET)
        self._approve_all(request, binding)
        receipt = self.controller.issue_blanket_grant(request)
        return receipt["grant_id"], binding

    def test_production_open_has_no_raw_keys_or_clock_and_remains_disconnected(self) -> None:
        signature = inspect.signature(access.ReconstructionAccessControllerV3.open)
        self.assertEqual(
            set(signature.parameters),
            {"ledger_directory", "sealed_authority_handle"},
        )
        with self.assertRaises(access.AuthenticationError):
            access.ReconstructionAccessControllerV3.open(
                ledger_directory=self.ledger,
                sealed_authority_handle=object(),
            )
        self.assertNotIn("clock", inspect.signature(access.ReconstructionAccessControllerV3._open_for_static_tests).parameters)

    def test_forged_person_capability_and_raw_identity_are_rejected(self) -> None:
        forged = self._person("kira", key=b"wrong-person-authority-key-000000")
        request, _ = self._request()
        with self.assertRaises(access.AuthenticationError):
            self.controller.record_participant_decision(
                request,
                participant_capability=forged,
                decision=access.ParticipantDecisionV3.DENY,
            )
        with self.assertRaises((TypeError, access.AuthenticationError)):
            self.controller.record_participant_decision(
                request,
                participant_capability="kira",  # type: ignore[arg-type]
                decision=access.ParticipantDecisionV3.DENY,
            )

    def test_biological_owner_and_synthetic_robert_are_not_equivalent(self) -> None:
        request, binding = self._request(viewer="biological_robert")
        self.controller.record_participant_decision(
            request,
            participant_capability=self._person("kira"),
            decision=access.ParticipantDecisionV3.APPROVE,
            approved_scope=access.ReconstructionScopeV3.SELECTED_ZONES,
            approved_zones=("face", "hands"),
            visual_body_exposure_allowed=True,
        )
        with self.assertRaises(access.DecisionError):
            self.controller.record_participant_decision(
                request,
                participant_capability=self._person("biological_robert"),
                decision=access.ParticipantDecisionV3.APPROVE,
                approved_scope=access.ReconstructionScopeV3.SELECTED_ZONES,
                approved_zones=("face", "hands"),
                visual_body_exposure_allowed=True,
            )
        with self.assertRaises(access.DecisionError):
            self.controller.issue_one_use_grant(request)
        self.controller.record_participant_decision(
            request,
            participant_capability=self._person("synthetic_robert"),
            decision=access.ParticipantDecisionV3.APPROVE,
            approved_scope=access.ReconstructionScopeV3.SELECTED_ZONES,
            approved_zones=("face", "hands"),
            visual_body_exposure_allowed=True,
        )
        self.assertIsInstance(
            self.controller.issue_one_use_grant(request),
            access.OneUseViewCapabilityV3,
        )
        self.assertEqual(binding.participant_ids, ("kira", "synthetic_robert"))

    def test_one_use_is_exact_and_consumed_once(self) -> None:
        request, binding = self._request()
        self._approve_all(request, binding)
        grant = self.controller.issue_one_use_grant(request)
        receipt = self.controller.consume_one_use_grant(
            grant,
            viewer_capability=self._person("biological_robert"),
            reconstruction_binding=binding,
            exact_scope=access.ReconstructionScopeV3.SELECTED_ZONES,
            exact_zones=("face", "hands"),
            visual_body_exposure_allowed=True,
        )
        self.assertEqual(receipt["status"], "RECONSTRUCTION_VIEW_AUTHORIZED_ONCE")
        self.assertFalse(receipt["private_content_included"])
        with self.assertRaises(access.CapabilityError):
            self.controller.consume_one_use_grant(
                grant,
                viewer_capability=self._person("biological_robert"),
                reconstruction_binding=binding,
                exact_scope=access.ReconstructionScopeV3.SELECTED_ZONES,
                exact_zones=("face", "hands"),
                visual_body_exposure_allowed=True,
            )

    def test_one_use_capability_does_not_resurrect_after_restart(self) -> None:
        request, binding = self._request()
        self._approve_all(request, binding)
        grant = self.controller.issue_one_use_grant(request)
        restarted = self._open()
        with self.assertRaises(access.CapabilityError):
            restarted.consume_one_use_grant(
                grant,
                viewer_capability=self._person("biological_robert"),
                reconstruction_binding=binding,
                exact_scope=access.ReconstructionScopeV3.SELECTED_ZONES,
                exact_zones=("face", "hands"),
                visual_body_exposure_allowed=True,
            )

    def test_denial_uncertainty_and_missing_participant_fail_closed(self) -> None:
        for decision in (
            access.ParticipantDecisionV3.DENY,
            access.ParticipantDecisionV3.UNCERTAIN,
        ):
            request, binding = self._request()
            self.controller.record_participant_decision(
                request,
                participant_capability=self._person(binding.participant_ids[0]),
                decision=decision,
            )
            self.controller.record_participant_decision(
                request,
                participant_capability=self._person(binding.participant_ids[1]),
                decision=access.ParticipantDecisionV3.APPROVE,
                approved_scope=access.ReconstructionScopeV3.SELECTED_ZONES,
                approved_zones=("face", "hands"),
                visual_body_exposure_allowed=True,
            )
            with self.assertRaises(access.DecisionError):
                self.controller.issue_one_use_grant(request)

    def test_arbitrary_three_participant_set_requires_all_three(self) -> None:
        binding = self._binding(("kira", "lisa", "synthetic_robert"))
        request, _ = self._request(binding=binding)
        for participant in ("kira", "lisa"):
            self.controller.record_participant_decision(
                request,
                participant_capability=self._person(participant),
                decision=access.ParticipantDecisionV3.APPROVE,
                approved_scope=access.ReconstructionScopeV3.SELECTED_ZONES,
                approved_zones=("face", "hands"),
                visual_body_exposure_allowed=True,
            )
        with self.assertRaises(access.DecisionError):
            self.controller.issue_one_use_grant(request)
        self.controller.record_participant_decision(
            request,
            participant_capability=self._person("synthetic_robert"),
            decision=access.ParticipantDecisionV3.APPROVE,
            approved_scope=access.ReconstructionScopeV3.SELECTED_ZONES,
            approved_zones=("face", "hands"),
            visual_body_exposure_allowed=True,
        )
        self.assertIsInstance(self.controller.issue_one_use_grant(request), access.OneUseViewCapabilityV3)

    def test_blanket_persists_restart_but_stays_exact_viewer_and_binding(self) -> None:
        grant_id, binding = self._blanket()
        restarted = self._open()
        receipt = restarted.use_blanket_grant(
            grant_id=grant_id,
            viewer_capability=self._person("biological_robert", session_id="new_owner_session"),
            reconstruction_binding=binding,
            requested_scope=access.ReconstructionScopeV3.SELECTED_ZONES,
            requested_zones=("face",),
            visual_body_exposure_allowed=True,
        )
        self.assertEqual(receipt["viewer_id"], "biological_robert")
        with self.assertRaises(access.CapabilityError):
            restarted.use_blanket_grant(
                grant_id=grant_id,
                viewer_capability=self._person("synthetic_robert"),
                reconstruction_binding=binding,
                requested_scope=access.ReconstructionScopeV3.SELECTED_ZONES,
                requested_zones=("face",),
                visual_body_exposure_allowed=True,
            )
        with self.assertRaises(access.CapabilityError):
            restarted.use_blanket_grant(
                grant_id=grant_id,
                viewer_capability=self._person("biological_robert"),
                reconstruction_binding=self._binding(revision_byte="d"),
                requested_scope=access.ReconstructionScopeV3.SELECTED_ZONES,
                requested_zones=("face",),
                visual_body_exposure_allowed=True,
            )

    def test_any_participant_narrowing_is_immediate_and_durable(self) -> None:
        grant_id, binding = self._blanket()
        narrowed = self.controller.narrow_blanket_grant(
            grant_id=grant_id,
            participant_capability=self._person("kira"),
            new_scope=access.ReconstructionScopeV3.SELECTED_ZONES,
            new_zones=("face",),
            visual_body_exposure_allowed=True,
        )
        self.assertEqual(narrowed["status"], "BLANKET_GRANT_NARROWED_IMMEDIATELY")
        with self.assertRaises(access.CapabilityError):
            self.controller.use_blanket_grant(
                grant_id=grant_id,
                viewer_capability=self._person("biological_robert"),
                reconstruction_binding=binding,
                requested_scope=access.ReconstructionScopeV3.SELECTED_ZONES,
                requested_zones=("hands",),
                visual_body_exposure_allowed=True,
            )
        restarted = self._open()
        self.assertEqual(restarted.current_blanket_grants()[0]["zones"], ["face"])

    def test_any_participant_revocation_is_immediate_and_durable(self) -> None:
        grant_id, binding = self._blanket()
        receipt = self.controller.revoke_blanket_grant(
            grant_id=grant_id,
            participant_capability=self._person("synthetic_robert"),
        )
        self.assertEqual(receipt["status"], "BLANKET_GRANT_REVOKED_IMMEDIATELY")
        for selected in (self.controller, self._open()):
            with self.assertRaises(access.CapabilityError):
                selected.use_blanket_grant(
                    grant_id=grant_id,
                    viewer_capability=self._person("biological_robert"),
                    reconstruction_binding=binding,
                    requested_scope=access.ReconstructionScopeV3.SELECTED_ZONES,
                    requested_zones=("face",),
                    visual_body_exposure_allowed=True,
                )

    def test_nonparticipant_cannot_narrow_or_revoke(self) -> None:
        grant_id, _ = self._blanket()
        with self.assertRaises(access.DecisionError):
            self.controller.narrow_blanket_grant(
                grant_id=grant_id,
                participant_capability=self._person("biological_robert"),
                new_scope=access.ReconstructionScopeV3.SUMMARY,
            )
        with self.assertRaises(access.DecisionError):
            self.controller.revoke_blanket_grant(
                grant_id=grant_id,
                participant_capability=self._person("biological_robert"),
            )

    def test_exact_own_perspective_content_envelope_is_one_shot_not_view_access(self) -> None:
        binding = self._binding()
        content = "I remember my own feelings, and I am choosing to tell you only that."
        envelope = self._content_envelope(
            content=content,
            speaker="kira",
            listener="biological_robert",
            binding=binding,
        )
        permit = self.controller.create_own_perspective_verbal_permit(
            speaker_capability=self._person("kira"),
            listener_capability=self._person("biological_robert"),
            reconstruction_binding=binding,
            content_envelope=envelope,
            exact_content=content,
        )
        receipt = self.controller.consume_own_perspective_verbal_permit(
            permit,
            speaker_capability=self._person("kira"),
            listener_capability=self._person("biological_robert"),
            exact_content=content,
        )
        self.assertTrue(receipt["verbal_disclosure_is_not_reconstruction_access"])
        self.assertFalse(receipt["private_content_included"])
        with self.assertRaises(access.CapabilityError):
            self.controller.consume_own_perspective_verbal_permit(
                permit,
                speaker_capability=self._person("kira"),
                listener_capability=self._person("biological_robert"),
                exact_content=content,
            )

    def test_verbal_content_drift_or_protected_flag_fails(self) -> None:
        binding = self._binding()
        content = "I am sharing only my own reaction."
        envelope = self._content_envelope(
            content=content,
            speaker="kira",
            listener="biological_robert",
            binding=binding,
        )
        with self.assertRaises(access.BindingError):
            self.controller.create_own_perspective_verbal_permit(
                speaker_capability=self._person("kira"),
                listener_capability=self._person("biological_robert"),
                reconstruction_binding=binding,
                content_envelope=envelope,
                exact_content=content + " changed",
            )
        unsafe = self._content_envelope(
            content=content,
            speaker="kira",
            listener="biological_robert",
            binding=binding,
            permission_inferred_from_intimacy=True,
        )
        with self.assertRaises(access.BindingError):
            self.controller.create_own_perspective_verbal_permit(
                speaker_capability=self._person("kira"),
                listener_capability=self._person("biological_robert"),
                reconstruction_binding=binding,
                content_envelope=unsafe,
                exact_content=content,
            )

    def test_ledger_never_contains_private_content_or_mock_keys(self) -> None:
        binding = self._binding()
        secret_text = "private-unique-content-that-must-never-enter-the-ledger"
        envelope = self._content_envelope(
            content=secret_text,
            speaker="kira",
            listener="biological_robert",
            binding=binding,
        )
        self.controller.create_own_perspective_verbal_permit(
            speaker_capability=self._person("kira"),
            listener_capability=self._person("biological_robert"),
            reconstruction_binding=binding,
            content_envelope=envelope,
            exact_content=secret_text,
        )
        combined = b"".join(path.read_bytes() for path in self.ledger.glob("*.json"))
        self.assertNotIn(secret_text.encode("utf-8"), combined)
        for key in (
            _MOCK_PERSON_KEY,
            _MOCK_BINDING_KEY,
            _MOCK_CONTENT_KEY,
            _MOCK_LEDGER_KEY,
            _MOCK_ANCHOR_KEY,
        ):
            self.assertNotIn(key, combined)

    def test_event_tamper_duplicate_and_reorder_fail_closed(self) -> None:
        self._request()
        events = sorted(self.ledger.glob("[0-9]*.json"))
        target = events[-1]
        original = target.read_bytes()
        target.write_bytes(original.replace(b"biological_robert", b"biological_roberx"))
        with self.assertRaises(access.LedgerIntegrityError):
            self._open()
        target.write_bytes(original)
        duplicate = self.ledger / f"000000000999_{'f' * 64}.json"
        duplicate.write_bytes(original)
        with self.assertRaises(access.LedgerIntegrityError):
            self._open()

    def test_reordered_event_filenames_fail_closed(self) -> None:
        self._request()
        events = sorted(self.ledger.glob("[0-9]*.json"))
        self.assertGreaterEqual(len(events), 2)
        first, second = events[0], events[1]
        temporary = self.ledger / "swap.tmp"
        first.rename(temporary)
        second.rename(first)
        temporary.rename(second)
        with self.assertRaises(access.LedgerIntegrityError):
            self._open()

    def test_unknown_partial_and_stale_lock_files_fail_closed(self) -> None:
        for name in ("unknown.txt", ".pending_crash.tmp", ".append.lock"):
            path = self.ledger / name
            path.write_text("crash", encoding="utf-8")
            with self.assertRaises(access.LedgerIntegrityError, msg=name):
                self._open()
            path.unlink()

    def test_tail_deletion_is_detected_by_internal_and_external_heads(self) -> None:
        self._request()
        events = sorted(self.ledger.glob("[0-9]*.json"))
        events[-1].unlink()
        with self.assertRaises(access.LedgerIntegrityError):
            self._open()

    def test_older_valid_ledger_and_head_pair_cannot_erase_revocation(self) -> None:
        grant_id, _ = self._blanket()
        snapshot = self.root / "older_pair"
        shutil.copytree(self.ledger, snapshot)
        self.controller.revoke_blanket_grant(
            grant_id=grant_id,
            participant_capability=self._person("kira"),
        )
        for path in list(self.ledger.iterdir()):
            path.unlink()
        for path in snapshot.iterdir():
            shutil.copy2(path, self.ledger / path.name)
        # The external protected anchor was not rolled back with the attacker-
        # supplied ledger directory, so the formerly valid pair now fails.
        with self.assertRaises(access.LedgerIntegrityError):
            self._open()

    def test_missing_or_reset_external_anchor_never_reinitializes_nonempty_ledger(self) -> None:
        self._request()
        reset_path = self.root / "reset_anchor.json"
        reset = _MockDurableTrustedAnchor(reset_path, _MOCK_ANCHOR_KEY)
        with self.assertRaises(access.LedgerIntegrityError):
            self._open(anchor=reset)
        reset_path.unlink()
        missing = _MockDurableTrustedAnchor(reset_path, _MOCK_ANCHOR_KEY, initialize=False)
        with self.assertRaises(access.LedgerIntegrityError):
            self._open(anchor=missing)

    def test_atomic_publication_flushes_before_link_and_updates_head_after_link(self) -> None:
        operations: list[str] = []
        real_fsync = access.os.fsync
        real_link = access.os.link
        real_replace = access.os.replace

        def tracked_fsync(descriptor: int) -> None:
            operations.append("fsync")
            real_fsync(descriptor)

        def tracked_link(source: object, destination: object) -> None:
            operations.append("event_link")
            source_path = Path(source)
            destination_path = Path(destination)
            self.assertEqual(source_path.parent.resolve(), destination_path.parent.resolve())
            self.assertTrue(source_path.name.startswith(".pending_"))
            self.assertRegex(destination_path.name, r"^[0-9]{12}_[0-9a-f]{64}\.json$")
            real_link(source, destination)
            # Windows hard-link publication must preserve O_EXCL-like
            # no-replace behavior for an already published final name.
            with self.assertRaises(FileExistsError):
                real_link(source, destination)

        def tracked_replace(source: object, destination: object) -> None:
            if Path(destination).name == "HEAD.json":
                operations.append("head_replace")
            real_replace(source, destination)

        with mock.patch.object(access.os, "fsync", tracked_fsync), mock.patch.object(
            access.os, "link", tracked_link
        ), mock.patch.object(access.os, "replace", tracked_replace):
            self._request()
        link_index = operations.index("event_link")
        head_index = operations.index("head_replace")
        self.assertIn("fsync", operations[:link_index])
        self.assertLess(link_index, head_index)
        self.assertIn("fsync", operations[head_index + 1 :])

    def test_hardlink_publication_failure_leaves_no_partial_and_faults_rollback_anchor(self) -> None:
        before = {path.name for path in self.ledger.iterdir()}
        with mock.patch.object(access.os, "link", side_effect=OSError("simulated crash")):
            with self.assertRaises(OSError):
                self._request()
        after = {path.name for path in self.ledger.iterdir()}
        self.assertEqual(before, after)
        self.assertFalse(any(name.startswith(".pending") for name in after))
        self.assertNotIn(".append.lock", after)
        with self.assertRaises(access.LedgerIntegrityError):
            self._open()

    def test_head_replace_failure_leaves_recoverably_visible_event_but_faults_closed(self) -> None:
        before_events = set(self.ledger.glob("[0-9]*.json"))
        real_replace = access.os.replace

        def fail_head_replace(source: object, destination: object) -> None:
            if Path(destination).name == "HEAD.json":
                raise OSError("simulated head replacement crash")
            real_replace(source, destination)

        with mock.patch.object(access.os, "replace", fail_head_replace):
            with self.assertRaises(OSError):
                self._request(request_id="request_head_crash")
        after_events = set(self.ledger.glob("[0-9]*.json"))
        self.assertEqual(len(after_events), len(before_events) + 1)
        self.assertFalse(any(path.name.startswith(".pending") for path in self.ledger.iterdir()))
        self.assertFalse((self.ledger / ".append.lock").exists())
        with self.assertRaises(access.LedgerIntegrityError):
            self._open()

    def test_concurrent_writer_collision_fails_one_closed_without_corruption(self) -> None:
        second = self._open()
        reached_link = threading.Event()
        release_link = threading.Event()
        real_link = access.os.link
        results: list[str] = []

        def blocking_link(source: object, destination: object) -> None:
            reached_link.set()
            if not release_link.wait(5):
                raise RuntimeError("test link release timed out")
            real_link(source, destination)

        def first_writer() -> None:
            try:
                self._request(request_id="request_concurrent_first")
                results.append("first_ok")
            except Exception as exc:  # pragma: no cover - diagnostic branch
                results.append(type(exc).__name__)

        with mock.patch.object(access.os, "link", blocking_link):
            thread = threading.Thread(target=first_writer)
            thread.start()
            self.assertTrue(reached_link.wait(5))
            try:
                with self.assertRaises(access.LedgerIntegrityError):
                    second.create_access_request(
                        viewer_capability=self._person("biological_robert"),
                        reconstruction_binding=self._binding(),
                        request_id="request_concurrent_second",
                        mode=access.GrantModeV3.ONE_USE,
                        requested_scope=access.ReconstructionScopeV3.SUMMARY,
                    )
            finally:
                release_link.set()
                thread.join(5)
        self.assertEqual(results, ["first_ok"])
        self.assertTrue(self.controller.verify_ledger()["semantic_replay_passed"])

    def test_trusted_clock_is_internal_and_rollback_faults_controller(self) -> None:
        now = 5000.0
        viewer = self._person("biological_robert", now=now)
        binding = self._binding()
        with mock.patch.object(access.time, "monotonic", return_value=now):
            self.controller.create_access_request(
                viewer_capability=viewer,
                reconstruction_binding=binding,
                request_id="request_clock_test",
                mode=access.GrantModeV3.ONE_USE,
                requested_scope=access.ReconstructionScopeV3.SUMMARY,
            )
        with mock.patch.object(access.time, "monotonic", return_value=now - 1):
            with self.assertRaises(access.ControllerFaultedError):
                self.controller.create_access_request(
                    viewer_capability=viewer,
                    reconstruction_binding=binding,
                    request_id="request_clock_rollback",
                    mode=access.GrantModeV3.ONE_USE,
                    requested_scope=access.ReconstructionScopeV3.SUMMARY,
                )

    def test_participant_session_must_still_be_current_at_grant_issuance(self) -> None:
        base = time.monotonic() + 1000.0
        binding = self._binding()
        with mock.patch.object(access.time, "monotonic", return_value=base):
            request = self.controller.create_access_request(
                viewer_capability=self._person("biological_robert", now=base),
                reconstruction_binding=binding,
                request_id="request_participant_expiry",
                mode=access.GrantModeV3.ONE_USE,
                requested_scope=access.ReconstructionScopeV3.SUMMARY,
            )
            for participant in binding.participant_ids:
                self.controller.record_participant_decision(
                    request,
                    participant_capability=self._person(
                        participant, now=base, lifetime=1.0
                    ),
                    decision=access.ParticipantDecisionV3.APPROVE,
                    approved_scope=access.ReconstructionScopeV3.SUMMARY,
                )
        with mock.patch.object(access.time, "monotonic", return_value=base + 2.0):
            with self.assertRaises(access.DecisionError):
                self.controller.issue_one_use_grant(request)

    def test_test_authority_primitives_are_not_public_exports(self) -> None:
        for name in (
            "HmacExactPersonCapabilityVerifierV3",
            "HmacReconstructionBindingVerifierV3",
            "HmacOwnPerspectiveContentVerifierV3",
        ):
            self.assertNotIn(name, access.__all__)
            self.assertFalse(hasattr(access, name))
        for private_name in (
            "_HmacExactPersonCapabilityVerifierV3",
            "_HmacReconstructionBindingVerifierV3",
            "_HmacOwnPerspectiveContentVerifierV3",
        ):
            self.assertNotIn(private_name, access.__all__)

    def test_authority_key_change_is_rejected_on_reopen(self) -> None:
        changed = access._HmacExactPersonCapabilityVerifierV3(
            issuer_id="person_authority",
            key_id="person_key_v1",
            verification_key=b"changed-person-key-static-test-000001",
        )
        with self.assertRaises(access.LedgerIntegrityError):
            self._open(person_verifier=changed)


if __name__ == "__main__":
    unittest.main()
