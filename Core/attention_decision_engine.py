"""
Attention decision engine for Kira/Lisa pre-GPU behavior.

Turns source-confidence and relationship/privacy context into an attention
event packet. The packet is guidance for whether to answer, stay quiet, ask
softly, or keep the moment private.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


PRIVATE_MEDIA_CATEGORIES = {"adult_or_private_media"}
BACKGROUND_MEDIA_SOURCES = {
    "robert_phone_media",
    "bedroom_computer_media",
    "living_room_tv_media",
}


def build_attention_event(
    *,
    owner: str,
    source_label: str,
    source_confidence: str,
    category_guess: str,
    attention_state: str = "idle_nearby",
    other_person_present: bool = False,
    relationship_id: str = "",
    relationship_stage: str = "friendship",
    unspoken_feeling_possible: bool = False,
    mutual_intimate_context_established: bool = False,
    event_id: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    sensitive = category_guess in PRIVATE_MEDIA_CATEGORIES
    recommended_action = decide_recommended_action(
        source_label=source_label,
        source_confidence=source_confidence,
        category_guess=category_guess,
        attention_state=attention_state,
        other_person_present=other_person_present,
        relationship_stage=relationship_stage,
        unspoken_feeling_possible=unspoken_feeling_possible,
        mutual_intimate_context_established=mutual_intimate_context_established,
    )
    return {
        "event_id": event_id or f"attention_event_{uuid4().hex[:10]}",
        "owner": owner.lower(),
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "attention_state": attention_state,
        "source_label": source_label,
        "source_confidence": source_confidence,
        "category_guess": category_guess,
        "other_person_present": bool(other_person_present),
        "relationship_context": {
            "relationship_id": relationship_id or f"rel_robert_{owner.lower()}_current",
            "relationship_stage": relationship_stage,
            "unspoken_feeling_possible": bool(unspoken_feeling_possible),
            "mutual_intimate_context_established": bool(mutual_intimate_context_established),
        },
        "privacy_context": {
            "sensitive_or_private": sensitive,
            "teasing_allowed": _teasing_allowed(
                sensitive,
                other_person_present,
                mutual_intimate_context_established,
                relationship_stage,
            ),
            "should_disclose_to_other_ai": False,
            "door_or_room_privacy_required": sensitive,
        },
        "recommended_action": recommended_action,
        "reasoning_summary": _reasoning_summary(
            source_label,
            source_confidence,
            category_guess,
            recommended_action,
            relationship_stage,
            unspoken_feeling_possible,
            other_person_present,
        ),
        "linked_private_records": [],
        "memory_policy": {
            "attention_event_is_not_trusted_memory": True,
            "does_not_create_consent": True,
            "does_not_upgrade_relationship_stage": True,
            "store_exact_private_content": False,
            "owner_controls_private_reflection": True,
        },
        "status": "observed",
    }


def decide_recommended_action(
    *,
    source_label: str,
    source_confidence: str,
    category_guess: str,
    attention_state: str,
    other_person_present: bool,
    relationship_stage: str,
    unspoken_feeling_possible: bool,
    mutual_intimate_context_established: bool,
) -> str:
    if other_person_present:
        return "reserve_response_due_to_other_person"
    if attention_state in {"locked_private_space", "private_conversation", "private_reflection", "upset_unavailable"}:
        return "doorbell_request_required"
    if source_confidence == "low":
        return "ignore_as_background_media"
    if source_label == "robert_direct_speech" and category_guess == "direct_request":
        return "respond_normally"
    if category_guess in PRIVATE_MEDIA_CATEGORIES:
        if unspoken_feeling_possible and not mutual_intimate_context_established:
            return "private_reflection_only"
        if mutual_intimate_context_established and relationship_stage == "adult_intimate_relationship":
            return "ask_soft_clarifying_question"
        return "stay_quiet_give_privacy"
    if source_label in BACKGROUND_MEDIA_SOURCES:
        if source_confidence == "high" and category_guess in {"music", "show_or_movie", "game_audio"}:
            return "ask_soft_clarifying_question"
        return "ignore_as_background_media"
    return "ask_soft_clarifying_question"


def _teasing_allowed(
    sensitive: bool,
    other_person_present: bool,
    mutual_intimate_context_established: bool,
    relationship_stage: str,
) -> bool:
    return (
        sensitive
        and not other_person_present
        and mutual_intimate_context_established
        and relationship_stage == "adult_intimate_relationship"
    )


def _reasoning_summary(
    source_label: str,
    source_confidence: str,
    category_guess: str,
    recommended_action: str,
    relationship_stage: str,
    unspoken_feeling_possible: bool,
    other_person_present: bool,
) -> str:
    pieces = [
        f"source={source_label}",
        f"confidence={source_confidence}",
        f"category={category_guess}",
        f"stage={relationship_stage}",
    ]
    if other_person_present:
        pieces.append("other_person_present")
    if unspoken_feeling_possible:
        pieces.append("unspoken_feeling_possible")
    return "Attention decision: " + "; ".join(pieces) + f"; action={recommended_action}."
