"""Bounded initiative and turn-taking opportunities for one active person.

This module is a pure, supervised daytime-session primitive.  It accepts
structured evidence and returns a *decision opportunity*, never dialogue or an
executed action.  It opens no device, calls no model, writes no file, promotes
no memory, and changes no relationship state.

Every stateful operation requires the exact person/activation lease.  A switch
or deactivation purges the bounded in-memory decision and floor state.
"""

from __future__ import annotations

import math
import re
import secrets
import threading
from dataclasses import dataclass, replace
from typing import Any, Mapping


OUTCOMES = frozenset(
    {
        "private_decision_pending",
        "continue_activity",
        "consider_speaking",
        "consider_action",
        "ignore",
        "defer",
        "leave",
    }
)
INPUT_PROVENANCE = frozenset(
    {
        "robert_live_input",
        "supervised_owner_input",
        "private_person_decision",
        "environment_derived",
        "other_person_tts_playback",
        "own_tts_playback",
    }
)
BUSY_PROVENANCE = frozenset(
    {
        "camera_derived",
        "owner_status",
        "activity_context",
        "unknown_derived",
    }
)
TURN_EVENT_KINDS = frozenset(
    {
        "robert_interrupting_person",
        "robert_interruption_ended",
        "person_seeking_floor",
        "person_floor_granted",
        "person_floor_released",
    }
)
_CANONICAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_LEASE_FIELDS = {"person_id", "activation_revision", "session_nonce"}


class InitiativeLeaseError(PermissionError):
    """Raised when a caller lacks the exact active initiative lease."""


class InitiativeSessionBoundaryError(RuntimeError):
    """Raised when work is attempted outside a supervised daytime session."""


def _canonical_id(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _CANONICAL_ID.fullmatch(value):
        raise ValueError(f"{field_name} must be a canonical identifier")
    return value


def _unit(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a finite number from 0 to 1")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{field_name} must be from 0 to 1")
    return result


def _finite_range(value: Any, field_name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f"{field_name} must be from {minimum} to {maximum}")
    return result


@dataclass(frozen=True, slots=True)
class InitiativeLease:
    person_id: str
    activation_revision: str | int
    session_nonce: str

    def as_dict(self) -> dict[str, str | int]:
        return {
            "person_id": self.person_id,
            "activation_revision": self.activation_revision,
            "session_nonce": self.session_nonce,
        }


@dataclass(frozen=True, slots=True)
class PacingProfile:
    """Owner-reviewed, per-person pacing values with no global cooldown."""

    profile_id: str
    initiative_threshold: float
    initiative_bias: float
    speech_preference: float
    action_preference: float
    boredom_weight: float
    urgency_weight: float
    unfinished_thread_weight: float
    busy_deference_weight: float
    activity_continuation_weight: float
    minimum_bid_interval_seconds: float
    deliberation_margin: float
    urgent_pacing_override: float
    leave_valence_threshold: float
    leave_arousal_threshold: float

    def __post_init__(self) -> None:
        _canonical_id(self.profile_id, "profile_id")
        for field_name in (
            "initiative_threshold",
            "initiative_bias",
            "speech_preference",
            "action_preference",
            "boredom_weight",
            "urgency_weight",
            "unfinished_thread_weight",
            "busy_deference_weight",
            "activity_continuation_weight",
            "deliberation_margin",
            "urgent_pacing_override",
            "leave_arousal_threshold",
        ):
            _unit(getattr(self, field_name), field_name)
        _finite_range(
            self.minimum_bid_interval_seconds,
            "minimum_bid_interval_seconds",
            0.0,
            3600.0,
        )
        _finite_range(self.leave_valence_threshold, "leave_valence_threshold", -1.0, 0.0)


@dataclass(frozen=True, slots=True)
class SensoryCueRef:
    cue_id: str
    provenance: str
    source_person_id: str = ""

    def __post_init__(self) -> None:
        _canonical_id(self.cue_id, "cue_id")
        if self.provenance not in INPUT_PROVENANCE:
            raise ValueError("unsupported sensory cue provenance")
        if self.source_person_id:
            _canonical_id(self.source_person_id, "source_person_id")


@dataclass(frozen=True, slots=True)
class ActivityContext:
    activity_id: str
    engagement: float
    interruptible: bool

    def __post_init__(self) -> None:
        _canonical_id(self.activity_id, "activity_id")
        _unit(self.engagement, "engagement")
        if not isinstance(self.interruptible, bool):
            raise TypeError("interruptible must be boolean")


@dataclass(frozen=True, slots=True)
class UnfinishedThread:
    thread_id: str
    salience: float
    awaits_person_decision: bool = True

    def __post_init__(self) -> None:
        _canonical_id(self.thread_id, "thread_id")
        _unit(self.salience, "salience")
        if not isinstance(self.awaits_person_decision, bool):
            raise TypeError("awaits_person_decision must be boolean")


@dataclass(frozen=True, slots=True)
class EmotionSignal:
    emotion_id: str
    valence: float
    arousal: float

    def __post_init__(self) -> None:
        _canonical_id(self.emotion_id, "emotion_id")
        _finite_range(self.valence, "valence", -1.0, 1.0)
        _unit(self.arousal, "arousal")


@dataclass(frozen=True, slots=True)
class RobertBusyEvidence:
    observed: bool = False
    confidence: float = 0.0
    provenance: str = "unknown_derived"
    cue_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.observed, bool):
            raise TypeError("observed must be boolean")
        _unit(self.confidence, "confidence")
        if self.provenance not in BUSY_PROVENANCE:
            raise ValueError("unsupported Robert-busy evidence provenance")
        if not isinstance(self.cue_ids, tuple):
            raise TypeError("busy cue_ids must be a tuple")
        for cue_id in self.cue_ids:
            _canonical_id(cue_id, "busy cue id")


