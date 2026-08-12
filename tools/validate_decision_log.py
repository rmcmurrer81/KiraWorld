"""
Validate decision log JSON files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "decision_id",
    "timestamp",
    "actor",
    "decision_type",
    "summary",
    "reason",
    "privacy_impact",
    "outcome",
    "visibility",
    "status",
}

VALID_DECISION_TYPES = {
    "memory",
    "relationship",
    "privacy",
    "autonomy",
    "temporary_ai",
    "doctor_ai",
    "avatar",
    "embodiment",
    "source_processing",
    "public_export",
    "other",
}
VALID_PRIVACY_IMPACTS = {"none", "private_summary", "sealed_details", "participant_only", "public_candidate"}
VALID_VISIBILITY = {"system_only", "participants_only", "robert_summary_allowed", "public"}
VALID_STATUS = {"draft", "active", "superseded", "archived"}


def _object(data: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object.")
        return {}
    return value


def validate_decision_log(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    for key in ("decision_id", "timestamp", "summary", "reason", "outcome"):
        if not data.get(key):
            errors.append(f"{key} is required.")

    actor = _object(data, "actor", errors)
    if actor:
        if not actor.get("actor_id"):
            errors.append("actor.actor_id is required.")
        if not actor.get("actor_type"):
            errors.append("actor.actor_type is required.")

    if data.get("decision_type") not in VALID_DECISION_TYPES:
        errors.append(f"decision_type must be one of: {', '.join(sorted(VALID_DECISION_TYPES))}")
    if data.get("privacy_impact") not in VALID_PRIVACY_IMPACTS:
        errors.append(f"privacy_impact must be one of: {', '.join(sorted(VALID_PRIVACY_IMPACTS))}")
    if data.get("visibility") not in VALID_VISIBILITY:
        errors.append(f"visibility must be one of: {', '.join(sorted(VALID_VISIBILITY))}")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")

    if data.get("privacy_impact") == "sealed_details" and data.get("visibility") == "public":
        errors.append("sealed decision details cannot be public.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a decision log JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_decision_log(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
