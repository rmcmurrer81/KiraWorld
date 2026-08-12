"""Parent R6 static successor for one private Qwen3-TTS original voice run.

The shipped R6 payload and binding are disabled.  This source contains the
future bounded parent path but performs nothing without a separately audited,
hash-pinned, one-use external authorization.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import traceback
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
R6_PAYLOAD_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v6.json")
R6_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r6_guards.py")
R6_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v6.py")
R6_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v6.py")
R5_PAYLOAD_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v5.json")
R5_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r5_guards.py")
R5_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v5.py")
R5_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v5.py")
R4_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r4_guards.py")
R4_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v4.py")
R4_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v4.py")
R3_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r3_guards.py")
R3_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v3.py")
R2_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py")
R2_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v2.py")
R2_CONTRACT_REL = Path("TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json")
R2_ENVIRONMENT_REL = Path("Voice/sidecars/qwen3_tts_voice_forge_v2/environment_spec_v2.json")
R2_REGISTRY_REL = Path("Data/voice/policies/temporaryai_qwen3_tts_voice_forge_bundle_registry_v2.json")
R2_CORPUS_REL = Path("Data/voice/policies/qwen3_tts_voice_forge_evaluation_corpus_v2.json")
R4_MANIFEST_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v4.json")
R5_AUDIT_REL = Path(
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R5_INDEPENDENT_AUDIT_20260809.md"
)
R5_AUDIT_SHA256 = "82ea5a0a543fde40f7a1d05dc166798f98acbd9ae120c11ba8fb7f9ffbb5f43a"
OUTPUT_ROOT_REL = Path("Voice/voice_forge/private_review_v6")
LEDGER_ROOT_REL = Path("Data/voice/runtime/qwen3_tts_voice_forge_authorization_ledger_v6")
RESERVATION_ROOT_REL = Path(
    "Data/voice/runtime/qwen3_tts_voice_forge_parent_reservations_v6"
)
INCIDENT_ROOT_REL = Path("RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r6/runtime_incidents")
HASH = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")


R6_REQUIRED_PAYLOADS = {
    path.as_posix()
    for path in (
        R6_GUARDS_REL,
        R6_WORKER_REL,
        R6_RUNNER_REL,
        R5_PAYLOAD_REL,
        R5_GUARDS_REL,
        R5_WORKER_REL,
        R5_RUNNER_REL,
        R4_GUARDS_REL,
        R4_RUNNER_REL,
        R4_WORKER_REL,
        R4_MANIFEST_REL,
        Path(
            "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R4_INDEPENDENT_AUDIT_20260809.md"
        ),
        R3_GUARDS_REL,
        R3_RUNNER_REL,
        Path("tools/qwen3_tts_original_voice_forge_worker_v3.py"),
        Path("TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v3.json"),
        R2_WORKER_REL,
        R2_RUNNER_REL,
        R2_CONTRACT_REL,
        R2_ENVIRONMENT_REL,
        R2_REGISTRY_REL,
        R2_CORPUS_REL,
        R5_AUDIT_REL,
        Path("System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R6_REPAIR_BOUNDARY_20260810.md"),
    )
}


class R6LauncherError(RuntimeError):
    """The R6 parent failed closed."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise R6LauncherError("R6 path escaped project") from exc


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise R6LauncherError(f"duplicate bootstrap JSON key: {key}")
        result[key] = value
    return result


