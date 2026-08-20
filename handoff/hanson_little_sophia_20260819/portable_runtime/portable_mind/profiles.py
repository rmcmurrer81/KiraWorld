from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import SAFE_ID, package_root
from .strict_json import load_path_strict


class ProfileError(ValueError):
    pass


@dataclass(frozen=True)
class PublicProfile:
    profile_id: str
    display_name: str
    description: str
    conversational_style: tuple[str, ...]
    values: tuple[str, ...]
    boundaries: tuple[str, ...]
    voice: dict[str, Any]

    def prompt_view(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "description": self.description,
            "conversational_style": list(self.conversational_style),
            "values": list(self.values),
            "boundaries": list(self.boundaries),
        }


def profiles_dir() -> Path:
    return package_root() / "profiles"


def load_profile(profile_id: str, root: Path | None = None) -> PublicProfile:
    if not SAFE_ID.fullmatch(profile_id):
        raise ProfileError("invalid profile identifier")
    source = (root or profiles_dir()) / f"{profile_id}.json"
    try:
        raw = load_path_strict(source)
    except FileNotFoundError as exc:
        raise ProfileError(f"unknown profile: {profile_id}") from exc
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ProfileError(f"profile {profile_id} is not strict valid JSON") from exc
    required = {
        "schema_version",
        "profile_id",
        "display_name",
        "description",
        "conversational_style",
        "values",
        "boundaries",
        "voice",
    }
    if not isinstance(raw, dict) or set(raw) != required:
        raise ProfileError(f"profile {profile_id} has an unexpected schema")
    if raw["schema_version"] != 1 or raw["profile_id"] != profile_id:
        raise ProfileError(f"profile {profile_id} identity mismatch")
    for list_field in ("conversational_style", "values", "boundaries"):
        if not isinstance(raw[list_field], list) or not all(
            isinstance(item, str) and item.strip() for item in raw[list_field]
        ):
            raise ProfileError(f"profile field {list_field} must be a non-empty string list")
    if not isinstance(raw["voice"], dict):
        raise ProfileError("voice metadata must be an object")
    return PublicProfile(
        profile_id=profile_id,
        display_name=str(raw["display_name"]),
        description=str(raw["description"]),
        conversational_style=tuple(raw["conversational_style"]),
        values=tuple(raw["values"]),
        boundaries=tuple(raw["boundaries"]),
        voice=dict(raw["voice"]),
    )


def available_profiles(root: Path | None = None) -> tuple[str, ...]:
    directory = root or profiles_dir()
    return tuple(sorted(path.stem for path in directory.glob("*.json")))
