"""Bounded jobs with verified backend truth and core-owned publication."""

from __future__ import annotations

import math
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from .backends import BackendProtocol, CancellationToken
from .backends.base import BackendCapabilities
from .errors import CancelledError, ConflictError, NotFoundError, ValidationError
from .models import BackendResult, JobSnapshot, JobState, SynthesisRequest, VoiceProfile
from .output import (
    PublishedOutput,
    ValidatedOutput,
    publish_no_replace,
    remove_published_if_owned,
    validate_backend_output,
)
from .paths import atomic_write_json_new
from .reservations import OutputReservation


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _public_request(request: SynthesisRequest) -> dict[str, object]:
    """Return only operational counts and non-secret synthesis controls."""

    return {
        "voice_id": request.voice_id,
        "language": request.language,
        "speed": request.speed,
        "style": request.style,
        "text_characters": len(request.text),
        "metadata_items": len(request.metadata),
    }


def _validate_result_truth(
    result: BackendResult, caps: BackendCapabilities, request: SynthesisRequest
) -> None:
    if not isinstance(result, BackendResult):
        raise ValidationError("backend returned an invalid result contract")
    exact = {
        "backend_name": (result.backend_name, caps.name),
        "backend_version": (result.backend_version, caps.version),
        "format": (result.format, "wav"),
        "model_source": (result.model_source, caps.model_source),
        "model_revision": (result.model_revision, caps.model_revision),
        "voice_id": (result.voice_id, request.voice_id),
        "license_id": (result.license_id, caps.license_id),
        "offline": (result.offline, True),
        "provenance_scope": (result.provenance_scope, caps.provenance_scope),
    }
    if any(actual != expected for actual, expected in exact.values()):
        raise ValidationError("backend result provenance disagrees with capabilities or request")
    if request.voice_id not in caps.voice_ids:
        raise ValidationError("backend result voice is outside the capability allowlist")
    if (
        not isinstance(result.sample_rate_hz, int)
        or isinstance(result.sample_rate_hz, bool)
        or result.sample_rate_hz != 24_000
        or not isinstance(result.duration_seconds, (int, float))
        or isinstance(result.duration_seconds, bool)
        or not math.isfinite(float(result.duration_seconds))
        or result.duration_seconds <= 0
        or not isinstance(result.mock_audio, bool)
        or result.mock_audio != caps.mock
    ):
        raise ValidationError("backend result media contract is invalid")


def _validate_execution_capabilities(
    caps: BackendCapabilities, request: SynthesisRequest
) -> None:
    if (
        not isinstance(caps, BackendCapabilities)
        or not caps.ready
        or not caps.offline
        or caps.network_access != "none"
        or caps.telemetry != "none"
        or not isinstance(caps.formats,tuple)
        or not isinstance(caps.languages,tuple)
        or not isinstance(caps.voice_ids,tuple)
        or caps.formats != ("wav",)
        or request.language not in caps.languages
        or request.voice_id not in caps.voice_ids
        or not caps.name
        or not caps.version
        or not caps.model_source
        or not caps.model_revision
        or not caps.license_id
        or not caps.provenance_scope
        or caps.provenance_scope == "unspecified"
        or not isinstance(caps.audition_evidence_grants_runtime_access, bool)
        or any(not isinstance(value,bool) for value in (
            caps.ready,caps.voice_cloning,caps.voice_design,caps.mock,caps.offline))
    ):
        raise ValidationError("backend execution capabilities are not an enforced local-only contract")


@dataclass(slots=True)
class _Job:
    job_id: str
    state: JobState
    created_at: str
    updated_at: str
    request: SynthesisRequest
    voice: VoiceProfile
    final_path: Path
    staging_path: Path
    receipt_path: Path
    reservation: OutputReservation
    cancel_event: threading.Event
    timeout_seconds: float
    error: dict[str, str] | None = None
    finalized: bool = False


Publisher = Callable[[VoiceProfile, Path, Path, ValidatedOutput], PublishedOutput]


