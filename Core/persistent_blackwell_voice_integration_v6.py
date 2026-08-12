"""Parent coordinator for the inactive Blackwell v6 child-owned IPC candidate."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Any, Mapping

from Core.blackwell_v6_process_boundary import (
    JsonLineWorkerProcess,
    V6ProcessBoundaryError,
    V6ProcessTimeout,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v6.persistent_worker import (
    V6ContractError,
    load_canonical_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_FLAG = "KIRA_ENABLE_BLACKWELL_CPU_PARK_CANDIDATE_V6"
PRODUCTION_ROUTING_AUTHORIZED = False
LIVE_ADAPTER_AVAILABLE = False
PLAYBACK_IMPLEMENTED = False


def _hash_nonempty(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise V6ContractError(f"nonempty {label} is required")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _restricted_environment(static_nonce: str | None = None) -> dict[str, str]:
    permitted = (
        "USERNAME",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "APPDATA",
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
    )
    result = {key: os.environ[key] for key in permitted if os.environ.get(key)}
    result.update(
        {
            "PYTHONPATH": str(PROJECT_ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1",
            "KIRA_DISABLE_PLAYBACK": "1",
            "KIRA_DISABLE_CPU_VOICE": "1",
            "KIRA_DISABLE_SAPI": "1",
            "KIRA_DISABLE_GENERIC_VOICE": "1",
        }
    )
    if static_nonce is not None:
        result["KIRA_V6_STATIC_TEST_NONCE"] = static_nonce
    return result


class BlackwellV6Coordinator:
    """Serial parent facade; it never owns a model/backend Python object."""

    def __init__(self, process: JsonLineWorkerProcess, *, static_fixture: bool) -> None:
        self.config = load_canonical_config()
        self.process = process
        self.static_fixture = static_fixture
        self.state = "UNLOADED"
        self.cleanup_debt = False
        self.last_owned_token_hash: str | None = None
        self.worker_instance_id: str | None = None
        self.worker_pid: int | None = None

    @classmethod
    def production_candidate(cls):
        config = load_canonical_config()
        if (
            config["live_execution_authorized"] is not True
            or config["live_adapter_available"] is not True
            or LIVE_ADAPTER_AVAILABLE is not True
        ):
            raise V6ContractError(
                "v6 live worker is unavailable/default-off; no live adapter command may be invented"
            )
        raise V6ContractError("no reviewed v6 live adapter command exists")

    @classmethod
    def static_fixture_candidate(cls, *, nonce: str):
        if len(nonce) != 64 or any(character not in "0123456789abcdef" for character in nonce):
            raise V6ContractError("static fixture nonce must be SHA-256")
        config = load_canonical_config()
        command = (
            str(Path(sys.executable).resolve(strict=True)),
            "-u",
            "-m",
            "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v6.worker_entry",
            "--static-fixture",
            "--nonce",
            nonce,
        )
        process = JsonLineWorkerProcess(
            command=command,
            cwd=PROJECT_ROOT,
            environment=_restricted_environment(nonce),
            maximum_request_bytes=int(config["ipc_bounds"]["maximum_request_bytes"]),
            maximum_response_bytes=int(config["ipc_bounds"]["maximum_response_bytes"]),
            maximum_stderr_bytes=int(config["ipc_bounds"]["maximum_stderr_bytes"]),
            maximum_pending_responses=int(config["ipc_bounds"]["maximum_pending_responses"]),
            start_timeout_seconds=float(config["operation_bounds_seconds"]["worker_start"]),
            lock_timeout_seconds=float(config["operation_bounds_seconds"]["ipc_lock_acquire"]),
            terminate_timeout_seconds=float(config["operation_bounds_seconds"]["terminate_tree"]),
            shutdown_timeout_seconds=float(config["operation_bounds_seconds"]["shutdown"]),
            maximum_worker_job_memory_mib=int(
                config["resource_bounds"]["maximum_worker_job_memory_mib"]
            ),
            expected_creation_token_digest=hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            expected_static_fixture=True,
        )
        return cls(process, static_fixture=True)

    def start(self) -> dict[str, Any]:
        result = self.process.start()
        self.worker_instance_id = result["worker_instance_id"]
        self.worker_pid = result["pid"]
        return result

    def _invoke(self, operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        bounds = self.config["operation_bounds_seconds"]
        bound_key = {
            "qwen_stream": "qwen_real_stream",
            "recover_external": "cleanup",
        }.get(operation, operation)
        if bound_key not in bounds:
            raise V6ContractError(f"operation has no immutable aggregate bound: {operation}")
        try:
            envelope = self.process.invoke(operation, payload, float(bounds[bound_key]))
        except Exception:
            # A protocol failure or hard deadline can kill the exact child
            # before it reports cleanup.  Keep explicit debt (and any
            # provisional Qwen token binding) for fresh-worker recovery.
            self.cleanup_debt = True
            self.state = "CLEANUP_DEBT"
            raise
        value = envelope["value"]
        if not isinstance(value, dict):
            self.process.cancel_or_cleanup_without_waiting_for_operation_lock(
                "non_object_semantic_result"
            )
            self.cleanup_debt = True
            raise V6ContractError("worker semantic result is not an object")
        if isinstance(value.get("state"), str):
            self.state = value["state"]
        if value.get("success") is False or value.get("cleanup_debt") is True:
            cleanup = value.get("cleanup")
            self.cleanup_debt = bool(
                value.get("cleanup_debt") is True
                or (isinstance(cleanup, dict) and cleanup.get("cleanup_debt") is True)
            )
        cleanup = value.get("cleanup")
        cleanup_absence = cleanup.get("qwen_absence") if isinstance(cleanup, dict) else None
        if (
            (operation == "qwen_stream" and value.get("success") is True)
            or (
                isinstance(cleanup, dict)
                and cleanup.get("unloaded") is True
                and isinstance(cleanup_absence, dict)
                and cleanup_absence.get("records") == []
            )
            or (
                operation == "cleanup"
                and value.get("unloaded") is True
                and isinstance(value.get("qwen_absence"), dict)
                and value["qwen_absence"].get("records") == []
            )
        ):
            self.last_owned_token_hash = None
        return {**envelope, "value": value}

    def load(self, *, owner: str):
        return self._invoke("load", {"owner_hash": _hash_nonempty(owner, "owner")})

    def park(self, *, reason: str):
        return self._invoke("park", {"reason": reason})

    def resume(self, *, reason: str):
        return self._invoke("resume", {"reason": reason})

    def qwen_load(self, *, owner: str, session: str, token: str, ttl_seconds: int):
        token_hash = _hash_nonempty(token, "token")
        minimum = int(self.config["qwen_policy"]["minimum_token_characters"])
        if len(token) < minimum:
            raise V6ContractError("Qwen token is below the immutable length bound")
        payload = {
            "owner_hash": _hash_nonempty(owner, "owner"),
            "session_hash": _hash_nonempty(session, "session"),
            "token_hash": token_hash,
            "ttl_seconds": ttl_seconds,
        }
        if len({payload["owner_hash"], payload["session_hash"], token_hash}) != 3:
            raise V6ContractError("Qwen ownership bindings must be distinct")
        # Bind provisionally before IPC.  If the child loads Qwen and is then
        # killed before replying, the parent still has the exact cleanup key.
        self.last_owned_token_hash = token_hash
        result = self._invoke("qwen_load", payload)
        return result

    def qwen_stream(self, *, owner: str, session: str, token: str, messages: list[dict[str, str]]):
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

    def artifact_status(self, lease: Mapping[str, Any]):
        return self._invoke(
            "artifact_status",
            {
                "handle_id": lease["handle_id"],
                "artifact_sha256": lease["artifact_sha256"],
                "generation_id": lease["generation_id"],
            },
        )

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

    def recover_forced_termination_with_fresh_worker(self, *, reason: str) -> dict[str, Any]:
        token_hash = self.last_owned_token_hash
        if token_hash is None:
            return {
                "recovered": self.process.last_termination is not None
                and self.process.last_termination.get("root_exited") is True,
                "reason": "no_owned_qwen_binding; killed worker proves voice absence",
            }
        recovery_nonce = hashlib.sha256(
            f"v6-recovery:{token_hash}:{reason}".encode("utf-8")
        ).hexdigest()
        recovery = type(self).static_fixture_candidate(nonce=recovery_nonce)
        try:
            recovery.start()
            envelope = recovery._invoke(
                "recover_external",
                {"token_hash": token_hash, "reason": reason},
            )
            proven = envelope["value"].get("external_qwen_cleanup_proven") is True
            if proven:
                self.cleanup_debt = False
                self.state = "UNLOADED"
                self.last_owned_token_hash = None
            return {"recovered": proven, "evidence": envelope}
        finally:
            recovery.process.close()


__all__ = [
    "BlackwellV6Coordinator",
    "FEATURE_FLAG",
    "LIVE_ADAPTER_AVAILABLE",
    "PLAYBACK_IMPLEMENTED",
    "PRODUCTION_ROUTING_AUTHORIZED",
    "V6ProcessBoundaryError",
    "V6ProcessTimeout",
]
