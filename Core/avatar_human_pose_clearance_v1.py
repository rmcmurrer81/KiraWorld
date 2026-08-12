"""Pure pose, clearance, and support-contact contract for human avatars.

The coordinates used by this module match the current Avatar Builder convention:
``+X`` is the character's left, ``-Y`` is forward, and ``+Z`` is up.  This file
has no Blender dependency.  It deliberately describes foundations rather than
claiming that a pose, animation, collision system, or daily-life capability has
passed visual review.
"""

from __future__ import annotations

from copy import deepcopy
from math import sqrt
from typing import Any, Mapping, Sequence


METHOD_ID = "avatar_human_pose_clearance_contact_v1"
SUPPORTED_POSES = ("neutral", "seated", "lying_supine", "eating_ready")

_EPSILON = 1.0e-12


def _vec3(value: Sequence[float]) -> tuple[float, float, float]:
    if len(value) != 3:
        raise ValueError("a three-component point or vector is required")
    result = tuple(float(item) for item in value)
    if not all(-1.0e6 < item < 1.0e6 for item in result):
        raise ValueError("point or vector contains a non-finite or extreme value")
    return result


def _add(
    left: Sequence[float], right: Sequence[float]
) -> tuple[float, float, float]:
    a = _vec3(left)
    b = _vec3(right)
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(
    left: Sequence[float], right: Sequence[float]
) -> tuple[float, float, float]:
    a = _vec3(left)
    b = _vec3(right)
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(value: Sequence[float], factor: float) -> tuple[float, float, float]:
    point = _vec3(value)
    amount = float(factor)
    return (point[0] * amount, point[1] * amount, point[2] * amount)


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    a = _vec3(left)
    b = _vec3(right)
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _length(value: Sequence[float]) -> float:
    return sqrt(_dot(value, value))


def _lerp(
    start: Sequence[float], end: Sequence[float], fraction: float
) -> tuple[float, float, float]:
    return _add(start, _scale(_sub(end, start), float(fraction)))


def segment_segment_distance(
    first_start: Sequence[float],
    first_end: Sequence[float],
    second_start: Sequence[float],
    second_end: Sequence[float],
) -> float:
    """Return the shortest Euclidean distance between two closed 3-D segments."""

    p1 = _vec3(first_start)
    q1 = _vec3(first_end)
    p2 = _vec3(second_start)
    q2 = _vec3(second_end)
    d1 = _sub(q1, p1)
    d2 = _sub(q2, p2)
    offset = _sub(p1, p2)
    a = _dot(d1, d1)
    e = _dot(d2, d2)
    f = _dot(d2, offset)

    if a <= _EPSILON and e <= _EPSILON:
        return _length(offset)
    if a <= _EPSILON:
        first_fraction = 0.0
        second_fraction = max(0.0, min(1.0, f / e))
    else:
        c = _dot(d1, offset)
        if e <= _EPSILON:
            second_fraction = 0.0
            first_fraction = max(0.0, min(1.0, -c / a))
        else:
            b = _dot(d1, d2)
            denominator = a * e - b * b
            first_fraction = (
                max(0.0, min(1.0, (b * f - c * e) / denominator))
                if denominator > _EPSILON
                else 0.0
            )
            second_fraction = (b * first_fraction + f) / e
            if second_fraction < 0.0:
                second_fraction = 0.0
                first_fraction = max(0.0, min(1.0, -c / a))
            elif second_fraction > 1.0:
                second_fraction = 1.0
                first_fraction = max(0.0, min(1.0, (b - c) / a))
    first_point = _add(p1, _scale(d1, first_fraction))
    second_point = _add(p2, _scale(d2, second_fraction))
    return _length(_sub(first_point, second_point))


def solve_support_contact_translation(
    *,
    measured_support_z_m: float,
    support_plane_z_m: float,
    clearance_m: float = 0.001,
    body_height_m: float,
    maximum_translation_height_fraction: float = 0.30,
) -> dict[str, Any]:
    """Solve a bounded vertical correction that creates contact without penetration."""

    height = float(body_height_m)
    clearance = float(clearance_m)
    maximum_fraction = float(maximum_translation_height_fraction)
    if not 0.8 <= height <= 2.7:
        raise ValueError("body height must describe a human-scale avatar")
    if not 0.0 <= clearance <= 0.01:
        raise ValueError("support clearance must be between zero and one centimetre")
    if not 0.0 < maximum_fraction <= 0.65:
        raise ValueError("maximum support translation fraction is unsafe")
    target_z = float(support_plane_z_m) + clearance
    delta_z = target_z - float(measured_support_z_m)
    maximum_delta = height * maximum_fraction
    if abs(delta_z) > maximum_delta:
        raise ValueError("support correction exceeds the bounded human-pose range")
    return {
        "method_id": METHOD_ID,
        "measured_support_z_m": float(measured_support_z_m),
        "support_plane_z_m": float(support_plane_z_m),
        "clearance_m": clearance,
        "target_support_z_m": target_z,
        "world_vertical_translation_m": delta_z,
        "maximum_allowed_translation_m": maximum_delta,
        "contact_target_without_penetration": True,
    }


