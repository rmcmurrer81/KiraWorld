#!/usr/bin/env python3
"""One bounded action-only Kira R21 movement/deformation review attempt.

The worker is deliberately bound to the exact private, inactive R21 eyebrow
Attempt-02 Blend.  It may add actions, but it must leave every inherited mesh,
material binding, modifier, transform, weight assignment, rig-rest datum, and
inherited action unchanged.  Cameras and contact props are temporary render
evidence and are removed before the append-only Blend is saved.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import traceback
from typing import Any, Iterable, Sequence

import bpy
from mathutils import Vector


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_assemble_kira_r19_bald_owner_review as assembly  # noqa: E402
import blender_correct_kira_r19_targeted_attempt06 as prior  # noqa: E402
import blender_probe_blackproject_r19_seated_contact as seated  # noqa: E402


DEFAULT_CONFIG = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r21_action_only_movement_correction/MOVEMENT_CONFIG_ATTEMPT_01.json"
)
POSE_FRAME = 30
TEMP_COLLECTION = "KIRA_R21_MOVEMENT_ATTEMPT01_TEMP_RENDER_ONLY"
ACTION_PREFIX = "KIRA_R21_MOVEMENT_ATTEMPT01_"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def json_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def degrees_to_radians(raw: dict[str, Sequence[float]]) -> dict[str, tuple[float, float, float]]:
    return {
        str(name): tuple(math.radians(float(value)) for value in values)
        for name, values in raw.items()
    }


def float_matrix(matrix: Any) -> list[list[float]]:
    return [[float(value) for value in row] for row in matrix]


def action_signature(action: bpy.types.Action) -> dict[str, Any]:
    curves: list[dict[str, Any]] = []
    try:
        fcurves = list(action.fcurves)
    except (AttributeError, RuntimeError):
        fcurves = []
    for curve in sorted(fcurves, key=lambda item: (item.data_path, int(item.array_index))):
        points = []
        for point in curve.keyframe_points:
            points.append(
                {
                    "co": [float(point.co[0]), float(point.co[1])],
                    "handle_left": [float(point.handle_left[0]), float(point.handle_left[1])],
                    "handle_right": [float(point.handle_right[0]), float(point.handle_right[1])],
                    "interpolation": str(point.interpolation),
                    "handle_left_type": str(point.handle_left_type),
                    "handle_right_type": str(point.handle_right_type),
                }
            )
        curves.append(
            {
                "data_path": str(curve.data_path),
                "array_index": int(curve.array_index),
                "keyframes": points,
            }
        )
    custom = {
        str(key): action[key]
        for key in sorted(action.keys())
        if isinstance(action[key], (bool, int, float, str))
    }
    payload = {
        "name": action.name,
        "use_fake_user": bool(action.use_fake_user),
        "frame_range": [float(value) for value in action.frame_range],
        "custom_properties": custom,
        "fcurves": curves,
    }
    payload["sha256"] = json_sha256(payload)
    return payload


def inherited_action_snapshot() -> dict[str, dict[str, Any]]:
    return {
        action.name: action_signature(action)
        for action in sorted(bpy.data.actions, key=lambda item: item.name)
        if not action.name.startswith(ACTION_PREFIX)
    }


def mesh_snapshot(obj: bpy.types.Object) -> dict[str, Any]:
    record = prior.mesh_immutable_state(obj)
    record["material_bindings"] = assembly.material_binding_signature(obj)
    record["hide_render"] = bool(obj.hide_render)
    record["hide_viewport"] = bool(obj.hide_viewport)
    return record


def inherited_mesh_snapshot() -> dict[str, dict[str, Any]]:
    return {
        obj.name: mesh_snapshot(obj)
        for obj in sorted(bpy.data.objects, key=lambda item: item.name)
        if obj.type == "MESH" and not obj.name.startswith("KIRA_R21_MOVEMENT_ATTEMPT01_TEMP_")
    }


def evaluated_coordinate_sha256(obj: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    for index, point in enumerate(assembly.evaluated_vertices(obj)):
        digest.update(
            f"{index}:{float(point.x):.12g},{float(point.y):.12g},{float(point.z):.12g};".encode(
                "ascii"
            )
        )
    return digest.hexdigest()


def load_and_verify_config(config_path: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    paths = {
        "source_blend": PROJECT_ROOT / str(config["source_blend"]),
        "source_evidence": PROJECT_ROOT / str(config["source_evidence"]),
        "r19_movement_evidence": PROJECT_ROOT / str(config["r19_movement_evidence"]),
        "r19_movement_config": PROJECT_ROOT / str(config["r19_movement_config"]),
        "recovery_output": PROJECT_ROOT / str(config["recovery_output_dir"]),
        "owner_output": PROJECT_ROOT / str(config["owner_review_output_dir"]),
    }
    expected = {
        "source_blend": str(config["source_blend_sha256"]),
        "source_evidence": str(config["source_evidence_sha256"]),
        "r19_movement_evidence": str(config["r19_movement_evidence_sha256"]),
        "r19_movement_config": str(config["r19_movement_config_sha256"]),
    }
    for key in expected:
        path = paths[key]
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256_file(path)
        if actual != expected[key].lower():
            raise RuntimeError(f"protected input hash mismatch for {key}: {actual}")
    if len(config["seated_candidates"]) != 2:
        raise RuntimeError("main seated/leg defect must have exactly two candidates")
    ids = [str(item["id"]) for item in config["seated_candidates"]]
    if len(ids) != len(set(ids)):
        raise RuntimeError("seated candidate IDs must be unique")
    for path in (paths["recovery_output"], paths["owner_output"]):
        if path.exists():
            raise FileExistsError(f"append-only output exists: {path}")
    if Path(bpy.data.filepath).resolve() != paths["source_blend"].resolve():
        raise RuntimeError("worker was not opened with the exact configured source Blend")
    return config, paths


def find_components(config: dict[str, Any]) -> tuple[bpy.types.Object, bpy.types.Object, list[bpy.types.Object]]:
    body = bpy.data.objects.get(str(config["body_object"]))
    rig = bpy.data.objects.get(str(config["rig_object"]))
    if body is None or body.type != "MESH":
        raise RuntimeError("exact configured R21 body object is missing")
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError("exact configured native rig is missing")
    if len(rig.data.bones) != int(config["expected_rig_joint_count"]):
        raise RuntimeError("native rig joint count drifted")
    if assembly.mesh_geometry_uv_signature(body) != str(config["body_geometry_uv_sha256"]):
        raise RuntimeError("approved body geometry/UV signature drifted")
    if prior.weight_signature(body) != str(config["body_positive_weight_assignment_sha256"]):
        raise RuntimeError("approved body weight signature drifted")
    if prior.rig_immutable_signature(rig) != str(config["rig_rest_sha256"]):
        raise RuntimeError("approved native rest-rig signature drifted")
    nails = sorted(
        [obj for obj in bpy.data.objects if obj.type == "MESH" and bool(obj.get("nail_component"))],
        key=lambda item: item.name,
    )
    if len(nails) != 20:
        raise RuntimeError(f"expected inherited 20-nail inventory, found {len(nails)}")
    return body, rig, nails


SEMANTIC_PREFIXES: list[tuple[str, tuple[str, ...]]] = [
    ("left_hand", ("lHand_", "lThumb", "lIndex", "lMid", "lRing", "lPinky")),
    ("right_hand", ("rHand_", "rThumb", "rIndex", "rMid", "rRing", "rPinky")),
    ("left_forearm", ("lForearm",)),
    ("right_forearm", ("rForearm",)),
    ("left_upper_arm", ("lShldr",)),
    ("right_upper_arm", ("rShldr",)),
    ("left_foot", ("lFoot_", "lToe_", "lMetatarsals_", "lBigToe", "lSmallToe")),
    ("right_foot", ("rFoot_", "rToe_", "rMetatarsals_", "rBigToe", "rSmallToe")),
    ("left_lower_leg_knee", ("lShin_",)),
    ("right_lower_leg_knee", ("rShin_",)),
    ("left_upper_thigh_hip", ("lThighBend_", "lThighTwist_")),
    ("right_upper_thigh_hip", ("rThighBend_", "rThighTwist_")),
    ("pelvis_perineum", ("pelvis_", "hip_")),
    ("abdomen_torso", ("abdomen", "chest", "lPectoral", "rPectoral")),
    ("neck_head_face", ("neck", "head", "upperFace", "lowerFace", "jaw", "eye", "Brow")),
]


def polygon_region(body: bpy.types.Object, face_index: int) -> dict[str, Any]:
    if face_index < 0 or face_index >= len(body.data.polygons):
        return {"region": "unknown_face_index", "scores": {}, "face_index": face_index}
    polygon = body.data.polygons[face_index]
    group_names = {group.index: group.name for group in body.vertex_groups}
    scores = {name: 0.0 for name, _ in SEMANTIC_PREFIXES}
    for vertex_index in polygon.vertices:
        vertex = body.data.vertices[int(vertex_index)]
        for assignment in vertex.groups:
            group_name = group_names.get(int(assignment.group), "")
            weight = float(assignment.weight)
            for region, prefixes in SEMANTIC_PREFIXES:
                if group_name.startswith(prefixes):
                    scores[region] += weight
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    region, score = ranked[0]
    if score <= 1.0e-8:
        region = "unclassified_weight_region"
    return {
        "face_index": int(face_index),
        "region": region,
        "dominant_weight_sum": round(float(score), 9),
        "scores": {name: round(value, 9) for name, value in ranked if value > 1.0e-8},
    }


def pair_key(pair: dict[str, Any]) -> str:
    values = sorted(int(value) for value in pair["face_indices"])
    return f"{values[0]}:{values[1]}"


def localize_report(
    body: bpy.types.Object,
    report: dict[str, Any],
    neutral_keys: set[str],
) -> dict[str, Any]:
    rows = []
    counts: dict[str, int] = {}
    for pair in report.get("pairs", []):
        faces = [int(value) for value in pair["face_indices"]]
        first = polygon_region(body, faces[0])
        second = polygon_region(body, faces[1])
        label = "__".join(sorted((str(first["region"]), str(second["region"]))))
        counts[label] = counts.get(label, 0) + 1
        center = [
            (float(pair["face_centers"][0][axis]) + float(pair["face_centers"][1][axis])) * 0.5
            for axis in range(3)
        ]
        rows.append(
            {
                "pair_key": pair_key(pair),
                "face_indices": faces,
                "first_face": first,
                "second_face": second,
                "localized_pair_region": label,
                "neutral_relationship": (
                    "inherited_at_neutral" if pair_key(pair) in neutral_keys else "pose_induced_or_pose_exposed"
                ),
                "midpoint_world_m": [round(value, 9) for value in center],
                "center_distance_m": float(pair["center_distance_m"]),
                "maximum_intersection_segment_length_m": max(
                    (
                        float(item.get("intersection_segment_length_m", 0.0))
                        for item in pair.get("triangle_pair_classifications", [])
                    ),
                    default=0.0,
                ),
            }
        )
    pose_keys = {row["pair_key"] for row in rows}
    return {
        "exact_pair_count": int(report["exact_genuine_penetration_pair_count"]),
        "localized_pair_region_counts": dict(sorted(counts.items())),
        "inherited_neutral_pair_count": sum(
            row["neutral_relationship"] == "inherited_at_neutral" for row in rows
        ),
        "pose_induced_or_pose_exposed_pair_count": sum(
            row["neutral_relationship"] == "pose_induced_or_pose_exposed" for row in rows
        ),
        "neutral_pairs_absent_in_pose_count": len(neutral_keys - pose_keys),
        "neutral_pairs_absent_in_pose": sorted(neutral_keys - pose_keys),
        "pairs": rows,
    }


def joint_metrics(rig: bpy.types.Object) -> dict[str, Any]:
    names = {
        "left_knee": "lThighBend_05",
        "right_knee": "rThighBend_021",
        "left_ankle": "lShin_07",
        "right_ankle": "rShin_023",
    }
    points: dict[str, Vector] = {}
    for label, bone_name in names.items():
        bone = rig.pose.bones.get(bone_name)
        if bone is None:
            raise RuntimeError(f"joint metric bone missing: {bone_name}")
        points[label] = rig.matrix_world @ bone.tail
    return {
        "points_world_m": {
            key: [round(float(value), 9) for value in point]
            for key, point in points.items()
        },
        "bilateral_knee_center_separation_m": round(
            float((points["left_knee"] - points["right_knee"]).length), 9
        ),
        "bilateral_ankle_center_separation_m": round(
            float((points["left_ankle"] - points["right_ankle"]).length), 9
        ),
    }


def pose_record(
    pose_id: str,
    rotations_degrees: dict[str, Sequence[float]],
    body: bpy.types.Object,
    rig: bpy.types.Object,
    nails: list[bpy.types.Object],
    neutral_points: list[Vector],
    neutral_keys: set[str],
    regions: dict[str, list[int]],
    config: dict[str, Any],
) -> dict[str, Any]:
    rotations = degrees_to_radians(rotations_degrees)
    assembly.apply_rotations(rig, rotations)
    posed = assembly.evaluated_vertices(body)
    exact = assembly.exact_body_intersection_report(body)
    localized = localize_report(body, exact, neutral_keys)
    body_nail = assembly.exact_cross_intersections(body, nails)
    stretch = assembly.edge_stretch_report(body, neutral_points, posed, set(range(len(neutral_points))))
    record: dict[str, Any] = {
        "id": pose_id,
        "rotations_degrees_xyz": rotations_degrees,
        "exact_intersections": exact,
        "localized_intersections": localized,
        "exact_body_nail_intersections": body_nail,
        "deformation_stretch": stretch,
        "joint_metrics": joint_metrics(rig),
        "visual_acceptance_claimed": False,
    }
    if pose_id.startswith("seated_open_supported"):
        seat_regions = {key: regions[key] for key in ("pelvis", "left_foot", "right_foot")}
        record["support_contact"] = seated.contact_solution(body, posed, seat_regions)
        record["seated_geometry"] = seated.geometric_pose_metrics(body, posed, seat_regions)
    elif pose_id == "supine_relaxed_foundation":
        record["supine_metrics"] = prior.supine_metrics(
            posed,
            neutral_points,
            float(config["support_epsilon_m"]),
            float(config["contact_tolerance_m"]),
        )
    elif pose_id in ("table_reach_foundation", "hand_to_mouth_drink_foundation"):
        record["reach_metrics"] = prior.reach_metrics(
            posed,
            neutral_points,
            regions,
            float(config["support_epsilon_m"]),
            float(config["contact_tolerance_m"]),
        )
    assembly.reset_pose(rig)
    return record


def seated_score(record: dict[str, Any], neutral_count: int) -> tuple[float, dict[str, float]]:
    localized = record["localized_intersections"]
    stretch = record["deformation_stretch"]["all_body_edges"]
    contact = record["support_contact"]
    geometry = record["seated_geometry"]
    nail_pairs = int(
        record["exact_body_nail_intersections"]["total_exact_genuine_body_nail_triangle_pair_count"]
    )
    parts = {
        "pose_induced_pair_penalty": float(localized["pose_induced_or_pose_exposed_pair_count"] * 100000.0),
        "total_pair_excess_penalty": float(
            max(0, int(localized["exact_pair_count"]) - neutral_count) * 10000.0
        ),
        "body_nail_crossing_penalty": float(nail_pairs * 1000000.0),
        "three_support_failure_penalty": (
            0.0 if bool(contact["all_three_supports_within_tolerance"]) else 1000000.0
        ),
        "support_penetration_penalty": (
            0.0 if bool(contact["all_three_supports_no_penetration"]) else 1000000.0
        ),
        "maximum_edge_ratio_penalty": float(max(0.0, stretch["maximum_ratio"] - 1.0) * 100.0),
        "bilateral_foot_height_penalty": float(
            geometry["bilateral_foot_low_height_difference_m"] * 10000.0
        ),
        "sole_pitch_penalty": float(
            (
                geometry["left_toe_heel_bottom_height_difference_m"]
                + geometry["right_toe_heel_bottom_height_difference_m"]
            )
            * 5000.0
        ),
        "posterior_contact_reward": -float(
            contact["seat"]["contact_point_count_within_tolerance"] * 0.1
        ),
    }
    return sum(parts.values()), parts


def action_name(pose_id: str) -> str:
    return ACTION_PREFIX + pose_id.upper()


def author_pose_action(
    rig: bpy.types.Object,
    pose_id: str,
    rotations_degrees: dict[str, Sequence[float]],
    candidate_id: str,
) -> bpy.types.Action:
    name = action_name(pose_id)
    if bpy.data.actions.get(name) is not None:
        raise RuntimeError(f"new action collision: {name}")
    action = assembly.author_action(
        rig,
        name,
        degrees_to_radians(rotations_degrees),
        candidate_id,
    )
    action["action_only_movement_attempt"] = 1
    action["pose_id"] = pose_id
    action["private_owner_review_only"] = True
    action["inactive"] = True
    action["owner_approved"] = False
    action["runtime_assignment_allowed"] = False
    action["movement_foundation_not_full_biological_capability"] = True
    action.use_fake_user = True
    assembly.reset_pose(rig)
    return action


def scaled_rotations(
    rotations_degrees: dict[str, Sequence[float]], factor: float
) -> dict[str, tuple[float, float, float]]:
    return {
        name: tuple(math.radians(float(value) * factor) for value in values)
        for name, values in rotations_degrees.items()
    }


def author_transition_action(
    rig: bpy.types.Object,
    selected: dict[str, Any],
    frames: Sequence[int],
    candidate_id: str,
) -> bpy.types.Action:
    if len(frames) != 6:
        raise RuntimeError("sit/stand transition requires exactly six predeclared frames")
    name = action_name("sit_to_stand_transition_foundation")
    if bpy.data.actions.get(name) is not None:
        raise RuntimeError(f"new action collision: {name}")
    factors = (0.0, 0.45, 1.0, 1.0, 0.45, 0.0)
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = action
    rotations_degrees = selected["rotations_degrees_xyz"]
    for frame, factor in zip(frames, factors):
        pose = scaled_rotations(rotations_degrees, factor)
        for bone in rig.pose.bones:
            bone.rotation_mode = "XYZ"
            bone.rotation_euler = (0.0, 0.0, 0.0)
            bone.location = (0.0, 0.0, 0.0)
            bone.scale = (1.0, 1.0, 1.0)
        for bone_name, rotation in pose.items():
            bone = rig.pose.bones.get(bone_name)
            if bone is None:
                raise RuntimeError(f"transition bone missing: {bone_name}")
            bone.rotation_euler = rotation
            bone.keyframe_insert(data_path="rotation_euler", frame=int(frame), group=bone_name)
    try:
        for curve in action.fcurves:
            for point in curve.keyframe_points:
                point.interpolation = "BEZIER"
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"
    except (AttributeError, RuntimeError):
        pass
    action["candidate_id"] = candidate_id
    action["action_only_movement_attempt"] = 1
    action["pose_id"] = "sit_to_stand_transition_foundation"
    action["selected_seated_source"] = str(selected["id"])
    action["private_owner_review_only"] = True
    action["inactive"] = True
    action["owner_approved"] = False
    action["runtime_assignment_allowed"] = False
    action["transition_foundation_not_foot_lock_or_biomechanical_proof"] = True
    assembly.reset_pose(rig)
    return action


def transition_audit(
    action: bpy.types.Action,
    frames: Sequence[int],
    body: bpy.types.Object,
    rig: bpy.types.Object,
    neutral_points: list[Vector],
    neutral_keys: set[str],
    regions: dict[str, list[int]],
) -> list[dict[str, Any]]:
    records = []
    rig.animation_data_create()
    rig.animation_data.action = action
    for frame in frames:
        bpy.context.scene.frame_set(int(frame))
        bpy.context.view_layer.update()
        posed = assembly.evaluated_vertices(body)
        exact = assembly.exact_body_intersection_report(body)
        feet = {}
        for side in ("left", "right"):
            points = [posed[index] for index in regions[f"{side}_foot"]]
            feet[side] = {
                "low_z_m": min(float(point.z) for point in points),
                "center_world_m": [
                    float(value) for value in (sum(points, Vector()) / len(points))
                ],
            }
        records.append(
            {
                "frame": int(frame),
                "exact_pair_count": int(exact["exact_genuine_penetration_pair_count"]),
                "localized_intersections": localize_report(body, exact, neutral_keys),
                "deformation_stretch": assembly.edge_stretch_report(
                    body, neutral_points, posed, set(range(len(neutral_points)))
                ),
                "joint_metrics": joint_metrics(rig),
                "feet": feet,
            }
        )
    assembly.reset_pose(rig)
    return records


def scene_render_snapshot(scene: bpy.types.Scene) -> dict[str, Any]:
    return {
        "camera": scene.camera.name if scene.camera else None,
        "engine": scene.render.engine,
        "resolution_x": int(scene.render.resolution_x),
        "resolution_y": int(scene.render.resolution_y),
        "resolution_percentage": int(scene.render.resolution_percentage),
        "film_transparent": bool(scene.render.film_transparent),
        "filepath": scene.render.filepath,
    }


def restore_scene_render(scene: bpy.types.Scene, snapshot: dict[str, Any]) -> None:
    scene.camera = bpy.data.objects.get(snapshot["camera"]) if snapshot["camera"] else None
    scene.render.engine = str(snapshot["engine"])
    scene.render.resolution_x = int(snapshot["resolution_x"])
    scene.render.resolution_y = int(snapshot["resolution_y"])
    scene.render.resolution_percentage = int(snapshot["resolution_percentage"])
    scene.render.film_transparent = bool(snapshot["film_transparent"])
    scene.render.filepath = str(snapshot["filepath"])


def make_temp_collection() -> bpy.types.Collection:
    existing = bpy.data.collections.get(TEMP_COLLECTION)
    if existing is not None:
        raise RuntimeError("temporary render collection unexpectedly exists")
    collection = bpy.data.collections.new(TEMP_COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    return collection


def make_temp_camera(collection: bpy.types.Collection) -> bpy.types.Object:
    data = bpy.data.cameras.new("KIRA_R21_MOVEMENT_ATTEMPT01_TEMP_CAMERA_DATA")
    camera = bpy.data.objects.new("KIRA_R21_MOVEMENT_ATTEMPT01_TEMP_CAMERA", data)
    collection.objects.link(camera)
    data.type = "ORTHO"
    data.lens = 52.0
    return camera


def make_temp_material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    material = bpy.data.materials.new("KIRA_R21_MOVEMENT_ATTEMPT01_TEMP_" + name)
    material.diffuse_color = color
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Roughness"].default_value = 0.78
    return material


def make_temp_cube(
    collection: bpy.types.Collection,
    name: str,
    center: Sequence[float],
    dimensions: Sequence[float],
    material: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=tuple(float(value) for value in center))
    obj = bpy.context.object
    obj.name = "KIRA_R21_MOVEMENT_ATTEMPT01_TEMP_" + name
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)
    obj.dimensions = tuple(float(value) for value in dimensions)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    obj["temporary_render_evidence_only"] = True
    return obj


def clear_temp_props(collection: bpy.types.Collection, keep_camera: bpy.types.Object) -> None:
    for obj in list(collection.objects):
        if obj != keep_camera:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if isinstance(data, bpy.types.Mesh) and data.users == 0:
                bpy.data.meshes.remove(data)


def render_view(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output_dir: Path,
    label: str,
    location: Vector,
    target: Vector,
    ortho_scale: float,
) -> dict[str, Any]:
    camera.location = location
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = float(max(0.12, ortho_scale))
    scene.camera = camera
    path = output_dir / f"{label}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {
        "label": label,
        "path": project_relative(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def configure_render(scene: bpy.types.Scene, config: dict[str, Any]) -> None:
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = int(config["render_resolution"])
    scene.render.resolution_y = int(config["render_resolution"])
    scene.render.resolution_percentage = int(config["render_percentage"])
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.curvature_ridge_factor = 1.4
    scene.display.shading.curvature_valley_factor = 1.0
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.018, 0.025, 0.035)


def body_bounds(body: bpy.types.Object) -> tuple[Vector, Vector, Vector, float]:
    box = assembly.bounds(assembly.evaluated_vertices(body))
    low = Vector(box["low"])
    high = Vector(box["high"])
    center = (low + high) * 0.5
    return low, high, center, float(high.z - low.z)


def show_seat_props(
    collection: bpy.types.Collection,
    record: dict[str, Any],
    body: bpy.types.Object,
) -> list[bpy.types.Object]:
    seat_metrics = record["support_contact"]
    seat_data = seat_metrics["seat"]
    floor_data = seat_metrics["floor"]
    low, high, _, _ = body_bounds(body)
    seat_mat = make_temp_material("SEAT_MAT", (0.04, 0.16, 0.24, 1.0))
    floor_mat = make_temp_material("FLOOR_MAT", (0.055, 0.065, 0.075, 1.0))
    return [
        make_temp_cube(
            collection,
            "SEAT",
            (
                (seat_data["x_min_m"] + seat_data["x_max_m"]) * 0.5,
                (seat_data["y_min_m"] + seat_data["y_max_m"]) * 0.5,
                float(seat_data["top_z_m"]) - 0.035,
            ),
            (
                float(seat_data["x_max_m"] - seat_data["x_min_m"]),
                float(seat_data["y_max_m"] - seat_data["y_min_m"]),
                0.07,
            ),
            seat_mat,
        ),
        make_temp_cube(
            collection,
            "FLOOR",
            (
                (low.x + high.x) * 0.5,
                (low.y + high.y) * 0.5,
                float(floor_data["top_z_m"]) - 0.015,
            ),
            ((high.x - low.x) + 0.65, (high.y - low.y) + 0.65, 0.03),
            floor_mat,
        ),
    ]


def render_pose_suite(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    collection: bpy.types.Collection,
    owner_dir: Path,
    body: bpy.types.Object,
    rig: bpy.types.Object,
    records: dict[str, dict[str, Any]],
    selected_id: str,
    transition: bpy.types.Action,
    frames: Sequence[int],
    regions: dict[str, list[int]],
) -> list[dict[str, Any]]:
    renders: list[dict[str, Any]] = []

    assembly.reset_pose(rig)
    low, high, center, height = body_bounds(body)
    distance = height * 2.25 + 0.7
    renders.append(
        render_view(
            scene,
            camera,
            owner_dir,
            "neutral_front",
            Vector((center.x, center.y - distance, center.z)),
            center,
            height * 1.08,
        )
    )

    for pose_id in ("left_knee_bend_70", "right_knee_bend_70", "bilateral_knee_bend_65"):
        assembly.apply_rotations(rig, degrees_to_radians(records[pose_id]["rotations_degrees_xyz"]))
        low, high, center, height = body_bounds(body)
        distance = height * 2.15 + 0.7
        renders.append(
            render_view(
                scene,
                camera,
                owner_dir,
                pose_id + "_front_three_quarter",
                Vector((center.x + distance * 0.48, center.y - distance, center.z)),
                center,
                height * 1.10,
            )
        )
        knees = []
        for name in ("lThighBend_05", "rThighBend_021"):
            bone = rig.pose.bones[name]
            knees.append(rig.matrix_world @ bone.tail)
        knee_center = sum(knees, Vector()) / len(knees)
        renders.append(
            render_view(
                scene,
                camera,
                owner_dir,
                pose_id + "_knees_close",
                Vector((knee_center.x + 1.0, knee_center.y - 1.35, knee_center.z + 0.18)),
                knee_center,
                0.62,
            )
        )
        assembly.reset_pose(rig)

    for pose_id in ("seated_open_supported_a", "seated_open_supported_b"):
        record = records[pose_id]
        assembly.apply_rotations(rig, degrees_to_radians(record["rotations_degrees_xyz"]))
        clear_temp_props(collection, camera)
        show_seat_props(collection, record, body)
        low, high, center, height = body_bounds(body)
        distance = height * 2.25 + 0.7
        renders.append(
            render_view(
                scene,
                camera,
                owner_dir,
                "candidate_" + pose_id + "_front_three_quarter",
                Vector((center.x + distance * 0.55, center.y - distance, center.z)),
                center,
                height * 1.12,
            )
        )
        if pose_id == selected_id:
            for suffix, location in {
                "left_profile": Vector((center.x - distance, center.y, center.z)),
                "right_profile": Vector((center.x + distance, center.y, center.z)),
                "rear_three_quarter": Vector((center.x - distance * 0.55, center.y + distance, center.z)),
            }.items():
                renders.append(
                    render_view(
                        scene,
                        camera,
                        owner_dir,
                        "selected_seated_" + suffix,
                        location,
                        center,
                        height * 1.12,
                    )
                )
            foot_points = [
                assembly.region_center(assembly.evaluated_vertices(body), regions["left_foot"]),
                assembly.region_center(assembly.evaluated_vertices(body), regions["right_foot"]),
            ]
            foot_center = sum(foot_points, Vector()) / 2.0
            renders.append(
                render_view(
                    scene,
                    camera,
                    owner_dir,
                    "selected_seated_bilateral_foot_contact_close",
                    Vector((foot_center.x + 1.15, foot_center.y - 1.25, foot_center.z + 0.10)),
                    foot_center,
                    0.68,
                )
            )
        clear_temp_props(collection, camera)
        assembly.reset_pose(rig)

    pose_id = "supine_relaxed_foundation"
    assembly.apply_rotations(rig, degrees_to_radians(records[pose_id]["rotations_degrees_xyz"]))
    low, high, center, height = body_bounds(body)
    support_z = float(records[pose_id]["supine_metrics"]["support_plane_z_m"])
    mat = make_temp_material("SUPINE_SUPPORT_MAT", (0.04, 0.14, 0.21, 1.0))
    make_temp_cube(
        collection,
        "SUPINE_SUPPORT",
        ((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, support_z - 0.04),
        ((high.x - low.x) + 0.35, (high.y - low.y) + 0.35, 0.08),
        mat,
    )
    span = max(high.x - low.x, high.y - low.y, high.z - low.z)
    distance = span * 2.2 + 0.7
    for suffix, location in {
        "side": Vector((center.x + distance, center.y, center.z)),
        "three_quarter": Vector((center.x + distance * 0.55, center.y - distance * 0.70, center.z + distance * 0.28)),
        "top": Vector((center.x, center.y, center.z + distance)),
    }.items():
        renders.append(
            render_view(scene, camera, owner_dir, "supine_" + suffix, location, center, span * 1.12)
        )
    clear_temp_props(collection, camera)
    assembly.reset_pose(rig)

    for pose_id in ("table_reach_foundation", "hand_to_mouth_drink_foundation"):
        record = records[pose_id]
        assembly.apply_rotations(rig, degrees_to_radians(record["rotations_degrees_xyz"]))
        points = assembly.evaluated_vertices(body)
        hand_points = [points[index] for index in regions["left_hand"]]
        hand_center = sum(hand_points, Vector()) / len(hand_points)
        low, high, center, height = body_bounds(body)
        distance = height * 2.20 + 0.7
        if pose_id == "table_reach_foundation":
            table_z = float(record["reach_metrics"]["table_top_z_m"])
            mat = make_temp_material("TABLE_MAT", (0.04, 0.15, 0.22, 1.0))
            make_temp_cube(
                collection,
                "TABLE",
                (hand_center.x, hand_center.y, table_z - 0.03),
                (0.58, 0.52, 0.06),
                mat,
            )
        else:
            cup_mat = make_temp_material("CUP_MAT", (0.12, 0.42, 0.58, 1.0))
            make_temp_cube(
                collection,
                "HAND_HELD_CUP_PROXY",
                hand_center,
                (0.055, 0.055, 0.11),
                cup_mat,
            )
        renders.append(
            render_view(
                scene,
                camera,
                owner_dir,
                pose_id + "_front_three_quarter",
                Vector((center.x + distance * 0.50, center.y - distance, center.z)),
                center,
                height * 1.08,
            )
        )
        renders.append(
            render_view(
                scene,
                camera,
                owner_dir,
                pose_id + "_hand_face_close",
                Vector((hand_center.x + 0.95, hand_center.y - 1.15, hand_center.z + 0.20)),
                hand_center,
                0.62,
            )
        )
        clear_temp_props(collection, camera)
        assembly.reset_pose(rig)

    rig.animation_data_create()
    rig.animation_data.action = transition
    selected_record = records[selected_id]
    for frame in frames:
        bpy.context.scene.frame_set(int(frame))
        bpy.context.view_layer.update()
        if int(frame) == int(frames[2]):
            clear_temp_props(collection, camera)
            show_seat_props(collection, selected_record, body)
        low, high, center, height = body_bounds(body)
        distance = height * 2.20 + 0.7
        renders.append(
            render_view(
                scene,
                camera,
                owner_dir,
                f"sit_stand_transition_frame_{int(frame):03d}",
                Vector((center.x + distance * 0.50, center.y - distance, center.z)),
                center,
                height * 1.10,
            )
        )
    clear_temp_props(collection, camera)
    assembly.reset_pose(rig)
    return renders


def cleanup_temp(collection: bpy.types.Collection, camera: bpy.types.Object) -> None:
    clear_temp_props(collection, camera)
    camera_data = camera.data
    bpy.data.objects.remove(camera, do_unlink=True)
    if camera_data.users == 0:
        bpy.data.cameras.remove(camera_data)
    for material in list(bpy.data.materials):
        if material.name.startswith("KIRA_R21_MOVEMENT_ATTEMPT01_TEMP_") and material.users == 0:
            bpy.data.materials.remove(material)
    if collection.users == 0 or len(collection.objects) == 0:
        bpy.data.collections.remove(collection)


def make_manifest(paths: Iterable[Path], manifest_path: Path) -> dict[str, Any]:
    entries = []
    for path in sorted({item.resolve() for item in paths}, key=lambda item: str(item).lower()):
        if path == manifest_path.resolve() or not path.is_file():
            continue
        entries.append(
            {
                "path": project_relative(path),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schema_version": 1,
        "append_only": True,
        "attempt": "attempt_01",
        "files_excluding_this_manifest": entries,
    }
    write_json(manifest_path, manifest)
    return manifest


def run(config_path: Path) -> int:
    config, paths = load_and_verify_config(config_path)
    source_hash_before = sha256_file(paths["source_blend"])
    source_evidence = json.loads(paths["source_evidence"].read_text(encoding="utf-8"))
    if source_evidence["output"]["blend_sha256"] != source_hash_before:
        raise RuntimeError("source evidence does not bind the configured source Blend")
    r19_evidence = json.loads(paths["r19_movement_evidence"].read_text(encoding="utf-8"))
    if int(r19_evidence["neutral_exact_self_intersection_baseline"]) != 29:
        raise RuntimeError("R19 Attempt-06 neutral movement baseline drifted")

    paths["recovery_output"].mkdir(parents=True, exist_ok=False)
    paths["owner_output"].mkdir(parents=True, exist_ok=False)

    body, rig, nails = find_components(config)
    assembly.reset_pose(rig)
    mesh_before = inherited_mesh_snapshot()
    rig_before = prior.rig_immutable_signature(rig)
    inherited_actions_before = inherited_action_snapshot()
    neutral_coordinate_before = evaluated_coordinate_sha256(body)
    neutral_points = assembly.evaluated_vertices(body)
    neutral_exact = assembly.exact_body_intersection_report(body)
    neutral_count = int(neutral_exact["exact_genuine_penetration_pair_count"])
    if neutral_count != int(config["expected_neutral_exact_pair_count"]):
        raise RuntimeError(
            f"R21 neutral exact-pair baseline drifted: {neutral_count} != {config['expected_neutral_exact_pair_count']}"
        )
    neutral_keys = {pair_key(pair) for pair in neutral_exact["pairs"]}
    regions = prior.region_maps(body)

    records: dict[str, dict[str, Any]] = {}
    for item in config["seated_candidates"]:
        records[str(item["id"])] = pose_record(
            str(item["id"]),
            item["rotations_degrees_xyz"],
            body,
            rig,
            nails,
            neutral_points,
            neutral_keys,
            regions,
            config,
        )
    for pose_id, rotations in config["fixed_pose_actions"].items():
        records[str(pose_id)] = pose_record(
            str(pose_id),
            rotations,
            body,
            rig,
            nails,
            neutral_points,
            neutral_keys,
            regions,
            config,
        )

    seated_scores = {}
    for item in config["seated_candidates"]:
        pose_id = str(item["id"])
        score, parts = seated_score(records[pose_id], neutral_count)
        seated_scores[pose_id] = {"score": float(score), "parts": parts}
    selected_id = min(seated_scores, key=lambda key: (seated_scores[key]["score"], key))

    new_actions = {}
    for pose_id, record in records.items():
        action = author_pose_action(
            rig,
            pose_id,
            record["rotations_degrees_xyz"],
            str(config["candidate_id"]),
        )
        action["selected_seated_candidate"] = bool(pose_id == selected_id)
        new_actions[action.name] = action_signature(action)
    transition_action = author_transition_action(
        rig,
        records[selected_id],
        [int(value) for value in config["transition_frames"]],
        str(config["candidate_id"]),
    )
    new_actions[transition_action.name] = action_signature(transition_action)
    transition_records = transition_audit(
        transition_action,
        [int(value) for value in config["transition_frames"]],
        body,
        rig,
        neutral_points,
        neutral_keys,
        regions,
    )

    scene = bpy.context.scene
    render_snapshot = scene_render_snapshot(scene)
    temp_collection = make_temp_collection()
    camera = make_temp_camera(temp_collection)
    configure_render(scene, config)
    renders = render_pose_suite(
        scene,
        camera,
        temp_collection,
        paths["owner_output"],
        body,
        rig,
        records,
        selected_id,
        transition_action,
        [int(value) for value in config["transition_frames"]],
        regions,
    )
    cleanup_temp(temp_collection, camera)
    restore_scene_render(scene, render_snapshot)
    assembly.reset_pose(rig)

    mesh_after = inherited_mesh_snapshot()
    inherited_actions_after = inherited_action_snapshot()
    rig_after = prior.rig_immutable_signature(rig)
    neutral_coordinate_after = evaluated_coordinate_sha256(body)
    mesh_mismatches = sorted(
        name
        for name in set(mesh_before) | set(mesh_after)
        if mesh_before.get(name) != mesh_after.get(name)
    )
    if mesh_mismatches:
        raise RuntimeError(f"inherited mesh state drifted: {mesh_mismatches}")
    if inherited_actions_after != inherited_actions_before:
        raise RuntimeError("one or more inherited actions changed")
    if rig_after != rig_before:
        raise RuntimeError("native rest-rig changed")
    if neutral_coordinate_after != neutral_coordinate_before:
        raise RuntimeError("neutral evaluated body coordinates did not restore exactly")
    if bpy.data.collections.get(TEMP_COLLECTION) is not None:
        raise RuntimeError("temporary render collection survived cleanup")
    if any(obj.name.startswith("KIRA_R21_MOVEMENT_ATTEMPT01_TEMP_") for obj in bpy.data.objects):
        raise RuntimeError("temporary render object survived cleanup")

    rig.animation_data_create()
    rig.animation_data.action = None
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    blend_path = paths["owner_output"] / "KIRA_R21_BALD_PRIVATE_INACTIVE_ACTION_ONLY_MOVEMENT_ATTEMPT01.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)

    source_hash_after = sha256_file(paths["source_blend"])
    if source_hash_after != source_hash_before:
        raise RuntimeError("source Blend changed during append-only movement authoring")

    # Reopen the append-only output and re-prove the protected body/rig and
    # unassigned action state.  This is still the same single bounded run.
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    body_reopen, rig_reopen, _ = find_components(config)
    assembly.reset_pose(rig_reopen)
    mesh_reopen = inherited_mesh_snapshot()
    inherited_actions_reopen = inherited_action_snapshot()
    reopen_new_actions = {
        action.name: action_signature(action)
        for action in sorted(bpy.data.actions, key=lambda item: item.name)
        if action.name.startswith(ACTION_PREFIX)
    }
    if mesh_reopen != mesh_before:
        raise RuntimeError("protected mesh state changed after save/reopen")
    if inherited_actions_reopen != inherited_actions_before:
        raise RuntimeError("inherited action state changed after save/reopen")
    if prior.rig_immutable_signature(rig_reopen) != rig_before:
        raise RuntimeError("native rest-rig changed after save/reopen")
    if evaluated_coordinate_sha256(body_reopen) != neutral_coordinate_before:
        raise RuntimeError("neutral evaluated body coordinates changed after save/reopen")
    if rig_reopen.animation_data and rig_reopen.animation_data.action is not None:
        raise RuntimeError("new movement action remained assigned after reopen")
    expected_new_names = set(new_actions) | {transition_action.name}
    if set(reopen_new_actions) != expected_new_names:
        raise RuntimeError("new action inventory changed after save/reopen")

    exact_dir = paths["recovery_output"] / "exact_intersections"
    localized_dir = paths["recovery_output"] / "localized_intersections"
    exact_dir.mkdir()
    localized_dir.mkdir()
    write_json(exact_dir / "neutral.json", neutral_exact)
    write_json(localized_dir / "neutral.json", localize_report(body_reopen, neutral_exact, neutral_keys))
    compact_pose_records = {}
    for pose_id, record in records.items():
        exact_path = exact_dir / f"{pose_id}.json"
        localized_path = localized_dir / f"{pose_id}.json"
        write_json(exact_path, record["exact_intersections"])
        write_json(localized_path, record["localized_intersections"])
        compact = dict(record)
        compact.pop("exact_intersections")
        compact.pop("localized_intersections")
        compact["exact_intersection_report"] = project_relative(exact_path)
        compact["exact_intersection_report_sha256"] = sha256_file(exact_path)
        compact["localized_intersection_report"] = project_relative(localized_path)
        compact["localized_intersection_report_sha256"] = sha256_file(localized_path)
        compact_pose_records[pose_id] = compact
    transition_path = paths["recovery_output"] / "SIT_STAND_TRANSITION_AUDIT.json"
    write_json(transition_path, transition_records)

    evidence = {
        "schema_version": 1,
        "artifact_kind": "KIRA_R21_ACTION_ONLY_MOVEMENT_CORRECTION_BUILD_EVIDENCE",
        "created_utc": utc_now(),
        "status": "PRIVATE_INACTIVE_ONE_BOUNDED_ACTION_ONLY_MOVEMENT_ATTEMPT_PENDING_VISUAL_REVIEW",
        "candidate_id": config["candidate_id"],
        "scope": config["scope"],
        "source": {
            "blend": project_relative(paths["source_blend"]),
            "sha256_before": source_hash_before,
            "sha256_after": source_hash_after,
            "unchanged": source_hash_after == source_hash_before,
            "source_evidence": project_relative(paths["source_evidence"]),
            "source_evidence_sha256": sha256_file(paths["source_evidence"]),
        },
        "preflight": {
            "body_object": body.name,
            "body_geometry_uv_sha256": assembly.mesh_geometry_uv_signature(body_reopen),
            "body_positive_weight_assignment_sha256": prior.weight_signature(body_reopen),
            "rig_object": rig_reopen.name,
            "rig_joint_count": len(rig_reopen.data.bones),
            "rig_rest_sha256": prior.rig_immutable_signature(rig_reopen),
            "protected_mesh_object_count": len(mesh_before),
            "inherited_action_count": len(inherited_actions_before),
            "neutral_evaluated_coordinate_sha256": neutral_coordinate_before,
            "neutral_exact_pair_count": neutral_count,
            "exactly_two_seated_candidates": len(config["seated_candidates"]) == 2,
            "open_search_used": False,
        },
        "r19_attempt06_root_cause": {
            "selected_action": "KIRA_R19_ATTEMPT05_SEATED_OPEN_HIP_A",
            "neutral_exact_pairs": 29,
            "seated_exact_pairs": 32,
            "seated_maximum_edge_ratio": 4.042985449,
            "visible_failure": "stiff posture and one incompletely planted heel/foot",
            "repair_direction": "greater bilateral proximal-leg clearance with bounded symmetric support and action-only preservation",
        },
        "neutral": {
            "exact_intersection_report": project_relative(exact_dir / "neutral.json"),
            "exact_intersection_report_sha256": sha256_file(exact_dir / "neutral.json"),
            "localized_intersection_report": project_relative(localized_dir / "neutral.json"),
            "localized_intersection_report_sha256": sha256_file(localized_dir / "neutral.json"),
        },
        "pose_records": compact_pose_records,
        "seated_selection": {
            "candidates": seated_scores,
            "selected_id": selected_id,
            "selection_is_engineering_only_not_owner_approval": True,
        },
        "sit_stand_transition": {
            "action": transition_action.name,
            "audit": project_relative(transition_path),
            "audit_sha256": sha256_file(transition_path),
            "keyframes": [int(value) for value in config["transition_frames"]],
            "foot_lock_or_inverse_kinematics_claimed": False,
            "biomechanical_acceptance_claimed": False,
        },
        "new_actions_after_reopen": reopen_new_actions,
        "renders": renders,
        "protected_verification": {
            "all_inherited_mesh_states_exact_after_save_reopen": mesh_reopen == mesh_before,
            "body_rest_geometry_uv_weights_exact": True,
            "face_eyes_brows_pelvis_nails_skin_material_bindings_exact": True,
            "native_rest_rig_exact_after_save_reopen": True,
            "all_inherited_actions_exact_after_save_reopen": True,
            "neutral_evaluated_coordinates_exact_after_save_reopen": True,
            "new_actions_unassigned_after_save_reopen": True,
            "temporary_camera_support_table_cup_objects_absent_from_saved_blend": True,
        },
        "output": {
            "blend": project_relative(blend_path),
            "blend_sha256": sha256_file(blend_path),
            "blend_bytes": blend_path.stat().st_size,
        },
        "truth_boundary": {
            "owner_visual_approval_required": True,
            "movement_actions_are_foundations_not_full_biological_function_proof": True,
            "seat_or_floor_contact_is_not_pressure_or_soft_tissue_simulation": True,
            "hand_to_mouth_is_not_eating_swallowing_or_drinking_proof": True,
            "activation_assignment_export_publication_performed": False,
        },
    }
    evidence_path = paths["recovery_output"] / "BUILD_EVIDENCE.json"
    write_json(evidence_path, evidence)
    owner_readme = paths["owner_output"] / "OWNER_REVIEW_README.md"
    owner_readme.write_text(
        "# Kira R21 action-only movement Attempt 01\n\n"
        "Private, inactive, unassigned, unpublished owner-review evidence. "
        "The exact accepted rest body, face, eyes, brows, pelvis, nails, skin, "
        "weights, and native rest rig are unchanged. Only append-only actions "
        "were retained in the Blend.\n\n"
        f"Engineering-selected seated candidate: `{selected_id}`. This selection "
        "is not Robert's visual approval. Review neutral, unilateral/bilateral "
        "knee, both seated candidates, selected seat/foot contact, supine, "
        "table reach, hand-to-mouth, and six sit/stand transition frames.\n\n"
        "No pose proves comfort, soft-tissue pressure, eating, swallowing, "
        "drinking, or complete biological movement.\n",
        encoding="utf-8",
    )
    rollback = paths["recovery_output"] / "ROLLBACK.md"
    rollback.write_text(
        "# Rollback\n\n"
        "Do not assign or activate the Attempt-01 movement Blend. The exact "
        "source remains unchanged at:\n\n"
        f"`{project_relative(paths['source_blend'])}`\n\n"
        f"SHA-256: `{source_hash_before}`\n\n"
        "Rollback is therefore selection-only: continue using the source Blend "
        "and ignore/delete no evidence automatically.\n",
        encoding="utf-8",
    )
    manifest_path = paths["recovery_output"] / "PACKAGE_MANIFEST.json"
    package_files = [
        blend_path,
        evidence_path,
        transition_path,
        rollback,
        owner_readme,
        *[Path(item["path"]) if Path(item["path"]).is_absolute() else PROJECT_ROOT / item["path"] for item in renders],
        *exact_dir.glob("*.json"),
        *localized_dir.glob("*.json"),
    ]
    make_manifest(package_files, manifest_path)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve()
    try:
        return run(config_path)
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "status": "FAILED_ONE_BOUNDED_ACTION_ONLY_MOVEMENT_ATTEMPT",
            "created_utc": utc_now(),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        output = PROJECT_ROOT / (
            "RecoverySprint/continuation_20260802/"
            "kira_r21_action_only_movement_correction/attempt_01_failure.json"
        )
        if not output.exists():
            write_json(output, failure)
        print(json.dumps(failure, indent=2, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
