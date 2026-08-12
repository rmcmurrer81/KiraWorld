"""
Validate the hardware intake and rested-build gate checklist.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "gate_id",
    "status",
    "purpose",
    "expected_return_plan",
    "intake_record",
    "safe_storage",
    "rest_before_build_gate",
    "post_purchase_compatibility_check",
    "first_build_day",
    "do_not_do_tired",
    "success_definition",
}
VALID_STATUS = {"draft", "active", "completed", "archived"}
REQUIRED_REST_CONFIRMATIONS = {
    "not_sleep_deprived",
    "hands_steady",
    "has_eaten_recently",
    "good_lighting",
    "enough_uninterrupted_time",
    "parts_and_tools_are_organized",
}
REQUIRED_BLOCKED_TIRED = {
    "opening_cpu_socket",
    "installing_cpu",
    "installing_ram",
    "installing_cooler",
    "plugging_in_power_for_first_boot",
}
REQUIRED_SAFE_STORAGE = {
    "flat_dry_stable_surface",
    "away_from_liquids",
    "not_under_heavy_items",
    "do_not_discard_packaging",
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


def validate_hardware_intake_rest_gate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append("Missing required fields: " + ", ".join(missing))

    _require_string(errors, data, "gate_id", "root")
    _require_string(errors, data, "purpose", "root")
    if data.get("status") not in VALID_STATUS:
        errors.append("status must be one of: " + ", ".join(sorted(VALID_STATUS)) + ".")

    expected = data.get("expected_return_plan")
    if not isinstance(expected, dict):
        errors.append("expected_return_plan must be an object.")
        expected = {}
    for key in ("known_reserved_item", "likely_condition"):
        _require_string(errors, expected, key, "expected_return_plan")
    _require_list(errors, expected, "immediate_actions", "expected_return_plan")

    intake = data.get("intake_record")
    if not isinstance(intake, dict):
        errors.append("intake_record must be an object.")
        intake = {}
    cpu = intake.get("cpu")
    if not isinstance(cpu, dict):
        errors.append("intake_record.cpu must be an object.")
        cpu = {}
    _require_string(errors, cpu, "expected_model", "intake_record.cpu")
    _require_string(errors, cpu, "purchase_status", "intake_record.cpu")
    ram = intake.get("ram")
    if not isinstance(ram, dict):
        errors.append("intake_record.ram must be an object.")
        ram = {}
    _require_string(errors, ram, "purchase_status", "intake_record.ram")

    storage = data.get("safe_storage")
    if not isinstance(storage, dict):
        errors.append("safe_storage must be an object.")
        storage = {}
    storage_rules = set(str(item) for item in _require_list(errors, storage, "required_conditions", "safe_storage"))
    missing_storage = sorted(REQUIRED_SAFE_STORAGE - storage_rules)
    if missing_storage:
        errors.append("safe_storage.required_conditions missing: " + ", ".join(missing_storage))

    gate = data.get("rest_before_build_gate")
    if not isinstance(gate, dict):
        errors.append("rest_before_build_gate must be an object.")
        gate = {}
    if gate.get("assembly_blocked_until_rest_gate_passes") is not True:
        errors.append("rest_before_build_gate.assembly_blocked_until_rest_gate_passes must be true.")
    confirmations = set(str(item) for item in _require_list(errors, gate, "must_confirm_before_build", "rest_before_build_gate"))
    missing_confirmations = sorted(REQUIRED_REST_CONFIRMATIONS - confirmations)
    if missing_confirmations:
        errors.append("rest_before_build_gate.must_confirm_before_build missing: " + ", ".join(missing_confirmations))
    blocked = set(str(item) for item in _require_list(errors, gate, "blocked_before_rest_gate", "rest_before_build_gate"))
    missing_blocked = sorted(REQUIRED_BLOCKED_TIRED - blocked)
    if missing_blocked:
        errors.append("rest_before_build_gate.blocked_before_rest_gate missing: " + ", ".join(missing_blocked))
    _require_list(errors, gate, "allowed_before_rest_gate", "rest_before_build_gate")

    compatibility = data.get("post_purchase_compatibility_check")
    if not isinstance(compatibility, dict):
        errors.append("post_purchase_compatibility_check must be an object.")
        compatibility = {}
    compat_cpu = compatibility.get("cpu")
    if not isinstance(compat_cpu, dict):
        errors.append("post_purchase_compatibility_check.cpu must be an object.")
        compat_cpu = {}
    if compat_cpu.get("must_match_motherboard_socket") != "LGA1851":
        errors.append("post_purchase_compatibility_check.cpu.must_match_motherboard_socket must be LGA1851.")
    for key in ("confirm_bios_support", "confirm_cooler_mounting_support", "confirm_power_and_thermal_plan"):
        if compat_cpu.get(key) is not True:
            errors.append(f"post_purchase_compatibility_check.cpu.{key} must be true.")
    compat_ram = compatibility.get("ram")
    if not isinstance(compat_ram, dict):
        errors.append("post_purchase_compatibility_check.ram must be an object.")
        compat_ram = {}
    if compat_ram.get("required_type") != "DDR5":
        errors.append("post_purchase_compatibility_check.ram.required_type must be DDR5.")
    if compat_ram.get("build_can_wait_if_ram_not_obtained") is not True:
        errors.append("post_purchase_compatibility_check.ram.build_can_wait_if_ram_not_obtained must be true.")
    _require_list(errors, compatibility, "before_opening_parts", "post_purchase_compatibility_check")

    first_build = data.get("first_build_day")
    if not isinstance(first_build, dict):
        errors.append("first_build_day must be an object.")
        first_build = {}
    for key in ("start_conditions", "order", "if_ram_not_available"):
        _require_list(errors, first_build, key, "first_build_day")

    tired_rules = set(str(item) for item in _require_list(errors, data, "do_not_do_tired", "root"))
    if "do_not_start_kira_activation_before_hardware_and_readiness_checks" not in tired_rules:
        errors.append("do_not_do_tired must include do_not_start_kira_activation_before_hardware_and_readiness_checks.")

    success = data.get("success_definition")
    if not isinstance(success, list) or len(success) < 5:
        errors.append("success_definition must contain at least 5 statements.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate hardware intake and rested-build gate JSON.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_hardware_intake_rest_gate(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
