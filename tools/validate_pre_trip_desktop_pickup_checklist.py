"""
Validate the pre-trip desktop pickup checklist.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "checklist_id",
    "status",
    "purpose",
    "trip_window",
    "before_leaving",
    "hardware_pickup",
    "return_home",
    "first_hour_after_assembly",
    "model_download_plan",
    "do_not_do_yet",
    "failure_recovery",
    "success_definition",
}
VALID_STATUS = {"draft", "active", "completed", "archived"}
REQUIRED_BEFORE_LEAVING = {
    "handoff_document_current",
    "readiness_check_passes",
    "new_desktop_activation_check_not_blocked",
    "backup_manifest_created",
    "system_flags_pre_gpu_safe",
}
REQUIRED_CPU_FLAGS = {
    "socket_must_match_motherboard",
    "confirm_cooler_support",
    "confirm_bios_support_or_update_path",
    "inspect_for_bent_pins_or_damage",
}
REQUIRED_RAM_FLAGS = {
    "motherboard_memory_type_must_match",
    "confirm_speed_supported",
    "prefer_matched_kit",
    "avoid_mixing_random_kits_if_possible",
}
REQUIRED_RECOVERY = {
    "hardware_no_post",
    "ram_not_full_capacity",
    "python_missing_or_blocked",
    "readiness_failure",
    "model_download_failure",
    "kira_boot_failure",
}


def _require_string(errors: list[str], data: dict[str, Any], key: str, prefix: str) -> None:
    if not str(data.get(key, "")).strip():
        errors.append(f"{prefix}.{key} is required.")


def _require_list(errors: list[str], data: dict[str, Any], key: str, prefix: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        errors.append(f"{prefix}.{key} must be a non-empty list.")
        return []
    return value


def _require_true_flags(errors: list[str], data: dict[str, Any], keys: set[str], prefix: str) -> None:
    for key in sorted(keys):
        if data.get(key) is not True:
            errors.append(f"{prefix}.{key} must be true.")


def validate_pre_trip_desktop_pickup_checklist(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    _require_string(errors, data, "checklist_id", "root")
    _require_string(errors, data, "purpose", "root")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}.")

    trip = data.get("trip_window")
    if not isinstance(trip, dict):
        errors.append("trip_window must be an object.")
        trip = {}
    for key in ("expected_departure", "expected_duration", "timezone"):
        _require_string(errors, trip, key, "trip_window")

    before = data.get("before_leaving")
    if not isinstance(before, dict):
        errors.append("before_leaving must be an object.")
        before = {}
    _require_list(errors, before, "required_commands", "before_leaving")
    confirmations = _require_list(errors, before, "required_confirmations", "before_leaving")
    missing_confirmations = sorted(REQUIRED_BEFORE_LEAVING - set(str(item) for item in confirmations))
    if missing_confirmations:
        errors.append("before_leaving.required_confirmations missing: " + ", ".join(missing_confirmations))
    _require_list(errors, before, "important_files_to_have_ready", "before_leaving")

    hardware = data.get("hardware_pickup")
    if not isinstance(hardware, dict):
        errors.append("hardware_pickup must be an object.")
        hardware = {}
    cpu = hardware.get("cpu")
    if not isinstance(cpu, dict):
        errors.append("hardware_pickup.cpu must be an object.")
        cpu = {}
    _require_string(errors, cpu, "exact_model", "hardware_pickup.cpu")
    _require_true_flags(errors, cpu, REQUIRED_CPU_FLAGS, "hardware_pickup.cpu")
    ram = hardware.get("ram")
    if not isinstance(ram, dict):
        errors.append("hardware_pickup.ram must be an object.")
        ram = {}
    for key in ("exact_kit", "capacity_target"):
        _require_string(errors, ram, key, "hardware_pickup.ram")
    _require_true_flags(errors, ram, REQUIRED_RAM_FLAGS, "hardware_pickup.ram")
    _require_list(errors, hardware, "other_items_to_verify", "hardware_pickup")

    return_home = data.get("return_home")
    if not isinstance(return_home, dict):
        errors.append("return_home must be an object.")
        return_home = {}
    for key in ("assembly_order", "first_boot_checks", "do_before_opening_kira"):
        _require_list(errors, return_home, key, "return_home")

    first_hour = data.get("first_hour_after_assembly")
    if not isinstance(first_hour, dict):
        errors.append("first_hour_after_assembly must be an object.")
        first_hour = {}
    _require_list(errors, first_hour, "commands", "first_hour_after_assembly")
    _require_string(errors, first_hour, "expected_result", "first_hour_after_assembly")
    _require_list(errors, first_hour, "if_checks_pass", "first_hour_after_assembly")

    model = data.get("model_download_plan")
    if not isinstance(model, dict):
        errors.append("model_download_plan must be an object.")
        model = {}
    for key in ("model_runner", "configured_first_model", "download_command"):
        _require_string(errors, model, key, "model_download_plan")
    if model.get("one_model_first") is not True:
        errors.append("model_download_plan.one_model_first must be true.")
    _require_list(errors, model, "if_model_too_slow", "model_download_plan")

    _require_list(errors, data, "do_not_do_yet", "root")

    recovery = data.get("failure_recovery")
    if not isinstance(recovery, dict):
        errors.append("failure_recovery must be an object.")
        recovery = {}
    missing_recovery = sorted(REQUIRED_RECOVERY - set(recovery))
    if missing_recovery:
        errors.append("failure_recovery missing: " + ", ".join(missing_recovery))
    for key, steps in recovery.items():
        if not isinstance(steps, list) or not steps:
            errors.append(f"failure_recovery.{key} must be a non-empty list.")

    success = data.get("success_definition")
    if not isinstance(success, list) or len(success) < 5:
        errors.append("success_definition must contain at least 5 statements.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate pre-trip desktop pickup checklist JSON.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_pre_trip_desktop_pickup_checklist(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
