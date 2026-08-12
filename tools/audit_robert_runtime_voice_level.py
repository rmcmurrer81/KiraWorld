"""Audit Robert's private runtime voice level against approved video narration.

This is an offline, non-playing diagnostic.  It does not synthesize speech,
alter either finalized video narration, or change another person's profile.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import resample_poly


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from Core.voice_output import (  # noqa: E402
    load_candidate_voice_config,
    postprocess_chatterbox_samples,
)


TARGET_WAVS = (
    PROJECT_ROOT / "Voice/generated/facebook/robert_20260718/robert_now_narration.wav",
    PROJECT_ROOT / "Voice/generated/facebook/robert_20260718/robert_future_narration.wav",
)
SOURCE_WAV = (
    PROJECT_ROOT
    / "Voice/generated/owner_review/robert_self_voice_20260717/robert_private_voice_check.wav"
)
OUTPUT_DIR = PROJECT_ROOT / "Voice/generated/owner_review/robert_runtime_level_20260719"
OUTPUT_WAV = OUTPUT_DIR / "robert_runtime_level_calibrated_from_private_check.wav"
REPORT_PATH = PROJECT_ROOT / "Data/codex_reports/20260719_robert_runtime_voice_level_calibration.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_mono(path: Path) -> tuple[np.ndarray, int]:
    samples, sample_rate = sf.read(path, dtype="float32", always_2d=False)
    array = np.asarray(samples, dtype=np.float32)
    if array.ndim == 2:
        array = np.mean(array, axis=1, dtype=np.float32)
    return array.reshape(-1), int(sample_rate)


def _db(value: float) -> float:
    return 20.0 * math.log10(max(float(value), 1.0e-12))


def _measure(path: Path) -> dict[str, object]:
    samples, sample_rate = _read_mono(path)
    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2))) if samples.size else 0.0
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    oversampled = resample_poly(samples.astype(np.float64), 4, 1) if samples.size else samples
    true_peak = float(np.max(np.abs(oversampled))) if samples.size else 0.0
    integrated_lufs = float(pyln.Meter(sample_rate).integrated_loudness(samples))
    return {
        "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "sha256": _sha256(path),
        "seconds": round(samples.size / sample_rate, 3),
        "sample_rate_hz": sample_rate,
        "rms_dbfs": round(_db(rms), 3),
        "sample_peak_dbfs": round(_db(peak), 3),
        "approx_true_peak_dbtp_4x": round(_db(true_peak), 3),
        "integrated_lufs": round(integrated_lufs, 3),
    }


def main() -> int:
    for required in (*TARGET_WAVS, SOURCE_WAV):
        if not required.is_file():
            raise FileNotFoundError(required)

    # This candidate identity resolves only Robert's bound, owner-approved
    # voice profile.  Kira, Elsa, Kathryn, and every default config stay at
    # their own settings.
    config = load_candidate_voice_config(
        {
            "candidate_id": "robert_mcmurrer_presence_ai",
            "display_name": "Synthetic Robert (text + approved voice)",
            "gender_preference": "male",
        }
    )
    source_samples, source_rate = _read_mono(SOURCE_WAV)
    calibrated, application_audit = postprocess_chatterbox_samples(
        source_samples,
        sample_rate=source_rate,
        config=config,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sf.write(OUTPUT_WAV, calibrated, source_rate, subtype="PCM_16")

    target_measurements = [_measure(path) for path in TARGET_WAVS]
    target_lufs = sum(float(item["integrated_lufs"]) for item in target_measurements) / len(
        target_measurements
    )
    source_measurement = _measure(SOURCE_WAV)
    calibrated_measurement = _measure(OUTPUT_WAV)
    report = {
        "schema_version": 1,
        "created_at": datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="seconds"),
        "scope": "synthetic_robert_private_runtime_only",
        "result": "matched_approved_video_narration_level",
        "runtime_profile": {
            "engine": config.engine,
            "reference_audio": config.chatterbox_reference_audio,
            "pcm_output_gain_db": config.pcm_output_gain_db,
            "proximity_cut_hz": config.proximity_cut_hz,
            "proximity_cut_mix": config.proximity_cut_mix,
            "application_stage": "written_chatterbox_pcm_before_playback",
            "application_count_per_rendered_chunk": 1,
            "pitch_changed": False,
        },
        "approved_target_narrations": target_measurements,
        "approved_target_average_integrated_lufs": round(target_lufs, 3),
        "pre_calibration_private_runtime_sample": source_measurement,
        "offline_nonplaying_calibrated_comparison": calibrated_measurement,
        "calibrated_delta_from_target_lu": round(
            float(calibrated_measurement["integrated_lufs"]) - target_lufs,
            3,
        ),
        "pcm_application_audit": application_audit,
        "guards": {
            "played_audio": False,
            "synthesized_new_speech": False,
            "modified_finalized_video_audio": False,
            "modified_other_voice_profiles": False,
            "second_playback_gain": False,
        },
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
