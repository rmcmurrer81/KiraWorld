"""Fail-closed speaker-consistency evidence for bounded WAV references.

This module deliberately does less than speaker identification.  It compares
speech embeddings from an owner-confirmed anchor with bounded audio from a
different source and records reproducible similarity evidence.  A positive
score never approves a person, assigns a voice, trains/clones a model, or
activates a TemporaryAI.

The production embedding backend is loaded lazily.  It uses
``microsoft/wavlm-base-plus-sv`` through Transformers and is cache-only by
default; callers must explicitly opt in before Hugging Face may download the
model.  Tests can inject an embedding backend and therefore never need the
network or model cache.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import statistics
import struct
import tempfile
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, Sequence


DEFAULT_MODEL_ID = "microsoft/wavlm-base-plus-sv"
DEFAULT_MODEL_REVISION = "main"
TARGET_SAMPLE_RATE = 16_000
SCHEMA_VERSION = 1


class ConsistencyEvidenceError(RuntimeError):
    """Base error for evidence that cannot safely be produced."""


class AudioRejectedError(ConsistencyEvidenceError):
    """Raised when an anchor WAV fails an input or quality requirement."""


class ModelUnavailableError(ConsistencyEvidenceError):
    """Raised when the configured embedding model cannot be loaded safely."""


@dataclass(frozen=True)
class BoundedWav:
    """An already bounded WAV and the source from which it was extracted.

    ``source_id`` identifies the underlying recording, not this particular
    WAV file.  Candidate and anchor source IDs must differ.  The optional
    source bounds are audit metadata only; this module never seeks outside the
    supplied WAV.
    """

    path: Path
    source_id: str
    range_id: str = ""
    source_start_seconds: float | None = None
    source_end_seconds: float | None = None
    owner_confirmed_target_only: bool = False
    source_media_sha256: str = ""


@dataclass(frozen=True)
class AudioQualityPolicy:
    min_file_seconds: float = 1.50
    min_active_seconds: float = 1.25
    min_rms_dbfs: float = -48.0
    max_clipping_fraction: float = 0.01
    min_segment_seconds: float = 1.25
    max_segment_seconds: float = 12.0
    max_silence_gap_seconds: float = 0.42
    segment_padding_seconds: float = 0.12


class EmbeddingBackend(Protocol):
    """Small injectable surface used by the analyzer and offline tests."""

    def embed(self, samples: Sequence[float], sample_rate: int) -> Sequence[float]: ...

    def metadata(self) -> dict[str, Any]: ...


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_floats(values: Sequence[float]) -> str:
    digest = hashlib.sha256()
    for offset in range(0, len(values), 4096):
        chunk = values[offset : offset + 4096]
        digest.update(struct.pack(f"<{len(chunk)}f", *chunk))
    return digest.hexdigest()


def _dbfs(value: float) -> float:
    return round(20.0 * math.log10(max(value, 1e-12)), 3)


def _percentile(values: Sequence[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * ratio)))
    return float(ordered[index])


def _read_pcm_wav(path: Path) -> tuple[list[float], int, dict[str, Any]]:
    """Read uncompressed PCM WAV and mix channels without hidden conversion."""

    path = path.expanduser().resolve()
    if not path.is_file():
        raise AudioRejectedError(f"Bounded WAV does not exist: {path}")
    try:
        with wave.open(str(path), "rb") as reader:
            channels = reader.getnchannels()
            width = reader.getsampwidth()
            rate = reader.getframerate()
            frames = reader.getnframes()
            compression = reader.getcomptype()
            raw = reader.readframes(frames)
    except (wave.Error, OSError) as exc:
        raise AudioRejectedError(f"Unreadable WAV: {path.name}: {exc}") from exc

    if compression != "NONE":
        raise AudioRejectedError("Only uncompressed PCM WAV input is accepted.")
    if channels < 1 or rate < 8_000:
        raise AudioRejectedError("WAV has invalid channels or sample rate.")
    if width not in {1, 2, 3, 4}:
        raise AudioRejectedError(f"Unsupported PCM sample width: {width} bytes.")

    frame_width = channels * width
    if len(raw) < frame_width or len(raw) % frame_width:
        raise AudioRejectedError("WAV contains incomplete PCM frames.")

    def decode_sample(blob: bytes) -> float:
        if width == 1:
            return (blob[0] - 128) / 128.0
        if width == 2:
            return int.from_bytes(blob, "little", signed=True) / 32768.0
        if width == 3:
            integer = int.from_bytes(blob, "little", signed=False)
            if integer & 0x800000:
                integer -= 1 << 24
            return integer / 8388608.0
        return int.from_bytes(blob, "little", signed=True) / 2147483648.0

    samples: list[float] = []
    for frame_offset in range(0, len(raw), frame_width):
        total = 0.0
        for channel in range(channels):
            start = frame_offset + channel * width
            total += decode_sample(raw[start : start + width])
        samples.append(total / channels)

    return samples, rate, {
        "channels_in_file": channels,
        "sample_width_bytes": width,
        "sample_rate_hz": rate,
        "frame_count": frames,
        "mixed_to_mono": channels > 1,
    }


def _frame_levels(samples: Sequence[float], sample_rate: int, frame_ms: int = 30) -> list[float]:
    frame_size = max(1, round(sample_rate * frame_ms / 1000))
    levels: list[float] = []
    for start in range(0, len(samples), frame_size):
        chunk = samples[start : start + frame_size]
        if chunk:
            levels.append(math.sqrt(sum(value * value for value in chunk) / len(chunk)))
    return levels


def inspect_audio_quality(
    samples: Sequence[float], sample_rate: int, policy: AudioQualityPolicy
) -> dict[str, Any]:
    duration = len(samples) / sample_rate if sample_rate else 0.0
    rms = math.sqrt(sum(value * value for value in samples) / len(samples)) if samples else 0.0
    peak = max((abs(value) for value in samples), default=0.0)
    clipping_fraction = (
        sum(1 for value in samples if abs(value) >= 0.999) / len(samples) if samples else 1.0
    )
    levels = _frame_levels(samples, sample_rate)
    p10, p75 = _percentile(levels, 0.10), _percentile(levels, 0.75)
    # The cap keeps a steady, clean voice from being misclassified as silence.
    threshold = max(0.0015, min(p75 * 0.45, p10 * 2.8 if p10 else p75 * 0.20))
    active_frames = [value for value in levels if value >= threshold]
    frame_seconds = 0.030
    active_seconds = min(duration, len(active_frames) * frame_seconds)
    active_fraction = len(active_frames) / len(levels) if levels else 0.0
    active_rms = math.sqrt(sum(value * value for value in active_frames) / len(active_frames)) if active_frames else 0.0
    quiet_frames = [value for value in levels if value < threshold]
    quiet_rms = (
        math.sqrt(sum(value * value for value in quiet_frames) / len(quiet_frames))
        if quiet_frames
        else p10
    )
    snr_proxy_db = 20.0 * math.log10(max(active_rms, 1e-12) / max(quiet_rms, 1e-12))

    reasons: list[str] = []
    if duration < policy.min_file_seconds:
        reasons.append("file_too_short")
    if active_seconds < policy.min_active_seconds:
        reasons.append("insufficient_active_audio")
    if _dbfs(rms) < policy.min_rms_dbfs:
        reasons.append("audio_too_quiet")
    if clipping_fraction > policy.max_clipping_fraction:
        reasons.append("excessive_clipping")

    return {
        "status": "accepted_for_consistency_analysis" if not reasons else "rejected",
        "rejection_reasons": reasons,
        "duration_seconds": round(duration, 3),
        "rms_dbfs": _dbfs(rms),
        "peak_dbfs": _dbfs(peak),
        "clipping_fraction": round(clipping_fraction, 7),
        "active_seconds_energy_estimate": round(active_seconds, 3),
        "active_fraction_energy_estimate": round(active_fraction, 4),
        "energy_snr_proxy_db": round(snr_proxy_db, 3),
        "energy_threshold_dbfs": _dbfs(threshold),
        "note": "Energy estimates are quality/segmentation aids, not speech or speaker identity proof.",
    }


def _resample(samples: Sequence[float], source_rate: int, target_rate: int) -> list[float]:
    if source_rate == target_rate:
        return list(samples)
    if not samples or source_rate <= 0 or target_rate <= 0:
        return []
    # Linear interpolation keeps input handling dependency-free.  WavLM's
    # feature extractor receives the resulting 16 kHz floats.
    target_length = max(1, round(len(samples) * target_rate / source_rate))
    scale = source_rate / target_rate
    result: list[float] = []
    for target_index in range(target_length):
        source_position = min(len(samples) - 1, target_index * scale)
        left = int(source_position)
        right = min(len(samples) - 1, left + 1)
        fraction = source_position - left
        result.append(samples[left] * (1.0 - fraction) + samples[right] * fraction)
    return result


def segment_on_silence(
    samples: Sequence[float], sample_rate: int, policy: AudioQualityPolicy
) -> list[tuple[int, int]]:
    """Return energy-bounded ranges; it does not claim voice activity identity."""

    frame_ms = 30
    frame_size = max(1, round(sample_rate * frame_ms / 1000))
    levels = _frame_levels(samples, sample_rate, frame_ms)
    if not levels:
        return []
    p10, p75 = _percentile(levels, 0.10), _percentile(levels, 0.75)
    threshold = max(0.0015, min(p75 * 0.45, p10 * 2.8 if p10 else p75 * 0.20))
    active = [index for index, value in enumerate(levels) if value >= threshold]
    if not active:
        return []

    max_gap_frames = max(1, round(policy.max_silence_gap_seconds * 1000 / frame_ms))
    groups: list[tuple[int, int]] = []
    start = previous = active[0]
    for index in active[1:]:
        if index - previous > max_gap_frames:
            groups.append((start, previous + 1))
            start = index
        previous = index
    groups.append((start, previous + 1))

    padding = round(policy.segment_padding_seconds * sample_rate)
    min_samples = round(policy.min_segment_seconds * sample_rate)
    max_samples = round(policy.max_segment_seconds * sample_rate)
    ranges: list[tuple[int, int]] = []
    for start_frame, end_frame in groups:
        start_sample = max(0, start_frame * frame_size - padding)
        end_sample = min(len(samples), end_frame * frame_size + padding)
        if end_sample - start_sample < min_samples:
            continue
        cursor = start_sample
        while end_sample - cursor > max_samples:
            ranges.append((cursor, cursor + max_samples))
            cursor += max_samples
        if end_sample - cursor >= min_samples:
            ranges.append((cursor, end_sample))
    return ranges


def _normalise(vector: Sequence[float]) -> list[float]:
    values = [float(value) for value in vector]
    norm = math.sqrt(sum(value * value for value in values))
    if not values or not math.isfinite(norm) or norm <= 1e-12:
        raise ModelUnavailableError("Embedding backend returned an empty or zero vector.")
    normalised = [value / norm for value in values]
    if not all(math.isfinite(value) for value in normalised):
        raise ModelUnavailableError("Embedding backend returned non-finite values.")
    return normalised


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ModelUnavailableError("Embedding dimensions do not match.")
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right))))


class WavLMSpeakerEmbedder:
    """Lazy WavLM x-vector backend with cache-only behavior by default."""

    def __init__(
        self,
        *,
        model_id: str = DEFAULT_MODEL_ID,
        revision: str = DEFAULT_MODEL_REVISION,
        cache_dir: Path | None = None,
        allow_download: bool = False,
        device: str = "cpu",
    ) -> None:
        self.model_id = model_id
        self.requested_revision = revision
        self.cache_dir = cache_dir
        self.allow_download = allow_download
        self.device = device
        self._feature_extractor: Any = None
        self._model: Any = None
        self._resolved_revision = ""
        self._embedding_dimension: int | None = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import Wav2Vec2FeatureExtractor, WavLMForXVector
        except (ImportError, OSError) as exc:
            raise ModelUnavailableError(f"WavLM dependencies unavailable: {exc}") from exc

        kwargs: dict[str, Any] = {
            "revision": self.requested_revision,
            "local_files_only": not self.allow_download,
        }
        if self.cache_dir:
            kwargs["cache_dir"] = str(self.cache_dir)
        try:
            self._feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(self.model_id, **kwargs)
            self._model = WavLMForXVector.from_pretrained(self.model_id, **kwargs)
            self._model.to(torch.device(self.device))
            self._model.eval()
        except Exception as exc:
            mode = "download allowed" if self.allow_download else "cache only"
            raise ModelUnavailableError(
                f"Could not load {self.model_id}@{self.requested_revision} ({mode}): {exc}"
            ) from exc
        commit = getattr(self._model.config, "_commit_hash", None)
        self._resolved_revision = str(commit or self.requested_revision)

    def embed(self, samples: Sequence[float], sample_rate: int) -> Sequence[float]:
        self._load()
        if sample_rate != TARGET_SAMPLE_RATE:
            raise ModelUnavailableError(
                f"WavLM backend requires {TARGET_SAMPLE_RATE} Hz input; got {sample_rate}."
            )
        import torch

        inputs = self._feature_extractor(
            list(samples), sampling_rate=sample_rate, return_tensors="pt", padding=False
        )
        input_values = inputs["input_values"].to(self.device)
        attention_mask = inputs.get("attention_mask")
        kwargs = {"attention_mask": attention_mask.to(self.device)} if attention_mask is not None else {}
        with torch.inference_mode():
            output = self._model(input_values=input_values, **kwargs)
        embedding = output.embeddings[0].detach().cpu().float().tolist()
        self._embedding_dimension = len(embedding)
        return embedding

    def metadata(self) -> dict[str, Any]:
        return {
            "backend": "transformers.WavLMForXVector",
            "model_id": self.model_id,
            "requested_revision": self.requested_revision,
            "resolved_revision": self._resolved_revision,
            "local_files_only": not self.allow_download,
            "download_explicitly_allowed": self.allow_download,
            "device": self.device,
            "loaded": self._model is not None,
            "embedding_dimension": self._embedding_dimension,
        }


def capability_report(
    *, model_id: str = DEFAULT_MODEL_ID, revision: str = DEFAULT_MODEL_REVISION
) -> dict[str, Any]:
    """Report dependencies/cache without loading or downloading a model."""

    dependencies = {
        name: importlib.util.find_spec(name) is not None
        for name in ("torch", "torchaudio", "transformers", "huggingface_hub")
    }
    cached_revisions: list[str] = []
    cache_inspection_error = ""
    if dependencies["huggingface_hub"]:
        try:
            from huggingface_hub import scan_cache_dir

            cache = scan_cache_dir()
            for repository in cache.repos:
                if repository.repo_id == model_id:
                    cached_revisions.extend(
                        sorted(
                            {
                                str(item.commit_hash)
                                for item in repository.revisions
                                if getattr(item, "commit_hash", None)
                            }
                        )
                    )
        except Exception as exc:
            cache_inspection_error = str(exc)[:500]
    return {
        "schema_version": SCHEMA_VERSION,
        "operation": "speaker_consistency_capability_check",
        "model_id": model_id,
        "requested_revision": revision,
        "dependencies": dependencies,
        "all_dependencies_available": all(dependencies.values()),
        "cached_model_revisions": cached_revisions,
        "cache_ready": bool(cached_revisions),
        "cache_inspection_error": cache_inspection_error,
        "safe_default": "cache_only_no_download",
        "real_analysis_ready_without_download": all(dependencies.values()) and bool(cached_revisions),
        "identity_proof": False,
        "voice_assignment_performed": False,
        "voice_clone_or_training_performed": False,
        "activation_performed": False,
    }


def _prepare_wav(
    item: BoundedWav,
    policy: AudioQualityPolicy,
    *,
    split_on_silence: bool,
) -> tuple[dict[str, Any], list[tuple[str, list[float]]]]:
    samples, rate, format_info = _read_pcm_wav(item.path)
    quality = inspect_audio_quality(samples, rate, policy)
    record: dict[str, Any] = {
        "source_id": item.source_id,
        "range_id": item.range_id,
        "path": str(item.path.expanduser().resolve()),
        "source_start_seconds": item.source_start_seconds,
        "source_end_seconds": item.source_end_seconds,
        "owner_confirmed_target_only": item.owner_confirmed_target_only,
        "declared_source_media_sha256": item.source_media_sha256,
        "sha256": sha256_file(item.path.expanduser().resolve()),
        "format": format_info,
        "quality": quality,
    }
    if quality["status"] == "rejected":
        record["segments"] = []
        return record, []

    ranges = (
        segment_on_silence(samples, rate, policy)
        if split_on_silence
        else [(0, len(samples))]
    )
    if not ranges:
        record["quality"] = dict(quality)
        record["quality"]["status"] = "rejected"
        record["quality"]["rejection_reasons"] = ["no_usable_energy_bounded_segments"]
        record["segments"] = []
        return record, []

    prepared: list[tuple[str, list[float]]] = []
    segment_records: list[dict[str, Any]] = []
    for number, (start, end) in enumerate(ranges, 1):
        segment_id = f"segment_{number:04d}"
        segment_samples = list(samples[start:end])
        resampled = _resample(segment_samples, rate, TARGET_SAMPLE_RATE)
        prepared.append((segment_id, resampled))
        segment_records.append(
            {
                "segment_id": segment_id,
                "start_seconds_in_bounded_wav": round(start / rate, 3),
                "end_seconds_in_bounded_wav": round(end / rate, 3),
                "duration_seconds": round((end - start) / rate, 3),
                "canonical_16khz_float_sha256": _sha256_floats(resampled),
            }
        )
    record["segments"] = segment_records
    return record, prepared


def _decision(score: float, support_threshold: float, reject_threshold: float) -> str:
    if score >= support_threshold:
        return "speaker_consistency_supported_not_identity_proof"
    if score < reject_threshold:
        return "speaker_consistency_not_supported"
    return "indeterminate_manual_source_review_required"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def analyze_speaker_consistency(
    *,
    anchor: BoundedWav,
    candidates: Sequence[BoundedWav],
    backend: EmbeddingBackend | None = None,
    policy: AudioQualityPolicy | None = None,
    split_on_silence: bool = True,
    support_threshold: float = 0.80,
    reject_threshold: float = 0.60,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Build consistency evidence without making any identity/action decision."""

    if not anchor.owner_confirmed_target_only:
        raise ConsistencyEvidenceError(
            "Anchor must be explicitly owner-confirmed as bounded target-only speech."
        )
    if not anchor.source_id.strip():
        raise ConsistencyEvidenceError("Anchor source_id is required.")
    if not candidates:
        raise ConsistencyEvidenceError("At least one independent-source candidate is required.")
    if not (0.0 <= reject_threshold < support_threshold <= 1.0):
        raise ValueError("Thresholds must satisfy 0 <= reject < support <= 1.")
    for candidate in candidates:
        if not candidate.source_id.strip():
            raise ConsistencyEvidenceError("Every candidate source_id is required.")
        if candidate.source_id.strip() == anchor.source_id.strip():
            raise ConsistencyEvidenceError(
                "Candidate and anchor must come from different underlying source IDs."
            )
    for item in (anchor, *candidates):
        if item.source_media_sha256 and not (
            len(item.source_media_sha256) == 64
            and all(character in "0123456789abcdefABCDEF" for character in item.source_media_sha256)
        ):
            raise ConsistencyEvidenceError("Declared source_media_sha256 must be 64 hexadecimal characters.")

    policy = policy or AudioQualityPolicy()
    anchor_record, anchor_segments = _prepare_wav(
        anchor, policy, split_on_silence=split_on_silence
    )
    if not anchor_segments:
        reasons = anchor_record["quality"].get("rejection_reasons", [])
        raise AudioRejectedError(f"Anchor failed quality checks: {', '.join(reasons)}")

    prepared_candidates: list[tuple[dict[str, Any], list[tuple[str, list[float]]]]] = []
    for candidate in candidates:
        record, segments = _prepare_wav(candidate, policy, split_on_silence=split_on_silence)
        identical_bounded_audio = record["sha256"] == anchor_record["sha256"]
        identical_declared_media = bool(
            anchor.source_media_sha256
            and candidate.source_media_sha256
            and anchor.source_media_sha256.lower() == candidate.source_media_sha256.lower()
        )
        independent = not identical_bounded_audio and not identical_declared_media
        record["source_independence"] = {
            "different_declared_source_ids": candidate.source_id != anchor.source_id,
            "bounded_wav_sha256_differs": not identical_bounded_audio,
            "declared_source_media_sha256_differs": (
                anchor.source_media_sha256.lower() != candidate.source_media_sha256.lower()
                if anchor.source_media_sha256 and candidate.source_media_sha256
                else None
            ),
            "status": (
                "accepted_declared_cross_source"
                if independent
                else "rejected_same_audio_or_underlying_media"
            ),
            "note": (
                "Different source IDs are owner/tool provenance; hashes additionally reject exact "
                "duplicate audio or a declared identical underlying media file."
            ),
        }
        record["independent_source_from_anchor"] = independent
        if not independent:
            record["pre_embedding_rejection_reasons"] = [
                "candidate_is_not_cryptographically_distinct_from_anchor"
            ]
            segments = []
        prepared_candidates.append((record, segments))

    backend = backend or WavLMSpeakerEmbedder()
    anchor_embeddings: list[tuple[str, list[float]]] = []
    dimension = 0
    if any(segments for _, segments in prepared_candidates):
        for segment_id, samples in anchor_segments:
            anchor_embeddings.append(
                (segment_id, _normalise(backend.embed(samples, TARGET_SAMPLE_RATE)))
            )
        dimension = len(anchor_embeddings[0][1])
        if any(len(vector) != dimension for _, vector in anchor_embeddings):
            raise ModelUnavailableError("Anchor embedding dimensions are inconsistent.")

        anchor_record["embedding_evidence"] = {
            "status": "computed",
            "segment_count": len(anchor_embeddings),
            "embedding_dimension": dimension,
            "segment_embedding_hashes": [
                {"segment_id": segment_id, "embedding_sha256": _sha256_floats(vector)}
                for segment_id, vector in anchor_embeddings
            ],
        }
    else:
        anchor_record["embedding_evidence"] = {
            "status": "not_computed_no_eligible_independent_candidate",
            "segment_count": 0,
            "embedding_dimension": None,
            "segment_embedding_hashes": [],
        }

    candidate_results: list[dict[str, Any]] = []
    for record, segments in prepared_candidates:
        if not segments:
            record["consistency_evidence"] = {
                "status": "rejected_before_embedding",
                "decision": "no_consistency_evidence",
                "cosine_scores": [],
                "rejection_reasons": record.get(
                    "pre_embedding_rejection_reasons",
                    record["quality"].get("rejection_reasons", []),
                ),
            }
            candidate_results.append(record)
            continue

        candidate_embeddings: list[tuple[str, list[float]]] = []
        for segment_id, samples in segments:
            vector = _normalise(backend.embed(samples, TARGET_SAMPLE_RATE))
            if len(vector) != dimension:
                raise ModelUnavailableError("Candidate embedding dimensions do not match anchor.")
            candidate_embeddings.append((segment_id, vector))

        comparisons: list[dict[str, Any]] = []
        raw_scores: list[float] = []
        for candidate_segment_id, candidate_vector in candidate_embeddings:
            for anchor_segment_id, anchor_vector in anchor_embeddings:
                score = _cosine(candidate_vector, anchor_vector)
                raw_scores.append(score)
                comparisons.append(
                    {
                        "candidate_segment_id": candidate_segment_id,
                        "anchor_segment_id": anchor_segment_id,
                        "cosine_similarity": round(score, 6),
                    }
                )
        median_score = statistics.median(raw_scores)
        record["consistency_evidence"] = {
            "status": "computed",
            "decision": _decision(median_score, support_threshold, reject_threshold),
            "aggregate_method": "median_of_all_cross_source_segment_pair_cosines",
            "median_cosine_similarity": round(median_score, 6),
            "mean_cosine_similarity": round(statistics.fmean(raw_scores), 6),
            "minimum_cosine_similarity": round(min(raw_scores), 6),
            "maximum_cosine_similarity": round(max(raw_scores), 6),
            "support_threshold": support_threshold,
            "reject_threshold": reject_threshold,
            "thresholds_are_operational_not_identity_calibrated": True,
            "cosine_scores": comparisons,
            "candidate_embedding_hashes": [
                {"segment_id": segment_id, "embedding_sha256": _sha256_floats(vector)}
                for segment_id, vector in candidate_embeddings
            ],
            "interpretation": (
                "Similarity to an owner-confirmed anchor across a different recording. "
                "It is consistency evidence only and cannot identify or authorize a person."
            ),
        }
        candidate_results.append(record)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": now_iso(),
        "operation": "bounded_wav_cross_source_speaker_consistency_evidence",
        "model": backend.metadata(),
        "configuration": {
            "target_sample_rate_hz": TARGET_SAMPLE_RATE,
            "split_on_silence": split_on_silence,
            "quality_policy": {
                key: getattr(policy, key)
                for key in policy.__dataclass_fields__
            },
            "support_threshold": support_threshold,
            "reject_threshold": reject_threshold,
        },
        "anchor": anchor_record,
        "candidates": candidate_results,
        "limits_and_actions": {
            "consistency_is_identity_proof": False,
            "may_auto_approve_or_select_a_speaker": False,
            "voice_assignment_performed": False,
            "voice_clone_or_training_performed": False,
            "temporary_ai_activation_performed": False,
            "source_download_performed_by_this_module": False,
            "media_modified": False,
            "only_optional_write": "JSON evidence manifest",
        },
    }
    if output_path:
        _write_json_atomic(output_path, manifest)
    return manifest


__all__ = [
    "AudioQualityPolicy",
    "AudioRejectedError",
    "BoundedWav",
    "ConsistencyEvidenceError",
    "DEFAULT_MODEL_ID",
    "DEFAULT_MODEL_REVISION",
    "ModelUnavailableError",
    "WavLMSpeakerEmbedder",
    "analyze_speaker_consistency",
    "capability_report",
    "inspect_audio_quality",
    "segment_on_silence",
]
