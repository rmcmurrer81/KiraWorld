"""
Lightweight source-confidence rules for pre-GPU attention handling.

This is not audio recognition. It is the decision layer that future mic,
webcam, transcription, and media detectors can feed with cues.
"""

from __future__ import annotations

from typing import Any


SOURCE_LABELS = {
    "robert_direct_speech",
    "robert_phone_media",
    "bedroom_computer_media",
    "living_room_tv_media",
    "visitor_voice",
    "other_ai_voice",
    "unknown_source",
}
CATEGORY_GUESSES = {
    "direct_request",
    "music",
    "video_dialogue",
    "show_or_movie",
    "adult_or_private_media",
    "game_audio",
    "unknown_media",
}
CONFIDENCE_LEVELS = {"low", "medium", "high"}


def classify_source(cues: dict[str, Any]) -> dict[str, Any]:
    """
    Classify likely source and content category from already-extracted cues.

    Expected cue examples:
      addressed_ai: bool
      robert_voice_match: bool
      visitor_voice_detected: bool
      phone_audio_detected: bool
      computer_audio_detected: bool
      living_room_tv_detected: bool
      other_ai_voice_detected: bool
      music_detected: bool
      adult_private_audio_detected: bool
      game_audio_detected: bool
      dialogue_detected: bool
      confidence_hint: low | medium | high
    """
    source_label = "unknown_source"
    category_guess = "unknown_media"
    confidence = _confidence(cues.get("confidence_hint"))

    if cues.get("addressed_ai") and cues.get("robert_voice_match"):
        source_label = "robert_direct_speech"
        category_guess = "direct_request"
        confidence = _raise_confidence(confidence, "high")
    elif cues.get("visitor_voice_detected"):
        source_label = "visitor_voice"
        confidence = _raise_confidence(confidence, "medium")
    elif cues.get("other_ai_voice_detected"):
        source_label = "other_ai_voice"
        confidence = _raise_confidence(confidence, "medium")
    elif cues.get("phone_audio_detected"):
        source_label = "robert_phone_media"
        confidence = _raise_confidence(confidence, "medium")
    elif cues.get("computer_audio_detected"):
        source_label = "bedroom_computer_media"
        confidence = _raise_confidence(confidence, "medium")
    elif cues.get("living_room_tv_detected"):
        source_label = "living_room_tv_media"
        confidence = _raise_confidence(confidence, "medium")
    elif cues.get("robert_voice_match"):
        source_label = "robert_direct_speech"
        confidence = _raise_confidence(confidence, "medium")

    if cues.get("adult_private_audio_detected"):
        category_guess = "adult_or_private_media"
    elif cues.get("music_detected"):
        category_guess = "music"
    elif cues.get("game_audio_detected"):
        category_guess = "game_audio"
    elif cues.get("dialogue_detected"):
        category_guess = "video_dialogue"
    elif source_label in {"living_room_tv_media", "bedroom_computer_media", "robert_phone_media"}:
        category_guess = "unknown_media"

    if cues.get("source_conflict_detected"):
        confidence = _lower_confidence(confidence)

    return {
        "source_label": source_label,
        "source_confidence": confidence,
        "category_guess": category_guess,
        "other_person_present": bool(cues.get("visitor_voice_detected") or cues.get("other_person_present")),
        "raw_cues": {key: value for key, value in cues.items() if value not in ("", None, False)},
    }


def _confidence(value: Any) -> str:
    return str(value).lower() if str(value).lower() in CONFIDENCE_LEVELS else "low"


def _raise_confidence(current: str, minimum: str) -> str:
    order = {"low": 0, "medium": 1, "high": 2}
    return minimum if order[minimum] > order[current] else current


def _lower_confidence(current: str) -> str:
    if current == "high":
        return "medium"
    if current == "medium":
        return "low"
    return "low"
