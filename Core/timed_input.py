"""
Small Windows-friendly timed input helper.

PowerShell stdin does not provide a simple cross-platform input timeout. This
helper uses msvcrt on Windows so chat runners can do lightweight idle-life work
while waiting for Robert.
"""

from __future__ import annotations

import sys
import time


def timed_input(prompt: str, timeout_seconds: float | None = None) -> tuple[str | None, bool]:
    """Return (text, timed_out). None means no complete line arrived in time."""
    if timeout_seconds is None or timeout_seconds <= 0 or sys.platform != "win32":
        try:
            return input(prompt), False
        except (EOFError, KeyboardInterrupt):
            raise

    import msvcrt

    print(prompt, end="", flush=True)
    chars: list[str] = []
    deadline = time.monotonic() + timeout_seconds
    while True:
        if not msvcrt.kbhit():
            if not chars and time.monotonic() >= deadline:
                print()
                return None, True
            time.sleep(0.05)
            continue
        char = msvcrt.getwch()
        if char in ("\r", "\n"):
            print()
            return "".join(chars), False
        if char == "\003":
            raise KeyboardInterrupt
        if char == "\b":
            if chars:
                chars.pop()
                print("\b \b", end="", flush=True)
            continue
        chars.append(char)
        print(char, end="", flush=True)
