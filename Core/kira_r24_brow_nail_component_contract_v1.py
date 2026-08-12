"""Pure fail-closed contracts for the Kira R24 brow/nail preparation.

This module has no Blender dependency.  It deliberately cannot identify a
future body from a friendly name alone: the caller must bind the exact Blend,
body, rig, replaceable brow, twenty source nails, pose evidence, and append-only
output paths before the Blender preparation worker may begin.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from Core.avatar_nail_weight_constrained_projection_v1 import (
    NailWeightConstrainedProjectionError,
    hit_meets_declared_digit_gate,
    select_connected_weight_constrained_grid,
)


SCHEMA = "kira.r24.brow_nail_component_preparation.v1"
METHOD_ID = "kira_r24_connected_digit_nails_v2"
MODE = "NO_SAVE_PRIVATE_INACTIVE_PREPARATION"

R21_REJECTED_SOURCE_SHA256 = (
    "bb4d9a4b0d11c17047001278d7dadd105857bcc976ae7c0ec15a93b7945b00e4"
)
BROW_SOURCE_PATH = (
    "Avatar/private_owner_review/kira_r21_brow_only_correction_attempt_02/"
    "KIRA_R21_BALD_PRIVATE_INACTIVE_BROW_ATTEMPT02_REVIEW.blend"
)
BROW_SOURCE_SHA256 = (
    "5d6a5ee2eaad2b3a453bb439dcfc0df3864850723a0b60b9858c5d4d6ab648ae"
)
OLD_BROW_NAME = "Kira_R19_Accepted_Brows01"

BROW_BINDINGS = (
    {
        "object": "Kira_R21_Natural_Overlapping_Brow_Attempt02_NEGATIVE_X",
        "geometry_uv_sha256": (
            "68368c2f1047335d4830cf521e818ec3987d52cbc35aee27750b38871c4a99d0"
        ),
        "positive_weight_sha256": (
            "b046434607e8734700e88b767e3c8f2830ffd7949f0d8f957f4c4840970ac2eb"
        ),
        "bones": ("rBrowInner_0119", "rBrowMid_0120", "rBrowOuter_0122"),
    },
    {
        "object": "Kira_R21_Natural_Overlapping_Brow_Attempt02_POSITIVE_X",
        "geometry_uv_sha256": (
            "d265ca0226c62018dbe616278a31d74d6678e16c348df162adb9f7c96be58d96"
        ),
        "positive_weight_sha256": (
            "3614fb07165afc607cff98c76112e02a8507d81d0207fc2a50ae8b5c219cc985"
        ),
        "bones": ("lBrowInner_0123", "lBrowMid_0124", "lBrowOuter_0125"),
    },
)

NAIL_BINDINGS = (
    ("fingernail_1_L", "R19_BlackProject_fingernail_1_L_source_native", "lThumb3_049"),
    ("fingernail_2_L", "R19_BlackProject_fingernail_2_L_source_native", "lIndex3_053"),
    ("fingernail_3_L", "R19_BlackProject_fingernail_3_L_source_native", "lMid3_057"),
    ("fingernail_4_L", "R19_BlackProject_fingernail_4_L_source_native", "lRing3_061"),
    ("fingernail_5_L", "R19_BlackProject_fingernail_5_L_source_native", "lPinky3_065"),
    ("fingernail_1_R", "R19_BlackProject_fingernail_1_R_source_native", "rThumb3_074"),
    ("fingernail_2_R", "R19_BlackProject_fingernail_2_R_source_native", "rIndex3_078"),
    ("fingernail_3_R", "R19_BlackProject_fingernail_3_R_source_native", "rMid3_082"),
    ("fingernail_4_R", "R19_BlackProject_fingernail_4_R_source_native", "rRing3_01"),
    ("fingernail_5_R", "R19_BlackProject_fingernail_5_R_source_native", "rPinky3_088"),
    ("toenail_1_L", "R19_BlackProject_toenail_1_L_source_native", "lBigToe_2_020"),
    ("toenail_2_L", "R19_BlackProject_toenail_2_L_source_native", "lSmallToe1_2_018"),
    ("toenail_3_L", "R19_BlackProject_toenail_3_L_source_native", "lSmallToe2_2_016"),
    ("toenail_4_L", "R19_BlackProject_toenail_4_L_source_native", "lSmallToe3_2_014"),
    ("toenail_5_L", "R19_BlackProject_toenail_5_L_source_native", "lSmallToe4_2_012"),
    ("toenail_1_R", "R19_BlackProject_toenail_1_R_source_native", "rBigToe_2_036"),
    ("toenail_2_R", "R19_BlackProject_toenail_2_R_source_native", "rSmallToe1_2_034"),
    ("toenail_3_R", "R19_BlackProject_toenail_3_R_source_native", "rSmallToe2_2_032"),
    ("toenail_4_R", "R19_BlackProject_toenail_4_R_source_native", "rSmallToe3_2_030"),
    ("toenail_5_R", "R19_BlackProject_toenail_5_R_source_native", "rSmallToe4_2_028"),
)

MAXIMUM_REFERENCE_CENTER_ERROR_M = 0.0015
MAXIMUM_SAMPLE_DISPLACEMENT_M = 0.004
MINIMUM_CLEARANCE_M = 0.000040
MAXIMUM_CLEARANCE_M = 0.000450
MAXIMUM_FREE_EDGE_M = 0.000500
NAIL_PLATE_THICKNESS_M = 0.000180

EXPECTED_RENDER_KEYS = (
    "left_hand_dorsal",
    "left_hand_oblique",
    "right_hand_dorsal",
    "right_hand_oblique",
    "left_foot_dorsal",
    "left_foot_oblique",
    "right_foot_dorsal",
    "right_foot_oblique",
)

REQUIRED_POSE_KEYS = (
    "neutral",
    "left_finger_flex",
    "right_finger_flex",
    "open_hands",
    "closed_hands",
    "power_grip",
    "precision_grip",
    "toe_flex",
    "left_knee_bend",
    "right_knee_bend",
    "bilateral_knee_bend",
    "seated",
    "supine",
    "reach_object_use",
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class KiraR24ComponentContractError(ValueError):
    """Raised whenever a preparation binding or measured gate is incomplete."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def require_sha256(value: Any, label: str) -> str:
    normalized = str(value).strip().lower()
    if not _SHA256.fullmatch(normalized) or normalized == "0" * 64:
        raise KiraR24ComponentContractError(f"{label} is not an exact SHA-256")
    return normalized


