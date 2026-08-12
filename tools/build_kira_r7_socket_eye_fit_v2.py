"""Build the inactive R7 v2 realistic-brown-eye candidate for Kira's R6 head.

This bounded Blender authoring pass keeps the socket geometry proven by R7 v1
and replaces its flat procedural discs with user-authorized, source-derived
iris/sclera textures plus real shallow corneal lens meshes.  The rejected fake
lid inserts are intentionally absent: blink is explicitly unsupported until a
future facial-retopology pass provides real lid topology and deformation.

The tool never writes an Avatar Builder selection, Home World runtime binding,
live person state, chat, voice, or life-loop file.  It exports one separate
eye-only GLB and fixed offline review evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy  # type: ignore
from mathutils import Vector  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
R6_BODY = (
    ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6"
    / "r6_20260718_163658/kira_provisional_body_r6.glb"
)
STAGED_EYE = (
    ROOT
    / "Avatar/models/staged/kira/eyes/kira_brown_eye_rig_v3_2"
    / "kira_brown_eye_rig_v3_2.glb"
)
PUBLIC_EYE = (
    ROOT
    / "Data/world_builds/notebook_worlds/home_world/builds"
    / "home_world_main_house_20260630_223000/preview/public/models/home_world/kira"
    / "kira_brown_eye_rig_v3_2.glb"
)
MAIN_JS = (
    ROOT
    / "Data/world_builds/notebook_worlds/home_world/builds"
    / "home_world_main_house_20260630_223000/preview/src/main.js"
)
SOURCE_ARCHIVE = Path(r"C:\Users\robmc\Desktop\91\sci-fi-girl-v02-walkcycle-test.zip")
DEFAULT_OUTPUT = (
    ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_r7_socket_eye_fit"
    / "review_20260722_v2"
)
EXPECTED = {
    "r6_body": "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
    "staged_eye": "fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413",
    "public_eye": "fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413",
    "main_js": "56a763b0c235f63359b76c0aacdcbc74b222ad71043c8bb12bc7e4f055175b04",
    "source_archive": "ed9d90f09cc5a17881e14738bc102a704ee331add9442bad1e4d970fc9d4bfb1",
}
EYE_CENTERS = {
    "Left": Vector((-0.022298403532608698, -0.0432, 1.106764266304348)),
    "Right": Vector((0.022298403532608698, -0.0432, 1.106764266304348)),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--candidate-id", default="kira_r7_socket_eye_v2")
    parser.add_argument("--sclera-half-width-mm", type=float, default=9.05)
    parser.add_argument("--sclera-half-height-mm", type=float, default=3.12)
    parser.add_argument("--sclera-front-y", type=float, default=-0.04905)
    parser.add_argument("--sclera-rim-y", type=float, default=-0.04815)
    parser.add_argument("--iris-radius-mm", type=float, default=2.90)
    parser.add_argument("--iris-front-y", type=float, default=-0.04938)
    parser.add_argument("--cornea-radius-mm", type=float, default=3.14)
    parser.add_argument("--cornea-depth-mm", type=float, default=0.55)
    parser.add_argument("--gaze-yaw-degrees", type=float, default=13.0)
    parser.add_argument(
        "--visual-decision",
        choices=("pending", "accept", "reject"),
        default="pending",
    )
    parser.add_argument(
        "--visual-note",
        default="Original-resolution fixed renders require human visual inspection.",
    )
    return parser.parse_args(values)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    datablocks = (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.cameras,
        bpy.data.lights,
    )
    for collection in datablocks:
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def set_input(bsdf, name: str, value) -> None:
    socket = bsdf.inputs.get(name)
    if socket is not None:
        socket.default_value = value


def image_texture_material(
    name: str,
    base_color_path: Path,
    normal_path: Path,
    roughness: float,
    normal_strength: float,
    specular: float,
    coat: float,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    base = nodes.new("ShaderNodeTexImage")
    base.name = f"{name}_BaseColor"
    base.image = bpy.data.images.load(str(base_color_path), check_existing=True)
    base.image.colorspace_settings.name = "sRGB"
    base.image.pack()
    normal = nodes.new("ShaderNodeTexImage")
    normal.name = f"{name}_Normal"
    normal.image = bpy.data.images.load(str(normal_path), check_existing=True)
    normal.image.colorspace_settings.name = "Non-Color"
    normal.image.pack()
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.inputs["Strength"].default_value = normal_strength
    set_input(bsdf, "Roughness", roughness)
    set_input(bsdf, "Specular IOR Level", specular)
    set_input(bsdf, "Coat Weight", coat)
    set_input(bsdf, "Coat Roughness", 0.12)
    links.new(base.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(normal.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def cornea_material() -> bpy.types.Material:
    material = bpy.data.materials.new("Kira_R7_V2_Physical_Cornea")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        set_input(bsdf, "Base Color", (0.92, 0.97, 1.0, 1.0))
        set_input(bsdf, "Roughness", 0.055)
        set_input(bsdf, "Specular IOR Level", 0.50)
        set_input(bsdf, "IOR", 1.376)
        set_input(bsdf, "Transmission Weight", 0.82)
        set_input(bsdf, "Coat Weight", 0.22)
        set_input(bsdf, "Coat Roughness", 0.035)
        set_input(bsdf, "Alpha", 0.20)
    try:
        material.surface_render_method = "DITHERED"
    except (AttributeError, TypeError, ValueError):
        pass
    material.diffuse_color = (0.92, 0.97, 1.0, 0.20)
    return material


def new_empty(name: str, location=(0.0, 0.0, 0.0), parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "SPHERE"
    obj.empty_display_size = 0.002
    obj.location = location
    bpy.context.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def assign_planar_uv(mesh: bpy.types.Mesh, half_width: float, half_height: float) -> None:
    layer = mesh.uv_layers.new(name="UVMap")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex = mesh.vertices[mesh.loops[loop_index].vertex_index]
            layer.data[loop_index].uv = (
                0.5 + vertex.co.x / (2.0 * half_width),
                0.5 + vertex.co.z / (2.0 * half_height),
            )


def almond_surface(
    name: str,
    half_width: float,
    half_height: float,
    center_y: float,
    rim_y: float,
    material: bpy.types.Material,
    parent,
    rings: int = 10,
    sectors: int = 96,
):
    vertices: list[tuple[float, float, float]] = []
    for ring in range(rings + 1):
        radial = ring / rings
        for sector in range(sectors):
            angle = 2.0 * math.pi * sector / sectors
            x = math.cos(angle) * half_width * radial
            z = math.sin(angle) * half_height * radial
            y = center_y + (rim_y - center_y) * radial * radial
            vertices.append((x, y, z))
    faces: list[tuple[int, int, int, int]] = []
    for ring in range(rings):
        for sector in range(sectors):
            nxt = (sector + 1) % sectors
            faces.append(
                (
                    ring * sectors + sector,
                    ring * sectors + nxt,
                    (ring + 1) * sectors + nxt,
                    (ring + 1) * sectors + sector,
                )
            )
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(material)
    assign_planar_uv(mesh, half_width, half_height)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj


def iris_surface(
    name: str,
    radius: float,
    y: float,
    material: bpy.types.Material,
    parent,
    rings: int = 12,
    sectors: int = 96,
):
    vertices: list[tuple[float, float, float]] = []
    for ring in range(rings + 1):
        radial = ring / rings
        for sector in range(sectors):
            angle = 2.0 * math.pi * sector / sectors
            # The iris is behind the cornea and is only microscopically curved;
            # its photographic radial structure comes from the supplied map.
            bulge = -0.000045 * (1.0 - radial * radial)
            vertices.append(
                (
                    math.cos(angle) * radius * radial,
                    y + bulge,
                    math.sin(angle) * radius * radial,
                )
            )
    faces: list[tuple[int, int, int, int]] = []
    for ring in range(rings):
        for sector in range(sectors):
            nxt = (sector + 1) % sectors
            faces.append(
                (
                    ring * sectors + sector,
                    ring * sectors + nxt,
                    (ring + 1) * sectors + nxt,
                    (ring + 1) * sectors + sector,
                )
            )
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(material)
    assign_planar_uv(mesh, radius, radius)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj


def cornea_lens(
    name: str,
    radius: float,
    depth: float,
    iris_y: float,
    material: bpy.types.Material,
    parent,
):
    # A thin closed ellipsoid supplies actual corneal curvature and area-light
    # reflections.  It is not a painted/fake catchlight disc.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, location=(0.0, 0.0, 0.0))
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = (0.0, iris_y + depth * 0.38, 0.0)
    obj.scale = (radius, depth, radius)
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def build_eye(
    side: str,
    center: Vector,
    rig,
    sclera_material: bpy.types.Material,
    iris_material: bpy.types.Material,
    cornea_mat: bpy.types.Material,
    args: argparse.Namespace,
):
    half_width = args.sclera_half_width_mm / 1000.0
    half_height = args.sclera_half_height_mm / 1000.0
    iris_radius = args.iris_radius_mm / 1000.0
    cornea_radius = args.cornea_radius_mm / 1000.0
    cornea_depth = args.cornea_depth_mm / 1000.0
    socket = new_empty(f"Kira{side}EyeSocket", center, rig)
    pivot = new_empty(f"Kira{side}EyePivot", (0.0, 0.0, 0.0), socket)
    sclera = almond_surface(
        f"Kira{side}Sclera",
        half_width,
        half_height,
        args.sclera_front_y - center.y,
        args.sclera_rim_y - center.y,
        sclera_material,
        socket,
    )
    iris = iris_surface(
        f"Kira{side}Iris",
        iris_radius,
        args.iris_front_y - center.y,
        iris_material,
        pivot,
    )
    cornea = cornea_lens(
        f"Kira{side}Cornea",
        cornea_radius,
        cornea_depth,
        args.iris_front_y - center.y,
        cornea_mat,
        pivot,
    )
    socket["side"] = side.lower()
    socket["measured_r6_socket_center"] = [float(value) for value in center]
    pivot["yaw_limit_degrees"] = 16.0
    pivot["pitch_limit_degrees"] = 10.0
    iris["pupil_and_limbal_detail"] = "embedded_in_source_derived_iris_texture"
    cornea["kind"] = "closed_shallow_transparent_ellipsoid_not_fake_catchlight"
    return {
        "socket": socket,
        "pivot": pivot,
        "sclera": sclera,
        "iris": iris,
        "cornea": cornea,
    }


def descendants(root) -> list[bpy.types.Object]:
    result = [root]
    for child in root.children:
        result.extend(descendants(child))
    return result


def select_only(objects: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def pose(eyes: dict[str, dict[str, bpy.types.Object]], yaw: float = 0.0, pitch: float = 0.0) -> None:
    for record in eyes.values():
        record["pivot"].rotation_euler = (
            math.radians(-pitch),
            0.0,
            math.radians(yaw),
        )
    bpy.context.view_layer.update()


def add_camera_and_lights():
    bpy.ops.object.camera_add(location=(0.0, -0.34, 1.108))
    camera = bpy.context.object
    camera.name = "Kira_R7_V2_Fixed_Review_Camera"
    camera.data.type = "PERSP"
    camera.data.lens = 72
    camera.data.sensor_width = 36
    camera.data.dof.use_dof = False
    bpy.context.scene.camera = camera
    target = Vector((0.0, -0.042, 1.107))
    for name, location, energy, size in (
        ("Kira_R7_V2_Eye_Key", (-0.18, -0.24, 1.26), 34.0, 0.18),
        ("Kira_R7_V2_Eye_Fill", (0.19, -0.22, 1.17), 18.0, 0.16),
        ("Kira_R7_V2_Eye_Rim", (0.0, 0.03, 1.23), 20.0, 0.14),
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        look_at(light, target)
    return camera


def render_view(
    path: Path,
    camera,
    camera_location: tuple[float, float, float],
    target: Vector,
    lens: float,
) -> None:
    camera.location = camera_location
    camera.data.lens = lens
    look_at(camera, target)
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def file_record(path: Path) -> dict[str, object]:
    return {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def main() -> None:
    args = parse_args()
    output = args.output_dir.resolve()
    renders = output / "fixed_renders"
    textures = output / "derived_textures"
    texture_manifest_path = textures / "texture_derivation_manifest.json"
    output.mkdir(parents=True, exist_ok=True)
    renders.mkdir(parents=True, exist_ok=True)
    if not texture_manifest_path.is_file():
        raise RuntimeError(
            "Derived eye textures are missing. Run tools/prepare_kira_r7_eye_v2_textures.py first."
        )
    texture_manifest = json.loads(texture_manifest_path.read_text(encoding="utf-8"))
    texture_paths = {
        key: Path(record["path"]).resolve()
        for key, record in texture_manifest["generated"].items()
    }
    texture_checks = {
        key: path.is_file() and sha256(path) == texture_manifest["generated"][key]["sha256"]
        for key, path in texture_paths.items()
    }
    if not all(texture_checks.values()):
        raise RuntimeError(f"Derived eye texture hash check failed: {texture_checks}")

    sources = {
        "r6_body": R6_BODY,
        "staged_eye": STAGED_EYE,
        "public_eye": PUBLIC_EYE,
        "main_js": MAIN_JS,
        "source_archive": SOURCE_ARCHIVE,
    }
    hashes_before = {key: sha256(path) for key, path in sources.items()}
    checks_before = {key: hashes_before[key] == EXPECTED[key] for key in sources}
    if not all(checks_before.values()):
        raise RuntimeError(f"Immutable input/live hash check failed: {checks_before}")

    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(R6_BODY))
    bpy.context.scene.frame_set(0)
    body_meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    body = max(body_meshes, key=lambda obj: len(obj.data.vertices))

    sclera_material = image_texture_material(
        "Kira_R7_V2_Living_Sclera",
        texture_paths["sclera_base_color"],
        texture_paths["sclera_normal"],
        roughness=0.34,
        normal_strength=0.20,
        specular=0.34,
        coat=0.10,
    )
    iris_material = image_texture_material(
        "Kira_R7_V2_Source_Derived_Brown_Iris",
        texture_paths["brown_iris_base_color"],
        texture_paths["iris_normal"],
        roughness=0.46,
        normal_strength=0.34,
        specular=0.16,
        coat=0.0,
    )
    cornea_mat = cornea_material()

    rig = new_empty("KiraBrownEyeRig_R7_V2_RealisticMaterials", (0.0, 0.0, 0.0))
    rig["schema_version"] = 7.2
    rig["candidate_id"] = args.candidate_id
    rig["inactive_review_only"] = True
    rig["source_r6_sha256"] = hashes_before["r6_body"]
    rig["source_folder91_archive_sha256"] = hashes_before["source_archive"]
    rig["no_live_binding"] = True
    rig["blink_supported"] = False
    rig["blink_reason"] = (
        "R6 has no authored natural eyelid deformation; rejected v1 insert lids were removed."
    )
    eyes = {
        side: build_eye(
            side,
            center,
            rig,
            sclera_material,
            iris_material,
            cornea_mat,
            args,
        )
        for side, center in EYE_CENTERS.items()
    }
    bpy.context.view_layer.update()

    candidate_glb = output / f"{args.candidate_id}.glb"
    pose(eyes)
    select_only(descendants(rig))
    bpy.ops.export_scene.gltf(
        filepath=str(candidate_glb),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_animations=False,
        export_morph=False,
        export_apply=False,
        export_extras=True,
    )

    camera = add_camera_and_lights()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.world.color = (0.012, 0.016, 0.024)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -1.55
    target = Vector((0.0, -0.041, 1.107))

    fixed = {
        "neutral_front": ((0.0, -0.34, 1.108), target, 72.0, 0.0, 0.0),
        "neutral_left_30deg": ((-0.17, -0.295, 1.110), target, 72.0, 0.0, 0.0),
        "neutral_right_30deg": ((0.17, -0.295, 1.110), target, 72.0, 0.0, 0.0),
        "neutral_left_profile": ((-0.34, -0.010, 1.110), target, 72.0, 0.0, 0.0),
        "neutral_right_profile": ((0.34, -0.010, 1.110), target, 72.0, 0.0, 0.0),
        "gaze_left_front": (
            (0.0, -0.34, 1.108), target, 72.0, -args.gaze_yaw_degrees, 0.0
        ),
        "gaze_right_front": (
            (0.0, -0.34, 1.108), target, 72.0, args.gaze_yaw_degrees, 0.0
        ),
        "gaze_up_front": ((0.0, -0.34, 1.108), target, 72.0, 0.0, 7.0),
        "gaze_down_front": ((0.0, -0.34, 1.108), target, 72.0, 0.0, -7.0),
        "macro_left_iris_cornea": (
            (-0.0223, -0.092, 1.1068), EYE_CENTERS["Left"], 82.0, 0.0, 0.0
        ),
        "macro_right_iris_cornea": (
            (0.0223, -0.092, 1.1068), EYE_CENTERS["Right"], 82.0, 0.0, 0.0
        ),
    }
    views: dict[str, dict[str, object]] = {}
    for name, (camera_location, view_target, lens, yaw, pitch) in fixed.items():
        pose(eyes, yaw=yaw, pitch=pitch)
        path = renders / f"{name}.png"
        render_view(path, camera, camera_location, view_target, lens)
        views[name] = {
            **file_record(path),
            "camera_location": list(camera_location),
            "camera_target": [float(value) for value in view_target],
            "camera_lens_mm": lens,
            "gaze_yaw_degrees": yaw,
            "gaze_pitch_degrees": pitch,
        }
    pose(eyes)

    blend_path = output / f"{args.candidate_id}_offline_review.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    hashes_after = {key: sha256(path) for key, path in sources.items()}
    checks_after = {key: hashes_after[key] == EXPECTED[key] for key in sources}

    required_nodes = [
        "KiraLeftEyeSocket",
        "KiraRightEyeSocket",
        "KiraLeftEyePivot",
        "KiraRightEyePivot",
        "KiraLeftSclera",
        "KiraRightSclera",
        "KiraLeftIris",
        "KiraRightIris",
        "KiraLeftCornea",
        "KiraRightCornea",
    ]
    descendants_names = sorted(obj.name for obj in descendants(rig))
    structural = {
        "all_required_nodes_present": all(
            bpy.data.objects.get(name) is not None for name in required_nodes
        ),
        "exactly_two_sclera_nodes": sum(name.endswith("Sclera") for name in descendants_names) == 2,
        "exactly_two_iris_nodes": sum(name.endswith("Iris") for name in descendants_names) == 2,
        "exactly_two_cornea_nodes": sum(name.endswith("Cornea") for name in descendants_names) == 2,
        "no_fake_insert_lid_nodes": not any("Lid" in name for name in descendants_names),
        "blink_explicitly_unsupported": rig["blink_supported"] is False,
        "source_derived_texture_hashes_match": all(texture_checks.values()),
        "source_and_live_files_unchanged": hashes_before == hashes_after == EXPECTED,
        "candidate_is_separate_eye_only_glb": candidate_glb.resolve() not in sources.values(),
        "r6_body_context_not_exported": body.name not in descendants_names,
    }
    if not all(structural.values()):
        raise RuntimeError(f"R7 v2 structural check failed: {structural}")

    if args.visual_decision == "pending":
        visual = {
            "socket_alignment_front_and_three_quarter": None,
            "no_profile_protrusion": None,
            "four_gaze_views_plausible": None,
            "brown_iris_reads_as_living_texture_not_flat_disc": None,
            "sclera_reads_as_living_tissue": None,
            "cornea_reads_as_natural_wet_lens": None,
            "overall_visual_fit_passed": None,
        }
        status = "inactive_fixed_view_review_pending"
    elif args.visual_decision == "accept":
        visual = {
            "socket_alignment_front_and_three_quarter": True,
            "no_profile_protrusion": True,
            "four_gaze_views_plausible": True,
            "brown_iris_reads_as_living_texture_not_flat_disc": True,
            "sclera_reads_as_living_tissue": True,
            "cornea_reads_as_natural_wet_lens": True,
            "overall_visual_fit_passed": True,
        }
        status = "inactive_visual_fit_candidate_passed_owner_review_pending"
    else:
        visual = {
            "socket_alignment_front_and_three_quarter": False,
            "no_profile_protrusion": True,
            "four_gaze_views_plausible": False,
            "brown_iris_reads_as_living_texture_not_flat_disc": False,
            "sclera_reads_as_living_tissue": False,
            "cornea_reads_as_natural_wet_lens": False,
            "macro_views_show_eye_detail": False,
            "overall_visual_fit_passed": False,
        }
        status = "rejected_visual_fit"
    visual.update(
        {
            "blink_supported": False,
            "blink_reason": (
                "No real R6 lid topology/deformation is authored; v1 fake insert lids were removed."
            ),
            "promotion_allowed": False,
            "owner_review_required_before_any_promotion": True,
            "note": args.visual_note,
        }
    )

    evidence_path = output / "evidence.json"
    evidence = {
        "schema_version": 2,
        "candidate_id": args.candidate_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "kind": "offline_blender_inactive_eye_only_authoring_no_activation_no_binding_no_runtime_write",
        "status": status,
        "promotion_allowed": False,
        "authorization_context": (
            "Robert explicitly supplied Desktop Folder 91 to improve the avatar/world/movement builders. "
            "Only the archive's eye diffuse/normals are used in this local inactive candidate; no "
            "redistribution or license claim is made."
        ),
        "sources": {
            key: {"path": rel(path), "sha256": hashes_before[key]}
            for key, path in sources.items()
        },
        "texture_derivation_manifest": file_record(texture_manifest_path),
        "derived_textures": {
            key: file_record(path) for key, path in texture_paths.items()
        },
        "candidate": file_record(candidate_glb),
        "offline_review_blend": file_record(blend_path),
        "parameters": {
            "measured_socket_centers_blender_native": {
                side.lower(): [float(value) for value in center]
                for side, center in EYE_CENTERS.items()
            },
            "sclera_half_width_mm": args.sclera_half_width_mm,
            "sclera_half_height_mm": args.sclera_half_height_mm,
            "sclera_front_y": args.sclera_front_y,
            "sclera_rim_y": args.sclera_rim_y,
            "iris_radius_mm": args.iris_radius_mm,
            "iris_front_y": args.iris_front_y,
            "cornea_radius_mm": args.cornea_radius_mm,
            "cornea_depth_mm": args.cornea_depth_mm,
            "gaze_yaw_degrees": args.gaze_yaw_degrees,
        },
        "hashes_before": hashes_before,
        "hashes_after": hashes_after,
        "structural_checks": structural,
        "fixed_renders": views,
        "visual_acceptance": visual,
        "limits": [
            "The candidate is not referenced by Avatar Builder or Home World.",
            "The review does not activate Kira or any other person.",
            "Blink is unsupported; this candidate deliberately has no fake insert lids.",
            "Texture and structural checks do not prove visual realism.",
            "Owner approval and a separate reversible promotion task remain mandatory after any visual pass.",
        ],
    }
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": status,
                "candidate": file_record(candidate_glb),
                "evidence": file_record(evidence_path),
                "fixed_render_count": len(views),
                "structural_checks": structural,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
