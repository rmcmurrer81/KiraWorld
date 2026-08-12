from __future__ import annotations

import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.avatar_body_policy_gate import enforce_marinette_procedural_body_policy  # noqa: E402

MODEL_DIR = ROOT / "Avatar" / "models" / "temp_ai" / "ladybug_marinette_expanded_smoke"
AVATAR = MODEL_DIR / "avatar.glb"
METADATA = MODEL_DIR / "avatar_foundation_skeleton_v1.json"

created: list[tuple[bpy.types.Object, str | None]] = []


def material(name: str, color: tuple[float, float, float, float], roughness: float = 0.65):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Alpha"].default_value = color[3]
    if color[3] < 1:
        mat.blend_method = "BLEND"
        mat.use_screen_refraction = True
        mat.show_transparent_back = True
    return mat


BONE = material("foundation_bone_warm_white", (0.86, 0.83, 0.78, 1.0))
JOINT = material("foundation_joint_blue", (0.18, 0.36, 0.58, 1.0))
SKIN_MARKER = material("foundation_skin_marker", (0.90, 0.67, 0.58, 1.0))
UNDERLAYER = material("foundation_modest_underlayer", (0.78, 0.82, 0.84, 1.0))
HAIR_GUIDE = material("foundation_hair_guide_navy", (0.01, 0.03, 0.11, 1.0), 0.42)
EYE = material("foundation_eye_blue", (0.03, 0.52, 0.78, 1.0), 0.35)
BLACK = material("foundation_black_detail", (0.01, 0.012, 0.015, 1.0))
OUTFIT_SHIRT = material("marinette_first_outfit_soft_white_shirt", (0.94, 0.92, 0.86, 1.0), 0.72)
OUTFIT_JACKET = material("marinette_first_outfit_dark_jacket", (0.025, 0.045, 0.095, 1.0), 0.58)
OUTFIT_PANTS = material("marinette_first_outfit_rose_pants", (0.74, 0.45, 0.56, 1.0), 0.7)
OUTFIT_SHOE = material("marinette_first_outfit_dark_flat_shoes", (0.015, 0.015, 0.018, 1.0), 0.5)
OUTFIT_DETAIL = material("marinette_first_outfit_shirt_detail", (0.78, 0.18, 0.28, 1.0), 0.62)
LEFT = material("foundation_left_side_marker", (0.50, 0.63, 0.88, 1.0))
RIGHT = material("foundation_right_side_marker", (0.88, 0.52, 0.62, 1.0))
HAND_CONTACT = material("foundation_hand_contact_collider", (0.30, 0.86, 1.0, 0.0), 0.35)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def sphere(name: str, loc, scale, mat, bone: str, segments: int = 24, register: bool = True):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=max(8, segments // 2), radius=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    if register:
        created.append((obj, bone))
    return obj


def cube(name: str, loc, scale, mat, bone: str, register: bool = True):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    if register:
        created.append((obj, bone))
    return obj


def cylinder_between(name: str, start, end, radius: float, mat, bone: str, vertices: int = 18, register: bool = True):
    start_v = Vector(start)
    end_v = Vector(end)
    direction = end_v - start_v
    mid = start_v + direction * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=direction.length, location=mid)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    if register:
        created.append((obj, bone))
    return obj


def assign_mesh_to_bone(obj: bpy.types.Object, bone: str):
    obj.vertex_groups.clear()
    group = obj.vertex_groups.new(name=bone)
    group.add(range(len(obj.data.vertices)), 1.0, "REPLACE")


def join_hand_parts(name: str, parts: list[bpy.types.Object]):
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    for poly in obj.data.polygons:
        poly.use_smooth = True
    created.append((obj, None))
    return obj


def add_skinned_hand_mesh(side: str, sign: int, hand, base_x: float, finger_specs):
    parts: list[bpy.types.Object] = []

    palm = sphere(
        f"skinned_hand_palm_source.{side}",
        hand,
        (0.046, 0.025, 0.037),
        SKIN_MARKER,
        f"hand.{side}",
        24,
        register=False,
    )
    assign_mesh_to_bone(palm, f"hand.{side}")
    parts.append(palm)

    for finger, x_offset, y_offset, z_start, segments, radius in finger_specs:
        start = Vector((base_x + sign * x_offset, y_offset, z_start))
        for seg_index, (dx, dy, dz) in enumerate(segments, start=1):
            end = start + Vector((sign * dx, dy, dz))
            bone_name = f"{finger}.{seg_index:02d}.{side}"
            segment = cylinder_between(
                f"skinned_hand_{finger}_{seg_index:02d}_source.{side}",
                tuple(start),
                tuple(end),
                max(0.0052, radius - (seg_index - 1) * 0.00055),
                SKIN_MARKER,
                bone_name,
                14,
                register=False,
            )
            assign_mesh_to_bone(segment, bone_name)
            parts.append(segment)
            if seg_index == len(segments):
                tip = sphere(
                    f"skinned_hand_{finger}_tip_source.{side}",
                    tuple(end),
                    (radius * 0.9, radius * 0.9, radius * 0.9),
                    SKIN_MARKER,
                    bone_name,
                    12,
                    register=False,
                )
                assign_mesh_to_bone(tip, bone_name)
                parts.append(tip)
                contact = sphere(
                    f"hand_contact_collider_{finger}_tip.{side}",
                    tuple(end),
                    (0.014, 0.014, 0.014),
                    HAND_CONTACT,
                    bone_name,
                    10,
                )
            start = end

    return join_hand_parts(f"skinned_hand_mesh.{side}", parts)


