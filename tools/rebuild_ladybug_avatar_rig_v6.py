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

from tools.avatar_body_policy_gate import enforce_body_policy  # noqa: E402

MODEL_DIR = ROOT / "Avatar" / "models" / "temp_ai" / "ladybug_marinette_expanded_smoke"
AVATAR = MODEL_DIR / "avatar.glb"
METADATA = MODEL_DIR / "avatar_functional_rig_v6.json"
REFERENCE_DIR = Path.home() / "Desktop" / "Ladybug"
REFERENCE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
EXTERNAL_HEAD_SOURCES = [
    Path.home() / "Downloads" / "marinette.glb",
    Path.home() / "Downloads" / "marinette (1).glb",
]
EXTERNAL_RIG_REFERENCE_SOURCES = [
    Path.home() / "Downloads" / "ladybug_rigged.glb",
    Path.home() / "Downloads" / "ladybug_rigged (1).glb",
    Path.home() / "Downloads" / "ladybug_rigged.usdz",
    Path.home() / "Downloads" / "ladybug_rigged.zip",
    Path.home() / "Downloads" / "ladybug-rigged.zip",
]
GENERIC_BODY_REFERENCE_SOURCES = [
    Path.home() / "Downloads" / "base_female_-_game_ready_-_rigged_-_low_poly.glb",
    Path.home() / "Downloads" / "base_female_-_game_ready_-_rigged_-_low_poly (1).glb",
    Path.home() / "Downloads" / "human_models_set_-_malefemale_rigged.glb",
]
WORLD_FURNITURE_REFERENCE_SOURCES = [
    Path.home() / "Downloads" / "56_harbour_terrace.glb",
    Path.home() / "Downloads" / "56_Harbour_Terrace.usdz",
    Path.home() / "Downloads" / "56_harbour_terrace.zip",
    Path.home() / "Downloads" / "56-harbour-terrace.zip",
]
HAND_REFERENCE_SOURCES = [
    ROOT
    / "Assets"
    / "third_party"
    / "intake"
    / "3d_models_kira_world"
    / "avatar_builder_references"
    / "rigged_hand_base_mesh.glb",
    ROOT
    / "Assets"
    / "third_party"
    / "intake"
    / "3d_models_kira_world"
    / "avatar_builder_references"
    / "rigged_arms.glb",
]
EXTERNAL_HEAD_OBJECTS = {
    "Object_26": ("reference_show_head_face", "head"),
    "Object_24": ("reference_show_hair_shell", "head"),
    "Object_28": ("reference_show_eye_shells", "head"),
    "Object_10": ("reference_show_upper_lashes", "head"),
    "Object_6": ("reference_show_brow_lash_detail", "head"),
    "Object_3": ("reference_show_pupil_detail", "head"),
    "Object_9": ("reference_show_mouth_line", "jaw"),
    "Object_15": ("reference_show_lower_lip_detail", "jaw"),
    "Object_23": ("reference_show_nostril_detail", "head"),
}
EXTERNAL_HEAD_TARGET_CENTER = Vector((0.0, 0.082, 2.035))
EXTERNAL_HEAD_SCALE = 0.0142
EXTERNAL_HEAD_ANCHOR = "Object_26"
REFERENCE_HEAD_BASE_Z = 2.035
GENERIC_BODY_ANCHORS = ("model_body_m_body_0", "Object_60")
GENERIC_BODY_BONE = "__auto_body_surface__"
TORSO_SHELL_BONE = "__torso_shell_surface__"
HAND_SURFACE_BONE = "__auto_hand_surface__"
# Keep downloaded rigged bodies as references until their rest pose and weights
# are retargeted to the v6 locomotion skeleton. A direct nearest-bone bind can
# deform their full-body mesh badly because the source armature pose differs.
USE_ACTIVE_GENERIC_BODY_SURFACE = False
CANDIDATE_ID = "ladybug_marinette_expanded_smoke"


