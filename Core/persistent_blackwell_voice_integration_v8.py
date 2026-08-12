"""Default-off parent coordinator for Blackwell CPU-park v8.

V8 is not production routing.  It exposes a real, killable engineering
command only after a future different-agent static audit and an explicit
per-run capability.  Importing this module is inert.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Any, Mapping

from Core.blackwell_v7_process_boundary import (
    JsonLineWorkerProcess,
    V7ProcessBoundaryError,
    V7ProcessTimeout,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v7.persistent_worker import (
    load_canonical_config as load_v7_config,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.candidate_contract import (
    PROJECT_ROOT,
    V8ContractError,
    is_sha256,
    load_canonical_config,
    verify_fresh_audit_authorization,
    verify_preserved_bytes,
)


FEATURE_FLAG = "KIRA_ENABLE_BLACKWELL_CPU_PARK_CANDIDATE_V8"
PRODUCTION_ROUTING_AUTHORIZED = False
LIVE_ADAPTER_AVAILABLE = True
PLAYBACK_IMPLEMENTED = True
PLAYBACK_AUTHORIZED = False


def _hash_nonempty(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise V8ContractError(f"nonempty {label} is required")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _base_environment() -> dict[str, str]:
    allowed = (
        "USERNAME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA",
        "APPDATA", "SystemRoot", "SYSTEMROOT", "WINDIR", "PATH", "PATHEXT",
        "PROGRAMDATA", "DriverData", "ComSpec", "SystemDrive", "ProgramFiles",
        "ProgramFiles(x86)", "ProgramW6432", "CommonProgramFiles",
        "CommonProgramFiles(x86)", "CommonProgramW6432",
    )
    result = {key: value for key in allowed if (value := os.environ.get(key))}
    result.update(
        {
            "PYTHONPATH": str(PROJECT_ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1",
            "KIRA_DISABLE_CPU_VOICE": "1",
            "KIRA_DISABLE_SAPI": "1",
            "KIRA_DISABLE_GENERIC_VOICE": "1",
            "KIRA_VOICE_FORCE_SAPI": "0",
        }
    )
    return result


def _static_environment(nonce: str, *, startup_descendant: bool) -> dict[str, str]:
    result = _base_environment()
    result["KIRA_V8_STATIC_TEST_NONCE"] = nonce
    if startup_descendant:
        result["KIRA_V8_STATIC_PRE_READY_DESCENDANT"] = "1"
    return result


def _live_environment(config: dict[str, Any], nonce: str) -> dict[str, str]:
    result = _base_environment()
    cache_root = (
        PROJECT_ROOT / "RecoverySprint/runtime_cache/blackwell_chatterbox_persistent_candidate"
    ).resolve()
    project_cache = (PROJECT_ROOT / "RecoverySprint/runtime_cache").resolve()
    cache_root.relative_to(project_cache)
    cache_paths = {
        "TORCHINDUCTOR_CACHE_DIR": cache_root / "torchinductor",
        "TRITON_CACHE_DIR": cache_root / "triton",
        "TEMP": cache_root / "temp",
        "TMP": cache_root / "temp",
    }
    for path in cache_paths.values():
        path.resolve().relative_to(cache_root)
        path.mkdir(parents=True, exist_ok=True)
    result.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "CUDA_VISIBLE_DEVICES": "0",
            "KIRA_PERSISTENT_BLACKWELL_CANDIDATE": "1",
            "KIRA_PERSISTENT_BLACKWELL_ALLOW_MODEL_LOAD": "1",
            "KIRA_PERSISTENT_BLACKWELL_SESSION_NONCE": nonce,
            "KIRA_V8_LIVE_SESSION_NONCE": nonce,
            config["engineering_run_opt_in"]: config["engineering_run_opt_in_value"],
            **{key: str(path) for key, path in cache_paths.items()},
        }
    )
    return result


class BlackwellV8Coordinator:
    """Serial facade; all live objects remain in the Job-owned child."""

    def __init__(self, process: JsonLineWorkerProcess, *, static_fixture: bool) -> None:
        self.config = load_canonical_config()
        self.state_config = load_v7_config()
        self.process = process
        self.static_fixture = static_fixture
        self.state = "UNLOADED"
        self.cleanup_debt = False
        self.last_owned_token_hash: str | None = None
        self.worker_instance_id: str | None = None
        self.worker_pid: int | None = None

    @classmethod
    def production_candidate(cls):
        raise V8ContractError(
            "v8 is not production routing; current exact v2 route remains unchanged"
        )

    @classmethod
    def static_fixture_candidate(cls, *, nonce: str, startup_descendant: bool = False):
        if not is_sha256(nonce):
            raise V8ContractError("static fixture nonce must be SHA-256")
        config = load_canonical_config()
        state = load_v7_config()
        command = (
            str(Path(sys.executable).resolve(strict=True)),
            "-u", "-m",
            "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.worker_entry",
            "--static-fixture", "--nonce", nonce,
        )
        process = cls._process(
            command=command,
            environment=_static_environment(nonce, startup_descendant=startup_descendant),
            config=config,
            state=state,
            nonce=nonce,
            expected_static=True,
            startup_descendant=startup_descendant,
        )
        return cls(process, static_fixture=True)

    @classmethod
    def bounded_engineering_candidate(
        cls, *, nonce: str, accepted_audit_sha256: str
    ):
        if not is_sha256(nonce) or not is_sha256(accepted_audit_sha256):
            raise V8ContractError("live nonce/audit binding must be SHA-256")
        config = load_canonical_config()
        verify_preserved_bytes(config)
        verify_fresh_audit_authorization(
            config, expected_audit_sha256=accepted_audit_sha256
        )
        if os.environ.get(config["engineering_run_opt_in"]) != config["engineering_run_opt_in_value"]:
            raise V8ContractError("explicit outer per-run v8 capability is absent")
        state = load_v7_config()
        python = (PROJECT_ROOT / config["voice_live_component"]["python"]).resolve(strict=True)
        command = (
            str(python), "-u", "-m",
            "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.worker_entry",
            "--live", "--nonce", nonce,
            "--accepted-audit-sha256", accepted_audit_sha256,
        )
        process = cls._process(
            command=command,
            environment=_live_environment(config, nonce),
            config=config,
            state=state,
            nonce=nonce,
            expected_static=False,
            startup_descendant=False,
        )
        return cls(process, static_fixture=False)

    @staticmethod
    def _process(
        *, command: tuple[str, ...], environment: dict[str, str],
        config: dict[str, Any], state: dict[str, Any], nonce: str,
        expected_static: bool, startup_descendant: bool,
    ) -> JsonLineWorkerProcess:
        return JsonLineWorkerProcess(
            command=command,
            cwd=PROJECT_ROOT,
            environment=environment,
            maximum_request_bytes=int(state["ipc_bounds"]["maximum_request_bytes"]),
            maximum_response_bytes=int(state["ipc_bounds"]["maximum_response_bytes"]),
            maximum_stderr_bytes=int(state["ipc_bounds"]["maximum_stderr_bytes"]),
            maximum_pending_responses=int(state["ipc_bounds"]["maximum_pending_responses"]),
            start_timeout_seconds=float(config["operation_bounds_seconds"]["worker_start"]),
            lock_timeout_seconds=float(state["operation_bounds_seconds"]["ipc_lock_acquire"]),
            terminate_timeout_seconds=float(state["operation_bounds_seconds"]["terminate_tree"]),
            shutdown_timeout_seconds=float(config["operation_bounds_seconds"]["shutdown"]),
            maximum_worker_job_memory_mib=int(
                state["resource_bounds"]["maximum_worker_job_memory_mib"]
            ),
            expected_creation_token_digest=hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            expected_static_fixture=expected_static,
            expected_startup_descendant=startup_descendant,
        )

    def start(self) -> dict[str, Any]:
        result = self.process.start()
        self.worker_instance_id = result["worker_instance_id"]
        self.worker_pid = result["pid"]
        return result

    def _invoke(self, operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        bound_key = {"qwen_stream": "qwen_real_stream"}.get(operation, operation)
        bounds = self.config["operation_bounds_seconds"]
        if self.static_fixture and operation.startswith("fixture_"):
            timeout = 2.0
        elif bound_key not in bounds:
            state_bounds = self.state_config["operation_bounds_seconds"]
            if bound_key not in state_bounds:
                raise V8ContractError(f"operation has no aggregate bound: {operation}")
            timeout = float(state_bounds[bound_key])
        else:
            timeout = float(bounds[bound_key])
        try:
            envelope = self.process.invoke(operation, payload, timeout)
        except Exception:
            self.state = "CLEANUP_DEBT"
            self.cleanup_debt = True
            raise
        value = envelope.get("value")
        if not isinstance(value, dict):
            self.process.cancel_or_cleanup_without_waiting_for_operation_lock(
                "v8_non_object_semantic_result"
            )
            self.state = "CLEANUP_DEBT"
            self.cleanup_debt = True
            raise V8ContractError("v8 worker result is not an object")
        if isinstance(value.get("state"), str):
            self.state = value["state"]
        if value.get("success") is False:
            cleanup = value.get("cleanup")
            self.cleanup_debt = not (
                isinstance(cleanup, dict)
                and (cleanup.get("unloaded") is True or cleanup.get("success") is True)
            )
        return {**envelope, "value": value}

    def load(self, *, owner: str):
        return self._invoke("load", {"owner_hash": _hash_nonempty(owner, "owner")})

    def park(self, *, reason: str):
        return self._invoke("park", {"reason": reason})

    def resume(self, *, reason: str):
        return self._invoke("resume", {"reason": reason})

    def qwen_load(self, *, owner: str, session: str, token: str, ttl_seconds: int):
        token_hash = _hash_nonempty(token, "token")
        payload = {
            "owner_hash": _hash_nonempty(owner, "owner"),
            "session_hash": _hash_nonempty(session, "session"),
            "token_hash": token_hash,
            "ttl_seconds": ttl_seconds,
        }
        if len({payload["owner_hash"], payload["session_hash"], token_hash}) != 3:
            raise V8ContractError("Qwen ownership bindings must be distinct")
        self.last_owned_token_hash = token_hash
        return self._invoke("qwen_load", payload)

    def qwen_stream(
        self, *, owner: str, session: str, token: str,
        messages: list[dict[str, str]],
    ):
        return self._invoke(
            "qwen_stream",
            {
                "owner_hash": _hash_nonempty(owner, "owner"),
                "session_hash": _hash_nonempty(session, "session"),
                "token_hash": _hash_nonempty(token, "token"),
                "messages": messages,
            },
        )

    def synthesize(self, request: Mapping[str, Any]):
        return self._invoke("synthesis", request)

    def playback(self, lease: Mapping[str, Any], *, playback_id: str):
        if not is_sha256(playback_id):
            raise V8ContractError("playback ID must be SHA-256")
        return self._invoke(
            "playback",
            {
                "handle_id": lease["handle_id"],
                "artifact_sha256": lease["artifact_sha256"],
                "generation_id": lease["generation_id"],
                "playback_id": playback_id,
            },
        )

    def owner_hearing_ack(
        self, lease: Mapping[str, Any], *, owner: str, playback_id: str,
        observation: str, acknowledgement_id: str,
    ):
        return self._invoke(
            "owner_hearing_ack",
            {
                "playback_id": playback_id,
                "artifact_sha256": lease["artifact_sha256"],
                "generation_id": lease["generation_id"],
                "owner_hash": _hash_nonempty(owner, "owner"),
                "observation": observation,
                "acknowledgement_id": acknowledgement_id,
            },
        )

    def playback_status(self):
        return self._invoke("playback_status", {})

    def cleanup(self, *, reason: str):
        return self._invoke("cleanup", {"reason": reason})

    def cancel_now(self, *, reason: str) -> dict[str, Any]:
        termination = self.process.cancel_or_cleanup_without_waiting_for_operation_lock(reason)
        self.cleanup_debt = True
        self.state = "CLEANUP_DEBT"
        return {
            "cancelled": termination["root_exited"],
            "cleanup_debt": True,
            "termination": termination,
            "qwen_recovery_required": self.last_owned_token_hash is not None,
        }

    def close(self) -> dict[str, Any]:
        return self.process.close()


__all__ = [
    "BlackwellV8Coordinator",
    "FEATURE_FLAG",
    "LIVE_ADAPTER_AVAILABLE",
    "PLAYBACK_AUTHORIZED",
    "PLAYBACK_IMPLEMENTED",
    "PRODUCTION_ROUTING_AUTHORIZED",
    "V7ProcessBoundaryError",
    "V7ProcessTimeout",
]
