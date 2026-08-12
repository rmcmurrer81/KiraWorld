"""Blender adapter for the versioned human pose/clearance contract.

This adapter edits only pose transforms on an already-built armature.  It does
not create a body, register or activate an avatar, save a blend, export an
asset, or author animation.  Callers remain responsible for private visual and
mesh-collision review before using any resulting pose.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

import bpy
from mathutils import Matrix, Quaternion, Vector

from Core.avatar_human_pose_clearance_v1 import (
    METHOD_ID,
    build_pose_plan,
    segment_segment_distance,
    solve_support_contact_translation,
)


class AvatarHumanPoseClearanceBlenderError(RuntimeError):
    """Raised when a rig or evaluated body cannot satisfy the fail-closed gate."""


def reset_pose_v1(armature: Any) -> None:
    """Restore exact basis transforms without assuming any rotation mode."""

    if getattr(armature, "type", None) != "ARMATURE":
        raise AvatarHumanPoseClearanceBlenderError("an armature object is required")
    for pose_bone in armature.pose.bones:
        pose_bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def _require_pose_bone(armature: Any, name: str) -> Any:
    pose_bone = armature.pose.bones.get(name)
    if pose_bone is None:
        raise AvatarHumanPoseClearanceBlenderError(f"required pose bone missing: {name}")
    return pose_bone


def _world_from_armature_point(armature: Any, point: Sequence[float]) -> Vector:
    return armature.matrix_world @ Vector(tuple(float(item) for item in point))


def _armature_from_world_point(armature: Any, point: Sequence[float]) -> Vector:
    return armature.matrix_world.inverted() @ Vector(tuple(float(item) for item in point))


def _aim_pose_bone_at_world_point(
    armature: Any, bone_name: str, target_world: Sequence[float]
) -> dict[str, Any]:
    """Aim a pose bone by measured current direction, never a guessed Euler axis."""

    pose_bone = _require_pose_bone(armature, bone_name)
    target_armature = _armature_from_world_point(armature, target_world)
    current_direction = pose_bone.tail - pose_bone.head
    desired_direction = target_armature - pose_bone.head
    if current_direction.length <= 1.0e-8 or desired_direction.length <= 1.0e-8:
        raise AvatarHumanPoseClearanceBlenderError(
            f"degenerate aim direction for pose bone: {bone_name}"
        )
    rotation = current_direction.normalized().rotation_difference(
        desired_direction.normalized()
    )
    pivot = pose_bone.head.copy()
    rotated_matrix = (
        Matrix.Translation(pivot)
        @ rotation.to_matrix().to_4x4()
        @ Matrix.Translation(-pivot)
        @ pose_bone.matrix
    )
    pose_bone.matrix = rotated_matrix
    bpy.context.view_layer.update()
    final_direction = (pose_bone.tail - pose_bone.head).normalized()
    angular_error = final_direction.angle(desired_direction.normalized())
    return {
        "bone": bone_name,
        "target_world_m": list(map(float, target_world)),
        "angular_error_radians": float(angular_error),
        "assumed_euler_axis_used": False,
    }


def _rotate_pose_bone_in_world(
    armature: Any, bone_name: str, axis_world: Sequence[float], angle_radians: float
) -> None:
    pose_bone = _require_pose_bone(armature, bone_name)
    axis_armature = armature.matrix_world.inverted().to_3x3() @ Vector(axis_world)
    if axis_armature.length <= 1.0e-8:
        raise AvatarHumanPoseClearanceBlenderError("world rotation axis is degenerate")
    rotation = Quaternion(axis_armature.normalized(), float(angle_radians))
    pivot = pose_bone.head.copy()
    pose_bone.matrix = (
        Matrix.Translation(pivot)
        @ rotation.to_matrix().to_4x4()
        @ Matrix.Translation(-pivot)
        @ pose_bone.matrix
    )
    bpy.context.view_layer.update()


def _chain_target(
    origin_world: Vector, requested_world: Vector, chain_length_m: float
) -> Vector:
    direction = requested_world - origin_world
    if direction.length <= 1.0e-8:
        raise AvatarHumanPoseClearanceBlenderError("joint chain target is degenerate")
    return origin_world + direction.normalized() * float(chain_length_m)


def _hip_origin_world(armature: Any) -> Vector:
    left = _world_from_armature_point(
        armature, _require_pose_bone(armature, "upperleg01.L").head
    )
    right = _world_from_armature_point(
        armature, _require_pose_bone(armature, "upperleg01.R").head
    )
    return (left + right) * 0.5


def _target_world(
    hip_origin_world: Vector, plan: Mapping[str, Any], joint_name: str
) -> Vector:
    raw = dict(plan["joint_targets_m"])[joint_name]
    return hip_origin_world + Vector(tuple(float(item) for item in raw))


def _aim_two_part_chain(
    *,
    armature: Any,
    first_bone: str,
    second_bone: str,
    requested_end_world: Vector,
) -> list[dict[str, Any]]:
    first = _require_pose_bone(armature, first_bone)
    second = _require_pose_bone(armature, second_bone)
    origin_world = _world_from_armature_point(armature, first.head)
    first_length_world = (
        _world_from_armature_point(armature, first.tail) - origin_world
    ).length
    second_length_world = (
        _world_from_armature_point(armature, second.tail)
        - _world_from_armature_point(armature, second.head)
    ).length
    chain_length = float(first_length_world + second_length_world)
    actual_end_world = _chain_target(origin_world, requested_end_world, chain_length)
    reports = [
        _aim_pose_bone_at_world_point(armature, first_bone, actual_end_world),
        _aim_pose_bone_at_world_point(armature, second_bone, actual_end_world),
    ]
    return reports


def _apply_leg_targets(
    armature: Any, plan: Mapping[str, Any], hip_origin_world: Vector
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for side in ("L", "R"):
        requested_knee = _target_world(hip_origin_world, plan, f"knee.{side}")
        reports.extend(
            _aim_two_part_chain(
                armature=armature,
                first_bone=f"upperleg01.{side}",
                second_bone=f"upperleg02.{side}",
                requested_end_world=requested_knee,
            )
        )
        actual_knee = _world_from_armature_point(
            armature, _require_pose_bone(armature, f"lowerleg01.{side}").head
        )
        requested_ankle = _target_world(hip_origin_world, plan, f"ankle.{side}")
        calf_direction_target = actual_knee + (requested_ankle - requested_knee)
        reports.extend(
            _aim_two_part_chain(
                armature=armature,
                first_bone=f"lowerleg01.{side}",
                second_bone=f"lowerleg02.{side}",
                requested_end_world=calf_direction_target,
            )
        )
        actual_ankle = _world_from_armature_point(
            armature, _require_pose_bone(armature, f"foot.{side}").head
        )
        requested_toe = _target_world(hip_origin_world, plan, f"toe.{side}")
        toe_direction = requested_toe - requested_ankle
        reports.append(
            _aim_pose_bone_at_world_point(
                armature, f"foot.{side}", actual_ankle + toe_direction
            )
        )
    return reports


def _apply_eating_ready_arm_targets(
    armature: Any, plan: Mapping[str, Any], hip_origin_world: Vector
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for side in ("L", "R"):
        requested_elbow = _target_world(hip_origin_world, plan, f"elbow.{side}")
        reports.extend(
            _aim_two_part_chain(
                armature=armature,
                first_bone=f"upperarm01.{side}",
                second_bone=f"upperarm02.{side}",
                requested_end_world=requested_elbow,
            )
        )
        actual_elbow = _world_from_armature_point(
            armature, _require_pose_bone(armature, f"lowerarm01.{side}").head
        )
        requested_wrist = _target_world(hip_origin_world, plan, f"wrist.{side}")
        lower_direction_target = actual_elbow + (requested_wrist - requested_elbow)
        reports.extend(
            _aim_two_part_chain(
                armature=armature,
                first_bone=f"lowerarm01.{side}",
                second_bone=f"lowerarm02.{side}",
                requested_end_world=lower_direction_target,
            )
        )
    # A slight measured world-axis lean creates an eating-ready torso without
    # inventing a food prop or claiming an eating animation.
    _rotate_pose_bone_in_world(armature, "spine05", (1.0, 0.0, 0.0), 0.105)
    return reports


def _body_world_bounds(body: Any) -> tuple[Vector, Vector]:
    points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    if not points:
        raise AvatarHumanPoseClearanceBlenderError("body mesh has no vertices")
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def _vertex_weight_total(body: Any, vertex: Any, group_names: Iterable[str]) -> float:
    group_indices = {
        body.vertex_groups[name].index
        for name in group_names
        if body.vertex_groups.get(name) is not None
    }
    return sum(
        float(item.weight) for item in vertex.groups if item.group in group_indices
    )


def _support_vertex_indices(
    *, body: Any, armature: Any, body_height_m: float, support_kind: str
) -> tuple[list[int], dict[str, Any]]:
    low, high = _body_world_bounds(body)
    hip = _hip_origin_world(armature)
    height = float(body_height_m)
    selected: list[int] = []
    for vertex in body.data.vertices:
        point = body.matrix_world @ vertex.co
        if support_kind == "buttocks":
            coordinate_match = (
                0.018 * height <= abs(point.x - hip.x) <= 0.175 * height
                and hip.y + 0.012 * height <= point.y <= hip.y + 0.170 * height
                and hip.z - 0.155 * height <= point.z <= hip.z + 0.035 * height
            )
            weighted = _vertex_weight_total(
                body,
                vertex,
                (
                    "pelvis.L",
                    "pelvis.R",
                    "upperleg01.L",
                    "upperleg01.R",
                    "upperleg02.L",
                    "upperleg02.R",
                ),
            )
        elif support_kind == "back":
            coordinate_match = (
                abs(point.x - hip.x) <= 0.220 * height
                and hip.y + 0.010 * height <= point.y <= hip.y + 0.155 * height
                and hip.z - 0.015 * height <= point.z <= high.z - 0.070 * height
            )
            weighted = _vertex_weight_total(
                body,
                vertex,
                ("spine01", "spine02", "spine03", "spine04", "spine05"),
            )
        else:
            raise AvatarHumanPoseClearanceBlenderError(
                f"unknown support selection kind: {support_kind}"
            )
        if coordinate_match and weighted >= 0.15:
            selected.append(int(vertex.index))
    if len(selected) < 12:
        raise AvatarHumanPoseClearanceBlenderError(
            f"too few weighted {support_kind} support vertices: {len(selected)}"
        )
    return selected, {
        "support_kind": support_kind,
        "selected_rest_vertex_count": len(selected),
        "selection_is_weight_and_anatomical_region_bounded": True,
        "whole-body-lowest-point_shortcut_used": False,
        "rest_body_world_bounds_m": {"minimum": list(low), "maximum": list(high)},
    }


def _evaluated_vertex_world_points(body: Any, indices: Sequence[int]) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    try:
        if max(indices, default=-1) >= len(mesh.vertices):
            raise AvatarHumanPoseClearanceBlenderError(
                "evaluated topology changed before support-contact measurement"
            )
        return [evaluated.matrix_world @ mesh.vertices[int(index)].co for index in indices]
    finally:
        evaluated.to_mesh_clear()


def _translate_root_world_z(armature: Any, delta_z_m: float) -> None:
    root = _require_pose_bone(armature, "root")
    delta_armature = armature.matrix_world.inverted().to_3x3() @ Vector(
        (0.0, 0.0, float(delta_z_m))
    )
    matrix = root.matrix.copy()
    matrix.translation += delta_armature
    root.matrix = matrix
    bpy.context.view_layer.update()


def _solve_and_apply_support_contact(
    *,
    body: Any,
    armature: Any,
    support_indices: Sequence[int],
    support_plane_z_m: float,
    body_height_m: float,
    clearance_m: float = 0.001,
    maximum_translation_height_fraction: float = 0.30,
) -> dict[str, Any]:
    before_points = _evaluated_vertex_world_points(body, support_indices)
    measured_before = min(float(point.z) for point in before_points)
    solution = solve_support_contact_translation(
        measured_support_z_m=measured_before,
        support_plane_z_m=float(support_plane_z_m),
        clearance_m=float(clearance_m),
        body_height_m=float(body_height_m),
        maximum_translation_height_fraction=float(
            maximum_translation_height_fraction
        ),
    )
    _translate_root_world_z(armature, solution["world_vertical_translation_m"])
    after_points = _evaluated_vertex_world_points(body, support_indices)
    measured_after = min(float(point.z) for point in after_points)
    residual = measured_after - float(solution["target_support_z_m"])
    if abs(residual) > 0.002:
        raise AvatarHumanPoseClearanceBlenderError(
            f"world-space support contact residual exceeded 2 mm: {residual}"
        )
    return {
        **solution,
        "measured_support_z_after_m": measured_after,
        "contact_residual_m": residual,
        "contact_residual_within_2mm": True,
        "root_translation_applied_in_world_vertical": True,
        "root_bone_local_location_shortcut_used": False,
    }


def _evaluated_leg_capsule_clearance(
    armature: Any, body_height_m: float
) -> dict[str, Any]:
    height = float(body_height_m)

    def point(name: str, endpoint: str) -> Vector:
        pose_bone = _require_pose_bone(armature, name)
        return _world_from_armature_point(armature, getattr(pose_bone, endpoint))

    thigh_left = (
        point("upperleg01.L", "head"),
        point("lowerleg01.L", "head"),
    )
    thigh_right = (
        point("upperleg01.R", "head"),
        point("lowerleg01.R", "head"),
    )
    thigh_left = (thigh_left[0].lerp(thigh_left[1], 0.24), thigh_left[1])
    thigh_right = (thigh_right[0].lerp(thigh_right[1], 0.24), thigh_right[1])
    calf_left = (point("lowerleg01.L", "head"), point("foot.L", "head"))
    calf_right = (point("lowerleg01.R", "head"), point("foot.R", "head"))
    thigh_radius = 0.032 * height
    calf_radius = 0.026 * height
    rows = []
    for first_name, first, second_name, second, radius in (
        ("thigh.L", thigh_left, "thigh.R", thigh_right, thigh_radius * 2.0),
        ("thigh.L", thigh_left, "calf.R", calf_right, thigh_radius + calf_radius),
        ("calf.L", calf_left, "thigh.R", thigh_right, calf_radius + thigh_radius),
        ("calf.L", calf_left, "calf.R", calf_right, calf_radius * 2.0),
    ):
        centerline = segment_segment_distance(first[0], first[1], second[0], second[1])
        rows.append(
            {
                "first": first_name,
                "second": second_name,
                "centerline_distance_m": centerline,
                "conservative_radius_sum_m": radius,
                "capsule_surface_clearance_m": centerline - radius,
            }
        )
    minimum = min(row["capsule_surface_clearance_m"] for row in rows)
    required = 0.006 * height
    if minimum < required:
        raise AvatarHumanPoseClearanceBlenderError(
            "evaluated bilateral leg centerlines cross or lack conservative clearance"
        )
    return {
        "passed": True,
        "minimum_capsule_surface_clearance_m": minimum,
        "required_capsule_surface_clearance_m": required,
        "pairs": rows,
        "mesh_self_intersection_audit_still_required": True,
    }


def apply_pose_foundation_v1(
    *,
    armature: Any,
    body: Any,
    pose_name: str,
    body_height_m: float,
    seat_top_z_m: float | None = None,
    support_plane_z_m: float | None = None,
) -> dict[str, Any]:
    """Apply one bounded static pose foundation to an existing inactive body."""

    if getattr(body, "type", None) != "MESH":
        raise AvatarHumanPoseClearanceBlenderError("a primary body mesh is required")
    plan = build_pose_plan(
        pose_name,
        body_height_m=float(body_height_m),
        seat_top_z_m=seat_top_z_m,
        support_plane_z_m=support_plane_z_m,
    )
    reset_pose_v1(armature)
    if pose_name == "neutral":
        return {
            "method_id": METHOD_ID,
            "pose_name": "neutral",
            "rest_pose_restored": True,
            "runtime_activation_allowed": False,
            "visual_review_required": True,
        }

    support_kind = "back" if pose_name == "lying_supine" else "buttocks"
    support_indices, selection_report = _support_vertex_indices(
        body=body,
        armature=armature,
        body_height_m=float(body_height_m),
        support_kind=support_kind,
    )
    if pose_name == "lying_supine":
        # Upright +Z becomes headward +Y and anatomical front -Y becomes +Z.
        _rotate_pose_bone_in_world(armature, "root", (1.0, 0.0, 0.0), -1.5707963267948966)
    hip_origin = _hip_origin_world(armature)
    aim_reports = _apply_leg_targets(armature, plan, hip_origin)
    if pose_name == "eating_ready":
        aim_reports.extend(_apply_eating_ready_arm_targets(armature, plan, hip_origin))

    clearance = _evaluated_leg_capsule_clearance(armature, float(body_height_m))
    plane = support_plane_z_m if pose_name == "lying_supine" else seat_top_z_m
    if plane is None:
        raise AvatarHumanPoseClearanceBlenderError("support plane unexpectedly missing")
    contact = _solve_and_apply_support_contact(
        body=body,
        armature=armature,
        support_indices=support_indices,
        support_plane_z_m=float(plane),
        body_height_m=float(body_height_m),
        maximum_translation_height_fraction=(
            0.55 if pose_name == "lying_supine" else 0.30
        ),
    )
    return {
        "method_id": METHOD_ID,
        "pose_name": pose_name,
        "plan": plan,
        "bone_aim_reports": aim_reports,
        "support_selection": selection_report,
        "support_contact": contact,
        "bilateral_leg_clearance": clearance,
        "assumed_euler_axis_used": False,
        "root_local_location_shortcut_used": False,
        "pose_objects_created": False,
        "animation_authored": False,
        "runtime_activation_allowed": False,
        "save_or_export_performed": False,
        "visual_mesh_intersection_review_required": True,
    }
