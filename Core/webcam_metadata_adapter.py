"""
Webcam metadata adapter.

This module is metadata-only. It can turn measured or simulated frame features
into perception cues without storing raw images or video.
"""

from __future__ import annotations

from typing import Any


def analyze_frame_metadata(
    *,
    brightness: float,
    motion_score: float = 0.0,
    person_probability: float = 0.0,
    robert_face_probability: float = 0.0,
    other_person_probability: float = 0.0,
    phone_visible_probability: float = 0.0,
    screen_visible_probability: float = 0.0,
) -> dict[str, Any]:
    """Convert privacy-safe video metadata into perception cues."""
    confidence_hint = "low"
    if max(person_probability, robert_face_probability, other_person_probability, phone_visible_probability, screen_visible_probability) >= 0.75:
        confidence_hint = "high"
    elif max(person_probability, robert_face_probability, other_person_probability, phone_visible_probability, screen_visible_probability) >= 0.45:
        confidence_hint = "medium"

    return {
        "visual_present": brightness > 0.05,
        "motion_detected": motion_score >= 0.2,
        "person_visible": person_probability >= 0.5,
        "robert_visible": robert_face_probability >= 0.65,
        "other_person_present": other_person_probability >= 0.55,
        "phone_visible": phone_visible_probability >= 0.55,
        "screen_visible": screen_visible_probability >= 0.55,
        "phone_audio_detected": phone_visible_probability >= 0.65,
        "living_room_tv_detected": screen_visible_probability >= 0.65,
        "confidence_hint": confidence_hint,
        "metadata": {
            "brightness": _round(brightness),
            "motion_score": _round(motion_score),
            "person_probability": _round(person_probability),
            "robert_face_probability": _round(robert_face_probability),
            "other_person_probability": _round(other_person_probability),
            "phone_visible_probability": _round(phone_visible_probability),
            "screen_visible_probability": _round(screen_visible_probability),
            "raw_frame_stored": False,
        },
    }


def capture_webcam_metadata(camera_index: int = 0) -> dict[str, Any]:
    """
    Optional real webcam metadata probe.

    Requires the optional `opencv-python` package. Captures a transient frame,
    computes simple brightness metadata, and releases the frame. It does not
    save raw images or video.
    """
    try:
        import cv2  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on local install
        return {
            "available": False,
            "error": f"opencv-python unavailable: {exc}",
            "raw_frame_stored": False,
        }

    camera = cv2.VideoCapture(camera_index)
    try:
        if not camera.isOpened():
            return {
                "available": False,
                "error": f"camera {camera_index} could not be opened",
                "raw_frame_stored": False,
            }
        ok, frame = camera.read()
        if not ok:
            return {
                "available": False,
                "error": "camera frame read failed",
                "raw_frame_stored": False,
            }
        brightness = float(frame.mean()) / 255.0
        height, width = frame.shape[:2]
        return {
            "available": True,
            "brightness": round(max(0.0, min(1.0, brightness)), 4),
            "width": int(width),
            "height": int(height),
            "raw_frame_stored": False,
        }
    finally:
        camera.release()


def _round(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)
