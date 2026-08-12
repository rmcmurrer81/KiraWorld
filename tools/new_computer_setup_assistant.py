"""
New computer setup assistant for Kira/Lisa first local-model launch.

This tool is safe to run before any model is installed. By default it only
checks the machine and prints the exact next actions. With --download-model it
will ask Ollama to pull the configured first model.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QWEN_MODEL = "qwen3.5:9b"
QWEN_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"


def load_json(relative_path: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))


def get_default_model() -> str:
    data = load_json("config/model_runtime.json")
    model = str(data.get("ollama", {}).get("default_model", QWEN_MODEL)).strip()
    digest = str(data.get("ollama", {}).get("default_digest", "")).strip().casefold()
    if model != QWEN_MODEL or digest != QWEN_DIGEST:
        raise RuntimeError("model_runtime.json does not pin the exact approved Qwen 3.5 identity")
    return model


def check_python() -> tuple[bool, str]:
    version = sys.version_info
    ok = version.major == 3 and version.minor >= 10
    return ok, f"Python {version.major}.{version.minor}.{version.micro}"


def check_project_files() -> tuple[bool, str]:
    required = [
        "chat_kira.py",
        "Core/conversation_loop.py",
        "tools/readiness_check.py",
        "tools/desktop_model_readiness.py",
        "config/model_runtime.json",
        "config/system_flags.json",
        "Data/launch/kira_first_talk_context.json",
        "Data/launch/lisa_first_talk_context.json",
    ]
    missing = [path for path in required if not (PROJECT_ROOT / path).exists()]
    if missing:
        return False, "missing: " + ", ".join(missing)
    return True, "required launch files exist"


def check_disk_space() -> tuple[bool, str]:
    usage = shutil.disk_usage(PROJECT_ROOT)
    free_gb = usage.free / (1024**3)
    ok = free_gb >= 30
    detail = f"{free_gb:.1f} GB free on project drive"
    if not ok:
        detail += " (model download may be tight; 30+ GB recommended for first setup)"
    return ok, detail


def check_ollama_installed() -> tuple[bool, str]:
    path = shutil.which("ollama")
    if not path:
        return False, "ollama command not found"
    return True, path


def run_command(args: list[str]) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            args,
            cwd=str(PROJECT_ROOT),
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
    except FileNotFoundError:
        return False, f"{args[0]} not found"
    except subprocess.TimeoutExpired:
        return False, "command timed out: " + " ".join(args)
    output = (completed.stdout + completed.stderr).strip()
    if completed.returncode != 0:
        return False, output or f"exit code {completed.returncode}"
    return True, output or "ok"


def check_ollama_version() -> tuple[bool, str]:
    installed, detail = check_ollama_installed()
    if not installed:
        return False, detail
    return run_command(["ollama", "--version"])


def check_model_installed(model_name: str) -> tuple[bool, str]:
    installed, detail = check_ollama_installed()
    if not installed:
        return False, detail
    ok, output = run_command(["ollama", "list"])
    if not ok:
        return False, output
    if model_name.lower() in output.lower():
        return True, f"{model_name} is installed"
    return False, f"{model_name} is not installed yet"


def download_model(model_name: str) -> tuple[bool, str]:
    installed, detail = check_ollama_installed()
    if not installed:
        return False, detail
    try:
        completed = subprocess.run(
            ["ollama", "pull", model_name],
            cwd=str(PROJECT_ROOT),
            text=True,
            timeout=60 * 60,
            check=False,
        )
    except FileNotFoundError:
        return False, "ollama command not found"
    except subprocess.TimeoutExpired:
        return False, "model download timed out"
    if completed.returncode != 0:
        return False, f"ollama pull exited with {completed.returncode}"
    return True, f"{model_name} downloaded"


def build_report(model_name: str) -> list[tuple[str, bool, str]]:
    return [
        ("Python", *check_python()),
        ("Project files", *check_project_files()),
        ("Disk space", *check_disk_space()),
        ("Ollama installed", *check_ollama_version()),
        ("Configured model", *check_model_installed(model_name)),
    ]


def print_report(report: list[tuple[str, bool, str]], model_name: str) -> None:
    print("Kira new computer setup assistant")
    print("=" * 34)
    for name, ok, detail in report:
        marker = "PASS" if ok else "WARN" if name in {"Disk space", "Configured model"} else "FAIL"
        print(f"[{marker}] {name}: {detail}")

    print("\nNext actions")
    print("1. Run: py tools\\readiness_check.py")
    print("2. Run: py tools\\desktop_model_readiness.py")
    print(f"3. If Ollama is installed but the model is missing, run: py tools\\new_computer_setup_assistant.py --download-model --model {model_name}")
    print(f"4. For first Kira local-model test, set KIRA_MODEL_BACKEND=ollama and KIRA_MODEL_NAME={model_name}")
    print("5. Keep voice/avatar/webcam/world/temp_ai disabled until Kira text is stable.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a new desktop for Kira/Lisa local-model bring-up.")
    parser.add_argument("--model", default=get_default_model(), help="Ollama model name to check or download.")
    parser.add_argument("--download-model", action="store_true", help="Run ollama pull for the selected model.")
    args = parser.parse_args()

    model_name = str(args.model).strip()
    if args.download_model:
        ok, detail = download_model(model_name)
        marker = "PASS" if ok else "FAIL"
        print(f"[{marker}] Model download: {detail}")
        if not ok:
            raise SystemExit(1)

    report = build_report(model_name)
    print_report(report, model_name)

    failed_required = [name for name, ok, _detail in report if not ok and name not in {"Disk space", "Configured model"}]
    if failed_required:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
