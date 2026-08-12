"""
Validate creative project JSON files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "project_id",
    "owner",
    "title",
    "project_type",
    "linked_skills",
    "origin",
    "work_state",
    "privacy",
    "sharing_options",
    "public_export_policy",
    "memory_policy",
    "status",
}
VALID_OWNERS = {"kira", "lisa", "shared_kira_lisa"}
VALID_PROJECT_TYPES = {
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
VALID_STATUS = {
    "idea",
    "drafting",
    "private_review",
    "shared_with_robert",
    "public_export_candidate",
    "published_future",
    "paused",
    "archived",
}


def validate_creative_project(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    if not str(data.get("project_id", "")).strip():
        errors.append("project_id is required.")
    if data.get("owner") not in VALID_OWNERS:
        errors.append(f"owner must be one of: {', '.join(sorted(VALID_OWNERS))}")
    if data.get("project_type") not in VALID_PROJECT_TYPES:
        errors.append(f"project_type must be one of: {', '.join(sorted(VALID_PROJECT_TYPES))}")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")
    if "linked_skills" in data and not isinstance(data.get("linked_skills"), list):
        errors.append("linked_skills must be a list.")

    for object_field in ("origin", "work_state", "privacy", "sharing_options", "public_export_policy", "memory_policy"):
        if object_field in data and not isinstance(data.get(object_field), dict):
            errors.append(f"{object_field} must be an object.")

    privacy = data.get("privacy", {})
    if isinstance(privacy, dict):
        if privacy.get("default_visibility") not in {"owner_only", "participants_only", "shared_with_robert", "public_candidate"}:
            errors.append("privacy.default_visibility must be owner_only, participants_only, shared_with_robert, or public_candidate.")
        if privacy.get("private_notes_visible_to_robert") not in (True, False):
            errors.append("privacy.private_notes_visible_to_robert must be true or false.")

    sharing = data.get("sharing_options", {})
    if isinstance(sharing, dict):
        for key in ("may_invite_robert_to_watch", "may_read_to_robert", "may_share_summary", "may_keep_private", "may_share_with_other_ai"):
            if sharing.get(key) not in (True, False):
                errors.append(f"sharing_options.{key} must be true or false.")

    public_policy = data.get("public_export_policy", {})
    if isinstance(public_policy, dict):
        for key in (
            "public_posting_allowed_now",
            "may_create_public_export_candidate",
            "requires_robert_review_at_current_stage",
            "requires_owner_approval",
            "must_filter_private_memory",
            "must_filter_robert_personal_info",
        ):
            if public_policy.get(key) not in (True, False):
                errors.append(f"public_export_policy.{key} must be true or false.")
        if public_policy.get("public_posting_allowed_now") is True:
            errors.append("public_export_policy.public_posting_allowed_now must be false at current stage.")
        for required_true in ("requires_robert_review_at_current_stage", "requires_owner_approval", "must_filter_private_memory", "must_filter_robert_personal_info"):
            if public_policy.get(required_true) is not True:
                errors.append(f"public_export_policy.{required_true} must be true.")

    memory_policy = data.get("memory_policy", {})
    if isinstance(memory_policy, dict):
        for required_true in ("draft_is_not_lived_memory", "fictional_events_are_not_personal_history", "conversation_about_project_not_auto_memory"):
            if memory_policy.get(required_true) is not True:
                errors.append(f"memory_policy.{required_true} must be true.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a creative project JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_creative_project(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
