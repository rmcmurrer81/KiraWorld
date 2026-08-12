"""Pure preflight contract for the inactive profiled adult candidate builder.

This module has no Blender dependency and performs no writes.  It binds the
official MakeHuman source set, exact style profile, separately qualified adult
foundation, private output boundary, and the three live Kira state guards.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from Core.avatar_adult_foundation_qualification import (
    POLICY_PATH as ADULT_FOUNDATION_POLICY_PATH,
    REGISTRY_PATH as ADULT_FOUNDATION_REGISTRY_PATH,
    evaluate_adult_foundation_qualification,
)
from Core.avatar_adult_female_surface_authoring import (
    METHOD_ID as ADULT_SURFACE_METHOD_ID,
    frame_from_mapping,
    parameters_from_mapping,
)
from Core.avatar_adult_female_surface_authoring_v2 import (
    METHOD_ID as ADULT_SURFACE_DETAIL_METHOD_ID,
)
from Core.avatar_body_style_profile import validate_body_style_profile


BUILDER_CONFIG_PATH = Path(
    "Avatar/avatar_builder/tooling/profiled_adult_candidate_builder_v1.json"
)
QUALIFIED_FOUNDATION_AUTHORING_CONFIG = Path(
    "Avatar/avatar_builder/tooling/"
    "makehuman_adult_female_foundation_inactive_authoring_v1.json"
)
QUALIFIED_FOUNDATION_AUTHORING_CONFIG_SHA256 = (
    "9c42dd4056ba5d0543cdee211d4b95c04d17d48f1a437348e2fedfbcb3e60d07"
)
REQUIRED_FOUNDATION_ID = "generic_makehuman_adult_female_foundation_v1_20260801"
OUTPUT_ROOT = Path("Avatar/private_owner_review")
OFFICIAL_BASE = Path(
    "Avatar/avatar_builder/tooling/makehuman_official/"
    "makehuman/data/3dobjs/base.obj"
)
OFFICIAL_FEMALE_MACROS = (
    Path(
        "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/"
        "targets/macrodetails/"
        "universal-female-young-averagemuscle-averageweight.target"
    ),
    Path(
        "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/"
        "targets/macrodetails/caucasian-female-young.target"
    ),
)
OFFICIAL_RIG = Path(
    "Avatar/avatar_builder/tooling/makehuman_official/"
    "makehuman/data/rigs/default.mhskel"
)
OFFICIAL_WEIGHTS = Path(
    "Avatar/avatar_builder/tooling/makehuman_official/"
    "makehuman/data/rigs/default_weights.mhw"
)
LIVE_KIRA_STATE_FILES = (
    Path("Avatar/models/temp_ai/kira/avatar.glb"),
    Path("Avatar/state/body_selections/kira_runtime_body_selection.json"),
    Path("Data/runtime/kira_world_shell_state.json"),
)
OWNER_REVIEW_VIEW_LABELS = (
    "front",
    "rear",
    "left_profile",
    "right_profile",
    "left_three_quarter",
    "right_three_quarter",
    "face_close",
    "eyes_close",
    "left_hand_nails_close",
    "right_hand_nails_close",
    "left_foot_nails_close",
    "right_foot_nails_close",
    "left_knee_flexion",
    "right_knee_flexion",
    "protected_adult_relationship_front",
    "protected_adult_relationship_side",
    "protected_adult_relationship_three_quarter",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_OUTPUT_NAME_RE = re.compile(r"^kira_profiled_adult_candidate_[a-z0-9_]{8,95}$")

ROOT_FIELDS = {
    "schema_version",
    "builder_id",
    "required_qualified_foundation_id",
    "style_profile",
    "makehuman_source_set",
    "official_rig",
    "source_license",
    "adult_surface_authoring",
    "output_policy",
    "protected_live_kira_state",
    "owner_review_view_labels",
    "hair_provider_interface",
}


class ProfiledAdultCandidateContractError(ValueError):
    """Raised when a caller requests a blocked builder configuration."""


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


def _mapping(value: Any, label: str, blockers: list[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        blockers.append(f"{label}_must_be_object")
        return {}
    return value


def _exact_fields(
    value: Mapping[str, Any],
    expected: set[str],
    label: str,
    blockers: list[str],
) -> None:
    blockers.extend(
        f"{label}_field_missing:{name}"
        for name in sorted(expected.difference(value))
    )
    blockers.extend(
        f"{label}_field_unexpected:{name}"
        for name in sorted(set(value).difference(expected))
    )


def _safe_project_file(
    root: Path,
    raw: Any,
    *,
    label: str,
    blockers: list[str],
    expected: Path | None = None,
    suffix: str | None = None,
) -> Path | None:
    value = _text(raw)
    relative = Path(value)
    if not value or relative.is_absolute() or ".." in relative.parts:
        blockers.append(f"{label}_path_unsafe")
        return None
    if expected is not None and relative.as_posix() != expected.as_posix():
        blockers.append(f"{label}_path_not_exact_official_asset")
        return None
    project = root.resolve()
    path = (project / relative).resolve()
    try:
        path.relative_to(project)
    except ValueError:
        blockers.append(f"{label}_path_escaped_project")
        return None
    if suffix is not None and path.suffix.lower() != suffix.lower():
        blockers.append(f"{label}_suffix_invalid")
        return None
    if not path.is_file():
        blockers.append(f"{label}_file_missing")
        return None
    return path


def _binding(
    root: Path,
    value: Any,
    *,
    label: str,
    blockers: list[str],
    expected: Path | None = None,
    suffix: str | None = None,
) -> dict[str, str]:
    record = _mapping(value, f"{label}_binding", blockers)
    expected_digest = _text(record.get("sha256")).lower()
    if not SHA256_RE.fullmatch(expected_digest):
        blockers.append(f"{label}_sha256_invalid")
    path = _safe_project_file(
        root,
        record.get("path"),
        label=label,
        blockers=blockers,
        expected=expected,
        suffix=suffix,
    )
    actual = _sha256(path) if path is not None else ""
    if path is not None and SHA256_RE.fullmatch(expected_digest) and actual != expected_digest:
        blockers.append(f"{label}_sha256_mismatch")
    return {
        "path": path.relative_to(root.resolve()).as_posix() if path else _text(record.get("path")),
        "sha256": actual,
    }


def scaled_adult_surface_settings(
    authoring: Mapping[str, Any],
    target_height_m: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Scale metric authoring settings while leaving normalized axes intact."""

    if isinstance(target_height_m, bool):
        raise ProfiledAdultCandidateContractError("target_height_m_invalid")
    target = float(target_height_m)
    baseline = float(authoring.get("baseline_height_m") or 0.0)
    if not 1.35 <= target <= 2.05 or not 1.35 <= baseline <= 2.05:
        raise ProfiledAdultCandidateContractError("authoring_height_out_of_bounds")
    if authoring.get("scale_frame_and_metric_parameters_to_target_height") is not True:
        raise ProfiledAdultCandidateContractError("authoring_metric_scaling_not_required")
    ratio = target / baseline
    frame = dict(_mapping(authoring.get("frame"), "authoring_frame", []))
    parameters = dict(_mapping(authoring.get("parameters"), "authoring_parameters", []))
    frame["origin"] = [float(value) * ratio for value in frame.get("origin", [])]
    for name in ("half_width_m", "half_length_m", "max_surface_offset_m"):
        frame[name] = float(frame.get(name) or 0.0) * ratio
    parameters["relief_scale_m"] = float(parameters.get("relief_scale_m") or 0.0) * ratio
    parameters["degeneracy_area_m2"] = (
        float(parameters.get("degeneracy_area_m2") or 0.0) * ratio * ratio
    )
    # These constructors validate axes, bounded dimensions, and parameters.
    frame_from_mapping(frame)
    parameters_from_mapping(parameters)
    return frame, parameters


