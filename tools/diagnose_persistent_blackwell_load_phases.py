#!/usr/bin/env python3
"""Append-only diagnosis for the inactive persistent Blackwell voice loader.

The default command is read-only and performs no heavy import.  A later,
explicitly authorized execution starts the exact sealed Python 3.11.9 runtime
in the candidate's restricted offline environment and emits phase events while
loading.  It never synthesizes, plays audio, changes routing, or promotes the
candidate.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import gc
import hashlib
import importlib.metadata
import json
import os
import queue
import secrets
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Iterator


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate"
CONFIG_PATH = CANDIDATE_ROOT / "candidate_config.json"
CONTRACT_PATH = CANDIDATE_ROOT / "candidate_contract.py"
CLIENT_PATH = CANDIDATE_ROOT / "candidate_client.py"
WORKER_PATH = CANDIDATE_ROOT / "persistent_worker.py"
TTS_SOURCE_PATH = (
    ROOT
    / "Voice"
    / "sidecars"
    / "chatterbox_blackwell_gpu"
    / ".venv"
    / "Lib"
    / "site-packages"
    / "chatterbox"
    / "tts.py"
)
ACCEPTANCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
)
DIAGNOSTIC_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_load_phase_diagnostic"
)

EXPECTED_SHA256 = {
    "attempt_01": "7272dc7da369569d077f88972d491aa84071582c42b798040e6106c7c98ec76b",
    "attempt_02": "0bbf02d021c6217a7fbeca79e4f809bf640789215c61c14b2a9b675a9d67d115",
    "candidate_config": "a96278400a675a8e8dc38c38087659de52e2b8b0d2bcc345118a64177b0899d0",
    "candidate_contract": "89decf08ed3502b6e771d3940867d5f7c2f31bb2f4fc0e515083dc15fbf850fe",
    "candidate_client": "66b62c958c764344138e8c79f1cec4b63a6ba74a9e3ee0a77f777503a835dfe1",
    "candidate_worker": "aa67d6eb7be12ddc61e1fcdf57715cfbe6f26ac966a996d7bab7304e7415b060",
    "installed_chatterbox_tts_source": "7896787bc17e20eafcd1dce7b8a4a6ea3a6478baab771c60d63e9e81f5564195",
    "production_routing": "a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81",
    "production_gpu_worker": "c7ac33170f5f5b85ef7df717a71bf468b2f37166bb5f70e6441bea8ed6d8da1e",
    "sealed_cpu_worker": "856c195173f8932f1b9d731634290f9eb78bb543e90da37c1346160e45334f46",
}

BOUND_FILES = {
    "attempt_01": ACCEPTANCE_ROOT / "attempt_01" / "PERSISTENT_BLACKWELL_ACCEPTANCE.json",
    "attempt_02": ACCEPTANCE_ROOT / "attempt_02" / "PERSISTENT_BLACKWELL_ACCEPTANCE.json",
    "candidate_config": CONFIG_PATH,
    "candidate_contract": CONTRACT_PATH,
    "candidate_client": CLIENT_PATH,
    "candidate_worker": WORKER_PATH,
    "installed_chatterbox_tts_source": TTS_SOURCE_PATH,
    "production_routing": ROOT / "Voice" / "sidecars" / "kira_approved_voice_routing.json",
    "production_gpu_worker": ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_gpu" / "sidecar_worker.py",
    "sealed_cpu_worker": ROOT / "Voice" / "sidecars" / "chatterbox_py311" / "sidecar_worker.py",
}

MODEL_FILENAMES = (
    "ve.safetensors",
    "t3_cfg.safetensors",
    "s3gen.safetensors",
    "tokenizer.json",
    "conds.pt",
)

DIAGNOSTIC_PHASES = (
    "preflight.runtime_metadata",
    "preflight.approved_identity_hashes",
    "preflight.qwen_absence",
    "import.torch",
    "import.torchaudio",
    "import.transformers_compatibility",
    "import.numpy",
    "import.soundfile",
    "import.huggingface_hub",
    "import.safetensors_torch",
    "import.librosa",
    "import.perth",
    "import.chatterbox_class",
    "cache.resolve.ve.safetensors",
    "cache.resolve.t3_cfg.safetensors",
    "cache.resolve.s3gen.safetensors",
    "cache.resolve.tokenizer.json",
    "cache.resolve.conds.pt",
    "cuda.contract_and_initialize",
    "from_pretrained.total",
    "from_pretrained.voice_encoder.construct",
    "from_pretrained.voice_encoder.load_file",
    "from_pretrained.voice_encoder.load_state_dict",
    "from_pretrained.voice_encoder.device_transfer",
    "from_pretrained.t3.construct",
    "from_pretrained.t3.load_file",
    "from_pretrained.t3.load_state_dict",
    "from_pretrained.t3.device_transfer",
    "from_pretrained.s3gen.construct",
    "from_pretrained.s3gen.load_file",
    "from_pretrained.s3gen.load_state_dict",
    "from_pretrained.s3gen.device_transfer",
    "from_pretrained.tokenizer.construct",
    "from_pretrained.builtin_conditionals.load",
    "from_pretrained.builtin_conditionals.device_transfer",
    "from_pretrained.chatterbox.construct",
    "reference.prepare_conditionals",
    "cleanup.model_release_gc",
    "cleanup.cuda_empty_cache",
)

PHASE_TIMEOUT_SECONDS = {
    "preflight.runtime_metadata": 15.0,
    "preflight.approved_identity_hashes": 30.0,
    "preflight.qwen_absence": 10.0,
    "import.torch": 120.0,
    "import.torchaudio": 90.0,
    "import.transformers_compatibility": 180.0,
    "import.numpy": 30.0,
    "import.soundfile": 30.0,
    "import.huggingface_hub": 60.0,
    "import.safetensors_torch": 60.0,
    "import.librosa": 90.0,
    "import.perth": 90.0,
    "import.chatterbox_class": 180.0,
    "cuda.contract_and_initialize": 60.0,
    "from_pretrained.total": 900.0,
    "reference.prepare_conditionals": 300.0,
    "cleanup.model_release_gc": 120.0,
    "cleanup.cuda_empty_cache": 60.0,
}
DEFAULT_NESTED_TIMEOUT_SECONDS = 300.0
OVERALL_TIMEOUT_SECONDS = 1800.0


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def bound_integrity() -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for label, path in BOUND_FILES.items():
        actual = sha256_file(path) if path.is_file() else None
        rows[label] = {
            "path": project_relative(path),
            "expected_sha256": EXPECTED_SHA256[label],
            "actual_sha256": actual,
            "matches": actual == EXPECTED_SHA256[label],
            "bytes": path.stat().st_size if path.is_file() else None,
        }
    return {"passed": all(row["matches"] for row in rows.values()), "files": rows}


def static_cache_inventory() -> dict[str, Any]:
    profile = Path(os.environ.get("USERPROFILE") or "")
    cache = profile / ".cache" / "huggingface" / "hub" / "models--ResembleAI--chatterbox"
    ref = cache / "refs" / "main"
    revision = ref.read_text(encoding="utf-8").strip() if ref.is_file() else None
    snapshot = cache / "snapshots" / str(revision or "")
    files: list[dict[str, Any]] = []
    for name in MODEL_FILENAMES:
        path = snapshot / name
        files.append(
            {
                "filename": name,
                "path": str(path.resolve()),
                "present": path.is_file(),
                "bytes": path.stat().st_size if path.is_file() else None,
                "sha256_intentionally_not_computed": True,
            }
        )
    return {
        "repo_id": "ResembleAI/chatterbox",
        "cache_root": str(cache.resolve()),
        "revision": revision,
        "snapshot_root": str(snapshot.resolve()),
        "all_required_files_present": bool(revision) and all(row["present"] for row in files),
        "files": files,
        "cache_modified": False,
    }


def describe() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "artifact_kind": "persistent_blackwell_load_phase_diagnostic",
        "status": "prepared_inactive_not_executed",
        "candidate_status": "inactive_private_candidate_not_production",
        "production_route_unchanged": True,
        "production_preference": "blackwell_gpu_one_shot_eager_cuda",
        "automatic_fallback": "sealed_cpu_chatterbox_only",
        "synthesis_performed": False,
        "playback_performed": False,
        "model_or_gpu_execution_performed_by_describe": False,
        "attempt_02_observed_total_wall_seconds": 888.583143,
        "attempt_02_last_confirmed_boundary": "before_model_load",
        "attempt_02_internal_stall_phase": "UNKNOWN_BECAUSE_LOAD_EMITTED_NO_PROGRESS_EVENTS",
        "resource_sampler_hazard": {
            "starts_before_backend_imports": True,
            "interval_seconds": 0.25,
            "external_process_per_sample": "nvidia-smi.exe",
            "causal_status": "PLAUSIBLE_CONFOUNDER_NOT_PROVEN_CAUSE",
            "diagnostic_behavior": "no_repeating_nvidia_smi_sampler",
        },
        "phases": list(DIAGNOSTIC_PHASES),
        "phase_timeout_seconds": PHASE_TIMEOUT_SECONDS,
        "nested_default_timeout_seconds": DEFAULT_NESTED_TIMEOUT_SECONDS,
        "overall_timeout_seconds": OVERALL_TIMEOUT_SECONDS,
        "full_load_generates_audio": False,
        "full_load_prepares_reference_conditionals": True,
        "full_load_changes_production_routing": False,
    }


def blender_process_evidence() -> dict[str, Any]:
    completed = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq blender.exe", "/FO", "CSV", "/NH"],
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    matches = [line for line in lines if "blender.exe" in line.casefold()]
    return {
        "query_succeeded": completed.returncode == 0,
        "active": bool(matches),
        "matches": matches,
        "returncode": completed.returncode,
        "stderr": completed.stderr.strip()[:1000],
        "process_state_changed": False,
    }


def allocate_attempt_directory(root: Path = DIAGNOSTIC_ROOT) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    existing = {
        item.name for item in root.iterdir() if item.is_dir() and item.name.startswith("attempt_")
    }
    index = 1
    while f"attempt_{index:02d}" in existing:
        index += 1
    target = root / f"attempt_{index:02d}"
    target.mkdir(parents=False, exist_ok=False)
    return target


class EventEmitter:
    def __init__(self, stream: Any) -> None:
        self.stream = stream
        self.lock = threading.Lock()
        self.phase_stack: list[tuple[str, int]] = []
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._heartbeats, name="kira-load-diagnostic-heartbeat", daemon=True)

    def emit(self, message_type: str, **values: Any) -> None:
        payload = {"schema_version": 1, "message_type": message_type, "utc": utc_now(), **values}
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with self.lock:
            self.stream.write(encoded + "\n")
            self.stream.flush()

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=3)

    def _heartbeats(self) -> None:
        while not self.stop_event.wait(2.0):
            with self.lock:
                phase = self.phase_stack[-1] if self.phase_stack else None
            if phase is not None:
                name, started_ns = phase
                self.emit(
                    "heartbeat",
                    phase=name,
                    phase_elapsed_seconds=round((time.perf_counter_ns() - started_ns) / 1e9, 6),
                    pid=os.getpid(),
                )

    @contextlib.contextmanager
    def phase(self, name: str, **metadata: Any) -> Iterator[None]:
        started_ns = time.perf_counter_ns()
        with self.lock:
            self.phase_stack.append((name, started_ns))
        self.emit("phase_start", phase=name, monotonic_ns=started_ns, pid=os.getpid(), **metadata)
        try:
            yield
        except Exception as exc:
            self.emit(
                "phase_end",
                phase=name,
                status="failed",
                error_type=type(exc).__name__,
                error=str(exc)[:4000],
                elapsed_seconds=round((time.perf_counter_ns() - started_ns) / 1e9, 9),
                pid=os.getpid(),
            )
            raise
        else:
            self.emit(
                "phase_end",
                phase=name,
                status="passed",
                elapsed_seconds=round((time.perf_counter_ns() - started_ns) / 1e9, 9),
                pid=os.getpid(),
            )
        finally:
            with self.lock:
                if self.phase_stack and self.phase_stack[-1][0] == name:
                    self.phase_stack.pop()
                else:
                    self.phase_stack = [item for item in self.phase_stack if item[0] != name]


def child_worker(scope: str) -> int:
    protocol_stdout = sys.stdout
    emitter = EventEmitter(protocol_stdout)
    emitter.start()
    model: Any | None = None
    torch: Any | None = None
    try:
        if str(CANDIDATE_ROOT) not in sys.path:
            sys.path.insert(0, str(CANDIDATE_ROOT))
        with contextlib.redirect_stdout(sys.stderr):
            import candidate_contract

            config = candidate_contract.load_candidate_config()
            candidate_contract.verify_candidate_config(config)
            candidate_contract.verify_restricted_environment(
                config,
                require_load_opt_in=(scope == "full_load"),
            )
            emitter.emit(
                "worker_ready",
                pid=os.getpid(),
                python=sys.version,
                scope=scope,
                synthesis_performed=False,
                playback_performed=False,
            )
            with emitter.phase("preflight.runtime_metadata"):
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
                if versions != expected or tuple(sys.version_info[:3]) != (3, 11, 9):
                    raise RuntimeError(f"sealed runtime mismatch: versions={versions}, python={sys.version}")
            emitter.emit("evidence", kind="runtime_metadata", versions=versions)
            with emitter.phase("preflight.approved_identity_hashes"):
                identity = candidate_contract.verify_identity_files(config)
            emitter.emit("evidence", kind="approved_identity", identity=identity)
            with emitter.phase("preflight.qwen_absence"):
                qwen = candidate_contract.qwen_residency_evidence(config)
                if qwen.get("qwen_absent_proven") is not True:
                    raise RuntimeError(f"Qwen absence not proven: {qwen}")
            emitter.emit("evidence", kind="qwen_absence", qwen=qwen)

            with emitter.phase("import.torch"):
                import torch as imported_torch
            torch = imported_torch
            with emitter.phase("import.torchaudio"):
                import torchaudio
            with emitter.phase("import.transformers_compatibility"):
                from transformers import GPT2Config, GPT2Model, LlamaConfig, LlamaModel
            with emitter.phase("import.numpy"):
                import numpy as np
            with emitter.phase("import.soundfile"):
                import soundfile as sf
            with emitter.phase("import.huggingface_hub"):
                from huggingface_hub import hf_hub_download
            with emitter.phase("import.safetensors_torch"):
                from safetensors.torch import load_file
            with emitter.phase("import.librosa"):
                import librosa
            with emitter.phase("import.perth"):
                import perth
            with emitter.phase("import.chatterbox_class"):
                import chatterbox.tts as chatterbox_tts
                from chatterbox.tts import ChatterboxTTS
            emitter.emit(
                "evidence",
                kind="imports",
                modules={
                    "torch": torch.__version__,
                    "torchaudio": torchaudio.__version__,
                    "numpy": np.__version__,
                    "soundfile": sf.__version__,
                    "librosa": librosa.__version__,
                    "perth": getattr(perth, "__version__", "unreported"),
                    "LlamaModel": LlamaModel.__module__,
                    "LlamaConfig": LlamaConfig.__module__,
                    "GPT2Model": GPT2Model.__module__,
                    "GPT2Config": GPT2Config.__module__,
                },
            )

            resolved: dict[str, str] = {}
            for filename in MODEL_FILENAMES:
                with emitter.phase(f"cache.resolve.{filename}", local_files_only=True):
                    path = Path(
                        hf_hub_download(
                            repo_id=chatterbox_tts.REPO_ID,
                            filename=filename,
                            local_files_only=True,
                        )
                    ).resolve()
                    if not path.is_file():
                        raise FileNotFoundError(path)
                    resolved[filename] = str(path)
                emitter.emit(
                    "evidence",
                    kind="cache_file",
                    filename=filename,
                    path=str(path),
                    bytes=path.stat().st_size,
                    sha256_intentionally_not_computed=True,
                )
            parents = {str(Path(value).parent) for value in resolved.values()}
            if len(parents) != 1:
                raise RuntimeError(f"model cache files do not share one snapshot: {parents}")
            emitter.emit("evidence", kind="cache_resolution", snapshot_root=next(iter(parents)))

            if scope == "pre_cuda":
                emitter.emit(
                    "terminal",
                    status="passed_pre_cuda_only",
                    full_model_loaded=False,
                    reference_prepared=False,
                    synthesis_performed=False,
                    playback_performed=False,
                )
                return 0

            with emitter.phase("cuda.contract_and_initialize"):
                checks = {
                    "cuda_available": bool(torch.cuda.is_available()),
                    "device_name": torch.cuda.get_device_name(0),
                    "device_capability": list(torch.cuda.get_device_capability(0)),
                    "compiled_architectures": torch.cuda.get_arch_list(),
                }
                if not checks["cuda_available"]:
                    raise RuntimeError("CUDA unavailable")
                if checks["device_name"] != config["required_device_name"]:
                    raise RuntimeError(f"device mismatch: {checks}")
                if checks["device_capability"] != config["required_device_capability"]:
                    raise RuntimeError(f"capability mismatch: {checks}")
                if config["required_compiled_architecture"] not in checks["compiled_architectures"]:
                    raise RuntimeError(f"architecture mismatch: {checks}")
                torch.cuda.synchronize(0)
                torch.cuda.empty_cache()
            emitter.emit("evidence", kind="cuda_contract", checks=checks)

            original_hf = chatterbox_tts.hf_hub_download
            original_from_local = ChatterboxTTS.__dict__["from_local"]

            def traced_hf_hub_download(*args: Any, **kwargs: Any) -> str:
                filename = str(kwargs.get("filename") or (args[1] if len(args) > 1 else "unknown"))
                kwargs["local_files_only"] = True
                with emitter.phase(f"from_pretrained.cache_resolve.{filename}", local_files_only=True):
                    return str(original_hf(*args, **kwargs))

            def traced_from_local(cls: Any, ckpt_dir: Any, device: str) -> Any:
                directory = Path(ckpt_dir)
                map_location = torch.device("cpu") if device in ("cpu", "mps") else None
                with emitter.phase("from_pretrained.voice_encoder.construct"):
                    ve = chatterbox_tts.VoiceEncoder()
                with emitter.phase("from_pretrained.voice_encoder.load_file"):
                    ve_state = load_file(directory / "ve.safetensors")
                with emitter.phase("from_pretrained.voice_encoder.load_state_dict"):
                    ve.load_state_dict(ve_state)
                    del ve_state
                with emitter.phase("from_pretrained.voice_encoder.device_transfer", device=device):
                    ve.to(device).eval()

                with emitter.phase("from_pretrained.t3.construct"):
                    t3 = chatterbox_tts.T3()
                with emitter.phase("from_pretrained.t3.load_file"):
                    t3_state = load_file(directory / "t3_cfg.safetensors")
                if "model" in t3_state.keys():
                    t3_state = t3_state["model"][0]
                with emitter.phase("from_pretrained.t3.load_state_dict"):
                    t3.load_state_dict(t3_state)
                    del t3_state
                with emitter.phase("from_pretrained.t3.device_transfer", device=device):
                    t3.to(device).eval()

                with emitter.phase("from_pretrained.s3gen.construct"):
                    s3gen = chatterbox_tts.S3Gen()
                with emitter.phase("from_pretrained.s3gen.load_file"):
                    s3_state = load_file(directory / "s3gen.safetensors")
                with emitter.phase("from_pretrained.s3gen.load_state_dict"):
                    s3gen.load_state_dict(s3_state, strict=False)
                    del s3_state
                with emitter.phase("from_pretrained.s3gen.device_transfer", device=device):
                    s3gen.to(device).eval()

                with emitter.phase("from_pretrained.tokenizer.construct"):
                    tokenizer = chatterbox_tts.EnTokenizer(str(directory / "tokenizer.json"))
                conds = None
                builtin = directory / "conds.pt"
                if builtin.exists():
                    with emitter.phase("from_pretrained.builtin_conditionals.load"):
                        conds = chatterbox_tts.Conditionals.load(builtin, map_location=map_location)
                    with emitter.phase(
                        "from_pretrained.builtin_conditionals.device_transfer", device=device
                    ):
                        conds = conds.to(device)
                with emitter.phase("from_pretrained.chatterbox.construct"):
                    return cls(t3, s3gen, ve, tokenizer, device, conds=conds)

            chatterbox_tts.hf_hub_download = traced_hf_hub_download
            ChatterboxTTS.from_local = classmethod(traced_from_local)
            try:
                with emitter.phase(
                    "from_pretrained.total",
                    implementation="sealed_from_pretrained_with_hash_bound_instrumented_from_local",
                ):
                    model = ChatterboxTTS.from_pretrained(device="cuda")
            finally:
                chatterbox_tts.hf_hub_download = original_hf
                ChatterboxTTS.from_local = original_from_local

            emitter.emit(
                "evidence",
                kind="model_loaded",
                sample_rate=int(model.sr),
                allocated_bytes=int(torch.cuda.memory_allocated(0)),
                reserved_bytes=int(torch.cuda.memory_reserved(0)),
            )
            with emitter.phase("reference.prepare_conditionals"):
                model.prepare_conditionals(str(candidate_contract.project_file(config["approved_reference"])))
            torch.cuda.synchronize(0)
            emitter.emit(
                "evidence",
                kind="reference_prepared",
                approved_reference_sha256=identity["reference_sha256"],
                conditionals_present=model.conds is not None,
                allocated_bytes=int(torch.cuda.memory_allocated(0)),
                reserved_bytes=int(torch.cuda.memory_reserved(0)),
            )

            with emitter.phase("cleanup.model_release_gc"):
                model = None
                gc.collect()
            with emitter.phase("cleanup.cuda_empty_cache"):
                torch.cuda.empty_cache()
                torch.cuda.synchronize(0)
            emitter.emit(
                "terminal",
                status="passed_full_load_diagnostic_only",
                full_model_loaded_then_released=True,
                reference_prepared=True,
                synthesis_performed=False,
                playback_performed=False,
                allocated_after_cleanup_bytes=int(torch.cuda.memory_allocated(0)),
                reserved_after_cleanup_bytes=int(torch.cuda.memory_reserved(0)),
            )
            return 0
    except Exception as exc:
        emitter.emit(
            "terminal",
            status="failed_preserved_inactive",
            error_type=type(exc).__name__,
            error=str(exc)[:8000],
            traceback=traceback.format_exc()[-16000:],
            synthesis_performed=False,
            playback_performed=False,
            candidate_promoted=False,
        )
        return 2
    finally:
        model = None
        if torch is not None:
            try:
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize(0)
            except Exception:
                pass
        emitter.stop()


def _stream_reader(stream: Any, output: queue.Queue[tuple[str, str]], label: str) -> None:
    while True:
        raw = stream.readline()
        if not raw:
            return
        output.put((label, raw.decode("utf-8", errors="replace").rstrip("\r\n")))


def phase_timeout(name: str) -> float:
    if name in PHASE_TIMEOUT_SECONDS:
        return PHASE_TIMEOUT_SECONDS[name]
    if name.startswith("cache.resolve.") or name.startswith("from_pretrained.cache_resolve."):
        return 60.0
    if name.startswith("from_pretrained."):
        return 300.0
    return DEFAULT_NESTED_TIMEOUT_SECONDS


def run_diagnostic(scope: str) -> tuple[Path, dict[str, Any]]:
    integrity = bound_integrity()
    if integrity["passed"] is not True:
        raise RuntimeError("preserved candidate/attempt/production integrity mismatch")
    blender = blender_process_evidence()
    if blender["query_succeeded"] is not True or blender["active"] is True:
        raise RuntimeError(f"cannot prove no active Blender process: {blender}")

    if str(CANDIDATE_ROOT) not in sys.path:
        sys.path.insert(0, str(CANDIDATE_ROOT))
    import candidate_client
    import candidate_contract

    config = candidate_contract.load_candidate_config()
    qwen = candidate_contract.qwen_residency_evidence(config)
    if qwen.get("qwen_absent_proven") is not True:
        raise RuntimeError(f"Qwen absence not proven; diagnostic refused: {qwen}")
    nonce = secrets.token_urlsafe(48)
    environment = candidate_client.restricted_candidate_environment(
        config,
        session_nonce=nonce,
        allow_gpu_model_load=(scope == "full_load"),
    )
    environment["KIRA_PERSISTENT_LOAD_PHASE_DIAGNOSTIC"] = "1"
    attempt = allocate_attempt_directory()
    event_path = attempt / "EVENTS.jsonl"
    stderr_path = attempt / "STDERR.log"
    report_path = attempt / "REPORT.json"
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "persistent_blackwell_load_phase_diagnostic",
        "started_at": utc_now(),
        "scope": scope,
        "candidate_status": "inactive_private_candidate_not_production",
        "production_route_unchanged": True,
        "synthesis_performed": False,
        "playback_performed": False,
        "bound_integrity_before": integrity,
        "blender_before": blender,
        "qwen_before": qwen,
        "events": [],
    }
    command = [
        str(candidate_contract.project_file(config["python"])),
        str(Path(__file__).resolve()),
        "--child-worker",
        "--scope",
        scope,
    ]
    process = subprocess.Popen(
        command,
        cwd=str(ROOT),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert process.stdout is not None and process.stderr is not None
    incoming: queue.Queue[tuple[str, str]] = queue.Queue()
    stdout_thread = threading.Thread(target=_stream_reader, args=(process.stdout, incoming, "stdout"), daemon=True)
    stderr_thread = threading.Thread(target=_stream_reader, args=(process.stderr, incoming, "stderr"), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    started = time.monotonic()
    phase_starts: dict[str, float] = {}
    active_phases: list[str] = []
    terminal: dict[str, Any] | None = None
    timed_out_phase: str | None = None
    stderr_lines: list[str] = []
    try:
        with event_path.open("x", encoding="utf-8", newline="\n") as events_file:
            while True:
                now = time.monotonic()
                if now - started > OVERALL_TIMEOUT_SECONDS:
                    timed_out_phase = active_phases[-1] if active_phases else "overall"
                    break
                if active_phases:
                    current = active_phases[-1]
                    if now - phase_starts[current] > phase_timeout(current):
                        timed_out_phase = current
                        break
                try:
                    label, line = incoming.get(timeout=0.5)
                except queue.Empty:
                    if process.poll() is not None:
                        break
                    continue
                if label == "stderr":
                    if sum(len(value) for value in stderr_lines) < 131072:
                        stderr_lines.append(line)
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    payload = {"schema_version": 1, "message_type": "malformed_stdout", "raw": line[:4000]}
                events_file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
                events_file.flush()
                report["events"].append(payload)
                if payload.get("message_type") == "phase_start":
                    name = str(payload.get("phase"))
                    phase_starts[name] = time.monotonic()
                    active_phases.append(name)
                elif payload.get("message_type") == "phase_end":
                    name = str(payload.get("phase"))
                    if name in active_phases:
                        active_phases.remove(name)
                    phase_starts.pop(name, None)
                elif payload.get("message_type") == "terminal":
                    terminal = payload
                if process.poll() is not None and incoming.empty():
                    break
        if timed_out_phase is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        else:
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
    finally:
        stdout_thread.join(timeout=3)
        stderr_thread.join(timeout=3)
    stderr_path.write_text("\n".join(stderr_lines) + ("\n" if stderr_lines else ""), encoding="utf-8")
    report.update(
        {
            "finished_at": utc_now(),
            "wall_seconds": round(time.monotonic() - started, 6),
            "child_pid": process.pid,
            "child_returncode": process.returncode,
            "timed_out_phase": timed_out_phase,
            "terminal": terminal,
            "status": (
                "passed_diagnostic_only"
                if terminal and str(terminal.get("status", "")).startswith("passed_") and timed_out_phase is None
                else "failed_preserved_inactive"
            ),
            "event_log_sha256": sha256_file(event_path),
            "stderr_sha256": sha256_file(stderr_path),
            "bound_integrity_after": bound_integrity(),
            "synthesis_performed": False,
            "playback_performed": False,
            "production_routing_changed": False,
            "candidate_promoted": False,
        }
    )
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return attempt, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--static-self-check", action="store_true")
    parser.add_argument("--execute-diagnostic", action="store_true")
    parser.add_argument("--confirm-no-active-blender", action="store_true")
    parser.add_argument("--child-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--scope", choices=("pre_cuda", "full_load"), default="pre_cuda")
    args = parser.parse_args()
    if args.child_worker:
        return child_worker(args.scope)
    if args.execute_diagnostic:
        if not args.confirm_no_active_blender:
            parser.error("--execute-diagnostic requires --confirm-no-active-blender")
        attempt, report = run_diagnostic(args.scope)
        print(json.dumps({"attempt": project_relative(attempt), **report}, indent=2))
        return 0 if report["status"] == "passed_diagnostic_only" else 2
    result = describe()
    if args.static_self_check:
        result["bound_integrity"] = bound_integrity()
        result["cache_inventory"] = static_cache_inventory()
        result["static_self_check_passed"] = bool(
            result["bound_integrity"]["passed"]
            and result["cache_inventory"]["all_required_files_present"]
        )
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("static_self_check_passed", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
