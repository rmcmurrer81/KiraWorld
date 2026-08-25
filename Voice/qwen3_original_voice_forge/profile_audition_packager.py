from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
from typing import Any, Iterable
import wave

import feasibility_worker
import profile_audition_planner as planner


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_SCHEMA = "kira.qwen3.profile-audition-evidence-package.v1"
PACKAGE_STATUS = "NONBINDING_AUDITION_EVIDENCE_NOT_APPROVED_NOT_ACTIVE"
RETRY_SCHEMA = "kira-qwen3-profile-audition-retry-plan-v1"
RETRY_STATUS = "NONBINDING_ASR_REGENERATION_ONLY_NOT_APPROVED_NOT_ACTIVE"
RECEIPT_SCHEMA = "kira-qwen3-voice-design-feasibility-receipt-v1"
RECEIPT_STATUS = "TECHNICAL_FEASIBILITY_SAMPLE_NOT_APPROVED_NOT_ACTIVE"
ASR_SCHEMA = "kira-qwen3-voice-design-asr-audit-v1"
ASR_AUDITOR = "torchaudio_WAV2VEC2_ASR_BASE_960H_greedy"
ASR_NOTE = "ASR WER is an intelligibility proxy, not a naturalness or identity rating."
ASR_CHECKPOINT = {
    "filename": "wav2vec2_fairseq_base_ls960_asr_ls960.pth",
    "bytes": 377_664_473,
    "sha256": "488fd4f16de84438ffc945334278c1b9fb9b7159a806c1080b16111a958c945d",
}
MAX_ASR_WER = 0.25
MAX_JSON_BYTES = 1024 * 1024
MAX_REQUEST_BYTES = 16 * 1024
MAX_RECEIPT_BYTES = 128 * 1024
MAX_ASR_BYTES = 64 * 1024
MAX_WAV_BYTES = 8 * 1024 * 1024
MAX_STRING_LENGTH = 16 * 1024
MAX_CONTAINER_ITEMS = 2048
MAX_DEPTH = 20

EXPECTED_PALETTES = ("calm_clear", "warm_rounded", "grounded_assured")
EXPECTED_RETRIES = {
    "grounded_assured": {
        "failed_candidate_id": "emily_carter_generated_expert_c3_a8ffe79a1e21",
        "retry_candidate_id": "emily_carter_generated_expert_c3r1_2c76f489708a",
    },
    "warm_rounded": {
        "failed_candidate_id": "emily_carter_generated_expert_c2_ae20eb201c77",
        "retry_candidate_id": "emily_carter_generated_expert_c2r1_b35a5b3b28e1",
    },
}
EMILY_SUBJECT_ID = "emily_carter_generated_expert"
RETRY_TOP_KEYS = {
    "schema",
    "status",
    "source_integration_sha256",
    "source_audition_plan",
    "retry_policy",
    "retries",
    "assertions",
}
RETRY_SOURCE_KEYS = {"filename", "bytes", "sha256"}
RETRY_POLICY = {
    "reason": "pinned ASR word error rate exceeded 0.25",
    "attempt": 1,
    "seed_change": "original seed plus one",
    "text_change": (
        "replace acronym and audition wording with a plain-language "
        "role-specific clarity sentence"
    ),
    "voice_traits_changed": False,
    "failed_audio_is_preserved_as_negative_evidence": True,
}
EXPECTED_RETRY_TEXT = (
    "This voice explains artificial intelligence and computer programming in a "
    "clear, patient way. It separates facts from assumptions and offers practical "
    "next steps."
)
RETRY_ENTRY_KEYS = {
    "palette_id",
    "failed_candidate_id",
    "failed_request_sha256",
    "failed_wav_sha256",
    "failed_asr_report_sha256",
    "failed_word_error_rate",
    "retry_request_relative_path",
    "retry_request_sha256",
    "retry_candidate_id",
}
RETRY_ASSERTIONS = {
    "named_person_imitation": False,
    "source_recording_used": False,
    "voice_assigned": False,
    "voice_activated": False,
    "route_changed": False,
}
RECEIPT_KEYS = {
    "audio",
    "candidate_id",
    "gpu_memory",
    "limitations",
    "model_files",
    "model_revision",
    "rendered_design_prompt",
    "request_path",
    "request_sha256",
    "runtime",
    "schema",
    "status",
    "timing",
    "voice_traits",
}
RECEIPT_AUDIO_KEYS = {
    "bytes",
    "channels",
    "duration_seconds",
    "frames",
    "peak_float",
    "rms_float",
    "sample_rate_hz",
    "sample_width_bytes",
    "sha256",
}
RECEIPT_GPU_KEYS = {
    "final_allocated_bytes",
    "final_reserved_bytes",
    "peak_allocated_bytes",
    "peak_reserved_bytes",
}
RECEIPT_RUNTIME_KEYS = {
    "attention",
    "capability",
    "cuda",
    "device",
    "dtype",
    "network_contract",
    "python",
    "torch",
    "torchaudio",
    "transformers",
}
RECEIPT_TIMING_KEYS = {"generation_seconds", "load_seconds"}
RECEIPT_LIMITATIONS = [
    "No person identity, likeness, or named-voice claim is made.",
    "This sample has not passed listening, collision, pronunciation, or activation review.",
    "This worker does not bind, route, play, publish, or replace a voice.",
    (
        "Production remains blocked pending reviewed OS-enforced isolation and a "
        "sealed parent/worker authority."
    ),
]
ASR_KEYS = {
    "schema",
    "status",
    "auditor",
    "torchaudio",
    "asr_checkpoint",
    "input",
    "device",
    "model_load_seconds",
    "asr_seconds",
    "expected",
    "transcript",
    "word_error_rate",
    "note",
}
ASR_INPUT_KEYS = {
    "wav_filename",
    "wav_sha256",
    "request_filename",
    "request_sha256",
}
WINDOWS_RESERVED_NAMES = {
    "aux",
    "clock$",
    "con",
    "nul",
    "prn",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}


