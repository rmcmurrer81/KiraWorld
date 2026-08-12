"""Fail-closed validation for identity-free adult body-style profiles.

The profile layer is intentionally declarative and read-only.  It can select
and weight licensed MakeHuman detail targets and describe materials, eyes, and
hair, but it cannot author anatomy, qualify topology, build a mesh, render, or
change the live avatar.  A changed styled candidate must go through the adult
foundation and independent review gates under its new exact artifact hash.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


SCHEMA_PATH = Path(
    "Avatar/avatar_builder/style_profiles/adult_body_style_profile_v1.schema.json"
)
DEFAULT_PROFILE_PATH = Path(
    "Avatar/avatar_builder/style_profiles/"
    "natural_athletic_warm_asymmetric_waves_v1.json"
)
SCHEMA_ID = "avatar_builder_identity_free_adult_body_style_profile_v1"
OFFICIAL_TARGET_ROOT = Path(
    "Avatar/avatar_builder/tooling/makehuman_official/"
    "makehuman/data/targets"
)
SAFE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
MAX_TARGET_WEIGHT = 0.25

ROOT_KEYS = {
    "schema_version",
    "schema_id",
    "profile_id",
    "profile_kind",
    "reusable_for",
    "state",
    "authority",
    "separation_contract",
    "design_direction",
    "dimensions",
    "source_licenses",
    "target_policy",
    "shape_targets",
    "material_profile",
    "eye_profile",
    "hair_profile",
    "application_contract",
}


class BodyStyleProfileError(ValueError):
    """Raised when a caller asks to load a profile that did not validate."""


def _text(value: Any) -> str:
    return str(value or "").strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _mapping(
    value: Any,
    label: str,
    blockers: list[str],
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        blockers.append(f"{label}_must_be_object")
        return {}
    return value


def _exact_keys(
    value: Mapping[str, Any],
    expected: set[str],
    label: str,
    blockers: list[str],
) -> None:
    missing = sorted(expected.difference(value))
    unexpected = sorted(set(value).difference(expected))
    blockers.extend(f"{label}_field_missing:{name}" for name in missing)
    blockers.extend(f"{label}_field_unexpected:{name}" for name in unexpected)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _range_pair(
    value: Any,
    *,
    label: str,
    minimum: float,
    maximum: float,
    blockers: list[str],
) -> bool:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(_is_number(item) for item in value)
    ):
        blockers.append(f"{label}_range_invalid")
        return False
    low, high = (float(value[0]), float(value[1]))
    if low < minimum or high > maximum or low > high:
        blockers.append(f"{label}_range_out_of_bounds")
        return False
    return True


def _safe_project_file(
    project_root: Path,
    raw_path: Any,
    *,
    label: str,
    blockers: list[str],
    suffix: str | None = None,
    within: Path | None = None,
) -> Path | None:
    value = _text(raw_path)
    relative = Path(value)
    if not value or relative.is_absolute() or ".." in relative.parts:
        blockers.append(f"{label}_path_unsafe")
        return None
    root = project_root.resolve()
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        blockers.append(f"{label}_path_escaped_project")
        return None
    if within is not None:
        allowed = (root / within).resolve()
        try:
            resolved.relative_to(allowed)
        except ValueError:
            blockers.append(f"{label}_path_outside_allowed_root")
            return None
    if suffix is not None and resolved.suffix.lower() != suffix.lower():
        blockers.append(f"{label}_suffix_invalid")
        return None
    if not resolved.is_file():
        blockers.append(f"{label}_file_missing")
        return None
    return resolved


def _verify_binding(
    project_root: Path,
    binding: Any,
    *,
    label: str,
    blockers: list[str],
    suffix: str | None = None,
    within: Path | None = None,
) -> tuple[Path | None, str]:
    record = _mapping(binding, f"{label}_binding", blockers)
    expected = _text(record.get("sha256")).lower()
    if not SHA256_RE.fullmatch(expected):
        blockers.append(f"{label}_sha256_invalid")
    path = _safe_project_file(
        project_root,
        record.get("path"),
        label=label,
        blockers=blockers,
        suffix=suffix,
        within=within,
    )
    actual = ""
    if path is not None:
        actual = _sha256(path)
        if SHA256_RE.fullmatch(expected) and actual != expected:
            blockers.append(f"{label}_sha256_mismatch")
    return path, actual


def _parse_hex(value: Any, label: str, blockers: list[str]) -> tuple[int, int, int] | None:
    text = _text(value)
    if not HEX_COLOR_RE.fullmatch(text):
        blockers.append(f"{label}_hex_invalid")
        return None
    return tuple(int(text[index : index + 2], 16) for index in (1, 3, 5))


def _validate_schema(project_root: Path, blockers: list[str]) -> tuple[str, str]:
    path = _safe_project_file(
        project_root,
        SCHEMA_PATH.as_posix(),
        label="profile_schema",
        blockers=blockers,
        suffix=".json",
    )
    if path is None:
        return "", ""
    digest = _sha256(path)
    try:
        schema = _read_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        blockers.append("profile_schema_json_invalid")
        return path.relative_to(project_root.resolve()).as_posix(), digest
    if schema.get("$id") != SCHEMA_ID:
        blockers.append("profile_schema_id_invalid")
    if schema.get("type") != "object":
        blockers.append("profile_schema_root_type_invalid")
    required = schema.get("required")
    if not isinstance(required, list) or set(required) != ROOT_KEYS:
        blockers.append("profile_schema_required_fields_drifted")
    if schema.get("additionalProperties") is not False:
        blockers.append("profile_schema_not_fail_closed")
    return path.relative_to(project_root.resolve()).as_posix(), digest


def _validate_authority(profile: Mapping[str, Any], blockers: list[str]) -> None:
    authority = _mapping(profile.get("authority"), "authority", blockers)
    _exact_keys(
        authority,
        {
            "maturity_status",
            "age_gate",
            "body_class",
            "adult_confirmation_required_at_application",
            "unknown_or_minor_blocked",
        },
        "authority",
        blockers,
    )
    if authority.get("maturity_status") != "confirmed_adult":
        blockers.append("authority_maturity_must_be_confirmed_adult")
    if authority.get("age_gate") != "adult_only":
        blockers.append("authority_age_gate_must_be_adult_only")
    if authority.get("body_class") != "adult_female":
        blockers.append("authority_body_class_must_be_adult_female")
    if authority.get("adult_confirmation_required_at_application") is not True:
        blockers.append("authority_adult_reconfirmation_not_required")
    if authority.get("unknown_or_minor_blocked") is not True:
        blockers.append("authority_unknown_or_minor_not_blocked")


def _validate_separation(profile: Mapping[str, Any], blockers: list[str]) -> None:
    separation = _mapping(
        profile.get("separation_contract"),
        "separation_contract",
        blockers,
    )
    _exact_keys(
        separation,
        {
            "layer",
            "adult_foundation_qualification_required",
            "anatomy_topology_source",
            "changes_anatomy_topology",
            "contains_or_copies_geometry",
            "anatomy_relationships_included",
            "can_qualify_adult_foundation",
            "post_style_exact_hash_requalification_required",
        },
        "separation_contract",
        blockers,
    )
    if separation.get("layer") != "style_only":
        blockers.append("separation_layer_not_style_only")
    if separation.get("adult_foundation_qualification_required") is not True:
        blockers.append("adult_foundation_qualification_not_required")
    if separation.get("anatomy_topology_source") != "separate_qualified_foundation":
        blockers.append("anatomy_topology_source_not_separate")
    for name in (
        "changes_anatomy_topology",
        "contains_or_copies_geometry",
        "anatomy_relationships_included",
        "can_qualify_adult_foundation",
    ):
        if separation.get(name) is not False:
            blockers.append(f"separation_forbidden_capability_enabled:{name}")
    if separation.get("post_style_exact_hash_requalification_required") is not True:
        blockers.append("post_style_exact_hash_requalification_not_required")


def _validate_design_direction(
    project_root: Path,
    profile: Mapping[str, Any],
    blockers: list[str],
) -> int:
    direction = _mapping(profile.get("design_direction"), "design_direction", blockers)
    _exact_keys(
        direction,
        {
            "direction_id",
            "descriptors",
            "earlier_means_prior_visual_direction_not_subject_age",
            "sources",
        },
        "design_direction",
        blockers,
    )
    descriptors = direction.get("descriptors")
    required_descriptors = {
        "natural_athletic",
        "warm_earlier_skin_direction",
        "curvier_hips_and_buttocks",
        "slightly_narrower_waist",
        "natural_fuller_adult_bust",
        "modest_muscle_and_tone",
    }
    if not isinstance(descriptors, list) or not required_descriptors.issubset(descriptors):
        blockers.append("design_direction_descriptors_incomplete")
    if direction.get("earlier_means_prior_visual_direction_not_subject_age") is not True:
        blockers.append("earlier_direction_age_interpretation_unsafe")
    sources = direction.get("sources")
    if not isinstance(sources, list) or len(sources) != 2:
        blockers.append("design_direction_sources_must_be_exactly_two")
        return 0
    by_kind = {
        _text(source.get("kind")): source
        for source in sources
        if isinstance(source, Mapping)
    }
    if set(by_kind) != {"owner_text", "audited_generic_earlier_render"}:
        blockers.append("design_direction_source_kinds_invalid")
        return 0
    owner = by_kind["owner_text"]
    _exact_keys(
        owner,
        {
            "kind",
            "source_id",
            "qualitative_only",
            "private_person_measurements_used",
            "biometric_indices_used",
            "copied_geometry_used",
        },
        "owner_text_source",
        blockers,
    )
    if owner.get("qualitative_only") is not True:
        blockers.append("owner_text_not_qualitative_only")
    for name in (
        "private_person_measurements_used",
        "biometric_indices_used",
        "copied_geometry_used",
    ):
        if owner.get(name) is not False:
            blockers.append(f"owner_text_forbidden_data_enabled:{name}")
    render = by_kind["audited_generic_earlier_render"]
    _exact_keys(
        render,
        {
            "kind",
            "path",
            "sha256",
            "audit_path",
            "audit_sha256",
            "source_candidate_status",
            "qualitative_only",
            "allowed_uses",
            "forbidden_uses",
        },
        "design_render_source",
        blockers,
    )
    _verify_binding(
        project_root,
        {"path": render.get("path"), "sha256": render.get("sha256")},
        label="design_render",
        blockers=blockers,
        suffix=".png",
    )
    _verify_binding(
        project_root,
        {"path": render.get("audit_path"), "sha256": render.get("audit_sha256")},
        label="design_render_audit",
        blockers=blockers,
        suffix=".json",
    )
    if render.get("qualitative_only") is not True:
        blockers.append("design_render_not_qualitative_only")
    allowed = set(render.get("allowed_uses") or [])
    if allowed != {
        "warm_skin_palette_direction",
        "asymmetric_side_part_wavy_hair_silhouette",
    }:
        blockers.append("design_render_allowed_uses_invalid")
    forbidden = set(render.get("forbidden_uses") or [])
    required_forbidden = {
        "geometry_copy",
        "topology_copy",
        "measurement_extraction",
        "biometric_index_extraction",
        "identity_landmark_extraction",
        "material_acceptance_claim",
        "body_acceptance_claim",
    }
    if forbidden != required_forbidden:
        blockers.append("design_render_forbidden_uses_incomplete")
    if render.get("source_candidate_status") != "REJECTED_PRIVATE_ENGINEERING_EVIDENCE":
        blockers.append("design_render_rejected_status_not_preserved")
    return 2


def _validate_dimensions(profile: Mapping[str, Any], blockers: list[str]) -> None:
    dimensions = _mapping(profile.get("dimensions"), "dimensions", blockers)
    _exact_keys(
        dimensions,
        {
            "target_height_m",
            "height_tolerance_m",
            "basis",
            "only_numeric_body_measurement",
            "private_person_measurements_used",
            "proportion_or_biometric_indices_present",
        },
        "dimensions",
        blockers,
    )
    height = dimensions.get("target_height_m")
    if not _is_number(height) or not 1.35 <= float(height) <= 2.05:
        blockers.append("target_height_m_out_of_bounds")
    tolerance = dimensions.get("height_tolerance_m")
    if not _is_number(tolerance) or not 0.0 < float(tolerance) <= 0.01:
        blockers.append("height_tolerance_m_out_of_bounds")
    if dimensions.get("basis") != "owner_specified_avatar_target_not_extracted_biometric":
        blockers.append("height_basis_invalid")
    if dimensions.get("only_numeric_body_measurement") is not True:
        blockers.append("additional_numeric_body_measurements_present")
    if dimensions.get("private_person_measurements_used") is not False:
        blockers.append("private_person_measurements_present")
    if dimensions.get("proportion_or_biometric_indices_present") is not False:
        blockers.append("proportion_or_biometric_indices_present")


def _validate_licenses(
    project_root: Path,
    profile: Mapping[str, Any],
    blockers: list[str],
) -> dict[str, Mapping[str, Any]]:
    licenses = profile.get("source_licenses")
    if not isinstance(licenses, list) or not licenses:
        blockers.append("source_licenses_missing")
        return {}
    records: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(licenses):
        label = f"source_license_{index}"
        record = _mapping(raw, label, blockers)
        _exact_keys(
            record,
            {
                "binding_id",
                "source_name",
                "source_url",
                "license_id",
                "license_url",
                "adaptation_allowed",
                "style_target_use_allowed",
                "applies_to_path_prefix",
                "evidence_path",
                "evidence_sha256",
            },
            label,
            blockers,
        )
        binding_id = _text(record.get("binding_id"))
        if not SAFE_ID_RE.fullmatch(binding_id):
            blockers.append(f"{label}_binding_id_invalid")
        elif binding_id in records:
            blockers.append(f"source_license_binding_duplicate:{binding_id}")
        else:
            records[binding_id] = record
        if record.get("license_id") != "CC0-1.0":
            blockers.append(f"{label}_license_id_not_cc0")
        if record.get("source_name") != "MakeHuman official bundled assets":
            blockers.append(f"{label}_source_name_invalid")
        if record.get("adaptation_allowed") is not True:
            blockers.append(f"{label}_adaptation_not_allowed")
        if record.get("style_target_use_allowed") is not True:
            blockers.append(f"{label}_style_target_use_not_allowed")
        if record.get("applies_to_path_prefix") != OFFICIAL_TARGET_ROOT.as_posix():
            blockers.append(f"{label}_path_prefix_invalid")
        _verify_binding(
            project_root,
            {"path": record.get("evidence_path"), "sha256": record.get("evidence_sha256")},
            label=f"{label}_evidence",
            blockers=blockers,
            suffix=".md",
        )
    return records


def _validate_targets(
    project_root: Path,
    profile: Mapping[str, Any],
    licenses: Mapping[str, Mapping[str, Any]],
    blockers: list[str],
) -> tuple[list[dict[str, Any]], int]:
    policy = _mapping(profile.get("target_policy"), "target_policy", blockers)
    _exact_keys(
        policy,
        {
            "allowed_root",
            "maximum_absolute_weight",
            "exact_sha256_required",
            "official_makehuman_targets_only",
            "all_targets_must_be_symmetric",
            "negative_weights_allowed",
        },
        "target_policy",
        blockers,
    )
    if policy.get("allowed_root") != OFFICIAL_TARGET_ROOT.as_posix():
        blockers.append("target_policy_allowed_root_invalid")
    maximum = policy.get("maximum_absolute_weight")
    if (
        not _is_number(maximum)
        or float(maximum) <= 0.0
        or float(maximum) > MAX_TARGET_WEIGHT
    ):
        blockers.append("target_policy_maximum_weight_invalid")
        maximum_value = MAX_TARGET_WEIGHT
    else:
        maximum_value = float(maximum)
    for name in (
        "exact_sha256_required",
        "official_makehuman_targets_only",
        "all_targets_must_be_symmetric",
        "negative_weights_allowed",
    ):
        expected = False if name == "negative_weights_allowed" else True
        if policy.get(name) is not expected:
            blockers.append(f"target_policy_flag_invalid:{name}")
    targets = profile.get("shape_targets")
    if not isinstance(targets, list) or not targets:
        blockers.append("shape_targets_missing")
        return [], 0
    resolved: list[dict[str, Any]] = []
    ids: set[str] = set()
    paths: set[str] = set()
    pairs: dict[str, list[dict[str, Any]]] = {}
    for index, raw in enumerate(targets):
        label = f"shape_target_{index}"
        record = _mapping(raw, label, blockers)
        _exact_keys(
            record,
            {
                "target_id",
                "design_intent",
                "path",
                "sha256",
                "weight",
                "license_binding_id",
                "symmetry",
            },
            label,
            blockers,
        )
        target_id = _text(record.get("target_id"))
        if not SAFE_ID_RE.fullmatch(target_id):
            blockers.append(f"{label}_id_invalid")
        elif target_id in ids:
            blockers.append(f"shape_target_id_duplicate:{target_id}")
        ids.add(target_id)
        relative_path = _text(record.get("path"))
        if relative_path in paths:
            blockers.append(f"shape_target_path_duplicate:{relative_path}")
        paths.add(relative_path)
        path, actual = _verify_binding(
            project_root,
            {"path": relative_path, "sha256": record.get("sha256")},
            label=label,
            blockers=blockers,
            suffix=".target",
            within=OFFICIAL_TARGET_ROOT,
        )
        weight = record.get("weight")
        if (
            not _is_number(weight)
            or float(weight) <= 0.0
            or float(weight) > maximum_value
        ):
            blockers.append(f"{label}_weight_out_of_bounds")
            weight_value = 0.0
        else:
            weight_value = float(weight)
        binding_id = _text(record.get("license_binding_id"))
        if binding_id not in licenses:
            blockers.append(f"{label}_license_binding_unknown")
        symmetry = _mapping(record.get("symmetry"), f"{label}_symmetry", blockers)
        mode = symmetry.get("mode")
        filename = Path(relative_path).name
        if mode == "bilateral_single_target":
            if set(symmetry) != {"mode"}:
                blockers.append(f"{label}_bilateral_symmetry_fields_invalid")
            if filename.startswith(("l-", "r-")):
                blockers.append(f"{label}_unilateral_target_marked_bilateral")
        elif mode == "paired_left_right":
            if set(symmetry) != {"mode", "pair_id", "side"}:
                blockers.append(f"{label}_paired_symmetry_fields_invalid")
            pair_id = _text(symmetry.get("pair_id"))
            side = symmetry.get("side")
            if not SAFE_ID_RE.fullmatch(pair_id):
                blockers.append(f"{label}_pair_id_invalid")
            if side not in {"left", "right"}:
                blockers.append(f"{label}_pair_side_invalid")
            expected_prefix = "l-" if side == "left" else "r-"
            if side in {"left", "right"} and not filename.startswith(expected_prefix):
                blockers.append(f"{label}_pair_side_path_mismatch")
            pairs.setdefault(pair_id, []).append(
                {
                    "side": side,
                    "weight": weight_value,
                    "path": relative_path,
                    "license_binding_id": binding_id,
                    "design_intent": record.get("design_intent"),
                }
            )
        else:
            blockers.append(f"{label}_symmetry_mode_invalid")
        resolved.append(
            {
                "target_id": target_id,
                "path": relative_path,
                "sha256": actual,
                "weight": weight_value,
                "symmetry_mode": mode,
                "verified": path is not None and actual == _text(record.get("sha256")).lower(),
            }
        )
    for pair_id, rows in pairs.items():
        sides = {row["side"] for row in rows}
        if len(rows) != 2 or sides != {"left", "right"}:
            blockers.append(f"symmetry_pair_incomplete:{pair_id}")
            continue
        left = next(row for row in rows if row["side"] == "left")
        right = next(row for row in rows if row["side"] == "right")
        if abs(left["weight"] - right["weight"]) > 1.0e-12:
            blockers.append(f"symmetry_pair_weight_mismatch:{pair_id}")
        if left["license_binding_id"] != right["license_binding_id"]:
            blockers.append(f"symmetry_pair_license_mismatch:{pair_id}")
        if left["design_intent"] != right["design_intent"]:
            blockers.append(f"symmetry_pair_intent_mismatch:{pair_id}")
        left_token = left["path"].replace("/l-", "/{side}-", 1)
        right_token = right["path"].replace("/r-", "/{side}-", 1)
        if left_token == left["path"] or left_token != right_token:
            blockers.append(f"symmetry_pair_path_mismatch:{pair_id}")
    return resolved, len(pairs)


def _validate_materials(profile: Mapping[str, Any], blockers: list[str]) -> None:
    material = _mapping(profile.get("material_profile"), "material_profile", blockers)
    _exact_keys(material, {"status", "skin"}, "material_profile", blockers)
    skin = _mapping(material.get("skin"), "skin_profile", blockers)
    _exact_keys(
        skin,
        {
            "color_space",
            "base_srgb_hex",
            "earlier_warm_reference_srgb_hex",
            "maximum_srgb_channel_delta",
            "palette_direction",
            "pale_r13_direction_allowed",
            "roughness_range",
            "subsurface_weight_range",
            "microvariation_required",
        },
        "skin_profile",
        blockers,
    )
    base = _parse_hex(skin.get("base_srgb_hex"), "skin_base", blockers)
    reference = _parse_hex(
        skin.get("earlier_warm_reference_srgb_hex"),
        "skin_warm_reference",
        blockers,
    )
    maximum = skin.get("maximum_srgb_channel_delta")
    if not _is_number(maximum) or not 0 <= float(maximum) <= 24:
        blockers.append("skin_maximum_channel_delta_invalid")
    elif base is not None and reference is not None:
        if max(abs(a - b) for a, b in zip(base, reference)) > float(maximum):
            blockers.append("skin_palette_drifted_from_warm_reference")
    if skin.get("color_space") != "sRGB":
        blockers.append("skin_color_space_invalid")
    if skin.get("palette_direction") != "warm_earlier_visual_reference":
        blockers.append("skin_palette_direction_invalid")
    if skin.get("pale_r13_direction_allowed") is not False:
        blockers.append("pale_r13_skin_direction_not_blocked")
    if skin.get("microvariation_required") is not True:
        blockers.append("skin_microvariation_not_required")
    _range_pair(
        skin.get("roughness_range"),
        label="skin_roughness",
        minimum=0.0,
        maximum=1.0,
        blockers=blockers,
    )
    _range_pair(
        skin.get("subsurface_weight_range"),
        label="skin_subsurface_weight",
        minimum=0.0,
        maximum=0.35,
        blockers=blockers,
    )
    if material.get("status") != "SPECIFICATION_ONLY_NOT_APPLIED":
        blockers.append("material_profile_status_invalid")


def _validate_eyes(profile: Mapping[str, Any], blockers: list[str]) -> None:
    eyes = _mapping(profile.get("eye_profile"), "eye_profile", blockers)
    _exact_keys(
        eyes,
        {
            "iris_color_family",
            "iris_srgb_hex",
            "limbal_srgb_hex",
            "natural_iris_variation_required",
            "black_band_artifact_forbidden",
            "status",
        },
        "eye_profile",
        blockers,
    )
    if eyes.get("iris_color_family") != "brown":
        blockers.append("eye_iris_color_must_be_brown")
    _parse_hex(eyes.get("iris_srgb_hex"), "eye_iris", blockers)
    _parse_hex(eyes.get("limbal_srgb_hex"), "eye_limbal", blockers)
    if eyes.get("natural_iris_variation_required") is not True:
        blockers.append("natural_iris_variation_not_required")
    if eyes.get("black_band_artifact_forbidden") is not True:
        blockers.append("black_band_artifact_not_forbidden")
    if eyes.get("status") != "SPECIFICATION_ONLY_NOT_APPLIED":
        blockers.append("eye_profile_status_invalid")


def _validate_hair(profile: Mapping[str, Any], blockers: list[str]) -> None:
    hair = _mapping(profile.get("hair_profile"), "hair_profile", blockers)
    _exact_keys(
        hair,
        {
            "style",
            "earlier_means_prior_preferred_style_not_subject_age",
            "color_family",
            "root_srgb_hex",
            "tip_srgb_hex",
            "source_geometry_copied",
            "representation_requirement",
            "wind",
            "wet",
            "readiness_status",
        },
        "hair_profile",
        blockers,
    )
    if hair.get("style") != "asymmetric_deep_side_part_shoulder_length_loose_waves":
        blockers.append("hair_earlier_style_direction_invalid")
    if hair.get("earlier_means_prior_preferred_style_not_subject_age") is not True:
        blockers.append("hair_earlier_direction_age_interpretation_unsafe")
    if hair.get("color_family") != "natural_black":
        blockers.append("hair_color_family_invalid")
    _parse_hex(hair.get("root_srgb_hex"), "hair_root", blockers)
    _parse_hex(hair.get("tip_srgb_hex"), "hair_tip", blockers)
    if hair.get("source_geometry_copied") is not False:
        blockers.append("hair_source_geometry_copy_enabled")
    if hair.get("representation_requirement") != "guide_curves_with_render_children_or_validated_dynamic_equivalent":
        blockers.append("hair_dynamic_representation_requirement_invalid")
    wind = _mapping(hair.get("wind"), "hair_wind", blockers)
    wet = _mapping(hair.get("wet"), "hair_wet", blockers)
    _exact_keys(
        wind,
        {
            "required",
            "root_pin_fraction",
            "collision_required",
            "guide_response",
            "runtime_proof_required",
        },
        "hair_wind",
        blockers,
    )
    _exact_keys(
        wet,
        {
            "required",
            "parameter",
            "clump_strength_range",
            "volume_multiplier_range",
            "darkening_fraction_range",
            "specular_increase_range",
            "gravity_alignment_increases_with_wetness",
            "runtime_proof_required",
        },
        "hair_wet",
        blockers,
    )
    for section, value in (("wind", wind), ("wet", wet)):
        if value.get("required") is not True:
            blockers.append(f"hair_{section}_readiness_not_required")
        if value.get("runtime_proof_required") is not True:
            blockers.append(f"hair_{section}_runtime_proof_not_required")
    root_pin = wind.get("root_pin_fraction")
    if not _is_number(root_pin) or not 0.9 <= float(root_pin) <= 1.0:
        blockers.append("hair_wind_root_pin_out_of_bounds")
    if wind.get("collision_required") is not True:
        blockers.append("hair_wind_collision_not_required")
    if wet.get("parameter") != "hair_wetness_0_1":
        blockers.append("hair_wetness_parameter_invalid")
    if wet.get("gravity_alignment_increases_with_wetness") is not True:
        blockers.append("hair_wet_gravity_alignment_not_required")
    for name, upper in (
        ("clump_strength_range", 1.0),
        ("volume_multiplier_range", 1.0),
        ("darkening_fraction_range", 0.4),
        ("specular_increase_range", 0.5),
    ):
        _range_pair(
            wet.get(name),
            label=f"hair_wet_{name}",
            minimum=0.0,
            maximum=upper,
            blockers=blockers,
        )
    if hair.get("readiness_status") != "SPECIFICATION_ONLY_NOT_RUNTIME_PROVEN":
        blockers.append("hair_readiness_status_overclaims_proof")


def _validate_application(profile: Mapping[str, Any], blockers: list[str]) -> None:
    contract = _mapping(
        profile.get("application_contract"),
        "application_contract",
        blockers,
    )
    _exact_keys(
        contract,
        {
            "mode",
            "foundation_qualification_required_at_application",
            "confirmed_adult_recheck_required",
            "exact_target_hash_recheck_required",
            "post_style_topology_anatomy_deformation_review_required",
            "private_owner_review_required",
            "runtime_activation_allowed",
            "render_save_or_export_authorized_by_profile",
            "clothing_authorized_by_profile",
            "publication_authorized_by_profile",
        },
        "application_contract",
        blockers,
    )
    required_true = (
        "foundation_qualification_required_at_application",
        "confirmed_adult_recheck_required",
        "exact_target_hash_recheck_required",
        "post_style_topology_anatomy_deformation_review_required",
        "private_owner_review_required",
    )
    for name in required_true:
        if contract.get(name) is not True:
            blockers.append(f"application_required_gate_disabled:{name}")
    if contract.get("mode") != "validate_then_apply_as_listed":
        blockers.append("application_mode_invalid")
    for name in (
        "runtime_activation_allowed",
        "render_save_or_export_authorized_by_profile",
        "clothing_authorized_by_profile",
        "publication_authorized_by_profile",
    ):
        if contract.get(name) is not False:
            blockers.append(f"application_forbidden_authority_enabled:{name}")


def validate_body_style_profile(
    project_root: Path,
    profile_path: Path | str = DEFAULT_PROFILE_PATH,
) -> dict[str, Any]:
    """Validate a style profile and all local bindings without side effects."""

    root = Path(project_root).resolve()
    blockers: list[str] = []
    schema_path, schema_digest = _validate_schema(root, blockers)
    requested = Path(profile_path)
    path = _safe_project_file(
        root,
        requested.as_posix(),
        label="style_profile",
        blockers=blockers,
        suffix=".json",
    )
    profile: dict[str, Any] = {}
    profile_digest = ""
    if path is not None:
        profile_digest = _sha256(path)
        try:
            profile = _read_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            blockers.append("style_profile_json_invalid")
    if profile:
        _exact_keys(profile, ROOT_KEYS, "style_profile", blockers)
        if profile.get("schema_version") != 1:
            blockers.append("style_profile_schema_version_invalid")
        if profile.get("schema_id") != SCHEMA_ID:
            blockers.append("style_profile_schema_id_invalid")
        profile_id = _text(profile.get("profile_id"))
        if not SAFE_ID_RE.fullmatch(profile_id):
            blockers.append("style_profile_id_invalid")
        if profile.get("profile_kind") != "identity_free_adult_body_style":
            blockers.append("style_profile_kind_invalid")
        if profile.get("state") != "DECLARATIVE_ONLY_NOT_APPLIED":
            blockers.append("style_profile_state_invalid")
        reusable = profile.get("reusable_for")
        if reusable != ["confirmed_adult_female_avatar_candidates"]:
            blockers.append("style_profile_reuse_scope_invalid")
        _validate_authority(profile, blockers)
        _validate_separation(profile, blockers)
        source_count = _validate_design_direction(root, profile, blockers)
        _validate_dimensions(profile, blockers)
        licenses = _validate_licenses(root, profile, blockers)
        targets, pair_count = _validate_targets(root, profile, licenses, blockers)
        _validate_materials(profile, blockers)
        _validate_eyes(profile, blockers)
        _validate_hair(profile, blockers)
        _validate_application(profile, blockers)
    else:
        profile_id = ""
        source_count = 0
        targets = []
        pair_count = 0
    blockers = _dedupe(blockers)
    return {
        "schema_version": 1,
        "validation": "avatar_builder_identity_free_adult_body_style_profile_v1",
        "status": "VALIDATED_DECLARATIVE_STYLE_PROFILE" if not blockers else "BLOCKED_INVALID_STYLE_PROFILE",
        "valid": not blockers,
        "profile_id": profile_id,
        "profile_path": (
            path.relative_to(root).as_posix() if path is not None else requested.as_posix()
        ),
        "profile_sha256": profile_digest,
        "schema_path": schema_path,
        "schema_sha256": schema_digest,
        "design_source_count": source_count,
        "target_count": len(targets),
        "symmetric_pair_count": pair_count,
        "total_target_weight": round(sum(row["weight"] for row in targets), 9),
        "resolved_targets": targets,
        "blockers": blockers,
        "build_performed": False,
        "blender_invoked": False,
        "render_performed": False,
        "candidate_saved": False,
        "runtime_mutation_performed": False,
        "runtime_activation_allowed": False,
    }


def load_validated_body_style_profile(
    project_root: Path,
    profile_path: Path | str = DEFAULT_PROFILE_PATH,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return profile plus report, raising when the fail-closed gate blocks."""

    report = validate_body_style_profile(project_root, profile_path)
    if not report["valid"]:
        raise BodyStyleProfileError("; ".join(report["blockers"]))
    path = Path(project_root).resolve() / Path(report["profile_path"])
    return _read_json(path), report


__all__ = [
    "BodyStyleProfileError",
    "DEFAULT_PROFILE_PATH",
    "MAX_TARGET_WEIGHT",
    "OFFICIAL_TARGET_ROOT",
    "SCHEMA_ID",
    "SCHEMA_PATH",
    "load_validated_body_style_profile",
    "validate_body_style_profile",
]
