"""Review-first acoustic grouping for mixed-speaker voice reference packs.

This module deliberately does not claim biometric identification. It creates useful
speaker-shaped folders with acoustic review labels, then preserves human or
transcript-based identity hints as the authoritative names.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import struct
import wave
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _io_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _write_text(path: Path, value: str) -> None:
    """Write metadata reliably when descriptive Windows pack paths exceed MAX_PATH."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_io_path(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(value)


def _read_json(path: Path, default: Any) -> Any:
    try:
        with open(_io_path(path), "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError):
        return default


def _safe_name(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    return "_".join(part for part in cleaned.split("_") if part) or "speaker"


def _wav_samples(path: Path, max_seconds: float = 8.0) -> tuple[int, list[float]]:
    with wave.open(str(path), "rb") as handle:
        rate = handle.getframerate()
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        count = min(handle.getnframes(), int(rate * max_seconds))
        raw = handle.readframes(count)
    if width != 2:
        raise ValueError(f"Only 16-bit PCM WAV is supported for grouping: {path}")
    values = struct.unpack(f"<{len(raw) // 2}h", raw)
    if channels > 1:
        values = tuple(sum(values[index:index + channels]) / channels for index in range(0, len(values), channels))
    return rate, [float(value) for value in values]


def _pitch_estimate(rate: int, samples: list[float]) -> float:
    """Estimate a rough median fundamental from a few short voiced windows."""
    if not samples:
        return 0.0
    target_rate = 8000
    step = max(1, rate // target_rate)
    reduced = samples[::step]
    actual_rate = rate / step
    window = int(actual_rate * 0.08)
    hop = max(window, int(actual_rate * 0.25))
    pitches: list[float] = []
    for start in range(0, max(0, len(reduced) - window), hop):
        frame = reduced[start:start + window]
        mean = sum(frame) / len(frame)
        frame = [value - mean for value in frame]
        energy = sum(value * value for value in frame) / len(frame)
        if energy < 4000:
            continue
        low_lag = max(1, int(actual_rate / 320.0))
        high_lag = min(len(frame) // 2, int(actual_rate / 70.0))
        best_lag, best_score = 0, 0.0
        for lag in range(low_lag, high_lag + 1, 2):
            score = sum(frame[index] * frame[index + lag] for index in range(len(frame) - lag))
            if score > best_score:
                best_lag, best_score = lag, score
        if best_lag and best_score > energy * len(frame) * 0.18:
            pitches.append(actual_rate / best_lag)
    return round(median(pitches), 2) if pitches else 0.0


def acoustic_signature(path: Path) -> dict[str, float]:
    rate, samples = _wav_samples(path)
    if not samples:
        return {"rms": 0.0, "zcr": 0.0, "delta": 0.0, "crest": 0.0, "pitch_hz": 0.0}
    rms = math.sqrt(sum(value * value for value in samples) / len(samples))
    crossings = sum(1 for left, right in zip(samples, samples[1:]) if (left < 0 <= right) or (right < 0 <= left))
    delta = sum(abs(right - left) for left, right in zip(samples, samples[1:])) / max(1, len(samples) - 1)
    peak = max(abs(value) for value in samples)
    return {
        "rms": round(rms, 3),
        "zcr": round(crossings / max(1, len(samples) - 1), 6),
        "delta": round(delta, 3),
        "crest": round(peak / max(rms, 1.0), 4),
        "pitch_hz": _pitch_estimate(rate, samples),
    }


def _standardize(rows: list[list[float]]) -> list[list[float]]:
    if not rows:
        return []
    columns = list(zip(*rows))
    means = [sum(column) / len(column) for column in columns]
    scales = [math.sqrt(sum((value - mean) ** 2 for value in column) / len(column)) or 1.0 for column, mean in zip(columns, means)]
    return [[(value - means[index]) / scales[index] for index, value in enumerate(row)] for row in rows]


def _kmeans(rows: list[list[float]], cluster_count: int, rounds: int = 24) -> list[int]:
    if not rows:
        return []
    cluster_count = max(1, min(cluster_count, len(rows)))
    ordered = sorted(range(len(rows)), key=lambda index: tuple(rows[index]))
    centroids = [rows[ordered[min(len(ordered) - 1, round(index * (len(ordered) - 1) / max(1, cluster_count - 1)))]] for index in range(cluster_count)]
    labels = [0] * len(rows)
    for _ in range(rounds):
        new_labels = [min(range(cluster_count), key=lambda group: sum((value - centroids[group][axis]) ** 2 for axis, value in enumerate(row))) for row in rows]
        if new_labels == labels:
            break
        labels = new_labels
        for group in range(cluster_count):
            members = [rows[index] for index, label in enumerate(labels) if label == group]
            if members:
                centroids[group] = [sum(column) / len(column) for column in zip(*members)]
    return labels


def _hint_name(clip: dict[str, Any], hints: dict[str, Any]) -> str:
    clip_id = str(clip.get("clip_id", ""))
    direct = hints.get("clip_ids", {}).get(clip_id)
    if direct:
        return _safe_name(str(direct))
    start = float(clip.get("start_seconds", 0.0) or 0.0)
    end = float(clip.get("end_seconds", start) or start)
    for item in hints.get("time_ranges", []):
        overlap = min(end, float(item.get("end_seconds", 0.0))) - max(start, float(item.get("start_seconds", 0.0)))
        if overlap > 0 and item.get("speaker"):
            return _safe_name(str(item["speaker"]))
    return ""


def separate_reference_pack(pack_dir: Path, cluster_count: int | None = None) -> dict[str, Any]:
    pack_dir = pack_dir.resolve()
    manifest_path = pack_dir / "voice_reference_manifest.json"
    manifest = _read_json(manifest_path, {})
    clips = list(manifest.get("audio", {}).get("clips", []))
    if not clips:
        raise ValueError(f"No candidate clips were found in {manifest_path}")
    hints_path = pack_dir / "speaker_identity_hints.json"
    if not hints_path.exists():
        _write_text(hints_path, json.dumps({
            "note": "Names here are authoritative review hints. Add clip ids or time ranges after listening or aligning a transcript.",
            "clip_ids": {},
            "time_ranges": [],
        }, indent=2))
    hints = _read_json(hints_path, {})
    signatures: list[dict[str, float]] = []
    resolved_paths: list[Path] = []
    for clip in clips:
        raw_path = Path(str(clip.get("path", "")))
        path = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path
        resolved_paths.append(path)
        signatures.append(acoustic_signature(path))
    rows = _standardize([[item["pitch_hz"], item["zcr"], item["delta"], item["crest"]] for item in signatures])
    groups = cluster_count or max(2, min(8, round(math.sqrt(len(clips) / 18.0))))
    labels = _kmeans(rows, groups)
    cluster_pitches = {group: median([signatures[index]["pitch_hz"] for index, label in enumerate(labels) if label == group and signatures[index]["pitch_hz"] > 0] or [0.0]) for group in range(groups)}
    ordered_groups = sorted(range(groups), key=lambda group: cluster_pitches[group])
    male_index = female_index = neutral_index = 0
    acoustic_names: dict[int, str] = {}
    for group in ordered_groups:
        pitch = cluster_pitches[group]
        if pitch and pitch <= 145:
            male_index += 1; acoustic_names[group] = f"male_{male_index}"
        elif pitch >= 165:
            female_index += 1; acoustic_names[group] = f"female_{female_index}"
        else:
            neutral_index += 1; acoustic_names[group] = f"speaker_{neutral_index}"
    output = pack_dir / "speaker_separation"
    speakers_dir = output / "speakers"
    speakers_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for index, (clip, source, signature, group) in enumerate(zip(clips, resolved_paths, signatures, labels)):
        hinted = _hint_name(clip, hints)
        label = hinted or acoustic_names[group]
        destination = speakers_dir / label / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            try:
                os.link(source, destination)
            except OSError:
                shutil.copy2(source, destination)
        records.append({
            "clip_id": clip.get("clip_id"), "source_path": str(source), "group_path": str(destination),
            "speaker_label": label, "identity_status": "confirmed_hint" if hinted else "unverified_acoustic_group",
            "acoustic_cluster": group, "features": signature,
        })
    result = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pack_id": manifest.get("pack_id", pack_dir.name),
        "method": "review_first_acoustic_kmeans",
        "limitations": [
            "Folders are acoustic review groups, not biometric identity claims.",
            "Female/male labels are rough pitch-based review labels and can be wrong.",
            "Music, overlap, effects, and one person changing vocal style can split or merge groups.",
            "Add reviewed names to speaker_identity_hints.json and rerun to create named folders.",
        ],
        "cluster_count": groups,
        "speaker_labels": sorted({item["speaker_label"] for item in records}),
        "clips": records,
    }
    output.mkdir(parents=True, exist_ok=True)
    _write_text(output / "speaker_separation_manifest.json", json.dumps(result, indent=2))
    _write_text(
        output / "README.md",
        "# Speaker separation review\n\nListen to the grouped clips before approving a voice. "
        "Rename identities through `speaker_identity_hints.json`; do not treat acoustic labels as facts.\n",
    )
    return result


def build_speaker_audition_reels(
    pack_dir: Path,
    clips_per_group: int = 8,
    silence_seconds: float = 0.2,
) -> dict[str, Any]:
    """Build one short, review-only WAV reel for each acoustic group."""
    pack_dir = pack_dir.resolve()
    speakers_dir = pack_dir / "speaker_separation" / "speakers"
    if not speakers_dir.exists():
        raise ValueError(f"Speaker groups were not found in {speakers_dir}")

    reels_dir = pack_dir / "speaker_separation" / "review_reels"
    reels_dir.mkdir(parents=True, exist_ok=True)
    reel_records: list[dict[str, Any]] = []

    for group_dir in sorted(path for path in speakers_dir.iterdir() if path.is_dir()):
        available = sorted(group_dir.glob("*.wav"))
        if not available:
            continue
        wanted = max(1, min(int(clips_per_group), len(available)))
        if wanted == len(available):
            selected = available
        elif wanted == 1:
            selected = [available[len(available) // 2]]
        else:
            selected = [
                available[round(index * (len(available) - 1) / (wanted - 1))]
                for index in range(wanted)
            ]

        output_path = reels_dir / f"{group_dir.name}_audition.wav"
        source_names: list[str] = []
        baseline: tuple[int, int, int] | None = None
        written = 0
        with wave.open(str(output_path), "wb") as destination:
            for source in selected:
                with wave.open(str(source), "rb") as clip:
                    params = (clip.getnchannels(), clip.getsampwidth(), clip.getframerate())
                    if baseline is None:
                        baseline = params
                        destination.setnchannels(params[0])
                        destination.setsampwidth(params[1])
                        destination.setframerate(params[2])
                    if params != baseline:
                        continue
                    destination.writeframes(clip.readframes(clip.getnframes()))
                    silence_frames = int(params[2] * max(0.0, silence_seconds))
                    destination.writeframes(b"\x00" * silence_frames * params[0] * params[1])
                    source_names.append(source.name)
                    written += 1

        if not written:
            output_path.unlink(missing_ok=True)
            continue
        reel_records.append({
            "speaker_label": group_dir.name,
            "identity_status": "unverified_review_reel",
            "path": str(output_path),
            "clip_count": written,
            "source_clips": source_names,
        })

    if not reel_records:
        raise ValueError("No compatible WAV clips were available for audition reels.")
    result = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pack_id": pack_dir.name,
        "purpose": "Short listening reels for human speaker identification before clip approval.",
        "warning": "Acoustic labels are not identities. Do not train or approve a voice from a reel alone.",
        "reels": reel_records,
    }
    _write_text(reels_dir / "audition_reels_manifest.json", json.dumps(result, indent=2))
    _write_text(
        reels_dir / "README.md",
        "# Speaker-group audition reels\n\n"
        "Play each WAV to identify recurring speakers quickly. These labels are unverified acoustic groups. "
        "After listening, add reviewed names to `speaker_identity_hints.json`, rerun separation, and approve "
        "only clean target-only clips in the review panel.\n",
    )
    return result
