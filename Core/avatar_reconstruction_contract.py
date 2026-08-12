"""Truthful picture-first contracts for Avatar Builder reconstruction jobs.

This module does not generate or activate a body.  It answers the smaller,
safer question that every renderer must answer first: whether the reviewed
identity evidence, maturity-specific base policy, privacy rules, and wardrobe
separation are complete enough to stage a reconstruction candidate.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable


ADULT_MATURITY_CLASSES = frozenset({"adult", "confirmed_adult", "adult_confirmed"})
NON_ADULT_MATURITY_CLASSES = frozenset(
    {"non_adult_doll_safe", "uncertain_non_adult_safe_default"}
)
APPROVED_REFERENCE_STATUSES = frozenset(
    {
        "approved",
        "approved_for_avatar_identity",
        "approved_for_identity_reconstruction",
        "approved_for_private_avatar_reconstruction",
    }
)
PICTURE_EXTENSIONS = frozenset({".bmp", ".jpeg", ".jpg", ".png", ".webp"})
MODEL_EXTENSIONS = frozenset({".fbx", ".glb", ".gltf", ".obj", ".usdz"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_FRONT_VIEWS = frozenset(
    {
        "face_front",
        "front",
        "front_face",
        "full_body_front",
        "head_front",
    }
)
_DEPTH_VIEWS = frozenset(
    {
        "face_left_profile",
        "face_right_profile",
        "full_body_left",
        "full_body_right",
        "full_body_side",
        "head_left_profile",
        "head_right_profile",
        "left_profile",
        "profile",
        "right_profile",
        "side",
        "three_quarter",
        "three_quarter_left",
        "three_quarter_right",
    }
)
_FULL_BODY_VIEWS = frozenset(
    {
        "full_body",
        "full_body_back",
        "full_body_front",
        "full_body_left",
        "full_body_right",
        "full_body_side",
    }
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _text(value).lower()).strip("_")


def _reference_suffix(reference: dict[str, Any]) -> str:
    for key in ("local_file", "filename", "source_file"):
        value = _text(reference.get(key))
        if value:
            return Path(value).suffix.lower()
    return ""


def _reference_kind(reference: dict[str, Any]) -> str:
    declared = _normalized(
        reference.get("media_type")
        or reference.get("reference_type")
        or reference.get("kind")
    )
    suffix = _reference_suffix(reference)
    if suffix in PICTURE_EXTENSIONS or declared in {
        "image",
        "photo",
        "picture",
        "still_image",
    }:
        return "picture"
    if suffix in MODEL_EXTENSIONS or "model" in declared or declared in {
        "mesh",
        "three_d",
        "3d",
    }:
        return "model"
    return "unknown"


def _subject_matches(candidate_id: str, reference: dict[str, Any]) -> bool:
    subject = _normalized(
        reference.get("subject_id")
        or reference.get("candidate_id")
        or reference.get("identity_id")
    )
    return bool(subject) and subject == _normalized(candidate_id)


def _approved(reference: dict[str, Any]) -> bool:
    return _normalized(reference.get("review_status") or reference.get("status")) in {
        _normalized(value) for value in APPROVED_REFERENCE_STATUSES
    }


def _valid_hash(reference: dict[str, Any]) -> bool:
    return bool(_SHA256_RE.fullmatch(_text(reference.get("sha256")).lower()))


def _hash_integrity_verified(reference: dict[str, Any]) -> bool:
    return reference.get("artifact_hash_verified") is True or reference.get(
        "hash_verified_at_intake"
    ) is True


def _views(reference: dict[str, Any]) -> set[str]:
    values: list[Any] = []
    for key in ("view", "views", "camera_view", "coverage"):
        value = reference.get(key)
        if isinstance(value, (list, tuple, set)):
            values.extend(value)
        elif value:
            values.append(value)
    return {_normalized(value) for value in values if _normalized(value)}


def _picture_summary(candidate_id: str, references: list[dict[str, Any]]) -> dict[str, Any]:
    pictures = [item for item in references if _reference_kind(item) == "picture"]
    approved = [
        item
        for item in pictures
        if _approved(item)
        and _subject_matches(candidate_id, item)
        and _valid_hash(item)
        and _hash_integrity_verified(item)
    ]
    covered_views = set().union(*(_views(item) for item in approved)) if approved else set()
    has_front = bool(covered_views & _FRONT_VIEWS)
    has_depth = bool(covered_views & _DEPTH_VIEWS)
    has_full_body = bool(covered_views & _FULL_BODY_VIEWS)
    return {
        "total_count": len(pictures),
        "approved_exact_subject_hash_bound_count": len(approved),
        "unreviewed_or_unbound_count": len(pictures) - len(approved),
        "covered_views": sorted(covered_views),
        "has_front_identity_view": has_front,
        "has_profile_or_three_quarter_view": has_depth,
        "has_full_body_view": has_full_body,
        "minimum_multiview_identity_set_present": (
            len(approved) >= 3 and has_front and has_depth and has_full_body
        ),
        "policy": (
            "Pictures are the primary identity evidence. Each accepted picture must be "
            "review-approved, exact-subject scoped, SHA-256 bound, and classified by view."
        ),
    }


def _model_summary(candidate_id: str, references: list[dict[str, Any]]) -> dict[str, Any]:
    models = [item for item in references if _reference_kind(item) == "model"]
    usable: list[dict[str, Any]] = []
    rejected_count = 0
    for item in models:
        exact_subject_or_generic = _subject_matches(candidate_id, item) or bool(
            item.get("generic_structure_reference")
        )
        reference_only = item.get("reference_only") is True
        copying_blocked = item.get("copy_as_avatar_body_allowed") is False
        if (
            _approved(item)
            and _valid_hash(item)
            and _hash_integrity_verified(item)
            and exact_subject_or_generic
            and reference_only
            and copying_blocked
        ):
            usable.append(item)
        else:
            rejected_count += 1
    return {
        "total_count": len(models),
        "optional_measurement_reference_count": len(usable),
        "rejected_or_unreviewed_count": rejected_count,
        "can_substitute_for_picture_identity_evidence": False,
        "can_be_copied_as_candidate_body": False,
        "policy": (
            "Reviewed 3D models are optional measurement/topology guidance only. They "
            "cannot replace the picture identity set or become the candidate body."
        ),
    }


def maturity_base_contract(
    maturity_policy: dict[str, Any],
    *,
    request_complete_adult_anatomy: bool = False,
) -> dict[str, Any]:
    """Select the only permitted base/body-detail lane for a maturity class."""
    maturity_class = _text(maturity_policy.get("maturity_class"))
    is_adult = maturity_class in ADULT_MATURITY_CLASSES
    if is_adult:
        return {
            "maturity_class": maturity_class,
            "base_treatment": "neutral_adult_anatomy",
            "complete_adult_anatomy_requested": bool(request_complete_adult_anatomy),
            "complete_adult_anatomy_policy_eligible": bool(request_complete_adult_anatomy),
            "complete_adult_anatomy_allowed": False,
            "non_adult_doll_safe_allowed": False,
            "private_body_detail_policy": (
                "Adult-complete body topology may exist only in the private body artifact. "
                "Normal review/contact sheets remain clothed; no intimate review render is retained."
            ),
        }
    return {
        "maturity_class": maturity_class,
        "base_treatment": "non_adult_doll_safe",
        "complete_adult_anatomy_requested": bool(request_complete_adult_anatomy),
        "complete_adult_anatomy_policy_eligible": False,
        "complete_adult_anatomy_allowed": False,
        "non_adult_doll_safe_allowed": True,
        "private_body_detail_policy": (
            "Non-adult and uncertain candidates remain non-explicit and doll-safe. "
            "Adult anatomy references and adult-complete topology are forbidden."
        ),
    }


def evaluate_avatar_reconstruction_contract(
    *,
    candidate_id: str,
    maturity_policy: dict[str, Any],
    references: Iterable[dict[str, Any]] = (),
    request_complete_adult_anatomy: bool = False,
    requested_eye_color: str = "",
    measurements_reviewed: bool = False,
    adult_anatomy_reference_reviewed: bool = False,
    base_body_artifact_reviewed: bool = False,
    rig_topology_evidence_reviewed: bool = False,
    allow_provisional_identity_unknown: bool = False,
) -> dict[str, Any]:
    """Return a fail-closed staging contract without reading or copying source media."""
    items = [dict(item) for item in references if isinstance(item, dict)]
    picture_summary = _picture_summary(candidate_id, items)
    model_summary = _model_summary(candidate_id, items)
    base = maturity_base_contract(
        maturity_policy,
        request_complete_adult_anatomy=request_complete_adult_anatomy,
    )
    maturity_class = base["maturity_class"]
    base["adult_anatomy_reference_reviewed"] = bool(adult_anatomy_reference_reviewed)
    base["base_body_artifact_reviewed"] = bool(base_body_artifact_reviewed)
    base["rig_topology_evidence_reviewed"] = bool(rig_topology_evidence_reviewed)
    base["complete_adult_anatomy_allowed"] = bool(
        request_complete_adult_anatomy
        and maturity_class in ADULT_MATURITY_CLASSES
        and adult_anatomy_reference_reviewed
        and base_body_artifact_reviewed
        and rig_topology_evidence_reviewed
    )
    failures: list[str] = []
    warnings: list[str] = []

    if maturity_class not in ADULT_MATURITY_CLASSES | NON_ADULT_MATURITY_CLASSES:
        failures.append("invalid_or_missing_maturity_class")
    if request_complete_adult_anatomy and maturity_class not in ADULT_MATURITY_CLASSES:
        failures.append("adult_complete_anatomy_forbidden_for_non_adult_or_uncertain_candidate")
    elif request_complete_adult_anatomy and not adult_anatomy_reference_reviewed:
        failures.append("adult_complete_anatomy_reference_and_topology_plan_not_reviewed")
    elif request_complete_adult_anatomy and not rig_topology_evidence_reviewed:
        failures.append("complete_adult_topology_not_proven_on_selected_rig")
    if not base_body_artifact_reviewed:
        failures.append("selected_base_body_artifact_not_reviewed")
    if allow_provisional_identity_unknown:
        warnings.append("provisional_identity_fidelity_unknown_explicitly_accepted")
    else:
        if not picture_summary["approved_exact_subject_hash_bound_count"]:
            failures.append("no_approved_exact_subject_picture_identity_evidence")
        elif not picture_summary["minimum_multiview_identity_set_present"]:
            failures.append("approved_picture_identity_set_missing_required_multiview_coverage")
        if not measurements_reviewed:
            failures.append("body_measurements_or_landmarks_not_reviewed")
    if model_summary["total_count"] and not model_summary["optional_measurement_reference_count"]:
        warnings.append("model_references_exist_but_none_pass_optional_reference_only_gate")
    if not model_summary["total_count"]:
        warnings.append("no_optional_model_reference_supplied_picture_only_path_remains_valid")

    staging_allowed = not failures
    return {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "identity_reconstruction_mode": "picture_first_models_optional",
        "provisional_identity_unknown_allowed": bool(allow_provisional_identity_unknown),
        "identity_fidelity": (
            "unknown_provisional_not_identity_matched"
            if allow_provisional_identity_unknown
            else "must_match_reviewed_picture_evidence"
        ),
        "maturity_base_contract": base,
        "requested_features": {
            "eye_color": _text(requested_eye_color),
            "eye_color_status": (
                "requested_draft_pending_owner_visual_review"
                if _text(requested_eye_color)
                else "not_selected"
            ),
        },
        "picture_evidence": picture_summary,
        "optional_model_evidence": model_summary,
        "measurements_reviewed": bool(measurements_reviewed),
        "body_output_contract": {
            "one_stable_shared_rig": True,
            "identity_fit_required_for_this_stage": not allow_provisional_identity_unknown,
            "identity_fit_when_claimed_must_be_derived_from_reviewed_pictures_and_measurements": True,
            "reference_model_mesh_copying_allowed": False,
            "body_and_clothing_must_be_separate_artifacts": True,
            "hair_and_eyes_must_be_separate_fitted_systems": True,
            "generic_base_cannot_pass_as_identity_likeness": True,
        },
        "wardrobe_contract": {
            "clothing_baked_into_body_allowed": False,
            "separate_wearable_mesh_required": True,
            "each_garment_is_a_persistent_inventory_component": True,
            "same_size_sharing_supported_after_target_review": True,
            "size_label_alone_counts_as_fit_proof": False,
            "sharing_requires_measurement_envelope_match": True,
            "sharing_requires_same_maturity_lane": True,
            "sharing_requires_exact_target_body_rig_binding": True,
            "sharing_requires_target_deformation_penetration_and_owner_review": True,
            "sharing_transfers_one_item_cloning_forbidden": True,
            "shareable_component_policy": (
                "Avatar/avatar_builder/policies/"
                "separate_shareable_wearable_components_v1.json"
            ),
            "required_lifecycle_states": [
                "stored_hung",
                "stored_folded",
                "grasped",
                "right_sleeve_threaded",
                "left_sleeve_threaded",
                "both_sleeves_threaded",
                "worn_open",
                "worn_tied",
                "undressing_one_arm_at_a_time",
                "released_hung",
                "released_folded_or_supported_surface",
            ],
            "both_arm_orders_must_be_physically_evidenced": True,
            "timer_or_state_name_only_counts_as_proof": False,
            "runtime_activation_requires_exact_body_rig_garment_evidence_and_owner_registry": True,
        },
        "privacy_contract": {
            "source_pictures_private": True,
            "source_paths_omitted_from_public_reports": True,
            "normal_review_presentation": "clothed_only",
            "retain_intimate_review_images": False,
            "adult_private_body_artifact_does_not_make_anatomy_public": True,
        },
        "status": (
            "ready_for_private_provisional_generic_stage"
            if staging_allowed and allow_provisional_identity_unknown
            else "ready_for_private_staged_reconstruction"
            if staging_allowed
            else "blocked"
        ),
        "staging_allowed": staging_allowed,
        "runtime_activation_allowed": False,
        "failures": list(dict.fromkeys(failures)),
        "warnings": list(dict.fromkeys(warnings)),
        "truth_note": (
            "Readiness permits a private staged build only. It does not prove likeness, "
            "anatomical completeness, rig quality, clothing fit, owner approval, or runtime activation."
        ),
    }
