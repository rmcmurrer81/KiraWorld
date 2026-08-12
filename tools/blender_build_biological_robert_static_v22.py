"""V22 protected baseline experiment: correct the cavity at its geometric cause.

This branch starts from intact V15, not V21 geometry.  It preserves protected
regions, raises the integrated local form as a connected surface, replaces the
failed inherited pelvic albedo boundary, and improves removable review hair.
It remains blocked unless visual and topology gates pass.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v15_from_v14/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
OUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v22_protected_bridge_rebuild"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14")
if body is None:
    raise SystemExit("V15 body missing")
before = [v.co.copy() for v in body.data.vertices]

# The V21 probe proved that the visible teardrop is not an open boundary:
# there are zero boundary edges in the photographed local volume.  It is a
# deep exposed concavity caused by the low integrated form.  Raise only the
# forward midline surface, with a smooth local falloff and no global scaling.
# Material slot 1 contains exactly two face-connected regions in V15: the
# broad pelvic patch and the narrow failed external-anatomy component. Isolate
# the latter by face connectivity rather than a rectangular coordinate mask.
material_faces = [p for p in body.data.polygons if p.material_index == 1]
vertex_faces = {}
for face in material_faces:
    for index in face.vertices:
        vertex_faces.setdefault(index, set()).add(face.index)
face_map = {face.index: face for face in material_faces}
remaining = set(face_map)
components = []
while remaining:
    seed = remaining.pop()
    stack = [seed]
    member_faces = {seed}
    while stack:
        current = stack.pop()
        for vertex_index in face_map[current].vertices:
            for adjacent in vertex_faces.get(vertex_index, ()):
                if adjacent in remaining:
                    remaining.remove(adjacent)
                    member_faces.add(adjacent)
                    stack.append(adjacent)
    component_vertices = {
        vertex_index
        for face_index in member_faces
        for vertex_index in face_map[face_index].vertices
    }
    components.append((member_faces, component_vertices))
pelvis_anatomy_component = max(components, key=lambda item: len(item[1]))
changed = sorted(pelvis_anatomy_component[1])
for index in changed:
    co = body.data.vertices[index].co
    original_z = co.z
    co.z += .048
    co.y -= .008
    if original_z > .755:
        co.x *= .96
    elif original_z < .715:
        co.x *= 1.04

mask = body.vertex_groups.new(name="V22_LOCAL_GEOMETRY_CAUSE_REPAIR")
if changed:
    mask.add(changed, 1.0, "REPLACE")

# The inherited union assigned several pelvic faces to non-skin slots. This is
# the source of the pale/dark band even when the skin shader itself is valid.
# Reassign only the bounded lower-abdomen/groin/thigh-transition polygons to
# the same MBLab skin slot used by adjacent valid skin.
for polygon in body.data.polygons:
    if polygon.material_index in {1, 6}:
        polygon.material_index = 1

# Replace the inherited UV/albedo that paints a dark pelvic band.  One
# object-space skin shader is used across the complete skin; AO/cavity do not
# feed base color.
# Rebuild one shadow-free review skin for all exterior skin polygons.  The V15
# Boolean history split exterior skin between slots 1 and 6; both now use slot
# 1. AO/cavity are deliberately absent from base color.
skin = bpy.data.materials.get("MBLab_skin3")
if skin and skin.use_nodes:
    nodes = skin.node_tree.nodes
    links = skin.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = .47
    if bsdf.inputs.get("Subsurface Weight"):
        bsdf.inputs["Subsurface Weight"].default_value = .07
    coord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 4.0
    noise.inputs["Detail"].default_value = 2.0
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (.48, .24, .18, 1)
    ramp.color_ramp.elements[1].color = (.61, .34, .26, 1)
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = .04
    bump.inputs["Distance"].default_value = .01
    links.new(coord.outputs["Generated"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

# Fuller removable static-review hair. This changes hair only, never the head.
old_hair = bpy.data.materials.get("Robert_Natural_Medium_Brown_Hair")
if old_hair:
    hair_mat = old_hair.copy()
    hair_mat.name = "Robert_V22_Removable_Dark_Blonde_Static_Hair"
    hair_mat.diffuse_color = (.43, .29, .13, 1)
    if hair_mat.use_nodes:
        for node in hair_mat.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                node.inputs["Base Color"].default_value = (.43, .29, .13, 1)
                node.inputs["Roughness"].default_value = .44
    for hair in (o for o in bpy.context.scene.objects if o.name in {"Object_6", "Object_7"}):
        hair.scale.x *= 1.16
        hair.scale.y *= 1.18
        hair.scale.z *= 1.10
        hair.location.y -= .020
        hair.location.z -= .012
        for slot in hair.material_slots:
            slot.material = hair_mat
        hair["runtime_groom_complete"] = False

outside = []
for vertex, original in zip(body.data.vertices, before):
    delta = (vertex.co - original).length
    if delta > 1e-9 and vertex.index not in changed:
        outside.append(vertex.index)

body.name = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V22_PROTECTED_BRIDGE_REBUILD"
body["status"] = "BLOCKED — LOCAL BRIDGE TOPOLOGY INCOMPLETE"
body["source_v15_sha256"] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
body["visible_hole_diagnosis"] = "CLOSED CONCAVITY/LOW PLACEMENT; ZERO LOCAL BOUNDARY EDGES"
body["global_scaling_used"] = False
body["boolean_union_used"] = False
body["runtime_activation_allowed"] = False
blend = OUT / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V22_PROTECTED_BRIDGE_REBUILD.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
(OUT / "BUILD_REPORT.json").write_text(json.dumps({
    "schema_version": 1,
    "status": body["status"],
    "base": "intact V15",
    "v21_use": "engineering rules only; no V21 geometry",
    "hole_diagnosis": body["visible_hole_diagnosis"],
    "changed_vertex_count": len(set(changed)),
    "outside_mask_change_count": len(outside),
    "global_scaling_used": False,
    "boolean_union_used": False,
    "reference_body_surface_used": False,
    "clinical_structure_authorities": [
        "NCBI Bookshelf NBK482236",
        "NCBI Bookshelf NBK549893",
        "PMC4440541"
    ],
}, indent=2) + "\n", encoding="utf-8")
print(blend)
