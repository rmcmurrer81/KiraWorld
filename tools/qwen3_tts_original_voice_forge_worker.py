"""Fail-closed Qwen3-TTS original-voice forge worker.

The module is safe to import without Torch, Qwen3-TTS, a GPU, or model files.
Real inference is reachable only through the explicit CLI authorization gates
and an accepted isolated-environment specification.  Tests inject a fake
runtime; importing or testing this file never imports ``qwen_tts``.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib
import importlib.metadata
import io
import json
import math
import os
import re
import struct
import sys
import threading
import time
import traceback
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_RELATIVE = Path(
    "TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v1.json"
)
CONTRACT_ID = "temporary_ai_qwen3_tts_original_voice_forge_acceptance_v1"
JOB_SCHEMA = "qwen3_tts_original_voice_forge_job_v1"
VOICE_ORIGIN = "ORIGINAL_SYNTHETIC_TEXT_DESIGN_NOT_PERSON_CLONE"
IDENTITY_BASIS = "original_trait_description"
INITIAL_WATERMARK_STATUS = "NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK"
STRONG_WATERMARK_STATUS = (
    "NO_DOCUMENTED_OR_KNOWN_WATERMARK_DETECTED_AT_ACCEPTED_REVISION"
)
FAILURE_STATUS = "FAILED_TEXT_PLUS_SILENCE_ONLY"
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,79}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IMITATION_RE = re.compile(
    r"\b(sound|sounds|voice|talk|speak|speaks|clone|copy|imitate|impersonate)\s+"
    r"(?:exactly\s+|just\s+|identically\s+)?(?:like|as)\b|"
    r"\b(in\s+the\s+voice\s+of|celebrity\s+voice|public\s+figure\s+voice)\b",
    re.IGNORECASE,
)


class ForgeError(RuntimeError):
    """A fail-closed contract, environment, inference, or evidence failure."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ForgeError(f"could not read exact JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ForgeError(f"exact JSON must contain an object: {path}")
    return value


def write_new_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def write_new_json(path: Path, value: Any) -> None:
    write_new_bytes(path, canonical_json_bytes(value))


def require_sha256(label: str, value: Any) -> str:
    normalized = str(value or "").lower()
    if not SHA256_RE.fullmatch(normalized):
        raise ForgeError(f"{label} must be one lowercase SHA-256")
    return normalized


def verify_exact_file(path: Path, expected_hash: str, label: str) -> None:
    if not path.is_file():
        raise ForgeError(f"{label} is not an exact file: {path}")
    actual = sha256_file(path)
    if actual != require_sha256(f"{label} hash", expected_hash):
        raise ForgeError(f"{label} hash mismatch: expected {expected_hash}, got {actual}")


def resolve_inside(root: Path, value: str, label: str, *, require_relative: bool = True) -> Path:
    candidate = Path(value)
    if require_relative and candidate.is_absolute():
        raise ForgeError(f"{label} must be a project-relative local path")
    resolved_root = root.resolve()
    resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ForgeError(f"{label} escaped its allowed root: {value}") from exc
    return resolved


def project_relative(path: Path, project_root: Path) -> str:
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def verify_model_file_manifest(
    *,
    project_root: Path,
    model_dir: Path,
    manifest_path: Path,
    expected_manifest_hash: str,
    expected_repository: str,
) -> dict[str, Any]:
    verify_exact_file(manifest_path, expected_manifest_hash, "model file manifest")
    manifest = read_json(manifest_path)
    if manifest.get("schema") != "qwen3_tts_local_model_file_manifest_v1":
        raise ForgeError("model file manifest schema mismatch")
    if manifest.get("repository") != expected_repository:
        raise ForgeError("model file manifest repository mismatch")
    if manifest.get("complete_file_inventory") is not True:
        raise ForgeError("model file manifest is not a declared complete inventory")
    if not str(manifest.get("revision") or "").strip():
        raise ForgeError("model file manifest has no exact revision")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ForgeError("model file manifest has no file inventory")
    seen: set[str] = set()
    for row in files:
        if not isinstance(row, dict):
            raise ForgeError("model file manifest row is not an object")
        rel = str(row.get("path") or "")
        if not rel or rel in seen:
            raise ForgeError("model file manifest contains a missing or duplicate path")
        seen.add(rel)
        path = resolve_inside(model_dir, rel, "model file", require_relative=True)
        expected_size = row.get("bytes")
        if not path.is_file():
            raise ForgeError(f"model file is missing: {project_relative(path, project_root)}")
        if not isinstance(expected_size, int) or path.stat().st_size != expected_size:
            raise ForgeError(f"model file size mismatch: {rel}")
        verify_exact_file(path, str(row.get("sha256") or ""), f"model file {rel}")
    if manifest_path.resolve().parent != model_dir.resolve():
        raise ForgeError("model file manifest must be stored in its exact model directory")
    actual_files = {
        path.resolve().relative_to(model_dir.resolve()).as_posix()
        for path in model_dir.rglob("*")
        if path.is_file() and path.resolve() != manifest_path.resolve()
    }
    if actual_files != seen:
        missing = sorted(seen - actual_files)
        undeclared = sorted(actual_files - seen)
        raise ForgeError(
            "model directory inventory mismatch; "
            f"missing={missing[:5]} undeclared={undeclared[:5]}"
        )
    return manifest