@dataclass(frozen=True)
class CapturedFile:
    path: Path
    data: bytes
    sha256: str

    @property
    def size(self) -> int:
        return len(self.data)


@dataclass(frozen=True)
class RequestContext:
    subject_id: str
    palette_id: str
    source_kind: str
    file: CapturedFile
    document: dict[str, Any]

    @property
    def candidate_id(self) -> str:
        return str(self.document["candidate_id"])


@dataclass(frozen=True)
class RunEvidence:
    request: RequestContext
    receipt_file: CapturedFile
    receipt: dict[str, Any]
    asr_file: CapturedFile
    asr: dict[str, Any]
    wav_file: CapturedFile
    wav_info: dict[str, Any]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} keys do not match the required schema")
    return value


def _require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{label} is not a lowercase SHA-256")
    return value


def _require_nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} is not a nonnegative integer")
    return value


def _require_finite_number(value: object, label: str, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} is not numeric")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise ValueError(f"{label} is outside the allowed numeric range")
    return result


def _require_identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) > 64
        or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,63}", value)
    ):
        raise ValueError(f"{label} is not a safe candidate identifier")
    return value


def _safe_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError(f"{label} is not a bounded relative path")
    if "\\" in value or ":" in value:
        raise ValueError(f"{label} is not a POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{label} is unsafe")
    for part in path.parts:
        if part.endswith((".", " ")) or part.rstrip(" .").lower() in WINDOWS_RESERVED_NAMES:
            raise ValueError(f"{label} contains an unsafe Windows component")
    return value


