"""Bounded, memory-only publication queue for person-initiated events.

The queue is deliberately downstream of :mod:`shared_person_initiative`.
It does not decide what a person thinks, generate dialogue, execute actions,
write memory, or change a relationship.  It only accepts a previously
registered ``DecisionOpportunity`` and exposes the resulting public speech or
action intent to the exact active person session.

Private decision details and activation nonces never appear in the public
poll representation.  Each event nevertheless retains an internal exact
person/revision/nonce binding, represented publicly by a one-way binding
digest.  Switching or deactivating purges all decisions and events atomically.
"""

from __future__ import annotations

import hashlib
import math
import re
import secrets
import threading
import time
from dataclasses import dataclass, replace
from typing import Any, Callable, Mapping

try:  # Support both ``Core.*`` and a direct Core-directory import.
    from .shared_person_initiative import DecisionOpportunity, InitiativeLease
except ImportError:  # pragma: no cover - exercised by direct-import test setup
    from shared_person_initiative import DecisionOpportunity, InitiativeLease


PUBLIC_EVENT_KINDS = frozenset({"speech", "action", "leave"})
DECISION_TO_PUBLIC_KIND = {
    "consider_speaking": "speech",
    "consider_action": "action",
    "leave": "leave",
    "ignore": "ignore",
}
PUBLIC_PROVENANCE = {
    "speech": "person_initiated_speech_from_private_decision",
    "action": "person_initiated_action_intent_from_private_decision",
    "leave": "person_initiated_leave_intent_from_private_decision",
    "ignore": "person_chose_ignore_from_private_decision",
}

_CANONICAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_LEASE_FIELDS = frozenset({"person_id", "activation_revision", "session_nonce"})
_PRIVATE_OR_RAW_MARKERS = (
    "private_thought",
    "private-thought",
    "internal_monologue",
    "internal-monologue",
    "hidden_reasoning",
    "hidden-reasoning",
    "chain_of_thought",
    "chain-of-thought",
    "raw_sensory",
    "raw-sensory",
    "data:image/",
    "data:audio/",
    "data:video/",
    "base64,",
    "pixel_buffer",
    "audio_samples",
    "pcm_bytes",
)
_DENSE_BASE64 = re.compile(r"(?:[A-Za-z0-9+/]{160,}={0,2})")
_PRIVATE_OR_RAW_ID_PARTS = (
    "privatethought",
    "internalmonologue",
    "hiddenreasoning",
    "chainofthought",
    "rawsensory",
    "pixelbuffer",
    "audiosamples",
    "pcmbytes",
)


class PersonEventLeaseError(PermissionError):
    """Raised when a call is not bound to the exact active person session."""


class PersonEventEvidenceError(ValueError):
    """Raised for missing, incompatible, duplicated, or expired evidence."""


class PersonEventContentError(ValueError):
    """Raised when proposed public content contains private or raw material."""


class PersonEventQueueFullError(RuntimeError):
    """Raised instead of silently dropping an unacknowledged event/evidence."""


