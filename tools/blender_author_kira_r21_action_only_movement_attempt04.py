#!/usr/bin/env python3
"""Deferred Blender worker for Kira R21 movement Attempt 04.

The checked-in prepared config cannot authorize execution.  This worker exits
before output creation or Blender mutation unless a separate exact-hash release
record confirms that pelvic/nail priorities are complete and binds the final
source Blend/evidence.  When released, it authors append-only actions, creates
temporary evidence props, audits every declared phase, renders the declared
views, removes all temporary objects, saves one private inactive Blend, reopens
it, and re-proves the protected source state.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import traceback
from typing import Any, Iterable, Sequence

import bpy
from mathutils import Vector


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_author_kira_r21_action_only_movement_attempt01 as movement_base  # noqa: E402
import blender_author_kira_r21_brow_only_attempt01 as brow  # noqa: E402
import kira_r21_movement_attempt04_contract as contract  # noqa: E402


DEFAULT_CONFIG = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r21_action_only_movement_correction/"
    "MOVEMENT_CONFIG_ATTEMPT_04_PREPARED.json"
)
FAILURE_PATH = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r21_action_only_movement_correction/"
    "attempt_04_failure.json"
)
TEMP_COLLECTION = "KIRA_R21_MOVEMENT_ATTEMPT04_TEMP_EVIDENCE_ONLY"
TEMP_PREFIX = "KIRA_R21_MOVEMENT_ATTEMPT04_TEMP_"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--release", default="")
    return parser.parse_args(argv)


def project_relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def all_release_bone_names(config: dict[str, Any]) -> set[str]:
    result = {
        str(config["bone_map"][key])
        for key in ("hip", "pelvis", "abdomen_lower", "abdomen_upper", "chest_lower", "chest_upper")
    }
    for side in ("left", "right"):
        side_map = config["bone_map"][side]
        result.update(str(side_map[key]) for key in ("shoulder", "forearm", "hand", "thigh", "shin", "foot"))
        for digit in ("thumb", "index", "middle", "ring", "pinky"):
            result.update(str(value) for value in side_map[digit])
    return result


def validate_blender_source(
    config: dict[str, Any], release: dict[str, Any], source_path: Path
) -> tuple[bpy.types.Object, bpy.types.Object, list[bpy.types.Object]]:
    if Path(bpy.data.filepath).resolve() != source_path.resolve():
        raise RuntimeError("Blender was not opened with the exact released source Blend")
    body = bpy.data.objects.get(str(release["body_object"]))
    rig = bpy.data.objects.get(str(release["rig_object"]))
    if body is None or body.type != "MESH":
        raise RuntimeError("released body object is absent")
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError("released rig object is absent")
    if len(rig.data.bones) != int(config["protected_component_contract"]["expected_rig_joint_count"]):
        raise RuntimeError("released rig joint count drifted")
    missing = sorted(all_release_bone_names(config) - set(rig.pose.bones.keys()))
    if missing:
        raise RuntimeError(f"movement bone inventory is incomplete: {missing}")
    if brow.mesh_geometry_digest(body) != str(release["body_geometry_uv_sha256"]):
        raise RuntimeError("released body geometry/UV hash mismatch")
    if brow.weight_digest(body) != str(release["body_positive_weight_assignment_sha256"]):
        raise RuntimeError("released body weight hash mismatch")
    if brow.armature_digest(rig) != str(release["rig_rest_sha256"]):
        raise RuntimeError("released rest-rig hash mismatch")
    nails = sorted(
        [obj for obj in bpy.data.objects if obj.type == "MESH" and bool(obj.get("nail_component"))],
        key=lambda item: item.name,
    )
    if len(nails) != 20:
        raise RuntimeError(f"released body must retain 20 nail components; found {len(nails)}")
    return body, rig, nails


def reset_pose(rig: bpy.types.Object) -> None:
    rig.animation_data_create()
    rig.animation_data.action = None
    movement_base.assembly.reset_pose(rig)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def author_sequence_action(
    config: dict[str, Any], sequence: dict[str, Any], rig: bpy.types.Object
) -> bpy.types.Action:
    prefix = str(config["future_outputs"]["action_prefix"])
    name = prefix + str(sequence["id"]).upper()
    if bpy.data.actions.get(name) is not None:
        raise RuntimeError(f"new action collision: {name}")
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = action
    for phase in sequence["phases"]:
        movement_base.assembly.reset_pose(rig)
        expanded = contract.generate_phase_pose(config, phase)
        frame = int(phase["frame"])
        for bone_name, values in expanded["rotations_degrees_xyz"].items():
            bone = rig.pose.bones.get(bone_name)
            if bone is None:
                raise RuntimeError(f"action bone is absent: {bone_name}")
            bone.rotation_mode = "XYZ"
            bone.rotation_euler = tuple(math.radians(float(value)) for value in values)
            bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=bone_name)
        for bone_name, values in expanded["locations_m_xyz"].items():
            bone = rig.pose.bones.get(bone_name)
            if bone is None:
                raise RuntimeError(f"location bone is absent: {bone_name}")
            bone.location = tuple(float(value) for value in values)
            bone.keyframe_insert(data_path="location", frame=frame, group=bone_name)
    try:
        for curve in action.fcurves:
            for point in curve.keyframe_points:
                point.interpolation = "BEZIER"
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"
    except (AttributeError, RuntimeError):
        pass
    action["candidate_id"] = str(config["candidate_id"])
    action["sequence_id"] = str(sequence["id"])
    action["action_only_movement_attempt"] = 4
    action["private_owner_review_only"] = True
    action["inactive"] = True
    action["owner_approved"] = False
    action["runtime_assignment_allowed"] = False
    action["movement_evidence_not_biological_function_proof"] = True
    reset_pose(rig)
    return action


def body_bounds(body: bpy.types.Object) -> tuple[Vector, Vector, Vector, Vector]:
    raw = movement_base.assembly.bounds(movement_base.assembly.evaluated_vertices(body))
    low = Vector(raw["low"])
    high = Vector(raw["high"])
    return low, high, (low + high) * 0.5, high - low


def make_temp_collection() -> bpy.types.Collection:
    if bpy.data.collections.get(TEMP_COLLECTION) is not None:
        raise RuntimeError("Attempt-04 temporary collection already exists")
    collection = bpy.data.collections.new(TEMP_COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    return collection


def relink_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def make_material(name: str, color: Sequence[float]) -> bpy.types.Material:
    material = bpy.data.materials.new(TEMP_PREFIX + name)
    material.diffuse_color = tuple(float(value) for value in color)
    return material


def make_box(
    collection: bpy.types.Collection,
    name: str,
    center: Vector,
    dimensions: Sequence[float],
    material: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=center)
    obj = bpy.context.object
    obj.name = TEMP_PREFIX + name
    relink_to_collection(obj, collection)
    obj.dimensions = tuple(float(value) for value in dimensions)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    obj["temporary_evidence_only"] = True
    return obj


def make_cylinder(
    collection: bpy.types.Collection,
    name: str,
    center: Vector,
    dimensions: Sequence[float],
    material: bpy.types.Material,
) -> bpy.types.Object:
    radius = max(float(dimensions[0]), float(dimensions[1])) * 0.5
    depth = float(dimensions[2])
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=depth, location=center)
    obj = bpy.context.object
    obj.name = TEMP_PREFIX + name
    relink_to_collection(obj, collection)
    obj.data.materials.append(material)
    obj["temporary_evidence_only"] = True
    return obj


def anchor_center(spec: dict[str, Any], low: Vector, span: Vector) -> Vector:
    fractions = Vector(tuple(float(value) for value in spec["anchor_fraction_xyz"]))
    return Vector((low.x + span.x * fractions.x, low.y + span.y * fractions.y, low.z + span.z * fractions.z))


def needed_prop_names(sequence: dict[str, Any]) -> set[str]:
    names = {str(sequence.get("primary_prop", ""))} - {""}
    for phase in sequence["phases"]:
        for item in phase.get("contacts", []):
            names.add(str(item["prop"]))
    category = str(sequence.get("category", ""))
    if sequence["id"] == "handwashing_complete":
        names.update(("basin", "faucet", "soap", "towel"))
    elif sequence["id"] == "shower_entry_wash_exit":
        names.update(("shower_floor", "shower_control", "shower_grab_bar"))
    elif sequence["id"] == "bath_entry_supported_sit_rise_exit":
        names.update(("bath", "bath_grab_bar"))
    elif category == "door":
        names.add("door")
    return names


def create_sequence_props(
    config: dict[str, Any],
    sequence: dict[str, Any],
    collection: bpy.types.Collection,
    low: Vector,
    span: Vector,
) -> dict[str, bpy.types.Object]:
    material = make_material(str(sequence["id"]) + "_PROP", (0.08, 0.38, 0.52, 1.0))
    values: dict[str, bpy.types.Object] = {}
    for name in sorted(needed_prop_names(sequence)):
        spec = config["props"][name]
        center = anchor_center(spec, low, span)
        shape = str(spec["shape"])
        dimensions = spec["dimensions_m"]
        if shape == "cylinder":
            values[name] = make_cylinder(collection, name, center, dimensions, material)
        else:
            values[name] = make_box(collection, name, center, dimensions, material)
        if name == "door":
            handle_center = center + Vector((float(dimensions[0]) * 0.35, -float(dimensions[1]), 0.04))
            values["door:handle"] = make_cylinder(
                collection, "DOOR_HANDLE", handle_center, (0.035, 0.035, 0.18), material
            )
            values["door:handle"].rotation_euler.x = math.radians(90.0)
    return values


def remove_sequence_props(
    props: dict[str, bpy.types.Object], materials_before: set[str]
) -> None:
    removed: set[int] = set()
    for obj in props.values():
        pointer = int(obj.as_pointer())
        if pointer in removed:
            continue
        removed.add(pointer)
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if isinstance(data, bpy.types.Mesh) and data.users == 0:
            bpy.data.meshes.remove(data)
    for material in list(bpy.data.materials):
        if material.name not in materials_before and material.name.startswith(TEMP_PREFIX) and material.users == 0:
            bpy.data.materials.remove(material)


def hand_anchor(rig: bpy.types.Object, config: dict[str, Any], side: str) -> Vector:
    bone = rig.pose.bones[str(config["bone_map"][side]["hand"])]
    return rig.matrix_world @ bone.tail


def set_phase_prop_state(
    phase: dict[str, Any],
    sequence: dict[str, Any],
    props: dict[str, bpy.types.Object],
    rig: bpy.types.Object,
    config: dict[str, Any],
) -> None:
    primary = str(sequence.get("primary_prop", ""))
    if primary and primary in props:
        mode = str(phase.get("prop_mode", "fixed"))
        if mode == "follow_left_grip":
            props[primary].location = hand_anchor(rig, config, "left")
        elif mode == "follow_right_grip":
            props[primary].location = hand_anchor(rig, config, "right")
        elif mode == "follow_bilateral_grip":
            props[primary].location = (
                hand_anchor(rig, config, "left") + hand_anchor(rig, config, "right")
            ) * 0.5
    if "door:handle" in props:
        props["door:handle"].rotation_euler.z = math.radians(float(phase.get("door_handle_turn_degrees", 0.0)))
    if "door" in props:
        props["door"].rotation_euler.z = math.radians(float(phase.get("door_angle_degrees", 0.0)))
    bpy.context.view_layer.update()


def world_aabb(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[axis] for point in corners) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in corners) for axis in range(3))),
    )


def point_aabb_distance(point: Vector, low: Vector, high: Vector) -> float:
    squared = 0.0
    for axis in range(3):
        if point[axis] < low[axis]:
            squared += float(low[axis] - point[axis]) ** 2
        elif point[axis] > high[axis]:
            squared += float(point[axis] - high[axis]) ** 2
    return math.sqrt(squared)


def hand_landmarks(
    rig: bpy.types.Object, config: dict[str, Any], side: str
) -> dict[str, Vector]:
    side_map = config["bone_map"][side]
    names = {
        "palm": str(side_map["hand"]),
        "thumb_tip": str(side_map["thumb"][-1]),
        "index_tip": str(side_map["index"][-1]),
        "middle_tip": str(side_map["middle"][-1]),
        "ring_tip": str(side_map["ring"][-1]),
        "pinky_tip": str(side_map["pinky"][-1]),
    }
    return {label: rig.matrix_world @ rig.pose.bones[name].tail for label, name in names.items()}


def contact_audit(
    config: dict[str, Any],
    phase: dict[str, Any],
    props: dict[str, bpy.types.Object],
    rig: bpy.types.Object,
) -> list[dict[str, Any]]:
    maximum = float(config["acceptance_gates"]["hand_prop_contact_distance_m"]["maximum"])
    records = []
    for request in phase.get("contacts", []):
        prop_key = "door:handle" if request.get("surface") == "handle" else str(request["prop"])
        prop = props[prop_key]
        low, high = world_aabb(prop)
        side = str(request["hand"])
        points = hand_landmarks(rig, config, side)
        distances = {name: point_aabb_distance(point, low, high) for name, point in points.items()}
        touching_digits = sorted(
            name for name, distance in distances.items() if name != "palm" and distance <= maximum
        )
        grip = float(phase.get("motion", {}).get(side, {}).get("grip", 0.0))
        grip_pass = (
            not bool(request.get("grip"))
            or (
                grip >= float(config["acceptance_gates"]["minimum_finger_closure_for_grip"])
                and "thumb_tip" in touching_digits
                and len(set(touching_digits) - {"thumb_tip"}) >= 3
            )
        )
        records.append(
            {
                "prop": str(request["prop"]),
                "surface": request.get("surface"),
                "hand": side,
                "grip_requested": bool(request.get("grip")),
                "configured_grip_closure": grip,
                "landmark_distance_m": {name: round(value, 9) for name, value in distances.items()},
                "touching_digits": touching_digits,
                "distance_gate_pass": min(distances.values()) <= maximum,
                "grip_gate_pass": grip_pass,
            }
        )
    return records


def support_proxy(
    body: bpy.types.Object,
    posed: list[Vector],
    regions: dict[str, list[int]],
    phase: dict[str, Any],
) -> dict[str, Any]:
    planted = phase.get("planted_foot")
    if planted is None and phase.get("support") not in ("bilateral_feet", "bath_seat_and_bilateral_feet"):
        return {"required": False, "method": "evaluated_body_geometry_centroid_projection"}
    sides = ("left", "right") if planted in ("bilateral", None) or phase.get("support") else (str(planted),)
    support_points: list[Vector] = []
    foot_centers: dict[str, list[float]] = {}
    for side in sides:
        points = [posed[index] for index in regions[f"{side}_foot"]]
        low_z = min(point.z for point in points)
        sole = [point for point in points if point.z <= low_z + 0.015]
        support_points.extend(sole)
        center = sum(sole, Vector()) / max(1, len(sole))
        foot_centers[side] = [float(value) for value in center]
    centroid = sum(posed, Vector()) / len(posed)
    if not support_points:
        return {"required": True, "pass": False, "reason": "no sole support points"}
    low_x = min(point.x for point in support_points)
    high_x = max(point.x for point in support_points)
    low_y = min(point.y for point in support_points)
    high_y = max(point.y for point in support_points)
    margin = 0.01
    inside = low_x - margin <= centroid.x <= high_x + margin and low_y - margin <= centroid.y <= high_y + margin
    return {
        "required": True,
        "pass": bool(inside),
        "method": "evaluated_body_geometry_centroid_projection_not_biological_mass_claim",
        "geometry_centroid_world_m": [float(value) for value in centroid],
        "support_bounds_xy_m": [low_x, high_x, low_y, high_y],
        "foot_centers_world_m": foot_centers,
    }


def motion_ranges(
    config: dict[str, Any], sequence: dict[str, Any]
) -> dict[str, dict[str, float]]:
    values: dict[str, dict[str, list[float]]] = {
        side: {joint: [] for joint in ("shoulder", "forearm", "hand")}
        for side in ("left", "right")
    }
    for phase in sequence["phases"]:
        pose = contract.generate_phase_pose(config, phase)["rotations_degrees_xyz"]
        for side in ("left", "right"):
            for joint in ("shoulder", "forearm", "hand"):
                bone = str(config["bone_map"][side][joint])
                values[side][joint].append(max(abs(float(value)) for value in pose[bone]))
    return {
        side: {
            joint: max(samples) - min(samples) if samples else 0.0
            for joint, samples in joints.items()
        }
        for side, joints in values.items()
    }


def audit_sequence(
    config: dict[str, Any],
    sequence: dict[str, Any],
    action: bpy.types.Action,
    body: bpy.types.Object,
    rig: bpy.types.Object,
    nails: list[bpy.types.Object],
    neutral_points: list[Vector],
    neutral_keys: set[str],
    regions: dict[str, list[int]],
    collection: bpy.types.Collection,
) -> tuple[list[dict[str, Any]], dict[str, bpy.types.Object]]:
    low, _, _, span = body_bounds(body)
    materials_before = {material.name for material in bpy.data.materials}
    props = create_sequence_props(config, sequence, collection, low, span)
    records = []
    rig.animation_data.action = action
    planted_reference: dict[str, Vector] = {}
    for phase in sequence["phases"]:
        bpy.context.scene.frame_set(int(phase["frame"]))
        bpy.context.view_layer.update()
        set_phase_prop_state(phase, sequence, props, rig, config)
        posed = movement_base.assembly.evaluated_vertices(body)
        exact = movement_base.assembly.exact_body_intersection_report(body)
        localized = movement_base.localize_report(body, exact, neutral_keys)
        body_nail = movement_base.assembly.exact_cross_intersections(body, nails)
        prop_meshes = sorted(
            {obj for obj in props.values() if obj.type == "MESH"}, key=lambda item: item.name
        )
        body_prop = movement_base.assembly.exact_cross_intersections(body, prop_meshes)
        support = support_proxy(body, posed, regions, phase)
        drift: dict[str, Any] = {}
        for side, center_values in support.get("foot_centers_world_m", {}).items():
            center = Vector(center_values)
            reference = planted_reference.setdefault(side, center.copy())
            drift[side] = {
                "world_m": [float(value) for value in center],
                "drift_m": float((center - reference).length),
                "vertical_drift_m": abs(float(center.z - reference.z)),
            }
        records.append(
            {
                "phase": str(phase["id"]),
                "frame": int(phase["frame"]),
                "exact_self_intersections": exact,
                "localized_intersections": localized,
                "exact_body_nail_intersections": body_nail,
                "exact_body_prop_intersections": body_prop,
                "contacts": contact_audit(config, phase, props, rig),
                "support_proxy": support,
                "planted_foot_drift": drift,
                "deformation_stretch": movement_base.assembly.edge_stretch_report(
                    body, neutral_points, posed, set(range(len(neutral_points)))
                ),
                "generated_pose": contract.generate_phase_pose(config, phase),
            }
        )
    rig.animation_data.action = None
    movement_base.assembly.reset_pose(rig)
    # The caller renders before removing these sequence-local props.
    props["__materials_before__"] = materials_before  # type: ignore[assignment]
    return records, props


def compact_audit_records(
    records: list[dict[str, Any]],
    exact_dir: Path,
    localized_dir: Path,
    sequence_id: str,
) -> list[dict[str, Any]]:
    compact = []
    for record in records:
        phase_id = str(record["phase"])
        stem = f"{sequence_id}__{phase_id}"
        exact_path = exact_dir / f"{stem}.json"
        localized_path = localized_dir / f"{stem}.json"
        write_json(exact_path, record["exact_self_intersections"])
        write_json(localized_path, record["localized_intersections"])
        value = dict(record)
        value.pop("exact_self_intersections")
        value.pop("localized_intersections")
        value["exact_self_intersection_report"] = project_relative(exact_path)
        value["exact_self_intersection_report_sha256"] = contract.sha256_file(exact_path)
        value["localized_intersection_report"] = project_relative(localized_path)
        value["localized_intersection_report_sha256"] = contract.sha256_file(localized_path)
        compact.append(value)
    return compact


def phase_gate_summary(config: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    gates = config["acceptance_gates"]
    failures = []
    for record in records:
        label = f"{record['phase']}@{record['frame']}"
        if int(record["localized_intersections"]["pose_induced_or_pose_exposed_pair_count"]) > int(gates["maximum_pose_induced_or_exposed_self_intersection_pairs"]):
            failures.append(label + ":pose_induced_self_intersections")
        if int(record["exact_body_nail_intersections"]["total_exact_genuine_body_nail_triangle_pair_count"]) > int(gates["maximum_body_nail_intersection_pairs"]):
            failures.append(label + ":body_nail_intersections")
        if int(record["exact_body_prop_intersections"]["total_exact_genuine_body_nail_triangle_pair_count"]) > int(gates["maximum_body_prop_penetration_pairs"]):
            failures.append(label + ":body_prop_intersections")
        for contact in record["contacts"]:
            if not contact["distance_gate_pass"]:
                failures.append(label + f":{contact['hand']}_{contact['prop']}_distance")
            if not contact["grip_gate_pass"]:
                failures.append(label + f":{contact['hand']}_{contact['prop']}_grip")
        if record["support_proxy"].get("required") and not record["support_proxy"].get("pass"):
            failures.append(label + ":support_proxy")
        for side, drift in record["planted_foot_drift"].items():
            if float(drift["drift_m"]) > float(gates["maximum_planted_foot_drift_m"]):
                failures.append(label + f":{side}_planted_foot_drift")
            if float(drift["vertical_drift_m"]) > float(gates["maximum_planted_foot_vertical_drift_m"]):
                failures.append(label + f":{side}_planted_foot_vertical_drift")
    return {"pass": not failures, "failures": failures}


def make_camera(collection: bpy.types.Collection) -> bpy.types.Object:
    data = bpy.data.cameras.new(TEMP_PREFIX + "CAMERA_DATA")
    camera = bpy.data.objects.new(TEMP_PREFIX + "CAMERA", data)
    collection.objects.link(camera)
    data.type = "ORTHO"
    data.lens = 52.0
    return camera


def configure_render(scene: bpy.types.Scene) -> dict[str, Any]:
    snapshot = movement_base.scene_render_snapshot(scene)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.018, 0.025, 0.035)
    return snapshot


def render_one(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    owner_dir: Path,
    label: str,
    config: dict[str, Any],
    phase: dict[str, Any],
    body: bpy.types.Object,
    rig: bpy.types.Object,
    props: dict[str, bpy.types.Object],
    sequence: dict[str, Any],
    view: str,
) -> dict[str, Any]:
    low, high, center, span = body_bounds(body)
    scale = max(float(span.z) * 1.08, 0.7)
    target = center
    location = center + Vector((float(span.x) * 1.3, -float(span.z) * 1.7, float(span.z) * 0.2))
    if "feet" in view:
        foot_points = [
            rig.matrix_world @ rig.pose.bones[str(config["bone_map"][side]["foot"])].tail
            for side in ("left", "right")
        ]
        target = sum(foot_points, Vector()) / len(foot_points)
        scale = 0.62
        location = target + Vector((0.7, -0.86, 0.3))
    elif "seat_contact" in view:
        target = rig.matrix_world @ rig.pose.bones[str(config["bone_map"]["pelvis"])].head
        scale = 0.82
        side_sign = 1.0 if "left_profile" in view else -1.0
        location = target + Vector((side_sign * 1.0, 0.0, 0.18))
    elif view in ("left_arm_close", "right_arm_close"):
        side = "left" if view.startswith("left") else "right"
        shoulder = rig.matrix_world @ rig.pose.bones[str(config["bone_map"][side]["shoulder"])].head
        hand = hand_anchor(rig, config, side)
        target = (shoulder + hand) * 0.5
        scale = 0.82
        location = target + Vector((0.72, -0.9, 0.28))
    elif "close" in view:
        contacts = phase.get("contacts", [])
        sides = sorted({str(value["hand"]) for value in contacts})
        if not sides:
            sides = [side for side in ("left", "right") if side in phase.get("motion", {})]
        if not sides:
            sides = ["left", "right"]
        hand_points = [hand_anchor(rig, config, side) for side in sides]
        target = sum(hand_points, Vector()) / len(hand_points)
        contact_prop = None
        if contacts:
            first = contacts[0]
            key = "door:handle" if first.get("surface") == "handle" else str(first["prop"])
            contact_prop = props.get(key)
        if contact_prop is None:
            contact_prop = props.get(str(sequence.get("primary_prop", "")))
        if contact_prop is not None:
            target = (target + contact_prop.matrix_world.translation) * 0.5
        scale = 0.65
        location = target + Vector((0.62, -0.78, 0.42))
    elif "side" in view:
        location = center + Vector((float(span.z) * 1.8, 0.0, float(span.z) * 0.12))
    camera.location = location
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = scale
    scene.camera = camera
    path = owner_dir / f"{label}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {
        "label": label,
        "path": project_relative(path),
        "sha256": contract.sha256_file(path),
        "bytes": path.stat().st_size,
    }


def render_sequence(
    config: dict[str, Any],
    sequence: dict[str, Any],
    action: bpy.types.Action,
    body: bpy.types.Object,
    rig: bpy.types.Object,
    props: dict[str, bpy.types.Object],
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    owner_dir: Path,
) -> list[dict[str, Any]]:
    phases = {str(value["id"]): value for value in sequence["phases"]}
    renders = []
    rig.animation_data.action = action
    for request in sequence["evidence_views"]:
        phase = phases[str(request["phase"])]
        bpy.context.scene.frame_set(int(phase["frame"]))
        bpy.context.view_layer.update()
        set_phase_prop_state(phase, sequence, props, rig, config)
        label = f"{sequence['id']}__{phase['id']}__{request['view']}"
        renders.append(
            render_one(
                scene,
                camera,
                owner_dir,
                label,
                config,
                phase,
                body,
                rig,
                props,
                sequence,
                str(request["view"]),
            )
        )
    reset_pose(rig)
    return renders


def cleanup_temp_collection(collection: bpy.types.Collection, camera: bpy.types.Object) -> None:
    camera_data = camera.data
    bpy.data.objects.remove(camera, do_unlink=True)
    if camera_data.users == 0:
        bpy.data.cameras.remove(camera_data)
    if collection.users == 0 or len(collection.objects) == 0:
        bpy.data.collections.remove(collection)
    for material in list(bpy.data.materials):
        if material.name.startswith(TEMP_PREFIX) and material.users == 0:
            bpy.data.materials.remove(material)


def make_manifest(paths: Iterable[Path], manifest_path: Path) -> dict[str, Any]:
    entries = []
    for path in sorted({value.resolve() for value in paths}, key=str):
        entries.append(
            {
                "path": project_relative(path),
                "bytes": path.stat().st_size,
                "sha256": contract.sha256_file(path),
            }
        )
    value = {
        "schema_version": 1,
        "artifact_kind": "KIRA_R21_ACTION_ONLY_MOVEMENT_ATTEMPT04_PACKAGE_MANIFEST",
        "created_utc": utc_now(),
        "manifest_self_excluded": True,
        "files": entries,
    }
    write_json(manifest_path, value)
    return value


def run(config_path: Path, release_path: Path) -> int:
    # This entire release contract completes before output creation or Blender
    # mutation.  The checked-in prepared package has no release file.
    config = contract.load_json(config_path)
    prepared_summary = contract.validate_config(config)
    contract.validate_local_anchors(config, PROJECT_ROOT)
    if not release_path.is_file():
        raise RuntimeError("Attempt-04 Blender execution is not released")
    release = contract.load_json(release_path)
    release_paths = contract.validate_release(
        config,
        release,
        contract.sha256_file(config_path),
        PROJECT_ROOT,
    )

    source_path = release_paths["source_blend"]
    source_hash_before = contract.sha256_file(source_path)
    attempt03_path = PROJECT_ROOT / str(config["preserved_attempt_03"]["blend"])
    attempt03_hash_before = contract.sha256_file(attempt03_path)
    movement_base.ACTION_PREFIX = str(config["future_outputs"]["action_prefix"])
    body, rig, nails = validate_blender_source(config, release, source_path)
    reset_pose(rig)

    recovery_dir = PROJECT_ROOT / str(config["future_outputs"]["recovery_output_dir"])
    owner_dir = PROJECT_ROOT / str(config["future_outputs"]["owner_review_output_dir"])
    if recovery_dir.exists() or owner_dir.exists():
        raise FileExistsError("Attempt-04 append-only output already exists")
    recovery_dir.mkdir(parents=True, exist_ok=False)
    owner_dir.mkdir(parents=True, exist_ok=False)
    exact_dir = recovery_dir / "exact_intersections"
    localized_dir = recovery_dir / "localized_intersections"
    exact_dir.mkdir()
    localized_dir.mkdir()

    mesh_before = movement_base.inherited_mesh_snapshot()
    inherited_actions_before = movement_base.inherited_action_snapshot()
    rig_before = brow.armature_digest(rig)
    neutral_coordinate_before = movement_base.evaluated_coordinate_sha256(body)
    neutral_points = movement_base.assembly.evaluated_vertices(body)
    neutral_exact = movement_base.assembly.exact_body_intersection_report(body)
    neutral_keys = {movement_base.pair_key(pair) for pair in neutral_exact["pairs"]}
    regions = movement_base.prior.region_maps(body)

    actions = {
        sequence["id"]: author_sequence_action(config, sequence, rig)
        for sequence in config["sequences"]
    }
    temp_collection = make_temp_collection()
    camera = make_camera(temp_collection)
    scene = bpy.context.scene
    render_snapshot = configure_render(scene)
    sequence_evidence: dict[str, Any] = {}
    renders: list[dict[str, Any]] = []
    try:
        for sequence in config["sequences"]:
            records, props = audit_sequence(
                config,
                sequence,
                actions[sequence["id"]],
                body,
                rig,
                nails,
                neutral_points,
                neutral_keys,
                regions,
                temp_collection,
            )
            materials_before = props.pop("__materials_before__")  # type: ignore[arg-type]
            gate_summary = phase_gate_summary(config, records)
            renders.extend(
                render_sequence(
                    config,
                    sequence,
                    actions[sequence["id"]],
                    body,
                    rig,
                    props,
                    scene,
                    camera,
                    owner_dir,
                )
            )
            sequence_evidence[sequence["id"]] = {
                "phase_records": compact_audit_records(
                    records, exact_dir, localized_dir, str(sequence["id"])
                ),
                "motion_ranges_degrees": motion_ranges(config, sequence),
                "engineering_gates": gate_summary,
            }
            remove_sequence_props(props, materials_before)  # type: ignore[arg-type]
    finally:
        movement_base.restore_scene_render(scene, render_snapshot)
        reset_pose(rig)
        cleanup_temp_collection(temp_collection, camera)

    if bpy.data.collections.get(TEMP_COLLECTION) is not None:
        raise RuntimeError("temporary collection survived cleanup")
    if any(obj.name.startswith(TEMP_PREFIX) for obj in bpy.data.objects):
        raise RuntimeError("temporary evidence object survived cleanup")
    mesh_after = movement_base.inherited_mesh_snapshot()
    inherited_actions_after = movement_base.inherited_action_snapshot()
    if mesh_after != mesh_before:
        raise RuntimeError("protected mesh state changed during Attempt 04")
    if inherited_actions_after != inherited_actions_before:
        raise RuntimeError("inherited action state changed during Attempt 04")
    if brow.armature_digest(rig) != rig_before:
        raise RuntimeError("native rest rig changed during Attempt 04")
    if movement_base.evaluated_coordinate_sha256(body) != neutral_coordinate_before:
        raise RuntimeError("neutral evaluated body changed during Attempt 04")

    reset_pose(rig)
    blend_path = owner_dir / "KIRA_R21_BALD_PRIVATE_INACTIVE_ACTION_ONLY_MOVEMENT_ATTEMPT04.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    if contract.sha256_file(source_path) != source_hash_before:
        raise RuntimeError("released source Blend changed during Attempt 04")
    if contract.sha256_file(attempt03_path) != attempt03_hash_before:
        raise RuntimeError("preserved Attempt 03 changed during Attempt 04")

    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    body_reopen, rig_reopen, _ = validate_blender_source(config, release, blend_path)
    reset_pose(rig_reopen)
    new_actions = {
        action.name: movement_base.action_signature(action)
        for action in sorted(bpy.data.actions, key=lambda item: item.name)
        if action.name.startswith(str(config["future_outputs"]["action_prefix"]))
    }
    if sorted(new_actions) != contract.expected_action_names(config):
        raise RuntimeError("Attempt-04 new action inventory changed after save/reopen")
    if rig_reopen.animation_data and rig_reopen.animation_data.action is not None:
        raise RuntimeError("Attempt-04 action remained assigned after reopen")
    if movement_base.inherited_mesh_snapshot() != mesh_before:
        raise RuntimeError("protected mesh state changed after save/reopen")
    if movement_base.inherited_action_snapshot() != inherited_actions_before:
        raise RuntimeError("inherited action state changed after save/reopen")
    if brow.armature_digest(rig_reopen) != rig_before:
        raise RuntimeError("rest rig changed after save/reopen")
    if movement_base.evaluated_coordinate_sha256(body_reopen) != neutral_coordinate_before:
        raise RuntimeError("neutral evaluated body changed after save/reopen")

    all_sequence_gates_pass = all(
        bool(value["engineering_gates"]["pass"])
        for value in sequence_evidence.values()
    )
    evidence = {
        "schema_version": 1,
        "artifact_kind": "KIRA_R21_ACTION_ONLY_MOVEMENT_ATTEMPT04_BUILD_EVIDENCE",
        "created_utc": utc_now(),
        "status": (
            "PRIVATE_INACTIVE_ENGINEERING_GATES_PASS_PENDING_OWNER_VISUAL_REVIEW"
            if all_sequence_gates_pass
            else "PRIVATE_INACTIVE_ENGINEERING_GATES_FAILED_RETAINED_FOR_DIAGNOSIS"
        ),
        "candidate_id": config["candidate_id"],
        "prepared_contract": {
            "path": project_relative(config_path),
            "sha256": contract.sha256_file(config_path),
            "summary": prepared_summary,
        },
        "release": {
            "path": project_relative(release_path),
            "sha256": contract.sha256_file(release_path),
            "source_blend": project_relative(source_path),
            "source_blend_sha256_before": source_hash_before,
            "source_blend_sha256_after": contract.sha256_file(source_path),
            "source_evidence": project_relative(release_paths["source_evidence"]),
            "source_evidence_sha256": contract.sha256_file(release_paths["source_evidence"]),
        },
        "preserved_attempt_03": {
            "path": project_relative(attempt03_path),
            "sha256_before": attempt03_hash_before,
            "sha256_after": contract.sha256_file(attempt03_path),
            "unchanged": contract.sha256_file(attempt03_path) == attempt03_hash_before,
        },
        "neutral": {
            "exact_pair_count": int(neutral_exact["exact_genuine_penetration_pair_count"]),
            "evaluated_coordinate_sha256": neutral_coordinate_before,
        },
        "sequences": sequence_evidence,
        "new_actions_after_reopen": new_actions,
        "renders": renders,
        "engineering_gates_pass": all_sequence_gates_pass,
        "protected_verification": {
            "all_inherited_mesh_states_exact_after_save_reopen": True,
            "all_inherited_action_states_exact_after_save_reopen": True,
            "native_rest_rig_exact_after_save_reopen": True,
            "neutral_evaluated_coordinates_exact_after_save_reopen": True,
            "new_actions_unassigned_after_save_reopen": True,
            "temporary_props_and_camera_absent_after_save_reopen": True,
        },
        "output": {
            "blend": project_relative(blend_path),
            "blend_sha256": contract.sha256_file(blend_path),
            "blend_bytes": blend_path.stat().st_size,
        },
        "truth_boundary": config["truth_boundary"],
    }
    evidence_path = recovery_dir / "BUILD_EVIDENCE.json"
    write_json(evidence_path, evidence)
    readme = owner_dir / "OWNER_REVIEW_README.md"
    readme.write_text(
        "# Kira R21 movement Attempt 04\n\n"
        "Private, inactive, unassigned action-only evidence. Review natural arms, "
        "walk/jog/run contacts and reciprocal arm swing, object grips, door use, "
        "handwashing, shower balance, and bath support. Engineering pass does not "
        "equal owner approval or proof of biological function.\n",
        encoding="utf-8",
    )
    rollback = recovery_dir / "ROLLBACK.md"
    rollback.write_text(
        "# Rollback\n\nContinue selecting the exact released source Blend and ignore the "
        "Attempt-04 actions. No source or Attempt-03 file was changed. Delete no "
        "evidence automatically.\n",
        encoding="utf-8",
    )
    manifest_path = recovery_dir / "PACKAGE_MANIFEST.json"
    package_paths = [
        blend_path,
        evidence_path,
        readme,
        rollback,
        *[PROJECT_ROOT / item["path"] for item in renders],
        *exact_dir.glob("*.json"),
        *localized_dir.glob("*.json"),
    ]
    make_manifest(package_paths, manifest_path)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve()
    release_path = Path(args.release).resolve() if args.release else Path("")
    try:
        return run(config_path, release_path)
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "status": "FAILED_OR_NOT_RELEASED_ACTION_ONLY_MOVEMENT_ATTEMPT04",
            "created_utc": utc_now(),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "attempt_03_preserved": True,
        }
        # Do not create failure evidence for the normal prepared/no-release
        # state. A real released attempt may write one append-only failure file.
        if args.release and not FAILURE_PATH.exists():
            write_json(FAILURE_PATH, failure)
        print(json.dumps(failure, indent=2, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
