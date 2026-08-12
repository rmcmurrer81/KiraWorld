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
METADATA = MODEL_DIR / "avatar_functional_rig_v4.json"


def mat(name: str, color: tuple[float, float, float, float], roughness: float = 0.55, metallic: float = 0.0):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return material


SKIN = mat("v4_warm_skin_hand_detail", (0.93, 0.68, 0.57, 1), 0.66)
NAIL = mat("v4_natural_fingernails", (0.99, 0.78, 0.70, 1), 0.4)
HAIR = mat("v4_midnight_blue_hair_fibers", (0.012, 0.022, 0.075, 1), 0.32)
HAIR_HIGHLIGHT = mat("v4_blue_hair_anisotropic_highlights", (0.07, 0.13, 0.34, 1), 0.24)
EYE_GLOSS = mat("v4_eye_catchlight", (0.9, 0.98, 1.0, 0.82), 0.16)


def bounds(obj):
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector((min(v.x for v in corners), min(v.y for v in corners), min(v.z for v in corners))),
        Vector((max(v.x for v in corners), max(v.y for v in corners), max(v.z for v in corners))),
    )


def curve(name: str, points: list[Vector], material, bevel: float):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 5
    data.bevel_depth = bevel
    data.bevel_resolution = 2
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, co in zip(spline.bezier_points, points):
        point.co = co
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def add_finger(side: str, idx: int, base: Vector, direction: Vector, length: float, radius: float):
    empty = bpy.data.objects.new(f"v4_{side}_finger_{idx}_curl_control", None)
    bpy.context.collection.objects.link(empty)
    empty.empty_display_type = "SPHERE"
    empty.empty_display_size = 0.035
    empty.location = base

    mid = base + direction.normalized() * (length * 0.5)
    end = base + direction.normalized() * length
    bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=radius, depth=length, location=mid)
    shaft = bpy.context.object
    shaft.name = f"v4_{side}_finger_{idx}_phalange_mesh"
    shaft.data.materials.append(SKIN)
    shaft.parent = empty
    shaft.rotation_euler[1] = math.pi / 2

    bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=8, radius=radius * 1.12, location=end)
    tip = bpy.context.object
    tip.name = f"v4_{side}_finger_{idx}_rounded_tip"
    tip.scale = (0.75, 1.0, 0.65)
    tip.data.materials.append(SKIN)
    tip.parent = empty

    bpy.ops.mesh.primitive_cube_add(size=1, location=end + Vector((0, -0.002, radius * 0.72)))
    nail = bpy.context.object
    nail.name = f"v4_{side}_finger_{idx}_nail"
    nail.scale = (radius * 0.52, 0.0025, radius * 0.36)
    nail.data.materials.append(NAIL)
    nail.parent = empty
    return empty


def add_hand_detail_for_object(form: str, side: str):
    hand = bpy.data.objects.get(f"{form}_{side}_hand")
    if not hand:
        return []
    bmin, bmax = bounds(hand)
    center = (bmin + bmax) * 0.5
    sign = -1 if side == "left" else 1
    controls = []

    for i, offset in enumerate((-0.045, -0.018, 0.010, 0.037), start=1):
        base = Vector((center.x + sign * (0.018 + abs(offset) * 0.14), bmin.y - 0.015, center.z + offset))
        controls.append(add_finger(side, i, base, Vector((sign * 0.028, -0.075, 0.0)), 0.105 - abs(offset) * 0.35, 0.010))
    thumb_base = Vector((center.x + sign * 0.055, center.y - 0.005, center.z - 0.045))
    controls.append(add_finger(side, 0, thumb_base, Vector((sign * 0.060, -0.040, -0.015)), 0.080, 0.012))
    return controls


def add_visible_hair_layers():
    face = bpy.data.objects.get("shared_face")
    if not face:
        return []
    bmin, bmax = bounds(face)
    strands = []
    width = bmax.x - bmin.x

    for i in range(44):
        t = i / 43
        x = bmin.x + width * (0.05 + 0.9 * t)
        sweep = (t - 0.5)
        start = Vector((x, bmin.y - 0.026, bmax.z - 0.025 - 0.018 * math.cos(t * math.pi)))
        mid = Vector((x - 0.075 * sweep, bmin.y - 0.055, bmax.z - 0.135 - 0.045 * math.sin(t * math.pi)))
        end = Vector((x - 0.16 * sweep, bmin.y - 0.048, bmax.z - 0.315 - 0.06 * math.sin(t * math.pi)))
        strands.append(curve(f"v4_weighted_front_bang_{i:02d}", [start, mid, end], HAIR_HIGHLIGHT if i % 6 == 0 else HAIR, 0.0048))

    for side in ("left", "right"):
        pigtail = bpy.data.objects.get(f"shared_{side}_pigtail_lower") or bpy.data.objects.get(f"v3_pigtail_mass_{'l' if side == 'left' else 'r'}")
        if not pigtail:
            continue
        pmin, pmax = bounds(pigtail)
        sign = -1 if side == "left" else 1
        for i in range(32):
            t = i / 31
            z = pmin.z + (pmax.z - pmin.z) * t
            x = pmin.x + (pmax.x - pmin.x) * (0.35 + 0.28 * math.sin(t * math.pi))
            start = Vector((x, pmin.y - 0.010, z))
            mid = Vector((x + sign * 0.050, pmin.y - 0.032, z - 0.020))
            end = Vector((x + sign * 0.095, pmin.y - 0.012, z - 0.010))
            strands.append(curve(f"v4_{side}_pigtail_outer_strand_{i:02d}", [start, mid, end], HAIR_HIGHLIGHT if i % 7 == 0 else HAIR, 0.0052))
    return strands


