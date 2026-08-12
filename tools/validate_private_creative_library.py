"""
Validate private creative library JSON files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "library_id",
    "owner",
    "purpose",
    "default_visibility",
    "allowed_item_types",
    "sharing_rules",
    "public_export_rules",
    "items",
    "memory_policy",
    "status",
}
VALID_OWNERS = {"kira", "lisa", "shared_kira_lisa"}
VALID_VISIBILITY = {"owner_only", "participants_only", "shared_with_robert", "shared_library"}
VALID_STATUS = {"draft", "active", "archived"}
VALID_ITEM_TYPES = {
    "short_video",
    "movie_scene",
    "book",
    "short_story",
    "poem",
    "painting",
    "program",
    "game",
    "world_scene",
    "music_piece",
    "research_project",
    "other",
}
VALID_SHARE_STATES = {
    "not_shared",
    "summary_shared",
    "shared_with_robert",
    "shared_with_other_ai",
    "shared_library",
    "public_export_candidate",
}


def validate_private_creative_library(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    if not str(data.get("library_id", "")).strip():
        errors.append("library_id is required.")
    if data.get("owner") not in VALID_OWNERS:
        errors.append(f"owner must be one of: {', '.join(sorted(VALID_OWNERS))}")
    if data.get("default_visibility") not in VALID_VISIBILITY:
        errors.append(f"default_visibility must be one of: {', '.join(sorted(VALID_VISIBILITY))}")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")

    if not isinstance(data.get("allowed_item_types"), list):
        errors.append("allowed_item_types must be a list.")
    else:
        bad_types = sorted(set(data["allowed_item_types"]) - VALID_ITEM_TYPES)
        if bad_types:
            errors.append(f"unknown allowed_item_types: {', '.join(bad_types)}")

    sharing_rules = data.get("sharing_rules")
    if not isinstance(sharing_rules, dict):
        errors.append("sharing_rules must be an object.")
    else:
        if sharing_rules.get("owner_controls_sharing") is not True:
            errors.append("sharing_rules.owner_controls_sharing must be true.")
        if sharing_rules.get("private_notes_stay_private_by_default") is not True:
            errors.append("sharing_rules.private_notes_stay_private_by_default must be true.")
        if sharing_rules.get("robert_access_default") not in {"none", "summary_only", "owner_choice"}:
            errors.append("sharing_rules.robert_access_default must be none, summary_only, or owner_choice.")

    public_rules = data.get("public_export_rules")
    if not isinstance(public_rules, dict):
        errors.append("public_export_rules must be an object.")
    else:
        if public_rules.get("public_posting_allowed_now") is True:
            errors.append("public_export_rules.public_posting_allowed_now must be false at current stage.")
        for required_true in (
            "may_create_public_export_candidate",
            "requires_owner_approval",
            "requires_robert_review_at_current_stage",
            "must_filter_private_memory",
            "must_filter_robert_personal_info",
        ):
            if public_rules.get(required_true) is not True:
                errors.append(f"public_export_rules.{required_true} must be true.")

    items = data.get("items")
    if not isinstance(items, list):
        errors.append("items must be a list.")
    else:
        allowed_types = set(data.get("allowed_item_types", [])) if isinstance(data.get("allowed_item_types"), list) else set()
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"items[{index}] must be an object.")
                continue
            for field in ("item_id", "project_id", "title", "item_type", "visibility", "artifact_paths", "share_state", "private_notes_visible_to_robert", "public_export_candidate_id"):
                if field not in item:
                    errors.append(f"items[{index}].{field} is required.")
            if item.get("item_type") not in VALID_ITEM_TYPES:
                errors.append(f"items[{index}].item_type is unknown.")
            if allowed_types and item.get("item_type") not in allowed_types:
                errors.append(f"items[{index}].item_type is not allowed by this library.")
            if item.get("visibility") not in {"owner_only", "participants_only", "shared_with_robert", "shared_with_other_ai", "shared_library", "public_export_candidate"}:
                errors.append(f"items[{index}].visibility is invalid.")
            if item.get("share_state") not in VALID_SHARE_STATES:
                errors.append(f"items[{index}].share_state is invalid.")
            if not isinstance(item.get("artifact_paths"), list):
                errors.append(f"items[{index}].artifact_paths must be a list.")
            if item.get("private_notes_visible_to_robert") not in (True, False):
                errors.append(f"items[{index}].private_notes_visible_to_robert must be true or false.")
            if item.get("share_state") == "not_shared" and item.get("visibility") != "owner_only":
                errors.append(f"items[{index}] not_shared items must remain owner_only.")

    memory_policy = data.get("memory_policy")
    if not isinstance(memory_policy, dict):
        errors.append("memory_policy must be an object.")
    else:
        for required_true in (
            "library_items_are_not_lived_memories",
            "fictional_or_created_events_are_not_personal_history",
            "sharing_an_item_does_not_promote_memory",
        ):
            if memory_policy.get(required_true) is not True:
                errors.append(f"memory_policy.{required_true} must be true.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a private creative library JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_private_creative_library(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
