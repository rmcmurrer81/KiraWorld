"""
Validate Kira/Lisa reading interest profiles.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


VALID_OWNERS = {"kira", "lisa", "kira_lisa"}
VALID_STATUS = {"draft", "active", "archived"}
REQUIRED_FIELDS = {
    "profile_id",
    "owner",
    "current_interests",
    "preferred_categories",
    "theme_weights",
    "avoid_when_mood",
    "rotation_policy",
    "privacy",
    "status",
}


def validate_reading_interest_profile(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    if not str(data.get("profile_id", "")).strip():
        errors.append("profile_id is required.")
    if data.get("owner") not in VALID_OWNERS:
        errors.append(f"owner must be one of: {', '.join(sorted(VALID_OWNERS))}.")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}.")

    interests = data.get("current_interests")
    if not isinstance(interests, dict):
        errors.append("current_interests must be an object.")
        interests = {}
    for key in ("themes", "genres", "questions", "active_source_paths"):
        if not isinstance(interests.get(key), list):
            errors.append(f"current_interests.{key} must be a list.")
    if "favorite_source_paths" in interests and not isinstance(interests.get("favorite_source_paths"), list):
        errors.append("current_interests.favorite_source_paths must be a list when present.")
    if "historical_context_source_paths" in interests and not isinstance(interests.get("historical_context_source_paths"), list):
        errors.append("current_interests.historical_context_source_paths must be a list when present.")

    if not isinstance(data.get("preferred_categories"), list) or not data.get("preferred_categories"):
        errors.append("preferred_categories must be a non-empty list.")

    weights = data.get("theme_weights")
    if not isinstance(weights, dict) or not weights:
        errors.append("theme_weights must be a non-empty object.")
    else:
        for key, value in weights.items():
            if not isinstance(key, str) or not key.strip():
                errors.append("theme_weights keys must be non-empty strings.")
            if not isinstance(value, int) or isinstance(value, bool) or not (0 <= value <= 10):
                errors.append(f"theme_weights.{key} must be an integer from 0 to 10.")

    avoid = data.get("avoid_when_mood")
    if not isinstance(avoid, dict):
        errors.append("avoid_when_mood must be an object.")
    else:
        for key, value in avoid.items():
            if not isinstance(key, str) or not isinstance(value, list):
                errors.append("avoid_when_mood values must be lists.")

    rotation = data.get("rotation_policy")
    if not isinstance(rotation, dict):
        errors.append("rotation_policy must be an object.")
        rotation = {}
    for key in ("max_active_private_sessions", "max_active_shared_sessions"):
        value = rotation.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"rotation_policy.{key} must be a non-negative integer.")
    if rotation.get("include_new_arrivals") is not True:
        errors.append("rotation_policy.include_new_arrivals must be true.")
    if rotation.get("allow_rereading_favorites") is not True:
        errors.append("rotation_policy.allow_rereading_favorites must be true.")
    if rotation.get("reread_requires_reader_choice") is not True:
        errors.append("rotation_policy.reread_requires_reader_choice must be true.")
    if rotation.get("do_not_force_recommendations") is not True:
        errors.append("rotation_policy.do_not_force_recommendations must be true.")
    if not isinstance(rotation.get("mix_modes"), list) or not rotation.get("mix_modes"):
        errors.append("rotation_policy.mix_modes must be a non-empty list.")

    privacy = data.get("privacy")
    if not isinstance(privacy, dict):
        errors.append("privacy must be an object.")
    elif privacy.get("private_preferences_require_owner_permission") is not True:
        errors.append("privacy.private_preferences_require_owner_permission must be true.")

    return errors


def validate_profile_file(data: Any) -> list[str]:
    if not isinstance(data, list) or not data:
        return ["profile file must contain a non-empty list."]
    errors: list[str] = []
    seen = set()
    for index, profile in enumerate(data):
        if not isinstance(profile, dict):
            errors.append(f"profile[{index}] must be an object.")
            continue
        profile_id = str(profile.get("profile_id", ""))
        if profile_id in seen:
            errors.append(f"profile[{index}].profile_id is duplicated.")
        seen.add(profile_id)
        for error in validate_reading_interest_profile(profile):
            errors.append(f"profile[{index}]: {error}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate reading interest profile JSON.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_profile_file(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
