#!/usr/bin/env python3
"""Build Kira's isolated temporary-functional-body review candidate.

This worker is deliberately private and non-runtime.  It derives a generic
adult-female body from the locally enrolled BlackProject CC BY 4.0 foundation,
preserves that source's native 188-joint rig, welds the source body components,
authors bounded review actions, and writes evidence derived from the authored
scene.  It does not select, bind, activate, or replace Kira's current body.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
import blender_author_kira_r7_adult_surface_trial as audit_helpers  # noqa: E402
import blender_build_kira_temporary_functional_body as procedural_review  # noqa: E402


SOURCE_SHA256 = "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df"
REQUEST_SHA256 = "9c694741772699bb476e7e24fdd0e0dbfecf186be3fdfd5d8a77ac3035ec006b"
AUTHORITY_SHA256 = "TODO_AUTHORITY_SHA"
TARGET_HEIGHT_M = 1.651
WELD_TOLERANCE_M = 1e-6

PRIMARY_SURFACE_MESHES = (
    "Ariel_Mesh_Torso_0",
    "Ariel_Mesh_Arms_0",
    "Ariel_Mesh_Legs_0",
    "Ariel_Mesh_Genitalia_0",
    "Ariel_Mesh_Face_0",
    "Ariel_Mesh_Ears_0",
)

KEEP_MESHES = (
    *PRIMARY_SURFACE_MESHES,
    "Ariel_Mesh_Lips_0",
    "Ariel_Mesh_Teeth_0",
    "Ariel_Mesh_EyeSocket_0",
    "Ariel_Mesh_Mouth_0",
    "Ariel_Mesh_Pupils_0",
    "Ariel_Mesh_EyeMoisture_0",
    "Ariel_Mesh_Cornea_0",
    "Ariel_Mesh_Irises_0",
    "Ariel_Mesh_Sclera_0",
    "Ariel_Mesh_Fingernails_0",
    "Ariel_Mesh_Toenails_0",
    "Hair_Hair Thin_0",
    "Hair_Hair Mid_0",
    "Hair_Hair Long_0",
    "Eye_Brows_Brows02_0.001",
    "Eye_Lahes_EyeMoisture_0",
)

MATERIAL_TARGETS = {
    "skin": (0.79, 0.57, 0.45, 1.0),
    "skin_warm": (0.72, 0.45, 0.38, 1.0),
    "lip": (0.48, 0.16, 0.17, 1.0),
    "nail": (0.72, 0.43, 0.42, 1.0),
    "iris": (0.19, 0.075, 0.025, 1.0),
    "pupil": (0.005, 0.004, 0.003, 1.0),
    "sclera": (0.73, 0.68, 0.63, 1.0),
    "mouth": (0.22, 0.035, 0.035, 1.0),
    "teeth": (0.83, 0.78, 0.68, 1.0),
    "hair": (0.006, 0.004, 0.003, 1.0),
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_material(
    name: str,
    rgba: tuple[float, float, float, float],
    *,
    roughness: float,
    metallic: float = 0.0,
    transmission: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = rgba
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = rgba
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    if "Transmission Weight" in shader.inputs:
        shader.inputs["Transmission Weight"].default_value = transmission
    elif "Transmission" in shader.inputs:
        shader.inputs["Transmission"].default_value = transmission
    if "IOR" in shader.inputs:
        shader.inputs["IOR"].default_value = 1.42
    material.node_tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material


def replace_object_material(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.material_index = 0


def body_world_points(objects: list[bpy.types.Object]) -> list[Vector]:
    return [
        obj.matrix_world @ vertex.co
        for obj in objects
        if obj.type == "MESH"
        for vertex in obj.data.vertices
    ]


def roots_for(objects: list[bpy.types.Object]) -> list[bpy.types.Object]:
    object_set = set(objects)
    return [obj for obj in objects if obj.parent not in object_set]


def scale_to_height_and_floor(
    imported: list[bpy.types.Object],
    body_objects: list[bpy.types.Object],
    target_height_m: float,
) -> dict[str, float]:
    before = body_world_points(body_objects)
    low_before = min(point.z for point in before)
    high_before = max(point.z for point in before)
    source_height = high_before - low_before
    scale = target_height_m / source_height
    roots = roots_for(imported)
    for root in roots:
        root.scale = tuple(value * scale for value in root.scale)
    bpy.context.view_layer.update()
    after_scale = body_world_points(body_objects)
    floor = min(point.z for point in after_scale)
    for root in roots:
        root.location.z -= floor
    bpy.context.view_layer.update()
    final = body_world_points(body_objects)
    return {
        "source_body_height_m": round(source_height, 9),
        "uniform_scale": round(scale, 9),
        "floor_offset_m": round(-floor, 9),
        "final_body_height_m": round(max(point.z for point in final) - min(point.z for point in final), 9),
        "final_floor_z_m": round(min(point.z for point in final), 9),
    }


def apply_bounded_parameter_morph(obj: bpy.types.Object) -> dict[str, object]:
    """Apply only the requested -4% waist / +2% hip bounded generic morph."""

    inverse = obj.matrix_world.inverted()
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    low = min(point.z for point in points)
    high = max(point.z for point in points)
    height = high - low
    changed = 0
    maximum_delta = 0.0
    deform_group_indices = {
        group.index
        for group in obj.vertex_groups
        if group.name.startswith(
            (
                "pelvis_",
                "hip_",
                "abdomenLower_",
                "abdomenUpper_",
                "chestLower_",
                "chestUpper_",
                "lPectoral_",
                "rPectoral_",
            )
        )
    }
    for vertex in obj.data.vertices:
        region_weight = min(
            1.0,
            sum(
                float(assignment.weight)
                for assignment in vertex.groups
                if assignment.group in deform_group_indices
            ),
        )
        if region_weight <= 1e-5:
            continue
        world = obj.matrix_world @ vertex.co
        normalized_z = (world.z - low) / max(height, 1e-9)
        waist_bump = math.exp(-((normalized_z - 0.59) / 0.075) ** 2)
        hip_bump = math.exp(-((normalized_z - 0.48) / 0.085) ** 2)
        factor = 1.0 + region_weight * (-0.04 * waist_bump + 0.02 * hip_bump)
        original = world.copy()
        world.x *= factor
        delta = (world - original).length
        if delta > 1e-9:
            changed += 1
            maximum_delta = max(maximum_delta, delta)
            vertex.co = inverse @ world
    obj.data.update()
    return {
        "method": "bounded_symmetric_world_x_profile",
        "waist_abdomen_requested": -0.04,
        "hips_pelvis_requested": 0.02,
        "body_region_filter": "pelvis/hip/abdomen/chest/pectoral vertex-group influence",
        "changed_vertices": changed,
        "maximum_vertex_delta_m": round(maximum_delta, 9),
        "face_landmarks_changed": False,
        "identity_claim": "generic_non_identifiable_adult_female",
    }


def straighten_source_groom(
    body: bpy.types.Object,
    hair_objects: list[bpy.types.Object],
) -> dict[str, object]:
    """Reduce the licensed groom's lower curl into straight layered locks."""

    body_points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    low = Vector(tuple(min(point[axis] for point in body_points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in body_points) for axis in range(3)))
    height = high.z - low.z
    crown = high.z
    transition_start = crown - height * 0.025
    transition_end = crown - height * 0.30
    changed = 0
    maximum_delta = 0.0
    sum_before = 0.0
    sum_after = 0.0
    component_counts: dict[str, int] = {}
    processed_components = 0
    for obj in hair_objects:
        adjacency: list[list[int]] = [[] for _ in obj.data.vertices]
        for edge in obj.data.edges:
            a, b = map(int, edge.vertices)
            adjacency[a].append(b)
            adjacency[b].append(a)
        unseen = set(range(len(obj.data.vertices)))
        components: list[list[int]] = []
        while unseen:
            start = unseen.pop()
            stack = [start]
            component = [start]
            while stack:
                current = stack.pop()
                for neighbor in adjacency[current]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        stack.append(neighbor)
                        component.append(neighbor)
            components.append(component)
        component_counts[obj.data.name] = len(components)
        inverse = obj.matrix_world.inverted()
        for component in components:
            if len(component) < 6:
                continue
            component_points = [
                obj.matrix_world @ obj.data.vertices[index].co
                for index in component
            ]
            component_low = min(point.z for point in component_points)
            component_high = max(point.z for point in component_points)
            if component_high - component_low < height * 0.035:
                continue
            sample_count = max(3, min(24, len(component) // 14))
            ordered = sorted(component_points, key=lambda point: point.z)
            bottom = ordered[:sample_count]
            top = ordered[-sample_count:]
            root = Vector(
                (
                    sum(point.x for point in top) / len(top),
                    sum(point.y for point in top) / len(top),
                    component_high,
                )
            )
            tip = Vector(
                (
                    sum(point.x for point in bottom) / len(bottom),
                    sum(point.y for point in bottom) / len(bottom),
                    component_low,
                )
            )
            processed_components += 1
            for index in component:
                vertex = obj.data.vertices[index]
                world = obj.matrix_world @ vertex.co
                if world.z >= transition_start:
                    continue
                t = min(
                    1.0,
                    max(
                        0.0,
                        (component_high - world.z)
                        / max(component_high - component_low, 1e-9),
                    ),
                )
                target = root.lerp(tip, t)
                target.z = world.z
                ramp = min(
                    1.0,
                    max(
                        0.0,
                        (transition_start - world.z)
                        / max(transition_start - transition_end, 1e-9),
                    ),
                )
                blend = 0.96 * ramp
                before_error = math.hypot(world.x - target.x, world.y - target.y)
                updated = world.lerp(target, blend)
                after_error = math.hypot(updated.x - target.x, updated.y - target.y)
                delta = (updated - world).length
                if delta > 1e-9:
                    vertex.co = inverse @ updated
                    changed += 1
                    maximum_delta = max(maximum_delta, delta)
                    sum_before += before_error
                    sum_after += after_error
        obj.data.update()
        obj["removable_review_hair"] = True
        obj["runtime_hair_system_complete"] = False
        obj["straightening_method"] = "bounded connected-lock linear fit"
    return {
        "method": "bounded_connected_lock_linear_fit",
        "source_components": [obj.data.name for obj in hair_objects],
        "cap_or_crown_vertices_changed": False,
        "connected_component_counts": component_counts,
        "processed_vertical_components": processed_components,
        "changed_vertices": changed,
        "maximum_vertex_delta_m_before_global_scale": round(maximum_delta, 9),
        "mean_radial_deviation_before_m": round(sum_before / max(changed, 1), 9),
        "mean_radial_deviation_after_m": round(sum_after / max(changed, 1), 9),
        "removable_static_review_component": True,
        "runtime_grooming_or_secondary_motion_proven": False,
    }


def create_procedural_straight_review_groom(
    body: bpy.types.Object,
    armature: bpy.types.Object,
    material: bpy.types.Material,
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    """Author a removable straight review groom on this source's head bone."""

    points = audit_helpers.evaluated_vertices(body)
    box = audit_helpers.bounds(points)
    low = Vector(box["low"])
    high = Vector(box["high"])
    height = float(high.z - low.z)
    center = Vector(
        (
            float((low.x + high.x) * 0.5),
            float((low.y + high.y) * 0.5 + height * 0.006),
            float(high.z - height * 0.084),
        )
    )
    # The reusable curve helper invokes an object conversion.  The body must
    # not remain selected or Blender will also bake its armature modifier,
    # which creates a frozen T-pose and false zero-delta deformation pass.
    bpy.ops.object.select_all(action="DESELECT")
    cap = procedural_review.create_cap_mesh(center, height, material)
    for vertex in cap.data.vertices:
        vertex.co.x = center.x + (vertex.co.x - center.x) * 1.04
        vertex.co.y = center.y + (vertex.co.y - center.y) * 1.04
        vertex.co.z = center.z + (vertex.co.z - center.z) * 0.74 + height * 0.024
    cap.data.update()
    bpy.ops.object.select_all(action="DESELECT")
    strands = procedural_review.create_straight_strand_groom(center, height, material)
    for vertex in strands.data.vertices:
        vertex.co.z += height * 0.024
    strands.data.update()
    head_bone = "head_091"
    if head_bone not in armature.data.bones:
        raise ValueError(f"required review-groom head bone absent: {head_bone}")
    for obj in (cap, strands):
        world = obj.matrix_world.copy()
        obj.parent = armature
        obj.parent_type = "BONE"
        obj.parent_bone = head_bone
        obj.matrix_world = world
        obj["removable_review_hair"] = True
        obj["runtime_hair_system_complete"] = False
        obj["actual_black_hair_geometry"] = True
    return [cap, strands], {
        "color": "black",
        "texture": "straight",
        "review_style": "simple removable shoulder-clear bob",
        "component_names": [cap.name, strands.name],
        "head_bone_binding": head_bone,
        "removable": True,
        "procedurally_authored_from_request": True,
        "curl_heavy_source_groom_excluded": True,
        "opaque_source_scalp_cap_excluded": True,
        "replacement_cap_vertical_scale": 0.74,
        "replacement_cap_xy_scale": 1.04,
        "replacement_groom_vertical_offset_m": round(height * 0.024, 9),
        "body_armature_modifier_bake_prevented_by_selection_isolation": True,
        "runtime_grooming_growth_wetness_or_dynamics_complete": False,
        "truth_note": "Static removable review groom only; later production hair remains a separate stage.",
    }


def repair_pelvis_midline(body: bpy.types.Object) -> dict[str, object]:
    """Pair mirrored seam vertices before welding; never flatten a whole band."""

    points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    low = min(point.z for point in points)
    high = max(point.z for point in points)
    height = high - low
    z_low = low + height * 0.425
    z_high = low + height * 0.585
    x_threshold = height * 0.0033
    match_tolerance = height * 0.0010
    relevant_groups = {
        group.index
        for group in body.vertex_groups
        if group.name.startswith(
            (
                "pelvis_",
                "hip_",
                "abdomenLower_",
            )
        )
    }
    side_groups = {
        group.index
        for group in body.vertex_groups
        if group.name.startswith(("lThigh", "rThigh"))
    }
    inverse = body.matrix_world.inverted()
    positive: list[tuple[int, Vector]] = []
    negative: list[tuple[int, Vector]] = []
    for vertex in body.data.vertices:
        world = body.matrix_world @ vertex.co
        if not (z_low <= world.z <= z_high and abs(world.x) <= x_threshold):
            continue
        center_influence = sum(
            assignment.weight
            for assignment in vertex.groups
            if assignment.group in relevant_groups
        )
        side_influence = sum(
            assignment.weight
            for assignment in vertex.groups
            if assignment.group in side_groups
        )
        if center_influence <= 0.10 or side_influence >= 0.70:
            continue
        if world.x > 1e-8:
            positive.append((vertex.index, world))
        elif world.x < -1e-8:
            negative.append((vertex.index, world))
    tree = KDTree(len(negative))
    for index, (_, world) in enumerate(negative):
        tree.insert(Vector((-world.x, world.y, world.z)), index)
    tree.balance()
    paired_negative: set[int] = set()
    pairs: list[tuple[int, int, float]] = []
    maximum_shift = 0.0
    for positive_index, positive_world in positive:
        if not negative:
            break
        _, tree_index, distance = tree.find(positive_world)
        if tree_index in paired_negative or distance > match_tolerance:
            continue
        negative_index, negative_world = negative[tree_index]
        paired_negative.add(tree_index)
        maximum_shift = max(
            maximum_shift,
            abs(positive_world.x),
            abs(negative_world.x),
        )
        target = Vector(
            (
                0.0,
                (positive_world.y + negative_world.y) * 0.5,
                (positive_world.z + negative_world.z) * 0.5,
            )
        )
        body.data.vertices[positive_index].co = inverse @ target
        body.data.vertices[negative_index].co = inverse @ target
        pairs.append((positive_index, negative_index, float(distance)))
    body.data.update()
    before = len(body.data.vertices)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.remove_doubles(
        bm,
        verts=list(bm.verts),
        dist=max(1e-8, height * 1e-8),
    )
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    return {
        "method": "bounded_mirrored_pelvis_center_seam_pair_then_exact_weld",
        "normalized_z_range": [0.425, 0.585],
        "world_x_threshold_m_before_global_scale": round(x_threshold, 9),
        "mirror_match_tolerance_m_before_global_scale": round(match_tolerance, 9),
        "positive_candidate_count": len(positive),
        "negative_candidate_count": len(negative),
        "paired_vertex_pair_count": len(pairs),
        "paired_vertex_count": len(pairs) * 2,
        "maximum_mirror_pair_residual_m": round(max((pair[2] for pair in pairs), default=0.0), 9),
        "maximum_world_x_shift_m_before_global_scale": round(maximum_shift, 9),
        "vertex_count_before_final_weld": before,
        "vertex_count_after_final_weld": len(body.data.vertices),
        "vertices_merged_by_final_weld": before - len(body.data.vertices),
        "purpose": "repair only mirrored pelvis/back/perineal centerline pairs localized by the independent R2 audit; unpaired vertices remain untouched",
        "visual_and_independent_intersection_reaudit_required": True,
    }


def shorten_fingernails(obj: bpy.types.Object) -> dict[str, object]:
    """Shorten each nail plate toward its hand-side root without detaching it."""

    adjacency: list[list[int]] = [[] for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = map(int, edge.vertices)
        adjacency[a].append(b)
        adjacency[b].append(a)
    unseen = set(range(len(obj.data.vertices)))
    components: list[list[int]] = []
    while unseen:
        start = unseen.pop()
        stack = [start]
        component = [start]
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
                    component.append(neighbor)
        components.append(component)
    inverse = obj.matrix_world.inverted()
    changed = 0
    maximum_delta = 0.0
    component_records = []
    for component in components:
        points = [obj.matrix_world @ obj.data.vertices[index].co for index in component]
        center_x = sum(point.x for point in points) / len(points)
        positive_hand = center_x >= 0.0
        anchor_x = min(point.x for point in points) if positive_hand else max(point.x for point in points)
        before_length = max(point.x for point in points) - min(point.x for point in points)
        for index in component:
            vertex = obj.data.vertices[index]
            world = obj.matrix_world @ vertex.co
            updated = world.copy()
            # The source plates extend past the fingertip in a neutral pose.
            # Preserve the proximal/root side and shorten only the free end.
            updated.x = anchor_x + (world.x - anchor_x) * 0.30
            delta = (updated - world).length
            if delta > 1e-9:
                vertex.co = inverse @ updated
                changed += 1
                maximum_delta = max(maximum_delta, delta)
        component_records.append(
            {
                "vertex_count": len(component),
                "hand_side": "left_positive_x" if positive_hand else "right_negative_x",
                "length_before_m": round(before_length, 9),
                "length_after_m": round(before_length * 0.30, 9),
            }
        )
    obj.data.update()
    obj["ordinary_attached_review_nails"] = True
    obj["nail_length_factor"] = 0.30
    return {
        "method": "per_connected_plate_shorten_toward_hand_side_root",
        "component_count": len(components),
        "changed_vertices": changed,
        "maximum_vertex_delta_m_before_global_scale": round(maximum_delta, 9),
        "length_factor": 0.30,
        "components": component_records,
        "owner_visual_attachment_review_required": True,
    }


def raise_big_toenails(obj: bpy.types.Object) -> dict[str, object]:
    """Move only the two largest nail plates onto the dorsal big-toe surface."""

    adjacency: list[list[int]] = [[] for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = map(int, edge.vertices)
        adjacency[a].append(b)
        adjacency[b].append(a)
    unseen = set(range(len(obj.data.vertices)))
    components: list[list[int]] = []
    while unseen:
        start = unseen.pop()
        stack = [start]
        component = [start]
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
                    component.append(neighbor)
        components.append(component)
    ranked: list[tuple[float, list[int], dict[str, object]]] = []
    for component in components:
        points = [obj.matrix_world @ obj.data.vertices[index].co for index in component]
        low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
        high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
        size = high - low
        score = float(max(size.x, size.y) * max(min(size.x, size.y), 1e-9))
        ranked.append(
            (
                score,
                component,
                {
                    "vertex_count": len(component),
                    "bounds_low_before_m": [round(float(value), 9) for value in low],
                    "bounds_high_before_m": [round(float(value), 9) for value in high],
                },
            )
        )
    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = ranked[:2]
    shift = Vector((0.0, 0.0, 0.008))
    inverse = obj.matrix_world.inverted()
    selected_records: list[dict[str, object]] = []
    for _, component, record in selected:
        for index in component:
            vertex = obj.data.vertices[index]
            vertex.co = inverse @ ((obj.matrix_world @ vertex.co) + shift)
        record["dorsal_shift_before_global_scale_m"] = round(float(shift.z), 9)
        selected_records.append(record)
    obj.data.update()
    obj["ordinary_attached_review_toenails"] = True
    obj["big_toenail_dorsal_shift_before_global_scale_m"] = float(shift.z)
    return {
        "method": "two_largest_connected_nail_plates_dorsal_translation",
        "component_count": len(components),
        "selected_big_toenail_component_count": len(selected),
        "dorsal_shift_before_global_scale_m": round(float(shift.z), 9),
        "selected_components": selected_records,
        "owner_visual_attachment_review_required": True,
    }


def ordered_boundary_cycles(obj: bpy.types.Object) -> list[list[int]]:
    """Return ordered closed boundary cycles for one mesh."""

    edge_use: dict[tuple[int, int], int] = {}
    for polygon in obj.data.polygons:
        vertices = list(map(int, polygon.vertices))
        for index, a in enumerate(vertices):
            b = vertices[(index + 1) % len(vertices)]
            edge = tuple(sorted((a, b)))
            edge_use[edge] = edge_use.get(edge, 0) + 1
    boundary_edges = {edge for edge, count in edge_use.items() if count == 1}
    adjacency: dict[int, list[int]] = {}
    for a, b in boundary_edges:
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    if any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise ValueError(f"{obj.data.name} boundary is not a set of closed cycles")
    remaining = set(boundary_edges)
    cycles: list[list[int]] = []
    while remaining:
        first_edge = min(remaining)
        start = first_edge[0]
        previous = None
        current = start
        cycle: list[int] = []
        while True:
            cycle.append(current)
            neighbors = adjacency[current]
            if previous is None:
                next_vertex = min(neighbors)
            else:
                next_vertex = neighbors[0] if neighbors[0] != previous else neighbors[1]
            edge = tuple(sorted((current, next_vertex)))
            if edge not in remaining:
                if next_vertex == start:
                    break
                alternate = neighbors[1] if next_vertex == neighbors[0] else neighbors[0]
                alternate_edge = tuple(sorted((current, alternate)))
                if alternate_edge not in remaining:
                    raise ValueError(f"could not traverse {obj.data.name} boundary cycle")
                next_vertex = alternate
                edge = alternate_edge
            remaining.remove(edge)
            previous, current = current, next_vertex
            if current == start:
                break
        cycles.append(cycle)
    return sorted(cycles, key=len, reverse=True)


def remove_base_faces_under_adult_patch(
    base: bpy.types.Object,
    adult: bpy.types.Object,
) -> dict[str, object]:
    """Remove the exact base-surface island replaced by the licensed patch.

    The enrolled source patch has one 34-vertex boundary cycle whose vertices
    exactly duplicate vertices on the base body.  Treat that cycle as a cut,
    remove the smaller face island on its inside, then let the later exact
    weld join the patch to the retained boundary.  This avoids keeping the
    hidden underlying pelvis faces that caused hundreds of intersections.
    """

    cycles = ordered_boundary_cycles(adult)
    if len(cycles) != 1 or len(cycles[0]) != 34:
        raise ValueError(
            "licensed adult patch no longer exposes the reviewed single "
            f"34-vertex boundary: {[len(cycle) for cycle in cycles]}"
        )
    adult_cycle = cycles[0]
    base_points = [base.matrix_world @ vertex.co for vertex in base.data.vertices]
    tree = KDTree(len(base_points))
    for index, point in enumerate(base_points):
        tree.insert(point, index)
    tree.balance()
    mapped_cycle: list[int] = []
    distances: list[float] = []
    for adult_index in adult_cycle:
        point = adult.matrix_world @ adult.data.vertices[adult_index].co
        _nearest, base_index, distance = tree.find(point)
        mapped_cycle.append(int(base_index))
        distances.append(float(distance))
    if len(set(mapped_cycle)) != len(mapped_cycle) or max(distances) > 1e-7:
        raise ValueError(
            "adult patch boundary does not map one-to-one onto the base body: "
            f"unique={len(set(mapped_cycle))}/{len(mapped_cycle)} "
            f"maximum_distance={max(distances):.9g}"
        )
    cut_edges = {
        tuple(sorted((mapped_cycle[index], mapped_cycle[(index + 1) % len(mapped_cycle)])))
        for index in range(len(mapped_cycle))
    }
    base_edge_set = {
        tuple(sorted(map(int, edge.vertices)))
        for edge in base.data.edges
    }
    missing_edges = sorted(cut_edges - base_edge_set)
    if missing_edges:
        raise ValueError(
            f"{len(missing_edges)} mapped adult boundary edges are absent from the base surface"
        )

    edge_faces: dict[tuple[int, int], list[int]] = {}
    for polygon in base.data.polygons:
        vertices = list(map(int, polygon.vertices))
        for index, a in enumerate(vertices):
            b = vertices[(index + 1) % len(vertices)]
            edge_faces.setdefault(tuple(sorted((a, b))), []).append(polygon.index)
    open_cut_edges = [edge for edge in cut_edges if len(edge_faces.get(edge, [])) == 1]
    if len(open_cut_edges) == len(cut_edges):
        return {
            "method": "exact_open_boundary_fill",
            "adult_boundary_cycle_count": len(cycles),
            "adult_boundary_vertex_count": len(adult_cycle),
            "maximum_boundary_match_distance_m": round(max(distances), 12),
            "all_boundary_edges_present_on_base": True,
            "all_base_interface_edges_are_open_boundary_edges": True,
            "removed_base_face_count": 0,
            "removed_base_interior_vertex_count": 0,
            "retained_boundary_vertex_count": len(set(mapped_cycle)),
            "purpose": "fill the source body's existing 34-vertex adult-region opening; there is no hidden base face island under this licensed patch",
        }
    if open_cut_edges:
        raise ValueError(
            "adult interface is neither a complete open boundary nor a closed "
            f"replacement cycle: open_edges={len(open_cut_edges)}/{len(cut_edges)}"
        )
    neighbors: list[set[int]] = [set() for _ in base.data.polygons]
    for edge, faces in edge_faces.items():
        if edge in cut_edges or len(faces) != 2:
            continue
        a, b = faces
        neighbors[a].add(b)
        neighbors[b].add(a)
    unseen = set(range(len(base.data.polygons)))
    face_components: list[list[int]] = []
    face_component_index: dict[int, int] = {}
    while unseen:
        start = unseen.pop()
        stack = [start]
        component = [start]
        while stack:
            current = stack.pop()
            for neighbor in neighbors[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
                    component.append(neighbor)
        component_index = len(face_components)
        for face_index in component:
            face_component_index[face_index] = component_index
        face_components.append(component)

    adjacent_components: set[int] = set()
    for edge in cut_edges:
        for face_index in edge_faces.get(edge, []):
            adjacent_components.add(face_component_index[face_index])
    if len(adjacent_components) != 2:
        raise ValueError(
            "adult boundary did not split the base into exactly two adjacent "
            f"face regions: adjacent_components={sorted(adjacent_components)} "
            f"all_sizes={sorted((len(component) for component in face_components))}"
        )
    inside_component_index = min(adjacent_components, key=lambda index: len(face_components[index]))
    outside_component_index = max(adjacent_components, key=lambda index: len(face_components[index]))
    inside_faces = set(face_components[inside_component_index])
    outside_faces = set(face_components[outside_component_index])
    if len(inside_faces) >= len(outside_faces) or len(inside_faces) > len(base.data.polygons) * 0.08:
        raise ValueError(
            "bounded adult replacement region is not the expected smaller island: "
            f"inside={len(inside_faces)} outside={len(outside_faces)}"
        )
    inside_vertices = {
        int(vertex)
        for face_index in inside_faces
        for vertex in base.data.polygons[face_index].vertices
    }
    retained_vertices = {
        int(vertex)
        for polygon in base.data.polygons
        if polygon.index not in inside_faces
        for vertex in polygon.vertices
    }
    removable_interior_vertices = inside_vertices - retained_vertices

    bm = bmesh.new()
    bm.from_mesh(base.data)
    bm.faces.ensure_lookup_table()
    faces_to_delete = [bm.faces[index] for index in sorted(inside_faces)]
    bmesh.ops.delete(bm, geom=faces_to_delete, context="FACES_ONLY")
    bm.verts.ensure_lookup_table()
    verts_to_delete = [
        bm.verts[index]
        for index in sorted(removable_interior_vertices)
        if index < len(bm.verts)
    ]
    if verts_to_delete:
        bmesh.ops.delete(bm, geom=verts_to_delete, context="VERTS")
    bm.to_mesh(base.data)
    bm.free()
    base.data.update()
    return {
        "method": "exact_matching_boundary_replacement",
        "adult_boundary_cycle_count": len(cycles),
        "adult_boundary_vertex_count": len(adult_cycle),
        "maximum_boundary_match_distance_m": round(max(distances), 12),
        "all_boundary_edges_present_on_base": True,
        "base_face_components_after_virtual_cut": sorted(
            (len(component) for component in face_components)
        ),
        "removed_base_face_count": len(inside_faces),
        "removed_base_interior_vertex_count": len(removable_interior_vertices),
        "retained_boundary_vertex_count": len(set(mapped_cycle)),
        "purpose": "replace the source's simplified underlying pelvis faces with its licensed adult surface patch instead of retaining two intersecting layers",
    }


def join_and_weld(
    by_mesh_name: dict[str, bpy.types.Object],
    armature: bpy.types.Object,
) -> tuple[bpy.types.Object, dict[str, object]]:
    sources = [by_mesh_name[name] for name in PRIMARY_SURFACE_MESHES]
    adult = by_mesh_name["Ariel_Mesh_Genitalia_0"]
    base_sources = [
        by_mesh_name[name]
        for name in PRIMARY_SURFACE_MESHES
        if name != "Ariel_Mesh_Genitalia_0"
    ]
    source_vertices = sum(len(obj.data.vertices) for obj in sources)
    source_faces = sum(len(obj.data.polygons) for obj in sources)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in base_sources:
        obj.hide_viewport = False
        obj.hide_set(False)
        obj.select_set(True)
    active = base_sources[0]
    bpy.context.view_layer.objects.active = active
    bpy.ops.object.join()
    body = active
    before_base_weld = len(body.data.vertices)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=WELD_TOLERANCE_M)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    base_vertices_after_weld = len(body.data.vertices)
    adult_replacement = remove_base_faces_under_adult_patch(body, adult)
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    adult.hide_viewport = False
    adult.hide_set(False)
    adult.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    body.name = "Kira_Temporary_Functional_Body_Primary_Surface"
    body.data.name = "Kira_Temporary_Functional_Body_Primary_Surface_Mesh"
    body["rapid_body_primary_surface"] = True
    body["candidate_id"] = "kira_temporary_functional_body_20260730"
    body["adult_status"] = "adult"
    body["body_class"] = "adult_female"
    body["owner_approved"] = False
    body["runtime_assignment_allowed"] = False
    body["source_sha256"] = SOURCE_SHA256
    body["source_license"] = "CC BY 4.0"
    before_weld = len(body.data.vertices)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=WELD_TOLERANCE_M)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    for polygon in body.data.polygons:
        polygon.use_smooth = True
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
    body.data.update()
    modifier = next((item for item in body.modifiers if item.type == "ARMATURE"), None)
    if modifier is None:
        modifier = body.modifiers.new("KIRA_TFB_NATIVE_188_RIG", "ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = True
    return body, {
        "source_meshes": list(PRIMARY_SURFACE_MESHES),
        "source_vertex_total": source_vertices,
        "source_polygon_total": source_faces,
        "joined_vertex_total_before_weld": before_weld,
        "vertex_total_after_weld": len(body.data.vertices),
        "vertices_merged": before_weld - len(body.data.vertices),
        "base_joined_vertex_total_before_weld": before_base_weld,
        "base_vertex_total_after_weld": base_vertices_after_weld,
        "adult_patch_replacement": adult_replacement,
        "weld_tolerance_m": WELD_TOLERANCE_M,
        "native_rig_preserved": True,
        "native_joint_count": len(armature.data.bones),
    }


def set_component_properties(meshes: list[bpy.types.Object]) -> None:
    for obj in meshes:
        if not obj.get("rapid_body_primary_surface", False):
            obj["rapid_body_primary_surface"] = False
        obj["candidate_id"] = "kira_temporary_functional_body_20260730"
        obj["private_review_only"] = True
        obj["owner_approved"] = False
        obj["runtime_assignment_allowed"] = False


def clear_pose(armature: bpy.types.Object) -> None:
    armature.animation_data_create()
    armature.animation_data.action = None
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        pose_bone.location = (0.0, 0.0, 0.0)
        pose_bone.scale = (1.0, 1.0, 1.0)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


POSES: dict[str, dict[str, tuple[float, float, float]]] = {
    "neutral": {},
    "reach": {
        "lShldrBend_042": (0.0, math.radians(-18), math.radians(54)),
        "lForearmBend_044": (0.0, math.radians(54), 0.0),
        "lHand_046": (math.radians(8), 0.0, math.radians(-8)),
        "chestUpper_040": (0.0, math.radians(-6), 0.0),
    },
    "stride": {
        "lThighBend_05": (math.radians(24), 0.0, math.radians(2)),
        "lShin_07": (math.radians(28), 0.0, 0.0),
        "rThighBend_021": (math.radians(-18), 0.0, math.radians(-2)),
        "rShin_023": (math.radians(8), 0.0, 0.0),
        "lShldrBend_042": (math.radians(-8), 0.0, math.radians(18)),
        "rShldrBend_067": (math.radians(8), 0.0, math.radians(-18)),
    },
    "seated": {
        "lThighBend_05": (math.radians(-62), 0.0, math.radians(4)),
        "rThighBend_021": (math.radians(-62), 0.0, math.radians(-4)),
        "lShin_07": (math.radians(70), 0.0, 0.0),
        "rShin_023": (math.radians(70), 0.0, 0.0),
        "abdomenLower_037": (math.radians(-7), 0.0, 0.0),
    },
    "hip_flexion": {
        "lThighBend_05": (math.radians(-42), 0.0, math.radians(8)),
        "lShin_07": (math.radians(48), 0.0, 0.0),
        "pelvis_04": (math.radians(5), 0.0, 0.0),
    },
    "knee_flexion": {
        "lThighBend_05": (math.radians(10), 0.0, math.radians(2)),
        "lShin_07": (math.radians(55), 0.0, 0.0),
    },
    "knee_flexion_right": {
        "rThighBend_021": (math.radians(10), 0.0, math.radians(-2)),
        "rShin_023": (math.radians(55), 0.0, 0.0),
    },
    "hand_test": {
        "lShldrBend_042": (0.0, math.radians(-10), math.radians(44)),
        "lForearmBend_044": (0.0, math.radians(38), 0.0),
        "lIndex1_051": (math.radians(22), 0.0, 0.0),
        "lIndex2_052": (math.radians(28), 0.0, 0.0),
        "lIndex3_053": (math.radians(20), 0.0, 0.0),
        "lMid1_055": (math.radians(24), 0.0, 0.0),
        "lMid2_056": (math.radians(30), 0.0, 0.0),
        "lMid3_057": (math.radians(22), 0.0, 0.0),
    },
}


def author_action(
    armature: bpy.types.Object,
    name: str,
    rotations: dict[str, tuple[float, float, float]],
) -> bpy.types.Action:
    clear_pose(armature)
    action = bpy.data.actions.new(f"KIRA_TFB_{name.upper()}")
    action.use_fake_user = True
    armature.animation_data.action = action
    for frame in (1, 30):
        for pose_bone in armature.pose.bones:
            pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        for bone_name, rotation in rotations.items():
            pose_bone = armature.pose.bones.get(bone_name)
            if pose_bone is None:
                raise ValueError(f"required pose bone absent: {bone_name}")
            pose_bone.rotation_euler = rotation if frame == 30 else (0.0, 0.0, 0.0)
            pose_bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=bone_name)
    action["candidate_id"] = "kira_temporary_functional_body_20260730"
    action["review_action"] = name
    return action


def activate_action(armature: bpy.types.Object, action: bpy.types.Action, frame: int) -> None:
    armature.animation_data_create()
    armature.animation_data.action = action
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def make_camera(scene: bpy.types.Scene) -> bpy.types.Object:
    data = bpy.data.cameras.new("Kira_TFB_Review_Camera")
    data.type = "ORTHO"
    camera = bpy.data.objects.new("Kira_TFB_Review_Camera", data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return camera


def make_seated_review_props(
    body: bpy.types.Object,
    armature: bpy.types.Object,
    seated_action: bpy.types.Action,
    material: bpy.types.Material,
) -> list[bpy.types.Object]:
    activate_action(armature, seated_action, 30)
    points = audit_helpers.evaluated_vertices(body)
    pelvis_indices = audit_helpers.region_indices(body, ("pelvis_", "hip_"))
    pelvis_points = [points[index] for index in pelvis_indices] or points
    pelvis_x = [point.x for point in pelvis_points]
    pelvis_y = [point.y for point in pelvis_points]
    pelvis_z = [point.z for point in pelvis_points]
    seat_top = audit_helpers.quantile(pelvis_z, 0.035) - 0.004
    seat_center_y = (
        audit_helpers.quantile(pelvis_y, 0.25)
        + audit_helpers.quantile(pelvis_y, 0.85)
    ) * 0.5
    seat_half_x = max(
        0.29,
        (audit_helpers.quantile(pelvis_x, 0.97) - audit_helpers.quantile(pelvis_x, 0.03)) * 0.62,
    )
    seat_half_y = 0.19
    clear_pose(armature)
    props: list[bpy.types.Object] = []
    specifications = (
        ("Kira_TFB_Seated_Contact_Seat", (0.0, seat_center_y, seat_top - 0.025), (seat_half_x, seat_half_y, 0.025)),
        ("Kira_TFB_Seated_Contact_Left_Support", (-seat_half_x * 0.72, seat_center_y + 0.05, seat_top * 0.5), (0.035, 0.035, max(0.04, seat_top * 0.5))),
        ("Kira_TFB_Seated_Contact_Right_Support", (seat_half_x * 0.72, seat_center_y + 0.05, seat_top * 0.5), (0.035, 0.035, max(0.04, seat_top * 0.5))),
    )
    for name, location, scale in specifications:
        bpy.ops.mesh.primitive_cube_add(location=location)
        obj = bpy.context.object
        obj.name = name
        obj.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.data.materials.append(material)
        obj["review_context_prop_only"] = True
        obj["candidate_component"] = False
        obj["must_not_export"] = True
        obj.hide_render = True
        props.append(obj)
    for obj in props:
        obj["seat_surface_top_z_m"] = float(seat_top)
        obj["seat_center_y_m"] = float(seat_center_y)
    return props


def render(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    path: Path,
    location: Vector,
    target: Vector,
    ortho_scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = ortho_scale
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_review_set(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output_dir: Path,
    body: bpy.types.Object,
    armature: bpy.types.Object,
    actions: dict[str, bpy.types.Action],
    seated_review_props: list[bpy.types.Object],
) -> dict[str, str]:
    renders: dict[str, str] = {}
    activate_action(armature, actions["neutral"], 1)
    points = audit_helpers.evaluated_vertices(body)
    box = audit_helpers.bounds(points)
    low = Vector(box["low"])
    high = Vector(box["high"])
    center = (low + high) * 0.5
    height = box["size"][2]
    width = box["size"][0]
    depth = box["size"][1]
    full_scale = max(height * 1.10, width * 1.18)
    side_scale = max(height * 1.10, depth * 1.18)
    distance = 3.0
    neutral_views = (
        ("front", Vector((center.x, center.y - distance, center.z)), full_scale),
        ("rear", Vector((center.x, center.y + distance, center.z)), full_scale),
        ("left_profile", Vector((center.x + distance, center.y, center.z)), side_scale),
        ("right_profile", Vector((center.x - distance, center.y, center.z)), side_scale),
        ("left_three_quarter", Vector((center.x + 2.35, center.y - 2.35, center.z)), full_scale),
        ("right_three_quarter", Vector((center.x - 2.35, center.y - 2.35, center.z)), full_scale),
    )
    for name, location, scale in neutral_views:
        path = output_dir / f"{name}.png"
        render(scene, camera, path, location, center, scale)
        renders[name] = path.name
    detail_views = (
        ("face_close", Vector((0.0, -2.2, high.z - height * 0.10)), Vector((0.0, center.y, high.z - height * 0.105)), height * 0.26),
        ("crown_top_close", Vector((center.x, center.y, high.z + 2.2)), Vector((center.x, center.y, high.z - height * 0.07)), height * 0.30),
        ("rear_hairline_close", Vector((center.x, center.y + 2.2, high.z - height * 0.10)), Vector((center.x, center.y, high.z - height * 0.105)), height * 0.28),
        ("adult_surface_front_close", Vector((0.0, -2.0, low.z + height * 0.45)), Vector((0.0, center.y, low.z + height * 0.45)), height * 0.26),
        ("adult_surface_three_quarter_close", Vector((1.35, center.y - 1.55, low.z + height * 0.45)), Vector((0.0, center.y, low.z + height * 0.45)), height * 0.29),
        ("left_hand_nails_close", Vector((high.x + 1.2, -1.2, low.z + height * 0.57)), Vector((high.x * 0.92, center.y, low.z + height * 0.57)), height * 0.20),
        ("left_foot_toenails_close", Vector((width * 0.18, -1.25, low.z + height * 0.07)), Vector((width * 0.18, center.y, low.z + height * 0.07)), height * 0.18),
    )
    for name, location, target, scale in detail_views:
        path = output_dir / f"{name}.png"
        render(scene, camera, path, location, target, scale)
        renders[name] = path.name
    for name in ("reach", "stride", "seated", "hip_flexion", "knee_flexion", "knee_flexion_right", "hand_test"):
        activate_action(armature, actions[name], 30)
        posed = audit_helpers.evaluated_vertices(body)
        posed_box = audit_helpers.bounds(posed)
        posed_low = Vector(posed_box["low"])
        posed_high = Vector(posed_box["high"])
        posed_center = (posed_low + posed_high) * 0.5
        scale = max(posed_box["size"][0], posed_box["size"][2]) * 1.18
        location = Vector((posed_center.x, posed_center.y - 3.0, posed_center.z))
        if name in {"seated", "hip_flexion"}:
            location = Vector((posed_center.x + 2.4, posed_center.y - 2.4, posed_center.z))
        elif name == "knee_flexion":
            # A true side view makes flexion direction unambiguous.  This is
            # an explicit visual gate: a knee that bends posteriorly cannot
            # pass merely because the deformation numbers remain finite.
            location = Vector((posed_center.x + 3.0, posed_center.y, posed_center.z))
        elif name == "knee_flexion_right":
            location = Vector((posed_center.x - 3.0, posed_center.y, posed_center.z))
        for prop in seated_review_props:
            prop.hide_render = name != "seated"
        path = output_dir / f"pose_{name}.png"
        render(scene, camera, path, location, posed_center, scale)
        renders[f"pose_{name}"] = path.name
    for prop in seated_review_props:
        prop.hide_render = True
    activate_action(armature, actions["neutral"], 1)
    return renders


def export_candidate(
    path: Path,
    armature: bpy.types.Object,
    meshes: list[bpy.types.Object],
) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_nla_strips=True,
        export_skins=True,
        export_morph=True,
        export_extras=True,
        export_yup=True,
    )


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    project_root = Path(config["project_root"]).resolve(strict=True)
    source_path = (project_root / config["source_path"]).resolve(strict=True)
    request_path = (project_root / config["request_path"]).resolve(strict=True)
    authority_path = (project_root / config["authority_path"]).resolve(strict=True)
    output_dir = (project_root / config["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if sha256_file(source_path) != SOURCE_SHA256:
        raise ValueError("staged source hash mismatch")
    if sha256_file(request_path) != REQUEST_SHA256:
        raise ValueError("request hash mismatch")
    authority_sha = sha256_file(authority_path)
    if config["authority_sha256"] != authority_sha:
        raise ValueError("authority record hash mismatch")
    if config.get("runtime_assignment_allowed") or config.get("owner_approved"):
        raise ValueError("this worker permits only an inactive unapproved candidate")
    if "robert" in json.dumps(config).lower():
        raise ValueError("Robert data is forbidden from this isolated Kira build configuration")

    request = json.loads(request_path.read_text(encoding="utf-8"))
    if request["privacy"]["robert_private_data_allowed"]:
        raise ValueError("request privacy gate is open to Robert data")

    audit_helpers.clear_scene()
    scene = bpy.context.scene
    collection = bpy.data.collections.new("KIRA_TEMPORARY_FUNCTIONAL_BODY_PRIVATE_REVIEW")
    scene.collection.children.link(collection)
    imported = audit_helpers.import_glb(source_path)
    for obj in imported:
        audit_helpers.move_to_collection(obj, collection)
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    if len(armatures) != 1 or len(armatures[0].data.bones) != 188:
        raise ValueError("enrolled source does not expose the reviewed single 188-joint rig")
    armature = armatures[0]
    armature.name = "Kira_Temporary_Functional_Body_Rig_188"
    armature.data.name = "Kira_Temporary_Functional_Body_Rig_188_Data"
    armature["candidate_id"] = "kira_temporary_functional_body_20260730"
    armature["private_review_only"] = True
    armature["runtime_assignment_allowed"] = False
    armature["owner_approved"] = False

    by_mesh_name = {
        obj.data.name: obj for obj in imported if obj.type == "MESH"
    }
    source_mesh_names = sorted(by_mesh_name)
    missing = sorted(set(KEEP_MESHES) - set(by_mesh_name))
    if missing:
        raise ValueError(f"required source meshes missing: {missing}")
    for obj in list(imported):
        if obj.type == "MESH" and obj.data.name not in KEEP_MESHES:
            bpy.data.objects.remove(obj, do_unlink=True)
    meshes = [obj for obj in collection.objects if obj.type == "MESH"]
    by_mesh_name = {obj.data.name: obj for obj in meshes}

    skin = make_material("Kira_TFB_Light_Natural_Skin", MATERIAL_TARGETS["skin"], roughness=0.52)
    lips = make_material("Kira_TFB_Natural_Lips", MATERIAL_TARGETS["lip"], roughness=0.46)
    nails = make_material("Kira_TFB_Natural_Nails", MATERIAL_TARGETS["nail"], roughness=0.33)
    iris = make_material("Kira_TFB_Natural_Brown_Iris", MATERIAL_TARGETS["iris"], roughness=0.26)
    pupil = make_material("Kira_TFB_Pupil", MATERIAL_TARGETS["pupil"], roughness=0.20)
    sclera = make_material("Kira_TFB_Natural_Sclera", MATERIAL_TARGETS["sclera"], roughness=0.42)
    mouth = make_material("Kira_TFB_Mouth", MATERIAL_TARGETS["mouth"], roughness=0.48)
    teeth = make_material("Kira_TFB_Teeth", MATERIAL_TARGETS["teeth"], roughness=0.32)
    hair = make_material("Kira_TFB_Black_Hair", MATERIAL_TARGETS["hair"], roughness=0.38)
    clear_eye = make_material("Kira_TFB_Clear_Eye_Surface", (0.92, 0.96, 1.0, 0.18), roughness=0.08, transmission=0.72)
    review_prop_material = make_material("Kira_TFB_Review_Seat_Material", (0.075, 0.12, 0.17, 1.0), roughness=0.64)

    for name in ("Ariel_Mesh_Torso_0", "Ariel_Mesh_Arms_0", "Ariel_Mesh_Legs_0", "Ariel_Mesh_Face_0", "Ariel_Mesh_Ears_0", "Ariel_Mesh_EyeSocket_0"):
        replace_object_material(by_mesh_name[name], skin)
    # The source adult-region mesh is welded into the same primary surface and
    # deliberately uses the same skin material.  R1 used a separate material
    # that exposed a triangular construction boundary and was visually
    # rejected as a pasted-on patch.
    replace_object_material(by_mesh_name["Ariel_Mesh_Genitalia_0"], skin)
    replace_object_material(by_mesh_name["Ariel_Mesh_Lips_0"], lips)
    replace_object_material(by_mesh_name["Ariel_Mesh_Fingernails_0"], nails)
    replace_object_material(by_mesh_name["Ariel_Mesh_Toenails_0"], nails)
    replace_object_material(by_mesh_name["Ariel_Mesh_Irises_0"], iris)
    replace_object_material(by_mesh_name["Ariel_Mesh_Pupils_0"], pupil)
    replace_object_material(by_mesh_name["Ariel_Mesh_Sclera_0"], sclera)
    replace_object_material(by_mesh_name["Ariel_Mesh_Mouth_0"], mouth)
    replace_object_material(by_mesh_name["Ariel_Mesh_Teeth_0"], teeth)
    for name in ("Ariel_Mesh_Cornea_0", "Ariel_Mesh_EyeMoisture_0", "Eye_Lahes_EyeMoisture_0"):
        replace_object_material(by_mesh_name[name], clear_eye)
    replace_object_material(by_mesh_name["Eye_Brows_Brows02_0.001"], hair)
    for name in ("Hair_Hair Thin_0", "Hair_Hair Mid_0", "Hair_Hair Long_0"):
        replace_object_material(by_mesh_name[name], hair)

    body, authoring = join_and_weld(by_mesh_name, armature)
    # Collapse inherited duplicate skin slots into one material assignment.
    # This prevents source-slot/split-normal patches from appearing only after
    # deformation even when every source component was nominally recolored.
    replace_object_material(body, skin)
    fingernail_refinement = shorten_fingernails(
        by_mesh_name["Ariel_Mesh_Fingernails_0"]
    )
    toenail_refinement = {
        "method": "r7_dorsal_translation_rejected_and_disabled",
        "changed_vertices": 0,
        "reason": "the R7 two-largest-component translation made the big-toe nail visibly float and pierce the toe",
        "owner_visual_attachment_review_required": True,
    }
    morph = apply_bounded_parameter_morph(body)
    # R4/R5's coordinate snapping was independently proven destructive:
    # nonmanifold edges and pelvis intersections increased even though the
    # full-body silhouette looked similar.  Preserve the liked body direction
    # and leave this surface untouched until an actual bridge/union operation
    # can prove a cleaner exact-SHA result.
    pelvis_midline_repair = {
        "method": "destructive_coordinate_snap_disabled",
        "vertices_changed": 0,
        "reason": "R5 independent audit found 204 nonmanifold edges and 1384 pelvis intersections after the mirrored-pair snap",
        "required_next_gate": "independent exact-SHA topology/intersection audit",
    }
    hair_straightening = straighten_source_groom(
        body,
        [
            by_mesh_name["Hair_Hair Thin_0"],
            by_mesh_name["Hair_Hair Mid_0"],
            by_mesh_name["Hair_Hair Long_0"],
        ],
    )
    current_objects = list(collection.objects)
    scale_record = scale_to_height_and_floor(current_objects, [body], TARGET_HEIGHT_M)
    meshes = [obj for obj in collection.objects if obj.type == "MESH"]
    set_component_properties(meshes)

    topology = audit_helpers.topology_record(body)
    weights = audit_helpers.weight_record(body, {bone.name for bone in armature.data.bones})
    topology_pass = (
        topology["connected_components"] == 1
        and topology["boundary_edge_count"] == 0
        and topology["overused_edge_count"] == 0
        and topology["degenerate_face_count_under_1e_12_m2"] == 0
    )
    weight_pass = (
        weights["unweighted_vertex_count"] == 0
        and not weights["invalid_target_groups"]
        and weights["maximum_positive_groups_per_vertex"] <= 4
        and weights["weight_sum"]["minimum"] > 0.999
        and weights["weight_sum"]["maximum"] < 1.001
    )

    actions = {name: author_action(armature, name, rotations) for name, rotations in POSES.items()}
    clear_pose(armature)
    rest_positions = audit_helpers.evaluated_vertices(body)
    region_specs = {
        "left_forearm_hand": ("lForearm", "lHand", "lIndex", "lMid"),
        "left_lower_leg_foot": ("lShin", "lFoot", "lToe", "lMetatarsals"),
        "pelvis_hips": ("pelvis_", "lThigh", "rThigh"),
        "upper_torso": ("abdomen", "chest"),
    }
    deformation: dict[str, object] = {}
    deformation_passes: dict[str, bool] = {}
    for name, action in actions.items():
        activate_action(armature, action, 30 if name != "neutral" else 1)
        metrics = audit_helpers.deformation_record(body, rest_positions, region_specs)
        stretch = metrics["edge_stretch_ratio"]
        passed = (
            metrics["all_coordinates_finite"]
            and stretch["p05"] >= 0.65
            and stretch["p95"] <= 1.40
            and stretch["fraction_under_half"] <= 0.002
            and stretch["fraction_over_2x"] <= 0.002
        )
        deformation[name] = {
            "action": action.name,
            "sample_frame": 30 if name != "neutral" else 1,
            "rotations_degrees_xyz": {
                bone: [round(math.degrees(value), 3) for value in values]
                for bone, values in POSES[name].items()
            },
            "metrics": metrics,
        }
        deformation_passes[name] = passed
    clear_pose(armature)

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 800
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.025, 0.032, 0.044)
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = False
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.show_specular_highlight = True
    camera = make_camera(scene)
    seated_review_props = make_seated_review_props(
        body,
        armature,
        actions["seated"],
        review_prop_material,
    )
    # Workbench does not reproduce the clear corneal transmission used by the
    # GLB.  Hide only the clear review overlays while rendering so the actual
    # brown iris is assessable; restore them before export.
    clear_review_mesh_names = (
        "Ariel_Mesh_Cornea_0",
        "Ariel_Mesh_EyeMoisture_0",
        "Eye_Lahes_EyeMoisture_0",
    )
    clear_review_objects = [by_mesh_name[name] for name in clear_review_mesh_names]
    for obj in clear_review_objects:
        obj.hide_render = True
    renders = render_review_set(
        scene,
        camera,
        output_dir,
        body,
        armature,
        actions,
        seated_review_props,
    )
    for obj in clear_review_objects:
        obj.hide_render = False
    clear_pose(armature)

    armature.show_in_front = False
    candidate_path = output_dir / "kira_hart_temporary_functional_body_private_candidate.glb"
    export_candidate(candidate_path, armature, meshes)
    blend_path = output_dir / "kira_hart_temporary_functional_body_private_review.blend"
    scene["candidate_id"] = "kira_temporary_functional_body_20260730"
    scene["private_review_only"] = True
    scene["owner_approved"] = False
    scene["runtime_assignment_allowed"] = False
    scene["runtime_activation_allowed"] = False
    scene["public_export_allowed"] = False
    scene["robert_private_data_used"] = False
    scene["independent_audit_required"] = True
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    visual_gate = "PENDING_INDEPENDENT_VISUAL_REVIEW"
    overall_author_gate = topology_pass and weight_pass and all(deformation_passes.values())
    render_bindings = {
        name: {
            "path": str((output_dir / filename).relative_to(project_root)).replace("\\", "/"),
            "sha256": sha256_file(output_dir / filename),
            "size_bytes": (output_dir / filename).stat().st_size,
        }
        for name, filename in renders.items()
    }
    evidence = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "candidate_id": "kira_temporary_functional_body_20260730",
        "status": "PRIVATE_INSPECTION_CANDIDATE_AWAITING_INDEPENDENT_AUDIT_AND_OWNER_REVIEW",
        "sources": {
            "staged_foundation": {
                "path": config["source_path"],
                "sha256": SOURCE_SHA256,
                "bytes": source_path.stat().st_size,
                "title": "Base Female Character",
                "author": "BlackProject",
                "source_url": "https://sketchfab.com/3d-models/base-female-character-ec7445f61d9e499186578b8ef4814b6a",
                "license": "CC BY 4.0",
                "role": "generic adult-female derivative foundation with native 188-joint rig",
            },
            "authority": {
                "path": config["authority_path"],
                "sha256": authority_sha,
                "size_bytes": authority_path.stat().st_size,
            },
            "request": {
                "path": config["request_path"],
                "sha256": REQUEST_SHA256,
                "size_bytes": request_path.stat().st_size,
            },
        },
        "privacy": {
            "robert_private_photos_used": False,
            "robert_measurements_used": False,
            "robert_morphs_or_surface_used": False,
            "identifiable_person_likeness_used": False,
            "private_local_review_only": True,
            "runtime_files_read_or_written_by_worker": False,
            "reference_inputs": ["owner text specification", "licensed generic adult-female foundation"],
        },
        "request_parameters": request["parameters"],
        "foundation_import": {
            "source_mesh_count": 28,
            "kept_mesh_names": list(KEEP_MESHES),
            "excluded_mesh_names": sorted(set(source_mesh_names) - set(KEEP_MESHES)),
            "native_joint_count": 188,
            "native_rig_preserved": True,
            "source_completion_not_assumed": True,
        },
        "authoring": authoring,
        "adult_surface_authoring": {
            "authored_on_primary_body_surface": True,
            "separate_or_floating_adult_surface_present": False,
            "separate_or_floating_anatomy_mesh_created": False,
            "adult_surface_interface_weld_or_bridge_evidence": bool(
                authoring["vertices_merged"] > 0
                and topology["connected_components"] == 1
            ),
            "original_component_role": "licensed source external adult-region component joined to torso/arms/legs/face/ears before exact-position weld",
            "interface_evidence": {
                "primary_surface_object": body.name,
                "source_component": "Ariel_Mesh_Genitalia_0",
                "weld_tolerance_m": authoring["weld_tolerance_m"],
                "vertices_merged_across_all_primary_components": authoring["vertices_merged"],
                "post_weld_positional_connected_components": topology["connected_components"],
                "same_skin_material_used_across_interface": True,
                "r1_triangular_material_patch_removed": True
            },
            "owner_visual_review_required": True,
            "dynamic_soft_tissue_behavior_proven": False
        },
        "parameter_morph": morph,
        "pelvis_midline_repair": pelvis_midline_repair,
        "fingernail_refinement": fingernail_refinement,
        "toenail_refinement": toenail_refinement,
        "hair_straightening": hair_straightening,
        "stature": scale_record,
        "materials": {
            "skin": "light natural neutral-warm review material",
            "primary_surface_skin_material_slot_count": len(body.data.materials),
            "imported_custom_split_normals_cleared": True,
            "regional_adult_skin": "same continuous skin material in R2; R1 triangular material discontinuity removed",
            "eyes": "actual source eye meshes with brown iris, black pupil, natural sclera, clear corneal layer",
            "mouth": "actual source lips, teeth, mouth cavity meshes",
            "nails": "actual source fingernail and toenail meshes",
            "hair": "licensed source Thin, Mid, and Long layered components, recolored black and fitted toward straight connected locks; oversized Front curl and opaque source cap excluded; runtime grooming and dynamics remain unproven",
            "eye_artifact_repair": "opaque source eyelash-card mesh excluded because it rendered as hard black bands above and below the eyes; actual eye, iris, sclera, brow, and clear-eye surfaces preserved",
            "scalp_artifact_repair": "opaque source scalp cap excluded entirely; crown_top_close.png and rear_hairline_close.png are dedicated proof views for actual black hair geometry and natural uncovered scalp",
        },
        "topology_author_audit": topology,
        "weights_author_audit": weights,
        "deformation_author_audit": deformation,
        "deformation_author_passes": deformation_passes,
        "actions": {name: action.name for name, action in actions.items()},
        "review_renders": renders,
        "render_bindings": render_bindings,
        "review_context": {
            "seated_contact_props": [obj.name for obj in seated_review_props],
            "exported_with_candidate": False,
            "purpose": "make actual pelvis-to-seat contact legible; the backless seat and supports are not candidate body components and do not alter the pose",
            "lighting": "neutral studio material view with cast shadows and cavity disabled so hard shadow polygons cannot be mistaken for skin/material discontinuities",
            "knee_flexion_visual_gate": "pose_knee_flexion.png is rendered from the side and must visibly show ordinary posterior lower-leg flexion; finite deformation metrics alone cannot pass this gate",
        },
        "candidate": {
            "path": str(candidate_path.relative_to(project_root)).replace("\\", "/"),
            "bytes": candidate_path.stat().st_size,
            "sha256": sha256_file(candidate_path),
            "primary_surface_property": "rapid_body_primary_surface=true",
            "owner_approved": False,
            "runtime_assignment_allowed": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        },
        "review_blend": {
            "path": str(blend_path.relative_to(project_root)).replace("\\", "/"),
            "bytes": blend_path.stat().st_size,
            "sha256": sha256_file(blend_path),
        },
        "gates": {
            "author_topology_gate": topology_pass,
            "author_weight_gate": weight_pass,
            "author_bounded_deformation_gate": all(deformation_passes.values()),
            "author_combined_gate": overall_author_gate,
            "independent_exact_sha_topology_intersection_audit": "PENDING",
            "independent_bounded_deformation_audit": "PENDING",
            "visual_review": visual_gate,
            "owner_review": "PENDING",
            "runtime_eligibility": False,
        },
        "truth_note": "This is a private, inactive inspection candidate. The authored booleans do not substitute for the required independent exact-SHA topology/intersection audit, independent pose audit, visual inspection, or Robert's owner approval. It is not selected, attached, activated, public, or a permanent Kira appearance.",
    }
    evidence_path = output_dir / "BUILD_EVIDENCE.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "status": evidence["status"],
        "candidate": str(candidate_path),
        "evidence": str(evidence_path),
        "topology_pass": topology_pass,
        "weight_pass": weight_pass,
        "deformation_pass": all(deformation_passes.values()),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
