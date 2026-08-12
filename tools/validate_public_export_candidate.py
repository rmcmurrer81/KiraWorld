"""
Validate public export candidate JSON files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "export_id",
    "title",
    "created_by",
    "content_type",
    "source_world_id",
    "visibility_scope",
    "autonomy_state",
    "privacy_review",
    "content_notes",
    "approval",
    "status",
}

VALID_CREATORS = {"kira", "lisa", "kira_lisa", "robert"}
VALID_CONTENT_TYPES = {"image", "video", "short", "post", "livestream_plan"}
VALID_VISIBILITY = {"public_export_candidate", "approved_public"}
VALID_AUTONOMY = {"manual_only", "request_mode", "approved_autonomy", "mature_autonomy"}
VALID_STATUS = {"draft", "needs_review", "approved", "posted", "archived"}


def _expect_object(data: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object.")
        return {}
    return value


def validate_public_export_candidate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if not data.get("export_id"):
        errors.append("export_id is required.")
    if not data.get("title"):
        errors.append("title is required.")
    if data.get("created_by") not in VALID_CREATORS:
        errors.append(f"created_by must be one of: {', '.join(sorted(VALID_CREATORS))}")
    if data.get("content_type") not in VALID_CONTENT_TYPES:
        errors.append(f"content_type must be one of: {', '.join(sorted(VALID_CONTENT_TYPES))}")
    if data.get("visibility_scope") not in VALID_VISIBILITY:
        errors.append(f"visibility_scope must be one of: {', '.join(sorted(VALID_VISIBILITY))}")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")

    autonomy = _expect_object(data, "autonomy_state", errors)
    if autonomy:
        current_level = autonomy.get("current_level")
        if current_level not in VALID_AUTONOMY:
            errors.append(f"autonomy_state.current_level must be one of: {', '.join(sorted(VALID_AUTONOMY))}")
        if autonomy.get("posting_without_robert_permission_allowed") is True and current_level != "mature_autonomy":
            errors.append("posting without Robert permission requires mature_autonomy.")

    privacy = _expect_object(data, "privacy_review", errors)
    if privacy:
        private_flags = [
            "contains_private_memory",
            "contains_robert_personal_info",
            "contains_kira_lisa_private_content",
        ]
        for key in private_flags:
            if not isinstance(privacy.get(key), bool):
                errors.append(f"privacy_review.{key} must be true or false.")
        if any(privacy.get(key) is True for key in private_flags):
            if not privacy.get("redactions_needed"):
                errors.append("exports containing private material must list redactions_needed.")

    approval = _expect_object(data, "approval", errors)
    if approval:
        requires_robert = approval.get("robert_approval_required_now")
        post_allowed = bool(autonomy.get("posting_without_robert_permission_allowed")) if autonomy else False
        if requires_robert is not True and not post_allowed:
            errors.append("Robert approval is required unless mature posting autonomy is active.")
        if data.get("status") in {"approved", "posted"} and requires_robert is True and not approval.get("approved_at"):
            errors.append("approved or posted exports requiring Robert approval must include approved_at.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a public export candidate JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_public_export_candidate(data)
    if errors:
        print(f"{path} is not ready for approval:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"{path} is structurally ready for review.")


if __name__ == "__main__":
    main()