def validate_profiled_candidate_builder_config(
    project_root: Path,
    config_path: Path | str = BUILDER_CONFIG_PATH,
) -> dict[str, Any]:
    """Validate exact builder assets and policy without evaluating output."""

    root = Path(project_root).resolve()
    blockers: list[str] = []
    path = _safe_project_file(
        root,
        Path(config_path).as_posix(),
        label="builder_config",
        blockers=blockers,
        suffix=".json",
    )
    payload: dict[str, Any] = {}
    digest = ""
    if path is not None:
        digest = _sha256(path)
        try:
            payload = _read_json(path)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            blockers.append("builder_config_json_invalid")
    resolved: dict[str, Any] = {}
    if payload:
        _exact_fields(payload, ROOT_FIELDS, "builder_config", blockers)
        if payload.get("schema_version") != 1:
            blockers.append("builder_config_schema_invalid")
        if payload.get("builder_id") != "profiled_confirmed_adult_female_candidate_builder_v1":
            blockers.append("builder_id_invalid")
        if payload.get("required_qualified_foundation_id") != REQUIRED_FOUNDATION_ID:
            blockers.append("required_foundation_id_invalid")

        style = _mapping(payload.get("style_profile"), "style_profile", blockers)
        _exact_fields(
            style,
            {
                "path",
                "sha256",
                "required_profile_id",
                "required_target_count",
                "required_target_height_m",
            },
            "style_profile",
            blockers,
        )
        resolved["style_profile"] = _binding(
            root,
            style,
            label="style_profile",
            blockers=blockers,
            suffix=".json",
        )
        if style.get("required_profile_id") != "natural_athletic_warm_asymmetric_waves_v1":
            blockers.append("required_style_profile_id_invalid")
        if style.get("required_target_count") != 12:
            blockers.append("required_style_target_count_invalid")
        if style.get("required_target_height_m") != 1.651:
            blockers.append("required_target_height_invalid")

        source = _mapping(payload.get("makehuman_source_set"), "makehuman_source_set", blockers)
        _exact_fields(
            source,
            {
                "base_body",
                "female_macros",
                "male_helper_groups_allowed",
                "copied_anatomy_geometry_allowed",
            },
            "makehuman_source_set",
            blockers,
        )
        base = _mapping(source.get("base_body"), "makehuman_base_body", blockers)
        if base.get("face_group") != "body":
            blockers.append("makehuman_base_face_group_invalid")
        resolved["base_body"] = _binding(
            root,
            base,
            label="makehuman_base_body",
            blockers=blockers,
            expected=OFFICIAL_BASE,
            suffix=".obj",
        )
        macros = source.get("female_macros")
        if not isinstance(macros, list) or len(macros) != len(OFFICIAL_FEMALE_MACROS):
            blockers.append("female_macro_bindings_incomplete")
            macros = []
        resolved_macros = []
        for index, expected in enumerate(OFFICIAL_FEMALE_MACROS):
            raw = macros[index] if index < len(macros) else {}
            macro = _mapping(raw, f"female_macro_{index}", blockers)
            if macro.get("weight") != 1.0:
                blockers.append(f"female_macro_{index}_weight_invalid")
            resolved_macros.append(
                {
                    **_binding(
                        root,
                        macro,
                        label=f"female_macro_{index}",
                        blockers=blockers,
                        expected=expected,
                        suffix=".target",
                    ),
                    "weight": macro.get("weight"),
                }
            )
        resolved["female_macros"] = resolved_macros
        if source.get("male_helper_groups_allowed") is not False:
            blockers.append("male_helper_groups_not_blocked")
        if source.get("copied_anatomy_geometry_allowed") is not False:
            blockers.append("copied_anatomy_geometry_not_blocked")

        rig = _mapping(payload.get("official_rig"), "official_rig", blockers)
        _exact_fields(
            rig,
            {
                "skeleton",
                "weights",
                "maximum_influences",
                "normalize_every_vertex",
                "fallback_root_for_unweighted",
            },
            "official_rig",
            blockers,
        )
        resolved["skeleton"] = _binding(
            root,
            rig.get("skeleton"),
            label="official_skeleton",
            blockers=blockers,
            expected=OFFICIAL_RIG,
            suffix=".mhskel",
        )
        resolved["weights"] = _binding(
            root,
            rig.get("weights"),
            label="official_weights",
            blockers=blockers,
            expected=OFFICIAL_WEIGHTS,
            suffix=".mhw",
        )
        if rig.get("maximum_influences") != 4:
            blockers.append("official_rig_maximum_influences_invalid")
        if rig.get("normalize_every_vertex") is not True:
            blockers.append("official_rig_normalization_not_required")
        if rig.get("fallback_root_for_unweighted") is not True:
            blockers.append("official_rig_unweighted_fallback_not_required")

        license_record = _mapping(payload.get("source_license"), "source_license", blockers)
        if license_record.get("license_id") != "CC0-1.0":
            blockers.append("source_license_not_cc0")
        if license_record.get("adaptation_allowed") is not True:
            blockers.append("source_adaptation_not_allowed")
        if license_record.get("foundation_and_style_use_allowed") is not True:
            blockers.append("source_foundation_style_use_not_allowed")
        resolved["license_evidence"] = _binding(
            root,
            license_record.get("evidence"),
            label="source_license_evidence",
            blockers=blockers,
            suffix=".md",
        )

        authoring = _mapping(payload.get("adult_surface_authoring"), "adult_surface_authoring", blockers)
        _exact_fields(
            authoring,
            {
                "method_id",
                "qualified_neutral_config",
                "baseline_height_m",
                "scale_frame_and_metric_parameters_to_target_height",
                "frame",
                "parameters",
                "structured_detail_refinement",
                "retain_all_landmark_groups",
                "independent_requalification_required",
            },
            "adult_surface_authoring",
            blockers,
        )
        if authoring.get("method_id") != ADULT_SURFACE_METHOD_ID:
            blockers.append("adult_surface_method_id_invalid")
        if authoring.get("retain_all_landmark_groups") is not True:
            blockers.append("adult_landmark_retention_not_required")
        if authoring.get("independent_requalification_required") is not True:
            blockers.append("adult_surface_requalification_not_required")
        detail = _mapping(
            authoring.get("structured_detail_refinement"),
            "structured_detail_refinement",
            blockers,
        )
        _exact_fields(
            detail,
            {
                "method_id",
                "baseline_relief_scale_m",
                "boundary_taper_power",
                "posterior_frame",
                "continuous_primary_surface_only",
                "no_internal_tract_claim",
                "independent_topology_relationship_visual_requalification_required",
            },
            "structured_detail_refinement",
            blockers,
        )
        if detail.get("method_id") != ADULT_SURFACE_DETAIL_METHOD_ID:
            blockers.append("adult_surface_detail_method_id_invalid")
        try:
            detail_relief = float(detail.get("baseline_relief_scale_m"))
        except (TypeError, ValueError):
            detail_relief = 0.0
        if not 0.0025 <= detail_relief <= 0.008:
            blockers.append("adult_surface_detail_relief_scale_invalid")
        if detail.get("boundary_taper_power") != 2:
            blockers.append("adult_surface_detail_taper_invalid")
        try:
            frame_from_mapping(
                _mapping(
                    detail.get("posterior_frame"),
                    "structured_detail_posterior_frame",
                    blockers,
                )
            )
        except (TypeError, ValueError):
            blockers.append("adult_surface_detail_posterior_frame_invalid")
        if detail.get("continuous_primary_surface_only") is not True:
            blockers.append("adult_surface_detail_continuity_not_required")
        if detail.get("no_internal_tract_claim") is not True:
            blockers.append("adult_surface_detail_scope_invalid")
        if (
            detail.get(
                "independent_topology_relationship_visual_requalification_required"
            )
            is not True
        ):
            blockers.append("adult_surface_detail_requalification_not_required")
        neutral_binding = _mapping(
            authoring.get("qualified_neutral_config"),
            "qualified_neutral_config",
            blockers,
        )
        _exact_fields(
            neutral_binding,
            {"path", "sha256"},
            "qualified_neutral_config",
            blockers,
        )
        if (
            _text(neutral_binding.get("sha256")).lower()
            != QUALIFIED_FOUNDATION_AUTHORING_CONFIG_SHA256
        ):
            blockers.append("qualified_neutral_config_not_exact_qualified_sha256")
        resolved["qualified_neutral_config"] = _binding(
            root,
            neutral_binding,
            label="qualified_neutral_config",
            blockers=blockers,
            expected=QUALIFIED_FOUNDATION_AUTHORING_CONFIG,
            suffix=".json",
        )
        neutral_path = _safe_project_file(
            root,
            neutral_binding.get("path"),
            label="qualified_neutral_config_semantic_source",
            blockers=blockers,
            expected=QUALIFIED_FOUNDATION_AUTHORING_CONFIG,
            suffix=".json",
        )
        neutral: Mapping[str, Any] = {}
        if neutral_path is not None:
            try:
                neutral = _read_json(neutral_path)
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
                blockers.append("qualified_neutral_config_json_invalid")
        if neutral:
            if neutral.get("schema_version") != 1:
                blockers.append("qualified_neutral_config_schema_invalid")
            if neutral.get("foundation_id") != "makehuman_hm08_female_macro_source":
                blockers.append("qualified_neutral_config_foundation_id_invalid")
            if neutral.get("target_height_m") != authoring.get("baseline_height_m"):
                blockers.append("adult_surface_baseline_not_exact_qualified_height")
            if authoring.get("frame") != neutral.get("frame"):
                blockers.append("adult_surface_frame_not_exact_qualified_config")
            if authoring.get("parameters") != neutral.get("parameters"):
                blockers.append("adult_surface_parameters_not_exact_qualified_config")
        try:
            scaled_adult_surface_settings(authoring, 1.651)
        except (TypeError, ValueError, ProfiledAdultCandidateContractError) as exc:
            blockers.append(f"adult_surface_settings_invalid:{type(exc).__name__}")

        output = _mapping(payload.get("output_policy"), "output_policy", blockers)
        if output.get("allowed_root") != OUTPUT_ROOT.as_posix():
            blockers.append("output_allowed_root_invalid")
        if output.get("required_directory_prefix") != "kira_profiled_adult_candidate_":
            blockers.append("output_directory_prefix_invalid")
        required_output_flags = {
            "direct_new_child_only": True,
            "overwrite_allowed": False,
            "inactive": True,
            "assigned": False,
            "clothing_included": False,
            "publication_allowed": False,
            "runtime_activation_allowed": False,
            "private_glb_allowed_only_with_explicit_flag": True,
            "owner_review_rendering_allowed_only_with_explicit_flag": True,
        }
        for name, expected in required_output_flags.items():
            if output.get(name) is not expected:
                blockers.append(f"output_policy_flag_invalid:{name}")

        live = payload.get("protected_live_kira_state")
        if live != [path.as_posix() for path in LIVE_KIRA_STATE_FILES]:
            blockers.append("protected_live_kira_state_set_invalid")
        views = payload.get("owner_review_view_labels")
        if views != list(OWNER_REVIEW_VIEW_LABELS):
            blockers.append("owner_review_view_labels_invalid")
        hair = _mapping(payload.get("hair_provider_interface"), "hair_provider_interface", blockers)
        if hair.get("callable_name") != "build_dynamic_hair":
            blockers.append("hair_provider_callable_invalid")
        required_hair_flags = {
            "provider_must_be_project_relative_and_sha256_bound": True,
            "provider_optional_for_hairless_engineering_candidate": True,
            "static_legacy_hair_import_allowed": False,
            "blackproject_hair_or_geometry_allowed": False,
            "wind_and_wet_runtime_proof_still_required": True,
        }
        for name, expected in required_hair_flags.items():
            if hair.get(name) is not expected:
                blockers.append(f"hair_provider_flag_invalid:{name}")
    blockers = _dedupe(blockers)
    return {
        "schema_version": 1,
        "validation": "profiled_adult_candidate_builder_config_v1",
        "status": "VALIDATED_BUILDER_CONFIG" if not blockers else "BLOCKED_BUILDER_CONFIG",
        "valid": not blockers,
        "config_path": path.relative_to(root).as_posix() if path else Path(config_path).as_posix(),
        "config_sha256": digest,
        "resolved_bindings": resolved,
        "blockers": blockers,
        "build_performed": False,
        "blender_invoked": False,
        "output_created": False,
        "runtime_mutation_performed": False,
    }