def require_project_path(root: Path, value: Any, label: str) -> Path:
    text = str(value).strip().replace("\\", "/")
    if not text or Path(text).is_absolute():
        raise KiraR24ComponentContractError(
            f"{label} must be a nonempty project-relative path"
        )
    resolved_root = root.resolve()
    resolved = (resolved_root / Path(text)).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise KiraR24ComponentContractError(
            f"{label} resolves outside the project"
        ) from exc
    return resolved


def _exact_true(mapping: Mapping[str, Any], keys: Iterable[str], label: str) -> None:
    failed = [key for key in keys if mapping.get(key) is not True]
    if failed:
        raise KiraR24ComponentContractError(f"{label} gates are not true: {failed}")


def _require_exact_number(mapping: Mapping[str, Any], key: str, expected: float) -> None:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise KiraR24ComponentContractError(f"{key} is not numeric")
    if not math.isfinite(float(value)) or not math.isclose(
        float(value), expected, rel_tol=0.0, abs_tol=1.0e-12
    ):
        raise KiraR24ComponentContractError(
            f"{key} must remain exactly {expected}"
        )


def validate_config(
    raw: Mapping[str, Any],
    *,
    project_root: Path,
    verify_files: bool,
) -> dict[str, Any]:
    """Validate and normalize the exact future-candidate run contract."""

    if raw.get("schema") != SCHEMA or raw.get("mode") != MODE:
        raise KiraR24ComponentContractError("schema or no-save mode mismatch")
    if raw.get("status") != "PREPARED_NOT_RUN":
        raise KiraR24ComponentContractError("config is not PREPARED_NOT_RUN")

    candidate = raw.get("candidate")
    if not isinstance(candidate, Mapping):
        raise KiraR24ComponentContractError("candidate binding is missing")
    candidate_path = require_project_path(
        project_root, candidate.get("path"), "candidate.path"
    )
    candidate_sha = require_sha256(candidate.get("sha256"), "candidate.sha256")
    if candidate_sha == R21_REJECTED_SOURCE_SHA256:
        raise KiraR24ComponentContractError(
            "the rejected R21 pelvis source cannot be rebound as the future candidate"
        )
    _exact_true(
        candidate,
        ("private", "inactive", "unassigned", "unpublished"),
        "candidate boundary",
    )
    if candidate.get("runtime_activation_allowed") is not False:
        raise KiraR24ComponentContractError("candidate activation must be false")
    require_sha256(
        candidate.get("full_scene_state_sha256"),
        "candidate.full_scene_state_sha256",
    )

    body = candidate.get("body")
    rig = candidate.get("rig")
    old_brow = candidate.get("replaceable_old_brow")
    if not all(isinstance(row, Mapping) for row in (body, rig, old_brow)):
        raise KiraR24ComponentContractError("body/rig/old-brow bindings are incomplete")
    for field in (
        "complete_mesh_sha256",
        "geometry_uv_sha256",
        "positive_weight_sha256",
        "world_matrix_sha256",
        "modifier_stack_sha256",
    ):
        require_sha256(body.get(field), f"candidate.body.{field}")
    for field in ("rest_pose_sha256", "pose_sha256", "world_matrix_sha256"):
        require_sha256(rig.get(field), f"candidate.rig.{field}")
    if str(old_brow.get("object")) != OLD_BROW_NAME:
        raise KiraR24ComponentContractError("replaceable old brow identity drifted")
    for field in (
        "complete_mesh_sha256",
        "geometry_uv_sha256",
        "positive_weight_sha256",
        "world_matrix_sha256",
        "modifier_stack_sha256",
    ):
        require_sha256(old_brow.get(field), f"candidate.replaceable_old_brow.{field}")

    brow_source = raw.get("brow_source")
    if not isinstance(brow_source, Mapping):
        raise KiraR24ComponentContractError("brow source binding is missing")
    if str(brow_source.get("path")).replace("\\", "/") != BROW_SOURCE_PATH:
        raise KiraR24ComponentContractError("brow source path is not Attempt 02")
    if require_sha256(brow_source.get("sha256"), "brow_source.sha256") != BROW_SOURCE_SHA256:
        raise KiraR24ComponentContractError("brow source hash is not Attempt 02")
    if brow_source.get("author_new_brow_geometry") is not False:
        raise KiraR24ComponentContractError("third-brow authoring is forbidden")
    supplied_brows = brow_source.get("objects")
    if not isinstance(supplied_brows, Sequence) or isinstance(supplied_brows, (str, bytes)):
        raise KiraR24ComponentContractError("brow object bindings are missing")
    if json.loads(json.dumps(supplied_brows)) != json.loads(json.dumps(BROW_BINDINGS)):
        raise KiraR24ComponentContractError("Attempt 02 brow fingerprints drifted")

    source_nails = candidate.get("source_nails")
    if not isinstance(source_nails, Sequence) or isinstance(source_nails, (str, bytes)):
        raise KiraR24ComponentContractError("twenty source nail bindings are missing")
    if len(source_nails) != 20:
        raise KiraR24ComponentContractError("exactly twenty source nails are required")
    by_id = {str(row.get("nail_id")): row for row in source_nails if isinstance(row, Mapping)}
    if len(by_id) != 20:
        raise KiraR24ComponentContractError("source nail IDs are missing or duplicated")
    for nail_id, source_object, bone in NAIL_BINDINGS:
        row = by_id.get(nail_id)
        if row is None or str(row.get("source_object")) != source_object or str(row.get("bone")) != bone:
            raise KiraR24ComponentContractError(f"exact nail binding drifted: {nail_id}")
        for field in (
            "complete_mesh_sha256",
            "geometry_uv_sha256",
            "positive_weight_sha256",
            "world_matrix_sha256",
            "modifier_stack_sha256",
        ):
            require_sha256(row.get(field), f"source_nails.{nail_id}.{field}")
        anchor = row.get("corrected_anchor_world_m")
        if not _finite_vector(anchor, 3):
            raise KiraR24ComponentContractError(f"source_nails.{nail_id} anchor invalid")

    gates = raw.get("gates")
    if not isinstance(gates, Mapping):
        raise KiraR24ComponentContractError("mandatory gates are missing")
    _exact_true(
        gates,
        (
            "component_id_zero_rejected",
            "corrected_reference_center_controls_placement",
            "full_modifier_stack_bound",
            "full_scene_state_bound",
            "render_before_any_save",
            "all_pose_contact_intersection_gates_required",
            "no_third_brow_authoring",
            "no_partial_candidate",
        ),
        "component preparation",
    )
    _require_exact_number(gates, "maximum_reference_center_error_m", MAXIMUM_REFERENCE_CENTER_ERROR_M)
    _require_exact_number(gates, "maximum_sample_displacement_m", MAXIMUM_SAMPLE_DISPLACEMENT_M)
    _require_exact_number(gates, "minimum_clearance_m", MINIMUM_CLEARANCE_M)
    _require_exact_number(gates, "maximum_clearance_m", MAXIMUM_CLEARANCE_M)
    _require_exact_number(gates, "maximum_free_edge_m", MAXIMUM_FREE_EDGE_M)
    _require_exact_number(gates, "nail_plate_thickness_m", NAIL_PLATE_THICKNESS_M)

    pose_evidence = raw.get("pose_evidence")
    if not isinstance(pose_evidence, Mapping):
        raise KiraR24ComponentContractError("pose evidence binding is missing")
    pose_path = require_project_path(
        project_root, pose_evidence.get("path"), "pose_evidence.path"
    )
    pose_sha = require_sha256(pose_evidence.get("sha256"), "pose_evidence.sha256")
    if require_sha256(
        pose_evidence.get("candidate_sha256"), "pose_evidence.candidate_sha256"
    ) != candidate_sha:
        raise KiraR24ComponentContractError("pose evidence belongs to another candidate")

    output = raw.get("output")
    if not isinstance(output, Mapping):
        raise KiraR24ComponentContractError("output binding is missing")
    if output.get("candidate_blend") is not None or output.get("save_blend_allowed") is not False:
        raise KiraR24ComponentContractError("the preparation worker is no-save")
    evidence_dir = require_project_path(
        project_root, output.get("evidence_dir"), "output.evidence_dir"
    )
    render_dir = require_project_path(
        project_root, output.get("render_staging_dir"), "output.render_staging_dir"
    )
    if evidence_dir == render_dir or render_dir.parent != evidence_dir:
        raise KiraR24ComponentContractError(
            "render staging must be a direct child of the append-only evidence directory"
        )

    if verify_files:
        expected_files = (
            (candidate_path, candidate_sha, "candidate"),
            (require_project_path(project_root, BROW_SOURCE_PATH, "brow source"), BROW_SOURCE_SHA256, "brow source"),
            (pose_path, pose_sha, "pose evidence"),
        )
        for path, expected, label in expected_files:
            if not path.is_file() or sha256_file(path) != expected:
                raise KiraR24ComponentContractError(f"{label} file/hash mismatch")
        if evidence_dir.exists() or render_dir.exists():
            raise KiraR24ComponentContractError("append-only output already exists")

    return {
        "candidate_path": candidate_path,
        "candidate_sha256": candidate_sha,
        "body": dict(body),
        "rig": dict(rig),
        "old_brow": dict(old_brow),
        "source_nails": by_id,
        "pose_evidence_path": pose_path,
        "pose_evidence_sha256": pose_sha,
        "evidence_dir": evidence_dir,
        "render_dir": render_dir,
        "raw": dict(raw),
    }


