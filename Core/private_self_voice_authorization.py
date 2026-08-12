from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _project_file(root: Path, value: object, *, suffix: str) -> Path | None:
    relative = str(value or "").strip().replace("\\", "/")
    if not relative or Path(relative).is_absolute() or not relative.lower().endswith(suffix.lower()):
        return None
    try:
        path = (root / relative).resolve(strict=True)
        path.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return path if path.is_file() else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_private_self_voice_authorization(
    candidate_id: str,
    candidate_profile: dict[str, Any],
    *,
    project_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Fail closed unless an owner self-voice is bound to reviewed local audio.

    This validator authorizes only a private text/voice conversation.  It does
    not activate a person, body, world presence, life loop, microphone, webcam,
    external messaging, or public/official voice use.
    """

    root = Path(project_root).resolve()
    reasons: list[str] = []
    voice_section = candidate_profile.get("voice_and_behavior")
    if not isinstance(voice_section, dict):
        voice_section = {}

    authorization_path = _project_file(
        root,
        voice_section.get("voice_authorization"),
        suffix=".json",
    )
    voice_profile_path = _project_file(
        root,
        voice_section.get("voice_profile"),
        suffix=".json",
    )
    if authorization_path is None:
        reasons.append("authorization_file_missing_or_outside_project")
    if voice_profile_path is None:
        reasons.append("voice_profile_missing_or_outside_project")

    authorization = _read_json(authorization_path) if authorization_path else {}
    voice_profile = _read_json(voice_profile_path) if voice_profile_path else {}
    binding = authorization.get("binding") if isinstance(authorization.get("binding"), dict) else {}
    scope = authorization.get("scope") if isinstance(authorization.get("scope"), dict) else {}
    allowed = authorization.get("allowed") if isinstance(authorization.get("allowed"), dict) else {}
    prohibited = authorization.get("not_authorized") if isinstance(authorization.get("not_authorized"), dict) else {}
    authorized_by = (
        authorization.get("authorized_by")
        if isinstance(authorization.get("authorized_by"), dict)
        else {}
    )

    if authorization.get("status") != "approved_for_private_local_text_voice_chat":
        reasons.append("authorization_status_not_approved")
    if scope.get("candidate_id") != candidate_id:
        reasons.append("authorization_candidate_mismatch")
    if authorized_by.get("self_voice_subject") is not True:
        reasons.append("self_voice_subject_approval_missing")
    if allowed.get("private_local_text_voice_chat") is not True:
        reasons.append("private_text_voice_scope_missing")
    for key in ("body_activation", "world_presence", "life_loop", "microphone", "webcam", "public_release"):
        if prohibited.get(key) is not True:
            reasons.append(f"required_scope_boundary_missing:{key}")

    voice_id = str(voice_profile.get("voice_id") or "").strip()
    if not voice_id or binding.get("voice_profile_id") != voice_id:
        reasons.append("voice_profile_id_mismatch")
    status = voice_profile.get("status") if isinstance(voice_profile.get("status"), dict) else {}
    if status.get("ready_for_text_tts") is not True:
        reasons.append("voice_profile_not_ready_for_text_tts")
    source_audio = (
        voice_profile.get("source_audio")
        if isinstance(voice_profile.get("source_audio"), dict)
        else {}
    )
    reference_rel = str(source_audio.get("approved_reference_wav") or "").replace("\\", "/")
    if binding.get("approved_reference_wav") != reference_rel:
        reasons.append("approved_reference_path_mismatch")
    if int(source_audio.get("reviewed_target_clip_count") or 0) < 1:
        reasons.append("no_reviewed_target_clips")
    if float(source_audio.get("reviewed_target_seconds") or 0.0) < 20.0:
        reasons.append("less_than_20_reviewed_seconds")

    reference_path = _project_file(root, reference_rel, suffix=".wav")
    duration_seconds = 0.0
    wav_sha256 = ""
    if reference_path is None:
        reasons.append("approved_reference_wav_missing_or_outside_project")
    else:
        try:
            with wave.open(str(reference_path), "rb") as audio:
                frame_rate = audio.getframerate()
                duration_seconds = audio.getnframes() / frame_rate if frame_rate else 0.0
                if audio.getnchannels() != 1:
                    reasons.append("approved_reference_not_mono")
                if audio.getsampwidth() != 2:
                    reasons.append("approved_reference_not_pcm16")
                if audio.getcomptype() != "NONE":
                    reasons.append("approved_reference_is_compressed")
        except (OSError, EOFError, wave.Error):
            reasons.append("approved_reference_invalid_wav")
        if duration_seconds < 20.0:
            reasons.append("approved_reference_duration_too_short")
        wav_sha256 = _sha256(reference_path)
        if binding.get("approved_reference_sha256") != wav_sha256:
            reasons.append("approved_reference_hash_mismatch")

    return {
        "allowed": not reasons,
        "candidate_id": candidate_id,
        "voice_profile_id": voice_id,
        "engine": str(status.get("current_playback_engine") or ""),
        "approved_reference_wav": reference_rel,
        "approved_reference_sha256": wav_sha256,
        "reviewed_target_clip_count": int(source_audio.get("reviewed_target_clip_count") or 0),
        "reviewed_target_seconds": float(source_audio.get("reviewed_target_seconds") or 0.0),
        "wav_duration_seconds": round(duration_seconds, 3),
        "reasons": reasons,
        "scope": "private_local_text_voice_chat_only",
    }

