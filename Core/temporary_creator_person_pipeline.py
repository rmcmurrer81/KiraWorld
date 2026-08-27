"""Fail-closed work-order bridge for the existing Temporary Creator.

One authenticated founder/permanent-person command may prepare the *draft*
pipeline.  The command creates one shared person ID and deterministic,
hash-bound work orders for mind/knowledge research, Avatar Builder, voice, and
Kira World residency.  It never claims that any of those outputs exist.

The creator exposes exactly three kinds: ``expert``, ``fictional``, and
``historical``.  Fictional and historical voices always begin with the existing
identity-matched metadata/video discovery contract.  A reconstructed voice is
planned only after a bound evidence record says no usable recording was found;
that lane is permanently labelled non-authentic.

V4 static evidence remains a separate signed gate.  Draft discovery orders may
be queued by the authenticated command, but material generation and residency
remain blocked until their evidence gates pass.  Creation can never activate a
person or grant permanent promotion.
"""

from __future__ import annotations

from copy import deepcopy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping

from Core.avatar_builder_orchestration import evaluate_avatar_builder_orchestration
from Core.temp_ai_voice_discovery import (
    build_candidate_voice_discovery_request,
    validate_request as validate_voice_discovery_request,
)
from Core.temporary_person_request import build_request as build_temporary_person_request
from Core import temporary_ai_creator_quality_v4 as quality_v4


SCHEMA_VERSION = 1
PIPELINE_KIND = "temporary_creator_person_pipeline_v1"
MANIFEST_KIND = "temporary_creator_shared_person_manifest_v1"
MIND_ORDER_KIND = "temporary_creator_mind_knowledge_work_order_v1"
AVATAR_ORDER_KIND = "temporary_creator_avatar_builder_work_order_v1"
VOICE_ORDER_KIND = "temporary_creator_voice_generator_work_order_v1"
RESIDENCY_ORDER_KIND = "temporary_creator_kira_world_residency_work_order_v1"
READINESS_KIND = "temporary_creator_shared_person_readiness_v1"
VOICE_SOURCE_REVIEW_KIND = "temporary_creator_voice_source_evidence_review_v1"

ALLOWED_CREATOR_TYPES = frozenset({"expert", "fictional", "historical"})
ALLOWED_AUTHORITY_CLASSES = frozenset({"founder", "permanent_person"})
ALLOWED_STAGE_STATUSES = frozenset({"draft", "queued", "blocked", "ready"})
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]{2,79}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

TYPE_CONFIG = {
    "expert": {
        "request_type": "expert",
        "ui_category": "Expert",
        "ai_type": "expert_temp_ai",
        "identity_mode": "original_expert",
    },
    "fictional": {
        "request_type": "fictional_character",
        "ui_category": "Fictional Character",
        "ai_type": "canon_reconstruction_temp_ai",
        "identity_mode": "source_bounded_fictional_reconstruction",
    },
    "historical": {
        "request_type": "historical_person",
        "ui_category": "Historical Person",
        "ai_type": "historical_temp_ai",
        "identity_mode": "source_bounded_historical_reconstruction",
    },
}

WORKSPACE_RELATIVE_ROOT = Path("TemporaryAI") / "creator_work_orders"

EXPERT_STABLE_VOICE_PROFILES = {
    "neutral": {
        "profile_id": "stable_neutral_narrator_v1",
        "voice_presentation": "neutral",
    },
    "masculine": {
        "profile_id": "stable_warm_male_v1",
        "voice_presentation": "masculine",
    },
    "feminine": {
        "profile_id": "stable_calm_female_v1",
        "voice_presentation": "feminine",
    },
}


class TemporaryCreatorPipelineError(ValueError):
    """A creator input, evidence binding, or workspace boundary failed."""


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TemporaryCreatorPipelineError("value_is_not_canonical_json") from exc


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _expert_stable_voice_profile(gender_preference: object) -> dict[str, str]:
    """Select a static original profile without claiming synthesis or assignment."""

    value = _text(gender_preference).casefold()
    tokens = set(re.findall(r"[a-z]+", value))
    if tokens & {"female", "feminine", "woman", "girl"}:
        presentation = "feminine"
    elif tokens & {"male", "masculine", "man", "boy"}:
        presentation = "masculine"
    else:
        presentation = "neutral"
    selected = EXPERT_STABLE_VOICE_PROFILES[presentation]
    return {
        **selected,
        "catalog_id": "stable_original_voice_profiles_v1",
        "selection_basis": "gender_preference_or_neutral_default",
        "current_truth": "static_style_recommendation_only_unsynthesized",
    }


def _slug(value: object, *, limit: int = 60) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _text(value).casefold()).strip("_")[:limit]


def _canonical_id(value: object, label: str) -> str:
    result = _text(value).casefold()
    if ID_RE.fullmatch(result) is None:
        raise TemporaryCreatorPipelineError(f"{label}_must_be_canonical_id")
    return result


def _canonical_utc(value: object, label: str) -> str:
    result = _text(value)
    if UTC_RE.fullmatch(result) is None:
        raise TemporaryCreatorPipelineError(f"{label}_must_be_second_precision_utc_z")
    try:
        dt.datetime.fromisoformat(result[:-1] + "+00:00")
    except ValueError as exc:
        raise TemporaryCreatorPipelineError(f"{label}_invalid") from exc
    return result


def _canonical_relative(value: object, label: str) -> str:
    raw = _text(value).replace("\\", "/")
    pure = PurePosixPath(raw)
    if (
        not raw
        or pure.is_absolute()
        or raw != pure.as_posix()
        or any(part in {"", ".", ".."} for part in pure.parts)
        or ":" in pure.parts[0]
    ):
        raise TemporaryCreatorPipelineError(f"{label}_must_be_canonical_relative_path")
    return raw


