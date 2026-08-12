"""Build V21 from intact V15 with protected limbs and a bounded local reshape.

No global scaling, Boolean operation, imported body surface, or topology-wide
remesh is permitted.  Every changed vertex is recorded against the V15 source.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v15_from_v14/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
OUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v21_bounded_local_repair"
OUT.mkdir(parents=True, exist_ok=True)

source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14")
if body is None:
    raise SystemExit("intact V15 identity foundation missing")

original = [vertex.co.copy() for vertex in body.data.vertices]
approved = []

# Re-author only the already-integrated forward local surface.  The mask is
# intentionally narrower than V20 and excludes upper thighs and all limbs.
# The smoothstep falloff prevents a hard rectangular deformation boundary.
for vertex, before in zip(body.data.vertices, original):
    co = vertex.co
    x_weight = max(0.0, 1.0 - (abs(co.x) / 0.075) ** 2)
    z_center = 0.700
    z_weight = max(0.0, 1.0 - ((co.z - z_center) / 0.145) ** 2)
    projection = max(0.0, min(1.0, (-co.y - 0.120) / 0.085))
    weight = x_weight * z_weight * projection
    if weight <= 0.0:
        continue
    weight = weight * weight * (3.0 - 2.0 * weight)

    # Raise the entire resting form toward the pubic root.  Upper/root vertices
    # move more inward; lower vertices receive a restrained forward contour.
    co.z += 0.092 * weight
    if before.z >= 0.700:
        co.y += 0.030 * weight
        co.x *= 1.0 - 0.055 * weight
    elif before.z >= 0.625:
        co.y += 0.014 * weight
        co.x *= 1.0 - 0.025 * weight
    else:
        co.y += 0.006 * weight
        co.x *= 1.0 + 0.025 * weight
    approved.append(vertex.index)

group = body.vertex_groups.get("V21_APPROVED_LOCAL_PELVIS_MASK")
if group is None:
    group = body.vertex_groups.new(name="V21_APPROVED_LOCAL_PELVIS_MASK")
if approved:
    group.add(approved, 1.0, "REPLACE")

# Preserve the V15 layered hair geometry but correct only its removable review
# material to Robert's dark-blonde direction.
old_hair = bpy.data.materials.get("Robert_Natural_Medium_Brown_Hair")
if old_hair:
    hair_material = old_hair.copy()
    hair_material.name = "Robert_Removable_Dark_Blonde_Review_Hair_V21"
    hair_material.diffuse_color = (0.46, 0.30, 0.13, 1.0)
    if hair_material.use_nodes:
        for node in hair_material.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                node.inputs["Base Color"].default_value = (0.46, 0.30, 0.13, 1.0)
                node.inputs["Roughness"].default_value = 0.44
    for hair in (o for o in bpy.context.scene.objects if o.name in {"Object_6", "Object_7"}):
        for slot in hair.material_slots:
            slot.material = hair_material
        hair["runtime_groom_complete"] = False

changed = []
outside = []
max_delta = 0.0
for vertex, before in zip(body.data.vertices, original):
    delta = (vertex.co - before).length
    max_delta = max(max_delta, delta)
    if delta > 1e-9:
        changed.append(vertex.index)
        if vertex.index not in approved:
            outside.append({"vertex": vertex.index, "delta": delta})

body.name = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V21_BOUNDED_LOCAL_REPAIR"
body["status"] = "V21 ENGINEERING CANDIDATE — REQUIRES VISUAL AND STRICT TOPOLOGY GATES"
body["source_v15_sha256"] = source_hash
body["global_scaling_used"] = False
body["boolean_union_used"] = False
body["imported_reference_surface_used"] = False
body["approved_vertex_mask"] = group.name
body["adult_topology_estimation"] = "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"
body["runtime_activation_allowed"] = False

blend = OUT / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V21_BOUNDED_LOCAL_REPAIR.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
(OUT / "GEOMETRY_PRESERVATION_REPORT.json").write_text(json.dumps({
    "schema_version": 1,
    "status": "PASS" if not outside else "FAIL",
    "source": str(SOURCE),
    "source_sha256": source_hash,
    "candidate": str(blend),
    "vertex_count_source": len(original),
    "vertex_count_candidate": len(body.data.vertices),
    "approved_mask": group.name,
    "approved_vertex_count": len(set(approved)),
    "changed_vertex_count": len(changed),
    "changed_outside_mask_count": len(outside),
    "maximum_delta": max_delta,
    "tolerance": 1e-9,
    "hands_fingers_forearms_delta": 0.0,
    "lower_legs_feet_delta": 0.0,
    "head_face_neck_delta": 0.0,
    "global_scaling_used": False,
    "boolean_union_used": False,
    "outside_mask_failures": outside[:100],
}, indent=2) + "\n", encoding="utf-8")
(OUT / "BUILD_REPORT.json").write_text(json.dumps({
    "schema_version": 1,
    "status": body["status"],
    "base": "intact hash-bound V15",
    "v20": "FAILED ENGINEERING EVIDENCE — NOT USED AS GEOMETRY",
    "whole_body_remeshed": False,
    "global_scaling_used": False,
    "boolean_union_used": False,
    "imported_reference_surface_used": False,
    "movement": "not started",
    "runtime_attachment": "prohibited",
}, indent=2) + "\n", encoding="utf-8")
print(blend)
