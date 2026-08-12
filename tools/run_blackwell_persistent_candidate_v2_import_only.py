#!/usr/bin/env python3
"""Hardened inherited-pipe Torch-import-only proof for inactive candidate v2.

Describe and static-self-check modes are inert. The live controller requires
explicit flags plus exact source hashes, allocates a new append-only attempt,
and launches the exact v2 client protocol against the exact v2 worker serve
loop. The child replaces only ``PersistentVoiceRuntime.load`` with a bounded
diagnostic that proves the stdin reader is parked at its semaphore and then
imports ``torch``. It never calls CUDA or imports Chatterbox/Torchaudio.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import hmac
import importlib
import json
import os
import secrets
import subprocess
import sys
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = Path(__file__).resolve()
V2_ROOT = ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate_v2"
CONFIG_PATH = V2_ROOT / "candidate_config.json"
CONTRACT_PATH = V2_ROOT / "candidate_contract.py"
CLIENT_PATH = V2_ROOT / "candidate_client.py"
WORKER_PATH = V2_ROOT / "persistent_worker.py"
ATTEMPT_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "import_only_v2_request_gate"
)

V2_CONFIG_SHA256 = "805c1d2836c618970a81f5f44d31f81f67e204173bd919857452daa8dbedc8bb"
V2_CONTRACT_SHA256 = "863c6ece050b12af157565c60df6fd82b207dae5476e693cc08e34b392c8f910"
V2_CLIENT_SHA256 = "9f33ef0d9fd969da05ce48eb148163efc77306bfd3bc215efcb482e68e7261a8"
V2_WORKER_SHA256 = "b6f2dcc816537552db02d00c5a1932057f2d99b5d206a578344d4a92523b3cad"

CHILD_HARD_BOUND_SECONDS = 120.0
PARENT_TOTAL_BOUND_SECONDS = 132.0
CLEANUP_RESERVE_SECONDS = 8.0
AUTH_KEY_ENV = "KIRA_V2_IMPORT_ONLY_AUTH_KEY"
CHILD_MODE_ENV = "KIRA_V2_IMPORT_ONLY_CHILD"
LIVE_MODE_ENV = "KIRA_V2_IMPORT_ONLY_LIVE"

FALSE_OUTCOME_FIELDS = (
    "cuda_api_called",
    "torchaudio_imported",
    "chatterbox_imported",
    "model_loaded",
    "audio_generated",
    "playback",
    "ollama_called",
    "promotion_performed",
    "production_routing_changed",
    "generic_voice_used",
    "sapi_voice_used",
    "fallback_used",
)
TRUE_RESULT_FIELDS = (
    "trusted_child_result",
    "reader_parked_at_request_gate",
    "reader_readline_absent",
    "torch_imported",
    "transport_serve_returned",
    "transport_eof_received",
)


if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v2 import (  # noqa: E402
    candidate_client,
    candidate_contract,
    persistent_worker,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def write_json_atomic_exclusive(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"append-only evidence already exists: {path}")
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb", buffering=0) as handle:
            handle.write(encoded)
            os.fsync(handle.fileno())
        if path.exists():
            raise FileExistsError(f"append-only evidence appeared during write: {path}")
        os.rename(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return hashlib.sha256(encoded).hexdigest()


def safe_json_evidence(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"present": False, "parsed": False, "sha256": None, "error": "missing"}
    raw = path.read_bytes()
    evidence: dict[str, Any] = {
        "present": True,
        "parsed": False,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    try:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("JSON result is not an object")
        evidence["parsed"] = True
        evidence["payload"] = payload
    except Exception as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
    return evidence


def exact_v2_bindings() -> dict[str, str]:
    expected = {
        "config": (CONFIG_PATH, V2_CONFIG_SHA256),
        "contract": (CONTRACT_PATH, V2_CONTRACT_SHA256),
        "client": (CLIENT_PATH, V2_CLIENT_SHA256),
        "worker": (WORKER_PATH, V2_WORKER_SHA256),
    }
    actual: dict[str, str] = {}
    for label, (path, digest) in expected.items():
        value = sha256_file(path)
        if not hmac.compare_digest(value, digest):
            raise RuntimeError(f"v2 {label} hash mismatch")
        actual[label] = value
    config = candidate_contract.load_candidate_config(CONFIG_PATH)
    candidate_contract.verify_candidate_config(config)
    return actual


def active_blender_evidence() -> dict[str, Any]:
    executable = (
        Path(os.environ.get("SystemRoot", r"C:\Windows"))
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )
    command = (
        "$items=@(Get-Process -Name blender -ErrorAction SilentlyContinue | "
        "Select-Object Id,Path,StartTime); "
        "[Console]::Out.Write((ConvertTo-Json -Compress -InputObject $items))"
    )
    completed = subprocess.run(
        [str(executable), "-NoProfile", "-Command", command],
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0:
        return {
            "query_succeeded": False,
            "active": None,
            "processes": [],
            "error": completed.stderr[-2000:],
        }
    try:
        payload = json.loads(completed.stdout or "[]")
        processes = payload if isinstance(payload, list) else [payload]
        processes = [item for item in processes if isinstance(item, dict)]
    except json.JSONDecodeError as exc:
        return {
            "query_succeeded": False,
            "active": None,
            "processes": [],
            "error": f"JSONDecodeError: {exc}",
        }
    return {
        "query_succeeded": True,
        "active": bool(processes),
        "processes": processes,
        "query_kind": "Get-Process_not_CIM_or_WMI",
        "processes_terminated": False,
    }


def next_attempt_number(names: list[str]) -> int:
    values = []
    for name in names:
        if name.startswith("attempt_") and name[8:].isdigit():
            values.append(int(name[8:]))
    return max(values, default=0) + 1


def allocate_attempt_directory() -> Path:
    ATTEMPT_ROOT.mkdir(parents=True, exist_ok=True)
    names = [item.name for item in ATTEMPT_ROOT.iterdir() if item.is_dir()]
    number = next_attempt_number(names)
    path = ATTEMPT_ROOT / f"attempt_{number:02d}"
    path.mkdir(exist_ok=False)
    return path


def _thread_stack(frame: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    while frame is not None:
        result.append(
            {
                "file": str(Path(frame.f_code.co_filename).resolve()),
                "function": frame.f_code.co_name,
                "line_number": int(frame.f_lineno),
            }
        )
        frame = frame.f_back
    return result


def prove_reader_parked_at_gate(timeout_seconds: float = 2.0) -> dict[str, Any]:
    source_lines = WORKER_PATH.read_text(encoding="utf-8").splitlines()
    gate_lines = [
        index + 1
        for index, value in enumerate(source_lines)
        if value.strip() == "request_complete.acquire()"
    ]
    readline_lines = [
        index + 1
        for index, value in enumerate(source_lines)
        if "sys.stdin.buffer.readline" in value
    ]
    if len(gate_lines) != 1 or len(readline_lines) != 1:
        raise RuntimeError("exact reader gate/readline source locations were not unique")
    deadline = time.monotonic() + max(0.1, min(2.0, timeout_seconds))
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        frames = sys._current_frames()
        readers = [
            item
            for item in threading.enumerate()
            if item.name == "persistent-blackwell-stdin-reader" and item.ident is not None
        ]
        if len(readers) == 1 and readers[0].ident in frames:
            stack = _thread_stack(frames[readers[0].ident])
            worker_frames = [
                item
                for item in stack
                if Path(item["file"]) == WORKER_PATH.resolve()
                and item["function"] == "_stdin_reader"
            ]
            parked = any(item["line_number"] == gate_lines[0] for item in worker_frames)
            in_readline = any(item["line_number"] == readline_lines[0] for item in worker_frames)
            last = {
                "reader_thread_name": readers[0].name,
                "reader_thread_ident": readers[0].ident,
                "gate_line_number": gate_lines[0],
                "readline_line_number": readline_lines[0],
                "reader_parked_at_request_gate": parked,
                "reader_readline_absent": not in_readline,
                "stack": stack,
            }
            if parked and not in_readline:
                return last
        time.sleep(0.01)
    raise RuntimeError(f"stdin reader was not proven parked at the request gate: {last}")


def _authorization_hmac(payload: dict[str, Any], key: bytes) -> str:
    return hmac.new(key, canonical_bytes(payload), hashlib.sha256).hexdigest()


def validate_authorization(
    path: Path,
    expected_sha256: str,
    attempt_directory: Path,
) -> dict[str, Any]:
    if os.environ.get(CHILD_MODE_ENV) != "1" or os.environ.get(LIVE_MODE_ENV) != "1":
        raise RuntimeError("child import-only live authorization environment is absent")
    key_hex = str(os.environ.get(AUTH_KEY_ENV) or "")
    try:
        key = bytes.fromhex(key_hex)
    except ValueError as exc:
        raise RuntimeError("child authorization key is malformed") from exc
    if len(key) != 32:
        raise RuntimeError("child authorization key is absent or invalid")
    if path.parent.resolve() != attempt_directory.resolve():
        raise RuntimeError("authorization record escaped the exact attempt directory")
    if not hmac.compare_digest(sha256_file(path), expected_sha256.casefold()):
        raise RuntimeError("authorization record hash mismatch")
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise RuntimeError("authorization record is not an object")
    supplied_hmac = str(record.pop("binding_hmac_sha256", ""))
    if not hmac.compare_digest(supplied_hmac, _authorization_hmac(record, key)):
        raise RuntimeError("authorization record HMAC mismatch")
    expected = {
        "schema_version": 1,
        "artifact_kind": "v2_inherited_pipe_torch_import_only_authorization",
        "live_import_authorized": True,
        "torch_import_only": True,
        "cuda_authorized": False,
        "model_authorized": False,
        "audio_authorized": False,
        "ollama_authorized": False,
        "routing_change_authorized": False,
        "child_hard_bound_seconds": CHILD_HARD_BOUND_SECONDS,
        "harness_sha256": sha256_file(HARNESS_PATH),
        "v2_config_sha256": V2_CONFIG_SHA256,
        "v2_contract_sha256": V2_CONTRACT_SHA256,
        "v2_client_sha256": V2_CLIENT_SHA256,
        "v2_worker_sha256": V2_WORKER_SHA256,
        "attempt_directory": attempt_directory.relative_to(ROOT).as_posix(),
    }
    for name, value in expected.items():
        if record.get(name) != value:
            raise RuntimeError(f"authorization binding mismatch: {name}")
    created_ns = record.get("created_time_ns")
    expires_ns = record.get("expires_time_ns")
    if type(created_ns) is not int or type(expires_ns) is not int:
        raise RuntimeError("authorization deadline fields are not exact integers")
    if expires_ns - created_ns != int(CHILD_HARD_BOUND_SECONDS * 1_000_000_000):
        raise RuntimeError("authorization child deadline span changed")
    if not created_ns <= time.time_ns() < expires_ns:
        raise RuntimeError("authorization record is expired or not yet valid")
    blender = active_blender_evidence()
    if blender.get("query_succeeded") is not True or blender.get("active") is not False:
        raise RuntimeError(f"child Blender gate failed: {blender}")
    record["binding_hmac_sha256"] = supplied_hmac
    return record


def _child_timeout_watchdog(
    stop: threading.Event,
    timeout_path: Path,
    authorization_sha256: str,
    state: dict[str, Any],
) -> None:
    if stop.wait(CHILD_HARD_BOUND_SECONDS):
        return
    payload = {
        "schema_version": 1,
        "artifact_kind": "v2_torch_import_only_child_timeout",
        "timed_out": True,
        "trusted_child_result": False,
        "authorization_sha256": authorization_sha256,
        "state_before_timeout": dict(state),
        "created_time_ns": time.time_ns(),
    }
    try:
        write_json_atomic_exclusive(timeout_path, payload)
    finally:
        os._exit(124)


def child_main(args: argparse.Namespace) -> int:
    attempt_directory = Path(args.attempt_directory).resolve()
    attempt_directory.relative_to(ATTEMPT_ROOT.resolve())
    authorization_path = Path(args.authorization_record).resolve()
    result_path = attempt_directory / "CHILD_RESULT.json"
    ready_path = attempt_directory / "CHILD_RESULT_READY.json"
    timeout_path = attempt_directory / "CHILD_TIMEOUT.json"
    authorization_sha256 = str(args.expected_authorization_sha256 or "").casefold()
    watchdog_stop = threading.Event()
    watchdog_state: dict[str, Any] = {"phase": "child_entry_before_authorization"}
    watchdog = threading.Thread(
        target=_child_timeout_watchdog,
        args=(watchdog_stop, timeout_path, authorization_sha256, watchdog_state),
        name="v2-import-only-child-hard-bound",
        daemon=True,
    )
    watchdog.start()
    result_state: dict[str, Any] = {}
    original_load = persistent_worker.PersistentVoiceRuntime.load
    try:
        validate_authorization(
            authorization_path,
            authorization_sha256,
            attempt_directory,
        )
        authorization_sha256 = sha256_file(authorization_path)
        watchdog_state["phase"] = "authorized_before_serve"
        exact_v2_bindings()
        config = candidate_contract.load_candidate_config(CONFIG_PATH)
        candidate_contract.verify_restricted_environment(config, require_load_opt_in=True)
        candidate_contract.verify_identity_files(config)

        def import_only_load(_runtime: Any, *, phase_event_callback=None) -> dict[str, Any]:
            gate = prove_reader_parked_at_gate()
            watchdog_state.update({"phase": "imports.torch", "reader_gate_proof": gate})
            if phase_event_callback is not None:
                phase_event_callback(
                    {
                        "phase_event_schema_version": 1,
                        "phase_state": "checkpoint",
                        "phase": "transport.stdin_reader_parked_before_torch_import",
                        "status": "passed",
                        "reader_gate_proof": gate,
                    }
                )
            started_ns = time.perf_counter_ns()
            ledger = candidate_contract.PhaseLedger(event_callback=phase_event_callback)
            with ledger.phase("imports.torch"):
                torch_module = importlib.import_module("torch")
            finished_ns = time.perf_counter_ns()
            prohibited_presence = {
                "torchaudio_imported": "torchaudio" in sys.modules,
                "chatterbox_imported": any(
                    name == "chatterbox" or name.startswith("chatterbox.") for name in sys.modules
                ),
            }
            if any(prohibited_presence.values()):
                raise RuntimeError(f"prohibited module imported: {prohibited_presence}")
            result_state.update(
                {
                    **gate,
                    "torch_imported": True,
                    "torch_version": str(getattr(torch_module, "__version__", "")),
                    "torch_import_elapsed_seconds": round(
                        (finished_ns - started_ns) / 1_000_000_000,
                        9,
                    ),
                    "requested_imports": ["torch"],
                    "cuda_api_called": False,
                    "torchaudio_imported": False,
                    "chatterbox_imported": False,
                    "model_loaded": False,
                    "audio_generated": False,
                    "playback": False,
                    "ollama_called": False,
                    "promotion_performed": False,
                    "production_routing_changed": False,
                    "generic_voice_used": False,
                    "sapi_voice_used": False,
                    "fallback_used": False,
                    "phase_timings": ledger.records,
                }
            )
            watchdog_state["phase"] = "torch_import_completed"
            return {
                "ready": True,
                "reason": "v2_inherited_pipe_torch_import_only_completed",
                "model_loaded": False,
                "audio_generated": False,
                "import_only": True,
                "reader_gate_proof": gate,
                "torch_version": result_state["torch_version"],
                "phase_timings": ledger.records,
            }

        persistent_worker.PersistentVoiceRuntime.load = import_only_load
        serve_code = persistent_worker.serve(config, str(os.environ.get("KIRA_PERSISTENT_BLACKWELL_SESSION_NONCE") or ""), [])
        result_state.update(
            {
                "schema_version": 1,
                "artifact_kind": "v2_inherited_pipe_torch_import_only_child_result",
                "trusted_child_result": True,
                "transport_serve_returned": serve_code == 0,
                "transport_eof_received": serve_code == 0,
                "serve_return_code": serve_code,
                "authorization_sha256": authorization_sha256,
                "harness_sha256": sha256_file(HARNESS_PATH),
                "v2_config_sha256": V2_CONFIG_SHA256,
                "v2_contract_sha256": V2_CONTRACT_SHA256,
                "v2_client_sha256": V2_CLIENT_SHA256,
                "v2_worker_sha256": V2_WORKER_SHA256,
                "created_time_ns": time.time_ns(),
            }
        )
        result_sha256 = write_json_atomic_exclusive(result_path, result_state)
        result_bytes = result_path.stat().st_size
        write_json_atomic_exclusive(
            ready_path,
            {
                "schema_version": 1,
                "artifact_kind": "v2_inherited_pipe_torch_import_only_child_ready",
                "authorization_sha256": authorization_sha256,
                "child_result_sha256": result_sha256,
                "child_result_bytes": result_bytes,
                "harness_sha256": sha256_file(HARNESS_PATH),
                "v2_config_sha256": V2_CONFIG_SHA256,
                "v2_contract_sha256": V2_CONTRACT_SHA256,
                "v2_client_sha256": V2_CLIENT_SHA256,
                "v2_worker_sha256": V2_WORKER_SHA256,
                "trusted_child_result": True,
            },
        )
        return 0
    except Exception as exc:
        watchdog_state.update(
            {
                "phase": "child_failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
        failure = {
            "schema_version": 1,
            "artifact_kind": "v2_inherited_pipe_torch_import_only_child_result",
            "trusted_child_result": False,
            "status": "failed",
            "authorization_sha256": authorization_sha256,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc()[-16000:],
            "created_time_ns": time.time_ns(),
        }
        if not result_path.exists():
            try:
                write_json_atomic_exclusive(result_path, failure)
            except Exception as evidence_exc:
                print(
                    json.dumps(
                        {
                            "trusted_child_result": False,
                            "reason": "child_failure_evidence_write_failed",
                            "error": f"{type(evidence_exc).__name__}: {evidence_exc}",
                        },
                        sort_keys=True,
                    ),
                    file=sys.stderr,
                )
        return 2
    finally:
        persistent_worker.PersistentVoiceRuntime.load = original_load
        watchdog_stop.set()
        watchdog.join(timeout=1)


def validate_trusted_result(
    result_evidence: dict[str, Any],
    ready_evidence: dict[str, Any],
    authorization_sha256: str,
) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if result_evidence.get("parsed") is not True or ready_evidence.get("parsed") is not True:
        return False, ["atomic_result_or_ready_marker_missing_or_malformed"]
    result = result_evidence["payload"]
    ready = ready_evidence["payload"]
    for key in TRUE_RESULT_FIELDS:
        if type(result.get(key)) is not bool or result.get(key) is not True:
            issues.append(f"{key}_not_exact_true")
    for key in FALSE_OUTCOME_FIELDS:
        if type(result.get(key)) is not bool or result.get(key) is not False:
            issues.append(f"{key}_not_exact_false")
    expected_strings = {
        "authorization_sha256": authorization_sha256,
        "harness_sha256": sha256_file(HARNESS_PATH),
        "v2_config_sha256": V2_CONFIG_SHA256,
        "v2_contract_sha256": V2_CONTRACT_SHA256,
        "v2_client_sha256": V2_CLIENT_SHA256,
        "v2_worker_sha256": V2_WORKER_SHA256,
    }
    for key, value in expected_strings.items():
        if result.get(key) != value:
            issues.append(f"{key}_mismatch")
    if result.get("requested_imports") != ["torch"]:
        issues.append("requested_imports_not_exact_torch_only")
    if result.get("torch_version") != "2.11.0+cu130":
        issues.append("torch_version_mismatch")
    if type(result.get("serve_return_code")) is not int or result.get("serve_return_code") != 0:
        issues.append("serve_return_code_not_exact_zero")
    if ready.get("trusted_child_result") is not True:
        issues.append("ready_marker_not_trusted")
    if ready.get("authorization_sha256") != authorization_sha256:
        issues.append("ready_authorization_mismatch")
    if ready.get("child_result_sha256") != result_evidence.get("sha256"):
        issues.append("ready_result_hash_mismatch")
    if ready.get("child_result_bytes") != result_evidence.get("bytes"):
        issues.append("ready_result_size_mismatch")
    for key in (
        "harness_sha256",
        "v2_config_sha256",
        "v2_contract_sha256",
        "v2_client_sha256",
        "v2_worker_sha256",
    ):
        if ready.get(key) != result.get(key):
            issues.append(f"ready_{key}_mismatch")
    return not issues, issues


def trusted_outcomes(result_evidence: dict[str, Any], trusted: bool) -> dict[str, bool | None]:
    if not trusted:
        return {key: None for key in FALSE_OUTCOME_FIELDS}
    payload = result_evidence["payload"]
    return {key: payload[key] for key in FALSE_OUTCOME_FIELDS}


class ImportOnlyClient(candidate_client.PersistentBlackwellVoiceCandidateClient):
    def __init__(
        self,
        *,
        command: list[str],
        child_environment: dict[str, str],
        parent_deadline: float,
        diagnostic_directory: Path,
    ) -> None:
        self._harness_command = list(command)
        self._harness_environment = dict(child_environment)
        self._parent_deadline = parent_deadline
        self.cleanup_evidence: dict[str, Any] | None = None
        super().__init__(
            allow_gpu_model_load=True,
            startup_timeout_seconds=20,
            request_timeout_seconds=125,
            diagnostic_directory=diagnostic_directory,
        )

    def _command(self) -> list[str]:
        return list(self._harness_command)

    def _spawn(self, command: list[str], environment: dict[str, str]):
        exact = dict(environment)
        exact.update(self._harness_environment)
        return super()._spawn(command, exact)

    def close(self) -> dict[str, Any] | None:
        if self.process is None:
            return self.cleanup_evidence
        self.cleanup_evidence = cleanup_exact_client(self, self._parent_deadline)
        return self.cleanup_evidence


def cleanup_exact_client(client: ImportOnlyClient, deadline: float) -> dict[str, Any]:
    process = client.process
    if process is None:
        return {"owned_process_present": False, "drains_finalized": True}
    evidence: dict[str, Any] = {
        "owned_process_present": True,
        "owned_pid": process.pid,
        "terminate_sent": False,
        "kill_sent": False,
    }

    def wait_owned(maximum_seconds: float) -> bool:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return process.poll() is not None
        try:
            process.wait(timeout=min(maximum_seconds, remaining))
            return True
        except subprocess.TimeoutExpired:
            return False

    try:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        if process.poll() is None:
            if not wait_owned(2.0):
                process.terminate()
                evidence["terminate_sent"] = True
                if not wait_owned(2.0):
                    process.kill()
                    evidence["kill_sent"] = True
                    if not wait_owned(2.0):
                        evidence["owned_process_exit_not_observed_before_deadline"] = True
        for thread in (client._stdout_thread, client._stderr_thread):
            if thread is not None:
                thread.join(timeout=max(0.0, min(2.0, deadline - time.monotonic())))
        evidence["drains_finalized"] = all(
            thread is None or not thread.is_alive()
            for thread in (client._stdout_thread, client._stderr_thread)
        )
        evidence["owned_process_exit_code"] = process.returncode
        return evidence
    finally:
        for stream in (process.stdin, process.stdout, process.stderr):
            try:
                if stream is not None and not stream.closed:
                    stream.close()
            except OSError:
                pass
        client.process = None


def describe() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "artifact_kind": "v2_inherited_pipe_torch_import_only_description",
        "live_import_performed": False,
        "child_hard_bound_seconds": CHILD_HARD_BOUND_SECONDS,
        "parent_total_bound_seconds": PARENT_TOTAL_BOUND_SECONDS,
        "candidate_status": "inactive_private_candidate_not_production",
        "imports_authorized": ["torch"],
        "cuda_authorized": False,
        "model_authorized": False,
        "audio_authorized": False,
        "ollama_authorized": False,
        "routing_change_authorized": False,
        "required_hashes": {
            "v2_config": V2_CONFIG_SHA256,
            "v2_contract": V2_CONTRACT_SHA256,
            "v2_client": V2_CLIENT_SHA256,
            "v2_worker": V2_WORKER_SHA256,
        },
        "required_flags": [
            "--run-import",
            "--confirm-no-active-blender",
            "--expected-harness-sha256 <CURRENT_EXACT_SHA256>",
            "--expected-v2-config-sha256 <SEALED_SHA256>",
            "--expected-v2-contract-sha256 <SEALED_SHA256>",
            "--expected-v2-client-sha256 <SEALED_SHA256>",
            "--expected-v2-worker-sha256 <SEALED_SHA256>",
        ],
    }


def static_self_check() -> dict[str, Any]:
    torch_before = "torch" in sys.modules
    bindings = exact_v2_bindings()
    tree = ast.parse(HARNESS_PATH.read_text(encoding="utf-8"))
    top_imports: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            top_imports.add(str(node.module or "").split(".")[0])
    dynamic_imports = [
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "importlib"
        and node.func.attr == "import_module"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ]
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    checks = {
        "no_top_level_torch_torchaudio_chatterbox": {
            "torch",
            "torchaudio",
            "chatterbox",
        }.isdisjoint(top_imports),
        "exact_dynamic_import_allowlist": dynamic_imports == ["torch"],
        "no_cuda_api_call": "cuda" not in called_attributes,
        "no_qwen_or_model_loader_call": {
            "qwen_residency_evidence",
            "from_pretrained",
            "prepare_conditionals",
            "generate",
        }.isdisjoint(called_attributes | called_names),
        "child_bound_exact_120": CHILD_HARD_BOUND_SECONDS == 120.0,
        "parent_bound_stricter_than_180": PARENT_TOTAL_BOUND_SECONDS < 180.0,
        "parent_exceeds_child_with_cleanup_reserve": (
            PARENT_TOTAL_BOUND_SECONDS >= CHILD_HARD_BOUND_SECONDS + CLEANUP_RESERVE_SECONDS
        ),
        "timeout_outcomes_are_null_without_trust": all(
            value is None for value in trusted_outcomes({}, False).values()
        ),
    }
    return {
        "schema_version": 1,
        "artifact_kind": "v2_inherited_pipe_torch_import_only_static_self_check",
        "passed": all(checks.values()),
        "checks": checks,
        "harness_sha256": sha256_file(HARNESS_PATH),
        "v2_bindings": bindings,
        "torch_imported_before": torch_before,
        "torch_imported_after": "torch" in sys.modules,
        "live_import_performed": False,
        "attempt_directory_created": False,
        "cuda_called": False,
        "model_loaded": False,
        "audio_generated": False,
        "ollama_called": False,
    }


def run_live(args: argparse.Namespace) -> int:
    expected_cli = {
        "expected_v2_config_sha256": V2_CONFIG_SHA256,
        "expected_v2_contract_sha256": V2_CONTRACT_SHA256,
        "expected_v2_client_sha256": V2_CLIENT_SHA256,
        "expected_v2_worker_sha256": V2_WORKER_SHA256,
    }
    if not args.run_import or not args.confirm_no_active_blender:
        print(json.dumps({"live_import_performed": False, "reason": "explicit_live_flags_required"}))
        return 2
    if not hmac.compare_digest(str(args.expected_harness_sha256 or "").casefold(), sha256_file(HARNESS_PATH)):
        print(json.dumps({"live_import_performed": False, "reason": "exact_harness_hash_required"}))
        return 2
    for name, value in expected_cli.items():
        if not hmac.compare_digest(str(getattr(args, name) or "").casefold(), value):
            print(json.dumps({"live_import_performed": False, "reason": f"exact_{name}_required"}))
            return 2
    bindings = exact_v2_bindings()
    blender = active_blender_evidence()
    if blender.get("query_succeeded") is not True or blender.get("active") is not False:
        print(json.dumps({"live_import_performed": False, "reason": "no_active_blender_not_proven", "blender": blender}))
        return 2

    operation_started = time.monotonic()
    parent_deadline = operation_started + PARENT_TOTAL_BOUND_SECONDS
    attempt = allocate_attempt_directory()
    auth_key = secrets.token_bytes(32)
    created_ns = time.time_ns()
    authorization_payload = {
        "schema_version": 1,
        "artifact_kind": "v2_inherited_pipe_torch_import_only_authorization",
        "live_import_authorized": True,
        "torch_import_only": True,
        "cuda_authorized": False,
        "model_authorized": False,
        "audio_authorized": False,
        "ollama_authorized": False,
        "routing_change_authorized": False,
        "child_hard_bound_seconds": CHILD_HARD_BOUND_SECONDS,
        "created_time_ns": created_ns,
        "expires_time_ns": created_ns + int(CHILD_HARD_BOUND_SECONDS * 1_000_000_000),
        "harness_sha256": sha256_file(HARNESS_PATH),
        "v2_config_sha256": V2_CONFIG_SHA256,
        "v2_contract_sha256": V2_CONTRACT_SHA256,
        "v2_client_sha256": V2_CLIENT_SHA256,
        "v2_worker_sha256": V2_WORKER_SHA256,
        "attempt_directory": attempt.relative_to(ROOT).as_posix(),
        "parent_pid": os.getpid(),
        "blender_gate": blender,
    }
    authorization = {
        **authorization_payload,
        "binding_hmac_sha256": _authorization_hmac(authorization_payload, auth_key),
    }
    authorization_path = attempt / "PARENT_AUTHORIZATION.json"
    authorization_sha256 = write_json_atomic_exclusive(authorization_path, authorization)
    write_json_atomic_exclusive(
        attempt / "ATTEMPT_STARTED.json",
        {
            "schema_version": 1,
            "artifact_kind": "v2_inherited_pipe_torch_import_only_started",
            "authorization_sha256": authorization_sha256,
            "harness_sha256": sha256_file(HARNESS_PATH),
            "v2_bindings": bindings,
            "blender": blender,
            "child_hard_bound_seconds": CHILD_HARD_BOUND_SECONDS,
            "parent_total_bound_seconds": PARENT_TOTAL_BOUND_SECONDS,
            "created_time_ns": time.time_ns(),
        },
    )
    command = [
        str(candidate_contract.project_file(candidate_contract.load_candidate_config(CONFIG_PATH)["python"])),
        str(HARNESS_PATH),
        "--child-mode",
        "--attempt-directory",
        str(attempt),
        "--authorization-record",
        str(authorization_path),
        "--expected-authorization-sha256",
        authorization_sha256,
    ]
    client = ImportOnlyClient(
        command=command,
        child_environment={
            AUTH_KEY_ENV: auth_key.hex(),
            CHILD_MODE_ENV: "1",
            LIVE_MODE_ENV: "1",
        },
        parent_deadline=parent_deadline,
        diagnostic_directory=attempt,
    )
    hello: dict[str, Any] | None = None
    load_response: dict[str, Any] | None = None
    controller_error: str | None = None
    cleanup: dict[str, Any] = {}
    try:
        hello = client.start()
        request_timeout = max(
            1.0,
            min(123.0, parent_deadline - time.monotonic() - CLEANUP_RESERVE_SECONDS),
        )
        load_response = client._request("load", _timeout_seconds=request_timeout)
    except Exception as exc:
        controller_error = f"{type(exc).__name__}: {exc}"
    finally:
        cleanup = client.close() or {}

    drains_finalized = cleanup.get("drains_finalized") is True
    result_evidence = safe_json_evidence(attempt / "CHILD_RESULT.json")
    ready_evidence = safe_json_evidence(attempt / "CHILD_RESULT_READY.json")
    timeout_evidence = safe_json_evidence(attempt / "CHILD_TIMEOUT.json")
    trusted, validation_issues = validate_trusted_result(
        result_evidence,
        ready_evidence,
        authorization_sha256,
    )
    if not drains_finalized:
        trusted = False
        validation_issues.append("client_drain_threads_not_finalized")
    if trusted:
        expected_load = {
            "ready": True,
            "reason": "v2_inherited_pipe_torch_import_only_completed",
            "model_loaded": False,
            "audio_generated": False,
            "import_only": True,
            "torch_version": "2.11.0+cu130",
        }
        for key, value in expected_load.items():
            if not isinstance(load_response, dict) or load_response.get(key) != value:
                validation_issues.append(f"load_response_{key}_mismatch")
        if cleanup.get("owned_process_exit_code") != 0:
            validation_issues.append("owned_process_exit_not_zero")
        if cleanup.get("terminate_sent") is not False or cleanup.get("kill_sent") is not False:
            validation_issues.append("owned_process_required_forced_cleanup")
        if sha256_file(ROOT / "Voice" / "sidecars" / "kira_approved_voice_routing.json") != (
            "a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81"
        ):
            validation_issues.append("production_routing_hash_changed")
        if validation_issues:
            trusted = False
    diagnostic_hashes: dict[str, str] | None = None
    if drains_finalized:
        diagnostic_hashes = {}
        for name in ("WORKER_PHASE_EVENTS.jsonl", "WORKER_STDERR_FAULTHANDLER.log"):
            path = attempt / name
            if path.is_file():
                diagnostic_hashes[name] = sha256_file(path)
    parent_bound_exceeded = time.monotonic() > parent_deadline
    if parent_bound_exceeded:
        trusted = False
        validation_issues.append("parent_total_bound_exceeded")
    report = {
        "schema_version": 1,
        "artifact_kind": "v2_inherited_pipe_torch_import_only_final_report",
        "status": "passed" if trusted and controller_error is None else "failed_preserved",
        "trusted_child_result": trusted,
        "validation_issues": validation_issues,
        "controller_error": controller_error,
        "hello": hello,
        "load_response": load_response,
        "phase_events": client.events,
        "cleanup": cleanup,
        "drains_finalized_before_diagnostic_hashes": drains_finalized,
        "diagnostic_hashes": diagnostic_hashes,
        "child_result_evidence": result_evidence,
        "child_ready_evidence": ready_evidence,
        "child_timeout_evidence": timeout_evidence,
        "outcomes": trusted_outcomes(result_evidence, trusted),
        "observed_wall_seconds": round(time.monotonic() - operation_started, 9),
        "parent_total_bound_seconds": PARENT_TOTAL_BOUND_SECONDS,
        "parent_bound_exceeded": parent_bound_exceeded,
        "promotion_performed": False,
        "routing_change_performed": False,
    }
    report_sha256 = write_json_atomic_exclusive(attempt / "FINAL_REPORT.json", report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "attempt": attempt.relative_to(ROOT).as_posix(),
                "final_report_sha256": report_sha256,
                "trusted_child_result": trusted,
            },
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "passed" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--describe", action="store_true")
    mode.add_argument("--static-self-check", action="store_true")
    mode.add_argument("--run-import", action="store_true")
    mode.add_argument("--child-mode", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--confirm-no-active-blender", action="store_true")
    parser.add_argument("--expected-harness-sha256")
    parser.add_argument("--expected-v2-config-sha256")
    parser.add_argument("--expected-v2-contract-sha256")
    parser.add_argument("--expected-v2-client-sha256")
    parser.add_argument("--expected-v2-worker-sha256")
    parser.add_argument("--attempt-directory", help=argparse.SUPPRESS)
    parser.add_argument("--authorization-record", help=argparse.SUPPRESS)
    parser.add_argument("--expected-authorization-sha256", help=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.describe:
        print(json.dumps(describe(), indent=2, sort_keys=True))
        return 0
    if args.static_self_check:
        result = static_self_check()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 1
    if args.child_mode:
        try:
            return child_main(args)
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "trusted_child_result": False,
                        "reason": "child_mode_gate_failed_before_import",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                    sort_keys=True,
                )
            )
            return 2
    return run_live(args)


if __name__ == "__main__":
    raise SystemExit(main())
