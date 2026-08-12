"""Read-only oral-rig probe for Kira's exact approved R19 baseline.

This worker is intentionally *not* an authoring worker.  It is loaded by
Blender with the exact approved R19 Blend and writes one append-only JSON
report outside the Blend.  It does not call operators, change a frame, alter a
pose, add controls, render, or save the Blend.

The filename retains the planned R21 lip-sync workstream name, but the input
contract deliberately binds only to the owner-approved R19 baseline.  A later
pelvis, movement, brow, or nail candidate is not selected by this probe.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260802/"
    "kira_r21_exact_wav_lipsync_preparation/"
    "attempt_02_r19_baseline_probe_worker/PROBE_CONFIG.json"
)
CONFIG_PATH = (PROJECT_ROOT / CONFIG_RELATIVE_PATH).resolve()
ORAL_TOKENS = ("jaw", "lip", "mouth", "teeth", "tooth", "tongue", "cheek", "nasolabial")
EPSILON = 1.0e-12


class OralProbeError(RuntimeError):
    """Raised when the sealed source or append-only output contract drifts."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_blender_name(name: str) -> str:
    stem, dot, suffix = str(name).rpartition(".")
    return stem if dot and len(suffix) == 3 and suffix.isdigit() else str(name)


def project_relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def resolve_project_path(relative_value: str, *, must_exist: bool) -> Path:
    supplied = Path(relative_value)
    if supplied.is_absolute() or ".." in supplied.parts:
        raise OralProbeError(f"project-relative path required: {relative_value!r}")
    resolved = (PROJECT_ROOT / supplied).resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise OralProbeError(f"path escaped project root: {relative_value!r}") from exc
    if must_exist and not resolved.is_file():
        raise OralProbeError(f"required file is missing: {relative_value}")
    return resolved


def vector_record(value: Sequence[float]) -> list[float]:
    return [round(float(component), 12) for component in value]


def matrix_record(value: Any) -> list[list[float]]:
    return [vector_record(row) for row in value]


def load_config() -> tuple[dict[str, Any], Path, Path]:
    if not CONFIG_PATH.is_file():
        raise OralProbeError(f"fixed probe config is missing: {CONFIG_RELATIVE_PATH}")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise OralProbeError("unsupported probe config schema")
    if config.get("mode") != "READ_ONLY_NO_SAVE_NO_RENDER":
        raise OralProbeError("probe mode is not the fixed read-only mode")

    source = resolve_project_path(str(config["source_blend"]["path"]), must_exist=True)
    output = resolve_project_path(str(config["output_report"]), must_exist=False)
    if project_relative(CONFIG_PATH) != CONFIG_RELATIVE_PATH:
        raise OralProbeError("fixed config path drifted")
    if output.exists():
        raise OralProbeError(f"append-only output already exists: {project_relative(output)}")
    if not output.parent.is_dir():
        raise OralProbeError("append-only output directory must be prepared before Blender starts")
    return config, source, output


def mesh_geometry_uv_signature(obj: bpy.types.Object) -> str:
    """Reproduce the exact historical R19 freeze-ledger signature."""
    digest = hashlib.sha256()
    digest.update(canonical_blender_name(obj.data.name).encode("utf-8"))
    for vertex in obj.data.vertices:
        digest.update(
            (
                f"v:{vertex.index}:{float(vertex.co.x):.12g}:"
                f"{float(vertex.co.y):.12g}:{float(vertex.co.z):.12g};"
            ).encode("ascii")
        )
    for polygon in obj.data.polygons:
        digest.update(
            ("p:" + ",".join(str(int(index)) for index in polygon.vertices) + ";").encode(
                "ascii"
            )
        )
    for layer in obj.data.uv_layers:
        digest.update(f"uv:{layer.name};".encode("utf-8"))
        for entry in layer.data:
            digest.update(
                (f"{float(entry.uv.x):.12g},{float(entry.uv.y):.12g};").encode("ascii")
            )
    return digest.hexdigest()


def positive_weight_signature(obj: bpy.types.Object) -> str:
    """Reproduce the exact historical R19 positive-weight signature."""
    digest = hashlib.sha256()
    group_names = {int(group.index): group.name for group in obj.vertex_groups}
    for vertex in obj.data.vertices:
        digest.update(f"v:{int(vertex.index)};".encode("ascii"))
        assignments = sorted(
            (group_names[int(item.group)], float(item.weight))
            for item in vertex.groups
            if float(item.weight) > 0.0
        )
        for name, weight in assignments:
            digest.update(f"{name}:{weight:.12g};".encode("utf-8"))
    return digest.hexdigest()


