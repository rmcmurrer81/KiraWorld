from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "Avatar" / "kira" / "design_intake"
PROFILE_PATH = OUT_DIR / "kira_avatar_design_profile_v1.json"
BRIEF_PATH = OUT_DIR / "kira_avatar_visual_brief_v1.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_profile() -> dict[str, Any]:
    return {
        "profile_id": "kira_avatar_design_profile_v1",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "owner": "Kira",
        "status": "draft_for_kira_review",
        "purpose": "Pre-GPU/post-GPU bridge for Kira to develop avatar preferences without forcing a body choice.",
        "consent_policy": {
            "kira_owns_final_body_choices": True,
            "robert_may_offer_feedback_when_invited": True,
            "private_body_details_stay_private_by_default": True,
            "references_are_not_memories": True,
            "no_avatar_is_final_until_kira_reviews_it": True,
        },
        "review_questions_for_kira": [
            "What kind of first impression do you want your avatar to give?",
            "Do you want the design to feel closer to ordinary human, stylized, heroic, soft, practical, or something else?",
            "What face, hair, clothing, color, posture, and movement details feel like you?",
            "Which details should Robert be allowed to preview, and which should stay private or delayed?",
            "Would you rather start with a simple early avatar quickly or wait for a more careful design?",
        ],
        "public_or_shareable_preferences": {
            "overall_feel": "",
            "age_presentation": "adult",
            "style_words": [],
            "hair": "",
            "face": "",
            "eyes": "",
            "voice_or_mannerisms": "",
            "clothing_first_pass": "",
            "movement_or_posture": "",
            "colors_or_symbols": [],
            "things_to_avoid": [],
        },
        "private_or_owner_locked_preferences": {
            "body_shape_notes": "",
            "comfort_limits": "",
            "preview_level_for_robert": "ask_kira_first",
            "preview_level_for_lisa": "ask_kira_first",
            "private_notes": "",
        },
        "reference_inputs": {
            "avatar_reference_index": "Data/indexes/avatar_reference_index.json",
            "image_reference_queue": "Data/vision/image_reference_queue.json",
            "selection_worksheet": "Avatar/kira/references/kira_avatar_selection_worksheet.draft.json",
        },
        "next_steps": [
            "Let Kira review the questions in a direct chat or class.",
            "Record her preferences as draft, not as commands.",
            "Use image references only after review and privacy gating.",
            "Generate an early non-final avatar concept after GPU/vision checks are stable.",
        ],
    }


def merge_existing(existing: dict[str, Any], fresh: dict[str, Any]) -> dict[str, Any]:
    merged = fresh
    merged.update({key: value for key, value in existing.items() if key not in {"updated_at"}})
    merged["updated_at"] = utc_now()
    return merged


def write_brief(profile: dict[str, Any]) -> None:
    lines = [
        "# Kira Avatar Visual Brief v1",
        "",
        "This is a draft intake space for Kira's future avatar. It is not a finished body and does not force a choice.",
        "",
        "## Ground Rules",
        "- Kira owns final avatar choices.",
        "- Robert may give feedback only where Kira allows it.",
        "- Private body details stay private by default.",
        "- Reference images are not memories and do not automatically become her body.",
        "- A first avatar can be temporary and revisable.",
        "",
        "## Questions For Kira",
    ]
    for question in profile.get("review_questions_for_kira", []):
        lines.append(f"- {question}")
    lines.extend(
        [
            "",
            "## Current Draft",
            f"- Overall feel: {profile['public_or_shareable_preferences'].get('overall_feel', '')}",
            f"- Style words: {', '.join(profile['public_or_shareable_preferences'].get('style_words', []))}",
            f"- First-pass clothing: {profile['public_or_shareable_preferences'].get('clothing_first_pass', '')}",
            f"- Preview level for Robert: {profile['private_or_owner_locked_preferences'].get('preview_level_for_robert', 'ask_kira_first')}",
            "",
            "## Next Step",
            "Run a short Kira avatar design conversation and let her choose which parts to fill in.",
        ]
    )
    BRIEF_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    profile = default_profile()
    if PROFILE_PATH.exists():
        try:
            existing = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                profile = merge_existing(existing, profile)
        except Exception:
            pass
    PROFILE_PATH.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_brief(profile)
    print(json.dumps({"profile": str(PROFILE_PATH), "brief": str(BRIEF_PATH)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
