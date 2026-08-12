"""Build the owner-directed V8 static foundation from the preferred V1."""

from __future__ import annotations

import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
OUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v11_from_v1"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))

body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1")
rig = next((obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"), None)
if body is None or rig is None:
    raise SystemExit("preferred V1 body or rig missing")

# Remove V1's experimental attached anatomy and review-only iris overlays.
for obj in list(bpy.context.scene.objects):
    if obj == body or obj == rig:
        continue
    if any(token in obj.name for token in (
        "External_Anatomy", "Separate_Brown_Iris", "Separate_Pupil",
    )):
        bpy.data.objects.remove(obj, do_unlink=True)

# Slightly thinner than V1 while retaining V1's head/face.  Scale only the
# torso and limbs, with a smooth transition below the neck.
for vertex in body.data.vertices:
    z = vertex.co.z
    if z >= 1.58:
        factor = 1.0
    elif z >= 1.42:
        factor = 0.965 + (z - 1.42) / 0.16 * 0.035
    else:
        factor = 0.965
    vertex.co.x *= factor
    vertex.co.y *= factor

skin = bpy.data.materials.get("MBLab_skin3")
if skin is None:
    raise SystemExit("V1 continuous skin material missing")

# Regional color variation is subtle and nonuniform. Existing diffuse texture
# detail remains the primary skin authority; these small authored regions
# prevent a flat single-tone result.
def region_material(name, color, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


# V1's texture already contains natural lip, nipple, nail and regional skin
# variation.  The rejected V9 polygon masks were visibly patch-like, so retain
# the continuous authored texture rather than painting geometric rectangles.
body["regional_skin_variation"] = "PRESERVED_FROM_V1_TEXTURE"

# Bake the evaluated V1 surface into a clean mesh before local topology work.
# Applying V1's stacked modifiers in-place corrupted the rejected V8 build.
depsgraph = bpy.context.evaluated_depsgraph_get()
evaluated = body.evaluated_get(depsgraph)
baked_mesh = bpy.data.meshes.new_from_object(
    evaluated, preserve_all_data_layers=True, depsgraph=depsgraph
)
baked = bpy.data.objects.new("BIOLOGICAL_ROBERT_V1_BAKED_SURFACE", baked_mesh)
baked.matrix_world = body.matrix_world.copy()
bpy.context.collection.objects.link(baked)
bpy.data.objects.remove(body, do_unlink=True)
body = baked

# Build one neutral estimated adult-anatomy construction volume.  It overlaps
# deeply with the V1 pubic surface, is remeshed by itself, then exact-unioned
# locally so V1's face and body detail are not globally remeshed.
parts = []
for location, scale, radius in (
    ((0, -0.070, 0.700), (1.30, 1.00, 1.00), 0.040),  # buried pubic root
    ((0, -0.155, 0.635), (1.18, 0.88, 1.10), 0.035),  # neutral scrotum
    ((0, -0.198, 0.620), (0.80, 0.86, 1.70), 0.022),  # resting shaft
    ((0, -0.200, 0.580), (0.86, 0.88, 0.70), 0.022),  # subtle glans
):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=48, ring_count=28, radius=radius, location=location, scale=scale
    )
    part = bpy.context.object
    part.data.materials.append(skin)
    parts.append(part)
bpy.ops.object.select_all(action="DESELECT")
for part in parts:
    part.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
anatomy = parts[0]
anatomy.name = "Robert_Anatomy_Construction_ESTIMATED"
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
anatomy.data.remesh_voxel_size = 0.0035
anatomy.data.remesh_voxel_adaptivity = 0.0
bpy.ops.object.voxel_remesh()

bpy.context.view_layer.objects.active = body
body.select_set(True)
union = body.modifiers.new("LocalAdultTopologyUnion", "BOOLEAN")
union.operation = "UNION"
union.solver = "EXACT"
union.object = anatomy
while list(body.modifiers).index(union) > 0:
    bpy.ops.object.modifier_move_up(modifier=union.name)
bpy.ops.object.modifier_apply(modifier=union.name)
bpy.data.objects.remove(anatomy, do_unlink=True)
for polygon in body.data.polygons:
    polygon.use_smooth = True

body.name = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V11_FROM_V1"
body["status"] = "AWAITING ROBERT STATIC LIKENESS REVIEW"
body["preferred_source"] = "V1"
body["v7_direction_rejected"] = True
body["runtime_activation_allowed"] = False
body["movement_claimed"] = False
body["adult_topology_estimation"] = "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"
body["regional_skin_variation"] = "PRESERVED_FROM_V1_TEXTURE"
body["hair_status"] = "ABSENT"
body["glasses_status"] = "ABSENT"

rig.animation_data_clear()
body.parent = None
body["rig_binding_status"] = "DEFERRED — STATIC LIKENESS REVIEW ONLY"

blend_path = OUT / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V11_FROM_V1.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
(OUT / "BUILD_REPORT.json").write_text(json.dumps({
    "schema_version": 1,
    "status": "AWAITING ROBERT STATIC LIKENESS REVIEW",
    "preferred_base": "V1",
    "v7_direction": "REJECTED_BY_OWNER",
    "slightly_thinner_than_v1": True,
    "adult_topology": "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE",
    "skin_variation": ["existing V1 lip, nipple, nail, and regional texture variation"],
    "hair": "absent",
    "glasses": "absent",
    "movement_claimed": False,
    "runtime_activation_allowed": False,
}, indent=2) + "\n", encoding="utf-8")
print(blend_path)
