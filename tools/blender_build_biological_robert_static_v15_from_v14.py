"""Build the next protected Biological Robert static candidate from V14."""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v14_from_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V14_FROM_V1.blend"
HAIR_REFERENCE = ROOT / "Avatar/avatar_builder/asset_library/hair_reference/short_hair_cut_in_layers_with_bones_90fd798a2e.glb"
OUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v15_from_v14"
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V14_FROM_V1")
if body is None:
    raise SystemExit("V14 active repair foundation missing")

# One modest slimming pass below the neck. The V14 face/head is untouched.
# Different zones receive small local reductions so the result remains an
# ordinary adult body rather than becoming athletic or skinny.
for vertex in body.data.vertices:
    co = vertex.co
    if co.z >= 1.58:
        continue
    co.x *= 0.982
    co.y *= 0.975
    if 0.76 <= co.z <= 1.22:  # abdomen and waist
        co.x *= 0.978
        co.y *= 0.970
    elif 1.22 < co.z <= 1.53:  # chest
        co.x *= 0.988
        co.y *= 0.985
    if 0.40 <= co.z <= 0.92 and abs(co.x) > 0.08:  # thighs
        center = 0.18 if co.x > 0 else -0.18
        co.x = center + (co.x - center) * 0.965
        co.y *= 0.978
    if 1.00 <= co.z <= 1.48 and abs(co.x) > 0.24:  # upper arms
        center = 0.31 if co.x > 0 else -0.31
        co.x = center + (co.x - center) * 0.965
        co.y *= 0.978

# Refine the already-unioned neutral anatomy without detaching it: raise the
# protruding region, bring it slightly closer to the pelvis, and apply local
# smoothing through a vertex group. The body remains one mesh/object.
anatomy_group = body.vertex_groups.new(name="V15_LOCAL_ANATOMY_REFINEMENT")
anatomy_indices = []
for vertex in body.data.vertices:
    co = vertex.co
    if abs(co.x) < 0.09 and co.y < -0.115 and 0.61 < co.z < 0.80:
        weight = min(1.0, max(0.0, (-co.y - 0.115) / 0.07))
        co.z += 0.030 * weight
        co.y += 0.010 * weight
        co.x *= 0.94 + 0.06 * (1.0 - weight)
        anatomy_indices.append(vertex.index)
if anatomy_indices:
    anatomy_group.add(anatomy_indices, 1.0, "REPLACE")
    smooth = body.modifiers.new("V15LocalAnatomySurfaceCleanup", "SMOOTH")
    smooth.vertex_group = anatomy_group.name
    smooth.factor = 0.30
    smooth.iterations = 4
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    bpy.ops.object.modifier_apply(modifier=smooth.name)

# Build a removable layered curve groom for static review. It is intentionally
# not a painted texture, helmet, or baked part of the body.
hair_material = bpy.data.materials.new("Robert_Natural_Medium_Brown_Hair")
hair_material.use_nodes = True
bsdf = hair_material.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.028, 0.010, 0.004, 1.0)
bsdf.inputs["Roughness"].default_value = 0.72
hair_data = bpy.data.curves.new("Robert_Layered_Curve_Groom_Data", type="CURVE")
hair_data.dimensions = "3D"
hair_data.resolution_u = 3
hair_data.bevel_depth = 0.0028
hair_data.bevel_resolution = 3
hair_data.resolution_u = 3
hair = bpy.data.objects.new("Robert_Removable_Layered_Curve_Groom_V15", hair_data)
bpy.context.collection.objects.link(hair)
hair.data.materials.append(hair_material)

# Two interleaved layers of groom strands follow the scalp from a subtle
# left-side part. Individual splines remain editable for later restyling.
for layer in range(2):
    for strand_index in range(96):
        theta = -math.pi + (2 * math.pi * strand_index / 96.0) + layer * 0.018
        spline = hair_data.splines.new("NURBS")
        point_count = 7
        spline.points.add(point_count - 1)
        end_polar = 1.76 + 0.10 * math.sin(theta * 2.0) + layer * 0.035
        for point_index in range(point_count):
            t = point_index / (point_count - 1)
            polar = 0.11 + (end_polar - 0.11) * t
            # The part leans slightly left and the ends sweep backward.
            x = 0.106 * math.sin(polar) * math.cos(theta) - 0.018 * (1.0 - t)
            y = 0.096 * math.sin(polar) * math.sin(theta) + 0.006 + 0.010 * t
            z = 1.744 + 0.086 * math.cos(polar)
            wave = 0.0018 * math.sin(strand_index * 1.73 + point_index * 1.2)
            spline.points[point_index].co = (x + wave, y, z, 1.0)
        spline.order_u = 4
        spline.use_endpoint_u = True
