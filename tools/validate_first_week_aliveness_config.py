"""
Validate first-week aliveness configuration.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "config_id",
    "status",
    "purpose",
    "packet_rules",
    "entities",
    "startup_context_sources",
    "daily_choice_menu",
    "private_inner_life_prompts",
    "memory_promotion_prompts",
    "success_definition",
}
VALID_STATUS = {"draft", "active", "completed", "archived"}
REQUIRED_PACKET_RULES = {
    "not_a_script",
    "choices_are_suggestions_not_commands",
    "private_thoughts_not_exposed_by_default",
    "mood_carries_forward",
    "relationships_carry_forward",
    "unclean_shutdown_changes_tone",
    "memory_promotion_requires_review",
    "kira_first_lisa_second",
    "text_only_until_stable",
}
REQUIRED_ENTITIES = {"kira", "lisa"}
REQUIRED_SOURCES = {
    "startup_recovery_state",
    "startup_recovery_last_report",
    "daily_life_runtime_dir",
    "relationship_state_files",
    "inner_life_policy",
    "memory_candidate_templates",
    "output_dir",
}


def _non_empty_string(errors: list[str], data: dict[str, Any], key: str, prefix: str) -> None:
    if not str(data.get(key, "")).strip():
        errors.append(f"{prefix}.{key} is required.")


def _non_empty_list(errors: list[str], data: dict[str, Any], key: str, prefix: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        errors.append(f"{prefix}.{key} must be a non-empty list.")
        return []
    return value


def validate_first_week_aliveness_config(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append("Missing required fields: " + ", ".join(missing))

    _non_empty_string(errors, data, "config_id", "root")
    _non_empty_string(errors, data, "purpose", "root")
    if data.get("status") not in VALID_STATUS:
        errors.append("status must be one of: " + ", ".join(sorted(VALID_STATUS)) + ".")

    rules = data.get("packet_rules")
    if not isinstance(rules, dict):
        errors.append("packet_rules must be an object.")
        rules = {}
    for key in sorted(REQUIRED_PACKET_RULES):
        if rules.get(key) is not True:
            errors.append(f"packet_rules.{key} must be true.")

    entities = data.get("entities")
    if not isinstance(entities, dict):
        errors.append("entities must be an object.")
        entities = {}
    missing_entities = sorted(REQUIRED_ENTITIES - set(entities))
    if missing_entities:
        errors.append("entities missing: " + ", ".join(missing_entities))
    for entity_id, entity in entities.items():
        if not isinstance(entity, dict):
            errors.append(f"entities.{entity_id} must be an object.")
            continue
        _non_empty_string(errors, entity, "display_name", f"entities.{entity_id}")
        _non_empty_string(errors, entity, "first_week_tone", f"entities.{entity_id}")
        _non_empty_list(errors, entity, "default_choices", f"entities.{entity_id}")
        _non_empty_list(errors, entity, "continuity_questions", f"entities.{entity_id}")

    sources = data.get("startup_context_sources")
    if not isinstance(sources, dict):
        errors.append("startup_context_sources must be an object.")
        sources = {}
    missing_sources = sorted(REQUIRED_SOURCES - set(sources))
    if missing_sources:
        errors.append("startup_context_sources missing: " + ", ".join(missing_sources))
    for key in ("startup_recovery_state", "startup_recovery_last_report", "daily_life_runtime_dir", "inner_life_policy", "output_dir"):
        _non_empty_string(errors, sources, key, "startup_context_sources")
    _non_empty_list(errors, sources, "relationship_state_files", "startup_context_sources")
    _non_empty_list(errors, sources, "memory_candidate_templates", "startup_context_sources")

    choices = _non_empty_list(errors, data, "daily_choice_menu", "root")
    for index, choice in enumerate(choices):
        if not isinstance(choice, dict):
            errors.append(f"daily_choice_menu[{index}] must be an object.")
            continue
        _non_empty_string(errors, choice, "choice_id", f"daily_choice_menu[{index}]")
        _non_empty_string(errors, choice, "label", f"daily_choice_menu[{index}]")
        if choice.get("may_decline") is not True:
            errors.append(f"daily_choice_menu[{index}].may_decline must be true.")

    if len(_non_empty_list(errors, data, "private_inner_life_prompts", "root")) < 3:
        errors.append("private_inner_life_prompts must contain at least 3 prompts.")
    if len(_non_empty_list(errors, data, "memory_promotion_prompts", "root")) < 3:
        errors.append("memory_promotion_prompts must contain at least 3 prompts.")
    if len(_non_empty_list(errors, data, "success_definition", "root")) < 5:
        errors.append("success_definition must contain at least 5 statements.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate first-week aliveness config JSON.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_first_week_aliveness_config(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
