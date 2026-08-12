"""Read-only local voice-source audit and clean-range review queue.

This module connects TemporaryAI voice discovery to files that the project owner
has already placed under ``Data/library``.  It performs only container metadata
inspection and integrity hashing.  It does not extract audio, play media, run a
voice model, identify a biometric speaker, assign a voice, or activate anyone.

The result is deliberately a *review queue*.  Acoustic grouping can later help a
human find recurring speakers, but a group is never auto-labelled as the target
character or performer.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from Core.temp_ai_local_media_intake import LIBRARY_ROOT, PROJECT_ROOT, resolve_ffmpeg


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def resolve_library_voice_source(value: str | Path) -> Path:
    """Resolve one regular non-symlink file confined to ``Data/library``."""
    root = LIBRARY_ROOT.resolve()
    raw = Path(str(value))
    path = raw if raw.is_absolute() else PROJECT_ROOT / raw
    if path.is_symlink():
        raise ValueError("Local voice-source review rejects symlink sources.")
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("Local voice-source review is confined to Data/library.") from exc
    if not path.is_file():
        raise FileNotFoundError(f"Local voice-source file does not exist: {path}")
    return path


def _seconds_from_duration(value: str) -> float:
    hours, minutes, seconds = value.split(":")
    return round(int(hours) * 3600 + int(minutes) * 60 + float(seconds), 3)


def probe_media_container(path: Path) -> dict[str, Any]:
    """Inspect container headers with FFmpeg; no output file or playback occurs."""
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        return {
            "status": "ffmpeg_unavailable",
            "duration_seconds": None,
            "video_streams": [],
            "audio_streams": [],
        }
    completed = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    duration_match = re.search(r"Duration:\s*(\d{2}:\d{2}:\d{2}(?:\.\d+)?)", output)
    duration = _seconds_from_duration(duration_match.group(1)) if duration_match else None
    video_streams: list[dict[str, Any]] = []
    audio_streams: list[dict[str, Any]] = []
    for line in output.splitlines():
        if "Stream #" not in line:
            continue
        video = re.search(
            r"Video:\s*([^,]+).*?\b(\d{2,5})x(\d{2,5})\b.*?(\d+(?:\.\d+)?)\s*fps",
            line,
        )
        if video:
            video_streams.append(
                {
                    "codec": video.group(1).strip(),
                    "width": int(video.group(2)),
                    "height": int(video.group(3)),
                    "fps": float(video.group(4)),
                }
            )
        audio = re.search(
            r"Audio:\s*([^,]+).*?(\d+)\s*Hz,\s*([^,]+)",
            line,
        )
        if audio:
            audio_streams.append(
                {
                    "codec": audio.group(1).strip(),
                    "sample_rate_hz": int(audio.group(2)),
                    "channel_layout": audio.group(3).strip(),
                }
            )
    return {
        "status": "container_metadata_read_no_decode_or_playback",
        "duration_seconds": duration,
        "video_streams": video_streams,
        "audio_streams": audio_streams,
    }


def _collect_local_leads(request: dict[str, Any]) -> list[dict[str, Any]]:
    leads: list[dict[str, Any]] = []
    for field in ("local_authorized_source_leads", "private_local_source_candidates"):
        values = request.get(field, [])
        if not isinstance(values, list):
            raise ValueError(f"{field} must be a list when present.")
        for index, value in enumerate(values, 1):
            if not isinstance(value, dict) or not str(value.get("path") or "").strip():
                raise ValueError(f"Every {field} entry needs a local path.")
            item = deepcopy(value)
            item["request_field"] = field
            item["request_field_index"] = index
            leads.append(item)
    return leads


def _content_risks(lead: dict[str, Any], path: Path) -> list[str]:
    text = " ".join(
        str(value or "")
        for value in (
            path.stem,
            lead.get("role"),
            lead.get("selected_title"),
            lead.get("content_note"),
        )
    ).casefold()
    risks = [str(item) for item in lead.get("known_content_risks", []) if str(item).strip()]
    checks = (
        (("song", "first_time_in_forever", "do_you_want_to_build_a_snowman"), "song_or_music_dominant_source"),
        (("young_elsa", "young elsa", "childhood"), "young_character_variant_risk"),
        (("mixed", "ensemble", "cast"), "mixed_speaker_risk"),
        (("trailer", "teaser"), "trailer_or_teaser_risk"),
    )
    for terms, label in checks:
        if any(term in text for term in terms) and label not in risks:
            risks.append(label)
    return risks


def _local_review_ranking(
    lead: dict[str, Any], path: Path, metadata: dict[str, Any], risks: list[str]
) -> dict[str, Any]:
    role = str(lead.get("role") or "").casefold().replace("-", " ")
    binding = str(lead.get("continuity_binding_status") or "").casefold()
    score = 10
    reasons = ["owner-authorized local-library lead +10"]
    if "primary adult-present" in role or "primary adult present" in role:
        score += 45
        reasons.append("primary adult-present continuity +45")
    elif "earlier same-performer" in role or "supplement" in role:
        score += 22
        reasons.append("same-performer continuity supplement +22")
    elif "selected continuity" in role or "exact continuity" in role:
        score += 28
        reasons.append("selected-continuity source +28")
    if binding in {
        "official_credit_bound_to_selected_title",
        "verified_selected_title_in_exact_continuity",
        "project_owner_selected_exact_continuity",
    }:
        score += 18
        reasons.append("explicit selected-title binding +18")
    duration = metadata.get("duration_seconds")
    if isinstance(duration, (int, float)) and 0 < duration <= 1200:
        score += 8
        reasons.append("bounded short-form source +8")
    deductions = {
        "song_or_music_dominant_source": 28,
        "young_character_variant_risk": 45,
        "mixed_speaker_risk": 14,
        "trailer_or_teaser_risk": 10,
    }
    for risk in risks:
        amount = deductions.get(risk, 6)
        score -= amount
        reasons.append(f"{risk} -{amount}")
    bounded = max(0, min(score, 100))
    band = (
        "first_clean_range_review"
        if bounded >= 65
        else "supplementary_clean_range_review"
        if bounded >= 35
        else "low_priority_or_reject_before_range_selection"
    )
    return {
        "score": bounded,
        "raw_score_before_0_100_clamp": score,
        "band": band,
        "reasons": reasons,
        "metadata_rank_only": True,
        "auto_select_source": False,
        "auto_select_speaker_or_acoustic_group": False,
    }


def _range_review_entry(
    request: dict[str, Any], lead: dict[str, Any], source_id: str, risks: list[str]
) -> dict[str, Any]:
    target = request.get("identity_target") if isinstance(request.get("identity_target"), dict) else {}
    return {
        "queue_id": f"{request.get('candidate_id', 'candidate')}_{source_id}_clean_range_review_v1",
        "status": "needs_exact_bounded_ranges_and_human_audiovisual_review",
        "source_id": source_id,
        "selected_ranges": [],
        "target": {
            "character": deepcopy(target.get("character", {})),
            "variant": deepcopy(target.get("variant", {})),
            "speaker": deepcopy(target.get("speaker", {})),
            "performer": deepcopy(target.get("performer", {})),
        },
        "known_content_risks": risks,
        "range_constraints": {
            "minimum_seconds": 1.0,
            "maximum_seconds_each": 45.0,
            "maximum_ranges": 12,
            "maximum_total_seconds": 180.0,
            "minimum_approved_target_only_seconds_for_later_reference": 20.0,
        },
        "speaker_selection_contract": {
            "diarization_or_acoustic_grouping_may_group_similar_clips": True,
            "diarization_or_acoustic_grouping_identifies_a_person": False,
            "automatic_target_group_selection_allowed": False,
            "human_audiovisual_identity_review_required": True,
            "production_credit_or_cast_record_required": True,
            "wrong_or_uncertain_group_must_remain_unselected": True,
        },
        "clean_speech_checks": {
            "target_only_speech": "pending",
            "overlapping_speech": "pending_reject_if_true",
            "music": "pending_reject_if_material",
            "narration": "pending_reject_if_true",
            "sound_effects": "pending_reject_if_material",
            "stable_character_delivery": "pending",
            "technical_quality": "pending",
        },
        "next_action": str(
            lead.get("next_action")
            or "A human selects exact short time ranges, confirms the visible/audible target, then runs bounded private-local extraction."
        ),
    }


Probe = Callable[[Path], dict[str, Any]]


def build_local_voice_source_review_manifest(
    request: dict[str, Any], *, probe: Probe = probe_media_container
) -> dict[str, Any]:
    """Build a hash-bound, read-only review manifest for local source leads."""
    records: list[dict[str, Any]] = []
    for number, lead in enumerate(_collect_local_leads(request), 1):
        path = resolve_library_voice_source(str(lead["path"]))
        actual_hash = file_sha256(path)
        requested_hash = str(lead.get("sha256") or "").lower()
        if requested_hash and requested_hash != actual_hash:
            raise ValueError(
                "Local voice-source SHA-256 mismatch for "
                f"{_project_relative(path)}: expected {requested_hash}, got {actual_hash}."
            )
        metadata = probe(path)
        risks = _content_risks(lead, path)
        source_id = str(lead.get("source_id") or f"local_source_{number:03d}")
        rank = _local_review_ranking(lead, path, metadata, risks)
        records.append(
            {
                "source_id": source_id,
                "path": _project_relative(path),
                "role": str(lead.get("role") or "owner-authorized local source lead"),
                "selected_title": str(lead.get("selected_title") or ""),
                "request_field": lead["request_field"],
                "integrity": {
                    "sha256": actual_hash,
                    "request_sha256": requested_hash,
                    "request_hash_matches": True,
                    "size_bytes": path.stat().st_size,
                    "mtime_ns": path.stat().st_mtime_ns,
                },
                "container_metadata": metadata,
                "continuity_binding_status": str(
                    lead.get("continuity_binding_status")
                    or "owner_selected_local_lead_pending_production_credit_review"
                ),
                "performer_binding_status": str(
                    lead.get("performer_binding_status")
                    or "pending_human_scene_and_cast_credit_review"
                ),
                "known_content_risks": risks,
                "review_ranking": rank,
                "clean_range_review": _range_review_entry(request, lead, source_id, risks),
                "readiness": {
                    "container_and_integrity_audited": True,
                    "speaker_identity_proven": False,
                    "clean_target_only_range_selected": False,
                    "voice_reference_ready": False,
                    "voice_assignment_ready": False,
                    "activation_ready": False,
                },
            }
        )
    records.sort(
        key=lambda item: (
            -int(
                item.get("review_ranking", {}).get(
                    "raw_score_before_0_100_clamp",
                    item.get("review_ranking", {}).get("score", 0),
                )
                or 0
            ),
            str(item.get("source_id") or ""),
        )
    )
    for rank, item in enumerate(records, 1):
        item["review_ranking"]["rank"] = rank
    return {
        "schema_version": 1,
        "created_at": now_iso(),
        "candidate_id": str(request.get("candidate_id") or ""),
        "status": "local_sources_audited_clean_ranges_pending" if records else "no_local_source_leads",
        "identity_target": deepcopy(request.get("identity_target", {})),
        "sources": records,
        "selection": {
            "highest_ranked_source_id": records[0]["source_id"] if records else "",
            "source_auto_selected": False,
            "speaker_or_acoustic_group_auto_selected": False,
            "voice_assigned": False,
            "candidate_activated": False,
        },
        "operation_evidence": {
            "local_files_read_for_hash_and_container_metadata": bool(records),
            "audio_decoded_for_listening": False,
            "audio_played": False,
            "bounded_audio_extracted": False,
            "diarization_run": False,
            "voice_model_or_clone_run": False,
            "speech_generated": False,
            "voice_assigned": False,
            "candidate_activated": False,
        },
        "truth_note": "Ranking chooses which source a human should inspect first. It never proves or selects a target speaker, diarization group, or voice.",
    }


def build_clean_range_review_queue(manifest: dict[str, Any]) -> dict[str, Any]:
    """Flatten one evidence manifest into a human-facing bounded range queue."""
    entries = []
    for source in manifest.get("sources", []):
        entries.append(
            {
                "rank": source.get("review_ranking", {}).get("rank"),
                "source_id": source.get("source_id"),
                "path": source.get("path"),
                "role": source.get("role"),
                "selected_title": source.get("selected_title"),
                "source_sha256": source.get("integrity", {}).get("sha256"),
                "container_metadata": deepcopy(source.get("container_metadata", {})),
                "review_ranking": deepcopy(source.get("review_ranking", {})),
                "clean_range_review": deepcopy(source.get("clean_range_review", {})),
            }
        )
    return {
        "schema_version": 1,
        "created_at": now_iso(),
        "candidate_id": str(manifest.get("candidate_id") or ""),
        "status": "awaiting_human_bounded_range_selection" if entries else "no_local_source_leads",
        "entries": entries,
        "selection": {
            "selected_source_id": "",
            "selected_ranges": [],
            "selected_speaker_or_acoustic_group": "",
            "automatic_selection_allowed": False,
        },
        "completion_rule": "A queue entry is not voice evidence until exact short ranges pass human audiovisual identity, clean-speech, and technical-quality review.",
        "operations": {
            "audio_played": False,
            "audio_extracted": False,
            "diarization_run": False,
            "voice_model_or_clone_run": False,
            "voice_assigned": False,
            "candidate_activated": False,
        },
    }