def create_armature():
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm = bpy.context.object
    arm.name = "Marinette_Foundation_Skeleton_v1"
    arm.data.name = "Marinette_Foundation_Skeleton_v1_Data"
    arm.show_in_front = True
    bones = arm.data.edit_bones
    bones.remove(bones[0])

    def bone(name, head, tail, parent=None):
        b = bones.new(name)
        b.head = Vector(head)
        b.tail = Vector(tail)
        b.roll = 0
        if parent:
            b.parent = bones[parent]
            b.use_connect = False
        return b

    bone("hips", (0, 0, 0.90), (0, 0, 1.04))
    bone("spine", (0, 0, 1.04), (0, 0, 1.35), "hips")
    bone("chest", (0, 0, 1.35), (0, 0, 1.48), "spine")
    bone("neck", (0, 0, 1.48), (0, 0, 1.57), "chest")
    bone("head", (0, 0, 1.57), (0, 0, 1.73), "neck")
    bone("jaw", (0, 0.10, 1.59), (0, 0.17, 1.56), "head")

    for side, sign in (("L", -1), ("R", 1)):
        bone(f"upper_arm.{side}", (0.16 * sign, 0, 1.42), (0.33 * sign, 0, 1.21), "chest")
        bone(f"forearm.{side}", (0.33 * sign, 0, 1.21), (0.43 * sign, 0.02, 1.00), f"upper_arm.{side}")
        bone(f"hand.{side}", (0.43 * sign, 0.02, 1.00), (0.45 * sign, 0.06, 0.93), f"forearm.{side}")

        base_x = 0.45 * sign
        finger_specs = [
            ("thumb", -0.045, 0.045, 0.928, [(-0.016, 0.026, -0.014), (-0.010, 0.020, -0.014), (-0.006, 0.015, -0.010)]),
            ("index", -0.018, 0.069, 0.946, [(-0.004, 0.034, -0.018), (-0.002, 0.026, -0.016), (-0.001, 0.020, -0.012)]),
            ("middle", 0.000, 0.073, 0.940, [(0.000, 0.037, -0.019), (0.000, 0.028, -0.017), (0.000, 0.022, -0.013)]),
            ("ring", 0.018, 0.070, 0.934, [(0.003, 0.034, -0.018), (0.002, 0.026, -0.016), (0.001, 0.020, -0.012)]),
            ("pinky", 0.036, 0.064, 0.927, [(0.006, 0.029, -0.016), (0.004, 0.023, -0.014), (0.002, 0.017, -0.011)]),
        ]
        for finger, x_offset, y_offset, z_start, segments in finger_specs:
            parent = f"hand.{side}"
            start = Vector((base_x + sign * x_offset, y_offset, z_start))
            for seg_index, (dx, dy, dz) in enumerate(segments, start=1):
                end = start + Vector((sign * dx, dy, dz))
                b = bone(f"{finger}.{seg_index:02d}.{side}", start, end, parent)
                parent = b.name
                start = end

        bone(f"thigh.{side}", (0.085 * sign, 0, 0.90), (0.105 * sign, 0.01, 0.53), "hips")
        bone(f"shin.{side}", (0.105 * sign, 0.01, 0.53), (0.10 * sign, 0.01, 0.055), f"thigh.{side}")
        bone(f"foot.{side}", (0.10 * sign, 0.01, 0.055), (0.10 * sign, 0.20, 0.055), f"shin.{side}")

        bone(f"pigtail.{side}.01", (0.13 * sign, -0.02, 1.66), (0.23 * sign, -0.03, 1.55), "head")
        bone(f"pigtail.{side}.02", (0.23 * sign, -0.03, 1.55), (0.31 * sign, -0.02, 1.45), f"pigtail.{side}.01")

    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def bind_meshes(arm):
    for obj, bone in created:
        if bone:
            assign_mesh_to_bone(obj, bone)
        modifier = obj.modifiers.new("Foundation_Skeleton_Armature", "ARMATURE")
        modifier.object = arm
        obj.parent = arm


