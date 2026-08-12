from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = "http://127.0.0.1:8767/"
ICON_PATH = ROOT / "Assets" / "icons" / "kira_world_shell_icon.ico"


def message_box(text: str, title: str = "Kira World Shell", flags: int = 0) -> int:
    return ctypes.windll.user32.MessageBoxW(None, text, title, flags)


def launcher_context() -> tuple[str, str, int]:
    token = str(os.environ.get("KIRA_SHELL_API_TOKEN") or "").strip()
    launch_id = str(os.environ.get("KIRA_SHELL_LAUNCH_ID") or "").strip().lower()
    raw_pid = str(os.environ.get("KIRA_SHELL_CHILD_PID") or "0").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token):
        raise ValueError("KIRA_SHELL_API_TOKEN is missing or invalid")
    if not re.fullmatch(r"[0-9a-f]{32}", launch_id):
        raise ValueError("KIRA_SHELL_LAUNCH_ID is missing or invalid")
    if not raw_pid.isdigit():
        raise ValueError("KIRA_SHELL_CHILD_PID is invalid")
    return token, launch_id, int(raw_pid)


def api_json(url: str, path: str, body: dict | None = None, timeout: float = 5.0) -> dict:
    token, _, _ = launcher_context()
    endpoint = url.rstrip("/") + path
    data = None
    headers = {
        "accept": "application/json",
        "X-Kira-Shell-Token": token,
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["content-type"] = "application/json"
    request = urllib.request.Request(endpoint, data=data, headers=headers, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_shell(url: str, timeout: float) -> bool:
    _, launch_id, owned_pid = launcher_context()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            state = api_json(url, "/api/state", timeout=1.5)
            if (
                state.get("shell_launch_id") == launch_id
                and (not owned_pid or int(state.get("shell_pid") or 0) == owned_pid)
            ):
                return True
            time.sleep(0.4)
        except Exception:
            time.sleep(0.4)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Native Kira World Shell viewer.")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--wait", type=float, default=20.0)
    parser.add_argument("--title", default="Kira World Shell")
    args = parser.parse_args()

    if not wait_for_shell(args.url, args.wait):
        message_box(
            "The Kira World Shell server did not become ready. Start_Kira_World_Shell.bat should start it first.",
            flags=0x10,
        )
        return 2

    try:
        import webview
    except Exception as exc:
        message_box(f"The native Kira viewer dependency is missing or broken:\n\n{exc}", flags=0x10)
        return 3

    close_allowed = {"value": False}

    def on_closing() -> bool:
        if close_allowed["value"]:
            return True
        try:
            state = api_json(args.url, "/api/state", timeout=2.0)
            active_label = state.get("active_label") or state.get("active_candidate") or ""
            if active_label:
                answer = message_box(
                    f"{active_label} is active.\n\nClose Kira World Shell safely and pause the active AI first?",
                    flags=0x31,
                )
                if answer != 1:
                    return False
            api_json(args.url, "/api/safe-close", {"reason": "Robert closed the native Kira viewer"}, timeout=6.0)
            close_allowed["value"] = True
            return True
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            answer = message_box(
                f"The shell did not confirm a safe close:\n\n{exc}\n\nClose the viewer anyway?",
                flags=0x31,
            )
            return answer == 1
        except Exception as exc:
            message_box(f"Safe close failed:\n\n{exc}", flags=0x10)
            return False

    window = webview.create_window(
        args.title,
        args.url,
        width=1400,
        height=860,
        min_size=(1000, 640),
        maximized=True,
        background_color="#07111c",
        confirm_close=False,
        text_select=False,
    )
    if window is None:
        return 4
    window.events.closing += on_closing
    webview.start(private_mode=False, storage_path=str(ROOT / "Data" / "runtime" / "kira_shell_webview"), icon=str(ICON_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
