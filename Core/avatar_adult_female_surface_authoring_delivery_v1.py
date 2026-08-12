"""Bounded delivery field for one continuous adult-female skin surface.

This module is the delivery-only successor to the checkpointed v3 probe.  It
keeps the same one-surface, capped-opening and no-internal-tract constraints,
but replaces the rectangular support chart and parallel Gaussian bars with
rounded transition masks and converging tapered folds.  It has no Blender,
render, save, export, activation, publication, or identity dependency.
"""

from __future__ import annotations

from dataclasses import asdict
import math
from pathlib import Path
from typing import Any, Mapping

from Core.avatar_adult_female_surface_authoring import (
    LANDMARK_GROUP_PREFIX,
    REQUIRED_RELATIONSHIPS,
    SurfaceFrame,
    landmark_group_name,
)
from Core.avatar_adult_female_surface_authoring_v3 import (
    VisibleSurfaceParameters,
    load_required_relationships,
    parameters_from_mapping,
)


METHOD_ID = "generic_continuous_adult_female_external_surface_delivery_v1"
BASE_DETAIL_METHOD_ID = "generic_continuous_adult_female_external_surface_v2"
OPENING_REPRESENTATION = (
    "camera_visible_annular_rim_and_recessed_cap_on_one_closed_primary_surface"
)


FRONT_FEATURE_SAMPLE_POINTS: Mapping[str, tuple[float, float]] = {
    "mons_pubis": (0.0, 0.72),
    "labia_majora_left": (0.245, 0.20),
    "labia_majora_right": (-0.245, 0.20),
    "labia_minora_left": (0.082, 0.19),
    "labia_minora_right": (-0.082, 0.19),
    "clitoral_hood": (0.0, 0.47),
    "clitoris": (0.0, 0.405),
    "vestibule": (0.0, 0.205),
    "urethral_opening": (0.0, 0.29),
    "urethral_rim_left": (0.055, 0.29),
    "vaginal_opening": (0.0, 0.075),
    "vaginal_rim_left": (0.095, 0.075),
    "fourchette": (0.0, -0.05),
}

REAR_FEATURE_SAMPLE_POINTS: Mapping[str, tuple[float, float]] = {
    "perineal_transition": (0.0, -0.18),
    "anal_recess": (0.0, 0.15),
    "anal_rim_left": (0.13, 0.15),
}


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


def _soft_band(value: float, lower: float, upper: float, fade: float) -> float:
    if value <= lower - fade or value >= upper + fade:
        return 0.0
    left = 1.0 if value >= lower else _smoothstep((value - (lower - fade)) / fade)
    right = 1.0 if value <= upper else _smoothstep(((upper + fade) - value) / fade)
    return left * right


def _curved_ridge(
    u: float,
    v: float,
    *,
    side: float,
    end_center: float,
    central_spread: float,
    center_v: float,
    curve_sv: float,
    width_u: float,
    lower_v: float,
    upper_v: float,
    end_fade_v: float,
) -> float:
    """A softly terminated fold that converges at both ends."""

    center = float(side) * (
        float(end_center)
        + float(central_spread)
        * math.exp(-0.5 * ((float(v) - center_v) / curve_sv) ** 2)
    )
    across = math.exp(-0.5 * ((float(u) - center) / width_u) ** 2)
    return across * _soft_band(float(v), lower_v, upper_v, end_fade_v)


def front_support_taper(u: float, v: float) -> float:
    """Rounded chart support with a wide, C1-like transition ring."""

    lateral = _soft_band(abs(float(u)), 0.0, 0.43, 0.23)
    longitudinal = _soft_band(float(v), -0.09, 0.72, 0.16)
    # A rounded superellipse removes the rectangular plate corners while the
    # axis bands keep the exact support compact and auditable.
    radius = ((abs(float(u)) / 0.68) ** 4 + (abs(float(v) - 0.30) / 0.63) ** 4) ** 0.25
    if radius >= 1.0:
        rounded = 0.0
    elif radius <= 0.72:
        rounded = 1.0
    else:
        rounded = _smoothstep((1.0 - radius) / 0.28)
    return lateral * longitudinal * rounded


