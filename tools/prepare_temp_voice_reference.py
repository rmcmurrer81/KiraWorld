"""Prepare a bounded, reviewable mono PCM voice reference.

This helper performs only deterministic signal cleanup.  It does not identify
a speaker, approve a source, train a model, or activate a TemporaryAI.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal


def _resample(samples: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate == target_rate:
        return samples
    divisor = int(np.gcd(source_rate, target_rate))
    return signal.resample_poly(samples, target_rate // divisor, source_rate // divisor)


def prepare(source: Path, output: Path, *, notch_hz: list[float]) -> dict:
    samples, source_rate = sf.read(source, dtype="float32", always_2d=True)
    mono = samples.mean(axis=1)
    mono = _resample(mono, int(source_rate), 24000).astype(np.float64, copy=False)

    # Remove sub-voice rumble and inaudible/high-frequency source residue while
    # retaining the speech band used by the local reference TTS backend.
    mono = signal.sosfiltfilt(signal.butter(4, (70.0, 10500.0), btype="bandpass", fs=24000, output="sos"), mono)
    for frequency in notch_hz:
        b, a = signal.iirnotch(frequency, 24.0, fs=24000)
        mono = signal.filtfilt(b, a, mono)

    peak_before = float(np.max(np.abs(mono))) if mono.size else 0.0
    if peak_before > 0:
        mono *= (10.0 ** (-3.0 / 20.0)) / peak_before
    mono = np.clip(mono, -1.0, 1.0)
    output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output, mono.astype(np.float32), 24000, subtype="PCM_16")
    return {
        "source": str(source),
        "output": str(output),
        "source_rate_hz": int(source_rate),
        "output_rate_hz": 24000,
        "channels": 1,
        "sample_width_bits": 16,
        "duration_seconds": round(len(mono) / 24000.0, 3),
        "notch_hz": notch_hz,
        "peak_before_normalization": round(peak_before, 6),
        "identity_or_approval_inferred": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--notch-hz", type=float, action="append", default=[])
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output, notch_hz=args.notch_hz), indent=2))


if __name__ == "__main__":
    main()
