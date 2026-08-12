#!/usr/bin/env python3
"""Inactive persistent eager-CUDA Chatterbox candidate for Kira's exact voice.

The worker speaks a bounded JSON-lines protocol over inherited stdin/stdout.
It never plays audio and has no fallback path.  Torch and Chatterbox imports
occur only after an explicit ``load`` request in a process launched with the
separate model-load acceptance opt-in.
"""

from __future__ import annotations

import argparse
import contextlib
import faulthandler
import gc
import importlib.metadata
import json
import math
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
import warnings
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


SIDECAR_ROOT = Path(__file__).resolve().parent
if str(SIDECAR_ROOT) not in sys.path:
    sys.path.insert(0, str(SIDECAR_ROOT))

from candidate_contract import (  # noqa: E402
    CONFIG_PATH,
    REJECTED_RUNTIME_TEXT,
    ROOT,
    PhaseLedger,
    load_candidate_config,
    project_file,
    qwen_residency_evidence,
    safe_output_path,
    sha256_file,
    sha256_text,
    validate_envelope,
    validate_synthesis_request,
    validate_wav,
    verify_candidate_config,
    verify_identity_files,
    verify_restricted_environment,
)


def _gpu_memory_used_mib() -> float | None:
    try:
        executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "nvidia-smi.exe"
        if not executable.is_file():
            return None
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
    """Host sampler with boundary-only external GPU process queries.

    Torch's allocator counters remain the authoritative proof that model load
    and synthesis used CUDA.  Spawning ``nvidia-smi`` every 250 ms while
    Windows is importing and initializing the CUDA stack can contend with the
    very operation being measured, so the background thread samples only host
    RAM.  Total-GPU memory is captured once at each operation boundary.
    """

    def __init__(self, interval_seconds: float = 0.25) -> None:
        self._interval = max(0.1, min(1.0, float(interval_seconds)))
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name="persistent-blackwell-resource-sampler",
            daemon=True,
        )
        self.samples = 0
        self.external_gpu_samples = 0
        self.peak_process_rss_mib = 0.0
        self.peak_system_used_mib = 0.0
        self.baseline_gpu_used_mib: float | None = None
        self.peak_gpu_used_mib = 0.0
        self.errors: list[str] = []

    def _sample(self, *, include_external_gpu: bool = False) -> None:
        try:
            import psutil

            process_mib = psutil.Process().memory_info().rss / (1024 * 1024)
            memory = psutil.virtual_memory()
            self.peak_process_rss_mib = max(self.peak_process_rss_mib, process_mib)
            self.peak_system_used_mib = max(
                self.peak_system_used_mib,
                (memory.total - memory.available) / (1024 * 1024),
            )
        except Exception as exc:
            self.errors.append(f"psutil:{type(exc).__name__}:{exc}")
        self.samples += 1
        if include_external_gpu:
            gpu_mib = _gpu_memory_used_mib()
            if self.external_gpu_samples == 0:
                self.baseline_gpu_used_mib = gpu_mib
            self.external_gpu_samples += 1
            if gpu_mib is not None:
                self.peak_gpu_used_mib = max(self.peak_gpu_used_mib, gpu_mib)

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            self._sample()

    def start(self) -> None:
        self._sample(include_external_gpu=True)
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        self._thread.join(timeout=2)
        self._sample(include_external_gpu=True)
        baseline = self.baseline_gpu_used_mib
        return {
            "sample_count": self.samples,
            "host_sample_count": self.samples,
            "external_gpu_sample_count": self.external_gpu_samples,
            "gpu_sampling_mode": "boundary_only_external_nvidia_smi",
            "background_external_gpu_polling": False,
            "gpu_peak_measurement_scope": "operation_boundary_snapshots_not_continuous_peak",
            "peak_process_rss_mib": round(self.peak_process_rss_mib, 1),
            "peak_system_ram_used_mib": round(self.peak_system_used_mib, 1),
            "baseline_total_gpu_used_mib": round(baseline, 1) if baseline is not None else None,
            "peak_total_gpu_used_mib": round(self.peak_gpu_used_mib, 1) if self.peak_gpu_used_mib else None,
            "peak_total_gpu_delta_mib": (
                round(max(0.0, self.peak_gpu_used_mib - baseline), 1)
                if baseline is not None and self.peak_gpu_used_mib
                else None
            ),
            "sampling_errors": list(dict.fromkeys(self.errors))[:10],
        }


def _actual_backend_loader(ledger: PhaseLedger) -> dict[str, Any]:
    """Import the approved runtime lazily, with every cold phase separated."""

    with ledger.phase("imports.torch"):
        import torch
    with ledger.phase("imports.torchaudio"):
        import torchaudio
    with ledger.phase("imports.transformers_compatibility"):
        from transformers import GPT2Config, GPT2Model, LlamaConfig, LlamaModel
    with ledger.phase("imports.numpy"):
        import numpy as np
    with ledger.phase("imports.soundfile"):
        import soundfile as sf
    with ledger.phase("imports.chatterbox"):
        from chatterbox.tts import ChatterboxTTS

    core = ROOT / "Core"
    if str(core) not in sys.path:
        sys.path.insert(0, str(core))
    with ledger.phase("imports.dialogue_contracts"):
        from dialogue_audio_signal import assess_generated_speech_chunk, gentle_proximity_correction
        from dialogue_tts import split_for_tts, spoken_words

    return {
        "torch": torch,
        "torchaudio": torchaudio,
        "numpy": np,
        "soundfile": sf,
        "model_factory": ChatterboxTTS.from_pretrained,
        "assess_generated_speech_chunk": assess_generated_speech_chunk,
        "gentle_proximity_correction": gentle_proximity_correction,
        "split_for_tts": split_for_tts,
        "spoken_words": spoken_words,
        "transformers_compatibility_imports": {
            "LlamaModel": LlamaModel.__module__,
            "LlamaConfig": LlamaConfig.__module__,
            "GPT2Model": GPT2Model.__module__,
            "GPT2Config": GPT2Config.__module__,
        },
    }