def rear_support_taper(u: float, v: float) -> float:
    lateral = _soft_band(abs(float(u)), 0.0, 0.36, 0.18)
    longitudinal = _soft_band(float(v), -0.30, 0.40, 0.12)
    radius = ((abs(float(u)) / 0.56) ** 4 + (abs(float(v) - 0.05) / 0.49) ** 4) ** 0.25
    if radius >= 1.0:
        rounded = 0.0
    elif radius <= 0.70:
        rounded = 1.0
    else:
        rounded = _smoothstep((1.0 - radius) / 0.30)
    return lateral * longitudinal * rounded


def front_structured_field(u: float, v: float) -> float:
    """Nested converging folds, vestibule, capped openings and fourchette."""

    value = 0.10 * _g(u, v, cu=0.0, cv=0.72, su=0.42, sv=0.13)

    for side in (-1.0, 1.0):
        # The broad outer fold is strongest centrally and joins the body at
        # both ends without a vertical bar or a hard rectangular shelf.
        value += 0.38 * _curved_ridge(
            u,
            v,
            side=side,
            end_center=0.105,
            central_spread=0.145,
            center_v=0.19,
            curve_sv=0.25,
            width_u=0.090,
            lower_v=-0.08,
            upper_v=0.58,
            end_fade_v=0.16,
        )
        # A shallow sulcus prevents the outer and inner forms becoming one
        # slab while remaining much softer than the checkpointed ridges.
        value -= 0.075 * _curved_ridge(
            u,
            v,
            side=side,
            end_center=0.070,
            central_spread=0.095,
            center_v=0.19,
            curve_sv=0.24,
            width_u=0.040,
            lower_v=-0.04,
            upper_v=0.52,
            end_fade_v=0.13,
        )
        # The inner fold is narrower, slightly shorter and converges into the
        # hood/fourchette instead of remaining parallel to the outer fold.
        value += 0.27 * _curved_ridge(
            u,
            v,
            side=side,
            end_center=0.018,
            central_spread=0.070,
            center_v=0.19,
            curve_sv=0.16,
            width_u=0.030,
            lower_v=-0.015,
            upper_v=0.43,
            end_fade_v=0.10,
        )

    value -= 0.095 * _g(u, v, cu=0.0, cv=0.20, su=0.13, sv=0.22)
    value -= 0.035 * _g(u, v, cu=0.0, cv=0.20, su=0.035, sv=0.25)

    # A shallow hood/sulcus/clitoral sequence rather than one horizontal bar.
    value += 0.23 * _g(u, v, cu=0.0, cv=0.47, su=0.13, sv=0.055)
    value -= 0.085 * _g(u, v, cu=0.0, cv=0.438, su=0.070, sv=0.028)
    value += 0.17 * _g(u, v, cu=0.0, cv=0.405, su=0.034, sv=0.030)

    # Both openings remain closed primary-surface caps surrounded by a low
    # annular rim.  The lower cap is vertically elliptical and deliberately
    # shallower than the rejected punched-hole appearance.
    value += 0.14 * _g(u, v, cu=0.0, cv=0.29, su=0.068, sv=0.054)
    value -= 0.39 * _g(u, v, cu=0.0, cv=0.29, su=0.024, sv=0.022)
    value += 0.23 * _g(u, v, cu=0.0, cv=0.075, su=0.110, sv=0.085)
    value -= 0.56 * _g(u, v, cu=0.0, cv=0.075, su=0.047, sv=0.058)

    value += 0.25 * _g(u, v, cu=0.0, cv=-0.05, su=0.13, sv=0.045)
    return max(-0.85, min(0.85, value))


