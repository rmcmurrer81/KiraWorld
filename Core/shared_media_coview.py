"""Ephemeral adult co-view decisions for one exact resident media session.

This module does not classify people or media.  It records only a short-lived,
explicit decision made by a caller-confirmed adult participant.  Every decision
is bound to one resident activation and one opaque media ID.  It is therefore
not a maturity override, a reusable unlock, or evidence that anybody watched
the item.

All state is process memory only.  There is intentionally no persistence or
serialization API, and public status snapshots omit capability tokens and
session nonces.
"""

from __future__ import annotations

import hmac
import math
import re
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable


DEFAULT_COVIEW_TTL_SECONDS = 90.0
MAX_COVIEW_TTL_SECONDS = 300.0
DEFAULT_MAX_ACTIVE_DECISIONS = 16
MAX_ACTIVE_DECISIONS = 128
ROBERT_OWNER_PARTICIPANT_ID = "robert_owner"
DEFAULT_CONFIRMED_ADULT_PARTICIPANT_IDS = frozenset(
    {ROBERT_OWNER_PARTICIPANT_ID}
)

_CANONICAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_OPAQUE_MEDIA_ID = re.compile(r"^[a-f0-9]{64}$")


class SharedMediaCoviewError(RuntimeError):
    """Base error for malformed or unauthorized co-view decisions."""


class SharedMediaCoviewDecisionRequired(SharedMediaCoviewError):
    """An explicit choice by a confirmed adult participant is absent."""


class SharedMediaCoviewNotFound(SharedMediaCoviewError):
    """The decision is unknown, expired, revoked, or incorrectly bound."""


class SharedMediaCoviewCapacityError(SharedMediaCoviewError):
    """The bounded in-memory decision store is full."""


def _nonserializable(*_args: Any, **_kwargs: Any) -> None:
    raise TypeError("shared media co-view decisions must not be serialized")


