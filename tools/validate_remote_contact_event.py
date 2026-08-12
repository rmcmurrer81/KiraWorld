"""
Validate remote contact event JSON files.

Remote contact events are text/call/video bridge records. They are not trusted
memories, consent records, relationship upgrades, or proof that voice/video is
currently active.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "event_id",
    "timestamp",
    "direction",
    "initiator",
    "recipient",
    "channel",
    "urgency",
    "reason",
    "privacy_context",
    "delivery_state",
    "response_state",
    "memory_policy",
    "status",
}
VALID_DIRECTION = {"robert_to_ai", "ai_to_robert", "system_to_robert", "system_to_ai"}
VALID_ACTORS = {"real_robert", "kira", "lisa", "kira_lisa", "system"}
VALID_CHANNELS = {
    "pre_gpu_text_message",
    "pre_gpu_group_text",
    "pre_gpu_contact_request",
    "pre_gpu_optional_voice_call",
    "future_voice_call",
    "future_video_call",
    "future_picture_message",
    "future_video_chat_picture_share",
    "future_virtual_phone_call",
}
VALID_URGENCY = {"low", "normal", "high", "emergency"}
VALID_DELIVERY = {"draft", "queued", "ringing", "sent", "delivered", "read", "missed", "declined", "failed"}
VALID_RESPONSE = {"none", "waiting", "accepted", "declined", "delayed", "replied", "ignored"}
VALID_STATUS = {"draft", "active", "processed", "archived"}


def validate_remote_contact_event(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if not str(data.get("event_id", "")).strip():
        errors.append("event_id is required.")
    if data.get("direction") not in VALID_DIRECTION:
        errors.append(f"direction must be one of: {', '.join(sorted(VALID_DIRECTION))}")
    if data.get("initiator") not in VALID_ACTORS - {"kira_lisa"}:
        errors.append("initiator must be real_robert, kira, lisa, or system.")
    if data.get("recipient") not in VALID_ACTORS:
        errors.append(f"recipient must be one of: {', '.join(sorted(VALID_ACTORS))}")
    if data.get("channel") not in VALID_CHANNELS:
        errors.append(f"channel must be one of: {', '.join(sorted(VALID_CHANNELS))}")
    if data.get("urgency") not in VALID_URGENCY:
        errors.append(f"urgency must be one of: {', '.join(sorted(VALID_URGENCY))}")
    if data.get("delivery_state") not in VALID_DELIVERY:
        errors.append(f"delivery_state must be one of: {', '.join(sorted(VALID_DELIVERY))}")
    if data.get("response_state") not in VALID_RESPONSE:
        errors.append(f"response_state must be one of: {', '.join(sorted(VALID_RESPONSE))}")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")

    privacy = data.get("privacy_context")
    if not isinstance(privacy, dict):
        errors.append("privacy_context must be an object.")
    else:
        required_bool = {
            "recipient_may_decline_or_delay",
            "respects_quiet_hours",
            "blocked_by_private_session",
            "voice_allowed_now",
            "video_allowed_now",
            "camera_view_allowed_now",
            "exact_private_content_blocked",
        }
        for key in sorted(required_bool):
            if privacy.get(key) not in (True, False):
                errors.append(f"privacy_context.{key} must be true or false.")
        optional_bool = {
            "recipient_may_ignore",
            "decline_delay_or_ignore_reason_may_be_private",
            "pictures_allowed_now",
        }
        for key in sorted(optional_bool):
            if key in privacy and privacy.get(key) not in (True, False):
                errors.append(f"privacy_context.{key} must be true or false when present.")
        if privacy.get("recipient_may_decline_or_delay") is not True:
            errors.append("privacy_context.recipient_may_decline_or_delay must be true.")
        if privacy.get("exact_private_content_blocked") is not True:
            errors.append("privacy_context.exact_private_content_blocked must be true.")
        if "recipient_may_ignore" in privacy and privacy.get("recipient_may_ignore") is not True:
            errors.append("privacy_context.recipient_may_ignore must be true when present.")
        if "decline_delay_or_ignore_reason_may_be_private" in privacy and privacy.get("decline_delay_or_ignore_reason_may_be_private") is not True:
            errors.append("privacy_context.decline_delay_or_ignore_reason_may_be_private must be true when present.")

    memory = data.get("memory_policy")
    if not isinstance(memory, dict):
        errors.append("memory_policy must be an object.")
    else:
        for key in (
            "remote_contact_event_is_not_trusted_memory",
            "does_not_create_consent",
            "does_not_upgrade_relationship_stage",
            "can_become_memory_promotion_candidate",
        ):
            if memory.get(key) is not True:
                errors.append(f"memory_policy.{key} must be true.")
        if memory.get("store_exact_private_content") is not False:
            errors.append("memory_policy.store_exact_private_content must be false.")

    if data.get("channel", "").startswith("future_") and isinstance(privacy, dict):
        if privacy.get("voice_allowed_now") is True or privacy.get("video_allowed_now") is True or privacy.get("camera_view_allowed_now") is True:
            errors.append("future call channels must not claim voice/video/camera is allowed now.")

    if data.get("urgency") == "emergency" and data.get("channel") != "pre_gpu_contact_request":
        errors.append("pre-GPU emergency should be logged as a contact request, not an automatic call.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a remote contact event JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_remote_contact_event(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