def _verify_runtime_metadata(config: dict[str, Any]) -> dict[str, str]:
    if tuple(sys.version_info[:3]) != (3, 11, 9):
        raise ValueError("persistent candidate runtime requires exact Python 3.11.9")
    versions = {
        "chatterbox-tts": importlib.metadata.version("chatterbox-tts"),
        "torch": importlib.metadata.version("torch"),
        "torchaudio": importlib.metadata.version("torchaudio"),
    }
    expected = {
        "chatterbox-tts": config["chatterbox_version"],
        "torch": config["torch_version"],
        "torchaudio": config["torchaudio_version"],
    }
    if versions != expected:
        raise ValueError(f"persistent candidate dependency mismatch: {versions}")
    return versions


MODEL_ALLOCATION_FLOOR_BYTES = 256 * 1024 * 1024
REQUIRED_CUDA_MODEL_COMPONENTS = ("t3", "s3gen", "ve")


@contextlib.contextmanager
def _load_stack_dump_watchdog(config: dict[str, Any]) -> Any:
    """Emit bounded repeated Python stack snapshots while a load request is active."""

    diagnostics = config["diagnostics"]
    interval = float(diagnostics["faulthandler_dump_interval_seconds"])
    repeat = diagnostics["faulthandler_repeat"] is True
    previously_enabled = faulthandler.is_enabled()
    if not previously_enabled:
        faulthandler.enable(file=sys.stderr, all_threads=True)
    faulthandler.dump_traceback_later(
        interval,
        repeat=repeat,
        file=sys.stderr,
        exit=False,
    )
    try:
        yield
    finally:
        faulthandler.cancel_dump_traceback_later()
        if not previously_enabled:
            faulthandler.disable()


def _device_type(value: Any) -> str:
    """Return a normalized device type without importing Torch at module load."""

    if value is None:
        return ""
    direct = getattr(value, "type", None)
    if direct:
        return str(direct).strip().casefold()
    text = str(value).strip().casefold()
    return text.split(":", 1)[0] if text else ""


def _module_cuda_evidence(module: Any) -> dict[str, Any]:
    """Inspect every exposed parameter/buffer device without moving the module."""

    observed: set[str] = set()
    parameter_count = 0
    buffer_count = 0
    for provider_name in ("parameters", "buffers"):
        provider = getattr(module, provider_name, None)
        if not callable(provider):
            continue
        try:
            values = provider()
        except TypeError:
            values = provider(recurse=True)
        for value in values:
            device_type = _device_type(getattr(value, "device", None))
            if device_type:
                observed.add(device_type)
            if provider_name == "parameters":
                parameter_count += 1
            else:
                buffer_count += 1
    return {
        "present": module is not None,
        "parameter_count": parameter_count,
        "buffer_count": buffer_count,
        "observed_tensor_count": parameter_count + buffer_count,
        "observed_device_types": sorted(observed),
        "all_observed_tensors_cuda": bool(observed) and observed == {"cuda"},
    }


def _model_cuda_residency_evidence(model: Any) -> dict[str, Any]:
    model_device_type = _device_type(getattr(model, "device", None))
    components = {
        name: _module_cuda_evidence(getattr(model, name, None))
        for name in REQUIRED_CUDA_MODEL_COMPONENTS
    }
    all_components_cuda = all(
        evidence.get("present") is True
        and evidence.get("observed_tensor_count", 0) > 0
        and evidence.get("all_observed_tensors_cuda") is True
        for evidence in components.values()
    )
    return {
        "model_device_type": model_device_type,
        "required_core_components": list(REQUIRED_CUDA_MODEL_COMPONENTS),
        "core_components": components,
        "model_device_cuda": model_device_type == "cuda",
        "all_core_components_cuda": all_components_cuda,
        "model_and_core_components_cuda": model_device_type == "cuda" and all_components_cuda,
    }


def _qwen_absence_proven(evidence: Any) -> bool:
    return bool(
        isinstance(evidence, dict)
        and evidence.get("query_succeeded") is True
        and evidence.get("qwen_absent_proven") is True
        and not evidence.get("qwen_records")
        and evidence.get("model_state_changed") is False
    )


