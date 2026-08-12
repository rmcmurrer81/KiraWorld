"""Reusable Blender adapter for Kira's bounded appearance delivery v3.

The adapter changes appearance only: it preserves every body coordinate, rig
weight, scalp polygon, and body object identity.  Lips and nipple-areola tone
are assigned to polygons on the existing primary body mesh.  Eyebrows and eye
surrounds are lightweight facial components rigidly attached to the head bone;
they are not scalp hair and create no scalp-hair dependency.
"""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import statistics
import struct
from typing import Any, Mapping, Sequence

import bpy
from mathutils import Vector

import tools.blender_profiled_adult_candidate_components as v1
from Core.avatar_kira_appearance_delivery_v3 import (
    KiraAppearanceDeliveryV3Error,
    METHOD_ID,
    REGIONAL_SKIN_MULTIPLY_NODE,
    REGIONAL_SKIN_TINT_ATTRIBUTE,
    brow_profile,
    continuous_strip_topology,
    load_validated_kira_appearance_delivery_v3,
    regional_skin_multiplier,
    required_face_vertex_count,
    tapered_line_radius,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class KiraAppearanceBlenderV3Error(RuntimeError):
    pass


def _coordinate_sha256(body: Any) -> str:
    digest = sha256()
    for vertex in body.data.vertices:
        digest.update(struct.pack("<3d", *(float(value) for value in vertex.co)))
    return digest.hexdigest()


def _material(name: str, srgb_hex: str, roughness: float) -> Any:
    found = bpy.data.materials.get(name)
    if found is not None:
        return found
    material = v1._simple_material(  # noqa: SLF001
        name, str(srgb_hex), roughness=float(roughness)
    )
    material["kira_appearance_delivery_v3"] = True
    material["scalp_hair_material"] = False
    material["image_texture_dependency"] = False
    return material


def _principled(material: Any) -> Any:
    if material is None or not material.use_nodes or material.node_tree is None:
        raise KiraAppearanceBlenderV3Error("appearance requires a node skin material")
    found = material.node_tree.nodes.get("Principled BSDF")
    if found is None:
        found = next(
            (node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"),
            None,
        )
    if found is None:
        raise KiraAppearanceBlenderV3Error("skin Principled BSDF is missing")
    return found


def _material_index(body: Any, material: Any) -> int:
    for index, found in enumerate(body.data.materials):
        if found == material:
            return int(index)
    body.data.materials.append(material)
    return len(body.data.materials) - 1


def install_regional_skin_tint_v3(
    body: Any, config: Mapping[str, Any]
) -> dict[str, Any]:
    """Insert a bounded per-corner tint into the existing skin albedo path."""

    if body is None or body.type != "MESH" or not body.data.materials:
        raise KiraAppearanceBlenderV3Error("regional skin tint requires a mesh body")
    skin_config = config["skin"]
    material = body.data.materials[0]
    principled = _principled(material)
    mesh = body.data
    attribute = mesh.color_attributes.get(REGIONAL_SKIN_TINT_ATTRIBUTE)
    if attribute is None:
        attribute = mesh.color_attributes.new(
            name=REGIONAL_SKIN_TINT_ATTRIBUTE,
            type=str(skin_config["attribute_type"]),
            domain=str(skin_config["attribute_domain"]),
        )
    if attribute.domain != "CORNER" or attribute.data_type != "BYTE_COLOR":
        raise KiraAppearanceBlenderV3Error("regional skin attribute storage drifted")

    xs = [float(vertex.co.x) for vertex in mesh.vertices]
    ys = [float(vertex.co.y) for vertex in mesh.vertices]
    zs = [float(vertex.co.z) for vertex in mesh.vertices]
    if not xs or not ys or not zs:
        raise KiraAppearanceBlenderV3Error("regional skin body is empty")
    x_half = max(abs(min(xs)), abs(max(xs)))
    y_min, y_max = min(ys), max(ys)
    y_mid = (y_min + y_max) * 0.5
    z_min, z_max = min(zs), max(zs)
    height = z_max - z_min
    if min(x_half, y_mid - y_min, height) <= 1.0e-8:
        raise KiraAppearanceBlenderV3Error("regional skin normalization bounds invalid")

    values: list[tuple[float, float, float]] = []
    for loop_index, loop in enumerate(mesh.loops):
        point = mesh.vertices[loop.vertex_index].co
        multiplier = regional_skin_multiplier(
            normalized_lateral=float(point.x) / x_half,
            normalized_height=(float(point.z) - z_min) / height,
            frontness=max(0.0, min(1.0, (y_mid - float(point.y)) / (y_mid - y_min))),
        )
        attribute.data[loop_index].color = (*multiplier, 1.0)
        values.append(multiplier)

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    attribute_node = nodes.get(REGIONAL_SKIN_TINT_ATTRIBUTE)
    multiply = nodes.get(REGIONAL_SKIN_MULTIPLY_NODE)
    base_input = v1._principled_input(principled, "Base Color")  # noqa: SLF001
    if base_input is None:
        raise KiraAppearanceBlenderV3Error("skin base-color socket missing")
    if attribute_node is None and multiply is None:
        attribute_node = nodes.new("ShaderNodeVertexColor")
        attribute_node.name = REGIONAL_SKIN_TINT_ATTRIBUTE
        attribute_node.label = "Bounded regional skin tint (facial/extremity warmth)"
        attribute_node.layer_name = REGIONAL_SKIN_TINT_ATTRIBUTE
        multiply = nodes.new("ShaderNodeMixRGB")
        multiply.name = REGIONAL_SKIN_MULTIPLY_NODE
        multiply.label = "Preserve microvariation x regional tint"
        multiply.blend_type = "MULTIPLY"
        multiply.inputs[0].default_value = 1.0
        existing_link = base_input.links[0] if base_input.links else None
        if existing_link is not None:
            existing_socket = existing_link.from_socket
            links.remove(existing_link)
            links.new(existing_socket, multiply.inputs[1])
        else:
            multiply.inputs[1].default_value = tuple(material.diffuse_color)
        links.new(attribute_node.outputs["Color"], multiply.inputs[2])
        links.new(multiply.outputs["Color"], base_input)
    elif attribute_node is None or multiply is None:
        raise KiraAppearanceBlenderV3Error("partial regional skin shader graph found")
    else:
        attribute_node.layer_name = REGIONAL_SKIN_TINT_ATTRIBUTE

    if not any(link.from_node == multiply and link.to_socket == base_input for link in links):
        raise KiraAppearanceBlenderV3Error("regional skin tint is not on real albedo path")
    if not any(link.from_node == attribute_node and link.to_node == multiply for link in links):
        raise KiraAppearanceBlenderV3Error("regional skin attribute is disconnected")
    minimums = [min(row[channel] for row in values) for channel in range(3)]
    maximums = [max(row[channel] for row in values) for channel in range(3)]
    minimum_bound = float(skin_config["minimum_channel_multiplier"])
    maximum_bound = float(skin_config["maximum_channel_multiplier"])
    if min(minimums) < minimum_bound - 1.0e-6 or max(maximums) > maximum_bound + 1.0e-6:
        raise KiraAppearanceBlenderV3Error("regional skin values escaped config bounds")
    non_neutral = sum(
        max(abs(channel - 1.0) for channel in row) >= 0.002 for row in values
    )
    if non_neutral < max(100, len(values) // 100):
        raise KiraAppearanceBlenderV3Error("regional skin tint is effectively flat")
    material["kira_regional_skin_tint_v3"] = True
    body["regional_skin_variation"] = METHOD_ID
    return {
        "method": "bounded_per_corner_regional_skin_albedo_multiplier_v3",
        "material": material.name,
        "attribute": REGIONAL_SKIN_TINT_ATTRIBUTE,
        "attribute_domain": attribute.domain,
        "attribute_data_type": attribute.data_type,
        "loop_count": len(values),
        "non_neutral_loop_count": non_neutral,
        "channel_minimums": minimums,
        "channel_maximums": maximums,
        "shader_attribute_node": attribute_node.name,
        "shader_multiply_node": multiply.name,
        "connected_to_real_principled_base_color": True,
        "preexisting_microvariation_preserved_upstream": True,
        "image_textures_added": False,
        "measured_color_claim": False,
    }


def _vertex_group_weight(body: Any, names: Sequence[str]) -> dict[int, float]:
    group_indices = {
        group.index
        for name in names
        if (group := body.vertex_groups.get(str(name))) is not None
    }
    return {
        vertex.index: max(
            (assignment.weight for assignment in vertex.groups if assignment.group in group_indices),
            default=0.0,
        )
        for vertex in body.data.vertices
    }


def _lip_polygons(body: Any, lip_config: Mapping[str, Any]) -> tuple[list[int], dict[str, Any]]:
    weights = _vertex_group_weight(body, lip_config["source_vertex_groups"])
    threshold = float(lip_config["minimum_source_weight"])
    candidates = [
        body.data.vertices[index]
        for index, weight in weights.items()
        if weight >= threshold
    ]
    if len(candidates) < 30:
        raise KiraAppearanceBlenderV3Error("rig-supported lip region is missing")
    xs = [float(vertex.co.x) for vertex in candidates]
    ys = sorted(float(vertex.co.y) for vertex in candidates)
    zs = [float(vertex.co.z) for vertex in candidates]
    center_x = (min(xs) + max(xs)) * 0.5
    center_z = statistics.median(zs)
    radius_x = max(0.008, (max(xs) - min(xs)) * 0.43)
    radius_z = max(0.005, (max(zs) - min(zs)) * 0.27)
    front_cutoff = ys[min(len(ys) - 1, int(len(ys) * 0.48))] + 0.0025
    eligible = {
        vertex.index
        for vertex in body.data.vertices
        if weights.get(vertex.index, 0.0) >= threshold * 0.34
        and ((float(vertex.co.x) - center_x) / radius_x) ** 2
        + ((float(vertex.co.z) - center_z) / radius_z) ** 2
        <= 1.0
        and float(vertex.co.y) <= front_cutoff
    }
    selected = [
        int(polygon.index)
        for polygon in body.data.polygons
        if sum(int(index) in eligible for index in polygon.vertices)
        >= required_face_vertex_count(len(polygon.vertices))
    ]
    if len(selected) < int(lip_config["minimum_polygon_count"]):
        raise KiraAppearanceBlenderV3Error(
            f"bounded rig-supported lip coverage too sparse: {len(selected)}"
        )
    return selected, {
        "selection": "rig_supported_oris_groups_plus_bounded_front_ellipse",
        "source_group_names": list(lip_config["source_vertex_groups"]),
        "source_candidate_vertex_count": len(candidates),
        "eligible_vertex_count": len(eligible),
        "center_object_local_m": [center_x, front_cutoff, center_z],
        "radii_m": [radius_x, radius_z],
        "polygon_count": len(selected),
    }


def _areola_region_vertices(
    body: Any,
    *,
    side: str,
    areola_config: Mapping[str, Any],
) -> tuple[set[int], dict[str, Any]]:
    group_name = f"AFES_TORSO__areola_{'left' if side == 'L' else 'right'}"
    group = body.vertex_groups.get(group_name)
    if group is not None:
        indices = {
            vertex.index
            for vertex in body.data.vertices
            if any(
                assignment.group == group.index and assignment.weight >= 0.5
                for assignment in vertex.groups
            )
        }
        if len(indices) >= 3:
            points = [body.data.vertices[index].co for index in indices]
            center_x = statistics.median(float(point.x) for point in points)
            center_z = statistics.median(float(point.z) for point in points)
            radius = max(
                math.hypot(float(point.x) - center_x, float(point.z) - center_z)
                for point in points
            ) * 1.08
            return indices, {
                "source": "same_surface_adult_authoring_vertex_group",
                "vertex_group": group_name,
                "vertex_count": len(indices),
                "center_object_local_m": [center_x, center_z],
                "radius_m": radius,
            }
    z_values = [float(vertex.co.z) for vertex in body.data.vertices]
    height = max(z_values) - min(z_values)
    baseline = float(areola_config["fallback_baseline_height_m"])
    scale = height / baseline
    breast_group_name = f"breast.{side}"
    breast_group = body.vertex_groups.get(breast_group_name)
    front_candidates: list[Any] = []
    if breast_group is not None:
        weighted = [
            vertex
            for vertex in body.data.vertices
            if any(
                assignment.group == breast_group.index and assignment.weight >= 0.15
                for assignment in vertex.groups
            )
        ]
        front_count = max(8, int(len(weighted) * 0.10))
        front_candidates = sorted(weighted, key=lambda vertex: float(vertex.co.y))[
            :front_count
        ]
    if front_candidates:
        center_x = statistics.median(float(vertex.co.x) for vertex in front_candidates)
        center_z = statistics.median(float(vertex.co.z) for vertex in front_candidates)
        fallback_source = "bounded_frontmost_breast_rig_group_fallback"
    else:
        center_x = float(areola_config["fallback_center_abs_x_m"]) * scale
        if side == "R":
            center_x = -center_x
        center_z = min(z_values) + float(areola_config["fallback_center_z_m"]) * scale
        fallback_source = "bounded_height_scaled_coordinate_fallback"
    radius = float(areola_config["fallback_radius_m"]) * scale
    alignment = float(areola_config["minimum_front_normal_alignment"])
    indices = {
        vertex.index
        for vertex in body.data.vertices
        if ((float(vertex.co.x) - center_x) / radius) ** 2
        + ((float(vertex.co.z) - center_z) / radius) ** 2
        <= 1.0
        and float(vertex.normal.y) <= -alignment
    }
    if len(indices) < 3:
        raise KiraAppearanceBlenderV3Error(
            f"same-surface fallback areola region too sparse for {side}: {len(indices)}"
        )
    return indices, {
        "source": fallback_source,
        "vertex_group": None,
        "vertex_count": len(indices),
        "center_object_local_m": [center_x, center_z],
        "radius_m": radius,
        "minimum_front_normal_alignment": alignment,
        "breast_rig_group": breast_group_name if front_candidates else None,
        "frontmost_breast_sample_count": len(front_candidates),
    }


def _smoothstep(edge0: float, edge1: float, value: float) -> float:
    if edge1 <= edge0:
        raise ValueError("smoothstep edges must be increasing")
    amount = max(0.0, min(1.0, (float(value) - edge0) / (edge1 - edge0)))
    return amount * amount * (3.0 - 2.0 * amount)


def _multiply_toward(
    color: Sequence[float], multiplier: Sequence[float], weight: float
) -> tuple[float, float, float, float]:
    amount = max(0.0, min(1.0, float(weight)))
    return tuple(
        max(0.0, min(1.0, float(color[channel]) * (1.0 + (float(multiplier[channel]) - 1.0) * amount)))
        for channel in range(3)
    ) + (1.0,)


def assign_natural_surface_tones_v3(
    body: Any, config: Mapping[str, Any]
) -> dict[str, Any]:
    """Blend lip and nipple-areola tone into the real primary-skin albedo path."""

    if body is None or body.type != "MESH" or not bool(body.get("primary_surface")):
        raise KiraAppearanceBlenderV3Error("surface tones require the primary body mesh")
    tones = config["surface_tones"]
    lip_config = tones["lip"]
    areola_config = tones["nipple_areola"]
    lip_polygons, lip_selection = _lip_polygons(body, lip_config)
    areola_polygons: dict[str, list[int]] = {}
    areola_selection: dict[str, Any] = {}
    for side in ("L", "R"):
        indices, region = _areola_region_vertices(
            body, side=side, areola_config=areola_config
        )
        selected = [
            int(polygon.index)
            for polygon in body.data.polygons
            if sum(int(index) in indices for index in polygon.vertices)
            >= required_face_vertex_count(len(polygon.vertices))
        ]
        if len(selected) < int(areola_config["minimum_polygon_count_per_side"]):
            raise KiraAppearanceBlenderV3Error(
                f"same-surface areola coverage too sparse for {side}: {len(selected)}"
            )
        areola_polygons[side] = selected
        areola_selection[side] = {**region, "polygon_count": len(selected)}
    overlap = set(lip_polygons).intersection(
        set(areola_polygons["L"]) | set(areola_polygons["R"])
    )
    if overlap:
        raise KiraAppearanceBlenderV3Error("lip and areola regions overlap")

    attribute = body.data.color_attributes.get(REGIONAL_SKIN_TINT_ATTRIBUTE)
    if attribute is None or attribute.domain != "CORNER":
        raise KiraAppearanceBlenderV3Error(
            "same-surface tones require the connected regional skin attribute"
        )
    material_indices_before = [
        int(polygon.material_index) for polygon in body.data.polygons
    ]
    lip_region_materials = {
        material_indices_before[index] for index in lip_polygons
    }
    areola_region_materials = {
        material_indices_before[index]
        for side in ("L", "R")
        for index in areola_polygons[side]
    }
    if lip_region_materials != {0} or areola_region_materials != {0}:
        raise KiraAppearanceBlenderV3Error(
            "localized tones must remain on existing primary skin material index 0"
        )

    lip_weights = _vertex_group_weight(body, lip_config["source_vertex_groups"])
    lip_threshold = float(lip_config["minimum_source_weight"])
    lip_center_x, lip_front_cutoff, lip_center_z = lip_selection[
        "center_object_local_m"
    ]
    lip_radius_x, lip_radius_z = lip_selection["radii_m"]
    lip_multiplier = tuple(float(value) for value in lip_config["center_color_multiplier"])
    lip_tinted_loops = 0
    lip_maximum_weight = 0.0
    for loop_index, loop in enumerate(body.data.loops):
        vertex = body.data.vertices[loop.vertex_index]
        radius_squared = (
            (float(vertex.co.x) - lip_center_x) / lip_radius_x
        ) ** 2 + ((float(vertex.co.z) - lip_center_z) / lip_radius_z) ** 2
        if radius_squared > 1.0:
            continue
        group_weight = max(
            0.0,
            min(1.0, lip_weights.get(vertex.index, 0.0) / (lip_threshold * 2.0)),
        )
        front_weight = _smoothstep(
            0.0,
            1.0,
            (lip_front_cutoff + 0.004 - float(vertex.co.y)) / 0.012,
        )
        mask = max(0.0, 1.0 - radius_squared) ** 0.72 * group_weight * front_weight
        if mask <= 0.005:
            continue
        attribute.data[loop_index].color = _multiply_toward(
            attribute.data[loop_index].color, lip_multiplier, mask
        )
        lip_tinted_loops += 1
        lip_maximum_weight = max(lip_maximum_weight, mask)

    areola_tinted_loops: dict[str, int] = {"L": 0, "R": 0}
    areola_maximum_weights: dict[str, float] = {"L": 0.0, "R": 0.0}
    areola_multiplier = tuple(
        float(value) for value in areola_config["areola_center_color_multiplier"]
    )
    nipple_multiplier = tuple(
        float(value) for value in areola_config["nipple_core_color_multiplier"]
    )
    edge_start = float(areola_config["soft_edge_start_normalized_radius"])
    minimum_alignment = float(areola_config["minimum_front_normal_alignment"])
    for side in ("L", "R"):
        center_x, center_z = areola_selection[side]["center_object_local_m"]
        radius = float(areola_selection[side]["radius_m"])
        for loop_index, loop in enumerate(body.data.loops):
            vertex = body.data.vertices[loop.vertex_index]
            if float(vertex.normal.y) > -minimum_alignment:
                continue
            normalized_radius = math.hypot(
                float(vertex.co.x) - center_x,
                float(vertex.co.z) - center_z,
            ) / radius
            if normalized_radius >= 1.18:
                continue
            outer_weight = 1.0 - _smoothstep(edge_start, 1.18, normalized_radius)
            core_weight = math.exp(-0.5 * (normalized_radius / 0.24) ** 2)
            local_multiplier = tuple(
                areola_multiplier[channel]
                + (nipple_multiplier[channel] - areola_multiplier[channel])
                * core_weight
                for channel in range(3)
            )
            attribute.data[loop_index].color = _multiply_toward(
                attribute.data[loop_index].color,
                local_multiplier,
                outer_weight,
            )
            if outer_weight > 0.005:
                areola_tinted_loops[side] += 1
                areola_maximum_weights[side] = max(
                    areola_maximum_weights[side], outer_weight
                )
    if lip_tinted_loops < 40 or min(areola_tinted_loops.values()) < 6:
        raise KiraAppearanceBlenderV3Error(
            "localized soft skin tone coverage is too sparse: "
            f"lip={lip_tinted_loops};areola={areola_tinted_loops}"
        )
    if [int(polygon.material_index) for polygon in body.data.polygons] != material_indices_before:
        raise KiraAppearanceBlenderV3Error("localized tint changed polygon material indices")
    body.data.update()
    body["natural_lip_surface_tone"] = METHOD_ID
    body["natural_nipple_areola_surface_tone"] = METHOD_ID
    return {
        "method": "soft_localized_real_albedo_corner_tint_on_primary_skin_v3",
        "same_primary_body_mesh": True,
        "separate_lip_mesh_created": False,
        "separate_nipple_or_areola_mesh_created": False,
        "body_coordinate_change_required": False,
        "polygon_material_indices_unchanged": True,
        "existing_primary_skin_material_index": 0,
        "new_material_slot_added": False,
        "regional_tint_attribute": REGIONAL_SKIN_TINT_ATTRIBUTE,
        "lip": {
            **lip_selection,
            "material": body.data.materials[0].name,
            "material_index": 0,
            "qualitative_target_srgb_hex": str(
                lip_config["qualitative_target_srgb_hex"]
            ),
            "center_color_multiplier": list(lip_multiplier),
            "tinted_loop_count": lip_tinted_loops,
            "maximum_tint_weight": lip_maximum_weight,
            "natural_readability_not_makeup": True,
        },
        "nipple_areola": {
            "selection": areola_selection,
            "material": body.data.materials[0].name,
            "material_index": 0,
            "qualitative_target_srgb_hex": str(
                areola_config["qualitative_target_srgb_hex"]
            ),
            "areola_center_color_multiplier": list(areola_multiplier),
            "nipple_core_color_multiplier": list(nipple_multiplier),
            "tinted_loop_count": areola_tinted_loops,
            "maximum_tint_weight": areola_maximum_weights,
            "bilateral_polygon_count": sum(map(len, areola_polygons.values())),
        },
    }


def _project_face_point(tree: Any, x: float, z: float, offset_m: float) -> Vector:
    origin = Vector((float(x), -0.48, float(z)))
    hit, normal, _face, _distance = tree.ray_cast(
        origin, Vector((0.0, 1.0, 0.0)), 1.0
    )
    if hit is None or normal is None:
        raise KiraAppearanceBlenderV3Error(
            f"facial appearance projection missed at x={x:.6f},z={z:.6f}"
        )
    if normal.dot(Vector((0.0, -1.0, 0.0))) < 0.0:
        normal = -normal
    return hit + normal.normalized() * float(offset_m)


def _parent_to_head(obj: Any, armature: Any) -> None:
    if armature is None or armature.type != "ARMATURE":
        raise KiraAppearanceBlenderV3Error("facial components require an armature")
    if armature.pose.bones.get("head") is None:
        raise KiraAppearanceBlenderV3Error("head bone missing")
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = "head"
    obj.matrix_world = world


def _brow_material(config: Mapping[str, Any]) -> Any:
    brow = config["eye_surrounds"]["brow"]
    material = _material(
        str(brow["material_name"]),
        str(brow["srgb_hex"]),
        float(brow["roughness"]),
    )
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    principled = _principled(material)
    if nodes.get("Kira_Brow_Density_Noise_V3") is None:
        coordinates = nodes.new("ShaderNodeTexCoord")
        coordinates.name = "Kira_Brow_Generated_Coordinates_V3"
        noise = nodes.new("ShaderNodeTexNoise")
        noise.name = "Kira_Brow_Density_Noise_V3"
        noise.inputs["Scale"].default_value = 22.0
        noise.inputs["Detail"].default_value = 2.0
        noise.inputs["Roughness"].default_value = 0.46
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.name = "Kira_Brow_Bounded_Color_Ramp_V3"
        base = v1.srgb_hex_to_linear_rgba(str(brow["srgb_hex"]))
        ramp.color_ramp.elements[0].color = tuple(
            max(0.0, channel * 0.78) for channel in base[:3]
        ) + (1.0,)
        ramp.color_ramp.elements[1].color = tuple(
            min(1.0, channel * 1.16) for channel in base[:3]
        ) + (1.0,)
        base_input = v1._principled_input(principled, "Base Color")  # noqa: SLF001
        if base_input is None:
            raise KiraAppearanceBlenderV3Error("brow base-color socket missing")
        links.new(coordinates.outputs["Generated"], noise.inputs["Vector"])
        links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], base_input)
    material["facial_component_only"] = True
    material["scalp_hair_material"] = False
    return material


def _continuous_brow_mesh(
    *,
    name: str,
    tree: Any,
    center: Vector,
    width: float,
    height: float,
    side_sign: float,
    sample_count: int,
    material: Any,
) -> tuple[Any, dict[str, Any]]:
    topology = continuous_strip_topology(sample_count)
    vertices: list[Vector] = []
    faces: list[tuple[int, int, int, int]] = []
    thicknesses: list[float] = []
    for sample in range(sample_count):
        u = -1.0 + 2.0 * sample / (sample_count - 1)
        profile = brow_profile(u=u, side_sign=side_sign)
        x = float(center.x + u * width * 0.54)
        center_z = float(
            center.z
            + height
            * (
                0.5
                + profile["center_offset_eye_heights"]
                + (0.012 if side_sign > 0.0 else -0.004)
            )
        )
        half_thickness = float(height * profile["half_thickness_eye_heights"])
        thicknesses.append(half_thickness * 2.0)
        lower = _project_face_point(tree, x, center_z - half_thickness, 0.00034)
        upper = _project_face_point(tree, x, center_z + half_thickness, 0.00034)
        vertices.extend((lower, upper))
        if sample:
            previous = (sample - 1) * 2
            current = sample * 2
            faces.append((previous, current, current + 1, previous + 1))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(point) for point in vertices], [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(material)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj, {
        **topology,
        "minimum_thickness_m": min(thicknesses),
        "maximum_thickness_m": max(thicknesses),
        "continuous_mesh_object": True,
        "isolated_vertical_strokes": 0,
    }


def _continuous_curve(
    *,
    name: str,
    points: Sequence[Vector],
    radii: Sequence[float],
    material: Any,
    bevel_depth: float,
) -> Any:
    if len(points) < 9 or len(points) != len(radii):
        raise KiraAppearanceBlenderV3Error("continuous facial curve samples invalid")
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 3
    data.bevel_depth = float(bevel_depth)
    data.bevel_resolution = 2
    data.resolution_u = 3
    spline = data.splines.new("NURBS")
    spline.points.add(len(points) - 1)
    for target, point, radius in zip(spline.points, points, radii):
        target.co = (*point, 1.0)
        target.radius = float(radius)
    spline.order_u = min(4, len(points))
    spline.use_endpoint_u = True
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(material)
    return obj


def replace_feminine_eye_surrounds_v3(
    *,
    body: Any,
    armature: Any,
    eye_objects: Sequence[Any],
    candidate_id: str,
    config: Mapping[str, Any],
    superseded_objects: Sequence[Any] = (),
) -> tuple[list[Any], dict[str, Any]]:
    """Create continuous brows and layered lids, then remove supplied v2 parts."""

    tree = v1._world_surface_bvh(body)  # noqa: SLF001
    eye_config = config["eye_surrounds"]
    brow_material = _brow_material(config)
    lash_config = eye_config["upper_lash"]
    lid_config = eye_config["lower_lid"]
    lash_material = _material(
        str(lash_config["material_name"]),
        str(lash_config["srgb_hex"]),
        float(lash_config["roughness"]),
    )
    lid_material = _material(
        str(lid_config["material_name"]),
        str(lid_config["srgb_hex"]),
        float(lid_config["roughness"]),
    )
    created: list[Any] = []
    records: dict[str, Any] = {}
    try:
        for side in ("L", "R"):
            sclera = next(
                (
                    obj
                    for obj in eye_objects
                    if f"sclera_{side}".casefold() in obj.name.casefold()
                ),
                None,
            )
            if sclera is None:
                raise KiraAppearanceBlenderV3Error(
                    f"eye component inventory missing sclera {side}"
                )
            low, high = v1._object_bounds(sclera)  # noqa: SLF001
            center = (low + high) * 0.5
            width = float(high.x - low.x)
            height = float(high.z - low.z)
            if min(width, height) <= 0.004:
                raise KiraAppearanceBlenderV3Error("eye bounds are implausibly small")
            sign = 1.0 if center.x >= 0.0 else -1.0
            brow, brow_record = _continuous_brow_mesh(
                name=f"{candidate_id}_continuous_brow_v3_{side}",
                tree=tree,
                center=center,
                width=width,
                height=height,
                side_sign=sign,
                sample_count=int(eye_config["brow"]["sample_count"]),
                material=brow_material,
            )
            created.append(brow)

            upper_lash: list[Vector] = []
            upper_lid: list[Vector] = []
            lower_lid: list[Vector] = []
            radii: list[float] = []
            sample_count = int(lash_config["sample_count"])
            for sample in range(sample_count):
                u = -1.0 + 2.0 * sample / (sample_count - 1)
                x = float(center.x + u * width * 0.47)
                arch = 1.0 - u * u
                upper_lash.append(
                    _project_face_point(
                        tree,
                        x,
                        float(center.z + height * (0.15 + 0.15 * arch)),
                        0.00030,
                    )
                )
                upper_lid.append(
                    _project_face_point(
                        tree,
                        x,
                        float(center.z + height * (0.36 + 0.11 * arch)),
                        0.00031,
                    )
                )
                lower_lid.append(
                    _project_face_point(
                        tree,
                        x,
                        float(center.z - height * (0.16 + 0.075 * arch)),
                        0.00028,
                    )
                )
                radii.append(tapered_line_radius(u=u, minimum_fraction=0.20))
            lash = _continuous_curve(
                name=f"{candidate_id}_continuous_upper_lash_v3_{side}",
                points=upper_lash,
                radii=radii,
                material=lash_material,
                bevel_depth=max(0.00013, height * 0.0060),
            )
            crease = _continuous_curve(
                name=f"{candidate_id}_subtle_upper_lid_crease_v3_{side}",
                points=upper_lid,
                radii=radii,
                material=lid_material,
                bevel_depth=max(0.000075, height * 0.0035),
            )
            lower = _continuous_curve(
                name=f"{candidate_id}_subtle_lower_lid_v3_{side}",
                points=lower_lid,
                radii=radii,
                material=lid_material,
                bevel_depth=max(0.000065, height * 0.0030),
            )
            created.extend((lash, crease, lower))
            roles = (
                (brow, "brow"),
                (lash, "upper_lash"),
                (crease, "upper_lid"),
                (lower, "lower_lid"),
            )
            for obj, role in roles:
                obj["candidate_id"] = candidate_id
                obj["kira_appearance_delivery_v3"] = True
                obj["facial_presentation_role"] = role
                obj["scalp_hair_dependency"] = False
                obj["private_owner_review_only"] = True
                obj["runtime_activation_allowed"] = False
                _parent_to_head(obj, armature)
            records[side] = {
                "eye_width_m": width,
                "eye_height_m": height,
                "brow": {"object": brow.name, **brow_record},
                "upper_lash": {
                    "object": lash.name,
                    "continuous_spline_count": 1,
                    "sample_count": len(upper_lash),
                },
                "upper_lid_crease": {
                    "object": crease.name,
                    "continuous_spline_count": 1,
                    "sample_count": len(upper_lid),
                },
                "lower_lid": {
                    "object": lower.name,
                    "continuous_spline_count": 1,
                    "sample_count": len(lower_lid),
                },
            }
    except Exception:
        for obj in created:
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        raise

    removed: list[str] = []
    replaceable_roles = {"brow", "upper_lash", "upper_lid", "lower_lid"}
    for obj in list(superseded_objects):
        if obj is None or obj.name not in bpy.data.objects:
            continue
        if str(obj.get("facial_presentation_role", "")) not in replaceable_roles:
            continue
        if str(obj.get("candidate_id", "")) not in {"", candidate_id}:
            raise KiraAppearanceBlenderV3Error(
                f"refusing to remove another candidate's facial component: {obj.name}"
            )
        removed.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)
    return created, {
        "method": "continuous_conformal_brows_and_layered_eye_surrounds_v3",
        "new_object_count": len(created),
        "brow_object_count": 2,
        "brow_connected_component_count": 2,
        "brow_isolated_vertical_stroke_count": 0,
        "upper_lash_object_count": 2,
        "upper_lid_crease_object_count": 2,
        "lower_lid_object_count": 2,
        "superseded_v2_object_count": len(removed),
        "superseded_v2_objects_removed": removed,
        "direct_head_bone_parenting": True,
        "scalp_hair_dependency": False,
        "identity_geometry_substitute": False,
        "records": records,
        "visual_requalification_required": True,
    }