def _within(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
        return True
    except ValueError:
        return False


def _reject_symlink_components(path: Path, stop: Path) -> None:
    current = path
    while True:
        if current.exists() and current.is_symlink():
            raise TemporaryCreatorPipelineError("symlink_or_reparse_workspace_component")
        if current == stop or current == current.parent:
            break
        current = current.parent


def _safe_workspace(
    execution_root: Path, workspace: Path, person_id: str
) -> tuple[Path, Path]:
    root = Path(execution_root).resolve()
    if not root.is_dir():
        raise TemporaryCreatorPipelineError("execution_root_missing")
    raw = Path(workspace)
    requested = (raw if raw.is_absolute() else root / raw).resolve()
    allowed = (root / WORKSPACE_RELATIVE_ROOT).resolve()
    if requested == allowed:
        target = (allowed / person_id).resolve()
    elif requested.parent == allowed and requested.name.casefold() == person_id.casefold():
        target = requested
    else:
        raise TemporaryCreatorPipelineError("workspace_outside_creator_work_order_root")
    if not _within(target, allowed) or target == allowed:
        raise TemporaryCreatorPipelineError("workspace_outside_creator_work_order_root")
    _reject_symlink_components(target, root)
    target.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(target, root)
    return root, target


def _safe_bound_file(
    execution_root: Path,
    relative: object,
    expected_sha256: object,
    *,
    canonical_json_required: bool = False,
) -> tuple[str, Path, dict[str, Any], str]:
    rel = _canonical_relative(relative, "evidence_relative")
    expected = _text(expected_sha256).casefold()
    if SHA256_RE.fullmatch(expected) is None:
        raise TemporaryCreatorPipelineError("evidence_sha256_invalid")
    root = Path(execution_root).resolve()
    path = (root / Path(*PurePosixPath(rel).parts)).resolve(strict=True)
    if not _within(path, root) or path.is_symlink() or not path.is_file():
        raise TemporaryCreatorPipelineError("evidence_file_outside_root_or_not_regular")
    _reject_symlink_components(path, root)
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise TemporaryCreatorPipelineError("evidence_sha256_mismatch")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise TemporaryCreatorPipelineError("evidence_json_invalid") from exc
    if not isinstance(value, dict):
        raise TemporaryCreatorPipelineError("evidence_json_root_not_object")
    if canonical_json_required and raw not in {
        canonical_json_bytes(value),
        quality_v4.canonical_json_bytes(value),
    }:
        raise TemporaryCreatorPipelineError("evidence_json_not_canonical")
    return rel, path, value, actual


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False
    ).encode("utf-8") + b"\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return hashlib.sha256(raw).hexdigest()


def _status(status: str, *, blockers: list[str] | None = None, **extra: Any) -> dict[str, Any]:
    if status not in ALLOWED_STAGE_STATUSES:
        raise TemporaryCreatorPipelineError("internal_stage_status_invalid")
    return {"status": status, "blockers": list(blockers or []), **extra}