def _finite_vector(value: Any, length: int) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and len(value) == length
        and all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and math.isfinite(float(item))
            for item in value
        )
    )


def hit_meets_declared_digit_gate_v2(raw: Mapping[str, Any]) -> bool:
    """The reserved zero component is never a connected digit component."""

    try:
        component = int(raw.get("raw_component_id"))
    except (TypeError, ValueError):
        return False
    return component > 0 and hit_meets_declared_digit_gate(raw)


def select_connected_weight_constrained_grid_v2(
    hit_stacks: Sequence[Sequence[Mapping[str, Any]]],
    *,
    center_sample_index: int,
) -> dict[str, Any]:
    filtered = [
        [dict(hit) for hit in stack if hit_meets_declared_digit_gate_v2(hit)]
        for stack in hit_stacks
    ]
    if not filtered or not filtered[center_sample_index]:
        raise NailWeightConstrainedProjectionError(
            "center sample has no positive connected digit component"
        )
    result = select_connected_weight_constrained_grid(
        filtered, center_sample_index=center_sample_index
    )
    if int(result["selected_raw_component_id"]) <= 0:
        raise NailWeightConstrainedProjectionError(
            "reserved component zero reached the selected grid"
        )
    return result


def _distance(left: Sequence[float], right: Sequence[float]) -> float:
    if not _finite_vector(left, 3) or not _finite_vector(right, 3):
        raise KiraR24ComponentContractError("point is not a finite 3-vector")
    return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(left, right)))