def add_eye_catchlights():
    created = 0
    for name in ("shared_left_iris", "shared_right_iris"):
        eye = bpy.data.objects.get(name)
        if not eye:
            continue
        bmin, bmax = bounds(eye)
        loc = Vector((bmin.x + (bmax.x - bmin.x) * 0.35, bmin.y - 0.004, bmax.z - (bmax.z - bmin.z) * 0.28))
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.012, location=loc)
        light = bpy.context.object
        light.name = f"v4_{name}_catchlight"
        light.scale = (0.65, 0.22, 0.65)
        light.data.materials.append(EYE_GLOSS)
        created += 1
    return created


def ensure_shape_keys():
    keys = {}
    for name in ("shared_face", "shared_mouth"):
        obj = bpy.data.objects.get(name)
        if not obj or obj.type != "MESH":
            continue
        if not obj.data.shape_keys:
            obj.shape_key_add(name="Basis")
        added = []
        for key in ("blink_left", "blink_right", "smile_soft", "mouth_open", "viseme_AA", "viseme_EE", "viseme_OO", "viseme_MBP"):
            if key not in obj.data.shape_keys.key_blocks:
                obj.shape_key_add(name=key)
                added.append(key)
        keys[name] = added
    return keys


def add_nla_proxy_actions(controls):
    for control in controls:
        for action_name, open_rot, closed_rot in (
            ("open_hand", (0.02, 0, 0), (0.70, 0, 0)),
            ("close_hand", (0.70, 0, 0), (0.02, 0, 0)),
        ):
            action = bpy.data.actions.new(f"{action_name}_{control.name}")
            control.animation_data_clear()
            control.animation_data_create()
            control.animation_data.action = action
            for frame, rot in ((1, closed_rot), (18, open_rot), (36, open_rot)):
                if action_name == "close_hand":
                    rot = open_rot if frame == 1 else closed_rot
                bpy.context.scene.frame_set(frame)
                control.rotation_euler = rot
                control.keyframe_insert(data_path="rotation_euler", frame=frame)
            track = control.animation_data.nla_tracks.new()
            track.name = action_name
            track.strips.new(action_name, 1, action)
            control.animation_data.action = None


def main():
    enforce_marinette_live_body_policy(ROOT, AVATAR)
    if not AVATAR.exists():
        raise FileNotFoundError(AVATAR)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = MODEL_DIR / f"avatar_before_rig_mesh_v4_{stamp}.glb"
    shutil.copy2(AVATAR, backup)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.import_scene.gltf(filepath=str(AVATAR))

    controls = []
    for form in ("civilian", "hero"):
        for side in ("left", "right"):
            controls.extend(add_hand_detail_for_object(form, side))
    strands = add_visible_hair_layers()
    catchlights = add_eye_catchlights()
    shape_keys = ensure_shape_keys()
    add_nla_proxy_actions(controls)

    bpy.context.scene["kira_avatar_functional_rig_v4"] = (
        "Mesh/control pass for visible fingers, hair layers, eye catchlights, named facial/lip-sync shape keys, "
        "and NLA hand-open/hand-close proxy actions. This is not final photoreal grooming or full body mocap."
    )
    bpy.ops.export_scene.gltf(
        filepath=str(AVATAR),
        export_format="GLB",
        export_animations=True,
        export_nla_strips=True,
        export_force_sampling=True,
    )
    METADATA.write_text(json.dumps({
        "schema_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "avatar_glb": str(AVATAR.relative_to(ROOT)).replace("\\", "/"),
        "backup_glb": str(backup.relative_to(ROOT)).replace("\\", "/"),
        "target_height_m": 1.57,
        "added_finger_controls": len(controls),
        "added_hair_strands": len(strands),
        "added_eye_catchlights": catchlights,
        "shape_key_hooks": shape_keys,
        "actions": ["stand_idle", "walk", "jog", "sit_proxy_runtime", "open_hand", "close_hand", "talking"],
        "limits": "functional mesh/blendshape hook pass; final realistic hair simulation and production facial rig still require a real sculpt/groom pipeline",
    }, indent=2), encoding="utf-8")
    print(f"Updated {AVATAR}")
    print(f"Backup {backup}")
    print(f"Wrote {METADATA}")
    print(f"Finger controls: {len(controls)} | hair strands: {len(strands)} | catchlights: {catchlights}")


if __name__ == "__main__":
    main()
