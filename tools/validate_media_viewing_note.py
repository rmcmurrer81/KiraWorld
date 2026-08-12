"""
Validate a media viewing/listening/reading note.

Media notes record reactions and preferences. They are not lived memories,
canon records, or Temporary AI profiles.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "note_id",
    "viewer",
    "media_title",
    "media_type",
    "source_path_or_service",
    "access_mode",
    "reaction_summary",
    "memory_policy",
    "privacy",
    "status",
}

VALID_VIEWERS = {"kira", "lisa", "kira_lisa", "robert_avatar", "other"}
VALID_MEDIA_TYPES = {
    "movie",
    "show",
    "episode",
    "youtube_video",
    "music_video",
    "livestream",
    "local_video",
    "music",
    "script",
    "story",
    "novel",
    "document",
    "other",
}
VALID_ACCESS_MODES = {
    "watched",
    "listened",
    "read",
    "read_script",
    "read_summary",
    "heard_about",
    "mixed",
}
VALID_VISIBILITY = {"owner_only", "participants_only", "shared_with_robert", "public_summary"}
VALID_STATUS = {"draft", "active", "archived"}


def validate_media_viewing_note(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if data.get("viewer") not in VALID_VIEWERS:
        errors.append(f"viewer must be one of: {', '.join(sorted(VALID_VIEWERS))}")
    if data.get("media_type") not in VALID_MEDIA_TYPES:
        errors.append(f"media_type must be one of: {', '.join(sorted(VALID_MEDIA_TYPES))}")
    if data.get("access_mode") not in VALID_ACCESS_MODES:
        errors.append(f"access_mode must be one of: {', '.join(sorted(VALID_ACCESS_MODES))}")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")

    for field in ("note_id", "media_title", "source_path_or_service", "reaction_summary"):
        if not str(data.get(field, "")).strip():
            errors.append(f"{field} is required.")

    memory_policy = data.get("memory_policy")
    if not isinstance(memory_policy, dict):
        errors.append("memory_policy must be an object.")
    else:
        required_true = {
            "does_not_become_lived_memory",
            "does_not_create_temporary_ai_automatically",
            "source_material_remains_source",
        }
        for key in sorted(required_true):
            if memory_policy.get(key) is not True:
                errors.append(f"memory_policy.{key} must be true.")

    privacy = data.get("privacy")
    if not isinstance(privacy, dict):
        errors.append("privacy must be an object.")
    else:
        visibility = privacy.get("default_visibility")
        if visibility not in VALID_VISIBILITY:
            errors.append(f"privacy.default_visibility must be one of: {', '.join(sorted(VALID_VISIBILITY))}")
        if privacy.get("public_export_allowed_without_review") is True:
            errors.append("media notes cannot allow public export without review.")
        if visibility == "owner_only" and privacy.get("may_share_summary") is not True:
            errors.append("owner_only notes should still allow an owner-approved summary share.")

    for optional_list in ("emotional_reactions", "questions"):
        if optional_list in data and not isinstance(data[optional_list], list):
            errors.append(f"{optional_list} must be a list.")

    preferences = data.get("preferences")
    if preferences is not None and not isinstance(preferences, dict):
        errors.append("preferences must be an object when present.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a media viewing note JSON file.")
    parser.add_argument("path", help="Path to media viewing note JSON.")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_media_viewing_note(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
