#!/usr/bin/env python3
"""Start, health-check, and optionally open the pinned Louvre R7 review."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "tools" / "serve_louvre_corrected_r7_owner_review.py"
LOG_DIR = ROOT / "Logs" / "louvre_corrected_r7_review"
DEFAULT_PORT = 5197
EXPECTED_BUILD_ID = "notebook_world_louvre_corrected_r7_20260716_235000"
EXPECTED_PROTOCOL = "louvre_corrected_zero_person_owner_review_r7"


def health(port: int) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=0.8) as response:
            result = json.loads(response.read().decode())
    except (OSError, ValueError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
        return None
    if not isinstance(result, dict):
        return None
    if result.get("protocol") != EXPECTED_PROTOCOL or result.get("build_id") != EXPECTED_BUILD_ID:
        return None
    if result.get("ready") is not True:
        return None
    isolation = result.get("runtime_isolation") or {}
    if isolation.get("solo_review_only") is not True:
        return None
    if int(isolation.get("people_loaded", -1)) != 0 or int(isolation.get("minds_loaded", -1)) != 0:
        return None
    for flag in ("person_systems_loaded", "mind_systems_loaded", "voice_systems_loaded", "home_world_loaded", "tardis_loaded"):
        if isolation.get(flag) is not False:
            return None
    return result


def start(port: int) -> tuple[subprocess.Popen[bytes], Path, Path]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = LOG_DIR / f"r7_{port}.out.log"
    err_path = LOG_DIR / f"r7_{port}.err.log"
    out = out_path.open("ab", buffering=0)
    err = err_path.open("ab", buffering=0)
    kwargs: dict[str, Any] = {}
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    try:
        process = subprocess.Popen(
            [sys.executable, "-u", str(SERVER), "--port", str(port), "--no-open"],
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            creationflags=flags,
            **kwargs,
        )
    finally:
        out.close()
        err.close()
    return process, out_path, err_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        print(f"Louvre corrected R7 launch FAILED: invalid port {args.port}", file=sys.stderr)
        return 2
    current = health(args.port)
    if current is None:
        try:
            process, out_path, err_path = start(args.port)
        except OSError as exc:
            print(f"Louvre corrected R7 launch FAILED: {exc}", file=sys.stderr)
            return 1
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            current = health(args.port)
            if current is not None:
                break
            if process.poll() is not None:
                print(f"Louvre R7 server exited {process.returncode}. Logs: {out_path} / {err_path}", file=sys.stderr)
                return 1
            time.sleep(0.15)
        if current is None:
            print(f"Louvre R7 did not become healthy. Logs: {out_path} / {err_path}", file=sys.stderr)
            return 1
    url = f"http://127.0.0.1:{args.port}/?solo=1&bookmark=west_arrival"
    print(f"Verified pinned Louvre R7: people=0, minds=0, rejected scan absent, physical portals locked. {url}")
    if not args.no_open:
        webbrowser.open(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
