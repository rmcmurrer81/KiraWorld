"""Gated phone intake for requesting, not fabricating, a temporary person."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any


SUPPORTED_TYPES = {
    "historical_person",
    "fictional_character",
    "expert",
    "generated_original",
    "memory_relative",
    "other",
}
REQUIRED_RECORDS = (
    "identity",
    "personality",
    "memories",
    "knowledge_limits",
    "timeline",
    "point_of_view",
    "spoken_channel",
    "private_mind",
    "runtime_truth",
    "actions",
    "body",
    "voice",
    "relationships",
    "privacy",
    "consent",
    "activation_state",
)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:60] or "temporary_person"


def build_request(
    *,
    requested_by: dict[str, Any],
    request_type: str,
    request_text: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    details = dict(details or {})
    request_type = str(request_type or "").strip()
    request_text = str(request_text or "").strip()
    requester_id = str(requested_by.get("person_id") or "").strip()
    requester_authorized = requested_by.get("authorized") is True
    clarifications: list[str] = []
    blockers: list[str] = []
    if not requester_id:
        blockers.append("requester_identity_missing")
    if not requester_authorized:
        blockers.append("requester_not_authorized")
    if request_type not in SUPPORTED_TYPES:
        clarifications.append("What kind of temporary person is requested?")
    if not request_text:
        clarifications.append("What person, character, period, or expertise is wanted?")
    if request_type in {"historical_person", "fictional_character"}:
        for field, question in (
            ("exact_identity", "Which exact identity is intended?"),
            ("version_or_continuity", "Which version or continuity is intended?"),
            ("timeline_or_period", "What timeline, canon point, age, or historical period should be locked?"),
            ("point_of_view", "Whose point of view and knowledge boundary should apply?"),
        ):
            if not str(details.get(field) or "").strip():
                clarifications.append(question)
    if request_type == "expert" and not str(details.get("expert_domain") or "").strip():
        clarifications.append("What exact expert domain and purpose are needed?")
    if request_type == "memory_relative" and not details.get("owner_approved_memory_sources"):
        clarifications.append("Which owner-approved memory sources may be used?")

    created = _now()
    request_id = f"temporary_person_request_{_slug(request_text)}_{uuid.uuid4().hex[:10]}"
    records = {
        name: {
            "status": "not_built",
            "evidence": [],
            "owner_review": "pending",
        }
        for name in REQUIRED_RECORDS
    }
    records["activation_state"].update({"value": "inactive", "activation_allowed": False})
    records["voice"].update({
        "generic_fallback_allowed": False,
        "character_identity_separate_from_performer": True,
        "public_media_is_not_voice_clone_permission": True,
    })
    records["body"].update({
        "character_appearance_separate_from_performer": True,
        "pictures_and_video_require_evidence_and_rights_review": True,
    })
    return {
        "schema_version": "temporary_person_phone_request_v1",
        "request_id": request_id,
        "created_at": created,
        "requested_by": requested_by,
        "request_type": request_type,
        "request_text": request_text,
        "details": details,
        "clarifications_needed": clarifications,
        "blockers": blockers,
        "status": "blocked" if blockers else "needs_clarification" if clarifications else "ready_for_evidence_pipeline",
        "records": records,
        "gates": {
            "mind": "pending",
            "voice": "pending",
            "body": "pending",
            "timeline": "pending",
            "privacy": "pending",
            "source": "pending",
            "rights": "pending",
            "owner_review": "pending",
        },
        "activation_allowed": False,
        "fabricated_finished_person": False,
        "request_fingerprint": hashlib.sha256(
            json.dumps(
                {"requested_by": requested_by, "request_type": request_type, "request_text": request_text, "details": details},
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest(),
    }


def save_request(request: dict[str, Any], root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{request['request_id']}.json"
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing.get("request_fingerprint") == request.get("request_fingerprint"):
            return target
        raise FileExistsError(target)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(request, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(target)
    return target