def _normalize_candidate(candidate_data: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(candidate_data, Mapping):
        return {}, ["candidate_data_must_be_object"]
    creator_type = _text(candidate_data.get("creator_type")).casefold()
    blockers: list[str] = []
    if creator_type not in ALLOWED_CREATOR_TYPES:
        blockers.append("creator_type_must_be_expert_fictional_or_historical")
    subject = _text(candidate_data.get("subject_or_domain"))
    display_name = _text(candidate_data.get("display_name")) or subject
    default_roles = {
        "expert": f"{subject} expert" if subject else "expert",
        "fictional": "fictional character",
        "historical": "historical person",
    }
    role_title = _text(candidate_data.get("role_title")) or default_roles.get(
        creator_type, "temporary person"
    )
    version = _text(candidate_data.get("version_or_timepoint"))
    gender = _text(candidate_data.get("gender_preference")) or "Doesn't matter"
    personality = _text(candidate_data.get("personality_notes")) or (
        "Natural, source-bounded, and honest about uncertainty."
    )
    if not subject:
        blockers.append("subject_or_domain_missing")
    if not personality:
        blockers.append("personality_notes_missing")

    availability_supplied = isinstance(candidate_data.get("availability"), Mapping)
    availability_raw = candidate_data.get("availability")
    availability_raw = availability_raw if isinstance(availability_raw, Mapping) else {}
    availability: dict[str, bool] = {}
    for actor in ("kira", "lisa"):
        default_value = actor == "kira"
        value = availability_raw.get(actor, default_value)
        if not isinstance(value, bool):
            blockers.append(f"availability_{actor}_must_be_boolean_when_supplied")
            value = default_value
        availability[actor] = value

    auth_raw = candidate_data.get("requested_by")
    auth_raw = auth_raw if isinstance(auth_raw, Mapping) else {}
    requester_id = _text(auth_raw.get("person_id")).casefold()
    if ID_RE.fullmatch(requester_id) is None:
        blockers.append("authenticated_requester_id_missing_or_invalid")
    authority_class = _text(auth_raw.get("authority_class")).casefold()
    if authority_class not in ALLOWED_AUTHORITY_CLASSES:
        blockers.append("requester_must_be_founder_or_permanent_person")
    if auth_raw.get("authorized") is not True or auth_raw.get("authenticated") is not True:
        blockers.append("single_creator_command_not_authenticated_and_authorized")
    command_text = _text(auth_raw.get("command_text"))
    if not command_text:
        blockers.append("creator_command_text_missing")

    normalized = {
        "creator_type": creator_type,
        "display_name": display_name,
        "role_title": role_title,
        "subject_or_domain": subject,
        "version_or_timepoint": version,
        "gender_preference": gender,
        "personality_notes": personality,
        "availability": availability,
        "requested_by": {
            "person_id": requester_id,
            "authority_class": authority_class,
            "authenticated": auth_raw.get("authenticated") is True,
            "authorized": auth_raw.get("authorized") is True,
            "command_text": command_text,
            "command_sha256": hashlib.sha256(command_text.encode("utf-8")).hexdigest(),
        },
        "autonomous_defaults": {
            "display_name_from_subject": not bool(_text(candidate_data.get("display_name"))),
            "role_title_from_creator_type": not bool(_text(candidate_data.get("role_title"))),
            "personality_source_bounded_default": not bool(
                _text(candidate_data.get("personality_notes"))
            ),
            "availability_defaulted": not availability_supplied,
            "routine_questions_required": False,
            "question_only_if_material_identity_ambiguity": True,
        },
    }
    identity_hash = canonical_sha256(normalized)
    explicit_person_id = _text(
        candidate_data.get("person_id") or candidate_data.get("candidate_id")
    ).casefold()
    if explicit_person_id:
        if ID_RE.fullmatch(explicit_person_id) is None:
            blockers.append("explicit_person_id_invalid")
            person_id = ""
        else:
            person_id = explicit_person_id
    else:
        prefix = _slug(display_name) or "temporary_person"
        person_id = f"{creator_type or 'temporary'}_{prefix}_{identity_hash[:10]}"[:80]
    normalized["person_id"] = person_id
    normalized["input_sha256"] = canonical_sha256(
        {key: value for key, value in normalized.items() if key != "input_sha256"}
    )
    return normalized, list(dict.fromkeys(blockers))


def _identity_resolution(candidate: Mapping[str, Any]) -> dict[str, Any]:
    kind = candidate["creator_type"]
    version = candidate["version_or_timepoint"]
    if kind == "expert":
        return {
            "status": "ready",
            "identity_mode": "original_expert",
            "selected_life_or_canon_point": "original_person_no_source_life_point",
            "confidence": "explicit_original_design",
            "ambiguity_fail_closed": False,
        }
    if kind == "fictional":
        return {
            "status": "ready" if version else "blocked",
            "identity_mode": "source_bounded_fictional_reconstruction",
            "selected_life_or_canon_point": version,
            "confidence": "user_selected_pending_evidence" if version else "unresolved",
            "ambiguity_fail_closed": not bool(version),
            "resolution_strategy": "rank_primary_canon_and_official_continuity_sources",
        }
    if version:
        point = version
        status = "ready"
        confidence = "user_selected_pending_evidence"
    else:
        point = (
            "late life immediately before the final independently documented public-life "
            "event; exact cutoff and knowledge boundary pending ranked-source verification"
        )
        status = "queued"
        confidence = "provisional_low"
    return {
        "status": status,
        "identity_mode": "source_bounded_historical_reconstruction",
        "selected_life_or_canon_point": point,
        "confidence": confidence,
        "ambiguity_fail_closed": status != "ready",
        "resolution_strategy": "rank_primary_historical_and_authoritative_secondary_sources",
        "post_cutoff_events_are_not_autobiographical_memory": True,
    }


def _build_intake(candidate: Mapping[str, Any], created_at_utc: str) -> dict[str, Any]:
    config = TYPE_CONFIG[candidate["creator_type"]]
    details: dict[str, Any] = {
        "exact_identity": candidate["subject_or_domain"],
        "version_or_continuity": candidate["version_or_timepoint"] or "autonomous_source_resolution",
        "timeline_or_period": candidate["version_or_timepoint"] or "autonomous_source_resolution",
        "point_of_view": "source-bounded perspective; sources are evidence, not lived memory",
        "expert_domain": candidate["subject_or_domain"],
    }
    request = build_temporary_person_request(
        requested_by={
            "person_id": candidate["requested_by"]["person_id"],
            "authorized": True,
        },
        request_type=config["request_type"],
        request_text=candidate["subject_or_domain"],
        details=details,
    )
    request["request_id"] = f"request_{candidate['person_id']}"
    request["created_at"] = created_at_utc
    request["request_fingerprint"] = candidate["input_sha256"]
    request["single_authenticated_command_sha256"] = candidate["requested_by"][
        "command_sha256"
    ]
    request["per_source_owner_approval_required"] = False
    request["activation_allowed"] = False
    request["fabricated_finished_person"] = False
    return request


def _build_mind_order(
    candidate: Mapping[str, Any],
    identity: Mapping[str, Any],
    input_sha256: str,
) -> dict[str, Any]:
    kind = candidate["creator_type"]
    if kind == "expert":
        source_classes = [
            "official_domain_source",
            "authoritative_secondary",
            "current_reviewed_reference",
        ]
        memory_policy = "expert knowledge is sourced knowledge, never invented autobiography"
    elif kind == "fictional":
        source_classes = [
            "primary_canon",
            "official_rightsholder_continuity",
            "authoritative_secondary",
        ]
        memory_policy = "only selected-continuity facts through the verified cutoff may seed source memories"
    else:
        source_classes = [
            "primary_historical",
            "contemporaneous_record",
            "authoritative_secondary",
        ]
        memory_policy = "documented facts through the verified life point are source facts, not fabricated recall"
    execution_blockers = []
    if identity.get("ambiguity_fail_closed") is True:
        execution_blockers.append("identity_or_life_point_requires_evidence_resolution")
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": MIND_ORDER_KIND,
        "person_id": candidate["person_id"],
        "candidate_input_sha256": input_sha256,
        "status": "queued",
        "execution_status": "blocked" if execution_blockers else "queued",
        "execution_blockers": execution_blockers,
        "subject_or_domain": candidate["subject_or_domain"],
        "life_or_canon_point": identity["selected_life_or_canon_point"],
        "autonomous_evidence_plan": {
            "gather_and_rank_sources": True,
            "source_classes": source_classes,
            "confidence_labels_required": True,
            "claim_to_evidence_hash_binding_required": True,
            "conflicts_and_uncertainty_must_remain_visible": True,
            "identity_ambiguity_must_fail_closed": True,
            "per_source_owner_approval_required": False,
        },
        "memory_policy": memory_policy,
        "mind_or_knowledge_built": False,
        "runtime_memory_written": False,
        "activation_allowed": False,
    }


