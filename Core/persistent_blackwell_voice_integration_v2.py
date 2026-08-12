"""Default-off host integration for the accepted persistent Blackwell v2 candidate.

The normal one-shot Blackwell route and sealed-CPU fallback remain production
truth.  This module is deliberately separate from ``Core.voice_output`` and
does not play audio, promote a route, or provide SAPI/generic fallback.  It
binds the exact inactive v2 package to the exact append-only full-GPU
engineering-pass report so a later owner-heard acceptance can exercise a
session-owned worker without changing production routing.
"""

from __future__ import annotations

import atexit
import array
import hashlib
import importlib
import json
import math
import os
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

if __package__:
    from . import persistent_blackwell_voice_integration as _v1
else:  # Direct ``Core`` imports used by older launchers/tests.
    import persistent_blackwell_voice_integration as _v1


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_PACKAGE = "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v2"
CANDIDATE_CLIENT_MODULE = f"{CANDIDATE_PACKAGE}.candidate_client"
CANDIDATE_ROOT = (
    PROJECT_ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate_v2"
)
CANDIDATE_CLIENT_PATH = CANDIDATE_ROOT / "candidate_client.py"
CANDIDATE_STAGING_ROOT = (
    PROJECT_ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "runtime_integration_staging_v2"
)
FULL_GPU_PASS_REPORT_PATH = (
    PROJECT_ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "full_gpu_v2"
    / "attempt_02"
    / "FINAL_REPORT.json"
)
FULL_GPU_PASS_REPORT_SHA256 = (
    "40771bb8961a09a9e627e2c8b3a0d80da18dbb3199aea900912c56ceefc7d339"
)
FEATURE_FLAG = "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2"
APPROVED_PROFILE_SHA256 = _v1.APPROVED_PROFILE_SHA256
APPROVED_REFERENCE_SHA256 = _v1.APPROVED_REFERENCE_SHA256
APPROVED_PROFILE_PATH = PROJECT_ROOT / "Voice" / "profiles" / "temp_ai" / "kira_voice_profile.json"
APPROVED_REFERENCE_PATH = (
    PROJECT_ROOT
    / "Voice"
    / "reference_packs"
    / "kira"
    / "kira_online_source_20260706_221447"
    / "model_input"
    / "approved_reference.wav"
)
PRODUCTION_ROUTING_PATH = PROJECT_ROOT / "Voice" / "sidecars" / "kira_approved_voice_routing.json"
PRODUCTION_ROUTING_SHA256 = (
    "a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81"
)
GENERATED_AUDIO_ROOT = PROJECT_ROOT / "Voice" / "generated"
WORKER_IDLE_UNLOAD_SECONDS = 600.0
SEALED_ARTIFACTS = {
    "candidate_config": (
        CANDIDATE_ROOT / "candidate_config.json",
        "805c1d2836c618970a81f5f44d31f81f67e204173bd919857452daa8dbedc8bb",
    ),
    "candidate_contract": (
        CANDIDATE_ROOT / "candidate_contract.py",
        "863c6ece050b12af157565c60df6fd82b207dae5476e693cc08e34b392c8f910",
    ),
    "candidate_client": (
        CANDIDATE_CLIENT_PATH,
        "9f33ef0d9fd969da05ce48eb148163efc77306bfd3bc215efcb482e68e7261a8",
    ),
    "candidate_worker": (
        CANDIDATE_ROOT / "persistent_worker.py",
        "b6f2dcc816537552db02d00c5a1932057f2d99b5d206a578344d4a92523b3cad",
    ),
    "approved_profile": (APPROVED_PROFILE_PATH, APPROVED_PROFILE_SHA256),
    "approved_reference": (APPROVED_REFERENCE_PATH, APPROVED_REFERENCE_SHA256),
    "production_routing_manifest": (PRODUCTION_ROUTING_PATH, PRODUCTION_ROUTING_SHA256),
}


def _explicit_true(value: Any) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "on"}


