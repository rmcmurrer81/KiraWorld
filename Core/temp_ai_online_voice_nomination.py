"""Fail-closed online voice-source nomination for TemporaryAI candidates.

This stage answers *which exact web sources and time ranges should a later,
authorized machine-analysis pass inspect first*.  It deliberately does not
download media, extract audio, train/clone a voice, assign a voice, synthesize
speech, or activate a candidate.

Metadata, an owner's source nomination, acoustic clustering, and a video title
are useful ranking evidence; none of them is speaker-identity proof.  A range
can pass the optional machine-evidence gate only when exact URL/range bindings,
an owner-approved face reference, active-speaker evidence, single-speaker
evidence, and conservative audio-quality measurements all pass.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import shutil
import sys
import wave
from array import array
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from Core.temp_ai_voice_discovery import (
    CANDIDATE_ROOT,
    canonical_url,
    fetch_video_metadata,
    resolve_candidate_dir,
    search_video_metadata,
    slug,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUEST_FILENAME = "automatic_voice_source_nomination_request.json"
RESULT_FILENAME = "automatic_voice_source_nominations.json"
OWNER_REVIEW_FILENAME = "automatic_voice_source_owner_range_review.json"
SCHEMA_VERSION = 1
MAX_URLS = 12
MAX_SEARCH_QUERIES = 6
MAX_SEARCH_RESULTS_PER_QUERY = 10
MAX_RANGE_SECONDS = 45.0

MUSIC_TERMS = {
    "karaoke",
    "lyrics",
    "mmd",
    "music video",
    "official audio",
    "parody",
    "sing along",
    "sing-along",
    "song",
    "soundtrack",
    "withoutmusic",
}
MIXED_SOURCE_TERMS = {
    "behind the scenes",
    "cast",
    "compilation",
    "explains",
    "interview",
    "reaction",
    "rehearsal",
    "teaser",
    "trailer",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _finite_number(value: Any, *, field: str, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite number.") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number.")
    if minimum is not None and number < minimum:
        raise ValueError(f"{field} must be >= {minimum}.")
    if maximum is not None and number > maximum:
        raise ValueError(f"{field} must be <= {maximum}.")
    return number


def _unique_strings(values: Iterable[Any], *, maximum: int, field: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
        if len(result) > maximum:
            raise ValueError(f"{field} accepts at most {maximum} entries.")
    return result


def build_nomination_request(
    *,
    candidate_id: str,
    target_name: str,
    version: str,
    speaker: str,
    performer: str,
    urls: Iterable[str],
    start_seconds: float = 0.0,
    end_seconds: float | None = None,
    owner_nominated_target_only: bool = False,
    owner_note: str = "",
    search_queries: Iterable[str] = (),
) -> dict[str, Any]:
    """Build one bounded, metadata-only source-nomination request."""

    if not candidate_id or slug(candidate_id) != candidate_id:
        raise ValueError("candidate_id must be a normalized lowercase identifier.")
    target_name = str(target_name or "").strip()
    version = str(version or "").strip()
    speaker = str(speaker or "").strip()
    performer = str(performer or "").strip()
    if not target_name or not version or not speaker:
        raise ValueError("target_name, version, and speaker are required.")

    queries = _unique_strings(search_queries, maximum=MAX_SEARCH_QUERIES, field="search_queries")
    normalized_urls = _unique_strings(
        (canonical_url(item) for item in urls), maximum=MAX_URLS, field="urls"
    )
    if not normalized_urls and not queries:
        raise ValueError("At least one exact source URL or bounded metadata-search query is required.")
    start = _finite_number(start_seconds, field="start_seconds", minimum=0.0)
    end = None if end_seconds is None else _finite_number(end_seconds, field="end_seconds", minimum=0.0)
    if end is not None:
        if end <= start:
            raise ValueError("end_seconds must be greater than start_seconds.")
        if end - start > MAX_RANGE_SECONDS:
            raise ValueError(f"One nominated range cannot exceed {MAX_RANGE_SECONDS:g} seconds.")

    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": f"{candidate_id}_automatic_voice_source_nomination_v1",
        "created_at": now_iso(),
        "candidate_id": candidate_id,
        "identity_target": {
            "target_name": target_name,
            "version": version,
            "speaker": speaker,
            "performer": performer,
        },
        "sources": [
            {
                "url": url,
                "origin": "explicit_seed_url",
                "nominated_start_seconds": start,
                "nominated_end_seconds": end,
                "owner_nominated_target_only": bool(owner_nominated_target_only),
                "owner_note": str(owner_note or "").strip(),
            }
            for url in normalized_urls
        ],
        "search_queries": queries,
        "policy": {
            "metadata_only": True,
            "allow_media_download": False,
            "allow_audio_extraction": False,
            "allow_voice_training_or_cloning": False,
            "allow_voice_assignment": False,
            "allow_synthesis": False,
            "allow_candidate_activation": False,
            "owner_nomination_is_ranking_evidence_not_identity_proof": True,
            "machine_identity_must_fail_closed": True,
        },
    }


def request_from_candidate(
    candidate_id: str,
    *,
    urls: Iterable[str],
    start_seconds: float = 0.0,
    end_seconds: float | None = None,
    owner_nominated_target_only: bool = False,
    owner_note: str = "",
    search_queries: Iterable[str] = (),
) -> dict[str, Any]:
    """Bind a request to the candidate's existing exact identity record."""

    candidate_dir = resolve_candidate_dir(candidate_id)
    discovery = read_json(candidate_dir / "voice_discovery_request.json", {})
    identity = discovery.get("identity_target") if isinstance(discovery.get("identity_target"), dict) else {}
    variant = identity.get("variant") if isinstance(identity.get("variant"), dict) else {}
    speaker = identity.get("speaker") if isinstance(identity.get("speaker"), dict) else {}
    performer = identity.get("performer") if isinstance(identity.get("performer"), dict) else {}
    character = identity.get("character") if isinstance(identity.get("character"), dict) else {}
    return build_nomination_request(
        candidate_id=candidate_id,
        target_name=str(character.get("label") or identity.get("display_name") or ""),
        version=str(identity.get("version_or_timepoint") or variant.get("label") or ""),
        speaker=str(speaker.get("label") or identity.get("display_name") or ""),
        performer=str(performer.get("name") or ""),
        urls=urls,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        owner_nominated_target_only=owner_nominated_target_only,
        owner_note=owner_note,
        search_queries=search_queries,
    )