def rig_rest_signature(rig: bpy.types.Object) -> str:
    """Reproduce the exact historical R19 armature-rest signature."""
    digest = hashlib.sha256()
    for bone in sorted(rig.data.bones, key=lambda item: item.name):
        matrix_local = ",".join(
            f"{float(value):.12g}" for row in bone.matrix_local for value in row
        )
        digest.update(
            (
                f"{bone.name}|{bone.parent.name if bone.parent else ''}|"
                f"{float(bone.head_local.x):.12g},{float(bone.head_local.y):.12g},"
                f"{float(bone.head_local.z):.12g}|{float(bone.tail_local.x):.12g},"
                f"{float(bone.tail_local.y):.12g},{float(bone.tail_local.z):.12g}|"
                f"{matrix_local}|{int(bool(bone.use_deform))};"
            ).encode("utf-8")
        )
    return digest.hexdigest()


def find_exact_mesh_object(spec: dict[str, Any]) -> bpy.types.Object:
    object_name = str(spec["object_name"])
    mesh_name = str(spec["mesh_data_name"])
    matches = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH" and obj.name == object_name and obj.data.name == mesh_name
    ]
    data_name_matches = [
        obj for obj in bpy.data.objects if obj.type == "MESH" and obj.data.name == mesh_name
    ]
    if len(matches) != 1 or len(data_name_matches) != 1:
        raise OralProbeError(
            f"exact oral mesh identity failed for {object_name}/{mesh_name}: "
            f"exact={len(matches)}, data_name={len(data_name_matches)}"
        )
    return matches[0]


def find_exact_rig(config: dict[str, Any]) -> bpy.types.Object:
    expected_name = str(config["rig"]["object_name"])
    matches = [
        obj for obj in bpy.data.objects if obj.type == "ARMATURE" and obj.name == expected_name
    ]
    if len(matches) != 1:
        raise OralProbeError(f"exact rig identity failed for {expected_name}: {len(matches)}")
    return matches[0]


def assert_component_contract(
    spec: dict[str, Any], obj: bpy.types.Object, rig: bpy.types.Object
) -> dict[str, Any]:
    actual_geometry = mesh_geometry_uv_signature(obj)
    actual_weights = positive_weight_signature(obj)
    expected_geometry = str(spec["geometry_uv_sha256"]).lower()
    expected_weights = str(spec["positive_weight_assignment_sha256"]).lower()
    if actual_geometry != expected_geometry:
        raise OralProbeError(f"geometry/UV hash mismatch for {obj.name}")
    if actual_weights != expected_weights:
        raise OralProbeError(f"positive-weight hash mismatch for {obj.name}")
    if len(obj.data.vertices) != int(spec["vertices"]):
        raise OralProbeError(f"vertex-count mismatch for {obj.name}")
    if len(obj.data.polygons) != int(spec["faces"]):
        raise OralProbeError(f"face-count mismatch for {obj.name}")

    armature_modifiers = [modifier for modifier in obj.modifiers if modifier.type == "ARMATURE"]
    modifier_targets = [modifier.object.name if modifier.object else None for modifier in armature_modifiers]
    if rig.name not in modifier_targets:
        raise OralProbeError(f"{obj.name} is not bound to the exact native rig")
    return {
        "object_name": obj.name,
        "mesh_data_name": obj.data.name,
        "vertices": len(obj.data.vertices),
        "edges": len(obj.data.edges),
        "faces": len(obj.data.polygons),
        "geometry_uv_sha256": actual_geometry,
        "positive_weight_assignment_sha256": actual_weights,
        "object_matrix_world": matrix_record(obj.matrix_world),
        "armature_modifier_targets": modifier_targets,
        "shape_key_datablock": obj.data.shape_keys.name if obj.data.shape_keys else None,
    }