def _validate_json_shape(value: object, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise ValueError("JSON nesting is too deep")
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("JSON contains a non-finite number")
        return
    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            raise ValueError("JSON string is too long")
        if any(ord(character) < 32 for character in value):
            raise ValueError("JSON string contains a control character")
        return
    if isinstance(value, list):
        if len(value) > MAX_CONTAINER_ITEMS:
            raise ValueError("JSON list is too large")
        for item in value:
            _validate_json_shape(item, depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > MAX_CONTAINER_ITEMS:
            raise ValueError("JSON object is too large")
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ValueError("JSON key is invalid")
            _validate_json_shape(key, depth + 1)
            _validate_json_shape(item, depth + 1)
        return
    raise ValueError("JSON contains an unsupported value")


def _parse_json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"{label} is not valid UTF-8") from error
    document = json.loads(
        text,
        object_pairs_hook=strict_object,
        parse_constant=reject_constant,
    )
    _validate_json_shape(document)
    if not isinstance(document, dict):
        raise ValueError(f"{label} must be a JSON object")
    return document


def _is_link_or_reparse(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError as error:
        raise ValueError(f"cannot inspect path safely: {path.name}") from error
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    file_attributes = getattr(info, "st_file_attributes", 0)
    return bool(
        stat.S_ISLNK(info.st_mode)
        or file_attributes & reparse_flag
        or path.is_symlink()
        or getattr(path, "is_junction", lambda: False)()
    )


def _validate_existing_absolute(path: Path, *, directory: bool, label: str) -> Path:
    supplied = Path(path)
    if not supplied.is_absolute() or ".." in supplied.parts:
        raise ValueError(f"{label} must be an absolute path without traversal")
    current = Path(supplied.anchor)
    for part in supplied.parts[1:]:
        current /= part
        if not current.exists():
            raise ValueError(f"{label} is missing")
        if _is_link_or_reparse(current):
            raise ValueError(f"{label} contains a link, junction, or reparse point")
    if directory and not supplied.is_dir():
        raise ValueError(f"{label} is not a directory")
    if not directory and not supplied.is_file():
        raise ValueError(f"{label} is not a regular file")
    return supplied.resolve(strict=True)


def _outside_repository(path: Path, label: str) -> None:
    try:
        path.relative_to(REPOSITORY_ROOT)
    except ValueError:
        return
    raise ValueError(f"{label} must remain outside the KiraWorld repository")


def _capture_file(path: Path, maximum: int, label: str) -> CapturedFile:
    inspected = _validate_existing_absolute(path, directory=False, label=label)
    before = inspected.stat()
    with inspected.open("rb") as source:
        payload = source.read(maximum + 1)
    after = inspected.stat()
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_identity != after_identity:
        raise ValueError(f"{label} changed while it was read")
    if not payload or len(payload) > maximum:
        raise ValueError(f"{label} size is outside the allowed bound")
    if len(payload) != before.st_size:
        raise ValueError(f"{label} could not be read completely")
    return CapturedFile(inspected, payload, sha256_bytes(payload))


def _safe_child(root: Path, relative: str, label: str) -> Path:
    safe = _safe_relative_path(relative, label)
    candidate = root.joinpath(*PurePosixPath(safe).parts)
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} escapes its root") from error
    return candidate


def _exact_entries(directory: Path, expected: set[str], label: str) -> None:
    actual: set[str] = set()
    for entry in directory.iterdir():
        if _is_link_or_reparse(entry):
            raise ValueError(f"{label} contains a link, junction, or reparse point")
        if not entry.is_file() and not entry.is_dir():
            raise ValueError(f"{label} contains an unsupported entry")
        actual.add(entry.name)
    if actual != expected:
        raise ValueError(f"{label} scope is not exact")


def _load_request_context(
    path: Path, subject_id: str, palette_id: str, source_kind: str
) -> RequestContext:
    first = _capture_file(path, MAX_REQUEST_BYTES, "request")
    worker_document = feasibility_worker.load_request(first.path)
    second = _capture_file(path, MAX_REQUEST_BYTES, "request")
    if first.data != second.data:
        raise ValueError("request changed across feasibility-worker validation")
    document = _parse_json_bytes(first.data, "request")
    if document != worker_document:
        raise ValueError("request differs from the feasibility-worker interpretation")
    return RequestContext(subject_id, palette_id, source_kind, first, document)


def _expected_model_files() -> list[dict[str, object]]:
    return [
        {"path": path, "bytes": size, "sha256": digest}
        for path, (size, digest) in feasibility_worker.EXPECTED_MODEL_FILES.items()
    ]


def _inspect_wav_bytes(payload: bytes) -> dict[str, Any]:
    if len(payload) < 44 or payload[:4] != b"RIFF" or payload[8:12] != b"WAVE":
        raise ValueError("WAV is not a canonical RIFF/WAVE file")
    if struct.unpack_from("<I", payload, 4)[0] + 8 != len(payload):
        raise ValueError("WAV RIFF length does not bind the complete file")
    try:
        with wave.open(io.BytesIO(payload), "rb") as audio:
            channels = audio.getnchannels()
            sample_width = audio.getsampwidth()
            sample_rate = audio.getframerate()
            frames = audio.getnframes()
            compression = audio.getcomptype()
            frame_bytes = audio.readframes(frames)
            if audio.readframes(1):
                raise ValueError("WAV reports data after its declared frames")
    except (EOFError, wave.Error) as error:
        raise ValueError("WAV structure is invalid") from error
    if channels != 1 or sample_width != 2 or sample_rate != 24_000 or compression != "NONE":
        raise ValueError("WAV is not canonical mono PCM16 24 kHz")
    if len(frame_bytes) != frames * channels * sample_width:
        raise ValueError("WAV frame payload is truncated")
    duration = frames / sample_rate
    if not 0.25 <= duration <= 60.0:
        raise ValueError("WAV duration is outside the allowed bound")
    return {
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate_hz": sample_rate,
        "frames": frames,
        "duration_seconds": duration,
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
    }


def _validate_receipt(
    receipt: dict[str, Any], request: RequestContext, wav: CapturedFile, wav_info: dict[str, Any]
) -> None:
    value = _require_exact_keys(receipt, RECEIPT_KEYS, "receipt")
    if value["schema"] != RECEIPT_SCHEMA or value["status"] != RECEIPT_STATUS:
        raise ValueError("receipt schema or status is unsupported")
    if value["candidate_id"] != request.candidate_id:
        raise ValueError("receipt candidate does not match the request")
    if value["request_path"] != request.file.path.name:
        raise ValueError("receipt request filename does not match")
    if value["request_sha256"] != request.file.sha256:
        raise ValueError("receipt request hash does not match")
    if value["voice_traits"] != request.document["voice_traits"]:
        raise ValueError("receipt voice traits do not match the request")
    expected_prompt = feasibility_worker.render_design_prompt(request.document["voice_traits"])
    if value["rendered_design_prompt"] != expected_prompt:
        raise ValueError("receipt rendered prompt does not match the current worker")
    if value["model_revision"] != feasibility_worker.MODEL_REVISION:
        raise ValueError("receipt model revision is not pinned")
    if value["model_files"] != _expected_model_files():
        raise ValueError("receipt does not bind the exact 13-file model manifest")

    audio = _require_exact_keys(value["audio"], RECEIPT_AUDIO_KEYS, "receipt audio")
    if audio["sha256"] != wav.sha256 or audio["bytes"] != wav.size:
        raise ValueError("receipt audio hash or size does not bind the WAV")
    for key in ("channels", "sample_width_bytes", "sample_rate_hz", "frames"):
        if audio[key] != wav_info[key]:
            raise ValueError(f"receipt audio {key} does not match the WAV")
    duration = _require_finite_number(audio["duration_seconds"], "audio duration")
    if not math.isclose(duration, wav_info["duration_seconds"], rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("receipt audio duration does not match the WAV")
    peak = _require_finite_number(audio["peak_float"], "audio peak")
    rms = _require_finite_number(audio["rms_float"], "audio RMS")
    if peak <= 0.001 or peak > 1.5 or rms <= 0.0001 or rms > peak:
        raise ValueError("receipt audio amplitude evidence is implausible")

    memory = _require_exact_keys(value["gpu_memory"], RECEIPT_GPU_KEYS, "GPU memory")
    for key, item in memory.items():
        _require_nonnegative_int(item, f"GPU memory {key}")
    timing = _require_exact_keys(value["timing"], RECEIPT_TIMING_KEYS, "timing")
    for key, item in timing.items():
        _require_finite_number(item, f"timing {key}")
    runtime = _require_exact_keys(value["runtime"], RECEIPT_RUNTIME_KEYS, "runtime")
    if runtime["attention"] != "sdpa" or runtime["dtype"] != "bfloat16":
        raise ValueError("receipt runtime does not match the bounded worker")
    if runtime["network_contract"] != (
        "tool_restricted_network_plus_offline_flags_not_production_os_isolation"
    ):
        raise ValueError("receipt network contract is unsupported")
    capability = runtime["capability"]
    if (
        not isinstance(capability, list)
        or len(capability) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in capability)
    ):
        raise ValueError("receipt CUDA capability is invalid")
    for key in ("cuda", "device", "python", "torch", "torchaudio", "transformers"):
        item = runtime[key]
        if not isinstance(item, str) or not item or len(item) > 128:
            raise ValueError(f"receipt runtime {key} is invalid")
    if value["limitations"] != RECEIPT_LIMITATIONS:
        raise ValueError("receipt limitations do not preserve the worker boundary")


def _validate_asr(
    report: dict[str, Any], request: RequestContext, wav: CapturedFile, *, passing: bool
) -> float:
    value = _require_exact_keys(report, ASR_KEYS, "ASR report")
    expected_status = "PASS" if passing else "REVIEW"
    if value["schema"] != ASR_SCHEMA or value["status"] != expected_status:
        raise ValueError("ASR report schema or status is unsupported")
    if value["auditor"] != ASR_AUDITOR or value["asr_checkpoint"] != ASR_CHECKPOINT:
        raise ValueError("ASR report is not bound to the pinned auditor and checkpoint")
    if value["note"] != ASR_NOTE:
        raise ValueError("ASR report note is not the bounded proxy disclosure")
    report_input = _require_exact_keys(value["input"], ASR_INPUT_KEYS, "ASR input")
    if report_input != {
        "wav_filename": "candidate.wav",
        "wav_sha256": wav.sha256,
        "request_filename": request.file.path.name,
        "request_sha256": request.file.sha256,
    }:
        raise ValueError("ASR report input does not bind the request and WAV")
    if value["expected"] != request.document["text"]:
        raise ValueError("ASR expected text does not match the request")
    if not isinstance(value["transcript"], str) or not value["transcript"].strip():
        raise ValueError("ASR transcript is missing")
    if len(value["transcript"]) > 4096:
        raise ValueError("ASR transcript is too long")
    for key in ("torchaudio", "device"):
        if not isinstance(value[key], str) or not value[key] or len(value[key]) > 128:
            raise ValueError(f"ASR {key} is invalid")
    _require_finite_number(value["model_load_seconds"], "ASR model load seconds")
    _require_finite_number(value["asr_seconds"], "ASR seconds")
    wer = _require_finite_number(value["word_error_rate"], "ASR word error rate")
    if passing and wer > MAX_ASR_WER:
        raise ValueError("passing ASR word error rate exceeds 0.25")
    if not passing and wer <= MAX_ASR_WER:
        raise ValueError("negative ASR evidence does not exceed the retry threshold")
    return wer


def _validate_original_plan(
    plan_path: Path,
) -> tuple[CapturedFile, dict[str, Any], dict[tuple[str, str], RequestContext]]:
    path = _validate_existing_absolute(plan_path, directory=False, label="original plan")
    _outside_repository(path, "original plan")
    root = path.parent
    _outside_repository(root, "original plan root")
    if path.name != "audition-request-plan.json":
        raise ValueError("original plan filename is not exact")
    _exact_entries(root, {"audition-request-plan.json", "requests"}, "original plan root")
    requests_root = _validate_existing_absolute(root / "requests", directory=True, label="requests root")
    plan_file = _capture_file(path, MAX_JSON_BYTES, "original plan")
    document = _parse_json_bytes(plan_file.data, "original plan")
    expected = planner.build_request_plan()
    if document != expected:
        raise ValueError("original plan does not exactly match the current trusted source plan")
    bundles = document["bundles"]
    if len(bundles) != 6:
        raise ValueError("original plan must contain exactly six bundles")
    expected_subjects = {str(bundle["subject_id"]) for bundle in bundles}
    _exact_entries(requests_root, expected_subjects, "original request root")
    contexts: dict[tuple[str, str], RequestContext] = {}
    for bundle in bundles:
        subject_id = str(bundle["subject_id"])
        variants = bundle["variants"]
        if [variant["palette_id"] for variant in variants] != list(EXPECTED_PALETTES):
            raise ValueError("bundle palettes are missing, extra, duplicated, or reordered")
        bundle_root = _validate_existing_absolute(
            requests_root / subject_id, directory=True, label="bundle request root"
        )
        expected_files = {PurePosixPath(variant["request_relative_path"]).name for variant in variants}
        _exact_entries(bundle_root, expected_files, "bundle request root")
        for variant in variants:
            palette_id = str(variant["palette_id"])
            relative = _safe_relative_path(variant["request_relative_path"], "request path")
            request_path = _safe_child(root, relative, "request path")
            context = _load_request_context(request_path, subject_id, palette_id, "original")
            if context.file.sha256 != variant["request_sha256"]:
                raise ValueError("original request hash does not match the plan")
            if context.document != variant["request"]:
                raise ValueError("original request does not match the embedded plan request")
            key = (subject_id, palette_id)
            if key in contexts:
                raise ValueError("duplicate original request slot")
            contexts[key] = context
    if len(contexts) != 18:
        raise ValueError("original plan does not resolve to exactly 18 requests")
    return plan_file, document, contexts


def _validate_retry_plan(
    retry_path: Path,
    original_plan_file: CapturedFile,
    original_plan: dict[str, Any],
    originals: dict[tuple[str, str], RequestContext],
) -> tuple[CapturedFile, dict[str, Any], dict[str, RequestContext], dict[str, dict[str, Any]]]:
    path = _validate_existing_absolute(retry_path, directory=False, label="retry plan")
    _outside_repository(path, "retry plan")
    root = path.parent
    _outside_repository(root, "retry plan root")
    if path.name != "retry-plan.json":
        raise ValueError("retry plan filename is not exact")
    _exact_entries(root, {"retry-plan.json", "requests"}, "retry plan root")
    requests_root = _validate_existing_absolute(root / "requests", directory=True, label="retry requests root")
    retry_file = _capture_file(path, MAX_JSON_BYTES, "retry plan")
    document = _require_exact_keys(_parse_json_bytes(retry_file.data, "retry plan"), RETRY_TOP_KEYS, "retry plan")
    if document["schema"] != RETRY_SCHEMA or document["status"] != RETRY_STATUS:
        raise ValueError("retry plan schema or status is unsupported")
    if document["source_integration_sha256"] != original_plan["source"]["sha256"]:
        raise ValueError("retry plan does not bind the trusted source integration plan")
    source_plan = _require_exact_keys(document["source_audition_plan"], RETRY_SOURCE_KEYS, "retry source plan")
    if source_plan != {
        "filename": original_plan_file.path.name,
        "bytes": original_plan_file.size,
        "sha256": original_plan_file.sha256,
    }:
        raise ValueError("retry plan does not bind the exact original plan")
    if document["retry_policy"] != RETRY_POLICY or document["assertions"] != RETRY_ASSERTIONS:
        raise ValueError("retry policy or assertions are not exact")
    retries = document["retries"]
    if not isinstance(retries, list) or len(retries) != 2:
        raise ValueError("retry plan must contain exactly two retries")
    by_palette: dict[str, dict[str, Any]] = {}
    for raw in retries:
        entry = _require_exact_keys(raw, RETRY_ENTRY_KEYS, "retry entry")
        palette_id = entry["palette_id"]
        if palette_id not in EXPECTED_RETRIES or palette_id in by_palette:
            raise ValueError("retry palette is missing, extra, or duplicated")
        expected_ids = EXPECTED_RETRIES[palette_id]
        if entry["failed_candidate_id"] != expected_ids["failed_candidate_id"]:
            raise ValueError("retry failed candidate is not the expected Emily original")
        if entry["retry_candidate_id"] != expected_ids["retry_candidate_id"]:
            raise ValueError("retry candidate is not the expected retry1 ID")
        _require_identifier(entry["failed_candidate_id"], "failed candidate id")
        _require_identifier(entry["retry_candidate_id"], "retry candidate id")
        for field in (
            "failed_request_sha256",
            "failed_wav_sha256",
            "failed_asr_report_sha256",
            "retry_request_sha256",
        ):
            _require_sha256(entry[field], field)
        failed_wer = _require_finite_number(entry["failed_word_error_rate"], "failed WER")
        if failed_wer <= MAX_ASR_WER:
            raise ValueError("retry entry failed WER does not exceed 0.25")
        original = originals[(EMILY_SUBJECT_ID, palette_id)]
        if original.candidate_id != entry["failed_candidate_id"]:
            raise ValueError("retry failed candidate does not match the original plan slot")
        if original.file.sha256 != entry["failed_request_sha256"]:
            raise ValueError("retry failed request hash does not match the original request")
        by_palette[str(palette_id)] = entry
    if set(by_palette) != set(EXPECTED_RETRIES):
        raise ValueError("retry plan does not contain the exact two Emily retry slots")

    expected_retry_files = {
        PurePosixPath(_safe_relative_path(entry["retry_request_relative_path"], "retry request path")).name
        for entry in by_palette.values()
    }
    _exact_entries(requests_root, expected_retry_files, "retry requests root")
    contexts: dict[str, RequestContext] = {}
    for palette_id, entry in by_palette.items():
        relative = _safe_relative_path(entry["retry_request_relative_path"], "retry request path")
        request_path = _safe_child(root, relative, "retry request path")
        context = _load_request_context(request_path, EMILY_SUBJECT_ID, palette_id, "retry1")
        original = originals[(EMILY_SUBJECT_ID, palette_id)]
        if context.candidate_id != entry["retry_candidate_id"]:
            raise ValueError("retry request candidate ID does not match the retry plan")
        if context.file.sha256 != entry["retry_request_sha256"]:
            raise ValueError("retry request hash does not match the retry plan")
        for field in (
            "schema",
            "language",
            "voice_traits",
            "intent",
            "named_person_imitation",
            "nonproduction_feasibility",
        ):
            if context.document[field] != original.document[field]:
                raise ValueError(f"retry request unexpectedly changes {field}")
        if context.document["seed"] != original.document["seed"] + 1:
            raise ValueError("retry seed is not exactly original seed plus one")
        if context.document["text"] != EXPECTED_RETRY_TEXT:
            raise ValueError("retry text is not the exact reviewed plain-language text")
        contexts[palette_id] = context
    return retry_file, document, contexts, by_palette


def _load_run(
    run_root: Path, request: RequestContext, *, passing: bool
) -> RunEvidence:
    run_dir = _validate_existing_absolute(
        run_root / request.candidate_id, directory=True, label="candidate run"
    )
    _exact_entries(run_dir, {"candidate.wav", "receipt.json", "asr-audit.json"}, "candidate run")
    wav_file = _capture_file(run_dir / "candidate.wav", MAX_WAV_BYTES, "candidate WAV")
    wav_info = _inspect_wav_bytes(wav_file.data)
    receipt_file = _capture_file(run_dir / "receipt.json", MAX_RECEIPT_BYTES, "receipt")
    receipt = _parse_json_bytes(receipt_file.data, "receipt")
    _validate_receipt(receipt, request, wav_file, wav_info)
    asr_file = _capture_file(run_dir / "asr-audit.json", MAX_ASR_BYTES, "ASR report")
    asr = _parse_json_bytes(asr_file.data, "ASR report")
    _validate_asr(asr, request, wav_file, passing=passing)
    return RunEvidence(request, receipt_file, receipt, asr_file, asr, wav_file, wav_info)


def _validate_runs(
    original_runs_root: Path,
    retry_runs_root: Path,
    originals: dict[tuple[str, str], RequestContext],
    retries: dict[str, RequestContext],
    retry_entries: dict[str, dict[str, Any]],
) -> tuple[list[RunEvidence], list[RunEvidence]]:
    original_root = _validate_existing_absolute(
        original_runs_root, directory=True, label="original runs root"
    )
    retry_root = _validate_existing_absolute(retry_runs_root, directory=True, label="retry runs root")
    _outside_repository(original_root, "original runs root")
    _outside_repository(retry_root, "retry runs root")
    _exact_entries(original_root, {context.candidate_id for context in originals.values()}, "original runs root")
    _exact_entries(retry_root, {context.candidate_id for context in retries.values()}, "retry runs root")
    selected: list[RunEvidence] = []
    negatives: list[RunEvidence] = []
    for key in sorted(originals):
        subject_id, palette_id = key
        context = originals[key]
        is_negative = subject_id == EMILY_SUBJECT_ID and palette_id in EXPECTED_RETRIES
        evidence = _load_run(original_root, context, passing=not is_negative)
        if is_negative:
            entry = retry_entries[palette_id]
            wer = float(evidence.asr["word_error_rate"])
            if not math.isclose(wer, float(entry["failed_word_error_rate"]), rel_tol=0.0, abs_tol=1e-9):
                raise ValueError("negative ASR WER does not match the retry plan")
            if evidence.wav_file.sha256 != entry["failed_wav_sha256"]:
                raise ValueError("negative WAV hash does not match the retry plan")
            if evidence.asr_file.sha256 != entry["failed_asr_report_sha256"]:
                raise ValueError("negative ASR report hash does not match the retry plan")
            negatives.append(evidence)
        else:
            selected.append(evidence)
    for palette_id in sorted(retries):
        selected.append(_load_run(retry_root, retries[palette_id], passing=True))
    if len(selected) != 18 or len(negatives) != 2:
        raise ValueError("selection must resolve to exactly 18 passes and two negatives")
    selected_slots = {(item.request.subject_id, item.request.palette_id) for item in selected}
    expected_slots = set(originals)
    if selected_slots != expected_slots or len(selected_slots) != len(selected):
        raise ValueError("selection has an ambiguous, missing, extra, or duplicated slot")
    for item in selected:
        should_retry = item.request.subject_id == EMILY_SUBJECT_ID and item.request.palette_id in EXPECTED_RETRIES
        if should_retry != (item.request.source_kind == "retry1"):
            raise ValueError("Emily retry selection policy was not followed exactly")
    return selected, negatives


def _validate_output_root(path: Path, inputs: Iterable[Path]) -> Path:
    supplied = Path(path)
    if not supplied.is_absolute() or ".." in supplied.parts:
        raise ValueError("output root must be a new absolute path without traversal")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}", supplied.name):
        raise ValueError("output root name is unsafe")
    if supplied.name.endswith((".", " ")) or supplied.name.rstrip(" .").lower() in WINDOWS_RESERVED_NAMES:
        raise ValueError("output root name is unsafe on Windows")
    parent = _validate_existing_absolute(supplied.parent, directory=True, label="output parent")
    _outside_repository(parent, "output parent")
    target = parent / supplied.name
    if target.exists():
        raise ValueError("output root already exists")
    resolved_inputs = [Path(item).resolve(strict=True) for item in inputs]
    for input_path in resolved_inputs:
        try:
            target.relative_to(input_path if input_path.is_dir() else input_path.parent)
        except ValueError:
            pass
        else:
            raise ValueError("output root must not be inside an input root")
        try:
            input_path.relative_to(target)
        except ValueError:
            pass
        else:
            raise ValueError("output root must not contain an input root")
    return target


