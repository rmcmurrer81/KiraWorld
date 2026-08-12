"""Create a staged robe/towel soft-goods proof model.

This is a real Blender GLB proof for the wardrobe lab. It is not an approved
runtime cloth solver. Its job is to give the Avatar Builder and World Builder
visible, named mesh states to grade: hanging robe, worn tied robe, folded robe,
towel on rack, folded towels, and wrapped towel.

Run:
  "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background --python tools/create_robe_towel_soft_goods_proof_20260714.py
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

import bpy  # type: ignore
from mathutils import Vector  # type: ignore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "robe_towel_soft_goods_proof_20260714_170000"
OUT_DIR = PROJECT_ROOT / "Avatar" / "avatar_builder" / "wardrobe_training" / "proof_runs" / RUN_ID
MODEL_OUT = OUT_DIR / "robe_towel_soft_goods_states.glb"
MANIFEST_OUT = OUT_DIR / "robe_towel_soft_goods_states_manifest.json"
STATE_MACHINE_OUT = OUT_DIR / "robe_towel_item_state_machine.json"
INDEX_OUT = OUT_DIR / "index.html"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def clear_scene() -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)
    for curve in list(bpy.data.curves):
        bpy.data.curves.remove(curve)


def material(name: str, color: tuple[float, float, float, float], roughness: float = 0.75) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = color[3]
    if color[3] < 1.0:
        mat.blend_method = "BLEND"
        mat.show_transparent_back = True
    return mat


def add_cube(
    name: str,
    loc: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    rot: tuple[float, float, float] = (0, 0, 0),
    bevel: float = 0.0,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new(f"{name}_soft_bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 4
        obj.modifiers.new(f"{name}_weighted_normals", "WEIGHTED_NORMAL")
    return obj


def add_soft_panel(
    name: str,
    center: tuple[float, float, float],
    width: float,
    height: float,
    mat: bpy.types.Material,
    *,
    zrot: float = 0.0,
    fold_depth: float = 0.018,
    curl: float = 0.0,
    thickness: float = 0.010,
    columns: int = 10,
    rows: int = 14,
) -> bpy.types.Object:
    verts = []
    faces = []
    cx, cy, cz = center
    cr = math.cos(zrot)
    sr = math.sin(zrot)
    for row in range(rows + 1):
        v = row / rows
        for col in range(columns + 1):
            u = col / columns
            lx = (u - 0.5) * width
            lz = (v - 0.5) * height
            edge_pull = (abs(u - 0.5) * 2.0) ** 2
            wave = math.sin(u * math.pi * 4.0 + v * math.pi * 1.25) * fold_depth
            sag = -0.035 * (1.0 - v) * (0.35 + edge_pull * 0.65)
            y = cy + wave + curl * (u - 0.5) ** 2
            rx = lx * cr - lz * sr
            rz = lx * sr + lz * cr
            verts.append((cx + rx, y, cz + rz + sag))
    stride = columns + 1
    for row in range(rows):
        for col in range(columns):
            a = row * stride + col
            faces.append((a, a + 1, a + stride + 1, a + stride))
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    solidify = obj.modifiers.new(f"{name}_cloth_thickness", "SOLIDIFY")
    solidify.thickness = thickness
    bevel = obj.modifiers.new(f"{name}_soft_edge_bevel", "BEVEL")
    bevel.width = thickness * 0.55
    bevel.segments = 3
    obj.modifiers.new(f"{name}_weighted_normals", "WEIGHTED_NORMAL")
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def add_cylinder(
    name: str,
    loc: tuple[float, float, float],
    radius: float,
    depth: float,
    mat: bpy.types.Material,
    vertices: int = 32,
    rot: tuple[float, float, float] = (0, 0, 0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def add_sphere(
    name: str,
    loc: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    segments: int = 32,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=max(8, segments // 2), radius=1.0, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def add_curve(
    name: str,
    points: list[tuple[float, float, float]],
    mat: bpy.types.Material,
    bevel_depth: float = 0.012,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(name, type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 3
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 4
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points):
        point.co = (co[0], co[1], co[2], 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def add_empty(name: str, loc: tuple[float, float, float], size: float = 0.05) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "SPHERE"
    obj.empty_display_size = size
    obj.location = loc
    bpy.context.collection.objects.link(obj)
    return obj


def make_tile_wall(prefix: str, x: float, y: float, z: float, mat_wall: bpy.types.Material, mat_line: bpy.types.Material) -> None:
    add_cube(f"{prefix}_bathroom_tile_wall", (x, y, z + 0.95), (1.35, 0.035, 0.95), mat_wall, bevel=0.003)
    for i in range(7):
        px = x - 1.15 + i * 0.38
        add_cube(f"{prefix}_tile_vertical_grout_{i}", (px, y - 0.037, z + 0.95), (0.006, 0.004, 0.92), mat_line)
    for i in range(6):
        pz = z + 0.25 + i * 0.27
        add_cube(f"{prefix}_tile_horizontal_grout_{i}", (x, y - 0.038, pz), (1.32, 0.004, 0.006), mat_line)


def make_hanging_robe(origin: Vector, mats: dict[str, bpy.types.Material]) -> list[str]:
    names: list[str] = []
    make_tile_wall("robe_hanging", origin.x, origin.y + 0.22, 0.0, mats["tile"], mats["grout"])
    hook = add_cylinder(
        "bathroom_wall_hook_for_shared_white_robe_v1",
        (origin.x, origin.y - 0.02, 1.72),
        0.035,
        0.16,
        mats["metal"],
        rot=(math.radians(90), 0, 0),
    )
    names.append(hook.name)
    names.append(add_empty("robe_hook_loop_anchor_to_wall_hook", (origin.x, origin.y - 0.11, 1.68), 0.035).name)
    names.append(add_curve("shared_white_bath_robe_v1_hook_loop", [(origin.x - 0.06, origin.y - 0.12, 1.67), (origin.x, origin.y - 0.15, 1.73), (origin.x + 0.06, origin.y - 0.12, 1.67)], mats["cloth_edge"], 0.009).name)
    robe_parts = [
        add_soft_panel("robe_hanging_back_panel_soft_mesh", (origin.x, origin.y - 0.145, 1.18), 0.58, 1.08, mats["robe"], fold_depth=0.020, curl=0.018),
        add_soft_panel("robe_hanging_left_front_panel_soft_mesh", (origin.x - 0.15, origin.y - 0.185, 1.10), 0.27, 0.96, mats["robe"], zrot=math.radians(-4), fold_depth=0.018, curl=0.012),
        add_soft_panel("robe_hanging_right_front_panel_soft_mesh", (origin.x + 0.15, origin.y - 0.185, 1.10), 0.27, 0.96, mats["robe"], zrot=math.radians(4), fold_depth=0.018, curl=0.012),
        add_soft_panel("robe_hanging_left_sleeve_opening_soft_mesh", (origin.x - 0.48, origin.y - 0.18, 1.17), 0.16, 0.70, mats["robe"], zrot=math.radians(-18), fold_depth=0.014, curl=0.016),
        add_soft_panel("robe_hanging_right_sleeve_opening_soft_mesh", (origin.x + 0.48, origin.y - 0.18, 1.17), 0.16, 0.70, mats["robe"], zrot=math.radians(18), fold_depth=0.014, curl=0.016),
        add_soft_panel("robe_hanging_shawl_collar_left", (origin.x - 0.10, origin.y - 0.215, 1.43), 0.11, 0.39, mats["cloth_edge"], zrot=math.radians(-22), fold_depth=0.006, thickness=0.014),
        add_soft_panel("robe_hanging_shawl_collar_right", (origin.x + 0.10, origin.y - 0.215, 1.43), 0.11, 0.39, mats["cloth_edge"], zrot=math.radians(22), fold_depth=0.006, thickness=0.014),
    ]
    for obj in robe_parts:
        names.append(obj.name)
    names.append(add_curve("robe_hanging_loose_belt_left_end", [(origin.x - 0.10, origin.y - 0.23, 1.02), (origin.x - 0.28, origin.y - 0.26, 0.88), (origin.x - 0.18, origin.y - 0.24, 0.72)], mats["cloth_edge"], 0.014).name)
    names.append(add_curve("robe_hanging_loose_belt_right_end", [(origin.x + 0.07, origin.y - 0.23, 1.02), (origin.x + 0.26, origin.y - 0.27, 0.91), (origin.x + 0.18, origin.y - 0.25, 0.70)], mats["cloth_edge"], 0.014).name)
    return names


def make_adult_fit_proxy(origin: Vector, mats: dict[str, bpy.types.Material]) -> list[str]:
    names: list[str] = []
    proxy = material("transparent_adult_fit_collision_proxy", (0.70, 0.78, 0.85, 0.28), 0.9)
    names.append(add_sphere("adult_fit_proxy_torso_collision_not_character_body", (origin.x, origin.y, 1.18), (0.20, 0.13, 0.34), proxy, 32).name)
    names.append(add_sphere("adult_fit_proxy_head_collision", (origin.x, origin.y - 0.01, 1.68), (0.12, 0.10, 0.14), proxy, 32).name)
    for side, sign in (("left", -1), ("right", 1)):
        names.append(add_cylinder(f"adult_fit_proxy_{side}_arm_collision", (origin.x + sign * 0.33, origin.y, 1.22), 0.035, 0.42, proxy, rot=(0, math.radians(62 * sign), 0)).name)
    return names


def make_worn_robe(origin: Vector, mats: dict[str, bpy.types.Material]) -> list[str]:
    names = make_adult_fit_proxy(origin, mats)
    worn_parts = [
        add_soft_panel("robe_worn_tied_back_panel_follows_spine", (origin.x, origin.y + 0.070, 1.13), 0.47, 0.94, mats["robe"], fold_depth=0.010, curl=0.020),
        add_soft_panel("robe_worn_tied_left_front_panel_body_fit", (origin.x - 0.085, origin.y - 0.120, 1.12), 0.22, 0.92, mats["robe"], zrot=math.radians(-4), fold_depth=0.012, curl=0.022),
        add_soft_panel("robe_worn_tied_right_front_panel_body_fit", (origin.x + 0.085, origin.y - 0.125, 1.12), 0.22, 0.92, mats["robe"], zrot=math.radians(4), fold_depth=0.012, curl=0.022),
        add_soft_panel("robe_worn_tied_left_sleeve_follows_left_arm", (origin.x - 0.36, origin.y - 0.035, 1.19), 0.13, 0.54, mats["robe"], zrot=math.radians(-63), fold_depth=0.009, curl=0.012),
        add_soft_panel("robe_worn_tied_right_sleeve_follows_right_arm", (origin.x + 0.36, origin.y - 0.035, 1.19), 0.13, 0.54, mats["robe"], zrot=math.radians(63), fold_depth=0.009, curl=0.012),
        add_soft_panel("robe_worn_tied_shawl_collar_left", (origin.x - 0.08, origin.y - 0.155, 1.42), 0.10, 0.36, mats["cloth_edge"], zrot=math.radians(-18), fold_depth=0.005, thickness=0.014),
        add_soft_panel("robe_worn_tied_shawl_collar_right", (origin.x + 0.08, origin.y - 0.155, 1.42), 0.10, 0.36, mats["cloth_edge"], zrot=math.radians(18), fold_depth=0.005, thickness=0.014),
        add_cube("robe_worn_left_pocket", (origin.x - 0.16, origin.y - 0.155, 0.92), (0.075, 0.014, 0.08), mats["cloth_edge"], bevel=0.01),
        add_cube("robe_worn_right_pocket", (origin.x + 0.16, origin.y - 0.155, 0.92), (0.075, 0.014, 0.08), mats["cloth_edge"], bevel=0.01),
    ]
    for obj in worn_parts:
        names.append(obj.name)
    names.append(add_curve("robe_worn_tied_belt_left_loop_to_knot", [(origin.x - 0.23, origin.y - 0.16, 1.05), (origin.x - 0.08, origin.y - 0.19, 1.02), (origin.x, origin.y - 0.20, 1.03)], mats["cloth_edge"], 0.014).name)
    names.append(add_curve("robe_worn_tied_belt_right_loop_to_knot", [(origin.x + 0.23, origin.y - 0.16, 1.05), (origin.x + 0.08, origin.y - 0.19, 1.02), (origin.x, origin.y - 0.20, 1.03)], mats["cloth_edge"], 0.014).name)
    names.append(add_curve("robe_worn_tied_belt_dangling_ends", [(origin.x, origin.y - 0.22, 1.02), (origin.x - 0.03, origin.y - 0.24, 0.83), (origin.x + 0.05, origin.y - 0.23, 0.70)], mats["cloth_edge"], 0.012).name)
    names.append(add_empty("robe_worn_belt_knot_anchor", (origin.x, origin.y - 0.22, 1.03), 0.035).name)
    return names


def make_folded_robe(origin: Vector, mats: dict[str, bpy.types.Material]) -> list[str]:
    names: list[str] = []
    names.append(add_cube("robe_folded_storage_soft_bundle_base", (origin.x, origin.y, 0.72), (0.34, 0.24, 0.09), mats["robe"], bevel=0.035).name)
    names.append(add_cube("robe_folded_storage_visible_collar_fold", (origin.x - 0.06, origin.y - 0.03, 0.83), (0.22, 0.045, 0.035), mats["cloth_edge"], rot=(0, 0, math.radians(-9)), bevel=0.012).name)
    names.append(add_curve("robe_folded_storage_belt_wrapped_around_bundle", [(origin.x - 0.30, origin.y - 0.03, 0.84), (origin.x, origin.y - 0.06, 0.86), (origin.x + 0.30, origin.y - 0.03, 0.84)], mats["cloth_edge"], 0.011).name)
    return names


def make_towels(origin: Vector, mats: dict[str, bpy.types.Material]) -> list[str]:
    names: list[str] = []
    add_cube("towel_rack_bathroom_wall", (origin.x, origin.y + 0.20, 1.15), (0.95, 0.030, 0.72), mats["tile"], bevel=0.003)
    names.append(add_cylinder("shared_white_bath_towel_v1_rack_bar", (origin.x, origin.y - 0.05, 1.42), 0.018, 0.74, mats["metal"], rot=(0, math.radians(90), 0)).name)
    names.append(add_soft_panel("shared_white_bath_towel_v1_front_hung_panel", (origin.x, origin.y - 0.09, 1.12), 0.58, 0.62, mats["towel"], fold_depth=0.018, curl=0.014, thickness=0.012).name)
    names.append(add_soft_panel("shared_white_bath_towel_v1_back_hung_panel", (origin.x, origin.y + 0.005, 1.12), 0.58, 0.58, mats["towel"], fold_depth=0.014, curl=0.010, thickness=0.012).name)
    names.append(add_cube("shared_white_hand_towel_v1_folded_stack_1", (origin.x - 0.43, origin.y - 0.05, 0.82), (0.24, 0.17, 0.045), mats["towel"], bevel=0.02).name)
    names.append(add_cube("shared_white_hand_towel_v1_folded_stack_2", (origin.x - 0.43, origin.y - 0.05, 0.89), (0.23, 0.16, 0.040), mats["towel"], bevel=0.02).name)
    wrap_proxy = material("transparent_wrap_body_collision_proxy", (0.70, 0.78, 0.85, 0.25), 0.9)
    names.append(add_sphere("towel_wrap_body_collision_proxy", (origin.x + 0.45, origin.y, 1.04), (0.17, 0.11, 0.30), wrap_proxy, 32).name)
    names.append(add_cylinder("shared_white_bath_towel_v1_wrapped_around_body_band", (origin.x + 0.45, origin.y - 0.01, 1.03), 0.19, 0.40, mats["towel"], vertices=64, rot=(0, 0, 0)).name)
    names.append(add_cube("shared_white_bath_towel_v1_wrap_overlap_edge", (origin.x + 0.60, origin.y - 0.16, 1.03), (0.025, 0.020, 0.22), mats["cloth_edge"], bevel=0.008).name)
    return names


def add_labels(mats: dict[str, bpy.types.Material]) -> None:
    labels = [
        ("hanging robe on hook", (-2.55, -0.98, 0.18)),
        ("worn tied robe on fit proxy", (0.0, -0.98, 0.18)),
        ("folded robe", (0.0, 0.28, 0.18)),
        ("towel rack / stack / wrap", (2.55, -0.98, 0.18)),
    ]
    for text, loc in labels:
        bpy.ops.object.text_add(location=loc, rotation=(math.radians(74), 0, 0))
        obj = bpy.context.object
        obj.name = f"label_{text.replace(' ', '_').replace('/', '_')}"
        obj.data.body = text
        obj.data.align_x = "CENTER"
        obj.data.align_y = "CENTER"
        obj.data.size = 0.060
        obj.data.materials.append(mats["label"])


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render_view(name: str, camera: bpy.types.Object, loc: tuple[float, float, float], target: tuple[float, float, float], ortho: float) -> str:
    camera.location = loc
    look_at(camera, Vector(target))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho
    path = OUT_DIR / f"{name}.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return rel(path)


def build_scene() -> dict:
    clear_scene()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mats = {
        "robe": material("robe_white_terry_cloth_draft", (0.96, 0.95, 0.90, 1.0), 0.92),
        "towel": material("towel_white_terry_cloth_draft", (0.98, 0.97, 0.92, 1.0), 0.95),
        "cloth_edge": material("soft_white_seam_and_belt_edge", (0.86, 0.84, 0.78, 1.0), 0.88),
        "tile": material("bathroom_white_tile", (0.82, 0.88, 0.86, 1.0), 0.55),
        "grout": material("light_gray_tile_grout", (0.58, 0.64, 0.64, 1.0), 0.75),
        "metal": material("brushed_metal_hook_and_rack", (0.45, 0.48, 0.48, 1.0), 0.38),
        "floor": material("warm_spa_floor", (0.54, 0.57, 0.50, 1.0), 0.65),
        "label": material("dark_blue_review_label", (0.05, 0.16, 0.22, 1.0), 0.5),
    }
    add_cube("soft_goods_review_floor", (0, 0, 0.02), (4.0, 2.0, 0.02), mats["floor"])
    hanging = make_hanging_robe(Vector((-2.45, 0.0, 0.0)), mats)
    worn = make_worn_robe(Vector((0.0, -0.05, 0.0)), mats)
    folded = make_folded_robe(Vector((0.0, 0.72, 0.0)), mats)
    towels = make_towels(Vector((2.45, 0.0, 0.0)), mats)
    add_labels(mats)

    bpy.ops.object.light_add(type="AREA", location=(0.0, -3.0, 4.2))
    key = bpy.context.object
    key.name = "robe_towel_soft_goods_key_light"
    key.data.energy = 650
    key.data.size = 5.0
    bpy.ops.object.camera_add(location=(0, -5.0, 2.2))
    camera = bpy.context.object
    camera.name = "robe_towel_soft_goods_review_camera"
    bpy.context.scene.camera = camera
    bpy.context.scene.render.resolution_x = 1400
    bpy.context.scene.render.resolution_y = 950
    bpy.context.scene.world.color = (0.025, 0.035, 0.04)
    try:
        bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        bpy.context.scene.render.engine = "BLENDER_EEVEE"

    views = {
        "overview": render_view("overview", camera, (0.0, -6.0, 2.45), (0.0, -0.02, 1.05), 5.5),
        "robe_hanging_on_bathroom_hook": render_view("robe_hanging_on_bathroom_hook", camera, (-2.45, -2.2, 1.45), (-2.45, -0.05, 1.25), 1.55),
        "robe_worn_tied_walk_pose": render_view("robe_worn_tied_walk_pose", camera, (0.0, -2.55, 1.45), (0.0, -0.05, 1.15), 1.55),
        "robe_folded_storage": render_view("robe_folded_storage", camera, (0.0, -1.4, 1.45), (0.0, 0.72, 0.78), 0.95),
        "towel_rack_stack_wrap": render_view("towel_rack_stack_wrap", camera, (2.45, -2.35, 1.35), (2.45, -0.02, 1.10), 1.55),
        "side_collision_check": render_view("side_collision_check", camera, (4.1, -0.2, 1.50), (0.0, -0.02, 1.10), 3.2),
    }

    bpy.ops.export_scene.gltf(filepath=str(MODEL_OUT), export_format="GLB", export_yup=True, export_animations=False)

    state_machine = {
        "schema_version": 1,
        "created_at": datetime.now().isoformat(),
        "status": "staged_real_mesh_proof_not_runtime_approved",
        "model": rel(MODEL_OUT),
        "robe_id": "shared_white_bath_robe_v1",
        "towel_ids": ["shared_white_bath_towel_v1", "shared_white_hand_towel_v1"],
        "states_present_as_named_meshes": {
            "robe": ["hanging_on_hook", "folded_storage", "worn_tied", "belt_knot_anchor"],
            "towel": ["hung_on_towel_rack", "folded_stack", "wrapped_around_body"],
        },
        "missing_before_runtime": [
            "cloth simulation or fitted skinned garment mesh",
            "avatar hand grab IK",
            "robe sleeve dressing animation with collision",
            "towel body drying/wrapping animation",
            "round-trip same-item inventory binding",
        ],
    }
    STATE_MACHINE_OUT.write_text(json.dumps(state_machine, indent=2), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now().isoformat(),
        "run_id": RUN_ID,
        "status": "draft_real_mesh_assignment_proof_ready_for_robert_review",
        "model": rel(MODEL_OUT),
        "state_machine": rel(STATE_MACHINE_OUT),
        "renders": views,
        "mesh_groups": {
            "hanging_robe": hanging,
            "worn_robe": worn,
            "folded_robe": folded,
            "towels": towels,
        },
        "truth_note": "This is a staged real GLB proof. It gives the builders visible mesh states to learn from, but it is not approved clothing physics and should not be placed in Home World as a wearable item yet.",
        "automatic_grade": {
            "json_only": "passed_not_json_only",
            "real_visual_artifacts": "passed",
            "runtime_cloth_solver": "failed_not_implemented_yet",
            "avatar_can_dress_undress_walk": "failed_not_implemented_yet",
        },
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    INDEX_OUT.write_text(
        "<!doctype html><meta charset=\"utf-8\"><title>Robe Towel Soft Goods Proof</title>"
        "<body style=\"background:#07121a;color:#d9edf7;font-family:Arial,sans-serif\">"
        "<h1>Robe/Towel Soft Goods Proof</h1>"
        "<p>Draft real GLB proof. Not runtime approved yet.</p>"
        + "".join(f"<h2>{name}</h2><img src=\"{Path(path).name}\" style=\"max-width:900px;width:95%;border:1px solid #24506b\">" for name, path in views.items())
        + "</body>",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    manifest = build_scene()
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
