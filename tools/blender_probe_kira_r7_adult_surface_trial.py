#!/usr/bin/env python3
"""Read-only geometry probe for the inactive Kira R7 adult-surface trial."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


ROOT = Path(r"C:\Users\robmc\Kira")
KIRA = ROOT / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6/r6_20260718_163658/kira_provisional_body_r6.glb"
REFERENCE = Path(r"C:\Users\robmc\Desktop\5\base_female_character.glb")
OUT = ROOT / "Data/avatar_builder_workspace_tests/kira_r7_adult_surface_trial_20260722/probe.json"
BODY = {
    "Ariel_Mesh_Torso_0",
    "Ariel_Mesh_Arms_0",
    "Ariel_Mesh_Legs_0",
    "Ariel_Mesh_Fingernails_0",
    "Ariel_Mesh_Toenails_0",
    "Ariel_Mesh_Genitalia_0",
}


def imported(path: Path) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [obj for obj in bpy.data.objects if obj not in before]


def head(arm: bpy.types.Object, name: str) -> Vector:
    return arm.matrix_world @ arm.data.bones[name].head_local


def bounds(points: list[Vector]) -> dict[str, list[float]]:
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    return {"low": list(low), "high": list(high), "size": list(high - low)}


def components(obj: bpy.types.Object) -> list[int]:
    links: list[list[int]] = [[] for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = edge.vertices
        links[a].append(b)
        links[b].append(a)
    seen: set[int] = set()
    result: list[int] = []
    for start in range(len(links)):
        if start in seen:
            continue
        todo = deque([start])
        seen.add(start)
        size = 0
        while todo:
            here = todo.popleft()
            size += 1
            for other in links[here]:
                if other not in seen:
                    seen.add(other)
                    todo.append(other)
        result.append(size)
    return sorted(result, reverse=True)


def nearest_summary(a: bpy.types.Object, b: bpy.types.Object, scale: float, ref_hips: Vector, kira_hips: Vector) -> dict[str, object]:
    points_b = [kira_hips + (b.matrix_world @ v.co - ref_hips) * scale for v in b.data.vertices]
    tree = KDTree(len(points_b))
    for index, point in enumerate(points_b):
        tree.insert(point, index)
    tree.balance()
    distances = []
    under = defaultdict(int)
    for vertex in a.data.vertices:
        point = kira_hips + (a.matrix_world @ vertex.co - ref_hips) * scale
        _co, _index, distance = tree.find(point)
        distances.append(float(distance))
        for threshold in (1e-7, 1e-6, 1e-5, 1e-4, 5e-4, 1e-3, 5e-3):
            if distance <= threshold:
                under[str(threshold)] += 1
    distances.sort()
    return {
        "a": a.data.name,
        "b": b.data.name,
        "minimum_m": distances[0],
        "p01_m": distances[max(0, round((len(distances) - 1) * 0.01))],
        "p05_m": distances[max(0, round((len(distances) - 1) * 0.05))],
        "counts_a_vertices_with_nearest_b_under_m": dict(under),
    }


def main() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    kira_objects = imported(KIRA)
    reference_objects = imported(REFERENCE)
    kira_arm = next(obj for obj in kira_objects if obj.type == "ARMATURE")
    ref_arm = next(obj for obj in reference_objects if obj.type == "ARMATURE")
    meshes = {obj.data.name: obj for obj in reference_objects if obj.type == "MESH" and obj.data.name in BODY}
    kira_hips = head(kira_arm, "mixamorig:Hips_01")
    kira_head = head(kira_arm, "mixamorig:Head_06")
    # `hip_03` is the source root at world zero.  `pelvis_04` is the actual
    # anatomical hip landmark and must be used for proportion fitting.
    ref_hips = head(ref_arm, "pelvis_04")
    ref_head = head(ref_arm, "head_091")
    scale = (kira_head - kira_hips).length / (ref_head - ref_hips).length
    bone_names = [
        "mixamorig:Hips_01", "mixamorig:Spine_02", "mixamorig:Spine1_03",
        "mixamorig:Spine2_04", "mixamorig:Neck_05", "mixamorig:Head_06",
        "mixamorig:LeftShoulder_08", "mixamorig:LeftArm_09",
        "mixamorig:LeftUpLeg_055", "mixamorig:LeftLeg_056", "mixamorig:LeftFoot_057",
    ]
    fitted_bounds = {}
    for name, obj in meshes.items():
        points = [kira_hips + (obj.matrix_world @ v.co - ref_hips) * scale for v in obj.data.vertices]
        fitted_bounds[name] = bounds(points)
    torso = meshes["Ariel_Mesh_Torso_0"]
    group_names = {group.index: group.name for group in torso.vertex_groups}
    neck_z = head(kira_arm, "mixamorig:Neck_05").z
    head_z = head(kira_arm, "mixamorig:Head_06").z
    z_bins = defaultdict(int)
    weights_above = defaultdict(int)
    for vertex in torso.data.vertices:
        point = kira_hips + (torso.matrix_world @ vertex.co - ref_hips) * scale
        if point.z >= neck_z:
            z_bins["at_or_above_neck"] += 1
        if point.z >= (neck_z + head_z) * 0.5:
            z_bins["at_or_above_neck_head_mid"] += 1
        if point.z >= head_z:
            z_bins["at_or_above_head"] += 1
        if point.z >= neck_z:
            for assignment in vertex.groups:
                if assignment.weight > 1e-4:
                    weights_above[group_names[assignment.group]] += 1
    result = {
        "kira_bone_heads_world": {name: list(head(kira_arm, name)) for name in bone_names},
        "reference_landmarks_world": {
            bone.name: list(ref_arm.matrix_world @ bone.head_local)
            for bone in ref_arm.data.bones
            if bone.name.startswith(("hip_", "pelvis_", "abdomenLower_", "abdomenUpper_", "chestLower_", "chestUpper_", "neckLower_", "neckUpper_", "head_", "lThighBend_", "lShin_", "lFoot_"))
        },
        "global_scale": scale,
        "fitted_bounds": fitted_bounds,
        "component_sizes": {name: components(obj) for name, obj in meshes.items()},
        "torso_cut_probe": {
            "neck_z": neck_z,
            "head_z": head_z,
            "counts": dict(z_bins),
            "positive_groups_above_neck": dict(sorted(weights_above.items())),
        },
        "nearest_part_pairs": [
            nearest_summary(meshes["Ariel_Mesh_Torso_0"], meshes["Ariel_Mesh_Arms_0"], scale, ref_hips, kira_hips),
            nearest_summary(meshes["Ariel_Mesh_Torso_0"], meshes["Ariel_Mesh_Legs_0"], scale, ref_hips, kira_hips),
            nearest_summary(meshes["Ariel_Mesh_Arms_0"], meshes["Ariel_Mesh_Torso_0"], scale, ref_hips, kira_hips),
            nearest_summary(meshes["Ariel_Mesh_Legs_0"], meshes["Ariel_Mesh_Torso_0"], scale, ref_hips, kira_hips),
            nearest_summary(meshes["Ariel_Mesh_Arms_0"], meshes["Ariel_Mesh_Fingernails_0"], scale, ref_hips, kira_hips),
            nearest_summary(meshes["Ariel_Mesh_Legs_0"], meshes["Ariel_Mesh_Toenails_0"], scale, ref_hips, kira_hips),
            nearest_summary(meshes["Ariel_Mesh_Torso_0"], meshes["Ariel_Mesh_Genitalia_0"], scale, ref_hips, kira_hips),
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


main()
