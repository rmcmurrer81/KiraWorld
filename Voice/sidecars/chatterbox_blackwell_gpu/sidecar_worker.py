#!/usr/bin/env python3
"""One-shot experimental Blackwell worker for Kira's sealed Chatterbox voice."""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
import traceback
import warnings
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(__file__).with_name("sidecar_config.json")
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


def project_file(relative: str) -> Path:
    value = Path(str(relative).replace("\\", "/"))
    if value.is_absolute() or ".." in value.parts:
        raise ValueError("unsafe project-relative path")
    resolved = (ROOT / value).resolve()
    resolved.relative_to(ROOT.resolve())
    return resolved


def load_and_verify_config() -> dict[str, Any]:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("unsupported Blackwell sidecar config schema")
    if str(os.environ.get("KIRA_BLACKWELL_VOICE_EXPERIMENT", "")).strip() != "1":
        raise ValueError("Blackwell candidate requires an explicit experiment opt-in")
    if sha256_file(Path(__file__)) != str(data.get("worker_sha256") or "").casefold():
        raise ValueError("Blackwell sidecar worker hash mismatch")

    sealed_files = (
        ("shared_worker", "shared_worker_sha256", "accepted CPU worker"),
        ("dependency_manifest", "dependency_manifest_sha256", "dependency manifest"),
        ("gpu_readiness", "gpu_readiness_sha256", "GPU readiness evidence"),
        ("approved_profile", "approved_profile_sha256", "voice profile"),
        ("approved_reference", "approved_reference_sha256", "approved reference"),
    )
    for path_key, hash_key, label in sealed_files:
        path = project_file(data[path_key])
        if not path.is_file() or sha256_file(path) != str(data.get(hash_key) or "").casefold():
            raise ValueError(f"{label} hash mismatch")

    profile = project_file(data["approved_profile"])
    profile_data = json.loads(profile.read_text(encoding="utf-8-sig"))
    source = profile_data.get("source_audio") or {}
    approved = str(source.get("approved_reference_wav") or "").replace("\\", "/")
    if source.get("required") is not True or approved != data["approved_reference"]:
        raise ValueError("voice profile no longer requires the sealed approved reference")
    if tuple(sys.version_info[:3]) != (3, 11, 9):
        raise ValueError("Blackwell sidecar requires exact Python 3.11.9")

    required_versions = {
        "chatterbox-tts": data["chatterbox_version"],
        "torch": data["torch_version"],
        "torchaudio": data["torchaudio_version"],
    }
    for package, expected in required_versions.items():
        actual = importlib.metadata.version(package)
        if actual != expected:
            raise ValueError(f"sealed dependency mismatch: {package}={actual}, expected {expected}")
    if str(os.environ.get("HF_HUB_OFFLINE", "")) != "1" or str(
        os.environ.get("TRANSFORMERS_OFFLINE", "")
    ) != "1":
        raise ValueError("Blackwell sidecar requires offline cache-only environment")
    if data.get("compute_device") != "cuda" or data.get("playback") is not False:
        raise ValueError("Blackwell sidecar policy mismatch")

    import torch
    import torchaudio

    cuda_checks = {
        "torch_runtime": torch.__version__ == data["torch_version"],
        "torchaudio_runtime": torchaudio.__version__ == data["torchaudio_version"],
        "cuda_runtime": torch.version.cuda == data["cuda_runtime"],
        "cuda_available": torch.cuda.is_available(),
        "device": torch.cuda.get_device_name(0) == data["required_device_name"] if torch.cuda.is_available() else False,
        "capability": list(torch.cuda.get_device_capability(0)) == [12, 0] if torch.cuda.is_available() else False,
        "sm_120": "sm_120" in torch.cuda.get_arch_list(),
    }
    if not all(cuda_checks.values()):
        raise ValueError(f"Blackwell CUDA readiness mismatch: {cuda_checks}")
    data["runtime_cuda_checks"] = cuda_checks
    return data


