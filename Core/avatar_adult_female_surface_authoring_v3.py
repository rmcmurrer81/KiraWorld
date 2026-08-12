"""Camera-visible continuous adult-female external-surface method v3.

V1 established a closed, weighted, one-component authoring patch.  V2 added
signed detail but its single tilted chart can cross from the visible ventral
sheet onto the returning under-body sheet.  This identity-free v3 contract
separates the camera-front vulvar chart from the rear anal chart and requires
local primary-surface subdivision before evaluating small rims and recesses.

The method still describes only one capped external skin surface.  It creates
no helper anatomy, Boolean, copied anatomy, open tract, paint-only substitute,
identity, runtime selection, render, export, or activation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any, Mapping

from Core.avatar_adult_female_surface_authoring import (
    LANDMARK_GROUP_PREFIX,
    POLICY_PATH,
    REQUIRED_RELATIONSHIPS,
    SurfaceFrame,
    landmark_group_name,
)


METHOD_ID = "generic_continuous_adult_female_external_surface_v3"
BASE_DETAIL_METHOD_ID = "generic_continuous_adult_female_external_surface_v2"
OPENING_REPRESENTATION = (
    "camera_visible_annular_rim_and_recessed_cap_on_continuous_primary_surface"
)


@dataclass(frozen=True)
class VisibleSurfaceParameters:
    local_subdivision_cuts: int = 3
    front_prominence_scale_m: float = 0.0060
    rear_prominence_scale_m: float = 0.0055
    minimum_front_normal_alignment: float = 0.12
    minimum_rear_normal_alignment: float = 0.10
    minimum_feature_vertices: int = 10
    maximum_skin_influences: int = 4
    degeneracy_area_m2: float = 1.0e-12
    maximum_new_vertices: int = 12000


# All vulvar structures are deliberately kept on the measured camera-visible
# front sheet.  Positive v is superior/anterior in this chart.
FRONT_FEATURE_SAMPLE_POINTS: Mapping[str, tuple[float, float]] = {
    "mons_pubis": (0.0, 0.72),
    "labia_majora_left": (0.24, 0.20),
    "labia_majora_right": (-0.24, 0.20),
    "labia_minora_left": (0.085, 0.19),
    "labia_minora_right": (-0.085, 0.19),
    "clitoral_hood": (0.0, 0.48),
    "clitoris": (0.0, 0.40),
    "vestibule": (0.0, 0.20),
    "urethral_opening": (0.0, 0.30),
    "urethral_rim_left": (0.060, 0.30),
    "vaginal_opening": (0.0, 0.10),
    "vaginal_rim_left": (0.105, 0.10),
    "fourchette": (0.0, -0.02),
}

# Positive v is superior in the rear chart.  The anal recess is therefore
# superior/posterior to the lower perineal transition on that visible sheet.
REAR_FEATURE_SAMPLE_POINTS: Mapping[str, tuple[float, float]] = {
    "perineal_transition": (0.0, -0.18),
    "anal_recess": (0.0, 0.15),
    "anal_rim_left": (0.13, 0.15),
}


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be a finite number")
    return result


def parameters_from_mapping(value: Mapping[str, Any] | None) -> VisibleSurfaceParameters:
    raw = dict(value or {})
    allowed = set(VisibleSurfaceParameters.__dataclass_fields__)
    unexpected = sorted(set(raw).difference(allowed))
    if unexpected:
        raise ValueError(f"unknown v3 parameter(s): {', '.join(unexpected)}")
    defaults = VisibleSurfaceParameters()
    integer_names = {
        "local_subdivision_cuts",
        "minimum_feature_vertices",
        "maximum_skin_influences",
        "maximum_new_vertices",
    }
    parsed: dict[str, int | float] = {}
    for name in allowed:
        supplied = raw.get(name, getattr(defaults, name))
        if name in integer_names:
            if isinstance(supplied, bool) or not isinstance(supplied, int):
                raise ValueError(f"{name} must be an integer")
            parsed[name] = supplied
        else:
            parsed[name] = _finite_number(supplied, name)
    result = VisibleSurfaceParameters(**parsed)  # type: ignore[arg-type]
    if not 1 <= result.local_subdivision_cuts <= 3:
        raise ValueError("local_subdivision_cuts must remain within [1, 3]")
    if not 0.0035 <= result.front_prominence_scale_m <= 0.009:
        raise ValueError("front_prominence_scale_m outside [0.0035, 0.009]")
    if not 0.003 <= result.rear_prominence_scale_m <= 0.008:
        raise ValueError("rear_prominence_scale_m outside [0.003, 0.008]")
    if not 0.05 <= result.minimum_front_normal_alignment <= 0.50:
        raise ValueError("minimum_front_normal_alignment outside [0.05, 0.50]")
    if not 0.05 <= result.minimum_rear_normal_alignment <= 0.50:
        raise ValueError("minimum_rear_normal_alignment outside [0.05, 0.50]")
    if not 4 <= result.minimum_feature_vertices <= 64:
        raise ValueError("minimum_feature_vertices outside [4, 64]")
    if not 1 <= result.maximum_skin_influences <= 8:
        raise ValueError("maximum_skin_influences outside [1, 8]")
    if not 1000 <= result.maximum_new_vertices <= 50000:
        raise ValueError("maximum_new_vertices outside [1000, 50000]")
    if not 1.0e-16 <= result.degeneracy_area_m2 <= 1.0e-8:
        raise ValueError("degeneracy_area_m2 outside bounded range")
    return result


def load_required_relationships(project_root: Path) -> tuple[str, ...]:
    root = Path(project_root).resolve(strict=True)
    path = (root / POLICY_PATH).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("adult-foundation policy escaped the project root") from exc
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    values = payload.get("required_adult_female_relationships")
    if not isinstance(values, list) or not all(
        isinstance(value, str) and value.strip() for value in values
    ):
        raise ValueError("adult-foundation relationship policy is invalid")
    normalized = tuple(value.strip() for value in values)
    if normalized != REQUIRED_RELATIONSHIPS:
        raise ValueError("v3 relationship contract drifted from policy")
    return normalized


def _g(u: float, v: float, *, cu: float, cv: float, su: float, sv: float) -> float:
    return math.exp(
        -0.5
        * (
            ((float(u) - cu) / su) ** 2
            + ((float(v) - cv) / sv) ** 2
        )
    )


def _smoothstep(value: float) -> float:
    t = max(0.0, min(1.0, float(value)))
    return t * t * (3.0 - 2.0 * t)


def _curved_paired_ridge(
    u: float,
    v: float,
    *,
    side: float,
    base_center: float,
    center_bulge: float,
    curve_center_v: float,
    curve_scale_v: float,
    width_u: float,
    envelope_center_v: float,
    envelope_scale_v: float,
) -> float:
    """Return one tapered ridge whose two ends converge toward the midline."""

    center = float(side) * (
        float(base_center)
        + float(center_bulge)
        * math.exp(
            -0.5
            * ((float(v) - float(curve_center_v)) / float(curve_scale_v)) ** 2
        )
    )
    across = math.exp(-0.5 * ((float(u) - center) / float(width_u)) ** 2)
    along = math.exp(
        -0.5
        * ((float(v) - float(envelope_center_v)) / float(envelope_scale_v)) ** 4
    )
    return across * along


def front_support_taper(u: float, v: float) -> float:
    abs_u = abs(float(u))
    if abs_u >= 0.58 or float(v) <= -0.12 or float(v) >= 0.79:
        return 0.0
    lateral = 1.0 if abs_u <= 0.48 else _smoothstep((0.58 - abs_u) / 0.10)
    lower = 1.0 if float(v) >= -0.05 else _smoothstep((float(v) + 0.12) / 0.07)
    upper = 1.0 if float(v) <= 0.70 else _smoothstep((0.79 - float(v)) / 0.09)
    return lateral * lower * upper


def rear_support_taper(u: float, v: float) -> float:
    abs_u = abs(float(u))
    if abs_u >= 0.52 or float(v) <= -0.38 or float(v) >= 0.48:
        return 0.0
    lateral = 1.0 if abs_u <= 0.40 else _smoothstep((0.52 - abs_u) / 0.12)
    lower = 1.0 if float(v) >= -0.30 else _smoothstep((float(v) + 0.38) / 0.08)
    upper = 1.0 if float(v) <= 0.40 else _smoothstep((0.48 - float(v)) / 0.08)
    return lateral * lower * upper


def front_structured_field(u: float, v: float) -> float:
    """Nested visible-sheet folds, sulci, annular rims, and capped recesses."""

    value = 0.13 * _g(u, v, cu=0.0, cv=0.72, su=0.46, sv=0.12)

    # The paired folds follow converging centerlines instead of four parallel
    # Gaussian bars.  This keeps the upper and lower ends continuous with the
    # surrounding skin while preserving distinct left/right relief.
    for side in (-1.0, 1.0):
        value += 0.72 * _curved_paired_ridge(
            u,
            v,
            side=side,
            base_center=0.11,
            center_bulge=0.13,
            curve_center_v=0.19,
            curve_scale_v=0.22,
            width_u=0.080,
            envelope_center_v=0.19,
            envelope_scale_v=0.31,
        )
        value -= 0.13 * _curved_paired_ridge(
            u,
            v,
            side=side,
            base_center=0.29,
            center_bulge=0.055,
            curve_center_v=0.19,
            curve_scale_v=0.25,
            width_u=0.070,
            envelope_center_v=0.19,
            envelope_scale_v=0.32,
        )
        value += 0.52 * _curved_paired_ridge(
            u,
            v,
            side=side,
            base_center=0.033,
            center_bulge=0.057,
            curve_center_v=0.19,
            curve_scale_v=0.16,
            width_u=0.031,
            envelope_center_v=0.19,
            envelope_scale_v=0.205,
        )

    # A shallow vestibular bed separates the nested folds without producing a
    # long black trench in a neutral view.
    value -= 0.10 * _g(u, v, cu=0.0, cv=0.20, su=0.13, sv=0.23)
    value -= 0.09 * _g(u, v, cu=0.0, cv=0.18, su=0.046, sv=0.27)

    # A shallow crescent-like hood, short sulcus, and localized clitoral relief.
    value += 0.48 * _g(u, v, cu=0.0, cv=0.48, su=0.135, sv=0.052)
    value -= 0.17 * _g(u, v, cu=0.0, cv=0.438, su=0.068, sv=0.026)
    value += 0.34 * _g(u, v, cu=0.0, cv=0.40, su=0.036, sv=0.030)

    # Each opening remains a raised annular rim around a recessed, closed cap.
    # The caps are shallower than v3's first prototype so they read as anatomy,
    # not two punched holes; no open boundary or internal tract is created.
    value += 0.24 * _g(u, v, cu=0.0, cv=0.30, su=0.074, sv=0.058)
    value -= 0.76 * _g(u, v, cu=0.0, cv=0.30, su=0.026, sv=0.024)
    value += 0.36 * _g(u, v, cu=0.0, cv=0.10, su=0.120, sv=0.096)
    value -= 0.94 * _g(u, v, cu=0.0, cv=0.10, su=0.052, sv=0.052)

    # The fourchette closes the visible lower relationship before the surface
    # turns toward the separately charted perineum.
    value += 0.27 * _g(u, v, cu=0.0, cv=-0.02, su=0.14, sv=0.040)
    return max(-1.10, min(1.10, value))


def rear_structured_field(u: float, v: float) -> float:
    value = 0.18 * _g(u, v, cu=0.0, cv=-0.18, su=0.31, sv=0.14)
    value += 0.58 * _g(u, v, cu=0.0, cv=0.15, su=0.18, sv=0.14)
    value -= 1.16 * _g(u, v, cu=0.0, cv=0.15, su=0.055, sv=0.055)
    return max(-1.10, min(1.10, value))


def front_surface_displacement(
    u: float,
    v: float,
    *,
    prominence_scale_m: float,
) -> float:
    return float(prominence_scale_m) * front_support_taper(u, v) * front_structured_field(u, v)


def rear_surface_displacement(
    u: float,
    v: float,
    *,
    prominence_scale_m: float,
) -> float:
    return float(prominence_scale_m) * rear_support_taper(u, v) * rear_structured_field(u, v)


def front_landmark_memberships(u: float, v: float, *, threshold: float = 0.18) -> tuple[str, ...]:
    rows: list[str] = []

    def member(cu: float, cv: float, su: float, sv: float) -> bool:
        return _g(u, v, cu=cu, cv=cv, su=su, sv=sv) >= float(threshold)

    if member(0.0, 0.72, 0.46, 0.13):
        rows.append("mons_pubis")
    majora_left = member(0.24, 0.20, 0.12, 0.34)
    majora_right = member(-0.24, 0.20, 0.12, 0.34)
    if majora_left or majora_right:
        rows.append("paired_labia_majora")
    if majora_left:
        rows.append("paired_labia_majora__left")
    if majora_right:
        rows.append("paired_labia_majora__right")
    minora_left = member(0.085, 0.19, 0.055, 0.25)
    minora_right = member(-0.085, 0.19, 0.055, 0.25)
    if minora_left or minora_right:
        rows.append("paired_labia_minora")
    if minora_left:
        rows.append("paired_labia_minora__left")
    if minora_right:
        rows.append("paired_labia_minora__right")
    if member(0.0, 0.48, 0.16, 0.075):
        rows.append("clitoral_hood")
    if member(0.0, 0.40, 0.065, 0.055):
        rows.append("clitoris")
    if member(0.0, 0.20, 0.16, 0.22):
        rows.append("vestibule")
    if member(0.0, 0.30, 0.070, 0.060):
        rows.append("urethral_opening_anterior_to_vaginal_opening")
    if member(0.0, 0.10, 0.12, 0.105):
        rows.append("vaginal_opening")
    if member(0.0, -0.02, 0.15, 0.060):
        rows.append("posterior_commissure_fourchette")
    return tuple(rows)


def rear_landmark_memberships(u: float, v: float, *, threshold: float = 0.18) -> tuple[str, ...]:
    transition = _g(u, v, cu=0.0, cv=-0.18, su=0.32, sv=0.16)
    anal = _g(u, v, cu=0.0, cv=0.15, su=0.15, sv=0.12)
    rows: list[str] = []
    if max(transition, anal) >= threshold:
        rows.append("perineal_transition_to_anus_and_pelvic_floor")
    if transition >= threshold:
        rows.append("perineal_transition_to_anus_and_pelvic_floor__perineal_transition")
    if anal >= threshold:
        rows.append("perineal_transition_to_anus_and_pelvic_floor__posterior_anal_recess")
    return tuple(rows)


def feature_sample_displacements(parameters: VisibleSurfaceParameters) -> dict[str, float]:
    values = {
        name: front_surface_displacement(
            point[0],
            point[1],
            prominence_scale_m=parameters.front_prominence_scale_m,
        )
        for name, point in FRONT_FEATURE_SAMPLE_POINTS.items()
    }
    values.update(
        {
            name: rear_surface_displacement(
                point[0],
                point[1],
                prominence_scale_m=parameters.rear_prominence_scale_m,
            )
            for name, point in REAR_FEATURE_SAMPLE_POINTS.items()
        }
    )
    return values


def _assert_signed_contrasts(samples: Mapping[str, float]) -> None:
    positive = (
        "mons_pubis",
        "labia_majora_left",
        "labia_majora_right",
        "labia_minora_left",
        "labia_minora_right",
        "clitoral_hood",
        "clitoris",
        "urethral_rim_left",
        "vaginal_rim_left",
        "fourchette",
        "perineal_transition",
        "anal_rim_left",
    )
    recessed = ("vestibule", "urethral_opening", "vaginal_opening", "anal_recess")
    if any(samples[name] <= 0.0 for name in positive):
        raise ValueError("v3 positive feature sample lost relief")
    if any(samples[name] >= 0.0 for name in recessed):
        raise ValueError("v3 recessed feature sample lost depth")
    margins = {
        "majora_over_vestibule": min(samples["labia_majora_left"], samples["labia_majora_right"]) - samples["vestibule"],
        "minora_over_vestibule": min(samples["labia_minora_left"], samples["labia_minora_right"]) - samples["vestibule"],
        "urethral_rim_over_cap": samples["urethral_rim_left"] - samples["urethral_opening"],
        "vaginal_rim_over_cap": samples["vaginal_rim_left"] - samples["vaginal_opening"],
        "fourchette_over_vaginal_cap": samples["fourchette"] - samples["vaginal_opening"],
        "anal_rim_over_cap": samples["anal_rim_left"] - samples["anal_recess"],
    }
    required = {
        "majora_over_vestibule": 0.0030,
        "minora_over_vestibule": 0.0025,
        "urethral_rim_over_cap": 0.0030,
        "vaginal_rim_over_cap": 0.0040,
        "fourchette_over_vaginal_cap": 0.0035,
        "anal_rim_over_cap": 0.0030,
    }
    failures = [name for name, minimum in required.items() if margins[name] < minimum]
    if failures:
        raise ValueError("v3 signed contrast gate failed: " + ",".join(failures))


def build_authoring_contract(
    project_root: Path,
    front_frame: SurfaceFrame,
    rear_frame: SurfaceFrame,
    parameters: VisibleSurfaceParameters,
) -> dict[str, Any]:
    relationships = load_required_relationships(project_root)
    samples = feature_sample_displacements(parameters)
    _assert_signed_contrasts(samples)
    if not (
        FRONT_FEATURE_SAMPLE_POINTS["clitoris"][1]
        > FRONT_FEATURE_SAMPLE_POINTS["urethral_opening"][1]
        > FRONT_FEATURE_SAMPLE_POINTS["vaginal_opening"][1]
        > FRONT_FEATURE_SAMPLE_POINTS["fourchette"][1]
    ):
        raise ValueError("v3 ventral anterior/posterior ordering failed")
    if not (
        REAR_FEATURE_SAMPLE_POINTS["anal_recess"][1]
        > REAR_FEATURE_SAMPLE_POINTS["perineal_transition"][1]
    ):
        raise ValueError("v3 rear perineal/anal ordering failed")
    return {
        "schema_version": 3,
        "method_id": METHOD_ID,
        "base_detail_method_id": BASE_DETAIL_METHOD_ID,
        "status": "UNPROMOTED_INACTIVE_AUTHORING_METHOD",
        "body_class": "adult_female",
        "scope": "complete_required_external_relationships_no_internal_tract_claim",
        "front_frame": asdict(front_frame),
        "rear_frame": asdict(rear_frame),
        "parameters": asdict(parameters),
        "relationships": list(relationships),
        "opening_representation": OPENING_REPRESENTATION,
        "feature_sample_displacements_m": samples,
        "chart_separation": {
            "camera_front_vulvar_relationships": True,
            "curved_underbody_perineal_continuity_retained": True,
            "camera_rear_anal_relationship": True,
            "tilted_chart_cross_sheet_sampling_forbidden": True,
        },
        "local_selected_face_subdivision_required": True,
        "same_primary_surface_required": True,
        "source_anatomy_geometry_copy_allowed": False,
        "wrong_sex_helper_allowed": False,
        "separate_anatomy_mesh_allowed": False,
        "boolean_anatomy_union_allowed": False,
        "painted_only_relationship_allowed": False,
        "internal_tract_claim_allowed": False,
        "result_component_count_required": 1,
        "result_boundary_edges_required": 0,
        "result_nonmanifold_edges_required": 0,
        "result_degenerate_faces_required": 0,
        "new_global_nonadjacent_self_intersection_pairs_allowed": False,
        "skin_weights": {
            "preserve_existing_vertices": True,
            "interpolate_new_vertices": True,
            "normalize_new_vertices": True,
            "maximum_influences": parameters.maximum_skin_influences,
        },
        "landmark_group_prefix": LANDMARK_GROUP_PREFIX,
        "landmark_groups": {
            relationship: landmark_group_name(relationship)
            for relationship in relationships
        },
        "feature_samples_are_preflight_not_visual_acceptance": True,
        "independent_topology_review_required": True,
        "independent_relationship_review_required": True,
        "independent_visual_prominence_review_required": True,
        "qualified": False,
        "runtime_activation_allowed": False,
        "render_performed": False,
        "export_performed": False,
    }


__all__ = [
    "BASE_DETAIL_METHOD_ID",
    "FRONT_FEATURE_SAMPLE_POINTS",
    "METHOD_ID",
    "OPENING_REPRESENTATION",
    "REAR_FEATURE_SAMPLE_POINTS",
    "VisibleSurfaceParameters",
    "build_authoring_contract",
    "feature_sample_displacements",
    "front_landmark_memberships",
    "front_structured_field",
    "front_support_taper",
    "front_surface_displacement",
    "load_required_relationships",
    "parameters_from_mapping",
    "rear_landmark_memberships",
    "rear_structured_field",
    "rear_support_taper",
    "rear_surface_displacement",
]
