"""Validate logical notebook-world collections and their isolation gates."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


_ID_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MEMBER_STATUSES = {"request_prepared", "queued_not_requested", "deployed"}


def _normalized_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and bool(path.parts)
        and ":" not in path.parts[0]
        and all(part not in {"", ".", ".."} for part in path.parts)
        and path.as_posix() == value
    )


def _expect_false(container: dict[str, Any], key: str, errors: list[str], prefix: str) -> None:
    if container.get(key) is not False:
        errors.append(f"{prefix}.{key} must be false.")


def _observed_ram_gb(hardware_profile: dict[str, Any] | None) -> int | float | None:
    if not isinstance(hardware_profile, dict):
        return None
    try:
        value = hardware_profile["known_build"]["current_observed_ram"]["capacity_gb"]
    except (KeyError, TypeError):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def validate_notebook_world_collection(
    data: dict[str, Any],
    hardware_profile: dict[str, Any] | None = None,
) -> list[str]:
    """Return structural and resource-isolation errors for a collection manifest."""

    errors: list[str] = []
    if not isinstance(data, dict):
        return ["Collection manifest must be a JSON object."]
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1.")
    collection_id = data.get("collection_id")
    if not isinstance(collection_id, str) or not _ID_RE.fullmatch(collection_id):
        errors.append("collection_id must be a normalized identifier.")
    if data.get("collection_kind") != "logical_notebook_collection":
        errors.append("collection_kind must be logical_notebook_collection.")
    if data.get("status") != "planned_request_only":
        errors.append("A new collection must remain planned_request_only.")

    runtime = data.get("runtime_policy")
    if not isinstance(runtime, dict):
        errors.append("runtime_policy must be an object.")
        runtime = {}
    if runtime.get("load_mode") != "sequential_members_only":
        errors.append("runtime_policy.load_mode must be sequential_members_only.")
    if runtime.get("max_concurrent_notebook_worlds") != 1:
        errors.append("runtime_policy.max_concurrent_notebook_worlds must be 1.")
    for key in (
        "co_load_members_allowed",
        "loads_home_world",
        "loads_resident_minds",
        "loads_voice",
        "loads_ollama",
        "memory_reconstruction_members_allowed",
    ):
        _expect_false(runtime, key, errors, "runtime_policy")
    if not _normalized_relative_path(runtime.get("hardware_profile")):
        errors.append("runtime_policy.hardware_profile must be a normalized project-relative path.")
    if not _normalized_relative_path(runtime.get("resource_gate_path")):
        errors.append("runtime_policy.resource_gate_path must be a normalized project-relative path.")

    protected = data.get("protected_world_policy")
    if not isinstance(protected, dict):
        errors.append("protected_world_policy must be an object.")
        protected = {}
    for key in ("merge_into_home_world_allowed", "strip_mall_mutation_allowed"):
        _expect_false(protected, key, errors, "protected_world_policy")

    members = data.get("members")
    if not isinstance(members, list) or not members:
        errors.append("members must be a non-empty list.")
        members = []
    seen_world_ids: set[str] = set()
    for position, member in enumerate(members):
        prefix = f"members[{position}]"
        if not isinstance(member, dict):
            errors.append(f"{prefix} must be an object.")
            continue
        world_id = member.get("notebook_world_id")
        if not isinstance(world_id, str) or not _ID_RE.fullmatch(world_id) or not world_id.endswith("_notebook_world"):
            errors.append(f"{prefix}.notebook_world_id must be a normalized *_notebook_world identifier.")
        elif world_id in seen_world_ids:
            errors.append(f"{prefix}.notebook_world_id is duplicated.")
        else:
            seen_world_ids.add(world_id)
        if member.get("member_type") != "place_notebook_world":
            errors.append(f"{prefix}.member_type must be place_notebook_world; memory reconstructions are not collection members.")
        member_status = member.get("status")
        if member_status not in _MEMBER_STATUSES:
            errors.append(f"{prefix}.status is invalid.")
        request_path = member.get("prepared_request_path")
        if member_status in {"request_prepared", "deployed"} and not _normalized_relative_path(request_path):
            errors.append(f"{prefix}.prepared_request_path is required and must be project-relative.")
        if member_status == "queued_not_requested" and request_path is not None and request_path != "":
            errors.append(f"{prefix}.prepared_request_path must be empty until a request is prepared.")
        if member_status == "deployed":
            pinned = member.get("pinned_deployment")
            if not isinstance(pinned, dict):
                errors.append(f"{prefix}.pinned_deployment is required for deployed members.")
            else:
                if not _normalized_relative_path(pinned.get("manifest_path")):
                    errors.append(f"{prefix}.pinned_deployment.manifest_path must be project-relative.")
                if not isinstance(pinned.get("manifest_sha256"), str) or not _SHA256_RE.fullmatch(pinned["manifest_sha256"]):
                    errors.append(f"{prefix}.pinned_deployment.manifest_sha256 must be a lowercase SHA-256 digest.")

    ram_gb = _observed_ram_gb(hardware_profile)
    if hardware_profile is not None and ram_gb is None:
        errors.append("Hardware profile does not contain a numeric current observed RAM capacity.")
    if ram_gb is not None and ram_gb < 64:
        if runtime.get("max_concurrent_notebook_worlds") != 1 or runtime.get("co_load_members_allowed") is not False:
            errors.append("Below 64GB RAM, collection members must remain strictly sequential with one notebook world loaded at a time.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a logical notebook-world collection manifest.")
    parser.add_argument("manifest")
    parser.add_argument("--hardware-profile")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    hardware_profile = None
    if args.hardware_profile:
        hardware_profile = json.loads(Path(args.hardware_profile).read_text(encoding="utf-8"))
    errors = validate_notebook_world_collection(data, hardware_profile)
    if errors:
        print(f"{manifest_path} is not safe to register:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{manifest_path} is structurally safe as a sequential logical collection.")


if __name__ == "__main__":
    main()