def _driver_curve_record(curve: Any) -> dict[str, Any]:
    driver = curve.driver
    variables = []
    for variable in driver.variables:
        variables.append(
            {
                "name": variable.name,
                "type": variable.type,
                "targets": [
                    {
                        "id_name": target.id.name if target.id else None,
                        "id_type": target.id_type,
                        "data_path": target.data_path,
                        "bone_target": target.bone_target,
                        "transform_type": target.transform_type,
                        "transform_space": target.transform_space,
                    }
                    for target in variable.targets
                ],
            }
        )
    return {
        "data_path": curve.data_path,
        "array_index": int(curve.array_index),
        "driver_type": driver.type,
        "expression": driver.expression,
        "mute": bool(curve.mute),
        "variables": variables,
    }


def driver_inventory(id_block: Any, label: str) -> dict[str, Any]:
    animation_data = getattr(id_block, "animation_data", None)
    curves = list(getattr(animation_data, "drivers", ())) if animation_data else []
    return {
        "id_label": label,
        "id_name": str(getattr(id_block, "name", "")),
        "driver_count": len(curves),
        "drivers": [_driver_curve_record(curve) for curve in curves],
    }


def _shape_key_delta_record(block: Any) -> dict[str, Any]:
    relative = block.relative_key if getattr(block, "relative_key", None) else block
    squared_sum = 0.0
    max_delta = 0.0
    changed = 0
    digest = hashlib.sha256()
    for index, point in enumerate(block.data):
        delta = point.co - relative.data[index].co
        length = float(delta.length)
        squared_sum += length * length
        max_delta = max(max_delta, length)
        if length > EPSILON:
            changed += 1
        digest.update(
            (
                f"{index}:{float(point.co.x):.12g},{float(point.co.y):.12g},"
                f"{float(point.co.z):.12g};"
            ).encode("ascii")
        )
    count = len(block.data)
    return {
        "name": block.name,
        "relative_key": relative.name,
        "value": float(block.value),
        "slider_min": float(block.slider_min),
        "slider_max": float(block.slider_max),
        "mute": bool(block.mute),
        "vertex_count": count,
        "changed_vertex_count_from_relative": changed,
        "maximum_delta_m": max_delta,
        "rms_delta_m": math.sqrt(squared_sum / count) if count else 0.0,
        "coordinate_sha256": digest.hexdigest(),
    }


def shape_key_inventory(obj: bpy.types.Object) -> dict[str, Any]:
    keys = obj.data.shape_keys
    if keys is None:
        return {
            "object_name": obj.name,
            "mesh_data_name": obj.data.name,
            "shape_key_count": 0,
            "shape_keys": [],
            "animation": None,
        }
    return {
        "object_name": obj.name,
        "mesh_data_name": obj.data.name,
        "shape_key_datablock": keys.name,
        "shape_key_count": len(keys.key_blocks),
        "shape_keys": [_shape_key_delta_record(block) for block in keys.key_blocks],
        "animation": driver_inventory(keys, f"shape_keys:{keys.name}"),
    }


def _iter_action_fcurves(action: Any) -> Iterator[Any]:
    seen: set[int] = set()
    for curve in getattr(action, "fcurves", ()):
        pointer = int(curve.as_pointer())
        if pointer not in seen:
            seen.add(pointer)
            yield curve
    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            for channelbag in getattr(strip, "channelbags", ()):
                for curve in getattr(channelbag, "fcurves", ()):
                    pointer = int(curve.as_pointer())
                    if pointer not in seen:
                        seen.add(pointer)
                        yield curve


def _curve_record(curve: Any) -> dict[str, Any]:
    points = list(curve.keyframe_points)
    return {
        "data_path": curve.data_path,
        "array_index": int(curve.array_index),
        "keyframe_count": len(points),
        "frame_min": min((float(point.co.x) for point in points), default=None),
        "frame_max": max((float(point.co.x) for point in points), default=None),
        "mute": bool(curve.mute),
    }


def action_inventory(oral_bone_names: Sequence[str]) -> dict[str, Any]:
    lowered_names = tuple(name.lower() for name in oral_bone_names)
    actions = []
    relevant_action_names = []
    for action in sorted(bpy.data.actions, key=lambda item: item.name):
        curves = list(_iter_action_fcurves(action))
        relevant = []
        for curve in curves:
            path_lower = curve.data_path.lower()
            if any(name in path_lower for name in lowered_names) or any(
                token in path_lower for token in ORAL_TOKENS
            ):
                relevant.append(_curve_record(curve))
        if relevant:
            relevant_action_names.append(action.name)
        actions.append(
            {
                "name": action.name,
                "frame_range": [float(value) for value in action.frame_range],
                "curve_count": len(curves),
                "relevant_oral_curve_count": len(relevant),
                "relevant_oral_curves": relevant,
                "slot_identifiers": [
                    str(getattr(slot, "identifier", "")) for slot in getattr(action, "slots", ())
                ],
                "layer_names": [layer.name for layer in getattr(action, "layers", ())],
            }
        )
    return {
        "action_count": len(actions),
        "relevant_oral_action_names": relevant_action_names,
        "actions": actions,
    }


