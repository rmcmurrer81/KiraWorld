"""Bind Synthetic Robert's private self-voice to his portable runtime.

Synthetic Robert is a persistent portable-runtime identity, not a TemporaryAI
candidate.  The historical authorization record uses the old string
``robert_mcmurrer_presence_ai`` as an immutable *voice authorization binding
id*.  This adapter preserves that signed/checksummed binding without creating
a TemporaryAI profile or treating that legacy id as Synthetic Robert's
runtime identity.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from Core.private_self_voice_authorization import (
    validate_private_self_voice_authorization,
)


SYNTHETIC_ROBERT_PERSON_ID = "synthetic_robert"
AUTHORIZATION_BINDING_ID = "robert_mcmurrer_presence_ai"
PORTABLE_PROFILE_RELATIVE = Path(
    "handoff/hanson_little_sophia_20260819/portable_runtime/profiles/synthetic_robert.json"
)
VOICE_PROFILE_RELATIVE = Path("Voice/profiles/temp_ai/robert_mcmurrer_voice_profile.json")
VOICE_AUTHORIZATION_RELATIVE = Path(
    "Voice/authorizations/robert_self_voice_runtime_approval_20260717.json"
)


def is_synthetic_robert_persistent_identity(
    candidate: Mapping[str, Any] | None,
) -> bool:
    """Recognize the canonical person and legacy authorization binding IDs.

    The canonical ID is authoritative even if an untrusted caller removes or
    renames the display label.  Historical display hints remain accepted only
    for backward-compatible guard coverage; they never authorize TemporaryAI
    or generic operating-system voice routing.
    """

    candidate = candidate or {}
    profile = candidate.get("profile")
    if not isinstance(profile, Mapping):
        profile = candidate
    candidate_id = str(
        candidate.get("candidate_id") or profile.get("candidate_id") or ""
    ).strip().casefold()
    if candidate_id in {SYNTHETIC_ROBERT_PERSON_ID, AUTHORIZATION_BINDING_ID}:
        return True
    display = str(profile.get("display_name") or "").strip().casefold()
    identity = f"{display} {candidate_id}"
    return any(
        token in identity
        for token in ("robert_mcmurrer", "robert presence", "synthetic robert")
    )


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def build_synthetic_robert_voice_validator_profile() -> dict[str, Any]:
    """Return only the narrow payload required by the legacy validator."""

    return {
        "candidate_id": SYNTHETIC_ROBERT_PERSON_ID,
        "display_name": "Synthetic Robert",
        "gender_preference": "male",
        "voice_and_behavior": {
            "voice_authorization": VOICE_AUTHORIZATION_RELATIVE.as_posix(),
            "voice_profile": VOICE_PROFILE_RELATIVE.as_posix(),
        },
    }


def validate_synthetic_robert_voice_route(
    *, project_root: str | Path,
) -> dict[str, Any]:
    """Validate exact voice bytes and the separate portable identity route."""

    root = Path(project_root).resolve()
    portable = _read_object(root / PORTABLE_PROFILE_RELATIVE)
    authorization = _read_object(root / VOICE_AUTHORIZATION_RELATIVE)
    voice_profile = _read_object(root / VOICE_PROFILE_RELATIVE)
    result = validate_private_self_voice_authorization(
        AUTHORIZATION_BINDING_ID,
        build_synthetic_robert_voice_validator_profile(),
        project_root=root,
    )
    reasons = list(result.get("reasons", []))

    if portable.get("profile_id") != SYNTHETIC_ROBERT_PERSON_ID:
        reasons.append("portable_profile_identity_mismatch")
    if portable.get("display_name") != "Synthetic Robert":
        reasons.append("portable_profile_display_name_mismatch")
    portable_voice = portable.get("voice") if isinstance(portable.get("voice"), dict) else {}
    if portable_voice.get("default_voice_profile") != "robert":
        reasons.append("portable_default_voice_profile_mismatch")
    if portable_voice.get("fallback_policy") != "text_only":
        reasons.append("portable_voice_fallback_policy_mismatch")

    scope = authorization.get("scope") if isinstance(authorization.get("scope"), dict) else {}
    if scope.get("candidate_id") != AUTHORIZATION_BINDING_ID:
        reasons.append("legacy_authorization_binding_id_mismatch")
    if scope.get("person") != "synthetic_robert_variant":
        reasons.append("authorization_person_route_mismatch")
    if scope.get("biological_robert_and_synthetic_robert_remain_distinct") is not True:
        reasons.append("biological_and_synthetic_robert_separation_missing")

    if voice_profile.get("target_type") != "synthetic_robert_persistent_runtime":
        reasons.append("voice_profile_target_type_mismatch")
    runtime_audio = (
        voice_profile.get("runtime_audio_postprocess")
        if isinstance(voice_profile.get("runtime_audio_postprocess"), dict)
        else {}
    )
    if runtime_audio.get("scope") != "synthetic_robert_private_runtime_only":
        reasons.append("voice_profile_runtime_scope_mismatch")

    return {
        **result,
        "allowed": not reasons,
        "person_id": SYNTHETIC_ROBERT_PERSON_ID,
        "identity_route": "portable_persistent_synthetic_robert",
        "authorization_binding_id": AUTHORIZATION_BINDING_ID,
        "portable_profile": PORTABLE_PROFILE_RELATIVE.as_posix(),
        "temporary_ai_profile_used": False,
        "reasons": list(dict.fromkeys(reasons)),
    }
