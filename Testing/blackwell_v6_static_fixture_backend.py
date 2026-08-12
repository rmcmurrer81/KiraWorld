"""Standard-library-only fake backend for Blackwell v6 hostile static tests."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
import wave
from pathlib import Path
from typing import Any

from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v6 import persistent_worker as worker


ROOT = Path(__file__).resolve().parents[1]


class StaticTensor:
    def __init__(self, device: str, payload: bytes):
        self.device = device
        self.payload = payload
        self.shape = (2, 2)
        self.dtype = "float32"

    def to(self, device: str):
        self.device = device
        return self

    def detach(self):
        return self

    def cpu(self):
        return self.to("cpu")

    def contiguous(self):
        return self

    def content_bytes(self):
        return self.payload


class StaticModule:
    def __init__(self, name: str, device: str = "cuda"):
        self.tensor = StaticTensor(device, name.encode("utf-8"))

    def parameters(self):
        return [self.tensor]

    def buffers(self):
        return []

    def to(self, device: str):
        self.tensor.to(device)
        return self


class StaticConditionGroup:
    def __init__(self, device: str = "cuda"):
        self.token = StaticTensor(device, b"v6-condition-token")

    def to(self, device: str):
        self.token.to(device)
        return self


class StaticConditions:
    def __init__(self, device: str = "cuda"):
        self.t3 = StaticConditionGroup(device)

    def to(self, device: str):
        self.t3.to(device)
        return self


class StaticModel:
    def __init__(self, device: str = "cuda"):
        self.t3 = StaticModule("t3", device)
        self.s3gen = StaticModule("s3gen", device)
        self.ve = StaticModule("ve", device)
        self.conds = StaticConditions(device)
        self.device = device


class ManualClock:
    def __init__(self, value: float = 1000.0):
        self.value = value

    def __call__(self):
        return self.value

    def advance(self, seconds: float):
        self.value += seconds


class StaticV6Backend:
    def __init__(self, *, now, worker_pid: int, lease_id: str):
        self.now = now
        self.worker_pid = worker_pid
        self.lease_id = lease_id
        self.model = StaticModel()
        self.resource_sequence = 0
        self.qwen_sequence = 0
        self.qwen_records: list[dict[str, str]] = []
        self.qwen_race_phase: str | None = None
        self.qwen_race_mode = "exact"
        self.resource_mode = "normal"
        self.stream_chunks = ["Natural ", "reply."]
        self.stream_advance_per_chunk = 0.0
        self.qwen_unload_success = True
        self.release_success = True
        self.artifact_mode = "valid"
        self.cuda_mode = "valid"
        self.last_load_kwargs: dict[str, Any] | None = None
        self.last_qwen_load_request: dict[str, Any] | None = None
        self.last_qwen_stream_request: dict[str, Any] | None = None
        self.last_synthesis_kwargs: dict[str, Any] | None = None
        root = ROOT / "RecoverySprint/runtime_cache/blackwell_chatterbox/v6_outputs"
        self.output_dir = root / (
            f"static_v6_{worker_pid}_{time.monotonic_ns()}_{id(self)}"
        )

    def close(self):
        shutil.rmtree(self.output_dir, ignore_errors=True)

    def resources(self, *, label: str, worker_pid: int):
        self.resource_sequence += 1
        model_device = getattr(self.model, "device", "cpu")
        if self.resource_mode == "high_park_rss" and label.startswith("park"):
            rss, commit, available, fraction = 20000.0, 30000.0, 6500.0, 0.75
        elif model_device == "cuda" and label not in {"load_before", "cleanup_after"}:
            rss, commit, available, fraction = 7000.0, 16000.0, 9000.0, 0.4
        else:
            rss, commit, available, fraction = 1000.0, 12000.0, 12000.0, 0.3
        if model_device == "cuda" and label not in {"load_before", "cleanup_after"}:
            allocated, reserved, cuda_free = 3_500_000_000.0, 3_800_000_000.0, 8000.0
        else:
            allocated, reserved, cuda_free = 0.0, 0.0, 15000.0
        captured = self.now()
        if self.resource_mode == "nan":
            rss = float("nan")
        elif self.resource_mode == "future":
            captured += 10.0
        return {
            "process_rss_mib": rss,
            "system_commit_used_mib": commit,
            "system_commit_limit_mib": 40000.0,
            "available_physical_mib": available,
            "total_physical_mib": 32000.0,
            "system_commit_fraction": fraction,
            "cuda_allocated_bytes": allocated,
            "cuda_reserved_bytes": reserved,
            "cuda_free_mib": cuda_free,
            "cuda_total_mib": 16000.0,
            "captured_monotonic": captured,
            "sample_id": hashlib.sha256(
                f"v6-resource:{self.resource_sequence}:{label}:{captured}".encode()
            ).hexdigest(),
            "sample_sequence": self.resource_sequence,
            "pid": worker_pid,
            "cuda_device_name": worker.EXACT_CUDA_DEVICE_NAME,
            "compute_capability": [12, 0],
        }

    def qwen_residency(self, *, phase, serialization_lease_id, worker_pid):
        self.qwen_sequence += 1
        if phase == self.qwen_race_phase:
            if self.qwen_race_mode == "extra":
                self.qwen_records[:] = [
                    {"model": worker.EXACT_QWEN_MODEL, "digest": worker.EXACT_QWEN_DIGEST},
                    {"model": "unowned:1b", "digest": "0" * 64},
                ]
            elif self.qwen_race_mode == "wrong":
                self.qwen_records[:] = [
                    {"model": worker.EXACT_QWEN_MODEL, "digest": "0" * 64}
                ]
            else:
                self.qwen_records[:] = [
                    {"model": worker.EXACT_QWEN_MODEL, "digest": worker.EXACT_QWEN_DIGEST}
                ]
        captured = self.now()
        return {
            "query_succeeded": True,
            "records": list(self.qwen_records),
            "serialization_lease_id": serialization_lease_id,
            "lease_exclusive": True,
            "sample_id": hashlib.sha256(
                f"v6-qwen:{self.qwen_sequence}:{phase}:{captured}".encode()
            ).hexdigest(),
            "sample_sequence": self.qwen_sequence,
            "captured_monotonic": captured,
            "phase": phase,
            "worker_pid": worker_pid,
        }

    def load_voice(self, **kwargs):
        self.last_load_kwargs = dict(kwargs)
        self.model = StaticModel()
        return {
            "model": self.model,
            "identity": worker.verify_identity_files(),
            "load_proof": {
                "from_pretrained_call_count": 1,
                "prepare_conditionals_call_count": 1,
                "approved_audio_prompt_path": kwargs["approved_audio_prompt_path"],
                "approved_audio_prompt_sha256": kwargs["approved_audio_prompt_sha256"],
                "serialization_lease_id": kwargs["serialization_lease_id"],
                "worker_pid": self.worker_pid,
            },
        }

    def voice_model_binding(self, **kwargs):
        return {
            "same_object": kwargs["model"] is self.model,
            "model_object_id": id(kwargs["model"]),
            "backend_object_id": id(self),
            "model_generation": kwargs["model_generation"],
            "worker_pid": kwargs["worker_pid"],
        }

    @staticmethod
    def cuda_cache_cleanup():
        return {
            "cache_cleared": True,
            "synchronize_before": True,
            "empty_cache_called": True,
            "synchronize_after": True,
        }

    def release_voice(self):
        if self.release_success:
            self.model = StaticModel("cpu")
        return {
            "released": self.release_success,
            "owned_model_count": 0 if self.release_success else 1,
            "owned_condition_count": 0 if self.release_success else 1,
        }

    def qwen_load_only(self, *, request):
        self.last_qwen_load_request = dict(request)
        self.qwen_records[:] = [
            {"model": worker.EXACT_QWEN_MODEL, "digest": worker.EXACT_QWEN_DIGEST}
        ]
        request_hash = hashlib.sha256(
            json.dumps(
                request, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()
        return {
            "model": worker.EXACT_QWEN_MODEL,
            "digest": worker.EXACT_QWEN_DIGEST,
            "request_hash": request_hash,
            "response": "",
            "message": {"content": ""},
            "eval_count": 0,
            "prompt_eval_count": 0,
            "serialization_lease_id": self.lease_id,
        }

    def qwen_stream(self, *, request):
        self.last_qwen_stream_request = dict(request)
        chunks = list(self.stream_chunks)
        if self.stream_advance_per_chunk:
            original = chunks
            chunks = []
            for item in original:
                self.now.advance(self.stream_advance_per_chunk)
                chunks.append(item)
        self.qwen_records[:] = []
        text = "".join(chunks)
        request_hash = hashlib.sha256(
            json.dumps(
                request, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()
        return {
            "model": worker.EXACT_QWEN_MODEL,
            "digest": worker.EXACT_QWEN_DIGEST,
            "request_hash": request_hash,
            "chunks": chunks,
            "final_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "keep_alive": 0,
            "serialization_lease_id": self.lease_id,
        }

    def qwen_unload_owned(self, **kwargs):
        if self.qwen_unload_success:
            self.qwen_records[:] = []
        return {
            "unloaded": self.qwen_unload_success,
            "model": kwargs["model"],
            "digest": kwargs["digest"],
            "token_hash": kwargs["token_hash"],
            "serialization_lease_id": kwargs["serialization_lease_id"],
        }

    @staticmethod
    def _write_wav(path: Path, silent: bool = False):
        samples = [0] * 1600 if silent else [0, 1200, -1200, 600, -600] * 320
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(16000)
            handle.writeframes(
                b"".join(int(value).to_bytes(2, "little", signed=True) for value in samples)
            )

    def synthesize_cuda(self, **kwargs):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.last_synthesis_kwargs = dict(kwargs)
        path = self.output_dir / f"{kwargs['generation_id']}.wav"
        self._write_wav(path, silent=self.artifact_mode == "silent")
        artifact_sha = worker.sha256_file(path)
        now = self.now()
        return {
            "artifact_path": str(path.resolve()),
            "artifact_sha256": artifact_sha,
            "generation_id": kwargs["generation_id"],
            "text_sha256": kwargs["text_sha256"],
            "prompt_path": kwargs["approved_audio_prompt_path"],
            "prompt_sha256": kwargs["approved_audio_prompt_sha256"],
            "route": "blackwell_gpu",
            "device": "cuda",
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "generation_started_monotonic": now - 0.1,
            "generation_ended_monotonic": now,
            "model_generation": kwargs["model_generation"],
            "model_object_id": kwargs["model_object_id"],
            "backend_object_id": kwargs["backend_object_id"],
        }

    def cuda_generation_evidence(self, **kwargs):
        now = self.now()
        sample_end = 10**12 if self.cuda_mode == "future" else now
        return {
            "generation_id": kwargs["generation_id"],
            "text_sha256": kwargs["text_sha256"],
            "artifact_sha256": kwargs["artifact_sha256"],
            "model_generation": kwargs["model_generation"],
            "worker_instance_id": kwargs["worker_instance_id"],
            "worker_pid": kwargs["worker_pid"],
            "model_object_id": id(self.model),
            "backend_object_id": id(self),
            "device": "cuda",
            "cuda_device_name": worker.EXACT_CUDA_DEVICE_NAME,
            "compute_capability": [12, 0],
            "allocated_before_bytes": 100,
            "peak_allocated_bytes": 1000,
            "allocated_after_bytes": 120,
            "synchronize_before": True,
            "synchronize_after": True,
            "unsupported_architecture_warning": False,
            "no_kernel_image_error": False,
            "sample_start_monotonic": now - 0.2,
            "sample_end_monotonic": sample_end,
        }


__all__ = [
    "ManualClock",
    "StaticModel",
    "StaticV6Backend",
]
