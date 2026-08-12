from __future__ import annotations

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


def material(name: str, color: tuple[float, float, float, float], roughness: float = 0.7):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


SKIN = material("functional_skin_finger_mat", (0.90, 0.64, 0.52, 1), 0.72)
HAIR = material("functional_deep_blue_hair_strand_mat", (0.018, 0.042, 0.105, 1), 0.86)


def world_bounds(obj):
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    mins = Vector((min(v.x for v in corners), min(v.y for v in corners), min(v.z for v in corners)))
    maxs = Vector((max(v.x for v in corners), max(v.y for v in corners), max(v.z for v in corners)))
    return mins, maxs


def add_finger_node(form: str, side_name: str, index: int, base: Vector, length: float, radius: float):
    side_sign = -1 if side_name == "left" else 1
    empty_name = f"{form}_{side_name}_finger_{index + 1:02d}_control"
    mesh_name = f"{form}_{side_name}_finger_{index + 1:02d}"

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=base)
    empty = bpy.context.object
    empty.name = empty_name
    empty.empty_display_size = 0.035

    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=length, location=(base.x, base.y, base.z - length / 2))
    shaft = bpy.context.object
    shaft.name = f"{mesh_name}_shaft"
    shaft.data.materials.append(SKIN)
    shaft.parent = empty
    shaft.matrix_parent_inverse = empty.matrix_world.inverted()

    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=radius * 1.04, location=(base.x, base.y, base.z - length))
    tip = bpy.context.object
    tip.name = f"{mesh_name}_tip"
    tip.data.materials.append(SKIN)
    tip.parent = empty
    tip.matrix_parent_inverse = empty.matrix_world.inverted()

    empty.rotation_euler[1] = side_sign * (index - 2) * 0.015
    if index == 0:
        empty.rotation_euler[1] = side_sign * 0.46
        empty.rotation_euler[2] = side_sign * 0.2
    return empty


def add_hand_fingers(form: str, side_name: str):
    hand = bpy.data.objects.get(f"{form}_{side_name}_hand")
    if not hand:
        return []
    mins, maxs = world_bounds(hand)
    center = (mins + maxs) * 0.5
    width = maxs.x - mins.x
    front_y = mins.y - 0.006
    base_z = mins.z + 0.014
    side_sign = -1 if side_name == "left" else 1
    nodes = []
    for i in range(5):
        x_offset = (-0.38 + i * 0.19) * width
        if i == 0:
            x_offset = side_sign * width * 0.56
        base = Vector((center.x + x_offset, front_y, base_z + (0.01 if i in (1, 2) else 0)))
        length = 0.105 if i == 0 else 0.135 - abs(i - 2) * 0.01
        radius = 0.012 if i else 0.014
        nodes.append(add_finger_node(form, side_name, i, base, length, radius))
    return nodes