@dataclass(frozen=True, slots=True)
class RecentBid:
    bid_id: str
    actor_person_id: str
    age_seconds: float

    def __post_init__(self) -> None:
        _canonical_id(self.bid_id, "bid_id")
        _canonical_id(self.actor_person_id, "actor_person_id")
        _finite_range(self.age_seconds, "bid age_seconds", 0.0, 86_400.0)


@dataclass(frozen=True, slots=True)
class RecentTurn:
    turn_id: str
    actor_person_id: str
    age_seconds: float
    provenance: str

    def __post_init__(self) -> None:
        _canonical_id(self.turn_id, "turn_id")
        _canonical_id(self.actor_person_id, "actor_person_id")
        _finite_range(self.age_seconds, "turn age_seconds", 0.0, 86_400.0)
        if self.provenance not in INPUT_PROVENANCE:
            raise ValueError("unsupported recent-turn provenance")


@dataclass(frozen=True, slots=True)
class OpportunityInputs:
    sensory_cues: tuple[SensoryCueRef, ...]
    current_activity: ActivityContext
    unfinished_thread: UnfinishedThread | None
    emotion: EmotionSignal
    boredom: float
    urgency: float
    robert_busy: RobertBusyEvidence
    recent_bids: tuple[RecentBid, ...] = ()
    recent_turns: tuple[RecentTurn, ...] = ()

    def __post_init__(self) -> None:
        _unit(self.boredom, "boredom")
        _unit(self.urgency, "urgency")
        if not isinstance(self.sensory_cues, tuple):
            raise TypeError("sensory_cues must be a tuple")
        if not isinstance(self.recent_bids, tuple) or not isinstance(self.recent_turns, tuple):
            raise TypeError("recent bids and turns must be tuples")
        if not all(isinstance(cue, SensoryCueRef) for cue in self.sensory_cues):
            raise TypeError("every sensory cue must be a SensoryCueRef")
        if not isinstance(self.current_activity, ActivityContext):
            raise TypeError("current_activity must be an ActivityContext")
        if self.unfinished_thread is not None and not isinstance(
            self.unfinished_thread,
            UnfinishedThread,
        ):
            raise TypeError("unfinished_thread must be an UnfinishedThread or None")
        if not isinstance(self.emotion, EmotionSignal):
            raise TypeError("emotion must be an EmotionSignal")
        if not isinstance(self.robert_busy, RobertBusyEvidence):
            raise TypeError("robert_busy must be RobertBusyEvidence")
        if not all(isinstance(bid, RecentBid) for bid in self.recent_bids):
            raise TypeError("every recent bid must be a RecentBid")
        if not all(isinstance(turn, RecentTurn) for turn in self.recent_turns):
            raise TypeError("every recent turn must be a RecentTurn")