def _constraints_record(pose_bone: Any) -> list[dict[str, Any]]:
    return [
        {
            "name": constraint.name,
            "type": constraint.type,
            "influence": float(constraint.influence),
            "mute": bool(constraint.mute),
            "target": constraint.target.name if getattr(constraint, "target", None) else None,
            "subtarget": str(getattr(constraint, "subtarget", "")),
        }
        for constraint in pose_bone.constraints
    ]


def _identity_basis_error(matrix_basis: Matrix) -> float:
    identity = Matrix.Identity(4)
    return max(abs(float(matrix_basis[row][column] - identity[row][column])) for row in range(4) for column in range(4))


def oral_bone_axes(rig: bpy.types.Object, bone_names: Sequence[str]) -> dict[str, Any]:
    missing = sorted(name for name in bone_names if rig.data.bones.get(name) is None)
    if missing:
        raise OralProbeError(f"required oral bones are missing: {missing}")
    records = []
    for name in bone_names:
        bone = rig.data.bones[name]
        pose_bone = rig.pose.bones.get(name)
        if pose_bone is None:
            raise OralProbeError(f"pose bone is missing for {name}")
        armature_rotation = bone.matrix_local.to_3x3()
        world_matrix = rig.matrix_world @ bone.matrix_local
        world_rotation = world_matrix.to_3x3()
        armature_axes = {
            axis: vector_record(armature_rotation @ vector)
            for axis, vector in (
                ("x", Vector((1.0, 0.0, 0.0))),
                ("y", Vector((0.0, 1.0, 0.0))),
                ("z", Vector((0.0, 0.0, 1.0))),
            )
        }
        world_axes = {
            axis: vector_record((world_rotation @ vector).normalized())
            for axis, vector in (
                ("x", Vector((1.0, 0.0, 0.0))),
                ("y", Vector((0.0, 1.0, 0.0))),
                ("z", Vector((0.0, 0.0, 1.0))),
            )
        }
        records.append(
            {
                "name": name,
                "parent": bone.parent.name if bone.parent else None,
                "use_deform": bool(bone.use_deform),
                "length_m": float(bone.length),
                "head_armature_m": vector_record(bone.head_local),
                "tail_armature_m": vector_record(bone.tail_local),
                "head_world_m": vector_record(rig.matrix_world @ bone.head_local),
                "tail_world_m": vector_record(rig.matrix_world @ bone.tail_local),
                "matrix_local": matrix_record(bone.matrix_local),
                "armature_space_unit_axes": armature_axes,
                "world_space_unit_axes": world_axes,
                "pose": {
                    "rotation_mode": pose_bone.rotation_mode,
                    "location": vector_record(pose_bone.location),
                    "rotation_euler": vector_record(pose_bone.rotation_euler),
                    "rotation_quaternion": vector_record(pose_bone.rotation_quaternion),
                    "scale": vector_record(pose_bone.scale),
                    "matrix_basis": matrix_record(pose_bone.matrix_basis),
                    "identity_basis_max_abs_error": _identity_basis_error(pose_bone.matrix_basis),
                    "constraints": _constraints_record(pose_bone),
                },
            }
        )
    return {
        "measurement_space": "armature_rest_and_world_rest_axes_no_perturbation",
        "motion_range_inference_allowed": False,
        "bones": records,
        "all_required_bones_at_identity_pose_basis": all(
            record["pose"]["identity_basis_max_abs_error"] <= EPSILON for record in records
        ),
    }


def _world_coordinate(obj: bpy.types.Object, vertex: Any) -> Vector:
    return obj.matrix_world @ vertex.co


def _weight_assignments_by_vertex(obj: bpy.types.Object) -> list[dict[str, float]]:
    group_names = {int(group.index): group.name for group in obj.vertex_groups}
    return [
        {
            group_names[int(item.group)]: float(item.weight)
            for item in vertex.groups
            if float(item.weight) > 0.0
        }
        for vertex in obj.data.vertices
    ]


