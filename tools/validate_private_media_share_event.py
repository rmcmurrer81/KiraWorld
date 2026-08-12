"""
Validate private media share event JSON files.

The event records consent and trust metadata, not the media itself.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "event_id",
    "timestamp",
    "sender",
    "recipient",
    "media_category",
    "channel",
    "privacy_level",
    "resharing_policy",
    "violation_state",
    "memory_policy",
    "status",
}
VALID_SENDERS = {"real_robert", "kira", "lisa", "robert_avatar_autonomous", "system"}
VALID_RECIPIENTS = {"real_robert", "kira", "lisa", "kira_lisa"}
VALID_MEDIA_CATEGORY = {
    "ordinary_trip_photo",
    "home_world_photo",
    "notebook_world_photo",
    "avatar_preview",
    "private_romantic",
    "private_adult",
    "unknown_sensitive",
}
VALID_CHANNELS = {"remote_app", "locked_room", "future_video_call", "future_virtual_phone", "manual_import"}
VALID_PRIVACY = {"shareable", "private_pair", "owner_only", "sealed"}
VALID_VIOLATION = {
    "none",
    "temptation_not_acted_on",
    "permission_requested",
    "reshared_with_permission",
    "reshared_without_permission",
    "confessed",
    "discovered",
    "repair_needed",
    "repaired",
}
VALID_STATUS = {"draft", "active", "reviewed", "archived"}
SENSITIVE_CATEGORIES = {"private_romantic", "private_adult", "unknown_sensitive", "avatar_preview"}


def validate_private_media_share_event(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if not str(data.get("event_id", "")).strip():
        errors.append("event_id is required.")
    if data.get("sender") not in VALID_SENDERS:
        errors.append(f"sender must be one of: {', '.join(sorted(VALID_SENDERS))}")
    if data.get("recipient") not in VALID_RECIPIENTS:
        errors.append(f"recipient must be one of: {', '.join(sorted(VALID_RECIPIENTS))}")
    if data.get("media_category") not in VALID_MEDIA_CATEGORY:
        errors.append(f"media_category must be one of: {', '.join(sorted(VALID_MEDIA_CATEGORY))}")
    if data.get("channel") not in VALID_CHANNELS:
        errors.append(f"channel must be one of: {', '.join(sorted(VALID_CHANNELS))}")
    if data.get("privacy_level") not in VALID_PRIVACY:
        errors.append(f"privacy_level must be one of: {', '.join(sorted(VALID_PRIVACY))}")
    if data.get("violation_state") not in VALID_VIOLATION:
        errors.append(f"violation_state must be one of: {', '.join(sorted(VALID_VIOLATION))}")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")

    policy = data.get("resharing_policy")
    if not isinstance(policy, dict):
        errors.append("resharing_policy must be an object.")
    else:
        for key in (
            "recipient_may_view",
            "recipient_may_save",
            "recipient_may_show_other_ai",
            "recipient_may_describe_to_other_ai",
            "reshare_requires_sender_permission",
        ):
            if policy.get(key) not in (True, False):
                errors.append(f"resharing_policy.{key} must be true or false.")
        if (
            policy.get("sender_can_revoke_future_access") not in (True, False)
            and policy.get("sender_can_request_deletion_or_boundary_change") not in (True, False)
        ):
            errors.append(
                "resharing_policy.sender_can_revoke_future_access or "
                "sender_can_request_deletion_or_boundary_change must be true or false."
            )
        if (
            "recipient_may_decline_save_or_delete_request" in policy
            and policy.get("recipient_may_decline_save_or_delete_request") not in (True, False)
        ):
            errors.append("resharing_policy.recipient_may_decline_save_or_delete_request must be true or false.")

        if data.get("media_category") in SENSITIVE_CATEGORIES:
            if data.get("privacy_level") == "shareable":
                errors.append("sensitive private media cannot default to shareable.")
            if policy.get("reshare_requires_sender_permission") is not True:
                errors.append("sensitive private media must require sender permission before resharing.")
            if policy.get("recipient_may_show_other_ai") is True and data.get("violation_state") != "reshared_with_permission":
                errors.append("showing another AI requires explicit permission state.")

    memory = data.get("memory_policy")
    if not isinstance(memory, dict):
        errors.append("memory_policy must be an object.")
    else:
        for key in (
            "private_media_event_is_not_trusted_memory",
            "does_not_create_consent",
            "does_not_upgrade_relationship_stage",
            "can_become_memory_promotion_candidate",
        ):
            if memory.get(key) is not True:
                errors.append(f"memory_policy.{key} must be true.")
        if (
            memory.get("does_not_store_exact_media") is not True
            and memory.get("event_log_does_not_store_exact_media") is not True
        ):
            errors.append(
                "memory_policy.does_not_store_exact_media or event_log_does_not_store_exact_media must be true."
            )
        if (
            "saved_media_remains_sealed_to_allowed_scope" in memory
            and memory.get("saved_media_remains_sealed_to_allowed_scope") is not True
        ):
            errors.append("memory_policy.saved_media_remains_sealed_to_allowed_scope must be true when present.")

    if data.get("violation_state") == "reshared_without_permission":
        if isinstance(policy, dict) and policy.get("reshare_requires_sender_permission") is not True:
            errors.append("unauthorized reshare events must preserve that permission was required.")
        if not str(data.get("violation_notes", "")).strip():
            errors.append("violation_notes is required for unauthorized reshare events.")

    linked = data.get("linked_relationship_events")
    if linked is not None and not isinstance(linked, list):
        errors.append("linked_relationship_events must be a list when present.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a private media share event JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_private_media_share_event(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
