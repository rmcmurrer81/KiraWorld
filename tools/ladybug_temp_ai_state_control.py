"""Small state-control helper for the Ladybug/Marinette TemporaryAI stub.

This does not run a full TemporaryAI conversation. It prepares and updates the
runtime form state so a later launcher can start as Marinette on first use and
resume the last chosen form afterward.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = PROJECT_ROOT / "TemporaryAI" / "characters" / "ladybug" / "ladybug_form_state_default_v1.json"
POLICY_PATH = PROJECT_ROOT / "TemporaryAI" / "characters" / "ladybug" / "ladybug_form_state_policy_v1.md"
ACTIVATION_CONTEXT = PROJECT_ROOT / "TemporaryAI" / "characters" / "ladybug" / "activation_context" / "ladybug_marinette_canon_source_test_v1.json"
INSTANCE_STATE_PATH = PROJECT_ROOT / "Data" / "temporary_ai_instances" / "ladybug_marinette_canon_source_test.form_state.json"
SESSION_DIR = PROJECT_ROOT / "Data" / "temporary_ai_instances" / "ladybug_sessions"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def initial_state(reset: bool = False) -> dict[str, Any]:
    template = load_json(TEMPLATE_PATH)
    if INSTANCE_STATE_PATH.exists() and not reset:
        return load_json(INSTANCE_STATE_PATH)
    state = dict(template)
    state["status"] = "runtime_state"
    state["created_from_template"] = rel(TEMPLATE_PATH)
    state["created_at"] = utc_now()
    state["updated_at"] = utc_now()
    state["activation_count"] = 0
    state["last_activation_at"] = ""
    state["last_closed_at"] = ""
    state["notes"] = [
        "First activation starts as marinette.",
        "After first activation, resume last_chosen_form unless explicitly reset.",
        "Runtime state is separate from source foundation files.",
    ]
    return state


def save_session_packet(state: dict[str, Any], action: str) -> Path:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    session_id = f"ladybug_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{action}"
    packet = {
        "session_id": session_id,
        "created_at": utc_now(),
        "action": action,
        "state_path": rel(INSTANCE_STATE_PATH),
        "policy_path": rel(POLICY_PATH),
        "activation_context": rel(ACTIVATION_CONTEXT),
        "state_snapshot": state,
        "launcher_note": "This is a pre-conversation state packet, not a transcript and not Kira/Lisa memory.",
    }
    path = SESSION_DIR / f"{session_id}.json"
    write_json(path, packet)
    return path


def cmd_init(args: argparse.Namespace) -> dict[str, Any]:
    state = initial_state(reset=args.reset)
    state["updated_at"] = utc_now()
    write_json(INSTANCE_STATE_PATH, state)
    packet = save_session_packet(state, "init")
    return {"ok": True, "message": "Ladybug/Marinette form state initialized.", "state_path": rel(INSTANCE_STATE_PATH), "packet": rel(packet), "state": state}


def cmd_status(_args: argparse.Namespace) -> dict[str, Any]:
    state = initial_state(reset=False)
    return {"ok": True, "state_path": rel(INSTANCE_STATE_PATH), "state_exists": INSTANCE_STATE_PATH.exists(), "state": state}


def cmd_activate(args: argparse.Namespace) -> dict[str, Any]:
    state = initial_state(reset=args.reset)
    if args.reset:
        state["first_activation_complete"] = False
        state["current_form"] = state.get("first_activation_form", "marinette")
        state["last_chosen_form"] = state["current_form"]
    if not state.get("first_activation_complete"):
        state["current_form"] = state.get("first_activation_form", "marinette")
    else:
        state["current_form"] = state.get("last_chosen_form", "marinette")
    state["first_activation_complete"] = True
    state["activation_count"] = int(state.get("activation_count", 0) or 0) + 1
    state["last_activation_at"] = utc_now()
    state["updated_at"] = utc_now()
    write_json(INSTANCE_STATE_PATH, state)
    packet = save_session_packet(state, "activate")
    return {
        "ok": True,
        "message": f"Prepared Ladybug TemporaryAI state as {state['current_form']}.",
        "state_path": rel(INSTANCE_STATE_PATH),
        "packet": rel(packet),
        "state": state,
    }


def cmd_switch(args: argparse.Namespace) -> dict[str, Any]:
    state = initial_state(reset=False)
    form = args.form.strip().lower()
    if form not in state.get("allowed_forms", []):
        return {"ok": False, "message": f"Unsupported form: {form}", "allowed_forms": state.get("allowed_forms", [])}
    state["current_form"] = form
    state["last_chosen_form"] = form
    state["updated_at"] = utc_now()
    write_json(INSTANCE_STATE_PATH, state)
    packet = save_session_packet(state, f"switch_{form}")
    return {"ok": True, "message": f"Switched current form to {form}.", "state_path": rel(INSTANCE_STATE_PATH), "packet": rel(packet), "state": state}


def cmd_close(_args: argparse.Namespace) -> dict[str, Any]:
    state = initial_state(reset=False)
    state["last_closed_at"] = utc_now()
    state["last_chosen_form"] = state.get("current_form", state.get("last_chosen_form", "marinette"))
    state["updated_at"] = utc_now()
    write_json(INSTANCE_STATE_PATH, state)
    packet = save_session_packet(state, "close")
    return {"ok": True, "message": "Closed Ladybug state cleanly.", "state_path": rel(INSTANCE_STATE_PATH), "packet": rel(packet), "state": state}


def print_result(result: dict[str, Any]) -> None:
    print(result.get("message") or ("OK" if result.get("ok") else "Not OK"))
    state = result.get("state", {})
    if state:
        print(f"Current form: {state.get('current_form')}")
        print(f"Last chosen form: {state.get('last_chosen_form')}")
        print(f"First activation complete: {state.get('first_activation_complete')}")
        print(f"Activation count: {state.get('activation_count', 0)}")
    if result.get("state_path"):
        print(f"State: {result['state_path']}")
    if result.get("packet"):
        print(f"Packet: {result['packet']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Ladybug/Marinette TemporaryAI form state.")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--reset", action="store_true")
    init.set_defaults(func=cmd_init)
    status = sub.add_parser("status")
    status.set_defaults(func=cmd_status)
    activate = sub.add_parser("activate")
    activate.add_argument("--reset", action="store_true")
    activate.set_defaults(func=cmd_activate)
    switch = sub.add_parser("switch")
    switch.add_argument("form", choices=["marinette", "ladybug"])
    switch.set_defaults(func=cmd_switch)
    close = sub.add_parser("close")
    close.set_defaults(func=cmd_close)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = args.func(args)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_result(result)
    if not result.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
