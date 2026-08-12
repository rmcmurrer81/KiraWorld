"""
Validate memory sharing request JSON files.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "request_id",
    "reconstruction_id",
    "source_memory_id",
    "requested_by",
    "intended_viewer",
    "requested_scope",
    "required_approvals",
    "approval_status",
    "participant_responses",
    "approved_scope",
    "visual_body_exposure_allowed",
    "permanent_replay_access_granted",
    "privacy_rules",
    "status",
}

VALID_SCOPES = {
    "summary",
    "emotional_meaning",
    "verbal_details_only",
    "non_intimate_lead_in",
    "selected_zones",
    "one_time_full_replay",
    "full_replay",
}
VALID_APPROVAL_STATUS = {"draft", "approved", "denied", "partial", "expired"}
VALID_RESPONSE = {"pending", "yes", "no", "not_yet", "summary_only", "verbal_details_only", "selected_zones_only", "one_time_only"}
VALID_APPROVED_SCOPE = {"none", *VALID_SCOPES}
VALID_STATUS = {"draft", "ready_for_review", "approved", "denied", "archived"}
VISUAL_SCOPES = {"selected_zones", "one_time_full_replay", "full_replay"}
SCOPE_RIGHTS = {
    "summary": frozenset({"summary"}),
    "emotional_meaning": frozenset({"summary", "emotional_meaning"}),
    "verbal_details_only": frozenset(
        {"summary", "emotional_meaning", "verbal_selected_details"}
    ),
    "non_intimate_lead_in": frozenset(
        {"summary", "emotional_meaning", "non_intimate_visual"}
    ),
    "selected_zones": frozenset(
        {
            "summary",
            "emotional_meaning",
            "non_intimate_visual",
            "selected_locked_zones",
        }
    ),
    "one_time_full_replay": frozenset(
        {
            "summary",
            "emotional_meaning",
            "non_intimate_visual",
            "selected_locked_zones",
            "full_visual_replay",
        }
    ),
    "full_replay": frozenset(
        {
            "summary",
            "emotional_meaning",
            "non_intimate_visual",
            "selected_locked_zones",
            "full_visual_replay",
        }
    ),
}
RESPONSE_SCOPE = {
    "summary_only": "summary",
    "verbal_details_only": "verbal_details_only",
    "selected_zones_only": "selected_zones",
    "one_time_only": "one_time_full_replay",
}
MAX_APPROVAL_LIFETIME_SECONDS = 900.0


def _expect_object(data: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object.")
        return {}
    return value


def _responses_by_participant(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    responses = data.get("participant_responses", [])
    if not isinstance(responses, list):
        return {}
    result = {}
    for response in responses:
        if isinstance(response, dict) and response.get("participant_id"):
            result[response["participant_id"]] = response
    return result


def _scope_is_subset(approved: str, allowed: str) -> bool:
    if approved == "none":
        return True
    if approved not in SCOPE_RIGHTS or allowed not in SCOPE_RIGHTS:
        return False
    if not SCOPE_RIGHTS[approved] <= SCOPE_RIGHTS[allowed]:
        return False
    # Equal content rights do not permit upgrading one-time access to reusable
    # full replay.
    return not (approved == "full_replay" and allowed == "one_time_full_replay")


def _parse_iso8601(value: Any, field_name: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field_name} is required for an approved request.")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field_name} must be an ISO-8601 timestamp.")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        errors.append(f"{field_name} must include a timezone.")
        return None
    return parsed


def validate_memory_sharing_request(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    for key in ("request_id", "reconstruction_id", "source_memory_id", "requested_by", "intended_viewer"):
        if not data.get(key):
            errors.append(f"{key} is required.")

    if data.get("requested_scope") not in VALID_SCOPES:
        errors.append(f"requested_scope must be one of: {', '.join(sorted(VALID_SCOPES))}")
    if data.get("approved_scope") not in VALID_APPROVED_SCOPE:
        errors.append(f"approved_scope must be one of: {', '.join(sorted(VALID_APPROVED_SCOPE))}")
    if data.get("approval_status") not in VALID_APPROVAL_STATUS:
        errors.append(f"approval_status must be one of: {', '.join(sorted(VALID_APPROVAL_STATUS))}")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")

    required_approvals = data.get("required_approvals", [])
    if not isinstance(required_approvals, list) or not required_approvals:
        errors.append("required_approvals must be a non-empty list.")
        required_ids: list[str] = []
    else:
        required_ids = [
            value for value in required_approvals if isinstance(value, str) and value
        ]
        if len(required_ids) != len(required_approvals):
            errors.append("required_approvals entries must be non-empty strings.")
        if len(required_ids) != len(set(required_ids)):
            errors.append("required_approvals must not contain duplicate participant IDs.")

    responses = data.get("participant_responses", [])
    if not isinstance(responses, list) or not responses:
        errors.append("participant_responses must be a non-empty list.")
    else:
        response_ids = [
            response.get("participant_id")
            for response in responses
            if isinstance(response, dict)
            and isinstance(response.get("participant_id"), str)
            and response.get("participant_id")
        ]
        if len(response_ids) != len(responses):
            errors.append("every participant response requires a non-empty participant_id.")
        if len(response_ids) != len(set(response_ids)):
            errors.append("participant_responses must not contain duplicate participant IDs.")
        seen = _responses_by_participant(data)
        for participant in required_ids:
            if participant not in seen:
                errors.append(f"participant_responses missing required participant: {participant}")
        for participant in sorted(set(response_ids) - set(required_ids)):
            errors.append(f"participant_responses contains unexpected participant: {participant}")
        for response in responses:
            if not isinstance(response, dict):
                errors.append("participant_responses entries must be objects.")
                continue
            if response.get("response") not in VALID_RESPONSE:
                errors.append(f"invalid response for {response.get('participant_id', 'unknown')}: {response.get('response')}")
            if response.get("response") == "no" and not response.get("denial_reason"):
                errors.append(f"no response for {response.get('participant_id', 'unknown')} should include denial_reason.")

    privacy_rules = _expect_object(data, "privacy_rules", errors)
    if privacy_rules:
        if privacy_rules.get("full_replay_blocked_if_any_no") is not True:
            errors.append("privacy_rules.full_replay_blocked_if_any_no must be true.")
        if privacy_rules.get("single_viewing_does_not_grant_replay_access") is not True:
            errors.append("privacy_rules.single_viewing_does_not_grant_replay_access must be true.")
        if privacy_rules.get("visual_body_exposure_requires_explicit_participant_consent") is not True:
            errors.append("privacy_rules.visual_body_exposure_requires_explicit_participant_consent must be true.")
        if privacy_rules.get("verbal_details_only_does_not_grant_visual_replay") is not True:
            errors.append("privacy_rules.verbal_details_only_does_not_grant_visual_replay must be true.")
        if data.get("approved_scope") == "non_intimate_lead_in":
            if privacy_rules.get("non_intimate_lead_in_must_stop_at_locked_boundary") is not True:
                errors.append("privacy_rules.non_intimate_lead_in_must_stop_at_locked_boundary must be true for non_intimate_lead_in.")
            if data.get("stop_at_locked_boundary") is not True:
                errors.append("non_intimate_lead_in must set stop_at_locked_boundary true.")
            if data.get("locked_boundary_behavior") not in {"pause", "fade_to_black", "stop", "locked_door_marker", "switch_to_verbal_summary"}:
                errors.append("non_intimate_lead_in requires a valid locked_boundary_behavior.")

    response_values = [
        response.get("response")
        for response in responses
        if isinstance(response, dict)
    ] if isinstance(responses, list) else []
    any_no = any(value in {"no", "not_yet"} for value in response_values)
    all_yes = bool(response_values) and all(value == "yes" for value in response_values)

    approved_scope = data.get("approved_scope")
    requested_scope = data.get("requested_scope")
    if (
        approved_scope in VALID_APPROVED_SCOPE
        and requested_scope in VALID_SCOPES
        and not _scope_is_subset(approved_scope, requested_scope)
    ):
        errors.append("approved_scope must not exceed requested_scope.")
    if approved_scope in VALID_SCOPES and isinstance(responses, list):
        for response in responses:
            if not isinstance(response, dict):
                continue
            response_value = response.get("response")
            if response_value == "yes":
                maximum_scope = requested_scope
            else:
                maximum_scope = RESPONSE_SCOPE.get(response_value)
            if maximum_scope is not None and not _scope_is_subset(
                approved_scope, maximum_scope
            ):
                errors.append(
                    "approved_scope exceeds the response scope for "
                    f"{response.get('participant_id', 'unknown')}."
                )
    if any_no and approved_scope in {"selected_zones", "one_time_full_replay", "full_replay"}:
        errors.append("visual or full replay cannot be approved when any participant says no or not_yet.")
    if any_no and data.get("approval_status") == "approved":
        errors.append("approval_status cannot be approved when any participant says no or not_yet.")

    if approved_scope == "verbal_details_only" and data.get("visual_body_exposure_allowed") is True:
        errors.append("verbal_details_only must not allow visual body exposure.")
    if approved_scope == "verbal_details_only" and data.get("permanent_replay_access_granted") is True:
        errors.append("verbal_details_only must not grant permanent replay access.")
    if approved_scope == "non_intimate_lead_in" and data.get("visual_body_exposure_allowed") is True:
        errors.append("non_intimate_lead_in must not allow visual body exposure.")
    if approved_scope == "non_intimate_lead_in" and data.get("permanent_replay_access_granted") is True:
        errors.append("non_intimate_lead_in must not grant permanent replay access.")

    if approved_scope in VISUAL_SCOPES and data.get("visual_body_exposure_allowed") is True:
        for response in responses if isinstance(responses, list) else []:
            if isinstance(response, dict) and response.get("visual_body_exposure_allowed") is not True:
                errors.append(f"visual body exposure requires explicit consent from {response.get('participant_id', 'unknown')}.")

    if approved_scope == "one_time_full_replay" and data.get("permanent_replay_access_granted") is True:
        errors.append("one_time_full_replay must not grant permanent replay access.")
    if data.get("permanent_replay_access_granted") is True and approved_scope != "full_replay":
        errors.append("permanent replay access requires approved_scope full_replay.")
    if approved_scope == "full_replay" and not all_yes:
        errors.append("full_replay requires yes from every required participant.")

    if data.get("approval_status") == "approved":
        audit = _expect_object(data, "audit", errors)
        resolved_at = _parse_iso8601(
            audit.get("resolved_at") if audit else None,
            "audit.resolved_at",
            errors,
        )
        expires_at = _parse_iso8601(
            data.get("expires_at") or (audit.get("expires_at") if audit else None),
            "expires_at",
            errors,
        )
        if resolved_at is not None and expires_at is not None:
            lifetime = (expires_at - resolved_at).total_seconds()
            if lifetime <= 0:
                errors.append("expires_at must be after audit.resolved_at.")
            elif lifetime > MAX_APPROVAL_LIFETIME_SECONDS:
                errors.append(
                    "approved request lifetime exceeds the bounded maximum."
                )
        if data.get("revoked_at"):
            errors.append("an approved request cannot remain approved after revocation.")
        if approved_scope == "one_time_full_replay" and data.get("consumed_at"):
            errors.append("a consumed one-time replay cannot remain approved.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a memory sharing request JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_memory_sharing_request(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