def _point_cloud_summary(points: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not points:
        return {
            "point_count": 0,
            "source_objects": [],
            "aabb_min_world_m": None,
            "aabb_max_world_m": None,
            "centroid_world_m": None,
            "point_sha256": sha256_json([]),
        }
    coordinates = [point["coordinate"] for point in points]
    mins = [min(float(coordinate[axis]) for coordinate in coordinates) for axis in range(3)]
    maxs = [max(float(coordinate[axis]) for coordinate in coordinates) for axis in range(3)]
    centroid = [
        sum(float(coordinate[axis]) for coordinate in coordinates) / len(coordinates)
        for axis in range(3)
    ]
    digest_rows = [
        {
            "object": point["object"],
            "vertex": int(point["vertex"]),
            "coordinate": vector_record(point["coordinate"]),
            "weight": round(float(point["weight"]), 12),
        }
        for point in sorted(points, key=lambda item: (item["object"], int(item["vertex"])))
    ]
    return {
        "point_count": len(points),
        "source_objects": sorted({str(point["object"]) for point in points}),
        "aabb_min_world_m": vector_record(mins),
        "aabb_max_world_m": vector_record(maxs),
        "centroid_world_m": vector_record(centroid),
        "point_sha256": sha256_json(digest_rows),
    }


def mesh_weight_inventory(
    mesh_objects: Sequence[bpy.types.Object], bone_names: Sequence[str]
) -> dict[str, Any]:
    object_records = []
    for obj in sorted(mesh_objects, key=lambda item: item.name):
        assignments = _weight_assignments_by_vertex(obj)
        group_names = {group.name for group in obj.vertex_groups}
        relevant_groups = sorted(group_names.intersection(bone_names))
        bone_records = []
        for bone_name in bone_names:
            weighted = [
                (index, assignment[bone_name])
                for index, assignment in enumerate(assignments)
                if assignment.get(bone_name, 0.0) > 0.0
            ]
            if not weighted:
                continue
            points = [
                {
                    "object": obj.name,
                    "vertex": index,
                    "coordinate": _world_coordinate(obj, obj.data.vertices[index]),
                    "weight": weight,
                }
                for index, weight in weighted
            ]
            bone_records.append(
                {
                    "bone_name": bone_name,
                    "positive_vertex_count": len(weighted),
                    "minimum_positive_weight": min(weight for _, weight in weighted),
                    "maximum_weight": max(weight for _, weight in weighted),
                    "total_weight": sum(weight for _, weight in weighted),
                    "weighted_vertex_assignment_sha256": sha256_json(
                        [[index, round(weight, 12)] for index, weight in weighted]
                    ),
                    "world_point_cloud": _point_cloud_summary(points),
                }
            )
        if relevant_groups:
            object_records.append(
                {
                    "object_name": obj.name,
                    "mesh_data_name": obj.data.name,
                    "vertex_count": len(obj.data.vertices),
                    "relevant_group_names": relevant_groups,
                    "bones_with_positive_weights": bone_records,
                }
            )
    return {
        "mesh_object_count_with_oral_weights": len(object_records),
        "objects": object_records,
    }


def semantic_region_points(
    mesh_objects: Sequence[bpy.types.Object], semantic_groups: dict[str, list[str]]
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {name: [] for name in semantic_groups}
    for obj in mesh_objects:
        assignments = _weight_assignments_by_vertex(obj)
        for index, assignment in enumerate(assignments):
            coordinate = _world_coordinate(obj, obj.data.vertices[index])
            for region_name, group_names in semantic_groups.items():
                weight = max((assignment.get(group_name, 0.0) for group_name in group_names), default=0.0)
                if weight > 0.0:
                    result[region_name].append(
                        {
                            "object": obj.name,
                            "mesh": obj.data.name,
                            "vertex": index,
                            "coordinate": coordinate,
                            "weight": weight,
                        }
                    )
    return result


def _minimum_point_distance(
    first: Sequence[dict[str, Any]], second: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    if not first or not second:
        return {
            "measurable": False,
            "reason": "one_or_both_semantic_point_clouds_empty",
            "minimum_vertex_sample_distance_m": None,
            "closest_first": None,
            "closest_second": None,
        }
    tree = KDTree(len(second))
    for index, point in enumerate(second):
        tree.insert(point["coordinate"], index)
    tree.balance()
    best: tuple[float, dict[str, Any], dict[str, Any]] | None = None
    for point in first:
        _coordinate, second_index, distance = tree.find(point["coordinate"])
        candidate = (float(distance), point, second[int(second_index)])
        if best is None or candidate[0] < best[0]:
            best = candidate
    assert best is not None
    distance, point_a, point_b = best
    return {
        "measurable": True,
        "measurement_kind": "minimum_weighted-vertex-sample_distance_not_signed_surface_clearance",
        "minimum_vertex_sample_distance_m": distance,
        "closest_first": {
            "object": point_a["object"],
            "mesh": point_a["mesh"],
            "vertex": int(point_a["vertex"]),
            "coordinate_world_m": vector_record(point_a["coordinate"]),
            "semantic_weight": float(point_a["weight"]),
        },
        "closest_second": {
            "object": point_b["object"],
            "mesh": point_b["mesh"],
            "vertex": int(point_b["vertex"]),
            "coordinate_world_m": vector_record(point_b["coordinate"]),
            "semantic_weight": float(point_b["weight"]),
        },
    }


def _aabb_relationship(
    first_summary: dict[str, Any], second_summary: dict[str, Any]
) -> dict[str, Any]:
    if not first_summary["point_count"] or not second_summary["point_count"]:
        return {"measurable": False, "axis_separation_m": None, "aabb_overlap": None}
    first_min = first_summary["aabb_min_world_m"]
    first_max = first_summary["aabb_max_world_m"]
    second_min = second_summary["aabb_min_world_m"]
    second_max = second_summary["aabb_max_world_m"]
    separations = [
        max(0.0, float(first_min[axis]) - float(second_max[axis]), float(second_min[axis]) - float(first_max[axis]))
        for axis in range(3)
    ]
    return {
        "measurable": True,
        "axis_separation_m": vector_record(separations),
        "aabb_overlap": all(value <= EPSILON for value in separations),
    }


def rest_clearance_inventory(
    regions: dict[str, list[dict[str, Any]]], relation_specs: Sequence[dict[str, str]]
) -> dict[str, Any]:
    summaries = {name: _point_cloud_summary(points) for name, points in regions.items()}
    relations = []
    for spec in relation_specs:
        first_name = spec["first"]
        second_name = spec["second"]
        first = regions[first_name]
        second = regions[second_name]
        relations.append(
            {
                "id": spec["id"],
                "first_region": first_name,
                "second_region": second_name,
                "point_distance": _minimum_point_distance(first, second),
                "aabb_relationship": _aabb_relationship(
                    summaries[first_name], summaries[second_name]
                ),
            }
        )
    return {
        "coordinate_basis": "undeformed_mesh_datablock_vertices_transformed_by_object_matrix_world",
        "important_limit": (
            "vertex-sample distances localize candidate contacts; they do not prove signed "
            "surface clearance, collision freedom, watertight anatomy, or functional speech"
        ),
        "regions": summaries,
        "relations": relations,
    }


def _all_driver_sources() -> Iterator[tuple[str, Any]]:
    for obj in bpy.data.objects:
        yield f"object:{obj.name}", obj
    for mesh in bpy.data.meshes:
        yield f"mesh:{mesh.name}", mesh
        if mesh.shape_keys is not None:
            yield f"shape_keys:{mesh.shape_keys.name}", mesh.shape_keys
    for armature in bpy.data.armatures:
        yield f"armature:{armature.name}", armature
    for material in bpy.data.materials:
        yield f"material:{material.name}", material
        if material.node_tree is not None:
            yield f"material_node_tree:{material.node_tree.name}", material.node_tree


def relevant_driver_inventory(oral_bone_names: Sequence[str]) -> dict[str, Any]:
    lowered_names = tuple(name.lower() for name in oral_bone_names)
    sources = []
    total_driver_count = 0
    for label, id_block in _all_driver_sources():
        inventory = driver_inventory(id_block, label)
        total_driver_count += int(inventory["driver_count"])
        relevant = []
        for driver in inventory["drivers"]:
            searchable = json.dumps(driver, sort_keys=True).lower()
            if any(name in searchable for name in lowered_names) or any(
                token in searchable for token in ORAL_TOKENS
            ):
                relevant.append(driver)
        if relevant:
            sources.append(
                {
                    "id_label": label,
                    "id_name": inventory["id_name"],
                    "relevant_driver_count": len(relevant),
                    "drivers": relevant,
                }
            )
    return {
        "all_scanned_driver_count": total_driver_count,
        "source_count_with_relevant_oral_drivers": len(sources),
        "sources": sources,
    }


def _pose_state_digest(rig: bpy.types.Object) -> str:
    rows = []
    for pose_bone in sorted(rig.pose.bones, key=lambda item: item.name):
        rows.append(
            {
                "name": pose_bone.name,
                "matrix_basis": matrix_record(pose_bone.matrix_basis),
                "constraints": _constraints_record(pose_bone),
            }
        )
    return sha256_json(rows)


def _shape_key_state_digest(mesh_objects: Sequence[bpy.types.Object]) -> str:
    return sha256_json([shape_key_inventory(obj) for obj in sorted(mesh_objects, key=lambda item: item.name)])


def _action_state_digest() -> str:
    rows = []
    for action in sorted(bpy.data.actions, key=lambda item: item.name):
        rows.append(
            {
                "name": action.name,
                "frame_range": [float(value) for value in action.frame_range],
                "curves": [_curve_record(curve) for curve in _iter_action_fcurves(action)],
            }
        )
    return sha256_json(rows)


def source_state_digest(
    oral_objects: Sequence[bpy.types.Object], all_mesh_objects: Sequence[bpy.types.Object], rig: bpy.types.Object
) -> dict[str, Any]:
    scene = bpy.context.scene
    record = {
        "scene_frame_current": int(scene.frame_current),
        "scene_frame_subframe": float(scene.frame_subframe),
        "oral_geometry_uv": {
            obj.name: mesh_geometry_uv_signature(obj) for obj in oral_objects
        },
        "oral_positive_weights": {
            obj.name: positive_weight_signature(obj) for obj in oral_objects
        },
        "rig_rest_sha256": rig_rest_signature(rig),
        "pose_state_sha256": _pose_state_digest(rig),
        "shape_key_state_sha256": _shape_key_state_digest(all_mesh_objects),
        "action_state_sha256": _action_state_digest(),
    }
    return {"state": record, "sha256": sha256_json(record)}


def run_probe() -> dict[str, Any]:
    config, source_path, output_path = load_config()
    loaded_path = Path(bpy.data.filepath).resolve()
    if loaded_path != source_path:
        raise OralProbeError(
            f"wrong Blend loaded: {project_relative(loaded_path)} != {project_relative(source_path)}"
        )
    source_hash_before = sha256_file(source_path)
    expected_source_hash = str(config["source_blend"]["sha256"]).lower()
    if source_hash_before != expected_source_hash:
        raise OralProbeError("approved R19 source SHA-256 mismatch")
    if source_path.stat().st_size != int(config["source_blend"]["size_bytes"]):
        raise OralProbeError("approved R19 source size mismatch")

    dirty_before = bool(bpy.data.is_dirty)
    if dirty_before:
        raise OralProbeError("loaded source was already dirty before the read-only probe")

    rig = find_exact_rig(config)
    actual_rig_hash = rig_rest_signature(rig)
    if actual_rig_hash != str(config["rig"]["rest_structure_sha256"]).lower():
        raise OralProbeError("native 188-bone rig rest hash mismatch")
    if len(rig.data.bones) != int(config["rig"]["bone_count"]):
        raise OralProbeError("native rig bone count mismatch")

    oral_objects = []
    component_records = []
    for spec in config["oral_components"]:
        obj = find_exact_mesh_object(spec)
        oral_objects.append(obj)
        component_records.append(assert_component_contract(spec, obj, rig))

    all_mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    before_state = source_state_digest(oral_objects, all_mesh_objects, rig)

    oral_names = [str(name) for name in config["oral_bone_names"]]
    axes = oral_bone_axes(rig, oral_names)
    weights = mesh_weight_inventory(all_mesh_objects, oral_names)
    region_points = semantic_region_points(all_mesh_objects, config["semantic_regions"])
    clearances = rest_clearance_inventory(region_points, config["rest_relations"])
    shape_keys = [shape_key_inventory(obj) for obj in sorted(all_mesh_objects, key=lambda item: item.name)]
    actions = action_inventory(oral_names)
    drivers = relevant_driver_inventory(oral_names)

    after_state = source_state_digest(oral_objects, all_mesh_objects, rig)
    source_hash_after = sha256_file(source_path)
    dirty_after = bool(bpy.data.is_dirty)
    source_unchanged = bool(
        source_hash_after == source_hash_before
        and before_state["sha256"] == after_state["sha256"]
        and dirty_after == dirty_before
        and not dirty_after
    )
    if not source_unchanged:
        raise OralProbeError("read-only source-state invariant failed")

    reserved_names = set(str(name) for name in config["reserved_action_names"])
    action_collisions = sorted(reserved_names.intersection(action.name for action in bpy.data.actions))
    region_measurability = {
        name: len(points) > 0 for name, points in region_points.items()
    }
    required_relations_measurable = all(
        relation["point_distance"]["measurable"] for relation in clearances["relations"]
    )
    authoring_gate = bool(
        source_unchanged
        and axes["all_required_bones_at_identity_pose_basis"]
        and all(region_measurability.values())
        and required_relations_measurable
        and not action_collisions
    )

    report = {
        "schema_version": 1,
        "artifact_kind": "KIRA_R19_ORAL_RIG_READ_ONLY_RESPONSE_PROBE",
        "status": "READ_ONLY_PROBE_COMPLETED_NO_SAVE_NO_RENDER_NO_AUTHORING",
        "selection_truth": {
            "selected_source": project_relative(source_path),
            "selected_source_sha256": source_hash_before,
            "approved_rest_face_must_remain_unchanged": True,
            "later_pelvis_candidate_selected": False,
            "later_movement_candidate_selected": False,
            "body_or_runtime_activation_authorized": False,
        },
        "source_integrity": {
            "source_size_bytes": source_path.stat().st_size,
            "disk_sha256_before": source_hash_before,
            "disk_sha256_after": source_hash_after,
            "bpy_data_dirty_before": dirty_before,
            "bpy_data_dirty_after": dirty_after,
            "state_before": before_state,
            "state_after": after_state,
            "source_unchanged": source_unchanged,
            "save_invoked": False,
            "render_invoked": False,
            "frame_changed": False,
            "pose_or_mesh_perturbed": False,
        },
        "scene_observation": {
            "frame_current": int(bpy.context.scene.frame_current),
            "frame_subframe": float(bpy.context.scene.frame_subframe),
            "active_scene": bpy.context.scene.name,
            "active_view_layer": bpy.context.view_layer.name,
        },
        "oral_components": component_records,
        "rig": {
            "object_name": rig.name,
            "bone_count": len(rig.data.bones),
            "rest_structure_sha256": actual_rig_hash,
            "object_matrix_world": matrix_record(rig.matrix_world),
            "animation": driver_inventory(rig, f"object:{rig.name}"),
        },
        "oral_bone_axes": axes,
        "named_bone_weight_inventory": weights,
        "rest_relationships": clearances,
        "available_controls": {
            "shape_keys_all_meshes": shape_keys,
            "actions": actions,
            "relevant_drivers": drivers,
            "reserved_action_names": sorted(reserved_names),
            "reserved_action_name_collisions": action_collisions,
        },
        "probe_findings": {
            "semantic_region_measurability": region_measurability,
            "all_required_relations_measurable": required_relations_measurable,
            "authoring_gate_passed": authoring_gate,
            "authoring_was_run": False,
            "owner_visual_acceptance_inferred": False,
            "next_step": (
                "review measured axes, weights, controls, and clearances before preparing "
                "a separate append-only static AH/EE/O/FV/MBP authoring attempt"
            ),
        },
        "measurement_limits": [
            "No bone was perturbed, so safe rotation/translation ranges are not inferred.",
            "Vertex-sample distances are not signed surface-clearance or collision proof.",
            "Bone names and weights do not prove visually correct deformation.",
            "A mouth-named mesh and tongue bones do not alone prove usable tongue geometry.",
            "No saved Blend, render, viseme action, runtime binding, or body activation exists.",
        ],
    }
    with output_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")
    return report


if __name__ == "__main__":
    completed = run_probe()
    print(
        "KIRA_R19_ORAL_RIG_READ_ONLY_PROBE_COMPLETE "
        + json.dumps(
            {
                "source_sha256": completed["selection_truth"]["selected_source_sha256"],
                "source_unchanged": completed["source_integrity"]["source_unchanged"],
                "authoring_gate_passed": completed["probe_findings"]["authoring_gate_passed"],
            },
            sort_keys=True,
        )
    )
