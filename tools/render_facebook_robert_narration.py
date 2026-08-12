"""Render two local owner-review narration drafts with Robert's approved self voice.

This intentionally changes loudness and close-mic bass only.  It never changes
pitch, and it fails closed if the approved reference or Chatterbox is missing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.dialogue_audio_signal import gentle_proximity_correction
from Core.voice_output import VoiceOutputConfig, release_voice_output, synthesize_text_to_wav


REFERENCE = ROOT / "Voice/reference_packs/robert_mcmurrer/robert_mcmurrer_online_source_20260714_230541/model_input/approved_reference.wav"
AUTHORIZATION = ROOT / "Voice/authorizations/robert_self_voice_runtime_approval_20260717.json"
SCRIPTS = {
    "now": ROOT / "Data/codex_reports/facebook_assets/robert_narration_now.txt",
    "future": ROOT / "Data/codex_reports/facebook_assets/robert_narration_future.txt",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_owner_review_authorization() -> dict[str, object]:
    """Fail closed unless the authorization binds this exact review-only reference."""
    authorization = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    allowed = authorization.get("allowed", {})
    binding = authorization.get("binding", {})
    expected_reference = str(REFERENCE.relative_to(ROOT)).replace("\\", "/")
    if not isinstance(allowed, dict) or allowed.get("offline_nonplaying_owner_review_wav") is not True:
        raise ValueError("Authorization does not allow offline nonplaying owner-review WAV output.")
    if not isinstance(binding, dict) or binding.get("approved_reference_wav") != expected_reference:
        raise ValueError("Authorization is not bound to the configured Robert reference WAV.")
    if binding.get("approved_reference_sha256") != sha256(REFERENCE):
        raise ValueError("Configured Robert reference WAV does not match the authorized SHA-256.")
    return authorization


def postprocess(raw_path: Path, final_path: Path, *, gain_db: float) -> dict[str, float | int]:
    audio, sample_rate = sf.read(raw_path, dtype="float32", always_2d=False)
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1, dtype=np.float32)
    audio = gentle_proximity_correction(audio, sample_rate=sample_rate, cutoff_hz=95.0, mix=0.30)
    audio = np.clip(audio * math.pow(10.0, gain_db / 20.0), -0.98, 0.98).astype(np.float32)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    partial = final_path.with_suffix(".partial.wav")
    sf.write(partial, audio, sample_rate, subtype="PCM_16")
    partial.replace(final_path)
    return {
        "sample_rate": int(sample_rate),
        "frames": int(len(audio)),
        "duration_seconds": round(len(audio) / sample_rate, 3),
        "peak": round(float(np.max(np.abs(audio))) if len(audio) else 0.0, 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    parser.add_argument("--gain-db", type=float, default=-9.5)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "Voice/generated/facebook/robert_20260718")
    args = parser.parse_args()
    if not REFERENCE.exists() or not AUTHORIZATION.exists():
        print("Approved Robert reference or runtime authorization is missing.", file=sys.stderr)
        return 2
    try:
        authorization = validate_owner_review_authorization()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Owner-review voice authorization validation failed: {exc}", file=sys.stderr)
        return 2
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    config = VoiceOutputConfig(
        enabled=True,
        engine="chatterbox_tts",
        max_chars=0,
        chatterbox_reference_audio=str(REFERENCE.relative_to(ROOT)).replace("\\", "/"),
        chatterbox_device=args.device,
        output_dir=str(output_dir.relative_to(ROOT)).replace("\\", "/"),
        play_audio=False,
    )
    records: list[dict[str, object]] = []
    try:
        for label, script_path in SCRIPTS.items():
            text = script_path.read_text(encoding="utf-8").strip()
            raw_path = output_dir / f"robert_{label}_raw.wav"
            final_path = output_dir / f"robert_{label}_narration.wav"
            result = synthesize_text_to_wav(text, raw_path, config)
            if not result.get("generated"):
                print(json.dumps(result, indent=2), file=sys.stderr)
                return 3
            signal = postprocess(raw_path, final_path, gain_db=args.gain_db)
            raw_path.unlink(missing_ok=True)
            records.append(
                {
                    "label": label,
                    "script": str(script_path.relative_to(ROOT)).replace("\\", "/"),
                    "script_sha256": sha256(script_path),
                    "output": str(final_path.relative_to(ROOT)).replace("\\", "/"),
                    "output_sha256": sha256(final_path),
                    "chatterbox_result": result,
                    "signal": signal,
                }
            )
    finally:
        release_voice_output()
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "generated_owner_review_required",
        "voice": "Robert McMurrer approved self-voice reference",
        "reference": str(REFERENCE.relative_to(ROOT)).replace("\\", "/"),
        "reference_sha256": sha256(REFERENCE),
        "authorization": str(AUTHORIZATION.relative_to(ROOT)).replace("\\", "/"),
        "authorization_status": authorization.get("status"),
        "authorization_scope": "offline nonplaying owner review only",
        "public_release_authorized": False,
        "public_release_gate": "Robert must listen to and explicitly approve the exact final MP4 by filename and SHA-256 before public posting.",
        "gain_db": args.gain_db,
        "pitch_changed": False,
        "proximity_correction": {"cutoff_hz": 95.0, "dry_highpass_mix": 0.30},
        "human_listening_verified": False,
        "records": records,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
