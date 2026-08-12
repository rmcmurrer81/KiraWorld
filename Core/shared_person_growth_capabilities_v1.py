"""Shared, person-separated growth primitives for synthetic people.

This module is deliberately narrower than a complete mind.  It creates a
fresh capability profile for one exact person and supplies a bounded,
lease-bound in-memory session for source-grounded present facts, learning
proposals, and causal emotion records.  It does not call a model, write a
promoted memory, infer maturity, grant consent, execute an action, or copy
another person's private state.

The same code/schema may be shared after acceptance.  Identity, memories,
backstory, private emotions, relationships, permissions, maturity and lived
experience may not be shared.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import threading
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = PROJECT_ROOT / "Data" / "foundation" / "shared_person_growth_capabilities_v1.json"
PROFILE_SCHEMA = "kira.shared_person_growth_profile.v1"
EVENT_SCHEMA = "kira.shared_person_growth_event.v1"
CREATOR_ATTACHMENT_SCHEMA = "kira.temporary_creator_growth_attachment.v1"
ROLLOUT_STAGES = (
    "DESIGN_ONLY",
    "STATIC_CANDIDATE",
    "STATIC_AUDITED",
    "BOUNDED_LIVE_ACCEPTED",
    "SHARED_PERSON_ENABLED",
)
MATURITY_STATUSES = frozenset({"confirmed_adult", "non_adult", "unresolved"})
PRIVACY_CLASSES = frozenset(
    {"public_shared", "person_private", "multi_person_private", "maturity_restricted"}
)
SOURCE_KINDS = frozenset(
    {"owner_statement", "reviewed_memory", "sensory_receipt", "media_receipt", "tool_receipt", "correction_receipt"}
)
CONTRADICTION_STATES = frozenset(
    {"not_checked", "no_conflict_found", "possible_conflict", "blocked_conflict"}
)
REVIEW_DECISIONS = frozenset({"accept_for_separate_memory_review", "reject", "defer"})
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{2,127}$")
_RELATIVE_ROOT_RE = re.compile(r"^Data/person_private/[a-f0-9]{32}/[a-z_]+$")


class GrowthCapabilityError(ValueError):
    """Raised when a shared capability record crosses a truth boundary."""


class GrowthLeaseError(PermissionError):
    """Raised when a caller does not hold the exact active person's lease."""


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_mapping(value: Mapping[str, Any]) -> str:
    return _sha256_bytes(_canonical_json_bytes(value))


