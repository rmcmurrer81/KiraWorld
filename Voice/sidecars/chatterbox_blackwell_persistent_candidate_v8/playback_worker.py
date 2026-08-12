#!/usr/bin/env python3
"""One-shot synchronous WAV consumer for Blackwell v8.

The only live audio API is Windows ``winsound.PlaySound`` with the already
verified immutable WAV bytes in synchronous memory mode.
There is no TTS, SAPI, generic voice, fallback, model, network, or person-state
path in this process.  It emits API timing truth; it never infers that the
owner heard the speaker.
"""

from __future__ import annotations

import argparse
import array
import hashlib
import io
import json
import math
import os
import sys
import time
import wave
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OWNED_ROOT = (
    PROJECT_ROOT / "RecoverySprint/runtime_cache/blackwell_chatterbox/v8_playback"
).resolve()
MAXIMUM_WAV_BYTES = 52_428_800


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _sha256_file(path: Path) -> tuple[str, bytes]:
    with path.open("rb") as handle:
        raw = handle.read(MAXIMUM_WAV_BYTES + 1)
    if not raw or len(raw) > MAXIMUM_WAV_BYTES:
        raise RuntimeError("playback WAV is empty or oversized")
    return hashlib.sha256(raw).hexdigest(), raw


def _validate_wav(raw: bytes) -> None:
    try:
        with wave.open(io.BytesIO(raw), "rb") as handle:
            channels = handle.getnchannels()
            width = handle.getsampwidth()
            rate = handle.getframerate()
            frames = handle.getnframes()
            compression = handle.getcomptype()
            pcm = handle.readframes(frames)
    except (wave.Error, EOFError, OSError) as exc:
        raise RuntimeError(f"playback WAV is unreadable: {exc}") from exc
    duration = frames / rate if rate else 0.0
    if (
        channels not in {1, 2}
        or width != 2
        or not 16_000 <= rate <= 48_000
        or compression != "NONE"
        or not 0.05 <= duration <= 120.0
        or len(pcm) != frames * channels * width
    ):
        raise RuntimeError("playback WAV structure is outside the sealed bounds")
    samples = array.array("h")
    samples.frombytes(pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    peak = max((abs(value) for value in samples), default=0)
    if peak < 1:
        raise RuntimeError("playback WAV is silent")


def _monotonic() -> float:
    value = float(time.monotonic())
    if not math.isfinite(value) or value < 0:
        raise RuntimeError("playback monotonic clock is invalid")
    return value


def _write(value: dict[str, Any]) -> None:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    if len(payload) > 65_536:
        raise RuntimeError("playback result exceeded its JSON bound")
    sys.stdout.buffer.write(payload + b"\n")
    sys.stdout.buffer.flush()


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--wav", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--generation-id", required=True)
    parser.add_argument("--model-generation", required=True)
    parser.add_argument("--component-fingerprint", required=True)
    parser.add_argument("--playback-id", required=True)
    parser.add_argument("--child-token-hash", required=True)
    args = parser.parse_args()
    bindings = (
        args.sha256,
        args.generation_id,
        args.model_generation,
        args.component_fingerprint,
        args.playback_id,
        args.child_token_hash,
    )
    if not all(_is_sha256(value) for value in bindings):
        raise RuntimeError("playback binding digest is invalid")
    child_token = os.environ.pop("KIRA_V8_PLAYBACK_CHILD_TOKEN", "")
    if hashlib.sha256(child_token.encode("utf-8")).hexdigest() != args.child_token_hash:
        raise RuntimeError("playback one-time child capability mismatch")
    raw_path = Path(args.wav)
    if not raw_path.is_absolute() or raw_path.is_symlink():
        raise RuntimeError("playback WAV path is not absolute/non-symlink")
    path = raw_path.resolve(strict=True)
    try:
        relative = path.relative_to(OWNED_ROOT)
    except ValueError as exc:
        raise RuntimeError("playback WAV escaped the owned root") from exc
    cursor = OWNED_ROOT
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise RuntimeError("playback WAV path contains a symbolic link")
    observed_sha, raw = _sha256_file(path)
    if observed_sha != args.sha256:
        raise RuntimeError("playback WAV SHA-256 changed before API invocation")
    _validate_wav(raw)
    if os.name != "nt":
        raise RuntimeError("v8 live playback is Windows-only")
    import winsound  # Imported only after every byte/path/capability gate.

    started = _monotonic()
    winsound.PlaySound(raw, winsound.SND_MEMORY | winsound.SND_SYNC)
    ended = _monotonic()
    if ended < started:
        raise RuntimeError("playback API interval is invalid")
    if _sha256_file(path)[0] != args.sha256:
        raise RuntimeError("playback WAV changed during API invocation")
    _write(
        {
            "schema_version": 1,
            "playback_id": args.playback_id,
            "artifact_sha256": args.sha256,
            "generation_id": args.generation_id,
            "model_generation": args.model_generation,
            "component_fingerprint": args.component_fingerprint,
            "route": "blackwell_gpu",
            "device": "cuda",
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "playback_api_start_monotonic": started,
            "playback_api_end_monotonic": ended,
            "playback_api_completed": True,
            "owner_hearing_observation": None,
            "owner_hearing_proven": False,
            "wav_byte_length": len(raw),
            "playback_source": "verified_in_memory_wav_bytes",
            "played_memory_sha256": hashlib.sha256(raw).hexdigest(),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
