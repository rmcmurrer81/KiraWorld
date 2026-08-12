"""Build V19 Stage-A static likeness from the V18/V15 identity lineage."""
from __future__ import annotations
import json
from pathlib import Path
import bmesh
import bpy

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v15_from_v14/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
OUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v19_from_v18"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14")
if body is None:
    raise SystemExit("V18/V15-lineage foundation missing")

# Small continuous second slimming pass; the face and head are untouched.
for vertex in body.data.vertices:
    co = vertex.co
    # Smoothly fade the change between shoulder and neck, avoiding horizontal
    # deformation seams caused by piecewise bands.
    fade = 1.0 - min(1.0, max(0.0, (co.z - 1.42) / 0.18))
    co.x *= 1.0 - 0.052 * fade
    co.y *= 1.0 - 0.058 * fade

# Refine only the existing connected surface. Graded weights preserve the
# pubic transition while raising the visible root and improving its side read.
group = body.vertex_groups.new(name="V19_LOCAL_ANATOMY_REPAIR")
indices = []
for vertex in body.data.vertices:
    co = vertex.co
    if abs(co.x) < 0.110 and co.y < -0.088 and 0.535 < co.z < 0.835:
        forward = min(1.0, max(0.0, (-co.y - 0.092) / 0.105))
        weight = forward
        # Translate the native connected form substantially as a unit. Earlier
        # z-dependent scaling distorted it into stacked lobes.
        co.z += 0.100 * weight
        co.y -= 0.003 * weight
        indices.append(vertex.index)
if indices:
    group.add(indices, 1.0, "REPLACE")
    smooth = body.modifiers.new("V19LocalAnatomySurfaceCleanup", "SMOOTH")
    smooth.vertex_group = group.name
    smooth.factor = 0.10
    smooth.iterations = 1
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    bpy.ops.object.modifier_apply(modifier=smooth.name)

# Owner-authoritative blonde removable review hair.
old_hair = bpy.data.materials.get("Robert_Natural_Medium_Brown_Hair")
if old_hair:
    hair_mat = old_hair.copy()
    hair_mat.name = "Robert_Removable_Dark_Blonde_Review_Hair"
    hair_mat.diffuse_color = (0.36, 0.21, 0.085, 1.0)
    hair_mat.use_nodes = True
    for node in hair_mat.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            if node.inputs.get("Base Color"):
                node.inputs["Base Color"].default_value = (0.36, 0.21, 0.075, 1.0)
            if node.inputs.get("Roughness"):
                node.inputs["Roughness"].default_value = 0.42
    for hair in (o for o in bpy.context.scene.objects if o.name in {"Object_6", "Object_7"}):
        hair.scale.x *= 1.10
        hair.scale.y *= 1.10
        hair.scale.z *= 1.05
        hair.location.y -= 0.014
        hair.location.z -= 0.010
        for slot in hair.material_slots:
            slot.material = hair_mat
        hair["hair_color_class"] = "dark_blonde"
        hair["removable_static_review_component"] = True
        hair["runtime_groom_complete"] = False

# Close primary-skin boundaries only.
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
    members, stack = {seed}, [seed]
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
boundaries = [e for e in bm.edges if e.is_boundary and all(v.index in largest for v in e.verts)]
if boundaries:
    bmesh.ops.holes_fill(bm, edges=boundaries, sides=0)
bm.to_mesh(mesh)
bm.free()
mesh.update()
for polygon in mesh.polygons:
    polygon.use_smooth = True

