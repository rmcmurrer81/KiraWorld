from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


os.environ["KIRA_SHELL_TEXT_ONLY"] = "1"
os.environ["KIRA_TEXT_VOICE_CHAT_ACTIVE"] = "1"
os.environ["KIRA_WORLD_SHELL_ACTIVE"] = "0"
os.environ["KIRA_PRE_RAM_KIRA_ONLY"] = "0"
os.environ["KIRA_VOICE_PREWARM_ON_ACTIVATE"] = "0"
os.environ["KIRA_VOICE_BENCHMARK_CAPTURE"] = "0"

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import kira_world_shell_server as shell  # noqa: E402


class CapturingQueue(queue.Queue):
    def __init__(self, capture_path: Path) -> None:
        super().__init__()
        self.capture_path = capture_path
        self.captures: list[dict] = []
        self.capture_lock = threading.Lock()

    def put(self, item, block: bool = True, timeout=None) -> None:
        if isinstance(item, dict) and item.get("_voice_queue_control") != "stop":
            candidate = str(item.get("active") or "")
            label = str(item.get("active_label") or candidate)
            binding = shell.required_reference_voice_binding(candidate, label)
            cfg = binding["config"]
            reference_value = str(getattr(cfg, "chatterbox_reference_audio", "") or "")
            reference = Path(reference_value)
            if reference_value and not reference.is_absolute():
                reference = shell.ROOT / reference
            record = {
                "candidate": candidate,
                "label": label,
                "session_token": int(item.get("session_token") or 0),
                "engine": str(getattr(cfg, "engine", "") or ""),
                "required_reference": bool(binding.get("required")),
                "binding_ready": bool(binding.get("ready")),
                "generic_fallback_blocked": bool(binding.get("required")),
                "reference_audio": reference_value,
                "reference_exists": bool(reference_value and reference.is_file()),
                "reference_sha256": (
                    hashlib.sha256(reference.read_bytes()).hexdigest()
                    if reference_value and reference.is_file()
                    else ""
                ),
                "queued_text_sha256": hashlib.sha256(str(item.get("text") or "").encode("utf-8")).hexdigest(),
                "audio_generated": False,
                "audio_played": False,
            }
            with self.capture_lock:
                self.captures.append(record)
                self.capture_path.write_text(json.dumps(self.captures, indent=2) + "\n", encoding="utf-8")
        super().put(item, block=block, timeout=timeout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    args = parser.parse_args()

    runtime = args.runtime.resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    shell.RUNTIME_DIR = runtime
    shell.STATE_PATH = runtime / "state.json"
    shell.CHAT_LOG = runtime / "chat.jsonl"
    shell.LIFE_LOOP_LOG = runtime / "life_loop.jsonl"
    shell.LOCK_PATH = runtime / "server.lock"
    shell.TEMP_AI_DIR = runtime / "avatar_state"
    shell.TEMP_AI_DIR.mkdir(parents=True, exist_ok=True)
    shell.TEXT_ONLY_CHAT_MODE = True
    shell.PRE_RAM_KIRA_ONLY_MODE = False
    shell.VOICE_PREWARM_ON_ACTIVATE = False
    shell.VOICE_QUEUE_WORKER = None

    sentinel = {
        "owner_test_sentinel": "preserve-me",
        "last_avatar_positions": {
            "kira": {
                "location": "home",
                "position": {"x": 1.25, "y": 0.0, "z": -2.5},
                "updated_at": "2026-07-18T00:00:00Z",
            }
        },
    }
    initial = json.loads(json.dumps(shell.DEFAULT_STATE))
    initial.update(sentinel)
    initial["active_candidate"] = ""
    initial["last_active_candidate"] = ""
    initial["active_conversation_mode"] = ""
    shell.STATE_PATH.write_text(json.dumps(initial, indent=2) + "\n", encoding="utf-8")

    # Reproduce the real regression precondition: mutable state files contain
    # only an internal id and action.  The public selector/chat label must still
    # come from each authored TemporaryAI profile.
    for candidate_id in (
        "elsa_frozen_frozen_fever_frozen_ii_20260716",
        "kathryn_merteuil_kathryn_merteuil_20260605_213017",
    ):
        (shell.TEMP_AI_DIR / f"{candidate_id}.json").write_text(
            json.dumps({"candidate_id": candidate_id, "action": "idle"}, indent=2) + "\n",
            encoding="utf-8",
        )

    capture_queue = CapturingQueue(runtime / "voice_queue_captures.json")
    shell.VOICE_REPLY_QUEUE = capture_queue
    update_calls: list[dict] = []

    def isolated_update_candidate(candidate: str, **kwargs):
        update_calls.append({"candidate": candidate, **kwargs})
        return {"candidate": candidate, **kwargs}

    shell.update_candidate = isolated_update_candidate
    shell.write_avatar_activity_state = lambda *args, **kwargs: None
    shell.temporary_ai_reply = lambda active, active_label, text, location, state: (
        f"This is {active_label}'s isolated launcher and voice-queue reply."
    )
    shell._ensure_voice_queue_worker = lambda: None
    shell.release_voice_output = lambda: {
        "released": False,
        "reason": "isolated_browser_smoke_no_voice_model_loaded",
        "generated_audio": False,
        "playback": False,
    }

    class IsolatedHandler(shell.Handler):
        def do_GET(self) -> None:
            if urlparse(self.path).path == "/__test/audit":
                self._json(200, {
                    "ok": True,
                    "state": shell.load_state(),
                    "voice_session_token": shell.VOICE_SESSION_TOKEN,
                    "voice_worker_started": shell.VOICE_QUEUE_WORKER is not None,
                    "voice_queue_captures": list(capture_queue.captures),
                    "update_calls": list(update_calls),
                    "audio_generated": False,
                    "audio_played": False,
                    "world_processes_started": False,
                })
                return
            super().do_GET()

        def do_POST(self) -> None:
            if urlparse(self.path).path == "/__test/shutdown":
                self._json(200, {"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            super().do_POST()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), IsolatedHandler)
    print(json.dumps({"ready": True, "url": f"http://127.0.0.1:{args.port}/", "runtime": str(runtime)}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
