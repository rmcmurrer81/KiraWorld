from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.avatar_body_policy_gate import (  # noqa: E402
    RuntimeActivationApprovalError,
    activate_staged_model_if_approved,
    enforce_marinette_procedural_body_policy,
)

CANONICAL_CANDIDATE_ID = "ladybug_marinette_expanded_smoke"
MODEL_DIR = ROOT / "Avatar" / "models" / "temp_ai" / "ladybug_marinette_expanded_smoke"
AVATAR = MODEL_DIR / "avatar.glb"
STAGED = MODEL_DIR / "avatar_redo_doll_safe_v1_20260712.glb"
MANIFEST = MODEL_DIR / "avatar_redo_doll_safe_v1.json"
ACTIVATION_APPROVAL = MODEL_DIR / "avatar_redo_doll_safe_v1.activation_approval.json"


created_meshes: list[tuple[bpy.types.Object, str]] = []


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def mat(name: str, color: tuple[float, float, float, float], roughness: float = 0.55) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = color
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
    return material


SKIN = mat("redo_v1_marinette_smooth_doll_safe_skin", (0.83, 0.64, 0.56, 1.0), 0.62)
HAIR = mat("redo_v1_marinette_deep_blue_black_hair", (0.004, 0.012, 0.055, 1.0), 0.48)
HAIR_HI = mat("redo_v1_marinette_blue_hair_highlight", (0.025, 0.045, 0.15, 1.0), 0.42)
WHITE = mat("redo_v1_named_eye_white", (0.92, 0.96, 1.0, 1.0), 0.35)
IRIS = mat("redo_v1_named_blue_iris", (0.05, 0.38, 0.72, 1.0), 0.30)
PUPIL = mat("redo_v1_named_pupil_black", (0.004, 0.004, 0.006, 1.0), 0.22)
LIP = mat("redo_v1_soft_lip_tint", (0.65, 0.25, 0.34, 1.0), 0.50)
BLUSH = mat("redo_v1_soft_cheek_tint", (0.92, 0.38, 0.48, 1.0), 0.58)
RED = mat("redo_v1_red_pigtail_ties", (0.72, 0.03, 0.07, 1.0), 0.50)
SHOE = mat("redo_v1_simple_black_flats", (0.018, 0.017, 0.020, 1.0), 0.52)