def validate_reference_bound_candidate(
    *,
    reference_center: Sequence[float],
    candidate_center: Sequence[float],
    projected_points: Sequence[Sequence[float]],
    expected_points: Sequence[Sequence[float]],
) -> dict[str, Any]:
    if len(projected_points) != 81 or len(expected_points) != 81:
        raise KiraR24ComponentContractError("a complete 9x9 footprint is required")
    center_error = _distance(reference_center, candidate_center)
    projected_centroid = [
        sum(float(point[axis]) for point in projected_points) / len(projected_points)
        for axis in range(3)
    ]
    centroid_error = _distance(reference_center, projected_centroid)
    displacements = [
        _distance(expected, projected)
        for expected, projected in zip(expected_points, projected_points)
    ]
    maximum_displacement = max(displacements)
    if center_error > MAXIMUM_REFERENCE_CENTER_ERROR_M:
        raise KiraR24ComponentContractError("candidate center escaped the source landmark")
    if centroid_error > MAXIMUM_REFERENCE_CENTER_ERROR_M:
        raise KiraR24ComponentContractError("projected centroid escaped the source landmark")
    if maximum_displacement > MAXIMUM_SAMPLE_DISPLACEMENT_M:
        raise KiraR24ComponentContractError("a projection sample moved more than 4 mm")
    return {
        "candidate_center_to_reference_m": center_error,
        "projected_centroid_to_reference_m": centroid_error,
        "maximum_sample_displacement_m": maximum_displacement,
        "all_reference_binding_gates_passed": True,
    }