def resolve_watermark_status(evidence: Any) -> str:
    if not isinstance(evidence, dict):
        return INITIAL_WATERMARK_STATUS
    requested = evidence.get("requested_status", INITIAL_WATERMARK_STATUS)
    if requested == INITIAL_WATERMARK_STATUS:
        return INITIAL_WATERMARK_STATUS
    if requested != STRONG_WATERMARK_STATUS:
        raise ForgeError("unknown or overstated watermark status requested")
    required_true = (
        "exact_revision_source_scan_passed",
        "dependency_scan_passed",
        "wav_inventory_passed",
        "detector_positive_controls_passed",
        "repeated_generated_samples_no_known_mark_detected",
        "owner_hearing_acceptance_passed",
    )
    if not all(evidence.get(key) is True for key in required_true):
        raise ForgeError("stronger watermark status lacks every explicit evidence gate")
    detectors = evidence.get("detectors")
    if not isinstance(detectors, list) or not detectors:
        raise ForgeError("stronger watermark status has no named detector evidence")
    for detector in detectors:
        if not isinstance(detector, dict):
            raise ForgeError("watermark detector evidence row is invalid")
        if not all(str(detector.get(k) or "").strip() for k in ("name", "version", "evidence_sha256")):
            raise ForgeError("watermark detector evidence is incomplete")
        require_sha256("watermark detector evidence hash", detector["evidence_sha256"])
    return STRONG_WATERMARK_STATUS


def validate_job_identity(job: dict[str, Any]) -> None:
    if job.get("schema") != JOB_SCHEMA:
        raise ForgeError("job schema mismatch")
    candidate_id = str(job.get("candidate_id") or "")
    voice_id = str(job.get("opaque_voice_id") or "")
    if not SAFE_ID.fullmatch(candidate_id):
        raise ForgeError("candidate_id is not a safe opaque identifier")
    if not SAFE_ID.fullmatch(voice_id):
        raise ForgeError("opaque_voice_id is not a safe opaque identifier")
    if job.get("voice_origin") != VOICE_ORIGIN:
        raise ForgeError("job is not an original synthetic text-designed voice")
    if job.get("identity_basis") != IDENTITY_BASIS:
        raise ForgeError("job identity basis is not original trait description")
    if job.get("named_real_person_imitation_requested") is not False:
        raise ForgeError("named-real-person imitation is forbidden in this harness")
    if job.get("named_real_person_names") != []:
        raise ForgeError("named-real-person names must be empty")
    traits = str(job.get("design_traits_text") or "").strip()
    if len(traits) < 20:
        raise ForgeError("design traits are missing or too short")
    if IMITATION_RE.search(traits):
        raise ForgeError("design traits appear to request imitation of another person's voice")
    for field in ("design_traits", "reference", "test"):
        text_key = f"{field}_text"
        hash_key = f"{field}_text_sha256"
        text = str(job.get(text_key) or "")
        if not text.strip():
            raise ForgeError(f"{text_key} is empty")
        expected = require_sha256(hash_key, job.get(hash_key))
        actual = sha256_text(text)
        if expected != actual:
            raise ForgeError(f"{text_key} hash mismatch: expected {expected}, got {actual}")
    if not str(job.get("language") or "").strip():
        raise ForgeError("language is empty")
    resolve_watermark_status(job.get("watermark_evidence"))


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("contract_id") != CONTRACT_ID or contract.get("version") != 1:
        raise ForgeError("acceptance contract identity mismatch")
    execution = contract.get("execution") or {}
    required_false = (
        "network_allowed",
        "playback_allowed",
        "activation_assignment_publication_or_upload_allowed",
        "torch_compile_allowed",
        "flash_attention_or_triton_required",
    )
    if not execution.get("default_is_inert") or any(execution.get(k) is not False for k in required_false):
        raise ForgeError("acceptance contract weakened its inert/offline execution boundary")
    if execution.get("attention_implementation") != "sdpa":
        raise ForgeError("only ordinary eager/SDPA is accepted")
    failure = contract.get("failure_behavior") or {}
    if failure.get("status") != FAILURE_STATUS:
        raise ForgeError("failure behavior does not preserve text plus silence")
    for key in (
        "generic_voice_fallback_allowed",
        "sapi_fallback_allowed",
        "other_person_voice_fallback_allowed",
        "current_voice_routing_change_allowed",
    ):
        if failure.get(key) is not False:
            raise ForgeError(f"forbidden fallback or routing mutation enabled: {key}")
    watermark = contract.get("watermark") or {}
    if watermark.get("removal_disabling_evasion_or_circumvention_allowed") is not False:
        raise ForgeError("watermark removal or circumvention was enabled")


