#!/usr/bin/env python3
"""Author and gate Kira's inactive R7 adult external-surface trial.

The trial preserves the attributed adult reference rest surface, welds its
exactly coincident component seams, transfers only body weights to Kira's
exact 79-joint cage, and isolates the source head.  It never writes a live
binding.  A GLB is deliberately withheld unless every engineering and
identity gate passes; the currently pinned neck evidence prevents that.
"""

from __future__ import annotations

import argparse
import bmesh
import hashlib
import json
import math
import sys
from collections import defaultdict, deque
from pathlib import Path

import bpy
from mathutils import Vector


BODY_MESHES = (
    "Ariel_Mesh_Torso_0",
    "Ariel_Mesh_Arms_0",
    "Ariel_Mesh_Legs_0",
    "Ariel_Mesh_Fingernails_0",
    "Ariel_Mesh_Toenails_0",
    "Ariel_Mesh_Genitalia_0",
)

IDENTITY_EXCLUSION_TOKENS = (
    "face", "lips", "ears", "eyesocket", "mouth", "teeth", "pupil",
    "iris", "sclera", "cornea", "eyemoisture", "eyelash", "brow", "hair",
)

LIGHT_SKIN_SRGB_HEX = "#e6c0a9"
LIGHT_SKIN_RGBA = (230 / 255, 192 / 255, 169 / 255, 1.0)
WELD_TOLERANCE_M = 1e-6


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
    if name == "_rootJoint":
        return "_rootJoint"
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
    fingers = (
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
    for prefix, target in fingers:
        if name.startswith(prefix):
            return target
    return None


def quantile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return float(ordered[index])


def bounds(points: list[Vector]) -> dict[str, list[float]]:
    low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    return {
        "low": [round(float(value), 9) for value in low],
        "high": [round(float(value), 9) for value in high],
        "size": [round(float(value), 9) for value in high - low],
    }


def source_vertex_weights(obj: bpy.types.Object) -> tuple[list[dict[str, float]], dict[str, object]]:
    group_names = {group.index: group.name for group in obj.vertex_groups}
    rows: list[dict[str, float]] = []
    input_mass = 0.0
    mapped_mass = 0.0
    unmapped: set[str] = set()
    for vertex in obj.data.vertices:
        merged: defaultdict[str, float] = defaultdict(float)
        vertex_mapped = 0.0
        for assignment in vertex.groups:
            if assignment.weight <= 1e-8:
                continue
            source_name = group_names[assignment.group]
            weight = float(assignment.weight)
            input_mass += weight
            target = target_for_source_bone(source_name)
            if target is None:
                unmapped.add(source_name)
                continue
            merged[target] += weight
            mapped_mass += weight
            vertex_mapped += weight
        if vertex_mapped > 1e-8:
            for target in list(merged):
                merged[target] /= vertex_mapped
        rows.append(dict(merged))
    return rows, {
        "mesh": obj.data.name,
        "vertex_count": len(rows),
        "mapped_vertex_count": sum(bool(row) for row in rows),
        "mapped_mass_fraction": round(mapped_mass / input_mass, 9) if input_mass else 0.0,
        "unmapped_positive_source_groups": sorted(unmapped),
    }


def fit_point(
    point: Vector,
    reference_pelvis: Vector,
    kira_pelvis: Vector,
    upper_scale: float,
    lower_scale: float,
) -> Vector:
    delta = point - reference_pelvis
    vertical_scale = upper_scale if delta.z >= 0.0 else lower_scale
    return Vector((
        kira_pelvis.x + delta.x * upper_scale,
        kira_pelvis.y + delta.y * upper_scale,
        kira_pelvis.z + delta.z * vertical_scale,
    ))


def build_welded_surface(
    sources: list[bpy.types.Object],
    collection: bpy.types.Collection,
    material: bpy.types.Material,
    reference_pelvis: Vector,
    kira_pelvis: Vector,
    upper_scale: float,
    lower_scale: float,
) -> tuple[bpy.types.Object, dict[str, object]]:
    vertices: list[Vector] = []
    faces: list[tuple[int, ...]] = []
    weight_accumulator: list[defaultdict[str, float]] = []
    weight_samples: list[int] = []
    key_to_index: dict[tuple[int, int, int], int] = {}
    key_sources: defaultdict[tuple[int, int, int], set[str]] = defaultdict(set)
    mappings: list[dict[str, object]] = []
    original_vertex_total = 0
    duplicate_face_count = 0
    seen_faces: set[tuple[int, ...]] = set()

    for source in sources:
        rows, mapping = source_vertex_weights(source)
        mappings.append(mapping)
        original_vertex_total += len(source.data.vertices)
        local_to_merged: list[int] = []
        for vertex, row in zip(source.data.vertices, rows, strict=True):
            fitted = fit_point(
                source.matrix_world @ vertex.co,
                reference_pelvis,
                kira_pelvis,
                upper_scale,
                lower_scale,
            )
            key = tuple(round(float(value) / WELD_TOLERANCE_M) for value in fitted)
            index = key_to_index.get(key)
            if index is None:
                index = len(vertices)
                key_to_index[key] = index
                vertices.append(fitted)
                weight_accumulator.append(defaultdict(float))
                weight_samples.append(0)
            key_sources[key].add(source.data.name)
            for group, weight in row.items():
                weight_accumulator[index][group] += weight
            weight_samples[index] += 1
            local_to_merged.append(index)
        for polygon in source.data.polygons:
            mapped = tuple(local_to_merged[index] for index in polygon.vertices)
            if len(set(mapped)) < 3:
                continue
            canonical = tuple(sorted(mapped))
            if canonical in seen_faces:
                duplicate_face_count += 1
                continue
            seen_faces.add(canonical)
            faces.append(mapped)

    mesh = bpy.data.meshes.new("KIRA_R7_ADULT_EXTERNAL_SURFACE_WELDED")
    mesh.from_pydata([tuple(point) for point in vertices], [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Kira_R7_Adult_Surface_Trial", mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.color = LIGHT_SKIN_RGBA
    obj["inactive_review_only"] = True
    obj["skin_tone_contract"] = "pre_r6_live_light_untextured_v1"
    obj["skin_tone_srgb_hex"] = LIGHT_SKIN_SRGB_HEX
    obj["source_license"] = "CC BY 4.0"
    obj["source_identity_assets_excluded"] = True

    group_objects: dict[str, bpy.types.VertexGroup] = {}
    discarded_weight_mass = 0.0
    for index, weights in enumerate(weight_accumulator):
        if not weights:
            continue
        ordered = sorted(weights.items(), key=lambda item: (-item[1], item[0]))
        kept = ordered[:4]
        discarded_weight_mass += sum(value for _, value in ordered[4:])
        total = sum(value for _, value in kept)
        if total <= 1e-12:
            continue
        for group_name, weight in kept:
            group = group_objects.get(group_name)
            if group is None:
                group = obj.vertex_groups.new(name=group_name)
                group_objects[group_name] = group
            group.add([index], weight / total, "REPLACE")

    cross_mesh_weld_keys = sum(1 for names in key_sources.values() if len(names) > 1)
    record = {
        "source_meshes": [source.data.name for source in sources],
        "source_vertex_total": original_vertex_total,
        "welded_vertex_total_before_neck_cut": len(vertices),
        "vertices_merged": original_vertex_total - len(vertices),
        "cross_mesh_weld_locations": cross_mesh_weld_keys,
        "weld_tolerance_m": WELD_TOLERANCE_M,
        "face_total_before_neck_cut": len(faces),
        "duplicate_faces_removed": duplicate_face_count,
        "target_weight_group_count": len(group_objects),
        "top_four_weight_limit": 4,
        "discarded_weight_mass_before_renormalization": round(discarded_weight_mass, 9),
        "per_source_weight_mapping": mappings,
    }
    return obj, record


def bisect_object(obj: bpy.types.Object, cut_z: float, keep_above: bool) -> dict[str, int]:
    before_vertices = len(obj.data.vertices)
    before_polygons = len(obj.data.polygons)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(
        bm,
        geom=geom,
        dist=1e-7,
        plane_co=Vector((0.0, 0.0, cut_z)),
        plane_no=Vector((0.0, 0.0, 1.0)),
        clear_inner=keep_above,
        clear_outer=not keep_above,
    )
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return {
        "vertices_before": before_vertices,
        "vertices_after": len(obj.data.vertices),
        "polygons_before": before_polygons,
        "polygons_after": len(obj.data.polygons),
    }


def topology_record(obj: bpy.types.Object) -> dict[str, object]:
    mesh = obj.data
    edge_use: defaultdict[tuple[int, int], int] = defaultdict(int)
    adjacency: list[list[int]] = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = map(int, edge.vertices)
        adjacency[a].append(b)
        adjacency[b].append(a)
    for polygon in mesh.polygons:
        values = list(map(int, polygon.vertices))
        for index, a in enumerate(values):
            b = values[(index + 1) % len(values)]
            edge_use[tuple(sorted((a, b)))] += 1
    seen: set[int] = set()
    component_sizes: list[int] = []
    for start in range(len(mesh.vertices)):
        if start in seen:
            continue
        todo = deque([start])
        seen.add(start)
        size = 0
        while todo:
            current = todo.popleft()
            size += 1
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    todo.append(neighbor)
        component_sizes.append(size)

    boundary_edges = [edge for edge, count in edge_use.items() if count == 1]
    boundary_graph: defaultdict[int, list[int]] = defaultdict(list)
    for a, b in boundary_edges:
        boundary_graph[a].append(b)
        boundary_graph[b].append(a)
    boundary_seen: set[int] = set()
    boundary_parts = []
    for start in boundary_graph:
        if start in boundary_seen:
            continue
        todo = deque([start])
        boundary_seen.add(start)
        vertices = []
        while todo:
            current = todo.popleft()
            vertices.append(current)
            for neighbor in boundary_graph[current]:
                if neighbor not in boundary_seen:
                    boundary_seen.add(neighbor)
                    todo.append(neighbor)
        degrees = [len(boundary_graph[index]) for index in vertices]
        boundary_parts.append({
            "vertex_count": len(vertices),
            "closed_cycle": bool(vertices) and all(degree == 2 for degree in degrees),
            "degree_histogram": {
                str(degree): degrees.count(degree) for degree in sorted(set(degrees))
            },
        })
    face_areas = [float(polygon.area) for polygon in mesh.polygons]
    return {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "connected_components": len(component_sizes),
        "component_sizes": sorted(component_sizes, reverse=True),
        "boundary_edge_count": len(boundary_edges),
        "boundary_connected_parts": len(boundary_parts),
        "boundary_closed_cycle_count": sum(part["closed_cycle"] for part in boundary_parts),
        "boundary_parts": boundary_parts,
        "overused_edge_count": sum(1 for count in edge_use.values() if count > 2),
        "minimum_face_area_m2": round(min(face_areas, default=0.0), 12),
        "degenerate_face_count_under_1e_12_m2": sum(area <= 1e-12 for area in face_areas),
    }


def weight_record(obj: bpy.types.Object, valid_bones: set[str]) -> dict[str, object]:
    names = {group.index: group.name for group in obj.vertex_groups}
    unweighted = 0
    invalid_groups: set[str] = set()
    maximum_groups = 0
    sums = []
    for vertex in obj.data.vertices:
        positive = [assignment for assignment in vertex.groups if assignment.weight > 1e-8]
        maximum_groups = max(maximum_groups, len(positive))
        total = sum(float(assignment.weight) for assignment in positive)
        sums.append(total)
        if total <= 1e-8:
            unweighted += 1
        for assignment in positive:
            name = names[assignment.group]
            if name not in valid_bones:
                invalid_groups.add(name)
    return {
        "vertex_count": len(obj.data.vertices),
        "weighted_vertex_count": len(obj.data.vertices) - unweighted,
        "unweighted_vertex_count": unweighted,
        "weighted_vertex_fraction": round((len(obj.data.vertices) - unweighted) / max(1, len(obj.data.vertices)), 9),
        "maximum_positive_groups_per_vertex": maximum_groups,
        "invalid_target_groups": sorted(invalid_groups),
        "weight_sum": {
            "minimum": round(min(sums, default=0.0), 9),
            "median": round(quantile(sums, 0.5), 9),
            "maximum": round(max(sums, default=0.0), 9),
        },
    }


def make_identity_head_reference(
    source: bpy.types.Object,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
    cut_z: float,
) -> tuple[bpy.types.Object, dict[str, int]]:
    points = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
    faces = [tuple(polygon.vertices) for polygon in source.data.polygons]
    mesh = bpy.data.meshes.new("EXACT_KIRA_R6_HEAD_REFERENCE_MESH")
    mesh.from_pydata([tuple(point) for point in points], [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Exact_Kira_R6_Head_Reference_Only", mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.color = (0.18, 0.72, 0.92, 1.0)
    obj["source_role"] = "exact_kira_r6_identity_overlay_not_fused"
    obj["candidate_component"] = False
    cut = bisect_object(obj, cut_z, keep_above=True)
    return obj, cut


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
    elif name == "bilateral_squat":
        values = {
            "mixamorig:LeftUpLeg_055": (math.radians(34), 0.0, math.radians(5)),
            "mixamorig:RightUpLeg_060": (math.radians(34), 0.0, math.radians(-5)),
            "mixamorig:LeftLeg_056": (math.radians(-55), 0.0, 0.0),
            "mixamorig:RightLeg_061": (math.radians(-55), 0.0, 0.0),
            "mixamorig:Spine_02": (math.radians(-12), 0.0, 0.0),
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


def region_indices(obj: bpy.types.Object, prefixes: tuple[str, ...]) -> list[int]:
    group_indices = {
        group.index for group in obj.vertex_groups if group.name.startswith(prefixes)
    }
    return [
        vertex.index
        for vertex in obj.data.vertices
        if any(
            assignment.group in group_indices and assignment.weight > 0.25
            for assignment in vertex.groups
        )
    ]


def centroid(points: list[Vector]) -> Vector:
    total = Vector((0.0, 0.0, 0.0))
    for point in points:
        total += point
    return total / len(points) if points else total


def deformation_record(
    obj: bpy.types.Object,
    rest: list[Vector],
    region_specs: dict[str, tuple[str, ...]],
) -> dict[str, object]:
    current = evaluated_vertices(obj)
    ratios = []
    finite = all(math.isfinite(value) for point in current for value in point)
    for edge in obj.data.edges:
        a, b = map(int, edge.vertices)
        rest_length = (rest[a] - rest[b]).length
        current_length = (current[a] - current[b]).length
        if rest_length > 1e-9:
            ratios.append(current_length / rest_length)
    regions = {}
    for name, prefixes in region_specs.items():
        indices = region_indices(obj, prefixes)
        regions[name] = round(
            (centroid([current[i] for i in indices]) - centroid([rest[i] for i in indices])).length,
            9,
        ) if indices else 0.0
    edge_count = max(1, len(ratios))
    return {
        "all_coordinates_finite": finite,
        "world_bounds_m": bounds(current),
        "edge_stretch_ratio": {
            "minimum": round(min(ratios, default=0.0), 9),
            "p05": round(quantile(ratios, 0.05), 9),
            "median": round(quantile(ratios, 0.5), 9),
            "p95": round(quantile(ratios, 0.95), 9),
            "maximum": round(max(ratios, default=0.0), 9),
            "edges_over_2x": sum(ratio > 2.0 for ratio in ratios),
            "edges_under_half": sum(ratio < 0.5 for ratio in ratios),
            "fraction_over_2x": round(sum(ratio > 2.0 for ratio in ratios) / edge_count, 9),
            "fraction_under_half": round(sum(ratio < 0.5 for ratio in ratios) / edge_count, 9),
        },
        "region_centroid_displacement_m": regions,
    }


def look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def render_view(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    path: Path,
    location: Vector,
    target: Vector,
    scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = scale
    look_at(camera, target)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    kira_path = Path(config["kira_source"]).resolve(strict=True)
    reference_path = Path(config["reference_source"]).resolve(strict=True)
    neck_path = Path(config["neck_evidence"]).resolve(strict=True)
    output_dir = Path(config["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if sha256_file(kira_path) != config["kira_sha256"]:
        raise ValueError("Kira source hash mismatch")
    if sha256_file(reference_path) != config["reference_sha256"]:
        raise ValueError("adult reference hash mismatch")
    neck_evidence = json.loads(neck_path.read_text(encoding="utf-8"))
    if neck_evidence["conclusion"]["defensible_existing_closed_neck_ring_count"] != 0:
        raise ValueError("pinned neck evidence changed")
    if config.get("live_binding_change_requested"):
        raise ValueError("live binding is forbidden in this worker")

    clear_scene()
    scene = bpy.context.scene
    pinned_kira = bpy.data.collections.new("PINNED_KIRA_R6_SOURCE")
    pinned_reference = bpy.data.collections.new("PINNED_CC_BY_ADULT_REFERENCE")
    review = bpy.data.collections.new("INACTIVE_KIRA_R7_ADULT_SURFACE_REVIEW")
    identity = bpy.data.collections.new("EXACT_KIRA_IDENTITY_REFERENCE_NOT_FUSED")
    scene.collection.children.link(pinned_kira)
    scene.collection.children.link(pinned_reference)
    scene.collection.children.link(review)
    scene.collection.children.link(identity)

    kira_objects = import_glb(kira_path)
    for obj in kira_objects:
        move_to_collection(obj, pinned_kira)
        obj.hide_render = True
        obj.hide_viewport = True
        obj.hide_select = True
        obj["source_role"] = "pinned_kira_r6_read_only"
    reference_objects = import_glb(reference_path)
    for obj in reference_objects:
        move_to_collection(obj, pinned_reference)
        obj.hide_render = True
        obj.hide_viewport = True
        obj.hide_select = True
        obj["source_role"] = "pinned_cc_by_reference_read_only"

    kira_armatures = [obj for obj in kira_objects if obj.type == "ARMATURE"]
    reference_armatures = [obj for obj in reference_objects if obj.type == "ARMATURE"]
    if len(kira_armatures) != 1 or len(kira_armatures[0].data.bones) != 79:
        raise ValueError("Kira source is not the pinned exact 79-joint cage")
    if len(reference_armatures) != 1 or len(reference_armatures[0].data.bones) != 188:
        raise ValueError("adult reference is not the pinned 188-joint source")
    kira_armature = kira_armatures[0]
    reference_armature = reference_armatures[0]
    kira_armature.hide_viewport = False
    kira_armature.hide_render = True
    kira_armature.hide_select = True
    kira_armature.show_in_front = True

    reference_meshes = {
        obj.data.name: obj for obj in reference_objects if obj.type == "MESH"
    }
    if not all(name in reference_meshes for name in BODY_MESHES):
        raise ValueError("authorized adult external-form component set is incomplete")
    body_sources = [reference_meshes[name] for name in BODY_MESHES]
    identity_excluded = sorted(
        name for name in reference_meshes
        if any(token in name.lower() for token in IDENTITY_EXCLUSION_TOKENS)
    )
    if any(source.data.name in identity_excluded for source in body_sources):
        raise ValueError("identity-bearing adult source entered the body trial")

    reference_pelvis = world_bone_head(reference_armature, "pelvis_04")
    reference_head = world_bone_head(reference_armature, "head_091")
    kira_pelvis = world_bone_head(kira_armature, "mixamorig:Hips_01")
    kira_head = world_bone_head(kira_armature, "mixamorig:Head_06")
    reference_points = [
        source.matrix_world @ vertex.co
        for source in body_sources
        for vertex in source.data.vertices
    ]
    kira_meshes = [obj for obj in kira_objects if obj.type == "MESH"]
    # R6 also contains an Icosphere helper with unit-scale bounds (-1..1).
    # (A default factory Cube can likewise contaminate ad-hoc probes that do
    # not clear the startup scene.)  Neither is Kira's skinned body and neither
    # may be used as a stature/floor landmark.  The exact R6 body is the sole
    # dominant skinned mesh (57,745 vertices in the pinned source).
    largest_kira_mesh = max(kira_meshes, key=lambda obj: len(obj.data.vertices))
    kira_points = [
        largest_kira_mesh.matrix_world @ vertex.co
        for vertex in largest_kira_mesh.data.vertices
    ]
    reference_floor = min(point.z for point in reference_points)
    kira_floor = min(point.z for point in kira_points)
    upper_scale = (kira_head.z - kira_pelvis.z) / (reference_head.z - reference_pelvis.z)
    lower_scale = (kira_pelvis.z - kira_floor) / (reference_pelvis.z - reference_floor)

    skin = bpy.data.materials.new("KIRA_PRE_R6_LIGHT_SKIN_UNTEXTURED")
    skin.diffuse_color = LIGHT_SKIN_RGBA
    identity_material = bpy.data.materials.new("EXACT_KIRA_R6_IDENTITY_REFERENCE_CYAN")
    identity_material.diffuse_color = (0.18, 0.72, 0.92, 1.0)
    surface, authoring = build_welded_surface(
        body_sources,
        review,
        skin,
        reference_pelvis,
        kira_pelvis,
        upper_scale,
        lower_scale,
    )

    # The reference head shell is removed.  The plane is deterministic but is
    # not claimed as Kira's approved identity seam.
    neck_cut_z = float(world_bone_head(kira_armature, "mixamorig:Neck_05").z)
    body_cut = bisect_object(surface, neck_cut_z, keep_above=False)
    surface["source_head_removed"] = True
    surface["neck_cut_is_owner_approved_identity_seam"] = False
    surface["neck_cut_z_m"] = neck_cut_z
    modifier = surface.modifiers.new("EXACT_KIRA_79_JOINT_CAGE", type="ARMATURE")
    modifier.object = kira_armature
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = True

    identity_head, head_cut = make_identity_head_reference(
        largest_kira_mesh, identity, identity_material, neck_cut_z
    )
    identity_head.hide_render = True

    topology = topology_record(surface)
    weights = weight_record(surface, {bone.name for bone in kira_armature.data.bones})
    reset_pose(kira_armature)
    rest_positions = evaluated_vertices(surface)
    region_specs = {
        "left_forearm_hand": ("mixamorig:LeftForeArm", "mixamorig:LeftHand"),
        "left_lower_leg_foot": ("mixamorig:LeftLeg", "mixamorig:LeftFoot"),
        "upper_torso": ("mixamorig:Spine1", "mixamorig:Spine2"),
    }
    poses: dict[str, dict[str, object]] = {
        "rest": {
            "rotations_degrees_xyz": {},
            "metrics": deformation_record(surface, rest_positions, region_specs),
        }
    }
    for pose_name in ("upper_limb", "hip_knee", "spine", "bilateral_squat"):
        rotations = apply_pose(kira_armature, pose_name)
        poses[pose_name] = {
            "rotations_degrees_xyz": rotations,
            "metrics": deformation_record(surface, rest_positions, region_specs),
        }
    reset_pose(kira_armature)

    topology_pass = (
        topology["connected_components"] == 1
        and topology["overused_edge_count"] == 0
        and topology["degenerate_face_count_under_1e_12_m2"] == 0
        and topology["boundary_connected_parts"] == 1
        and topology["boundary_closed_cycle_count"] == 1
    )
    weights_pass = (
        weights["unweighted_vertex_count"] == 0
        and weights["maximum_positive_groups_per_vertex"] <= 4
        and not weights["invalid_target_groups"]
        and weights["weight_sum"]["minimum"] > 0.999
        and weights["weight_sum"]["maximum"] < 1.001
    )
    pose_passes = {}
    for pose_name, record in poses.items():
        metric = record["metrics"]
        stretch = metric["edge_stretch_ratio"]
        pose_passes[pose_name] = (
            metric["all_coordinates_finite"]
            and stretch["p05"] >= 0.70
            and stretch["p95"] <= 1.30
            and stretch["fraction_under_half"] <= 0.001
            and stretch["fraction_over_2x"] <= 0.001
        )
    deformation_pass = all(pose_passes.values())
    identity_preserved_and_joined = False
    full_adult_topology_proven = False

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
    camera_data = bpy.data.cameras.new("OwnerReviewCamera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("OwnerReviewCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    rest_bounds = bounds(rest_positions)
    low = Vector(rest_bounds["low"])
    high = Vector(rest_bounds["high"])
    center = (low + high) * 0.5
    front_scale = max(rest_bounds["size"][0], rest_bounds["size"][2]) * 1.22
    side_scale = max(rest_bounds["size"][1], rest_bounds["size"][2]) * 1.22
    renders: dict[str, str] = {}
    neutral_views = (
        ("neutral_front", Vector((center.x, center.y - 3.0, center.z)), front_scale),
        ("neutral_back", Vector((center.x, center.y + 3.0, center.z)), front_scale),
        ("neutral_left", Vector((center.x + 3.0, center.y, center.z)), side_scale),
        ("neutral_right", Vector((center.x - 3.0, center.y, center.z)), side_scale),
    )
    for name, location, scale in neutral_views:
        path = output_dir / f"{name}.png"
        render_view(scene, camera, path, location, center, scale)
        renders[name] = path.name

    # Exact current R6 head geometry is shown only as a differently colored,
    # isolated identity overlay.  It is not fused to or exported with the body.
    identity_head.hide_render = False
    overlay_points = rest_positions + [
        identity_head.matrix_world @ vertex.co for vertex in identity_head.data.vertices
    ]
    overlay_bounds = bounds(overlay_points)
    overlay_low = Vector(overlay_bounds["low"])
    overlay_high = Vector(overlay_bounds["high"])
    overlay_center = (overlay_low + overlay_high) * 0.5
    overlay_front_scale = max(overlay_bounds["size"][0], overlay_bounds["size"][2]) * 1.22
    overlay_side_scale = max(overlay_bounds["size"][1], overlay_bounds["size"][2]) * 1.22
    for name, location, scale in (
        ("identity_overlay_front", Vector((overlay_center.x, overlay_center.y - 3.0, overlay_center.z)), overlay_front_scale),
        ("identity_overlay_side", Vector((overlay_center.x + 3.0, overlay_center.y, overlay_center.z)), overlay_side_scale),
    ):
        path = output_dir / f"{name}.png"
        render_view(scene, camera, path, location, overlay_center, scale)
        renders[name] = path.name
    identity_head.hide_render = True

    for pose_name, side in (
        ("upper_limb", False),
        ("hip_knee", False),
        ("spine", True),
        ("bilateral_squat", False),
    ):
        apply_pose(kira_armature, pose_name)
        posed = evaluated_vertices(surface)
        posed_bounds = bounds(posed)
        posed_low = Vector(posed_bounds["low"])
        posed_high = Vector(posed_bounds["high"])
        posed_center = (posed_low + posed_high) * 0.5
        scale = max(
            posed_bounds["size"][1 if side else 0], posed_bounds["size"][2]
        ) * 1.28
        location = (
            Vector((posed_center.x + 3.0, posed_center.y, posed_center.z))
            if side
            else Vector((posed_center.x, posed_center.y - 3.0, posed_center.z))
        )
        path = output_dir / f"pose_{pose_name}.png"
        render_view(scene, camera, path, location, posed_center, scale)
        renders[f"pose_{pose_name}"] = path.name
    reset_pose(kira_armature)

    decision = {
        "status": "rejected_identity_seam_and_complete_adult_topology_not_proven_no_candidate",
        "inactive_review_blend_created": True,
        "candidate_glb_created": False,
        "live_binding_changed": False,
        "runtime_activation_allowed": False,
        "avatar_builder_promotion_allowed": False,
        "why": [
            "The rest-preserving corrected-pelvis weight-transfer is materially better than the rejected residual-warp diagnostic and is retained for review evidence.",
            "Kira's exact R6 head has no defensible existing closed neck ring; the cyan exact-head overlay is intentionally isolated and not fused to the adult body surface.",
            "A deterministic plane cut is useful engineering evidence but is not an owner-approved semantic identity seam.",
            "The attributed external-form components and welded surface cannot by themselves prove complete adult anatomy or identity preservation.",
            "No body can be promoted merely from a recolor, silhouette, finite pose, or source model label.",
        ],
    }
    if not topology_pass:
        decision["why"].append("The welded/cut body did not pass the strict single-surface topology gate.")
    if not weights_pass:
        decision["why"].append("The transferred weights did not pass the exact-79-joint normalization gate.")
    if not deformation_pass:
        decision["why"].append("At least one fixed pose failed the strict deformation gate.")

    evidence = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "mode": config["mode"],
        "sources": {
            "kira_r6": {"path": str(kira_path), "sha256": config["kira_sha256"], "joint_count": 79},
            "adult_reference": {
                "path": str(reference_path),
                "sha256": config["reference_sha256"],
                "joint_count": 188,
                "provenance": config["reference_provenance"],
            },
            "neck_evidence": {"path": str(neck_path), "sha256": config["neck_evidence_sha256"]},
        },
        "landmark_correction": {
            "rejected_old_landmark": "hip_03 (source root at world zero; not anatomical pelvis)",
            "correct_anatomical_pelvis": "pelvis_04",
            "reference_root_world_m": [round(float(v), 9) for v in world_bone_head(reference_armature, "hip_03")],
            "reference_pelvis_world_m": [round(float(v), 9) for v in reference_pelvis],
            "reference_head_world_m": [round(float(v), 9) for v in reference_head],
            "kira_pelvis_world_m": [round(float(v), 9) for v in kira_pelvis],
            "kira_head_world_m": [round(float(v), 9) for v in kira_head],
            "upper_body_scale": round(upper_scale, 9),
            "lower_body_scale": round(lower_scale, 9),
            "reference_floor_z_m": round(reference_floor, 9),
            "kira_floor_z_m": round(kira_floor, 9),
            "kira_floor_landmark_mesh": largest_kira_mesh.data.name,
            "kira_floor_landmark_vertex_count": len(largest_kira_mesh.data.vertices),
            "excluded_kira_helper_meshes_from_floor_landmark": sorted(
                obj.data.name for obj in kira_meshes if obj != largest_kira_mesh
            ),
        },
        "surface_authoring": {
            **authoring,
            "method": "rest-preserving_piecewise_vertical_fit_plus_exact_component_weld_plus_source_weight_name_collapse",
            "skin_tone": {"srgb_hex": LIGHT_SKIN_SRGB_HEX, "contract": "pre_r6_live_light_untextured_v1"},
            "source_materials_or_textures_copied": False,
            "identity_bearing_source_meshes_excluded": identity_excluded,
            "body_cut": body_cut,
            "head_reference_cut": head_cut,
            "neck_cut_z_m": round(neck_cut_z, 9),
            "reference_head_shell_removed": True,
            "exact_kira_r6_head_overlay_created": True,
            "exact_kira_r6_head_overlay_fused": False,
        },
        "topology": topology,
        "weights": weights,
        "deformation": poses,
        "pose_gate_results": pose_passes,
        "renders": renders,
        "gates": {
            "cohesive_body_surface_topology_passed": topology_pass,
            "exact_79_joint_weight_transfer_passed": weights_pass,
            "stable_fixed_pose_deformation_passed": deformation_pass,
            "identity_head_preserved_and_joined": identity_preserved_and_joined,
            "complete_adult_topology_proven": full_adult_topology_proven,
            "owner_visual_review_approved": False,
            "candidate_export_allowed": False,
            "live_binding_allowed": False,
        },
        "decision": decision,
    }
    evidence_path = output_dir / "evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    scene["inactive_review_only"] = True
    scene["candidate_export_allowed"] = False
    scene["live_binding_allowed"] = False
    scene["runtime_activation_allowed"] = False
    scene["owner_approved"] = False
    scene["complete_adult_topology_proven"] = False
    scene["identity_head_joined"] = False
    readme = bpy.data.texts.new("READ_ME_KIRA_R7_ADULT_SURFACE_TRIAL.txt")
    readme.write(
        "KIRA R7 ADULT EXTERNAL-SURFACE TRIAL - INACTIVE REVIEW ONLY\n\n"
        "This file corrects the earlier source-root/pelvis landmark error and preserves\n"
        "the adult reference rest surface while transferring body weights to Kira's exact\n"
        "79-joint cage. Exactly coincident source component seams were welded and the\n"
        "source head shell was removed. The cyan object is Kira's exact current R6 head\n"
        "geometry shown only as an isolated identity overlay. It is not fused because the\n"
        "pinned Kira topology has no defensible existing closed neck ring. This is not a\n"
        "candidate, not complete-adult-topology proof, and may not be bound or activated.\n\n"
        "Reference: Base Female Character by BlackProject, CC BY 4.0, Sketchfab.\n"
    )
    reset_pose(kira_armature)
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(config["review_blend"])))
    print(json.dumps({"ok": True, "status": decision["status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