def _avatar_preflight(candidate: Mapping[str, Any], execution_root: Path) -> dict[str, Any]:
    request = {
        "schema_version": 1,
        "candidate_id": candidate["person_id"],
        "subject_id": candidate["person_id"],
        "render_requested": False,
        "runtime_activation_requested": False,
        "reusable_method_id": None,
        "maturity_policy": {"maturity_class": "", "evidence": {}},
        "source_strategy": {
            "mode": "",
            "licensed_derivative": {"selected": False},
            "photo_only": {"selected": False},
        },
        "components": {},
        "readiness_evidence": {},
        "privacy": {
            "normal_review_route": "clothed_only",
            "intimate_render_retained": False,
            "private_source_paths_in_report": False,
            "public_export_allowed": False,
        },
    }
    return evaluate_avatar_builder_orchestration(
        request, project_root=execution_root
    )


def _visual_queries(candidate: Mapping[str, Any], identity: Mapping[str, Any]) -> list[str]:
    subject = candidate["subject_or_domain"]
    point = identity["selected_life_or_canon_point"]
    if candidate["creator_type"] == "expert":
        return [
            f"original adult {candidate['role_title']} visual design references",
            f"original professional wardrobe {candidate['role_title']}",
        ]
    if candidate["creator_type"] == "fictional":
        return [
            f'"{subject}" "{point}" official character reference',
            f'"{subject}" "{point}" official full body',
            f'"{subject}" "{point}" official profile view',
        ]
    return [
        f'"{subject}" "{point}" verified archival portrait',
        f'"{subject}" "{point}" full length historical photograph',
        f'"{subject}" "{point}" profile photograph archive',
    ]


def _build_avatar_order(
    candidate: Mapping[str, Any],
    identity: Mapping[str, Any],
    *,
    v4_ready: bool,
    execution_root: Path,
    codesign_id: str,
) -> dict[str, Any]:
    identity_blocked = identity.get("ambiguity_fail_closed") is True
    blockers = []
    if not v4_ready:
        blockers.append("signed_v4_static_evidence_not_ready")
    if identity_blocked:
        blockers.append("identity_or_life_point_ambiguous")
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": AVATAR_ORDER_KIND,
        "person_id": candidate["person_id"],
        "candidate_input_sha256": candidate["input_sha256"],
        "status": "queued",
        "execution_status": "blocked" if blockers else "queued",
        "execution_blockers": blockers,
        "design_lane": (
            "original_expert_body_voice_codesign"
            if candidate["creator_type"] == "expert"
            else "identity_evidence_reconstruction"
        ),
        "body_voice_codesign_id": codesign_id if candidate["creator_type"] == "expert" else "",
        "recommended_stable_voice_profile": (
            _expert_stable_voice_profile(candidate["gender_preference"])
            if candidate["creator_type"] == "expert"
            else None
        ),
        "autonomous_visual_reference_plan": {
            "queries": _visual_queries(candidate, identity),
            "gather_online_metadata_and_reviewable_references": True,
            "rank_identity_and_life_point_match": True,
            "rank_source_authority_and_rights": True,
            "multiview_targets": ["front", "profile_or_three_quarter", "full_body"],
            "confidence_labels_required": True,
            "identity_ambiguity_must_fail_closed": True,
            "automatic_reference_is_not_owner_quality_approval": True,
        },
        "avatar_builder_api": "Core.avatar_builder_orchestration.evaluate_avatar_builder_orchestration",
        "avatar_builder_preflight": _avatar_preflight(candidate, execution_root),
        "render_or_generation_requested_by_this_orchestrator": False,
        "avatar_or_body_created": False,
        "owner_clothed_review_required_before_runtime": True,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
    }


def _profile_for_voice(candidate: Mapping[str, Any], identity: Mapping[str, Any]) -> dict[str, Any]:
    config = TYPE_CONFIG[candidate["creator_type"]]
    return {
        "candidate_id": candidate["person_id"],
        "display_name": candidate["display_name"],
        "role_title": candidate["role_title"],
        "ui_category": config["ui_category"],
        "ai_type": config["ai_type"],
        "gender_preference": candidate["gender_preference"],
        "personality_notes": candidate["personality_notes"],
        "knowledge_plan": {
            "version_or_life_point": identity["selected_life_or_canon_point"]
        },
        "activation_policy": {
            "available_to_kira_after_review": candidate["availability"]["kira"],
            "available_to_lisa_after_review": candidate["availability"]["lisa"],
            "current_status": "draft_work_orders_only",
        },
    }


def _voice_discovery(
    candidate: Mapping[str, Any], identity: Mapping[str, Any], created_at_utc: str
) -> dict[str, Any]:
    profile = _profile_for_voice(candidate, identity)
    creation = {
        "candidate_id": candidate["person_id"],
        "display_name_or_role": candidate["display_name"],
        "ui_category": TYPE_CONFIG[candidate["creator_type"]]["ui_category"],
        "ai_type": TYPE_CONFIG[candidate["creator_type"]]["ai_type"],
        "creation_type": TYPE_CONFIG[candidate["creator_type"]]["request_type"],
        "input": {
            "version_life_point_or_canon_point": identity[
                "selected_life_or_canon_point"
            ]
        },
    }
    request = build_candidate_voice_discovery_request(profile, creation)
    request["created_at"] = created_at_utc
    validate_voice_discovery_request(
        request, expected_candidate_id=candidate["person_id"]
    )
    return request


