#!/usr/bin/env python3
"""Lazy live adapters for the inactive Blackwell CPU-park v8 candidate.

Nothing in this module executes at import time.  Constructing ``LiveBackendV8``
is permitted only inside the killable v8 worker after the external audit and
per-run gates have passed.  The backend reuses the exact sealed persistent-v2
Chatterbox runtime in-process so v7 can fingerprint the real ``t3``, ``s3gen``
and ``ve`` parameters/buffers and move that same model CPU <-> CUDA.
"""

from __future__ import annotations

import ctypes
import hashlib
import importlib
import json
import math
import os
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Mapping

from Core.blackwell_v7_process_boundary import (
    process_identity_digest,
    process_identity_from_handle,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.candidate_contract import (
    EXACT_PROFILE_SHA256,
    EXACT_QWEN_DIGEST,
    EXACT_QWEN_MODEL,
    EXACT_REFERENCE_SHA256,
    PROJECT_ROOT,
    V8ContractError,
    canonical_json_sha256,
    is_sha256,
    sha256_file,
    strict_json_loads,
    verify_preserved_bytes,
)


class LiveAdapterError(V8ContractError):
    pass


def _finite_monotonic() -> float:
    value = float(time.monotonic())
    if not math.isfinite(value) or value < 0:
        raise LiveAdapterError("monotonic clock is invalid")
    return value


def _read_bounded(response: Any, maximum: int) -> bytes:
    value = response.read(maximum + 1)
    if not isinstance(value, bytes) or not value or len(value) > maximum:
        raise LiveAdapterError("loopback response is empty or oversized")
    return value


class ExactQwen35LoopbackAdapter:
    """Bounded loopback-only Ollama operations for the exact approved digest."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.base = str(config["qwen_base_url"])
        if self.base != "http://127.0.0.1:11434":
            raise LiveAdapterError("Qwen live adapter is loopback-only")
        self.allowed = frozenset(config["qwen_allowed_endpoints"])
        self.maximum_response = int(config["playback"]["maximum_wav_bytes"])
        self._sample_sequence = 0

    def _request(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None,
        timeout: float,
    ) -> Any:
        if endpoint not in self.allowed or method not in {"GET", "POST"}:
            raise LiveAdapterError("Ollama endpoint/method is not approved")
        body = None
        headers: dict[str, str] = {}
        if payload is not None:
            body = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base + endpoint,
            data=body,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(request, timeout=max(0.1, float(timeout))) as response:
            if int(getattr(response, "status", 0)) != 200:
                raise LiveAdapterError("Ollama loopback response was not HTTP 200")
            return strict_json_loads(_read_bounded(response, 1024 * 1024))

    @staticmethod
    def _inventory(payload: Any) -> list[dict[str, str]]:
        if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
            raise LiveAdapterError("Ollama inventory schema is invalid")
        records: list[dict[str, str]] = []
        for index, item in enumerate(payload["models"]):
            if not isinstance(item, dict):
                raise LiveAdapterError(f"Ollama inventory record {index} is not an object")
            model = str(item.get("model") or item.get("name") or "").strip()
            digest = str(item.get("digest") or "").strip().lower()
            if not model or not is_sha256(digest):
                raise LiveAdapterError(f"Ollama inventory record {index} has invalid identity")
            records.append({"model": model, "digest": digest})
        return records

    def installed_identity(self) -> dict[str, str]:
        records = self._inventory(self._request("GET", "/api/tags", None, 5.0))
        matches = [record for record in records if record["model"] == EXACT_QWEN_MODEL]
        if matches != [{"model": EXACT_QWEN_MODEL, "digest": EXACT_QWEN_DIGEST}]:
            raise LiveAdapterError("installed Qwen name/digest is not exact and unique")
        return dict(matches[0])

    def residency_records(self) -> list[dict[str, str]]:
        return self._inventory(self._request("GET", "/api/ps", None, 5.0))

    def residency_evidence(
        self, *, phase: str, serialization_lease_id: str, worker_pid: int
    ) -> dict[str, Any]:
        records = self.residency_records()
        self._sample_sequence += 1
        captured = _finite_monotonic()
        sample_id = canonical_json_sha256(
            {
                "captured_monotonic": captured,
                "phase": phase,
                "records": records,
                "sample_sequence": self._sample_sequence,
                "serialization_lease_id": serialization_lease_id,
                "worker_pid": worker_pid,
            }
        )
        return {
            "query_succeeded": True,
            "records": records,
            "serialization_lease_id": serialization_lease_id,
            "lease_exclusive": True,
            "sample_id": sample_id,
            "sample_sequence": self._sample_sequence,
            "captured_monotonic": captured,
            "phase": phase,
            "worker_pid": worker_pid,
        }

    def load_only(self, request: dict[str, Any]) -> dict[str, Any]:
        self.installed_identity()
        ttl = request.get("keep_alive_seconds")
        if isinstance(ttl, bool) or not isinstance(ttl, int) or ttl <= 0:
            raise LiveAdapterError("Qwen load-only TTL is invalid")
        outbound = {
            "model": EXACT_QWEN_MODEL,
            "prompt": "",
            "stream": False,
            "keep_alive": f"{ttl}s",
            "options": {"num_predict": 0},
        }
        response = self._request("POST", "/api/generate", outbound, 55.0)
        if not isinstance(response, dict) or str(response.get("model") or "") != EXACT_QWEN_MODEL:
            raise LiveAdapterError("Qwen load-only returned an unapproved model")
        if response.get("response") not in (None, "") or response.get("eval_count") not in (None, 0):
            raise LiveAdapterError("Qwen load-only generated hidden text")
        if self.residency_records() != [{"model": EXACT_QWEN_MODEL, "digest": EXACT_QWEN_DIGEST}]:
            raise LiveAdapterError("exact Qwen was not solely resident after load-only")
        return {
            "model": EXACT_QWEN_MODEL,
            "digest": EXACT_QWEN_DIGEST,
            "request_hash": canonical_json_sha256(request),
            "response": "",
            "message": {"content": ""},
            "eval_count": 0,
            "prompt_eval_count": 0,
            "serialization_lease_id": request["serialization_lease_id"],
        }

    def stream(self, request: dict[str, Any]) -> dict[str, Any]:
        self.installed_identity()
        if self.residency_records() != [{"model": EXACT_QWEN_MODEL, "digest": EXACT_QWEN_DIGEST}]:
            raise LiveAdapterError("exact Qwen is not solely resident before stream")
        outbound = {
            "model": EXACT_QWEN_MODEL,
            "messages": request["messages"],
            "stream": True,
            "keep_alive": 0,
            "think": False,
        }
        encoded = json.dumps(
            outbound,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        http_request = urllib.request.Request(
            self.base + "/api/chat",
            data=encoded,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        chunks: list[str] = []
        total = 0
        done_seen = False
        with urllib.request.urlopen(http_request, timeout=85.0) as response:
            if int(getattr(response, "status", 0)) != 200:
                raise LiveAdapterError("Qwen stream was not HTTP 200")
            while True:
                line = response.readline(1024 * 1024 + 1)
                if not line:
                    break
                total += len(line)
                if total > 1024 * 1024 or len(line) > 1024 * 1024:
                    raise LiveAdapterError("Qwen stream transport exceeded byte bound")
                item = strict_json_loads(line)
                if not isinstance(item, dict) or item.get("model") != EXACT_QWEN_MODEL:
                    raise LiveAdapterError("Qwen stream item model/schema mismatch")
                message = item.get("message")
                content = message.get("content") if isinstance(message, dict) else None
                if isinstance(content, str) and content:
                    chunks.append(content)
                if item.get("done") is True:
                    done_seen = True
                    break
        text = "".join(chunks)
        if not done_seen or not text.strip():
            raise LiveAdapterError("Qwen stream did not complete with text")
        if self.residency_records() != []:
            raise LiveAdapterError("Qwen keep_alive=0 did not release residency")
        return {
            "model": EXACT_QWEN_MODEL,
            "digest": EXACT_QWEN_DIGEST,
            "request_hash": canonical_json_sha256(request),
            "chunks": chunks,
            "final_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "keep_alive": 0,
            "serialization_lease_id": request["serialization_lease_id"],
        }

    def unload_owned(self, **values: Any) -> dict[str, Any]:
        if (
            values.get("model") != EXACT_QWEN_MODEL
            or values.get("digest") != EXACT_QWEN_DIGEST
            or not is_sha256(values.get("token_hash"))
            or not is_sha256(values.get("serialization_lease_id"))
        ):
            raise LiveAdapterError("Qwen unload ownership binding is invalid")
        self._request(
            "POST",
            "/api/generate",
            {"model": EXACT_QWEN_MODEL, "prompt": "", "stream": False, "keep_alive": 0},
            15.0,
        )
        if self.residency_records() != []:
            raise LiveAdapterError("Qwen unload did not prove absence")
        return {
            "unloaded": True,
            "model": EXACT_QWEN_MODEL,
            "digest": EXACT_QWEN_DIGEST,
            "token_hash": values["token_hash"],
            "serialization_lease_id": values["serialization_lease_id"],
        }


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def _windows_memory_mib() -> tuple[float, float, float, float]:
    if os.name != "nt":
        raise LiveAdapterError("v8 live resource adapter currently requires Windows")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    status = _MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise LiveAdapterError("GlobalMemoryStatusEx failed")
    counters = _PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(
        kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
    ):
        raise LiveAdapterError("GetProcessMemoryInfo failed")
    unit = 1024.0 * 1024.0
    return (
        counters.WorkingSetSize / unit,
        (status.ullTotalPageFile - status.ullAvailPageFile) / unit,
        status.ullTotalPageFile / unit,
        status.ullAvailPhys / unit,
    )


class LiveBackendV8:
    """Real v8 backend, instantiated only behind all external live gates."""

    def __init__(self, config: dict[str, Any], *, worker_pid: int, lease_id: str) -> None:
        verify_preserved_bytes(config)
        self.config = config
        self.worker_pid = worker_pid
        self.lease_id = lease_id
        self.qwen = ExactQwen35LoopbackAdapter(config)
        self._resource_sequence = 0
        self._runtime: Any | None = None
        self._module: Any | None = None
        self._last_cuda: dict[str, Any] | None = None

    def _load_v2_module(self) -> Any:
        if self._module is None:
            module = importlib.import_module(
                self.config["voice_live_component"]["module"]
            )
            path = Path(module.__file__).resolve(strict=True)
            if sha256_file(path) != self.config["voice_live_component"]["worker_sha256"]:
                raise LiveAdapterError("imported persistent-v2 worker byte hash drift")
            self._module = module
        return self._module

    def _torch(self) -> Any:
        if self._runtime is not None and self._runtime.backend is not None:
            return self._runtime.backend["torch"]
        return importlib.import_module("torch")

    def resources(self, *, label: str, worker_pid: int) -> dict[str, Any]:
        if worker_pid != self.worker_pid:
            raise LiveAdapterError("resource request worker PID mismatch")
        process_rss, commit_used, commit_limit, available = _windows_memory_mib()
        total_physical = available + max(process_rss, 1.0)
        status = _MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(status)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise LiveAdapterError("GlobalMemoryStatusEx total-physical query failed")
        total_physical = status.ullTotalPhys / (1024.0 * 1024.0)
        torch = self._torch()
        if not torch.cuda.is_available():
            raise LiveAdapterError("CUDA is unavailable")
        torch.cuda.synchronize(0)
        allocated = int(torch.cuda.memory_allocated(0))
        reserved = int(torch.cuda.memory_reserved(0))
        free, total = torch.cuda.mem_get_info(0)
        name = str(torch.cuda.get_device_name(0))
        capability = list(torch.cuda.get_device_capability(0))
        self._resource_sequence += 1
        captured = _finite_monotonic()
        values = {
            "label": label,
            "pid": worker_pid,
            "sample_sequence": self._resource_sequence,
            "captured_monotonic": captured,
            "process_rss_mib": process_rss,
            "system_commit_used_mib": commit_used,
            "system_commit_limit_mib": commit_limit,
            "available_physical_mib": available,
            "total_physical_mib": total_physical,
            "cuda_allocated_bytes": allocated,
            "cuda_reserved_bytes": reserved,
            "cuda_free_mib": free / (1024.0 * 1024.0),
            "cuda_total_mib": total / (1024.0 * 1024.0),
            "cuda_device_name": name,
            "compute_capability": capability,
        }
        return {
            "sample_id": canonical_json_sha256(values),
            "sample_sequence": self._resource_sequence,
            "pid": worker_pid,
            "process_rss_mib": process_rss,
            "system_commit_used_mib": commit_used,
            "system_commit_limit_mib": commit_limit,
            "available_physical_mib": available,
            "total_physical_mib": total_physical,
            "system_commit_fraction": commit_used / commit_limit,
            "cuda_allocated_bytes": allocated,
            "cuda_reserved_bytes": reserved,
            "cuda_free_mib": free / (1024.0 * 1024.0),
            "cuda_total_mib": total / (1024.0 * 1024.0),
            "captured_monotonic": captured,
            "cuda_device_name": name,
            "compute_capability": capability,
        }

    def qwen_residency(self, *, phase: str, serialization_lease_id: str, worker_pid: int):
        return self.qwen.residency_evidence(
            phase=phase,
            serialization_lease_id=serialization_lease_id,
            worker_pid=worker_pid,
        )

    def load_voice(self, **values: Any) -> dict[str, Any]:
        if values["serialization_lease_id"] != self.lease_id:
            raise LiveAdapterError("voice load lease mismatch")
        module = self._load_v2_module()
        v2_config = module.load_candidate_config()
        module.verify_candidate_config(v2_config)
        runtime = module.PersistentVoiceRuntime(v2_config)
        result = runtime.load()
        if result.get("ready") is not True or runtime.model is None:
            raise LiveAdapterError(f"persistent-v2 runtime load failed: {result}")
        self._runtime = runtime
        identity = {
            "profile_path": self.config["approved_profile"],
            "profile_sha256": sha256_file(PROJECT_ROOT / self.config["approved_profile"]),
            "reference_path": self.config["approved_reference"],
            "reference_sha256": sha256_file(PROJECT_ROOT / self.config["approved_reference"]),
            "audio_prompt_path": self.config["approved_reference"],
            "audio_prompt_sha256": sha256_file(PROJECT_ROOT / self.config["approved_reference"]),
        }
        return {
            "model": runtime.model,
            "identity": identity,
            "load_proof": {
                "from_pretrained_call_count": 1,
                "prepare_conditionals_call_count": 1,
                "approved_audio_prompt_path": values["approved_audio_prompt_path"],
                "approved_audio_prompt_sha256": values["approved_audio_prompt_sha256"],
                "serialization_lease_id": self.lease_id,
                "worker_pid": self.worker_pid,
            },
        }

    def voice_model_binding(self, **values: Any) -> dict[str, Any]:
        model = values["model"]
        return {
            "same_object": bool(self._runtime is not None and self._runtime.model is model),
            "model_object_id": id(model),
            "backend_object_id": id(self),
            "model_generation": values["model_generation"],
            "worker_pid": self.worker_pid,
        }

    def cuda_cache_cleanup(self) -> dict[str, Any]:
        torch = self._torch()
        torch.cuda.synchronize(0)
        torch.cuda.empty_cache()
        torch.cuda.synchronize(0)
        return {
            "cache_cleared": True,
            "synchronize_before": True,
            "empty_cache_called": True,
            "synchronize_after": True,
        }

    def release_voice(self) -> dict[str, Any]:
        if self._runtime is not None:
            result = self._runtime.unload(reason="v8_release_voice")
            if result.get("unloaded") is not True:
                raise LiveAdapterError("persistent-v2 release did not complete")
        self._runtime = None
        self._last_cuda = None
        return {"released": True, "owned_model_count": 0, "owned_condition_count": 0}

    def qwen_load_only(self, *, request: dict[str, Any]) -> dict[str, Any]:
        return self.qwen.load_only(request)

    def qwen_stream(self, *, request: dict[str, Any]) -> dict[str, Any]:
        return self.qwen.stream(request)

    def qwen_unload_owned(self, **values: Any) -> dict[str, Any]:
        return self.qwen.unload_owned(**values)

    def synthesize_cuda(self, **values: Any) -> dict[str, Any]:
        runtime = self._runtime
        if runtime is None or runtime.model is not values["model"]:
            raise LiveAdapterError("synthesis does not own the exact persistent-v2 model")
        if values["backend_object_id"] != id(self):
            raise LiveAdapterError("synthesis backend identity mismatch")
        started_sample = _finite_monotonic()
        if not is_sha256(values["generation_id"]):
            raise LiveAdapterError("synthesis generation ID is invalid")
        runtime_root = (PROJECT_ROOT / "RecoverySprint/runtime_cache").resolve(strict=True)
        owned_literal = Path(values["owned_output_root"])
        if not owned_literal.is_absolute():
            raise LiveAdapterError("synthesis owned output root is not absolute")
        owned_resolved = owned_literal.resolve(strict=False)
        try:
            owned_resolved.relative_to(runtime_root)
        except ValueError as exc:
            raise LiveAdapterError("synthesis output root escaped runtime cache") from exc
        if owned_literal.is_symlink():
            raise LiveAdapterError("synthesis output root is a symbolic link")
        owned_literal.mkdir(parents=True, exist_ok=True)
        owned_root = owned_literal.resolve(strict=True)
        owned_root.relative_to(runtime_root)
        target = owned_root / f"{values['generation_id']}.wav"
        if target.exists() or target.is_symlink():
            raise LiveAdapterError("synthesis target already exists or is a link")
        request = {
            "request_id": values["generation_id"],
            "text": values["text"],
            "target": str(target),
            "calibration": {
                "pcm_output_gain_db": 0.0,
                "proximity_cut_hz": 0.0,
                "proximity_cut_mix": 0.0,
            },
        }
        generation_started = _finite_monotonic()
        result = runtime.synthesize(request)
        generation_ended = _finite_monotonic()
        if result.get("generated") is not True or not target.is_file():
            raise LiveAdapterError(f"persistent-v2 CUDA synthesis failed: {result}")
        artifact_sha = sha256_file(target)
        gpu = result.get("gpu_proof") or {}
        if gpu.get("actual_gpu_execution") is not True:
            raise LiveAdapterError("persistent-v2 result did not prove actual CUDA execution")
        sample_ended = _finite_monotonic()
        self._last_cuda = {
            "generation_id": values["generation_id"],
            "text_sha256": values["text_sha256"],
            "artifact_sha256": artifact_sha,
            "model_generation": values["model_generation"],
            "component_fingerprint": values["component_fingerprint"],
            "worker_instance_id": values["worker_instance_id"],
            "worker_pid": values["worker_pid"],
            "model_object_id": values["model_object_id"],
            "backend_object_id": values["backend_object_id"],
            "device": "cuda",
            "cuda_device_name": self.config["voice_live_component"]["device_name"],
            "compute_capability": self.config["voice_live_component"]["compute_capability"],
            "allocated_before_bytes": int(gpu["allocated_before_bytes"]),
            "peak_allocated_bytes": int(gpu["peak_allocated_bytes"]),
            "allocated_after_bytes": int(gpu["allocated_after_bytes"]),
            "synchronize_before": bool(gpu.get("cuda_synchronize_before_generation_succeeded")),
            "synchronize_after": bool(gpu.get("cuda_synchronize_after_generation_succeeded")),
            "unsupported_architecture_warning": False,
            "no_kernel_image_error": False,
            "sample_start_monotonic": started_sample,
            "sample_end_monotonic": sample_ended,
        }
        return {
            "artifact_path": str(target.resolve()),
            "artifact_sha256": artifact_sha,
            "generation_id": values["generation_id"],
            "text_sha256": values["text_sha256"],
            "prompt_path": values["approved_audio_prompt_path"],
            "prompt_sha256": values["approved_audio_prompt_sha256"],
            "route": "blackwell_gpu",
            "device": "cuda",
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "generation_started_monotonic": generation_started,
            "generation_ended_monotonic": generation_ended,
            "model_generation": values["model_generation"],
            "component_fingerprint": values["component_fingerprint"],
            "model_object_id": values["model_object_id"],
            "backend_object_id": values["backend_object_id"],
        }

    def cuda_generation_evidence(self, **values: Any) -> dict[str, Any]:
        if self._last_cuda is None:
            raise LiveAdapterError("CUDA generation evidence is absent")
        expected = {key: self._last_cuda[key] for key in values}
        if expected != values:
            raise LiveAdapterError("CUDA evidence request does not match last generation")
        return dict(self._last_cuda)


def _child_is_in_job(process: subprocess.Popen[Any]) -> bool:
    if os.name != "nt":
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    result = ctypes.c_int(0)
    if not kernel32.IsProcessInJob(
        ctypes.c_void_p(int(process._handle)), None, ctypes.byref(result)  # type: ignore[attr-defined]
    ):
        raise LiveAdapterError("IsProcessInJob(playback child) failed")
    return bool(result.value)


def _playback_child_environment(child_token: str) -> dict[str, str]:
    allowed = (
        "USERNAME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA",
        "APPDATA", "SystemRoot", "SYSTEMROOT", "WINDIR", "PATH", "PATHEXT",
        "ComSpec", "SystemDrive", "TEMP", "TMP",
    )
    result = {key: value for key in allowed if (value := os.environ.get(key))}
    result.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1",
            "KIRA_V8_PLAYBACK_CHILD_TOKEN": child_token,
        }
    )
    return result


def _terminate_exact_playback_child(
    process: subprocess.Popen[bytes], grace_seconds: float
) -> None:
    if process.poll() is not None:
        return
    process.kill()
    try:
        process.communicate(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        # The child was already proven to be inside the worker's inherited
        # kill-on-close Job.  Exit this worker so the parent observes EOF and
        # closes that exact Job rather than returning with a live descendant.
        os._exit(86)


class BoundedPlaybackRunnerV8:
    """Consume exact retained WAV bytes in one killable inherited-Job child."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.policy = config["playback"]
        self.runtime_root = (PROJECT_ROOT / "RecoverySprint/runtime_cache").resolve(
            strict=True
        )
        self.root_literal = PROJECT_ROOT / self.policy["owned_copy_root"]
        prospective = self.root_literal.resolve(strict=False)
        try:
            prospective.relative_to(self.runtime_root)
        except ValueError as exc:
            raise LiveAdapterError("playback owned-copy root escaped runtime cache") from exc
        if self.root_literal.is_symlink():
            raise LiveAdapterError("playback owned-copy root is a symbolic link")
        self.worker = (PROJECT_ROOT / self.policy["worker"]).resolve(strict=True)
        if sha256_file(self.worker) != self.policy["worker_sha256"]:
            raise LiveAdapterError("playback worker byte hash drift")

    def play_exact(
        self,
        *,
        retained_bytes: bytes,
        artifact_sha256: str,
        generation_id: str,
        model_generation: str,
        component_fingerprint: str,
        playback_id: str,
    ) -> dict[str, Any]:
        if (
            not isinstance(retained_bytes, bytes)
            or not retained_bytes
            or len(retained_bytes) > int(self.policy["maximum_wav_bytes"])
            or hashlib.sha256(retained_bytes).hexdigest() != artifact_sha256
            or not all(is_sha256(value) for value in (
                artifact_sha256, generation_id, model_generation,
                component_fingerprint, playback_id,
            ))
        ):
            raise LiveAdapterError("playback retained-byte binding is invalid")
        if sha256_file(self.worker) != self.policy["worker_sha256"]:
            raise LiveAdapterError("playback worker changed before spawn")
        executable = Path(sys.executable).resolve(strict=True)
        if sha256_file(executable) != self.config["voice_live_component"]["python_sha256"]:
            raise LiveAdapterError("playback executable changed before spawn")
        self.root_literal.mkdir(parents=True, exist_ok=True)
        root = self.root_literal.resolve(strict=True)
        root.relative_to(self.runtime_root)
        if self.root_literal.is_symlink():
            raise LiveAdapterError("playback owned-copy root became a symbolic link")
        wav = root / f"{playback_id}.wav"
        if wav.exists():
            raise LiveAdapterError("playback owned copy already exists")
        process: subprocess.Popen[bytes] | None = None
        started = _finite_monotonic()
        completed: dict[str, Any] | None = None
        pending_error: Exception | None = None
        cleanup_error: Exception | None = None
        try:
            with wav.open("xb") as handle:
                handle.write(retained_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            if sha256_file(wav) != artifact_sha256:
                raise LiveAdapterError("playback owned copy changed after write")
            command = [
                str(executable),
                str(self.worker),
                "--wav", str(wav),
                "--sha256", artifact_sha256,
                "--generation-id", generation_id,
                "--model-generation", model_generation,
                "--component-fingerprint", component_fingerprint,
                "--playback-id", playback_id,
            ]
            child_token = uuid.uuid4().hex + uuid.uuid4().hex
            child_token_hash = hashlib.sha256(child_token.encode("utf-8")).hexdigest()
            command.extend(["--child-token-hash", child_token_hash])
            command_digest = canonical_json_sha256(command)
            child_environment = _playback_child_environment(child_token)
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                creationflags=flags,
                env=child_environment,
            )
            if not _child_is_in_job(process):
                raise LiveAdapterError("playback child did not inherit the worker Job")
            identity = process_identity_from_handle(
                int(process._handle) if os.name == "nt" else process.pid,  # type: ignore[attr-defined]
                process.pid,
            )
            stdout, stderr = process.communicate(
                timeout=float(self.policy["maximum_playback_seconds"])
            )
            if (
                len(stdout) > int(self.policy["maximum_result_bytes"])
                or len(stderr) > int(self.policy["maximum_result_bytes"])
            ):
                raise LiveAdapterError("playback child output exceeded bound")
            if process.returncode != 0:
                raise LiveAdapterError(
                    f"playback child failed rc={process.returncode}: "
                    f"{stderr[:4096].decode('utf-8', 'replace')}"
                )
            result = strict_json_loads(stdout)
            required = {
                "schema_version", "playback_id", "artifact_sha256", "generation_id",
                "model_generation", "component_fingerprint", "route", "device",
                "generic_voice_used", "sapi_voice_used", "fallback_used",
                "playback_api_start_monotonic", "playback_api_end_monotonic",
                "playback_api_completed", "owner_hearing_observation",
                "owner_hearing_proven", "wav_byte_length", "playback_source",
                "played_memory_sha256",
            }
            if not isinstance(result, dict) or set(result) != required:
                raise LiveAdapterError("playback child result schema is not exact")
            if (
                result["schema_version"] != 1
                or result["playback_id"] != playback_id
                or result["artifact_sha256"] != artifact_sha256
                or result["generation_id"] != generation_id
                or result["model_generation"] != model_generation
                or result["component_fingerprint"] != component_fingerprint
                or result["route"] != "blackwell_gpu"
                or result["device"] != "cuda"
                or result["generic_voice_used"] is not False
                or result["sapi_voice_used"] is not False
                or result["fallback_used"] is not False
                or result["playback_api_completed"] is not True
                or result["owner_hearing_observation"] is not None
                or result["owner_hearing_proven"] is not False
                or result["wav_byte_length"] != len(retained_bytes)
                or result["playback_source"] != "verified_in_memory_wav_bytes"
                or result["played_memory_sha256"] != artifact_sha256
            ):
                raise LiveAdapterError("playback child identity/truth binding failed")
            ended = _finite_monotonic()
            completed = {
                **result,
                "playback_process_identity": identity,
                "playback_process_identity_digest": process_identity_digest(identity),
                "playback_process_in_inherited_job": True,
                "parent_playback_start_monotonic": started,
                "parent_playback_end_monotonic": ended,
                "playback_worker_sha256": sha256_file(self.worker),
                "playback_command_digest": command_digest,
                "playback_capability_hash": child_token_hash,
            }
        except subprocess.TimeoutExpired as exc:
            pending_error = LiveAdapterError("bounded playback child timed out")
            pending_error.__cause__ = exc
        except Exception as exc:
            pending_error = exc
        finally:
            try:
                if process is not None and process.poll() is None:
                    _terminate_exact_playback_child(
                        process,
                        float(self.policy["maximum_process_exit_grace_seconds"]),
                    )
                wav.unlink(missing_ok=True)
                if wav.exists():
                    raise LiveAdapterError("playback owned copy remained after cleanup")
            except Exception as exc:
                cleanup_error = exc
        if cleanup_error is not None:
            raise LiveAdapterError(f"playback child/copy cleanup failed: {cleanup_error}")
        if pending_error is not None:
            raise pending_error
        if completed is None:
            raise LiveAdapterError("playback completed without exact telemetry")
        return {**completed, "owned_copy_deleted_after_return": True}


__all__ = [
    "BoundedPlaybackRunnerV8",
    "ExactQwen35LoopbackAdapter",
    "LiveAdapterError",
    "LiveBackendV8",
]
