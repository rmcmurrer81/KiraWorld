"""
Validate skill development JSON files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "skill_id",
    "owner",
    "skill_name",
    "skill_domain",
    "origin",
    "preference_signal",
    "learning_state",
    "practice_rules",
    "autonomy_limits",
    "privacy",
    "status",
}
VALID_OWNERS = {"kira", "lisa", "shared_kira_lisa"}
VALID_DOMAINS = {
    "filmmaking",
    "video_editing",
    "storytelling",
    "writing",
    "programming",
    "painting",
    "music",
    "world_building",
    "research",
    "other",
}
VALID_LEARNING_STAGES = {"spark", "curious", "beginner", "practicing", "competent", "advanced", "paused"}
VALID_STATUS = {"draft", "active", "paused", "archived"}


def validate_skill_development(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    if not str(data.get("skill_id", "")).strip():
        errors.append("skill_id is required.")
    if data.get("owner") not in VALID_OWNERS:
        errors.append(f"owner must be one of: {', '.join(sorted(VALID_OWNERS))}")
    if data.get("skill_domain") not in VALID_DOMAINS:
        errors.append(f"skill_domain must be one of: {', '.join(sorted(VALID_DOMAINS))}")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")

    for object_field in ("origin", "preference_signal", "learning_state", "practice_rules", "autonomy_limits", "privacy"):
        if object_field in data and not isinstance(data.get(object_field), dict):
            errors.append(f"{object_field} must be an object.")

    preference = data.get("preference_signal", {})
    if isinstance(preference, dict):
        for field in ("likes", "dislikes", "curious_about"):
            if field in preference and not isinstance(preference.get(field), list):
                errors.append(f"preference_signal.{field} must be a list.")
        interest_level = preference.get("interest_level")
        if not isinstance(interest_level, (int, float)) or not 0 <= float(interest_level) <= 1:
            errors.append("preference_signal.interest_level must be a number from 0 to 1.")

    learning = data.get("learning_state", {})
    if isinstance(learning, dict):
        if learning.get("learning_stage") not in VALID_LEARNING_STAGES:
            errors.append(f"learning_state.learning_stage must be one of: {', '.join(sorted(VALID_LEARNING_STAGES))}")
        confidence = learning.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            errors.append("learning_state.confidence must be a number from 0 to 1.")

    practice = data.get("practice_rules", {})
    if isinstance(practice, dict):
        for key in (
            "may_read_or_study_pre_gpu",
            "may_make_private_drafts_pre_gpu",
            "may_use_local_library_sources",
            "may_install_tools_without_approval",
            "may_spend_money_without_approval",
            "may_contact_people_without_approval",
        ):
            if practice.get(key) not in (True, False):
                errors.append(f"practice_rules.{key} must be true or false.")
        for blocked_key in (
            "may_install_tools_without_approval",
            "may_spend_money_without_approval",
            "may_contact_people_without_approval",
        ):
            if practice.get(blocked_key) is True:
                errors.append(f"practice_rules.{blocked_key} must remain false at current stage.")

    autonomy = data.get("autonomy_limits", {})
    if isinstance(autonomy, dict):
        for key in ("can_start_private_project", "can_invite_robert_to_view", "can_keep_private", "can_publish_publicly_now", "requires_public_export_review"):
            if autonomy.get(key) not in (True, False):
                errors.append(f"autonomy_limits.{key} must be true or false.")
        if autonomy.get("can_publish_publicly_now") is True:
            errors.append("autonomy_limits.can_publish_publicly_now must be false at current stage.")
        if autonomy.get("requires_public_export_review") is not True:
            errors.append("autonomy_limits.requires_public_export_review must be true.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a skill development JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_skill_development(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
