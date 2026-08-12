#!/usr/bin/env python3
"""Measure the inactive R2 neck boundaries and squat outliers for R3 authoring.

This is a read-only Blender probe.  It opens an existing review Blend supplied
on Blender's command line and writes JSON only; it never exports or binds an
avatar candidate.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def boundary_parts(obj: bpy.types.Object) -> list[dict[str, object]]:
    edge_use: defaultdict[tuple[int, int], int] = defaultdict(int)
    for polygon in obj.data.polygons:
        values = list(map(int, polygon.vertices))
        for index, a in enumerate(values):
            b = values[(index + 1) % len(values)]
            edge_use[tuple(sorted((a, b)))] += 1
    boundary = [edge for edge, count in edge_use.items() if count == 1]
    graph: defaultdict[int, list[int]] = defaultdict(list)
    for a, b in boundary:
        graph[a].append(b)
        graph[b].append(a)
    seen: set[int] = set()
    result: list[dict[str, object]] = []
    for start in graph:
        if start in seen:
            continue
        todo = deque([start])
        seen.add(start)
        indices: list[int] = []
        while todo:
            current = todo.popleft()
            indices.append(current)
            for neighbor in graph[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    todo.append(neighbor)
        points = [obj.matrix_world @ obj.data.vertices[index].co for index in indices]
        center = sum(points, Vector()) / len(points)
        radii = [math.hypot(point.x - center.x, point.y - center.y) for point in points]
        result.append(
            {
                "vertex_count": len(indices),
                "closed_cycle": all(len(graph[index]) == 2 for index in indices),
                "z_min": min(point.z for point in points),
                "z_max": max(point.z for point in points),
                "center": list(center),
                "radial_min": min(radii),
                "radial_mean": sum(radii) / len(radii),
                "radial_max": max(radii),
                "indices": sorted(indices),
            }
        )
    return result


def reset_pose(armature: bpy.types.Object) -> None:
    for bone in armature.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.location = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()


def cut_keep_above(obj: bpy.types.Object, cut_z: float) -> None:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(
        bm,
        geom=geom,
        dist=1e-7,
        plane_co=Vector((0.0, 0.0, cut_z)),
        plane_no=Vector((0.0, 0.0, 1.0)),
        clear_inner=True,
        clear_outer=False,
    )
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def evaluated_vertices(obj: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def vertex_weights(obj: bpy.types.Object, index: int) -> list[tuple[str, float]]:
    names = {group.index: group.name for group in obj.vertex_groups}
    return sorted(
        (
            (names[assignment.group], round(float(assignment.weight), 6))
            for assignment in obj.data.vertices[index].groups
            if assignment.weight > 1e-8
        ),
        key=lambda item: (-item[1], item[0]),
    )


def smooth_pair_band(
    obj: bpy.types.Object,
    first: str,
    second: str,
    z_low: float,
    z_high: float,
    iterations: int,
    strength: float,
    side_sign: int,
) -> dict[str, object]:
    groups = {group.name: group for group in obj.vertex_groups}
    a_group = groups[first]
    b_group = groups[second]
    adjacency: list[list[int]] = [[] for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = map(int, edge.vertices)
        adjacency[a].append(b)
        adjacency[b].append(a)

    def pair_value(index: int) -> tuple[float, float, float]:
        values = {name: weight for name, weight in vertex_weights(obj, index)}
        a = values.get(first, 0.0)
        b = values.get(second, 0.0)
        total = a + b
        return ((a / total) if total > 1e-8 else 0.0, total, min(a, b))

    eligible = [
        vertex.index
        for vertex in obj.data.vertices
        if z_low <= (obj.matrix_world @ vertex.co).z <= z_high
        and (obj.matrix_world @ vertex.co).x * side_sign >= -1e-6
        and pair_value(vertex.index)[1] > 0.90
        and pair_value(vertex.index)[2] > 1e-5
    ]
    max_delta = 0.0
    for _ in range(iterations):
        previous = {index: pair_value(index)[:2] for index in eligible}
        updates: dict[int, tuple[float, float]] = {}
        for index in eligible:
            own, total = previous[index]
            neighbors = [
                neighbor
                for neighbor in adjacency[index]
                if neighbor in previous
            ]
            if not neighbors:
                continue
            mean = sum(previous[neighbor][0] for neighbor in neighbors) / len(neighbors)
            value = own * (1.0 - strength) + mean * strength
            updates[index] = (value, total)
            max_delta = max(max_delta, abs(value - own))
        for index, (value, total) in updates.items():
            a_group.add([index], value * total, "REPLACE")
            b_group.add([index], (1.0 - value) * total, "REPLACE")
    return {
        "groups": [first, second],
        "z_band": [z_low, z_high],
        "iterations": iterations,
        "strength": strength,
        "side_sign": side_sign,
        "eligible_vertices": len(eligible),
        "max_normalized_pair_delta_per_iteration": round(max_delta, 9),
    }


def squat_metrics(obj: bpy.types.Object, armature: bpy.types.Object) -> dict[str, object]:
    reset_pose(armature)
    rest = evaluated_vertices(obj)
    rotations = {
        "mixamorig:LeftUpLeg_055": (math.radians(34), 0.0, math.radians(5)),
        "mixamorig:RightUpLeg_060": (math.radians(34), 0.0, math.radians(-5)),
        "mixamorig:LeftLeg_056": (math.radians(-55), 0.0, 0.0),
        "mixamorig:RightLeg_061": (math.radians(-55), 0.0, 0.0),
        "mixamorig:Spine_02": (math.radians(-12), 0.0, 0.0),
    }
    for name, rotation in rotations.items():
        armature.pose.bones[name].rotation_euler = rotation
    bpy.context.view_layer.update()
    current = evaluated_vertices(obj)
    ratios = []
    for edge in obj.data.edges:
        a, b = map(int, edge.vertices)
        base = (rest[a] - rest[b]).length
        if base > 1e-9:
            ratios.append((current[a] - current[b]).length / base)
    ordered = sorted(ratios)
    reset_pose(armature)
    return {
        "minimum": min(ordered),
        "p05": ordered[round((len(ordered) - 1) * 0.05)],
        "p95": ordered[round((len(ordered) - 1) * 0.95)],
        "maximum": max(ordered),
        "under_half": sum(value < 0.5 for value in ordered),
        "over_2x": sum(value > 2.0 for value in ordered),
        "fraction_under_half": sum(value < 0.5 for value in ordered) / len(ordered),
        "fraction_over_2x": sum(value > 2.0 for value in ordered) / len(ordered),
    }


def main() -> int:
    args = parse_args()
    surface = bpy.data.objects.get("Kira_R7_Adult_Surface_Trial")
    head = bpy.data.objects.get("Exact_Kira_R6_Head_Reference_Only")
    if surface is None or head is None:
        raise RuntimeError("R2 review surface/head objects were not found")
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE" and len(obj.data.bones) == 79]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one exact 79-joint cage, found {len(armatures)}")
    armature = armatures[0]
    reset_pose(armature)
    rest = evaluated_vertices(surface)
    rotations = {
        "mixamorig:LeftUpLeg_055": (math.radians(34), 0.0, math.radians(5)),
        "mixamorig:RightUpLeg_060": (math.radians(34), 0.0, math.radians(-5)),
        "mixamorig:LeftLeg_056": (math.radians(-55), 0.0, 0.0),
        "mixamorig:RightLeg_061": (math.radians(-55), 0.0, 0.0),
        "mixamorig:Spine_02": (math.radians(-12), 0.0, 0.0),
    }
    for name, rotation in rotations.items():
        armature.pose.bones[name].rotation_euler = rotation
    bpy.context.view_layer.update()
    current = evaluated_vertices(surface)

    bad: list[dict[str, object]] = []
    dominant_pairs: Counter[str] = Counter()
    z_bins: Counter[str] = Counter()
    for edge in surface.data.edges:
        a, b = map(int, edge.vertices)
        rest_length = (rest[a] - rest[b]).length
        if rest_length <= 1e-9:
            continue
        ratio = (current[a] - current[b]).length / rest_length
        if ratio >= 0.5:
            continue
        wa = vertex_weights(surface, a)
        wb = vertex_weights(surface, b)
        pair = " | ".join(sorted((wa[0][0] if wa else "NONE", wb[0][0] if wb else "NONE")))
        dominant_pairs[pair] += 1
        mid = (rest[a] + rest[b]) * 0.5
        z_bins[f"{math.floor(mid.z * 20) / 20:.2f}"] += 1
        bad.append(
            {
                "edge": [a, b],
                "ratio": round(ratio, 9),
                "rest_midpoint": [round(float(value), 9) for value in mid],
                "weights_a": wa,
                "weights_b": wb,
            }
        )
    reset_pose(armature)
    record = {
        "surface": {
            "vertices": len(surface.data.vertices),
            "polygons": len(surface.data.polygons),
            "boundary_parts": boundary_parts(surface),
        },
        "head": {
            "vertices": len(head.data.vertices),
            "polygons": len(head.data.polygons),
            "boundary_parts": boundary_parts(head),
        },
        "candidate_head_cut_boundaries": {},
        "bones": {
            name: {
                "head": list(armature.matrix_world @ armature.data.bones[name].head_local),
                "tail": list(armature.matrix_world @ armature.data.bones[name].tail_local),
            }
            for name in (
                "mixamorig:Hips_01",
                "mixamorig:Spine_02",
                "mixamorig:Neck_05",
                "mixamorig:Head_06",
                "mixamorig:LeftUpLeg_055",
                "mixamorig:RightUpLeg_060",
            )
        },
        "squat_edges_under_half": bad,
        "squat_edge_count_under_half": len(bad),
        "dominant_group_pairs": dict(dominant_pairs.most_common()),
        "midpoint_z_bins": dict(sorted(z_bins.items())),
        "weight_smoothing_trials": {},
    }
    neck_z = float((armature.matrix_world @ armature.data.bones["mixamorig:Neck_05"].head_local).z)
    head_z = float((armature.matrix_world @ armature.data.bones["mixamorig:Head_06"].head_local).z)
    for fraction in (0.20, 0.35, 0.50, 0.65, 0.80):
        cut_z = neck_z + (head_z - neck_z) * fraction
        clone = head.copy()
        clone.data = head.data.copy()
        bpy.context.scene.collection.objects.link(clone)
        cut_keep_above(clone, cut_z)
        record["candidate_head_cut_boundaries"][f"neck_to_head_{fraction:.2f}"] = {
            "cut_z": cut_z,
            "vertices": len(clone.data.vertices),
            "polygons": len(clone.data.polygons),
            "boundary_parts": boundary_parts(clone),
        }
        bpy.data.objects.remove(clone, do_unlink=True)
    for iterations in (1, 2, 4, 8):
        clone = surface.copy()
        clone.data = surface.data.copy()
        bpy.context.scene.collection.objects.link(clone)
        repairs = []
        for side in ("Left", "Right"):
            repairs.append(
                smooth_pair_band(
                    clone,
                    f"mixamorig:{side}UpLeg_0{'55' if side == 'Left' else '60'}",
                    f"mixamorig:{side}Leg_0{'56' if side == 'Left' else '61'}",
                    0.27,
                    0.38,
                    iterations,
                    0.5,
                    1 if side == "Left" else -1,
                )
            )
            repairs.append(
                smooth_pair_band(
                    clone,
                    "mixamorig:Hips_01",
                    f"mixamorig:{side}UpLeg_0{'55' if side == 'Left' else '60'}",
                    0.50,
                    0.60,
                    iterations,
                    0.5,
                    1 if side == "Left" else -1,
                )
            )
        record["weight_smoothing_trials"][f"iterations_{iterations}"] = {
            "repairs": repairs,
            "squat": squat_metrics(clone, armature),
        }
        bpy.data.objects.remove(clone, do_unlink=True)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output), "bad_edges": len(bad)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
