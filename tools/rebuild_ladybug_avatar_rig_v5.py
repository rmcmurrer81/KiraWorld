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

from tools.avatar_body_policy_gate import enforce_marinette_live_body_policy  # noqa: E402

MODEL_DIR = ROOT / "Avatar" / "models" / "temp_ai" / "ladybug_marinette_expanded_smoke"
AVATAR = MODEL_DIR / "avatar.glb"
METADATA = MODEL_DIR / "avatar_functional_rig_v5.json"


def material(name: str, color: tuple[float, float, float, float], roughness: float = 0.55):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


SKIN = material("v5_warm_skin", (0.92, 0.67, 0.56, 1), 0.62)
NAIL = material("v5_soft_nail", (0.98, 0.82, 0.77, 1), 0.4)
HAIR = material("v5_midnight_hair", (0.012, 0.02, 0.075, 1), 0.3)
LID = material("v5_soft_lid", (0.82, 0.56, 0.48, 1), 0.55)


def world_bounds(obj: bpy.types.Object):
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(v.x for v in corners), min(v.y for v in corners), min(v.z for v in corners))),
        Vector((max(v.x for v in corners), max(v.y for v in corners), max(v.z for v in corners))),
    )


def clean_old_helpers():
    removed = []
    for obj in list(bpy.context.scene.objects):
        n = obj.name.lower()
        if n.startswith(("v3_", "v4_")) or "_control" in n or "curl_control" in n:
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    return removed


def make_armature():
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    armature = bpy.context.object
    armature.name = "Marinette_Rig_v5"
    armature.data.name = "Marinette_Rig_v5_Data"
    armature.show_in_front = True
    eb = armature.data.edit_bones
    eb.remove(eb[0])

    def bone(name, head, tail, parent=None):
        b = eb.new(name)
        b.head = Vector(head)
        b.tail = Vector(tail)
        b.roll = 0
        if parent:
            b.parent = eb[parent]
            b.use_connect = False
        return b

    bone("hips", (0, 0, 1.05), (0, 0, 1.42))
    bone("spine", (0, 0, 1.38), (0, 0, 1.92), "hips")
    bone("chest", (0, 0, 1.88), (0, 0, 2.35), "spine")
    bone("neck", (0, 0, 2.32), (0, 0, 2.62), "chest")
    bone("head", (0, 0, 2.58), (0, 0, 3.35), "neck")
    bone("jaw", (0, -0.04, 2.84), (0, -0.11, 2.74), "head")
    for side, sign in (("L", -1), ("R", 1)):
        bone(f"upper_arm.{side}", (0.18 * sign, 0, 2.2), (0.48 * sign, -0.005, 1.86), "chest")
        bone(f"forearm.{side}", (0.48 * sign, -0.005, 1.86), (0.43 * sign, -0.01, 1.55), f"upper_arm.{side}")
        bone(f"hand.{side}", (0.43 * sign, -0.01, 1.55), (0.43 * sign, -0.04, 1.42), f"forearm.{side}")
        bone(f"thigh.{side}", (0.12 * sign, 0, 1.06), (0.16 * sign, 0, 0.55), "hips")
        bone(f"shin.{side}", (0.16 * sign, 0, 0.55), (0.13 * sign, 0, 0.14), f"thigh.{side}")
        bone(f"foot.{side}", (0.13 * sign, 0, 0.14), (0.13 * sign, -0.18, 0.04), f"shin.{side}")
        for finger, spread in (("thumb", -0.055), ("index", -0.025), ("middle", 0.0), ("ring", 0.025), ("pinky", 0.05)):
            base = Vector((0.43 * sign + 0.025 * sign, -0.04, 1.48 + spread))
            b1 = bone(f"{finger}.01.{side}", base, base + Vector((0.035 * sign, -0.045, 0)), f"hand.{side}")
            b2 = bone(f"{finger}.02.{side}", b1.tail, b1.tail + Vector((0.025 * sign, -0.04, 0)), b1.name)
            bone(f"{finger}.03.{side}", b2.tail, b2.tail + Vector((0.018 * sign, -0.032, 0)), b2.name)
        bone(f"pigtail.{side}.01", (0.18 * sign, 0.06, 2.84), (0.36 * sign, 0.04, 2.7), "head")
        bone(f"pigtail.{side}.02", (0.36 * sign, 0.04, 2.7), (0.48 * sign, 0.0, 2.55), f"pigtail.{side}.01")
        bone(f"pigtail.{side}.03", (0.48 * sign, 0.0, 2.55), (0.55 * sign, -0.03, 2.42), f"pigtail.{side}.02")
    for i, x in enumerate((-0.22, -0.1, 0.02, 0.14), start=1):
        bone(f"bang.{i:02d}", (x, -0.04, 3.34), (x - 0.04, -0.12, 3.03), "head")

    bpy.ops.object.mode_set(mode="OBJECT")
    return armature


