"""Attempt-2 contract for the bounded continuous adult-surface delivery.

The analytic field is unchanged from delivery v1.  V2 records the repaired
operation order: subdivide the proven v2 surface first, then remove the full
legacy v2 field, preserving the failed v1 implementation and evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from Core.avatar_adult_female_surface_authoring import SurfaceFrame
from Core.avatar_adult_female_surface_authoring_delivery_v1 import (
    BASE_DETAIL_METHOD_ID,
    FRONT_FEATURE_SAMPLE_POINTS,
    OPENING_REPRESENTATION,
    REAR_FEATURE_SAMPLE_POINTS,
    VisibleSurfaceParameters,
    feature_sample_displacements,
    front_landmark_memberships,
    front_structured_field,
    front_support_taper,
    front_surface_displacement,
    load_required_relationships,
    parameters_from_mapping,
    rear_landmark_memberships,
    rear_structured_field,
    rear_support_taper,
    rear_surface_displacement,
)
from Core.avatar_adult_female_surface_authoring_delivery_v1 import (
    build_authoring_contract as _build_v1_contract,
)


METHOD_ID = "generic_continuous_adult_female_external_surface_delivery_v2"


def build_authoring_contract(
    project_root: Path,
    front_frame: SurfaceFrame,
    rear_frame: SurfaceFrame,
    parameters: VisibleSurfaceParameters,
) -> dict[str, Any]:
    contract = _build_v1_contract(project_root, front_frame, rear_frame, parameters)
    contract["schema_version"] = 5
    contract["method_id"] = METHOD_ID
    contract["operation_order"] = [
        "local_subdivision_on_proven_v2_surface",
        "delivery_field_application",
        "full_legacy_v2_posterior_then_front_removal",
        "final_exact_topology_and_intersection_audit",
    ]
    contract["legacy_field_removed_before_subdivision"] = False
    contract["failed_delivery_v1_preserved"] = True
    return contract


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
