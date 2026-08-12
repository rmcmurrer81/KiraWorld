"""Build two separate private Robert candidates from the reviewed foundation."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/private_owner_review/dual_robert_20260729/foundation/robert_fitting_foundation.blend"
OUTPUT = ROOT / "Avatar/outputs/user/dual_robert_candidates_20260729"
OUTPUT.mkdir(parents=True, exist_ok=True)


def material(name, color, metallic=0.0, roughness=0.5):
    value = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    value.diffuse_color = (*color, 1.0)
    value.use_nodes = True
    bsdf = value.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return value


def parent_to_head(obj, rig):
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = "head"
    obj.matrix_world = world


def add_hair(rig):
    brown = material("Robert_Hair_Brown", (0.19, 0.095, 0.045), roughness=0.72)
    curve_data = bpy.data.curves.new("Robert_Hair_Strands", "CURVE")
    curve_data.dimensions = "3D"
    curve_data.bevel_depth = 0.0032
    curve_data.bevel_resolution = 2
    curve_data.resolution_u = 2
    # A layered short haircut; every strand is geometry, not a helmet cap.
    for ring, z in enumerate((1.705, 1.735, 1.765, 1.795, 1.815)):
        radius_x = 0.115 * (1.0 - max(0, ring - 2) * 0.08)
        radius_y = 0.105 * (1.0 - max(0, ring - 2) * 0.10)
        count = 48 - ring * 4
        for index in range(count):
            angle = 2 * math.pi * index / count
            x = math.sin(angle) * radius_x
            y = -0.055 + math.cos(angle) * radius_y
            # Front/top strands sweep slightly to Robert's right.
            sweep = 0.018 * max(0.0, math.cos(angle))
            spline = curve_data.splines.new("POLY")
            spline.points.add(2)
            spline.points[0].co = (x, y, z - 0.02, 1)
            spline.points[1].co = (x + sweep, y - 0.008, z + 0.025, 1)
            spline.points[2].co = (x + sweep * 1.5, y - 0.012, z + 0.045, 1)
    hair = bpy.data.objects.new("Robert_Hair_Separate", curve_data)
    bpy.context.collection.objects.link(hair)
    curve_data.materials.append(brown)
    parent_to_head(hair, rig)
    return hair


def add_glasses(rig):
    dark = material("Robert_Glasses_Dark", (0.015, 0.012, 0.01), metallic=0.15, roughness=0.28)
    pieces = []
    for x in (-0.037, 0.037):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.037,
            minor_radius=0.0032,
            major_segments=40,
            minor_segments=8,
            location=(x, -0.184, 1.735),
            rotation=(math.pi / 2, 0, 0),
        )
        pieces.append(bpy.context.object)
    for location, scale in (
        ((0, -0.184, 1.735), (0.020, 0.003, 0.003)),
        ((-0.079, -0.158, 1.735), (0.043, 0.0025, 0.0025)),
        ((0.079, -0.158, 1.735), (0.043, 0.0025, 0.0025)),
    ):
        bpy.ops.mesh.primitive_cube_add(location=location, scale=scale)
        pieces.append(bpy.context.object)
    bpy.ops.object.select_all(action="DESELECT")
    for piece in pieces:
        piece.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    bpy.ops.object.join()
    glasses = pieces[0]
    glasses.name = "Robert_Glasses_Separate_Removable"
    glasses.data.materials.append(dark)
    parent_to_head(glasses, rig)
    return glasses


def _assign_weight(obj, group_name, weight=1.0):
    group = obj.vertex_groups.new(name=group_name)
    group.add(list(range(len(obj.data.vertices))), weight, "REPLACE")


def _join_named(parts, name):
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    parts[0].name = name
    return parts[0]


def add_review_clothes(rig):
    black = material("Robert_Review_Cloth_Black", (0.012, 0.014, 0.018), roughness=0.86)
    # Independently authored, articulated fitting garments.  They are not
    # duplicated body polygons, and each region follows its carrying bone.
    bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=0.34, radius2=0.285, depth=0.55, location=(0, -0.005, 1.22))
    torso = bpy.context.object
    torso.scale.y = 0.64
    _assign_weight(torso, "spine01")
    shirt_parts = [torso]
    for x, bone in ((-0.365, "upperarm_L"), (0.365, "upperarm_R")):
        bpy.ops.mesh.primitive_cone_add(
            vertices=40, radius1=0.115, radius2=0.095, depth=0.32,
            location=(x, -0.005, 1.40), rotation=(0, math.pi / 2, 0),
        )
        sleeve = bpy.context.object
        _assign_weight(sleeve, bone)
        shirt_parts.append(sleeve)
    shirt = _join_named(shirt_parts, "Robert_Review_Shirt_Separate")

    bpy.ops.mesh.primitive_cone_add(vertices=56, radius1=0.285, radius2=0.33, depth=0.28, location=(0, 0, 0.89))
    waist = bpy.context.object
    waist.scale.y = 0.66
    _assign_weight(waist, "pelvis")
    pants_parts = [waist]
    for x, bone in ((-0.155, "thigh_L"), (0.155, "thigh_R")):
        bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.155, radius2=0.19, depth=0.58, location=(x, 0, 0.60))
        leg = bpy.context.object
        leg.scale.y = 0.72
        _assign_weight(leg, bone)
        pants_parts.append(leg)
    pants = _join_named(pants_parts, "Robert_Review_Pants_Separate")

    garments = [shirt, pants]
    for garment in garments:
        garment.data.materials.append(black)
        modifier = garment.modifiers.new("Armature", "ARMATURE")
        modifier.object = rig
        garment.parent = rig
    return garments


def add_motion_action(rig):
    action = bpy.data.actions.new("BODY_ONLY_REVIEW_walk_stop_turn_sit_rise_lie_get_up")
    rig.animation_data_create()
    rig.animation_data.action = action
    bones = rig.pose.bones
    # The MB-Lab IK controls are useful interactively, but they override the
    # FK rotations used by this bounded body-only proof.  Mute them for this
    # authored action so the encoded movement reflects the keyed limbs.
    for bone in bones:
        for constraint in bone.constraints:
            constraint.mute = True
    rig.rotation_mode = "XYZ"

    def set_pose(frame, values):
        for name, rotation in values.items():
            bone = bones.get(name)
            if bone is None:
                continue
            bone.rotation_mode = "XYZ"
            bone.rotation_euler = rotation
            bone.keyframe_insert("rotation_euler", frame=frame, group=name)
        root = bones.get("root")
        if root:
            root.keyframe_insert("location", frame=frame, group="root")

    set_pose(1, {})
    # Four continuous walk cycles then stop.
    for frame, sign in ((20, 1), (32, -1), (44, 1), (56, -1), (68, 0)):
        set_pose(frame, {
            "thigh_L": (0.42 * sign, 0, 0),
            "thigh_R": (-0.42 * sign, 0, 0),
            "calf_L": (-0.34 if sign < 0 else 0, 0, 0),
            "calf_R": (-0.34 if sign > 0 else 0, 0, 0),
            "upperarm_L": (-0.24 * sign, 0, 0),
            "upperarm_R": (0.24 * sign, 0, 0),
        })
    set_pose(88, {"spine01": (0, 0, 0.42)})
    set_pose(108, {"spine01": (0, 0, -0.42)})
    set_pose(128, {})
    rig.location = (0, 0, 0)
    rig.rotation_euler = (0, 0, 0)
    rig.keyframe_insert("location", frame=1)
    rig.keyframe_insert("rotation_euler", frame=1)
    rig.location = (0, -0.5, 0)
    rig.keyframe_insert("location", frame=68)
    rig.keyframe_insert("location", frame=128)
    rig.rotation_euler = (0, 0, 0.45)
    rig.keyframe_insert("rotation_euler", frame=88)
    rig.rotation_euler = (0, 0, -0.45)
    rig.keyframe_insert("rotation_euler", frame=108)
    rig.rotation_euler = (0, 0, 0)
    rig.keyframe_insert("rotation_euler", frame=128)
    set_pose(158, {"thigh_L": (-1.35, 0, 0), "thigh_R": (-1.35, 0, 0), "calf_L": (1.35, 0, 0), "calf_R": (1.35, 0, 0), "spine01": (0.16, 0, 0)})
    rig.location = (0, -0.5, -0.48)
    rig.keyframe_insert("location", frame=158)
    set_pose(188, {"thigh_L": (-1.35, 0, 0), "thigh_R": (-1.35, 0, 0), "calf_L": (1.35, 0, 0), "calf_R": (1.35, 0, 0)})
    set_pose(218, {})
    rig.location = (0, -0.5, 0)
    rig.keyframe_insert("location", frame=218)
    set_pose(258, {"spine01": (-0.08, 0, 0), "thigh_L": (-0.08, 0, 0), "thigh_R": (-0.08, 0, 0)})
    rig.rotation_euler = (math.pi / 2, 0, 0)
    rig.location = (0, 0.25, 0.55)
    rig.keyframe_insert("rotation_euler", frame=258)
    rig.keyframe_insert("location", frame=258)
    set_pose(288, {})
    set_pose(328, {})
    rig.keyframe_insert("rotation_euler", frame=288)
    rig.keyframe_insert("location", frame=288)
    rig.rotation_euler = (0, 0, 0)
    rig.location = (0, 0, 0)
    rig.keyframe_insert("rotation_euler", frame=328)
    rig.keyframe_insert("location", frame=328)
    return action


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for target_id, slug in (
    ("BIOLOGICAL_ROBERT_AVATAR", "biological_robert_avatar"),
    ("SYNTHETIC_ROBERT_TWIN_BODY", "synthetic_robert_twin_body"),
):
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    body = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
    rig = next(obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE")
    body.name = f"{target_id}_Body"
    rig.name = f"{target_id}_Rig"
    hair = add_hair(rig)
    glasses = add_glasses(rig)
    garments = add_review_clothes(rig)
    # These first authored fitting components visibly failed inspection.
    # Preserve them as evidence in the candidate file but exclude them from
    # the body/rig proof; they must never masquerade as approved components.
    hair["quality_status"] = "REJECTED — SPIKED/FITTING FAILURE"
    hair.hide_render = True
    for garment in garments:
        garment["quality_status"] = "REJECTED — FIT/DEFORMATION FAILURE"
        garment.hide_render = True
    action = add_motion_action(rig)
    body["subject_id"] = target_id
    body["status"] = "PARTIAL — LIKENESS INCOMPLETE — NOT ACTIVATED"
    glasses["component_state"] = "worn"
    glasses["supported_states"] = "stored,held,worn,removed,placed,discarded"
    candidate_dir = OUTPUT / slug
    candidate_dir.mkdir(parents=True, exist_ok=True)
    blend_path = candidate_dir / f"{slug}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.object.select_all(action="DESELECT")
    for obj in (body, rig, hair, glasses, *garments):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = body
    glb_path = candidate_dir / f"{slug}.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_skins=True,
        export_morph=True,
    )
    manifest = {
        "schema_version": 1,
        "subject_id": target_id,
        "status": "PARTIAL — LIKENESS INCOMPLETE — NOT ACTIVATED",
        "body_sha256": sha(glb_path),
        "body_path": glb_path.name,
        "blend_sha256": sha(blend_path),
        "components": {
            "body": body.name,
            "rig": rig.name,
            "hair": hair.name,
            "glasses": glasses.name,
            "review_clothes": [item.name for item in garments],
        },
        "glasses_states": ["stored", "held", "worn", "removed", "placed", "discarded"],
        "rejected_components": {
            "hair": "spiked/fitting failure; excluded from renders",
            "review_clothes": "fit/deformation failure; excluded from renders",
        },
        "body_only_motion_action": action.name,
        "runtime_activation_allowed": False,
        "owner_review_required": True,
        "truth_note": "A real fitted foundation and motion action exist. Hair and review clothing failed visible inspection and are excluded. Likeness, glasses behavior, and movement quality remain incomplete.",
    }
    manifest_path = candidate_dir / "CANDIDATE_MANIFEST.json"
    manifest["component_manifest_path"] = manifest_path.name
    manifest["rig_manifest_path"] = "RIG_AND_MOTION_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (candidate_dir / "RIG_AND_MOTION_MANIFEST.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "subject_id": target_id,
                "rig": rig.name,
                "action": action.name,
                "frames": 328,
                "fps": 24,
                "body_only_test": True,
                "person_activated": False,
                "required_review": ["walk", "stop", "turn_left", "turn_right", "sit", "rise", "lie_down", "get_up"],
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(target_id, glb_path)
