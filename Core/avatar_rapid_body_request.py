"""Validation for existing-Avatar-Builder rapid body requests.

This module validates intake and privacy boundaries only. It does not author,
assign, activate, or approve a body.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any


ALLOWED_PURPOSES = {"TEMPORARY_FUNCTIONAL_BODY", "OWNER_REVIEW_BODY"}
ALLOWED_BODY_CLASSES = {"adult_female", "adult_male"}
ALLOWED_BUILD_PRESETS = {
    "natural_average",
    "natural_athletic",
    "natural_slender",
    "natural_stocky",
}
BOUNDED_NUMERIC_PARAMETERS = {
    "muscularity": (0.0, 0.45),
    "body_mass": (-0.15, 0.15),
    "shoulder_width": (-0.12, 0.12),
    "chest_torso": (-0.12, 0.12),
    "waist_abdomen": (-0.12, 0.08),
    "hips_pelvis": (-0.08, 0.10),
    "arms": (-0.08, 0.10),
    "legs": (-0.08, 0.10),
    "hands": (-0.05, 0.05),
    "feet": (-0.05, 0.05),
    "neck": (-0.08, 0.08),
}
ALLOWED_FACE_LANDMARK_PRESETS = {
    "bounded_generic_adult_female",
    "bounded_generic_adult_male",
    "bounded_owner_authorized_landmarks",
}
ALLOWED_SKIN_DIRECTIONS = {
    "light_natural_regional_variation",
    "medium_natural_regional_variation",
    "deep_natural_regional_variation",
    "owner_authorized_natural_regional_variation",
}
ALLOWED_IRIS_COLORS = {
    "natural_blue",
    "natural_brown",
    "natural_gray",
    "natural_green",
    "natural_hazel",
    "owner_authorized_natural",
}
ALLOWED_HAIR_TEXTURES = {
    "coily",
    "curly",
    "straight",
    "wavy",
}
ALLOWED_REVIEW_HAIR_STYLES = {
    "simple_removable_shoulders_clear",
    "simple_removable_short",
    "simple_removable_tied_back",
}
PROHIBITED_SOURCE_FRAGMENTS = {
    "robert",
    "dual_robert",
    "biological_robert",
    "synthetic_robert",
    "robert_avatar",
    "robert/private",
    "private_owner_review/dual_robert",
}


class RapidBodyRequestError(ValueError):
    """Raised when a rapid-body request is unsafe or structurally invalid."""


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RapidBodyRequestError(f"{name} must be an object")
    return value


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise RapidBodyRequestError(f"{name} must be a list")
    return value


def _normalized_path(value: str) -> str:
    return PurePosixPath(value.replace("\\", "/")).as_posix().casefold()


def _reject_prohibited_source(value: str, field: str) -> None:
    normalized = _normalized_path(value)
    for fragment in PROHIBITED_SOURCE_FRAGMENTS:
        if fragment in normalized:
            raise RapidBodyRequestError(
                f"{field} contains prohibited Robert-private source fragment "
                f"{fragment!r}"
            )


def validate_rapid_body_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized summary or fail closed.

    The validator deliberately requires an inactive private candidate. Runtime
    assignment and approval are later owner-controlled actions.
    """

    payload = _require_dict(payload, "payload")
    if payload.get("schema_version") != 1:
        raise RapidBodyRequestError("schema_version must be 1")

    owner = _require_dict(payload.get("display_owner"), "display_owner")
    owner_id = str(owner.get("stable_id", "")).strip()
    owner_name = str(owner.get("display_name", "")).strip()
    if not owner_id or not owner_name:
        raise RapidBodyRequestError("display_owner requires stable_id and display_name")

    purpose = str(payload.get("body_purpose", "")).strip()
    if purpose not in ALLOWED_PURPOSES:
        raise RapidBodyRequestError(f"unsupported body_purpose {purpose!r}")
    if str(payload.get("adult_status", "")).casefold() != "adult":
        raise RapidBodyRequestError("rapid body foundations require explicit adult status")

    body_class = str(payload.get("body_class", "")).strip()
    if body_class not in ALLOWED_BODY_CLASSES:
        raise RapidBodyRequestError(f"unsupported body_class {body_class!r}")

    parameters = _require_dict(payload.get("parameters"), "parameters")
    allowed_parameter_keys = {
        "height_m",
        "build_preset",
        *BOUNDED_NUMERIC_PARAMETERS,
        "face_landmarks",
        "skin_direction",
        "iris_color",
        "hair",
    }
    unknown_parameter_keys = sorted(
        str(key) for key in parameters if key not in allowed_parameter_keys
    )
    if unknown_parameter_keys:
        raise RapidBodyRequestError(
            "unsupported rapid-body parameters: "
            + ", ".join(unknown_parameter_keys)
        )
    height_m = float(parameters.get("height_m", 0.0))
    if not 1.35 <= height_m <= 2.20:
        raise RapidBodyRequestError("height_m is outside the supported human range")
    build = str(parameters.get("build_preset", "")).strip()
    if build not in ALLOWED_BUILD_PRESETS:
        raise RapidBodyRequestError(f"unsupported build_preset {build!r}")
    normalized_parameters: dict[str, Any] = {
        "height_m": height_m,
        "build_preset": build,
    }
    for name, (minimum, maximum) in BOUNDED_NUMERIC_PARAMETERS.items():
        if name not in parameters:
            raise RapidBodyRequestError(f"parameters.{name} is required")
        try:
            value = float(parameters[name])
        except (TypeError, ValueError) as exc:
            raise RapidBodyRequestError(
                f"parameters.{name} must be numeric"
            ) from exc
        if not minimum <= value <= maximum:
            raise RapidBodyRequestError(
                f"parameters.{name} is outside the bounded range "
                f"[{minimum}, {maximum}]"
            )
        normalized_parameters[name] = value

    face_landmarks = str(parameters.get("face_landmarks", "")).strip()
    if face_landmarks not in ALLOWED_FACE_LANDMARK_PRESETS:
        raise RapidBodyRequestError(
            f"unsupported face_landmarks preset {face_landmarks!r}"
        )
    skin_direction = str(parameters.get("skin_direction", "")).strip()
    if skin_direction not in ALLOWED_SKIN_DIRECTIONS:
        raise RapidBodyRequestError(
            f"unsupported skin_direction {skin_direction!r}"
        )
    iris_color = str(parameters.get("iris_color", "")).strip()
    if iris_color not in ALLOWED_IRIS_COLORS:
        raise RapidBodyRequestError(f"unsupported iris_color {iris_color!r}")
    hair = _require_dict(parameters.get("hair"), "parameters.hair")
    hair_color = str(hair.get("color", "")).strip()
    if not hair_color or len(hair_color) > 48:
        raise RapidBodyRequestError(
            "parameters.hair.color must be a short owner-readable value"
        )
    hair_texture = str(hair.get("texture", "")).strip()
    if hair_texture not in ALLOWED_HAIR_TEXTURES:
        raise RapidBodyRequestError(
            f"unsupported hair texture {hair_texture!r}"
        )
    review_style = str(hair.get("review_style", "")).strip()
    if review_style not in ALLOWED_REVIEW_HAIR_STYLES:
        raise RapidBodyRequestError(
            f"unsupported review hair style {review_style!r}"
        )
    normalized_parameters.update(
        {
            "face_landmarks": face_landmarks,
            "skin_direction": skin_direction,
            "iris_color": iris_color,
            "hair": {
                "color": hair_color,
                "texture": hair_texture,
                "review_style": review_style,
            },
        }
    )

    foundation = _require_dict(payload.get("foundation_requirements"), "foundation_requirements")
    required_true = (
        "continuous_topology",
        "integrated_adult_anatomy",
        "movement_ready_rig",
        "deformation_regions",
        "future_clothing_compatible",
        "future_hair_compatible",
    )
    missing = [name for name in required_true if foundation.get(name) is not True]
    if missing:
        raise RapidBodyRequestError(
            "foundation requirements must explicitly require: " + ", ".join(missing)
        )
    source_path = str(foundation.get("selected_source_path", "")).strip()
    if source_path:
        _reject_prohibited_source(source_path, "foundation.selected_source_path")

    references = _require_list(payload.get("reference_inputs"), "reference_inputs")
    for index, item in enumerate(references):
        item = _require_dict(item, f"reference_inputs[{index}]")
        subject_id = str(item.get("subject_id", "")).strip()
        if subject_id not in {owner_id, "generic_non_identifiable"}:
            raise RapidBodyRequestError(
                f"reference_inputs[{index}].subject_id must match the owner or "
                "generic_non_identifiable"
            )
        for key in ("path", "source_path", "local_file", "uri"):
            if item.get(key):
                _reject_prohibited_source(str(item[key]), f"reference_inputs[{index}].{key}")

    privacy = _require_dict(payload.get("privacy"), "privacy")
    if privacy.get("robert_private_data_allowed") is not False:
        raise RapidBodyRequestError("robert_private_data_allowed must be false")
    if privacy.get("identifiable_person_likeness_allowed") is not False:
        raise RapidBodyRequestError(
            "identifiable_person_likeness_allowed must be false for this request"
        )

    output = _require_dict(payload.get("output"), "output")
    if output.get("runtime_assignment_allowed") is not False:
        raise RapidBodyRequestError("runtime_assignment_allowed must be false")
    if output.get("owner_approved") is not False:
        raise RapidBodyRequestError("owner_approved must be false at intake")
    if str(output.get("candidate_state", "")).strip() != "PRIVATE_INSPECTION_CANDIDATE":
        raise RapidBodyRequestError(
            "candidate_state must be PRIVATE_INSPECTION_CANDIDATE at intake"
        )
    if output.get("kira_permanent_selection_claimed") is not False:
        raise RapidBodyRequestError(
            "kira_permanent_selection_claimed must be false at intake"
        )
    output_root = str(output.get("private_candidate_root", "")).strip()
    if not output_root:
        raise RapidBodyRequestError("private_candidate_root is required")
    _reject_prohibited_source(output_root, "output.private_candidate_root")

    baseline = _require_dict(
        payload.get("runtime_nonmutation_baseline"),
        "runtime_nonmutation_baseline",
    )
    for name in ("live_body", "body_selection", "world_shell_state"):
        record = _require_dict(baseline.get(name), f"runtime_nonmutation_baseline.{name}")
        path = str(record.get("path", "")).strip()
        digest = str(record.get("sha256", "")).strip().casefold()
        if not path or len(digest) != 64:
            raise RapidBodyRequestError(
                f"runtime_nonmutation_baseline.{name} requires path and SHA-256"
            )
        _reject_prohibited_source(path, f"runtime_nonmutation_baseline.{name}.path")

    return {
        "status": "VALID_PRIVATE_RAPID_BODY_REQUEST",
        "owner_id": owner_id,
        "owner_name": owner_name,
        "purpose": purpose,
        "adult_status": "adult",
        "body_class": body_class,
        "height_m": height_m,
        "build_preset": build,
        "parameters": normalized_parameters,
        "integrated_adult_anatomy_required": True,
        "anatomy_status": "REQUIRED_UNPROVEN_UNTIL_CANDIDATE_AUDIT",
        "reference_count": len(references),
        "robert_private_data_allowed": False,
        "runtime_assignment_allowed": False,
        "owner_approved": False,
        "candidate_state": "PRIVATE_INSPECTION_CANDIDATE",
        "runtime_nonmutation_baseline_count": len(baseline),
    }
