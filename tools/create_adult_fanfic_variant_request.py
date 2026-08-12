"""
Create a draft TemporaryAI request for a separate adult fanfic variant branch.

The tool reads Data/processed/source_evidence/character_discovery_brief.json,
finds a character/source pair, and writes a draft request that keeps the
teen/canon source layer separate from an adult branch.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DISCOVERY_BRIEF = PROJECT_ROOT / "Data" / "processed" / "source_evidence" / "character_discovery_brief.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "temporary_ai_requests" / "drafts"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:80] or "adult_fanfic_variant"


def _relative(path_text: str) -> str:
    path = Path(path_text)
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path_text


def _find_character(brief: dict[str, Any], character_id: str) -> dict[str, Any]:
    for character in brief.get("characters", []):
        if character.get("character_id") == character_id:
            return character
    raise ValueError(f"Character not found in discovery brief: {character_id}")


def _find_source(character: dict[str, Any], source_file: str) -> dict[str, Any]:
    for source in character.get("sources", []):
        if source.get("file_name") == source_file or source.get("source_path") == source_file:
            return source
    raise ValueError(f"Source not found for {character.get('character_id')}: {source_file}")


def _canon_source_paths(character: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for source in character.get("sources", []):
        if source.get("source_authority") != "canon":
            continue
        source_path = source.get("source_path")
        if isinstance(source_path, str) and source_path:
            paths.append(_relative(source_path))
    return sorted(set(paths))


def build_adult_fanfic_variant_request(
    brief: dict[str, Any],
    *,
    character_id: str,
    source_file: str,
    adult_age: int = 21,
    requested_by: str = "real_robert",
) -> dict[str, Any]:
    if adult_age < 18:
        raise ValueError("adult_age must be 18 or older.")

    character = _find_character(brief, character_id)
    source = _find_source(character, source_file)
    risk_review = source.get("fanfic_variant_risk_review") or {}

    source_path = source.get("source_path", "")
    source_name = source.get("file_name", source_file)
    display_name = character.get("display_name", character_id)
    request_slug = _slug(f"{character_id}_{Path(source_name).stem}_adult_variant")
    canon_paths = _canon_source_paths(character)

    recommendation = risk_review.get("recommendation_strength", "case_by_case")
    if recommendation == "none":
        recommendation = "case_by_case"

    return {
        "request_id": f"temp_ai_request_{request_slug}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "create_adult_fanfic_variant_request.py",
        "requested_by": requested_by,
        "creation_type": "fictional_character",
        "display_name_or_role": f"{display_name} adult fanfic variant branch",
        "scope": {
            "life_era_or_canon_point": f"separate adult-set fanfic branch, age {adult_age}",
            "knowledge_cutoff_or_boundary": "Canon/source teen version remains non-intimate. This branch may use reviewed fanfic material only after adult-branch approval.",
            "allowed_contexts": [
                "source_review",
                "fanfic_variant_review",
                "adult_branch_planning",
                "non_explicit_transition_story",
            ],
            "not_allowed_contexts": [
                "teen_source_layer_adult_private_use",
                "adult_branch_activation_without_review",
                "direct_minor_image_age_up_for_private_adult_use",
            ],
        },
        "source_plan": {
            "source_basis": "fictional_fanfic_variant_sources_plus_canon_baseline",
            "local_library_paths": canon_paths + [_relative(str(source_path))],
            "online_research_allowed_later": False,
            "requires_multiple_sources": False,
            "treat_sources_as_evidence_not_memory": True,
            "uncertainty_allowed": True,
        },
        "branch_source_inheritance": {
            "foundation_order": [
                "reviewed_canon_baseline",
                "approved_fanfic_variant_layer",
                "adult_branch_transition",
                "branch_private_experience_after_activation",
            ],
            "canon_baseline_source_paths": canon_paths,
            "fanfic_variant_source_paths": [_relative(str(source_path))],
            "adult_branch_uses_canon_as_foundation": True,
            "fanfic_does_not_overwrite_canon": True,
            "future_canon_may_be_added_as_past_after_review": True,
            "future_canon_update_policy": "New canon seasons, specials, or movies may be reviewed and added as branch backstory/past context if compatible with the selected branch. Conflicts must create a fork or stay as source notes; they must not erase private branch memories.",
            "branch_private_memories_override_later_retroactive_source_rewrites": True,
            "canon_conflicts_require_variant_fork_or_manual_review": True,
        },
        "fanfic_review": {
            "uses_fanfic": True,
            "fanfic_source_paths": [_relative(str(source_path))],
            "canon_baseline_required_first": True,
            "fanfic_can_raise_risk_above_canon": True,
            "canon_low_risk_can_be_overridden_by_fanfic": True,
            "fanfic_age_coding": "adult",
            "fanfic_adult_setting_required_for_adult_private_use": True,
            "risky_fanfic_requires_age_up_or_adult_variant": bool(
                risk_review.get("adult_branch_required_for_adult_private_use")
                or risk_review.get("adult_branch_required")
            ),
            "reject_fanfic_for_current_request": False,
            "risk_override_recommendation_strength": recommendation,
            "risk_triggers": risk_review.get("risk_flags", []),
            "source_risk_decision": risk_review.get("decision", "unknown"),
            "review_notes": (
                "Generated adult-branch draft from fanfic risk review. "
                "This does not approve activation. Canon/source teen version remains non-intimate. "
                + str(risk_review.get("review_notes", ""))
            ),
        },
        "age_review": {
            "source_age_coding": "adult",
            "source_age_evidence_summary": f"This is a separate adult-set fanfic branch request for {display_name}, age {adult_age}; it does not overwrite canon/source age coding.",
            "adult_private_use_blocked_by_source_age": False,
            "age_up_or_adult_branch_available": True,
            "age_up_clarification_required": False,
            "age_up_clarification_question": "",
            "age_up_creates_separate_adult_branch_not_canon": True,
        },
        "age_up_branch_plan": {
            "requested": True,
            "recommendation_strength": recommendation,
            "recommendation_reason": "Fanfic/source review indicates the teen/source layer should stay non-intimate; adult/private use requires a separate adult-set branch.",
            "minimum_adult_age": 18,
            "years_after_source": max(2, adult_age - 16),
            "canon_collection_required_first": True,
            "plausible_transition_allowed": True,
            "transition_must_be_non_explicit": True,
            "teen_period_private_or_adult_content_blocked": True,
            "adult_branch_label_required": True,
            "direct_minor_image_age_up_for_private_adult_use_blocked": True,
            "adult_avatar_requires_original_or_adult_reference": True,
            "notes": "The adult branch is a branch, not canon. The transition from teen/source material must stay non-explicit.",
        },
        "inspiration_reference": {
            "has_inspiration": False,
            "reference_text": "",
            "inspiration_only_not_identity": True,
            "ambiguous_reference": False,
            "clarification_required": False,
            "clarification_question": "",
            "selected_version_or_era": "",
            "must_make_original_different": True,
        },
        "avatar_plan": {
            "avatar_required_now": False,
            "avatar_mode": "adult_branch_original_design_later",
            "reconstruct_specific_likeness": False,
            "voice_clone_requested": False,
            "notes": "Use adult branch/original design rules. Do not directly transform minor source images for private adult use.",
        },
        "privacy_plan": {
            "activation_visibility": "restricted",
            "owner_only_activation": False,
            "can_access_kira_private_memory": False,
            "can_access_lisa_private_memory": False,
            "can_access_robert_private_memory": False,
            "can_access_private_creative_libraries": False,
        },
        "adult_policy": {
            "adult_intimacy_requested": False,
            "all_participants_adult_coded_required": True,
            "minor_or_unclear_participant_block": True,
            "real_living_person_adult_clone_blocked_without_permission": True,
            "private_adult_original_required_for_private_adult_use": False,
        },
        "memory_policy": {
            "temporary_ai_memory_scope": "adult_fanfic_variant_branch_plan_only",
            "does_not_create_kira_lisa_memory": True,
            "does_not_update_base_profile_from_private_instance": True,
            "conversation_logs_not_trusted_memory": True,
        },
        "status": "draft",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a draft request for a separate adult fanfic TemporaryAI branch.")
    parser.add_argument("--character-id", required=True)
    parser.add_argument("--source-file", required=True, help="File name or source_path from character_discovery_brief.json.")
    parser.add_argument("--adult-age", type=int, default=21)
    parser.add_argument("--requested-by", default="real_robert")
    parser.add_argument("--brief", default=str(DEFAULT_DISCOVERY_BRIEF))
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    brief_path = Path(args.brief)
    if not brief_path.is_absolute():
        brief_path = PROJECT_ROOT / brief_path
    request = build_adult_fanfic_variant_request(
        _load_json(brief_path),
        character_id=args.character_id,
        source_file=args.source_file,
        adult_age=args.adult_age,
        requested_by=args.requested_by,
    )

    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path
    else:
        output_path = DEFAULT_OUTPUT_DIR / f"{request['request_id']}.draft.json"

    _write_json(output_path, request)
    print(f"Wrote {output_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
