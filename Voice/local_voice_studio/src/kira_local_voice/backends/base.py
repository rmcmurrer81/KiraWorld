"""Backend contract; neural engines plug in here without entering the API layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event
from time import monotonic
from typing import Protocol

from ..errors import CancelledError
from ..models import BackendResult, SynthesisRequest, VoiceProfile


@dataclass(frozen=True, slots=True)
class BackendCapabilities:
    name: str
    version: str
    ready: bool
    formats: tuple[str, ...]
    languages: tuple[str, ...]
    voice_cloning: bool
    voice_design: bool
    mock: bool
    offline: bool = True
    network_access: str = "none"
    telemetry: str = "none"
    model_source: str = "none"
    model_revision: str = "none"
    license_id: str = "none"
    voice_ids: tuple[str, ...] = ()
    provenance_scope: str = "unspecified"
    audition_evidence_revision: str | None = None
    audition_evidence_grants_runtime_access: bool = False
    unavailable_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "ready": self.ready,
            "formats": list(self.formats),
            "languages": list(self.languages),
            "voice_cloning": self.voice_cloning,
            "voice_design": self.voice_design,
            "mock": self.mock,
            "offline": self.offline,
            "network_access": self.network_access,
            "telemetry": self.telemetry,
            "model_source": self.model_source,
            "model_revision": self.model_revision,
            "license_id": self.license_id,
            "voice_ids": list(self.voice_ids),
            "provenance_scope": self.provenance_scope,
            "audition_evidence_revision": self.audition_evidence_revision,
            "audition_evidence_grants_runtime_access": self.audition_evidence_grants_runtime_access,
            "unavailable_reason": self.unavailable_reason,
        }


class CancellationToken:
    def __init__(self, event: Event, deadline: float | None = None):
        self._event = event
        self._deadline = deadline

    @property
    def cancelled(self) -> bool:
        return self._event.is_set() or (self._deadline is not None and monotonic() >= self._deadline)

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise CancelledError("synthesis job was cancelled")


class BackendProtocol(Protocol):
    def capabilities(self) -> BackendCapabilities: ...

    def synthesize(
        self,
        request: SynthesisRequest,
        voice: VoiceProfile,
        output_path: Path,
        cancellation: CancellationToken,
    ) -> BackendResult: ...
