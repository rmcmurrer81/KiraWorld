"""Build V18 static likeness from the intact V15 identity foundation."""

from __future__ import annotations

import json
from pathlib import Path

import bmesh
import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v15_from_v14/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
OUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v18_from_v15"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))

body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14")
if body is None:
    raise SystemExit("intact V15 identity foundation missing")

# Slightly slimmer than V17's target without becoming athletic or generic.
for vertex in body.data.vertices:
    co = vertex.co
    if co.z >= 1.58:
        continue
    if 0.76 <= co.z <= 1.22:
        co.x *= 0.972
        co.y *= 0.962
    elif 1.22 < co.z <= 1.53:
        co.x *= 0.982
        co.y *= 0.978
    if 0.40 <= co.z <= 0.92 and abs(co.x) > 0.08:
        center = 0.18 if co.x > 0 else -0.18
        co.x = center + (co.x - center) * 0.968
        co.y *= 0.976
    if 1.00 <= co.z <= 1.48 and abs(co.x) > 0.24:
        center = 0.31 if co.x > 0 else -0.31
        co.x = center + (co.x - center) * 0.970
        co.y *= 0.976

# Higher, closer, and more differentiated local anatomy reshape on the
# existing integrated skin. This does not introduce another body/identity.
repair_group = body.vertex_groups.new(name="V18_LOCAL_ANATOMY_REPAIR")
repair_indices = []
for vertex in body.data.vertices:
    co = vertex.co
    if abs(co.x) < 0.100 and co.y < -0.100 and 0.60 < co.z < 0.82:
        projection = min(1.0, max(0.0, (-co.y - 0.100) / 0.082))
        co.z += 0.058 * projection
        raised_z = co.z
        if raised_z >= 0.735:  # pubic/root transition
            co.y -= 0.010 * projection
            co.x *= 0.96
        elif raised_z >= 0.690:  # neutral shaft
            co.y -= 0.004 * projection
            co.x *= 0.90
        else:  # lower scrotal contour
            co.y += 0.007 * projection
            co.x *= 1.08
        repair_indices.append(vertex.index)
if repair_indices:
    repair_group.add(repair_indices, 1.0, "REPLACE")
    smooth = body.modifiers.new("V18LocalAnatomySurfaceCleanup", "SMOOTH")
    smooth.vertex_group = repair_group.name
    smooth.factor = 0.22
    smooth.iterations = 3
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    bpy.ops.object.modifier_apply(modifier=smooth.name)

# Fit the removable layered V15 hair fuller, lower, and farther forward so the
# crown, temple, and side silhouettes do not read as bald. It remains a static
# review component rather than a claimed runtime groom.
for hair in (obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.name in {"Object_6", "Object_7"}):
    hair.scale.x *= 1.10
    hair.scale.y *= 1.10
    hair.scale.z *= 1.05
    hair.location.y -= 0.014
    hair.location.z -= 0.010
    hair["v18_static_review_fit"] = "FULLER_CROWN_TEMPLE_SIDE"
    hair["runtime_hair_system_complete"] = False

# Close boundary loops belonging only to the largest connected component.
# Eyes, teeth, nails, and removable hair remain separate normal components.
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
bm.edges.ensure_lookup_table()
main_boundaries = [
    edge for edge in bm.edges
    if edge.is_boundary
    and edge.verts[0].index in largest
    and edge.verts[1].index in largest
]
filled_boundary_edge_count = len(main_boundaries)
if main_boundaries:
    bmesh.ops.holes_fill(bm, edges=main_boundaries, sides=0)
bm.to_mesh(mesh)
bm.free()
mesh.update()
for polygon in mesh.polygons:
    polygon.use_smooth = True

# Preserve V1 maps and separate color from shading by retaining the coherent
# skin network; actual underside form shadows are handled by review lights.
skin = bpy.data.materials.get("MBLab_skin3")
if skin and skin.use_nodes:
    for name, value in {"skin_bump": 0.42, "skin_oil": 0.11, "skin_veins": 0.10}.items():
        node = skin.node_tree.nodes.get(name)
        if node and node.outputs:
            node.outputs[0].default_value = value

body.name = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V18_FROM_V15"
body["status"] = "AWAITING ROBERT STATIC LIKENESS REVIEW"
body["preferred_likeness_lineage"] = "V1 -> V14 -> V15 -> V18"
body["v7_direction_rejected"] = True
body["v17_approval_direction"] = "REJECTED — LOW ANATOMY AND THIN HAIR SILHOUETTE"
body["slimming_pass"] = "MODESTLY THINNER THAN V17 TARGET; NON-ATHLETIC"
body["anatomy_repair"] = "V15 INTEGRATED SURFACE RAISED AND LOCALLY DIFFERENTIATED"
body["main_component_boundary_edges_targeted"] = filled_boundary_edge_count
body["regional_skin_variation"] = "V1 ALBEDO/LIP MAP PRESERVED"
body["hair_status"] = "REMOVABLE FULLER LAYERED STATIC-REVIEW COMPONENT"
body["movement_claimed"] = False
body["runtime_activation_allowed"] = False

blend_path = OUT / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V18_FROM_V15.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
(OUT / "BUILD_REPORT.json").write_text(json.dumps({
    "schema_version": 1,
    "status": "AWAITING ROBERT STATIC LIKENESS REVIEW",
    "repair_base": "V15",
    "lineage": ["V1", "V14", "V15", "V18"],
    "v17_approval_direction": "REJECTED",
    "main_component_boundary_edges_targeted_for_fill": filled_boundary_edge_count,
    "changes": [
        "modestly slimmer body below neck",
        "integrated anatomy raised and locally differentiated",
        "fuller lower forward removable static hair fit",
        "largest-component boundary loops targeted for closure",
        "V1 skin maps preserved",
    ],
    "movement": "not started",
    "runtime_attachment": "not permitted",
    "activation": "not permitted",
    "synthetic_robert": "not started",
    "kira": "not started",
    "clothing": "not started",
}, indent=2) + "\n", encoding="utf-8")
print(blend_path)
