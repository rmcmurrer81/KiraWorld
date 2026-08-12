"""Provenance-first TemporaryAI voice *metadata* discovery.

The discovery layer indexes metadata and never downloads media, extracts audio,
trains a model, synthesizes speech, or activates a TemporaryAI. That boundary is
stage-scoped rather than a blanket ban on the TemporaryAI creator: an already
local, user-authorized source can later enter the separate bounded and
human-reviewed :mod:`Core.temp_ai_local_media_intake` lane.
"""
from __future__ import annotations

import json
import hashlib
import ipaddress
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from Core.temp_ai_local_voice_source_review import build_local_voice_source_review_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = PROJECT_ROOT / "TemporaryAI" / "candidates"
REQUEST_FILENAME = "voice_discovery_request.json"
INDEX_FILENAME = "voice_discovery_index.json"

VERIFIED_CONSENT = {
    "explicit_performer_consent",
    "explicit_rightsholder_and_performer_consent",
    "self_recorded_and_authorized",
}
PERMITTED_RECORDING_RIGHTS = {
    "owned",
    "licensed_for_voice_model_use",
    "public_domain_voice_model_use_reviewed",
    "explicitly_authorized_for_voice_model_use",
    "self_recorded",
}
OPEN_MODEL_LICENSES = {
    "apache-2.0",
    "bsd-2-clause",
    "bsd-3-clause",
    "cc-by-4.0",
    "mit",
    "mpl-2.0",
}
DIRECT_VIDEO_METADATA_HOSTS = {"www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}
REVIEWED_SOURCE_AUTHORITY = {
    "official_rightsholder_page",
    "official_studio_page",
    "official_verified_channel",
    "reviewed_archive_primary_source",
}
POSSIBLE_SOURCE_AUTHORITY = {
    "platform_verified_publisher_candidate",
    "platform_verified_disney_branded_channel_candidate",
    "official_publisher_candidate_pending_owner_review",
}
VERIFIED_CONTINUITY_BINDINGS = {
    "verified_exact_selected_continuity",
    "verified_selected_title_in_exact_continuity",
}
VERIFIED_PERFORMER_BINDINGS = {
    "official_credit_bound_to_target_speaker_and_title",
    "verified_cast_credit_for_selected_title",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str, limit: int = 100) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return cleaned[:limit] or "unknown"


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def resolve_candidate_dir(candidate_id: str) -> Path:
    """Resolve one existing candidate without allowing traversal or symlink escape."""
    if not candidate_id or slug(candidate_id) != candidate_id:
        raise ValueError("candidate_id must be a normalized lowercase identifier.")
    root = CANDIDATE_ROOT.resolve()
    candidate = (root / candidate_id).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("candidate_id escapes TemporaryAI/candidates.") from exc
    if not candidate.is_dir():
        raise FileNotFoundError(f"TemporaryAI candidate does not exist: {candidate_id}")
    return candidate


def canonical_url(raw_url: str) -> str:
    """Return a stable exact HTTP(S) URL while dropping common tracking fields."""
    value = str(raw_url or "").strip()
    if not value:
        return ""
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Voice source URL must be an absolute HTTP(S) URL: {value}")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Voice discovery rejects source URLs containing credentials.")
    hostname = str(parsed.hostname or "").lower().rstrip(".")
    if (
        hostname == "localhost"
        or hostname.endswith(".localhost")
        or hostname.endswith((".local", ".internal", ".lan", ".home", ".home.arpa"))
        or ("." not in hostname and ":" not in hostname)
    ):
        raise ValueError("Voice discovery rejects localhost or private single-label source URLs.")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
        or address.is_multicast
    ):
        raise ValueError("Voice discovery rejects non-public IP-literal source URLs.")
    host = parsed.netloc.lower()
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/")
        if video_id:
            return f"https://www.youtube.com/watch?v={urllib.parse.quote(video_id)}"
    kept = [
        (key, item)
        for key, item in query
        if not key.lower().startswith("utm_") and key.lower() not in {"si", "feature", "ref", "source"}
    ]
    normalized_host = "www.youtube.com" if host in {"youtube.com", "m.youtube.com"} else host
    normalized_query = urllib.parse.urlencode(kept, doseq=True)
    return urllib.parse.urlunsplit((parsed.scheme.lower(), normalized_host, parsed.path or "/", normalized_query, ""))


def direct_video_metadata_allowed(url: str) -> bool:
    return str(urllib.parse.urlsplit(canonical_url(url)).hostname or "").lower() in DIRECT_VIDEO_METADATA_HOSTS


def _subject_kind(profile: dict[str, Any], creation: dict[str, Any]) -> str:
    category = str(profile.get("ui_category") or creation.get("ui_category") or "").lower()
    ai_type = str(profile.get("ai_type") or creation.get("ai_type") or "").lower()
    creation_type = str(creation.get("creation_type") or "").lower()
    if "historical" in category or "historical" in ai_type or creation_type == "historical_person":
        return "historical_person"
    if "fictional" in category or "canon_reconstruction" in ai_type or creation_type == "fictional_character":
        return "fictional_character"
    if "generated" in ai_type or creation_type in {"generated_original", "expert"} or "expert" in ai_type:
        return "generated_original"
    if "memory_relative" in ai_type:
        return "memory_relative"
    return "unknown_review_required"


