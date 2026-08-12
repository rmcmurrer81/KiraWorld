"""
Validate a memory reconstruction world draft.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "reconstruction_id",
    "source_memory_id",
    "title",
    "world_type",
    "status",
    "phase_support",
    "owners",
    "participants_in_memory",
    "privacy",
    "pre_gpu_recall",
    "post_gpu_world",
    "confirmed_zones",
    "inferred_zones",
    "unknown_zones",
    "sealed_private_zones",
    "perspectives",
    "forbidden_inferences",
}


def validate_world(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if data.get("world_type") != "memory_reconstruction":
        errors.append("world_type must be memory_reconstruction.")

    phase = data.get("phase_support", {})
    if not isinstance(phase, dict):
        errors.append("phase_support must be an object.")
    elif not phase.get("pre_gpu_recall") and not phase.get("post_gpu_world"):
        errors.append("At least one phase_support mode must be true.")

    owners = data.get("owners", [])
    if not isinstance(owners, list) or not owners:
        errors.append("owners must be a non-empty list.")

    privacy = data.get("privacy", {})
    if not isinstance(privacy, dict):
        errors.append("privacy must be an object.")
    else:
        if privacy.get("level") in {"private_shared", "locked"}:
            consent = privacy.get("consent_required_from", [])
            if not consent:
                errors.append("private_shared or locked worlds require consent_required_from.")

    confirmed = data.get("confirmed_zones", [])
    unknown = data.get("unknown_zones", [])
    sealed_private = data.get("sealed_private_zones", [])
    if not isinstance(confirmed, list) or not confirmed:
        errors.append("confirmed_zones must be a non-empty list.")
    if not isinstance(unknown, list):
        errors.append("unknown_zones must be a list, even if empty.")
    if not isinstance(sealed_private, list):
        errors.append("sealed_private_zones must be a list, even if empty.")
    for index, zone in enumerate(sealed_private):
        if not isinstance(zone, dict):
            errors.append(f"sealed_private_zones[{index}] must be an object.")
            continue
        if not zone.get("owners"):
            errors.append(f"sealed_private_zones[{index}] must define owners.")
        if zone.get("privacy_level") not in {"private_shared", "locked"}:
            errors.append(f"sealed_private_zones[{index}] must use private_shared or locked privacy_level.")
        if not zone.get("share_requires"):
            errors.append(f"sealed_private_zones[{index}] must define share_requires.")

    forbidden = data.get("forbidden_inferences", [])
    if not isinstance(forbidden, list) or not forbidden:
        errors.append("forbidden_inferences must be a non-empty list.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a memory reconstruction world JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_world(data)
    if errors:
        print(f"{path} is not ready for approval:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"{path} is structurally ready for review.")


if __name__ == "__main__":
    main()
