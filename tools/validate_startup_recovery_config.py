"""
Validate startup recovery configuration for desktop auto-start.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "startup_recovery_id",
    "status",
    "purpose",
    "auto_start",
    "health_checks",
    "power_loss_recovery",
    "watched_identity_roots",
    "required_files",
    "success_definition",
}
VALID_STATUS = {"draft", "active", "completed", "archived"}
REQUIRED_AUTO_START_TRUE = {
    "windows_startup_supported",
    "install_manually_after_new_desktop_is_stable",
    "require_checks_before_launch",
    "block_launch_on_failed_checks",
    "do_not_auto_start_lisa_until_kira_stable",
    "do_not_auto_start_temporary_ai",
}
REQUIRED_HEALTH_CHECKS = {
    "startup_recovery_config_valid",
    "required_files_exist",
    "watched_identity_roots_exist",
    "json_files_parse",
    "system_flags_safe",
    "readiness_check_passes",
    "desktop_model_readiness_passes",
}
REQUIRED_POWER_LOSS_TRUE = {
    "detect_unclean_previous_session",
    "block_launch_if_deeper_checks_fail",
}


def _non_empty_string(errors: list[str], data: dict[str, Any], key: str, prefix: str) -> None:
    if not str(data.get(key, "")).strip():
        errors.append(f"{prefix}.{key} is required.")


def _non_empty_list(errors: list[str], data: dict[str, Any], key: str, prefix: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        errors.append(f"{prefix}.{key} must be a non-empty list.")
        return []
    return value


def validate_startup_recovery_config(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append("Missing required fields: " + ", ".join(missing))

    _non_empty_string(errors, data, "startup_recovery_id", "root")
    _non_empty_string(errors, data, "purpose", "root")
    if data.get("status") not in VALID_STATUS:
        errors.append("status must be one of: " + ", ".join(sorted(VALID_STATUS)) + ".")

    auto_start = data.get("auto_start")
    if not isinstance(auto_start, dict):
        errors.append("auto_start must be an object.")
        auto_start = {}
    for key in sorted(REQUIRED_AUTO_START_TRUE):
        if auto_start.get(key) is not True:
            errors.append(f"auto_start.{key} must be true.")
    if auto_start.get("default_enabled_in_repo") is not False:
        errors.append("auto_start.default_enabled_in_repo must be false until Robert installs it on the desktop.")
    _non_empty_string(errors, auto_start, "startup_script", "auto_start")
    _non_empty_string(errors, auto_start, "launch_mode", "auto_start")
    _non_empty_string(errors, auto_start, "launch_command", "auto_start")

    health = data.get("health_checks")
    if not isinstance(health, dict):
        errors.append("health_checks must be an object.")
        health = {}
    checks = set(str(item) for item in health.get("required_before_launch", []))
    missing_checks = sorted(REQUIRED_HEALTH_CHECKS - checks)
    if missing_checks:
        errors.append("health_checks.required_before_launch missing: " + ", ".join(missing_checks))
    _non_empty_list(errors, health, "commands", "health_checks")
    _non_empty_string(errors, health, "write_report_to", "health_checks")
    _non_empty_string(errors, health, "write_state_to", "health_checks")

    recovery = data.get("power_loss_recovery")
    if not isinstance(recovery, dict):
        errors.append("power_loss_recovery must be an object.")
        recovery = {}
    for key in sorted(REQUIRED_POWER_LOSS_TRUE):
        if recovery.get(key) is not True:
            errors.append(f"power_loss_recovery.{key} must be true.")
    _non_empty_string(errors, recovery, "unclean_session_action", "power_loss_recovery")
    _non_empty_list(errors, recovery, "deeper_check_commands", "power_loss_recovery")
    _non_empty_list(errors, recovery, "record_possible_causes", "power_loss_recovery")
    _non_empty_list(errors, recovery, "recovery_notes", "power_loss_recovery")

    roots = _non_empty_list(errors, data, "watched_identity_roots", "root")
    required_files = _non_empty_list(errors, data, "required_files", "root")
    success = _non_empty_list(errors, data, "success_definition", "root")
    if len(roots) < 5:
        errors.append("watched_identity_roots should include Kira, Lisa, TemporaryAI, and core Data roots.")
    if len(required_files) < 8:
        errors.append("required_files should include launch scripts, config, prompts, and recovery tools.")
    if len(success) < 5:
        errors.append("success_definition must contain at least 5 statements.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate startup recovery config JSON.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_startup_recovery_config(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