def _lower_sha(value: Any, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise GrowthCapabilityError(f"{field_name} must be lowercase SHA-256")
    return value


def _identifier(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
        raise GrowthCapabilityError(f"{field_name} must be a canonical identifier")
    return value


def _text(value: Any, field_name: str, maximum: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GrowthCapabilityError(f"{field_name} must be non-empty text")
    normalized = value.strip()
    if len(normalized.encode("utf-8")) > maximum:
        raise GrowthCapabilityError(f"{field_name} exceeds {maximum} UTF-8 bytes")
    return normalized


def _unit(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GrowthCapabilityError(f"{field_name} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise GrowthCapabilityError(f"{field_name} must be from 0 to 1")
    return result


def _utc(value: Any, field_name: str) -> datetime:
    text = _text(value, field_name, 64)
    if not text.endswith("Z"):
        raise GrowthCapabilityError(f"{field_name} must be canonical UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise GrowthCapabilityError(f"{field_name} must be valid UTC") from exc
    if parsed.tzinfo != timezone.utc:
        raise GrowthCapabilityError(f"{field_name} must be UTC")
    return parsed


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GrowthCapabilityError("growth capability policy is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise GrowthCapabilityError("growth capability policy must be an object")
    if value.get("schema") != "kira.shared_person_growth_capabilities_policy.v1":
        raise GrowthCapabilityError("growth capability policy schema mismatch")
    if value.get("rollout_order") != list(ROLLOUT_STAGES):
        raise GrowthCapabilityError("growth capability rollout order drifted")
    capabilities = value.get("capabilities")
    if not isinstance(capabilities, dict) or not capabilities:
        raise GrowthCapabilityError("growth capability catalog is missing")
    for capability_id, definition in capabilities.items():
        _identifier(capability_id, "capability_id")
        if not isinstance(definition, dict):
            raise GrowthCapabilityError("each capability definition must be an object")
        if definition.get("stage") not in ROLLOUT_STAGES:
            raise GrowthCapabilityError("capability stage is unsupported")
        if not isinstance(definition.get("live_enabled"), bool):
            raise GrowthCapabilityError("capability live_enabled must be boolean")
    if any(definition.get("live_enabled") for definition in capabilities.values()):
        raise GrowthCapabilityError("v1 static policy must not enable a live capability")
    return value


def policy_sha256(path: Path = POLICY_PATH) -> str:
    return _sha256_bytes(path.read_bytes())


def _private_root_token(person_id: str, profile_id: str, root_nonce_sha256: str) -> str:
    material = f"{person_id}\n{profile_id}\n{root_nonce_sha256}\n".encode("utf-8")
    return _sha256_bytes(material)[:32]


def build_fresh_capability_profile(
    *,
    person_id: str,
    candidate_id: str,
    profile_id: str,
    root_nonce_sha256: str,
    maturity_status: str,
    policy_path: Path = POLICY_PATH,
) -> dict[str, Any]:
    """Build one fresh, inactive profile without copying person-private data."""

    person_id = _identifier(person_id, "person_id")
    candidate_id = _identifier(candidate_id, "candidate_id")
    profile_id = _identifier(profile_id, "profile_id")
    root_nonce_sha256 = _lower_sha(root_nonce_sha256, "root_nonce_sha256")
    if maturity_status not in MATURITY_STATUSES:
        raise GrowthCapabilityError("maturity_status is unsupported")
    policy = load_policy(policy_path)
    root_token = _private_root_token(person_id, profile_id, root_nonce_sha256)
    prefix = f"Data/person_private/{root_token}"
    capabilities = deepcopy(policy["capabilities"])
    profile: dict[str, Any] = {
        "schema": PROFILE_SCHEMA,
        "profile_id": profile_id,
        "person_binding": {
            "person_id": person_id,
            "candidate_id": candidate_id,
            "person_and_candidate_are_distinct_bindings": True,
            "owner_or_name_equivalence_grants_nothing": True,
        },
        "policy": {
            "path": policy_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": policy_sha256(policy_path),
            "stage": "STATIC_CANDIDATE",
        },
        "maturity": {
            "status": maturity_status,
            "classification_inferred_by_this_module": False,
            "full_adult_curriculum_eligible": maturity_status == "confirmed_adult",
            "full_adult_curriculum_delivered": False,
            "adult_anatomy_added": False,
            "consent_granted": False,
            "default_body_lane": (
                "separately_selected_adult_body_pending"
                if maturity_status == "confirmed_adult"
                else "doll_safe_non_anatomical"
            ),
        },
        "private_state_roots": {
            "present_context": f"{prefix}/present_context",
            "learning_proposals": f"{prefix}/learning_proposals",
            "emotion": f"{prefix}/emotion",
            "initiative": f"{prefix}/initiative",
            "memory_review": f"{prefix}/memory_review",
        },
        "capabilities": capabilities,
        "truth_boundaries": {
            "model_output_is_advisory": True,
            "present_context_is_not_memory": True,
            "learning_proposal_is_not_promoted_memory": True,
            "private_emotion_is_not_public_speech": True,
            "body_response_is_not_desire_or_consent": True,
            "permission_is_not_relationship_or_preference": True,
            "opening_media_is_not_experience": True,
        },
        "inheritance": {
            "shared_code_and_schema_only": True,
            "never_inherited": list(policy["never_inherited_from_another_person"]),
            "source_person_id": None,
            "source_profile_id": None,
            "copied_private_records": 0,
            "copied_capability_leases": 0,
            "copied_acceptance_receipts": 0,
        },
        "runtime": {
            "activated": False,
            "model_connected": False,
            "memory_writer_connected": False,
            "external_actions_connected": False,
            "sensory_devices_connected": False,
            "media_playback_connected": False,
            "body_control_connected": False,
        },
    }
    profile["profile_fingerprint_sha256"] = _sha256_mapping(profile)
    validate_capability_profile(profile, policy_path=policy_path)
    return profile


def validate_capability_profile(
    profile: Mapping[str, Any], *, policy_path: Path = POLICY_PATH
) -> dict[str, Any]:
    if not isinstance(profile, Mapping) or profile.get("schema") != PROFILE_SCHEMA:
        raise GrowthCapabilityError("capability profile schema mismatch")
    person = profile.get("person_binding")
    if not isinstance(person, Mapping):
        raise GrowthCapabilityError("person binding is missing")
    _identifier(person.get("person_id"), "person_id")
    _identifier(person.get("candidate_id"), "candidate_id")
    _identifier(profile.get("profile_id"), "profile_id")
    maturity = profile.get("maturity")
    if not isinstance(maturity, Mapping) or maturity.get("status") not in MATURITY_STATUSES:
        raise GrowthCapabilityError("maturity status is missing or unsupported")
    is_adult = maturity["status"] == "confirmed_adult"
    if maturity.get("full_adult_curriculum_eligible") is not is_adult:
        raise GrowthCapabilityError("adult curriculum eligibility drifted from exact maturity")
    for forbidden_true in ("full_adult_curriculum_delivered", "adult_anatomy_added", "consent_granted"):
        if maturity.get(forbidden_true) is not False:
            raise GrowthCapabilityError(f"{forbidden_true} cannot be inherited or inferred")
    policy = profile.get("policy")
    if not isinstance(policy, Mapping):
        raise GrowthCapabilityError("policy binding is missing")
    if policy.get("sha256") != policy_sha256(policy_path):
        raise GrowthCapabilityError("policy hash mismatch")
    roots = profile.get("private_state_roots")
    if not isinstance(roots, Mapping) or len(roots) != 5:
        raise GrowthCapabilityError("private state roots are incomplete")
    root_values = list(roots.values())
    if len(set(root_values)) != len(root_values):
        raise GrowthCapabilityError("private state roots must be distinct")
    prefixes = set()
    for root in root_values:
        if not isinstance(root, str) or _RELATIVE_ROOT_RE.fullmatch(root) is None:
            raise GrowthCapabilityError("private state root is not canonical")
        prefixes.add(root.rsplit("/", 1)[0])
    if len(prefixes) != 1:
        raise GrowthCapabilityError("private state roots cross person namespaces")
    capabilities = profile.get("capabilities")
    policy_capabilities = load_policy(policy_path)["capabilities"]
    if capabilities != policy_capabilities:
        raise GrowthCapabilityError("capability catalog drifted from policy")
    runtime = profile.get("runtime")
    if not isinstance(runtime, Mapping) or any(value is not False for value in runtime.values()):
        raise GrowthCapabilityError("static profile must leave every runtime route disabled")
    inheritance = profile.get("inheritance")
    if not isinstance(inheritance, Mapping):
        raise GrowthCapabilityError("inheritance boundary is missing")
    if inheritance.get("shared_code_and_schema_only") is not True:
        raise GrowthCapabilityError("only code and schema may be shared")
    for field in ("copied_private_records", "copied_capability_leases", "copied_acceptance_receipts"):
        if inheritance.get(field) != 0:
            raise GrowthCapabilityError("person-private inheritance is forbidden")
    fingerprint = profile.get("profile_fingerprint_sha256")
    _lower_sha(fingerprint, "profile_fingerprint_sha256")
    unsigned = deepcopy(dict(profile))
    unsigned.pop("profile_fingerprint_sha256", None)
    if _sha256_mapping(unsigned) != fingerprint:
        raise GrowthCapabilityError("profile fingerprint mismatch")
    return deepcopy(dict(profile))


@dataclass(frozen=True, slots=True)
class GrowthLease:
    person_id: str
    profile_id: str
    activation_revision: str
    session_nonce_sha256: str


class PersonGrowthSession:
    """One bounded memory-only proposal session for one exact person."""

    def __init__(
        self,
        *,
        profile: Mapping[str, Any],
        activation_revision: str,
        session_nonce_sha256: str,
        clock: Callable[[], float],
        max_events: int = 128,
    ) -> None:
        self._profile = validate_capability_profile(profile)
        if not callable(clock):
            raise GrowthCapabilityError("clock must be callable")
        if isinstance(max_events, bool) or not isinstance(max_events, int) or not 1 <= max_events <= 512:
            raise GrowthCapabilityError("max_events must be an integer from 1 to 512")
        binding = self._profile["person_binding"]
        self._lease = GrowthLease(
            person_id=binding["person_id"],
            profile_id=self._profile["profile_id"],
            activation_revision=_identifier(activation_revision, "activation_revision"),
            session_nonce_sha256=_lower_sha(session_nonce_sha256, "session_nonce_sha256"),
        )
        self._clock = clock
        self._max_events = max_events
        self._last_clock: float | None = None
        self._events: list[dict[str, Any]] = []
        self._known_present_event_ids: set[str] = set()
        self._known_proposal_ids: set[str] = set()
        self._active = True
        self._lock = threading.RLock()

    @property
    def lease(self) -> GrowthLease:
        return self._lease

    def _require(self, lease: GrowthLease) -> None:
        if not isinstance(lease, GrowthLease) or lease != self._lease or not self._active:
            raise GrowthLeaseError("growth lease does not match the active person/profile/session")

    def _timestamp(self) -> float:
        raw = self._clock()
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise GrowthCapabilityError("clock must return a finite number")
        value = float(raw)
        if not math.isfinite(value) or value < 0:
            raise GrowthCapabilityError("clock must return a nonnegative finite number")
        if self._last_clock is not None and value < self._last_clock:
            raise GrowthCapabilityError("clock must remain monotonic")
        self._last_clock = value
        return value

    def _append(self, kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if len(self._events) >= self._max_events:
            raise GrowthCapabilityError("growth session event limit reached")
        previous = self._events[-1]["event_sha256"] if self._events else "0" * 64
        event = {
            "schema": EVENT_SCHEMA,
            "sequence": len(self._events) + 1,
            "kind": _identifier(kind, "event_kind"),
            "person_id": self._lease.person_id,
            "profile_id": self._lease.profile_id,
            "activation_revision": self._lease.activation_revision,
            "recorded_at_monotonic_seconds": self._timestamp(),
            "previous_event_sha256": previous,
            **deepcopy(dict(payload)),
            "model_generation_performed": False,
            "durable_memory_mutated": False,
            "external_action_executed": False,
        }
        event["event_sha256"] = _sha256_mapping(event)
        self._events.append(event)
        return deepcopy(event)

    def record_present_fact(
        self,
        lease: GrowthLease,
        *,
        present_event_id: str,
        factual_summary: str,
        source_kind: str,
        source_receipt_sha256: str,
        observed_at_utc: str,
        expires_at_utc: str,
    ) -> dict[str, Any]:
        with self._lock:
            self._require(lease)
            present_event_id = _identifier(present_event_id, "present_event_id")
            if present_event_id in self._known_present_event_ids:
                raise GrowthCapabilityError("present_event_id was already used")
            if source_kind not in SOURCE_KINDS:
                raise GrowthCapabilityError("source_kind is unsupported")
            observed = _utc(observed_at_utc, "observed_at_utc")
            expires = _utc(expires_at_utc, "expires_at_utc")
            if expires <= observed:
                raise GrowthCapabilityError("present fact expiry must follow observation")
            event = self._append(
                "present_fact",
                {
                    "present_event_id": present_event_id,
                    "factual_summary": _text(factual_summary, "factual_summary"),
                    "source_kind": source_kind,
                    "source_receipt_sha256": _lower_sha(source_receipt_sha256, "source_receipt_sha256"),
                    "observed_at_utc": observed_at_utc,
                    "expires_at_utc": expires_at_utc,
                    "present_context_only": True,
                    "memory_promotion_proposed": False,
                },
            )
            self._known_present_event_ids.add(present_event_id)
            return event

    def propose_learning(
        self,
        lease: GrowthLease,
        *,
        proposal_id: str,
        proposed_claim: str,
        source_present_event_ids: Sequence[str],
        privacy_class: str,
        contradiction_state: str,
    ) -> dict[str, Any]:
        with self._lock:
            self._require(lease)
            proposal_id = _identifier(proposal_id, "proposal_id")
            if proposal_id in self._known_proposal_ids:
                raise GrowthCapabilityError("proposal_id was already used")
            if isinstance(source_present_event_ids, (str, bytes)) or not isinstance(source_present_event_ids, Sequence):
                raise GrowthCapabilityError("source_present_event_ids must be a sequence")
            source_ids = tuple(_identifier(item, "source_present_event_id") for item in source_present_event_ids)
            if not source_ids or len(set(source_ids)) != len(source_ids):
                raise GrowthCapabilityError("learning proposal needs unique source events")
            if any(item not in self._known_present_event_ids for item in source_ids):
                raise GrowthCapabilityError("learning proposal references an unknown present fact")
            if privacy_class not in PRIVACY_CLASSES:
                raise GrowthCapabilityError("privacy_class is unsupported")
            if contradiction_state not in CONTRADICTION_STATES:
                raise GrowthCapabilityError("contradiction_state is unsupported")
            event = self._append(
                "learning_proposal",
                {
                    "proposal_id": proposal_id,
                    "proposed_claim": _text(proposed_claim, "proposed_claim"),
                    "source_present_event_ids": list(source_ids),
                    "privacy_class": privacy_class,
                    "contradiction_state": contradiction_state,
                    "proposal_state": "PROPOSED_NOT_MEMORY",
                    "promotion_requires_separate_person_owned_review": True,
                },
            )
            self._known_proposal_ids.add(proposal_id)
            return event

    def review_learning_proposal(
        self,
        lease: GrowthLease,
        *,
        proposal_id: str,
        decision: str,
        review_authority_receipt_sha256: str,
    ) -> dict[str, Any]:
        with self._lock:
            self._require(lease)
            proposal_id = _identifier(proposal_id, "proposal_id")
            if proposal_id not in self._known_proposal_ids:
                raise GrowthCapabilityError("learning proposal is unknown")
            if decision not in REVIEW_DECISIONS:
                raise GrowthCapabilityError("learning review decision is unsupported")
            return self._append(
                "learning_review",
                {
                    "proposal_id": proposal_id,
                    "decision": decision,
                    "review_authority_receipt_sha256": _lower_sha(
                        review_authority_receipt_sha256,
                        "review_authority_receipt_sha256",
                    ),
                    "separate_memory_writer_still_required": decision == "accept_for_separate_memory_review",
                    "memory_written_by_this_review": False,
                },
            )

    def record_causal_emotion(
        self,
        lease: GrowthLease,
        *,
        emotion_event_id: str,
        cause_present_event_ids: Sequence[str],
        possible_interpretations: Sequence[str],
        selected_appraisal: str,
        emotion_label: str,
        intensity: float,
        confidence: float,
        unresolved: bool,
    ) -> dict[str, Any]:
        with self._lock:
            self._require(lease)
            if not isinstance(unresolved, bool):
                raise GrowthCapabilityError("unresolved must be boolean")
            if isinstance(cause_present_event_ids, (str, bytes)) or not isinstance(cause_present_event_ids, Sequence):
                raise GrowthCapabilityError("cause_present_event_ids must be a sequence")
            cause_ids = tuple(_identifier(item, "cause_present_event_id") for item in cause_present_event_ids)
            if not cause_ids or any(item not in self._known_present_event_ids for item in cause_ids):
                raise GrowthCapabilityError("causal emotion requires known present facts")
            if isinstance(possible_interpretations, (str, bytes)) or not isinstance(possible_interpretations, Sequence):
                raise GrowthCapabilityError("possible_interpretations must be a sequence")
            interpretations = [_text(item, "possible_interpretation", 500) for item in possible_interpretations]
            if not interpretations or len(interpretations) > 8:
                raise GrowthCapabilityError("causal emotion needs one to eight interpretations")
            return self._append(
                "causal_emotion",
                {
                    "emotion_event_id": _identifier(emotion_event_id, "emotion_event_id"),
                    "cause_present_event_ids": list(cause_ids),
                    "possible_interpretations": interpretations,
                    "possible_interpretations_are_advisory": True,
                    "selected_appraisal": _text(selected_appraisal, "selected_appraisal"),
                    "emotion_label": _text(emotion_label, "emotion_label", 128),
                    "intensity": _unit(intensity, "intensity"),
                    "confidence": _unit(confidence, "confidence"),
                    "unresolved": unresolved,
                    "visibility": "person_private",
                    "public_expression_selected": False,
                    "physiological_response_recorded": False,
                    "private_desire_recorded": False,
                    "preference_recorded": False,
                    "consent_recorded": False,
                    "health_state_recorded": False,
                },
            )

    def public_snapshot(self, lease: GrowthLease) -> dict[str, Any]:
        with self._lock:
            self._require(lease)
            return {
                "schema": "kira.shared_person_growth_public_snapshot.v1",
                "person_id": self._lease.person_id,
                "profile_id": self._lease.profile_id,
                "event_count": len(self._events),
                "head_event_sha256": self._events[-1]["event_sha256"] if self._events else "0" * 64,
                "private_payload_exposed": False,
                "memory_persisted": False,
                "external_action_executed": False,
                "storage": "bounded_memory_only",
            }

    def private_records(self, lease: GrowthLease) -> list[dict[str, Any]]:
        with self._lock:
            self._require(lease)
            return deepcopy(self._events)

    def deactivate(self, lease: GrowthLease) -> dict[str, Any]:
        with self._lock:
            self._require(lease)
            count = len(self._events)
            self._events.clear()
            self._known_present_event_ids.clear()
            self._known_proposal_ids.clear()
            self._active = False
            return {
                "person_id": self._lease.person_id,
                "purged_memory_only_event_count": count,
                "durable_memory_deleted": False,
                "identity_changed": False,
            }

    def __getstate__(self) -> None:
        raise TypeError("PersonGrowthSession is memory-only and not serializable")


def build_temporary_creator_attachment(
    *,
    candidate_id: str,
    display_name: str,
    person_id: str,
    profile_id: str,
    root_nonce_sha256: str,
    maturity_status: str,
) -> dict[str, Any]:
    """Return the inert document Temporary Creator can write for a new person."""

    candidate_id = _identifier(candidate_id, "candidate_id")
    profile = build_fresh_capability_profile(
        person_id=person_id,
        candidate_id=candidate_id,
        profile_id=profile_id,
        root_nonce_sha256=root_nonce_sha256,
        maturity_status=maturity_status,
    )
    attachment = {
        "schema": CREATOR_ATTACHMENT_SCHEMA,
        "candidate_id": candidate_id,
        "display_name": _text(display_name, "display_name", 256),
        "growth_profile": profile,
        "creator_truth": {
            "fresh_profile_created": True,
            "existing_person_profile_copied": False,
            "existing_person_private_data_read": False,
            "activation_allowed": False,
            "assignment_allowed": False,
            "model_or_device_called": False,
            "requires_separate_static_audit": True,
            "requires_bounded_live_acceptance_before_shared_enablement": True,
        },
    }
    attachment["attachment_sha256"] = _sha256_mapping(attachment)
    return attachment


def validate_temporary_creator_attachment(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema") != CREATOR_ATTACHMENT_SCHEMA:
        raise GrowthCapabilityError("creator attachment schema mismatch")
    candidate_id = _identifier(value.get("candidate_id"), "candidate_id")
    _text(value.get("display_name"), "display_name", 256)
    profile = validate_capability_profile(value.get("growth_profile"))
    if profile["person_binding"]["candidate_id"] != candidate_id:
        raise GrowthCapabilityError("creator attachment candidate binding mismatch")
    truth = value.get("creator_truth")
    if not isinstance(truth, Mapping):
        raise GrowthCapabilityError("creator truth is missing")
    required_true = {
        "fresh_profile_created",
        "requires_separate_static_audit",
        "requires_bounded_live_acceptance_before_shared_enablement",
    }
    required_false = {
        "existing_person_profile_copied",
        "existing_person_private_data_read",
        "activation_allowed",
        "assignment_allowed",
        "model_or_device_called",
    }
    if any(truth.get(field) is not True for field in required_true):
        raise GrowthCapabilityError("creator attachment lost a required true boundary")
    if any(truth.get(field) is not False for field in required_false):
        raise GrowthCapabilityError("creator attachment enabled or copied a forbidden route")
    digest = _lower_sha(value.get("attachment_sha256"), "attachment_sha256")
    unsigned = deepcopy(dict(value))
    unsigned.pop("attachment_sha256", None)
    if _sha256_mapping(unsigned) != digest:
        raise GrowthCapabilityError("creator attachment hash mismatch")
    return deepcopy(dict(value))

