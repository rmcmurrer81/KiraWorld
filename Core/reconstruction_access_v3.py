"""General, fail-closed reconstruction permission controller v3.

This append-only successor does not render or disclose reconstruction content.
It accepts independently signed exact-person capabilities, independently
signed reconstruction bindings, and independently signed verbal content
envelopes.  It returns authorization receipts only.

The durable ledger is a directory of immutable, hash-chained, HMAC-authenticated
event files.  Each event is flushed before an atomic no-replace hard-link makes
it visible.  A stale writer lock, partial file, unknown file, broken chain, or
semantic replay error faults the controller closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import secrets
import threading
import time
from typing import Any, Mapping, Sequence


SCHEMA = "kira.reconstruction_access.v3"
LEDGER_SCHEMA = "kira.reconstruction_access_ledger.v3"
MAX_PERSON_SESSION_SECONDS = 900.0
MAX_REQUEST_SECONDS = 300.0
MAX_VERBAL_PERMIT_SECONDS = 120.0
MAX_PARTICIPANTS = 32
MAX_ZONES = 64
MAX_CONTENT_UTF8_BYTES = 64 * 1024
MAX_LEDGER_EVENT_BYTES = 1024 * 1024

_ID = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_EVENT_NAME = re.compile(r"^(?P<sequence>[0-9]{12})_(?P<digest>[0-9a-f]{64})\.json$")
_PERSON_DOMAIN = b"kira.reconstruction.person_capability.v3\0"
_BINDING_DOMAIN = b"kira.reconstruction.binding.v3\0"
_CONTENT_DOMAIN = b"kira.reconstruction.content_envelope.v3\0"
_LEDGER_DOMAIN = b"kira.reconstruction.ledger_event.v3\0"
_HEAD_DOMAIN = b"kira.reconstruction.ledger_head.v3\0"


class ReconstructionAccessV3Error(RuntimeError):
    """Base v3 boundary error."""


class AuthenticationError(ReconstructionAccessV3Error):
    """An exact independently signed identity capability was invalid."""


class BindingError(ReconstructionAccessV3Error):
    """A reconstruction or content binding was invalid."""


class DecisionError(ReconstructionAccessV3Error):
    """A participant decision was absent, uncertain, denied, or inconsistent."""


class CapabilityError(ReconstructionAccessV3Error):
    """An opaque request or grant capability was invalid."""


class LedgerIntegrityError(ReconstructionAccessV3Error):
    """The durable append-only ledger could not be trusted."""


class ControllerFaultedError(ReconstructionAccessV3Error):
    """A prior clock, ledger, or transition failure faulted authorization closed."""


class GrantModeV3(str, Enum):
    ONE_USE = "one_use"
    EXACT_REVOCABLE_BLANKET = "exact_revocable_blanket"


class ParticipantDecisionV3(str, Enum):
    APPROVE = "approve"
    DENY = "deny"
    UNCERTAIN = "uncertain"


class ReconstructionScopeV3(str, Enum):
    SUMMARY = "summary"
    EMOTIONAL_MEANING = "emotional_meaning"
    VERBAL_DETAILS = "verbal_details"
    NON_INTIMATE_VISUAL = "non_intimate_visual"
    SELECTED_ZONES = "selected_zones"
    FULL_REPLAY = "full_replay"


_SCOPE_RANK = {
    ReconstructionScopeV3.SUMMARY: 0,
    ReconstructionScopeV3.EMOTIONAL_MEANING: 1,
    ReconstructionScopeV3.VERBAL_DETAILS: 2,
    ReconstructionScopeV3.NON_INTIMATE_VISUAL: 3,
    ReconstructionScopeV3.SELECTED_ZONES: 4,
    ReconstructionScopeV3.FULL_REPLAY: 5,
}
_VISUAL_SCOPES = frozenset(
    {
        ReconstructionScopeV3.NON_INTIMATE_VISUAL,
        ReconstructionScopeV3.SELECTED_ZONES,
        ReconstructionScopeV3.FULL_REPLAY,
    }
)


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise BindingError("value is not canonical JSON") from exc
    return text.encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return _sha256_bytes(_canonical_json_bytes(value))


def _hmac_hex(key: bytes, domain: bytes, payload: Mapping[str, Any]) -> str:
    return hmac.new(key, domain + _canonical_json_bytes(payload), hashlib.sha256).hexdigest()


def _trusted_key(value: bytes, field: str) -> bytes:
    if not isinstance(value, bytes) or len(value) < 32:
        raise AuthenticationError(f"{field} must be at least 32 secret bytes")
    return bytes(value)


def _opaque_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise BindingError(f"{field} must be one lowercase opaque ID")
    return value


def _sha256(value: str, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise BindingError(f"{field} must be one lowercase SHA-256")
    return value


def _signature(value: str, field: str = "signature") -> str:
    return _sha256(value, field)


def _finite_monotonic(value: float, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AuthenticationError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise AuthenticationError(f"{field} must be finite and nonnegative")
    return result


def _ttl(value: float, maximum: float, field: str) -> float:
    result = _finite_monotonic(value, field)
    if not 0 < result <= maximum:
        raise BindingError(f"{field} exceeds its bounded maximum")
    return result


def _participants(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise BindingError("participant_ids must be a sequence")
    result = tuple(_opaque_id(value, "participant_id") for value in values)
    if not result or len(result) > MAX_PARTICIPANTS:
        raise BindingError("participant_ids has an invalid count")
    if len(result) != len(set(result)):
        raise BindingError("participant_ids contains duplicates")
    if result != tuple(sorted(result)):
        raise BindingError("participant_ids must use canonical sorted order")
    return result


def _scope(value: ReconstructionScopeV3 | str) -> ReconstructionScopeV3:
    if isinstance(value, ReconstructionScopeV3):
        return value
    try:
        return ReconstructionScopeV3(value)
    except (TypeError, ValueError) as exc:
        raise BindingError("invalid reconstruction scope") from exc


def _zones(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise BindingError("zones must be a sequence")
    result = tuple(_opaque_id(value, "zone") for value in values)
    if len(result) > MAX_ZONES or len(result) != len(set(result)):
        raise BindingError("zones must be unique and bounded")
    if result != tuple(sorted(result)):
        raise BindingError("zones must use canonical sorted order")
    return result


def _policy(
    scope: ReconstructionScopeV3 | str,
    zones: Sequence[str],
    visual_body_exposure_allowed: bool,
) -> tuple[ReconstructionScopeV3, tuple[str, ...], bool]:
    selected_scope = _scope(scope)
    selected_zones = _zones(zones)
    if not isinstance(visual_body_exposure_allowed, bool):
        raise BindingError("visual decision must be Boolean")
    if selected_scope not in _VISUAL_SCOPES:
        if selected_zones or visual_body_exposure_allowed:
            raise BindingError("nonvisual scope cannot expose visuals or zones")
    elif visual_body_exposure_allowed is not True:
        raise BindingError("visual scope requires an explicit true visual decision")
    if selected_scope is ReconstructionScopeV3.SELECTED_ZONES and not selected_zones:
        raise BindingError("selected-zone scope requires at least one exact zone")
    if selected_scope is not ReconstructionScopeV3.SELECTED_ZONES and selected_zones:
        raise BindingError("zones are valid only for selected-zone scope")
    return selected_scope, selected_zones, visual_body_exposure_allowed


def _is_policy_subset(
    child: tuple[ReconstructionScopeV3, tuple[str, ...], bool],
    parent: tuple[ReconstructionScopeV3, tuple[str, ...], bool],
) -> bool:
    child_scope, child_zones, child_visual = child
    parent_scope, parent_zones, parent_visual = parent
    if _SCOPE_RANK[child_scope] > _SCOPE_RANK[parent_scope]:
        return False
    if child_visual and not parent_visual:
        return False
    if child_scope is ReconstructionScopeV3.SELECTED_ZONES:
        if parent_scope is ReconstructionScopeV3.SELECTED_ZONES:
            return set(child_zones).issubset(parent_zones)
        return parent_scope is ReconstructionScopeV3.FULL_REPLAY
    return not child_zones


@dataclass(frozen=True, slots=True)
class SignedExactPersonCapabilityV3:
    issuer_id: str
    key_id: str
    person_id: str
    session_id: str
    activation_revision: str
    issued_monotonic: float
    expires_monotonic: float
    nonce: str
    signature: str


@dataclass(frozen=True, slots=True)
class SignedReconstructionBindingV3:
    issuer_id: str
    key_id: str
    binding_id: str
    reconstruction_id: str
    source_sha256: str
    reconstruction_revision_sha256: str
    material_context_sha256: str
    participant_ids: tuple[str, ...]
    signature: str


@dataclass(frozen=True, slots=True)
class SignedOwnPerspectiveContentEnvelopeV3:
    issuer_id: str
    key_id: str
    envelope_id: str
    speaker_id: str
    intended_listener_id: str
    binding_digest: str
    participant_ids: tuple[str, ...]
    content_sha256: str
    content_utf8_bytes: int
    content_class: str
    contains_visual_replay: bool
    contains_locked_zone_details: bool
    contains_other_participant_private_perspective: bool
    contains_other_participant_private_body_details: bool
    contains_other_participant_private_words: bool
    permission_inferred_from_relationship: bool
    permission_inferred_from_intimacy: bool
    signature: str


@dataclass(frozen=True, slots=True)
class _VerifiedPerson:
    person_id: str
    session_id: str
    activation_revision: str
    expires_monotonic: float
    capability_digest: str


@dataclass(frozen=True, slots=True)
class _VerifiedBinding:
    binding_id: str
    reconstruction_id: str
    source_sha256: str
    reconstruction_revision_sha256: str
    material_context_sha256: str
    participant_ids: tuple[str, ...]
    binding_digest: str


@dataclass(frozen=True, slots=True)
class _VerifiedContent:
    envelope_id: str
    speaker_id: str
    intended_listener_id: str
    binding_digest: str
    participant_ids: tuple[str, ...]
    content_sha256: str
    content_utf8_bytes: int
    envelope_digest: str


def _person_payload(value: SignedExactPersonCapabilityV3) -> dict[str, Any]:
    return {
        "schema": "kira.exact_person_capability.v3",
        "issuer_id": _opaque_id(value.issuer_id, "issuer_id"),
        "key_id": _opaque_id(value.key_id, "key_id"),
        "person_id": _opaque_id(value.person_id, "person_id"),
        "session_id": _opaque_id(value.session_id, "session_id"),
        "activation_revision": _opaque_id(value.activation_revision, "activation_revision"),
        "issued_monotonic": _finite_monotonic(value.issued_monotonic, "issued_monotonic"),
        "expires_monotonic": _finite_monotonic(value.expires_monotonic, "expires_monotonic"),
        "nonce": _opaque_id(value.nonce, "nonce"),
    }


def _binding_payload(value: SignedReconstructionBindingV3) -> dict[str, Any]:
    return {
        "schema": "kira.reconstruction_binding.v3",
        "issuer_id": _opaque_id(value.issuer_id, "issuer_id"),
        "key_id": _opaque_id(value.key_id, "key_id"),
        "binding_id": _opaque_id(value.binding_id, "binding_id"),
        "reconstruction_id": _opaque_id(value.reconstruction_id, "reconstruction_id"),
        "source_sha256": _sha256(value.source_sha256, "source_sha256"),
        "reconstruction_revision_sha256": _sha256(
            value.reconstruction_revision_sha256, "reconstruction_revision_sha256"
        ),
        "material_context_sha256": _sha256(
            value.material_context_sha256, "material_context_sha256"
        ),
        "participant_ids": list(_participants(value.participant_ids)),
    }


def _content_payload(value: SignedOwnPerspectiveContentEnvelopeV3) -> dict[str, Any]:
    boolean_fields = {
        "contains_visual_replay": value.contains_visual_replay,
        "contains_locked_zone_details": value.contains_locked_zone_details,
        "contains_other_participant_private_perspective": value.contains_other_participant_private_perspective,
        "contains_other_participant_private_body_details": value.contains_other_participant_private_body_details,
        "contains_other_participant_private_words": value.contains_other_participant_private_words,
        "permission_inferred_from_relationship": value.permission_inferred_from_relationship,
        "permission_inferred_from_intimacy": value.permission_inferred_from_intimacy,
    }
    if any(not isinstance(item, bool) for item in boolean_fields.values()):
        raise BindingError("content-envelope classification flags must be Boolean")
    if isinstance(value.content_utf8_bytes, bool) or not isinstance(value.content_utf8_bytes, int):
        raise BindingError("content_utf8_bytes must be an integer")
    if not 0 < value.content_utf8_bytes <= MAX_CONTENT_UTF8_BYTES:
        raise BindingError("content envelope has an invalid byte count")
    if value.content_class != "own_perspective_verbal":
        raise BindingError("content envelope has the wrong content class")
    return {
        "schema": "kira.own_perspective_content_envelope.v3",
        "issuer_id": _opaque_id(value.issuer_id, "issuer_id"),
        "key_id": _opaque_id(value.key_id, "key_id"),
        "envelope_id": _opaque_id(value.envelope_id, "envelope_id"),
        "speaker_id": _opaque_id(value.speaker_id, "speaker_id"),
        "intended_listener_id": _opaque_id(
            value.intended_listener_id, "intended_listener_id"
        ),
        "binding_digest": _sha256(value.binding_digest, "binding_digest"),
        "participant_ids": list(_participants(value.participant_ids)),
        "content_sha256": _sha256(value.content_sha256, "content_sha256"),
        "content_utf8_bytes": value.content_utf8_bytes,
        "content_class": value.content_class,
        **boolean_fields,
    }


class _HmacExactPersonCapabilityVerifierV3:
    """Verifier half of an independent exact-person authentication authority."""

    def __init__(self, *, issuer_id: str, key_id: str, verification_key: bytes) -> None:
        self.issuer_id = _opaque_id(issuer_id, "issuer_id")
        self.key_id = _opaque_id(key_id, "key_id")
        self._key = _trusted_key(verification_key, "verification_key")
        self.key_fingerprint = _sha256_bytes(self._key)

    def authority_pin(self) -> dict[str, str]:
        return {
            "issuer_id": self.issuer_id,
            "key_id": self.key_id,
            "key_fingerprint_sha256": self.key_fingerprint,
        }

    def verify(self, value: SignedExactPersonCapabilityV3, *, now: float) -> _VerifiedPerson:
        if not isinstance(value, SignedExactPersonCapabilityV3):
            raise AuthenticationError("signed exact-person capability required")
        payload = _person_payload(value)
        if payload["issuer_id"] != self.issuer_id or payload["key_id"] != self.key_id:
            raise AuthenticationError("person capability authority mismatch")
        signature = _signature(value.signature)
        expected = _hmac_hex(self._key, _PERSON_DOMAIN, payload)
        if not hmac.compare_digest(signature, expected):
            raise AuthenticationError("person capability signature mismatch")
        issued = float(payload["issued_monotonic"])
        expires = float(payload["expires_monotonic"])
        if not issued < expires or expires - issued > MAX_PERSON_SESSION_SECONDS:
            raise AuthenticationError("person capability has an invalid lifetime")
        if issued > now + 1.0:
            raise AuthenticationError("person capability is not yet valid")
        if now >= expires:
            raise AuthenticationError("person capability expired")
        return _VerifiedPerson(
            person_id=str(payload["person_id"]),
            session_id=str(payload["session_id"]),
            activation_revision=str(payload["activation_revision"]),
            expires_monotonic=expires,
            capability_digest=_canonical_sha256({**payload, "signature": signature}),
        )


class _HmacReconstructionBindingVerifierV3:
    """Verifier half of an independent reconstruction/source authority."""

    def __init__(self, *, issuer_id: str, key_id: str, verification_key: bytes) -> None:
        self.issuer_id = _opaque_id(issuer_id, "issuer_id")
        self.key_id = _opaque_id(key_id, "key_id")
        self._key = _trusted_key(verification_key, "verification_key")
        self.key_fingerprint = _sha256_bytes(self._key)

    def authority_pin(self) -> dict[str, str]:
        return {
            "issuer_id": self.issuer_id,
            "key_id": self.key_id,
            "key_fingerprint_sha256": self.key_fingerprint,
        }

    def verify(self, value: SignedReconstructionBindingV3) -> _VerifiedBinding:
        if not isinstance(value, SignedReconstructionBindingV3):
            raise BindingError("signed reconstruction binding required")
        payload = _binding_payload(value)
        if payload["issuer_id"] != self.issuer_id or payload["key_id"] != self.key_id:
            raise BindingError("reconstruction authority mismatch")
        signature = _signature(value.signature)
        expected = _hmac_hex(self._key, _BINDING_DOMAIN, payload)
        if not hmac.compare_digest(signature, expected):
            raise BindingError("reconstruction binding signature mismatch")
        return _VerifiedBinding(
            binding_id=str(payload["binding_id"]),
            reconstruction_id=str(payload["reconstruction_id"]),
            source_sha256=str(payload["source_sha256"]),
            reconstruction_revision_sha256=str(payload["reconstruction_revision_sha256"]),
            material_context_sha256=str(payload["material_context_sha256"]),
            participant_ids=tuple(payload["participant_ids"]),
            binding_digest=_canonical_sha256({**payload, "signature": signature}),
        )


class _HmacOwnPerspectiveContentVerifierV3:
    """Verifier half of an independent disclosure-content classifier."""

    def __init__(self, *, issuer_id: str, key_id: str, verification_key: bytes) -> None:
        self.issuer_id = _opaque_id(issuer_id, "issuer_id")
        self.key_id = _opaque_id(key_id, "key_id")
        self._key = _trusted_key(verification_key, "verification_key")
        self.key_fingerprint = _sha256_bytes(self._key)

    def authority_pin(self) -> dict[str, str]:
        return {
            "issuer_id": self.issuer_id,
            "key_id": self.key_id,
            "key_fingerprint_sha256": self.key_fingerprint,
        }

    def verify(self, value: SignedOwnPerspectiveContentEnvelopeV3) -> _VerifiedContent:
        if not isinstance(value, SignedOwnPerspectiveContentEnvelopeV3):
            raise BindingError("signed own-perspective content envelope required")
        payload = _content_payload(value)
        if payload["issuer_id"] != self.issuer_id or payload["key_id"] != self.key_id:
            raise BindingError("content-envelope authority mismatch")
        signature = _signature(value.signature)
        expected = _hmac_hex(self._key, _CONTENT_DOMAIN, payload)
        if not hmac.compare_digest(signature, expected):
            raise BindingError("content-envelope signature mismatch")
        protected_flags = (
            "contains_visual_replay",
            "contains_locked_zone_details",
            "contains_other_participant_private_perspective",
            "contains_other_participant_private_body_details",
            "contains_other_participant_private_words",
            "permission_inferred_from_relationship",
            "permission_inferred_from_intimacy",
        )
        if any(payload[field] is not False for field in protected_flags):
            raise BindingError("content envelope crosses the own-perspective verbal boundary")
        return _VerifiedContent(
            envelope_id=str(payload["envelope_id"]),
            speaker_id=str(payload["speaker_id"]),
            intended_listener_id=str(payload["intended_listener_id"]),
            binding_digest=str(payload["binding_digest"]),
            participant_ids=tuple(payload["participant_ids"]),
            content_sha256=str(payload["content_sha256"]),
            content_utf8_bytes=int(payload["content_utf8_bytes"]),
            envelope_digest=_canonical_sha256({**payload, "signature": signature}),
        )


class AccessRequestCapabilityV3:
    __slots__ = ()

    def __new__(cls) -> "AccessRequestCapabilityV3":
        raise CapabilityError("request capabilities are controller-issued and opaque")


class OneUseViewCapabilityV3:
    __slots__ = ()

    def __new__(cls) -> "OneUseViewCapabilityV3":
        raise CapabilityError("one-use capabilities are controller-issued and opaque")


class VerbalDisclosureCapabilityV3:
    __slots__ = ()

    def __new__(cls) -> "VerbalDisclosureCapabilityV3":
        raise CapabilityError("verbal capabilities are controller-issued and opaque")


class _DurableAppendOnlyLedgerV3:
    def __init__(
        self,
        directory: Path,
        *,
        integrity_key: bytes,
        authority_pins: Mapping[str, Mapping[str, str]],
        trusted_anti_rollback_anchor: object,
    ) -> None:
        self.directory = Path(directory)
        self._key = _trusted_key(integrity_key, "ledger_integrity_key")
        self._key_fingerprint = _sha256_bytes(self._key)
        self._thread_lock = threading.RLock()
        if not callable(getattr(trusted_anti_rollback_anchor, "read_anchor", None)) or not callable(
            getattr(trusted_anti_rollback_anchor, "advance_anchor", None)
        ):
            raise LedgerIntegrityError("trusted external anti-rollback anchor required")
        self._trusted_anchor = trusted_anti_rollback_anchor
        if self.directory.exists() and self.directory.is_symlink():
            raise LedgerIntegrityError("ledger directory may not be a symlink")
        self.directory.mkdir(parents=True, exist_ok=True)
        if self.directory.is_symlink() or not self.directory.is_dir():
            raise LedgerIntegrityError("ledger path is not a real directory")
        self.directory = self.directory.resolve(strict=True)
        expected_init = {
            "ledger_schema": LEDGER_SCHEMA,
            "integrity_key_fingerprint_sha256": self._key_fingerprint,
            "authority_pins": {
                key: dict(value) for key, value in sorted(authority_pins.items())
            },
            "atomic_write_method": "fsync_file_then_hardlink_no_replace",
            "trusted_external_anti_rollback_anchor_required": True,
            "private_reconstruction_content_logged": False,
        }
        events = self.read_verified()
        if not events:
            self.append("ledger_initialized", expected_init)
            events = self.read_verified()
        if len(events) < 1 or events[0]["event_type"] != "ledger_initialized":
            raise LedgerIntegrityError("ledger initialization event is absent")
        if events[0]["payload"] != expected_init:
            raise LedgerIntegrityError("ledger authority pins or integrity key changed")

    @property
    def lock_path(self) -> Path:
        return self.directory / ".append.lock"

    @property
    def head_path(self) -> Path:
        return self.directory / "HEAD.json"

    def _head_record(self, sequence: int, event_sha256: str) -> dict[str, Any]:
        base = {
            "schema": "kira.reconstruction_access_ledger_head.v3",
            "sequence": sequence,
            "head_event_sha256": event_sha256,
            "integrity_key_fingerprint_sha256": self._key_fingerprint,
        }
        return {
            **base,
            "head_hmac_sha256": _hmac_hex(self._key, _HEAD_DOMAIN, base),
        }

    def _validate_head(self, events: Sequence[Mapping[str, Any]]) -> None:
        if not events:
            if self.head_path.exists():
                raise LedgerIntegrityError("empty ledger has a head anchor")
            return
        if not self.head_path.is_file() or self.head_path.is_symlink():
            raise LedgerIntegrityError("ledger head anchor is absent or unsafe")
        raw = self.head_path.read_bytes()
        if len(raw) > 4096:
            raise LedgerIntegrityError("ledger head anchor exceeds its size bound")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LedgerIntegrityError("ledger head anchor is invalid JSON") from exc
        if not isinstance(value, dict) or raw != _canonical_json_bytes(value) + b"\n":
            raise LedgerIntegrityError("ledger head anchor is not canonical")
        required = {
            "schema",
            "sequence",
            "head_event_sha256",
            "integrity_key_fingerprint_sha256",
            "head_hmac_sha256",
        }
        if set(value) != required:
            raise LedgerIntegrityError("ledger head fields are not exact")
        base = {key: value[key] for key in value if key != "head_hmac_sha256"}
        if value["schema"] != "kira.reconstruction_access_ledger_head.v3":
            raise LedgerIntegrityError("ledger head schema mismatch")
        if value["sequence"] != len(events):
            raise LedgerIntegrityError("ledger rollback or incomplete head update detected")
        if value["head_event_sha256"] != events[-1]["event_sha256"]:
            raise LedgerIntegrityError("ledger head event mismatch")
        if value["integrity_key_fingerprint_sha256"] != self._key_fingerprint:
            raise LedgerIntegrityError("ledger head integrity-key mismatch")
        supplied = _sha256(value["head_hmac_sha256"], "head_hmac_sha256")
        expected = _hmac_hex(self._key, _HEAD_DOMAIN, base)
        if not hmac.compare_digest(supplied, expected):
            raise LedgerIntegrityError("ledger head HMAC mismatch")

    def _validate_external_anchor(self, events: Sequence[Mapping[str, Any]]) -> None:
        try:
            anchor = self._trusted_anchor.read_anchor()
        except Exception as exc:
            raise LedgerIntegrityError("trusted external anchor could not be read") from exc
        if (
            not isinstance(anchor, tuple)
            or len(anchor) != 2
            or isinstance(anchor[0], bool)
            or not isinstance(anchor[0], int)
            or not isinstance(anchor[1], str)
        ):
            raise LedgerIntegrityError("trusted external anchor returned an invalid record")
        sequence, head = anchor
        if sequence < 0:
            raise LedgerIntegrityError("trusted external anchor sequence is invalid")
        if sequence == 0:
            if head != "" or events:
                raise LedgerIntegrityError("nonempty ledger has no trusted external anchor")
            return
        _sha256(head, "trusted_external_head")
        if sequence != len(events) or not events or events[-1]["event_sha256"] != head:
            raise LedgerIntegrityError(
                "ledger rollback, fork, or incomplete externally anchored commit detected"
            )

    def _write_head_atomic(self, sequence: int, event_sha256: str) -> None:
        value = self._head_record(sequence, event_sha256)
        encoded = _canonical_json_bytes(value) + b"\n"
        temporary = self.directory / f".pending_head_{secrets.token_hex(16)}.tmp"
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as stream:
                stream.write(encoded)
                stream.flush()
                # On Windows Python maps fsync to the platform file-buffer
                # commit.  The final head is opened and committed again after
                # the same-directory atomic replace.
                os.fsync(stream.fileno())
        finally:
            os.close(descriptor)
        try:
            os.replace(temporary, self.head_path)
            # Windows requires a write-capable descriptor for its fsync/
            # FlushFileBuffers mapping even though no additional bytes are
            # written after the atomic replace.
            committed_descriptor = os.open(self.head_path, os.O_RDWR)
            try:
                os.fsync(committed_descriptor)
            finally:
                os.close(committed_descriptor)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def _event_base(
        self,
        *,
        sequence: int,
        previous_event_sha256: str,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema": LEDGER_SCHEMA,
            "sequence": sequence,
            "event_id": f"evt_{secrets.token_hex(16)}",
            "event_type": _opaque_id(event_type, "event_type"),
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "previous_event_sha256": previous_event_sha256,
            "payload": dict(payload),
        }

    def _validated_event(self, raw: bytes, path: Path, expected_sequence: int, previous: str) -> dict[str, Any]:
        if len(raw) > MAX_LEDGER_EVENT_BYTES:
            raise LedgerIntegrityError("ledger event exceeds the size bound")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LedgerIntegrityError("ledger event is not canonical JSON") from exc
        if not isinstance(value, dict):
            raise LedgerIntegrityError("ledger event must be an object")
        canonical = _canonical_json_bytes(value) + b"\n"
        if raw != canonical:
            raise LedgerIntegrityError("ledger event bytes are not canonical")
        required = {
            "schema",
            "sequence",
            "event_id",
            "event_type",
            "created_utc",
            "previous_event_sha256",
            "payload",
            "event_sha256",
            "event_hmac_sha256",
        }
        if set(value) != required:
            raise LedgerIntegrityError("ledger event fields are not exact")
        if value["schema"] != LEDGER_SCHEMA or value["sequence"] != expected_sequence:
            raise LedgerIntegrityError("ledger schema or sequence mismatch")
        _opaque_id(value["event_id"], "event_id")
        _opaque_id(value["event_type"], "event_type")
        if not isinstance(value["created_utc"], str) or not value["created_utc"]:
            raise LedgerIntegrityError("ledger UTC timestamp is invalid")
        if value["previous_event_sha256"] != previous:
            raise LedgerIntegrityError("ledger chain predecessor mismatch")
        if not isinstance(value["payload"], dict):
            raise LedgerIntegrityError("ledger payload must be an object")
        event_sha = _sha256(value["event_sha256"], "event_sha256")
        event_hmac = _sha256(value["event_hmac_sha256"], "event_hmac_sha256")
        base = {key: value[key] for key in value if key not in {"event_sha256", "event_hmac_sha256"}}
        expected_sha = _canonical_sha256(base)
        if not hmac.compare_digest(event_sha, expected_sha):
            raise LedgerIntegrityError("ledger event hash mismatch")
        expected_hmac = _hmac_hex(self._key, _LEDGER_DOMAIN, {**base, "event_sha256": event_sha})
        if not hmac.compare_digest(event_hmac, expected_hmac):
            raise LedgerIntegrityError("ledger event HMAC mismatch")
        match = _EVENT_NAME.fullmatch(path.name)
        if match is None:
            raise LedgerIntegrityError("ledger event filename is invalid")
        if int(match.group("sequence")) != expected_sequence or match.group("digest") != event_sha:
            raise LedgerIntegrityError("ledger event filename binding mismatch")
        return value

    def _read_verified(self, *, own_lock: bool) -> list[dict[str, Any]]:
        entries = list(self.directory.iterdir())
        if self.lock_path in entries and not own_lock:
            raise LedgerIntegrityError("ledger writer lock is present")
        paths: list[Path] = []
        for path in entries:
            if path == self.lock_path and own_lock:
                continue
            if path == self.head_path:
                continue
            if path.is_symlink() or not path.is_file():
                raise LedgerIntegrityError("ledger contains a non-regular entry")
            if _EVENT_NAME.fullmatch(path.name) is None:
                raise LedgerIntegrityError("ledger contains an unknown or partial file")
            paths.append(path)
        paths.sort(key=lambda item: item.name)
        events: list[dict[str, Any]] = []
        previous = ""
        for expected_sequence, path in enumerate(paths, 1):
            match = _EVENT_NAME.fullmatch(path.name)
            assert match is not None
            if int(match.group("sequence")) != expected_sequence:
                raise LedgerIntegrityError("ledger sequence is not contiguous")
            event = self._validated_event(path.read_bytes(), path, expected_sequence, previous)
            events.append(event)
            previous = event["event_sha256"]
        self._validate_head(events)
        self._validate_external_anchor(events)
        return events

    def read_verified(self) -> list[dict[str, Any]]:
        with self._thread_lock:
            return self._read_verified(own_lock=False)

    def _acquire_writer_lock(self) -> int:
        try:
            descriptor = os.open(
                self.lock_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError as exc:
            raise LedgerIntegrityError("ledger writer lock is already present") from exc
        try:
            payload = f"pid={os.getpid()} runtime={secrets.token_hex(16)}\n".encode("ascii")
            os.write(descriptor, payload)
            os.fsync(descriptor)
        except Exception:
            os.close(descriptor)
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass
            raise
        return descriptor

    def append(self, event_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise LedgerIntegrityError("ledger payload must be a mapping")
        with self._thread_lock:
            lock_descriptor = self._acquire_writer_lock()
            temporary: Path | None = None
            try:
                events = self._read_verified(own_lock=True)
                sequence = len(events) + 1
                previous = events[-1]["event_sha256"] if events else ""
                base = self._event_base(
                    sequence=sequence,
                    previous_event_sha256=previous,
                    event_type=event_type,
                    payload=payload,
                )
                event_sha = _canonical_sha256(base)
                event = {
                    **base,
                    "event_sha256": event_sha,
                    "event_hmac_sha256": _hmac_hex(
                        self._key,
                        _LEDGER_DOMAIN,
                        {**base, "event_sha256": event_sha},
                    ),
                }
                encoded = _canonical_json_bytes(event) + b"\n"
                if len(encoded) > MAX_LEDGER_EVENT_BYTES:
                    raise LedgerIntegrityError("ledger event exceeds the size bound")
                destination = self.directory / f"{sequence:012d}_{event_sha}.json"
                if destination.exists():
                    raise LedgerIntegrityError("ledger destination already exists")
                try:
                    self._trusted_anchor.advance_anchor(
                        expected_sequence=sequence - 1,
                        expected_head=previous,
                        new_sequence=sequence,
                        new_head=event_sha,
                    )
                except Exception as exc:
                    raise LedgerIntegrityError(
                        "trusted external anchor refused the monotonic advance"
                    ) from exc
                temporary = self.directory / f".pending_{secrets.token_hex(16)}.tmp"
                descriptor = os.open(
                    temporary,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
                try:
                    with os.fdopen(descriptor, "wb", closefd=False) as stream:
                        stream.write(encoded)
                        stream.flush()
                        os.fsync(stream.fileno())
                finally:
                    os.close(descriptor)
                # Hard-link publication is atomic and refuses an existing final
                # name on both Windows and POSIX.  No unsafe replace fallback is
                # permitted.
                os.link(temporary, destination)
                temporary.unlink()
                temporary = None
                self._write_head_atomic(sequence, event_sha)
                return event
            finally:
                if temporary is not None:
                    try:
                        temporary.unlink()
                    except FileNotFoundError:
                        pass
                os.close(lock_descriptor)
                try:
                    self.lock_path.unlink()
                except FileNotFoundError:
                    pass

    def verification_receipt(self) -> dict[str, Any]:
        events = self.read_verified()
        return {
            "schema": LEDGER_SCHEMA,
            "event_count": len(events),
            "head_event_sha256": events[-1]["event_sha256"] if events else "",
            "integrity_key_fingerprint_sha256": self._key_fingerprint,
            "append_only_atomic_event_files": True,
            "trusted_external_anti_rollback_anchor_verified": True,
            "private_reconstruction_content_logged": False,
        }


@dataclass(slots=True)
class _ResponseState:
    participant_id: str
    decision: ParticipantDecisionV3
    policy: tuple[ReconstructionScopeV3, tuple[str, ...], bool] | None
    participant_expires_monotonic: float
    event_sha256: str


@dataclass(slots=True)
class _RequestState:
    request_id: str
    mode: GrantModeV3
    viewer: _VerifiedPerson
    binding: _VerifiedBinding
    requested_policy: tuple[ReconstructionScopeV3, tuple[str, ...], bool]
    issued_at: float
    expires_at: float
    responses: dict[str, _ResponseState]
    invalidated_reason: str = ""
    grant_issued: bool = False


@dataclass(slots=True)
class _OneUseState:
    grant_id: str
    viewer_id: str
    viewer_session_id: str
    binding: _VerifiedBinding
    policy: tuple[ReconstructionScopeV3, tuple[str, ...], bool]
    expires_at: float
    consumed: bool = False
    revoked: bool = False


@dataclass(slots=True)
class _BlanketState:
    grant_id: str
    viewer_id: str
    binding_id: str
    reconstruction_id: str
    source_sha256: str
    reconstruction_revision_sha256: str
    material_context_sha256: str
    binding_digest: str
    participant_ids: tuple[str, ...]
    policy: tuple[ReconstructionScopeV3, tuple[str, ...], bool]
    active: bool
    revision: int
    last_event_sha256: str


@dataclass(slots=True)
class _VerbalState:
    permit_id: str
    speaker_id: str
    speaker_session_id: str
    listener_id: str
    listener_session_id: str
    binding_digest: str
    envelope_digest: str
    content_sha256: str
    content_utf8_bytes: int
    participant_ids: tuple[str, ...]
    expires_at: float
    consumed: bool = False
    revoked: bool = False


_KNOWN_EVENTS = frozenset(
    {
        "ledger_initialized",
        "access_request_created",
        "participant_decision_recorded",
        "pending_request_revoked",
        "one_use_grant_issued",
        "one_use_grant_consumed",
        "one_use_grant_revoked",
        "blanket_grant_created",
        "blanket_grant_used",
        "blanket_grant_narrowed",
        "blanket_grant_revoked",
        "verbal_permit_created",
        "verbal_permit_consumed",
        "verbal_permit_revoked",
    }
)


class ReconstructionAccessControllerV3:
    """Receipt-only generalized v3 controller; construct with :meth:`open`."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise CapabilityError("use open(); direct construction is forbidden")

    @classmethod
    def open(
        cls,
        *,
        ledger_directory: Path,
        sealed_authority_handle: object,
    ) -> "ReconstructionAccessControllerV3":
        """Production boundary reserved for a future sealed authority adapter.

        V3 is intentionally static/mocked in this checkpoint.  A normal caller
        cannot choose authentication, reconstruction, content, or ledger HMAC
        keys.  The future adapter must obtain a non-caller-mintable sealed
        handle from protected operating-system storage and then be audited in
        a separate integration change.
        """

        del cls, ledger_directory, sealed_authority_handle
        raise AuthenticationError(
            "production sealed authority adapter is not connected; static v3 cannot open live"
        )

    @classmethod
    def _open_for_static_tests(
        cls,
        *,
        ledger_directory: Path,
        ledger_integrity_key: bytes,
        person_verifier: _HmacExactPersonCapabilityVerifierV3,
        reconstruction_verifier: _HmacReconstructionBindingVerifierV3,
        content_verifier: _HmacOwnPerspectiveContentVerifierV3,
        trusted_anti_rollback_anchor: object,
    ) -> "ReconstructionAccessControllerV3":
        """Private constructor used only by isolated mocked hostile tests."""

        if cls is not ReconstructionAccessControllerV3:
            raise CapabilityError("subclass construction is forbidden")
        if not isinstance(person_verifier, _HmacExactPersonCapabilityVerifierV3):
            raise AuthenticationError("exact-person verifier required")
        if not isinstance(reconstruction_verifier, _HmacReconstructionBindingVerifierV3):
            raise AuthenticationError("reconstruction verifier required")
        if not isinstance(content_verifier, _HmacOwnPerspectiveContentVerifierV3):
            raise AuthenticationError("content-envelope verifier required")
        self = object.__new__(cls)
        self._lock = threading.RLock()
        self._runtime_epoch = f"runtime_{secrets.token_hex(16)}"
        self._last_clock: float | None = None
        self._faulted = False
        self._person_verifier = person_verifier
        self._reconstruction_verifier = reconstruction_verifier
        self._content_verifier = content_verifier
        self._requests: dict[AccessRequestCapabilityV3, _RequestState] = {}
        self._one_use: dict[OneUseViewCapabilityV3, _OneUseState] = {}
        self._verbal: dict[VerbalDisclosureCapabilityV3, _VerbalState] = {}
        self._blankets: dict[str, _BlanketState] = {}
        self._ledger = _DurableAppendOnlyLedgerV3(
            ledger_directory,
            integrity_key=ledger_integrity_key,
            authority_pins={
                "person": person_verifier.authority_pin(),
                "reconstruction": reconstruction_verifier.authority_pin(),
                "content": content_verifier.authority_pin(),
            },
            trusted_anti_rollback_anchor=trusted_anti_rollback_anchor,
        )
        self._replay_durable_blankets()
        return self

    def _ensure_live(self) -> None:
        if self._faulted:
            raise ControllerFaultedError("controller is faulted closed")

    def _now(self) -> float:
        self._ensure_live()
        value = float(time.monotonic())
        if not math.isfinite(value) or value < 0:
            self._faulted = True
            raise ControllerFaultedError("trusted monotonic clock is invalid")
        if self._last_clock is not None and value < self._last_clock:
            self._faulted = True
            raise ControllerFaultedError("trusted monotonic clock moved backward")
        self._last_clock = value
        return value

    def _append(self, event_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        self._ensure_live()
        try:
            return self._ledger.append(event_type, payload)
        except Exception:
            self._faulted = True
            raise

    def _person(self, capability: SignedExactPersonCapabilityV3, *, now: float) -> _VerifiedPerson:
        return self._person_verifier.verify(capability, now=now)

    def _binding(self, binding: SignedReconstructionBindingV3) -> _VerifiedBinding:
        return self._reconstruction_verifier.verify(binding)

    @staticmethod
    def _binding_fields(binding: _VerifiedBinding) -> dict[str, Any]:
        return {
            "binding_id": binding.binding_id,
            "reconstruction_id": binding.reconstruction_id,
            "source_sha256": binding.source_sha256,
            "reconstruction_revision_sha256": binding.reconstruction_revision_sha256,
            "material_context_sha256": binding.material_context_sha256,
            "binding_digest": binding.binding_digest,
            "participant_ids": list(binding.participant_ids),
        }

    @staticmethod
    def _policy_fields(
        policy: tuple[ReconstructionScopeV3, tuple[str, ...], bool]
    ) -> dict[str, Any]:
        return {
            "scope": policy[0].value,
            "zones": list(policy[1]),
            "visual_body_exposure_allowed": policy[2],
        }

    @staticmethod
    def _same_binding(left: _VerifiedBinding, right: _VerifiedBinding) -> bool:
        return left == right

    def _replay_durable_blankets(self) -> None:
        events = self._ledger.read_verified()
        self._blankets = {}
        for event in events:
            event_type = event["event_type"]
            if event_type not in _KNOWN_EVENTS:
                raise LedgerIntegrityError(f"unknown ledger event type: {event_type}")
            payload = event["payload"]
            if event_type == "blanket_grant_created":
                grant_id = _opaque_id(payload.get("grant_id"), "grant_id")
                if grant_id in self._blankets:
                    raise LedgerIntegrityError("duplicate blanket grant ID")
                participant_ids = _participants(payload.get("participant_ids"))
                policy = _policy(
                    payload.get("scope"),
                    payload.get("zones"),
                    payload.get("visual_body_exposure_allowed"),
                )
                self._blankets[grant_id] = _BlanketState(
                    grant_id=grant_id,
                    viewer_id=_opaque_id(payload.get("viewer_id"), "viewer_id"),
                    binding_id=_opaque_id(payload.get("binding_id"), "binding_id"),
                    reconstruction_id=_opaque_id(
                        payload.get("reconstruction_id"), "reconstruction_id"
                    ),
                    source_sha256=_sha256(payload.get("source_sha256"), "source_sha256"),
                    reconstruction_revision_sha256=_sha256(
                        payload.get("reconstruction_revision_sha256"),
                        "reconstruction_revision_sha256",
                    ),
                    material_context_sha256=_sha256(
                        payload.get("material_context_sha256"), "material_context_sha256"
                    ),
                    binding_digest=_sha256(payload.get("binding_digest"), "binding_digest"),
                    participant_ids=participant_ids,
                    policy=policy,
                    active=True,
                    revision=1,
                    last_event_sha256=event["event_sha256"],
                )
            elif event_type in {"blanket_grant_used", "blanket_grant_narrowed", "blanket_grant_revoked"}:
                grant_id = _opaque_id(payload.get("grant_id"), "grant_id")
                state = self._blankets.get(grant_id)
                if state is None:
                    raise LedgerIntegrityError("blanket event references an absent grant")
                if not state.active:
                    raise LedgerIntegrityError("blanket event follows revocation")
                if event_type == "blanket_grant_used":
                    used_policy = _policy(
                        payload.get("scope"),
                        payload.get("zones"),
                        payload.get("visual_body_exposure_allowed"),
                    )
                    if not _is_policy_subset(used_policy, state.policy):
                        raise LedgerIntegrityError("blanket-use event exceeds current policy")
                elif event_type == "blanket_grant_narrowed":
                    participant_id = _opaque_id(payload.get("participant_id"), "participant_id")
                    if participant_id not in state.participant_ids:
                        raise LedgerIntegrityError("nonparticipant narrowed a blanket grant")
                    narrowed = _policy(
                        payload.get("scope"),
                        payload.get("zones"),
                        payload.get("visual_body_exposure_allowed"),
                    )
                    if narrowed == state.policy or not _is_policy_subset(narrowed, state.policy):
                        raise LedgerIntegrityError("blanket narrowing is not strictly narrower")
                    state.policy = narrowed
                    state.revision += 1
                else:
                    participant_id = _opaque_id(payload.get("participant_id"), "participant_id")
                    if participant_id not in state.participant_ids:
                        raise LedgerIntegrityError("nonparticipant revoked a blanket grant")
                    state.active = False
                    state.revision += 1
                state.last_event_sha256 = event["event_sha256"]

    def verify_ledger(self) -> dict[str, Any]:
        with self._lock:
            self._ensure_live()
            receipt = self._ledger.verification_receipt()
            # Semantic replay detects valid-HMAC but invalid transition order.
            self._replay_durable_blankets()
            return {**receipt, "semantic_replay_passed": True}

    def create_access_request(
        self,
        *,
        viewer_capability: SignedExactPersonCapabilityV3,
        reconstruction_binding: SignedReconstructionBindingV3,
        request_id: str,
        mode: GrantModeV3,
        requested_scope: ReconstructionScopeV3,
        requested_zones: Sequence[str] = (),
        visual_body_exposure_allowed: bool = False,
        ttl_seconds: float = MAX_REQUEST_SECONDS,
    ) -> AccessRequestCapabilityV3:
        with self._lock:
            now = self._now()
            viewer = self._person(viewer_capability, now=now)
            binding = self._binding(reconstruction_binding)
            identifier = _opaque_id(request_id, "request_id")
            if not isinstance(mode, GrantModeV3):
                raise BindingError("explicit grant mode required")
            policy = _policy(
                requested_scope, requested_zones, visual_body_exposure_allowed
            )
            ttl = _ttl(ttl_seconds, MAX_REQUEST_SECONDS, "ttl_seconds")
            capability = object.__new__(AccessRequestCapabilityV3)
            state = _RequestState(
                request_id=identifier,
                mode=mode,
                viewer=viewer,
                binding=binding,
                requested_policy=policy,
                issued_at=now,
                expires_at=min(now + ttl, viewer.expires_monotonic),
                responses={},
            )
            event = self._append(
                "access_request_created",
                {
                    "request_id": identifier,
                    "mode": mode.value,
                    "viewer_id": viewer.person_id,
                    "viewer_session_id": viewer.session_id,
                    **self._binding_fields(binding),
                    **self._policy_fields(policy),
                    "relationship_or_intimacy_inferred": False,
                },
            )
            del event
            self._requests[capability] = state
            return capability

    def _request(self, capability: AccessRequestCapabilityV3, *, now: float) -> _RequestState:
        if not isinstance(capability, AccessRequestCapabilityV3):
            raise CapabilityError("exact opaque request capability required")
        state = self._requests.get(capability)
        if state is None:
            raise CapabilityError("request capability is cloned, stale, or belongs elsewhere")
        if state.invalidated_reason:
            raise CapabilityError(f"request invalidated: {state.invalidated_reason}")
        if now >= state.expires_at:
            state.invalidated_reason = "expired"
            raise CapabilityError("request expired")
        return state

    def record_participant_decision(
        self,
        request_capability: AccessRequestCapabilityV3,
        *,
        participant_capability: SignedExactPersonCapabilityV3,
        decision: ParticipantDecisionV3,
        approved_scope: ReconstructionScopeV3 | None = None,
        approved_zones: Sequence[str] = (),
        visual_body_exposure_allowed: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            now = self._now()
            request = self._request(request_capability, now=now)
            participant = self._person(participant_capability, now=now)
            if participant.person_id not in request.binding.participant_ids:
                raise DecisionError("decision signer is not an exact participant")
            if participant.person_id in request.responses:
                raise DecisionError("participant already made the exact request decision")
            if not isinstance(decision, ParticipantDecisionV3):
                raise DecisionError("explicit participant decision required")
            policy: tuple[ReconstructionScopeV3, tuple[str, ...], bool] | None = None
            if decision is ParticipantDecisionV3.APPROVE:
                if approved_scope is None:
                    raise DecisionError("approval requires an exact scope")
                policy = _policy(
                    approved_scope, approved_zones, visual_body_exposure_allowed
                )
                if not _is_policy_subset(policy, request.requested_policy):
                    raise DecisionError("participant approval exceeds the request")
            elif approved_scope is not None or approved_zones or visual_body_exposure_allowed:
                raise DecisionError("denial or uncertainty cannot carry access policy")
            event = self._append(
                "participant_decision_recorded",
                {
                    "request_id": request.request_id,
                    "participant_id": participant.person_id,
                    "participant_session_id": participant.session_id,
                    "decision": decision.value,
                    "approved_policy": self._policy_fields(policy) if policy else None,
                    "relationship_or_intimacy_inferred": False,
                },
            )
            request.responses[participant.person_id] = _ResponseState(
                participant_id=participant.person_id,
                decision=decision,
                policy=policy,
                participant_expires_monotonic=participant.expires_monotonic,
                event_sha256=event["event_sha256"],
            )
            return {
                "status": "PARTICIPANT_DECISION_RECORDED",
                "request_id": request.request_id,
                "participant_id": participant.person_id,
                "decision": decision.value,
                "audit_event_sha256": event["event_sha256"],
                "reconstruction_access_granted": False,
            }

    def revoke_pending_request(
        self,
        request_capability: AccessRequestCapabilityV3,
        *,
        participant_capability: SignedExactPersonCapabilityV3,
    ) -> dict[str, Any]:
        with self._lock:
            now = self._now()
            request = self._request(request_capability, now=now)
            participant = self._person(participant_capability, now=now)
            if participant.person_id not in request.binding.participant_ids:
                raise DecisionError("only an exact participant may revoke")
            event = self._append(
                "pending_request_revoked",
                {
                    "request_id": request.request_id,
                    "participant_id": participant.person_id,
                },
            )
            request.invalidated_reason = f"revoked_by:{participant.person_id}"
            return {
                "status": "PENDING_REQUEST_REVOKED",
                "request_id": request.request_id,
                "participant_id": participant.person_id,
                "audit_event_sha256": event["event_sha256"],
            }

    def _unanimous_policy(
        self, request: _RequestState, *, now: float
    ) -> tuple[ReconstructionScopeV3, tuple[str, ...], bool]:
        expected = set(request.binding.participant_ids)
        if set(request.responses) != expected or len(request.responses) != len(expected):
            raise DecisionError("every exact participant must decide")
        ordered = [request.responses[item] for item in request.binding.participant_ids]
        if any(now >= item.participant_expires_monotonic for item in ordered):
            raise DecisionError("a participant authentication session expired before issuance")
        if any(item.decision is not ParticipantDecisionV3.APPROVE for item in ordered):
            raise DecisionError("every exact participant must affirmatively approve")
        policies = {item.policy for item in ordered}
        if len(policies) != 1 or None in policies:
            raise DecisionError("participants did not approve one exact common policy")
        policy = next(iter(policies))
        assert policy is not None
        return policy

    def issue_one_use_grant(
        self, request_capability: AccessRequestCapabilityV3
    ) -> OneUseViewCapabilityV3:
        with self._lock:
            now = self._now()
            request = self._request(request_capability, now=now)
            if request.mode is not GrantModeV3.ONE_USE:
                raise DecisionError("request is not one-use")
            if request.grant_issued:
                raise DecisionError("request already issued its only grant")
            policy = self._unanimous_policy(request, now=now)
            grant_id = f"oneuse_{secrets.token_hex(16)}"
            event = self._append(
                "one_use_grant_issued",
                {
                    "grant_id": grant_id,
                    "request_id": request.request_id,
                    "viewer_id": request.viewer.person_id,
                    "viewer_session_id": request.viewer.session_id,
                    **self._binding_fields(request.binding),
                    **self._policy_fields(policy),
                    "decision_event_sha256s": [
                        request.responses[item].event_sha256
                        for item in request.binding.participant_ids
                    ],
                    "one_shot": True,
                },
            )
            capability = object.__new__(OneUseViewCapabilityV3)
            self._one_use[capability] = _OneUseState(
                grant_id=grant_id,
                viewer_id=request.viewer.person_id,
                viewer_session_id=request.viewer.session_id,
                binding=request.binding,
                policy=policy,
                expires_at=request.expires_at,
            )
            request.grant_issued = True
            return capability

    def consume_one_use_grant(
        self,
        grant_capability: OneUseViewCapabilityV3,
        *,
        viewer_capability: SignedExactPersonCapabilityV3,
        reconstruction_binding: SignedReconstructionBindingV3,
        exact_scope: ReconstructionScopeV3,
        exact_zones: Sequence[str] = (),
        visual_body_exposure_allowed: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            now = self._now()
            if not isinstance(grant_capability, OneUseViewCapabilityV3):
                raise CapabilityError("exact opaque one-use capability required")
            state = self._one_use.get(grant_capability)
            if state is None:
                raise CapabilityError("one-use capability is cloned, stale, or belongs elsewhere")
            if state.consumed or state.revoked or now >= state.expires_at:
                raise CapabilityError("one-use grant is consumed, revoked, or expired")
            viewer = self._person(viewer_capability, now=now)
            binding = self._binding(reconstruction_binding)
            policy = _policy(exact_scope, exact_zones, visual_body_exposure_allowed)
            if viewer.person_id != state.viewer_id or viewer.session_id != state.viewer_session_id:
                raise CapabilityError("one-use viewer/session binding mismatch")
            if not self._same_binding(binding, state.binding) or policy != state.policy:
                raise CapabilityError("one-use reconstruction/policy binding mismatch")
            event = self._append(
                "one_use_grant_consumed",
                {
                    "grant_id": state.grant_id,
                    "viewer_id": viewer.person_id,
                    "viewer_session_id": viewer.session_id,
                    "binding_digest": binding.binding_digest,
                    **self._policy_fields(policy),
                    "one_shot_consumed": True,
                },
            )
            state.consumed = True
            return {
                "status": "RECONSTRUCTION_VIEW_AUTHORIZED_ONCE",
                "grant_id": state.grant_id,
                "viewer_id": viewer.person_id,
                "viewer_session_id": viewer.session_id,
                "binding_digest": binding.binding_digest,
                **self._policy_fields(policy),
                "authorization_receipt_only": True,
                "private_content_included": False,
                "audit_event_sha256": event["event_sha256"],
            }

    def revoke_one_use_grant(
        self,
        grant_capability: OneUseViewCapabilityV3,
        *,
        participant_capability: SignedExactPersonCapabilityV3,
    ) -> dict[str, Any]:
        with self._lock:
            now = self._now()
            if not isinstance(grant_capability, OneUseViewCapabilityV3):
                raise CapabilityError("exact opaque one-use capability required")
            state = self._one_use.get(grant_capability)
            if state is None or state.consumed or state.revoked:
                raise CapabilityError("one-use grant is absent or no longer revocable")
            participant = self._person(participant_capability, now=now)
            if participant.person_id not in state.binding.participant_ids:
                raise DecisionError("only an exact participant may revoke")
            event = self._append(
                "one_use_grant_revoked",
                {"grant_id": state.grant_id, "participant_id": participant.person_id},
            )
            state.revoked = True
            return {
                "status": "ONE_USE_GRANT_REVOKED",
                "grant_id": state.grant_id,
                "participant_id": participant.person_id,
                "audit_event_sha256": event["event_sha256"],
            }

    def issue_blanket_grant(self, request_capability: AccessRequestCapabilityV3) -> dict[str, Any]:
        with self._lock:
            now = self._now()
            request = self._request(request_capability, now=now)
            if request.mode is not GrantModeV3.EXACT_REVOCABLE_BLANKET:
                raise DecisionError("request is not exact revocable blanket")
            if request.grant_issued:
                raise DecisionError("request already issued its only grant")
            policy = self._unanimous_policy(request, now=now)
            grant_id = f"blanket_{secrets.token_hex(16)}"
            payload = {
                "grant_id": grant_id,
                "request_id": request.request_id,
                "viewer_id": request.viewer.person_id,
                **self._binding_fields(request.binding),
                **self._policy_fields(policy),
                "decision_event_sha256s": [
                    request.responses[item].event_sha256
                    for item in request.binding.participant_ids
                ],
                "revocable_by_any_exact_participant": True,
                "universal_memory_grant": False,
                "relationship_or_intimacy_inferred": False,
            }
            event = self._append("blanket_grant_created", payload)
            self._blankets[grant_id] = _BlanketState(
                grant_id=grant_id,
                viewer_id=request.viewer.person_id,
                binding_id=request.binding.binding_id,
                reconstruction_id=request.binding.reconstruction_id,
                source_sha256=request.binding.source_sha256,
                reconstruction_revision_sha256=request.binding.reconstruction_revision_sha256,
                material_context_sha256=request.binding.material_context_sha256,
                binding_digest=request.binding.binding_digest,
                participant_ids=request.binding.participant_ids,
                policy=policy,
                active=True,
                revision=1,
                last_event_sha256=event["event_sha256"],
            )
            request.grant_issued = True
            return {
                "status": "EXACT_REVOCABLE_BLANKET_GRANT_CREATED",
                "grant_id": grant_id,
                "viewer_id": request.viewer.person_id,
                "binding_digest": request.binding.binding_digest,
                "participant_ids": list(request.binding.participant_ids),
                **self._policy_fields(policy),
                "authorization_receipt_only": True,
                "audit_event_sha256": event["event_sha256"],
            }

    def _blanket(self, grant_id: str) -> _BlanketState:
        identifier = _opaque_id(grant_id, "grant_id")
        state = self._blankets.get(identifier)
        if state is None:
            raise CapabilityError("exact blanket grant is absent")
        if not state.active:
            raise CapabilityError("blanket grant was revoked")
        return state

    @staticmethod
    def _binding_matches_blanket(binding: _VerifiedBinding, state: _BlanketState) -> bool:
        return (
            binding.binding_id == state.binding_id
            and binding.reconstruction_id == state.reconstruction_id
            and binding.source_sha256 == state.source_sha256
            and binding.reconstruction_revision_sha256
            == state.reconstruction_revision_sha256
            and binding.material_context_sha256 == state.material_context_sha256
            and binding.binding_digest == state.binding_digest
            and binding.participant_ids == state.participant_ids
        )

    def use_blanket_grant(
        self,
        *,
        grant_id: str,
        viewer_capability: SignedExactPersonCapabilityV3,
        reconstruction_binding: SignedReconstructionBindingV3,
        requested_scope: ReconstructionScopeV3,
        requested_zones: Sequence[str] = (),
        visual_body_exposure_allowed: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            now = self._now()
            state = self._blanket(grant_id)
            viewer = self._person(viewer_capability, now=now)
            binding = self._binding(reconstruction_binding)
            policy = _policy(requested_scope, requested_zones, visual_body_exposure_allowed)
            if viewer.person_id != state.viewer_id:
                raise CapabilityError("blanket viewer identity mismatch")
            if not self._binding_matches_blanket(binding, state):
                raise CapabilityError("blanket reconstruction/participant-set binding mismatch")
            if not _is_policy_subset(policy, state.policy):
                raise CapabilityError("requested view exceeds the current blanket policy")
            event = self._append(
                "blanket_grant_used",
                {
                    "grant_id": state.grant_id,
                    "viewer_id": viewer.person_id,
                    "viewer_session_id": viewer.session_id,
                    "binding_digest": binding.binding_digest,
                    "grant_revision": state.revision,
                    **self._policy_fields(policy),
                },
            )
            state.last_event_sha256 = event["event_sha256"]
            return {
                "status": "RECONSTRUCTION_VIEW_AUTHORIZED_BY_EXACT_BLANKET",
                "grant_id": state.grant_id,
                "grant_revision": state.revision,
                "viewer_id": viewer.person_id,
                "viewer_session_id": viewer.session_id,
                "binding_digest": binding.binding_digest,
                **self._policy_fields(policy),
                "authorization_receipt_only": True,
                "private_content_included": False,
                "audit_event_sha256": event["event_sha256"],
            }

    def narrow_blanket_grant(
        self,
        *,
        grant_id: str,
        participant_capability: SignedExactPersonCapabilityV3,
        new_scope: ReconstructionScopeV3,
        new_zones: Sequence[str] = (),
        visual_body_exposure_allowed: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            now = self._now()
            state = self._blanket(grant_id)
            participant = self._person(participant_capability, now=now)
            if participant.person_id not in state.participant_ids:
                raise DecisionError("only an exact participant may narrow")
            narrowed = _policy(new_scope, new_zones, visual_body_exposure_allowed)
            if narrowed == state.policy or not _is_policy_subset(narrowed, state.policy):
                raise DecisionError("new blanket policy must be strictly narrower")
            event = self._append(
                "blanket_grant_narrowed",
                {
                    "grant_id": state.grant_id,
                    "participant_id": participant.person_id,
                    "previous_revision": state.revision,
                    **self._policy_fields(narrowed),
                },
            )
            state.policy = narrowed
            state.revision += 1
            state.last_event_sha256 = event["event_sha256"]
            return {
                "status": "BLANKET_GRANT_NARROWED_IMMEDIATELY",
                "grant_id": state.grant_id,
                "participant_id": participant.person_id,
                "grant_revision": state.revision,
                **self._policy_fields(narrowed),
                "audit_event_sha256": event["event_sha256"],
            }

    def revoke_blanket_grant(
        self,
        *,
        grant_id: str,
        participant_capability: SignedExactPersonCapabilityV3,
    ) -> dict[str, Any]:
        with self._lock:
            now = self._now()
            state = self._blanket(grant_id)
            participant = self._person(participant_capability, now=now)
            if participant.person_id not in state.participant_ids:
                raise DecisionError("only an exact participant may revoke")
            event = self._append(
                "blanket_grant_revoked",
                {
                    "grant_id": state.grant_id,
                    "participant_id": participant.person_id,
                    "previous_revision": state.revision,
                },
            )
            state.active = False
            state.revision += 1
            state.last_event_sha256 = event["event_sha256"]
            return {
                "status": "BLANKET_GRANT_REVOKED_IMMEDIATELY",
                "grant_id": state.grant_id,
                "participant_id": participant.person_id,
                "grant_revision": state.revision,
                "audit_event_sha256": event["event_sha256"],
            }

    def create_own_perspective_verbal_permit(
        self,
        *,
        speaker_capability: SignedExactPersonCapabilityV3,
        listener_capability: SignedExactPersonCapabilityV3,
        reconstruction_binding: SignedReconstructionBindingV3,
        content_envelope: SignedOwnPerspectiveContentEnvelopeV3,
        exact_content: str,
        ttl_seconds: float = MAX_VERBAL_PERMIT_SECONDS,
    ) -> VerbalDisclosureCapabilityV3:
        with self._lock:
            now = self._now()
            speaker = self._person(speaker_capability, now=now)
            listener = self._person(listener_capability, now=now)
            binding = self._binding(reconstruction_binding)
            envelope = self._content_verifier.verify(content_envelope)
            if speaker.person_id not in binding.participant_ids:
                raise BindingError("verbal speaker is not an exact participant")
            if (
                envelope.speaker_id != speaker.person_id
                or envelope.intended_listener_id != listener.person_id
                or envelope.binding_digest != binding.binding_digest
                or envelope.participant_ids != binding.participant_ids
            ):
                raise BindingError("content envelope identity/reconstruction binding mismatch")
            if not isinstance(exact_content, str) or not exact_content:
                raise BindingError("exact verbal content must be a nonempty string")
            encoded = exact_content.encode("utf-8")
            if (
                len(encoded) != envelope.content_utf8_bytes
                or _sha256_bytes(encoded) != envelope.content_sha256
            ):
                raise BindingError("exact verbal content does not match its signed envelope")
            ttl = _ttl(ttl_seconds, MAX_VERBAL_PERMIT_SECONDS, "ttl_seconds")
            permit_id = f"verbal_{secrets.token_hex(16)}"
            capability = object.__new__(VerbalDisclosureCapabilityV3)
            state = _VerbalState(
                permit_id=permit_id,
                speaker_id=speaker.person_id,
                speaker_session_id=speaker.session_id,
                listener_id=listener.person_id,
                listener_session_id=listener.session_id,
                binding_digest=binding.binding_digest,
                envelope_digest=envelope.envelope_digest,
                content_sha256=envelope.content_sha256,
                content_utf8_bytes=envelope.content_utf8_bytes,
                participant_ids=binding.participant_ids,
                expires_at=min(
                    now + ttl,
                    speaker.expires_monotonic,
                    listener.expires_monotonic,
                ),
            )
            event = self._append(
                "verbal_permit_created",
                {
                    "permit_id": permit_id,
                    "speaker_id": speaker.person_id,
                    "speaker_session_id": speaker.session_id,
                    "listener_id": listener.person_id,
                    "listener_session_id": listener.session_id,
                    "binding_digest": binding.binding_digest,
                    "participant_ids": list(binding.participant_ids),
                    "envelope_digest": envelope.envelope_digest,
                    "content_sha256": envelope.content_sha256,
                    "content_utf8_bytes": envelope.content_utf8_bytes,
                    "visual_reconstruction_access_granted": False,
                    "relationship_or_intimacy_inferred": False,
                    "private_content_logged": False,
                },
            )
            del event
            self._verbal[capability] = state
            return capability

    def consume_own_perspective_verbal_permit(
        self,
        permit_capability: VerbalDisclosureCapabilityV3,
        *,
        speaker_capability: SignedExactPersonCapabilityV3,
        listener_capability: SignedExactPersonCapabilityV3,
        exact_content: str,
    ) -> dict[str, Any]:
        with self._lock:
            now = self._now()
            if not isinstance(permit_capability, VerbalDisclosureCapabilityV3):
                raise CapabilityError("exact opaque verbal capability required")
            state = self._verbal.get(permit_capability)
            if state is None or state.consumed or state.revoked or now >= state.expires_at:
                raise CapabilityError("verbal permit is absent, consumed, revoked, or expired")
            speaker = self._person(speaker_capability, now=now)
            listener = self._person(listener_capability, now=now)
            if (
                speaker.person_id != state.speaker_id
                or speaker.session_id != state.speaker_session_id
                or listener.person_id != state.listener_id
                or listener.session_id != state.listener_session_id
            ):
                raise CapabilityError("verbal speaker/listener session binding mismatch")
            if not isinstance(exact_content, str):
                raise BindingError("exact verbal content must be text")
            encoded = exact_content.encode("utf-8")
            if len(encoded) != state.content_utf8_bytes or _sha256_bytes(encoded) != state.content_sha256:
                raise BindingError("verbal content changed after permit creation")
            event = self._append(
                "verbal_permit_consumed",
                {
                    "permit_id": state.permit_id,
                    "speaker_id": state.speaker_id,
                    "listener_id": state.listener_id,
                    "binding_digest": state.binding_digest,
                    "envelope_digest": state.envelope_digest,
                    "content_sha256": state.content_sha256,
                    "visual_reconstruction_access_granted": False,
                    "private_content_logged": False,
                    "one_shot_consumed": True,
                },
            )
            state.consumed = True
            return {
                "status": "OWN_PERSPECTIVE_VERBAL_DISCLOSURE_AUTHORIZED_ONCE",
                "permit_id": state.permit_id,
                "speaker_id": state.speaker_id,
                "listener_id": state.listener_id,
                "content_sha256": state.content_sha256,
                "content_utf8_bytes": state.content_utf8_bytes,
                "authorization_receipt_only": True,
                "verbal_disclosure_is_not_reconstruction_access": True,
                "private_content_included": False,
                "audit_event_sha256": event["event_sha256"],
            }

    def revoke_own_perspective_verbal_permit(
        self,
        permit_capability: VerbalDisclosureCapabilityV3,
        *,
        speaker_capability: SignedExactPersonCapabilityV3,
    ) -> dict[str, Any]:
        with self._lock:
            now = self._now()
            if not isinstance(permit_capability, VerbalDisclosureCapabilityV3):
                raise CapabilityError("exact opaque verbal capability required")
            state = self._verbal.get(permit_capability)
            if state is None or state.consumed or state.revoked:
                raise CapabilityError("verbal permit is absent or no longer revocable")
            speaker = self._person(speaker_capability, now=now)
            if speaker.person_id != state.speaker_id or speaker.session_id != state.speaker_session_id:
                raise CapabilityError("only the exact speaker/session may revoke verbal disclosure")
            event = self._append(
                "verbal_permit_revoked",
                {"permit_id": state.permit_id, "speaker_id": state.speaker_id},
            )
            state.revoked = True
            return {
                "status": "VERBAL_PERMIT_REVOKED",
                "permit_id": state.permit_id,
                "speaker_id": state.speaker_id,
                "audit_event_sha256": event["event_sha256"],
            }

    def current_blanket_grants(self) -> list[dict[str, Any]]:
        with self._lock:
            self._ensure_live()
            return [
                {
                    "grant_id": state.grant_id,
                    "viewer_id": state.viewer_id,
                    "binding_id": state.binding_id,
                    "reconstruction_id": state.reconstruction_id,
                    "binding_digest": state.binding_digest,
                    "participant_ids": list(state.participant_ids),
                    **self._policy_fields(state.policy),
                    "active": state.active,
                    "revision": state.revision,
                    "private_content_included": False,
                }
                for state in sorted(self._blankets.values(), key=lambda item: item.grant_id)
            ]


__all__ = [
    "AuthenticationError",
    "BindingError",
    "CapabilityError",
    "ControllerFaultedError",
    "DecisionError",
    "GrantModeV3",
    "LedgerIntegrityError",
    "OneUseViewCapabilityV3",
    "ParticipantDecisionV3",
    "ReconstructionAccessControllerV3",
    "ReconstructionAccessV3Error",
    "ReconstructionScopeV3",
    "SignedExactPersonCapabilityV3",
    "SignedOwnPerspectiveContentEnvelopeV3",
    "SignedReconstructionBindingV3",
    "VerbalDisclosureCapabilityV3",
]
