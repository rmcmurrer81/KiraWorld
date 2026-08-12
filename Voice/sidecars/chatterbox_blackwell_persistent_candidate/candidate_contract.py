"""Standard-library contract for the inactive persistent Blackwell voice candidate.

Importing this module never imports Torch, Chatterbox, audio libraries, or an
audio device.  The same validation code is used by the parent client, worker,
and no-model tests.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import tempfile
import time
import uuid
import wave
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator
from urllib import request as urllib_request


ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(__file__).with_name("candidate_config.json")
HEX_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PRIVATE_MARKERS = (
    "private mind:",
    "factual truth:",
    "hidden reasoning:",
    "internal monologue:",
    "private thought:",
)
REJECTED_RUNTIME_TEXT = (
    "unsupported gpu architecture",
    "unsupported architecture",
    "no kernel image",
    "sm_120 is not compatible",
    "not compatible with the current pytorch installation",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def project_file(relative: Any) -> Path:
    value = Path(str(relative or "").replace("\\", "/"))
    if not value.parts or value.is_absolute() or ".." in value.parts:
        raise ValueError("candidate path must be project-relative")
    resolved = (ROOT / value).resolve()
    resolved.relative_to(ROOT.resolve())
    return resolved


def load_candidate_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("persistent candidate config must be a JSON object")
    return payload


def _require_sha256(value: Any, label: str) -> str:
    normalized = str(value or "").strip().casefold()
    if not HEX_SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{label} is not a SHA-256 digest")
    return normalized


def verify_candidate_config(config: dict[str, Any]) -> dict[str, str]:
    """Verify the inactive candidate and every source/identity binding."""

    expected = {
        "schema_version": 1,
        "candidate_status": "inactive_private_candidate_not_production",
        "production_routing_authorized": False,
        "compute_device": "cuda",
        "input_channel": "public_spoken_only",
        "playback": False,
        "generic_voice_fallback_allowed": False,
        "sapi_fallback_allowed": False,
        "unsealed_fallback_allowed": False,
        "automatic_fallback_inside_candidate": None,
        "offline_cache_only": True,
        "qwen_absence_required_before_model_load": True,
        "qwen_absence_required_before_every_generation_attempt": True,
        "explicit_unload_required": True,
    }
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"persistent candidate policy mismatch: {key}")

    exact_values = {
        "candidate_id": "kira_chatterbox_blackwell_persistent_eager_cuda_candidate_v1",
        "python": "Voice/sidecars/chatterbox_blackwell_gpu/.venv/Scripts/python.exe",
        "worker": "Voice/sidecars/chatterbox_blackwell_persistent_candidate/persistent_worker.py",
        "client": "Voice/sidecars/chatterbox_blackwell_persistent_candidate/candidate_client.py",
        "contract": "Voice/sidecars/chatterbox_blackwell_persistent_candidate/candidate_contract.py",
        "approved_profile": "Voice/profiles/temp_ai/kira_voice_profile.json",
        "approved_profile_sha256": "102d17f5420a1a16b3a920204ebde0d532c0a9bfd2979dca28048378ecddc116",
        "approved_reference": (
            "Voice/reference_packs/kira/kira_online_source_20260706_221447/"
            "model_input/approved_reference.wav"
        ),
        "approved_reference_sha256": (
            "2039a2abd600a63c294d69c2b2e4d450c64c850dc6d1c9a4fbfa1700ba92069c"
        ),
        "qwen_model": "qwen3.5:9b",
        "qwen_digest": "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
        "qwen_ps_endpoint": "http://127.0.0.1:11434/api/ps",
        "runtime_cache_root": (
            "RecoverySprint/runtime_cache/blackwell_chatterbox_persistent_candidate"
        ),
    }
    for key, value in exact_values.items():
        if config.get(key) != value:
            raise ValueError(f"persistent candidate exact binding mismatch: {key}")
    if config.get("allowed_output_roots") != [
        "RecoverySprint/continuation_20260802/persistent_blackwell_voice_candidate_acceptance"
    ]:
        raise ValueError("persistent candidate output-root binding mismatch")
    expected_host_return_contract = {
        "package": "chatterbox-tts",
        "package_version": "0.1.7",
        "installed_source_path": (
            "Voice/sidecars/chatterbox_blackwell_gpu/.venv/Lib/site-packages/"
            "chatterbox/tts.py"
        ),
        "installed_source_sha256": (
            "7896787bc17e20eafcd1dce7b8a4a6ea3a6478baab771c60d63e9e81f5564195"
        ),
        "public_generate_return_device": "cpu",
        "host_return_expected": True,
        "host_return_is_not_cuda_execution_proof": True,
        "accepted_output_tensors_cuda": False,
    }
    if config.get("official_chatterbox_host_return_contract") != expected_host_return_contract:
        raise ValueError("persistent candidate official Chatterbox host-return contract changed")
    expected_diagnostics = {
        "enabled_for_bounded_acceptance_only": True,
        "phase_progress_event_schema_version": 1,
        "phase_start_and_finish_events_required": True,
        "phase_event_journal_filename": "WORKER_PHASE_EVENTS.jsonl",
        "stderr_faulthandler_filename": "WORKER_STDERR_FAULTHANDLER.log",
        "faulthandler_dump_interval_seconds": 120,
        "faulthandler_repeat": True,
        "diagnostic_files_append_only": True,
    }
    if config.get("diagnostics") != expected_diagnostics:
        raise ValueError("persistent candidate diagnostic contract changed")

    if config.get("python_version") != "3.11.9":
        raise ValueError("persistent candidate requires exact Python 3.11.9")
    if config.get("chatterbox_version") != "0.1.7":
        raise ValueError("persistent candidate Chatterbox version mismatch")
    if config.get("torch_version") != "2.11.0+cu130":
        raise ValueError("persistent candidate Torch version mismatch")
    if config.get("torchaudio_version") != "2.11.0+cu130":
        raise ValueError("persistent candidate Torchaudio version mismatch")
    if config.get("required_device_name") != "NVIDIA GeForce RTX 5060 Ti":
        raise ValueError("persistent candidate device pin mismatch")
    if config.get("required_device_capability") != [12, 0]:
        raise ValueError("persistent candidate capability pin mismatch")
    if config.get("required_compiled_architecture") != "sm_120":
        raise ValueError("persistent candidate architecture pin mismatch")

    bounds = config.get("bounds") if isinstance(config.get("bounds"), dict) else {}
    expected_bounds = {
        "max_line_bytes": 65536,
        "max_response_bytes": 1048576,
        "max_text_characters": 4000,
        "max_chunk_characters": 180,
        "max_chunks_per_request": 32,
        "max_generation_attempts_per_chunk": 3,
        "max_requests_per_process": 64,
        "idle_unload_seconds": 600,
        "hard_process_lifetime_seconds": 3600,
    }
    for key, value in expected_bounds.items():
        if bounds.get(key) != value:
            raise ValueError(f"persistent candidate bound mismatch: {key}")

    hashes: dict[str, str] = {}
    artifacts = config.get("sealed_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("persistent candidate sealed-artifact list is missing")
    labels: set[str] = set()
    paths_by_label: dict[str, str] = {}
    for entry in artifacts:
        if not isinstance(entry, dict):
            raise ValueError("persistent candidate sealed-artifact entry is invalid")
        label = str(entry.get("label") or "").strip()
        if not label or label in labels:
            raise ValueError("persistent candidate sealed-artifact label is invalid")
        labels.add(label)
        relative_path = str(entry.get("path") or "").replace("\\", "/")
        paths_by_label[label] = relative_path
        path = project_file(relative_path)
        expected_hash = _require_sha256(entry.get("sha256"), f"{label} expected hash")
        if not path.is_file():
            raise ValueError(f"persistent candidate artifact is missing: {label}")
        actual_hash = sha256_file(path)
        if not hmac.compare_digest(actual_hash, expected_hash):
            raise ValueError(f"persistent candidate artifact hash mismatch: {label}")
        hashes[label] = actual_hash

    required_labels = {
        "candidate_contract",
        "candidate_client",
        "candidate_worker",
        "blackwell_python",
        "dependency_manifest",
        "gpu_readiness",
        "sealed_cpu_worker",
        "dialogue_audio_signal",
        "dialogue_tts",
        "installed_chatterbox_tts_source",
        "approved_profile",
        "approved_reference",
        "production_routing_manifest",
    }
    if labels != required_labels:
        missing = sorted(required_labels - labels)
        unexpected = sorted(labels - required_labels)
        raise ValueError(
            f"persistent candidate artifact set mismatch: missing={missing}, unexpected={unexpected}"
        )
    expected_paths = {
        "candidate_contract": exact_values["contract"],
        "candidate_client": exact_values["client"],
        "candidate_worker": exact_values["worker"],
        "blackwell_python": exact_values["python"],
        "dependency_manifest": (
            "Voice/sidecars/chatterbox_blackwell_gpu/evidence/dependency_manifest.json"
        ),
        "gpu_readiness": (
            "Voice/sidecars/chatterbox_blackwell_gpu/evidence/"
            "torch_gpu_readiness_postdeps.json"
        ),
        "sealed_cpu_worker": "Voice/sidecars/chatterbox_py311/sidecar_worker.py",
        "dialogue_audio_signal": "Core/dialogue_audio_signal.py",
        "dialogue_tts": "Core/dialogue_tts.py",
        "installed_chatterbox_tts_source": (
            "Voice/sidecars/chatterbox_blackwell_gpu/.venv/Lib/site-packages/"
            "chatterbox/tts.py"
        ),
        "approved_profile": exact_values["approved_profile"],
        "approved_reference": exact_values["approved_reference"],
        "production_routing_manifest": "Voice/sidecars/kira_approved_voice_routing.json",
    }
    if paths_by_label != expected_paths:
        raise ValueError("persistent candidate sealed-artifact path mapping changed")
    fixed_hashes = {
        "blackwell_python": "21bb438c0d4a6f1f164b9a646f6ee000340185e5871180aec06db8d3f07c0082",
        "dependency_manifest": "7266ab156aa2764e9145d3122a5bad3ae18c6392867c44d0dd2e19dfad4c5665",
        "gpu_readiness": "5d74d70ae2c486d432e7a56a2710ef377c0c6c15ca8bb605e6c2d6b0688b0117",
        "sealed_cpu_worker": "856c195173f8932f1b9d731634290f9eb78bb543e90da37c1346160e45334f46",
        "dialogue_audio_signal": "893970380087558d7992888d00aaade97e34416ef71e395bab1f20d6635c9aa3",
        "dialogue_tts": "3de4d2e1d30bde6fc96061a7990544ca9712ee7d39a90bfaa66fcd1494c4b22c",
        "installed_chatterbox_tts_source": (
            "7896787bc17e20eafcd1dce7b8a4a6ea3a6478baab771c60d63e9e81f5564195"
        ),
        "approved_profile": exact_values["approved_profile_sha256"],
        "approved_reference": exact_values["approved_reference_sha256"],
        "production_routing_manifest": (
            "a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81"
        ),
    }
    for label, expected_hash in fixed_hashes.items():
        if hashes.get(label) != expected_hash:
            raise ValueError(f"persistent candidate fixed artifact changed: {label}")

    profile = project_file(config.get("approved_profile"))
    reference = project_file(config.get("approved_reference"))
    profile_hash = _require_sha256(config.get("approved_profile_sha256"), "profile hash")
    reference_hash = _require_sha256(config.get("approved_reference_sha256"), "reference hash")
    if hashes["approved_profile"] != profile_hash:
        raise ValueError("persistent candidate approved-profile binding mismatch")
    if hashes["approved_reference"] != reference_hash:
        raise ValueError("persistent candidate approved-reference binding mismatch")
    profile_data = json.loads(profile.read_text(encoding="utf-8-sig"))
    source = profile_data.get("source_audio") if isinstance(profile_data, dict) else None
    source = source if isinstance(source, dict) else {}
    approved = str(source.get("approved_reference_wav") or "").replace("\\", "/")
    if source.get("required") is not True or approved != config.get("approved_reference"):
        raise ValueError("approved profile no longer requires the exact approved reference")
    if reference != project_file(approved):
        raise ValueError("approved reference resolved-path mismatch")

    generation = config.get("generation") if isinstance(config.get("generation"), dict) else {}
    if generation != {
        "repetition_penalty": 1.2,
        "min_p": 0.05,
        "top_p": 1.0,
        "exaggeration": 0.5,
        "cfg_weight": 0.5,
        "temperature": 0.8,
    }:
        raise ValueError("persistent candidate generation settings changed")
    return hashes


def verify_identity_files(config: dict[str, Any]) -> dict[str, str]:
    """Recheck the exact approved identity immediately before load/request."""

    profile = project_file(config.get("approved_profile"))
    reference = project_file(config.get("approved_reference"))
    expected_profile = _require_sha256(config.get("approved_profile_sha256"), "profile hash")
    expected_reference = _require_sha256(config.get("approved_reference_sha256"), "reference hash")
    actual_profile = sha256_file(profile)
    actual_reference = sha256_file(reference)
    if not hmac.compare_digest(actual_profile, expected_profile):
        raise ValueError("approved Kira voice profile changed")
    if not hmac.compare_digest(actual_reference, expected_reference):
        raise ValueError("approved Kira voice reference changed")
    return {
        "profile_sha256": actual_profile,
        "reference_sha256": actual_reference,
    }


def safe_output_path(relative: Any, config: dict[str, Any]) -> Path:
    target = project_file(relative)
    if target.suffix.casefold() != ".wav":
        raise ValueError("persistent candidate output must be a WAV")
    allowed = False
    for root_value in config.get("allowed_output_roots") or []:
        root = project_file(root_value)
        try:
            target.relative_to(root)
            allowed = target != root
        except ValueError:
            continue
        if allowed:
            break
    if not allowed:
        raise ValueError("persistent candidate output is outside approved project roots")
    return target


def validate_session_nonce(value: Any, expected: str) -> None:
    supplied = str(value or "")
    if len(supplied) < 32 or len(supplied) > 256:
        raise ValueError("invalid persistent candidate session nonce")
    if not hmac.compare_digest(supplied, expected):
        raise ValueError("persistent candidate session nonce mismatch")


def validate_envelope(
    request: Any,
    *,
    config: dict[str, Any],
    session_nonce: str,
    seen_request_ids: set[str],
) -> dict[str, Any]:
    if not isinstance(request, dict) or request.get("schema_version") != 1:
        raise ValueError("invalid persistent candidate request schema")
    validate_session_nonce(request.get("session_nonce"), session_nonce)
    request_id = str(request.get("request_id") or "")
    try:
        uuid.UUID(request_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("invalid persistent candidate request id") from exc
    if request_id in seen_request_ids:
        raise ValueError("persistent candidate request id replayed")
    operation = str(request.get("operation") or "")
    if operation not in {"status", "load", "synthesize", "unload", "shutdown"}:
        raise ValueError("unsupported persistent candidate operation")
    if request.get("playback") not in (None, False):
        raise ValueError("playback is forbidden inside the persistent candidate")
    if request.get("fallback") not in (None, False):
        raise ValueError("fallback is forbidden inside the persistent candidate")
    seen_request_ids.add(request_id)
    return dict(request)


def validate_synthesis_request(request: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    if request.get("channel") != config.get("input_channel"):
        raise ValueError("persistent candidate accepts only public SPOKEN text")
    text = str(request.get("text") or "").strip()
    max_chars = int((config.get("bounds") or {}).get("max_text_characters") or 0)
    if not text or len(text) > max_chars:
        raise ValueError("public spoken text is empty or oversized")
    lowered = text.casefold()
    if any(marker in lowered for marker in PRIVATE_MARKERS):
        raise ValueError("private or factual channel marker reached persistent candidate")
    if request.get("text_sha256") != sha256_text(text):
        raise ValueError("persistent candidate spoken-text hash mismatch")
    if request.get("profile_sha256") != config.get("approved_profile_sha256"):
        raise ValueError("request did not bind the approved profile hash")
    if request.get("reference_sha256") != config.get("approved_reference_sha256"):
        raise ValueError("request did not bind the approved reference hash")
    target = safe_output_path(request.get("output_relative"), config)
    if target.exists():
        raise FileExistsError("persistent candidate refuses to overwrite an existing WAV")
    calibration: dict[str, float] = {}
    limits = {
        "pcm_output_gain_db": (-60.0, 6.0),
        "proximity_cut_hz": (0.0, 12000.0),
        "proximity_cut_mix": (0.0, 1.0),
    }
    for key, (minimum, maximum) in limits.items():
        raw = request.get(key, 0.0)
        if isinstance(raw, bool):
            raise ValueError(f"invalid persistent candidate calibration: {key}")
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid persistent candidate calibration: {key}") from exc
        if not minimum <= value <= maximum:
            raise ValueError(f"out-of-range persistent candidate calibration: {key}")
        calibration[key] = value
    return {
        **request,
        "text": text,
        "target": target,
        "calibration": calibration,
    }


def qwen_residency_evidence(config: dict[str, Any], timeout_seconds: float = 2.0) -> dict[str, Any]:
    """Read exact local residency without loading or unloading any model."""

    endpoint = str(config.get("qwen_ps_endpoint") or "")
    expected_digest = str(config.get("qwen_digest") or "").casefold()
    expected_name = str(config.get("qwen_model") or "").casefold()
    try:
        opener = urllib_request.build_opener(urllib_request.ProxyHandler({}))
        with opener.open(
            urllib_request.Request(endpoint, method="GET"),
            timeout=max(0.2, min(5.0, float(timeout_seconds))),
        ) as response:
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("Ollama /api/ps response exceeded 1 MiB")
        payload = json.loads(raw.decode("utf-8"))
        models = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(models, list):
            raise ValueError("Ollama /api/ps did not return a models list")
        matches: list[dict[str, str]] = []
        for item in models:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "")
            model = str(item.get("model") or "")
            digest = str(item.get("digest") or "").casefold()
            identity = f"{name} {model}".casefold()
            if "qwen" in identity or expected_name in identity or digest == expected_digest:
                matches.append({"name": name, "model": model, "digest": digest})
        return {
            "query_succeeded": True,
            "qwen_absent_proven": not matches,
            "qwen_records": matches,
            "endpoint": endpoint,
            "model_state_changed": False,
        }
    except Exception as exc:
        return {
            "query_succeeded": False,
            "qwen_absent_proven": False,
            "qwen_records": [],
            "endpoint": endpoint,
            "reason": "qwen_residency_query_failed_gpu_blocked",
            "error": f"{type(exc).__name__}: {exc}",
            "model_state_changed": False,
        }


def verify_restricted_environment(config: dict[str, Any], *, require_load_opt_in: bool) -> dict[str, str]:
    if os.environ.get("KIRA_PERSISTENT_BLACKWELL_CANDIDATE") != "1":
        raise ValueError("persistent Blackwell candidate requires explicit process opt-in")
    if require_load_opt_in and os.environ.get("KIRA_PERSISTENT_BLACKWELL_ALLOW_MODEL_LOAD") != "1":
        raise ValueError("persistent Blackwell model load requires explicit acceptance opt-in")
    if os.environ.get("HF_HUB_OFFLINE") != "1" or os.environ.get("TRANSFORMERS_OFFLINE") != "1":
        raise ValueError("persistent Blackwell candidate requires offline cache-only mode")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise ValueError("persistent Blackwell candidate requires CUDA_VISIBLE_DEVICES=0")
    nonce = str(os.environ.get("KIRA_PERSISTENT_BLACKWELL_SESSION_NONCE") or "")
    if len(nonce) < 32 or len(nonce) > 256:
        raise ValueError("persistent Blackwell candidate session nonce is missing or invalid")

    cache_root = project_file(config.get("runtime_cache_root"))
    cache_root.mkdir(parents=True, exist_ok=True)
    expected = {
        "TORCHINDUCTOR_CACHE_DIR": cache_root / "torchinductor",
        "TRITON_CACHE_DIR": cache_root / "triton",
        "TEMP": cache_root / "temp",
        "TMP": cache_root / "temp",
    }
    resolved: dict[str, str] = {}
    for key, expected_path in expected.items():
        actual = Path(str(os.environ.get(key) or "")).resolve()
        expected_resolved = expected_path.resolve()
        actual.relative_to(cache_root.resolve())
        if actual != expected_resolved:
            raise ValueError(f"persistent candidate controlled cache mismatch: {key}")
        actual.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="kira_voice_probe_", dir=actual, delete=True):
            pass
        resolved[key] = str(actual)
    return resolved


def validate_wav(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        sample_rate = handle.getframerate()
        frames = handle.getnframes()
        payload = handle.readframes(frames)
    if sample_width != 2:
        raise ValueError("persistent candidate WAV is not PCM16")
    import array
    import math
    import sys

    samples = array.array("h")
    samples.frombytes(payload[: len(payload) - (len(payload) % 2)])
    if sys.byteorder != "little":
        samples.byteswap()
    peak = max((abs(int(value)) for value in samples), default=0) / 32767.0
    rms = math.sqrt(sum(float(value) ** 2 for value in samples) / len(samples)) / 32767.0 if samples else 0.0
    duration = frames / sample_rate if sample_rate else 0.0
    passed = channels == 1 and sample_rate >= 8000 and duration >= 0.1 and peak >= 0.001 and rms >= 0.0001
    return {
        "passed": passed,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate": sample_rate,
        "frames": frames,
        "duration_seconds": round(duration, 6),
        "peak_normalized": round(peak, 8),
        "rms_normalized": round(rms, 8),
        "non_silent": peak >= 0.001 and rms >= 0.0001,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


class PhaseLedger:
    """Append-only monotonic/UTC phase records for one operation."""

    def __init__(
        self,
        event_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.records: list[dict[str, Any]] = []
        self._event_callback = event_callback

    def _emit_phase_event(self, state: str, record: dict[str, Any]) -> None:
        if self._event_callback is None:
            return
        self._event_callback(
            {
                "phase_event_schema_version": 1,
                "phase_state": state,
                **dict(record),
            }
        )

    @contextmanager
    def phase(self, name: str, **metadata: Any) -> Iterator[None]:
        start_monotonic_ns = time.perf_counter_ns()
        start_utc_ns = time.time_ns()
        record: dict[str, Any] = {
            "phase": str(name),
            "start_monotonic_ns": start_monotonic_ns,
            "start_utc_ns": start_utc_ns,
            **metadata,
        }
        self._emit_phase_event("started", record)
        try:
            yield
        except Exception as exc:
            record["status"] = "failed"
            record["error_type"] = type(exc).__name__
            raise
        else:
            record["status"] = "passed"
        finally:
            end_monotonic_ns = time.perf_counter_ns()
            record["end_monotonic_ns"] = end_monotonic_ns
            record["end_utc_ns"] = time.time_ns()
            record["elapsed_seconds"] = round(
                (end_monotonic_ns - start_monotonic_ns) / 1_000_000_000,
                9,
            )
            self.records.append(record)
            self._emit_phase_event("finished", record)


def call_with_phase(
    ledger: PhaseLedger,
    name: str,
    callback: Callable[[], Any],
    **metadata: Any,
) -> Any:
    with ledger.phase(name, **metadata):
        return callback()
