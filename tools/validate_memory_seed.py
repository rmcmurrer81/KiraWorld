"""
Validate draft memory seed JSON before it becomes approved canon.

This is intentionally conservative. If a memory leaves important gaps unclear,
the validator asks for explicit known_unknowns instead of letting Kira/Lisa fill
those gaps later.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "memory_id",
    "title",
    "participants",
    "privacy_level",
    "canon_anchors",
    "known_unknowns",
    "allowed_expansion",
    "forbidden_changes",
    "forbidden_inferences",
}

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


def validate_seed(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    anchors = data.get("canon_anchors", [])
    if not isinstance(anchors, list) or not anchors:
        errors.append("canon_anchors must be a non-empty list.")

    unknowns = data.get("known_unknowns", [])
    if not isinstance(unknowns, list):
        errors.append("known_unknowns must be a list, even if empty.")

    forbidden = data.get("forbidden_inferences", [])
    if not isinstance(forbidden, list) or not forbidden:
        errors.append("forbidden_inferences must list what the model may not infer.")

    all_text = " ".join(flatten_strings(data)).lower()
    vague_hits = sorted(word for word in VAGUE_WORDS if word in all_text)
    if vague_hits and not unknowns:
        errors.append(
            "Vague wording found without known_unknowns: " + ", ".join(vague_hits)
        )

    if data.get("privacy_level") in {"private_shared", "locked"}:
        sharing = data.get("sharing_rule", "")
        if "consent" not in str(sharing).lower():
            errors.append("Private/shared memories need an explicit consent sharing_rule.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a memory seed JSON file.")
    parser.add_argument("path", help="Path to the seed JSON file.")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_seed(data)

    if errors:
        print(f"{path} is not ready for approval:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"{path} is structurally ready for review.")


if __name__ == "__main__":
    main()