def load_shared_worker(config: dict[str, Any]) -> ModuleType:
    path = project_file(config["shared_worker"])
    spec = importlib.util.spec_from_file_location("kira_sealed_cpu_worker_contract", path)
    if spec is None or spec.loader is None:
        raise ImportError("unable to load shared sealed sidecar contract")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gpu_memory_used_mib() -> float | None:
    try:
        executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "nvidia-smi.exe"
        completed = subprocess.run(
            [str(executable), "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            text=True,
            capture_output=True,
            timeout=3,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        values = [float(line.strip()) for line in completed.stdout.splitlines() if line.strip()]
        return sum(values) if completed.returncode == 0 and values else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


class ResourceSampler:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="blackwell-voice-resource-sampler", daemon=True)
        self.samples = 0
        self.peak_process_rss_mib = 0.0
        self.peak_system_used_mib = 0.0
        self.baseline_gpu_used_mib: float | None = None
        self.peak_gpu_used_mib = 0.0

    def _sample(self) -> None:
        import psutil

        process_mib = psutil.Process().memory_info().rss / (1024 * 1024)
        memory = psutil.virtual_memory()
        gpu_mib = gpu_memory_used_mib()
        if self.samples == 0:
            self.baseline_gpu_used_mib = gpu_mib
        self.samples += 1
        self.peak_process_rss_mib = max(self.peak_process_rss_mib, process_mib)
        self.peak_system_used_mib = max(
            self.peak_system_used_mib,
            (memory.total - memory.available) / (1024 * 1024),
        )
        if gpu_mib is not None:
            self.peak_gpu_used_mib = max(self.peak_gpu_used_mib, gpu_mib)

    def _run(self) -> None:
        while not self._stop.wait(0.1):
            try:
                self._sample()
            except Exception:
                continue

    def start(self) -> None:
        self._sample()
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        self._thread.join(timeout=2)
        self._sample()
        baseline = self.baseline_gpu_used_mib
        return {
            "sample_count": self.samples,
            "peak_process_rss_mib": round(self.peak_process_rss_mib, 1),
            "peak_system_ram_used_mib": round(self.peak_system_used_mib, 1),
            "baseline_gpu_vram_used_mib": round(baseline, 1) if baseline is not None else None,
            "peak_gpu_vram_used_mib": round(self.peak_gpu_used_mib, 1) if self.peak_gpu_used_mib else None,
            "peak_sidecar_gpu_delta_mib": (
                round(max(0.0, self.peak_gpu_used_mib - baseline), 1)
                if baseline is not None and self.peak_gpu_used_mib
                else None
            ),
        }


def synthesize(config: dict[str, Any], shared: ModuleType) -> dict[str, Any]:
    import torch
    # Chatterbox imports these through Transformers' lazy module registry. A
    # cold first import failed in attempt 1 without exposing the nested cause.
    # Resolve the exact classes explicitly before Chatterbox inserts its model
    # stack, making the compatibility boundary deterministic and diagnosable.
    from transformers import GPT2Config, GPT2Model, LlamaConfig, LlamaModel

    request = shared.read_request(config)
    compatibility_imports = {
        "LlamaModel": LlamaModel.__module__,
        "LlamaConfig": LlamaConfig.__module__,
        "GPT2Model": GPT2Model.__module__,
        "GPT2Config": GPT2Config.__module__,
    }
    torch.cuda.synchronize(0)
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(0)
    free_before, total = torch.cuda.mem_get_info(0)
    captured: list[str] = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = shared.synthesize(request, config)
        captured = [str(item.message) for item in caught]
    torch.cuda.synchronize(0)
    peak_allocated = int(torch.cuda.max_memory_allocated(0))
    peak_reserved = int(torch.cuda.max_memory_reserved(0))
    torch.cuda.empty_cache()
    torch.cuda.synchronize(0)
    free_after, total_after = torch.cuda.mem_get_info(0)
    warning_text = "\n".join(captured).casefold()
    rejected = [value for value in REJECTED_RUNTIME_TEXT if value in warning_text]
    gpu_proof = {
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "device_name": torch.cuda.get_device_name(0),
        "device_capability": list(torch.cuda.get_device_capability(0)),
        "compiled_architectures": torch.cuda.get_arch_list(),
        "peak_allocated_bytes": peak_allocated,
        "peak_reserved_bytes": peak_reserved,
        "free_before_bytes": int(free_before),
        "free_after_empty_cache_bytes": int(free_after),
        "total_before_bytes": int(total),
        "total_after_bytes": int(total_after),
        "actual_gpu_allocation": peak_allocated >= 256 * 1024 * 1024,
        "captured_warnings": captured,
        "rejected_warning_matches": rejected,
    }
    result["gpu_proof"] = gpu_proof
    result["transformers_compatibility_imports"] = compatibility_imports
    if result.get("generated") is True and (not gpu_proof["actual_gpu_allocation"] or rejected):
        return {
            **result,
            "generated": False,
            "reason": "blackwell_gpu_execution_proof_failed",
            "gpu_proof": gpu_proof,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    sampler = ResourceSampler()
    sampler.start()
    started = time.perf_counter()
    try:
        config = load_and_verify_config()
        if args.self_check:
            result: dict[str, Any] = {
                "ready": True,
                "reason": "sealed_blackwell_sidecar_ready",
                "sidecar_id": config["sidecar_id"],
                "python_version": ".".join(str(value) for value in sys.version_info[:3]),
                "chatterbox_version": importlib.metadata.version("chatterbox-tts"),
                "torch_version": importlib.metadata.version("torch"),
                "torchaudio_version": importlib.metadata.version("torchaudio"),
                "reference_sha256": config["approved_reference_sha256"],
                "runtime_cuda_checks": config["runtime_cuda_checks"],
                "playback": False,
                "model_loaded": False,
                "production_preferred": False,
            }
        else:
            result = synthesize(config, load_shared_worker(config))
    except Exception as exc:
        result = {
            "generated": False,
            "ready": False,
            "reason": "blackwell_sidecar_error",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "playback": False,
            "generic_voice_used": False,
        }
    result["process_seconds"] = round(time.perf_counter() - started, 3)
    resources = sampler.stop()
    result["resources"] = resources
    if result.get("generated") is True:
        delta = resources.get("peak_sidecar_gpu_delta_mib")
        result["gpu_utilization_observed"] = bool(delta is not None and float(delta) >= 256.0)
        if result["gpu_utilization_observed"] is not True:
            result["generated"] = False
            result["reason"] = "external_gpu_utilization_not_observed"
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    gc.collect()
    return 0 if result.get("generated") is True or result.get("ready") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
