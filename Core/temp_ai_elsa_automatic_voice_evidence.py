"""One-click, fail-closed preparation of Elsa source evidence.

This module is intentionally narrow.  It prepares two already selected time
ranges from one exact official source, reuses hash-valid bounded-analysis runs,
and concatenates their 16 kHz mono PCM files in a deterministic order.  The
result is evidence only: it does not make an identity claim or perform any
model/runtime operation.
"""
from __future__ import annotations

import json
import os
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from Core.temp_ai_online_media_analysis import (
    PROJECT_ROOT,
    SAMPLE_RATE,
    build_analysis_request,
    file_sha256,
    resolve_candidate_dir,
    run_private_online_analysis,
)
from Core.temp_ai_voice_discovery import canonical_url


SCHEMA_VERSION = 1
ELSA_CANDIDATE_ID = "elsa_frozen_frozen_fever_frozen_ii_20260716"
OFFICIAL_SOURCE_URL = "https://www.youtube.com/watch?v=utAwhtPlx8c"
SELECTED_RANGES: tuple[tuple[float, float], ...] = (
    (40.12, 43.72),
    (54.86, 58.16),
)
OUTPUT_RELATIVE = Path("workbench") / "inputs" / "identity_reviews"
ANCHOR_FILENAME = "elsa_official_dressing_room_evidence.wav"
MANIFEST_FILENAME = "elsa_automatic_official_voice_evidence.json"


