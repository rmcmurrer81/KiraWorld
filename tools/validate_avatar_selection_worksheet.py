"""
Validate pre-GPU avatar selection worksheets.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "worksheet_id",
    "owner",
    "stage",
    "source_index",
    "selection_status",
    "feature_preferences",
    "privacy",
    "feedback_permissions",
    "post_gpu_upgrade_path",
    "rules",
    "status",
}

VALID_OWNERS = {"kira", "lisa", "user", "temp_ai"}
VALID_STAGES = {"pre_gpu", "post_gpu"}
VALID_SELECTION_STATUS = {"not_started", "browsing", "leaning", "selected", "waiting_for_gpu"}
VALID_PREVIEW_LEVELS = {"no_preview", "feature_only", "shoulders_up", "full_body_feedback", "clothed_only"}
VALID_STATUS = {"draft", "active", "archived"}


def validate_avatar_selection_worksheet(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if data.get("owner") not in VALID_OWNERS:
        errors.append(f"owner must be one of: {', '.join(sorted(VALID_OWNERS))}")
    if data.get("stage") not in VALID_STAGES:
        errors.append(f"stage must be one of: {', '.join(sorted(VALID_STAGES))}")
    if data.get("selection_status") not in VALID_SELECTION_STATUS:
        errors.append(f"selection_status must be one of: {', '.join(sorted(VALID_SELECTION_STATUS))}")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")

    source_index = data.get("source_index")
    if not isinstance(source_index, dict):
        errors.append("source_index must be an object.")
    else:
        if not source_index.get("path"):
            errors.append("source_index.path is required.")

    feature_preferences = data.get("feature_preferences")
    if not isinstance(feature_preferences, dict):
        errors.append("feature_preferences must be an object.")
    else:
        for key, value in feature_preferences.items():
            if not isinstance(value, dict):
                errors.append(f"feature_preferences.{key} must be an object.")
                continue
            if "candidate_reference_paths" in value and not isinstance(value["candidate_reference_paths"], list):
                errors.append(f"feature_preferences.{key}.candidate_reference_paths must be a list.")
            if "notes" in value and not isinstance(value["notes"], str):
                errors.append(f"feature_preferences.{key}.notes must be a string.")

    privacy = data.get("privacy")
    if not isinstance(privacy, dict):
        errors.append("privacy must be an object.")
    else:
        if privacy.get("owner_controls_visibility") is not True:
            errors.append("privacy.owner_controls_visibility must be true.")
        if privacy.get("default_preview_level") != "no_preview":
            errors.append("privacy.default_preview_level must be no_preview.")
        if privacy.get("body_choices_private_by_default") is not True:
            errors.append("privacy.body_choices_private_by_default must be true.")
        if privacy.get("show_body_to_robert_by_default") is not False:
            errors.append("privacy.show_body_to_robert_by_default must be false.")
        allowed = privacy.get("allowed_preview_levels")
        if not isinstance(allowed, list) or not set(allowed).issubset(VALID_PREVIEW_LEVELS):
            errors.append(f"privacy.allowed_preview_levels must contain only: {', '.join(sorted(VALID_PREVIEW_LEVELS))}")

    feedback = data.get("feedback_permissions")
    if not isinstance(feedback, dict):
        errors.append("feedback_permissions must be an object.")
    else:
        for participant in ("robert", "kira", "lisa"):
            if participant in feedback:
                item = feedback[participant]
                if not isinstance(item, dict):
                    errors.append(f"feedback_permissions.{participant} must be an object.")
                    continue
                if item.get("may_be_asked_for_opinion") not in {True, False}:
                    errors.append(f"feedback_permissions.{participant}.may_be_asked_for_opinion must be true or false.")
                level = item.get("maximum_preview_level")
                if level not in VALID_PREVIEW_LEVELS:
                    errors.append(f"feedback_permissions.{participant}.maximum_preview_level is invalid.")

    upgrade = data.get("post_gpu_upgrade_path")
    if not isinstance(upgrade, dict):
        errors.append("post_gpu_upgrade_path must be an object.")
    else:
        if upgrade.get("pre_gpu_is_design_intent_only") is not True:
            errors.append("post_gpu_upgrade_path.pre_gpu_is_design_intent_only must be true.")
        if upgrade.get("claim_3d_avatar_exists_now") is not False:
            errors.append("post_gpu_upgrade_path.claim_3d_avatar_exists_now must be false.")

    rules = data.get("rules")
    if not isinstance(rules, dict):
        errors.append("rules must be an object.")
    else:
        required_true = {
            "do_not_clone_single_reference_person",
            "do_not_treat_reference_as_memory",
            "do_not_treat_reference_as_identity_fact",
            "final_avatar_is_new_person_design",
        }
        for key in sorted(required_true):
            if rules.get(key) is not True:
                errors.append(f"rules.{key} must be true.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an avatar selection worksheet.")
    parser.add_argument("path", help="Path to avatar selection worksheet JSON.")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_avatar_selection_worksheet(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
