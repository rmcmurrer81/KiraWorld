"""
Microphone metadata adapter.

This module is metadata-only. It can turn measured or simulated audio features
into perception cues without storing raw audio.
"""

from __future__ import annotations

import math
from typing import Any, Iterable


def analyze_audio_metadata(
    *,
    rms_level: float,
    peak_level: float,
    speech_probability: float = 0.0,
    music_probability: float = 0.0,
    adult_private_probability: float = 0.0,
    robert_voice_probability: float = 0.0,
    visitor_voice_probability: float = 0.0,
    phone_audio_probability: float = 0.0,
    tv_audio_probability: float = 0.0,
    addressed_ai_probability: float = 0.0,
) -> dict[str, Any]:
    """Convert privacy-safe audio metadata into perception cues."""
    confidence_hint = "low"
    if max(speech_probability, music_probability, robert_voice_probability, phone_audio_probability, tv_audio_probability) >= 0.75:
        confidence_hint = "high"
    elif max(speech_probability, music_probability, robert_voice_probability, phone_audio_probability, tv_audio_probability) >= 0.45:
        confidence_hint = "medium"

    return {
        "audio_present": rms_level > 0.02 or peak_level > 0.05,
        "speech_detected": speech_probability >= 0.45,
        "music_detected": music_probability >= 0.55,
        "adult_private_audio_detected": adult_private_probability >= 0.6,
        "robert_voice_match": robert_voice_probability >= 0.65,
        "visitor_voice_detected": visitor_voice_probability >= 0.55,
        "phone_audio_detected": phone_audio_probability >= 0.55,
        "living_room_tv_detected": tv_audio_probability >= 0.55,
        "addressed_ai": addressed_ai_probability >= 0.6,
        "dialogue_detected": speech_probability >= 0.45,
        "confidence_hint": confidence_hint,
        "metadata": {
            "rms_level": _round(rms_level),
            "peak_level": _round(peak_level),
            "speech_probability": _round(speech_probability),
            "music_probability": _round(music_probability),
            "adult_private_probability": _round(adult_private_probability),
            "robert_voice_probability": _round(robert_voice_probability),
            "visitor_voice_probability": _round(visitor_voice_probability),
            "phone_audio_probability": _round(phone_audio_probability),
            "tv_audio_probability": _round(tv_audio_probability),
            "addressed_ai_probability": _round(addressed_ai_probability),
            "raw_audio_stored": False,
        },
    }


def analyze_sample_levels(samples: Iterable[float]) -> dict[str, float]:
    """Calculate simple level metadata from normalized audio samples."""
    values = [float(sample) for sample in samples]
    if not values:
        return {"rms_level": 0.0, "peak_level": 0.0}
    peak = max(abs(sample) for sample in values)
    rms = math.sqrt(sum(sample * sample for sample in values) / len(values))
    return {"rms_level": _round(rms), "peak_level": _round(peak)}


def capture_microphone_metadata(duration_seconds: float = 1.0, sample_rate: int = 16000) -> dict[str, Any]:
    """
    Optional real microphone metadata probe.

    Requires the optional `sounddevice` package. This function records only
    transient samples, computes levels, and returns metadata. It does not save
    raw audio.
    """
    try:
        import sounddevice as sd  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on local install
        return {
            "available": False,
            "error": f"sounddevice unavailable: {exc}",
            "raw_audio_stored": False,
        }

    frame_count = max(1, int(duration_seconds * sample_rate))
    recording = sd.rec(frame_count, samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()
    flat_samples = [float(row[0]) for row in recording]
    levels = analyze_sample_levels(flat_samples)
    return {
        "available": True,
        **levels,
        "raw_audio_stored": False,
        "duration_seconds": duration_seconds,
        "sample_rate": sample_rate,
    }


def _round(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)
