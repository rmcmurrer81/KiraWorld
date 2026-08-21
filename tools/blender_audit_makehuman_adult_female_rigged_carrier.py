#!/usr/bin/env python3
"""Read-only pose-space audit for one inactive MakeHuman carrier.

The worker requires the same exact one-run authorization as the builder and
only runs in background Blender with factory startup and automatic script
execution disabled.  It opens the fresh carrier without executing embedded
scripts, evaluates the configured bounded poses in memory, restores the rest
pose, and never saves, renders, exports, assigns an identity, or activates a
runtime candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
from typing import Any, Iterable, Mapping, Sequence

import bmesh
import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_makehuman_rigged_carrier import (  # noqa: E402
    EXPECTED_PELVIC_GROUPS,
    EXPECTED_POSE_IDS,
    REQUIRED_BLENDER_FLAGS,
    RiggedCarrierError,
    canonical_sha256,
    evaluate_pose_gate,
    native_filesystem_path,
    project_path,
    read_json,
    same_filesystem_path,
    sha256_file,
    validate_one_run_authorization,
)
from tools.blender_exact_mesh_intersections import (  # noqa: E402
    exact_nonadjacent_intersection_report,
)


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--authorization", required=True)
    return parser.parse_args(values)


def _project_argument(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def require_safe_blender_invocation() -> Path:
    if not bpy.app.background:
        raise RiggedCarrierError("carrier audit requires Blender background mode")
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    blender_arguments = sys.argv[:separator]
    for flag in REQUIRED_BLENDER_FLAGS:
        if blender_arguments.count(flag) != 1:
            raise RiggedCarrierError(f"carrier audit requires Blender flag {flag}")
    autoexec = getattr(bpy.context.preferences.filepaths, "use_scripts_auto_execute", None)
    if autoexec is not False:
        raise RiggedCarrierError("automatic script execution must be disabled")
    executable = Path(sys.executable).resolve(strict=True)
    if executable.name.lower() not in {"blender", "blender.exe"}:
        raise RiggedCarrierError("worker executable is not Blender")
    return executable


def _matrix_values(matrix: Any) -> list[float]:
    values = [float(matrix[row][column]) for row in range(4) for column in range(4)]
    if not all(math.isfinite(value) for value in values):
        raise RiggedCarrierError("matrix contains non-finite value")
    return values


def _mesh_geometry_digest(body: bpy.types.Object) -> str:
    mesh = body.data
    digest = hashlib.sha256()
    digest.update(struct.pack("<QQ", len(mesh.vertices), len(mesh.polygons)))
    for vertex in mesh.vertices:
        digest.update(struct.pack("<I3d", int(vertex.index), *(float(v) for v in vertex.co)))
    for polygon in mesh.polygons:
        indices = tuple(int(value) for value in polygon.vertices)
        digest.update(struct.pack("<II", int(polygon.index), len(indices)))
        digest.update(struct.pack(f"<{len(indices)}I", *indices))
    return digest.hexdigest()


def _weight_digest(body: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    groups = list(body.vertex_groups)
    digest.update(struct.pack("<I", len(groups)))
    for group in groups:
        encoded = group.name.encode("utf-8")
        digest.update(struct.pack("<II", int(group.index), len(encoded)))
        digest.update(encoded)
    assignment_count = 0
    for vertex in body.data.vertices:
        assignments = sorted(
            (int(item.group), float(item.weight))
            for item in vertex.groups
            if float(item.weight) > 0.0
        )
        digest.update(struct.pack("<II", int(vertex.index), len(assignments)))
        for group_index, weight in assignments:
            digest.update(struct.pack("<Id", group_index, weight))
            assignment_count += 1
    digest.update(struct.pack("<Q", assignment_count))
    return digest.hexdigest()


def _armature_digest(armature: bpy.types.Object) -> str:
    records = []
    for bone in armature.data.bones:
        records.append(
            {
                "name": bone.name,
                "parent": bone.parent.name if bone.parent else None,
                "use_deform": bool(bone.use_deform),
                "matrix_local": _matrix_values(bone.matrix_local),
            }
        )
    return canonical_sha256(records)


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    try:
        with native_filesystem_path(path).open(
            "x", encoding="utf-8", newline="\n"
        ) as stream:
            stream.write(text)
    except FileExistsError as exc:
        raise RiggedCarrierError(f"refusing to overwrite audit report: {path}") from exc


def _receipt_matches(report: Mapping[str, Any], field: str) -> bool:
    receipt = report.get(field)
    if not isinstance(receipt, str):
        return False
    unsigned = dict(report)
    del unsigned[field]
    return canonical_sha256(unsigned) == receipt


def _require_candidate_scene(
    config: Mapping[str, Any],
    build_report: Mapping[str, Any],
) -> tuple[bpy.types.Object, bpy.types.Object]:
    objects = list(bpy.data.objects)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    armatures = [obj for obj in objects if obj.type == "ARMATURE"]
    if len(objects) != 2 or len(meshes) != 1 or len(armatures) != 1:
        raise RiggedCarrierError("candidate must contain only one body and one armature")
    body = meshes[0]
    armature = armatures[0]
    candidate = config["candidate"]
    source = config["source"]
    if body.name != source["primary_object_id"]:
        raise RiggedCarrierError("candidate body object ID differs")
    if armature.name != candidate["armature_id"]:
        raise RiggedCarrierError("candidate armature object ID differs")
    if body.get("primary_surface") is not True:
        raise RiggedCarrierError("candidate body is not the qualified primary surface")
    for datablock in (body, armature):
        if datablock.get("inactive_rigged_carrier_candidate") is not True:
            raise RiggedCarrierError("inactive carrier marker differs")
        if datablock.get("carrier_candidate_id") != candidate["candidate_id"]:
            raise RiggedCarrierError("carrier candidate ID differs")
        if datablock.get("source_foundation_sha256") != source["sha256"]:
            raise RiggedCarrierError("carrier source binding differs")
        if datablock.get("runtime_activation_allowed") is not False:
            raise RiggedCarrierError("runtime activation boundary differs")
        if datablock.get("public_export_allowed") is not False:
            raise RiggedCarrierError("public export boundary differs")
    if body.get("generic_identity_neutral") is not True or body.get("bald") is not True:
        raise RiggedCarrierError("generic bald carrier boundary differs")
    for key in ("contains_hair", "contains_clothing", "contains_internal_anatomy"):
        if body.get(key) is not False or bpy.context.scene.get(key) is not False:
            raise RiggedCarrierError(f"separation marker differs: {key}")
    if bpy.context.scene.get("inactive_rigged_carrier_candidate") is not True:
        raise RiggedCarrierError("scene inactive-carrier marker differs")
    if bpy.context.scene.get("runtime_activation_allowed") is not False:
        raise RiggedCarrierError("scene runtime boundary differs")
    if bpy.context.scene.get("public_export_allowed") is not False:
        raise RiggedCarrierError("scene public boundary differs")
    if body.data.shape_keys is not None:
        raise RiggedCarrierError("candidate unexpectedly contains shape keys")
    if body.data.uv_layers or body.data.materials or body.material_slots:
        raise RiggedCarrierError("candidate unexpectedly contains appearance data")
    if bpy.data.materials or bpy.data.images or bpy.data.actions or bpy.data.libraries:
        raise RiggedCarrierError("candidate unexpectedly contains linked or appearance/action data")
    for obj in objects:
        animation = obj.animation_data
        if animation is not None and (
            animation.action is not None or len(animation.nla_tracks) != 0
        ):
            raise RiggedCarrierError("candidate unexpectedly contains animation data")
    modifiers = [modifier for modifier in body.modifiers if modifier.type == "ARMATURE"]
    if len(body.modifiers) != 1 or len(modifiers) != 1 or modifiers[0].object != armature:
        raise RiggedCarrierError("candidate armature modifier binding differs")
    if body.parent != armature:
        raise RiggedCarrierError("candidate body parent binding differs")

    body_record = build_report.get("body")
    armature_record = build_report.get("armature")
    if not isinstance(body_record, Mapping) or not isinstance(armature_record, Mapping):
        raise RiggedCarrierError("build report body or armature record is absent")
    if _mesh_geometry_digest(body) != body_record.get("geometry_sha256_after"):
        raise RiggedCarrierError("saved candidate geometry differs from build report")
    if _weight_digest(body) != body_record.get("weight_sha256_after"):
        raise RiggedCarrierError("saved candidate weights differ from build report")
    if _armature_digest(armature) != armature_record.get("rest_sha256"):
        raise RiggedCarrierError("saved armature rest definition differs from build report")
    if len(body.data.vertices) != int(source["expected_vertex_count"]):
        raise RiggedCarrierError("saved carrier vertex count differs")
    if len(body.data.polygons) != int(source["expected_face_count"]):
        raise RiggedCarrierError("saved carrier face count differs")
    if len(armature.data.bones) != int(config["skeleton"]["expected_bone_count"]):
        raise RiggedCarrierError("saved carrier bone count differs")
    return body, armature


def _group_members(body: bpy.types.Object, group_names: Sequence[str]) -> dict[str, set[int]]:
    result: dict[str, set[int]] = {}
    for name in group_names:
        group = body.vertex_groups.get(name)
        if group is None:
            raise RiggedCarrierError(f"required pelvic group is absent: {name}")
        members = {
            int(vertex.index)
            for vertex in body.data.vertices
            if any(
                item.group == group.index and float(item.weight) >= 0.5
                for item in vertex.groups
            )
        }
        if not members:
            raise RiggedCarrierError(f"required pelvic group is empty: {name}")
        result[name] = members
    return result


def _evaluated_mesh(body: bpy.types.Object) -> tuple[Any, Any]:
    dependency_graph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(dependency_graph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=dependency_graph)
    if mesh is None:
        raise RiggedCarrierError("Blender did not provide an evaluated carrier mesh")
    return evaluated, mesh


def _finite_points(mesh: Any) -> list[Vector]:
    points = [vertex.co.copy() for vertex in mesh.vertices]
    if not points or any(
        not all(math.isfinite(float(component)) for component in point)
        for point in points
    ):
        raise RiggedCarrierError("evaluated carrier contains empty or non-finite geometry")
    return points


def _triangles(mesh: Any) -> list[tuple[int, int, int]]:
    mesh.calc_loop_triangles()
    return [tuple(int(value) for value in triangle.vertices) for triangle in mesh.loop_triangles]


def _pelvic_topology(
    mesh: Any,
    members: set[int],
) -> tuple[list[tuple[int, int]], list[tuple[int, int, int]]]:
    edges = [
        tuple(int(value) for value in edge.vertices)
        for edge in mesh.edges
        if all(int(value) in members for value in edge.vertices)
    ]
    triangles = [
        triangle
        for triangle in _triangles(mesh)
        if all(index in members for index in triangle)
    ]
    if not edges or not triangles:
        raise RiggedCarrierError("pelvic landmark union has no internal edges or triangles")
    return edges, triangles


def _length(first: Vector, second: Vector) -> float:
    return float((second - first).length)


def _area(first: Vector, second: Vector, third: Vector) -> float:
    return float((second - first).cross(third - first).length * 0.5)


def _positive_baselines(
    points: Sequence[Vector],
    edges: Iterable[tuple[int, int]],
    triangles: Iterable[tuple[int, int, int]],
    *,
    label: str,
) -> tuple[list[float], list[float]]:
    edge_lengths = [_length(points[first], points[second]) for first, second in edges]
    triangle_areas = [
        _area(points[first], points[second], points[third])
        for first, second, third in triangles
    ]
    if not edge_lengths or min(edge_lengths) <= 1.0e-12:
        raise RiggedCarrierError(f"{label} rest mesh contains a degenerate edge")
    if not triangle_areas or min(triangle_areas) <= 1.0e-14:
        raise RiggedCarrierError(f"{label} rest mesh contains a degenerate triangle")
    return edge_lengths, triangle_areas


def _signed_volume(
    points: Sequence[Vector],
    triangles: Iterable[tuple[int, int, int]],
) -> float:
    return float(
        sum(
            points[first].dot(points[second].cross(points[third])) / 6.0
            for first, second, third in triangles
        )
    )


def _root_rotation_correction(armature: bpy.types.Object) -> Any:
    root = armature.pose.bones.get("root")
    if root is None:
        raise RiggedCarrierError("candidate has no root pose bone")
    relative = root.matrix.to_3x3() @ root.bone.matrix_local.to_3x3().inverted()
    if abs(float(relative.determinant())) <= 1.0e-10:
        raise RiggedCarrierError("root pose rotation is singular")
    return relative.inverted()


def _orientation_metrics(
    rest_points: Sequence[Vector],
    posed_points: Sequence[Vector],
    triangles: Sequence[tuple[int, int, int]],
    root_correction: Any,
) -> tuple[int, float]:
    reversal_count = 0
    minimum_alignment = 1.0
    for first, second, third in triangles:
        rest_normal = (rest_points[second] - rest_points[first]).cross(
            rest_points[third] - rest_points[first]
        )
        posed_normal = (posed_points[second] - posed_points[first]).cross(
            posed_points[third] - posed_points[first]
        )
        if rest_normal.length <= 1.0e-14 or posed_normal.length <= 1.0e-14:
            reversal_count += 1
            minimum_alignment = min(minimum_alignment, -1.0)
            continue
        corrected = root_correction @ posed_normal.normalized()
        alignment = float(rest_normal.normalized().dot(corrected.normalized()))
        minimum_alignment = min(minimum_alignment, alignment)
        if alignment <= 0.0:
            reversal_count += 1
    return reversal_count, minimum_alignment


def _bone_group_members(body: bpy.types.Object, name: str) -> set[int]:
    group = body.vertex_groups.get(name)
    if group is None:
        raise RiggedCarrierError(f"pose bone has no matching weight group: {name}")
    members = {
        int(vertex.index)
        for vertex in body.data.vertices
        if any(
            item.group == group.index and float(item.weight) > 1.0e-8
            for item in vertex.groups
        )
    }
    if not members:
        raise RiggedCarrierError(f"pose bone weight group is empty: {name}")
    return members


def _reset_pose(armature: bpy.types.Object) -> None:
    for bone in armature.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.location = (0.0, 0.0, 0.0)
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()


def _apply_pose(armature: bpy.types.Object, pose: Mapping[str, Any]) -> None:
    _reset_pose(armature)
    rotations = pose.get("rotations_degrees_xyz")
    if not isinstance(rotations, Mapping):
        raise RiggedCarrierError("pose rotations are malformed")
    for bone_name, vector in rotations.items():
        bone = armature.pose.bones.get(str(bone_name))
        if bone is None:
            raise RiggedCarrierError(f"pose references absent bone: {bone_name}")
        if not isinstance(vector, list) or len(vector) != 3:
            raise RiggedCarrierError(f"pose rotation is malformed: {bone_name}")
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = tuple(math.radians(float(value)) for value in vector)
    bpy.context.view_layer.update()


def _pose_record(
    body: bpy.types.Object,
    armature: bpy.types.Object,
    pose: Mapping[str, Any],
    rest_points: Sequence[Vector],
    global_edges: Sequence[tuple[int, int]],
    global_triangles: Sequence[tuple[int, int, int]],
    global_rest_edge_lengths: Sequence[float],
    global_rest_triangle_areas: Sequence[float],
    rest_signed_volume: float,
    pelvic_edges: Sequence[tuple[int, int]],
    pelvic_triangles: Sequence[tuple[int, int, int]],
    pelvic_rest_edge_lengths: Sequence[float],
    pelvic_rest_triangle_areas: Sequence[float],
    thresholds: Mapping[str, Any],
) -> dict[str, Any]:
    _apply_pose(armature, pose)
    requested_rotations = dict(pose["rotations_degrees_xyz"])
    applied_rotations: dict[str, dict[str, Any]] = {}
    for bone_name, expected in requested_rotations.items():
        bone = armature.pose.bones.get(str(bone_name))
        if bone is None:
            raise RiggedCarrierError(f"pose references absent bone: {bone_name}")
        actual = [math.degrees(float(value)) for value in bone.rotation_euler]
        maximum_error = max(
            abs(actual[index] - float(expected[index])) for index in range(3)
        )
        applied_rotations[str(bone_name)] = {
            "expected_degrees_xyz": list(expected),
            "actual_degrees_xyz": actual,
            "maximum_absolute_error_degrees": maximum_error,
            "matrix_sha256": canonical_sha256(_matrix_values(bone.matrix)),
        }
    rotation_application_passed = all(
        record["maximum_absolute_error_degrees"] <= 1.0e-6
        for record in applied_rotations.values()
    )
    root_correction = _root_rotation_correction(armature)
    evaluated, mesh = _evaluated_mesh(body)
    try:
        points = _finite_points(mesh)
        if len(points) != len(body.data.vertices):
            raise RiggedCarrierError("pose evaluation changed carrier vertex count")
        if len(mesh.polygons) != len(body.data.polygons):
            raise RiggedCarrierError("pose evaluation changed carrier face count")
        if [tuple(int(value) for value in edge.vertices) for edge in mesh.edges] != list(
            global_edges
        ):
            raise RiggedCarrierError("pose evaluation changed carrier edge topology")
        if _triangles(mesh) != list(global_triangles):
            raise RiggedCarrierError("pose evaluation changed carrier triangle topology")
        displacements = [
            float((points[index] - rest_points[index]).length)
            for index in range(len(points))
        ]
        movement_epsilon = float(thresholds["movement_epsilon_m"])
        moved_vertex_count = sum(value > movement_epsilon for value in displacements)
        maximum_displacement = max(displacements, default=0.0)
        rotated_bone_response: dict[str, dict[str, Any]] = {}
        for bone_name in requested_rotations:
            members = _bone_group_members(body, str(bone_name))
            maximum_group_displacement = max(displacements[index] for index in members)
            rotated_bone_response[str(bone_name)] = {
                "weighted_vertex_count": len(members),
                "maximum_weighted_vertex_displacement_m": maximum_group_displacement,
                "responded": maximum_group_displacement >= float(
                    thresholds["minimum_rotated_bone_group_maximum_displacement_m"]
                ),
            }

        global_edge_ratios = [
            _length(points[first], points[second]) / baseline
            for (first, second), baseline in zip(
                global_edges, global_rest_edge_lengths
            )
        ]
        global_area_ratios = [
            _area(points[first], points[second], points[third]) / baseline
            for (first, second, third), baseline in zip(
                global_triangles, global_rest_triangle_areas
            )
        ]
        if not global_edge_ratios or not global_area_ratios or not all(
            math.isfinite(value)
            for value in global_edge_ratios + global_area_ratios
        ):
            raise RiggedCarrierError("global pose ratios are empty or non-finite")
        reversal_count, minimum_normal_alignment = _orientation_metrics(
            rest_points,
            points,
            global_triangles,
            root_correction,
        )
        posed_signed_volume = _signed_volume(points, global_triangles)
        signed_volume_ratio = posed_signed_volume / rest_signed_volume

        pelvic_edge_ratios = [
            _length(points[first], points[second]) / baseline
            for (first, second), baseline in zip(
                pelvic_edges, pelvic_rest_edge_lengths
            )
        ]
        pelvic_area_ratios = [
            _area(points[first], points[second], points[third]) / baseline
            for (first, second, third), baseline in zip(
                pelvic_triangles, pelvic_rest_triangle_areas
            )
        ]
        if not pelvic_edge_ratios or not pelvic_area_ratios or not all(
            math.isfinite(value)
            for value in pelvic_edge_ratios + pelvic_area_ratios
        ):
            raise RiggedCarrierError("pelvic pose ratios are empty or non-finite")
        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)
            exact = exact_nonadjacent_intersection_report(
                bm,
                include_pair_details=False,
            )
        finally:
            bm.free()
        intersections = int(exact["exact_genuine_penetration_pair_count"])
        gates = evaluate_pose_gate(
            str(pose["pose_id"]),
            {
                "exact_intersection_pairs": intersections,
                "pelvic_minimum_edge_ratio": min(pelvic_edge_ratios),
                "pelvic_maximum_edge_ratio": max(pelvic_edge_ratios),
                "pelvic_minimum_triangle_area_ratio": min(pelvic_area_ratios),
                "global_minimum_edge_ratio": min(global_edge_ratios),
                "global_maximum_edge_ratio": max(global_edge_ratios),
                "global_minimum_triangle_area_ratio": min(global_area_ratios),
                "global_maximum_triangle_area_ratio": max(global_area_ratios),
                "orientation_reversal_triangle_count": reversal_count,
                "signed_volume_ratio": signed_volume_ratio,
                "rotation_application_passed": rotation_application_passed,
                "requested_rotation_count": len(requested_rotations),
                "moved_vertex_count": moved_vertex_count,
                "maximum_displacement_m": maximum_displacement,
                "rotated_bone_group_response_passed": all(
                    record["responded"] is True
                    for record in rotated_bone_response.values()
                ),
            },
            thresholds,
        )
        movement_passed = gates["movement"]
        global_deformation_passed = gates["global_deformation"]
        passed = gates["passed"]
        return {
            "pose_id": pose["pose_id"],
            "rotations_degrees_xyz": dict(pose["rotations_degrees_xyz"]),
            "evaluated_vertex_count": len(points),
            "evaluated_face_count": len(mesh.polygons),
            "applied_rotations": applied_rotations,
            "rotation_application_passed": rotation_application_passed,
            "gates": gates,
            "movement": {
                "epsilon_m": movement_epsilon,
                "moved_vertex_count": moved_vertex_count,
                "maximum_displacement_m": maximum_displacement,
                "rotated_bone_weighted_region_response": rotated_bone_response,
                "passed": movement_passed,
            },
            "exact_nonadjacent_self_intersection_pairs": intersections,
            "exact_intersection_summary": {
                key: value
                for key, value in exact.items()
                if key not in {"pairs"}
            },
            "pelvic_patch": {
                "edge_count": len(pelvic_edge_ratios),
                "triangle_count": len(pelvic_area_ratios),
                "minimum_edge_ratio": min(pelvic_edge_ratios),
                "maximum_edge_ratio": max(pelvic_edge_ratios),
                "minimum_triangle_area_ratio": min(pelvic_area_ratios),
                "maximum_triangle_area_ratio": max(pelvic_area_ratios),
            },
            "global_surface_deformation": {
                "edge_count": len(global_edge_ratios),
                "triangle_count": len(global_area_ratios),
                "minimum_edge_ratio": min(global_edge_ratios),
                "maximum_edge_ratio": max(global_edge_ratios),
                "minimum_triangle_area_ratio": min(global_area_ratios),
                "maximum_triangle_area_ratio": max(global_area_ratios),
                "orientation_reversal_triangle_count_after_root_rotation_correction": reversal_count,
                "minimum_oriented_normal_alignment_after_root_rotation_correction": minimum_normal_alignment,
                "signed_volume_m3": posed_signed_volume,
                "signed_volume_ratio": signed_volume_ratio,
                "passed": global_deformation_passed,
            },
            "passed": passed,
        }
    finally:
        evaluated.to_mesh_clear()


def main() -> int:
    args = parse_args()
    blender_executable = require_safe_blender_invocation()
    config_path = _project_argument(args.config).resolve(strict=True)
    authorization_path = _project_argument(args.authorization).resolve(strict=True)
    authorization = validate_one_run_authorization(
        PROJECT_ROOT,
        config_path,
        authorization_path,
        blender_executable,
        operation="audit",
    )
    config = read_json(config_path, "rigged-carrier config")
    output = config["output"]
    source_path = project_path(
        PROJECT_ROOT, config["source"]["path"], "source", must_exist=True
    )
    candidate_path = project_path(
        PROJECT_ROOT, output["candidate_blend"], "candidate", must_exist=True
    )
    build_report_path = project_path(
        PROJECT_ROOT, output["build_report"], "build report", must_exist=True
    )
    audit_report_path = project_path(
        PROJECT_ROOT, output["audit_report"], "audit report", must_exist=False
    )
    if (
        native_filesystem_path(audit_report_path).exists()
        or native_filesystem_path(audit_report_path).is_symlink()
    ):
        raise RiggedCarrierError("append-only audit output already exists")

    build_report = read_json(build_report_path, "carrier build report")
    if build_report.get("status") != (
        "BUILT_PRIVATE_INACTIVE_PENDING_INDEPENDENT_POSE_AUDIT_AND_OWNER_REVIEW"
    ):
        raise RiggedCarrierError("carrier build report status differs")
    if not _receipt_matches(build_report, "build_receipt_sha256"):
        raise RiggedCarrierError("carrier build report receipt differs")
    if build_report.get("config_sha256") != sha256_file(config_path):
        raise RiggedCarrierError("carrier build report config binding differs")
    build_authorization = build_report.get("authorization")
    if not isinstance(build_authorization, Mapping):
        raise RiggedCarrierError("carrier build authorization receipt is absent")
    authorization_binding = {
        "path": output["one_run_authorization"],
        "sha256": sha256_file(authorization_path),
        "one_run_id": authorization["one_run_id"],
        "preflight_receipt_sha256": authorization["preflight_receipt_sha256"],
        "controller_sha256": authorization["controller_sha256"],
        "builder_sha256": authorization["builder_sha256"],
        "auditor_sha256": authorization["auditor_sha256"],
        "intersection_auditor_sha256": authorization[
            "intersection_auditor_sha256"
        ],
    }
    for key, expected in authorization_binding.items():
        if build_authorization.get(key) != expected:
            raise RiggedCarrierError(
                f"build/audit authorization chain differs: {key}"
            )
    candidate_record = build_report.get("candidate")
    source_record = build_report.get("source")
    if not isinstance(candidate_record, Mapping) or not isinstance(source_record, Mapping):
        raise RiggedCarrierError("carrier build report artifact binding is absent")
    if candidate_record.get("path") != output["candidate_blend"]:
        raise RiggedCarrierError("carrier build report candidate path differs")
    candidate_sha_before = sha256_file(candidate_path)
    source_sha_before = sha256_file(source_path)
    if candidate_record.get("sha256") != candidate_sha_before:
        raise RiggedCarrierError("carrier candidate hash differs from build report")
    if source_sha_before != config["source"]["sha256"]:
        raise RiggedCarrierError("qualified source changed before pose audit")
    if source_record.get("sha256_before") != source_sha_before:
        raise RiggedCarrierError("carrier build report source binding differs")
    if source_record.get("sha256_after") != source_sha_before:
        raise RiggedCarrierError("carrier build report did not preserve source")
    if source_record.get("unchanged") is not True:
        raise RiggedCarrierError("carrier build report source preservation differs")

    bpy.ops.wm.open_mainfile(filepath=str(candidate_path), load_ui=False, use_scripts=False)
    if not same_filesystem_path(Path(bpy.data.filepath), candidate_path):
        raise RiggedCarrierError("Blender did not open the exact carrier candidate")
    body, armature = _require_candidate_scene(config, build_report)

    pose_audit = config["pose_audit"]
    poses = list(pose_audit["poses"])
    if tuple(pose["pose_id"] for pose in poses) != EXPECTED_POSE_IDS:
        raise RiggedCarrierError("configured pose order differs")
    group_names = tuple(pose_audit["pelvic_landmark_groups"])
    if group_names != EXPECTED_PELVIC_GROUPS:
        raise RiggedCarrierError("configured pelvic landmark groups differ")
    group_members = _group_members(body, group_names)
    pelvic_members = set().union(*group_members.values())

    _reset_pose(armature)
    evaluated, rest_mesh = _evaluated_mesh(body)
    try:
        rest_points = _finite_points(rest_mesh)
        raw_points = [vertex.co.copy() for vertex in body.data.vertices]
        rest_displacements = [
            float((rest_points[index] - raw_points[index]).length)
            for index in range(len(rest_points))
        ]
        maximum_rest_displacement = max(rest_displacements, default=math.inf)
        if maximum_rest_displacement > float(
            pose_audit["maximum_rest_pose_surface_displacement_m"]
        ):
            raise RiggedCarrierError("armature changes the carrier in rest pose")
        global_edges = [
            tuple(int(value) for value in edge.vertices) for edge in rest_mesh.edges
        ]
        global_triangles = _triangles(rest_mesh)
        global_rest_edge_lengths, global_rest_triangle_areas = _positive_baselines(
            rest_points,
            global_edges,
            global_triangles,
            label="global",
        )
        rest_signed_volume = _signed_volume(rest_points, global_triangles)
        if not math.isfinite(rest_signed_volume) or abs(rest_signed_volume) <= 1.0e-10:
            raise RiggedCarrierError("rest carrier has zero or invalid signed volume")
        pelvic_edges, pelvic_triangles = _pelvic_topology(rest_mesh, pelvic_members)
        pelvic_rest_edge_lengths, pelvic_rest_triangle_areas = _positive_baselines(
            rest_points,
            pelvic_edges,
            pelvic_triangles,
            label="pelvic",
        )
    finally:
        evaluated.to_mesh_clear()

    pose_records = [
        _pose_record(
            body,
            armature,
            pose,
            rest_points,
            global_edges,
            global_triangles,
            global_rest_edge_lengths,
            global_rest_triangle_areas,
            rest_signed_volume,
            pelvic_edges,
            pelvic_triangles,
            pelvic_rest_edge_lengths,
            pelvic_rest_triangle_areas,
            pose_audit,
        )
        for pose in poses
    ]
    _reset_pose(armature)
    if any(
        any(abs(float(value)) > 1.0e-12 for value in bone.rotation_euler)
        for bone in armature.pose.bones
    ):
        raise RiggedCarrierError("auditor did not restore the rest pose in memory")

    candidate_sha_after = sha256_file(candidate_path)
    source_sha_after = sha256_file(source_path)
    if candidate_sha_after != candidate_sha_before:
        raise RiggedCarrierError("carrier candidate changed during read-only audit")
    if source_sha_after != source_sha_before:
        raise RiggedCarrierError("qualified source changed during read-only audit")
    technical_pass = all(record["passed"] is True for record in pose_records)
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_type": "makehuman_adult_female_rigged_carrier_pose_space_audit",
        "status": (
            "POSE_SPACE_TECHNICAL_PASS_PENDING_OWNER_REVIEW"
            if technical_pass
            else "POSE_SPACE_TECHNICAL_FAIL"
        ),
        "candidate_id": config["candidate"]["candidate_id"],
        "config_sha256": sha256_file(config_path),
        "authorization": {
            "path": authorization_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256_file(authorization_path),
            "one_run_id": authorization["one_run_id"],
            "preflight_receipt_sha256": authorization["preflight_receipt_sha256"],
            "controller_sha256": authorization["controller_sha256"],
            "builder_sha256": authorization["builder_sha256"],
            "auditor_sha256": authorization["auditor_sha256"],
            "intersection_auditor_sha256": authorization[
                "intersection_auditor_sha256"
            ],
        },
        "source": {
            "path": config["source"]["path"],
            "sha256_before": source_sha_before,
            "sha256_after": source_sha_after,
            "unchanged": source_sha_before == source_sha_after,
        },
        "candidate": {
            "path": output["candidate_blend"],
            "bytes": native_filesystem_path(candidate_path).stat().st_size,
            "sha256_before": candidate_sha_before,
            "sha256_after": candidate_sha_after,
            "unchanged": candidate_sha_before == candidate_sha_after,
        },
        "build_report": {
            "path": output["build_report"],
            "sha256": sha256_file(build_report_path),
            "receipt_verified": True,
        },
        "pelvic_landmark_groups": {
            name: len(group_members[name]) for name in group_names
        },
        "pelvic_patch": {
            "union_vertex_count": len(pelvic_members),
            "internal_edge_count": len(pelvic_edges),
            "internal_triangle_count": len(pelvic_triangles),
        },
        "rest_pose": {
            "maximum_surface_displacement_from_saved_mesh_m": maximum_rest_displacement,
            "global_edge_count": len(global_edges),
            "global_triangle_count": len(global_triangles),
            "signed_volume_m3": rest_signed_volume,
            "passed": True,
        },
        "thresholds": {
            key: pose_audit[key]
            for key in pose_audit
            if key
            not in {
                "required_pose_ids",
                "pelvic_landmark_groups",
                "poses",
            }
        },
        "poses": pose_records,
        "technical_pass": technical_pass,
        "read_only_actions": {
            "candidate_saved": False,
            "source_saved": False,
            "render_performed": False,
            "export_performed": False,
            "hair_added": False,
            "clothing_added": False,
            "internal_anatomy_added": False,
            "identity_styling_added": False,
            "runtime_activation_performed": False,
            "public_export_performed": False,
        },
        "authority": {
            "owner_approved": False,
            "candidate_assignment_authorized": False,
            "anatomy_authoring_authorized": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        },
        "blender": {
            "version": list(bpy.app.version),
            "background": bool(bpy.app.background),
            "factory_startup_flag_present_before_separator": (
                "--factory-startup" in sys.argv[: sys.argv.index("--")]
            ),
            "autoexec_disabled_flag_present_before_separator": (
                "--disable-autoexec" in sys.argv[: sys.argv.index("--")]
            ),
            "executable_sha256": sha256_file(blender_executable),
        },
    }
    report["audit_receipt_sha256"] = canonical_sha256(report)
    _write_new_json(audit_report_path, report)
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0 if technical_pass else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "AUDIT_REJECTED",
                    "error": str(exc),
                    "candidate_saved": False,
                    "source_saved": False,
                    "runtime_activation_performed": False,
                    "public_export_performed": False,
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