def _object(path: Path, expected_hash: str | None, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise R6LauncherError(f"{label} is missing or unsafe")
    payload = path.read_bytes()
    if expected_hash is not None and (
        not HASH.fullmatch(str(expected_hash or "")) or sha256_bytes(payload) != expected_hash
    ):
        raise R6LauncherError(f"{label} differs from its exact external hash")
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise R6LauncherError(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise R6LauncherError(f"{label} is not an object")
    return value


def bootstrap_external_trust(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    """Verify R6 payload and authority before importing any dependency."""

    manifest = _object(PROJECT_ROOT / R6_PAYLOAD_REL, args.payload_manifest_sha256, "R6 parent bootstrap payload")
    if (
        manifest.get("schema") != "qwen3_tts_voice_forge_payload_manifest_v6"
        or manifest.get("status")
        != "IMMUTABLE_STATIC_PAYLOAD_REQUIRES_FRESH_AUDIT_AND_EXTERNAL_AUTHORIZATION"
        or manifest.get("execution_allowed") is not False
        or manifest.get("self_authorization_allowed") is not False
        or manifest.get("predecessor_payload_manifest_path") != R5_PAYLOAD_REL.as_posix()
        or manifest.get("rejected_r5_audit_path") != R5_AUDIT_REL.as_posix()
        or manifest.get("rejected_r5_audit_sha256") != R5_AUDIT_SHA256
        or sha256_file(PROJECT_ROOT / R5_AUDIT_REL) != R5_AUDIT_SHA256
    ):
        raise R6LauncherError("R6 bootstrap payload self-authorized or lost rejected R5")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise R6LauncherError("R6 payload inventory is not a list")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
            raise R6LauncherError("R6 payload row is not exact")
        rel = str(row.get("path") or "")
        path = (PROJECT_ROOT / rel).resolve()
        if rel in indexed or rel not in R6_REQUIRED_PAYLOADS or relative(path) != rel:
            raise R6LauncherError("R6 payload row is duplicate, unexpected, or unsafe")
        if (
            not path.is_file() or path.is_symlink()
            or path.stat().st_size != row.get("bytes")
            or sha256_file(path) != row.get("sha256")
        ):
            raise R6LauncherError(f"R6 payload drift: {rel}")
        indexed[rel] = row
    if set(indexed) != R6_REQUIRED_PAYLOADS:
        raise R6LauncherError("R6 payload inventory is incomplete")
    authorization_path = Path(args.execution_authorization).resolve()
    auth_rel = relative(authorization_path)
    if not auth_rel.startswith("Data/voice/authorizations/qwen3_tts_voice_forge_v6/"):
        raise R6LauncherError("R6 authorization root mismatch")
    authorization = _object(authorization_path, args.execution_authorization_sha256, "R6 parent bootstrap authorization")
    if (
        authorization.get("schema") != "qwen3_tts_voice_forge_execution_authorization_v6"
        or authorization.get("status") != "FRESH_R6_AUDIT_ACCEPTED_ONE_BOUNDED_RUN"
        or authorization.get("execution_allowed") is not True
        or authorization.get("one_use") is not True
        or authorization.get("payload_manifest_path") != R6_PAYLOAD_REL.as_posix()
        or authorization.get("payload_manifest_sha256") != args.payload_manifest_sha256
        or authorization.get("rejected_r5_audit_path") != R5_AUDIT_REL.as_posix()
        or authorization.get("rejected_r5_audit_sha256") != R5_AUDIT_SHA256
        or authorization.get("bundle_id") != args.bundle_id
        or authorization.get("run_id") != args.run_id
    ):
        raise R6LauncherError("R6 parent bootstrap authorization mismatch")
    return manifest, indexed, authorization


def load_sealed_module(rel: Path, row: dict[str, Any], name: str) -> Any:
    path = (PROJECT_ROOT / rel).resolve()
    if (
        not path.is_file() or path.is_symlink()
        or path.stat().st_size != row.get("bytes")
        or sha256_file(path) != row.get("sha256")
    ):
        raise R6LauncherError(f"R6 sealed dependency drift: {rel.as_posix()}")
    source = path.read_bytes()
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(source, str(path), "exec", dont_inherit=True, optimize=0), module.__dict__)
    if sha256_file(path) != row.get("sha256"):
        raise R6LauncherError(f"R6 dependency changed during import: {rel.as_posix()}")
    return module


def reserve_pending(run_id: str, bundle_id: str) -> Path:
    root = PROJECT_ROOT / OUTPUT_ROOT_REL / run_id / bundle_id
    root.mkdir(parents=True, exist_ok=True)
    for index in range(1, 1000):
        pending = root / f"attempt_{index:03d}"
        try:
            pending.mkdir(exist_ok=False)
            return pending
        except FileExistsError:
            continue
    raise R6LauncherError("no append-only R6 attempt slot remains")


def reserve_incident(r6: Any, bundle_id: str, run_id: str) -> Path:
    return r6.reserve_incident(PROJECT_ROOT / INCIDENT_ROOT_REL, bundle_id, run_id)


def _ledger_path(authorization_hash: str) -> Path:
    return PROJECT_ROOT / LEDGER_ROOT_REL / f"{authorization_hash}.json"


def write_parent_reservations(
    *,
    r6: Any,
    r5: Any,
    v2: Any,
    pending: Path,
    args: argparse.Namespace,
    authorization: dict[str, Any],
    authorization_evidence: dict[str, Any],
    bundle: dict[str, Any],
    binding: dict[str, str],
    job_evidence: dict[str, Any],
    entry: dict[str, Any],
    parent_preflight: dict[str, Any],
    parent_full_preflight: dict[str, Any],
    nonce_ledger: Path,
    nonce_ledger_hash: str,
) -> tuple[dict[str, Any], Path, str, Path, dict[str, Any], str]:
    frozen = {
        "schema": "qwen3_tts_voice_forge_parent_reservation_v2",
        "status": "RESERVED_AND_NONCE_CONSUMED_FOR_EXACT_QUEUE",
        "r4_schema": "qwen3_tts_voice_forge_parent_reservation_v4",
        "r5_schema": "qwen3_tts_voice_forge_parent_reservation_v5",
        "r6_schema": "qwen3_tts_voice_forge_parent_reservation_v6",
        "utc": r6.utc_now(),
        **binding,
        **v2.queue_binding_payload(bundle),
        "attempt": relative(pending),
        "nonce_ledger_path": relative(nonce_ledger),
        "nonce_ledger_sha256": nonce_ledger_hash,
        "verified_worker_path": R2_WORKER_REL.as_posix(),
        "verified_worker_sha256": sha256_file(PROJECT_ROOT / R2_WORKER_REL),
        "verified_entry_worker_path": R6_WORKER_REL.as_posix(),
        "verified_entry_worker_sha256": sha256_file(PROJECT_ROOT / R6_WORKER_REL),
        "verified_frozen_core_worker_path": R2_WORKER_REL.as_posix(),
        "verified_frozen_core_worker_sha256": sha256_file(PROJECT_ROOT / R2_WORKER_REL),
        "verified_frozen_r3_worker_path": "tools/qwen3_tts_original_voice_forge_worker_v3.py",
        "verified_frozen_r3_worker_sha256": sha256_file(PROJECT_ROOT / "tools/qwen3_tts_original_voice_forge_worker_v3.py"),
        "harness_manifest_sha256": sha256_file(PROJECT_ROOT / R4_MANIFEST_REL),
        "contract_sha256": sha256_file(PROJECT_ROOT / R2_CONTRACT_REL),
        "environment_spec_sha256": sha256_file(PROJECT_ROOT / R2_ENVIRONMENT_REL),
        "trusted_registry_sha256": sha256_file(PROJECT_ROOT / R2_REGISTRY_REL),
        "bundle_seal_sha256": entry["bundle_seal_sha256"],
        "verified_original_synthetic_job": job_evidence,
        "exact_wheel_to_installed_bindings": parent_preflight,
        "network_boundary": "OFFLINE_FLAGS_ONLY_NO_PROCESS_LEVEL_NETWORK_DENIAL",
        "network_nonuse_proven": False,
    }
    r6.write_new_json(pending / "parent_reservation.json", frozen)
    ledger_path = _ledger_path(args.execution_authorization_sha256)
    reservation_v6 = {
        "schema": "qwen3_tts_voice_forge_parent_reservation_v6",
        "status": "EXTERNAL_AUTHORITY_PARENT_PREFLIGHT_AND_WORKER_IDENTITY_RESERVED",
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "attempt": relative(pending),
        "payload_manifest_sha256": args.payload_manifest_sha256,
        "execution_authorization_sha256": args.execution_authorization_sha256,
        "authorization_nonce_sha256": authorization["authorization_nonce_sha256"],
        "worker_instance_nonce_sha256": authorization["worker_instance_nonce_sha256"],
        "generation_seed": authorization["generation_seed"],
        "parent_authorization_ledger_path": relative(ledger_path),
        "verified_entry_worker_path": R6_WORKER_REL.as_posix(),
        "verified_entry_worker_sha256": sha256_file(PROJECT_ROOT / R6_WORKER_REL),
        "exact_parent_preflight_provenance": parent_preflight,
        "exact_parent_full_provenance": parent_full_preflight,
        "exact_parent_full_provenance_sha256": r6.canonical_sha256(parent_full_preflight),
        "frozen_parent_reservation_sha256": sha256_file(pending / "parent_reservation.json"),
    }
    # This exact one-use reservation must outlive the later atomic rename of
    # the attempt directory.  A reservation inside ``pending`` would make the
    # ledger and worker claim point at a path that stops existing after a
    # successful finalization.
    reservation_path = (
        PROJECT_ROOT
        / RESERVATION_ROOT_REL
        / f"{args.execution_authorization_sha256}.json"
    )
    r6.write_new_json(reservation_path, reservation_v6)
    reservation_hash = sha256_file(reservation_path)
    ledger = {
        "schema": "qwen3_tts_voice_forge_authorization_ledger_v6",
        "status": "CONSUMED_FOR_ONE_EXACT_PENDING_ATTEMPT",
        "utc": r6.utc_now(),
        "authorization_sha256": args.execution_authorization_sha256,
        "authorization_nonce_sha256": authorization["authorization_nonce_sha256"],
        "worker_instance_nonce_sha256": authorization["worker_instance_nonce_sha256"],
        "payload_manifest_sha256": args.payload_manifest_sha256,
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "attempt": relative(pending),
        "parent_reservation_path": relative(reservation_path),
        "parent_reservation_sha256": reservation_hash,
        "verified_worker_path": R6_WORKER_REL.as_posix(),
        "verified_worker_sha256": sha256_file(PROJECT_ROOT / R6_WORKER_REL),
    }
    r6.write_new_json(ledger_path, ledger)
    ledger_hash = sha256_file(ledger_path)
    expected = {key: value for key, value in ledger.items() if key not in {"schema", "status", "utc"}}
    r6.validate_parent_ledger(ledger, expected=expected)
    compatibility_v5 = {
        "schema": "qwen3_tts_voice_forge_parent_reservation_v5",
        "status": "EXTERNAL_AUTHORITY_AND_PARENT_PREFLIGHT_RESERVED",
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "attempt": relative(pending),
        "payload_manifest_sha256": args.payload_manifest_sha256,
        "execution_authorization": authorization_evidence,
        "execution_authorization_sha256": args.execution_authorization_sha256,
        "authorization_ledger_path": relative(ledger_path),
        "authorization_ledger_sha256": ledger_hash,
        "exact_parent_preflight_provenance": parent_preflight,
        "exact_parent_full_provenance": parent_full_preflight,
        "exact_parent_full_provenance_sha256": r5.canonical_sha256(parent_full_preflight),
        "frozen_parent_reservation_sha256": sha256_file(pending / "parent_reservation.json"),
    }
    r6.write_new_json(pending / "parent_reservation_v5.json", compatibility_v5)
    return (
        reservation_v6,
        reservation_path,
        reservation_hash,
        ledger_path,
        ledger,
        ledger_hash,
    )


class _JobBasicLimit(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32), ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t), ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64), ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64), ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64), ("OtherTransferCount", ctypes.c_uint64),
    ]