AnalysisRunner = Callable[..., dict[str, Any]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _project_relative(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _resolve_manifest_file(
    raw_path: str,
    *,
    candidate_dir: Path,
    project_root: Path,
) -> Path:
    path = Path(str(raw_path or ""))
    if not path.is_absolute():
        path = project_root / path
    if path.is_symlink():
        raise ValueError("Cached PCM evidence cannot be a symlink.")
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(candidate_dir.resolve())
    except ValueError as exc:
        raise ValueError("Cached PCM evidence escaped the Elsa candidate folder.") from exc
    if not resolved.is_file():
        raise ValueError("Cached PCM evidence is not a regular file.")
    return resolved


def _validate_pcm(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as source:
        channels = source.getnchannels()
        sample_width = source.getsampwidth()
        sample_rate = source.getframerate()
        frame_count = source.getnframes()
        compression = source.getcomptype()
    if (channels, sample_width, sample_rate, compression) != (1, 2, SAMPLE_RATE, "NONE"):
        raise ValueError("Elsa evidence must be mono 16-bit 16 kHz PCM WAV.")
    return {
        "path": path,
        "sha256": file_sha256(path),
        "bytes": path.stat().st_size,
        "frames": frame_count,
        "duration_seconds": round(frame_count / SAMPLE_RATE, 3),
    }


def _matching_clean_cache(
    candidate_dir: Path,
    *,
    start_seconds: float,
    end_seconds: float,
    project_root: Path,
) -> tuple[dict[str, Any], Path] | None:
    analysis_root = candidate_dir / "workbench" / "inputs" / "online_voice_analysis"
    manifests = sorted(analysis_root.glob("*/analysis_manifest.json"), reverse=True)
    expected_url = canonical_url(OFFICIAL_SOURCE_URL)
    for path in manifests:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            source = value.get("source") if isinstance(value.get("source"), dict) else {}
            bounds = source.get("requested_range") if isinstance(source.get("requested_range"), dict) else {}
            review = value.get("objective_review") if isinstance(value.get("objective_review"), dict) else {}
            if canonical_url(str(source.get("url") or "")) != expected_url:
                continue
            if abs(float(bounds.get("start_seconds")) - start_seconds) > 0.001:
                continue
            if abs(float(bounds.get("end_seconds")) - end_seconds) > 0.001:
                continue
            if review.get("basic_signal_quality_passed") is not True:
                continue
            if review.get("possible_contamination_flagged") is not False:
                continue
            artifacts = value.get("artifacts") if isinstance(value.get("artifacts"), dict) else {}
            pcm = artifacts.get("mono_16khz_pcm") if isinstance(artifacts.get("mono_16khz_pcm"), dict) else {}
            pcm_path = _resolve_manifest_file(
                str(pcm.get("path") or ""), candidate_dir=candidate_dir, project_root=project_root
            )
            details = _validate_pcm(pcm_path)
            if str(pcm.get("sha256") or "") != details["sha256"]:
                continue
            return value, pcm_path
        except (OSError, ValueError, TypeError, json.JSONDecodeError, wave.Error):
            continue
    return None


def _run_one_range(
    *,
    candidate_id: str,
    candidate_dir: Path,
    project_root: Path,
    start_seconds: float,
    end_seconds: float,
    analysis_runner: AnalysisRunner,
    candidate_root: Path | None,
) -> tuple[dict[str, Any], Path, bool]:
    cached = _matching_clean_cache(
        candidate_dir,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        project_root=project_root,
    )
    if cached:
        return cached[0], cached[1], True

    request = build_analysis_request(
        candidate_id=candidate_id,
        source_url=OFFICIAL_SOURCE_URL,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        owner_authorized_private_analysis=True,
    )
    kwargs: dict[str, Any] = {}
    if candidate_root is not None:
        kwargs["candidate_root"] = candidate_root
    result = analysis_runner(request, **kwargs)
    review = result.get("objective_review") if isinstance(result.get("objective_review"), dict) else {}
    if review.get("basic_signal_quality_passed") is not True:
        raise RuntimeError("The bounded Elsa range failed basic signal-quality checks.")
    if review.get("possible_contamination_flagged") is not False:
        raise RuntimeError("The bounded Elsa range was contamination-flagged and was not combined.")
    pcm = result.get("artifacts", {}).get("mono_16khz_pcm", {})
    pcm_path = _resolve_manifest_file(
        str(pcm.get("path") or ""), candidate_dir=candidate_dir, project_root=project_root
    )
    details = _validate_pcm(pcm_path)
    if str(pcm.get("sha256") or "") != details["sha256"]:
        raise RuntimeError("The bounded Elsa PCM hash did not match its analysis manifest.")
    return result, pcm_path, False


def concatenate_pcm_deterministically(inputs: list[Path], output: Path) -> dict[str, Any]:
    """Concatenate exact PCM frames without resampling or added silence."""
    if not inputs:
        raise ValueError("At least one PCM input is required.")
    chunks: list[bytes] = []
    total_frames = 0
    for path in inputs:
        _validate_pcm(path)
        with wave.open(str(path), "rb") as source:
            frame_count = source.getnframes()
            chunks.append(source.readframes(frame_count))
            total_frames += frame_count
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".wav", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with wave.open(str(temporary), "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(SAMPLE_RATE)
            target.setcomptype("NONE", "not compressed")
            target.setnframes(total_frames)
            for chunk in chunks:
                target.writeframesraw(chunk)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return _validate_pcm(output)


def build_elsa_automatic_voice_evidence(
    *,
    candidate_id: str = ELSA_CANDIDATE_ID,
    candidate_root: Path | None = None,
    project_root: Path = PROJECT_ROOT,
    analysis_runner: AnalysisRunner = run_private_online_analysis,
) -> dict[str, Any]:
    """Build or reuse both ranges and emit one bounded evidence WAV/manifest."""
    candidate_dir = resolve_candidate_dir(candidate_id, candidate_root)
    entries: list[dict[str, Any]] = []
    pcm_paths: list[Path] = []
    reused = 0
    acquired = 0
    for start_seconds, end_seconds in SELECTED_RANGES:
        result, pcm_path, was_reused = _run_one_range(
            candidate_id=candidate_id,
            candidate_dir=candidate_dir,
            project_root=project_root,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            analysis_runner=analysis_runner,
            candidate_root=candidate_root,
        )
        reused += int(was_reused)
        acquired += int(not was_reused)
        details = _validate_pcm(pcm_path)
        entries.append(
            {
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "analysis_id": str(result.get("analysis_id") or ""),
                "cache_reused": was_reused,
                "pcm": {
                    "path": _project_relative(pcm_path, project_root),
                    "sha256": details["sha256"],
                    "duration_seconds": details["duration_seconds"],
                },
                "basic_signal_quality_passed": True,
                "possible_contamination_flagged": False,
                "speaker_identity_verified": False,
            }
        )
        pcm_paths.append(pcm_path)

    output_dir = candidate_dir / OUTPUT_RELATIVE
    anchor_path = output_dir / ANCHOR_FILENAME
    anchor = concatenate_pcm_deterministically(pcm_paths, anchor_path)
    manifest_path = output_dir / MANIFEST_FILENAME
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _now_iso(),
        "candidate_id": candidate_id,
        "status": "bounded_official_source_evidence_prepared_identity_unverified",
        "source": {
            "url": canonical_url(OFFICIAL_SOURCE_URL),
            "publisher_context": "official_source_selected_for_bounded_private_evidence",
            "ranges": entries,
        },
        "combined_evidence_wav": {
            "path": _project_relative(anchor_path, project_root),
            "sha256": anchor["sha256"],
            "bytes": anchor["bytes"],
            "sample_rate_hz": SAMPLE_RATE,
            "channels": 1,
            "sample_width_bits": 16,
            "duration_seconds": anchor["duration_seconds"],
            "concatenation_order": [[start, end] for start, end in SELECTED_RANGES],
            "added_silence_seconds": 0,
        },
        "cache": {"bounded_runs_reused": reused, "bounded_runs_acquired": acquired},
        "authority_boundary": {
            "speaker_identity_claimed": False,
            "target_only_identity_claimed": False,
            "voice_training_or_cloning_performed": False,
            "voice_synthesis_performed": False,
            "voice_assigned": False,
            "candidate_activated": False,
            "runtime_changed": False,
            "manual_review_gui_opened": False,
        },
        "next_stage": "evidence_only_requires_separate_identity_and_model_governance",
    }
    _write_json_atomic(manifest_path, manifest)
    manifest["manifest_path"] = _project_relative(manifest_path, project_root)
    return manifest


__all__ = [
    "ANCHOR_FILENAME",
    "ELSA_CANDIDATE_ID",
    "MANIFEST_FILENAME",
    "OFFICIAL_SOURCE_URL",
    "SELECTED_RANGES",
    "build_elsa_automatic_voice_evidence",
    "concatenate_pcm_deterministically",
]