def validate_nomination_request(request: dict[str, Any], *, expected_candidate_id: str = "") -> None:
    if int(request.get("schema_version", 0) or 0) != SCHEMA_VERSION:
        raise ValueError(f"nomination schema_version must be {SCHEMA_VERSION}.")
    candidate_id = str(request.get("candidate_id") or "")
    if not candidate_id or slug(candidate_id) != candidate_id:
        raise ValueError("nomination candidate_id is invalid.")
    if expected_candidate_id and candidate_id != expected_candidate_id:
        raise ValueError("nomination candidate_id does not match its candidate folder.")
    target = request.get("identity_target") if isinstance(request.get("identity_target"), dict) else {}
    for key in ("target_name", "version", "speaker"):
        if not str(target.get(key) or "").strip():
            raise ValueError(f"identity_target.{key} is required.")
    sources = request.get("sources")
    if not isinstance(sources, list) or len(sources) > MAX_URLS:
        raise ValueError(f"sources must contain 0-{MAX_URLS} items.")
    queries = request.get("search_queries")
    if not isinstance(queries, list) or len(queries) > MAX_SEARCH_QUERIES:
        raise ValueError(f"search_queries must contain 0-{MAX_SEARCH_QUERIES} items.")
    if not sources and not queries:
        raise ValueError("A nomination request needs a seed source or bounded search query.")
    for item in sources:
        if not isinstance(item, dict):
            raise ValueError("Every source must be an object.")
        canonical_url(str(item.get("url") or ""))
        start = _finite_number(item.get("nominated_start_seconds", 0), field="nominated_start_seconds", minimum=0)
        if item.get("nominated_end_seconds") is not None:
            end = _finite_number(item.get("nominated_end_seconds"), field="nominated_end_seconds", minimum=0)
            if end <= start or end - start > MAX_RANGE_SECONDS:
                raise ValueError("Each explicit source range must be positive and no longer than 45 seconds.")
    policy = request.get("policy") if isinstance(request.get("policy"), dict) else {}
    if policy.get("metadata_only") is not True:
        raise ValueError("Automatic online nomination is metadata-only.")
    forbidden = (
        "allow_media_download",
        "allow_audio_extraction",
        "allow_voice_training_or_cloning",
        "allow_voice_assignment",
        "allow_synthesis",
        "allow_candidate_activation",
    )
    enabled = [name for name in forbidden if policy.get(name) not in {False, None}]
    if enabled:
        raise ValueError(f"Online nomination cannot enable: {', '.join(enabled)}")


def _metadata_text(metadata: dict[str, Any]) -> str:
    return " ".join(
        str(metadata.get(key) or "")
        for key in ("title", "publisher", "channel", "description")
    ).casefold()


