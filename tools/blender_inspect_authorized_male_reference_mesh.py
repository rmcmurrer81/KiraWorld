"""Inspect the authorized adult male structural-reference mesh.

This script is diagnostic only.  It records object/component bounds and local
pelvis connectivity so the Avatar Builder can author its own bounded topology
without transferring the reference person's full body or identity surface.
"""

from __future__ import annotations

import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/avatar_builder/asset_library/adult_anatomy_reference/"
    "male_nude_2_a30390340f.glb"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/male_nude_2_mesh_structure.json"
)


def connected_components(bm: bmesh.types.BMesh):
    unseen = set(bm.verts)
    result = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        component = [seed]
        while stack:
            vertex = stack.pop()
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other in unseen:
                    unseen.remove(other)
                    stack.append(other)
                    component.append(other)
        result.append(component)
    return result


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))

objects = []
for obj in bpy.context.scene.objects:
    if obj.type != "MESH":
        continue
    world_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    components = connected_components(bm)
    component_rows = []
    for component in sorted(components, key=len, reverse=True):
        world = [obj.matrix_world @ vertex.co for vertex in component]
        component_rows.append(
            {
                "vertex_count": len(component),
                "min": [min(co[axis] for co in world) for axis in range(3)],
                "max": [max(co[axis] for co in world) for axis in range(3)],
                "center": [
                    sum(co[axis] for co in world) / len(world)
                    for axis in range(3)
                ],
            }
        )
    bm.free()
    objects.append(
        {
            "name": obj.name,
            "vertex_count": len(obj.data.vertices),
            "edge_count": len(obj.data.edges),
            "polygon_count": len(obj.data.polygons),
            "material_names": [
                material.name if material else None
                for material in obj.data.materials
            ],
            "bounds": {
                "min": [
                    min(co[axis] for co in world_corners)
                    for axis in range(3)
                ],
                "max": [
                    max(co[axis] for co in world_corners)
                    for axis in range(3)
                ],
            },
            "connected_components": component_rows,
        }
    )

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(
    json.dumps(
        {
            "source": str(SOURCE),
            "use": "STRUCTURAL GUIDANCE ONLY",
            "full_body_identity_surface_transfer_allowed": False,
            "objects": objects,
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(OUT)
