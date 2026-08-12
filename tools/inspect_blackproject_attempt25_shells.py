#!/usr/bin/env python3
"""Read-only geometry inventory for the preserved R19 attempt-25 nail Blend."""

from __future__ import annotations

import json
import math

import bpy
from mathutils import Vector


PREFIX = "R19_BlackProject_"
SOURCE_NAIL_MESHES = {"Ariel_Mesh_Fingernails_0", "Ariel_Mesh_Toenails_0"}
GRID = 17


def _centroid(points: list[Vector]) -> Vector:
    return sum(points, Vector()) / len(points)


def _bone_segment_distance(point: Vector, head: Vector, tail: Vector) -> float:
    delta = tail - head
    if delta.length_squared <= 1.0e-16:
        return float((point - head).length)
    amount = max(0.0, min(1.0, float((point - head).dot(delta) / delta.length_squared)))
    return float((point - (head + delta * amount)).length)


def _grid_edges(points: list[Vector]) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    values: list[float] = []
    for row in range(GRID):
        for column in range(GRID):
            index = row * GRID + column
            if row + 1 < GRID:
                other = (row + 1) * GRID + column
                value = float((points[index] - points[other]).length)
                values.append(value)
                rows.append({"axis": "longitudinal", "a": index, "b": other, "length_m": value})
            if column + 1 < GRID:
                other = row * GRID + column + 1
                value = float((points[index] - points[other]).length)
                values.append(value)
                rows.append({"axis": "lateral", "a": index, "b": other, "length_m": value})
    rows.sort(key=lambda item: float(item["length_m"]), reverse=True)
    ordered = sorted(values)
    return {
        "maximum_neighbor_edge_m": max(values),
        "median_neighbor_edge_m": ordered[len(ordered) // 2],
        "largest_neighbors": rows[:12],
    }


def main() -> None:
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one armature, found {len(armatures)}")
    armature = armatures[0]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    generated = sorted(
        [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith(PREFIX)],
        key=lambda obj: obj.name,
    )
    rows = []
    for obj in generated:
        raw_points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        evaluated_obj = obj.evaluated_get(depsgraph)
        evaluated_mesh = evaluated_obj.to_mesh()
        try:
            evaluated_points = [
                evaluated_obj.matrix_world @ vertex.co for vertex in evaluated_mesh.vertices
            ]
        finally:
            evaluated_obj.to_mesh_clear()
        groups = [group.name for group in obj.vertex_groups]
        bone_name = groups[0] if len(groups) == 1 else ""
        bone = armature.data.bones.get(bone_name)
        if bone is None:
            head = tail = Vector((math.nan, math.nan, math.nan))
            raw_to_tail = raw_to_segment = math.nan
            evaluated_to_tail = evaluated_to_segment = math.nan
        else:
            head = armature.matrix_world @ bone.head_local
            tail = armature.matrix_world @ bone.tail_local
            raw_center = _centroid(raw_points)
            evaluated_center = _centroid(evaluated_points)
            raw_to_tail = float((raw_center - tail).length)
            raw_to_segment = _bone_segment_distance(raw_center, head, tail)
            evaluated_to_tail = float((evaluated_center - tail).length)
            evaluated_to_segment = _bone_segment_distance(evaluated_center, head, tail)
        rows.append(
            {
                "object": obj.name,
                "mesh": obj.data.name,
                "bone": bone_name,
                "raw_vertex_count": len(raw_points),
                "evaluated_vertex_count": len(evaluated_points),
                "raw_centroid_world_m": [float(value) for value in _centroid(raw_points)],
                "evaluated_centroid_world_m": [float(value) for value in _centroid(evaluated_points)],
                "bone_head_world_m": [float(value) for value in head],
                "bone_tail_world_m": [float(value) for value in tail],
                "raw_centroid_to_bone_tail_m": raw_to_tail,
                "raw_centroid_to_bone_segment_m": raw_to_segment,
                "evaluated_centroid_to_bone_tail_m": evaluated_to_tail,
                "evaluated_centroid_to_bone_segment_m": evaluated_to_segment,
                "raw_grid_edges": _grid_edges(raw_points),
                "materials": [slot.name if slot else "" for slot in obj.data.materials],
                "modifiers": [modifier.type for modifier in obj.modifiers],
            }
        )
    possible_source = sorted(
        {
            f"{obj.name}|{obj.data.name}"
            for obj in bpy.data.objects
            if obj.type == "MESH"
            and (
                obj.data.name in SOURCE_NAIL_MESHES
                or ("nail" in obj.name.lower() and not obj.name.startswith(PREFIX))
                or ("nail" in obj.data.name.lower() and not obj.name.startswith(PREFIX))
            )
        }
    )
    print(
        "BLACKPROJECT_ATTEMPT25_SHELL_INVENTORY="
        + json.dumps(
            {
                "generated_shell_count": len(generated),
                "generated_object_names": [obj.name for obj in generated],
                "possible_source_nail_objects_or_meshes": possible_source,
                "records": rows,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
