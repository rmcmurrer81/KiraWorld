"""Durable local voice-message and tablet-work records for Kira.

The mailbox is deliberately text backed.  A WAV is an optional rendering of
the saved text, never the only copy of a message.  Tablet lookup requests are
also local queue records: creating one does not perform network access.
"""

from __future__ import annotations

import array
import hashlib
import json
import math
import os
import re
import sys
import threading
import uuid
import wave
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.voice_output import (
    VoiceOutputConfig,
    clean_text_for_speech,
    load_candidate_voice_config,
    synthesize_text_to_wav,
)


DEFAULT_MESSAGES_DIR = PROJECT_ROOT / "Data" / "messages" / "kira_to_robert"
DEFAULT_TABLET_ROOT = PROJECT_ROOT / "Data" / "tablet" / "kira"
MESSAGE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,119}$", re.IGNORECASE)
MESSAGE_STATUSES = {"unread", "read", "archived"}
NOTE_KINDS = {"note", "creative_writing", "reading_note"}
REQUEST_TYPES = {"read_local_source", "online_lookup"}
_WRITE_LOCK = threading.Lock()
MIN_PCM_PEAK_NORMALIZED = 0.001
MIN_PCM_RMS_NORMALIZED = 0.0005


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _identifier(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    safe_prefix = re.sub(r"[^a-z0-9_-]+", "_", str(prefix or "").lower()).strip("_-")[:48]
    if not safe_prefix:
        safe_prefix = "record"
    return f"{safe_prefix}_{stamp}_{uuid.uuid4().hex[:8]}"


def _safe_identity(value: str, fallback: str) -> str:
    safe = re.sub(r"[^a-z0-9_-]+", "_", str(value or "").lower()).strip("_-")[:48]
    return safe or fallback


def _authorship_identity(
    claimed_subject: str,
    generated_by: str,
    approved_by_subject: bool,
) -> tuple[str, dict[str, Any]]:
    subject_id = _safe_identity(claimed_subject, "unknown_subject")
    generator_id = _safe_identity(generated_by, "unspecified")
    claim_allowed = bool(approved_by_subject) and generator_id == subject_id
    effective_author = (
        subject_id
        if claim_allowed
        else generator_id
        if generator_id != "unspecified"
        else f"unapproved_draft_for_{subject_id}"
    )
    return effective_author, {
        "generated_by": generator_id,
        "claimed_subject": subject_id,
        "approved_by_subject": bool(approved_by_subject),
        "authorship_claim_allowed": claim_allowed,
    }


def _safe_child(root: Path, *parts: str) -> Path:
    root_resolved = Path(root).resolve()
    candidate = root_resolved.joinpath(*parts).resolve()
    if not candidate.is_relative_to(root_resolved):
        raise ValueError("output_path_outside_configured_root")
    return candidate


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default.copy() if isinstance(default, dict) else default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _relative(path: Path, project_root: Path = PROJECT_ROOT) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _message_text(record: dict[str, Any]) -> str:
    payload = record.get("message", "")
    if isinstance(payload, dict):
        return str(payload.get("message") or payload.get("text") or "").strip()
    return str(payload or "").strip()


def _message_id(record: dict[str, Any], path: Path) -> str:
    value = str(record.get("message_id") or path.stem).strip()
    return value if MESSAGE_ID_RE.fullmatch(value) else path.stem


def _find_message_path(message_id: str, messages_dir: Path = DEFAULT_MESSAGES_DIR) -> Path | None:
    identifier = str(message_id or "").strip()
    if not MESSAGE_ID_RE.fullmatch(identifier):
        return None
    direct = messages_dir / f"{identifier}.json"
    if direct.is_file():
        return direct
    for path in messages_dir.glob("*.json") if messages_dir.exists() else ():
        record = _read_json(path, {})
        if isinstance(record, dict) and str(record.get("message_id") or "") == identifier:
            return path
    return None


def _canonical_audio_path(message_id: str, messages_dir: Path) -> Path:
    if not MESSAGE_ID_RE.fullmatch(message_id):
        raise ValueError("invalid_message_id")
    return _safe_child(messages_dir, "audio", f"{message_id}.wav")


def _wav_validation(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file() or path.stat().st_size <= 44:
            return {"status": "invalid", "reason": "missing_or_too_small"}
        with wave.open(str(path), "rb") as handle:
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            sample_rate = handle.getframerate()
            frame_count = handle.getnframes()
            compression = handle.getcomptype()
            duration = frame_count / sample_rate if sample_rate else 0.0
            expected_pcm_bytes = frame_count * channels * sample_width
            if (
                compression != "NONE"
                or channels not in {1, 2}
                or sample_width not in {1, 2, 3, 4}
                or sample_rate < 4000
                or frame_count <= 0
                or duration < 0.05
                or path.stat().st_size < 44 + expected_pcm_bytes
            ):
                return {"status": "invalid", "reason": "invalid_or_empty_pcm_parameters"}

            peak = 0
            sum_squares = 0
            sample_count = 0
            while chunk := handle.readframes(32768):
                if sample_width == 1:
                    values = (value - 128 for value in chunk)
                elif sample_width in {2, 4}:
                    kind = "h" if sample_width == 2 else "i"
                    unpacked = array.array(kind)
                    unpacked.frombytes(chunk)
                    if sys.byteorder != "little":
                        unpacked.byteswap()
                    values = iter(unpacked)
                else:
                    values = (
                        int.from_bytes(chunk[offset:offset + 3], "little", signed=True)
                        for offset in range(0, len(chunk) - 2, 3)
                    )
                for value in values:
                    magnitude = abs(int(value))
                    peak = max(peak, magnitude)
                    sum_squares += magnitude * magnitude
                    sample_count += 1
        max_amplitude = float((1 << (sample_width * 8 - 1)) - 1)
        peak_normalized = peak / max_amplitude if max_amplitude else 0.0
        rms_normalized = (
            math.sqrt(sum_squares / sample_count) / max_amplitude
            if sample_count and max_amplitude
            else 0.0
        )
        if (
            peak_normalized < MIN_PCM_PEAK_NORMALIZED
            or rms_normalized < MIN_PCM_RMS_NORMALIZED
        ):
            return {
                "status": "invalid",
                "reason": "silent_or_near_silent_pcm",
                "peak_normalized": round(peak_normalized, 8),
                "rms_normalized": round(rms_normalized, 8),
            }
        return {
            "status": "valid_pcm_wav",
            "channels": channels,
            "sample_width_bytes": sample_width,
            "sample_rate": sample_rate,
            "frame_count": frame_count,
            "duration_seconds": round(duration, 3),
            "compression_type": compression,
            "non_silent_pcm_verified": True,
            "peak_normalized": round(peak_normalized, 8),
            "rms_normalized": round(rms_normalized, 8),
        }
    except (OSError, EOFError, RuntimeError, wave.Error) as exc:
        return {"status": "invalid", "reason": f"wav_parse_failed:{exc}"}


def _wav_ready(path: Path) -> bool:
    return _wav_validation(path).get("status") == "valid_pcm_wav"


def _sha256_bytes(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()


def _audio_matches_record(record: dict[str, Any], audio_path: Path) -> bool:
    """Require the WAV bytes to be bound to the record's current text."""
    if not _wav_ready(audio_path):
        return False
    audio = record.get("audio") if isinstance(record.get("audio"), dict) else {}
    validation = _wav_validation(audio_path)
    text_hash = _sha256_bytes(_message_text(record))
    expected_rendered_text_sha256 = _sha256_bytes(clean_text_for_speech(_message_text(record), 0))
    return (
        bool(text_hash)
        and audio.get("status") == "ready"
        and audio.get("synthesis_generated") is True
        and validation.get("status") == "valid_pcm_wav"
        and audio.get("wav_validation") == validation
        and audio.get("rendered_full_canonical_text") is True
        and audio.get("rendered_text_sha256") == expected_rendered_text_sha256
        and str(audio.get("source_text_sha256") or "").lower() == text_hash
        and str(audio.get("wav_sha256") or "").lower() == _sha256_file(audio_path)
    )


def _lightweight_voice_config(subject: str = "kira") -> VoiceOutputConfig:
    label = str(subject or "kira").strip().capitalize() or "Kira"
    config = load_candidate_voice_config(
        {
            "candidate_id": label.lower(),
            "display_name": label,
            "gender_preference": "female" if label.lower() in {"kira", "lisa"} else "",
        }
    )
    target_voice_requested = str(os.environ.get("KIRA_MESSAGE_TARGET_VOICE", "")).strip().lower() in {
        "1", "true", "yes", "on"
    }
    if (
        target_voice_requested
        and config.engine == "chatterbox_tts"
        and config.chatterbox_reference_audio
    ):
        # The world-shell endpoint is called only when Robert clicks the message.
        # Preserve the reviewed reference voice, render the full durable text in
        # bounded chunks, and leave playback entirely to the browser click.
        return replace(config, play_audio=False, max_chars=max(4000, config.max_chars))

    # Outside an opted-in shell, retain the lightweight non-playing fallback.
    return replace(
        config,
        engine="windows_sapi_powershell",
        play_audio=False,
        chatterbox_reference_audio="",
        output_dir="",
        max_chars=4000,
    )


def _voice_identity_status(engine: str) -> str:
    normalized = str(engine or "").strip().lower()
    if normalized == "chatterbox_tts":
        return "reviewed_reference_chatterbox"
    if normalized == "windows_sapi_powershell":
        return "temporary_sapi_approximation"
    return "unverified_voice_backend"


def list_voice_messages(
    messages_dir: Path = DEFAULT_MESSAGES_DIR,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return safe UI records without changing unread state."""
    if not messages_dir.exists():
        return []
    records: list[dict[str, Any]] = []
    paths = sorted(messages_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    for path in paths[: max(0, limit)]:
        record = _read_json(path, {})
        if not isinstance(record, dict):
            continue
        identifier = _message_id(record, path)
        if not MESSAGE_ID_RE.fullmatch(identifier):
            continue
        audio_path = _canonical_audio_path(identifier, messages_dir)
        audio_ready = _audio_matches_record(record, audio_path)
        stored_audio = record.get("audio") if isinstance(record.get("audio"), dict) else {}
        stored_audio_status = str(stored_audio.get("status") or "not_generated")
        audio_status = (
            "ready"
            if audio_ready
            else "stale_or_unverified"
            if stored_audio_status == "ready" or _wav_ready(audio_path)
            else stored_audio_status
        )
        payload = record.get("message", {}) if isinstance(record.get("message"), dict) else {}
        provenance = (
            record.get("authorship_provenance")
            if isinstance(record.get("authorship_provenance"), dict)
            else {}
        )
        claim_allowed = provenance.get("authorship_claim_allowed") is True
        claimed_subject = str(
            provenance.get("claimed_subject") or record.get("subject") or "unknown_subject"
        )
        sender = str(
            record.get("sender")
            or (claimed_subject if claim_allowed else "unverified_legacy_sender")
        )
        text = _message_text(record)
        records.append(
            {
                "message_id": identifier,
                "created_at": str(record.get("created_at") or ""),
                "subject": claimed_subject,
                "sender": sender,
                "generated_by": str(provenance.get("generated_by") or "unknown"),
                "approved_by_subject": provenance.get("approved_by_subject") is True,
                "authorship_claim_allowed": claim_allowed,
                "status": str(record.get("status") or "unread"),
                "text": text,
                "preview": text[:180],
                "reason": str(payload.get("reason") or ""),
                "urgency": str(payload.get("urgency") or "normal"),
                "privacy": str(payload.get("privacy") or "shareable"),
                "audio_status": audio_status,
                "audio_reason": "source_text_or_wav_hash_mismatch" if audio_status == "stale_or_unverified" else str(stored_audio.get("reason") or ""),
                "audio_voice_identity_status": str(stored_audio.get("voice_identity_status") or "not_rendered_or_unverified"),
                "audio_ready": audio_ready,
            }
        )
    return records


def voice_message_inbox(
    messages_dir: Path = DEFAULT_MESSAGES_DIR,
    *,
    include_messages: bool = True,
    limit: int = 50,
) -> dict[str, Any]:
    all_messages = list_voice_messages(messages_dir, limit=100000)
    messages = all_messages[: max(0, limit)]
    unread = sum(item["status"] == "unread" for item in all_messages)
    return {
        "total": len(all_messages),
        "unread": unread,
        "has_unread": unread > 0,
        "latest_created_at": messages[0]["created_at"] if messages else "",
        "messages": messages if include_messages else [],
    }


def ensure_voice_message_audio(
    message_id_or_path: str | Path,
    *,
    messages_dir: Path = DEFAULT_MESSAGES_DIR,
    synthesizer: Callable[..., dict[str, Any]] = synthesize_text_to_wav,
    config: VoiceOutputConfig | None = None,
) -> dict[str, Any]:
    """Create or verify the canonical WAV and persist a truthful audio state."""
    supplied_path = Path(message_id_or_path)
    if supplied_path.suffix.lower() == ".json" and supplied_path.is_file():
        path = supplied_path
        messages_dir = path.parent
    else:
        path = _find_message_path(str(message_id_or_path), messages_dir)
    if path is None or not path.is_file():
        return {"generated": False, "reason": "message_not_found", "audio_ready": False}

    with _WRITE_LOCK:
        record = _read_json(path, {})
        if not isinstance(record, dict):
            return {"generated": False, "reason": "invalid_message_record", "audio_ready": False}
        identifier = _message_id(record, path)
        text = _message_text(record)
        source_text_sha256 = _sha256_bytes(text)
        if not text:
            result = {"generated": False, "reason": "empty_message_text", "audio_ready": False}
        else:
            audio_path = _canonical_audio_path(identifier, messages_dir)
            if _audio_matches_record(record, audio_path):
                validation = _wav_validation(audio_path)
                stored_audio = record.get("audio") if isinstance(record.get("audio"), dict) else {}
                stored_engine = str(stored_audio.get("engine") or "windows_sapi_powershell")
                result = {
                    "generated": True,
                    "reason": "already_ready",
                    "audio_ready": True,
                    "audio_path": _relative(audio_path),
                    "engine": stored_engine,
                    "voice_identity_status": str(
                        stored_audio.get("voice_identity_status") or _voice_identity_status(stored_engine)
                    ),
                    "source_text_sha256": source_text_sha256,
                    "wav_sha256": _sha256_file(audio_path),
                    "wav_validation": validation,
                    "synthesis_generated": True,
                }
            else:
                # Never leave an old WAV available after the canonical text or
                # integrity metadata changes.
                try:
                    audio_path.unlink(missing_ok=True)
                except OSError:
                    pass
                voice_config = config or _lightweight_voice_config(str(record.get("subject") or "kira"))
                try:
                    synthesis = synthesizer(text, audio_path, config=voice_config)
                except Exception as exc:  # pragma: no cover - backend defensive boundary
                    synthesis = {"generated": False, "reason": "voice_synthesis_exception", "error": str(exc)}
                validation = _wav_validation(audio_path)
                backend_succeeded = synthesis.get("generated") is True
                full_rendered_text = clean_text_for_speech(text, 0)
                backend_rendered_text = str(synthesis.get("text") or "")
                rendered_full_canonical_text = backend_rendered_text == full_rendered_text
                ready = (
                    backend_succeeded
                    and rendered_full_canonical_text
                    and validation.get("status") == "valid_pcm_wav"
                )
                if not ready:
                    try:
                        audio_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                result = {
                    **synthesis,
                    "generated": ready,
                    "audio_ready": ready,
                    "audio_path": _relative(audio_path) if ready else "",
                    "source_text_sha256": source_text_sha256,
                    "wav_sha256": _sha256_file(audio_path) if ready else "",
                    "wav_validation": validation,
                    "synthesis_generated": backend_succeeded,
                    "rendered_full_canonical_text": rendered_full_canonical_text,
                    "rendered_text_sha256": _sha256_bytes(backend_rendered_text) if backend_rendered_text else "",
                }
                if not backend_succeeded:
                    result["reason"] = str(synthesis.get("reason") or "voice_backend_reported_failure")
                elif not ready and result.get("reason") in {"ok", "already_ready"}:
                    result["reason"] = (
                        "rendered_text_is_missing_or_truncated"
                        if not rendered_full_canonical_text
                        else "invalid_or_missing_wav_output"
                    )

        rendered_engine = str(result.get("engine") or "windows_sapi_powershell")
        record["audio"] = {
            "status": "ready" if result.get("audio_ready") else "blocked",
            "wav_path": result.get("audio_path", ""),
            "engine": rendered_engine,
            "voice_identity_status": str(
                result.get("voice_identity_status") or _voice_identity_status(rendered_engine)
            ),
            "reason": result.get("reason", "voice_synthesis_failed"),
            "source_text_chars": len(text),
            "source_text_sha256": source_text_sha256,
            "wav_sha256": str(result.get("wav_sha256") or ""),
            "synthesis_generated": bool(result.get("synthesis_generated", result.get("generated"))),
            "wav_validation": result.get("wav_validation") if isinstance(result.get("wav_validation"), dict) else {},
            "rendered_full_canonical_text": bool(result.get("rendered_full_canonical_text", result.get("audio_ready"))),
            "rendered_text_sha256": str(result.get("rendered_text_sha256") or (_sha256_bytes(clean_text_for_speech(text, 0)) if result.get("audio_ready") else "")),
            "acoustic_speech_content_verified": False,
            "verification_scope": "backend success, full rendered-text payload, PCM WAV parse, and text/WAV hashes; human listening still required",
            "rendered_text_chars": len(str(result.get("text") or text if result.get("audio_ready") else "")),
            "rendered_text_may_be_truncated": bool(result.get("text")) and len(str(result.get("text"))) < len(text),
            "updated_at": utc_now(),
            "text_backed": True,
            "auto_played_while_robert_away": False,
        }
        _write_json(path, record)
    return result


def voice_message_audio_path(message_id: str, messages_dir: Path = DEFAULT_MESSAGES_DIR) -> Path | None:
    path = _find_message_path(message_id, messages_dir)
    if path is None:
        return None
    record = _read_json(path, {})
    identifier = _message_id(record, path) if isinstance(record, dict) else ""
    audio_path = _canonical_audio_path(identifier, messages_dir) if identifier else None
    return audio_path if audio_path and isinstance(record, dict) and _audio_matches_record(record, audio_path) else None


def set_voice_message_status(
    message_id: str,
    status: str,
    *,
    messages_dir: Path = DEFAULT_MESSAGES_DIR,
) -> dict[str, Any]:
    normalized = str(status or "").strip().lower()
    if normalized not in MESSAGE_STATUSES:
        return {"ok": False, "reason": "invalid_message_status"}
    path = _find_message_path(message_id, messages_dir)
    if path is None:
        return {"ok": False, "reason": "message_not_found"}
    with _WRITE_LOCK:
        record = _read_json(path, {})
        if not isinstance(record, dict):
            return {"ok": False, "reason": "invalid_message_record"}
        record["status"] = normalized
        record["reviewed_at"] = utc_now()
        if normalized == "read":
            record["played_or_read_at"] = record["reviewed_at"]
        _write_json(path, record)
    return {"ok": True, "message_id": message_id, "status": normalized}


def create_voice_message(
    text: str,
    *,
    subject: str = "kira",
    reason: str = "",
    urgency: str = "normal",
    privacy: str = "shareable",
    run_id: str = "",
    requested_by: str = "",
    generated_by: str = "",
    approved_by_subject: bool = False,
    messages_dir: Path = DEFAULT_MESSAGES_DIR,
    synthesize: bool = True,
) -> dict[str, Any]:
    clean = str(text or "").strip()[:4000]
    if not clean:
        raise ValueError("message_text_required")
    subject_id = _safe_identity(subject, "kira")
    sender_id, provenance = _authorship_identity(
        subject_id,
        generated_by,
        approved_by_subject,
    )
    provenance["requested_by"] = _safe_identity(requested_by, "unspecified")
    identifier = _identifier(f"{sender_id}_message_to_robert")
    path = _safe_child(messages_dir, f"{identifier}.json")
    record = {
        "message_id": identifier,
        "created_at": utc_now(),
        "run_id": run_id,
        "subject": subject_id,
        "sender": sender_id,
        "status": "unread",
        "kind": (
            f"{subject_id}_to_robert_voice_message"
            if provenance["authorship_claim_allowed"]
            else f"unapproved_voice_message_draft_for_{subject_id}"
        ),
        "message": {
            "message": clean,
            "reason": str(reason or "")[:1000],
            "urgency": urgency if urgency in {"low", "normal", "high"} else "normal",
            "privacy": privacy if privacy in {"shareable", "summary_only"} else "shareable",
        },
        "authorship_provenance": provenance,
        "audio": {"status": "not_generated", "text_backed": True},
        "memory_policy": {"not_auto_promoted": True, "review_before_memory": True},
    }
    with _WRITE_LOCK:
        _write_json(path, record)
    audio_result = ensure_voice_message_audio(path, messages_dir=messages_dir) if synthesize else {"generated": False, "reason": "not_requested", "audio_ready": False}
    return {"record": _read_json(path, record), "path": path, "audio_result": audio_result}


def save_tablet_note(
    text: str,
    *,
    note_kind: str = "note",
    title: str = "",
    author: str = "kira",
    source: str = "kira_tablet",
    linked_artifact: str = "",
    body_grounding: dict[str, Any] | None = None,
    requested_by: str = "",
    generated_by: str = "",
    approved_by_subject: bool = False,
    tablet_root: Path = DEFAULT_TABLET_ROOT,
) -> dict[str, Any]:
    clean = str(text or "").strip()[:20000]
    if not clean:
        raise ValueError("tablet_note_text_required")
    kind = str(note_kind or "note").strip().lower()
    if kind not in NOTE_KINDS:
        raise ValueError("invalid_tablet_note_kind")
    claimed_author_id = _safe_identity(author, "unknown_author")
    requester_id = _safe_identity(requested_by, "unspecified")
    author_id, provenance = _authorship_identity(
        claimed_author_id,
        generated_by,
        approved_by_subject,
    )
    identifier = _identifier(f"{author_id}_tablet_{kind}")
    path = _safe_child(tablet_root, "notes", f"{identifier}.json")
    grounding = body_grounding if isinstance(body_grounding, dict) else {}
    record = {
        "note_id": identifier,
        "created_at": utc_now(),
        "author": author_id,
        "kind": kind,
        "title": str(title or kind.replace("_", " ").title())[:240],
        "text": clean,
        "source": source,
        "linked_artifact": linked_artifact,
        "authorship_provenance": {
            **provenance,
            "requested_by": requester_id,
            "claimed_author": claimed_author_id,
        },
        "tablet_state": {
            "local_only": True,
            "physical_tablet_use_proven": bool(grounding.get("physical_tablet_use_proven", False)),
            "body_grounding": grounding,
        },
        "memory_policy": {
            "not_auto_promoted": True,
            "creative_work_not_lived_memory": kind == "creative_writing",
            "review_before_memory": True,
        },
    }
    with _WRITE_LOCK:
        _write_json(path, record)
    return {"ok": True, "note_id": identifier, "path": path, "record": record}


def queue_tablet_request(
    query: str,
    *,
    request_type: str,
    purpose: str = "",
    requested_by: str = "kira",
    source_hint: str = "",
    body_grounding: dict[str, Any] | None = None,
    tablet_root: Path = DEFAULT_TABLET_ROOT,
) -> dict[str, Any]:
    clean = str(query or "").strip()[:2000]
    if not clean:
        raise ValueError("tablet_request_query_required")
    kind = str(request_type or "").strip().lower()
    if kind not in REQUEST_TYPES:
        raise ValueError("invalid_tablet_request_type")
    requester_id = _safe_identity(requested_by, "unknown_requester")
    identifier = _identifier(f"{requester_id}_tablet_request")
    path = _safe_child(tablet_root, "requests", f"{identifier}.json")
    is_online = kind == "online_lookup"
    grounding = body_grounding if isinstance(body_grounding, dict) else {}
    record = {
        "request_id": identifier,
        "created_at": utc_now(),
        "requested_by": requester_id,
        "request_type": kind,
        "query": clean,
        "purpose": str(purpose or "")[:1000],
        "source_hint": str(source_hint or "")[:1000],
        "status": "pending_robert_review" if is_online else "pending_local_source_selection",
        "execution": {
            "network_access_performed": False,
            "source_opened": False,
            "completion_claim_allowed": False,
            "reason": "A request record is not evidence that Kira searched or read anything.",
        },
        "tablet_state": {
            "local_only": True,
            "physical_tablet_use_proven": bool(grounding.get("physical_tablet_use_proven", False)),
            "body_grounding": grounding,
        },
        "memory_policy": {"not_auto_promoted": True, "review_before_memory": True},
    }
    with _WRITE_LOCK:
        _write_json(path, record)
    return {"ok": True, "request_id": identifier, "path": path, "record": record}


def tablet_workspace_summary(tablet_root: Path = DEFAULT_TABLET_ROOT) -> dict[str, Any]:
    note_paths = list((tablet_root / "notes").glob("*.json")) if (tablet_root / "notes").exists() else []
    request_paths = list((tablet_root / "requests").glob("*.json")) if (tablet_root / "requests").exists() else []
    pending = 0
    for path in request_paths:
        record = _read_json(path, {})
        if isinstance(record, dict) and str(record.get("status") or "").startswith("pending_"):
            pending += 1
    latest_note = max(note_paths, key=lambda item: item.stat().st_mtime, default=None)
    latest_request = max(request_paths, key=lambda item: item.stat().st_mtime, default=None)
    return {
        "notes": len(note_paths),
        "requests": len(request_paths),
        "pending_requests": pending,
        "latest_note_path": _relative(latest_note) if latest_note else "",
        "latest_request_path": _relative(latest_request) if latest_request else "",
        "online_access_performed_by_queue": False,
    }
