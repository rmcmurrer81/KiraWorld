"""Fail-closed wearable capability evidence for Avatar Builder.

This module validates a *capability manifest*.  It does not run a cloth
simulation, advance a garment state machine, render a body, or authorize a
wearable for runtime use.  A passing result means only that exact-hash,
physics-trace evidence has been supplied for the complete two-sleeve robe
lifecycle described below.

The manifest deliberately distinguishes a stored or released garment from a
garment still owned by an avatar.  It also requires both possible arm orders
for dressing and undressing so a one-sided animation cannot be presented as a
general clothing capability.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PASS_STATUSES = frozenset({"approved", "pass", "passed"})
TRACE_BASES = frozenset(
    {
        "runtime_collision_and_physics_trace",
        "runtime_sensor_trace",
        "verified_physics_trace",
    }
)

REQUIRED_ROBE_STATES = (
    "stored_hung",
    "stored_folded",
    "grasped",
    "right_sleeve_threaded",
    "left_sleeve_threaded",
    "both_sleeves_threaded",
    "worn_open",
    "worn_tied",
    "held_after_undressing",
    "released_hung",
    "released_folded",
)

REQUIRED_ROBE_TRANSITIONS = (
    "hung_to_grasped",
    "folded_to_grasped",
    "dress_right_arm_first",
    "dress_left_arm_first",
    "dress_left_arm_second",
    "dress_right_arm_second",
    "settle_both_arms_worn_open",
    "tie_worn",
    "untie_worn",
    "undress_left_arm_first",
    "undress_right_arm_first",
    "undress_left_arm_second",
    "undress_right_arm_second",
    "release_to_hung",
    "release_to_folded",
)

REQUIRED_ROBE_PHASES = REQUIRED_ROBE_STATES + REQUIRED_ROBE_TRANSITIONS


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _text(value).lower()).strip("_")


def _valid_sha256(value: Any) -> bool:
    return bool(SHA256_RE.fullmatch(_text(value).lower()))


def canonical_sha256(value: Any) -> str:
    """Hash JSON evidence without retaining images, geometry, or raw traces."""

    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return ""
    return hashlib.sha256(encoded).hexdigest()


def _positive_int(value: Any, minimum: int) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= minimum
    )


def _phase_specific_failures(phase_id: str, payload: Mapping[str, Any]) -> list[str]:
    """Require physical facts appropriate to one lifecycle phase."""

    failures: list[str] = []

    def require(condition: bool, suffix: str) -> None:
        if not condition:
            failures.append(f"phase_{phase_id}_{suffix}")

    if phase_id in {"stored_hung", "released_hung"}:
        require(bool(_text(payload.get("hook_anchor_id"))), "hook_anchor_missing")
        require(payload.get("supported_by_named_hook") is True, "hook_support_not_proven")
        require(payload.get("hand_contact_active") is False, "hand_not_released")
        require(_positive_int(payload.get("stable_sample_count"), 3), "stable_samples_missing")

    if phase_id in {"stored_folded", "released_folded"}:
        require(bool(_text(payload.get("storage_surface_anchor_id"))), "storage_anchor_missing")
        require(payload.get("folded_geometry_observed") is True, "folded_geometry_not_proven")
        require(payload.get("supported_by_named_surface") is True, "surface_support_not_proven")
        require(payload.get("hand_contact_active") is False, "hand_not_released")
        require(_positive_int(payload.get("stable_sample_count"), 3), "stable_samples_missing")

    if phase_id in {"grasped", "hung_to_grasped", "folded_to_grasped"}:
        require(bool(_text(payload.get("hand_anchor_id"))), "hand_anchor_missing")
        require(payload.get("hand_contact") is True, "hand_contact_not_proven")
        require(payload.get("held") is True, "held_state_not_proven")
        require(payload.get("source_support_removed") is True, "source_support_not_removed")
        require(payload.get("source_copy_visible_after") is False, "duplicate_source_copy_present")

    if phase_id.startswith("dress_"):
        expected_side = "left" if "left" in phase_id else "right"
        require(bool(_text(payload.get("sleeve_portal_anchor_id"))), "sleeve_portal_missing")
        require(_normalized(payload.get("arm_side")) == expected_side, "arm_side_mismatch")
        require(payload.get("continuous_sleeve_crossing") is True, "continuous_crossing_not_proven")
        require(payload.get("teleported") is False, "teleport_or_direct_placement_reported")
        require(_positive_int(payload.get("path_sample_count"), 3), "path_samples_missing")

    if phase_id in {
        "right_sleeve_threaded",
        "left_sleeve_threaded",
        "both_sleeves_threaded",
    }:
        require(payload.get("sleeve_membership_physically_observed") is True, "sleeve_membership_not_proven")
        if phase_id == "both_sleeves_threaded":
            require(payload.get("left_arm_threaded") is True, "left_arm_not_threaded")
            require(payload.get("right_arm_threaded") is True, "right_arm_not_threaded")

    if phase_id in {"settle_both_arms_worn_open", "worn_open", "worn_tied"}:
        require(payload.get("both_shoulders_supported") is True, "shoulder_support_not_proven")
        require(payload.get("garment_follows_verified_rig") is True, "verified_rig_follow_not_proven")
        require(payload.get("garment_detached") is False, "garment_detached")

    if phase_id in {"tie_worn", "worn_tied"}:
        require(payload.get("both_belt_endpoints_continuous") is True, "belt_endpoint_continuity_missing")
        require(payload.get("knot_formed") is True, "knot_not_formed")
        require(payload.get("knot_secured") is True, "knot_not_secured")
        require(_positive_int(payload.get("two_hand_path_sample_count"), 5), "two_hand_path_missing")

    if phase_id == "untie_worn":
        require(payload.get("both_belt_endpoints_continuous") is True, "belt_endpoint_continuity_missing")
        require(payload.get("knot_released") is True, "knot_not_released")
        require(payload.get("endpoints_separated") is True, "belt_endpoints_not_separated")

    if phase_id.startswith("undress_"):
        expected_side = "left" if "left" in phase_id else "right"
        require(bool(_text(payload.get("sleeve_portal_anchor_id"))), "sleeve_portal_missing")
        require(_normalized(payload.get("arm_side")) == expected_side, "arm_side_mismatch")
        require(payload.get("continuous_sleeve_exit") is True, "continuous_exit_not_proven")
        require(payload.get("teleported") is False, "teleport_or_direct_placement_reported")
        require(payload.get("garment_retained_by_other_arm_or_hand") is True, "garment_control_lost")
        require(_positive_int(payload.get("path_sample_count"), 3), "path_samples_missing")

    if phase_id == "held_after_undressing":
        require(payload.get("both_arms_out") is True, "both_arms_not_out")
        require(payload.get("shoulder_attachment_removed") is True, "shoulder_attachment_not_removed")
        require(payload.get("held") is True, "held_state_not_proven")

    if phase_id in {"release_to_hung", "release_to_folded"}:
        require(payload.get("hand_contact_before_support") is True, "pre_support_hand_contact_missing")
        require(payload.get("target_support_active") is True, "target_support_not_active")
        require(payload.get("hand_released_after_support") is True, "release_after_support_not_proven")
        require(payload.get("source_hand_empty") is True, "source_hand_not_empty")
        require(payload.get("duplicate_active_representations") == 0, "duplicate_representation_present")

    return failures


def evaluate_wearable_capability_manifest(
    manifest: Mapping[str, Any] | None,
    *,
    candidate_id: str,
    subject_id: str,
    garment_sha256: str,
    body_sha256: str,
    rig_sha256: str,
) -> dict[str, Any]:
    """Validate a complete two-sleeve tied-robe capability evidence pack.

    The evaluator is intentionally strict and reusable.  A shirt or other
    garment with a different lifecycle needs a separately reviewed profile;
    callers may not silently mark robe-only phases "not applicable".
    """

    data = manifest if isinstance(manifest, Mapping) else {}
    if not data:
        return {
            "schema_version": 1,
            "candidate_id": _text(candidate_id),
            "subject_id": _text(subject_id),
            "capability_profile": "two_sleeve_tied_robe_v1",
            "status": "blocked",
            "capability_evidence_complete": False,
            "review_stage_allowed": False,
            "runtime_activation_allowed": False,
            "caller_declarations_are_runtime_authority": False,
            "trusted_worker_rehash_required_before_mutation": True,
            "required_states": list(REQUIRED_ROBE_STATES),
            "required_transitions": list(REQUIRED_ROBE_TRANSITIONS),
            "failures": ["wearable_capability_manifest_missing"],
            "truth_note": (
                "No wearable capability manifest was supplied. State names, timers, or a static "
                "robe preview cannot substitute for exact physical evidence."
            ),
        }
    failures: list[str] = []

    def require(condition: bool, failure: str) -> None:
        if not condition:
            failures.append(failure)

    expected_hashes = {
        "garment_sha256": _text(garment_sha256).lower(),
        "body_sha256": _text(body_sha256).lower(),
        "rig_sha256": _text(rig_sha256).lower(),
    }
    for label, digest in expected_hashes.items():
        require(_valid_sha256(digest), f"expected_{label}_invalid")
        require(_text(data.get(label)).lower() == digest, f"manifest_{label}_mismatch")

    require(_text(data.get("candidate_id")) == _text(candidate_id), "manifest_candidate_id_mismatch")
    require(_text(data.get("subject_id")) == _text(subject_id), "manifest_subject_id_mismatch")
    require(_normalized(data.get("capability_profile")) == "two_sleeve_tied_robe_v1", "unsupported_capability_profile")
    require(data.get("garment_is_separate_artifact") is True, "garment_not_proven_separate_from_body")
    require(data.get("skinned_to_exact_rig") is True, "garment_not_proven_skinned_to_exact_rig")
    require(data.get("clothing_baked_into_body") is False, "clothing_baked_into_body")
    require(data.get("capability_only_not_runtime_claim") is True, "manifest_must_be_capability_only")

    states = data.get("state_inventory")
    transitions = data.get("transition_inventory")
    state_set = {_normalized(value) for value in states} if isinstance(states, list) else set()
    transition_set = (
        {_normalized(value) for value in transitions}
        if isinstance(transitions, list)
        else set()
    )
    for state in REQUIRED_ROBE_STATES:
        require(state in state_set, f"required_state_missing_{state}")
    for transition in REQUIRED_ROBE_TRANSITIONS:
        require(transition in transition_set, f"required_transition_missing_{transition}")

    phase_evidence = data.get("phase_evidence")
    evidence_map = phase_evidence if isinstance(phase_evidence, Mapping) else {}
    item_instance_ids: set[str] = set()
    for phase_id in REQUIRED_ROBE_PHASES:
        record_value = evidence_map.get(phase_id)
        record = record_value if isinstance(record_value, Mapping) else {}
        prefix = f"phase_{phase_id}"
        require(bool(record), f"{prefix}_evidence_missing")
        require(_normalized(record.get("status")) in PASS_STATUSES, f"{prefix}_not_passed")
        require(_normalized(record.get("capture_basis")) in TRACE_BASES, f"{prefix}_capture_basis_not_physical")
        require(record.get("timer_only") is False, f"{prefix}_timer_only_forbidden")
        payload_value = record.get("evidence_payload")
        payload = payload_value if isinstance(payload_value, Mapping) else {}
        digest = canonical_sha256(payload)
        require(_valid_sha256(record.get("evidence_sha256")), f"{prefix}_evidence_sha256_invalid")
        require(_text(record.get("evidence_sha256")).lower() == digest, f"{prefix}_evidence_sha256_mismatch")
        require(_text(payload.get("phase_id")) == phase_id, f"{prefix}_payload_phase_mismatch")
        require(_text(payload.get("candidate_id")) == _text(candidate_id), f"{prefix}_candidate_mismatch")
        require(_text(payload.get("subject_id")) == _text(subject_id), f"{prefix}_subject_mismatch")
        require(_text(payload.get("garment_sha256")).lower() == expected_hashes["garment_sha256"], f"{prefix}_garment_hash_mismatch")
        require(_text(payload.get("body_sha256")).lower() == expected_hashes["body_sha256"], f"{prefix}_body_hash_mismatch")
        require(_text(payload.get("rig_sha256")).lower() == expected_hashes["rig_sha256"], f"{prefix}_rig_hash_mismatch")
        item_instance_id = _text(payload.get("item_instance_id"))
        require(bool(item_instance_id), f"{prefix}_item_instance_missing")
        if item_instance_id:
            item_instance_ids.add(item_instance_id)
        require(payload.get("same_item_continuity") is True, f"{prefix}_same_item_continuity_not_proven")
        require(payload.get("duplicate_active_representations") == 0, f"{prefix}_duplicate_representation_present")
        require(payload.get("physical_trace") is True, f"{prefix}_physical_trace_not_proven")
        require(_positive_int(payload.get("trace_frame_count"), 3), f"{prefix}_trace_frames_missing")
        require(payload.get("named_anchors_verified") is True, f"{prefix}_named_anchors_not_verified")
        failures.extend(_phase_specific_failures(phase_id, payload))

    require(
        len(item_instance_ids) == 1,
        "phase_item_instance_ids_not_identical",
    )

    failures = list(dict.fromkeys(failures))
    passed = not failures
    return {
        "schema_version": 1,
        "candidate_id": _text(candidate_id),
        "subject_id": _text(subject_id),
        "capability_profile": "two_sleeve_tied_robe_v1",
        "status": "capability_evidence_complete" if passed else "blocked",
        "capability_evidence_complete": passed,
        "review_stage_allowed": False,
        "runtime_activation_allowed": False,
        "caller_declarations_are_runtime_authority": False,
        "trusted_worker_rehash_required_before_mutation": True,
        "required_states": list(REQUIRED_ROBE_STATES),
        "required_transitions": list(REQUIRED_ROBE_TRANSITIONS),
        "failures": failures,
        "truth_note": (
            "A pass validates exact-hash capability evidence only. It does not run or prove a "
            "live cloth simulation, approve visual quality, authorize a wearable, or activate runtime use."
        ),
    }