def _canonical_id(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not _CANONICAL_ID.fullmatch(value):
        raise SharedMediaCoviewError(
            f"{field_name} must be a canonical identifier"
        )
    return value


def _bounded_text(
    value: object,
    field_name: str,
    *,
    minimum: int = 1,
    maximum: int = 512,
) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise SharedMediaCoviewError(f"{field_name} is malformed")
    if not minimum <= len(value) <= maximum or any(
        character.isspace() for character in value
    ):
        raise SharedMediaCoviewError(f"{field_name} is malformed")
    return value


def _media_id(value: object) -> str:
    if not isinstance(value, str) or not _OPAQUE_MEDIA_ID.fullmatch(value):
        raise SharedMediaCoviewError(
            "media_id must be the exact opaque library media identifier"
        )
    return value


@dataclass(frozen=True, slots=True)
class SharedMediaCoviewBinding:
    """Exact resident activation and opaque media-item boundary."""

    person_id: str
    activation_revision: str
    session_nonce: str
    media_id: str

    __getstate__ = _nonserializable
    __reduce_ex__ = _nonserializable

    def __repr__(self) -> str:
        return (
            "SharedMediaCoviewBinding(person_id=<bound>, "
            "activation_revision=<bound>, session_nonce=<redacted>, "
            "media_id=<bound>)"
        )


@dataclass(frozen=True, slots=True)
class SharedMediaCoviewReceipt:
    """Capability returned only to the creating in-process caller."""

    token: str
    expires_at_monotonic: float

    __getstate__ = _nonserializable
    __reduce_ex__ = _nonserializable

    def __repr__(self) -> str:
        return (
            "SharedMediaCoviewReceipt(token=<redacted>, "
            f"expires_at_monotonic={self.expires_at_monotonic!r})"
        )


@dataclass(frozen=True, slots=True)
class SharedMediaCoviewStatus:
    """Non-secret status; neither the token nor session nonce is included."""

    active: bool
    person_id: str
    activation_revision: str
    media_id: str
    adult_participant_id: str
    expires_at_monotonic: float
    expires_in_seconds: float
    refresh_count: int

    __getstate__ = _nonserializable
    __reduce_ex__ = _nonserializable


@dataclass(frozen=True, slots=True)
class SharedMediaCoviewSnapshot:
    """Redacted diagnostic view of active in-memory decisions."""

    active_count: int
    decisions: tuple[SharedMediaCoviewStatus, ...]

    __getstate__ = _nonserializable
    __reduce_ex__ = _nonserializable


class _DecisionState:
    __slots__ = (
        "token",
        "binding",
        "adult_participant_id",
        "created_at",
        "expires_at",
        "idle_ttl_seconds",
        "refresh_count",
    )

    __getstate__ = _nonserializable
    __reduce_ex__ = _nonserializable

    def __init__(
        self,
        *,
        token: str,
        binding: SharedMediaCoviewBinding,
        adult_participant_id: str,
        created_at: float,
        expires_at: float,
        idle_ttl_seconds: float,
    ) -> None:
        self.token = token
        self.binding = binding
        self.adult_participant_id = adult_participant_id
        self.created_at = created_at
        self.expires_at = expires_at
        self.idle_ttl_seconds = idle_ttl_seconds
        self.refresh_count = 0


class SharedMediaCoviewManager:
    """Thread-safe, bounded, non-persistent co-view decision manager."""

    __getstate__ = _nonserializable
    __reduce_ex__ = _nonserializable

    def __init__(
        self,
        *,
        confirmed_adult_participant_ids: Iterable[str] = (),
        clock: Callable[[], float] = time.monotonic,
        default_ttl_seconds: float = DEFAULT_COVIEW_TTL_SECONDS,
        max_active_decisions: int = DEFAULT_MAX_ACTIVE_DECISIONS,
    ) -> None:
        if not callable(clock):
            raise SharedMediaCoviewError("clock must be callable")
        self._clock = clock
        self._last_clock_value: float | None = None
        self._default_ttl_seconds = self._validated_ttl(default_ttl_seconds)
        if (
            isinstance(max_active_decisions, bool)
            or not isinstance(max_active_decisions, int)
            or not 1 <= max_active_decisions <= MAX_ACTIVE_DECISIONS
        ):
            raise SharedMediaCoviewError(
                f"max_active_decisions must be within [1, {MAX_ACTIVE_DECISIONS}]"
            )
        confirmed = set(DEFAULT_CONFIRMED_ADULT_PARTICIPANT_IDS)
        for participant_id in confirmed_adult_participant_ids:
            confirmed.add(_canonical_id(participant_id, "adult_participant_id"))
        self._confirmed_adult_participant_ids = frozenset(confirmed)
        self._max_active_decisions = max_active_decisions
        self._decisions: dict[str, _DecisionState] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _validated_binding(
        binding: SharedMediaCoviewBinding,
    ) -> SharedMediaCoviewBinding:
        if not isinstance(binding, SharedMediaCoviewBinding):
            raise SharedMediaCoviewError(
                "a SharedMediaCoviewBinding is required"
            )
        return SharedMediaCoviewBinding(
            person_id=_canonical_id(binding.person_id, "person_id"),
            activation_revision=_bounded_text(
                binding.activation_revision,
                "activation_revision",
                maximum=256,
            ),
            session_nonce=_bounded_text(
                binding.session_nonce,
                "session_nonce",
                minimum=16,
                maximum=512,
            ),
            media_id=_media_id(binding.media_id),
        )

    @staticmethod
    def _binding_matches(
        left: SharedMediaCoviewBinding,
        right: SharedMediaCoviewBinding,
    ) -> bool:
        return all(
            hmac.compare_digest(left_value, right_value)
            for left_value, right_value in (
                (left.person_id, right.person_id),
                (left.activation_revision, right.activation_revision),
                (left.session_nonce, right.session_nonce),
                (left.media_id, right.media_id),
            )
        )

    @staticmethod
    def _token(token: object) -> str:
        if (
            not isinstance(token, str)
            or not 32 <= len(token) <= 256
            or any(character.isspace() for character in token)
        ):
            raise SharedMediaCoviewNotFound(
                "co-view decision is unknown, expired, revoked, or incorrectly bound"
            )
        return token

    @staticmethod
    def _validated_ttl(ttl_seconds: object) -> float:
        if (
            isinstance(ttl_seconds, bool)
            or not isinstance(ttl_seconds, (int, float))
            or not math.isfinite(float(ttl_seconds))
            or not 0.0 < float(ttl_seconds) <= MAX_COVIEW_TTL_SECONDS
        ):
            raise SharedMediaCoviewError(
                f"ttl_seconds must be within (0, {MAX_COVIEW_TTL_SECONDS}]"
            )
        return float(ttl_seconds)

    def _now_locked(self) -> float:
        raw = self._clock()
        if (
            isinstance(raw, bool)
            or not isinstance(raw, (int, float))
            or not math.isfinite(float(raw))
        ):
            raise SharedMediaCoviewError("clock must return a finite number")
        now = float(raw)
        if self._last_clock_value is not None and now < self._last_clock_value:
            raise SharedMediaCoviewError("co-view clock must be monotonic")
        self._last_clock_value = now
        return now

    def _purge_expired_locked(self, now: float) -> int:
        expired = [
            token
            for token, decision in self._decisions.items()
            if now >= decision.expires_at
        ]
        for token in expired:
            del self._decisions[token]
        return len(expired)

    def _adult_participant(self, adult_participant_id: object) -> str:
        participant = _canonical_id(
            adult_participant_id,
            "adult_participant_id",
        )
        if participant not in self._confirmed_adult_participant_ids:
            raise SharedMediaCoviewDecisionRequired(
                "a current confirmed adult participant must make the co-view decision"
            )
        return participant

    @staticmethod
    def _status(decision: _DecisionState, now: float) -> SharedMediaCoviewStatus:
        return SharedMediaCoviewStatus(
            active=True,
            person_id=decision.binding.person_id,
            activation_revision=decision.binding.activation_revision,
            media_id=decision.binding.media_id,
            adult_participant_id=decision.adult_participant_id,
            expires_at_monotonic=decision.expires_at,
            expires_in_seconds=max(0.0, decision.expires_at - now),
            refresh_count=decision.refresh_count,
        )

    def _find_locked(
        self,
        token: str,
        binding: SharedMediaCoviewBinding,
        adult_participant_id: str,
        now: float,
    ) -> _DecisionState:
        self._purge_expired_locked(now)
        decision = self._decisions.get(token)
        if (
            decision is None
            or not self._binding_matches(decision.binding, binding)
            or not hmac.compare_digest(
                decision.adult_participant_id,
                adult_participant_id,
            )
        ):
            raise SharedMediaCoviewNotFound(
                "co-view decision is unknown, expired, revoked, or incorrectly bound"
            )
        return decision

    def create(
        self,
        binding: SharedMediaCoviewBinding,
        *,
        adult_participant_id: str,
        adult_decision: bool,
        ttl_seconds: float | None = None,
    ) -> SharedMediaCoviewReceipt:
        """Create one decision only after an explicit confirmed-adult choice."""

        exact_binding = self._validated_binding(binding)
        participant = self._adult_participant(adult_participant_id)
        if adult_decision is not True:
            raise SharedMediaCoviewDecisionRequired(
                "the adult participant must explicitly choose to co-view this item"
            )
        ttl = (
            self._default_ttl_seconds
            if ttl_seconds is None
            else self._validated_ttl(ttl_seconds)
        )
        with self._lock:
            now = self._now_locked()
            self._purge_expired_locked(now)
            if len(self._decisions) >= self._max_active_decisions:
                raise SharedMediaCoviewCapacityError(
                    "ephemeral co-view decision capacity is reached"
                )
            for _ in range(16):
                token = secrets.token_urlsafe(32)
                if token not in self._decisions:
                    break
            else:  # pragma: no cover - cryptographically implausible
                raise SharedMediaCoviewError(
                    "could not allocate an opaque co-view capability"
                )
            expires_at = now + ttl
            self._decisions[token] = _DecisionState(
                token=token,
                binding=exact_binding,
                adult_participant_id=participant,
                created_at=now,
                expires_at=expires_at,
                idle_ttl_seconds=ttl,
            )
            return SharedMediaCoviewReceipt(
                token=token,
                expires_at_monotonic=expires_at,
            )

    def validate(
        self,
        token: str,
        binding: SharedMediaCoviewBinding,
        *,
        adult_participant_id: str,
    ) -> SharedMediaCoviewStatus:
        """Validate exact activation, media item, participant, and timeout."""

        exact_token = self._token(token)
        exact_binding = self._validated_binding(binding)
        participant = self._adult_participant(adult_participant_id)
        with self._lock:
            now = self._now_locked()
            return self._status(
                self._find_locked(
                    exact_token,
                    exact_binding,
                    participant,
                    now,
                ),
                now,
            )

    def refresh(
        self,
        token: str,
        binding: SharedMediaCoviewBinding,
        *,
        adult_participant_id: str,
    ) -> SharedMediaCoviewStatus:
        """Slide the idle timeout while the same adult remains participating."""

        exact_token = self._token(token)
        exact_binding = self._validated_binding(binding)
        participant = self._adult_participant(adult_participant_id)
        with self._lock:
            now = self._now_locked()
            decision = self._find_locked(
                exact_token,
                exact_binding,
                participant,
                now,
            )
            decision.expires_at = now + decision.idle_ttl_seconds
            decision.refresh_count += 1
            return self._status(decision, now)

    def revoke(
        self,
        token: str,
        binding: SharedMediaCoviewBinding,
        *,
        adult_participant_id: str,
    ) -> None:
        """Revoke one exactly bound decision without affecting other media."""

        exact_token = self._token(token)
        exact_binding = self._validated_binding(binding)
        participant = self._adult_participant(adult_participant_id)
        with self._lock:
            now = self._now_locked()
            self._find_locked(
                exact_token,
                exact_binding,
                participant,
                now,
            )
            del self._decisions[exact_token]

    def purge_expired(self) -> int:
        with self._lock:
            return self._purge_expired_locked(self._now_locked())

    def purge_for_participant(self, adult_participant_id: str) -> int:
        """Revoke all decisions when that adult stops participating."""

        participant = _canonical_id(
            adult_participant_id,
            "adult_participant_id",
        )
        with self._lock:
            now = self._now_locked()
            self._purge_expired_locked(now)
            tokens = [
                token
                for token, decision in self._decisions.items()
                if hmac.compare_digest(
                    decision.adult_participant_id,
                    participant,
                )
            ]
            for token in tokens:
                del self._decisions[token]
            return len(tokens)

    def purge_for_media_id(self, media_id: str) -> int:
        """Revoke every unexpired decision for one reclassified exact item."""

        exact_media_id = _media_id(media_id)
        with self._lock:
            now = self._now_locked()
            self._purge_expired_locked(now)
            tokens = [
                token
                for token, decision in self._decisions.items()
                if hmac.compare_digest(decision.binding.media_id, exact_media_id)
            ]
            for token in tokens:
                del self._decisions[token]
            return len(tokens)

    def purge_invalid_context(
        self,
        *,
        active_binding: SharedMediaCoviewBinding | None,
        participating_adult_ids: Iterable[str],
    ) -> int:
        """Purge on stop, activation switch, media change, or participant exit.

        The caller supplies its complete current context.  Only a decision
        matching the one active binding and a still-present confirmed adult is
        retained.  ``active_binding=None`` represents deactivation or media
        stop and revokes every decision.
        """

        exact_binding = (
            None
            if active_binding is None
            else self._validated_binding(active_binding)
        )
        present: set[str] = set()
        for participant_id in participating_adult_ids:
            candidate = _canonical_id(
                participant_id,
                "participating_adult_id",
            )
            if candidate in self._confirmed_adult_participant_ids:
                present.add(candidate)
        with self._lock:
            now = self._now_locked()
            self._purge_expired_locked(now)
            tokens = [
                token
                for token, decision in self._decisions.items()
                if exact_binding is None
                or not self._binding_matches(decision.binding, exact_binding)
                or decision.adult_participant_id not in present
            ]
            for token in tokens:
                del self._decisions[token]
            return len(tokens)

    def purge_all(self) -> int:
        with self._lock:
            count = len(self._decisions)
            self._decisions.clear()
            return count

    def snapshot(self) -> SharedMediaCoviewSnapshot:
        """Return redacted, non-serializable status with no capabilities."""

        with self._lock:
            now = self._now_locked()
            self._purge_expired_locked(now)
            statuses = tuple(
                self._status(decision, now)
                for decision in sorted(
                    self._decisions.values(),
                    key=lambda item: (
                        item.created_at,
                        item.binding.person_id,
                        item.binding.media_id,
                    ),
                )
            )
            return SharedMediaCoviewSnapshot(
                active_count=len(statuses),
                decisions=statuses,
            )

    @property
    def active_count(self) -> int:
        return self.snapshot().active_count
