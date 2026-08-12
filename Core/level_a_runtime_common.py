"""Shared primitives for the deterministic Level-A non-person fixture runtime.

Level A is engineering evidence only.  These helpers deliberately reject
person identity, memory, relationship, maturity, and consent payloads so a
fixture event cannot be reinterpreted as a synthetic person's lived event.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
import re
from typing import Any, Mapping


FIXTURE_KIND = "NON_PERSON_DETERMINISTIC_FIXTURE"
CAPABILITY_LADDER = (
    "NOT_IMPLEMENTED",
    "CONTRACT_ONLY",
    "NON_PERSON_FIXTURE_PASS",
    "BODY_HOOKS_VERIFIED",
    "PHYSIOLOGY_STATE_VERIFIED",
    "PERSON_DECISION_INTEGRATED",
    "PRIVACY_AND_CONTINUITY_PASS",
    "OWNER_SUPERVISED_PASS",
    "GENERALIZATION_PASS",
    "AVATAR_BUILDER_METHOD_PROMOTED",
)
LEVEL_A_MAX_STATUS = "NON_PERSON_FIXTURE_PASS"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

FORBIDDEN_PERSON_PAYLOAD_KEYS = frozenset(
    {
        "person_id",
        "person_identity",
        "private_mind",
        "spoken",
        "memory",
        "memories",
        "relationship",
        "relationship_status",
        "preference",
        "desire",
        "consent",
        "maturity_status",
        "classification_evidence",
        "voice_profile",
        "person_likeness",
    }
)

FORBIDDEN_PERSON_PAYLOAD_TERMS = frozenset(
    {
        "person",
        "mind",
        "memory",
        "relationship",
        "preference",
        "desire",
        "consent",
        "maturity",
        "voice",
        "likeness",
    }
)


class LevelARuntimeError(ValueError):
    """Base deterministic fixture validation failure."""


class LevelABoundaryError(LevelARuntimeError):
    """A caller attempted to cross the non-person Level-A boundary."""


class LevelATransitionError(LevelARuntimeError):
    """A state transition was invalid or out of order."""


class LevelAConservationError(LevelARuntimeError):
    """A reservoir or route conservation invariant failed."""


class LevelADiagnosisBoundaryError(LevelARuntimeError):
    """An observation or test was improperly converted into diagnosis."""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def require_identifier(value: Any, field: str) -> str:
    result = str(value or "").strip()
    if not result or len(result) > 160:
        raise LevelARuntimeError(f"{field} must be a nonempty bounded identifier")
    if any(character in result for character in ("/", "\\", "\x00")):
        raise LevelARuntimeError(f"{field} contains a forbidden path character")
    return result


def require_nonnegative_int(value: Any, field: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LevelARuntimeError(f"{field} must be an integer")
    if value < (1 if positive else 0):
        qualifier = "positive" if positive else "nonnegative"
        raise LevelARuntimeError(f"{field} must be {qualifier}")
    return value


def parse_utc(value: Any, field: str = "at_utc") -> datetime:
    raw = str(value or "").strip()
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise LevelARuntimeError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise LevelARuntimeError(f"{field} must include a timezone offset")
    if parsed.utcoffset().total_seconds() != 0.0:
        raise LevelARuntimeError(f"{field} must resolve to UTC")
    return parsed


def assert_level_a_capability_status(value: Any, field: str) -> str:
    status = str(value or "")
    if status not in CAPABILITY_LADDER:
        raise LevelABoundaryError(f"{field} uses an unknown capability status")
    if CAPABILITY_LADDER.index(status) > CAPABILITY_LADDER.index(LEVEL_A_MAX_STATUS):
        raise LevelABoundaryError(
            f"{field} exceeds the Level-A non-person evidence ceiling"
        )
    return status


def _walk_payload(value: Any, *, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            folded = key.casefold()
            tokens = frozenset(part for part in re.split(r"[^a-z0-9]+", folded) if part)
            if (
                folded in FORBIDDEN_PERSON_PAYLOAD_KEYS
                or tokens.intersection(FORBIDDEN_PERSON_PAYLOAD_TERMS)
            ):
                raise LevelABoundaryError(
                    f"{path}.{key} is person-layer data and is forbidden in Level A"
                )
            _walk_payload(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _walk_payload(child, path=f"{path}[{index}]")


def validate_event(
    event: Mapping[str, Any],
    *,
    allowed_domains: frozenset[str],
    prior_event_ids: set[str],
    current_clock_utc: str,
) -> dict[str, Any]:
    if not isinstance(event, Mapping):
        raise LevelARuntimeError("event must be an object")
    if set(event) != {"event_id", "at_utc", "domain", "action", "payload"}:
        raise LevelARuntimeError("event fields must be exact")
    event_id = require_identifier(event.get("event_id"), "event_id")
    if event_id in prior_event_ids:
        raise LevelATransitionError(f"duplicate event_id: {event_id}")
    domain = str(event.get("domain") or "").strip()
    if domain not in allowed_domains:
        raise LevelATransitionError(f"unsupported event domain: {domain}")
    action = require_identifier(event.get("action"), "action")
    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        raise LevelARuntimeError("event payload must be an object")
    _walk_payload(payload)
    event_time = parse_utc(event.get("at_utc"))
    if event_time < parse_utc(current_clock_utc, "current_clock_utc"):
        raise LevelATransitionError("event time cannot move backward")
    return {
        "event_id": event_id,
        "at_utc": str(event["at_utc"]),
        "domain": domain,
        "action": action,
        "payload": deepcopy(dict(payload)),
    }


def append_event_receipt(state: dict[str, Any], event: Mapping[str, Any]) -> None:
    receipt = {
        "event_id": event["event_id"],
        "at_utc": event["at_utc"],
        "domain": event["domain"],
        "action": event["action"],
        "payload_sha256": canonical_sha256(event["payload"]),
        "event_is_person_memory": False,
        "event_is_lived_experience": False,
    }
    state["event_log"].append(receipt)
    state["seen_event_ids"].append(event["event_id"])
    state["revision"] += 1
    state["clock_utc"] = event["at_utc"]


def validate_event_ledger(state: Mapping[str, Any]) -> None:
    revision = require_nonnegative_int(state.get("revision"), "revision")
    seen = state.get("seen_event_ids")
    event_log = state.get("event_log")
    if not isinstance(seen, list) or not isinstance(event_log, list):
        raise LevelARuntimeError("event ledger must be a list")
    if len(seen) != len(set(seen)) or len(seen) != len(event_log) or revision != len(seen):
        raise LevelATransitionError("event ledger or revision drifted")
    if [row.get("event_id") for row in event_log] != seen:
        raise LevelATransitionError("event ledger ordering drifted")
    prior_time: datetime | None = None
    exact_fields = {
        "event_id",
        "at_utc",
        "domain",
        "action",
        "payload_sha256",
        "event_is_person_memory",
        "event_is_lived_experience",
    }
    for index, row in enumerate(event_log):
        if not isinstance(row, Mapping) or set(row) != exact_fields:
            raise LevelATransitionError(f"event receipt {index} fields drifted")
        require_identifier(row.get("event_id"), f"event_log[{index}].event_id")
        require_identifier(row.get("domain"), f"event_log[{index}].domain")
        require_identifier(row.get("action"), f"event_log[{index}].action")
        digest = row.get("payload_sha256")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise LevelATransitionError(f"event receipt {index} payload hash is invalid")
        current_time = parse_utc(row.get("at_utc"), f"event_log[{index}].at_utc")
        if prior_time is not None and current_time < prior_time:
            raise LevelATransitionError("event receipt time moved backward")
        prior_time = current_time
        if (
            row.get("event_is_person_memory") is not False
            or row.get("event_is_lived_experience") is not False
        ):
            raise LevelABoundaryError("event ledger became memory or lived experience")
    clock = parse_utc(state.get("clock_utc"), "clock_utc")
    if prior_time is not None and clock != prior_time:
        raise LevelATransitionError("event ledger final time and fixture clock differ")


def deep_copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return deepcopy(dict(value))