def _voice_source_review(
    execution_root: Path,
    evidence: Mapping[str, Any] | None,
    *,
    person_id: str,
    discovery_sha256: str,
) -> tuple[dict[str, Any] | None, str, list[str]]:
    if not evidence:
        return None, "", ["voice_source_identity_rights_review_not_present"]
    try:
        _rel, _path, record, evidence_sha = _safe_bound_file(
            execution_root,
            evidence.get("record_relative"),
            evidence.get("record_sha256"),
        )
        if record.get("schema_version") != 1 or record.get("record_kind") != VOICE_SOURCE_REVIEW_KIND:
            raise TemporaryCreatorPipelineError("voice_source_review_schema_invalid")
        if record.get("person_id") != person_id:
            raise TemporaryCreatorPipelineError("voice_source_review_person_mismatch")
        if record.get("discovery_request_sha256") != discovery_sha256:
            raise TemporaryCreatorPipelineError("voice_source_review_discovery_mismatch")
        if record.get("activation_allowed") is not False:
            raise TemporaryCreatorPipelineError("voice_source_review_cannot_activate")
        if record.get("source_review_complete") is not True:
            raise TemporaryCreatorPipelineError("voice_source_review_incomplete")
        outcome = record.get("outcome")
        if outcome not in {"usable_recording_approved", "no_usable_recording"}:
            raise TemporaryCreatorPipelineError("voice_source_review_outcome_invalid")
        if SHA256_RE.fullmatch(_text(record.get("search_evidence_sha256")).casefold()) is None:
            raise TemporaryCreatorPipelineError("voice_search_evidence_sha256_invalid")
        if outcome == "usable_recording_approved":
            if (
                record.get("identity_review_complete") is not True
                or record.get("rights_review_complete") is not True
                or record.get("voice_model_use_authorized") is not True
                or record.get("selected_recording_identity_bound") is not True
                or SHA256_RE.fullmatch(
                    _text(record.get("selected_recording_sha256")).casefold()
                )
                is None
            ):
                raise TemporaryCreatorPipelineError("usable_recording_gates_incomplete")
        else:
            if record.get("voice_model_use_authorized") is not False:
                raise TemporaryCreatorPipelineError("no_recording_outcome_cannot_authorize_recording_use")
            if not _text(record.get("no_usable_reason")):
                raise TemporaryCreatorPipelineError("no_usable_recording_reason_missing")
        return deepcopy(record), evidence_sha, []
    except (OSError, TemporaryCreatorPipelineError) as exc:
        return None, "", [str(exc)]


def _reconstructed_voice_order(
    candidate: Mapping[str, Any], review: Mapping[str, Any], review_sha256: str, *, v4_ready: bool
) -> dict[str, Any]:
    factors = review.get("reconstruction_factors")
    factors = factors if isinstance(factors, Mapping) else {}
    required = (
        "age_or_life_stage",
        "origin_or_region",
        "primary_language",
        "era_or_timepoint",
        "physiology_notes",
        "personality_notes",
    )
    missing = [name for name in required if not _text(factors.get(name))]
    blockers = list(missing)
    if not v4_ready:
        blockers.append("signed_v4_static_evidence_not_ready")
    return {
        "record_kind": "temporary_creator_non_authentic_reconstructed_voice_work_order_v1",
        "person_id": candidate["person_id"],
        "status": "blocked" if blockers else "queued",
        "blockers": blockers,
        "source_review_sha256": review_sha256,
        "basis": {name: _text(factors.get(name)) for name in required},
        "authenticity_label": "NON_AUTHENTIC_RECONSTRUCTED_VOICE",
        "must_not_be_called_authentic_official_or_exact": True,
        "owner_preview_review_required": True,
        "voice_generated": False,
        "voice_assigned": False,
        "activation_allowed": False,
    }


def _build_voice_order(
    candidate: Mapping[str, Any],
    identity: Mapping[str, Any],
    *,
    created_at_utc: str,
    v4_ready: bool,
    codesign_id: str,
    execution_root: Path,
    voice_source_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    discovery = _voice_discovery(candidate, identity, created_at_utc)
    discovery_sha = canonical_sha256(discovery)
    if candidate["creator_type"] == "expert":
        blockers = [] if v4_ready else ["signed_v4_static_evidence_not_ready"]
        stable_profile = _expert_stable_voice_profile(candidate["gender_preference"])
        lane = {
            "record_kind": "temporary_creator_original_expert_voice_codesign_v1",
            "body_voice_codesign_id": codesign_id,
            "status": "queued" if not blockers else "blocked",
            "blockers": blockers,
            "desired_original_traits": {
                "gender_preference": candidate["gender_preference"],
                "personality_notes": candidate["personality_notes"],
                "role_title": candidate["role_title"],
            },
            "recommended_stable_voice_profile": stable_profile,
            "named_person_imitation_requested": False,
            "owner_preview_review_required": True,
        }
        stage_status = "queued"
        stage_blockers = blockers
        source_review = None
        source_review_sha = ""
        fallback = None
    else:
        source_review, source_review_sha, review_blockers = _voice_source_review(
            execution_root,
            voice_source_evidence,
            person_id=candidate["person_id"],
            discovery_sha256=discovery_sha,
        )
        fallback = None
        lane = None
        stage_blockers = list(review_blockers)
        if not v4_ready:
            stage_blockers.append("signed_v4_static_evidence_not_ready")
        if source_review is not None:
            if source_review["outcome"] == "no_usable_recording":
                fallback = _reconstructed_voice_order(
                    candidate, source_review, source_review_sha, v4_ready=v4_ready
                )
                stage_blockers = list(fallback["blockers"])
            else:
                blockers = [] if v4_ready else ["signed_v4_static_evidence_not_ready"]
                lane = {
                    "record_kind": "temporary_creator_identity_recording_voice_work_order_v1",
                    "person_id": candidate["person_id"],
                    "status": "queued" if not blockers else "blocked",
                    "blockers": blockers,
                    "source_review_sha256": source_review_sha,
                    "selected_recording_sha256": source_review[
                        "selected_recording_sha256"
                    ],
                    "owner_preview_review_required": True,
                    "voice_generated": False,
                    "voice_assigned": False,
                }
                stage_blockers = blockers
        stage_status = "queued"
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": VOICE_ORDER_KIND,
        "person_id": candidate["person_id"],
        "candidate_input_sha256": candidate["input_sha256"],
        "status": stage_status,
        "execution_status": "blocked" if stage_blockers else "queued",
        "execution_blockers": stage_blockers,
        "online_recording_discovery_first": candidate["creator_type"] in {"fictional", "historical"},
        "voice_discovery_api": "Core.temp_ai_voice_discovery.build_candidate_voice_discovery_request",
        "discovery_request": discovery,
        "discovery_request_sha256": discovery_sha,
        "source_review_evidence_sha256": source_review_sha,
        "selected_generation_lane": lane,
        "reconstructed_voice_fallback": fallback,
        "voice_workshop_api": "Core.local_voice_workshop",
        "source_identity_rights_review_required": candidate["creator_type"] in {"fictional", "historical"},
        "audio_generated": False,
        "voice_assigned": False,
        "voice_played": False,
        "activation_allowed": False,
    }


