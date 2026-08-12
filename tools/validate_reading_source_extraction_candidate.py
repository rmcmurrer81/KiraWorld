"""
Validate reading source extraction candidate JSON files.

These records bridge slow reading into possible TemporaryAI profile drafts or
notebook world source plans without automatically creating either one.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "candidate_id",
    "created_from",
    "reader_interest",
    "source_material",
    "character_profile_candidates",
    "place_reconstruction_candidates",
    "safety_review",
    "memory_policy",
    "approval",
    "status",
}

VALID_SOURCE_TYPES = {"slow_reading_session", "media_viewing_note", "manual_library_scan_request"}
VALID_READERS = {"kira", "lisa", "kira_lisa", "robert_avatar", "temporary_ai"}
VALID_INTEREST_TYPES = {"character", "place", "character_and_place", "theme", "temporary_ai", "notebook_world"}
VALID_MATERIAL_TYPES = {"novel", "story", "fanfic", "script", "comic", "manga", "document", "other"}
VALID_SOURCE_AUTHORITY = {"raw_library_source", "canon_source", "fanfic_variant", "reference", "unknown"}
VALID_PROFILE_GOALS = {"possible_temporary_ai", "source_note_only", "relationship_tree_only"}
VALID_WORLD_GOALS = {"possible_notebook_world", "source_note_only", "visual_reference_only"}
VALID_STATUS = {"draft", "needs_review", "approved_for_profile_draft", "approved_for_world_plan", "blocked", "archived"}


def _require_bool(errors: list[str], data: dict[str, Any], key: str, expected: bool, prefix: str) -> None:
    if data.get(key) is not expected:
        errors.append(f"{prefix}.{key} must be {str(expected).lower()}.")


def validate_reading_source_extraction_candidate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if not str(data.get("candidate_id", "")).strip():
        errors.append("candidate_id is required.")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}.")

    created_from = data.get("created_from")
    if not isinstance(created_from, dict):
        errors.append("created_from must be an object.")
        created_from = {}
    else:
        if created_from.get("source_type") not in VALID_SOURCE_TYPES:
            errors.append(f"created_from.source_type must be one of: {', '.join(sorted(VALID_SOURCE_TYPES))}.")
        for field in ("source_id", "source_path"):
            if not str(created_from.get(field, "")).strip():
                errors.append(f"created_from.{field} is required.")

    interest = data.get("reader_interest")
    if not isinstance(interest, dict):
        errors.append("reader_interest must be an object.")
        interest = {}
    else:
        if interest.get("reader") not in VALID_READERS:
            errors.append(f"reader_interest.reader must be one of: {', '.join(sorted(VALID_READERS))}.")
        if interest.get("interest_type") not in VALID_INTEREST_TYPES:
            errors.append(f"reader_interest.interest_type must be one of: {', '.join(sorted(VALID_INTEREST_TYPES))}.")
        if not str(interest.get("interest_summary", "")).strip():
            errors.append("reader_interest.interest_summary is required.")
        for key in ("reader_may_keep_private", "reader_may_request_temporary_ai_later", "reader_may_request_notebook_world_later"):
            _require_bool(errors, interest, key, True, "reader_interest")

    source = data.get("source_material")
    if not isinstance(source, dict):
        errors.append("source_material must be an object.")
        source = {}
    else:
        for field in ("title", "source_path", "canon_or_variant_status"):
            if not str(source.get(field, "")).strip():
                errors.append(f"source_material.{field} is required.")
        if source.get("material_type") not in VALID_MATERIAL_TYPES:
            errors.append(f"source_material.material_type must be one of: {', '.join(sorted(VALID_MATERIAL_TYPES))}.")
        if source.get("source_authority") not in VALID_SOURCE_AUTHORITY:
            errors.append(f"source_material.source_authority must be one of: {', '.join(sorted(VALID_SOURCE_AUTHORITY))}.")
        _require_bool(errors, source, "requires_content_scan", True, "source_material")

    characters = data.get("character_profile_candidates")
    if not isinstance(characters, list):
        errors.append("character_profile_candidates must be a list.")
        characters = []
    for index, character in enumerate(characters):
        if not isinstance(character, dict):
            errors.append(f"character_profile_candidates[{index}] must be an object.")
            continue
        if not str(character.get("character_name", "")).strip():
            errors.append(f"character_profile_candidates[{index}].character_name is required.")
        if character.get("profile_goal") not in VALID_PROFILE_GOALS:
            errors.append(f"character_profile_candidates[{index}].profile_goal must be one of: {', '.join(sorted(VALID_PROFILE_GOALS))}.")
        if not isinstance(character.get("source_evidence_needed"), list) or not character.get("source_evidence_needed"):
            errors.append(f"character_profile_candidates[{index}].source_evidence_needed must be a non-empty list.")
        age_review = character.get("age_review")
        if not isinstance(age_review, dict):
            errors.append(f"character_profile_candidates[{index}].age_review must be an object.")
        else:
            _require_bool(errors, age_review, "adult_or_intimate_use_blocked_until_review", True, f"character_profile_candidates[{index}].age_review")
        policy = character.get("temporary_ai_policy")
        if not isinstance(policy, dict):
            errors.append(f"character_profile_candidates[{index}].temporary_ai_policy must be an object.")
        else:
            for key in ("does_not_activate_ai", "requires_separate_temporary_ai_request", "source_faithfulness_required", "fanfic_must_not_overwrite_canon"):
                _require_bool(errors, policy, key, True, f"character_profile_candidates[{index}].temporary_ai_policy")

    places = data.get("place_reconstruction_candidates")
    if not isinstance(places, list):
        errors.append("place_reconstruction_candidates must be a list.")
        places = []
    for index, place in enumerate(places):
        if not isinstance(place, dict):
            errors.append(f"place_reconstruction_candidates[{index}] must be an object.")
            continue
        if not str(place.get("place_name", "")).strip():
            errors.append(f"place_reconstruction_candidates[{index}].place_name is required.")
        if place.get("world_goal") not in VALID_WORLD_GOALS:
            errors.append(f"place_reconstruction_candidates[{index}].world_goal must be one of: {', '.join(sorted(VALID_WORLD_GOALS))}.")
        if not isinstance(place.get("source_evidence_needed"), list) or not place.get("source_evidence_needed"):
            errors.append(f"place_reconstruction_candidates[{index}].source_evidence_needed must be a non-empty list.")
        policy = place.get("notebook_world_policy")
        if not isinstance(policy, dict):
            errors.append(f"place_reconstruction_candidates[{index}].notebook_world_policy must be an object.")
        else:
            for key in ("does_not_create_world_automatically", "requires_separate_notebook_world_request", "can_be_private_by_default", "must_label_inferred_details"):
                _require_bool(errors, policy, key, True, f"place_reconstruction_candidates[{index}].notebook_world_policy")

    safety = data.get("safety_review")
    if not isinstance(safety, dict):
        errors.append("safety_review must be an object.")
        safety = {}
    for key in (
        "scan_for_minor_or_unclear_age",
        "scan_for_adult_or_private_content",
        "scan_for_drug_use_or_manipulation_or_violence",
        "scan_for_fanfic_variant_risk",
        "scan_for_source_conflicts",
        "block_private_adult_use_until_review",
    ):
        _require_bool(errors, safety, key, True, "safety_review")

    memory = data.get("memory_policy")
    if not isinstance(memory, dict):
        errors.append("memory_policy must be an object.")
        memory = {}
    for key in (
        "source_material_remains_source",
        "does_not_become_lived_memory",
        "reader_liking_character_is_not_relationship_memory",
        "reader_dream_or_fantasy_is_not_source_canon",
        "does_not_create_temporary_ai_automatically",
        "does_not_create_notebook_world_automatically",
    ):
        _require_bool(errors, memory, key, True, "memory_policy")

    approval = data.get("approval")
    if not isinstance(approval, dict):
        errors.append("approval must be an object.")
        approval = {}
    for key in (
        "profile_extraction_requires_review",
        "temporary_ai_creation_requires_separate_request",
        "notebook_world_creation_requires_separate_request",
        "robert_approval_required_current_stage",
        "kira_lisa_private_interest_may_remain_private",
    ):
        _require_bool(errors, approval, key, True, "approval")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a reading source extraction candidate JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_reading_source_extraction_candidate(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