def classify_bone(obj: bpy.types.Object):
    n = obj.name.lower()
    if "mouth" in n:
        return "jaw"
    if any(k in n for k in ("eye", "iris", "pupil", "glint", "brow", "lash", "face", "nose", "ear", "blush")):
        return "head"
    if "neck" in n:
        return "neck"
    side = ".L" if "left" in n or "_l_" in n else ".R" if "right" in n or "_r_" in n else ""
    if "pigtail" in n:
        return f"pigtail{side}.02" if side else "head"
    if any(k in n for k in ("hair", "fringe", "bang")):
        return "head"
    if "finger" in n or "hand" in n:
        return f"hand{side}" if side else "hand.L"
    if "forearm" in n:
        return f"forearm{side}" if side else "forearm.L"
    if "arm" in n:
        return f"upper_arm{side}" if side else "upper_arm.L"
    if "foot" in n or "shoe" in n:
        return f"foot{side}" if side else "foot.L"
    if "leg" in n or "shin" in n:
        return f"shin{side}" if side else "shin.L"
    if any(k in n for k in ("body", "shirt", "jacket", "torso", "chest")):
        return "chest"
    if obj.type == "MESH":
        bmin, bmax = world_bounds(obj)
        center = (bmin + bmax) * 0.5
        if center.z > 2.55:
            return "head"
        if center.z > 1.45:
            return "chest"
        return "hips"
    return "hips"


def bind_meshes(armature):
    bound = 0
    for obj in list(bpy.context.scene.objects):
        if obj.type != "MESH":
            continue
        bone_name = classify_bone(obj)
        if bone_name not in armature.data.bones:
            bone_name = "hips"
        obj.vertex_groups.clear()
        group = obj.vertex_groups.new(name=bone_name)
        group.add(range(len(obj.data.vertices)), 1.0, "REPLACE")
        mod = obj.modifiers.new("Marinette_Rig_v5_Armature", "ARMATURE")
        mod.object = armature
        obj.parent = armature
        bound += 1
    return bound


def add_usable_fingers():
    created = []
    for form in ("civilian", "hero"):
        for side, sign in (("left", -1), ("right", 1)):
            hand = bpy.data.objects.get(f"{form}_{side}_hand")
            if not hand:
                continue
            bmin, bmax = world_bounds(hand)
            center = (bmin + bmax) * 0.5
            for i, spread in enumerate((-0.045, -0.018, 0.01, 0.036, 0.062)):
                base = Vector((center.x + sign * 0.035, bmin.y - 0.02, center.z + spread))
                bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.009, depth=0.095, location=base + Vector((sign * 0.026, -0.038, 0)))
                finger = bpy.context.object
                finger.name = f"v5_{form}_{side}_finger_{i+1}_deform_mesh"
                finger.rotation_euler[1] = math.pi / 2
                finger.data.materials.append(SKIN)
                bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.0105, location=base + Vector((sign * 0.055, -0.075, 0)))
                tip = bpy.context.object
                tip.name = f"v5_{form}_{side}_finger_{i+1}_tip"
                tip.data.materials.append(SKIN)
                bpy.ops.mesh.primitive_cube_add(size=1, location=base + Vector((sign * 0.06, -0.078, 0.006)))
                nail = bpy.context.object
                nail.name = f"v5_{form}_{side}_finger_{i+1}_nail"
                nail.scale = (0.006, 0.002, 0.004)
                nail.data.materials.append(NAIL)
                created.extend([finger.name, tip.name, nail.name])
    return created