def _canonical_id(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _CANONICAL_ID.fullmatch(value):
        raise ValueError(f"{field_name} must be a canonical identifier")
    return value


def _public_identifier(value: Any, field_name: str) -> str:
    result = _canonical_id(value, field_name)
    normalized = re.sub(r"[_.:-]", "", result.casefold())
    if any(marker in normalized for marker in _PRIVATE_OR_RAW_ID_PARTS):
        raise PersonEventContentError(
            f"{field_name} contains a private-thought or raw-sensory marker"
        )
    return result


def _bounded_positive_number(
    value: Any,
    field_name: str,
    *,
    minimum: float,
    maximum: float,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f"{field_name} must be from {minimum} to {maximum}")
    return result


def _validate_public_text(value: Any, field_name: str, *, maximum_bytes: int) -> str:
    if not isinstance(value, str):
        raise PersonEventContentError(f"{field_name} must be public text")
    if not value or value != value.strip():
        raise PersonEventContentError(f"{field_name} must be non-empty exact public text")
    if len(value.encode("utf-8")) > maximum_bytes:
        raise PersonEventContentError(f"{field_name} exceeds its public-text limit")
    if any(ord(character) < 32 and character not in "\t\n\r" for character in value):
        raise PersonEventContentError(f"{field_name} contains binary control data")
    folded = value.casefold()
    if any(marker in folded for marker in _PRIVATE_OR_RAW_MARKERS):
        raise PersonEventContentError(
            f"{field_name} contains a private-thought or raw-sensory marker"
        )
    if _DENSE_BASE64.search(value):
        raise PersonEventContentError(f"{field_name} resembles encoded raw payload data")
    return value


@dataclass(frozen=True, slots=True)
class PublicPersonEvent:
    """One unexecuted public event safe for the shared owner-facing UI."""

    event_id: str
    sequence: int
    person_id: str
    activation_revision: str | int
    event_kind: str
    channel: str
    spoken_text: str | None
    action_id: str | None
    public_action_description: str | None
    decision_id: str
    decision_outcome: str
    provenance: str
    activation_binding_digest: str

    def as_public_dict(self) -> dict[str, Any]:
        """Return a poll-safe representation with no nonce or private details."""

        return {
            "event_id": self.event_id,
            "sequence": self.sequence,
            "person_id": self.person_id,
            "activation_revision": self.activation_revision,
            "event_kind": self.event_kind,
            "channel": self.channel,
            "spoken_text": self.spoken_text,
            "action_id": self.action_id,
            "public_action_description": self.public_action_description,
            "decision_evidence": {
                "decision_id": self.decision_id,
                "decision_outcome": self.decision_outcome,
                "activation_binding_digest": self.activation_binding_digest,
                "exact_session_binding_verified": True,
            },
            "provenance": self.provenance,
            "person_initiated": True,
            "public_content_only": True,
            "action_executed": False,
            "memory_persisted": False,
            "relationship_changed": False,
        }


@dataclass(frozen=True, slots=True)
class DecisionDisposition:
    """Evidence receipt for a private decision that creates no public event."""

    person_id: str
    activation_revision: str | int
    decision_id: str
    decision_outcome: str
    provenance: str
    activation_binding_digest: str

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "person_id": self.person_id,
            "activation_revision": self.activation_revision,
            "decision_id": self.decision_id,
            "decision_outcome": self.decision_outcome,
            "provenance": self.provenance,
            "activation_binding_digest": self.activation_binding_digest,
            "event_enqueued": False,
            "public_content": None,
            "memory_persisted": False,
            "relationship_changed": False,
        }


@dataclass(slots=True)
class _DecisionEvidence:
    decision_id: str
    person_id: str
    activation_revision: str | int
    session_nonce: str
    outcome: str
    registered_monotonic: float
    expires_monotonic: float
    consumed: bool = False


@dataclass(slots=True)
class _QueuedEvent:
    public_event: PublicPersonEvent
    session_nonce: str
    created_monotonic: float
    expires_monotonic: float


