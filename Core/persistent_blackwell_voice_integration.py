"""Default-off session integration for the sealed persistent Blackwell candidate.

The accepted one-shot Blackwell -> sealed-CPU router remains production truth.
This module only makes the already sealed persistent candidate reachable behind
an explicit environment flag so a later live acceptance can exercise the exact
owner application lifecycle.  It never edits or weakens the candidate, never
plays audio, and never discovers or terminates a process it did not create.
"""

from __future__ import annotations

import atexit
import hashlib
import importlib.util
import os
import threading
import time
import uuid
import wave
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = (
    PROJECT_ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate"
)
CANDIDATE_CLIENT_PATH = CANDIDATE_ROOT / "candidate_client.py"
CANDIDATE_STAGING_ROOT = (
    PROJECT_ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "runtime_integration_staging"
)
FEATURE_FLAG = "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE"
APPROVED_PROFILE_SHA256 = (
    "102d17f5420a1a16b3a920204ebde0d532c0a9bfd2979dca28048378ecddc116"
)
APPROVED_REFERENCE_SHA256 = (
    "2039a2abd600a63c294d69c2b2e4d450c64c850dc6d1c9a4fbfa1700ba92069c"
)


def _explicit_true(value: Any) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "on"}


def feature_enabled() -> bool:
    """Return the explicit flag state; missing/ambiguous values fail closed."""

    return _explicit_true(os.environ.get(FEATURE_FLAG, "0"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_project_wav(path: Path) -> Path:
    target = Path(path).resolve()
    target.relative_to(PROJECT_ROOT.resolve())
    if target.suffix.casefold() != ".wav":
        raise ValueError("persistent voice integration target must be a project-owned WAV")
    if target.exists():
        raise FileExistsError("persistent voice integration refuses to overwrite a WAV")
    return target


def _validate_wav(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as reader:
        channels = int(reader.getnchannels())
        sample_width = int(reader.getsampwidth())
        sample_rate = int(reader.getframerate())
        frames = int(reader.getnframes())
    passed = (
        path.is_file()
        and path.stat().st_size > 44
        and channels in {1, 2}
        and sample_width in {1, 2, 3, 4}
        and sample_rate >= 8000
        and frames > 0
    )
    return {
        "passed": passed,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate_hz": sample_rate,
        "frame_count": frames,
        "sha256": _sha256_file(path),
    }


def _load_sealed_client_class() -> type:
    """Load the exact sealed client lazily; flag-off imports stay model-free."""

    if not CANDIDATE_CLIENT_PATH.is_file():
        raise FileNotFoundError("sealed persistent Blackwell client is missing")
    spec = importlib.util.spec_from_file_location(
        "kira_sealed_persistent_blackwell_candidate_client",
        CANDIDATE_CLIENT_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError("sealed persistent Blackwell client could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if Path(str(module.__file__)).resolve() != CANDIDATE_CLIENT_PATH.resolve():
        raise ImportError("persistent Blackwell client resolved to the wrong file")
    return module.PersistentBlackwellVoiceCandidateClient


class PersistentBlackwellVoiceIntegration:
    """Own one exact persistent worker for one shell voice-session owner."""

    def __init__(self, client_factory: Callable[..., Any] | None = None) -> None:
        self._client_factory = client_factory
        self._lock = threading.RLock()
        self._client: Any | None = None
        self._owner = ""
        self._generation = 0
        self._loaded = False
        self._events: list[dict[str, Any]] = []

    def _record(self, event: str, **details: Any) -> dict[str, Any]:
        record = {
            "event": event,
            "wall_time_utc_epoch_seconds": round(time.time(), 6),
            "generation": self._generation,
            "owner": self._owner,
            **details,
        }
        # Only bounded machine facts belong here; no public/private text.
        self._events.append(record)
        del self._events[:-64]
        return dict(record)

    def status(self) -> dict[str, Any]:
        with self._lock:
            process = getattr(self._client, "process", None) if self._client else None
            pid = getattr(process, "pid", None)
            running = bool(process is not None and process.poll() is None)
            return {
                "feature_flag": FEATURE_FLAG,
                "feature_enabled": feature_enabled(),
                "candidate_status": "default_off_pending_live_acceptance",
                "session_owner": self._owner,
                "session_generation": self._generation,
                "owned_worker_running": running,
                "owned_worker_pid": int(pid) if isinstance(pid, int) else None,
                "model_loaded": self._loaded,
                "playback_inside_worker": False,
                "automatic_fallback": "sealed_cpu_only_when_active_candidate_fails",
                "one_shot_route_rollback_preserved": True,
                "events": [dict(item) for item in self._events],
            }

    def begin_session(self, owner: str) -> dict[str, Any]:
        normalized = str(owner or "").strip()
        if not feature_enabled():
            return {
                "begun": False,
                "reason": "persistent_blackwell_feature_flag_disabled",
                **self.status(),
            }
        if not normalized or len(normalized) > 160:
            return {"begun": False, "reason": "invalid_persistent_voice_session_owner"}
        with self._lock:
            if self._owner == normalized:
                return {"begun": True, "reason": "session_already_owned", **self.status()}
            previous_cleanup = self._close_locked("session_owner_changed")
            self._generation += 1
            self._owner = normalized
            self._record(
                "session_begun",
                prior_owned_worker_closed=bool(previous_cleanup.get("owned_worker_was_present")),
            )
            return {"begun": True, "reason": "session_owner_recorded", **self.status()}

    def _new_client_locked(self) -> Any:
        factory = self._client_factory or _load_sealed_client_class()
        return factory(
            allow_gpu_model_load=True,
            startup_timeout_seconds=60.0,
            request_timeout_seconds=900.0,
        )

    @staticmethod
    def _qwen_absence_proven(payload: Any, key: str) -> bool:
        evidence = payload.get(key) if isinstance(payload, dict) else None
        return bool(
            isinstance(evidence, dict)
            and evidence.get("query_succeeded") is True
            and evidence.get("qwen_absent_proven") is True
            and not evidence.get("qwen_records")
            and evidence.get("model_state_changed") is False
        )

    @classmethod
    def _worker_generation_qwen_absence_proven(cls, payload: Any) -> bool:
        checks = payload.get("chunk_checks") if isinstance(payload, dict) else None
        if not isinstance(checks, list) or not checks:
            return False
        for chunk in checks:
            if not isinstance(chunk, dict):
                return False
            accepted_number = chunk.get("accepted_attempt")
            attempts = chunk.get("attempts")
            if not isinstance(attempts, list) or not attempts:
                return False
            accepted = next(
                (
                    item
                    for item in attempts
                    if isinstance(item, dict)
                    and item.get("attempt") == accepted_number
                    and item.get("passed") is True
                    and item.get("output_tensor_was_cuda") is False
                    and item.get("output_tensor_returned_to_host") is True
                    and item.get("official_host_return_contract_satisfied") is True
                ),
                None,
            )
            if accepted is None:
                return False
            qwen = accepted.get("qwen_residency")
            if not cls._qwen_absence_proven(
                {"accepted_generation_qwen": qwen},
                "accepted_generation_qwen",
            ):
                return False
        return True

    def prewarm(self, owner: str) -> dict[str, Any]:
        begun = self.begin_session(owner)
        if begun.get("begun") is not True:
            return {"warmed": False, **begun}
        started = time.perf_counter()
        with self._lock:
            try:
                if self._client is None:
                    self._client = self._new_client_locked()
                    hello = self._client.start()
                    if hello.get("ready") is not True or hello.get("model_loaded") is not False:
                        raise RuntimeError("persistent candidate handshake contract failed")
                else:
                    hello = None
                load_result = self._client.load()
                load_lifecycle = (
                    load_result.get("lifecycle")
                    if isinstance(load_result.get("lifecycle"), dict)
                    else {}
                )
                if (
                    load_result.get("ready") is not True
                    or load_lifecycle.get("model_loaded") is not True
                ):
                    raise RuntimeError("persistent candidate did not prove a loaded CUDA model")
                load_gpu_proof = load_result.get("gpu_proof")
                load_gpu_proof = load_gpu_proof if isinstance(load_gpu_proof, dict) else {}
                required_load_gpu_proof = (
                    "actual_gpu_allocation",
                    "persistent_model_allocation_present",
                    "cuda_synchronize_before_model_load_succeeded",
                    "cuda_synchronize_after_conditioning_succeeded",
                    "model_and_core_components_cuda",
                    "no_rejected_runtime_warnings",
                )
                if not all(load_gpu_proof.get(key) is True for key in required_load_gpu_proof):
                    raise RuntimeError("persistent candidate load CUDA evidence was incomplete")
                if not self._qwen_absence_proven(
                    load_result,
                    "parent_qwen_residency_before_load",
                ):
                    raise RuntimeError("Qwen absence was not proven before persistent prewarm")
                self._loaded = True
                elapsed = round(time.perf_counter() - started, 6)
                self._record(
                    "prewarm_completed",
                    elapsed_seconds=elapsed,
                    client_started=hello is not None,
                    model_reused=bool(load_result.get("model_reused")),
                )
                return {
                    "warmed": True,
                    "ready": True,
                    "reason": "persistent_blackwell_model_ready",
                    "device": "cuda",
                    "sidecar_lifecycle": "session_owned_persistent_candidate",
                    "model_reused": bool(load_result.get("model_reused")),
                    "duration_seconds": elapsed,
                    "playback": False,
                    "generated_audio": False,
                    **self.status(),
                }
            except Exception as exc:
                cleanup = self._close_locked("prewarm_failed")
                self._record("prewarm_failed", error_type=type(exc).__name__)
                return {
                    "warmed": False,
                    "ready": False,
                    "reason": "persistent_blackwell_prewarm_failed",
                    "error_type": type(exc).__name__,
                    "owned_worker_cleanup": cleanup,
                    "playback": False,
                    "generated_audio": False,
                    **self.status(),
                }

    def synthesize(
        self,
        *,
        text: str,
        target: Path,
        pcm_output_gain_db: float,
        proximity_cut_hz: float,
        proximity_cut_mix: float,
    ) -> dict[str, Any]:
        if not feature_enabled():
            return {
                "generated": False,
                "reason": "persistent_blackwell_feature_flag_disabled",
                "persistent_route_eligible": False,
                "playback": False,
            }
        normalized = str(text or "").strip()
        text_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        started = time.perf_counter()
        with self._lock:
            if not self._owner:
                return {
                    "generated": False,
                    "reason": "persistent_blackwell_no_owned_voice_session",
                    "persistent_route_eligible": False,
                    "playback": False,
                }
            try:
                final_target = _safe_project_wav(Path(target))
                if self._client is None or not self._loaded:
                    warm_result = self.prewarm(self._owner)
                    if warm_result.get("warmed") is not True:
                        return {
                            "generated": False,
                            "reason": "persistent_blackwell_lazy_prewarm_failed",
                            "persistent_route_eligible": True,
                            "prewarm": warm_result,
                            "owned_worker_cleanup": warm_result.get(
                                "owned_worker_cleanup",
                                {
                                    "owned_worker_was_present": False,
                                    "owned_worker_closed": True,
                                },
                            ),
                            "playback": False,
                        }
                request_id = uuid.uuid4().hex
                staging = CANDIDATE_STAGING_ROOT / f"session_{self._generation:06d}" / f"{request_id}.wav"
                staging.parent.mkdir(parents=True, exist_ok=True)
                relative = staging.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
                response = self._client.synthesize(
                    text=normalized,
                    output_relative=relative,
                    pcm_output_gain_db=float(pcm_output_gain_db),
                    proximity_cut_hz=float(proximity_cut_hz),
                    proximity_cut_mix=float(proximity_cut_mix),
                )
                issues: list[str] = []
                if response.get("generated") is not True:
                    issues.append("candidate_did_not_generate")
                if response.get("channel") != "public_spoken_only":
                    issues.append("public_spoken_channel_mismatch")
                if response.get("requested_text_bound") is not True:
                    issues.append("requested_text_binding_not_proven")
                if response.get("device") != "cuda":
                    issues.append("device_not_cuda")
                if response.get("text_sha256") != text_hash:
                    issues.append("public_spoken_text_hash_mismatch")
                if response.get("profile_sha256") != APPROVED_PROFILE_SHA256:
                    issues.append("approved_profile_hash_mismatch")
                if response.get("reference_sha256") != APPROVED_REFERENCE_SHA256:
                    issues.append("approved_reference_hash_mismatch")
                if response.get("playback") is not False:
                    issues.append("worker_playback_violation")
                if response.get("generic_voice_used") is not False:
                    issues.append("generic_voice_violation")
                if response.get("sapi_voice_used") is not False:
                    issues.append("sapi_voice_violation")
                if response.get("fallback_used") is not False:
                    issues.append("candidate_internal_fallback_violation")
                gpu_proof = response.get("gpu_proof")
                gpu_proof = gpu_proof if isinstance(gpu_proof, dict) else {}
                if gpu_proof.get("actual_gpu_execution") is not True:
                    issues.append("actual_gpu_execution_not_proven")
                if gpu_proof.get("model_and_core_components_cuda") is not True:
                    issues.append("model_or_core_component_not_proven_cuda")
                if gpu_proof.get("cuda_synchronize_before_generation_succeeded") is not True:
                    issues.append("cuda_synchronize_before_generation_not_proven")
                if gpu_proof.get("cuda_synchronize_after_generation_succeeded") is not True:
                    issues.append("cuda_synchronize_after_generation_not_proven")
                if gpu_proof.get("persistent_model_allocation_present") is not True:
                    issues.append("persistent_gpu_allocation_not_proven")
                if gpu_proof.get("generation_peak_exceeded_baseline") is not True:
                    issues.append("generation_gpu_peak_did_not_exceed_baseline")
                if gpu_proof.get("no_rejected_runtime_warnings") is not True:
                    issues.append("rejected_architecture_or_kernel_warning")
                if gpu_proof.get("qwen_absence_proven_for_accepted_generation") is not True:
                    issues.append("worker_qwen_absence_summary_not_proven")
                if gpu_proof.get("official_host_return_contract_satisfied") is not True:
                    issues.append("official_chatterbox_host_return_not_proven")
                if gpu_proof.get("accepted_output_tensors_host_cpu") is not True:
                    issues.append("accepted_host_cpu_output_not_proven")
                if gpu_proof.get("accepted_output_tensors_cuda") is not False:
                    issues.append("accepted_output_tensors_cuda_truth_violation")
                if not self._qwen_absence_proven(
                    response,
                    "parent_qwen_residency_before_synthesis",
                ):
                    issues.append("qwen_absence_not_proven_before_synthesis")
                if not self._worker_generation_qwen_absence_proven(response):
                    issues.append("qwen_absence_not_proven_for_accepted_generation")
                if not staging.is_file():
                    issues.append("candidate_staging_wav_missing")
                    staging_wav = {}
                else:
                    staging_wav = _validate_wav(staging)
                    if staging_wav.get("passed") is not True:
                        issues.append("candidate_staging_wav_invalid")
                if issues:
                    cleanup = self._close_locked("synthesis_contract_failed")
                    self._record(
                        "synthesis_contract_failed",
                        issue_count=len(issues),
                        text_sha256=text_hash,
                    )
                    return {
                        "generated": False,
                        "reason": "persistent_blackwell_synthesis_contract_failed",
                        "issues": issues,
                        "persistent_route_eligible": True,
                        "owned_worker_cleanup": cleanup,
                        "playback": False,
                    }
                final_target.parent.mkdir(parents=True, exist_ok=True)
                # Both paths are project-owned and on the same volume. Replace
                # is used only after the caller target was proven absent.
                staging.replace(final_target)
                final_wav = _validate_wav(final_target)
                if (
                    final_wav.get("passed") is not True
                    or final_wav.get("sha256") != staging_wav.get("sha256")
                ):
                    cleanup = self._close_locked("final_wav_validation_failed")
                    return {
                        "generated": False,
                        "reason": "persistent_blackwell_final_wav_validation_failed",
                        "persistent_route_eligible": True,
                        "owned_worker_cleanup": cleanup,
                        "playback": False,
                    }
                elapsed = round(time.perf_counter() - started, 6)
                self._record(
                    "synthesis_completed",
                    elapsed_seconds=elapsed,
                    text_sha256=text_hash,
                    wav_sha256=final_wav["sha256"],
                )
                return {
                    **response,
                    "generated": True,
                    "reason": "ok",
                    "route_id": "blackwell_gpu_persistent_candidate",
                    "approved_voice_path_used": "blackwell_gpu",
                    "sidecar_lifecycle": "session_owned_persistent_candidate",
                    "persistent_worker_reused": True,
                    "text": normalized,
                    "text_sha256": text_hash,
                    "audio_path": str(final_target),
                    "wav_validation": final_wav,
                    "staging_promoted_to_caller_target": True,
                    "integration_elapsed_seconds": elapsed,
                    "playback": False,
                    "generic_voice_used": False,
                    "persistent_route_eligible": True,
                }
            except Exception as exc:
                cleanup = self._close_locked("synthesis_exception")
                self._record("synthesis_failed", error_type=type(exc).__name__, text_sha256=text_hash)
                return {
                    "generated": False,
                    "reason": "persistent_blackwell_synthesis_failed",
                    "error_type": type(exc).__name__,
                    "persistent_route_eligible": True,
                    "owned_worker_cleanup": cleanup,
                    "playback": False,
                }

    def _close_locked(self, reason: str) -> dict[str, Any]:
        client = self._client
        self._client = None
        was_loaded = self._loaded
        self._loaded = False
        if client is None:
            return {
                "owned_worker_was_present": False,
                "owned_worker_closed": True,
                "model_was_loaded": was_loaded,
                "reason": reason,
            }
        unload_result: dict[str, Any] | None = None
        close_result: dict[str, Any] | None = None
        unload_error_type = ""
        close_error_type = ""
        try:
            unload_result = client.unload()
        except Exception as exc:
            unload_error_type = type(exc).__name__
        try:
            close_result = client.close()
        except Exception as exc:
            close_error_type = type(exc).__name__
        process = getattr(client, "process", None)
        still_running = bool(process is not None and process.poll() is None)
        return {
            "owned_worker_was_present": True,
            "owned_worker_closed": not still_running,
            "model_was_loaded": was_loaded,
            "unload_reported": isinstance(unload_result, dict),
            "close_reported": isinstance(close_result, dict),
            "owned_process_exit_code": (
                close_result.get("owned_process_exit_code")
                if isinstance(close_result, dict)
                else None
            ),
            "owned_process_forced_termination": bool(
                isinstance(close_result, dict)
                and close_result.get("owned_process_forced_termination")
            ),
            "unload_error_type": unload_error_type,
            "close_error_type": close_error_type,
            "reason": reason,
        }

    def close(self, reason: str = "explicit_release") -> dict[str, Any]:
        with self._lock:
            cleanup = self._close_locked(reason)
            previous_owner = self._owner
            self._owner = ""
            self._record(
                "session_closed",
                previous_owner_present=bool(previous_owner),
                owned_worker_closed=bool(cleanup.get("owned_worker_closed")),
            )
            return {
                "released": bool(cleanup.get("model_was_loaded")),
                "reason": reason,
                "persistent_integration": True,
                "cleanup": cleanup,
                "playback": False,
                "generated_audio": False,
                **self.status(),
            }


_INTEGRATION = PersistentBlackwellVoiceIntegration()


def begin_session(owner: str) -> dict[str, Any]:
    return _INTEGRATION.begin_session(owner)


def prewarm(owner: str) -> dict[str, Any]:
    return _INTEGRATION.prewarm(owner)


def synthesize(
    *,
    text: str,
    target: Path,
    pcm_output_gain_db: float = 0.0,
    proximity_cut_hz: float = 0.0,
    proximity_cut_mix: float = 0.0,
) -> dict[str, Any]:
    return _INTEGRATION.synthesize(
        text=text,
        target=target,
        pcm_output_gain_db=pcm_output_gain_db,
        proximity_cut_hz=proximity_cut_hz,
        proximity_cut_mix=proximity_cut_mix,
    )


def release(reason: str = "explicit_release") -> dict[str, Any]:
    return _INTEGRATION.close(reason)


def status() -> dict[str, Any]:
    return _INTEGRATION.status()


atexit.register(lambda: _INTEGRATION.close("python_process_exit"))
