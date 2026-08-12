"""Append-only, nail-only R21 correction candidate.

The accepted R21 body, face, eyes, rig, and pelvis are fingerprinted and left
byte-equivalent in Blender data.  Only the twenty rejected source-native nail
objects are replaced.  Their licensed centers, PCA envelopes, and exact distal
bone bindings are used as placement landmarks; their visually rejected square
geometry is not reused as final geometry.

Run only while no other Blender authoring/render process is active.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
import traceback
from pathlib import Path
from typing import Any, Iterable

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.blender_exact_mesh_intersections as exact_auditor


SOURCE = ROOT / "Avatar/private_owner_review/kira_r21_bald_localized_correction_attempt_08_review/KIRA_R21_BALD_PRIVATE_INACTIVE_PELVIS_ATTEMPT08_REVIEW.blend"
EVIDENCE_DIR = ROOT / "RecoverySprint/continuation_20260802/kira_r21_nail_correction/author_attempt_01"
OWNER_DIR = ROOT / "Avatar/private_owner_review/kira_r21_bald_localized_correction_attempt_09_nails"
OUTPUT_BLEND = OWNER_DIR / "KIRA_R21_BALD_PRIVATE_INACTIVE_PELVIS_NAILS_ATTEMPT09.blend"
EVIDENCE_PATH = EVIDENCE_DIR / "BUILD_EVIDENCE.json"
OWNER_EVIDENCE_PATH = OWNER_DIR / "BUILD_EVIDENCE.json"
FAILURE_PATH = EVIDENCE_DIR / "FAILURE_EVIDENCE.json"
README_PATH = OWNER_DIR / "OWNER_REVIEW_README.md"
MANIFEST_PATH = OWNER_DIR / "FILE_MANIFEST.json"

BODY_NAME = "Kira_R21_Bald_Private_Inactive_Pelvis_Attempt01"
RIG_NAME = "Kira_R19_BlackProject_Native_188_Rig"
GRID_ROWS = 13
GRID_COLUMNS = 9
BASE_CLEARANCE_CANDIDATES = (0.012, 0.020, 0.035, 0.055, 0.080)
PLATE_BASE_THICKNESS = 0.018
PLATE_CENTER_ARCH = 0.024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(chunks: Iterable[bytes]) -> str:
    digest = hashlib.sha256()
    for chunk in chunks:
        digest.update(chunk)
    return digest.hexdigest()


def mesh_signature(obj: bpy.types.Object) -> str:
    chunks: list[bytes] = [obj.name.encode(), obj.data.name.encode()]
    for vertex in obj.data.vertices:
        chunks.append(struct.pack("<3d", *map(float, vertex.co)))
    for polygon in obj.data.polygons:
        chunks.append(struct.pack("<I", len(polygon.vertices)))
        chunks.extend(struct.pack("<I", int(index)) for index in polygon.vertices)
        chunks.append(struct.pack("<i", int(polygon.material_index)))
    for layer in obj.data.uv_layers:
        chunks.append(layer.name.encode())
        for datum in layer.data:
            chunks.append(struct.pack("<2d", *map(float, datum.uv)))
    for vertex in obj.data.vertices:
        for assignment in sorted(vertex.groups, key=lambda item: item.group):
            chunks.append(struct.pack("<Id", int(assignment.group), float(assignment.weight)))
    chunks.extend(group.name.encode() for group in obj.vertex_groups)
    if obj.data.shape_keys is not None:
        for block in obj.data.shape_keys.key_blocks:
            chunks.append(block.name.encode())
            for point in block.data:
                chunks.append(struct.pack("<3d", *map(float, point.co)))
    chunks.extend(
        (slot.material.name if slot.material else "").encode()
        for slot in obj.material_slots
    )
    return sha256_bytes(chunks)


def rig_signature(rig: bpy.types.Object) -> str:
    chunks: list[bytes] = [rig.name.encode()]
    for bone in sorted(rig.data.bones, key=lambda item: item.name):
        chunks.extend(
            [
                bone.name.encode(),
                (bone.parent.name if bone.parent else "").encode(),
                struct.pack("<3d", *map(float, bone.head_local)),
                struct.pack("<3d", *map(float, bone.tail_local)),
                struct.pack("<?", bool(bone.use_deform)),
            ]
        )
    for pose_bone in sorted(rig.pose.bones, key=lambda item: item.name):
        chunks.extend(
            [
                pose_bone.name.encode(),
                pose_bone.rotation_mode.encode(),
                struct.pack("<16d", *(float(value) for row in pose_bone.matrix_basis for value in row)),
            ]
        )
    return sha256_bytes(chunks)


def matrix_record(matrix: Matrix) -> list[list[float]]:
    return [[float(value) for value in row] for row in matrix]


def non_nail_manifest() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        if is_nail(obj):
            continue
        row: dict[str, Any] = {
            "type": obj.type,
            "parent": obj.parent.name if obj.parent else None,
            "parent_type": obj.parent_type,
            "matrix_basis": matrix_record(obj.matrix_basis),
            "matrix_parent_inverse": matrix_record(obj.matrix_parent_inverse),
            "hide_render": bool(obj.hide_render),
            "hide_viewport": bool(obj.hide_viewport),
        }
        if obj.type == "MESH":
            row["mesh_signature_sha256"] = mesh_signature(obj)
        elif obj.type == "ARMATURE":
            row["rig_signature_sha256"] = rig_signature(obj)
        result[obj.name] = row
    return result


def scene_state_record() -> dict[str, Any]:
    scene = bpy.context.scene
    return {
        "scene": scene.name,
        "camera": scene.camera.name if scene.camera else None,
        "render_engine": scene.render.engine,
        "resolution_x": int(scene.render.resolution_x),
        "resolution_y": int(scene.render.resolution_y),
        "resolution_percentage": int(scene.render.resolution_percentage),
        "image_file_format": scene.render.image_settings.file_format,
        "render_filepath": scene.render.filepath,
        "film_transparent": bool(scene.render.film_transparent),
        "world": scene.world.name if scene.world else None,
        "world_color": list(map(float, scene.world.color)) if scene.world else None,
    }


def is_nail(obj: bpy.types.Object) -> bool:
    if obj.type != "MESH":
        return False
    terms = " ".join(
        [obj.name, obj.data.name]
        + [slot.material.name for slot in obj.material_slots if slot.material]
    ).lower()
    return bool(obj.get("nail_component")) or "nail" in terms


def natural_material(name: str, rgba: tuple[float, float, float, float], *, free_edge: bool) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = rgba
    material["kira_r21_natural_nail_material"] = True
    material["role"] = "subtle_translucent_free_edge" if free_edge else "warm_translucent_nail_bed"
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled is None:
        raise RuntimeError("Principled BSDF unavailable")
    values = {
        "Base Color": rgba,
        "Roughness": 0.38 if free_edge else 0.34,
        "Alpha": rgba[3],
        "IOR": 1.376,
        "Coat Weight": 0.07 if free_edge else 0.11,
        "Coat Roughness": 0.32,
        "Transmission Weight": 0.035 if free_edge else 0.025,
        "Subsurface Weight": 0.018,
    }
    for key, value in values.items():
        socket = principled.inputs.get(key)
        if socket is not None:
            socket.default_value = value
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = "DITHERED"
    elif hasattr(material, "blend_method"):
        material.blend_method = "BLEND"
    if hasattr(material, "use_transparency_overlap"):
        material.use_transparency_overlap = False
    return material


def source_definition(obj: bpy.types.Object, rig: bpy.types.Object) -> dict[str, Any]:
    lower = obj.name.lower()
    kind = "toenail" if "toenail" in lower else "fingernail"
    tokens = lower.split("_")
    marker = "toenail" if kind == "toenail" else "fingernail"
    marker_index = tokens.index(marker)
    digit = int(tokens[marker_index + 1])
    side = tokens[marker_index + 2].upper()
    weighted_groups = []
    for group in obj.vertex_groups:
        total = 0.0
        count = 0
        for vertex in obj.data.vertices:
            try:
                weight = float(group.weight(vertex.index))
            except RuntimeError:
                continue
            if weight > 0.0:
                total += weight
                count += 1
        if count:
            weighted_groups.append((total, count, group.name))
    if not weighted_groups:
        raise RuntimeError(f"source nail has no binding: {obj.name}")
    weighted_groups.sort(reverse=True)
    bone_name = weighted_groups[0][2]
    bone = rig.data.bones.get(bone_name)
    if bone is None:
        raise RuntimeError(f"missing distal bone {bone_name}")
    points = np.asarray([tuple(float(value) for value in vertex.co) for vertex in obj.data.vertices], dtype=np.float64)
    center = points.mean(axis=0)
    covariance = np.cov((points - center).T)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    normal = Vector(tuple(float(value) for value in eigenvectors[:, 0])).normalized()
    tangent_a = Vector(tuple(float(value) for value in eigenvectors[:, 1])).normalized()
    tangent_b = Vector(tuple(float(value) for value in eigenvectors[:, 2])).normalized()
    bone_direction = (bone.tail_local - bone.head_local).normalized()
    length = tangent_a if abs(tangent_a.dot(bone_direction)) >= abs(tangent_b.dot(bone_direction)) else tangent_b
    if length.dot(bone_direction) < 0.0:
        length = -length
    length = (length - normal * length.dot(normal)).normalized()
    return {
        "source_object": obj.name,
        "source_mesh": obj.data.name,
        "kind": kind,
        "digit": digit,
        "side": side,
        "bone": bone_name,
        "source_vertex_count": len(obj.data.vertices),
        "source_polygon_count": len(obj.data.polygons),
        "source_mesh_signature_sha256": mesh_signature(obj),
        "source_center_base": Vector(tuple(float(value) for value in center)),
        "source_normal_candidate_base": normal,
        "source_length_candidate_base": length,
        "source_points": points,
        "source_pca_eigenvalues": [float(value) for value in eigenvalues],
        "source_positive_weight_groups": [
            {"name": name, "positive_vertex_count": count, "weight_sum": total}
            for total, count, name in weighted_groups
        ],
    }


def body_geometry(body: bpy.types.Object) -> tuple[list[Vector], list[tuple[int, int, int]], BVHTree]:
    body.data.calc_loop_triangles()
    points = [vertex.co.copy() for vertex in body.data.vertices]
    triangles = [tuple(map(int, triangle.vertices)) for triangle in body.data.loop_triangles]
    return points, triangles, BVHTree.FromPolygons(points, triangles, all_triangles=True)


def exact_cross_record(
    body_points: list[Vector],
    body_triangles: list[tuple[int, int, int]],
    body_tree: BVHTree,
    nail_points: list[Vector],
    nail_triangles: list[tuple[int, int, int]],
) -> dict[str, Any]:
    nail_tree = BVHTree.FromPolygons(nail_points, nail_triangles, all_triangles=True)
    low = Vector(tuple(min(float(point[axis]) for point in body_points) for axis in range(3)))
    high = Vector(tuple(max(float(point[axis]) for point in body_points) for axis in range(3)))
    tolerance = max(1.0e-10, float((high - low).length) * 1.0e-8)
    raw_pairs = sorted(body_tree.overlap(nail_tree))
    counts: dict[str, int] = {}
    genuine: list[list[int]] = []
    for body_index, nail_index in raw_pairs:
        result = exact_auditor.classify_triangle_pair(
            tuple(body_points[index] for index in body_triangles[body_index]),
            tuple(nail_points[index] for index in nail_triangles[nail_index]),
            linear_tolerance=tolerance,
        )
        classification = str(result["classification"])
        counts[classification] = counts.get(classification, 0) + 1
        if result.get("genuine_penetration") is True:
            genuine.append([int(body_index), int(nail_index)])
    return {
        "broad_phase_candidate_pair_count": len(raw_pairs),
        "classification_counts": counts,
        "exact_genuine_penetration_pair_count": len(genuine),
        "exact_genuine_penetration_pairs": genuine,
        "linear_tolerance": tolerance,
    }


def rounded_width_factor(u: float) -> float:
    if u < -0.70:
        t = max(0.0, min(1.0, (u + 1.0) / 0.30))
        smooth = t * t * (3.0 - 2.0 * t)
        return 0.62 + 0.38 * smooth
    if u > 0.68:
        t = max(0.0, min(1.0, (1.0 - u) / 0.32))
        smooth = t * t * (3.0 - 2.0 * t)
        return 0.72 + 0.28 * smooth
    return 1.0


def build_plate_geometry(
    definition: dict[str, Any],
    body_tree: BVHTree,
    clearance: float,
) -> tuple[list[Vector], list[tuple[int, ...]], list[int], dict[str, Any]]:
    source_center: Vector = definition["source_center_base"]
    normal: Vector = definition["source_normal_candidate_base"].copy()
    nearest, nearest_normal, _face, nearest_distance = body_tree.find_nearest(source_center, 4.0)
    if nearest is None or nearest_normal is None:
        raise RuntimeError(f"no body surface near {definition['source_object']}")
    if normal.dot(nearest_normal) < 0.0:
        normal = -normal
    normal.normalize()
    length: Vector = definition["source_length_candidate_base"].copy()
    length = length - normal * length.dot(normal)
    if length.length <= 1.0e-8:
        raise RuntimeError(f"length tangent collapsed for {definition['source_object']}")
    length.normalize()
    bone_direction = (
        bpy.data.objects[RIG_NAME].data.bones[definition["bone"]].tail_local
        - bpy.data.objects[RIG_NAME].data.bones[definition["bone"]].head_local
    ).normalized()
    if length.dot(bone_direction) < 0.0:
        length = -length
    width = normal.cross(length)
    if width.length <= 1.0e-8:
        raise RuntimeError(f"width tangent collapsed for {definition['source_object']}")
    width.normalize()
    length = width.cross(normal).normalized()
    if length.dot(bone_direction) < 0.0:
        length = -length
        width = -width

    points_np: np.ndarray = definition["source_points"]
    centered = points_np - np.asarray(tuple(source_center), dtype=np.float64)
    length_values = centered @ np.asarray(tuple(length), dtype=np.float64)
    width_values = centered @ np.asarray(tuple(width), dtype=np.float64)
    source_length = float(length_values.max() - length_values.min())
    source_width = float(width_values.max() - width_values.min())
    if definition["kind"] == "fingernail":
        length_scale = 0.68 if definition["digit"] == 1 else 0.70
        width_scale = 0.88
        proximal_shift = 0.075
    else:
        length_scale = 0.70 if definition["digit"] == 1 else 0.76
        width_scale = 0.90
        proximal_shift = 0.050
    target_length = source_length * length_scale
    target_width = source_width * width_scale
    nominal_center = source_center - length * (source_length * proximal_shift)
    ray_hit, ray_normal, ray_face, ray_distance = body_tree.ray_cast(
        nominal_center + normal * 3.0,
        -normal,
        6.0,
    )
    if ray_hit is None or ray_normal is None:
        ray_hit, ray_normal, ray_face, ray_distance = body_tree.find_nearest(nominal_center, 4.0)
    if ray_hit is None or ray_normal is None:
        raise RuntimeError(f"center projection failed for {definition['source_object']}")
    if ray_normal.dot(normal) < 0.0:
        ray_normal = -ray_normal
    surface_center = ray_hit.copy()

    bottom: list[Vector] = []
    top: list[Vector] = []
    sample_normals: list[Vector] = []
    projection_distances: list[float] = []
    for row in range(GRID_ROWS):
        u = -1.0 + 2.0 * row / (GRID_ROWS - 1)
        row_width = target_width * 0.5 * rounded_width_factor(u)
        for column in range(GRID_COLUMNS):
            v = -1.0 + 2.0 * column / (GRID_COLUMNS - 1)
            nominal = surface_center + length * (u * target_length * 0.5) + width * (v * row_width)
            hit, hit_normal, _hit_face, hit_distance = body_tree.ray_cast(
                nominal + normal * 2.2,
                -normal,
                4.4,
            )
            if hit is None or hit_normal is None or hit_normal.dot(normal) < 0.15:
                hit, hit_normal, _hit_face, hit_distance = body_tree.find_nearest(nominal, 2.5)
            if hit is None or hit_normal is None:
                raise RuntimeError(f"grid projection failed {definition['source_object']} row={row} col={column}")
            if hit_normal.dot(normal) < 0.0:
                hit_normal = -hit_normal
            hit_normal.normalize()
            if hit_normal.dot(normal) < 0.15:
                raise RuntimeError(f"grid surface winding mismatch {definition['source_object']} row={row} col={column}")
            bottom_point = hit + hit_normal * clearance
            transverse_arch = PLATE_CENTER_ARCH * max(0.0, 1.0 - v * v)
            top_point = bottom_point + hit_normal * (PLATE_BASE_THICKNESS + transverse_arch)
            bottom.append(bottom_point)
            top.append(top_point)
            sample_normals.append(hit_normal.copy())
            projection_distances.append(float(hit_distance))

    count = GRID_ROWS * GRID_COLUMNS
    vertices = bottom + top
    faces: list[tuple[int, ...]] = []
    material_indices: list[int] = []
    for row in range(GRID_ROWS - 1):
        for column in range(GRID_COLUMNS - 1):
            a = row * GRID_COLUMNS + column
            b = (row + 1) * GRID_COLUMNS + column
            c = (row + 1) * GRID_COLUMNS + column + 1
            d = row * GRID_COLUMNS + column + 1
            faces.append((count + a, count + b, count + c, count + d))
            material_indices.append(1 if row == GRID_ROWS - 2 else 0)
            faces.append((d, c, b, a))
            material_indices.append(0)
    for row in range(GRID_ROWS - 1):
        for column in (0, GRID_COLUMNS - 1):
            a = row * GRID_COLUMNS + column
            b = (row + 1) * GRID_COLUMNS + column
            faces.append((a, b, count + b, count + a) if column == GRID_COLUMNS - 1 else (b, a, count + a, count + b))
            material_indices.append(0)
    for row, material_index in ((0, 0), (GRID_ROWS - 1, 1)):
        for column in range(GRID_COLUMNS - 1):
            a = row * GRID_COLUMNS + column
            b = row * GRID_COLUMNS + column + 1
            faces.append((b, a, count + a, count + b) if row == 0 else (a, b, count + b, count + a))
            material_indices.append(material_index)
    details = {
        "source_length_base_units": source_length,
        "source_width_base_units": source_width,
        "target_length_base_units": target_length,
        "target_width_base_units": target_width,
        "length_scale_from_source_envelope": length_scale,
        "width_scale_from_source_envelope": width_scale,
        "proximal_center_shift_source_length_fraction": proximal_shift,
        "base_clearance_base_units": clearance,
        "plate_base_thickness_base_units": PLATE_BASE_THICKNESS,
        "plate_center_arch_base_units": PLATE_CENTER_ARCH,
        "surface_center_base": list(map(float, surface_center)),
        "outward_base": list(map(float, normal)),
        "distal_base": list(map(float, length)),
        "lateral_base": list(map(float, width)),
        "source_center_nearest_distance_base_units": float(nearest_distance),
        "center_projection_face": int(ray_face),
        "center_projection_distance_base_units": float(ray_distance),
        "maximum_grid_projection_distance_base_units": max(projection_distances),
        "minimum_grid_normal_alignment": min(float(value.dot(normal)) for value in sample_normals),
        "grid_rows": GRID_ROWS,
        "grid_columns": GRID_COLUMNS,
        "connected_closed_shell_by_construction": True,
    }
    return vertices, faces, material_indices, details


def create_nail_object(
    definition: dict[str, Any],
    vertices: list[Vector],
    faces: list[tuple[int, ...]],
    material_indices: list[int],
    body: bpy.types.Object,
    rig: bpy.types.Object,
    bed_material: bpy.types.Material,
    edge_material: bpy.types.Material,
) -> bpy.types.Object:
    identifier = f"{definition['kind']}_{definition['digit']}_{definition['side']}"
    name = f"Kira_R21_Natural_{identifier}_Attempt01"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata([tuple(point) for point in vertices], [], faces)
    mesh.materials.append(bed_material)
    mesh.materials.append(edge_material)
    for polygon, index in zip(mesh.polygons, material_indices):
        polygon.material_index = index
        polygon.use_smooth = True
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = rig
    obj.parent_type = "OBJECT"
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_basis = Matrix.Identity(4)
    modifier = obj.modifiers.new("Armature", "ARMATURE")
    modifier.object = rig
    group = obj.vertex_groups.new(name=definition["bone"])
    group.add(list(range(len(mesh.vertices))), 1.0, "REPLACE")
    obj["nail_component"] = True
    obj["nail_kind"] = definition["kind"]
    obj["nail_digit"] = int(definition["digit"])
    obj["nail_side"] = definition["side"]
    obj["terminal_bone"] = definition["bone"]
    obj["component_status"] = "private_inactive_owner_review"
    obj["geometry_policy"] = "short_rounded_curved_translucent_embedded_plate"
    obj["placement_landmark_source"] = definition["source_object"]
    obj["source_native_geometry_reused_as_final"] = False
    return obj


def mesh_points_triangles(obj: bpy.types.Object, *, evaluated: bool) -> tuple[list[Vector], list[tuple[int, int, int]]]:
    if evaluated:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated_obj = obj.evaluated_get(depsgraph)
        mesh = evaluated_obj.to_mesh()
        try:
            mesh.calc_loop_triangles()
            points = [evaluated_obj.matrix_world @ vertex.co for vertex in mesh.vertices]
            triangles = [tuple(map(int, triangle.vertices)) for triangle in mesh.loop_triangles]
        finally:
            evaluated_obj.to_mesh_clear()
        return points, triangles
    obj.data.calc_loop_triangles()
    return (
        [vertex.co.copy() for vertex in obj.data.vertices],
        [tuple(map(int, triangle.vertices)) for triangle in obj.data.loop_triangles],
    )


def clearance_record(points: list[Vector], body_tree: BVHTree) -> dict[str, Any]:
    distances = []
    for point in points:
        _hit, _normal, _face, distance = body_tree.find_nearest(point)
        if distance is None:
            raise RuntimeError("clearance nearest query failed")
        distances.append(float(distance))
    return {
        "sample_count": len(distances),
        "minimum_unsigned_surface_clearance": min(distances),
        "maximum_unsigned_surface_clearance": max(distances),
        "mean_unsigned_surface_clearance": sum(distances) / len(distances),
    }


def evaluated_body_geometry(body: bpy.types.Object) -> tuple[list[Vector], list[tuple[int, int, int]], BVHTree]:
    points, triangles = mesh_points_triangles(body, evaluated=True)
    return points, triangles, BVHTree.FromPolygons(points, triangles, all_triangles=True)


def nail_pair_audit(nails: list[bpy.types.Object]) -> dict[str, Any]:
    geometry = {}
    for nail in nails:
        points, triangles = mesh_points_triangles(nail, evaluated=True)
        geometry[nail.name] = (points, triangles, BVHTree.FromPolygons(points, triangles, all_triangles=True))
    broad_pairs = []
    for index, left in enumerate(nails):
        left_points, left_triangles, left_tree = geometry[left.name]
        for right in nails[index + 1 :]:
            right_points, right_triangles, right_tree = geometry[right.name]
            overlaps = left_tree.overlap(right_tree)
            if overlaps:
                broad_pairs.append({"left": left.name, "right": right.name, "broad_phase_pair_count": len(overlaps)})
    return {
        "tested_object_pair_count": len(nails) * (len(nails) - 1) // 2,
        "object_pairs_with_broad_phase_overlap": broad_pairs,
        "no_nail_to_nail_broad_phase_overlap": not broad_pairs,
    }


def add_lights(scene: bpy.types.Scene) -> list[bpy.types.Object]:
    lights = []
    target = Vector((0.0, -0.02, 0.88))
    for name, location, energy, size in (
        ("R21_NAIL_KEY_TMP", (1.8, -2.1, 2.4), 650.0, 2.0),
        ("R21_NAIL_FILL_TMP", (-1.6, -1.4, 1.7), 420.0, 1.8),
        ("R21_NAIL_RIM_TMP", (0.0, 1.4, 2.5), 520.0, 1.6),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()
        lights.append(obj)
    return lights


def render_review(nails: list[bpy.types.Object], records: list[dict[str, Any]]) -> dict[str, str]:
    scene = bpy.context.scene
    old = {
        "camera": scene.camera,
        "engine": scene.render.engine,
        "resolution_x": scene.render.resolution_x,
        "resolution_y": scene.render.resolution_y,
        "resolution_percentage": scene.render.resolution_percentage,
        "filepath": scene.render.filepath,
        "film_transparent": scene.render.film_transparent,
        "image_file_format": scene.render.image_settings.file_format,
        "world_color": tuple(scene.world.color) if scene.world else None,
    }
    old_hide = {obj.name: bool(obj.hide_render) for obj in bpy.data.objects}
    temporary: list[bpy.types.Object] = []
    try:
        for obj in bpy.data.objects:
            if obj.type == "MESH" and ("Support" in obj.name or "Floor" in obj.name or "Table" in obj.name or "ContextCup" in obj.name):
                obj.hide_render = True
        scene.render.engine = "BLENDER_EEVEE_NEXT"
        scene.render.resolution_x = 800
        scene.render.resolution_y = 800
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.render.film_transparent = False
        if scene.world:
            scene.world.color = (0.006, 0.008, 0.012)
        camera_data = bpy.data.cameras.new("R21_NAIL_CAMERA_TMP")
        camera_data.type = "ORTHO"
        camera = bpy.data.objects.new("R21_NAIL_CAMERA_TMP", camera_data)
        scene.collection.objects.link(camera)
        scene.camera = camera
        temporary.append(camera)
        temporary.extend(add_lights(scene))
        depsgraph = bpy.context.evaluated_depsgraph_get()
        outputs: dict[str, str] = {}
        for kind, label in (("fingernail", "hand"), ("toenail", "foot")):
            for side, side_label in (("L", "left"), ("R", "right")):
                selected = [nail for nail in nails if nail.get("nail_kind") == kind and nail.get("nail_side") == side]
                selected_records = [row for row in records if row["kind"] == kind and row["side"] == side]
                points = []
                for nail in selected:
                    evaluated = nail.evaluated_get(depsgraph)
                    mesh = evaluated.to_mesh()
                    try:
                        points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
                    finally:
                        evaluated.to_mesh_clear()
                low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
                high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
                target = (low + high) * 0.5
                normal = Vector()
                for row in selected_records:
                    base_normal = Vector(row["geometry"]["outward_base"])
                    normal += (bpy.data.objects[BODY_NAME].matrix_world.to_3x3() @ base_normal).normalized()
                normal.normalize()
                lateral_bias = Vector((0.20 if side == "L" else -0.20, -0.08, 0.22 if kind == "fingernail" else 0.12))
                oblique = normal + lateral_bias
                if oblique.length <= 1.0e-8:
                    oblique = normal.copy()
                oblique.normalize()
                span = max(float(value) for value in (high - low))
                scale = max(0.145 if kind == "fingernail" else 0.155, span * (1.50 if kind == "fingernail" else 1.65))
                for view_name, direction in (("dorsal", normal), ("oblique", oblique)):
                    camera.location = target + direction * 0.52
                    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
                    camera.data.ortho_scale = scale
                    path = OWNER_DIR / f"{side_label}_{label}_{view_name}_all_five_close.png"
                    scene.render.filepath = str(path)
                    bpy.ops.render.render(write_still=True)
                    outputs[f"{side_label}_{label}_{view_name}"] = path.name
        return outputs
    finally:
        for name, value in old_hide.items():
            obj = bpy.data.objects.get(name)
            if obj is not None:
                obj.hide_render = value
        for obj in temporary:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data and data.users == 0:
                if isinstance(data, bpy.types.Camera):
                    bpy.data.cameras.remove(data)
                elif isinstance(data, bpy.types.Light):
                    bpy.data.lights.remove(data)
        scene.camera = old["camera"]
        scene.render.engine = old["engine"]
        scene.render.resolution_x = old["resolution_x"]
        scene.render.resolution_y = old["resolution_y"]
        scene.render.resolution_percentage = old["resolution_percentage"]
        scene.render.filepath = old["filepath"]
        scene.render.film_transparent = old["film_transparent"]
        scene.render.image_settings.file_format = old["image_file_format"]
        if scene.world and old["world_color"] is not None:
            scene.world.color = old["world_color"]


def main() -> None:
    if EVIDENCE_DIR.exists() or OWNER_DIR.exists():
        raise RuntimeError("append-only output directory already exists")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=False)
    OWNER_DIR.mkdir(parents=True, exist_ok=False)
    source_sha_before = sha256_file(SOURCE)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    body = bpy.data.objects.get(BODY_NAME)
    rig = bpy.data.objects.get(RIG_NAME)
    if body is None or body.type != "MESH":
        raise RuntimeError("exact R21 body missing")
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError("exact R21 rig missing")
    source_nails = sorted((obj for obj in bpy.data.objects if is_nail(obj)), key=lambda item: item.name)
    if len(source_nails) != 20:
        raise RuntimeError(f"expected 20 source nails, found {len(source_nails)}")

    body_signature_before = mesh_signature(body)
    rig_signature_before = rig_signature(rig)
    non_nail_before = non_nail_manifest()
    scene_state_before = scene_state_record()
    definitions = [source_definition(obj, rig) for obj in source_nails]
    if len({definition["bone"] for definition in definitions}) != 20:
        raise RuntimeError("source nail distal bone mapping not unique")
    body_points, body_triangles, body_tree = body_geometry(body)
    bed_material = natural_material("Kira_R21_Natural_Nail_Bed_Attempt01", (0.61, 0.30, 0.28, 0.86), free_edge=False)
    edge_material = natural_material("Kira_R21_Natural_Nail_Free_Edge_Attempt01", (0.88, 0.72, 0.67, 0.80), free_edge=True)

    for obj in source_nails:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)

    nails: list[bpy.types.Object] = []
    records: list[dict[str, Any]] = []
    for definition in definitions:
        attempts = []
        accepted = None
        for clearance in BASE_CLEARANCE_CANDIDATES:
            vertices, faces, material_indices, geometry = build_plate_geometry(definition, body_tree, clearance)
            triangles = []
            for face in faces:
                if len(face) == 3:
                    triangles.append(tuple(face))
                elif len(face) == 4:
                    triangles.extend([(face[0], face[1], face[2]), (face[0], face[2], face[3])])
            audit = exact_cross_record(body_points, body_triangles, body_tree, vertices, triangles)
            attempt = {
                "base_clearance_base_units": clearance,
                "exact_intersections": audit,
            }
            attempts.append(attempt)
            if audit["exact_genuine_penetration_pair_count"] == 0:
                accepted = (vertices, faces, material_indices, geometry, audit)
                break
        if accepted is None:
            raise RuntimeError(f"no intersection-free clearance for {definition['source_object']}: {attempts}")
        vertices, faces, material_indices, geometry, raw_audit = accepted
        nail = create_nail_object(definition, vertices, faces, material_indices, body, rig, bed_material, edge_material)
        nails.append(nail)
        record = {
            "nail_id": f"{definition['kind']}_{definition['digit']}_{definition['side']}",
            "kind": definition["kind"],
            "digit": definition["digit"],
            "side": definition["side"],
            "object": nail.name,
            "mesh": nail.data.name,
            "bone": definition["bone"],
            "source_landmark": {
                "object": definition["source_object"],
                "mesh": definition["source_mesh"],
                "mesh_signature_sha256": definition["source_mesh_signature_sha256"],
                "vertex_count": definition["source_vertex_count"],
                "polygon_count": definition["source_polygon_count"],
                "pca_eigenvalues": definition["source_pca_eigenvalues"],
                "positive_weight_groups": definition["source_positive_weight_groups"],
                "geometry_reused_as_final": False,
            },
            "geometry": geometry,
            "raw_intersection_attempts": attempts,
            "raw_exact_intersections": raw_audit,
            "vertex_count": len(nail.data.vertices),
            "polygon_count": len(nail.data.polygons),
            "connected_closed_shell": True,
            "all_vertices_unit_weight_to_exact_distal_bone": True,
            "parent_is_exact_rig": nail.parent == rig,
            "armature_modifier_targets_exact_rig": len([m for m in nail.modifiers if m.type == "ARMATURE" and m.object == rig]) == 1,
        }
        records.append(record)

    bpy.context.view_layer.update()
    eval_body_points, eval_body_triangles, eval_body_tree = evaluated_body_geometry(body)
    for nail, record in zip(nails, records):
        nail_points, nail_triangles = mesh_points_triangles(nail, evaluated=True)
        record["evaluated_exact_intersections"] = exact_cross_record(
            eval_body_points,
            eval_body_triangles,
            eval_body_tree,
            nail_points,
            nail_triangles,
        )
        record["evaluated_clearance"] = clearance_record(nail_points, eval_body_tree)

    nail_pair_record = nail_pair_audit(nails)
    body_signature_after = mesh_signature(body)
    rig_signature_after = rig_signature(rig)
    non_nail_after = non_nail_manifest()
    scene_state_after_authoring = scene_state_record()
    validations = {
        "component_count": len(nails),
        "fingernail_count": sum(record["kind"] == "fingernail" for record in records),
        "toenail_count": sum(record["kind"] == "toenail" for record in records),
        "all_twenty_present": len(nails) == 20,
        "all_twenty_unique_distal_bones": len({record["bone"] for record in records}) == 20,
        "all_raw_body_intersection_free": all(record["raw_exact_intersections"]["exact_genuine_penetration_pair_count"] == 0 for record in records),
        "all_evaluated_body_intersection_free": all(record["evaluated_exact_intersections"]["exact_genuine_penetration_pair_count"] == 0 for record in records),
        "no_nail_to_nail_broad_phase_overlap": nail_pair_record["no_nail_to_nail_broad_phase_overlap"],
        "accepted_body_face_eyes_pelvis_mesh_unchanged": body_signature_before == body_signature_after,
        "accepted_rig_unchanged": rig_signature_before == rig_signature_after,
        "all_non_nail_objects_unchanged": non_nail_before == non_nail_after,
        "scene_state_unchanged_after_authoring": scene_state_before == scene_state_after_authoring,
        "source_native_geometry_not_reused_as_final": all(record["source_landmark"]["geometry_reused_as_final"] is False for record in records),
        "private_inactive": True,
        "runtime_assignment_changed": False,
        "hair_changed": False,
        "brows_changed": False,
        "pelvis_changed": False,
    }
    if not all(
        validations[key]
        for key in (
            "all_twenty_present",
            "all_twenty_unique_distal_bones",
            "all_raw_body_intersection_free",
            "all_evaluated_body_intersection_free",
            "no_nail_to_nail_broad_phase_overlap",
            "accepted_body_face_eyes_pelvis_mesh_unchanged",
            "accepted_rig_unchanged",
            "all_non_nail_objects_unchanged",
            "scene_state_unchanged_after_authoring",
            "source_native_geometry_not_reused_as_final",
        )
    ):
        raise RuntimeError(f"nail delivery validation failed: {validations}")

    # Preserve the fully gated private geometry before the review-render stage.
    # A renderer failure must not silently discard a complete nail correction.
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND), check_existing=False)
    renders = render_review(nails, records)
    if non_nail_manifest() != non_nail_before:
        raise RuntimeError("temporary render setup failed to restore exact non-nail scene state")
    if scene_state_record() != scene_state_before:
        raise RuntimeError("temporary render setup failed to restore exact scene state")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND), check_existing=False)
    source_sha_after = sha256_file(SOURCE)
    if source_sha_after != source_sha_before:
        raise RuntimeError("source Blend changed")
    evidence = {
        "schema": "kira_r21_nail_only_correction_attempt01_v1",
        "status": "PRIVATE_INACTIVE_NAIL_ONLY_REVIEW_CANDIDATE",
        "tooling": {
            "author_script_project_relative": Path(__file__).resolve().relative_to(ROOT).as_posix(),
            "author_script_sha256": sha256_file(Path(__file__).resolve()),
            "preflight_project_relative": "RecoverySprint/continuation_20260802/kira_r21_nail_correction/preflight_01/NAIL_PREFLIGHT.json",
            "preflight_sha256": sha256_file(ROOT / "RecoverySprint/continuation_20260802/kira_r21_nail_correction/preflight_01/NAIL_PREFLIGHT.json"),
            "plan_project_relative": "RecoverySprint/continuation_20260802/kira_r21_nail_correction/preflight_01/NAIL_ONLY_CORRECTION_PLAN.md",
            "plan_sha256": sha256_file(ROOT / "RecoverySprint/continuation_20260802/kira_r21_nail_correction/preflight_01/NAIL_ONLY_CORRECTION_PLAN.md"),
            "placement_diagnosis_project_relative": "RecoverySprint/continuation_20260802/kira_r21_nail_correction/preflight_01/PLACEMENT_DIAGNOSIS.md",
            "placement_diagnosis_sha256": sha256_file(ROOT / "RecoverySprint/continuation_20260802/kira_r21_nail_correction/preflight_01/PLACEMENT_DIAGNOSIS.md"),
        },
        "source": {
            "project_relative_path": SOURCE.relative_to(ROOT).as_posix(),
            "sha256_before": source_sha_before,
            "sha256_after": source_sha_after,
            "unchanged": True,
        },
        "method": {
            "placement": "licensed source-native centers + PCA envelope + exact distal bone mapping",
            "visible_geometry": "new short rounded curved translucent conformal closed shells",
            "rejected_source_native_visible_geometry_reused": False,
            "rows": GRID_ROWS,
            "columns": GRID_COLUMNS,
            "clearance_candidates_base_units": list(BASE_CLEARANCE_CANDIDATES),
        },
        "records": records,
        "nail_pair_audit": nail_pair_record,
        "preservation": {
            "body_object": BODY_NAME,
            "body_mesh_signature_before": body_signature_before,
            "body_mesh_signature_after": body_signature_after,
            "body_face_eyes_skin_pelvis_unchanged": body_signature_before == body_signature_after,
            "rig_object": RIG_NAME,
            "rig_signature_before": rig_signature_before,
            "rig_signature_after": rig_signature_after,
            "rig_unchanged": rig_signature_before == rig_signature_after,
            "non_nail_manifest_before_sha256": hashlib.sha256(json.dumps(non_nail_before, sort_keys=True).encode()).hexdigest(),
            "non_nail_manifest_after_sha256": hashlib.sha256(json.dumps(non_nail_after, sort_keys=True).encode()).hexdigest(),
            "all_non_nail_objects_unchanged": non_nail_before == non_nail_after,
            "scene_state_before": scene_state_before,
            "scene_state_after_authoring": scene_state_after_authoring,
            "scene_state_after_render_cleanup": scene_state_record(),
            "scene_state_unchanged": scene_state_record() == scene_state_before,
        },
        "validation": validations,
        "renders": renders,
        "blend": {
            "project_relative_path": OUTPUT_BLEND.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(OUTPUT_BLEND),
        },
        "limitations": [
            "This candidate corrects only visible nail plates; it does not claim biological nail growth or medical physiology.",
            "Owner visual approval remains required.",
            "Movement/deformation tests are a later bounded stage; this candidate remains inactive and unassigned.",
            "The inherited disclosed R21 pelvic seam-normal and intersection limitations are unchanged by this nail-only branch.",
        ],
    }
    evidence_text = json.dumps(evidence, indent=2) + "\n"
    EVIDENCE_PATH.write_text(evidence_text, encoding="utf-8")
    OWNER_EVIDENCE_PATH.write_text(evidence_text, encoding="utf-8")
    README_PATH.write_text(
        "# Kira R21 nail-only Attempt 01 owner review\n\n"
        "This private, inactive candidate preserves the accepted face, general body, eyes, rig, and the R21 pelvic candidate exactly. Only the twenty rejected nail objects were replaced.\n\n"
        "The new set uses the exact source-native digit centers, PCA envelopes, and distal-bone bindings as landmarks, but does not reuse the rejected long square/polygonal source geometry. Each visible plate is short, rounded, curved, subtly translucent, conformal, and independently verified against the body.\n\n"
        "Review the eight close images for all five nails on each hand and foot. No activation, assignment, hair, brow, pelvis, or runtime change is included. See BUILD_EVIDENCE.json for exact intersection and preservation evidence.\n\n"
        "Remaining scope: owner visual approval and later movement/deformation testing. The inherited disclosed R21 pelvic limitations are unchanged.\n",
        encoding="utf-8",
    )
    manifest_rows = []
    for path in sorted(OWNER_DIR.iterdir(), key=lambda item: item.name):
        if path == MANIFEST_PATH or not path.is_file():
            continue
        manifest_rows.append({"file": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    MANIFEST_PATH.write_text(json.dumps({"schema": "kira_r21_nail_attempt01_file_manifest_v1", "files": manifest_rows}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": evidence["status"], "blend": str(OUTPUT_BLEND), "blend_sha256": evidence["blend"]["sha256"], "all_evaluated_body_intersection_free": validations["all_evaluated_body_intersection_free"], "renders": renders}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        OWNER_DIR.mkdir(parents=True, exist_ok=True)
        blend_preserved = OUTPUT_BLEND.is_file()
        failure = {
            "schema": "kira_r21_nail_only_correction_attempt01_failure_v1",
            "status": "REVIEW_RENDER_OR_PACKAGING_FAILED_GEOMETRY_CANDIDATE_PRESERVED" if blend_preserved else "FAILED_NO_CANDIDATE",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "source_project_relative": SOURCE.relative_to(ROOT).as_posix(),
            "source_sha256": sha256_file(SOURCE) if SOURCE.is_file() else None,
            "blend_saved": blend_preserved,
            "blend_sha256": sha256_file(OUTPUT_BLEND) if blend_preserved else None,
        }
        FAILURE_PATH.write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        failure_name = "ATTEMPT_INCOMPLETE_CANDIDATE_PRESERVED.md" if blend_preserved else "ATTEMPT_FAILED_NO_CANDIDATE.md"
        (OWNER_DIR / failure_name).write_text(
            (
                "# Kira R21 nail Attempt 01 incomplete\n\n"
                "The fully gated private geometry Blend was preserved, but the review render or packaging stage failed. Nothing was activated. See the append-only failure evidence.\n"
                if blend_preserved
                else "# Kira R21 nail Attempt 01 failed\n\nNo review candidate was accepted or activated. See the append-only failure evidence.\n"
            ),
            encoding="utf-8",
        )
        print(json.dumps(failure, indent=2))
        raise
