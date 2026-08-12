"""Bounded private-local media intake for TemporaryAI voice and movement evidence.

Metadata discovery intentionally does not download media.  This separate lane may
read a user-authorized file already under ``Data/library`` and extract only
explicit, short scene ranges.  Extracted segments remain review candidates until
human identity, speaker cleanliness, and movement tracking checks pass.

This module never trains/clones a voice, assigns a voice, activates a TemporaryAI,
or grants public-release/official-voice status.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from Core.voice_reference_pipeline import resolve_ffmpeg


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = PROJECT_ROOT / "TemporaryAI" / "candidates"
LIBRARY_ROOT = PROJECT_ROOT / "Data" / "library"
INTAKE_RELATIVE = Path("workbench") / "inputs" / "private_local_media_intake"

SCHEMA_VERSION = 1
MIN_SEGMENT_SECONDS = 1.0
MAX_SEGMENT_SECONDS = 45.0
MAX_TOTAL_SECONDS = 180.0
MAX_SEGMENTS = 12
ALLOWED_EVIDENCE = {"voice", "movement"}
QUEUE_HARD_CAP = 3


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str, limit: int = 100) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
    return cleaned[:limit] or "unknown"


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


def project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _confined_existing_file(path: Path, root: Path, label: str) -> Path:
    resolved_root = root.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"{label} must remain under {resolved_root}.") from exc
    if not resolved.is_file():
        raise FileNotFoundError(f"{label} does not exist: {resolved}")
    return resolved


def resolve_library_source(source: str | Path, library_root: Path | None = None) -> Path:
    root = (library_root or LIBRARY_ROOT).resolve()
    raw = Path(source)
    if not raw.is_absolute():
        project_candidate = (PROJECT_ROOT / raw).resolve()
        library_candidate = (root / raw).resolve()
        raw = project_candidate if project_candidate.exists() else library_candidate
    return _confined_existing_file(raw, root, "Private local media source")


def resolve_candidate_dir(candidate_id: str, candidate_root: Path | None = None) -> Path:
    if not candidate_id or slug(candidate_id) != candidate_id:
        raise ValueError("candidate_id must be a normalized lowercase identifier.")
    root = (candidate_root or CANDIDATE_ROOT).resolve()
    candidate = (root / candidate_id).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("candidate_id escapes the TemporaryAI candidate root.") from exc
    if not candidate.is_dir():
        raise FileNotFoundError(f"TemporaryAI candidate does not exist: {candidate_id}")
    return candidate


def parse_timecode(value: str | int | float) -> float:
    if isinstance(value, (int, float)):
        seconds = float(value)
    else:
        text = str(value).strip()
        if not text:
            raise ValueError("Timecode cannot be empty.")
        parts = text.split(":")
        if len(parts) > 3:
            raise ValueError(f"Invalid timecode: {value}")
        try:
            numbers = [float(part) for part in parts]
        except ValueError as exc:
            raise ValueError(f"Invalid timecode: {value}") from exc
        seconds = 0.0
        for number in numbers:
            seconds = seconds * 60.0 + number
    if seconds < 0:
        raise ValueError("Timecodes cannot be negative.")
    return round(seconds, 3)


def parse_range_expression(expression: str, evidence_types: Iterable[str]) -> dict[str, Any]:
    if "-" not in expression:
        raise ValueError("Scene range must be START-END, for example 00:12:03-00:12:24.")
    start_text, end_text = expression.split("-", 1)
    return {
        "start_seconds": parse_timecode(start_text),
        "end_seconds": parse_timecode(end_text),
        "evidence_types": sorted(set(evidence_types)),
    }


def normalize_scene_ranges(
    ranges: Iterable[dict[str, Any]],
    default_evidence_types: Iterable[str],
) -> list[dict[str, Any]]:
    default_types = sorted({str(item).strip().lower() for item in default_evidence_types if str(item).strip()})
    unknown_default = set(default_types) - ALLOWED_EVIDENCE
    if unknown_default:
        raise ValueError(f"Unsupported evidence types: {', '.join(sorted(unknown_default))}")
    normalized: list[dict[str, Any]] = []
    for number, item in enumerate(ranges, 1):
        if not isinstance(item, dict):
            raise ValueError("Every scene range must be an object.")
        start = parse_timecode(item.get("start_seconds", item.get("start", "")))
        end = parse_timecode(item.get("end_seconds", item.get("end", "")))
        duration = round(end - start, 3)
        if duration < MIN_SEGMENT_SECONDS:
            raise ValueError(f"Scene range {number} is shorter than {MIN_SEGMENT_SECONDS:g} second.")
        if duration > MAX_SEGMENT_SECONDS:
            raise ValueError(
                f"Scene range {number} exceeds the {MAX_SEGMENT_SECONDS:g}-second per-range limit. "
                "Split it into reviewed target scenes."
            )
        evidence = sorted(
            {
                str(value).strip().lower()
                for value in item.get("evidence_types", default_types)
                if str(value).strip()
            }
        )
        if not evidence or set(evidence) - ALLOWED_EVIDENCE:
            raise ValueError("Every range needs voice and/or movement evidence intent.")
        normalized.append(
            {
                "segment_id": str(item.get("segment_id") or f"segment_{number:03d}"),
                "start_seconds": start,
                "end_seconds": end,
                "duration_seconds": duration,
                "evidence_types": evidence,
                "scene_note": str(item.get("scene_note") or ""),
                "expected_other_speakers_or_people": [
                    str(value) for value in item.get("expected_other_speakers_or_people", [])
                ],
            }
        )
    if len(normalized) > MAX_SEGMENTS:
        raise ValueError(f"A request may contain at most {MAX_SEGMENTS} bounded scene ranges.")
    total = round(sum(float(item["duration_seconds"]) for item in normalized), 3)
    if total > MAX_TOTAL_SECONDS:
        raise ValueError(f"Total requested media exceeds the {MAX_TOTAL_SECONDS:g}-second request limit.")
    segment_ids = [str(item["segment_id"]) for item in normalized]
    if len(segment_ids) != len(set(segment_ids)) or any(slug(value) != value for value in segment_ids):
        raise ValueError("segment_id values must be unique normalized lowercase identifiers.")
    return normalized


def _request_payload(request: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(request)
    payload.pop("integrity", None)
    return payload


def request_payload_sha256(request: dict[str, Any]) -> str:
    return json_sha256(_request_payload(request))


def build_intake_request(
    *,
    candidate_id: str,
    source_path: str | Path,
    character_label: str,
    variant_label: str,
    speaker_label: str,
    performer_label: str,
    evidence_types: Iterable[str] = ("voice", "movement"),
    scene_ranges: Iterable[dict[str, Any]] = (),
    private_local_use_authorized: bool = False,
    authorized_by: str = "",
    authorization_note: str = "",
    request_label: str = "",
    candidate_root: Path | None = None,
    library_root: Path | None = None,
) -> dict[str, Any]:
    candidate_dir = resolve_candidate_dir(candidate_id, candidate_root)
    source = resolve_library_source(source_path, library_root)
    evidence = sorted({str(item).strip().lower() for item in evidence_types if str(item).strip()})
    ranges = normalize_scene_ranges(scene_ranges, evidence)
    if not all(str(value).strip() for value in (character_label, variant_label, speaker_label, performer_label)):
        raise ValueError("Character, variant, speaker, and performer labels are all required for local intake.")
    if private_local_use_authorized and not str(authorized_by).strip():
        raise ValueError("authorized_by is required when private local intake is authorized.")
    source_stat = source.stat()
    request_id = slug(
        request_label
        or f"{candidate_id}_{source.stem}_private_local_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    status = "queued_for_bounded_candidate_extraction" if private_local_use_authorized and ranges else (
        "draft_needs_bounded_scene_ranges" if not ranges else "draft_needs_private_local_authorization"
    )
    request: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "created_at": now_iso(),
        "candidate_id": candidate_id,
        "status": status,
        "identity_target": {
            "character": {"character_id": slug(character_label), "label": str(character_label).strip()},
            "variant": {"variant_id": slug(variant_label), "label": str(variant_label).strip()},
            "speaker": {"speaker_id": slug(speaker_label), "label": str(speaker_label).strip()},
            "performer": {"performer_id": slug(performer_label), "label": str(performer_label).strip()},
            "identity_rule": "character, variant, speaker, and performer stay separate even when one performer has multiple roles",
        },
        "source": {
            "kind": "private_local_library_media",
            "path": project_relative(source),
            "sha256": file_sha256(source),
            "size_bytes": source_stat.st_size,
            "mtime_ns": source_stat.st_mtime_ns,
            "suffix": source.suffix.lower(),
            "whole_source_may_not_be_auto_extracted": True,
        },
        "authorization": {
            "private_local_reference_use_authorized": bool(private_local_use_authorized),
            "authorized_by": str(authorized_by).strip(),
            "authorized_at": now_iso() if private_local_use_authorized else "",
            "authorization_note": str(authorization_note).strip(),
            "scope": "bounded private-local voice and movement reference preparation",
            "public_release_authorized": False,
            "official_voice_or_performer_claim_authorized": False,
        },
        "requested_evidence_types": evidence,
        "scene_ranges": ranges,
        "limits": {
            "maximum_segments": MAX_SEGMENTS,
            "maximum_seconds_per_segment": MAX_SEGMENT_SECONDS,
            "maximum_total_seconds": MAX_TOTAL_SECONDS,
            "requested_total_seconds": round(sum(float(item["duration_seconds"]) for item in ranges), 3),
        },
        "review_contract": {
            "candidate_extraction_is_not_evidence_approval": True,
            "human_audio_visual_identity_review_required": True,
            "production_credit_or_cast_evidence_required": True,
            "diarization_or_acoustic_grouping_is_an_aid_not_identity_proof": True,
            "voice_reject_if_overlap_music_narration_or_material_effects": True,
            "movement_requires_confirmed_visible_target_track": True,
        },
        "action_boundaries": {
            "metadata_discovery_remains_no_download": True,
            "bounded_candidate_clip_extraction_allowed": bool(private_local_use_authorized and ranges),
            "whole_movie_or_episode_extraction_allowed": False,
            "voice_clone_or_training_run_allowed_by_this_request": False,
            "voice_assignment_allowed_by_this_request": False,
            "temporary_ai_activation_allowed_by_this_request": False,
            "public_release_allowed_by_this_request": False,
        },
        "paths": {
            "candidate_dir": project_relative(candidate_dir),
            "intake_root": project_relative(candidate_dir / INTAKE_RELATIVE),
        },
    }
    request["integrity"] = {"request_payload_sha256": request_payload_sha256(request)}
    validate_intake_request(
        request,
        expected_candidate_id=candidate_id,
        candidate_root=candidate_root,
        library_root=library_root,
        verify_source_hash=False,
    )
    return request


def validate_intake_request(
    request: dict[str, Any],
    *,
    expected_candidate_id: str = "",
    candidate_root: Path | None = None,
    library_root: Path | None = None,
    verify_source_hash: bool = True,
) -> Path:
    if int(request.get("schema_version", 0) or 0) != SCHEMA_VERSION:
        raise ValueError(f"local media intake schema_version must be {SCHEMA_VERSION}.")
    candidate_id = str(request.get("candidate_id") or "")
    if expected_candidate_id and candidate_id != expected_candidate_id:
        raise ValueError("Request candidate_id does not match its candidate folder.")
    resolve_candidate_dir(candidate_id, candidate_root)
    request_id = str(request.get("request_id") or "")
    if not request_id or slug(request_id) != request_id:
        raise ValueError("request_id must be a normalized lowercase identifier.")
    identity = request.get("identity_target") if isinstance(request.get("identity_target"), dict) else {}
    for lane in ("character", "variant", "speaker", "performer"):
        record = identity.get(lane) if isinstance(identity.get(lane), dict) else {}
        if not str(record.get("label") or "").strip() or not str(record.get(f"{lane}_id") or "").strip():
            raise ValueError(f"identity_target.{lane} must include an id and label.")
    source_record = request.get("source") if isinstance(request.get("source"), dict) else {}
    source = resolve_library_source(str(source_record.get("path") or ""), library_root)
    if source.stat().st_size != int(source_record.get("size_bytes", -1)):
        raise ValueError("Local media source size changed after the request was created.")
    source_hash = str(source_record.get("sha256") or "")
    if not re.fullmatch(r"[a-f0-9]{64}", source_hash):
        raise ValueError("Local media request needs an exact lowercase SHA-256 source binding.")
    if verify_source_hash and file_sha256(source) != source_hash:
        raise ValueError("Local media source SHA-256 changed after the request was created.")
    ranges = normalize_scene_ranges(request.get("scene_ranges", []), request.get("requested_evidence_types", []))
    if ranges != request.get("scene_ranges", []):
        raise ValueError("Scene ranges are not in canonical bounded form.")
    authorization = request.get("authorization") if isinstance(request.get("authorization"), dict) else {}
    boundaries = request.get("action_boundaries") if isinstance(request.get("action_boundaries"), dict) else {}
    can_extract = bool(authorization.get("private_local_reference_use_authorized") and ranges)
    if boundaries.get("bounded_candidate_clip_extraction_allowed") is not can_extract:
        raise ValueError("Bounded extraction gate does not match authorization and range state.")
    for key in (
        "whole_movie_or_episode_extraction_allowed",
        "voice_clone_or_training_run_allowed_by_this_request",
        "voice_assignment_allowed_by_this_request",
        "temporary_ai_activation_allowed_by_this_request",
        "public_release_allowed_by_this_request",
    ):
        if boundaries.get(key) not in {False, None}:
            raise ValueError(f"Local intake cannot enable {key}.")
    if authorization.get("public_release_authorized") not in {False, None}:
        raise ValueError("Private-local intake cannot grant public release.")
    integrity = request.get("integrity") if isinstance(request.get("integrity"), dict) else {}
    if integrity.get("request_payload_sha256") != request_payload_sha256(request):
        raise ValueError("Local media request payload hash is invalid.")
    return source


def request_output_path(
    request: dict[str, Any],
    *,
    candidate_root: Path | None = None,
) -> Path:
    candidate_dir = resolve_candidate_dir(str(request.get("candidate_id") or ""), candidate_root)
    return candidate_dir / INTAKE_RELATIVE / "requests" / f"{request['request_id']}.json"


def save_intake_request(
    request: dict[str, Any],
    *,
    candidate_root: Path | None = None,
    library_root: Path | None = None,
) -> Path:
    validate_intake_request(
        request,
        candidate_root=candidate_root,
        library_root=library_root,
        verify_source_hash=False,
    )
    destination = request_output_path(request, candidate_root=candidate_root)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Local media intake request already exists: {destination}")
    write_json(destination, request)
    return destination


def _run_ffmpeg(command: list[str], output: Path) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    if completed.returncode != 0 or not output.is_file():
        raise RuntimeError(f"Bounded FFmpeg extraction failed: {completed.stderr.strip()[-1200:]}")


def extract_bounded_segment(
    source: Path,
    segment: dict[str, Any],
    output_dir: Path,
) -> dict[str, Path]:
    """Extract one already-bounded review segment; never accepts an open-ended range."""
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is unavailable. Run tools/check_voice_pipeline.py.")
    start = float(segment["start_seconds"])
    duration = float(segment["duration_seconds"])
    if duration < MIN_SEGMENT_SECONDS or duration > MAX_SEGMENT_SECONDS:
        raise ValueError("Extractor received an out-of-bounds segment.")
    segment_dir = output_dir / str(segment["segment_id"])
    segment_dir.mkdir(parents=True, exist_ok=False)
    artifacts: dict[str, Path] = {}
    if "voice" in segment["evidence_types"]:
        voice_path = segment_dir / "candidate_voice_mono_24khz.wav"
        _run_ffmpeg(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{start:.3f}",
                "-i",
                str(source),
                "-t",
                f"{duration:.3f}",
                "-vn",
                "-ac",
                "1",
                "-ar",
                "24000",
                "-c:a",
                "pcm_s16le",
                str(voice_path),
            ],
            voice_path,
        )
        artifacts["voice_wav"] = voice_path
    if "movement" in segment["evidence_types"]:
        review_path = segment_dir / "candidate_movement_review.mp4"
        _run_ffmpeg(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{start:.3f}",
                "-i",
                str(source),
                "-t",
                f"{duration:.3f}",
                "-vf",
                "scale=-2:720:force_original_aspect_ratio=decrease",
                "-r",
                "24",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "28",
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-movflags",
                "+faststart",
                str(review_path),
            ],
            review_path,
        )
        artifacts["movement_review_mp4"] = review_path
    return artifacts


def build_review_template(pack_manifest: dict[str, Any]) -> dict[str, Any]:
    reviews: list[dict[str, Any]] = []
    for segment in pack_manifest.get("segments", []):
        reviews.append(
            {
                "segment_id": segment["segment_id"],
                "human_identity_review": {
                    "reviewed": False,
                    "reviewer": "",
                    "reviewed_at": "",
                    "target_character_confirmed": False,
                    "target_variant_confirmed": False,
                    "target_speaker_confirmed": False,
                    "target_performer_confirmed": False,
                    "identity_basis": [],
                    "notes": "",
                },
                "diarization_aid": {
                    "status": "not_run",
                    "used_as_aid_only_not_identity_proof": True,
                    "reviewed_group_label": "",
                },
                "voice_review": {
                    "decision": "pending" if "voice" in segment["evidence_types"] else "not_requested",
                    "target_only_speech": None,
                    "overlapping_speech": None,
                    "music_present": None,
                    "narration_present": None,
                    "material_sound_effects_present": None,
                    "stable_character_delivery": None,
                    "notes": "",
                },
                "movement_review": {
                    "decision": "pending" if "movement" in segment["evidence_types"] else "not_requested",
                    "target_visible": None,
                    "target_track_confirmed": None,
                    "material_occlusion": None,
                    "shot_cuts_confuse_motion": None,
                    "movement_is_performer_evidence_not_character_memory": True,
                    "notes": "",
                },
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "pack_id": pack_manifest["pack_id"],
        "request_payload_sha256": pack_manifest["request_payload_sha256"],
        "source_sha256": pack_manifest["source"]["sha256"],
        "status": "pending_human_review",
        "segments": reviews,
    }


SegmentExtractor = Callable[[Path, dict[str, Any], Path], dict[str, Path]]


def extract_candidate_pack(
    request: dict[str, Any],
    *,
    candidate_root: Path | None = None,
    library_root: Path | None = None,
    extractor: SegmentExtractor = extract_bounded_segment,
) -> dict[str, Any]:
    source = validate_intake_request(
        request,
        expected_candidate_id=str(request.get("candidate_id") or ""),
        candidate_root=candidate_root,
        library_root=library_root,
        verify_source_hash=True,
    )
    if request.get("status") != "queued_for_bounded_candidate_extraction":
        raise ValueError("Only an explicitly authorized, ranged, queued request can extract candidate clips.")
    ranges = list(request.get("scene_ranges", []))
    if not ranges:
        raise ValueError("Whole-source or open-ended extraction is forbidden; add bounded scene ranges first.")
    candidate_dir = resolve_candidate_dir(str(request["candidate_id"]), candidate_root)
    pack_dir = candidate_dir / INTAKE_RELATIVE / "packs" / str(request["request_id"])
    if pack_dir.exists() or pack_dir.is_symlink():
        raise FileExistsError(f"Candidate intake pack already exists: {pack_dir}")
    segments_dir = pack_dir / "candidate_segments"
    segments_dir.mkdir(parents=True, exist_ok=False)
    segment_records: list[dict[str, Any]] = []
    try:
        for segment in ranges:
            artifacts = extractor(source, segment, segments_dir)
            artifact_records: dict[str, Any] = {}
            for label, artifact in artifacts.items():
                path = artifact.resolve()
                try:
                    path.relative_to(pack_dir.resolve())
                except ValueError as exc:
                    raise ValueError("Extractor returned an artifact outside the request pack.") from exc
                if not path.is_file():
                    raise FileNotFoundError(f"Expected extracted artifact is missing: {path}")
                artifact_records[label] = {
                    "path": project_relative(path),
                    "sha256": file_sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            segment_records.append({**segment, "artifacts": artifact_records, "evidence_status": "unreviewed_candidate"})
    except Exception:
        shutil.rmtree(pack_dir, ignore_errors=True)
        raise
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "pack_id": str(request["request_id"]),
        "created_at": now_iso(),
        "candidate_id": str(request["candidate_id"]),
        "status": "candidate_segments_extracted_pending_human_review",
        "request_payload_sha256": request_payload_sha256(request),
        "identity_target": deepcopy(request["identity_target"]),
        "source": deepcopy(request["source"]),
        "authorization_scope": deepcopy(request["authorization"]),
        "segments": segment_records,
        "review_gate": deepcopy(request["review_contract"]),
        "outputs": {
            "voice_model_or_clone_created": False,
            "voice_assigned": False,
            "movement_profile_assigned": False,
            "temporary_ai_activated": False,
            "public_release_authorized": False,
        },
    }
    write_json(pack_dir / "candidate_pack_manifest.json", manifest)
    write_json(pack_dir / "human_review.json", build_review_template(manifest))
    return manifest


def _identity_review_passes(review: dict[str, Any]) -> tuple[bool, list[str]]:
    identity = review.get("human_identity_review") if isinstance(review.get("human_identity_review"), dict) else {}
    blockers: list[str] = []
    if (
        identity.get("reviewed") is not True
        or not str(identity.get("reviewer") or "").strip()
        or not str(identity.get("reviewed_at") or "").strip()
    ):
        blockers.append("human identity review, reviewer, and review time are required")
    for key in (
        "target_character_confirmed",
        "target_variant_confirmed",
        "target_speaker_confirmed",
        "target_performer_confirmed",
    ):
        if identity.get(key) is not True:
            blockers.append(key.replace("_", " ") + " is required")
    basis = {str(item) for item in identity.get("identity_basis", [])}
    if "human_audio_visual_scene_review" not in basis:
        blockers.append("human audiovisual scene review is required")
    if "production_credit_or_cast_record" not in basis:
        blockers.append("production credit or cast evidence is required")
    diarization = review.get("diarization_aid") if isinstance(review.get("diarization_aid"), dict) else {}
    if diarization.get("used_as_aid_only_not_identity_proof") is not True:
        blockers.append("diarization must remain an aid rather than identity proof")
    if diarization.get("status") not in {"reviewed_group_consistent", "not_needed_single_speaker_confirmed"}:
        blockers.append("diarization/acoustic-group status needs human review")
    return not blockers, blockers


def promote_reviewed_evidence(
    pack_dir: Path,
    review: dict[str, Any],
    *,
    library_root: Path | None = None,
) -> dict[str, Any]:
    pack_dir = pack_dir.resolve()
    manifest = read_json(pack_dir / "candidate_pack_manifest.json", {})
    if not manifest:
        raise FileNotFoundError(f"candidate_pack_manifest.json is missing from {pack_dir}")
    if review.get("pack_id") != manifest.get("pack_id"):
        raise ValueError("Review pack_id does not match the candidate pack.")
    if review.get("request_payload_sha256") != manifest.get("request_payload_sha256"):
        raise ValueError("Review request hash does not match the candidate pack.")
    if review.get("source_sha256") != manifest.get("source", {}).get("sha256"):
        raise ValueError("Review source hash does not match the candidate pack.")
    source = resolve_library_source(str(manifest.get("source", {}).get("path") or ""), library_root)
    if file_sha256(source) != manifest.get("source", {}).get("sha256"):
        raise ValueError("Private local source changed after candidate extraction.")
    manifest_segments = {str(item["segment_id"]): item for item in manifest.get("segments", [])}
    review_segments = {str(item.get("segment_id") or ""): item for item in review.get("segments", [])}
    if (
        set(review_segments) != set(manifest_segments)
        or "" in review_segments
        or len(review.get("segments", [])) != len(manifest_segments)
    ):
        raise ValueError("Review must contain every extracted segment exactly once.")
    for segment in manifest_segments.values():
        for artifact in segment.get("artifacts", {}).values():
            artifact_path = Path(str(artifact.get("path") or ""))
            if not artifact_path.is_absolute():
                artifact_path = PROJECT_ROOT / artifact_path
            artifact_path = artifact_path.resolve()
            try:
                artifact_path.relative_to(pack_dir)
            except ValueError as exc:
                raise ValueError("Candidate artifact path escapes its intake pack.") from exc
            if not artifact_path.is_file() or file_sha256(artifact_path) != artifact.get("sha256"):
                raise ValueError("Candidate artifact is missing or changed after extraction.")
    approved_voice: list[dict[str, Any]] = []
    approved_movement: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for segment_id, segment in manifest_segments.items():
        item = review_segments[segment_id]
        identity_ok, identity_blockers = _identity_review_passes(item)
        voice_blockers = list(identity_blockers)
        movement_blockers = list(identity_blockers)
        voice = item.get("voice_review") if isinstance(item.get("voice_review"), dict) else {}
        movement = item.get("movement_review") if isinstance(item.get("movement_review"), dict) else {}
        if "voice" in segment.get("evidence_types", []):
            if segment.get("expected_other_speakers_or_people", []) and item.get("diarization_aid", {}).get("status") != "reviewed_group_consistent":
                voice_blockers.append("mixed scene requires a reviewed diarization/acoustic group")
            if voice.get("decision") != "approve_voice_reference":
                voice_blockers.append("voice decision is not approve_voice_reference")
            if voice.get("target_only_speech") is not True:
                voice_blockers.append("target-only speech is not confirmed")
            for key in ("overlapping_speech", "music_present", "narration_present", "material_sound_effects_present"):
                if voice.get(key) is not False:
                    voice_blockers.append(key.replace("_", " ") + " must be false")
            if voice.get("stable_character_delivery") is not True:
                voice_blockers.append("stable character delivery is not confirmed")
            if not voice_blockers:
                approved_voice.append(segment)
        if "movement" in segment.get("evidence_types", []):
            if movement.get("decision") != "approve_movement_reference":
                movement_blockers.append("movement decision is not approve_movement_reference")
            if movement.get("target_visible") is not True or movement.get("target_track_confirmed") is not True:
                movement_blockers.append("a visible, confirmed target track is required")
            if movement.get("material_occlusion") is not False:
                movement_blockers.append("material occlusion must be false")
            if movement.get("shot_cuts_confuse_motion") is not False:
                movement_blockers.append("shot cuts must not confuse the movement sample")
            if movement.get("movement_is_performer_evidence_not_character_memory") is not True:
                movement_blockers.append("movement must remain performance evidence, not character memory")
            if not movement_blockers:
                approved_movement.append(segment)
        decisions.append(
            {
                "segment_id": segment_id,
                "voice_approved": segment in approved_voice,
                "voice_blockers": voice_blockers if "voice" in segment.get("evidence_types", []) else [],
                "movement_approved": segment in approved_movement,
                "movement_blockers": movement_blockers if "movement" in segment.get("evidence_types", []) else [],
            }
        )
    voice_seconds = round(sum(float(item["duration_seconds"]) for item in approved_voice), 3)
    movement_seconds = round(sum(float(item["duration_seconds"]) for item in approved_movement), 3)
    result = {
        "schema_version": SCHEMA_VERSION,
        "pack_id": manifest["pack_id"],
        "created_at": now_iso(),
        "candidate_id": manifest["candidate_id"],
        "status": "review_complete",
        "request_payload_sha256": manifest["request_payload_sha256"],
        "source_sha256": manifest["source"]["sha256"],
        "identity_target": deepcopy(manifest["identity_target"]),
        "decisions": decisions,
        "approved_voice_segments": [item["segment_id"] for item in approved_voice],
        "approved_voice_seconds": voice_seconds,
        "approved_movement_segments": [item["segment_id"] for item in approved_movement],
        "approved_movement_seconds": movement_seconds,
        "readiness": {
            "voice_reference_evidence_ready": voice_seconds > 0,
            "minimum_20_reviewed_voice_seconds_for_later_model_reference": voice_seconds >= 20.0,
            "movement_reference_evidence_ready": movement_seconds > 0,
            "voice_clone_or_training_performed": False,
            "voice_assignment_performed": False,
            "movement_profile_assignment_performed": False,
            "temporary_ai_activation_performed": False,
            "public_release_or_official_voice_claim_allowed": False,
        },
    }
    write_json(pack_dir / "reviewed_evidence_manifest.json", result)
    return result


def discover_queued_requests(
    *,
    candidate_root: Path | None = None,
    max_requests: int = 1,
) -> list[Path]:
    if max_requests < 1 or max_requests > QUEUE_HARD_CAP:
        raise ValueError(f"max_requests must be between 1 and {QUEUE_HARD_CAP}.")
    root = (candidate_root or CANDIDATE_ROOT).resolve()
    queued: list[Path] = []
    if not root.exists():
        return []
    for candidate in sorted(path for path in root.iterdir() if path.is_dir()):
        request_dir = candidate / INTAKE_RELATIVE / "requests"
        for request_path in sorted(request_dir.glob("*.json")) if request_dir.exists() else []:
            request = read_json(request_path, {})
            if request.get("status") != "queued_for_bounded_candidate_extraction":
                continue
            pack_manifest = candidate / INTAKE_RELATIVE / "packs" / str(request.get("request_id") or "") / "candidate_pack_manifest.json"
            if pack_manifest.exists():
                continue
            queued.append(request_path)
            if len(queued) >= max_requests:
                return queued
    return queued


def tool_readiness() -> dict[str, Any]:
    def available(module: str) -> bool:
        try:
            return importlib.util.find_spec(module) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            return False

    return {
        "ffmpeg_bounded_audio_video_extraction": {"ready": bool(resolve_ffmpeg()), "path": resolve_ffmpeg() or ""},
        "existing_acoustic_grouping_review_aid": {
            "ready": (PROJECT_ROOT / "Core" / "voice_speaker_separation.py").is_file(),
            "note": "Acoustic folders are not biometric identity.",
        },
        "torch": available("torch"),
        "torchaudio": available("torchaudio"),
        "librosa": available("librosa"),
        "soundfile": available("soundfile"),
        "pyannote_audio": available("pyannote.audio"),
        "opencv": available("cv2"),
        "mediapipe": available("mediapipe"),
        "current_movement_lane": "bounded review video plus human target-track notes; automated pose tracking is not installed",
    }
