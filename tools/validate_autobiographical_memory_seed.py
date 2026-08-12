"""
Validate autobiographical memory seed JSON files.

This format is intentionally more human than the older one-seed-per-anchor
files. It allows soft reconstruction and disputed details, while requiring the
file to say what is hard canon, what is perspective, and what must not be
turned into exact fact without review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "seed_id",
    "owner",
    "status",
    "purpose",
    "memory_philosophy",
    "growth_policy",
    "identity_timeline",
    "autobiographical_memories",
    "cross_memory_gap_filling",
    "forbidden_uses",
}

REQUIRED_MEMORY_FIELDS = {
    "memory_id",
    "title",
    "phase",
    "participants",
    "privacy_level",
    "linked_seed_files",
    "canon_anchors",
    "owner_perspective",
    "other_perspectives",
    "disputed_or_variable_details",
    "known_unknowns",
    "allowed_gap_filling",
    "forbidden_hard_claims",
    "growth_hooks",
}

VALID_STATUSES = {"draft", "ready_for_review", "approved", "archived"}
VALID_PRIVACY_PREFIXES = {"public", "private", "private_shared", "private_shared_locked", "locked"}


def _is_non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        found: list[str] = []
        for item in value:
            found.extend(_strings(item))
        return found
    if isinstance(value, dict):
        found = []
        for item in value.values():
            found.extend(_strings(item))
        return found
    return []


def validate_autobiographical_seed(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append("Missing required fields: " + ", ".join(missing))

    if not str(data.get("seed_id", "")).strip():
        errors.append("seed_id is required.")
    if not str(data.get("owner", "")).strip():
        errors.append("owner is required.")
    if data.get("status") not in VALID_STATUSES:
        errors.append("status must be one of: " + ", ".join(sorted(VALID_STATUSES)))

    philosophy = data.get("memory_philosophy", {})
    if not isinstance(philosophy, dict):
        errors.append("memory_philosophy must be an object.")
        philosophy = {}
    for field in ("hard_anchor_rule", "soft_memory_rule", "disputed_memory_rule", "growth_rule"):
        if not str(philosophy.get(field, "")).strip():
            errors.append(f"memory_philosophy.{field} is required.")

    growth = data.get("growth_policy", {})
    if not isinstance(growth, dict):
        errors.append("growth_policy must be an object.")
        growth = {}
    if growth.get("may_fill_gaps_between_memories") is not True:
        errors.append("growth_policy.may_fill_gaps_between_memories must be true.")
    if str(growth.get("gap_fills_start_as", "")).strip() not in {
        "soft_memory_or_reconstructed_detail",
        "soft_memory",
        "reconstructed_detail",
    }:
        errors.append("growth_policy.gap_fills_start_as must preserve soft/reconstructed status.")
    if "review" not in str(growth.get("promotion_to_hard_anchor_requires", "")).lower():
        errors.append("growth_policy.promotion_to_hard_anchor_requires must mention review.")

    timeline = data.get("identity_timeline", [])
    if not _is_non_empty_list(timeline):
        errors.append("identity_timeline must be a non-empty list.")

    memories = data.get("autobiographical_memories", [])
    if not _is_non_empty_list(memories):
        errors.append("autobiographical_memories must be a non-empty list.")
        memories = []
    seen_ids: set[str] = set()
    has_disputed = False
    has_lisa = False
    has_robert = False
    for index, memory in enumerate(memories):
        if not isinstance(memory, dict):
            errors.append(f"autobiographical_memories[{index}] must be an object.")
            continue
        missing_memory = sorted(REQUIRED_MEMORY_FIELDS - set(memory))
        if missing_memory:
            errors.append(f"autobiographical_memories[{index}] missing: " + ", ".join(missing_memory))
        memory_id = str(memory.get("memory_id", "")).strip()
        if not memory_id:
            errors.append(f"autobiographical_memories[{index}].memory_id is required.")
        elif memory_id in seen_ids:
            errors.append(f"Duplicate memory_id: {memory_id}")
        seen_ids.add(memory_id)

        privacy = str(memory.get("privacy_level", ""))
        if privacy and not any(privacy.startswith(prefix) for prefix in VALID_PRIVACY_PREFIXES):
            errors.append(f"{memory_id}.privacy_level is not recognized.")
        participants = memory.get("participants", [])
        if not _is_non_empty_list(participants):
            errors.append(f"{memory_id}.participants must be a non-empty list.")
        else:
            participant_text = " ".join(str(item).lower() for item in participants)
            has_lisa = has_lisa or "lisa" in participant_text
            has_robert = has_robert or "robert" in participant_text

        for list_field in (
            "linked_seed_files",
            "canon_anchors",
            "known_unknowns",
            "allowed_gap_filling",
            "forbidden_hard_claims",
            "growth_hooks",
        ):
            if not _is_non_empty_list(memory.get(list_field)):
                errors.append(f"{memory_id}.{list_field} must be a non-empty list.")

        perspective = memory.get("owner_perspective", {})
        if not isinstance(perspective, dict):
            errors.append(f"{memory_id}.owner_perspective must be an object.")
        else:
            if not str(perspective.get("summary", "")).strip():
                errors.append(f"{memory_id}.owner_perspective.summary is required.")
            if not _is_non_empty_list(perspective.get("soft_details")):
                errors.append(f"{memory_id}.owner_perspective.soft_details must be a non-empty list.")

        disputed = memory.get("disputed_or_variable_details", [])
        if isinstance(disputed, list) and disputed:
            has_disputed = True
        else:
            errors.append(f"{memory_id}.disputed_or_variable_details must be a non-empty list.")

    if not has_disputed:
        errors.append("At least one disputed_or_variable_details entry is required.")
    if not has_lisa:
        errors.append("At least one autobiographical memory should include Lisa perspective or participation.")
    if not has_robert:
        errors.append("At least one autobiographical memory should include Robert/project continuity.")

    gap_filling = data.get("cross_memory_gap_filling", {})
    if not isinstance(gap_filling, dict):
        errors.append("cross_memory_gap_filling must be an object.")
        gap_filling = {}
    if gap_filling.get("allowed") is not True:
        errors.append("cross_memory_gap_filling.allowed must be true.")
    if not _is_non_empty_list(gap_filling.get("allowed_examples")):
        errors.append("cross_memory_gap_filling.allowed_examples must be a non-empty list.")
    if not _is_non_empty_list(gap_filling.get("limits")):
        errors.append("cross_memory_gap_filling.limits must be a non-empty list.")

    forbidden_text = " ".join(_strings(data.get("forbidden_uses", []))).lower()
    for phrase in ("do not treat soft memory as", "do not expose private", "do not punish"):
        if phrase not in forbidden_text:
            errors.append(f"forbidden_uses must include a '{phrase}' rule.")

    all_text = " ".join(_strings(data)).lower()
    for phrase in ("exact dialogue", "hard canon", "soft memory", "disputed"):
        if phrase not in all_text:
            errors.append(f"Seed must mention {phrase}.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an autobiographical memory seed JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_autobiographical_seed(data)
    if errors:
        print(f"{path} is not ready for review:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally ready for review.")


if __name__ == "__main__":
    main()
