"""Immutable public data contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class SourceBasis(StrEnum):
    """What a voice is based on; never infer identity from a friendly name."""

    SOURCE_RECORDING_BACKED = "source_recording_backed"
    DESIGNED = "designed"
    GENERIC_FALLBACK = "generic_fallback"


class AuditionStatus(StrEnum):
    NOT_AUDITIONED = "not_auditioned"
    AUDITIONED = "auditioned"
    OWNER_APPROVED = "owner_approved"


class ConsentBasis(StrEnum):
    SOURCE_SUBJECT_CONSENT = "source_subject_consent"
    SYNTHETIC_DESIGN = "synthetic_design"
    GENERIC_NO_IDENTITY = "generic_no_identity"


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class ConsentRecord:
    basis: ConsentBasis
    subject_id: str
    authority: str
    scope: str
    recorded_at: str
    evidence_sha256: str | None
    reference_recording_permitted: bool
    generated_audio_permitted: bool
    revocable: bool = True
    expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReferenceDescriptor:
    sha256: str
    bytes: int
    duration_seconds: float
    channels: int
    sample_width_bytes: int
    sample_rate_hz: int
    frame_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class VoiceProfile:
    voice_id: str
    display_name: str
    source_basis: SourceBasis
    audition_status: AuditionStatus
    consent: ConsentRecord
    language: str = "en-US"
    description: str = ""
    reference_hashes: tuple[str, ...] = ()
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["reference_hashes"] = list(self.reference_hashes)
        return result


@dataclass(frozen=True, slots=True)
class SynthesisRequest:
    text: str
    voice_id: str
    output_name: str | None = None
    language: str = "en-US"
    speed: float = 1.0
    style: str = "neutral"
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BackendResult:
    format: str
    sample_rate_hz: int
    duration_seconds: float
    backend_name: str
    backend_version: str
    mock_audio: bool
    model_source: str = "none"
    model_revision: str = "none"
    voice_id: str = "none"
    license_id: str = "none"
    offline: bool = True
    provenance_scope: str = "unspecified"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class JobSnapshot:
    job_id: str
    state: JobState
    created_at: str
    updated_at: str
    request: dict[str, Any]
    output_path: str | None = None
    receipt_path: str | None = None
    error: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["state"] = self.state.value
        return result
