"""
New desktop activation checker for Kira, Lisa, and first TemporaryAI dry run.

This tool does not activate models or TemporaryAIs. It validates the activation
checklist, confirms important files exist, and prints the ordered launch runway.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_new_desktop_activation_checklist import validate_new_desktop_activation_checklist


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKLIST = PROJECT_ROOT / "Data" / "launch" / "new_desktop_activation_checklist.json"

REQUIRED_FILES = [
    "System/Docs/NEW_DESKTOP_ACTIVATION_SEQUENCE_v1.md",
    "System/Docs/NEW_COMPUTER_CODEX_SETUP_RUNBOOK_v1.md",
    "System/Docs/FIRST_LIVE_MODEL_DAY_RUNBOOK_v1.md",
    "System/Docs/DAY_ONE_CONVERSATION_GROUNDING_CHECKLIST_v1.md",
    "Data/launch/kira_first_talk_context.json",
    "Data/launch/lisa_first_talk_context.json",
    "Data/launch/first_live_model_day_checklist.json",
    "Data/launch/first_month_operations_checklist.json",
    "Data/reading/reading_interest_profiles.json",
    "Data/reading/reactions/reading_reaction_template.json",
    "tools/new_computer_setup_assistant.py",
    "tools/desktop_model_readiness.py",
    "tools/readiness_check.py",
    "tools/daily_life.py",
    "tools/recommend_reading.py",
    "tools/plan_temp_ai_request.py",
    "tools/build_backup_manifest.py",
    "chat_kira.py",
    "chat_lisa.py",
]


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_checklist(path: Path = DEFAULT_CHECKLIST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def required_file_report() -> list[dict[str, Any]]:
    report = []
    for relative in REQUIRED_FILES:
        path = PROJECT_ROOT / relative
        report.append({"path": relative, "exists": path.exists()})
    return report


def build_activation_report(checklist_path: Path = DEFAULT_CHECKLIST) -> dict[str, Any]:
    checklist = load_checklist(checklist_path)
    validation_errors = validate_new_desktop_activation_checklist(checklist)
    files = required_file_report()
    missing_files = [item["path"] for item in files if not item["exists"]]
    blocked = bool(validation_errors or missing_files)
    return {
        "checklist_path": _relative(checklist_path),
        "checklist_id": checklist.get("checklist_id"),
        "status": checklist.get("status"),
        "blocked": blocked,
        "validation_errors": validation_errors,
        "missing_files": missing_files,
        "stage_count": len(checklist.get("activation_sequence", [])) if isinstance(checklist.get("activation_sequence"), list) else 0,
        "stages": [
            {
                "stage": stage.get("stage"),
                "stage_id": stage.get("stage_id"),
                "goal": stage.get("goal"),
                "required_commands": stage.get("required_commands", []),
                "required_success": stage.get("required_success", []),
            }
            for stage in checklist.get("activation_sequence", [])
            if isinstance(stage, dict)
        ],
        "first_commands": [
            "py tools\\new_computer_setup_assistant.py",
            "py tools\\readiness_check.py",
            "py tools\\desktop_model_readiness.py",
            "py tools\\build_backup_manifest.py",
        ],
        "stage_rule": checklist.get("stage_rule", {}),
    }


def print_report(report: dict[str, Any], show_stages: bool) -> None:
    print("Kira new desktop activation check")
    print("=" * 33)
    print(f"Checklist: {report['checklist_path']}")
    print(f"Status: {report.get('status')}")
    print(f"Blocked: {report['blocked']}")

    if report["validation_errors"]:
        print("\nValidation errors:")
        for error in report["validation_errors"]:
            print(f"- {error}")
    if report["missing_files"]:
        print("\nMissing files:")
        for path in report["missing_files"]:
            print(f"- {path}")

    print("\nFirst commands:")
    for command in report["first_commands"]:
        print(f"- {command}")

    if show_stages:
        print("\nActivation stages:")
        for stage in report["stages"]:
            print(f"{stage['stage']}. {stage['stage_id']}: {stage['goal']}")
            for command in stage["required_commands"]:
                print(f"   - {command}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the new desktop activation runway.")
    parser.add_argument("--checklist", default=str(DEFAULT_CHECKLIST))
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--show-stages", action="store_true", help="Print ordered stages and commands.")
    args = parser.parse_args()

    checklist_path = Path(args.checklist)
    if not checklist_path.is_absolute():
        checklist_path = PROJECT_ROOT / checklist_path

    report = build_activation_report(checklist_path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report, args.show_stages)
    if report["blocked"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