def _validate_v4_operation(
    root: Path,
    evidence: Mapping[str, Any],
    *,
    expected_operation: str,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    envelope_rel, _path, envelope_hint, envelope_sha = _safe_bound_file(
        root,
        evidence.get("envelope_relative"),
        evidence.get("envelope_sha256"),
        canonical_json_required=True,
    )
    trusted = _text(envelope_hint.get("issued_at_utc"))
    envelope, observed_sha = quality_v4._load_and_validate_envelope(
        root, envelope_rel, envelope_sha, trusted
    )
    if observed_sha != envelope_sha or envelope.get("operation") != expected_operation:
        raise TemporaryCreatorPipelineError("v4_signed_operation_mismatch")
    marker_rel = (
        f"{quality_v4.CONSUMPTION_NAMESPACE}/{envelope['authorization_id']}--"
        f"{envelope['nonce']}.json"
    )
    marker_path = root / Path(*PurePosixPath(marker_rel).parts)
    if not marker_path.is_file():
        raise TemporaryCreatorPipelineError("v4_consumption_marker_missing")
    marker = json.loads(marker_path.read_text("utf-8"))
    if (
        set(marker) != set(quality_v4.CONSUMPTION_KEYS)
        or marker.get("envelope_sha256") != envelope_sha
        or marker.get("authorization_id") != envelope["authorization_id"]
        or marker.get("nonce") != envelope["nonce"]
        or marker.get("operation") != expected_operation
        or marker.get("lifecycle") != quality_v4.private_lifecycle()
    ):
        raise TemporaryCreatorPipelineError("v4_consumption_marker_binding_invalid")
    _outcome_rel, _outcome_path, outcome, _outcome_sha = _safe_bound_file(
        root,
        evidence.get("outcome_relative"),
        evidence.get("outcome_sha256"),
        canonical_json_required=True,
    )
    if (
        outcome.get("record_kind") != quality_v4.OUTCOME_KIND
        or outcome.get("status") != "success"
        or outcome.get("stage") != "complete"
        or outcome.get("operation") != expected_operation
        or outcome.get("envelope_sha256") != envelope_sha
        or outcome.get("activation_assignment_publication_or_registration_changed") is not False
        or outcome.get("model_body_voice_avatar_blender_browser_or_live_work_started") is not False
        or outcome.get("lifecycle") != quality_v4.private_lifecycle()
    ):
        raise TemporaryCreatorPipelineError("v4_success_outcome_invalid")
    return envelope, outcome, envelope_sha


def _validate_v4_evidence(
    root: Path,
    evidence: Mapping[str, Any] | None,
    candidate: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    if not evidence:
        return None, ["signed_v4_creation_and_static_evaluation_evidence_missing"]
    try:
        creation_evidence = evidence.get("creation")
        evaluation_evidence = evidence.get("evaluation")
        if not isinstance(creation_evidence, Mapping) or not isinstance(
            evaluation_evidence, Mapping
        ):
            raise TemporaryCreatorPipelineError("v4_evidence_operations_missing")
        create_envelope, create_outcome, create_sha = _validate_v4_operation(
            root, creation_evidence, expected_operation="create_static_quality"
        )
        quality_rel, _quality_path, quality, quality_sha = _safe_bound_file(
            root,
            creation_evidence.get("quality_record_relative"),
            creation_evidence.get("quality_record_sha256"),
            canonical_json_required=True,
        )
        outputs = create_outcome.get("outputs")
        outputs = outputs if isinstance(outputs, Mapping) else {}
        if (
            outputs.get("quality_record") != quality_rel
            or outputs.get("quality_record_sha256") != quality_sha
            or quality.get("record_kind") != quality_v4.CREATION_RESULT_KIND
            or quality.get("quality_status") != quality_v4.READY_STATUS
            or quality.get("candidate_id") != candidate["person_id"]
            or quality.get("display_name") != candidate["display_name"]
            or quality.get("model_loaded_or_called") is not False
            or quality.get("lifecycle") != quality_v4.private_lifecycle()
        ):
            raise TemporaryCreatorPipelineError("v4_quality_record_binding_invalid")
        if (
            candidate["creator_type"] == "expert"
            and quality.get("expert_domain") != candidate["subject_or_domain"]
        ):
            raise TemporaryCreatorPipelineError("v4_expert_domain_mismatch")
        eval_envelope, eval_outcome, eval_sha = _validate_v4_operation(
            root, evaluation_evidence, expected_operation="evaluate_static_responses"
        )
        result_rel, _result_path, result, result_sha = _safe_bound_file(
            root,
            evaluation_evidence.get("evaluation_result_relative"),
            evaluation_evidence.get("evaluation_result_sha256"),
            canonical_json_required=True,
        )
        eval_outputs = eval_outcome.get("outputs")
        eval_outputs = eval_outputs if isinstance(eval_outputs, Mapping) else {}
        if (
            create_envelope.get("request_id") != eval_envelope.get("request_id")
            or eval_envelope.get("creation_authorization_sha256") != create_sha
            or eval_envelope.get("quality_record_sha256") != quality_sha
            or eval_outputs.get("evaluation_result") != result_rel
            or eval_outputs.get("evaluation_result_sha256") != result_sha
            or result.get("record_kind") != quality_v4.EVALUATION_RESULT_KIND
            or result.get("status") != quality_v4.STATIC_EVALUATION_STATUS
            or result.get("static_response_receipts_passed") is not True
            or result.get("live_model_execution_verified") is not False
            or result.get("live_qwen_quality_accepted") is not False
            or result.get("activation_assignment_publication_or_registration_changed") is not False
            or result.get("quality_record_sha256") != quality_sha
            or result.get("creation_authorization_sha256") != create_sha
            or result.get("lifecycle") != quality_v4.private_lifecycle()
        ):
            raise TemporaryCreatorPipelineError("v4_static_evaluation_binding_invalid")
        summary = {
            "creation_envelope_sha256": create_sha,
            "quality_record_sha256": quality_sha,
            "evaluation_envelope_sha256": eval_sha,
            "evaluation_result_sha256": result_sha,
            "request_id": create_envelope["request_id"],
            "candidate_id": quality["candidate_id"],
            "static_only": True,
            "live_model_quality_accepted": False,
            "activation_allowed": False,
            "evidence": {
                "creation": {
                    key: _text(creation_evidence.get(key))
                    for key in (
                        "envelope_relative",
                        "envelope_sha256",
                        "outcome_relative",
                        "outcome_sha256",
                        "quality_record_relative",
                        "quality_record_sha256",
                    )
                },
                "evaluation": {
                    key: _text(evaluation_evidence.get(key))
                    for key in (
                        "envelope_relative",
                        "envelope_sha256",
                        "outcome_relative",
                        "outcome_sha256",
                        "evaluation_result_relative",
                        "evaluation_result_sha256",
                    )
                },
            },
        }
        summary["evidence_graph_sha256"] = canonical_sha256(summary)
        return summary, []
    except (OSError, ValueError, quality_v4.QualityV4Error) as exc:
        return None, [f"v4_evidence_invalid:{str(exc)[:240]}"]


def _promotion_policy() -> dict[str, Any]:
    return {
        "temporary_by_default": True,
        "creation_can_promote": False,
        "permanent_promotion": {
            "status": "blocked",
            "explicit_founder_approval_required": True,
            "founder_approval_present": False,
            "verified_ram_capacity_required": True,
            "ram_capacity_verified": False,
            "verified_residency_capacity_required": True,
            "residency_capacity_verified": False,
            "separate_promotion_workflow_required": True,
        },
    }


def _build_residency_order(
    candidate: Mapping[str, Any], *, avatar_order: Mapping[str, Any], voice_order: Mapping[str, Any]
) -> dict[str, Any]:
    blockers = [
        "reviewed_avatar_result_not_present",
        "reviewed_voice_result_not_present",
        "final_founder_activation_review_not_present",
        "ram_capacity_not_verified",
        "residency_capacity_not_verified",
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RESIDENCY_ORDER_KIND,
        "person_id": candidate["person_id"],
        "candidate_input_sha256": candidate["input_sha256"],
        "status": "blocked",
        "blockers": blockers,
        "queue_contract": "temporary_ai_activation_queue_v1",
        "requested_temporary_visibility_after_review": deepcopy(
            candidate["availability"]
        ),
        "avatar_work_order_sha256": canonical_sha256(avatar_order),
        "voice_work_order_sha256": canonical_sha256(voice_order),
        "promotion_policy": _promotion_policy(),
        "residency_record_created": False,
        "person_present_in_kira_world": False,
        "activation_performed": False,
        "permanent_promotion_performed": False,
    }


def _build_registration_readiness(
    candidate: Mapping[str, Any],
    *,
    bundle_id: str,
    v4_ready: bool,
    v4_summary: Mapping[str, Any] | None,
    mind_order: Mapping[str, Any],
    avatar_order: Mapping[str, Any],
    voice_order: Mapping[str, Any],
    residency_order: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the only manifest existing-surface registry adapters should read.

    Work-order creation alone is never enough for discovery.  A later finalizer
    must replace the blocked evidence rows with exact reviewed result bindings;
    registry adapters must ignore every manifest whose status is not ``ready``.
    """

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": READINESS_KIND,
        "bundle_id": bundle_id,
        "person_id": candidate["person_id"],
        "status": "blocked",
        "ready_for_existing_surface_registration": False,
        "existing_surfaces": {
            "kira_text_voice_chat": {
                "discoverable": False,
                "registration_performed": False,
            },
            "kira_world_shell": {
                "discoverable": False,
                "registration_performed": False,
            },
        },
        "draft_or_failed_people_must_remain_hidden": True,
        "v4_evidence": deepcopy(v4_summary.get("evidence", {}))
        if v4_summary
        else {},
        "required_exact_result_evidence": {
            "v4_static_gate_ready": v4_ready,
            "mind_knowledge_reviewed_result": False,
            "avatar_builder_reviewed_result": False,
            "voice_generator_reviewed_result": False,
            "final_founder_activation_review": False,
            "ram_capacity_verified": False,
            "residency_capacity_verified": False,
        },
        "work_order_content_sha256": {
            "mind_knowledge": canonical_sha256(mind_order),
            "avatar_builder": canonical_sha256(avatar_order),
            "voice_generator": canonical_sha256(voice_order),
            "kira_world_residency": canonical_sha256(residency_order),
        },
        "activation_allowed": False,
        "person_present_in_kira_world": False,
        "permanent_promotion_allowed": False,
    }


def orchestrate_temporary_creator(
    execution_root: Path,
    workspace: Path,
    candidate_data: Mapping[str, Any],
    *,
    created_at_utc: str | None = None,
    v4_evidence: Mapping[str, Any] | None = None,
    voice_source_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create or refresh deterministic, inert work orders for one person.

    ``workspace`` must be either ``TemporaryAI/creator_work_orders`` (the
    shared-person child is selected automatically) or that person's exact
    ``TemporaryAI/creator_work_orders/<person_id>`` child inside
    ``execution_root``.  The function performs no network, model, avatar,
    audio, runtime, queue, activation, or promotion operation.
    """

    timestamp = _canonical_utc(created_at_utc or utc_now(), "created_at_utc")
    candidate, input_blockers = _normalize_candidate(candidate_data)
    if input_blockers:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_kind": PIPELINE_KIND,
            "person_id": candidate.get("person_id", ""),
            "overall_status": "draft",
            "stages": {
                "authenticated_command": _status("draft", blockers=input_blockers),
                "mind_knowledge": _status("blocked", blockers=["authenticated_command_incomplete"]),
                "v4_static_gate": _status("blocked", blockers=["authenticated_command_incomplete"]),
                "avatar_builder": _status("blocked", blockers=["authenticated_command_incomplete"]),
                "voice_generator": _status("blocked", blockers=["authenticated_command_incomplete"]),
                "kira_world_residency": _status("blocked", blockers=["authenticated_command_incomplete"]),
            },
            "written_files": {},
            "activation_allowed": False,
            "person_present_in_kira_world": False,
            "permanent_promotion_allowed": False,
        }

    root, target = _safe_workspace(
        execution_root, workspace, candidate["person_id"]
    )
    identity = _identity_resolution(candidate)
    intake = _build_intake(candidate, timestamp)
    v4_summary, v4_blockers = _validate_v4_evidence(root, v4_evidence, candidate)
    v4_ready = v4_summary is not None
    codesign_id = f"{candidate['person_id']}_body_voice_codesign_v1"
    mind_order = _build_mind_order(candidate, identity, candidate["input_sha256"])
    avatar_order = _build_avatar_order(
        candidate,
        identity,
        v4_ready=v4_ready,
        execution_root=root,
        codesign_id=codesign_id,
    )
    voice_order = _build_voice_order(
        candidate,
        identity,
        created_at_utc=timestamp,
        v4_ready=v4_ready,
        codesign_id=codesign_id,
        execution_root=root,
        voice_source_evidence=voice_source_evidence,
    )
    residency_order = _build_residency_order(
        candidate, avatar_order=avatar_order, voice_order=voice_order
    )
    bundle_id = f"{candidate['person_id']}_creator_bundle_{candidate['input_sha256'][:12]}"
    readiness = _build_registration_readiness(
        candidate,
        bundle_id=bundle_id,
        v4_ready=v4_ready,
        v4_summary=v4_summary,
        mind_order=mind_order,
        avatar_order=avatar_order,
        voice_order=voice_order,
        residency_order=residency_order,
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": MANIFEST_KIND,
        "bundle_id": bundle_id,
        "person_id": candidate["person_id"],
        "created_at_utc": timestamp,
        "creator_type": candidate["creator_type"],
        "display_name": candidate["display_name"],
        "role_title": candidate["role_title"],
        "subject_or_domain": candidate["subject_or_domain"],
        "candidate_input_sha256": candidate["input_sha256"],
        "single_authenticated_command_sha256": candidate["requested_by"][
            "command_sha256"
        ],
        "identity_resolution": identity,
        "v4_static_evidence": v4_summary or {},
        "temporary_by_default": True,
        "activation_allowed": False,
        "person_present_in_kira_world": False,
        "permanent_promotion_allowed": False,
    }
    files = {
        "person_manifest.json": manifest,
        "temporary_person_request.json": intake,
        "mind_knowledge_work_order.json": mind_order,
        "avatar_builder_work_order.json": avatar_order,
        "voice_generator_work_order.json": voice_order,
        "kira_world_residency_work_order.json": residency_order,
        "shared_person_readiness.json": readiness,
    }
    written: dict[str, str] = {}
    for filename, value in files.items():
        written[filename] = _write_json_atomic(target / filename, value)

    stages = {
        "authenticated_command": _status(
            "ready",
            command_sha256=candidate["requested_by"]["command_sha256"],
        ),
        "mind_knowledge": _status(
            "queued",
            blockers=list(mind_order["execution_blockers"]),
            work_order_sha256=written["mind_knowledge_work_order.json"],
        ),
        "v4_static_gate": _status(
            "ready" if v4_ready else "blocked",
            blockers=v4_blockers,
            evidence=v4_summary or {},
        ),
        "avatar_builder": _status(
            "queued",
            blockers=list(avatar_order["execution_blockers"]),
            work_order_sha256=written["avatar_builder_work_order.json"],
        ),
        "voice_generator": _status(
            "queued",
            blockers=list(voice_order["execution_blockers"]),
            work_order_sha256=written["voice_generator_work_order.json"],
        ),
        "kira_world_residency": _status(
            "blocked",
            blockers=list(residency_order["blockers"]),
            work_order_sha256=written["kira_world_residency_work_order.json"],
        ),
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": PIPELINE_KIND,
        "bundle_id": bundle_id,
        "person_id": candidate["person_id"],
        "overall_status": "queued",
        "workspace_relative": target.relative_to(root).as_posix(),
        "candidate_input_sha256": candidate["input_sha256"],
        "stages": stages,
        "written_files": written,
        "truth": {
            "mind_or_knowledge_built": False,
            "avatar_or_body_created": False,
            "voice_generated_or_assigned": False,
            "residency_record_created": False,
            "person_present_in_kira_world": False,
            "activation_performed": False,
            "permanent_promotion_performed": False,
        },
        "activation_allowed": False,
        "person_present_in_kira_world": False,
        "permanent_promotion_allowed": False,
        "promotion_policy": _promotion_policy(),
    }
    result["result_sha256"] = canonical_sha256(result)
    _write_json_atomic(target / "pipeline_result.json", result)
    return deepcopy(result)


__all__ = [
    "ALLOWED_CREATOR_TYPES",
    "ALLOWED_STAGE_STATUSES",
    "AVATAR_ORDER_KIND",
    "MANIFEST_KIND",
    "MIND_ORDER_KIND",
    "PIPELINE_KIND",
    "READINESS_KIND",
    "RESIDENCY_ORDER_KIND",
    "SCHEMA_VERSION",
    "TemporaryCreatorPipelineError",
    "VOICE_ORDER_KIND",
    "VOICE_SOURCE_REVIEW_KIND",
    "WORKSPACE_RELATIVE_ROOT",
    "canonical_json_bytes",
    "canonical_sha256",
    "file_sha256",
    "orchestrate_temporary_creator",
]
