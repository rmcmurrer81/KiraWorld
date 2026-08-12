"""
Relationship state manager for Kira 2.0.

Relationship state records current emotional meaning between participants.
It is separate from memory and conversation logs.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


METRIC_KEYS = {
    "trust",
    "familiarity",
    "emotional_closeness",
    "comfort",
    "conflict_level",
    "privacy_sensitivity",
}

VALID_STATUS = {"draft", "active", "under_review", "archived"}
MAX_EVENT_DELTA = 0.15
VALID_EVENT_TYPES = {
    "vulnerable_share",
    "dream_share",
    "private_avoidance",
    "privacy_discovery",
    "gentle_disclosure",
    "conflict",
    "repair",
    "boundary_set",
    "apology",
    "inside_joke",
    "ordinary_warmth",
    "boundary_respected",
    "boundary_pressure",
    "other",
}


def clamp_metric(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def validate_relationship_state(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "relationship_id",
        "participants",
        "relationship_type",
        "metrics",
        "boundaries",
        "consent_context",
        "milestones",
        "unresolved_issues",
        "privacy_rules",
        "linked_records",
        "status",
    }
    missing = sorted(required - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if not data.get("relationship_id"):
        errors.append("relationship_id is required.")
    if not isinstance(data.get("participants"), list) or len(data.get("participants", [])) < 2:
        errors.append("participants must list at least two participants.")

    metrics = data.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("metrics must be an object.")
    else:
        missing_metrics = sorted(METRIC_KEYS - set(metrics))
        if missing_metrics:
            errors.append(f"Missing metrics: {', '.join(missing_metrics)}")
        for key in METRIC_KEYS & set(metrics):
            value = metrics.get(key)
            if not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
                errors.append(f"metrics.{key} must be a number from 0.0 to 1.0.")

    for key in ("boundaries", "milestones", "unresolved_issues", "linked_records"):
        if key in data and not isinstance(data.get(key), list):
            errors.append(f"{key} must be a list.")

    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")

    return errors


def validate_relationship_event(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "event_id",
        "relationship_id",
        "event_type",
        "participants",
        "privacy",
        "emotional_effect",
        "suggested_metric_changes",
        "relationship_update_policy",
        "status",
    }
    missing = sorted(required - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if not data.get("event_id"):
        errors.append("event_id is required.")
    if not data.get("relationship_id"):
        errors.append("relationship_id is required.")
    if data.get("event_type") not in VALID_EVENT_TYPES:
        errors.append(f"event_type must be one of: {', '.join(sorted(VALID_EVENT_TYPES))}")
    if not isinstance(data.get("participants"), list) or not data.get("participants"):
        errors.append("participants must be a non-empty list.")

    changes = data.get("suggested_metric_changes")
    if not isinstance(changes, dict):
        errors.append("suggested_metric_changes must be an object.")
    else:
        for key, value in changes.items():
            if key not in METRIC_KEYS:
                errors.append(f"unknown metric in suggested_metric_changes: {key}")
            elif not isinstance(value, (int, float)):
                errors.append(f"suggested_metric_changes.{key} must be a number.")
            elif abs(float(value)) > MAX_EVENT_DELTA:
                errors.append(f"suggested_metric_changes.{key} exceeds max event delta {MAX_EVENT_DELTA}.")

    policy = data.get("relationship_update_policy")
    if not isinstance(policy, dict):
        errors.append("relationship_update_policy must be an object.")
    else:
        if policy.get("creates_romance") is True:
            errors.append("relationship events cannot directly create romance.")
        if policy.get("creates_intimacy") is True:
            errors.append("relationship events cannot directly create intimacy.")
        if policy.get("requires_review_before_apply") is not False and data.get("status") == "applied":
            errors.append("applied events must not require review before apply.")

    return errors


class RelationshipStateManager:
    def __init__(self, state_file: str | Path = "Data/relationships/relationship_states.json") -> None:
        self.state_path = Path(state_file)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            self._write_states([])

    def _read_states(self) -> list[dict[str, Any]]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write_states(self, states: list[dict[str, Any]]) -> None:
        self.state_path.write_text(json.dumps(states, indent=2, ensure_ascii=False), encoding="utf-8")

    def list_states(self) -> list[dict[str, Any]]:
        return self._read_states()

    def get_state(self, relationship_id: str) -> dict[str, Any] | None:
        for state in self._read_states():
            if state.get("relationship_id") == relationship_id:
                return state
        return None

    def add_state(self, state: dict[str, Any]) -> None:
        errors = validate_relationship_state(state)
        if errors:
            raise ValueError("; ".join(errors))
        states = self._read_states()
        if any(existing.get("relationship_id") == state.get("relationship_id") for existing in states):
            raise ValueError(f"relationship_id already exists: {state.get('relationship_id')}")
        states.append(deepcopy(state))
        self._write_states(states)

    def update_metrics(self, relationship_id: str, changes: dict[str, float]) -> dict[str, Any]:
        states = self._read_states()
        for state in states:
            if state.get("relationship_id") != relationship_id:
                continue
            metrics = state.setdefault("metrics", {})
            for key, delta in changes.items():
                if key not in METRIC_KEYS:
                    raise ValueError(f"unknown relationship metric: {key}")
                metrics[key] = clamp_metric(float(metrics.get(key, 0.0)) + float(delta))
            state["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._write_states(states)
            return state
        raise KeyError(relationship_id)

    def add_milestone(self, relationship_id: str, milestone: dict[str, Any]) -> dict[str, Any]:
        return self._append_to_list(relationship_id, "milestones", milestone)

    def add_unresolved_issue(self, relationship_id: str, issue: dict[str, Any]) -> dict[str, Any]:
        return self._append_to_list(relationship_id, "unresolved_issues", issue)

    def apply_event(self, event: dict[str, Any]) -> dict[str, Any]:
        errors = validate_relationship_event(event)
        if errors:
            raise ValueError("; ".join(errors))
        policy = event.get("relationship_update_policy", {})
        if policy.get("requires_review_before_apply") is True:
            raise ValueError("event requires review before apply")
        relationship_id = event["relationship_id"]
        changes = event.get("suggested_metric_changes", {})
        updated = self.update_metrics(relationship_id, changes)
        linked_records = updated.setdefault("linked_records", [])
        event_id = event.get("event_id")
        if event_id and event_id not in linked_records:
            linked_records.append(event_id)
        updated["recent_emotional_tone"] = event.get(
            "resulting_tone",
            updated.get("recent_emotional_tone", "mixed"),
        )
        states = self._read_states()
        for index, state in enumerate(states):
            if state.get("relationship_id") == relationship_id:
                states[index] = updated
                break
        self._write_states(states)
        return updated

    def _append_to_list(self, relationship_id: str, field: str, item: dict[str, Any]) -> dict[str, Any]:
        states = self._read_states()
        for state in states:
            if state.get("relationship_id") != relationship_id:
                continue
            state.setdefault(field, []).append(deepcopy(item))
            state["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._write_states(states)
            return state
        raise KeyError(relationship_id)
