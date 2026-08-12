"""Build the single inactive Biological Robert static-likeness review candidate.

This is a protected anatomical review artifact.  It deliberately contains no
movement action, hair, glasses, clothing claim, or runtime approval.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
import bmesh


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Avatar/avatar_builder/tooling"))
import mb_lab_official as mblab  # noqa: E402

OUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v7"
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
mblab.register()
mblab.algorithms.remove_censors = lambda: None
scene = bpy.context.scene
scene.mblab_character_name = "m_ca01"
scene.mblab_use_ik = False
scene.mblab_use_muscle = False
scene.mblab_use_cycles = False
scene.mblab_use_eevee = False
mblab.start_lab_session()

body = next(
    obj for obj in scene.objects
    if obj.type == "MESH" and obj.get("manuellab_id") == "m_ca01"
)

# Cross-view evidence shows a tall, broad, high-body-mass adult man.  The
# profile and rear views justify abdominal, chest, hip and thigh mass that the
# prior reduced candidate incorrectly removed.
body.character_age = 0.28
body.character_mass = 0.27
body.character_tone = -0.24
mblab.age_update(body, bpy.context)
mblab.mass_update(body, bpy.context)
mblab.tone_update(body, bpy.context)

morphs = {
    # Body/proportion pass.
    "Abdomen_Mass": 0.12,
    "Chest_Girth": 0.14,
    "Chest_SizeX": 0.10,
    "Chest_SizeY": 0.14,
    "Torso_BellyPosZ": -0.10,
    "Waist_Size": 0.14,
    "Shoulders_Mass": 0.13,
    "Shoulders_SizeX": 0.13,
    "Shoulders_PosZ": -0.04,
    "Neck_Mass": 0.15,
    "Neck_Length": -0.22,
    "Neck_Size": 0.10,
    "Arms_UpperarmGirth": 0.15,
    "Arms_ForearmMass": 0.12,
    "Hands_Size": 0.08,
    "Hands_Mass": 0.10,
    "Legs_UpperThighGirth": 0.15,
    "Legs_LowerThighGirth": 0.14,
    "Legs_CalfGirth": 0.10,
    "Legs_AnkleSize": 0.06,
    # Robert-specific head/face evidence from front and opposed profiles.
    "Head_SizeX": 0.18,
    "Head_SizeZ": -0.10,
    "Head_Nucha": 0.10,
    "Forehead_SizeX": 0.13,
    "Forehead_SizeZ": -0.06,
    "Forehead_Curve": -0.04,
    "Eyebrows_Ridge": 0.12,
    "Eyebrows_PosZ": -0.08,
    "Eyes_Size": -0.15,
    "Eyes_SizeZ": -0.10,
    "Eyes_PosX": 0.04,
    "Eyes_TypeHooded": 0.18,
    "Eyes_BagProminence": 0.12,
    "Eyes_BagSize": 0.10,
    "Nose_BridgeSizeX": 0.16,
    "Nose_BaseSizeX": 0.22,
    "Nose_BaseSizeZ": 0.06,
    "Nose_TipSize": 0.14,
    "Nose_SizeY": 0.08,
    "Face_Parallelepiped": 0.30,
    "Face_Ellipsoid": -0.12,
    "Jaw_ScaleX": 0.25,
    "Jaw_Angle": 0.10,
    "Jaw_Prominence": 0.08,
    "Chin_SizeX": 0.20,
    "Chin_SizeZ": -0.08,
    "Chin_Prominence": 0.05,
    "Mouth_SizeX": 0.08,
    "Mouth_UpperlipSizeZ": -0.06,
    "Mouth_LowerlipSizeZ": -0.03,
    "Mouth_CornersPosZ": -0.04,
}

applied = {}
for key, value in morphs.items():
    if key in mblab.mblab_humanoid.character_data:
        setattr(body, key, value)
        applied[key] = value
mblab.mblab_humanoid.update_character(mode="update_all")

# Owner-authorized protected anatomical review: replace MB-Lab's black censor
# material with the same skin material used by the surrounding adult topology.
# This remains local/private and is never a public or ordinary preview.
generic_mat = bpy.data.materials.get("MBlab_generic")
skin_mat = bpy.data.materials.get("MBLab_skin3")
if generic_mat and skin_mat:
    for index, assigned in enumerate(body.data.materials):
        if assigned == generic_mat:
            body.data.materials[index] = skin_mat

# The MB-Lab base topology itself is doll-safe even after its censor material
# is removed.  The owner explicitly authorized an anatomically complete adult
# male base and supplied adult anatomy references.  Add a separate, neutral,
# nonsexual, estimated external-anatomy component rather than misreporting the
# smooth base as complete.  Identity-specific dimensions remain OWNER INPUT
# NEEDED; only general resting anatomy is represented here.
anatomy_parts = []
anatomy_skin = skin_mat
# Broad root volume overlaps the existing lower pelvis so the final Boolean
# union has a continuous anatomical transition rather than a pasted-on edge.
bpy.ops.mesh.primitive_uv_sphere_add(
    segments=48, ring_count=28, radius=0.050,
    location=(0, -0.075, 0.775), scale=(1.55, 1.15, 1.10),
)
anatomy_parts.append(bpy.context.object)
bpy.ops.mesh.primitive_uv_sphere_add(
    segments=48, ring_count=28, radius=0.040,
    location=(0, -0.085, 0.690), scale=(1.22, 0.88, 1.15),
)
anatomy_parts.append(bpy.context.object)
bpy.ops.mesh.primitive_uv_sphere_add(
    segments=40, ring_count=24, radius=0.025,
    location=(0, -0.142, 0.705), scale=(0.82, 0.88, 1.82),
)
shaft = bpy.context.object
anatomy_parts.append(shaft)
bpy.ops.mesh.primitive_uv_sphere_add(
    segments=40, ring_count=24, radius=0.025,
    location=(0, -0.143, 0.659), scale=(0.88, 0.90, 0.72),
)
anatomy_parts.append(bpy.context.object)
for index, part in enumerate(anatomy_parts, 1):
    part.name = f"Robert_Adult_Male_External_Anatomy_ESTIMATED_{index:02d}"
    if anatomy_skin:
        part.data.materials.append(anatomy_skin)
    part["classification"] = "ESTIMATED_FROM_AUTHORIZED_ADULT_ANATOMY_GUIDANCE"
    part["identity_measurement_status"] = "OWNER INPUT NEEDED"

# Collapse the fitted morphs and retain only the continuous skin surface. Eye,
# tooth, lash and nail islands are rebuilt as separate components where
# necessary; they must not confuse the single-skin-surface validator.
bpy.context.view_layer.objects.active = body
body.select_set(True)
if body.data.shape_keys:
    bpy.ops.object.shape_key_remove(all=True)
for modifier in list(body.modifiers):
    body.modifiers.remove(modifier)
skin_slots = {index for index, mat in enumerate(body.data.materials) if mat == skin_mat}
bm = bmesh.new()
bm.from_mesh(body.data)
remove_faces = [face for face in bm.faces if face.material_index not in skin_slots]
bmesh.ops.delete(bm, geom=remove_faces, context="FACES")
loose = [vert for vert in bm.verts if not vert.link_faces]
if loose:
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
bm.to_mesh(body.data)
bm.free()

# Join all overlapping anatomical construction volumes into the skin object,
# then voxel-remesh them as one watertight surface.  This prevents a visually
# attached but internally disconnected component from falsely passing.
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
for part in anatomy_parts:
    part.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
body.data.remesh_voxel_size = 0.009
body.data.remesh_voxel_adaptivity = 0.0
bpy.ops.object.voxel_remesh()
body.data.materials.clear()
review_skin = bpy.data.materials.new("Robert_Continuous_Skin_Review")
review_skin.use_nodes = True
skin_bsdf = review_skin.node_tree.nodes.get("Principled BSDF")
skin_bsdf.inputs["Base Color"].default_value = (0.52, 0.31, 0.245, 1)
skin_bsdf.inputs["Roughness"].default_value = 0.58
body.data.materials.append(review_skin)
for group in list(body.vertex_groups):
    body.vertex_groups.remove(group)
pelvis_group = body.vertex_groups.new(name="pelvis")
pelvis_ids = [v.index for v in body.data.vertices if v.co.z < 0.86]
pelvis_group.add(pelvis_ids, 1.0, "REPLACE")
for polygon in body.data.polygons:
    polygon.use_smooth = True
surface_smooth = body.modifiers.new(name="StaticReviewSurfaceSmooth", type="SMOOTH")
surface_smooth.factor = 0.18
surface_smooth.iterations = 2
body["adult_topology_integration"] = "VOXEL_REMESH_SINGLE_SKIN_SURFACE"
body["adult_topology_estimation"] = "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"

# Repair the stock eye materials for deterministic private review.  Their
# missing/unsupported image links otherwise render the iris as blank white.
for mat_name, color in (
    ("MBLab_Iris_V4", (0.16, 0.075, 0.035, 1)),
    ("MBlab_pupil", (0.004, 0.003, 0.002, 1)),
):
    eye_mat = bpy.data.materials.get(mat_name)
    if eye_mat:
        eye_mat.diffuse_color = color
        eye_mat.use_nodes = True
        bsdf = eye_mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            base = bsdf.inputs.get("Base Color")
            if base:
                for link in list(base.links):
                    eye_mat.node_tree.links.remove(link)
                base.default_value = color

# The stock eye shader renders cyan in this Blender build.  Add fitted,
# separate brown iris surfaces for the private likeness review rather than
# allowing that rendering defect to distort the face assessment.
iris_mat = bpy.data.materials.new("Robert_Brown_Iris_Review")
iris_mat.diffuse_color = (0.19, 0.095, 0.045, 1)
iris_mat.use_nodes = True
iris_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.19, 0.095, 0.045, 1)
iris_mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.72
pupil_mat = bpy.data.materials.new("Robert_Pupil_Review")
pupil_mat.diffuse_color = (0.008, 0.006, 0.004, 1)
pupil_mat.use_nodes = True
pupil_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.008, 0.006, 0.004, 1)
pupil_mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.80
eye_white_mat = bpy.data.materials.new("Robert_Eye_White_Review")
eye_white_mat.use_nodes = True
eye_white_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.72, 0.68, 0.63, 1)
eye_white_mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.48
for side, x in (("L", -0.034), ("R", 0.034)):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=40, ring_count=24, radius=0.0185,
        location=(x, -0.132, 1.700), scale=(1.0, 0.92, 0.82),
    )
    eye = bpy.context.object
    eye.name = f"Robert_{side}_Separate_Eyeball_REVIEW"
    eye.data.materials.append(eye_white_mat)
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32, ring_count=16, radius=0.0105,
        location=(x, -0.1510, 1.700), scale=(0.68, 0.10, 0.68),
    )
    iris = bpy.context.object
    iris.name = f"Robert_{side}_Separate_Brown_Iris_REVIEW"
    iris.data.materials.append(iris_mat)
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=24, ring_count=12, radius=0.0042,
        location=(x, -0.1520, 1.700), scale=(0.80, 0.08, 0.80),
    )
    pupil = bpy.context.object
    pupil.name = f"Robert_{side}_Separate_Pupil_REVIEW"
    pupil.data.materials.append(pupil_mat)

body.name = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V7"
body["status"] = "AWAITING ROBERT STATIC LIKENESS REVIEW"
body["runtime_activation_allowed"] = False
body["movement_claimed"] = False
body["hair_status"] = "ABSENT_PENDING_HEAD_APPROVAL"
body["glasses_status"] = "ABSENT_PENDING_HEAD_APPROVAL"
body["review_classification"] = "PRIVATE_PROTECTED_ANATOMICAL"

rig = next((obj for obj in scene.objects if obj.type == "ARMATURE"), None)
if rig:
    rig.name = "BIOLOGICAL_ROBERT_STATIC_REST_RIG"
    rig.animation_data_clear()
    body.parent = None
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    try:
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        body["rig_binding_status"] = "AUTOMATIC_WEIGHTS_BOUND_TO_STATIC_REST_RIG"
    except RuntimeError as exc:
        body["rig_binding_status"] = f"FAILED — {exc}"
    for pose_bone in rig.pose.bones:
        pose_bone.rotation_mode = "QUATERNION"
        pose_bone.rotation_quaternion = (1, 0, 0, 0)
        pose_bone.location = (0, 0, 0)
        pose_bone.scale = (1, 1, 1)
    # Stable neutral review stance: arms relaxed beside the torso rather than
    # the MB-Lab fitting A-pose.  No animation/action is created.
    for name, z_rotation in (("upperarm_L", -0.72), ("upperarm_R", 0.72)):
        pose_bone = rig.pose.bones.get(name)
        if pose_bone:
            pose_bone.rotation_mode = "XYZ"
            pose_bone.rotation_euler = (0, 0, z_rotation)

blend_path = OUT / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V7.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

report = {
    "schema_version": 1,
    "status": "AWAITING ROBERT STATIC LIKENESS REVIEW",
    "subject_id": "BIOLOGICAL_ROBERT_AVATAR",
    "private_protected_anatomical_review": True,
    "runtime_activation_allowed": False,
    "owner_approved": False,
    "movement_claimed": False,
    "synthetic_robert_updated": False,
    "hair": "absent pending head approval",
    "glasses": "absent pending head approval",
    "applied_morphs": applied,
    "source_method": "protected multiview visual fitting with official MB-Lab adult male topology",
}
(OUT / "BUILD_REPORT.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(blend_path)
