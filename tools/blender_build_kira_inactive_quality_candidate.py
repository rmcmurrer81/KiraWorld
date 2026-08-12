"""Build and render one private, inactive Kira avatar quality candidate.

This Blender worker is intentionally bounded.  It imports the already-enrolled
adult base, keeps its 79-bone rig, authors new eye and clothing meshes, renders
only clothed review views, and exports only beneath a caller-supplied private
review directory.  It never reads or writes Kira's live runtime model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


HEAD_BONE = "mixamorig:Head_06"
LEFT_ARM = "mixamorig:LeftArm_09"
LEFT_FOREARM = "mixamorig:LeftForeArm_010"
LEFT_HAND = "mixamorig:LeftHand_011"
RIGHT_ARM = "mixamorig:RightArm_033"
RIGHT_FOREARM = "mixamorig:RightForeArm_034"
RIGHT_HAND = "mixamorig:RightHand_035"
LEFT_THIGH = "mixamorig:LeftUpLeg_055"
LEFT_SHIN = "mixamorig:LeftLeg_056"
RIGHT_THIGH = "mixamorig:RightUpLeg_060"
RIGHT_SHIN = "mixamorig:RightLeg_061"
LEFT_FOOT = "mixamorig:LeftFoot_057"
RIGHT_FOOT = "mixamorig:RightFoot_062"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (
        bpy.data.meshes,
        bpy.data.armatures,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def make_material(
    name: str,
    rgba: tuple[float, float, float, float],
    *,
    roughness: float,
    metallic: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = rgba
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return material


def set_single_material(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True


def mesh_world_points(obj: bpy.types.Object, *, evaluated: bool = False) -> list[Vector]:
    if not evaluated:
        return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    instance = obj.evaluated_get(depsgraph)
    mesh = instance.to_mesh()
    try:
        return [instance.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        instance.to_mesh_clear()


def bounds_for_points(points: list[Vector]) -> tuple[Vector, Vector]:
    if not points:
        raise ValueError("no mesh points available")
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def bounds_for_objects(objects: list[bpy.types.Object], *, evaluated: bool = False) -> tuple[Vector, Vector]:
    return bounds_for_points(
        [point for obj in objects for point in mesh_world_points(obj, evaluated=evaluated)]
    )


def vector_list(value: Vector) -> list[float]:
    return [round(float(component), 6) for component in value]


def primary_body_and_armature() -> tuple[bpy.types.Object, bpy.types.Object]:
    meshes = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and len(obj.data.vertices) > 1000
    ]
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if not meshes or len(armatures) != 1:
        raise ValueError("expected one enrolled adult body and one armature")
    body = max(meshes, key=lambda item: len(item.data.vertices))
    return body, armatures[0]


def remove_source_helpers(body: bpy.types.Object) -> list[str]:
    removed: list[str] = []
    for obj in list(bpy.context.scene.objects):
        if obj is body or obj.type != "MESH":
            continue
        if len(obj.data.vertices) <= 128 or obj.name.lower() in {"icosphere", "sphere", "cube"}:
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    return removed


def percentile(values: list[float], ratio: float, fallback: float) -> float:
    if not values:
        return fallback
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * ratio)))
    return float(ordered[index])


def measure_eye_fit(body: bpy.types.Object, low: Vector, high: Vector) -> dict[str, object]:
    points = mesh_world_points(body)
    height = high.z - low.z
    center_x = (low.x + high.x) * 0.5
    eye_z = low.z + height * 0.944
    x_offset = height * 0.0185
    half_width = height * 0.0100
    half_height = height * 0.00380
    half_depth = height * 0.00180
    eyes: dict[str, object] = {}
    for side, sign in (("left", 1.0), ("right", -1.0)):
        target_x = center_x + sign * x_offset
        samples = [
            point
            for point in points
            if abs(point.x - target_x) <= half_width * 1.35
            and abs(point.z - eye_z) <= half_height * 1.8
        ]
        face_surface_y = percentile([point.y for point in samples], 0.08, low.y + height * 0.014)
        # Embed the ellipsoid into the existing face and expose only a shallow
        # front cap.  This avoids a flat eye plane floating beyond the facial
        # silhouette in three-quarter/profile views.
        center_y = face_surface_y + half_depth * 0.92
        eyes[side] = {
            "center": [round(target_x, 6), round(center_y, 6), round(eye_z, 6)],
            "face_surface_y": round(face_surface_y, 6),
            "half_width": round(half_width, 6),
            "half_height": round(half_height, 6),
            "half_depth": round(half_depth, 6),
            "front_surface_y": round(center_y - half_depth, 6),
            "front_surface_behind_face_m": round((center_y - half_depth) - face_surface_y, 6),
            "sample_count": len(samples),
        }
    return {
        "method": (
            "native adult-base eye-band samples plus a flattened 2.65:1 sclera opening; "
            "the separate supplied low-poly eye model was used only as proportion guidance"
        ),
        "front_axis": "negative_y",
        "body_height_native_m": round(height, 6),
        "eyes": eyes,
        "rejected_pass_comparison": {
            "rejected_shape": "round sphere",
            "rejected_native_diameter_m": 0.015642,
            "r3_native_visible_width_m": round(half_width * 2.0, 6),
            "r3_native_visible_height_m": round(half_height * 2.0, 6),
        },
    }


def add_uv_ellipsoid(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    material: bpy.types.Material,
    *,
    segments: int = 48,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=max(12, segments // 2),
        radius=1.0,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_mesh"
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    set_single_material(obj, material)
    return obj


def add_rounded_box(
    name: str,
    location: tuple[float, float, float],
    half_extents: tuple[float, float, float],
    material: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_mesh"
    obj.scale = half_extents
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new(name="closed_shoe_rounded_edges", type="BEVEL")
    bevel.width = min(half_extents) * 0.42
    bevel.segments = 5
    bevel.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    set_single_material(obj, material)
    return obj


def attach_to_bone(
    obj: bpy.types.Object,
    armature: bpy.types.Object,
    bone_name: str,
) -> None:
    # These fitted parts are authored in world space.  Convert their vertices to
    # the armature's local mesh space, then skin them exactly like the body.  A
    # prior bone-parented attempt looked correct in rest pose but displaced the
    # eyes when the rig was posed because the bone-parent inverse did not match
    # the imported 0.161... object transform.
    armature_local = armature.matrix_world.inverted() @ obj.matrix_world
    obj.data.transform(armature_local)
    obj.matrix_world = Matrix.Identity(4)
    group = obj.vertex_groups.new(name=bone_name)
    group.add([vertex.index for vertex in obj.data.vertices], 1.0, "REPLACE")
    modifier = obj.modifiers.new(name="kira_candidate_armature", type="ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    obj.parent = armature
    obj.parent_type = "OBJECT"
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_basis = Matrix.Identity(4)


def eyelid_curve(
    name: str,
    *,
    center: Vector,
    half_width: float,
    half_height: float,
    face_y: float,
    upper: bool,
    material: bpy.types.Material,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(f"{name}_curve", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 3
    curve.bevel_depth = half_height * 0.11
    curve.bevel_resolution = 3
    spline = curve.splines.new("POLY")
    samples = 17
    spline.points.add(samples - 1)
    for index in range(samples):
        t = -1.0 + 2.0 * index / (samples - 1)
        arch = math.sqrt(max(0.0, 1.0 - t * t))
        z_offset = arch * half_height * (0.82 if upper else -0.68)
        spline.points[index].co = (
            center.x + t * half_width,
            face_y - half_height * 0.035,
            center.z + z_offset,
            1.0,
        )
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_mesh"
    obj.select_set(False)
    return obj


def add_eye_system(
    armature: bpy.types.Object,
    eye_fit: dict[str, object],
    materials: dict[str, bpy.types.Material],
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    objects: list[bpy.types.Object] = []
    metrics: dict[str, object] = {}
    for side in ("left", "right"):
        fit = eye_fit["eyes"][side]
        center = Vector(fit["center"])
        half_width = float(fit["half_width"])
        half_height = float(fit["half_height"])
        half_depth = float(fit["half_depth"])
        sclera = add_uv_ellipsoid(
            f"kira_{side}_almond_sclera_r3",
            tuple(center),
            (half_width, half_depth, half_height),
            materials["sclera"],
        )
        iris_center_y = center.y - half_depth * 1.018
        iris_radius = half_height * 0.74
        iris_outer = add_uv_ellipsoid(
            f"kira_{side}_warm_brown_iris_outer_r3",
            (center.x, iris_center_y, center.z),
            (iris_radius, half_depth * 0.035, iris_radius),
            materials["iris_outer"],
            segments=40,
        )
        iris_inner = add_uv_ellipsoid(
            f"kira_{side}_warm_brown_iris_inner_r3",
            (center.x, iris_center_y - half_depth * 0.045, center.z),
            (iris_radius * 0.72, half_depth * 0.025, iris_radius * 0.72),
            materials["iris_inner"],
            segments=36,
        )
        pupil = add_uv_ellipsoid(
            f"kira_{side}_round_pupil_r3",
            (center.x, iris_center_y - half_depth * 0.075, center.z),
            (iris_radius * 0.37, half_depth * 0.018, iris_radius * 0.37),
            materials["pupil"],
            segments=32,
        )
        catchlight = add_uv_ellipsoid(
            f"kira_{side}_soft_catchlight_r3",
            (
                center.x - iris_radius * 0.24,
                iris_center_y - half_depth * 0.095,
                center.z + iris_radius * 0.27,
            ),
            (iris_radius * 0.11, half_depth * 0.012, iris_radius * 0.11),
            materials["catchlight"],
            segments=20,
        )
        # The source face already carries an eyelid contour.  A separate flat
        # outline was visibly floating at oblique angles, so R3 intentionally
        # omits it until socket-aware facial retopology is available.
        side_objects = [sclera, iris_outer, iris_inner, pupil, catchlight]
        for obj in side_objects:
            attach_to_bone(obj, armature, HEAD_BONE)
            obj["candidate_id"] = "kira"
            obj["private_inactive_review_only"] = True
        objects.extend(side_objects)
        metrics[side] = {
            "parts": [obj.name for obj in side_objects],
            "head_bone_binding": HEAD_BONE,
            "visible_width_m": round(half_width * 2.0, 6),
            "visible_height_m": round(half_height * 2.0, 6),
            "iris_diameter_m": round(iris_radius * 2.0, 6),
            "front_surface_behind_face_m": fit["front_surface_behind_face_m"],
        }
    return objects, metrics


def smooth_open_boundaries(mesh: bpy.types.Mesh, *, iterations: int = 8, factor: float = 0.58) -> int:
    """Relax cut garment borders while leaving the fitted interior untouched."""

    edge_use: dict[tuple[int, int], int] = {}
    for polygon in mesh.polygons:
        indices = [int(index) for index in polygon.vertices]
        for index, first in enumerate(indices):
            second = indices[(index + 1) % len(indices)]
            edge = tuple(sorted((first, second)))
            edge_use[edge] = edge_use.get(edge, 0) + 1
    neighbors: dict[int, set[int]] = {}
    for (first, second), count in edge_use.items():
        if count != 1:
            continue
        neighbors.setdefault(first, set()).add(second)
        neighbors.setdefault(second, set()).add(first)
    for _ in range(iterations):
        updates: dict[int, Vector] = {}
        for index, adjacent in neighbors.items():
            if len(adjacent) != 2:
                continue
            average = sum((mesh.vertices[value].co for value in adjacent), Vector()) / 2.0
            updates[index] = mesh.vertices[index].co.lerp(average, factor)
        for index, value in updates.items():
            mesh.vertices[index].co = value
    mesh.update()
    return len(neighbors)


def create_surface_garment(
    name: str,
    *,
    source: bpy.types.Object,
    armature: bpy.types.Object,
    predicate,
    material: bpy.types.Material,
    offset: float,
    thickness: float,
) -> bpy.types.Object:
    source.data.update()
    selected = [
        polygon
        for polygon in source.data.polygons
        if predicate(source.matrix_world @ polygon.center)
    ]
    if not selected:
        raise ValueError(f"no source polygons selected for {name}")
    source_indices = sorted({int(index) for polygon in selected for index in polygon.vertices})
    mapping = {old: new for new, old in enumerate(source_indices)}
    imported_scale = sum(abs(value) for value in source.matrix_world.to_scale()) / 3.0
    if imported_scale <= 1e-8:
        raise ValueError(f"invalid imported scale for {name}")
    local_offset = offset / imported_scale
    local_thickness = thickness / imported_scale
    vertices = [
        tuple(source.data.vertices[index].co + source.data.vertices[index].normal * local_offset)
        for index in source_indices
    ]
    faces = [tuple(mapping[int(index)] for index in polygon.vertices) for polygon in selected]
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    garment = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(garment)
    set_single_material(garment, material)
    smoothed_boundary_vertex_count = smooth_open_boundaries(mesh)

    groups = {
        source_group.name: garment.vertex_groups.new(name=source_group.name)
        for source_group in source.vertex_groups
    }
    for old_index, new_index in mapping.items():
        source_vertex = source.data.vertices[old_index]
        for membership in source_vertex.groups:
            source_group = source.vertex_groups[membership.group]
            groups[source_group.name].add([new_index], float(membership.weight), "REPLACE")

    solidify = garment.modifiers.new(name="opaque_cloth_thickness", type="SOLIDIFY")
    solidify.thickness = local_thickness
    solidify.offset = 1.0
    solidify.use_rim = True
    bpy.context.view_layer.objects.active = garment
    garment.select_set(True)
    bpy.ops.object.modifier_apply(modifier=solidify.name)
    garment.select_set(False)

    modifier = garment.modifiers.new(name="kira_candidate_armature", type="ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    # Garment vertices are copied from the body's local mesh coordinates.  Copy
    # the body's complete object/parent transform so the imported 0.161... rig
    # scale is inherited exactly once.  Using a freshly calculated parent
    # inverse here made the first private review garments roughly 6.2x too big.
    garment.parent = source.parent
    garment.parent_type = source.parent_type
    garment.matrix_parent_inverse = source.matrix_parent_inverse.copy()
    garment.matrix_basis = source.matrix_basis.copy()
    garment["candidate_id"] = "kira"
    garment["separate_clothing_mesh"] = True
    garment["opaque_material"] = True
    garment["private_inactive_review_only"] = True
    garment["smoothed_boundary_vertex_count"] = smoothed_boundary_vertex_count
    garment["requested_world_offset_m"] = float(offset)
    garment["requested_world_thickness_m"] = float(thickness)
    return garment


def weighted_coverage(obj: bpy.types.Object) -> dict[str, object]:
    weighted = sum(1 for vertex in obj.data.vertices if vertex.groups)
    count = len(obj.data.vertices)
    return {
        "vertex_count": count,
        "weighted_vertex_count": weighted,
        "coverage": round(weighted / max(1, count), 6),
    }


def add_closed_shoes(
    body: bpy.types.Object,
    armature: bpy.types.Object,
    low: Vector,
    high: Vector,
    material: bpy.types.Material,
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    """Create one closed, foot-bone-skinned flat shoe per side."""

    height = high.z - low.z
    center_x = (low.x + high.x) * 0.5
    points = mesh_world_points(body)
    shoes: list[bpy.types.Object] = []
    metrics: dict[str, object] = {}
    for side, sign, bone_name in (
        ("left", 1.0, LEFT_FOOT),
        ("right", -1.0, RIGHT_FOOT),
    ):
        samples = [
            point
            for point in points
            if point.z <= low.z + height * 0.068
            and sign * (point.x - center_x) >= 0.0
        ]
        foot_low, foot_high = bounds_for_points(samples)
        half_x = (foot_high.x - foot_low.x) * 0.5 + height * 0.0065
        half_y = (foot_high.y - foot_low.y) * 0.5 + height * 0.0090
        half_z = max((foot_high.z - foot_low.z) * 0.42, height * 0.0175)
        center = Vector(
            (
                (foot_low.x + foot_high.x) * 0.5,
                (foot_low.y + foot_high.y) * 0.5 - height * 0.003,
                low.z + half_z * 0.98,
            )
        )
        shoe = add_rounded_box(
            f"kira_{side}_separate_closed_flat_shoe_r3",
            tuple(center),
            (half_x, half_y, half_z),
            material,
        )
        attach_to_bone(shoe, armature, bone_name)
        shoe["candidate_id"] = "kira"
        shoe["separate_clothing_mesh"] = True
        shoe["opaque_material"] = True
        shoe["closed_surface"] = True
        shoe["private_inactive_review_only"] = True
        shoes.append(shoe)
        metrics[side] = {
            "name": shoe.name,
            "foot_bone_binding": bone_name,
            "sample_count": len(samples),
            "fit_bounds_low": vector_list(foot_low),
            "fit_bounds_high": vector_list(foot_high),
            "closed_surface": True,
        }
    return shoes, metrics


def add_outfit(
    body: bpy.types.Object,
    armature: bpy.types.Object,
    low: Vector,
    high: Vector,
    materials: dict[str, bpy.types.Material],
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    height = high.z - low.z
    center_x = (low.x + high.x) * 0.5

    def relative_z(point: Vector) -> float:
        return (point.z - low.z) / height

    top = create_surface_garment(
        "kira_separate_opaque_teal_top_r3",
        source=body,
        armature=armature,
        predicate=lambda point: (
            0.395 <= relative_z(point)
            <= (
                0.785
                + 0.070
                * min(
                    1.0,
                    (
                        abs(point.x - center_x)
                        / max(height * 0.120, 1e-8)
                    )
                    ** 2,
                )
            )
            and abs(point.x - center_x) <= height * 0.205
        ),
        material=materials["top"],
        offset=height * 0.0068,
        thickness=height * 0.0018,
    )
    leggings = create_surface_garment(
        "kira_separate_opaque_charcoal_leggings_r3",
        source=body,
        armature=armature,
        predicate=lambda point: (
            0.020 <= relative_z(point) <= 0.600
            and abs(point.x - center_x) <= height * 0.180
        ),
        material=materials["leggings"],
        offset=height * 0.0062,
        thickness=height * 0.0019,
    )
    shoes, shoe_metrics = add_closed_shoes(body, armature, low, high, materials["shoes"])
    garments = [top, leggings, *shoes]
    return garments, {
        "separate_mesh_count": len(garments),
        "pieces": [
            {
                "name": obj.name,
                "material": obj.data.materials[0].name,
                "opaque": True,
                "weights": weighted_coverage(obj),
            }
            for obj in garments
        ],
        "top_overlaps_leggings_by_body_height_ratio": 0.205,
        "leggings_overlap_closed_shoes": True,
        "closed_shoes": shoe_metrics,
        "clean_seams_owner_approved": False,
        "dressing_behavior_proven": False,
        "cloth_simulation_proven": False,
    }


def reset_pose(armature: bpy.types.Object) -> None:
    if armature.animation_data:
        armature.animation_data.action = None
    for bone in armature.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def rotate_pose_bone_toward(
    armature: bpy.types.Object,
    bone_name: str,
    target_world: Vector,
) -> None:
    bone = armature.pose.bones.get(bone_name)
    if bone is None:
        raise ValueError(f"missing pose bone: {bone_name}")
    target = armature.matrix_world.inverted() @ target_world
    current = (bone.tail - bone.head).normalized()
    desired = (target - bone.head).normalized()
    delta = current.rotation_difference(desired)
    pivot = bone.head.copy()
    bone.matrix = (
        Matrix.Translation(pivot)
        @ delta.to_matrix().to_4x4()
        @ Matrix.Translation(-pivot)
        @ bone.matrix
    )
    bpy.context.view_layer.update()


def arm_targets(
    armature: bpy.types.Object,
    *,
    side: str,
    low: Vector,
    height: float,
    pose: str,
) -> None:
    if side == "left":
        names = (LEFT_ARM, LEFT_FOREARM, LEFT_HAND)
    else:
        names = (RIGHT_ARM, RIGHT_FOREARM, RIGHT_HAND)
    upper = armature.pose.bones[names[0]]
    sign = 1.0 if upper.head.x >= 0.0 else -1.0
    shoulder_world = armature.matrix_world @ upper.head
    if pose == "reach" and side == "right":
        elbow = shoulder_world + Vector((sign * height * 0.075, -height * 0.125, -height * 0.035))
        hand = shoulder_world + Vector((sign * height * 0.045, -height * 0.315, -height * 0.045))
    elif pose == "walk":
        phase = 1.0 if side == "left" else -1.0
        elbow = shoulder_world + Vector((sign * height * 0.095, phase * height * 0.050, -height * 0.155))
        hand = Vector((sign * height * 0.165, phase * height * 0.095, low.z + height * 0.445))
    else:
        elbow = shoulder_world + Vector((sign * height * 0.095, height * 0.015, -height * 0.165))
        hand = Vector((sign * height * 0.155, -height * 0.010, low.z + height * 0.430))
    rotate_pose_bone_toward(armature, names[0], elbow)
    rotate_pose_bone_toward(armature, names[1], hand)
    hand_bone = armature.pose.bones[names[2]]
    hand_tip = hand + Vector((0.0, -height * 0.010, -height * 0.055))
    rotate_pose_bone_toward(armature, names[2], hand_tip)


def apply_pose(armature: bpy.types.Object, pose: str, low: Vector, high: Vector) -> None:
    reset_pose(armature)
    height = high.z - low.z
    arm_targets(armature, side="left", low=low, height=height, pose=pose)
    arm_targets(armature, side="right", low=low, height=height, pose=pose)
    if pose == "walk":
        left_thigh = armature.pose.bones[LEFT_THIGH]
        hip_world = armature.matrix_world @ left_thigh.head
        knee_target = hip_world + Vector((0.0, -height * 0.105, -height * 0.195))
        rotate_pose_bone_toward(armature, LEFT_THIGH, knee_target)
        left_shin = armature.pose.bones[LEFT_SHIN]
        knee_world = armature.matrix_world @ left_shin.head
        ankle_target = knee_world + Vector((0.0, height * 0.075, -height * 0.175))
        rotate_pose_bone_toward(armature, LEFT_SHIN, ankle_target)
    bpy.context.view_layer.update()


def create_action(
    armature: bpy.types.Object,
    *,
    name: str,
    pose: str,
    low: Vector,
    high: Vector,
) -> bpy.types.Action:
    apply_pose(armature, pose, low, high)
    action = bpy.data.actions.new(name)
    armature.animation_data_create()
    armature.animation_data.action = action
    for frame in (1, 24):
        for bone in armature.pose.bones:
            bone.rotation_mode = "QUATERNION"
            bone.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=bone.name)
            bone.keyframe_insert(data_path="location", frame=frame, group=bone.name)
            bone.keyframe_insert(data_path="scale", frame=frame, group=bone.name)
    action["private_inactive_review_only"] = True
    action["pose_label"] = pose
    return action


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_lighting(center: Vector, height: float) -> None:
    specs = [
        (Vector((-0.75, -1.2, 1.1)), 760.0, 2.8),
        (Vector((0.9, -0.45, 0.7)), 430.0, 2.4),
        (Vector((0.2, 0.95, 1.25)), 560.0, 2.5),
    ]
    for index, (direction, energy, size) in enumerate(specs, start=1):
        bpy.ops.object.light_add(type="AREA", location=center + direction * height)
        light = bpy.context.object
        light.name = f"kira_private_review_light_{index}"
        light.data.energy = energy
        light.data.size = size
        look_at(light, center)


def add_ground(low: Vector, high: Vector, material: bpy.types.Material) -> bpy.types.Object:
    height = high.z - low.z
    bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, low.z - height * 0.009))
    ground = bpy.context.object
    ground.name = "private_review_ground_not_exported"
    ground.scale = (height * 0.75, height * 0.75, height * 0.009)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    set_single_material(ground, material)
    ground["private_diagnostic_helper"] = True
    return ground


def render_view(
    output: Path,
    *,
    camera: bpy.types.Object,
    center: Vector,
    direction: Vector,
    ortho_scale: float,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    distance = max(1.0, ortho_scale * 3.0)
    camera.location = center + direction.normalized() * distance
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho_scale
    look_at(camera, center)
    bpy.context.scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def finite_pose_metrics(objects: list[bpy.types.Object]) -> dict[str, object]:
    points = [point for obj in objects for point in mesh_world_points(obj, evaluated=True)]
    finite = all(math.isfinite(component) for point in points for component in point)
    low, high = bounds_for_points(points)
    return {
        "evaluated_vertex_count": len(points),
        "finite_coordinates": finite,
        "bounds_low": vector_list(low),
        "bounds_high": vector_list(high),
        "extent": vector_list(high - low),
    }


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    project_root = Path(config["project_root"]).resolve(strict=True)
    source = Path(config["source_model"]).resolve(strict=True)
    output_dir = Path(config["output_dir"]).resolve()
    allowed_root = (
        project_root / "Avatar" / "avatar_builder" / "candidate_sources" / "kira_inactive_quality_r3"
    ).resolve()
    output_dir.relative_to(allowed_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    if sha256_file(source) != config["source_sha256"]:
        raise ValueError("adult base SHA-256 mismatch")

    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(source))
    body, armature = primary_body_and_armature()
    removed = remove_source_helpers(body)
    body.name = "kira_adult_base_body_private_r3"
    body.data.name = "kira_adult_base_body_private_r3_mesh"
    armature.name = "kira_79_bone_private_r3_rig"
    armature.data.name = "kira_79_bone_private_r3_skeleton"
    body["candidate_id"] = "kira"
    body["maturity_policy"] = "adult"
    body["private_inactive_review_only"] = True
    body["runtime_activation_allowed"] = False

    materials = {
        "skin": make_material("kira_private_warm_neutral_skin_r3", (0.72, 0.51, 0.40, 1.0), roughness=0.66),
        "sclera": make_material("kira_warm_realistic_sclera_r3", (0.91, 0.89, 0.83, 1.0), roughness=0.30),
        "iris_outer": make_material("kira_deep_brown_iris_outer_r3", (0.055, 0.018, 0.006, 1.0), roughness=0.34),
        "iris_inner": make_material("kira_warm_brown_iris_inner_r3", (0.16, 0.045, 0.010, 1.0), roughness=0.28),
        "pupil": make_material("kira_black_pupil_r3", (0.002, 0.001, 0.001, 1.0), roughness=0.18),
        "catchlight": make_material("kira_soft_eye_catchlight_r3", (1.0, 0.97, 0.90, 1.0), roughness=0.12),
        "top": make_material("kira_opaque_teal_cloth_r3", (0.025, 0.24, 0.29, 1.0), roughness=0.78),
        "leggings": make_material("kira_opaque_charcoal_cloth_r3", (0.035, 0.045, 0.060, 1.0), roughness=0.82),
        "shoes": make_material("kira_opaque_flat_shoe_r3", (0.18, 0.075, 0.035, 1.0), roughness=0.72),
        "ground": make_material("private_review_ground_material", (0.16, 0.18, 0.21, 1.0), roughness=0.9),
    }
    set_single_material(body, materials["skin"])
    low, high = bounds_for_objects([body])
    eye_fit = measure_eye_fit(body, low, high)
    eye_objects, eye_metrics = add_eye_system(armature, eye_fit, materials)
    garments, clothing_metrics = add_outfit(body, armature, low, high, materials)
    review_objects = [body, *eye_objects, *garments]

    armature["candidate_id"] = "kira"
    armature["private_inactive_review_only"] = True
    armature["runtime_activation_allowed"] = False
    actions = [
        create_action(armature, name="kira_quality_relaxed_r3", pose="relaxed", low=low, high=high),
        create_action(armature, name="kira_quality_walk_r3", pose="walk", low=low, high=high),
        create_action(armature, name="kira_quality_reach_r3", pose="reach", low=low, high=high),
    ]

    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.018, 0.022, 0.030)
    height = high.z - low.z
    full_center = Vector(((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, low.z + height * 0.52))
    head_center = Vector((0.0, low.y, low.z + height * 0.895))
    add_ground(low, high, materials["ground"])
    add_lighting(full_center, height)
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "kira_private_review_camera"
    scene.camera = camera

    renders: dict[str, str] = {}
    pose_metrics: dict[str, object] = {}
    for pose in ("relaxed", "walk", "reach"):
        apply_pose(armature, pose, low, high)
        pose_metrics[pose] = finite_pose_metrics(review_objects)
        if pose == "relaxed":
            views = {
                "front": Vector((0.0, -1.0, 0.05)),
                "front_three_quarter": Vector((0.72, -1.0, 0.08)),
                "left_profile": Vector((1.0, 0.0, 0.04)),
                "back": Vector((0.0, 1.0, 0.04)),
            }
        else:
            views = {
                "front_three_quarter": Vector((0.68, -1.0, 0.08)),
                "left_profile": Vector((1.0, 0.0, 0.04)),
            }
        for view_name, direction in views.items():
            key = f"{pose}_{view_name}"
            path = output_dir / f"{key}.png"
            render_view(
                path,
                camera=camera,
                center=full_center,
                direction=direction,
                ortho_scale=height * 1.18,
            )
            renders[key] = str(path)
        if pose in {"walk", "reach"}:
            key = f"{pose}_head_three_quarter"
            path = output_dir / f"{key}.png"
            render_view(
                path,
                camera=camera,
                center=head_center,
                direction=Vector((0.68, -1.0, 0.04)),
                ortho_scale=height * 0.30,
            )
            renders[key] = str(path)
    apply_pose(armature, "relaxed", low, high)
    close_path = output_dir / "relaxed_head_closeup.png"
    render_view(
        close_path,
        camera=camera,
        center=head_center,
        direction=Vector((0.0, -1.0, 0.02)),
        ortho_scale=height * 0.30,
    )
    renders["relaxed_head_closeup"] = str(close_path)
    relaxed_head_profile_path = output_dir / "relaxed_head_left_profile.png"
    render_view(
        relaxed_head_profile_path,
        camera=camera,
        center=head_center,
        direction=Vector((1.0, 0.0, 0.02)),
        ortho_scale=height * 0.30,
    )
    renders["relaxed_head_left_profile"] = str(relaxed_head_profile_path)

    for obj in list(bpy.context.scene.objects):
        obj.select_set(False)
    export_objects = [armature, *review_objects]
    for obj in export_objects:
        obj.hide_render = False
        obj.hide_viewport = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature
    model_path = output_dir / "kira_inactive_clothed_quality_r3_review.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(model_path),
        export_format="GLB",
        use_selection=True,
        export_apply=False,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_force_sampling=True,
        export_def_bones=True,
        export_yup=True,
        export_morph=True,
        export_extras=True,
    )

    relaxed_metrics = pose_metrics["relaxed"]
    manifest = {
        "schema_version": 1,
        "created_at": now_iso(),
        "candidate_id": "kira",
        "candidate_revision": "inactive_quality_r3",
        "status": "private_inactive_visual_review_candidate_owner_approval_required",
        "source": {
            "project_path": config["source_project_path"],
            "sha256": config["source_sha256"],
            "body_vertices": len(body.data.vertices),
            "removed_source_helpers": removed,
        },
        "model": {
            "path": str(model_path),
            "sha256": sha256_file(model_path),
            "private_clothed_review_assembly": True,
        },
        "body": {
            "maturity_policy": "adult",
            "base_surface_preserved": True,
            "likeness_claimed": False,
            "known_limit": "Kira has no owner-approved exact identity multiview set; this remains a generic adult base.",
        },
        "eyes": {
            "color": "warm realistic brown",
            "fit": eye_fit,
            "parts": eye_metrics,
            "head_bone_binding": HEAD_BONE,
            "blink_proven": False,
            "gaze_control_proven": False,
        },
        "clothing": clothing_metrics,
        "rig": {
            "armature": armature.name,
            "bone_count": len(armature.data.bones),
            "required_bones_present": all(
                name in armature.data.bones
                for name in (
                    HEAD_BONE,
                    LEFT_ARM,
                    LEFT_FOREARM,
                    LEFT_HAND,
                    RIGHT_ARM,
                    RIGHT_FOREARM,
                    RIGHT_HAND,
                    LEFT_THIGH,
                    LEFT_SHIN,
                    RIGHT_THIGH,
                    RIGHT_SHIN,
                    LEFT_FOOT,
                    RIGHT_FOOT,
                )
            ),
            "body_weight_coverage": weighted_coverage(body),
            "actions": [action.name for action in actions],
            "pose_metrics": pose_metrics,
            "stable_working_rig_claimed": False,
        },
        "ground_review": {
            "render_ground_top_z_m": round(float(low.z), 6),
            "relaxed_evaluated_min_z_m": relaxed_metrics["bounds_low"][2],
            "render_alignment_gap_m": round(float(relaxed_metrics["bounds_low"][2] - low.z), 6),
            "locomotion_contact_proven": False,
        },
        "renders": {
            key: {"path": value, "sha256": sha256_file(Path(value))}
            for key, value in renders.items()
        },
        "truth": {
            "private_inactive_review_only": True,
            "live_runtime_model_modified": False,
            "unclothed_render_retained": False,
            "adult_complete_topology_proven": False,
            "identity_likeness_owner_approved": False,
            "eye_socket_fit_owner_approved": False,
            "garment_coverage_owner_approved": False,
            "garment_penetration_proven_absent": False,
            "stable_visual_deformation_proven": False,
            "dressing_behavior_proven": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
            "positive_proof_gate_released": False,
        },
    }
    manifest_path = output_dir / "kira_inactive_quality_r3_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "manifest": str(manifest_path), "model": str(model_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