def add_foundation_body():
    sphere("head_scale_marker", (0, 0.025, 1.66), (0.125, 0.105, 0.14), SKIN_MARKER, "head", 32)
    sphere("neck_joint", (0, 0, 1.50), (0.035, 0.035, 0.045), JOINT, "neck")
    sphere("torso_modest_underlayer", (0, 0, 1.23), (0.16, 0.105, 0.245), UNDERLAYER, "spine", 32)
    sphere("pelvis_modest_underlayer", (0, 0, 0.88), (0.14, 0.095, 0.105), UNDERLAYER, "hips", 32)
    sphere("marinette_first_outfit_white_shirt_shell", (0, 0.012, 1.23), (0.166, 0.108, 0.246), OUTFIT_SHIRT, "spine", 32)
    cube("marinette_first_outfit_dark_jacket_left_panel", (-0.074, 0.112, 1.25), (0.052, 0.012, 0.17), OUTFIT_JACKET, "chest")
    cube("marinette_first_outfit_dark_jacket_right_panel", (0.074, 0.112, 1.25), (0.052, 0.012, 0.17), OUTFIT_JACKET, "chest")
    cube("marinette_first_outfit_dark_jacket_hem", (0, 0.11, 1.04), (0.13, 0.012, 0.024), OUTFIT_JACKET, "spine")
    cube("marinette_first_outfit_shirt_front_detail", (0, 0.122, 1.22), (0.018, 0.008, 0.082), OUTFIT_DETAIL, "spine")
    sphere("marinette_first_outfit_rose_pants_hip_shell", (0, 0.006, 0.86), (0.142, 0.096, 0.108), OUTFIT_PANTS, "hips", 32)

    sphere("left_eye_forward_marker", (-0.042, 0.112, 1.68), (0.018, 0.006, 0.018), EYE, "head")
    sphere("right_eye_forward_marker", (0.042, 0.112, 1.68), (0.018, 0.006, 0.018), EYE, "head")
    cylinder_between("mouth_forward_marker", (-0.035, 0.125, 1.61), (0.035, 0.125, 1.61), 0.004, BLACK, "jaw", 10)
    sphere("nose_forward_marker", (0, 0.12, 1.64), (0.014, 0.010, 0.018), SKIN_MARKER, "head")

    sphere("hair_cap_reference", (0, -0.005, 1.75), (0.13, 0.10, 0.055), HAIR_GUIDE, "head", 32)
    for side, sign in (("L", -1), ("R", 1)):
        sphere(f"pigtail_mass_reference.{side}", (0.27 * sign, -0.02, 1.51), (0.065, 0.055, 0.055), HAIR_GUIDE, f"pigtail.{side}.02", 24)
        cylinder_between(f"pigtail_hair_bone_visible.{side}", (0.15 * sign, -0.02, 1.64), (0.30 * sign, -0.02, 1.48), 0.010, HAIR_GUIDE, f"pigtail.{side}.01")

        shoulder = (0.16 * sign, 0, 1.42)
        elbow = (0.33 * sign, 0, 1.21)
        wrist = (0.43 * sign, 0.02, 1.00)
        hand = (0.45 * sign, 0.06, 0.93)
        hip = (0.085 * sign, 0, 0.90)
        knee = (0.105 * sign, 0.01, 0.53)
        ankle = (0.10 * sign, 0.01, 0.055)
        toe = (0.10 * sign, 0.20, 0.055)
        base_x = 0.45 * sign

        cylinder_between(f"upper_arm_bone_visible.{side}", shoulder, elbow, 0.026, BONE, f"upper_arm.{side}")
        cylinder_between(f"forearm_bone_visible.{side}", elbow, wrist, 0.023, BONE, f"forearm.{side}")
        cylinder_between(f"marinette_first_outfit_jacket_upper_sleeve.{side}", shoulder, elbow, 0.030, OUTFIT_JACKET, f"upper_arm.{side}")
        cylinder_between(f"marinette_first_outfit_jacket_forearm_sleeve.{side}", elbow, wrist, 0.026, OUTFIT_JACKET, f"forearm.{side}")
        sphere(f"shoulder_joint_visible.{side}", shoulder, (0.035, 0.035, 0.035), JOINT, f"upper_arm.{side}")
        sphere(f"elbow_joint_visible.{side}", elbow, (0.032, 0.032, 0.032), JOINT, f"forearm.{side}")
        sphere(f"wrist_joint_visible.{side}", wrist, (0.026, 0.026, 0.026), JOINT, f"hand.{side}")

        visible_finger_specs = [
            ("thumb", -0.045, 0.045, 0.928, [(-0.016, 0.026, -0.014), (-0.010, 0.020, -0.014), (-0.006, 0.015, -0.010)], 0.0105),
            ("index", -0.018, 0.069, 0.946, [(-0.004, 0.034, -0.018), (-0.002, 0.026, -0.016), (-0.001, 0.020, -0.012)], 0.0094),
            ("middle", 0.000, 0.073, 0.940, [(0.000, 0.037, -0.019), (0.000, 0.028, -0.017), (0.000, 0.022, -0.013)], 0.0097),
            ("ring", 0.018, 0.070, 0.934, [(0.003, 0.034, -0.018), (0.002, 0.026, -0.016), (0.001, 0.020, -0.012)], 0.0090),
            ("pinky", 0.036, 0.064, 0.927, [(0.006, 0.029, -0.016), (0.004, 0.023, -0.014), (0.002, 0.017, -0.011)], 0.0078),
        ]
        add_skinned_hand_mesh(side, sign, hand, base_x, visible_finger_specs)

        cylinder_between(f"thigh_bone_visible.{side}", hip, knee, 0.034, BONE, f"thigh.{side}")
        cylinder_between(f"shin_bone_visible.{side}", knee, ankle, 0.030, BONE, f"shin.{side}")
        cylinder_between(f"marinette_first_outfit_rose_pants_thigh.{side}", hip, knee, 0.038, OUTFIT_PANTS, f"thigh.{side}")
        cylinder_between(f"marinette_first_outfit_rose_pants_shin.{side}", knee, ankle, 0.034, OUTFIT_PANTS, f"shin.{side}")
        cylinder_between(f"foot_bone_visible.{side}", ankle, toe, 0.026, BLACK, f"foot.{side}")
        cube(f"flat_foot_sole.{side}", (0.10 * sign, 0.12, 0.020), (0.040, 0.095, 0.012), OUTFIT_SHOE, f"foot.{side}")
        cube(f"marinette_first_outfit_flat_shoe_upper.{side}", (0.10 * sign, 0.145, 0.044), (0.046, 0.095, 0.018), OUTFIT_SHOE, f"foot.{side}")
        sphere(f"hip_joint_visible.{side}", hip, (0.038, 0.038, 0.038), JOINT, f"thigh.{side}")
        sphere(f"knee_joint_visible.{side}", knee, (0.034, 0.034, 0.034), JOINT, f"shin.{side}")
        sphere(f"ankle_joint_visible.{side}", ankle, (0.026, 0.026, 0.026), JOINT, f"foot.{side}")


