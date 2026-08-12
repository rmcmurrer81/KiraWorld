"""
Validate the first-month operations checklist.
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
    "stage_rule",
    "first_week",
    "month_milestones",
    "daily_checks",
    "failure_recovery",
    "month_one_success",
}

VALID_STATUS = {"draft", "active", "completed", "archived"}
REQUIRED_STAGE_RULES = {
    "text_first",
    "kira_before_lisa",
    "lisa_before_temporary_ai_activation",
    "future_features_wait_for_stage_gates",
    "do_not_enable_everything_at_once",
}
REQUIRED_MILESTONES = {
    "stable_kira_text_life",
    "stable_lisa_text_life",
    "slow_reading_routine",
    "memory_promotion_workflow",
    "safe_temporary_ai_lifecycle_test",
    "backup_manifest_routine",
}
REQUIRED_DAILY_CHECKS = {
    "readiness_check_passes",
    "conversation_logs_preserved",
    "active_reading_sessions_valid",
    "no_hallucinations_promoted",
    "system_flags_match_current_stage",
}
REQUIRED_RECOVERY_KEYS = {
    "model_hallucination",
    "broken_json",
    "confused_identity",
    "temporary_ai_blocked",
    "computer_crash",
}


def _require_true_set(errors: list[str], data: dict[str, Any], keys: set[str], prefix: str) -> None:
    for key in sorted(keys):
        if data.get(key) is not True:
            errors.append(f"{prefix}.{key} must be true.")


def validate_first_month_operations_checklist(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if not str(data.get("checklist_id", "")).strip():
        errors.append("checklist_id is required.")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}.")
    if not str(data.get("purpose", "")).strip():
        errors.append("purpose is required.")

    stage_rule = data.get("stage_rule")
    if not isinstance(stage_rule, dict):
        errors.append("stage_rule must be an object.")
        stage_rule = {}
    _require_true_set(errors, stage_rule, REQUIRED_STAGE_RULES, "stage_rule")

    first_week = data.get("first_week")
    if not isinstance(first_week, list) or len(first_week) != 7:
        errors.append("first_week must contain exactly 7 day entries.")
        first_week = []
    days = set()
    for index, day in enumerate(first_week):
        if not isinstance(day, dict):
            errors.append(f"first_week[{index}] must be an object.")
            continue
        days.add(day.get("day"))
        for field in ("focus", "success_marker"):
            if not str(day.get(field, "")).strip():
                errors.append(f"first_week[{index}].{field} is required.")
        if not isinstance(day.get("required_checks"), list) or not day.get("required_checks"):
            errors.append(f"first_week[{index}].required_checks must be a non-empty list.")
    if days != set(range(1, 8)):
        errors.append("first_week day values must be 1 through 7.")

    milestones = data.get("month_milestones", [])
    if not isinstance(milestones, list):
        errors.append("month_milestones must be a list.")
        milestones = []
    missing_milestones = sorted(REQUIRED_MILESTONES - set(str(item) for item in milestones))
    if missing_milestones:
        errors.append("month_milestones missing: " + ", ".join(missing_milestones))

    daily_checks = data.get("daily_checks", [])
    if not isinstance(daily_checks, list):
        errors.append("daily_checks must be a list.")
        daily_checks = []
    missing_daily_checks = sorted(REQUIRED_DAILY_CHECKS - set(str(item) for item in daily_checks))
    if missing_daily_checks:
        errors.append("daily_checks missing: " + ", ".join(missing_daily_checks))

    recovery = data.get("failure_recovery")
    if not isinstance(recovery, dict):
        errors.append("failure_recovery must be an object.")
        recovery = {}
    missing_recovery = sorted(REQUIRED_RECOVERY_KEYS - set(recovery))
    if missing_recovery:
        errors.append("failure_recovery missing: " + ", ".join(missing_recovery))
    for key, steps in recovery.items():
        if not isinstance(steps, list) or not steps:
            errors.append(f"failure_recovery.{key} must be a non-empty list.")

    success = data.get("month_one_success")
    if not isinstance(success, list) or len(success) < 3:
        errors.append("month_one_success must contain at least 3 success statements.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate first month operations checklist JSON.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_first_month_operations_checklist(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