@dataclass(frozen=True, slots=True)
class InterruptionEvent:
    event_id: str
    kind: str
    provenance: str
    cue_id: str = ""

    def __post_init__(self) -> None:
        _canonical_id(self.event_id, "event_id")
        if self.kind not in TURN_EVENT_KINDS:
            raise ValueError("unsupported interruption event kind")
        if self.provenance not in INPUT_PROVENANCE:
            raise ValueError("unsupported interruption event provenance")
        if self.cue_id:
            _canonical_id(self.cue_id, "cue_id")


@dataclass(frozen=True, slots=True)
class TurnTakingState:
    robert_interrupting_person: bool = False
    person_seeking_floor: bool = False
    person_has_floor: bool = False
    last_event_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "robert_interrupting_person": self.robert_interrupting_person,
            "person_seeking_floor": self.person_seeking_floor,
            "person_has_floor": self.person_has_floor,
            "last_event_id": self.last_event_id or None,
        }


@dataclass(frozen=True, slots=True)
class DecisionOpportunity:
    decision_id: str
    person_id: str
    activation_revision: str | int
    pacing_profile_id: str
    outcome: str
    initiative_score: float
    speaking_pull: float
    action_pull: float
    reason_codes: tuple[str, ...]
    considered_cue_ids: tuple[str, ...]
    excluded_own_tts_cue_ids: tuple[str, ...]
    separate_input_turn_ids: tuple[str, ...]
    turn_taking: TurnTakingState

    def __post_init__(self) -> None:
        if self.outcome not in OUTCOMES:
            raise ValueError("unsupported initiative outcome")

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "person_id": self.person_id,
            "activation_revision": self.activation_revision,
            "pacing_profile_id": self.pacing_profile_id,
            "outcome": self.outcome,
            "initiative_score": self.initiative_score,
            "speaking_pull": self.speaking_pull,
            "action_pull": self.action_pull,
            "reason_codes": list(self.reason_codes),
            "considered_cue_ids": list(self.considered_cue_ids),
            "excluded_own_tts_cue_ids": list(self.excluded_own_tts_cue_ids),
            "separate_input_turn_ids": list(self.separate_input_turn_ids),
            "turn_taking": self.turn_taking.as_dict(),
            "opportunity_only": True,
            "words_generated": False,
            "action_executed": False,
            "memory_persisted": False,
            "relationship_changed": False,
            "robert_busy_is_command": False,
            "robert_busy_proves_motive": False,
            "camera_evidence_is_command": False,
            "camera_evidence_proves_attention_or_motive": False,
        }


