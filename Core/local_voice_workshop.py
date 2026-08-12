"""Inactive, provenance-first local voice workshop contracts.

This module validates already-existing PCM WAV files and writes immutable
evidence records.  It deliberately has no audio capture, extraction,
generation, playback, model import/load, profile creation, route activation,
or current-version-pointer operation.
"""
from __future__ import annotations

import array
import hashlib
import json
import math
import re
import sys
import wave
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSHOP_RELATIVE_ROOT = Path("Voice") / "workshop"
SCHEMA_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{1,79}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

OWNER_PREVIEW_APPROVAL_TEXT = "I approve this exact inactive voice preview."
OWNER_PROMOTION_APPROVAL_TEXT = "I approve this exact inactive promotion proposal."
OWNER_ROLLBACK_APPROVAL_TEXT = "I approve this exact inactive rollback proposal."

PRIVATE_MARKERS = (
    "private mind:",
    "private_mind:",
    "factual:",
    "runtime truth:",
    "runtime_truth:",
)


class VoiceWorkshopError(ValueError):
    """Raised when workshop evidence fails closed."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_id(value: object, label: str) -> str:
    candidate = str(value or "").strip()
    if not ID_PATTERN.fullmatch(candidate):
        raise VoiceWorkshopError(
            f"{label} must match {ID_PATTERN.pattern}; got {candidate!r}."
        )
    return candidate


def _require_sha256(value: object, label: str) -> str:
    candidate = str(value or "").strip().lower()
    if not SHA256_PATTERN.fullmatch(candidate):
        raise VoiceWorkshopError(f"{label} must be one lowercase SHA-256 digest.")
    return candidate


def _require_timestamp(value: object, label: str) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        raise VoiceWorkshopError(f"{label} is required.")
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise VoiceWorkshopError(f"{label} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise VoiceWorkshopError(f"{label} must include a timezone.")
    return candidate


def _require_text(value: object, label: str, *, minimum: int = 1) -> str:
    candidate = str(value or "").strip()
    if len(candidate) < minimum:
        raise VoiceWorkshopError(f"{label} must contain at least {minimum} characters.")
    return candidate


def _read_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VoiceWorkshopError(f"Could not read JSON object {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise VoiceWorkshopError(f"Expected a JSON object in {path}.")
    return data


def _write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    except FileExistsError as exc:
        raise VoiceWorkshopError(f"Immutable workshop record already exists: {path}") from exc


def _relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise VoiceWorkshopError(f"Path is outside the project: {path}") from exc


def resolve_project_file(
    value: object,
    *,
    project_root: Path = PROJECT_ROOT,
    suffixes: Iterable[str] | None = None,
) -> Path:
    raw = str(value or "").strip().replace("\\", "/")
    if not raw or Path(raw).is_absolute():
        raise VoiceWorkshopError("Workshop evidence paths must be project-relative.")
    root = project_root.resolve()
    try:
        path = (root / raw).resolve(strict=True)
        path.relative_to(root)
    except (OSError, ValueError) as exc:
        raise VoiceWorkshopError(f"Workshop evidence file is missing or outside project: {raw}") from exc
    if not path.is_file():
        raise VoiceWorkshopError(f"Workshop evidence is not a regular file: {raw}")
    if suffixes and path.suffix.casefold() not in {item.casefold() for item in suffixes}:
        raise VoiceWorkshopError(f"Workshop evidence has an unsupported suffix: {raw}")
    return path


def _resolve_version_dir(version_dir: Path, project_root: Path) -> Path:
    root = project_root.resolve()
    workshop_root = (root / WORKSHOP_RELATIVE_ROOT).resolve()
    path = version_dir if version_dir.is_absolute() else root / version_dir
    path = path.resolve()
    try:
        path.relative_to(workshop_root)
    except ValueError as exc:
        raise VoiceWorkshopError(
            f"Version directory must remain under {WORKSHOP_RELATIVE_ROOT.as_posix()}."
        ) from exc
    return path


def _verified_file_binding(
    record: dict[str, Any],
    path_key: str,
    hash_key: str,
    *,
    project_root: Path,
    suffixes: Iterable[str] | None = None,
) -> tuple[Path, str]:
    path = resolve_project_file(
        record.get(path_key), project_root=project_root, suffixes=suffixes
    )
    expected = _require_sha256(record.get(hash_key), hash_key)
    actual = file_sha256(path)
    if actual != expected:
        raise VoiceWorkshopError(
            f"Hash mismatch for {path_key}: expected {expected}, got {actual}."
        )
    return path, actual


def inspect_pcm_wav(
    wav_path: Path,
    *,
    project_root: Path = PROJECT_ROOT,
    purpose: str = "source",
) -> dict[str, Any]:
    """Inspect a WAV without playback, model loading, or audio output."""

    try:
        path = wav_path.resolve(strict=True)
        path.relative_to(project_root.resolve())
    except (OSError, ValueError) as exc:
        raise VoiceWorkshopError(
            "WAV must be an existing regular file inside the project."
        ) from exc
    if not path.is_file():
        raise VoiceWorkshopError("WAV evidence must be a regular file.")
    if path.stat().st_size > 256 * 1024 * 1024:
        raise VoiceWorkshopError("WAV exceeds the bounded 256 MiB inspection limit.")
    reasons: list[str] = []
    try:
        with wave.open(str(path), "rb") as reader:
            channels = reader.getnchannels()
            sample_width = reader.getsampwidth()
            sample_rate = reader.getframerate()
            frame_count = reader.getnframes()
            compression = reader.getcomptype()
            raw = reader.readframes(frame_count)
    except (OSError, EOFError, wave.Error) as exc:
        raise VoiceWorkshopError(f"Unreadable WAV {path}: {exc}") from exc

    duration = frame_count / sample_rate if sample_rate else 0.0
    if channels != 1:
        reasons.append("wav_must_be_mono")
    if sample_width != 2:
        reasons.append("wav_must_be_pcm16")
    if compression != "NONE":
        reasons.append("wav_must_be_uncompressed_pcm")
    if sample_rate < 24000:
        reasons.append("sample_rate_below_24000_hz")
    if frame_count <= 0 or duration <= 0:
        reasons.append("wav_has_no_audio_frames")

    samples = array.array("h")
    if sample_width == 2 and raw:
        samples.frombytes(raw[: len(raw) - (len(raw) % 2)])
        if sys.byteorder != "little":
            samples.byteswap()
    absolute = [abs(int(item)) for item in samples]
    sample_count = len(absolute)
    peak = max(absolute, default=0)
    rms = (
        math.sqrt(sum(float(item) * float(item) for item in samples) / sample_count)
        if sample_count
        else 0.0
    )
    peak_dbfs = 20.0 * math.log10(peak / 32767.0) if peak else float("-inf")
    rms_dbfs = 20.0 * math.log10(rms / 32767.0) if rms else float("-inf")
    clip_threshold = round(32767 * (10 ** (-0.1 / 20.0)))
    clipped = sum(1 for item in absolute if item >= clip_threshold)
    silence_threshold = round(32767 * (10 ** (-50.0 / 20.0)))
    silent = sum(1 for item in absolute if item <= silence_threshold)
    clipping_ratio = clipped / sample_count if sample_count else 1.0
    silence_ratio = silent / sample_count if sample_count else 1.0
    dc_offset = (
        abs(sum(float(item) for item in samples) / sample_count) / 32767.0
        if sample_count
        else 1.0
    )

    if not sample_count or peak == 0 or not math.isfinite(rms_dbfs):
        reasons.append("wav_is_silent")
    if clipping_ratio > 0.001:
        reasons.append("clipping_ratio_above_0_001")
    if math.isfinite(peak_dbfs) and not (-18.0 <= peak_dbfs <= -1.0):
        reasons.append("peak_dbfs_outside_review_range")
    if math.isfinite(rms_dbfs) and not (-35.0 <= rms_dbfs <= -10.0):
        reasons.append("rms_dbfs_outside_review_range")
    if silence_ratio > 0.35:
        reasons.append("silence_ratio_above_0_35")
    if dc_offset > 0.02:
        reasons.append("dc_offset_above_0_02")
    if purpose == "master_candidate" and not (6.0 <= duration <= 10.0):
        reasons.append("master_duration_must_be_6_to_10_seconds")
    if purpose == "preview_output" and not (0.10 <= duration <= 120.0):
        reasons.append("preview_duration_outside_0_1_to_120_seconds")

    return {
        "record_type": "wav_technical_report",
        "schema_version": SCHEMA_VERSION,
        "purpose": purpose,
        "path": _relative(project_root, path),
        "sha256": file_sha256(path),
        "size_bytes": path.stat().st_size,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate_hz": sample_rate,
        "frame_count": frame_count,
        "duration_seconds": round(duration, 6),
        "compression": compression,
        "sample_count": sample_count,
        "peak_dbfs": round(peak_dbfs, 6) if math.isfinite(peak_dbfs) else None,
        "rms_dbfs": round(rms_dbfs, 6) if math.isfinite(rms_dbfs) else None,
        "clipping_ratio": round(clipping_ratio, 9),
        "silence_ratio": round(silence_ratio, 9),
        "dc_offset_ratio": round(dc_offset, 9),
        "passed": not reasons,
        "reasons": reasons,
        "operation": {
            "audio_played": False,
            "audio_generated": False,
            "model_loaded": False,
        },
    }


def validate_permission_record(
    record: dict[str, Any], *, project_root: Path = PROJECT_ROOT
) -> dict[str, Any]:
    person_id = _require_id(record.get("person_id"), "person_id")
    profile_id = _require_id(record.get("profile_id"), "profile_id")
    permission_id = _require_id(record.get("permission_id"), "permission_id")
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    source_path, source_sha = _verified_file_binding(
        source,
        "path",
        "sha256",
        project_root=project_root,
        suffixes={".wav"},
    )
    _require_id(source.get("source_id"), "source.source_id")
    speaker_id = _require_id(source.get("speaker_id"), "source.speaker_id")
    if speaker_id != person_id:
        raise VoiceWorkshopError(
            "source.speaker_id must exactly match the target person_id."
        )
    _require_text(source.get("recording_kind"), "source.recording_kind", minimum=3)
    _require_text(source.get("language"), "source.language", minimum=2)
    provenance = source.get("provenance") if isinstance(source.get("provenance"), dict) else {}
    _require_text(provenance.get("origin"), "source.provenance.origin", minimum=3)
    _require_text(
        provenance.get("recorder_or_publisher"),
        "source.provenance.recorder_or_publisher",
        minimum=2,
    )
    _require_text(
        provenance.get("chain_of_custody"),
        "source.provenance.chain_of_custody",
        minimum=10,
    )
    rights = record.get("rights") if isinstance(record.get("rights"), dict) else {}
    required_rights = (
        "speaker_consent_confirmed",
        "recording_rights_confirmed",
        "recording_possession_and_processing",
        "voice_model_conditioning_rights_confirmed",
        "voice_conditioning_private_local",
        "named_person_private_local_synthesis",
    )
    missing = [key for key in required_rights if rights.get(key) is not True]
    if missing:
        raise VoiceWorkshopError(
            "Permission record lacks confirmed private-local rights: " + ", ".join(missing)
        )
    if record.get("revoked") is not False:
        raise VoiceWorkshopError("Permission record is revoked or has no explicit revoked=false.")
    authority = (
        record.get("confirmed_by")
        if isinstance(record.get("confirmed_by"), dict)
        else {}
    )
    _require_id(authority.get("authority_id"), "confirmed_by.authority_id")
    _require_text(
        authority.get("confirmation_text"),
        "confirmed_by.confirmation_text",
        minimum=20,
    )
    _require_timestamp(authority.get("confirmed_at"), "confirmed_by.confirmed_at")

    normalized = deepcopy(record)
    normalized.update(
        {
            "record_type": "permission_record",
            "schema_version": SCHEMA_VERSION,
            "permission_id": permission_id,
            "person_id": person_id,
            "profile_id": profile_id,
            "status": "confirmed_private_local_voice_conditioning_only",
            "revoked": False,
        }
    )
    normalized["source"] = deepcopy(source)
    normalized["source"]["path"] = _relative(project_root, source_path)
    normalized["source"]["sha256"] = source_sha
    normalized["public_or_commercial_authority_granted"] = bool(
        rights.get("public_distribution") is True and rights.get("commercial_use") is True
    )
    return normalized


def validate_history(version_dir: Path) -> list[dict[str, Any]]:
    path = version_dir / "history.jsonl"
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    previous = ""
    for expected_sequence, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            raise VoiceWorkshopError("History contains a blank line.")
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise VoiceWorkshopError(f"Invalid history JSON at line {expected_sequence}.") from exc
        if not isinstance(event, dict):
            raise VoiceWorkshopError("History entries must be JSON objects.")
        recorded_hash = _require_sha256(event.get("event_sha256"), "event_sha256")
        unsigned = dict(event)
        unsigned.pop("event_sha256", None)
        if canonical_json_sha256(unsigned) != recorded_hash:
            raise VoiceWorkshopError(f"History hash mismatch at sequence {expected_sequence}.")
        if event.get("sequence") != expected_sequence:
            raise VoiceWorkshopError(f"History sequence mismatch at line {expected_sequence}.")
        if str(event.get("previous_event_sha256") or "") != previous:
            raise VoiceWorkshopError(f"History chain mismatch at sequence {expected_sequence}.")
        previous = recorded_hash
        events.append(event)
    return events


def _append_history(
    version_dir: Path,
    *,
    event_type: str,
    actor_id: str,
    record_path: Path,
    recorded_at: str,
) -> dict[str, Any]:
    events = validate_history(version_dir)
    record_relative = record_path.resolve().relative_to(version_dir.resolve()).as_posix()
    event = {
        "record_type": "workshop_history_event",
        "schema_version": SCHEMA_VERSION,
        "sequence": len(events) + 1,
        "previous_event_sha256": events[-1]["event_sha256"] if events else "",
        "event_type": _require_text(event_type, "event_type"),
        "actor_id": _require_id(actor_id, "actor_id"),
        "recorded_at": _require_timestamp(recorded_at, "recorded_at"),
        "record_path": record_relative,
        "record_sha256": file_sha256(record_path),
    }
    event["event_sha256"] = canonical_json_sha256(event)
    history_path = version_dir / "history.jsonl"
    with history_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
    return event


def initialize_version(
    version_dir: Path,
    request: dict[str, Any],
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    path = _resolve_version_dir(version_dir, project_root)
    person_id = _require_id(request.get("person_id"), "person_id")
    profile_id = _require_id(request.get("profile_id"), "profile_id")
    version_id = _require_id(request.get("version_id"), "version_id")
    if path.name != version_id:
        raise VoiceWorkshopError("Version directory name must exactly equal version_id.")
    parent_version_id = str(request.get("parent_version_id") or "").strip()
    if parent_version_id:
        _require_id(parent_version_id, "parent_version_id")
    created_by = _require_id(request.get("created_by"), "created_by")
    created_at = _require_timestamp(request.get("created_at"), "created_at")
    permission_input = (
        request.get("permission_record")
        if isinstance(request.get("permission_record"), dict)
        else {}
    )
    permission = validate_permission_record(permission_input, project_root=project_root)
    if (permission["person_id"], permission["profile_id"]) != (person_id, profile_id):
        raise VoiceWorkshopError("Permission record person/profile binding mismatch.")
    source_path = resolve_project_file(
        permission["source"]["path"], project_root=project_root, suffixes={".wav"}
    )
    technical = inspect_pcm_wav(source_path, project_root=project_root, purpose="source")
    format_blockers = {
        "wav_must_be_mono",
        "wav_must_be_pcm16",
        "wav_must_be_uncompressed_pcm",
        "sample_rate_below_24000_hz",
        "wav_has_no_audio_frames",
        "wav_is_silent",
    }
    if format_blockers.intersection(technical["reasons"]):
        raise VoiceWorkshopError(
            "Source WAV failed foundational format/signal gates: "
            + ", ".join(technical["reasons"])
        )
    if path.exists():
        raise VoiceWorkshopError(f"Version directory already exists: {path}")
    path.mkdir(parents=True, exist_ok=False)
    manifest = {
        "record_type": "voice_workshop_version",
        "schema_version": SCHEMA_VERSION,
        "status": "inactive_evidence_only",
        "person_id": person_id,
        "profile_id": profile_id,
        "version_id": version_id,
        "parent_version_id": parent_version_id,
        "created_by": created_by,
        "created_at": created_at,
        "permission_id": permission["permission_id"],
        "source": {
            "path": technical["path"],
            "sha256": technical["sha256"],
        },
        "boundaries": {
            "audio_generation": False,
            "audio_playback": False,
            "model_loading_or_training": False,
            "profile_creation": False,
            "routing_or_default_activation": False,
        },
    }
    manifest_path = path / "version_manifest.json"
    permission_path = path / "permission_record.json"
    technical_path = path / "source_technical_report.json"
    _write_json_exclusive(manifest_path, manifest)
    _write_json_exclusive(permission_path, permission)
    _write_json_exclusive(technical_path, technical)
    _append_history(
        path,
        event_type="version_initialized",
        actor_id=created_by,
        record_path=manifest_path,
        recorded_at=created_at,
    )
    _append_history(
        path,
        event_type="permission_record_bound",
        actor_id=created_by,
        record_path=permission_path,
        recorded_at=created_at,
    )
    _append_history(
        path,
        event_type="source_technical_report_bound",
        actor_id=created_by,
        record_path=technical_path,
        recorded_at=created_at,
    )
    return manifest


def _load_version(version_dir: Path) -> dict[str, Any]:
    manifest = _read_object(version_dir / "version_manifest.json")
    if manifest.get("record_type") != "voice_workshop_version":
        raise VoiceWorkshopError("Invalid workshop version manifest.")
    return manifest


def append_candidate_review(
    version_dir: Path,
    review: dict[str, Any],
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    path = _resolve_version_dir(version_dir, project_root)
    manifest = _load_version(path)
    review_id = _require_id(review.get("review_id"), "review_id")
    for key in ("person_id", "profile_id", "version_id"):
        if str(review.get(key) or "") != str(manifest.get(key) or ""):
            raise VoiceWorkshopError(f"Candidate review {key} mismatch.")
    candidate = review.get("candidate") if isinstance(review.get("candidate"), dict) else {}
    candidate_path, candidate_sha = _verified_file_binding(
        candidate,
        "path",
        "sha256",
        project_root=project_root,
        suffixes={".wav"},
    )
    if _require_sha256(candidate.get("source_sha256"), "candidate.source_sha256") != str(
        manifest.get("source", {}).get("sha256") or ""
    ):
        raise VoiceWorkshopError("Candidate is not bound to this version's source SHA-256.")
    if str(candidate.get("source_path") or "").replace("\\", "/") != str(
        manifest.get("source", {}).get("path") or ""
    ):
        raise VoiceWorkshopError("Candidate is not bound to this version's exact source path.")
    if candidate.get("derivation_method") != "single_contiguous_clip_no_concatenation":
        raise VoiceWorkshopError(
            "Candidate derivation_method must prove one contiguous clip with no concatenation."
        )
    try:
        source_start = float(candidate.get("source_start_seconds"))
        source_end = float(candidate.get("source_end_seconds"))
    except (TypeError, ValueError) as exc:
        raise VoiceWorkshopError(
            "Candidate source_start_seconds/source_end_seconds must be numbers."
        ) from exc
    if not math.isfinite(source_start) or not math.isfinite(source_end):
        raise VoiceWorkshopError("Candidate source times must be finite.")
    if source_start < 0.0 or source_end <= source_start:
        raise VoiceWorkshopError("Candidate source interval must be positive and ordered.")
    decision = str(review.get("decision") or "").strip()
    if decision not in {"accepted_clean_master_candidate", "rejected"}:
        raise VoiceWorkshopError("Candidate decision must be accepted_clean_master_candidate or rejected.")
    human = review.get("human_review") if isinstance(review.get("human_review"), dict) else {}
    reviewer_id = _require_id(human.get("reviewer_id"), "human_review.reviewer_id")
    reviewed_at = _require_timestamp(human.get("reviewed_at"), "human_review.reviewed_at")
    _require_text(human.get("review_statement"), "human_review.review_statement", minimum=15)
    if decision == "accepted_clean_master_candidate":
        required_true = (
            "exact_source_context_opened",
            "target_identity_confirmed",
            "target_only_speech",
            "no_overlapping_speech",
            "no_music",
            "no_material_sound_effects",
            "no_material_background_noise",
            "no_material_reverb",
            "stable_delivery",
        )
        missing = [key for key in required_true if human.get(key) is not True]
        if missing:
            raise VoiceWorkshopError(
                "Accepted candidate lacks human review gates: " + ", ".join(missing)
            )
        _require_text(human.get("transcript"), "human_review.transcript", minimum=2)

    technical = inspect_pcm_wav(
        candidate_path, project_root=project_root, purpose="master_candidate"
    )
    source_interval = source_end - source_start
    if abs(source_interval - float(technical["duration_seconds"])) > 0.05:
        raise VoiceWorkshopError(
            "Candidate duration does not match its exact contiguous source interval."
        )
    normalized = deepcopy(review)
    normalized.update(
        {
            "record_type": "candidate_review",
            "schema_version": SCHEMA_VERSION,
            "review_id": review_id,
            "decision": decision,
            "technical_report": technical,
        }
    )
    normalized["candidate"] = deepcopy(candidate)
    normalized["candidate"]["path"] = _relative(project_root, candidate_path)
    normalized["candidate"]["sha256"] = candidate_sha
    output = path / "reviews" / f"{review_id}.json"
    _write_json_exclusive(output, normalized)
    _append_history(
        path,
        event_type="candidate_review_appended",
        actor_id=reviewer_id,
        record_path=output,
        recorded_at=reviewed_at,
    )
    return normalized


def _history_records(version_dir: Path, event_type: str) -> list[tuple[int, Path, dict[str, Any]]]:
    records: list[tuple[int, Path, dict[str, Any]]] = []
    for event in validate_history(version_dir):
        if event.get("event_type") != event_type:
            continue
        path = (version_dir / str(event["record_path"])).resolve(strict=True)
        path.relative_to(version_dir.resolve())
        if file_sha256(path) != event.get("record_sha256"):
            raise VoiceWorkshopError(f"History-bound record changed: {path}")
        records.append((int(event["sequence"]), path, _read_object(path)))
    return records


def select_clean_master(
    version_dir: Path,
    request: dict[str, Any],
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    path = _resolve_version_dir(version_dir, project_root)
    manifest = _load_version(path)
    selection_id = _require_id(request.get("selection_id"), "selection_id")
    selected_by = _require_id(request.get("selected_by"), "selected_by")
    selected_at = _require_timestamp(request.get("selected_at"), "selected_at")
    latest_by_candidate: dict[str, tuple[int, dict[str, Any]]] = {}
    for sequence, _record_path, record in _history_records(
        path, "candidate_review_appended"
    ):
        candidate_sha = str(record.get("candidate", {}).get("sha256") or "")
        latest_by_candidate[candidate_sha] = (sequence, record)

    eligible: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for sequence, record in latest_by_candidate.values():
        if record.get("decision") != "accepted_clean_master_candidate":
            continue
        technical = record.get("technical_report") if isinstance(record.get("technical_report"), dict) else {}
        if technical.get("passed") is not True:
            continue
        duration = float(technical.get("duration_seconds") or 0.0)
        clipping = float(technical.get("clipping_ratio") or 0.0)
        silence = float(technical.get("silence_ratio") or 0.0)
        rms = float(technical.get("rms_dbfs") or -99.0)
        peak = float(technical.get("peak_dbfs") or -99.0)
        candidate_sha = str(record.get("candidate", {}).get("sha256") or "")
        score = (
            round(abs(duration - 8.0), 9),
            round(clipping, 9),
            round(silence, 9),
            round(abs(rms + 22.0), 9),
            round(abs(peak + 6.0), 9),
            candidate_sha,
        )
        eligible.append(
            (
                score,
                {
                    "history_sequence": sequence,
                    "review_id": record["review_id"],
                    "candidate": deepcopy(record["candidate"]),
                    "technical_report": deepcopy(technical),
                    "deterministic_score": list(score),
                },
            )
        )
    if not eligible:
        raise VoiceWorkshopError("No latest accepted candidate passes the exact 6–10 second clean-master gate.")
    eligible.sort(key=lambda item: item[0])
    selected = eligible[0][1]
    expected = str(request.get("expected_candidate_sha256") or "").strip().lower()
    if expected and _require_sha256(expected, "expected_candidate_sha256") != selected["candidate"]["sha256"]:
        raise VoiceWorkshopError("Deterministic selection did not match expected_candidate_sha256.")
    result = {
        "record_type": "clean_master_selection",
        "schema_version": SCHEMA_VERSION,
        "status": "inactive_reference_candidate_selected_no_audio_created",
        "selection_id": selection_id,
        "person_id": manifest["person_id"],
        "profile_id": manifest["profile_id"],
        "version_id": manifest["version_id"],
        "selected_by": selected_by,
        "selected_at": selected_at,
        "selected": selected,
        "eligible_candidate_count": len(eligible),
        "selection_rule": "min(abs(duration-8), clipping, silence, abs(rms+22), abs(peak+6), sha256)",
        "long_concatenation_used": False,
        "audio_created": False,
    }
    output = path / "selections" / f"{selection_id}.json"
    _write_json_exclusive(output, result)
    _append_history(
        path,
        event_type="clean_master_selected",
        actor_id=selected_by,
        record_path=output,
        recorded_at=selected_at,
    )
    return result


def _load_version_record(
    version_dir: Path,
    relative_path: object,
    expected_sha256: object,
    expected_type: str,
) -> tuple[Path, dict[str, Any], str]:
    raw = str(relative_path or "").strip().replace("\\", "/")
    if not raw or Path(raw).is_absolute():
        raise VoiceWorkshopError("Version record path must be version-relative.")
    try:
        path = (version_dir / raw).resolve(strict=True)
        path.relative_to(version_dir.resolve())
    except (OSError, ValueError) as exc:
        raise VoiceWorkshopError(f"Missing or escaping version record: {raw}") from exc
    actual = file_sha256(path)
    if actual != _require_sha256(expected_sha256, f"{expected_type}_sha256"):
        raise VoiceWorkshopError(f"Hash mismatch for {expected_type}.")
    data = _read_object(path)
    if data.get("record_type") != expected_type:
        raise VoiceWorkshopError(f"Expected {expected_type}, got {data.get('record_type')!r}.")
    return path, data, actual


def _load_project_workshop_record(
    project_root: Path,
    project_relative_path: object,
    expected_sha256: object,
    expected_type: str,
) -> tuple[Path, dict[str, Any], str]:
    path = resolve_project_file(
        project_relative_path,
        project_root=project_root,
        suffixes={".json"},
    )
    try:
        path.relative_to((project_root.resolve() / WORKSHOP_RELATIVE_ROOT).resolve())
    except ValueError as exc:
        raise VoiceWorkshopError(
            "Cross-version records must remain under Voice/workshop."
        ) from exc
    actual = file_sha256(path)
    if actual != _require_sha256(expected_sha256, f"{expected_type}_sha256"):
        raise VoiceWorkshopError(f"Hash mismatch for {expected_type}.")
    data = _read_object(path)
    if data.get("record_type") != expected_type:
        raise VoiceWorkshopError(f"Expected {expected_type}, got {data.get('record_type')!r}.")
    return path, data, actual


def create_preview_request(
    version_dir: Path,
    request: dict[str, Any],
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    path = _resolve_version_dir(version_dir, project_root)
    manifest = _load_version(path)
    preview_id = _require_id(request.get("preview_id"), "preview_id")
    requested_by = _require_id(request.get("requested_by"), "requested_by")
    requested_at = _require_timestamp(request.get("requested_at"), "requested_at")
    _selection_path, selection, selection_sha = _load_version_record(
        path,
        request.get("selection_path"),
        request.get("selection_sha256"),
        "clean_master_selection",
    )
    for key in ("person_id", "profile_id", "version_id"):
        if selection.get(key) != manifest.get(key):
            raise VoiceWorkshopError(f"Preview selection {key} mismatch.")
    profile_path, profile_sha = _verified_file_binding(
        request,
        "profile_path",
        "profile_sha256",
        project_root=project_root,
        suffixes={".json"},
    )
    profile = _read_object(profile_path)
    if str(profile.get("profile_id") or "") != manifest["profile_id"]:
        raise VoiceWorkshopError("Inactive profile file profile_id mismatch.")
    model = request.get("model_contract") if isinstance(request.get("model_contract"), dict) else {}
    if (
        model.get("engine") != "chatterbox_tts"
        or model.get("model_name") != "chatterbox-tts"
        or str(model.get("model_version") or "") != "0.1.7"
    ):
        raise VoiceWorkshopError("Preview model contract must be chatterbox-tts 0.1.7.")
    _verified_file_binding(
        model,
        "config_path",
        "config_sha256",
        project_root=project_root,
        suffixes={".json"},
    )
    for flag in (
        "playback_allowed",
        "auto_activate",
        "generic_voice_fallback_allowed",
        "sapi_fallback_allowed",
    ):
        if request.get(flag) is not False:
            raise VoiceWorkshopError(f"Preview request requires {flag}=false.")
    phrases = request.get("phrases") if isinstance(request.get("phrases"), list) else []
    if not 1 <= len(phrases) <= 20:
        raise VoiceWorkshopError("Preview request needs 1–20 phrases.")
    normalized_phrases: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in phrases:
        if not isinstance(item, dict):
            raise VoiceWorkshopError("Every preview phrase must be an object.")
        phrase_id = _require_id(item.get("phrase_id"), "phrase_id")
        if phrase_id in seen:
            raise VoiceWorkshopError("Preview phrase ids must be unique.")
        seen.add(phrase_id)
        text = _require_text(item.get("text"), "phrase.text")
        if len(text) > 400:
            raise VoiceWorkshopError("Preview phrase exceeds 400 characters.")
        if any(marker in text.casefold() for marker in PRIVATE_MARKERS):
            raise VoiceWorkshopError("Preview phrase contains a non-public channel marker.")
        normalized_phrases.append(
            {
                "phrase_id": phrase_id,
                "text": text,
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
    result = {
        "record_type": "preview_request",
        "schema_version": SCHEMA_VERSION,
        "status": "request_only_no_synthesis_performed",
        "preview_id": preview_id,
        "person_id": manifest["person_id"],
        "profile_id": manifest["profile_id"],
        "version_id": manifest["version_id"],
        "requested_by": requested_by,
        "requested_at": requested_at,
        "selection_path": str(request["selection_path"]).replace("\\", "/"),
        "selection_sha256": selection_sha,
        "reference_path": selection["selected"]["candidate"]["path"],
        "reference_sha256": selection["selected"]["candidate"]["sha256"],
        "profile_path": _relative(project_root, profile_path),
        "profile_sha256": profile_sha,
        "model_contract": deepcopy(model),
        "phrases": normalized_phrases,
        "playback_allowed": False,
        "auto_activate": False,
        "generic_voice_fallback_allowed": False,
        "sapi_fallback_allowed": False,
        "workshop_generated_audio": False,
    }
    output = path / "previews" / "requests" / f"{preview_id}.json"
    _write_json_exclusive(output, result)
    _append_history(
        path,
        event_type="preview_requested",
        actor_id=requested_by,
        record_path=output,
        recorded_at=requested_at,
    )
    return result


def record_preview_result(
    version_dir: Path,
    result_input: dict[str, Any],
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    path = _resolve_version_dir(version_dir, project_root)
    manifest = _load_version(path)
    result_id = _require_id(result_input.get("result_id"), "result_id")
    recorded_by = _require_id(result_input.get("recorded_by"), "recorded_by")
    recorded_at = _require_timestamp(result_input.get("recorded_at"), "recorded_at")
    _request_path, request, request_sha = _load_version_record(
        path,
        result_input.get("request_path"),
        result_input.get("request_sha256"),
        "preview_request",
    )
    for key in ("person_id", "profile_id", "version_id"):
        if request.get(key) != manifest.get(key):
            raise VoiceWorkshopError(f"Preview request {key} mismatch.")
    route = result_input.get("route") if isinstance(result_input.get("route"), dict) else {}
    required_route = {
        "engine": "chatterbox_tts",
        "profile_sha256": request["profile_sha256"],
        "reference_sha256": request["reference_sha256"],
        "generic_voice_used": False,
        "sapi_voice_used": False,
        "playback": False,
    }
    for key, expected in required_route.items():
        if route.get(key) != expected:
            raise VoiceWorkshopError(f"Preview route mismatch: {key} must be {expected!r}.")
    expected_phrases = {item["phrase_id"]: item for item in request["phrases"]}
    outputs = result_input.get("outputs") if isinstance(result_input.get("outputs"), list) else []
    if len(outputs) != len(expected_phrases):
        raise VoiceWorkshopError("Preview result must contain exactly one output per requested phrase.")
    normalized_outputs: list[dict[str, Any]] = []
    seen: set[str] = set()
    allowed_audio_root = (path / "preview_audio").resolve()
    for item in outputs:
        if not isinstance(item, dict):
            raise VoiceWorkshopError("Every preview output must be an object.")
        phrase_id = _require_id(item.get("phrase_id"), "output.phrase_id")
        if phrase_id in seen or phrase_id not in expected_phrases:
            raise VoiceWorkshopError("Preview output phrase id is duplicate or unrequested.")
        seen.add(phrase_id)
        if item.get("text_sha256") != expected_phrases[phrase_id]["text_sha256"]:
            raise VoiceWorkshopError("Preview output text hash mismatch.")
        wav_path, wav_sha = _verified_file_binding(
            item,
            "path",
            "sha256",
            project_root=project_root,
            suffixes={".wav"},
        )
        try:
            wav_path.relative_to(allowed_audio_root)
        except ValueError as exc:
            raise VoiceWorkshopError("Preview WAV must be under this version's preview_audio directory.") from exc
        technical = inspect_pcm_wav(
            wav_path, project_root=project_root, purpose="preview_output"
        )
        if technical["passed"] is not True:
            raise VoiceWorkshopError(
                f"Preview WAV {phrase_id} failed signal gates: "
                + ", ".join(technical["reasons"])
            )
        normalized_outputs.append(
            {
                "phrase_id": phrase_id,
                "text_sha256": item["text_sha256"],
                "path": _relative(project_root, wav_path),
                "sha256": wav_sha,
                "technical_report": technical,
            }
        )
    result = {
        "record_type": "preview_result_receipt",
        "schema_version": SCHEMA_VERSION,
        "status": "external_preview_recorded_unapproved_inactive",
        "result_id": result_id,
        "preview_id": request["preview_id"],
        "person_id": manifest["person_id"],
        "profile_id": manifest["profile_id"],
        "version_id": manifest["version_id"],
        "recorded_by": recorded_by,
        "recorded_at": recorded_at,
        "request_path": str(result_input["request_path"]).replace("\\", "/"),
        "request_sha256": request_sha,
        "route": deepcopy(route),
        "outputs": sorted(normalized_outputs, key=lambda item: item["phrase_id"]),
        "generated_by_external_harness": True,
        "workshop_generated_audio": False,
        "playback_performed_by_workshop": False,
        "activation_performed": False,
    }
    output = path / "previews" / "results" / f"{result_id}.json"
    _write_json_exclusive(output, result)
    _append_history(
        path,
        event_type="preview_result_recorded",
        actor_id=recorded_by,
        record_path=output,
        recorded_at=recorded_at,
    )
    return result


_APPROVAL_CONTRACTS = {
    "preview": ("preview_result_receipt", OWNER_PREVIEW_APPROVAL_TEXT),
    "promotion": ("promotion_proposal", OWNER_PROMOTION_APPROVAL_TEXT),
    "rollback": ("rollback_proposal", OWNER_ROLLBACK_APPROVAL_TEXT),
}


def record_owner_approval(
    version_dir: Path,
    approval: dict[str, Any],
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    path = _resolve_version_dir(version_dir, project_root)
    manifest = _load_version(path)
    approval_id = _require_id(approval.get("approval_id"), "approval_id")
    kind = str(approval.get("approval_kind") or "").strip()
    if kind not in _APPROVAL_CONTRACTS:
        raise VoiceWorkshopError("approval_kind must be preview, promotion, or rollback.")
    expected_type, expected_text = _APPROVAL_CONTRACTS[kind]
    owner_id = _require_id(approval.get("owner_id"), "owner_id")
    approved_at = _require_timestamp(approval.get("approved_at"), "approved_at")
    if str(approval.get("confirmation_text") or "") != expected_text:
        raise VoiceWorkshopError(f"Exact owner confirmation required: {expected_text}")
    _target_path, target, target_sha = _load_version_record(
        path,
        approval.get("target_path"),
        approval.get("target_sha256"),
        expected_type,
    )
    for key in ("person_id", "profile_id", "version_id"):
        if target.get(key) != manifest.get(key):
            raise VoiceWorkshopError(f"Approval target {key} mismatch.")
    result = {
        "record_type": "owner_approval_receipt",
        "schema_version": SCHEMA_VERSION,
        "status": "explicit_owner_approval_recorded_no_activation",
        "approval_id": approval_id,
        "approval_kind": kind,
        "person_id": manifest["person_id"],
        "profile_id": manifest["profile_id"],
        "version_id": manifest["version_id"],
        "owner_id": owner_id,
        "approved_at": approved_at,
        "confirmation_text": expected_text,
        "target_path": str(approval["target_path"]).replace("\\", "/"),
        "target_sha256": target_sha,
        "scope": f"exact_inactive_{kind}_record_only",
        "activation_performed": False,
    }
    output = path / "approvals" / f"{approval_id}.json"
    _write_json_exclusive(output, result)
    _append_history(
        path,
        event_type=f"owner_{kind}_approval_recorded",
        actor_id=owner_id,
        record_path=output,
        recorded_at=approved_at,
    )
    return result


def validate_sealed_route_receipt(
    receipt: dict[str, Any],
    *,
    expected_device: str,
    expected_role: str,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    if receipt.get("record_type") != "sealed_route_receipt":
        raise VoiceWorkshopError("Route evidence is not a sealed_route_receipt.")
    _require_id(receipt.get("seal_id"), "seal_id")
    for key in ("person_id", "profile_id", "version_id"):
        _require_id(receipt.get(key), key)
    required = {
        "status": "sealed_accepted",
        "engine": "chatterbox_tts",
        "compute_device": expected_device,
        "route_role": expected_role,
        "input_channel": "public_spoken_only",
        "offline_cache_only": True,
        "playback": False,
        "generic_voice_fallback_allowed": False,
        "sapi_fallback_allowed": False,
        "separately_sealed": True,
    }
    for key, expected in required.items():
        if receipt.get(key) != expected:
            raise VoiceWorkshopError(f"Sealed route {key} must be {expected!r}.")
    bindings = (
        ("profile_path", "profile_sha256", {".json"}),
        ("reference_path", "reference_sha256", {".wav"}),
        ("worker_path", "worker_sha256", {".py"}),
        ("config_path", "config_sha256", {".json"}),
        ("acceptance_path", "acceptance_sha256", {".json"}),
    )
    normalized = deepcopy(receipt)
    for path_key, hash_key, suffixes in bindings:
        file_path, actual = _verified_file_binding(
            receipt,
            path_key,
            hash_key,
            project_root=project_root,
            suffixes=suffixes,
        )
        normalized[path_key] = _relative(project_root, file_path)
        normalized[hash_key] = actual
    return normalized


def create_promotion_proposal(
    version_dir: Path,
    request: dict[str, Any],
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    path = _resolve_version_dir(version_dir, project_root)
    manifest = _load_version(path)
    proposal_id = _require_id(request.get("proposal_id"), "proposal_id")
    proposed_by = _require_id(request.get("proposed_by"), "proposed_by")
    proposed_at = _require_timestamp(request.get("proposed_at"), "proposed_at")
    _selection_path, selection, selection_sha = _load_version_record(
        path, request.get("selection_path"), request.get("selection_sha256"), "clean_master_selection"
    )
    _preview_path, preview, preview_sha = _load_version_record(
        path, request.get("preview_result_path"), request.get("preview_result_sha256"), "preview_result_receipt"
    )
    _approval_path, preview_approval, preview_approval_sha = _load_version_record(
        path, request.get("preview_approval_path"), request.get("preview_approval_sha256"), "owner_approval_receipt"
    )
    if preview_approval.get("approval_kind") != "preview" or preview_approval.get("target_sha256") != preview_sha:
        raise VoiceWorkshopError("Promotion requires exact owner approval of this preview result.")
    profile_path, profile_sha = _verified_file_binding(
        request,
        "profile_path",
        "profile_sha256",
        project_root=project_root,
        suffixes={".json"},
    )
    profile = _read_object(profile_path)
    if str(profile.get("profile_id") or "") != manifest["profile_id"]:
        raise VoiceWorkshopError("Promotion profile_id mismatch.")
    gpu_path, gpu_raw, gpu_receipt_sha = _load_version_record(
        path, request.get("gpu_seal_path"), request.get("gpu_seal_sha256"), "sealed_route_receipt"
    )
    cpu_path, cpu_raw, cpu_receipt_sha = _load_version_record(
        path, request.get("cpu_seal_path"), request.get("cpu_seal_sha256"), "sealed_route_receipt"
    )
    gpu = validate_sealed_route_receipt(
        gpu_raw,
        expected_device="cuda",
        expected_role="preferred",
        project_root=project_root,
    )
    cpu = validate_sealed_route_receipt(
        cpu_raw,
        expected_device="cpu",
        expected_role="same_identity_automatic_fallback_only",
        project_root=project_root,
    )
    if gpu["seal_id"] == cpu["seal_id"]:
        raise VoiceWorkshopError("GPU and CPU routes need separately sealed receipts.")
    exact_identity = (
        manifest["person_id"],
        manifest["profile_id"],
        manifest["version_id"],
    )
    for route in (gpu, cpu):
        if (route["person_id"], route["profile_id"], route["version_id"]) != exact_identity:
            raise VoiceWorkshopError("Sealed route exact identity mismatch.")
    reference_sha = selection["selected"]["candidate"]["sha256"]
    reference_path = selection["selected"]["candidate"]["path"]
    for route in (gpu, cpu):
        if route["profile_sha256"] != profile_sha or route["reference_sha256"] != reference_sha:
            raise VoiceWorkshopError("GPU/CPU route is not the same exact profile/reference identity.")
        if route["reference_path"] != reference_path:
            raise VoiceWorkshopError("Sealed route reference path does not match clean-master selection.")
    if preview.get("route", {}).get("profile_sha256") != profile_sha or preview.get("route", {}).get("reference_sha256") != reference_sha:
        raise VoiceWorkshopError("Preview did not use the exact promotion profile/reference.")
    rollback_target = request.get("rollback_target")
    if rollback_target is not None and not isinstance(rollback_target, dict):
        raise VoiceWorkshopError("rollback_target must be an object or null.")
    if isinstance(rollback_target, dict):
        for key in ("proposal_path", "proposal_sha256", "approval_path", "approval_sha256"):
            _require_text(rollback_target.get(key), f"rollback_target.{key}")
        _require_sha256(rollback_target["proposal_sha256"], "rollback_target.proposal_sha256")
        _require_sha256(rollback_target["approval_sha256"], "rollback_target.approval_sha256")
    result = {
        "record_type": "promotion_proposal",
        "schema_version": SCHEMA_VERSION,
        "status": "inactive_hash_bound_proposal_awaiting_exact_owner_promotion_approval",
        "proposal_id": proposal_id,
        "person_id": manifest["person_id"],
        "profile_id": manifest["profile_id"],
        "version_id": manifest["version_id"],
        "proposed_by": proposed_by,
        "proposed_at": proposed_at,
        "profile_path": _relative(project_root, profile_path),
        "profile_sha256": profile_sha,
        "reference_path": reference_path,
        "reference_sha256": reference_sha,
        "selection_path": str(request["selection_path"]).replace("\\", "/"),
        "selection_sha256": selection_sha,
        "preview_result_path": str(request["preview_result_path"]).replace("\\", "/"),
        "preview_result_sha256": preview_sha,
        "preview_approval_path": str(request["preview_approval_path"]).replace("\\", "/"),
        "preview_approval_sha256": preview_approval_sha,
        "preferred_route": {
            "receipt_path": gpu_path.relative_to(path).as_posix(),
            "receipt_sha256": gpu_receipt_sha,
            "seal_id": gpu["seal_id"],
            "device": "cuda",
        },
        "automatic_fallback": {
            "receipt_path": cpu_path.relative_to(path).as_posix(),
            "receipt_sha256": cpu_receipt_sha,
            "seal_id": cpu["seal_id"],
            "device": "cpu",
            "same_exact_identity": True,
        },
        "policy": {
            "generic_voice_fallback_allowed": False,
            "sapi_fallback_allowed": False,
            "fallback_if_both_sealed_routes_fail": "text_only_voice_unavailable",
            "activation_or_default_change_allowed_by_this_record": False,
        },
        "rollback_target": deepcopy(rollback_target),
        "activation_performed": False,
        "default_changed": False,
        "apply_operation_exists": False,
    }
    output = path / "proposals" / "promotion" / f"{proposal_id}.json"
    _write_json_exclusive(output, result)
    _append_history(
        path,
        event_type="inactive_promotion_proposed",
        actor_id=proposed_by,
        record_path=output,
        recorded_at=proposed_at,
    )
    return result


def create_rollback_proposal(
    version_dir: Path,
    request: dict[str, Any],
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    path = _resolve_version_dir(version_dir, project_root)
    manifest = _load_version(path)
    rollback_id = _require_id(request.get("rollback_id"), "rollback_id")
    proposed_by = _require_id(request.get("proposed_by"), "proposed_by")
    proposed_at = _require_timestamp(request.get("proposed_at"), "proposed_at")
    bindings: dict[str, Any] = {}
    for prefix in ("current", "target"):
        proposal_path, proposal, proposal_sha = _load_project_workshop_record(
            project_root,
            request.get(f"{prefix}_proposal_path"),
            request.get(f"{prefix}_proposal_sha256"),
            "promotion_proposal",
        )
        approval_path, approval, approval_sha = _load_project_workshop_record(
            project_root,
            request.get(f"{prefix}_approval_path"),
            request.get(f"{prefix}_approval_sha256"),
            "owner_approval_receipt",
        )
        if approval.get("approval_kind") != "promotion" or approval.get("target_sha256") != proposal_sha:
            raise VoiceWorkshopError(f"{prefix} promotion lacks exact owner approval.")
        for key in ("person_id", "profile_id", "version_id"):
            if approval.get(key) != proposal.get(key):
                raise VoiceWorkshopError(
                    f"{prefix} approval/proposal {key} binding mismatch."
                )
        if proposal.get("person_id") != manifest["person_id"]:
            raise VoiceWorkshopError(f"{prefix} proposal person_id mismatch.")
        if proposal.get("profile_id") != manifest["profile_id"]:
            raise VoiceWorkshopError(f"{prefix} proposal profile_id mismatch.")
        if prefix == "current" and proposal.get("version_id") != manifest["version_id"]:
            raise VoiceWorkshopError(
                "Current proposal must belong to the version receiving the rollback proposal."
            )
        bindings[prefix] = {
            "proposal_path": _relative(project_root, proposal_path),
            "proposal_sha256": proposal_sha,
            "approval_path": _relative(project_root, approval_path),
            "approval_sha256": approval_sha,
            "proposal_id": proposal["proposal_id"],
            "version_id": proposal["version_id"],
            "profile_sha256": proposal["profile_sha256"],
            "reference_sha256": proposal["reference_sha256"],
        }
    if bindings["current"]["proposal_sha256"] == bindings["target"]["proposal_sha256"]:
        raise VoiceWorkshopError("Rollback target must differ from the current proposal.")
    result = {
        "record_type": "rollback_proposal",
        "schema_version": SCHEMA_VERSION,
        "status": "inactive_hash_bound_rollback_proposal_not_applied",
        "rollback_id": rollback_id,
        "person_id": manifest["person_id"],
        "profile_id": manifest["profile_id"],
        "version_id": manifest["version_id"],
        "proposed_by": proposed_by,
        "proposed_at": proposed_at,
        "current": bindings["current"],
        "target": bindings["target"],
        "requires_exact_owner_rollback_approval": True,
        "activation_performed": False,
        "default_changed": False,
        "apply_operation_exists": False,
    }
    output = path / "proposals" / "rollback" / f"{rollback_id}.json"
    _write_json_exclusive(output, result)
    _append_history(
        path,
        event_type="inactive_rollback_proposed",
        actor_id=proposed_by,
        record_path=output,
        recorded_at=proposed_at,
    )
    return result


def verify_version(
    version_dir: Path, *, project_root: Path = PROJECT_ROOT
) -> dict[str, Any]:
    path = _resolve_version_dir(version_dir, project_root)
    manifest = _load_version(path)
    events = validate_history(path)
    permission = _read_object(path / "permission_record.json")
    permission_valid = validate_permission_record(permission, project_root=project_root)
    if (permission_valid["person_id"], permission_valid["profile_id"]) != (
        manifest["person_id"],
        manifest["profile_id"],
    ):
        raise VoiceWorkshopError("Stored permission no longer matches version identity.")
    records: list[dict[str, Any]] = []
    for event in events:
        record = (path / event["record_path"]).resolve(strict=True)
        record.relative_to(path)
        actual = file_sha256(record)
        if actual != event["record_sha256"]:
            raise VoiceWorkshopError(f"History-bound record changed: {event['record_path']}")
        records.append({"path": event["record_path"], "sha256": actual})
    return {
        "record_type": "voice_workshop_verification",
        "schema_version": SCHEMA_VERSION,
        "status": "verified_inactive_no_runtime_change",
        "person_id": manifest["person_id"],
        "profile_id": manifest["profile_id"],
        "version_id": manifest["version_id"],
        "history_event_count": len(events),
        "history_head_sha256": events[-1]["event_sha256"] if events else "",
        "records": records,
        "audio_generated": False,
        "audio_played": False,
        "model_loaded": False,
        "activation_performed": False,
    }