class _JobExtendedLimit(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JobBasicLimit), ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _JobBasicAccounting(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_int64), ("TotalKernelTime", ctypes.c_int64),
        ("ThisPeriodTotalUserTime", ctypes.c_int64), ("ThisPeriodTotalKernelTime", ctypes.c_int64),
        ("TotalPageFaultCount", ctypes.c_uint32), ("TotalProcesses", ctypes.c_uint32),
        ("ActiveProcesses", ctypes.c_uint32), ("TotalTerminatedProcesses", ctypes.c_uint32),
    ]


def run_contained_worker_v6(command: list[str], *, env: dict[str, str], timeout: float) -> tuple[subprocess.CompletedProcess[bytes], dict[str, Any]]:
    """Run in a Windows Job and query parent-owned peaks/IO after quiescence."""

    if os.name != "nt":
        raise R6LauncherError("R6 bounded worker containment is Windows-only")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
    create_job = kernel32.CreateJobObjectW
    create_job.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    create_job.restype = ctypes.c_void_p
    set_job = kernel32.SetInformationJobObject
    set_job.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    set_job.restype = ctypes.c_int
    assign_job = kernel32.AssignProcessToJobObject
    assign_job.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    assign_job.restype = ctypes.c_int
    terminate_job = kernel32.TerminateJobObject
    terminate_job.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    terminate_job.restype = ctypes.c_int
    query_job = kernel32.QueryInformationJobObject
    query_job.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    query_job.restype = ctypes.c_int
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    close_handle.restype = ctypes.c_int
    resume_process = ntdll.NtResumeProcess
    resume_process.argtypes = [ctypes.c_void_p]
    resume_process.restype = ctypes.c_long
    job = create_job(None, None)
    if not job:
        raise R6LauncherError("cannot create R6 Job Object")
    info = _JobExtendedLimit()
    info.BasicLimitInformation.LimitFlags = 0x00002000
    if not set_job(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
        close_handle(job)
        raise R6LauncherError("cannot configure R6 Job Object")
    process: subprocess.Popen[bytes] | None = None
    started = time.perf_counter()
    try:
        process = subprocess.Popen(
            command, cwd=str(PROJECT_ROOT), env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=0x00000004 | 0x00000200 | 0x01000000,
        )
        process_handle = ctypes.c_void_p(int(process._handle))  # type: ignore[attr-defined]
        if not assign_job(job, process_handle):
            process.kill()
            raise R6LauncherError("cannot assign suspended R6 worker to Job")
        if resume_process(process_handle) != 0:
            terminate_job(job, 2)
            raise R6LauncherError("cannot resume contained R6 worker")
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            terminate_job(job, 2)
            process.communicate()
            raise R6LauncherError("contained R6 worker timed out") from exc
        terminate_job(job, 0)
        accounting = _JobBasicAccounting()
        extended = _JobExtendedLimit()
        if not query_job(job, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None):
            raise R6LauncherError("cannot query R6 Job accounting after termination")
        if not query_job(job, 9, ctypes.byref(extended), ctypes.sizeof(extended), None):
            raise R6LauncherError("cannot query R6 Job resource evidence")
        wall = time.perf_counter() - started
        observation = {
            "schema": "qwen3_tts_voice_forge_parent_job_observation_v6",
            "observed_by_parent_not_child": True,
            "windows_job_assigned_before_resume": True,
            "primary_worker_exit_code": int(process.returncode or 0),
            "job_termination_requested_after_primary_exit": True,
            "active_processes_after_termination": int(accounting.ActiveProcesses),
            "process_tree_quiescent_before_finalization": accounting.ActiveProcesses == 0,
            "quiescence_observed_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "finalization_started_utc": "PARENT_MUST_BIND_AFTER_RESOURCE_RECONCILIATION",
            "parent_wall_seconds": wall,
            "peak_process_memory_used_bytes": int(extended.PeakProcessMemoryUsed),
            "peak_job_memory_used_bytes": int(extended.PeakJobMemoryUsed),
            "io_read_operation_count": int(extended.IoInfo.ReadOperationCount),
            "io_write_operation_count": int(extended.IoInfo.WriteOperationCount),
            "io_read_bytes": int(extended.IoInfo.ReadTransferCount),
            "io_write_bytes": int(extended.IoInfo.WriteTransferCount),
            "worker_stdout_bytes": len(stdout),
            "worker_stdout_sha256": sha256_bytes(stdout),
            "worker_stderr_bytes": len(stderr),
            "worker_stderr_sha256": sha256_bytes(stderr),
        }
        return subprocess.CompletedProcess(command, int(process.returncode or 0), stdout, stderr), observation
    finally:
        if process is not None and process.poll() is None:
            terminate_job(job, 2)
            process.wait(timeout=10)
        close_handle(job)


def parse_canonical_child(r6: Any, payload: bytes) -> dict[str, Any]:
    if not payload.endswith(b"\n") or payload.endswith(b"\n\n") or b"\r" in payload or b"\n" in payload[:-1]:
        raise R6LauncherError("R6 child stdout is not one canonical object plus LF")
    value = r6.strict_json_bytes(payload[:-1], "R6 child stdout")
    r6.require_exact_keys(value, r6.R6_CHILD_KEYS, "R6 child stdout")
    if payload[:-1] != r6.canonical_bytes(value):
        raise R6LauncherError("R6 child stdout is not canonical")
    return value


def file_row(role: str, path: Path) -> dict[str, Any]:
    return {"role": role, "path": relative(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def validate_output_chain(
    *, r6: Any, finalized: Path, child: dict[str, Any], semantic: dict[str, Any], accepted: dict[str, dict[str, Any]] | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    def read(name: str, expected: str | None = None) -> dict[str, Any]:
        return r6.strict_read_json(finalized / name, expected_sha256=expected, label=f"R6 finalized {name}")

    r4_profile = read("voice_profile_candidate_v4.json")
    r5_profile = read("voice_profile_candidate_v5.json", semantic["r5_profile_sha256"])
    r5_manifest = read("worker_manifest_v5.json", semantic["r5_worker_manifest_sha256"])
    r6_profile = read("voice_profile_candidate_v6.json", child["profile_sha256"])
    r6_manifest = read("worker_manifest_v6.json", child["manifest_sha256"])
    evaluator = read("evaluator_evidence_v6.json", child["evaluator_evidence_sha256"])
    worker_resource = read("worker_resource_evidence_v6.json", child["worker_resource_evidence_sha256"])
    core = {key: semantic[key] for key in r6.CORE_BINDING_KEYS}
    r6.validate_r5_safe_extension(
        r4_profile=r4_profile, r5_profile=r5_profile, expected_core=core,
        expected_r4_profile_sha256=semantic["r4_profile_sha256"],
        expected_payload_sha256=semantic["payload_manifest_sha256"],
        expected_authorization_sha256=semantic["execution_authorization_sha256"],
        expected_parent_ledger_sha256=semantic["parent_authorization_ledger_sha256"],
    )
    r6.validate_r5_manifest(
        manifest=r5_manifest, expected_core=core, expected_run_id=semantic["run_id"],
        expected_r4_manifest_sha256=semantic["r4_worker_manifest_sha256"],
        expected_r4_profile_sha256=semantic["r4_profile_sha256"],
        expected_r5_profile_sha256=semantic["r5_profile_sha256"],
        expected_payload_sha256=semantic["payload_manifest_sha256"],
        expected_authorization_sha256=semantic["execution_authorization_sha256"],
        expected_parent_ledger_sha256=semantic["parent_authorization_ledger_sha256"],
    )
    r6.validate_r6_profile_and_manifest(
        r5_profile=r5_profile, r6_profile=r6_profile, r6_manifest=r6_manifest,
        child_result=child, semantic_binding=semantic,
        r5_profile_sha256=semantic["r5_profile_sha256"],
        r5_manifest_sha256=semantic["r5_worker_manifest_sha256"],
        r6_profile_sha256=child["profile_sha256"],
    )
    r6.validate_evaluator_evidence(evaluator, semantic_binding=semantic)
    r6.validate_worker_resource_evidence(worker_resource, semantic_binding=semantic)
    for name, expected_hash in (
        ("original_design_reference.wav", semantic["reference_wav_sha256"]),
        ("runtime_clone_test.wav", semantic["clone_test_wav_sha256"]),
        ("runtime_clone_prompt.pt", semantic["runtime_clone_prompt_sha256"]),
        ("reference_asr_transcript_v6.txt", semantic["reference_transcript_sha256"]),
        ("clone_asr_transcript_v6.txt", semantic["clone_transcript_sha256"]),
    ):
        if sha256_file(finalized / name) != expected_hash:
            raise R6LauncherError(f"R6 held artifact changed: {name}")
    if accepted is not None:
        for role in (
            "r4_profile", "r4_manifest", "r5_profile", "r5_manifest", "r6_profile",
            "r6_manifest", "evaluator_evidence", "worker_resource_evidence",
            "reference_wav", "clone_test_wav", "runtime_clone_prompt",
            "reference_transcript", "clone_transcript",
        ):
            if role not in accepted:
                raise R6LauncherError(f"R6 accepted inventory lacks {role}")
    return evaluator, worker_resource


def later_use_semantic_validator(r6: Any, project_root: Path) -> Callable[[dict[str, dict[str, Any]], dict[str, Any]], None]:
    def validate(indexed: dict[str, dict[str, Any]], semantic: dict[str, Any]) -> None:
        required = {
            "r4_profile", "r4_manifest", "r5_profile", "r5_manifest", "r6_profile",
            "r6_manifest", "verified_child_result", "evaluator_evidence",
            "worker_resource_evidence", "parent_resource_evidence", "reference_wav",
            "clone_test_wav", "runtime_clone_prompt", "reference_transcript",
            "clone_transcript", "parent_authorization_ledger", "worker_launch_claim",
            "parent_reservation",
            "live_identity_clearance", "live_watermark_scan", "bundle_envelope",
            "bundle_seal", "canonical_candidate_profile", "canonical_creation_request",
            "job", "owner_authorization", "identity_clearance_manifest",
            "watermark_preflight_manifest", "evaluation_corpus",
            "voice_design_model_manifest", "base_model_manifest",
        }
        if not required.issubset(indexed):
            raise R6LauncherError("R6 later-use accepted inventory is incomplete")
        child = r6.strict_read_json(
            project_root / indexed["verified_child_result"]["path"],
            expected_sha256=indexed["verified_child_result"]["sha256"],
            label="R6 later-use child result",
        )
        finalized = (project_root / indexed["r6_manifest"]["path"]).parent
        _evaluator, worker_resource = validate_output_chain(
            r6=r6, finalized=finalized, child=child, semantic=semantic, accepted=indexed
        )
        parent_resource = r6.strict_read_json(
            project_root / indexed["parent_resource_evidence"]["path"],
            expected_sha256=indexed["parent_resource_evidence"]["sha256"],
            label="R6 later-use parent resource evidence",
        )
        r6.validate_resource_evidence(
            parent_resource, worker_evidence=worker_resource, semantic_binding=semantic
        )
        claim = r6.strict_read_json(
            project_root / indexed["worker_launch_claim"]["path"],
            expected_sha256=semantic["worker_launch_claim_sha256"],
            label="R6 later-use worker claim",
        )
        ledger = r6.strict_read_json(
            project_root / indexed["parent_authorization_ledger"]["path"],
            expected_sha256=semantic["parent_authorization_ledger_sha256"],
            label="R6 later-use parent ledger",
        )
        reservation = r6.strict_read_json(
            project_root / indexed["parent_reservation"]["path"],
            expected_sha256=semantic["parent_reservation_sha256"],
            label="R6 later-use parent reservation",
        )
        r6.validate_parent_reservation(
            reservation,
            expected={
                "bundle_id": semantic["bundle_id"],
                "run_id": semantic["run_id"],
                "attempt": semantic["attempt"],
                "payload_manifest_sha256": semantic["payload_manifest_sha256"],
                "execution_authorization_sha256": semantic[
                    "execution_authorization_sha256"
                ],
                "authorization_nonce_sha256": semantic[
                    "execution_authorization_nonce_sha256"
                ],
                "worker_instance_nonce_sha256": ledger[
                    "worker_instance_nonce_sha256"
                ],
                "generation_seed": semantic["generation_seed"],
                "parent_authorization_ledger_path": indexed[
                    "parent_authorization_ledger"
                ]["path"],
                "verified_entry_worker_path": ledger["verified_worker_path"],
                "verified_entry_worker_sha256": ledger["verified_worker_sha256"],
            },
        )
        if (
            indexed["parent_reservation"]["sha256"]
            != semantic["parent_reservation_sha256"]
            or ledger["parent_reservation_path"]
            != indexed["parent_reservation"]["path"]
        ):
            raise R6LauncherError(
                "R6 later-use stable parent reservation binding mismatch"
            )
        ledger_expected = {
            "authorization_sha256": semantic["execution_authorization_sha256"],
            "authorization_nonce_sha256": semantic["execution_authorization_nonce_sha256"],
            "worker_instance_nonce_sha256": ledger["worker_instance_nonce_sha256"],
            "payload_manifest_sha256": semantic["payload_manifest_sha256"],
            "bundle_id": semantic["bundle_id"],
            "run_id": semantic["run_id"],
            "attempt": semantic["attempt"],
            "parent_reservation_path": ledger["parent_reservation_path"],
            "parent_reservation_sha256": semantic["parent_reservation_sha256"],
            "verified_worker_path": ledger["verified_worker_path"],
            "verified_worker_sha256": ledger["verified_worker_sha256"],
        }
        r6.validate_parent_ledger(ledger, expected=ledger_expected)
        expected_claim = {
            "authorization_sha256": semantic["execution_authorization_sha256"],
            "authorization_nonce_sha256": semantic["execution_authorization_nonce_sha256"],
            "worker_instance_nonce_sha256": ledger["worker_instance_nonce_sha256"],
            "payload_manifest_sha256": semantic["payload_manifest_sha256"],
            "bundle_id": semantic["bundle_id"], "run_id": semantic["run_id"],
            "attempt": semantic["attempt"],
            "parent_reservation_path": ledger["parent_reservation_path"],
            "parent_reservation_sha256": semantic["parent_reservation_sha256"],
            "parent_ledger_path": indexed["parent_authorization_ledger"]["path"],
            "parent_ledger_sha256": semantic["parent_authorization_ledger_sha256"],
            "worker_path": ledger["verified_worker_path"],
            "worker_sha256": ledger["verified_worker_sha256"],
        }
        r6.validate_worker_launch_claim(claim, expected=expected_claim)
        evaluator = r6.strict_read_json(
            project_root / indexed["evaluator_evidence"]["path"],
            expected_sha256=semantic["evaluator_evidence_sha256"],
            label="R6 later-use evaluator evidence",
        )
        for evidence_key, role in (
            ("named_person_clearance", "live_identity_clearance"),
            ("watermark", "live_watermark_scan"),
        ):
            section = evaluator[evidence_key]
            expected_hash = section["live_report_sha256"]
            if indexed[role]["sha256"] != expected_hash:
                raise R6LauncherError(f"R6 later-use {role} evidence mismatch")
        exact_role_hashes = {
            "canonical_candidate_profile": semantic["canonical_profile_sha256"],
            "canonical_creation_request": semantic["canonical_creation_request_sha256"],
            "job": semantic["job_sha256"],
            "owner_authorization": semantic["owner_authorization_sha256"],
            "identity_clearance_manifest": evaluator["named_person_clearance"]["static_manifest_sha256"],
            "watermark_preflight_manifest": evaluator["watermark"]["preflight_manifest_sha256"],
            "voice_design_model_manifest": semantic["voice_design_model_manifest_sha256"],
            "base_model_manifest": semantic["base_model_manifest_sha256"],
        }
        for role, expected_hash in exact_role_hashes.items():
            if indexed[role]["sha256"] != expected_hash:
                raise R6LauncherError(f"R6 later-use trusted {role} hash mismatch")
        job = r6.strict_read_json(
            project_root / indexed["job"]["path"],
            expected_sha256=semantic["job_sha256"],
            label="R6 later-use original-design job",
        )
        if (
            job.get("voice_origin") != "ORIGINAL_SYNTHETIC_TEXT_DESIGN_NOT_PERSON_CLONE"
            or job.get("identity_basis") != "original_trait_description"
            or job.get("design_traits_text_sha256") != semantic["original_trait_prompt_sha256"]
            or job.get("reference_text_sha256") != semantic["reference_text_sha256"]
            or job.get("test_text_sha256") != semantic["test_text_sha256"]
        ):
            raise R6LauncherError("R6 later-use job semantics drifted")
    return validate


def reopen_acceptance_for_later_use(
    r6: Any, *, acceptance_path: Path, expected_acceptance_sha256: str
) -> dict[str, Any]:
    return r6.reopen_acceptance_for_later_use(
        project_root=PROJECT_ROOT,
        acceptance_path=acceptance_path,
        expected_acceptance_sha256=expected_acceptance_sha256,
        required_payloads=R6_REQUIRED_PAYLOADS,
        semantic_validator=later_use_semantic_validator(r6, PROJECT_ROOT),
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not args.execute or not args.acknowledge_private_unreviewed or not args.acknowledge_no_download:
        raise R6LauncherError("R6 parent remains inert without all bounded acknowledgements")
    if not SAFE_ID.fullmatch(str(args.bundle_id or "")) or not SAFE_ID.fullmatch(str(args.run_id or "")):
        raise R6LauncherError("R6 requires safe opaque bundle/run IDs")
    _boot_manifest, boot_indexed, _boot_auth = bootstrap_external_trust(args)
    r6 = load_sealed_module(R6_GUARDS_REL, boot_indexed[R6_GUARDS_REL.as_posix()], "qwen3_tts_r6_parent_guards")
    incident = reserve_incident(r6, args.bundle_id, args.run_id)
    pending: Path | None = None
    stage = "EXTERNAL_TRUST_VERIFIED"
    try:
        _payload, indexed = r6.verify_payload_manifest(
            project_root=PROJECT_ROOT,
            expected_manifest_sha256=args.payload_manifest_sha256,
            required_payloads=R6_REQUIRED_PAYLOADS,
        )
        verified_at = datetime.now(timezone.utc)
        authorization, authorization_evidence = r6.verify_execution_authorization(
            project_root=PROJECT_ROOT,
            authorization_path=Path(args.execution_authorization),
            expected_authorization_sha256=args.execution_authorization_sha256,
            expected_manifest_sha256=args.payload_manifest_sha256,
            bundle_id=args.bundle_id,
            run_id=args.run_id,
            verified_at=verified_at,
        )
        r5 = load_sealed_module(R5_GUARDS_REL, indexed[R5_GUARDS_REL.as_posix()], "qwen3_tts_r5_guards_for_r6_parent")
        r5_runner = load_sealed_module(R5_RUNNER_REL, indexed[R5_RUNNER_REL.as_posix()], "qwen3_tts_r5_runner_for_r6")
        r4_guards = load_sealed_module(R4_GUARDS_REL, indexed[R4_GUARDS_REL.as_posix()], "qwen3_tts_r4_guards_for_r6_parent")
        r4_runner = load_sealed_module(R4_RUNNER_REL, indexed[R4_RUNNER_REL.as_posix()], "qwen3_tts_r4_runner_for_r6")
        r3_guards = load_sealed_module(R3_GUARDS_REL, indexed[R3_GUARDS_REL.as_posix()], "qwen3_tts_r3_guards_for_r6_parent")
        r3_runner = load_sealed_module(R3_RUNNER_REL, indexed[R3_RUNNER_REL.as_posix()], "qwen3_tts_r3_runner_for_r6")
        v2 = load_sealed_module(R2_RUNNER_REL, indexed[R2_RUNNER_REL.as_posix()], "qwen3_tts_r2_runner_for_r6")
        r5_runner.install_strict_json_readers(r5, r4_runner, r3_guards, r3_runner, v2)
        r5_runner.configure_parent_chain(r5=r5, r4_guards=r4_guards, r3_guards=r3_guards, r3_runner=r3_runner, v2=v2)
        contract = r6.strict_read_json(PROJECT_ROOT / R2_CONTRACT_REL, label="R6 contract")
        environment = r6.strict_read_json(PROJECT_ROOT / R2_ENVIRONMENT_REL, label="R6 environment")
        bundle, entry, bundle_dir = v2.verify_bundle_envelope(args.bundle_id)
        binding = r4_guards.execution_binding(bundle)
        job_evidence = r4_runner.validate_bound_original_job(v2, bundle, bundle_dir)
        isolated_python, parent_preflight = r3_runner.validate_ready_environment_r3(
            v2=v2, guards=r3_guards, contract=contract, environment=environment,
            worker_path=PROJECT_ROOT / R6_WORKER_REL,
        )
        parent_preflight = r5.require_strict_provenance_map(parent_preflight, "R6 parent preflight")
        parent_full_preflight = r5_runner.derive_parent_full_provenance(
            r5, v2=v2, r3_guards=r3_guards, environment=environment
        )
        pending = reserve_pending(args.run_id, args.bundle_id)
        nonce_ledger, nonce_ledger_hash = v2.consume_nonce(bundle, pending)
        (
            reservation_v6,
            reservation_path,
            reservation_hash,
            ledger_path,
            _ledger,
            ledger_hash,
        ) = write_parent_reservations(
            r6=r6, r5=r5, v2=v2, pending=pending, args=args,
            authorization=authorization, authorization_evidence=authorization_evidence,
            bundle=bundle,
            binding=binding, job_evidence=job_evidence, entry=entry,
            parent_preflight=parent_preflight, parent_full_preflight=parent_full_preflight,
            nonce_ledger=nonce_ledger, nonce_ledger_hash=nonce_ledger_hash,
        )
        command = [
            str(isolated_python), "-I", "-B", str(PROJECT_ROOT / R6_WORKER_REL),
            "--execute", "--acknowledge-private-unreviewed", "--bundle-id", args.bundle_id,
            "--run-id", args.run_id, "--pending-dir", str(pending),
            "--payload-manifest-sha256", args.payload_manifest_sha256,
            "--execution-authorization", str(Path(args.execution_authorization).resolve()),
            "--execution-authorization-sha256", args.execution_authorization_sha256,
        ]
        stage = "CONTAINED_R6_WORKER"
        completed, parent_observation = run_contained_worker_v6(
            command,
            env=r5_runner.restricted_child_environment(v2, isolated_python, args.run_id),
            timeout=1800,
        )
        r6.write_new(pending / "worker_stdout_v6.log", completed.stdout)
        r6.write_new(pending / "worker_stderr_v6.log", completed.stderr)
        if completed.returncode != 0:
            raise R6LauncherError(f"R6 worker failed with {completed.returncode}")
        child = parse_canonical_child(r6, completed.stdout)
        semantic = r6.strict_read_json(
            pending / "worker_manifest_v6.json",
            expected_sha256=child["manifest_sha256"],
            label="R6 pre-final manifest",
        )["semantic_binding_v6"]
        claim_path = PROJECT_ROOT / child["worker_launch_claim_path"]
        claim = r6.strict_read_json(
            claim_path, expected_sha256=child["worker_launch_claim_sha256"], label="R6 parent worker claim"
        )
        expected_claim = {
            "authorization_sha256": args.execution_authorization_sha256,
            "authorization_nonce_sha256": authorization["authorization_nonce_sha256"],
            "worker_instance_nonce_sha256": authorization["worker_instance_nonce_sha256"],
            "payload_manifest_sha256": args.payload_manifest_sha256,
            "bundle_id": args.bundle_id, "run_id": args.run_id, "attempt": relative(pending),
            "parent_reservation_path": relative(reservation_path),
            "parent_reservation_sha256": reservation_hash,
            "parent_ledger_path": relative(ledger_path), "parent_ledger_sha256": ledger_hash,
            "worker_path": R6_WORKER_REL.as_posix(),
            "worker_sha256": sha256_file(PROJECT_ROOT / R6_WORKER_REL),
        }
        r6.validate_worker_launch_claim(claim, expected=expected_claim)
        validate_output_chain(r6=r6, finalized=pending, child=child, semantic=semantic)
        parent_observation["finalization_started_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        worker_resource = r6.strict_read_json(
            pending / "worker_resource_evidence_v6.json",
            expected_sha256=child["worker_resource_evidence_sha256"],
            label="R6 worker resource evidence",
        )
        parent_resource = {
            "schema": "qwen3_tts_voice_forge_resource_reconciliation_v6",
            "status": "PARENT_RECONCILED_AFTER_PROCESS_TREE_QUIESCENCE",
            "semantic_binding_sha256": r6.evidence_subject_sha256(semantic),
            "worker_resource_evidence_sha256": child["worker_resource_evidence_sha256"],
            "parent_job_observation": parent_observation,
            "parent_job_observation_sha256": r6.canonical_sha256(parent_observation),
            "worker_only_telemetry_accepted_as_parent_truth": False,
            "reconciliation_passed": True,
        }
        r6.validate_resource_evidence(parent_resource, worker_evidence=worker_resource, semantic_binding=semantic)
        r6.write_new_json(pending / "parent_resource_evidence_v6.json", parent_resource)
        r6.write_new_json(pending / "verified_child_result_v6.json", child)
        finalized = r5.finalize_pending_tree(pending, pending.parent / f"finalized_{pending.name}")
        pending = None
        validate_output_chain(r6=r6, finalized=finalized, child=child, semantic=semantic)
        role_names = {
            "r4_profile": "voice_profile_candidate_v4.json", "r4_manifest": "worker_manifest_v4.json",
            "r5_profile": "voice_profile_candidate_v5.json", "r5_manifest": "worker_manifest_v5.json",
            "r6_profile": "voice_profile_candidate_v6.json", "r6_manifest": "worker_manifest_v6.json",
            "verified_child_result": "verified_child_result_v6.json",
            "evaluator_evidence": "evaluator_evidence_v6.json",
            "worker_resource_evidence": "worker_resource_evidence_v6.json",
            "parent_resource_evidence": "parent_resource_evidence_v6.json",
            "reference_wav": "original_design_reference.wav", "clone_test_wav": "runtime_clone_test.wav",
            "runtime_clone_prompt": "runtime_clone_prompt.pt",
            "reference_transcript": "reference_asr_transcript_v6.txt",
            "clone_transcript": "clone_asr_transcript_v6.txt",
            "live_identity_clearance": "live_identity_clearance_v2.json",
            "live_watermark_scan": "live_watermark_documentation_scan_v2.json",
        }
        accepted_files = [file_row(role, finalized / name) for role, name in role_names.items()]
        bundle_bound_paths = {
            "bundle_envelope": bundle_dir / "acceptance_bundle.json",
            "bundle_seal": bundle_dir / "BUNDLE_SEAL.json",
            "canonical_candidate_profile": PROJECT_ROOT / bundle["canonical_profile_path"],
            "canonical_creation_request": PROJECT_ROOT / bundle["canonical_creation_request_path"],
            "job": bundle_dir / bundle["job_path"],
            "owner_authorization": bundle_dir / bundle["owner_authorization_path"],
            "identity_clearance_manifest": bundle_dir / bundle["identity_clearance_manifest_path"],
            "watermark_preflight_manifest": bundle_dir / bundle["watermark_evidence_manifest_path"],
            "evaluation_corpus": PROJECT_ROOT / bundle["evaluation_corpus_path"],
            "voice_design_model_manifest": PROJECT_ROOT / bundle["voice_design_model_manifest_path"],
            "base_model_manifest": PROJECT_ROOT / bundle["base_model_manifest_path"],
        }
        accepted_files.extend(
            file_row(role, path) for role, path in bundle_bound_paths.items()
        )
        accepted_files.extend(
            [
                file_row("parent_reservation", reservation_path),
                file_row("parent_authorization_ledger", ledger_path),
                file_row("worker_launch_claim", claim_path),
            ]
        )
        accepted_indexed = r6.verify_accepted_files(project_root=PROJECT_ROOT, rows=accepted_files)
        later_validator = later_use_semantic_validator(r6, PROJECT_ROOT)
        later_validator(accepted_indexed, semantic)
        acceptance = {
            "schema": "qwen3_tts_original_voice_forge_parent_acceptance_v6",
            "status": "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_FRESH_EXECUTION_AUDIT_REQUIRED",
            "accepted_utc": r6.utc_now(),
            "authorization_verified_at_start_utc": verified_at.isoformat().replace("+00:00", "Z"),
            "semantic_binding_v6": semantic,
            "semantic_binding_v6_sha256": r6.canonical_sha256(semantic),
            "payload_manifest_path": R6_PAYLOAD_REL.as_posix(),
            "payload_manifest_sha256": args.payload_manifest_sha256,
            "execution_authorization_path": relative(Path(args.execution_authorization)),
            "execution_authorization_sha256": args.execution_authorization_sha256,
            "independent_r6_audit_path": authorization["independent_audit_path"],
            "independent_r6_audit_sha256": authorization["independent_audit_sha256"],
            "rejected_r5_audit_path": R5_AUDIT_REL.as_posix(),
            "rejected_r5_audit_sha256": R5_AUDIT_SHA256,
            "parent_authorization_ledger_path": relative(ledger_path),
            "parent_authorization_ledger_sha256": ledger_hash,
            "worker_launch_claim_path": relative(claim_path),
            "worker_launch_claim_sha256": child["worker_launch_claim_sha256"],
            "accepted_files": accepted_files,
            "accepted_files_sha256": r6.canonical_sha256(accepted_files),
            "owner_hearing_acceptance": "PENDING",
            "assignment_allowed": False,
            "activation_allowed": False,
            "publication_or_upload_allowed": False,
            "complete_later_use_revalidation_required": True,
        }
        acceptance_path = finalized.parent / f"{finalized.name}_parent_acceptance_v6.json"
        r6.write_new_json(acceptance_path, acceptance)
        acceptance_hash = sha256_file(acceptance_path)
        reopen_acceptance_for_later_use(
            r6, acceptance_path=acceptance_path, expected_acceptance_sha256=acceptance_hash
        )
        return {**acceptance, "parent_acceptance_path": relative(acceptance_path), "parent_acceptance_sha256": acceptance_hash}
    except BaseException as exc:
        try:
            r6.write_new_json(
                incident / "failure_v6.json",
                {
                    "schema": "qwen3_tts_voice_forge_failure_v6", "status": "FAILED_CLOSED",
                    "stage": stage, "error_type": type(exc).__name__, "error": str(exc),
                    "traceback": traceback.format_exc(), "attempt": relative(pending) if pending else None,
                },
            )
        except BaseException:
            pass
        raise


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--acknowledge-private-unreviewed", action="store_true")
    parser.add_argument("--acknowledge-no-download", action="store_true")
    parser.add_argument("--bundle-id")
    parser.add_argument("--run-id")
    parser.add_argument("--payload-manifest-sha256")
    parser.add_argument("--execution-authorization")
    parser.add_argument("--execution-authorization-sha256")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    result = run(parse_args(argv))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as exc:
        print(f"R6 Qwen3-TTS parent failed closed: {exc}", file=sys.stderr)
        raise SystemExit(2)
