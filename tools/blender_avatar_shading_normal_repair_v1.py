"""Localized weighted-normal repair for rear scalp and flexing knees.

This adapter adds one non-deform mask group and one final Weighted Normal
modifier.  It never changes mesh coordinates, topology, existing vertex-group
weights, materials, textures, anatomy, or scalp-hair state.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import struct
from typing import Any, Mapping

import bpy

from Core.avatar_shading_normal_repair_v1 import (
    METHOD_ID,
    combined_shading_mask_weight,
    load_validated_avatar_shading_normal_repair_v1,
    rear_scalp_mask_weight,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AvatarShadingNormalBlenderV1Error(RuntimeError):
    pass


def _coordinate_sha256(body: Any) -> str:
    digest = sha256()
    for vertex in body.data.vertices:
        digest.update(struct.pack("<3d", *(float(value) for value in vertex.co)))
    return digest.hexdigest()


def _topology_sha256(body: Any) -> str:
    digest = sha256()
    for edge in body.data.edges:
        digest.update(struct.pack("<2I", *(int(value) for value in edge.vertices)))
    for polygon in body.data.polygons:
        digest.update(struct.pack("<I", len(polygon.vertices)))
        for index in polygon.vertices:
            digest.update(struct.pack("<I", int(index)))
    return digest.hexdigest()


def _group_assignment_sha256(
    body: Any, *, included_names: set[str]
) -> str:
    group_names = {
        group.index: group.name
        for group in body.vertex_groups
        if group.name in included_names
    }
    digest = sha256()
    for vertex in body.data.vertices:
        for assignment in sorted(
            (
                (group_names[item.group], float(item.weight))
                for item in vertex.groups
                if item.group in group_names
            ),
            key=lambda row: row[0],
        ):
            digest.update(struct.pack("<I", int(vertex.index)))
            digest.update(assignment[0].encode("utf-8") + b"\0")
            digest.update(struct.pack("<d", assignment[1]))
    return digest.hexdigest()


def _material_snapshot(body: Any) -> dict[str, Any]:
    digest = sha256()
    for polygon in body.data.polygons:
        digest.update(struct.pack("<I", int(polygon.material_index)))
    return {
        "slots": [material.name if material else None for material in body.data.materials],
        "polygon_material_index_sha256": digest.hexdigest(),
    }


def _attribute_sha256(body: Any, name: str) -> str | None:
    attribute = body.data.color_attributes.get(name)
    if attribute is None:
        return None
    digest = sha256()
    for item in attribute.data:
        digest.update(struct.pack("<4d", *(float(value) for value in item.color)))
    return digest.hexdigest()


def _evaluated_position_sha256(body: Any) -> tuple[str, int]:
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        digest = sha256()
        for vertex in mesh.vertices:
            digest.update(struct.pack("<3d", *(float(value) for value in vertex.co)))
        return digest.hexdigest(), len(mesh.vertices)
    finally:
        evaluated.to_mesh_clear()


def _weights_for_group(body: Any, name: str) -> dict[int, float]:
    group = body.vertex_groups.get(name)
    if group is None:
        raise AvatarShadingNormalBlenderV1Error(f"required group missing: {name}")
    return {
        vertex.index: max(
            (
                float(assignment.weight)
                for assignment in vertex.groups
                if assignment.group == group.index
            ),
            default=0.0,
        )
        for vertex in body.data.vertices
    }


def install_localized_shading_normal_repair_v1(
    *,
    body: Any,
    armature: Any,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Install one final, mask-limited Weighted Normal modifier."""

    config, contract = load_validated_avatar_shading_normal_repair_v1(project_root)
    if body is None or body.type != "MESH" or not bool(body.get("primary_surface")):
        raise AvatarShadingNormalBlenderV1Error("normal repair requires primary body mesh")
    if armature is None or armature.type != "ARMATURE":
        raise AvatarShadingNormalBlenderV1Error("normal repair requires body armature")
    modifier_config = config["normal_modifier"]
    mask_name = str(modifier_config["mask_vertex_group"])
    modifier_name = str(modifier_config["name"])
    if body.vertex_groups.get(mask_name) is not None or body.modifiers.get(modifier_name) is not None:
        raise AvatarShadingNormalBlenderV1Error("normal repair already installed")

    coordinates_before = _coordinate_sha256(body)
    topology_before = _topology_sha256(body)
    vertex_count_before = len(body.data.vertices)
    polygon_count_before = len(body.data.polygons)
    existing_group_names = {group.name for group in body.vertex_groups}
    bone_names = {bone.name for bone in armature.data.bones}
    deform_group_names = existing_group_names.intersection(bone_names)
    existing_groups_before = _group_assignment_sha256(
        body, included_names=existing_group_names
    )
    deform_weights_before = _group_assignment_sha256(
        body, included_names=deform_group_names
    )
    material_before = _material_snapshot(body)
    regional_tint_before = _attribute_sha256(body, "Kira_Regional_Skin_Tint_V3")
    image_names_before = set(bpy.data.images.keys())
    object_names_before = set(bpy.data.objects.keys())
    evaluated_before, evaluated_vertex_count_before = _evaluated_position_sha256(body)

    coordinates = [vertex.co for vertex in body.data.vertices]
    xs = [float(point.x) for point in coordinates]
    ys = [float(point.y) for point in coordinates]
    zs = [float(point.z) for point in coordinates]
    z_min, z_max = min(zs), max(zs)
    body_height = z_max - z_min
    if body_height <= 0.0:
        raise AvatarShadingNormalBlenderV1Error("body height is invalid")
    membership_names = list(
        config["rear_scalp_mask"]["required_existing_membership_groups"]
    )
    membership_maps = {
        name: _weights_for_group(body, name) for name in membership_names
    }
    head_related = [
        vertex
        for vertex in body.data.vertices
        if sum(weights[vertex.index] for weights in membership_maps.values())
        >= float(config["rear_scalp_mask"]["minimum_existing_membership_sum"])
    ]
    if not head_related:
        raise AvatarShadingNormalBlenderV1Error("head/neck shading frame is empty")
    head_x_half = max(abs(float(vertex.co.x)) for vertex in head_related)
    head_y_min = min(float(vertex.co.y) for vertex in head_related)
    head_y_max = max(float(vertex.co.y) for vertex in head_related)
    if min(head_x_half, head_y_max - head_y_min) <= 1.0e-8:
        raise AvatarShadingNormalBlenderV1Error("head/neck shading frame is invalid")

    knee_names = list(config["knee_mask"]["required_existing_groups"])
    left_knee = _weights_for_group(body, knee_names[0])
    right_knee = _weights_for_group(body, knee_names[1])
    mask_values: dict[int, float] = {}
    scalp_count = 0
    left_knee_count = 0
    right_knee_count = 0
    front_face_mask_count = 0
    for vertex in body.data.vertices:
        membership = sum(
            weights[vertex.index] for weights in membership_maps.values()
        )
        rearwardness = (float(vertex.co.y) - head_y_min) / (head_y_max - head_y_min)
        scalp = rear_scalp_mask_weight(
            normalized_body_height=(float(vertex.co.z) - z_min) / body_height,
            normalized_head_rearwardness=rearwardness,
            normalized_head_lateral=float(vertex.co.x) / head_x_half,
            existing_head_neck_membership=membership,
        )
        left = left_knee[vertex.index]
        right = right_knee[vertex.index]
        value = combined_shading_mask_weight(
            scalp_weight=scalp,
            left_knee_weight=left,
            right_knee_weight=right,
        )
        if value <= 0.005:
            continue
        mask_values[vertex.index] = value
        scalp_count += scalp > 0.005
        left_knee_count += left > 0.005
        right_knee_count += right > 0.005
        if (
            float(vertex.co.z) >= z_min + body_height * 0.80
            and rearwardness < 0.62
            and left <= 0.005
            and right <= 0.005
        ):
            front_face_mask_count += 1
    if scalp_count < 80 or min(left_knee_count, right_knee_count) < 80:
        raise AvatarShadingNormalBlenderV1Error(
            "localized normal mask is incomplete: "
            f"scalp={scalp_count};left_knee={left_knee_count};right_knee={right_knee_count}"
        )
    if front_face_mask_count:
        raise AvatarShadingNormalBlenderV1Error(
            f"rear-scalp mask leaked onto front face: {front_face_mask_count}"
        )

    mask_group = body.vertex_groups.new(name=mask_name)
    modifier = None
    try:
        for vertex_index, weight in mask_values.items():
            mask_group.add([int(vertex_index)], float(weight), "REPLACE")
        modifier = body.modifiers.new(modifier_name, "WEIGHTED_NORMAL")
        modifier.vertex_group = mask_name
        modifier.mode = str(modifier_config["mode"])
        modifier.weight = int(modifier_config["weight"])
        modifier.thresh = float(modifier_config["threshold_radians"])
        modifier.keep_sharp = bool(modifier_config["keep_sharp"])
        modifier.use_face_influence = bool(modifier_config["use_face_influence"])
        bpy.context.view_layer.update()

        coordinates_after = _coordinate_sha256(body)
        topology_after = _topology_sha256(body)
        existing_groups_after = _group_assignment_sha256(
            body, included_names=existing_group_names
        )
        deform_weights_after = _group_assignment_sha256(
            body, included_names=deform_group_names
        )
        material_after = _material_snapshot(body)
        regional_tint_after = _attribute_sha256(body, "Kira_Regional_Skin_Tint_V3")
        evaluated_after, evaluated_vertex_count_after = _evaluated_position_sha256(body)
        gates = {
            "primary_mesh_coordinates_unchanged": coordinates_after == coordinates_before,
            "evaluated_vertex_positions_unchanged": evaluated_after == evaluated_before,
            "topology_unchanged": topology_after == topology_before,
            "vertex_and_polygon_counts_unchanged": (
                len(body.data.vertices) == vertex_count_before
                and len(body.data.polygons) == polygon_count_before
                and evaluated_vertex_count_after == evaluated_vertex_count_before
            ),
            "existing_vertex_groups_unchanged": existing_groups_after == existing_groups_before,
            "existing_deform_weight_hash_unchanged": (
                deform_weights_after == deform_weights_before
            ),
            "only_new_vertex_group_is_non_deform_shading_mask": (
                {group.name for group in body.vertex_groups}.difference(existing_group_names)
                == {mask_name}
                and mask_name not in bone_names
            ),
            "material_slots_and_polygon_indices_unchanged": material_after == material_before,
            "regional_skin_attribute_unchanged": regional_tint_after == regional_tint_before,
            "images_unchanged": set(bpy.data.images.keys()) == image_names_before,
            "objects_unchanged": set(bpy.data.objects.keys()) == object_names_before,
            "weighted_normal_is_last_modifier": body.modifiers[-1] == modifier,
            "clean_bald_scalp_material_unchanged": (
                all(
                    int(polygon.material_index) == 0
                    for polygon in body.data.polygons
                    if any(
                        float(body.data.vertices[index].co.z)
                        >= z_min + body_height * 0.94
                        for index in polygon.vertices
                    )
                )
            ),
        }
        if not all(gates.values()):
            raise AvatarShadingNormalBlenderV1Error(
                "localized normal hard gate failed: "
                + json.dumps(gates, sort_keys=True)
            )
    except Exception:
        if modifier is not None and body.modifiers.get(modifier.name) is not None:
            body.modifiers.remove(modifier)
        if body.vertex_groups.get(mask_group.name) is not None:
            body.vertex_groups.remove(mask_group)
        raise

    report = {
        "method_id": METHOD_ID,
        "contract": contract,
        "implementation": "one_final_mask_limited_weighted_normal_modifier",
        "modifier": {
            "name": modifier.name,
            "type": modifier.type,
            "mode": modifier.mode,
            "weight": int(modifier.weight),
            "threshold_radians": float(modifier.thresh),
            "keep_sharp": bool(modifier.keep_sharp),
            "vertex_group": modifier.vertex_group,
            "modifier_index": list(body.modifiers).index(modifier),
            "modifier_count": len(body.modifiers),
        },
        "mask": {
            "name": mask_name,
            "non_deform": mask_name not in bone_names,
            "weighted_vertex_count": len(mask_values),
            "rear_scalp_vertex_count": scalp_count,
            "left_knee_vertex_count": left_knee_count,
            "right_knee_vertex_count": right_knee_count,
            "front_face_mask_vertex_count": front_face_mask_count,
            "minimum_weight": min(mask_values.values()),
            "maximum_weight": max(mask_values.values()),
        },
        "gates": gates,
        "primary_coordinate_sha256_before_after": [
            coordinates_before,
            coordinates_after,
        ],
        "evaluated_position_sha256_before_after": [
            evaluated_before,
            evaluated_after,
        ],
        "topology_sha256_before_after": [topology_before, topology_after],
        "existing_deform_weight_sha256_before_after": [
            deform_weights_before,
            deform_weights_after,
        ],
        "existing_vertex_group_assignment_sha256_before_after": [
            existing_groups_before,
            existing_groups_after,
        ],
        "materials_before_after": [material_before, material_after],
        "regional_skin_attribute_sha256_before_after": [
            regional_tint_before,
            regional_tint_after,
        ],
        "face_body_anatomy_geometry_changed": False,
        "existing_rig_weights_changed": False,
        "scalp_material_changed": False,
        "scalp_hair_dependency_added": False,
        "runtime_activation_allowed": False,
        "owner_visual_review_required": True,
    }
    body["avatar_shading_normal_repair_v1"] = True
    body["avatar_shading_normal_repair_v1_report"] = json.dumps(
        report, sort_keys=True
    )
    return report


__all__ = [
    "AvatarShadingNormalBlenderV1Error",
    "METHOD_ID",
    "install_localized_shading_normal_repair_v1",
]
