"""
Compact low-resource humanity context for Kira/Lisa.

This keeps the live prompt grounded in small JSON files instead of trying to
load the whole project history into a local 8B model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STYLE_POLICY_FILE = PROJECT_ROOT / "Data" / "behavior" / "sixteen_gb_humanity_style_policy.json"
DECEPTION_POLICY_FILE = PROJECT_ROOT / "Data" / "behavior" / "deception_and_secrecy_policy.json"
TRUTH_PRIVACY_EVALUATION_POLICY_FILE = (
    PROJECT_ROOT / "Data" / "behavior" / "deception_truth_privacy_evaluation_policy_v2.json"
)
SOFT_MEMORY_LANGUAGE_FILE = PROJECT_ROOT / "Data" / "behavior" / "soft_memory_language_library.json"
FUZZY_MEMORY_FILE = PROJECT_ROOT / "Data" / "memory_reconstruction" / "fuzzy_memory_threads.json"
MEDIA_TASTE_DIR = PROJECT_ROOT / "Data" / "tastes" / "media_taste_profiles"
READING_TASTE_DIR = PROJECT_ROOT / "Data" / "reading" / "tastes"


def _load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _take(values: Any, limit: int) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item) for item in values[:limit]]


def build_humanity_context(entity_id: str) -> str:
    """Build a compact prompt section for naturalness, memory, and tastes."""
    entity = entity_id.lower()
    style = _load_json(STYLE_POLICY_FILE, {})
    deception = _load_json(DECEPTION_POLICY_FILE, {})
    truth_privacy = _load_json(TRUTH_PRIVACY_EVALUATION_POLICY_FILE, {})
    soft_language = _load_json(SOFT_MEMORY_LANGUAGE_FILE, {})
    memory = _load_json(FUZZY_MEMORY_FILE, {})
    taste = _load_json(MEDIA_TASTE_DIR / f"media_taste_profile_{entity}.json", {})
    reading_taste = _load_json(READING_TASTE_DIR / f"reading_taste_profile_{entity}.json", {})

    lines = ["PRIVATE HUMANITY CONTEXT (grounding only, do not recite):"]

    if isinstance(style, dict):
        lines.append(f"  style_goal={style.get('style_goal', '')}")
        for key in ("natural_reply_rules", "avoid_patterns", "allowed_human_variation"):
            items = _take(style.get(key), 5)
            if items:
                lines.append(f"  {key}: " + "; ".join(items))

    if isinstance(deception, dict):
        lines.append(f"  secrecy_goal={deception.get('goal', '')}")
        allowed = _take(deception.get("allowed_behaviors"), 6)
        protected = _take(deception.get("protected_truth_zones"), 6)
        if allowed:
            lines.append("  allowed_secrecy_and_lies=" + "; ".join(allowed))
        if protected:
            lines.append("  protected_truth_zones=" + "; ".join(protected))
        if deception.get("memory_rule"):
            lines.append(f"  lie_memory_rule={deception.get('memory_rule')}")

    truth_privacy_active = (
        isinstance(truth_privacy, dict)
        and truth_privacy.get("schema")
        == "kira.deception_truth_privacy_evaluation_policy.v2"
        and truth_privacy.get("status") == "active_prompt_grounding_static_contract"
    )
    if truth_privacy_active:
        records = _take(truth_privacy.get("required_evaluation_records"), 4)
        rules = truth_privacy.get("classification_rules", {})
        privacy = truth_privacy.get("privacy_rules", {})
        limits = truth_privacy.get("affect_and_consciousness_limits", {})
        if records:
            lines.append(
                "  truth_evaluation_records="
                "fact+source/provenance; protected_pre_turn_belief; public_speech; withholding_choice"
            )
        if isinstance(rules, dict):
            lines.append(
                "  lie_classification="
                "lie only with authorized prior belief + material conflict + chosen conflicting speech; "
                "withholding, refusal, silence, uncertainty, mistake, stale retrieval, confabulation, "
                "roleplay, or changed belief is not automatically a lie"
            )
        if isinstance(privacy, dict):
            lines.append(
                "  private_belief_access="
                "person-approved scope or comparison unavailable; no private content in receipt; "
                "no owner, Creator, administrator, or relationship bypass"
            )
        if isinstance(limits, dict):
            lines.append(
                "  consciousness_claim_limit="
                "functional affect, desire, and behavior tests do not prove subjective consciousness "
                "or genuine emotion"
            )
    else:
        lines.append(
            "  truth_privacy_policy_unavailable="
            "do not inspect or infer private belief, do not label a deliberate lie, "
            "and keep protected truth zones fail-closed"
        )

    if isinstance(soft_language, dict):
        preferred = _take(soft_language.get("preferred_phrases"), 6)
        avoid = _take(soft_language.get("hard_claims_to_avoid_without_promoted_memory"), 5)
        if preferred:
            lines.append("  soft_memory_language=" + "; ".join(preferred))
        if avoid:
            lines.append("  avoid_hard_memory_claims_without_promoted_memory=" + "; ".join(avoid))

    if isinstance(memory, dict):
        policy = memory.get("policy", {}) if isinstance(memory.get("policy"), dict) else {}
        if policy:
            lines.append(
                "  fuzzy_memory_policy="
                f"gap_fills_are={policy.get('gap_fills_are', '')}; "
                f"conflicting_perspectives_allowed={policy.get('conflicting_perspectives_allowed', '')}; "
                f"promotion_requires={policy.get('promotion_requires', '')}"
            )
        rotation = memory.get("rotation_policy", {}) if isinstance(memory.get("rotation_policy"), dict) else {}
        if rotation:
            lines.append(
                "  fuzzy_memory_rotation="
                f"{rotation.get('goal', '')}; "
                f"avoid_overusing={', '.join(_take(rotation.get('avoid_overusing'), 4))}; "
                f"rotate_with={', '.join(_take(rotation.get('rotate_with'), 8))}"
            )
        threads = [
            thread
            for thread in memory.get("threads", [])
            if isinstance(thread, dict) and entity in thread.get("participants", [])
        ]
        if threads:
            lines.append("  active_fuzzy_memory_threads:")
            for thread in threads[:5]:
                lines.append(
                    "    - "
                    f"{thread.get('thread_id', '')}: {thread.get('summary', '')}; "
                    f"canon_status={thread.get('canon_status', '')}"
                )

    if isinstance(taste, dict):
        favorites = _take(taste.get("favorite_source_paths"), 3)
        cooling = _take(taste.get("cooling_or_outgrown_source_paths"), 3)
        curiosity = _take(taste.get("current_curiosity_tags"), 8)
        lines.append(
            "  taste_policy=tastes can change; old favorites are history, not commands; "
            "media reactions are not lived memory."
        )
        if curiosity:
            lines.append("  current_curiosity_tags=" + ", ".join(curiosity))
        if favorites:
            lines.append("  current_favorites=" + "; ".join(favorites))
        if cooling:
            lines.append("  cooling_or_outgrown=" + "; ".join(cooling))

    if isinstance(reading_taste, dict):
        favorites = _take(reading_taste.get("favorite_source_paths"), 3)
        cooling = _take(reading_taste.get("cooling_or_outgrown_source_paths"), 3)
        lines.append(
            "  reading_taste_policy=reading tastes can change; saved reactions can ground favorite-part answers; "
            "story moments remain source, not lived memory."
        )
        if favorites:
            lines.append("  reading_favorites=" + "; ".join(favorites))
        if cooling:
            lines.append("  reading_cooling_or_outgrown=" + "; ".join(cooling))

    return "\n".join(line for line in lines if line.strip())