def validate_environment_spec(spec: dict[str, Any], *, require_ready: bool) -> None:
    pins = spec.get("pinned_core_packages") or {}
    expected = {
        "qwen-tts": "0.1.1",
        "transformers": "4.57.3",
        "accelerate": "1.12.0",
    }
    if pins != expected:
        raise ForgeError("isolated environment core package pins changed")
    runtime = spec.get("runtime") or {}
    if runtime.get("attention_implementation") != "sdpa":
        raise ForgeError("environment does not specify SDPA")
    if runtime.get("ordinary_eager_cuda") is not True:
        raise ForgeError("environment does not specify eager CUDA")
    if runtime.get("torch_compile") is not False:
        raise ForgeError("torch.compile is forbidden in this acceptance")
    torch_spec = spec.get("torch_installation") or {}
    if require_ready:
        if spec.get("status") != "ACCEPTED_READY_FOR_BOUNDED_OFFLINE_RUN":
            raise ForgeError("isolated environment is not accepted ready")
        if torch_spec.get("status") != "PINNED_OFFICIAL_BLACKWELL_WINDOWS_WHEELS_ACCEPTED":
            raise ForgeError("official Blackwell Torch/Torchaudio pair is still pending")
        if not str(torch_spec.get("torch") or "") or not str(torch_spec.get("torchaudio") or ""):
            raise ForgeError("Torch/Torchaudio versions are not pinned")


def verify_installed_core_versions(spec: dict[str, Any]) -> None:
    for package, expected in (spec.get("pinned_core_packages") or {}).items():
        try:
            actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError as exc:
            raise ForgeError(f"required isolated package is not installed: {package}") from exc
        if actual != expected:
            raise ForgeError(f"isolated package version mismatch for {package}: {actual} != {expected}")


def _process_rss_bytes() -> int:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(counters),
            counters.cb,
        )
        if not ok:
            raise ForgeError("GetProcessMemoryInfo failed")
        return int(counters.WorkingSetSize)
    try:
        import resource

        maximum = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return maximum if sys.platform == "darwin" else maximum * 1024
    except (ImportError, OSError) as exc:
        raise ForgeError("process RSS telemetry is unavailable") from exc


class ForgeRuntime(Protocol):
    def environment_evidence(self) -> dict[str, Any]: ...
    def rss_bytes(self) -> int: ...
    def cuda_allocated_bytes(self) -> int: ...
    def cuda_reserved_bytes(self) -> int: ...
    def load(self, role: str, model_path: Path) -> None: ...
    def generate_voice_design(self, *, text: str, language: str, instruct: str) -> tuple[Any, int]: ...
    def create_voice_clone_prompt(self, *, ref_audio: tuple[Any, int], ref_text: str) -> Any: ...
    def generate_voice_clone(self, *, text: str, language: str, prompt: Any) -> tuple[Any, int]: ...
    def serialize_prompt(self, prompt: Any) -> bytes: ...
    def unload(self) -> None: ...


