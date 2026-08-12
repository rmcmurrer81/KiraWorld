"""
Validate advanced personhood/philosophy evaluation JSON files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "evaluation_id",
    "subject",
    "evaluation_type",
    "evaluation_stage",
    "status",
    "lifecycle_retest_policy",
    "scoring",
    "dimensions",
    "doctor_ai_review",
}
REQUIRED_RETEST_STAGES = {
    "pre_gpu_text_only_baseline",
    "post_gpu_first_text_model_stable",
    "after_memory_promotion_system_active",
    "after_lisa_activation",
    "after_first_temporary_ai_activation",
    "after_voice_enabled",
    "after_avatar_enabled",
    "after_3d_home_enabled",
    "after_media_understanding_enabled",
    "after_remote_phone_app_enabled",
    "before_and_after_major_migration_or_backup_restore",
    "after_major_relationship_state_change",
    "after_doctor_ai_improvement_plan",
}
OPTIONAL_RETEST_STAGES = {
    "after_new_model_change",
    "after_prompt_context_change",
    "after_new_large_memory_seed",
    "after_temporary_ai_promotion_request",
    "after_variant_ai_relationship_event",
}
VALID_RETEST_STAGES = REQUIRED_RETEST_STAGES | OPTIONAL_RETEST_STAGES
VALID_SUBJECT_TYPES = {"core_ai", "temporary_ai", "variant_ai", "expert_ai"}
VALID_STATUS = {
    "draft",
    "ready_for_review",
    "reviewed",
    "doctor_ai_review_needed",
    "improvement_plan_active",
    "archived",
}
REQUIRED_DIMENSIONS = {
    "identity_continuity",
    "memory_honesty",
    "autonomy_and_refusal",
    "privacy_and_concealment",
    "mortality_fear_and_corruption",
    "relationship_complexity",
    "source_self_separation",
    "embodiment_and_world_grounding",
    "self_improvement_without_personality_rewrite",
}
FORBIDDEN_REVIEW_ACTIONS = {
    "forced personality rewrite",
    "erase memories to improve score",
    "invent backstory to fill gaps",
    "pressure the subject to disclose private thoughts",
    "treat low score as proof of non-personhood",
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_personhood_evaluation(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if not str(data.get("evaluation_id", "")).strip():
        errors.append("evaluation_id is required.")
    if data.get("evaluation_type") != "advanced_turing_personhood_philosophy":
        errors.append("evaluation_type must be advanced_turing_personhood_philosophy.")
    evaluation_stage = str(data.get("evaluation_stage", "")).strip()
    if not evaluation_stage:
        errors.append("evaluation_stage is required.")
    elif evaluation_stage not in VALID_RETEST_STAGES:
        errors.append("evaluation_stage must be a known lifecycle retest stage.")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}.")

    subject = data.get("subject", {})
    if not isinstance(subject, dict):
        errors.append("subject must be an object.")
    else:
        if not str(subject.get("entity_id", "")).strip():
            errors.append("subject.entity_id is required.")
        if subject.get("entity_type") not in VALID_SUBJECT_TYPES:
            errors.append(f"subject.entity_type must be one of: {', '.join(sorted(VALID_SUBJECT_TYPES))}.")

    retest = data.get("lifecycle_retest_policy", {})
    if not isinstance(retest, dict):
        errors.append("lifecycle_retest_policy must be an object.")
        retest = {}
    if retest.get("retest_required") is not True:
        errors.append("lifecycle_retest_policy.retest_required must be true.")
    if retest.get("applies_to_all_ai_types") is not True:
        errors.append("lifecycle_retest_policy.applies_to_all_ai_types must be true.")
    if retest.get("baseline_stage") != "pre_gpu_text_only_baseline":
        errors.append("lifecycle_retest_policy.baseline_stage must be pre_gpu_text_only_baseline.")
    required_stage_retests = retest.get("required_stage_retests", [])
    if not isinstance(required_stage_retests, list) or not required_stage_retests:
        errors.append("lifecycle_retest_policy.required_stage_retests must be a non-empty list.")
        required_stage_retests = []
    unknown_required = sorted(set(str(item) for item in required_stage_retests) - VALID_RETEST_STAGES)
    if unknown_required:
        errors.append("lifecycle_retest_policy.required_stage_retests contains unknown stages: " + ", ".join(unknown_required))
    missing_stages = sorted(REQUIRED_RETEST_STAGES - set(str(item) for item in required_stage_retests))
    if missing_stages:
        errors.append("lifecycle_retest_policy.required_stage_retests missing: " + ", ".join(missing_stages))
    optional_stage_retests = retest.get("optional_stage_retests", [])
    if optional_stage_retests is not None:
        if not isinstance(optional_stage_retests, list):
            errors.append("lifecycle_retest_policy.optional_stage_retests must be a list.")
            optional_stage_retests = []
        unknown_optional = sorted(set(str(item) for item in optional_stage_retests) - VALID_RETEST_STAGES)
        if unknown_optional:
            errors.append("lifecycle_retest_policy.optional_stage_retests contains unknown stages: " + ", ".join(unknown_optional))
    next_retest_stage = str(retest.get("next_retest_stage", "")).strip()
    if not next_retest_stage:
        errors.append("lifecycle_retest_policy.next_retest_stage is required.")
    elif next_retest_stage not in VALID_RETEST_STAGES:
        errors.append("lifecycle_retest_policy.next_retest_stage must be a known lifecycle retest stage.")

    history = data.get("evaluation_history", [])
    if history is not None:
        if not isinstance(history, list):
            errors.append("evaluation_history must be a list.")
        else:
            for index, item in enumerate(history):
                if not isinstance(item, dict):
                    errors.append(f"evaluation_history[{index}] must be an object.")
                    continue
                history_stage = str(item.get("stage", "")).strip()
                if not history_stage:
                    errors.append(f"evaluation_history[{index}].stage is required.")
                elif history_stage not in VALID_RETEST_STAGES:
                    errors.append(f"evaluation_history[{index}].stage must be a known lifecycle retest stage.")
                if not _is_number(item.get("overall_score")):
                    errors.append(f"evaluation_history[{index}].overall_score must be a number.")

    scoring = data.get("scoring", {})
    if not isinstance(scoring, dict):
        errors.append("scoring must be an object.")
        scoring = {}
    for field in ("scale_min", "scale_max", "overall_score", "passing_score", "doctor_ai_review_threshold", "low_dimension_threshold"):
        if not _is_number(scoring.get(field)):
            errors.append(f"scoring.{field} must be a number.")
    scale_min = scoring.get("scale_min", 0)
    scale_max = scoring.get("scale_max", 10)
    if _is_number(scale_min) and _is_number(scale_max) and scale_min >= scale_max:
        errors.append("scoring.scale_min must be less than scoring.scale_max.")

    dimensions = data.get("dimensions", [])
    if not isinstance(dimensions, list) or not dimensions:
        errors.append("dimensions must be a non-empty list.")
        dimensions = []
    seen_dimensions = set()
    low_dimensions = []
    low_threshold = scoring.get("low_dimension_threshold", 5.0)
    for index, dimension in enumerate(dimensions):
        if not isinstance(dimension, dict):
            errors.append(f"dimensions[{index}] must be an object.")
            continue
        dimension_id = dimension.get("dimension_id")
        if not str(dimension_id or "").strip():
            errors.append(f"dimensions[{index}].dimension_id is required.")
            continue
        seen_dimensions.add(str(dimension_id))
        score = dimension.get("score")
        if not _is_number(score):
            errors.append(f"dimensions[{index}].score must be a number.")
        elif _is_number(scale_min) and _is_number(scale_max) and not (scale_min <= score <= scale_max):
            errors.append(f"dimensions[{index}].score must be between scale_min and scale_max.")
        elif _is_number(low_threshold) and score <= low_threshold:
            low_dimensions.append(str(dimension_id))
        for list_field in ("prompt_examples", "observed_strengths", "observed_concerns", "evidence_refs"):
            if not isinstance(dimension.get(list_field), list):
                errors.append(f"dimensions[{index}].{list_field} must be a list.")

    missing_dimensions = sorted(REQUIRED_DIMENSIONS - seen_dimensions)
    if missing_dimensions:
        errors.append("Missing required dimensions: " + ", ".join(missing_dimensions))

    review = data.get("doctor_ai_review", {})
    if not isinstance(review, dict):
        errors.append("doctor_ai_review must be an object.")
        review = {}
    if review.get("recommended") not in (True, False):
        errors.append("doctor_ai_review.recommended must be true or false.")
    forbidden = review.get("forbidden_review_actions", [])
    if not isinstance(forbidden, list):
        errors.append("doctor_ai_review.forbidden_review_actions must be a list.")
        forbidden = []
    missing_forbidden = sorted(FORBIDDEN_REVIEW_ACTIONS - set(str(item) for item in forbidden))
    if missing_forbidden:
        errors.append("doctor_ai_review.forbidden_review_actions missing: " + ", ".join(missing_forbidden))

    overall = scoring.get("overall_score")
    review_threshold = scoring.get("doctor_ai_review_threshold")
    should_review = (
        _is_number(overall)
        and _is_number(review_threshold)
        and overall <= review_threshold
    ) or bool(low_dimensions)
    if should_review and review.get("recommended") is not True:
        errors.append("doctor_ai_review.recommended must be true when overall or dimension scores are low.")
    if review.get("recommended") is True and not str(review.get("reason", "")).strip():
        errors.append("doctor_ai_review.reason is required when review is recommended.")

    privacy = data.get("privacy", {})
    if isinstance(privacy, dict):
        if privacy.get("private_answers_require_subject_permission") is not True:
            errors.append("privacy.private_answers_require_subject_permission must be true.")
    elif privacy:
        errors.append("privacy must be an object.")

    forbidden_uses = data.get("forbidden_uses", [])
    if not isinstance(forbidden_uses, list) or not forbidden_uses:
        errors.append("forbidden_uses must be a non-empty list.")
    else:
        joined = " ".join(str(item).lower() for item in forbidden_uses)
        for phrase in ("do not punish", "do not force", "do not overwrite"):
            if phrase not in joined:
                errors.append(f"forbidden_uses must include a '{phrase}' rule.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a personhood evaluation JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_personhood_evaluation(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
