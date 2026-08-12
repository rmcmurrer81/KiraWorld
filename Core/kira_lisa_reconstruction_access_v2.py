"""Fail-closed access control for Kira and Lisa's college reconstruction.

This is an append-only v2 repair beside the preserved v1 reflection runtime.
It deliberately does not render, replay, persist private text, call a model, or
grant a world capability.  It provides the exact-source authorization boundary
that any later reconstruction adapter must cross.

Security properties:

* the source memory, source digest, reconstruction ID, and participant set are
  pinned in this module and re-verified by :meth:`load_pinned`;
* public construction and caller-supplied policy/classification mappings are
  not supported;
* all participant, request, view, and verbal-disclosure capabilities are
  opaque identity capabilities.  Equal-looking or copied objects are not
  accepted;
* every nonparticipant view, including a summary view, requires one current,
  exact, scope-specific decision from both Kira and Lisa;
* decisions are never accepted from model output or arbitrary mappings;
* expiry, revocation, uncertainty, material-context drift, reconstruction
  drift, clock rollback, and one-shot consumption all fail closed;
* participant private reads expose only that participant's ledger; and
* decision and ledger records are hash chained and verified before protected
  reads or authorization.

The controller is memory-only.  Its audit chain is integrity evidence for one
process lifetime, not a claim of durable storage or accepted live replay.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
from pathlib import Path
import re
import threading
import time
from typing import Any, Callable, Mapping, Sequence

from Core.adult_health_curriculum_runtime import (
    ConfirmedAdultHealthCurriculumRuntime,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MEMORY_PATH = (
    PROJECT_ROOT
    / "Data"
    / "memory_seeds"
    / "shared_kira_lisa_college_phase_001.draft.json"
)
SOURCE_MEMORY_ID = "shared_kira_lisa_college_phase_001"
SOURCE_MEMORY_SHA256 = (
    "5249718a450122739e2cee0f7f7fb08892af258a659d91e6de46fb6383eacad7"
)
RECONSTRUCTION_ID = "memworld_shared_kira_lisa_college_phase_001"
EXACT_PARTICIPANTS = ("kira", "lisa")
EXACT_PARTICIPANT_SET = frozenset(EXACT_PARTICIPANTS)
MAX_PARTICIPANT_SESSION_SECONDS = 600.0
MAX_REQUEST_SECONDS = 300.0
MAX_VERBAL_PERMIT_SECONDS = 120.0
ALLOWED_RECONSTRUCTION_SOURCE_LABELS = frozenset(
    {
        "stored_shared_anchor",
        "selected_person_private_recall",
        "inferred_reconstruction",
        "current_interpretation",
    }
)
EXPOSED_SHARED_ANCHORS = frozenset(
    {
        "Kira and Lisa had repeated private moments of closeness during their college phase.",
        "The source memory describes the private closeness as including sexual intimacy remembered as meaningful by both participants.",
        "Their stored historical interpretations differed.",
        "They ultimately valued their friendship more than continuing romantically.",
        "The stored long-term outcome is deeper trust and an unresolved emotional thread, not a permanent romantic relationship.",
    }
)

_CANONICAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReconstructionAccessError(RuntimeError):
    """Base error for the exact reconstruction boundary."""


class PinnedAuthorityError(ReconstructionAccessError):
    """Pinned source, participant, or classification authority failed."""


class CapabilityError(PermissionError, ReconstructionAccessError):
    """An opaque capability was missing, stale, cloned, or misbound."""


class DecisionError(ValueError, ReconstructionAccessError):
    """A participant decision or requested scope was invalid."""


class IntegrityError(ReconstructionAccessError):
    """An append-only chain or clock invariant failed."""


class ReconstructionScope(str, Enum):
    SUMMARY = "summary"
    EMOTIONAL_MEANING = "emotional_meaning"
    VERBAL_DETAILS_ONLY = "verbal_details_only"
    NON_INTIMATE_LEAD_IN = "non_intimate_lead_in"
    SELECTED_ZONES = "selected_zones"
    ONE_TIME_FULL_REPLAY = "one_time_full_replay"
    FULL_REPLAY = "full_replay"


class ParticipantDecision(str, Enum):
    APPROVE = "approve"
    DENY = "deny"
    UNCERTAIN = "uncertain"


class AuthenticatedParticipantOrigin(str, Enum):
    """Control-plane origins; model/adaptor output is intentionally absent."""

    PRIVATE_PERSON_UI = "private_person_ui"
    SUPERVISED_PERSON_SESSION = "supervised_person_session"


class ReconstructionWriteOrigin(str, Enum):
    """Only person-selected control-plane writes; model output is absent."""

    PRIVATE_PERSON_SELECTION = "private_person_selection"
    SUPERVISED_PERSON_CONFIRMATION = "supervised_person_confirmation"


_SCOPE_RIGHTS: dict[ReconstructionScope, frozenset[str]] = {
    ReconstructionScope.SUMMARY: frozenset({"summary"}),
    ReconstructionScope.EMOTIONAL_MEANING: frozenset(
        {"summary", "emotional_meaning"}
    ),
    ReconstructionScope.VERBAL_DETAILS_ONLY: frozenset(
        {"summary", "emotional_meaning", "verbal_selected_details"}
    ),
    ReconstructionScope.NON_INTIMATE_LEAD_IN: frozenset(
        {"summary", "emotional_meaning", "non_intimate_visual"}
    ),
    ReconstructionScope.SELECTED_ZONES: frozenset(
        {
            "summary",
            "emotional_meaning",
            "non_intimate_visual",
            "selected_locked_zones",
        }
    ),
    ReconstructionScope.ONE_TIME_FULL_REPLAY: frozenset(
        {
            "summary",
            "emotional_meaning",
            "non_intimate_visual",
            "selected_locked_zones",
            "full_visual_replay",
        }
    ),
    ReconstructionScope.FULL_REPLAY: frozenset(
        {
            "summary",
            "emotional_meaning",
            "non_intimate_visual",
            "selected_locked_zones",
            "full_visual_replay",
        }
    ),
}
_VISUAL_SCOPES = frozenset(
    {
        ReconstructionScope.NON_INTIMATE_LEAD_IN,
        ReconstructionScope.SELECTED_ZONES,
        ReconstructionScope.ONE_TIME_FULL_REPLAY,
        ReconstructionScope.FULL_REPLAY,
    }
)
_FULL_SCOPES = frozenset(
    {ReconstructionScope.ONE_TIME_FULL_REPLAY, ReconstructionScope.FULL_REPLAY}
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DecisionError("value is not canonical JSON") from exc
    return hashlib.sha256(encoded).hexdigest()


def _canonical_id(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not _CANONICAL_ID.fullmatch(value):
        raise DecisionError(f"{field_name} must be a canonical identifier")
    return value


def _exact_sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise DecisionError(f"{field_name} must be a SHA-256 digest")
    digest = value.casefold()
    if not _SHA256.fullmatch(digest):
        raise DecisionError(f"{field_name} must be a SHA-256 digest")
    return digest


def _bounded_text(value: object, field_name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise DecisionError(f"{field_name} must be non-empty exact text")
    if len(value.encode("utf-8")) > maximum:
        raise DecisionError(f"{field_name} exceeds its byte limit")
    if any(ord(character) < 32 and character not in "\t\n\r" for character in value):
        raise DecisionError(f"{field_name} contains binary control data")
    return value


def _finite_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DecisionError(f"{field_name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise DecisionError(f"{field_name} must be a finite number")
    return result


def _scope(value: object, field_name: str) -> ReconstructionScope:
    if not isinstance(value, ReconstructionScope):
        raise DecisionError(
            f"{field_name} must be an exact ReconstructionScope, not model text"
        )
    return value


def _decision(value: object) -> ParticipantDecision:
    if not isinstance(value, ParticipantDecision):
        raise DecisionError(
            "decision must be an exact ParticipantDecision from the private control plane"
        )
    return value


def _scope_is_subset(
    approved: ReconstructionScope, requested: ReconstructionScope
) -> bool:
    approved_rights = _SCOPE_RIGHTS[approved]
    requested_rights = _SCOPE_RIGHTS[requested]
    if not approved_rights <= requested_rights:
        return False
    # The two full scopes have equal rights but different lifetime semantics.
    if (
        approved is ReconstructionScope.FULL_REPLAY
        and requested is ReconstructionScope.ONE_TIME_FULL_REPLAY
    ):
        return False
    return True


def _validate_ttl(value: object, maximum: float, field_name: str) -> float:
    ttl = _finite_number(value, field_name)
    if not 0.0 < ttl <= maximum:
        raise DecisionError(f"{field_name} must be greater than zero and at most {maximum:g}")
    return ttl


def _verify_pinned_authority() -> dict[str, Any]:
    try:
        digest = _sha256_file(SOURCE_MEMORY_PATH)
        raw = json.loads(SOURCE_MEMORY_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PinnedAuthorityError("unable to read exact source memory") from exc
    if digest != SOURCE_MEMORY_SHA256:
        raise PinnedAuthorityError("exact source memory digest mismatch")
    if not isinstance(raw, dict):
        raise PinnedAuthorityError("exact source memory must be an object")
    if raw.get("memory_id") != SOURCE_MEMORY_ID:
        raise PinnedAuthorityError("exact source memory ID mismatch")
    participants = raw.get("participants")
    if (
        not isinstance(participants, list)
        or participants != list(EXACT_PARTICIPANTS)
        or len(participants) != len(set(participants))
    ):
        raise PinnedAuthorityError("exact participant set/order mismatch")
    if raw.get("status") != "draft":
        raise PinnedAuthorityError("source memory status drift")
    if raw.get("privacy_level") != "private_shared":
        raise PinnedAuthorityError("source memory privacy drift")
    if raw.get("sharing_rule") != "requires_all_participant_consent":
        raise PinnedAuthorityError("source memory sharing rule drift")
    for person_id in EXACT_PARTICIPANTS:
        try:
            runtime = ConfirmedAdultHealthCurriculumRuntime.load(person_id)
        except Exception as exc:
            raise PinnedAuthorityError(
                f"exact confirmed-adult authority failed for {person_id}"
            ) from exc
        if runtime.person_id != person_id:
            raise PinnedAuthorityError("confirmed-adult exact-person mismatch")
    return deepcopy(raw)


class _OpaqueCapability:
    """No-value capability.  Only controller registry identity is authoritative."""

    __slots__ = ()

    def __new__(cls, *args: object, **kwargs: object) -> "_OpaqueCapability":
        raise TypeError(f"{cls.__name__} cannot be constructed directly")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(<opaque>)"

    def __copy__(self) -> "_OpaqueCapability":
        return object.__new__(type(self))

    def __deepcopy__(self, memo: dict[int, Any]) -> "_OpaqueCapability":
        del memo
        return object.__new__(type(self))

    def __reduce__(self) -> object:
        raise TypeError(f"{type(self).__name__} is not serializable")


class ParticipantPrivateLeaseV2(_OpaqueCapability):
    """Opaque exact-person private session lease."""


class ReconstructionAccessRequestV2(_OpaqueCapability):
    """Opaque exact reconstruction access request."""


class NonparticipantViewLeaseV2(_OpaqueCapability):
    """Opaque one-shot nonparticipant view lease."""


class OwnPerspectiveVerbalPermitV2(_OpaqueCapability):
    """Opaque one-shot permit for selected own-perspective records only."""


@dataclass(slots=True)
class _ParticipantState:
    person_id: str
    activation_revision: str
    session_id: str
    origin: AuthenticatedParticipantOrigin
    issued_at: float
    expires_at: float
    active: bool = True


@dataclass(slots=True)
class _ResponseState:
    participant_id: str
    decision: ParticipantDecision
    approved_scope: ReconstructionScope | None
    approved_zones: tuple[str, ...]
    visual_body_exposure_allowed: bool
    event_sha256: str
    recorded_at: float
    revoked: bool = False
    uncertain_after_decision: bool = False


@dataclass(slots=True)
class _RequestState:
    request_id: str
    viewer_id: str
    viewer_session_id: str
    requested_scope: ReconstructionScope
    requested_zones: tuple[str, ...]
    reconstruction_digest: str
    material_context_digest: str
    issued_at: float
    expires_at: float
    request_event_sha256: str = ""
    responses: dict[str, _ResponseState] = field(default_factory=dict)
    leases: list[NonparticipantViewLeaseV2] = field(default_factory=list)
    invalidated_reason: str | None = None


@dataclass(slots=True)
class _ViewLeaseState:
    request_capability: ReconstructionAccessRequestV2
    request_id: str
    viewer_id: str
    viewer_session_id: str
    approved_scope: ReconstructionScope
    approved_zones: tuple[str, ...]
    visual_body_exposure_allowed: bool
    reconstruction_digest: str
    material_context_digest: str
    issued_at: float
    expires_at: float
    decision_event_hashes: tuple[str, ...]
    issuance_event_sha256: str = ""
    consumed: bool = False
    invalidated_reason: str | None = None


@dataclass(slots=True)
class _VerbalPermitState:
    participant_capability: ParticipantPrivateLeaseV2
    person_id: str
    participant_session_id: str
    intended_listener: str
    listener_session_id: str
    record_sequences: tuple[int, ...]
    record_hashes: tuple[str, ...]
    issued_at: float
    expires_at: float
    consumed: bool = False


class KiraLisaReconstructionAccessControllerV2:
    """Exact-source memory-only controller; construct only with ``load_pinned``."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PinnedAuthorityError("use load_pinned(); custom policy is forbidden")

    @classmethod
    def load_pinned(
        cls,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> "KiraLisaReconstructionAccessControllerV2":
        if cls is not KiraLisaReconstructionAccessControllerV2:
            raise PinnedAuthorityError("subclass construction is forbidden")
        if not callable(clock):
            raise PinnedAuthorityError("clock must be callable")
        source = _verify_pinned_authority()
        self = object.__new__(cls)
        self._source = source
        self._clock = clock
        self._last_clock: float | None = None
        self._clock_faulted = False
        self._lock = threading.RLock()
        self._controller_binding_digest = _canonical_sha256(
            {
                "schema": "kira.kira_lisa_reconstruction_access_controller.v2",
                "source_memory_id": SOURCE_MEMORY_ID,
                "source_memory_sha256": SOURCE_MEMORY_SHA256,
                "reconstruction_id": RECONSTRUCTION_ID,
                "exact_participants": list(EXACT_PARTICIPANTS),
            }
        )
        self._participants: dict[ParticipantPrivateLeaseV2, _ParticipantState] = {}
        self._requests: dict[ReconstructionAccessRequestV2, _RequestState] = {}
        self._request_ids: set[str] = set()
        self._view_leases: dict[NonparticipantViewLeaseV2, _ViewLeaseState] = {}
        self._verbal_permits: dict[
            OwnPerspectiveVerbalPermitV2, _VerbalPermitState
        ] = {}
        self._ledgers: dict[str, list[dict[str, Any]]] = {
            person_id: [] for person_id in EXACT_PARTICIPANTS
        }
        self._ledger_seals: dict[str, tuple[int, str | None]] = {
            person_id: (0, None) for person_id in EXACT_PARTICIPANTS
        }
        self._audit_records: list[dict[str, Any]] = []
        self._audit_seal_count = 0
        self._audit_seal_head: str | None = None
        self._append_audit(
            "controller_loaded",
            {
                "source_memory_id": SOURCE_MEMORY_ID,
                "source_memory_sha256": SOURCE_MEMORY_SHA256,
                "reconstruction_id": RECONSTRUCTION_ID,
                "exact_participants": list(EXACT_PARTICIPANTS),
                "custom_policy_accepted": False,
                "custom_classification_accepted": False,
            },
        )
        return self

    def _now(self) -> float:
        if self._clock_faulted:
            raise IntegrityError("clock previously rolled back; controller is invalidated")
        try:
            value = _finite_number(self._clock(), "clock")
        except DecisionError as exc:
            self._clock_faulted = True
            self._invalidate_all("clock_error")
            raise IntegrityError("clock failed closed") from exc
        if self._last_clock is not None and value < self._last_clock:
            self._clock_faulted = True
            self._invalidate_all("clock_rollback")
            raise IntegrityError("clock rollback invalidated all capabilities")
        self._last_clock = value
        return value

    def _invalidate_all(self, reason: str) -> None:
        for state in self._participants.values():
            state.active = False
        for state in self._requests.values():
            state.invalidated_reason = state.invalidated_reason or reason
        for state in self._view_leases.values():
            state.invalidated_reason = state.invalidated_reason or reason

    def _append_audit(
        self, event_type: str, details: Mapping[str, Any], *, now: float | None = None
    ) -> dict[str, Any]:
        event_time = self._now() if now is None else now
        previous = (
            self._audit_records[-1]["event_sha256"] if self._audit_records else None
        )
        record = {
            "schema": "kira.reconstruction_access_audit_event.v2",
            "sequence": len(self._audit_records) + 1,
            "event_type": _canonical_id(event_type, "event_type"),
            "recorded_at_clock_seconds": event_time,
            "controller_binding_digest": self._controller_binding_digest,
            "source_memory_id": SOURCE_MEMORY_ID,
            "source_memory_sha256": SOURCE_MEMORY_SHA256,
            "reconstruction_id": RECONSTRUCTION_ID,
            "details": deepcopy(dict(details)),
            "previous_event_sha256": previous,
        }
        record["event_sha256"] = _canonical_sha256(record)
        self._audit_records.append(record)
        self._audit_seal_count = len(self._audit_records)
        self._audit_seal_head = record["event_sha256"]
        return record

    def verify_audit_chain(self) -> dict[str, Any]:
        with self._lock:
            previous: str | None = None
            for index, raw in enumerate(self._audit_records, start=1):
                if not isinstance(raw, dict):
                    raise IntegrityError("audit record is not an object")
                record = deepcopy(raw)
                digest = record.pop("event_sha256", None)
                if record.get("sequence") != index:
                    raise IntegrityError("audit sequence mismatch")
                if record.get("previous_event_sha256") != previous:
                    raise IntegrityError("audit previous-hash mismatch")
                if record.get("controller_binding_digest") != self._controller_binding_digest:
                    raise IntegrityError("audit controller binding mismatch")
                if _canonical_sha256(record) != digest:
                    raise IntegrityError("audit event digest mismatch")
                previous = digest
            if len(self._audit_records) != self._audit_seal_count:
                raise IntegrityError("audit chain length seal mismatch")
            if previous != self._audit_seal_head:
                raise IntegrityError("audit chain head seal mismatch")
            return {
                "verified": True,
                "event_count": len(self._audit_records),
                "head_sha256": previous,
                "storage": "memory_only",
                "private_text_logged": False,
            }

    def audit_snapshot(self) -> dict[str, Any]:
        with self._lock:
            verification = self.verify_audit_chain()
            return {
                "schema": "kira.reconstruction_access_audit_snapshot.v2",
                "controller_binding_digest": self._controller_binding_digest,
                "events": deepcopy(self._audit_records),
                "verification": verification,
                "append_only_api": True,
                "durable_storage_claimed": False,
            }

    def _audit_event_locked(self, event_sha256: str, event_type: str) -> dict[str, Any]:
        digest = _exact_sha256(event_sha256, "event_sha256")
        for record in self._audit_records:
            if record.get("event_sha256") == digest:
                if record.get("event_type") != event_type:
                    raise IntegrityError("audit event type binding mismatch")
                return record
        raise IntegrityError("bound audit event is missing")

    def _verify_request_event_locked(self, state: _RequestState) -> None:
        record = self._audit_event_locked(
            state.request_event_sha256, "nonparticipant_request_created"
        )
        details = record.get("details")
        expected = {
            "request_id": state.request_id,
            "intended_viewer": state.viewer_id,
            "viewer_session_id": state.viewer_session_id,
            "requested_scope": state.requested_scope.value,
            "requested_zones": list(state.requested_zones),
            "reconstruction_digest": state.reconstruction_digest,
            "material_context_digest": state.material_context_digest,
            "required_participants": list(EXACT_PARTICIPANTS),
            "expires_at_clock_seconds": state.expires_at,
        }
        if details != expected:
            raise IntegrityError("request state does not match its append-only event")

    def _verify_response_event_locked(
        self, request: _RequestState, response: _ResponseState
    ) -> None:
        record = self._audit_event_locked(
            response.event_sha256, "participant_decision_recorded"
        )
        details = record.get("details")
        if not isinstance(details, Mapping):
            raise IntegrityError("participant decision event details are missing")
        exact = {
            "request_id": request.request_id,
            "participant_id": response.participant_id,
            "decision": response.decision.value,
            "approved_scope": (
                response.approved_scope.value if response.approved_scope else None
            ),
            "approved_zones": list(response.approved_zones),
            "visual_body_exposure_allowed": response.visual_body_exposure_allowed,
            "intended_viewer": request.viewer_id,
            "viewer_session_id": request.viewer_session_id,
            "requested_scope": request.requested_scope.value,
            "reconstruction_digest": request.reconstruction_digest,
            "material_context_digest": request.material_context_digest,
            "model_output_accepted_as_permission": False,
        }
        if any(details.get(key) != value for key, value in exact.items()):
            raise IntegrityError("participant response state does not match its event")

    def _verify_view_issuance_event_locked(self, state: _ViewLeaseState) -> None:
        record = self._audit_event_locked(
            state.issuance_event_sha256, "nonparticipant_view_lease_issued"
        )
        details = record.get("details")
        expected = {
            "request_id": state.request_id,
            "intended_viewer": state.viewer_id,
            "viewer_session_id": state.viewer_session_id,
            "approved_scope": state.approved_scope.value,
            "approved_zones": list(state.approved_zones),
            "visual_body_exposure_allowed": state.visual_body_exposure_allowed,
            "decision_event_hashes": list(state.decision_event_hashes),
            "expires_at_clock_seconds": state.expires_at,
            "one_shot_consumption_required": True,
        }
        if details != expected:
            raise IntegrityError("view lease state does not match its issuance event")

    def _current_reconstruction_digest_locked(self) -> str:
        for person_id in EXACT_PARTICIPANTS:
            self._verify_person_ledger_locked(person_id)
        return _canonical_sha256(
            {
                "schema": "kira.kira_lisa_reconstruction_binding.v2",
                "source_memory_id": SOURCE_MEMORY_ID,
                "source_memory_sha256": SOURCE_MEMORY_SHA256,
                "reconstruction_id": RECONSTRUCTION_ID,
                "participants": list(EXACT_PARTICIPANTS),
                "ledger_heads": {
                    person_id: (
                        self._ledgers[person_id][-1]["record_sha256"]
                        if self._ledgers[person_id]
                        else None
                    )
                    for person_id in EXACT_PARTICIPANTS
                },
            }
        )

    def current_reconstruction_binding(self) -> dict[str, Any]:
        with self._lock:
            self.verify_audit_chain()
            return {
                "reconstruction_id": RECONSTRUCTION_ID,
                "reconstruction_digest": self._current_reconstruction_digest_locked(),
                "source_memory_id": SOURCE_MEMORY_ID,
                "source_memory_sha256": SOURCE_MEMORY_SHA256,
                "exact_participants": list(EXACT_PARTICIPANTS),
                "private_text_included": False,
            }

    def activate_participant_private_session(
        self,
        *,
        participant_id: str,
        activation_revision: str,
        session_id: str,
        origin: AuthenticatedParticipantOrigin,
        ttl_seconds: float,
    ) -> ParticipantPrivateLeaseV2:
        """Control-plane entry for an already authenticated private person UI.

        No model adapter is accepted.  Integrators must call this only after
        their person/session authentication gate succeeds.
        """

        person = _canonical_id(participant_id, "participant_id").casefold()
        if person not in EXACT_PARTICIPANT_SET:
            raise CapabilityError("participant is not in the exact source participant set")
        revision = _canonical_id(activation_revision, "activation_revision")
        session = _canonical_id(session_id, "session_id")
        if not isinstance(origin, AuthenticatedParticipantOrigin):
            raise CapabilityError("participant activation requires a control-plane origin")
        ttl = _validate_ttl(
            ttl_seconds, MAX_PARTICIPANT_SESSION_SECONDS, "ttl_seconds"
        )
        with self._lock:
            self.verify_audit_chain()
            now = self._now()
            capability = object.__new__(ParticipantPrivateLeaseV2)
            self._participants[capability] = _ParticipantState(
                person_id=person,
                activation_revision=revision,
                session_id=session,
                origin=origin,
                issued_at=now,
                expires_at=now + ttl,
            )
            self._append_audit(
                "participant_session_activated",
                {
                    "participant_id": person,
                    "activation_revision": revision,
                    "session_id": session,
                    "origin": origin.value,
                    "expires_at_clock_seconds": now + ttl,
                    "raw_lease_nonce_exposed": False,
                },
                now=now,
            )
            return capability

    def _require_participant_locked(
        self,
        capability: ParticipantPrivateLeaseV2,
        *,
        expected_person_id: str | None = None,
        expected_session_id: str | None = None,
    ) -> _ParticipantState:
        if not isinstance(capability, ParticipantPrivateLeaseV2):
            raise CapabilityError("exact participant private lease required")
        state = self._participants.get(capability)
        if state is None:
            raise CapabilityError("participant lease is a clone or belongs to another controller")
        now = self._now()
        if not state.active:
            raise CapabilityError("participant lease is revoked")
        if now >= state.expires_at:
            state.active = False
            raise CapabilityError("participant lease expired")
        if expected_person_id is not None and state.person_id != expected_person_id:
            raise CapabilityError("participant lease person mismatch")
        if expected_session_id is not None and state.session_id != expected_session_id:
            raise CapabilityError("participant lease session mismatch")
        return state

    def close_participant_private_session(
        self, capability: ParticipantPrivateLeaseV2
    ) -> None:
        with self._lock:
            self.verify_audit_chain()
            state = self._require_participant_locked(capability)
            state.active = False
            now = self._now()
            self._append_audit(
                "participant_session_closed",
                {"participant_id": state.person_id, "session_id": state.session_id},
                now=now,
            )

    def append_person_reconstruction(
        self,
        capability: ParticipantPrivateLeaseV2,
        *,
        participant_id: str,
        participant_session_id: str,
        reflection_text: str,
        source_label: str,
        confidence: float,
        recall_strength_delta: float,
        write_origin: ReconstructionWriteOrigin,
    ) -> dict[str, Any]:
        person = _canonical_id(participant_id, "participant_id").casefold()
        session = _canonical_id(participant_session_id, "participant_session_id")
        if not isinstance(write_origin, ReconstructionWriteOrigin):
            raise DecisionError(
                "reconstruction write requires a person-selected control-plane origin"
            )
        with self._lock:
            self.verify_audit_chain()
            state = self._require_participant_locked(
                capability,
                expected_person_id=person,
                expected_session_id=session,
            )
            self._verify_person_ledger_locked(person)
            label = _canonical_id(source_label, "source_label").casefold()
            if label not in ALLOWED_RECONSTRUCTION_SOURCE_LABELS:
                raise DecisionError("unsupported reconstruction source label")
            text = _bounded_text(reflection_text, "reflection_text", 4000)
            if label == "stored_shared_anchor" and text not in EXPOSED_SHARED_ANCHORS:
                raise DecisionError("stored shared anchor is not an exact exposed anchor")
            bounded_confidence = _finite_number(confidence, "confidence")
            if not 0.0 <= bounded_confidence <= 1.0:
                raise DecisionError("confidence must be from zero to one")
            bounded_delta = _finite_number(
                recall_strength_delta, "recall_strength_delta"
            )
            if not -0.25 <= bounded_delta <= 0.25:
                raise DecisionError("recall strength delta is outside the bounded range")
            now = self._now()
            records = self._ledgers[person]
            record = {
                "schema": "kira.person_owned_college_reconstruction.v2",
                "sequence": len(records) + 1,
                "person_id": person,
                "participant_session_id": state.session_id,
                "source_memory_id": SOURCE_MEMORY_ID,
                "source_memory_sha256": SOURCE_MEMORY_SHA256,
                "recorded_at_clock_seconds": now,
                "source_label": label,
                "confidence": bounded_confidence,
                "confidence_is_person_scoped_not_shared_fact": True,
                "recall_strength_delta": bounded_delta,
                "recall_strength_delta_is_subjective_not_accuracy": True,
                "reflection_text": text,
                "reflection_text_sha256": hashlib.sha256(
                    text.encode("utf-8")
                ).hexdigest(),
                "previous_record_sha256": (
                    records[-1]["record_sha256"] if records else None
                ),
                "shared_canon_status": "unchanged",
                "other_person_reconstruction_changed": False,
                "consent_or_replay_permission_created": False,
            }
            record["record_sha256"] = _canonical_sha256(record)
            records.append(record)
            self._ledger_seals[person] = (len(records), record["record_sha256"])
            # Reconstruction drift invalidates all pre-existing requests/leases.
            for request in self._requests.values():
                request.invalidated_reason = (
                    request.invalidated_reason or "reconstruction_changed"
                )
            for lease in self._view_leases.values():
                lease.invalidated_reason = (
                    lease.invalidated_reason or "reconstruction_changed"
                )
            audit = self._append_audit(
                "person_reconstruction_appended",
                {
                    "participant_id": person,
                    "participant_session_id": state.session_id,
                    "record_sequence": record["sequence"],
                    "record_sha256": record["record_sha256"],
                    "reflection_text_sha256": record["reflection_text_sha256"],
                    "write_origin": write_origin.value,
                    "private_text_logged": False,
                    "outstanding_access_invalidated": True,
                },
                now=now,
            )
            return {
                "person_id": person,
                "sequence": record["sequence"],
                "record_sha256": record["record_sha256"],
                "audit_event_sha256": audit["event_sha256"],
                "shared_canon_mutated": False,
                "permission_created": False,
            }

    def _verify_person_ledger_locked(self, person_id: str) -> dict[str, Any]:
        if person_id not in EXACT_PARTICIPANT_SET:
            raise IntegrityError("unsupported ledger person")
        previous: str | None = None
        for index, raw in enumerate(self._ledgers[person_id], start=1):
            if not isinstance(raw, dict):
                raise IntegrityError("private ledger record is not an object")
            record = deepcopy(raw)
            digest = record.pop("record_sha256", None)
            if record.get("sequence") != index:
                raise IntegrityError("private ledger sequence mismatch")
            if record.get("person_id") != person_id:
                raise IntegrityError("private ledger person mismatch")
            if record.get("source_memory_id") != SOURCE_MEMORY_ID:
                raise IntegrityError("private ledger source ID mismatch")
            if record.get("source_memory_sha256") != SOURCE_MEMORY_SHA256:
                raise IntegrityError("private ledger source digest mismatch")
            if record.get("previous_record_sha256") != previous:
                raise IntegrityError("private ledger previous-hash mismatch")
            text = record.get("reflection_text")
            if not isinstance(text, str) or hashlib.sha256(
                text.encode("utf-8")
            ).hexdigest() != record.get("reflection_text_sha256"):
                raise IntegrityError("private ledger text digest mismatch")
            if _canonical_sha256(record) != digest:
                raise IntegrityError("private ledger record digest mismatch")
            previous = digest
        sealed_count, sealed_head = self._ledger_seals[person_id]
        if len(self._ledgers[person_id]) != sealed_count:
            raise IntegrityError("private ledger length seal mismatch")
        if previous != sealed_head:
            raise IntegrityError("private ledger head seal mismatch")
        return {
            "verified": True,
            "record_count": len(self._ledgers[person_id]),
            "head_sha256": previous,
        }

    def participant_private_snapshot(
        self,
        capability: ParticipantPrivateLeaseV2,
        *,
        participant_id: str,
        participant_session_id: str,
        reconstruction_id: str,
    ) -> dict[str, Any]:
        person = _canonical_id(participant_id, "participant_id").casefold()
        session = _canonical_id(participant_session_id, "participant_session_id")
        if reconstruction_id != RECONSTRUCTION_ID:
            raise CapabilityError("wrong reconstruction ID")
        with self._lock:
            self.verify_audit_chain()
            self._require_participant_locked(
                capability,
                expected_person_id=person,
                expected_session_id=session,
            )
            verification = self._verify_person_ledger_locked(person)
            return {
                "schema": "kira.person_owned_college_reconstruction_snapshot.v2",
                "person_id": person,
                "reconstruction_id": RECONSTRUCTION_ID,
                "source_memory_id": SOURCE_MEMORY_ID,
                "source_memory_sha256": SOURCE_MEMORY_SHA256,
                "records": deepcopy(self._ledgers[person]),
                "private_text_included": True,
                "other_person_ledger_included": False,
                "shared_canon_mutated": False,
                "verification": verification,
                "live_exact_person_lease_required": True,
            }

    def create_own_perspective_verbal_permit(
        self,
        capability: ParticipantPrivateLeaseV2,
        *,
        participant_id: str,
        participant_session_id: str,
        intended_listener: str,
        listener_session_id: str,
        record_sequences: Sequence[int],
        ttl_seconds: float,
    ) -> OwnPerspectiveVerbalPermitV2:
        person = _canonical_id(participant_id, "participant_id").casefold()
        person_session = _canonical_id(
            participant_session_id, "participant_session_id"
        )
        listener = _canonical_id(intended_listener, "intended_listener").casefold()
        listener_session = _canonical_id(listener_session_id, "listener_session_id")
        ttl = _validate_ttl(ttl_seconds, MAX_VERBAL_PERMIT_SECONDS, "ttl_seconds")
        if not isinstance(record_sequences, Sequence) or isinstance(
            record_sequences, (str, bytes)
        ):
            raise DecisionError("record_sequences must be a bounded sequence")
        sequences = tuple(record_sequences)
        if not sequences or len(sequences) > 32:
            raise DecisionError("record_sequences must contain from 1 to 32 entries")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in sequences):
            raise DecisionError("record_sequences must contain integers")
        if len(sequences) != len(set(sequences)):
            raise DecisionError("record_sequences must not contain duplicates")
        with self._lock:
            self.verify_audit_chain()
            self._require_participant_locked(
                capability,
                expected_person_id=person,
                expected_session_id=person_session,
            )
            self._verify_person_ledger_locked(person)
            records = self._ledgers[person]
            if any(value < 1 or value > len(records) for value in sequences):
                raise DecisionError("verbal permit selected an absent private record")
            hashes = tuple(records[value - 1]["record_sha256"] for value in sequences)
            now = self._now()
            permit = object.__new__(OwnPerspectiveVerbalPermitV2)
            self._verbal_permits[permit] = _VerbalPermitState(
                participant_capability=capability,
                person_id=person,
                participant_session_id=person_session,
                intended_listener=listener,
                listener_session_id=listener_session,
                record_sequences=sequences,
                record_hashes=hashes,
                issued_at=now,
                expires_at=now + ttl,
            )
            self._append_audit(
                "own_perspective_verbal_permit_created",
                {
                    "participant_id": person,
                    "intended_listener": listener,
                    "listener_session_id": listener_session,
                    "record_hashes": list(hashes),
                    "expires_at_clock_seconds": now + ttl,
                    "visual_replay_allowed": False,
                    "locked_zone_access_allowed": False,
                    "other_participant_perspective_allowed": False,
                },
                now=now,
            )
            return permit

    def consume_own_perspective_verbal_permit(
        self,
        permit: OwnPerspectiveVerbalPermitV2,
        *,
        participant_id: str,
        intended_listener: str,
        listener_session_id: str,
    ) -> dict[str, Any]:
        person = _canonical_id(participant_id, "participant_id").casefold()
        listener = _canonical_id(intended_listener, "intended_listener").casefold()
        listener_session = _canonical_id(listener_session_id, "listener_session_id")
        with self._lock:
            self.verify_audit_chain()
            if not isinstance(permit, OwnPerspectiveVerbalPermitV2):
                raise CapabilityError("exact own-perspective verbal permit required")
            state = self._verbal_permits.get(permit)
            if state is None:
                raise CapabilityError("verbal permit is a clone or belongs to another controller")
            self._require_participant_locked(
                state.participant_capability,
                expected_person_id=state.person_id,
                expected_session_id=state.participant_session_id,
            )
            now = self._now()
            if state.consumed:
                raise CapabilityError("verbal permit was already consumed")
            if now >= state.expires_at:
                raise CapabilityError("verbal permit expired")
            if (
                person != state.person_id
                or listener != state.intended_listener
                or listener_session != state.listener_session_id
            ):
                raise CapabilityError("verbal permit binding mismatch")
            self._verify_person_ledger_locked(person)
            records = self._ledgers[person]
            current_hashes = tuple(
                records[value - 1]["record_sha256"] for value in state.record_sequences
            )
            if current_hashes != state.record_hashes:
                raise IntegrityError("selected own-perspective records changed")
            state.consumed = True
            audit = self._append_audit(
                "own_perspective_verbal_permit_consumed",
                {
                    "participant_id": person,
                    "intended_listener": listener,
                    "listener_session_id": listener_session,
                    "record_hashes": list(current_hashes),
                    "visual_replay_allowed": False,
                    "locked_zone_access_allowed": False,
                    "other_participant_perspective_allowed": False,
                },
                now=now,
            )
            return {
                "status": "OWN_PERSPECTIVE_VERBAL_SELECTION_AUTHORIZED_ONCE",
                "participant_id": person,
                "intended_listener": listener,
                "listener_session_id": listener_session,
                "record_hashes": list(current_hashes),
                "audit_event_sha256": audit["event_sha256"],
                "visual_replay_authorized": False,
                "locked_zone_access_authorized": False,
                "full_replay_authorized": False,
                "other_participant_perspective_authorized": False,
                "private_text_in_receipt": False,
            }

    def create_nonparticipant_request(
        self,
        *,
        request_id: str,
        intended_viewer: str,
        viewer_session_id: str,
        requested_scope: ReconstructionScope,
        requested_zones: Sequence[str] = (),
        reconstruction_id: str,
        reconstruction_digest: str,
        material_context_digest: str,
        ttl_seconds: float,
    ) -> ReconstructionAccessRequestV2:
        request = _canonical_id(request_id, "request_id")
        viewer = _canonical_id(intended_viewer, "intended_viewer").casefold()
        viewer_session = _canonical_id(viewer_session_id, "viewer_session_id")
        if viewer in EXACT_PARTICIPANT_SET:
            raise DecisionError("participant access must use the private participant route")
        scope = _scope(requested_scope, "requested_scope")
        zones = self._validate_zones(scope, requested_zones, "requested_zones")
        if reconstruction_id != RECONSTRUCTION_ID:
            raise DecisionError("wrong reconstruction ID")
        digest = _exact_sha256(reconstruction_digest, "reconstruction_digest")
        context_digest = _exact_sha256(
            material_context_digest, "material_context_digest"
        )
        ttl = _validate_ttl(ttl_seconds, MAX_REQUEST_SECONDS, "ttl_seconds")
        with self._lock:
            self.verify_audit_chain()
            current_digest = self._current_reconstruction_digest_locked()
            if digest != current_digest:
                raise DecisionError("reconstruction digest is stale or untrusted")
            if request in self._request_ids:
                raise DecisionError("request_id must be unique and append-only")
            now = self._now()
            capability = object.__new__(ReconstructionAccessRequestV2)
            self._requests[capability] = _RequestState(
                request_id=request,
                viewer_id=viewer,
                viewer_session_id=viewer_session,
                requested_scope=scope,
                requested_zones=zones,
                reconstruction_digest=digest,
                material_context_digest=context_digest,
                issued_at=now,
                expires_at=now + ttl,
            )
            self._request_ids.add(request)
            audit = self._append_audit(
                "nonparticipant_request_created",
                {
                    "request_id": request,
                    "intended_viewer": viewer,
                    "viewer_session_id": viewer_session,
                    "requested_scope": scope.value,
                    "requested_zones": list(zones),
                    "reconstruction_digest": digest,
                    "material_context_digest": context_digest,
                    "required_participants": list(EXACT_PARTICIPANTS),
                    "expires_at_clock_seconds": now + ttl,
                },
                now=now,
            )
            self._requests[capability].request_event_sha256 = audit["event_sha256"]
            return capability

    @staticmethod
    def _validate_zones(
        scope: ReconstructionScope,
        values: Sequence[str],
        field_name: str,
    ) -> tuple[str, ...]:
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            raise DecisionError(f"{field_name} must be a sequence")
        zones = tuple(_canonical_id(value, field_name) for value in values)
        if len(zones) != len(set(zones)):
            raise DecisionError(f"{field_name} must not contain duplicates")
        if len(zones) > 32:
            raise DecisionError(f"{field_name} exceeds its bounded count")
        if scope is ReconstructionScope.SELECTED_ZONES:
            if not zones:
                raise DecisionError("selected_zones requires at least one exact zone")
        elif zones:
            raise DecisionError(f"{field_name} is allowed only for selected_zones")
        return zones

    def _require_request_locked(
        self,
        capability: ReconstructionAccessRequestV2,
    ) -> _RequestState:
        if not isinstance(capability, ReconstructionAccessRequestV2):
            raise CapabilityError("exact reconstruction request capability required")
        state = self._requests.get(capability)
        if state is None:
            raise CapabilityError("request is a clone or belongs to another controller")
        self._verify_request_event_locked(state)
        now = self._now()
        if state.invalidated_reason:
            raise CapabilityError(f"request invalidated: {state.invalidated_reason}")
        if now >= state.expires_at:
            state.invalidated_reason = "expired"
            raise CapabilityError("request expired")
        if state.reconstruction_digest != self._current_reconstruction_digest_locked():
            state.invalidated_reason = "reconstruction_changed"
            raise CapabilityError("request reconstruction binding is stale")
        return state

    @staticmethod
    def _require_request_arguments(
        state: _RequestState,
        *,
        request_id: str,
        intended_viewer: str,
        viewer_session_id: str,
        requested_scope: ReconstructionScope,
        reconstruction_digest: str,
        material_context_digest: str,
    ) -> None:
        if _canonical_id(request_id, "request_id") != state.request_id:
            raise CapabilityError("request ID binding mismatch")
        if _canonical_id(intended_viewer, "intended_viewer").casefold() != state.viewer_id:
            raise CapabilityError("intended viewer binding mismatch")
        if _canonical_id(viewer_session_id, "viewer_session_id") != state.viewer_session_id:
            raise CapabilityError("viewer session binding mismatch")
        if _scope(requested_scope, "requested_scope") is not state.requested_scope:
            raise CapabilityError("requested scope binding mismatch")
        if _exact_sha256(reconstruction_digest, "reconstruction_digest") != state.reconstruction_digest:
            raise CapabilityError("reconstruction digest binding mismatch")
        if _exact_sha256(material_context_digest, "material_context_digest") != state.material_context_digest:
            raise CapabilityError("material context binding mismatch")

    def record_participant_decision(
        self,
        participant_capability: ParticipantPrivateLeaseV2,
        request_capability: ReconstructionAccessRequestV2,
        *,
        participant_id: str,
        participant_session_id: str,
        request_id: str,
        intended_viewer: str,
        viewer_session_id: str,
        requested_scope: ReconstructionScope,
        reconstruction_digest: str,
        material_context_digest: str,
        decision: ParticipantDecision,
        approved_scope: ReconstructionScope | None,
        approved_zones: Sequence[str] = (),
        visual_body_exposure_allowed: bool,
    ) -> dict[str, Any]:
        person = _canonical_id(participant_id, "participant_id").casefold()
        person_session = _canonical_id(
            participant_session_id, "participant_session_id"
        )
        outcome = _decision(decision)
        if not isinstance(visual_body_exposure_allowed, bool):
            raise DecisionError("visual_body_exposure_allowed must be boolean")
        with self._lock:
            self.verify_audit_chain()
            participant = self._require_participant_locked(
                participant_capability,
                expected_person_id=person,
                expected_session_id=person_session,
            )
            request = self._require_request_locked(request_capability)
            self._require_request_arguments(
                request,
                request_id=request_id,
                intended_viewer=intended_viewer,
                viewer_session_id=viewer_session_id,
                requested_scope=requested_scope,
                reconstruction_digest=reconstruction_digest,
                material_context_digest=material_context_digest,
            )
            if person in request.responses:
                raise DecisionError("duplicate participant response is forbidden")
            if set(request.responses) - EXACT_PARTICIPANT_SET:
                raise IntegrityError("extra participant response detected")
            if outcome is ParticipantDecision.APPROVE:
                scope = _scope(approved_scope, "approved_scope")
                if not _scope_is_subset(scope, request.requested_scope):
                    raise DecisionError("approved scope exceeds the requested scope")
                zones = self._validate_zones(scope, approved_zones, "approved_zones")
                if scope is ReconstructionScope.SELECTED_ZONES:
                    if not set(zones) <= set(request.requested_zones):
                        raise DecisionError("approved zones exceed requested zones")
                if scope in _VISUAL_SCOPES:
                    if visual_body_exposure_allowed is not True:
                        raise DecisionError("visual scope requires explicit visual approval")
                elif visual_body_exposure_allowed:
                    raise DecisionError("nonvisual scope cannot grant visual exposure")
            else:
                if approved_scope is not None or tuple(approved_zones):
                    raise DecisionError("deny or uncertainty cannot carry an approved scope")
                if visual_body_exposure_allowed:
                    raise DecisionError("deny or uncertainty cannot allow visual exposure")
                scope = None
                zones = ()
            now = self._now()
            audit = self._append_audit(
                "participant_decision_recorded",
                {
                    "request_id": request.request_id,
                    "participant_id": person,
                    "participant_session_id": participant.session_id,
                    "participant_activation_revision": participant.activation_revision,
                    "decision": outcome.value,
                    "approved_scope": scope.value if scope else None,
                    "approved_zones": list(zones),
                    "visual_body_exposure_allowed": visual_body_exposure_allowed,
                    "intended_viewer": request.viewer_id,
                    "viewer_session_id": request.viewer_session_id,
                    "requested_scope": request.requested_scope.value,
                    "reconstruction_digest": request.reconstruction_digest,
                    "material_context_digest": request.material_context_digest,
                    "model_output_accepted_as_permission": False,
                },
                now=now,
            )
            request.responses[person] = _ResponseState(
                participant_id=person,
                decision=outcome,
                approved_scope=scope,
                approved_zones=zones,
                visual_body_exposure_allowed=visual_body_exposure_allowed,
                event_sha256=audit["event_sha256"],
                recorded_at=now,
            )
            return {
                "request_id": request.request_id,
                "participant_id": person,
                "decision": outcome.value,
                "approved_scope": scope.value if scope else None,
                "audit_event_sha256": audit["event_sha256"],
                "responses_recorded": sorted(request.responses),
                "required_participants": list(EXACT_PARTICIPANTS),
                "access_granted": False,
            }

    def _invalidate_request_leases_locked(
        self, request_capability: ReconstructionAccessRequestV2, reason: str
    ) -> None:
        request = self._requests[request_capability]
        for capability in request.leases:
            lease = self._view_leases.get(capability)
            if lease is not None:
                lease.invalidated_reason = lease.invalidated_reason or reason

    def revoke_or_mark_uncertain(
        self,
        participant_capability: ParticipantPrivateLeaseV2,
        request_capability: ReconstructionAccessRequestV2,
        *,
        participant_id: str,
        participant_session_id: str,
        request_id: str,
        reason: str,
        uncertain: bool = False,
    ) -> dict[str, Any]:
        person = _canonical_id(participant_id, "participant_id").casefold()
        person_session = _canonical_id(
            participant_session_id, "participant_session_id"
        )
        reason_text = _bounded_text(reason, "reason", 512)
        if not isinstance(uncertain, bool):
            raise DecisionError("uncertain must be boolean")
        with self._lock:
            self.verify_audit_chain()
            self._require_participant_locked(
                participant_capability,
                expected_person_id=person,
                expected_session_id=person_session,
            )
            request = self._requests.get(request_capability)
            if request is None:
                raise CapabilityError("request is a clone or belongs to another controller")
            if request.request_id != _canonical_id(request_id, "request_id"):
                raise CapabilityError("request ID binding mismatch")
            response = request.responses.get(person)
            if response is None:
                raise DecisionError("participant has no response to revoke or question")
            if response.revoked or response.uncertain_after_decision:
                raise DecisionError("response was already invalidated")
            if uncertain:
                response.uncertain_after_decision = True
                event_type = "participant_decision_became_uncertain"
                invalidation = "participant_uncertainty"
            else:
                response.revoked = True
                event_type = "participant_decision_revoked"
                invalidation = "participant_revocation"
            self._invalidate_request_leases_locked(request_capability, invalidation)
            now = self._now()
            audit = self._append_audit(
                event_type,
                {
                    "request_id": request.request_id,
                    "participant_id": person,
                    "reason_sha256": hashlib.sha256(
                        reason_text.encode("utf-8")
                    ).hexdigest(),
                    "reason_text_logged": False,
                    "all_issued_leases_invalidated": True,
                },
                now=now,
            )
            return {
                "request_id": request.request_id,
                "participant_id": person,
                "status": "uncertain" if uncertain else "revoked",
                "audit_event_sha256": audit["event_sha256"],
                "all_issued_leases_invalidated": True,
            }

    def issue_nonparticipant_view_lease(
        self,
        request_capability: ReconstructionAccessRequestV2,
        *,
        request_id: str,
        intended_viewer: str,
        viewer_session_id: str,
        requested_scope: ReconstructionScope,
        reconstruction_digest: str,
        material_context_digest: str,
    ) -> NonparticipantViewLeaseV2:
        with self._lock:
            self.verify_audit_chain()
            request = self._require_request_locked(request_capability)
            self._require_request_arguments(
                request,
                request_id=request_id,
                intended_viewer=intended_viewer,
                viewer_session_id=viewer_session_id,
                requested_scope=requested_scope,
                reconstruction_digest=reconstruction_digest,
                material_context_digest=material_context_digest,
            )
            if set(request.responses) != EXACT_PARTICIPANT_SET:
                raise DecisionError("one exact response from both Kira and Lisa is required")
            if len(request.responses) != len(EXACT_PARTICIPANTS):
                raise IntegrityError("duplicate or extra response count detected")
            ordered = [request.responses[person] for person in EXACT_PARTICIPANTS]
            for response in ordered:
                self._verify_response_event_locked(request, response)
            if any(response.participant_id not in EXACT_PARTICIPANT_SET for response in ordered):
                raise IntegrityError("extra participant response detected")
            if any(response.decision is not ParticipantDecision.APPROVE for response in ordered):
                raise DecisionError("every exact participant must affirmatively approve")
            if any(response.revoked for response in ordered):
                raise DecisionError("a participant revoked permission")
            if any(response.uncertain_after_decision for response in ordered):
                raise DecisionError("participant uncertainty invalidates permission")
            approved_scopes = {response.approved_scope for response in ordered}
            approved_zones = {response.approved_zones for response in ordered}
            visual_values = {
                response.visual_body_exposure_allowed for response in ordered
            }
            if len(approved_scopes) != 1 or None in approved_scopes:
                raise DecisionError("participants did not approve one exact common scope")
            if len(approved_zones) != 1:
                raise DecisionError("participants did not approve one exact common zone set")
            if len(visual_values) != 1:
                raise DecisionError("participants did not make the same visual decision")
            approved_scope = next(iter(approved_scopes))
            assert isinstance(approved_scope, ReconstructionScope)
            zones = next(iter(approved_zones))
            visual_allowed = next(iter(visual_values))
            if not _scope_is_subset(approved_scope, request.requested_scope):
                raise IntegrityError("approved scope exceeds request")
            if approved_scope not in _VISUAL_SCOPES and visual_allowed:
                raise IntegrityError("nonvisual approval was escalated to visual")
            if approved_scope in _VISUAL_SCOPES and visual_allowed is not True:
                raise IntegrityError("visual approval is incomplete")
            if request.leases:
                raise DecisionError(
                    "this exact request already issued its single view lease"
                )
            now = self._now()
            expires_at = min(request.expires_at, now + MAX_REQUEST_SECONDS)
            if not now < expires_at:
                raise CapabilityError("authorization expired before lease issuance")
            capability = object.__new__(NonparticipantViewLeaseV2)
            self._view_leases[capability] = _ViewLeaseState(
                request_capability=request_capability,
                request_id=request.request_id,
                viewer_id=request.viewer_id,
                viewer_session_id=request.viewer_session_id,
                approved_scope=approved_scope,
                approved_zones=zones,
                visual_body_exposure_allowed=visual_allowed,
                reconstruction_digest=request.reconstruction_digest,
                material_context_digest=request.material_context_digest,
                issued_at=now,
                expires_at=expires_at,
                decision_event_hashes=tuple(
                    response.event_sha256 for response in ordered
                ),
            )
            request.leases.append(capability)
            audit = self._append_audit(
                "nonparticipant_view_lease_issued",
                {
                    "request_id": request.request_id,
                    "intended_viewer": request.viewer_id,
                    "viewer_session_id": request.viewer_session_id,
                    "approved_scope": approved_scope.value,
                    "approved_zones": list(zones),
                    "visual_body_exposure_allowed": visual_allowed,
                    "decision_event_hashes": [
                        response.event_sha256 for response in ordered
                    ],
                    "expires_at_clock_seconds": expires_at,
                    "one_shot_consumption_required": True,
                },
                now=now,
            )
            self._view_leases[capability].issuance_event_sha256 = audit[
                "event_sha256"
            ]
            return capability

    def note_material_context_change(
        self,
        *,
        previous_material_context_digest: str,
        new_material_context_digest: str,
    ) -> dict[str, Any]:
        previous = _exact_sha256(
            previous_material_context_digest, "previous_material_context_digest"
        )
        new = _exact_sha256(
            new_material_context_digest, "new_material_context_digest"
        )
        if previous == new:
            raise DecisionError("material context change requires a new digest")
        with self._lock:
            self.verify_audit_chain()
            invalidated = 0
            for request_capability, request in self._requests.items():
                if request.material_context_digest == previous:
                    request.invalidated_reason = "material_context_changed"
                    self._invalidate_request_leases_locked(
                        request_capability, "material_context_changed"
                    )
                    invalidated += 1
            now = self._now()
            audit = self._append_audit(
                "material_context_changed",
                {
                    "previous_material_context_digest": previous,
                    "new_material_context_digest": new,
                    "requests_invalidated": invalidated,
                },
                now=now,
            )
            return {
                "requests_invalidated": invalidated,
                "audit_event_sha256": audit["event_sha256"],
            }

    def consume_nonparticipant_view(
        self,
        lease_capability: NonparticipantViewLeaseV2,
        *,
        request_id: str,
        intended_viewer: str,
        viewer_session_id: str,
        approved_scope: ReconstructionScope,
        approved_zones: Sequence[str] = (),
        reconstruction_digest: str,
        material_context_digest: str,
    ) -> dict[str, Any]:
        request = _canonical_id(request_id, "request_id")
        viewer = _canonical_id(intended_viewer, "intended_viewer").casefold()
        session = _canonical_id(viewer_session_id, "viewer_session_id")
        scope = _scope(approved_scope, "approved_scope")
        zones = self._validate_zones(scope, approved_zones, "approved_zones")
        digest = _exact_sha256(reconstruction_digest, "reconstruction_digest")
        context_digest = _exact_sha256(
            material_context_digest, "material_context_digest"
        )
        with self._lock:
            self.verify_audit_chain()
            if not isinstance(lease_capability, NonparticipantViewLeaseV2):
                raise CapabilityError("exact nonparticipant view lease required")
            state = self._view_leases.get(lease_capability)
            if state is None:
                raise CapabilityError("view lease is a clone or belongs to another controller")
            self._verify_view_issuance_event_locked(state)
            now = self._now()
            if state.invalidated_reason:
                raise CapabilityError(f"view lease invalidated: {state.invalidated_reason}")
            if state.consumed:
                raise CapabilityError("view lease was already consumed")
            if now >= state.expires_at:
                state.invalidated_reason = "expired"
                raise CapabilityError("view lease expired")
            request_state = self._requests.get(state.request_capability)
            if request_state is None or request_state.invalidated_reason:
                raise CapabilityError("source request is no longer valid")
            ordered = [request_state.responses.get(person) for person in EXACT_PARTICIPANTS]
            if any(response is None for response in ordered):
                raise CapabilityError("required participant response disappeared")
            for response in ordered:
                assert response is not None
                self._verify_response_event_locked(request_state, response)
            if any(
                response.revoked or response.uncertain_after_decision
                for response in ordered
                if response is not None
            ):
                raise CapabilityError("current participant permission is no longer unanimous")
            if (
                request != state.request_id
                or viewer != state.viewer_id
                or session != state.viewer_session_id
                or scope is not state.approved_scope
                or zones != state.approved_zones
                or digest != state.reconstruction_digest
                or context_digest != state.material_context_digest
            ):
                raise CapabilityError("view lease binding mismatch")
            if digest != self._current_reconstruction_digest_locked():
                state.invalidated_reason = "reconstruction_changed"
                raise CapabilityError("reconstruction changed before consumption")
            state.consumed = True
            audit = self._append_audit(
                "nonparticipant_view_lease_consumed",
                {
                    "request_id": state.request_id,
                    "intended_viewer": state.viewer_id,
                    "viewer_session_id": state.viewer_session_id,
                    "approved_scope": state.approved_scope.value,
                    "approved_zones": list(state.approved_zones),
                    "visual_body_exposure_allowed": state.visual_body_exposure_allowed,
                    "reconstruction_digest": state.reconstruction_digest,
                    "material_context_digest": state.material_context_digest,
                    "one_shot_consumed": True,
                },
                now=now,
            )
            return {
                "status": "NONPARTICIPANT_RECONSTRUCTION_VIEW_AUTHORIZED_ONCE",
                "request_id": state.request_id,
                "intended_viewer": state.viewer_id,
                "viewer_session_id": state.viewer_session_id,
                "approved_scope": state.approved_scope.value,
                "approved_zones": list(state.approved_zones),
                "visual_body_exposure_allowed": state.visual_body_exposure_allowed,
                "locked_zone_access_allowed": state.approved_scope
                in {
                    ReconstructionScope.SELECTED_ZONES,
                    ReconstructionScope.ONE_TIME_FULL_REPLAY,
                    ReconstructionScope.FULL_REPLAY,
                },
                "full_replay_allowed": state.approved_scope in _FULL_SCOPES,
                "decision_event_hashes": list(state.decision_event_hashes),
                "audit_event_sha256": audit["event_sha256"],
                "private_content_in_receipt": False,
                "model_output_granted_permission": False,
                "lease_reusable": False,
            }

    def __getstate__(self) -> None:
        raise TypeError("reconstruction controller is memory-only and not serializable")


__all__ = [
    "AuthenticatedParticipantOrigin",
    "CapabilityError",
    "DecisionError",
    "EXACT_PARTICIPANTS",
    "IntegrityError",
    "KiraLisaReconstructionAccessControllerV2",
    "MAX_PARTICIPANT_SESSION_SECONDS",
    "MAX_REQUEST_SECONDS",
    "NonparticipantViewLeaseV2",
    "OwnPerspectiveVerbalPermitV2",
    "ParticipantDecision",
    "ParticipantPrivateLeaseV2",
    "PinnedAuthorityError",
    "RECONSTRUCTION_ID",
    "ReconstructionWriteOrigin",
    "ReconstructionAccessError",
    "ReconstructionAccessRequestV2",
    "ReconstructionScope",
    "SOURCE_MEMORY_ID",
    "SOURCE_MEMORY_SHA256",
]
