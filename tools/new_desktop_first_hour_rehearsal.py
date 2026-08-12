"""
Print and validate Robert's first-hour new desktop activation rehearsal.

This does not activate Kira, Lisa, a model, or a TemporaryAI. It validates the
checklist and prints the safest command order for the first desktop session.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_new_desktop_first_hour_rehearsal import validate_new_desktop_first_hour_rehearsal


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REHEARSAL = PROJECT_ROOT / "Data" / "launch" / "new_desktop_first_hour_rehearsal.json"

REQUIRED_FILES = [
    "System/Docs/NEW_DESKTOP_FIRST_HOUR_REHEARSAL_v1.md",
    "System/Docs/NEW_DESKTOP_ACTIVATION_SEQUENCE_v1.md",
    "System/Docs/FIRST_LIVE_MODEL_DAY_RUNBOOK_v1.md",
    "Data/launch/new_desktop_first_hour_rehearsal.json",
    "Data/launch/new_desktop_activation_checklist.json",
    "tools/first_live_conversation_smoke.py",
    "tools/new_desktop_activation_check.py",
    "tools/new_computer_setup_assistant.py",
    "tools/desktop_model_readiness.py",
    "tools/build_backup_manifest.py",
    "tools/startup_recovery_check.py",
    "tools/validate_temp_ai_simple_request.py",
    "tools/plan_temp_ai_request.py",
    "Data/temporary_ai_requests/examples/robotics_humanoid_hardware_expert_request.example.json",
    "Data/temporary_ai_requests/examples/kira_mother_memory_relative_request.example.json",
    "chat_kira.py",
    "chat_lisa.py",
]


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_rehearsal(path: Path = DEFAULT_REHEARSAL) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def required_file_report() -> list[dict[str, Any]]:
    report = []
    for relative in REQUIRED_FILES:
        path = PROJECT_ROOT / relative
        report.append({"path": relative, "exists": path.exists()})
    return report


def build_rehearsal_report(path: Path = DEFAULT_REHEARSAL) -> dict[str, Any]:
    data = load_rehearsal(path)
    validation_errors = validate_new_desktop_first_hour_rehearsal(data)
    file_report = required_file_report()
    missing_files = [item["path"] for item in file_report if not item["exists"]]
    blocked = bool(validation_errors or missing_files)
    return {
        "rehearsal_path": _relative(path),
        "rehearsal_id": data.get("rehearsal_id"),
        "status": data.get("status"),
        "blocked": blocked,
        "validation_errors": validation_errors,
        "missing_files": missing_files,
        "required_preflight_commands": data.get("required_preflight_commands", []),
        "stub_smoke_commands": data.get("stub_smoke_commands", []),
        "first_model_commands": data.get("first_model_commands", []),
        "temporary_ai_dry_run_commands": data.get("temporary_ai_dry_run_commands", []),
        "blocked_first_hour_actions": data.get("blocked_first_hour_actions", []),
        "success_definition": data.get("success_definition", []),
    }


def _print_list(title: str, values: list[Any]) -> None:
    print(f"\n{title}:")
    for value in values:
        print(f"- {value}")


def print_report(report: dict[str, Any], show_commands: bool) -> None:
    print("Kira new desktop first-hour rehearsal")
    print("=" * 39)
    print(f"Checklist: {report['rehearsal_path']}")
    print(f"Status: {report.get('status')}")
    print(f"Blocked: {report['blocked']}")

    if report["validation_errors"]:
        _print_list("Validation errors", report["validation_errors"])
    if report["missing_files"]:
        _print_list("Missing files", report["missing_files"])

    if show_commands:
        _print_list("Preflight commands", report["required_preflight_commands"])
        _print_list("Stub smoke commands", report["stub_smoke_commands"])
        _print_list("First model commands", report["first_model_commands"])
        _print_list("TemporaryAI dry-run commands", report["temporary_ai_dry_run_commands"])

    _print_list("Blocked first-hour actions", report["blocked_first_hour_actions"])
    _print_list("Success definition", report["success_definition"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the first-hour new desktop rehearsal.")
    parser.add_argument("--rehearsal", default=str(DEFAULT_REHEARSAL))
    parser.add_argument("--show-commands", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    path = Path(args.rehearsal)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    report = build_rehearsal_report(path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report, args.show_commands)
    if report["blocked"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
