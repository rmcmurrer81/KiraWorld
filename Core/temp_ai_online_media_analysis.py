"""Bounded, owner-authorized online media preparation for TemporaryAI evidence.

This is deliberately separate from metadata nomination.  It acquires one
explicit public URL/time range into a private candidate workbench, hashes every
artifact, prepares mono 16 kHz PCM, creates silence-bounded review segments,
and emits objective signal diagnostics.  It never identifies a speaker and it
cannot train/clone, assign, synthesize, or activate a voice/person.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import time
import wave
from array import array
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from Core.temp_ai_voice_discovery import CANDIDATE_ROOT, canonical_url, slug
from Core.voice_reference_pipeline import resolve_ffmpeg


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1
MIN_RANGE_SECONDS = 2.0
MAX_RANGE_SECONDS = 45.0
MAX_SOURCE_BYTES = 300 * 1024 * 1024
SAMPLE_RATE = 16_000
REQUEST_FILENAME = "automatic_online_private_analysis_request.json"
RESULT_FILENAME = "automatic_online_private_analysis_latest.json"
ERROR_FILENAME = "automatic_online_private_analysis_last_error.json"
RUNS_RELATIVE = Path("workbench") / "inputs" / "online_voice_analysis"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _finite(value: Any, field: str, minimum: float = 0.0) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite number.") from exc
    if not math.isfinite(number) or number < minimum:
        raise ValueError(f"{field} must be a finite number >= {minimum}.")
    return number


def resolve_candidate_dir(candidate_id: str, candidate_root: Path | None = None) -> Path:
    if not candidate_id or slug(candidate_id) != candidate_id:
        raise ValueError("candidate_id must be a normalized lowercase identifier.")
    root = (candidate_root or CANDIDATE_ROOT).resolve()
    candidate = (root / candidate_id).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("candidate_id escapes the candidate root.") from exc
    if not candidate.is_dir() or candidate.is_symlink():
        raise FileNotFoundError(f"TemporaryAI candidate does not exist: {candidate_id}")
    return candidate


def build_analysis_request(
    *,
    candidate_id: str,
    source_url: str,
    start_seconds: float,
    end_seconds: float,
    owner_authorized_private_analysis: bool,
) -> dict[str, Any]:
    """Create one bounded request; explicit authority is mandatory."""
    if owner_authorized_private_analysis is not True:
        raise PermissionError("Online acquisition requires --owner-authorized-private-analysis.")
    start = _finite(start_seconds, "start_seconds")
    end = _finite(end_seconds, "end_seconds")
    duration = end - start
    if duration < MIN_RANGE_SECONDS or duration > MAX_RANGE_SECONDS:
        raise ValueError(f"The requested range must be {MIN_RANGE_SECONDS:.0f}–{MAX_RANGE_SECONDS:.0f} seconds.")
    if slug(candidate_id) != candidate_id:
        raise ValueError("candidate_id must be a normalized lowercase identifier.")
    url = canonical_url(source_url)
    if not url:
        raise ValueError("source_url is required.")
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": f"{candidate_id}_bounded_online_private_analysis_v1",
        "created_at": now_iso(),
        "candidate_id": candidate_id,
        "source_url": url,
        "range": {
            "start_seconds": round(start, 3),
            "end_seconds": round(end, 3),
            "duration_seconds": round(duration, 3),
        },
        "authority": {
            "owner_authorized_private_analysis": True,
            "scope": "bounded_private_evidence_acquisition_and_objective_audio_preparation_only",
        },
        "policy": {
            "maximum_range_seconds": MAX_RANGE_SECONDS,
            "no_playlist": True,
            "speaker_identity_may_be_claimed": False,
            "voice_training_or_cloning_allowed": False,
            "voice_assignment_allowed": False,
            "voice_synthesis_allowed": False,
            "candidate_activation_allowed": False,
            "public_distribution_allowed": False,
        },
    }


def validate_analysis_request(request: dict[str, Any], *, candidate_root: Path | None = None) -> Path:
    if not isinstance(request, dict):
        raise ValueError("Analysis request must be a JSON object.")
    if request.get("authority", {}).get("owner_authorized_private_analysis") is not True:
        raise PermissionError("Explicit owner authority is missing.")
    policy = request.get("policy") if isinstance(request.get("policy"), dict) else {}
    forbidden = (
        "speaker_identity_may_be_claimed",
        "voice_training_or_cloning_allowed",
        "voice_assignment_allowed",
        "voice_synthesis_allowed",
        "candidate_activation_allowed",
        "public_distribution_allowed",
    )
    if any(policy.get(key) is not False for key in forbidden):
        raise ValueError("Private analysis request attempted to grant forbidden identity/model/runtime authority.")
    canonical_url(str(request.get("source_url") or ""))
    bounds = request.get("range") if isinstance(request.get("range"), dict) else {}
    start = _finite(bounds.get("start_seconds"), "range.start_seconds")
    end = _finite(bounds.get("end_seconds"), "range.end_seconds")
    duration = end - start
    if duration < MIN_RANGE_SECONDS or duration > MAX_RANGE_SECONDS:
        raise ValueError("Analysis range is outside the bounded private-analysis limit.")
    if abs(duration - float(bounds.get("duration_seconds", -1))) > 0.01:
        raise ValueError("Analysis duration does not match its exact range.")
    return resolve_candidate_dir(str(request.get("candidate_id") or ""), candidate_root)


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def resolve_ytdlp_command() -> list[str] | None:
    if executable := shutil.which("yt-dlp"):
        return [executable]
    return [sys.executable, "-m", "yt_dlp"] if _module_available("yt_dlp") else None


def analysis_capabilities() -> dict[str, Any]:
    ffmpeg = resolve_ffmpeg()
    ytdlp = resolve_ytdlp_command()
    configured_overlap = os.environ.get("KIRA_PYANNOTE_PIPELINE", "").strip()
    return {
        "yt_dlp": {"ready": bool(ytdlp), "command_kind": "executable_or_python_module" if ytdlp else "unavailable"},
        "ffmpeg": {"ready": bool(ffmpeg), "path": ffmpeg or ""},
        "pyannote_audio_installed": _module_available("pyannote.audio"),
        "local_overlap_pipeline_configured": bool(configured_overlap and Path(configured_overlap).exists()),
        "network_model_download_allowed": False,
    }


def _inside_regular_file(path: Path, parent: Path, *, field: str) -> Path:
    resolved_parent = parent.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(resolved_parent)
    except ValueError as exc:
        raise ValueError(f"{field} escaped its private analysis directory.") from exc
    if path.is_symlink() or not resolved.is_file():
        raise ValueError(f"{field} must be a regular project-local file.")
    return resolved


def acquire_bounded_media(request: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    """Acquire only the explicit range with yt-dlp; no playlist/cookies/model use."""
    command = resolve_ytdlp_command()
    ffmpeg = resolve_ffmpeg()
    if not command:
        raise RuntimeError("yt-dlp is unavailable.")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is unavailable.")
    output_dir.mkdir(parents=True, exist_ok=False)
    bounds = request["range"]
    section = f"*{float(bounds['start_seconds']):.3f}-{float(bounds['end_seconds']):.3f}"
    template = output_dir / "bounded_source.%(ext)s"
    full_command = command + [
        "--no-playlist",
        "--no-warnings",
        "--write-info-json",
        "--download-sections",
        section,
        "--force-keyframes-at-cuts",
        "--max-filesize",
        "300M",
        "--ffmpeg-location",
        # yt-dlp accepts either a directory containing an executable named
        # ffmpeg or the exact binary path.  imageio-ffmpeg uses a versioned
        # filename, so passing its parent incorrectly reports FFmpeg missing.
        str(Path(ffmpeg)),
        "-f",
        "bv*+ba/b",
        "--merge-output-format",
        "mp4",
        "-o",
        str(template),
        str(request["source_url"]),
    ]
    completed = subprocess.run(
        full_command,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1800,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()[-1:] or ["provider failed"]
        raise RuntimeError(f"Bounded yt-dlp acquisition failed: {detail[0][:800]}")
    ignored = {".json", ".part", ".ytdl", ".temp"}
    media = sorted(
        (item for item in output_dir.glob("bounded_source.*") if item.suffix.lower() not in ignored),
        key=lambda item: item.stat().st_size,
        reverse=True,
    )
    if not media:
        raise RuntimeError("yt-dlp completed without a bounded media artifact.")
    media_path = _inside_regular_file(media[0], output_dir, field="acquired media")
    if media_path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("Acquired bounded media exceeds the 300 MiB private-analysis limit.")
    info_files = sorted(output_dir.glob("bounded_source*.info.json"))
    metadata_path = _inside_regular_file(info_files[0], output_dir, field="provider metadata") if info_files else None
    return {
        "media_path": media_path,
        "metadata_path": metadata_path,
        "provider": "yt_dlp_bounded_section",
        "range_applied_by_provider": True,
        "command_policy": {
            "no_playlist": True,
            "download_sections": section,
            "cookies_requested": False,
            "maximum_file_size_bytes": MAX_SOURCE_BYTES,
        },
    }


def _run_ffmpeg(command: list[str], output: Path) -> None:
    completed = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        check=False,
    )
    if completed.returncode != 0 or not output.is_file():
        raise RuntimeError(f"FFmpeg objective preparation failed: {completed.stderr.strip()[-900:]}")


def prepare_review_video_and_pcm(source: Path, review_video: Path, pcm_wav: Path, duration_seconds: float) -> None:
    """Preserve the bounded source as review video and make mono 16 kHz PCM."""
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is unavailable.")
    review_video.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, review_video)
    _run_ffmpeg(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-t",
            f"{duration_seconds:.3f}",
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(SAMPLE_RATE),
            "-c:a",
            "pcm_s16le",
            str(pcm_wav),
        ],
        pcm_wav,
    )


def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * ratio)))
    return ordered[index]


def _dbfs(rms: float) -> float:
    return -120.0 if rms <= 0 else 20.0 * math.log10(rms / 32768.0)


def _frame_metrics(samples: list[int], rate: int, frame_ms: int = 20) -> list[dict[str, float]]:
    size = max(1, round(rate * frame_ms / 1000))
    rows: list[dict[str, float]] = []
    for start in range(0, len(samples), size):
        frame = samples[start : start + size]
        if len(frame) < max(1, size // 2):
            continue
        rms = math.sqrt(sum(value * value for value in frame) / len(frame))
        crossings = sum(1 for left, right in zip(frame, frame[1:]) if (left < 0 <= right) or (right < 0 <= left))
        rows.append(
            {
                "rms": rms,
                "dbfs": _dbfs(rms),
                "zcr": crossings / max(1, len(frame) - 1),
                "peak": float(max(abs(value) for value in frame)),
            }
        )
    return rows


def _autocorrelation_tonality(frame: list[int], rate: int) -> float:
    if len(frame) < 128:
        return 0.0
    mean = sum(frame) / len(frame)
    centered = [value - mean for value in frame]
    energy = sum(value * value for value in centered)
    if energy <= 1.0:
        return 0.0
    low_lag = max(2, int(rate / 1200.0))
    high_lag = min(len(centered) // 2, int(rate / 75.0))
    best = 0.0
    for lag in range(low_lag, high_lag + 1, 2):
        numerator = sum(centered[index] * centered[index + lag] for index in range(len(centered) - lag))
        denominator = math.sqrt(
            sum(centered[index] ** 2 for index in range(len(centered) - lag))
            * sum(centered[index + lag] ** 2 for index in range(len(centered) - lag))
        )
        if denominator:
            best = max(best, numerator / denominator)
    return max(0.0, min(1.0, best))


def analyze_pcm_wav(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as reader:
        channels = reader.getnchannels()
        width = reader.getsampwidth()
        rate = reader.getframerate()
        frame_count = reader.getnframes()
        raw = reader.readframes(frame_count)
    if channels != 1 or width != 2 or rate != SAMPLE_RATE:
        raise ValueError("Objective analysis requires mono 16-bit 16 kHz PCM WAV.")
    values = array("h")
    values.frombytes(raw)
    if sys.byteorder != "little":
        values.byteswap()
    samples = list(values)
    duration = len(samples) / rate if rate else 0.0
    rows = _frame_metrics(samples, rate)
    levels = [row["dbfs"] for row in rows]
    overall_rms = math.sqrt(sum(value * value for value in samples) / max(1, len(samples)))
    noise = _percentile(levels, 0.10)
    speech = _percentile(levels, 0.90)
    threshold = max(-48.0, noise + 8.0, speech - 18.0)
    active = [row for row in rows if row["dbfs"] >= threshold]
    quiet = [index for index, row in enumerate(rows) if noise - 1.0 <= row["dbfs"] < threshold - 2.0]
    frame_size = round(rate * 0.02)
    tonal_scores: list[float] = []
    for frame_index in quiet[::4][:80]:
        start = frame_index * frame_size
        window = samples[start : start + frame_size * 2]
        tonal_scores.append(_autocorrelation_tonality(window, rate))
    tonal_ratio = sum(score >= 0.58 for score in tonal_scores) / max(1, len(tonal_scores))
    clipping_ratio = sum(abs(value) >= 32760 for value in samples) / max(1, len(samples))
    active_ratio = len(active) / max(1, len(rows))
    silence_ratio = sum(row["dbfs"] < -55.0 for row in rows) / max(1, len(rows))
    loud = _percentile([row["dbfs"] for row in active], 0.90) if active else -120.0
    overlap_proxy_frames = [
        row
        for row in active
        if row["dbfs"] >= loud - 1.5 and 0.035 <= row["zcr"] <= 0.24 and row["peak"] / max(row["rms"], 1.0) < 2.2
    ]
    overlap_proxy_ratio = len(overlap_proxy_frames) / max(1, len(active))
    quality_pass = bool(
        duration >= MIN_RANGE_SECONDS
        and clipping_ratio <= 0.005
        and active_ratio >= 0.12
        and speech - noise >= 12.0
        and -55.0 <= _dbfs(overall_rms) <= -3.0
    )
    tonal_status = "possible_tonal_or_music_residue" if len(tonal_scores) >= 3 and tonal_ratio >= 0.25 else (
        "not_detected_by_basic_pause_tonality_proxy" if len(tonal_scores) >= 3 else "insufficient_quiet_frames"
    )
    return {
        "path": relative(path),
        "sha256": file_sha256(path),
        "bytes": path.stat().st_size,
        "sample_rate_hz": rate,
        "channels": channels,
        "sample_width_bits": width * 8,
        "duration_seconds": round(duration, 3),
        "peak": round(max((abs(value) for value in samples), default=0) / 32768.0, 6),
        "overall_rms_dbfs": round(_dbfs(overall_rms), 3),
        "clipping_ratio": round(clipping_ratio, 8),
        "active_frame_ratio": round(active_ratio, 6),
        "silence_frame_ratio": round(silence_ratio, 6),
        "noise_floor_dbfs_p10_proxy": round(noise, 3),
        "speech_level_dbfs_p90_proxy": round(speech, 3),
        "snr_db_percentile_proxy": round(speech - noise, 3),
        "activity_threshold_dbfs": round(threshold, 3),
        "quality_gate": {
            "passed": quality_pass,
            "scope": "container_and_basic_signal_quality_only_not_identity_or_clean-speaker_approval",
        },
        "contamination_heuristics": {
            "pause_tonality": {
                "status": tonal_status,
                "sampled_quiet_windows": len(tonal_scores),
                "tonal_window_ratio": round(tonal_ratio, 6),
                "can_prove_no_music": False,
            },
            "material_noise": {
                "status": "possible_low_snr_or_material_noise" if speech - noise < 15.0 else "not_detected_by_snr_proxy",
                "can_prove_clean_background": False,
            },
            "overlap_proxy": {
                "status": "possible_overlap_activity" if overlap_proxy_ratio >= 0.18 else "not_flagged_by_basic_energy_zcr_proxy",
                "flagged_active_frame_ratio": round(overlap_proxy_ratio, 6),
                "can_identify_speakers": False,
                "can_clear_overlap": False,
            },
        },
        "limits": [
            "Signal heuristics do not identify a person or prove target-only speech.",
            "No-music and no-overlap decisions require stronger analysis or audiovisual review.",
        ],
    }


def segment_pcm_on_silence(source_wav: Path, output_dir: Path, diagnostics: dict[str, Any]) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with wave.open(str(source_wav), "rb") as reader:
        params = (reader.getnchannels(), reader.getsampwidth(), reader.getframerate())
        raw = reader.readframes(reader.getnframes())
    values = array("h")
    values.frombytes(raw)
    if sys.byteorder != "little":
        values.byteswap()
    samples = list(values)
    rate = params[2]
    frame_ms = 20
    frame_size = max(1, round(rate * frame_ms / 1000))
    rows = _frame_metrics(samples, rate, frame_ms)
    threshold = float(diagnostics["activity_threshold_dbfs"])
    padding = 3
    silence_hold = round(360 / frame_ms)
    minimum = round(700 / frame_ms)
    maximum = round(12_000 / frame_ms)
    ranges: list[tuple[int, int]] = []
    start: int | None = None
    last_active: int | None = None
    for index, row in enumerate(rows):
        if row["dbfs"] >= threshold:
            if start is None:
                start = max(0, index - padding)
            last_active = index
        if start is not None and last_active is not None:
            hit_max = index - start + 1 >= maximum
            held_silence = index - last_active >= silence_hold
            if hit_max or held_silence:
                end = min(len(rows), (index + 1) if hit_max else (last_active + padding + 1))
                if end - start >= minimum:
                    ranges.append((start, end))
                start = None
                last_active = None
    if start is not None and len(rows) - start >= minimum:
        ranges.append((start, len(rows)))
    records: list[dict[str, Any]] = []
    for number, (start_frame, end_frame) in enumerate(ranges, 1):
        start_sample = start_frame * frame_size
        end_sample = min(len(samples), end_frame * frame_size)
        path = output_dir / f"segment_{number:04d}.wav"
        segment_values = array("h", samples[start_sample:end_sample])
        if sys.byteorder != "little":
            segment_values.byteswap()
        with wave.open(str(path), "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(rate)
            writer.writeframes(segment_values.tobytes())
        segment_diagnostics = analyze_pcm_wav(path)
        records.append(
            {
                "segment_id": f"segment_{number:04d}",
                "path": relative(path),
                "sha256": segment_diagnostics["sha256"],
                "bytes": segment_diagnostics["bytes"],
                "start_seconds_relative_to_requested_range": round(start_sample / rate, 3),
                "end_seconds_relative_to_requested_range": round(end_sample / rate, 3),
                "duration_seconds": segment_diagnostics["duration_seconds"],
                "objective_diagnostics": segment_diagnostics,
                "identity_status": "unverified_no_identity_claim",
                "speaker_status": "unverified_may_contain_any_speaker_or_overlap",
                "model_input_allowed": False,
            }
        )
    return records


Acquirer = Callable[[dict[str, Any], Path], dict[str, Any]]
Preparer = Callable[[Path, Path, Path, float], None]


def run_private_online_analysis(
    request: dict[str, Any],
    *,
    candidate_root: Path | None = None,
    acquirer: Acquirer = acquire_bounded_media,
    preparer: Preparer = prepare_review_video_and_pcm,
) -> dict[str, Any]:
    candidate_dir = validate_analysis_request(request, candidate_root=candidate_root)
    request_path = candidate_dir / REQUEST_FILENAME
    result_path = candidate_dir / RESULT_FILENAME
    write_json(request_path, request)
    fingerprint = hashlib.sha256(
        f"{request['source_url']}|{request['range']['start_seconds']}|{request['range']['end_seconds']}".encode("utf-8")
    ).hexdigest()[:12]
    run_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{fingerprint}"
    run_dir = candidate_dir / RUNS_RELATIVE / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    acquisition_dir = run_dir / "acquisition"
    acquisition = acquirer(request, acquisition_dir)
    if not isinstance(acquisition, dict) or not acquisition.get("media_path"):
        raise ValueError("Acquirer did not return a bounded media path.")
    source = _inside_regular_file(Path(acquisition["media_path"]), run_dir, field="acquired media")
    if source.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("Acquired media exceeds the private-analysis size limit.")
    metadata_path = None
    if acquisition.get("metadata_path"):
        metadata_path = _inside_regular_file(Path(acquisition["metadata_path"]), run_dir, field="provider metadata")
    prepared_dir = run_dir / "prepared"
    review_video = prepared_dir / f"bounded_review_video{source.suffix.lower() or '.bin'}"
    pcm_wav = prepared_dir / "voice_mono_16khz_pcm.wav"
    preparer(source, review_video, pcm_wav, float(request["range"]["duration_seconds"]))
    review_video = _inside_regular_file(review_video, run_dir, field="bounded review video")
    pcm_wav = _inside_regular_file(pcm_wav, run_dir, field="prepared PCM")
    diagnostics = analyze_pcm_wav(pcm_wav)
    segments = segment_pcm_on_silence(pcm_wav, run_dir / "segments", diagnostics)
    contamination = diagnostics["contamination_heuristics"]
    possible_contamination = bool(
        contamination["pause_tonality"]["status"] == "possible_tonal_or_music_residue"
        or contamination["material_noise"]["status"] == "possible_low_snr_or_material_noise"
        or diagnostics["clipping_ratio"] > 0.005
    )
    metadata = read_json(metadata_path, {}) if metadata_path else {}
    result = {
        "schema_version": SCHEMA_VERSION,
        "analysis_id": run_id,
        "created_at": now_iso(),
        "candidate_id": request["candidate_id"],
        "request_id": request["request_id"],
        "request_sha256": json_sha256(request),
        "status": "objective_audio_preparation_complete_identity_unverified",
        "source": {
            "url": request["source_url"],
            "requested_range": request["range"],
            "provider": str(acquisition.get("provider") or "injected_test_acquirer"),
            "provider_metadata": {
                "path": relative(metadata_path) if metadata_path else "",
                "sha256": file_sha256(metadata_path) if metadata_path else "",
                "title": str(metadata.get("title") or ""),
                "channel": str(metadata.get("channel") or metadata.get("uploader") or ""),
                "duration_seconds": metadata.get("duration"),
                "metadata_is_not_speaker_identity": True,
            },
            "bounded_media": {
                "path": relative(source),
                "sha256": file_sha256(source),
                "bytes": source.stat().st_size,
            },
            "acquisition_policy": acquisition.get("command_policy", {}),
        },
        "artifacts": {
            "bounded_review_video": {
                "path": relative(review_video),
                "sha256": file_sha256(review_video),
                "bytes": review_video.stat().st_size,
            },
            "mono_16khz_pcm": diagnostics,
            "segments": segments,
            "segment_count": len(segments),
        },
        "objective_review": {
            "basic_signal_quality_passed": diagnostics["quality_gate"]["passed"],
            "possible_contamination_flagged": possible_contamination,
            "cleanup_and_qc_required": possible_contamination,
            "overlap": contamination["overlap_proxy"],
            "overlap_cleared": False,
            "speaker_identity_verified": False,
            "target_only_speech_verified": False,
            "eligible_for_identity_or_cleanup_review": bool(segments),
            "eligible_for_private_reference_pack_input": False,
            "eligible_for_direct_model_input": False,
        },
        "capabilities": analysis_capabilities(),
        "authority_boundary": {
            "private_bounded_analysis_was_owner_authorized": True,
            "speaker_identity_claimed": False,
            "voice_training_or_cloning_performed": False,
            "voice_assigned": False,
            "voice_synthesized": False,
            "candidate_activated": False,
            "manual_400_clip_review_box_opened": False,
        },
        "next_stage": {
            "status": "requires_identity_binding_and_overlap_or_contamination_qc",
            "note": "Prepared segments are evidence candidates only; no identity or model decision was made.",
        },
        "run_dir": relative(run_dir),
    }
    write_json(run_dir / "analysis_manifest.json", result)
    write_json(result_path, result)
    return result


def write_failure_record(
    *, candidate_id: str, source_url: str, start_seconds: float, end_seconds: float, error: Exception
) -> Path | None:
    try:
        candidate = resolve_candidate_dir(candidate_id)
    except Exception:
        return None
    record = {
        "schema_version": SCHEMA_VERSION,
        "created_at": now_iso(),
        "candidate_id": candidate_id,
        "source_url": source_url,
        "range": {"start_seconds": start_seconds, "end_seconds": end_seconds},
        "status": "bounded_private_analysis_failed_no_identity_or_model_change",
        "error_type": type(error).__name__,
        "error": str(error)[:1000],
        "speaker_identity_claimed": False,
        "voice_training_or_cloning_performed": False,
        "voice_assigned": False,
        "voice_synthesized": False,
        "candidate_activated": False,
    }
    path = candidate / ERROR_FILENAME
    write_json(path, record)
    return path


__all__ = [
    "MAX_RANGE_SECONDS",
    "MIN_RANGE_SECONDS",
    "SAMPLE_RATE",
    "acquire_bounded_media",
    "analysis_capabilities",
    "analyze_pcm_wav",
    "build_analysis_request",
    "prepare_review_video_and_pcm",
    "run_private_online_analysis",
    "segment_pcm_on_silence",
    "validate_analysis_request",
    "write_failure_record",
]
