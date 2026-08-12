from __future__ import annotations

import math
import shutil
import sys
from datetime import datetime
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.avatar_body_policy_gate import enforce_marinette_live_body_policy  # noqa: E402

MODEL_PATH = ROOT / "Avatar" / "models" / "temp_ai" / "ladybug_marinette_expanded_smoke" / "avatar.glb"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_PATH = MODEL_PATH.with_name(f"avatar_before_hair_hands_v3_{STAMP}.glb")


def make_material(name: str, color: tuple[float, float, float, float], roughness: float = 0.45):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = 0.0
    return mat


HAIR_MAT = make_material("v3_layered_midnight_blue_hair", (0.015, 0.025, 0.11, 1.0), 0.28)
HAIR_HILITE_MAT = make_material("v3_soft_blue_hair_highlights", (0.08, 0.14, 0.34, 1.0), 0.22)
NAIL_MAT = make_material("v3_soft_natural_nails", (0.98, 0.74, 0.64, 1.0), 0.38)
SKIN_MAT = make_material("v3_warm_fingertip_skin", (0.96, 0.70, 0.58, 1.0), 0.5)


def curve_strand(name: str, points: list[tuple[float, float, float]], mat, bevel: float = 0.006):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 4
    curve.bevel_depth = bevel
    curve.bevel_resolution = 2
    spl = curve.splines.new("POLY")
    spl.points.add(len(points) - 1)
    for point, co in zip(spl.points, points):
        point.co = (co[0], co[1], co[2], 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def add_scalp_strands():
    # Fan-shaped layered bangs and crown strands. These are visible geometry guides
    # until the avatar graduates to a real groom/hair-simulation asset.
    for i in range(34):
        t = -1.0 + (2.0 * i / 33)
        start = (0.015 * t, 1.56, 0.025)
        mid = (0.13 * t, 1.50 - 0.03 * abs(t), 0.105)
        end = (0.24 * t, 1.42 - 0.05 * abs(t), 0.085 - 0.015 * abs(t))
        mat = HAIR_HILITE_MAT if i % 5 == 0 else HAIR_MAT
        curve_strand(f"v3_bang_strand_{i:02d}", [start, mid, end], mat, 0.0055)
    for i in range(24):
        angle = (i / 24) * math.tau
        r0 = 0.05
        r1 = 0.22
        start = (math.cos(angle) * r0, 1.58, math.sin(angle) * r0)
        mid = (math.cos(angle) * 0.15, 1.54, math.sin(angle) * 0.14)
        end = (math.cos(angle) * r1, 1.48, math.sin(angle) * r1)
        curve_strand(f"v3_crown_strand_{i:02d}", [start, mid, end], HAIR_MAT, 0.0045)


def add_pigtail_strands():
    for side in (-1, 1):
        base_x = side * 0.31
        for i in range(28):
            frac = -1.0 + 2.0 * i / 27
            sway = 0.035 * math.sin(i * 1.7)
            start = (base_x, 1.38 + 0.045 * frac, 0.015 + sway)
            mid = (base_x + side * (0.06 + 0.025 * math.cos(i)), 1.31 + 0.035 * frac, 0.02 + sway)
            end = (base_x + side * 0.18, 1.22 + 0.055 * frac, 0.025 + sway)
            mat = HAIR_HILITE_MAT if i % 6 == 0 else HAIR_MAT
            curve_strand(f"v3_pigtail_{'r' if side > 0 else 'l'}_strand_{i:02d}", [start, mid, end], mat, 0.006)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.105, location=(base_x + side * 0.07, 1.30, 0.02))
        tie = bpy.context.object
        tie.name = f"v3_pigtail_mass_{'r' if side > 0 else 'l'}"
        tie.scale = (1.25, 0.7, 0.9)
        tie.data.materials.append(HAIR_MAT)


def add_hand_details():
    # Approximate fingertip/nail landmarks for the current simple GLB. The runtime
    # already animates fingers procedurally; these make hands read as hands in GLB.
    for side in (-1, 1):
        palm_x = side * 0.43
        for i, offset in enumerate([-0.048, -0.02, 0.008, 0.036]):
            x = palm_x + side * (0.034 + abs(offset) * 0.3)
            y = 0.78 + offset
            z = 0.035 + (i - 1.5) * 0.012
            bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.014, location=(x, y, z))
            tip = bpy.context.object
            tip.name = f"v3_{'right' if side > 0 else 'left'}_fingertip_{i}"
            tip.scale = (0.75, 1.1, 0.55)
            tip.data.materials.append(SKIN_MAT)
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x + side * 0.004, y + 0.005, z + 0.009))
            nail = bpy.context.object
            nail.name = f"v3_{'right' if side > 0 else 'left'}_fingernail_{i}"
            nail.scale = (0.009, 0.003, 0.005)
            nail.data.materials.append(NAIL_MAT)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.013, location=(palm_x + side * 0.02, 0.815, -0.028))
        thumb = bpy.context.object
        thumb.name = f"v3_{'right' if side > 0 else 'left'}_thumb_tip"
        thumb.scale = (0.8, 1.0, 0.7)
        thumb.data.materials.append(SKIN_MAT)


def main():
    enforce_marinette_live_body_policy(ROOT, MODEL_PATH)
    if not MODEL_PATH.exists():
        raise FileNotFoundError(MODEL_PATH)
    shutil.copy2(MODEL_PATH, BACKUP_PATH)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.import_scene.gltf(filepath=str(MODEL_PATH))
    add_scalp_strands()
    add_pigtail_strands()
    add_hand_details()
    bpy.context.scene["kira_avatar_v3_note"] = (
        "Functional bridge pass: visible layered hair strands and hand/fingertip detail. "
        "Full production strand grooming, physics, facial rigging, and blendshape-driven lipsync remain future work."
    )
    bpy.ops.export_scene.gltf(filepath=str(MODEL_PATH), export_format="GLB")
    print(f"Updated {MODEL_PATH}")
    print(f"Backup {BACKUP_PATH}")


if __name__ == "__main__":
    main()
