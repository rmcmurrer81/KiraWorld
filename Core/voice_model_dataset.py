"""Prepare reviewed target-only clips for a configurable local voice model."""
from __future__ import annotations

import shutil
import wave
from pathlib import Path
from typing import Any

from Core.voice_reference_pipeline import APPROVED_AUTHORIZATION, PROJECT_ROOT, read_json, relative, write_json


def prepare_model_reference(pack_dir: Path) -> dict[str, Any]:
    pack_dir = pack_dir.resolve()
    manifest = read_json(pack_dir / "voice_reference_manifest.json", {})
    if not manifest:
        raise FileNotFoundError(f"No voice_reference_manifest.json in {pack_dir}")
    authorization = str(manifest.get("source", {}).get("authorization_status", "review_required"))
    clips = [clip for clip in manifest.get("audio", {}).get("clips", []) if clip.get("review_status") == "approved_target"]
    total_seconds = round(sum(float(clip.get("duration_seconds", 0)) for clip in clips), 2)
    if authorization not in APPROVED_AUTHORIZATION:
        raise ValueError("Pack authorization must be owned, licensed, authorized, or self_recorded.")
    if total_seconds < 20:
        raise ValueError(f"At least 20 seconds of approved target-only speech is required; found {total_seconds}.")
    output = pack_dir / "model_input"
    wav_dir = output / "approved_wavs"
    if output.exists():
        shutil.rmtree(output)
    wav_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for clip in clips:
        source = PROJECT_ROOT / str(clip["path"])
        if not source.exists():
            raise FileNotFoundError(f"Approved clip is missing: {source}")
        target = wav_dir / source.name
        shutil.copy2(source, target)
        copied.append(target)
    combined = output / "approved_reference.wav"
    _combine_wavs(copied, combined)
    request = {
        "schema_version": 1,
        "target": manifest.get("target", {}),
        "reference_audio": relative(combined),
        "approved_clip_count": len(copied),
        "approved_seconds": total_seconds,
        "language": "en",
        "model_backend": "not_configured",
        "status": "reference_ready_backend_needed",
        "note": "Use this reviewed reference with a separately installed local model backend. Raw source audio is never passed through.",
    }
    write_json(output / "voice_model_request.json", request)
    return request


def _combine_wavs(sources: list[Path], destination: Path) -> None:
    parameters: tuple[int, int, int] | None = None
    frames: list[bytes] = []
    for source in sources:
        with wave.open(str(source), "rb") as reader:
            current = (reader.getnchannels(), reader.getsampwidth(), reader.getframerate())
            if parameters is None:
                parameters = current
            if current != parameters:
                raise ValueError("Approved WAV clips must share channels, sample width, and sample rate.")
            frames.append(reader.readframes(reader.getnframes()))
    if not parameters:
        raise ValueError("No approved WAV clips were supplied.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as writer:
        writer.setnchannels(parameters[0]); writer.setsampwidth(parameters[1]); writer.setframerate(parameters[2]); writer.writeframes(b"".join(frames))