def apply_kira_appearance_delivery_v3(
    *,
    body: Any,
    armature: Any,
    eye_objects: Sequence[Any],
    candidate_id: str,
    project_root: Path = PROJECT_ROOT,
    superseded_facial_objects: Sequence[Any] = (),
) -> tuple[list[Any], dict[str, Any]]:
    """Apply all v3 appearance components without changing body coordinates."""

    config, contract = load_validated_kira_appearance_delivery_v3(project_root)
    if body is None or body.type != "MESH" or not bool(body.get("primary_surface")):
        raise KiraAppearanceBlenderV3Error("appearance delivery requires primary mesh")
    coordinates_before = _coordinate_sha256(body)
    vertex_count_before = len(body.data.vertices)
    polygon_count_before = len(body.data.polygons)
    image_names_before = set(bpy.data.images.keys())
    scalp_materials_before = {
        int(polygon.material_index)
        for polygon in body.data.polygons
        if any(
            float(body.data.vertices[index].co.z)
            >= max(float(vertex.co.z) for vertex in body.data.vertices) * 0.94
            for index in polygon.vertices
        )
    }
    regional_skin = install_regional_skin_tint_v3(body, config)
    surface_tones = assign_natural_surface_tones_v3(body, config)
    facial_objects, eye_surrounds = replace_feminine_eye_surrounds_v3(
        body=body,
        armature=armature,
        eye_objects=eye_objects,
        candidate_id=candidate_id,
        config=config,
        superseded_objects=superseded_facial_objects,
    )
    coordinates_after = _coordinate_sha256(body)
    if coordinates_after != coordinates_before:
        raise KiraAppearanceBlenderV3Error("appearance adapter changed body coordinates")
    if (
        len(body.data.vertices) != vertex_count_before
        or len(body.data.polygons) != polygon_count_before
    ):
        raise KiraAppearanceBlenderV3Error("appearance adapter changed body topology")
    if set(bpy.data.images.keys()) != image_names_before:
        raise KiraAppearanceBlenderV3Error("appearance adapter added an image texture")
    z_max = max(float(vertex.co.z) for vertex in body.data.vertices)
    scalp_materials_after = {
        int(polygon.material_index)
        for polygon in body.data.polygons
        if any(
            float(body.data.vertices[index].co.z) >= z_max * 0.94
            for index in polygon.vertices
        )
    }
    if scalp_materials_after != scalp_materials_before or scalp_materials_after != {0}:
        raise KiraAppearanceBlenderV3Error("clean primary-skin scalp material changed")
    forbidden_tokens = ("scalp_hair", "hair_groom", "hair_master", "responsive_groom")
    if any(
        any(token in obj.name.casefold() for token in forbidden_tokens)
        for obj in facial_objects
    ):
        raise KiraAppearanceBlenderV3Error("facial component crossed scalp-hair boundary")
    body["kira_appearance_delivery_method"] = METHOD_ID
    body["complete_natural_bald_scalp"] = True
    body["scalp_hair_dependency_allowed"] = False
    report = {
        "method_id": METHOD_ID,
        "contract": contract,
        "regional_skin": regional_skin,
        "same_surface_tones": surface_tones,
        "eye_surrounds": eye_surrounds,
        "body_coordinate_sha256_before": coordinates_before,
        "body_coordinate_sha256_after": coordinates_after,
        "body_coordinates_unchanged": True,
        "body_vertex_count_before_after": [vertex_count_before, len(body.data.vertices)],
        "body_polygon_count_before_after": [polygon_count_before, len(body.data.polygons)],
        "rig_or_deform_weight_change": False,
        "image_textures_added": False,
        "scalp_material_indices_before": sorted(scalp_materials_before),
        "scalp_material_indices_after": sorted(scalp_materials_after),
        "clean_bald_scalp_preserved": True,
        "scalp_hair_dependency_count": 0,
        "runtime_activation_allowed": False,
        "glb_export_allowed": False,
        "identity_match_claim_allowed": False,
        "visual_requalification_required": True,
    }
    body["kira_appearance_delivery_v3_report"] = json.dumps(report, sort_keys=True)
    return facial_objects, report


__all__ = [
    "KiraAppearanceBlenderV3Error",
    "METHOD_ID",
    "apply_kira_appearance_delivery_v3",
    "assign_natural_surface_tones_v3",
    "install_regional_skin_tint_v3",
    "replace_feminine_eye_surrounds_v3",
]
