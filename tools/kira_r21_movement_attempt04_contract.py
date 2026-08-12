#!/usr/bin/env python3
"""Pure-Python contract for Kira R21 movement Attempt 04.

The module is intentionally Blender-free so the complete movement plan can be
validated before any Blender process is authorized.  It validates required
sequence/phase/contact/render coverage and deterministically expands semantic
phase parameters into native-rig rotations and root locations.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


REQUIRED_SEQUENCE_IDS = {
    "natural_neutral_arms",
    "walk_cycle",
    "jog_cycle",
    "run_cycle",
    "book_reach_grasp_retract_hold",
    "tablet_reach_grasp_retract_hold",
    "phone_reach_grasp_retract_hold",
    "door_handle_push_step_through",
    "door_handle_pull_step_through",
    "handwashing_complete",
    "shower_entry_wash_exit",
    "bath_entry_supported_sit_rise_exit",
}

REQUIRED_PHASES = {
    "natural_neutral_arms": ("neutral",),
    "walk_cycle": (
        "left_contact",
        "left_midstance",
        "passing",
        "right_contact",
        "right_midstance",
        "loop",
    ),
    "jog_cycle": (
        "left_contact",
        "flight_to_right",
        "right_contact",
        "flight_to_left",
        "loop",
    ),
    "run_cycle": (
        "left_contact",
        "flight_to_right",
        "right_contact",
        "flight_to_left",
        "loop",
    ),
    "book_reach_grasp_retract_hold": (
        "neutral",
        "reach",
        "grasp",
        "retract",
        "hold",
    ),
    "tablet_reach_grasp_retract_hold": (
        "neutral",
        "reach",
        "grasp",
        "retract",
        "hold",
    ),
    "phone_reach_grasp_retract_hold": (
        "neutral",
        "reach",
        "grasp",
        "retract",
        "hold",
    ),
    "door_handle_push_step_through": (
        "neutral",
        "reach",
        "grip",
        "turn",
        "push",
        "step_through",
        "release",
    ),
    "door_handle_pull_step_through": (
        "neutral",
        "reach",
        "grip",
        "turn",
        "pull",
        "step_through",
        "release",
    ),
    "handwashing_complete": (
        "neutral",
        "faucet_on",
        "soap",
        "rub",
        "rinse",
        "faucet_off",
        "dry",
    ),
    "shower_entry_wash_exit": (
        "approach",
        "entry",
        "balance",
        "controls",
        "wash_upper",
        "wash_lower",
        "exit_balance",
        "exit",
    ),
    "bath_entry_supported_sit_rise_exit": (
        "approach",
        "entry_support",
        "lower",
        "supported_sit",
        "supported_rise",
        "exit_support",
        "exit",
    ),
}

REQUIRED_EVIDENCE = {
    "exact_nonadjacent_self_intersections_per_phase",
    "localized_pose_induced_or_exposed_pairs_per_phase",
    "exact_body_nail_intersections_per_phase",
    "exact_body_prop_intersections_per_contact_phase",
    "hand_palm_thumb_and_fingertip_to_prop_distances",
    "finger_closure_per_grip_phase",
    "shoulder_elbow_wrist_motion_ranges",
    "planted_foot_drift_and_vertical_drift",
    "geometry_centroid_support_polygon_proxy",
    "seat_floor_rim_bar_handle_and_basin_contact_records",
    "source_and_output_hashes_before_and_after",
    "all_inherited_mesh_action_rig_and_neutral_coordinate_signatures",
    "new_action_assignment_state_after_save_reopen",
    "temporary_prop_and_camera_absence_after_save_reopen",
    "close_hand_arm_prop_renders",
    "full_body_support_and_contact_renders",
    "owner_visual_review",
}


class ContractError(ValueError):
    """Raised when a prepared Attempt-04 contract is incomplete or unsafe."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError(f"expected JSON object: {path}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def _sequence_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values = config.get("sequences")
    _require(isinstance(values, list), "sequences must be a list")
    result: dict[str, dict[str, Any]] = {}
    for value in values:
        _require(isinstance(value, dict), "each sequence must be an object")
        name = str(value.get("id", ""))
        _require(name and name not in result, f"duplicate or empty sequence id: {name}")
        result[name] = value
    return result