class JobManager:
    def __init__(
        self,
        backend: BackendProtocol,
        *,
        staging_root: Path,
        workers: int = 1,
        max_jobs: int = 128,
        authorize: Callable[[VoiceProfile], None] | None = None,
        publisher: Publisher | None = None,
        receipt_writer: Callable[[Path, dict], None] = atomic_write_json_new,
    ):
        self.backend = backend
        self.staging_root = staging_root.resolve()
        self.staging_root.mkdir(parents=True, exist_ok=True)
        self.max_jobs = max(1, max_jobs)
        self._authorize = authorize
        self._publisher = publisher or (
            lambda _voice, staging, final, checked: publish_no_replace(staging, final, checked)
        )
        self._receipt_writer = receipt_writer
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, workers), thread_name_prefix="local-voice"
        )
        self._jobs: dict[str, _Job] = {}
        self._lock = threading.RLock()
        self._closed = False

    def submit(
        self,
        request: SynthesisRequest,
        voice: VoiceProfile,
        final_path: Path,
        receipt_path: Path,
        reservation: OutputReservation,
        *,
        timeout_seconds: float,
    ) -> JobSnapshot:
        with self._lock:
            if self._closed:
                raise ConflictError("job manager is closed")
            self._prune_terminal_locked()
            if len(self._jobs) >= self.max_jobs:
                raise ConflictError("local synthesis queue is full")
            stamp, job_id = _now(), uuid.uuid4().hex
            job = _Job(
                job_id,
                JobState.QUEUED,
                stamp,
                stamp,
                request,
                voice,
                final_path,
                self.staging_root / f"{job_id}.wav.partial",
                receipt_path,
                reservation,
                threading.Event(),
                timeout_seconds,
            )
            self._jobs[job_id] = job
        try:
            self._executor.submit(self._run, job_id)
        except Exception:
            with self._lock:
                self._jobs.pop(job_id, None)
            reservation.release()
            raise
        return self.snapshot(job_id)

    def snapshot(self, job_id: str) -> JobSnapshot:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise NotFoundError(f"unknown job_id: {job_id}")
            return JobSnapshot(
                job.job_id,
                job.state,
                job.created_at,
                job.updated_at,
                _public_request(job.request),
                job.final_path.name if job.state is JobState.SUCCEEDED else None,
                job.receipt_path.name if job.receipt_path.exists() else None,
                dict(job.error) if job.error else None,
            )

    def cancel(self, job_id: str) -> JobSnapshot:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise NotFoundError(f"unknown job_id: {job_id}")
            if job.state in {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED}:
                raise ConflictError(f"job is already terminal: {job.state.value}")
            job.cancel_event.set()
            job.updated_at = _now()
        return self.snapshot(job_id)

    def wait(self, job_id: str, timeout: float = 10.0) -> JobSnapshot:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            snapshot = self.snapshot(job_id)
            if snapshot.state in {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED}:
                return snapshot
            time.sleep(0.01)
        raise TimeoutError(f"job did not finish within {timeout} seconds")

    def close(self, timeout: float = 5.0) -> bool:
        queued: list[_Job] = []
        with self._lock:
            self._closed = True
            for job in self._jobs.values():
                if job.state is JobState.QUEUED:
                    job.cancel_event.set()
                    job.state = JobState.CANCELLED
                    queued.append(job)
                elif job.state is JobState.RUNNING:
                    job.cancel_event.set()
        for job in queued:
            self._finish(
                job,
                JobState.CANCELLED,
                None,
                None,
                None,
                {"code": "cancelled", "message": "synthesis was cancelled"},
            )
        deadline = time.monotonic() + max(0.0, timeout)
        while time.monotonic() < deadline:
            with self._lock:
                done = all(
                    job.state not in {JobState.QUEUED, JobState.RUNNING}
                    for job in self._jobs.values()
                )
            if done:
                self._executor.shutdown(wait=True, cancel_futures=True)
                return True
            time.sleep(0.01)
        self._executor.shutdown(wait=False, cancel_futures=True)
        return False

    def _run(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            if job.state is not JobState.QUEUED:
                return
            if job.cancel_event.is_set():
                job.state = JobState.CANCELLED
                cancelled_before_start = True
            else:
                job.state, job.updated_at = JobState.RUNNING, _now()
                cancelled_before_start = False
        if cancelled_before_start:
            self._finish(
                job,
                JobState.CANCELLED,
                None,
                None,
                None,
                {"code": "cancelled", "message": "synthesis was cancelled"},
            )
            return

        terminal = JobState.FAILED
        result: BackendResult | None = None
        checked: ValidatedOutput | None = None
        published: PublishedOutput | None = None
        error: dict[str, str] | None = None
        token = CancellationToken(job.cancel_event, time.monotonic() + job.timeout_seconds)
        try:
            if self._authorize:
                self._authorize(job.voice)
            token.raise_if_cancelled()
            caps = self.backend.capabilities()
            _validate_execution_capabilities(caps, job.request)
            result = self.backend.synthesize(job.request, job.voice, job.staging_path, token)
            token.raise_if_cancelled()
            after_caps = self.backend.capabilities()
            _validate_execution_capabilities(after_caps, job.request)
            if after_caps != caps:
                raise ValidationError("backend capabilities changed during synthesis")
            _validate_result_truth(result, after_caps, job.request)
            if self._authorize:
                self._authorize(job.voice)
            checked = validate_backend_output(job.staging_path, self.staging_root, result)
            token.raise_if_cancelled()
            published = self._publisher(job.voice, job.staging_path, job.final_path, checked)
            token.raise_if_cancelled()
            terminal = JobState.SUCCEEDED
        except CancelledError:
            terminal = JobState.CANCELLED
            error = {"code": "cancelled", "message": "synthesis was cancelled or timed out"}
        except Exception:
            terminal = JobState.FAILED
            error = {
                "code": "synthesis_failed",
                "message": "synthesis failed validation or execution",
            }
        finally:
            job.staging_path.unlink(missing_ok=True)
        self._finish(job, terminal, result, checked, published, error)

    def _finish(
        self,
        job: _Job,
        terminal: JobState,
        result: BackendResult | None,
        checked: ValidatedOutput | None,
        published: PublishedOutput | None,
        error: dict[str, str] | None,
    ) -> None:
        with self._lock:
            if job.finalized:
                return
            job.finalized = True
        if terminal is not JobState.SUCCEEDED and published is not None:
            remove_published_if_owned(job.final_path, published)
            published = None
        completed = _now()
        receipt = self._receipt(job, terminal, completed, result, checked, error)
        try:
            self._receipt_writer(job.receipt_path, receipt)
        except Exception:
            cleanup_ok = published is None or remove_published_if_owned(job.final_path, published)
            terminal = JobState.FAILED
            error = {
                "code": "receipt_io_failure",
                "message": "receipt could not be persisted and output was withdrawn"
                if cleanup_ok
                else "receipt could not be persisted; owned-output cleanup was refused",
            }
        finally:
            job.reservation.release()
        with self._lock:
            job.state, job.updated_at, job.error = terminal, completed, error

    @staticmethod
    def _receipt(
        job: _Job,
        terminal: JobState,
        completed: str,
        result: BackendResult | None,
        checked: ValidatedOutput | None,
        error: dict[str, str] | None,
    ) -> dict[str, object]:
        return {
            "schema": "kira.local-voice.receipt.v3",
            "job_id": job.job_id,
            "state": terminal.value,
            "created_at": job.created_at,
            "completed_at": completed,
            "request": _public_request(job.request),
            "voice": {
                "voice_id": job.voice.voice_id,
                "source_basis": job.voice.source_basis.value,
                "audition_status": job.voice.audition_status.value,
            },
            "backend": result.to_dict() if result else None,
            "output": None
            if terminal is not JobState.SUCCEEDED or checked is None
            else {
                "relative_name": job.final_path.name,
                "sha256": checked.sha256,
                "bytes": checked.bytes,
                "duration_seconds": checked.duration_seconds,
                "sample_rate_hz": checked.sample_rate_hz,
            },
            "error": error,
        }

    def _prune_terminal_locked(self) -> None:
        if len(self._jobs) < self.max_jobs:
            return
        for job_id, job in sorted(self._jobs.items(), key=lambda pair: pair[1].updated_at):
            if job.state in {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED}:
                self._jobs.pop(job_id, None)
                if len(self._jobs) < self.max_jobs:
                    return