def mat(name, color, roughness=0.55, metallic=0.0, subsurface=0.0, specular=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        for input_name in ("Subsurface Weight", "Subsurface"):
            if input_name in bsdf.inputs:
                bsdf.inputs[input_name].default_value = subsurface
        if specular is not None:
            for input_name in ("Specular IOR Level", "Specular"):
                if input_name in bsdf.inputs:
                    bsdf.inputs[input_name].default_value = specular
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = color[3]
    return m


SKIN = mat("v6_neutral_skin_tone_base_soft_sheen", (0.78, 0.60, 0.55, 1), 0.58, 0.0, 0.20)
BLUSH = mat("v6_soft_blush", (0.91, 0.38, 0.48, 1), 0.58, 0.0, 0.06)
LIP = mat("v6_soft_lip_tint", (0.78, 0.30, 0.38, 1), 0.50, 0.0, 0.05)
HAIR = mat("v6_blue_black_hair_anisotropic_proxy", (0.002, 0.006, 0.030, 1), 0.84, 0.0, 0.0, 0.12)
HAIR_HI = mat("v6_hair_highlight_strands", (0.012, 0.022, 0.065, 1), 0.88, 0.0, 0.0, 0.06)
HAIR_WET = mat("v6_wet_hair_state_dark_gloss_reference", (0.001, 0.006, 0.030, 1), 0.16, 0.0, 0.0, 0.55)
WHITE = mat("v6_eye_white", (0.92, 0.97, 1.0, 1), 0.35)
IRIS = mat("v6_blue_iris", (0.02, 0.58, 0.82, 1), 0.28)
PUPIL = mat("v6_pupil_black", (0.005, 0.006, 0.008, 1), 0.2)
JACKET = mat("v6_civilian_charcoal_jacket_cloth", (0.035, 0.038, 0.04, 1), 0.72)
SHIRT = mat("v6_civilian_white_floral_shirt_cloth", (0.93, 0.92, 0.86, 1), 0.66)
PANTS = mat("v6_civilian_pink_pants_cloth", (0.88, 0.34, 0.49, 1), 0.68)
SHOE = mat("v6_pale_pink_ballet_flats", (0.93, 0.76, 0.68, 1), 0.58)
CUFF = mat("v6_white_pink_dot_cuffs", (0.98, 0.90, 0.91, 1), 0.62)
BLACK = mat("v6_lash_brow_black", (0.004, 0.004, 0.006, 1), 0.42)
RED = mat("v6_ladybug_red_suit_cloth", (0.78, 0.02, 0.06, 1), 0.52)
SPOT = mat("v6_ladybug_black_spots", (0.005, 0.005, 0.006, 1), 0.45)
SLEEP = mat("v6_sleepwear_lavender_modest", (0.62, 0.48, 0.82, 1), 0.75)
SWIM = mat("v6_swimwear_blue_modest", (0.08, 0.25, 0.58, 1), 0.48)
GOLD = mat("v6_earring_gold_transformation_token", (0.93, 0.62, 0.12, 1), 0.28, 0.35)


created_meshes: list[tuple[bpy.types.Object, str]] = []


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def add_uv(name, loc, scale, material, bone, segments=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=max(12, segments // 2), radius=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.shade_smooth()
    obj.data.materials.append(material)
    created_meshes.append((obj, bone))
    return obj


def add_soft_head(name, loc, scale, material, bone, segments=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1, location=loc)
    obj = bpy.context.object
    obj.name = name

    # Start from Blender's stable UV sphere topology, then reshape the local
    # vertices. This avoids the duplicate-pole cone artifact from the previous
    # hand-built mesh while keeping a face-friendly oval silhouette.
    for vertex in obj.data.vertices:
        co = vertex.co
        z = max(-1.0, min(1.0, co.z))
        front = max(0.0, co.y)
        rear = max(0.0, -co.y)
        lower_face = max(0.0, -z - 0.06)
        chin = max(0.0, -z - 0.54)
        forehead = max(0.0, z - 0.28)
        cheek_band = max(0.0, 1.0 - abs(z + 0.03) * 1.65)
        eye_band = max(0.0, 1.0 - abs(z - 0.34) * 3.6)
        jaw_band = max(0.0, 1.0 - abs(z + 0.52) * 2.8)
        temple_band = max(0.0, 1.0 - abs(z - 0.20) * 2.2)
        centerline = max(0.0, 1.0 - abs(co.x) * 5.0)
        nose_zone = max(0.0, 1.0 - abs(z - 0.05) * 5.2) * centerline
        mouth_zone = max(0.0, 1.0 - abs(z + 0.26) * 5.8) * centerline
        chin_zone = max(0.0, 1.0 - abs(z + 0.50) * 4.8) * max(0.0, 1.0 - abs(co.x) * 4.0)

        co.x *= (
            1.0
            - lower_face * 0.17
            - chin * 0.18
            + cheek_band * front * 0.070
            + jaw_band * 0.030
            + temple_band * 0.030
        )
        co.y *= 1.0 - lower_face * 0.10 + cheek_band * front * 0.070 - rear * forehead * 0.020
        co.z *= 1.0 + forehead * 0.020 - chin * 0.045

        co.y += front * cheek_band * 0.038
        co.y -= rear * lower_face * 0.018
        co.z -= chin * front * 0.014
        co.y += front * (nose_zone * 0.060 + mouth_zone * 0.012 + chin_zone * 0.012)
        co.z -= front * chin_zone * 0.008
        if eye_band and front > 0.20:
            co.y -= eye_band * 0.012

    obj.scale = scale
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()
    obj.select_set(False)
    created_meshes.append((obj, bone))
    return obj


def add_cube(name, loc, scale, material, bone):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    created_meshes.append((obj, bone))
    return obj


def add_cyl(name, loc, radius, depth, material, bone, rot=(0, 0, 0), vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    bpy.ops.object.shade_smooth()
    obj.data.materials.append(material)
    created_meshes.append((obj, bone))
    return obj


def add_limb(name, start, end, radius, material, bone, vertices=32):
    start_v = Vector(start)
    end_v = Vector(end)
    direction = end_v - start_v
    midpoint = (start_v + end_v) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=direction.length, location=midpoint)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    bpy.ops.object.shade_smooth()
    obj.data.materials.append(material)
    created_meshes.append((obj, bone))
    return obj


def append_ellipsoid_mesh(verts, faces, center, scale, u_segments=28, v_segments=14):
    base = len(verts)
    center_v = Vector(center)
    scale_v = Vector(scale)
    for j in range(v_segments + 1):
        theta = math.pi * j / v_segments
        z = math.cos(theta)
        ring_radius = math.sin(theta)
        for i in range(u_segments):
            phi = math.tau * i / u_segments
            verts.append(tuple(center_v + Vector((
                math.cos(phi) * ring_radius * scale_v.x,
                math.sin(phi) * ring_radius * scale_v.y,
                z * scale_v.z,
            ))))
    for j in range(v_segments):
        ring = base + j * u_segments
        next_ring = ring + u_segments
        for i in range(u_segments):
            faces.append((
                ring + i,
                ring + (i + 1) % u_segments,
                next_ring + (i + 1) % u_segments,
                next_ring + i,
            ))


def _tube_frame(tangent):
    tangent_v = tangent.normalized()
    up = Vector((0.0, 0.0, 1.0))
    if abs(tangent_v.dot(up)) > 0.86:
        up = Vector((0.0, 1.0, 0.0))
    normal = tangent_v.cross(up).normalized()
    binormal = normal.cross(tangent_v).normalized()
    return normal, binormal


def append_tapered_tube_mesh(verts, faces, points, radii, segments=18):
    if len(points) < 2:
        return
    point_vs = [Vector(point) for point in points]
    base = len(verts)
    for index, point in enumerate(point_vs):
        previous_point = point_vs[max(0, index - 1)]
        next_point = point_vs[min(len(point_vs) - 1, index + 1)]
        tangent = next_point - previous_point
        if tangent.length_squared < 0.000001:
            tangent = Vector((0.0, 0.0, -1.0))
        normal, binormal = _tube_frame(tangent)
        radius = radii[min(index, len(radii) - 1)]
        squash = 0.74 if index == 0 else 0.88
        for i in range(segments):
            phi = math.tau * i / segments
            ring_point = point + normal * (math.cos(phi) * radius) + binormal * (math.sin(phi) * radius * squash)
            verts.append(tuple(ring_point))

    for ring_index in range(len(point_vs) - 1):
        ring = base + ring_index * segments
        next_ring = ring + segments
        for i in range(segments):
            faces.append((
                ring + i,
                ring + (i + 1) % segments,
                next_ring + (i + 1) % segments,
                next_ring + i,
            ))

    start_center = len(verts)
    verts.append(tuple(point_vs[0]))
    end_center = len(verts)
    verts.append(tuple(point_vs[-1]))
    for i in range(segments):
        faces.append((start_center, base + i, base + (i + 1) % segments))
        last_ring = base + (len(point_vs) - 1) * segments
        faces.append((end_center, last_ring + (i + 1) % segments, last_ring + i))


def add_relaxed_hand_surface(side, sign, palm_center, material):
    """One visible skinned hand surface, bound to the existing v6 hand/finger bones."""
    palm = Vector(palm_center)
    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    append_ellipsoid_mesh(verts, faces, palm, (0.041, 0.026, 0.041), 30, 14)

    finger_layout = [
        ("thumb", -0.038, -0.012, 0.008, 0.046, 0.030, 0.030, 0.0080),
        ("index", -0.026, 0.002, 0.012, 0.062, 0.010, 0.004, 0.0072),
        ("middle", -0.008, 0.004, 0.014, 0.067, 0.006, 0.000, 0.0076),
        ("ring", 0.010, 0.002, 0.011, 0.060, -0.003, -0.002, 0.0070),
        ("pinky", 0.027, -0.001, 0.007, 0.052, -0.008, -0.004, 0.0063),
    ]
    for finger, x_spread, y_extra, z_extra, length, x_curve, lift, base_radius in finger_layout:
        x = palm.x + x_spread * sign
        start = Vector((x, palm.y + 0.016 + y_extra, palm.z + z_extra))
        knuckle = Vector((
            x + x_curve * 0.24 * sign,
            palm.y + 0.032 + y_extra + lift,
            palm.z - 0.024 - length * 0.18 + z_extra,
        ))
        tip = Vector((
            x + x_curve * 0.52 * sign,
            palm.y + 0.038 + y_extra + lift,
            palm.z - 0.034 - length * 0.52 + z_extra,
        ))
        append_tapered_tube_mesh(
            verts,
            faces,
            [start, knuckle, tip],
            [base_radius, base_radius * 0.78, base_radius * 0.54],
            segments=18,
        )

    wrist_fill = [
        (palm.x, palm.y - 0.012, palm.z + 0.034),
        (palm.x, palm.y - 0.032, palm.z + 0.070),
    ]
    append_tapered_tube_mesh(verts, faces, wrist_fill, [0.022, 0.018], segments=20)

    mesh = bpy.data.meshes.new(f"production_relaxed_hand_surface.{side}_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.validate(clean_customdata=False)
    obj = bpy.data.objects.new(f"production_relaxed_skinned_hand.{side}", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()
    obj.select_set(False)
    created_meshes.append((obj, f"{HAND_SURFACE_BONE}.{side}"))
    return obj


def add_anatomy_body_shell(name, material):
    """Single smooth neutral torso/hip shell bound by nearest v6 body bone."""
    ring_count = 56
    rings = [
        (1.805, 0.082, 0.052, 0.006),
        (1.730, 0.150, 0.070, 0.012),
        (1.625, 0.146, 0.078, 0.017),
        (1.500, 0.128, 0.073, 0.018),
        (1.365, 0.106, 0.064, 0.014),
        (1.235, 0.114, 0.066, 0.006),
        (1.110, 0.142, 0.076, 0.001),
        (1.015, 0.150, 0.074, -0.001),
        (0.935, 0.104, 0.062, -0.001),
    ]
    verts = []
    for ring_index, (z, rx, ry, cy) in enumerate(rings):
        normalized = ring_index / max(1, len(rings) - 1)
        for i in range(ring_count):
            theta = math.tau * i / ring_count
            x = math.cos(theta) * rx
            y = cy + math.sin(theta) * ry
            front = max(0.0, math.sin(theta))
            back = max(0.0, -math.sin(theta))
            waist = max(0.0, 1.0 - abs(normalized - 0.58) * 4.0)
            shoulder = max(0.0, 1.0 - abs(normalized - 0.20) * 5.0)
            hip = max(0.0, 1.0 - abs(normalized - 0.78) * 4.0)
            y += front * (0.010 * shoulder + 0.008 * waist + 0.004 * hip)
            y -= back * (0.005 * waist)
            verts.append((x, y, z))

    faces = []
    for r in range(len(rings) - 1):
        base = r * ring_count
        next_base = (r + 1) * ring_count
        for i in range(ring_count):
            faces.append((base + i, base + (i + 1) % ring_count, next_base + (i + 1) % ring_count, next_base + i))
    top_center = len(verts)
    verts.append((0, rings[0][3], rings[0][0] + 0.010))
    bottom_center = len(verts)
    verts.append((0, rings[-1][3], rings[-1][0] - 0.010))
    for i in range(ring_count):
        faces.append((top_center, (i + 1) % ring_count, i))
        bottom_base = (len(rings) - 1) * ring_count
        faces.append((bottom_center, bottom_base + i, bottom_base + (i + 1) % ring_count))

    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.validate(clean_customdata=False)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()
    obj.select_set(False)
    created_meshes.append((obj, TORSO_SHELL_BONE))
    return obj


def add_strand_chain(name, points, radius, material, bone, vertices=8):
    if len(points) < 2:
        return
    prev = Vector(points[0])
    for i, point in enumerate(points[1:], 1):
        current = Vector(point)
        seg_radius = max(radius * (1.0 - i * 0.10), radius * 0.55)
        add_limb(f"{name}_seg_{i:02d}", prev, current, seg_radius, material, bone, vertices=vertices)
        prev = current


def add_hair_card(name, points, widths, material, bone):
    """Hair-card guide disabled; strand/lock geometry carries the visible hair."""
    return None
    if len(points) < 2:
        return None
    vectors = [Vector(point) for point in points]
    if isinstance(widths, (int, float)):
        widths = [float(widths)] * len(vectors)
    elif len(widths) != len(vectors):
        widths = [float(widths[0])] * len(vectors)

    verts = []
    for i, point in enumerate(vectors):
        before = vectors[max(0, i - 1)]
        after = vectors[min(len(vectors) - 1, i + 1)]
        tangent = after - before
        if tangent.length < 0.0001:
            tangent = Vector((1, 0, 0))
        tangent.normalize()
        side = Vector((-tangent.y, tangent.x, 0.0))
        if side.length < 0.0001:
            side = Vector((1, 0, 0))
        side.normalize()
        verts.append(tuple(point + side * widths[i]))
        verts.append(tuple(point - side * widths[i]))

    faces = []
    for i in range(len(vectors) - 1):
        faces.append((i * 2, i * 2 + 1, i * 2 + 3, i * 2 + 2))
        faces.append((i * 2 + 2, i * 2 + 3, i * 2 + 1, i * 2))

    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    created_meshes.append((obj, bone))
    return obj


def add_swept_hair_strands(prefix, count, root_fn, mid_fn, end_fn, radius, bone_fn):
    for i in range(count):
        t = i / max(1, count - 1)
        add_strand_chain(
            f"{prefix}_{i:02d}",
            [root_fn(t, i), mid_fn(t, i), end_fn(t, i)],
            radius * (1.22 if i % 9 == 0 else 1.0),
            HAIR_HI if i % 5 == 0 else HAIR,
            bone_fn(t, i),
            vertices=7,
        )


def collect_reference_images(limit=24):
    if not REFERENCE_DIR.exists():
        return []
    refs = []
    for path in sorted(REFERENCE_DIR.rglob("*"), key=lambda item: item.name.lower()):
        if path.suffix.lower() not in REFERENCE_EXTENSIONS:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        refs.append({
            "name": path.name,
            "folder": str(path.parent.relative_to(Path.home())),
            "bytes": size,
        })
        if len(refs) >= limit:
            break
    return refs


def make_rig():
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm = bpy.context.object
    arm.name = "Marinette_Rig_v6"
    arm.data.name = "Marinette_Rig_v6_Data"
    arm.show_in_front = True
    eb = arm.data.edit_bones
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

    bone("hips", (0, 0, 0.98), (0, 0, 1.20))
    bone("spine", (0, 0, 1.17), (0, 0, 1.56), "hips")
    bone("chest", (0, 0, 1.50), (0, 0, 1.84), "spine")
    bone("neck", (0, 0, 1.76), (0, 0, 1.88), "chest")
    bone("head", (0, 0, 1.855), (0, 0, 2.30), "neck")
    bone("jaw", (0, 0.18, 2.020), (0, 0.26, 1.944), "head")
    for side, sign in (("L", -1), ("R", 1)):
        bone(f"eyelid.{side}", (0.075 * sign, 0.255, 2.265), (0.075 * sign, 0.31, 2.205), "head")
        bone(f"upper_arm.{side}", (0.188 * sign, 0, 1.650), (0.245 * sign, 0.020, 1.345), "chest")
        bone(f"forearm.{side}", (0.245 * sign, 0.020, 1.345), (0.230 * sign, 0.048, 1.075), f"upper_arm.{side}")
        bone(f"hand.{side}", (0.230 * sign, 0.048, 1.075), (0.232 * sign, 0.080, 0.970), f"forearm.{side}")
        bone(f"thigh.{side}", (0.105 * sign, 0, 0.995), (0.145 * sign, 0.018, 0.58), "hips")
        bone(f"shin.{side}", (0.145 * sign, 0.018, 0.58), (0.125 * sign, 0.038, 0.15), f"thigh.{side}")
        bone(f"foot.{side}", (0.125 * sign, 0.038, 0.15), (0.125 * sign, 0.22, 0.07), f"shin.{side}")
        for i, finger in enumerate(("thumb", "index", "middle", "ring", "pinky")):
            xoff = (i - 2) * 0.011 * sign
            base = Vector((0.232 * sign + xoff, 0.100, 0.970))
            b1 = bone(f"{finger}.01.{side}", base, base + Vector((0.004 * sign, 0.017, -0.025)), f"hand.{side}")
            b2 = bone(f"{finger}.02.{side}", b1.tail, b1.tail + Vector((0.002 * sign, 0.017, -0.024)), b1.name)
            bone(f"{finger}.03.{side}", b2.tail, b2.tail + Vector((0.002 * sign, 0.013, -0.019)), b2.name)
        bone(f"pigtail.{side}.01", (0.142 * sign, -0.034, 2.070), (0.186 * sign, -0.080, 2.008), "head")
        bone(f"pigtail.{side}.02", (0.186 * sign, -0.080, 2.008), (0.232 * sign, -0.116, 1.946), f"pigtail.{side}.01")
        bone(f"pigtail.{side}.03", (0.232 * sign, -0.116, 1.946), (0.262 * sign, -0.122, 1.895), f"pigtail.{side}.02")
    for i, x in enumerate((-0.2, -0.11, -0.03, 0.06, 0.14), 1):
        bone(f"bang.{i:02d}", (x, 0.03, 2.325), (x - 0.04, 0.205, 2.065), "head")
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


BODY_WEIGHT_SEGMENTS = {
    "hips": ((0, 0, 0.98), (0, 0, 1.20)),
    "spine": ((0, 0, 1.17), (0, 0, 1.56)),
    "chest": ((0, 0, 1.50), (0, 0, 1.84)),
    "neck": ((0, 0, 1.76), (0, 0, 1.88)),
}

for _side, _sign in (("L", -1), ("R", 1)):
    BODY_WEIGHT_SEGMENTS.update({
        f"upper_arm.{_side}": ((0.188 * _sign, 0, 1.650), (0.245 * _sign, 0.020, 1.345)),
        f"forearm.{_side}": ((0.245 * _sign, 0.020, 1.345), (0.230 * _sign, 0.048, 1.075)),
        f"hand.{_side}": ((0.230 * _sign, 0.048, 1.075), (0.232 * _sign, 0.080, 0.970)),
        f"thigh.{_side}": ((0.105 * _sign, 0, 0.995), (0.145 * _sign, 0.018, 0.58)),
        f"shin.{_side}": ((0.145 * _sign, 0.018, 0.58), (0.125 * _sign, 0.038, 0.15)),
        f"foot.{_side}": ((0.125 * _sign, 0.038, 0.15), (0.125 * _sign, 0.22, 0.07)),
    })
    for _i, _finger in enumerate(("thumb", "index", "middle", "ring", "pinky")):
        _xoff = (_i - 2) * 0.011 * _sign
        _base = Vector((0.232 * _sign + _xoff, 0.100, 0.970))
        _b1_tail = _base + Vector((0.004 * _sign, 0.017, -0.025))
        _b2_tail = _b1_tail + Vector((0.002 * _sign, 0.017, -0.024))
        _b3_tail = _b2_tail + Vector((0.002 * _sign, 0.013, -0.019))
        BODY_WEIGHT_SEGMENTS[f"{_finger}.01.{_side}"] = (tuple(_base), tuple(_b1_tail))
        BODY_WEIGHT_SEGMENTS[f"{_finger}.02.{_side}"] = (tuple(_b1_tail), tuple(_b2_tail))
        BODY_WEIGHT_SEGMENTS[f"{_finger}.03.{_side}"] = (tuple(_b2_tail), tuple(_b3_tail))


def distance_to_segment(point, start, end):
    start_v = Vector(start)
    end_v = Vector(end)
    seg = end_v - start_v
    if seg.length_squared < 0.000001:
        return (point - start_v).length
    t = max(0.0, min(1.0, (point - start_v).dot(seg) / seg.length_squared))
    nearest = start_v + seg * t
    return (point - nearest).length


def nearest_v6_body_bone(point):
    best_name = "spine"
    best_dist = 999.0
    for bone_name, (start, end) in BODY_WEIGHT_SEGMENTS.items():
        dist = distance_to_segment(point, start, end)
        if dist < best_dist:
            best_name = bone_name
            best_dist = dist
    return best_name


def hand_weight_segments(side):
    names = [f"hand.{side}"]
    for finger in ("thumb", "index", "middle", "ring", "pinky"):
        names.extend((f"{finger}.01.{side}", f"{finger}.02.{side}", f"{finger}.03.{side}"))
    return {name: BODY_WEIGHT_SEGMENTS[name] for name in names if name in BODY_WEIGHT_SEGMENTS}


def nearest_v6_hand_bone(point, side):
    best_name = f"hand.{side}"
    best_dist = 999.0
    for bone_name, (start, end) in hand_weight_segments(side).items():
        dist = distance_to_segment(point, start, end)
        if dist < best_dist:
            best_name = bone_name
            best_dist = dist
    return best_name


def bind_auto_body_surface(obj):
    groups = {name: obj.vertex_groups.new(name=name) for name in BODY_WEIGHT_SEGMENTS}
    assignments: dict[str, list[int]] = {name: [] for name in BODY_WEIGHT_SEGMENTS}
    for vertex in obj.data.vertices:
        bone_name = nearest_v6_body_bone(vertex.co)
        assignments[bone_name].append(vertex.index)
    for bone_name, indices in assignments.items():
        if indices:
            groups[bone_name].add(indices, 1.0, "REPLACE")


def bind_auto_hand_surface(obj, side):
    segments = hand_weight_segments(side)
    groups = {name: obj.vertex_groups.new(name=name) for name in segments}
    assignments: dict[str, list[int]] = {name: [] for name in segments}
    for vertex in obj.data.vertices:
        bone_name = nearest_v6_hand_bone(vertex.co, side)
        assignments[bone_name].append(vertex.index)
    for bone_name, indices in assignments.items():
        if indices:
            groups[bone_name].add(indices, 1.0, "REPLACE")


def bind_torso_shell_surface(obj):
    groups = {name: obj.vertex_groups.new(name=name) for name in ("hips", "spine", "chest")}
    for vertex in obj.data.vertices:
        z = vertex.co.z
        weights = {"hips": 0.0, "spine": 0.0, "chest": 0.0}
        if z < 1.12:
            t = max(0.0, min(1.0, (z - 0.94) / 0.18))
            weights["hips"] = 1.0 - t * 0.35
            weights["spine"] = t * 0.35
        elif z < 1.40:
            t = max(0.0, min(1.0, (z - 1.12) / 0.28))
            weights["hips"] = 0.45 * (1.0 - t)
            weights["spine"] = 0.55 + 0.25 * t
            weights["chest"] = 0.20 * t
        elif z < 1.62:
            t = max(0.0, min(1.0, (z - 1.40) / 0.22))
            weights["spine"] = 0.72 * (1.0 - t)
            weights["chest"] = 0.28 + 0.72 * t
        else:
            weights["chest"] = 1.0
        total = sum(weights.values()) or 1.0
        for bone_name, weight in weights.items():
            if weight > 0.001:
                groups[bone_name].add([vertex.index], weight / total, "REPLACE")


def bind_to_rig(arm):
    for obj, bone in created_meshes:
        obj.vertex_groups.clear()
        if bone == GENERIC_BODY_BONE:
            bind_auto_body_surface(obj)
        elif bone == TORSO_SHELL_BONE:
            bind_torso_shell_surface(obj)
        elif bone.startswith(f"{HAND_SURFACE_BONE}."):
            bind_auto_hand_surface(obj, bone.rsplit(".", 1)[-1])
        else:
            vg = obj.vertex_groups.new(name=bone)
            vg.add(range(len(obj.data.vertices)), 1.0, "REPLACE")
        mod = obj.modifiers.new("Marinette_Rig_v6_Armature", "ARMATURE")
        mod.object = arm
        obj.parent = arm


def object_world_bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    low = Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
    high = Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
    return low, high


def remove_procedural_head_surface():
    """Drop the proxy head/hair pieces once shape keys have been authored."""
    global created_meshes
    remove_prefixes = (
        "shared_head_reference",
        "shared_eye_outline",
        "shared_eye_white",
        "shared_iris",
        "shared_pupil",
        "shared_eye_highlight",
        "shared_upper_lid",
        "shared_lower_lid",
        "shared_soft_arch_brow",
        "shared_side_lash",
        "shared_soft_ear",
        "shared_ear_gold_earring",
        "shared_soft_cheek",
        "shared_smile_lip",
        "shared_upper_lip",
        "shared_lower_lip",
        "shared_nose",
        "shared_soft_chin",
        "hair_",
        "strand_",
    )
    kept = []
    for obj, bone in created_meshes:
        if obj.name.startswith(remove_prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        kept.append((obj, bone))
    created_meshes = kept


def find_external_head_source():
    for path in EXTERNAL_HEAD_SOURCES:
        if path.exists():
            return path
    return None


def collect_existing_sources(paths):
    return [
        {
            "path": str(path),
            "bytes": path.stat().st_size,
        }
        for path in paths
        if path.exists()
    ]


def find_generic_body_source():
    for path in GENERIC_BODY_REFERENCE_SOURCES:
        if path.exists():
            return path
    return None


def clone_generic_body_mesh(source_obj, source_center):
    low, high = object_world_bounds(source_obj)
    # The downloaded base female body is already Blender Z-up. Keep the body,
    # arms, hands, legs, and feet, but crop away the generic head so the
    # imported Marinette reference head/hair remains the visual authority.
    height = max(0.001, high.z - low.z)
    source_cutoff = low.z + height * 0.858
    target_foot_z = 0.035
    target_neck_cut_z = 1.820
    scale_z = (target_neck_cut_z - target_foot_z) / max(0.001, source_cutoff - low.z)
    scale_x = 0.78
    scale_y = 0.90
    target_y = 0.018

    source_vertices = [source_obj.matrix_world @ vertex.co for vertex in source_obj.data.vertices]
    face_indices = []
    used = set()
    for polygon in source_obj.data.polygons:
        verts = list(polygon.vertices)
        if any(source_vertices[index].z > source_cutoff for index in verts):
            continue
        face_indices.append(verts)
        used.update(verts)

    index_map = {}
    verts = []
    for old_index in sorted(used):
        world = source_vertices[old_index]
        index_map[old_index] = len(verts)
        verts.append((
            (world.x - source_center.x) * scale_x,
            (world.y - source_center.y) * scale_y + target_y,
            (world.z - low.z) * scale_z + target_foot_z,
        ))

    faces = [tuple(index_map[index] for index in face) for face in face_indices if all(index in index_map for index in face)]
    mesh = bpy.data.meshes.new("active_generic_full_body_surface_neutral_base_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.validate(clean_customdata=False)
    obj = bpy.data.objects.new("active_generic_full_body_surface_neutral_base", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(SKIN)
    created_meshes.append((obj, GENERIC_BODY_BONE))
    return obj


def import_generic_body_surface():
    source = find_generic_body_source()
    if not source:
        print("Generic rigged body source not found; keeping procedural v6 body fallback.")
        return None

    enforce_body_policy(
        project_root=ROOT,
        candidate_id=CANDIDATE_ID,
        body_treatment="non_adult_doll_safe",
        selected_asset_paths=[source],
        declared_asset_records=[{
            "id": f"legacy_generic_adult_body:{source.name}",
            "filename": source.name,
            "adult_only": True,
            "allowed_for_non_adult": False,
        }],
        expected_maturity_classes={"non_adult_doll_safe"},
        require_asset_evidence=True,
    )

    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(source))
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    source_objects = {obj.name: obj for obj in imported if obj.type == "MESH"}
    body = next((source_objects.get(name) for name in GENERIC_BODY_ANCHORS if source_objects.get(name)), None)
    if not body:
        print(f"Generic body GLB missing {GENERIC_BODY_ANCHORS}; keeping procedural v6 body fallback.")
        for obj in imported:
            bpy.data.objects.remove(obj, do_unlink=True)
        return None

    low, high = object_world_bounds(body)
    source_center = (low + high) * 0.5
    clone_generic_body_mesh(body, source_center)

    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)

    print(f"Imported neutral full-body surface from {source}")
    return str(source)


def remove_core_body_proxy_surface():
    """Remove torso/leg proxies once the neutral core body mesh imports."""
    global created_meshes
    remove_prefixes = (
        "shared_neck",
        "base_body_",
        "active_neutral_",
        "active_neck_",
        "active_upper_chest_",
        "base_upper_arm",
        "base_elbow",
        "base_forearm",
        "base_wrist",
        "base_hand",
        "hand_proxy",
        "shared_thumb_",
        "shared_index_",
        "shared_middle_",
        "shared_ring_",
        "shared_pinky_",
        "base_thigh",
        "base_knee",
        "base_shin",
        "base_ankle",
        "base_foot",
        "base_toe",
    )
    kept = []
    for obj, bone in created_meshes:
        if obj.name.startswith(remove_prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        kept.append((obj, bone))
    created_meshes = kept


def remove_torso_proxy_surface():
    """Replace stacked torso proxy pieces with the smooth body shell."""
    global created_meshes
    remove_names = {
        "base_body_smooth_mannequin_torso",
        "base_body_upper_chest_soft",
        "base_body_neck_chest_blend",
        "base_body_waist_blend_soft",
        "base_body_smooth_hips",
        "base_body_soft_lower_back_fill",
    }
    kept = []
    for obj, bone in created_meshes:
        if obj.name in remove_names:
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        kept.append((obj, bone))
    created_meshes = kept


def clone_reference_mesh(source_obj, new_name, bone, source_center):
    mesh = source_obj.data.copy()
    obj = bpy.data.objects.new(new_name, mesh)
    bpy.context.collection.objects.link(obj)

    for material in source_obj.data.materials:
        if material:
            obj.data.materials.append(material.copy())

    for vertex in mesh.vertices:
        world = source_obj.matrix_world @ vertex.co
        vertex.co = Vector((
            (world.x - source_center.x) * EXTERNAL_HEAD_SCALE + EXTERNAL_HEAD_TARGET_CENTER.x,
            -(world.y - source_center.y) * EXTERNAL_HEAD_SCALE + EXTERNAL_HEAD_TARGET_CENTER.y,
            (world.z - source_center.z) * EXTERNAL_HEAD_SCALE + EXTERNAL_HEAD_TARGET_CENTER.z,
        ))
    mesh.flip_normals()
    mesh.validate(clean_customdata=False)
    mesh.update()
    obj.name = new_name
    created_meshes.append((obj, bone))
    return obj


def import_reference_head_layer():
    source = find_external_head_source()
    if not source:
        print("Reference Marinette GLB not found; keeping procedural head fallback.")
        return None

    enforce_body_policy(
        project_root=ROOT,
        candidate_id=CANDIDATE_ID,
        body_treatment="non_adult_doll_safe",
        selected_asset_paths=[source],
        declared_asset_records=[{
            "id": f"legacy_character_reference_head:{source.name}",
            "filename": source.name,
            "reference_only": True,
            "copy_as_avatar_body_allowed": False,
        }],
        expected_maturity_classes={"non_adult_doll_safe"},
        require_asset_evidence=True,
    )

    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(source))
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    source_objects = {obj.name: obj for obj in imported if obj.type == "MESH"}
    anchor = source_objects.get(EXTERNAL_HEAD_ANCHOR)
    if not anchor:
        print(f"Reference Marinette GLB missing {EXTERNAL_HEAD_ANCHOR}; keeping procedural head fallback.")
        for obj in imported:
            bpy.data.objects.remove(obj, do_unlink=True)
        return None

    low, high = object_world_bounds(anchor)
    source_center = (low + high) * 0.5
    cloned = []
    for source_name, (new_name, bone) in EXTERNAL_HEAD_OBJECTS.items():
        source_obj = source_objects.get(source_name)
        if not source_obj:
            continue
        cloned.append(clone_reference_mesh(source_obj, new_name, bone, source_center))

    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)

    print(f"Imported {len(cloned)} reference head meshes from {source}")
    return str(source)


def build_reference_blink_layer():
    head_z_delta = EXTERNAL_HEAD_TARGET_CENTER.z - REFERENCE_HEAD_BASE_Z
    for side, sign in (("L", -1), ("R", 1)):
        # Skin-toned lids sit just above the downloaded reference eyes. The
        # blink shape key pulls them down, while the lid bones keep a runtime
        # target for future eye-contact and expression logic.
        add_uv(
            f"reference_blink_upper_lid.{side}",
            (0.054 * sign, 0.182, 2.084 + head_z_delta),
            (0.023, 0.0008, 0.0032),
            SKIN,
            f"eyelid.{side}",
            segments=32,
        )
        add_limb(
            f"reference_blink_lower_lid_line.{side}",
            (0.027 * sign, 0.184, 2.052 + head_z_delta),
            (0.080 * sign, 0.184, 2.053 + head_z_delta),
            0.00052,
            BLACK,
            "head",
            vertices=8,
        )


def build_body():
    add_soft_head("shared_head_reference_oval_face", (0, 0.070, 2.108), (0.164, 0.116, 0.190), SKIN, "head", segments=96, rings=48)
    add_uv("shared_neck", (0, 0.010, 1.807), (0.036, 0.032, 0.072), SKIN, "neck", segments=40)
    add_uv("base_body_smooth_mannequin_torso", (0, 0.006, 1.375), (0.122, 0.074, 0.360), SKIN, "spine", segments=64)
    add_uv("base_body_upper_chest_soft", (0, 0.012, 1.610), (0.136, 0.082, 0.145), SKIN, "chest", segments=56)
    add_uv("base_body_neck_chest_blend", (0, 0.006, 1.760), (0.088, 0.054, 0.085), SKIN, "chest", segments=48)
    add_uv("base_body_waist_blend_soft", (0, 0.0, 1.180), (0.094, 0.064, 0.095), SKIN, "spine", segments=48)
    add_uv("base_body_smooth_hips", (0, 0, 1.005), (0.130, 0.080, 0.086), SKIN, "hips", segments=48)
    add_uv("base_body_soft_lower_back_fill", (0, -0.020, 1.235), (0.104, 0.046, 0.165), SKIN, "spine", segments=40)
    for side, sign in (("L", -1), ("R", 1)):
        eye_x = 0.055 * sign
        add_uv(f"shared_eye_outline.{side}", (eye_x, 0.226, 2.184), (0.0300, 0.0012, 0.0140), BLACK, "head", segments=56)
        add_uv(f"shared_eye_white.{side}", (eye_x, 0.230, 2.184), (0.0260, 0.0020, 0.0120), WHITE, "head", segments=56)
        add_uv(f"shared_iris_blue.{side}", (eye_x, 0.234, 2.183), (0.0090, 0.0010, 0.0090), IRIS, "head", segments=36)
        add_uv(f"shared_pupil.{side}", (eye_x, 0.237, 2.183), (0.0033, 0.0006, 0.0033), PUPIL, "head", segments=24)
        add_uv(f"shared_eye_highlight.{side}", (eye_x - 0.0035 * sign, 0.239, 2.190), (0.0022, 0.00045, 0.0022), WHITE, "head", segments=12)
        add_cube(f"shared_upper_lid.{side}", (eye_x, 0.238, 2.197), (0.024, 0.00045, 0.00072), BLACK, f"eyelid.{side}")
        add_cube(f"shared_lower_lid_line.{side}", (eye_x, 0.238, 2.169), (0.011, 0.00035, 0.00040), BLACK, "head")
        add_limb(
            f"shared_soft_arch_brow.{side}",
            (0.024 * sign, 0.230, 2.217),
            (0.092 * sign, 0.232, 2.230),
            0.00070,
            BLACK,
            "head",
            vertices=8,
        )
        for lash_i in range(3):
            lash_x = (0.071 + lash_i * 0.0040) * sign
            add_limb(
                f"shared_side_lash_{lash_i}.{side}",
                (lash_x, 0.235, 2.186 + lash_i * 0.0025),
                (lash_x + 0.007 * sign, 0.238, 2.191 + lash_i * 0.0032),
                0.00048,
                BLACK,
                "head",
                vertices=8,
            )
        add_uv(f"shared_soft_ear.{side}", (0.172 * sign, 0.006, 2.104), (0.012, 0.006, 0.022), SKIN, "head", segments=20)
        add_uv(f"shared_ear_gold_earring.{side}", (0.190 * sign, 0.008, 2.098), (0.008, 0.0055, 0.016), GOLD, "head", segments=24)
        add_uv(f"shared_soft_cheek_tint.{side}", (0.075 * sign, 0.229, 2.071), (0.011, 0.00075, 0.0040), BLUSH, "head", segments=24)
        shoulder = (0.160 * sign, 0.0, 1.615)
        elbow = (0.216 * sign, 0.020, 1.330)
        wrist = (0.205 * sign, 0.048, 1.065)
        hip = (0.105 * sign, 0.0, 0.995)
        knee = (0.145 * sign, 0.018, 0.58)
        ankle = (0.125 * sign, 0.038, 0.15)
        add_limb(f"base_shoulder_connector.{side}", (0.118 * sign, 0.002, 1.615), shoulder, 0.025, SKIN, "chest", vertices=28)
        add_uv(f"base_shoulder_cap.{side}", shoulder, (0.034, 0.031, 0.034), SKIN, f"upper_arm.{side}", segments=32)
        add_limb(f"base_upper_arm.{side}", shoulder, elbow, 0.027, SKIN, f"upper_arm.{side}", vertices=36)
        add_uv(f"base_elbow_joint.{side}", elbow, (0.030, 0.027, 0.030), SKIN, f"forearm.{side}", segments=32)
        add_limb(f"base_forearm.{side}", elbow, wrist, 0.024, SKIN, f"forearm.{side}", vertices=36)
        add_uv(f"base_wrist_joint.{side}", wrist, (0.025, 0.022, 0.020), SKIN, f"forearm.{side}", segments=28)
        palm_center = (0.207 * sign, 0.080, 0.960)
        add_relaxed_hand_surface(side, sign, palm_center, SKIN)
        add_limb(f"base_thigh.{side}", hip, knee, 0.043, SKIN, f"thigh.{side}", vertices=36)
        add_uv(f"base_knee_joint.{side}", knee, (0.040, 0.035, 0.038), SKIN, f"shin.{side}", segments=28)
        add_limb(f"base_shin.{side}", knee, ankle, 0.035, SKIN, f"shin.{side}", vertices=36)
        add_uv(f"base_ankle.{side}", ankle, (0.031, 0.027, 0.049), SKIN, f"foot.{side}", segments=28)
        add_uv(f"base_foot_soft.{side}", (0.125 * sign, 0.165, 0.065), (0.066, 0.112, 0.028), SKIN, f"foot.{side}", segments=32)
        for toe in range(4):
            add_uv(
                f"base_toe_hint_{toe}.{side}",
                (0.125 * sign + (toe - 1.5) * 0.014 * sign, 0.264, 0.073),
                (0.007, 0.010, 0.006),
                SKIN,
                f"foot.{side}",
                segments=12,
            )

    add_cube("shared_smile_lip", (0, 0.229, 2.044), (0.023, 0.00045, 0.00042), LIP, "jaw")
    add_uv("shared_upper_lip_soft_shadow", (0, 0.228, 2.051), (0.009, 0.00040, 0.0010), LIP, "jaw", segments=16)
    add_uv("shared_lower_lip_soft_volume", (0, 0.228, 2.037), (0.008, 0.00035, 0.0010), LIP, "jaw", segments=16)
    add_uv("shared_nose_tip_soft", (0, 0.231, 2.114), (0.0052, 0.0030, 0.0068), SKIN, "head", segments=24)
    add_limb("shared_nose_bridge_soft", (0, 0.220, 2.148), (0, 0.229, 2.118), 0.0012, SKIN, "head", vertices=12)
    add_uv("shared_nose_under_soft_shadow", (0, 0.232, 2.104), (0.0013, 0.00022, 0.00055), SKIN, "head", segments=12)
    add_uv("shared_soft_chin_volume", (0, 0.202, 1.996), (0.010, 0.0022, 0.0050), SKIN, "jaw", segments=20)


def build_hair():
    # These are deliberately small scalp shadows, not the visible hairstyle. The
    # strand and lock chains below carry the silhouette so the hair stops reading
    # as a plastic cap.
    add_uv("hair_underlayer_hidden_crown_shadow", (-0.004, -0.018, 2.242), (0.146, 0.070, 0.034), HAIR, "head", segments=64)
    add_uv("hair_underlayer_hidden_back_scalp_shadow", (0.000, -0.086, 2.082), (0.098, 0.018, 0.076), HAIR, "head", segments=48)
    add_uv("hair_underlayer_hidden_front_hairline_shadow", (-0.040, 0.112, 2.194), (0.108, 0.012, 0.020), HAIR, "head", segments=48)
    add_uv("hair_underlayer_swept_bang_mass", (-0.044, 0.126, 2.194), (0.120, 0.017, 0.027), HAIR, "head", segments=56)
    add_uv("hair_underlayer_right_swept_side_mass", (0.112, 0.034, 2.088), (0.016, 0.009, 0.078), HAIR, "head", segments=32)
    add_uv("hair_underlayer_left_swept_side_mass", (-0.126, 0.036, 2.084), (0.016, 0.009, 0.080), HAIR, "head", segments=32)

    # Visible surface forms sit just in front of the face mesh. The previous
    # pass had too many hair pieces hidden behind the head, which made the crown
    # look bald even though the strand count was higher.
    add_uv("hair_surface_crown_coverage_top", (-0.016, 0.072, 2.274), (0.132, 0.032, 0.021), HAIR, "head", segments=64)
    add_uv("hair_surface_crown_coverage_back", (0.004, -0.040, 2.210), (0.134, 0.028, 0.058), HAIR, "head", segments=56)
    add_uv("hair_surface_left_temples_coverage", (-0.136, 0.052, 2.112), (0.020, 0.010, 0.068), HAIR, "head", segments=32)
    add_uv("hair_surface_right_temples_coverage", (0.132, 0.048, 2.108), (0.020, 0.010, 0.066), HAIR, "head", segments=32)
    add_uv("hair_surface_forehead_swept_bang_fill", (-0.040, 0.218, 2.236), (0.118, 0.0042, 0.014), HAIR, "head", segments=56)
    add_uv("hair_surface_forehead_left_taper_fill", (-0.096, 0.219, 2.208), (0.034, 0.0035, 0.010), HAIR, "head", segments=36)
    add_uv("hair_surface_forehead_right_lift_fill", (0.058, 0.212, 2.250), (0.046, 0.0035, 0.010), HAIR, "head", segments=36)

    add_hair_card(
        "hair_card_major_swept_bang_reference_shape",
        [(0.108, 0.228, 2.266), (0.020, 0.232, 2.252), (-0.112, 0.222, 2.216)],
        [0.010, 0.007, 0.0025],
        HAIR,
        "head",
    )
    add_hair_card(
        "hair_card_lower_bang_taper_reference_shape",
        [(0.084, 0.228, 2.228), (-0.004, 0.232, 2.212), (-0.094, 0.220, 2.186)],
        [0.006, 0.0045, 0.002],
        HAIR,
        "head",
    )
    for side, sign in (("L", -1), ("R", 1)):
        add_hair_card(
            f"hair_card_face_framing_soft_lock.{side}",
            [(sign * 0.116, 0.206, 2.174), (sign * 0.136, 0.160, 2.086), (sign * 0.134, 0.100, 1.994)],
            [0.007, 0.0048, 0.0022],
            HAIR,
            "head",
        )

    bang_locks = [
        ("major", (0.108, 0.226, 2.270), (0.022, 0.232, 2.254), (-0.102, 0.221, 2.224), 0.0038),
        ("upper", (0.070, 0.222, 2.286), (-0.012, 0.230, 2.266), (-0.124, 0.218, 2.220), 0.0032),
        ("lower", (0.096, 0.228, 2.236), (0.006, 0.232, 2.216), (-0.098, 0.220, 2.194), 0.0024),
        ("side_drop", (-0.116, 0.214, 2.180), (-0.136, 0.178, 2.092), (-0.138, 0.124, 1.998), 0.0022),
    ]
    for name, root, mid, end, radius in bang_locks:
        add_strand_chain(
            f"hair_sculpted_side_swept_bang_{name}",
            [root, mid, end],
            radius,
            HAIR,
            "head",
            vertices=18,
        )
    for i in range(8):
        t = i / 7
        add_strand_chain(
            f"hair_visible_bang_micro_strand_{i:02d}",
            [
                (0.104 - 0.204 * t, 0.218, 2.282 - 0.004 * math.sin(t * math.pi)),
                (0.032 - 0.158 * t, 0.222, 2.250 - 0.008 * t),
                (-0.052 - 0.090 * t, 0.212, 2.214 - 0.008 * (1.0 - t)),
            ],
            0.00042 if i % 3 else 0.00056,
            HAIR_HI if i % 4 == 0 else HAIR,
            "head",
            vertices=7,
        )

    add_swept_hair_strands(
        "strand_front_swept_hairline_fiber",
        16,
        lambda t, i: (0.132 - 0.270 * t, 0.046 + 0.008 * math.sin(t * math.tau), 2.280 - 0.008 * math.cos(t * math.pi)),
        lambda t, i: (0.078 - 0.210 * t, 0.100 + 0.006 * math.sin((t + 0.15) * math.tau), 2.238 - 0.022 * t),
        lambda t, i: (-0.006 - 0.130 * t, 0.132, 2.188 - 0.018 * (1.0 - t) + 0.004 * math.sin(t * math.pi)),
        0.00048,
        lambda t, i: f"bang.{max(1, min(5, int(t * 5) + 1)):02d}",
    )

    add_swept_hair_strands(
        "strand_crown_part_surface_fiber",
        54,
        lambda t, i: (-0.140 + 0.280 * t, -0.064 + 0.008 * math.sin(t * math.tau), 2.292 - 0.006 * abs(t - 0.5)),
        lambda t, i: (-0.112 + 0.230 * t, 0.014 + 0.014 * math.sin((t + 0.2) * math.tau), 2.264),
        lambda t, i: (-0.080 + 0.150 * t, 0.094, 2.224 - 0.012 * math.cos(t * math.pi)),
        0.00058,
        lambda t, i: "head",
    )

    for i in range(10):
        t = i / 9
        root_x = -0.134 + 0.268 * t
        end_x = -0.154 + 0.284 * t
        sweep_bias = math.sin((t - 0.18) * math.pi)
        add_strand_chain(
            f"hair_visible_swept_bang_lock_bundle_{i:02d}",
            [
                (root_x, 0.036, 2.292 - 0.008 * math.cos(t * math.tau)),
                (root_x * 0.84 - 0.030, 0.110, 2.260 - 0.012 * t),
                (end_x - 0.015 * sweep_bias, 0.160, 2.208 - 0.016 * (1.0 - t)),
            ],
            0.0012 if i % 3 else 0.0015,
            HAIR,
            f"bang.{max(1, min(5, int(t * 5) + 1)):02d}",
            vertices=12,
        )

    for i in range(12):
        t = i / 11
        root_x = -0.145 + 0.285 * t
        root = (
            root_x,
            0.080 + 0.010 * math.sin(t * math.tau),
            2.302 - 0.010 * math.cos(t * math.tau),
        )
        mid = (
            -0.118 + 0.244 * t,
            0.142 + 0.010 * math.sin((t + 0.2) * math.tau),
            2.250 - 0.040 * t,
        )
        end = (
            -0.168 + 0.290 * t,
            0.172,
            2.176 - 0.052 * (1.0 - t) + 0.010 * math.sin(t * math.pi),
        )
        bone_index = max(1, min(5, int(t * 5) + 1))
        mat_for_strand = HAIR_HI if i % 4 == 0 else HAIR
        add_strand_chain(
            f"strand_bang_reference_sweep_{i:02d}",
            [root, mid, end],
            0.00062 if i % 4 else 0.00082,
            mat_for_strand,
            f"bang.{bone_index:02d}",
            vertices=7,
        )

    for i in range(18):
        t = i / 17
        x = -0.134 + 0.268 * t
        add_strand_chain(
            f"strand_crown_surface_flow_{i:02d}",
            [
                (x, -0.026 + 0.010 * math.sin(t * math.tau), 2.328),
                (x * 0.80 - 0.016, 0.042 + 0.016 * math.sin((t + 0.15) * math.tau), 2.294),
                (x * 0.50 - 0.032, 0.122, 2.232 - 0.012 * math.cos(t * math.pi)),
            ],
            0.00068 if i % 6 else 0.00092,
            HAIR_HI if i % 5 == 0 else HAIR,
            "head",
            vertices=7,
        )

    for i in range(26):
        t = i / 25
        side_sweep = -1.0 + 2.0 * t
        add_strand_chain(
            f"strand_back_scalp_to_tie_flow_{i:02d}",
            [
                (0.120 * side_sweep, -0.076, 2.258 - 0.010 * abs(side_sweep)),
                (0.145 * side_sweep, -0.096, 2.112 - 0.018 * abs(side_sweep)),
                (0.184 * side_sweep, -0.052, 1.970),
            ],
            0.00072,
            HAIR_HI if i % 7 == 0 else HAIR,
            "head",
            vertices=7,
        )

    for side, sign in (("L", -1), ("R", 1)):
        add_uv(f"hair_pigtail_root_shadow_under_strands.{side}", (0.150 * sign, -0.052, 2.010), (0.012, 0.009, 0.022), HAIR, f"pigtail.{side}.01", segments=24)
        add_cyl(f"hair_pigtail_tie_ribbon.{side}", (0.170 * sign, -0.068, 1.994), 0.0038, 0.026, HAIR_HI, f"pigtail.{side}.01", rot=(math.pi / 2, 0, math.pi / 2), vertices=18)
        add_limb(f"hair_pigtail_gather_bridge.{side}", (0.150 * sign, -0.052, 2.010), (0.228 * sign, -0.112, 1.942), 0.0040, HAIR, f"pigtail.{side}.01", vertices=16)
        add_uv(f"hair_pigtail_core_shadow_under_strands.{side}", (0.246 * sign, -0.128, 1.924), (0.028, 0.018, 0.037), HAIR, f"pigtail.{side}.02", segments=40)
        add_uv(f"hair_pigtail_tapered_tip_shadow.{side}", (0.278 * sign, -0.128, 1.886), (0.010, 0.0065, 0.014), HAIR, f"pigtail.{side}.03", segments=24)
        add_limb(
            f"hair_side_smooth_lock_over_fibers.{side}",
            (sign * 0.118, 0.196, 2.166),
            (sign * 0.136, 0.126, 2.006),
            0.0016,
            HAIR,
            "head",
            vertices=10,
        )

        for i in range(18):
            angle = -1.40 + (2.80 * i / 17)
            sweep = math.sin(angle)
            lift = math.cos(angle)
            root = (
                sign * (0.170 + 0.004 * math.sin(i * 0.47)),
                -0.068 + 0.003 * math.cos(i * 0.37),
                1.994 + 0.005 * math.sin(i * 0.23),
            )
            mid = (
                sign * (0.242 + 0.016 * sweep),
                -0.126 + 0.006 * math.sin(angle * 1.7),
                1.924 + 0.018 * lift,
            )
            end = (
                sign * (0.278 + 0.012 * sweep),
                -0.128 + 0.005 * math.cos(angle),
                1.886 + 0.008 * lift,
            )
            add_strand_chain(
                f"hair_pigtail_visible_lock_bundle_{i:02d}.{side}",
                [root, mid, end],
                0.0016 if i % 3 else 0.0021,
                HAIR_HI if i % 4 == 0 else HAIR,
                f"pigtail.{side}.03",
                vertices=10,
            )

        for i in range(58):
            angle = -1.45 + (2.90 * i / 57)
            sweep = math.sin(angle)
            lift = math.cos(angle)
            root = (
                sign * (0.170 + 0.006 * math.sin(i * 0.41)),
                -0.068 + 0.003 * math.cos(i * 0.37),
                1.994 + 0.006 * math.sin(i * 0.23),
            )
            mid = (
                sign * (0.242 + 0.014 * sweep),
                -0.126 + 0.008 * math.sin(angle * 1.7),
                1.924 + 0.016 * lift,
            )
            end = (
                sign * (0.278 + 0.010 * sweep),
                -0.128 + 0.004 * math.cos(angle),
                1.886 + 0.006 * lift,
            )
            add_strand_chain(
                f"strand_pigtail_hair_fiber_{i:02d}.{side}",
                [root, mid, end],
                0.00058 if i % 4 else 0.00076,
                HAIR_HI if i % 4 == 0 else HAIR,
                f"pigtail.{side}.03",
                vertices=7,
            )

        for i in range(6):
            z_start = 2.196 - i * 0.010
            add_strand_chain(
                f"strand_face_framing_lock_{i:02d}.{side}",
                [
                    (sign * (0.122 + i * 0.002), 0.188, z_start),
                    (sign * (0.140 + i * 0.0015), 0.142, 2.050 - i * 0.008),
                    (sign * (0.150 + i * 0.001), 0.086, 1.944 - i * 0.006),
                ],
                0.00046,
                HAIR_HI if i % 3 == 0 else HAIR,
                "head",
                vertices=7,
            )


def build_wardrobe():
    add_cube("civilian_jacket_left_panel_cloth_proxy", (-0.09, 0.18, 1.5), (0.055, 0.025, 0.35), JACKET, "chest")
    add_cube("civilian_jacket_right_panel_cloth_proxy", (0.09, 0.18, 1.5), (0.055, 0.025, 0.35), JACKET, "chest")
    add_cube("civilian_shirt_floral_mark", (0.045, 0.205, 1.58), (0.035, 0.006, 0.035), BLUSH, "chest")
    add_cube("sleepwear_lavender_top_hidden", (0, 0.215, 1.48), (0.255, 0.02, 0.36), SLEEP, "chest")
    add_cube("sleepwear_lavender_pants_hidden", (0, 0.045, 0.58), (0.19, 0.02, 0.42), SLEEP, "hips")
    add_cube("swimwear_modest_one_piece_hidden", (0, 0.225, 1.28), (0.235, 0.022, 0.48), SWIM, "chest")
    add_cube("hero_ladybug_suit_top_hidden", (0, 0.23, 1.45), (0.255, 0.024, 0.42), RED, "chest")
    add_cube("hero_ladybug_mask_hidden", (0, 0.275, 2.31), (0.18, 0.008, 0.045), RED, "head")
    for x, z in [(-0.08, 1.56), (0.1, 1.35), (-0.12, 0.68), (0.13, 0.36)]:
        add_uv("hero_ladybug_black_spot_hidden", (x, 0.255, z), (0.025, 0.006, 0.025), SPOT, "chest" if z > 1 else "hips")


def add_shape_keys():
    for obj, _ in created_meshes:
        if not obj.name.startswith(("reference_blink_upper_lid", "shared_smile_lip", "shared_eye_white")):
            continue
        obj.shape_key_add(name="Basis")
        if obj.name.startswith("reference_blink_upper_lid"):
            kb = obj.shape_key_add(name="blink_closed")
            for v in kb.data:
                v.co.z -= 0.021
                v.co.y += 0.0008
        if "lip" in obj.name:
            for key in ("viseme_AA", "viseme_EE", "viseme_OO", "viseme_MBP", "smile_soft"):
                kb = obj.shape_key_add(name=key)
                for v in kb.data:
                    if key == "viseme_AA":
                        v.co.z -= 0.025
                    elif key == "viseme_EE":
                        v.co.x *= 1.18
                    elif key == "viseme_OO":
                        v.co.x *= 0.72
                        v.co.z *= 1.08


def key_bone(arm, frame, bone_name, rot=(0, 0, 0), loc=None):
    pb = arm.pose.bones[bone_name]
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = rot
    if loc:
        pb.location = loc
        pb.keyframe_insert("location", frame=frame)
    pb.keyframe_insert("rotation_euler", frame=frame)


def make_action(arm, name, frames):
    action = bpy.data.actions.new(name)
    arm.animation_data_create()
    arm.animation_data.action = action
    for frame, values in frames.items():
        for bone_name, rot in values.items():
            key_bone(arm, frame, bone_name, rot)
    action.use_fake_user = True
    return action


def animate_shape_keys(name, keyframes):
    action = bpy.data.actions.new(name)
    for obj, _ in created_meshes:
        if not obj.data.shape_keys:
            continue
        obj.data.shape_keys.animation_data_create()
        obj.data.shape_keys.animation_data.action = action
        for key_name, frames in keyframes.items():
            kb = obj.data.shape_keys.key_blocks.get(key_name)
            if not kb:
                continue
            for frame, value in frames:
                kb.value = value
                kb.keyframe_insert("value", frame=frame)
    action.use_fake_user = True
    return action


def make_animations(arm):
    make_action(arm, "idle", {
        1: {"chest": (0, 0, 0), "head": (0, 0, 0), "pigtail.L.03": (0, 0, 0.03), "pigtail.R.03": (0, 0, -0.03)},
        24: {"chest": (0.025, 0, 0), "head": (-0.015, 0, 0.015), "pigtail.L.03": (0.04, 0, 0.08), "pigtail.R.03": (0.04, 0, -0.08)},
        48: {"chest": (0, 0, 0), "head": (0, 0, 0), "pigtail.L.03": (0, 0, 0.03), "pigtail.R.03": (0, 0, -0.03)},
    })
    walk = {}
    for f, s in [(1, 1), (10, -1), (20, 1), (30, -1), (40, 1)]:
        walk[f] = {
            "thigh.L": (0.38 * s, 0, 0.04),
            "shin.L": (-0.55 if s > 0 else 0.18, 0, 0),
            "foot.L": (-0.16 * s, 0, 0),
            "thigh.R": (-0.38 * s, 0, -0.04),
            "shin.R": (0.18 if s > 0 else -0.55, 0, 0),
            "foot.R": (0.16 * s, 0, 0),
            "upper_arm.L": (-0.065 * s, 0, 0.012),
            "upper_arm.R": (0.065 * s, 0, -0.012),
            "forearm.L": (-0.045, 0.0, 0.008 * s),
            "forearm.R": (-0.045, 0.0, -0.008 * s),
            "hand.L": (0.012 * s, 0, -0.016 * s),
            "hand.R": (-0.012 * s, 0, 0.016 * s),
            "chest": (0.010, 0.014 * s, 0),
            "head": (-0.012, -0.010 * s, 0),
            "pigtail.L.03": (0.035, 0.014 * s, 0.075 * s),
            "pigtail.R.03": (0.035, -0.014 * s, 0.075 * s),
        }
    make_action(arm, "walk", walk)
    make_action(arm, "wave", {
        1: {"upper_arm.R": (-0.55, 0, -0.9), "forearm.R": (-0.35, 0, -0.25), "hand.R": (0, 0, 0.15)},
        12: {"upper_arm.R": (-0.65, 0, -1.1), "forearm.R": (-0.15, 0, 0.35), "hand.R": (0, 0, -0.3)},
        24: {"upper_arm.R": (-0.55, 0, -0.9), "forearm.R": (-0.35, 0, -0.25), "hand.R": (0, 0, 0.15)},
    })
    make_action(arm, "use_computer", {
        1: {"upper_arm.L": (-0.38, 0, 0.18), "upper_arm.R": (-0.38, 0, -0.18), "forearm.L": (-0.8, 0, 0.1), "forearm.R": (-0.8, 0, -0.1), "head": (0.12, 0, 0)},
        30: {"upper_arm.L": (-0.4, 0, 0.2), "upper_arm.R": (-0.4, 0, -0.2), "forearm.L": (-0.92, 0, 0.04), "forearm.R": (-0.92, 0, -0.04), "head": (0.08, 0.04, 0)},
    })
    make_action(arm, "talking", {
        1: {"jaw": (0, 0, 0), "head": (0, 0, 0)},
        8: {"jaw": (0.22, 0, 0), "head": (-0.04, 0.03, 0)},
        16: {"jaw": (0.04, 0, 0), "head": (0.02, -0.02, 0)},
        24: {"jaw": (0.18, 0, 0), "head": (0, 0.02, 0)},
        32: {"jaw": (0, 0, 0), "head": (0, 0, 0)},
    })
    make_action(arm, "blink", {
        1: {"eyelid.L": (0, 0, 0), "eyelid.R": (0, 0, 0)},
        8: {"eyelid.L": (0, 0, 0), "eyelid.R": (0, 0, 0)},
        10: {"eyelid.L": (0.45, 0, 0), "eyelid.R": (0.45, 0, 0)},
        13: {"eyelid.L": (0, 0, 0), "eyelid.R": (0, 0, 0)},
        48: {"eyelid.L": (0, 0, 0), "eyelid.R": (0, 0, 0)},
    })
    animate_shape_keys("blink_reference_lids", {
        "blink_closed": [(1, 0), (8, 0), (10, 1), (12, 1), (14, 0), (48, 0)],
    })
    animate_shape_keys("viseme_talking", {
        "viseme_AA": [(1, 0), (8, 1), (14, 0)],
        "viseme_EE": [(12, 0), (18, 1), (24, 0)],
        "viseme_OO": [(22, 0), (28, 1), (32, 0)],
        "viseme_MBP": [(30, 0), (34, 1), (38, 0)],
    })


def hide_non_default_layers():
    # Keep wardrobe meshes exportable. The world runtime hides/shows named layers.
    return
    for obj, _ in created_meshes:
        if obj.name.startswith(("sleepwear_", "swimwear_", "hero_")):
            obj.hide_viewport = True
            obj.hide_render = True


def remove_export_junk_objects():
    global created_meshes
    junk_prefixes = ("Icosphere",)
    kept = []
    for obj, bone in created_meshes:
        mesh_name = obj.data.name if getattr(obj, "data", None) else ""
        if obj.name.startswith(junk_prefixes) or mesh_name.startswith(junk_prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        kept.append((obj, bone))
    created_meshes = kept
    for obj in list(bpy.context.scene.objects):
        mesh_name = obj.data.name if getattr(obj, "data", None) else ""
        if obj.type == "MESH" and (obj.name.startswith(junk_prefixes) or mesh_name.startswith(junk_prefixes)):
            bpy.data.objects.remove(obj, do_unlink=True)
    for obj in list(bpy.data.objects):
        mesh_name = obj.data.name if getattr(obj, "data", None) else ""
        if obj.type == "MESH" and (obj.name.startswith(junk_prefixes) or mesh_name.startswith(junk_prefixes)):
            bpy.data.objects.remove(obj, do_unlink=True)


def export_glb():
    if AVATAR.exists():
        backup = AVATAR.with_name(f"avatar_before_v6_{datetime.now().strftime('%Y%m%d_%H%M%S')}.glb")
        shutil.copy2(AVATAR, backup)
    bpy.ops.object.select_all(action="DESELECT")
    for obj, _ in created_meshes:
        if obj.name in bpy.data.objects:
            obj.select_set(True)
    arm = bpy.data.objects.get("Marinette_Rig_v6")
    if arm:
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(
        filepath=str(AVATAR),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_animations=True,
        export_nla_strips=False,
        export_all_influences=True,
    )


def preflight_body_policy() -> dict:
    gate = enforce_body_policy(
        project_root=ROOT,
        candidate_id=CANDIDATE_ID,
        body_treatment="non_adult_doll_safe",
        expected_maturity_classes={"non_adult_doll_safe"},
        require_asset_evidence=False,
    )
    external_head = find_external_head_source()
    if external_head:
        enforce_body_policy(
            project_root=ROOT,
            candidate_id=CANDIDATE_ID,
            body_treatment="non_adult_doll_safe",
            selected_asset_paths=[external_head],
            declared_asset_records=[{
                "id": f"legacy_character_reference_head:{external_head.name}",
                "filename": external_head.name,
                "reference_only": True,
                "copy_as_avatar_body_allowed": False,
            }],
            expected_maturity_classes={"non_adult_doll_safe"},
            require_asset_evidence=True,
        )
    generic_body = find_generic_body_source() if USE_ACTIVE_GENERIC_BODY_SURFACE else None
    if generic_body:
        enforce_body_policy(
            project_root=ROOT,
            candidate_id=CANDIDATE_ID,
            body_treatment="non_adult_doll_safe",
            selected_asset_paths=[generic_body],
            declared_asset_records=[{
                "id": f"legacy_generic_adult_body:{generic_body.name}",
                "filename": generic_body.name,
                "adult_only": True,
                "allowed_for_non_adult": False,
            }],
            expected_maturity_classes={"non_adult_doll_safe"},
            require_asset_evidence=True,
        )
    return gate


def main():
    body_policy_gate = preflight_body_policy()
    clear_scene()
    arm = make_rig()
    build_body()
    build_hair()
    add_anatomy_body_shell("active_neutral_smooth_body_shell", SKIN)
    remove_torso_proxy_surface()
    # The active body export stays wardrobe-free. Clothes are separate avatar-builder attachments.
    external_body_source = import_generic_body_surface() if USE_ACTIVE_GENERIC_BODY_SURFACE else None
    if external_body_source and USE_ACTIVE_GENERIC_BODY_SURFACE:
        remove_core_body_proxy_surface()
    remove_procedural_head_surface()
    external_head_source = import_reference_head_layer()
    build_reference_blink_layer()
    generic_body_reference_candidate = find_generic_body_source()
    add_shape_keys()
    bind_to_rig(arm)
    hide_non_default_layers()
    make_animations(arm)
    remove_export_junk_objects()
    export_glb()
    METADATA.write_text(json.dumps({
        "version": "v6_reference_head_smooth_neutral_body_production_hands_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "body_policy_validation": body_policy_gate,
        "source": "v6 locomotion rig with downloaded Marinette GLB head, smooth neutral body shell, and production-hand bridge layer",
        "external_head_source": external_head_source,
        "external_body_source": external_body_source,
        "generic_body_reference_candidate": str(generic_body_reference_candidate) if generic_body_reference_candidate else None,
        "external_rig_reference_sources": collect_existing_sources(EXTERNAL_RIG_REFERENCE_SOURCES),
        "generic_body_reference_sources": collect_existing_sources(GENERIC_BODY_REFERENCE_SOURCES),
        "world_furniture_reference_sources": collect_existing_sources(WORLD_FURNITURE_REFERENCE_SOURCES),
        "hand_reference_sources": collect_existing_sources(HAND_REFERENCE_SOURCES),
        "reference_images": collect_reference_images(),
        "notes": [
            "Clean armature with knees, elbows, hands, fifteen finger chains per side, jaw, pigtail, and bang proxy bones.",
            "The visible export is a neutral skin-tone base body with a smooth torso/hip shell, v6 arm/hand/finger controls, one skinned hand surface per side, and the downloaded reference head, eyes, lashes, mouth, and hair bound onto the v6 skeleton.",
            "The old bead-hand palm, finger cylinders, and fingertip spheres have been replaced by a single relaxed hand surface per side weighted to the existing hand and finger bones.",
            "A visible reference blink layer now exists after the downloaded head import, so the blink action has exported eyelid geometry instead of empty bones.",
            "Downloaded generic rigged bodies are tracked as anatomy references only on this pass because their rest pose and armature need retargeting before they can safely drive the active v6 locomotion body.",
            "Wardrobe geometry is intentionally not baked into the base body; clothing should be separate attachable/skinned layers.",
            "The old procedural face and hair proxy layer is removed before export so the better reference mesh is not hidden by simple geometry.",
            "The downloaded Ladybug rigged model is tracked as a retargeting and proportion reference, not as the active neutral visible body because it carries suit and mask geometry.",
            "The staged rigged hand and rigged arm GLBs are now recorded as the production hand retarget references for avatar-builder bodies.",
            "The downloaded generic female body is kept as a scale/proportion guide while clothes remain separate wardrobe layers.",
            "The 56 Harbour Terrace furniture file is tracked for the later house realism pass and needs scale normalization/extraction before placement.",
            "Avatar-builder bodies should use the reference_images list for face landmarks, skin tone calibration, hairline placement, and hairstyle selection.",
            "This is a stable reusable foundation, not a final photoreal mesh sculpt."
        ],
        "generator_upgrade": {
            "body_strategy": "reuse the v6 locomotion skeleton, keep downloaded neutral bodies as retarget references, and export a single smooth neutral torso/hip shell with v6 arms, hands, fingers, legs, and feet",
            "head_strategy": "use the downloaded show-model head layer as the current visual target while the builder grows a real landmark-fitted mesh pipeline",
            "hair_strategy": "use the downloaded hair shell for silhouette now; future layers should replace it with skinned curves/cards plus strand physics",
            "hand_strategy": "replace visible bead hands with one skinned relaxed hand mesh per side, weighted to hand and finger bones, and use staged rigged hand/arm GLBs as retarget references",
            "rigged_reference_strategy": "use the 153-bone Ladybug download for retargeting tests and hand/foot control comparison after the neutral body surface is stable",
            "generic_body_reference_strategy": "use the downloaded rigged base body for neutral anatomy/proportion targets while keeping clothes as separate wardrobe layers",
            "furniture_reference_strategy": "extract normalized furniture meshes from the Harbour Terrace pack during the home-world realism pass instead of importing the whole architecture-scale scene",
            "reference_reconstruction_required": "the next avatar-builder step should replace this primitive proxy with a real one-piece landmark-fitted head mesh, albedo, normals, facial loops, and skinned curve/card hair",
            "next_required_layer": "add object-level finger colliders, IK grip target solving, and foot IK/contact locks after the production hand surface is validated in runtime"
        },
        "wardrobe": {
            "visible_in_base_glb": [],
            "planned_external_layers": ["civilian outfit", "sleepwear", "swimwear", "Ladybug suit bound to earring transformation tokens"]
        },
        "hair_states": {
            "default": {
                "mode": "downloaded_reference_tied_style",
                "bones": ["head"],
                "runtime_goal": "stable show-model silhouette now; later split into simulated strand groups for pigtails, bangs, and hair-down styles"
            },
            "hair_down": {
                "mode": "future_attachment_layer_from_reference_landmarks",
                "runtime_goal": "replace tied pigtail strand groups with longer blue-black strand strips when showering, swimming, or changing style"
            },
            "wet": {
                "mode": "future_material_state",
                "material_reference": HAIR_WET.name,
                "runtime_goal": "darker glossy strands, heavier downward spring, reduced flyaway motion"
            }
        },
        "hair_collision_targets": {
            "finger_can_thread": ["future_curve_bang_strands", "future_curve_side_locks", "future_curve_pigtail_groups"],
            "future_colliders": ["head capsule", "neck capsule", "shoulder capsules", "hand and finger capsules"],
            "runtime_rule": "fingers should push strands aside; strands should return with damped spring motion"
        },
        "animation_clips": [a.name for a in bpy.data.actions],
        "mesh_count": len(created_meshes),
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
