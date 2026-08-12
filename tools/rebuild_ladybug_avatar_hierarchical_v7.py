from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Euler, Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.avatar_body_policy_gate import enforce_marinette_procedural_body_policy  # noqa: E402

MODEL_DIR = ROOT / "Avatar" / "models" / "temp_ai" / "ladybug_marinette_expanded_smoke"
AVATAR = MODEL_DIR / "avatar.glb"
METADATA = MODEL_DIR / "avatar_functional_rig_v7.json"


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def make_mat(name, color, roughness=0.55, metallic=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = color
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Alpha"].default_value = alpha
    if alpha < 1:
        mat.blend_method = "BLEND"
        mat.use_screen_refraction = True
    return mat


def setup_materials():
    return {
        "skin": make_mat("v7_warm_skin", (0.91, 0.68, 0.59, 1), 0.48),
        "blush": make_mat("v7_soft_blush", (0.95, 0.42, 0.55, 1), 0.55),
        "hair": make_mat("v7_blue_black_hair", (0.008, 0.02, 0.085, 1), 0.27, 0.04),
        "hair_hi": make_mat("v7_hair_blue_highlight", (0.065, 0.095, 0.24, 1), 0.22, 0.03),
        "eye": make_mat("v7_eye_white", (0.93, 0.98, 1.0, 1), 0.34),
        "iris": make_mat("v7_clear_blue_iris", (0.02, 0.62, 0.88, 1), 0.25),
        "pupil": make_mat("v7_pupil", (0.004, 0.006, 0.008, 1), 0.25),
        "jacket": make_mat("v7_charcoal_jacket", (0.035, 0.043, 0.058, 1), 0.72),
        "shirt": make_mat("v7_white_floral_shirt", (0.94, 0.93, 0.88, 1), 0.66),
        "pants": make_mat("v7_pink_pants", (0.82, 0.28, 0.44, 1), 0.68),
        "shoe": make_mat("v7_black_flats", (0.008, 0.009, 0.012, 1), 0.62),
        "gold": make_mat("v7_gold_earrings", (0.93, 0.62, 0.12, 1), 0.28, 0.35),
        "red": make_mat("v7_ladybug_red", (0.78, 0.02, 0.06, 1), 0.52),
        "black": make_mat("v7_ladybug_black", (0.005, 0.005, 0.006, 1), 0.45),
        "sleep": make_mat("v7_sleepwear_lavender", (0.62, 0.48, 0.82, 1), 0.75),
        "swim": make_mat("v7_swimwear_blue", (0.08, 0.25, 0.58, 1), 0.48),
    }


def empty(name, loc, parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.08
    obj.location = loc
    obj.rotation_mode = "XYZ"
    if parent:
        keep_parent(obj, parent)
    return obj


def keep_parent(obj, parent):
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world


def add_sphere(name, loc, scale, mat, parent=None, segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    obj.rotation_mode = "XYZ"
    if parent:
        keep_parent(obj, parent)
    return obj


def add_cube(name, loc, scale, mat, parent=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    obj.rotation_mode = "XYZ"
    if parent:
        keep_parent(obj, parent)
    return obj


def add_cyl(name, loc, radius, depth, mat, parent=None, rot=(0, 0, 0), vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    obj.rotation_mode = "XYZ"
    if parent:
        keep_parent(obj, parent)
    return obj


def add_hair_strand(name, loc, length, parent, mat, side=1, tilt=0.0):
    return add_cyl(
        name,
        loc,
        0.006,
        length,
        mat,
        parent,
        rot=(0.25 + tilt, side * 0.12, side * 0.18),
        vertices=8,
    )


def make_pivots():
    p = {}
    p["root"] = empty("v7_marinette_root", (0, 0, 0))
    p["hips"] = empty("v7_hips", (0, 0, 0.98), p["root"])
    p["torso"] = empty("v7_torso", (0, 0, 1.37), p["hips"])
    p["head"] = empty("v7_head", (0, 0.05, 2.12), p["torso"])
    for side, sx in (("L", -1), ("R", 1)):
        p[f"upper_arm.{side}"] = empty(f"v7_upper_arm.{side}", (0.22 * sx, 0.02, 1.72), p["torso"])
        p[f"forearm.{side}"] = empty(f"v7_forearm.{side}", (0.38 * sx, 0.03, 1.45), p[f"upper_arm.{side}"])
        p[f"hand.{side}"] = empty(f"v7_hand.{side}", (0.39 * sx, 0.06, 1.18), p[f"forearm.{side}"])
        p[f"thigh.{side}"] = empty(f"v7_thigh.{side}", (0.10 * sx, 0.0, 0.88), p["hips"])
        p[f"shin.{side}"] = empty(f"v7_shin.{side}", (0.12 * sx, 0.02, 0.50), p[f"thigh.{side}"])
        p[f"foot.{side}"] = empty(f"v7_foot.{side}", (0.12 * sx, 0.10, 0.12), p[f"shin.{side}"])
        p[f"pigtail.{side}"] = empty(f"v7_pigtail.{side}", (0.28 * sx, 0.0, 2.16), p["head"])
        p[f"bangs.{side}"] = empty(f"v7_bangs.{side}", (0.06 * sx, 0.16, 2.34), p["head"])
    return p


def build_avatar(p, m):
    add_sphere("shared_modest_body_base", (0, 0, 1.23), (0.20, 0.13, 0.25), m["shirt"], p["hips"], 32, 16)
    add_sphere("civilian_shirt_torso", (0, 0.02, 1.48), (0.24, 0.15, 0.36), m["shirt"], p["torso"], 32, 16)
    add_cube("civilian_jacket_left_panel", (-0.08, 0.175, 1.50), (0.052, 0.025, 0.33), m["jacket"], p["torso"])
    add_cube("civilian_jacket_right_panel", (0.08, 0.175, 1.50), (0.052, 0.025, 0.33), m["jacket"], p["torso"])
    add_cube("civilian_jacket_back", (0, -0.11, 1.50), (0.23, 0.025, 0.34), m["jacket"], p["torso"])
    add_sphere("civilian_floral_shirt_mark", (0.045, 0.185, 1.58), (0.035, 0.006, 0.028), m["blush"], p["torso"], 16, 8)

    add_sphere("shared_neck", (0, 0.02, 1.86), (0.055, 0.045, 0.10), m["skin"], p["torso"], 20, 10)
    add_sphere("shared_head_marinette_soft", (0, 0.08, 2.24), (0.215, 0.185, 0.265), m["skin"], p["head"], 48, 24)
    add_sphere("shared_chin_softener", (0, 0.11, 2.04), (0.15, 0.11, 0.08), m["skin"], p["head"], 24, 12)
    add_sphere("shared_nose", (0, 0.255, 2.23), (0.022, 0.018, 0.034), m["skin"], p["head"], 16, 8)
    mouth = add_cube("face_mouth_lipsync", (0, 0.268, 2.13), (0.085, 0.007, 0.010), m["blush"], p["head"])
    upper_lip = add_cube("face_upper_lip", (0, 0.272, 2.145), (0.072, 0.006, 0.006), m["blush"], p["head"])
    lower_lip = add_cube("face_lower_lip", (0, 0.273, 2.116), (0.065, 0.006, 0.006), m["blush"], p["head"])

    blink_targets = []
    for side, sx in (("L", -1), ("R", 1)):
        add_sphere(f"face_eye_white.{side}", (0.075 * sx, 0.248, 2.30), (0.050, 0.018, 0.036), m["eye"], p["head"], 24, 12)
        add_sphere(f"face_iris_blue.{side}", (0.075 * sx, 0.263, 2.30), (0.024, 0.006, 0.026), m["iris"], p["head"], 18, 8)
        add_sphere(f"face_pupil.{side}", (0.075 * sx, 0.268, 2.30), (0.010, 0.003, 0.012), m["pupil"], p["head"], 12, 6)
        lid = add_cube(f"face_blink_lid.{side}", (0.075 * sx, 0.272, 2.335), (0.058, 0.006, 0.007), m["skin"], p["head"])
        blink_targets.append(lid)
        add_cube(f"face_brow.{side}", (0.075 * sx, 0.264, 2.375), (0.055, 0.005, 0.006), m["hair"], p["head"], rot=(0, 0, 0.12 * -sx))
        add_sphere(f"face_blush.{side}", (0.135 * sx, 0.252, 2.20), (0.044, 0.008, 0.018), m["blush"], p["head"], 16, 8)
        add_sphere(f"shared_gold_earring.{side}", (0.225 * sx, 0.025, 2.20), (0.018, 0.010, 0.030), m["gold"], p["head"], 16, 8)

    add_sphere("hair_cap_full_blueblack", (0, -0.005, 2.42), (0.235, 0.18, 0.15), m["hair"], p["head"], 40, 16)
    add_sphere("hair_side_swept_bangs_mass", (-0.055, 0.160, 2.40), (0.195, 0.045, 0.075), m["hair"], p["head"], 32, 10)
    for i, x in enumerate((-0.165, -0.125, -0.085, -0.045, -0.005, 0.04), 1):
        add_hair_strand(f"hair_soft_bang_strand_{i:02d}", (x, 0.205, 2.235 - i * 0.006), 0.23, p["bangs.L"], m["hair_hi"], -1, i * 0.01)
    for side, sx in (("L", -1), ("R", 1)):
        add_sphere(f"hair_low_pigtail_volume.{side}", (0.38 * sx, -0.01, 2.05), (0.125, 0.105, 0.095), m["hair"], p[f"pigtail.{side}"], 32, 12)
        add_sphere(f"hair_pigtail_tie_red.{side}", (0.27 * sx, 0.02, 2.075), (0.025, 0.018, 0.018), m["red"], p[f"pigtail.{side}"], 16, 8)
        add_hair_strand(f"hair_side_lock.{side}", (0.19 * sx, 0.16, 2.12), 0.28, p["head"], m["hair_hi"], sx, 0.05)
        for i in range(5):
            add_hair_strand(
                f"hair_pigtail_fabric_strand_{i:02d}.{side}",
                (sx * (0.34 + i * 0.018), 0.070, 1.98 - i * 0.010),
                0.18,
                p[f"pigtail.{side}"],
                m["hair_hi"],
                sx,
                i * 0.02,
            )

    for side, sx in (("L", -1), ("R", 1)):
        add_cyl(f"civilian_upper_arm_sleeve.{side}", (0.31 * sx, 0.015, 1.59), 0.043, 0.32, m["jacket"], p[f"upper_arm.{side}"], rot=(0.30, 0, 0.55 * sx))
        add_cyl(f"shared_forearm_skin.{side}", (0.39 * sx, 0.035, 1.31), 0.034, 0.29, m["skin"], p[f"forearm.{side}"], rot=(0.25, 0, 0.12 * sx))
        add_sphere(f"shared_elbow_round.{side}", (0.38 * sx, 0.03, 1.45), (0.040, 0.035, 0.040), m["skin"], p[f"forearm.{side}"], 16, 8)
        add_sphere(f"shared_hand_palm.{side}", (0.40 * sx, 0.075, 1.13), (0.040, 0.026, 0.050), m["skin"], p[f"hand.{side}"], 18, 8)
        for i, finger in enumerate(("thumb", "index", "middle", "ring", "pinky")):
            zoff = (i - 2) * 0.020
            length = 0.075 if finger in ("thumb", "pinky") else 0.092
            add_cyl(
                f"shared_finger_{finger}.{side}",
                (sx * (0.425 + i * 0.006), 0.128, 1.13 + zoff),
                0.006,
                length,
                m["skin"],
                p[f"hand.{side}"],
                rot=(math.pi / 2, 0, math.pi / 2),
                vertices=8,
            )
        add_cyl(f"civilian_thigh_pants.{side}", (0.11 * sx, 0.0, 0.70), 0.050, 0.38, m["pants"], p[f"thigh.{side}"], rot=(0.04, 0, 0.04 * sx))
        add_cyl(f"civilian_shin_pants.{side}", (0.13 * sx, 0.02, 0.33), 0.043, 0.36, m["pants"], p[f"shin.{side}"], rot=(0.04, 0, -0.02 * sx))
        add_sphere(f"civilian_knee.{side}", (0.12 * sx, 0.02, 0.50), (0.045, 0.038, 0.045), m["pants"], p[f"shin.{side}"], 16, 8)
        add_sphere(f"shared_ankle.{side}", (0.12 * sx, 0.045, 0.14), (0.028, 0.024, 0.044), m["skin"], p[f"foot.{side}"], 12, 6)
        add_sphere(f"civilian_black_flat_shoe.{side}", (0.12 * sx, 0.16, 0.055), (0.062, 0.115, 0.030), m["shoe"], p[f"foot.{side}"], 16, 8)

    add_cube("sleepwear_lavender_top_hidden", (0, 0.21, 1.48), (0.25, 0.018, 0.32), m["sleep"], p["torso"])
    add_cube("swimwear_modest_blue_hidden", (0, 0.215, 1.32), (0.235, 0.020, 0.42), m["swim"], p["torso"])
    add_cube("hero_ladybug_suit_top_hidden", (0, 0.218, 1.45), (0.25, 0.022, 0.40), m["red"], p["torso"])
    add_cube("hero_ladybug_mask_hidden", (0, 0.277, 2.30), (0.18, 0.008, 0.045), m["red"], p["head"])
    return {"blink": blink_targets, "mouth": [mouth, upper_lip, lower_lip]}


def set_key(obj, frame, loc=None, rot=None, scale=None):
    if loc is not None:
        obj.location = loc
        obj.keyframe_insert("location", frame=frame)
    if rot is not None:
        obj.rotation_euler = Euler(rot, "XYZ")
        obj.keyframe_insert("rotation_euler", frame=frame)
    if scale is not None:
        obj.scale = scale
        obj.keyframe_insert("scale", frame=frame)


def stash_clip(obj, clip_name):
    if not obj.animation_data or not obj.animation_data.action:
        return
    action = obj.animation_data.action
    action.name = f"{obj.name}_{clip_name}"
    track = obj.animation_data.nla_tracks.new()
    track.name = clip_name
    strip = track.strips.new(clip_name, int(action.frame_range[0]), action)
    strip.name = clip_name
    obj.animation_data.action = None


def clip(obj, name, keys):
    obj.animation_data_create()
    obj.animation_data.action = bpy.data.actions.new(f"{obj.name}_{name}_action")
    for frame, data in keys:
        set_key(obj, frame, data.get("loc"), data.get("rot"), data.get("scale"))
    stash_clip(obj, name)


def make_animation_clips(p, face):
    clip(p["root"], "idle", [(1, {"loc": (0, 0, 0)}), (30, {"loc": (0, 0, 0.018)}), (60, {"loc": (0, 0, 0)})])
    clip(p["torso"], "idle", [(1, {"rot": (0, 0, 0)}), (30, {"rot": (0.015, 0, 0.012)}), (60, {"rot": (0, 0, 0)})])
    clip(p["head"], "idle", [(1, {"rot": (0, 0, 0)}), (45, {"rot": (0.02, 0.03, -0.02)}), (90, {"rot": (0, -0.03, 0.02)}), (120, {"rot": (0, 0, 0)})])
    for side, sx in (("L", -1), ("R", 1)):
        clip(p[f"pigtail.{side}"], "idle", [(1, {"rot": (0, 0, 0)}), (45, {"rot": (0.035, sx * 0.10, sx * 0.05)}), (90, {"rot": (0, sx * -0.08, sx * -0.04)}), (120, {"rot": (0, 0, 0)})])

    walk_keys = [(1, 0), (10, 1), (20, 0), (30, -1), (40, 0)]
    for side, sx, phase in (("L", -1, 1), ("R", 1, -1)):
        clip(p[f"thigh.{side}"], "walk", [(f, {"rot": (0.42 * phase * v, 0, 0.03 * sx)}) for f, v in walk_keys])
        clip(p[f"shin.{side}"], "walk", [(f, {"rot": (-0.48 * max(0, phase * v), 0, 0)}) for f, v in walk_keys])
        clip(p[f"foot.{side}"], "walk", [(1, {"rot": (0, 0, 0)}), (10, {"rot": (-0.22 * phase, 0, 0)}), (20, {"rot": (0, 0, 0)}), (30, {"rot": (0.18 * phase, 0, 0)}), (40, {"rot": (0, 0, 0)})])
        clip(p[f"upper_arm.{side}"], "walk", [(f, {"rot": (-0.28 * phase * v, 0, sx * 0.05)}) for f, v in walk_keys])
        clip(p[f"forearm.{side}"], "walk", [(f, {"rot": (-0.10, 0, 0)}) for f, _ in walk_keys])
        clip(p[f"pigtail.{side}"], "walk", [(1, {"rot": (0, 0, 0)}), (10, {"rot": (0.08, sx * -0.12, sx * 0.05)}), (20, {"rot": (0, 0, 0)}), (30, {"rot": (0.08, sx * 0.12, sx * -0.05)}), (40, {"rot": (0, 0, 0)})])
    clip(p["torso"], "walk", [(1, {"rot": (0, 0, 0)}), (10, {"rot": (0.025, 0, -0.025)}), (20, {"rot": (0, 0, 0)}), (30, {"rot": (0.025, 0, 0.025)}), (40, {"rot": (0, 0, 0)})])

    clip(p["head"], "look_around", [(1, {"rot": (0, 0, 0)}), (35, {"rot": (0.02, -0.32, 0)}), (70, {"rot": (0.01, 0.32, 0)}), (105, {"rot": (0, 0, 0)})])
    clip(p["head"], "talking", [(1, {"rot": (0, 0, 0)}), (18, {"rot": (0.025, -0.04, 0)}), (36, {"rot": (-0.01, 0.04, 0)}), (54, {"rot": (0, 0, 0)})])
    for part in face["mouth"]:
        clip(part, "talking", [(1, {"scale": part.scale.copy()}), (10, {"scale": (part.scale.x * 1.12, part.scale.y, part.scale.z * 0.55)}), (20, {"scale": part.scale.copy()}), (32, {"scale": (part.scale.x * 0.82, part.scale.y, part.scale.z * 1.45)}), (44, {"scale": part.scale.copy()})])
        clip(part, "viseme_talking", [(1, {"scale": part.scale.copy()}), (8, {"scale": (part.scale.x, part.scale.y, part.scale.z * 0.45)}), (16, {"scale": (part.scale.x * 1.2, part.scale.y, part.scale.z)}), (24, {"scale": (part.scale.x * 0.75, part.scale.y, part.scale.z * 1.35)}), (32, {"scale": part.scale.copy()})])
    for lid in face["blink"]:
        base_loc = lid.location.copy()
        clip(lid, "blink", [(1, {"loc": base_loc}), (5, {"loc": (base_loc.x, base_loc.y, base_loc.z - 0.05)}), (9, {"loc": base_loc}), (60, {"loc": base_loc})])

    clip(p["upper_arm.R"], "wave", [(1, {"rot": (0, 0, 0.1)}), (12, {"rot": (-1.1, 0, -0.95)}), (25, {"rot": (-1.0, 0.3, -0.85)}), (38, {"rot": (-1.0, -0.3, -0.9)}), (50, {"rot": (-1.1, 0.2, -0.85)}), (70, {"rot": (0, 0, 0.1)})])
    clip(p["forearm.R"], "wave", [(1, {"rot": (-0.05, 0, 0)}), (12, {"rot": (-0.95, 0, 0)}), (50, {"rot": (-0.95, 0, 0)}), (70, {"rot": (-0.05, 0, 0)})])
    clip(p["hand.R"], "wave", [(1, {"rot": (0, 0, 0)}), (20, {"rot": (0, 0.45, 0.35)}), (35, {"rot": (0, -0.45, -0.25)}), (50, {"rot": (0, 0.35, 0.30)}), (70, {"rot": (0, 0, 0)})])

    clip(p["torso"], "sit", [(1, {"rot": (0, 0, 0)}), (25, {"rot": (-0.12, 0, 0)}), (60, {"rot": (-0.12, 0, 0)})])
    for side in ("L", "R"):
        clip(p[f"thigh.{side}"], "sit", [(1, {"rot": (0, 0, 0)}), (25, {"rot": (-1.1, 0, 0)}), (60, {"rot": (-1.1, 0, 0)})])
        clip(p[f"shin.{side}"], "sit", [(1, {"rot": (0, 0, 0)}), (25, {"rot": (1.28, 0, 0)}), (60, {"rot": (1.28, 0, 0)})])
    clip(p["upper_arm.R"], "door_open_reach", [(1, {"rot": (0, 0, 0)}), (20, {"rot": (-0.55, 0.05, -0.95)}), (45, {"rot": (-0.6, 0.12, -0.95)}), (70, {"rot": (0, 0, 0)})])
    clip(p["forearm.R"], "door_open_reach", [(1, {"rot": (0, 0, 0)}), (20, {"rot": (-0.75, 0, 0)}), (45, {"rot": (-0.85, 0, 0)}), (70, {"rot": (0, 0, 0)})])
    clip(p["upper_arm.L"], "use_computer", [(1, {"rot": (-0.30, 0, 0.35)}), (25, {"rot": (-0.55, 0, 0.28)}), (50, {"rot": (-0.35, 0, 0.35)})])
    clip(p["upper_arm.R"], "use_computer", [(1, {"rot": (-0.30, 0, -0.35)}), (25, {"rot": (-0.55, 0, -0.28)}), (50, {"rot": (-0.35, 0, -0.35)})])
    clip(p["head"], "use_computer", [(1, {"rot": (0.08, 0, 0)}), (50, {"rot": (0.08, 0.05, 0)}), (100, {"rot": (0.08, -0.05, 0)})])
    clip(p["torso"], "pick_up", [(1, {"rot": (0, 0, 0)}), (20, {"rot": (0.50, 0, 0)}), (45, {"rot": (0.50, 0, 0)}), (70, {"rot": (0, 0, 0)})])
    clip(p["upper_arm.R"], "pick_up", [(1, {"rot": (0, 0, 0)}), (20, {"rot": (-0.9, 0, -0.28)}), (45, {"rot": (-0.9, 0, -0.28)}), (70, {"rot": (0, 0, 0)})])
    clip(p["torso"], "change_clothes", [(1, {"rot": (0, 0, 0)}), (24, {"rot": (-0.06, 0.12, 0)}), (48, {"rot": (-0.06, -0.12, 0)}), (72, {"rot": (0, 0, 0)})])
    clip(p["upper_arm.L"], "change_clothes", [(1, {"rot": (0, 0, 0)}), (24, {"rot": (-1.0, 0, 0.55)}), (48, {"rot": (-0.35, 0, 0.25)}), (72, {"rot": (0, 0, 0)})])
    clip(p["upper_arm.R"], "change_clothes", [(1, {"rot": (0, 0, 0)}), (24, {"rot": (-0.35, 0, -0.25)}), (48, {"rot": (-1.0, 0, -0.55)}), (72, {"rot": (0, 0, 0)})])
    for side in ("L", "R"):
        clip(p[f"thigh.{side}"], "swim_idle", [(1, {"rot": (0.18, 0, 0)}), (25, {"rot": (-0.18, 0, 0)}), (50, {"rot": (0.18, 0, 0)})])
        clip(p[f"shin.{side}"], "swim_idle", [(1, {"rot": (-0.28, 0, 0)}), (25, {"rot": (0.18, 0, 0)}), (50, {"rot": (-0.28, 0, 0)})])


def hide_non_default_layers():
    for obj in bpy.data.objects:
        name = obj.name.lower()
        if name.startswith(("hero_", "sleepwear_", "swimwear_")):
            obj.hide_viewport = True
            obj.hide_render = True


def export(body_policy_gate: dict):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(AVATAR),
        export_format="GLB",
        export_animations=True,
        export_nla_strips=True,
        export_apply=False,
    )
    METADATA.write_text(
        json.dumps(
            {
                "version": "v7_hierarchical_stability_pass",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": str(AVATAR),
                "body_policy_validation": body_policy_gate,
                "approach": "Object-hierarchy animation rig to stop detached skinned primitive failures while keeping a migration path to a true deform rig.",
                "clips": [
                    "idle",
                    "walk",
                    "talking",
                    "viseme_talking",
                    "blink",
                    "look_around",
                    "wave",
                    "sit",
                    "door_open_reach",
                    "use_computer",
                    "pick_up",
                    "change_clothes",
                    "swim_idle",
                ],
                "body_notes": [
                    "Civilian Marinette default restored: blue-black side-swept hair, low pigtails, blue eyes, white floral shirt, charcoal jacket, pink pants, black flats.",
                    "Hands include stable palms and five fingers per hand.",
                    "Hair uses attached pigtail and strand proxies with idle/walk sway clips.",
                    "Non-adult modest base remains covered under clothing layers.",
                ],
                "next": [
                    "Replace primitive hierarchy with deformable production mesh once the motion/pathing loop is stable.",
                    "Add motion-learning recorder that saves successful clips from runtime interactions.",
                    "Upgrade hair and fabric proxies to physics-driven cloth in runtime.",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main():
    body_policy_gate = enforce_marinette_procedural_body_policy(ROOT)
    clear_scene()
    mats = setup_materials()
    pivots = make_pivots()
    face = build_avatar(pivots, mats)
    make_animation_clips(pivots, face)
    hide_non_default_layers()
    export(body_policy_gate)


if __name__ == "__main__":
    main()
