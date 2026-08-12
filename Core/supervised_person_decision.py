"""Default-off supervised private-decision bridge for one active person.

The existing :mod:`shared_person_initiative` evaluator creates a bounded
``DecisionOpportunity``.  This module lets a supplied adapter make exactly one
structured private choice for that opportunity and, only when that choice is
compatible with the opportunity, passes public speech/action/leave content to
``PersonInitiatedEventQueue``.

It deliberately has no model backend, timer loop, device access, persistence,
memory writer, relationship writer, action executor, canned dialogue, or
fallback response.  A malformed or stale result fails closed and is never
retried.  The caller owns supervision and any later model adapter.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import secrets
import threading
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Mapping, Protocol

try:  # Support both ``Core.*`` and direct Core-directory imports.
    from .person_initiated_event_queue import (
        PersonInitiatedEventQueue,
        PublicPersonEvent,
    )
    from .shared_person_initiative import DecisionOpportunity, InitiativeLease
except ImportError:  # pragma: no cover - exercised by direct-import setups.
    from person_initiated_event_queue import PersonInitiatedEventQueue, PublicPersonEvent
    from shared_person_initiative import DecisionOpportunity, InitiativeLease


REQUEST_SCHEMA_VERSION = "supervised_person_private_decision_request_v1"
RESULT_SCHEMA_VERSION = "supervised_person_private_decision_result_v1"
PRIVATE_CHOICES = frozenset({"speak", "action", "continue", "ignore", "leave"})
_CHOICES_BY_OPPORTUNITY = {
    "consider_speaking": frozenset({"speak", "continue", "ignore"}),
    "consider_action": frozenset({"action", "continue", "ignore"}),
    "leave": frozenset({"leave", "continue", "ignore"}),
    "ignore": frozenset({"ignore"}),
    "continue_activity": frozenset({"continue", "ignore"}),
    "defer": frozenset({"continue", "ignore"}),
    "private_decision_pending": frozenset({"continue", "ignore"}),
}
_PUBLIC_CHOICES = frozenset({"speak", "action", "leave"})
_RESULT_FIELDS = frozenset(
    {
        "schema_version",
        "decision_id",
        "person_id",
        "activation_revision",
        "pacing_profile_id",
        "profile_revision",
        "context_id",
        "choice",
        "confidence",
        "spoken_text",
        "action_id",
        "action_description",
    }
)
_CONTEXT_CHANNELS = frozenset(
    {"factual_runtime_truth", "private_mind", "public_history"}
)
_CANONICAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_DENSE_BASE64 = re.compile(r"(?:[A-Za-z0-9+/]{160,}={0,2})")
_RAW_MARKERS = (
    "data:image/",
    "data:audio/",
    "data:video/",
    "base64,",
    "raw_sensory",
    "pixel_buffer",
    "audio_samples",
    "pcm_bytes",
)
_PUBLIC_PRIVATE_MARKERS = (
    "private_thought",
    "private-thought",
    "internal_monologue",
    "internal-monologue",
    "hidden_reasoning",
    "hidden-reasoning",
    "chain_of_thought",
    "chain-of-thought",
    *_RAW_MARKERS,
)
_PRIVATE_ID_PARTS = (
    "privatethought",
    "internalmonologue",
    "hiddenreasoning",
    "chainofthought",
    "rawsensory",
    "pixelbuffer",
    "audiosamples",
    "pcmbytes",
)


class SupervisedDecisionError(RuntimeError):
    """Base error for the default-off supervised decision bridge."""


class DecisionActivationError(PermissionError, SupervisedDecisionError):
    """Raised when an operation lacks the exact active-person lease."""


class DecisionBindingError(ValueError, SupervisedDecisionError):
    """Raised when opportunity, profile, or context bindings do not match."""


class DecisionAdapterError(SupervisedDecisionError):
    """Raised when the supplied adapter cannot produce one usable result."""


class DecisionSchemaError(ValueError, SupervisedDecisionError):
    """Raised when an adapter result violates the exact result schema."""


class DecisionLimitError(SupervisedDecisionError):
    """Raised when a per-activation technical anti-runaway bound is reached."""


class PrivateDecisionAdapter(Protocol):
    """Minimal adapter protocol; live model selection remains outside this module."""

    def decide(self, request: Mapping[str, Any]) -> Mapping[str, Any] | str:
        """Return one exact JSON-compatible decision object or JSON string."""


def _canonical_id(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _CANONICAL_ID.fullmatch(value):
        raise ValueError(f"{field_name} must be a canonical identifier")
    return value


def _public_id(value: Any, field_name: str) -> str:
    result = _canonical_id(value, field_name)
    normalized = re.sub(r"[_.:-]", "", result.casefold())
    if any(marker in normalized for marker in _PRIVATE_ID_PARTS):
        raise ValueError(f"{field_name} contains a private/raw identifier marker")
    return result


def _validate_revision(value: Any, field_name: str = "activation_revision") -> str | int:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise TypeError(f"{field_name} must be a string or integer")
    if isinstance(value, str):
        _canonical_id(value, field_name)
    return value


def _bounded_int(value: Any, field_name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{field_name} must be from {minimum} to {maximum}")
    return value


def _unit(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a finite number from 0 to 1")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{field_name} must be from 0 to 1")
    return result


def _bounded_text(
    value: Any,
    field_name: str,
    *,
    maximum_bytes: int,
    allow_private_markers: bool,
) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty exact text")
    if len(value.encode("utf-8")) > maximum_bytes:
        raise ValueError(f"{field_name} exceeds its byte limit")
    if any(ord(character) < 32 and character not in "\t\n\r" for character in value):
        raise ValueError(f"{field_name} contains binary control data")
    folded = value.casefold()
    markers = _RAW_MARKERS if allow_private_markers else _PUBLIC_PRIVATE_MARKERS
    if any(marker in folded for marker in markers) or _DENSE_BASE64.search(value):
        raise ValueError(f"{field_name} contains private/raw payload material")
    return value


def _canonical_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _lease_digest(lease: InitiativeLease) -> str:
    encoded = (
        f"{lease.person_id}\0{lease.activation_revision}\0{lease.session_nonce}"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class DecisionContextItem:
    """One bounded context item, never raw camera/audio/media data."""

    item_id: str
    channel: str
    text: str
    certainty: float
    source_ref_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _canonical_id(self.item_id, "item_id")
        if self.channel not in _CONTEXT_CHANNELS:
            raise ValueError("unsupported decision-context channel")
        _bounded_text(
            self.text,
            "context item text",
            maximum_bytes=2048,
            allow_private_markers=True,
        )
        _unit(self.certainty, "certainty")
        if not isinstance(self.source_ref_ids, tuple):
            raise TypeError("source_ref_ids must be a tuple")
        if len(self.source_ref_ids) > 32:
            raise ValueError("source_ref_ids exceeds its bounded count")
        for source_ref_id in self.source_ref_ids:
            _canonical_id(source_ref_id, "source_ref_id")

    def as_private_request_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "channel": self.channel,
            "text": self.text,
            "certainty": float(self.certainty),
            "source_ref_ids": list(self.source_ref_ids),
        }


@dataclass(frozen=True, slots=True)
class ExactDecisionContext:
    """Exact ephemeral context for one initiative opportunity."""

    context_id: str
    person_id: str
    activation_revision: str | int
    decision_id: str
    considered_cue_ids: tuple[str, ...]
    excluded_own_tts_cue_ids: tuple[str, ...]
    separate_input_turn_ids: tuple[str, ...]
    items: tuple[DecisionContextItem, ...]
    external_turn_id: str = ""

    def __post_init__(self) -> None:
        _canonical_id(self.context_id, "context_id")
        _canonical_id(self.person_id, "person_id")
        _validate_revision(self.activation_revision)
        _canonical_id(self.decision_id, "decision_id")
        for field_name in (
            "considered_cue_ids",
            "excluded_own_tts_cue_ids",
            "separate_input_turn_ids",
        ):
            values = getattr(self, field_name)
            if not isinstance(values, tuple):
                raise TypeError(f"{field_name} must be a tuple")
            if len(values) > 64:
                raise ValueError(f"{field_name} exceeds its bounded count")
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
            for value in values:
                _canonical_id(value, field_name)
        if not isinstance(self.items, tuple):
            raise TypeError("items must be a tuple")
        if not 1 <= len(self.items) <= 64:
            raise ValueError("items must contain from 1 to 64 bounded items")
        if not all(isinstance(item, DecisionContextItem) for item in self.items):
            raise TypeError("every item must be a DecisionContextItem")
        item_ids = [item.item_id for item in self.items]
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("context item IDs must be unique")
        if self.external_turn_id:
            _canonical_id(self.external_turn_id, "external_turn_id")

    def as_private_request_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "person_id": self.person_id,
            "activation_revision": self.activation_revision,
            "decision_id": self.decision_id,
            "considered_cue_ids": list(self.considered_cue_ids),
            "excluded_own_tts_cue_ids": list(self.excluded_own_tts_cue_ids),
            "separate_input_turn_ids": list(self.separate_input_turn_ids),
            "external_turn_id": self.external_turn_id or None,
            "items": [item.as_private_request_dict() for item in self.items],
        }


@dataclass(frozen=True, slots=True)
class PersonDecisionProfile:
    """Exact per-person decision profile and per-activation technical limits."""

    person_id: str
    pacing_profile_id: str
    profile_revision: str
    decision_style_facts: tuple[str, ...]
    allowed_action_ids: tuple[str, ...]
    max_model_calls_per_activation: int = 16
    max_public_events_per_activation: int = 8
    max_consecutive_public_events_without_external_input: int = 2
    max_adapter_response_bytes: int = 12_288
    max_spoken_bytes: int = 8_192
    max_action_description_bytes: int = 2_048

    def __post_init__(self) -> None:
        _canonical_id(self.person_id, "person_id")
        _canonical_id(self.pacing_profile_id, "pacing_profile_id")
        _canonical_id(self.profile_revision, "profile_revision")
        if not isinstance(self.decision_style_facts, tuple):
            raise TypeError("decision_style_facts must be a tuple")
        if not 1 <= len(self.decision_style_facts) <= 32:
            raise ValueError("decision_style_facts must contain from 1 to 32 facts")
        for index, value in enumerate(self.decision_style_facts):
            _bounded_text(
                value,
                f"decision_style_facts[{index}]",
                maximum_bytes=1024,
                allow_private_markers=True,
            )
        if not isinstance(self.allowed_action_ids, tuple):
            raise TypeError("allowed_action_ids must be a tuple")
        if len(self.allowed_action_ids) > 64:
            raise ValueError("allowed_action_ids exceeds its bounded count")
        if len(set(self.allowed_action_ids)) != len(self.allowed_action_ids):
            raise ValueError("allowed_action_ids must be unique")
        for action_id in self.allowed_action_ids:
            _public_id(action_id, "allowed_action_id")
        _bounded_int(
            self.max_model_calls_per_activation,
            "max_model_calls_per_activation",
            1,
            64,
        )
        _bounded_int(
            self.max_public_events_per_activation,
            "max_public_events_per_activation",
            0,
            32,
        )
        _bounded_int(
            self.max_consecutive_public_events_without_external_input,
            "max_consecutive_public_events_without_external_input",
            0,
            8,
        )
        _bounded_int(
            self.max_adapter_response_bytes,
            "max_adapter_response_bytes",
            512,
            65_536,
        )
        _bounded_int(self.max_spoken_bytes, "max_spoken_bytes", 64, 16_384)
        _bounded_int(
            self.max_action_description_bytes,
            "max_action_description_bytes",
            64,
            4_096,
        )

    def binding_dict(self) -> dict[str, Any]:
        return {
            "person_id": self.person_id,
            "pacing_profile_id": self.pacing_profile_id,
            "profile_revision": self.profile_revision,
            "decision_style_facts": list(self.decision_style_facts),
            "allowed_action_ids": list(self.allowed_action_ids),
            "limits": {
                "max_model_calls_per_activation": self.max_model_calls_per_activation,
                "max_public_events_per_activation": self.max_public_events_per_activation,
                "max_consecutive_public_events_without_external_input": (
                    self.max_consecutive_public_events_without_external_input
                ),
                "max_adapter_response_bytes": self.max_adapter_response_bytes,
                "max_spoken_bytes": self.max_spoken_bytes,
                "max_action_description_bytes": self.max_action_description_bytes,
            },
        }


@dataclass(frozen=True, slots=True)
class DecisionExecutionReceipt:
    """Public-safe receipt; adapter output and private context are omitted."""

    person_id: str
    activation_revision: str | int
    decision_id: str
    pacing_profile_id: str
    profile_revision: str
    context_id: str
    choice: str
    confidence: float
    adapter_invocations: int
    activation_binding_digest: str
    profile_binding_digest: str
    context_binding_digest: str
    public_event: PublicPersonEvent | None = None
    quiet_reason: str | None = None

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "person_id": self.person_id,
            "activation_revision": self.activation_revision,
            "decision_id": self.decision_id,
            "pacing_profile_id": self.pacing_profile_id,
            "profile_revision": self.profile_revision,
            "context_id": self.context_id,
            "choice": self.choice,
            "confidence": self.confidence,
            "adapter_invocations": self.adapter_invocations,
            "activation_binding_digest": self.activation_binding_digest,
            "profile_binding_digest": self.profile_binding_digest,
            "context_binding_digest": self.context_binding_digest,
            "public_event": (
                self.public_event.as_public_dict() if self.public_event else None
            ),
            "quiet_reason": self.quiet_reason,
            "private_profile_exposed": False,
            "private_context_exposed": False,
            "raw_adapter_result_retained": False,
            "private_reasoning_requested": False,
            "memory_persisted": False,
            "relationship_changed": False,
            "action_executed": False,
            "live_default_enabled": False,
        }


@dataclass(slots=True)
class _ActivationState:
    lease: InitiativeLease
    profile_binding_digest: str
    model_calls: int = 0
    public_events: int = 0
    consecutive_public_events_without_external_input: int = 0
    last_external_turn_id: str = ""
    in_flight_decision_ids: set[str] = field(default_factory=set)
    completed_decision_ids: set[str] = field(default_factory=set)


class SupervisedPersonDecisionEngine:
    """One default-off, exact-lease private-decision bridge.

    No decision loop is included.  The owner-integrated caller must explicitly
    supply each opportunity and adapter call while the supervised feature is
    enabled.  Anti-runaway controls are count bounds, not a universal cooldown.
    """

    def __init__(self, event_queue: PersonInitiatedEventQueue) -> None:
        if not isinstance(event_queue, PersonInitiatedEventQueue):
            raise TypeError("event_queue must be a PersonInitiatedEventQueue")
        self._event_queue = event_queue
        self._lock = threading.RLock()
        self._state: _ActivationState | None = None

    def activate(
        self,
        lease: InitiativeLease,
        profile: PersonDecisionProfile,
        *,
        supervised: bool,
        enabled: bool,
    ) -> dict[str, Any]:
        """Bind one exact lease; both explicit gates must be true."""

        supplied = self._validate_lease_shape(lease)
        if not isinstance(profile, PersonDecisionProfile):
            raise TypeError("profile must be a PersonDecisionProfile")
        if supervised is not True or enabled is not True:
            raise DecisionActivationError(
                "private decision activation requires explicit supervision and enablement"
            )
        if profile.person_id != supplied.person_id:
            raise DecisionBindingError("profile person does not match the exact lease")
        profile_digest = _canonical_digest(profile.binding_dict())
        with self._lock:
            self._event_queue.activate(supplied)
            self._state = _ActivationState(replace(supplied), profile_digest)
            return self.snapshot(supplied)

    def switch_person(
        self,
        current_lease: InitiativeLease,
        new_lease: InitiativeLease,
        new_profile: PersonDecisionProfile,
        *,
        supervised: bool,
        enabled: bool,
    ) -> dict[str, Any]:
        supplied_new = self._validate_lease_shape(new_lease)
        if not isinstance(new_profile, PersonDecisionProfile):
            raise TypeError("new_profile must be a PersonDecisionProfile")
        if supervised is not True or enabled is not True:
            raise DecisionActivationError(
                "private decision switching requires explicit supervision and enablement"
            )
        if new_profile.person_id != supplied_new.person_id:
            raise DecisionBindingError("new profile person does not match the new lease")
        with self._lock:
            self._require_lease_locked(current_lease)
            self._event_queue.switch_person(current_lease, supplied_new)
            self._state = _ActivationState(
                replace(supplied_new),
                _canonical_digest(new_profile.binding_dict()),
            )
            return self.snapshot(supplied_new)

    def deactivate(self, lease: InitiativeLease) -> dict[str, int]:
        with self._lock:
            state = self._require_lease_locked(lease)
            removed = self._event_queue.deactivate(state.lease)
            in_flight = len(state.in_flight_decision_ids)
            completed = len(state.completed_decision_ids)
            self._state = None
            return {
                "events_purged": int(removed.get("events_purged", 0)),
                "decision_evidence_purged": int(
                    removed.get("decision_evidence_purged", 0)
                ),
                "in_flight_invalidated": in_flight,
                "completed_ids_purged": completed,
            }

    def note_external_turn(self, lease: InitiativeLease, turn_id: str) -> None:
        """Reset only this activation's consecutive-public-event counter."""

        turn_id = _canonical_id(turn_id, "turn_id")
        with self._lock:
            state = self._require_lease_locked(lease)
            if state.last_external_turn_id != turn_id:
                state.last_external_turn_id = turn_id
                state.consecutive_public_events_without_external_input = 0

    def decide_once(
        self,
        lease: InitiativeLease,
        opportunity: DecisionOpportunity,
        profile: PersonDecisionProfile,
        context: ExactDecisionContext,
        adapter: PrivateDecisionAdapter | Callable[[Mapping[str, Any]], Mapping[str, Any] | str],
    ) -> DecisionExecutionReceipt:
        """Invoke exactly one supplied adapter and publish at most one event."""

        if not isinstance(opportunity, DecisionOpportunity):
            raise TypeError("opportunity must be a DecisionOpportunity")
        if not isinstance(profile, PersonDecisionProfile):
            raise TypeError("profile must be a PersonDecisionProfile")
        if not isinstance(context, ExactDecisionContext):
            raise TypeError("context must be an ExactDecisionContext")

        with self._lock:
            state = self._require_lease_locked(lease)
            self._validate_bindings_locked(state, opportunity, profile, context)
            if state.model_calls >= profile.max_model_calls_per_activation:
                raise DecisionLimitError("per-activation model-call bound reached")
            if (
                opportunity.decision_id in state.in_flight_decision_ids
                or opportunity.decision_id in state.completed_decision_ids
            ):
                raise DecisionBindingError("decision opportunity was already processed")
            allowed_choices = set(_CHOICES_BY_OPPORTUNITY[opportunity.outcome])
            public_budget_reasons: list[str] = []
            if state.public_events >= profile.max_public_events_per_activation:
                allowed_choices.difference_update(_PUBLIC_CHOICES)
                public_budget_reasons.append("per_activation_public_event_bound")
            if (
                state.consecutive_public_events_without_external_input
                >= profile.max_consecutive_public_events_without_external_input
            ):
                allowed_choices.difference_update(_PUBLIC_CHOICES)
                public_budget_reasons.append("consecutive_public_event_bound")
            if not allowed_choices:
                allowed_choices = {"continue", "ignore"}
            state.model_calls += 1
            state.in_flight_decision_ids.add(opportunity.decision_id)
            request = self._build_request(
                state,
                opportunity,
                profile,
                context,
                allowed_choices=frozenset(allowed_choices),
                public_budget_reasons=tuple(public_budget_reasons),
            )
            activation_digest = _lease_digest(state.lease)
            profile_digest = state.profile_binding_digest
            context_digest = _canonical_digest(context.as_private_request_dict())

        try:
            raw_result = self._invoke_adapter_once(adapter, request)
            result = self._validate_result(
                raw_result,
                opportunity=opportunity,
                profile=profile,
                context=context,
                allowed_choices=frozenset(allowed_choices),
            )
        except Exception:
            with self._lock:
                active = self._state
                if (
                    active is not None
                    and secrets.compare_digest(
                        _lease_digest(active.lease),
                        activation_digest,
                    )
                ):
                    active.in_flight_decision_ids.discard(opportunity.decision_id)
            raise

        with self._lock:
            try:
                state = self._require_lease_locked(lease)
                self._validate_bindings_locked(state, opportunity, profile, context)
            except Exception:
                active = self._state
                if (
                    active is not None
                    and secrets.compare_digest(
                        _lease_digest(active.lease),
                        activation_digest,
                    )
                ):
                    active.in_flight_decision_ids.discard(opportunity.decision_id)
                raise
            if opportunity.decision_id not in state.in_flight_decision_ids:
                raise DecisionActivationError(
                    "decision activation changed while the adapter was running"
                )
            choice = result["choice"]
            public_event: PublicPersonEvent | None = None
            quiet_reason: str | None = None
            try:
                if choice in _PUBLIC_CHOICES:
                    self._event_queue.register_private_decision(lease, opportunity)
                    if choice == "speak":
                        public_event = self._event_queue.publish_speech(
                            lease,
                            opportunity.decision_id,
                            result["spoken_text"],
                        )
                    elif choice == "action":
                        public_event = self._event_queue.publish_action(
                            lease,
                            opportunity.decision_id,
                            action_id=result["action_id"],
                            public_description=result["action_description"],
                        )
                    else:
                        public_event = self._event_queue.publish_leave(
                            lease,
                            opportunity.decision_id,
                            action_id=result["action_id"],
                            public_description=result["action_description"],
                        )
                    state.public_events += 1
                    state.consecutive_public_events_without_external_input += 1
                else:
                    quiet_reason = (
                        "person_chose_continue_current_activity"
                        if choice == "continue"
                        else "person_chose_ignore"
                    )
            except Exception:
                state.in_flight_decision_ids.discard(opportunity.decision_id)
                state.completed_decision_ids.add(opportunity.decision_id)
                raise
            state.in_flight_decision_ids.discard(opportunity.decision_id)
            state.completed_decision_ids.add(opportunity.decision_id)
            return DecisionExecutionReceipt(
                person_id=state.lease.person_id,
                activation_revision=state.lease.activation_revision,
                decision_id=opportunity.decision_id,
                pacing_profile_id=profile.pacing_profile_id,
                profile_revision=profile.profile_revision,
                context_id=context.context_id,
                choice=choice,
                confidence=result["confidence"],
                adapter_invocations=1,
                activation_binding_digest=activation_digest,
                profile_binding_digest=profile_digest,
                context_binding_digest=context_digest,
                public_event=public_event,
                quiet_reason=quiet_reason,
            )

    def snapshot(self, lease: InitiativeLease) -> dict[str, Any]:
        with self._lock:
            state = self._require_lease_locked(lease)
            return {
                "lease_binding": {
                    "person_id": state.lease.person_id,
                    "activation_revision": state.lease.activation_revision,
                    "activation_binding_digest": _lease_digest(state.lease),
                },
                "profile_binding_digest": state.profile_binding_digest,
                "model_calls": state.model_calls,
                "public_events": state.public_events,
                "consecutive_public_events_without_external_input": (
                    state.consecutive_public_events_without_external_input
                ),
                "last_external_turn_id": state.last_external_turn_id or None,
                "in_flight_count": len(state.in_flight_decision_ids),
                "completed_decision_count": len(state.completed_decision_ids),
                "storage": "memory_only",
                "timer_loop_present": False,
                "universal_cooldown_present": False,
                "live_default_enabled": False,
                "memory_persisted": False,
                "relationship_changed": False,
                "action_executed": False,
            }

    def __getstate__(self) -> None:
        raise TypeError("SupervisedPersonDecisionEngine is memory-only and not serializable")

    @staticmethod
    def _validate_lease_shape(lease: InitiativeLease) -> InitiativeLease:
        if not isinstance(lease, InitiativeLease):
            raise DecisionActivationError("an exact InitiativeLease is required")
        _canonical_id(lease.person_id, "lease person_id")
        _validate_revision(lease.activation_revision)
        if not isinstance(lease.session_nonce, str) or len(lease.session_nonce) < 32:
            raise DecisionActivationError("lease session_nonce is invalid")
        return lease

    def _require_lease_locked(self, lease: InitiativeLease) -> _ActivationState:
        supplied = self._validate_lease_shape(lease)
        state = self._state
        if state is None:
            raise DecisionActivationError("no supervised private-decision activation")
        if (
            supplied.person_id != state.lease.person_id
            or supplied.activation_revision != state.lease.activation_revision
            or not secrets.compare_digest(supplied.session_nonce, state.lease.session_nonce)
        ):
            raise DecisionActivationError("lease does not match the active person")
        return state

    @staticmethod
    def _validate_bindings_locked(
        state: _ActivationState,
        opportunity: DecisionOpportunity,
        profile: PersonDecisionProfile,
        context: ExactDecisionContext,
    ) -> None:
        if opportunity.outcome not in _CHOICES_BY_OPPORTUNITY:
            raise DecisionBindingError("unsupported initiative opportunity outcome")
        _canonical_id(opportunity.decision_id, "decision_id")
        _canonical_id(opportunity.person_id, "opportunity person_id")
        _validate_revision(opportunity.activation_revision)
        _canonical_id(opportunity.pacing_profile_id, "opportunity pacing_profile_id")
        if opportunity.person_id != state.lease.person_id:
            raise DecisionBindingError("opportunity person does not match the lease")
        if opportunity.activation_revision != state.lease.activation_revision:
            raise DecisionBindingError("opportunity revision does not match the lease")
        if profile.person_id != state.lease.person_id:
            raise DecisionBindingError("profile person does not match the lease")
        if profile.pacing_profile_id != opportunity.pacing_profile_id:
            raise DecisionBindingError("profile does not match the opportunity")
        if _canonical_digest(profile.binding_dict()) != state.profile_binding_digest:
            raise DecisionBindingError("profile changed after activation")
        if context.person_id != state.lease.person_id:
            raise DecisionBindingError("context person does not match the lease")
        if context.activation_revision != state.lease.activation_revision:
            raise DecisionBindingError("context revision does not match the lease")
        if context.decision_id != opportunity.decision_id:
            raise DecisionBindingError("context does not bind the exact opportunity")
        if context.considered_cue_ids != opportunity.considered_cue_ids:
            raise DecisionBindingError("context considered cues do not match the opportunity")
        if context.excluded_own_tts_cue_ids != opportunity.excluded_own_tts_cue_ids:
            raise DecisionBindingError("context own-TTS exclusions do not match the opportunity")
        if context.separate_input_turn_ids != opportunity.separate_input_turn_ids:
            raise DecisionBindingError("context input turns do not match the opportunity")
        if context.external_turn_id != state.last_external_turn_id:
            raise DecisionBindingError("context external turn is stale or unregistered")

    @staticmethod
    def _build_request(
        state: _ActivationState,
        opportunity: DecisionOpportunity,
        profile: PersonDecisionProfile,
        context: ExactDecisionContext,
        *,
        allowed_choices: frozenset[str],
        public_budget_reasons: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "schema_version": REQUEST_SCHEMA_VERSION,
            "exact_binding": {
                "person_id": state.lease.person_id,
                "activation_revision": state.lease.activation_revision,
                "activation_binding_digest": _lease_digest(state.lease),
                "decision_id": opportunity.decision_id,
                "pacing_profile_id": profile.pacing_profile_id,
                "profile_revision": profile.profile_revision,
                "context_id": context.context_id,
            },
            "opportunity": opportunity.as_dict(),
            "private_profile": profile.binding_dict(),
            "private_context": context.as_private_request_dict(),
            "allowed_choices": sorted(allowed_choices),
            "public_emission_bound_reasons": list(public_budget_reasons),
            "response_contract": {
                "schema_version": RESULT_SCHEMA_VERSION,
                "exact_fields": sorted(_RESULT_FIELDS),
                "reasoning_field_allowed": False,
                "one_choice_only": True,
                "no_fallback_words": True,
                "no_memory_mutation": True,
                "no_relationship_mutation": True,
                "no_action_execution": True,
            },
        }

    @staticmethod
    def _invoke_adapter_once(
        adapter: PrivateDecisionAdapter
        | Callable[[Mapping[str, Any]], Mapping[str, Any] | str],
        request: Mapping[str, Any],
    ) -> Mapping[str, Any] | str:
        method = getattr(adapter, "decide", None)
        callable_adapter = method if callable(method) else adapter
        if not callable(callable_adapter):
            raise TypeError("adapter must be callable or expose decide(request)")
        try:
            return callable_adapter(request)
        except Exception as exc:
            raise DecisionAdapterError(
                f"supplied private-decision adapter failed once: {type(exc).__name__}: {exc}"
            ) from exc

    @staticmethod
    def _validate_result(
        raw_result: Mapping[str, Any] | str,
        *,
        opportunity: DecisionOpportunity,
        profile: PersonDecisionProfile,
        context: ExactDecisionContext,
        allowed_choices: frozenset[str],
    ) -> dict[str, Any]:
        if isinstance(raw_result, str):
            encoded = raw_result.encode("utf-8")
            if len(encoded) > profile.max_adapter_response_bytes:
                raise DecisionSchemaError("adapter result exceeds its byte limit")
            try:
                result = json.loads(raw_result)
            except json.JSONDecodeError as exc:
                raise DecisionSchemaError("adapter result is not exact JSON") from exc
        elif isinstance(raw_result, Mapping):
            try:
                encoded = json.dumps(
                    raw_result,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            except (TypeError, ValueError) as exc:
                raise DecisionSchemaError("adapter result is not JSON-compatible") from exc
            if len(encoded) > profile.max_adapter_response_bytes:
                raise DecisionSchemaError("adapter result exceeds its byte limit")
            result = dict(raw_result)
        else:
            raise DecisionSchemaError("adapter result must be a mapping or JSON object")
        if not isinstance(result, dict) or set(result) != _RESULT_FIELDS:
            raise DecisionSchemaError("adapter result must contain exactly the required fields")
        exact_expected = {
            "schema_version": RESULT_SCHEMA_VERSION,
            "decision_id": opportunity.decision_id,
            "person_id": opportunity.person_id,
            "activation_revision": opportunity.activation_revision,
            "pacing_profile_id": profile.pacing_profile_id,
            "profile_revision": profile.profile_revision,
            "context_id": context.context_id,
        }
        for field_name, expected in exact_expected.items():
            if result[field_name] != expected:
                raise DecisionSchemaError(f"adapter result {field_name} binding mismatch")
        choice = result["choice"]
        if (
            not isinstance(choice, str)
            or choice not in PRIVATE_CHOICES
            or choice not in allowed_choices
        ):
            raise DecisionSchemaError("adapter choice is not allowed for this opportunity")
        try:
            confidence = _unit(result["confidence"], "confidence")
        except (TypeError, ValueError) as exc:
            raise DecisionSchemaError("adapter result confidence is invalid") from exc

        spoken_text = result["spoken_text"]
        action_id = result["action_id"]
        action_description = result["action_description"]
        if choice == "speak":
            try:
                spoken_text = _bounded_text(
                    spoken_text,
                    "spoken_text",
                    maximum_bytes=profile.max_spoken_bytes,
                    allow_private_markers=False,
                )
            except (TypeError, ValueError) as exc:
                raise DecisionSchemaError("spoken_text is not safe public content") from exc
            if action_id is not None or action_description is not None:
                raise DecisionSchemaError("speech result must not contain action fields")
        elif choice in {"action", "leave"}:
            if spoken_text is not None:
                raise DecisionSchemaError("action/leave result must not contain spoken_text")
            try:
                action_id = _public_id(action_id, "action_id")
            except (TypeError, ValueError) as exc:
                raise DecisionSchemaError("action/leave result requires a valid action_id") from exc
            if action_id not in profile.allowed_action_ids:
                raise DecisionSchemaError("action_id is not allowed by the exact person profile")
            if action_description is not None:
                try:
                    action_description = _bounded_text(
                        action_description,
                        "action_description",
                        maximum_bytes=profile.max_action_description_bytes,
                        allow_private_markers=False,
                    )
                except (TypeError, ValueError) as exc:
                    raise DecisionSchemaError(
                        "action_description is not safe public content"
                    ) from exc
        else:
            if spoken_text is not None or action_id is not None or action_description is not None:
                raise DecisionSchemaError("quiet result must not contain public content")
        result.update(
            {
                "choice": choice,
                "confidence": confidence,
                "spoken_text": spoken_text,
                "action_id": action_id,
                "action_description": action_description,
            }
        )
        return result
