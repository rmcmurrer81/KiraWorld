"""
Validate the new desktop first-hour rehearsal checklist.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "rehearsal_id",
    "status",
    "purpose",
    "first_hour_rules",
    "required_preflight_commands",
    "stub_smoke_commands",
    "first_model_commands",
    "kira_smoke_questions",
    "lisa_smoke_questions",
    "temporary_ai_dry_run_commands",
    "blocked_first_hour_actions",
    "success_definition",
    "failure_recovery",
}
VALID_STATUS = {"draft", "active", "completed", "archived"}
REQUIRED_RULES = {
    "text_only_first",
    "stub_before_local_model",
    "kira_before_lisa",
    "temporary_ai_dry_run_only",
    "one_model_first",
    "backup_before_model_download",
    "do_not_promote_smoke_test_output",
}
REQUIRED_BLOCKS = {
    "enable_voice",
    "enable_avatar",
    "enable_world",
    "enable_webcam",
    "enable_internet_autonomy",
    "activate_temporary_ai",
    "run_adult_private_temporary_ai",
    "promote_smoke_test_output_to_memory",
    "download_multiple_models",
}


def _require_non_empty_list(errors: list[str], data: dict[str, Any], key: str) -> None:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        errors.append(f"{key} must be a non-empty list.")


def validate_new_desktop_first_hour_rehearsal(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    if not str(data.get("rehearsal_id", "")).strip():
        errors.append("rehearsal_id is required.")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}.")
    if not str(data.get("purpose", "")).strip():
        errors.append("purpose is required.")

    rules = data.get("first_hour_rules")
    if not isinstance(rules, dict):
        errors.append("first_hour_rules must be an object.")
        rules = {}
    for rule in sorted(REQUIRED_RULES):
        if rules.get(rule) is not True:
            errors.append(f"first_hour_rules.{rule} must be true.")

    for key in (
        "required_preflight_commands",
        "stub_smoke_commands",
        "first_model_commands",
        "kira_smoke_questions",
        "lisa_smoke_questions",
        "temporary_ai_dry_run_commands",
        "blocked_first_hour_actions",
        "success_definition",
        "failure_recovery",
    ):
        _require_non_empty_list(errors, data, key)

    blocked = set(str(item) for item in data.get("blocked_first_hour_actions", []) if isinstance(item, str))
    missing_blocks = sorted(REQUIRED_BLOCKS - blocked)
    if missing_blocks:
        errors.append("blocked_first_hour_actions missing: " + ", ".join(missing_blocks))

    preflight_text = "\n".join(str(item) for item in data.get("required_preflight_commands", []))
    for required_command in (
        "py tools\\readiness_check.py",
        "py tools\\desktop_model_readiness.py",
        "py tools\\build_backup_manifest.py",
    ):
        if required_command not in preflight_text:
            errors.append(f"required_preflight_commands must include {required_command}.")

    temp_ai_text = "\n".join(str(item) for item in data.get("temporary_ai_dry_run_commands", []))
    if "validate_temp_ai_simple_request.py" not in temp_ai_text or "plan_temp_ai_request.py" not in temp_ai_text:
        errors.append("temporary_ai_dry_run_commands must validate and plan TemporaryAI examples.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate new desktop first-hour rehearsal JSON.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_new_desktop_first_hour_rehearsal(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
