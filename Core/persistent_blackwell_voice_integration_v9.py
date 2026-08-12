"""Default-off coordinator for the append-only Blackwell v9 static repair.

V9 changes only the Windows root/worker identity boundary.  The v8 worker and
all v2-v8 behavior remain sealed.  Importing this module is inert, and no live
factory can be reached without a future different-agent v9 audit plus a new
per-run capability.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from Core.blackwell_v9_process_boundary import V9JsonLineWorkerProcess
from Core.persistent_blackwell_voice_integration_v8 import (
    BlackwellV8Coordinator,
    _live_environment as _v8_live_environment,
    _static_environment as _v8_static_environment,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v7.persistent_worker import (
    load_canonical_config as load_v7_config,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8 import (
    candidate_contract as v8_contract,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v9.candidate_contract import (
    PROJECT_ROOT,
    V9ContractError,
    is_sha256,
    load_canonical_config,
    verify_fresh_audit_authorization,
    verify_per_run_live_capability,
    verify_preserved_bytes,
    verify_topology_executables,
)


FEATURE_FLAG = "KIRA_ENABLE_BLACKWELL_VENV_DESCENDANT_IDENTITY_CANDIDATE_V9"
PRODUCTION_ROUTING_AUTHORIZED = False
LIVE_EXECUTION_AUTHORIZED_BY_THIS_MODULE = False
PLAYBACK_AUTHORIZED = False


class BlackwellV9Coordinator(BlackwellV8Coordinator):
    """V8 semantic facade with the v9 dual-process identity supervisor."""

    def __init__(self, process: V9JsonLineWorkerProcess, *, static_fixture: bool) -> None:
        super().__init__(process, static_fixture=static_fixture)
        self.v9_config = load_canonical_config()

    @classmethod
    def production_candidate(cls):
        raise V9ContractError(
            "v9 is not production routing; the exact current route remains unchanged"
        )

    @classmethod
    def static_fixture_candidate(cls, *, nonce: str):
        if not is_sha256(nonce):
            raise V9ContractError("static fixture nonce must be SHA-256")
        config = load_canonical_config()
        verify_preserved_bytes(config)
        identities = verify_topology_executables(config)
        launcher = Path(identities["launcher"]["executable_path"])
        command = (
            str(launcher),
            "-u",
            "-m",
            config["worker_module"],
            "--static-fixture",
            "--nonce",
            nonce,
        )
        process = cls._v9_process(
            command=command,
            environment=_v8_static_environment(nonce, startup_descendant=False),
            config=config,
            nonce=nonce,
            expected_static=True,
            expected_launcher_identity=identities["launcher"],
            expected_worker_identity=identities["worker"],
        )
        return cls(process, static_fixture=True)

    @classmethod
    def _static_fixture_for_hostile_test(
        cls,
        *,
        nonce: str,
        command: tuple[str, ...],
        expected_launcher_identity: dict[str, Any],
        expected_worker_identity: dict[str, Any],
    ):
        """Static-only test seam; never used by normal or live construction."""

        if not is_sha256(nonce):
            raise V9ContractError("hostile static fixture nonce must be SHA-256")
        config = load_canonical_config()
        process = cls._v9_process(
            command=command,
            environment=_v8_static_environment(nonce, startup_descendant=False),
            config=config,
            nonce=nonce,
            expected_static=True,
            expected_launcher_identity=expected_launcher_identity,
            expected_worker_identity=expected_worker_identity,
        )
        return cls(process, static_fixture=True)

    @classmethod
    def bounded_engineering_candidate(
        cls,
        *,
        nonce: str,
        accepted_v9_audit_sha256: str,
        accepted_v8_worker_audit_sha256: str,
    ):
        if not all(
            is_sha256(value)
            for value in (
                nonce,
                accepted_v9_audit_sha256,
                accepted_v8_worker_audit_sha256,
            )
        ):
            raise V9ContractError("live v9 nonce/audit bindings must be SHA-256")
        config = load_canonical_config()
        verify_preserved_bytes(config)
        identities = verify_topology_executables(config)
        verify_fresh_audit_authorization(
            config, expected_audit_sha256=accepted_v9_audit_sha256
        )
        verify_per_run_live_capability(config)
        v8_binding = config["v8_worker_audit_binding"]
        if accepted_v8_worker_audit_sha256 != v8_binding["sha256"]:
            raise V9ContractError("exact accepted v8 worker audit binding is wrong")
        v8_config = v8_contract.load_canonical_config()
        v8_contract.verify_fresh_audit_authorization(
            v8_config, expected_audit_sha256=accepted_v8_worker_audit_sha256
        )
        launcher = Path(identities["launcher"]["executable_path"])
        command = (
            str(launcher),
            "-u",
            "-m",
            config["worker_module"],
            "--live",
            "--nonce",
            nonce,
            "--accepted-audit-sha256",
            accepted_v8_worker_audit_sha256,
        )
        environment = _v8_live_environment(v8_config, nonce)
        environment["KIRA_V9_LIVE_SESSION_NONCE"] = nonce
        environment[config["engineering_run_opt_in"]] = config["engineering_run_opt_in_value"]
        process = cls._v9_process(
            command=command,
            environment=environment,
            config=config,
            nonce=nonce,
            expected_static=False,
            expected_launcher_identity=identities["launcher"],
            expected_worker_identity=identities["worker"],
        )
        return cls(process, static_fixture=False)

    @staticmethod
    def _v9_process(
        *,
        command: tuple[str, ...],
        environment: dict[str, str],
        config: dict[str, Any],
        nonce: str,
        expected_static: bool,
        expected_launcher_identity: dict[str, Any],
        expected_worker_identity: dict[str, Any],
    ) -> V9JsonLineWorkerProcess:
        v8_config = v8_contract.load_canonical_config()
        state = load_v7_config()
        return V9JsonLineWorkerProcess(
            command=command,
            cwd=PROJECT_ROOT,
            environment=environment,
            maximum_request_bytes=int(state["ipc_bounds"]["maximum_request_bytes"]),
            maximum_response_bytes=int(state["ipc_bounds"]["maximum_response_bytes"]),
            maximum_stderr_bytes=int(state["ipc_bounds"]["maximum_stderr_bytes"]),
            maximum_pending_responses=int(state["ipc_bounds"]["maximum_pending_responses"]),
            start_timeout_seconds=float(v8_config["operation_bounds_seconds"]["worker_start"]),
            lock_timeout_seconds=float(state["operation_bounds_seconds"]["ipc_lock_acquire"]),
            terminate_timeout_seconds=float(state["operation_bounds_seconds"]["terminate_tree"]),
            shutdown_timeout_seconds=float(v8_config["operation_bounds_seconds"]["shutdown"]),
            maximum_worker_job_memory_mib=int(
                state["resource_bounds"]["maximum_worker_job_memory_mib"]
            ),
            expected_creation_token_digest=hashlib.sha256(
                nonce.encode("utf-8")
            ).hexdigest(),
            expected_static_fixture=expected_static,
            expected_startup_descendant=False,
            expected_launcher_identity=expected_launcher_identity,
            expected_worker_identity=expected_worker_identity,
        )


__all__ = [
    "BlackwellV9Coordinator",
    "FEATURE_FLAG",
    "LIVE_EXECUTION_AUTHORIZED_BY_THIS_MODULE",
    "PLAYBACK_AUTHORIZED",
    "PRODUCTION_ROUTING_AUTHORIZED",
]