def set_pose(arm, frame: int, rotations: dict[str, tuple[float, float, float]]):
    bpy.context.scene.frame_set(frame)
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.keyframe_insert("rotation_euler", frame=frame)
        pb.keyframe_insert("location", frame=frame)

    for bone, rot in rotations.items():
        pb = arm.pose.bones[bone]
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = tuple(math.radians(v) for v in rot)
        pb.keyframe_insert("rotation_euler", frame=frame)


def merge_poses(*poses: dict[str, tuple[float, float, float]]) -> dict[str, tuple[float, float, float]]:
    merged: dict[str, tuple[float, float, float]] = {}
    for pose in poses:
        merged.update(pose)
    return merged


def relaxed_hands_pose() -> dict[str, tuple[float, float, float]]:
    pose: dict[str, tuple[float, float, float]] = {}
    for side in ("L", "R"):
        thumb_twist = -18 if side == "L" else 18
        pose[f"thumb.01.{side}"] = (-18, 0, thumb_twist)
        pose[f"thumb.02.{side}"] = (-15, 0, 0)
        pose[f"thumb.03.{side}"] = (-8, 0, 0)
        for finger, curl in (("index", -36), ("middle", -40), ("ring", -38), ("pinky", -34)):
            pose[f"{finger}.01.{side}"] = (curl, 0, 0)
            pose[f"{finger}.02.{side}"] = (curl * 0.72, 0, 0)
            pose[f"{finger}.03.{side}"] = (curl * 0.42, 0, 0)
    return pose


def open_hands_pose() -> dict[str, tuple[float, float, float]]:
    pose: dict[str, tuple[float, float, float]] = {}
    for side in ("L", "R"):
        pose[f"thumb.01.{side}"] = (-6, 0, -10 if side == "L" else 10)
        pose[f"thumb.02.{side}"] = (-4, 0, 0)
        pose[f"thumb.03.{side}"] = (-2, 0, 0)
        for finger in ("index", "middle", "ring", "pinky"):
            pose[f"{finger}.01.{side}"] = (-8, 0, 0)
            pose[f"{finger}.02.{side}"] = (-4, 0, 0)
            pose[f"{finger}.03.{side}"] = (-2, 0, 0)
    return pose


