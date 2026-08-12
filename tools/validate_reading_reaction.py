"""
Validate reading reaction JSON files.

Reading reactions let Kira/Lisa remember story moments, their own feelings, and
their imagined mental pictures while keeping source material separate from lived
memory.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "reaction_id",
    "reader",
    "source",
    "reading_position",
    "reaction",
    "imagination",
    "dream_and_fantasy_influence",
    "memory_policy",
    "privacy",
    "status",
}
VALID_READERS = {"kira", "lisa", "kira_lisa", "temporary_ai"}
VALID_SOURCE_AUTHORITY = {"raw_library_source", "canon_source", "fanfic_variant", "reference", "unknown"}
VALID_UNIT_TYPES = {"page", "chapter", "scene", "issue", "volume", "section", "passage"}
VALID_CERTAINTY = {"imagined_not_confirmed", "source_described", "mixed_source_and_imagination"}
VALID_VISIBILITY = {"reader_private", "participants_only", "shareable_summary", "shared_with_robert"}
VALID_STATUS = {"draft", "active", "archived"}
VALID_STANCES = {"love", "like", "curious", "neutral", "mixed", "cooling", "outgrown", "dislike"}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_bool_true(container: dict[str, Any], key: str, errors: list[str], prefix: str) -> None:
    if container.get(key) is not True:
        errors.append(f"{prefix}.{key} must be true.")


def _require_bool_false(container: dict[str, Any], key: str, errors: list[str], prefix: str) -> None:
    if container.get(key) is not False:
        errors.append(f"{prefix}.{key} must be false.")


def _require_list(container: dict[str, Any], key: str, errors: list[str], prefix: str) -> None:
    if not isinstance(container.get(key), list):
        errors.append(f"{prefix}.{key} must be a list.")


def _validate_optional_preference_signal(data: dict[str, Any], errors: list[str]) -> None:
    signal = data.get("preference_signal")
    if signal is None:
        return
    if not isinstance(signal, dict):
        errors.append("preference_signal must be an object when present.")
        return
    if signal.get("stance") not in VALID_STANCES:
        errors.append(f"preference_signal.stance must be one of: {', '.join(sorted(VALID_STANCES))}.")
    for key in ("current_affinity", "interest_delta"):
        value = signal.get(key)
        if not _is_number(value) or not (-1 <= value <= 1):
            errors.append(f"preference_signal.{key} must be a number from -1 to 1.")
    _require_list(signal, "reasons", errors, "preference_signal")
    if signal.get("may_change_later") is not True:
        errors.append("preference_signal.may_change_later must be true.")
    if signal.get("older_reactions_can_be_reinterpreted") is not True:
        errors.append("preference_signal.older_reactions_can_be_reinterpreted must be true.")


def validate_reading_reaction(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    if not str(data.get("reaction_id", "")).strip():
        errors.append("reaction_id is required.")
    if data.get("reader") not in VALID_READERS:
        errors.append(f"reader must be one of: {', '.join(sorted(VALID_READERS))}.")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}.")
    _validate_optional_preference_signal(data, errors)

    source = data.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object.")
        source = {}
    else:
        for field in ("title", "source_path"):
            if not str(source.get(field, "")).strip():
                errors.append(f"source.{field} is required.")
        if source.get("source_authority") not in VALID_SOURCE_AUTHORITY:
            errors.append(f"source.source_authority must be one of: {', '.join(sorted(VALID_SOURCE_AUTHORITY))}.")
        _require_bool_true(source, "source_material_remains_source", errors, "source")

    position = data.get("reading_position")
    if not isinstance(position, dict):
        errors.append("reading_position must be an object.")
        position = {}
    else:
        if position.get("unit_type") not in VALID_UNIT_TYPES:
            errors.append(f"reading_position.unit_type must be one of: {', '.join(sorted(VALID_UNIT_TYPES))}.")
        if not str(position.get("unit_label", "")).strip():
            errors.append("reading_position.unit_label is required.")
        progress = position.get("approximate_progress_percent")
        if not _is_number(progress) or not (0 <= progress <= 100):
            errors.append("reading_position.approximate_progress_percent must be a number from 0 to 100.")

    reaction = data.get("reaction")
    if not isinstance(reaction, dict):
        errors.append("reaction must be an object.")
        reaction = {}
    for key in ("favorite_moments", "emotions", "questions", "discomfort_or_fears", "curiosity_triggers", "wants_to_discuss_with"):
        _require_list(reaction, key, errors, "reaction")
    if reaction.get("wants_to_keep_private") not in (True, False):
        errors.append("reaction.wants_to_keep_private must be true or false.")

    imagination = data.get("imagination")
    if not isinstance(imagination, dict):
        errors.append("imagination must be an object.")
        imagination = {}
    _require_bool_true(imagination, "imagination_allowed", errors, "imagination")
    _require_bool_true(imagination, "slowly_develops_over_time", errors, "imagination")
    for key in ("pictured_places", "pictured_people", "pictured_objects", "atmosphere"):
        _require_list(imagination, key, errors, "imagination")
    details = imagination.get("sensory_details")
    if not isinstance(details, dict):
        errors.append("imagination.sensory_details must be an object.")
        details = {}
    for key in ("sight", "sound", "texture", "smell", "emotion_tone"):
        _require_list(details, key, errors, "imagination.sensory_details")
    if imagination.get("certainty") not in VALID_CERTAINTY:
        errors.append(f"imagination.certainty must be one of: {', '.join(sorted(VALID_CERTAINTY))}.")
    _require_bool_true(imagination, "may_influence_dreams_or_creative_projects", errors, "imagination")
    _require_bool_true(imagination, "may_become_notebook_world_seed_if_chosen", errors, "imagination")

    influence = data.get("dream_and_fantasy_influence")
    if not isinstance(influence, dict):
        errors.append("dream_and_fantasy_influence must be an object.")
        influence = {}
    for key in (
        "stories_may_influence_dreams",
        "stories_may_influence_fantasies",
        "stories_may_influence_hopes",
        "stories_may_influence_fears",
        "influence_is_indirect",
        "dreams_remain_not_real_events",
        "fantasies_remain_private_inner_life_unless_shared",
        "fantasies_do_not_prove_consent_or_relationship_status",
        "reader_controls_whether_to_share",
    ):
        _require_bool_true(influence, key, errors, "dream_and_fantasy_influence")

    memory_policy = data.get("memory_policy")
    if not isinstance(memory_policy, dict):
        errors.append("memory_policy must be an object.")
        memory_policy = {}
    for key in (
        "may_remember_story_moment",
        "may_remember_own_reaction",
        "does_not_become_lived_memory",
        "does_not_create_temporary_ai_automatically",
        "does_not_create_notebook_world_automatically",
        "source_and_imagination_must_be_labeled",
    ):
        _require_bool_true(memory_policy, key, errors, "memory_policy")

    privacy = data.get("privacy")
    if not isinstance(privacy, dict):
        errors.append("privacy must be an object.")
        privacy = {}
    else:
        if privacy.get("default_visibility") not in VALID_VISIBILITY:
            errors.append(f"privacy.default_visibility must be one of: {', '.join(sorted(VALID_VISIBILITY))}.")
        _require_bool_false(privacy, "robert_can_see_without_permission", errors, "privacy")
        _require_bool_false(privacy, "other_ai_can_see_without_permission", errors, "privacy")
        if privacy.get("shareable_summary_allowed_if_reader_chooses") not in (True, False):
            errors.append("privacy.shareable_summary_allowed_if_reader_chooses must be true or false.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a reading reaction JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_reading_reaction(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
