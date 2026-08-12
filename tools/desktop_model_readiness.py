"""
Desktop/local-model readiness check for Kira.

This is safe to run before a model is installed. It checks files, environment
settings, disk space, and optionally whether the Ollama endpoint is reachable.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str) -> dict[str, Any]:
    path = PROJECT_ROOT / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


def check_exists(relative_path: str) -> tuple[bool, str]:
    path = PROJECT_ROOT / relative_path
    return path.exists(), relative_path


def check_json(relative_path: str) -> tuple[bool, str]:
    path = PROJECT_ROOT / relative_path
    if not path.exists():
        return False, f"{relative_path} missing"
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"{relative_path} invalid JSON: {exc}"
    return True, f"{relative_path} valid JSON"


def check_disk_space() -> tuple[bool, str]:
    usage = shutil.disk_usage(PROJECT_ROOT)
    free_gb = usage.free / (1024 ** 3)
    ok = free_gb >= 15
    detail = f"{free_gb:.1f} GB free at project drive"
    if not ok:
        detail += " (text/stub ok; local 7B/8B model setup may be tight)"
    return ok, detail


def check_system_flags_text_only() -> tuple[bool, str]:
    data = load_json("config/system_flags.json")
    enabled = [
        key for key in ("voice_enabled", "avatar_enabled", "world_enabled", "temp_ai_enabled")
        if data.get(key) is True
    ]
    if enabled:
        return False, "first local talk should keep disabled: " + ", ".join(enabled)
    return True, "voice/avatar/world/temp_ai disabled for first text talk"


def check_runtime_config() -> tuple[bool, str]:
    data = load_json("config/model_runtime.json")
    required = data.get("desktop_first_talk", {}).get("required_files", [])
    missing = [path for path in required if not (PROJECT_ROOT / path).exists()]
    if missing:
        return False, "missing required runtime files: " + ", ".join(missing)
    return True, "model runtime config required files exist"


def check_first_live_model_day_checklist() -> tuple[bool, str]:
    data = load_json("Data/launch/first_live_model_day_checklist.json")
    disabled = data.get("must_remain_disabled_on_day_one", {})
    enabled = [key for key, value in disabled.items() if value is not False]
    if enabled:
        return False, "day-one checklist has enabled future features: " + ", ".join(enabled)
    if not data.get("kira_grounding_prompts") or not data.get("lisa_grounding_prompts"):
        return False, "day-one checklist must include Kira and Lisa grounding prompts"
    if "grounded" not in str(data.get("memory_promotion_rule", "")).lower():
        return False, "day-one memory promotion rule must require grounded review"
    return True, "first live model day checklist is conservative"


def check_env() -> tuple[bool, str]:
    backend = os.getenv("KIRA_MODEL_BACKEND", "stub").strip().lower()
    model = os.getenv("KIRA_MODEL_NAME", "").strip()
    endpoint = os.getenv("KIRA_OLLAMA_ENDPOINT", "http://localhost:11434/api/chat").strip()

    if backend == "stub":
        return True, "KIRA_MODEL_BACKEND=stub (safe pre-model mode)"
    if backend != "ollama":
        return False, f"unsupported KIRA_MODEL_BACKEND={backend}"
    if not model:
        return False, "KIRA_MODEL_BACKEND=ollama but KIRA_MODEL_NAME is not set"
    return True, f"KIRA_MODEL_BACKEND=ollama, model={model}, endpoint={endpoint}"


def check_ollama_endpoint() -> tuple[bool, str]:
    backend = os.getenv("KIRA_MODEL_BACKEND", "stub").strip().lower()
    if backend != "ollama":
        return True, "Ollama endpoint check skipped in stub mode"

    endpoint = os.getenv("KIRA_OLLAMA_ENDPOINT", "http://localhost:11434/api/chat").strip()
    payload = {
        "model": os.getenv("KIRA_MODEL_NAME", "").strip(),
        "messages": [{"role": "user", "content": "Reply with OK."}],
        "stream": False,
        "options": {"num_predict": 8},
    }
    try:
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = data.get("message", {}).get("content", "").strip()
        if text:
            return True, f"Ollama responded: {text[:80]}"
        return False, "Ollama responded but no message content was returned"
    except urllib.error.URLError as exc:
        return False, f"Ollama endpoint not reachable: {exc}"
    except Exception as exc:
        return False, f"Ollama check failed: {exc}"


def main() -> None:
    checks = [
        ("Runtime config JSON", lambda: check_json("config/model_runtime.json")),
        ("Launch context", lambda: check_exists("System/Prompts/kira_launch_context_v1.md")),
        ("First talk context JSON", lambda: check_json("Data/launch/kira_first_talk_context.json")),
        ("First live model day checklist JSON", lambda: check_json("Data/launch/first_live_model_day_checklist.json")),
        ("Kira memory file", lambda: check_json("Data/memories_kira.json")),
        ("System flags text-only", check_system_flags_text_only),
        ("Runtime required files", check_runtime_config),
        ("First live model day checklist", check_first_live_model_day_checklist),
        ("Disk space", check_disk_space),
        ("Environment", check_env),
        ("Ollama endpoint", check_ollama_endpoint),
    ]

    print("Kira desktop/local-model readiness")
    print("=" * 36)
    failed_required = []
    warnings = []
    for name, check in checks:
        ok, detail = check()
        marker = "PASS" if ok else "WARN" if name == "Disk space" else "FAIL"
        print(f"[{marker}] {name}: {detail}")
        if not ok and name == "Disk space":
            warnings.append(name)
        elif not ok:
            failed_required.append(name)

    if warnings:
        print("\nWarnings do not block stub/text testing, but matter for local models.")
    if failed_required:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
