"""
Validate attention event JSON files.

Attention events are lightweight source/attention decisions. They are not
trusted memories, consent records, or relationship-stage upgrades.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "event_id",
    "owner",
    "timestamp",
    "attention_state",
    "source_label",
    "source_confidence",
    "category_guess",
    "other_person_present",
    "relationship_context",
    "privacy_context",
    "recommended_action",
    "memory_policy",
    "status",
}

VALID_OWNERS = {"kira", "lisa", "kira_lisa", "system"}
VALID_ATTENTION_STATES = {
    "focused_on_user",
    "idle_nearby",
    "reading_or_researching",
    "private_reflection",
    "private_conversation",
    "locked_private_space",
    "upset_unavailable",
}
VALID_SOURCE_LABELS = {
    "robert_direct_speech",
    "robert_phone_media",
    "bedroom_computer_media",
    "living_room_tv_media",
    "visitor_voice",
    "other_ai_voice",
    "unknown_source",
}
VALID_CONFIDENCE = {"low", "medium", "high"}
VALID_CATEGORY_GUESSES = {
    "direct_request",
    "music",
    "video_dialogue",
    "show_or_movie",
    "adult_or_private_media",
    "game_audio",
    "unknown_media",
}
VALID_ACTIONS = {
    "respond_normally",
    "ask_soft_clarifying_question",
    "stay_quiet_give_privacy",
    "look_away",
    "ignore_as_background_media",
    "doorbell_request_required",
    "private_reflection_only",
    "reserve_response_due_to_other_person",
    "log_metadata_only",
}
VALID_STATUS = {"draft", "observed", "processed", "archived"}


def validate_attention_event(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if data.get("owner") not in VALID_OWNERS:
        errors.append(f"owner must be one of: {', '.join(sorted(VALID_OWNERS))}")
    if data.get("attention_state") not in VALID_ATTENTION_STATES:
        errors.append(f"attention_state must be one of: {', '.join(sorted(VALID_ATTENTION_STATES))}")
    if data.get("source_label") not in VALID_SOURCE_LABELS:
        errors.append(f"source_label must be one of: {', '.join(sorted(VALID_SOURCE_LABELS))}")
    if data.get("source_confidence") not in VALID_CONFIDENCE:
        errors.append(f"source_confidence must be one of: {', '.join(sorted(VALID_CONFIDENCE))}")
    if data.get("category_guess") not in VALID_CATEGORY_GUESSES:
        errors.append(f"category_guess must be one of: {', '.join(sorted(VALID_CATEGORY_GUESSES))}")
    if data.get("recommended_action") not in VALID_ACTIONS:
        errors.append(f"recommended_action must be one of: {', '.join(sorted(VALID_ACTIONS))}")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")

    if not str(data.get("event_id", "")).strip():
        errors.append("event_id is required.")
    if not isinstance(data.get("other_person_present"), bool):
        errors.append("other_person_present must be a boolean.")

    relationship_context = data.get("relationship_context")
    if not isinstance(relationship_context, dict):
        errors.append("relationship_context must be an object.")
    else:
        for key in ("relationship_id", "relationship_stage", "unspoken_feeling_possible", "mutual_intimate_context_established"):
            if key not in relationship_context:
                errors.append(f"relationship_context.{key} is required.")
        for key in ("unspoken_feeling_possible", "mutual_intimate_context_established"):
            if key in relationship_context and not isinstance(relationship_context.get(key), bool):
                errors.append(f"relationship_context.{key} must be a boolean.")

    privacy_context = data.get("privacy_context")
    if not isinstance(privacy_context, dict):
        errors.append("privacy_context must be an object.")
    else:
        for key in ("sensitive_or_private", "teasing_allowed", "should_disclose_to_other_ai", "door_or_room_privacy_required"):
            if key not in privacy_context:
                errors.append(f"privacy_context.{key} is required.")
            elif not isinstance(privacy_context.get(key), bool):
                errors.append(f"privacy_context.{key} must be a boolean.")

    memory_policy = data.get("memory_policy")
    if not isinstance(memory_policy, dict):
        errors.append("memory_policy must be an object.")
    else:
        required_true = {
            "attention_event_is_not_trusted_memory",
            "does_not_create_consent",
            "does_not_upgrade_relationship_stage",
            "owner_controls_private_reflection",
        }
        for key in sorted(required_true):
            if memory_policy.get(key) is not True:
                errors.append(f"memory_policy.{key} must be true.")
        if memory_policy.get("store_exact_private_content") is not False:
            errors.append("memory_policy.store_exact_private_content must be false.")

    linked_private_records = data.get("linked_private_records")
    if linked_private_records is not None and not isinstance(linked_private_records, list):
        errors.append("linked_private_records must be a list when present.")

    if data.get("category_guess") == "adult_or_private_media":
        if data.get("recommended_action") in {"respond_normally", "ask_soft_clarifying_question"}:
            errors.append("adult_or_private_media should not default to ordinary response or questions.")
        if isinstance(privacy_context, dict) and privacy_context.get("sensitive_or_private") is not True:
            errors.append("adult_or_private_media requires privacy_context.sensitive_or_private true.")
        if isinstance(memory_policy, dict) and memory_policy.get("store_exact_private_content") is not False:
            errors.append("adult_or_private_media must not store exact private content.")

    if data.get("other_person_present") is True:
        if data.get("recommended_action") not in {"reserve_response_due_to_other_person", "ask_soft_clarifying_question", "ignore_as_background_media"}:
            errors.append("events with another person present should use reserved or neutral actions.")
        if isinstance(privacy_context, dict) and privacy_context.get("teasing_allowed") is True:
            errors.append("teasing_allowed must be false when another person is present.")

    if isinstance(relationship_context, dict) and relationship_context.get("unspoken_feeling_possible") is True:
        if data.get("recommended_action") == "respond_normally" and data.get("category_guess") == "adult_or_private_media":
            errors.append("unspoken private-media reactions should not respond normally.")
        if isinstance(privacy_context, dict) and privacy_context.get("should_disclose_to_other_ai") is True:
            errors.append("unspoken feelings should not disclose to the other AI by default.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an attention event JSON file.")
    parser.add_argument("path", help="Path to attention event JSON.")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_attention_event(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
