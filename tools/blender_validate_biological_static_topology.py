"""Validate the protected static foundation's single-surface topology."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy


source = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(source))
body = next(
    (
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and obj.name.startswith("BIOLOGICAL_ROBERT_STATIC_LIKENESS_")
    ),
    None,
)
if body is None or body.type != "MESH":
    raise SystemExit("missing integrated V2 body")
mesh = body.data
adjacency = [set() for _ in mesh.vertices]
edge_use = {}
for edge in mesh.edges:
    a, b = edge.vertices
    adjacency[a].add(b)
    adjacency[b].add(a)
    edge_use[tuple(sorted((a, b)))] = 0
for poly in mesh.polygons:
    ids = list(poly.vertices)
    for index, a in enumerate(ids):
        b = ids[(index + 1) % len(ids)]
        key = tuple(sorted((a, b)))
        edge_use[key] = edge_use.get(key, 0) + 1
remaining = set(range(len(mesh.vertices)))
components = []
vertex_component = {}
while remaining:
    seed = remaining.pop()
    stack = [seed]
    count = 1
    members = [seed]
    while stack:
        current = stack.pop()
        for neighbor in adjacency[current]:
            if neighbor in remaining:
                remaining.remove(neighbor)
                stack.append(neighbor)
                members.append(neighbor)
                count += 1
    components.append(count)
    component_id = len(components) - 1
    for member in members:
        vertex_component[member] = component_id
boundary_edges = sum(1 for count in edge_use.values() if count == 1)
nonmanifold_edges = sum(1 for count in edge_use.values() if count != 2)
separate_anatomy_objects = [
    obj.name for obj in bpy.context.scene.objects
    if obj != body and "External_Anatomy" in obj.name
]
material_names = [mat.name for mat in body.data.materials if mat]
armature_modifiers = [
    modifier.object.name for modifier in body.modifiers
    if modifier.type == "ARMATURE" and modifier.object
]
largest_component_id = max(range(len(components)), key=lambda index: components[index])
largest_component_vertices = {
    index for index, component_id in vertex_component.items()
    if component_id == largest_component_id
}
main_skin_boundary_edges = sum(
    1 for (a, b), count in edge_use.items()
    if count == 1 and a in largest_component_vertices and b in largest_component_vertices
)
main_skin_nonmanifold_edges = sum(
    1 for (a, b), count in edge_use.items()
    if count != 2 and a in largest_component_vertices and b in largest_component_vertices
)
anatomy_region_ids = [
    vertex.index for vertex in mesh.vertices
    if vertex.co.z < 0.82 and abs(vertex.co.x) < 0.10 and vertex.co.y < -0.03
]
anatomy_connected_to_primary_skin = bool(anatomy_region_ids) and all(
    vertex_component.get(index) == largest_component_id for index in anatomy_region_ids
)
regional_skin_variation = {
    "v1_texture_preserved": str(body.get("regional_skin_variation", "")).startswith(("PRESERVED_FROM_V1", "V1 ")),
    "base_skin": any(name == "MBLab_skin3" for name in material_names),
}
connection_pass = (
    not separate_anatomy_objects
    and anatomy_connected_to_primary_skin
    and all(regional_skin_variation.values())
)
strict_topology_pass = (
    connection_pass
    and len(components) == 1
    and boundary_edges == 0
    and nonmanifold_edges == 0
)
report = {
    "schema_version": 1,
    "status": "PASS" if strict_topology_pass else "FAIL",
    "narrow_anatomy_connection_status": "PASS" if connection_pass else "FAIL",
    "strict_topology_status": "PASS" if strict_topology_pass else "FAIL",
    "status_scope": "The narrow PASS proves anatomy-region component membership only; it is not likeness or visual realism approval.",
    "body_object": body.name,
    "mesh_objects_named_as_anatomy_components": separate_anatomy_objects,
    "connected_components": len(components),
    "component_vertex_counts": sorted(components, reverse=True),
    "vertices": len(mesh.vertices),
    "polygons": len(mesh.polygons),
    "boundary_edges": boundary_edges,
    "nonmanifold_edges": nonmanifold_edges,
    "main_skin_boundary_edges": main_skin_boundary_edges,
    "main_skin_nonmanifold_edges": main_skin_nonmanifold_edges,
    "material_names": material_names,
    "anatomy_connected_to_primary_skin": anatomy_connected_to_primary_skin,
    "anatomy_visual_integration": "BLOCKED — CONNECTED TO PRIMARY SKIN, BUT SIDE-VIEW FORM REMAINS STRUCTURALLY TOO CRUDE",
    "regional_skin_variation": regional_skin_variation,
    "armature_bindings": armature_modifiers,
    "rig_binding_status": body.get("rig_binding_status", ""),
    "adult_topology_estimation": body.get("adult_topology_estimation", ""),
    "runtime_activation_allowed": False,
    "owner_review_required": True,
}
target = source.parent / "TOPOLOGY_INTEGRATION_REPORT.json"
target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report))