def load_validated_profiled_candidate_builder_config(
    project_root: Path,
    config_path: Path | str = BUILDER_CONFIG_PATH,
) -> tuple[dict[str, Any], dict[str, Any]]:
    report = validate_profiled_candidate_builder_config(project_root, config_path)
    if not report["valid"]:
        raise ProfiledAdultCandidateContractError("; ".join(report["blockers"]))
    path = Path(project_root).resolve() / Path(report["config_path"])
    return _read_json(path), report


def capture_live_kira_state_hashes(project_root: Path) -> dict[str, str]:
    """Hash the exact three live-state files or fail before candidate work."""

    root = Path(project_root).resolve(strict=True)
    result: dict[str, str] = {}
    for relative in LIVE_KIRA_STATE_FILES:
        path = (root / relative).resolve(strict=True)
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ProfiledAdultCandidateContractError(
                f"live_state_path_escaped:{relative.as_posix()}"
            ) from exc
        if not path.is_file():
            raise ProfiledAdultCandidateContractError(
                f"live_state_file_missing:{relative.as_posix()}"
            )
        result[relative.as_posix()] = _sha256(path)
    return result


def verify_live_kira_state_unchanged(
    project_root: Path,
    before: Mapping[str, str],
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        after = capture_live_kira_state_hashes(project_root)
    except (OSError, ProfiledAdultCandidateContractError) as exc:
        after = {}
        blockers.append(f"live_state_after_unavailable:{type(exc).__name__}")
    expected_keys = [path.as_posix() for path in LIVE_KIRA_STATE_FILES]
    if list(before) != expected_keys:
        blockers.append("live_state_before_set_invalid")
    for path in expected_keys:
        expected = _text(before.get(path)).lower()
        if not SHA256_RE.fullmatch(expected):
            blockers.append(f"live_state_before_sha256_invalid:{path}")
        elif after.get(path) != expected:
            blockers.append(f"live_state_changed:{path}")
    blockers = _dedupe(blockers)
    return {
        "passed": not blockers,
        "before": dict(before),
        "after": after,
        "blockers": blockers,
    }


def _private_output_path(
    root: Path,
    output_dir: Path | str,
    blockers: list[str],
) -> Path | None:
    relative = Path(output_dir)
    if relative.is_absolute() or ".." in relative.parts:
        blockers.append("output_directory_unsafe")
        return None
    if relative.parent.as_posix() != OUTPUT_ROOT.as_posix():
        blockers.append("output_directory_not_direct_private_owner_review_child")
        return None
    if not SAFE_OUTPUT_NAME_RE.fullmatch(relative.name):
        blockers.append("output_directory_name_invalid")
        return None
    project = root.resolve()
    output = (project / relative).resolve()
    try:
        output.relative_to((project / OUTPUT_ROOT).resolve())
    except ValueError:
        blockers.append("output_directory_escaped_private_root")
        return None
    if output.exists():
        blockers.append("output_directory_already_exists_refuse_overwrite")
    return output


def evaluate_profiled_candidate_preflight(
    project_root: Path,
    output_dir: Path | str,
    *,
    config_path: Path | str = BUILDER_CONFIG_PATH,
) -> dict[str, Any]:
    """Evaluate every gate before Blender is allowed to mutate a scene."""

    root = Path(project_root).resolve(strict=True)
    blockers: list[str] = []
    config_report = validate_profiled_candidate_builder_config(root, config_path)
    blockers.extend(config_report["blockers"])
    try:
        config = _read_json(root / Path(config_report["config_path"]))
    except (OSError, ValueError, json.JSONDecodeError):
        config = {}
    foundation = evaluate_adult_foundation_qualification(
        root,
        REQUIRED_FOUNDATION_ID,
    )
    foundation_gate_files: dict[str, str] = {}
    for relative in (
        ADULT_FOUNDATION_POLICY_PATH,
        ADULT_FOUNDATION_REGISTRY_PATH,
    ):
        gate_path = (root / relative).resolve()
        if not gate_path.is_file():
            blockers.append(f"foundation_gate_file_missing:{relative.as_posix()}")
        else:
            foundation_gate_files[relative.as_posix()] = _sha256(gate_path)
    if foundation.get("foundation_id") != REQUIRED_FOUNDATION_ID:
        blockers.append("foundation_result_id_mismatch")
    if foundation.get("qualified_for_adult_foundation") is not True:
        blockers.append("required_generic_adult_foundation_not_qualified")
    style_binding = config.get("style_profile") if isinstance(config.get("style_profile"), Mapping) else {}
    style_path = Path(_text(style_binding.get("path")) or ".")
    style = validate_body_style_profile(root, style_path)
    if style.get("valid") is not True:
        blockers.append("exact_style_profile_not_valid")
    if style.get("profile_sha256") != _text(style_binding.get("sha256")).lower():
        blockers.append("exact_style_profile_hash_mismatch")
    if style.get("profile_id") != style_binding.get("required_profile_id"):
        blockers.append("exact_style_profile_id_mismatch")
    if style.get("target_count") != style_binding.get("required_target_count"):
        blockers.append("exact_style_target_count_mismatch")
    try:
        profile_payload = _read_json(root / style_path)
        height = float(profile_payload.get("dimensions", {}).get("target_height_m"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        height = 0.0
    if height != style_binding.get("required_target_height_m"):
        blockers.append("exact_style_target_height_mismatch")
    output = _private_output_path(root, output_dir, blockers)
    try:
        live_hashes = capture_live_kira_state_hashes(root)
    except (OSError, ProfiledAdultCandidateContractError) as exc:
        live_hashes = {}
        blockers.append(f"live_kira_state_preflight_failed:{type(exc).__name__}")
    blockers = _dedupe(blockers)
    return {
        "schema_version": 1,
        "preflight": "profiled_confirmed_adult_female_candidate_v1",
        "status": "READY_FOR_EXPLICIT_INACTIVE_BUILD" if not blockers else "BLOCKED_BEFORE_BLENDER_MUTATION",
        "ready": not blockers,
        "required_foundation_id": REQUIRED_FOUNDATION_ID,
        "foundation": foundation,
        "foundation_gate_files": foundation_gate_files,
        "style_profile": style,
        "builder_config": config_report,
        "target_height_m": height,
        "output_directory": output.relative_to(root).as_posix() if output else Path(output_dir).as_posix(),
        "live_kira_state_before": live_hashes,
        "blockers": blockers,
        "build_performed": False,
        "blender_scene_mutated": False,
        "render_performed": False,
        "candidate_saved": False,
        "private_glb_exported": False,
        "runtime_mutation_performed": False,
        "runtime_activation_allowed": False,
    }


__all__ = [
    "BUILDER_CONFIG_PATH",
    "LIVE_KIRA_STATE_FILES",
    "OFFICIAL_BASE",
    "OFFICIAL_FEMALE_MACROS",
    "OFFICIAL_RIG",
    "OFFICIAL_WEIGHTS",
    "OUTPUT_ROOT",
    "OWNER_REVIEW_VIEW_LABELS",
    "QUALIFIED_FOUNDATION_AUTHORING_CONFIG",
    "QUALIFIED_FOUNDATION_AUTHORING_CONFIG_SHA256",
    "ProfiledAdultCandidateContractError",
    "REQUIRED_FOUNDATION_ID",
    "capture_live_kira_state_hashes",
    "evaluate_profiled_candidate_preflight",
    "load_validated_profiled_candidate_builder_config",
    "scaled_adult_surface_settings",
    "validate_profiled_candidate_builder_config",
    "verify_live_kira_state_unchanged",
]