def _seated_joints(height: float) -> dict[str, tuple[float, float, float]]:
    """Chair-sitting targets relative to the midpoint between the hip joints."""

    return {
        "hip.L": (+0.062 * height, 0.000 * height, 0.000 * height),
        "hip.R": (-0.062 * height, 0.000 * height, 0.000 * height),
        "knee.L": (+0.108 * height, -0.218 * height, -0.020 * height),
        "knee.R": (-0.108 * height, -0.218 * height, -0.020 * height),
        "ankle.L": (+0.108 * height, -0.190 * height, -0.238 * height),
        "ankle.R": (-0.108 * height, -0.190 * height, -0.238 * height),
        "toe.L": (+0.108 * height, -0.258 * height, -0.246 * height),
        "toe.R": (-0.108 * height, -0.258 * height, -0.246 * height),
        "shoulder.L": (+0.125 * height, -0.010 * height, +0.290 * height),
        "shoulder.R": (-0.125 * height, -0.010 * height, +0.290 * height),
        "elbow.L": (+0.205 * height, -0.065 * height, +0.205 * height),
        "elbow.R": (-0.205 * height, -0.065 * height, +0.205 * height),
        "wrist.L": (+0.225 * height, -0.125 * height, +0.145 * height),
        "wrist.R": (-0.225 * height, -0.125 * height, +0.145 * height),
    }


def _eating_ready_joints(height: float) -> dict[str, tuple[float, float, float]]:
    joints = _seated_joints(height)
    joints.update(
        {
            "elbow.L": (+0.155 * height, -0.175 * height, +0.215 * height),
            "elbow.R": (-0.155 * height, -0.175 * height, +0.215 * height),
            "wrist.L": (+0.090 * height, -0.285 * height, +0.205 * height),
            "wrist.R": (-0.090 * height, -0.285 * height, +0.205 * height),
            "hand_focus": (0.000 * height, -0.325 * height, +0.205 * height),
        }
    )
    return joints


def _lying_joints(height: float) -> dict[str, tuple[float, float, float]]:
    """Relaxed supine targets after the body root is rotated onto its back."""

    return {
        "hip.L": (+0.062 * height, 0.000 * height, 0.000 * height),
        "hip.R": (-0.062 * height, 0.000 * height, 0.000 * height),
        "knee.L": (+0.084 * height, -0.225 * height, +0.012 * height),
        "knee.R": (-0.084 * height, -0.225 * height, +0.012 * height),
        "ankle.L": (+0.092 * height, -0.458 * height, +0.000 * height),
        "ankle.R": (-0.092 * height, -0.458 * height, +0.000 * height),
        "toe.L": (+0.092 * height, -0.515 * height, +0.018 * height),
        "toe.R": (-0.092 * height, -0.515 * height, +0.018 * height),
        "shoulder.L": (+0.125 * height, +0.290 * height, +0.010 * height),
        "shoulder.R": (-0.125 * height, +0.290 * height, +0.010 * height),
        "elbow.L": (+0.205 * height, +0.205 * height, +0.015 * height),
        "elbow.R": (-0.205 * height, +0.205 * height, +0.015 * height),
        "wrist.L": (+0.225 * height, +0.115 * height, +0.015 * height),
        "wrist.R": (-0.225 * height, +0.115 * height, +0.015 * height),
    }


def build_pose_plan(
    pose_name: str,
    *,
    body_height_m: float,
    seat_top_z_m: float | None = None,
    support_plane_z_m: float | None = None,
) -> dict[str, Any]:
    """Return an immutable-by-convention pose foundation plan.

    Joint coordinates are offsets from the midpoint between the two hip joints.
    ``seated`` and ``eating_ready`` require a measured seat top.  ``lying_supine``
    requires a measured support plane.  Neutral intentionally carries no target
    joints: the Blender adapter must restore the rig's exact rest pose.
    """

    name = str(pose_name).strip().lower()
    if name not in SUPPORTED_POSES:
        raise ValueError(f"unsupported pose foundation: {pose_name}")
    height = float(body_height_m)
    if not 0.8 <= height <= 2.7:
        raise ValueError("body height must describe a human-scale avatar")
    if name in {"seated", "eating_ready"} and seat_top_z_m is None:
        raise ValueError("a measured seat top is required for a seated foundation")
    if name == "lying_supine" and support_plane_z_m is None:
        raise ValueError("a measured support plane is required for a lying foundation")

    if name == "neutral":
        joints: dict[str, tuple[float, float, float]] = {}
    elif name == "seated":
        joints = _seated_joints(height)
    elif name == "eating_ready":
        joints = _eating_ready_joints(height)
    else:
        joints = _lying_joints(height)

    plan = {
        "method_id": METHOD_ID,
        "pose_name": name,
        "body_height_m": height,
        "coordinate_frame": {
            "left": "+X",
            "forward": "-Y",
            "up": "+Z",
            "joint_origin": "midpoint_between_hip_joint_heads",
        },
        "joint_targets_m": joints,
        "seat_top_z_m": None if seat_top_z_m is None else float(seat_top_z_m),
        "support_plane_z_m": (
            None if support_plane_z_m is None else float(support_plane_z_m)
        ),
        "world_space_support_contact_required": name
        in {"seated", "eating_ready", "lying_supine"},
        "bilateral_leg_clearance_required": name in {"seated", "eating_ready"},
        "root_local_location_shortcut_forbidden": True,
        "assumed_euler_axis_rotation_forbidden": True,
        "inactive_authoring_foundation_only": True,
        "runtime_activation_allowed": False,
        "animation_capability_claimed": False,
        "visual_review_required": True,
    }
    plan["clearance_validation"] = validate_pose_plan(plan)
    return deepcopy(plan)


