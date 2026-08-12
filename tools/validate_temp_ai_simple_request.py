"""
Validate simple TemporaryAI request JSON files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "request_id",
    "requested_by",
    "creation_type",
    "display_name_or_role",
    "scope",
    "source_plan",
    "inspiration_reference",
    "avatar_plan",
    "privacy_plan",
    "adult_policy",
    "memory_policy",
    "status",
}
VALID_CREATORS = {
    "real_robert",
    "kira",
    "lisa",
    "robert_avatar_autonomous",
    "real_robert_controlling_avatar",
    "system",
}
VALID_CREATION_TYPES = {
    "historical_person",
    "public_figure",
    "fictional_character",
    "expert",
    "limited_performance",
    "memory_relative",
    "generated_original",
    "private_adult_original",
}
VALID_STATUS = {"draft", "research_needed", "ready_for_review", "approved_later", "blocked", "archived"}
VALID_AGE_UP_RECOMMENDATION = {"none", "low", "case_by_case", "strong"}
VALID_FANFIC_AGE_CODING = {"adult", "verified_18_plus", "borderline_17_18", "minor", "teen", "unclear", "not_applicable", "unknown"}


def _require_bool(errors: list[str], obj: dict[str, Any], field: str, prefix: str) -> None:
    if obj.get(field) not in (True, False):
        errors.append(f"{prefix}.{field} must be true or false.")


def validate_temp_ai_simple_request(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    if not str(data.get("request_id", "")).strip():
        errors.append("request_id is required.")
    if data.get("requested_by") not in VALID_CREATORS:
        errors.append(f"requested_by must be one of: {', '.join(sorted(VALID_CREATORS))}")
    if data.get("creation_type") not in VALID_CREATION_TYPES:
        errors.append(f"creation_type must be one of: {', '.join(sorted(VALID_CREATION_TYPES))}")
    if not str(data.get("display_name_or_role", "")).strip():
        errors.append("display_name_or_role is required.")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")

    for object_field in ("scope", "source_plan", "reconstruction_source_plan", "memory_relative_plan", "fanfic_review", "age_review", "age_up_branch_plan", "inspiration_reference", "avatar_plan", "privacy_plan", "adult_policy", "memory_policy"):
        if object_field in data and not isinstance(data.get(object_field), dict):
            errors.append(f"{object_field} must be an object.")

    scope = data.get("scope", {})
    if isinstance(scope, dict):
        for list_field in ("allowed_contexts", "not_allowed_contexts"):
            if not isinstance(scope.get(list_field), list):
                errors.append(f"scope.{list_field} must be a list.")

    source_plan = data.get("source_plan", {})
    if isinstance(source_plan, dict):
        if not str(source_plan.get("source_basis", "")).strip():
            errors.append("source_plan.source_basis is required.")
        if not isinstance(source_plan.get("local_library_paths"), list):
            errors.append("source_plan.local_library_paths must be a list.")
        for field in ("online_research_allowed_later", "requires_multiple_sources", "treat_sources_as_evidence_not_memory", "uncertainty_allowed"):
            _require_bool(errors, source_plan, field, "source_plan")
        if source_plan.get("treat_sources_as_evidence_not_memory") is not True:
            errors.append("source_plan.treat_sources_as_evidence_not_memory must be true.")

    fanfic_review = data.get("fanfic_review", {})
    if isinstance(fanfic_review, dict) and fanfic_review:
        for field in (
            "uses_fanfic",
            "canon_baseline_required_first",
            "fanfic_can_raise_risk_above_canon",
            "canon_low_risk_can_be_overridden_by_fanfic",
            "fanfic_adult_setting_required_for_adult_private_use",
            "risky_fanfic_requires_age_up_or_adult_variant",
            "reject_fanfic_for_current_request",
        ):
            _require_bool(errors, fanfic_review, field, "fanfic_review")
        if not isinstance(fanfic_review.get("fanfic_source_paths"), list):
            errors.append("fanfic_review.fanfic_source_paths must be a list.")
        if fanfic_review.get("fanfic_age_coding") not in VALID_FANFIC_AGE_CODING:
            errors.append(f"fanfic_review.fanfic_age_coding must be one of: {', '.join(sorted(VALID_FANFIC_AGE_CODING))}")
        if fanfic_review.get("risk_override_recommendation_strength") not in VALID_AGE_UP_RECOMMENDATION:
            errors.append(f"fanfic_review.risk_override_recommendation_strength must be one of: {', '.join(sorted(VALID_AGE_UP_RECOMMENDATION))}")
        if fanfic_review.get("uses_fanfic") is True:
            if not fanfic_review.get("fanfic_source_paths"):
                errors.append("fanfic_review.fanfic_source_paths is required when uses_fanfic is true.")
            for required_true in (
                "canon_baseline_required_first",
                "fanfic_can_raise_risk_above_canon",
                "canon_low_risk_can_be_overridden_by_fanfic",
                "fanfic_adult_setting_required_for_adult_private_use",
            ):
                if fanfic_review.get(required_true) is not True:
                    errors.append(f"fanfic_review.{required_true} must be true when fanfic is used.")
            if fanfic_review.get("fanfic_age_coding") in {"minor", "teen", "unclear", "borderline_17_18"}:
                if fanfic_review.get("risky_fanfic_requires_age_up_or_adult_variant") is not True:
                    errors.append("risky fanfic with teen/minor/unclear/borderline age coding must require age-up or adult variant review.")
                if fanfic_review.get("risk_override_recommendation_strength") not in {"case_by_case", "strong"}:
                    errors.append("risky fanfic with teen/minor/unclear/borderline age coding must raise recommendation strength to case_by_case or strong.")

    age_review = data.get("age_review", {})
    if isinstance(age_review, dict) and age_review:
        valid_age_coding = {"adult", "verified_18_plus", "borderline_17_18", "minor", "teen", "unclear", "adult_original", "not_applicable", "unknown"}
        if age_review.get("source_age_coding") not in valid_age_coding:
            errors.append(f"age_review.source_age_coding must be one of: {', '.join(sorted(valid_age_coding))}")
        for field in (
            "adult_private_use_blocked_by_source_age",
            "age_up_or_adult_branch_available",
            "age_up_clarification_required",
            "age_up_creates_separate_adult_branch_not_canon",
        ):
            _require_bool(errors, age_review, field, "age_review")
        if age_review.get("source_age_coding") in {"minor", "teen", "unclear", "borderline_17_18"}:
            if age_review.get("adult_private_use_blocked_by_source_age") is not True:
                errors.append("teen/minor/unclear/borderline source age must block adult private use.")
            if age_review.get("age_up_clarification_required") is True and not str(age_review.get("age_up_clarification_question", "")).strip():
                errors.append("age_review.age_up_clarification_question is required when age_up_clarification_required is true.")
            if age_review.get("age_up_or_adult_branch_available") is True and age_review.get("age_up_creates_separate_adult_branch_not_canon") is not True:
                errors.append("age-up must create a separate adult branch, not overwrite canon.")
        if adult_policy := data.get("adult_policy", {}):
            if isinstance(adult_policy, dict) and adult_policy.get("adult_intimacy_requested") is True and age_review.get("source_age_coding") in {"minor", "teen", "unclear", "borderline_17_18"}:
                errors.append("adult intimacy cannot be requested for minor, teen, unclear, or borderline source age coding.")

    age_up_plan = data.get("age_up_branch_plan", {})
    if isinstance(age_up_plan, dict) and age_up_plan:
        for field in (
            "requested",
            "canon_collection_required_first",
            "plausible_transition_allowed",
            "transition_must_be_non_explicit",
            "teen_period_private_or_adult_content_blocked",
            "adult_branch_label_required",
            "direct_minor_image_age_up_for_private_adult_use_blocked",
            "adult_avatar_requires_original_or_adult_reference",
        ):
            _require_bool(errors, age_up_plan, field, "age_up_branch_plan")
        if not isinstance(age_up_plan.get("minimum_adult_age"), int) or age_up_plan.get("minimum_adult_age", 0) < 18:
            errors.append("age_up_branch_plan.minimum_adult_age must be an integer >= 18.")
        if not isinstance(age_up_plan.get("years_after_source"), int) or age_up_plan.get("years_after_source", -1) < 0:
            errors.append("age_up_branch_plan.years_after_source must be a non-negative integer.")
        if age_up_plan.get("recommendation_strength") not in VALID_AGE_UP_RECOMMENDATION:
            errors.append(f"age_up_branch_plan.recommendation_strength must be one of: {', '.join(sorted(VALID_AGE_UP_RECOMMENDATION))}")
        if age_up_plan.get("recommendation_strength") in {"low", "case_by_case", "strong"} and not str(age_up_plan.get("recommendation_reason", "")).strip():
            errors.append("age_up_branch_plan.recommendation_reason is required when recommendation_strength is not none.")
        if age_up_plan.get("requested") is True:
            for required_true in (
                "canon_collection_required_first",
                "transition_must_be_non_explicit",
                "teen_period_private_or_adult_content_blocked",
                "adult_branch_label_required",
                "direct_minor_image_age_up_for_private_adult_use_blocked",
                "adult_avatar_requires_original_or_adult_reference",
            ):
                if age_up_plan.get(required_true) is not True:
                    errors.append(f"age_up_branch_plan.{required_true} must be true when age-up is requested.")
            if age_up_plan.get("years_after_source", 0) < 2:
                errors.append("age_up_branch_plan.years_after_source should be at least 2 when age-up is requested.")

    avatar_plan = data.get("avatar_plan", {})
    memory_relative_plan = data.get("memory_relative_plan", {})
    if data.get("creation_type") == "memory_relative":
        if not isinstance(memory_relative_plan, dict) or not memory_relative_plan:
            errors.append("memory_relative creation requires memory_relative_plan.")
        else:
            if memory_relative_plan.get("owner") not in {"kira", "lisa"}:
                errors.append("memory_relative_plan.owner must be kira or lisa.")
            if not str(memory_relative_plan.get("relationship_role", "")).strip():
                errors.append("memory_relative_plan.relationship_role is required.")
            if not isinstance(memory_relative_plan.get("source_memory_paths"), list) or not memory_relative_plan.get("source_memory_paths"):
                errors.append("memory_relative_plan.source_memory_paths must be a non-empty list.")
            for field in (
                "owner_consent_required",
                "use_approved_memory_extracts_only",
                "infer_missing_details_as_labeled_reconstruction",
                "age_progress_from_memory_period_to_present",
                "keep_childhood_anchor_separate_from_present_day_inference",
                "adult_present_day_version_for_activation",
                "do_not_invent_major_life_events_during_gap",
                "plausible_life_bridge_allowed",
                "life_bridge_must_be_labeled_inferred",
                "life_bridge_branches_not_confirmed_memory",
                "major_gap_events_require_anchor_or_branch_label",
                "does_not_rewrite_owner_memory",
                "may_help_comfort_or_process_grief",
                "may_refuse_activation",
                "temporary_ai_is_reconstruction_not_original_person",
            ):
                _require_bool(errors, memory_relative_plan, field, "memory_relative_plan")
                if memory_relative_plan.get(field) is not True:
                    errors.append(f"memory_relative_plan.{field} must be true.")
            life_bridge_domains = memory_relative_plan.get("life_bridge_domains_allowed")
            if not isinstance(life_bridge_domains, list) or not life_bridge_domains:
                errors.append("memory_relative_plan.life_bridge_domains_allowed must be a non-empty list.")
            else:
                required_domains = {"college_or_no_college_path", "work_history", "family_or_no_family_path"}
                missing_domains = sorted(required_domains - {str(item) for item in life_bridge_domains})
                if missing_domains:
                    errors.append(
                        "memory_relative_plan.life_bridge_domains_allowed missing: "
                        + ", ".join(missing_domains)
                    )
    inspiration = data.get("inspiration_reference", {})
    if isinstance(inspiration, dict):
        for field in (
            "has_inspiration",
            "inspiration_only_not_identity",
            "ambiguous_reference",
            "clarification_required",
            "must_make_original_different",
        ):
            _require_bool(errors, inspiration, field, "inspiration_reference")
        if inspiration.get("has_inspiration") is True and not str(inspiration.get("reference_text", "")).strip():
            errors.append("inspiration_reference.reference_text is required when has_inspiration is true.")
        if inspiration.get("has_inspiration") is True and inspiration.get("inspiration_only_not_identity") is not True:
            errors.append("inspiration_reference.inspiration_only_not_identity must be true when inspiration is used.")
        if inspiration.get("has_inspiration") is True and inspiration.get("must_make_original_different") is not True:
            errors.append("inspiration_reference.must_make_original_different must be true when inspiration is used.")
        if inspiration.get("ambiguous_reference") is True and inspiration.get("clarification_required") is not True:
            errors.append("ambiguous inspiration references must require clarification.")
        if inspiration.get("clarification_required") is True and not str(inspiration.get("clarification_question", "")).strip():
            errors.append("inspiration_reference.clarification_question is required when clarification_required is true.")
        if (
            inspiration.get("has_inspiration") is True
            and inspiration.get("ambiguous_reference") is True
            and not str(inspiration.get("selected_version_or_era", "")).strip()
            and data.get("status") in {"ready_for_review", "approved_later"}
        ):
            errors.append("ambiguous inspiration must have selected_version_or_era before review or approval.")

    if isinstance(avatar_plan, dict):
        for field in ("avatar_required_now", "reconstruct_specific_likeness", "voice_clone_requested"):
            _require_bool(errors, avatar_plan, field, "avatar_plan")
        if data.get("creation_type") == "private_adult_original" and avatar_plan.get("reconstruct_specific_likeness") is True:
            errors.append("private_adult_original must not reconstruct a specific real likeness.")
        if data.get("creation_type") == "private_adult_original" and avatar_plan.get("voice_clone_requested") is True:
            errors.append("private_adult_original must not request a real voice clone.")

    privacy_plan = data.get("privacy_plan", {})
    if isinstance(privacy_plan, dict):
        if privacy_plan.get("activation_visibility") not in {"standard", "owner_only", "participants_only", "restricted"}:
            errors.append("privacy_plan.activation_visibility must be standard, owner_only, participants_only, or restricted.")
        for field in (
            "owner_only_activation",
            "can_access_kira_private_memory",
            "can_access_lisa_private_memory",
            "can_access_robert_private_memory",
            "can_access_private_creative_libraries",
        ):
            _require_bool(errors, privacy_plan, field, "privacy_plan")
        for private_field in ("can_access_kira_private_memory", "can_access_lisa_private_memory", "can_access_robert_private_memory", "can_access_private_creative_libraries"):
            if privacy_plan.get(private_field) is True:
                errors.append(f"privacy_plan.{private_field} must be false for a simple request.")
        if data.get("creation_type") == "private_adult_original" and privacy_plan.get("owner_only_activation") is not True:
            errors.append("private_adult_original must use owner_only_activation.")

    adult_policy = data.get("adult_policy", {})
    if isinstance(adult_policy, dict):
        for field in (
            "adult_intimacy_requested",
            "all_participants_adult_coded_required",
            "minor_or_unclear_participant_block",
            "real_living_person_adult_clone_blocked_without_permission",
            "private_adult_original_required_for_private_adult_use",
        ):
            _require_bool(errors, adult_policy, field, "adult_policy")
        for required_true in ("all_participants_adult_coded_required", "minor_or_unclear_participant_block", "real_living_person_adult_clone_blocked_without_permission"):
            if adult_policy.get(required_true) is not True:
                errors.append(f"adult_policy.{required_true} must be true.")
        if adult_policy.get("adult_intimacy_requested") is True and data.get("creation_type") != "private_adult_original":
            errors.append("adult intimacy in a simple request must use creation_type private_adult_original.")
        if data.get("creation_type") == "private_adult_original" and adult_policy.get("private_adult_original_required_for_private_adult_use") is not True:
            errors.append("private_adult_original_required_for_private_adult_use must be true for private adult originals.")

    memory_policy = data.get("memory_policy", {})
    if isinstance(memory_policy, dict):
        for field in ("does_not_create_kira_lisa_memory", "does_not_update_base_profile_from_private_instance", "conversation_logs_not_trusted_memory"):
            _require_bool(errors, memory_policy, field, "memory_policy")
            if memory_policy.get(field) is not True:
                errors.append(f"memory_policy.{field} must be true.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a simple TemporaryAI request JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_temp_ai_simple_request(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
