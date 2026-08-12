"""Build and render an inactive R7 eye candidate for Kira's exact R6 head.

This is an offline Blender authoring/review tool.  It imports the immutable R6
body for socket context, builds one separate eye-only asset, and renders fixed
front, bilateral three-quarter, bilateral profile, blink, and gaze views.  It
does not write a live/public eye asset, a runtime binding, person state, chat,
voice, or life-loop state.

The R6 aperture audit established that the socket centres are correct but a
spherical 17.2 mm globe cannot be translated into a visually safe interval.
This R7 experiment therefore uses a shallow socket-conforming sclera, keeps the
sclera stationary, and rotates only the existing iris/limbus/pupil/cornea
controller children.  It retains the exact node names expected by the existing
structural contract and adds no second eye pair.
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
DEFAULT_OUTPUT = (
    ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_r7_socket_eye_fit"
    / "review_20260722_v1"
)

EXPECTED = {
    "r6_body": "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
    "staged_eye": "fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413",
    "public_eye": "fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413",
    "main_js": "56a763b0c235f63359b76c0aacdcbc74b222ad71043c8bb12bc7e4f055175b04",
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
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--candidate-id", default="kira_r7_socket_eye_v1")
    parser.add_argument("--sclera-half-width-mm", type=float, default=9.05)
    parser.add_argument("--sclera-half-height-mm", type=float, default=3.12)
    parser.add_argument("--sclera-front-y", type=float, default=-0.04905)
    parser.add_argument("--sclera-rim-y", type=float, default=-0.04815)
    parser.add_argument("--iris-radius-mm", type=float, default=2.90)
    parser.add_argument("--iris-front-y", type=float, default=-0.04938)
    parser.add_argument("--gaze-yaw-degrees", type=float, default=13.0)
    parser.add_argument(
        "--visual-decision",
        choices=("pending", "accept", "reject"),
        default="pending",
    )
    return parser.parse_args(values)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def principled(name: str, color: tuple[float, float, float, float], roughness: float, **values):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        for socket_name, value in values.items():
            socket = bsdf.inputs.get(socket_name)
            if socket is not None:
                socket.default_value = value
    return material


def materials() -> dict[str, bpy.types.Material]:
    skin = principled("Kira_R7_Review_Eyelid_Skin", (0.56, 0.39, 0.31, 1.0), 0.64)
    sclera = principled(
        "Kira_R7_Sclera_Natural_White", (0.67, 0.61, 0.57, 1.0), 0.53,
        **{"Specular IOR Level": 0.20},
    )
    limbal = principled(
        "Kira_R7_Limbal_Deep_Brown", (0.012, 0.0035, 0.0015, 1.0), 0.55,
        **{"Specular IOR Level": 0.16},
    )
    # Keep the three iris values close enough to read as one brown iris.  The
    # early pass used bright orange concentric rings and looked mechanical.
    iris_dark = principled(
        "Kira_R7_Iris_Dark_Brown", (0.026, 0.007, 0.002, 1.0), 0.55,
        **{"Specular IOR Level": 0.16},
    )
    iris_mid = principled(
        "Kira_R7_Iris_Medium_Brown", (0.070, 0.020, 0.005, 1.0), 0.52,
        **{"Specular IOR Level": 0.18},
    )
    iris_light = principled(
        "Kira_R7_Iris_Subtle_Amber_Flecks", (0.15, 0.055, 0.012, 1.0), 0.48,
        **{"Specular IOR Level": 0.18},
    )
    pupil = principled(
        "Kira_R7_Pupil", (0.0012, 0.0005, 0.0003, 1.0), 0.42,
        **{"Specular IOR Level": 0.12},
    )
    wetline = principled("Kira_R7_Wetline", (0.18, 0.07, 0.04, 1.0), 0.25)
    catchlight = principled("Kira_R7_Catchlight", (0.95, 0.98, 1.0, 1.0), 0.08)
    return {
        "skin": skin,
        "sclera": sclera,
        "limbal": limbal,
        "iris_dark": iris_dark,
        "iris_mid": iris_mid,
        "iris_light": iris_light,
        "pupil": pupil,
        "wetline": wetline,
        "catchlight": catchlight,
    }


def new_empty(name: str, location=(0.0, 0.0, 0.0), parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "SPHERE"
    obj.empty_display_size = 0.002
    obj.location = location
    bpy.context.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def almond_surface(
    name: str,
    half_width: float,
    half_height: float,
    center_y: float,
    rim_y: float,
    material: bpy.types.Material,
    parent,
    rings: int = 7,
    sectors: int = 64,
):
    vertices: list[tuple[float, float, float]] = []
    for ring in range(rings + 1):
        radial = ring / rings
        for sector in range(sectors):
            angle = 2.0 * math.pi * sector / sectors
            x = math.cos(angle) * half_width * radial
            z = math.sin(angle) * half_height * radial
            # A shallow convex front fills the aperture without carrying the
            # temple-protruding volume of the rejected spherical eye family.
            y = center_y + (rim_y - center_y) * radial * radial
            vertices.append((x, y, z))
    faces: list[tuple[int, int, int, int]] = []
    for ring in range(rings):
        for sector in range(sectors):
            nxt = (sector + 1) % sectors
            a = ring * sectors + sector
            b = ring * sectors + nxt
            c = (ring + 1) * sectors + nxt
            d = (ring + 1) * sectors + sector
            faces.append((a, b, c, d))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj


def radial_disc(
    name: str,
    radius: float,
    y: float,
    material_slots: list[bpy.types.Material],
    parent,
    inner_radius: float = 0.0,
    rings: int = 7,
    sectors: int = 64,
):
    vertices: list[tuple[float, float, float]] = []
    for ring in range(rings + 1):
        ratio = ring / rings
        radial = inner_radius + (radius - inner_radius) * ratio
        for sector in range(sectors):
            angle = 2.0 * math.pi * sector / sectors
            bulge = -0.00018 * (1.0 - ratio * ratio)
            vertices.append((math.cos(angle) * radial, y + bulge, math.sin(angle) * radial))
    faces: list[tuple[int, int, int, int]] = []
    for ring in range(rings):
        for sector in range(sectors):
            nxt = (sector + 1) % sectors
            a = ring * sectors + sector
            b = ring * sectors + nxt
            c = (ring + 1) * sectors + nxt
            d = (ring + 1) * sectors + sector
            faces.append((a, b, c, d))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for material in material_slots:
        mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    for index, polygon in enumerate(mesh.polygons):
        polygon.use_smooth = True
        ring = index // sectors
        sector = index % sectors
        if len(material_slots) == 1:
            polygon.material_index = 0
        elif len(material_slots) == 2:
            polygon.material_index = 1 if (sector * 7 + ring * 3) % 17 in (0, 1) else 0
        else:
            # Radial, low-contrast variation rather than synthetic-looking
            # concentric rings.  The integer pattern is deterministic.
            pattern = (sector * 7 + ring * 3) % 31
            polygon.material_index = 2 if pattern in (0, 1) else 1 if pattern in (2, 3, 4, 5) else 0
    return obj


def eyelid_surface(
    name: str,
    upper: bool,
    half_width: float,
    half_height: float,
    open_y: float,
    closed_y: float,
    material: bpy.types.Material,
    parent,
):
    samples = 41
    rows = 9
    basis: list[tuple[float, float, float]] = []
    closed: list[tuple[float, float, float]] = []
    for row in range(rows):
        v = row / (rows - 1)
        for index in range(samples):
            u = -1.0 + 2.0 * index / (samples - 1)
            x = half_width * u
            arch = math.sqrt(max(0.0, 1.0 - u * u))
            rim_z = half_height * arch * (1.0 if upper else -1.0)
            # Open basis remains behind the eye surface as a thin folded band.
            base_z = rim_z + (-1.0 if upper else 1.0) * 0.00010 * arch * v
            basis.append((x, open_y, base_z))
            seam_z = (-0.00010 if upper else 0.00010) * arch
            closed_z = rim_z * (1.0 - v) + seam_z * v
            edge = abs(u)
            closed.append((x, closed_y + 0.00010 * edge * edge, closed_z))
    faces: list[tuple[int, int, int, int]] = []
    for row in range(rows - 1):
        for index in range(samples - 1):
            a = row * samples + index
            b = a + 1
            c = (row + 1) * samples + index + 1
            d = (row + 1) * samples + index
            faces.append((a, d, c, b) if upper else (a, b, c, d))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(basis, [], faces)
    mesh.update()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.shape_key_add(name="Basis")
    blink = obj.shape_key_add(name="Blink")
    for index, coordinate in enumerate(closed):
        blink.data[index].co = Vector(coordinate)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj


def build_eye(side: str, center: Vector, rig, mats: dict[str, bpy.types.Material], args: argparse.Namespace):
    half_width = args.sclera_half_width_mm / 1000.0
    half_height = args.sclera_half_height_mm / 1000.0
    iris_radius = args.iris_radius_mm / 1000.0
    socket = new_empty(f"Kira{side}EyeSocket", center, rig)
    pivot = new_empty(f"Kira{side}EyePivot", (0.0, 0.0, 0.0), socket)
    sclera = almond_surface(
        f"Kira{side}Sclera",
        half_width,
        half_height,
        args.sclera_front_y - center.y,
        args.sclera_rim_y - center.y,
        mats["sclera"],
        socket,
    )
    limbal = radial_disc(
        f"Kira{side}LimbalRing",
        iris_radius * 1.065,
        args.iris_front_y - center.y + 0.00008,
        [mats["limbal"]],
        pivot,
        inner_radius=iris_radius * 0.965,
        rings=2,
    )
    iris = radial_disc(
        f"Kira{side}Iris",
        iris_radius,
        args.iris_front_y - center.y,
        [mats["iris_mid"], mats["iris_dark"], mats["iris_light"]],
        pivot,
        rings=8,
    )
    pupil = radial_disc(
        f"Kira{side}Pupil",
        iris_radius * 0.39,
        args.iris_front_y - center.y - 0.00022,
        [mats["pupil"]],
        pivot,
        rings=3,
    )
    # The existing R6 head has no authored corneal volume that can be proven
    # safe in profile.  Keep the contract node, but make this review mesh a
    # small specular catchlight on the iris instead of the bright annulus used
    # by the rejected early experiment.  A later facial-retopology pass may
    # replace it with a true transparent corneal shell.
    cornea = radial_disc(
        f"Kira{side}Cornea",
        iris_radius * 0.105,
        args.iris_front_y - center.y - 0.00034,
        [mats["catchlight"]],
        pivot,
        rings=3,
    )
    cornea.location.x = -iris_radius * 0.22
    cornea.location.z = iris_radius * 0.24
    cornea.scale.z = 0.78
    upper = eyelid_surface(
        f"Kira{side}UpperLid", True, half_width * 0.99, half_height * 0.99,
        args.sclera_rim_y - center.y + 0.0016,
        args.iris_front_y - center.y - 0.00055,
        mats["skin"], socket,
    )
    lower = eyelid_surface(
        f"Kira{side}LowerLid", False, half_width * 0.99, half_height * 0.99,
        args.sclera_rim_y - center.y + 0.0016,
        args.iris_front_y - center.y - 0.00048,
        mats["skin"], socket,
    )
    socket["side"] = side.lower()
    socket["measured_r6_socket_center"] = [float(value) for value in center]
    pivot["yaw_limit_degrees"] = 16.0
    pivot["pitch_limit_degrees"] = 10.0
    return {
        "socket": socket,
        "pivot": pivot,
        "sclera": sclera,
        "limbal": limbal,
        "iris": iris,
        "pupil": pupil,
        "cornea": cornea,
        "upper": upper,
        "lower": lower,
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


def pose(eyes: dict[str, dict[str, bpy.types.Object]], yaw: float = 0.0, pitch: float = 0.0, blink: float = 0.0) -> None:
    for record in eyes.values():
        record["pivot"].rotation_euler = (
            math.radians(-pitch),
            0.0,
            math.radians(yaw),
        )
        for key in ("upper", "lower"):
            record[key].data.shape_keys.key_blocks["Blink"].value = blink
    bpy.context.view_layer.update()


def add_camera_and_lights():
    bpy.ops.object.camera_add(location=(0.0, -0.34, 1.108))
    camera = bpy.context.object
    camera.name = "Kira_R7_Eye_Fixed_Review_Camera"
    camera.data.type = "PERSP"
    camera.data.lens = 72
    camera.data.sensor_width = 36
    camera.data.dof.use_dof = False
    bpy.context.scene.camera = camera
    target = Vector((0.0, -0.035, 1.107))
    for name, location, energy, size in (
        ("Kira_R7_Eye_Key", (-0.22, -0.31, 1.29), 20.0, 0.26),
        ("Kira_R7_Eye_Fill", (0.22, -0.25, 1.18), 9.0, 0.22),
        ("Kira_R7_Eye_Rim", (0.0, 0.05, 1.24), 13.0, 0.18),
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        look_at(light, target)
    return camera


def render_view(path: Path, camera, camera_location: tuple[float, float, float], target: Vector) -> None:
    camera.location = camera_location
    look_at(camera, target)
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def file_record(path: Path) -> dict[str, object]:
    return {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def main() -> None:
    args = parse_args()
    output = args.output_dir.resolve()
    renders = output / "fixed_renders"
    output.mkdir(parents=True, exist_ok=True)
    renders.mkdir(parents=True, exist_ok=True)

    sources = {
        "r6_body": R6_BODY,
        "staged_eye": STAGED_EYE,
        "public_eye": PUBLIC_EYE,
        "main_js": MAIN_JS,
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
    mats = materials()
    # Preserve the exact imported R6 body material for review.  Replacing it
    # made the first two offline renders nearly white and obscured the socket
    # boundary, which cannot support an honest fit decision.  Reuse the same
    # material on the candidate lids so their closure can be judged against
    # the untouched head.  The source GLB itself remains byte-immutable.
    if body.data.materials:
        mats["skin"] = body.data.materials[0]

    rig = new_empty("KiraBrownEyeRig_R7_SocketFit", (0.0, 0.0, 0.0))
    rig["schema_version"] = 7
    rig["candidate_id"] = args.candidate_id
    rig["inactive_review_only"] = True
    rig["source_r6_sha256"] = hashes_before["r6_body"]
    rig["source_staged_eye_sha256"] = hashes_before["staged_eye"]
    rig["no_live_binding"] = True
    eyes = {side: build_eye(side, center, rig, mats, args) for side, center in EYE_CENTERS.items()}
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
        export_morph=True,
        export_apply=False,
        export_extras=True,
    )

    camera = add_camera_and_lights()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.world.color = (0.012, 0.016, 0.024)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -1.75
    target = Vector((0.0, -0.036, 1.107))

    views: dict[str, dict[str, object]] = {}
    fixed = {
        "neutral_front": ((0.0, -0.34, 1.108), 0.0, 0.0, 0.0),
        "neutral_left_30deg": ((-0.17, -0.295, 1.110), 0.0, 0.0, 0.0),
        "neutral_right_30deg": ((0.17, -0.295, 1.110), 0.0, 0.0, 0.0),
        "neutral_left_profile": ((-0.34, -0.010, 1.110), 0.0, 0.0, 0.0),
        "neutral_right_profile": ((0.34, -0.010, 1.110), 0.0, 0.0, 0.0),
        "blink_closed_front": ((0.0, -0.34, 1.108), 0.0, 0.0, 1.0),
        "gaze_left_front": ((0.0, -0.34, 1.108), -args.gaze_yaw_degrees, 0.0, 0.0),
        "gaze_right_front": ((0.0, -0.34, 1.108), args.gaze_yaw_degrees, 0.0, 0.0),
        "gaze_up_front": ((0.0, -0.34, 1.108), 0.0, 7.0, 0.0),
        "gaze_down_front": ((0.0, -0.34, 1.108), 0.0, -7.0, 0.0),
    }
    for name, (camera_location, yaw, pitch, blink) in fixed.items():
        pose(eyes, yaw=yaw, pitch=pitch, blink=blink)
        path = renders / f"{name}.png"
        render_view(path, camera, camera_location, target)
        views[name] = {
            **file_record(path),
            "camera_location": list(camera_location),
            "gaze_yaw_degrees": yaw,
            "gaze_pitch_degrees": pitch,
            "blink": blink,
        }
    pose(eyes)

    blend_path = output / f"{args.candidate_id}_offline_review.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    hashes_after = {key: sha256(path) for key, path in sources.items()}
    checks_after = {key: hashes_after[key] == EXPECTED[key] for key in sources}
    required_nodes = [
        "KiraLeftEyeSocket", "KiraRightEyeSocket",
        "KiraLeftEyePivot", "KiraRightEyePivot",
        "KiraLeftSclera", "KiraRightSclera",
        "KiraLeftIris", "KiraRightIris",
        "KiraLeftLimbalRing", "KiraRightLimbalRing",
        "KiraLeftPupil", "KiraRightPupil",
        "KiraLeftCornea", "KiraRightCornea",
        "KiraLeftUpperLid", "KiraLeftLowerLid",
        "KiraRightUpperLid", "KiraRightLowerLid",
    ]
    actual_sclera_nodes = sorted(
        obj.name for obj in descendants(rig) if obj.name.endswith("Sclera")
    )
    structural = {
        "all_required_nodes_present": all(bpy.data.objects.get(name) is not None for name in required_nodes),
        "exactly_two_sclera_nodes": actual_sclera_nodes
        == ["KiraLeftSclera", "KiraRightSclera"],
        "four_blink_morphs_present": all(
            bpy.data.objects[name].data.shape_keys is not None
            and "Blink" in bpy.data.objects[name].data.shape_keys.key_blocks
            for name in (
                "KiraLeftUpperLid", "KiraLeftLowerLid",
                "KiraRightUpperLid", "KiraRightLowerLid",
            )
        ),
        "source_and_live_files_unchanged": hashes_before == hashes_after == EXPECTED,
        "candidate_is_separate_eye_only_glb": candidate_glb.resolve() not in sources.values(),
    }
    if not all(structural.values()):
        raise RuntimeError(f"R7 eye structural check failed: {structural}")

    if args.visual_decision == "pending":
        visual = {
            "both_irises_centered_and_visible_front": None,
            "both_irises_visible_left_30deg": None,
            "both_irises_visible_right_30deg": None,
            "no_protrusion_left_profile": None,
            "no_protrusion_right_profile": None,
            "plausible_closed_blink": None,
            "plausible_left_right_up_down_gaze": None,
            "realistic_brown_iris_material_not_flat_or_mechanical": None,
            "visual_fit_passed": None,
        }
    elif args.visual_decision == "accept":
        visual = {
            "both_irises_centered_and_visible_front": True,
            "both_irises_visible_left_30deg": True,
            "both_irises_visible_right_30deg": True,
            "no_protrusion_left_profile": True,
            "no_protrusion_right_profile": True,
            "plausible_closed_blink": True,
            "plausible_left_right_up_down_gaze": True,
            "realistic_brown_iris_material_not_flat_or_mechanical": True,
            "visual_fit_passed": True,
        }
    else:
        # Fixed-view inspection of this concrete candidate proves the socket
        # position, profile containment, and gaze controls, but the authored
        # iris still reads as a flat procedural disc and the lid closure is
        # not yet integrated naturally with the R6 face.  Preserve those
        # useful positive findings while failing the complete visual gate.
        visual = {
            "both_irises_centered_and_visible_front": True,
            "both_irises_visible_left_30deg": True,
            "both_irises_visible_right_30deg": True,
            "no_protrusion_left_profile": True,
            "no_protrusion_right_profile": True,
            "plausible_closed_blink": False,
            "plausible_left_right_up_down_gaze": True,
            "realistic_brown_iris_material_not_flat_or_mechanical": False,
            "visual_fit_passed": False,
        }
    visual["promotion_allowed"] = False
    visual["owner_review_required_before_any_promotion"] = True
    visual["note"] = (
        "Null fields require original-resolution visual inspection."
        if args.visual_decision == "pending"
        else "Author-recorded fixed-view decision; owner review and a separate promotion task are still required."
    )
    status = (
        "inactive_fixed_view_review_pending"
        if args.visual_decision == "pending"
        else "inactive_visual_fit_candidate_passed_owner_review_pending"
        if args.visual_decision == "accept"
        else "rejected_visual_fit"
    )
    evidence_path = output / "evidence.json"
    evidence = {
        "schema_version": 1,
        "candidate_id": args.candidate_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "kind": "offline_blender_inactive_eye_only_authoring_no_activation_no_binding_no_runtime_write",
        "status": status,
        "promotion_allowed": False,
        "sources": {key: {"path": rel(path), "sha256": hashes_before[key]} for key, path in sources.items()},
        "candidate": file_record(candidate_glb),
        "offline_review_blend": file_record(blend_path),
        "parameters": {
            "measured_socket_centers_blender_native": {
                side.lower(): [float(value) for value in center] for side, center in EYE_CENTERS.items()
            },
            "sclera_half_width_mm": args.sclera_half_width_mm,
            "sclera_half_height_mm": args.sclera_half_height_mm,
            "sclera_front_y": args.sclera_front_y,
            "sclera_rim_y": args.sclera_rim_y,
            "iris_radius_mm": args.iris_radius_mm,
            "iris_front_y": args.iris_front_y,
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
            "A structural pass does not prove visual fit.",
            "Owner approval and a separate reversible promotion task remain mandatory even after a visual pass.",
        ],
    }
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": status,
        "candidate": file_record(candidate_glb),
        "evidence": file_record(evidence_path),
        "fixed_render_count": len(views),
        "structural_checks": structural,
    }, indent=2))


if __name__ == "__main__":
    main()
