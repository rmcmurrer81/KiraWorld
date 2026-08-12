"""Build one complete, bald, inactive Kira body for private owner review.

This is a delivery-focused successor to the frozen R15 builder.  It reuses the
qualified adult-female foundation and accepted R15 components, adds only the
bounded presentation/adult-surface repairs, and deliberately instantiates no
scalp-hair provider or scalp-hair asset.  Eyebrows, lashes, and lid definition
remain facial presentation components.  The output boundary is append-only and
never assigns, activates, clothes, publishes, uploads, or exports a GLB.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
import time
from typing import Any, Mapping, Sequence

import bpy
from mathutils import Quaternion, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tools.blender_build_profiled_kira_adult_candidate as r15
from Core.avatar_adult_female_surface_authoring import (
    LANDMARK_GROUP_PREFIX,
    SurfaceFrame,
    frame_from_mapping,
    parameters_from_mapping,
)
from Core.avatar_adult_female_surface_authoring_v3 import (
    METHOD_ID as DELIVERY_SURFACE_METHOD_ID,
    parameters_from_mapping as delivery_parameters_from_mapping,
)
from Core.avatar_profiled_adult_candidate_contract import (
    ProfiledAdultCandidateContractError,
    evaluate_profiled_candidate_preflight,
    load_validated_profiled_candidate_builder_config,
    scaled_adult_surface_settings,
    verify_live_kira_state_unchanged,
)
from Core.avatar_profiled_nonanatomy_presentation_v2 import FACE_TARGETS
from tools.blender_author_adult_female_external_surface import (
    author_continuous_adult_female_surface,
)
from tools.blender_author_adult_female_external_surface_v3 import (
    refine_existing_continuous_adult_female_surface_v3,
)
from tools.blender_author_adult_female_external_surface_v2 import (
    refine_existing_continuous_adult_female_surface_v2,
)
from tools.blender_profiled_adult_candidate_components import (
    add_natural_helper_eyes,
    add_natural_nails,
    apply_knee_solution,
    apply_relaxed_hand_pose,
    build_body_object,
    build_official_rig_and_normalized_weights,
    build_warm_skin_material,
    prepare_profiled_body_source,
    reset_pose,
    sha256_file,
    solve_bilateral_knee_axes_and_actions,
    transformed_source_point,
)
from tools.blender_profiled_adult_candidate_components_v2 import (
    add_feminine_eye_surrounds_v2,
    calibrate_warm_non_pale_skin_v2,
    component_bone_frame_v2,
    install_knee_corrective_smoothing_v2,
    install_shadow_controlled_review_rig_v2,
)
from tools.blender_repair_bounded_self_intersections import (
    repair_bounded_self_intersections,
)


class KiraBaldDeliveryBuildError(RuntimeError):
    """Raised before a partial result can be represented as review-ready."""


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DELIVERY_POLICY_PATH = Path(
    "Avatar/avatar_builder/tooling/kira_bald_low_resource_body_delivery_v1.json"
)
DELIVERY_SURFACE_CONFIG_PATH = Path(
    "Avatar/avatar_builder/tooling/adult_female_surface_v3_inactive_refinement.json"
)
BOUNDED_ANATOMY_RESULT_PATH = Path(
    "RecoverySprint/adult_surface_delivery_probe/BOUNDED_DELIVERY_RESULT.json"
)
BOUNDED_FACE_RESULT_PATH = Path(
    "RecoverySprint/continuation_20260801/"
    "KIRA_FACE_DELIVERY_BOUNDED_RESULT_20260801.json"
)
BOUNDED_NAIL_RESULT_PATH = Path(
    "RecoverySprint/continuation_20260801/"
    "KIRA_NAIL_DELIVERY_BOUNDED_RESULT_20260801.json"
)
DELIVERY_IMPLEMENTATION_PATHS = (
    Path("tools/blender_build_profiled_kira_bald_delivery_candidate.py"),
    Path("tools/blender_profiled_adult_candidate_components_v2.py"),
    Path("Core/avatar_profiled_nonanatomy_presentation_v2.py"),
    Path("tools/blender_author_adult_female_external_surface_v3.py"),
    Path("Core/avatar_adult_female_surface_authoring_v3.py"),
    DELIVERY_POLICY_PATH,
    DELIVERY_SURFACE_CONFIG_PATH,
    BOUNDED_ANATOMY_RESULT_PATH,
    BOUNDED_FACE_RESULT_PATH,
    BOUNDED_NAIL_RESULT_PATH,
)
REQUIRED_REVIEW_VIEW_LABELS = (
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
    "neutral_standing",
    "crown_top_scalp",
    "rear_scalp_hairline",
    "bilateral_knee_flexion",
    "seated_front_three_quarter",
    "seated_side_contact",
)


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(
        description="Build the complete bald low-resource Kira body for private review."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help=(
            "New project-relative Avatar/private_owner_review/"
            "kira_profiled_adult_candidate_* directory."
        ),
    )
    parser.add_argument(
        "--acknowledge-inactive-private-candidate",
        action="store_true",
        help="Required acknowledgement; never authorizes assignment or activation.",
    )
    parser.add_argument(
        "--render-owner-review",
        action="store_true",
        help="Required for this delivery builder; renders the exact 23-view package.",
    )
    return parser.parse_args(argv)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise KiraBaldDeliveryBuildError(f"JSON root is not an object: {path}")
    return payload


def _validate_delivery_policy() -> tuple[dict[str, Any], dict[str, Any]]:
    path = (PROJECT_ROOT / DELIVERY_POLICY_PATH).resolve(strict=True)
    policy = _read_json(path)
    if (
        policy.get("policy_id") != "kira_bald_low_resource_body_delivery_v1"
        or policy.get("asset_id") != "KIRA_BALD_LOW_RESOURCE_BODY"
        or tuple(policy.get("required_review_view_labels", ()))
        != REQUIRED_REVIEW_VIEW_LABELS
    ):
        raise KiraBaldDeliveryBuildError("bald delivery policy identity or view list drifted")
    scalp = policy.get("scalp_hair_policy", {})
    forbidden_true = (
        "scalp_hair_provider_allowed",
        "scalp_hair_objects_allowed",
        "scalp_hair_materials_allowed",
        "scalp_hair_images_or_textures_allowed",
        "scalp_hair_guides_allowed",
        "scalp_hair_controllers_allowed",
        "black_scalp_cap_or_dome_allowed",
        "painted_scalp_hair_allowed",
        "hair_state_review_renders_allowed",
    )
    if any(scalp.get(key) is not False for key in forbidden_true):
        raise KiraBaldDeliveryBuildError("bald delivery scalp-hair prohibition drifted")
    if (
        scalp.get("natural_primary_skin_surface_continues_over_scalp") is not True
        or scalp.get(
            "eyebrows_lashes_and_lid_definition_are_facial_presentation_not_scalp_hair"
        )
        is not True
    ):
        raise KiraBaldDeliveryBuildError("natural scalp/facial presentation policy drifted")
    output = policy.get("output_policy", {})
    if (
        output.get("glb_exported_by_this_builder") is not False
        or output.get("runtime_activation_allowed") is not False
        or output.get("assignment_allowed") is not False
        or output.get("publication_allowed") is not False
    ):
        raise KiraBaldDeliveryBuildError("bald delivery output safety policy drifted")
    return policy, {
        "path": DELIVERY_POLICY_PATH.as_posix(),
        "sha256": sha256_file(path),
        "policy_id": policy["policy_id"],
        "asset_id": policy["asset_id"],
        "exact_required_view_count": len(REQUIRED_REVIEW_VIEW_LABELS),
    }


def _capture_delivery_hash_snapshot(
    *,
    config: Mapping[str, Any],
    config_report: Mapping[str, Any],
    profile: Mapping[str, Any],
    preflight: Mapping[str, Any],
) -> dict[str, Any]:
    snapshot = r15._capture_build_hash_snapshot(  # noqa: SLF001
        config=config,
        config_report=config_report,
        profile=profile,
        preflight=preflight,
        provider_path=None,
        provider_sha256=None,
    )
    records = snapshot["records"]
    for relative in DELIVERY_IMPLEMENTATION_PATHS:
        r15._record_hash_binding(  # noqa: SLF001
            records,
            raw_path=relative.as_posix(),
            expected_sha256=None,
            role="bald_delivery_executed_implementation_or_policy",
        )
    for target in FACE_TARGETS:
        r15._record_hash_binding(  # noqa: SLF001
            records,
            raw_path=target["path"],
            expected_sha256=target["sha256"],
            role=f"bounded_rejected_qualitative_face_target:{target['target_id']}",
        )
    snapshot["records"] = dict(sorted(records.items()))
    snapshot["record_count"] = len(records)
    snapshot["delivery_builder_revision"] = "kira_bald_delivery_candidate_v1"
    snapshot["scalp_hair_provider_bound"] = False
    return snapshot


def _synchronize_face_geometry_into_source(
    source: dict[str, Any], body: Any,
) -> dict[str, Any]:
    """Make pre-rig source coordinates exactly match the face-directed body.

    The v2 face adapter first proves compatibility against the untouched compact
    source.  After that proof, this inverse coordinate conversion updates the
    source arrays before joint construction, surface authoring, and helper-eye
    construction.  It does not apply a second face delta.
    """

    scale = float(source["uniform_scale"])
    floor_z = float(source["source_floor_z"])
    if scale <= 0.0:
        raise KiraBaldDeliveryBuildError("invalid source scale during face synchronization")
    source_vertices = source["source_vertices_after_all_targets"]
    body_vertices = source["body_vertices"]
    for source_index, compact_index in source["source_to_body"].items():
        point = body.data.vertices[int(compact_index)].co.copy()
        body_vertices[int(compact_index)] = point.copy()
        source_vertices[int(source_index)] = Vector(
            (
                float(point.x) / scale,
                float(point.z) / scale + floor_z,
                -float(point.y) / scale,
            )
        )
    errors = [
        float(
            (
                transformed_source_point(source, int(source_index))
                - body.data.vertices[int(compact_index)].co
            ).length
        )
        for source_index, compact_index in source["source_to_body"].items()
    ]
    maximum = max(errors, default=math.inf)
    if maximum > 1.0e-7:
        raise KiraBaldDeliveryBuildError(
            f"pre-rig face/source synchronization error: {maximum:.12f}"
        )
    return {
        "method": "inverse_makehuman_coordinate_sync_after_compatible_face_v2",
        "synchronized_body_vertex_count": len(errors),
        "maximum_roundtrip_error_m": maximum,
        "completed_before_rig": True,
        "completed_before_adult_surface_authoring": True,
        "face_delta_applied_exactly_once": True,
    }


def _scaled_frame(raw: Mapping[str, Any], scale: float) -> SurfaceFrame:
    return SurfaceFrame(
        origin=tuple(float(value) * scale for value in raw["origin"]),
        lateral_axis=tuple(float(value) for value in raw["lateral_axis"]),
        longitudinal_axis=tuple(float(value) for value in raw["longitudinal_axis"]),
        outward_axis=tuple(float(value) for value in raw["outward_axis"]),
        half_width_m=float(raw["half_width_m"]) * scale,
        half_length_m=float(raw["half_length_m"]) * scale,
        max_surface_offset_m=float(raw["max_surface_offset_m"]) * scale,
    )


def _author_delivery_adult_surface(
    *, body: Any, config: Mapping[str, Any], target_height_m: float,
) -> tuple[dict[str, Any], Vector]:
    scaled_frame, scaled_parameters = scaled_adult_surface_settings(
        config["adult_surface_authoring"], target_height_m
    )
    frame = frame_from_mapping(scaled_frame)
    parameters = parameters_from_mapping(scaled_parameters)
    report = author_continuous_adult_female_surface(
        body,
        frame=frame,
        parameters=parameters,
        project_root=PROJECT_ROOT,
    )
    if report.get("global_topology_ready_for_qualification") is not True:
        raise KiraBaldDeliveryBuildError("v1 adult surface topology gate failed")

    detail_config = config["adult_surface_authoring"]["structured_detail_refinement"]
    baseline_height = float(config["adult_surface_authoring"]["baseline_height_m"])
    ratio = float(target_height_m) / baseline_height
    posterior_payload = dict(detail_config["posterior_frame"])
    posterior_payload["origin"] = [float(value) * ratio for value in posterior_payload["origin"]]
    for key in ("half_width_m", "half_length_m", "max_surface_offset_m"):
        posterior_payload[key] = float(posterior_payload[key]) * ratio
    posterior_frame = frame_from_mapping(posterior_payload)
    relief_scale = float(detail_config["baseline_relief_scale_m"]) * ratio
    v2 = refine_existing_continuous_adult_female_surface_v2(
        body,
        frame=frame,
        base_parameters=parameters,
        posterior_frame=posterior_frame,
        target_relief_scale_m=relief_scale,
        target_taper_power=int(detail_config["boundary_taper_power"]),
    )
    if (
        v2.get("new_global_nonadjacent_self_intersection_pairs") != 0
        or v2.get("topology_changed") is not False
        or v2.get("rig_weights_changed") is not False
        or v2.get("landmark_group_names_changed") is not False
        or v2.get("posterior_landmark_memberships_rebound_to_curved_frame") is not True
    ):
        raise KiraBaldDeliveryBuildError("v2 adult detail invariant failed")

    delivery_config = _read_json(PROJECT_ROOT / DELIVERY_SURFACE_CONFIG_PATH)
    if (
        delivery_config.get("method_id") != DELIVERY_SURFACE_METHOD_ID
        or delivery_config.get("required_base_detail_method_id")
        != "generic_continuous_adult_female_external_surface_v2"
    ):
        raise KiraBaldDeliveryBuildError("delivery adult-surface config identity drifted")
    delivery_scale = float(target_height_m) / float(delivery_config["baseline_height_m"])
    parameter_values = dict(delivery_config["parameters"])
    parameter_values["front_prominence_scale_m"] *= delivery_scale
    parameter_values["rear_prominence_scale_m"] *= delivery_scale
    parameter_values["degeneracy_area_m2"] *= delivery_scale * delivery_scale
    delivery_parameters = delivery_parameters_from_mapping(parameter_values)
    delivery = refine_existing_continuous_adult_female_surface_v3(
        body,
        front_frame=_scaled_frame(
            delivery_config["front_visible_sheet_frame"], delivery_scale
        ),
        rear_frame=_scaled_frame(
            delivery_config["rear_anal_sheet_frame"], delivery_scale
        ),
        parameters=delivery_parameters,
        legacy_v2_frame=_scaled_frame(
            config["adult_surface_authoring"]["frame"], ratio
        ),
        legacy_v2_posterior_frame=_scaled_frame(
            detail_config["posterior_frame"], ratio
        ),
        legacy_v2_relief_scale_m=relief_scale,
        legacy_v2_taper_power=int(detail_config["boundary_taper_power"]),
        front_visible_sheet_minimum_outward_depth_m=float(
            delivery_config["surface_selection"][
                "front_visible_sheet_minimum_outward_depth_m"
            ]
        )
        * delivery_scale,
        rear_visible_sheet_minimum_outward_depth_m=float(
            delivery_config["surface_selection"][
                "rear_visible_sheet_minimum_outward_depth_m"
            ]
        )
        * delivery_scale,
        project_root=PROJECT_ROOT,
    )
    topology = delivery.get("result_topology", {})
    if (
        delivery.get("status")
        != "REFINED_INACTIVE_AWAITING_INDEPENDENT_REQUALIFICATION"
        or delivery.get("detail_method_id") != DELIVERY_SURFACE_METHOD_ID
        or topology.get("primary_surface_components") != 1
        or topology.get("boundary_edges") != 0
        or topology.get("nonmanifold_edges") != 0
        or topology.get("degenerate_faces") != 0
        or delivery.get("new_global_nonadjacent_self_intersection_pairs") != 0
        or delivery.get("same_primary_mesh_object") is not True
        or delivery.get("source_anatomy_geometry_copied") is not False
        or delivery.get("separate_anatomy_mesh_created") is not False
        or delivery.get("boolean_anatomy_union_used") is not False
        or delivery.get("runtime_activation_allowed") is not False
    ):
        raise KiraBaldDeliveryBuildError("delivery adult-surface hard gate failed")
    report["structured_detail_refinement_v2"] = v2
    bounded_result_path = PROJECT_ROOT / BOUNDED_ANATOMY_RESULT_PATH
    bounded_result = _read_json(bounded_result_path)
    if (
        bounded_result.get("bounded_attempts_consumed") != 2
        or bounded_result.get("integration_instruction")
        != (
            "Do not bind either delivery_v1 or delivery_v2. Present the best safe "
            "complete candidate with the preserved v3/R15 visible defect disclosed, "
            "or wait for owner direction; do not begin a third anatomy repair attempt."
        )
    ):
        raise KiraBaldDeliveryBuildError("bounded anatomy fallback record drifted")
    report["visible_surface_refinement_v3_fallback"] = delivery
    report["bounded_delivery_attempt_result"] = {
        "path": BOUNDED_ANATOMY_RESULT_PATH.as_posix(),
        "sha256": sha256_file(bounded_result_path),
        "bounded_attempts_consumed": 2,
        "new_delivery_component_passed": False,
        "fallback_method": "checkpointed_v3_attempt_06",
    }
    report["known_unresolved_visual_defects"] = [
        "localized anatomy has a rectangular or plate-like transition",
        "localized anatomy has schematic parallel ridges instead of naturally blended folds",
    ]
    report["owner_visual_decision_required"] = True
    report["final_detail_method_id"] = DELIVERY_SURFACE_METHOD_ID
    body["adult_relationship_surface_method"] = str(report.get("method_id") or "")
    body["adult_relationship_surface_detail_method"] = DELIVERY_SURFACE_METHOD_ID
    body["adult_relationships_require_independent_requalification"] = True
    return report, Vector(tuple(scaled_frame["origin"]))


def _set_knee_without_reset(armature: Any, solution: Mapping[str, Any]) -> None:
    lower = armature.pose.bones[str(solution["lower_bone"])]
    lower.rotation_mode = "QUATERNION"
    lower.rotation_quaternion = Quaternion(
        Vector(tuple(solution["axis_vector"])),
        math.radians(float(solution["signed_angle_degrees"])),
    )


def _apply_bilateral_knee_pose(armature: Any, knee_report: Mapping[str, Any]) -> None:
    reset_pose(armature)
    _set_knee_without_reset(armature, knee_report["solutions"]["left"])
    _set_knee_without_reset(armature, knee_report["solutions"]["right"])
    bpy.context.view_layer.update()


def _apply_seated_pose(
    armature: Any, knee_report: Mapping[str, Any], target_height_m: float,
) -> dict[str, Any]:
    reset_pose(armature)
    for side in ("L", "R"):
        upper = armature.pose.bones.get(f"upperleg01.{side}")
        if upper is None:
            raise KiraBaldDeliveryBuildError(f"seated upper-leg bone missing: {side}")
        upper.rotation_mode = "XYZ"
        upper.rotation_euler = (math.radians(-72.0), 0.0, 0.0)
    for name in ("left", "right"):
        solution = dict(knee_report["solutions"][name])
        solution["signed_angle_degrees"] = 76.0 * float(solution.get("sign", 1.0))
        _set_knee_without_reset(armature, solution)
    spine = armature.pose.bones.get("spine05")
    if spine is not None:
        spine.rotation_mode = "XYZ"
        spine.rotation_euler = (math.radians(4.0), 0.0, 0.0)
    root = armature.pose.bones.get("root")
    if root is None:
        raise KiraBaldDeliveryBuildError("seated root bone missing")
    root.location = (0.0, 0.0, -float(target_height_m) * 0.19)
    bpy.context.view_layer.update()
    return {
        "method": "bounded_private_seated_review_pose_v1",
        "upper_leg_flexion_degrees": -72.0,
        "lower_leg_signed_flexion_degrees": 76.0,
        "root_lowering_m": -float(target_height_m) * 0.19,
        "contact_or_stability_claim": False,
        "owner_visual_contact_review_required": True,
    }


def _add_private_seat_prop(target_height_m: float) -> Any:
    material = bpy.data.materials.new("Kira_Private_Seat_Contact_Diagnostic_Material")
    material.diffuse_color = (0.025, 0.045, 0.070, 1.0)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = material.diffuse_color
        principled.inputs["Roughness"].default_value = 0.62
    bpy.ops.mesh.primitive_cube_add(
        location=(0.0, 0.075, float(target_height_m) * 0.269),
        scale=(
            float(target_height_m) * 0.255,
            float(target_height_m) * 0.19,
            float(target_height_m) * 0.018,
        ),
    )
    seat = bpy.context.object
    seat.name = "Kira_Private_Seat_Contact_Diagnostic"
    seat.data.materials.append(material)
    seat.hide_render = True
    seat["private_review_prop_only"] = True
    seat["runtime_activation_allowed"] = False
    seat["publication_allowed"] = False
    return seat


def _zero_scalp_hair_inventory(
    *, body: Any, candidate_objects: Sequence[Any], policy_report: Mapping[str, Any],
) -> dict[str, Any]:
    facial_roles = {"brow", "upper_lash", "lower_lid"}
    facial_objects = [
        obj
        for obj in candidate_objects
        if str(obj.get("facial_presentation_role") or "") in facial_roles
    ]
    facial_materials = {
        material.name
        for obj in facial_objects
        if hasattr(obj.data, "materials")
        for material in obj.data.materials
        if material is not None
    }

    def object_is_scalp_hair(obj: Any) -> bool:
        if obj in facial_objects:
            return False
        name = obj.name.lower()
        marked = any(
            bool(obj.get(key))
            for key in (
                "responsive_avatar_hair",
                "scalp_hair",
                "dynamic_hair",
                "hair_groom",
            )
        )
        tokened = any(
            token in name
            for token in ("scalp_hair", "hair_groom", "hair_master", "responsive_groom")
        )
        controlled = any(
            key in obj
            for key in (
                "hair_wind_direction_minus1_1",
                "hair_wetness_0_1",
                "hair_dryness_0_1",
            )
        )
        return marked or tokened or controlled

    scalp_objects = [obj.name for obj in candidate_objects if object_is_scalp_hair(obj)]
    scalp_materials = [
        material.name
        for material in bpy.data.materials
        if material.name not in facial_materials
        and any(token in material.name.lower() for token in ("scalp", "hair", "groom"))
    ]
    scalp_images = [
        image.name
        for image in bpy.data.images
        if any(token in image.name.lower() for token in ("scalp", "hair", "groom"))
    ]
    scalp_node_groups = [
        group.name
        for group in bpy.data.node_groups
        if any(token in group.name.lower() for token in ("scalp", "hair", "groom"))
    ]
    controller_objects = [
        obj.name
        for obj in candidate_objects
        if obj not in facial_objects
        and any(str(key).startswith("hair_") for key in obj.keys())
    ]
    imported_provider_modules = sorted(
        name
        for name in sys.modules
        if "blender_author_responsive_avatar_hair" in name
    )
    body_material_names = [
        material.name for material in body.data.materials if material is not None
    ]
    separate_scalp_slots = [
        name
        for name in body_material_names
        if any(token in name.lower() for token in ("scalp", "hair", "groom"))
    ]
    blockers = []
    for label, rows in (
        ("scalp_hair_objects", scalp_objects),
        ("scalp_hair_materials", scalp_materials),
        ("scalp_hair_images", scalp_images),
        ("scalp_hair_node_groups", scalp_node_groups),
        ("scalp_hair_controllers", controller_objects),
        ("imported_scalp_hair_provider_modules", imported_provider_modules),
        ("separate_scalp_body_material_slots", separate_scalp_slots),
    ):
        if rows:
            blockers.append(f"{label}_not_zero")
    return {
        "policy_id": policy_report["policy_id"],
        "policy_path": policy_report["path"],
        "asset_id": policy_report["asset_id"],
        "passed": not blockers,
        "blockers": blockers,
        "scalp_hair_provider_path": None,
        "scalp_hair_provider_sha256": None,
        "scalp_hair_provider_invoked": False,
        "scalp_hair_objects": scalp_objects,
        "scalp_hair_materials": scalp_materials,
        "scalp_hair_images_or_textures": scalp_images,
        "scalp_hair_node_groups": scalp_node_groups,
        "scalp_hair_controller_objects": controller_objects,
        "imported_scalp_hair_provider_modules": imported_provider_modules,
        "separate_scalp_body_material_slots": separate_scalp_slots,
        "body_material_slots": body_material_names,
        "natural_scalp_is_same_primary_skin_surface": not separate_scalp_slots,
        "black_scalp_cap_or_dome_created": False,
        "painted_scalp_hair_created": False,
        "hair_state_review_renders_created": False,
        "facial_presentation_objects_excluded_from_scalp_hair": [
            {"object": obj.name, "role": obj["facial_presentation_role"]}
            for obj in facial_objects
        ],
        "eyebrows_and_lashes_retained": any(
            obj.get("facial_presentation_role") == "brow" for obj in facial_objects
        )
        and any(
            obj.get("facial_presentation_role") == "upper_lash"
            for obj in facial_objects
        ),
        "complete_body_not_hairless_engineering_candidate": True,
    }


def _render_owner_review_views(
    *,
    scene: Any,
    output_dir: Path,
    body: Any,
    armature: Any,
    candidate_objects: Sequence[Any],
    knee_report: Mapping[str, Any],
    protected_target: Vector,
    target_height_m: float,
) -> dict[str, Any]:
    camera, lighting_report = install_shadow_controlled_review_rig_v2(
        scene, target_height_m
    )
    low, high = r15._world_bounds([body])  # noqa: SLF001
    body_target = Vector((0.0, (low.y + high.y) * 0.5, target_height_m * 0.51))
    face_target = Vector((0.0, (low.y + high.y) * 0.5, high.z - target_height_m * 0.085))
    eye_target = r15._named_center(candidate_objects, "brown_iris", face_target)  # noqa: SLF001
    knee_left = armature.matrix_world @ armature.data.bones["lowerleg01.L"].head_local
    knee_right = armature.matrix_world @ armature.data.bones["lowerleg01.R"].head_local
    knee_center = (knee_left + knee_right) * 0.5
    distance = float(target_height_m) * 3.0
    hand_left_direction = r15._named_review_normal(  # noqa: SLF001
        candidate_objects, "fingernail_3_L", Vector((0.0, -1.0, 0.0))
    ) + Vector((-0.10, 0.0, 0.30))
    hand_right_direction = r15._named_review_normal(  # noqa: SLF001
        candidate_objects, "fingernail_3_R", Vector((0.0, -1.0, 0.0))
    ) + Vector((0.10, 0.0, 0.30))
    foot_left_direction = r15._named_review_normal(  # noqa: SLF001
        candidate_objects, "toenail_1_L", Vector((0.0, -0.12, 1.0))
    ) + Vector((-0.08, -0.35, 0.0))
    foot_right_direction = r15._named_review_normal(  # noqa: SLF001
        candidate_objects, "toenail_1_R", Vector((0.0, -0.12, 1.0))
    ) + Vector((0.08, -0.35, 0.0))
    component_frames = {
        "left_hand_nails_close": component_bone_frame_v2(
            armature,
            side="L",
            kind="hand",
            view_direction=hand_left_direction,
            target_height_m=target_height_m,
        ),
        "right_hand_nails_close": component_bone_frame_v2(
            armature,
            side="R",
            kind="hand",
            view_direction=hand_right_direction,
            target_height_m=target_height_m,
        ),
        "left_foot_nails_close": component_bone_frame_v2(
            armature,
            side="L",
            kind="foot",
            view_direction=foot_left_direction,
            target_height_m=target_height_m,
        ),
        "right_foot_nails_close": component_bone_frame_v2(
            armature,
            side="R",
            kind="foot",
            view_direction=foot_right_direction,
            target_height_m=target_height_m,
        ),
    }
    directions = {
        "front": Vector((0.0, -1.0, 0.03)),
        "rear": Vector((0.0, 1.0, 0.03)),
        "left_profile": Vector((-1.0, 0.0, 0.03)),
        "right_profile": Vector((1.0, 0.0, 0.03)),
        "left_three_quarter": Vector((-0.68, -0.73, 0.03)),
        "right_three_quarter": Vector((0.68, -0.73, 0.03)),
        "face_close": Vector((0.0, -1.0, 0.01)),
        "eyes_close": Vector((0.0, -1.0, 0.01)),
        "left_hand_nails_close": Vector(component_frames["left_hand_nails_close"]["view_direction"]),
        "right_hand_nails_close": Vector(component_frames["right_hand_nails_close"]["view_direction"]),
        "left_foot_nails_close": Vector(component_frames["left_foot_nails_close"]["view_direction"]),
        "right_foot_nails_close": Vector(component_frames["right_foot_nails_close"]["view_direction"]),
        "left_knee_flexion": Vector((-0.55, -1.0, 0.10)),
        "right_knee_flexion": Vector((0.55, -1.0, 0.10)),
        "protected_adult_relationship_front": Vector((0.0, -1.0, 0.02)),
        "protected_adult_relationship_side": Vector((1.0, 0.0, 0.02)),
        "protected_adult_relationship_three_quarter": Vector((0.72, -0.70, 0.02)),
        "neutral_standing": Vector((0.0, -1.0, 0.03)),
        "crown_top_scalp": Vector((0.0, -0.10, 1.0)),
        "rear_scalp_hairline": Vector((0.0, 1.0, 0.01)),
        "bilateral_knee_flexion": Vector((0.0, -1.0, 0.08)),
        "seated_front_three_quarter": Vector((0.68, -1.0, 0.07)),
        "seated_side_contact": Vector((1.0, 0.0, 0.035)),
    }
    targets = {
        "face_close": face_target,
        "eyes_close": eye_target,
        "left_hand_nails_close": Vector(component_frames["left_hand_nails_close"]["target"]),
        "right_hand_nails_close": Vector(component_frames["right_hand_nails_close"]["target"]),
        "left_foot_nails_close": Vector(component_frames["left_foot_nails_close"]["target"]),
        "right_foot_nails_close": Vector(component_frames["right_foot_nails_close"]["target"]),
        "left_knee_flexion": knee_left,
        "right_knee_flexion": knee_right,
        "protected_adult_relationship_front": protected_target,
        "protected_adult_relationship_side": protected_target,
        "protected_adult_relationship_three_quarter": protected_target,
        "crown_top_scalp": Vector((0.0, (low.y + high.y) * 0.5, high.z - target_height_m * 0.08)),
        "rear_scalp_hairline": face_target,
        "bilateral_knee_flexion": knee_center,
        "seated_front_three_quarter": Vector((0.0, 0.0, target_height_m * 0.43)),
        "seated_side_contact": Vector((0.0, 0.0, target_height_m * 0.40)),
    }
    scales = {
        "face_close": target_height_m * 0.33,
        "eyes_close": target_height_m * 0.13,
        "left_hand_nails_close": component_frames["left_hand_nails_close"]["ortho_scale_m"],
        "right_hand_nails_close": component_frames["right_hand_nails_close"]["ortho_scale_m"],
        "left_foot_nails_close": component_frames["left_foot_nails_close"]["ortho_scale_m"],
        "right_foot_nails_close": component_frames["right_foot_nails_close"]["ortho_scale_m"],
        "left_knee_flexion": target_height_m * 0.43,
        "right_knee_flexion": target_height_m * 0.43,
        "protected_adult_relationship_front": target_height_m * 0.29,
        "protected_adult_relationship_side": target_height_m * 0.29,
        "protected_adult_relationship_three_quarter": target_height_m * 0.29,
        "crown_top_scalp": target_height_m * 0.36,
        "rear_scalp_hairline": target_height_m * 0.36,
        "bilateral_knee_flexion": target_height_m * 0.62,
        "seated_front_three_quarter": target_height_m * 0.98,
        "seated_side_contact": target_height_m * 0.98,
    }
    seat = _add_private_seat_prop(target_height_m)
    rendered: list[dict[str, Any]] = []
    relaxed_hands: list[dict[str, Any]] = []
    seated_pose_reports: list[dict[str, Any]] = []
    for label in REQUIRED_REVIEW_VIEW_LABELS:
        reset_pose(armature)
        seat.hide_render = True
        if label == "left_knee_flexion":
            apply_knee_solution(armature, knee_report["solutions"]["left"])
        elif label == "right_knee_flexion":
            apply_knee_solution(armature, knee_report["solutions"]["right"])
        elif label == "bilateral_knee_flexion":
            _apply_bilateral_knee_pose(armature, knee_report)
        elif label == "left_hand_nails_close":
            relaxed_hands.append(
                apply_relaxed_hand_pose(armature, "L", target_height_m=target_height_m)
            )
        elif label == "right_hand_nails_close":
            relaxed_hands.append(
                apply_relaxed_hand_pose(armature, "R", target_height_m=target_height_m)
            )
        elif label in {"seated_front_three_quarter", "seated_side_contact"}:
            seated_pose_reports.append(
                _apply_seated_pose(armature, knee_report, target_height_m)
            )
            seat.hide_render = False
        target = targets.get(label, body_target)
        direction = directions[label].normalized()
        camera.location = target + direction * distance
        r15._look_at(camera, target)  # noqa: SLF001
        camera.data.ortho_scale = float(scales.get(label, target_height_m * 1.12))
        if label in {
            "front",
            "rear",
            "left_profile",
            "right_profile",
            "left_three_quarter",
            "right_three_quarter",
            "neutral_standing",
            "seated_front_three_quarter",
            "seated_side_contact",
        }:
            scene.render.resolution_x = 900
            scene.render.resolution_y = 1100
        else:
            scene.render.resolution_x = 900
            scene.render.resolution_y = 900
        path = output_dir / f"{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        seat.hide_render = True
        rendered.append(
            {
                "label": label,
                "path": path.name,
                "sha256": sha256_file(path),
                "protected_view": label.startswith("protected_adult_relationship_"),
                "scalp_review_view": label in {"crown_top_scalp", "rear_scalp_hairline"},
                "pose_view": label
                in {
                    "left_knee_flexion",
                    "right_knee_flexion",
                    "bilateral_knee_flexion",
                    "seated_front_three_quarter",
                    "seated_side_contact",
                },
            }
        )
    reset_pose(armature)
    seat.hide_render = True
    labels = tuple(row["label"] for row in rendered)
    if labels != REQUIRED_REVIEW_VIEW_LABELS or len(set(labels)) != len(labels):
        raise KiraBaldDeliveryBuildError("rendered review label set/order drifted")
    return {
        "render_performed": True,
        "view_count": len(rendered),
        "exact_required_labels": list(REQUIRED_REVIEW_VIEW_LABELS),
        "views": rendered,
        "supplemental_hair_response_view_count": 0,
        "hair_state_review_renders_created": False,
        "bald_scalp_review_views": ["crown_top_scalp", "rear_scalp_hairline"],
        "neutral_review_lighting": lighting_report,
        "component_bone_frames": component_frames,
        "relaxed_hand_poses": relaxed_hands,
        "seated_pose_reports": seated_pose_reports,
        "seated_contact_claimed": False,
        "private_seat_review_prop": seat.name,
        "private_owner_review_only": True,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    if args.acknowledge_inactive_private_candidate is not True:
        raise KiraBaldDeliveryBuildError(
            "--acknowledge-inactive-private-candidate is required"
        )
    if args.render_owner_review is not True:
        raise KiraBaldDeliveryBuildError(
            "--render-owner-review is required for a delivery candidate"
        )
    policy, policy_report = _validate_delivery_policy()
    output_relative = Path(args.output_dir)
    preflight = evaluate_profiled_candidate_preflight(PROJECT_ROOT, output_relative)
    if preflight["ready"] is not True:
        raise ProfiledAdultCandidateContractError(
            "candidate preflight blocked: " + "; ".join(preflight["blockers"])
        )
    config, config_report = load_validated_profiled_candidate_builder_config(PROJECT_ROOT)
    profile_path = PROJECT_ROOT / config["style_profile"]["path"]
    if sha256_file(profile_path) != config["style_profile"]["sha256"]:
        raise KiraBaldDeliveryBuildError("style profile changed after preflight")
    profile = _read_json(profile_path)
    target_height_m = float(profile["dimensions"]["target_height_m"])
    candidate_id = output_relative.name
    output_dir = PROJECT_ROOT / output_relative
    if output_dir.exists():
        raise KiraBaldDeliveryBuildError("output appeared after preflight")
    snapshot = _capture_delivery_hash_snapshot(
        config=config,
        config_report=config_report,
        profile=profile,
        preflight=preflight,
    )
    r15._assert_background_factory_startup_safe_scene()  # noqa: SLF001
    r15._clear_scene_after_preflight()  # noqa: SLF001
    scene = bpy.context.scene
    base_path = PROJECT_ROOT / config["makehuman_source_set"]["base_body"]["path"]
    r15._assert_exact_bound_file(  # noqa: SLF001
        base_path,
        config["makehuman_source_set"]["base_body"]["sha256"],
        "official base body before source construction",
    )
    source = prepare_profiled_body_source(
        base_path=base_path,
        female_macros=config["makehuman_source_set"]["female_macros"],
        resolved_style_targets=preflight["style_profile"]["resolved_targets"],
        project_root=PROJECT_ROOT,
        target_height_m=target_height_m,
    )
    expected_style_order = [row["target_id"] for row in profile["shape_targets"]]
    if (
        source["style_target_ids_in_application_order"] != expected_style_order
        or source["style_target_count"] != 12
    ):
        raise KiraBaldDeliveryBuildError("exact style target order/count drifted")
    skin_material, base_skin_report = build_warm_skin_material(profile)
    body = build_body_object(source, candidate_id, skin_material)
    face_boundary_path = PROJECT_ROOT / BOUNDED_FACE_RESULT_PATH
    face_boundary = _read_json(face_boundary_path)
    if (
        face_boundary.get("bounded_attempts_consumed") != 2
        or face_boundary.get("status")
        != "NO_KIRA_SPECIFIC_FACE_REPAIR_PASSED_ALL_HARD_GATES"
    ):
        raise KiraBaldDeliveryBuildError("bounded face fallback record drifted")
    face_report = {
        "method": "preserved_profiled_source_face_after_two_bounded_v2_failures",
        "geometry_delta_applied": False,
        "bounded_result_path": BOUNDED_FACE_RESULT_PATH.as_posix(),
        "bounded_result_sha256": sha256_file(face_boundary_path),
        "bounded_attempts_consumed": 2,
        "known_visible_defect": (
            "face remains generic and is not yet a successful Kira-specific likeness"
        ),
        "owner_visual_decision_required": True,
        "identity_match_claim_allowed": False,
    }
    source_sync_report = {
        "required": False,
        "performed": False,
        "reason": "no failed v2 face delta was applied to the preserved source face",
    }
    skin_calibration_report = calibrate_warm_non_pale_skin_v2(body)

    skeleton_path = PROJECT_ROOT / config["official_rig"]["skeleton"]["path"]
    weights_path = PROJECT_ROOT / config["official_rig"]["weights"]["path"]
    r15._assert_exact_bound_file(  # noqa: SLF001
        skeleton_path,
        config["official_rig"]["skeleton"]["sha256"],
        "official skeleton before rig construction",
    )
    r15._assert_exact_bound_file(  # noqa: SLF001
        weights_path,
        config["official_rig"]["weights"]["sha256"],
        "official weights before rig construction",
    )
    armature, rig_report = build_official_rig_and_normalized_weights(
        body=body,
        source=source,
        skeleton_path=skeleton_path,
        weights_path=weights_path,
        candidate_id=candidate_id,
        maximum_influences=4,
    )
    cleanup_report = repair_bounded_self_intersections(body)
    if int(
        cleanup_report.get("after", {}).get(
            "exact_genuine_penetration_pair_count", -1
        )
    ) != 0:
        raise KiraBaldDeliveryBuildError("bounded source cleanup did not reach zero")
    adult_surface_report, protected_target = _author_delivery_adult_surface(
        body=body,
        config=config,
        target_height_m=target_height_m,
    )
    retained_landmarks = sorted(
        group.name
        for group in body.vertex_groups
        if group.name.startswith(LANDMARK_GROUP_PREFIX)
    )
    if not retained_landmarks:
        raise KiraBaldDeliveryBuildError("adult landmark groups missing after delivery surface")
    lip_report = {
        "applied": False,
        "reason": (
            "the bounded v2 face direction failed; its target-derived lip index set "
            "was not reused independently"
        ),
    }
    r15._assert_exact_bound_file(  # noqa: SLF001
        base_path,
        config["makehuman_source_set"]["base_body"]["sha256"],
        "official base body before helper-eye construction",
    )
    eye_objects, eye_report = add_natural_helper_eyes(
        base_path=base_path,
        source=source,
        body=body,
        armature=armature,
        eye_profile=profile["eye_profile"],
        candidate_id=candidate_id,
    )
    facial_objects, facial_report = add_feminine_eye_surrounds_v2(
        body=body,
        armature=armature,
        eye_objects=eye_objects,
        candidate_id=candidate_id,
    )
    nail_objects, nail_report = add_natural_nails(
        body=body,
        armature=armature,
        target_height_m=target_height_m,
        candidate_id=candidate_id,
    )
    nail_boundary_path = PROJECT_ROOT / BOUNDED_NAIL_RESULT_PATH
    nail_boundary = _read_json(nail_boundary_path)
    if (
        nail_boundary.get("bounded_attempts_consumed") != 2
        or nail_boundary.get("status")
        != "NO_ROUNDED_SILHOUETTE_REPAIR_PASSED_BODY_FIT_GATE"
    ):
        raise KiraBaldDeliveryBuildError("bounded nail fallback record drifted")
    rounded_nail_report = {
        "applied": False,
        "fallback": "preserved_v1_conformal_nails",
        "nail_count": len(nail_objects),
        "bounded_result_path": BOUNDED_NAIL_RESULT_PATH.as_posix(),
        "bounded_result_sha256": sha256_file(nail_boundary_path),
        "bounded_attempts_consumed": 2,
        "known_visible_defect": (
            "fingernail and toenail silhouettes may remain visibly square rather "
            "than naturally rounded"
        ),
        "owner_visual_decision_required": True,
    }
    knee_corrective_report = install_knee_corrective_smoothing_v2(
        body, armature, target_height_m
    )
    knee_report = solve_bilateral_knee_axes_and_actions(armature, body)
    if (
        knee_report.get("skeleton_kinematic_objective_pass") is not True
        or knee_report.get("knee_mesh_deformation_quality_proven") is not True
    ):
        raise KiraBaldDeliveryBuildError("bilateral knee engineering gate failed")

    candidate_objects = [
        body,
        armature,
        *eye_objects,
        *facial_objects,
        *nail_objects,
    ]
    r15._mark_inactive_private(candidate_objects, scene, candidate_id)  # noqa: SLF001
    scene["candidate_author_id"] = "profiled_kira_bald_delivery_candidate_v1"
    scene["candidate_asset_id"] = "KIRA_BALD_LOW_RESOURCE_BODY"
    scene["complete_natural_bald_scalp"] = True
    scene["scalp_hair_dependency_allowed"] = False
    body["candidate_asset_id"] = "KIRA_BALD_LOW_RESOURCE_BODY"
    body["complete_natural_bald_scalp"] = True
    body["scalp_hair_dependency_allowed"] = False
    topology = r15._mesh_topology_counts(body)  # noqa: SLF001
    if (
        topology["surface_components"] != 1
        or topology["boundary_edges"] != 0
        or topology["nonmanifold_edges"] != 0
    ):
        raise KiraBaldDeliveryBuildError("final primary body surface is not one closed manifold")
    zero_hair = _zero_scalp_hair_inventory(
        body=body,
        candidate_objects=candidate_objects,
        policy_report=policy_report,
    )
    if zero_hair["passed"] is not True:
        raise KiraBaldDeliveryBuildError(
            "zero scalp-hair dependency gate failed: " + "; ".join(zero_hair["blockers"])
        )
    live_before_output = verify_live_kira_state_unchanged(
        PROJECT_ROOT, preflight["live_kira_state_before"]
    )
    if live_before_output["passed"] is not True:
        raise KiraBaldDeliveryBuildError("live Kira state changed during build")
    hashes_before_output = r15._verify_build_hash_snapshot(snapshot)  # noqa: SLF001
    if hashes_before_output["passed"] is not True:
        raise KiraBaldDeliveryBuildError(
            "delivery binding changed before output: "
            + "; ".join(hashes_before_output["blockers"])
        )

    output_dir.mkdir(parents=False, exist_ok=False)
    render_report = _render_owner_review_views(
        scene=scene,
        output_dir=output_dir,
        body=body,
        armature=armature,
        candidate_objects=candidate_objects,
        knee_report=knee_report,
        protected_target=protected_target,
        target_height_m=target_height_m,
    )
    reset_pose(armature)
    blend_path = output_dir / f"{candidate_id}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    blend_record = {"path": blend_path.name, "sha256": sha256_file(blend_path)}
    live_after = verify_live_kira_state_unchanged(
        PROJECT_ROOT, preflight["live_kira_state_before"]
    )
    hashes_at_commit = r15._verify_build_hash_snapshot(snapshot)  # noqa: SLF001
    if live_after["passed"] is not True or hashes_at_commit["passed"] is not True:
        raise KiraBaldDeliveryBuildError(
            "live state or exact delivery binding changed before evidence commit"
        )
    evidence = {
        "schema_version": 1,
        "evidence_type": "inactive_complete_kira_bald_delivery_candidate_v1",
        "candidate_id": candidate_id,
        "candidate_asset_id": "KIRA_BALD_LOW_RESOURCE_BODY",
        "status": "INACTIVE_PRIVATE_COMPLETE_BODY_AWAITING_OWNER_VISUAL_DECISION",
        "delivery_policy": policy_report,
        "complete_body_boundary": {
            "complete_body": True,
            "bald_low_resource_body": True,
            "hairless_engineering_candidate": False,
            "natural_scalp_is_primary_skin_surface": True,
            "face_head_body_hands_feet_nails_eyes_brows_lashes_lids_present": True,
            "adult_surface_relationships_present_on_one_primary_surface": True,
            "minor_visible_refinements_may_be_owner_directed_after_review": True,
        },
        "preflight": preflight,
        "builder_config": config_report,
        "source": {
            key: value
            for key, value in source.items()
            if key
            not in {
                "source_vertices_after_all_targets",
                "body_vertices",
                "body_faces",
                "source_to_body",
            }
        },
        "application_order": [
            "official_base_body_group",
            "official_female_macros",
            "validator_resolved_style_targets_as_listed",
            "uniform_scale_to_1.651m",
            "preserved_profiled_source_face_after_two_bounded_v2_failures",
            "no_failed_face_delta_synchronized_into_source",
            "warm_non_pale_skin_calibration_v2",
            "official_rig_and_normalized_weights",
            "bounded_exact_source_cleanup",
            "continuous_adult_surface_v1_then_v2_then_checkpointed_v3_fallback",
            "preserved_primary_skin_lip_presentation_after_bounded_face_failure",
            "natural_helper_eyes_then_brows_lashes_lids_v2",
            "preserved_v1_conformal_nails_after_two_bounded_rounding_failures",
            "localized_knee_corrective_smoothing_before_axis_solver",
            "zero_scalp_hair_dependency_gate",
            "exact_23_view_private_owner_review_render",
        ],
        "appearance": {
            "face": face_report,
            "source_synchronization": source_sync_report,
            "skin": {
                "base_profile_material": base_skin_report,
                "warm_non_pale_calibration_v2": skin_calibration_report,
            },
            "natural_lip_material": lip_report,
            "eyes": eye_report,
            "eye_surrounds": facial_report,
            "nails": nail_report,
            "rounded_nails": rounded_nail_report,
        },
        "rig": rig_report,
        "bounded_source_cleanup": cleanup_report,
        "adult_surface_authoring": adult_surface_report,
        "known_unresolved_visible_defects": [
            {
                "component": "Kira-specific face appearance",
                "defect": (
                    "the safe profiled source face remains generic and is not yet a "
                    "successful Kira-specific facial likeness"
                ),
                "bounded_repairs_consumed": 2,
                "owner_decision_required": True,
            },
            {
                "component": "localized external adult anatomy presentation",
                "defect": (
                    "rectangular or plate-like transition with schematic parallel "
                    "ridges instead of naturally blended folds"
                ),
                "structural_state": (
                    "one closed weighted primary surface with zero new global "
                    "nonadjacent self-intersection pairs"
                ),
                "bounded_repairs_consumed": 2,
                "owner_decision_required": True,
            },
            {
                "component": "fingernail and toenail silhouettes",
                "defect": (
                    "the safe conformal nails may remain visibly square rather than "
                    "naturally rounded"
                ),
                "bounded_repairs_consumed": 2,
                "owner_decision_required": True,
            }
        ],
        "retained_adult_landmark_groups": retained_landmarks,
        "knees": {
            "axis_solver": knee_report,
            "corrective_smoothing_v2": knee_corrective_report,
        },
        "zero_scalp_hair_dependency": zero_hair,
        "final_primary_surface_topology": topology,
        "owner_review": render_report,
        "outputs": {
            "blend": blend_record,
            "private_glb": {
                "exported": False,
                "status": "GLB_EXPORT_NOT_IMPLEMENTED_BY_BALD_DELIVERY_BUILDER",
            },
        },
        "protected_live_kira_state": live_after,
        "build_hash_bindings": {
            "snapshot": snapshot,
            "verified_before_output_creation": hashes_before_output,
            "verified_at_evidence_commit": hashes_at_commit,
        },
        "safety": {
            "private_owner_review_only": True,
            "inactive": True,
            "assigned": False,
            "clothing_included": False,
            "publication_allowed": False,
            "runtime_activation_allowed": False,
            "live_kira_state_mutated": False,
            "glb_exported": False,
            "scalp_hair_instantiated": False,
            "body_activation_or_replacement_performed": False,
        },
        "build_elapsed_seconds": time.perf_counter() - started,
    }
    evidence_path = output_dir / "BUILD_EVIDENCE.json"
    evidence_path.write_text(
        json.dumps(r15._json_safe(evidence), indent=2, sort_keys=True) + "\n",  # noqa: SLF001
        encoding="utf-8",
    )
    return {
        "status": evidence["status"],
        "candidate_id": candidate_id,
        "candidate_asset_id": evidence["candidate_asset_id"],
        "output_directory": output_relative.as_posix(),
        "blend": blend_record,
        "render_count": render_report["view_count"],
        "evidence_path": evidence_path.relative_to(PROJECT_ROOT).as_posix(),
        "evidence_sha256": sha256_file(evidence_path),
        "runtime_activation_allowed": False,
        "live_kira_state_mutated": False,
        "scalp_hair_dependency_count": 0,
    }


def main() -> int:
    try:
        result = build(_arguments())
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "BLOCKED_OR_FAILED_WITHOUT_ACTIVATION",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "runtime_activation_allowed": False,
                    "live_kira_state_mutation_intended": False,
                    "scalp_hair_instantiation_intended": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        raise
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
