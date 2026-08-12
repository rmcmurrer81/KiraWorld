"""Organic, topology-preserving adult-female surface repair contract v4.

The R16 checkpoint proved that the required relationships can live on one
closed, weighted primary skin, but its v3 chart read as a raised rectangular
plate with schematic ridges.  This module defines a deliberately lower-amplitude
replacement field with broad C2 radial support, softly converging folds and
closed shallow recesses.  The method is generic: adult-only references inform
transition softness and relative relief only; no source identity is copied.

The companion Blender adapter replaces coordinates on the existing v3 mesh.
It does not subdivide, create anatomy objects, use Booleans, save, render,
export, assign, activate, publish, or make an internal-tract claim.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
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
    METHOD_ID as BASE_DETAIL_METHOD_ID,
    load_required_relationships,
)


METHOD_ID = "generic_continuous_adult_female_external_surface_delivery_v4"
OPENING_REPRESENTATION = (
    "subtle_annular_relief_and_shallow_recessed_cap_on_one_closed_primary_surface"
)
COLLISION_REPAIR_MAX_PASSES = 4
COLLISION_REPAIR_MAX_VERTICES = 192
COLLISION_REPAIR_MAX_FRACTION_OF_CHANGED_VERTICES = 0.12
COLLISION_REPAIR_RETENTION_BY_RING = (0.0, 0.45, 0.75)


@dataclass(frozen=True)
class OrganicSurfaceParameters:
    """Bounded values for the low-relief replacement and normal-only fairing."""

    front_prominence_scale_m: float = 0.00235
    rear_prominence_scale_m: float = 0.00190
    deterministic_asymmetry_fraction: float = 0.025
    minimum_front_normal_alignment: float = 0.06
    minimum_rear_normal_alignment: float = 0.06
    alignment_fade_width: float = 0.26
    fairing_iterations: int = 2
    fairing_strength: float = 0.18
    fairing_max_step_m: float = 0.00045
    maximum_total_correction_m: float = 0.008
    minimum_feature_vertices: int = 8
    maximum_skin_influences: int = 4
    degeneracy_area_m2: float = 1.0e-12


FRONT_FEATURE_SAMPLE_POINTS: Mapping[str, tuple[float, float]] = {
    "mons_pubis": (0.0, 0.70),
    "labia_majora_left": (0.23, 0.18),
    "labia_majora_right": (-0.23, 0.18),
    "labia_minora_left": (0.075, 0.18),
    "labia_minora_right": (-0.075, 0.18),
    "clitoral_hood": (0.0, 0.45),
    "clitoris": (0.0, 0.385),
    "vestibule": (0.0, 0.19),
    "urethral_opening": (0.0, 0.275),
    "urethral_rim_left": (0.050, 0.275),
    "vaginal_opening": (0.0, 0.060),
    "vaginal_rim_left": (0.092, 0.060),
    "fourchette": (0.0, -0.055),
}

REAR_FEATURE_SAMPLE_POINTS: Mapping[str, tuple[float, float]] = {
    "perineal_transition": (0.0, -0.17),
    "anal_recess": (0.0, 0.14),
    "anal_rim_left": (0.125, 0.14),
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


def parameters_from_mapping(
    value: Mapping[str, Any] | None,
) -> OrganicSurfaceParameters:
    raw = dict(value or {})
    allowed = set(OrganicSurfaceParameters.__dataclass_fields__)
    unexpected = sorted(set(raw).difference(allowed))
    if unexpected:
        raise ValueError(f"unknown delivery-v4 parameter(s): {', '.join(unexpected)}")
    defaults = OrganicSurfaceParameters()
    integer_names = {
        "fairing_iterations",
        "minimum_feature_vertices",
        "maximum_skin_influences",
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
    result = OrganicSurfaceParameters(**parsed)  # type: ignore[arg-type]
    if not 0.0014 <= result.front_prominence_scale_m <= 0.0032:
        raise ValueError("front_prominence_scale_m outside [0.0014, 0.0032]")
    if not 0.0010 <= result.rear_prominence_scale_m <= 0.0028:
        raise ValueError("rear_prominence_scale_m outside [0.0010, 0.0028]")
    if not 0.0 <= result.deterministic_asymmetry_fraction <= 0.06:
        raise ValueError("deterministic_asymmetry_fraction outside [0, 0.06]")
    if not 0.03 <= result.minimum_front_normal_alignment <= 0.30:
        raise ValueError("minimum_front_normal_alignment outside [0.03, 0.30]")
    if not 0.03 <= result.minimum_rear_normal_alignment <= 0.30:
        raise ValueError("minimum_rear_normal_alignment outside [0.03, 0.30]")
    if not 0.10 <= result.alignment_fade_width <= 0.45:
        raise ValueError("alignment_fade_width outside [0.10, 0.45]")
    if not 0 <= result.fairing_iterations <= 4:
        raise ValueError("fairing_iterations outside [0, 4]")
    if not 0.0 <= result.fairing_strength <= 0.35:
        raise ValueError("fairing_strength outside [0, 0.35]")
    if not 0.0001 <= result.fairing_max_step_m <= 0.0010:
        raise ValueError("fairing_max_step_m outside [0.0001, 0.0010]")
    if not 0.004 <= result.maximum_total_correction_m <= 0.012:
        raise ValueError("maximum_total_correction_m outside [0.004, 0.012]")
    if not 4 <= result.minimum_feature_vertices <= 64:
        raise ValueError("minimum_feature_vertices outside [4, 64]")
    if not 1 <= result.maximum_skin_influences <= 8:
        raise ValueError("maximum_skin_influences outside [1, 8]")
    if not 1.0e-16 <= result.degeneracy_area_m2 <= 1.0e-8:
        raise ValueError("degeneracy_area_m2 outside bounded range")
    return result


def _g(u: float, v: float, *, cu: float, cv: float, su: float, sv: float) -> float:
    return math.exp(
        -0.5
        * (
            ((float(u) - cu) / su) ** 2
            + ((float(v) - cv) / sv) ** 2
        )
    )


def _smootherstep(value: float) -> float:
    """Quintic smootherstep: zero first/second derivatives at both ends."""

    t = max(0.0, min(1.0, float(value)))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _elliptic_support(
    u: float,
    v: float,
    *,
    center_v: float,
    radius_u: float,
    radius_v: float,
    full_support_radius: float,
) -> float:
    radius = math.sqrt(
        (float(u) / float(radius_u)) ** 2
        + ((float(v) - float(center_v)) / float(radius_v)) ** 2
    )
    if radius >= 1.0:
        return 0.0
    if radius <= float(full_support_radius):
        return 1.0
    normalized = (1.0 - radius) / (1.0 - float(full_support_radius))
    return _smootherstep(normalized)


def front_support_taper(u: float, v: float) -> float:
    """A broad ellipse, not the rejected rectangle/superellipse plate."""

    return _elliptic_support(
        u,
        v,
        center_v=0.27,
        radius_u=0.82,
        radius_v=0.86,
        full_support_radius=0.20,
    )


def rear_support_taper(u: float, v: float) -> float:
    return _elliptic_support(
        u,
        v,
        center_v=0.04,
        radius_u=0.62,
        radius_v=0.60,
        full_support_radius=0.18,
    )


def alignment_blend(
    alignment: float,
    *,
    minimum_alignment: float,
    fade_width: float,
) -> float:
    """Smoothly suppress coordinate edits on a returning/side-facing sheet."""

    return _smootherstep(
        (float(alignment) - float(minimum_alignment)) / float(fade_width)
    )


def _organic_fold(
    u: float,
    v: float,
    *,
    side: float,
    end_center: float,
    middle_spread: float,
    center_v: float,
    curve_sv: float,
    width_u: float,
    length_sv: float,
) -> float:
    """One broad fold whose centerline converges smoothly at both ends."""

    center = float(side) * (
        float(end_center)
        + float(middle_spread)
        * math.exp(-0.5 * ((float(v) - center_v) / curve_sv) ** 2)
    )
    across = math.exp(-0.5 * ((float(u) - center) / width_u) ** 2)
    along = math.exp(-0.5 * ((float(v) - center_v) / length_sv) ** 4)
    return across * along


def front_structured_field(
    u: float,
    v: float,
    *,
    asymmetry_fraction: float = 0.025,
) -> float:
    """Low-relief, softly nested relationships with no parallel-bar motif."""

    asymmetry = max(0.0, min(0.06, float(asymmetry_fraction)))
    value = 0.075 * _g(u, v, cu=0.0, cv=0.68, su=0.44, sv=0.19)

    for side in (-1.0, 1.0):
        side_gain = 1.0 + side * asymmetry
        value += side_gain * 0.29 * _organic_fold(
            u,
            v,
            side=side,
            end_center=0.075,
            middle_spread=0.155,
            center_v=0.18,
            curve_sv=0.27,
            width_u=0.105,
            length_sv=0.37,
        )
        value -= side_gain * 0.040 * _organic_fold(
            u,
            v,
            side=side,
            end_center=0.055,
            middle_spread=0.092,
            center_v=0.18,
            curve_sv=0.24,
            width_u=0.050,
            length_sv=0.31,
        )
        value += side_gain * 0.145 * _organic_fold(
            u,
            v,
            side=side,
            end_center=0.015,
            middle_spread=0.061,
            center_v=0.18,
            curve_sv=0.17,
            width_u=0.038,
            length_sv=0.235,
        )

    # Broad negative space separates the folds without producing a long slot.
    value -= 0.160 * _g(u, v, cu=0.0, cv=0.18, su=0.145, sv=0.225)
    value -= 0.040 * _g(u, v, cu=0.0, cv=0.18, su=0.045, sv=0.19)

    # The superior sequence remains shallow and vertically blended.
    value += 0.105 * _g(u, v, cu=0.0, cv=0.45, su=0.145, sv=0.075)
    value -= 0.040 * _g(u, v, cu=0.0, cv=0.418, su=0.075, sv=0.040)
    value += 0.065 * _g(u, v, cu=0.0, cv=0.385, su=0.045, sv=0.040)

    # Closed, very shallow caps with soft rims.  These encode surface
    # relationships; they do not form holes or internal geometry.
    value += 0.075 * _g(u, v, cu=0.0, cv=0.275, su=0.070, sv=0.060)
    value -= 0.155 * _g(u, v, cu=0.0, cv=0.275, su=0.026, sv=0.026)
    value += 0.135 * _g(u, v, cu=0.0, cv=0.060, su=0.115, sv=0.095)
    value -= 0.285 * _g(u, v, cu=0.0, cv=0.060, su=0.050, sv=0.062)
    value += 0.105 * _g(u, v, cu=0.0, cv=-0.055, su=0.145, sv=0.055)
    return max(-0.48, min(0.48, value))


def rear_structured_field(u: float, v: float) -> float:
    value = 0.060 * _g(u, v, cu=0.0, cv=-0.17, su=0.31, sv=0.17)
    value += 0.145 * _g(u, v, cu=0.0, cv=0.14, su=0.18, sv=0.15)
    value -= 0.315 * _g(u, v, cu=0.0, cv=0.14, su=0.055, sv=0.060)
    return max(-0.42, min(0.42, value))


def front_surface_displacement(
    u: float,
    v: float,
    *,
    prominence_scale_m: float,
    asymmetry_fraction: float = 0.025,
) -> float:
    return (
        float(prominence_scale_m)
        * front_support_taper(u, v)
        * front_structured_field(u, v, asymmetry_fraction=asymmetry_fraction)
    )


def rear_surface_displacement(
    u: float,
    v: float,
    *,
    prominence_scale_m: float,
) -> float:
    return (
        float(prominence_scale_m)
        * rear_support_taper(u, v)
        * rear_structured_field(u, v)
    )


def front_landmark_memberships(
    u: float,
    v: float,
    *,
    threshold: float = 0.16,
) -> tuple[str, ...]:
    rows: list[str] = []

    def member(cu: float, cv: float, su: float, sv: float) -> bool:
        return _g(u, v, cu=cu, cv=cv, su=su, sv=sv) >= float(threshold)

    if member(0.0, 0.70, 0.45, 0.17):
        rows.append("mons_pubis")
    majora_left = member(0.23, 0.18, 0.14, 0.33)
    majora_right = member(-0.23, 0.18, 0.14, 0.33)
    if majora_left or majora_right:
        rows.append("paired_labia_majora")
    if majora_left:
        rows.append("paired_labia_majora__left")
    if majora_right:
        rows.append("paired_labia_majora__right")
    minora_left = member(0.075, 0.18, 0.060, 0.225)
    minora_right = member(-0.075, 0.18, 0.060, 0.225)
    if minora_left or minora_right:
        rows.append("paired_labia_minora")
    if minora_left:
        rows.append("paired_labia_minora__left")
    if minora_right:
        rows.append("paired_labia_minora__right")
    if member(0.0, 0.45, 0.16, 0.09):
        rows.append("clitoral_hood")
    if member(0.0, 0.385, 0.065, 0.060):
        rows.append("clitoris")
    if member(0.0, 0.19, 0.17, 0.22):
        rows.append("vestibule")
    if member(0.0, 0.275, 0.072, 0.065):
        rows.append("urethral_opening_anterior_to_vaginal_opening")
    if member(0.0, 0.060, 0.125, 0.110):
        rows.append("vaginal_opening")
    if member(0.0, -0.055, 0.155, 0.070):
        rows.append("posterior_commissure_fourchette")
    return tuple(rows)


def rear_landmark_memberships(
    u: float,
    v: float,
    *,
    threshold: float = 0.16,
) -> tuple[str, ...]:
    transition = _g(u, v, cu=0.0, cv=-0.17, su=0.32, sv=0.18)
    anal = _g(u, v, cu=0.0, cv=0.14, su=0.16, sv=0.13)
    rows: list[str] = []
    if max(transition, anal) >= threshold:
        rows.append("perineal_transition_to_anus_and_pelvic_floor")
    if transition >= threshold:
        rows.append(
            "perineal_transition_to_anus_and_pelvic_floor__perineal_transition"
        )
    if anal >= threshold:
        rows.append(
            "perineal_transition_to_anus_and_pelvic_floor__posterior_anal_recess"
        )
    return tuple(rows)


def feature_sample_displacements(
    parameters: OrganicSurfaceParameters,
) -> dict[str, float]:
    values = {
        name: front_surface_displacement(
            point[0],
            point[1],
            prominence_scale_m=parameters.front_prominence_scale_m,
            asymmetry_fraction=parameters.deterministic_asymmetry_fraction,
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


def _assert_signed_relationships(samples: Mapping[str, float]) -> None:
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
        raise ValueError("delivery-v4 positive relationship sample lost relief")
    if any(samples[name] >= 0.0 for name in recessed):
        raise ValueError("delivery-v4 recessed relationship sample lost depth")
    contrast_pairs = (
        ("labia_majora_left", "vestibule"),
        ("labia_majora_right", "vestibule"),
        ("labia_minora_left", "vestibule"),
        ("labia_minora_right", "vestibule"),
        ("urethral_rim_left", "urethral_opening"),
        ("vaginal_rim_left", "vaginal_opening"),
        ("fourchette", "vaginal_opening"),
        ("anal_rim_left", "anal_recess"),
    )
    if any(samples[high] - samples[low] < 0.00020 for high, low in contrast_pairs):
        raise ValueError("delivery-v4 subtle signed contrast gate failed")
    if max(abs(value) for value in samples.values()) > 0.00125:
        raise ValueError("delivery-v4 sample exceeds low-relief visual bound")


def build_authoring_contract(
    project_root: Path,
    front_frame: SurfaceFrame,
    rear_frame: SurfaceFrame,
    parameters: OrganicSurfaceParameters,
) -> dict[str, Any]:
    relationships = load_required_relationships(project_root)
    samples = feature_sample_displacements(parameters)
    _assert_signed_relationships(samples)
    if not (
        FRONT_FEATURE_SAMPLE_POINTS["clitoris"][1]
        > FRONT_FEATURE_SAMPLE_POINTS["urethral_opening"][1]
        > FRONT_FEATURE_SAMPLE_POINTS["vaginal_opening"][1]
        > FRONT_FEATURE_SAMPLE_POINTS["fourchette"][1]
    ):
        raise ValueError("delivery-v4 ventral ordering failed")
    return {
        "schema_version": 6,
        "method_id": METHOD_ID,
        "base_detail_method_id": BASE_DETAIL_METHOD_ID,
        "status": "UNPROMOTED_INACTIVE_TARGETED_VISUAL_REPAIR",
        "body_class": "adult_female",
        "scope": "complete_required_external_relationships_no_internal_tract_claim",
        "front_frame": asdict(front_frame),
        "rear_frame": asdict(rear_frame),
        "parameters": asdict(parameters),
        "relationships": list(relationships),
        "opening_representation": OPENING_REPRESENTATION,
        "feature_sample_displacements_m": samples,
        "visual_repair": {
            "rejected_v3_rectangular_plate_replaced": True,
            "rejected_v3_schematic_parallel_ridges_replaced": True,
            "support": "broad_compact_elliptic_c2_smootherstep",
            "relief": "subtle_converging_low_amplitude_continuous_surface",
            "deterministic_non_identity_asymmetry": True,
            "normal_axis_laplacian_fairing_allowed": True,
        },
        "topology_change_allowed": False,
        "source_vertex_indices_must_be_preserved": True,
        "source_skin_weights_must_be_preserved_exactly": True,
        "source_landmark_memberships_must_be_preserved_exactly": True,
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
        "bounded_new_intersection_repair": {
            "mode": "local_source_coordinate_retention_backtracking",
            "maximum_passes": COLLISION_REPAIR_MAX_PASSES,
            "maximum_vertices": COLLISION_REPAIR_MAX_VERTICES,
            "maximum_fraction_of_changed_vertices": (
                COLLISION_REPAIR_MAX_FRACTION_OF_CHANGED_VERTICES
            ),
            "retention_by_offending_face_ring": list(
                COLLISION_REPAIR_RETENTION_BY_RING
            ),
            "source_inherited_pairs_are_not_repaired_or_hidden": True,
            "final_new_pair_count_required": 0,
        },
        "feature_samples_are_preflight_not_visual_acceptance": True,
        "owner_visual_review_required": True,
        "qualified": False,
        "runtime_activation_allowed": False,
        "render_performed": False,
        "export_performed": False,
        "landmark_group_prefix": LANDMARK_GROUP_PREFIX,
        "landmark_groups": {
            relationship: landmark_group_name(relationship)
            for relationship in relationships
        },
    }


__all__ = [
    "BASE_DETAIL_METHOD_ID",
    "COLLISION_REPAIR_MAX_FRACTION_OF_CHANGED_VERTICES",
    "COLLISION_REPAIR_MAX_PASSES",
    "COLLISION_REPAIR_MAX_VERTICES",
    "COLLISION_REPAIR_RETENTION_BY_RING",
    "FRONT_FEATURE_SAMPLE_POINTS",
    "METHOD_ID",
    "OPENING_REPRESENTATION",
    "OrganicSurfaceParameters",
    "REAR_FEATURE_SAMPLE_POINTS",
    "alignment_blend",
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
