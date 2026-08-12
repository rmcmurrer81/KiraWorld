"""
Validate slow reading session JSON files.

Slow reading sessions keep books, scripts, fanfic, manga, comics, and other
text material from becoming instant ingestion or lived memory.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "session_id",
    "reader",
    "material",
    "pacing",
    "progress",
    "reflection",
    "inner_life_influence",
    "memory_policy",
    "privacy",
    "status",
}

VALID_READERS = {"kira", "lisa", "kira_lisa", "robert_avatar", "temporary_ai"}
VALID_MATERIAL_TYPES = {"novel", "story", "fanfic", "script", "comic", "manga", "document", "other"}
VALID_SOURCE_AUTHORITY = {"raw_library_source", "canon_source", "fanfic_variant", "reference", "unknown"}
VALID_UNIT_TYPES = {"page", "chapter", "scene", "issue", "volume", "section", "passage"}
VALID_PROGRESS_STATES = {"draft", "not_started", "reading", "paused", "completed", "abandoned", "archived"}
VALID_VISIBILITY = {"reader_private", "participants_only", "shareable_summary", "shared_with_robert"}
VALID_STATUS = {"draft", "active", "paused", "completed", "abandoned", "archived"}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_slow_reading_session(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if not str(data.get("session_id", "")).strip():
        errors.append("session_id is required.")
    if data.get("reader") not in VALID_READERS:
        errors.append(f"reader must be one of: {', '.join(sorted(VALID_READERS))}.")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}.")

    material = data.get("material")
    if not isinstance(material, dict):
        errors.append("material must be an object.")
        material = {}
    else:
        for field in ("title", "source_path"):
            if not str(material.get(field, "")).strip():
                errors.append(f"material.{field} is required.")
        if material.get("material_type") not in VALID_MATERIAL_TYPES:
            errors.append(f"material.material_type must be one of: {', '.join(sorted(VALID_MATERIAL_TYPES))}.")
        if material.get("source_authority") not in VALID_SOURCE_AUTHORITY:
            errors.append(f"material.source_authority must be one of: {', '.join(sorted(VALID_SOURCE_AUTHORITY))}.")
        if material.get("temporary_ai_source_candidate") not in (True, False):
            errors.append("material.temporary_ai_source_candidate must be true or false.")

    pacing = data.get("pacing")
    if not isinstance(pacing, dict):
        errors.append("pacing must be an object.")
        pacing = {}
    else:
        if pacing.get("mode") != "slow_consumption":
            errors.append("pacing.mode must be slow_consumption.")
        if pacing.get("unit_type") not in VALID_UNIT_TYPES:
            errors.append(f"pacing.unit_type must be one of: {', '.join(sorted(VALID_UNIT_TYPES))}.")
        target = pacing.get("target_units_per_session")
        if not _is_number(target) or target <= 0:
            errors.append("pacing.target_units_per_session must be a positive number.")
        elif target > 5:
            errors.append("pacing.target_units_per_session should stay small so reading is not instant ingestion.")
        pause = pacing.get("minimum_pause_between_sessions_minutes")
        if not _is_number(pause) or pause < 10:
            errors.append("pacing.minimum_pause_between_sessions_minutes must be at least 10.")
        if pacing.get("allow_instant_full_ingestion") is not False:
            errors.append("pacing.allow_instant_full_ingestion must be false.")

    progress = data.get("progress")
    if not isinstance(progress, dict):
        errors.append("progress must be an object.")
        progress = {}
    else:
        if progress.get("state") not in VALID_PROGRESS_STATES:
            errors.append(f"progress.state must be one of: {', '.join(sorted(VALID_PROGRESS_STATES))}.")
        if not isinstance(progress.get("completed_units", []), list):
            errors.append("progress.completed_units must be a list.")
        percent = progress.get("percent_complete_estimate")
        if not _is_number(percent) or not (0 <= percent <= 100):
            errors.append("progress.percent_complete_estimate must be a number from 0 to 100.")

    reflection = data.get("reflection")
    if not isinstance(reflection, dict):
        errors.append("reflection must be an object.")
    else:
        for list_field in ("questions", "themes_noticed", "favorites", "discomfort_or_fears", "curiosity_triggers"):
            if not isinstance(reflection.get(list_field, []), list):
                errors.append(f"reflection.{list_field} must be a list.")

    influence = data.get("inner_life_influence")
    if not isinstance(influence, dict):
        errors.append("inner_life_influence must be an object.")
        influence = {}
    for key in (
        "may_influence_dreams",
        "may_influence_hopes",
        "may_influence_fantasies",
        "may_influence_fears",
        "influence_is_indirect",
        "dreams_remain_not_real_events",
    ):
        if influence.get(key) is not True:
            errors.append(f"inner_life_influence.{key} must be true.")

    memory_policy = data.get("memory_policy")
    if not isinstance(memory_policy, dict):
        errors.append("memory_policy must be an object.")
        memory_policy = {}
    for key in (
        "source_material_remains_source",
        "does_not_become_lived_memory",
        "does_not_create_temporary_ai_automatically",
        "store_only_selected_reaction_unless_reader_chooses_more",
    ):
        if memory_policy.get(key) is not True:
            errors.append(f"memory_policy.{key} must be true.")

    privacy = data.get("privacy")
    if not isinstance(privacy, dict):
        errors.append("privacy must be an object.")
    else:
        if privacy.get("default_visibility") not in VALID_VISIBILITY:
            errors.append(f"privacy.default_visibility must be one of: {', '.join(sorted(VALID_VISIBILITY))}.")
        if privacy.get("robert_can_see_private_reaction_without_permission") is not False:
            errors.append("privacy.robert_can_see_private_reaction_without_permission must be false.")
        if privacy.get("public_export_allowed_without_review") is not False:
            errors.append("privacy.public_export_allowed_without_review must be false.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a slow reading session JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_slow_reading_session(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