# Side-swept frontal strands cover the crown-to-hairline transition while
# keeping the underlying groom editable rather than forming a rigid shell.
for strand_index in range(52):
    u = strand_index / 51.0
    end_x = -0.092 + 0.184 * u
    spline = hair_data.splines.new("NURBS")
    spline.points.add(6)
    for point_index in range(7):
        t = point_index / 6.0
        x = -0.025 * (1.0 - t) + end_x * t + 0.010 * math.sin(math.pi * t)
        y = -0.048 * (1.0 - t) - 0.165 * t
        z = 1.828 - 0.108 * (t ** 1.45) + 0.006 * math.sin(math.pi * t)
        spline.points[point_index].co = (x, y, z, 1.0)
    spline.order_u = 4
    spline.use_endpoint_u = True
hair["component_type"] = "REMOVABLE_REVIEW_HAIR"
hair["construction"] = "LAYERED_EDITABLE_CURVE_GROOM"
hair["runtime_approved"] = False
hair["runtime_hair_system_complete"] = False
hair["future_runtime_spec_required"] = True

# Use the locally approved layered short-hair reference (which includes bones)
# as the visible static groom. Preserve the editable procedural groom above as
# construction evidence, but do not render its unfinished first fit.
hair.hide_render = True
before_hair_import = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(HAIR_REFERENCE))
visible_hair_parts = [obj for obj in bpy.data.objects if obj not in before_hair_import]
hair_root = bpy.data.objects.new("Robert_Removable_Layered_Hair_Root_V15", None)
bpy.context.collection.objects.link(hair_root)
for obj in visible_hair_parts:
    if obj.type == "MESH":
        if obj.name == "Icosphere":
            obj.hide_render = True
            continue
        obj.parent = None
        for modifier in list(obj.modifiers):
            obj.modifiers.remove(modifier)
        obj.location = (0.0, -0.020, 1.660)
        obj.rotation_euler = (0.0, 0.0, 0.0)
        obj.scale = (0.740, 0.740, 0.740)
        obj.data.materials.clear()
        obj.data.materials.append(hair_material)
        obj["static_review_component"] = True
hair_root["component_type"] = "REMOVABLE_LAYERED_HAIR_WITH_BONES"
hair_root["runtime_approved"] = False
hair_root["runtime_hair_system_complete"] = False
hair_root["future_runtime_spec_required"] = True

body.name = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14"
body["status"] = "AWAITING ROBERT STATIC LIKENESS REVIEW"
body["active_repair_branch"] = "V14"
body["preferred_likeness_lineage"] = "V1 -> V14 -> V15"
body["v7_direction_rejected"] = True
body["slimming_pass"] = "MODEST BELOW NECK; NON-ATHLETIC"
body["anatomy_integration"] = "ONE CONNECTED BODY SURFACE; LOCALLY RAISED AND SMOOTHED"
body["regional_skin_variation"] = "PRESERVED_FROM_V1_TEXTURE"
body["hair_status"] = "REMOVABLE LAYERED CURVE GROOM — STATIC REVIEW ONLY"
body["glasses_status"] = "ABSENT"
body["rig_binding_status"] = "DEFERRED — STATIC LIKENESS REVIEW ONLY"
body["movement_claimed"] = False
body["runtime_activation_allowed"] = False

blend_path = OUT / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
(OUT / "BUILD_REPORT.json").write_text(json.dumps({
    "schema_version": 1,
    "status": "AWAITING ROBERT STATIC LIKENESS REVIEW",
    "active_repair_base": "V14",
    "lineage": ["V1", "V14", "V15"],
    "v7_direction": "REJECTED EVIDENCE ONLY",
    "changes": [
        "modest additional slimming below the neck",
        "abdomen, waist, chest, upper arms, and thighs reduced locally",
        "integrated anatomy raised, brought closer to pelvis, and locally smoothed",
        "removable natural medium-brown static-review hairstyle added",
        "V1-derived face and regional skin texture preserved",
    ],
    "glasses": "off",
    "movement": "not started",
    "runtime_attachment": "not permitted",
    "synthetic_robert": "not started",
    "kira": "not started",
    "clothing": "not started",
}, indent=2) + "\n", encoding="utf-8")
print(blend_path)