def add_uv(
    name: str,
    loc: tuple[float, float, float],
    scale: tuple[float, float, float],
    material: bpy.types.Material,
    bone: str,
    segments: int = 48,
    rings: int | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings or max(12, segments // 2),
        radius=1.0,
        location=loc,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_mesh"
    obj.scale = scale
    obj.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    created_meshes.append((obj, bone))
    return obj


def add_limb(
    name: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    radius: float,
    material: bpy.types.Material,
    bone: str,
    vertices: int = 32,
) -> bpy.types.Object:
    start_v = Vector(start)
    end_v = Vector(end)
    direction = end_v - start_v
    midpoint = (start_v + end_v) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=max(direction.length, 0.001), location=midpoint)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_mesh"
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    obj.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    created_meshes.append((obj, bone))
    return obj


def add_soft_head() -> None:
    head = add_uv(
        "redo_v1_head_marinette_soft_oval_named",
        (0.0, 0.060, 2.080),
        (0.155, 0.112, 0.188),
        SKIN,
        "head",
        96,
        48,
    )
    for vertex in head.data.vertices:
        co = vertex.co
        z = max(-1.0, min(1.0, co.z))
        front = max(0.0, co.y)
        lower = max(0.0, -z - 0.05)
        chin = max(0.0, -z - 0.54)
        cheek = max(0.0, 1.0 - abs(z + 0.02) * 1.75)
        eye_band = max(0.0, 1.0 - abs(z - 0.32) * 3.8)
        centerline = max(0.0, 1.0 - abs(co.x) * 5.0)
        nose = max(0.0, 1.0 - abs(z - 0.06) * 5.2) * centerline
        mouth = max(0.0, 1.0 - abs(z + 0.25) * 5.8) * centerline
        co.x *= 1.0 - lower * 0.16 - chin * 0.18 + cheek * front * 0.06
        co.y *= 1.0 - lower * 0.08 + cheek * front * 0.05
        co.y += front * (nose * 0.048 + mouth * 0.010)
        if eye_band and front > 0.20:
            co.y -= eye_band * 0.010
    head.data.update()


def make_rig() -> bpy.types.Object:
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    armature = bpy.context.object
    armature.name = "Marinette_Doll_Safe_Redo_Rig_v1"
    armature.data.name = "Marinette_Doll_Safe_Redo_Rig_v1_Data"
    armature.show_in_front = True
    bones = armature.data.edit_bones
    bones.remove(bones[0])

    def bone(name: str, head: tuple[float, float, float], tail: tuple[float, float, float], parent: str | None = None) -> None:
        item = bones.new(name)
        item.head = Vector(head)
        item.tail = Vector(tail)
        item.roll = 0
        if parent:
            item.parent = bones[parent]
            item.use_connect = False

    bone("hips", (0, 0, 0.94), (0, 0, 1.15))
    bone("spine", (0, 0, 1.13), (0, 0, 1.48), "hips")
    bone("chest", (0, 0, 1.45), (0, 0, 1.72), "spine")
    bone("neck", (0, 0, 1.68), (0, 0, 1.82), "chest")
    bone("head", (0, 0, 1.80), (0, 0, 2.28), "neck")
    bone("jaw", (0, 0.18, 2.02), (0, 0.24, 1.96), "head")
    for side, sign in (("L", -1), ("R", 1)):
        bone(f"eye_socket.{side}", (0.056 * sign, 0.208, 2.118), (0.056 * sign, 0.260, 2.118), "head")
        bone(f"eyelid.{side}", (0.056 * sign, 0.224, 2.135), (0.056 * sign, 0.280, 2.090), "head")
        bone(f"upper_arm.{side}", (0.140 * sign, 0, 1.61), (0.225 * sign, 0.025, 1.31), "chest")
        bone(f"forearm.{side}", (0.225 * sign, 0.025, 1.31), (0.210 * sign, 0.060, 1.04), f"upper_arm.{side}")
        bone(f"hand.{side}", (0.210 * sign, 0.060, 1.04), (0.212 * sign, 0.080, 0.94), f"forearm.{side}")
        bone(f"thigh.{side}", (0.082 * sign, 0, 0.96), (0.110 * sign, 0.018, 0.58), "hips")
        bone(f"shin.{side}", (0.110 * sign, 0.018, 0.58), (0.100 * sign, 0.038, 0.16), f"thigh.{side}")
        bone(f"foot.{side}", (0.100 * sign, 0.038, 0.16), (0.100 * sign, 0.190, 0.08), f"shin.{side}")
        bone(f"pigtail.{side}.01", (0.124 * sign, -0.042, 2.035), (0.178 * sign, -0.086, 1.968), "head")
        bone(f"pigtail.{side}.02", (0.178 * sign, -0.086, 1.968), (0.226 * sign, -0.118, 1.900), f"pigtail.{side}.01")
        bone(f"pigtail.{side}.03", (0.226 * sign, -0.118, 1.900), (0.246 * sign, -0.130, 1.850), f"pigtail.{side}.02")
    for i, x in enumerate((-0.130, -0.075, -0.020, 0.040, 0.090), 1):
        bone(f"bang.{i:02d}", (x, 0.038, 2.260), (x - 0.035, 0.202, 2.080), "head")
    bpy.ops.object.mode_set(mode="OBJECT")
    return armature


def build_body() -> None:
    add_soft_head()
    add_uv("redo_v1_smooth_doll_safe_torso_no_anatomy", (0, 0.004, 1.360), (0.116, 0.070, 0.330), SKIN, "spine", 72)
    add_uv("redo_v1_smooth_upper_chest_no_anatomy", (0, 0.006, 1.585), (0.128, 0.074, 0.105), SKIN, "chest", 64)
    add_uv("redo_v1_smooth_neck_bridge", (0, 0.000, 1.765), (0.060, 0.042, 0.075), SKIN, "neck", 48)
    add_uv("redo_v1_soft_shoulder_chest_blend", (0, 0.003, 1.620), (0.156, 0.058, 0.060), SKIN, "chest", 56)
    add_uv("redo_v1_soft_waist_hip_blend", (0, 0.000, 1.125), (0.112, 0.065, 0.080), SKIN, "spine", 48)
    add_uv("redo_v1_smooth_hips_doll_safe", (0, 0.000, 1.000), (0.124, 0.074, 0.085), SKIN, "hips", 56)
    for side, sign in (("L", -1), ("R", 1)):
        add_uv(f"redo_v1_smooth_shoulder_joint.{side}", (0.132 * sign, 0.006, 1.595), (0.038, 0.033, 0.042), SKIN, f"upper_arm.{side}", 32)
        add_limb(f"redo_v1_upper_arm_smooth.{side}", (0.135 * sign, 0.008, 1.58), (0.220 * sign, 0.028, 1.31), 0.027, SKIN, f"upper_arm.{side}")
        add_uv(f"redo_v1_smooth_elbow_joint.{side}", (0.220 * sign, 0.028, 1.310), (0.026, 0.022, 0.026), SKIN, f"forearm.{side}", 24)
        add_limb(f"redo_v1_forearm_smooth.{side}", (0.220 * sign, 0.028, 1.31), (0.205 * sign, 0.062, 1.045), 0.022, SKIN, f"forearm.{side}")
        add_uv(f"redo_v1_smooth_wrist_joint.{side}", (0.207 * sign, 0.063, 1.045), (0.020, 0.016, 0.020), SKIN, f"hand.{side}", 20)
        add_uv(f"redo_v1_simple_hand_smooth.{side}", (0.208 * sign, 0.073, 0.990), (0.032, 0.020, 0.040), SKIN, f"hand.{side}", 32)
        add_uv(f"redo_v1_smooth_hip_joint.{side}", (0.072 * sign, 0.005, 0.960), (0.044, 0.034, 0.044), SKIN, f"thigh.{side}", 32)
        add_limb(f"redo_v1_thigh_smooth.{side}", (0.072 * sign, 0.006, 0.950), (0.110 * sign, 0.020, 0.590), 0.037, SKIN, f"thigh.{side}")
        add_uv(f"redo_v1_smooth_knee_joint.{side}", (0.110 * sign, 0.020, 0.590), (0.033, 0.027, 0.033), SKIN, f"shin.{side}", 28)
        add_limb(f"redo_v1_shin_smooth.{side}", (0.110 * sign, 0.020, 0.590), (0.098 * sign, 0.040, 0.170), 0.030, SKIN, f"shin.{side}")
        add_uv(f"redo_v1_smooth_ankle_joint.{side}", (0.099 * sign, 0.042, 0.170), (0.023, 0.018, 0.026), SKIN, f"foot.{side}", 20)
        add_uv(f"redo_v1_simple_black_flat_shoe.{side}", (0.100 * sign, 0.142, 0.075), (0.040, 0.082, 0.026), SHOE, f"foot.{side}", 32)


def build_face() -> None:
    for side, sign in (("L", -1), ("R", 1)):
        x = 0.055 * sign
        add_uv(f"redo_v1_eye_socket_anchor.{side}", (x, 0.218, 2.126), (0.032, 0.0012, 0.017), SKIN, f"eye_socket.{side}", 32)
        add_uv(f"redo_v1_eye_white.{side}", (x, 0.230, 2.126), (0.025, 0.0016, 0.012), WHITE, f"eye_socket.{side}", 48)
        add_uv(f"redo_v1_iris_blue.{side}", (x, 0.233, 2.125), (0.0085, 0.0008, 0.0085), IRIS, f"eye_socket.{side}", 32)
        add_uv(f"redo_v1_pupil_black.{side}", (x, 0.235, 2.125), (0.0032, 0.00045, 0.0032), PUPIL, f"eye_socket.{side}", 18)
        add_uv(f"redo_v1_soft_upper_lid.{side}", (x, 0.236, 2.137), (0.024, 0.0005, 0.0022), HAIR, f"eyelid.{side}", 24)
        add_uv(f"redo_v1_soft_cheek_tint.{side}", (0.073 * sign, 0.228, 2.050), (0.011, 0.00075, 0.0055), BLUSH, "head", 18)
    add_uv("redo_v1_named_soft_nose_tip", (0, 0.232, 2.080), (0.0052, 0.0028, 0.0062), SKIN, "head", 20)
    add_limb("redo_v1_soft_smile_line", (-0.026, 0.232, 2.000), (0.026, 0.232, 2.000), 0.0014, LIP, "jaw", 12)


def build_hair() -> None:
    add_uv("redo_v1_hair_cap_deep_blue_black", (-0.006, 0.030, 2.228), (0.142, 0.058, 0.044), HAIR, "head", 72)
    add_uv("redo_v1_back_hair_mass_round", (0.000, -0.065, 2.100), (0.108, 0.030, 0.088), HAIR, "head", 64)
    add_uv("redo_v1_side_swept_bangs_main", (-0.044, 0.202, 2.195), (0.118, 0.006, 0.020), HAIR, "bang.02", 56)
    add_uv("redo_v1_side_swept_bangs_left_taper", (-0.095, 0.205, 2.170), (0.038, 0.004, 0.015), HAIR_HI, "bang.01", 36)
    add_uv("redo_v1_side_swept_bangs_right_lift", (0.052, 0.200, 2.218), (0.050, 0.004, 0.015), HAIR_HI, "bang.04", 36)
    for side, sign in (("L", -1), ("R", 1)):
        add_uv(f"redo_v1_low_pigtail_root.{side}", (0.132 * sign, -0.046, 2.018), (0.022, 0.016, 0.030), HAIR, f"pigtail.{side}.01", 36)
        add_uv(f"redo_v1_red_pigtail_tie.{side}", (0.164 * sign, -0.068, 1.990), (0.012, 0.010, 0.012), RED, f"pigtail.{side}.01", 24)
        add_limb(f"redo_v1_pigtail_gather_bridge.{side}", (0.140 * sign, -0.054, 2.010), (0.218 * sign, -0.114, 1.920), 0.006, HAIR, f"pigtail.{side}.02", 18)
        add_uv(f"redo_v1_low_twin_pigtail_volume.{side}", (0.230 * sign, -0.122, 1.900), (0.039, 0.026, 0.054), HAIR, f"pigtail.{side}.02", 48)
        add_uv(f"redo_v1_pigtail_tapered_tip.{side}", (0.252 * sign, -0.130, 1.840), (0.017, 0.012, 0.026), HAIR_HI, f"pigtail.{side}.03", 30)
        add_limb(f"redo_v1_soft_side_lock.{side}", (0.088 * sign, 0.128, 2.135), (0.122 * sign, 0.045, 1.965), 0.005, HAIR_HI, "head", 12)


def bind_to_rig(armature: bpy.types.Object) -> None:
    for obj, bone in created_meshes:
        obj.vertex_groups.clear()
        group = obj.vertex_groups.new(name=bone)
        group.add(range(len(obj.data.vertices)), 1.0, "REPLACE")
        modifier = obj.modifiers.new("Marinette_Doll_Safe_Redo_Rig_v1_Armature", "ARMATURE")
        modifier.object = armature
        obj.parent = armature


def scene_bounds() -> dict[str, list[float]]:
    lows: list[Vector] = []
    highs: list[Vector] = []
    for obj, _bone in created_meshes:
        corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        lows.append(Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners))))
        highs.append(Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners))))
    low = Vector((min(v.x for v in lows), min(v.y for v in lows), min(v.z for v in lows)))
    high = Vector((max(v.x for v in highs), max(v.y for v in highs), max(v.z for v in highs)))
    size = high - low
    return {
        "min": [round(low.x, 5), round(low.y, 5), round(low.z, 5)],
        "max": [round(high.x, 5), round(high.y, 5), round(high.z, 5)],
        "size": [round(size.x, 5), round(size.y, 5), round(size.z, 5)],
    }