def validate_pose_gate_matrix(raw: Mapping[str, Any], candidate_sha256: str) -> dict[str, Any]:
    if require_sha256(raw.get("candidate_sha256"), "pose matrix candidate") != require_sha256(
        candidate_sha256, "expected pose candidate"
    ):
        raise KiraR24ComponentContractError("pose matrix belongs to another candidate")
    rows = raw.get("poses")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise KiraR24ComponentContractError("pose rows are missing")
    by_key = {str(row.get("pose")): row for row in rows if isinstance(row, Mapping)}
    if set(by_key) != set(REQUIRED_POSE_KEYS):
        raise KiraR24ComponentContractError("pose inventory is incomplete or contains extras")
    for key in REQUIRED_POSE_KEYS:
        row = by_key[key]
        require_sha256(row.get("action_sha256"), f"pose {key} action")
        _exact_true(
            row,
            (
                "contact_gate_passed",
                "all_20_nails_attached",
                "all_clearance_gates_passed",
                "no_body_nail_intersections",
                "no_nail_pair_overlap",
            ),
            f"pose {key}",
        )
        if int(row.get("nail_count", -1)) != 20:
            raise KiraR24ComponentContractError(f"pose {key} does not contain 20 nails")
        if int(row.get("exact_body_nail_crossing_pair_count", -1)) != 0:
            raise KiraR24ComponentContractError(f"pose {key} has a body/nail crossing")
        if int(row.get("tested_nail_pair_count", -1)) != 190:
            raise KiraR24ComponentContractError(f"pose {key} did not test all nail pairs")
        minimum = float(row.get("minimum_clearance_m", -1.0))
        maximum = float(row.get("maximum_clearance_m", math.inf))
        if minimum < MINIMUM_CLEARANCE_M or maximum > MAXIMUM_CLEARANCE_M:
            raise KiraR24ComponentContractError(f"pose {key} clearance is out of bounds")
    return {
        "required_pose_count": len(REQUIRED_POSE_KEYS),
        "required_pose_keys": list(REQUIRED_POSE_KEYS),
        "all_pose_contact_intersection_gates_passed": True,
    }