def _phase_map(sequence: dict[str, Any]) -> dict[str, dict[str, Any]]:
    phases = sequence.get("phases")
    _require(isinstance(phases, list) and phases, f"{sequence['id']} has no phases")
    result: dict[str, dict[str, Any]] = {}
    frames: list[int] = []
    for value in phases:
        _require(isinstance(value, dict), f"{sequence['id']} phase must be an object")
        phase_id = str(value.get("id", ""))
        _require(
            phase_id and phase_id not in result,
            f"{sequence['id']} has duplicate or empty phase id: {phase_id}",
        )
        frame = int(value.get("frame", 0))
        _require(frame > 0, f"{sequence['id']}:{phase_id} frame must be positive")
        frames.append(frame)
        result[phase_id] = value
    _require(frames == sorted(frames), f"{sequence['id']} frames are not increasing")
    _require(len(frames) == len(set(frames)), f"{sequence['id']} frames are duplicated")
    return result


def _view_map(sequence: dict[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for value in sequence.get("evidence_views", []):
        phase = str(value.get("phase", ""))
        view = str(value.get("view", ""))
        _require(phase and view, f"{sequence['id']} has an incomplete evidence view")
        result.setdefault(phase, set()).add(view)
    return result


def _has_close_prop_view(views: Iterable[str]) -> bool:
    return any("prop_close" in value or "handle_wrist_close" in value for value in views)


def _validate_release_boundary(config: dict[str, Any]) -> None:
    _require(config.get("execution_release") is None, "prepared config already has a release")
    source = config.get("source_binding", {})
    _require(
        source.get("mode") == "DEFERRED_UNTIL_PELVIC_AND_NAIL_PRIORITIES_COMPLETE",
        "Attempt 04 must remain deferred behind pelvic/nail priorities",
    )
    for key in (
        "execution_source_blend",
        "execution_source_sha256",
        "execution_source_evidence",
        "execution_source_evidence_sha256",
    ):
        _require(source.get(key) is None, f"prepared source field must remain null: {key}")
    _require(
        bool(source.get("release_must_bind_exact_post_priority_source")),
        "release must bind the exact post-priority source",
    )


def _validate_preservation(config: dict[str, Any]) -> None:
    protected = config.get("protected_component_contract", {})
    for key in (
        "body_mesh_mutation_allowed",
        "rest_rig_mutation_allowed",
        "weight_mutation_allowed",
        "material_mutation_allowed",
    ):
        _require(protected.get(key) is False, f"unsafe mutation permission: {key}")
    _require(
        protected.get("only_append_only_actions_allowed") is True,
        "only append-only actions may be authored",
    )
    attempt03 = config.get("preserved_attempt_03", {})
    _require(attempt03.get("must_remain_byte_exact") is True, "Attempt 03 is not sealed")
    _require(attempt03.get("must_not_be_used_as_source") is True, "Attempt 03 cannot be source")
    outputs = config.get("future_outputs", {})
    for key in ("private", "inactive", "unassigned", "unpublished"):
        _require(outputs.get(key) is True, f"future output must be {key}")
    _require(outputs.get("runtime_activation_allowed") is False, "runtime activation is forbidden")


def _validate_gait(sequence: dict[str, Any]) -> None:
    phases = _phase_map(sequence)
    speed = sequence["id"].split("_", 1)[0]
    planted = {str(value.get("planted_foot")) for value in phases.values()}
    _require("left" in planted and "right" in planted, f"{speed} lacks bilateral contact phases")
    first = phases[REQUIRED_PHASES[sequence["id"]][0]]["motion"]
    last = phases[REQUIRED_PHASES[sequence["id"]][-1]]["motion"]
    _require(first == last, f"{speed} loop endpoint does not equal its start")
    for phase in phases.values():
        motion = phase.get("motion", {})
        _require(motion.get("kind") == "gait", f"{speed} contains a non-gait motion")
        _require(motion.get("speed") == speed, f"{speed} profile mismatch")
        stride = float(motion.get("stride_factor", 0.0))
        _require(-1.0 <= stride <= 1.0, f"{speed} stride factor out of bounds")
        pose = generate_phase_pose(config=None, phase=phase, gait_profiles_override=None)
        left_arm = pose["rotations_degrees_xyz"]["__semantic_left_arm_swing__"][0]
        right_arm = pose["rotations_degrees_xyz"]["__semantic_right_arm_swing__"][0]
        left_leg = pose["rotations_degrees_xyz"]["__semantic_left_leg_swing__"][0]
        right_leg = pose["rotations_degrees_xyz"]["__semantic_right_leg_swing__"][0]
        _require(left_arm * left_leg <= 0.0, f"{speed} left arm is not reciprocal")
        _require(right_arm * right_leg <= 0.0, f"{speed} right arm is not reciprocal")


def _validate_interaction(sequence: dict[str, Any]) -> None:
    phases = _phase_map(sequence)
    views = _view_map(sequence)
    prop = str(sequence.get("primary_prop", ""))
    _require(bool(prop), f"{sequence['id']} lacks a primary prop")
    for phase_id, phase in phases.items():
        contacts = phase.get("contacts", [])
        for contact in contacts:
            _require(contact.get("prop") in (prop, "faucet", "soap", "basin", "towel", "shower_grab_bar", "shower_control", "bath_grab_bar"), f"{sequence['id']} has an unknown contact prop")
            if bool(contact.get("grip")):
                _require(
                    _has_close_prop_view(views.get(phase_id, set())),
                    f"{sequence['id']}:{phase_id} grip lacks a close hand/arm/prop render",
                )
        mode = str(phase.get("prop_mode", "fixed"))
        if mode.startswith("follow_"):
            preceding = [value for value in phases.values() if int(value["frame"]) < int(phase["frame"])]
            _require(
                any(any(bool(item.get("grip")) for item in value.get("contacts", [])) for value in preceding),
                f"{sequence['id']}:{phase_id} follows a grip before a static contact gate",
            )


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    _require(config.get("schema_version") == 1, "unsupported schema")
    _require(
        config.get("status") == "PREPARED_NOT_EXECUTED_WAITING_FOR_PELVIC_AND_NAIL_PRIORITY_SOURCE",
        "Attempt 04 is not in its prepared-only state",
    )
    _validate_release_boundary(config)
    _validate_preservation(config)

    sequences = _sequence_map(config)
    _require(set(sequences) == REQUIRED_SEQUENCE_IDS, "required sequence inventory mismatch")
    for sequence_id, expected in REQUIRED_PHASES.items():
        actual = tuple(_phase_map(sequences[sequence_id]))
        _require(actual == expected, f"{sequence_id} phase order mismatch: {actual}")
    for sequence_id in ("walk_cycle", "jog_cycle", "run_cycle"):
        _validate_gait(sequences[sequence_id])
    for sequence_id, sequence in sequences.items():
        if sequence_id != "natural_neutral_arms" and sequence.get("category") != "gait":
            _validate_interaction(sequence)

    evidence = set(config.get("required_evidence", []))
    _require(evidence == REQUIRED_EVIDENCE, "required evidence inventory mismatch")
    gates = config.get("acceptance_gates", {})
    _require(
        int(gates.get("maximum_pose_induced_or_exposed_self_intersection_pairs", -1)) == 0,
        "pose-induced self intersections must be zero",
    )
    _require(
        int(gates.get("maximum_body_prop_penetration_pairs", -1)) == 0,
        "body/prop penetrations must be zero",
    )
    _require(
        gates.get("reciprocal_arm_swing_required_for_walk_jog_run") is True,
        "reciprocal arm swing gate is missing",
    )
    _require(
        gates.get("static_prop_contact_must_pass_before_follow_grip_attachment") is True,
        "static-to-follow grip gate is missing",
    )

    neutral_phase = _phase_map(sequences["natural_neutral_arms"])["neutral"]
    neutral = generate_phase_pose(config, neutral_phase)
    bone_map = config["bone_map"]
    left_shoulder = neutral["rotations_degrees_xyz"][bone_map["left"]["shoulder"]]
    right_shoulder = neutral["rotations_degrees_xyz"][bone_map["right"]["shoulder"]]
    max_side = float(config["motion_profiles"]["natural_neutral"]["shoulder_side_degrees"])
    _require(max(abs(left_shoulder[2]), abs(right_shoulder[2])) <= max_side, "neutral arms remain presentation-wide")

    return {
        "sequence_count": len(sequences),
        "phase_count": sum(len(value["phases"]) for value in sequences.values()),
        "evidence_view_count": sum(len(value.get("evidence_views", [])) for value in sequences.values()),
        "required_evidence_count": len(evidence),
        "prepared_only": True,
        "blender_execution_authorized": False,
    }


def _natural_pose(config: dict[str, Any]) -> dict[str, list[float]]:
    bone_map = config["bone_map"]
    profile = config["motion_profiles"]["natural_neutral"]
    side = float(profile["shoulder_side_degrees"])
    forward = float(profile["shoulder_forward_degrees"])
    elbow = float(profile["elbow_flex_degrees"])
    wrist = float(profile["wrist_relax_degrees"])
    pose = {
        bone_map["left"]["shoulder"]: [forward, -2.0, side],
        bone_map["right"]["shoulder"]: [forward, 2.0, -side],
        bone_map["left"]["forearm"]: [0.0, elbow, 0.0],
        bone_map["right"]["forearm"]: [0.0, -elbow, 0.0],
        bone_map["left"]["hand"]: [wrist, 0.0, -2.0],
        bone_map["right"]["hand"]: [wrist, 0.0, 2.0],
    }
    _apply_finger_curl(config, pose, "left", float(profile["finger_closure"]))
    _apply_finger_curl(config, pose, "right", float(profile["finger_closure"]))
    return pose


def _apply_finger_curl(
    config: dict[str, Any],
    pose: dict[str, list[float]],
    side: str,
    closure: float,
) -> None:
    closure = max(0.0, min(1.0, float(closure)))
    profile = config["motion_profiles"]["upper_body"]
    side_map = config["bone_map"][side]
    for name, degrees in zip(side_map["thumb"], profile["thumb_joint_curl_degrees"]):
        pose[name] = [float(degrees) * closure, 0.0, -10.0 * closure if side == "left" else 10.0 * closure]
    for digit in ("index", "middle", "ring", "pinky"):
        for name, degrees in zip(side_map[digit], profile["finger_joint_curl_degrees"]):
            pose[name] = [float(degrees) * closure, 0.0, 0.0]


def _apply_upper_body_side(
    config: dict[str, Any],
    pose: dict[str, list[float]],
    side: str,
    values: dict[str, Any],
) -> None:
    profile = config["motion_profiles"]["upper_body"]
    side_map = config["bone_map"][side]
    sign = 1.0 if side == "left" else -1.0
    extension = max(0.0, min(1.0, float(values.get("extension", 0.0))))
    elbow = max(0.0, min(1.0, float(values.get("elbow", 0.0))))
    wrist = max(-1.0, min(1.0, float(values.get("wrist", 0.0))))
    grip = max(0.0, min(1.0, float(values.get("grip", 0.0))))
    neutral_side = float(config["motion_profiles"]["natural_neutral"]["shoulder_side_degrees"])
    pose[side_map["shoulder"]] = [
        -float(profile["maximum_shoulder_forward_degrees"]) * extension,
        -sign * float(profile["maximum_shoulder_lateral_degrees"]) * extension,
        sign * (neutral_side + 24.0 * extension),
    ]
    pose[side_map["forearm"]] = [
        0.0,
        sign * float(profile["maximum_elbow_flex_degrees"]) * elbow,
        0.0,
    ]
    pose[side_map["hand"]] = [
        float(profile["maximum_wrist_turn_degrees"]) * wrist,
        0.0,
        -sign * 12.0 * extension,
    ]
    _apply_finger_curl(config, pose, side, grip)


def _apply_whole_body(
    config: dict[str, Any],
    pose: dict[str, list[float]],
    locations: dict[str, list[float]],
    motion: dict[str, Any],
) -> None:
    bones = config["bone_map"]
    for side in ("left", "right"):
        if isinstance(motion.get(side), dict):
            _apply_upper_body_side(config, pose, side, motion[side])
    for side in ("left", "right"):
        side_map = bones[side]
        step = float(motion.get(f"{side}_step", 0.0))
        knee = float(motion.get(f"{side}_knee", 0.0))
        hip = float(motion.get(f"{side}_hip", 0.0))
        pose[side_map["thigh"]] = [-42.0 * step - 62.0 * hip, 0.0, 5.0 * step * (1.0 if side == "left" else -1.0)]
        pose[side_map["shin"]] = [72.0 * max(abs(step) * 0.5, knee), 0.0, 0.0]
        pose[side_map["foot"]] = [-18.0 * max(abs(step), knee), 0.0, 0.0]
    lean = float(motion.get("body_lean", 0.0))
    pose[bones["abdomen_lower"]] = [-12.0 * lean, 0.0, 0.0]
    pose[bones["chest_lower"]] = [-8.0 * lean, 0.0, 0.0]
    locations[bones["hip"]] = [
        0.0,
        float(motion.get("root_forward_m", 0.0)),
        -float(motion.get("root_down_m", 0.0)),
    ]


def generate_phase_pose(
    config: dict[str, Any] | None,
    phase: dict[str, Any],
    gait_profiles_override: dict[str, Any] | None = None,
) -> dict[str, dict[str, list[float]]]:
    """Expand one semantic phase into deterministic rotations and locations.

    A minimal semantic-only path is retained for gait contract checks before a
    config is supplied; real worker calls always provide the complete config.
    """

    motion = phase.get("motion", {})
    kind = str(motion.get("kind", ""))
    if config is None:
        if kind != "gait":
            raise ContractError("semantic-only generation supports gait only")
        stride = float(motion.get("stride_factor", 0.0))
        return {
            "rotations_degrees_xyz": {
                "__semantic_left_arm_swing__": [stride, 0.0, 0.0],
                "__semantic_right_arm_swing__": [-stride, 0.0, 0.0],
                "__semantic_left_leg_swing__": [-stride, 0.0, 0.0],
                "__semantic_right_leg_swing__": [stride, 0.0, 0.0],
            },
            "locations_m_xyz": {},
        }

    pose = _natural_pose(config)
    locations: dict[str, list[float]] = {}
    bones = config["bone_map"]
    if kind == "natural_neutral":
        pass
    elif kind == "gait":
        speed = str(motion["speed"])
        profile = (gait_profiles_override or config["motion_profiles"]["gait"])[speed]
        stride = float(motion["stride_factor"])
        left_knee = float(motion.get("left_knee_factor", 0.0))
        right_knee = float(motion.get("right_knee_factor", 0.0))
        hip_swing = float(profile["hip_swing_degrees"])
        arm_swing = float(profile["arm_swing_degrees"])
        pose[bones["left"]["thigh"]] = [-hip_swing * stride, 0.0, 2.0 * stride]
        pose[bones["right"]["thigh"]] = [hip_swing * stride, 0.0, -2.0 * stride]
        pose[bones["left"]["shin"]] = [float(profile["knee_flex_degrees"]) * left_knee, 0.0, 0.0]
        pose[bones["right"]["shin"]] = [float(profile["knee_flex_degrees"]) * right_knee, 0.0, 0.0]
        pose[bones["left"]["foot"]] = [-float(profile["ankle_degrees"]) * left_knee, 0.0, 0.0]
        pose[bones["right"]["foot"]] = [-float(profile["ankle_degrees"]) * right_knee, 0.0, 0.0]
        pose[bones["left"]["shoulder"]][0] = arm_swing * stride
        pose[bones["right"]["shoulder"]][0] = -arm_swing * stride
        pose[bones["left"]["forearm"]][1] = float(profile["elbow_flex_degrees"])
        pose[bones["right"]["forearm"]][1] = -float(profile["elbow_flex_degrees"])
        locations[bones["hip"]] = [0.0, 0.0, float(profile["root_bob_m"]) * float(motion.get("root_bob_factor", 0.0))]
    elif kind == "upper_body":
        for side in ("left", "right"):
            if isinstance(motion.get(side), dict):
                _apply_upper_body_side(config, pose, side, motion[side])
    elif kind == "whole_body":
        _apply_whole_body(config, pose, locations, motion)
    else:
        raise ContractError(f"unsupported motion kind: {kind}")
    return {"rotations_degrees_xyz": pose, "locations_m_xyz": locations}


def expected_action_names(config: dict[str, Any]) -> list[str]:
    prefix = str(config["future_outputs"]["action_prefix"])
    return sorted(prefix + str(value["id"]).upper() for value in config["sequences"])


def expected_render_labels(config: dict[str, Any]) -> list[str]:
    labels = []
    for sequence in config["sequences"]:
        for value in sequence.get("evidence_views", []):
            labels.append(f"{sequence['id']}__{value['phase']}__{value['view']}")
    return sorted(labels)


def validate_local_anchors(config: dict[str, Any], project_root: Path) -> dict[str, str]:
    """Verify only preserved/current preparation anchors; never bind execution."""

    source = config["source_binding"]
    attempt03 = config["preserved_attempt_03"]
    checks = {
        source["current_reference_blend"]: source["current_reference_sha256"],
        source["current_reference_evidence"]: source["current_reference_evidence_sha256"],
        attempt03["blend"]: attempt03["blend_sha256"],
        attempt03["build_evidence"]: attempt03["build_evidence_sha256"],
        attempt03["package_manifest"]: attempt03["package_manifest_sha256"],
    }
    actual: dict[str, str] = {}
    for relative, expected in checks.items():
        path = project_root / relative
        _require(path.is_file(), f"missing local anchor: {relative}")
        digest = sha256_file(path)
        _require(digest == expected, f"local anchor drifted: {relative}: {digest}")
        actual[relative] = digest
    return actual


def validate_release(
    config: dict[str, Any],
    release: dict[str, Any],
    prepared_config_sha256: str,
    project_root: Path,
) -> dict[str, Path]:
    _require(release.get("schema_version") == 1, "release schema mismatch")
    _require(release.get("authorized_for_blender_execution") is True, "Blender release is absent")
    _require(
        release.get("prepared_config_sha256") == prepared_config_sha256,
        "release does not bind the exact prepared config",
    )
    _require(
        release.get("pelvic_and_nail_priorities_complete") is True,
        "pelvic/nail priorities are not complete",
    )
    required = (
        "source_blend",
        "source_blend_sha256",
        "source_evidence",
        "source_evidence_sha256",
        "body_object",
        "body_geometry_uv_sha256",
        "body_positive_weight_assignment_sha256",
        "rig_object",
        "rig_rest_sha256",
    )
    for key in required:
        _require(bool(release.get(key)), f"release is missing {key}")
    paths = {
        "source_blend": project_root / str(release["source_blend"]),
        "source_evidence": project_root / str(release["source_evidence"]),
    }
    for key, hash_key in (
        ("source_blend", "source_blend_sha256"),
        ("source_evidence", "source_evidence_sha256"),
    ):
        _require(paths[key].is_file(), f"release path is absent: {paths[key]}")
        _require(sha256_file(paths[key]) == release[hash_key], f"release hash mismatch: {key}")
    _require(
        release["rig_rest_sha256"]
        == config["protected_component_contract"]["reference_rig_rest_sha256"],
        "release changed the native rest rig",
    )
    return paths
