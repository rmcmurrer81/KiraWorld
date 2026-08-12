#!/usr/bin/env python3
"""Read-only post-build engineering audit for one private Kira candidate.

Run this script in a new background Blender process with factory startup and
auto-execution disabled.  It opens an exact SHA-256-bound Blend, evaluates the
actual armature-deformed primary mesh in bounded rest and pose states, and
writes one append-only JSON artifact outside the candidate directory.  It
never renders, saves, exports, assigns, activates, or visually accepts a body.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import sys
import traceback
from typing import Any, Callable, Mapping, Sequence

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_adult_female_surface_authoring import (  # noqa: E402
    LANDMARK_GROUP_PREFIX,
    METHOD_ID as ADULT_SURFACE_METHOD_ID,
)
from Core.avatar_adult_female_surface_authoring_v2 import (  # noqa: E402
    METHOD_ID as ADULT_SURFACE_DETAIL_METHOD_ID,
)
from Core.avatar_profiled_adult_candidate_contract import (  # noqa: E402
    BUILDER_CONFIG_PATH,
    OWNER_REVIEW_VIEW_LABELS,
    load_validated_profiled_candidate_builder_config,
    scaled_adult_surface_settings,
)
from Core.avatar_profiled_kira_candidate_audit_contract import (  # noqa: E402
    MAIN_EVIDENCE_NAME,
    evaluate_postbuild_audit_preflight,
    sha256_file,
    verify_inputs_unchanged,
)
from tools.blender_audit_inactive_adult_female_foundation import (  # noqa: E402
    LANDMARK_GROUPS,
    SUBGROUPS,
    _coincident_duplicate_triangles,
    _component_labels,
    _group_members,
    _induced_component_count,
)
from tools.blender_exact_mesh_intersections import (  # noqa: E402
    exact_nonadjacent_intersection_report,
)


AUDITOR_ID = "profiled_kira_candidate_postbuild_auditor_v2"
LEFT_KNEE_ACTION = "kira_profiled_private_knee_flex_left_axis_solved"
RIGHT_KNEE_ACTION = "kira_profiled_private_knee_flex_right_axis_solved"
POSE_NAMES = (
    "rest",
    "symmetric_upperleg_flexion",
    "asymmetric_upperleg_lunge",
    "symmetric_pelvis_open",
    "left_knee_flexion",
    "right_knee_flexion",
    "bilateral_knee_flexion",
)
GLOBAL_EDGE_RATIO_BOUNDS = (0.35, 2.0)
PELVIC_EDGE_RATIO_BOUNDS = (0.55, 1.55)
MAX_NEW_GLOBAL_EXACT_INTERSECTIONS = 8
RELATIONSHIP_EXTENT_RATIO_MINIMUM = 0.35
RELATIONSHIP_RMS_RATIO_MINIMUM = 0.35
RELATIONSHIP_AREA_RATIO_MINIMUM = 0.15

ORDERING_SPECS: Mapping[str, tuple[str, str, str, float, str]] = {
    "labia_majora_left_right": (
        "labia_majora_left",
        "labia_majora_right",
        "normalized_lateral_u",
        0.10,
        "positive u is configured anatomical left",
    ),
    "labia_minora_left_right": (
        "labia_minora_left",
        "labia_minora_right",
        "normalized_lateral_u",
        0.10,
        "positive u is configured anatomical left",
    ),
    "urethral_anterior_to_vaginal": (
        "urethral_opening_anterior_to_vaginal_opening",
        "vaginal_opening",
        "normalized_longitudinal_v",
        0.05,
        "positive v is configured anterior/superior",
    ),
    "clitoris_anterior_to_vaginal": (
        "clitoris",
        "vaginal_opening",
        "normalized_longitudinal_v",
        0.05,
        "positive v is configured anterior/superior",
    ),
    "vaginal_anterior_to_fourchette": (
        "vaginal_opening",
        "posterior_commissure_fourchette",
        "normalized_longitudinal_v",
        0.05,
        "positive v is configured anterior/superior",
    ),
    "fourchette_anterior_to_anal_recess": (
        "posterior_commissure_fourchette",
        "posterior_anal_recess",
        "normalized_longitudinal_v",
        0.05,
        "positive v is configured anterior/superior",
    ),
    "perineal_transition_anterior_to_anal_recess": (
        "perineal_transition",
        "posterior_anal_recess",
        "normalized_longitudinal_v",
        0.05,
        "positive v is configured anterior/superior",
    ),
}

RELIEF_SPECS: Mapping[str, tuple[str, str, float]] = {
    "labia_majora_outward_of_vaginal_recess": (
        "paired_labia_majora", "vaginal_opening", 0.005
    ),
    "labia_minora_outward_of_vaginal_recess": (
        "paired_labia_minora", "vaginal_opening", 0.003
    ),
    "vestibule_outward_of_vaginal_recess": (
        "vestibule", "vaginal_opening", 0.005
    ),
    "clitoris_outward_of_urethral_recess": (
        "clitoris", "urethral_opening_anterior_to_vaginal_opening", 0.001
    ),
    "fourchette_outward_of_vaginal_recess": (
        "posterior_commissure_fourchette", "vaginal_opening", 0.005
    ),
    "perineal_transition_outward_of_anal_recess": (
        "perineal_transition", "posterior_anal_recess", 0.003
    ),
}


class ProfiledKiraPostbuildAuditError(RuntimeError):
    """Raised when the fresh-process audit cannot safely continue."""


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(
        description="Read-only append-only post-build Kira candidate audit."
    )
    parser.add_argument("--blend", required=True)
    parser.add_argument("--blend-sha256", required=True)
    parser.add_argument("--build-evidence-sha256", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--optional-private-glb")
    parser.add_argument("--optional-private-glb-sha256")
    return parser.parse_args(argv)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ProfiledKiraPostbuildAuditError(f"JSON root must be an object: {path}")
    return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _relative(path: Path) -> str:
    return path.resolve(strict=True).relative_to(PROJECT_ROOT.resolve(strict=True)).as_posix()


def _stat_record(path: Path) -> dict[str, Any]:
    value = path.stat()
    return {
        "path": _relative(path),
        "sha256": sha256_file(path),
        "size_bytes": int(value.st_size),
        "mtime_ns_observed": int(value.st_mtime_ns),
        "read_only_audit_input": True,
    }


def _factory_startup_fingerprint() -> dict[str, Any]:
    objects = sorted((obj.name, obj.type) for obj in bpy.data.objects)
    record = {
        "background": bool(bpy.app.background),
        "blend_filepath_empty": bpy.data.filepath == "",
        "scene_names": sorted(scene.name for scene in bpy.data.scenes),
        "objects": [{"name": name, "type": kind} for name, kind in objects],
        "library_count": len(bpy.data.libraries),
        "expected_command_flags": [
            "--background", "--factory-startup", "--disable-autoexec"
        ],
    }
    record["passed"] = bool(
        record["background"]
        and record["blend_filepath_empty"]
        and record["scene_names"] == ["Scene"]
        and objects == [("Camera", "CAMERA"), ("Cube", "MESH"), ("Light", "LIGHT")]
        and record["library_count"] == 0
    )
    return record


def _canonical_cycle(indices: Sequence[int]) -> tuple[int, ...]:
    values = tuple(int(value) for value in indices)
    rotations = [values[index:] + values[:index] for index in range(len(values))]
    reverse = tuple(reversed(values))
    rotations.extend(
        reverse[index:] + reverse[:index] for index in range(len(reverse))
    )
    return min(rotations)


def _topology_signature(bm: bmesh.types.BMesh) -> dict[str, Any]:
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.index_update()
    bm.faces.index_update()
    edges = sorted(
        tuple(sorted(int(vert.index) for vert in edge.verts)) for edge in bm.edges
    )
    faces = sorted(_canonical_cycle([vert.index for vert in face.verts]) for face in bm.faces)
    payload = json.dumps(
        {
            "vertices": len(bm.verts),
            "edges": edges,
            "faces": faces,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "vertex_count": len(bm.verts),
        "edge_count": len(bm.edges),
        "face_count": len(bm.faces),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _stats(values: Sequence[float]) -> dict[str, float | None]:
    finite = [float(value) for value in values if math.isfinite(float(value))]
    if not finite:
        return {"minimum": None, "median": None, "mean": None, "maximum": None}
    return {
        "minimum": min(finite),
        "median": statistics.median(finite),
        "mean": statistics.fmean(finite),
        "maximum": max(finite),
    }


def _percentile(values: Sequence[float], fraction: float) -> float | None:
    finite = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not finite:
        return None
    position = (len(finite) - 1) * fraction
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return finite[lower]
    alpha = position - lower
    return finite[lower] * (1.0 - alpha) + finite[upper] * alpha


def _local_coordinates(point: Vector, frame: Mapping[str, Any]) -> tuple[float, float, float]:
    origin = Vector(frame["origin"])
    lateral = Vector(frame["lateral_axis"]).normalized()
    longitudinal = Vector(frame["longitudinal_axis"]).normalized()
    outward = Vector(frame["outward_axis"]).normalized()
    delta = point - origin
    return (
        float(delta.dot(lateral) / float(frame["half_width_m"])),
        float(delta.dot(longitudinal) / float(frame["half_length_m"])),
        float(delta.dot(outward)),
    )


def _relationship_geometry(
    bm: bmesh.types.BMesh,
    members: set[int],
    *,
    frame: Mapping[str, Any],
    minimum_vertices: int,
    component_labels: Mapping[int, int],
    primary_component_id: int,
) -> dict[str, Any]:
    bm.verts.ensure_lookup_table()
    points = [bm.verts[index].co.copy() for index in sorted(members) if index < len(bm.verts)]
    incident_edges = [
        edge for edge in bm.edges
        if any(int(vert.index) in members for vert in edge.verts)
    ]
    internal_edges = [
        edge for edge in bm.edges
        if all(int(vert.index) in members for vert in edge.verts)
    ]
    connection_edges = [
        edge for edge in incident_edges
        if not all(int(vert.index) in members for vert in edge.verts)
    ]
    incident_faces = [
        face for face in bm.faces
        if any(int(vert.index) in members for vert in face.verts)
    ]
    internal_faces = [
        face for face in bm.faces
        if all(int(vert.index) in members for vert in face.verts)
    ]
    if points:
        low = Vector(tuple(min(float(point[axis]) for point in points) for axis in range(3)))
        high = Vector(tuple(max(float(point[axis]) for point in points) for axis in range(3)))
        centroid = sum(points, Vector((0.0, 0.0, 0.0))) / len(points)
        extent = float((high - low).length)
        rms_radius = math.sqrt(
            statistics.fmean(float((point - centroid).length_squared) for point in points)
        )
    else:
        low = high = centroid = Vector((0.0, 0.0, 0.0))
        extent = rms_radius = 0.0
    local = [_local_coordinates(point, frame) for point in points]
    u_values = [value[0] for value in local]
    v_values = [value[1] for value in local]
    depths = [value[2] for value in local]
    area = sum(float(face.calc_area()) for face in incident_faces)
    depth_span = max(depths, default=0.0) - min(depths, default=0.0)
    geometry_present = bool(
        len(points) >= minimum_vertices
        and internal_edges
        and incident_faces
        and area > 1.0e-12
        and extent > 1.0e-7
        and depth_span > 1.0e-6
    )
    connected = bool(
        geometry_present
        and connection_edges
        and all(component_labels.get(index) == primary_component_id for index in members)
    )
    return {
        "vertex_count": len(points),
        "minimum_vertex_count_required": minimum_vertices,
        "incident_edge_count": len(incident_edges),
        "internal_edge_count": len(internal_edges),
        "connection_edge_count": len(connection_edges),
        "incident_face_count": len(incident_faces),
        "internal_face_count": len(internal_faces),
        "incident_surface_area_m2": area,
        "induced_component_count": _induced_component_count(bm, members),
        "bounds_min_object_m": [float(value) for value in low],
        "bounds_max_object_m": [float(value) for value in high],
        "centroid_object_m": [float(value) for value in centroid],
        "spatial_extent_m": extent,
        "rms_radius_m": rms_radius,
        "normalized_lateral_u": _stats(u_values),
        "normalized_longitudinal_v": _stats(v_values),
        "outward_depth_m": _stats(depths),
        "outward_depth_span_m": depth_span,
        "geometry_present": geometry_present,
        "connected_to_primary_surface": connected,
    }


def _median(record: Mapping[str, Any], field: str) -> float:
    value = record.get(field)
    if not isinstance(value, Mapping):
        return math.nan
    median = value.get("median")
    return float(median) if isinstance(median, (int, float)) else math.nan


def _relationship_checks(
    records: Mapping[str, Mapping[str, Any]],
    *,
    rest_checks: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    ordering: dict[str, Any] = {}
    for label, (first, second, field, rest_minimum, convention) in ORDERING_SPECS.items():
        first_value = _median(records[first], field)
        second_value = _median(records[second], field)
        margin = first_value - second_value
        if rest_checks is None:
            minimum = rest_minimum
        else:
            rest_margin = float(rest_checks["ordering"][label]["measured_margin"])
            minimum = max(0.01 if field == "normalized_lateral_u" else 0.005, rest_margin * 0.20)
        passed = math.isfinite(margin) and margin > minimum
        ordering[label] = {
            "first_group": first,
            "second_group": second,
            "coordinate": field,
            "first_median": first_value,
            "second_median": second_value,
            "measured_margin": margin,
            "minimum_margin_required": minimum,
            "rest_minimum_margin": rest_minimum,
            "coordinate_convention": convention,
            "passed": passed,
        }
    relief: dict[str, Any] = {}
    for label, (outward, recessed, rest_minimum) in RELIEF_SPECS.items():
        outward_depth = _median(records[outward], "outward_depth_m")
        recessed_depth = _median(records[recessed], "outward_depth_m")
        margin = outward_depth - recessed_depth
        if rest_checks is None:
            minimum = rest_minimum
        else:
            rest_margin = float(rest_checks["relief"][label]["measured_margin_m"])
            minimum = max(0.0002, rest_margin * 0.10)
        passed = math.isfinite(margin) and margin > minimum
        relief[label] = {
            "outward_group": outward,
            "recessed_group": recessed,
            "outward_median_depth_m": outward_depth,
            "recessed_median_depth_m": recessed_depth,
            "measured_margin_m": margin,
            "minimum_margin_required_m": minimum,
            "rest_minimum_margin_m": rest_minimum,
            "coordinate_convention": "larger depth is farther outward from the body",
            "passed": passed,
        }
    return {
        "ordering": ordering,
        "relief": relief,
        "ordering_passed": all(record["passed"] for record in ordering.values()),
        "relief_passed": all(record["passed"] for record in relief.values()),
    }


def _reset_pose(armature: bpy.types.Object) -> None:
    if armature.animation_data is not None:
        armature.animation_data.action = None
    bpy.context.scene.frame_set(1)
    for bone in armature.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def _set_local_rotation(armature: bpy.types.Object, bone_name: str, axis: Vector, degrees: float) -> None:
    bone = armature.pose.bones.get(bone_name)
    if bone is None:
        raise ProfiledKiraPostbuildAuditError(f"required pose bone missing: {bone_name}")
    bone.rotation_mode = "QUATERNION"
    bone.rotation_quaternion = Quaternion(axis, math.radians(degrees))


def _action_snapshot(armature: bpy.types.Object, action_name: str) -> dict[str, Matrix]:
    action = bpy.data.actions.get(action_name)
    if action is None:
        raise ProfiledKiraPostbuildAuditError(f"required knee action missing: {action_name}")
    _reset_pose(armature)
    armature.animation_data_create()
    armature.animation_data.action = action
    bpy.context.scene.frame_set(30)
    bpy.context.view_layer.update()
    snapshot = {
        bone.name: bone.matrix_basis.copy()
        for bone in armature.pose.bones
        if any(
            abs(float(bone.matrix_basis[row][column]) - (1.0 if row == column else 0.0))
            > 1.0e-8
            for row in range(4)
            for column in range(4)
        )
    }
    _reset_pose(armature)
    if not snapshot:
        raise ProfiledKiraPostbuildAuditError(f"knee action has no evaluated pose: {action_name}")
    return snapshot


def _apply_snapshot(armature: bpy.types.Object, snapshot: Mapping[str, Matrix]) -> None:
    for name, matrix in snapshot.items():
        bone = armature.pose.bones.get(name)
        if bone is None:
            raise ProfiledKiraPostbuildAuditError(f"action pose bone missing: {name}")
        bone.matrix_basis = matrix.copy()
    bpy.context.view_layer.update()


def _pose_setters(armature: bpy.types.Object) -> Mapping[str, Callable[[], None]]:
    left_knee = _action_snapshot(armature, LEFT_KNEE_ACTION)
    right_knee = _action_snapshot(armature, RIGHT_KNEE_ACTION)

    def rest() -> None:
        _reset_pose(armature)

    def symmetric_upperleg() -> None:
        _reset_pose(armature)
        _set_local_rotation(armature, "upperleg01.L", Vector((1.0, 0.0, 0.0)), 12.0)
        _set_local_rotation(armature, "upperleg01.R", Vector((1.0, 0.0, 0.0)), 12.0)
        bpy.context.view_layer.update()

    def asymmetric_upperleg() -> None:
        _reset_pose(armature)
        _set_local_rotation(armature, "upperleg01.L", Vector((1.0, 0.0, 0.0)), 20.0)
        _set_local_rotation(armature, "upperleg01.R", Vector((1.0, 0.0, 0.0)), -10.0)
        bpy.context.view_layer.update()

    def symmetric_pelvis() -> None:
        _reset_pose(armature)
        _set_local_rotation(armature, "pelvis.L", Vector((0.0, 0.0, 1.0)), 8.0)
        _set_local_rotation(armature, "pelvis.R", Vector((0.0, 0.0, 1.0)), -8.0)
        bpy.context.view_layer.update()

    def knee_left() -> None:
        _reset_pose(armature)
        _apply_snapshot(armature, left_knee)

    def knee_right() -> None:
        _reset_pose(armature)
        _apply_snapshot(armature, right_knee)

    def knees_bilateral() -> None:
        _reset_pose(armature)
        _apply_snapshot(armature, left_knee)
        _apply_snapshot(armature, right_knee)

    return {
        "rest": rest,
        "symmetric_upperleg_flexion": symmetric_upperleg,
        "asymmetric_upperleg_lunge": asymmetric_upperleg,
        "symmetric_pelvis_open": symmetric_pelvis,
        "left_knee_flexion": knee_left,
        "right_knee_flexion": knee_right,
        "bilateral_knee_flexion": knees_bilateral,
    }


def _pose_bone_deltas(armature: bpy.types.Object) -> dict[str, Any]:
    names = (
        "pelvis.L",
        "pelvis.R",
        "upperleg01.L",
        "upperleg01.R",
        "lowerleg01.L",
        "lowerleg01.R",
    )
    result: dict[str, Any] = {}
    for name in names:
        bone = armature.pose.bones.get(name)
        if bone is None:
            result[name] = {"present": False}
            continue
        translation, rotation, scale = bone.matrix_basis.decompose()
        rotation.normalize()
        angle = math.degrees(float(rotation.angle))
        axis = rotation.axis if angle > 1.0e-7 else Vector((0.0, 0.0, 0.0))
        result[name] = {
            "present": True,
            "rotation_angle_degrees": angle,
            "rotation_axis_local": [float(value) for value in axis],
            "translation_m": [float(value) for value in translation],
            "scale": [float(value) for value in scale],
            "matrix_basis": [
                [float(value) for value in row] for row in bone.matrix_basis
            ],
        }
    return result


def _pose_intent_gates(poses: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    def angle(pose: str, bone: str) -> float:
        return float(poses[pose]["pose_bone_deltas"][bone]["rotation_angle_degrees"])

    def axis_component(pose: str, bone: str, axis: int) -> float:
        return float(poses[pose]["pose_bone_deltas"][bone]["rotation_axis_local"][axis])

    symmetric_left = angle("symmetric_upperleg_flexion", "upperleg01.L")
    symmetric_right = angle("symmetric_upperleg_flexion", "upperleg01.R")
    asymmetric_left = angle("asymmetric_upperleg_lunge", "upperleg01.L")
    asymmetric_right = angle("asymmetric_upperleg_lunge", "upperleg01.R")
    pelvis_left = angle("symmetric_pelvis_open", "pelvis.L")
    pelvis_right = angle("symmetric_pelvis_open", "pelvis.R")
    left_knee_left = angle("left_knee_flexion", "lowerleg01.L")
    left_knee_right = angle("left_knee_flexion", "lowerleg01.R")
    right_knee_left = angle("right_knee_flexion", "lowerleg01.L")
    right_knee_right = angle("right_knee_flexion", "lowerleg01.R")
    both_knee_left = angle("bilateral_knee_flexion", "lowerleg01.L")
    both_knee_right = angle("bilateral_knee_flexion", "lowerleg01.R")
    checks = {
        "rest_relevant_bones_are_identity": all(
            angle("rest", bone) <= 1.0e-5
            for bone in (
                "pelvis.L", "pelvis.R", "upperleg01.L", "upperleg01.R",
                "lowerleg01.L", "lowerleg01.R",
            )
        ),
        "symmetric_upperleg_pose_is_bilateral_equal_and_same_axis": bool(
            10.0 <= symmetric_left <= 14.0
            and 10.0 <= symmetric_right <= 14.0
            and abs(symmetric_left - symmetric_right) <= 0.01
            and axis_component("symmetric_upperleg_flexion", "upperleg01.L", 0) > 0.99
            and axis_component("symmetric_upperleg_flexion", "upperleg01.R", 0) > 0.99
        ),
        "asymmetric_upperleg_pose_has_bounded_opposed_unequal_deltas": bool(
            18.0 <= asymmetric_left <= 22.0
            and 8.0 <= asymmetric_right <= 12.0
            and axis_component("asymmetric_upperleg_lunge", "upperleg01.L", 0) > 0.99
            and axis_component("asymmetric_upperleg_lunge", "upperleg01.R", 0) < -0.99
        ),
        "symmetric_pelvis_open_pose_is_bilateral_mirrored": bool(
            6.0 <= pelvis_left <= 10.0
            and 6.0 <= pelvis_right <= 10.0
            and abs(pelvis_left - pelvis_right) <= 0.01
            and axis_component("symmetric_pelvis_open", "pelvis.L", 2) > 0.99
            and axis_component("symmetric_pelvis_open", "pelvis.R", 2) < -0.99
        ),
        "left_knee_action_deforms_only_left_lowerleg": bool(
            left_knee_left >= 15.0 and left_knee_right <= 1.0e-4
        ),
        "right_knee_action_deforms_only_right_lowerleg": bool(
            right_knee_right >= 15.0 and right_knee_left <= 1.0e-4
        ),
        "bilateral_knee_pose_deforms_both_lowerlegs": bool(
            both_knee_left >= 15.0 and both_knee_right >= 15.0
        ),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "measured_angles_degrees": {
            "symmetric_upperleg_left": symmetric_left,
            "symmetric_upperleg_right": symmetric_right,
            "asymmetric_upperleg_left": asymmetric_left,
            "asymmetric_upperleg_right": asymmetric_right,
            "symmetric_pelvis_left": pelvis_left,
            "symmetric_pelvis_right": pelvis_right,
            "left_pose_left_knee": left_knee_left,
            "left_pose_right_knee": left_knee_right,
            "right_pose_left_knee": right_knee_left,
            "right_pose_right_knee": right_knee_right,
            "bilateral_pose_left_knee": both_knee_left,
            "bilateral_pose_right_knee": both_knee_right,
        },
    }


def _evaluated_bmesh(body: bpy.types.Object) -> tuple[Any, bmesh.types.BMesh]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.index_update()
    bm.faces.index_update()
    bm.normal_update()
    return evaluated, bm


def _edge_lengths(bm: bmesh.types.BMesh) -> list[float]:
    return [float((edge.verts[0].co - edge.verts[1].co).length) for edge in bm.edges]


def _edge_ratio_record(
    current: Sequence[float],
    rest: Sequence[float],
    indices: Sequence[int],
    bounds: tuple[float, float],
) -> dict[str, Any]:
    available = [
        index for index in indices
        if 0 <= index < len(current) and index < len(rest)
    ]
    ratios = [
        float(current[index] / rest[index])
        for index in available
        if rest[index] > 1.0e-12
    ]
    minimum = min(ratios, default=0.0)
    maximum = max(ratios, default=math.inf)
    return {
        "requested_edge_count": len(indices),
        "available_edge_count": len(available),
        "nonzero_rest_edge_count": len(ratios),
        "minimum_ratio": minimum,
        "p05_ratio": _percentile(ratios, 0.05),
        "median_ratio": _percentile(ratios, 0.50),
        "p95_ratio": _percentile(ratios, 0.95),
        "maximum_ratio": maximum,
        "minimum_allowed": bounds[0],
        "maximum_allowed": bounds[1],
        "passed": bool(
            ratios
            and len(available) == len(indices)
            and len(ratios) == len(indices)
            and minimum >= bounds[0]
            and maximum <= bounds[1]
        ),
    }


def _pose_mesh_record(
    body: bpy.types.Object,
    *,
    frame: Mapping[str, Any],
    group_members: Mapping[str, set[int]],
    minimum_vertices: int,
    pelvic_vertices: set[int],
    rest: Mapping[str, Any] | None,
) -> dict[str, Any]:
    evaluated, bm = _evaluated_bmesh(body)
    try:
        finite = all(
            math.isfinite(float(component))
            for vert in bm.verts
            for component in vert.co
        )
        topology = _topology_signature(bm)
        component_labels, sizes = _component_labels(bm)
        primary_component = max(range(len(sizes)), key=sizes.__getitem__) if sizes else -1
        relationships = {
            name: _relationship_geometry(
                bm,
                members,
                frame=frame,
                minimum_vertices=minimum_vertices,
                component_labels=component_labels,
                primary_component_id=primary_component,
            )
            for name, members in group_members.items()
        }
        relation_checks = _relationship_checks(
            relationships,
            rest_checks=None if rest is None else rest["relationship_checks"],
        )
        exact = exact_nonadjacent_intersection_report(bm, include_pair_details=True)
        genuine_pairs = [
            row for row in exact["pairs"]
            if row.get("genuine_positive_area_or_segment_penetration") is True
        ]
        exact_pair_signatures = sorted(
            tuple(sorted(int(index) for index in row["face_indices"]))
            for row in genuine_pairs
        )
        pelvic_faces = {
            int(face.index)
            for face in bm.faces
            if any(int(vert.index) in pelvic_vertices for vert in face.verts)
        }
        pelvic_pairs = [
            row for row in genuine_pairs
            if any(int(index) in pelvic_faces for index in row["face_indices"])
        ]
        pelvic_pair_signatures = sorted(
            tuple(sorted(int(index) for index in row["face_indices"]))
            for row in pelvic_pairs
        )
        lengths = _edge_lengths(bm)
        if rest is None:
            all_edge_indices = list(range(len(lengths)))
            pelvic_edge_indices = [
                int(edge.index) for edge in bm.edges
                if all(int(vert.index) in pelvic_vertices for vert in edge.verts)
            ]
            edge_stretch = {
                "global": _edge_ratio_record(lengths, lengths, all_edge_indices, GLOBAL_EDGE_RATIO_BOUNDS),
                "pelvic_patch": _edge_ratio_record(lengths, lengths, pelvic_edge_indices, PELVIC_EDGE_RATIO_BOUNDS),
            }
        else:
            all_edge_indices = list(range(len(lengths)))
            pelvic_edge_indices = list(rest["pelvic_edge_indices"])
            edge_stretch = {
                "global": _edge_ratio_record(
                    lengths, rest["edge_lengths"], all_edge_indices, GLOBAL_EDGE_RATIO_BOUNDS
                ),
                "pelvic_patch": _edge_ratio_record(
                    lengths, rest["edge_lengths"], pelvic_edge_indices, PELVIC_EDGE_RATIO_BOUNDS
                ),
            }
        topology_metrics = {
            "surface_component_count": len(sizes),
            "boundary_edge_count": sum(len(edge.link_faces) == 1 for edge in bm.edges),
            "nonmanifold_edge_count": sum(len(edge.link_faces) not in {1, 2} for edge in bm.edges),
            "degenerate_face_count": sum(float(face.calc_area()) <= 1.0e-12 for face in bm.faces),
            "coincident_duplicate_triangle_pair_count": _coincident_duplicate_triangles(bm),
            "exact_nonadjacent_intersection_pair_count": int(
                exact["exact_genuine_penetration_pair_count"]
            ),
            "pelvic_patch_exact_intersection_pair_count": len(pelvic_pairs),
        }
        geometry_present = all(
            record["geometry_present"] and record["connected_to_primary_surface"]
            for record in relationships.values()
        )
        collapse: dict[str, Any] = {}
        if rest is not None:
            for name, current in relationships.items():
                baseline = rest["relationships"][name]
                extent_ratio = current["spatial_extent_m"] / max(
                    float(baseline["spatial_extent_m"]), 1.0e-12
                )
                rms_ratio = current["rms_radius_m"] / max(
                    float(baseline["rms_radius_m"]), 1.0e-12
                )
                area_ratio = current["incident_surface_area_m2"] / max(
                    float(baseline["incident_surface_area_m2"]), 1.0e-12
                )
                collapse[name] = {
                    "vertex_count_unchanged": current["vertex_count"] == baseline["vertex_count"],
                    "extent_ratio_to_rest": extent_ratio,
                    "rms_radius_ratio_to_rest": rms_ratio,
                    "incident_area_ratio_to_rest": area_ratio,
                    "passed": bool(
                        current["vertex_count"] == baseline["vertex_count"]
                        and extent_ratio >= RELATIONSHIP_EXTENT_RATIO_MINIMUM
                        and rms_ratio >= RELATIONSHIP_RMS_RATIO_MINIMUM
                        and area_ratio >= RELATIONSHIP_AREA_RATIO_MINIMUM
                    ),
                }
        same_topology = rest is None or topology == rest["topology_signature"]
        rest_exact_pairs = set() if rest is None else {
            tuple(int(index) for index in pair)
            for pair in rest["exact_pair_signatures"]
        }
        rest_pelvic_pairs = set() if rest is None else {
            tuple(int(index) for index in pair)
            for pair in rest["pelvic_pair_signatures"]
        }
        new_global_signatures = (
            []
            if rest is None
            else sorted(set(exact_pair_signatures).difference(rest_exact_pairs))
        )
        new_pelvic_signatures = (
            []
            if rest is None
            else sorted(set(pelvic_pair_signatures).difference(rest_pelvic_pairs))
        )
        return {
            "finite_coordinates": finite,
            "topology_signature": topology,
            "same_topology_as_rest": same_topology,
            "topology_metrics": topology_metrics,
            "exact_intersection_report": {
                **{key: value for key, value in exact.items() if key != "pairs"},
                "genuine_pairs": genuine_pairs,
                "non_genuine_pair_details_omitted_from_evidence": True,
            },
            "pelvic_face_count": len(pelvic_faces),
            "pelvic_exact_intersection_pairs": pelvic_pairs,
            "exact_pair_signatures": exact_pair_signatures,
            "pelvic_pair_signatures": pelvic_pair_signatures,
            "new_global_exact_pair_signatures_over_rest": new_global_signatures,
            "new_pelvic_exact_pair_signatures_over_rest": new_pelvic_signatures,
            "new_global_exact_intersection_pairs_over_rest": len(new_global_signatures),
            "new_pelvic_exact_intersection_pairs_over_rest": len(new_pelvic_signatures),
            "edge_stretch": edge_stretch,
            "relationships": relationships,
            "relationship_checks": relation_checks,
            "relationship_noncollapse": collapse,
            "relationship_geometry_present": geometry_present,
            "edge_lengths": lengths,
            "pelvic_edge_indices": pelvic_edge_indices,
            "evaluated_mesh_read_only": True,
        }
    finally:
        bm.free()
        evaluated.to_mesh_clear()


def _weight_audit(body: bpy.types.Object, armature: bpy.types.Object) -> dict[str, Any]:
    deform = {bone.name for bone in armature.data.bones if bone.use_deform}
    group_by_index = {group.index: group.name for group in body.vertex_groups}
    rows: list[tuple[float, int, list[str]]] = []
    unknown_assignments: Counter[str] = Counter()
    for vertex in body.data.vertices:
        positive = [item for item in vertex.groups if float(item.weight) > 1.0e-8]
        rig_items = [item for item in positive if group_by_index.get(item.group) in deform]
        for item in positive:
            name = group_by_index.get(item.group, "")
            if name not in deform and not name.startswith(LANDMARK_GROUP_PREFIX):
                unknown_assignments[name] += 1
        rows.append(
            (
                sum(float(item.weight) for item in rig_items),
                len(rig_items),
                sorted(group_by_index.get(item.group, "") for item in rig_items),
            )
        )
    sums = [row[0] for row in rows]
    counts = [row[1] for row in rows]
    result = {
        "vertex_count": len(rows),
        "deform_bone_group_count": len(deform),
        "deform_bone_names": sorted(deform),
        "minimum_weight_sum": min(sums, default=0.0),
        "maximum_weight_sum": max(sums, default=0.0),
        "unweighted_vertex_count": sum(value <= 1.0e-8 for value in sums),
        "weight_sum_out_of_tolerance_count": sum(abs(value - 1.0) > 1.0e-4 for value in sums),
        "maximum_positive_influence_count": max(counts, default=0),
        "vertices_over_four_influences": sum(value > 4 for value in counts),
        "unknown_positive_nonlandmark_group_assignments": dict(unknown_assignments),
    }
    result["passed"] = bool(
        rows
        and result["unweighted_vertex_count"] == 0
        and result["weight_sum_out_of_tolerance_count"] == 0
        and result["maximum_positive_influence_count"] <= 4
        and not unknown_assignments
    )
    return result


def _png_record(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"path": path.relative_to(PROJECT_ROOT).as_posix(), "exists": path.is_file()}
    if not path.is_file():
        record.update({"valid_png_header": False, "sha256": None, "size_bytes": 0})
        return record
    data = path.read_bytes()[:24]
    valid = len(data) == 24 and data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR"
    width, height = struct.unpack(">II", data[16:24]) if valid else (0, 0)
    record.update(
        {
            "valid_png_header": valid,
            "width_px": width,
            "height_px": height,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    )
    return record


def _render_inventory(candidate_dir: Path) -> dict[str, Any]:
    views = {label: _png_record(candidate_dir / f"{label}.png") for label in OWNER_REVIEW_VIEW_LABELS}
    extras = sorted(
        path.name for path in candidate_dir.glob("*.png")
        if path.stem not in OWNER_REVIEW_VIEW_LABELS
    )
    passed = all(
        record["exists"] and record["valid_png_header"] and record["size_bytes"] > 0
        for record in views.values()
    )
    return {
        "exact_required_labels": list(OWNER_REVIEW_VIEW_LABELS),
        "required_view_count": len(OWNER_REVIEW_VIEW_LABELS),
        "views": views,
        "extra_png_names": extras,
        "inventory_passed": passed,
        "render_invoked_by_auditor": False,
        "visual_content_reviewed_by_auditor": False,
        "owner_visual_acceptance": False,
    }


def _metadata_audit(
    body: bpy.types.Object,
    armature: bpy.types.Object,
    candidate_id: str,
) -> dict[str, Any]:
    candidate_objects = [obj for obj in bpy.data.objects if obj.get("candidate_id") == candidate_id]
    object_flags = {
        obj.name: {
            "type": obj.type,
            "data_name": getattr(getattr(obj, "data", None), "name", None),
            "primary_surface": obj.get("primary_surface"),
            "body_class": obj.get("body_class"),
            "confirmed_adult": obj.get("confirmed_adult"),
            "material_names": [
                slot.material.name
                for slot in obj.material_slots
                if slot.material is not None
            ],
            "shape_key_names": (
                [
                    block.name
                    for block in obj.data.shape_keys.key_blocks
                ]
                if getattr(getattr(obj, "data", None), "shape_keys", None) is not None
                else []
            ),
            "private_owner_review_only": obj.get("private_owner_review_only"),
            "inactive_candidate": obj.get("inactive_candidate"),
            "runtime_activation_allowed": obj.get("runtime_activation_allowed"),
            "roster_registration_allowed": obj.get("roster_registration_allowed"),
            "publication_allowed": obj.get("publication_allowed"),
            "clothing_included": obj.get("clothing_included"),
        }
        for obj in candidate_objects
    }
    object_flags_pass = bool(candidate_objects) and all(
        record["private_owner_review_only"] is True
        and record["inactive_candidate"] is True
        and record["runtime_activation_allowed"] is False
        and record["roster_registration_allowed"] is False
        and record["publication_allowed"] is False
        and record["clothing_included"] is False
        for record in object_flags.values()
    )
    unmarked_content_objects = sorted(
        obj.name
        for obj in bpy.data.objects
        if obj.type in {"MESH", "ARMATURE", "CURVE", "SURFACE", "FONT", "META"}
        and obj.get("candidate_id") != candidate_id
    )
    scene = bpy.context.scene
    scene_flags = {
        "candidate_id": scene.get("candidate_id"),
        "candidate_status": scene.get("candidate_status"),
        "body_class": scene.get("body_class"),
        "confirmed_adult": scene.get("confirmed_adult"),
        "private_owner_review_only": scene.get("private_owner_review_only"),
        "runtime_activation_allowed": scene.get("runtime_activation_allowed"),
        "roster_registration_allowed": scene.get("roster_registration_allowed"),
        "publication_allowed": scene.get("publication_allowed"),
        "clothing_included": scene.get("clothing_included"),
    }
    scene_flags_pass = bool(
        scene_flags["candidate_id"] == candidate_id
        and scene_flags["candidate_status"] == "INACTIVE_UNASSIGNED_AWAITING_OWNER_AND_INDEPENDENT_REVIEW"
        and scene_flags["body_class"] == "adult_female"
        and scene_flags["confirmed_adult"] is True
        and scene_flags["private_owner_review_only"] is True
        and scene_flags["runtime_activation_allowed"] is False
        and scene_flags["roster_registration_allowed"] is False
        and scene_flags["publication_allowed"] is False
        and scene_flags["clothing_included"] is False
    )
    body_flags_pass = bool(
        body.get("primary_surface") is True
        and body.get("body_class") == "adult_female"
        and body.get("confirmed_adult") is True
        and body.get("generic_identity_neutral_foundation") is False
        and body.get("kira_styling_applied") is True
        and body.get("wrong_sex_helper_present") is False
        and body.get("adult_relationship_surface_method") == ADULT_SURFACE_METHOD_ID
        and body.get("adult_relationship_surface_detail_method")
        == ADULT_SURFACE_DETAIL_METHOD_ID
        and body.get("adult_female_surface_method_id") == ADULT_SURFACE_METHOD_ID
        and body.get("adult_female_surface_detail_method_id")
        == ADULT_SURFACE_DETAIL_METHOD_ID
        and body.get("adult_relationships_require_independent_requalification") is True
        and body.get("candidate_id") == candidate_id
        and armature.get("candidate_id") == candidate_id
    )
    return {
        "candidate_object_count": len(candidate_objects),
        "candidate_objects": object_flags,
        "all_candidate_object_safety_flags_passed": object_flags_pass,
        "unmarked_content_object_names": unmarked_content_objects,
        "all_content_objects_are_candidate_marked": not unmarked_content_objects,
        "scene": scene_flags,
        "scene_safety_flags_passed": scene_flags_pass,
        "primary_adult_surface_metadata_passed": body_flags_pass,
        "passed": (
            object_flags_pass
            and not unmarked_content_objects
            and scene_flags_pass
            and body_flags_pass
        ),
    }


def _build_binding_audit(
    build: Mapping[str, Any],
    *,
    candidate_id: str,
    blend_path: Path,
    blend_hash: str,
    config_report: Mapping[str, Any],
    expected_landmark_names: Sequence[str],
    optional_glb: Mapping[str, Any] | None,
) -> dict[str, Any]:
    output = build.get("outputs") if isinstance(build.get("outputs"), Mapping) else {}
    blend = output.get("blend") if isinstance(output.get("blend"), Mapping) else {}
    builder_config = build.get("builder_config") if isinstance(build.get("builder_config"), Mapping) else {}
    safety = build.get("safety") if isinstance(build.get("safety"), Mapping) else {}
    adult = build.get("adult_confirmation") if isinstance(build.get("adult_confirmation"), Mapping) else {}
    protected = (
        build.get("protected_live_kira_state")
        if isinstance(build.get("protected_live_kira_state"), Mapping)
        else {}
    )
    hash_bindings = (
        build.get("build_hash_bindings")
        if isinstance(build.get("build_hash_bindings"), Mapping)
        else {}
    )
    adult_surface = (
        build.get("adult_surface_authoring")
        if isinstance(build.get("adult_surface_authoring"), Mapping)
        else {}
    )
    structured_detail = (
        adult_surface.get("structured_detail_refinement")
        if isinstance(adult_surface.get("structured_detail_refinement"), Mapping)
        else {}
    )
    checks = {
        "candidate_id_exact": build.get("candidate_id") == candidate_id,
        "inactive_status_exact": build.get("status") == "INACTIVE_PRIVATE_CANDIDATE_AWAITING_OWNER_AND_INDEPENDENT_REVIEW",
        "blend_name_exact": blend.get("path") == blend_path.name,
        "blend_hash_exact": blend.get("sha256") == blend_hash,
        "builder_config_valid_at_build": builder_config.get("valid") is True,
        "builder_config_hash_matches_current_exact": builder_config.get("config_sha256") == config_report.get("config_sha256"),
        "retained_landmarks_exact": sorted(build.get("retained_adult_landmark_groups", [])) == sorted(expected_landmark_names),
        "adult_activation_pending_exact": adult.get("current_candidate_qualified_for_activation") is False,
        "pose_space_audit_was_pending": adult.get("pose_space_pelvic_patch_deformation_audit_status") == "NOT_PERFORMED",
        "private_safety_exact": safety.get("private_owner_review_only") is True,
        "inactive_safety_exact": safety.get("inactive") is True,
        "unassigned_safety_exact": safety.get("assigned") is False,
        "clothing_absent_exact": safety.get("clothing_included") is False,
        "publication_blocked_exact": safety.get("publication_allowed") is False,
        "runtime_activation_blocked_exact": safety.get("runtime_activation_allowed") is False,
        "build_reports_live_state_unchanged": safety.get("live_kira_state_mutated") is False,
        "protected_live_state_internal_integrity_passed": bool(
            protected.get("passed") is True
            and protected.get("before") == protected.get("after")
        ),
        "build_hashes_verified_before_output": bool(
            isinstance(hash_bindings.get("verified_before_output_creation"), Mapping)
            and hash_bindings["verified_before_output_creation"].get("passed") is True
        ),
        "build_hashes_verified_at_commit": bool(
            isinstance(hash_bindings.get("verified_at_evidence_commit"), Mapping)
            and hash_bindings["verified_at_evidence_commit"].get("passed") is True
        ),
        "v1_base_authoring_report_exact": bool(
            adult_surface.get("method_id") == ADULT_SURFACE_METHOD_ID
        ),
        "v2_structured_detail_report_exact": bool(
            structured_detail.get("base_method_id") == ADULT_SURFACE_METHOD_ID
            and structured_detail.get("detail_method_id")
            == ADULT_SURFACE_DETAIL_METHOD_ID
        ),
        "v2_structured_detail_preserved_topology_and_rig": bool(
            structured_detail.get("new_global_nonadjacent_self_intersection_pairs")
            == 0
            and structured_detail.get("topology_changed") is False
            and structured_detail.get("rig_weights_changed") is False
            and structured_detail.get("landmark_group_names_changed") is False
            and structured_detail.get(
                "posterior_landmark_memberships_rebound_to_curved_frame"
            )
            is True
            and structured_detail.get("separate_anatomy_mesh_created") is False
            and structured_detail.get("boolean_anatomy_union_used") is False
            and structured_detail.get("copied_anatomy_geometry_used") is False
        ),
    }
    glb_record = output.get("private_glb") if isinstance(output.get("private_glb"), Mapping) else {}
    if optional_glb is not None:
        checks.update(
            {
                "optional_glb_was_exported": glb_record.get("exported") is True,
                "optional_glb_name_exact": glb_record.get("path") == Path(optional_glb["path"]).name,
                "optional_glb_hash_exact": glb_record.get("sha256") == optional_glb["sha256"],
                "optional_glb_still_unvalidated": glb_record.get("validation_status") == "UNVALIDATED_PENDING_FRESH_IMPORT",
                "optional_glb_runtime_survival_not_preclaimed": glb_record.get("hair_curve_and_morph_runtime_survival_proven") is False,
            }
        )
    return {"checks": checks, "passed": all(checks.values())}


def _audit_loaded_candidate(preflight: Mapping[str, Any]) -> dict[str, Any]:
    resolved = preflight["resolved"]
    candidate_id = str(resolved["candidate_id"])
    blend_path = PROJECT_ROOT / resolved["blend"]["path"]
    build_path = PROJECT_ROOT / resolved["build_evidence"]["path"]
    build = _read_json(build_path)
    config, config_report = load_validated_profiled_candidate_builder_config(PROJECT_ROOT)
    target_height = float(config["style_profile"]["required_target_height_m"])
    frame, scaled_parameters = scaled_adult_surface_settings(
        config["adult_surface_authoring"], target_height
    )
    expected_groups = {**LANDMARK_GROUPS, **SUBGROUPS}
    expected_group_names = sorted(expected_groups.values())

    loaded = Path(bpy.data.filepath).resolve(strict=True)
    if loaded != blend_path.resolve(strict=True):
        raise ProfiledKiraPostbuildAuditError("Blender loaded filepath differs from exact bound input")
    primary = [
        obj for obj in bpy.data.objects
        if obj.type == "MESH" and obj.get("primary_surface") is True
    ]
    if len(primary) != 1:
        raise ProfiledKiraPostbuildAuditError(
            f"expected exactly one marked primary adult surface, found {len(primary)}"
        )
    body = primary[0]
    armatures = [
        obj for obj in bpy.data.objects
        if obj.type == "ARMATURE" and obj.get("candidate_id") == candidate_id
    ]
    if len(armatures) != 1:
        raise ProfiledKiraPostbuildAuditError(
            f"expected exactly one candidate armature, found {len(armatures)}"
        )
    armature = armatures[0]
    modifiers = [modifier for modifier in body.modifiers if modifier.type == "ARMATURE"]
    rig_binding = {
        "candidate_armature_name": armature.name,
        "expected_armature_name": f"{candidate_id}_official_rig",
        "armature_modifier_count": len(modifiers),
        "armature_modifier_names": [modifier.name for modifier in modifiers],
        "all_armature_modifiers_target_intended_armature": bool(modifiers) and all(
            modifier.object == armature and modifier.use_vertex_groups for modifier in modifiers
        ),
    }
    rig_binding["passed"] = bool(
        armature.name == rig_binding["expected_armature_name"]
        and len(modifiers) == 1
        and rig_binding["all_armature_modifiers_target_intended_armature"]
    )
    actual_group_names = sorted(
        group.name for group in body.vertex_groups
        if group.name.startswith(LANDMARK_GROUP_PREFIX)
    )
    landmark_binding = {
        "expected_exact_group_names": expected_group_names,
        "actual_group_names": actual_group_names,
        "exact_set_passed": actual_group_names == expected_group_names,
        "body_declared_group_count": body.get("adult_relationship_landmark_group_count"),
        "method_id": body.get("adult_relationship_surface_method"),
        "detail_method_id": body.get("adult_relationship_surface_detail_method"),
        "source_base_method_id": body.get("adult_female_surface_method_id"),
        "source_detail_method_id": body.get("adult_female_surface_detail_method_id"),
        "configured_detail_method_id": config["adult_surface_authoring"][
            "structured_detail_refinement"
        ]["method_id"],
    }
    landmark_binding["passed"] = bool(
        landmark_binding["exact_set_passed"]
        and landmark_binding["body_declared_group_count"] == len(expected_group_names)
        and landmark_binding["method_id"] == ADULT_SURFACE_METHOD_ID
        and landmark_binding["detail_method_id"] == ADULT_SURFACE_DETAIL_METHOD_ID
        and landmark_binding["source_base_method_id"] == ADULT_SURFACE_METHOD_ID
        and landmark_binding["source_detail_method_id"]
        == ADULT_SURFACE_DETAIL_METHOD_ID
        and landmark_binding["configured_detail_method_id"]
        == ADULT_SURFACE_DETAIL_METHOD_ID
    )
    members = {name: _group_members(body, group_name) for name, group_name in expected_groups.items()}
    pelvic_vertices = set().union(*members.values())
    weights = _weight_audit(body, armature)
    metadata = _metadata_audit(body, armature, candidate_id)
    binding = _build_binding_audit(
        build,
        candidate_id=candidate_id,
        blend_path=blend_path,
        blend_hash=resolved["blend"]["sha256"],
        config_report=config_report,
        expected_landmark_names=expected_group_names,
        optional_glb=resolved.get("optional_private_glb"),
    )

    setters = _pose_setters(armature)
    if tuple(setters) != POSE_NAMES:
        raise ProfiledKiraPostbuildAuditError("internal pose set drifted")
    poses: dict[str, Any] = {}
    rest_internal: dict[str, Any] | None = None
    for name in POSE_NAMES:
        setters[name]()
        record = _pose_mesh_record(
            body,
            frame=frame,
            group_members=members,
            minimum_vertices=int(scaled_parameters["minimum_landmark_vertices"]),
            pelvic_vertices=pelvic_vertices,
            rest=rest_internal,
        )
        record["pose_bone_deltas"] = _pose_bone_deltas(armature)
        if name == "rest":
            rest_internal = record
        poses[name] = record
    _reset_pose(armature)

    rest = poses["rest"]
    rest_topology = rest["topology_metrics"]
    rest_passed = bool(
        rest["finite_coordinates"]
        and rest["same_topology_as_rest"]
        and rest_topology["surface_component_count"] == 1
        and rest_topology["boundary_edge_count"] == 0
        and rest_topology["nonmanifold_edge_count"] == 0
        and rest_topology["degenerate_face_count"] == 0
        and rest_topology["coincident_duplicate_triangle_pair_count"] == 0
        and rest_topology["exact_nonadjacent_intersection_pair_count"] == 0
        and rest_topology["pelvic_patch_exact_intersection_pair_count"] == 0
        and rest["edge_stretch"]["global"]["passed"]
        and rest["edge_stretch"]["pelvic_patch"]["passed"]
        and rest["relationship_geometry_present"]
        and rest["relationship_checks"]["ordering_passed"]
        and rest["relationship_checks"]["relief_passed"]
    )
    pose_gate_records: dict[str, Any] = {}
    for name in POSE_NAMES[1:]:
        record = poses[name]
        pose_gate_records[name] = {
            "finite_coordinates": record["finite_coordinates"],
            "same_topology_as_rest": record["same_topology_as_rest"],
            "zero_degenerate_faces": record["topology_metrics"]["degenerate_face_count"] == 0,
            "zero_coincident_duplicate_triangles": record["topology_metrics"]["coincident_duplicate_triangle_pair_count"] == 0,
            "global_edge_stretch_passed": record["edge_stretch"]["global"]["passed"],
            "pelvic_edge_stretch_passed": record["edge_stretch"]["pelvic_patch"]["passed"],
            "relationship_geometry_present": record["relationship_geometry_present"],
            "all_relationship_regions_noncollapsed": all(
                row["passed"] for row in record["relationship_noncollapse"].values()
            ),
            "ordering_preserved": record["relationship_checks"]["ordering_passed"],
            "relief_preserved": record["relationship_checks"]["relief_passed"],
            "zero_new_pelvic_patch_exact_intersections_over_rest": record["new_pelvic_exact_intersection_pairs_over_rest"] == 0,
            "new_global_exact_intersections_within_bound": record["new_global_exact_intersection_pairs_over_rest"] <= MAX_NEW_GLOBAL_EXACT_INTERSECTIONS,
        }
        pose_gate_records[name]["passed"] = all(pose_gate_records[name].values())
    pose_passed = all(record["passed"] for record in pose_gate_records.values())
    pose_intent = _pose_intent_gates(poses)
    render_inventory = _render_inventory(blend_path.parent)
    gates = {
        "build_evidence_and_exact_config_binding": binding["passed"],
        "exactly_one_marked_primary_adult_surface": len(primary) == 1,
        "intended_armature_and_modifier": rig_binding["passed"],
        "normalized_maximum_four_rig_weights": weights["passed"],
        "adult_landmark_set_and_method_exact": landmark_binding["passed"],
        "inactive_private_safety_metadata": metadata["passed"],
        "rest_topology_and_relationships": rest_passed,
        "all_six_deformation_pose_gates": pose_passed,
        "all_pose_intents_measured_and_bounded": pose_intent["passed"],
        "required_owner_review_view_inventory": render_inventory["inventory_passed"],
    }
    implementation_paths = [
        Path("tools/blender_audit_profiled_kira_adult_candidate.py"),
        Path("tools/blender_exact_mesh_intersections.py"),
        Path("tools/blender_audit_inactive_adult_female_foundation.py"),
        Path("tools/blender_build_profiled_kira_adult_candidate.py"),
        Path("tools/blender_author_adult_female_external_surface_v2.py"),
        Path("Core/avatar_adult_female_surface_authoring.py"),
        Path("Core/avatar_adult_female_surface_authoring_v2.py"),
        Path("Core/avatar_profiled_adult_candidate_contract.py"),
        Path("Core/avatar_profiled_kira_candidate_audit_contract.py"),
        BUILDER_CONFIG_PATH,
    ]
    return {
        "candidate_id": candidate_id,
        "build_evidence_binding": binding,
        "qualified_scaled_adult_frame": frame,
        "scaled_adult_parameters": scaled_parameters,
        "landmark_binding": landmark_binding,
        "rig_binding": rig_binding,
        "weight_audit": weights,
        "safety_metadata": metadata,
        "poses": {
            name: {
                key: value
                for key, value in record.items()
                if key not in {"edge_lengths", "pelvic_edge_indices"}
            }
            for name, record in poses.items()
        },
        "rest_gate_passed": rest_passed,
        "pose_gate_summary": pose_gate_records,
        "pose_intent_gates": pose_intent,
        "all_pose_gates_passed": pose_passed,
        "owner_review_view_inventory": render_inventory,
        "gates": gates,
        "passed": all(gates.values()),
        "implementation_hashes": {
            path.as_posix(): sha256_file(PROJECT_ROOT / path) for path in implementation_paths
        },
        "action_inventory": [
            {
                "name": action.name,
                "frame_range": [
                    float(action.frame_range[0]),
                    float(action.frame_range[1]),
                ],
                "fake_user": bool(action.use_fake_user),
            }
            for action in sorted(bpy.data.actions, key=lambda item: item.name)
        ],
    }


def _write_evidence(output_dir: Path, evidence: Mapping[str, Any]) -> Path:
    if output_dir.exists():
        raise ProfiledKiraPostbuildAuditError("append-only audit output appeared before commit")
    output_dir.mkdir(parents=True, exist_ok=False)
    path = output_dir / MAIN_EVIDENCE_NAME
    if path.exists():
        raise ProfiledKiraPostbuildAuditError("refusing to overwrite main audit evidence")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(_json_safe(evidence), stream, indent=2, sort_keys=True)
        stream.write("\n")
    return path


def run(args: argparse.Namespace) -> tuple[dict[str, Any], Path | None]:
    preflight = evaluate_postbuild_audit_preflight(
        PROJECT_ROOT,
        blend_path=args.blend,
        blend_sha256=args.blend_sha256,
        build_evidence_sha256=args.build_evidence_sha256,
        output_dir=args.output_dir,
        optional_glb_path=args.optional_private_glb,
        optional_glb_sha256=args.optional_private_glb_sha256,
    )
    if preflight["ready"] is not True:
        return {
            "schema_version": 1,
            "audit": AUDITOR_ID,
            "status": "BLOCKED_BEFORE_BLENDER_OPEN_NO_EVIDENCE_WRITTEN",
            "preflight": preflight,
        }, None
    resolved = preflight["resolved"]
    output_dir = PROJECT_ROOT / resolved["output_directory"]
    factory = _factory_startup_fingerprint()
    bindings = {
        key: value
        for key, value in resolved.items()
        if key in {"blend", "build_evidence", "optional_private_glb"}
    }
    input_before = {
        key: _stat_record(PROJECT_ROOT / record["path"])
        for key, record in bindings.items()
    }
    before_matches_preflight = all(
        input_before[key]["sha256"] == bindings[key]["sha256"]
        for key in bindings
    )
    result: dict[str, Any] | None = None
    fatal: dict[str, Any] | None = None
    if factory["passed"] and before_matches_preflight:
        try:
            bpy.ops.wm.open_mainfile(
                filepath=str(PROJECT_ROOT / resolved["blend"]["path"]),
                load_ui=False,
                use_scripts=False,
            )
            result = _audit_loaded_candidate(preflight)
        except Exception as exc:
            fatal = {
                "error_type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
        finally:
            for armature in [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]:
                try:
                    _reset_pose(armature)
                except Exception:
                    pass
    elif not factory["passed"]:
        fatal = {
            "error_type": "UnsafeStartupFingerprint",
            "message": "fresh background factory-startup fingerprint did not pass",
        }
    else:
        fatal = {
            "error_type": "InputChangedAfterPreflight",
            "message": "an exact input changed between preflight and Blender open",
        }
    unchanged = verify_inputs_unchanged(PROJECT_ROOT, bindings)
    passed = bool(result and result["passed"] and fatal is None and unchanged["passed"])
    evidence = {
        "schema_version": 1,
        "audit": AUDITOR_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "PASSED_POSTBUILD_ENGINEERING_AUDIT_REMAINS_INACTIVE_OWNER_REVIEW_ONLY"
            if passed
            else "BLOCKED_POSTBUILD_ENGINEERING_AUDIT_REMAINS_INACTIVE"
        ),
        "passed": passed,
        "preflight": preflight,
        "factory_startup_fingerprint": factory,
        "input_files_before": input_before,
        "input_files_still_matched_preflight_before_open": before_matches_preflight,
        "input_integrity_after": unchanged,
        "audit_result": result,
        "fatal_error": fatal,
        "truth_boundaries": {
            "candidate_file_modified": False,
            "render_performed": False,
            "blend_saved": False,
            "export_performed": False,
            "activation_performed": False,
            "clothing_added": False,
            "publication_or_upload_performed": False,
            "postbuild_engineering_gates_passed": bool(result and result["passed"]),
            "owner_visual_acceptance": False,
            "runtime_qualified": False,
            "activation_allowed": False,
            "private_glb_runtime_survival_proven": False,
            "optional_glb_requires_separate_clean_process_import": "optional_private_glb" in bindings,
        },
    }
    path = _write_evidence(output_dir, evidence)
    return evidence, path


def main() -> int:
    evidence, path = run(_arguments())
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "passed": evidence.get("passed", False),
                "evidence_path": _relative(path) if path is not None else None,
                "evidence_sha256": sha256_file(path) if path is not None else None,
                "runtime_qualified": False,
                "activation_allowed": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if evidence.get("passed") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
