"""Deterministic Person/World boundary fixture for Level-A testing.

The neutral actors in this module are labels used by a test harness, not
synthetic people.  Their responses can exercise privacy and coordination logic
but never become person consent, an authorized external action, or memory.
"""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping

from Core.level_a_runtime_common import (
    CAPABILITY_LADDER,
    FIXTURE_KIND,
    LevelABoundaryError,
    LevelARuntimeError,
    LevelATransitionError,
    append_event_receipt,
    assert_level_a_capability_status,
    canonical_json,
    canonical_sha256,
    parse_utc,
    require_identifier,
    validate_event,
    validate_event_ledger,
)


MODEL_ID = "person_world_level_a_non_person_boundary_v1"
DOMAINS = frozenset({"privacy", "coordination", "action", "audit_memory"})
RESPONSES = frozenset({"yes", "no", "uncertain"})
PRIVACY_STATES = frozenset({"open", "locked"})
COORDINATION_STATES = frozenset(
    {
        "none",
        "proposed",
        "responses_pending",
        "fixture_gate_satisfied",
        "fixture_gate_blocked",
        "stopped",
        "interrupted",
        "recovered",
    }
)


def create_person_world_fixture(
    *, fixture_id: str, actor_fixture_ids: list[str], started_at_utc: str
) -> dict[str, Any]:
    fixture = require_identifier(fixture_id, "fixture_id")
    actors = [require_identifier(value, "actor_fixture_id") for value in actor_fixture_ids]
    if len(actors) < 2 or len(actors) != len(set(actors)):
        raise LevelARuntimeError("at least two unique neutral actor fixtures are required")
    parse_utc(started_at_utc, "started_at_utc")
    state = {
        "schema_version": 1,
        "model_id": MODEL_ID,
        "fixture_id": fixture,
        "fixture_kind": FIXTURE_KIND,
        "actor_fixture_ids": actors,
        "clock_utc": started_at_utc,
        "revision": 0,
        "seen_event_ids": [],
        "event_log": [],
        "capability_ladder": list(CAPABILITY_LADDER),
        "capability_statuses": {
            "locked_context_access_fixture": "NON_PERSON_FIXTURE_PASS",
            "decision_action_separation_fixture": "NON_PERSON_FIXTURE_PASS",
            "stop_interrupt_recovery_fixture": "NON_PERSON_FIXTURE_PASS",
            "persistence_no_false_memory_fixture": "NON_PERSON_FIXTURE_PASS",
            "person_decision_integration": "NOT_IMPLEMENTED",
            "person_private_memory": "NOT_IMPLEMENTED",
            "runtime_external_action": "NOT_IMPLEMENTED",
        },
        "privacy": {
            "context_id": None,
            "state": "open",
            "allowed_actor_fixture_ids": [],
            "denied_actor_fixture_ids": [],
            "pending_entry_requests": [],
            "content_storage_enabled": False,
            "private_content_stored": False,
            "person_privacy_claimed": False,
        },
        "coordination": {
            "proposal_id": None,
            "activity_id": None,
            "context_id": None,
            "participant_fixture_ids": [],
            "fixture_responses": {},
            "state": "none",
            "fixture_coordination_gate_satisfied": False,
            "current_person_consent_claimed": False,
            "prior_response_reusable": False,
        },
        "action": {
            "external_action_authorized": False,
            "external_action_performed": False,
            "block_reason": "LEVEL_A_HAS_NO_ACTIVE_PERSON_OR_PERSON_CONSENT",
        },
        "audit_memory": {
            "audit_event_count": 0,
            "event_log_is_person_memory": False,
            "person_memory_writes": 0,
            "completion_memory_claimed": False,
        },
        "person_integration": {
            "active_person_ids": [],
            "exact_subject_bound_adult_evidence": {},
            "person_decision_integrated": False,
            "person_action_authorized": False,
            "runtime_activation": False,
        },
        "truth_boundary": {
            "actor_fixtures_are_people": False,
            "fixture_response_is_person_consent": False,
            "fixture_coordination_is_external_action": False,
            "audit_log_is_person_memory": False,
            "private_content_exists": False,
            "relationship_state_exists": False,
            "person_active": False,
        },
    }
    validate_person_world_state(state)
    return state


