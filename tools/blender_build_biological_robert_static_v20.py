"""Build V20 with a purpose-built local pelvis reconstruction.

Only a bounded pelvis/groin volume is reconstructed. Robert's V15 face and the
rest of his identity surface are not remeshed. The authorized adult reference
contributes local structure only.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v15_from_v14/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
REFERENCE = ROOT / "Avatar/avatar_builder/asset_library/adult_anatomy_reference/male_reproductive_system_f5c19ef767.glb"
OUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v20_local_pelvis_rebuild"
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14")
if body is None:
    raise SystemExit("intact V15 identity foundation missing")
skin = bpy.data.materials.get("MBLab_skin3")
if skin is None:
    raise SystemExit("V1/V15 skin material missing")

# Continuous modest slimming. The fade ends below the head and avoids the
# horizontal band boundaries seen in rejected evidence.
for vertex in body.data.vertices:
    co = vertex.co
    fade = 1.0 - min(1.0, max(0.0, (co.z - 1.42) / 0.18))
    co.x *= 1.0 - 0.050 * fade
    co.y *= 1.0 - 0.055 * fade

# Import the authorized coherent lower-torso/pelvis reference and fit only that
# local structural surface into Robert space.
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(REFERENCE))
imported = [obj for obj in bpy.data.objects if obj not in before]
reference_source = max(
    (o for o in imported if o.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
source_points = [reference_source.matrix_world @ vertex.co for vertex in reference_source.data.vertices]
mins = [min(point[i] for point in source_points) for i in range(3)]
maxs = [max(point[i] for point in source_points) for i in range(3)]
centers = [(mins[i] + maxs[i]) / 2 for i in range(3)]
scale = Vector((0.0260, 0.0210, 0.0160))
reference_vertices = [
    Vector((
        (point.x - centers[0]) * scale.x,
        (point.y - centers[1]) * scale.y - 0.085,
        (point.z - mins[2]) * scale.z + 0.47,
    ))
    for point in source_points
]
reference_faces = [tuple(polygon.vertices) for polygon in reference_source.data.polygons]
reference_face_count = len(reference_faces)
local_mesh = bpy.data.meshes.new("V20_Coherent_Pelvis_Reference_Structure")
local_mesh.from_pydata(reference_vertices, [], reference_faces)
local_mesh.update()
local = bpy.data.objects.new("V20_Local_Pelvis_Retopology", local_mesh)
bpy.context.collection.objects.link(local)
local.data.materials.append(skin)
bm = bmesh.new()
bm.from_mesh(local.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.00001)
boundary = [edge for edge in bm.edges if edge.is_boundary]
if boundary:
    bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(local.data)
bm.free()
local.data.update()

# Replace the outer reference's schematic external primitives with the model's
# dedicated reproductive-surface component, transformed by the exact same
# calibration so its pubic/root relationship is preserved.
secondary = min(
    (o for o in imported if o.type == "MESH" and len(o.data.vertices) > 10),
    key=lambda obj: len(obj.data.vertices),
)
secondary_points = [secondary.matrix_world @ vertex.co for vertex in secondary.data.vertices]
secondary_vertices = [
    Vector((
        (point.x - centers[0]) * scale.x,
        (point.y - centers[1]) * scale.y - 0.025,
        (point.z - mins[2]) * scale.z + 0.47,
    ))
    for point in secondary_points
]
secondary_mesh = bpy.data.meshes.new("V20_Dedicated_External_Structure")
secondary_mesh.from_pydata(
    secondary_vertices,
    [],
    [tuple(polygon.vertices) for polygon in secondary.data.polygons],
)
secondary_mesh.update()
secondary_local = bpy.data.objects.new("V20_Dedicated_External_Structure", secondary_mesh)
bpy.context.collection.objects.link(secondary_local)
secondary_local.data.materials.append(skin)

dedicated_union = local.modifiers.new("V20DedicatedExternalUnion", "BOOLEAN")
dedicated_union.operation = "UNION"
dedicated_union.solver = "EXACT"
dedicated_union.object = secondary_local
bpy.ops.object.modifier_apply(modifier=dedicated_union.name)
bpy.data.objects.remove(secondary_local, do_unlink=True)

# Convert the reference's near-horizontal presentation into a neutral resting
# form. Rotate only the forward external surface around its high pubic root;
# the pelvis, lower abdomen, thighs, and perineal boundary remain fixed.
pivot = Vector((0.0, -0.145, 0.735))
angle = math.radians(38.0)
cosine, sine = math.cos(angle), math.sin(angle)
for vertex in local.data.vertices:
    co = vertex.co
    if abs(co.x) <= 0.095 and co.y < -0.165 and 0.57 <= co.z <= 0.81:
        delta = co - pivot
        weight = min(1.0, max(0.0, (-co.y - 0.165) / 0.10))
        rotated_y = (delta.y * cosine - delta.z * sine) * 0.72
        rotated_z = (delta.y * sine + delta.z * cosine) * 0.72
        co.y = pivot.y + delta.y * (1.0 - weight) + rotated_y * weight
        co.z = pivot.z + delta.z * (1.0 - weight) + rotated_z * weight

for obj in imported:
    bpy.data.objects.remove(obj, do_unlink=True)

print("V20_COHERENT_LOCAL_REFERENCE", len(local.data.vertices), len(local.data.polygons))
for polygon in local.data.polygons:
    polygon.use_smooth = True

# Keep the intact Robert surface and union the reconstructed volume into it.
# The earlier subtract-and-replace experiment produced visible waist and knee
# discontinuities because the structural reference did not match Robert at
# those remote boundaries.  V20 must change only the local outward surface.
bpy.context.view_layer.objects.active = body
body.select_set(True)
union = body.modifiers.new("V20UnionLocalPelvisRetopology", "BOOLEAN")
union.operation = "UNION"
union.solver = "EXACT"
union.object = local
bpy.ops.object.modifier_apply(modifier=union.name)
bpy.data.objects.remove(local, do_unlink=True)
for polygon in body.data.polygons:
    polygon.use_smooth = True
    center = polygon.center
    # Boolean-created faces otherwise inherit slot zero (eyelash), producing a
    # lace-like texture. The rebuilt pelvis belongs to the continuous skin
    # material, which is slot one on the V15 body.
    if abs(center.x) <= 0.36 and -0.32 <= center.y <= 0.24 and 0.43 <= center.z <= 1.03:
        polygon.material_index = 1

# Removable dark-blonde review hair; static-only.
old_hair = bpy.data.materials.get("Robert_Natural_Medium_Brown_Hair")
if old_hair:
    hair_mat = old_hair.copy()
    hair_mat.name = "Robert_Removable_Dark_Blonde_Review_Hair_V20"
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
        hair["runtime_groom_complete"] = False

# One continuous review skin. Local retopology has new UVs, so applying the old
# UV atlas to it creates a false "painted shorts" boundary. V20 therefore uses
# an object-space procedural albedo with subtle variation and separately
# controlled roughness/SSS/bump. No AO or cavity input is used as color.
if skin.use_nodes:
    bump_node = skin.node_tree.nodes.get("Human_mblab_skn_bump")
    bump_image = bump_node.image if bump_node else None
    skin.node_tree.nodes.clear()
    output = skin.node_tree.nodes.new("ShaderNodeOutputMaterial")
    output.name = "V20_Skin_Output"
    principled = skin.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    principled.name = "V20_Continuous_Skin_Shader"
    principled.inputs["Roughness"].default_value = 0.48
    if principled.inputs.get("Subsurface Weight"):
        principled.inputs["Subsurface Weight"].default_value = 0.075
    texcoord = skin.node_tree.nodes.new("ShaderNodeTexCoord")
    texcoord.name = "V20_Object_Coordinates"
    noise = skin.node_tree.nodes.new("ShaderNodeTexNoise")
    noise.name = "V20_Subtle_Skin_Variation"
    noise.inputs["Scale"].default_value = 4.0
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Roughness"].default_value = 0.48
    ramp = skin.node_tree.nodes.new("ShaderNodeValToRGB")
    ramp.name = "V20_Skin_Albedo_Range"
    ramp.color_ramp.elements[0].color = (0.49, 0.235, 0.17, 1.0)
    ramp.color_ramp.elements[1].color = (0.62, 0.34, 0.25, 1.0)
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[1].position = 0.75
    skin.node_tree.links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
    skin.node_tree.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    skin.node_tree.links.new(ramp.outputs["Color"], principled.inputs["Base Color"])
    bump = skin.node_tree.nodes.new("ShaderNodeBump")
    bump.name = "V20_Procedural_Micro_Bump"
    bump.inputs["Strength"].default_value = 0.055
    bump.inputs["Distance"].default_value = 0.018
    skin.node_tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    skin.node_tree.links.new(bump.outputs["Normal"], principled.inputs["Normal"])
    skin.node_tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])

body.name = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V20_LOCAL_PELVIS_REBUILD"
body["status"] = "V20 ENGINEERING CANDIDATE — REQUIRES RENDERED VISUAL GATE"
body["preferred_likeness_lineage"] = "V1 -> V14 -> V15 -> V20"
body["local_retopology_method"] = "BOUNDED ROBERT TRANSITION + AUTHORIZED STRUCTURAL CROP"
body["adult_topology_estimation"] = "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"
body["movement_claimed"] = False
body["runtime_activation_allowed"] = False
blend_path = OUT / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V20_LOCAL_PELVIS_REBUILD.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
(OUT / "BUILD_REPORT.json").write_text(json.dumps({
    "schema_version": 1,
    "status": "V20 ENGINEERING CANDIDATE — REQUIRES RENDERED VISUAL GATE",
    "base": "intact V15 identity foundation",
    "reference_faces_used_for_local_structure": reference_face_count,
    "whole_body_remeshed": False,
    "face_remeshed": False,
    "local_reconstruction_volume": {
        "x": [-0.31, 0.31], "y": [-0.27, 0.19], "z": [0.48, 0.98]
    },
    "stage_b": "deferred",
    "runtime_attachment": "prohibited",
}, indent=2) + "\n", encoding="utf-8")
print(blend_path)
