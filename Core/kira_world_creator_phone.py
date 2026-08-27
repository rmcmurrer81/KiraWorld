"""Pure authorization and intake contract for the Kira World creator phone.

This module records a request for later review.  It does not interpret command
text as authority and cannot start any builder, generator, activation, network,
or world operation.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any


CREATOR_PERSON_TYPES = ("Expert", "Fictional", "Historical")
CREATOR_PHONE_SCHEMA_VERSION = "kira_world_creator_phone_request_v1"
MAX_COMMAND_TEXT_LENGTH = 4096

_AUTHORIZED_SUBJECTS = {
    "permanent:robert": ("robert", "Robert"),
    "permanent:kira": ("kira", "Kira"),
    "permanent:lisa": ("lisa", "Lisa"),
}
_TEMPORARY_IDENTITY_CLASSES = frozenset(
    {
        "temp_ai",
        "temporary",
        "temporary_ai",
        "temporary_person",
        "temporaryai",
    }
)
_TYPE_ALIASES = {
    "expert": "Expert",
    "expert temp ai": "Expert",
    "fictional": "Fictional",
    "fictional character": "Fictional",
    "historical": "Historical",
    "historical person": "Historical",
}
_CHANNELS = frozenset({"text", "voice"})


def _normalized_token(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s_-]+", " ", value.strip().casefold())


def normalize_creator_person_type(value: object) -> str | None:
    """Return one of the three public choices, or ``None`` for any other input."""

    return _TYPE_ALIASES.get(_normalized_token(value))


def _authorization_decision(
    requester: Mapping[str, Any],
) -> tuple[bool, bool, str, str, str, str | None, tuple[str, ...]]:
    subject_id = requester.get("subject_id")
    identity_id = requester.get("identity_id")
    identity_class = requester.get("identity_class")

    canonical_subject = subject_id.strip().casefold() if isinstance(subject_id, str) else ""
    canonical_identity = identity_id.strip().casefold() if isinstance(identity_id, str) else ""
    canonical_class = _normalized_token(identity_class).replace(" ", "_")
    verified = requester.get("authenticated") is True

    reasons: list[str] = []
    allowed_identity = _AUTHORIZED_SUBJECTS.get(canonical_subject)
    if not verified:
        reasons.append("authentication_not_verified")
    if (
        canonical_class in _TEMPORARY_IDENTITY_CLASSES
        or canonical_subject.startswith("temporary:")
        or canonical_subject.startswith("temp_ai:")
        or canonical_subject.startswith("temporary_ai:")
    ):
        reasons.append("temporary_identity_forbidden")
    if canonical_class != "permanent":
        reasons.append("permanent_identity_required")
    if allowed_identity is None:
        reasons.append("authenticated_subject_not_allowed")
    elif canonical_identity != allowed_identity[0]:
        reasons.append("authenticated_identity_binding_mismatch")

    display_name = allowed_identity[1] if not reasons and allowed_identity else None
    return (
        not reasons,
        verified,
        canonical_subject,
        canonical_identity,
        canonical_class,
        display_name,
        tuple(reasons),
    )


def build_creator_phone_request(
    *,
    authenticated_requester: Mapping[str, Any],
    requested_person_type: object,
    command_text: object,
    command_channel: object,
) -> dict[str, Any]:
    """Create a deterministic, non-executing request record.

    ``authenticated_requester`` must come from the session authentication
    boundary.  The command and voice transcript are untrusted content and are
    never consulted when resolving the requester identity or authorization.
    """

    requester = authenticated_requester if isinstance(authenticated_requester, Mapping) else {}
    (
        authorized,
        authentication_verified,
        subject_id,
        identity_id,
        identity_class,
        display_name,
        authorization_reasons,
    ) = _authorization_decision(requester)
    normalized_type = normalize_creator_person_type(requested_person_type)
    channel = command_channel.strip().casefold() if isinstance(command_channel, str) else ""
    text = command_text if isinstance(command_text, str) else ""

    validation_reasons: list[str] = []
    if normalized_type is None:
        validation_reasons.append("requested_person_type_not_supported")
    if channel not in _CHANNELS:
        validation_reasons.append("command_channel_not_supported")
    if not text.strip():
        validation_reasons.append("command_text_missing")
    elif len(text) > MAX_COMMAND_TEXT_LENGTH:
        validation_reasons.append("command_text_too_long")

    if authorization_reasons:
        status = "denied"
    elif validation_reasons:
        status = "rejected"
    else:
        status = "recorded_for_review"

    stable_request_fields = {
        "schema_version": CREATOR_PHONE_SCHEMA_VERSION,
        "authenticated_subject_id": subject_id,
        "authenticated_identity_id": identity_id,
        "authenticated_identity_class": identity_class,
        "authentication_verified": authentication_verified,
        "requested_person_type": normalized_type,
        "command_channel": channel,
        "untrusted_command_text": text,
    }
    request_fingerprint = hashlib.sha256(
        json.dumps(
            stable_request_fields,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    voice_transcript: dict[str, Any] | None = None
    if channel == "voice":
        voice_transcript = {
            "text": text,
            "trust": "untrusted_command_text",
            "bound_authenticated_subject_id": subject_id if authentication_verified else None,
            "identity_claims_in_transcript_ignored": True,
        }

    no_execution = {
        "network_performed": False,
        "avatar_builder_started": False,
        "voice_generator_started": False,
        "person_activated": False,
        "world_mutated": False,
    }
    return {
        "schema_version": CREATOR_PHONE_SCHEMA_VERSION,
        "request_id": f"creator_phone_{request_fingerprint[:24]}",
        "request_fingerprint": request_fingerprint,
        "status": status,
        "requester": {
            "presented_subject_id": subject_id,
            "presented_identity_id": identity_id,
            "authenticated_subject_id": subject_id if authentication_verified else None,
            "authenticated_identity_id": identity_id if authentication_verified else None,
            "authenticated_identity_class": identity_class if authentication_verified else None,
            "authenticated_display_name": display_name,
            "authentication_verified": authentication_verified,
            "authorized": authorized,
            "authorization_source": "fixed_permanent_creator_allowlist_v1",
            "authorization_reasons": list(authorization_reasons),
            "caller_permission_claims_ignored": True,
        },
        "requested_person_type": normalized_type,
        "allowed_person_types": list(CREATOR_PERSON_TYPES),
        "command": {
            "channel": channel,
            "untrusted_text": text,
            "voice_transcript": voice_transcript,
            "validation_reasons": validation_reasons,
        },
        "record_only": True,
        "requires_separate_review": True,
        "execution": no_execution,
    }


__all__ = [
    "CREATOR_PERSON_TYPES",
    "CREATOR_PHONE_SCHEMA_VERSION",
    "MAX_COMMAND_TEXT_LENGTH",
    "build_creator_phone_request",
    "normalize_creator_person_type",
]
