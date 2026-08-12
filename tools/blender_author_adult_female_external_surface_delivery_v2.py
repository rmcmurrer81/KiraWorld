"""Second and final bounded delivery adapter for the adult surface.

Delivery v1 proved that removing the legacy plate before local subdivision can
make the sparse curved under-body boundary overlap.  This preserved attempt-2
adapter performs the proven local subdivision first, then subtracts the full
legacy v2 posterior/front fields and runs a new exact final audit.  It never
saves, exports, assigns, activates, publishes, adds hair, or creates separate
anatomy geometry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from Core.avatar_adult_female_surface_authoring import SurfaceFrame
from Core.avatar_adult_female_surface_authoring_delivery_v2 import (
    FRONT_FEATURE_SAMPLE_POINTS,
    METHOD_ID,
    REAR_FEATURE_SAMPLE_POINTS,
    VisibleSurfaceParameters,
    build_authoring_contract,
    feature_sample_displacements,
    front_landmark_memberships,
    front_support_taper,
    front_surface_displacement,
    rear_landmark_memberships,
    rear_support_taper,
    rear_surface_displacement,
)
import tools.blender_author_adult_female_external_surface_v3 as checkpoint_adapter
from tools.blender_author_adult_female_external_surface import (
    AdultFemaleSurfaceAuthoringError,
)
from tools.blender_author_adult_female_external_surface_delivery_v1 import (
    _apply_same_surface_torso_landmarks,
    _mesh_snapshot,
    _remove_complete_legacy_v2_fields,
    _smooth_only_local_authored_faces,
)


def refine_existing_continuous_adult_female_surface_delivery_v2(
    obj: bpy.types.Object,
    *,
    front_frame: SurfaceFrame,
    rear_frame: SurfaceFrame,
    parameters: VisibleSurfaceParameters,
    legacy_v2_frame: SurfaceFrame,
    legacy_v2_posterior_frame: SurfaceFrame,
    legacy_v2_relief_scale_m: float,
    legacy_v2_taper_power: int,
    legacy_v2_minimum_normal_alignment: float,
    front_visible_sheet_minimum_outward_depth_m: float,
    rear_visible_sheet_minimum_outward_depth_m: float,
    body_scale: float,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    if obj is None or obj.type != "MESH" or obj.mode != "OBJECT":
        raise AdultFemaleSurfaceAuthoringError("delivery_v2_requires_object_mesh")
    if not bool(obj.get("primary_surface")):
        raise AdultFemaleSurfaceAuthoringError("delivery_v2_requires_primary_surface")
    if obj.get("adult_female_surface_detail_method_id") != "generic_continuous_adult_female_external_surface_v2":
        raise AdultFemaleSurfaceAuthoringError("delivery_v2_requires_exact_v2_base")
    if bool(obj.get("runtime_activation_allowed")):
        raise AdultFemaleSurfaceAuthoringError("delivery_v2_refuses_runtime_activatable_object")

    original_mesh = obj.data
    source_topology, source_pairs, source_digest = _mesh_snapshot(
        original_mesh,
        parameters.degeneracy_area_m2,
    )
    staging_mesh = original_mesh.copy()
    staging_mesh.name = f"{original_mesh.name}__{METHOD_ID}_staging"
    obj.data = staging_mesh
    committed = False
    patched_names = {
        "METHOD_ID": METHOD_ID,
        "FRONT_FEATURE_SAMPLE_POINTS": FRONT_FEATURE_SAMPLE_POINTS,
        "REAR_FEATURE_SAMPLE_POINTS": REAR_FEATURE_SAMPLE_POINTS,
        "build_authoring_contract": build_authoring_contract,
        "feature_sample_displacements": feature_sample_displacements,
        "front_landmark_memberships": front_landmark_memberships,
        "front_support_taper": front_support_taper,
        "front_surface_displacement": front_surface_displacement,
        "rear_landmark_memberships": rear_landmark_memberships,
        "rear_support_taper": rear_support_taper,
        "rear_surface_displacement": rear_surface_displacement,
        # The complete legacy target is reversed after stable subdivision.
        "v2_surface_displacement": lambda *_args, **_kwargs: 0.0,
        "v2_posterior_surface_displacement": lambda *_args, **_kwargs: 0.0,
    }
    originals = {name: getattr(checkpoint_adapter, name) for name in patched_names}
    try:
        for name, value in patched_names.items():
            setattr(checkpoint_adapter, name, value)
        detail = checkpoint_adapter.refine_existing_continuous_adult_female_surface_v3(
            obj,
            front_frame=front_frame,
            rear_frame=rear_frame,
            parameters=parameters,
            legacy_v2_frame=legacy_v2_frame,
            legacy_v2_posterior_frame=legacy_v2_posterior_frame,
            legacy_v2_relief_scale_m=float(legacy_v2_relief_scale_m),
            legacy_v2_taper_power=int(legacy_v2_taper_power),
            front_visible_sheet_minimum_outward_depth_m=float(
                front_visible_sheet_minimum_outward_depth_m
            ),
            rear_visible_sheet_minimum_outward_depth_m=float(
                rear_visible_sheet_minimum_outward_depth_m
            ),
            project_root=project_root,
        )

        legacy_removal = _remove_complete_legacy_v2_fields(
            obj.data,
            front_frame=legacy_v2_frame,
            posterior_frame=legacy_v2_posterior_frame,
            target_relief_scale_m=float(legacy_v2_relief_scale_m),
            target_taper_power=int(legacy_v2_taper_power),
            minimum_normal_alignment=float(legacy_v2_minimum_normal_alignment),
        )
        cleaned_topology, cleaned_pairs, cleaned_digest = _mesh_snapshot(
            obj.data,
            parameters.degeneracy_area_m2,
        )
        cleanup_new_pairs = cleaned_pairs.difference(source_pairs)
        if cleanup_new_pairs:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v2_post_subdivision_legacy_removal_created_new_intersections:"
                + str(sorted(cleanup_new_pairs)[0])
            )

        torso = _apply_same_surface_torso_landmarks(obj, body_scale=float(body_scale))
        smoothing = _smooth_only_local_authored_faces(obj.data, body_scale=float(body_scale))
        final_topology, final_pairs, final_digest = _mesh_snapshot(
            obj.data,
            parameters.degeneracy_area_m2,
        )
        new_pairs = final_pairs.difference(source_pairs)
        if new_pairs:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v2_new_global_self_intersections_detected:"
                f"before={len(source_pairs)};after={len(final_pairs)};"
                f"first_new_pair={sorted(new_pairs)[0]}"
            )
        if (
            final_topology["primary_surface_components"] != 1
            or final_topology["boundary_edges"] != 0
            or final_topology["nonmanifold_edges"] != 0
            or final_topology["degenerate_faces"] != 0
        ):
            raise AdultFemaleSurfaceAuthoringError("delivery_v2_final_topology_gate_failed")

        detail["delivery_method_id"] = METHOD_ID
        detail["status"] = "DELIVERY_COMPONENT_INACTIVE_AWAITING_OWNER_VISUAL_REVIEW"
        detail["checkpoint_source_mesh_digest_sha256"] = source_digest
        detail["post_subdivision_legacy_clean_mesh_digest_sha256"] = cleaned_digest
        detail["result_mesh_digest_sha256"] = final_digest
        detail["checkpoint_source_topology"] = source_topology
        detail["post_subdivision_legacy_clean_topology"] = cleaned_topology
        detail["result_topology"] = final_topology
        detail["legacy_field_removal_post_subdivision"] = legacy_removal
        detail["same_surface_torso_landmarks"] = torso
        detail["localized_smooth_shading"] = smoothing
        detail["checkpoint_source_intersection_pairs"] = len(source_pairs)
        detail["post_subdivision_legacy_clean_intersection_pairs"] = len(cleaned_pairs)
        detail["result_global_nonadjacent_self_intersection_pairs"] = len(final_pairs)
        detail["new_global_nonadjacent_self_intersection_pairs"] = len(new_pairs)
        detail["operation_order"] = [
            "local_subdivision_on_proven_v2_surface",
            "delivery_field_application",
            "full_legacy_v2_posterior_then_front_removal",
            "same_surface_torso_landmarks",
            "final_exact_audit",
        ]
        detail["failed_delivery_v1_preserved"] = True
        detail["rounded_transition_support"] = True
        detail["hair_dependency"] = False
        detail["scalp_geometry_changed"] = False
        detail["same_primary_mesh_object"] = True
        detail["separate_anatomy_mesh_created"] = False
        detail["boolean_anatomy_union_used"] = False
        detail["copied_anatomy_geometry_used"] = False
        detail["runtime_activation_allowed"] = False
        detail["render_performed"] = False
        detail["export_performed"] = False

        try:
            metadata = json.loads(str(obj.get("adult_female_surface_metadata_json") or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            metadata = {}
        metadata["delivery_refinement_v2"] = detail
        metadata["result_mesh_digest_sha256"] = final_digest
        metadata["qualified_for_adult_foundation"] = False
        metadata["runtime_activation_allowed"] = False
        obj["adult_female_surface_detail_method_id"] = METHOD_ID
        obj["adult_female_surface_detail_status"] = detail["status"]
        obj["adult_female_surface_metadata_json"] = json.dumps(
            metadata,
            sort_keys=True,
            separators=(",", ":"),
        )
        obj["adult_foundation_qualified"] = False
        obj["runtime_activation_allowed"] = False
        committed = True
        return detail
    finally:
        for name, value in originals.items():
            setattr(checkpoint_adapter, name, value)
        if not committed:
            failed_mesh = obj.data
            obj.data = original_mesh
            if failed_mesh is not original_mesh and failed_mesh.users == 0:
                bpy.data.meshes.remove(failed_mesh)
        elif staging_mesh.users == 0:
            bpy.data.meshes.remove(staging_mesh)


__all__ = [
    "AdultFemaleSurfaceAuthoringError",
    "refine_existing_continuous_adult_female_surface_delivery_v2",
]