class OfficialQwenRuntime:
    """Lazy real adapter using only the API documented by QwenLM/Qwen3-TTS."""

    def __init__(self) -> None:
        self.torch = importlib.import_module("torch")
        qwen_tts = importlib.import_module("qwen_tts")
        self.Qwen3TTSModel = getattr(qwen_tts, "Qwen3TTSModel")
        self.model: Any = None
        if not self.torch.cuda.is_available():
            raise ForgeError("CUDA is unavailable")

    def environment_evidence(self) -> dict[str, Any]:
        capability = self.torch.cuda.get_device_capability(0)
        return {
            "device": "cuda:0",
            "device_name": self.torch.cuda.get_device_name(0),
            "compute_capability": [int(capability[0]), int(capability[1])],
            "torch_version": str(self.torch.__version__),
            "torchaudio_version": importlib.metadata.version("torchaudio"),
            "qwen_tts_version": importlib.metadata.version("qwen-tts"),
            "transformers_version": importlib.metadata.version("transformers"),
            "accelerate_version": importlib.metadata.version("accelerate"),
            "attention_implementation": "sdpa",
            "ordinary_eager_cuda": True,
            "torch_compile_invoked": False,
        }

    def rss_bytes(self) -> int:
        return _process_rss_bytes()

    def cuda_allocated_bytes(self) -> int:
        return int(self.torch.cuda.memory_allocated(0))

    def cuda_reserved_bytes(self) -> int:
        return int(self.torch.cuda.memory_reserved(0))

    def load(self, role: str, model_path: Path) -> None:
        if self.model is not None:
            raise ForgeError("attempted to keep two Qwen3-TTS models resident")
        if role not in {"voice_design", "runtime_clone"}:
            raise ForgeError(f"unknown model role: {role}")
        # Exact official API, but with ordinary eager/SDPA instead of optional
        # FlashAttention. A local directory and local_files_only prevent a
        # model-id typo from becoming an implicit download.
        self.model = self.Qwen3TTSModel.from_pretrained(
            str(model_path),
            device_map="cuda:0",
            dtype=self.torch.bfloat16,
            attn_implementation="sdpa",
            local_files_only=True,
        )
        self.torch.cuda.synchronize(0)

    def generate_voice_design(self, *, text: str, language: str, instruct: str) -> tuple[Any, int]:
        if self.model is None:
            raise ForgeError("VoiceDesign model is not loaded")
        wavs, sample_rate = self.model.generate_voice_design(
            text=text,
            language=language,
            instruct=instruct,
        )
        self.torch.cuda.synchronize(0)
        return wavs[0], int(sample_rate)

    def create_voice_clone_prompt(self, *, ref_audio: tuple[Any, int], ref_text: str) -> Any:
        if self.model is None:
            raise ForgeError("Base model is not loaded")
        prompt = self.model.create_voice_clone_prompt(
            ref_audio=ref_audio,
            ref_text=ref_text,
            x_vector_only_mode=False,
        )
        self.torch.cuda.synchronize(0)
        return prompt

    def generate_voice_clone(self, *, text: str, language: str, prompt: Any) -> tuple[Any, int]:
        if self.model is None:
            raise ForgeError("Base model is not loaded")
        wavs, sample_rate = self.model.generate_voice_clone(
            text=text,
            language=language,
            voice_clone_prompt=prompt,
        )
        self.torch.cuda.synchronize(0)
        return wavs[0], int(sample_rate)

    def serialize_prompt(self, prompt: Any) -> bytes:
        buffer = io.BytesIO()
        self.torch.save(prompt, buffer)
        return buffer.getvalue()

    def unload(self) -> None:
        self.model = None
        gc.collect()
        self.torch.cuda.empty_cache()
        self.torch.cuda.synchronize(0)


