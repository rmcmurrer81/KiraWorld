#!/usr/bin/env python3
"""Blender worker for Kira's inactive adult-retarget gate diagnostic.

The worker constructs a disposable, attributed body-only retarget trial in a
new evidence folder.  It deliberately excludes every identity-bearing source
head/face asset.  The trial is saved only so the failure can be inspected; it
is never exported or bound as an avatar candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict, deque
from pathlib import Path

import bpy
from mathutils import Vector


BODY_MESHES = {
    "Ariel_Mesh_Torso_0",
    "Ariel_Mesh_Arms_0",
    "Ariel_Mesh_Legs_0",
    "Ariel_Mesh_Fingernails_0",
    "Ariel_Mesh_Toenails_0",
    "Ariel_Mesh_Genitalia_0",
}

IDENTITY_EXCLUSION_TOKENS = (
    "face",
    "lips",
    "ears",
    "eyesocket",
    "mouth",
    "teeth",
    "pupil",
    "iris",
    "sclera",
    "cornea",
    "eyemoisture",
    "eyelash",
    "brow",
    "hair",
)


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


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)


def import_glb(path: Path) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [obj for obj in bpy.data.objects if obj not in before]


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def world_bone_head(armature: bpy.types.Object, name: str) -> Vector:
    return armature.matrix_world @ armature.data.bones[name].head_local


def target_for_source_bone(name: str) -> str | None:
    """Explicit deterministic major-body mapping from the CC BY rig to Kira."""

    exact = {
        "_rootJoint": "_rootJoint",
    }
    if name in exact:
        return exact[name]

    mappings = (
        (("hip_", "pelvis_"), "mixamorig:Hips_01"),
        (("abdomenLower_",), "mixamorig:Spine_02"),
        (("abdomenUpper_",), "mixamorig:Spine1_03"),
        (("chestLower_", "chestUpper_", "lPectoral_", "rPectoral_"), "mixamorig:Spine2_04"),
        (("neckLower_", "neckUpper_"), "mixamorig:Neck_05"),
        (("head_",), "mixamorig:Head_06"),
        (("lCollar_",), "mixamorig:LeftShoulder_08"),
        (("lShldrBend_", "lShldrTwist_"), "mixamorig:LeftArm_09"),
        (("lForearmBend_", "lForearmTwist_"), "mixamorig:LeftForeArm_010"),
        (("lHand_", "lCarpal"), "mixamorig:LeftHand_011"),
        (("rCollar_",), "mixamorig:RightShoulder_032"),
        (("rShldrBend_", "rShldrTwist_"), "mixamorig:RightArm_033"),
        (("rForearmBend_", "rForearmTwist_"), "mixamorig:RightForeArm_034"),
        (("rHand_", "rCarpal"), "mixamorig:RightHand_035"),
        (("lThighBend_", "lThighTwist_"), "mixamorig:LeftUpLeg_055"),
        (("lShin_",), "mixamorig:LeftLeg_056"),
        (("lFoot_", "lMetatarsals_"), "mixamorig:LeftFoot_057"),
        (("lToe_", "lSmallToe", "lBigToe"), "mixamorig:LeftToeBase_058"),
        (("rThighBend_", "rThighTwist_"), "mixamorig:RightUpLeg_060"),
        (("rShin_",), "mixamorig:RightLeg_061"),
        (("rFoot_", "rMetatarsals_"), "mixamorig:RightFoot_062"),
        (("rToe_", "rSmallToe", "rBigToe"), "mixamorig:RightToeBase_063"),
    )
    for prefixes, target in mappings:
        if name.startswith(prefixes):
            return target

    finger_specs = (
        ("lThumb1_", "mixamorig:LeftHandThumb1_012"),
        ("lThumb2_", "mixamorig:LeftHandThumb2_013"),
        ("lThumb3_", "mixamorig:LeftHandThumb3_014"),
        ("lIndex1_", "mixamorig:LeftHandIndex1_016"),
        ("lIndex2_", "mixamorig:LeftHandIndex2_017"),
        ("lIndex3_", "mixamorig:LeftHandIndex3_018"),
        ("lMid1_", "mixamorig:LeftHandMiddle1_020"),
        ("lMid2_", "mixamorig:LeftHandMiddle2_021"),
        ("lMid3_", "mixamorig:LeftHandMiddle3_022"),
        ("lRing1_", "mixamorig:LeftHandRing1_024"),
        ("lRing2_", "mixamorig:LeftHandRing2_025"),
        ("lRing3_", "mixamorig:LeftHandRing3_026"),
        ("lPinky1_", "mixamorig:LeftHandPinky1_028"),
        ("lPinky2_", "mixamorig:LeftHandPinky2_029"),
        ("lPinky3_", "mixamorig:LeftHandPinky3_030"),
        ("rThumb1_", "mixamorig:RightHandThumb1_036"),
        ("rThumb2_", "mixamorig:RightHandThumb2_037"),
        ("rThumb3_", "mixamorig:RightHandThumb3_038"),
        ("rIndex1_", "mixamorig:RightHandIndex1_040"),
        ("rIndex2_", "mixamorig:RightHandIndex2_041"),
        ("rIndex3_", "mixamorig:RightHandIndex3_042"),
        ("rMid1_", "mixamorig:RightHandMiddle1_044"),
        ("rMid2_", "mixamorig:RightHandMiddle2_045"),
        ("rMid3_", "mixamorig:RightHandMiddle3_00"),
        ("rRing1_", "mixamorig:RightHandRing1_047"),
        ("rRing2_", "mixamorig:RightHandRing2_048"),
        ("rRing3_", "mixamorig:RightHandRing3_049"),
        ("rPinky1_", "mixamorig:RightHandPinky1_051"),
        ("rPinky2_", "mixamorig:RightHandPinky2_052"),
        ("rPinky3_", "mixamorig:RightHandPinky3_053"),
    )
    for prefix, target in finger_specs:
        if name.startswith(prefix):
            return target
    return None


def topology_record(obj: bpy.types.Object) -> dict[str, object]:
    mesh = obj.data
    use_count: defaultdict[tuple[int, int], int] = defaultdict(int)
    adjacency: list[list[int]] = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = sorted(edge.vertices)
        adjacency[a].append(b)
        adjacency[b].append(a)
    for poly in mesh.polygons:
        verts = list(poly.vertices)
        for index, a in enumerate(verts):
            b = verts[(index + 1) % len(verts)]
            use_count[tuple(sorted((a, b)))] += 1
    seen: set[int] = set()
    component_sizes: list[int] = []
    for start in range(len(mesh.vertices)):
        if start in seen:
            continue
        queue = deque([start])
        seen.add(start)
        size = 0
        while queue:
            current = queue.popleft()
            size += 1
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        component_sizes.append(size)
    boundary = sum(1 for count in use_count.values() if count == 1)
    non_manifold = sum(1 for count in use_count.values() if count != 2)
    return {
        "object": obj.name,
        "mesh": mesh.name,
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "connected_components": len(component_sizes),
        "largest_component_vertices": max(component_sizes, default=0),
        "boundary_edge_count": boundary,
        "non_manifold_edge_count": non_manifold,
    }


def quantile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return float(ordered[index])


def mapped_vertex_weights(obj: bpy.types.Object) -> tuple[list[dict[str, float]], dict[str, object]]:
    group_names = {group.index: group.name for group in obj.vertex_groups}
    per_vertex: list[dict[str, float]] = []
    input_mass = 0.0
    mapped_mass = 0.0
    mapped_vertices = 0
    source_groups: set[str] = set()
    unmapped_groups: set[str] = set()
    for vertex in obj.data.vertices:
        merged: defaultdict[str, float] = defaultdict(float)
        vertex_input = 0.0
        vertex_mapped = 0.0
        for assignment in vertex.groups:
            if assignment.weight <= 1e-8:
                continue
            source = group_names[assignment.group]
            weight = float(assignment.weight)
            source_groups.add(source)
            input_mass += weight
            vertex_input += weight
            target = target_for_source_bone(source)
            if target is None:
                unmapped_groups.add(source)
                continue
            merged[target] += weight
            mapped_mass += weight
            vertex_mapped += weight
        if vertex_mapped > 1e-8:
            mapped_vertices += 1
            for target in list(merged):
                merged[target] /= vertex_mapped
        per_vertex.append(dict(merged))
    return per_vertex, {
        "vertex_count": len(obj.data.vertices),
        "mapped_vertex_count": mapped_vertices,
        "unmapped_vertex_count": len(obj.data.vertices) - mapped_vertices,
        "input_weight_mass": round(input_mass, 9),
        "mapped_weight_mass": round(mapped_mass, 9),
        "mapped_mass_fraction": round(mapped_mass / input_mass, 9) if input_mass else 0.0,
        "positive_source_groups": sorted(source_groups),
        "unmapped_positive_source_groups": sorted(unmapped_groups),
    }


def create_trial_mesh(
    source: bpy.types.Object,
    reference_armature: bpy.types.Object,
    kira_armature: bpy.types.Object,
    target_collection: bpy.types.Collection,
    comparison_collection: bpy.types.Collection,
    material: bpy.types.Material,
    comparison_material: bpy.types.Material,
    global_scale: float,
    reference_hips: Vector,
    kira_hips: Vector,
) -> tuple[bpy.types.Object, bpy.types.Object, dict[str, object]]:
    weights, mapping_record = mapped_vertex_weights(source)
    source_groups = {group.index: group.name for group in source.vertex_groups}
    joint_residuals: dict[tuple[str, str], Vector] = {}
    for source_name in mapping_record["positive_source_groups"]:
        target_name = target_for_source_bone(source_name)
        if target_name is None:
            continue
        reference_head = world_bone_head(reference_armature, source_name)
        target_head = world_bone_head(kira_armature, target_name)
        fitted_head = kira_hips + (reference_head - reference_hips) * global_scale
        joint_residuals[(source_name, target_name)] = target_head - fitted_head

    vertices: list[tuple[float, float, float]] = []
    uniformly_fitted: list[Vector] = []
    warped_positions: list[Vector] = []
    vertex_displacements: list[float] = []
    maximum_joint_correction = 0.0
    for vertex in source.data.vertices:
        original_world = source.matrix_world @ vertex.co
        fitted = kira_hips + (original_world - reference_hips) * global_scale
        correction = Vector((0.0, 0.0, 0.0))
        correction_weight = 0.0
        for assignment in vertex.groups:
            if assignment.weight <= 1e-8:
                continue
            source_name = source_groups[assignment.group]
            target_name = target_for_source_bone(source_name)
            if target_name is None:
                continue
            weight = float(assignment.weight)
            correction += joint_residuals[(source_name, target_name)] * weight
            correction_weight += weight
        if correction_weight > 1e-8:
            correction /= correction_weight
        maximum_joint_correction = max(maximum_joint_correction, correction.length)
        position = fitted + correction
        uniformly_fitted.append(fitted)
        warped_positions.append(position)
        vertex_displacements.append((position - fitted).length)
        vertices.append(tuple(float(value) for value in position))

    rest_edge_ratios: list[float] = []
    for edge in source.data.edges:
        a, b = edge.vertices
        original_length = (uniformly_fitted[a] - uniformly_fitted[b]).length
        warped_length = (warped_positions[a] - warped_positions[b]).length
        if original_length > 1e-9:
            rest_edge_ratios.append(warped_length / original_length)

    faces = [tuple(poly.vertices) for poly in source.data.polygons]
    comparison_mesh = bpy.data.meshes.new(f"UNIFORM_FIT_{source.data.name}")
    comparison_mesh.from_pydata(
        [tuple(float(value) for value in point) for point in uniformly_fitted],
        [],
        faces,
    )
    comparison_mesh.update()
    comparison = bpy.data.objects.new(
        f"UNIFORM_FIT_{source.data.name}", comparison_mesh
    )
    comparison_collection.objects.link(comparison)
    comparison["inactive_uniform_fit_comparison_only"] = True
    comparison["source_mesh"] = source.data.name
    comparison["source_license"] = "CC BY 4.0"
    comparison.color = (0.48, 0.50, 0.54, 1.0)
    comparison.data.materials.append(comparison_material)
    comparison.hide_render = True

    mesh = bpy.data.meshes.new(f"DIAGNOSTIC_{source.data.name}")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    trial = bpy.data.objects.new(f"DIAGNOSTIC_{source.data.name}", mesh)
    target_collection.objects.link(trial)
    trial["inactive_diagnostic_only"] = True
    trial["source_mesh"] = source.data.name
    trial["source_license"] = "CC BY 4.0"
    trial.color = (0.18, 0.48, 0.68, 1.0)
    trial.data.materials.append(material)

    target_groups: dict[str, bpy.types.VertexGroup] = {}
    for vertex_index, merged in enumerate(weights):
        for target_name, weight in merged.items():
            group = target_groups.get(target_name)
            if group is None:
                group = trial.vertex_groups.new(name=target_name)
                target_groups[target_name] = group
            group.add([vertex_index], weight, "REPLACE")

    modifier = trial.modifiers.new(name="DIAGNOSTIC_KIRA_79_CAGE", type="ARMATURE")
    modifier.object = kira_armature
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = True
    mapping_record["maximum_joint_head_correction_m"] = round(maximum_joint_correction, 9)
    mapping_record["target_group_count"] = len(target_groups)
    uniform_bounds = bounds(uniformly_fitted)
    warped_bounds = bounds(warped_positions)
    mapping_record["rest_shape_delta_from_uniformly_scaled_reference"] = {
        "uniform_fit_bounds_m": uniform_bounds,
        "warped_trial_bounds_m": warped_bounds,
        "warped_to_uniform_axis_size_ratio": [
            round(warped / uniform, 9) if uniform > 1e-9 else 0.0
            for warped, uniform in zip(
                warped_bounds["size"], uniform_bounds["size"], strict=True
            )
        ],
        "vertex_displacement_m": {
            "median": round(quantile(vertex_displacements, 0.5), 9),
            "p95": round(quantile(vertex_displacements, 0.95), 9),
            "maximum": round(max(vertex_displacements, default=0.0), 9),
        },
        "edge_length_ratio": {
            "minimum": round(min(rest_edge_ratios, default=0.0), 9),
            "p05": round(quantile(rest_edge_ratios, 0.05), 9),
            "median": round(quantile(rest_edge_ratios, 0.5), 9),
            "p95": round(quantile(rest_edge_ratios, 0.95), 9),
            "maximum": round(max(rest_edge_ratios, default=0.0), 9),
            "edges_over_2x": sum(1 for ratio in rest_edge_ratios if ratio > 2.0),
            "edges_under_half": sum(1 for ratio in rest_edge_ratios if ratio < 0.5),
        },
    }
    return trial, comparison, mapping_record


def reset_pose(armature: bpy.types.Object) -> None:
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        pose_bone.location = (0.0, 0.0, 0.0)
        pose_bone.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()


def apply_pose(armature: bpy.types.Object, name: str) -> dict[str, list[float]]:
    reset_pose(armature)
    values: dict[str, tuple[float, float, float]] = {}
    if name == "upper_limb":
        values = {
            "mixamorig:LeftArm_09": (0.0, math.radians(-25), math.radians(38)),
            "mixamorig:LeftForeArm_010": (0.0, math.radians(68), 0.0),
            "mixamorig:LeftHand_011": (math.radians(10), 0.0, math.radians(-8)),
        }
    elif name == "hip_knee":
        values = {
            "mixamorig:LeftUpLeg_055": (math.radians(42), 0.0, math.radians(8)),
            "mixamorig:LeftLeg_056": (math.radians(-62), 0.0, 0.0),
            "mixamorig:LeftFoot_057": (math.radians(18), 0.0, 0.0),
        }
    elif name == "spine":
        values = {
            "mixamorig:Spine_02": (0.0, math.radians(10), 0.0),
            "mixamorig:Spine1_03": (0.0, math.radians(13), 0.0),
            "mixamorig:Spine2_04": (math.radians(-5), math.radians(9), 0.0),
        }
    for bone_name, rotation in values.items():
        armature.pose.bones[bone_name].rotation_euler = rotation
    bpy.context.view_layer.update()
    return {
        bone: [round(math.degrees(value), 3) for value in rotation]
        for bone, rotation in values.items()
    }


def evaluated_vertices(obj: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def bounds(points: list[Vector]) -> dict[str, list[float]]:
    low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    return {
        "low": [round(float(value), 9) for value in low],
        "high": [round(float(value), 9) for value in high],
        "size": [round(float(value), 9) for value in high - low],
    }


def region_indices(obj: bpy.types.Object, prefixes: tuple[str, ...]) -> list[int]:
    group_indices = {
        group.index for group in obj.vertex_groups if group.name.startswith(prefixes)
    }
    result = []
    for vertex in obj.data.vertices:
        if any(
            assignment.group in group_indices and assignment.weight > 0.25
            for assignment in vertex.groups
        ):
            result.append(vertex.index)
    return result


def centroid(points: list[Vector]) -> Vector:
    if not points:
        return Vector((0.0, 0.0, 0.0))
    total = Vector((0.0, 0.0, 0.0))
    for point in points:
        total += point
    return total / len(points)


def deformation_record(
    objects: list[bpy.types.Object],
    rest_positions: dict[str, list[Vector]],
    region_specs: dict[str, tuple[str, ...]],
) -> dict[str, object]:
    all_points: list[Vector] = []
    ratios: list[float] = []
    finite = True
    region_displacements: defaultdict[str, list[float]] = defaultdict(list)
    for obj in objects:
        current = evaluated_vertices(obj)
        original = rest_positions[obj.name]
        all_points.extend(current)
        finite = finite and all(math.isfinite(value) for point in current for value in point)
        for edge in obj.data.edges:
            a, b = edge.vertices
            rest_length = (original[a] - original[b]).length
            current_length = (current[a] - current[b]).length
            if rest_length > 1e-9:
                ratios.append(current_length / rest_length)
        for region, prefixes in region_specs.items():
            indices = region_indices(obj, prefixes)
            if indices:
                rest_center = centroid([original[index] for index in indices])
                current_center = centroid([current[index] for index in indices])
                region_displacements[region].append((current_center - rest_center).length)
    return {
        "all_coordinates_finite": finite,
        "world_bounds_m": bounds(all_points),
        "edge_stretch_ratio": {
            "minimum": round(min(ratios, default=0.0), 9),
            "p05": round(quantile(ratios, 0.05), 9),
            "median": round(quantile(ratios, 0.5), 9),
            "p95": round(quantile(ratios, 0.95), 9),
            "maximum": round(max(ratios, default=0.0), 9),
            "edges_over_2x": sum(1 for ratio in ratios if ratio > 2.0),
            "edges_under_half": sum(1 for ratio in ratios if ratio < 0.5),
        },
        "region_centroid_displacement_m": {
            region: round(max(values, default=0.0), 9)
            for region, values in region_displacements.items()
        },
    }


def look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def render_view(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    path: Path,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    ortho_scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = ortho_scale
    look_at(camera, Vector(target))
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    kira_path = Path(config["kira_source"]).resolve(strict=True)
    reference_path = Path(config["reference_source"]).resolve(strict=True)
    output_dir = Path(config["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if sha256_file(kira_path) != config["kira_sha256"]:
        raise ValueError("Kira source hash mismatch")
    if sha256_file(reference_path) != config["reference_sha256"]:
        raise ValueError("adult reference source hash mismatch")
    if config.get("candidate_glb_export_requested") or config.get(
        "live_binding_change_requested"
    ):
        raise ValueError("this worker is diagnostic-only")

    neck_evidence = json.loads(
        Path(config["neck_evidence"]).read_text(encoding="utf-8")
    )
    if neck_evidence["conclusion"]["defensible_existing_closed_neck_ring_count"] != 0:
        raise ValueError("pinned neck blocker evidence is inconsistent")

    clear_scene()
    kira_source_collection = bpy.data.collections.new("PINNED_KIRA_R6_READ_ONLY")
    reference_source_collection = bpy.data.collections.new("PINNED_CC_BY_REFERENCE_HIDDEN")
    comparison_collection = bpy.data.collections.new("INACTIVE_UNIFORM_FIT_COMPARISON")
    diagnostic_collection = bpy.data.collections.new("INACTIVE_RETARGET_DIAGNOSTIC_ONLY")
    bpy.context.scene.collection.children.link(kira_source_collection)
    bpy.context.scene.collection.children.link(reference_source_collection)
    bpy.context.scene.collection.children.link(comparison_collection)
    bpy.context.scene.collection.children.link(diagnostic_collection)

    kira_objects = import_glb(kira_path)
    for obj in kira_objects:
        move_to_collection(obj, kira_source_collection)
        obj.hide_select = True
        obj.hide_render = True
        obj["source_role"] = "pinned_kira_r6_read_only"
    reference_objects = import_glb(reference_path)
    for obj in reference_objects:
        move_to_collection(obj, reference_source_collection)
        obj.hide_select = True
        obj.hide_render = True
        obj["source_role"] = "pinned_cc_by_reference_read_only"

    kira_armatures = [obj for obj in kira_objects if obj.type == "ARMATURE"]
    reference_armatures = [obj for obj in reference_objects if obj.type == "ARMATURE"]
    if len(kira_armatures) != 1 or len(kira_armatures[0].data.bones) != 79:
        raise ValueError("Kira did not import as one exact 79-joint cage")
    if len(reference_armatures) != 1 or len(reference_armatures[0].data.bones) != 188:
        raise ValueError("reference did not import as one exact 188-joint rig")
    kira_armature = kira_armatures[0]
    reference_armature = reference_armatures[0]

    all_reference_meshes = [obj for obj in reference_objects if obj.type == "MESH"]
    source_body = [obj for obj in all_reference_meshes if obj.data.name in BODY_MESHES]
    if {obj.data.name for obj in source_body} != BODY_MESHES:
        raise ValueError("the authorized body-only component set is incomplete")
    identity_meshes = sorted(
        obj.data.name
        for obj in all_reference_meshes
        if any(token in obj.data.name.lower() for token in IDENTITY_EXCLUSION_TOKENS)
    )
    if any(obj.data.name in identity_meshes for obj in source_body):
        raise ValueError("an identity-bearing source mesh entered the body-only trial")

    reference_hips = world_bone_head(reference_armature, "hip_03")
    reference_head = world_bone_head(reference_armature, "head_091")
    kira_hips = world_bone_head(kira_armature, "mixamorig:Hips_01")
    kira_head = world_bone_head(kira_armature, "mixamorig:Head_06")
    reference_torso_length = (reference_head - reference_hips).length
    kira_torso_length = (kira_head - kira_hips).length
    if reference_torso_length <= 1e-9:
        raise ValueError("reference torso landmark distance is zero")
    global_scale = kira_torso_length / reference_torso_length

    material = bpy.data.materials.new("DIAGNOSTIC_BLUE_NO_SOURCE_MATERIAL")
    material.diffuse_color = (0.10, 0.34, 0.62, 1.0)
    comparison_material = bpy.data.materials.new("UNIFORM_GRAY_NO_SOURCE_MATERIAL")
    comparison_material.diffuse_color = (0.38, 0.40, 0.44, 1.0)
    trial_objects: list[bpy.types.Object] = []
    comparison_objects: list[bpy.types.Object] = []
    mapping_records = []
    topology_records = []
    for source in sorted(source_body, key=lambda item: item.data.name):
        topology_records.append(topology_record(source))
        trial, comparison, mapping = create_trial_mesh(
            source,
            reference_armature,
            kira_armature,
            diagnostic_collection,
            comparison_collection,
            material,
            comparison_material,
            global_scale,
            reference_hips,
            kira_hips,
        )
        trial_objects.append(trial)
        comparison_objects.append(comparison)
        mapping["source_mesh"] = source.data.name
        mapping_records.append(mapping)

    # Only the trial and the Kira cage are visible in saved diagnostic evidence.
    kira_armature.hide_render = False
    kira_armature.hide_viewport = False
    kira_armature.hide_select = True
    kira_armature.show_in_front = True
    kira_armature.data.display_type = "STICK"
    kira_armature["diagnostic_cage_only"] = True

    scene = bpy.context.scene
    scene["inactive_diagnostic_only"] = True
    scene["candidate_export_allowed"] = False
    scene["avatar_builder_binding_allowed"] = False
    scene["runtime_activation_allowed"] = False
    scene["owner_approved"] = False
    scene["adult_anatomy_proven"] = False
    scene["reference_attribution"] = (
        "Base Female Character by BlackProject, CC BY 4.0, Sketchfab"
    )
    readme = bpy.data.texts.new("READ_ME_INACTIVE_FAILED_GATE.txt")
    readme.write(
        "KIRA R7 ADULT RETARGET GATE - INACTIVE DIAGNOSTIC ONLY\n\n"
        "This Blend is not Kira's body and is not an avatar candidate. It contains a\n"
        "disposable body-only weight/pose trial made from the attributed CC BY source.\n"
        "All source face, lip, ear, eye, mouth, teeth, hair, brow, and eyelash meshes\n"
        "were excluded. The pinned Kira topology has no defensible closed neck ring, so\n"
        "Kira's exact protected head cannot be separated and attached without a manual\n"
        "semantic boundary selection. Export, binding, activation, and promotion are off.\n\n"
        "Source: Base Female Character by BlackProject, CC BY 4.0, Sketchfab\n"
    )

    reset_pose(kira_armature)
    rest_positions = {obj.name: evaluated_vertices(obj) for obj in trial_objects}
    rest_record = deformation_record(
        trial_objects,
        rest_positions,
        {
            "left_forearm_hand": ("mixamorig:LeftForeArm", "mixamorig:LeftHand"),
            "left_lower_leg_foot": ("mixamorig:LeftLeg", "mixamorig:LeftFoot"),
            "upper_torso": ("mixamorig:Spine1", "mixamorig:Spine2"),
        },
    )

    # Deterministic deformation tests. These prove only that the diagnostic
    # groups respond; visual/static evidence still controls any quality claim.
    poses: dict[str, dict[str, object]] = {
        "rest": {"rotations_degrees_xyz": {}, "metrics": rest_record}
    }
    for pose_name in ("upper_limb", "hip_knee", "spine"):
        rotations = apply_pose(kira_armature, pose_name)
        metrics = deformation_record(
            trial_objects,
            rest_positions,
            {
                "left_forearm_hand": ("mixamorig:LeftForeArm", "mixamorig:LeftHand"),
                "left_lower_leg_foot": ("mixamorig:LeftLeg", "mixamorig:LeftFoot"),
                "upper_torso": ("mixamorig:Spine1", "mixamorig:Spine2"),
            },
        )
        poses[pose_name] = {
            "rotations_degrees_xyz": rotations,
            "metrics": metrics,
        }

    # Fixed owner-review renders.
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.show_specular_highlight = True
    camera_data = bpy.data.cameras.new("DiagnosticCamera")
    camera = bpy.data.objects.new("DiagnosticCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    comparison_points = [
        obj.matrix_world @ vertex.co
        for obj in comparison_objects
        for vertex in obj.data.vertices
    ]
    comparison_bounds = bounds(comparison_points)
    comparison_low = Vector(comparison_bounds["low"])
    comparison_high = Vector(comparison_bounds["high"])
    review_center = (comparison_low + comparison_high) * 0.5
    front_scale = max(comparison_bounds["size"][0], comparison_bounds["size"][2]) * 1.22
    side_scale = max(comparison_bounds["size"][1], comparison_bounds["size"][2]) * 1.22
    render_paths: dict[str, str] = {}

    # First show that uniform scaling retains the adult source shape but leaves
    # large joint-head residuals. Then show the deterministic correction's
    # collapse. Both are diagnostic-only derivatives with source materials off.
    for obj in trial_objects:
        obj.hide_render = True
    for obj in comparison_objects:
        obj.hide_render = False
    kira_armature.hide_render = True
    uniform_front = output_dir / "uniform_fit_reference_front.png"
    render_view(
        scene,
        camera,
        uniform_front,
        (review_center.x, review_center.y - 3.0, review_center.z),
        tuple(review_center),
        front_scale,
    )
    render_paths["uniform_fit_reference_front"] = uniform_front.name
    uniform_side = output_dir / "uniform_fit_reference_side.png"
    render_view(
        scene,
        camera,
        uniform_side,
        (review_center.x + 3.0, review_center.y, review_center.z),
        tuple(review_center),
        side_scale,
    )
    render_paths["uniform_fit_reference_side"] = uniform_side.name
    for obj in comparison_objects:
        obj.hide_render = True
    for obj in trial_objects:
        obj.hide_render = False
    kira_armature.hide_render = False

    reset_pose(kira_armature)
    trial_rest_points = [
        point for obj in trial_objects for point in evaluated_vertices(obj)
    ]
    trial_bounds = bounds(trial_rest_points)
    trial_low = Vector(trial_bounds["low"])
    trial_high = Vector(trial_bounds["high"])
    trial_center = (trial_low + trial_high) * 0.5
    trial_front_scale = max(trial_bounds["size"][0], trial_bounds["size"][2]) * 1.22
    trial_side_scale = max(trial_bounds["size"][1], trial_bounds["size"][2]) * 1.22
    same_scale = output_dir / "retarget_rest_same_scale_comparison.png"
    render_view(
        scene,
        camera,
        same_scale,
        (review_center.x, review_center.y - 3.0, review_center.z),
        tuple(review_center),
        front_scale,
    )
    render_paths["retarget_rest_same_scale_comparison"] = same_scale.name
    rest_front = output_dir / "retarget_rest_front.png"
    render_view(
        scene,
        camera,
        rest_front,
        (trial_center.x, trial_center.y - 3.0, trial_center.z),
        tuple(trial_center),
        trial_front_scale,
    )
    render_paths["rest_front"] = rest_front.name
    rest_side = output_dir / "retarget_rest_side.png"
    render_view(
        scene,
        camera,
        rest_side,
        (trial_center.x + 3.0, trial_center.y, trial_center.z),
        tuple(trial_center),
        trial_side_scale,
    )
    render_paths["rest_side"] = rest_side.name
    for pose_name, location, scale in (
        (
            "upper_limb",
            (trial_center.x, trial_center.y - 3.0, trial_center.z),
            trial_front_scale * 1.12,
        ),
        (
            "hip_knee",
            (trial_center.x, trial_center.y - 3.0, trial_center.z),
            trial_front_scale * 1.12,
        ),
        (
            "spine",
            (trial_center.x + 3.0, trial_center.y, trial_center.z),
            trial_side_scale * 1.12,
        ),
    ):
        apply_pose(kira_armature, pose_name)
        path = output_dir / f"retarget_{pose_name}.png"
        render_view(scene, camera, path, location, tuple(trial_center), scale)
        render_paths[pose_name] = path.name
    reset_pose(kira_armature)

    total_vertices = sum(record["vertex_count"] for record in mapping_records)
    mapped_vertices = sum(record["mapped_vertex_count"] for record in mapping_records)
    total_input_mass = sum(record["input_weight_mass"] for record in mapping_records)
    mapped_mass = sum(record["mapped_weight_mass"] for record in mapping_records)
    maximum_correction = max(
        record["maximum_joint_head_correction_m"] for record in mapping_records
    )
    neck_blocker = {
        "defensible_existing_closed_neck_ring_count": 0,
        "automatic_boundary_result": neck_evidence["conclusion"][
            "automatic_boundary_result"
        ],
        "lower_neck_candidate_edges": neck_evidence[
            "lower_neck_existing_edge_cycle_search"
        ]["candidate_edge_count"],
        "lower_neck_connected_parts": neck_evidence[
            "lower_neck_existing_edge_cycle_search"
        ]["connected_part_count"],
        "lower_neck_closed_cycles": neck_evidence[
            "lower_neck_existing_edge_cycle_search"
        ]["topologically_closed_cycle_count"],
    }
    collapsed_meshes = []
    severely_displaced_meshes = []
    for record in mapping_records:
        delta = record["rest_shape_delta_from_uniformly_scaled_reference"]
        if delta["vertex_displacement_m"]["p95"] > 0.05:
            severely_displaced_meshes.append(record["source_mesh"])
        if (
            delta["edge_length_ratio"]["minimum"] < 0.5
            or delta["edge_length_ratio"]["maximum"] > 2.0
        ):
            collapsed_meshes.append(record["source_mesh"])
    decision = {
        "status": "blocked_retarget_rest_shape_collapsed_and_no_identity_neck_seam_no_candidate",
        "reversible_offline_trial_authored": True,
        "valid_avatar_candidate_authored": False,
        "candidate_glb_created": False,
        "rest_shape_gate_passed": False,
        "rest_shape_collapse_detected_on_meshes": collapsed_meshes,
        "severe_rest_displacement_detected_on_meshes": severely_displaced_meshes,
        "why": [
            "The exact Kira body contains no defensible existing closed neck edge ring, so the protected identity/head cannot be separated without manual semantic selection.",
            "The trial uses six fragmented source body meshes and an explicit 188-to-79 major-body weight collapse; it is an attributed diagnostic derivative, not a project-owned cohesive Kira surface.",
            "The reference torso itself carries positive BelowJaw, ear, jaw-clench, and lower-jaw influences, so its mesh name does not provide a defensible body-versus-identity boundary.",
            "The deterministic joint-head correction severely changes the uniformly scaled source at rest; fixed renders show a skeleton-like collapsed body before any pose is applied.",
            "A responding limb/hip/spine pose is necessary but cannot prove seam quality, adult topology completeness, natural deformation, or Kira identity preservation.",
        ],
    }
    evidence = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "mode": config["mode"],
        "sources": {
            "kira_r6": {"path": str(kira_path), "sha256": config["kira_sha256"]},
            "adult_reference": {
                "path": str(reference_path),
                "sha256": config["reference_sha256"],
                "provenance": config["reference_provenance"],
            },
            "neck_evidence": {
                "path": config["neck_evidence"],
                "sha256": config["neck_evidence_sha256"],
            },
        },
        "static_topology_inspection": {
            "included_body_meshes": topology_records,
            "identity_bearing_meshes_excluded": identity_meshes,
            "included_vertex_total": sum(item["vertices"] for item in topology_records),
            "included_polygon_total": sum(item["polygons"] for item in topology_records),
            "included_mesh_count": len(topology_records),
            "cohesive_single_surface": False,
        },
        "retarget_trial": {
            "method": "global_hip_head_scale_plus_weighted_mapped_joint_head_residual",
            "global_scale": round(global_scale, 9),
            "reference_hip_to_head_m": round(reference_torso_length, 9),
            "kira_hip_to_head_m": round(kira_torso_length, 9),
            "maximum_joint_head_correction_m": round(maximum_correction, 9),
            "major_body_mapping_records": mapping_records,
            "summary": {
                "vertex_count": total_vertices,
                "mapped_vertex_count": mapped_vertices,
                "mapped_vertex_fraction": round(mapped_vertices / total_vertices, 9),
                "mapped_weight_mass_fraction": round(mapped_mass / total_input_mass, 9),
                "source_rig_bone_count": 188,
                "target_cage_bone_count": 79,
                "rest_shape_gate_passed": False,
                "rest_shape_collapse_detected_on_meshes": collapsed_meshes,
                "severe_rest_displacement_detected_on_meshes": severely_displaced_meshes,
            },
            "identity_meshes_copied": False,
            "source_materials_or_textures_copied": False,
            "saved_role": "inactive_failure_diagnostic_only",
        },
        "deformation_evidence": poses,
        "neck_boundary_blocker": neck_blocker,
        "fixed_review_renders": render_paths,
        "decision": decision,
        "exact_manual_blender_operation": {
            "required_semantic_selections": [
                "On Kira Object_85/Cuerpo__0, manually select two open transverse neck edge chains, one on each mirrored half-shell, below the full jaw, ears, scalp, face, eyelids, and sockets, with coincident front/back sagittal endpoints.",
                "Flood-select and hash the complete protected Kira head above those chains, explicitly including every disconnected identity-bearing face component and the exact existing 207-vertex mouth island.",
                "On the authorized reference, select only Ariel_Mesh_Torso_0, Ariel_Mesh_Arms_0, Ariel_Mesh_Legs_0, Ariel_Mesh_Fingernails_0, Ariel_Mesh_Toenails_0, and Ariel_Mesh_Genitalia_0; keep every listed identity-bearing mesh excluded.",
                "Manually attest the reference torso's open neck attachment boundary and establish reviewed one-to-one seam correspondence to a newly authored project-owned Kira body neck ring; do not weld by nearest coordinate.",
                "Review and freeze an explicit 188-to-79 body-bone mapping, including collapsed twist, pectoral, metatarsal, toe, carpal, and finger influences, before any production weight transfer.",
            ],
            "operation_after_owner_approval": (
                "Duplicate only the approved Kira neck chains into a new project-owned quad surface, author the body downward around Kira's unchanged 79-joint cage using the CC BY body only as an attributed construction reference, then weight-paint and test shoulder/elbow, wrist/fingers, spine, hip/knee, ankle/toes, squat, sit, walk, and floor-contact poses before any export."
            ),
        },
        "gates": {
            "owner_approved": False,
            "protected_head_mask_available": False,
            "cohesive_adult_surface_available": False,
            "complete_adult_anatomy_proven": False,
            "stable_79_joint_deformation_proven": False,
            "candidate_export_allowed": False,
            "avatar_builder_binding_allowed": False,
            "runtime_activation_allowed": False,
            "autobuild_allowed": False,
        },
        "safety": {
            "pinned_kira_source_edited": False,
            "pinned_reference_source_edited": False,
            "candidate_glb_exported": False,
            "live_kira_body_changed": False,
            "avatar_builder_binding_changed": False,
            "runtime_binding_changed": False,
            "home_world_changed": False,
            "person_state_changed": False,
        },
        "truth_note": (
            "The diagnostic proves only exact source structure, mapped-weight response, and the unresolved identity-preserving seam gate. It does not prove a full adult Kira body, anatomy completeness, natural motion, or production readiness."
        ),
    }
    Path(config["evidence"]).write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    bpy.ops.wm.save_as_mainfile(filepath=config["diagnostic_blend"])
    print(json.dumps({"ok": True, "decision": decision["status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