def add_lids_and_shape_keys():
    created = []
    for side, x in (("left", -0.09), ("right", 0.09)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, -0.265, 3.095))
        lid = bpy.context.object
        lid.name = f"v5_{side}_blink_lid"
        lid.scale = (0.075, 0.006, 0.012)
        lid.data.materials.append(LID)
        lid.shape_key_add(name="Basis")
        closed = lid.shape_key_add(name="blink_closed")
        for v in closed.data:
            v.co.z -= 0.045
        created.append(lid.name)

    for name in ("shared_mouth", "shared_face"):
        obj = bpy.data.objects.get(name)
        if not obj or obj.type != "MESH":
            continue
        if not obj.data.shape_keys:
            obj.shape_key_add(name="Basis")
        for key in ("blink_left", "blink_right", "mouth_open", "viseme_AA", "viseme_EE", "viseme_OO", "viseme_MBP", "smile_soft"):
            if key not in obj.data.shape_keys.key_blocks:
                kb = obj.shape_key_add(name=key)
                if "mouth" in name:
                    for v in kb.data:
                        if "OO" in key:
                            v.co.x *= 0.75
                            v.co.z *= 1.08
                        elif "EE" in key:
                            v.co.x *= 1.18
                        elif key in ("mouth_open", "viseme_AA"):
                            v.co.z -= 0.025
                        elif "MBP" in key:
                            v.co.z += 0.01
    return created


def set_pose(armature, frame, values):
    bpy.context.scene.frame_set(frame)
    for bone_name, rot in values.items():
        pb = armature.pose.bones.get(bone_name)
        if not pb:
            continue
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = rot
        pb.keyframe_insert(data_path="rotation_euler", frame=frame)
    armature.keyframe_insert(data_path="location", frame=frame)


def make_action(armature, name, frames):
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    armature.animation_data_clear()
    armature.animation_data_create()
    action = bpy.data.actions.new(name)
    armature.animation_data.action = action
    for frame, loc, values in frames:
        armature.location = loc
        set_pose(armature, frame, values)
    track = armature.animation_data.nla_tracks.new()
    track.name = name
    track.strips.new(name, frames[0][0], action)
    armature.animation_data.action = None
    return action


