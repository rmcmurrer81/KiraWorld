"""Fail-closed audit and private roster records for rapid body candidates.

This module belongs to the existing Avatar Builder workspace.  It does not
launch Blender, create a second user interface, assign a body, activate a
person, or alter runtime state.

The enrolled adult body assets are engineering/cage sources, not finished
people.  A rapid candidate is admitted to the *private inspection roster* only
when:

* the request is valid and its exact hash is bound to the build evidence;
* the selected source is an exact enrolled cage-fit source whose unmodified
  copying is forbidden;
* an exact, distinct GLB candidate exists inside the request's private root;
* independent GLB envelope/skin/rig inspection and Blender-authored evidence
  pass the bounded structural gates;
* all required renders are exact-hash bound and an independent visual review
  explicitly says the candidate is suitable to show for private inspection;
* no Robert-private reference path or person-specific payload entered the
  package; and
* every recorded runtime sentinel remains byte-for-byte unchanged.

Roster admission is not owner approval, Kira selection, runtime assignment,
movement approval, clothing approval, final-hair approval, or publication
authority.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from Core.avatar_body_topology import inspect_glb_topology
from Core.avatar_rapid_body_request import (
    RapidBodyRequestError,
    validate_rapid_body_request,
)


SOURCE_AUTHORITY_PATH = Path(
    "Avatar/avatar_builder/multiview_authoring/base_catalog/authority.json"
)
PRIVATE_ROSTER_PATH = Path(
    "Avatar/avatar_builder/rapid_body_pipeline/private_inspection_roster_v1.json"
)

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PRIVATE_SOURCE_MARKERS = (
    "avatar/private_owner_review/dual_robert",
    "biological_robert",
    "synthetic_robert",
    "robert_avatar",
    "robert avatar base",
    "desktop/reference",
    "desktop/robert",
    "protected_reference/robert",
    "reference_measurements/robert",
    "likeness_v1",
    "likeness_v14",
    "likeness_v15",
    "likeness_v17",
    "likeness_v18",
    "likeness_v19",
    "likeness_v20",
    "likeness_v21",
    "likeness_v22",
    "likeness_v23",
    "likeness_v24",
)
REQUIRED_RENDER_LABELS = (
    "neutral_front",
    "neutral_back",
    "neutral_left_profile",
    "neutral_right_profile",
    "neutral_left_three_quarter",
    "neutral_right_three_quarter",
    "face_close_front",
    "crown_top_close",
    "rear_hairline_close",
    "left_hand_nail_close",
    "left_foot_nail_close",
    "protected_adult_surface_front",
    "protected_adult_surface_side",
    "pose_reach",
    "pose_stride",
    "pose_seated",
    "pose_hip_flexion",
    "pose_hand",
    "pose_knee_flexion",
    "pose_knee_flexion_right",
)
REQUIRED_DEFORMATION_POSE_LABELS = (
    "reach",
    "stride",
    "seated",
    "hip_flexion",
    "hand",
    "knee_flexion",
    "knee_flexion_right",
)
REQUIRED_ANATOMICAL_KNEE_DIRECTION_LABELS = (
    "knee_flexion",
    "knee_flexion_right",
)
REQUIRED_TRUE_BUILD_GATES = (
    "new_transformed_surface_not_unmodified_copy",
    "one_connected_primary_body_surface",
    "zero_primary_body_nonmanifold_edges",
    "known_boundary_cycles_reported",
    "integrated_external_adult_form_engineering_gate",
    "adult_surface_matches_requested_body_class",
    "movement_ready_structural_and_bounded_pose_gate",
    "brown_review_eyes_present",
    "straight_black_removable_review_hair_present",
    "ordinary_finger_and_toe_nail_review_components_present",
    "future_clothing_structural_compatibility",
    "future_hair_structural_compatibility",
)
DERIVATIVE_REQUIRED_TRUE_BUILD_GATES = (
    "author_topology_gate",
    "author_weight_gate",
    "author_bounded_deformation_gate",
    "author_combined_gate",
)
DERIVATIVE_REQUIRED_FALSE_PRIVACY_FIELDS = (
    "robert_private_photos_used",
    "robert_measurements_used",
    "robert_morphs_or_surface_used",
    "identifiable_person_likeness_used",
    "runtime_files_read_or_written_by_worker",
)
DERIVATIVE_RENDER_ALIASES = {
    "neutral_front": ("neutral_front", "front"),
    "neutral_back": ("neutral_back", "rear"),
    "neutral_left_profile": ("neutral_left_profile", "left_profile"),
    "neutral_right_profile": ("neutral_right_profile", "right_profile"),
    "neutral_left_three_quarter": (
        "neutral_left_three_quarter",
        "left_three_quarter",
    ),
    "neutral_right_three_quarter": (
        "neutral_right_three_quarter",
        "right_three_quarter",
    ),
    "face_close_front": ("face_close_front", "face_close"),
    "crown_top_close": (
        "crown_top_close",
        "crown_close",
        "scalp_crown_close",
        "top_of_head_close",
    ),
    "rear_hairline_close": (
        "rear_hairline_close",
        "hairline_rear_close",
        "back_hairline_close",
    ),
    "left_hand_nail_close": (
        "left_hand_nail_close",
        "left_hand_nails_close",
    ),
    "left_foot_nail_close": (
        "left_foot_nail_close",
        "left_foot_toenails_close",
    ),
    "protected_adult_surface_front": (
        "protected_adult_surface_front",
        "adult_surface_front_close",
    ),
    "protected_adult_surface_side": (
        "protected_adult_surface_side",
        "adult_surface_side_close",
        "adult_surface_three_quarter_close",
    ),
    "pose_reach": ("pose_reach",),
    "pose_stride": ("pose_stride",),
    "pose_seated": ("pose_seated",),
    "pose_hip_flexion": ("pose_hip_flexion",),
    "pose_hand": ("pose_hand", "pose_hand_test"),
    "pose_knee_flexion": ("pose_knee_flexion",),
    "pose_knee_flexion_right": (
        "pose_knee_flexion_right",
        "pose_right_knee_flexion",
    ),
}
REQUIRED_VISUAL_REVIEW_CHECKS = (
    "overall_body_direction_preserved",
    "knees_no_reverse_or_hyperextension",
    "eyes_no_hard_bands_or_uv_material_artifacts",
    "scalp_no_nonhair_black_patch_or_cap_artifact",
    "seated_contact_no_penetration_or_floating",
    "requested_hair_texture_visibly_met",
    "fingernails_attached_and_ordinary",
    "toenails_attached_and_ordinary",
    "protected_adult_surface_complete_and_natural",
    "protected_adult_surface_matches_requested_body_class",
    "skin_and_component_material_continuity",
)
VISUAL_CHECK_RELEVANT_RENDER_LABELS = {
    "overall_body_direction_preserved": {
        "neutral_front",
        "neutral_back",
        "neutral_left_profile",
        "neutral_right_profile",
        "neutral_left_three_quarter",
        "neutral_right_three_quarter",
    },
    "knees_no_reverse_or_hyperextension": {
        "pose_knee_flexion",
        "pose_knee_flexion_right",
        "pose_stride",
        "pose_seated",
        "pose_hip_flexion",
    },
    "eyes_no_hard_bands_or_uv_material_artifacts": {
        "face_close_front",
    },
    "scalp_no_nonhair_black_patch_or_cap_artifact": {
        "crown_top_close",
        "rear_hairline_close",
    },
    "seated_contact_no_penetration_or_floating": {
        "pose_seated",
    },
    "requested_hair_texture_visibly_met": {
        "neutral_front",
        "neutral_left_profile",
        "neutral_right_profile",
        "neutral_back",
        "crown_top_close",
        "rear_hairline_close",
    },
    "fingernails_attached_and_ordinary": {
        "left_hand_nail_close",
        "pose_hand",
    },
    "toenails_attached_and_ordinary": {
        "left_foot_nail_close",
    },
    "protected_adult_surface_complete_and_natural": {
        "protected_adult_surface_front",
        "protected_adult_surface_side",
    },
    "protected_adult_surface_matches_requested_body_class": {
        "protected_adult_surface_front",
        "protected_adult_surface_side",
    },
    "skin_and_component_material_continuity": set(REQUIRED_RENDER_LABELS),
}
VISUAL_CHECK_REQUIRED_RENDER_LABELS = {
    "knees_no_reverse_or_hyperextension": {
        "pose_knee_flexion",
        "pose_knee_flexion_right",
    },
    "scalp_no_nonhair_black_patch_or_cap_artifact": {
        "crown_top_close",
        "rear_hairline_close",
    },
    "requested_hair_texture_visibly_met": {
        "neutral_front",
        "neutral_back",
        "crown_top_close",
        "rear_hairline_close",
    },
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _text(value).lower()).strip("_")


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _valid_digest(value: Any) -> bool:
    return bool(SHA256_RE.fullmatch(_text(value).lower()))


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _resolve_project_file(
    project_root: Path,
    raw_path: Any,
    *,
    must_exist: bool = True,
) -> Path | None:
    text = _text(raw_path)
    if not text:
        return None
    candidate = Path(text)
    if not candidate.is_absolute():
        if ".." in candidate.parts:
            return None
        candidate = project_root / candidate
    try:
        resolved = candidate.resolve(strict=must_exist)
        resolved.relative_to(project_root.resolve(strict=True))
    except (OSError, ValueError):
        return None
    if must_exist and not resolved.is_file():
        return None
    return resolved


def _relative(project_root: Path, path: Path) -> str:
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def _binding_matches(
    project_root: Path,
    raw: Any,
    *,
    label: str,
    failures: list[str],
) -> tuple[Path | None, str]:
    if not isinstance(raw, Mapping):
        failures.append(f"{label}_binding_missing")
        return None, ""
    digest = _text(raw.get("sha256")).lower()
    if not _valid_digest(digest):
        failures.append(f"{label}_sha256_invalid")
    path = _resolve_project_file(project_root, raw.get("path"))
    if path is None:
        failures.append(f"{label}_path_invalid")
        return None, digest
    if _valid_digest(digest) and sha256_file(path) != digest:
        failures.append(f"{label}_sha256_mismatch")
    if "size_bytes" in raw:
        try:
            expected_size = int(raw.get("size_bytes"))
        except (TypeError, ValueError):
            failures.append(f"{label}_size_invalid")
        else:
            if path.stat().st_size != expected_size:
                failures.append(f"{label}_size_mismatch")
    return path, digest


def _private_source_findings(value: Any) -> list[str]:
    """Find private identity-source contamination without echoing values.

    Required statements such as ``robert_private_data_allowed: false`` are
    intentionally allowed.  This scanner targets source/path strings and
    person-specific payload fields rather than the mere word "Robert".
    """

    findings: list[str] = []

    def visit(current: Any, path: tuple[str, ...]) -> None:
        if isinstance(current, Mapping):
            for raw_key, child in current.items():
                key = _normalized(raw_key)
                field = ".".join((*path, key))
                if any(
                    token in key
                    for token in (
                        "identity_measurement",
                        "likeness_delta",
                        "private_anatomy_observation",
                        "person_specific_coordinate",
                        "owner_photo_landmark",
                        "robert_reference_hash",
                    )
                ):
                    findings.append(f"private_person_payload_key:{field}")
                visit(child, (*path, key))
            return
        if isinstance(current, (list, tuple)):
            for index, child in enumerate(current):
                visit(child, (*path, str(index)))
            return
        if not isinstance(current, str):
            return
        lowered = current.replace("\\", "/").casefold()
        if any(marker in lowered for marker in PRIVATE_SOURCE_MARKERS):
            findings.append(
                "prohibited_private_identity_source:"
                + (".".join(path) or "root")
            )

    visit(value, ())
    return _dedupe(findings)


def _source_authority(
    project_root: Path,
    source_path: Path,
    source_sha256: str,
    *,
    authority_path: Path,
    failures: list[str],
) -> dict[str, Any]:
    path = project_root / authority_path
    try:
        authority = _read_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        failures.append("source_authority_unreadable")
        return {}
    if authority.get("schema_version") != 1:
        failures.append("source_authority_schema_invalid")
    entries = authority.get("entries")
    if not isinstance(entries, list):
        failures.append("source_authority_entries_invalid")
        entries = []
    matches: list[Mapping[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        entry_path = _resolve_project_file(project_root, entry.get("path"))
        if (
            entry_path == source_path
            and _text(entry.get("sha256")).lower() == source_sha256
        ):
            matches.append(entry)
    if len(matches) != 1:
        failures.append("source_not_exactly_enrolled_in_authority_catalog")
        return {
            "catalog_path": authority_path.as_posix(),
            "catalog_sha256": sha256_file(path),
        }
    entry = matches[0]
    if _normalized(entry.get("topology_lane")) != "confirmed_adult_topology":
        failures.append("source_not_in_adult_engineering_lane")
    if (
        _normalized(entry.get("allowed_use"))
        != "cage_fit_source_new_surface_required"
    ):
        failures.append("source_not_authorized_for_bounded_cage_fit")
    if entry.get("copy_as_candidate_body_allowed") is not False:
        failures.append("source_must_forbid_unmodified_candidate_copy")
    maturity = entry.get("maturity_authority")
    if not isinstance(maturity, Mapping) or maturity.get("adult_only") is not True:
        failures.append("source_adult_only_authority_missing")
    structural = entry.get("structural_audit")
    if not isinstance(structural, Mapping) or structural.get("valid_glb") is not True:
        failures.append("source_structural_audit_invalid")

    # Deliberately do not convert local embedded metadata into a public-release
    # license claim.  This private proof has no publication/export authority.
    return {
        "catalog_path": authority_path.as_posix(),
        "catalog_sha256": sha256_file(path),
        "base_id": _text(entry.get("base_id")),
        "source_path": _relative(project_root, source_path),
        "source_sha256": source_sha256,
        "source_role": "ENROLLED_ADULT_CAGE_FIT_ENGINEERING_SOURCE_ONLY",
        "allowed_use": _text(entry.get("allowed_use")),
        "copy_as_candidate_body_allowed": False,
        "source_stable_working_rig_proven": bool(
            entry.get("stable_working_rig_proven")
        ),
        "source_anatomical_completeness_proven": bool(
            entry.get("anatomical_completeness_proven")
        ),
        "known_boundary_loops": entry.get("known_boundary_loops"),
        "license_release_status": (
            "LOCAL_METADATA EXISTS; NOT REVALIDATED FOR PUBLIC RELEASE"
        ),
        "public_release_allowed": False,
        "truth_note": (
            "The source is a cage-fit engineering input, not a complete body "
            "and not a selectable Avatar Builder result. Candidate structure "
            "must be proven independently on the derivative artifact."
        ),
    }


def _bound_derivative_source_authority(
    project_root: Path,
    source_path: Path,
    source_sha256: str,
    binding: Any,
    *,
    failures: list[str],
) -> dict[str, Any]:
    """Validate a source-adjacent, exact-hash derivative authority record."""

    authority_path, authority_sha256 = _binding_matches(
        project_root,
        binding,
        label="source_derivative_authority",
        failures=failures,
    )
    if authority_path is None:
        return {}
    try:
        authority = _read_json(authority_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        failures.append("source_derivative_authority_unreadable")
        return {}
    if authority.get("schema_version") != 1:
        failures.append("source_derivative_authority_schema_invalid")
    local_asset = authority.get("local_asset")
    if not isinstance(local_asset, Mapping):
        failures.append("source_derivative_authority_local_asset_missing")
        local_asset = {}
    authorized_path = _resolve_project_file(
        project_root,
        local_asset.get("path"),
    )
    if authorized_path != source_path:
        failures.append("source_derivative_authority_path_mismatch")
    if _text(local_asset.get("sha256")).lower() != source_sha256:
        failures.append("source_derivative_authority_sha256_mismatch")
    if _text(local_asset.get("copy_policy")) != (
        "exact_byte_copy_of_reviewed_source; do_not_replace_in_place"
    ):
        failures.append("source_derivative_authority_copy_policy_invalid")

    source = authority.get("source")
    if not isinstance(source, Mapping):
        failures.append("source_derivative_provenance_missing")
        source = {}
    for field in ("title", "author", "source_url", "license", "license_url"):
        if not _text(source.get(field)):
            failures.append(f"source_derivative_provenance_missing:{field}")
    if source.get("attribution_required_on_derivatives") is not True:
        failures.append("source_derivative_attribution_requirement_missing")

    reviewed = authority.get("reviewed_structure")
    if not isinstance(reviewed, Mapping):
        failures.append("source_derivative_structure_record_missing")
        reviewed = {}
    try:
        joint_count = int(reviewed.get("joint_count", 0))
        mesh_count = int(reviewed.get("mesh_count", 0))
    except (TypeError, ValueError):
        joint_count = 0
        mesh_count = 0
    if joint_count < 15 or mesh_count < 1:
        failures.append("source_derivative_structure_record_invalid")
    allowed = authority.get("allowed_use")
    if not isinstance(allowed, Mapping):
        failures.append("source_derivative_allowed_use_missing")
        allowed = {}
    if (
        _normalized(allowed.get("lane"))
        != "adult_female_avatar_derivative"
    ):
        failures.append("source_derivative_lane_invalid")
    if allowed.get("may_export_private_derivative_candidate") is not True:
        failures.append("source_private_derivative_export_not_authorized")
    if (
        allowed.get("may_activate_or_replace_runtime_without_separate_approval")
        is not False
    ):
        failures.append("source_authority_runtime_boundary_invalid")
    forbidden = authority.get("forbidden_use")
    if not isinstance(forbidden, Mapping):
        failures.append("source_derivative_forbidden_use_missing")
        forbidden = {}
    for field in (
        "minor_or_age_ambiguous_lane",
        "robert_private_reference_input",
        "claim_source_is_kira_likeness",
        "claim_complete_topology_from_filename_or_metadata_alone",
        "runtime_assignment_without_owner_approval",
        "public_distribution_without_required_attribution_and_review",
    ):
        if forbidden.get(field) is not True:
            failures.append(
                f"source_derivative_forbidden_use_not_enforced:{field}"
            )
    return {
        "authority_path": _relative(project_root, authority_path),
        "authority_sha256": authority_sha256,
        "authority_id": _text(authority.get("authority_id")),
        "source_path": _relative(project_root, source_path),
        "source_sha256": source_sha256,
        "source_role": (
            "LICENSED_ADULT_FEMALE_DERIVATIVE_ENGINEERING_SOURCE;"
            " NOT A FINISHED OR SELECTABLE BODY"
        ),
        "provenance": {
            "title": _text(source.get("title")),
            "author": _text(source.get("author")),
            "source_url": _text(source.get("source_url")),
            "license": _text(source.get("license")),
            "license_url": _text(source.get("license_url")),
            "attribution_required": True,
        },
        "source_structure": {
            "mesh_count": mesh_count,
            "joint_count": joint_count,
            "adult_external_component_present": bool(
                reviewed.get("adult_external_anatomy_component_present")
            ),
        },
        "source_stable_working_rig_proven": False,
        "source_anatomical_completeness_proven": False,
        "candidate_must_be_distinct_derivative": True,
        "public_release_allowed": False,
        "truth_note": (
            "The authority permits a private adult-female derivative while "
            "requiring attribution. It does not certify candidate topology, "
            "visual completeness, motion, owner approval, or runtime use."
        ),
    }


def build_workspace_record(
    project_root: Path,
    request_path: Path,
) -> dict[str, Any]:
    """Create an owner-readable, non-runtime Avatar Builder workspace record."""

    root = project_root.resolve(strict=True)
    path = request_path.resolve(strict=True)
    payload = _read_json(path)
    summary = validate_rapid_body_request(payload)
    parameters = summary["parameters"]
    numeric = {
        name: parameters[name]
        for name in (
            "muscularity",
            "body_mass",
            "shoulder_width",
            "chest_torso",
            "waist_abdomen",
            "hips_pelvis",
            "arms",
            "legs",
            "hands",
            "feet",
            "neck",
        )
    }
    return {
        "schema_version": 1,
        "artifact_type": "avatar_builder_rapid_body_workspace_record",
        "workspace_id": f"{summary['owner_id']}_temporary_functional_body_20260730",
        "owner_id": summary["owner_id"],
        "owner_name": summary["owner_name"],
        "normal_entry_point": "EXISTING_AVATAR_BUILDER_WORKSPACE",
        "request": {
            "path": _relative(root, path),
            "sha256": sha256_file(path),
        },
        "candidate_state": "PRIVATE_INSPECTION_CANDIDATE",
        "skeleton_policy": {
            "accepted_private_candidate_profile": (
                "ANY_INDEPENDENTLY_PROVEN_ADULT_HUMANOID_RIG"
            ),
            "fixed_runtime_joint_count_required_at_this_phase": False,
            "candidate_skeleton_profile_record_required": True,
            "future_runtime_adapter_or_eligibility_proof_required": True,
            "current_runtime_compatibility_claimed": False,
        },
        "runtime_assignment": {
            "allowed": False,
            "performed": False,
            "runtime_profile_truth": "NO_BODY_UNCHANGED",
        },
        "owner_controls": {
            "height": {
                "height_m": parameters["height_m"],
                "bounded_range_m": [1.35, 2.20],
            },
            "build": {
                "preset": parameters["build_preset"],
                "muscularity": parameters["muscularity"],
                "body_mass": parameters["body_mass"],
            },
            "torso_waist_hips": {
                "shoulders": parameters["shoulder_width"],
                "chest_torso": parameters["chest_torso"],
                "waist_abdomen": parameters["waist_abdomen"],
                "hips_pelvis": parameters["hips_pelvis"],
            },
            "arms_legs": {
                "arms": parameters["arms"],
                "legs": parameters["legs"],
            },
            "hands_feet": {
                "hands": parameters["hands"],
                "feet": parameters["feet"],
            },
            "neck": parameters["neck"],
            "face": parameters["face_landmarks"],
            "skin": parameters["skin_direction"],
            "eyes": parameters["iris_color"],
            "hair": deepcopy(parameters["hair"]),
            "anatomy": {
                "requested": "integrated_adult_anatomy",
                "status": "REQUIRED_UNPROVEN_UNTIL_EXACT_CANDIDATE_AUDIT",
                "owner_visual_acceptance": False,
                "movement_function_proven": False,
            },
        },
        "privacy": {
            "private_local_review_only": True,
            "robert_private_data_allowed": False,
            "identifiable_person_likeness_allowed": False,
        },
        "approval_truth": {
            "owner_approved": False,
            "kira_selected": False,
            "movement_approved": False,
            "clothing_approved": False,
            "final_hair_approved": False,
        },
        "no_new_launcher_or_interface_created": True,
    }


def evaluate_candidate_package(
    project_root: Path,
    request_path: Path,
    evidence_path: Path,
    *,
    topology_audit: Mapping[str, Any] | None = None,
    topology_audit_path: Path | None = None,
    deformation_audit: Mapping[str, Any] | None = None,
    deformation_audit_path: Path | None = None,
    visual_review: Mapping[str, Any] | None = None,
    authority_path: Path = SOURCE_AUTHORITY_PATH,
) -> dict[str, Any]:
    """Independently audit one exact rapid-body package without mutation."""

    root = project_root.resolve(strict=True)
    failures: list[str] = []
    warnings: list[str] = []
    try:
        request = _read_json(request_path)
        request_summary = validate_rapid_body_request(request)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
        RapidBodyRequestError,
    ) as exc:
        return {
            "schema_version": 1,
            "gate": "avatar_builder_rapid_body_candidate_v1",
            "status": "BLOCKED",
            "private_inspection_roster_admission_allowed": False,
            "runtime_assignment_allowed": False,
            "failures": [f"request_invalid:{type(exc).__name__}"],
        }
    try:
        evidence = _read_json(evidence_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "schema_version": 1,
            "gate": "avatar_builder_rapid_body_candidate_v1",
            "status": "BLOCKED",
            "private_inspection_roster_admission_allowed": False,
            "runtime_assignment_allowed": False,
            "failures": [f"build_evidence_invalid:{type(exc).__name__}"],
        }

    derivative_schema = isinstance(evidence.get("sources"), Mapping)
    evidence_family = (
        "licensed_derivative_foundation_v1"
        if derivative_schema
        else "enrolled_cage_fit_v1"
    )
    failures.extend(_private_source_findings(request))
    failures.extend(_private_source_findings(evidence))
    privacy = evidence.get("privacy")
    if not isinstance(privacy, Mapping):
        failures.append("build_privacy_record_missing")
        privacy = {}
    privacy_false_fields = (
        DERIVATIVE_REQUIRED_FALSE_PRIVACY_FIELDS
        if derivative_schema
        else (
            "robert_private_data_allowed",
            "robert_private_data_read_or_used_by_worker",
            "identifiable_person_likeness_used",
            "copy_existing_person_body_used",
            "runtime_files_read_or_written_by_worker",
        )
    )
    for field in privacy_false_fields:
        if privacy.get(field) is not False:
            failures.append(f"build_privacy_false_required:{field}")
    if privacy.get("private_local_review_only") is not True:
        failures.append("build_not_marked_private_local_review_only")

    expected_request_digest = sha256_file(request_path)
    evidence_sources = evidence.get("sources")
    if derivative_schema and not isinstance(evidence_sources, Mapping):
        failures.append("build_sources_record_missing")
        evidence_sources = {}
    evidence_request = (
        evidence_sources.get("request")
        if derivative_schema and isinstance(evidence_sources, Mapping)
        else evidence.get("request")
    )
    if not isinstance(evidence_request, Mapping):
        failures.append("build_request_binding_missing")
        evidence_request = {}
    if _text(evidence_request.get("sha256")).lower() != expected_request_digest:
        failures.append("build_request_sha256_mismatch")
    evidence_request_path = _resolve_project_file(
        root,
        evidence_request.get("path"),
    )
    if evidence_request_path != request_path.resolve():
        failures.append("build_request_path_mismatch")
    evidence_parameters = (
        evidence.get("request_parameters")
        if derivative_schema
        else evidence_request.get("parameters")
    )
    if evidence_parameters != request.get("parameters"):
        failures.append("build_parameters_do_not_match_validated_request")

    source = (
        evidence_sources.get("staged_foundation")
        if derivative_schema and isinstance(evidence_sources, Mapping)
        else evidence.get("source")
    )
    if not isinstance(source, Mapping):
        failures.append("build_source_record_missing")
        source = {}
    source_path = _resolve_project_file(root, source.get("path"))
    source_digest = _text(source.get("sha256")).lower()
    if source_path is None:
        failures.append("build_source_path_invalid")
        source_authority = {}
    else:
        if not _valid_digest(source_digest):
            failures.append("build_source_sha256_invalid")
        elif sha256_file(source_path) != source_digest:
            failures.append("build_source_sha256_mismatch")
        if derivative_schema:
            source_authority = _bound_derivative_source_authority(
                root,
                source_path,
                source_digest,
                evidence_sources.get("authority"),
                failures=failures,
            )
        else:
            source_authority = _source_authority(
                root,
                source_path,
                source_digest,
                authority_path=authority_path,
                failures=failures,
            )

    artifacts = evidence.get("artifacts")
    if derivative_schema:
        candidate_binding = evidence.get("candidate")
    else:
        if not isinstance(artifacts, Mapping):
            failures.append("build_artifacts_missing")
            artifacts = {}
        candidate_binding = artifacts.get("candidate_glb")
    candidate_path, candidate_digest = _binding_matches(
        root,
        candidate_binding,
        label="candidate_glb",
        failures=failures,
    )
    expected_private_root = _resolve_project_file(
        root,
        request["output"]["private_candidate_root"],
        must_exist=False,
    )
    if expected_private_root is None:
        failures.append("request_private_candidate_root_invalid")
    if candidate_path is not None and expected_private_root is not None:
        try:
            candidate_path.relative_to(expected_private_root)
        except ValueError:
            failures.append("candidate_glb_outside_private_candidate_root")
    try:
        evidence_path.resolve().relative_to(expected_private_root)
    except (AttributeError, ValueError):
        failures.append("build_evidence_outside_private_candidate_root")
    if candidate_digest and candidate_digest == source_digest:
        failures.append("candidate_is_unmodified_source_copy")

    glb_report: dict[str, Any] = {}
    if candidate_path is not None:
        glb_report = inspect_glb_topology(
            candidate_path,
            artifact_id="kira_temporary_functional_body_private_candidate",
        )
        if glb_report.get("sha256") != candidate_digest:
            failures.append("independent_glb_digest_mismatch")
        if glb_report.get("valid_glb") is not True:
            failures.append("candidate_not_valid_self_contained_glb")
        if glb_report.get("humanoid_rig_structurally_ready") is not True:
            failures.append("candidate_independent_humanoid_rig_structure_failed")

    build_gates = evidence.get("gates")
    if not isinstance(build_gates, Mapping):
        failures.append("build_gates_missing")
        build_gates = {}
    required_true_gates = (
        DERIVATIVE_REQUIRED_TRUE_BUILD_GATES
        if derivative_schema
        else REQUIRED_TRUE_BUILD_GATES
    )
    for gate in required_true_gates:
        if build_gates.get(gate) is not True:
            failures.append(f"build_gate_not_passed:{gate}")
    false_gate_record = (
        candidate_binding
        if derivative_schema and isinstance(candidate_binding, Mapping)
        else build_gates
    )
    for gate in (
        "owner_approved",
        "runtime_assignment_allowed",
        "public_export_allowed",
    ):
        if false_gate_record.get(gate) is not False:
            failures.append(f"build_gate_false_required:{gate}")
    if (
        derivative_schema
        and false_gate_record.get("runtime_activation_allowed") is not False
    ):
        failures.append(
            "build_gate_false_required:runtime_activation_allowed"
        )

    surface = (
        evidence.get("adult_surface_authoring")
        if derivative_schema
        else evidence.get("surface_authoring")
    )
    if not isinstance(surface, Mapping):
        failures.append("surface_authoring_evidence_missing")
        surface = {}
    author_topology = (
        evidence.get("topology_author_audit")
        if derivative_schema
        else surface.get("body_topology_after")
    )
    if derivative_schema and isinstance(author_topology, Mapping):
        boundary_parts = author_topology.get("boundary_parts")
        if isinstance(boundary_parts, list):
            open_boundary_chain_count = sum(
                1
                for item in boundary_parts
                if isinstance(item, Mapping)
                and item.get("closed_cycle") is not True
            )
        else:
            open_boundary_chain_count = 0
        topology = {
            "surface_island_count": author_topology.get(
                "connected_components"
            ),
            "boundary_loop_count": author_topology.get(
                "boundary_closed_cycle_count"
            ),
            "open_boundary_chain_count": open_boundary_chain_count,
            "non_manifold_edge_count": author_topology.get(
                "overused_edge_count"
            ),
            "degenerate_face_count": author_topology.get(
                "degenerate_face_count_under_1e_12_m2"
            ),
        }
    else:
        topology = author_topology
    if not isinstance(topology, Mapping):
        failures.append("body_topology_after_missing")
        topology = {}
    if topology.get("surface_island_count") != 1:
        failures.append("primary_body_not_one_connected_surface")
    if topology.get("non_manifold_edge_count") != 0:
        failures.append("primary_body_nonmanifold_edges_present")
    if int(
        topology.get(
            "degenerate_face_count",
            topology.get("collapsed_face_count", 0),
        )
        or 0
    ) != 0:
        failures.append("primary_body_degenerate_faces_present")
    parametric = (
        evidence.get("parameter_morph")
        if derivative_schema
        else surface.get("request_parametric_key")
    )
    if not isinstance(parametric, Mapping):
        failures.append("request_parametric_surface_evidence_missing")
        parametric = {}
    try:
        moved_vertices = int(
            parametric.get(
                "changed_vertices",
                parametric.get("moved_vertex_count", 0),
            )
        )
        maximum_delta = float(
            parametric.get(
                "maximum_vertex_delta_m",
                parametric.get("maximum_world_displacement_m", 0.0),
            )
        )
    except (TypeError, ValueError):
        moved_vertices = 0
        maximum_delta = 0.0
    if moved_vertices <= 0 or maximum_delta <= 0.0:
        failures.append("new_subject_surface_deformation_not_proven")
    external = (
        surface
        if derivative_schema
        else parametric.get("integrated_external_adult_form")
    )
    if not isinstance(external, Mapping):
        failures.append("integrated_adult_form_evidence_missing")
        external = {}
    authored_on_primary = external.get(
        "authored_on_primary_body_surface",
        external.get("adult_surface_joined_to_primary_body"),
    )
    separate_or_floating = external.get(
        "separate_or_floating_anatomy_mesh_created",
        external.get("separate_or_floating_adult_surface_present"),
    )
    named_regions_displaced = external.get(
        "all_named_regions_received_surface_displacement",
        external.get("adult_surface_interface_weld_or_bridge_evidence"),
    )
    owner_visual_required = external.get(
        "visual_owner_review_required",
        external.get("owner_visual_review_required"),
    )
    dynamic_behavior = external.get(
        "functional_soft_tissue_behavior_proven",
        external.get("dynamic_soft_tissue_behavior_proven"),
    )
    declared_body_class = _normalized(
        external.get(
            "body_class",
            external.get("adult_surface_body_class"),
        )
    )
    requested_body_class = _normalized(request_summary.get("body_class"))
    wrong_class_excluded = external.get(
        "wrong_body_class_helper_or_surface_excluded"
    )
    body_class_visually_reviewed = external.get(
        "requested_body_class_visually_reviewed"
    )
    if authored_on_primary is not True:
        failures.append("adult_form_not_authored_on_primary_surface")
    if separate_or_floating is not False:
        failures.append("separate_or_floating_anatomy_not_excluded")
    if named_regions_displaced is not True:
        failures.append("adult_form_named_region_surface_evidence_incomplete")
    if owner_visual_required is not True:
        failures.append("adult_form_owner_visual_review_gate_missing")
    if dynamic_behavior is not False:
        failures.append("adult_form_functional_behavior_false_required")
    if declared_body_class != requested_body_class:
        failures.append("adult_surface_requested_body_class_mismatch")
    if wrong_class_excluded is not True:
        failures.append(
            "wrong_body_class_helper_or_surface_not_explicitly_excluded"
        )
    if body_class_visually_reviewed is not True:
        failures.append(
            "requested_body_class_visual_review_not_recorded"
        )

    independent_topology = (
        topology_audit if isinstance(topology_audit, Mapping) else {}
    )
    if not independent_topology:
        failures.append("independent_topology_intersection_audit_missing")
    else:
        if topology_audit_path is None or not topology_audit_path.is_file():
            failures.append("independent_topology_audit_file_binding_missing")
        else:
            if expected_private_root is None:
                failures.append(
                    "independent_topology_audit_private_root_unavailable"
                )
            else:
                try:
                    topology_audit_path.resolve().relative_to(
                        expected_private_root
                    )
                except ValueError:
                    failures.append(
                        "independent_topology_audit_outside_private_root"
                    )
            try:
                persisted_topology = _read_json(topology_audit_path)
            except (
                OSError,
                UnicodeError,
                json.JSONDecodeError,
                ValueError,
            ):
                persisted_topology = {}
                failures.append("independent_topology_audit_file_unreadable")
            if persisted_topology != dict(independent_topology):
                failures.append(
                    "independent_topology_audit_memory_file_mismatch"
                )
        if (
            _normalized(independent_topology.get("audit_mode"))
            != "independent_blender_rapid_body_topology_v1"
        ):
            failures.append("independent_topology_audit_mode_invalid")
        if (
            _text(independent_topology.get("producer"))
            != "tools/blender_audit_rapid_body_candidate.py"
        ):
            failures.append("independent_topology_audit_producer_invalid")
        if (
            _text(independent_topology.get("candidate_sha256")).lower()
            != candidate_digest
        ):
            failures.append("independent_topology_candidate_sha256_mismatch")
        if independent_topology.get("input_modified") is not False:
            failures.append("independent_topology_input_modified_or_unreported")
        if (
            independent_topology.get("topology_intersection_gate_passed")
            is not True
        ):
            failures.append("independent_topology_intersection_gate_failed")
        if independent_topology.get("primary_marker_count") != 1:
            failures.append("independent_primary_surface_marker_count_invalid")
        independent_body = independent_topology.get("primary_body")
        if not isinstance(independent_body, Mapping):
            failures.append("independent_primary_body_audit_missing")
            independent_body = {}
        if independent_body.get("present") is not True:
            failures.append("independent_primary_body_not_present")
        if independent_body.get("surface_island_count") != 1:
            failures.append("independent_primary_body_not_one_surface")
        if independent_body.get("non_manifold_edge_count") != 0:
            failures.append("independent_primary_body_nonmanifold_edges")
        if independent_body.get("degenerate_face_count") != 0:
            failures.append("independent_primary_body_degenerate_faces")
        if independent_body.get("open_boundary_chain_count") != 0:
            failures.append("independent_primary_body_open_boundary_chain")
        if (
            independent_body.get("boundary_loop_count")
            != independent_body.get(
                "reviewed_intentional_boundary_loop_count"
            )
        ):
            failures.append(
                "independent_boundary_loops_not_exactly_reviewed"
            )
        boundary_support = independent_body.get(
            "boundary_component_support"
        )
        if not isinstance(boundary_support, Mapping):
            failures.append(
                "independent_boundary_component_support_audit_missing"
            )
            boundary_support = {}
        if (
            _normalized(boundary_support.get("method"))
            != (
                "exact_import_boundary_vertices_to_supported_component_"
                "vertex_kdtree"
            )
        ):
            failures.append(
                "independent_boundary_component_support_method_invalid"
            )
        if boundary_support.get("coverage_complete") is not True:
            failures.append(
                "independent_boundary_component_support_incomplete"
            )
        if (
            boundary_support.get("boundary_loop_count")
            != independent_body.get("boundary_loop_count")
        ):
            failures.append(
                "independent_boundary_component_support_count_mismatch"
            )
        if (
            boundary_support.get("supported_boundary_loop_count")
            != independent_body.get("boundary_loop_count")
        ):
            failures.append(
                "independent_boundary_component_supported_count_mismatch"
            )
        if boundary_support.get("unsupported_boundary_loop_count") != 0:
            failures.append(
                "independent_unsupported_boundary_component_present"
            )
        if independent_body.get("unweighted_vertex_count") != 0:
            failures.append("independent_primary_body_unweighted_vertices")
        if (
            independent_body.get("weight_sum_out_of_tolerance_count")
            != 0
        ):
            failures.append(
                "independent_primary_body_weight_sum_out_of_tolerance"
            )
        intersections = independent_topology.get("self_intersection")
        if not isinstance(intersections, Mapping):
            failures.append("independent_self_intersection_audit_missing")
            intersections = {}
        if intersections.get("complete_bvh_overlap_scan") is not True:
            failures.append("independent_self_intersection_scan_incomplete")
        if (
            _normalized(intersections.get("adjacency_method"))
            != "raw_index_or_positional_weld_key_shared_vertex"
        ):
            failures.append(
                "independent_self_intersection_adjacency_method_invalid"
            )
        try:
            weld_tolerance = float(
                intersections.get("positional_weld_tolerance_m", 0.0)
            )
        except (TypeError, ValueError):
            weld_tolerance = 0.0
        if weld_tolerance <= 0.0:
            failures.append(
                "independent_self_intersection_weld_tolerance_missing"
            )
        if (
            intersections.get(
                "coincident_duplicate_triangle_pair_count"
            )
            != 0
        ):
            failures.append(
                "independent_primary_body_duplicate_triangles"
            )
        if (
            intersections.get(
                "nonadjacent_intersecting_source_face_pair_count"
            )
            != 0
        ):
            failures.append("independent_primary_body_self_intersections")
        comparison_keys = (
            "surface_island_count",
            "boundary_loop_count",
            "open_boundary_chain_count",
            "non_manifold_edge_count",
        )
        for key in comparison_keys:
            if key in topology and topology.get(key) != independent_body.get(
                key
            ):
                failures.append(
                    f"build_and_independent_topology_count_mismatch:{key}"
                )
        build_degenerate = topology.get(
            "degenerate_face_count",
            topology.get("collapsed_face_count"),
        )
        if (
            build_degenerate is not None
            and build_degenerate
            != independent_body.get("degenerate_face_count")
        ):
            failures.append(
                "build_and_independent_topology_count_mismatch:"
                "degenerate_face_count"
            )

    independent_deformation = (
        deformation_audit if isinstance(deformation_audit, Mapping) else {}
    )
    if not independent_deformation:
        failures.append("independent_bounded_deformation_audit_missing")
    else:
        if (
            deformation_audit_path is None
            or not deformation_audit_path.is_file()
        ):
            failures.append(
                "independent_deformation_audit_file_binding_missing"
            )
        else:
            if expected_private_root is None:
                failures.append(
                    "independent_deformation_audit_private_root_unavailable"
                )
            else:
                try:
                    deformation_audit_path.resolve().relative_to(
                        expected_private_root
                    )
                except ValueError:
                    failures.append(
                        "independent_deformation_audit_outside_private_root"
                    )
            try:
                persisted_deformation = _read_json(
                    deformation_audit_path
                )
            except (
                OSError,
                UnicodeError,
                json.JSONDecodeError,
                ValueError,
            ):
                persisted_deformation = {}
                failures.append(
                    "independent_deformation_audit_file_unreadable"
                )
            if persisted_deformation != dict(independent_deformation):
                failures.append(
                    "independent_deformation_audit_memory_file_mismatch"
                )
        if (
            _normalized(independent_deformation.get("audit_mode"))
            != "independent_blender_rapid_body_deformation_v1"
        ):
            failures.append("independent_deformation_audit_mode_invalid")
        if (
            _text(independent_deformation.get("producer"))
            != "tools/blender_audit_rapid_body_candidate.py"
        ):
            failures.append("independent_deformation_audit_producer_invalid")
        if (
            _text(independent_deformation.get("candidate_sha256")).lower()
            != candidate_digest
        ):
            failures.append(
                "independent_deformation_candidate_sha256_mismatch"
            )
        if independent_deformation.get("input_modified") is not False:
            failures.append(
                "independent_deformation_input_modified_or_unreported"
            )
        if (
            independent_deformation.get(
                "bounded_pose_deformation_gate_passed"
            )
            is not True
        ):
            failures.append("independent_bounded_deformation_gate_failed")
        required_poses = independent_deformation.get(
            "required_pose_labels"
        )
        if (
            not isinstance(required_poses, list)
            or set(_text(label) for label in required_poses)
            != set(REQUIRED_DEFORMATION_POSE_LABELS)
        ):
            failures.append(
                "independent_required_pose_policy_mismatch"
            )
        missing_poses = independent_deformation.get("missing_pose_labels")
        failed_poses = independent_deformation.get("failed_pose_labels")
        if missing_poses not in ([], ()):
            failures.append("independent_required_pose_labels_missing")
        if failed_poses not in ([], ()):
            failures.append("independent_required_pose_labels_failed")
        pose_records = independent_deformation.get("pose_records")
        if not isinstance(pose_records, Mapping):
            failures.append("independent_pose_records_missing")
            pose_records = {}
        for knee_label in REQUIRED_ANATOMICAL_KNEE_DIRECTION_LABELS:
            knee_record = pose_records.get(knee_label)
            if not isinstance(knee_record, Mapping):
                failures.append(
                    "independent_anatomical_knee_direction_record_missing:"
                    f"{knee_label}"
                )
                continue
            if (
                knee_record.get("anatomical_knee_direction_passed")
                is not True
            ):
                failures.append(
                    "independent_anatomical_knee_direction_failed:"
                    f"{knee_label}"
                )
            direction = knee_record.get("anatomical_knee_direction")
            direction_records = knee_record.get(
                "anatomical_knee_direction_records"
            )
            if isinstance(direction, Mapping):
                exact_records = [direction]
            elif isinstance(direction_records, list):
                exact_records = [
                    value
                    for value in direction_records
                    if isinstance(value, Mapping)
                ]
            else:
                exact_records = []
            if not exact_records:
                failures.append(
                    "independent_anatomical_knee_measurement_missing:"
                    f"{knee_label}"
                )
                continue
            if any(
                value.get("passed") is not True
                or value.get(
                    "measured_from_exact_imported_skeleton"
                )
                is not True
                or not _text(value.get("anatomical_forward_axis"))
                or not _text(value.get("upper_leg_bone"))
                or not _text(value.get("lower_leg_bone"))
                or not _text(value.get("ankle_bone"))
                for value in exact_records
            ):
                failures.append(
                    "independent_anatomical_knee_measurement_invalid:"
                    f"{knee_label}"
                )
        restoration = independent_deformation.get("restoration")
        if (
            not isinstance(restoration, Mapping)
            or restoration.get("restored_within_1e_6_m") is not True
        ):
            failures.append("independent_rest_pose_not_restored")
        skeleton = independent_deformation.get("skeleton_profile")
        if not isinstance(skeleton, Mapping):
            failures.append("independent_skeleton_profile_missing")
        else:
            try:
                joint_count = int(skeleton.get("joint_count", 0))
            except (TypeError, ValueError):
                joint_count = 0
            if joint_count < 15:
                failures.append("independent_skeleton_joint_count_too_low")
            if skeleton.get("runtime_compatibility_claimed") is not False:
                failures.append(
                    "independent_skeleton_must_not_claim_runtime_compatibility"
                )
            if (
                skeleton.get(
                    "future_adapter_or_eligibility_proof_required"
                )
                is not True
            ):
                failures.append(
                    "independent_skeleton_future_adapter_gate_missing"
                )

    renders = (
        evidence.get("render_bindings")
        if derivative_schema
        else evidence.get("renders")
    )
    if not isinstance(renders, Mapping):
        failures.append("render_evidence_missing")
        renders = {}
    verified_render_bindings: dict[str, dict[str, Any]] = {}
    for label in REQUIRED_RENDER_LABELS:
        raw_render = renders.get(label)
        if derivative_schema:
            for alias in DERIVATIVE_RENDER_ALIASES[label]:
                if isinstance(renders.get(alias), Mapping):
                    raw_render = renders.get(alias)
                    break
        path, digest = _binding_matches(
            root,
            raw_render,
            label=f"render_{label}",
            failures=failures,
        )
        if path is not None:
            if expected_private_root is not None:
                try:
                    path.relative_to(expected_private_root)
                except ValueError:
                    failures.append(f"render_outside_private_root:{label}")
            verified_render_bindings[label] = {
                "path": _relative(root, path),
                "sha256": digest,
                "size_bytes": path.stat().st_size,
            }

    runtime_results: dict[str, Any] = {}
    baseline = request.get("runtime_nonmutation_baseline")
    if not isinstance(baseline, Mapping):
        failures.append("runtime_nonmutation_baseline_missing")
        baseline = {}
    for name in ("live_body", "body_selection", "world_shell_state"):
        record = baseline.get(name)
        if not isinstance(record, Mapping):
            failures.append(f"runtime_baseline_missing:{name}")
            continue
        path = _resolve_project_file(root, record.get("path"))
        expected_digest = _text(record.get("sha256")).lower()
        try:
            expected_size = int(record.get("bytes"))
        except (TypeError, ValueError):
            expected_size = -1
        current_digest = sha256_file(path) if path is not None else ""
        current_size = path.stat().st_size if path is not None else -1
        unchanged = bool(
            path is not None
            and _valid_digest(expected_digest)
            and current_digest == expected_digest
            and current_size == expected_size
        )
        if not unchanged:
            failures.append(f"runtime_sentinel_changed:{name}")
        runtime_results[name] = {
            "path": _relative(root, path) if path is not None else "",
            "baseline_sha256": expected_digest,
            "after_sha256": current_digest,
            "baseline_bytes": expected_size,
            "after_bytes": current_size,
            "unchanged": unchanged,
        }

    review = visual_review if isinstance(visual_review, Mapping) else {}
    if review:
        if _text(review.get("candidate_sha256")).lower() != candidate_digest:
            failures.append("visual_review_candidate_sha256_mismatch")
        if (
            _normalized(review.get("status"))
            != "passed_for_private_inspection"
        ):
            failures.append("independent_visual_review_not_passed")
        if review.get("owner_approval_claimed") is not False:
            failures.append("visual_review_must_not_claim_owner_approval")
        if not _text(review.get("reviewed_at")):
            failures.append("independent_visual_review_time_missing")
        if not _text(review.get("reviewed_by")):
            failures.append("independent_visual_reviewer_missing")
        visual_checks = review.get("check_results")
        if not isinstance(visual_checks, Mapping):
            failures.append("independent_visual_check_results_missing")
            visual_checks = {}
        for check_name in REQUIRED_VISUAL_REVIEW_CHECKS:
            check = visual_checks.get(check_name)
            if not isinstance(check, Mapping):
                failures.append(
                    f"independent_visual_check_missing:{check_name}"
                )
                continue
            if check.get("passed") is not True:
                failures.append(
                    f"independent_visual_check_not_passed:{check_name}"
                )
            labels = check.get("evidence_render_labels")
            if (
                not isinstance(labels, list)
                or not labels
                or any(not _text(label) for label in labels)
            ):
                failures.append(
                    f"independent_visual_check_evidence_missing:{check_name}"
                )
            elif any(
                _text(label) not in verified_render_bindings
                for label in labels
            ):
                failures.append(
                    f"independent_visual_check_evidence_unbound:{check_name}"
                )
            elif not (
                set(_text(label) for label in labels)
                & VISUAL_CHECK_RELEVANT_RENDER_LABELS[check_name]
            ):
                failures.append(
                    f"independent_visual_check_evidence_irrelevant:{check_name}"
                )
            elif not VISUAL_CHECK_REQUIRED_RENDER_LABELS.get(
                check_name, set()
            ).issubset(set(_text(label) for label in labels)):
                failures.append(
                    f"independent_visual_check_evidence_incomplete:{check_name}"
                )
    else:
        failures.append("independent_visual_review_pending")

    failures = _dedupe(failures)
    warnings = _dedupe(warnings)
    admitted = not failures
    return {
        "schema_version": 1,
        "gate": "avatar_builder_rapid_body_candidate_v1",
        "evidence_family": evidence_family,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_id": _text(evidence.get("candidate_id")),
        "owner_id": request_summary["owner_id"],
        "candidate_state": (
            "PRIVATE_INSPECTION_CANDIDATE"
            if admitted
            else "BLOCKED_PRIVATE_BUILD_EVIDENCE"
        ),
        "status": (
            "PASSED_FOR_PRIVATE_INSPECTION_ROSTER"
            if admitted
            else "BLOCKED"
        ),
        "private_inspection_roster_admission_allowed": admitted,
        "runtime_assignment_allowed": False,
        "runtime_assignment_performed": False,
        "owner_approved": False,
        "kira_selected": False,
        "movement_approved": False,
        "clothing_approved": False,
        "final_hair_approved": False,
        "public_export_allowed": False,
        "request": {
            "path": _relative(root, request_path),
            "sha256": expected_request_digest,
            "validated_parameters": request_summary["parameters"],
        },
        "candidate": {
            "path": (
                _relative(root, candidate_path)
                if candidate_path is not None
                else ""
            ),
            "sha256": candidate_digest,
            "size_bytes": (
                candidate_path.stat().st_size
                if candidate_path is not None
                else 0
            ),
            "distinct_from_cage_source": bool(
                candidate_digest
                and source_digest
                and candidate_digest != source_digest
            ),
        },
        "source_authority": source_authority,
        "independent_glb_structure": glb_report,
        "independent_topology_intersection": deepcopy(
            dict(independent_topology)
        ),
        "independent_topology_audit_binding": {
            "path": (
                _relative(root, topology_audit_path)
                if topology_audit_path is not None
                and topology_audit_path.is_file()
                else ""
            ),
            "sha256": (
                sha256_file(topology_audit_path)
                if topology_audit_path is not None
                and topology_audit_path.is_file()
                else ""
            ),
        },
        "independent_bounded_deformation": deepcopy(
            dict(independent_deformation)
        ),
        "independent_deformation_audit_binding": {
            "path": (
                _relative(root, deformation_audit_path)
                if deformation_audit_path is not None
                and deformation_audit_path.is_file()
                else ""
            ),
            "sha256": (
                sha256_file(deformation_audit_path)
                if deformation_audit_path is not None
                and deformation_audit_path.is_file()
                else ""
            ),
        },
        "skeleton_profile": {
            "joint_count": (
                independent_deformation.get(
                    "skeleton_profile",
                    {},
                ).get("joint_count")
                if isinstance(
                    independent_deformation.get("skeleton_profile"),
                    Mapping,
                )
                else (
                    glb_report.get("topology_metrics", {}).get(
                        "unique_joint_count"
                    )
                    if isinstance(
                        glb_report.get("topology_metrics"),
                        Mapping,
                    )
                    else None
                )
            ),
            "maximum_joints_in_one_skin": (
                glb_report.get("topology_metrics", {}).get(
                    "maximum_joints_in_one_skin"
                )
                if isinstance(glb_report.get("topology_metrics"), Mapping)
                else None
            ),
            "independent_humanoid_structure_passed": bool(
                glb_report.get("humanoid_rig_structurally_ready")
            ),
            "current_runtime_compatibility_claimed": False,
            "future_runtime_adapter_or_eligibility_proof_required": True,
        },
        "blender_body_topology": dict(topology),
        "adult_surface_authoring": dict(external),
        "verified_render_bindings": verified_render_bindings,
        "runtime_nonmutation": runtime_results,
        "visual_review": deepcopy(dict(review)),
        "private_person_source_findings": _private_source_findings(
            {"request": request, "evidence": evidence}
        ),
        "failures": failures,
        "warnings": warnings,
        "truth_note": (
            "A pass admits an exact artifact only to the existing Avatar "
            "Builder private inspection roster. It never changes the runtime "
            "profile, assigns the body, records owner/Kira approval, proves "
            "long-duration movement, or grants publication authority."
        ),
    }


def private_roster_entry(
    project_root: Path,
    audit_path: Path,
) -> dict[str, Any]:
    """Create a nonselectable roster entry from one exact passing audit."""

    root = project_root.resolve(strict=True)
    audit = _read_json(audit_path)
    if audit.get("private_inspection_roster_admission_allowed") is not True:
        raise ValueError("candidate audit did not pass private roster admission")
    if audit.get("runtime_assignment_allowed") is not False:
        raise ValueError("candidate audit incorrectly allows runtime assignment")
    candidate = audit.get("candidate")
    if not isinstance(candidate, Mapping):
        raise ValueError("candidate audit binding missing")
    path = _resolve_project_file(root, candidate.get("path"))
    digest = _text(candidate.get("sha256")).lower()
    if path is None or not _valid_digest(digest) or sha256_file(path) != digest:
        raise ValueError("candidate artifact changed after audit")
    if sha256_file(audit_path) == "":
        raise ValueError("audit is unreadable")
    return {
        "entry_id": f"{_normalized(audit.get('candidate_id'))}_{digest[:12]}",
        "owner_id": _text(audit.get("owner_id")),
        "candidate_state": "PRIVATE_INSPECTION_CANDIDATE",
        "candidate": {
            "path": _relative(root, path),
            "sha256": digest,
            "size_bytes": path.stat().st_size,
        },
        "candidate_audit": {
            "path": _relative(root, audit_path),
            "sha256": sha256_file(audit_path),
        },
        "private_inspection_visible": True,
        "runtime_selectable": False,
        "runtime_assignment_allowed": False,
        "runtime_assignment_performed": False,
        "owner_approved": False,
        "person_selected": False,
        "movement_approved": False,
        "clothing_approved": False,
        "final_hair_approved": False,
        "public_export_allowed": False,
        "normal_entry_point": "EXISTING_AVATAR_BUILDER_WORKSPACE",
    }


def roster_with_entry(
    roster: Mapping[str, Any],
    entry: Mapping[str, Any],
) -> dict[str, Any]:
    """Append one hash-unique private entry without enabling selection."""

    updated = deepcopy(dict(roster))
    if updated.get("schema_version") != 1:
        raise ValueError("private inspection roster schema must be 1")
    entries = updated.get("entries")
    if not isinstance(entries, list):
        raise ValueError("private inspection roster entries must be a list")
    if entry.get("runtime_selectable") is not False:
        raise ValueError("private inspection entries may never be runtime selectable")
    if entry.get("runtime_assignment_allowed") is not False:
        raise ValueError("private inspection entries may never allow assignment")
    entry_id = _text(entry.get("entry_id"))
    if not entry_id:
        raise ValueError("private inspection entry id is required")
    if any(
        isinstance(existing, Mapping)
        and _text(existing.get("entry_id")) == entry_id
        for existing in entries
    ):
        raise ValueError("private inspection roster entry already exists")
    entries.append(deepcopy(dict(entry)))
    updated["updated_at"] = datetime.now(timezone.utc).isoformat()
    return updated


__all__ = [
    "PRIVATE_ROSTER_PATH",
    "REQUIRED_DEFORMATION_POSE_LABELS",
    "REQUIRED_RENDER_LABELS",
    "REQUIRED_VISUAL_REVIEW_CHECKS",
    "SOURCE_AUTHORITY_PATH",
    "VISUAL_CHECK_RELEVANT_RENDER_LABELS",
    "VISUAL_CHECK_REQUIRED_RENDER_LABELS",
    "build_workspace_record",
    "evaluate_candidate_package",
    "private_roster_entry",
    "roster_with_entry",
    "sha256_file",
]