skin = bpy.data.materials.get("MBLab_skin3")
ao_nodes, skin_nodes = [], []
if skin and skin.use_nodes:
    for node in skin.node_tree.nodes:
        skin_nodes.append(node.name)
        if node.type == "AMBIENT_OCCLUSION" or "ambient occlusion" in node.name.lower():
            ao_nodes.append(node.name)
    # The inherited MB-Lab Eevee group produced broad gray bands from its
    # thickness/melanin interpretation. Rebuild the review skin with explicit,
    # independent albedo/roughness/SSS/normal inputs. The original albedo keeps
    # the mapped lips, nipples, and subtle regional color.
    albedo_node = skin.node_tree.nodes.get("Human_mblab_skn_albedo")
    albedo_image = albedo_node.image if albedo_node else None
    bump_node = skin.node_tree.nodes.get("Human_mblab_skn_bump")
    bump_image = bump_node.image if bump_node else None
    skin.node_tree.nodes.clear()
    output = skin.node_tree.nodes.new("ShaderNodeOutputMaterial")
    output.name = "V19_Skin_Output"
    principled = skin.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    principled.name = "V19_Separated_Skin_Shader"
    principled.inputs["Roughness"].default_value = 0.48
    if principled.inputs.get("Subsurface Weight"):
        principled.inputs["Subsurface Weight"].default_value = 0.075
    if principled.inputs.get("Subsurface Radius"):
        principled.inputs["Subsurface Radius"].default_value = (1.0, 0.42, 0.22)
    if albedo_image:
        albedo = skin.node_tree.nodes.new("ShaderNodeTexImage")
        albedo.name = "V19_Base_Albedo_Regional_Color"
        albedo.image = albedo_image
        blend = skin.node_tree.nodes.new("ShaderNodeMixRGB")
        blend.name = "V19_Subtle_Regional_Albedo_Blend"
        blend.blend_type = "MIX"
        blend.inputs[0].default_value = 0.30
        blend.inputs[1].default_value = (0.58, 0.30, 0.22, 1.0)
        skin.node_tree.links.new(albedo.outputs["Color"], blend.inputs[2])
        skin.node_tree.links.new(blend.outputs["Color"], principled.inputs["Base Color"])
    if bump_image:
        bump_tex = skin.node_tree.nodes.new("ShaderNodeTexImage")
        bump_tex.name = "V19_Normal_Detail_Source"
        bump_tex.image = bump_image
        bump = skin.node_tree.nodes.new("ShaderNodeBump")
        bump.name = "V19_Normal_Bump"
        bump.inputs["Strength"].default_value = 0.16
        bump.inputs["Distance"].default_value = 0.04
        skin.node_tree.links.new(bump_tex.outputs["Color"], bump.inputs["Height"])
        skin.node_tree.links.new(bump.outputs["Normal"], principled.inputs["Normal"])
    skin.node_tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])

body.name = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V19_FROM_V18"
body["status"] = "AWAITING ROBERT STATIC LIKENESS REVIEW"
body["preferred_likeness_lineage"] = "V1 -> V14 -> V15 -> V18 -> V19"
body["hair_color_class"] = "DARK_BLONDE"
body["slimming_pass"] = "SLIGHTLY THINNER THAN V18; FACE UNCHANGED"
body["anatomy_repair"] = "EXISTING CONNECTED SURFACE RAISED AND ROOT TRANSITION REFINED"
body["adult_topology_estimation"] = "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"
body["regional_skin_variation"] = "V1 ALBEDO/LIP MAP PRESERVED"
body["movement_claimed"] = False
body["runtime_activation_allowed"] = False
blend_path = OUT / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V19_FROM_V18.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
(OUT / "BUILD_REPORT.json").write_text(json.dumps({
    "schema_version": 1,
    "status": "AWAITING ROBERT STATIC LIKENESS REVIEW",
    "repair_base": "intact V15 identity foundation; V18 visual lessons reapplied without inherited deformation bands",
    "changes": [
        "hair material corrected to removable dark-blonde review class",
        "body modestly slimmed below neck",
        "existing connected anatomy surface raised and root transition refined",
        "V1 regional skin map retained",
    ],
    "skin_shader_ao_nodes": ao_nodes,
    "skin_shader_node_names": skin_nodes,
    "ao_baked_into_albedo_claim": False,
    "movement": "not started",
    "stage_b": "deferred until Robert accepts static likeness",
    "runtime_attachment": "not permitted",
}, indent=2) + "\n", encoding="utf-8")
print(blend_path)
