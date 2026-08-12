from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def boundary_components(obj: bpy.types.Object) -> list[dict[str, object]]:
    """Return compact connected boundary-loop measurements for mesh diagnosis."""

    edge_use: dict[tuple[int, int], int] = {}
    for polygon in obj.data.polygons:
        indices = list(polygon.vertices)
        for index, first in enumerate(indices):
            second = indices[(index + 1) % len(indices)]
            edge = tuple(sorted((int(first), int(second))))
            edge_use[edge] = edge_use.get(edge, 0) + 1
    adjacency: dict[int, set[int]] = {}
    for (first, second), count in edge_use.items():
        if count != 1:
            continue
        adjacency.setdefault(first, set()).add(second)
        adjacency.setdefault(second, set()).add(first)
    pending = set(adjacency)
    result: list[dict[str, object]] = []
    while pending:
        stack = [pending.pop()]
        component: set[int] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            for neighbor in adjacency.get(current, ()):
                if neighbor not in component:
                    pending.discard(neighbor)
                    stack.append(neighbor)
        points = [obj.matrix_world @ obj.data.vertices[index].co for index in component]
        low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
        high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
        center = (low + high) * 0.5
        result.append(
            {
                "vertex_count": len(component),
                "center": [round(float(value), 6) for value in center],
                "size": [round(float(value), 6) for value in high - low],
            }
        )
    return sorted(result, key=lambda item: int(item["vertex_count"]), reverse=True)


def mesh_components(obj: bpy.types.Object) -> list[dict[str, object]]:
    """Measure disconnected surface islands without modifying the model."""

    parent = list(range(len(obj.data.vertices)))

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
    for polygon in obj.data.polygons:
        indices = [int(value) for value in polygon.vertices]
        if not indices:
            continue
        used.update(indices)
        for value in indices[1:]:
            union(indices[0], value)
    groups: dict[int, list[int]] = {}
    for index in used:
        groups.setdefault(find(index), []).append(index)
    result: list[dict[str, object]] = []
    for indices in groups.values():
        points = [obj.matrix_world @ obj.data.vertices[index].co for index in indices]
        low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
        high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
        center = (low + high) * 0.5
        result.append(
            {
                "vertex_count": len(indices),
                "center": [round(float(value), 6) for value in center],
                "size": [round(float(value), 6) for value in high - low],
                "bounds_low": [round(float(value), 6) for value in low],
                "bounds_high": [round(float(value), 6) for value in high],
            }
        )
    return sorted(result, key=lambda item: int(item["vertex_count"]), reverse=True)


def bounds_for(obj: bpy.types.Object) -> dict[str, object]:
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    mins = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    maxs = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    size = maxs - mins
    return {
        "name": obj.name,
        "type": obj.type,
        "vertices": len(obj.data.vertices) if getattr(obj, "data", None) and hasattr(obj.data, "vertices") else 0,
        "min": [round(v, 5) for v in mins],
        "max": [round(v, 5) for v in maxs],
        "size": [round(v, 5) for v in size],
    }


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if not argv:
        raise SystemExit("usage: blender --background --python tools/inspect_glb_in_blender.py -- path.glb [...]")
    result: dict[str, object] = {}
    for raw in argv:
        path = Path(raw)
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()
        bpy.ops.import_scene.gltf(filepath=str(path))
        meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        armature_objects = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
        armatures = [obj.name for obj in armature_objects]
        result[str(path)] = {
            "mesh_count": len(meshes),
            "armatures": armatures,
            "armature_details": [
                {
                    "name": obj.name,
                    "bone_count": len(obj.data.bones),
                    "bones": [bone.name for bone in obj.data.bones],
                }
                for obj in armature_objects
            ],
            "meshes": [bounds_for(obj) for obj in meshes[:40]],
            "mesh_bindings": [
                {
                    "name": obj.name,
                    "parent": obj.parent.name if obj.parent else "",
                    "parent_type": obj.parent_type,
                    "location": [round(float(value), 7) for value in obj.location],
                    "rotation_euler": [round(float(value), 7) for value in obj.rotation_euler],
                    "scale": [round(float(value), 7) for value in obj.scale],
                    "matrix_world": [
                        [round(float(value), 7) for value in row]
                        for row in obj.matrix_world
                    ],
                    "matrix_parent_inverse": [
                        [round(float(value), 7) for value in row]
                        for row in obj.matrix_parent_inverse
                    ],
                    "vertex_group_count": len(obj.vertex_groups),
                    "vertex_groups": [group.name for group in obj.vertex_groups],
                    "modifiers": [
                        {
                            "name": modifier.name,
                            "type": modifier.type,
                            "object": (
                                modifier.object.name
                                if hasattr(modifier, "object") and modifier.object
                                else ""
                            ),
                        }
                        for modifier in obj.modifiers
                    ],
                }
                for obj in meshes[:40]
            ],
            "boundary_components": {
                obj.name: boundary_components(obj)[:40] for obj in meshes[:40]
            },
            "head_boundary_components": {
                obj.name: [
                    component
                    for component in boundary_components(obj)
                    if float(component["center"][2]) > 0.85
                ][:80]
                for obj in meshes[:40]
            },
            "mesh_components": {
                obj.name: mesh_components(obj)[:120] for obj in meshes[:40]
            },
            "animations": [action.name for action in bpy.data.actions],
        }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
