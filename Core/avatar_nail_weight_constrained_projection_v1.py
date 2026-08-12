"""Pure contracts for weight-constrained avatar nail surface selection.

A global first-hit ray may encounter a neighboring digit before the declared
digit.  This module selects from every bounded ray hit using the body's
transferred digit weights and a connected-region identifier.  It never changes
the nail inventory or substitutes the bone associated with the first surface.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "kira.avatar.nail_weight_constrained_projection.v1"
MINIMUM_EXPECTED_FAMILY_WEIGHT = 0.99
MAXIMUM_FOREIGN_DIGIT_FAMILY_WEIGHT = 0.01
MAXIMUM_WRONG_SIDE_DIGIT_WEIGHT = 0.01
MINIMUM_OUTWARD_NORMAL_ALIGNMENT = 0.12
MINIMUM_FINAL_CLEARANCE_M = 0.000040
MAXIMUM_FINAL_CLEARANCE_M = 0.000450


class NailWeightConstrainedProjectionError(ValueError):
    pass


def _finite_float(value: Any, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise NailWeightConstrainedProjectionError(f"{name} is not finite")
    return result


def _normalized_hit(raw: Mapping[str, Any]) -> dict[str, Any]:
    hit = dict(raw)
    required = (
        "ray_hit_ordinal",
        "ray_depth_m",
        "distance_to_expected_point_m",
        "evaluated_triangle_index",
        "raw_triangle_index",
        "raw_component_id",
        "expected_family_weight",
        "foreign_digit_family_weight",
        "wrong_side_digit_weight",
        "expected_family_is_dominant",
        "outward_normal_alignment",
    )
    missing = [name for name in required if name not in hit]
    if missing:
        raise NailWeightConstrainedProjectionError(
            f"ray hit is missing required evidence: {missing}"
        )
    for name in (
        "ray_hit_ordinal",
        "evaluated_triangle_index",
        "raw_triangle_index",
        "raw_component_id",
    ):
        hit[name] = int(hit[name])
        if hit[name] < 0:
            raise NailWeightConstrainedProjectionError(
                f"ray hit has negative {name}: {hit[name]}"
            )
    for name in (
        "ray_depth_m",
        "distance_to_expected_point_m",
        "expected_family_weight",
        "foreign_digit_family_weight",
        "wrong_side_digit_weight",
        "outward_normal_alignment",
    ):
        hit[name] = _finite_float(hit[name], name)
    if hit["ray_depth_m"] < 0.0 or hit["distance_to_expected_point_m"] < 0.0:
        raise NailWeightConstrainedProjectionError(
            "ray depth and expected-point distance must be nonnegative"
        )
    for name in (
        "expected_family_weight",
        "foreign_digit_family_weight",
        "wrong_side_digit_weight",
    ):
        if not 0.0 <= hit[name] <= 1.0 + 1.0e-9:
            raise NailWeightConstrainedProjectionError(
                f"ray hit has weight outside [0, 1]: {name}={hit[name]}"
            )
    hit["expected_family_is_dominant"] = bool(
        hit["expected_family_is_dominant"]
    )
    return hit


def hit_meets_declared_digit_gate(raw: Mapping[str, Any]) -> bool:
    """Return whether one surface hit belongs to the declared digit region."""

    hit = _normalized_hit(raw)
    return (
        hit["expected_family_weight"] >= MINIMUM_EXPECTED_FAMILY_WEIGHT
        and hit["foreign_digit_family_weight"]
        <= MAXIMUM_FOREIGN_DIGIT_FAMILY_WEIGHT
        and hit["wrong_side_digit_weight"] <= MAXIMUM_WRONG_SIDE_DIGIT_WEIGHT
        and hit["expected_family_is_dominant"] is True
        and hit["outward_normal_alignment"]
        >= MINIMUM_OUTWARD_NORMAL_ALIGNMENT
    )


def _hit_score(hit: Mapping[str, Any]) -> tuple[float, float, int, int, int]:
    return (
        float(hit["distance_to_expected_point_m"]),
        float(hit["ray_depth_m"]),
        int(hit["ray_hit_ordinal"]),
        int(hit["evaluated_triangle_index"]),
        int(hit["raw_triangle_index"]),
    )


def select_connected_weight_constrained_grid(
    hit_stacks: Iterable[Sequence[Mapping[str, Any]]],
    *,
    center_sample_index: int,
) -> dict[str, Any]:
    """Select one declared-digit hit per grid sample from one component.

    Candidate components come only from eligible center-sample hits.  A
    component is accepted only if every grid ray has an eligible hit in that
    same component.  This prevents a nail grid from stitching together two
    nearby fingers or selecting a neighboring first hit.
    """

    stacks = [[_normalized_hit(hit) for hit in stack] for stack in hit_stacks]
    if not stacks:
        raise NailWeightConstrainedProjectionError("projection grid has no samples")
    center = int(center_sample_index)
    if not 0 <= center < len(stacks):
        raise NailWeightConstrainedProjectionError(
            "center sample index lies outside the projection grid"
        )
    if any(not stack for stack in stacks):
        raise NailWeightConstrainedProjectionError(
            "one or more grid rays returned no evaluated-body hits"
        )

    eligible = [
        [hit for hit in stack if hit_meets_declared_digit_gate(hit)]
        for stack in stacks
    ]
    center_components = sorted(
        {
            int(hit["raw_component_id"])
            for hit in eligible[center]
        }
    )
    if not center_components:
        raise NailWeightConstrainedProjectionError(
            "center ray has no declared-digit connected-region hit"
        )

    complete_options = []
    component_attempts = []
    for component in center_components:
        selected = []
        missing_samples = []
        for sample_index, hits in enumerate(eligible):
            candidates = [
                hit
                for hit in hits
                if int(hit["raw_component_id"]) == component
            ]
            if not candidates:
                missing_samples.append(sample_index)
                continue
            selected.append(min(candidates, key=_hit_score))
        complete = not missing_samples and len(selected) == len(stacks)
        component_attempts.append(
            {
                "raw_component_id": component,
                "complete": complete,
                "selected_sample_count": len(selected),
                "missing_sample_indices": missing_samples,
            }
        )
        if complete:
            distances = [
                float(hit["distance_to_expected_point_m"]) for hit in selected
            ]
            depths = [float(hit["ray_depth_m"]) for hit in selected]
            complete_options.append(
                (
                    (
                        max(distances),
                        sum(distances),
                        sum(depths),
                        component,
                    ),
                    component,
                    selected,
                )
            )
    if not complete_options:
        raise NailWeightConstrainedProjectionError(
            "no declared-digit connected component covers the complete grid"
        )

    _score, component, selected = min(complete_options, key=lambda row: row[0])
    first_hit_rejected = sum(
        selected_hit["ray_hit_ordinal"] != 0 for selected_hit in selected
    )
    return {
        "schema": SCHEMA,
        "sample_count": len(stacks),
        "center_sample_index": center,
        "selected_raw_component_id": component,
        "selected_hits": selected,
        "selected_hit_ordinals": [
            int(hit["ray_hit_ordinal"]) for hit in selected
        ],
        "neighboring_or_occluding_first_hit_rejected_count": first_hit_rejected,
        "every_sample_matches_declared_digit": True,
        "every_sample_uses_one_connected_region": True,
        "automatic_bone_remap_performed": False,
        "component_attempts": component_attempts,
        "passed": True,
    }


def validate_final_evaluated_shell_gate(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed unless the complete evaluated nail shell clears the body."""

    record = dict(raw)
    source_count = int(record.get("source_top_vertex_count", 0))
    evaluated_count = int(record.get("evaluated_shell_vertex_count", 0))
    genuine = int(record.get("exact_genuine_triangle_pair_count", -1))
    minimum = _finite_float(
        record.get("minimum_unsigned_surface_clearance_m"),
        "minimum_unsigned_surface_clearance_m",
    )
    maximum = _finite_float(
        record.get("maximum_unsigned_surface_clearance_m"),
        "maximum_unsigned_surface_clearance_m",
    )
    gates = {
        "body_surface_is_evaluated": record.get("body_surface_space")
        == "evaluated_rest",
        "nail_surface_is_evaluated_armature_then_solidify": record.get(
            "nail_surface_space"
        )
        == "evaluated_armature_then_solidify",
        "exact_loop_triangle_narrow_phase_used": record.get(
            "exact_narrow_phase_used"
        )
        is True,
        "complete_shell_included": record.get("complete_shell_included") is True,
        "solidify_rim_included": record.get("solidify_rim_included") is True,
        "solidify_two_surface_blocks_present": source_count > 0
        and evaluated_count == source_count * 2,
        "zero_exact_genuine_penetrations": genuine == 0,
        "minimum_clearance_passed": minimum >= MINIMUM_FINAL_CLEARANCE_M,
        "maximum_clearance_passed": maximum <= MAXIMUM_FINAL_CLEARANCE_M,
        "clearance_order_valid": minimum <= maximum,
        "body_mesh_unchanged": record.get("body_mesh_unchanged") is True,
        "official_rig_unchanged": record.get("official_rig_unchanged") is True,
        "body_modifier_stack_unchanged": record.get(
            "body_modifier_stack_unchanged"
        )
        is True,
        "no_automatic_bone_remap": record.get(
            "automatic_bone_remap_performed"
        )
        is False,
    }
    if not all(gates.values()):
        failed = sorted(name for name, passed in gates.items() if not passed)
        raise NailWeightConstrainedProjectionError(
            f"final evaluated nail shell gate failed: {failed}"
        )
    return {
        "schema": SCHEMA,
        "gates": gates,
        "source_top_vertex_count": source_count,
        "evaluated_shell_vertex_count": evaluated_count,
        "exact_genuine_triangle_pair_count": genuine,
        "minimum_unsigned_surface_clearance_m": minimum,
        "maximum_unsigned_surface_clearance_m": maximum,
        "broad_phase_is_not_the_pass_gate": True,
        "automatic_bone_remap_performed": False,
        "passed": True,
    }


__all__ = [
    "MAXIMUM_FINAL_CLEARANCE_M",
    "MAXIMUM_FOREIGN_DIGIT_FAMILY_WEIGHT",
    "MAXIMUM_WRONG_SIDE_DIGIT_WEIGHT",
    "MINIMUM_EXPECTED_FAMILY_WEIGHT",
    "MINIMUM_FINAL_CLEARANCE_M",
    "MINIMUM_OUTWARD_NORMAL_ALIGNMENT",
    "NailWeightConstrainedProjectionError",
    "SCHEMA",
    "hit_meets_declared_digit_gate",
    "select_connected_weight_constrained_grid",
    "validate_final_evaluated_shell_gate",
]
