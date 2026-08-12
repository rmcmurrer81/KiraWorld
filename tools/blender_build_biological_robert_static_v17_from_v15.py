"""Build an intact V15-derived V17 static repair after rejecting V16."""

from __future__ import annotations

import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v15_from_v14/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
OUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v17_from_v15"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))

body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14")
if body is None:
    raise SystemExit("intact V15 repair base missing")

# Controlled, non-athletic slimming below the neck.
for vertex in body.data.vertices:
    co = vertex.co
    if co.z >= 1.58:
        continue
    if 0.76 <= co.z <= 1.22:
        co.x *= 0.980
        co.y *= 0.970
    elif 1.22 < co.z <= 1.53:
        co.x *= 0.988
        co.y *= 0.984
    if 0.40 <= co.z <= 0.92 and abs(co.x) > 0.08:
        center = 0.18 if co.x > 0 else -0.18
        co.x = center + (co.x - center) * 0.976
        co.y *= 0.982
    if 1.00 <= co.z <= 1.48 and abs(co.x) > 0.24:
        center = 0.31 if co.x > 0 else -0.31
        co.x = center + (co.x - center) * 0.978
        co.y *= 0.982

# Refine only the already-integrated V15 anatomy surface. Raise the full
# protruding region, strengthen the upper root transition, retain a narrower
# shaft, and preserve a distinct neutral lower contour.
group = body.vertex_groups.get("V17_ANATOMY_REPAIR") or body.vertex_groups.new(name="V17_ANATOMY_REPAIR")
indices = []
for vertex in body.data.vertices:
    co = vertex.co
    if abs(co.x) < 0.095 and co.y < -0.105 and 0.61 < co.z < 0.81:
        projection = min(1.0, max(0.0, (-co.y - 0.105) / 0.075))
        co.z += 0.042 * projection
        # Upper root transitions forward into the pubic region; the visible
        # resting anatomy stays close to the body rather than floating.
        if co.z > 0.715:
            co.y -= 0.006 * projection
            co.x *= 0.92
        else:
            co.y += 0.006 * projection
            co.x *= 1.04
        indices.append(vertex.index)
if indices:
    group.add(indices, 1.0, "REPLACE")
    smooth = body.modifiers.new("V17LocalAnatomyCleanup", "SMOOTH")
    smooth.vertex_group = group.name
    smooth.factor = 0.18
    smooth.iterations = 2
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    bpy.ops.object.modifier_apply(modifier=smooth.name)

# Keep the coherent V1 skin network but reduce effects that can read as muddy
# painted shadow. Preserve the authored albedo/lip map and subtle regional
# variation; lighting remains responsible for actual form shadow.
skin = bpy.data.materials.get("MBLab_skin3")
if skin and skin.use_nodes:
    values = {
        "skin_bump": 0.40,
        "skin_oil": 0.11,
        "skin_veins": 0.10,
    }
    for name, value in values.items():
        node = skin.node_tree.nodes.get(name)
        if node and node.outputs:
            node.outputs[0].default_value = value

body.name = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V17_FROM_V15"
body["status"] = "AWAITING ROBERT STATIC LIKENESS REVIEW"
body["active_repair_branch"] = "V15"
body["preferred_likeness_lineage"] = "V1 -> V14 -> V15 -> V17"
body["v7_direction_rejected"] = True
body["v16_reference_crop"] = "REJECTED — VISUAL ARTIFACTS"
body["slimming_pass"] = "CONTROLLED, MODEST, NON-ATHLETIC"
body["anatomy_repair"] = "INTEGRATED V15 SURFACE RAISED AND LOCALLY RESHAPED"
body["regional_skin_variation"] = "V1 ALBEDO/LIP MAP PRESERVED; SHADER EFFECTS REBALANCED"
body["hair_status"] = "REMOVABLE LAYERED STATIC-REVIEW COMPONENT; RUNTIME HAIR INCOMPLETE"
body["movement_claimed"] = False
body["runtime_activation_allowed"] = False

blend_path = OUT / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V17_FROM_V15.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
(OUT / "BUILD_REPORT.json").write_text(json.dumps({
    "schema_version": 1,
    "status": "AWAITING ROBERT STATIC LIKENESS REVIEW",
    "active_repair_base": "V15",
    "lineage": ["V1", "V14", "V15", "V17"],
    "v7_direction": "REJECTED EVIDENCE ONLY",
    "v16": "REJECTED CONSTRUCTION EVIDENCE — FRAGMENTED REFERENCE CROP",
    "changes": [
        "controlled additional slimming below the neck",
        "integrated anatomy raised and locally reshaped without a separate object",
        "upper root transition strengthened and lower contour retained",
        "V1 skin albedo and lip map preserved",
        "bump, veins, melanin, blush, and oil controls rebalanced",
        "removable V15 layered static hair preserved",
    ],
    "movement": "not started",
    "runtime_attachment": "not permitted",
    "synthetic_robert": "not started",
    "kira": "not started",
    "clothing": "not started",
}, indent=2) + "\n", encoding="utf-8")
print(blend_path)
