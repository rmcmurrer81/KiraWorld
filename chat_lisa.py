"""Laptop-safe Lisa chat runner."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from conversation_loop import ConversationLoop  # noqa: E402
from chat_kira import _idle_step, _print_help, _try_command  # noqa: E402
from idle_rhythm import IdleRhythm  # noqa: E402
from timed_input import timed_input  # noqa: E402
from Core.portable_os_voice import (  # noqa: E402
    cached_candidate_os_voice_route,
    speak_with_os_voice,
)


IDLE_STEP_SECONDS = int(os.getenv("KIRA_IDLE_STEP_SECONDS", "0"))
LISA_OS_VOICE_ENABLED = os.getenv("KIRA_LISA_OS_VOICE", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _idle_rhythm_from_args(idle_step_seconds: int = IDLE_STEP_SECONDS) -> IdleRhythm:
    if idle_step_seconds > 0:
        return IdleRhythm(min_seconds=idle_step_seconds, max_seconds=idle_step_seconds)
    return IdleRhythm()


def lisa_os_voice_route():
    """Select a generic installed female OS voice, never an identity claim."""

    return cached_candidate_os_voice_route(
        "lisa",
        "Lisa",
        "female",
        "",
    )


def lisa_reply_voice_allowed(text: str, turn_audit: object = None) -> tuple[bool, str]:
    """Keep runtime/offline diagnostics out of Lisa's OS voice output."""

    reply = str(text or "").strip()
    if not reply:
        return False, "empty_reply"
    lowered = reply.casefold()
    if lowered.startswith("[lisa - model offline]"):
        return False, "model_offline_diagnostic"
    if lowered.startswith("[lisa - error]"):
        return False, "model_error_diagnostic"
    audit = turn_audit if isinstance(turn_audit, dict) else {}
    model_calls = audit.get("model_calls")
    if isinstance(model_calls, list):
        for call in model_calls:
            if not isinstance(call, dict):
                continue
            if call.get("public_reply_suppressed") is True:
                return False, "model_reply_suppressed"
            if call.get("voice_generation_allowed") is False:
                return False, "model_call_disallows_voice"
    return True, "reply_allowed"


def speak_lisa_reply(
    text: str,
    *,
    enabled: bool = LISA_OS_VOICE_ENABLED,
    turn_audit: object = None,
) -> dict:
    if not enabled:
        return {"spoken": False, "reason": "lisa_os_voice_disabled"}
    allowed, reason = lisa_reply_voice_allowed(text, turn_audit)
    if not allowed:
        return {"spoken": False, "reason": reason}
    route = lisa_os_voice_route()
    if not route.available:
        return {"spoken": False, "reason": route.reason or "os_voice_unavailable"}
    return speak_with_os_voice(text, route)


def run_chat(
    idle_step_seconds: int = IDLE_STEP_SECONDS,
    *,
    voice_enabled: bool = LISA_OS_VOICE_ENABLED,
) -> None:
    loop = ConversationLoop(speaker="Lisa")
    idle_rhythm = _idle_rhythm_from_args(idle_step_seconds)
    print("Lisa text core is running. Type /quit to stop.")
    print("Backend defaults to stub mode unless KIRA_MODEL_BACKEND is set.")
    print("Type /help for live-session commands.")
    print(f"Idle life rhythm: fuzzy {idle_rhythm.min_seconds}-{idle_rhythm.max_seconds} seconds while waiting.")
    if voice_enabled:
        route = lisa_os_voice_route()
        if route.available:
            print(
                f"Voice output: generic installed {route.platform} OS voice "
                f"({route.voice_name}); this is not an authentic or cloned Lisa voice."
            )
        else:
            print(f"Voice output: text only; no supported installed OS voice is available ({route.reason}).")

    while True:
        wait_seconds = idle_rhythm.next_wait_seconds()
        try:
            raw_message, timed_out = timed_input("Robert> ", wait_seconds)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if timed_out:
            _idle_step(loop, reason=idle_rhythm.last_reason)
            continue
        user_message = (raw_message or "").strip()

        if user_message.lower() in {"/quit", "/exit"}:
            break

        if not user_message:
            continue

        if _try_command(loop, user_message):
            continue

        response = loop.process(user_message)
        print(f"Lisa> {response}")
        speak_lisa_reply(
            response,
            enabled=voice_enabled,
            turn_audit=loop.last_turn_audit,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Lisa text chat.")
    parser.add_argument("--idle-step-seconds", type=int, default=IDLE_STEP_SECONDS, help="Testing override. 0 uses fuzzy idle rhythm.")
    voice_group = parser.add_mutually_exclusive_group()
    voice_group.add_argument("--voice-output", dest="voice_output", action="store_true")
    voice_group.add_argument("--no-voice-output", dest="voice_output", action="store_false")
    parser.set_defaults(voice_output=LISA_OS_VOICE_ENABLED)
    args = parser.parse_args()
    run_chat(idle_step_seconds=args.idle_step_seconds, voice_enabled=args.voice_output)
