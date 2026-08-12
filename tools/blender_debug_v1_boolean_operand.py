"""Read-only Boolean diagnostics for the clean V1 primary skin."""

from pathlib import Path

import bmesh
import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects["BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"]
for modifier in list(body.modifiers):
    if modifier.type in {"ARMATURE", "CORRECTIVE_SMOOTH"}:
        bpy.context.view_layer.objects.active = body
        body.select_set(True)
        bpy.ops.object.modifier_apply(modifier=modifier.name)

mesh = body.data
adjacency = [set() for _ in mesh.vertices]
for edge in mesh.edges:
    a, b = edge.vertices
    adjacency[a].add(b)
    adjacency[b].add(a)
remaining = set(range(len(mesh.vertices)))
components = []
while remaining:
    seed = remaining.pop()
    members = {seed}
    stack = [seed]
    while stack:
        current = stack.pop()
        for neighbor in adjacency[current]:
            if neighbor in remaining:
                remaining.remove(neighbor)
                members.add(neighbor)
                stack.append(neighbor)
    components.append(members)
largest = max(components, key=len)

bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
bmesh.ops.delete(
    bm, geom=[vertex for vertex in bm.verts if vertex.index not in largest],
    context="VERTS",
)
print("primary", len(bm.verts), len(bm.faces), sum(e.is_boundary for e in bm.edges))
boundaries = [edge for edge in bm.edges if edge.is_boundary]
bmesh.ops.holes_fill(bm, edges=boundaries, sides=0)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
print(
    "closed",
    len(bm.verts),
    len(bm.faces),
    sum(e.is_boundary for e in bm.edges),
    bm.calc_volume(signed=True),
)
bm.to_mesh(mesh)
bm.free()
mesh.update()

for label, location, scale in (
    ("outside", (0.0, -0.5, 0.75), (0.05, 0.05, 0.05)),
    ("intersect", (0.0, -0.12, 0.79), (0.08, 0.08, 0.08)),
    ("front_020", (0.0, -0.20, 0.79), (0.08, 0.08, 0.08)),
    ("front_026", (0.0, -0.26, 0.79), (0.08, 0.08, 0.08)),
    ("front_032", (0.0, -0.32, 0.79), (0.08, 0.08, 0.08)),
):
    trial = body.copy()
    trial.data = body.data.copy()
    trial.name = f"trial_{label}"
    bpy.context.collection.objects.link(trial)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=location)
    operand = bpy.context.object
    operand.name = f"operand_{label}"
    operand.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.context.view_layer.objects.active = trial
    trial.select_set(True)
    modifier = trial.modifiers.new(f"union_{label}", "BOOLEAN")
    modifier.operation = "UNION"
    modifier.solver = "EXACT"
    modifier.object = operand
    while list(trial.modifiers).index(modifier) > 0:
        bpy.ops.object.modifier_move_up(modifier=modifier.name)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    check = bmesh.new()
    check.from_mesh(trial.data)
    print(
        label,
        len(check.verts),
        len(check.faces),
        sum(e.is_boundary for e in check.edges),
        sum(len(e.link_faces) > 2 for e in check.edges),
        check.calc_volume(signed=True),
    )
    check.free()
