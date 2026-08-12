"""
Create a grounded reading reaction and refresh reading tastes.

This is a lightweight 16GB tool: it records Kira/Lisa's reaction to a known
reading source without turning source material into lived memory.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from update_reading_tastes import DEFAULT_OUTPUT_DIR, DEFAULT_REACTION_DIR, build_profile
from validate_reading_reaction import validate_reading_reaction


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STANCE_AFFINITY = {
    "love": 0.9,
    "like": 0.6,
    "curious": 0.25,
    "neutral": 0.0,
    "mixed": 0.0,
    "cooling": -0.25,
    "outgrown": -0.45,
    "dislike": -0.65,
}


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    return re.sub(r"_+", "_", cleaned) or "untitled"


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _title_from_source_path(source_path: str) -> str:
    return Path(source_path.replace("\\", "/")).stem


def make_reading_reaction(
    reader: str,
    source_path: str,
    title: str = "",
    unit_label: str = "current_position",
    progress_percent: float = 0.0,
    stance: str = "curious",
    favorite_moments: list[str] | None = None,
    emotions: list[str] | None = None,
    reasons: list[str] | None = None,
    questions: list[str] | None = None,
    curiosity_triggers: list[str] | None = None,
    wants_to_keep_private: bool = True,
    source_authority: str = "raw_library_source",
) -> dict[str, Any]:
    normalized_source = source_path.replace("\\", "/")
    clean_title = title.strip() or _title_from_source_path(normalized_source)
    now = datetime.now(timezone.utc).isoformat()
    stance = stance.strip().lower()
    favorite_moments = favorite_moments or []
    emotions = emotions or []
    reasons = reasons or []
    questions = questions or []
    curiosity_triggers = curiosity_triggers or []
    reaction = {
        "reaction_id": f"reading_reaction_{reader}_{_slug(clean_title)}_{_slug(unit_label)}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "created_at": now,
        "reader": reader,
        "source": {
            "title": clean_title,
            "source_path": normalized_source,
            "source_authority": source_authority,
            "source_material_remains_source": True,
        },
        "reading_position": {
            "unit_type": "section",
            "unit_label": unit_label,
            "approximate_progress_percent": progress_percent,
        },
        "reaction": {
            "favorite_moments": favorite_moments,
            "emotions": emotions,
            "questions": questions,
            "discomfort_or_fears": [],
            "curiosity_triggers": curiosity_triggers,
            "wants_to_discuss_with": [],
            "wants_to_keep_private": wants_to_keep_private,
        },
        "preference_signal": {
            "stance": stance,
            "current_affinity": STANCE_AFFINITY.get(stance, 0.0),
            "interest_delta": 0.0,
            "reasons": reasons,
            "may_change_later": True,
            "older_reactions_can_be_reinterpreted": True,
        },
        "imagination": {
            "imagination_allowed": True,
            "slowly_develops_over_time": True,
            "pictured_places": [],
            "pictured_people": [],
            "pictured_objects": [],
            "atmosphere": [],
            "sensory_details": {
                "sight": [],
                "sound": [],
                "texture": [],
                "smell": [],
                "emotion_tone": [],
            },
            "certainty": "imagined_not_confirmed",
            "may_influence_dreams_or_creative_projects": True,
            "may_become_notebook_world_seed_if_chosen": True,
        },
        "dream_and_fantasy_influence": {
            "stories_may_influence_dreams": True,
            "stories_may_influence_fantasies": True,
            "stories_may_influence_hopes": True,
            "stories_may_influence_fears": True,
            "influence_is_indirect": True,
            "dreams_remain_not_real_events": True,
            "fantasies_remain_private_inner_life_unless_shared": True,
            "fantasies_do_not_prove_consent_or_relationship_status": True,
            "reader_controls_whether_to_share": True,
        },
        "memory_policy": {
            "may_remember_story_moment": True,
            "may_remember_own_reaction": True,
            "does_not_become_lived_memory": True,
            "does_not_create_temporary_ai_automatically": True,
            "does_not_create_notebook_world_automatically": True,
            "source_and_imagination_must_be_labeled": True,
        },
        "privacy": {
            "default_visibility": "reader_private" if wants_to_keep_private else "shareable_summary",
            "robert_can_see_without_permission": False,
            "other_ai_can_see_without_permission": False,
            "shareable_summary_allowed_if_reader_chooses": True,
        },
        "status": "active",
    }
    errors = validate_reading_reaction(reaction)
    if errors:
        raise ValueError("Invalid reading reaction: " + "; ".join(errors))
    return reaction


def write_reading_reaction(
    reaction: dict[str, Any],
    reaction_dir: Path = DEFAULT_REACTION_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, Path]:
    reaction_dir.mkdir(parents=True, exist_ok=True)
    reaction_path = reaction_dir / f"{reaction['reaction_id']}.json"
    reaction_path.write_text(json.dumps(reaction, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    profile = build_profile(str(reaction["reader"]), reaction_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_path = output_dir / f"reading_taste_profile_{reaction['reader']}.json"
    profile_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return reaction_path, profile_path


def describe_written(reaction_path: Path, profile_path: Path) -> str:
    return f"Reading reaction written: {_relative(reaction_path)}\nReading taste profile updated: {_relative(profile_path)}"