def approved_activation_requested() -> bool:
    script_args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return "--activate-approved" in script_args


def main() -> int:
    body_policy_gate = enforce_marinette_procedural_body_policy(ROOT)
    clear_scene()
    armature = make_rig()
    build_body()
    build_face()
    build_hair()
    bind_to_rig(armature)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(STAGED),
        export_format="GLB",
        export_yup=True,
        export_apply=True,
        export_animations=False,
    )

    activation_requested = approved_activation_requested()
    backup = MODEL_DIR / f"avatar_before_doll_safe_redo_v1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.glb"
    activation_error: RuntimeActivationApprovalError | None = None
    try:
        activation = activate_staged_model_if_approved(
            project_root=ROOT,
            candidate_id=CANONICAL_CANDIDATE_ID,
            staged_model=STAGED,
            live_model=AVATAR,
            approval_artifact=ACTIVATION_APPROVAL,
            activation_requested=activation_requested,
            backup_path=backup,
        )
    except RuntimeActivationApprovalError as exc:
        activation = dict(exc.validation)
        activation_error = exc

    MANIFEST.write_text(
        json.dumps(
            {
                "version": "marinette_doll_safe_redo_v1",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": (
                    "activation_blocked_review_only"
                    if activation_error
                    else activation["status"]
                ),
                "runtime_model": str(AVATAR.relative_to(ROOT)).replace("\\", "/"),
                "staged_model": str(STAGED.relative_to(ROOT)).replace("\\", "/"),
                "staged_model_sha256": activation.get("staged_sha256", ""),
                "active_model_replaced": bool(activation.get("active_model_replaced")),
                "runtime_activation_allowed": bool(activation.get("runtime_activation_allowed")),
                "activation_approval_artifact": str(ACTIVATION_APPROVAL.relative_to(ROOT)).replace("\\", "/"),
                "activation": activation,
                "maturity_policy": "non_adult_doll_safe",
                "adult_anatomy_assets_used": False,
                "body_policy_validation": body_policy_gate,
                "source_body_mesh": "procedural smooth doll-safe body; no adult base mesh",
                "reference_policy": "uses approved Marinette references as visual target; no head/body graft in this draft",
                "named_parts": [
                    "head",
                    "eye_socket.L/R",
                    "eye_white.L/R",
                    "iris_blue.L/R",
                    "pupil_black.L/R",
                    "low_twin_pigtail_volume.L/R",
                    "side_swept_bangs",
                    "smooth_doll_safe_torso_no_anatomy",
                ],
                "bounds": scene_bounds(),
                "acceptance_notes": [
                    "This is a redo draft for Robert review, not a final approved likeness.",
                    "Default execution is staged/review-only and does not replace the live avatar.",
                    "Live replacement requires --activate-approved plus a separate approval artifact matching the exact staged SHA-256.",
                    "The body is intentionally smooth and non-explicit for normal non-adult Marinette.",
                    "Hair is built as named pigtail/bang parts so the next builder pass can replace or refine it.",
                    "Eyes are named and bound to eye_socket bones so placement can be checked automatically.",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if activation_error:
        raise activation_error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
