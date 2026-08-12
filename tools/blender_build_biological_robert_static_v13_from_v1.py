"""Build a conservative V1-based static correction with seamless topology."""

from __future__ import annotations

import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
OUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v14_from_v1"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))

body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1")
anatomy = sorted(
    (obj for obj in bpy.context.scene.objects if "External_Anatomy_ESTIMATED" in obj.name),
    key=lambda obj: obj.name,
)
if body is None or len(anatomy) != 4:
    raise SystemExit("V1 body or its four conservative anatomy surfaces missing")

for obj in list(bpy.context.scene.objects):
    if "Separate_Brown_Iris" in obj.name or "Separate_Pupil" in obj.name:
        bpy.data.objects.remove(obj, do_unlink=True)

# Slightly thinner than V1 with a smooth neck transition; retain the V1 head.
for vertex in body.data.vertices:
    z = vertex.co.z
    factor = 1.0 if z >= 1.58 else (0.968 + (z - 1.42) / 0.16 * 0.032 if z >= 1.42 else 0.968)
    vertex.co.x *= factor
    vertex.co.y *= factor

# Owner correction: move the existing V1 anatomy slightly upward, inward, and
# closer to the pubic surface. Preserve a neutral resting adult form while
# avoiding the detached, low-hanging arrangement in V1.
for obj in anatomy[:2]:
    obj.location.x *= 0.72
    obj.location.y += 0.024
    obj.location.z += 0.052
    obj.scale.x *= 0.92
    obj.scale.y *= 0.92
    obj.scale.z *= 0.94
for obj in anatomy[2:]:
    obj.location.y += 0.030
    obj.location.z += 0.048
    obj.scale.x *= 0.94
    obj.scale.y *= 0.90
    obj.scale.z *= 0.93

skin = bpy.data.materials.get("MBLab_skin3")
if skin is None:
    raise SystemExit("V1 authored skin missing")

# Bake the accepted V1 surface, then exact-union each overlapping anatomy
# surface so the saved foundation has no separate or floating construction.
depsgraph = bpy.context.evaluated_depsgraph_get()
evaluated = body.evaluated_get(depsgraph)
baked_mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=depsgraph)
baked = bpy.data.objects.new("BIOLOGICAL_ROBERT_V1_BAKED_SURFACE", baked_mesh)
baked.matrix_world = body.matrix_world.copy()
bpy.context.collection.objects.link(baked)
bpy.data.objects.remove(body, do_unlink=True)
body = baked

# Join anatomy first so internal overlaps are resolved in one local operation.
bpy.ops.object.select_all(action="DESELECT")
for obj in anatomy:
    obj.select_set(True)
bpy.context.view_layer.objects.active = anatomy[0]
bpy.ops.object.join()
local = anatomy[0]
local.name = "LOCAL_ADULT_TOPOLOGY_CONSTRUCTION"
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
local.data.remesh_voxel_size = 0.0022
local.data.remesh_voxel_adaptivity = 0.0
bpy.ops.object.voxel_remesh()
if not local.data.materials:
    local.data.materials.append(skin)

bpy.context.view_layer.objects.active = body
body.select_set(True)
union = body.modifiers.new("SeamlessLocalAdultTopology", "BOOLEAN")
union.operation = "UNION"
union.solver = "EXACT"
union.object = local
while list(body.modifiers).index(union) > 0:
    bpy.ops.object.modifier_move_up(modifier=union.name)
bpy.ops.object.modifier_apply(modifier=union.name)
bpy.data.objects.remove(local, do_unlink=True)
for polygon in body.data.polygons:
    polygon.use_smooth = True

body.name = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V14_FROM_V1"
body["status"] = "AWAITING ROBERT STATIC LIKENESS REVIEW"
body["preferred_source"] = "V1"
body["v7_direction_rejected"] = True
body["slightly_thinner_than_v1"] = True
body["adult_topology_estimation"] = "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"
body["anatomy_integration"] = "ONE UNIONED SKIN SURFACE; NO SEPARATE ANATOMY OBJECT"
body["regional_skin_variation"] = "PRESERVED_FROM_V1_TEXTURE"
body["hair_status"] = "ABSENT"
body["glasses_status"] = "ABSENT"
body["rig_binding_status"] = "DEFERRED — STATIC LIKENESS REVIEW ONLY"
body["movement_claimed"] = False
body["runtime_activation_allowed"] = False
body.parent = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        obj.hide_render = True

blend_path = OUT / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V14_FROM_V1.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
(OUT / "BUILD_REPORT.json").write_text(json.dumps({
    "schema_version": 1,
    "status": "AWAITING ROBERT STATIC LIKENESS REVIEW",
    "preferred_base": "V1",
    "v7_direction": "REJECTED_BY_OWNER",
    "slightly_thinner_than_v1": True,
    "anatomy_integration": "single exact-unioned skin surface; moved upward/inward/closer than V1",
    "anatomy_estimation_label": "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE",
    "skin_variation": "preserved V1 authored texture",
    "hair": "absent",
    "glasses": "absent",
    "movement_claimed": False,
    "runtime_activation_allowed": False,
}, indent=2) + "\n", encoding="utf-8")
print(blend_path)
