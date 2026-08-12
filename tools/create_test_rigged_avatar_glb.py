import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


CANDIDATE_ID = "jessica_hale_robotics_engineer_20260611_041314"
DISPLAY_NAME = "Jessica Hale"
ROLE_TITLE = "Robotics Engineer"
OUT_DIR = Path("Avatar/models/temp_ai") / CANDIDATE_ID
OUT_GLB = OUT_DIR / "avatar_test_rig_v1.glb"
OUT_META = OUT_DIR / "avatar_test_rig_v1_manifest.json"


def mat(name, color, roughness=0.65):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    return material


def add_uv_sphere(name, location, scale, material, segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    return obj


def add_cube(name, location, scale, material):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    return obj


def add_cylinder(name, location, radius, depth, material, vertices=24, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def set_origin_empty_parent(obj, parent, bone_name=None):
    obj.parent = parent
    if bone_name:
        obj.parent_type = "BONE"
        obj.parent_bone = bone_name


def create_armature():
    bpy.ops.object.armature_add(location=(0, 0, 0))
    arm = bpy.context.object
    arm.name = "Jessica_Hale_TestRig_Armature"
    arm.data.name = "Jessica_Hale_TestRig_Skeleton"
    bpy.ops.object.mode_set(mode="EDIT")
    arm.data.edit_bones.remove(arm.data.edit_bones[0])

    def bone(name, head, tail, parent=None):
        b = arm.data.edit_bones.new(name)
        b.head = head
        b.tail = tail
        if parent:
            b.parent = arm.data.edit_bones[parent]
            b.use_connect = False
        return b

    bone("hips", (0, 0, 0.9), (0, 0, 1.05))
    bone("spine", (0, 0, 1.03), (0, 0, 1.33), "hips")
    bone("neck", (0, 0, 1.32), (0, 0, 1.43), "spine")
    bone("head", (0, 0, 1.42), (0, 0, 1.62), "neck")

    for side, x in [("L", -1), ("R", 1)]:
        bone(f"{side}_upper_arm", (0.17 * x, 0, 1.30), (0.47 * x, 0, 1.13), "spine")
        bone(f"{side}_lower_arm", (0.47 * x, 0, 1.13), (0.61 * x, 0, 0.92), f"{side}_upper_arm")
        bone(f"{side}_hand", (0.61 * x, 0, 0.92), (0.69 * x, 0, 0.87), f"{side}_lower_arm")
        for i, finger in enumerate(["thumb", "index", "middle", "ring", "pinky"]):
            y = (i - 2) * 0.018
            spread = -0.04 if finger == "thumb" else 0.0
            bone(f"{side}_{finger}_01", (0.68 * x, y + spread, 0.88), (0.75 * x, y + spread, 0.86), f"{side}_hand")
            bone(f"{side}_{finger}_02", (0.75 * x, y + spread, 0.86), (0.80 * x, y + spread, 0.84), f"{side}_{finger}_01")

        bone(f"{side}_upper_leg", (0.09 * x, 0, 0.90), (0.14 * x, 0, 0.50), "hips")
        bone(f"{side}_lower_leg", (0.14 * x, 0, 0.50), (0.12 * x, 0, 0.12), f"{side}_upper_leg")
        bone(f"{side}_foot", (0.12 * x, 0, 0.12), (0.12 * x, -0.13, 0.04), f"{side}_lower_leg")

    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def create_avatar_meshes(arm):
    skin = mat("warm_skin_material", (0.78, 0.55, 0.45, 1.0))
    hair = mat("dark_brown_hair_material", (0.08, 0.055, 0.045, 1.0))
    shirt = mat("robotics_lab_jacket_material", (0.82, 0.86, 0.88, 1.0))
    pants = mat("dark_work_pants_material", (0.08, 0.10, 0.13, 1.0))
    boot = mat("black_boot_material", (0.02, 0.02, 0.025, 1.0))
    blue = mat("engineering_blue_accent_material", (0.10, 0.38, 0.75, 1.0))
    eye_white = mat("eye_white_material", (0.95, 0.96, 0.94, 1.0))
    iris = mat("hazel_iris_material", (0.22, 0.48, 0.34, 1.0))
    black = mat("black_detail_material", (0.01, 0.01, 0.012, 1.0))

    body_parts = []
    body_parts.append(add_uv_sphere("torso_mesh", (0, 0, 1.12), (0.22, 0.12, 0.28), shirt, 32, 16))
    body_parts.append(add_uv_sphere("hips_mesh", (0, 0, 0.83), (0.18, 0.10, 0.13), pants, 32, 12))
    head = add_uv_sphere("head_mesh_with_face_blendshapes", (0, -0.015, 1.50), (0.14, 0.12, 0.17), skin, 48, 24)
    body_parts.append(head)
    body_parts.append(add_uv_sphere("hair_cap_mesh", (0, -0.015, 1.57), (0.145, 0.125, 0.10), hair, 48, 12))
    body_parts.append(add_uv_sphere("back_hair_bob_mesh", (0, 0.095, 1.45), (0.14, 0.08, 0.13), hair, 32, 12))

    for side, x in [("L", -1), ("R", 1)]:
        body_parts.append(add_cylinder(f"{side}_upper_arm_mesh", (0.33 * x, 0, 1.22), 0.035, 0.34, shirt, rotation=(0, math.radians(62), 0)))
        body_parts.append(add_cylinder(f"{side}_lower_arm_mesh", (0.54 * x, 0, 1.02), 0.032, 0.28, skin, rotation=(0, math.radians(35), 0)))
        body_parts.append(add_uv_sphere(f"{side}_palm_mesh", (0.68 * x, -0.002, 0.88), (0.04, 0.025, 0.035), skin, 16, 8))
        for i, finger in enumerate(["thumb", "index", "middle", "ring", "pinky"]):
            y = (i - 2) * 0.017
            length = 0.06 if finger != "thumb" else 0.052
            body_parts.append(add_cylinder(f"{side}_{finger}_mesh", (0.73 * x, y, 0.855), 0.007, length, skin, vertices=12, rotation=(0, math.radians(82), 0)))

        body_parts.append(add_cylinder(f"{side}_upper_leg_mesh", (0.10 * x, 0, 0.62), 0.045, 0.50, pants))
        body_parts.append(add_cylinder(f"{side}_lower_leg_mesh", (0.11 * x, 0, 0.28), 0.035, 0.36, pants))
        body_parts.append(add_cube(f"{side}_foot_mesh", (0.12 * x, -0.055, 0.045), (0.055, 0.10, 0.025), boot))

    for side, x in [("L", -1), ("R", 1)]:
        body_parts.append(add_uv_sphere(f"{side}_eye_white_mesh", (0.052 * x, -0.120, 1.525), (0.035, 0.012, 0.025), eye_white, 24, 8))
        body_parts.append(add_uv_sphere(f"{side}_iris_mesh", (0.052 * x, -0.132, 1.525), (0.014, 0.004, 0.014), iris, 16, 8))
        body_parts.append(add_uv_sphere(f"{side}_pupil_mesh", (0.052 * x, -0.136, 1.525), (0.006, 0.002, 0.006), black, 12, 6))

    body_parts.append(add_cube("mouth_mesh", (0, -0.137, 1.465), (0.045, 0.004, 0.006), black))
    body_parts.append(add_cube("blue_robotics_badge_mesh", (0.08, -0.124, 1.18), (0.035, 0.004, 0.035), blue))

    for obj in body_parts:
        obj.parent = arm

    add_shape_keys(head)
    return body_parts


def add_shape_keys(head):
    basis = head.shape_key_add(name="Basis")
    basis.interpolation = "KEY_LINEAR"
    blink = head.shape_key_add(name="blink")
    smile = head.shape_key_add(name="smile")
    mouth_open = head.shape_key_add(name="mouth_open")
    aa = head.shape_key_add(name="viseme_AA")
    oo = head.shape_key_add(name="viseme_OO")

    for idx, vert in enumerate(head.data.vertices):
        co = vert.co
        if co.y < -0.55 and 0.0 < co.z < 0.42:
            blink.data[idx].co.z -= 0.035
        if co.y < -0.55 and -0.40 < co.z < -0.05:
            smile.data[idx].co.x *= 1.08
            smile.data[idx].co.z += 0.015
            mouth_open.data[idx].co.z -= 0.030
            aa.data[idx].co.z -= 0.050
            oo.data[idx].co.x *= 0.82


def pose_bone(arm, name, rot=(0, 0, 0), loc=(0, 0, 0), frame=1):
    pb = arm.pose.bones[name]
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = tuple(math.radians(v) for v in rot)
    pb.location = loc
    pb.keyframe_insert("rotation_euler", frame=frame)
    pb.keyframe_insert("location", frame=frame)


def make_action(arm, name, frames):
    action = bpy.data.actions.new(name)
    arm.animation_data_create()
    arm.animation_data.action = action
    for frame, values in frames:
        bpy.context.scene.frame_set(frame)
        for bone_name, rot in values.items():
            pose_bone(arm, bone_name, rot=rot, frame=frame)
    action.use_fake_user = True


def create_actions(arm):
    make_action(arm, "stand_idle", [(1, {}), (30, {"head": (2, 0, 0)}), (60, {})])
    make_action(arm, "sit", [(1, {}), (35, {"hips": (-8, 0, 0), "L_upper_leg": (-72, 0, 0), "R_upper_leg": (-72, 0, 0), "L_lower_leg": (70, 0, 0), "R_lower_leg": (70, 0, 0)})])
    make_action(arm, "walk", [(1, {"L_upper_leg": (22, 0, 0), "R_upper_leg": (-22, 0, 0), "L_upper_arm": (-18, 0, 0), "R_upper_arm": (18, 0, 0)}), (18, {"L_upper_leg": (-22, 0, 0), "R_upper_leg": (22, 0, 0), "L_upper_arm": (18, 0, 0), "R_upper_arm": (-18, 0, 0)}), (36, {"L_upper_leg": (22, 0, 0), "R_upper_leg": (-22, 0, 0), "L_upper_arm": (-18, 0, 0), "R_upper_arm": (18, 0, 0)})])
    make_action(arm, "jog", [(1, {"L_upper_leg": (38, 0, 0), "R_upper_leg": (-38, 0, 0), "L_upper_arm": (-34, 0, 0), "R_upper_arm": (34, 0, 0)}), (12, {"L_upper_leg": (-38, 0, 0), "R_upper_leg": (38, 0, 0), "L_upper_arm": (34, 0, 0), "R_upper_arm": (-34, 0, 0)}), (24, {"L_upper_leg": (38, 0, 0), "R_upper_leg": (-38, 0, 0), "L_upper_arm": (-34, 0, 0), "R_upper_arm": (34, 0, 0)})])
    make_action(arm, "open_hand", [(1, {}), (25, {"L_index_01": (0, 0, -5), "L_middle_01": (0, 0, 0), "L_ring_01": (0, 0, 5), "R_index_01": (0, 0, 5), "R_middle_01": (0, 0, 0), "R_ring_01": (0, 0, -5)})])
    make_action(arm, "close_hand", [(1, {}), (25, {"L_index_01": (55, 0, 0), "L_middle_01": (60, 0, 0), "L_ring_01": (55, 0, 0), "L_pinky_01": (50, 0, 0), "L_thumb_01": (35, 0, 20), "R_index_01": (55, 0, 0), "R_middle_01": (60, 0, 0), "R_ring_01": (55, 0, 0), "R_pinky_01": (50, 0, 0), "R_thumb_01": (35, 0, -20)})])
    make_action(arm, "talk_gesture", [(1, {}), (30, {"head": (4, 0, -8), "R_upper_arm": (-24, 0, 18), "R_lower_arm": (-32, 0, 0)}), (60, {})])


def animate_shape_keys():
    head = bpy.data.objects["head_mesh_with_face_blendshapes"]
    keys = head.data.shape_keys
    keys.animation_data_create()
    action = bpy.data.actions.new("face_lipsync_test")
    keys.animation_data.action = action
    for name in ["blink", "smile", "mouth_open", "viseme_AA", "viseme_OO"]:
        block = keys.key_blocks[name]
        for frame, value in [(1, 0.0), (10, 1.0 if name in ["mouth_open", "viseme_AA"] else 0.0), (20, 0.0), (32, 1.0 if name == "viseme_OO" else 0.0), (42, 0.0), (50, 1.0 if name == "blink" else 0.0), (55, 0.0), (70, 1.0 if name == "smile" else 0.0)]:
            block.value = value
            block.keyframe_insert("value", frame=frame)
    action.use_fake_user = True


def export_glb():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(OUT_GLB),
        export_format="GLB",
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_morph=True,
        export_yup=True,
    )
    manifest = {
        "schema_version": 1,
        "candidate_id": CANDIDATE_ID,
        "display_name": DISPLAY_NAME,
        "role_title": ROLE_TITLE,
        "asset_type": "test_rigged_glb",
        "status": "pipeline_test_exported",
        "glb": str(OUT_GLB).replace("\\", "/"),
        "created_by": "tools/create_test_rigged_avatar_glb.py",
        "target_height_m": 1.65,
        "contains": {
            "armature": True,
            "finger_bones": True,
            "facial_shape_keys": ["blink", "smile", "mouth_open", "viseme_AA", "viseme_OO"],
            "actions": ["stand_idle", "sit", "walk", "jog", "open_hand", "close_hand", "talk_gesture", "face_lipsync_test"],
        },
        "truth_note": "This is a Blender pipeline proof, not final character art. It proves GLB export of mesh, rig, finger bones, facial blendshapes, and actions.",
    }
    OUT_META.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 90
    arm = create_armature()
    create_avatar_meshes(arm)
    create_actions(arm)
    animate_shape_keys()
    bpy.ops.object.light_add(type="AREA", location=(0, -3, 3))
    bpy.context.object.name = "soft_preview_key_light"
    bpy.context.object.data.energy = 350
    bpy.context.object.data.size = 4
    bpy.ops.object.camera_add(location=(0, -3.2, 1.35), rotation=(math.radians(76), 0, 0))
    bpy.context.scene.camera = bpy.context.object
    export_glb()


if __name__ == "__main__":
    main()
