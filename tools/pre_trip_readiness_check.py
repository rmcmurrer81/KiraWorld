"""
Pre-trip readiness check for Robert's CPU/RAM pickup and return-home setup.

This does not verify hardware compatibility online. It validates the local
trip checklist, confirms the activation runway files exist, and prints the
first commands to run before leaving and after assembly.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_pre_trip_desktop_pickup_checklist import validate_pre_trip_desktop_pickup_checklist


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKLIST = PROJECT_ROOT / "Data" / "launch" / "pre_trip_desktop_pickup_checklist.json"

REQUIRED_FILES = [
    "HANDOFF_FOR_NEXT_CODEX_SESSION.md",
    "DESKTOP_UPGRADE_HANDOFF.md",
    "System/Docs/PRE_TRIP_DESKTOP_PICKUP_AND_RETURN_RUNBOOK_v1.md",
    "System/Docs/NEW_DESKTOP_ACTIVATION_SEQUENCE_v1.md",
    "Data/launch/pre_trip_desktop_pickup_checklist.json",
    "Data/launch/new_desktop_activation_checklist.json",
    "tools/pre_trip_readiness_check.py",
    "tools/new_desktop_activation_check.py",
    "tools/readiness_check.py",
    "tools/build_backup_manifest.py",
    "config/model_runtime.json",
    "config/system_flags.json",
]


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _system_flags_safe() -> tuple[bool, list[str]]:
    path = PROJECT_ROOT / "config" / "system_flags.json"
    if not path.exists():
        return False, ["config/system_flags.json missing"]
    data = _load_json(path)
    enabled = [key for key in ("voice_enabled", "avatar_enabled", "world_enabled", "temp_ai_enabled") if data.get(key) is True]
    return not enabled, enabled


def build_pre_trip_report(checklist_path: Path = DEFAULT_CHECKLIST) -> dict[str, Any]:
    checklist = _load_json(checklist_path)
    validation_errors = validate_pre_trip_desktop_pickup_checklist(checklist)
    missing_files = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).exists()]
    flags_safe, enabled_flags = _system_flags_safe()
    blocked = bool(validation_errors or missing_files or not flags_safe)
    return {
        "checklist_path": _relative(checklist_path),
        "checklist_id": checklist.get("checklist_id"),
        "status": checklist.get("status"),
        "blocked": blocked,
        "validation_errors": validation_errors,
        "missing_files": missing_files,
        "system_flags_safe": flags_safe,
        "enabled_pre_gpu_flags": enabled_flags,
        "before_leaving_commands": checklist.get("before_leaving", {}).get("required_commands", []),
        "first_hour_after_assembly_commands": checklist.get("first_hour_after_assembly", {}).get("commands", []),
        "hardware_pickup": checklist.get("hardware_pickup", {}),
        "do_not_do_yet": checklist.get("do_not_do_yet", []),
    }


def print_report(report: dict[str, Any], show_checklist: bool) -> None:
    print("Kira pre-trip desktop pickup readiness")
    print("=" * 39)
    print(f"Checklist: {report['checklist_path']}")
    print(f"Status: {report['status']}")
    print(f"Blocked: {report['blocked']}")
    print(f"System flags safe: {report['system_flags_safe']}")

    if report["validation_errors"]:
        print("\nValidation errors:")
        for error in report["validation_errors"]:
            print(f"- {error}")
    if report["missing_files"]:
        print("\nMissing files:")
        for path in report["missing_files"]:
            print(f"- {path}")
    if report["enabled_pre_gpu_flags"]:
        print("\nPre-GPU flags enabled unexpectedly:")
        for flag in report["enabled_pre_gpu_flags"]:
            print(f"- {flag}")

    print("\nBefore leaving:")
    for command in report["before_leaving_commands"]:
        print(f"- {command}")

    print("\nFirst hour after assembly:")
    for command in report["first_hour_after_assembly_commands"]:
        print(f"- {command}")

    if show_checklist:
        print("\nHardware pickup notes:")
        hardware = report["hardware_pickup"]
        print(json.dumps(hardware, indent=2))
        print("\nDo not do yet:")
        for item in report["do_not_do_yet"]:
            print(f"- {item}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check pre-trip desktop pickup readiness.")
    parser.add_argument("--checklist", default=str(DEFAULT_CHECKLIST))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--show-checklist", action="store_true")
    args = parser.parse_args()

    checklist_path = Path(args.checklist)
    if not checklist_path.is_absolute():
        checklist_path = PROJECT_ROOT / checklist_path
    report = build_pre_trip_report(checklist_path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report, args.show_checklist)
    if report["blocked"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
