"""ROS-independent embodiment session and intention lifecycle primitives.

Protocol v0.2 deliberately separates two domains:

* an upstream system chooses what it remembers and what it wants to say; and
* a robot-side authority decides whether and how a requested physical action is
  executed by a particular body.

Consequently, lifecycle outcomes in this module apply only to physical
execution.  ``REJECTED`` or ``INTERRUPTED`` never instructs an upstream system
to alter memory, revise speech, or suppress a future choice.

The implementation has no ROS imports.  A ROS node or simulator can adapt its
messages to this small state machine while keeping transport concerns outside
the protocol reference.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


DECISION_SCOPE = "physical_execution_only"
MAX_IDENTIFIER_CHARS = 128
MAX_CANONICAL_PAYLOAD_BYTES = 16_384
MAX_JSON_DEPTH = 32
MAX_JSON_CONTAINER_ITEMS = 1_024
MAX_JSON_INTEGER_ABS = (1 << 63) - 1


class ProtocolError(ValueError):
    """Raised when a session cannot be constructed from valid protocol data."""


class ClockRegression(ProtocolError):
    """Raised when an injected monotonic clock moves backwards."""


class UnknownIntent(KeyError):
    """Raised when a lifecycle operation names an unknown intention."""


class InvalidTransition(ProtocolError):
    """Raised when an intention lifecycle transition is not allowed."""


class Capability(str, Enum):
    SPEECH = "speech"
    GAZE = "gaze"
    EXPRESSION = "expression"
    GESTURE = "gesture"


class SessionState(str, Enum):
    ACTIVE = "ACTIVE"
    DISCONNECTED = "DISCONNECTED"
    EXPIRED = "EXPIRED"


class IntentState(str, Enum):
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    INTERRUPTED = "INTERRUPTED"
    EXPIRED = "EXPIRED"


TERMINAL_INTENT_STATES = frozenset(
    {
        IntentState.COMPLETED,
        IntentState.REJECTED,
        IntentState.FAILED,
        IntentState.CANCELLED,
        IntentState.INTERRUPTED,
        IntentState.EXPIRED,
    }
)


class RequestDisposition(str, Enum):
    ADMITTED = "ADMITTED"
    DUPLICATE = "DUPLICATE"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class IntentEvent:
    """One immutable lifecycle observation."""

    state: IntentState
    at_ms: int
    reason_code: str
    detail: str = ""
    decision_scope: str = DECISION_SCOPE


@dataclass(frozen=True)
class IntentSnapshot:
    """Read-only view of one intention known to this session."""

    intent_id: str
    sequence: int
    capability: Capability
    canonical_payload: str
    state: IntentState
    requested_at_ms: int
    updated_at_ms: int
    events: tuple[IntentEvent, ...]
    decision_scope: str = DECISION_SCOPE

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL_INTENT_STATES

    @property
    def payload(self) -> dict[str, Any]:
        """Return a fresh payload object so callers cannot mutate the record."""

        return json.loads(self.canonical_payload)


@dataclass(frozen=True)
class RequestResult:
    """Result of submitting an intention request.

    ``accepted`` means the envelope is a valid new request or an exact retry.
    It is distinct from the robot-side ``IntentState.ACCEPTED`` transition.
    ``created`` is true only when new work entered the in-flight slot.
    """

    disposition: RequestDisposition
    reason_code: str
    detail: str
    intent: Optional[IntentSnapshot] = None
    decision_scope: str = DECISION_SCOPE

    @property
    def accepted(self) -> bool:
        return self.disposition is not RequestDisposition.REJECTED

    @property
    def created(self) -> bool:
        return self.disposition is RequestDisposition.ADMITTED

    @property
    def duplicate(self) -> bool:
        return self.disposition is RequestDisposition.DUPLICATE


@dataclass(frozen=True)
class SessionSnapshot:
    session_id: str
    body_id: str
    source_identity: str
    capabilities: frozenset[Capability]
    state: SessionState
    opened_at_ms: int
    expires_at_ms: int
    last_heartbeat_at_ms: int
    heartbeat_timeout_ms: int
    active_intent_id: Optional[str]
    last_sequence: int
    reason_code: str
    decision_scope: str = DECISION_SCOPE


@dataclass
class _IntentEntry:
    intent_id: str
    sequence: int
    capability: Capability
    canonical_payload: str
    canonical_request: str
    state: IntentState
    requested_at_ms: int
    updated_at_ms: int
    events: list[IntentEvent] = field(default_factory=list)

    def snapshot(self) -> IntentSnapshot:
        return IntentSnapshot(
            intent_id=self.intent_id,
            sequence=self.sequence,
            capability=self.capability,
            canonical_payload=self.canonical_payload,
            state=self.state,
            requested_at_ms=self.requested_at_ms,
            updated_at_ms=self.updated_at_ms,
            events=tuple(self.events),
        )


_ALLOWED_TRANSITIONS = {
    IntentState.REQUESTED: frozenset(
        {
            IntentState.ACCEPTED,
            IntentState.REJECTED,
            IntentState.CANCELLED,
            IntentState.INTERRUPTED,
            IntentState.EXPIRED,
        }
    ),
    IntentState.ACCEPTED: frozenset(
        {
            IntentState.STARTED,
            IntentState.FAILED,
            IntentState.CANCELLED,
            IntentState.INTERRUPTED,
            IntentState.EXPIRED,
        }
    ),
    IntentState.STARTED: frozenset(
        {
            IntentState.COMPLETED,
            IntentState.FAILED,
            IntentState.CANCELLED,
            IntentState.INTERRUPTED,
            IntentState.EXPIRED,
        }
    ),
}


def _monotonic_ms() -> int:
    return time.monotonic_ns() // 1_000_000


def _positive_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ProtocolError(f"{name} must be a positive integer.")
    return value


def _opaque_identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolError(f"{name} must be a non-empty opaque string.")
    if len(value) > MAX_IDENTIFIER_CHARS or any(
        ord(character) < 0x20 or ord(character) == 0x7F for character in value
    ):
        raise ProtocolError(
            f"{name} must be at most {MAX_IDENTIFIER_CHARS} characters and contain no controls."
        )
    return value


def _normalize_json(
    value: Any,
    path: str = "payload",
    *,
    depth: int = 0,
    active_containers: Optional[set[int]] = None,
) -> Any:
    """Copy and validate the JSON data model before canonical serialization."""

    if depth > MAX_JSON_DEPTH:
        raise ProtocolError(f"{path} exceeds the maximum JSON nesting depth.")
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        if abs(value) > MAX_JSON_INTEGER_ABS:
            raise ProtocolError(f"{path} exceeds the signed 64-bit JSON integer bound.")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProtocolError(f"{path} contains a non-finite number.")
        return value
    if active_containers is None:
        active_containers = set()
    if isinstance(value, Mapping):
        if len(value) > MAX_JSON_CONTAINER_ITEMS:
            raise ProtocolError(f"{path} contains too many object members.")
        marker = id(value)
        if marker in active_containers:
            raise ProtocolError(f"{path} contains a recursive object reference.")
        active_containers.add(marker)
        normalized: dict[str, Any] = {}
        try:
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ProtocolError(f"{path} contains a non-string object key.")
                normalized[key] = _normalize_json(
                    item,
                    f"{path}.{key}",
                    depth=depth + 1,
                    active_containers=active_containers,
                )
            return normalized
        finally:
            active_containers.remove(marker)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if len(value) > MAX_JSON_CONTAINER_ITEMS:
            raise ProtocolError(f"{path} contains too many array items.")
        marker = id(value)
        if marker in active_containers:
            raise ProtocolError(f"{path} contains a recursive array reference.")
        active_containers.add(marker)
        try:
            return [
                _normalize_json(
                    item,
                    f"{path}[{index}]",
                    depth=depth + 1,
                    active_containers=active_containers,
                )
                for index, item in enumerate(value)
            ]
        finally:
            active_containers.remove(marker)
    raise ProtocolError(f"{path} contains unsupported type {type(value).__name__}.")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


class EmbodimentSession:
    """State machine for exactly one active embodiment session.

    Identifiers are intentionally opaque.  This class neither parses identity
    claims nor treats ``source_identity`` as ownership of a body.  Capability
    negotiation only limits the four high-level social requests represented by
    :class:`Capability`.
    """

    SUPPORTED_CAPABILITIES = frozenset(Capability)

    def __init__(
        self,
        *,
        session_id: str,
        body_id: str,
        source_identity: str,
        capabilities: Iterable[Capability | str],
        session_ttl_ms: int,
        heartbeat_timeout_ms: int,
        now_ms: Callable[[], int] = _monotonic_ms,
    ) -> None:
        self.session_id = _opaque_identifier(session_id, "session_id")
        self.body_id = _opaque_identifier(body_id, "body_id")
        self.source_identity = _opaque_identifier(source_identity, "source_identity")
        self.session_ttl_ms = _positive_int(session_ttl_ms, "session_ttl_ms")
        self.heartbeat_timeout_ms = _positive_int(
            heartbeat_timeout_ms, "heartbeat_timeout_ms"
        )
        if self.heartbeat_timeout_ms > self.session_ttl_ms:
            raise ProtocolError("heartbeat_timeout_ms cannot exceed session_ttl_ms.")
        if not callable(now_ms):
            raise ProtocolError("now_ms must be callable.")
        self._clock = now_ms
        self._last_observed_ms: Optional[int] = None

        negotiated: set[Capability] = set()
        try:
            for capability in capabilities:
                negotiated.add(Capability(capability))
        except (TypeError, ValueError) as exc:
            raise ProtocolError(
                "capabilities may contain only speech, gaze, expression, and gesture."
            ) from exc
        if not negotiated:
            raise ProtocolError("At least one supported capability is required.")
        self.capabilities = frozenset(negotiated)

        opened_at_ms = self._read_now()
        self.opened_at_ms = opened_at_ms
        self.expires_at_ms = opened_at_ms + self.session_ttl_ms
        self.last_heartbeat_at_ms = opened_at_ms
        self._state = SessionState.ACTIVE
        self._state_reason_code = "SESSION_ACTIVE"
        self._active_intent_id: Optional[str] = None
        self._last_sequence = 0
        self._intents: dict[str, _IntentEntry] = {}

    @property
    def state(self) -> SessionState:
        self.tick()
        return self._state

    @property
    def last_sequence(self) -> int:
        return self._last_sequence

    @property
    def active_intent(self) -> Optional[IntentSnapshot]:
        self.tick()
        if self._active_intent_id is None:
            return None
        return self._intents[self._active_intent_id].snapshot()

    def snapshot(self) -> SessionSnapshot:
        now = self._read_now()
        self._refresh(now)
        return self._snapshot_without_clock()

    def intents(self) -> tuple[IntentSnapshot, ...]:
        now = self._read_now()
        self._refresh(now)
        return tuple(entry.snapshot() for entry in self._intents.values())

    def get_intent(self, intent_id: str) -> IntentSnapshot:
        now = self._read_now()
        self._refresh(now)
        try:
            return self._intents[intent_id].snapshot()
        except KeyError as exc:
            raise UnknownIntent(intent_id) from exc

    def heartbeat(self) -> bool:
        """Refresh liveness while active; an inactive session cannot reconnect."""

        now = self._read_now()
        self._refresh(now)
        if self._state is not SessionState.ACTIVE:
            return False
        self.last_heartbeat_at_ms = now
        return True

    def tick(self) -> SessionSnapshot:
        """Apply clock-driven TTL and heartbeat transitions."""

        now = self._read_now()
        self._refresh(now)
        return self._snapshot_without_clock()

    def disconnect(
        self,
        *,
        reason_code: str = "SESSION_DISCONNECTED",
        detail: str = "Embodiment transport disconnected.",
    ) -> SessionSnapshot:
        """Permanently disconnect this session and interrupt in-flight work."""

        now = self._read_now()
        self._refresh(now)
        if self._state is SessionState.ACTIVE:
            self._state = SessionState.DISCONNECTED
            self._state_reason_code = reason_code
            self._interrupt_active(now, reason_code, detail)
        return self._snapshot_without_clock()

    def request_intent(
        self,
        *,
        intent_id: str,
        sequence: int,
        capability: Capability | str,
        payload: Mapping[str, Any],
    ) -> RequestResult:
        """Admit one intention or suppress an exact retry idempotently."""

        now = self._read_now()
        self._refresh(now)

        try:
            normalized_intent_id = _opaque_identifier(intent_id, "intent_id")
        except ProtocolError as exc:
            return self._rejected_request("INVALID_INTENT_ID", str(exc))
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence <= 0:
            return self._rejected_request(
                "INVALID_SEQUENCE", "sequence must be a positive integer."
            )
        try:
            normalized_capability = Capability(capability)
        except (TypeError, ValueError):
            return self._rejected_request(
                "CAPABILITY_NOT_SUPPORTED",
                "Only speech, gaze, expression, and gesture are supported.",
            )
        if not isinstance(payload, Mapping):
            return self._rejected_request("INVALID_PAYLOAD", "payload must be a JSON object.")
        try:
            normalized_payload = _normalize_json(payload)
            canonical_payload = _canonical_json(normalized_payload)
        except (OverflowError, ProtocolError, RecursionError, TypeError, ValueError) as exc:
            return self._rejected_request("INVALID_PAYLOAD", str(exc))
        if len(canonical_payload.encode("utf-8")) > MAX_CANONICAL_PAYLOAD_BYTES:
            return self._rejected_request(
                "PAYLOAD_TOO_LARGE",
                f"Canonical payload exceeds {MAX_CANONICAL_PAYLOAD_BYTES} UTF-8 bytes.",
            )

        canonical_request = _canonical_json(
            {
                "capability": normalized_capability.value,
                "payload": normalized_payload,
                "sequence": sequence,
            }
        )
        existing = self._intents.get(normalized_intent_id)
        if existing is not None:
            if existing.canonical_request == canonical_request:
                return RequestResult(
                    disposition=RequestDisposition.DUPLICATE,
                    reason_code="DUPLICATE_SUPPRESSED",
                    detail="Exact retry suppressed; no new physical action was created.",
                    intent=existing.snapshot(),
                )
            return RequestResult(
                disposition=RequestDisposition.REJECTED,
                reason_code="INTENT_ID_CONFLICT",
                detail="intent_id was already used for a different canonical request.",
                intent=existing.snapshot(),
            )

        if self._state is not SessionState.ACTIVE:
            return self._rejected_request(
                "SESSION_NOT_ACTIVE",
                f"Session is {self._state.value.lower()} and cannot accept new actions.",
            )
        if normalized_capability not in self.capabilities:
            return self._rejected_request(
                "CAPABILITY_NOT_NEGOTIATED",
                f"Capability '{normalized_capability.value}' is not enabled for this session.",
            )
        if self._active_intent_id is not None:
            return self._rejected_request(
                "INTENT_IN_FLIGHT",
                f"Intent '{self._active_intent_id}' already occupies the single in-flight slot.",
            )
        if sequence <= self._last_sequence:
            return self._rejected_request(
                "SEQUENCE_NOT_MONOTONIC",
                f"sequence must be greater than {self._last_sequence}.",
            )

        event = IntentEvent(
            state=IntentState.REQUESTED,
            at_ms=now,
            reason_code="REQUESTED",
            detail="High-level physical action requested.",
        )
        entry = _IntentEntry(
            intent_id=normalized_intent_id,
            sequence=sequence,
            capability=normalized_capability,
            canonical_payload=canonical_payload,
            canonical_request=canonical_request,
            state=IntentState.REQUESTED,
            requested_at_ms=now,
            updated_at_ms=now,
            events=[event],
        )
        self._intents[normalized_intent_id] = entry
        self._active_intent_id = normalized_intent_id
        self._last_sequence = sequence
        return RequestResult(
            disposition=RequestDisposition.ADMITTED,
            reason_code="REQUESTED",
            detail="Request entered the single in-flight slot.",
            intent=entry.snapshot(),
        )

    def transition(
        self,
        intent_id: str,
        new_state: IntentState | str,
        *,
        reason_code: Optional[str] = None,
        detail: str = "",
    ) -> IntentSnapshot:
        """Apply an allowed physical-execution lifecycle transition."""

        try:
            normalized_state = IntentState(new_state)
        except (TypeError, ValueError) as exc:
            raise InvalidTransition(f"Unknown intention state: {new_state!r}.") from exc
        now = self._read_now()
        self._refresh(now)
        try:
            entry = self._intents[intent_id]
        except KeyError as exc:
            raise UnknownIntent(intent_id) from exc
        allowed = _ALLOWED_TRANSITIONS.get(entry.state, frozenset())
        if normalized_state not in allowed:
            raise InvalidTransition(
                f"Cannot transition intent '{intent_id}' from "
                f"{entry.state.value} to {normalized_state.value}."
            )
        self._apply_transition(
            entry,
            normalized_state,
            now,
            reason_code or normalized_state.value,
            detail,
        )
        return entry.snapshot()

    def accept(self, intent_id: str, *, detail: str = "") -> IntentSnapshot:
        return self.transition(
            intent_id,
            IntentState.ACCEPTED,
            reason_code="PHYSICAL_EXECUTION_ACCEPTED",
            detail=detail,
        )

    def reject(
        self, intent_id: str, *, reason_code: str = "PHYSICAL_EXECUTION_REJECTED", detail: str = ""
    ) -> IntentSnapshot:
        return self.transition(
            intent_id, IntentState.REJECTED, reason_code=reason_code, detail=detail
        )

    def start(self, intent_id: str, *, detail: str = "") -> IntentSnapshot:
        return self.transition(
            intent_id,
            IntentState.STARTED,
            reason_code="PHYSICAL_EXECUTION_STARTED",
            detail=detail,
        )

    def complete(self, intent_id: str, *, detail: str = "") -> IntentSnapshot:
        return self.transition(
            intent_id,
            IntentState.COMPLETED,
            reason_code="PHYSICAL_EXECUTION_COMPLETED",
            detail=detail,
        )

    def fail(
        self, intent_id: str, *, reason_code: str = "PHYSICAL_EXECUTION_FAILED", detail: str = ""
    ) -> IntentSnapshot:
        return self.transition(
            intent_id, IntentState.FAILED, reason_code=reason_code, detail=detail
        )

    def cancel(
        self, intent_id: str, *, reason_code: str = "PHYSICAL_EXECUTION_CANCELLED", detail: str = ""
    ) -> IntentSnapshot:
        return self.transition(
            intent_id, IntentState.CANCELLED, reason_code=reason_code, detail=detail
        )

    def interrupt(
        self,
        intent_id: str,
        *,
        reason_code: str = "PHYSICAL_EXECUTION_INTERRUPTED",
        detail: str = "",
    ) -> IntentSnapshot:
        return self.transition(
            intent_id, IntentState.INTERRUPTED, reason_code=reason_code, detail=detail
        )

    def expire(
        self, intent_id: str, *, reason_code: str = "INTENT_EXPIRED", detail: str = ""
    ) -> IntentSnapshot:
        return self.transition(
            intent_id, IntentState.EXPIRED, reason_code=reason_code, detail=detail
        )

    def _read_now(self) -> int:
        value = self._clock()
        if not isinstance(value, int) or isinstance(value, bool):
            raise ProtocolError("now_ms must return an integer millisecond timestamp.")
        if self._last_observed_ms is not None and value < self._last_observed_ms:
            raise ClockRegression(
                f"now_ms moved backwards from {self._last_observed_ms} to {value}."
            )
        self._last_observed_ms = value
        return value

    def _refresh(self, now: int) -> None:
        if self._state is not SessionState.ACTIVE:
            return
        if now >= self.expires_at_ms:
            self._state = SessionState.EXPIRED
            self._state_reason_code = "SESSION_TTL_EXPIRED"
            self._expire_active(
                now,
                "SESSION_TTL_EXPIRED",
                "Session TTL elapsed before physical execution reached a terminal state.",
            )
            return
        if now - self.last_heartbeat_at_ms >= self.heartbeat_timeout_ms:
            self._state = SessionState.DISCONNECTED
            self._state_reason_code = "HEARTBEAT_TIMEOUT"
            self._interrupt_active(
                now,
                "HEARTBEAT_TIMEOUT",
                "Heartbeat timeout interrupted physical execution.",
            )

    def _interrupt_active(self, now: int, reason_code: str, detail: str) -> None:
        if self._active_intent_id is None:
            return
        entry = self._intents[self._active_intent_id]
        self._apply_transition(entry, IntentState.INTERRUPTED, now, reason_code, detail)

    def _expire_active(self, now: int, reason_code: str, detail: str) -> None:
        if self._active_intent_id is None:
            return
        entry = self._intents[self._active_intent_id]
        self._apply_transition(entry, IntentState.EXPIRED, now, reason_code, detail)

    def _apply_transition(
        self,
        entry: _IntentEntry,
        new_state: IntentState,
        now: int,
        reason_code: str,
        detail: str,
    ) -> None:
        entry.state = new_state
        entry.updated_at_ms = now
        entry.events.append(
            IntentEvent(
                state=new_state,
                at_ms=now,
                reason_code=reason_code,
                detail=detail,
            )
        )
        if new_state in TERMINAL_INTENT_STATES and self._active_intent_id == entry.intent_id:
            self._active_intent_id = None

    def _snapshot_without_clock(self) -> SessionSnapshot:
        return SessionSnapshot(
            session_id=self.session_id,
            body_id=self.body_id,
            source_identity=self.source_identity,
            capabilities=self.capabilities,
            state=self._state,
            opened_at_ms=self.opened_at_ms,
            expires_at_ms=self.expires_at_ms,
            last_heartbeat_at_ms=self.last_heartbeat_at_ms,
            heartbeat_timeout_ms=self.heartbeat_timeout_ms,
            active_intent_id=self._active_intent_id,
            last_sequence=self._last_sequence,
            reason_code=self._state_reason_code,
        )

    @staticmethod
    def _rejected_request(reason_code: str, detail: str) -> RequestResult:
        return RequestResult(
            disposition=RequestDisposition.REJECTED,
            reason_code=reason_code,
            detail=detail,
        )


__all__ = [
    "Capability",
    "ClockRegression",
    "DECISION_SCOPE",
    "EmbodimentSession",
    "IntentEvent",
    "IntentSnapshot",
    "IntentState",
    "InvalidTransition",
    "ProtocolError",
    "MAX_CANONICAL_PAYLOAD_BYTES",
    "MAX_IDENTIFIER_CHARS",
    "RequestDisposition",
    "RequestResult",
    "SessionSnapshot",
    "SessionState",
    "TERMINAL_INTENT_STATES",
    "UnknownIntent",
]
