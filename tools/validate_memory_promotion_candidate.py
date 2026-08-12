"""
Validate a memory promotion candidate before saving it as Kira/Lisa memory.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "candidate_id",
    "owner",
    "memory_type",
    "summary",
    "detail",
    "core_facts",
    "known_unknowns",
    "forbidden_inferences",
    "privacy",
    "approval",
}

VALID_OWNERS = {"kira", "lisa", "shared"}
VALID_PRIVACY = {"public", "private", "private_shared", "locked"}
PRIVATE_PRIVACY = {"private", "private_shared", "locked"}
VAGUE_WORDS = {
    "mostly",
    "probably",
    "maybe",
    "somehow",
    "etc",
    "things",
    "stuff",
    "more or less",
    "kind of",
}


def flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        found: list[str] = []
        for item in value:
            found.extend(flatten_strings(item))
        return found
    if isinstance(value, dict):
        found = []
        for item in value.values():
            found.extend(flatten_strings(item))
        return found
    return []


def validate_candidate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if data.get("owner") not in VALID_OWNERS:
        errors.append("owner must be kira, lisa, or shared.")

    if not str(data.get("summary", "")).strip():
        errors.append("summary is required.")

    if not str(data.get("detail", "")).strip():
        errors.append("detail is required.")

    core_facts = data.get("core_facts", [])
    if not isinstance(core_facts, list) or not core_facts:
        errors.append("core_facts must be a non-empty list.")

    known_unknowns = data.get("known_unknowns", [])
    if not isinstance(known_unknowns, list):
        errors.append("known_unknowns must be a list.")

    forbidden = data.get("forbidden_inferences", [])
    if not isinstance(forbidden, list) or not forbidden:
        errors.append("forbidden_inferences must be a non-empty list.")

    privacy = data.get("privacy", {})
    privacy_level = privacy.get("level") if isinstance(privacy, dict) else None
    sharing_rule = privacy.get("sharing_rule", "") if isinstance(privacy, dict) else ""
    if privacy_level not in VALID_PRIVACY:
        errors.append("privacy.level must be public, private, private_shared, or locked.")
    if privacy_level in PRIVATE_PRIVACY and "consent" not in str(sharing_rule).lower() and sharing_rule != "owner_only":
        errors.append("private/shared/locked memories need owner_only or consent sharing_rule.")

    approval = data.get("approval", {})
    approved_by = approval.get("approved_by", "") if isinstance(approval, dict) else ""
    approval_reason = approval.get("approval_reason", "") if isinstance(approval, dict) else ""
    status = data.get("status", "draft")
    if status in {"ready_for_promotion", "promoted"}:
        if not str(approved_by).strip():
            errors.append("ready/promoted candidates require approval.approved_by.")
        if not str(approval_reason).strip():
            errors.append("ready/promoted candidates require approval.approval_reason.")

    all_text = " ".join(flatten_strings(data)).lower()
    vague_hits = sorted(word for word in VAGUE_WORDS if word in all_text)
    if vague_hits and not known_unknowns:
        errors.append(
            "Vague wording found without known_unknowns: " + ", ".join(vague_hits)
        )

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a memory promotion candidate.")
    parser.add_argument("path", help="Path to candidate JSON.")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_candidate(data)
    if errors:
        print(f"{path} is not ready:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