def closed_hands_pose() -> dict[str, tuple[float, float, float]]:
    pose: dict[str, tuple[float, float, float]] = {}
    for side in ("L", "R"):
        pose[f"thumb.01.{side}"] = (-34, 0, -22 if side == "L" else 22)
        pose[f"thumb.02.{side}"] = (-25, 0, 0)
        pose[f"thumb.03.{side}"] = (-14, 0, 0)
        for finger, curl in (("index", -48), ("middle", -52), ("ring", -50), ("pinky", -44)):
            pose[f"{finger}.01.{side}"] = (curl, 0, 0)
            pose[f"{finger}.02.{side}"] = (curl * 0.72, 0, 0)
            pose[f"{finger}.03.{side}"] = (curl * 0.42, 0, 0)
    return pose


def right_handle_grip_pose() -> dict[str, tuple[float, float, float]]:
    pose = relaxed_hands_pose()
    side = "R"
    pose[f"thumb.01.{side}"] = (-38, 0, 26)
    pose[f"thumb.02.{side}"] = (-28, 0, 0)
    pose[f"thumb.03.{side}"] = (-16, 0, 0)
    for finger, curl in (("index", -58), ("middle", -62), ("ring", -54), ("pinky", -44)):
        pose[f"{finger}.01.{side}"] = (curl, 0, 0)
        pose[f"{finger}.02.{side}"] = (curl * 0.76, 0, 0)
        pose[f"{finger}.03.{side}"] = (curl * 0.48, 0, 0)
    return pose


def make_action(arm, name: str, frames, defaults: dict[str, tuple[float, float, float]] | None = None):
    action = bpy.data.actions.new(name)
    arm.animation_data_create()
    arm.animation_data.action = action
    for frame, rotations in frames:
        set_pose(arm, frame, merge_poses(defaults or {}, rotations))
    action.use_fake_user = True
    return action


