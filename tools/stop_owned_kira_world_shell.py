"""Stop only the Kira shell process owned by one failed launcher attempt."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import signal
import time
from pathlib import Path


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        synchronize = 0x00100000
        query_limited_information = 0x00001000
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel32.WaitForSingleObject.restype = ctypes.c_ulong
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int
        handle = kernel32.OpenProcess(
            synchronize | query_limited_information,
            False,
            pid,
        )
        if not handle:
            return False
        try:
            wait_timeout = 0x00000102
            return kernel32.WaitForSingleObject(handle, 0) == wait_timeout
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--launch-id", required=True)
    args = parser.parse_args()

    if args.pid <= 0 or args.pid == os.getpid():
        print("Refusing an invalid owned server PID.")
        return 2
    if not 1 <= args.port <= 65535:
        print("Refusing an invalid owned server port.")
        return 2
    if not re.fullmatch(r"[0-9a-f]{32}", args.launch_id):
        print("Refusing an invalid launcher identity.")
        return 2

    runtime = Path(args.runtime)
    if not runtime.is_absolute():
        print("Refusing a non-absolute runtime directory.")
        return 2

    if not pid_alive(args.pid):
        print(f"Owned Kira shell process {args.pid} already exited.")
        return 0

    lock_path = runtime.resolve() / "kira_world_shell.lock"
    try:
        record = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"Refusing to stop a process without its readable exact lock: {exc}")
        return 2

    expected = {
        "pid": args.pid,
        "port": args.port,
        "launch_id": args.launch_id,
    }
    if any(record.get(key) != value for key, value in expected.items()):
        print("Refusing to stop a process whose lock does not match this launch.")
        return 2

    os.kill(args.pid, signal.SIGTERM)
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline and pid_alive(args.pid):
        time.sleep(0.1)
    if pid_alive(args.pid):
        print(f"Owned Kira shell process {args.pid} did not exit cleanly.")
        return 3
    print(f"Stopped only owned Kira shell process {args.pid}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
