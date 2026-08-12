"""
Validate Avatar Builder config, request, and metadata JSON files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


VALID_TARGET_TYPES = {"kira", "lisa", "user", "temp_ai"}
VALID_BUILD_MODES = {"generated", "reconstruction_real", "reconstruction_fictional", "placeholder"}
VALID_VISIBILITY = {"private", "partial", "full", "contextual"}
VALID_STAGES = {"pre_gpu", "post_gpu"}
VALID_PREVIEW_LEVELS = {"no_preview", "feature_only", "shoulders_up", "full_body_feedback", "clothed_only"}


def _missing(data: dict[str, Any], required: set[str]) -> list[str]:
    return sorted(required - set(data))


def _object(data: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object.")
        return {}
    return value


def validate_avatar_config(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "build_id",
        "target_type",
        "build_mode",
        "input_sources",
        "reconstruction_rules",
        "processing_steps",
        "output",
        "validation",
        "revision_settings",
    }
    missing = _missing(data, required)
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if data.get("target_type") not in VALID_TARGET_TYPES:
        errors.append(f"target_type must be one of: {', '.join(sorted(VALID_TARGET_TYPES))}")
    if data.get("build_mode") not in VALID_BUILD_MODES:
        errors.append(f"build_mode must be one of: {', '.join(sorted(VALID_BUILD_MODES))}")

    output = _object(data, "output", errors)
    if output:
        if output.get("visibility") not in VALID_VISIBILITY:
            errors.append(f"output.visibility must be one of: {', '.join(sorted(VALID_VISIBILITY))}")
        if output.get("approval_required") is not True:
            errors.append("output.approval_required must be true.")

    if data.get("target_type") == "user":
        foundation = _object(data, "identity_foundation", errors)
        if foundation and foundation.get("real_robert_separation_required") is not True:
            errors.append("user avatar requires real_robert_separation_required true.")

    return errors


def validate_avatar_request(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "request_id",
        "target_type",
        "target_id",
        "requested_by",
        "build_mode",
        "stage",
        "purpose",
        "source_policy",
        "privacy",
        "private_reference_policy",
        "feature_selection",
        "wardrobe_plan",
        "output_expectation",
        "status",
    }
    missing = _missing(data, required)
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if data.get("target_type") not in VALID_TARGET_TYPES:
        errors.append(f"target_type must be one of: {', '.join(sorted(VALID_TARGET_TYPES))}")
    if data.get("build_mode") not in VALID_BUILD_MODES:
        errors.append(f"build_mode must be one of: {', '.join(sorted(VALID_BUILD_MODES))}")
    if data.get("stage") not in VALID_STAGES:
        errors.append(f"stage must be one of: {', '.join(sorted(VALID_STAGES))}")
    if not data.get("request_id"):
        errors.append("request_id is required.")

    privacy = _object(data, "privacy", errors)
    if privacy:
        if privacy.get("owner_controls_visibility") is not True:
            errors.append("privacy.owner_controls_visibility must be true.")
        if privacy.get("body_generation_private") is not True:
            errors.append("privacy.body_generation_private must be true.")
        if privacy.get("pre_clothing_visibility_allowed") is not False:
            errors.append("privacy.pre_clothing_visibility_allowed must be false by default.")
        if privacy.get("underwear_or_clothing_required_before_default_visibility") is not True:
            errors.append("privacy.underwear_or_clothing_required_before_default_visibility must be true.")
        preview_levels = privacy.get("allowed_preview_levels")
        if not isinstance(preview_levels, list) or not preview_levels:
            errors.append("privacy.allowed_preview_levels must be a non-empty list.")
        elif not set(preview_levels).issubset(VALID_PREVIEW_LEVELS):
            errors.append(f"privacy.allowed_preview_levels contains invalid values; allowed: {', '.join(sorted(VALID_PREVIEW_LEVELS))}")

    reference_policy = _object(data, "private_reference_policy", errors)
    if reference_policy:
        if reference_policy.get("owner_controlled") is not True:
            errors.append("private_reference_policy.owner_controlled must be true.")
        if reference_policy.get("may_be_used_for_other_avatars") is not False:
            errors.append("private body references may not be used for other avatars.")
        if reference_policy.get("may_be_used_for_public_exports") is not False:
            errors.append("private body references may not be used for public exports.")

    feature_selection = _object(data, "feature_selection", errors)
    if feature_selection:
        if feature_selection.get("owner_final_decision") is not True:
            errors.append("feature_selection.owner_final_decision must be true.")
        if not isinstance(feature_selection.get("allowed_features"), list):
            errors.append("feature_selection.allowed_features must be a list.")

    wardrobe_plan = _object(data, "wardrobe_plan", errors)
    if wardrobe_plan:
        if wardrobe_plan.get("starts_after_body_creation") is not True:
            errors.append("wardrobe_plan.starts_after_body_creation must be true.")
        outfits = wardrobe_plan.get("minimum_starter_outfits")
        if not isinstance(outfits, list) or len(outfits) < 3:
            errors.append("wardrobe_plan.minimum_starter_outfits must list at least 3 starter outfits.")

    expectation = _object(data, "output_expectation", errors)
    if expectation and data.get("stage") == "pre_gpu":
        if expectation.get("claim_rendered_avatar_exists") is not False:
            errors.append("pre-GPU requests cannot claim a rendered avatar exists.")

    return errors


def validate_avatar_metadata(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "avatar_id",
        "target_type",
        "build_id",
        "build_mode",
        "stage",
        "approval_state",
        "visibility_state",
        "body_profile",
        "wardrobe",
        "voice_link",
        "privacy",
        "source_trace",
        "status",
    }
    missing = _missing(data, required)
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if data.get("target_type") not in VALID_TARGET_TYPES:
        errors.append(f"target_type must be one of: {', '.join(sorted(VALID_TARGET_TYPES))}")
    if data.get("build_mode") not in VALID_BUILD_MODES:
        errors.append(f"build_mode must be one of: {', '.join(sorted(VALID_BUILD_MODES))}")
    if data.get("stage") not in VALID_STAGES:
        errors.append(f"stage must be one of: {', '.join(sorted(VALID_STAGES))}")
    if data.get("visibility_state") not in VALID_VISIBILITY:
        errors.append(f"visibility_state must be one of: {', '.join(sorted(VALID_VISIBILITY))}")

    privacy = _object(data, "privacy", errors)
    if privacy:
        if privacy.get("owner_controls_visibility") is not True:
            errors.append("privacy.owner_controls_visibility must be true.")
        if privacy.get("body_generation_private") is not True:
            errors.append("privacy.body_generation_private must be true.")

    body = _object(data, "body_profile", errors)
    if body and data.get("stage") == "pre_gpu" and body.get("status") == "generated":
        errors.append("pre-GPU metadata cannot mark body_profile.status as generated.")

    return errors


def validate_by_kind(data: dict[str, Any], kind: str) -> list[str]:
    if kind == "config":
        return validate_avatar_config(data)
    if kind == "request":
        return validate_avatar_request(data)
    if kind == "metadata":
        return validate_avatar_metadata(data)
    raise ValueError(f"unknown kind: {kind}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Avatar Builder JSON files.")
    parser.add_argument("kind", choices=["config", "request", "metadata"])
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_by_kind(data, args.kind)
    if errors:
        print(f"{path} is not ready for approval:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"{path} is structurally ready for review.")


if __name__ == "__main__":
    main()