def _artifact_record(relative_path: str, payload: bytes, source_scope: str, source_relative_path: str) -> dict[str, Any]:
    return {
        "relative_path": _safe_relative_path(relative_path, "artifact path"),
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
        "source_scope": source_scope,
        "source_relative_path": _safe_relative_path(source_relative_path, "source artifact path"),
    }


def _add_copy(
    copies: list[tuple[str, bytes]],
    inventory: list[dict[str, Any]],
    relative_path: str,
    captured: CapturedFile,
    source_scope: str,
    source_relative_path: str,
) -> None:
    record = _artifact_record(relative_path, captured.data, source_scope, source_relative_path)
    if record["sha256"] != captured.sha256:
        raise ValueError("captured artifact hash changed in memory")
    copies.append((relative_path, captured.data))
    inventory.append(record)


def _build_package(
    original_plan_file: CapturedFile,
    retry_plan_file: CapturedFile,
    selected: list[RunEvidence],
    negatives: list[RunEvidence],
) -> tuple[list[tuple[str, bytes]], dict[str, Any]]:
    copies: list[tuple[str, bytes]] = []
    inventory: list[dict[str, Any]] = []
    _add_copy(
        copies,
        inventory,
        "provenance/audition-request-plan.json",
        original_plan_file,
        "original_plan",
        original_plan_file.path.name,
    )
    _add_copy(
        copies,
        inventory,
        "provenance/retry-plan.json",
        retry_plan_file,
        "retry_plan",
        retry_plan_file.path.name,
    )
    selections: list[dict[str, Any]] = []
    for evidence in sorted(selected, key=lambda item: (item.request.subject_id, item.request.palette_id)):
        request = evidence.request
        base = f"selected/{request.subject_id}/{request.palette_id}/{request.candidate_id}"
        request_target = f"{base}/{request.file.path.name}"
        source_scope = "retry_runs" if request.source_kind == "retry1" else "original_runs"
        request_scope = "retry_plan" if request.source_kind == "retry1" else "original_plan"
        request_plan_root = (
            retry_plan_file.path.parent
            if request.source_kind == "retry1"
            else original_plan_file.path.parent
        )
        request_source_relative = request.file.path.relative_to(request_plan_root).as_posix()
        _add_copy(
            copies,
            inventory,
            request_target,
            request.file,
            request_scope,
            request_source_relative,
        )
        for filename, captured in (
            ("receipt.json", evidence.receipt_file),
            ("asr-audit.json", evidence.asr_file),
            ("candidate.wav", evidence.wav_file),
        ):
            _add_copy(
                copies,
                inventory,
                f"{base}/{filename}",
                captured,
                source_scope,
                f"{request.candidate_id}/{filename}",
            )
        selections.append(
            {
                "subject_id": request.subject_id,
                "palette_id": request.palette_id,
                "candidate_id": request.candidate_id,
                "attempt": request.source_kind,
                "word_error_rate": evidence.asr["word_error_rate"],
                "artifact_root": base,
            }
        )

    negative_records: list[dict[str, Any]] = []
    for evidence in sorted(negatives, key=lambda item: item.request.palette_id):
        request = evidence.request
        base = f"negative-evidence/{request.subject_id}/{request.palette_id}/{request.candidate_id}"
        _add_copy(
            copies,
            inventory,
            f"{base}/{request.file.path.name}",
            request.file,
            "original_plan",
            request.file.path.relative_to(original_plan_file.path.parent).as_posix(),
        )
        for filename, captured in (
            ("receipt.json", evidence.receipt_file),
            ("asr-audit.json", evidence.asr_file),
        ):
            _add_copy(
                copies,
                inventory,
                f"{base}/{filename}",
                captured,
                "original_runs",
                f"{request.candidate_id}/{filename}",
            )
        negative_records.append(
            {
                "subject_id": request.subject_id,
                "palette_id": request.palette_id,
                "candidate_id": request.candidate_id,
                "word_error_rate": evidence.asr["word_error_rate"],
                "copied_artifact_root": base,
                "omitted_wav": {
                    "filename": "candidate.wav",
                    "bytes": evidence.wav_file.size,
                    "sha256": evidence.wav_file.sha256,
                    "disposition": "private_local_negative_artifact_not_copied",
                    "statement": (
                        "The failed WAV remains a private local negative artifact and "
                        "is intentionally not copied."
                    ),
                },
            }
        )
    relative_paths = [record["relative_path"] for record in inventory]
    if len(relative_paths) != len(set(relative_paths)):
        raise ValueError("package artifact target paths are ambiguous")
    if len(inventory) != 80:
        raise ValueError("package inventory must contain exactly 80 copied artifacts")

    manifest = {
        "schema": PACKAGE_SCHEMA,
        "status": PACKAGE_STATUS,
        "source_plans": {
            "original": {
                "filename": original_plan_file.path.name,
                "bytes": original_plan_file.size,
                "sha256": original_plan_file.sha256,
            },
            "retry1": {
                "filename": retry_plan_file.path.name,
                "bytes": retry_plan_file.size,
                "sha256": retry_plan_file.sha256,
            },
        },
        "model_manifest": {
            "revision": feasibility_worker.MODEL_REVISION,
            "file_count": 13,
            "files": _expected_model_files(),
        },
        "asr_gate": {
            "checkpoint": ASR_CHECKPOINT,
            "passing_status": "PASS",
            "maximum_word_error_rate": MAX_ASR_WER,
        },
        "summary": {
            "source_bundle_count": 6,
            "palette_count_per_bundle": 3,
            "selected_passing_attempt_count": 18,
            "negative_attempt_count": 2,
            "copied_artifact_count": len(inventory),
        },
        "selections": selections,
        "negative_evidence": negative_records,
        "artifact_inventory": sorted(inventory, key=lambda item: item["relative_path"]),
        "assertions": {
            "nonbinding": True,
            "human_listening_review_still_required": True,
            "voice_binding_created": False,
            "voice_activated": False,
            "route_changed": False,
            "profile_mutation_performed": False,
            "audio_generated_by_packager": False,
            "model_files_included": False,
            "failed_wavs_copied": False,
            "manifest_self_hash_excluded_to_avoid_recursive_self_reference": True,
        },
    }
    return copies, manifest


