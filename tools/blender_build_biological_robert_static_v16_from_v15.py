"""Build V16 directly from V15 with a reference-guided local anatomy repair."""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v15_from_v14/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
REFERENCE = ROOT / "Avatar/avatar_builder/asset_library/adult_anatomy_reference/male_nude_2_1_f117148577.glb"
OUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v16_from_v15"
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14")
if body is None:
    raise SystemExit("V15 active repair body missing")

# One further controlled slimming pass below the neck.
for vertex in body.data.vertices:
    co = vertex.co
    if co.z >= 1.58:
        continue
    if 0.76 <= co.z <= 1.22:
        co.x *= 0.982
        co.y *= 0.975
    elif 1.22 < co.z <= 1.53:
        co.x *= 0.990
        co.y *= 0.988
    if 0.40 <= co.z <= 0.92 and abs(co.x) > 0.08:
        center = 0.18 if co.x > 0 else -0.18
        co.x = center + (co.x - center) * 0.978
        co.y *= 0.985
    if 1.00 <= co.z <= 1.48 and abs(co.x) > 0.24:
        center = 0.31 if co.x > 0 else -0.31
        co.x = center + (co.x - center) * 0.980
        co.y *= 0.985

skin = bpy.data.materials.get("MBLab_skin3")
if skin is None:
    raise SystemExit("V1-derived coherent skin material missing")

# Remove only the failed protruding V15 local anatomy volume. The replacement
# patch below includes its own pubic/root transition and is unioned locally.
bpy.ops.mesh.primitive_cube_add(location=(0.0, -0.172, 0.705), scale=(0.105, 0.105, 0.115))
cutter = bpy.context.object
cutter.name = "V16_FAILED_LOCAL_ANATOMY_CUTTER"
bpy.context.view_layer.objects.active = body
body.select_set(True)
difference = body.modifiers.new("RemoveFailedV15LocalAnatomy", "BOOLEAN")
difference.operation = "DIFFERENCE"
difference.solver = "EXACT"
difference.object = cutter
bpy.ops.object.modifier_apply(modifier=difference.name)
bpy.data.objects.remove(cutter, do_unlink=True)

# Import the authorized adult reference temporarily. Transform only a narrow
# pubic/external-anatomy crop into Robert coordinates. No source face, torso,
# limbs, body proportions, skin, material, or identity surface is retained.
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(REFERENCE))
imported = [obj for obj in bpy.data.objects if obj not in before]
scale = 1.813 / 71.688
source_center_x = 1.690873
source_center_y = 0.435622
source_floor_z = -0.092019

vertices = []
faces = []
for source_obj in (obj for obj in imported if obj.type == "MESH"):
    transformed = []
    for vertex in source_obj.data.vertices:
        point = source_obj.matrix_world @ vertex.co
        transformed.append(Vector((
            -(point.x - source_center_x) * scale,
            -(point.y - source_center_y) * scale,
            (point.z - source_floor_z) * scale,
        )))
    for polygon in source_obj.data.polygons:
        points = [transformed[index] for index in polygon.vertices]
        center = sum(points, Vector()) / len(points)
        if (
            abs(center.x) <= 0.115
            and -0.225 <= center.y <= -0.055
            and 0.610 <= center.z <= 0.850
            and all(abs(point.x) <= 0.145 for point in points)
        ):
            base = len(vertices)
            vertices.extend(points)
            faces.append(tuple(base + index for index in range(len(points))))
for obj in imported:
    bpy.data.objects.remove(obj, do_unlink=True)
if len(faces) < 100:
    raise SystemExit(f"reference-guided local crop insufficient: {len(faces)} faces")

patch_mesh = bpy.data.meshes.new("V16_Reference_Guided_Local_Adult_Topology")
patch_mesh.from_pydata(vertices, [], faces)
patch_mesh.update()
patch = bpy.data.objects.new("V16_Reference_Guided_Local_Adult_Topology", patch_mesh)
bpy.context.collection.objects.link(patch)
patch.data.materials.append(skin)

# Consolidate the fragmented reference crop locally. This is intentionally
# limited to the small anatomy patch; Robert's V15 face/body is not remeshed.
bpy.context.view_layer.objects.active = patch
patch.select_set(True)
patch.data.remesh_voxel_size = 0.0018
patch.data.remesh_voxel_adaptivity = 0.0
bpy.ops.object.voxel_remesh()
for polygon in patch.data.polygons:
    polygon.use_smooth = True

bpy.context.view_layer.objects.active = body
body.select_set(True)
union = body.modifiers.new("V16ReferenceGuidedLocalUnion", "BOOLEAN")
union.operation = "UNION"
union.solver = "EXACT"
union.object = patch
bpy.ops.object.modifier_apply(modifier=union.name)
bpy.data.objects.remove(patch, do_unlink=True)
for polygon in body.data.polygons:
    polygon.use_smooth = True

body.name = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V16_FROM_V15"
body["status"] = "AWAITING ROBERT STATIC LIKENESS REVIEW"
body["active_repair_branch"] = "V15"
body["preferred_likeness_lineage"] = "V1 -> V14 -> V15 -> V16"
body["v7_direction_rejected"] = True
body["slimming_pass"] = "CONTROLLED ADDITIONAL REDUCTION BELOW NECK"
body["anatomy_method"] = "LOCAL REFERENCE-GUIDED CROP; SOURCE IDENTITY/BODY EXCLUDED"
body["adult_topology_estimation"] = "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"
body["regional_skin_variation"] = "PRESERVED_FROM_V1_TEXTURE"
body["hair_status"] = "REMOVABLE LAYERED STATIC-REVIEW COMPONENT; RUNTIME HAIR INCOMPLETE"
body["movement_claimed"] = False
body["runtime_activation_allowed"] = False

blend_path = OUT / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V16_FROM_V15.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
(OUT / "BUILD_REPORT.json").write_text(json.dumps({
    "schema_version": 1,
    "status": "AWAITING ROBERT STATIC LIKENESS REVIEW",
    "active_repair_base": "V15",
    "lineage": ["V1", "V14", "V15", "V16"],
    "v7_direction": "REJECTED EVIDENCE ONLY",
    "anatomy_repair": {
        "method": "narrow local crop from authorized adult reference, transformed and locally remeshed",
        "third_party_identity_surface_retained": False,
        "source_body_proportions_retained": False,
        "source_material_retained": False,
        "estimated": True,
    },
    "hair": "removable layered static-review component; runtime system incomplete",
    "movement": "not started",
    "runtime_attachment": "not permitted",
    "synthetic_robert": "not started",
    "kira": "not started",
    "clothing": "not started",
}, indent=2) + "\n", encoding="utf-8")
print(blend_path)
