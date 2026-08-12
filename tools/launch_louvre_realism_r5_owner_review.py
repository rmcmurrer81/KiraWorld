#!/usr/bin/env python3
"""Health-check and open the pinned Louvre R5 solo owner-review service."""

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
SERVER = ROOT / "tools" / "serve_louvre_realism_r5_owner_review.py"
LOG_DIR = ROOT / "Logs" / "louvre_realism_r5_review"
DEFAULT_PORT = 5195
EXPECTED_SERVICE = "louvre_realism_solo_owner_review"
EXPECTED_PROTOCOL = "louvre_real_model_context_owner_review_r5"
EXPECTED_BUILD_ID = "louvre_realism_owner_review_20260716_r5"


def health(port: int) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=.75) as response:
            payload = json.loads(response.read().decode())
    except (OSError, ValueError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("service") != EXPECTED_SERVICE:
        return None
    if payload.get("protocol") != EXPECTED_PROTOCOL or payload.get("build_id") != EXPECTED_BUILD_ID or payload.get("ready") is not True:
        return None
    isolation = payload.get("isolation") or {}
    if isolation.get("solo_review_only") is not True or int(isolation.get("people_loaded", -1)) != 0 or int(isolation.get("minds_loaded", -1)) != 0:
        return None
    for name in ("full_louvre_interior_enabled", "working_elevator_enabled", "gallery_inventory_enabled", "artwork_inventory_enabled"):
        if isolation.get(name) is not False:
            return None
    return payload


def start_server(port: int) -> tuple[subprocess.Popen[bytes], Path, Path]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stdout_path = LOG_DIR / f"r5_{port}.out.log"
    stderr_path = LOG_DIR / f"r5_{port}.err.log"
    out = stdout_path.open("ab", buffering=0)
    err = stderr_path.open("ab", buffering=0)
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
    return process, stdout_path, stderr_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        print(f"Louvre R5 launch FAILED: invalid port {args.port}", file=sys.stderr)
        return 2
    current = health(args.port)
    if current is None:
        try:
            process, stdout_path, stderr_path = start_server(args.port)
        except OSError as exc:
            print(f"Louvre R5 launch FAILED: {exc}", file=sys.stderr)
            return 1
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            current = health(args.port)
            if current is not None:
                break
            if process.poll() is not None:
                print(f"Louvre R5 server exited {process.returncode}. Logs: {stdout_path} / {stderr_path}", file=sys.stderr)
                return 1
            time.sleep(.15)
        if current is None:
            print(f"Louvre R5 did not become healthy. Port may be occupied. Logs: {stdout_path} / {stderr_path}", file=sys.stderr)
            return 1
    url = f"http://127.0.0.1:{args.port}/?solo=1&bookmark=arrival"
    print(f"Verified pinned Louvre R5: people=0, minds=0, full interior=false. {url}")
    if not args.no_open:
        webbrowser.open(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
