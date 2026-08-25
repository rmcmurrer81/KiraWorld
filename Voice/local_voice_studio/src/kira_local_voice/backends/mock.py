"""Deterministic contract backend. It never runs a model or imitates a person."""

from __future__ import annotations

import os
import tempfile
import time
import wave
from pathlib import Path
from datetime import UTC,datetime

from ..models import (AuditionStatus,BackendResult,ConsentBasis,ConsentRecord,SourceBasis,
                      SynthesisRequest,VoiceProfile)
from .base import BackendCapabilities, CancellationToken


class MockBackend:
    def __init__(self, *, step_delay_seconds: float = 0.0, steps: int = 4):
        self.step_delay_seconds = max(0.0, step_delay_seconds)
        self.steps = max(1, steps)

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            name="contract-mock",
            version="1.0",
            ready=True,
            formats=("wav",),
            languages=("en-US",),
            voice_cloning=False,
            voice_design=False,
            mock=True,
            offline=True,
            network_access="none",
            telemetry="none",
            model_source="contract-test-only",
            model_revision="1",
            license_id="internal-contract-test",
            voice_ids=("calm-fallback",),
            provenance_scope="silent_contract_test_only",
        )

    def synthesize(
        self,
        request: SynthesisRequest,
        voice: VoiceProfile,
        output_path: Path,
        cancellation: CancellationToken,
    ) -> BackendResult:
        del voice
        for _ in range(self.steps):
            cancellation.raise_if_cancelled()
            if self.step_delay_seconds:
                time.sleep(self.step_delay_seconds)
        cancellation.raise_if_cancelled()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent)
        os.close(fd)
        temp_path = Path(temporary)
        sample_rate = 24_000
        # A valid, clearly marked silent WAV proves transport and lifecycle only.
        duration = min(0.25, max(0.05, len(request.text) / 50_000))
        frames = int(sample_rate * duration)
        try:
            with wave.open(str(temp_path), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(sample_rate)
                audio.writeframes(b"\x00\x00" * frames)
            cancellation.raise_if_cancelled()
            os.replace(temp_path, output_path)
        finally:
            temp_path.unlink(missing_ok=True)

        return BackendResult(
            format="wav",
            sample_rate_hz=sample_rate,
            duration_seconds=round(frames / sample_rate, 6),
            backend_name="contract-mock",
            backend_version="1.0",
            mock_audio=True,
            model_source="contract-test-only",
            model_revision="1",
            voice_id=request.voice_id,
            license_id="internal-contract-test",
            offline=True,
            provenance_scope="silent_contract_test_only",
        )

def contract_mock_profile() -> VoiceProfile:
    return VoiceProfile("calm-fallback","Contract mock silence",SourceBasis.GENERIC_FALLBACK,
        AuditionStatus.NOT_AUDITIONED,
        ConsentRecord(ConsentBasis.GENERIC_NO_IDENTITY,"no-human-identity","Kira Labs contract test",
            "Silent transport test only",datetime.now(UTC).isoformat().replace("+00:00","Z"),None,
            False,True),description="Silent WAV contract test; not a real voice.")