def make_actions(arm):
    relaxed_hands = relaxed_hands_pose()
    make_action(arm, "idle_foundation_breathing", [
        (1, {}),
        (30, {"spine": (1.5, 0, 0), "head": (-1.0, 0, 0)}),
        (60, {}),
    ], defaults=relaxed_hands)

    make_action(arm, "walk_foundation_forward", [
        (1, {
            "hips": (0, 0, -2.0), "spine": (1.2, 0, 1.0), "chest": (-0.8, 0, 0.6), "head": (0, 0, -0.6),
            "thigh.L": (18, 0, 1.2), "shin.L": (-10, 0, 0), "foot.L": (-6, 0, 0),
            "thigh.R": (-16, 0, -1.2), "shin.R": (-34, 0, 0), "foot.R": (16, 0, 0),
            "upper_arm.L": (-13, 0, -1), "forearm.L": (24, 0, 0), "hand.L": (0, 0, 1),
            "upper_arm.R": (13, 0, 1), "forearm.R": (22, 0, 0), "hand.R": (0, 0, -1),
        }),
        (8, {
            "hips": (0, 0, -1.0), "spine": (-0.4, 0, 0.4), "chest": (0.2, 0, 0.2), "head": (0, 0, -0.2),
            "thigh.L": (10, 0, 0.4), "shin.L": (-30, 0, 0), "foot.L": (2, 0, 0),
            "thigh.R": (-8, 0, -0.4), "shin.R": (-42, 0, 0), "foot.R": (18, 0, 0),
            "upper_arm.L": (-7, 0, -1), "forearm.L": (22, 0, 0), "hand.L": (0, 0, 1),
            "upper_arm.R": (7, 0, 1), "forearm.R": (22, 0, 0), "hand.R": (0, 0, -1),
        }),
        (15, {
            "hips": (0, 0, 0.0), "spine": (-0.2, 0, 0.0), "chest": (0.2, 0, 0.0), "head": (0, 0, 0.0),
            "thigh.L": (-2, 0, 0), "shin.L": (-18, 0, 0), "foot.L": (0, 0, 0),
            "thigh.R": (14, 0, 0), "shin.R": (-48, 0, 0), "foot.R": (2, 0, 0),
            "upper_arm.L": (0, 0, -1), "forearm.L": (18, 0, 0), "hand.L": (0, 0, 0),
            "upper_arm.R": (0, 0, 1), "forearm.R": (18, 0, 0), "hand.R": (0, 0, 0),
        }),
        (22, {
            "hips": (0, 0, 1.0), "spine": (0.8, 0, -0.4), "chest": (-0.4, 0, -0.2), "head": (0, 0, 0.2),
            "thigh.L": (-15, 0, -0.4), "shin.L": (-30, 0, 0), "foot.L": (20, 0, 0),
            "thigh.R": (18, 0, 0.4), "shin.R": (-14, 0, 0), "foot.R": (-6, 0, 0),
            "upper_arm.L": (8, 0, -1), "forearm.L": (20, 0, 0), "hand.L": (0, 0, 1),
            "upper_arm.R": (-8, 0, 1), "forearm.R": (22, 0, 0), "hand.R": (0, 0, -1),
        }),
        (30, {
            "hips": (0, 0, 2.0), "spine": (1.2, 0, -1.0), "chest": (-0.8, 0, -0.6), "head": (0, 0, 0.6),
            "thigh.L": (-16, 0, -1.2), "shin.L": (-34, 0, 0), "foot.L": (16, 0, 0),
            "thigh.R": (18, 0, 1.2), "shin.R": (-10, 0, 0), "foot.R": (-6, 0, 0),
            "upper_arm.L": (13, 0, -1), "forearm.L": (22, 0, 0), "hand.L": (0, 0, 1),
            "upper_arm.R": (-13, 0, 1), "forearm.R": (24, 0, 0), "hand.R": (0, 0, -1),
        }),
        (38, {
            "hips": (0, 0, 1.0), "spine": (-0.4, 0, -0.4), "chest": (0.2, 0, -0.2), "head": (0, 0, 0.2),
            "thigh.L": (-8, 0, -0.4), "shin.L": (-42, 0, 0), "foot.L": (18, 0, 0),
            "thigh.R": (10, 0, 0.4), "shin.R": (-30, 0, 0), "foot.R": (2, 0, 0),
            "upper_arm.L": (7, 0, -1), "forearm.L": (22, 0, 0), "hand.L": (0, 0, 1),
            "upper_arm.R": (-7, 0, 1), "forearm.R": (22, 0, 0), "hand.R": (0, 0, -1),
        }),
        (45, {
            "hips": (0, 0, 0.0), "spine": (-0.2, 0, 0.0), "chest": (0.2, 0, 0.0), "head": (0, 0, 0.0),
            "thigh.L": (14, 0, 0), "shin.L": (-48, 0, 0), "foot.L": (2, 0, 0),
            "thigh.R": (-2, 0, 0), "shin.R": (-18, 0, 0), "foot.R": (0, 0, 0),
            "upper_arm.L": (0, 0, -1), "forearm.L": (18, 0, 0), "hand.L": (0, 0, 0),
            "upper_arm.R": (0, 0, 1), "forearm.R": (18, 0, 0), "hand.R": (0, 0, 0),
        }),
        (52, {
            "hips": (0, 0, -1.0), "spine": (0.8, 0, 0.4), "chest": (-0.4, 0, 0.2), "head": (0, 0, -0.2),
            "thigh.L": (18, 0, 0.4), "shin.L": (-14, 0, 0), "foot.L": (-6, 0, 0),
            "thigh.R": (-15, 0, -0.4), "shin.R": (-30, 0, 0), "foot.R": (20, 0, 0),
            "upper_arm.L": (-8, 0, -1), "forearm.L": (22, 0, 0), "hand.L": (0, 0, 1),
            "upper_arm.R": (8, 0, 1), "forearm.R": (20, 0, 0), "hand.R": (0, 0, -1),
        }),
        (60, {
            "hips": (0, 0, -2.0), "spine": (1.2, 0, 1.0), "chest": (-0.8, 0, 0.6), "head": (0, 0, -0.6),
            "thigh.L": (18, 0, 1.2), "shin.L": (-10, 0, 0), "foot.L": (-6, 0, 0),
            "thigh.R": (-16, 0, -1.2), "shin.R": (-34, 0, 0), "foot.R": (16, 0, 0),
            "upper_arm.L": (-13, 0, -1), "forearm.L": (24, 0, 0), "hand.L": (0, 0, 1),
            "upper_arm.R": (13, 0, 1), "forearm.R": (22, 0, 0), "hand.R": (0, 0, -1),
        }),
    ], defaults=relaxed_hands)

    sit_pose = {
        "hips": (-6, 0, 0),
        "spine": (5, 0, 0),
        "chest": (-3, 0, 0),
        "head": (2, 0, 0),
        "thigh.L": (68, 0, -4),
        "shin.L": (-72, 0, 0),
        "foot.L": (12, 0, 0),
        "thigh.R": (68, 0, 4),
        "shin.R": (-72, 0, 0),
        "foot.R": (12, 0, 0),
        "upper_arm.L": (6, 0, -8),
        "forearm.L": (26, 0, 0),
        "hand.L": (0, 0, 4),
        "upper_arm.R": (6, 0, 8),
        "forearm.R": (26, 0, 0),
        "hand.R": (0, 0, -4),
    }
    make_action(arm, "sit_foundation", [
        (1, {}),
        (18, merge_poses(sit_pose, {"thigh.L": (34, 0, -3), "thigh.R": (34, 0, 3), "shin.L": (-34, 0, 0), "shin.R": (-34, 0, 0)})),
        (36, sit_pose),
        (72, sit_pose),
    ], defaults=relaxed_hands)

    lie_pose = {
        "hips": (0, 0, 0),
        "spine": (2, 0, 0),
        "chest": (-2, 0, 0),
        "head": (8, 0, 0),
        "thigh.L": (8, 0, -3),
        "shin.L": (-12, 0, 0),
        "foot.L": (0, 0, 0),
        "thigh.R": (8, 0, 3),
        "shin.R": (-12, 0, 0),
        "foot.R": (0, 0, 0),
        "upper_arm.L": (-6, 0, -12),
        "forearm.L": (22, 0, 0),
        "hand.L": (0, 0, 10),
        "upper_arm.R": (-6, 0, 12),
        "forearm.R": (22, 0, 0),
        "hand.R": (0, 0, -10),
    }
    make_action(arm, "lie_down_foundation", [
        (1, sit_pose),
        (28, merge_poses(lie_pose, {"spine": (10, 0, 0), "head": (4, 0, 0)})),
        (55, lie_pose),
        (86, lie_pose),
    ], defaults=relaxed_hands)

    make_action(arm, "reach_door_handle_foundation", [
        (1, {"head": (0, -4, 0)}),
        (12, {"upper_arm.R": (-22, -6, 8), "forearm.R": (-28, 0, 0), "hand.R": (0, 0, -4), "head": (0, -8, 0)}),
        (22, merge_poses(right_handle_grip_pose(), {"upper_arm.R": (-34, -8, 12), "forearm.R": (-40, 0, 0), "hand.R": (0, 0, -8), "chest": (0, -3, 2), "head": (0, -10, 0)})),
        (34, merge_poses(right_handle_grip_pose(), {"upper_arm.R": (-36, -8, 14), "forearm.R": (-42, 0, 0), "hand.R": (0, 0, -4), "chest": (0, -4, 3), "head": (0, -8, 0)})),
        (48, {"upper_arm.R": (-20, -5, 8), "forearm.R": (-30, 0, 0), "hand.R": (0, 0, -3), "head": (0, -5, 0)}),
        (60, {}),
    ], defaults=relaxed_hands)

    hand_open = open_hands_pose()
    hand_closed = closed_hands_pose()

    make_action(arm, "relaxed_hands_foundation", [(1, open_hands_pose()), (25, relaxed_hands)])
    make_action(arm, "open_hands_foundation", [(1, relaxed_hands), (25, hand_open)])
    make_action(arm, "close_hands_foundation", [(1, relaxed_hands), (25, hand_closed)])
    make_action(arm, "wave_foundation", [
        (1, {}),
        (15, {"upper_arm.R": (-70, 0, 38), "forearm.R": (-55, 0, 0), "hand.R": (0, 0, -25)}),
        (30, {"upper_arm.R": (-70, 0, 38), "forearm.R": (-55, 0, 0), "hand.R": (0, 0, 25)}),
        (45, {"upper_arm.R": (-70, 0, 38), "forearm.R": (-55, 0, 0), "hand.R": (0, 0, -25)}),
        (60, {}),
    ], defaults=relaxed_hands)


