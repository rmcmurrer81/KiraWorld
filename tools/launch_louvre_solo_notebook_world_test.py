#!/usr/bin/env python3
"""Start the pinned Louvre solo server, verify it, then open its review URL.

The browser URL is only opened after the loopback server answers the dedicated
health endpoint with the expected service and build identity.  This process
does not import or start Home World, TemporaryAI, voice, Ollama, or TARDIS.
"""

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
SERVER = ROOT / "tools" / "serve_louvre_solo_notebook_world_test.py"
LOG_DIR = ROOT / "Logs" / "louvre_solo_review"
DEFAULT_PORT = 5183
LOOPBACK_HOST = "127.0.0.1"
EXPECTED_SERVICE = "louvre_solo_owner_review"
EXPECTED_PROTOCOL = "louvre_bounded_circulation_owner_review_r4"
EXPECTED_BUILD_ID = "louvre_owner_review_20260716_r4_bounded_circulation"
REVIEW_PATH = "/?solo=1&bookmark=arrival_scale"


class LaunchError(RuntimeError):
    """Raised when the exact local review service cannot be made healthy."""


def health_url(port: int) -> str:
    return f"http://{LOOPBACK_HOST}:{port}/healthz"


def review_url(port: int) -> str:
    return f"http://{LOOPBACK_HOST}:{port}{REVIEW_PATH}"


def read_health(port: int, *, timeout: float = 0.75) -> dict[str, Any] | None:
    request = urllib.request.Request(
        health_url(port),
        headers={"Accept": "application/json", "User-Agent": "Kira-Louvre-Solo-Launcher/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None
            content_type = response.headers.get_content_type()
            if content_type != "application/json":
                return None
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, ValueError, json.JSONDecodeError, urllib.error.URLError):
        return None
    if not isinstance(payload, dict):
        return None
    if (
        payload.get("service") != EXPECTED_SERVICE
        or payload.get("protocol") != EXPECTED_PROTOCOL
        or payload.get("build_id") != EXPECTED_BUILD_ID
        or payload.get("ready") is not True
    ):
        return None
    isolation = payload.get("isolation") or {}
    if isolation.get("solo_review_only") is not True:
        return None
    if int(isolation.get("people_loaded", -1)) != 0 or int(isolation.get("minds_loaded", -1)) != 0:
        return None
    if isolation.get("bounded_approximate_circulation_owner_review_enabled") is not True:
        return None
    for name in ("full_louvre_interior_enabled", "elevators_enabled", "gallery_enabled", "artwork_enabled"):
        if isolation.get(name) is not False:
            return None
    return payload


def wait_for_health(
    port: int,
    *,
    process: subprocess.Popen[bytes] | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        health = read_health(port)
        if health is not None:
            return health
        if process is not None and process.poll() is not None:
            raise LaunchError(f"The Louvre server exited before becoming healthy (exit {process.returncode}).")
        time.sleep(0.15)
    raise LaunchError(
        f"The Louvre server did not become healthy at {health_url(port)} within {timeout_seconds:.1f} seconds."
    )


def start_detached_server(port: int) -> tuple[subprocess.Popen[bytes], Path, Path]:
    if not SERVER.is_file():
        raise LaunchError(f"Server script is missing: {SERVER}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stdout_path = LOG_DIR / f"louvre_solo_{port}.out.log"
    stderr_path = LOG_DIR / f"louvre_solo_{port}.err.log"
    stdout_handle = stdout_path.open("ab", buffering=0)
    stderr_handle = stderr_path.open("ab", buffering=0)
    creationflags = 0
    popen_kwargs: dict[str, Any] = {}
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                "-u",
                str(SERVER),
                "--port",
                str(port),
                "--no-open",
            ],
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            creationflags=creationflags,
            **popen_kwargs,
        )
    except OSError as exc:
        raise LaunchError(f"Could not start the Louvre server: {exc}") from exc
    finally:
        stdout_handle.close()
        stderr_handle.close()
    return process, stdout_path, stderr_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--no-open", action="store_true", help="Verify startup without opening a browser")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not (1 <= args.port <= 65535):
        print(f"Louvre launch FAILED: invalid port {args.port}.", file=sys.stderr)
        return 2
    if not (1.0 <= args.timeout <= 60.0):
        print("Louvre launch FAILED: --timeout must be from 1 to 60 seconds.", file=sys.stderr)
        return 2

    existing = read_health(args.port)
    if existing is not None:
        url = review_url(args.port)
        print(f"The exact Louvre solo review server is already healthy: {existing.get('build_id')}.")
        if not args.no_open and not webbrowser.open(url):
            print(f"Browser auto-open was unavailable. Open this URL manually: {url}")
        else:
            print(f"Opened {url}" if not args.no_open else f"Verified {url}")
        return 0

    process: subprocess.Popen[bytes] | None = None
    stdout_path: Path | None = None
    stderr_path: Path | None = None
    try:
        process, stdout_path, stderr_path = start_detached_server(args.port)
        health = wait_for_health(args.port, process=process, timeout_seconds=args.timeout)
    except LaunchError as exc:
        print(f"Louvre launch FAILED: {exc}", file=sys.stderr)
        if stdout_path and stderr_path:
            print(f"Server logs: {stdout_path} and {stderr_path}", file=sys.stderr)
        print(
            f"Nothing was opened. Port {args.port} may already belong to a different program, "
            "or the pinned Louvre files may have failed verification.",
            file=sys.stderr,
        )
        return 1

    url = review_url(args.port)
    print(
        "Louvre solo review is healthy "
        f"({health.get('build_id')}; people=0; minds=0). Server PID: {process.pid if process else 'existing'}."
    )
    if not args.no_open and not webbrowser.open(url):
        print(f"Browser auto-open was unavailable. Open this URL manually: {url}")
    else:
        print(f"Opened {url}" if not args.no_open else f"Verified {url}")
    print("The local review server remains available until that background Python process is stopped or Windows restarts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
