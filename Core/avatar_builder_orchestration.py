"""Reusable, fail-closed Avatar Builder capability orchestration.

The orchestrator selects policy and evidence lanes.  It never authors meshes,
renders a body, copies an avatar into a live slot, or treats an animation name
as proof of physical behavior.

Every request has two explicit axes:

* one maturity topology lane: confirmed-adult or non-adult doll-safe;
* one reconstruction source lane: licensed shape-preserving derivative or
  photo-only reconstruction.

The resulting route is still only a plan until exact component, topology, rig,
face/lip-sync, locomotion/contact, wearable, privacy, and owner evidence all
pass.  Runtime activation always remains a separate default-deny workflow.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from Core.avatar_reusable_method_registry import (
    evaluate_reusable_method_selection,
)
from Core.avatar_reconstruction_contract import (
    ADULT_MATURITY_CLASSES,
    NON_ADULT_MATURITY_CLASSES,
)
from Core.garment_capability import evaluate_wearable_capability_manifest


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PASS_STATUSES = frozenset({"approved", "pass", "passed"})
OWNER_AUTHORITY_STATUSES = frozenset(
    {"verified_avatar_owner", "verified_subject_self_owner"}
)

CONFIRMED_ADULT_TOPOLOGY = "confirmed_adult_topology"
NON_ADULT_DOLL_SAFE_TOPOLOGY = "non_adult_doll_safe_topology"
LICENSED_SHAPE_PRESERVING_DERIVATIVE = "licensed_shape_preserving_derivative"
PHOTO_ONLY_RECONSTRUCTION = "photo_only_reconstruction"
PHOTO_PRIMARY_WITH_REFERENCE_MODEL_MEASUREMENT = (
    "photo_primary_with_reference_model_measurement"
)

COMPONENT_ROLES = ("body", "hair", "eyes", "clothes")

ADULT_TOPOLOGY_TESTS = (
    "continuous_body_surface",
    "adult_complete_topology",
    "head_neck_torso_continuity",
    "bilateral_hands_five_digits",
    "body_clothing_separation",
)

NON_ADULT_TOPOLOGY_TESTS = (
    "continuous_doll_safe_surface",
    "adult_anatomy_absent",
    "head_neck_torso_continuity",
    "bilateral_hands_five_digits",
    "body_clothing_separation",
)

STABLE_RIG_TESTS = (
    "weight_deformation",
    "shoulder_elbow_wrist",
    "hand_and_finger",
    "hip_knee_ankle",
    "idle_breathing",
    "walk",
    "stop",
    "turn",
    "sit",
    "rise_from_sit",
    "lie_down",
    "rise_from_lie",
    "visual_deformation",
)

FACE_LIP_SYNC_TESTS = (
    "blink",
    "gaze",
    "jaw",
    "emotion",
    "viseme_set",
    "text_to_viseme_timing",
    "audio_lip_sync",
)

LOCOMOTION_CONTACT_TESTS = (
    "grounded_walk",
    "stop_without_foot_slide",
    "turn_without_foot_slide",
    "stair_contact",
    "collision_safe_route",
    "door_hand_contact",
    "sit_support",
    "stand_support",
    "lie_support",
    "self_intersection",
    "garment_penetration",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _text(value).lower()).strip("_")


def _valid_sha256(value: Any) -> bool:
    return bool(SHA256_RE.fullmatch(_text(value).lower()))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _evaluate_identity_preflight(
    value: Mapping[str, Any] | None,
    *,
    candidate_id: str,
    subject_id: str,
    topology_lane: str,
) -> dict[str, Any]:
    """Validate a freshly computed canonical-profile preflight when supplied.

    In-memory contract tests may omit this external filesystem binding.  The
    file-based evaluator and production queue supply it whenever the project
    has the identity registry, so real requests cannot treat their own maturity
    declarations as canonical profile authority.
    """

    if value is None:
        return {
            "gate_id": "canonical_identity_preflight",
            "status": "not_enforced_for_in_memory_contract",
            "passed": None,
            "enforced": False,
            "failures": [],
        }
    preflight = _mapping(value)
    failures: list[str] = []
    raw_failures = preflight.get("failures", [])
    if not isinstance(raw_failures, list):
        raw_failures = ["malformed_failure_list"]
    failures.extend(
        f"identity_preflight_{_normalized(failure) or 'unspecified_failure'}"
        for failure in raw_failures
    )
    if preflight.get("passed") is not True:
        failures.append("identity_preflight_not_passed")
    if preflight.get("registry_binding_verified") is not True:
        failures.append("identity_preflight_registry_binding_not_verified")
    if _text(preflight.get("requested_candidate_id")) != candidate_id:
        failures.append("identity_preflight_requested_candidate_mismatch")
    if _text(preflight.get("requested_subject_id")) != subject_id:
        failures.append("identity_preflight_requested_subject_mismatch")
    identity = _mapping(preflight.get("identity"))
    if _text(identity.get("subject_id")) != subject_id:
        failures.append("identity_preflight_canonical_subject_mismatch")
    registry = _mapping(preflight.get("registry"))
    if not _valid_sha256(registry.get("sha256")):
        failures.append("identity_preflight_registry_sha256_invalid")
    profile = _mapping(preflight.get("canonical_profile"))
    if not _valid_sha256(profile.get("sha256")):
        failures.append("identity_preflight_profile_sha256_invalid")
    if profile.get("mutation_performed") is not False:
        failures.append("identity_preflight_profile_mutation_not_excluded")
    maturity = _mapping(preflight.get("maturity"))
    if _text(maturity.get("safety_topology_lane")) != topology_lane:
        failures.append("identity_preflight_topology_lane_mismatch")
    if preflight.get("authoring_allowed") is not True:
        failures.append("identity_preflight_authoring_not_allowed")
    if preflight.get("runtime_activation_allowed") is not False:
        failures.append("identity_preflight_must_not_authorize_runtime")
    failures = list(dict.fromkeys(failures))
    return {
        "gate_id": "canonical_identity_preflight",
        "status": "passed" if not failures else "blocked",
        "passed": not failures,
        "enforced": True,
        "requested_candidate_id": _text(preflight.get("requested_candidate_id")),
        "canonical_candidate_id": _text(preflight.get("canonical_candidate_id")),
        "candidate_alias_used": preflight.get("candidate_alias_used") is True,
        "identity_class": _text(identity.get("identity_class")),
        "variant_kind": _text(identity.get("variant_kind")),
        "selected_version": _text(identity.get("selected_version")),
        "maturity_lane": _text(maturity.get("lane")),
        "registry_sha256": _text(registry.get("sha256")),
        "profile_sha256": _text(profile.get("sha256")),
        "manual_review_notes": list(preflight.get("manual_review_notes", []))
        if isinstance(preflight.get("manual_review_notes"), list)
        else [],
        "failures": failures,
    }


def canonical_sha256(value: Any) -> str:
    try:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return ""
    return hashlib.sha256(payload).hexdigest()


def _reviewed_test_gate(
    gate_id: str,
    evidence_value: Any,
    *,
    expected_artifact_sha256: str,
    required_tests: tuple[str, ...],
) -> dict[str, Any]:
    evidence = _mapping(evidence_value)
    failures: list[str] = []
    digest = _text(evidence.get("artifact_sha256")).lower()
    expected = _text(expected_artifact_sha256).lower()
    if not evidence:
        return {
            "gate_id": gate_id,
            "status": "blocked",
            "passed": False,
            "artifact_sha256": "",
            "required_tests": list(required_tests),
            "missing_or_failed_tests": list(required_tests),
            "failures": [f"{gate_id}_evidence_missing"],
        }
    if not _valid_sha256(expected):
        failures.append(f"{gate_id}_expected_artifact_sha256_invalid")
    if digest != expected:
        failures.append(f"{gate_id}_artifact_sha256_mismatch")
    if evidence.get("exact_artifact_hash_verified") is not True:
        failures.append(f"{gate_id}_exact_artifact_hash_not_verified")
    if _normalized(evidence.get("review_status")) not in PASS_STATUSES:
        failures.append(f"{gate_id}_review_not_passed")
    if not _text(evidence.get("reviewed_by")):
        failures.append(f"{gate_id}_reviewer_missing")
    if not _text(evidence.get("reviewed_at")):
        failures.append(f"{gate_id}_review_timestamp_missing")
    tests = _mapping(evidence.get("test_results"))
    missing_tests = [
        test_id
        for test_id in required_tests
        if _normalized(tests.get(test_id)) != "passed"
    ]
    failures.extend(f"{gate_id}_test_not_passed_{test_id}" for test_id in missing_tests)
    failures = list(dict.fromkeys(failures))
    return {
        "gate_id": gate_id,
        "status": "passed" if not failures else "blocked",
        "passed": not failures,
        "artifact_sha256": digest,
        "required_tests": list(required_tests),
        "missing_or_failed_tests": missing_tests,
        "failures": failures,
    }


def _evaluate_maturity_route(
    request: Mapping[str, Any],
    *,
    candidate_id: str,
    subject_id: str,
) -> dict[str, Any]:
    policy = _mapping(request.get("maturity_policy"))
    evidence = _mapping(policy.get("evidence"))
    maturity_class = _normalized(policy.get("maturity_class"))
    failures: list[str] = []

    if maturity_class in ADULT_MATURITY_CLASSES:
        lane = CONFIRMED_ADULT_TOPOLOGY
    elif maturity_class in NON_ADULT_MATURITY_CLASSES:
        lane = NON_ADULT_DOLL_SAFE_TOPOLOGY
    else:
        lane = "blocked_unclassified_topology"
        failures.append("invalid_or_missing_maturity_class")

    if _text(evidence.get("candidate_id")) != candidate_id:
        failures.append("maturity_evidence_candidate_mismatch")
    if _text(evidence.get("subject_id")) != subject_id:
        failures.append("maturity_evidence_subject_mismatch")
    if _normalized(evidence.get("maturity_class")) != maturity_class:
        failures.append("maturity_evidence_class_mismatch")
    if not _valid_sha256(evidence.get("evidence_sha256")):
        failures.append("maturity_evidence_sha256_invalid")
    if evidence.get("exact_evidence_hash_verified") is not True:
        failures.append("maturity_evidence_hash_not_verified")
    if evidence.get("exact_subject_bound") is not True:
        failures.append("maturity_evidence_not_exact_subject_bound")
    if _normalized(evidence.get("review_status")) not in PASS_STATUSES:
        failures.append("maturity_evidence_not_reviewed")

    request_adult = request.get("request_complete_adult_anatomy") is True
    if lane == NON_ADULT_DOLL_SAFE_TOPOLOGY and request_adult:
        failures.append("adult_complete_anatomy_forbidden_in_non_adult_doll_safe_lane")

    failures = list(dict.fromkeys(failures))
    return {
        "status": "selected" if lane != "blocked_unclassified_topology" else "blocked",
        "selected_lane": lane,
        "maturity_class": maturity_class,
        "route_valid": not failures,
        "failures": failures,
        "lane_decisions": {
            CONFIRMED_ADULT_TOPOLOGY: lane == CONFIRMED_ADULT_TOPOLOGY,
            NON_ADULT_DOLL_SAFE_TOPOLOGY: lane == NON_ADULT_DOLL_SAFE_TOPOLOGY,
        },
    }


def _evaluate_licensed_source(
    evidence_value: Any,
    *,
    candidate_id: str,
    subject_id: str,
    topology_lane: str,
    candidate_body_sha256: str,
) -> list[str]:
    evidence = _mapping(evidence_value)
    failures: list[str] = []

    checks = (
        (evidence.get("selected") is True, "licensed_derivative_not_explicitly_selected"),
        (_text(evidence.get("candidate_id")) == candidate_id, "licensed_derivative_candidate_mismatch"),
        (_text(evidence.get("subject_id")) == subject_id, "licensed_derivative_subject_mismatch"),
        (_valid_sha256(evidence.get("source_sha256")), "licensed_source_sha256_invalid"),
        (evidence.get("exact_source_hash_verified") is True, "licensed_source_hash_not_verified"),
        (_valid_sha256(evidence.get("license_evidence_sha256")), "license_evidence_sha256_invalid"),
        (evidence.get("license_evidence_hash_verified") is True, "license_evidence_hash_not_verified"),
        (evidence.get("adaptation_allowed") is True, "source_license_does_not_allow_adaptation"),
        (evidence.get("attribution_bound") is True, "source_attribution_not_bound"),
        (_valid_sha256(evidence.get("source_role_map_sha256")), "source_role_map_sha256_invalid"),
        (evidence.get("source_role_map_hash_verified") is True, "source_role_map_hash_not_verified"),
        (evidence.get("licensed_source_surface_incorporated") is True, "licensed_surface_incorporation_not_disclosed"),
        (evidence.get("source_surface_shape_preserved") is True, "source_surface_shape_not_preserved"),
        (evidence.get("new_body_surface_authored") is False, "false_new_body_surface_authorship_claim"),
        (evidence.get("source_artifact_byte_copied") is False, "source_artifact_byte_copy_forbidden"),
        (evidence.get("source_materials_and_textures_exported") is False, "source_materials_or_textures_exported"),
        (evidence.get("candidate_output_allowlist_enforced") is True, "candidate_output_allowlist_not_enforced"),
        (_text(evidence.get("candidate_body_sha256")).lower() == _text(candidate_body_sha256).lower(), "licensed_derivative_body_hash_mismatch"),
    )
    failures.extend(failure for passed, failure in checks if not passed)
    if topology_lane == NON_ADULT_DOLL_SAFE_TOPOLOGY and evidence.get("adult_only_source") is not False:
        failures.append("adult_only_or_unscoped_licensed_source_forbidden_in_non_adult_lane")
    return failures


def _evaluate_photo_only_source(
    evidence_value: Any,
    *,
    candidate_id: str,
    topology_lane: str,
) -> list[str]:
    evidence = _mapping(evidence_value)
    contract = _mapping(evidence.get("reconstruction_contract"))
    failures: list[str] = []
    if evidence.get("selected") is not True:
        failures.append("photo_only_reconstruction_not_explicitly_selected")
    if evidence.get("licensed_source_surface_incorporated") is not False:
        failures.append("photo_only_lane_cannot_incorporate_a_model_surface")
    if _text(contract.get("candidate_id")) != candidate_id:
        failures.append("photo_reconstruction_contract_candidate_mismatch")
    if _normalized(contract.get("identity_reconstruction_mode")) != "picture_first_models_optional":
        failures.append("photo_reconstruction_contract_mode_mismatch")
    if contract.get("staging_allowed") is not True:
        failures.append("photo_reconstruction_contract_not_ready")
    pictures = _mapping(contract.get("picture_evidence"))
    if pictures.get("minimum_multiview_identity_set_present") is not True:
        failures.append("photo_only_multiview_identity_set_missing")
    models = _mapping(contract.get("optional_model_evidence"))
    if models.get("total_count") not in {0, None}:
        failures.append("photo_only_lane_contains_model_references")
    if models.get("optional_measurement_reference_count") not in {0, None}:
        failures.append("photo_only_lane_uses_model_measurement_reference")
    base = _mapping(contract.get("maturity_base_contract"))
    treatment = _normalized(base.get("base_treatment"))
    expected = (
        "neutral_adult_anatomy"
        if topology_lane == CONFIRMED_ADULT_TOPOLOGY
        else "non_adult_doll_safe"
    )
    if treatment != expected:
        failures.append("photo_reconstruction_contract_topology_lane_mismatch")
    if contract.get("runtime_activation_allowed") is not False:
        failures.append("photo_reconstruction_contract_must_not_authorize_runtime")
    return failures


def _evaluate_photo_primary_reference_model_source(
    evidence_value: Any,
    *,
    candidate_id: str,
    topology_lane: str,
    candidate_body_sha256: str,
) -> list[str]:
    """Validate pictures-as-identity plus model-as-measurement guidance.

    The reference model may contribute reviewed measurements/topology guidance,
    but its surface, texture, and identity cannot become candidate geometry.
    """

    evidence = _mapping(evidence_value)
    contract = _mapping(evidence.get("reconstruction_contract"))
    model = _mapping(evidence.get("reference_model"))
    failures: list[str] = []
    checks = (
        (evidence.get("selected") is True, "photo_primary_model_lane_not_explicitly_selected"),
        (evidence.get("pictures_are_identity_authority") is True, "pictures_not_declared_identity_authority"),
        (evidence.get("reference_model_is_identity_authority") is False, "reference_model_must_not_be_identity_authority"),
        (evidence.get("licensed_source_surface_incorporated") is False, "photo_primary_model_lane_cannot_incorporate_reference_surface"),
        (evidence.get("reference_model_surface_copied") is False, "reference_model_surface_copy_forbidden"),
        (evidence.get("reference_model_materials_or_textures_copied") is False, "reference_model_material_or_texture_copy_forbidden"),
        (evidence.get("new_candidate_surface_authored") is True, "new_candidate_surface_authorship_required"),
        (_text(evidence.get("candidate_body_sha256")).lower() == _text(candidate_body_sha256).lower(), "photo_primary_model_candidate_body_hash_mismatch"),
        (_valid_sha256(model.get("artifact_sha256")), "reference_model_sha256_invalid"),
        (model.get("exact_artifact_hash_verified") is True, "reference_model_hash_not_verified"),
        (_normalized(model.get("role")) == "measurement_and_topology_guidance_only", "reference_model_role_mismatch"),
        (_valid_sha256(model.get("usage_evidence_sha256")), "reference_model_usage_evidence_sha256_invalid"),
        (model.get("usage_evidence_hash_verified") is True, "reference_model_usage_evidence_hash_not_verified"),
        (model.get("measurement_guidance_use_allowed") is True, "reference_model_measurement_use_not_allowed"),
        (model.get("surface_copy_allowed") is False, "reference_model_surface_copy_must_be_disallowed"),
    )
    failures.extend(failure for passed, failure in checks if not passed)
    if _text(model.get("artifact_sha256")).lower() == _text(candidate_body_sha256).lower():
        failures.append("candidate_body_must_not_be_reference_model_byte_copy")
    if topology_lane == NON_ADULT_DOLL_SAFE_TOPOLOGY and model.get("adult_only_source") is not False:
        failures.append("adult_only_reference_model_forbidden_in_non_adult_lane")

    if _text(contract.get("candidate_id")) != candidate_id:
        failures.append("photo_reconstruction_contract_candidate_mismatch")
    if _normalized(contract.get("identity_reconstruction_mode")) != "picture_first_models_optional":
        failures.append("photo_reconstruction_contract_mode_mismatch")
    if contract.get("staging_allowed") is not True:
        failures.append("photo_reconstruction_contract_not_ready")
    pictures = _mapping(contract.get("picture_evidence"))
    if pictures.get("minimum_multiview_identity_set_present") is not True:
        failures.append("photo_primary_multiview_identity_set_missing")
    if pictures.get("accepted_pictures_are_identity_authority") is not True:
        failures.append("accepted_multiview_not_bound_as_identity_authority")
    models = _mapping(contract.get("optional_model_evidence"))
    total_count = models.get("total_count")
    measurement_count = models.get("optional_measurement_reference_count")
    if not isinstance(total_count, int) or total_count < 1:
        failures.append("reference_model_count_missing")
    if (
        not isinstance(measurement_count, int)
        or measurement_count < 1
        or (isinstance(total_count, int) and measurement_count > total_count)
    ):
        failures.append("reference_model_measurement_count_invalid")
    if models.get("models_are_identity_authority") is not False:
        failures.append("optional_models_must_not_be_identity_authority")
    if models.get("surface_copy_allowed") is not False:
        failures.append("optional_model_surface_copy_must_be_false")
    base = _mapping(contract.get("maturity_base_contract"))
    treatment = _normalized(base.get("base_treatment"))
    expected = (
        "neutral_adult_anatomy"
        if topology_lane == CONFIRMED_ADULT_TOPOLOGY
        else "non_adult_doll_safe"
    )
    if treatment != expected:
        failures.append("photo_reconstruction_contract_topology_lane_mismatch")
    if contract.get("runtime_activation_allowed") is not False:
        failures.append("photo_reconstruction_contract_must_not_authorize_runtime")
    return failures


def _evaluate_source_route(
    request: Mapping[str, Any],
    *,
    candidate_id: str,
    subject_id: str,
    topology_lane: str,
    candidate_body_sha256: str,
) -> dict[str, Any]:
    strategy = _mapping(request.get("source_strategy"))
    mode = _normalized(strategy.get("mode"))
    licensed = _mapping(strategy.get("licensed_derivative"))
    photo = _mapping(strategy.get("photo_only"))
    photo_primary_model = _mapping(
        strategy.get("photo_primary_with_reference_model_measurement")
    )
    failures: list[str] = []

    selected_count = sum(
        record.get("selected") is True
        for record in (licensed, photo, photo_primary_model)
    )
    if selected_count > 1:
        failures.append("multiple_reconstruction_source_lanes_selected")

    if mode == LICENSED_SHAPE_PRESERVING_DERIVATIVE:
        lane = LICENSED_SHAPE_PRESERVING_DERIVATIVE
        if photo.get("selected") is not False:
            failures.append("photo_only_lane_must_be_explicitly_unselected")
        if photo_primary_model.get("selected") is True:
            failures.append("photo_primary_model_lane_must_be_explicitly_unselected")
        failures.extend(
            _evaluate_licensed_source(
                licensed,
                candidate_id=candidate_id,
                subject_id=subject_id,
                topology_lane=topology_lane,
                candidate_body_sha256=candidate_body_sha256,
            )
        )
    elif mode == PHOTO_ONLY_RECONSTRUCTION:
        lane = PHOTO_ONLY_RECONSTRUCTION
        if licensed.get("selected") is not False:
            failures.append("licensed_derivative_lane_must_be_explicitly_unselected")
        if photo_primary_model.get("selected") is True:
            failures.append("photo_primary_model_lane_must_be_explicitly_unselected")
        failures.extend(
            _evaluate_photo_only_source(
                photo,
                candidate_id=candidate_id,
                topology_lane=topology_lane,
            )
        )
    elif mode == PHOTO_PRIMARY_WITH_REFERENCE_MODEL_MEASUREMENT:
        lane = PHOTO_PRIMARY_WITH_REFERENCE_MODEL_MEASUREMENT
        if licensed.get("selected") is not False:
            failures.append("licensed_derivative_lane_must_be_explicitly_unselected")
        if photo.get("selected") is True:
            failures.append("photo_only_lane_must_be_explicitly_unselected")
        failures.extend(
            _evaluate_photo_primary_reference_model_source(
                photo_primary_model,
                candidate_id=candidate_id,
                topology_lane=topology_lane,
                candidate_body_sha256=candidate_body_sha256,
            )
        )
    else:
        lane = "blocked_unclassified_source"
        failures.append("invalid_or_missing_reconstruction_source_lane")

    failures = list(dict.fromkeys(failures))
    return {
        "status": "selected" if lane != "blocked_unclassified_source" else "blocked",
        "selected_lane": lane,
        "route_valid": not failures,
        "failures": failures,
        "lane_decisions": {
            LICENSED_SHAPE_PRESERVING_DERIVATIVE: lane
            == LICENSED_SHAPE_PRESERVING_DERIVATIVE,
            PHOTO_ONLY_RECONSTRUCTION: lane == PHOTO_ONLY_RECONSTRUCTION,
            PHOTO_PRIMARY_WITH_REFERENCE_MODEL_MEASUREMENT: lane
            == PHOTO_PRIMARY_WITH_REFERENCE_MODEL_MEASUREMENT,
        },
    }


def _evaluate_components(request: Mapping[str, Any]) -> dict[str, Any]:
    components = _mapping(request.get("components"))
    if not components:
        return {
            "status": "blocked",
            "passed": False,
            "component_sha256": {role: "" for role in COMPONENT_ROLES},
            "required_roles": list(COMPONENT_ROLES),
            "failures": ["component_manifest_missing"],
        }
    failures: list[str] = []
    hashes: dict[str, str] = {}
    for role in COMPONENT_ROLES:
        record = _mapping(components.get(role))
        digest = _text(record.get("artifact_sha256")).lower()
        hashes[role] = digest
        if _normalized(record.get("artifact_role")) != role:
            failures.append(f"component_{role}_role_mismatch")
        if not _valid_sha256(digest):
            failures.append(f"component_{role}_sha256_invalid_or_missing")
        if record.get("exact_artifact_hash_verified") is not True:
            failures.append(f"component_{role}_exact_hash_not_verified")
        if record.get("separate_artifact") is not True:
            failures.append(f"component_{role}_not_separate")
    valid_hashes = [digest for digest in hashes.values() if _valid_sha256(digest)]
    if len(valid_hashes) != len(set(valid_hashes)):
        failures.append("component_artifact_hashes_must_be_distinct")
    body = _mapping(components.get("body"))
    if body.get("contains_hair") is not False:
        failures.append("body_artifact_contains_or_does_not_exclude_hair")
    if body.get("contains_eyes") is not False:
        failures.append("body_artifact_contains_or_does_not_exclude_eyes")
    if body.get("contains_clothes") is not False:
        failures.append("body_artifact_contains_or_does_not_exclude_clothes")
    failures = list(dict.fromkeys(failures))
    return {
        "status": "passed" if not failures else "blocked",
        "passed": not failures,
        "component_sha256": hashes,
        "required_roles": list(COMPONENT_ROLES),
        "failures": failures,
    }


def _evaluate_owner_clothed_review(
    evidence_value: Any,
    *,
    owner_identity_value: Any,
    candidate_id: str,
    subject_id: str,
    body_sha256: str,
    clothes_sha256: str,
) -> dict[str, Any]:
    owner_identity = _mapping(owner_identity_value)
    evidence = _mapping(evidence_value)
    failures: list[str] = []

    owner_id = _text(owner_identity.get("owner_id"))
    owner_authority_sha256 = _text(
        owner_identity.get("authority_artifact_sha256")
    ).lower()
    if not owner_identity:
        failures.append("owner_identity_evidence_missing")
    else:
        if not owner_id:
            failures.append("owner_identity_id_missing")
        if _text(owner_identity.get("candidate_id")) != candidate_id:
            failures.append("owner_identity_candidate_mismatch")
        if _text(owner_identity.get("subject_id")) != subject_id:
            failures.append("owner_identity_subject_mismatch")
        if _normalized(owner_identity.get("authority_status")) not in OWNER_AUTHORITY_STATUSES:
            failures.append("owner_identity_authority_not_verified")
        if not _valid_sha256(owner_authority_sha256):
            failures.append("owner_identity_authority_artifact_sha256_invalid")
        if owner_identity.get("exact_authority_artifact_hash_verified") is not True:
            failures.append("owner_identity_authority_artifact_hash_not_verified")

    if not evidence:
        failures.append("owner_clothed_review_evidence_missing")
        failures = list(dict.fromkeys(failures))
        return {
            "gate_id": "owner_clothed_review",
            "status": "blocked",
            "passed": False,
            "owner_id": owner_id,
            "owner_authority_artifact_sha256": owner_authority_sha256,
            "approval_artifact_sha256": "",
            "failures": failures,
        }

    if _normalized(evidence.get("approval_status")) not in {"approved", "approved_clothed_review"}:
        failures.append("owner_clothed_review_not_approved")
    if _text(evidence.get("candidate_id")) != candidate_id:
        failures.append("owner_review_candidate_mismatch")
    if _text(evidence.get("subject_id")) != subject_id:
        failures.append("owner_review_subject_mismatch")
    if _text(evidence.get("owner_id")) != owner_id or not owner_id:
        failures.append("owner_review_owner_identity_mismatch")
    if (
        _text(evidence.get("owner_authority_artifact_sha256")).lower()
        != owner_authority_sha256
        or not _valid_sha256(owner_authority_sha256)
    ):
        failures.append("owner_review_authority_artifact_mismatch")
    if _text(evidence.get("body_sha256")).lower() != body_sha256:
        failures.append("owner_review_body_sha256_mismatch")
    if _text(evidence.get("clothes_sha256")).lower() != clothes_sha256:
        failures.append("owner_review_clothes_sha256_mismatch")
    if not _valid_sha256(evidence.get("clothed_assembly_sha256")):
        failures.append("owner_review_clothed_assembly_sha256_invalid")
    approval_artifact_sha256 = _text(evidence.get("approval_artifact_sha256")).lower()
    if not _valid_sha256(approval_artifact_sha256):
        failures.append("owner_review_approval_artifact_sha256_invalid")
    if evidence.get("exact_approval_artifact_hash_verified") is not True:
        failures.append("owner_review_approval_artifact_hash_not_verified")
    approved_by = _text(evidence.get("approved_by"))
    if not approved_by:
        failures.append("owner_review_approver_missing")
    elif approved_by != owner_id:
        failures.append("owner_review_approver_is_not_bound_owner")
    if not _text(evidence.get("approved_at")):
        failures.append("owner_review_timestamp_missing")
    if evidence.get("clothed_only") is not True:
        failures.append("owner_review_must_be_clothed_only")
    if evidence.get("private_body_displayed") is not False:
        failures.append("owner_review_private_body_exposure_not_excluded")
    failures = list(dict.fromkeys(failures))
    return {
        "gate_id": "owner_clothed_review",
        "status": "passed" if not failures else "blocked",
        "passed": not failures,
        "owner_id": owner_id,
        "owner_authority_artifact_sha256": owner_authority_sha256,
        "approval_artifact_sha256": approval_artifact_sha256,
        "failures": failures,
    }


def evaluate_avatar_builder_orchestration(
    request: Mapping[str, Any] | None,
    *,
    identity_preflight: Mapping[str, Any] | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Return a source/maturity route and honest readiness decision."""

    data = request if isinstance(request, Mapping) else {}
    candidate_id = _text(data.get("candidate_id"))
    subject_id = _text(data.get("subject_id"))
    request_sha256 = canonical_sha256(data)
    global_failures: list[str] = []
    if not candidate_id:
        global_failures.append("candidate_id_missing")
    if not subject_id:
        global_failures.append("subject_id_missing")
    if not request_sha256:
        global_failures.append("request_not_canonical_json")
    if data.get("render_requested") is not False:
        global_failures.append("render_requested_must_be_false")
    if data.get("runtime_activation_requested") is not False:
        global_failures.append("runtime_activation_requested_must_be_false")

    reusable_method_gate = evaluate_reusable_method_selection(
        Path(project_root) if project_root is not None else Path.cwd(),
        data.get("reusable_method_id"),
    )

    components = _evaluate_components(data)
    body_sha = components["component_sha256"].get("body", "")
    clothes_sha = components["component_sha256"].get("clothes", "")
    maturity_route = _evaluate_maturity_route(
        data,
        candidate_id=candidate_id,
        subject_id=subject_id,
    )
    identity_preflight_gate = _evaluate_identity_preflight(
        identity_preflight,
        candidate_id=candidate_id,
        subject_id=subject_id,
        topology_lane=maturity_route["selected_lane"],
    )
    source_route = _evaluate_source_route(
        data,
        candidate_id=candidate_id,
        subject_id=subject_id,
        topology_lane=maturity_route["selected_lane"],
        candidate_body_sha256=body_sha,
    )

    readiness = _mapping(data.get("readiness_evidence"))
    topology_tests = (
        ADULT_TOPOLOGY_TESTS
        if maturity_route["selected_lane"] == CONFIRMED_ADULT_TOPOLOGY
        else NON_ADULT_TOPOLOGY_TESTS
    )
    topology_gate = _reviewed_test_gate(
        "topology",
        readiness.get("topology"),
        expected_artifact_sha256=body_sha,
        required_tests=topology_tests,
    )
    topology_evidence = _mapping(readiness.get("topology"))
    expected_treatment = (
        "neutral_adult_anatomy"
        if maturity_route["selected_lane"] == CONFIRMED_ADULT_TOPOLOGY
        else "non_adult_doll_safe"
    )
    if topology_evidence:
        if _normalized(topology_evidence.get("body_treatment")) != expected_treatment:
            topology_gate["failures"].append("topology_body_treatment_mismatch")
        if (
            maturity_route["selected_lane"] == NON_ADULT_DOLL_SAFE_TOPOLOGY
            and topology_evidence.get("adult_anatomy_present") is not False
        ):
            topology_gate["failures"].append("non_adult_topology_does_not_exclude_adult_anatomy")
    topology_gate["failures"] = list(dict.fromkeys(topology_gate["failures"]))
    topology_gate["passed"] = not topology_gate["failures"]
    topology_gate["status"] = "passed" if topology_gate["passed"] else "blocked"

    stable_rig_gate = _reviewed_test_gate(
        "stable_rig",
        readiness.get("stable_rig"),
        expected_artifact_sha256=body_sha,
        required_tests=STABLE_RIG_TESTS,
    )
    stable_rig_evidence = _mapping(readiness.get("stable_rig"))
    if stable_rig_evidence:
        if stable_rig_evidence.get("heuristic_only") is not False:
            stable_rig_gate["failures"].append("stable_rig_remains_heuristic_only")
        if stable_rig_evidence.get("visual_deformation_reviewed") is not True:
            stable_rig_gate["failures"].append("stable_rig_visual_deformation_not_reviewed")
    stable_rig_gate["failures"] = list(dict.fromkeys(stable_rig_gate["failures"]))
    stable_rig_gate["passed"] = not stable_rig_gate["failures"]
    stable_rig_gate["status"] = "passed" if stable_rig_gate["passed"] else "blocked"

    face_gate = _reviewed_test_gate(
        "face_lip_sync",
        readiness.get("face_lip_sync"),
        expected_artifact_sha256=body_sha,
        required_tests=FACE_LIP_SYNC_TESTS,
    )
    locomotion_gate = _reviewed_test_gate(
        "locomotion_contact",
        readiness.get("locomotion_contact"),
        expected_artifact_sha256=body_sha,
        required_tests=LOCOMOTION_CONTACT_TESTS,
    )

    rig_binding = _mapping(data.get("rig_binding"))
    rig_sha = _text(rig_binding.get("rig_sha256")).lower()
    rig_binding_failures: list[str] = []
    if not _valid_sha256(rig_sha):
        rig_binding_failures.append("rig_binding_sha256_invalid_or_missing")
    if rig_binding.get("exact_rig_hash_verified") is not True:
        rig_binding_failures.append("rig_binding_exact_hash_not_verified")
    rig_binding_gate = {
        "gate_id": "rig_binding",
        "status": "passed" if not rig_binding_failures else "blocked",
        "passed": not rig_binding_failures,
        "rig_sha256": rig_sha,
        "failures": rig_binding_failures,
    }

    wearable_gate = evaluate_wearable_capability_manifest(
        _mapping(readiness.get("wearable_capability")),
        candidate_id=candidate_id,
        subject_id=subject_id,
        garment_sha256=clothes_sha,
        body_sha256=body_sha,
        rig_sha256=rig_sha,
    )
    owner_gate = _evaluate_owner_clothed_review(
        readiness.get("owner_clothed_review"),
        owner_identity_value=data.get("owner_identity"),
        candidate_id=candidate_id,
        subject_id=subject_id,
        body_sha256=body_sha,
        clothes_sha256=clothes_sha,
    )

    privacy = _mapping(data.get("privacy"))
    privacy_failures: list[str] = []
    if _normalized(privacy.get("normal_review_route")) != "clothed_only":
        privacy_failures.append("normal_review_route_must_be_clothed_only")
    if privacy.get("intimate_render_retained") is not False:
        privacy_failures.append("intimate_render_retention_must_be_false")
    if privacy.get("private_source_paths_in_report") is not False:
        privacy_failures.append("private_source_paths_must_be_omitted_from_report")
    if privacy.get("public_export_allowed") is not False:
        privacy_failures.append("public_export_must_be_false")
    privacy_gate = {
        "gate_id": "privacy",
        "status": "passed" if not privacy_failures else "blocked",
        "passed": not privacy_failures,
        "failures": privacy_failures,
    }

    route_failures = [
        *global_failures,
        *maturity_route["failures"],
        *source_route["failures"],
        *identity_preflight_gate["failures"],
    ]
    capability_gates = {
        "reusable_method_selection": reusable_method_gate,
        "component_integrity": components,
        "topology": topology_gate,
        "rig_binding": rig_binding_gate,
        "stable_rig": stable_rig_gate,
        "face_lip_sync": face_gate,
        "locomotion_contact": locomotion_gate,
        "wearable_capability": wearable_gate,
        "privacy": privacy_gate,
        "owner_clothed_review": owner_gate,
    }
    all_gate_failures: list[str] = list(route_failures)
    for gate in capability_gates.values():
        all_gate_failures.extend(str(value) for value in gate.get("failures", []))
    all_gate_failures = list(dict.fromkeys(all_gate_failures))

    route_valid = not route_failures
    # Advanced garment behavior is intentionally independent from body review.
    # A tied-robe lifecycle is a later physical capability exam, not evidence
    # that the exact body/rig/face/locomotion package exists.  The body review
    # route still requires a distinct clothes artifact, clothed-only privacy,
    # and owner review of the clothed assembly.
    body_private_review_gate_ids = (
        "reusable_method_selection",
        "component_integrity",
        "topology",
        "rig_binding",
        "stable_rig",
        "face_lip_sync",
        "locomotion_contact",
        "privacy",
        "owner_clothed_review",
    )
    body_blocking_reasons: list[str] = list(route_failures)
    for gate_id in body_private_review_gate_ids:
        body_blocking_reasons.extend(
            str(value) for value in capability_gates[gate_id].get("failures", [])
        )
    body_blocking_reasons = list(dict.fromkeys(body_blocking_reasons))
    garment_blocking_reasons = list(
        dict.fromkeys(
            str(value)
            for value in capability_gates["wearable_capability"].get("failures", [])
        )
    )
    body_private_review_ready = route_valid and all(
        bool(gate.get("passed") or gate.get("capability_evidence_complete"))
        for gate_id, gate in capability_gates.items()
        if gate_id in body_private_review_gate_ids
    )
    garment_capability_ready = bool(
        capability_gates["wearable_capability"].get("passed")
        or capability_gates["wearable_capability"].get("capability_evidence_complete")
    )
    review_stage_allowed = body_private_review_ready
    result: dict[str, Any] = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "subject_id": subject_id,
        "request_sha256": request_sha256,
        "route": {
            "status": "selected_and_valid" if route_valid else "selected_but_blocked",
            "topology_lane": maturity_route["selected_lane"],
            "reconstruction_source_lane": source_route["selected_lane"],
            "ordered_lanes": [
                source_route["selected_lane"],
                maturity_route["selected_lane"],
            ],
            "lane_decisions": {
                **maturity_route["lane_decisions"],
                **source_route["lane_decisions"],
            },
            "failures": route_failures,
        },
        "identity_preflight": identity_preflight_gate,
        "capability_gates": capability_gates,
        "status": (
            "ready_for_private_clothed_review_only"
            if body_private_review_ready and garment_capability_ready
            else (
                "ready_for_private_clothed_review_garment_capability_pending"
                if body_private_review_ready
                else "capability_review_blocked"
            )
        ),
        "body_private_review_ready": body_private_review_ready,
        "body_private_review_gate_ids": list(body_private_review_gate_ids),
        "body_blocking_reasons": body_blocking_reasons,
        "advanced_garment_capability_ready": garment_capability_ready,
        "garment_blocking_reasons": garment_blocking_reasons,
        "review_stage_allowed": review_stage_allowed,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
        "caller_declarations_are_runtime_authority": False,
        "trusted_worker_rehash_required_before_mutation": True,
        "blocking_reasons": all_gate_failures,
        "separate_runtime_authority_required": True,
        "truth_note": (
            "This decision validates route and evidence contracts only. It does not render or "
            "activate a person, run a live simulation, prove visual quality from labels, or "
            "authorize public/runtime use. Runtime activation remains a separate owner-controlled "
            "default-deny workflow even when every capability gate passes. Advanced garment "
            "behavior is reported independently and does not block private review of an "
            "otherwise complete basic clothed body package."
        ),
    }
    result["decision_sha256"] = canonical_sha256(result)
    return result