def export_avatar(body_policy_gate: dict):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if AVATAR.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        shutil.copy2(AVATAR, MODEL_DIR / f"avatar_before_foundation_skeleton_v1_{stamp}.glb")

    bpy.ops.export_scene.gltf(
        filepath=str(AVATAR),
        export_format="GLB",
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_yup=True,
    )

    METADATA.write_text(json.dumps({
        "schema_version": 1,
        "asset": "avatar.glb",
        "body_policy_validation": body_policy_gate,
        "created_by": "tools/build_ladybug_foundation_skeleton_v1.py",
        "purpose": "Clean movement foundation with a first safe civilian outfit layer. This is not final Marinette character art.",
        "builder_foundation": {
            "use_as_avatar_builder_base": True,
            "fit_reference_images_after_rig_validation": True,
            "appearance_should_be_generated_on_top_of_this_rig": True,
            "notes": [
                "Keep the shared skeleton stable before adding character-specific body shapes.",
                "Avatar Builder should preserve this bone layout so future AI bodies can reuse movement training data.",
                "One skinned hand mesh per side is weighted to the actual hand and finger bones so hand poses can curl and grip.",
                "The hand uses a smaller smooth palm and slightly thicker fingers to avoid lumpy knuckles while preserving the same Avatar Builder bone contract.",
                "A first civilian outfit shell is bound to the rig so movement testing uses a clothed body over the safe non-anatomical base layer.",
            ],
        },
        "target_height_m": 1.62,
        "forward_axis": "+Y",
        "contains": {
            "armature": "Marinette_Foundation_Skeleton_v1",
            "major_joints": ["hips", "spine", "chest", "neck", "head", "jaw", "shoulders", "elbows", "wrists", "hips", "knees", "ankles", "feet"],
            "fingers_per_hand": 5,
            "finger_segments": 3,
            "hair_placeholders": ["hair_cap_reference", "pigtail_mass_reference.L", "pigtail_mass_reference.R"],
            "first_outfit_placeholders": ["white shirt", "dark jacket", "rose pants", "dark flat shoes"],
            "animations": [
                "idle_foundation_breathing",
                "walk_foundation_forward",
                "sit_foundation",
                "lie_down_foundation",
                "reach_door_handle_foundation",
                "relaxed_hands_foundation",
                "open_hands_foundation",
                "close_hands_foundation",
                "wave_foundation",
            ],
        },
        "next_step": "After the shared skeleton walks, grips, and plants feet correctly in Kira World, bind richer body/clothing/hair art to this same skeleton.",
    }, indent=2), encoding="utf-8")


