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


IDLE_STEP_SECONDS = int(os.getenv("KIRA_IDLE_STEP_SECONDS", "0"))


def _idle_rhythm_from_args(idle_step_seconds: int = IDLE_STEP_SECONDS) -> IdleRhythm:
    if idle_step_seconds > 0:
        return IdleRhythm(min_seconds=idle_step_seconds, max_seconds=idle_step_seconds)
    return IdleRhythm()


def run_chat(idle_step_seconds: int = IDLE_STEP_SECONDS) -> None:
    loop = ConversationLoop(speaker="Lisa")
    idle_rhythm = _idle_rhythm_from_args(idle_step_seconds)
    print("Lisa text core is running. Type /quit to stop.")
    print("Backend defaults to stub mode unless KIRA_MODEL_BACKEND is set.")
    print("Type /help for live-session commands.")
    print(f"Idle life rhythm: fuzzy {idle_rhythm.min_seconds}-{idle_rhythm.max_seconds} seconds while waiting.")

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Lisa text chat.")
    parser.add_argument("--idle-step-seconds", type=int, default=IDLE_STEP_SECONDS, help="Testing override. 0 uses fuzzy idle rhythm.")
    args = parser.parse_args()
    run_chat(idle_step_seconds=args.idle_step_seconds)