class PersonInitiatedEventQueue:
    """Thread-safe queue bound to exactly one initiative activation."""

    def __init__(
        self,
        *,
        max_events: int = 32,
        max_decisions: int = 128,
        event_ttl_seconds: float = 300.0,
        decision_ttl_seconds: float = 300.0,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if isinstance(max_events, bool) or not isinstance(max_events, int):
            raise TypeError("max_events must be an integer")
        if isinstance(max_decisions, bool) or not isinstance(max_decisions, int):
            raise TypeError("max_decisions must be an integer")
        if not 1 <= max_events <= 256:
            raise ValueError("max_events must be from 1 to 256")
        if not 1 <= max_decisions <= 1024:
            raise ValueError("max_decisions must be from 1 to 1024")
        self.max_events = max_events
        self.max_decisions = max_decisions
        self.event_ttl_seconds = _bounded_positive_number(
            event_ttl_seconds,
            "event_ttl_seconds",
            minimum=0.1,
            maximum=3600.0,
        )
        self.decision_ttl_seconds = _bounded_positive_number(
            decision_ttl_seconds,
            "decision_ttl_seconds",
            minimum=0.1,
            maximum=3600.0,
        )
        if not callable(monotonic):
            raise TypeError("monotonic must be callable")
        self._monotonic = monotonic
        self._lock = threading.RLock()
        self._lease: InitiativeLease | None = None
        self._decisions: dict[str, _DecisionEvidence] = {}
        self._events: dict[str, _QueuedEvent] = {}
        self._next_sequence = 1

    @property
    def current_lease(self) -> InitiativeLease | None:
        with self._lock:
            return replace(self._lease) if self._lease else None

    def activate(self, lease: InitiativeLease | Mapping[str, Any]) -> None:
        """Bind to an exact initiative lease after atomically purging old state."""

        supplied = self._coerce_lease(lease)
        with self._lock:
            self._purge_locked()
            self._lease = replace(supplied)

    def switch_person(
        self,
        current_lease: InitiativeLease | Mapping[str, Any],
        new_lease: InitiativeLease | Mapping[str, Any],
    ) -> dict[str, int]:
        """Validate the old activation, purge it, then bind the new activation."""

        supplied_new = self._coerce_lease(new_lease)
        with self._lock:
            self._require_lease_locked(current_lease)
            removed = self._purge_locked()
            self._lease = replace(supplied_new)
            return removed

    def deactivate(self, lease: InitiativeLease | Mapping[str, Any]) -> dict[str, int]:
        with self._lock:
            self._require_lease_locked(lease)
            return self._purge_locked()

    def register_private_decision(
        self,
        lease: InitiativeLease | Mapping[str, Any],
        decision: DecisionOpportunity,
    ) -> dict[str, Any]:
        """Retain only minimal linkage from one prior private opportunity."""

        if not isinstance(decision, DecisionOpportunity):
            raise PersonEventEvidenceError(
                "decision evidence must be a DecisionOpportunity, not an arbitrary payload"
            )
        decision_id = _public_identifier(decision.decision_id, "decision_id")
        with self._lock:
            active = self._require_lease_locked(lease)
            now = self._now_locked()
            self._expire_locked(now)
            if decision.person_id != active.person_id:
                raise PersonEventEvidenceError("decision person does not match the active person")
            if decision.activation_revision != active.activation_revision:
                raise PersonEventEvidenceError(
                    "decision revision does not match the active activation"
                )
            if decision.outcome not in DECISION_TO_PUBLIC_KIND:
                raise PersonEventEvidenceError(
                    "decision outcome cannot publish a public person-initiated event"
                )
            if decision_id in self._decisions:
                raise PersonEventEvidenceError("decision evidence is already registered")
            if len(self._decisions) >= self.max_decisions:
                raise PersonEventQueueFullError(
                    "private decision evidence capacity is full; no evidence was dropped"
                )
            self._decisions[decision_id] = _DecisionEvidence(
                decision_id=decision_id,
                person_id=active.person_id,
                activation_revision=active.activation_revision,
                session_nonce=active.session_nonce,
                outcome=decision.outcome,
                registered_monotonic=now,
                expires_monotonic=now + self.decision_ttl_seconds,
            )
            return {
                "registered": True,
                "decision_id": decision_id,
                "decision_outcome": decision.outcome,
                "private_details_retained": False,
                "public_event_enqueued": False,
            }

    def publish_speech(
        self,
        lease: InitiativeLease | Mapping[str, Any],
        decision_id: str,
        spoken_text: str,
    ) -> PublicPersonEvent:
        text = _validate_public_text(spoken_text, "spoken_text", maximum_bytes=8192)
        return self._publish(
            lease,
            decision_id,
            event_kind="speech",
            spoken_text=text,
        )

    def publish_action(
        self,
        lease: InitiativeLease | Mapping[str, Any],
        decision_id: str,
        *,
        action_id: str,
        public_description: str | None = None,
    ) -> PublicPersonEvent:
        action_id = _public_identifier(action_id, "action_id")
        description = (
            _validate_public_text(
                public_description,
                "public_description",
                maximum_bytes=2048,
            )
            if public_description is not None
            else None
        )
        return self._publish(
            lease,
            decision_id,
            event_kind="action",
            action_id=action_id,
            public_action_description=description,
        )

    def publish_leave(
        self,
        lease: InitiativeLease | Mapping[str, Any],
        decision_id: str,
        *,
        action_id: str,
        public_description: str | None = None,
    ) -> PublicPersonEvent:
        action_id = _public_identifier(action_id, "action_id")
        description = (
            _validate_public_text(
                public_description,
                "public_description",
                maximum_bytes=2048,
            )
            if public_description is not None
            else None
        )
        return self._publish(
            lease,
            decision_id,
            event_kind="leave",
            action_id=action_id,
            public_action_description=description,
        )

    def record_ignore(
        self,
        lease: InitiativeLease | Mapping[str, Any],
        decision_id: str,
    ) -> DecisionDisposition:
        """Consume an ignore decision without manufacturing public content."""

        decision_id = _canonical_id(decision_id, "decision_id")
        with self._lock:
            active, evidence = self._claim_evidence_locked(
                lease,
                decision_id,
                expected_kind="ignore",
                require_event_capacity=False,
            )
            evidence.consumed = True
            return DecisionDisposition(
                person_id=active.person_id,
                activation_revision=active.activation_revision,
                decision_id=evidence.decision_id,
                decision_outcome=evidence.outcome,
                provenance=PUBLIC_PROVENANCE["ignore"],
                activation_binding_digest=self._binding_digest(active),
            )

    def poll(
        self,
        lease: InitiativeLease | Mapping[str, Any],
        *,
        limit: int | None = None,
    ) -> tuple[PublicPersonEvent, ...]:
        if limit is None:
            limit = min(16, self.max_events)
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("limit must be an integer")
        if not 1 <= limit <= self.max_events:
            raise ValueError(f"limit must be from 1 to {self.max_events}")
        with self._lock:
            self._require_lease_locked(lease)
            self._expire_locked(self._now_locked())
            return tuple(
                replace(queued.public_event)
                for queued in list(self._events.values())[:limit]
            )

    def acknowledge(
        self,
        lease: InitiativeLease | Mapping[str, Any],
        event_id: str,
    ) -> bool:
        event_id = _canonical_id(event_id, "event_id")
        with self._lock:
            active = self._require_lease_locked(lease)
            self._expire_locked(self._now_locked())
            queued = self._events.get(event_id)
            if queued is None:
                return False
            if not secrets.compare_digest(queued.session_nonce, active.session_nonce):
                raise PersonEventLeaseError("queued event is not bound to the active session")
            del self._events[event_id]
            return True

    def snapshot(self, lease: InitiativeLease | Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            active = self._require_lease_locked(lease)
            self._expire_locked(self._now_locked())
            consumed = sum(evidence.consumed for evidence in self._decisions.values())
            return {
                "lease_binding": {
                    "person_id": active.person_id,
                    "activation_revision": active.activation_revision,
                    "activation_binding_digest": self._binding_digest(active),
                },
                "pending_event_count": len(self._events),
                "decision_evidence_count": len(self._decisions),
                "consumed_decision_count": consumed,
                "storage": "memory_only",
                "model_called": False,
                "action_executed": False,
                "memory_persisted": False,
                "relationship_changed": False,
            }

    def __getstate__(self) -> None:
        raise TypeError("PersonInitiatedEventQueue is memory-only and not serializable")

    def _publish(
        self,
        lease: InitiativeLease | Mapping[str, Any],
        decision_id: str,
        *,
        event_kind: str,
        spoken_text: str | None = None,
        action_id: str | None = None,
        public_action_description: str | None = None,
    ) -> PublicPersonEvent:
        decision_id = _canonical_id(decision_id, "decision_id")
        if event_kind not in PUBLIC_EVENT_KINDS:
            raise ValueError("unsupported public event kind")
        with self._lock:
            active, evidence = self._claim_evidence_locked(
                lease,
                decision_id,
                expected_kind=event_kind,
                require_event_capacity=True,
            )
            now = self._now_locked()
            event_id = f"person_event_{secrets.token_hex(12)}"
            channel = "public_SPOKEN" if event_kind == "speech" else "public_action_intent"
            event = PublicPersonEvent(
                event_id=event_id,
                sequence=self._next_sequence,
                person_id=active.person_id,
                activation_revision=active.activation_revision,
                event_kind=event_kind,
                channel=channel,
                spoken_text=spoken_text,
                action_id=action_id,
                public_action_description=public_action_description,
                decision_id=evidence.decision_id,
                decision_outcome=evidence.outcome,
                provenance=PUBLIC_PROVENANCE[event_kind],
                activation_binding_digest=self._binding_digest(active),
            )
            evidence.consumed = True
            self._events[event_id] = _QueuedEvent(
                public_event=event,
                session_nonce=active.session_nonce,
                created_monotonic=now,
                expires_monotonic=now + self.event_ttl_seconds,
            )
            self._next_sequence += 1
            return replace(event)

    def _claim_evidence_locked(
        self,
        lease: InitiativeLease | Mapping[str, Any],
        decision_id: str,
        *,
        expected_kind: str,
        require_event_capacity: bool,
    ) -> tuple[InitiativeLease, _DecisionEvidence]:
        active = self._require_lease_locked(lease)
        now = self._now_locked()
        self._expire_locked(now)
        evidence = self._decisions.get(decision_id)
        if evidence is None:
            raise PersonEventEvidenceError(
                "a prior unexpired registered private DecisionOpportunity is required"
            )
        if evidence.consumed:
            raise PersonEventEvidenceError("decision evidence has already been consumed")
        if (
            evidence.person_id != active.person_id
            or evidence.activation_revision != active.activation_revision
            or not secrets.compare_digest(evidence.session_nonce, active.session_nonce)
        ):
            raise PersonEventEvidenceError("decision evidence binding is not exact")
        actual_kind = DECISION_TO_PUBLIC_KIND[evidence.outcome]
        if actual_kind != expected_kind:
            raise PersonEventEvidenceError(
                f"decision outcome {evidence.outcome!r} cannot publish {expected_kind!r}"
            )
        if require_event_capacity and len(self._events) >= self.max_events:
            raise PersonEventQueueFullError(
                "public event capacity is full; no unacknowledged event was dropped"
            )
        return active, evidence

    def _require_lease_locked(
        self,
        lease: InitiativeLease | Mapping[str, Any],
    ) -> InitiativeLease:
        active = self._lease
        if active is None:
            raise PersonEventLeaseError("no person-event activation is active")
        supplied = self._coerce_lease(lease)
        if (
            supplied.person_id != active.person_id
            or supplied.activation_revision != active.activation_revision
            or not secrets.compare_digest(supplied.session_nonce, active.session_nonce)
        ):
            raise PersonEventLeaseError("person-event lease does not match the active person")
        return active

    @staticmethod
    def _coerce_lease(lease: InitiativeLease | Mapping[str, Any]) -> InitiativeLease:
        if isinstance(lease, InitiativeLease):
            supplied = lease
        elif isinstance(lease, Mapping) and frozenset(lease) == _LEASE_FIELDS:
            supplied = InitiativeLease(
                person_id=lease["person_id"],
                activation_revision=lease["activation_revision"],
                session_nonce=lease["session_nonce"],
            )
        else:
            raise PersonEventLeaseError("an exact initiative lease is required")
        _canonical_id(supplied.person_id, "person_id")
        if isinstance(supplied.activation_revision, bool) or not isinstance(
            supplied.activation_revision,
            (str, int),
        ):
            raise PersonEventLeaseError("activation_revision must be a string or integer")
        if isinstance(supplied.activation_revision, str):
            _canonical_id(supplied.activation_revision, "activation_revision")
        if not isinstance(supplied.session_nonce, str) or len(supplied.session_nonce) < 16:
            raise PersonEventLeaseError("session_nonce is invalid")
        return supplied

    @staticmethod
    def _binding_digest(lease: InitiativeLease) -> str:
        payload = (
            f"{lease.person_id}\0{lease.activation_revision}\0{lease.session_nonce}"
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _now_locked(self) -> float:
        now = self._monotonic()
        if isinstance(now, bool) or not isinstance(now, (int, float)):
            raise TypeError("monotonic clock must return a finite number")
        result = float(now)
        if not math.isfinite(result):
            raise ValueError("monotonic clock must return a finite number")
        return result

    def _expire_locked(self, now: float) -> None:
        expired_events = [
            event_id
            for event_id, queued in self._events.items()
            if queued.expires_monotonic <= now
        ]
        for event_id in expired_events:
            del self._events[event_id]
        expired_decisions = [
            decision_id
            for decision_id, evidence in self._decisions.items()
            if evidence.expires_monotonic <= now
        ]
        for decision_id in expired_decisions:
            del self._decisions[decision_id]

    def _purge_locked(self) -> dict[str, int]:
        removed = {
            "events_purged": len(self._events),
            "decision_evidence_purged": len(self._decisions),
        }
        self._lease = None
        self._decisions = {}
        self._events = {}
        self._next_sequence = 1
        return removed
