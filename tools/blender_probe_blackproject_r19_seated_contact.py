#!/usr/bin/env python3
"""Author and audit one append-only BlackProject-native seated-contact probe.

This worker opens the exact rejected R9b private-review Blend as a read-only
engineering baseline.  It preserves the native 188-joint armature, removes
scalp-hair objects only from the new probe copy, authors a bounded seated pose,
places a backless seat and common floor from evaluated surface measurements,
and records exact posed-mesh self-intersections plus explicit contact
residuals.  It never writes the source Blend or any runtime/avatar assignment.

Use ``--preflight-only`` to exercise inventory and deterministic pose search
without creating evidence or saving a Blend.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import bmesh
import bpy
from mathutils import Vector


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_exact_mesh_intersections as exact_intersections  # noqa: E402


SOURCE_REL = (
    "Avatar/private_owner_review/kira_temporary_functional_body_20260730/"
    "kira_tfb_blackproject_r9b_20260730_072700/"
    "kira_hart_temporary_functional_body_private_review.blend"
)
SOURCE_SHA256 = (
    "4ff92501e954e62f81b6a9cc4d11b9c939f4fdee18d1940d2c59855db7630f5c"
)
OUTPUT_REL = (
    "RecoverySprint/continuation_20260802/"
    "r19_blackproject_seated_contact/attempt_01"
)
ACTION_NAME = "KIRA_R19_BLACKPROJECT_SEATED_CONTACT_ATTEMPT_01"
POSE_FRAME = 30
CONTACT_TOLERANCE_M = 0.006
NO_PENETRATION_EPSILON_M = 0.00025
TARGET_SEAT_HEIGHT_M = 0.445


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / OUTPUT_REL),
    )
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def quantile(values: Iterable[float], fraction: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    position = max(0.0, min(1.0, fraction)) * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    alpha = position - low
    return ordered[low] * (1.0 - alpha) + ordered[high] * alpha


def rounded_vector(value: Vector) -> list[float]:
    return [round(float(component), 9) for component in value]


def bounds(points: list[Vector]) -> dict[str, Any]:
    low = Vector(
        tuple(min(float(point[axis]) for point in points) for axis in range(3))
    )
    high = Vector(
        tuple(max(float(point[axis]) for point in points) for axis in range(3))
    )
    return {
        "low": rounded_vector(low),
        "high": rounded_vector(high),
        "size": rounded_vector(high - low),
    }


def find_body_and_armature() -> tuple[bpy.types.Object, bpy.types.Object]:
    bodies = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH" and bool(obj.get("rapid_body_primary_surface"))
    ]
    if len(bodies) != 1:
        raise RuntimeError(
            f"expected one marked primary surface in R9b, found {len(bodies)}"
        )
    body = bodies[0]
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(
            f"expected one native armature in R9b, found {len(armatures)}"
        )
    armature = armatures[0]
    if len(armature.data.bones) != 188:
        raise RuntimeError(
            f"expected exact native 188-joint rig, found {len(armature.data.bones)}"
        )
    return body, armature


def scalp_hair_objects() -> list[bpy.types.Object]:
    results: list[bpy.types.Object] = []
    for obj in bpy.data.objects:
        identity = f"{obj.name} {getattr(obj.data, 'name', '')}".lower()
        if "hair" not in identity:
            continue
        if "brow" in identity or "lash" in identity:
            continue
        if obj.type in {"MESH", "CURVES", "CURVE", "PARTICLE"}:
            results.append(obj)
    return results


def remove_prior_contact_props() -> list[str]:
    removed: list[str] = []
    for obj in list(bpy.data.objects):
        identity = obj.name.lower()
        if bool(obj.get("review_context_prop_only")) or any(
            token in identity
            for token in ("seated_contact_seat", "seated_contact_left_support", "seated_contact_right_support")
        ):
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    return sorted(removed)


def reset_pose(armature: bpy.types.Object) -> None:
    armature.animation_data_create()
    armature.animation_data.action = None
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        pose_bone.location = (0.0, 0.0, 0.0)
        pose_bone.scale = (1.0, 1.0, 1.0)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def seated_rotations(
    hip_degrees: float,
    knee_degrees: float,
    ankle_degrees: float,
) -> dict[str, tuple[float, float, float]]:
    return {
        "lThighBend_05": (
            math.radians(hip_degrees),
            0.0,
            math.radians(7.0),
        ),
        "rThighBend_021": (
            math.radians(hip_degrees),
            0.0,
            math.radians(-7.0),
        ),
        "lShin_07": (math.radians(knee_degrees), 0.0, 0.0),
        "rShin_023": (math.radians(knee_degrees), 0.0, 0.0),
        "lFoot_08": (math.radians(ankle_degrees), 0.0, 0.0),
        "rFoot_024": (math.radians(ankle_degrees), 0.0, 0.0),
        "pelvis_04": (math.radians(3.0), 0.0, 0.0),
        "abdomenLower_037": (math.radians(-5.0), 0.0, 0.0),
        "abdomenUpper_038": (math.radians(2.0), 0.0, 0.0),
        "chestLower_039": (math.radians(2.0), 0.0, 0.0),
    }


def apply_rotations(
    armature: bpy.types.Object,
    rotations: dict[str, tuple[float, float, float]],
) -> None:
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
    for bone_name, rotation in rotations.items():
        pose_bone = armature.pose.bones.get(bone_name)
        if pose_bone is None:
            raise RuntimeError(f"required native pose bone missing: {bone_name}")
        pose_bone.rotation_euler = rotation
    bpy.context.view_layer.update()


def evaluated_vertices(obj: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def region_indices(
    obj: bpy.types.Object,
    prefixes: tuple[str, ...],
    *,
    minimum_weight: float = 0.12,
) -> list[int]:
    group_indices = {
        group.index
        for group in obj.vertex_groups
        if group.name.startswith(prefixes)
    }
    return [
        int(vertex.index)
        for vertex in obj.data.vertices
        if any(
            assignment.group in group_indices
            and float(assignment.weight) >= minimum_weight
            for assignment in vertex.groups
        )
    ]


def min_zone_height(
    points: list[Vector],
    *,
    axis: int,
    low_fraction: float,
    high_fraction: float,
) -> float:
    values = [float(point[axis]) for point in points]
    low = quantile(values, low_fraction)
    high = quantile(values, high_fraction)
    selected = [
        float(point.z)
        for point in points
        if low - 1e-9 <= float(point[axis]) <= high + 1e-9
    ]
    return quantile(selected, 0.035)


def geometric_pose_metrics(
    body: bpy.types.Object,
    points: list[Vector],
    regions: dict[str, list[int]],
) -> dict[str, Any]:
    left_foot = [points[index] for index in regions["left_foot"]]
    right_foot = [points[index] for index in regions["right_foot"]]
    pelvis = [points[index] for index in regions["pelvis"]]
    if not left_foot or not right_foot or not pelvis:
        raise RuntimeError("required weighted contact region is empty")

    pelvis_y = [float(point.y) for point in pelvis]
    posterior_threshold = quantile(pelvis_y, 0.54)
    posterior_pelvis = [
        point for point in pelvis if float(point.y) >= posterior_threshold
    ]
    seat_contact_z = min(float(point.z) for point in posterior_pelvis)

    left_floor_z = min(float(point.z) for point in left_foot)
    right_floor_z = min(float(point.z) for point in right_foot)
    common_floor_z = min(left_floor_z, right_floor_z)

    # Body faces toward negative Y in this source.  Comparing robust bottom
    # heights at the negative-Y toe and positive-Y heel ends is a deterministic
    # sole-pitch signal without assuming a perfectly planar anatomical sole.
    left_toe_z = min_zone_height(
        left_foot, axis=1, low_fraction=0.0, high_fraction=0.28
    )
    left_heel_z = min_zone_height(
        left_foot, axis=1, low_fraction=0.72, high_fraction=1.0
    )
    right_toe_z = min_zone_height(
        right_foot, axis=1, low_fraction=0.0, high_fraction=0.28
    )
    right_heel_z = min_zone_height(
        right_foot, axis=1, low_fraction=0.72, high_fraction=1.0
    )
    seat_height = seat_contact_z - common_floor_z
    return {
        "seat_contact_reference_z_m": seat_contact_z,
        "common_floor_reference_z_m": common_floor_z,
        "seat_height_above_common_floor_m": seat_height,
        "left_foot_low_z_m": left_floor_z,
        "right_foot_low_z_m": right_floor_z,
        "bilateral_foot_low_height_difference_m": abs(
            left_floor_z - right_floor_z
        ),
        "left_toe_heel_bottom_height_difference_m": abs(
            left_toe_z - left_heel_z
        ),
        "right_toe_heel_bottom_height_difference_m": abs(
            right_toe_z - right_heel_z
        ),
        "left_toe_bottom_z_m": left_toe_z,
        "left_heel_bottom_z_m": left_heel_z,
        "right_toe_bottom_z_m": right_toe_z,
        "right_heel_bottom_z_m": right_heel_z,
        "posterior_pelvis_y_threshold_m": posterior_threshold,
        "posterior_pelvis_point_count": len(posterior_pelvis),
        "body_bounds_m": bounds(points),
    }


def pose_search(
    body: bpy.types.Object,
    armature: bpy.types.Object,
    regions: dict[str, list[int]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    for hip_degrees in (-72.0, -78.0, -84.0):
        for knee_degrees in (82.0, 88.0, 94.0):
            for ankle_degrees in (-18.0, -12.0, -6.0, 0.0, 6.0, 12.0, 18.0):
                rotations = seated_rotations(
                    hip_degrees, knee_degrees, ankle_degrees
                )
                apply_rotations(armature, rotations)
                points = evaluated_vertices(body)
                metrics = geometric_pose_metrics(body, points, regions)
                score = (
                    abs(
                        metrics["seat_height_above_common_floor_m"]
                        - TARGET_SEAT_HEIGHT_M
                    )
                    * 14.0
                    + metrics["bilateral_foot_low_height_difference_m"] * 30.0
                    + metrics["left_toe_heel_bottom_height_difference_m"] * 16.0
                    + metrics["right_toe_heel_bottom_height_difference_m"] * 16.0
                    + abs(hip_degrees + 78.0) * 0.001
                    + abs(knee_degrees - 88.0) * 0.001
                )
                records.append(
                    {
                        "hip_degrees": hip_degrees,
                        "knee_degrees": knee_degrees,
                        "ankle_degrees": ankle_degrees,
                        "objective_score": round(float(score), 9),
                        "metrics": metrics,
                    }
                )
    records.sort(
        key=lambda record: (
            record["objective_score"],
            abs(record["hip_degrees"] + 78.0),
            abs(record["knee_degrees"] - 88.0),
            abs(record["ankle_degrees"]),
        )
    )
    selected = records[0]
    apply_rotations(
        armature,
        seated_rotations(
            selected["hip_degrees"],
            selected["knee_degrees"],
            selected["ankle_degrees"],
        ),
    )
    return selected, records[:10]


def exact_intersection_report(obj: bpy.types.Object) -> dict[str, Any]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bmesh.ops.transform(
            bm,
            matrix=evaluated.matrix_world,
            verts=list(bm.verts),
        )
        return exact_intersections.exact_nonadjacent_intersection_report(
            bm,
            include_pair_details=True,
        )
    finally:
        bm.free()
        evaluated.to_mesh_clear()


def contact_solution(
    body: bpy.types.Object,
    points: list[Vector],
    regions: dict[str, list[int]],
) -> dict[str, Any]:
    pelvis = [points[index] for index in regions["pelvis"]]
    left_foot = [points[index] for index in regions["left_foot"]]
    right_foot = [points[index] for index in regions["right_foot"]]

    pelvis_x = [float(point.x) for point in pelvis]
    pelvis_y = [float(point.y) for point in pelvis]
    posterior_threshold = quantile(pelvis_y, 0.54)
    posterior = [point for point in pelvis if float(point.y) >= posterior_threshold]
    seat_x_min = quantile(pelvis_x, 0.015) - 0.045
    seat_x_max = quantile(pelvis_x, 0.985) + 0.045
    seat_y_min = posterior_threshold - 0.018
    seat_y_max = max(pelvis_y) + 0.105
    seat_support_points = [
        point
        for point in posterior
        if seat_x_min <= float(point.x) <= seat_x_max
        and seat_y_min <= float(point.y) <= seat_y_max
    ]
    initial_seat_reference = min(float(point.z) for point in seat_support_points)
    # Include every evaluated body point that occupies the posterior support
    # footprint near the intended seat plane.  Setting the plane just below
    # the lowest such point prevents a hidden non-pelvis vertex from piercing
    # the prop while retaining a sub-millimetre support residual.
    seat_plane_candidates = [
        point
        for point in points
        if seat_x_min <= float(point.x) <= seat_x_max
        and seat_y_min <= float(point.y) <= seat_y_max
        and initial_seat_reference - 0.10
        <= float(point.z)
        <= initial_seat_reference + 0.16
    ]
    seat_top = (
        min(float(point.z) for point in seat_plane_candidates)
        - NO_PENETRATION_EPSILON_M
    )

    left_low = min(float(point.z) for point in left_foot)
    right_low = min(float(point.z) for point in right_foot)
    floor_top = min(left_low, right_low) - NO_PENETRATION_EPSILON_M

    def plane_metrics(
        selected: list[Vector], plane_z: float, tolerance: float
    ) -> dict[str, Any]:
        gaps = [float(point.z) - plane_z for point in selected]
        penetration_depths = [max(0.0, -gap) for gap in gaps]
        return {
            "point_count": len(selected),
            "minimum_signed_gap_m": round(min(gaps), 9),
            "maximum_penetration_depth_m": round(
                max(penetration_depths, default=0.0), 9
            ),
            "contact_point_count_within_tolerance": sum(
                -1e-9 <= gap <= tolerance for gap in gaps
            ),
            "minimum_absolute_contact_residual_m": round(
                min((abs(gap) for gap in gaps), default=999.0), 9
            ),
            "within_contact_tolerance": bool(
                min((abs(gap) for gap in gaps), default=999.0) <= tolerance
            ),
            "no_penetration": bool(
                max(penetration_depths, default=0.0) <= 1e-9
            ),
        }

    # Evaluate only points physically inside the support footprint.  The seat
    # is deliberately posterior and backless, so hanging lower legs cannot be
    # mistaken for seat penetration.
    seat_near_points = [
        point
        for point in points
        if seat_x_min <= float(point.x) <= seat_x_max
        and seat_y_min <= float(point.y) <= seat_y_max
        and seat_top - 0.04 <= float(point.z) <= seat_top + 0.16
    ]
    left_metrics = plane_metrics(left_foot, floor_top, CONTACT_TOLERANCE_M)
    right_metrics = plane_metrics(right_foot, floor_top, CONTACT_TOLERANCE_M)
    seat_metrics = plane_metrics(
        seat_near_points,
        seat_top,
        CONTACT_TOLERANCE_M,
    )
    return {
        "contact_tolerance_m": CONTACT_TOLERANCE_M,
        "no_penetration_epsilon_m": NO_PENETRATION_EPSILON_M,
        "seat": {
            "top_z_m": seat_top,
            "x_min_m": seat_x_min,
            "x_max_m": seat_x_max,
            "y_min_m": seat_y_min,
            "y_max_m": seat_y_max,
            "initial_posterior_pelvis_reference_z_m": initial_seat_reference,
            "plane_candidate_point_count": len(seat_plane_candidates),
            **seat_metrics,
        },
        "floor": {
            "top_z_m": floor_top,
            "left_foot": left_metrics,
            "right_foot": right_metrics,
        },
        "seat_height_above_floor_m": round(seat_top - floor_top, 9),
        "all_three_supports_within_tolerance": bool(
            seat_metrics["within_contact_tolerance"]
            and left_metrics["within_contact_tolerance"]
            and right_metrics["within_contact_tolerance"]
        ),
        "all_three_supports_no_penetration": bool(
            seat_metrics["no_penetration"]
            and left_metrics["no_penetration"]
            and right_metrics["no_penetration"]
        ),
    }


def make_material(
    name: str,
    color: tuple[float, float, float, float],
) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Roughness"].default_value = 0.72
    return material


def make_cube(
    name: str,
    center: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    material: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    obj["review_context_prop_only"] = True
    obj["candidate_component"] = False
    obj["must_not_export"] = True
    obj["private_probe_only"] = True
    return obj


def make_support_props(
    contact: dict[str, Any],
    body_points: list[Vector],
) -> list[bpy.types.Object]:
    seat = contact["seat"]
    floor = contact["floor"]
    support_material = make_material(
        "R19_CONTACT_SUPPORT_DARK_NAVY",
        (0.035, 0.13, 0.20, 1.0),
    )
    floor_material = make_material(
        "R19_CONTACT_FLOOR_NEUTRAL",
        (0.08, 0.10, 0.12, 1.0),
    )
    seat_thickness = 0.045
    seat_obj = make_cube(
        "R19_Seat_Surface",
        (
            (seat["x_min_m"] + seat["x_max_m"]) * 0.5,
            (seat["y_min_m"] + seat["y_max_m"]) * 0.5,
            seat["top_z_m"] - seat_thickness * 0.5,
        ),
        (
            seat["x_max_m"] - seat["x_min_m"],
            seat["y_max_m"] - seat["y_min_m"],
            seat_thickness,
        ),
        support_material,
    )
    body_box = bounds(body_points)
    low = Vector(body_box["low"])
    high = Vector(body_box["high"])
    floor_margin = 0.25
    floor_thickness = 0.025
    floor_obj = make_cube(
        "R19_Common_Foot_Floor",
        (
            (low.x + high.x) * 0.5,
            (low.y + high.y) * 0.5,
            floor["top_z_m"] - floor_thickness * 0.5,
        ),
        (
            (high.x - low.x) + floor_margin * 2.0,
            (high.y - low.y) + floor_margin * 2.0,
            floor_thickness,
        ),
        floor_material,
    )
    seat_obj["surface_top_z_m"] = float(seat["top_z_m"])
    floor_obj["surface_top_z_m"] = float(floor["top_z_m"])
    return [seat_obj, floor_obj]


def author_action(
    armature: bpy.types.Object,
    rotations: dict[str, tuple[float, float, float]],
) -> bpy.types.Action:
    existing = bpy.data.actions.get(ACTION_NAME)
    if existing is not None:
        bpy.data.actions.remove(existing)
    reset_pose(armature)
    action = bpy.data.actions.new(ACTION_NAME)
    action.use_fake_user = True
    armature.animation_data_create()
    armature.animation_data.action = action
    for frame in (1, POSE_FRAME):
        for pose_bone in armature.pose.bones:
            pose_bone.rotation_mode = "XYZ"
            pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        for bone_name, rotation in rotations.items():
            pose_bone = armature.pose.bones[bone_name]
            pose_bone.rotation_euler = (
                rotation if frame == POSE_FRAME else (0.0, 0.0, 0.0)
            )
            pose_bone.keyframe_insert(
                data_path="rotation_euler",
                frame=frame,
                group=bone_name,
            )
    action["private_probe_only"] = True
    action["source_baseline"] = "R9b rejected engineering material"
    action["native_joint_count"] = 188
    action["runtime_assignment_allowed"] = False
    armature.animation_data.action = action
    bpy.context.scene.frame_set(POSE_FRAME)
    bpy.context.view_layer.update()
    return action


def configure_render() -> tuple[bpy.types.Scene, bpy.types.Object]:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.show_specular_highlight = True
    scene.world.color = (0.006, 0.012, 0.018)
    camera_data = bpy.data.cameras.new("R19_Seated_Probe_Camera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R19_Seated_Probe_Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return scene, camera


def render_view(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    path: Path,
    location: Vector,
    target: Vector,
    scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = scale
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_evidence(
    output_dir: Path,
    body: bpy.types.Object,
) -> dict[str, str]:
    points = evaluated_vertices(body)
    box = bounds(points)
    low = Vector(box["low"])
    high = Vector(box["high"])
    center = (low + high) * 0.5
    height = high.z - low.z
    width = high.x - low.x
    scene, camera = configure_render()
    views = {
        "seated_left_profile": (
            Vector((center.x + 3.1, center.y, center.z)),
            center,
            height * 1.16,
        ),
        "seated_right_profile": (
            Vector((center.x - 3.1, center.y, center.z)),
            center,
            height * 1.16,
        ),
        "seated_front_three_quarter": (
            Vector((center.x + 2.55, center.y - 2.8, center.z)),
            center,
            height * 1.18,
        ),
        "seated_rear_three_quarter": (
            Vector((center.x - 2.55, center.y + 2.8, center.z)),
            center,
            height * 1.18,
        ),
        "seat_contact_close_profile": (
            Vector((center.x + 2.4, center.y, low.z + height * 0.60)),
            Vector((center.x, center.y, low.z + height * 0.49)),
            max(width * 1.45, height * 0.53),
        ),
        "both_feet_supported_close": (
            Vector((center.x + 2.4, center.y - 0.4, low.z + height * 0.14)),
            Vector((center.x, center.y - 0.08, low.z + height * 0.08)),
            max(width * 1.55, height * 0.31),
        ),
    }
    renders: dict[str, str] = {}
    for label, (location, target, scale) in views.items():
        path = output_dir / f"{label}.png"
        render_view(scene, camera, path, location, target, scale)
        renders[label] = path.name
    return renders


def degrees_record(
    rotations: dict[str, tuple[float, float, float]],
) -> dict[str, list[float]]:
    return {
        name: [round(math.degrees(value), 6) for value in rotation]
        for name, rotation in rotations.items()
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    source_path = PROJECT_ROOT / SOURCE_REL
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    source_hash_before = sha256_file(source_path)
    if source_hash_before != SOURCE_SHA256:
        raise RuntimeError(
            f"R9b source hash mismatch: {source_hash_before} != {SOURCE_SHA256}"
        )
    if Path(bpy.data.filepath).resolve() != source_path.resolve():
        raise RuntimeError(
            "worker must be launched with the exact R9b Blend as Blender input"
        )

    body, armature = find_body_and_armature()
    hair_objects = scalp_hair_objects()
    for obj in hair_objects:
        obj.hide_render = True
        obj.hide_viewport = True

    required_bones = set(seated_rotations(-78.0, 88.0, 0.0))
    missing_bones = sorted(required_bones - {bone.name for bone in armature.data.bones})
    if missing_bones:
        raise RuntimeError(f"native rig lacks required seated bones: {missing_bones}")

    regions = {
        "pelvis": region_indices(
            body,
            ("pelvis_", "lThighBend_", "rThighBend_"),
            minimum_weight=0.16,
        ),
        "left_foot": region_indices(
            body,
            ("lFoot_", "lToe_", "lMetatarsals_"),
            minimum_weight=0.10,
        ),
        "right_foot": region_indices(
            body,
            ("rFoot_", "rToe_", "rMetatarsals_"),
            minimum_weight=0.10,
        ),
    }
    if any(not indices for indices in regions.values()):
        raise RuntimeError(
            "one or more required weighted surface regions are absent: "
            + json.dumps({key: len(value) for key, value in regions.items()})
        )

    reset_pose(armature)
    selected, top_search = pose_search(body, armature, regions)
    selected_rotations = seated_rotations(
        selected["hip_degrees"],
        selected["knee_degrees"],
        selected["ankle_degrees"],
    )
    inventory = {
        "source": rel(source_path),
        "source_sha256": source_hash_before,
        "body_object": body.name,
        "body_vertices": len(body.data.vertices),
        "body_polygons": len(body.data.polygons),
        "armature_object": armature.name,
        "native_joint_count": len(armature.data.bones),
        "hair_objects_excluded": sorted(obj.name for obj in hair_objects),
        "region_vertex_counts": {
            key: len(value) for key, value in regions.items()
        },
        "selected_pose": selected,
        "top_pose_search_results": top_search,
    }
    if args.preflight_only:
        posed_points = evaluated_vertices(body)
        inventory["preflight_contact_solution"] = contact_solution(
            body, posed_points, regions
        )
        print(json.dumps(inventory, indent=2, sort_keys=True))
        reset_pose(armature)
        if sha256_file(source_path) != source_hash_before:
            raise RuntimeError("source Blend changed during preflight")
        return 0

    output_dir = Path(args.output_dir).resolve()
    expected_output = (PROJECT_ROOT / OUTPUT_REL).resolve()
    if output_dir != expected_output:
        raise RuntimeError(
            f"append-only probe must use exact output path {expected_output}"
        )
    if output_dir.exists():
        raise FileExistsError(
            f"append-only attempt_01 already exists; refusing overwrite: {output_dir}"
        )
    output_dir.mkdir(parents=True)

    # Exact neutral report is deliberately captured before adding the new
    # action or props, so inherited R9b penetrations remain distinguishable
    # from pose-induced change.
    reset_pose(armature)
    neutral_exact = exact_intersection_report(body)
    neutral_exact_path = output_dir / "EXACT_INTERSECTIONS_NEUTRAL_BASELINE.json"
    write_json(neutral_exact_path, neutral_exact)

    action = author_action(armature, selected_rotations)
    posed_points = evaluated_vertices(body)
    contact = contact_solution(body, posed_points, regions)
    posed_exact = exact_intersection_report(body)
    posed_exact_path = output_dir / "EXACT_INTERSECTIONS_SEATED_POSE.json"
    write_json(posed_exact_path, posed_exact)

    removed_prior_props = remove_prior_contact_props()
    # Removing prior context props does not affect the armature or evaluated
    # candidate body.  Re-assert the selected action after scene mutation.
    armature.animation_data.action = action
    bpy.context.scene.frame_set(POSE_FRAME)
    bpy.context.view_layer.update()
    support_props = make_support_props(contact, posed_points)

    for obj in list(hair_objects):
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)

    body["private_r19_seated_contact_probe"] = True
    body["runtime_assignment_allowed"] = False
    body["owner_approved"] = False
    armature["private_r19_seated_contact_probe"] = True
    armature["runtime_assignment_allowed"] = False
    bpy.context.scene["probe_status"] = "PRIVATE_APPEND_ONLY_ENGINEERING_EVIDENCE"
    bpy.context.scene["source_r9b_sha256"] = SOURCE_SHA256
    bpy.context.scene["scalp_hair_dependency"] = False

    renders = render_evidence(output_dir, body)
    blend_path = output_dir / "kira_r19_blackproject_seated_contact_probe.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)

    source_hash_after = sha256_file(source_path)
    if source_hash_after != source_hash_before:
        raise RuntimeError("R9b source Blend changed during append-only probe")

    neutral_count = int(neutral_exact["exact_genuine_penetration_pair_count"])
    posed_count = int(posed_exact["exact_genuine_penetration_pair_count"])
    delta = posed_count - neutral_count
    exact_gate = posed_count == 0
    inherited_baseline_not_repaired_here = neutral_count > 0
    contact_gate = bool(
        contact["all_three_supports_within_tolerance"]
        and contact["all_three_supports_no_penetration"]
    )
    evidence = {
        "schema_version": 1,
        "status": "PRIVATE_APPEND_ONLY_SEATED_CONTACT_PROBE",
        "attempt": "attempt_01",
        "scope": {
            "native_blackproject_rig_only": True,
            "source_or_runtime_changed": False,
            "scalp_hair_included": False,
            "candidate_activation_or_assignment": False,
            "body_surface_repair_attempted": False,
            "purpose": (
                "solve and measure a seated-pose/contact configuration for "
                "reuse by the next derivative candidate"
            ),
        },
        "source": {
            "path": rel(source_path),
            "sha256_before": source_hash_before,
            "sha256_after": source_hash_after,
            "unchanged": source_hash_before == source_hash_after,
            "baseline_status": "REJECTED_R9B_ENGINEERING_MATERIAL",
        },
        "inventory": inventory,
        "authored_action": {
            "name": action.name,
            "frame": POSE_FRAME,
            "rotations_degrees_xyz": degrees_record(selected_rotations),
            "native_joint_count": len(armature.data.bones),
        },
        "contact_solution": contact,
        "exact_nonadjacent_intersections": {
            "neutral_baseline_report": rel(neutral_exact_path),
            "neutral_baseline_exact_genuine_pair_count": neutral_count,
            "seated_pose_report": rel(posed_exact_path),
            "seated_pose_exact_genuine_pair_count": posed_count,
            "seated_minus_neutral_exact_pair_delta": delta,
            "absolute_zero_intersection_gate_passed": exact_gate,
            "inherited_r9b_surface_intersections_present": (
                inherited_baseline_not_repaired_here
            ),
            "truth_note": (
                "This bounded contact probe does not repair R9b's rejected "
                "surface.  An absolute intersection pass therefore requires "
                "the next derivative body to reproduce the pose against its "
                "repaired zero-intersection surface."
            ),
        },
        "gates": {
            "native_188_joint_rig_preserved": len(armature.data.bones) == 188,
            "seat_contact_within_tolerance": contact["seat"][
                "within_contact_tolerance"
            ],
            "left_foot_support_within_tolerance": contact["floor"][
                "left_foot"
            ]["within_contact_tolerance"],
            "right_foot_support_within_tolerance": contact["floor"][
                "right_foot"
            ]["within_contact_tolerance"],
            "support_surface_penetration_absent": contact[
                "all_three_supports_no_penetration"
            ],
            "contact_geometry_gate_passed": contact_gate,
            "absolute_exact_self_intersection_gate_passed": exact_gate,
            "overall_probe_is_body_acceptance": False,
        },
        "artifacts": {
            "blend": blend_path.name,
            "renders": renders,
            "support_props": [obj.name for obj in support_props],
            "prior_context_props_removed_from_probe_copy": removed_prior_props,
        },
        "truth_note": (
            "A contact pass proves only measured seat and foot support for "
            "this inactive probe.  It does not approve R9b, repair its adult "
            "surface, prove all movement, or authorize activation."
        ),
    }
    evidence_path = output_dir / "BUILD_EVIDENCE.json"
    write_json(evidence_path, evidence)

    manifest_entries: list[dict[str, Any]] = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name.lower()):
        if path.name == "PACKAGE_MANIFEST.json" or not path.is_file():
            continue
        manifest_entries.append(
            {
                "path": rel(path),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schema_version": 1,
        "attempt": "attempt_01",
        "append_only": True,
        "source_unchanged": source_hash_after == source_hash_before,
        "files": manifest_entries,
    }
    write_json(output_dir / "PACKAGE_MANIFEST.json", manifest)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
