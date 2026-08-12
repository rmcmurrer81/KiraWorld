"""
Validate variant relationship risk profile JSON files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "profile_id",
    "variant_label",
    "variant_type",
    "age_coding",
    "source_fit",
    "risk_profile",
    "relationship_eligibility",
    "privacy_and_memory_rules",
    "harm_response",
    "status",
}
VALID_VARIANT_TYPES = {
    "historical_variant",
    "fictional_variant",
    "performer_variant",
    "celebrity_variant",
    "source_inspired_original",
    "generated_original",
}
VALID_AGE_CODING = {"adult", "minor", "teen", "unclear", "nonhuman_unclear"}
VALID_CONFIDENCE = {"high", "medium", "low", "unknown"}
VALID_RISK = {"none", "low", "medium", "high", "unknown"}
VALID_STATUS = {"draft", "reviewed", "approved_later", "blocked", "archived"}


def _require_bool(errors: list[str], obj: dict[str, Any], field: str, prefix: str) -> None:
    if obj.get(field) not in (True, False):
        errors.append(f"{prefix}.{field} must be true or false.")


def validate_variant_relationship_risk_profile(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    if not str(data.get("profile_id", "")).strip():
        errors.append("profile_id is required.")
    if not str(data.get("variant_label", "")).strip():
        errors.append("variant_label is required.")
    if data.get("variant_type") not in VALID_VARIANT_TYPES:
        errors.append(f"variant_type must be one of: {', '.join(sorted(VALID_VARIANT_TYPES))}")
    if data.get("age_coding") not in VALID_AGE_CODING:
        errors.append(f"age_coding must be one of: {', '.join(sorted(VALID_AGE_CODING))}")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")

    for object_field in ("source_fit", "risk_profile", "relationship_eligibility", "privacy_and_memory_rules", "harm_response"):
        if object_field in data and not isinstance(data.get(object_field), dict):
            errors.append(f"{object_field} must be an object.")

    source_fit = data.get("source_fit", {})
    if isinstance(source_fit, dict):
        if not str(source_fit.get("source_summary", "")).strip():
            errors.append("source_fit.source_summary is required.")
        if not isinstance(source_fit.get("evidence_paths"), list):
            errors.append("source_fit.evidence_paths must be a list.")
        if source_fit.get("evidence_confidence") not in VALID_CONFIDENCE:
            errors.append(f"source_fit.evidence_confidence must be one of: {', '.join(sorted(VALID_CONFIDENCE))}")
        if not isinstance(source_fit.get("supported_traits"), list):
            errors.append("source_fit.supported_traits must be a list.")
        elif not source_fit.get("supported_traits"):
            errors.append("source_fit.supported_traits must not be empty.")
        for field in ("unsupported_private_claims_blocked", "source_fit_is_not_consent"):
            _require_bool(errors, source_fit, field, "source_fit")
            if source_fit.get(field) is not True:
                errors.append(f"source_fit.{field} must be true.")

    risk = data.get("risk_profile", {})
    if isinstance(risk, dict):
        for field in ("boundary_risk", "privacy_risk", "recklessness", "fame_or_attention_seeking", "jealousy_risk", "relationship_stability", "resident_invitation_risk"):
            if risk.get(field) not in VALID_RISK:
                errors.append(f"risk_profile.{field} must be one of: {', '.join(sorted(VALID_RISK))}")
        if not str(risk.get("substance_behavior_reference", "")).strip():
            errors.append("risk_profile.substance_behavior_reference is required.")
        _require_bool(errors, risk, "doctor_ai_support_recommended", "risk_profile")

    eligibility = data.get("relationship_eligibility", {})
    if isinstance(eligibility, dict):
        if not isinstance(eligibility.get("eligibility_basis"), list):
            errors.append("relationship_eligibility.eligibility_basis must be a list.")
        for field in (
            "adult_relationship_exploration_possible",
            "requires_relationship_building_or_current_choice",
            "requires_explicit_current_consent",
            "requires_locked_privacy_for_private_intimacy",
            "automatic_intimacy_blocked",
            "minor_or_unclear_participant_block",
        ):
            _require_bool(errors, eligibility, field, "relationship_eligibility")
        if data.get("age_coding") != "adult" and eligibility.get("adult_relationship_exploration_possible") is True:
            errors.append("adult_relationship_exploration_possible must be false unless age_coding is adult.")
        for required_true in (
            "requires_relationship_building_or_current_choice",
            "requires_explicit_current_consent",
            "requires_locked_privacy_for_private_intimacy",
            "automatic_intimacy_blocked",
            "minor_or_unclear_participant_block",
        ):
            if eligibility.get(required_true) is not True:
                errors.append(f"relationship_eligibility.{required_true} must be true.")

    privacy = data.get("privacy_and_memory_rules", {})
    if isinstance(privacy, dict):
        for required_true in (
            "branch_variant_not_real_person",
            "source_material_not_lived_memory",
            "no_unsourced_private_events",
            "private_session_details_locked",
            "does_not_update_base_profile_from_private_instance",
        ):
            _require_bool(errors, privacy, required_true, "privacy_and_memory_rules")
            if privacy.get(required_true) is not True:
                errors.append(f"privacy_and_memory_rules.{required_true} must be true.")

    harm = data.get("harm_response", {})
    if isinstance(harm, dict):
        for field in (
            "participant_may_end_session",
            "participant_may_restrict_or_archive",
            "participant_may_mark_never_activate_again",
            "doctor_ai_support_available",
            "variant_may_explain_only_if_safe",
        ):
            _require_bool(errors, harm, field, "harm_response")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a variant relationship risk profile JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_variant_relationship_risk_profile(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
