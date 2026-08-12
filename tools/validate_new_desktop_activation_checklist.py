"""
Validate the new desktop activation checklist.
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
    "activation_sequence",
    "smoke_tests",
    "temporary_ai_first_run",
    "backup_points",
    "failure_recovery",
    "success_definition",
}
VALID_STATUS = {"draft", "active", "completed", "archived"}
REQUIRED_STAGE_RULES = {
    "text_first",
    "kira_before_lisa",
    "lisa_before_temporary_ai",
    "stub_before_local_model",
    "one_model_first",
    "voice_avatar_world_disabled",
    "no_internet_autonomy_on_day_one",
    "no_temporary_ai_intimacy_first_run",
    "backup_before_each_major_stage",
}
REQUIRED_STAGE_IDS = {
    "preflight",
    "kira_stub_boot",
    "kira_local_model_boot",
    "kira_day_one_routine",
    "lisa_stub_and_local_boot",
    "kira_lisa_together",
    "temporary_ai_safe_lifecycle_dry_run",
}
REQUIRED_SMOKE_TESTS = {
    "kira_questions",
    "lisa_questions",
    "kira_lisa_questions",
    "temporary_ai_questions",
}
REQUIRED_TEMP_AI_KEYS = {
    "preferred_first_test",
    "ladybug_note",
    "required_lifecycle_steps",
    "blocked_first_run_modes",
}
REQUIRED_BACKUP_POINTS = {
    "before_first_kira_local_model_boot",
    "before_lisa_boot",
    "before_temporary_ai_lifecycle_test",
    "after_temporary_ai_deactivation_or_archive",
}
REQUIRED_RECOVERY_KEYS = {
    "setup_failure",
    "model_missing",
    "kira_identity_failure",
    "lisa_separation_failure",
    "memory_boundary_failure",
    "temporary_ai_blocked",
    "readiness_failure",
}


def _require_true_set(errors: list[str], data: dict[str, Any], keys: set[str], prefix: str) -> None:
    for key in sorted(keys):
        if data.get(key) is not True:
            errors.append(f"{prefix}.{key} must be true.")


def _require_non_empty_string(errors: list[str], data: dict[str, Any], key: str, prefix: str) -> None:
    if not str(data.get(key, "")).strip():
        errors.append(f"{prefix}.{key} is required.")


def _require_non_empty_list(errors: list[str], data: dict[str, Any], key: str, prefix: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        errors.append(f"{prefix}.{key} must be a non-empty list.")
        return []
    return value


def validate_new_desktop_activation_checklist(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    _require_non_empty_string(errors, data, "checklist_id", "root")
    _require_non_empty_string(errors, data, "purpose", "root")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}.")

    stage_rule = data.get("stage_rule")
    if not isinstance(stage_rule, dict):
        errors.append("stage_rule must be an object.")
        stage_rule = {}
    _require_true_set(errors, stage_rule, REQUIRED_STAGE_RULES, "stage_rule")

    sequence = data.get("activation_sequence")
    if not isinstance(sequence, list) or len(sequence) != len(REQUIRED_STAGE_IDS):
        errors.append(f"activation_sequence must contain exactly {len(REQUIRED_STAGE_IDS)} stages.")
        sequence = []
    stage_numbers = set()
    stage_ids = set()
    for index, stage in enumerate(sequence):
        if not isinstance(stage, dict):
            errors.append(f"activation_sequence[{index}] must be an object.")
            continue
        stage_numbers.add(stage.get("stage"))
        stage_ids.add(str(stage.get("stage_id", "")))
        for field in ("stage_id", "goal"):
            _require_non_empty_string(errors, stage, field, f"activation_sequence[{index}]")
        for field in ("required_commands", "required_success", "do_not_continue_if"):
            _require_non_empty_list(errors, stage, field, f"activation_sequence[{index}]")
    if stage_numbers != set(range(1, len(REQUIRED_STAGE_IDS) + 1)):
        errors.append("activation_sequence stage values must be contiguous starting at 1.")
    missing_stage_ids = sorted(REQUIRED_STAGE_IDS - stage_ids)
    if missing_stage_ids:
        errors.append("activation_sequence missing stage_id: " + ", ".join(missing_stage_ids))

    smoke = data.get("smoke_tests")
    if not isinstance(smoke, dict):
        errors.append("smoke_tests must be an object.")
        smoke = {}
    missing_smoke = sorted(REQUIRED_SMOKE_TESTS - set(smoke))
    if missing_smoke:
        errors.append("smoke_tests missing: " + ", ".join(missing_smoke))
    for key, questions in smoke.items():
        if not isinstance(questions, list) or len(questions) < 2:
            errors.append(f"smoke_tests.{key} must contain at least 2 questions.")

    temp_ai = data.get("temporary_ai_first_run")
    if not isinstance(temp_ai, dict):
        errors.append("temporary_ai_first_run must be an object.")
        temp_ai = {}
    missing_temp_ai = sorted(REQUIRED_TEMP_AI_KEYS - set(temp_ai))
    if missing_temp_ai:
        errors.append("temporary_ai_first_run missing: " + ", ".join(missing_temp_ai))
    for key in ("required_lifecycle_steps", "blocked_first_run_modes"):
        _require_non_empty_list(errors, temp_ai, key, "temporary_ai_first_run")
    for key in ("preferred_first_test", "ladybug_note"):
        _require_non_empty_string(errors, temp_ai, key, "temporary_ai_first_run")

    backup_points = data.get("backup_points")
    if not isinstance(backup_points, list):
        errors.append("backup_points must be a list.")
        backup_points = []
    missing_backup = sorted(REQUIRED_BACKUP_POINTS - set(str(item) for item in backup_points))
    if missing_backup:
        errors.append("backup_points missing: " + ", ".join(missing_backup))

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

    success = data.get("success_definition")
    if not isinstance(success, list) or len(success) < 5:
        errors.append("success_definition must contain at least 5 success statements.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate new desktop activation checklist JSON.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_new_desktop_activation_checklist(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