def validate_render_inventory(render_dir: Path, records: Mapping[str, Any]) -> dict[str, Any]:
    if set(records) != set(EXPECTED_RENDER_KEYS):
        raise KiraR24ComponentContractError("exactly eight named renders are required")
    resolved_root = render_dir.resolve()
    checked: dict[str, Any] = {}
    for key in EXPECTED_RENDER_KEYS:
        path = (resolved_root / str(records[key])).resolve()
        try:
            path.relative_to(resolved_root)
        except ValueError as exc:
            raise KiraR24ComponentContractError("render path escaped staging") from exc
        if not path.is_file() or path.stat().st_size <= 8:
            raise KiraR24ComponentContractError(f"render is absent or empty: {key}")
        with path.open("rb") as stream:
            signature = stream.read(8)
        if signature != b"\x89PNG\r\n\x1a\n":
            raise KiraR24ComponentContractError(f"render is not a readable PNG: {key}")
        checked[key] = {
            "path": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    return {"render_count": 8, "renders": checked, "all_render_gates_passed": True}


def validate_no_save_transaction(events: Sequence[str]) -> dict[str, Any]:
    required = (
        "exact_bindings_verified",
        "components_built_in_memory",
        "pose_gates_validated",
        "renders_validated",
        "protected_state_reverified",
        "evidence_written",
        "no_save_exit",
    )
    if any("save" in str(event).lower() and event != "no_save_exit" for event in events):
        raise KiraR24ComponentContractError("a save event is forbidden in preparation")
    positions = []
    for event in required:
        if events.count(event) != 1:
            raise KiraR24ComponentContractError(f"transaction event missing/duplicated: {event}")
        positions.append(events.index(event))
    if positions != sorted(positions):
        raise KiraR24ComponentContractError("transaction events are out of order")
    return {
        "events": list(events),
        "render_completed_before_no_save_exit": True,
        "blend_saved": False,
        "transaction_passed": True,
    }


__all__ = [
    "BROW_BINDINGS",
    "BROW_SOURCE_PATH",
    "BROW_SOURCE_SHA256",
    "EXPECTED_RENDER_KEYS",
    "KiraR24ComponentContractError",
    "MAXIMUM_CLEARANCE_M",
    "MAXIMUM_FREE_EDGE_M",
    "MAXIMUM_REFERENCE_CENTER_ERROR_M",
    "MAXIMUM_SAMPLE_DISPLACEMENT_M",
    "METHOD_ID",
    "MINIMUM_CLEARANCE_M",
    "MODE",
    "NAIL_BINDINGS",
    "NAIL_PLATE_THICKNESS_M",
    "OLD_BROW_NAME",
    "REQUIRED_POSE_KEYS",
    "SCHEMA",
    "canonical_json_sha256",
    "hit_meets_declared_digit_gate_v2",
    "require_project_path",
    "require_sha256",
    "select_connected_weight_constrained_grid_v2",
    "sha256_file",
    "validate_config",
    "validate_no_save_transaction",
    "validate_pose_gate_matrix",
    "validate_reference_bound_candidate",
    "validate_render_inventory",
]
