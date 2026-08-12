#!/usr/bin/env python3
"""Compile a fail-closed, exact-WAV viseme timeline from phone alignment.

This host-side tool does not launch Blender and does not alter an avatar.  It
binds an already-produced phone alignment to an exact WAV and transcript, then
creates bounded AH/EE/O/FV/MBP and jaw-open samples for later private Blender
review.  It intentionally refuses to estimate phone timing from text length or
audio amplitude: a successful forced-alignment artifact is required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import wave
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
CHANNELS = ("AH", "EE", "O", "FV", "MBP", "JAW_OPEN")
SILENCE_PHONES = {"", "SIL", "SP", "SPN", "PAU"}
PHONE_TO_VISEME = {
    # Bilabial closure.
    "M": "MBP",
    "B": "MBP",
    "P": "MBP",
    # Labiodental contact.
    "F": "FV",
    "V": "FV",
    # Front/spread vowels and palatal approximant.
    "IY": "EE",
    "IH": "EE",
    "EY": "EE",
    "EH": "EE",
    "AE": "EE",
    "Y": "EE",
    # Rounded/back vowels and labiovelar approximant.
    "OW": "O",
    "AO": "O",
    "UH": "O",
    "UW": "O",
    "OY": "O",
    "W": "O",
    # Open/central/rhotic vowels.  Diphthongs use one bounded review channel;
    # a later expanded rig may split their trajectories without changing this
    # exact source binding.
    "AA": "AH",
    "AH": "AH",
    "AX": "AH",
    "ER": "AH",
    "AY": "AH",
    "AW": "AH",
    # The five-pose review set has no dedicated consonant shapes.  These
    # consonants keep lip channels neutral and receive only a small jaw carry.
    "CH": None,
    "D": None,
    "DH": None,
    "G": None,
    "HH": None,
    "JH": None,
    "K": None,
    "L": None,
    "N": None,
    "NG": None,
    "R": None,
    "S": None,
    "SH": None,
    "T": None,
    "TH": None,
    "Z": None,
    "ZH": None,
}

ENVELOPE_SECONDS = {
    "AH": (0.070, 0.090),
    "EE": (0.065, 0.085),
    "O": (0.075, 0.095),
    "FV": (0.045, 0.050),
    "MBP": (0.040, 0.035),
}
JAW_CONTRIBUTION = {
    "AH": 0.85,
    "EE": 0.34,
    "O": 0.54,
    "FV": 0.08,
    "MBP": 0.04,
    None: 0.12,
}


class TimelineError(RuntimeError):
    """The proposed timeline cannot be bound truthfully or safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wav_record(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as stream:
        channels = int(stream.getnchannels())
        sample_width = int(stream.getsampwidth())
        sample_rate = int(stream.getframerate())
        frames = int(stream.getnframes())
        compression = stream.getcomptype()
    if channels != 1:
        raise TimelineError(f"exact review WAV must be mono, got {channels} channels")
    if sample_width != 2:
        raise TimelineError(
            f"exact review WAV must be 16-bit PCM, got {sample_width} bytes/sample"
        )
    if compression != "NONE":
        raise TimelineError(f"compressed WAV is not accepted: {compression}")
    if sample_rate <= 0 or frames <= 0:
        raise TimelineError("WAV has no usable PCM frames")
    return {
        "path": path.as_posix(),
        "sha256": sha256_file(path),
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate": sample_rate,
        "frames": frames,
        "duration_seconds": frames / sample_rate,
    }


def normalized_phone(value: object) -> str:
    return re.sub(r"[0-9]+$", "", str(value or "").strip().upper())


def load_and_validate_alignment(
    path: Path,
    *,
    wav: dict[str, Any],
    transcript_sha256: str,
    fps: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    alignment = json.loads(path.read_text(encoding="utf-8"))
    if alignment.get("schema_version") != 1:
        raise TimelineError("alignment schema_version must be 1")
    if alignment.get("status") != "passed":
        raise TimelineError("alignment status is not passed")
    if alignment.get("wav_sha256") != wav["sha256"]:
        raise TimelineError("alignment is not bound to the exact WAV")
    if alignment.get("transcript_sha256") != transcript_sha256:
        raise TimelineError("alignment is not bound to the exact transcript")
    if float(alignment.get("word_coverage", 0.0)) < 1.0:
        raise TimelineError("forced alignment does not cover every transcript word")
    if list(alignment.get("oov_words") or []):
        raise TimelineError("forced alignment contains out-of-vocabulary words")
    source = str(alignment.get("source") or "")
    if not source:
        raise TimelineError("alignment source is missing")

    raw_phones = alignment.get("phones")
    if not isinstance(raw_phones, list) or not raw_phones:
        raise TimelineError("alignment contains no phone intervals")

    phones: list[dict[str, Any]] = []
    previous_start = -1.0
    previous_end = 0.0
    duration = float(wav["duration_seconds"])
    tolerance = 1.0 / fps
    for index, raw in enumerate(raw_phones):
        if not isinstance(raw, dict):
            raise TimelineError(f"phone interval {index} is not an object")
        phone = normalized_phone(raw.get("phone"))
        start = float(raw.get("start_seconds"))
        end = float(raw.get("end_seconds"))
        if not math.isfinite(start) or not math.isfinite(end):
            raise TimelineError(f"phone interval {index} contains a non-finite time")
        if start < -tolerance or end <= start or end > duration + tolerance:
            raise TimelineError(
                f"phone interval {index} lies outside exact WAV bounds: {start}..{end}"
            )
        if start + tolerance < previous_start:
            raise TimelineError("phone intervals are not ordered")
        if start < previous_end - 0.020:
            raise TimelineError("phone intervals overlap by more than 20 ms")
        if phone not in SILENCE_PHONES and phone not in PHONE_TO_VISEME:
            raise TimelineError(f"unsupported phone {phone!r}; do not guess its viseme")
        phones.append(
            {
                "phone": phone,
                "word": str(raw.get("word") or ""),
                "start_seconds": max(0.0, start),
                "end_seconds": min(duration, end),
                "viseme": None if phone in SILENCE_PHONES else PHONE_TO_VISEME[phone],
            }
        )
        previous_start = start
        previous_end = max(previous_end, end)
    return alignment, phones


def smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def phone_envelope(phone: dict[str, Any], seconds: float) -> float:
    viseme = phone["viseme"]
    if viseme is None:
        return 0.0
    start = float(phone["start_seconds"])
    end = float(phone["end_seconds"])
    attack, release = ENVELOPE_SECONDS[viseme]
    attack_start = max(0.0, start - attack)
    release_end = end + release
    if seconds < attack_start or seconds > release_end:
        return 0.0
    if seconds < start:
        return smoothstep((seconds - attack_start) / max(start - attack_start, 1e-9))
    if seconds <= end:
        # Contact shapes must become explicit rather than merely approaching
        # closure/contact asymptotically.
        return 1.0
    return 1.0 - smoothstep((seconds - end) / max(release_end - end, 1e-9))


def sample_weights(phones: list[dict[str, Any]], seconds: float) -> dict[str, float]:
    lip = {name: 0.0 for name in CHANNELS if name != "JAW_OPEN"}
    jaw = 0.0
    for phone in phones:
        start = float(phone["start_seconds"])
        end = float(phone["end_seconds"])
        viseme = phone["viseme"]
        if viseme is not None:
            amount = phone_envelope(phone, seconds)
            lip[viseme] = max(lip[viseme], amount)
            jaw = max(jaw, amount * JAW_CONTRIBUTION[viseme])
        elif start <= seconds <= end and phone["phone"] not in SILENCE_PHONES:
            jaw = max(jaw, JAW_CONTRIBUTION[None])

    # FV and MBP are contact constraints.  Preserve their peak and fit any
    # anticipatory/release vowel contribution into the remaining unit range.
    contact = max(lip["FV"], lip["MBP"])
    if lip["FV"] and lip["MBP"]:
        if lip["FV"] >= lip["MBP"]:
            lip["MBP"] = min(lip["MBP"], 1.0 - lip["FV"])
        else:
            lip["FV"] = min(lip["FV"], 1.0 - lip["MBP"])
        contact = lip["FV"] + lip["MBP"]
    vowel_total = lip["AH"] + lip["EE"] + lip["O"]
    vowel_budget = max(0.0, 1.0 - contact)
    if vowel_total > vowel_budget and vowel_total > 0.0:
        scale = vowel_budget / vowel_total
        for name in ("AH", "EE", "O"):
            lip[name] *= scale
    lip["JAW_OPEN"] = min(1.0, max(0.0, jaw))
    return {name: round(float(lip[name]), 6) for name in CHANNELS}


def build_timeline(
    *,
    wav_path: Path,
    transcript: str,
    alignment_path: Path,
    fps: int,
) -> dict[str, Any]:
    if fps < 24 or fps > 120:
        raise TimelineError("fps must be between 24 and 120")
    wav = wav_record(wav_path)
    transcript_hash = sha256_text(transcript)
    alignment, phones = load_and_validate_alignment(
        alignment_path,
        wav=wav,
        transcript_sha256=transcript_hash,
        fps=fps,
    )
    duration = float(wav["duration_seconds"])
    last_frame = int(math.ceil(duration * fps))
    samples = []
    for frame in range(last_frame + 1):
        seconds = min(duration, frame / fps)
        samples.append(
            {
                "frame": frame,
                "seconds": round(seconds, 9),
                "weights": sample_weights(phones, seconds),
            }
        )

    # The saved candidate must begin and end in the exact approved rest face.
    zero = {name: 0.0 for name in CHANNELS}
    samples[0]["weights"] = dict(zero)
    samples[-1]["weights"] = dict(zero)
    peaks = {
        name: max(sample["weights"][name] for sample in samples)
        for name in CHANNELS
    }
    present = {phone["viseme"] for phone in phones if phone["viseme"] is not None}
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "KIRA_EXACT_WAV_FIVE_VISEME_COARTICULATION_TIMELINE",
        "status": "PROPOSED_PRIVATE_INACTIVE_TIMELINE_NOT_BODY_OR_RUNTIME_ACCEPTANCE",
        "source_wav": wav,
        "transcript": transcript,
        "transcript_sha256": transcript_hash,
        "alignment": {
            "path": alignment_path.as_posix(),
            "sha256": sha256_file(alignment_path),
            "source": alignment["source"],
            "status": alignment["status"],
            "word_coverage": alignment["word_coverage"],
            "oov_words": alignment.get("oov_words") or [],
        },
        "fps": fps,
        "channels": list(CHANNELS),
        "phones": phones,
        "samples": samples,
        "peak_weights": peaks,
        "present_visemes": sorted(present),
        "gates": {
            "exact_wav_hash_bound": True,
            "exact_transcript_hash_bound": True,
            "forced_alignment_required": True,
            "text_length_timing_used": False,
            "amplitude_only_timing_used": False,
            "first_and_last_samples_exact_rest": samples[0]["weights"] == zero
            and samples[-1]["weights"] == zero,
            "all_five_review_visemes_present": present == {"AH", "EE", "O", "FV", "MBP"},
            "runtime_binding_authorized": False,
            "activation_authorized": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wav", required=True)
    parser.add_argument("--transcript-file", required=True)
    parser.add_argument("--alignment", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fps", type=int, default=60)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    wav_path = Path(args.wav).resolve(strict=True)
    transcript_path = Path(args.transcript_file).resolve(strict=True)
    alignment_path = Path(args.alignment).resolve(strict=True)
    output_path = Path(args.output).resolve()
    if output_path.exists():
        raise TimelineError(f"append-only output already exists: {output_path}")
    transcript = transcript_path.read_text(encoding="utf-8").strip()
    if not transcript:
        raise TimelineError("transcript is empty")
    timeline = build_timeline(
        wav_path=wav_path,
        transcript=transcript,
        alignment_path=alignment_path,
        fps=args.fps,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(timeline, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output_path), "sha256": sha256_file(output_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