def validate_pose_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed on crossed legs, collapsed symmetry, and capsule overlap."""

    name = str(plan.get("pose_name") or "")
    if name not in SUPPORTED_POSES:
        raise ValueError("pose plan method/name is not recognized")
    if str(plan.get("method_id") or "") != METHOD_ID:
        raise ValueError("pose plan method id drifted")
    height = float(plan.get("body_height_m") or 0.0)
    joints = {
        str(key): _vec3(value)
        for key, value in dict(plan.get("joint_targets_m") or {}).items()
    }
    if name == "neutral":
        if joints:
            raise ValueError("neutral must restore rest pose, not invent joint targets")
        return {
            "passed": True,
            "pose_name": name,
            "checked_bilateral_joint_count": 0,
            "minimum_capsule_surface_clearance_m": None,
        }

    required = {
        f"{joint}.{side}"
        for joint in ("hip", "knee", "ankle", "toe", "shoulder", "elbow", "wrist")
        for side in ("L", "R")
    }
    missing = sorted(required - set(joints))
    if missing:
        raise ValueError(f"pose plan is missing bilateral joints: {missing}")

    symmetry_errors: list[float] = []
    for joint in ("hip", "knee", "ankle", "toe", "shoulder", "elbow", "wrist"):
        left = joints[f"{joint}.L"]
        right = joints[f"{joint}.R"]
        if left[0] <= 0.0 or right[0] >= 0.0:
            raise ValueError(f"{joint} targets cross or collapse onto the midline")
        symmetry_errors.extend(
            (abs(left[0] + right[0]), abs(left[1] - right[1]), abs(left[2] - right[2]))
        )
    maximum_symmetry_error = max(symmetry_errors, default=0.0)
    if maximum_symmetry_error > height * 1.0e-6:
        raise ValueError("bilateral target symmetry drifted")

    if name in {"seated", "eating_ready"}:
        for side in ("L", "R"):
            if joints[f"knee.{side}"][1] >= joints[f"hip.{side}"][1]:
                raise ValueError("seated knees must be forward of the hips")
            if joints[f"ankle.{side}"][2] >= joints[f"knee.{side}"][2]:
                raise ValueError("seated ankles must be below the knees")

    # Ignore the proximal 24% of each thigh: the two legs legitimately meet the
    # shared pelvis there.  Distal thigh and lower-leg capsules must stay apart.
    radii = {"thigh": 0.032 * height, "calf": 0.026 * height}
    segments = {
        "thigh.L": (_lerp(joints["hip.L"], joints["knee.L"], 0.24), joints["knee.L"]),
        "thigh.R": (_lerp(joints["hip.R"], joints["knee.R"], 0.24), joints["knee.R"]),
        "calf.L": (joints["knee.L"], joints["ankle.L"]),
        "calf.R": (joints["knee.R"], joints["ankle.R"]),
    }
    pairs = (
        ("thigh.L", "thigh.R", radii["thigh"] * 2.0),
        ("thigh.L", "calf.R", radii["thigh"] + radii["calf"]),
        ("calf.L", "thigh.R", radii["calf"] + radii["thigh"]),
        ("calf.L", "calf.R", radii["calf"] * 2.0),
    )
    clearance_rows: list[dict[str, Any]] = []
    for left_name, right_name, combined_radius in pairs:
        centerline = segment_segment_distance(*segments[left_name], *segments[right_name])
        surface_clearance = centerline - combined_radius
        clearance_rows.append(
            {
                "first_segment": left_name,
                "second_segment": right_name,
                "centerline_distance_m": centerline,
                "combined_conservative_radius_m": combined_radius,
                "capsule_surface_clearance_m": surface_clearance,
            }
        )
    minimum_clearance = min(
        row["capsule_surface_clearance_m"] for row in clearance_rows
    )
    required_clearance = 0.006 * height if name in {"seated", "eating_ready"} else 0.0
    if minimum_clearance < required_clearance:
        raise ValueError("bilateral limb capsules overlap or lack required clearance")

    return {
        "passed": True,
        "pose_name": name,
        "checked_bilateral_joint_count": 7,
        "maximum_symmetry_error_m": maximum_symmetry_error,
        "minimum_capsule_surface_clearance_m": minimum_clearance,
        "required_capsule_surface_clearance_m": required_clearance,
        "capsule_pairs": clearance_rows,
        "crossed_leg_target_absence_proven": True,
        "mesh_visual_and_collision_review_still_required": True,
    }