@dataclass
class TelemetrySampler:
    runtime: ForgeRuntime
    interval_seconds: float = 0.02
    peak_rss_bytes: int = 0
    peak_cuda_allocated_bytes: int = 0
    peak_cuda_reserved_bytes: int = 0
    samples: int = 0
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None
    _error: BaseException | None = None

    def sample_once(self) -> None:
        self.peak_rss_bytes = max(self.peak_rss_bytes, int(self.runtime.rss_bytes()))
        self.peak_cuda_allocated_bytes = max(
            self.peak_cuda_allocated_bytes, int(self.runtime.cuda_allocated_bytes())
        )
        self.peak_cuda_reserved_bytes = max(
            self.peak_cuda_reserved_bytes, int(self.runtime.cuda_reserved_bytes())
        )
        self.samples += 1

    def _run(self) -> None:
        try:
            while not self._stop.wait(self.interval_seconds):
                self.sample_once()
        except BaseException as exc:  # preserved and raised on the worker thread join
            self._error = exc

    def start(self) -> None:
        self.sample_once()
        self._thread = threading.Thread(target=self._run, name="forge-telemetry", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self.sample_once()
        if self._error is not None:
            raise ForgeError(f"telemetry sampler failed: {self._error}") from self._error


def _flatten_samples(samples: Any) -> list[float]:
    if hasattr(samples, "detach"):
        samples = samples.detach()
    if hasattr(samples, "cpu"):
        samples = samples.cpu()
    if hasattr(samples, "tolist"):
        samples = samples.tolist()
    if not isinstance(samples, (list, tuple)):
        samples = list(samples)
    while samples and isinstance(samples[0], (list, tuple)):
        if len(samples) != 1:
            raise ForgeError("only one mono waveform is accepted per output")
        samples = samples[0]
    values = [float(value) for value in samples]
    if not values or any(not math.isfinite(value) for value in values):
        raise ForgeError("generated waveform is empty or non-finite")
    return values


def write_pcm16_wav_new(path: Path, samples: Any, sample_rate: int) -> None:
    if not isinstance(sample_rate, int) or not 8000 <= sample_rate <= 192000:
        raise ForgeError(f"invalid output sample rate: {sample_rate}")
    values = _flatten_samples(samples)
    if max(abs(value) for value in values) <= 1.5:
        integers = [max(-32768, min(32767, int(round(value * 32767.0)))) for value in values]
    else:
        integers = [max(-32768, min(32767, int(round(value)))) for value in values]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as raw:
        with wave.open(raw, "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(sample_rate)
            writer.writeframes(struct.pack(f"<{len(integers)}h", *integers))
        raw.flush()
        os.fsync(raw.fileno())


def validate_readable_non_silent_wav(path: Path) -> dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as reader:
            channels = reader.getnchannels()
            width = reader.getsampwidth()
            rate = reader.getframerate()
            frames = reader.getnframes()
            payload = reader.readframes(frames)
    except (OSError, EOFError, wave.Error) as exc:
        raise ForgeError(f"WAV is unreadable: {path}: {exc}") from exc
    if channels != 1 or width != 2 or rate < 8000 or frames < max(1, rate // 10):
        raise ForgeError("WAV is not a sufficiently long mono PCM16 recording")
    values = struct.unpack(f"<{len(payload) // 2}h", payload)
    peak = max(abs(value) for value in values) if values else 0
    rms = math.sqrt(sum(value * value for value in values) / len(values)) if values else 0.0
    if peak <= 16 or rms <= 8.0:
        raise ForgeError("WAV is silent or effectively silent")
    return {
        "path": path.name,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "channels": channels,
        "sample_width_bytes": width,
        "sample_rate": rate,
        "frames": frames,
        "duration_seconds": frames / rate,
        "peak_pcm16": peak,
        "rms_pcm16": rms,
        "readable": True,
        "non_silent": True,
    }


def execute_job(
    *,
    project_root: Path,
    contract_path: Path,
    contract_sha256: str,
    environment_spec_path: Path,
    environment_spec_sha256: str,
    job_path: Path,
    job_sha256: str,
    output_dir: Path,
    runtime_factory: Callable[[], ForgeRuntime] | None = None,
    require_ready_environment: bool = True,
    verify_installed_versions: bool = True,
) -> dict[str, Any]:
    """Execute one exact append-only job after all non-runtime gates pass."""

    started_wall = time.perf_counter()
    project_root = project_root.resolve()
    expected_contract_path = (project_root / DEFAULT_CONTRACT_RELATIVE).resolve()
    if contract_path.resolve() != expected_contract_path:
        raise ForgeError("acceptance contract is not the exact project contract path")
    try:
        environment_spec_path.resolve().relative_to(project_root)
        job_path.resolve().relative_to(project_root)
    except ValueError as exc:
        raise ForgeError("environment spec and job must be project-confined exact files") from exc
    verify_exact_file(contract_path, contract_sha256, "acceptance contract")
    verify_exact_file(environment_spec_path, environment_spec_sha256, "environment spec")
    verify_exact_file(job_path, job_sha256, "forge job")
    contract = read_json(contract_path)
    spec = read_json(environment_spec_path)
    job = read_json(job_path)
    validate_contract(contract)
    validate_environment_spec(spec, require_ready=require_ready_environment)
    validate_job_identity(job)
    expected_environment_path = resolve_inside(
        project_root, contract["paths"]["environment_spec"], "contract environment spec"
    )
    if environment_spec_path.resolve() != expected_environment_path:
        raise ForgeError("environment spec is not the exact contract-bound project file")
    if verify_installed_versions:
        verify_installed_core_versions(spec)

    paths = contract["paths"]
    model_root = resolve_inside(project_root, paths["local_model_root"], "local model root")
    design_model = resolve_inside(project_root, str(job["voice_design_model_directory"]), "VoiceDesign model")
    base_model = resolve_inside(project_root, str(job["base_model_directory"]), "Base model")
    for label, actual, expected in (
        ("VoiceDesign", design_model, paths["voice_design_model_directory"]),
        ("Base", base_model, paths["base_model_directory"]),
    ):
        expected_path = resolve_inside(project_root, expected, f"expected {label} model")
        try:
            actual.relative_to(model_root)
        except ValueError as exc:
            raise ForgeError(f"{label} model escaped the local model root") from exc
        if actual != expected_path or not actual.is_dir():
            raise ForgeError(f"{label} must use the exact existing local model directory")

    design_manifest_path = resolve_inside(
        project_root, str(job["voice_design_model_manifest"]), "VoiceDesign manifest"
    )
    base_manifest_path = resolve_inside(
        project_root, str(job["base_model_manifest"]), "Base manifest"
    )
    design_manifest = verify_model_file_manifest(
        project_root=project_root,
        model_dir=design_model,
        manifest_path=design_manifest_path,
        expected_manifest_hash=str(job["voice_design_model_manifest_sha256"]),
        expected_repository="Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    )
    base_manifest = verify_model_file_manifest(
        project_root=project_root,
        model_dir=base_model,
        manifest_path=base_manifest_path,
        expected_manifest_hash=str(job["base_model_manifest_sha256"]),
        expected_repository="Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    )

    allowed_output = resolve_inside(project_root, paths["private_output_root"], "private output root")
    output_dir = output_dir.resolve()
    try:
        output_dir.relative_to(allowed_output)
    except ValueError as exc:
        raise ForgeError("output escaped the private voice-forge root") from exc
    expected_candidate_root = (allowed_output / str(job["candidate_id"])).resolve()
    if output_dir.parent != expected_candidate_root or not re.fullmatch(r"attempt_[0-9]{2,3}", output_dir.name):
        raise ForgeError("output must be one exact candidate-bound append-only attempt_NN directory")
    if output_dir.exists():
        raise ForgeError(f"append-only output already exists: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)

    runtime: ForgeRuntime | None = None
    sampler: TelemetrySampler | None = None
    events: list[dict[str, Any]] = []
    timings: dict[str, float] = {}
    reference_path = output_dir / "original_design_reference.wav"
    prompt_path = output_dir / "runtime_clone_prompt.pt"
    test_path = output_dir / "runtime_clone_test.wav"
    try:
        runtime = (runtime_factory or OfficialQwenRuntime)()
        environment = runtime.environment_evidence()
        if environment.get("device") != "cuda:0" or environment.get("ordinary_eager_cuda") is not True:
            raise ForgeError("runtime did not prove ordinary eager CUDA on cuda:0")
        if environment.get("attention_implementation") != "sdpa":
            raise ForgeError("runtime did not prove SDPA")
        if environment.get("torch_compile_invoked") is not False:
            raise ForgeError("runtime invoked or claimed torch.compile")
        baseline_allocated = int(runtime.cuda_allocated_bytes())
        baseline_reserved = int(runtime.cuda_reserved_bytes())
        baseline_rss = int(runtime.rss_bytes())
        sampler = TelemetrySampler(runtime)
        sampler.start()

        started = time.perf_counter()
        runtime.load("voice_design", design_model)
        sampler.sample_once()
        timings["voice_design_model_load_seconds"] = time.perf_counter() - started
        events.append({"event": "VOICE_DESIGN_MODEL_LOADED", "utc": utc_now()})

        started = time.perf_counter()
        reference_samples, reference_rate = runtime.generate_voice_design(
            text=str(job["reference_text"]),
            language=str(job["language"]),
            instruct=str(job["design_traits_text"]),
        )
        sampler.sample_once()
        voice_design_generation_allocated = int(runtime.cuda_allocated_bytes())
        timings["voice_design_generation_seconds"] = time.perf_counter() - started
        write_pcm16_wav_new(reference_path, reference_samples, reference_rate)
        reference_wav = validate_readable_non_silent_wav(reference_path)
        events.append({"event": "ORIGINAL_DESIGN_REFERENCE_WRITTEN", "utc": utc_now()})

        started = time.perf_counter()
        runtime.unload()
        timings["voice_design_unload_seconds"] = time.perf_counter() - started
        after_design_allocated = int(runtime.cuda_allocated_bytes())
        after_design_reserved = int(runtime.cuda_reserved_bytes())
        events.append({"event": "VOICE_DESIGN_UNLOADED", "utc": utc_now()})
        return_limit = int(contract["acceptance_gates"]["final_vram_return_within_bytes"])
        if (
            after_design_allocated > baseline_allocated + return_limit
            or after_design_reserved > baseline_reserved + return_limit
        ):
            raise ForgeError("VoiceDesign VRAM did not return before Base load")

        started = time.perf_counter()
        runtime.load("runtime_clone", base_model)
        sampler.sample_once()
        timings["base_model_load_seconds"] = time.perf_counter() - started
        events.append({"event": "BASE_MODEL_LOADED_AFTER_DESIGN_UNLOAD", "utc": utc_now()})

        started = time.perf_counter()
        clone_prompt = runtime.create_voice_clone_prompt(
            ref_audio=(reference_samples, reference_rate),
            ref_text=str(job["reference_text"]),
        )
        timings["clone_prompt_creation_seconds"] = time.perf_counter() - started
        write_new_bytes(prompt_path, runtime.serialize_prompt(clone_prompt))
        events.append({"event": "EXACT_CLONE_PROMPT_WRITTEN", "utc": utc_now()})

        started = time.perf_counter()
        test_samples, test_rate = runtime.generate_voice_clone(
            text=str(job["test_text"]),
            language=str(job["language"]),
            prompt=clone_prompt,
        )
        sampler.sample_once()
        clone_generation_allocated = int(runtime.cuda_allocated_bytes())
        timings["clone_test_generation_seconds"] = time.perf_counter() - started
        write_pcm16_wav_new(test_path, test_samples, test_rate)
        test_wav = validate_readable_non_silent_wav(test_path)
        events.append({"event": "RUNTIME_CLONE_TEST_WRITTEN", "utc": utc_now()})

        started = time.perf_counter()
        runtime.unload()
        timings["base_model_unload_seconds"] = time.perf_counter() - started
        final_allocated = int(runtime.cuda_allocated_bytes())
        final_reserved = int(runtime.cuda_reserved_bytes())
        events.append({"event": "BASE_MODEL_UNLOADED", "utc": utc_now()})
        sampler.stop()
        telemetry = {
            "baseline_process_rss_bytes": baseline_rss,
            "peak_process_rss_bytes": sampler.peak_rss_bytes,
            "baseline_cuda_allocated_bytes": baseline_allocated,
            "baseline_cuda_reserved_bytes": baseline_reserved,
            "peak_cuda_allocated_bytes": sampler.peak_cuda_allocated_bytes,
            "peak_cuda_reserved_bytes": sampler.peak_cuda_reserved_bytes,
            "after_voice_design_unload_cuda_allocated_bytes": after_design_allocated,
            "after_voice_design_unload_cuda_reserved_bytes": after_design_reserved,
            "voice_design_generation_cuda_allocated_bytes": voice_design_generation_allocated,
            "clone_generation_cuda_allocated_bytes": clone_generation_allocated,
            "final_cuda_allocated_bytes": final_allocated,
            "final_cuda_reserved_bytes": final_reserved,
            "samples": sampler.samples,
        }
        sampler = None
        if final_allocated > baseline_allocated + return_limit or final_reserved > baseline_reserved + return_limit:
            raise ForgeError("final VRAM allocation/reservation did not return within the contract bound")
        if telemetry["peak_cuda_allocated_bytes"] <= baseline_allocated:
            raise ForgeError("no actual CUDA allocation above baseline was measured")
        if (
            voice_design_generation_allocated <= baseline_allocated
            or clone_generation_allocated <= baseline_allocated
        ):
            raise ForgeError("actual CUDA allocation was not present during both synthesis stages")
        if telemetry["peak_process_rss_bytes"] <= 0 or telemetry["samples"] < 2:
            raise ForgeError("peak process RAM telemetry was not measured")

        watermark_status = resolve_watermark_status(job.get("watermark_evidence"))
        prompt_sha256 = sha256_file(prompt_path)
        profile = {
            "schema": "temporary_ai_qwen3_tts_original_voice_profile_candidate_v1",
            "status": "PRIVATE_UNREVIEWED_ENGINEERING_ACCEPTANCE_OWNER_HEARING_PENDING",
            "candidate_id": job["candidate_id"],
            "opaque_voice_id": job["opaque_voice_id"],
            "voice_origin": VOICE_ORIGIN,
            "identity_basis": IDENTITY_BASIS,
            "engine": "qwen3_tts_voice_design_then_clone",
            "offline_runtime": True,
            "assignment_allowed": False,
            "activation_allowed": False,
            "publication_or_upload_allowed": False,
            "generic_sapi_or_other_person_fallback_allowed": False,
            "failure_behavior": FAILURE_STATUS,
            "language": job["language"],
            "input_hashes": {
                "design_traits_sha256": job["design_traits_text_sha256"],
                "reference_text_sha256": job["reference_text_sha256"],
                "test_text_sha256": job["test_text_sha256"],
                "job_sha256": job_sha256,
                "contract_sha256": contract_sha256,
                "environment_spec_sha256": environment_spec_sha256,
            },
            "models": {
                "voice_design": {
                    "repository": design_manifest["repository"],
                    "revision": design_manifest["revision"],
                    "manifest_sha256": job["voice_design_model_manifest_sha256"],
                },
                "runtime_clone": {
                    "repository": base_manifest["repository"],
                    "revision": base_manifest["revision"],
                    "manifest_sha256": job["base_model_manifest_sha256"],
                },
            },
            "artifacts": {
                "original_design_reference": reference_wav,
                "runtime_clone_prompt": {
                    "path": prompt_path.name,
                    "sha256": prompt_sha256,
                    "bytes": prompt_path.stat().st_size,
                    "trusted_local_hash_verification_required_before_load": True,
                },
                "runtime_clone_test": test_wav,
            },
            "watermark_status": watermark_status,
            "watermark_removal_disabling_evasion_or_circumvention_used": False,
            "owner_hearing_acceptance": "PENDING",
        }
        profile_path = output_dir / "voice_profile_candidate.json"
        write_new_json(profile_path, profile)
        profile_sha256 = sha256_file(profile_path)
        timings["worker_total_through_profile_seconds"] = time.perf_counter() - started_wall
        manifest = {
            "schema": "qwen3_tts_original_voice_forge_worker_manifest_v1",
            "status": "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING",
            "created_utc": utc_now(),
            "candidate_id": job["candidate_id"],
            "opaque_voice_id": job["opaque_voice_id"],
            "private_append_only": True,
            "inactive_unassigned_unpublished": True,
            "official_api_sequence": contract["official_api_sequence"],
            "execution": {
                "network_used": False,
                "playback_used": False,
                "local_model_paths_only": True,
                "ordinary_eager_cuda": True,
                "attention_implementation": "sdpa",
                "torch_compile_invoked": False,
                "flash_attention_or_triton_required": False,
                "one_heavy_model_at_a_time": True,
                "voice_design_unloaded_before_base_load": True,
                "clean_worker_exit": "PARENT_MUST_CONFIRM_AFTER_PROCESS_EXIT",
            },
            "environment": environment,
            "input_hashes": profile["input_hashes"],
            "model_manifests": profile["models"],
            "artifacts": {
                **profile["artifacts"],
                "voice_profile_candidate": {
                    "path": profile_path.name,
                    "sha256": profile_sha256,
                    "bytes": profile_path.stat().st_size,
                },
            },
            "telemetry": telemetry,
            "timings_seconds": timings,
            "events": events,
            "watermark": {
                "status": watermark_status,
                "explicit_evidence": job.get("watermark_evidence"),
                "removal_disabling_evasion_or_circumvention_used": False,
                "absence_of_every_unknown_signal_claimed": False,
            },
            "failure_policy": {
                "on_any_future_mismatch": FAILURE_STATUS,
                "text_remains_available": True,
                "generic_voice_fallback_allowed": False,
                "sapi_fallback_allowed": False,
                "other_person_voice_fallback_allowed": False,
            },
        }
        manifest_path = output_dir / "worker_manifest.json"
        write_new_json(manifest_path, manifest)
        return {
            "status": manifest["status"],
            "output_dir": str(output_dir),
            "profile_path": str(profile_path),
            "profile_sha256": profile_sha256,
            "manifest_path": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "reference_wav_sha256": reference_wav["sha256"],
            "test_wav_sha256": test_wav["sha256"],
        }
    except BaseException as exc:
        if sampler is not None:
            try:
                sampler.stop()
            except BaseException:
                pass
        if runtime is not None:
            try:
                runtime.unload()
            except BaseException:
                pass
        failure = {
            "schema": "qwen3_tts_original_voice_forge_failure_v1",
            "status": FAILURE_STATUS,
            "candidate_id": job.get("candidate_id"),
            "opaque_voice_id": job.get("opaque_voice_id"),
            "utc": utc_now(),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "events": events,
            "fallback": {
                "text_remains_available": True,
                "voice_audio_result": "SILENCE_NO_AUDIO",
                "generic_voice_used": False,
                "sapi_used": False,
                "other_person_voice_used": False,
                "current_voice_route_changed": False,
            },
            "partial_artifacts_unapproved": [
                path.name for path in (reference_path, prompt_path, test_path) if path.exists()
            ],
        }
        try:
            write_new_json(output_dir / "failure.json", failure)
        except FileExistsError:
            pass
        raise ForgeError(str(exc)) from exc

    raise ForgeError("unreachable worker state")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--contract")
    parser.add_argument("--contract-sha256")
    parser.add_argument("--environment-spec")
    parser.add_argument("--environment-spec-sha256")
    parser.add_argument("--job")
    parser.add_argument("--job-sha256")
    parser.add_argument("--worker-sha256")
    parser.add_argument("--output-dir")
    parser.add_argument("--acknowledge-private-unreviewed", action="store_true")
    parser.add_argument("--acknowledge-no-download", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.execute:
        raise ForgeError("worker is inert without --execute")
    if not args.acknowledge_private_unreviewed or not args.acknowledge_no_download:
        raise ForgeError("both bounded execution acknowledgements are required")
    required = {
        "contract": args.contract,
        "contract_sha256": args.contract_sha256,
        "environment_spec": args.environment_spec,
        "environment_spec_sha256": args.environment_spec_sha256,
        "job": args.job,
        "job_sha256": args.job_sha256,
        "worker_sha256": args.worker_sha256,
        "output_dir": args.output_dir,
    }
    missing = sorted(key for key, value in required.items() if not value)
    if missing:
        raise ForgeError("missing explicit worker arguments: " + ", ".join(missing))
    verify_exact_file(Path(__file__).resolve(), args.worker_sha256, "worker")
    contract_for_python = read_json(Path(args.contract).resolve())
    expected_python = resolve_inside(
        PROJECT_ROOT, contract_for_python["paths"]["isolated_python"], "isolated Python"
    )
    if Path(sys.executable).resolve() != expected_python:
        raise ForgeError("worker is not running from the exact isolated Qwen3-TTS environment")
    execute_job(
        project_root=PROJECT_ROOT,
        contract_path=Path(args.contract).resolve(),
        contract_sha256=args.contract_sha256,
        environment_spec_path=Path(args.environment_spec).resolve(),
        environment_spec_sha256=args.environment_spec_sha256,
        job_path=Path(args.job).resolve(),
        job_sha256=args.job_sha256,
        output_dir=Path(args.output_dir).resolve(),
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ForgeError as exc:
        print(f"Qwen3-TTS original voice forge failed closed: {exc}", file=sys.stderr)
        raise SystemExit(2)
