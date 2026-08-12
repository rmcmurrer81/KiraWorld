from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import sys
import time
import urllib.request


def _launcher_value(name: str, pattern: str) -> str:
    value = str(os.environ.get(name) or "").strip()
    if not re.fullmatch(pattern, value):
        raise ValueError(f"{name} is missing or invalid")
    return value


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel32.WaitForSingleObject.restype = ctypes.c_ulong
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int
        handle = kernel32.OpenProcess(0x00101000, False, pid)
        if not handle:
            return False
        try:
            return kernel32.WaitForSingleObject(handle, 0) == 0x00000102
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--owned-pid", type=int, default=0)
    args = parser.parse_args()

    try:
        shell_token = _launcher_value(
            "KIRA_SHELL_API_TOKEN", r"[A-Za-z0-9_-]{32,128}"
        )
        launch_id = _launcher_value("KIRA_SHELL_LAUNCH_ID", r"[0-9a-f]{32}")
    except ValueError as exc:
        print(f"Kira World Shell readiness contract is invalid: {exc}")
        return 2

    endpoint = args.url.rstrip("/") + "/api/state"
    deadline = time.time() + args.timeout
    last_error = ""

    while time.time() < deadline:
        if args.owned_pid and not _pid_alive(args.owned_pid):
            last_error = "owned server process exited before readiness"
            break
        try:
            request = urllib.request.Request(
                endpoint,
                headers={"X-Kira-Shell-Token": shell_token},
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=1.5) as response:
                state = json.loads(response.read().decode("utf-8"))
            matches_owner = (
                isinstance(state, dict)
                and state.get("shell_launch_id") == launch_id
                and (
                    not args.owned_pid
                    or int(state.get("shell_pid") or 0) == args.owned_pid
                )
            )
            if matches_owner and "world_url" in state:
                print(f"Kira World Shell server ready at {args.url}")
                return 0
            last_error = "server answered, but it is not the launcher-owned shell process"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.5)

    print(f"Kira World Shell server did not become ready: {last_error}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