def rear_structured_field(u: float, v: float) -> float:
    value = 0.10 * _g(u, v, cu=0.0, cv=-0.18, su=0.28, sv=0.13)
    value += 0.31 * _g(u, v, cu=0.0, cv=0.15, su=0.17, sv=0.13)
    value -= 0.72 * _g(u, v, cu=0.0, cv=0.15, su=0.052, sv=0.052)
    return max(-0.85, min(0.85, value))


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

    if member(0.0, 0.72, 0.43, 0.14):
        rows.append("mons_pubis")
    majora_left = member(0.245, 0.20, 0.13, 0.32)
    majora_right = member(-0.245, 0.20, 0.13, 0.32)
    if majora_left or majora_right:
        rows.append("paired_labia_majora")
    if majora_left:
        rows.append("paired_labia_majora__left")
    if majora_right:
        rows.append("paired_labia_majora__right")
    minora_left = member(0.082, 0.19, 0.055, 0.22)
    minora_right = member(-0.082, 0.19, 0.055, 0.22)
    if minora_left or minora_right:
        rows.append("paired_labia_minora")
    if minora_left:
        rows.append("paired_labia_minora__left")
    if minora_right:
        rows.append("paired_labia_minora__right")
    if member(0.0, 0.47, 0.15, 0.075):
        rows.append("clitoral_hood")
    if member(0.0, 0.405, 0.060, 0.052):
        rows.append("clitoris")
    if member(0.0, 0.20, 0.16, 0.22):
        rows.append("vestibule")
    if member(0.0, 0.29, 0.070, 0.060):
        rows.append("urethral_opening_anterior_to_vaginal_opening")
    if member(0.0, 0.075, 0.12, 0.105):
        rows.append("vaginal_opening")
    if member(0.0, -0.05, 0.15, 0.060):
        rows.append("posterior_commissure_fourchette")
    return tuple(rows)


def rear_landmark_memberships(u: float, v: float, *, threshold: float = 0.18) -> tuple[str, ...]:
    transition = _g(u, v, cu=0.0, cv=-0.18, su=0.30, sv=0.16)
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
        raise ValueError("delivery positive feature sample lost relief")
    if any(samples[name] >= 0.0 for name in recessed):
        raise ValueError("delivery recessed feature sample lost depth")
    margins = {
        "majora_over_vestibule": min(samples["labia_majora_left"], samples["labia_majora_right"]) - samples["vestibule"],
        "minora_over_vestibule": min(samples["labia_minora_left"], samples["labia_minora_right"]) - samples["vestibule"],
        "urethral_rim_over_cap": samples["urethral_rim_left"] - samples["urethral_opening"],
        "vaginal_rim_over_cap": samples["vaginal_rim_left"] - samples["vaginal_opening"],
        "fourchette_over_vaginal_cap": samples["fourchette"] - samples["vaginal_opening"],
        "anal_rim_over_cap": samples["anal_rim_left"] - samples["anal_recess"],
    }
    failures = [name for name, value in margins.items() if value < 0.0012]
    if failures:
        raise ValueError("delivery signed contrast gate failed: " + ",".join(failures))


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
        raise ValueError("delivery ventral ordering failed")
    return {
        "schema_version": 4,
        "method_id": METHOD_ID,
        "base_detail_method_id": BASE_DETAIL_METHOD_ID,
        "status": "UNPROMOTED_INACTIVE_DELIVERY_COMPONENT",
        "body_class": "adult_female",
        "scope": "complete_required_external_relationships_no_internal_tract_claim",
        "front_frame": asdict(front_frame),
        "rear_frame": asdict(rear_frame),
        "parameters": asdict(parameters),
        "relationships": list(relationships),
        "opening_representation": OPENING_REPRESENTATION,
        "feature_sample_displacements_m": samples,
        "rounded_transition_support": True,
        "full_legacy_v2_front_and_posterior_field_removal_required": True,
        "same_primary_surface_required": True,
        "source_anatomy_geometry_copy_allowed": False,
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
        "independent_visual_review_required": True,
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
