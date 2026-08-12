"""
Validate voice profile JSON files for Kira, Lisa, user avatar, and Temporary AIs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "voice_id",
    "target_type",
    "voice_mode",
    "voice_characteristics",
    "status",
}

VALID_TARGET_TYPES = {"kira", "lisa", "user_avatar", "temp_ai"}
VALID_VOICE_MODES = {"original", "reconstruction", "generated", "placeholder"}


def _get_name(data: dict[str, Any]) -> str:
    return str(data.get("target_name") or data.get("name") or "")


def validate_voice_profile(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    target_type = data.get("target_type")
    if target_type not in VALID_TARGET_TYPES:
        errors.append(f"target_type must be one of: {', '.join(sorted(VALID_TARGET_TYPES))}")

    voice_mode = data.get("voice_mode")
    if voice_mode not in VALID_VOICE_MODES:
        errors.append(f"voice_mode must be one of: {', '.join(sorted(VALID_VOICE_MODES))}")

    if not data.get("voice_id"):
        errors.append("voice_id is required.")

    if not _get_name(data):
        errors.append("target name is required as target_name or name.")

    status = data.get("status", {})
    if not isinstance(status, dict):
        errors.append("status must be an object.")
    else:
        if voice_mode == "reconstruction":
            source_collected = bool(status.get("source_audio_collected"))
            ready_for_clone = bool(status.get("ready_for_clone", False))
            if ready_for_clone and not source_collected:
                errors.append("ready_for_clone cannot be true until source_audio_collected is true.")

    characteristics = data.get("voice_characteristics", {})
    if not isinstance(characteristics, dict):
        errors.append("voice_characteristics must be an object.")
    else:
        for key in ("pitch_range", "tone", "cadence", "energy_level"):
            if not characteristics.get(key):
                errors.append(f"voice_characteristics.{key} is required.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a voice profile JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_voice_profile(data)
    if errors:
        print(f"{path} is not ready for approval:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"{path} is structurally ready for review.")


if __name__ == "__main__":
    main()