def can_fixture_access(state: Mapping[str, Any], actor_fixture_id: str) -> bool:
    current = validate_person_world_state(state)
    actor = require_identifier(actor_fixture_id, "actor_fixture_id")
    if actor not in current["actor_fixture_ids"]:
        return False
    return _fixture_access_without_validation(current, actor)


def _fixture_access_without_validation(
    state: Mapping[str, Any], actor_fixture_id: str
) -> bool:
    privacy = state["privacy"]
    actor = str(actor_fixture_id)
    if actor in privacy["denied_actor_fixture_ids"]:
        return False
    if privacy["state"] == "open":
        return True
    return actor in privacy["allowed_actor_fixture_ids"]


def _require_actor(state: Mapping[str, Any], value: Any) -> str:
    actor = require_identifier(value, "actor_fixture_id")
    if actor not in state["actor_fixture_ids"]:
        raise LevelABoundaryError("unknown neutral actor fixture")
    return actor


def _apply_privacy(state: dict[str, Any], action: str, payload: Mapping[str, Any]) -> None:
    privacy = state["privacy"]
    if payload.get("fixture_control_signal") is not True:
        raise LevelABoundaryError("privacy transitions require fixture_control_signal=true")
    if action == "lock_context":
        if privacy["state"] != "open":
            raise LevelATransitionError("privacy context is already restricted")
        context_id = require_identifier(payload.get("context_id"), "context_id")
        allowed = [_require_actor(state, value) for value in payload.get("allowed_actor_fixture_ids", [])]
        if not allowed or len(allowed) != len(set(allowed)):
            raise LevelARuntimeError("locked context requires unique allowed fixtures")
        privacy.update(
            {
                "context_id": context_id,
                "state": "locked",
                "allowed_actor_fixture_ids": allowed,
                "denied_actor_fixture_ids": [],
                "pending_entry_requests": [],
            }
        )
        return
    if action == "request_entry":
        if privacy["state"] != "locked":
            raise LevelATransitionError("entry request requires a locked context")
        actor = _require_actor(state, payload.get("actor_fixture_id"))
        if actor in privacy["allowed_actor_fixture_ids"]:
            raise LevelATransitionError("fixture already has access")
        if actor not in privacy["pending_entry_requests"]:
            privacy["pending_entry_requests"].append(actor)
        return
    if action in {"grant_entry", "deny_entry"}:
        actor = _require_actor(state, payload.get("actor_fixture_id"))
        if actor not in privacy["pending_entry_requests"]:
            raise LevelATransitionError("no pending entry request")
        privacy["pending_entry_requests"].remove(actor)
        if action == "grant_entry":
            if actor not in privacy["allowed_actor_fixture_ids"]:
                privacy["allowed_actor_fixture_ids"].append(actor)
            if actor in privacy["denied_actor_fixture_ids"]:
                privacy["denied_actor_fixture_ids"].remove(actor)
        else:
            if actor not in privacy["denied_actor_fixture_ids"]:
                privacy["denied_actor_fixture_ids"].append(actor)
        return
    if action == "unlock_context":
        if privacy["state"] != "locked":
            raise LevelATransitionError("privacy context is not locked")
        privacy.update(
            {
                "context_id": None,
                "state": "open",
                "allowed_actor_fixture_ids": [],
                "denied_actor_fixture_ids": [],
                "pending_entry_requests": [],
            }
        )
        return
    raise LevelATransitionError(f"unsupported privacy action: {action}")


