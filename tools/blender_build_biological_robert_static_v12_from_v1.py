"""Build the V12 private static review from the owner-preferred V1 foundation."""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
REFERENCE = ROOT / "Avatar/avatar_builder/asset_library/adult_anatomy_reference/male_nude_2_1_f117148577.glb"
OUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v12_from_v1"
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1")
if body is None:
    raise SystemExit("owner-preferred V1 body missing")

# Preserve the accepted V1 face and authored skin texture. Remove only its
# earlier experimental anatomy construction and review-only iris overlays.
for obj in list(bpy.context.scene.objects):
    if obj == body:
        continue
    if any(token in obj.name for token in (
        "External_Anatomy", "Separate_Brown_Iris", "Separate_Pupil",
    )):
        bpy.data.objects.remove(obj, do_unlink=True)

# Owner direction: slightly thinner than V1, retaining the V1 head and face.
for vertex in body.data.vertices:
    z = vertex.co.z
    if z >= 1.58:
        factor = 1.0
    elif z >= 1.42:
        factor = 0.968 + (z - 1.42) / 0.16 * 0.032
    else:
        factor = 0.968
    vertex.co.x *= factor
    vertex.co.y *= factor

skin = bpy.data.materials.get("MBLab_skin3")
if skin is None:
    raise SystemExit("V1 continuous authored skin material missing")

# Bake V1's evaluated surface. This retains its accepted static pose and avoids
# the modifier corruption seen in rejected V8.
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

# Import the authorized reference temporarily and extract only its local
# pubic/external-anatomy topology. Its body proportions, face, identity, skin,
# and material are not transferred.
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(REFERENCE))
imported = [obj for obj in bpy.data.objects if obj not in before]
reference_body = bpy.data.objects.get("Object003_Object003_mtl_0")
if reference_body is None:
    raise SystemExit("authorized adult topology source missing")
world_points = [reference_body.matrix_world @ vertex.co for vertex in reference_body.data.vertices]
selected_faces = []
selected_indices = set()
for polygon in reference_body.data.polygons:
    points = [world_points[index] for index in polygon.vertices]
    center = sum(points, Vector()) / len(points)
    if (
        -2.2 <= center.x <= 3.2
        and 27.5 <= center.z <= 35.8
        and center.y >= 3.8
    ):
        selected_faces.append(tuple(polygon.vertices))
        selected_indices.update(polygon.vertices)
index_map = {old: new for new, old in enumerate(sorted(selected_indices))}
vertices = [world_points[index] for index in sorted(selected_indices)]
faces = [tuple(index_map[index] for index in face) for face in selected_faces]
patch_mesh = bpy.data.meshes.new("Authorized_Local_Adult_Topology")
patch_mesh.from_pydata(vertices, [], faces)
patch_mesh.update()
patch = bpy.data.objects.new("Authorized_Local_Adult_Topology", patch_mesh)
bpy.context.collection.objects.link(patch)
for obj in imported:
    bpy.data.objects.remove(obj, do_unlink=True)

# Fit the small topology patch to Robert without inheriting the reference
# model's athletic proportions. Reference front is +Y; Robert front is -Y.
source_center = Vector((2.106474, 4.708917, 29.793213))
for vertex in patch.data.vertices:
    point = vertex.co - source_center
    vertex.co = Vector((-point.x, -point.y, point.z)) * 0.033 + Vector((0, -0.160, 0.670))
patch.data.materials.append(skin)

# The extracted patch is an open local surface. Give it a thin inward
# construction shell, remesh only this local volume, then union it with the
# preserved V1 body. Global remeshing is intentionally avoided.
bpy.context.view_layer.objects.active = patch
patch.select_set(True)
solidify = patch.modifiers.new("InwardConstructionShell", "SOLIDIFY")
solidify.thickness = 0.010
solidify.offset = -1.0
bpy.ops.object.modifier_apply(modifier=solidify.name)
patch.data.remesh_voxel_size = 0.002
patch.data.remesh_voxel_adaptivity = 0.0
bpy.ops.object.voxel_remesh()

bpy.context.view_layer.objects.active = body
body.select_set(True)
union = body.modifiers.new("LocalAdultTopologyUnion", "BOOLEAN")
union.operation = "UNION"
union.solver = "EXACT"
union.object = patch
while list(body.modifiers).index(union) > 0:
    bpy.ops.object.modifier_move_up(modifier=union.name)
bpy.ops.object.modifier_apply(modifier=union.name)
bpy.data.objects.remove(patch, do_unlink=True)
for polygon in body.data.polygons:
    polygon.use_smooth = True

body.name = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V12_FROM_V1"
body["status"] = "AWAITING ROBERT STATIC LIKENESS REVIEW"
body["preferred_source"] = "V1"
body["v7_direction_rejected"] = True
body["slightly_thinner_than_v1"] = True
body["adult_topology_estimation"] = "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"
body["regional_skin_variation"] = "PRESERVED_FROM_V1_TEXTURE"
body["hair_status"] = "ABSENT"
body["glasses_status"] = "ABSENT"
body["rig_binding_status"] = "DEFERRED — STATIC LIKENESS REVIEW ONLY"
body["movement_claimed"] = False
body["runtime_activation_allowed"] = False
body.parent = None

for armature in (obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"):
    armature.hide_render = True

blend_path = OUT / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V12_FROM_V1.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
(OUT / "BUILD_REPORT.json").write_text(json.dumps({
    "schema_version": 1,
    "status": "AWAITING ROBERT STATIC LIKENESS REVIEW",
    "preferred_base": "V1",
    "v7_direction": "REJECTED_BY_OWNER",
    "slightly_thinner_than_v1": True,
    "anatomy_method": "local topology extracted from authorized reference, fitted and unioned to V1 surface",
    "anatomy_estimation_label": "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE",
    "reference_traits_not_transferred": [
        "athletic proportions", "face", "identity", "skin", "material",
    ],
    "skin_variation": "preserved V1 authored texture including regional variation",
    "hair": "absent",
    "glasses": "absent",
    "movement_claimed": False,
    "runtime_activation_allowed": False,
}, indent=2) + "\n", encoding="utf-8")
print(blend_path)
