"""Fail-closed contract for separate, size-compatible wearable components.

This module does not author clothing, simulate cloth, transfer an inventory
item, approve a garment, or activate an avatar.  It evaluates whether one
unchanged garment artifact has enough exact evidence to enter a *private
staged review* for a particular body.  A familiar size label is never proof:
measurements, maturity lane, target body/rig binding, deformation, penetration,
put-on, take-off, and transfer evidence must all agree.

The existing garment runtime remains the authority for the single physical
item instance and its owner/location state.  A per-target binding is an adapter
for the same garment asset; it must not clone the item or bake its surface into
the wearer's body.
"""

from __future__ import annotations

import math
import re
from typing import Any, Iterable


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SUPPORTED_MATURITY_CLASSES = frozenset({"adult", "non_adult_doll_safe"})
REQUIRED_LIFECYCLE_CAPABILITIES = frozenset(
    {
        "stored",
        "grasped",
        "put_on",
        "worn",
        "take_off",
        "released",
        "transferred_between_people",
    }
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _hash(value: Any) -> str:
    return _text(value).lower()


def _valid_hash(value: Any) -> bool:
    return bool(SHA256_RE.fullmatch(_hash(value)))


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _unique_text(values: Any) -> set[str]:
    if not isinstance(values, (list, tuple, set)):
        return set()
    return {_text(value) for value in values if _text(value)}


def _maturity_lane(value: Any) -> str:
    maturity_class = _text(value)
    if maturity_class == "adult":
        return "adult"
    if maturity_class == "non_adult_doll_safe":
        return "non_adult_doll_safe"
    return ""


def _find_target_binding(
    bindings: Any,
    *,
    subject_id: str,
    body_sha256: str,
    rig_sha256: str,
    garment_sha256: str,
) -> dict[str, Any] | None:
    if not isinstance(bindings, list):
        return None
    matches: list[dict[str, Any]] = []
    for raw in bindings:
        if not isinstance(raw, dict):
            continue
        if (
            _text(raw.get("subject_id")) == subject_id
            and _hash(raw.get("body_sha256")) == body_sha256
            and _hash(raw.get("rig_sha256")) == rig_sha256
            and _hash(raw.get("garment_sha256")) == garment_sha256
        ):
            matches.append(raw)
    return matches[0] if len(matches) == 1 else None


def _measurement_failures(
    envelope: Any,
    measurements: Any,
) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    matched: list[str] = []
    if not isinstance(envelope, dict) or not envelope:
        return ["measurement_envelope_missing"], matched
    if not isinstance(measurements, dict):
        return ["target_measurements_missing"], matched

    for name, raw_bounds in envelope.items():
        measurement_name = _text(name)
        if not measurement_name or not isinstance(raw_bounds, dict):
            failures.append("measurement_envelope_malformed")
            continue
        low = raw_bounds.get("minimum_m")
        high = raw_bounds.get("maximum_m")
        target_value = measurements.get(measurement_name)
        if not _finite_number(low) or not _finite_number(high):
            failures.append(f"measurement_bounds_invalid:{measurement_name}")
            continue
        low_value = float(low)
        high_value = float(high)
        if low_value <= 0 or high_value <= 0 or low_value > high_value:
            failures.append(f"measurement_bounds_invalid:{measurement_name}")
            continue
        if not _finite_number(target_value) or float(target_value) <= 0:
            failures.append(f"target_measurement_missing_or_invalid:{measurement_name}")
            continue
        if not low_value <= float(target_value) <= high_value:
            failures.append(f"target_outside_measurement_envelope:{measurement_name}")
            continue
        matched.append(measurement_name)
    return failures, matched


def evaluate_shareable_wearable_component(
    manifest: dict[str, Any] | None,
    target_body: dict[str, Any] | None,
) -> dict[str, Any]:
    """Evaluate one garment/target pair without authorizing runtime use.

    A passing decision means only that the exact garment may proceed to a
    private target-wearer review.  It cannot release Avatar Builder auto-build,
    approve public export, or make a runtime inventory transfer.
    """

    data = manifest if isinstance(manifest, dict) else {}
    target = target_body if isinstance(target_body, dict) else {}
    failures: list[str] = []

    def require(condition: bool, reason: str) -> None:
        if not condition:
            failures.append(reason)

    require(data.get("schema_version") == 1, "unsupported_or_missing_schema_version")
    component_id = _text(data.get("component_id"))
    require(bool(component_id), "component_id_missing")

    artifact = data.get("component_artifact")
    if not isinstance(artifact, dict):
        artifact = {}
        failures.append("component_artifact_missing")
    garment_sha256 = _hash(artifact.get("sha256"))
    require(
        _text(artifact.get("artifact_type")) == "separate_wearable_component",
        "artifact_not_declared_separate_wearable_component",
    )
    require(_valid_hash(garment_sha256), "garment_sha256_invalid")
    require(artifact.get("separate_from_body") is True, "garment_not_separate_from_body")
    require(artifact.get("clothing_baked_into_body") is False, "clothing_baked_into_body")
    require(artifact.get("contains_body_surface_copy") is False, "garment_contains_body_surface_copy")

    maturity_class = _text(data.get("maturity_class"))
    target_maturity = _text(target.get("maturity_class"))
    garment_maturity_lane = _maturity_lane(maturity_class)
    target_maturity_lane = _maturity_lane(target_maturity)
    require(maturity_class in SUPPORTED_MATURITY_CLASSES, "garment_maturity_class_invalid")
    require(target_maturity in SUPPORTED_MATURITY_CLASSES, "target_maturity_class_invalid")
    require(
        bool(garment_maturity_lane)
        and garment_maturity_lane == target_maturity_lane,
        "garment_and_target_maturity_lane_mismatch",
    )

    size_profile = data.get("size_profile")
    if not isinstance(size_profile, dict):
        size_profile = {}
        failures.append("size_profile_missing")
    require(
        _text(size_profile.get("scheme")) == "body_measurement_envelope_v1",
        "unsupported_size_profile_scheme",
    )
    require(_text(size_profile.get("measurement_unit")) == "metre", "measurement_unit_must_be_metre")
    require(bool(_text(size_profile.get("size_label"))), "size_label_missing")
    require(size_profile.get("ease_allowance_reviewed") is True, "ease_allowance_not_reviewed")
    measurement_failures, matched_measurements = _measurement_failures(
        size_profile.get("measurement_envelope"),
        target.get("measurements_m"),
    )
    failures.extend(measurement_failures)

    share = data.get("share_policy")
    if not isinstance(share, dict):
        share = {}
        failures.append("share_policy_missing")
    require(share.get("same_size_sharing_allowed") is True, "same_size_sharing_not_enabled")
    require(share.get("single_physical_instance") is True, "single_physical_instance_not_required")
    require(share.get("clone_on_transfer_allowed") is False, "clone_on_transfer_allowed")
    require(share.get("owner_consent_required") is True, "owner_consent_not_required")
    require(share.get("wearer_consent_required") is True, "wearer_consent_not_required")
    require(share.get("transfer_record_required") is True, "transfer_record_not_required")
    require(
        share.get("size_label_alone_counts_as_fit_proof") is False,
        "size_label_alone_incorrectly_counts_as_fit_proof",
    )

    lifecycle = data.get("lifecycle_contract")
    if not isinstance(lifecycle, dict):
        lifecycle = {}
        failures.append("lifecycle_contract_missing")
    capabilities = _unique_text(lifecycle.get("capabilities"))
    for capability in sorted(REQUIRED_LIFECYCLE_CAPABILITIES - capabilities):
        failures.append(f"lifecycle_capability_missing:{capability}")
    require(lifecycle.get("physical_transition_evidence_required") is True, "physical_transition_evidence_not_required")
    require(lifecycle.get("timer_or_state_name_only_counts_as_proof") is False, "timer_or_state_name_allowed_as_proof")
    require(lifecycle.get("put_on_evidence_reviewed") is True, "put_on_evidence_not_reviewed")
    require(lifecycle.get("take_off_evidence_reviewed") is True, "take_off_evidence_not_reviewed")
    require(lifecycle.get("transfer_evidence_reviewed") is True, "transfer_evidence_not_reviewed")

    subject_id = _text(target.get("subject_id"))
    body_sha256 = _hash(target.get("body_sha256"))
    rig_sha256 = _hash(target.get("rig_sha256"))
    require(bool(subject_id), "target_subject_id_missing")
    require(_valid_hash(body_sha256), "target_body_sha256_invalid")
    require(_valid_hash(rig_sha256), "target_rig_sha256_invalid")

    binding = _find_target_binding(
        data.get("target_bindings"),
        subject_id=subject_id,
        body_sha256=body_sha256,
        rig_sha256=rig_sha256,
        garment_sha256=garment_sha256,
    )
    require(binding is not None, "exact_target_body_rig_garment_binding_missing_or_ambiguous")
    if binding is not None:
        require(_valid_hash(binding.get("binding_sha256")), "target_binding_sha256_invalid")
        require(_valid_hash(binding.get("fit_evidence_sha256")), "fit_evidence_sha256_invalid")
        require(binding.get("measurement_fit_reviewed") is True, "target_measurement_fit_not_reviewed")
        require(binding.get("deformation_reviewed") is True, "target_deformation_not_reviewed")
        require(binding.get("penetration_reviewed") is True, "target_penetration_not_reviewed")
        require(binding.get("put_on_take_off_reviewed") is True, "target_put_on_take_off_not_reviewed")
        require(binding.get("owner_visual_reviewed") is True, "target_owner_visual_review_missing")
        require(binding.get("runtime_activation_approved") is False, "binding_must_not_self_approve_runtime")

    failures = list(dict.fromkeys(failures))
    compatible = not failures
    return {
        "schema_version": 1,
        "component_id": component_id,
        "target_subject_id": subject_id,
        "garment_sha256": garment_sha256,
        "size_label": _text(size_profile.get("size_label")),
        "matched_measurements": sorted(matched_measurements),
        "contract_compatible_for_private_share_fit_review": compatible,
        "status": "compatible_for_private_share_fit_review" if compatible else "blocked",
        "runtime_transfer_allowed": False,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
        "positive_proof_autobuild_released": False,
        "failures": failures,
        "truth_note": (
            "A compatible result proves only a hash-bound private fit-review contract for "
            "one target. It does not author a garment, prove cloth simulation, transfer the "
            "single inventory item, approve runtime use, or release Avatar Builder auto-build."
        ),
    }


def required_lifecycle_capabilities() -> Iterable[str]:
    """Expose a stable ordered view for UI/policy consumers."""

    return tuple(sorted(REQUIRED_LIFECYCLE_CAPABILITIES))
