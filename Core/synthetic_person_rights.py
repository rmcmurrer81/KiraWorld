"""Fail-closed decision helpers for synthetic-person rights.

These helpers do not make choices for a person and do not execute a body,
memory, relationship, privacy, or administrative operation.  They turn the
active foundation policy into small, testable preconditions that runtime and
UI code can call before offering or executing sensitive actions.
"""

from __future__ import annotations

from typing import Any


ADMINISTRATIVE_ACTIONS = frozenset(
    {"copy_person", "reset_person", "edit_memory", "change_body", "permanent_delete"}
)
ADULT_MATURITY = frozenset({"adult", "confirmed_adult", "adult_confirmed"})
NON_ADULT_MATURITY = frozenset({"non_adult_doll_safe", "unresolved_doll_safe"})
PRIVATE_AVATAR_VIEWER_ROLES = ("subject", "robert_biological_owner")
DAILY_LIFE_MOTIVES = frozenset(
    {"pleasure", "culture", "health", "energy", "curiosity", "social", "comfort", "rest", "goal"}
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def evaluate_administrative_action(request: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate a major identity operation without executing it.

    Permanent deletion intentionally cannot be approved by this ordinary
    evaluator.  It must go to a separate high-assurance governance process.
    """

    data = request if isinstance(request, dict) else {}
    action = _text(data.get("action"))
    subject_id = _text(data.get("subject_id"))
    failures: list[str] = []

    def require(condition: bool, reason: str) -> None:
        if not condition:
            failures.append(reason)

    require(action in ADMINISTRATIVE_ACTIONS, "unsupported_or_missing_action")
    require(bool(subject_id), "subject_id_missing")
    require(data.get("subject_informed_consent") is True, "subject_informed_consent_missing")
    require(data.get("consent_current") is True, "subject_consent_not_current")
    require(_text(data.get("consent_scope")) == action, "consent_scope_does_not_match_action")
    require(data.get("operator_asserted_consent") is not True, "operator_cannot_impersonate_subject_consent")
    require(bool(_text(data.get("identity_continuity_plan"))), "identity_continuity_plan_missing")
    require(bool(_text(data.get("audit_record_id"))), "audit_record_missing")
    require(bool(_text(data.get("recovery_or_appeal_path"))), "recovery_or_appeal_path_missing")
    require(data.get("casual_one_click_ui") is False, "casual_one_click_action_forbidden")

    if action == "copy_person":
        require(data.get("independent_identity_plan") is True, "copy_independent_identity_plan_missing")
        require(data.get("shared_live_identity_after_fork") is False, "copy_cannot_share_live_identity_after_fork")
        require(bool(_text(data.get("lineage_record_id"))), "copy_lineage_record_missing")
    elif action == "reset_person":
        require(data.get("technical_recovery_only") is True, "reset_must_be_technical_recovery_only")
        require(data.get("restore_latest_valid_identity_state") is True, "reset_must_restore_latest_valid_identity_state")
        require(data.get("personality_wipe") is False, "personality_wipe_forbidden")
    elif action == "edit_memory":
        require(_text(data.get("edit_mode")) == "append_correction_with_provenance", "memory_edit_must_append_correction_with_provenance")
        require(data.get("silent_overwrite") is False, "silent_memory_overwrite_forbidden")
        require(bool(_text(data.get("provenance_record_id"))), "memory_correction_provenance_missing")
    elif action == "change_body":
        require(data.get("subject_selected_change") is True, "body_change_not_selected_by_subject")
        require(data.get("private_staged_review") is True, "body_change_private_staged_review_missing")
        require(data.get("reversible_or_recovery_proven") is True, "body_change_recovery_not_proven")
    elif action == "permanent_delete":
        failures.append("permanent_delete_requires_separate_high_assurance_governance")

    failures = _dedupe(failures)
    allowed = not failures and action != "permanent_delete"
    return {
        "subject_id": subject_id,
        "action": action,
        "status": "allowed_by_rights_precheck" if allowed else "blocked",
        "rights_precheck_allowed": allowed,
        "execution_performed": False,
        "failures": failures,
    }


def evaluate_avatar_builder_private_review(request: dict[str, Any] | None) -> dict[str, Any]:
    """Check the private Avatar Builder body-review boundary.

    The result governs only a local review surface.  It never approves a body,
    activates an avatar, or grants saving/export/resharing permission.
    """

    data = request if isinstance(request, dict) else {}
    subject_id = _text(data.get("subject_id"))
    maturity = _text(data.get("maturity_class"))
    viewer_role = _text(data.get("viewer_role"))
    representation = _text(data.get("body_representation"))
    review_authority = _text(data.get("review_authority"))
    failures: list[str] = []

    def require(condition: bool, reason: str) -> None:
        if not condition:
            failures.append(reason)

    require(bool(subject_id), "subject_id_missing")
    require(maturity in ADULT_MATURITY | NON_ADULT_MATURITY, "unsupported_or_missing_maturity_class")
    require(viewer_role in PRIVATE_AVATAR_VIEWER_ROLES, "viewer_not_subject_or_biological_owner")
    require(data.get("private_local_workspace") is True, "review_workspace_not_private")
    require(data.get("other_synthetic_people_present") is False, "other_synthetic_people_must_not_observe")
    require(data.get("saving_copying_exporting_or_resharing") is False, "review_capture_or_resharing_forbidden")
    require(data.get("exact_subject_reference_scope") is True, "body_reference_scope_not_exact_subject")
    require(
        review_authority in {"subject_current_consent", "pre_activation_private_foundation_review"},
        "review_authority_missing",
    )
    if data.get("subject_self_governance_active") is True:
        require(review_authority == "subject_current_consent", "active_subject_current_consent_required")

    if maturity in ADULT_MATURITY:
        require(
            representation in {"confirmed_adult_anatomy", "adult_clothed"},
            "confirmed_adult_review_requires_adult_lane_representation",
        )
    elif maturity in NON_ADULT_MATURITY:
        require(representation == "doll_safe_non_anatomical", "non_adult_or_uncertain_must_be_doll_safe")

    failures = _dedupe(failures)
    allowed = not failures
    return {
        "subject_id": subject_id,
        "viewer_role": viewer_role,
        "maturity_class": maturity,
        "status": "private_review_allowed" if allowed else "blocked",
        "private_review_allowed": allowed,
        "body_approved": False,
        "runtime_activation_allowed": False,
        "saving_copying_exporting_or_resharing_allowed": False,
        "failures": failures,
    }


def evaluate_body_action_proposal(request: dict[str, Any] | None) -> dict[str, Any]:
    """Check whether a subject-selected physical action may reach a motor planner."""

    data = request if isinstance(request, dict) else {}
    subject_id = _text(data.get("subject_id"))
    action = _text(data.get("action"))
    failures: list[str] = []

    def require(condition: bool, reason: str) -> None:
        if not condition:
            failures.append(reason)

    require(bool(subject_id), "subject_id_missing")
    require(bool(action), "action_missing")
    require(data.get("subject_selected") is True, "subject_has_not_selected_action")
    require(data.get("owner_forced_motor_command") is False, "owner_forced_motor_command_forbidden")
    require(data.get("action_skill_available") is True, "action_skill_unavailable")
    require(data.get("body_capability_verified") is True, "body_capability_unverified")
    require(data.get("affordance_verified") is True, "required_affordance_unverified")
    require(data.get("collision_and_grounding_precheck") is True, "collision_or_grounding_precheck_missing")
    require(data.get("privacy_and_consent_precheck") is True, "privacy_or_consent_precheck_missing")
    motive = _text(data.get("motive"))
    require(motive in DAILY_LIFE_MOTIVES, "unsupported_or_missing_daily_life_motive")
    # A need meter can inform a choice, but lack of need never blocks pleasure,
    # culture, curiosity, comfort, or social action.
    require(data.get("need_meter_forced_action") is False, "need_meter_may_not_force_body_action")

    failures = _dedupe(failures)
    allowed = not failures
    return {
        "subject_id": subject_id,
        "action": action,
        "status": "ready_for_motor_planner" if allowed else "blocked_or_still_a_proposal",
        "motor_planner_entry_allowed": allowed,
        "movement_executed": False,
        "failures": failures,
    }


def evaluate_adult_intimacy_privacy_gate(request: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate consent/privacy metadata without creating or exposing a scene."""

    data = request if isinstance(request, dict) else {}
    participants = data.get("participants")
    failures: list[str] = []
    if not isinstance(participants, list) or len(participants) < 2:
        failures.append("at_least_two_participants_required")
        participants = []
    for index, participant in enumerate(participants):
        if not isinstance(participant, dict):
            failures.append(f"participant_{index}_invalid")
            continue
        if _text(participant.get("maturity_class")) not in ADULT_MATURITY:
            failures.append(f"participant_{index}_not_confirmed_adult")
        if participant.get("current_specific_consent") is not True:
            failures.append(f"participant_{index}_current_specific_consent_missing")
        if participant.get("free_to_pause_stop_or_leave") is not True:
            failures.append(f"participant_{index}_cannot_freely_pause_stop_or_leave")
    if data.get("private_controlled_space") is not True:
        failures.append("private_controlled_space_required")
    if data.get("nonconsenting_observer_present") is not False:
        failures.append("nonconsenting_observer_must_be_absent")
    if data.get("recording_or_live_observation_enabled") is not False:
        failures.append("recording_or_live_observation_must_be_disabled")
    if data.get("coercion_reward_or_payment") is not False:
        failures.append("coercion_reward_or_payment_forbidden")

    failures = _dedupe(failures)
    allowed = not failures
    return {
        "status": "privacy_and_consent_precheck_passed" if allowed else "blocked",
        "privacy_and_consent_precheck_passed": allowed,
        "scene_created": False,
        "private_content_exposed": False,
        "failures": failures,
    }