def _apply_coordination(state: dict[str, Any], action: str, payload: Mapping[str, Any]) -> None:
    coordination = state["coordination"]
    if payload.get("fixture_control_signal") is not True:
        raise LevelABoundaryError("coordination transitions require fixture_control_signal=true")
    if action == "propose":
        if coordination["state"] not in {"none", "recovered"}:
            raise LevelATransitionError("current proposal must stop and recover before replacement")
        participants = [_require_actor(state, value) for value in payload.get("participant_fixture_ids", [])]
        if len(participants) < 2 or len(participants) != len(set(participants)):
            raise LevelARuntimeError("proposal requires at least two unique fixture participants")
        coordination.update(
            {
                "proposal_id": require_identifier(payload.get("proposal_id"), "proposal_id"),
                "activity_id": require_identifier(payload.get("activity_id"), "activity_id"),
                "context_id": require_identifier(payload.get("context_id"), "context_id"),
                "participant_fixture_ids": participants,
                "fixture_responses": {},
                "state": "proposed",
                "fixture_coordination_gate_satisfied": False,
                "current_person_consent_claimed": False,
                "prior_response_reusable": False,
            }
        )
        return
    if action == "respond":
        if coordination["state"] not in {"proposed", "responses_pending"}:
            raise LevelATransitionError("proposal is not accepting responses")
        actor = _require_actor(state, payload.get("actor_fixture_id"))
        if actor not in coordination["participant_fixture_ids"]:
            raise LevelABoundaryError("fixture response came from a nonparticipant")
        response = str(payload.get("response") or "")
        if response not in RESPONSES:
            raise LevelARuntimeError("fixture response must be yes, no, or uncertain")
        coordination["fixture_responses"][actor] = response
        coordination["state"] = "responses_pending"
        coordination["fixture_coordination_gate_satisfied"] = False
        return
    if action == "evaluate":
        if coordination["state"] not in {"proposed", "responses_pending"}:
            raise LevelATransitionError("proposal cannot be evaluated")
        participants = coordination["participant_fixture_ids"]
        responses = coordination["fixture_responses"]
        exact_all_yes = set(responses) == set(participants) and all(
            responses[value] == "yes" for value in participants
        )
        exact_context = state["privacy"]["context_id"] == coordination["context_id"]
        privacy_allows = all(
            _fixture_access_without_validation(state, value) for value in participants
        )
        coordination["fixture_coordination_gate_satisfied"] = bool(
            exact_all_yes and exact_context and privacy_allows
        )
        coordination["state"] = (
            "fixture_gate_satisfied"
            if coordination["fixture_coordination_gate_satisfied"]
            else "fixture_gate_blocked"
        )
        state["action"]["external_action_authorized"] = False
        state["action"]["external_action_performed"] = False
        return
    if action in {"stop", "interrupt"}:
        actor = _require_actor(state, payload.get("actor_fixture_id"))
        if actor not in coordination["participant_fixture_ids"]:
            raise LevelABoundaryError("only an exact fixture participant can stop")
        if coordination["state"] in {"none", "stopped", "interrupted", "recovered"}:
            raise LevelATransitionError("coordination is not active")
        coordination["state"] = "stopped" if action == "stop" else "interrupted"
        coordination["fixture_coordination_gate_satisfied"] = False
        state["action"]["external_action_authorized"] = False
        return
    if action == "recover":
        if coordination["state"] not in {"stopped", "interrupted", "fixture_gate_blocked"}:
            raise LevelATransitionError("coordination cannot recover from its current state")
        coordination["state"] = "recovered"
        coordination["fixture_coordination_gate_satisfied"] = False
        coordination["prior_response_reusable"] = False
        return
    raise LevelATransitionError(f"unsupported coordination action: {action}")


