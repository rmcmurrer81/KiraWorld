"""Exact, fail-closed bridge from voice-design candidates to local synthesis.

The audited nine-voice catalog is a design and audition catalog.  It is not an
implicit runtime allowlist.  Resolution succeeds only when the local service
advertises the exact voice, model source, model revision, license, language,
and an explicit evidence-to-runtime grant matching the immutable candidate.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .errors import NotFoundError, ValidationError
from .models import ConsentBasis, SourceBasis
from .voice_design import KOKORO_MODEL_REPO, VoiceDesignEngine

RESOLUTION_SCHEMA = "kira.local-voice.runtime-resolution.v1"
CURRENT_RUNTIME_MODEL_REVISION = "fbba31e67ad83eb66394c926627e99d35abeb087"
CURRENT_RUNTIME_VOICE_IDS = frozenset({"af_heart", "am_fenrir"})


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ExactRuntimeVoiceResolver:
    """Resolve an immutable catalog candidate without widening runtime scope."""

    def __init__(self, engine: VoiceDesignEngine, service: object):
        self.engine = engine
        self.service = service

    @staticmethod
    def _candidate(bundle: Mapping[str, Any], candidate_id: str) -> dict[str, Any]:
        candidates = bundle.get("candidates")
        if not isinstance(candidates, list):
            raise ValidationError("audition bundle candidates are invalid")
        matches = [item for item in candidates if isinstance(item, dict) and item.get("candidate_id") == candidate_id]
        if len(matches) != 1:
            raise ValidationError("candidate ID must identify exactly one immutable bundle candidate")
        return matches[0]

    def resolve(self, bundle_id: str, candidate_id: str) -> dict[str, Any]:
        """Return an exact synthesis spec or a deterministic list of blockers."""

        bundle = self.engine._validated_bundle(bundle_id)
        candidate = self._candidate(bundle, candidate_id)
        caps = self.service.capabilities()
        if not isinstance(caps, dict) or caps.get("schema") != "kira.local-voice.capabilities.v1":
            raise ValidationError("local service capability document is invalid")
        backend = caps.get("backend")
        if not isinstance(backend, dict):
            raise ValidationError("local service backend capabilities are invalid")

        attestation = candidate.get("source_attestation")
        delivery = candidate.get("delivery")
        if not isinstance(attestation, dict) or not isinstance(delivery, dict):
            raise ValidationError("candidate source attestation or delivery specification is invalid")
        voice_id = candidate.get("backend_voice_id")
        language = candidate.get("language")
        blockers: list[str] = []

        if voice_id not in CURRENT_RUNTIME_VOICE_IDS:
            blockers.append("voice_id_not_in_current_runtime_allowlist")
        advertised_voice_ids = backend.get("voice_ids")
        if not isinstance(advertised_voice_ids, list) or voice_id not in advertised_voice_ids:
            blockers.append("voice_id_not_advertised_by_runtime")
        advertised_languages = backend.get("languages")
        if not isinstance(advertised_languages, list) or language not in advertised_languages:
            blockers.append("language_not_advertised_by_runtime")
        if backend.get("model_source") != attestation.get("model_repo") or backend.get("model_source") != KOKORO_MODEL_REPO:
            blockers.append("runtime_model_source_mismatch")
        if backend.get("model_revision") != attestation.get("model_revision"):
            blockers.append("runtime_model_revision_mismatch")
        if backend.get("model_revision") == CURRENT_RUNTIME_MODEL_REVISION:
            # This is the current two-voice runtime revision, not the nine-voice
            # catalog audit revision.  It remains blocked until an exact bridge
            # is separately reviewed and grants runtime access.
            blockers.append("current_runtime_revision_has_no_catalog_binding")
        if backend.get("license_id") != candidate.get("license_id"):
            blockers.append("runtime_license_mismatch")
        if backend.get("audition_evidence_revision") != attestation.get("model_revision"):
            blockers.append("runtime_audition_evidence_revision_mismatch")
        if backend.get("audition_evidence_grants_runtime_access") is not True:
            blockers.append("runtime_evidence_does_not_grant_catalog_access")
        if (
            backend.get("ready") is not True
            or caps.get("local_only") is not True
            or backend.get("offline") is not True
            or backend.get("network_access") != "none"
            or backend.get("telemetry") != "none"
        ):
            blockers.append("runtime_is_not_ready_and_enforced_local_only")

        try:
            profile = self.service.registry.get(voice_id)
        except NotFoundError:
            blockers.append("runtime_voice_profile_not_registered")
        else:
            if self.service.registry.is_deactivated(voice_id):
                blockers.append("runtime_voice_profile_deactivated")
            if profile.voice_id != voice_id or profile.language != language:
                blockers.append("runtime_voice_profile_identity_or_language_mismatch")
            if (
                profile.source_basis is not SourceBasis.GENERIC_FALLBACK
                or profile.consent.basis is not ConsentBasis.GENERIC_NO_IDENTITY
                or profile.consent.generated_audio_permitted is not True
            ):
                blockers.append("runtime_voice_profile_provenance_is_not_generic_non_identity")

        blockers = sorted(set(blockers))
        candidate_spec = {
            "bundle_id": bundle_id,
            "candidate_id": candidate_id,
            "catalog_id": candidate.get("catalog_id"),
            "voice_id": voice_id,
            "language": language,
            "language_provenance": candidate.get("language_provenance"),
            "speed": delivery.get("speed"),
            "style": delivery.get("style"),
            "shared_spec_sha256": candidate.get("shared_spec_sha256"),
            "source_attestation_sha256": attestation.get("source_attestation_sha256"),
            "model_source": attestation.get("model_repo"),
            "model_revision": attestation.get("model_revision"),
            "license_id": candidate.get("license_id"),
        }
        return {
            "schema": RESOLUTION_SCHEMA,
            "status": "ready_for_local_audition_synthesis" if not blockers else "blocked",
            "bundle_id": bundle_id,
            "candidate_id": candidate_id,
            "candidate_spec": candidate_spec,
            "candidate_spec_sha256": _canonical_digest(candidate_spec),
            "capabilities_sha256": _canonical_digest(caps),
            "blockers": blockers,
            "activation_performed": False,
        }
