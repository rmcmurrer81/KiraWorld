"""Validated application service independent of any neural backend."""

from __future__ import annotations

import re
import math
from dataclasses import replace
from datetime import UTC, datetime
from types import MappingProxyType
from pathlib import Path

from .backends import BackendProtocol, MockBackend
from .backends.base import BackendCapabilities
from .errors import BackendUnavailableError, ValidationError
from .jobs import JobManager
from .models import JobSnapshot, SynthesisRequest, VoiceProfile
from .output import MAX_OUTPUT_BYTES, PublishedOutput, ValidatedOutput, publish_no_replace
from .paths import PinnedDirectory, contained_path, safe_component
from .reference import inspect_wav
from .registry import VoiceRegistry, parse_timestamp
from .reservations import OutputReservation

MAX_TEXT_CHARACTERS = 4_000
MAX_TEXT_UTF8_BYTES = 16_000
MAX_METADATA_ITEMS = 24
MAX_METADATA_VALUE_CHARACTERS = 500
MAX_STORAGE_BYTES = 2 * 1024 * 1024 * 1024
DEFAULT_JOB_TIMEOUT_SECONDS = 120.0
_LANGUAGE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
_STYLE = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")


class LocalVoiceService:
    def __init__(
        self,
        data_root: Path,
        backend: BackendProtocol | None = None,
        *,
        max_storage_bytes: int = MAX_STORAGE_BYTES,
        per_job_reservation_bytes: int = MAX_OUTPUT_BYTES,
    ):
        if str(data_root).startswith("\\\\") or str(data_root).startswith("//"):
            raise ValidationError("local voice data root cannot use a UNC path")
        self.data_root = data_root.expanduser().resolve()
        self.outputs_root = contained_path(self.data_root, "outputs")
        self.receipts_root = contained_path(self.data_root, "receipts")
        self.staging_root = contained_path(self.data_root, "staging")
        self.reservations_root = contained_path(self.data_root, "reservations")
        self.reference_intake_root = contained_path(self.data_root, "reference_intake")
        self.registry = VoiceRegistry(contained_path(self.data_root, "voices"))
        self.backend = backend or MockBackend()
        self.max_storage_bytes = max_storage_bytes
        self.per_job_reservation_bytes = per_job_reservation_bytes
        self.jobs = JobManager(
            self.backend,
            staging_root=self.staging_root,
            authorize=self._authorize_at_execution,
            publisher=self._authorize_and_publish,
            max_jobs=128,
        )
        self.outputs_root.mkdir(parents=True, exist_ok=True)
        self.receipts_root.mkdir(parents=True, exist_ok=True)
        self.reservations_root.mkdir(parents=True, exist_ok=True)
        self.reference_intake_root.mkdir(parents=True, exist_ok=True)
        self._pinned_roots=tuple(PinnedDirectory.capture(path) for path in (
            self.data_root,self.outputs_root,self.receipts_root,self.staging_root,
            self.reservations_root,self.reference_intake_root,self.registry.root,
            self.registry.deactivation_root,
        ))

    def close(self) -> bool:
        return self.jobs.close()

    def health(self) -> dict[str, object]:
        caps = self.backend.capabilities()
        return {
            "status": "ok" if caps.ready else "degraded",
            "local_only": caps.offline and caps.network_access == "none" and caps.telemetry == "none",
            "backend": caps.name,
            "backend_ready": caps.ready,
            "mock_backend": caps.mock,
        }

    def capabilities(self) -> dict[str, object]:
        caps=self.backend.capabilities()
        return {
            "schema": "kira.local-voice.capabilities.v1",
            "local_only": caps.offline and caps.network_access == "none" and caps.telemetry == "none",
            "max_text_characters": MAX_TEXT_CHARACTERS,
            "max_text_utf8_bytes": MAX_TEXT_UTF8_BYTES,
            "request_formats": ["application/json"],
            "backend": caps.to_dict(),
            "provenance_dimensions": {
                "source_basis": ["source_recording_backed", "designed", "generic_fallback"],
                "audition_status": ["not_auditioned", "auditioned", "owner_approved"],
            },
        }

    def register_voice(self, profile: VoiceProfile) -> VoiceProfile:
        return self.registry.register(profile)

    def inspect_reference(self, source_path: Path) -> dict[str, object]:
        self._assert_roots()
        descriptor = inspect_wav(source_path, allowed_root=self.reference_intake_root)
        return {
            "schema": "kira.local-voice.reference-inspection.v1",
            "copied": False,
            "descriptor": descriptor.to_dict(),
        }

    def submit(self, request: SynthesisRequest, *, timeout_seconds: float = DEFAULT_JOB_TIMEOUT_SECONDS) -> JobSnapshot:
        self._assert_roots()
        request = self._validate_request(request)
        voice = self.registry.get(request.voice_id)
        self._authorize_at_execution(voice)
        caps = self.backend.capabilities()
        self._validate_backend_capabilities(caps)
        if request.language not in caps.languages:
            raise ValidationError("backend does not support the requested language")
        if request.voice_id not in caps.voice_ids:
            raise ValidationError("backend does not allow the requested voice")
        if "wav" not in caps.formats:
            raise ValidationError("backend does not support the required WAV format")
        if (
            not isinstance(timeout_seconds, (int, float))
            or isinstance(timeout_seconds, bool)
            or not math.isfinite(float(timeout_seconds))
            or not 1 <= timeout_seconds <= 600
        ):
            raise ValidationError("timeout_seconds must be between 1 and 600")
        if request.output_name is not None:
            safe_component(request.output_name,field="output_name")
        output_stem = request.output_name if request.output_name is not None else f"voice-{__import__('uuid').uuid4().hex}"
        safe_component(output_stem, field="output_name")
        request = replace(request, output_name=output_stem)
        output = contained_path(self.outputs_root, f"{output_stem}.wav")
        if output.exists():
            raise ValidationError(f"output already exists: {output_stem}.wav")
        reservation = OutputReservation.acquire(
            self.reservations_root,
            output_stem,
            outputs_root=self.outputs_root,
            staging_root=self.staging_root,
            max_storage_bytes=self.max_storage_bytes,
            reserved_bytes=self.per_job_reservation_bytes,
        )
        receipt = contained_path(self.receipts_root, f"{__import__('uuid').uuid4().hex}.json")
        try:
            return self.jobs.submit(
                request, voice, output, receipt, reservation, timeout_seconds=float(timeout_seconds)
            )
        except Exception:
            reservation.release()
            raise

    def get_job(self, job_id: str) -> JobSnapshot:
        return self.jobs.snapshot(safe_component(job_id, field="job_id"))

    def cancel_job(self, job_id: str) -> JobSnapshot:
        return self.jobs.cancel(safe_component(job_id, field="job_id"))

    @staticmethod
    def _validate_request(request: SynthesisRequest) -> SynthesisRequest:
        if not isinstance(request.text, str):
            raise ValidationError("text must be a string")
        text = request.text.strip()
        if not text:
            raise ValidationError("text is required")
        if len(text) > MAX_TEXT_CHARACTERS or len(text.encode("utf-8")) > MAX_TEXT_UTF8_BYTES:
            raise ValidationError("text exceeds local synthesis request limits")
        safe_component(request.voice_id, field="voice_id")
        if not isinstance(request.language, str) or not _LANGUAGE.fullmatch(request.language):
            raise ValidationError("language must be a BCP-47-like language tag")
        if (
            not isinstance(request.speed, (int, float))
            or isinstance(request.speed, bool)
            or not math.isfinite(float(request.speed))
            or not 0.5 <= request.speed <= 2.0
        ):
            raise ValidationError("speed must be between 0.5 and 2.0")
        if not isinstance(request.style, str) or not _STYLE.fullmatch(request.style):
            raise ValidationError("style must be a lowercase safe identifier")
        if not isinstance(request.metadata, dict):
            raise ValidationError("metadata must be a JSON object of short string pairs")
        if len(request.metadata) > MAX_METADATA_ITEMS:
            raise ValidationError("metadata contains too many items")
        for key, value in request.metadata.items():
            safe_component(key, field="metadata key")
            if not isinstance(value, str) or len(value) > MAX_METADATA_VALUE_CHARACTERS:
                raise ValidationError("metadata values must be short strings")
        return SynthesisRequest(
            text=text,
            voice_id=request.voice_id,
            output_name=request.output_name,
            language=request.language,
            speed=request.speed,
            style=request.style,
            metadata=MappingProxyType(dict(request.metadata)),
        )

    def _authorize_at_execution(self, expected: VoiceProfile) -> None:
        self._assert_roots()
        current = self.registry.get(expected.voice_id)
        if current.to_dict() != expected.to_dict():
            raise ValidationError("voice registry record changed after job submission")
        if self.registry.is_deactivated(expected.voice_id):
            raise ValidationError("voice is deactivated")
        if not current.consent.generated_audio_permitted:
            raise ValidationError("voice consent does not permit generated audio")
        if current.consent.recorded_at:
            recorded = parse_timestamp(current.consent.recorded_at, field="consent recorded_at")
            if recorded > datetime.now(UTC):
                raise ValidationError("voice consent is dated in the future")
        if current.consent.expires_at is not None:
            expires_at = parse_timestamp(current.consent.expires_at, field="consent expires_at")
            if expires_at <= datetime.now(UTC):
                raise ValidationError(f"voice consent has expired: {current.voice_id}")
        if current.source_basis.value == "source_recording_backed":
            raise ValidationError("source-backed voices require a future core-attested reference handle")

    def _authorize_and_publish(
        self,
        expected: VoiceProfile,
        staging_path: Path,
        final_path: Path,
        checked: ValidatedOutput,
    ) -> PublishedOutput:
        # Deactivation uses the same cross-process mutation guard. Permission
        # revalidation and the no-replace publication therefore happen as one
        # authorization transaction with respect to revocation.
        with self.registry.mutation_guard():
            self._authorize_at_execution(expected)
            return publish_no_replace(staging_path, final_path, checked)

    @staticmethod
    def _validate_backend_capabilities(caps: BackendCapabilities) -> None:
        if not isinstance(caps, BackendCapabilities):
            raise BackendUnavailableError("backend capability contract is invalid")
        if not caps.ready:
            raise BackendUnavailableError("backend is not ready")
        if not caps.offline or caps.network_access != "none" or caps.telemetry != "none":
            raise BackendUnavailableError("backend does not provide enforced local-only execution")
        if (
            not caps.name
            or not caps.version
            or not isinstance(caps.formats,tuple)
            or not isinstance(caps.languages,tuple)
            or not isinstance(caps.voice_ids,tuple)
            or caps.formats != ("wav",)
            or not caps.languages
            or not caps.voice_ids
            or not caps.model_source
            or not caps.model_revision
            or not caps.license_id
            or not caps.provenance_scope
            or caps.provenance_scope == "unspecified"
            or not isinstance(caps.audition_evidence_grants_runtime_access,bool)
            or any(not isinstance(value,bool) for value in (
                caps.ready,caps.voice_cloning,caps.voice_design,caps.mock,caps.offline))
            or any(not isinstance(item, str) or not item for item in caps.languages + caps.voice_ids)
        ):
            raise BackendUnavailableError("backend capability contract is incomplete")

    def _assert_roots(self) -> None:
        for root in self._pinned_roots: root.assert_unchanged()
