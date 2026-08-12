"""Build a non-destructive, independently controllable brown-eye rig for Kira.

The source body is imported only for socket calibration and rendered review.
It is never overwritten.  The primary deliverable is an eye-only GLB whose
nodes use the source body's native coordinates, so Home World can attach the
rig to Kira's head bone without replacing the existing body.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy  # type: ignore
from mathutils import Vector  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_BODY = ROOT / "Avatar/models/temp_ai/kira/avatar.glb"
DEFAULT_OUTPUT = ROOT / "Avatar/models/staged/kira/eyes/kira_brown_eye_rig_v3_2"

# Measured from Kira's exact active body (SHA-256 starts 3ec62ba8d70a).
# Blender native axes: X left/right, Y depth (negative is face-forward), Z up.
EYE_CENTERS = {
    "Left": Vector((-0.02232, -0.03980, 1.10676)),
    "Right": Vector((0.02232, -0.03980, 1.10676)),
}
EYE_RADIUS = 0.00860
IRIS_RADIUS = EYE_RADIUS * 0.355
PUPIL_RADIUS = IRIS_RADIUS * 0.43
OPEN_HALF_HEIGHT = 0.00345
APERTURE_HALF_WIDTH = 0.00945


def args() -> Path:
    if "--" in sys.argv:
        values = sys.argv[sys.argv.index("--") + 1 :]
        if values:
            return Path(values[0]).resolve()
    return DEFAULT_OUTPUT


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def principled(name: str, color, roughness: float, **values):
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


def setup_materials() -> dict[str, object]:
    materials = {
        "skin": principled("Kira_Eyelid_Skin", (0.43, 0.255, 0.180, 1.0), 0.60),
        "review_skin": principled("Kira_Runtime_Review_Skin", (0.43, 0.255, 0.180, 1.0), 0.60),
        "sclera": principled("Kira_Sclera_Warm_White", (0.74, 0.64, 0.57, 1.0), 0.40, **{"Coat Weight": 0.16}),
        "limbal": principled("Kira_Iris_Limbal_Ring", (0.025, 0.006, 0.002, 1.0), 0.40),
        "iris_dark": principled("Kira_Iris_Warm_Brown_Dark", (0.042, 0.010, 0.002, 1.0), 0.43),
        "iris_mid": principled("Kira_Iris_Warm_Brown_Mid", (0.125, 0.036, 0.007, 1.0), 0.39),
        "iris_light": principled("Kira_Iris_Warm_Brown_Light", (0.275, 0.090, 0.018, 1.0), 0.36),
        "pupil": principled("Kira_Pupil", (0.001, 0.0005, 0.0002, 1.0), 0.23),
    }
    cornea = principled(
        "Kira_Cornea_Clear",
        (0.74, 0.64, 0.57, 1.0),
        0.10,
        **{"IOR": 1.376, "Alpha": 0.0, "Transmission Weight": 0.0, "Coat Weight": 0.0},
    )
    cornea.surface_render_method = "DITHERED"
    materials["cornea"] = cornea
    return materials


def new_empty(name: str, location=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "SPHERE"
    obj.empty_display_size = 0.0035
    obj.location = location
    bpy.context.collection.objects.link(obj)
    if parent:
        obj.parent = parent
    return obj


def parent_keep_world(obj, parent) -> None:
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world


def smooth_object(obj) -> None:
    for polygon in obj.data.polygons:
        polygon.use_smooth = True


def uv_sphere(name: str, location, scale, material, segments=48, rings=24, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        radius=1.0,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.scale = scale
    obj.data.materials.append(material)
    smooth_object(obj)
    bpy.context.view_layer.update()
    if parent:
        parent_keep_world(obj, parent)
    return obj


def uv_sphere_local(name: str, location, scale, material, parent, segments=48, rings=24):
    """Create a sphere whose transform is expressed in its controller's space.

    This deliberately avoids keep-world parenting.  The failed v1 build mixed
    world and parent-local coordinates, which made gaze rotations orbit the
    eyes around a distant point.
    """
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        radius=1.0,
        location=(0.0, 0.0, 0.0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.parent = parent
    obj.location = location
    obj.scale = scale
    obj.data.materials.append(material)
    smooth_object(obj)
    return obj


def iris_mesh(name: str, materials: dict, parent):
    rings = 7
    sectors = 48
    vertices = []
    for ring in range(rings + 1):
        ratio = ring / rings
        radius = IRIS_RADIUS * ratio
        bulge = 0.00034 * (1.0 - ratio * ratio)
        for sector in range(sectors):
            angle = 2.0 * math.pi * sector / sectors
            vertices.append((
                math.cos(angle) * radius,
                -EYE_RADIUS * 0.985 - 0.00018 - bulge,
                math.sin(angle) * radius,
            ))
    faces = []
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
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for key in ("iris_dark", "iris_mid", "iris_light"):
        mesh.materials.append(materials[key])
    for index, polygon in enumerate(mesh.polygons):
        ring = index // sectors
        sector = index % sectors
        if ring == rings - 1:
            polygon.material_index = 0
        elif (sector + ring * 3) % 7 in (0, 1):
            polygon.material_index = 2
        else:
            polygon.material_index = 1 if ring % 2 else 0
        polygon.use_smooth = True
    obj.parent = parent
    obj.location = (0.0, 0.0, 0.0)
    return obj


def almond_sclera_mesh(name: str, center: Vector, material, parent):
    """Make a convex almond ocular surface that fits the base head opening."""
    sectors = 64
    vertices = [(center.x, center.y - 0.00125, center.z)]
    for index in range(sectors):
        angle = 2.0 * math.pi * index / sectors
        x = math.cos(angle) * APERTURE_HALF_WIDTH
        # A sin-weighted height creates tapered inner/outer eye corners.
        z = math.sin(angle) * OPEN_HALF_HEIGHT
        radial = math.sqrt((x / APERTURE_HALF_WIDTH) ** 2 + (z / OPEN_HALF_HEIGHT) ** 2)
        y = center.y - 0.00125 * max(0.0, 1.0 - radial * radial)
        vertices.append((center.x + x, y, center.z + z))
    faces = []
    for index in range(sectors):
        faces.append((0, index + 1, ((index + 1) % sectors) + 1))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    parent_keep_world(obj, parent)
    return obj


def eyelid_mesh(name: str, upper: bool, material, parent):
    """Create a curved half-almond lid with an open and a closed shape.

    The Basis is a narrow band parked behind the socket rim.  The Blink target
    expands that band over one half of the aperture and moves it just in front
    of the seated globe.  Together the upper and lower surfaces fully occlude
    the eye; they are not the flat horizontal strips used by the rejected v1.
    """
    samples = 33
    rows = 9
    vertices = []
    closed_locations = []
    for row in range(rows):
        v = row / (rows - 1)
        for index in range(samples):
            u = -1.0 + 2.0 * index / (samples - 1)
            x = APERTURE_HALF_WIDTH * u
            arch = math.sqrt(max(0.0, 1.0 - u * u))
            rim_z = OPEN_HALF_HEIGHT * arch * (1.0 if upper else -1.0)
            # Preserve a very narrow non-degenerate open band behind the face.
            base_step = 0.00024 * arch * v * (-1.0 if upper else 1.0)
            vertices.append((x, 0.0065, rim_z + base_step))

            # Slight overlap at the center seam prevents an iris-colored slit
            # at a fully closed blink.
            seam_z = (-0.00125 if upper else -0.00100) * arch
            closed_z = rim_z * (1.0 - v) + seam_z * v
            # Convex, socket-fitted surface: center is slightly farther forward
            # than the perimeter, while the perimeter meets the measured face.
            edge_ratio = abs(x) / APERTURE_HALF_WIDTH
            height_ratio = abs(closed_z) / OPEN_HALF_HEIGHT
            radial2 = min(1.0, edge_ratio * edge_ratio + height_ratio * height_ratio)
            # A flush closure only needs to clear the globe by a fraction of a
            # millimeter.  The upper surface sits 0.13 mm forward of the lower
            # one so their overlap reads as a soft lid seam, not a raised plug.
            closed_y = (-0.00945 if upper else -0.00932) + 0.00035 * radial2
            closed_locations.append((x, closed_y, closed_z))
    faces = []
    for row in range(rows - 1):
        for index in range(samples - 1):
            a = row * samples + index
            b = a + 1
            c = (row + 1) * samples + index + 1
            d = (row + 1) * samples + index
            faces.append((a, d, c, b) if upper else (a, b, c, d))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.location = (0.0, 0.0, 0.0)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    obj.shape_key_add(name="Basis")
    blink = obj.shape_key_add(name="Blink")
    for index, location in enumerate(closed_locations):
        blink.data[index].co = Vector(location)
    return obj


def build_eye(side: str, center: Vector, rig_root, materials: dict) -> dict:
    socket = new_empty(f"Kira{side}EyeSocket", center, rig_root)
    # All controller children are authored in pivot-local coordinates.  This is
    # the key v2 correction: the eye turns around its own center and can never
    # orbit or translate out of the socket.
    pivot = new_empty(f"Kira{side}EyePivot", (0.0, 0.0, 0.0), socket)

    sclera = uv_sphere_local(
        f"Kira{side}Sclera",
        (0.0, 0.0, 0.0),
        (EYE_RADIUS, EYE_RADIUS * 0.98, EYE_RADIUS),
        materials["sclera"],
        pivot,
    )
    limbal = uv_sphere_local(
        f"Kira{side}LimbalRing",
        (0.0, -EYE_RADIUS * 0.982, 0.0),
        (IRIS_RADIUS * 1.08, EYE_RADIUS * 0.018, IRIS_RADIUS * 1.08),
        materials["limbal"],
        pivot,
        segments=40,
        rings=16,
    )
    iris = iris_mesh(f"Kira{side}Iris", materials, pivot)
    pupil = uv_sphere_local(
        f"Kira{side}Pupil",
        (0.0, -EYE_RADIUS * 1.035, 0.0),
        (PUPIL_RADIUS, EYE_RADIUS * 0.012, PUPIL_RADIUS),
        materials["pupil"],
        pivot,
        segments=32,
        rings=12,
    )
    cornea = uv_sphere_local(
        f"Kira{side}Cornea",
        (0.0, -EYE_RADIUS * 1.010, 0.0),
        (IRIS_RADIUS * 1.18, EYE_RADIUS * 0.055, IRIS_RADIUS * 1.18),
        materials["cornea"],
        pivot,
        segments=48,
        rings=18,
    )
    upper_lid = eyelid_mesh(f"Kira{side}UpperLid", True, materials["skin"], socket)
    lower_lid = eyelid_mesh(f"Kira{side}LowerLid", False, materials["skin"], socket)
    socket["side"] = side.lower()
    socket["socket_center_native"] = list(center)
    pivot["yaw_limit_degrees"] = 30.0
    pivot["pitch_limit_degrees"] = 20.0
    pivot["convergence_limit_degrees"] = 8.0
    return {
        "socket": socket,
        "pivot": pivot,
        "sclera": sclera,
        "limbal": limbal,
        "iris": iris,
        "pupil": pupil,
        "cornea": cornea,
        "upper_lid": upper_lid,
        "lower_lid": lower_lid,
    }


def descendants(root) -> list:
    output = [root]
    for child in root.children:
        output.extend(descendants(child))
    return output


def set_selected(objects) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]


def look_at(obj, target) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_review_camera_and_lights():
    bpy.ops.object.camera_add(location=(0.0, -1.0, 1.105))
    camera = bpy.context.object
    camera.name = "KiraEyeReviewCamera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.185
    look_at(camera, (0.0, -0.03, 1.105))
    bpy.context.scene.camera = camera

    for name, location, energy, size in (
        ("KiraEyeKey", (-0.55, -0.75, 1.42), 82, 0.70),
        ("KiraEyeFill", (0.55, -0.45, 1.20), 38, 0.55),
        ("KiraEyeRim", (0.0, 0.15, 1.38), 52, 0.40),
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        look_at(light, (0.0, -0.02, 1.10))
    return camera


def set_eye_pose(eyes: dict, yaw_degrees=0.0, pitch_degrees=0.0, convergence_degrees=0.0, blink=0.0):
    for side, record in eyes.items():
        convergence = convergence_degrees if side == "Left" else -convergence_degrees
        record["pivot"].rotation_euler = (
            math.radians(-pitch_degrees),
            0.0,
            math.radians(yaw_degrees + convergence),
        )
        for lid_name in ("upper_lid", "lower_lid"):
            lid = record[lid_name]
            if lid.data.shape_keys:
                lid.data.shape_keys.key_blocks["Blink"].value = blink


def render(path: Path, camera, location=None, target=None, ortho_scale=None):
    if location is not None:
        camera.location = location
    if target is not None:
        look_at(camera, target)
    if ortho_scale is not None:
        camera.data.ortho_scale = ortho_scale
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    output_dir = args()
    output_dir.mkdir(parents=True, exist_ok=True)
    render_dir = output_dir / "renders"
    render_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat()

    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(SOURCE_BODY))
    body_meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and len(obj.data.vertices) > 1000]
    if not body_meshes:
        raise RuntimeError("Kira body mesh was not found")
    body = max(body_meshes, key=lambda obj: len(obj.data.vertices))
    for obj in list(bpy.context.scene.objects):
        if obj.type == "MESH" and len(obj.data.vertices) <= 100 and obj.name.lower().startswith("icosphere"):
            bpy.data.objects.remove(obj, do_unlink=True)

    materials = setup_materials()
    body.data.materials.clear()
    body.data.materials.append(materials["review_skin"])
    rig_root = new_empty("KiraBrownEyeRig_v3_2", (0, 0, 0))
    rig_root["schema_version"] = 32
    rig_root["asset_version"] = "3.2"
    rig_root["candidate_id"] = "kira"
    rig_root["source_body_sha256"] = sha256(SOURCE_BODY)
    rig_root["eye_color"] = "realistic warm brown"
    rig_root["coordinate_space"] = "Kira active avatar native Blender coordinates; glTF Y-up conversion expected"
    rig_root["runtime_policy"] = "staged opt-in until Robert reviews rendered and Home World evidence"
    eyes = {side: build_eye(side, center, rig_root, materials) for side, center in EYE_CENTERS.items()}
    bpy.context.view_layer.update()

    eye_glb = output_dir / "kira_brown_eye_rig_v3_2.glb"
    set_eye_pose(eyes)
    set_selected(descendants(rig_root))
    bpy.ops.export_scene.gltf(
        filepath=str(eye_glb),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_animations=False,
        export_morph=True,
        export_apply=False,
        export_extras=True,
    )

    review_glb = output_dir / "kira_body_with_staged_brown_eye_rig_v3_2.glb"
    selectable = [obj for obj in bpy.context.scene.objects if obj.type not in {"CAMERA", "LIGHT"}]
    set_selected(selectable)
    bpy.ops.export_scene.gltf(
        filepath=str(review_glb),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_animations=False,
        export_morph=True,
        export_apply=False,
        export_extras=True,
    )

    camera = add_review_camera_and_lights()
    scene = bpy.context.scene
    # Blender 5 exposes the current Eevee engine as BLENDER_EEVEE; older 4.x
    # builds used BLENDER_EEVEE_NEXT.
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.018, 0.022, 0.030)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -1.05

    views = {}
    poses = {
        "center": (0, 0, 0, 0),
        "look_left_extreme": (-22, 0, 0, 0),
        "look_right_extreme": (22, 0, 0, 0),
        "look_up": (0, 15, 0, 0),
        "look_down": (0, -15, 0, 0),
        "near_convergence": (0, 0, 6.0, 0),
        "blink_closed": (0, 0, 0, 1.0),
    }
    for name, pose in poses.items():
        set_eye_pose(eyes, yaw_degrees=pose[0], pitch_degrees=pose[1], convergence_degrees=pose[2], blink=pose[3])
        path = render_dir / f"{name}.png"
        render(path, camera, (0.0, -1.0, 1.105), (0.0, -0.03, 1.105), 0.185)
        views[name] = str(path)
    set_eye_pose(eyes)
    three_quarter = render_dir / "three_quarter.png"
    render(three_quarter, camera, (0.19, -0.92, 1.11), (0.0, -0.025, 1.105), 0.19)
    views["three_quarter"] = str(three_quarter)

    blend_path = output_dir / "kira_brown_eye_rig_review_v3_2.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    manifest = {
        "schema_version": 32,
        "asset_version": "3.2",
        "created_at": created_at,
        "candidate_id": "kira",
        "status": "staged_opt_in_pending_robert_visual_review",
        "source_body": str(SOURCE_BODY),
        "source_body_sha256": sha256(SOURCE_BODY),
        "source_body_changed": False,
        "eye_rig": str(eye_glb),
        "eye_rig_sha256": sha256(eye_glb),
        "review_model": str(review_glb),
        "review_model_sha256": sha256(review_glb),
        "review_blend": str(blend_path),
        "eye_color": "warm brown",
        "native_eye_centers": {side.lower(): [round(float(v), 6) for v in center] for side, center in EYE_CENTERS.items()},
        "eye_radius": EYE_RADIUS,
        "independent_controls": {
            "left_pivot": "KiraLeftEyePivot",
            "right_pivot": "KiraRightEyePivot",
            "left_blink_morphs": ["KiraLeftUpperLid:Blink", "KiraLeftLowerLid:Blink"],
            "right_blink_morphs": ["KiraRightUpperLid:Blink", "KiraRightLowerLid:Blink"],
            "yaw_limit_degrees": 30,
            "pitch_limit_degrees": 20,
            "convergence_limit_degrees": 8,
        },
        "parts_per_eye": ["socket", "pivot", "warm sclera", "limbal ring", "multi-tone brown iris", "black pupil", "clear cornea", "upper lid", "lower lid"],
        "renders": views,
        "known_limits": [
            "This is a staged eye rig, not a final Kira face likeness or approved replacement body.",
            "Eyelid skin is a fitted overlay because the current body has no facial blendshape rig.",
            "Rendered evidence must be reviewed before the opt-in runtime flag becomes a default.",
            "The body remains the current generic adult base; this task does not alter body topology, hair, or clothing.",
        ],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "eye_rig": str(eye_glb), "manifest": str(manifest_path)}))


if __name__ == "__main__":
    main()