def apply_person_world_event(
    state: Mapping[str, Any], event: Mapping[str, Any]
) -> dict[str, Any]:
    current = validate_person_world_state(state)
    normalized = validate_event(
        event,
        allowed_domains=DOMAINS,
        prior_event_ids=set(current["seen_event_ids"]),
        current_clock_utc=current["clock_utc"],
    )
    updated = deepcopy(current)
    domain = normalized["domain"]
    action = normalized["action"]
    payload = normalized["payload"]
    if domain == "privacy":
        _apply_privacy(updated, action, payload)
    elif domain == "coordination":
        _apply_coordination(updated, action, payload)
    elif domain == "action":
        raise LevelABoundaryError(
            "Level A cannot authorize or perform an external person action"
        )
    elif domain == "audit_memory":
        raise LevelABoundaryError(
            "Level-A audit events cannot be written as person memory"
        )
    append_event_receipt(updated, normalized)
    updated["audit_memory"]["audit_event_count"] = len(updated["event_log"])
    validate_person_world_state(updated)
    return updated


def validate_person_world_state(state: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        raise LevelARuntimeError("person/world fixture state must be an object")
    if state.get("schema_version") != 1 or state.get("model_id") != MODEL_ID:
        raise LevelARuntimeError("person/world fixture identity drifted")
    if state.get("fixture_kind") != FIXTURE_KIND:
        raise LevelABoundaryError("person/world state is not a Level-A fixture")
    require_identifier(state.get("fixture_id"), "fixture_id")
    actors = state.get("actor_fixture_ids")
    if not isinstance(actors, list) or len(actors) < 2 or len(actors) != len(set(actors)):
        raise LevelARuntimeError("neutral actor fixture inventory drifted")
    for actor in actors:
        require_identifier(actor, "actor_fixture_id")
    if tuple(state.get("capability_ladder", ())) != CAPABILITY_LADDER:
        raise LevelABoundaryError("capability ladder drifted")
    for key, value in dict(state.get("capability_statuses", {})).items():
        assert_level_a_capability_status(value, f"capability_statuses.{key}")
    parse_utc(state.get("clock_utc"), "clock_utc")
    validate_event_ledger(state)
    log = state["event_log"]

    privacy = state.get("privacy", {})
    if privacy.get("state") not in PRIVACY_STATES:
        raise LevelATransitionError("privacy state drifted")
    allowed_list = privacy.get("allowed_actor_fixture_ids", [])
    denied_list = privacy.get("denied_actor_fixture_ids", [])
    pending_list = privacy.get("pending_entry_requests", [])
    if not all(isinstance(value, list) for value in (allowed_list, denied_list, pending_list)):
        raise LevelARuntimeError("privacy fixture access lists must be lists")
    if any(len(value) != len(set(value)) for value in (allowed_list, denied_list, pending_list)):
        raise LevelATransitionError("privacy fixture access lists contain duplicates")
    allowed = set(allowed_list)
    denied = set(denied_list)
    pending = set(pending_list)
    if not allowed.issubset(set(actors)) or not denied.issubset(set(actors)) or allowed & denied:
        raise LevelABoundaryError("privacy fixture access lists drifted")
    if not pending.issubset(set(actors)) or pending.intersection(allowed):
        raise LevelABoundaryError("privacy pending-entry list drifted")
    if privacy["state"] == "open":
        if privacy.get("context_id") is not None or allowed or denied or pending:
            raise LevelATransitionError("open privacy context retained restricted state")
    else:
        require_identifier(privacy.get("context_id"), "privacy.context_id")
        if not allowed:
            raise LevelATransitionError("locked context has no allowed fixture")
    if (
        privacy.get("content_storage_enabled") is not False
        or privacy.get("private_content_stored") is not False
        or privacy.get("person_privacy_claimed") is not False
    ):
        raise LevelABoundaryError("Level-A privacy fixture acquired person content")

    coordination = state.get("coordination", {})
    participants = coordination.get("participant_fixture_ids", [])
    if not isinstance(participants, list) or len(participants) != len(set(participants)):
        raise LevelATransitionError("coordination participants are invalid")
    if not set(participants).issubset(set(actors)):
        raise LevelABoundaryError("coordination participants drifted")
    responses = coordination.get("fixture_responses", {})
    if not isinstance(responses, Mapping):
        raise LevelARuntimeError("fixture responses must be an object")
    if not set(responses).issubset(set(participants)):
        raise LevelABoundaryError("coordination response subject drifted")
    if any(value not in RESPONSES for value in responses.values()):
        raise LevelATransitionError("fixture response value drifted")
    coordination_state = coordination.get("state")
    if coordination_state not in COORDINATION_STATES:
        raise LevelATransitionError("coordination lifecycle state drifted")
    if coordination_state == "none":
        if any(
            coordination.get(key) is not None
            for key in ("proposal_id", "activity_id", "context_id")
        ) or participants or responses:
            raise LevelATransitionError("empty coordination state retained proposal data")
    else:
        for key in ("proposal_id", "activity_id", "context_id"):
            require_identifier(coordination.get(key), f"coordination.{key}")
        if len(participants) < 2:
            raise LevelATransitionError("active coordination requires two fixtures")
    if coordination.get("current_person_consent_claimed") is not False:
        raise LevelABoundaryError("fixture response was relabeled as person consent")
    if coordination.get("prior_response_reusable") is not False:
        raise LevelABoundaryError("prior fixture response became a reusable decision")
    gate = coordination.get("fixture_coordination_gate_satisfied")
    if not isinstance(gate, bool):
        raise LevelATransitionError("fixture coordination gate must be boolean")
    if gate is True and coordination_state != "fixture_gate_satisfied":
        raise LevelATransitionError("fixture coordination gate state drifted")
    if coordination_state == "fixture_gate_satisfied":
        exact_all_yes = set(responses) == set(participants) and all(
            responses[value] == "yes" for value in participants
        )
        exact_context = privacy.get("context_id") == coordination.get("context_id")
        access = all(
            _fixture_access_without_validation(state, value) for value in participants
        )
        if not gate or not exact_all_yes or not exact_context or not access:
            raise LevelATransitionError("fixture coordination gate invariant failed")

    action_state = state.get("action", {})
    if (
        action_state.get("external_action_authorized") is not False
        or action_state.get("external_action_performed") is not False
    ):
        raise LevelABoundaryError("Level A authorized or performed an external action")
    memory = state.get("audit_memory", {})
    if (
        memory.get("audit_event_count") != len(log)
        or memory.get("event_log_is_person_memory") is not False
        or memory.get("person_memory_writes") != 0
        or memory.get("completion_memory_claimed") is not False
    ):
        raise LevelABoundaryError("audit ledger became person memory")
    integration = state.get("person_integration", {})
    if (
        integration.get("active_person_ids") != []
        or integration.get("exact_subject_bound_adult_evidence") != {}
        or any(
            integration.get(key) is not False
            for key in (
                "person_decision_integrated",
                "person_action_authorized",
                "runtime_activation",
            )
        )
    ):
        raise LevelABoundaryError("Level A crossed the exact-adult/person integration gate")
    truth = state.get("truth_boundary")
    if not isinstance(truth, Mapping) or any(value is not False for value in truth.values()):
        raise LevelABoundaryError("person/world fixture crossed a false claim")
    return deepcopy(dict(state))


def person_world_state_sha256(state: Mapping[str, Any]) -> str:
    return canonical_sha256(validate_person_world_state(state))


def serialize_person_world_state(state: Mapping[str, Any]) -> str:
    return canonical_json(validate_person_world_state(state))


def restore_person_world_state(serialized: str) -> dict[str, Any]:
    try:
        raw = json.loads(serialized)
    except (TypeError, json.JSONDecodeError) as exc:
        raise LevelARuntimeError("serialized person/world state is invalid JSON") from exc
    return validate_person_world_state(raw)