def _accepted_generation_attempts(chunk_checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    for chunk in chunk_checks:
        accepted_number = chunk.get("accepted_attempt")
        attempts = chunk.get("attempts")
        if not isinstance(attempts, list):
            return []
        match = next(
            (
                attempt
                for attempt in attempts
                if isinstance(attempt, dict)
                and attempt.get("attempt") == accepted_number
                and attempt.get("passed") is True
            ),
            None,
        )
        if match is None:
            return []
        accepted.append(match)
    return accepted


def _synthesis_cuda_execution_evidence(
    *,
    model_residency: dict[str, Any],
    chunk_checks: list[dict[str, Any]],
    allocated_before: int,
    peak_allocated: int,
    synchronize_before_succeeded: bool,
    synchronize_after_succeeded: bool,
) -> dict[str, Any]:
    """Separate CUDA execution proof from Chatterbox's documented CPU return."""

    accepted = _accepted_generation_attempts(chunk_checks)
    complete_accepted_set = len(accepted) == len(chunk_checks) and bool(chunk_checks)
    official_host_return = complete_accepted_set and all(
        attempt.get("official_host_return_contract_satisfied") is True
        and attempt.get("output_tensor_returned_to_host") is True
        and attempt.get("output_tensor_was_cuda") is False
        for attempt in accepted
    )
    qwen_absent = complete_accepted_set and all(
        _qwen_absence_proven(attempt.get("qwen_residency")) for attempt in accepted
    )
    no_rejected_warnings = complete_accepted_set and all(
        not attempt.get("rejected_warning_matches") for attempt in accepted
    )
    persistent_allocation = allocated_before >= MODEL_ALLOCATION_FLOOR_BYTES
    peak_exceeded_baseline = peak_allocated > allocated_before
    actual_gpu_execution = all(
        (
            model_residency.get("model_and_core_components_cuda") is True,
            synchronize_before_succeeded,
            synchronize_after_succeeded,
            persistent_allocation,
            peak_exceeded_baseline,
            no_rejected_warnings,
            qwen_absent,
            official_host_return,
        )
    )
    return {
        "model_residency": model_residency,
        "model_and_core_components_cuda": (
            model_residency.get("model_and_core_components_cuda") is True
        ),
        "cuda_synchronize_before_generation_succeeded": synchronize_before_succeeded,
        "cuda_synchronize_after_generation_succeeded": synchronize_after_succeeded,
        "allocated_before_bytes": allocated_before,
        "peak_allocated_bytes": peak_allocated,
        "generation_peak_delta_bytes": peak_allocated - allocated_before,
        "persistent_model_allocation_present": persistent_allocation,
        "generation_peak_exceeded_baseline": peak_exceeded_baseline,
        "no_rejected_runtime_warnings": no_rejected_warnings,
        "qwen_absence_proven_for_accepted_generation": qwen_absent,
        "official_host_return_contract_satisfied": official_host_return,
        "accepted_output_tensors_host_cpu": official_host_return,
        "accepted_output_tensors_cuda": False,
        "actual_gpu_execution": actual_gpu_execution,
    }


class PersistentVoiceRuntime:
    """One persistent model and one immutable approved-reference conditioning."""

    def __init__(
        self,
        config: dict[str, Any],
        *,
        backend_loader: Callable[[PhaseLedger], dict[str, Any]] | None = None,
        qwen_probe: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        identity_verifier: Callable[[dict[str, Any]], dict[str, str]] | None = None,
        environment_verifier: Callable[..., dict[str, str]] | None = None,
        runtime_metadata_verifier: Callable[[dict[str, Any]], dict[str, str]] | None = None,
        resource_sampler_factory: Callable[[], ResourceSampler] | None = None,
    ) -> None:
        self.config = config
        self._backend_loader = backend_loader or _actual_backend_loader
        self._qwen_probe = qwen_probe or qwen_residency_evidence
        self._identity_verifier = identity_verifier or verify_identity_files
        self._environment_verifier = environment_verifier or verify_restricted_environment
        self._runtime_metadata_verifier = runtime_metadata_verifier or _verify_runtime_metadata
        self._resource_sampler_factory = resource_sampler_factory or ResourceSampler
        self.backend: dict[str, Any] | None = None
        self.model: Any | None = None
        self.sample_rate: int | None = None
        self.conditioned_reference_sha256: str | None = None
        self.model_load_count = 0
        self.reference_conditioning_count = 0
        self.successful_synthesis_count = 0
        self.generation_attempt_count = 0
        self.unload_count = 0
        self.load_gpu_proof: dict[str, Any] | None = None
        self.last_activity_monotonic = time.monotonic()
        self.last_unload: dict[str, Any] | None = None

    @property
    def loaded(self) -> bool:
        return self.model is not None and self.backend is not None

    def lifecycle(self) -> dict[str, Any]:
        return {
            "model_loaded": self.loaded,
            "model_load_count": self.model_load_count,
            "reference_conditioning_count": self.reference_conditioning_count,
            "successful_synthesis_count": self.successful_synthesis_count,
            "generation_attempt_count": self.generation_attempt_count,
            "unload_count": self.unload_count,
            "conditioned_reference_sha256": self.conditioned_reference_sha256,
            "last_unload": self.last_unload,
        }

    def _cuda_checks(self, backend: dict[str, Any]) -> dict[str, Any]:
        torch = backend["torch"]
        torchaudio = backend["torchaudio"]
        available = bool(torch.cuda.is_available())
        checks = {
            "torch_runtime": str(torch.__version__) == self.config["torch_version"],
            "torchaudio_runtime": str(torchaudio.__version__) == self.config["torchaudio_version"],
            "cuda_runtime": str(torch.version.cuda) == self.config["cuda_runtime"],
            "cuda_available": available,
            "device": (
                str(torch.cuda.get_device_name(0)) == self.config["required_device_name"]
                if available
                else False
            ),
            "capability": (
                list(torch.cuda.get_device_capability(0)) == self.config["required_device_capability"]
                if available
                else False
            ),
            "sm_120": (
                self.config["required_compiled_architecture"] in torch.cuda.get_arch_list()
                if available
                else False
            ),
        }
        if not all(checks.values()):
            raise ValueError(f"persistent Blackwell CUDA readiness mismatch: {checks}")
        return checks

    def load(
        self,
        *,
        phase_event_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        ledger = PhaseLedger(event_callback=phase_event_callback)
        started = time.perf_counter()
        if self.loaded:
            self.last_activity_monotonic = time.monotonic()
            return {
                "ready": True,
                "reason": "already_loaded",
                "model_reused": True,
                "gpu_proof": dict(self.load_gpu_proof or {}),
                "phase_timings": ledger.records,
                "lifecycle": self.lifecycle(),
            }
        sampler: ResourceSampler | None = None
        captured_warnings: list[str] = []
        backend: dict[str, Any] | None = None
        model: Any | None = None
        try:
            with ledger.phase("load.restricted_environment"):
                cache_paths = self._environment_verifier(self.config, require_load_opt_in=True)
            with ledger.phase("load.runtime_dependency_metadata"):
                runtime_versions = self._runtime_metadata_verifier(self.config)
            with ledger.phase("load.approved_identity_hashes"):
                identity = self._identity_verifier(self.config)
            with ledger.phase("load.qwen_absence"):
                qwen = self._qwen_probe(self.config)
                if not _qwen_absence_proven(qwen):
                    raise RuntimeError("Qwen absence was not proven before persistent GPU model load")
            sampler = self._resource_sampler_factory()
            sampler.start()
            backend = self._backend_loader(ledger)
            with ledger.phase("load.cuda_contract"):
                cuda_checks = self._cuda_checks(backend)
            torch = backend["torch"]
            cuda_synchronize_before_succeeded = False
            cuda_synchronize_after_succeeded = False
            with ledger.phase("load.cuda_prepare"):
                torch.cuda.synchronize(0)
                cuda_synchronize_before_succeeded = True
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats(0)
                allocated_before = int(torch.cuda.memory_allocated(0))
                reserved_before = int(torch.cuda.memory_reserved(0))
                free_before, total_before = torch.cuda.mem_get_info(0)
            with warnings.catch_warnings(record=True) as caught, contextlib.redirect_stdout(sys.stderr):
                warnings.simplefilter("always")
                with ledger.phase("load.model_from_pretrained"):
                    model = backend["model_factory"]("cuda")
                with ledger.phase("load.reference_prepare_conditionals"):
                    model.prepare_conditionals(str(project_file(self.config["approved_reference"])))
                captured_warnings = [str(item.message) for item in caught]
            with ledger.phase("load.cuda_synchronize_after_conditioning"):
                torch.cuda.synchronize(0)
                cuda_synchronize_after_succeeded = True
                allocated_after = int(torch.cuda.memory_allocated(0))
                reserved_after = int(torch.cuda.memory_reserved(0))
                peak_allocated = int(torch.cuda.max_memory_allocated(0))
                peak_reserved = int(torch.cuda.max_memory_reserved(0))
                free_after, total_after = torch.cuda.mem_get_info(0)
            warning_text = "\n".join(captured_warnings).casefold()
            rejected = [value for value in REJECTED_RUNTIME_TEXT if value in warning_text]
            if rejected:
                raise RuntimeError(f"rejected Blackwell runtime warning: {rejected}")
            model_residency = _model_cuda_residency_evidence(model)
            if model_residency.get("model_and_core_components_cuda") is not True:
                raise RuntimeError(
                    f"persistent Chatterbox model/core CUDA residency was not proven: {model_residency}"
                )
            if (
                allocated_after < MODEL_ALLOCATION_FLOOR_BYTES
                or peak_allocated < MODEL_ALLOCATION_FLOOR_BYTES
            ):
                raise RuntimeError("persistent Chatterbox model did not prove GPU allocation")
            self.backend = backend
            self.model = model
            self.sample_rate = int(model.sr)
            self.conditioned_reference_sha256 = identity["reference_sha256"]
            self.model_load_count += 1
            self.reference_conditioning_count += 1
            self.last_activity_monotonic = time.monotonic()
            gpu_proof = {
                "allocated_before_bytes": allocated_before,
                "allocated_after_bytes": allocated_after,
                "allocated_delta_bytes": allocated_after - allocated_before,
                "reserved_before_bytes": reserved_before,
                "reserved_after_bytes": reserved_after,
                "reserved_delta_bytes": reserved_after - reserved_before,
                "peak_allocated_bytes": peak_allocated,
                "peak_reserved_bytes": peak_reserved,
                "free_before_bytes": int(free_before),
                "free_after_bytes": int(free_after),
                "total_before_bytes": int(total_before),
                "total_after_bytes": int(total_after),
                "actual_gpu_allocation": True,
                "persistent_model_allocation_present": (
                    allocated_after >= MODEL_ALLOCATION_FLOOR_BYTES
                ),
                "cuda_synchronize_before_model_load_succeeded": (
                    cuda_synchronize_before_succeeded
                ),
                "cuda_synchronize_after_conditioning_succeeded": (
                    cuda_synchronize_after_succeeded
                ),
                "model_residency": model_residency,
                "model_and_core_components_cuda": (
                    model_residency.get("model_and_core_components_cuda") is True
                ),
                "captured_warnings": captured_warnings,
                "rejected_warning_matches": rejected,
                "no_rejected_runtime_warnings": not rejected,
            }
            self.load_gpu_proof = dict(gpu_proof)
            return {
                "ready": True,
                "reason": "persistent_model_loaded_and_reference_conditioned",
                "model_reused": False,
                "identity": identity,
                "qwen_residency": qwen,
                "cache_paths": cache_paths,
                "runtime_cuda_checks": cuda_checks,
                "runtime_versions": runtime_versions,
                "gpu_proof": gpu_proof,
                "transformers_compatibility_imports": backend.get(
                    "transformers_compatibility_imports", {}
                ),
                "phase_timings": ledger.records,
                "operation_seconds": round(time.perf_counter() - started, 6),
                "resources": sampler.stop(),
                "lifecycle": self.lifecycle(),
            }
        except Exception:
            with ledger.phase("load.failure_cleanup"):
                cleanup_torch = backend.get("torch") if backend else None
                model = None
                self._discard_partial_load()
                if cleanup_torch is not None and cleanup_torch.cuda.is_available():
                    cleanup_torch.cuda.empty_cache()
                    cleanup_torch.cuda.synchronize(0)
            resources = sampler.stop() if sampler is not None else {
                "sample_count": 0,
                "sampling_skipped_before_model_load": True,
            }
            exc = sys.exc_info()[1]
            return {
                "ready": False,
                "reason": "persistent_model_load_failed",
                "error_type": type(exc).__name__ if exc is not None else "UnknownError",
                "error": str(exc),
                "traceback": traceback.format_exc()[-12000:],
                "captured_warnings": captured_warnings,
                "phase_timings": ledger.records,
                "operation_seconds": round(time.perf_counter() - started, 6),
                "resources": resources,
                "lifecycle": self.lifecycle(),
            }

    def _discard_partial_load(self) -> None:
        self.model = None
        self.backend = None
        self.sample_rate = None
        self.conditioned_reference_sha256 = None
        self.load_gpu_proof = None
        gc.collect()

    def _generate_chunk(
        self,
        chunk: str,
        *,
        chunk_index: int,
        ledger: PhaseLedger,
    ) -> tuple[Any, dict[str, Any]]:
        if not self.loaded or self.backend is None or self.model is None or self.sample_rate is None:
            raise RuntimeError("persistent Chatterbox model is not loaded")
        torch = self.backend["torch"]
        np = self.backend["numpy"]
        assess = self.backend["assess_generated_speech_chunk"]
        spoken_words = self.backend["spoken_words"]
        generation = self.config["generation"]
        max_attempts = int(self.config["bounds"]["max_generation_attempts_per_chunk"])
        attempts: list[dict[str, Any]] = []
        accepted = None
        for attempt in range(1, max_attempts + 1):
            with ledger.phase(
                f"synthesis.chunk_{chunk_index:02d}.attempt_{attempt:02d}.qwen_absence"
            ):
                qwen = self._qwen_probe(self.config)
                if not _qwen_absence_proven(qwen):
                    raise RuntimeError("Qwen absence was not proven immediately before GPU generation")
            caught_messages: list[str] = []
            with warnings.catch_warnings(record=True) as caught, contextlib.redirect_stdout(sys.stderr):
                warnings.simplefilter("always")
                with ledger.phase(
                    f"synthesis.chunk_{chunk_index:02d}.attempt_{attempt:02d}.model_generate"
                ):
                    wav = self.model.generate(
                        chunk,
                        repetition_penalty=float(generation["repetition_penalty"]),
                        min_p=float(generation["min_p"]),
                        top_p=float(generation["top_p"]),
                        exaggeration=float(generation["exaggeration"]),
                        cfg_weight=float(generation["cfg_weight"]),
                        temperature=float(generation["temperature"]),
                    )
                caught_messages = [str(item.message) for item in caught]
            self.generation_attempt_count += 1
            warning_text = "\n".join(caught_messages).casefold()
            rejected = [value for value in REJECTED_RUNTIME_TEXT if value in warning_text]
            if rejected:
                raise RuntimeError(f"rejected Blackwell runtime warning: {rejected}")
            device_type = str(getattr(getattr(wav, "device", None), "type", ""))
            host_contract = self.config["official_chatterbox_host_return_contract"]
            output_tensor_returned_to_host = device_type == "cpu"
            official_host_return_contract_satisfied = bool(
                host_contract.get("host_return_expected") is True
                and host_contract.get("public_generate_return_device") == "cpu"
                and output_tensor_returned_to_host
            )
            with ledger.phase(
                f"synthesis.chunk_{chunk_index:02d}.attempt_{attempt:02d}.cuda_to_host"
            ):
                value = wav.squeeze() if hasattr(wav, "squeeze") else wav
                value = value.detach() if hasattr(value, "detach") else value
                value = value.cpu() if hasattr(value, "cpu") else value
                value = value.numpy() if hasattr(value, "numpy") else value
                samples = np.asarray(value, dtype=np.float32).reshape(-1)
            with ledger.phase(
                f"synthesis.chunk_{chunk_index:02d}.attempt_{attempt:02d}.signal_validation"
            ):
                check = assess(
                    samples,
                    sample_rate=self.sample_rate,
                    queued_word_count=len(spoken_words(chunk)),
                )
            check.update(
                {
                    "chunk_index": chunk_index,
                    "attempt": attempt,
                    "output_tensor_device_type": device_type,
                    "output_tensor_was_cuda": device_type == "cuda",
                    "output_tensor_returned_to_host": output_tensor_returned_to_host,
                    "official_host_return_contract_satisfied": (
                        official_host_return_contract_satisfied
                    ),
                    "captured_warnings": caught_messages,
                    "rejected_warning_matches": rejected,
                    "qwen_residency": qwen,
                }
            )
            attempts.append(check)
            if (
                check.get("passed") is True
                and check["official_host_return_contract_satisfied"] is True
            ):
                accepted = samples
                break
        if accepted is None:
            raise RuntimeError("persistent_chatterbox_signal_or_official_host_return_validation_failed")
        return accepted, {"attempts": attempts, "accepted_attempt": attempts[-1]["attempt"]}

    def _postprocess(self, samples: Any, calibration: dict[str, float]) -> tuple[Any, dict[str, Any]]:
        if self.backend is None or self.sample_rate is None:
            raise RuntimeError("persistent Chatterbox backend is not loaded")
        np = self.backend["numpy"]
        proximity = self.backend["gentle_proximity_correction"]
        arr = np.asarray(samples, dtype=np.float32).reshape(-1)
        gain_db = float(calibration["pcm_output_gain_db"])
        cutoff_hz = float(calibration["proximity_cut_hz"])
        cut_mix = float(calibration["proximity_cut_mix"])
        if cutoff_hz >= self.sample_rate / 2.0:
            raise ValueError("proximity cutoff must remain below output Nyquist")
        pre_rms = float(np.sqrt(np.mean(np.square(arr, dtype=np.float64)))) if arr.size else 0.0
        pre_peak = float(np.max(np.abs(arr))) if arr.size else 0.0
        corrected = proximity(
            arr,
            sample_rate=self.sample_rate,
            cutoff_hz=cutoff_hz,
            mix=cut_mix,
        )
        scaled = corrected * math.pow(10.0, gain_db / 20.0)
        clipped_count = int(np.count_nonzero(np.abs(scaled) > 0.98))
        processed = np.clip(scaled, -0.98, 0.98).astype(np.float32, copy=False)
        post_rms = float(np.sqrt(np.mean(np.square(processed, dtype=np.float64)))) if processed.size else 0.0
        post_peak = float(np.max(np.abs(processed))) if processed.size else 0.0
        return processed, {
            "applied": bool(gain_db != 0.0 or (cutoff_hz != 0.0 and cut_mix != 0.0)),
            "application_count": 1,
            "gain_db": gain_db,
            "proximity_cut_hz": cutoff_hz,
            "proximity_cut_mix": cut_mix,
            "pre_rms": round(pre_rms, 8),
            "pre_peak": round(pre_peak, 8),
            "post_rms": round(post_rms, 8),
            "post_peak": round(post_peak, 8),
            "clipped_sample_count": clipped_count,
            "pitch_changed": False,
        }

    def synthesize(self, request: dict[str, Any]) -> dict[str, Any]:
        ledger = PhaseLedger()
        started = time.perf_counter()
        if not self.loaded or self.backend is None or self.model is None or self.sample_rate is None:
            return {
                "generated": False,
                "reason": "persistent_model_not_loaded_explicit_load_required",
                "phase_timings": ledger.records,
                "lifecycle": self.lifecycle(),
            }
        sampler = self._resource_sampler_factory()
        sampler.start()
        target = Path(request["target"])
        partial = target.with_name(f".{target.stem}.{request['request_id']}.part.wav")
        chunks: list[str] = []
        chunk_manifest: dict[str, Any] = {}
        chunk_checks: list[dict[str, Any]] = []
        processed_chunks: list[Any] = []
        postprocess_checks: list[dict[str, Any]] = []
        target_promoted = False
        torch = self.backend["torch"]
        np = self.backend["numpy"]
        sf = self.backend["soundfile"]
        try:
            with ledger.phase("synthesis.approved_identity_hashes"):
                identity = self._identity_verifier(self.config)
                if identity["reference_sha256"] != self.conditioned_reference_sha256:
                    raise RuntimeError("conditioned reference no longer matches approved reference")
            with ledger.phase("synthesis.restricted_environment"):
                cache_paths = self._environment_verifier(self.config, require_load_opt_in=True)
            with ledger.phase("synthesis.chunking"):
                chunks, chunk_manifest = self.backend["split_for_tts"](
                    request["text"],
                    max_chars=int(self.config["bounds"]["max_chunk_characters"]),
                )
                if len(chunks) > int(self.config["bounds"]["max_chunks_per_request"]):
                    raise ValueError("persistent candidate request exceeds maximum chunk count")
            target.parent.mkdir(parents=True, exist_ok=True)
            partial.unlink(missing_ok=True)
            if target.exists():
                raise FileExistsError("persistent candidate refuses to overwrite an existing WAV")
            model_residency = _model_cuda_residency_evidence(self.model)
            if model_residency.get("model_and_core_components_cuda") is not True:
                raise RuntimeError(
                    f"persistent Chatterbox model/core CUDA residency was lost: {model_residency}"
                )
            cuda_synchronize_before_succeeded = False
            cuda_synchronize_after_succeeded = False
            with ledger.phase("synthesis.cuda_prepare"):
                torch.cuda.synchronize(0)
                cuda_synchronize_before_succeeded = True
                torch.cuda.reset_peak_memory_stats(0)
                allocated_before = int(torch.cuda.memory_allocated(0))
                reserved_before = int(torch.cuda.memory_reserved(0))
                free_before, total_before = torch.cuda.mem_get_info(0)
            for index, chunk in enumerate(chunks):
                accepted, check = self._generate_chunk(chunk, chunk_index=index, ledger=ledger)
                chunk_checks.append({"chunk_index": index, **check})
                with ledger.phase(f"synthesis.chunk_{index:02d}.pcm_postprocess"):
                    processed, postprocess = self._postprocess(accepted, request["calibration"])
                postprocess["chunk_index"] = index
                processed_chunks.append(processed)
                postprocess_checks.append(postprocess)
            with ledger.phase("synthesis.cuda_synchronize_after_generation"):
                torch.cuda.synchronize(0)
                cuda_synchronize_after_succeeded = True
                allocated_after = int(torch.cuda.memory_allocated(0))
                reserved_after = int(torch.cuda.memory_reserved(0))
                peak_allocated = int(torch.cuda.max_memory_allocated(0))
                peak_reserved = int(torch.cuda.max_memory_reserved(0))
                free_after, total_after = torch.cuda.mem_get_info(0)
            gpu_proof = _synthesis_cuda_execution_evidence(
                model_residency=model_residency,
                chunk_checks=chunk_checks,
                allocated_before=allocated_before,
                peak_allocated=peak_allocated,
                synchronize_before_succeeded=cuda_synchronize_before_succeeded,
                synchronize_after_succeeded=cuda_synchronize_after_succeeded,
            )
            if gpu_proof.get("actual_gpu_execution") is not True:
                raise RuntimeError(
                    f"persistent candidate did not prove eager-CUDA inference: {gpu_proof}"
                )
            with ledger.phase("synthesis.wav_write_partial"):
                with sf.SoundFile(
                    str(partial),
                    mode="w",
                    samplerate=self.sample_rate,
                    channels=1,
                    subtype="PCM_16",
                    format="WAV",
                ) as output:
                    for index, processed in enumerate(processed_chunks):
                        output.write(processed)
                        if index < len(processed_chunks) - 1:
                            output.write(
                                np.zeros(max(1, int(self.sample_rate * 0.06)), dtype=np.float32)
                            )
            with ledger.phase("synthesis.wav_validate_partial"):
                partial_validation = validate_wav(partial)
                if partial_validation.get("passed") is not True:
                    raise RuntimeError("persistent candidate WAV validation failed")
            with ledger.phase("synthesis.wav_atomic_promote"):
                if target.exists():
                    raise FileExistsError("persistent candidate target appeared before atomic promote")
                partial.replace(target)
                target_promoted = True
            with ledger.phase("synthesis.wav_validate_and_hash_final"):
                wav = validate_wav(target)
                if wav.get("passed") is not True:
                    raise RuntimeError("persistent candidate final WAV validation failed")
            self.successful_synthesis_count += 1
            self.last_activity_monotonic = time.monotonic()
            resources = sampler.stop()
            return {
                "generated": True,
                "reason": "ok",
                "engine": "chatterbox_tts",
                "candidate_id": self.config["candidate_id"],
                "request_id": request["request_id"],
                "channel": self.config["input_channel"],
                "text_sha256": sha256_text(request["text"]),
                "text_characters": len(request["text"]),
                "requested_public_words": self.backend["spoken_words"](request["text"]),
                "requested_text_bound": True,
                "profile_sha256": identity["profile_sha256"],
                "reference_relative": self.config["approved_reference"],
                "reference_sha256": identity["reference_sha256"],
                "conditioning_reused": True,
                "voice_identity_status": "reviewed_reference_chatterbox",
                "generic_voice_used": False,
                "sapi_voice_used": False,
                "fallback_used": False,
                "playback": False,
                "device": "cuda",
                "generation_seconds": round(time.perf_counter() - started, 6),
                "audio_path": str(target.resolve()),
                "audio_relative": target.resolve().relative_to(ROOT.resolve()).as_posix(),
                "wav_validation": wav,
                "partial_wav_validation": partial_validation,
                "chunks": chunk_manifest,
                "chunk_checks": chunk_checks,
                "audio_postprocess": {
                    "applied": any(item.get("applied") for item in postprocess_checks),
                    "application_count_per_chunk": 1,
                    "chunks": postprocess_checks,
                },
                "cache_paths": cache_paths,
                "gpu_proof": {
                    **gpu_proof,
                    "allocated_before_bytes": allocated_before,
                    "allocated_after_bytes": allocated_after,
                    "peak_allocated_bytes": peak_allocated,
                    "reserved_before_bytes": reserved_before,
                    "reserved_after_bytes": reserved_after,
                    "peak_reserved_bytes": peak_reserved,
                    "free_before_bytes": int(free_before),
                    "free_after_bytes": int(free_after),
                    "total_before_bytes": int(total_before),
                    "total_after_bytes": int(total_after),
                },
                "phase_timings": ledger.records,
                "operation_seconds": round(time.perf_counter() - started, 6),
                "resources": resources,
                "lifecycle": self.lifecycle(),
            }
        except Exception as exc:
            if target_promoted:
                target.unlink(missing_ok=True)
            resources = sampler.stop()
            failure_unload = self.unload(reason="synthesis_failure") if self.loaded else None
            return {
                "generated": False,
                "reason": "persistent_synthesis_failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc()[-12000:],
                "request_id": request.get("request_id"),
                "generic_voice_used": False,
                "sapi_voice_used": False,
                "fallback_used": False,
                "playback": False,
                "phase_timings": ledger.records,
                "operation_seconds": round(time.perf_counter() - started, 6),
                "resources": resources,
                "failure_unload": failure_unload,
                "lifecycle": self.lifecycle(),
            }
        finally:
            try:
                partial.unlink(missing_ok=True)
            except OSError:
                pass

    def unload(self, *, reason: str) -> dict[str, Any]:
        ledger = PhaseLedger()
        started = time.perf_counter()
        was_loaded = self.loaded
        torch = self.backend.get("torch") if self.backend else None
        allocated_before: int | None = None
        reserved_before: int | None = None
        allocated_after: int | None = None
        reserved_after: int | None = None
        with ledger.phase("unload.model_release_and_gc"):
            if torch is not None and torch.cuda.is_available():
                torch.cuda.synchronize(0)
                allocated_before = int(torch.cuda.memory_allocated(0))
                reserved_before = int(torch.cuda.memory_reserved(0))
            self.model = None
            self.sample_rate = None
            self.conditioned_reference_sha256 = None
            self.load_gpu_proof = None
            gc.collect()
        if torch is not None and torch.cuda.is_available():
            with ledger.phase("unload.cuda_empty_cache_and_synchronize"):
                torch.cuda.empty_cache()
                torch.cuda.synchronize(0)
                allocated_after = int(torch.cuda.memory_allocated(0))
                reserved_after = int(torch.cuda.memory_reserved(0))
        self.backend = None
        if was_loaded:
            self.unload_count += 1
        self.last_activity_monotonic = time.monotonic()
        self.last_unload = {
            "reason": reason,
            "was_loaded": was_loaded,
            "allocated_before_bytes": allocated_before,
            "allocated_after_bytes": allocated_after,
            "allocated_returned_bytes": (
                max(0, allocated_before - allocated_after)
                if allocated_before is not None and allocated_after is not None
                else None
            ),
            "reserved_before_bytes": reserved_before,
            "reserved_after_bytes": reserved_after,
            "reserved_returned_bytes": (
                max(0, reserved_before - reserved_after)
                if reserved_before is not None and reserved_after is not None
                else None
            ),
            "operation_seconds": round(time.perf_counter() - started, 6),
            "phase_timings": ledger.records,
        }
        return {
            "unloaded": True,
            "reason": reason,
            "model_was_loaded": was_loaded,
            "phase_timings": ledger.records,
            "operation_seconds": round(time.perf_counter() - started, 6),
            "lifecycle": self.lifecycle(),
        }


class PersistentWorkerHost:
    def __init__(
        self,
        config: dict[str, Any],
        session_nonce: str,
        startup_phase_timings: list[dict[str, Any]] | None = None,
        event_emitter: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.config = config
        self.session_nonce = session_nonce
        self.session_id = sha256_text(session_nonce)[:24]
        self.seen_request_ids: set[str] = set()
        self.request_count = 0
        self.runtime = PersistentVoiceRuntime(config)
        self.started_monotonic = time.monotonic()
        self.shutdown_requested = False
        self.startup_phase_timings = list(startup_phase_timings or [])
        self._event_emitter = event_emitter
        self._phase_event_sequence = 0

    def base_response(self, request_id: str | None = None) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "candidate_id": self.config["candidate_id"],
            "candidate_status": self.config["candidate_status"],
            "production_routing_authorized": False,
            "session_id": self.session_id,
            "request_id": request_id,
            "playback": False,
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
        }

    def hello(self) -> dict[str, Any]:
        return {
            **self.base_response(),
            "message_type": "hello",
            "ready": True,
            "reason": "persistent_candidate_protocol_ready_model_unloaded",
            "model_loaded": False,
            "worker_sha256": sha256_file(Path(__file__)),
            "config_sha256": sha256_file(CONFIG_PATH),
            "startup_phase_timings": self.startup_phase_timings,
            "lifecycle": self.runtime.lifecycle(),
        }

    def emit_operation_phase_event(
        self,
        *,
        request_id: str,
        operation: str,
        phase_event: dict[str, Any],
    ) -> None:
        if self._event_emitter is None:
            return
        self._phase_event_sequence += 1
        self._event_emitter(
            {
                **self.base_response(request_id),
                "message_type": "event",
                "event": "operation_phase_progress",
                "event_sequence": self._phase_event_sequence,
                "operation": operation,
                "phase_progress": dict(phase_event),
            }
        )

    def process(self, raw: Any) -> dict[str, Any]:
        request_id = str(raw.get("request_id") or "") if isinstance(raw, dict) else None
        try:
            self.request_count += 1
            if self.request_count > int(self.config["bounds"]["max_requests_per_process"]):
                if self.runtime.loaded:
                    self.runtime.unload(reason="request_limit")
                self.shutdown_requested = True
                raise RuntimeError("persistent candidate process request limit reached")
            request = validate_envelope(
                raw,
                config=self.config,
                session_nonce=self.session_nonce,
                seen_request_ids=self.seen_request_ids,
            )
            operation = request["operation"]
            if operation == "status":
                result: dict[str, Any] = {
                    "ready": True,
                    "reason": "status",
                    "lifecycle": self.runtime.lifecycle(),
                }
            elif operation == "load":
                callback = lambda event: self.emit_operation_phase_event(
                    request_id=request["request_id"],
                    operation=operation,
                    phase_event=event,
                )
                with _load_stack_dump_watchdog(self.config):
                    result = self.runtime.load(phase_event_callback=callback)
            elif operation == "synthesize":
                validated = validate_synthesis_request(request, self.config)
                result = self.runtime.synthesize(validated)
            elif operation == "unload":
                result = self.runtime.unload(reason="explicit_request")
            elif operation == "shutdown":
                result = self.runtime.unload(reason="explicit_shutdown")
                result["shutdown"] = True
                self.shutdown_requested = True
            else:  # pragma: no cover - validate_envelope rejects this.
                raise ValueError("unsupported operation")
            return {
                **self.base_response(request["request_id"]),
                "message_type": "response",
                "operation": operation,
                **result,
            }
        except Exception as exc:
            return {
                **self.base_response(request_id),
                "message_type": "response",
                "operation": str(raw.get("operation") or "") if isinstance(raw, dict) else "",
                "ready": False,
                "generated": False,
                "reason": "persistent_candidate_request_rejected",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "lifecycle": self.runtime.lifecycle(),
            }


def _emit(payload: dict[str, Any], max_bytes: int, *, output: Any | None = None) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    if len(encoded) > max_bytes:
        encoded = json.dumps(
            {
                "schema_version": 1,
                "message_type": "fatal",
                "reason": "persistent_candidate_response_oversized",
                "playback": False,
                "generic_voice_used": False,
                "sapi_voice_used": False,
                "fallback_used": False,
            },
            sort_keys=True,
        ).encode("utf-8")
    stream = output if output is not None else sys.stdout.buffer
    stream.write(encoded + b"\n")
    stream.flush()


def _stdin_reader(output: queue.Queue[tuple[str, Any]], max_bytes: int) -> None:
    while True:
        raw = sys.stdin.buffer.readline(max_bytes + 2)
        if raw == b"":
            output.put(("eof", None))
            return
        if len(raw) > max_bytes or not raw.endswith(b"\n"):
            output.put(("fatal", "persistent candidate request line is oversized or unterminated"))
            return
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            output.put(("request", {"_parse_error": f"{type(exc).__name__}: {exc}"}))
        else:
            output.put(("request", payload))


def serve(
    config: dict[str, Any],
    session_nonce: str,
    startup_phase_timings: list[dict[str, Any]],
) -> int:
    max_line = int(config["bounds"]["max_line_bytes"])
    max_response = int(config["bounds"]["max_response_bytes"])
    protocol_output = sys.stdout.buffer

    def emit_protocol(payload: dict[str, Any]) -> None:
        _emit(payload, max_response, output=protocol_output)

    host = PersistentWorkerHost(
        config,
        session_nonce,
        startup_phase_timings,
        event_emitter=emit_protocol,
    )
    idle_seconds = float(config["bounds"]["idle_unload_seconds"])
    hard_seconds = float(config["bounds"]["hard_process_lifetime_seconds"])
    incoming: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=2)
    reader = threading.Thread(
        target=_stdin_reader,
        args=(incoming, max_line),
        name="persistent-blackwell-stdin-reader",
        daemon=True,
    )
    reader.start()
    emit_protocol(host.hello())
    transport_message_count = 0
    try:
        while not host.shutdown_requested:
            now = time.monotonic()
            if now - host.started_monotonic >= hard_seconds:
                unload = host.runtime.unload(reason="hard_process_lifetime")
                emit_protocol(
                    {
                        **host.base_response(),
                        "message_type": "event",
                        "event": "hard_process_lifetime_reached",
                        **unload,
                    },
                )
                break
            if host.runtime.loaded and now - host.runtime.last_activity_monotonic >= idle_seconds:
                unload = host.runtime.unload(reason="idle_timeout")
                emit_protocol(
                    {
                        **host.base_response(),
                        "message_type": "event",
                        "event": "idle_model_unloaded",
                        **unload,
                    },
                )
            try:
                kind, payload = incoming.get(timeout=0.5)
            except queue.Empty:
                continue
            if kind == "eof":
                break
            if kind == "fatal":
                emit_protocol(
                    {
                        **host.base_response(),
                        "message_type": "fatal",
                        "ready": False,
                        "reason": "persistent_candidate_transport_rejected",
                        "error": str(payload),
                    },
                )
                break
            transport_message_count += 1
            if transport_message_count > int(config["bounds"]["max_requests_per_process"]):
                if host.runtime.loaded:
                    host.runtime.unload(reason="transport_request_limit")
                emit_protocol(
                    {
                        **host.base_response(),
                        "message_type": "fatal",
                        "ready": False,
                        "reason": "persistent_candidate_transport_request_limit_reached",
                    },
                )
                break
            if isinstance(payload, dict) and payload.get("_parse_error"):
                emit_protocol(
                    {
                        **host.base_response(),
                        "message_type": "response",
                        "ready": False,
                        "generated": False,
                        "reason": "persistent_candidate_malformed_json",
                        "error": payload["_parse_error"],
                    },
                )
                continue
            response = host.process(payload)
            emit_protocol(response)
    finally:
        if host.runtime.loaded:
            host.runtime.unload(reason="transport_closed")
        # The parent closes its exact stdin pipe immediately after receiving a
        # shutdown response.  Wait briefly for the reader to observe that EOF
        # so no daemon thread is left inside BufferedReader at interpreter
        # finalization on Windows.
        reader.join(timeout=10)
    return 0


def static_self_check(config: dict[str, Any]) -> dict[str, Any]:
    """Verify the candidate without importing Torch or loading any model."""

    torch_preimported = "torch" in sys.modules
    hashes = verify_candidate_config(config)
    cache_paths = verify_restricted_environment(config, require_load_opt_in=False)
    versions = _verify_runtime_metadata(config)
    return {
        "ready": True,
        "reason": "persistent_candidate_static_ready_model_unloaded",
        "candidate_id": config["candidate_id"],
        "candidate_status": config["candidate_status"],
        "production_routing_authorized": False,
        "python_version": ".".join(str(value) for value in sys.version_info[:3]),
        "versions": versions,
        "sealed_artifact_hashes": hashes,
        "cache_paths": cache_paths,
        "torch_imported_before": torch_preimported,
        "torch_imported_after": "torch" in sys.modules,
        "model_loaded": False,
        "audio_generated": False,
        "playback": False,
        "generic_voice_used": False,
        "sapi_voice_used": False,
        "fallback_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--serve", action="store_true")
    group.add_argument("--static-self-check", action="store_true")
    args = parser.parse_args()
    startup_ledger = PhaseLedger()
    try:
        with startup_ledger.phase("startup.config_load"):
            config = load_candidate_config()
        with startup_ledger.phase("startup.sealed_contract_verification"):
            verify_candidate_config(config)
        with startup_ledger.phase("startup.restricted_environment"):
            environment = verify_restricted_environment(config, require_load_opt_in=False)
        nonce = str(os.environ.get("KIRA_PERSISTENT_BLACKWELL_SESSION_NONCE") or "")
        if args.static_self_check:
            result = static_self_check(config)
            result["startup_phase_timings"] = startup_ledger.records
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0
        if not environment:
            raise ValueError("persistent candidate restricted environment was not verified")
        return serve(config, nonce, startup_ledger.records)
    except Exception as exc:
        result = {
            "ready": False,
            "generated": False,
            "reason": "persistent_candidate_startup_failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc()[-12000:],
            "production_routing_authorized": False,
            "playback": False,
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "startup_phase_timings": startup_ledger.records,
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