def add_hair_curve(name: str, points: list[Vector], bevel: float):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 3
    curve.bevel_depth = bevel
    curve.bevel_resolution = 2
    poly = curve.splines.new("POLY")
    poly.points.add(len(points) - 1)
    for point, co in zip(poly.points, points):
        point.co = (co.x, co.y, co.z, 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(HAIR)
    return obj


def add_hair_detail():
    face = bpy.data.objects.get("shared_face")
    if not face:
        return []
    mins, maxs = world_bounds(face)
    strands = []
    for i in range(12):
        t = i / 11
        x = mins.x + (maxs.x - mins.x) * (0.12 + 0.72 * t)
        start = Vector((x, mins.y - 0.022, maxs.z - 0.05 - 0.05 * math.sin(t * math.pi)))
        mid = Vector((x - 0.035 + 0.07 * t, mins.y - 0.045, maxs.z - 0.16 - 0.045 * math.sin(t * math.pi)))
        end = Vector((x - 0.055 + 0.11 * t, mins.y - 0.038, maxs.z - 0.28 - 0.035 * math.sin(t * math.pi)))
        strands.append(add_hair_curve(f"shared_front_hair_strand_{i + 1:02d}", [start, mid, end], 0.006))
    for side_name in ("left", "right"):
        obj = bpy.data.objects.get(f"shared_{side_name}_pigtail_lower")
        if not obj:
            continue
        pmins, pmaxs = world_bounds(obj)
        side_sign = -1 if side_name == "left" else 1
        for i in range(8):
            t = i / 7
            x = pmins.x + (pmaxs.x - pmins.x) * t
            start = Vector((x, pmins.y - 0.005, pmaxs.z - 0.03))
            mid = Vector((x + side_sign * 0.025, pmins.y - 0.02, (pmins.z + pmaxs.z) * 0.5))
            end = Vector((x + side_sign * 0.035, pmins.y - 0.01, pmins.z + 0.03))
            strands.append(add_hair_curve(f"shared_{side_name}_pigtail_hair_strand_{i + 1:02d}", [start, mid, end], 0.0055))
    return strands


def stash_action(obj, action_name: str, frames: list[tuple[int, tuple[float, float, float]]]):
    obj.animation_data_clear()
    obj.animation_data_create()
    action = bpy.data.actions.new(f"{action_name}_{obj.name}")
    obj.animation_data.action = action
    for frame, rotation in frames:
        bpy.context.scene.frame_set(frame)
        obj.rotation_euler = rotation
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    track = obj.animation_data.nla_tracks.new()
    track.name = action_name
    strip = track.strips.new(action_name, frames[0][0], action)
    strip.name = action_name
    obj.animation_data.action = None


def stash_scale_action(obj, action_name: str, frames: list[tuple[int, tuple[float, float, float]]]):
    obj.animation_data_create()
    action = bpy.data.actions.new(f"{action_name}_{obj.name}")
    obj.animation_data.action = action
    for frame, scale in frames:
        bpy.context.scene.frame_set(frame)
        obj.scale = scale
        obj.keyframe_insert(data_path="scale", frame=frame)
    track = obj.animation_data.nla_tracks.new()
    track.name = action_name
    strip = track.strips.new(action_name, frames[0][0], action)
    strip.name = action_name
    obj.animation_data.action = None


def add_functional_clips(finger_nodes):
    for node in finger_nodes:
        base = tuple(node.rotation_euler)
        curled = (0.72, base[1], base[2])
        open_pose = (0.02, base[1] * 0.55, base[2] * 0.55)
        stash_action(node, "open_hand", [(1, curled), (18, open_pose), (36, open_pose)])
        stash_action(node, "close_hand", [(1, open_pose), (18, curled), (36, curled)])

    mouth = bpy.data.objects.get("shared_mouth")
    if mouth:
        stash_scale_action(mouth, "talking", [(1, (1, 1, 1)), (8, (1.15, 2.8, 1)), (15, (1, 1, 1)), (22, (1.1, 2.0, 1)), (30, (1, 1, 1))])

    for name in ("shared_left_pigtail_lower", "shared_right_pigtail_lower"):
        obj = bpy.data.objects.get(name)
        if obj:
            base = tuple(obj.rotation_euler)
            sway_a = (base[0], base[1], base[2] - 0.055)
            sway_b = (base[0], base[1], base[2] + 0.055)
            stash_action(obj, "stand_idle", [(1, sway_a), (36, sway_b), (72, sway_a)])
            stash_action(obj, "walk", [(1, sway_a), (12, sway_b), (24, sway_a)])
            stash_action(obj, "jog", [(1, sway_a), (8, sway_b), (16, sway_a)])


def add_shape_key_placeholders():
    for name in ("shared_face", "shared_mouth"):
        obj = bpy.data.objects.get(name)
        if obj and obj.type == "MESH":
            if not obj.data.shape_keys:
                obj.shape_key_add(name="Basis")
            for key in ("blink", "smile", "mouth_open", "viseme_AA", "viseme_OO"):
                if key not in obj.data.shape_keys.key_blocks:
                    obj.shape_key_add(name=key)


def main():
    enforce_marinette_live_body_policy(ROOT, AVATAR)
    if not AVATAR.exists():
        raise FileNotFoundError(AVATAR)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = MODEL_DIR / f"avatar_before_functional_v2_{stamp}.glb"
    shutil.copy2(AVATAR, backup)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.import_scene.gltf(filepath=str(AVATAR))

    finger_nodes = []
    for form in ("civilian", "hero"):
        for side in ("left", "right"):
            finger_nodes.extend(add_hand_fingers(form, side))
    add_hair_detail()
    add_shape_key_placeholders()
    add_functional_clips(finger_nodes)

    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 72
    bpy.ops.export_scene.gltf(
        filepath=str(AVATAR),
        export_format="GLB",
        export_animations=True,
        export_nla_strips=True,
        export_force_sampling=True,
    )
    print(f"Backed up original avatar to: {backup}")
    print(f"Exported functional avatar v2 to: {AVATAR}")
    print(f"Added finger controls: {len(finger_nodes)}")


if __name__ == "__main__":
    main()
