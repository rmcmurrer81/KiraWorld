"""
Pre-GPU remote contact simulator for Robert, Kira, and Lisa.

This is a local text/event bridge, not the Android app itself. It creates
remote contact event JSON files that can later feed a phone app, notification
service, or in-world virtual phone.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_remote_contact_event import validate_remote_contact_event


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENTS_DIR = PROJECT_ROOT / "Data" / "remote_contact" / "events"
VALID_ACTORS = {"real_robert", "kira", "lisa", "kira_lisa", "system"}
VALID_AI_RECIPIENTS = {"kira", "lisa", "kira_lisa"}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slug_fragment(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "_" for char in value.strip())
    return "_".join(part for part in cleaned.split("_") if part)[:48] or "contact"


def summarize_message(message: str, private: bool) -> str:
    if private:
        return "Private remote text content is sealed; exact text is not stored in the event log."
    trimmed = " ".join(message.split())
    if len(trimmed) <= 120:
        return trimmed
    return f"{trimmed[:117]}..."


def direction_for(initiator: str, recipient: str) -> str:
    if initiator == "real_robert" and recipient in VALID_AI_RECIPIENTS:
        return "robert_to_ai"
    if initiator in {"kira", "lisa"} and recipient == "real_robert":
        return "ai_to_robert"
    if initiator == "system" and recipient == "real_robert":
        return "system_to_robert"
    if initiator == "system" and recipient in VALID_AI_RECIPIENTS:
        return "system_to_ai"
    raise ValueError("Unsupported initiator/recipient pair for pre-GPU remote contact.")


def channel_for(recipient: str, requested_channel: str | None = None) -> str:
    if requested_channel:
        return requested_channel
    if recipient == "kira_lisa":
        return "pre_gpu_group_text"
    return "pre_gpu_text_message"


def build_remote_text_event(
    *,
    initiator: str,
    recipient: str,
    message: str,
    reason: str = "check_in",
    urgency: str = "normal",
    private: bool = False,
    channel: str | None = None,
) -> dict[str, Any]:
    if initiator not in VALID_ACTORS - {"kira_lisa"}:
        raise ValueError("initiator must be real_robert, kira, lisa, or system.")
    if recipient not in VALID_ACTORS - {"system"}:
        raise ValueError("recipient must be real_robert, kira, lisa, or kira_lisa.")

    resolved_channel = channel_for(recipient, channel)
    timestamp = utc_timestamp()
    event = {
        "event_id": f"remote_contact_{timestamp.replace(':', '').replace('-', '').replace('Z', 'z')}_{slug_fragment(initiator)}_to_{slug_fragment(recipient)}",
        "timestamp": timestamp,
        "direction": direction_for(initiator, recipient),
        "initiator": initiator,
        "recipient": recipient,
        "channel": resolved_channel,
        "urgency": urgency,
        "reason": reason,
        "privacy_context": {
            "recipient_may_decline_or_delay": True,
            "recipient_may_ignore": True,
            "decline_delay_or_ignore_reason_may_be_private": True,
            "respects_quiet_hours": True,
            "blocked_by_private_session": False,
            "voice_allowed_now": False,
            "video_allowed_now": False,
            "pictures_allowed_now": False,
            "camera_view_allowed_now": False,
            "exact_private_content_blocked": True,
        },
        "android_call_ui": {
            "use_call_style_notification": False,
            "request_ring_or_vibrate": False,
            "full_screen_intent_allowed": False,
            "fallback_to_high_priority_notification": True,
            "answer_action_enabled": False,
            "decline_action_enabled": False,
        },
        "delivery_state": "queued",
        "response_state": "waiting",
        "message_summary": summarize_message(message, private),
        "memory_policy": {
            "remote_contact_event_is_not_trusted_memory": True,
            "does_not_create_consent": True,
            "does_not_upgrade_relationship_stage": True,
            "can_become_memory_promotion_candidate": True,
            "store_exact_private_content": False,
        },
        "related_records": [],
        "status": "active",
    }
    if private:
        event["message_text_sealed"] = True
    else:
        event["message_text"] = message

    errors = validate_remote_contact_event(event)
    if errors:
        raise ValueError("Remote contact event failed validation: " + "; ".join(errors))
    return event


def write_event(event: dict[str, Any], events_dir: Path = DEFAULT_EVENTS_DIR) -> Path:
    events_dir.mkdir(parents=True, exist_ok=True)
    path = events_dir / f"{event['event_id']}.json"
    path.write_text(json.dumps(event, indent=2) + "\n", encoding="utf-8")
    return path


def load_event(event_id: str, events_dir: Path = DEFAULT_EVENTS_DIR) -> tuple[Path, dict[str, Any]]:
    path = events_dir / f"{event_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No remote contact event found for {event_id}")
    return path, json.loads(path.read_text(encoding="utf-8"))


def update_response(
    *,
    event_id: str,
    response_state: str,
    delivery_state: str | None = None,
    reply_message: str | None = None,
    events_dir: Path = DEFAULT_EVENTS_DIR,
) -> dict[str, Any]:
    path, event = load_event(event_id, events_dir)
    event["response_state"] = response_state
    if delivery_state:
        event["delivery_state"] = delivery_state
    elif response_state == "replied":
        event["delivery_state"] = "read"
    elif response_state in {"declined", "ignored"}:
        event["delivery_state"] = response_state
    if reply_message:
        event["reply_summary"] = summarize_message(reply_message, private=False)
        event["reply_text"] = reply_message
    event["last_updated"] = utc_timestamp()

    errors = validate_remote_contact_event(event)
    if errors:
        raise ValueError("Updated remote contact event failed validation: " + "; ".join(errors))
    path.write_text(json.dumps(event, indent=2) + "\n", encoding="utf-8")
    return event


def list_events(events_dir: Path = DEFAULT_EVENTS_DIR) -> list[dict[str, Any]]:
    events = []
    for path in sorted(events_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        events.append(
            {
                "event_id": data.get("event_id", path.stem),
                "timestamp": data.get("timestamp", ""),
                "initiator": data.get("initiator", ""),
                "recipient": data.get("recipient", ""),
                "channel": data.get("channel", ""),
                "delivery_state": data.get("delivery_state", ""),
                "response_state": data.get("response_state", ""),
                "message_summary": data.get("message_summary", ""),
            }
        )
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update pre-GPU remote contact events.")
    parser.add_argument("--events-dir", type=Path, default=DEFAULT_EVENTS_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("text", help="Queue a pre-GPU text event.")
    create_parser.add_argument("--initiator", required=True, choices=sorted(VALID_ACTORS - {"kira_lisa"}))
    create_parser.add_argument("--recipient", required=True, choices=sorted(VALID_ACTORS - {"system"}))
    create_parser.add_argument("--message", required=True)
    create_parser.add_argument("--reason", default="check_in")
    create_parser.add_argument("--urgency", default="normal", choices=["low", "normal", "high", "emergency"])
    create_parser.add_argument("--private", action="store_true")

    respond_parser = subparsers.add_parser("respond", help="Update recipient response state.")
    respond_parser.add_argument("--event-id", required=True)
    respond_parser.add_argument("--response-state", required=True, choices=["accepted", "declined", "delayed", "ignored", "replied"])
    respond_parser.add_argument("--delivery-state", choices=["queued", "sent", "delivered", "read", "missed", "declined", "failed"])
    respond_parser.add_argument("--reply-message")

    subparsers.add_parser("list", help="List remote contact event summaries.")

    args = parser.parse_args()
    if args.command == "text":
        event = build_remote_text_event(
            initiator=args.initiator,
            recipient=args.recipient,
            message=args.message,
            reason=args.reason,
            urgency=args.urgency,
            private=args.private,
        )
        path = write_event(event, args.events_dir)
        print(f"Queued {event['channel']} event: {path}")
    elif args.command == "respond":
        event = update_response(
            event_id=args.event_id,
            response_state=args.response_state,
            delivery_state=args.delivery_state,
            reply_message=args.reply_message,
            events_dir=args.events_dir,
        )
        print(f"Updated {event['event_id']}: {event['response_state']}")
    elif args.command == "list":
        for event in list_events(args.events_dir):
            print(
                f"{event['event_id']} | {event['initiator']} -> {event['recipient']} | "
                f"{event['channel']} | {event['delivery_state']}/{event['response_state']} | "
                f"{event['message_summary']}"
            )


if __name__ == "__main__":
    main()