def feature_enabled() -> bool:
    """Return only the explicit v2 flag state; every other value fails closed."""

    return _explicit_true(os.environ.get(FEATURE_FLAG, "0"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _acceptance_binding() -> dict[str, Any]:
    """Validate exact accepted code/data before any candidate-code import."""

    if not FULL_GPU_PASS_REPORT_PATH.is_file():
        raise FileNotFoundError("persistent Blackwell v2 acceptance report is missing")
    actual_hash = _sha256_file(FULL_GPU_PASS_REPORT_PATH)
    if actual_hash != FULL_GPU_PASS_REPORT_SHA256:
        raise RuntimeError("persistent Blackwell v2 acceptance report hash mismatch")
    payload = json.loads(FULL_GPU_PASS_REPORT_PATH.read_text(encoding="utf-8"))
    required = {
        "engineering_pass": True,
        "status": "engineering_pass_pending_owner_heard_acceptance",
        "promotion_performed": False,
        "routing_change_performed": False,
        "playback_performed": False,
        "candidate_remains_inactive": True,
        "owner_heard_acceptance": False,
        "promotion_eligible": False,
    }
    mismatches = [key for key, value in required.items() if payload.get(key) != value]
    if mismatches:
        raise RuntimeError(
            "persistent Blackwell v2 acceptance truth mismatch: " + ", ".join(mismatches)
        )
    report_sealed = payload.get("sealed_artifact_hashes")
    report_sealed = report_sealed if isinstance(report_sealed, dict) else {}
    report_protected = payload.get("protected_before")
    report_protected = report_protected if isinstance(report_protected, dict) else {}
    artifact_hashes: dict[str, str] = {}
    artifact_paths: dict[str, str] = {}
    for artifact_id, (path, expected_hash) in SEALED_ARTIFACTS.items():
        if not path.is_file():
            raise FileNotFoundError(f"persistent Blackwell v2 artifact missing: {artifact_id}")
        actual_artifact_hash = _sha256_file(path)
        if actual_artifact_hash != expected_hash:
            raise RuntimeError(f"persistent Blackwell v2 artifact hash mismatch: {artifact_id}")
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        if report_protected.get(relative) != expected_hash:
            raise RuntimeError(
                f"persistent Blackwell v2 report binding mismatch: {artifact_id}"
            )
        sealed_report_hash = report_sealed.get(artifact_id)
        if sealed_report_hash is not None and sealed_report_hash != expected_hash:
            raise RuntimeError(
                f"persistent Blackwell v2 sealed report mismatch: {artifact_id}"
            )
        artifact_hashes[artifact_id] = actual_artifact_hash
        artifact_paths[artifact_id] = relative
    return {
        "valid": True,
        "path": FULL_GPU_PASS_REPORT_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": actual_hash,
        "engineering_pass": True,
        "owner_heard_acceptance": False,
        "promotion_eligible": False,
        "sealed_artifact_hashes": artifact_hashes,
        "sealed_artifact_paths": artifact_paths,
    }


def _load_sealed_client_class() -> type:
    """Package-import only the exact v2 client; no heavy model import occurs."""

    _acceptance_binding()
    if not CANDIDATE_CLIENT_PATH.is_file():
        raise FileNotFoundError("sealed persistent Blackwell v2 client is missing")
    module = importlib.import_module(CANDIDATE_CLIENT_MODULE)
    if Path(str(module.__file__)).resolve() != CANDIDATE_CLIENT_PATH.resolve():
        raise ImportError("persistent Blackwell v2 client resolved to the wrong file")
    client_class = getattr(module, "PersistentBlackwellVoiceCandidateClient", None)
    if not isinstance(client_class, type):
        raise ImportError("persistent Blackwell v2 client class is missing")
    return client_class


def _safe_generated_wav(path: Path) -> Path:
    target = Path(path).resolve()
    target.relative_to(GENERATED_AUDIO_ROOT.resolve())
    if target.suffix.casefold() != ".wav":
        raise ValueError("persistent voice v2 target must be a generated-audio WAV")
    if target.exists():
        raise FileExistsError("persistent voice v2 refuses to overwrite a WAV")
    return target


def _owned_cleanup_proven(cleanup: Any) -> bool:
    return bool(isinstance(cleanup, dict) and cleanup.get("owned_worker_closed") is True)


def _validate_non_silent_wav(path: Path) -> dict[str, Any]:
    import wave

    with wave.open(str(path), "rb") as reader:
        channels = int(reader.getnchannels())
        sample_width = int(reader.getsampwidth())
        sample_rate = int(reader.getframerate())
        frames = int(reader.getnframes())
        payload = reader.readframes(frames)
    if sample_width != 2:
        raise ValueError("persistent voice v2 WAV must be PCM16")
    samples = array.array("h")
    samples.frombytes(payload[: len(payload) - (len(payload) % 2)])
    if sys.byteorder != "little":
        samples.byteswap()
    peak = max((abs(int(value)) for value in samples), default=0) / 32767.0
    rms = (
        math.sqrt(sum(float(value) ** 2 for value in samples) / len(samples)) / 32767.0
        if samples
        else 0.0
    )
    duration = frames / sample_rate if sample_rate else 0.0
    non_silent = peak >= 0.001 and rms >= 0.0001
    passed = bool(
        path.is_file()
        and path.stat().st_size > 44
        and channels == 1
        and sample_rate >= 8000
        and duration >= 0.1
        and non_silent
    )
    return {
        "passed": passed,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate_hz": sample_rate,
        "frame_count": frames,
        "duration_seconds": round(duration, 6),
        "peak_normalized": round(peak, 8),
        "rms_normalized": round(rms, 8),
        "non_silent": non_silent,
        "sha256": _sha256_file(path),
    }


class PersistentBlackwellVoiceIntegrationV2(_v1.PersistentBlackwellVoiceIntegration):
    """Own one exact v2 worker for one explicit host voice-session owner."""

    def __init__(self, client_factory: Callable[..., Any] | None = None) -> None:
        super().__init__(client_factory=client_factory)
        self._operation_lock = threading.Lock()
        self._operation_in_flight = False
        self._operation_name = ""
        self._operation_client: Any | None = None
        # This counter identifies replacement of the host-owned client/worker
        # transport.  It intentionally does not change when only the CUDA
        # model is unloaded and later loaded again on the same worker.
        self._client_generation = 0
        self._test_client_injected = client_factory is not None
        self._last_load_telemetry: dict[str, Any] = {}
        self._last_load_verified_monotonic = 0.0
        self._cleanup_debt = False

    def _binding_failure_cleanup(self, reason: str) -> dict[str, Any] | None:
        with self._lock:
            present = bool(self._client is not None or self._owner or self._loaded)
        return self.close(reason).get("cleanup") if present else None

    @staticmethod
    def _abort_exact_owned_client(client: Any, reason: str) -> dict[str, Any]:
        process = getattr(client, "process", None)
        if process is None:
            return {
                "owned_worker_was_present": False,
                "owned_worker_closed": True,
                "forced_for_inflight_operation": False,
                "reason": reason,
            }
        forced = False
        try:
            running = process.poll() is None
        except Exception:
            running = True
        if running:
            forced = True
            try:
                if getattr(process, "stdin", None) is not None:
                    process.stdin.close()
            except Exception:
                pass
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                    process.wait(timeout=5)
                except Exception:
                    pass
        for stream_name in ("stdin", "stdout", "stderr"):
            try:
                stream = getattr(process, stream_name, None)
                if stream is not None:
                    stream.close()
            except Exception:
                pass
        for thread_name in ("_stdout_thread", "_stderr_thread"):
            thread = getattr(client, thread_name, None)
            if isinstance(thread, threading.Thread) and thread.is_alive():
                thread.join(timeout=2)
        try:
            closed = process.poll() is not None
        except Exception:
            closed = False
        return {
            "owned_worker_was_present": True,
            "owned_worker_closed": closed,
            "forced_for_inflight_operation": forced,
            "owned_process_exit_code": getattr(process, "returncode", None),
            "reason": reason,
        }

    @staticmethod
    def _safe_unload_telemetry(unload_result: Any) -> dict[str, Any]:
        result = unload_result if isinstance(unload_result, dict) else {}
        lifecycle = result.get("lifecycle")
        lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
        last_unload = lifecycle.get("last_unload")
        last_unload = last_unload if isinstance(last_unload, dict) else {}
        transport = result.get("parent_transport_timing")
        transport = transport if isinstance(transport, dict) else {}
        return {
            "reported": isinstance(unload_result, dict),
            "unloaded": result.get("unloaded") is True,
            "model_was_loaded": result.get("model_was_loaded") is True,
            "operation_seconds": result.get("operation_seconds"),
            "parent_transport_timing": {
                key: transport.get(key)
                for key in (
                    "request_submitted_monotonic_ns",
                    "response_received_monotonic_ns",
                    "elapsed_seconds",
                )
            },
            "lifecycle_model_loaded_after": lifecycle.get("model_loaded"),
            "last_unload": {
                key: last_unload.get(key)
                for key in (
                    "was_loaded",
                    "operation_seconds",
                    "allocated_before_bytes",
                    "allocated_after_bytes",
                    "allocated_returned_bytes",
                    "reserved_before_bytes",
                    "reserved_after_bytes",
                    "reserved_returned_bytes",
                )
            },
        }

    @staticmethod
    def _suspend_contract_issues(unload_result: Any) -> list[str]:
        """Require the worker to prove that its GPU model is no longer loaded."""

        result = unload_result if isinstance(unload_result, dict) else {}
        lifecycle = result.get("lifecycle")
        lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
        issues: list[str] = []
        if not isinstance(unload_result, dict):
            issues.append("unload_response_not_object")
        if result.get("unloaded") is not True:
            issues.append("unload_not_confirmed")
        if not isinstance(result.get("model_was_loaded"), bool):
            issues.append("model_was_loaded_truth_missing")
        if lifecycle.get("model_loaded") is not False:
            issues.append("worker_model_absence_not_proven")
        return issues

    def suspend_if_owner(
        self,
        expected_owner: str,
        reason: str = "owner_bound_model_only_suspend",
        *,
        expected_generation: int,
        timeout_seconds: float = 20.0,
    ) -> dict[str, Any]:
        """Boundedly unload one exact owner-generation model and retain its worker."""

        normalized_owner = str(expected_owner or "").strip()
        generation_valid = bool(
            isinstance(expected_generation, int)
            and not isinstance(expected_generation, bool)
            and expected_generation >= 0
        )
        try:
            bound_seconds = max(0.05, min(60.0, float(timeout_seconds)))
        except (TypeError, ValueError):
            bound_seconds = 20.0
        started = time.perf_counter()

        def result_base() -> dict[str, Any]:
            return {
                "requested_reason": reason,
                "suspend_bound_seconds": bound_seconds,
                "arbitrary_process_termination_performed": False,
                "playback": False,
                "generated_audio": False,
                "generic_voice_used": False,
                "sapi_voice_used": False,
            }

        with self._lock:
            owner_matched = bool(normalized_owner and self._owner == normalized_owner)
            generation_matched = bool(
                generation_valid and self._generation == expected_generation
            )
            if not owner_matched or not generation_matched:
                return {
                    **result_base(),
                    "suspended": False,
                    "ready_for_text_generation": False,
                    "model_release_proven": False,
                    "owner_matched": owner_matched,
                    "generation_matched": generation_matched,
                    "expected_generation_valid": generation_valid,
                    "reason": "persistent_blackwell_v2_owner_or_generation_no_longer_matches",
                    "suspend_attempted": False,
                    "session_owner_preserved": False,
                    "session_generation_preserved": False,
                    "duration_seconds": round(time.perf_counter() - started, 6),
                }

        operation_lock_acquired = self._operation_lock.acquire(timeout=bound_seconds)
        if not operation_lock_acquired:
            # A synthesis/prewarm owns the operation lock.  Revalidate and
            # abort only its exact session-owned child; never scan processes.
            with self._lock:
                session_matches = bool(
                    self._owner == normalized_owner
                    and self._generation == expected_generation
                )
                client = self._client if session_matches else None
                recovery = (
                    self._abort_exact_owned_client(
                        client, "model_only_suspend_wait_exceeded_bound"
                    )
                    if client is not None
                    else None
                )
                release_proven = bool(
                    isinstance(recovery, dict)
                    and recovery.get("owned_worker_was_present") is True
                    and recovery.get("owned_worker_closed") is True
                )
                if release_proven:
                    self._client = None
                    self._loaded = False
                    self._last_load_verified_monotonic = 0.0
                    self._cleanup_debt = False
                elif client is not None:
                    self._loaded = False
                    self._last_load_verified_monotonic = 0.0
                    self._cleanup_debt = True
                owner_preserved = self._owner == normalized_owner
                generation_preserved = self._generation == expected_generation
                session_preserved = owner_preserved and generation_preserved
                self._record(
                    "v2_model_suspend_wait_timed_out",
                    model_release_proven=release_proven,
                    owner_present=owner_preserved,
                    generation_present=generation_preserved,
                )
            return {
                **result_base(),
                "suspended": False,
                "ready_for_text_generation": release_proven and session_preserved,
                "model_release_proven": release_proven,
                "owner_matched": owner_preserved,
                "generation_matched": generation_preserved,
                "reason": (
                    "persistent_blackwell_v2_exact_worker_closed_after_suspend_wait_timeout"
                    if release_proven
                    else "persistent_blackwell_v2_suspend_wait_timeout_not_proven"
                ),
                "suspend_attempted": False,
                "operation_lock_acquired": False,
                "suspend_contract_issues": ["operation_lock_wait_timed_out"],
                "session_owner_preserved": owner_preserved,
                "session_generation_preserved": generation_preserved,
                "owned_worker_preserved": False,
                "exact_owned_worker_closed_for_recovery": release_proven,
                "exact_owned_worker_recovery": recovery,
                "duration_seconds": round(time.perf_counter() - started, 6),
            }

        try:
            with self._lock:
                owner_matched = self._owner == normalized_owner
                generation_matched = self._generation == expected_generation
                if not owner_matched or not generation_matched:
                    return {
                        **result_base(),
                        "suspended": False,
                        "ready_for_text_generation": False,
                        "model_release_proven": False,
                        "owner_matched": owner_matched,
                        "generation_matched": generation_matched,
                        "reason": "persistent_blackwell_v2_owner_or_generation_changed_before_suspend",
                        "suspend_attempted": False,
                        "operation_lock_acquired": True,
                        "session_owner_preserved": False,
                        "session_generation_preserved": False,
                        "duration_seconds": round(time.perf_counter() - started, 6),
                    }
                client = self._client
                process = getattr(client, "process", None) if client else None
                try:
                    worker_was_running = bool(
                        process is not None and process.poll() is None
                    )
                except Exception:
                    worker_was_running = bool(process is not None)
                model_was_loaded = bool(self._loaded and worker_was_running)
                if self._cleanup_debt:
                    return {
                        **result_base(),
                        "suspended": False,
                        "ready_for_text_generation": False,
                        "model_release_proven": False,
                        "owner_matched": True,
                        "reason": "persistent_blackwell_v2_cleanup_debt_blocks_suspend",
                        "suspend_attempted": False,
                        "operation_lock_acquired": True,
                        "model_was_loaded": model_was_loaded,
                        "session_owner_preserved": True,
                        "session_generation_preserved": True,
                        "owned_worker_preserved": worker_was_running,
                        "duration_seconds": round(time.perf_counter() - started, 6),
                    }
                if client is None or not worker_was_running:
                    if client is not None:
                        self._client = None
                    self._loaded = False
                    self._last_load_verified_monotonic = 0.0
                    self._record(
                        "v2_model_suspend_completed",
                        model_was_loaded=model_was_loaded,
                        owned_worker_preserved=False,
                    )
                    return {
                        **result_base(),
                        "suspended": True,
                        "ready_for_text_generation": True,
                        "model_release_proven": True,
                        "owner_matched": True,
                        "reason": "persistent_blackwell_v2_model_already_absent",
                        "suspend_attempted": False,
                        "operation_lock_acquired": True,
                        "model_was_loaded": model_was_loaded,
                        "session_owner_preserved": True,
                        "session_generation_preserved": True,
                        "owned_worker_preserved": False,
                        "worker_was_running": worker_was_running,
                        "owned_worker_running_after": False,
                        "exact_owned_worker_closed_for_recovery": False,
                        "duration_seconds": round(time.perf_counter() - started, 6),
                    }
                self._mark_operation_locked(client, "model_only_suspend")

            operation: dict[str, Any] = {"unload_result": None, "error_type": ""}

            def bounded_unload() -> None:
                try:
                    operation["unload_result"] = client.unload()
                except Exception as exc:
                    operation["error_type"] = type(exc).__name__

            unload_thread = threading.Thread(
                target=bounded_unload,
                name="persistent-blackwell-v2-model-only-suspend",
                daemon=True,
            )
            unload_thread.start()
            unload_thread.join(timeout=bound_seconds)
            timed_out = unload_thread.is_alive()
            unload_result = operation.get("unload_result")
            issues = (
                ["unload_timed_out"]
                if timed_out
                else self._suspend_contract_issues(unload_result)
            )
            if operation.get("error_type"):
                issues.append("unload_request_failed")

            with self._lock:
                attached = (
                    self._client is client
                    and self._owner == normalized_owner
                    and self._generation == expected_generation
                )
                self._finish_operation_locked(client)
                process = getattr(client, "process", None)
                try:
                    worker_running_after = bool(
                        process is not None and process.poll() is None
                    )
                except Exception:
                    worker_running_after = bool(process is not None)
                if not attached:
                    issues.append("session_or_worker_changed_during_suspend")
                if not issues and worker_running_after:
                    self._loaded = False
                    self._last_load_verified_monotonic = 0.0
                    self._cleanup_debt = False
                    self._record(
                        "v2_model_suspend_completed",
                        model_was_loaded=model_was_loaded,
                        owned_worker_preserved=True,
                    )
                    return {
                        **result_base(),
                        "suspended": True,
                        "ready_for_text_generation": True,
                        "model_release_proven": True,
                        "owner_matched": True,
                        "reason": "persistent_blackwell_v2_model_suspended",
                        "suspend_attempted": True,
                        "operation_lock_acquired": True,
                        "model_was_loaded": model_was_loaded,
                        "unload_telemetry": self._safe_unload_telemetry(unload_result),
                        "suspend_contract_issues": [],
                        "suspend_thread_finished": True,
                        "session_owner_preserved": True,
                        "session_generation_preserved": True,
                        "owned_worker_preserved": True,
                        "worker_was_running": True,
                        "owned_worker_running_after": True,
                        "exact_owned_worker_closed_for_recovery": False,
                        "duration_seconds": round(time.perf_counter() - started, 6),
                    }

                recovery = None
                if attached:
                    recovery = self._abort_exact_owned_client(
                        client, "model_only_suspend_contract_not_proven"
                    )
                    if recovery.get("owned_worker_closed") is True:
                        self._client = None
                        self._loaded = False
                        self._last_load_verified_monotonic = 0.0
                        self._cleanup_debt = False
                    else:
                        self._loaded = False
                        self._last_load_verified_monotonic = 0.0
                        self._cleanup_debt = True
                unload_thread.join(timeout=3.0)
                release_proven = bool(
                    attached
                    and isinstance(recovery, dict)
                    and recovery.get("owned_worker_closed") is True
                )
                owner_preserved = self._owner == normalized_owner
                generation_preserved = self._generation == expected_generation
                session_preserved = owner_preserved and generation_preserved
                self._record(
                    "v2_model_suspend_recovered" if release_proven else "v2_model_suspend_failed",
                    issue_count=len(issues),
                    model_release_proven=release_proven,
                    owner_present=owner_preserved,
                    generation_present=generation_preserved,
                )
                return {
                    **result_base(),
                    "suspended": False,
                    "ready_for_text_generation": release_proven and session_preserved,
                    "model_release_proven": release_proven,
                    "owner_matched": owner_preserved,
                    "generation_matched": generation_preserved,
                    "reason": (
                        "persistent_blackwell_v2_exact_worker_closed_after_suspend_failure"
                        if release_proven
                        else "persistent_blackwell_v2_model_suspend_not_proven"
                    ),
                    "suspend_attempted": True,
                    "operation_lock_acquired": True,
                    "model_was_loaded": model_was_loaded,
                    "unload_telemetry": self._safe_unload_telemetry(unload_result),
                    "unload_error_type": str(operation.get("error_type") or ""),
                    "suspend_contract_issues": issues,
                    "suspend_thread_finished": not unload_thread.is_alive(),
                    "session_owner_preserved": owner_preserved,
                    "session_generation_preserved": generation_preserved,
                    "owned_worker_preserved": False,
                    "worker_was_running": True,
                    "owned_worker_running_after": not release_proven,
                    "exact_owned_worker_closed_for_recovery": release_proven,
                    "exact_owned_worker_recovery": recovery,
                    "duration_seconds": round(time.perf_counter() - started, 6),
                }
        finally:
            self._operation_lock.release()

    def _close_locked(self, reason: str) -> dict[str, Any]:
        client = self._client
        was_loaded = self._loaded
        if client is None:
            self._loaded = False
            self._last_load_verified_monotonic = 0.0
            self._cleanup_debt = False
            return {
                "owned_worker_was_present": False,
                "owned_worker_closed": True,
                "model_was_loaded": was_loaded,
                "reason": reason,
            }
        in_flight = self._operation_in_flight and self._operation_client is client
        if in_flight:
            cleanup = self._abort_exact_owned_client(client, reason)
            cleanup["model_was_loaded"] = was_loaded
            cleanup["host_last_known_model_loaded"] = was_loaded
            if cleanup.get("owned_worker_closed") is True:
                self._client = None
                self._loaded = False
                self._last_load_verified_monotonic = 0.0
                self._cleanup_debt = False
            else:
                self._client = client
                self._loaded = False
                self._last_load_verified_monotonic = 0.0
                self._cleanup_debt = True
            return cleanup
        graceful: dict[str, Any] = {
            "unload_result": None,
            "close_result": None,
            "unload_error_type": "",
            "close_error_type": "",
        }

        def graceful_cleanup() -> None:
            try:
                graceful["unload_result"] = client.unload()
            except Exception as exc:
                graceful["unload_error_type"] = type(exc).__name__
            try:
                graceful["close_result"] = client.close()
            except Exception as exc:
                graceful["close_error_type"] = type(exc).__name__

        cleanup_thread = threading.Thread(
            target=graceful_cleanup,
            name="persistent-blackwell-v2-bounded-cleanup",
            daemon=True,
        )
        cleanup_thread.start()
        cleanup_thread.join(timeout=20.0)
        forced_idle_cleanup: dict[str, Any] | None = None
        if cleanup_thread.is_alive():
            forced_idle_cleanup = self._abort_exact_owned_client(
                client, "idle_cleanup_exceeded_20_seconds"
            )
            cleanup_thread.join(timeout=3.0)
        unload_result = graceful.get("unload_result")
        close_result = graceful.get("close_result")
        unload_error_type = str(graceful.get("unload_error_type") or "")
        close_error_type = str(graceful.get("close_error_type") or "")
        process = getattr(client, "process", None)
        still_running = bool(process is not None and process.poll() is None)
        worker_model_was_loaded = (
            unload_result.get("model_was_loaded") is True
            if isinstance(unload_result, dict)
            and "model_was_loaded" in unload_result
            else was_loaded
        )
        cleanup = {
            "owned_worker_was_present": True,
            "owned_worker_closed": not still_running,
            "model_was_loaded": worker_model_was_loaded,
            "host_last_known_model_loaded": was_loaded,
            "unload_reported": isinstance(unload_result, dict),
            "unload_telemetry": self._safe_unload_telemetry(unload_result),
            "close_reported": isinstance(close_result, dict),
            "owned_process_exit_code": (
                close_result.get("owned_process_exit_code")
                if isinstance(close_result, dict)
                else None
            ),
            "owned_process_forced_termination": bool(
                isinstance(close_result, dict)
                and close_result.get("owned_process_forced_termination")
            ) or bool(forced_idle_cleanup and forced_idle_cleanup.get("forced_for_inflight_operation")),
            "unload_error_type": unload_error_type,
            "close_error_type": close_error_type,
            "forced_for_inflight_operation": False,
            "forced_for_unresponsive_idle_cleanup": forced_idle_cleanup is not None,
            "cleanup_thread_finished": not cleanup_thread.is_alive(),
            "graceful_cleanup_bound_seconds": 20.0,
            "reason": reason,
        }
        if cleanup["owned_worker_closed"] is True:
            self._client = None
            self._loaded = False
            self._last_load_verified_monotonic = 0.0
            self._cleanup_debt = False
        else:
            # Retain the exact process handle and owner as cleanup debt.  No
            # later session may load a second worker until closure is proved.
            self._client = client
            self._loaded = False
            self._last_load_verified_monotonic = 0.0
            self._cleanup_debt = True
        return cleanup

    def close(self, reason: str = "explicit_release") -> dict[str, Any]:
        with self._lock:
            cleanup = self._close_locked(reason)
            previous_owner = self._owner
            if cleanup.get("owned_worker_closed") is True:
                self._owner = ""
            self._record(
                "v2_session_closed",
                previous_owner_present=bool(previous_owner),
                owned_worker_closed=bool(cleanup.get("owned_worker_closed")),
            )
        return {
            "released": bool(
                cleanup.get("model_was_loaded")
                and cleanup.get("owned_worker_closed") is True
            ),
            "release_attempted": bool(
                cleanup.get("owned_worker_was_present")
                or cleanup.get("model_was_loaded")
            ),
            "model_was_loaded": bool(cleanup.get("model_was_loaded")),
            "reason": reason,
            "persistent_integration": True,
            "cleanup": cleanup,
            "playback": False,
            "generated_audio": False,
            **self.status(),
        }

    def close_if_owner(self, expected_owner: str, reason: str) -> dict[str, Any]:
        """Close only the exact v2 session owner captured by the caller.

        The owner comparison and detachment happen under the integration lock,
        so a delayed session-end thread cannot unload a newer session.
        """

        normalized = str(expected_owner or "").strip()
        with self._lock:
            if not normalized or self._owner != normalized:
                return {
                    "released": False,
                    "release_attempted": False,
                    "owner_matched": False,
                    "expected_owner_present": bool(normalized),
                    "reason": "persistent_v2_owner_no_longer_matches",
                    "persistent_integration": True,
                    "cleanup": None,
                    "playback": False,
                    "generated_audio": False,
                    **self.status(),
                }
            cleanup = self._close_locked(reason)
            if cleanup.get("owned_worker_closed") is True:
                self._owner = ""
            self._record(
                "v2_owner_bound_session_closed",
                previous_owner_present=True,
                owned_worker_closed=bool(cleanup.get("owned_worker_closed")),
            )
            return {
                "released": bool(
                    cleanup.get("model_was_loaded")
                    and cleanup.get("owned_worker_closed") is True
                ),
                "release_attempted": True,
                "model_was_loaded": bool(cleanup.get("model_was_loaded")),
                "owner_matched": True,
                "expected_owner_present": True,
                "reason": reason,
                "persistent_integration": True,
                "cleanup": cleanup,
                "playback": False,
                "generated_audio": False,
                **self.status(),
            }

    def status(self) -> dict[str, Any]:
        with self._lock:
            process = getattr(self._client, "process", None) if self._client else None
            pid = getattr(process, "pid", None)
            running = bool(process is not None and process.poll() is None)
            worker_session_id = str(
                getattr(self._client, "session_id", "") if self._client else ""
            ).strip()
            if not running:
                self._loaded = False
                self._last_load_verified_monotonic = 0.0
            verification_age = (
                max(0.0, time.monotonic() - self._last_load_verified_monotonic)
                if self._last_load_verified_monotonic > 0.0
                else None
            )
            load_within_idle_bound = bool(
                running
                and self._loaded
                and verification_age is not None
                and verification_age < WORKER_IDLE_UNLOAD_SECONDS
            )
            try:
                acceptance = _acceptance_binding()
            except Exception as exc:
                acceptance = {"valid": False, "error_type": type(exc).__name__}
            binding_valid = acceptance.get("valid") is True
            candidate_status = (
                "test_only_injected_client_not_route_evidence"
                if self._test_client_injected
                else "default_off_engineering_pass_pending_owner_heard_acceptance"
                if binding_valid
                else "blocked_acceptance_or_artifact_binding_invalid"
            )
            return {
                "feature_flag": FEATURE_FLAG,
                "feature_enabled": feature_enabled(),
                "candidate_id": "kira_chatterbox_blackwell_persistent_eager_cuda_candidate_v2",
                "candidate_status": candidate_status,
                "candidate_package": CANDIDATE_PACKAGE,
                "full_gpu_acceptance": acceptance,
                "session_owner": self._owner,
                "session_generation": self._generation,
                "owned_worker_running": running,
                "owned_worker_pid": int(pid) if isinstance(pid, int) else None,
                "owned_worker_session_id": worker_session_id if running else "",
                "owned_client_generation": (
                    self._client_generation if self._client is not None else None
                ),
                "model_loaded": load_within_idle_bound,
                "model_loaded_verification": (
                    "worker_load_response_within_sealed_idle_bound"
                    if load_within_idle_bound
                    else "not_currently_proven"
                ),
                "model_loaded_verification_age_seconds": (
                    round(verification_age, 6)
                    if verification_age is not None
                    else None
                ),
                "worker_idle_unload_bound_seconds": WORKER_IDLE_UNLOAD_SECONDS,
                "host_last_known_model_loaded": bool(self._loaded and running),
                "cleanup_debt": self._cleanup_debt,
                "operation_in_flight": self._operation_in_flight,
                "operation_name": self._operation_name,
                "test_client_injected": self._test_client_injected,
                "playback_inside_worker": False,
                "generic_voice_allowed": False,
                "sapi_voice_allowed": False,
                "automatic_fallback": "sealed_cpu_only_outside_candidate_after_host_route_failure",
                "host_application_route_connected": False,
                "production_route_promoted": False,
                "routing_manifest_preserved": binding_valid,
                "one_shot_route_rollback_preserved": binding_valid,
                "events": [dict(item) for item in self._events],
            }

    def begin_session(self, owner: str) -> dict[str, Any]:
        normalized = str(owner or "").strip()
        if not feature_enabled():
            cleanup = self._binding_failure_cleanup("v2_feature_flag_disabled")
            return {
                "begun": False,
                "reason": "persistent_blackwell_v2_feature_flag_disabled",
                "owned_worker_cleanup": cleanup,
                **self.status(),
            }
        try:
            _acceptance_binding()
        except Exception as exc:
            cleanup = self._binding_failure_cleanup("v2_acceptance_binding_failed")
            return {
                "begun": False,
                "reason": "persistent_blackwell_v2_acceptance_binding_failed",
                "error_type": type(exc).__name__,
                "owned_worker_cleanup": cleanup,
                **self.status(),
            }
        if not normalized or len(normalized) > 160:
            return {"begun": False, "reason": "invalid_persistent_voice_v2_session_owner"}
        with self._lock:
            if self._cleanup_debt:
                debt_cleanup = self._close_locked(
                    "retry_cleanup_debt_before_new_session"
                )
                if debt_cleanup.get("owned_worker_closed") is not True:
                    return {
                        "begun": False,
                        "reason": "persistent_blackwell_v2_cleanup_debt_not_closed",
                        "owned_worker_cleanup": debt_cleanup,
                        **self.status(),
                    }
                self._owner = ""
            if self._owner == normalized:
                return {"begun": True, "reason": "session_already_owned", **self.status()}
            previous_cleanup = self._close_locked("session_owner_changed")
            if previous_cleanup.get("owned_worker_closed") is not True:
                self._cleanup_debt = True
                return {
                    "begun": False,
                    "reason": "persistent_blackwell_v2_prior_owner_cleanup_not_proven",
                    "owned_worker_cleanup": previous_cleanup,
                    **self.status(),
                }
            self._generation += 1
            self._owner = normalized
            self._record(
                "v2_session_begun",
                prior_owned_worker_closed=bool(previous_cleanup.get("owned_worker_closed")),
            )
            return {"begun": True, "reason": "v2_session_owner_recorded", **self.status()}

    def _new_client_locked(self) -> Any:
        _acceptance_binding()
        factory = self._client_factory or _load_sealed_client_class()
        return factory(
            allow_gpu_model_load=True,
            startup_timeout_seconds=60.0,
            request_timeout_seconds=900.0,
        )

    def _mark_operation_locked(self, client: Any, name: str) -> None:
        self._operation_in_flight = True
        self._operation_name = name
        self._operation_client = client

    def _finish_operation_locked(self, client: Any) -> None:
        if self._operation_client is client:
            self._operation_in_flight = False
            self._operation_name = ""
            self._operation_client = None

    @classmethod
    def _load_contract_issues(cls, load_result: Any) -> list[str]:
        result = load_result if isinstance(load_result, dict) else {}
        lifecycle = result.get("lifecycle")
        lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
        gpu = result.get("gpu_proof")
        gpu = gpu if isinstance(gpu, dict) else {}
        issues: list[str] = []
        if result.get("ready") is not True or lifecycle.get("model_loaded") is not True:
            issues.append("model_not_loaded")
        for key in (
            "actual_gpu_allocation",
            "persistent_model_allocation_present",
            "cuda_synchronize_before_model_load_succeeded",
            "cuda_synchronize_after_conditioning_succeeded",
            "model_and_core_components_cuda",
            "no_rejected_runtime_warnings",
        ):
            if gpu.get(key) is not True:
                issues.append(f"{key}_not_proven")
        if not cls._qwen_absence_proven(result, "parent_qwen_residency_before_load"):
            issues.append("qwen_absence_not_proven_before_load")
        if result.get("model_reused") is True:
            # The sealed worker intentionally returns a compact confirmation
            # when its already-conditioned CUDA model is still resident.  The
            # cold-load identity/runtime records were already validated by
            # this host for the same owned client; requiring those cold-only
            # fields again incorrectly rejects legitimate worker reuse.
            if result.get("reason") != "already_loaded":
                issues.append("reuse_reason_mismatch")
            model_load_count = lifecycle.get("model_load_count")
            if (
                isinstance(model_load_count, bool)
                or not isinstance(model_load_count, int)
                or model_load_count < 1
            ):
                issues.append("reuse_model_load_count_not_proven")
            conditioning_count = lifecycle.get("reference_conditioning_count")
            if (
                isinstance(conditioning_count, bool)
                or not isinstance(conditioning_count, int)
                or conditioning_count < 1
            ):
                issues.append("reuse_reference_conditioning_count_not_proven")
            if lifecycle.get("conditioned_reference_sha256") != APPROVED_REFERENCE_SHA256:
                issues.append("conditioned_reference_hash_not_proven_at_reuse")
            return issues
        identity = result.get("identity")
        identity = identity if isinstance(identity, dict) else {}
        if identity.get("profile_sha256") != APPROVED_PROFILE_SHA256:
            issues.append("approved_profile_hash_not_proven_at_load")
        if identity.get("reference_sha256") != APPROVED_REFERENCE_SHA256:
            issues.append("approved_reference_hash_not_proven_at_load")
        if lifecycle.get("conditioned_reference_sha256") != APPROVED_REFERENCE_SHA256:
            issues.append("conditioned_reference_hash_not_proven_at_load")
        runtime_checks = result.get("runtime_cuda_checks")
        runtime_checks = runtime_checks if isinstance(runtime_checks, dict) else {}
        for key in (
            "capability",
            "cuda_available",
            "cuda_runtime",
            "device",
            "sm_120",
            "torch_runtime",
            "torchaudio_runtime",
        ):
            if runtime_checks.get(key) is not True:
                issues.append(f"runtime_cuda_{key}_not_proven")
        versions = result.get("runtime_versions")
        versions = versions if isinstance(versions, dict) else {}
        expected_versions = {
            "torch": "2.11.0+cu130",
            "torchaudio": "2.11.0+cu130",
            "chatterbox-tts": "0.1.7",
        }
        for key, expected in expected_versions.items():
            if versions.get(key) != expected:
                issues.append(f"runtime_version_{key}_mismatch")
        return issues

    @staticmethod
    def _safe_reuse_telemetry(load_result: Any) -> dict[str, Any]:
        """Return only bounded proof carried by an already-loaded response."""

        result = load_result if isinstance(load_result, dict) else {}
        qwen = result.get("parent_qwen_residency_before_load")
        qwen = qwen if isinstance(qwen, dict) else {}
        gpu = result.get("gpu_proof")
        gpu = gpu if isinstance(gpu, dict) else {}
        lifecycle = result.get("lifecycle")
        lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
        transport = result.get("parent_transport_timing")
        transport = transport if isinstance(transport, dict) else {}

        def safe_number(value: Any) -> int | float | None:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            return value if math.isfinite(float(value)) else None

        required_gpu_flags = (
            "actual_gpu_allocation",
            "persistent_model_allocation_present",
            "cuda_synchronize_before_model_load_succeeded",
            "cuda_synchronize_after_conditioning_succeeded",
            "model_and_core_components_cuda",
            "no_rejected_runtime_warnings",
        )
        return {
            "telemetry_scope": "same_owned_worker_reuse_confirmation",
            "ready": result.get("ready") is True,
            "reason": result.get("reason"),
            "model_reused": result.get("model_reused") is True,
            "initial_cold_load_telemetry_preserved": True,
            "parent_transport_timing": {
                key: safe_number(transport.get(key))
                for key in (
                    "request_submitted_monotonic_ns",
                    "response_received_monotonic_ns",
                    "elapsed_seconds",
                )
            },
            "qwen_residency_before_load": {
                "query_succeeded": qwen.get("query_succeeded") is True,
                "qwen_absent_proven": qwen.get("qwen_absent_proven") is True,
                "qwen_record_count": len(qwen.get("qwen_records") or [])
                if isinstance(qwen.get("qwen_records"), list)
                else None,
                "model_state_changed": qwen.get("model_state_changed")
                if isinstance(qwen.get("model_state_changed"), bool)
                else None,
            },
            "gpu_proof": {key: gpu.get(key) is True for key in required_gpu_flags},
            "lifecycle": {
                key: lifecycle.get(key)
                for key in (
                    "model_loaded",
                    "model_load_count",
                    "reference_conditioning_count",
                    "successful_synthesis_count",
                    "generation_attempt_count",
                    "conditioned_reference_sha256",
                )
            },
        }

    @staticmethod
    def _safe_load_telemetry(
        load_result: Any,
        hello: Any = None,
    ) -> dict[str, Any]:
        result = load_result if isinstance(load_result, dict) else {}
        qwen = result.get("parent_qwen_residency_before_load")
        qwen = qwen if isinstance(qwen, dict) else {}
        gpu = result.get("gpu_proof")
        gpu = gpu if isinstance(gpu, dict) else {}
        lifecycle = result.get("lifecycle")
        lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
        transport = result.get("parent_transport_timing")
        transport = transport if isinstance(transport, dict) else {}
        hello_result = hello if isinstance(hello, dict) else {}
        process_start = hello_result.get("parent_process_start_timing")
        process_start = process_start if isinstance(process_start, dict) else {}
        resources = result.get("resources")
        resources = resources if isinstance(resources, dict) else {}
        runtime_versions = result.get("runtime_versions")
        runtime_versions = runtime_versions if isinstance(runtime_versions, dict) else {}
        runtime_checks = result.get("runtime_cuda_checks")
        runtime_checks = runtime_checks if isinstance(runtime_checks, dict) else {}
        identity = result.get("identity")
        identity = identity if isinstance(identity, dict) else {}

        def safe_number(value: Any) -> int | float | None:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            return value if math.isfinite(float(value)) else None

        allowed_phases = {
            "load.restricted_environment",
            "load.runtime_dependency_metadata",
            "load.approved_identity_hashes",
            "load.qwen_absence",
            "imports.torch",
            "imports.torchaudio",
            "imports.transformers_compatibility",
            "imports.numpy",
            "imports.soundfile",
            "imports.chatterbox",
            "imports.dialogue_contracts",
            "load.cuda_contract",
            "load.cuda_prepare",
            "load.model_from_pretrained",
            "load.reference_prepare_conditionals",
            "load.cuda_synchronize_after_conditioning",
        }
        phase_timings: list[dict[str, Any]] = []
        for phase in result.get("phase_timings") or []:
            if not isinstance(phase, dict) or phase.get("phase") not in allowed_phases:
                continue
            phase_timings.append(
                {
                    "phase": phase.get("phase"),
                    "elapsed_seconds": safe_number(phase.get("elapsed_seconds")),
                    "status": phase.get("status") if phase.get("status") in {"passed", "failed"} else None,
                }
            )
        gpu_keys = (
            "actual_gpu_allocation",
            "persistent_model_allocation_present",
            "cuda_synchronize_before_model_load_succeeded",
            "cuda_synchronize_after_conditioning_succeeded",
            "model_and_core_components_cuda",
            "no_rejected_runtime_warnings",
            "allocated_before_bytes",
            "allocated_after_bytes",
            "reserved_before_bytes",
            "reserved_after_bytes",
            "peak_allocated_bytes",
            "peak_reserved_bytes",
        )
        return {
            "telemetry_scope": "initial_worker_start_and_model_load",
            "ready": result.get("ready") is True,
            "model_reused": result.get("model_reused") is True,
            "operation_seconds": safe_number(result.get("operation_seconds")),
            "worker_start": {
                "ready": hello_result.get("ready") is True,
                "model_loaded_before_explicit_load": hello_result.get("model_loaded"),
                "worker_sha256": hello_result.get("worker_sha256"),
                "config_sha256": hello_result.get("config_sha256"),
                "elapsed_seconds": safe_number(process_start.get("elapsed_seconds")),
            },
            "parent_transport_timing": {
                key: safe_number(transport.get(key))
                for key in (
                    "request_submitted_monotonic_ns",
                    "response_received_monotonic_ns",
                    "elapsed_seconds",
                )
            },
            "qwen_residency_before_load": {
                "query_succeeded": qwen.get("query_succeeded") is True,
                "qwen_absent_proven": qwen.get("qwen_absent_proven") is True,
                "qwen_record_count": len(qwen.get("qwen_records") or [])
                if isinstance(qwen.get("qwen_records"), list)
                else None,
                "model_state_changed": qwen.get("model_state_changed")
                if isinstance(qwen.get("model_state_changed"), bool)
                else None,
            },
            "gpu_proof": {
                key: (
                    gpu.get(key) is True
                    if key
                    in {
                        "actual_gpu_allocation",
                        "persistent_model_allocation_present",
                        "cuda_synchronize_before_model_load_succeeded",
                        "cuda_synchronize_after_conditioning_succeeded",
                        "model_and_core_components_cuda",
                        "no_rejected_runtime_warnings",
                    }
                    else safe_number(gpu.get(key))
                )
                for key in gpu_keys
            },
            "runtime_versions": {
                key: runtime_versions.get(key)
                if isinstance(runtime_versions.get(key), str)
                else None
                for key in ("torch", "torchaudio", "chatterbox-tts")
            },
            "runtime_cuda_checks": {
                key: runtime_checks.get(key) is True
                for key in (
                    "capability",
                    "cuda_available",
                    "cuda_runtime",
                    "device",
                    "sm_120",
                    "torch_runtime",
                    "torchaudio_runtime",
                )
            },
            "identity": {
                "profile_sha256": identity.get("profile_sha256"),
                "reference_sha256": identity.get("reference_sha256"),
            },
            "resources": {
                key: safe_number(resources.get(key))
                for key in (
                    "peak_process_rss_mib",
                    "peak_system_ram_used_mib",
                    "baseline_total_gpu_used_mib",
                    "peak_total_gpu_used_mib",
                    "peak_total_gpu_delta_mib",
                    "host_sample_count",
                    "external_gpu_sample_count",
                )
            },
            "phase_timings": phase_timings,
            "lifecycle": {
                key: lifecycle.get(key)
                for key in (
                    "model_loaded",
                    "model_load_count",
                    "reference_conditioning_count",
                    "conditioned_reference_sha256",
                )
            },
        }

    def prewarm(self, owner: str) -> dict[str, Any]:
        begun = self.begin_session(owner)
        if begun.get("begun") is not True:
            return {"warmed": False, **begun}
        normalized_owner = str(owner or "").strip()
        started = time.perf_counter()
        with self._operation_lock:
            with self._lock:
                if self._owner != normalized_owner:
                    return {
                        "warmed": False,
                        "reason": "persistent_blackwell_v2_session_changed_before_prewarm",
                        "playback": False,
                        "generated_audio": False,
                    }
                process = getattr(self._client, "process", None) if self._client else None
                if self._client is not None and process is not None and process.poll() is not None:
                    self._close_locked("dead_worker_replaced_before_prewarm")
                client_started = self._client is None
                if self._client is None:
                    client = self._new_client_locked()
                    self._client_generation += 1
                    self._client = client
                client = self._client
                self._mark_operation_locked(client, "prewarm")
            try:
                hello = client.start() if client_started else None
                if hello is not None and (
                    hello.get("ready") is not True or hello.get("model_loaded") is not False
                ):
                    raise RuntimeError("persistent candidate v2 handshake contract failed")
                with self._lock:
                    if self._client is not client or self._owner != normalized_owner:
                        raise RuntimeError("persistent candidate v2 prewarm cancelled after start")
                load_result = client.load()
                issues = self._load_contract_issues(load_result)
                if issues:
                    raise RuntimeError("persistent candidate v2 load contract failed: " + ",".join(issues))
                model_reused = load_result.get("model_reused") is True
                with self._lock:
                    prior_cold_load_proven = bool(self._last_load_telemetry)
                if model_reused and (client_started or not prior_cold_load_proven):
                    raise RuntimeError(
                        "persistent candidate v2 reuse was not bound to a prior cold load"
                    )
                safe_load_telemetry = (
                    self._safe_reuse_telemetry(load_result)
                    if model_reused
                    else self._safe_load_telemetry(load_result, hello)
                )
                with self._lock:
                    if self._client is not client or self._owner != normalized_owner:
                        raise RuntimeError("persistent candidate v2 prewarm cancelled after load")
                    self._loaded = True
                    self._last_load_verified_monotonic = time.monotonic()
                    if not model_reused:
                        self._last_load_telemetry = safe_load_telemetry
                    self._finish_operation_locked(client)
                    elapsed = round(time.perf_counter() - started, 6)
                    self._record(
                        "v2_prewarm_completed",
                        elapsed_seconds=elapsed,
                        client_started=client_started,
                        worker_process_reused=not client_started,
                        model_reused=model_reused,
                        test_only=self._test_client_injected,
                    )
                return {
                    "warmed": True,
                    "ready": True,
                    "reason": "persistent_blackwell_v2_model_ready",
                    "device": "cuda",
                    "model_reused": model_reused,
                    "worker_process_reused": not client_started,
                    "duration_seconds": elapsed,
                    "sidecar_lifecycle": "session_owned_persistent_candidate_v2",
                    "load_telemetry": safe_load_telemetry,
                    "test_only_injected_client": self._test_client_injected,
                    "candidate_attempted": True,
                    "fallback_eligible": False,
                    "route_connected": False,
                    "production_route_promoted": False,
                    "playback": False,
                    "generated_audio": False,
                    **self.status(),
                }
            except Exception as exc:
                with self._lock:
                    attached = self._client is client
                    self._finish_operation_locked(client)
                    cleanup = self._close_locked("v2_prewarm_failed") if attached else None
                    error_detail = str(exc)[:500]
                    self._record(
                        "v2_prewarm_failed",
                        error_type=type(exc).__name__,
                        error_detail=error_detail,
                    )
                if not attached:
                    cleanup = self._abort_exact_owned_client(client, "detached_v2_prewarm_failed")
                cancelled = not attached
                cleanup_proven = _owned_cleanup_proven(cleanup)
                return {
                    "warmed": False,
                    "ready": False,
                    "reason": (
                        "persistent_blackwell_v2_prewarm_cancelled"
                        if cancelled
                        else "persistent_blackwell_v2_prewarm_failed"
                    ),
                    "error_type": type(exc).__name__,
                    "error_detail": error_detail,
                    "owned_worker_cleanup": cleanup,
                    "cancelled": cancelled,
                    "candidate_attempted": True,
                    "fallback_eligible": bool(
                        attached and cleanup_proven and not self._test_client_injected
                    ),
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
            cleanup = self._binding_failure_cleanup("v2_feature_flag_disabled_before_synthesis")
            cleanup_proven = cleanup is None or _owned_cleanup_proven(cleanup)
            return {
                "generated": False,
                "reason": "persistent_blackwell_v2_feature_flag_disabled",
                "persistent_route_eligible": False,
                "candidate_attempted": False,
                "fallback_allowed": cleanup_proven,
                "route_blocked": not cleanup_proven,
                "cancelled": False,
                "target_cleanup_proven": True,
                "owned_worker_cleanup": cleanup,
                "playback": False,
            }
        try:
            _acceptance_binding()
        except Exception as exc:
            cleanup = self._binding_failure_cleanup("v2_binding_failed")
            cleanup_proven = cleanup is None or _owned_cleanup_proven(cleanup)
            return {
                "generated": False,
                "reason": "persistent_blackwell_v2_binding_failed",
                "error_type": type(exc).__name__,
                "persistent_route_eligible": False,
                "candidate_attempted": False,
                "fallback_allowed": cleanup_proven,
                "route_blocked": not cleanup_proven,
                "cancelled": False,
                "target_cleanup_proven": True,
                "owned_worker_cleanup": cleanup,
                "playback": False,
            }
        try:
            final_target = _safe_generated_wav(Path(target))
        except Exception as exc:
            cleanup = self._binding_failure_cleanup("v2_target_rejected")
            return {
                "generated": False,
                "reason": "persistent_blackwell_v2_target_rejected",
                "error_type": type(exc).__name__,
                "persistent_route_eligible": False,
                "candidate_attempted": False,
                "fallback_allowed": False,
                "route_blocked": True,
                "cancelled": False,
                "target_cleanup_proven": not Path(target).exists(),
                "owned_worker_cleanup": cleanup,
                "playback": False,
            }
        normalized = str(text or "").strip()
        if not normalized:
            return {
                "generated": False,
                "reason": "persistent_blackwell_v2_empty_public_spoken_text",
                "persistent_route_eligible": False,
                "candidate_attempted": False,
                "fallback_allowed": True,
                "route_blocked": False,
                "cancelled": False,
                "target_cleanup_proven": True,
                "playback": False,
            }
        text_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        started = time.perf_counter()
        with self._lock:
            owner = self._owner
        if not owner:
            return {
                "generated": False,
                "reason": "persistent_blackwell_v2_no_owned_voice_session",
                "persistent_route_eligible": False,
                "candidate_attempted": False,
                "fallback_allowed": True,
                "route_blocked": False,
                "cancelled": False,
                "target_cleanup_proven": True,
                "playback": False,
            }
        warm_result = self.prewarm(owner)
        if warm_result.get("warmed") is not True:
            return {
                "generated": False,
                "reason": "persistent_blackwell_v2_lazy_prewarm_failed",
                "persistent_route_eligible": bool(
                    warm_result.get("fallback_eligible") is True
                ),
                "candidate_attempted": warm_result.get("candidate_attempted") is True,
                "fallback_allowed": warm_result.get("fallback_eligible") is True,
                "route_blocked": warm_result.get("fallback_eligible") is not True,
                "cancelled": warm_result.get("cancelled") is True,
                "target_cleanup_proven": True,
                "prewarm": warm_result,
                "owned_worker_cleanup": warm_result.get("owned_worker_cleanup"),
                "playback": False,
            }
        worker_process_reused = warm_result.get("worker_process_reused") is True
        persistent_model_reused = warm_result.get("model_reused") is True
        client: Any | None = None
        staging: Path | None = None
        final_link_created = False
        with self._operation_lock:
            try:
                with self._lock:
                    if self._owner != owner or self._client is None or not self._loaded:
                        raise RuntimeError("persistent candidate v2 session changed before synthesis")
                    client = self._client
                    self._mark_operation_locked(client, "synthesis")
                    generation = self._generation
                request_id = uuid.uuid4().hex
                staging = CANDIDATE_STAGING_ROOT / f"session_{generation:06d}" / f"{request_id}.wav"
                staging.parent.mkdir(parents=True, exist_ok=True)
                relative = staging.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
                response = client.synthesize(
                    text=normalized,
                    output_relative=relative,
                    pcm_output_gain_db=float(pcm_output_gain_db),
                    proximity_cut_hz=float(proximity_cut_hz),
                    proximity_cut_mix=float(proximity_cut_mix),
                )
                with self._lock:
                    attached = self._client is client and self._owner == owner
                if not attached:
                    raise RuntimeError("persistent candidate v2 synthesis cancelled")
                issues: list[str] = []
                expected = {
                    "generated": True,
                    "channel": "public_spoken_only",
                    "requested_text_bound": True,
                    "device": "cuda",
                    "text_sha256": text_hash,
                    "profile_sha256": APPROVED_PROFILE_SHA256,
                    "reference_sha256": APPROVED_REFERENCE_SHA256,
                    "playback": False,
                    "generic_voice_used": False,
                    "sapi_voice_used": False,
                    "fallback_used": False,
                    "conditioning_reused": True,
                }
                for key, value in expected.items():
                    if response.get(key) != value:
                        issues.append(f"{key}_contract_mismatch")
                gpu_proof = response.get("gpu_proof")
                gpu_proof = gpu_proof if isinstance(gpu_proof, dict) else {}
                for key in (
                    "actual_gpu_execution",
                    "model_and_core_components_cuda",
                    "cuda_synchronize_before_generation_succeeded",
                    "cuda_synchronize_after_generation_succeeded",
                    "persistent_model_allocation_present",
                    "generation_peak_exceeded_baseline",
                    "no_rejected_runtime_warnings",
                    "qwen_absence_proven_for_accepted_generation",
                    "official_host_return_contract_satisfied",
                    "accepted_output_tensors_host_cpu",
                ):
                    if gpu_proof.get(key) is not True:
                        issues.append(f"{key}_not_proven")
                if gpu_proof.get("accepted_output_tensors_cuda") is not False:
                    issues.append("accepted_output_tensors_cuda_truth_violation")
                if not self._qwen_absence_proven(
                    response, "parent_qwen_residency_before_synthesis"
                ):
                    issues.append("qwen_absence_not_proven_before_synthesis")
                if not self._worker_generation_qwen_absence_proven(response):
                    issues.append("qwen_absence_not_proven_for_accepted_generation")
                if staging is None or not staging.is_file():
                    issues.append("candidate_staging_wav_missing")
                    staging_wav: dict[str, Any] = {}
                else:
                    staging_wav = _validate_non_silent_wav(staging)
                    if staging_wav.get("passed") is not True:
                        issues.append("candidate_staging_wav_invalid_or_silent")
                worker_wav = response.get("wav_validation")
                worker_wav = worker_wav if isinstance(worker_wav, dict) else {}
                if (
                    worker_wav.get("passed") is not True
                    or worker_wav.get("non_silent") is not True
                    or worker_wav.get("sha256") != staging_wav.get("sha256")
                ):
                    issues.append("worker_wav_validation_not_bound")
                try:
                    response_audio = Path(str(response.get("audio_path") or "")).resolve()
                except (OSError, ValueError):
                    response_audio = Path()
                if staging is None or response_audio != staging.resolve():
                    issues.append("candidate_audio_path_mismatch")
                if issues:
                    with self._lock:
                        attached = self._client is client and self._owner == owner
                        self._finish_operation_locked(client)
                        cleanup = (
                            self._close_locked("v2_synthesis_contract_failed")
                            if attached
                            else None
                        )
                        self._record(
                            "v2_synthesis_contract_failed",
                            issue_count=len(issues),
                            text_sha256=text_hash,
                        )
                    if not attached:
                        cleanup = self._abort_exact_owned_client(
                            client, "detached_v2_synthesis_contract_failed"
                        )
                    cleanup_proven = _owned_cleanup_proven(cleanup)
                    fallback_allowed = bool(
                        attached and cleanup_proven and not self._test_client_injected
                    )
                    return {
                        "generated": False,
                        "reason": (
                            "persistent_blackwell_v2_synthesis_cancelled"
                            if not attached
                            else "persistent_blackwell_v2_synthesis_contract_failed"
                        ),
                        "issues": issues,
                        "persistent_route_eligible": fallback_allowed,
                        "candidate_attempted": True,
                        "fallback_allowed": fallback_allowed,
                        "route_blocked": not fallback_allowed,
                        "owned_worker_cleanup": cleanup,
                        "cancelled": not attached,
                        "target_cleanup_proven": True,
                        "playback": False,
                        "generic_voice_used": False,
                        "sapi_voice_used": False,
                    }
                # Hold the short host lock through exclusive link, validation,
                # and staging cleanup.  Release/owner-switch can interrupt the
                # long worker request, but cannot let an old session promote a
                # WAV after ownership has changed.
                with self._lock:
                    if self._client is not client or self._owner != owner:
                        raise RuntimeError(
                            "persistent candidate v2 synthesis cancelled before promotion"
                        )
                    final_target.parent.mkdir(parents=True, exist_ok=True)
                    os.link(staging, final_target)
                    final_link_created = True
                    final_wav = _validate_non_silent_wav(final_target)
                    if (
                        final_wav.get("passed") is not True
                        or final_wav.get("sha256") != staging_wav.get("sha256")
                    ):
                        # ``os.link`` above is exclusive.  Once it succeeds,
                        # this integration owns the exact final directory
                        # entry even if the staging link disappears before
                        # validation.  Remove that owned entry directly and
                        # prove absence before permitting any fallback route.
                        # Do not perform a pathname stat-then-unlink cleanup:
                        # another writer could replace the entry in that gap.
                        # Preserve whatever is now at the path and fail closed;
                        # no fallback route may touch it.
                        try:
                            target_cleanup_proven = not final_target.exists()
                        except OSError:
                            target_cleanup_proven = False
                        self._finish_operation_locked(client)
                        cleanup = self._close_locked("v2_final_wav_validation_failed")
                        cleanup_proven = _owned_cleanup_proven(cleanup)
                        fallback_allowed = bool(
                            cleanup_proven
                            and target_cleanup_proven
                            and not self._test_client_injected
                        )
                        return {
                            "generated": False,
                            "reason": "persistent_blackwell_v2_final_wav_validation_failed",
                            "persistent_route_eligible": fallback_allowed,
                            "candidate_attempted": True,
                            "fallback_allowed": fallback_allowed,
                            "route_blocked": not fallback_allowed,
                            "cancelled": False,
                            "target_cleanup_proven": target_cleanup_proven,
                            "owned_worker_cleanup": cleanup,
                            "playback": False,
                            "generic_voice_used": False,
                            "sapi_voice_used": False,
                        }
                    staging_cleanup_error_type = ""
                    try:
                        staging.unlink()
                    except FileNotFoundError:
                        pass
                    except OSError as exc:
                        # The validated final hard link is already complete.
                        # A residual candidate-staging link is cleanup debt,
                        # not a reason to regenerate or invalidate the WAV.
                        staging_cleanup_error_type = type(exc).__name__
                    self._finish_operation_locked(client)
                    elapsed = round(time.perf_counter() - started, 6)
                    self._record(
                        "v2_synthesis_completed",
                        elapsed_seconds=elapsed,
                        text_sha256=text_hash,
                        wav_sha256=final_wav["sha256"],
                        test_only=self._test_client_injected,
                    )
                test_only = self._test_client_injected
                return {
                    **response,
                    "generated": True,
                    "reason": "ok",
                    "route_id": (
                        "blackwell_gpu_persistent_candidate_v2_test_only"
                        if test_only
                        else "blackwell_gpu_persistent_candidate_v2_inactive"
                    ),
                    "approved_voice_path_used": None if test_only else "blackwell_gpu",
                    "sidecar_lifecycle": "session_owned_persistent_candidate_v2",
                    # Process/client reuse is independent from model residency.
                    # Exact Qwen/voice serialization deliberately unloads the
                    # model before Qwen, then reloads it on this same worker.
                    "persistent_worker_reused": worker_process_reused,
                    "persistent_model_reused": persistent_model_reused,
                    "lazy_model_reload_performed": not persistent_model_reused,
                    "test_only_injected_client": test_only,
                    "text": normalized,
                    "text_sha256": text_hash,
                    "audio_path": str(final_target),
                    "wav_validation": final_wav,
                    "staging_promoted_to_caller_target": True,
                    "staging_cleanup_error_type": staging_cleanup_error_type,
                    "integration_elapsed_seconds": elapsed,
                    "playback": False,
                    "generic_voice_used": False,
                    "sapi_voice_used": False,
                    "fallback_used": False,
                    "persistent_route_eligible": not test_only,
                    "candidate_attempted": True,
                    "fallback_allowed": False,
                    "route_blocked": False,
                    "cancelled": False,
                    "target_cleanup_proven": True,
                    "production_route_connected": False,
                    "production_route_promoted": False,
                    "full_gpu_acceptance_sha256": FULL_GPU_PASS_REPORT_SHA256,
                }
            except Exception as exc:
                # If exclusive link creation lost an EEXIST race, the target
                # belongs to somebody else.  Its presence is *not* cleanup
                # proof and no fallback may write the contested path.
                try:
                    linked_target_cleanup_proven = not final_target.exists()
                except OSError:
                    linked_target_cleanup_proven = False
                if final_link_created:
                    # Once final-link creation occurred, an exception leaves
                    # the pathname quarantined.  Never delete by pathname after
                    # a non-atomic identity check; fail closed instead.
                    try:
                        linked_target_cleanup_proven = not final_target.exists()
                    except OSError:
                        linked_target_cleanup_proven = False
                with self._lock:
                    attached = (
                        client is not None
                        and self._client is client
                        and self._owner == owner
                    )
                    if client is not None:
                        self._finish_operation_locked(client)
                    cleanup = self._close_locked("v2_synthesis_exception") if attached else None
                    self._record(
                        "v2_synthesis_failed",
                        error_type=type(exc).__name__,
                        text_sha256=text_hash,
                    )
                if client is not None and not attached:
                    cleanup = self._abort_exact_owned_client(
                        client, "detached_v2_synthesis_exception"
                    )
                cancelled = bool(
                    not attached
                    or "cancelled" in str(exc).casefold()
                    or "session changed" in str(exc).casefold()
                )
                fallback_eligible = bool(
                    not cancelled
                    and linked_target_cleanup_proven
                    and _owned_cleanup_proven(cleanup)
                    and not self._test_client_injected
                )
                return {
                    "generated": False,
                    "reason": (
                        "persistent_blackwell_v2_synthesis_cancelled"
                        if cancelled
                        else "persistent_blackwell_v2_synthesis_failed"
                    ),
                    "error_type": type(exc).__name__,
                    "persistent_route_eligible": fallback_eligible,
                    "candidate_attempted": client is not None,
                    "fallback_allowed": fallback_eligible,
                    "route_blocked": not fallback_eligible,
                    "cancelled": cancelled,
                    "linked_target_cleanup_proven": linked_target_cleanup_proven,
                    "owned_worker_cleanup": cleanup,
                    "playback": False,
                    "generic_voice_used": False,
                    "sapi_voice_used": False,
                }


_INTEGRATION = PersistentBlackwellVoiceIntegrationV2()


def begin_session(owner: str) -> dict[str, Any]:
    return _INTEGRATION.begin_session(owner)


def prewarm(owner: str) -> dict[str, Any]:
    return _INTEGRATION.prewarm(owner)


def suspend_if_owner(
    expected_owner: str,
    reason: str = "owner_bound_model_only_suspend",
    *,
    expected_generation: int,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    return _INTEGRATION.suspend_if_owner(
        expected_owner,
        reason,
        expected_generation=expected_generation,
        timeout_seconds=timeout_seconds,
    )


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


def release_if_owner(expected_owner: str, reason: str = "owner_bound_release") -> dict[str, Any]:
    return _INTEGRATION.close_if_owner(expected_owner, reason)


def status() -> dict[str, Any]:
    return _INTEGRATION.status()


atexit.register(lambda: _INTEGRATION.close("python_process_exit"))
