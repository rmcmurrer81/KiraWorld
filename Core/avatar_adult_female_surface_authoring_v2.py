"""Versioned structured continuous adult-female external-surface contract.

This identity-free v2 contract strengthens the visible external relationship
geometry that the v1 proof established only topologically.  It still authors
one closed primary skin surface: no copied anatomy, helper mesh, Boolean,
paint-only substitute, internal tract, runtime selection, render, or export is
part of this module.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import math
from pathlib import Path
from typing import Any, Mapping

from Core.avatar_adult_female_surface_authoring import (
    AuthoringParameters,
    LANDMARK_GROUP_PREFIX,
    POLICY_PATH,
    REQUIRED_RELATIONSHIPS,
    SurfaceFrame,
    gaussian,
    landmark_group_name,
)


METHOD_ID = "generic_continuous_adult_female_external_surface_v2"
OPENING_REPRESENTATION = "structured_recessed_capped_continuous_primary_surface"

# These fields serve both deterministic membership assignment and auditable
# feature placement.  The displacement evaluator below composes them by role
# instead of blindly summing every landmark Gaussian as v1 did.
FEATURE_COMPONENTS: Mapping[str, tuple[Mapping[str, float | str], ...]] = {
    "mons_pubis": (
        {"name": "mons", "u": 0.0, "v": 0.72, "su": 0.58, "sv": 0.22, "amplitude": 0.46},
    ),
    "paired_labia_majora": (
        {"name": "left", "u": 0.32, "v": 0.01, "su": 0.16, "sv": 0.48, "amplitude": 0.84},
        {"name": "right", "u": -0.32, "v": 0.01, "su": 0.16, "sv": 0.48, "amplitude": 0.84},
    ),
    "paired_labia_minora": (
        {"name": "left", "u": 0.12, "v": 0.03, "su": 0.055, "sv": 0.31, "amplitude": 0.60},
        {"name": "right", "u": -0.12, "v": 0.03, "su": 0.055, "sv": 0.31, "amplitude": 0.60},
    ),
    "clitoral_hood": (
        {"name": "hood", "u": 0.0, "v": 0.36, "su": 0.20, "sv": 0.095, "amplitude": 0.58},
    ),
    "clitoris": (
        {"name": "clitoris", "u": 0.0, "v": 0.28, "su": 0.060, "sv": 0.055, "amplitude": 0.46},
    ),
    "vestibule": (
        {"name": "vestibule", "u": 0.0, "v": 0.00, "su": 0.17, "sv": 0.28, "amplitude": -0.28},
    ),
    "urethral_opening_anterior_to_vaginal_opening": (
        {"name": "urethral_recess", "u": 0.0, "v": 0.14, "su": 0.040, "sv": 0.035, "amplitude": -0.90},
    ),
    "vaginal_opening": (
        {"name": "vaginal_recess", "u": 0.0, "v": -0.14, "su": 0.085, "sv": 0.125, "amplitude": -1.15},
    ),
    "posterior_commissure_fourchette": (
        {"name": "fourchette", "u": 0.0, "v": -0.40, "su": 0.20, "sv": 0.065, "amplitude": 0.50},
    ),
    "perineal_transition_to_anus_and_pelvic_floor": (
        {"name": "perineal_transition", "u": 0.0, "v": -0.53, "su": 0.36, "sv": 0.17, "amplitude": 0.12},
        {"name": "posterior_anal_recess", "u": 0.0, "v": -0.70, "su": 0.075, "sv": 0.060, "amplitude": -1.05},
    ),
}

FEATURE_SAMPLE_POINTS: Mapping[str, tuple[float, float]] = {
    "mons_pubis": (0.0, 0.72),
    "labia_majora_left": (0.32, 0.01),
    "labia_majora_right": (-0.32, 0.01),
    "labia_minora_left": (0.12, 0.03),
    "labia_minora_right": (-0.12, 0.03),
    "clitoral_hood": (0.0, 0.36),
    "clitoris": (0.0, 0.28),
    "urethral_opening": (0.0, 0.14),
    "vaginal_opening": (0.0, -0.14),
}

POSTERIOR_FEATURE_SAMPLE_POINTS: Mapping[str, tuple[float, float]] = {
    "fourchette": (0.0, 0.35),
    "perineal_transition": (0.0, -0.05),
    "anal_recess": (0.0, -0.36),
}

POSTERIOR_MEMBERSHIP_COMPONENTS: Mapping[str, Mapping[str, float | str]] = {
    "posterior_commissure_fourchette": {
        "name": "fourchette",
        "u": 0.0,
        "v": 0.35,
        "su": 0.22,
        "sv": 0.10,
    },
    "perineal_transition": {
        "name": "perineal_transition",
        "u": 0.0,
        "v": -0.05,
        "su": 0.38,
        "sv": 0.22,
    },
    "posterior_anal_recess": {
        "name": "posterior_anal_recess",
        "u": 0.0,
        "v": -0.36,
        "su": 0.30,
        "sv": 0.16,
    },
}


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
        raise ValueError("v2 relationship contract drifted from policy")
    if tuple(FEATURE_COMPONENTS) != normalized:
        raise ValueError("v2 feature implementation does not exactly cover policy")
    return normalized


def _smooth_axis_taper(value: float, power: int) -> float:
    magnitude = abs(float(value))
    if magnitude <= 0.80:
        return 1.0
    if magnitude >= 1.0:
        return 0.0
    t = (1.0 - magnitude) / 0.20
    smooth = t * t * (3.0 - 2.0 * t)
    return smooth ** max(1, int(power) - 1)


def boundary_taper(u: float, v: float, power: int) -> float:
    """Keep central/posterior anatomy full strength and taper only the seam."""

    radius = math.sqrt(float(u) * float(u) + float(v) * float(v))
    if radius >= 0.82:
        return 0.0
    if radius <= 0.72:
        radial = 1.0
    else:
        t = (0.82 - radius) / 0.10
        radial = (t * t * (3.0 - 2.0 * t)) ** max(2, int(power))
    return radial * _smooth_axis_taper(u, power) * _smooth_axis_taper(v, power)


def _g(u: float, v: float, *, cu: float, cv: float, su: float, sv: float) -> float:
    return math.exp(
        -0.5
        * (
            ((float(u) - cu) / su) ** 2
            + ((float(v) - cv) / sv) ** 2
        )
    )


def structured_field(u: float, v: float) -> float:
    """Return a bounded structured fold/rim/recess field in normalized space."""

    # Broad forms and the paired outer/inner folds.
    value = 0.46 * _g(u, v, cu=0.0, cv=0.72, su=0.58, sv=0.22)
    value += 0.84 * _g(u, v, cu=0.32, cv=0.01, su=0.16, sv=0.48)
    value += 0.84 * _g(u, v, cu=-0.32, cv=0.01, su=0.16, sv=0.48)
    value += 0.60 * _g(u, v, cu=0.12, cv=0.03, su=0.055, sv=0.31)
    value += 0.60 * _g(u, v, cu=-0.12, cv=0.03, su=0.055, sv=0.31)

    # A continuous central sulcus keeps the folds visually separated.  Broad
    # vestibular recession is evaluated independently so it cannot cancel the
    # paired ridges at their own sample points.
    value -= 0.42 * _g(u, v, cu=0.0, cv=0.02, su=0.075, sv=0.50)
    value -= 0.28 * _g(u, v, cu=0.0, cv=0.00, su=0.17, sv=0.28)

    # Anterior structures.
    value += 0.58 * _g(u, v, cu=0.0, cv=0.36, su=0.20, sv=0.095)
    value -= 0.18 * _g(u, v, cu=0.0, cv=0.315, su=0.085, sv=0.050)
    value += 0.46 * _g(u, v, cu=0.0, cv=0.28, su=0.060, sv=0.055)

    # Recessed capped openings with a raised continuous rim.  They remain part
    # of the same manifold surface and do not claim an internal tract.
    value += 0.18 * _g(u, v, cu=0.0, cv=0.14, su=0.090, sv=0.070)
    value -= 0.90 * _g(u, v, cu=0.0, cv=0.14, su=0.040, sv=0.035)
    value += 0.34 * _g(u, v, cu=0.0, cv=-0.14, su=0.18, sv=0.21)
    value -= 1.15 * _g(u, v, cu=0.0, cv=-0.14, su=0.085, sv=0.125)

    return max(-1.20, min(1.20, value))


def posterior_structured_field(u: float, v: float) -> float:
    """Fourchette/perineum/anal field for the curved posterior frame."""

    value = 0.58 * _g(u, v, cu=0.0, cv=0.35, su=0.22, sv=0.085)
    value += 0.14 * _g(u, v, cu=0.0, cv=-0.05, su=0.38, sv=0.20)
    value += 0.32 * _g(u, v, cu=0.0, cv=-0.36, su=0.25, sv=0.15)
    # The exact MakeHuman source has a sparse central posterior row.  Keep the
    # recessed cap broad enough that its nearest real vertex retains a clear
    # signed recession instead of barely touching the acceptance threshold.
    value -= 1.08 * _g(u, v, cu=0.0, cv=-0.36, su=0.16, sv=0.075)
    return max(-1.20, min(1.20, value))


def posterior_support_taper(u: float) -> float:
    """Limit curved-frame relief to the central posterior skin corridor."""

    magnitude = abs(float(u))
    if magnitude <= 0.30:
        return 1.0
    if magnitude >= 0.38:
        return 0.0
    t = (0.38 - magnitude) / 0.08
    return t * t * (3.0 - 2.0 * t)


def surface_displacement(
    u: float,
    v: float,
    *,
    relief_scale_m: float,
    taper_power: int,
) -> float:
    return (
        float(relief_scale_m)
        * boundary_taper(u, v, taper_power)
        * structured_field(u, v)
    )


def posterior_surface_displacement(
    u: float,
    v: float,
    *,
    relief_scale_m: float,
    taper_power: int,
) -> float:
    return (
        float(relief_scale_m)
        * posterior_support_taper(u)
        * boundary_taper(u, v, taper_power)
        * posterior_structured_field(u, v)
    )


def posterior_landmark_memberships(
    u: float,
    v: float,
    *,
    threshold: float,
) -> tuple[str, ...]:
    memberships: list[str] = []
    if gaussian(
        u,
        v,
        POSTERIOR_MEMBERSHIP_COMPONENTS["posterior_commissure_fourchette"],
    ) >= threshold:
        memberships.append("posterior_commissure_fourchette")
    perineal = gaussian(
        u,
        v,
        POSTERIOR_MEMBERSHIP_COMPONENTS["perineal_transition"],
    )
    anal = gaussian(
        u,
        v,
        POSTERIOR_MEMBERSHIP_COMPONENTS["posterior_anal_recess"],
    )
    if max(perineal, anal) >= threshold:
        memberships.append("perineal_transition_to_anus_and_pelvic_floor")
    if perineal >= threshold:
        memberships.append(
            "perineal_transition_to_anus_and_pelvic_floor__perineal_transition"
        )
    if anal >= threshold:
        memberships.append(
            "perineal_transition_to_anus_and_pelvic_floor__posterior_anal_recess"
        )
    return tuple(memberships)


def feature_influences(u: float, v: float) -> dict[str, float]:
    return {
        relationship: max(gaussian(u, v, component) for component in components)
        for relationship, components in FEATURE_COMPONENTS.items()
    }


def landmark_memberships(
    u: float,
    v: float,
    *,
    threshold: float,
) -> tuple[str, ...]:
    memberships: list[str] = []
    for relationship, components in FEATURE_COMPONENTS.items():
        values = [gaussian(u, v, component) for component in components]
        if max(values) >= threshold:
            memberships.append(relationship)
        if relationship in {"paired_labia_majora", "paired_labia_minora"}:
            for component, influence in zip(components, values):
                if influence >= threshold:
                    memberships.append(f"{relationship}__{component['name']}")
        if relationship == "perineal_transition_to_anus_and_pelvic_floor":
            for component, influence in zip(components, values):
                if influence >= threshold:
                    memberships.append(f"{relationship}__{component['name']}")
    return tuple(memberships)


def feature_sample_displacements(
    relief_scale_m: float,
    taper_power: int,
) -> dict[str, float]:
    values = {
        name: surface_displacement(
            point[0],
            point[1],
            relief_scale_m=relief_scale_m,
            taper_power=taper_power,
        )
        for name, point in FEATURE_SAMPLE_POINTS.items()
    }
    values.update(
        {
            name: posterior_surface_displacement(
                point[0],
                point[1],
                relief_scale_m=relief_scale_m,
                taper_power=taper_power,
            )
            for name, point in POSTERIOR_FEATURE_SAMPLE_POINTS.items()
        }
    )
    return values


def build_authoring_contract(
    project_root: Path,
    frame: SurfaceFrame,
    parameters: AuthoringParameters,
) -> dict[str, Any]:
    relationships = load_required_relationships(project_root)
    samples = feature_sample_displacements(
        parameters.relief_scale_m,
        parameters.boundary_taper_power,
    )
    if not (
        FEATURE_SAMPLE_POINTS["urethral_opening"][1]
        > FEATURE_SAMPLE_POINTS["vaginal_opening"][1]
        and POSTERIOR_FEATURE_SAMPLE_POINTS["perineal_transition"][1]
        > POSTERIOR_FEATURE_SAMPLE_POINTS["anal_recess"][1]
    ):
        raise ValueError("required anterior/posterior relationship is invalid")
    positive = (
        "mons_pubis",
        "labia_majora_left",
        "labia_majora_right",
        "labia_minora_left",
        "labia_minora_right",
        "clitoral_hood",
        "clitoris",
        "fourchette",
    )
    recessed = ("urethral_opening", "vaginal_opening", "anal_recess")
    if any(samples[name] <= 0.0 for name in positive):
        raise ValueError("v2 positive relationship sample lost relief")
    if any(samples[name] >= 0.0 for name in recessed):
        raise ValueError("v2 recessed relationship sample lost depth")
    return {
        "schema_version": 2,
        "method_id": METHOD_ID,
        "status": "UNPROMOTED_INACTIVE_AUTHORING_METHOD",
        "body_class": "adult_female",
        "scope": "complete_required_external_relationships_no_internal_tract_claim",
        "coordinate_convention": (
            "object_local; longitudinal positive toward mons/anterior; "
            "outward positive outside primary skin"
        ),
        "frame": asdict(frame),
        "parameters": asdict(parameters),
        "relationships": list(relationships),
        "relationship_geometry_mode": {
            relationship: "structured_continuous_primary_surface_fold_rim_or_recess"
            for relationship in relationships
        },
        "opening_representation": OPENING_REPRESENTATION,
        "feature_sample_displacements_m": samples,
        "feature_samples_are_contract_preflight_not_visual_acceptance": True,
        "source_anatomy_geometry_copy_allowed": False,
        "wrong_sex_helper_allowed": False,
        "separate_anatomy_mesh_allowed": False,
        "boolean_anatomy_union_allowed": False,
        "painted_only_relationship_allowed": False,
        "source_primary_surface_required": True,
        "source_component_count_required": 1,
        "source_boundary_edges_required": 0,
        "source_nonmanifold_edges_required": 0,
        "result_component_count_required": 1,
        "result_boundary_edges_required": 0,
        "result_nonmanifold_edges_required": 0,
        "authored_region_nonadjacent_self_intersection_pairs_required": 0,
        "new_global_nonadjacent_self_intersection_pairs_allowed": False,
        "qualification_global_nonadjacent_self_intersection_pairs_required": 0,
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
        "independent_topology_review_required": True,
        "independent_relationship_review_required": True,
        "independent_visual_prominence_review_required": True,
        "qualified_for_adult_foundation": False,
        "runtime_activation_allowed": False,
        "render_performed": False,
        "export_performed": False,
    }


__all__ = [
    "FEATURE_COMPONENTS",
    "FEATURE_SAMPLE_POINTS",
    "POSTERIOR_FEATURE_SAMPLE_POINTS",
    "POSTERIOR_MEMBERSHIP_COMPONENTS",
    "METHOD_ID",
    "OPENING_REPRESENTATION",
    "boundary_taper",
    "build_authoring_contract",
    "feature_influences",
    "feature_sample_displacements",
    "landmark_memberships",
    "load_required_relationships",
    "posterior_structured_field",
    "posterior_landmark_memberships",
    "posterior_support_taper",
    "posterior_surface_displacement",
    "structured_field",
    "surface_displacement",
]
