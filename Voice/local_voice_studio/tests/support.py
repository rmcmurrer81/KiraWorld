from __future__ import annotations

import hashlib
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kira_local_voice.models import (  # noqa: E402
    AuditionStatus,
    ConsentBasis,
    ConsentRecord,
    SourceBasis,
    VoiceProfile,
)


def generic_voice(voice_id: str = "calm-fallback") -> VoiceProfile:
    return VoiceProfile(
        voice_id=voice_id,
        display_name="Calm local fallback",
        source_basis=SourceBasis.GENERIC_FALLBACK,
        audition_status=AuditionStatus.AUDITIONED,
        consent=ConsentRecord(
            basis=ConsentBasis.GENERIC_NO_IDENTITY,
            subject_id="no-human-identity",
            authority="Kira Labs local design policy",
            scope="Local generated audio; no identity claim",
            recorded_at="2026-08-25T00:00:00Z",
            evidence_sha256=None,
            reference_recording_permitted=False,
            generated_audio_permitted=True,
        ),
    )


def source_voice(reference_hash: str, evidence_hash: str | None = None) -> VoiceProfile:
    return VoiceProfile(
        voice_id="consented-source-v1",
        display_name="Consented source voice",
        source_basis=SourceBasis.SOURCE_RECORDING_BACKED,
        audition_status=AuditionStatus.OWNER_APPROVED,
        consent=ConsentRecord(
            basis=ConsentBasis.SOURCE_SUBJECT_CONSENT,
            subject_id="subject-local-id",
            authority="subject-self-authorization",
            scope="Local synthesis for approved projects",
            recorded_at="2026-08-25T00:00:00Z",
            evidence_sha256=evidence_hash or "e" * 64,
            reference_recording_permitted=True,
            generated_audio_permitted=True,
        ),
        reference_hashes=(reference_hash,),
    )


def write_wav(path: Path, *, seconds: float = 1.0, rate: int = 16_000) -> str:
    frames = int(seconds * rate)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(b"\x00\x00" * frames)
    return hashlib.sha256(path.read_bytes()).hexdigest()