class SharedPersonInitiativeSession:
    """One bounded in-memory session, switched and read by exact lease."""

    def __init__(self, *, max_decisions: int = 64) -> None:
        if isinstance(max_decisions, bool) or not isinstance(max_decisions, int):
            raise TypeError("max_decisions must be an integer")
        if not 1 <= max_decisions <= 256:
            raise ValueError("max_decisions must be from 1 to 256")
        self.max_decisions = max_decisions
        self._lock = threading.RLock()
        self._lease: InitiativeLease | None = None
        self._profile: PacingProfile | None = None
        self._turn_state = TurnTakingState()
        self._decisions: list[DecisionOpportunity] = []
        self._turn_event_count = 0
        self._next_decision_number = 1

    @property
    def current_lease(self) -> InitiativeLease | None:
        with self._lock:
            return replace(self._lease) if self._lease else None

    def activate(
        self,
        person_id: str,
        activation_revision: str | int,
        *,
        pacing_profile: PacingProfile,
        supervised: bool,
        daytime: bool,
    ) -> InitiativeLease:
        """Purge prior state and open one explicitly supervised daytime lease."""

        person_id = _canonical_id(person_id, "person_id")
        self._validate_revision(activation_revision)
        if not isinstance(pacing_profile, PacingProfile):
            raise TypeError("pacing_profile must be a PacingProfile")
        if supervised is not True or daytime is not True:
            raise InitiativeSessionBoundaryError(
                "initiative sessions require explicit supervised daytime scope"
            )
        with self._lock:
            self._purge_locked()
            self._lease = InitiativeLease(
                person_id=person_id,
                activation_revision=activation_revision,
                session_nonce=secrets.token_urlsafe(32),
            )
            self._profile = pacing_profile
            return replace(self._lease)

    def switch_person(
        self,
        lease: InitiativeLease | Mapping[str, Any],
        person_id: str,
        activation_revision: str | int,
        *,
        pacing_profile: PacingProfile,
        supervised: bool,
        daytime: bool,
    ) -> InitiativeLease:
        """Validate the prior lease, purge it, and issue a distinct lease."""

        with self._lock:
            self._require_lease_locked(lease)
            return self.activate(
                person_id,
                activation_revision,
                pacing_profile=pacing_profile,
                supervised=supervised,
                daytime=daytime,
            )

    def deactivate(self, lease: InitiativeLease | Mapping[str, Any]) -> dict[str, int]:
        with self._lock:
            self._require_lease_locked(lease)
            removed = {
                "decisions_purged": len(self._decisions),
                "turn_events_purged": self._turn_event_count,
            }
            self._purge_locked()
            return removed

    def record_interruption_event(
        self,
        lease: InitiativeLease | Mapping[str, Any],
        event: InterruptionEvent,
    ) -> dict[str, Any]:
        """Update floor state without emitting speech or executing an action."""

        if not isinstance(event, InterruptionEvent):
            raise TypeError("event must be an InterruptionEvent")
        with self._lock:
            active = self._require_lease_locked(lease)
            if event.provenance == "own_tts_playback":
                return {
                    "accepted": False,
                    "reason": "own_tts_feedback_excluded",
                    "event_id": event.event_id,
                    "turn_taking": self._turn_state.as_dict(),
                }
            if (
                event.kind in {"robert_interrupting_person", "robert_interruption_ended"}
                and event.provenance not in {"robert_live_input", "supervised_owner_input"}
            ):
                return {
                    "accepted": False,
                    "reason": "direct_or_supervised_interruption_evidence_required",
                    "event_id": event.event_id,
                    "turn_taking": self._turn_state.as_dict(),
                }
            state = self._turn_state
            if event.kind == "robert_interrupting_person":
                state = TurnTakingState(True, False, False, event.event_id)
            elif event.kind == "robert_interruption_ended":
                state = replace(state, robert_interrupting_person=False, last_event_id=event.event_id)
            elif event.kind == "person_seeking_floor":
                state = replace(state, person_seeking_floor=True, last_event_id=event.event_id)
            elif event.kind == "person_floor_granted":
                state = TurnTakingState(False, False, True, event.event_id)
            elif event.kind == "person_floor_released":
                state = TurnTakingState(False, False, False, event.event_id)
            self._turn_state = state
            self._turn_event_count += 1
            return {
                "accepted": True,
                "event_id": event.event_id,
                "person_id": active.person_id,
                "turn_taking": state.as_dict(),
                "words_generated": False,
            }

    def evaluate(
        self,
        lease: InitiativeLease | Mapping[str, Any],
        facts: OpportunityInputs,
    ) -> DecisionOpportunity:
        """Return a private opportunity category; never words or execution."""

        if not isinstance(facts, OpportunityInputs):
            raise TypeError("facts must be OpportunityInputs")
        with self._lock:
            active = self._require_lease_locked(lease)
            profile = self._profile
            if profile is None:  # Defensive: exact lease normally proves this.
                raise InitiativeSessionBoundaryError("no pacing profile is active")
            self._validate_fact_provenance(active, facts)

            own_tts_cues = tuple(
                cue.cue_id for cue in facts.sensory_cues
                if cue.provenance == "own_tts_playback"
            )
            considered_cues = tuple(
                cue.cue_id for cue in facts.sensory_cues
                if cue.provenance != "own_tts_playback"
            )
            separate_turns = tuple(
                turn.turn_id for turn in facts.recent_turns
                if turn.provenance != "own_tts_playback"
            )
            reasons: list[str] = []
            if own_tts_cues:
                reasons.append("own_tts_feedback_excluded")
            if considered_cues:
                reasons.append("separate_input_available")

            thread_strength = (
                facts.unfinished_thread.salience
                if facts.unfinished_thread and facts.unfinished_thread.awaits_person_decision
                else 0.0
            )
            busy_strength = (
                facts.robert_busy.confidence if facts.robert_busy.observed else 0.0
            )
            score_without_busy = (
                profile.initiative_bias
                + facts.urgency * profile.urgency_weight
                + facts.boredom * profile.boredom_weight
                + thread_strength * profile.unfinished_thread_weight
                + facts.emotion.arousal * 0.08
                + (0.08 if considered_cues else 0.0)
                - facts.current_activity.engagement * profile.activity_continuation_weight
            )
            score = max(
                0.0,
                min(1.0, score_without_busy - busy_strength * profile.busy_deference_weight),
            )
            if busy_strength:
                reasons.append("robert_busy_evidence_advisory_only")

            recent_own_bid_ages = [
                bid.age_seconds
                for bid in facts.recent_bids
                if bid.actor_person_id == active.person_id
            ]
            pacing_hold = (
                bool(recent_own_bid_ages)
                and min(recent_own_bid_ages) < profile.minimum_bid_interval_seconds
                and facts.urgency < profile.urgent_pacing_override
            )
            if pacing_hold:
                score *= max(
                    0.0,
                    1.0 - profile.busy_deference_weight,
                )
                reasons.append("individual_pacing_interval_active")

            speaking_pull = max(
                0.0,
                min(
                    1.0,
                    profile.speech_preference
                    + thread_strength * 0.2
                    + (0.08 if separate_turns else 0.0),
                ),
            )
            action_pull = max(
                0.0,
                min(1.0, profile.action_preference + facts.boredom * 0.2),
            )

            no_independent_signal = (
                not considered_cues
                and not separate_turns
                and thread_strength == 0.0
                and facts.boredom == 0.0
                and facts.urgency == 0.0
            )
            leave_candidate = (
                facts.emotion.valence <= profile.leave_valence_threshold
                and facts.emotion.arousal >= profile.leave_arousal_threshold
                and facts.urgency < profile.urgent_pacing_override
                and thread_strength == 0.0
            )

            if self._turn_state.robert_interrupting_person:
                outcome = "defer"
                reasons.append("robert_currently_interrupting_person")
            elif pacing_hold:
                outcome = "defer"
            elif no_independent_signal and own_tts_cues:
                outcome = "ignore"
                reasons.append("no_independent_input_after_feedback_filter")
            elif leave_candidate:
                outcome = "leave"
                reasons.append("private_leave_opportunity")
            elif abs(score - profile.initiative_threshold) <= profile.deliberation_margin:
                outcome = "private_decision_pending"
                reasons.append("within_individual_deliberation_margin")
            elif score < profile.initiative_threshold:
                busy_was_decisive = (
                    busy_strength > 0.0
                    and score_without_busy >= profile.initiative_threshold
                )
                if busy_was_decisive:
                    outcome = "defer"
                    reasons.append("busy_evidence_shifted_opportunity_to_defer")
                elif facts.current_activity.engagement > 0.0:
                    outcome = "continue_activity"
                    reasons.append("current_activity_retained")
                else:
                    outcome = "ignore"
                    reasons.append("insufficient_independent_signal")
            elif speaking_pull >= action_pull:
                outcome = "consider_speaking"
                reasons.append("speaking_opportunity_only")
                if not self._turn_state.person_has_floor:
                    reasons.append("floor_not_granted")
            else:
                outcome = "consider_action"
                reasons.append("action_opportunity_only")

            decision = DecisionOpportunity(
                decision_id=f"initiative_{self._next_decision_number:04d}",
                person_id=active.person_id,
                activation_revision=active.activation_revision,
                pacing_profile_id=profile.profile_id,
                outcome=outcome,
                initiative_score=round(score, 6),
                speaking_pull=round(speaking_pull, 6),
                action_pull=round(action_pull, 6),
                reason_codes=tuple(reasons),
                considered_cue_ids=considered_cues,
                excluded_own_tts_cue_ids=own_tts_cues,
                separate_input_turn_ids=separate_turns,
                turn_taking=self._turn_state,
            )
            self._next_decision_number += 1
            self._decisions.append(decision)
            if len(self._decisions) > self.max_decisions:
                self._decisions.pop(0)
            return decision

    def snapshot(self, lease: InitiativeLease | Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            active = self._require_lease_locked(lease)
            return {
                "lease_binding": {
                    "person_id": active.person_id,
                    "activation_revision": active.activation_revision,
                },
                "session_scope": "supervised_daytime_in_memory",
                "pacing_profile_id": self._profile.profile_id if self._profile else None,
                "decision_count": len(self._decisions),
                "last_decision": self._decisions[-1].as_dict() if self._decisions else None,
                "turn_event_count": self._turn_event_count,
                "turn_taking": self._turn_state.as_dict(),
                "storage": "memory_only",
                "words_generated": False,
                "relationship_changed": False,
            }

    def __getstate__(self) -> None:
        raise TypeError("SharedPersonInitiativeSession is memory-only and not serializable")

    @staticmethod
    def _validate_revision(revision: str | int) -> None:
        if isinstance(revision, bool) or not isinstance(revision, (str, int)):
            raise TypeError("activation_revision must be a string or integer")
        if isinstance(revision, str):
            _canonical_id(revision, "activation_revision")

    def _require_lease_locked(
        self,
        lease: InitiativeLease | Mapping[str, Any],
    ) -> InitiativeLease:
        active = self._lease
        if active is None:
            raise InitiativeLeaseError("no initiative activation is active")
        if isinstance(lease, InitiativeLease):
            supplied = lease
        elif isinstance(lease, Mapping) and set(lease) == _LEASE_FIELDS:
            supplied = InitiativeLease(
                person_id=lease["person_id"],
                activation_revision=lease["activation_revision"],
                session_nonce=lease["session_nonce"],
            )
        else:
            raise InitiativeLeaseError("an exact initiative lease is required")
        if (
            supplied.person_id != active.person_id
            or supplied.activation_revision != active.activation_revision
            or not isinstance(supplied.session_nonce, str)
            or not secrets.compare_digest(supplied.session_nonce, active.session_nonce)
        ):
            raise InitiativeLeaseError("initiative lease does not match the active person")
        return active

    @staticmethod
    def _validate_fact_provenance(
        active: InitiativeLease,
        facts: OpportunityInputs,
    ) -> None:
        cue_ids: set[str] = set()
        for cue in facts.sensory_cues:
            if cue.cue_id in cue_ids:
                raise ValueError("sensory cue ids must be unique")
            cue_ids.add(cue.cue_id)
            if cue.provenance == "own_tts_playback" and cue.source_person_id != active.person_id:
                raise ValueError("own-TTS cue must identify the active person as source")
            if cue.provenance == "other_person_tts_playback" and cue.source_person_id == active.person_id:
                raise ValueError("active person's TTS must use own_tts_playback provenance")
        unknown_busy_cues = [
            cue_id for cue_id in facts.robert_busy.cue_ids if cue_id not in cue_ids
        ]
        if unknown_busy_cues:
            raise ValueError("Robert-busy evidence must cite supplied cue ids")
        for turn in facts.recent_turns:
            if (
                turn.provenance == "own_tts_playback"
                and turn.actor_person_id != active.person_id
            ):
                raise ValueError("own-TTS turn must identify the active person")

    def _purge_locked(self) -> None:
        self._lease = None
        self._profile = None
        self._turn_state = TurnTakingState()
        self._decisions = []
        self._turn_event_count = 0
        self._next_decision_number = 1
