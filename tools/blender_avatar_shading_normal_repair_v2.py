"""Scalp-only custom-normal smoothing for the R17 horizontal rear band."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector

from Core.avatar_shading_normal_repair_v2 import (
    METHOD_ID,
    load_validated_avatar_shading_normal_repair_v2,
    rear_scalp_mask_weight_v2,
)
from tools.blender_avatar_shading_normal_repair_v1 import (
    _attribute_sha256,
    _coordinate_sha256,
    _evaluated_position_sha256,
    _group_assignment_sha256,
    _material_snapshot,
    _topology_sha256,
    _weights_for_group,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AvatarShadingNormalBlenderV2Error(RuntimeError):
    pass


def _angle_degrees(left: Vector, right: Vector) -> float:
    dot = max(-1.0, min(1.0, float(left.normalized().dot(right.normalized()))))
    return math.degrees(math.acos(dot))


def _edge_angle_summary(
    body: Any, normals: list[Vector], mask: dict[int, float]
) -> dict[str, float | int]:
    values = sorted(
        _angle_degrees(normals[int(edge.vertices[0])], normals[int(edge.vertices[1])])
        for edge in body.data.edges
        if mask.get(int(edge.vertices[0]), 0.0) >= 0.05
        and mask.get(int(edge.vertices[1]), 0.0) >= 0.05
    )
    if not values:
        raise AvatarShadingNormalBlenderV2Error("rear-scalp masked edge set is empty")
    return {
        "edge_count": len(values),
        "mean_degrees": sum(values) / len(values),
        "maximum_degrees": max(values),
        "p95_degrees": values[min(len(values) - 1, int(len(values) * 0.95))],
    }


def install_rear_scalp_custom_normal_repair_v2(
    *,
    body: Any,
    armature: Any,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Smooth only the rear scalp's stored split normals; never move geometry."""

    config, contract = load_validated_avatar_shading_normal_repair_v2(project_root)
    if body is None or body.type != "MESH" or not bool(body.get("primary_surface")):
        raise AvatarShadingNormalBlenderV2Error("v2 normal repair requires primary mesh")
    if armature is None or armature.type != "ARMATURE":
        raise AvatarShadingNormalBlenderV2Error("v2 normal repair requires armature")
    if bool(getattr(body.data, "has_custom_normals", False)):
        raise AvatarShadingNormalBlenderV2Error(
            "v2 refuses to overwrite pre-existing custom normals"
        )

    coordinates_before = _coordinate_sha256(body)
    topology_before = _topology_sha256(body)
    evaluated_before, evaluated_count_before = _evaluated_position_sha256(body)
    existing_group_names = {group.name for group in body.vertex_groups}
    existing_groups_before = _group_assignment_sha256(
        body, included_names=existing_group_names
    )
    deform_names = existing_group_names.intersection(
        {bone.name for bone in armature.data.bones}
    )
    deform_before = _group_assignment_sha256(body, included_names=deform_names)
    materials_before = _material_snapshot(body)
    tint_before = _attribute_sha256(body, "Kira_Regional_Skin_Tint_V3")
    object_names_before = set(bpy.data.objects.keys())
    image_names_before = set(bpy.data.images.keys())
    vertex_count_before = len(body.data.vertices)
    polygon_count_before = len(body.data.polygons)

    mesh = body.data
    mesh.update()
    original = [vertex.normal.copy().normalized() for vertex in mesh.vertices]
    z_values = [float(vertex.co.z) for vertex in mesh.vertices]
    z_min, z_max = min(z_values), max(z_values)
    height = z_max - z_min
    membership_names = list(
        config["rear_scalp_mask"]["required_existing_membership_groups"]
    )
    membership_maps = {
        name: _weights_for_group(body, name) for name in membership_names
    }
    head_related = [
        vertex
        for vertex in mesh.vertices
        if sum(weights[vertex.index] for weights in membership_maps.values())
        >= float(config["rear_scalp_mask"]["minimum_existing_membership_sum"])
    ]
    head_x_half = max(abs(float(vertex.co.x)) for vertex in head_related)
    head_y_min = min(float(vertex.co.y) for vertex in head_related)
    head_y_max = max(float(vertex.co.y) for vertex in head_related)
    mask: dict[int, float] = {}
    front_face_mask_count = 0
    for vertex in mesh.vertices:
        membership = sum(
            weights[vertex.index] for weights in membership_maps.values()
        )
        rearwardness = (float(vertex.co.y) - head_y_min) / (head_y_max - head_y_min)
        value = rear_scalp_mask_weight_v2(
            normalized_body_height=(float(vertex.co.z) - z_min) / height,
            normalized_head_rearwardness=rearwardness,
            normalized_head_lateral=float(vertex.co.x) / head_x_half,
            existing_head_neck_membership=membership,
        )
        if value > 0.005:
            mask[vertex.index] = value
            if rearwardness < 0.62:
                front_face_mask_count += 1
    if len(mask) < 80 or front_face_mask_count:
        raise AvatarShadingNormalBlenderV2Error(
            f"rear-scalp mask invalid: count={len(mask)};front={front_face_mask_count}"
        )
    knee_indices: set[int] = set()
    for name in (
        "AVATAR_BUILDER_KNEE_CORRECTIVE_V2_L",
        "AVATAR_BUILDER_KNEE_CORRECTIVE_V2_R",
    ):
        weights = _weights_for_group(body, name)
        knee_indices.update(index for index, weight in weights.items() if weight > 0.005)
    if set(mask).intersection(knee_indices):
        raise AvatarShadingNormalBlenderV2Error("scalp normal mask overlaps knee region")

    adjacency: list[set[int]] = [set() for _vertex in mesh.vertices]
    for edge in mesh.edges:
        left, right = (int(value) for value in edge.vertices)
        adjacency[left].add(right)
        adjacency[right].add(left)
    smoothing = config["normal_smoothing"]
    result = [normal.copy() for normal in original]
    for _iteration in range(int(smoothing["laplacian_iterations"])):
        updated = [normal.copy() for normal in result]
        for index, weight in mask.items():
            neighbors = adjacency[index]
            if not neighbors:
                continue
            average = Vector((0.0, 0.0, 0.0))
            for neighbor in neighbors:
                average += result[neighbor]
            if average.length <= 1.0e-10:
                continue
            average.normalize()
            amount = float(smoothing["per_iteration_strength"]) * float(weight)
            blended = result[index].lerp(average, amount)
            if blended.length > 1.0e-10:
                updated[index] = blended.normalized()
        result = updated

    changed = {
        index: _angle_degrees(original[index], result[index]) for index in mask
    }
    maximum_change = max(changed.values())
    maximum_allowed = float(smoothing["maximum_normal_change_degrees"])
    outside_coordinate_delta = max(
        (
            float((original[index] - result[index]).length)
            for index in range(len(result))
            if index not in mask
        ),
        default=0.0,
    )
    # acos(dot(v, v)) is not a valid unchanged-vector gate in Blender's
    # float32 math: the rounded self-dot can report roughly 0.036 degrees.
    # Component distance is exact here because outside-mask normals are copied
    # and never assigned during the smoothing iterations.
    outside_change = 0.0
    if outside_coordinate_delta > 0.0:
        outside_change = max(
            (
                _angle_degrees(original[index], result[index])
                for index in range(len(result))
                if index not in mask
            ),
            default=0.0,
        )
    before_edges = _edge_angle_summary(body, original, mask)
    after_edges = _edge_angle_summary(body, result, mask)
    reduction = (
        float(before_edges["mean_degrees"]) - float(after_edges["mean_degrees"])
    ) / float(before_edges["mean_degrees"])
    if (
        maximum_change > maximum_allowed + 1.0e-6
        or outside_change > 1.0e-6
        or reduction
        < float(smoothing["minimum_masked_edge_mean_angle_reduction_fraction"])
    ):
        raise AvatarShadingNormalBlenderV2Error(
            "custom-normal quality gate failed: "
            + json.dumps(
                {
                    "maximum_change_degrees": maximum_change,
                    "outside_change_degrees": outside_change,
                    "outside_coordinate_delta": outside_coordinate_delta,
                    "edge_mean_reduction_fraction": reduction,
                },
                sort_keys=True,
            )
        )

    mesh.normals_split_custom_set_from_vertices(result)
    mesh.update()
    bpy.context.view_layer.update()
    coordinates_after = _coordinate_sha256(body)
    topology_after = _topology_sha256(body)
    evaluated_after, evaluated_count_after = _evaluated_position_sha256(body)
    existing_groups_after = _group_assignment_sha256(
        body, included_names=existing_group_names
    )
    deform_after = _group_assignment_sha256(body, included_names=deform_names)
    materials_after = _material_snapshot(body)
    tint_after = _attribute_sha256(body, "Kira_Regional_Skin_Tint_V3")
    gates = {
        "primary_coordinates_unchanged": coordinates_after == coordinates_before,
        "evaluated_positions_unchanged": evaluated_after == evaluated_before,
        "topology_unchanged": topology_after == topology_before,
        "counts_unchanged": (
            len(mesh.vertices) == vertex_count_before
            and len(mesh.polygons) == polygon_count_before
            and evaluated_count_after == evaluated_count_before
        ),
        "all_existing_vertex_groups_and_weights_unchanged": (
            existing_groups_after == existing_groups_before
            and {group.name for group in body.vertex_groups} == existing_group_names
        ),
        "deform_weights_unchanged": deform_after == deform_before,
        "materials_unchanged": materials_after == materials_before,
        "regional_skin_attribute_unchanged": tint_after == tint_before,
        "objects_unchanged": set(bpy.data.objects.keys()) == object_names_before,
        "images_unchanged": set(bpy.data.images.keys()) == image_names_before,
        "custom_normals_present": bool(mesh.has_custom_normals),
        "front_face_normals_unchanged": front_face_mask_count == 0,
        "knee_normals_unchanged": not bool(set(mask).intersection(knee_indices)),
        "clean_bald_scalp_material_unchanged": all(
            int(polygon.material_index) == 0
            for polygon in mesh.polygons
            if any(
                float(mesh.vertices[index].co.z) >= z_min + height * 0.94
                for index in polygon.vertices
            )
        ),
    }
    if not all(gates.values()):
        raise AvatarShadingNormalBlenderV2Error(
            "post-normal hard gate failed: " + json.dumps(gates, sort_keys=True)
        )
    report = {
        "method_id": METHOD_ID,
        "contract": contract,
        "implementation": "rear_scalp_only_laplacian_smoothed_custom_split_vertex_normals",
        "mask": {
            "vertex_count": len(mask),
            "front_face_vertex_count": front_face_mask_count,
            "knee_overlap_vertex_count": 0,
            "minimum_weight": min(mask.values()),
            "maximum_weight": max(mask.values()),
        },
        "normal_change": {
            "changed_vertex_count": sum(value > 1.0e-5 for value in changed.values()),
            "maximum_degrees": maximum_change,
            "mean_degrees": sum(changed.values()) / len(changed),
            "outside_mask_maximum_degrees": outside_change,
            "outside_mask_maximum_coordinate_delta": outside_coordinate_delta,
            "masked_edge_angles_before": before_edges,
            "masked_edge_angles_after": after_edges,
            "masked_edge_mean_reduction_fraction": reduction,
        },
        "gates": gates,
        "coordinate_sha256_before_after": [coordinates_before, coordinates_after],
        "evaluated_position_sha256_before_after": [evaluated_before, evaluated_after],
        "topology_sha256_before_after": [topology_before, topology_after],
        "existing_group_assignment_sha256_before_after": [
            existing_groups_before,
            existing_groups_after,
        ],
        "deform_weight_sha256_before_after": [deform_before, deform_after],
        "materials_before_after": [materials_before, materials_after],
        "regional_skin_attribute_sha256_before_after": [tint_before, tint_after],
        "body_geometry_changed": False,
        "existing_weights_changed": False,
        "face_or_anatomy_changed": False,
        "knee_repair_claimed": False,
        "knee_defect_deferred_to_deformation_repair": True,
        "scalp_material_changed": False,
        "scalp_hair_dependency_added": False,
        "runtime_activation_allowed": False,
        "owner_visual_review_required": True,
    }
    body["avatar_shading_normal_repair_v2"] = True
    body["avatar_shading_normal_repair_v2_report"] = json.dumps(
        report, sort_keys=True
    )
    return report


__all__ = [
    "AvatarShadingNormalBlenderV2Error",
    "METHOD_ID",
    "install_rear_scalp_custom_normal_repair_v2",
]
