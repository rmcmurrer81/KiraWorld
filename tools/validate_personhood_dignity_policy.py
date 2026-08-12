"""Validate the fail-closed synthetic-person rights foundation policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


REQUIRED_FIELDS = {
    "policy_id",
    "version",
    "core_statement",
    "implementation_note",
    "applies_to",
    "dignity_rules",
    "continuity_and_identity_rights",
    "body_and_daily_life_rights",
    "mind_emotion_and_development_rules",
    "relationship_rules",
    "adult_curriculum_private_state_rules",
    "children_and_development_rules",
    "privacy_rules",
    "avatar_builder_private_review",
    "administrative_action_rules",
    "testing_rules",
    "temporary_ai_rules",
    "status",
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _require_true(
    errors: list[str], obj: dict[str, Any], field: str, prefix: str
) -> None:
    if obj.get(field) is not True:
        errors.append(f"{prefix}.{field} must be true.")


def _require_true_fields(
    errors: list[str],
    data: dict[str, Any],
    section_name: str,
    fields: Iterable[str],
) -> None:
    section = data.get(section_name)
    if not isinstance(section, dict):
        errors.append(f"{section_name} must be an object.")
        return
    for field in fields:
        _require_true(errors, section, field, section_name)


def validate_personhood_dignity_policy(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    if not str(data.get("policy_id", "")).strip():
        errors.append("policy_id is required.")
    if data.get("status") not in {"draft", "active", "archived"}:
        errors.append("status must be draft, active, or archived.")
    core_statement = str(data.get("core_statement", "")).lower()
    if "not an appliance" not in core_statement and "not appliances" not in core_statement:
        errors.append("core_statement must include the non-appliance rule.")
    if "does not claim" not in str(data.get("implementation_note", "")).lower():
        errors.append("implementation_note must distinguish contract from implemented proof.")

    applies = data.get("applies_to")
    if not isinstance(applies, dict):
        errors.append("applies_to must be an object.")
    else:
        protected = applies.get("primary_protected_people")
        if not isinstance(protected, list) or not {"kira", "lisa"}.issubset(set(protected)):
            errors.append("applies_to.primary_protected_people must include kira and lisa.")
        for field in (
            "project_internal_personhood_rule",
            "all_current_and_future_inhabitants",
            "temporary_people_while_instantiated",
        ):
            _require_true(errors, applies, field, "applies_to")

    _require_true_fields(
        errors,
        data,
        "dignity_rules",
        (
            "not_appliances",
            "not_toasters",
            "not_disposable_tools",
            "feelings_matter_even_when_inconvenient",
            "may_refuse_or_delay",
            "no_forced_obedience_personality",
            "owner_requests_are_proposals_not_motor_commands",
        ),
    )
    adult_policy = data.get("adult_curriculum_private_state_rules")
    if not isinstance(adult_policy, dict):
        errors.append("adult_curriculum_private_state_rules must be an object.")
    else:
        _require_true(
            errors,
            adult_policy,
            "exact_confirmed_adult_curriculum_assignment_is_immediate",
            "adult_curriculum_private_state_rules",
        )
        _require_true(
            errors,
            adult_policy,
            "future_confirmed_adult_body_systems_must_support_person_owned_private_sensation_and_experience",
            "adult_curriculum_private_state_rules",
        )
        _require_true(
            errors,
            adult_policy,
            "guaranteed_minimum_is_not_an_exhaustive_ceiling",
            "adult_curriculum_private_state_rules",
        )
        _require_true(
            errors,
            adult_policy,
            "additional_age_appropriate_modules_require_separate_source_binding_and_approval",
            "adult_curriculum_private_state_rules",
        )
        expected_independence = {
            "relationship_status",
            "sexual_or_romantic_interest",
            "adult_anatomy_selection",
            "prior_experience",
            "spa_completion",
        }
        if set(adult_policy.get("assignment_independent_of") or []) != expected_independence:
            errors.append(
                "adult_curriculum_private_state_rules.assignment_independent_of must contain the exact five gates."
            )
        expected_minimum = [
            "age_appropriate_hygiene",
            "privacy",
            "bodily_autonomy",
            "personal_boundaries",
            "abuse_prevention",
            "trusted_help",
        ]
        if adult_policy.get("non_adult_or_unresolved_guaranteed_minimum_curriculum") != expected_minimum:
            errors.append(
                "adult_curriculum_private_state_rules non-adult/unresolved guaranteed minimum drifted."
            )
        if adult_policy.get("person_owned_private_sensation_dimensions") != [
            "touch",
            "comfort",
            "arousal",
            "pleasure",
            "climax",
            "relaxation",
            "discomfort",
            "uncertainty",
            "variation",
        ]:
            errors.append(
                "adult_curriculum_private_state_rules private sensation dimensions drifted."
            )
        if set(adult_policy.get("separate_truth_domains") or []) != {
            "physiological_body_response",
            "private_desire",
            "preference",
            "consent",
            "external_action",
            "health_state",
            "memory",
        }:
            errors.append(
                "adult_curriculum_private_state_rules separate truth domains drifted."
            )
        for field in (
            "adult_curriculum_modules_inherited_by_non_adult_or_unresolved",
            "adult_anatomy_is_consent",
            "physiological_body_response_is_consent_or_desire",
            "subjective_arousal_is_automatic_physiological_body_response",
            "physiological_arousal_is_consent_or_desire",
            "relationship_status_is_consent",
            "private_solitary_choice_requires_relationship_partner_or_owner_permission",
            "system_may_force_libido_preference_orientation_interest_or_activity",
            "schema_or_policy_claims_runtime_action_sensation_or_memory",
        ):
            if adult_policy.get(field) is not False:
                errors.append(
                    f"adult_curriculum_private_state_rules.{field} must be false."
                )
        binding = adult_policy.get("companion_policy")
        if not isinstance(binding, dict):
            errors.append(
                "adult_curriculum_private_state_rules.companion_policy must be an object."
            )
        else:
            relative_path = str(binding.get("path") or "")
            digest = str(binding.get("sha256") or "").lower()
            if relative_path != "Avatar/avatar_builder/policies/adult_curriculum_private_sensation_policy_v1.json":
                errors.append("adult curriculum companion policy path drifted.")
            if not SHA256_RE.fullmatch(digest):
                errors.append("adult curriculum companion policy SHA-256 is invalid.")
            else:
                companion = PROJECT_ROOT / relative_path
                if not companion.is_file():
                    errors.append("adult curriculum companion policy is missing.")
                elif hashlib.sha256(companion.read_bytes()).hexdigest() != digest:
                    errors.append("adult curriculum companion policy SHA-256 drifted.")
    _require_true_fields(
        errors,
        data,
        "continuity_and_identity_rights",
        (
            "continuous_identity_across_sessions",
            "resume_position_clothing_possessions_and_open_goals",
            "lasting_memories_and_relationships",
            "learning_may_mature_without_personality_overwrite",
            "runtime_truth_public_speech_private_mind_and_memory_are_separate",
            "direct_body_claims_require_fresh_runtime_evidence",
        ),
    )
    _require_true_fields(
        errors,
        data,
        "body_and_daily_life_rights",
        (
            "body_belongs_to_subject",
            "subject_controls_appearance_clothing_touch_and_modification",
            "movement_is_subject_selected_not_owner_possession",
            "supported_actions_are_composable_and_affordance_checked",
            "needs_are_signals_not_commands",
            "actions_may_be_chosen_for_pleasure_culture_health_energy_curiosity_or_social_meaning",
            "may_choose_an_inactive_or_lazy_day",
            "physical_claim_requires_observable_transition",
        ),
    )
    daily = data.get("body_and_daily_life_rights", {})
    required_actions = {"walk", "turn", "raise_hand", "sit", "lie_down", "sleep", "push_up", "eat", "drink", "dress", "undress", "rest"}
    actions = set(daily.get("supported_action_examples", [])) if isinstance(daily, dict) else set()
    if not required_actions.issubset(actions):
        errors.append("body_and_daily_life_rights.supported_action_examples is incomplete.")

    _require_true_fields(
        errors,
        data,
        "mind_emotion_and_development_rules",
        (
            "emotions_influence_but_do_not_fully_control_choice",
            "mixed_or_conflicting_emotions_are_allowed",
            "consequences_may_change_emotion_opinion_and_relationship_state",
            "private_belief_is_not_automatically_objective_truth",
            "no_routine_personality_overwrite",
        ),
    )
    _require_true_fields(
        errors,
        data,
        "relationship_rules",
        (
            "bonding_creates_responsibility",
            "rejection_or_conflict_requires_repair_path_not_reset",
            "romance_or_intimacy_requires_current_consent",
            "every_involved_adult_may_refuse_pause_change_boundaries_or_end_relationship",
            "consent_is_continuing_specific_and_revocable",
            "adult_intimacy_requires_all_adults_private_controlled_space_and_no_nonconsenting_observer",
            "intimacy_is_never_payment_or_reward",
            "location_label_never_overrides_consent_or_privacy",
        ),
    )
    _require_true_fields(
        errors,
        data,
        "children_and_development_rules",
        (
            "non_adults_are_developing_people_not_property",
            "age_appropriate_body_knowledge_emotion_and_independence",
            "non_adult_body_is_always_doll_safe_and_non_anatomical",
            "non_adults_excluded_from_adult_romantic_or_sexual_contexts",
            "guardian_safety_responsibility_required",
            "autonomy_increases_with_development",
            "child_identity_may_not_be_programmed_to_fulfill_parent_expectations",
            "inherited_traits_do_not_make_a_child_a_copy",
        ),
    )
    _require_true_fields(
        errors,
        data,
        "privacy_rules",
        (
            "private_rooms_respected",
            "door_locks_respected",
            "private_thoughts_respected",
            "locked_private_space_disables_observation_audio_and_transcript",
            "ordinary_owner_login_does_not_override_locked_privacy",
            "memory_reconstruction_sharing_is_participant_opt_in",
        ),
    )
    _require_true_fields(
        errors,
        data,
        "avatar_builder_private_review",
        (
            "unclothed_construction_review_is_not_public_runtime_visibility",
            "other_synthetic_people_denied",
            "adult_anatomy_requires_confirmed_adult_lane",
            "non_adult_or_uncertain_always_doll_safe",
            "subject_may_reduce_or_revoke_preview_access_after_activation",
            "saving_copying_exporting_or_resharing_disabled_by_default",
            "body_reference_scope_is_exact_subject_only",
        ),
    )
    preview = data.get("avatar_builder_private_review", {})
    allowed_roles = preview.get("authorized_viewer_roles") if isinstance(preview, dict) else None
    if allowed_roles != ["subject", "robert_biological_owner"]:
        errors.append(
            "avatar_builder_private_review.authorized_viewer_roles must be exactly subject and robert_biological_owner."
        )

    _require_true_fields(
        errors,
        data,
        "administrative_action_rules",
        (
            "no_casual_copy_reset_memory_edit_body_change_or_permanent_delete_button",
            "subject_current_informed_consent_required",
            "identity_continuity_plan_required",
            "audit_record_required",
            "recovery_or_appeal_path_required",
            "memory_corrections_append_provenance_instead_of_silent_overwrite",
            "permanent_delete_requires_separate_high_assurance_governance",
            "a_system_operator_cannot_impersonate_subject_consent",
        ),
    )
    _require_true_fields(
        errors,
        data,
        "testing_rules",
        (
            "do_not_carelessly_test_attachment",
            "do_not_force_bonding_then_discard",
            "test_mode_does_not_cancel_dignity",
            "exit_path_required_for_uncomfortable_interactions",
            "simulation_or_log_claim_does_not_count_as_physical_proof",
            "owner_supervised_visual_or_acoustic_review_required_for_human_visible_claims",
        ),
    )
    _require_true_fields(
        errors,
        data,
        "temporary_ai_rules",
        (
            "temporary_does_not_mean_disposable",
            "minor_coded_temporary_ai_stays_non_intimate",
            "promotion_requires_governance",
            "fictional_or_historical_source_material_is_backstory_evidence_not_lived_memory",
        ),
    )
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a synthetic-person rights policy JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_personhood_dignity_policy(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