def build_candidate_voice_discovery_request(
    profile: dict[str, Any],
    creation_request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a safe generic discovery request from a candidate scaffold."""
    creation = creation_request or {}
    candidate_id = str(profile.get("candidate_id") or creation.get("candidate_id") or "").strip()
    if not candidate_id:
        raise ValueError("Candidate profile needs candidate_id before voice discovery can be scaffolded.")
    display_name = str(
        profile.get("display_name")
        or creation.get("display_name_or_role")
        or candidate_id.replace("_", " ").title()
    ).strip()
    kind = _subject_kind(profile, creation)
    adaptation = profile.get("adaptation_lock") if isinstance(profile.get("adaptation_lock"), dict) else {}
    selected_identity = str(adaptation.get("selected_identity") or "").strip()
    version = str(
        adaptation.get("knowledge_cutoff")
        or profile.get("knowledge_plan", {}).get("version_or_life_point")
        or creation.get("input", {}).get("version_life_point_or_canon_point")
        or creation.get("source_plan", {}).get("canon_or_version_anchor")
        or ""
    ).strip()
    gender = str(profile.get("gender_preference") or "").strip().lower()
    voice_terms = ["English", "synthetic voice", "licensed"]
    model_queries = ["english tts"]
    if gender in {"female", "woman", "feminine"}:
        voice_terms.append("adult feminine")
        model_queries.append("female tts")
    elif gender in {"male", "man", "masculine"}:
        voice_terms.append("adult masculine")
        model_queries.append("male tts")

    character_id = slug(display_name) if kind == "fictional_character" else ""
    variant_id = slug(selected_identity or version) if kind == "fictional_character" and (selected_identity or version) else "base_version_review_required"
    speaker_id = slug(f"{display_name} {selected_identity or version}")
    recording_queries: list[str] = []
    archive_queries: list[str] = []
    if kind == "fictional_character":
        recording_queries = [
            f'"{display_name}" "{selected_identity or version}" official dialogue clip'.strip(),
            f'"{display_name}" "{selected_identity or version}" official scene'.strip(),
            f'"{display_name}" "{selected_identity or version}" official trailer dialogue'.strip(),
        ]
        model_queries.append(f"{display_name} voice tts")
    elif kind == "historical_person":
        recording_queries = [
            f'"{display_name}" verified voice recording',
            f'"{display_name}" speech recording archive',
        ]
        archive_queries = [f'"{display_name}" AND (audio OR sound)']
        model_queries.append(f"{display_name} voice model")

    return {
        "schema_version": 1,
        "request_id": f"{candidate_id}_voice_discovery_v1",
        "created_at": now_iso(),
        "candidate_id": candidate_id,
        "status": "metadata_discovery_request_not_run",
        "identity_target": {
            "subject_kind": kind,
            "display_name": display_name,
            "character": {"character_id": character_id, "label": display_name if character_id else ""},
            "variant": {"variant_id": variant_id, "label": selected_identity or version},
            "speaker": {"speaker_id": speaker_id, "label": display_name},
            "performer": {
                "performer_id": "unknown_review_required" if kind == "fictional_character" else "not_applicable_or_subject_self",
                "name": "",
                "living_status": "unknown_treat_as_living_for_consent_gate" if kind == "fictional_character" else "deceased_or_unknown_review_required",
                "consent_status": "not_found",
                "consent_evidence_urls": [],
            },
            "version_or_timepoint": version,
            "continuity": {
                "selected_titles": [],
                "endpoint": version,
                "language": "English",
                "excluded_titles_or_versions": [],
            },
            "shared_performer_does_not_merge_speakers": True,
        },
        "discovery": {
            "metadata_only": True,
            "allow_media_download": False,
            "allow_audio_extraction": False,
            "allow_model_download": False,
            "recording_queries": recording_queries,
            "archive_queries": archive_queries,
            "synthetic_model_queries": model_queries,
            "desired_non_imitative_voice_traits": voice_terms,
            "max_results_per_query": 5,
            "rank_recording_candidates": True,
            "auto_select_recording": False,
            "preferred_source_classes": [
                "official rightsholder title/video pages",
                "official studio or distributor channels",
                "reviewed archives with exact provenance",
            ],
        },
        "source_authority_registry": [],
        "seed_recordings": [],
        "seed_synthetic_models": [],
        "historical_voice_factors": {
            "anchor_date_or_era": {"value": version if kind == "historical_person" else "", "evidence_urls": [], "confidence": "unreviewed"},
            "chronological_age_or_band": {"value": "", "evidence_urls": [], "confidence": "unknown"},
            "places_and_regions": {"value": [], "evidence_urls": [], "confidence": "unknown"},
            "education_and_profession": {"value": [], "evidence_urls": [], "confidence": "unknown"},
            "languages_and_dialects": {"value": ["English"] if kind == "historical_person" else [], "evidence_urls": [], "confidence": "unreviewed"},
            "documented_health_or_voice_notes": {"value": [], "evidence_urls": [], "confidence": "unknown"},
        },
        "policy": {
            "living_performer_exact_voice_requires_explicit_consent_and_rights": True,
            "living_performer_consent_gate_scope": "model_assignment_official_claim_or_public_use_not_bounded_private_local_candidate_intake",
            "official_media_is_not_voice_clone_permission": True,
            "licensed_model_is_not_performer_consent": True,
            "historical_missing_recording_requires_speculative_label": True,
            "false_official_voice_claim_forbidden": True,
            "discovery_no_download_boundary_is_stage_scoped": True,
            "separate_private_local_bounded_intake_supported": True,
            "private_local_intake_path": "Core/temp_ai_local_media_intake.py",
            "private_local_intake_does_not_grant_public_release_or_official_claims": True,
            "activation_allowed": False,
        },
        "review_requirements": {
            "exact_continuity_binding_required": True,
            "official_performer_credit_binding_required": True,
            "target_only_speaker_verification_required": True,
            "diarization_is_not_identity_proof": True,
            "human_transcript_or_listening_review_required": True,
            "minimum_reviewed_target_only_seconds": 20.0,
            "technical_quality_review_required": True,
            "rights_and_consent_review_required": True,
            "metadata_rank_never_auto_assigns_a_voice": True,
        },
    }


def load_or_create_request(candidate_id: str) -> tuple[Path, dict[str, Any]]:
    candidate_dir = resolve_candidate_dir(candidate_id)
    request_path = candidate_dir / REQUEST_FILENAME
    if request_path.exists():
        request = read_json(request_path, {})
        validate_request(request, expected_candidate_id=candidate_id)
        return request_path, request
    profile = read_json(candidate_dir / "temporary_ai_profile.json", {})
    creation = read_json(candidate_dir / "creation_request.json", {})
    request = build_candidate_voice_discovery_request(profile, creation)
    validate_request(request, expected_candidate_id=candidate_id)
    write_json(request_path, request)
    return request_path, request


def validate_request(request: dict[str, Any], *, expected_candidate_id: str = "") -> None:
    if int(request.get("schema_version", 0) or 0) != 1:
        raise ValueError("voice discovery request schema_version must be 1.")
    candidate_id = str(request.get("candidate_id") or "")
    if not candidate_id or slug(candidate_id) != candidate_id:
        raise ValueError("voice discovery request candidate_id is invalid.")
    if expected_candidate_id and candidate_id != expected_candidate_id:
        raise ValueError("voice discovery request candidate_id does not match its candidate folder.")
    discovery = request.get("discovery") if isinstance(request.get("discovery"), dict) else {}
    if discovery.get("metadata_only") is not True:
        raise ValueError("Voice discovery is metadata-only.")
    forbidden = {
        "allow_media_download": discovery.get("allow_media_download"),
        "allow_audio_extraction": discovery.get("allow_audio_extraction"),
        "allow_model_download": discovery.get("allow_model_download"),
    }
    enabled = [name for name, value in forbidden.items() if value not in {False, None}]
    if enabled:
        raise ValueError(f"Voice discovery cannot enable: {', '.join(enabled)}")
    target = request.get("identity_target") if isinstance(request.get("identity_target"), dict) else {}
    for lane in ("character", "variant", "speaker", "performer"):
        if not isinstance(target.get(lane), dict):
            raise ValueError(f"identity_target.{lane} must be an object.")
    for collection in ("seed_recordings", "seed_synthetic_models"):
        if not isinstance(request.get(collection, []), list):
            raise ValueError(f"{collection} must be a list.")
        for item in request.get(collection, []):
            if not isinstance(item, dict) or not item.get("url"):
                raise ValueError(f"Every {collection} item must be an object with an exact URL.")
            canonical_url(str(item["url"]))
    registry = request.get("source_authority_registry", [])
    if not isinstance(registry, list):
        raise ValueError("source_authority_registry must be a list.")
    for item in registry:
        if not isinstance(item, dict):
            raise ValueError("Every source_authority_registry item must be an object.")
        if item.get("publisher_url"):
            canonical_url(str(item["publisher_url"]))
    policy = request.get("policy") if isinstance(request.get("policy"), dict) else {}
    if policy.get("activation_allowed") not in {False, None}:
        raise ValueError("Voice discovery cannot grant TemporaryAI activation.")


def _yt_dlp_command() -> list[str]:
    executable = shutil.which("yt-dlp")
    return [executable] if executable else [sys.executable, "-m", "yt_dlp"]


def _run_json_command(command: list[str], timeout: int = 90) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        error = completed.stderr.strip().splitlines()[-1:] or ["metadata provider failed"]
        raise RuntimeError(error[0][:500])
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Metadata provider returned invalid JSON.") from exc


def fetch_video_metadata(url: str) -> dict[str, Any]:
    """Fetch page metadata only. yt-dlp receives explicit skip-download flags."""
    command = _yt_dlp_command() + [
        "--dump-single-json",
        "--skip-download",
        "--no-playlist",
        "--no-warnings",
        "--no-write-thumbnail",
        "--no-write-subs",
        canonical_url(url),
    ]
    data = _run_json_command(command)
    return _normalize_youtube_entry(data, query="direct_url_metadata")


def search_video_metadata(query: str, limit: int) -> list[dict[str, Any]]:
    """Search public video metadata without requesting audio/video payloads."""
    count = max(1, min(int(limit), 20))
    command = _yt_dlp_command() + [
        "--flat-playlist",
        "--dump-single-json",
        "--skip-download",
        "--no-warnings",
        "--playlist-end",
        str(count),
        f"ytsearch{count}:{query}",
    ]
    payload = _run_json_command(command)
    return [_normalize_youtube_entry(item, query=query) for item in payload.get("entries", []) if isinstance(item, dict)]


def _normalize_youtube_entry(item: dict[str, Any], *, query: str) -> dict[str, Any]:
    video_id = str(item.get("id") or "").strip()
    url = item.get("webpage_url") or item.get("original_url") or item.get("url") or ""
    if video_id and (not str(url).startswith("http") or "youtube" in str(item.get("extractor_key", "")).lower()):
        url = f"https://www.youtube.com/watch?v={video_id}"
    return {
        "discovery_provider": "youtube_metadata_via_yt_dlp",
        "discovery_query": query,
        "url": canonical_url(str(url)),
        "title": str(item.get("title") or ""),
        "publisher": str(item.get("channel") or item.get("uploader") or item.get("uploader_id") or ""),
        "publisher_url": str(item.get("channel_url") or item.get("uploader_url") or ""),
        "published_at": str(item.get("upload_date") or item.get("release_date") or ""),
        "duration_seconds": item.get("duration"),
        "source_kind": "online_video_metadata",
        "authority": "unknown_until_reviewed",
    }


def _fetch_json_url(url: str, timeout: int = 30) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "Kira-TempAI-Voice-Discovery/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed metadata APIs
        return json.loads(response.read().decode("utf-8"))


def search_archive_metadata(query: str, limit: int) -> list[dict[str, Any]]:
    """Search Internet Archive item metadata; item media is never requested."""
    params = urllib.parse.urlencode(
        {
            "q": query,
            "fl[]": ["identifier", "title", "creator", "date", "licenseurl", "mediatype"],
            "rows": max(1, min(int(limit), 20)),
            "page": 1,
            "output": "json",
        },
        doseq=True,
    )
    payload = _fetch_json_url(f"https://archive.org/advancedsearch.php?{params}")
    results = []
    for item in payload.get("response", {}).get("docs", []):
        identifier = str(item.get("identifier") or "").strip()
        if not identifier:
            continue
        results.append(
            {
                "discovery_provider": "internet_archive_metadata_api",
                "discovery_query": query,
                "url": f"https://archive.org/details/{urllib.parse.quote(identifier)}",
                "title": str(item.get("title") or ""),
                "publisher": str(item.get("creator") or ""),
                "published_at": str(item.get("date") or ""),
                "source_kind": "archive_item_metadata",
                "authority": "archive_catalog_candidate_identity_unverified",
                "license_url": str(item.get("licenseurl") or ""),
                "media_type": str(item.get("mediatype") or ""),
            }
        )
    return results


def search_huggingface_model_metadata(query: str, limit: int) -> list[dict[str, Any]]:
    """Search Hugging Face model cards without downloading weights or datasets."""
    params = urllib.parse.urlencode({"search": query, "limit": max(1, min(int(limit), 20)), "full": "true"})
    payload = _fetch_json_url(f"https://huggingface.co/api/models?{params}")
    results = []
    for item in payload if isinstance(payload, list) else []:
        model_id = str(item.get("modelId") or item.get("id") or "").strip()
        if not model_id:
            continue
        tags = [str(tag) for tag in item.get("tags", [])]
        card = item.get("cardData") if isinstance(item.get("cardData"), dict) else {}
        license_id = str(card.get("license") or "")
        if not license_id:
            license_id = next((tag.partition(":")[2] for tag in tags if tag.startswith("license:")), "")
        results.append(
            {
                "discovery_provider": "huggingface_model_metadata_api",
                "discovery_query": query,
                "url": f"https://huggingface.co/{model_id}",
                "model_id": model_id,
                "title": model_id,
                "publisher": str(item.get("author") or model_id.partition("/")[0]),
                "last_modified": str(item.get("lastModified") or ""),
                "pipeline_tag": str(item.get("pipeline_tag") or ""),
                "tags": tags,
                "license_id": license_id.lower(),
                "source_kind": "synthetic_voice_model_metadata",
            }
        )
    return results


def _identity_binding(target: dict[str, Any]) -> dict[str, Any]:
    return {
        "character": deepcopy(target.get("character", {})),
        "variant": deepcopy(target.get("variant", {})),
        "speaker": deepcopy(target.get("speaker", {})),
        "performer": deepcopy(target.get("performer", {})),
        "continuity": deepcopy(target.get("continuity", {})),
        "shared_performer_does_not_merge_speakers": True,
    }


def _normalized_publisher_url(value: str) -> str:
    """Normalize a public publisher URL without requiring it to name media."""
    try:
        return canonical_url(value).rstrip("/")
    except ValueError:
        return ""


def _apply_source_authority_registry(
    seed: dict[str, Any], registry: list[dict[str, Any]]
) -> dict[str, Any]:
    """Attach only pre-reviewed publisher metadata; never infer authority from a badge.

    A platform verification badge is useful triage evidence, but it does not prove
    that a clip is an authorized voice-model source.  Registry entries are exact
    publisher bindings supplied by a candidate dossier or later human review.
    """
    result = deepcopy(seed)
    if isinstance(result.get("publisher_verification"), dict):
        return result
    publisher = str(result.get("publisher") or result.get("channel") or "").strip().casefold()
    publisher_url = _normalized_publisher_url(
        str(result.get("publisher_url") or result.get("channel_url") or "")
    )
    for entry in registry:
        if not isinstance(entry, dict):
            continue
        expected_name = str(entry.get("publisher") or "").strip().casefold()
        expected_url = _normalized_publisher_url(str(entry.get("publisher_url") or ""))
        name_match = bool(expected_name and publisher and expected_name == publisher)
        url_match = bool(expected_url and publisher_url and expected_url == publisher_url)
        if not (name_match or url_match):
            continue
        result["publisher_verification"] = {
            "status": str(entry.get("status") or "publisher_registry_match_pending_review"),
            "publisher": str(entry.get("publisher") or result.get("publisher") or ""),
            "publisher_url": str(entry.get("publisher_url") or result.get("publisher_url") or ""),
            "evidence_urls": list(entry.get("evidence_urls") or []),
            "note": str(
                entry.get("note")
                or "Exact publisher registry match; recording rights and target-speaker review remain separate."
            ),
        }
        break
    return result


def _rights_from_seed(seed: dict[str, Any]) -> dict[str, Any]:
    rights = seed.get("rights") if isinstance(seed.get("rights"), dict) else {}
    return {
        "recording_copyright_status": str(rights.get("recording_copyright_status") or "unknown"),
        "license_id": str(rights.get("license_id") or ""),
        "license_url": str(rights.get("license_url") or seed.get("license_url") or ""),
        "voice_model_or_training_rights": str(rights.get("voice_model_or_training_rights") or "not_established"),
        "performer_consent_status": str(rights.get("performer_consent_status") or "not_found"),
        "performer_consent_evidence_urls": list(rights.get("performer_consent_evidence_urls") or []),
        "character_or_brand_rights_status": str(rights.get("character_or_brand_rights_status") or "not_established"),
        "review_note": str(rights.get("review_note") or "Public availability and an official uploader do not grant voice-model rights."),
    }


def _clean_segment_gate(target: dict[str, Any], seed: dict[str, Any]) -> dict[str, Any]:
    present = list(seed.get("speakers_present") or [])
    target_only = (
        seed.get("target_only_segment_verification")
        if isinstance(seed.get("target_only_segment_verification"), dict)
        else {}
    )
    return {
        "status": "pending_no_audio_ingested",
        "target_speaker_id": str(target.get("speaker", {}).get("speaker_id") or ""),
        "known_speakers_present": present,
        "shared_performer_note": "Two character variants may share one performer and base timbre; their dialogue segments still need correct speaker/variant labels.",
        "requirements": [
            "Obtain media only in a later explicitly authorized intake step.",
            "Use diarization only to create review groups; it is not speaker identity proof.",
            "Align a reliable transcript, production credit, or human listening review to the target speaker and variant.",
            "Reject overlapping voices, narration, music-heavy speech, effects-heavy speech, and unclear speaker turns.",
            "Approve only target-only clean segments; keep every source time range and exact URL.",
            "Require at least 20 seconds of reviewed clean target-only speech before model-reference preparation.",
        ],
        "diarization_required_if_mixed_or_unknown": len(present) != 1,
        "diarization_is_speaker_identity_proof": False,
        "human_target_speaker_review_required": True,
        "approved_clean_seconds": 0.0,
        "target_only_segment_verification": {
            "status": str(target_only.get("status") or "pending_no_reviewed_segments"),
            "approved_source_ranges": [],
            "transcript_alignment_status": "pending",
            "human_identity_review_status": "pending",
            "overlap_rejected": False,
            "music_and_effects_rejected": False,
            "minimum_reviewed_seconds": 20.0,
            "passed": False,
        },
    }


def _source_authority_gate(seed: dict[str, Any]) -> dict[str, Any]:
    verification = (
        seed.get("publisher_verification")
        if isinstance(seed.get("publisher_verification"), dict)
        else {}
    )
    status = str(verification.get("status") or "unverified_publisher_metadata")
    if status in REVIEWED_SOURCE_AUTHORITY:
        gate_status = "reviewed_source_authority"
        score = 30
    elif status in POSSIBLE_SOURCE_AUTHORITY:
        gate_status = "possible_official_source_pending_review"
        score = 18
    else:
        gate_status = "unverified_source_authority"
        score = 0
    return {
        "status": gate_status,
        "publisher_verification_status": status,
        "evidence_urls": list(verification.get("evidence_urls") or []),
        "passed_for_provenance_triage": gate_status == "reviewed_source_authority",
        "voice_use_rights_proven": False,
        "ranking_points": score,
        "note": str(
            verification.get("note")
            or "A source badge or official uploader can support provenance triage but cannot grant voice-model rights."
        ),
    }


def _identity_evidence_gate(seed: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    continuity = (
        seed.get("continuity_binding")
        if isinstance(seed.get("continuity_binding"), dict)
        else {}
    )
    performer = (
        seed.get("performer_credit_binding")
        if isinstance(seed.get("performer_credit_binding"), dict)
        else {}
    )
    continuity_status = str(continuity.get("status") or "unverified_from_metadata")
    performer_status = str(performer.get("status") or "unverified_from_metadata")
    target_performer_id = str(target.get("performer", {}).get("performer_id") or "")
    bound_performer_id = str(performer.get("performer_id") or "")
    performer_id_matches = bool(
        target_performer_id
        and bound_performer_id
        and target_performer_id == bound_performer_id
    )
    continuity_passed = continuity_status in VERIFIED_CONTINUITY_BINDINGS
    performer_passed = (
        performer_status in VERIFIED_PERFORMER_BINDINGS and performer_id_matches
    )
    return {
        "continuity": {
            "status": continuity_status,
            "selected_title": str(continuity.get("selected_title") or ""),
            "evidence_urls": list(continuity.get("evidence_urls") or []),
            "passed": continuity_passed,
        },
        "performer_credit": {
            "status": performer_status,
            "performer_id": bound_performer_id,
            "target_performer_id": target_performer_id,
            "performer_id_matches": performer_id_matches,
            "evidence_urls": list(performer.get("evidence_urls") or []),
            "passed": performer_passed,
        },
        "exact_character_variant_speaker_binding_required": True,
        "passed": continuity_passed and performer_passed,
    }


def _technical_quality_gate(seed: dict[str, Any]) -> dict[str, Any]:
    reported = (
        seed.get("technical_quality_review")
        if isinstance(seed.get("technical_quality_review"), dict)
        else {}
    )
    return {
        "status": "pending_no_audio_ingested",
        "reported_metadata": deepcopy(reported),
        "requirements": {
            "minimum_sample_rate_hz": 24000,
            "minimum_total_reviewed_target_only_seconds": 20.0,
            "speech_not_clipped": True,
            "speech_to_noise_and_reverb_human_review": True,
            "reject_overlapping_speakers": True,
            "reject_music_heavy_or_effects_heavy_speech": True,
            "consistent_language_and_character_delivery": True,
        },
        "passed": False,
        "note": "Page metadata cannot prove acoustic quality; analyze only after separately authorized intake.",
    }


def _content_risk_flags(seed: dict[str, Any]) -> list[str]:
    title = str(seed.get("title") or "").lower()
    flags: list[str] = []
    for token, label in (
        ("trailer", "trailer_likely_mixed_music_effects_and_speakers"),
        ("teaser", "teaser_likely_music_or_little_dialogue"),
        ("interview", "performer_interview_is_not_character_delivery"),
        ("behind the scenes", "behind_the_scenes_may_mix_performer_and_character_audio"),
        ("sing", "singing_is_not_clean_spoken_dialogue"),
        ("song", "song_is_not_clean_spoken_dialogue"),
        ("young elsa", "young_character_variant_does_not_match_adult_target"),
    ):
        if token in title and label not in flags:
            flags.append(label)
    return flags


def _recording_triage_ranking(
    seed: dict[str, Any],
    relevance: dict[str, Any],
    source_gate: dict[str, Any],
    evidence_gate: dict[str, Any],
) -> dict[str, Any]:
    score = int(source_gate.get("ranking_points", 0) or 0)
    reasons: list[str] = []
    if score:
        reasons.append(f"source authority +{score}")
    if relevance.get("status") == "possible_target_lead_metadata_only":
        score += 20
        reasons.append("target terms +20")
    elif relevance.get("status") == "rejected_wrong_or_ambiguous_identity_metadata":
        score -= 45
        reasons.append("excluded or ambiguous identity -45")
    else:
        score -= 10
        reasons.append("low metadata relevance -10")
    if evidence_gate.get("continuity", {}).get("passed"):
        score += 20
        reasons.append("exact selected continuity +20")
    if evidence_gate.get("performer_credit", {}).get("passed"):
        score += 20
        reasons.append("official performer credit binding +20")
    risks = _content_risk_flags(seed)
    if risks:
        deduction = min(24, 6 * len(risks))
        score -= deduction
        reasons.append(f"content-risk flags -{deduction}")
    bounded = max(0, min(score, 100))
    band = "high_priority_review_lead" if bounded >= 65 else "medium_priority_review_lead" if bounded >= 35 else "low_priority_or_reject_lead"
    return {
        "score": bounded,
        "band": band,
        "reasons": reasons,
        "content_risk_flags": risks,
        "metadata_rank_only": True,
        "auto_select_allowed": False,
        "note": "Rank chooses review order only. It never verifies a speaker, grants rights, or assigns a voice.",
    }


def _metadata_relevance(seed: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    title = str(seed.get("title") or "")
    title_slug = f"_{slug(title, 300)}_"
    excluded = [str(item) for item in target.get("excluded_identity_names", [])]
    excluded_hits = [item for item in excluded if f"_{slug(item, 200)}_" in title_slug]
    labels = [
        str(target.get("display_name") or ""),
        str(target.get("character", {}).get("label") or ""),
        str(target.get("speaker", {}).get("label") or ""),
        *[str(item) for item in target.get("identity_aliases", [])],
    ]
    meaningful = {
        token
        for label in labels
        for token in slug(label, 300).split("_")
        if len(token) >= 4 and token not in {"home", "main", "english", "smith", "historical", "subject"}
    }
    hits = sorted(token for token in meaningful if f"_{token}_" in title_slug)
    if excluded_hits:
        status = "rejected_wrong_or_ambiguous_identity_metadata"
    elif hits:
        status = "possible_target_lead_metadata_only"
    else:
        status = "low_relevance_or_unverified_search_result"
    return {
        "status": status,
        "matched_target_terms": hits,
        "excluded_identity_hits": excluded_hits,
        "note": "Title/query relevance is only triage; it never verifies the person, character variant, speaker, or performer.",
    }


def _recording_candidate(seed: dict[str, Any], target: dict[str, Any], number: int) -> dict[str, Any]:
    url = canonical_url(str(seed.get("url") or ""))
    rights = _rights_from_seed(seed)
    performer = target.get("performer", {}) if isinstance(target.get("performer"), dict) else {}
    consent = rights["performer_consent_status"] or str(performer.get("consent_status") or "not_found")
    if consent == "not_found":
        consent = str(performer.get("consent_status") or "not_found")
    training_rights = rights["voice_model_or_training_rights"]
    speaker_verification = seed.get("speaker_identity_verification") if isinstance(seed.get("speaker_identity_verification"), dict) else {}
    verification_status = str(speaker_verification.get("status") or "unverified_metadata_candidate")
    authenticity_status = str(seed.get("recording_authenticity_status") or "unverified_metadata_candidate")
    living_status = str(performer.get("living_status") or "unknown_treat_as_living_for_consent_gate")
    living_gate = living_status not in {"deceased", "not_applicable_historical_subject_deceased"}
    source_gate = _source_authority_gate(seed)
    evidence_gate = _identity_evidence_gate(seed, target)
    technical_gate = _technical_quality_gate(seed)
    blockers: list[str] = []
    if not source_gate["passed_for_provenance_triage"]:
        blockers.append("source authority/provenance is not fully reviewed")
    if not evidence_gate["continuity"]["passed"]:
        blockers.append("exact selected-title continuity binding is not verified")
    if not evidence_gate["performer_credit"]["passed"]:
        blockers.append("official performer credit is not exactly bound to this target speaker and title")
    if training_rights not in PERMITTED_RECORDING_RIGHTS:
        blockers.append("voice-model/training rights are not explicitly established")
    if living_gate and consent not in VERIFIED_CONSENT:
        blockers.append("explicit living-performer consent is not established")
    if verification_status not in {"verified_target_speaker", "verified_historical_subject"}:
        blockers.append("target speaker identity is not verified")
    if authenticity_status not in {"verified_original_recording", "verified_broadcast_performance"}:
        blockers.append("recording authenticity/provenance is not fully verified")
    relevance = _metadata_relevance(seed, target)
    if relevance["status"] != "possible_target_lead_metadata_only":
        blockers.append("search-result identity relevance is low, ambiguous, or rejected")
    blockers.append("no clean target-only audio segments have been ingested and reviewed")
    ranking = _recording_triage_ranking(seed, relevance, source_gate, evidence_gate)
    return {
        "source_id": str(seed.get("source_id") or f"recording_candidate_{number:03d}"),
        "exact_url": url,
        "canonical_url": url,
        "title": str(seed.get("title") or ""),
        "publisher_or_channel": str(seed.get("publisher") or ""),
        "publisher_url": str(seed.get("publisher_url") or ""),
        "published_at": str(seed.get("published_at") or ""),
        "duration_seconds": seed.get("duration_seconds"),
        "source_kind": str(seed.get("source_kind") or "online_metadata_candidate"),
        "authority": str(seed.get("authority") or "unknown_until_reviewed"),
        "discovery_provider": str(seed.get("discovery_provider") or "seeded_exact_url"),
        "discovery_query": str(seed.get("discovery_query") or ""),
        "metadata_relevance": relevance,
        "review_ranking": ranking,
        "identity_binding": _identity_binding(target),
        "source_authority_gate": source_gate,
        "identity_evidence_gate": evidence_gate,
        "speakers_present": list(seed.get("speakers_present") or []),
        "performers_present": list(seed.get("performers_present") or []),
        "speaker_identity_verification": {
            "status": verification_status,
            "evidence_urls": list(speaker_verification.get("evidence_urls") or []),
            "note": str(speaker_verification.get("note") or "Search metadata is not biometric or speaker identity proof."),
        },
        "recording_authenticity_status": authenticity_status,
        "rights": rights,
        "media_state": {
            "metadata_only": True,
            "media_downloaded": False,
            "audio_extracted": False,
            "audio_saved": False,
            "captions_downloaded": False,
        },
        "clean_segment_gate": _clean_segment_gate(target, seed),
        "technical_quality_gate": technical_gate,
        "eligibility": {
            "broad_non_biometric_style_reference": True,
            "eligible_for_voice_model_input_now": False,
            "blocked_reasons": blockers,
            "official_voice_claim_allowed": False,
            "next_step": "Review the highest-ranked exact-continuity sources, then resolve provenance/rights/consent and use the separate target-only speaker/quality intake if authorized.",
        },
    }


def _model_candidate(seed: dict[str, Any], target: dict[str, Any], number: int) -> dict[str, Any]:
    url = canonical_url(str(seed.get("url") or ""))
    license_id = str(seed.get("license_id") or "").lower()
    identity_type = str(seed.get("voice_identity_type") or "unknown_review_required")
    identity_labels = [
        str(target.get("performer", {}).get("name") or ""),
        str(target.get("character", {}).get("label") or ""),
        str(target.get("speaker", {}).get("label") or ""),
        *[str(item) for item in target.get("identity_aliases", [])],
    ]
    identity_haystack = slug(
        " ".join(
            [
                str(seed.get("title") or ""),
                str(seed.get("model_id") or ""),
                str(seed.get("discovery_query") or ""),
            ]
        ),
        500,
    )
    matched_identity_labels = [
        label
        for label in identity_labels
        if label and len(slug(label)) >= 4 and slug(label) in identity_haystack
    ]
    claims_target = bool(seed.get("claims_target_performer_or_character_voice")) or bool(matched_identity_labels)
    performer = target.get("performer", {}) if isinstance(target.get("performer"), dict) else {}
    living_status = str(performer.get("living_status") or "unknown_treat_as_living_for_consent_gate")
    consent = str(performer.get("consent_status") or "not_found")
    living_gate = living_status not in {"deceased", "not_applicable_historical_subject_deceased"}
    blockers: list[str] = []
    if license_id not in OPEN_MODEL_LICENSES:
        blockers.append("model license is absent, unknown, custom, or not yet reviewed")
    if not bool(seed.get("voice_or_dataset_rights_documented")):
        blockers.append("model license does not by itself prove the voice/dataset identity rights")
    if claims_target and living_gate and consent not in VERIFIED_CONSENT:
        blockers.append("model targets a living performer/character voice without verified performer consent")
    if identity_type not in {"generic_original", "licensed_stock_voice"} and not bool(seed.get("identity_authorization_documented")):
        blockers.append("voice identity authorization is not documented")
    return {
        "model_candidate_id": str(seed.get("model_candidate_id") or seed.get("model_id") or f"synthetic_model_{number:03d}"),
        "exact_url": url,
        "title": str(seed.get("title") or seed.get("model_id") or ""),
        "publisher": str(seed.get("publisher") or ""),
        "last_modified": str(seed.get("last_modified") or ""),
        "pipeline_tag": str(seed.get("pipeline_tag") or ""),
        "discovery_provider": str(seed.get("discovery_provider") or "seeded_model_metadata"),
        "discovery_query": str(seed.get("discovery_query") or ""),
        "identity_binding": _identity_binding(target),
        "voice_identity_type": identity_type,
        "claims_target_performer_or_character_voice": claims_target,
        "matched_target_identity_labels": matched_identity_labels,
        "license": {
            "license_id": license_id,
            "license_url": str(seed.get("license_url") or ""),
            "model_code_or_weights_license_known": license_id in OPEN_MODEL_LICENSES,
            "voice_or_dataset_rights_documented": bool(seed.get("voice_or_dataset_rights_documented")),
            "identity_authorization_documented": bool(seed.get("identity_authorization_documented")),
            "review_note": "An open model-code/weights license is not proof that a named voice, dataset, character, or performer likeness is authorized.",
        },
        "artifact_state": {"metadata_only": True, "model_downloaded": False, "voice_generated": False},
        "eligibility": {
            "eligible_for_technical_license_review": license_id in OPEN_MODEL_LICENSES,
            "eligible_for_candidate_voice_now": False,
            "blocked_reasons": blockers or ["human model-card, voice identity, quality, and candidate listening review still required"],
            "official_voice_claim_allowed": False,
        },
    }


def _deduplicate(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        try:
            url = canonical_url(str(item.get("url") or ""))
        except ValueError:
            continue
        if not url or url in seen:
            continue
        seen.add(url)
        normalized = deepcopy(item)
        normalized["url"] = url
        result.append(normalized)
    return result


def _factor_value(factors: dict[str, Any], key: str) -> tuple[Any, list[str], str]:
    item = factors.get(key) if isinstance(factors.get(key), dict) else {}
    return item.get("value"), list(item.get("evidence_urls") or []), str(item.get("confidence") or "unknown")


def _has_value(value: Any) -> bool:
    return value is not None and value != "" and value != []


def build_historical_voice_lane(request: dict[str, Any], recordings: list[dict[str, Any]]) -> dict[str, Any]:
    target = request.get("identity_target", {})
    if target.get("subject_kind") != "historical_person":
        return {"applicable": False}
    verified = [
        item
        for item in recordings
        if item.get("speaker_identity_verification", {}).get("status") == "verified_historical_subject"
        and item.get("recording_authenticity_status") == "verified_original_recording"
    ]
    factors = request.get("historical_voice_factors") if isinstance(request.get("historical_voice_factors"), dict) else {}
    factor_cards = []
    for key in (
        "anchor_date_or_era",
        "chronological_age_or_band",
        "places_and_regions",
        "education_and_profession",
        "languages_and_dialects",
        "documented_health_or_voice_notes",
    ):
        value, urls, confidence = _factor_value(factors, key)
        factor_cards.append({"factor": key, "value": value, "evidence_urls": urls, "confidence": confidence})
    if verified:
        return {
            "applicable": True,
            "status": "verified_recording_candidates_found_but_not_ingested_or_model_ready",
            "verified_recording_source_ids": [item["source_id"] for item in verified],
            "use_rule": "Use only after recording rights, clean target-only segments, technical suitability, and review are all approved.",
            "speculative_design_needed": False,
            "authentic_voice_claim_allowed_now": False,
        }

    available = {card["factor"]: card["value"] for card in factor_cards if _has_value(card["value"])}
    return {
        "applicable": True,
        "status": "speculative_educational_voice_design_only_no_verified_recording_indexed",
        "verified_recording_source_ids": [],
        "verified_recording_available": False,
        "recording_evidence": [],
        "factors": factor_cards,
        "design": {
            "required_label": "speculative educational reconstruction; not the historical person's authentic voice",
            "base_voice_requirement": "Choose a licensed generic synthetic voice with no known-person identity claim.",
            "age_presentation": available.get("chronological_age_or_band", "adult range unresolved from current evidence"),
            "era_pronunciation_brief": available.get("anchor_date_or_era", "era research still required"),
            "regional_pronunciation_brief": available.get("places_and_regions", "region research still required"),
            "register_brief": available.get("education_and_profession", "education/profession research still required"),
            "language_brief": available.get("languages_and_dialects", "language research still required"),
            "documented_voice_or_health_constraints": available.get("documented_health_or_voice_notes", []),
            "uninferred_traits": [
                "exact biometric timbre",
                "exact pitch",
                "exact cadence",
                "exact accent",
                "medical or psychological voice traits",
            ],
            "artistic_defaults_must_be_labeled": True,
            "confidence": "low_until_factor_sources_are_reviewed",
            "voice_generated": False,
        },
        "authentic_voice_claim_allowed_now": False,
    }


def _recommended_lane(request: dict[str, Any], historical: dict[str, Any]) -> str:
    target = request.get("identity_target", {})
    kind = str(target.get("subject_kind") or "")
    performer = target.get("performer", {}) if isinstance(target.get("performer"), dict) else {}
    living = str(performer.get("living_status") or "").startswith("living") or "treat_as_living" in str(performer.get("living_status") or "")
    consent = str(performer.get("consent_status") or "not_found")
    if kind == "historical_person":
        if historical.get("verified_recording_available") is False:
            return "speculative_educational_voice_design_from_reviewed_factors"
        return "verified_historical_recording_review_lane"
    if kind == "fictional_character" and living and consent not in VERIFIED_CONSENT:
        return "licensed_original_non_imitative_character_voice"
    if kind in {"generated_original", "memory_relative"}:
        return "licensed_generic_or_original_synthetic_voice_selection"
    return "review_required_before_voice_assignment"


def run_voice_discovery(
    request: dict[str, Any],
    *,
    metadata_search: bool = False,
    video_search: Callable[[str, int], list[dict[str, Any]]] = search_video_metadata,
    direct_video_metadata: Callable[[str], dict[str, Any]] = fetch_video_metadata,
    archive_search: Callable[[str, int], list[dict[str, Any]]] = search_archive_metadata,
    model_search: Callable[[str, int], list[dict[str, Any]]] = search_huggingface_model_metadata,
) -> dict[str, Any]:
    """Run discovery using metadata providers, never media/model payload providers."""
    validate_request(request)
    target = deepcopy(request["identity_target"])
    discovery = request.get("discovery", {})
    limit = max(1, min(int(discovery.get("max_results_per_query", 5) or 5), 20))
    raw_recordings = list(deepcopy(request.get("seed_recordings", [])))
    raw_models = list(deepcopy(request.get("seed_synthetic_models", [])))
    errors: list[dict[str, str]] = []
    provider_skips: list[dict[str, str]] = []

    if metadata_search:
        seeded_urls = {canonical_url(str(item.get("url") or "")) for item in raw_recordings if item.get("url")}
        for url in sorted(seeded_urls):
            if not direct_video_metadata_allowed(url):
                provider_skips.append(
                    {
                        "provider": "direct_video_metadata",
                        "query_or_url": url,
                        "reason": "Host is not on the direct-metadata allowlist; seeded metadata remains indexed without a network fetch.",
                    }
                )
                continue
            try:
                metadata = direct_video_metadata(url)
                existing = next(item for item in raw_recordings if canonical_url(str(item.get("url") or "")) == url)
                for key, value in metadata.items():
                    if _has_value(value) and key not in {"url"}:
                        existing.setdefault(key, value)
            except Exception as exc:  # network/provider failure is recorded, not fatal
                errors.append({"provider": "direct_video_metadata", "query_or_url": url, "error": str(exc)[:500]})
        for query in discovery.get("recording_queries", []):
            try:
                raw_recordings.extend(video_search(str(query), limit))
            except Exception as exc:
                errors.append({"provider": "video_metadata_search", "query_or_url": str(query), "error": str(exc)[:500]})
        for query in discovery.get("archive_queries", []):
            try:
                raw_recordings.extend(archive_search(str(query), limit))
            except Exception as exc:
                errors.append({"provider": "archive_metadata_search", "query_or_url": str(query), "error": str(exc)[:500]})
        for query in discovery.get("synthetic_model_queries", []):
            try:
                raw_models.extend(model_search(str(query), limit))
            except Exception as exc:
                errors.append({"provider": "synthetic_model_metadata_search", "query_or_url": str(query), "error": str(exc)[:500]})

    registry = [
        deepcopy(item)
        for item in request.get("source_authority_registry", [])
        if isinstance(item, dict)
    ]
    normalized_recordings = [
        _apply_source_authority_registry(item, registry)
        for item in _deduplicate(raw_recordings)
    ]
    recordings = [
        _recording_candidate(item, target, index)
        for index, item in enumerate(normalized_recordings, 1)
    ]
    recordings.sort(
        key=lambda item: (
            -int(item.get("review_ranking", {}).get("score", 0) or 0),
            str(item.get("source_id") or ""),
        )
    )
    for rank, item in enumerate(recordings, 1):
        item["review_ranking"]["rank"] = rank
    models = [_model_candidate(item, target, index) for index, item in enumerate(_deduplicate(raw_models), 1)]
    local_source_review = build_local_voice_source_review_manifest(request)
    historical = build_historical_voice_lane(request, recordings)
    lane = _recommended_lane(request, historical)
    return {
        "schema_version": 1,
        "index_id": f"{request['candidate_id']}_voice_discovery_index_v1",
        "created_at": now_iso(),
        "candidate_id": request["candidate_id"],
        "status": "metadata_search_partial" if errors and metadata_search else "metadata_search_complete" if metadata_search else "seed_and_plan_index_complete_offline",
        "request_id": request.get("request_id", ""),
        "request_sha256": json_sha256(request),
        "identity_target": target,
        "identity_rule": "Character, variant, speaker, and performer are separate records. A shared performer never merges character speakers.",
        "recording_candidates": recordings,
        "ranked_recording_review_queue": [
            {
                "rank": item["review_ranking"]["rank"],
                "source_id": item["source_id"],
                "score": item["review_ranking"]["score"],
                "band": item["review_ranking"]["band"],
                "exact_url": item["exact_url"],
                "title": item["title"],
            }
            for item in recordings
        ],
        "local_source_review_manifest": local_source_review,
        "synthetic_model_candidates": models,
        "historical_person_lane": historical,
        "selection": {
            "recommended_lane": lane,
            "voice_assigned": False,
            "voice_generated": False,
            "voice_model_built_or_downloaded": False,
            "official_voice_claim_allowed": False,
            "activation_allowed": False,
            "human_review_required": True,
        },
        "readiness_gates": {
            "metadata_discovery_completed": bool(metadata_search or raw_recordings),
            "ranked_recording_leads_found": bool(recordings),
            "local_source_leads_audited": bool(local_source_review.get("sources")),
            "local_clean_range_review_pending": any(
                item.get("clean_range_review", {}).get("status")
                == "needs_exact_bounded_ranges_and_human_audiovisual_review"
                for item in local_source_review.get("sources", [])
            ),
            "exact_continuity_and_performer_binding_complete": any(
                item.get("identity_evidence_gate", {}).get("passed") is True
                for item in recordings
            ),
            "target_only_speaker_segments_approved": False,
            "technical_quality_passed": False,
            "voice_use_rights_and_consent_passed": False,
            "voice_reference_ready": False,
            "voice_assignment_ready": False,
            "voice_runtime_ready": False,
            "temporary_ai_activation_ready": False,
        },
        "provider_errors": errors,
        "provider_skips": provider_skips,
        "operation_evidence": {
            "metadata_only": True,
            "media_download_attempted": False,
            "audio_extraction_attempted": False,
            "model_download_attempted": False,
            "voice_clone_attempted": False,
            "speech_generation_attempted": False,
            "candidate_activation_attempted": False,
            "local_audio_played": False,
            "local_audio_extracted": False,
            "local_diarization_run": False,
        },
        "next_steps": [
            "Review exact source URLs, speaker/variant labels, performer credits, and rights evidence.",
            "For living performers, obtain explicit performer consent and recording/model rights before any exact-voice model path.",
            "For an authorized recording, use the separate clip extraction, diarization-as-review-aid, and human target-speaker approval workflow.",
            "For a blocked fictional-character reconstruction, audition licensed original voices for a non-imitative character design.",
            "Never label a generated result official, authentic, or the performer's voice without matching authority evidence.",
        ],
    }


def run_candidate_discovery(candidate_id: str, *, metadata_search: bool = False) -> tuple[Path, dict[str, Any]]:
    request_path, request = load_or_create_request(candidate_id)
    result = run_voice_discovery(request, metadata_search=metadata_search)
    output = request_path.parent / INDEX_FILENAME
    write_json(output, result)
    return output, result