def _write_exclusive(path: Path, payload: bytes) -> None:
    # Output starts brand-new. Build each directory one component at a time and
    # reject any reparse point that appears before the exclusive file create.
    root = path
    while root.parent != root and not root.exists():
        root = root.parent
    if not root.is_dir() or _is_link_or_reparse(root):
        raise ValueError("artifact destination parent is unsafe")
    relative_parts = path.parent.relative_to(root).parts
    current = root
    for part in relative_parts:
        current /= part
        if current.exists():
            if not current.is_dir() or _is_link_or_reparse(current):
                raise ValueError("artifact destination contains a reparse point")
        else:
            current.mkdir()
    with path.open("xb") as destination:
        destination.write(payload)
        destination.flush()
        os.fsync(destination.fileno())


def package_profile_auditions(
    original_plan_path: Path,
    original_runs_root: Path,
    retry_plan_path: Path,
    retry_runs_root: Path,
    output_root: Path,
) -> Path:
    original_plan_file, original_plan, originals = _validate_original_plan(original_plan_path)
    retry_plan_file, _retry_plan, retries, retry_entries = _validate_retry_plan(
        retry_plan_path, original_plan_file, original_plan, originals
    )
    selected, negatives = _validate_runs(
        original_runs_root, retry_runs_root, originals, retries, retry_entries
    )
    copies, manifest = _build_package(
        original_plan_file,
        retry_plan_file,
        selected,
        negatives,
    )
    if original_plan != planner.build_request_plan():
        raise ValueError("trusted source plan changed during package validation")
    target = _validate_output_root(
        output_root,
        (
            Path(original_plan_path),
            Path(original_runs_root),
            Path(retry_plan_path),
            Path(retry_runs_root),
        ),
    )
    # No filesystem output is created until every input, selection, hash, WAV,
    # and manifest record has validated in memory.
    target.mkdir()
    for relative_path, payload in copies:
        destination = _safe_child(target, relative_path, "artifact destination")
        _write_exclusive(destination, payload)
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    manifest_path = target / "package-manifest.json"
    _write_exclusive(manifest_path, manifest_bytes)
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Package the exact nonbinding six-profile Qwen audition evidence set."
    )
    parser.add_argument("--original-plan", required=True, type=Path)
    parser.add_argument("--original-runs-root", required=True, type=Path)
    parser.add_argument("--retry-plan", required=True, type=Path)
    parser.add_argument("--retry-runs-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    arguments = parser.parse_args()
    manifest = package_profile_auditions(
        arguments.original_plan,
        arguments.original_runs_root,
        arguments.retry_plan,
        arguments.retry_runs_root,
        arguments.output_root,
    )
    print(
        json.dumps(
            {
                "status": PACKAGE_STATUS,
                "manifest": manifest.name,
                "selected_passing_attempt_count": 18,
                "negative_attempt_count": 2,
                "audio_generated": False,
                "binding_created": False,
                "route_changed": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