def main():
    body_policy_gate = enforce_marinette_procedural_body_policy(ROOT)
    clear_scene()
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 80
    arm = create_armature()
    add_foundation_body()
    bind_meshes(arm)
    make_actions(arm)
    bpy.ops.object.light_add(type="AREA", location=(0, -3, 3))
    bpy.context.object.name = "foundation_preview_light"
    bpy.context.object.data.energy = 450
    bpy.context.object.data.size = 4
    bpy.ops.object.camera_add(location=(0, -3.0, 1.15), rotation=(math.radians(76), 0, 0))
    bpy.context.scene.camera = bpy.context.object
    export_avatar(body_policy_gate)


if __name__ == "__main__":
    main()


# CODEX_FOUNDATION_GAIT_V8
# Shared movement contract used by Kira World and the avatar builder. The current
# simple body should keep this mechanical and readable; later visual bodies can
# bind richer meshes, cloth, hair, and facial rigs to the same controls.
FOUNDATION_GAIT_V8 = {
    "authored_clip_seconds": 2.5,
    "runtime_ground_meters_per_second": 0.52,
    "runtime_upstairs_meters_per_second": 0.42,
    "stride_sync": "Runtime walk frame is driven by actual meters moved; timeScale remains a diagnostic value.",
    "stride_meters": 0.85,
    "phase_locked_to_distance": True,
    "support_phase": 0.52,
    "knee_lift_degrees": 48.0,
    "knee_plant_degrees": 10.0,
    "ankle_toeoff_degrees": 20.0,
    "elbow_swing_degrees": 24.0,
    "shoulder_swing_degrees": 14.0,
    "hip_counter_rotation_degrees": 5.0,
    "hand_contract": {
        "digits_per_hand": 5,
        "joints_per_finger": 3,
        "controls": ["curl", "spread", "thumbOppose", "pinch", "relax", "handleGrip"],
        "visible_segments_weighted_to_finger_bones": True,
        "next_visual_upgrade": "one-piece skinned hand mesh over the same controls",
        "default_pose": "relaxed_hands_foundation with curled non-pointing fingers",
        "door_pose": "reach_door_handle_foundation",
    },
    "door_interaction": {
        "sequence": ["face_handle", "reach", "finger_grip", "door_rotates", "release"],
        "door_opens_after_seconds": 0.95,
        "finish_seconds": 2.35,
        "runtime_success_rule": "door only opens after visible hand/finger contact reaches the handle threshold",
    },
    "posture_practice": {
        "clips": ["sit_foundation", "lie_down_foundation"],
        "targets": ["living_room_couch", "front_lawn_grass", "ladybug_guest_bed"],
    },
    "stairs": {
        "mode": "step-by-step",
        "runtime_treads": 16,
        "max_vertical_step_meters": 0.23,
        "require_foot_contact_before_pelvis_lift": True,
    },
}
FOUNDATION_GAIT_V7 = FOUNDATION_GAIT_V8
FOUNDATION_GAIT_V6 = FOUNDATION_GAIT_V8
FOUNDATION_GAIT_V5 = FOUNDATION_GAIT_V6
FOUNDATION_GAIT_V4 = FOUNDATION_GAIT_V6
FOUNDATION_GAIT_V3 = FOUNDATION_GAIT_V6
