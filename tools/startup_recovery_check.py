"""
Startup and power-loss recovery check for the desktop Kira system.

This tool can be run by Windows startup before Kira is opened. It validates the
startup recovery config, checks watched identity roots, parses watched JSON
files, detects a previous unclean session, and optionally runs command checks.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from validate_startup_recovery_config import validate_startup_recovery_config
except ModuleNotFoundError:  # Imported as tools.startup_recovery_check in tests.
    from tools.validate_startup_recovery_config import validate_startup_recovery_config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "Data" / "launch" / "startup_recovery_config.json"
DEFAULT_STATE = PROJECT_ROOT / "Data" / "launch" / "startup_recovery_state.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_state(state_path: Path = DEFAULT_STATE) -> dict[str, Any]:
    if not state_path.exists():
        return {
            "state_id": "startup_recovery_state_v1",
            "active_session": False,
            "last_startup_at": None,
            "last_clean_shutdown_at": None,
            "last_launch_mode": None,
            "last_report_path": None,
            "last_unclean_session_detected": False,
            "notes": [],
        }
    return _load_json(state_path)


def system_flags_safe() -> tuple[bool, list[str]]:
    path = PROJECT_ROOT / "config" / "system_flags.json"
    if not path.exists():
        return False, ["config/system_flags.json missing"]
    data = _load_json(path)
    enabled = [key for key in ("voice_enabled", "avatar_enabled", "world_enabled", "temp_ai_enabled") if data.get(key) is True]
    return not enabled, enabled


def parse_watched_json(roots: list[str]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for root in roots:
        path = PROJECT_ROOT / root
        if not path.exists():
            continue
        for json_path in sorted(path.rglob("*.json")):
            relative_parts = {part.lower() for part in json_path.relative_to(path).parts}
            # Archived candidates and candidate-authored workbench drafts are
            # evidence, not live identity/runtime authority. A deliberately
            # illustrative JSON fragment there must not block text-only startup.
            if "archived_candidates" in relative_parts or "workbench" in relative_parts:
                continue
            try:
                json.loads(json_path.read_text(encoding="utf-8-sig"))
            except Exception as exc:
                errors.append({"path": _relative(json_path), "error": str(exc)})
    return errors


def run_command(command: str, timeout: int = 180) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return {
        "command": command,
        "returncode": result.returncode,
        "passed": result.returncode == 0,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
    }


def mark_start(state_path: Path, launch_mode: str, report_path: Path | None = None) -> dict[str, Any]:
    state = load_state(state_path)
    state.update(
        {
            "active_session": True,
            "last_startup_at": _now(),
            "last_launch_mode": launch_mode,
            "last_report_path": _relative(report_path) if report_path else state.get("last_report_path"),
        }
    )
    _write_json(state_path, state)
    return state


def mark_clean_shutdown(state_path: Path) -> dict[str, Any]:
    state = load_state(state_path)
    state.update(
        {
            "active_session": False,
            "last_clean_shutdown_at": _now(),
            "last_unclean_session_detected": False,
        }
    )
    _write_json(state_path, state)
    return state


def build_startup_report(
    config_path: Path = DEFAULT_CONFIG,
    run_command_checks: bool = False,
    mark_session_start: bool = False,
) -> dict[str, Any]:
    config = _load_json(config_path)
    validation_errors = validate_startup_recovery_config(config)
    state_path = PROJECT_ROOT / config.get("health_checks", {}).get("write_state_to", "Data/launch/startup_recovery_state.json")
    report_path = PROJECT_ROOT / config.get("health_checks", {}).get("write_report_to", "Data/launch/startup_recovery_last_report.json")
    previous_state = load_state(state_path)
    unclean_previous_session = bool(previous_state.get("active_session"))

    required_files = config.get("required_files", [])
    missing_files = [path for path in required_files if not (PROJECT_ROOT / path).exists()]
    watched_roots = config.get("watched_identity_roots", [])
    missing_roots = [path for path in watched_roots if not (PROJECT_ROOT / path).exists()]
    json_errors = parse_watched_json(watched_roots)
    flags_safe, enabled_flags = system_flags_safe()

    command_results: list[dict[str, Any]] = []
    commands: list[str] = []
    if run_command_checks:
        commands.extend(config.get("health_checks", {}).get("commands", []))
        if unclean_previous_session:
            commands.extend(config.get("power_loss_recovery", {}).get("deeper_check_commands", []))
        seen: set[str] = set()
        for command in commands:
            if command in seen:
                continue
            seen.add(command)
            command_results.append(run_command(command))

    failed_commands = [item for item in command_results if not item["passed"]]
    blocked = bool(validation_errors or missing_files or missing_roots or json_errors or not flags_safe or failed_commands)

    report = {
        "generated_at": _now(),
        "config_path": _relative(config_path),
        "status": config.get("status"),
        "launch_mode": config.get("auto_start", {}).get("launch_mode"),
        "blocked": blocked,
        "unclean_previous_session": unclean_previous_session,
        "validation_errors": validation_errors,
        "missing_files": missing_files,
        "missing_watched_roots": missing_roots,
        "json_error_count": len(json_errors),
        "json_errors": json_errors,
        "system_flags_safe": flags_safe,
        "enabled_pre_gpu_flags": enabled_flags,
        "command_checks_ran": run_command_checks,
        "command_results": command_results,
        "failed_commands": [item["command"] for item in failed_commands],
        "recovery_notes": config.get("power_loss_recovery", {}).get("recovery_notes", []),
        "state_path": _relative(state_path),
    }
    _write_json(report_path, report)

    if mark_session_start and not blocked:
        mark_start(state_path, str(report["launch_mode"]), report_path)
    else:
        state = load_state(state_path)
        state["last_report_path"] = _relative(report_path)
        state["last_unclean_session_detected"] = unclean_previous_session
        _write_json(state_path, state)

    return report


def print_report(report: dict[str, Any]) -> None:
    print("Kira desktop startup recovery check")
    print("=" * 36)
    print(f"Config: {report['config_path']}")
    print(f"Status: {report['status']}")
    print(f"Launch mode: {report['launch_mode']}")
    print(f"Blocked: {report['blocked']}")
    print(f"Unclean previous session: {report['unclean_previous_session']}")
    print(f"System flags safe: {report['system_flags_safe']}")
    print(f"JSON errors: {report['json_error_count']}")

    if report["validation_errors"]:
        print("\nValidation errors:")
        for error in report["validation_errors"]:
            print(f"- {error}")
    if report["missing_files"]:
        print("\nMissing files:")
        for path in report["missing_files"]:
            print(f"- {path}")
    if report["missing_watched_roots"]:
        print("\nMissing watched roots:")
        for path in report["missing_watched_roots"]:
            print(f"- {path}")
    if report["enabled_pre_gpu_flags"]:
        print("\nPre-GPU flags enabled:")
        for flag in report["enabled_pre_gpu_flags"]:
            print(f"- {flag}")
    if report["failed_commands"]:
        print("\nFailed command checks:")
        for command in report["failed_commands"]:
            print(f"- {command}")
    if report["unclean_previous_session"]:
        print("\nRecovery notes:")
        for note in report["recovery_notes"]:
            print(f"- {note}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check desktop startup and power-loss recovery readiness.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--run-command-checks", action="store_true", help="Run readiness/model readiness command checks.")
    parser.add_argument("--mark-session-start", action="store_true", help="Mark session active if checks pass.")
    parser.add_argument("--mark-clean-shutdown", action="store_true", help="Mark the previous session as cleanly closed.")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    config = _load_json(config_path)
    state_path = PROJECT_ROOT / config.get("health_checks", {}).get("write_state_to", "Data/launch/startup_recovery_state.json")

    if args.mark_clean_shutdown:
        state = mark_clean_shutdown(state_path)
        if args.json:
            print(json.dumps(state, indent=2))
        else:
            print("Marked startup recovery session as cleanly shut down.")
        return

    report = build_startup_report(
        config_path=config_path,
        run_command_checks=args.run_command_checks,
        mark_session_start=args.mark_session_start,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    if report["blocked"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
