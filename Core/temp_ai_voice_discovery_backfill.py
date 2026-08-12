"""Safe backfill planning for current TemporaryAI voice discovery requests.

This module only creates the metadata-discovery request that already belongs to
the no-download discovery stage.  It cannot search providers, read media
payloads, extract audio, prepare a model, assign a voice, or activate a person.

The separate project-private authorization record validated here is a future
stage permission.  It is deliberately conditional on a human-confirmed,
target-only character/variant/speaker clip and does not itself perform or
authorize any public/official claim.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from Core.temp_ai_voice_discovery import (
    REQUEST_FILENAME,
    build_candidate_voice_discovery_request,
    read_json,
    slug,
    validate_request,
)


PROFILE_FILENAME = "temporary_ai_profile.json"
CREATION_FILENAME = "creation_request.json"
AUTHORIZATION_SCHEMA_VERSION = 1
AUTHORIZATION_STATUS = (
    "project_private_future_stage_authorization_recorded_no_operation_performed"
)
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]{0,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def discover_profile_candidates(candidate_root: Path) -> tuple[list[Path], list[dict[str, str]]]:
    """Return real profile folders and excluded non-profile artifact folders."""
    root = candidate_root.resolve()
    candidates: list[Path] = []
    excluded: list[dict[str, str]] = []
    if not root.is_dir():
        raise FileNotFoundError(f"TemporaryAI candidate root does not exist: {root}")
    for directory in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        if not directory.is_dir() or directory.is_symlink():
            continue
        if slug(directory.name) != directory.name:
            excluded.append(
                {"candidate_id": directory.name, "reason": "invalid_candidate_directory_name"}
            )
            continue
        profile = directory / PROFILE_FILENAME
        if not profile.is_file() or profile.is_symlink():
            excluded.append(
                {"candidate_id": directory.name, "reason": "no_temporary_ai_profile"}
            )
            continue
        candidates.append(directory)
    return candidates, excluded


def discovery_stage_boundary_proof(request: Mapping[str, Any]) -> dict[str, Any]:
    discovery = _mapping(request.get("discovery"))
    policy = _mapping(request.get("policy"))
    passed = all(
        (
            discovery.get("metadata_only") is True,
            discovery.get("allow_media_download") is False,
            discovery.get("allow_audio_extraction") is False,
            discovery.get("allow_model_download") is False,
            policy.get("activation_allowed") is False,
        )
    )
    separate_lane_exists = Path(__file__).with_name("temp_ai_local_media_intake.py").is_file()
    return {
        "passed": passed,
        "scope": "temporary_ai_voice_metadata_discovery_stage_only",
        "metadata_only": discovery.get("metadata_only") is True,
        "media_download_allowed": discovery.get("allow_media_download") is True,
        "audio_extraction_allowed": discovery.get("allow_audio_extraction") is True,
        "model_download_allowed": discovery.get("allow_model_download") is True,
        "activation_allowed": policy.get("activation_allowed") is True,
        "separate_private_local_stage_declared": (
            policy.get("separate_private_local_bounded_intake_supported") is True
            or separate_lane_exists
        ),
        # The request is validated by the discovery module and therefore governs
        # only discovery.  Older hand-authored requests need not be rewritten to
        # gain the separate local-media stage added later.
        "not_a_blanket_ban": separate_lane_exists,
        "proof_source": (
            "Core.temp_ai_voice_discovery metadata-only contract plus the separate "
            "Core.temp_ai_local_media_intake lane"
        ),
    }


def identity_and_source_blockers(request: Mapping[str, Any]) -> list[str]:
    """Report blanks that must be reviewed before exact-voice preparation."""
    target = _mapping(request.get("identity_target"))
    discovery = _mapping(request.get("discovery"))
    performer = _mapping(target.get("performer"))
    subject_kind = _text(target.get("subject_kind"))
    blockers: list[str] = []

    if not _text(target.get("version_or_timepoint")):
        blockers.append("version_or_timepoint_blank")
    variant = _mapping(target.get("variant"))
    if subject_kind == "fictional_character" and (
        not _text(variant.get("label"))
        or _text(variant.get("variant_id")) == "base_version_review_required"
    ):
        blockers.append("fictional_variant_blank_or_unresolved")
    if subject_kind == "fictional_character" and (
        not _text(performer.get("name"))
        or _text(performer.get("performer_id")) in {"", "unknown_review_required"}
    ):
        blockers.append("performer_blank_or_unresolved")

    recordings = request.get("seed_recordings")
    has_seed = isinstance(recordings, list) and any(isinstance(item, Mapping) for item in recordings)
    recording_queries = discovery.get("recording_queries")
    archive_queries = discovery.get("archive_queries")
    has_source_query = (
        isinstance(recording_queries, list) and any(_text(item) for item in recording_queries)
    ) or (isinstance(archive_queries, list) and any(_text(item) for item in archive_queries))
    if subject_kind in {"fictional_character", "historical_person"} and not has_seed:
        blockers.append("human_confirmed_target_only_recording_source_missing")
    if subject_kind in {"fictional_character", "historical_person"} and not has_source_query:
        blockers.append("recording_metadata_query_blank")
    if subject_kind == "unknown_review_required" and not has_seed and not has_source_query:
        blockers.append("voice_source_lane_unclassified")
    return blockers


def _request_from_candidate(directory: Path) -> dict[str, Any]:
    profile = read_json(directory / PROFILE_FILENAME, {})
    creation = read_json(directory / CREATION_FILENAME, {})
    if not isinstance(profile, dict):
        raise ValueError("temporary_ai_profile.json must be a JSON object")
    if not isinstance(creation, dict):
        creation = {}
    # The existing folder name is the request storage authority.  Preserve a
    # mismatching profile for human repair, but do not let the mismatch either
    # omit the candidate or write a request for a different identifier.
    profile = dict(profile)
    creation = dict(creation)
    profile["candidate_id"] = directory.name
    creation["candidate_id"] = directory.name
    request = build_candidate_voice_discovery_request(profile, creation)
    validate_request(request, expected_candidate_id=directory.name)
    return request


def plan_voice_discovery_backfill(candidate_root: Path) -> dict[str, Any]:
    candidates, excluded = discover_profile_candidates(candidate_root)
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for directory in candidates:
        request_path = directory / REQUEST_FILENAME
        action = "preserve_existing"
        try:
            profile_data = read_json(directory / PROFILE_FILENAME, {})
            profile_identity_blockers: list[str] = []
            if _text(_mapping(profile_data).get("candidate_id")) != directory.name:
                profile_identity_blockers.append("profile_candidate_id_mismatch_with_folder")
            if request_path.exists():
                if request_path.is_symlink() or not request_path.is_file():
                    raise ValueError("existing voice discovery request is not a regular file")
                request = read_json(request_path, {})
                validate_request(request, expected_candidate_id=directory.name)
            else:
                request = _request_from_candidate(directory)
                action = "create_missing"
            proof = discovery_stage_boundary_proof(request)
            if not proof["passed"]:
                raise ValueError("voice discovery request does not preserve the no-download stage")
            rows.append(
                {
                    "candidate_id": directory.name,
                    "action": action,
                    "request_path": request_path,
                    "request": request,
                    "blockers": list(
                        dict.fromkeys(
                            [*profile_identity_blockers, *identity_and_source_blockers(request)]
                        )
                    ),
                    "stage_boundary": proof,
                }
            )
        except Exception as exc:
            errors.append({"candidate_id": directory.name, "error": str(exc)[:500]})
    return {
        "profile_candidate_count": len(candidates),
        "excluded": excluded,
        "rows": rows,
        "errors": errors,
    }


def apply_voice_discovery_backfill(candidate_root: Path) -> dict[str, Any]:
    """Exclusively create missing requests; an existing request is never rewritten."""
    plan = plan_voice_discovery_backfill(candidate_root)
    created: list[str] = []
    preserved: list[str] = []
    errors = list(plan["errors"])
    for row in plan["rows"]:
        candidate_id = row["candidate_id"]
        request_path = row["request_path"]
        if row["action"] == "preserve_existing":
            preserved.append(candidate_id)
            continue
        payload = json.dumps(row["request"], indent=2, ensure_ascii=False) + "\n"
        try:
            request_path.parent.mkdir(parents=True, exist_ok=True)
            with request_path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
            persisted = read_json(request_path, {})
            validate_request(persisted, expected_candidate_id=candidate_id)
            if not discovery_stage_boundary_proof(persisted)["passed"]:
                raise ValueError("persisted request failed stage-boundary proof")
            created.append(candidate_id)
        except FileExistsError:
            # A concurrent creator won.  Validate it, but never replace it.
            try:
                existing = read_json(request_path, {})
                validate_request(existing, expected_candidate_id=candidate_id)
                preserved.append(candidate_id)
            except Exception as exc:
                errors.append({"candidate_id": candidate_id, "error": str(exc)[:500]})
        except Exception as exc:
            errors.append({"candidate_id": candidate_id, "error": str(exc)[:500]})

    post = plan_voice_discovery_backfill(candidate_root)
    blocker_rows = [
        {"candidate_id": row["candidate_id"], "blockers": row["blockers"]}
        for row in post["rows"]
        if row["blockers"]
    ]
    return {
        "status": "backfill_complete" if not errors and not post["errors"] else "backfill_complete_with_errors",
        "profile_candidate_count": post["profile_candidate_count"],
        "created_candidate_ids": created,
        "preserved_candidate_ids": sorted(set(preserved)),
        "excluded": post["excluded"],
        "blank_identity_or_source_blockers": blocker_rows,
        "all_requests_stage_boundary_passed": (
            not post["errors"]
            and len(post["rows"]) == post["profile_candidate_count"]
            and all(row["stage_boundary"]["passed"] for row in post["rows"])
        ),
        "discovery_no_download_is_stage_scoped": all(
            row["stage_boundary"]["not_a_blanket_ban"] for row in post["rows"]
        ),
        "operations_performed": {
            "metadata_requests_created": len(created),
            "metadata_provider_searches": 0,
            "media_downloads": 0,
            "audio_extractions": 0,
            "voice_models_prepared_or_trained": 0,
            "voices_assigned": 0,
            "candidates_activated": 0,
        },
        "errors": [*errors, *post["errors"]],
    }


def validate_private_exact_voice_authorization(record: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    if record.get("schema_version") != AUTHORIZATION_SCHEMA_VERSION:
        failures.append("schema_version_must_be_1")
    if not SAFE_ID_RE.fullmatch(_text(record.get("authorization_id"))):
        failures.append("authorization_id_invalid")
    if _text(record.get("status")) != AUTHORIZATION_STATUS:
        failures.append("authorization_status_invalid")
    owner = _mapping(record.get("authorized_by"))
    if _text(owner.get("name")) != "Robert McMurrer" or owner.get("project_owner") is not True:
        failures.append("project_owner_identity_not_bound")
    if _text(record.get("visibility")) != "project_private":
        failures.append("authorization_must_remain_project_private")

    scope = _mapping(record.get("future_scope"))
    required_scope = (
        scope.get("exact_voice_model_preparation_allowed_later") is True,
        scope.get("private_candidate_voice_assignment_allowed_later") is True,
        scope.get("public_release_allowed") is False,
        scope.get("official_voice_claim_allowed") is False,
    )
    if not all(required_scope):
        failures.append("future_scope_is_not_private_and_bounded")
    conditions = _mapping(record.get("required_clip_conditions"))
    for key in (
        "human_confirmed_target_only",
        "character_id_confirmed",
        "variant_id_confirmed",
        "speaker_id_confirmed",
        "performer_id_confirmed_when_applicable",
        "mixed_or_overlapping_speakers_rejected",
        "source_and_artifact_hashes_bound",
    ):
        if conditions.get(key) is not True:
            failures.append(f"required_clip_condition_missing:{key}")

    now = _mapping(record.get("operations_now"))
    for key in (
        "download_media",
        "extract_audio",
        "clone_or_train_voice",
        "prepare_voice_model",
        "assign_voice",
        "activate_candidate",
        "publish_or_claim_official",
    ):
        if now.get(key) is not False:
            failures.append(f"operation_now_must_be_false:{key}")
    boundaries = _mapping(record.get("stage_boundaries"))
    if boundaries.get("metadata_discovery_remains_no_download") is not True:
        failures.append("metadata_discovery_stage_boundary_missing")
    if boundaries.get("private_local_intake_is_separate") is not True:
        failures.append("private_local_intake_separation_missing")
    if boundaries.get("authorization_record_executes_no_operation") is not True:
        failures.append("authorization_must_execute_no_operation")
    return failures


def authorization_summary(record_path: Path) -> dict[str, Any]:
    record = read_json(record_path, {})
    failures = validate_private_exact_voice_authorization(record)
    return {
        "path": record_path.as_posix(),
        "sha256": sha256_file(record_path) if record_path.is_file() else "",
        "valid": not failures,
        "failures": failures,
        "status": _text(_mapping(record).get("status")),
        "operation_performed": False,
    }
