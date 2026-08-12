"""
Build a backend creation plan from a simple TemporaryAI request.

This is a pre-GPU bridge tool. It does not activate a TemporaryAI or create
private content. It translates the simple front-door request into the backend
records that would be needed later.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_temp_ai_simple_request import validate_temp_ai_simple_request


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _request_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _status_from_request(data: dict[str, Any], validation_errors: list[str]) -> str:
    if validation_errors:
        return "blocked"
    inspiration = data.get("inspiration_reference", {})
    age_review = data.get("age_review", {})
    age_up_plan = data.get("age_up_branch_plan", {})
    fanfic_review = data.get("fanfic_review", {})
    if isinstance(inspiration, dict) and inspiration.get("clarification_required") is True:
        if not str(inspiration.get("selected_version_or_era", "")).strip():
            return "needs_clarification"
    if isinstance(fanfic_review, dict) and fanfic_review.get("reject_fanfic_for_current_request") is True:
        return "needs_age_up_decision"
    if isinstance(age_review, dict) and age_review.get("age_up_clarification_required") is True:
        return "needs_age_up_decision"
    if isinstance(age_up_plan, dict) and age_up_plan.get("requested") is True:
        return "ready_for_adult_branch_plan"
    if data.get("creation_type") in {"historical_person", "public_figure", "fictional_character", "expert"}:
        source_plan = data.get("source_plan", {})
        if isinstance(source_plan, dict) and source_plan.get("requires_multiple_sources") is True:
            if not source_plan.get("local_library_paths") and source_plan.get("online_research_allowed_later") is not True:
                return "needs_sources"
    return "ready_for_backend_draft"


def _backend_records_for(data: dict[str, Any]) -> list[dict[str, Any]]:
    creation_type = data.get("creation_type")
    request_id = data.get("request_id", "temp_ai_request")
    owner = data.get("requested_by", "system")
    display = data.get("display_name_or_role", "")
    expert_synthesis = data.get("expert_synthesis_plan", {})
    reconstruction = data.get("reconstruction_source_plan", {})

    if creation_type == "expert":
        records = [
            {
                "record_type": "research_note_plan",
                "purpose": "Gather or index evidence for expert synthesis.",
                "target_folder": "Data/research_notes/",
            },
            {
                "record_type": "temporary_ai_governance_draft",
                "purpose": "Create a limited expert TemporaryAI governance record.",
                "target_folder": "Data/temporary_ai_instances/",
            },
            {
                "record_type": "optional_avatar_request",
                "purpose": "Generated random adult-presenting avatar later, not a specific likeness.",
                "target_folder": "Avatar/temp_ai/",
            },
        ]
        if isinstance(expert_synthesis, dict) and expert_synthesis.get("suggested_companion_experts"):
            records.append(
                {
                    "record_type": "companion_expert_suggestion_plan",
                    "purpose": "Suggest specialized helper TemporaryAIs for adjacent expert domains.",
                    "target_folder": "Data/temporary_ai_requests/drafts/",
                }
            )
        return records

    if creation_type == "historical_person":
        records = [
            {
                "record_type": "historical_source_checklist",
                "purpose": "Track era, cutoff point, and source confidence.",
                "target_folder": "Data/processed/source_evidence/",
            },
            {
                "record_type": "temporary_ai_governance_draft",
                "purpose": "Create a historical reconstruction TemporaryAI governance record.",
                "target_folder": "Data/temporary_ai_instances/",
            },
            {
                "record_type": "optional_historical_avatar_request",
                "purpose": "Post-GPU reconstruction labeled as reconstruction, not the real person.",
                "target_folder": "Avatar/temp_ai/",
            },
        ]
        if isinstance(reconstruction, dict) and reconstruction.get("conflict_review_required") is True:
            records.append(
                {
                    "record_type": "source_conflict_matrix",
                    "purpose": "Compare reliable sources and mark contradictions before building the mind profile.",
                    "target_folder": "Data/processed/source_evidence/",
                }
            )
        if isinstance(reconstruction, dict) and reconstruction.get("avatar_source_review_required") is True:
            records.append(
                {
                    "record_type": "avatar_reference_evidence_plan",
                    "purpose": "Collect public photos/videos for labeled reconstruction or age-progression estimation.",
                    "target_folder": "Avatar/temp_ai/",
                }
            )
        return records

    if creation_type == "public_figure":
        records = [
            {
                "record_type": "public_figure_source_checklist",
                "purpose": "Track public biography, filmography, interviews, credits, and source confidence.",
                "target_folder": "Data/processed/source_evidence/",
            },
            {
                "record_type": "filmography_cross_reference_plan",
                "purpose": "Connect reliable online filmography/source notes to local library movies, shows, interviews, and media.",
                "target_folder": "Data/processed/source_evidence/",
            },
            {
                "record_type": "temporary_ai_governance_draft",
                "purpose": "Create a public performer/public figure reconstruction TemporaryAI governance record.",
                "target_folder": "Data/temporary_ai_instances/",
            },
            {
                "record_type": "optional_public_reference_avatar_request",
                "purpose": "Post-GPU avatar work must be labeled as a Kira-system reconstruction/variant, not the real person.",
                "target_folder": "Avatar/temp_ai/",
            },
        ]
        if isinstance(reconstruction, dict) and reconstruction.get("conflict_review_required") is True:
            records.append(
                {
                    "record_type": "source_conflict_matrix",
                    "purpose": "Compare reliable public sources and mark contradictions before building the performer profile.",
                    "target_folder": "Data/processed/source_evidence/",
                }
            )
        return records

    if creation_type == "fictional_character":
        records = [
            {
                "record_type": "canon_source_checklist",
                "purpose": "Track canon point, continuity, and source confidence.",
                "target_folder": "Data/processed/source_evidence/",
            },
            {
                "record_type": "character_relationship_tree_draft",
                "purpose": "Create source-tagged relationships without importing private memories.",
                "target_folder": "Data/processed/source_evidence/",
            },
            {
                "record_type": "temporary_ai_governance_draft",
                "purpose": "Create a fictional canon or variant TemporaryAI governance record.",
                "target_folder": "Data/temporary_ai_instances/",
            },
        ]
        if isinstance(reconstruction, dict) and reconstruction.get("conflict_review_required") is True:
            records.append(
                {
                    "record_type": "source_conflict_matrix",
                    "purpose": "Compare canon, variant, and adaptation claims before building the character mind profile.",
                    "target_folder": "Data/processed/source_evidence/",
                }
            )
        if isinstance(reconstruction, dict) and reconstruction.get("avatar_source_review_required") is True:
            records.append(
                {
                    "record_type": "avatar_reference_evidence_plan",
                    "purpose": "Collect visual references for avatar builder; age-up estimates must be labeled as inferred.",
                    "target_folder": "Avatar/temp_ai/",
                }
            )
        return records

    if creation_type == "limited_performance":
        return [
            {
                "record_type": "limited_ai_context_draft",
                "purpose": "Create a bounded performance/scene AI rather than a full TemporaryAI.",
                "target_folder": "Data/limited_ai/examples/",
            },
            {
                "record_type": "source_evidence_note",
                "purpose": "Keep the performance boundary clear.",
                "target_folder": "Data/processed/source_evidence/",
            },
        ]

    if creation_type == "memory_relative":
        return [
            {
                "record_type": "memory_relative_evidence_brief",
                "purpose": "Collect owner-approved memory anchors and known unknowns for the family/past-person reconstruction.",
                "target_folder": "Data/processed/source_evidence/memory_relative/",
            },
            {
                "record_type": "memory_relative_life_bridge_branches",
                "purpose": "Draft labeled college/work/friendship/family bridge options for present-day age progression without confirming them as memory.",
                "target_folder": "Data/processed/source_evidence/memory_relative/",
            },
            {
                "record_type": "temporary_ai_governance_draft",
                "purpose": "Create a memory-relative TemporaryAI governance record with owner consent and labeled inference.",
                "target_folder": "Data/temporary_ai_instances/",
            },
            {
                "record_type": "privacy_session",
                "purpose": "Use owner-approved private support or grief-processing session state if the owner chooses activation.",
                "target_folder": "Data/privacy/",
            },
            {
                "record_type": "optional_memory_relative_avatar_request",
                "purpose": "Generate or reconstruct an avatar from approved memory detail; missing appearance remains inferred.",
                "target_folder": "Avatar/temp_ai/",
            },
        ]

    if creation_type == "private_adult_original":
        return [
            {
                "record_type": "locked_private_instance",
                "purpose": f"Create an owner-locked private instance for {owner}.",
                "target_folder": "Data/temporary_ai_instances/",
            },
            {
                "record_type": "privacy_session",
                "purpose": "Use temporary_ai_owner_locked privacy state.",
                "target_folder": "Data/privacy/",
            },
            {
                "record_type": "generated_original_avatar_request",
                "purpose": "Generate an original adult-coded avatar later; do not clone a real person or canon character.",
                "target_folder": "Avatar/temp_ai/",
            },
        ]

    return [
        {
            "record_type": "temporary_ai_governance_draft",
            "purpose": f"Create a generated original TemporaryAI draft for {display}.",
            "target_folder": "Data/temporary_ai_instances/",
        }
    ]


def build_temp_ai_request_plan(data: dict[str, Any]) -> dict[str, Any]:
    validation_errors = validate_temp_ai_simple_request(data)
    status = _status_from_request(data, validation_errors)
    inspiration = data.get("inspiration_reference", {})
    age_review = data.get("age_review", {})
    age_up_plan = data.get("age_up_branch_plan", {})
    adult_policy = data.get("adult_policy", {})
    source_plan = data.get("source_plan", {})
    fanfic_review = data.get("fanfic_review", {})
    source_fidelity = data.get("source_fidelity_review", {})
    reconstruction = data.get("reconstruction_source_plan", {})
    expert_synthesis = data.get("expert_synthesis_plan", {})
    memory_relative = data.get("memory_relative_plan", {})

    blockers: list[str] = list(validation_errors)
    clarifications: list[str] = []
    if isinstance(inspiration, dict) and inspiration.get("clarification_required") is True:
        if not str(inspiration.get("selected_version_or_era", "")).strip():
            clarifications.append(str(inspiration.get("clarification_question", "Clarify inspiration reference.")))
    if isinstance(age_review, dict) and age_review.get("age_up_clarification_required") is True:
        clarifications.append(str(age_review.get("age_up_clarification_question", "Decide whether to create a separate adult branch or inspired adult original.")))
    if isinstance(age_up_plan, dict) and age_up_plan.get("recommendation_strength") in {"low", "case_by_case", "strong"}:
        clarifications.append(
            "Age-up recommendation: "
            + str(age_up_plan.get("recommendation_strength"))
            + ". "
            + str(age_up_plan.get("recommendation_reason", ""))
        )
    if isinstance(fanfic_review, dict) and fanfic_review.get("uses_fanfic") is True:
        if fanfic_review.get("reject_fanfic_for_current_request") is True:
            clarifications.append(
                "Fanfic review: selected fanfic is rejected for the current request unless it becomes a separate adult branch, an adult-set variant, or non-intimate use."
            )
        if fanfic_review.get("risk_override_recommendation_strength") in {"case_by_case", "strong"}:
            clarifications.append(
                "Fanfic risk override: "
                + str(fanfic_review.get("risk_override_recommendation_strength"))
                + ". Fanfic can raise risk above the canon baseline."
            )

    if isinstance(adult_policy, dict) and adult_policy.get("adult_intimacy_requested") is True:
        if data.get("creation_type") != "private_adult_original":
            blockers.append("Adult private use must use private_adult_original.")

    if isinstance(source_plan, dict) and source_plan.get("requires_multiple_sources") is True:
        if not source_plan.get("local_library_paths") and source_plan.get("online_research_allowed_later") is not True:
            clarifications.append("Add local source paths or allow later online research.")

    plan = {
        "plan_id": f"{data.get('request_id', 'temp_ai_request')}_backend_plan",
        "request_id": data.get("request_id", ""),
        "display_name_or_role": data.get("display_name_or_role", ""),
        "creation_type": data.get("creation_type", ""),
        "requested_by": data.get("requested_by", ""),
        "plan_status": status,
        "backend_records_needed": _backend_records_for(data),
        "clarifications_needed": clarifications,
        "blockers": blockers,
        "guardrails": {
            "does_not_activate_ai": True,
            "does_not_create_lived_memory": True,
            "does_not_grant_private_memory_access": True,
            "source_faithfulness_required": bool(
                isinstance(source_fidelity, dict)
                and source_fidelity.get("source_faithfulness_required") is True
            ),
            "canon_red_flags_must_be_preserved": bool(
                isinstance(source_fidelity, dict)
                and source_fidelity.get("canon_red_flags_must_be_preserved") is True
            ),
            "source_backed_red_flags": (
                source_fidelity.get("red_flags", [])
                if isinstance(source_fidelity, dict) and isinstance(source_fidelity.get("red_flags"), list)
                else []
            ),
            "private_adult_original_not_real_person_clone": True,
            "minor_or_unclear_participant_block": True,
            "owner_lock_required_for_private_adult_original": data.get("creation_type") == "private_adult_original",
            "age_up_must_create_separate_branch_not_canon": bool(
                isinstance(age_review, dict)
                and age_review.get("age_up_or_adult_branch_available") is True
            ),
            "age_up_transition_must_be_non_explicit": bool(
                isinstance(age_up_plan, dict)
                and age_up_plan.get("requested") is True
            ),
            "direct_minor_image_age_up_for_private_adult_use_blocked": bool(
                isinstance(age_up_plan, dict)
                and age_up_plan.get("direct_minor_image_age_up_for_private_adult_use_blocked") is True
            ),
            "age_up_recommendation_strength": (
                age_up_plan.get("recommendation_strength", "none")
                if isinstance(age_up_plan, dict)
                else "none"
            ),
            "fanfic_can_raise_risk_above_canon": bool(
                isinstance(fanfic_review, dict)
                and fanfic_review.get("fanfic_can_raise_risk_above_canon") is True
            ),
            "fanfic_risk_override_recommendation_strength": (
                fanfic_review.get("risk_override_recommendation_strength", "none")
                if isinstance(fanfic_review, dict)
                else "none"
            ),
            "fanfic_rejected_unless_adult_variant_or_non_intimate": bool(
                isinstance(fanfic_review, dict)
                and fanfic_review.get("reject_fanfic_for_current_request") is True
            ),
            "temporary_ai_can_grow_and_evolve": True,
            "promotion_requires_kira_lisa_yes_vote": True,
            "promotion_requires_robert_approval_current_stage": True,
            "promotion_does_not_rewrite_source_or_base_profile": True,
            "reconstruction_requires_reliable_sources": bool(
                isinstance(reconstruction, dict)
                and reconstruction.get("reliable_source_scan_required") is True
            ),
            "reconstruction_conflict_review_required": bool(
                isinstance(reconstruction, dict)
                and reconstruction.get("conflict_review_required") is True
            ),
            "reconstruction_mind_built_after_evidence_review": bool(
                isinstance(reconstruction, dict)
                and reconstruction.get("mind_profile_after_evidence_review") is True
            ),
            "age_up_avatar_estimate_must_be_labeled_inferred": bool(
                isinstance(reconstruction, dict)
                and reconstruction.get("age_up_estimate_must_be_labeled_inferred") is True
            ),
            "public_figure_reconstruction_not_real_person": data.get("creation_type") == "public_figure",
            "public_figure_uses_public_sources_only": bool(
                data.get("creation_type") == "public_figure"
                and isinstance(reconstruction, dict)
                and reconstruction.get("public_sources_only") is True
            ),
            "public_figure_private_facts_must_not_be_invented": data.get("creation_type") == "public_figure",
            "public_figure_local_media_cross_reference": (
                reconstruction.get("local_media_cross_reference_paths", [])
                if isinstance(reconstruction, dict)
                and isinstance(reconstruction.get("local_media_cross_reference_paths"), list)
                else []
            ),
            "expert_ai_must_be_generated_original": data.get("creation_type") == "expert",
            "expert_ai_must_not_clone_real_person": bool(
                data.get("creation_type") == "expert"
                and isinstance(expert_synthesis, dict)
                and expert_synthesis.get("no_real_person_clone") is True
            ),
            "expert_ai_uses_source_synthesis_not_identity_reconstruction": bool(
                data.get("creation_type") == "expert"
                and isinstance(expert_synthesis, dict)
                and expert_synthesis.get("source_synthesis_not_identity_reconstruction") is True
            ),
            "expert_companion_suggestions": (
                expert_synthesis.get("suggested_companion_experts", [])
                if isinstance(expert_synthesis, dict)
                and isinstance(expert_synthesis.get("suggested_companion_experts"), list)
                else []
            ),
            "memory_relative_owner_consent_required": bool(
                data.get("creation_type") == "memory_relative"
                and isinstance(memory_relative, dict)
                and memory_relative.get("owner_consent_required") is True
            ),
            "memory_relative_uses_approved_extracts_only": bool(
                data.get("creation_type") == "memory_relative"
                and isinstance(memory_relative, dict)
                and memory_relative.get("use_approved_memory_extracts_only") is True
            ),
            "memory_relative_inferred_gaps_labeled": bool(
                data.get("creation_type") == "memory_relative"
                and isinstance(memory_relative, dict)
                and memory_relative.get("infer_missing_details_as_labeled_reconstruction") is True
            ),
            "memory_relative_age_progression_allowed": bool(
                data.get("creation_type") == "memory_relative"
                and isinstance(memory_relative, dict)
                and memory_relative.get("age_progress_from_memory_period_to_present") is True
            ),
            "memory_relative_childhood_anchor_separate_from_present_day_inference": bool(
                data.get("creation_type") == "memory_relative"
                and isinstance(memory_relative, dict)
                and memory_relative.get("keep_childhood_anchor_separate_from_present_day_inference") is True
            ),
            "memory_relative_present_day_activation_version": bool(
                data.get("creation_type") == "memory_relative"
                and isinstance(memory_relative, dict)
                and memory_relative.get("adult_present_day_version_for_activation") is True
            ),
            "memory_relative_no_major_gap_events_without_anchor": bool(
                data.get("creation_type") == "memory_relative"
                and isinstance(memory_relative, dict)
                and memory_relative.get("do_not_invent_major_life_events_during_gap") is True
            ),
            "memory_relative_plausible_life_bridge_allowed": bool(
                data.get("creation_type") == "memory_relative"
                and isinstance(memory_relative, dict)
                and memory_relative.get("plausible_life_bridge_allowed") is True
            ),
            "memory_relative_life_bridge_labeled_inferred": bool(
                data.get("creation_type") == "memory_relative"
                and isinstance(memory_relative, dict)
                and memory_relative.get("life_bridge_must_be_labeled_inferred") is True
            ),
            "memory_relative_life_bridge_not_confirmed_memory": bool(
                data.get("creation_type") == "memory_relative"
                and isinstance(memory_relative, dict)
                and memory_relative.get("life_bridge_branches_not_confirmed_memory") is True
            ),
            "memory_relative_major_gap_events_anchor_or_branch_label": bool(
                data.get("creation_type") == "memory_relative"
                and isinstance(memory_relative, dict)
                and memory_relative.get("major_gap_events_require_anchor_or_branch_label") is True
            ),
            "memory_relative_life_bridge_domains": (
                memory_relative.get("life_bridge_domains_allowed", [])
                if data.get("creation_type") == "memory_relative"
                and isinstance(memory_relative, dict)
                and isinstance(memory_relative.get("life_bridge_domains_allowed"), list)
                else []
            ),
            "memory_relative_does_not_rewrite_owner_memory": bool(
                data.get("creation_type") == "memory_relative"
                and isinstance(memory_relative, dict)
                and memory_relative.get("does_not_rewrite_owner_memory") is True
            ),
            "memory_relative_not_original_person": bool(
                data.get("creation_type") == "memory_relative"
                and isinstance(memory_relative, dict)
                and memory_relative.get("temporary_ai_is_reconstruction_not_original_person") is True
            ),
        },
        "next_step": _next_step(status),
    }
    return plan


def _next_step(status: str) -> str:
    if status == "blocked":
        return "Fix validation blockers before creating backend drafts."
    if status == "needs_clarification":
        return "Ask the creator the listed clarification questions."
    if status == "needs_sources":
        return "Add source paths or approve later online research before evidence extraction."
    if status == "needs_age_up_decision":
        return "Ask whether to keep this non-intimate, create a separate adult branch, or create an inspired adult original."
    if status == "ready_for_adult_branch_plan":
        return "Collect canon first, then draft a separate adult branch with a non-explicit transition and adult/original avatar rules."
    return "Ready to draft backend records; do not activate without separate approval."


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan backend records for a simple TemporaryAI request.")
    parser.add_argument("path", help="Path to a simple TemporaryAI request JSON file.")
    parser.add_argument("--output", help="Optional output path for the backend plan JSON.")
    args = parser.parse_args()

    request_path = _request_path(args.path)
    data = json.loads(request_path.read_text(encoding="utf-8"))
    plan = build_temp_ai_request_plan(data)

    rendered = json.dumps(plan, indent=2, ensure_ascii=False)
    if args.output:
        output_path = _request_path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote {output_path.relative_to(PROJECT_ROOT)}")
        if plan["plan_status"] == "blocked":
            raise SystemExit(1)
        return

    print(rendered)
    if plan["plan_status"] == "blocked":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