def make_actions(armature):
    zero = Vector((0, 0, 0))
    clips = []
    clips.append(make_action(armature, "idle", [
        (1, zero, {"chest": (0.015, 0, 0), "head": (0, 0, 0)}),
        (32, Vector((0, 0, 0.015)), {"chest": (-0.012, 0, 0), "head": (0.018, 0.01, 0)}),
        (64, zero, {"chest": (0.015, 0, 0), "head": (0, 0, 0)}),
    ]).name)
    clips.append(make_action(armature, "walk", [
        (1, zero, {"thigh.L": (0.55, 0, 0), "thigh.R": (-0.45, 0, 0), "shin.L": (-0.35, 0, 0), "upper_arm.L": (-0.35, 0, 0), "upper_arm.R": (0.35, 0, 0)}),
        (16, Vector((0, 0, 0.025)), {"thigh.L": (-0.45, 0, 0), "thigh.R": (0.55, 0, 0), "shin.R": (-0.35, 0, 0), "upper_arm.L": (0.35, 0, 0), "upper_arm.R": (-0.35, 0, 0)}),
        (32, zero, {"thigh.L": (0.55, 0, 0), "thigh.R": (-0.45, 0, 0), "shin.L": (-0.35, 0, 0), "upper_arm.L": (-0.35, 0, 0), "upper_arm.R": (0.35, 0, 0)}),
    ]).name)
    clips.append(make_action(armature, "talking", [
        (1, zero, {"jaw": (0.05, 0, 0), "head": (0.02, 0, -0.04)}),
        (12, zero, {"jaw": (0.22, 0, 0), "head": (-0.01, 0.02, 0.04)}),
        (24, zero, {"jaw": (0.08, 0, 0), "head": (0.01, -0.02, 0)}),
        (36, zero, {"jaw": (0.2, 0, 0), "head": (0.02, 0, -0.04)}),
    ]).name)
    clips.append(make_action(armature, "wave", [
        (1, zero, {"upper_arm.R": (-0.2, 0, -0.35), "forearm.R": (-0.4, 0, 0.15)}),
        (18, zero, {"upper_arm.R": (-1.55, 0.1, -0.55), "forearm.R": (-0.55, 0.25, 0.55), "hand.R": (0.2, 0, 0.5)}),
        (34, zero, {"upper_arm.R": (-1.55, 0.1, -0.55), "forearm.R": (-0.55, -0.25, -0.55), "hand.R": (0.2, 0, -0.5)}),
        (50, zero, {"upper_arm.R": (-1.55, 0.1, -0.55), "forearm.R": (-0.55, 0.25, 0.55), "hand.R": (0.2, 0, 0.5)}),
    ]).name)
    clips.append(make_action(armature, "use_computer", [
        (1, zero, {"upper_arm.L": (0.45, 0, 0.2), "forearm.L": (0.7, 0, 0), "upper_arm.R": (0.45, 0, -0.2), "forearm.R": (0.7, 0, 0)}),
        (28, zero, {"hand.L": (0.08, 0.05, 0.15), "hand.R": (0.08, -0.05, -0.15), "head": (0.18, 0, 0)}),
        (56, zero, {"hand.L": (0.08, -0.05, -0.12), "hand.R": (0.08, 0.05, 0.12), "head": (0.14, 0.03, 0)}),
    ]).name)
    return clips


def main():
    enforce_marinette_live_body_policy(ROOT, AVATAR)
    if not AVATAR.exists():
        raise FileNotFoundError(AVATAR)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = MODEL_DIR / f"avatar_before_rig_v5_{stamp}.glb"
    shutil.copy2(AVATAR, backup)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.import_scene.gltf(filepath=str(AVATAR))

    removed = clean_old_helpers()
    armature = make_armature()
    fingers = add_usable_fingers()
    lids = add_lids_and_shape_keys()
    bound = bind_meshes(armature)
    clips = make_actions(armature)

    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 64
    bpy.ops.export_scene.gltf(
        filepath=str(AVATAR),
        export_format="GLB",
        export_yup=True,
        export_animations=True,
        export_nla_strips=True,
        export_force_sampling=True,
        export_skins=True,
        export_morph=True,
    )

    METADATA.write_text(json.dumps({
        "version": "v5",
        "created_utc": stamp,
        "backup": str(backup),
        "removed_old_helper_count": len(removed),
        "new_finger_mesh_count": len(fingers),
        "blink_lids": lids,
        "bound_mesh_count": bound,
        "armature": armature.name,
        "clips": clips,
        "notes": [
            "Functional procedural rig pass with deform bones, hand bones, face shape keys, eyelid blink proxies, and exported locomotion/social clips.",
            "Hair has pigtail and bang bones/proxy meshes for future cloth or spring-bone simulation; full wet-hair physics remains a later runtime pass.",
        ],
    }, indent=2), encoding="utf-8")
    print(f"Rig v5 exported: {AVATAR}")
    print(f"Backup: {backup}")


if __name__ == "__main__":
    main()