def _word_match(text: str, label: str) -> bool:
    words = [word for word in re.findall(r"[a-z0-9]+", str(label).casefold()) if len(word) >= 3]
    return bool(words) and all(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


def _capability_status() -> dict[str, Any]:
    def available(name: str) -> bool:
        try:
            return importlib.util.find_spec(name) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            return False

    return {
        "yt_dlp_metadata_provider": bool(shutil.which("yt-dlp") or available("yt_dlp")),
        "local_audio_quality_libraries": {
            "torch": available("torch"),
            "torchaudio": available("torchaudio"),
            "librosa": available("librosa"),
            "soundfile": available("soundfile"),
        },
        "local_visual_identity_and_active_speaker": {
            "opencv": available("cv2"),
            "mediapipe": available("mediapipe"),
            "pyannote": available("pyannote"),
            "status": "unavailable_until_an_authorized_local_media_analyzer_and_reference_binding_exist",
        },
        "external_exact_bound_machine_evidence_supported": True,
    }


def _resolve_project_evidence_file(raw_path: Path | str, *, field: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if path.is_symlink():
        raise ValueError(f"{field} cannot be a symlink.")
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{field} must stay inside the Kira project.") from exc
    if not resolved.is_file():
        raise ValueError(f"{field} must be a regular file.")
    return resolved


def analyze_pcm_wav_quality(raw_path: Path | str) -> dict[str, Any]:
    """Measure bounded PCM-WAV diagnostics without making music/identity claims."""

    path = _resolve_project_evidence_file(raw_path, field="local_wav")
    with wave.open(str(path), "rb") as source:
        channels = source.getnchannels()
        sample_width = source.getsampwidth()
        sample_rate = source.getframerate()
        frame_count = source.getnframes()
        compression = source.getcomptype()
        raw = source.readframes(frame_count)
    if compression != "NONE" or sample_width != 2:
        raise ValueError("local_wav must be uncompressed 16-bit PCM WAV.")
    if channels < 1 or channels > 2 or sample_rate < 8000 or not raw:
        raise ValueError("local_wav has unsupported or empty audio parameters.")

    values = array("h")
    values.frombytes(raw)
    if sys.byteorder != "little":
        values.byteswap()
    if channels == 2:
        mono = [(values[index] + values[index + 1]) / 2.0 for index in range(0, len(values) - 1, 2)]
    else:
        mono = [float(value) for value in values]
    normalized = [value / 32768.0 for value in mono]
    frame_size = max(1, round(sample_rate * 0.020))
    frame_db: list[float] = []
    for start in range(0, len(normalized) - frame_size + 1, frame_size):
        frame = normalized[start : start + frame_size]
        rms = math.sqrt(sum(value * value for value in frame) / len(frame))
        frame_db.append(20.0 * math.log10(max(rms, 1e-8)))
    if not frame_db:
        raise ValueError("local_wav is too short for quality diagnostics.")

    def percentile(values_to_rank: list[float], fraction: float) -> float:
        ranked = sorted(values_to_rank)
        position = max(0, min(len(ranked) - 1, round((len(ranked) - 1) * fraction)))
        return ranked[position]

    overall_rms = math.sqrt(sum(value * value for value in normalized) / len(normalized))
    noise_floor = percentile(frame_db, 0.10)
    speech_level = percentile(frame_db, 0.90)
    peak = max(abs(value) for value in normalized)
    clipping_ratio = sum(1 for value in normalized if abs(value) >= 0.999) / len(normalized)
    active_ratio = sum(1 for value in frame_db if value > -45.0) / len(frame_db)
    silence_ratio = sum(1 for value in frame_db if value < -50.0) / len(frame_db)
    duration = frame_count / sample_rate
    result = {
        "path": path.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": file_sha256(path),
        "bytes": path.stat().st_size,
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "sample_width_bits": sample_width * 8,
        "duration_seconds": round(duration, 6),
        "peak": round(peak, 6),
        "overall_rms_dbfs": round(20.0 * math.log10(max(overall_rms, 1e-8)), 3),
        "clipping_ratio": round(clipping_ratio, 8),
        "active_frame_ratio": round(active_ratio, 6),
        "silence_frame_ratio": round(silence_ratio, 6),
        "noise_floor_dbfs_p10_proxy": round(noise_floor, 3),
        "speech_level_dbfs_p90_proxy": round(speech_level, 3),
        "snr_db_percentile_proxy": round(speech_level - noise_floor, 3),
        "limits": [
            "Percentile SNR is a diagnostic proxy, not source-separation or a proof of no background noise.",
            "These measurements cannot identify a person, detect all music, or prove that only one speaker is present.",
        ],
    }
    result["quality_gate"] = {
        "passed": bool(
            sample_rate >= 16000
            and channels == 1
            and duration >= 6.0
            and clipping_ratio <= 0.005
            and active_ratio >= 0.35
            and silence_ratio <= 0.40
            and speech_level - noise_floor >= 15.0
            and -50.0 <= result["overall_rms_dbfs"] <= -3.0
        ),
        "thresholds": {
            "minimum_sample_rate_hz": 16000,
            "required_channels": 1,
            "minimum_duration_seconds": 6.0,
            "maximum_clipping_ratio": 0.005,
            "minimum_active_frame_ratio": 0.35,
            "maximum_silence_frame_ratio": 0.40,
            "minimum_snr_db_percentile_proxy": 15.0,
            "overall_rms_dbfs_range": [-50.0, -3.0],
        },
    }
    return result


def build_owner_attested_range_review(
    nomination_result: dict[str, Any],
    *,
    source_url: str,
    start_seconds: float,
    end_seconds: float,
    local_media_path: Path | str,
    local_wav_path: Path | str,
    owner_attestation_path: Path | str,
    contamination_evidence_path: Path | str | None = None,
) -> dict[str, Any]:
    """Bind one owner-reviewed range to source bytes and objective WAV checks.

    This can replace a hundreds-of-rows clip box for an exact short range that
    Robert has already reviewed.  It creates review evidence only.
    """

    url = canonical_url(source_url)
    start = _finite_number(start_seconds, field="start_seconds", minimum=0)
    end = _finite_number(end_seconds, field="end_seconds", minimum=0)
    if end <= start or end - start > MAX_RANGE_SECONDS:
        raise ValueError("Owner-attested range must be positive and no longer than 45 seconds.")
    candidates = nomination_result.get("ranked_target_only_candidate_ranges", [])
    match = next(
        (
            item
            for item in candidates
            if canonical_url(str(item.get("exact_url") or "")) == url
            and abs(float(item.get("candidate_range", {}).get("start_seconds", -1)) - start) <= 0.01
            and abs(float(item.get("candidate_range", {}).get("end_seconds", -1)) - end) <= 0.01
        ),
        None,
    )
    if not match:
        raise ValueError("Owner attestation does not bind an exact nominated source range.")

    media_path = _resolve_project_evidence_file(local_media_path, field="local_media")
    attestation_path = _resolve_project_evidence_file(owner_attestation_path, field="owner_attestation")
    attestation = read_json(attestation_path, {})
    if not isinstance(attestation, dict):
        raise ValueError("owner_attestation must be a JSON object.")
    attestation_range = attestation.get("range") if isinstance(attestation.get("range"), dict) else {}
    attestation_checks = {
        "reviewer_is_real_robert": attestation.get("authorized_by") == "real_robert",
        "exact_url": canonical_url(str(attestation.get("source_url") or "")) == url,
        "exact_range": bool(
            abs(float(attestation_range.get("start_seconds", -1)) - start) <= 0.01
            and abs(float(attestation_range.get("end_seconds", -1)) - end) <= 0.01
        ),
        "audiovisual_source_reviewed": attestation.get("audiovisual_source_reviewed") is True,
        "target_identity_confirmed": attestation.get("target_identity_confirmed") is True,
        "target_only_speech_confirmed": attestation.get("target_only_speech_confirmed") is True,
        "no_other_speaker_confirmed": attestation.get("no_other_speaker_confirmed") is True,
        "no_overlap_confirmed": attestation.get("no_overlap_confirmed") is True,
        "no_music_confirmed": attestation.get("no_music_confirmed") is True,
        "scope_is_review_evidence_only": attestation.get("scope") == "private_source_review_evidence_only_no_model_or_runtime_authority",
    }
    human_gate_passed = all(attestation_checks.values())
    quality = analyze_pcm_wav_quality(local_wav_path)
    contamination: dict[str, Any] = {}
    contamination_path: Path | None = None
    if contamination_evidence_path:
        contamination_path = _resolve_project_evidence_file(
            contamination_evidence_path, field="contamination_evidence"
        )
        contamination = read_json(contamination_path, {})
        if not isinstance(contamination, dict):
            raise ValueError("contamination_evidence must be a JSON object.")
    contamination_range = (
        contamination.get("range") if isinstance(contamination.get("range"), dict) else {}
    )
    contamination_checks = {
        "evidence_present": bool(contamination_path),
        "exact_url": bool(contamination_path)
        and canonical_url(str(contamination.get("source_url") or "")) == url,
        "exact_range": bool(contamination_path)
        and abs(float(contamination_range.get("start_seconds", -1)) - start) <= 0.01
        and abs(float(contamination_range.get("end_seconds", -1)) - end) <= 0.01,
        "exact_wav_sha256": bool(contamination_path)
        and str(contamination.get("wav_sha256") or "").lower() == str(quality["sha256"]).lower(),
        "analyzer_provenance": bool(
            contamination_path
            and str(contamination.get("analyzer") or "").strip()
            and str(contamination.get("analyzer_version") or "").strip()
        ),
        "no_background_tonal_or_music_residue": contamination.get(
            "background_tonal_or_music_residue_detected"
        )
        is False,
        "no_material_noise": contamination.get("material_noise_detected") is False,
        "no_overlap": contamination.get("overlap_detected") is False,
        "explicit_clean_for_direct_model_input": contamination.get(
            "clean_for_direct_model_input"
        )
        is True,
    }
    contamination_gate_passed = all(contamination_checks.values())
    expected_duration = end - start
    duration_binding_passed = abs(float(quality["duration_seconds"]) - expected_duration) <= 0.10
    metadata_music_clear = not match.get("metadata_checks", {}).get("music_terms")
    candidate_evidence_ready = bool(
        human_gate_passed
        and quality["quality_gate"]["passed"]
        and duration_binding_passed
        and metadata_music_clear
    )
    direct_reference_input_ready = bool(candidate_evidence_ready and contamination_gate_passed)
    contamination_detected = bool(
        contamination.get("background_tonal_or_music_residue_detected") is True
        or contamination.get("material_noise_detected") is True
        or contamination.get("overlap_detected") is True
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "review_id": f"{nomination_result.get('candidate_id', 'candidate')}_owner_attested_online_range_v1",
        "created_at": now_iso(),
        "candidate_id": nomination_result.get("candidate_id", ""),
        "identity_target": deepcopy(nomination_result.get("identity_target", {})),
        "source": {
            "url": url,
            "title": match.get("metadata", {}).get("title", ""),
            "publisher": match.get("metadata", {}).get("publisher", ""),
            "publisher_authority": "third_party_upload_metadata_not_rightsholder_authority",
            "local_media_path": media_path.relative_to(PROJECT_ROOT).as_posix(),
            "local_media_sha256": file_sha256(media_path),
            "local_media_bytes": media_path.stat().st_size,
            "media_was_downloaded_before_this_review_builder": True,
            "review_builder_downloaded_media": False,
        },
        "range": {
            "start_seconds": round(start, 3),
            "end_seconds": round(end, 3),
            "duration_seconds": round(end - start, 3),
        },
        "owner_attestation": {
            "path": attestation_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": file_sha256(attestation_path),
            "checks": attestation_checks,
            "passed": human_gate_passed,
        },
        "automatic_audio_diagnostics": quality,
        "automatic_contamination_review": {
            "path": contamination_path.relative_to(PROJECT_ROOT).as_posix() if contamination_path else "",
            "sha256": file_sha256(contamination_path) if contamination_path else "",
            "checks": contamination_checks,
            "passed_for_direct_reference_input": contamination_gate_passed,
            "contamination_detected": contamination_detected,
            "findings": list(contamination.get("findings") or []),
            "rule": "A no-music human attestation cannot override exact-bound machine contamination evidence.",
        },
        "range_bindings": {
            "wav_duration_matches_exact_range": duration_binding_passed,
            "metadata_has_no_music_risk_term": metadata_music_clear,
            "active_speaker_automation": "not_available; exact target-only identity comes from Robert's audiovisual review",
            "face_identity_automation": "not_available; screenshots/contact sheet are context, not biometric proof",
        },
        "status": (
            "owner_attested_target_only_range_clean_reference_input_ready"
            if direct_reference_input_ready
            else "owner_attested_target_only_candidate_cleanup_and_qc_required"
            if candidate_evidence_ready and contamination_detected
            else "owner_attested_target_only_candidate_machine_contamination_check_required"
            if candidate_evidence_ready
            else "blocked_owner_attestation_or_audio_quality_gate_failed"
        ),
        "candidate_reference_evidence_ready": candidate_evidence_ready,
        "eligible_for_cleanup_and_qc_workbench": candidate_evidence_ready and not direct_reference_input_ready,
        "eligible_for_private_reference_pack_input": direct_reference_input_ready,
        "eligible_for_direct_model_input": False,
        "manual_clip_by_clip_box_required_for_this_exact_range": False if candidate_evidence_ready else True,
        "model_or_runtime_authority": {
            "voice_training_or_cloning_allowed": False,
            "voice_assignment_allowed": False,
            "voice_synthesis_allowed": False,
            "candidate_activation_allowed": False,
            "official_voice_claim_allowed": False,
        },
        "limits": [
            "This is one private source-review range, not consent for public distribution or an official-voice claim.",
            "The 1999 performance is earlier same-performer Kathryn evidence, not the selected 2016 adult-present continuity itself.",
            "No biometric voice or face identification was performed.",
        ],
    }


def _evidence_for_range(
    evidence_records: Iterable[dict[str, Any]], *, url: str, start: float, end: float
) -> dict[str, Any] | None:
    for evidence in evidence_records:
        if not isinstance(evidence, dict):
            continue
        try:
            evidence_url = canonical_url(str(evidence.get("source_url") or ""))
        except ValueError:
            continue
        if evidence_url != url:
            continue
        range_info = evidence.get("range") if isinstance(evidence.get("range"), dict) else {}
        try:
            evidence_start = float(range_info.get("start_seconds"))
            evidence_end = float(range_info.get("end_seconds"))
        except (TypeError, ValueError):
            continue
        if abs(evidence_start - start) <= 0.01 and abs(evidence_end - end) <= 0.01:
            return deepcopy(evidence)
    return None


def evaluate_machine_evidence(evidence: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate exact-bound machine evidence using conservative thresholds."""

    if not evidence:
        return {
            "passed": False,
            "status": "not_run_no_authorized_local_media_evidence",
            "failed_gates": [
                "exact media hash and analyzer provenance",
                "owner-approved target face reference",
                "target face is the active speaker",
                "single-speaker and overlap rejection",
                "music/noise/clipping quality",
            ],
        }

    provenance = evidence.get("provenance") if isinstance(evidence.get("provenance"), dict) else {}
    face = evidence.get("face_identity") if isinstance(evidence.get("face_identity"), dict) else {}
    active = evidence.get("active_speaker") if isinstance(evidence.get("active_speaker"), dict) else {}
    separation = evidence.get("speaker_separation") if isinstance(evidence.get("speaker_separation"), dict) else {}
    quality = evidence.get("audio_quality") if isinstance(evidence.get("audio_quality"), dict) else {}

    checks = {
        "exact media hash and analyzer provenance": bool(
            re.fullmatch(r"[0-9a-f]{64}", str(provenance.get("media_sha256") or "").lower())
            and str(provenance.get("analyzer") or "").strip()
            and str(provenance.get("analyzer_version") or "").strip()
        ),
        "owner-approved target face reference": bool(
            face.get("status") == "matched_owner_approved_target_reference"
            and float(face.get("confidence", 0) or 0) >= 0.95
            and float(face.get("visible_ratio", 0) or 0) >= 0.80
            and str(face.get("reference_bundle_id") or "").strip()
            and str(face.get("reference_bundle_sha256") or "").strip()
        ),
        "target face is the active speaker": bool(
            active.get("status") == "target_face_is_active_speaker"
            and float(active.get("confidence", 0) or 0) >= 0.90
            and float(active.get("coverage_ratio", 0) or 0) >= 0.80
        ),
        "single-speaker and overlap rejection": bool(
            int(separation.get("max_simultaneous_speakers", 99) or 99) == 1
            and float(separation.get("overlap_ratio", 1) or 1) <= 0.02
            and float(separation.get("confidence", 0) or 0) >= 0.90
        ),
        "music/noise/clipping quality": bool(
            float(quality.get("speech_ratio", 0) or 0) >= 0.75
            and float(quality.get("music_probability", 1) or 1) <= 0.05
            and float(quality.get("noise_probability", 1) or 1) <= 0.15
            and float(quality.get("snr_db", -999) or -999) >= 18.0
            and float(quality.get("clipping_ratio", 1) or 1) <= 0.005
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "passed": not failed,
        "status": "machine_target_only_candidate_gate_passed_not_human_approved" if not failed else "machine_evidence_failed_closed",
        "checks": checks,
        "failed_gates": failed,
        "important_limit": "Even a machine pass creates review evidence only; it never trains, clones, assigns, synthesizes, or activates a voice.",
    }


def _range_for_source(source: dict[str, Any], metadata: dict[str, Any]) -> tuple[float, float | None, list[str]]:
    start = _finite_number(source.get("nominated_start_seconds", 0), field="nominated_start_seconds", minimum=0)
    requested_end = source.get("nominated_end_seconds")
    duration = metadata.get("duration_seconds")
    notes: list[str] = []
    if requested_end is not None:
        end = _finite_number(requested_end, field="nominated_end_seconds", minimum=0)
    elif duration is not None:
        end = _finite_number(duration, field="duration_seconds", minimum=0)
        notes.append("end inferred from provider duration metadata")
    else:
        end = None
        notes.append("provider duration unavailable; exact end remains unresolved")
    if end is not None and end <= start:
        notes.append("nominated start is at or after provider duration")
        return start, None, notes
    if end is not None and end - start > MAX_RANGE_SECONDS:
        end = start + MAX_RANGE_SECONDS
        notes.append("analysis window truncated to the 45-second nomination limit")
    return start, end, notes


def _build_ranked_source(
    *,
    source: dict[str, Any],
    metadata: dict[str, Any],
    target: dict[str, Any],
    machine_evidence: Iterable[dict[str, Any]],
    ordinal: int,
) -> dict[str, Any]:
    url = canonical_url(str(source.get("url") or metadata.get("url") or ""))
    start, end, range_notes = _range_for_source(source, metadata)
    text = _metadata_text(metadata)
    target_match = _word_match(text, str(target.get("target_name") or ""))
    performer_match = bool(target.get("performer")) and _word_match(text, str(target.get("performer") or ""))
    music_hits = sorted(term for term in MUSIC_TERMS if term in text)
    mixed_hits = sorted(term for term in MIXED_SOURCE_TERMS if term in text)
    explicit_owner = bool(source.get("owner_nominated_target_only"))
    explicit_seed = source.get("origin") == "explicit_seed_url"
    exact_evidence = _evidence_for_range(machine_evidence, url=url, start=start, end=end) if end is not None else None
    machine_gate = evaluate_machine_evidence(exact_evidence)

    score = 0
    reasons: list[str] = []
    if explicit_owner:
        score += 80
        reasons.append("owner nominated the exact source and start time")
    if explicit_seed:
        # A URL deliberately supplied to this bounded run must outrank an
        # unverified metadata-search lead.  Search hits can otherwise collect
        # target-name and duration bonuses even when the video is unavailable
        # or contains the wrong speaker.  Exact-bound machine evidence still
        # has the larger bonus and remains a separate fail-closed gate.
        score += 100
        reasons.append("explicit source seed is ranked ahead of unreviewed search noise")
    if target_match:
        score += 30
        reasons.append("metadata contains the exact target name")
    if performer_match:
        score += 20
        reasons.append("metadata contains the selected performer name")
    if "monologue" in text:
        score += 20
        reasons.append("metadata labels a monologue")
    if end is not None and 6 <= end - start <= MAX_RANGE_SECONDS:
        score += 15
        reasons.append("bounded range length is suitable for later analysis")
    if music_hits:
        score -= 100
        reasons.append("metadata signals music/song risk")
    if mixed_hits:
        score -= 25
        reasons.append("metadata signals mixed-source risk")
    publisher = str(metadata.get("publisher") or "")
    if not publisher or not any(term in publisher.casefold() for term in ("official", "disney", "sony", "nbc")):
        score -= 10
        reasons.append("publisher authority is third-party or unverified")
    if machine_gate["passed"]:
        score += 150
        reasons.append("exact-bound machine target-only candidate gate passed")

    duration = None if end is None else round(end - start, 3)
    return {
        "source_id": f"online_nomination_{ordinal:03d}",
        "exact_url": url,
        "metadata": {
            "title": str(metadata.get("title") or ""),
            "publisher": publisher,
            "publisher_url": str(metadata.get("publisher_url") or ""),
            "published_at": str(metadata.get("published_at") or ""),
            "duration_seconds": metadata.get("duration_seconds"),
            "provider": str(metadata.get("discovery_provider") or "seeded_url_without_provider_refresh"),
            "metadata_only": True,
        },
        "identity_target": deepcopy(target),
        "candidate_range": {
            "start_seconds": round(start, 3),
            "end_seconds": None if end is None else round(end, 3),
            "duration_seconds": duration,
            "basis": "owner_exact_source_range_nomination" if explicit_owner else "metadata_analysis_window_only",
            "owner_note": str(source.get("owner_note") or ""),
            "notes": range_notes,
        },
        "metadata_checks": {
            "target_name_in_metadata": target_match,
            "performer_name_in_metadata": performer_match,
            "music_terms": music_hits,
            "mixed_source_terms": mixed_hits,
            "metadata_does_not_identify_the_speaker": True,
        },
        "machine_evidence_gate": machine_gate,
        "ranking": {"score": score, "reasons": reasons},
        "status": (
            "machine_target_only_candidate_not_human_approved"
            if machine_gate["passed"]
            else "ranked_candidate_range_pending_authorized_machine_analysis"
        ),
        "target_only_approved": False,
        "voice_reference_ready": False,
        "voice_training_or_cloning_allowed": False,
        "voice_assignment_allowed": False,
        "candidate_activation_allowed": False,
    }


def run_online_voice_nomination(
    request: dict[str, Any],
    *,
    metadata_search: bool = False,
    direct_metadata: Callable[[str], dict[str, Any]] = fetch_video_metadata,
    video_search: Callable[[str, int], list[dict[str, Any]]] = search_video_metadata,
    machine_evidence: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Rank exact online sources and bounded candidate ranges, fail closed."""

    validate_nomination_request(request)
    if not request.get("sources") and not metadata_search:
        raise ValueError("metadata_search is required when no exact seed URL is supplied.")
    target = deepcopy(request["identity_target"])
    raw_sources = [deepcopy(item) for item in request["sources"]]
    provider_errors: list[dict[str, str]] = []

    metadata_by_url: dict[str, dict[str, Any]] = {}
    if metadata_search:
        for source in raw_sources:
            url = canonical_url(str(source.get("url") or ""))
            try:
                metadata_by_url[url] = direct_metadata(url)
            except Exception as exc:
                provider_errors.append({"provider": "direct_video_metadata", "url": url, "error": str(exc)[:500]})
        for query in request.get("search_queries", []):
            try:
                for item in video_search(str(query), MAX_SEARCH_RESULTS_PER_QUERY):
                    url = canonical_url(str(item.get("url") or ""))
                    if not url or url in metadata_by_url:
                        continue
                    metadata_by_url[url] = deepcopy(item)
                    raw_sources.append(
                        {
                            "url": url,
                            "origin": "automatic_search_metadata_lead",
                            "nominated_start_seconds": 0.0,
                            "nominated_end_seconds": None,
                            "owner_nominated_target_only": False,
                            "owner_note": "automatically discovered metadata lead",
                        }
                    )
            except Exception as exc:
                provider_errors.append({"provider": "video_metadata_search", "query": str(query), "error": str(exc)[:500]})

    unique_sources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in raw_sources:
        url = canonical_url(str(source.get("url") or ""))
        if url in seen:
            continue
        seen.add(url)
        source["url"] = url
        unique_sources.append(source)

    ranked = [
        _build_ranked_source(
            source=source,
            metadata=metadata_by_url.get(source["url"], {"url": source["url"]}),
            target=target,
            machine_evidence=machine_evidence,
            ordinal=index,
        )
        for index, source in enumerate(unique_sources, 1)
    ]
    ranked.sort(key=lambda item: (-int(item["ranking"]["score"]), item["exact_url"]))
    for index, item in enumerate(ranked, 1):
        item["ranking"]["rank"] = index

    return {
        "schema_version": SCHEMA_VERSION,
        "result_id": f"{request['candidate_id']}_automatic_voice_source_nominations_v1",
        "created_at": now_iso(),
        "candidate_id": request["candidate_id"],
        "request_id": request["request_id"],
        "request_sha256": json_sha256(request),
        "identity_target": target,
        "status": "ranked_nominations_ready_no_source_approved",
        "ranked_target_only_candidate_ranges": ranked,
        "capabilities": _capability_status(),
        "provider_errors": provider_errors,
        "selection": {
            "highest_ranked_source_id": ranked[0]["source_id"] if ranked else "",
            "source_approved": False,
            "target_only_range_approved": False,
            "voice_reference_ready": False,
            "voice_trained_or_cloned": False,
            "voice_assigned": False,
            "voice_synthesized": False,
            "candidate_activated": False,
        },
        "next_automatic_stage": {
            "status": "blocked_until_bounded_online_media_analysis_has_explicit_project_authority",
            "required": [
                "download only the nominated bounded source under an explicit private-local evidence authorization",
                "bind exact source bytes by SHA-256",
                "match the visible face to an owner-approved target reference",
                "bind the target face to the active speaker",
                "reject overlap, music, noise, clipping, and materially reverberant audio",
                "emit review evidence without training, cloning, assigning, synthesizing, or activating",
            ],
            "manual_clip_by_clip_box_required_now": False,
        },
        "operation_evidence": {
            "metadata_only": True,
            "media_downloaded": False,
            "audio_extracted": False,
            "voice_trained_or_cloned": False,
            "voice_assigned": False,
            "voice_synthesized": False,
            "candidate_activated": False,
        },
    }


def candidate_artifact_paths(candidate_id: str) -> tuple[Path, Path]:
    candidate_dir = resolve_candidate_dir(candidate_id)
    return candidate_dir / REQUEST_FILENAME, candidate_dir / RESULT_FILENAME


def candidate_owner_review_path(candidate_id: str) -> Path:
    return resolve_candidate_dir(candidate_id) / OWNER_REVIEW_FILENAME
