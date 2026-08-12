"""Append-only Kira R21 eyebrow-only correction.

This worker replaces only ``Kira_R19_Accepted_Brows01`` in the complete,
private, inactive R21 attempt-08 review candidate. It creates two lightweight
mesh-strand brows that follow the accepted brow ridge, taper at every tip, and
carry native inner/mid/outer brow-bone weights. It does not edit the face,
body, eyes, rig, pelvis, nails, scalp, or hair.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


PROJECT = Path(r"C:\Users\robmc\Kira")
SOURCE_BLEND = PROJECT / "Avatar" / "private_owner_review" / "kira_r21_bald_localized_correction_attempt_08_review" / "KIRA_R21_BALD_PRIVATE_INACTIVE_PELVIS_ATTEMPT08_REVIEW.blend"
SOURCE_BLEND_SHA256 = "bb4d9a4b0d11c17047001278d7dadd105857bcc976ae7c0ec15a93b7945b00e4"
OUTPUT_DIR = PROJECT / "Avatar" / "private_owner_review" / "kira_r21_brow_only_correction_attempt_01"
OUTPUT_BLEND = OUTPUT_DIR / "KIRA_R21_BALD_PRIVATE_INACTIVE_BROW_ATTEMPT01_REVIEW.blend"
EVIDENCE_DIR = PROJECT / "RecoverySprint" / "continuation_20260802" / "kira_r21_brow_only_correction" / "author_attempt_01"
EVIDENCE_PATH = EVIDENCE_DIR / "BUILD_EVIDENCE.json"
README_PATH = OUTPUT_DIR / "OWNER_REVIEW_README.md"

OLD_BROW_NAME = "Kira_R19_Accepted_Brows01"
BODY_NAME = "Kira_R21_Bald_Private_Inactive_Pelvis_Attempt01"
RIG_NAME = "Kira_R19_BlProject_Native_188_Rig"  # corrected by lookup fallback below
RIG_NAME_FALLBACK = "Kira_R19_BlackProject_Native_188_Rig"
NEW_BROW_PREFIX = "Kira_R21_Natural_Tapered_Brow"
CANDIDATE_ID = "kira_r21_brow_only_correction_attempt_01"

STRANDS_PER_SIDE = 184
SAMPLES_PER_STRAND = 5
SURFACE_CLEARANCE_LOCAL = 0.027
RNG_SEED = 21018403


class BrowAuthoringError(RuntimeError):
    pass


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def relative(path: Path) -> str:
    return path.relative_to(PROJECT).as_posix()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def update_text(h: "hashlib._Hash", text: str) -> None:
    encoded = text.encode("utf-8")
    h.update(struct.pack("<I", len(encoded)))
    h.update(encoded)


def mesh_geometry_digest(obj: bpy.types.Object) -> str:
    h = hashlib.sha256()
    mesh = obj.data
    update_text(h, mesh.name)
    for vertex in mesh.vertices:
        h.update(struct.pack("<I3d", int(vertex.index), *map(float, vertex.co)))
    for edge in mesh.edges:
        h.update(struct.pack("<I2I", int(edge.index), *map(int, edge.vertices)))
    for polygon in mesh.polygons:
        h.update(struct.pack("<III", int(polygon.index), int(polygon.material_index), len(polygon.vertices)))
        for index in polygon.vertices:
            h.update(struct.pack("<I", int(index)))
    for layer in mesh.uv_layers:
        update_text(h, layer.name)
        for loop in layer.data:
            h.update(struct.pack("<2d", float(loop.uv.x), float(loop.uv.y)))
    return h.hexdigest()


def weight_digest(obj: bpy.types.Object) -> str:
    h = hashlib.sha256()
    names = {group.index: group.name for group in obj.vertex_groups}
    for index in sorted(names):
        h.update(struct.pack("<I", int(index)))
        update_text(h, names[index])
    for vertex in obj.data.vertices:
        h.update(struct.pack("<I", int(vertex.index)))
        for element in sorted(vertex.groups, key=lambda item: item.group):
            h.update(struct.pack("<Id", int(element.group), float(element.weight)))
    return h.hexdigest()


def matrix_digest(matrix: Any) -> str:
    h = hashlib.sha256()
    for row in matrix:
        h.update(struct.pack("<4d", *map(float, row)))
    return h.hexdigest()


def modifier_digest(obj: bpy.types.Object) -> str:
    h = hashlib.sha256()
    for modifier in obj.modifiers:
        update_text(h, modifier.name)
        update_text(h, modifier.type)
        linked = getattr(modifier, "object", None)
        update_text(h, linked.name if linked else "")
        h.update(struct.pack("<??", bool(modifier.show_viewport), bool(modifier.show_render)))
    return h.hexdigest()


def mesh_object_record(obj: bpy.types.Object) -> dict[str, Any]:
    return {
        "object": obj.name,
        "mesh": obj.data.name,
        "vertex_count": len(obj.data.vertices),
        "edge_count": len(obj.data.edges),
        "polygon_count": len(obj.data.polygons),
        "geometry_uv_sha256": mesh_geometry_digest(obj),
        "positive_weight_assignment_sha256": weight_digest(obj),
        "world_matrix_sha256": matrix_digest(obj.matrix_world),
        "parent": obj.parent.name if obj.parent else None,
        "parent_type": obj.parent_type,
        "parent_bone": obj.parent_bone,
        "modifier_sha256": modifier_digest(obj),
    }


def protected_mesh_snapshot(excluded: set[str]) -> dict[str, dict[str, Any]]:
    return {
        obj.name: mesh_object_record(obj)
        for obj in sorted(bpy.data.objects, key=lambda item: item.name)
        if obj.type == "MESH" and obj.name not in excluded
    }


def armature_digest(rig: bpy.types.Object) -> str:
    h = hashlib.sha256()
    update_text(h, rig.name)
    h.update(bytes.fromhex(matrix_digest(rig.matrix_world)))
    for bone in rig.data.bones:
        update_text(h, bone.name)
        update_text(h, bone.parent.name if bone.parent else "")
        h.update(struct.pack("<3d", *map(float, bone.head_local)))
        h.update(struct.pack("<3d", *map(float, bone.tail_local)))
        h.update(struct.pack("<??", bool(bone.use_deform), bool(bone.use_connect)))
        for row in bone.matrix_local:
            h.update(struct.pack("<4d", *map(float, row)))
    for pose_bone in rig.pose.bones:
        update_text(h, pose_bone.name)
        h.update(struct.pack("<3d", *map(float, pose_bone.location)))
        h.update(struct.pack("<4d", *map(float, pose_bone.rotation_quaternion)))
        h.update(struct.pack("<3d", *map(float, pose_bone.scale)))
        for row in pose_bone.matrix_basis:
            h.update(struct.pack("<4d", *map(float, row)))
    return h.hexdigest()


def percentile(values: Iterable[float], fraction: float) -> float:
    ordered = sorted(map(float, values))
    if not ordered:
        raise BrowAuthoringError("empty percentile input")
    position = max(0.0, min(1.0, float(fraction))) * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def old_brow_body_local_points(body: bpy.types.Object, brow: bpy.types.Object) -> list[Vector]:
    inverse = body.matrix_world.inverted()
    return [inverse @ (brow.matrix_world @ vertex.co) for vertex in brow.data.vertices]


def robust_side_anchor(points: list[Vector], sign: float) -> dict[str, float]:
    selected = [point for point in points if (point.x < 0.0 if sign < 0.0 else point.x > 0.0)]
    if len(selected) < 100:
        raise BrowAuthoringError("source brow does not contain enough points on both sides")
    absolute_x = [abs(float(point.x)) for point in selected]
    return {
        "inner_abs_x": percentile(absolute_x, 0.01),
        "outer_abs_x": percentile(absolute_x, 0.99),
        "median_z": percentile([float(point.z) for point in selected], 0.50),
        "z_p01": percentile([float(point.z) for point in selected], 0.01),
        "z_p99": percentile([float(point.z) for point in selected], 0.99),
    }


def body_local_bvh(body: bpy.types.Object) -> tuple[BVHTree, float, float]:
    vertices = [vertex.co.copy() for vertex in body.data.vertices]
    faces = [[int(index) for index in polygon.vertices] for polygon in body.data.polygons]
    return (
        BVHTree.FromPolygons(vertices, faces, all_triangles=False),
        min(float(point.y) for point in vertices),
        max(float(point.y) for point in vertices),
    )


def projected_front_point(
    tree: BVHTree,
    y_min: float,
    y_max: float,
    x: float,
    z: float,
    clearance: float,
) -> Vector:
    origin = Vector((float(x), y_min - 2.0, float(z)))
    hit, _normal, _face, _distance = tree.ray_cast(
        origin,
        Vector((0.0, 1.0, 0.0)),
        max(4.0, y_max - y_min + 4.0),
    )
    if hit is None:
        raise BrowAuthoringError(f"brow projection missed accepted face at x={x:.6f}, z={z:.6f}")
    return Vector((float(x), float(hit.y) - float(clearance), float(z)))


def brow_material(name: str, linear_rgba: tuple[float, float, float, float], roughness: float) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = linear_rgba
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled is None:
        raise BrowAuthoringError("new brow material has no Principled BSDF")
    principled.inputs["Base Color"].default_value = linear_rgba
    principled.inputs["Roughness"].default_value = float(roughness)
    principled.inputs["Metallic"].default_value = 0.0
    if "Specular IOR Level" in principled.inputs:
        principled.inputs["Specular IOR Level"].default_value = 0.20
    if "Coat Weight" in principled.inputs:
        principled.inputs["Coat Weight"].default_value = 0.0
    material["eyebrow_only"] = True
    material["scalp_hair_material"] = False
    material["candidate_id"] = CANDIDATE_ID
    return material


def gaussian_weights(u: float) -> tuple[float, float, float]:
    raw = (
        math.exp(-((u - 0.00) / 0.31) ** 2),
        math.exp(-((u - 0.52) / 0.30) ** 2),
        math.exp(-((u - 1.00) / 0.29) ** 2),
    )
    total = sum(raw)
    return tuple(value / total for value in raw)


def create_side_brow(
    *,
    body: bpy.types.Object,
    rig: bpy.types.Object,
    tree: BVHTree,
    y_min: float,
    y_max: float,
    anchor: dict[str, float],
    sign: float,
    label: str,
    materials: list[bpy.types.Material],
    rng: random.Random,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []
    face_materials: list[int] = []
    strand_vertex_ranges: list[tuple[list[int], float]] = []
    inner = anchor["inner_abs_x"]
    outer = anchor["outer_abs_x"]
    median_z = anchor["median_z"]
    if not 3.5 <= outer - inner <= 6.5:
        raise BrowAuthoringError(f"implausible inherited brow span for {label}: {outer-inner}")

    for strand in range(STRANDS_PER_SIDE):
        base_u = (strand + 0.5) / STRANDS_PER_SIDE
        jitter_u = (rng.random() - 0.5) * (0.78 / STRANDS_PER_SIDE)
        u = min(0.997, max(0.003, base_u + jitter_u))
        x_root = sign * (inner + (outer - inner) * u)

        arch = math.sin(math.pi * (u ** 0.92))
        center_z = median_z - 0.12 + 0.55 * arch - 0.07 * u
        half_band = max(0.11, 0.28 + 0.15 * (arch ** 0.75) - 0.16 * u)
        low_discrepancy = ((strand * 0.6180339887498949 + (0.17 if sign > 0 else 0.43)) % 1.0) - 0.5
        z_root = center_z + low_discrepancy * 2.0 * half_band + (rng.random() - 0.5) * 0.045

        flow_degrees = 56.0 - 61.0 * u + (rng.random() - 0.5) * 8.0
        flow = math.radians(flow_degrees)
        length = (0.39 + 0.13 * (1.0 - abs(2.0 * u - 0.75)) + (rng.random() - 0.5) * 0.055)
        length *= 0.78 + 0.22 * math.sin(math.pi * min(1.0, u + 0.05))
        dx = sign * math.cos(flow) * length
        dz = math.sin(flow) * length
        curvature = (0.045 + 0.030 * arch) * (0.85 + 0.30 * rng.random())
        half_width = (0.0120 + 0.0035 * rng.random()) * (0.78 + 0.22 * arch)
        clearance = SURFACE_CLEARANCE_LOCAL + (rng.random() - 0.5) * 0.004

        centerline = []
        for sample in range(SAMPLES_PER_STRAND):
            t = sample / (SAMPLES_PER_STRAND - 1)
            ease = t * (0.92 + 0.08 * t)
            centerline.append(
                Vector(
                    (
                        x_root + dx * ease,
                        0.0,
                        z_root + dz * ease + curvature * math.sin(math.pi * t),
                    )
                )
            )
        created_indices: list[int] = []
        for sample, center in enumerate(centerline):
            if sample == 0:
                tangent = centerline[1] - centerline[0]
            elif sample == len(centerline) - 1:
                tangent = centerline[-1] - centerline[-2]
            else:
                tangent = centerline[sample + 1] - centerline[sample - 1]
            tangent.y = 0.0
            tangent.normalize()
            cross = Vector((-tangent.z, 0.0, tangent.x))
            taper = (1.00, 0.90, 0.67, 0.36, 0.045)[sample]
            width = half_width * taper
            left = center - cross * width
            right = center + cross * width
            for point in (left, right):
                projected = projected_front_point(tree, y_min, y_max, point.x, point.z, clearance)
                created_indices.append(len(vertices))
                vertices.append(tuple(projected))
            if sample:
                current = len(vertices) - 2
                previous = current - 2
                faces.append((previous, current, current + 1, previous + 1))
                face_materials.append((strand * 7 + (0 if sign < 0 else 1)) % len(materials))
        strand_vertex_ranges.append((created_indices, u))

    mesh = bpy.data.meshes.new(f"{NEW_BROW_PREFIX}_{label}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    for material in materials:
        mesh.materials.append(material)
    for polygon, material_index in zip(mesh.polygons, face_materials):
        polygon.material_index = int(material_index)
        polygon.use_smooth = True

    obj = bpy.data.objects.new(f"{NEW_BROW_PREFIX}_{label}", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world = body.matrix_world.copy()
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.matrix_parent_inverse = rig.matrix_world.inverted()
    obj.matrix_world = world

    if sign < 0.0:
        bone_names = ("rBrowInner_0119", "rBrowMid_0120", "rBrowOuter_0122")
    else:
        bone_names = ("lBrowInner_0123", "lBrowMid_0124", "lBrowOuter_0125")
    for bone_name in bone_names:
        if rig.pose.bones.get(bone_name) is None:
            raise BrowAuthoringError(f"native brow expression bone missing: {bone_name}")
    groups = [obj.vertex_groups.new(name=bone_name) for bone_name in bone_names]
    for indices, u in strand_vertex_ranges:
        for group, weight in zip(groups, gaussian_weights(u)):
            if weight > 1.0e-6:
                group.add(indices, float(weight), "REPLACE")
    modifier = obj.modifiers.new("R21_Native_Brow_Expression_Attachment", "ARMATURE")
    modifier.object = rig
    obj["candidate_id"] = CANDIDATE_ID
    obj["component_role"] = "eyebrow"
    obj["inactive_candidate"] = True
    obj["private_owner_review_only"] = True
    obj["runtime_activation_allowed"] = False
    obj["scalp_hair"] = False
    obj["strand_count"] = STRANDS_PER_SIDE
    obj["strand_style"] = "dense_curved_tapered_skin_conforming_mesh_ribbons"
    return obj, {
        "object": obj.name,
        "side": label,
        "strand_count": STRANDS_PER_SIDE,
        "samples_per_strand": SAMPLES_PER_STRAND,
        "vertex_count": len(vertices),
        "polygon_count": len(faces),
        "geometry_uv_sha256": mesh_geometry_digest(obj),
        "positive_weight_assignment_sha256": weight_digest(obj),
        "native_expression_bones": list(bone_names),
        "source_anchor": anchor,
        "skin_projection_clearance_local_units": SURFACE_CLEARANCE_LOCAL,
    }


def body_distance_record(body: bpy.types.Object, brow_objects: list[bpy.types.Object]) -> dict[str, Any]:
    body_vertices = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    body_faces = [[int(index) for index in polygon.vertices] for polygon in body.data.polygons]
    tree = BVHTree.FromPolygons(body_vertices, body_faces, all_triangles=False)
    result = {}
    for obj in brow_objects:
        distances = []
        for vertex in obj.data.vertices:
            world = obj.matrix_world @ vertex.co
            _hit, _normal, _face, distance = tree.find_nearest(world)
            if distance is not None:
                distances.append(float(distance))
        ordered = sorted(distances)
        result[obj.name] = {
            "sample_count": len(ordered),
            "minimum_m": ordered[0],
            "median_m": ordered[len(ordered) // 2],
            "maximum_m": ordered[-1],
        }
        if ordered[0] <= 0.00004 or ordered[-1] >= 0.00080:
            raise BrowAuthoringError(
                f"{obj.name} surface clearance outside bounded skin-follow range: "
                f"min={ordered[0]}, max={ordered[-1]}"
            )
    return result


def add_area_light(name: str, location: tuple[float, float, float], target: Vector, energy: float, size: float) -> None:
    data = bpy.data.lights.new(name, "AREA")
    data.energy = float(energy)
    data.shape = "DISK"
    data.size = float(size)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_review(body: bpy.types.Object, brow_objects: list[bpy.types.Object]) -> list[dict[str, Any]]:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1050
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.004, 0.007, 0.012)
    for obj in bpy.data.objects:
        if obj.type in {"LIGHT", "CAMERA"}:
            obj.hide_render = True
    brow_points = [obj.matrix_world @ vertex.co for obj in brow_objects for vertex in obj.data.vertices]
    target = Vector(
        (
            sum(point.x for point in brow_points) / len(brow_points),
            sum(point.y for point in brow_points) / len(brow_points),
            sum(point.z for point in brow_points) / len(brow_points) - 0.025,
        )
    )
    add_area_light("R21_BROW_KEY", (1.5, -2.0, 2.4), target, 730.0, 3.2)
    add_area_light("R21_BROW_FILL", (-1.3, -1.5, 1.8), target, 430.0, 2.6)
    add_area_light("R21_BROW_RIM", (0.2, 1.6, 2.2), target, 500.0, 2.5)
    camera_data = bpy.data.cameras.new("R21_BROW_REVIEW_CAMERA_DATA")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R21_BROW_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = {
        "close_brows_front": (Vector((target.x, target.y - 2.0, target.z)), 0.235),
        "close_brows_left_three_quarter": (Vector((target.x - 0.72, target.y - 1.55, target.z + 0.02)), 0.245),
        "close_brows_right_three_quarter": (Vector((target.x + 0.72, target.y - 1.55, target.z + 0.02)), 0.245),
    }
    records = []
    for name, (location, scale) in views.items():
        camera.location = location
        camera.data.ortho_scale = float(scale)
        camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
        path = OUTPUT_DIR / f"{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        records.append({"label": name, "path": relative(path), "sha256": sha256_file(path)})
    return records


def main() -> None:
    if OUTPUT_DIR.exists() or EVIDENCE_DIR.exists():
        raise FileExistsError("append-only Kira R21 brow Attempt 01 output already exists")
    if Path(bpy.data.filepath).resolve() != SOURCE_BLEND.resolve():
        raise BrowAuthoringError("exact R21 attempt-08 source Blend is not loaded")
    if sha256_file(SOURCE_BLEND) != SOURCE_BLEND_SHA256:
        raise BrowAuthoringError("R21 attempt-08 source Blend hash mismatch")

    body = bpy.data.objects.get(BODY_NAME)
    rig = bpy.data.objects.get(RIG_NAME_FALLBACK) or bpy.data.objects.get(RIG_NAME)
    old_brow = bpy.data.objects.get(OLD_BROW_NAME)
    if body is None or body.type != "MESH":
        raise BrowAuthoringError(f"accepted R21 body missing: {BODY_NAME}")
    if rig is None or rig.type != "ARMATURE":
        raise BrowAuthoringError("native 188-bone rig missing")
    if old_brow is None or old_brow.type != "MESH":
        raise BrowAuthoringError(f"exact rejected brow object missing: {OLD_BROW_NAME}")

    old_brow_record = mesh_object_record(old_brow)
    old_distance = body_distance_record_unbounded(body, [old_brow])
    protected_before = protected_mesh_snapshot({OLD_BROW_NAME})
    rig_before = armature_digest(rig)
    body_before = protected_before[BODY_NAME]
    inherited_object_names = set(protected_before)
    points = old_brow_body_local_points(body, old_brow)
    negative_anchor = robust_side_anchor(points, -1.0)
    positive_anchor = robust_side_anchor(points, 1.0)
    tree, y_min, y_max = body_local_bvh(body)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=False)
    old_mesh = old_brow.data
    bpy.data.objects.remove(old_brow, do_unlink=True)
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)

    materials = [
        brow_material("Kira_R21_Brow_WarmBrown_Dark", (0.028, 0.010, 0.0045, 1.0), 0.72),
        brow_material("Kira_R21_Brow_WarmBrown_Mid", (0.046, 0.017, 0.0070, 1.0), 0.74),
        brow_material("Kira_R21_Brow_WarmBrown_Soft", (0.066, 0.027, 0.0120, 1.0), 0.76),
    ]
    rng = random.Random(RNG_SEED)
    negative, negative_record = create_side_brow(
        body=body,
        rig=rig,
        tree=tree,
        y_min=y_min,
        y_max=y_max,
        anchor=negative_anchor,
        sign=-1.0,
        label="NEGATIVE_X",
        materials=materials,
        rng=rng,
    )
    positive, positive_record = create_side_brow(
        body=body,
        rig=rig,
        tree=tree,
        y_min=y_min,
        y_max=y_max,
        anchor=positive_anchor,
        sign=1.0,
        label="POSITIVE_X",
        materials=materials,
        rng=rng,
    )
    new_brows = [negative, positive]
    distance_before_save = body_distance_record(body, new_brows)

    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND), check_existing=False)
    output_blend_sha = sha256_file(OUTPUT_BLEND)
    if sha256_file(SOURCE_BLEND) != SOURCE_BLEND_SHA256:
        raise BrowAuthoringError("source R21 Blend changed during append-only authoring")

    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT_BLEND))
    body = bpy.data.objects.get(BODY_NAME)
    rig = bpy.data.objects.get(RIG_NAME_FALLBACK) or bpy.data.objects.get(RIG_NAME)
    new_brows = [
        bpy.data.objects.get(f"{NEW_BROW_PREFIX}_NEGATIVE_X"),
        bpy.data.objects.get(f"{NEW_BROW_PREFIX}_POSITIVE_X"),
    ]
    if body is None or rig is None or any(obj is None for obj in new_brows):
        raise BrowAuthoringError("saved candidate did not reopen with exact protected body/rig/new brows")
    if bpy.data.objects.get(OLD_BROW_NAME) is not None:
        raise BrowAuthoringError("rejected old brow object remained instantiated after save")

    protected_after = {
        name: mesh_object_record(bpy.data.objects[name])
        for name in sorted(inherited_object_names)
        if bpy.data.objects.get(name) is not None
    }
    missing = sorted(inherited_object_names.difference(protected_after))
    mismatches = sorted(
        name for name in inherited_object_names.intersection(protected_after)
        if protected_before[name] != protected_after[name]
    )
    rig_after = armature_digest(rig)
    if missing or mismatches or rig_after != rig_before:
        raise BrowAuthoringError(
            f"protected face/body/eye/rig verification failed: missing={missing}, mismatches={mismatches}, rig={rig_after == rig_before}"
        )
    distance_after_reopen = body_distance_record(body, new_brows)
    renders = render_review(body, new_brows)

    evidence = {
        "schema_version": 1,
        "artifact_kind": "KIRA_R21_BROW_ONLY_CORRECTION_BUILD_EVIDENCE",
        "created_utc": now_utc(),
        "status": "PRIVATE_INACTIVE_BROW_ONLY_OWNER_REVIEW_CANDIDATE",
        "candidate_id": CANDIDATE_ID,
        "source": {
            "blend": relative(SOURCE_BLEND),
            "sha256": SOURCE_BLEND_SHA256,
            "source_unchanged_after_authoring": sha256_file(SOURCE_BLEND) == SOURCE_BLEND_SHA256,
            "rejected_brow": old_brow_record,
            "rejected_brow_body_surface_distance": old_distance,
        },
        "authorization_and_scope": {
            "changed": [OLD_BROW_NAME],
            "created": [obj.name for obj in new_brows],
            "approved_face_preserved": True,
            "approved_body_preserved": True,
            "eyes_preserved": True,
            "rig_preserved": True,
            "pelvis_changed": False,
            "nails_changed": False,
            "scalp_or_hair_changed": False,
            "private": True,
            "inactive": True,
            "unassigned": True,
            "unpublished": True,
        },
        "design": {
            "method": "two_dense_curved_tapered_brow_ribbon_meshes_projected_to_accepted_skin",
            "not_painted_lines": True,
            "not_vertical_pickets": True,
            "natural_medial_to_tail_flow": True,
            "detachable_component": True,
            "strand_count_per_side": STRANDS_PER_SIDE,
            "samples_per_strand": SAMPLES_PER_STRAND,
            "total_new_vertices": sum(len(obj.data.vertices) for obj in new_brows),
            "total_new_polygons": sum(len(obj.data.polygons) for obj in new_brows),
            "deterministic_seed": RNG_SEED,
            "side_records": [negative_record, positive_record],
        },
        "skin_attachment": {
            "before_save": distance_before_save,
            "after_reopen": distance_after_reopen,
            "old_rejected_maximum_clearance_m": max(value["maximum_m"] for value in old_distance.values()),
            "new_maximum_clearance_m": max(value["maximum_m"] for value in distance_after_reopen.values()),
            "bounded_skin_follow_gate_passed": True,
        },
        "protected_verification": {
            "protected_inherited_mesh_object_count": len(protected_before),
            "missing_after_reopen": missing,
            "mismatched_after_reopen": mismatches,
            "all_protected_mesh_objects_exact": not missing and not mismatches,
            "body_before": body_before,
            "body_after": protected_after[BODY_NAME],
            "body_exact": body_before == protected_after[BODY_NAME],
            "rig_before_sha256": rig_before,
            "rig_after_sha256": rig_after,
            "rig_exact": rig_before == rig_after,
        },
        "output": {
            "blend": relative(OUTPUT_BLEND),
            "blend_sha256": output_blend_sha,
            "renders": renders,
            "worker": relative(Path(__file__)),
            "worker_sha256": sha256_file(Path(__file__)),
        },
        "truth_boundary": {
            "visual_owner_approval_required": True,
            "candidate_is_not_activated_or_assigned": True,
            "this_attempt_does_not_claim_pelvis_nails_or_movement_approval": True,
        },
    }
    EVIDENCE_PATH.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    README_PATH.write_text(
        "# Kira R21 eyebrow-only owner review\n\n"
        "This append-only private candidate changes only the rejected eyebrow object. "
        "The approved face, body, eyes, and native rig match the source candidate exactly after save/reopen. "
        "Pelvis, nails, scalp, and hair were not changed.\n\n"
        "Review these close views:\n\n"
        "- [Front](close_brows_front.png)\n"
        "- [Left three-quarter](close_brows_left_three_quarter.png)\n"
        "- [Right three-quarter](close_brows_right_three_quarter.png)\n\n"
        "The brows use individually tapered, curved mesh ribbons projected close to the brow ridge and weighted "
        "to the native inner/mid/outer brow expression bones. They are not painted lines, solid plates, or vertical pickets.\n\n"
        "Owner visual approval is still required. This candidate is inactive, unassigned, and unpublished.\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": evidence["status"], "blend": str(OUTPUT_BLEND), "evidence": str(EVIDENCE_PATH)}))


def body_distance_record_unbounded(body: bpy.types.Object, brow_objects: list[bpy.types.Object]) -> dict[str, Any]:
    body_vertices = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    body_faces = [[int(index) for index in polygon.vertices] for polygon in body.data.polygons]
    tree = BVHTree.FromPolygons(body_vertices, body_faces, all_triangles=False)
    result = {}
    for obj in brow_objects:
        distances = []
        for vertex in obj.data.vertices:
            world = obj.matrix_world @ vertex.co
            _hit, _normal, _face, distance = tree.find_nearest(world)
            if distance is not None:
                distances.append(float(distance))
        ordered = sorted(distances)
        result[obj.name] = {
            "sample_count": len(ordered),
            "minimum_m": ordered[0],
            "median_m": ordered[len(ordered) // 2],
            "maximum_m": ordered[-1],
        }
    return result


if __name__ == "__main__":
    main()
