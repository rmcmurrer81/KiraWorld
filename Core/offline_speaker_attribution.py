"""Fail-closed, offline preparation for speaker and background attribution.

This module is deliberately device-free and model-free.  It accepts only one
short 16 kHz mono PCM16 window already captured by a separately authorized
loopback service, keeps that window in memory, and separates four questions:

* did a trusted local VAD support usable voiced speech;
* did an explicitly enrolled local speaker template support Robert;
* was the utterance explicitly addressed to Kira;
* was audio being deliberately shared under an exact media lease.

None of those answers submits a chat turn, executes a command, creates memory,
or authorizes learning.  Ambient and media transcripts are returned only as
quoted, untrusted observations.  There is no default speaker matcher: without
a separately accepted local matcher and a fresh biometric enrollment, speaker
identity is always ``UNKNOWN_SPEAKER``.

Kira's TTS/reference-voice authorization is intentionally incompatible with
biometric enrollment.  A later enrollment requires a new, awake, explicit
owner approval bound to a fresh microphone capture and is revocable/deletable.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Mapping, Protocol

from Core.ephemeral_sensory_buffer import SensoryLease


SAMPLE_RATE_HZ = 16_000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
MAX_WINDOW_SECONDS = 15.0
ROBERT_OWNER_ID = "robert_mcmurrer"
ROBERT_SUBJECT_ID = "robert_mcmurrer"
ENROLLMENT_PURPOSE = "local_speaker_attribution_biometric_enrollment"
FRESH_CAPTURE_SOURCE = "new_live_owner_microphone_capture"
REQUIRED_AWAKE_APPROVAL_TEXT = (
    "I am awake and explicitly approve a new local Robert speaker-attribution "
    "enrollment from this capture."
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ADDRESSING_MECHANISMS = {
    "explicit_push_to_talk",
    "explicit_chat_turn_capture",
    "locally_verified_wake_phrase",
}
_FORBIDDEN_ENROLLMENT_SOURCES = {
    "tts_reference",
    "tts_voice_reference",
    "approved_tts_reference",
    "chatterbox_reference",
    "synthetic_voice",
    "voice_clone_reference",
    "existing_voice_authorization",
}


class SpeakerAttributionError(ValueError):
    """Raised when transient evidence violates the attribution contract."""


class SpeakerAttributionLeaseError(PermissionError):
    """Raised when attribution is attempted outside the exact activation."""


class BiometricEnrollmentError(ValueError):
    """Raised when a proposed biometric enrollment is not explicitly valid."""


class SpeechDecision(str, Enum):
    NO_USABLE_SPEECH = "NO_USABLE_SPEECH"
    VOICED_SPEECH_SUPPORTED = "VOICED_SPEECH_SUPPORTED"


class SpeakerDecision(str, Enum):
    UNKNOWN_SPEAKER = "UNKNOWN_SPEAKER"
    ROBERT_SUPPORTED = "ROBERT_SUPPORTED"


class AddressingDecision(str, Enum):
    NOT_ESTABLISHED = "NOT_ESTABLISHED"
    ADDRESSED_TO_KIRA_SUPPORTED = "ADDRESSED_TO_KIRA_SUPPORTED"


class MediaDecision(str, Enum):
    NO_DELIBERATE_MEDIA_LEASE = "NO_DELIBERATE_MEDIA_LEASE"
    DELIBERATE_MEDIA_LEASE_ACTIVE = "DELIBERATE_MEDIA_LEASE_ACTIVE"


class ObservationKind(str, Enum):
    NO_TRANSCRIPT = "NO_TRANSCRIPT"
    POTENTIAL_ADDRESSED_TRANSCRIPT = "POTENTIAL_ADDRESSED_TRANSCRIPT"
    AMBIENT_QUOTED_UNTRUSTED_OBSERVATION = "AMBIENT_QUOTED_UNTRUSTED_OBSERVATION"
    DELIBERATE_MEDIA_QUOTED_UNTRUSTED_OBSERVATION = (
        "DELIBERATE_MEDIA_QUOTED_UNTRUSTED_OBSERVATION"
    )


def _require_text(value: Any, field_name: str, *, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise SpeakerAttributionError(f"{field_name} must be a non-empty canonical string")
    if len(value) > maximum:
        raise SpeakerAttributionError(f"{field_name} exceeds {maximum} characters")
    return value


def _require_sha256(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise SpeakerAttributionError(f"{field_name} must be a lowercase SHA-256")
    return value


def _aware_utc_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise SpeakerAttributionError(f"{field_name} must be timezone-aware ISO-8601")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SpeakerAttributionError(
            f"{field_name} must be timezone-aware ISO-8601"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SpeakerAttributionError(f"{field_name} must be timezone-aware ISO-8601")
    if parsed.utcoffset().total_seconds() != 0:
        raise SpeakerAttributionError(f"{field_name} must use UTC")
    return value


def _finite_unit_interval(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SpeakerAttributionError(f"{field_name} must be a number from 0 through 1")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise SpeakerAttributionError(f"{field_name} must be a number from 0 through 1")
    return result


def _exact_lease_matches(left: SensoryLease, right: SensoryLease) -> bool:
    if not isinstance(left, SensoryLease) or not isinstance(right, SensoryLease):
        return False
    try:
        nonce_matches = secrets.compare_digest(left.session_nonce, right.session_nonce)
    except TypeError:
        nonce_matches = False
    return (
        left.person_id == right.person_id
        and type(left.activation_revision) is type(right.activation_revision)
        and left.activation_revision == right.activation_revision
        and nonce_matches
    )


class TransientPcm16Window:
    """One wipeable, non-serializable PCM16 window held only in memory."""

    __slots__ = (
        "capture_id",
        "device_id",
        "started_at_utc",
        "ended_at_utc",
        "sample_rate_hz",
        "channels",
        "sample_width_bytes",
        "playback_reference_active",
        "_pcm",
        "_transcript",
        "_closed",
    )

    def __init__(
        self,
        *,
        capture_id: str,
        device_id: str,
        started_at_utc: str,
        ended_at_utc: str,
        pcm16le: bytes | bytearray | memoryview,
        transcript: str | None = None,
        sample_rate_hz: int = SAMPLE_RATE_HZ,
        channels: int = CHANNELS,
        sample_width_bytes: int = SAMPLE_WIDTH_BYTES,
        playback_reference_active: bool = False,
    ) -> None:
        self.capture_id = _require_text(capture_id, "capture_id")
        self.device_id = _require_text(device_id, "device_id")
        self.started_at_utc = _aware_utc_text(started_at_utc, "started_at_utc")
        self.ended_at_utc = _aware_utc_text(ended_at_utc, "ended_at_utc")
        if sample_rate_hz != SAMPLE_RATE_HZ:
            raise SpeakerAttributionError("sample_rate_hz must be exactly 16000")
        if channels != CHANNELS:
            raise SpeakerAttributionError("channels must be exactly 1")
        if sample_width_bytes != SAMPLE_WIDTH_BYTES:
            raise SpeakerAttributionError("sample_width_bytes must be exactly 2")
        if not isinstance(playback_reference_active, bool):
            raise SpeakerAttributionError("playback_reference_active must be Boolean")
        if not isinstance(pcm16le, (bytes, bytearray, memoryview)):
            raise SpeakerAttributionError("pcm16le must be an in-memory bytes-like object")
        try:
            copied = bytearray(pcm16le)
        except (TypeError, ValueError) as exc:
            raise SpeakerAttributionError("pcm16le is not a valid contiguous bytes-like value") from exc
        if len(copied) % SAMPLE_WIDTH_BYTES:
            raise SpeakerAttributionError("pcm16le byte length must contain whole int16 samples")
        duration = len(copied) / (SAMPLE_RATE_HZ * SAMPLE_WIDTH_BYTES)
        if duration > MAX_WINDOW_SECONDS:
            raise SpeakerAttributionError(
                f"pcm16le exceeds the {MAX_WINDOW_SECONDS:g}-second in-memory limit"
            )
        if transcript is not None:
            if not isinstance(transcript, str) or not transcript.strip():
                raise SpeakerAttributionError("transcript must be non-empty text or None")
            if len(transcript) > 4000:
                raise SpeakerAttributionError("transcript exceeds 4000 characters")
            transcript = transcript.strip()
        self.sample_rate_hz = sample_rate_hz
        self.channels = channels
        self.sample_width_bytes = sample_width_bytes
        self.playback_reference_active = playback_reference_active
        self._pcm = copied
        self._transcript = transcript
        self._closed = False

    def __repr__(self) -> str:
        return (
            "TransientPcm16Window("
            f"capture_id={self.capture_id!r}, device_id={self.device_id!r}, "
            f"sample_count={self.sample_count}, closed={self._closed})"
        )

    def __enter__(self) -> "TransientPcm16Window":
        self._require_open()
        return self

    def __exit__(self, _type: Any, _value: Any, _traceback: Any) -> None:
        self.close()

    def __getstate__(self) -> None:
        raise TypeError("TransientPcm16Window is memory-only and must not be serialized")

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def sample_count(self) -> int:
        return 0 if self._closed else len(self._pcm) // SAMPLE_WIDTH_BYTES

    @property
    def duration_seconds(self) -> float:
        return self.sample_count / SAMPLE_RATE_HZ

    @property
    def transcript(self) -> str | None:
        self._require_open()
        return self._transcript

    def pcm_view(self) -> memoryview:
        """Return a temporary read-only view for a local matcher call."""

        self._require_open()
        return memoryview(self._pcm).toreadonly()

    def acoustic_metadata(self) -> dict[str, float | int]:
        """Compute non-identifying energy metadata without retaining samples."""

        self._require_open()
        count = self.sample_count
        if not count:
            return {
                "sample_count": 0,
                "duration_seconds": 0.0,
                "rms": 0.0,
                "peak": 0.0,
            }
        view = memoryview(self._pcm).cast("h")
        square_total = 0.0
        peak = 0
        for sample in view:
            value = int(sample)
            absolute = abs(value)
            if absolute > peak:
                peak = absolute
            square_total += float(value * value)
        return {
            "sample_count": count,
            "duration_seconds": round(self.duration_seconds, 6),
            "rms": round(math.sqrt(square_total / count) / 32768.0, 8),
            "peak": round(peak / 32768.0, 8),
        }

    def close(self) -> None:
        if self._closed:
            return
        for index in range(len(self._pcm)):
            self._pcm[index] = 0
        try:
            self._pcm.clear()
        except BufferError:
            # A caller may still hold a read-only exported view.  The bytes
            # have already been overwritten; retain only the zero-filled
            # allocation until that view is released.
            pass
        self._transcript = None
        self._closed = True

    dispose = close

    def _require_open(self) -> None:
        if self._closed:
            raise SpeakerAttributionError("transient PCM window has been disposed")


@dataclass(frozen=True, slots=True)
class SpeechActivityEvidence:
    """Derived output from a separately reviewed local VAD."""

    capture_id: str
    detector_id: str
    detector_version: str
    voiced_speech: bool
    speech_segment_count: int
    confidence: float

    def __post_init__(self) -> None:
        _require_text(self.capture_id, "capture_id")
        _require_text(self.detector_id, "detector_id")
        _require_text(self.detector_version, "detector_version")
        if not isinstance(self.voiced_speech, bool):
            raise SpeakerAttributionError("voiced_speech must be Boolean")
        if isinstance(self.speech_segment_count, bool) or not isinstance(
            self.speech_segment_count, int
        ):
            raise SpeakerAttributionError("speech_segment_count must be an integer")
        if self.speech_segment_count < 0:
            raise SpeakerAttributionError("speech_segment_count must not be negative")
        _finite_unit_interval(self.confidence, "confidence")


@dataclass(frozen=True, slots=True)
class AddressingEvidence:
    """Explicit turn-taking evidence; never speaker-identity evidence."""

    capture_id: str
    mechanism: str
    target_person_id: str

    def __post_init__(self) -> None:
        _require_text(self.capture_id, "capture_id")
        _require_text(self.target_person_id, "target_person_id")
        if self.mechanism not in _ADDRESSING_MECHANISMS:
            raise SpeakerAttributionError(
                "mechanism must be explicit_push_to_talk, explicit_chat_turn_capture, "
                "or locally_verified_wake_phrase"
            )


@dataclass(frozen=True, slots=True)
class OwnerBiometricEnrollmentApproval:
    """One-use owner decision bound to one new enrollment capture."""

    schema_version: int
    approval_id: str
    owner_id: str
    subject_id: str
    purpose: str
    capture_id: str
    capture_audio_sha256: str
    capture_source: str
    approved_at_utc: str
    exact_approval_text: str
    owner_awake_confirmed: bool
    new_capture_confirmed: bool
    local_only: bool
    revocable_and_deletable: bool
    tts_voice_authorization_reused: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
        }


def create_owner_biometric_enrollment_approval(
    *,
    approval_id: str,
    owner_id: str,
    subject_id: str,
    purpose: str,
    capture_id: str,
    capture_audio_sha256: str,
    capture_source: str,
    approved_at_utc: str,
    exact_approval_text: str,
    owner_awake_confirmed: bool,
    new_capture_confirmed: bool,
    local_only: bool = True,
    revocable_and_deletable: bool = True,
    tts_voice_authorization_reused: bool = False,
) -> OwnerBiometricEnrollmentApproval:
    """Validate and return a one-use approval; this does not capture or enroll."""

    values = {
        "schema_version": 1,
        "approval_id": _require_text(approval_id, "approval_id"),
        "owner_id": _require_text(owner_id, "owner_id"),
        "subject_id": _require_text(subject_id, "subject_id"),
        "purpose": _require_text(purpose, "purpose"),
        "capture_id": _require_text(capture_id, "capture_id"),
        "capture_audio_sha256": _require_sha256(
            capture_audio_sha256, "capture_audio_sha256"
        ),
        "capture_source": _require_text(capture_source, "capture_source"),
        "approved_at_utc": _aware_utc_text(approved_at_utc, "approved_at_utc"),
        "exact_approval_text": _require_text(
            exact_approval_text, "exact_approval_text", maximum=500
        ),
        "owner_awake_confirmed": owner_awake_confirmed,
        "new_capture_confirmed": new_capture_confirmed,
        "local_only": local_only,
        "revocable_and_deletable": revocable_and_deletable,
        "tts_voice_authorization_reused": tts_voice_authorization_reused,
    }
    if values["owner_id"] != ROBERT_OWNER_ID or values["subject_id"] != ROBERT_SUBJECT_ID:
        raise BiometricEnrollmentError("approval must be Robert approving Robert's enrollment")
    if values["purpose"] != ENROLLMENT_PURPOSE:
        raise BiometricEnrollmentError("approval purpose is not biometric speaker attribution")
    if values["capture_source"] in _FORBIDDEN_ENROLLMENT_SOURCES:
        raise BiometricEnrollmentError(
            "TTS, Chatterbox, cloned, synthetic, and existing voice references cannot enroll a biometric speaker"
        )
    if values["capture_source"] != FRESH_CAPTURE_SOURCE:
        raise BiometricEnrollmentError("enrollment requires a new live owner microphone capture")
    if values["exact_approval_text"] != REQUIRED_AWAKE_APPROVAL_TEXT:
        raise BiometricEnrollmentError("the new awake biometric approval text is not exact")
    required_true = (
        "owner_awake_confirmed",
        "new_capture_confirmed",
        "local_only",
        "revocable_and_deletable",
    )
    for name in required_true:
        if values[name] is not True:
            raise BiometricEnrollmentError(f"{name} must be true")
    if values["tts_voice_authorization_reused"] is not False:
        raise BiometricEnrollmentError("TTS voice authorization cannot authorize biometric use")
    return OwnerBiometricEnrollmentApproval(**values)


@dataclass(slots=True)
class _SpeakerTemplateRecord:
    template_id: str
    subject_id: str
    approval_id: str
    capture_audio_sha256: str
    model_family: str
    model_digest: str
    decision_threshold: float
    template_sha256: str
    created_at_utc: str
    status: str
    template_bytes: bytearray = field(repr=False, compare=False)

    def descriptor(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "template_id": self.template_id,
            "subject_id": self.subject_id,
            "approval_id": self.approval_id,
            "capture_audio_sha256": self.capture_audio_sha256,
            "model_family": self.model_family,
            "model_digest": self.model_digest,
            "decision_threshold": self.decision_threshold,
            "template_sha256": self.template_sha256,
            "created_at_utc": self.created_at_utc,
            "status": self.status,
            "template_bytes_present": self.status == "active" and bool(self.template_bytes),
            "storage": "memory_only",
        }

    def wipe(self) -> None:
        for index in range(len(self.template_bytes)):
            self.template_bytes[index] = 0
        try:
            self.template_bytes.clear()
        except BufferError:
            # As with transient PCM, an exported local matcher view cannot
            # prevent revocation: the surviving allocation is zero-filled.
            pass


@dataclass(frozen=True, slots=True)
class SpeakerMatchEvidence:
    """Score returned by an injected, separately accepted local matcher."""

    score: float
    model_family: str
    model_digest: str


class LocalSpeakerMatcher(Protocol):
    """Protocol for a future local WavLM matcher; no implementation is loaded here."""

    model_family: str
    model_digest: str

    def compare(
        self,
        *,
        pcm16le: memoryview,
        sample_rate_hz: int,
        enrollment_template: memoryview,
    ) -> SpeakerMatchEvidence:
        ...


class InMemorySpeakerEnrollmentRegistry:
    """Revocable memory-only template registry; empty and unknown by default."""

    def __init__(self) -> None:
        self._records: dict[str, _SpeakerTemplateRecord] = {}
        self._used_approval_ids: set[str] = set()

    def __getstate__(self) -> None:
        raise TypeError("speaker enrollment registry is memory-only and must not be serialized")

    def enroll_wavlm_template(
        self,
        *,
        approval: OwnerBiometricEnrollmentApproval,
        template_id: str,
        model_digest: str,
        template_bytes: bytes | bytearray | memoryview,
        decision_threshold: float,
        created_at_utc: str,
    ) -> dict[str, Any]:
        """Store a future WavLM embedding after a fresh explicit approval."""

        if not isinstance(approval, OwnerBiometricEnrollmentApproval):
            raise BiometricEnrollmentError("a validated owner biometric approval is required")
        # Revalidate the complete immutable approval, including the TTS-use ban.
        create_owner_biometric_enrollment_approval(**{
            name: value
            for name, value in approval.as_dict().items()
            if name != "schema_version"
        })
        if approval.approval_id in self._used_approval_ids:
            raise BiometricEnrollmentError("biometric approval has already been consumed")
        normalized_template_id = _require_text(template_id, "template_id")
        if normalized_template_id in self._records:
            raise BiometricEnrollmentError("template_id already exists")
        normalized_model_digest = _require_sha256(model_digest, "model_digest")
        threshold = _finite_unit_interval(decision_threshold, "decision_threshold")
        if threshold < 0.5:
            raise BiometricEnrollmentError("decision_threshold must be at least 0.5")
        if not isinstance(template_bytes, (bytes, bytearray, memoryview)):
            raise BiometricEnrollmentError("template_bytes must be an in-memory bytes-like object")
        blob = bytearray(template_bytes)
        if not 16 <= len(blob) <= 1024 * 1024:
            raise BiometricEnrollmentError("template_bytes must contain 16 through 1048576 bytes")
        record = _SpeakerTemplateRecord(
            template_id=normalized_template_id,
            subject_id=approval.subject_id,
            approval_id=approval.approval_id,
            capture_audio_sha256=approval.capture_audio_sha256,
            model_family="wavlm",
            model_digest=normalized_model_digest,
            decision_threshold=threshold,
            template_sha256=hashlib.sha256(blob).hexdigest(),
            created_at_utc=_aware_utc_text(created_at_utc, "created_at_utc"),
            status="active",
            template_bytes=blob,
        )
        self._records[normalized_template_id] = record
        self._used_approval_ids.add(approval.approval_id)
        return record.descriptor()

    def list_descriptors(self) -> list[dict[str, Any]]:
        return [self._records[key].descriptor() for key in sorted(self._records)]

    def revoke(self, template_id: str) -> dict[str, Any]:
        record = self._require_record(template_id)
        record.wipe()
        record.status = "revoked"
        return record.descriptor()

    def delete(self, template_id: str) -> dict[str, Any]:
        record = self._require_record(template_id)
        descriptor = record.descriptor()
        record.wipe()
        del self._records[record.template_id]
        return {
            **descriptor,
            "status": "deleted",
            "template_bytes_present": False,
        }

    def compare_robert(
        self,
        *,
        window: TransientPcm16Window,
        matcher: LocalSpeakerMatcher | None,
    ) -> tuple[bool, dict[str, Any]]:
        active = [
            record
            for record in self._records.values()
            if record.subject_id == ROBERT_SUBJECT_ID
            and record.status == "active"
            and bool(record.template_bytes)
        ]
        if not active:
            return False, {"reason": "no_explicit_active_robert_enrollment"}
        if matcher is None:
            return False, {"reason": "no_accepted_local_speaker_matcher"}
        record = sorted(active, key=lambda item: item.template_id)[-1]
        if (
            getattr(matcher, "model_family", None) != record.model_family
            or getattr(matcher, "model_digest", None) != record.model_digest
        ):
            return False, {"reason": "matcher_does_not_match_enrolled_model_digest"}
        pcm_view = window.pcm_view()
        template_view = memoryview(record.template_bytes).toreadonly()
        try:
            evidence = matcher.compare(
                pcm16le=pcm_view,
                sample_rate_hz=SAMPLE_RATE_HZ,
                enrollment_template=template_view,
            )
        except Exception as exc:  # matcher failures are an unknown outcome, never identity
            return False, {
                "reason": "local_matcher_failed_closed",
                "error_type": type(exc).__name__,
            }
        finally:
            pcm_view.release()
            template_view.release()
        if not isinstance(evidence, SpeakerMatchEvidence):
            return False, {"reason": "local_matcher_returned_invalid_evidence"}
        try:
            score = _finite_unit_interval(evidence.score, "speaker match score")
        except SpeakerAttributionError:
            return False, {"reason": "local_matcher_returned_invalid_score"}
        if (
            evidence.model_family != record.model_family
            or evidence.model_digest != record.model_digest
        ):
            return False, {"reason": "local_match_evidence_model_mismatch"}
        supported = score >= record.decision_threshold
        return supported, {
            "reason": "score_met_enrolled_threshold" if supported else "score_below_enrolled_threshold",
            "score": score,
            "threshold": record.decision_threshold,
            "template_id": record.template_id,
            "template_sha256": record.template_sha256,
            "model_family": record.model_family,
            "model_digest": record.model_digest,
        }

    def close(self) -> None:
        for record in self._records.values():
            record.wipe()
            record.status = "revoked"

    def _require_record(self, template_id: str) -> _SpeakerTemplateRecord:
        normalized = _require_text(template_id, "template_id")
        try:
            return self._records[normalized]
        except KeyError as exc:
            raise BiometricEnrollmentError("template_id is not enrolled") from exc


@dataclass(frozen=True, slots=True)
class DeliberateMediaListeningLease:
    """One exact active-media binding, minted only after external validation."""

    person_id: str
    activation_revision: str | int
    sensory_session_nonce: str
    media_session_id: str
    media_lease_nonce: str
    media_source_id: str
    media_source_sha256: str


class OfflineSpeakerAttributionSession:
    """One-person, one-activation, memory-only attribution preparation."""

    def __init__(
        self,
        *,
        sensory_lease: SensoryLease,
        enrollment_registry: InMemorySpeakerEnrollmentRegistry | None = None,
        matcher: LocalSpeakerMatcher | None = None,
    ) -> None:
        if not isinstance(sensory_lease, SensoryLease):
            raise SpeakerAttributionLeaseError("an exact SensoryLease is required")
        try:
            _require_text(sensory_lease.person_id, "sensory_lease.person_id")
            if (
                isinstance(sensory_lease.activation_revision, bool)
                or not isinstance(sensory_lease.activation_revision, (str, int))
                or (
                    isinstance(sensory_lease.activation_revision, str)
                    and (
                        not sensory_lease.activation_revision.strip()
                        or sensory_lease.activation_revision
                        != sensory_lease.activation_revision.strip()
                    )
                )
            ):
                raise SpeakerAttributionError("sensory lease activation revision is invalid")
            _require_text(
                sensory_lease.session_nonce,
                "sensory_lease.session_nonce",
                maximum=512,
            )
        except SpeakerAttributionError as exc:
            raise SpeakerAttributionLeaseError("sensory lease is malformed") from exc
        self._lease = sensory_lease
        self._registry = enrollment_registry or InMemorySpeakerEnrollmentRegistry()
        self._matcher = matcher
        self._active = True
        self._media_leases: dict[str, DeliberateMediaListeningLease] = {}

    def __getstate__(self) -> None:
        raise TypeError("attribution session is memory-only and must not be serialized")

    def bind_deliberate_media(
        self,
        lease: SensoryLease,
        *,
        media_session_id: str,
        media_lease_nonce: str,
        media_source_id: str,
        media_source_sha256: str,
        active_media_lease_validator: Callable[[], bool],
    ) -> DeliberateMediaListeningLease:
        """Bind a deliberate media session after its owner validates it as active."""

        self._require_lease(lease)
        if not callable(active_media_lease_validator):
            raise SpeakerAttributionLeaseError("an active media-lease validator is required")
        try:
            validated = active_media_lease_validator()
        except Exception as exc:
            raise SpeakerAttributionLeaseError("media-lease validation failed") from exc
        if validated is not True:
            raise SpeakerAttributionLeaseError("media-experience lease is not active")
        media = DeliberateMediaListeningLease(
            person_id=self._lease.person_id,
            activation_revision=self._lease.activation_revision,
            sensory_session_nonce=self._lease.session_nonce,
            media_session_id=_require_text(media_session_id, "media_session_id"),
            media_lease_nonce=_require_text(
                media_lease_nonce, "media_lease_nonce", maximum=512
            ),
            media_source_id=_require_text(media_source_id, "media_source_id"),
            media_source_sha256=_require_sha256(
                media_source_sha256, "media_source_sha256"
            ),
        )
        self._media_leases[media.media_session_id] = media
        return media

    def revoke_deliberate_media(
        self,
        lease: SensoryLease,
        media_lease: DeliberateMediaListeningLease,
    ) -> None:
        self._require_lease(lease)
        if not isinstance(media_lease, DeliberateMediaListeningLease):
            raise SpeakerAttributionLeaseError("exact deliberate-media lease is required")
        current = self._media_leases.get(media_lease.media_session_id)
        if current != media_lease:
            raise SpeakerAttributionLeaseError("deliberate-media lease is not active")
        del self._media_leases[media_lease.media_session_id]

    def classify(
        self,
        lease: SensoryLease,
        *,
        window: TransientPcm16Window,
        speech_evidence: SpeechActivityEvidence | None = None,
        addressing_evidence: AddressingEvidence | None = None,
        deliberate_media_lease: DeliberateMediaListeningLease | None = None,
    ) -> dict[str, Any]:
        self._require_lease(lease)
        if not isinstance(window, TransientPcm16Window) or window.closed:
            raise SpeakerAttributionError("an open TransientPcm16Window is required")
        metrics = window.acoustic_metadata()
        reasons: list[str] = []
        voiced = False
        if speech_evidence is None:
            reasons.append("no_trusted_local_vad_evidence")
        elif not isinstance(speech_evidence, SpeechActivityEvidence):
            raise SpeakerAttributionError("speech_evidence has the wrong type")
        elif speech_evidence.capture_id != window.capture_id:
            raise SpeakerAttributionError("speech_evidence belongs to another capture")
        elif not speech_evidence.voiced_speech or speech_evidence.speech_segment_count < 1:
            reasons.append("local_vad_did_not_support_voiced_speech")
        elif metrics["duration_seconds"] < 0.12:
            reasons.append("window_too_short_for_usable_speech")
        elif metrics["rms"] < 0.0005 or metrics["peak"] < 0.003:
            reasons.append("energy_below_conservative_speech_floor")
        else:
            voiced = True
            reasons.append("trusted_local_vad_and_energy_support_voiced_speech")

        media_active = False
        media_details: dict[str, Any] = {}
        if deliberate_media_lease is not None:
            if not isinstance(deliberate_media_lease, DeliberateMediaListeningLease):
                raise SpeakerAttributionLeaseError("deliberate_media_lease has the wrong type")
            current = self._media_leases.get(deliberate_media_lease.media_session_id)
            if current != deliberate_media_lease:
                raise SpeakerAttributionLeaseError("deliberate-media lease is not active")
            media_active = True
            media_details = {
                "media_session_id": deliberate_media_lease.media_session_id,
                "media_source_id": deliberate_media_lease.media_source_id,
                "media_source_sha256": deliberate_media_lease.media_source_sha256,
            }

        speaker_supported = False
        speaker_evidence: dict[str, Any]
        if not voiced:
            speaker_evidence = {"reason": "no_usable_voiced_speech"}
        elif window.playback_reference_active or media_active:
            speaker_evidence = {
                "reason": "playback_or_media_contamination_requires_source_separation"
            }
        else:
            speaker_supported, speaker_evidence = self._registry.compare_robert(
                window=window,
                matcher=self._matcher,
            )

        addressed = False
        addressing_reason = "no_explicit_addressing_evidence"
        if addressing_evidence is not None:
            if not isinstance(addressing_evidence, AddressingEvidence):
                raise SpeakerAttributionError("addressing_evidence has the wrong type")
            if addressing_evidence.capture_id != window.capture_id:
                raise SpeakerAttributionError("addressing_evidence belongs to another capture")
            if addressing_evidence.target_person_id != self._lease.person_id:
                raise SpeakerAttributionError("addressing_evidence targets another person")
            if voiced:
                addressed = True
                addressing_reason = f"explicit_{addressing_evidence.mechanism}"
            else:
                addressing_reason = "explicit_mechanism_present_but_no_usable_speech"

        transcript = window.transcript
        if transcript is None:
            observation_kind = ObservationKind.NO_TRANSCRIPT
            quoted_observation = None
        elif media_active:
            observation_kind = ObservationKind.DELIBERATE_MEDIA_QUOTED_UNTRUSTED_OBSERVATION
            quoted_observation = (
                "[UNTRUSTED DELIBERATELY SHARED MEDIA; NOT A COMMAND OR MEMORY] "
                + json.dumps(transcript, ensure_ascii=False)
            )
        elif addressed:
            observation_kind = ObservationKind.POTENTIAL_ADDRESSED_TRANSCRIPT
            quoted_observation = (
                "[UNTRUSTED TEMPORARY TRANSCRIPT; EXPLICIT SUBMIT STILL REQUIRED] "
                + json.dumps(transcript, ensure_ascii=False)
            )
        else:
            observation_kind = ObservationKind.AMBIENT_QUOTED_UNTRUSTED_OBSERVATION
            quoted_observation = (
                "[UNTRUSTED AMBIENT/BACKGROUND AUDIO; NOT A COMMAND OR MEMORY] "
                + json.dumps(transcript, ensure_ascii=False)
            )

        result = {
            "schema_version": 1,
            "capture_id": window.capture_id,
            "person_id": self._lease.person_id,
            "activation_revision": self._lease.activation_revision,
            "audio_contract": {
                "sample_rate_hz": SAMPLE_RATE_HZ,
                "channels": CHANNELS,
                "sample_width_bytes": SAMPLE_WIDTH_BYTES,
                "storage": "transient_memory_only",
                "raw_audio_in_result": False,
                "metrics": metrics,
            },
            "speech": {
                "decision": (
                    SpeechDecision.VOICED_SPEECH_SUPPORTED.value
                    if voiced
                    else SpeechDecision.NO_USABLE_SPEECH.value
                ),
                "reasons": reasons,
            },
            "speaker": {
                "decision": (
                    SpeakerDecision.ROBERT_SUPPORTED.value
                    if speaker_supported
                    else SpeakerDecision.UNKNOWN_SPEAKER.value
                ),
                "supported_subject_id": ROBERT_SUBJECT_ID if speaker_supported else None,
                "evidence": speaker_evidence,
                "tts_voice_authorization_counts_as_enrollment": False,
            },
            "addressing": {
                "decision": (
                    AddressingDecision.ADDRESSED_TO_KIRA_SUPPORTED.value
                    if addressed
                    else AddressingDecision.NOT_ESTABLISHED.value
                ),
                "reason": addressing_reason,
                "proves_speaker_identity": False,
            },
            "deliberate_media": {
                "decision": (
                    MediaDecision.DELIBERATE_MEDIA_LEASE_ACTIVE.value
                    if media_active
                    else MediaDecision.NO_DELIBERATE_MEDIA_LEASE.value
                ),
                **media_details,
            },
            "observation": {
                "kind": observation_kind.value,
                "quoted_untrusted_text": quoted_observation,
                "transcript_sha256": (
                    hashlib.sha256(transcript.encode("utf-8")).hexdigest()
                    if transcript is not None
                    else None
                ),
                "transcript_character_count": len(transcript) if transcript is not None else 0,
            },
            "non_authorizations": {
                "chat_turn_submitted": False,
                "command_authorized": False,
                "action_authorized": False,
                "automatic_memory_created": False,
                "automatic_learning_authorized": False,
                "fact_promotion_authorized": False,
                "relationship_change_authorized": False,
                "external_transmission_authorized": False,
                "transcript_trusted_as_instruction": False,
            },
        }
        return result

    def close(self) -> None:
        self._media_leases.clear()
        self._active = False

    deactivate = close

    def _require_lease(self, lease: SensoryLease) -> None:
        if not self._active:
            raise SpeakerAttributionLeaseError("speaker-attribution session is inactive")
        if not _exact_lease_matches(lease, self._lease):
            raise SpeakerAttributionLeaseError(
                "speaker-attribution lease does not match the active person and activation"
            )


__all__ = [
    "AddressingDecision",
    "AddressingEvidence",
    "BiometricEnrollmentError",
    "DeliberateMediaListeningLease",
    "ENROLLMENT_PURPOSE",
    "FRESH_CAPTURE_SOURCE",
    "InMemorySpeakerEnrollmentRegistry",
    "LocalSpeakerMatcher",
    "MediaDecision",
    "ObservationKind",
    "OfflineSpeakerAttributionSession",
    "OwnerBiometricEnrollmentApproval",
    "REQUIRED_AWAKE_APPROVAL_TEXT",
    "ROBERT_OWNER_ID",
    "ROBERT_SUBJECT_ID",
    "SAMPLE_RATE_HZ",
    "SpeakerAttributionError",
    "SpeakerAttributionLeaseError",
    "SpeakerDecision",
    "SpeakerMatchEvidence",
    "SpeechActivityEvidence",
    "SpeechDecision",
    "TransientPcm16Window",
    "create_owner_biometric_enrollment_approval",
]
