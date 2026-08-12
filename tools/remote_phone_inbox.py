"""
Local pre-GPU phone inbox for Kira/Lisa remote contact events.

This is the human-friendly layer over remote_contact_simulator.py. It gives
Robert a small phone-like text inbox before the Android app exists.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from daily_life_manager import DailyLifeManager  # noqa: E402
from remote_contact_simulator import (
    DEFAULT_EVENTS_DIR,
    build_remote_text_event,
    list_events,
    load_event,
    update_response,
    write_event,
)


STATE_LABELS = {
    "waiting": "waiting",
    "replied": "replied",
    "accepted": "answered",
    "declined": "declined",
    "delayed": "delayed",
    "ignored": "ignored",
    "none": "draft",
}


def compact_actor(actor: str) -> str:
    return {
        "real_robert": "Robert",
        "kira": "Kira",
        "lisa": "Lisa",
        "kira_lisa": "Kira + Lisa",
        "system": "System",
    }.get(actor, actor)


def load_sorted_events(events_dir: Path = DEFAULT_EVENTS_DIR) -> list[dict[str, Any]]:
    events = list_events(events_dir)
    return sorted(events, key=lambda item: item.get("timestamp", ""), reverse=True)


def resolve_event_id(selector: str, events_dir: Path = DEFAULT_EVENTS_DIR) -> str:
    if selector.isdigit():
        index = int(selector) - 1
        events = load_sorted_events(events_dir)
        if index < 0 or index >= len(events):
            raise IndexError(f"Inbox item {selector} does not exist.")
        return str(events[index]["event_id"])
    return selector


def format_inbox_line(event: dict[str, Any], index: int) -> str:
    sender = compact_actor(str(event.get("initiator", "")))
    recipient = compact_actor(str(event.get("recipient", "")))
    state = STATE_LABELS.get(str(event.get("response_state", "")), str(event.get("response_state", "")))
    summary = str(event.get("message_summary", ""))
    return f"{index:>2}. {sender} -> {recipient} [{state}] {summary}"


def render_inbox(events_dir: Path = DEFAULT_EVENTS_DIR) -> str:
    events = load_sorted_events(events_dir)
    if not events:
        return "Kira/Lisa Phone\nNo remote texts yet."
    lines = ["Kira/Lisa Phone", "Inbox"]
    lines.extend(format_inbox_line(event, index) for index, event in enumerate(events, start=1))
    return "\n".join(lines)


def render_event(selector: str, events_dir: Path = DEFAULT_EVENTS_DIR) -> str:
    event_id = resolve_event_id(selector, events_dir)
    _path, event = load_event(event_id, events_dir)
    lines = [
        f"Remote Text: {event.get('event_id', event_id)}",
        f"From: {compact_actor(str(event.get('initiator', '')))}",
        f"To: {compact_actor(str(event.get('recipient', '')))}",
        f"Channel: {event.get('channel', '')}",
        f"State: {event.get('delivery_state', '')}/{event.get('response_state', '')}",
        f"Reason: {event.get('reason', '')}",
        "",
        "Message:",
    ]
    if event.get("message_text_sealed") is True:
        lines.append(str(event.get("message_summary", "Private text is sealed.")))
    else:
        lines.append(str(event.get("message_text", event.get("message_summary", ""))))
    if event.get("reply_text") or event.get("reply_summary"):
        lines.extend(["", "Reply:", str(event.get("reply_text", event.get("reply_summary", "")))])
    return "\n".join(lines)


def send_text(
    *,
    to: str,
    message: str,
    from_actor: str = "real_robert",
    reason: str = "check_in",
    urgency: str = "normal",
    private: bool = False,
    events_dir: Path = DEFAULT_EVENTS_DIR,
    daily_life_manager: DailyLifeManager | None = None,
) -> dict[str, Any]:
    event = build_remote_text_event(
        initiator=from_actor,
        recipient=to,
        message=message,
        reason=reason,
        urgency=urgency,
        private=private,
    )
    if from_actor == "real_robert":
        manager = daily_life_manager or DailyLifeManager()
        recipients = ["kira", "lisa"] if to == "kira_lisa" else [to]
        availability = {
            recipient: manager.phone_availability(recipient)
            for recipient in recipients
            if recipient in {"kira", "lisa"}
        }
        if availability:
            event["recipient_daily_life_availability"] = availability
            recommendations = {item["recommendation"] for item in availability.values()}
            if recommendations <= {"delay_or_ignore", "emergency_only", "delay_unless_urgent"} and urgency != "emergency":
                event["response_state"] = "delayed"
                event["delivery_state"] = "delivered"
            elif "may_decline_or_answer_coldly" in recommendations:
                event["response_state"] = "waiting"
                event["delivery_state"] = "delivered"
    write_event(event, events_dir)
    return event


def set_response(
    *,
    selector: str,
    response_state: str,
    reply_message: str | None = None,
    events_dir: Path = DEFAULT_EVENTS_DIR,
) -> dict[str, Any]:
    event_id = resolve_event_id(selector, events_dir)
    return update_response(
        event_id=event_id,
        response_state=response_state,
        reply_message=reply_message,
        events_dir=events_dir,
    )


def export_inbox_snapshot(
    events_dir: Path = DEFAULT_EVENTS_DIR,
    daily_life_manager: DailyLifeManager | None = None,
) -> dict[str, Any]:
    daily_life = daily_life_manager or DailyLifeManager()
    return {
        "screen": "kira_lisa_phone_inbox",
        "mode": "pre_gpu_text_only",
        "available_buttons": ["Text"],
        "future_buttons": ["Phone", "Video Chat"],
        "daily_life_availability": {
            "kira": daily_life.phone_availability("kira"),
            "lisa": daily_life.phone_availability("lisa"),
        },
        "events": load_sorted_events(events_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Use the local pre-GPU Kira/Lisa phone inbox.")
    parser.add_argument("--events-dir", type=Path, default=DEFAULT_EVENTS_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("inbox", help="Show the phone-style inbox.")

    read_parser = subparsers.add_parser("read", help="Read an event by inbox number or event id.")
    read_parser.add_argument("selector")

    send_parser = subparsers.add_parser("send", help="Send a pre-GPU text.")
    send_parser.add_argument("--to", required=True, choices=["kira", "lisa", "kira_lisa"])
    send_parser.add_argument("--message", required=True)
    send_parser.add_argument("--reason", default="check_in")
    send_parser.add_argument("--urgency", default="normal", choices=["low", "normal", "high", "emergency"])
    send_parser.add_argument("--private", action="store_true")

    reply_parser = subparsers.add_parser("reply", help="Mark an event replied and attach a reply.")
    reply_parser.add_argument("selector")
    reply_parser.add_argument("--message", required=True)

    for command in ("accept", "decline", "delay", "ignore"):
        action_parser = subparsers.add_parser(command, help=f"Mark an event as {command}ed.")
        action_parser.add_argument("selector")

    subparsers.add_parser("snapshot", help="Print a JSON snapshot of the inbox screen model.")

    args = parser.parse_args()
    if args.command == "inbox":
        print(render_inbox(args.events_dir))
    elif args.command == "read":
        print(render_event(args.selector, args.events_dir))
    elif args.command == "send":
        event = send_text(
            to=args.to,
            message=args.message,
            reason=args.reason,
            urgency=args.urgency,
            private=args.private,
            events_dir=args.events_dir,
        )
        print(f"Sent text to {compact_actor(args.to)}: {event['event_id']}")
    elif args.command == "reply":
        event = set_response(
            selector=args.selector,
            response_state="replied",
            reply_message=args.message,
            events_dir=args.events_dir,
        )
        print(f"Replied to {event['event_id']}")
    elif args.command in {"accept", "decline", "delay", "ignore"}:
        response_state = {
            "accept": "accepted",
            "decline": "declined",
            "delay": "delayed",
            "ignore": "ignored",
        }[args.command]
        event = set_response(selector=args.selector, response_state=response_state, events_dir=args.events_dir)
        print(f"Marked {event['event_id']} as {response_state}")
    elif args.command == "snapshot":
        print(json.dumps(export_inbox_snapshot(args.events_dir), indent=2))


if __name__ == "__main__":
    main()
