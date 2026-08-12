"""Final bounded front-chart reconstruction contract for adult surface v5.

R17's v4 field removed the analytic v3 displacement, but visual review proved
that thousands of locally subdivided vertices still retained the planar shape
of older delivery charts.  V5 is deliberately a component-only repair: the
13,380 index-stable MakeHuman vertices are the neutral anchors, only the one
connected subdivided front-chart component is harmonically reconstructed, and
a very low-amplitude relationship field is added on that same closed skin.

This pure module contains no Blender operations, identity coordinates, build,
render, save, export, assignment, activation, publication, hair, clothing, or
internal-tract claim.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Any, Mapping

from Core.avatar_adult_female_surface_authoring import (
    REQUIRED_RELATIONSHIPS,
    SurfaceFrame,
)
from Core.avatar_adult_female_surface_delivery_v4 import (
    FRONT_FEATURE_SAMPLE_POINTS,
    front_landmark_memberships,
    front_structured_field,
)


METHOD_ID = "generic_continuous_adult_female_external_surface_delivery_v5"
BASE_DETAIL_METHOD_ID = "generic_continuous_adult_female_external_surface_delivery_v4"
OPENING_REPRESENTATION = (
    "very_subtle_external_relationship_relief_on_harmonically_reconstructed_"
    "closed_primary_surface"
)


@dataclass(frozen=True)
class HarmonicSurfaceParameters:
    original_anchor_vertex_count: int = 13380
    minimum_front_component_vertices: int = 5000
    maximum_front_component_vertices: int = 5600
    minimum_front_anchor_neighbors: int = 120
    maximum_front_anchor_neighbors: int = 160
    harmonic_minimum_iterations: int = 20
    harmonic_maximum_iterations: int = 800
    harmonic_relaxation: float = 1.0
    harmonic_tolerance_m: float = 2.0e-6
    anchor_full_restore_radius: float = 0.68
    anchor_outer_restore_radius: float = 1.0
    anchor_restore_radius_u: float = 1.52
    anchor_restore_radius_v: float = 1.42
    anchor_restore_center_v: float = -0.02
    front_prominence_scale_m: float = 0.00135
    deterministic_asymmetry_fraction: float = 0.025
    minimum_front_normal_alignment: float = 0.06
    alignment_fade_width: float = 0.30
    maximum_total_correction_m: float = 0.09
    minimum_feature_vertices: int = 8
    maximum_skin_influences: int = 4
    degeneracy_area_m2: float = 1.0e-12


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
) -> HarmonicSurfaceParameters:
    raw = dict(value or {})
    allowed = set(HarmonicSurfaceParameters.__dataclass_fields__)
    unexpected = sorted(set(raw).difference(allowed))
    if unexpected:
        raise ValueError(f"unknown delivery-v5 parameter(s): {', '.join(unexpected)}")
    defaults = HarmonicSurfaceParameters()
    integer_names = {
        "original_anchor_vertex_count",
        "minimum_front_component_vertices",
        "maximum_front_component_vertices",
        "minimum_front_anchor_neighbors",
        "maximum_front_anchor_neighbors",
        "harmonic_minimum_iterations",
        "harmonic_maximum_iterations",
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
    result = HarmonicSurfaceParameters(**parsed)  # type: ignore[arg-type]
    if result.original_anchor_vertex_count != 13380:
        raise ValueError("original_anchor_vertex_count must remain 13380")
    if not 4000 <= result.minimum_front_component_vertices <= 5500:
        raise ValueError("minimum_front_component_vertices outside bounded range")
    if not result.minimum_front_component_vertices < result.maximum_front_component_vertices <= 8000:
        raise ValueError("maximum_front_component_vertices outside bounded range")
    if not 80 <= result.minimum_front_anchor_neighbors <= 150:
        raise ValueError("minimum_front_anchor_neighbors outside bounded range")
    if not result.minimum_front_anchor_neighbors < result.maximum_front_anchor_neighbors <= 220:
        raise ValueError("maximum_front_anchor_neighbors outside bounded range")
    if not 10 <= result.harmonic_minimum_iterations <= 100:
        raise ValueError("harmonic_minimum_iterations outside bounded range")
    if not result.harmonic_minimum_iterations <= result.harmonic_maximum_iterations <= 2000:
        raise ValueError("harmonic_maximum_iterations outside bounded range")
    if not 0.70 <= result.harmonic_relaxation <= 1.0:
        raise ValueError("harmonic_relaxation outside [0.70, 1.0]")
    if not 1.0e-9 <= result.harmonic_tolerance_m <= 1.0e-5:
        raise ValueError("harmonic_tolerance_m outside bounded range")
    if not 0.45 <= result.anchor_full_restore_radius <= 0.80:
        raise ValueError("anchor_full_restore_radius outside bounded range")
    if not result.anchor_full_restore_radius < result.anchor_outer_restore_radius <= 1.20:
        raise ValueError("anchor_outer_restore_radius outside bounded range")
    if not 1.15 <= result.anchor_restore_radius_u <= 1.80:
        raise ValueError("anchor_restore_radius_u outside bounded range")
    if not 1.10 <= result.anchor_restore_radius_v <= 1.80:
        raise ValueError("anchor_restore_radius_v outside bounded range")
    if not -0.25 <= result.anchor_restore_center_v <= 0.25:
        raise ValueError("anchor_restore_center_v outside bounded range")
    if not 0.0008 <= result.front_prominence_scale_m <= 0.0018:
        raise ValueError("front_prominence_scale_m outside [0.0008, 0.0018]")
    if not 0.0 <= result.deterministic_asymmetry_fraction <= 0.06:
        raise ValueError("deterministic_asymmetry_fraction outside [0, 0.06]")
    if not 0.03 <= result.minimum_front_normal_alignment <= 0.25:
        raise ValueError("minimum_front_normal_alignment outside bounded range")
    if not 0.15 <= result.alignment_fade_width <= 0.45:
        raise ValueError("alignment_fade_width outside bounded range")
    if not 0.03 <= result.maximum_total_correction_m <= 0.10:
        raise ValueError("maximum_total_correction_m outside bounded range")
    if not 4 <= result.minimum_feature_vertices <= 64:
        raise ValueError("minimum_feature_vertices outside [4, 64]")
    if not 1 <= result.maximum_skin_influences <= 8:
        raise ValueError("maximum_skin_influences outside [1, 8]")
    if not 1.0e-16 <= result.degeneracy_area_m2 <= 1.0e-8:
        raise ValueError("degeneracy_area_m2 outside bounded range")
    return result


def smootherstep(value: float) -> float:
    """Quintic interpolation with zero first and second endpoint derivatives."""

    t = max(0.0, min(1.0, float(value)))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def anchor_restore_weight(
    u: float,
    v: float,
    parameters: HarmonicSurfaceParameters,
) -> float:
    radius = math.sqrt(
        (float(u) / parameters.anchor_restore_radius_u) ** 2
        + (
            (float(v) - parameters.anchor_restore_center_v)
            / parameters.anchor_restore_radius_v
        )
        ** 2
    )
    if radius <= parameters.anchor_full_restore_radius:
        return 1.0
    if radius >= parameters.anchor_outer_restore_radius:
        return 0.0
    normalized = (
        parameters.anchor_outer_restore_radius - radius
    ) / (
        parameters.anchor_outer_restore_radius
        - parameters.anchor_full_restore_radius
    )
    return smootherstep(normalized)


def relationship_support(u: float, v: float) -> float:
    """Compact C2 ellipse for the subtle post-reconstruction relationship field."""

    radius = math.sqrt((float(u) / 0.78) ** 2 + ((float(v) - 0.25) / 0.88) ** 2)
    if radius >= 1.0:
        return 0.0
    if radius <= 0.22:
        return 1.0
    return smootherstep((1.0 - radius) / 0.78)


def alignment_blend(
    alignment: float,
    *,
    minimum_alignment: float,
    fade_width: float,
) -> float:
    return smootherstep(
        (float(alignment) - float(minimum_alignment)) / float(fade_width)
    )


def front_surface_displacement(
    u: float,
    v: float,
    *,
    prominence_scale_m: float,
    asymmetry_fraction: float = 0.025,
) -> float:
    return (
        float(prominence_scale_m)
        * relationship_support(u, v)
        * front_structured_field(
            u,
            v,
            asymmetry_fraction=float(asymmetry_fraction),
        )
    )


def feature_sample_displacements(
    parameters: HarmonicSurfaceParameters,
) -> dict[str, float]:
    return {
        name: front_surface_displacement(
            point[0],
            point[1],
            prominence_scale_m=parameters.front_prominence_scale_m,
            asymmetry_fraction=parameters.deterministic_asymmetry_fraction,
        )
        for name, point in FRONT_FEATURE_SAMPLE_POINTS.items()
    }


def build_authoring_contract(
    project_root: Path,
    front_frame: SurfaceFrame,
    parameters: HarmonicSurfaceParameters,
) -> dict[str, Any]:
    root = Path(project_root).resolve(strict=True)
    samples = feature_sample_displacements(parameters)
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
    )
    recessed = ("vestibule", "urethral_opening", "vaginal_opening")
    if any(samples[name] <= 0.0 for name in positive):
        raise ValueError("delivery-v5 positive relationship sample lost relief")
    if any(samples[name] >= 0.0 for name in recessed):
        raise ValueError("delivery-v5 recessed relationship sample lost depth")
    if max(abs(value) for value in samples.values()) > 0.00045:
        raise ValueError("delivery-v5 relationship field exceeds subtle bound")
    return {
        "schema_version": 1,
        "method_id": METHOD_ID,
        "base_detail_method_id": BASE_DETAIL_METHOD_ID,
        "status": "FINAL_BOUNDED_FRONT_CHART_REPAIR_INACTIVE",
        "body_class": "adult_female",
        "project_root": str(root),
        "scope": (
            "restore_front_chart_from_index_stable_neutral_anchors_then_add_"
            "subtle_complete_front_relationships_retain_v4_rear_relationships"
        ),
        "front_frame": {
            "origin": list(front_frame.origin),
            "lateral_axis": list(front_frame.lateral_axis),
            "longitudinal_axis": list(front_frame.longitudinal_axis),
            "outward_axis": list(front_frame.outward_axis),
            "half_width_m": front_frame.half_width_m,
            "half_length_m": front_frame.half_length_m,
            "max_surface_offset_m": front_frame.max_surface_offset_m,
        },
        "parameters": asdict(parameters),
        "required_relationships": list(REQUIRED_RELATIONSHIPS),
        "front_feature_sample_displacements_m": samples,
        "rear_v4_relationships_preserved_unchanged": True,
        "opening_representation": OPENING_REPRESENTATION,
        "neutral_anchor_source": "official_makehuman_index_stable_profiled_source",
        "harmonic_reconstruction": True,
        "anchor_boundary": "compact_quintic_c2_restore_weight",
        "topology_change_allowed": False,
        "same_primary_surface_required": True,
        "source_vertex_indices_must_be_preserved": True,
        "skin_weights_must_be_preserved_exactly": True,
        "landmark_memberships_must_be_preserved_exactly": True,
        "source_anatomy_geometry_copy_allowed": False,
        "separate_anatomy_mesh_allowed": False,
        "boolean_anatomy_union_allowed": False,
        "internal_tract_claim_allowed": False,
        "new_global_nonadjacent_self_intersection_pairs_allowed": False,
        "runtime_activation_allowed": False,
        "candidate_build_allowed": False,
        "render_performed": False,
        "export_performed": False,
        "owner_visual_review_required": True,
        "visual_attempt_limit": 2,
        "v6_allowed_after_this_attempt": False,
        "qualified": False,
    }


__all__ = [
    "BASE_DETAIL_METHOD_ID",
    "FRONT_FEATURE_SAMPLE_POINTS",
    "HarmonicSurfaceParameters",
    "METHOD_ID",
    "OPENING_REPRESENTATION",
    "alignment_blend",
    "anchor_restore_weight",
    "build_authoring_contract",
    "feature_sample_displacements",
    "front_landmark_memberships",
    "front_surface_displacement",
    "parameters_from_mapping",
    "relationship_support",
    "smootherstep",
]
