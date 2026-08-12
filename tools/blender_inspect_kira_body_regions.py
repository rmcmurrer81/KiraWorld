#!/usr/bin/env python3
"""Emit non-visual coordinate and weight evidence for a Kira body GLB.

This intentionally creates no render.  It is useful for private adult-body
work where the body may be inspected structurally but intimate imagery must
not be retained.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def bounds(points: list[Vector]) -> tuple[Vector, Vector]:
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def vector(value: Vector) -> list[float]:
    return [round(float(component), 8) for component in value]


def main() -> int:
    args = parse_args()
    source = Path(args.input).resolve(strict=True)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    arms = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    body = max(meshes, key=lambda obj: len(obj.data.vertices))
    points = [vertex.co.copy() for vertex in body.data.vertices]
    low, high = bounds(points)
    extent = high - low
    group_names = [group.name for group in body.vertex_groups]

    def region_count(z0: float, z1: float, x_fraction: float, y_front_fraction: float) -> int:
        center_x = (low.x + high.x) * 0.5
        front_y = low.y + extent.y * y_front_fraction
        return sum(
            1
            for point in points
            if low.z + extent.z * z0 <= point.z <= low.z + extent.z * z1
            and abs(point.x - center_x) <= extent.x * x_fraction
            and point.y <= front_y
        )

    shape_keys = []
    if body.data.shape_keys:
        shape_keys = [
            {"name": key.name, "value": round(float(key.value), 6)}
            for key in body.data.shape_keys.key_blocks
        ]

    group_stats: dict[str, object] = {}
    for wanted in (
        "mixamorig:Hips_01",
        "mixamorig:Spine_02",
        "mixamorig:Head_06",
        "mixamorig:LeftUpLeg_055",
        "mixamorig:RightUpLeg_060",
    ):
        group = body.vertex_groups.get(wanted)
        if group is None:
            continue
        weighted: list[tuple[Vector, float]] = []
        for vertex in body.data.vertices:
            weight = max(
                (
                    float(item.weight)
                    for item in vertex.groups
                    if int(item.group) == int(group.index)
                ),
                default=0.0,
            )
            if weight >= 0.25:
                weighted.append((vertex.co.copy(), weight))
        if weighted:
            weighted_low, weighted_high = bounds([item[0] for item in weighted])
            group_stats[wanted] = {
                "sample_count_weight_at_least_0.25": len(weighted),
                "local_low": vector(weighted_low),
                "local_high": vector(weighted_high),
            }

    bone_rest: dict[str, object] = {}
    if len(arms) == 1:
        for wanted in (
            "mixamorig:Hips_01",
            "mixamorig:Spine_02",
            "mixamorig:Head_06",
            "mixamorig:LeftUpLeg_055",
            "mixamorig:RightUpLeg_060",
        ):
            bone = arms[0].data.bones.get(wanted)
            if bone:
                bone_rest[wanted] = {
                    "head_local": vector(bone.head_local),
                    "tail_local": vector(bone.tail_local),
                }

    center_x = (low.x + high.x) * 0.5
    pelvis_front_grid: list[dict[str, object]] = []
    for z_center in (3.45, 3.55, 3.65, 3.75, 3.85, 3.95, 4.05):
        samples = [
            point
            for point in points
            if abs(point.x - center_x) <= 0.18 and abs(point.z - z_center) <= 0.035
        ]
        pelvis_front_grid.append(
            {
                "z_center_local": z_center,
                "sample_count": len(samples),
                "front_minimum_y": round(min((point.y for point in samples), default=0.0), 8),
                "back_maximum_y": round(max((point.y for point in samples), default=0.0), 8),
            }
        )
    chest_front_grid: list[dict[str, object]] = []
    for side, x_center in (("left", 0.31), ("right", -0.31)):
        for z_center in (5.20, 5.30, 5.40, 5.50, 5.60, 5.70):
            samples = [
                point
                for point in points
                if abs(point.x - x_center) <= 0.055 and abs(point.z - z_center) <= 0.035
            ]
            chest_front_grid.append(
                {
                    "side": side,
                    "x_center_local": x_center,
                    "z_center_local": z_center,
                    "sample_count": len(samples),
                    "front_minimum_y": round(min((point.y for point in samples), default=0.0), 8),
                }
            )

    evidence = {
        "schema_version": 1,
        "input": str(source),
        "non_visual_only": True,
        "mesh_count": len(meshes),
        "armature_count": len(arms),
        "body": {
            "name": body.name,
            "vertex_count": len(body.data.vertices),
            "polygon_count": len(body.data.polygons),
            "local_low": vector(low),
            "local_high": vector(high),
            "local_extent": vector(extent),
            "matrix_world": [
                [round(float(body.matrix_world[row][column]), 8) for column in range(4)]
                for row in range(4)
            ],
            "vertex_group_count": len(group_names),
            "vertex_group_names": group_names,
            "shape_keys": shape_keys,
            "weighted_region_stats": group_stats,
            "central_pelvis_front_grid": pelvis_front_grid,
            "chest_front_grid": chest_front_grid,
            "front_direction": "negative local Y, inherited from enrolled R5 evidence",
            "central_front_region_sample_counts": {
                "lower_pelvis_z_0.40_0.53": region_count(0.40, 0.53, 0.12, 0.38),
                "pelvis_z_0.43_0.50": region_count(0.43, 0.50, 0.08, 0.34),
                "lower_face_z_0.87_0.96": region_count(0.87, 0.96, 0.16, 0.30),
            },
        },
        "rig": {
            "bone_count": len(arms[0].data.bones) if len(arms) == 1 else None,
            "bone_names": [bone.name for bone in arms[0].data.bones] if len(arms) == 1 else [],
            "selected_rest_bones": bone_rest,
        },
        "truth_limit": "Coordinate/weight inventory only; no anatomy, fit, deformation, or runtime claim.",
    }
    output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output), "body": evidence["body"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
