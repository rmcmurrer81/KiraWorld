"""Emit a compact, read-only Blender audit for potential avatar source GLBs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def _clear() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for datablocks in (bpy.data.meshes, bpy.data.armatures, bpy.data.actions):
        for datablock in list(datablocks):
            datablocks.remove(datablock)
    for image in list(bpy.data.images):
        bpy.data.images.remove(image)


def _bounds(objects: list[bpy.types.Object]) -> dict[str, list[float]]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    if not points:
        return {"low": [], "high": [], "size": [], "center": []}
    low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    return {
        "low": [round(float(value), 6) for value in low],
        "high": [round(float(value), 6) for value in high],
        "size": [round(float(value), 6) for value in high - low],
        "center": [round(float(value), 6) for value in (low + high) * 0.5],
    }


def _mesh_components(obj: bpy.types.Object) -> list[dict[str, object]]:
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    parent = list(range(len(mesh.vertices)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first: int, second: int) -> None:
        left, right = find(first), find(second)
        if left != right:
            parent[right] = left

    used: set[int] = set()
    for polygon in mesh.polygons:
        indices = [int(value) for value in polygon.vertices]
        if not indices:
            continue
        used.update(indices)
        for value in indices[1:]:
            union(indices[0], value)
    groups: dict[int, list[int]] = {}
    for index in used:
        groups.setdefault(find(index), []).append(index)
    details: list[dict[str, object]] = []
    for indices in groups.values():
        points = [evaluated.matrix_world @ mesh.vertices[index].co for index in indices]
        low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
        high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
        details.append(
            {
                "vertices": len(indices),
                "low": [round(float(value), 6) for value in low],
                "high": [round(float(value), 6) for value in high],
                "size": [round(float(value), 6) for value in high - low],
            }
        )
    result = sorted(details, key=lambda item: int(item["vertices"]), reverse=True)
    evaluated.to_mesh_clear()
    return result


def _mesh_info(obj: bpy.types.Object) -> dict[str, object]:
    influences = [len(vertex.groups) for vertex in obj.data.vertices]
    edge_use: dict[tuple[int, int], int] = {}
    for polygon in obj.data.polygons:
        indices = [int(value) for value in polygon.vertices]
        for index, first in enumerate(indices):
            edge = tuple(sorted((first, indices[(index + 1) % len(indices)])))
            edge_use[edge] = edge_use.get(edge, 0) + 1
    shape_keys = []
    if obj.data.shape_keys:
        shape_keys = [block.name for block in obj.data.shape_keys.key_blocks]
    assignments: dict[int, int] = {}
    for vertex in obj.data.vertices:
        for assignment in vertex.groups:
            if assignment.weight > 0.00001:
                assignments[assignment.group] = assignments.get(assignment.group, 0) + 1
    role_tokens = ("eye", "blink", "jaw", "lip", "cheek", "corner", "eyebrow", "teeth", "finger", "thumb", "cape", "braid")
    role_weight_counts = {
        group.name: assignments.get(group.index, 0)
        for group in obj.vertex_groups
        if any(token in group.name.lower() for token in role_tokens)
        and assignments.get(group.index, 0) > 0
    }
    components = _mesh_components(obj)
    return {
        "name": obj.name,
        "data_name": obj.data.name,
        "vertices": len(obj.data.vertices),
        "polygons": len(obj.data.polygons),
        "triangles": sum(max(1, len(poly.vertices) - 2) for poly in obj.data.polygons),
        "materials": [material.name for material in obj.data.materials if material],
        "bounds": _bounds([obj]),
        "connected_surface_islands": len(components),
        "surface_island_details": components,
        "boundary_edge_count": sum(1 for count in edge_use.values() if count == 1),
        "vertex_group_count": len(obj.vertex_groups),
        "unweighted_vertex_count": sum(1 for count in influences if count == 0),
        "maximum_influences_per_vertex": max(influences, default=0),
        "shape_keys": shape_keys,
        "role_weighted_vertex_counts": role_weight_counts,
        "armature_modifiers": [
            modifier.object.name if modifier.object else ""
            for modifier in obj.modifiers
            if modifier.type == "ARMATURE"
        ],
    }


def _action_info(action: bpy.types.Action, armature: bpy.types.Object) -> dict[str, object]:
    armature.animation_data_create()
    armature.animation_data.action = action
    start, end = (float(value) for value in action.frame_range)
    samples = sorted({int(round(start)), int(round((start + end) * 0.5)), int(round(end))})
    matrices: dict[str, list[tuple[float, ...]]] = {bone.name: [] for bone in armature.pose.bones}
    for frame in samples:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        for bone in armature.pose.bones:
            matrices[bone.name].append(tuple(float(value) for row in bone.matrix_basis for value in row))
    moving: list[str] = []
    for name, values in matrices.items():
        first = values[0]
        if any(max(abs(left - right) for left, right in zip(first, current)) > 0.00001 for current in values[1:]):
            moving.append(name)
    face_tokens = ("eye", "blink", "jaw", "lip", "cheek", "corner", "eyebrow", "teeth", "forehead")
    return {
        "name": action.name,
        "frame_range": [start, end],
        "slot_count": len(action.slots),
        "sampled_frames": samples,
        "moving_bone_count": len(moving),
        "moving_face_bones": [name for name in moving if any(token in name.lower() for token in face_tokens)],
    }


def inspect(path: Path) -> dict[str, object]:
    _clear()
    bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.view_layer.update()
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    skinned = [obj for obj in meshes if any(mod.type == "ARMATURE" for mod in obj.modifiers)]
    unskinned = [obj for obj in meshes if obj not in skinned]
    return {
        "path": str(path),
        "mesh_count": len(meshes),
        "skinned_mesh_count": len(skinned),
        "unskinned_meshes": [obj.name for obj in unskinned],
        "character_bounds_skinned_only": _bounds(skinned),
        "meshes": [_mesh_info(obj) for obj in meshes],
        "armatures": [
            {
                "name": obj.name,
                "bone_count": len(obj.data.bones),
                "deform_bone_count": sum(1 for bone in obj.data.bones if bone.use_deform),
                "bones": [bone.name for bone in obj.data.bones],
            }
            for obj in armatures
        ],
        "animations": [_action_info(action, armatures[0]) for action in bpy.data.actions] if armatures else [],
        "images": [
            {"name": image.name, "size": [int(image.size[0]), int(image.size[1])], "packed": image.packed_file is not None}
            for image in bpy.data.images
        ],
    }


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if not argv:
        raise SystemExit("usage: blender --background --python tools/audit_glb_avatar_source.py -- model.glb [...]")
    print("AVATAR_SOURCE_AUDIT_JSON_BEGIN")
    print(json.dumps([inspect(Path(raw)) for raw in argv], indent=2))
    print("AVATAR_SOURCE_AUDIT_JSON_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
