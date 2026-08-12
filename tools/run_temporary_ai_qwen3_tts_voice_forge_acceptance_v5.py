"""Parent-owned append-only R5 acceptance launcher (inert pending audit).

R5 cannot be enabled by editing its payload manifest.  A later bounded run
would require the independently published immutable-manifest SHA-256 and the
SHA-256 of a separate append-only, one-use, bundle/run-scoped authorization.
The shipped authorization example is disabled and ``execution_allowed`` stays
false.  This module does not run during static verification.
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
import secrets
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_MANIFEST_REL = Path(
    "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v5.json"
)
R5_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r5_guards.py")
R5_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v5.py")
R5_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v5.py")
R4_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r4_guards.py")
R4_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v4.py")
R4_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v4.py")
R4_MANIFEST_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v4.json")
R4_AUDIT_REL = Path(
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R4_INDEPENDENT_AUDIT_20260809.md"
)
R3_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r3_guards.py")
R3_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v3.py")
R3_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v3.py")
R3_MANIFEST_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v3.json")
R2_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v2.py")
R2_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py")
R2_CONTRACT_REL = Path(
    "TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json"
)
R2_ENVIRONMENT_REL = Path("Voice/sidecars/qwen3_tts_voice_forge_v2/environment_spec_v2.json")
R2_REGISTRY_REL = Path(
    "Data/voice/policies/temporaryai_qwen3_tts_voice_forge_bundle_registry_v2.json"
)
R2_CORPUS_REL = Path("Data/voice/policies/qwen3_tts_voice_forge_evaluation_corpus_v2.json")
OUTPUT_ROOT_REL = Path("Voice/voice_forge/private_review_v5")
AUTH_LEDGER_ROOT_REL = Path(
    "Data/voice/runtime/qwen3_tts_voice_forge_authorization_ledger_v5"
)
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")


R5_REQUIRED_PAYLOADS = {
    path.as_posix()
    for path in (
        R5_GUARDS_REL,
        R5_WORKER_REL,
        R5_RUNNER_REL,
        R4_GUARDS_REL,
        R4_WORKER_REL,
        R4_RUNNER_REL,
        R4_MANIFEST_REL,
        R4_AUDIT_REL,
        R3_GUARDS_REL,
        R3_WORKER_REL,
        R3_RUNNER_REL,
        R3_MANIFEST_REL,
        R2_WORKER_REL,
        R2_RUNNER_REL,
        R2_CONTRACT_REL,
        R2_ENVIRONMENT_REL,
        R2_REGISTRY_REL,
        R2_CORPUS_REL,
    )
}
CHILD_KEYS = {
    "schema",
    "status",
    "bundle_id",
    "run_id",
    "payload_manifest_sha256",
    "execution_authorization_sha256",
    "authorization_ledger_sha256",
    "manifest_path",
    "manifest_sha256",
    "profile_path",
    "profile_sha256",
    "artifact_seals_sha256",
    "exact_provenance_sha256",
}


class R5LauncherError(RuntimeError):
    """The append-only R5 parent launcher failed closed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _bootstrap_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise R5LauncherError(f"duplicate bootstrap JSON key: {key}")
        value[key] = child
    return value


def _bootstrap_object(path: Path, expected_sha256: str, label: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{64}", str(expected_sha256 or "")):
        raise R5LauncherError(f"{label} expected hash is invalid")
    if not path.is_file() or path.is_symlink():
        raise R5LauncherError(f"{label} is missing, non-regular, or a symlink")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise R5LauncherError(f"{label} differs from its external hash")
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_bootstrap_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise R5LauncherError(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise R5LauncherError(f"{label} is not an object")
    return value


def bootstrap_verify_external_trust(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    """Verify external trust bytes before importing any R5 dependency."""

    manifest_path = (PROJECT_ROOT / PAYLOAD_MANIFEST_REL).resolve()
    manifest = _bootstrap_object(
        manifest_path, args.payload_manifest_sha256, "R5 bootstrap payload manifest"
    )
    if (
        manifest.get("schema") != "qwen3_tts_voice_forge_payload_manifest_v5"
        or manifest.get("status") != "IMMUTABLE_PAYLOAD_REQUIRES_EXTERNAL_AUTHORIZATION"
        or manifest.get("execution_allowed") is not False
        or manifest.get("self_authorization_allowed") is not False
    ):
        raise R5LauncherError("R5 bootstrap payload attempted to authorize itself")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise R5LauncherError("R5 bootstrap payload inventory is not a list")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
            raise R5LauncherError("R5 bootstrap payload row is not exact")
        rel = str(row.get("path") or "")
        if rel in indexed or rel not in R5_REQUIRED_PAYLOADS:
            raise R5LauncherError("R5 bootstrap payload row is duplicate or unexpected")
        path = (PROJECT_ROOT / rel).resolve()
        try:
            path.relative_to(PROJECT_ROOT.resolve())
        except ValueError as exc:
            raise R5LauncherError("R5 bootstrap payload escaped the project") from exc
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != row.get("bytes")
            or sha256_file(path) != row.get("sha256")
        ):
            raise R5LauncherError(f"R5 bootstrap payload drift: {rel}")
        indexed[rel] = row
    if set(indexed) != R5_REQUIRED_PAYLOADS:
        raise R5LauncherError("R5 bootstrap payload inventory is incomplete")

    authorization_path = Path(args.execution_authorization).resolve()
    try:
        auth_rel = authorization_path.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise R5LauncherError("R5 bootstrap authorization escaped the project") from exc
    if not auth_rel.startswith("Data/voice/authorizations/qwen3_tts_voice_forge_v5/"):
        raise R5LauncherError("R5 bootstrap authorization root mismatch")
    authorization = _bootstrap_object(
        authorization_path,
        args.execution_authorization_sha256,
        "R5 bootstrap execution authorization",
    )
    exact_keys = {
        "schema", "status", "execution_allowed", "one_use",
        "payload_manifest_path", "payload_manifest_sha256",
        "independent_audit_path", "independent_audit_sha256",
        "rejected_r4_audit_path", "rejected_r4_audit_sha256",
        "bundle_id", "run_id", "authorization_nonce_sha256",
        "issued_utc", "expires_utc",
    }
    if set(authorization) != exact_keys:
        raise R5LauncherError("R5 bootstrap authorization fields are not exact")
    if (
        authorization.get("schema") != "qwen3_tts_voice_forge_execution_authorization_v5"
        or authorization.get("status") != "INDEPENDENT_AUDIT_ACCEPTED_ONE_BOUNDED_RUN"
        or authorization.get("execution_allowed") is not True
        or authorization.get("one_use") is not True
        or authorization.get("payload_manifest_path") != PAYLOAD_MANIFEST_REL.as_posix()
        or authorization.get("payload_manifest_sha256") != args.payload_manifest_sha256
        or authorization.get("bundle_id") != args.bundle_id
        or authorization.get("run_id") != args.run_id
        or authorization.get("rejected_r4_audit_path") != R4_AUDIT_REL.as_posix()
        or authorization.get("rejected_r4_audit_sha256")
        != "04073b96cd4d514aaa5e60b75783d0e2a1c024782fce591fc83fcfe3e2befe9b"
        or sha256_file(PROJECT_ROOT / R4_AUDIT_REL)
        != authorization.get("rejected_r4_audit_sha256")
    ):
        raise R5LauncherError("R5 bootstrap authorization binding mismatch")
    if not re.fullmatch(
        r"[0-9a-f]{64}", str(authorization.get("authorization_nonce_sha256") or "")
    ):
        raise R5LauncherError("R5 bootstrap authorization nonce is invalid")
    audit_rel = str(authorization.get("independent_audit_path") or "")
    audit_path = (PROJECT_ROOT / audit_rel).resolve()
    try:
        resolved_audit_rel = audit_path.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise R5LauncherError("R5 bootstrap independent audit escaped project") from exc
    if (
        not audit_rel.startswith("System/Docs/")
        or resolved_audit_rel != audit_rel
        or "TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R5_INDEPENDENT_AUDIT_" not in audit_rel
        or not re.fullmatch(r"[0-9a-f]{64}", str(authorization.get("independent_audit_sha256") or ""))
        or not audit_path.is_file()
        or audit_path.is_symlink()
        or sha256_file(audit_path) != authorization.get("independent_audit_sha256")
    ):
        raise R5LauncherError("R5 bootstrap independent audit binding mismatch")
    try:
        issued = datetime.fromisoformat(str(authorization["issued_utc"]).replace("Z", "+00:00"))
        expires = datetime.fromisoformat(str(authorization["expires_utc"]).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise R5LauncherError("R5 bootstrap authorization timestamps are invalid") from exc
    now = datetime.now(timezone.utc)
    if issued.tzinfo is None or expires.tzinfo is None or issued > now or now > expires:
        raise R5LauncherError("R5 bootstrap authorization is future-dated or expired")
    return manifest, indexed, authorization


def bootstrap_reserve_incident(bundle_id: str, run_id: str) -> Path:
    root = (PROJECT_ROOT / OUTPUT_ROOT_REL / "failure_journal" / bundle_id / run_id).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for _ in range(128):
        incident = root / f"incident_{secrets.token_hex(16)}"
        try:
            incident.mkdir(exist_ok=False)
        except FileExistsError:
            continue
        payload = json.dumps(
            {
                "schema": "qwen3_tts_voice_forge_failure_slot_v5",
                "status": "RESERVED_BEFORE_EXTERNAL_TRUST_VERIFICATION",
                "bundle_id": bundle_id,
                "run_id": run_id,
                "incident_id": incident.name,
            },
            sort_keys=True,
        ).encode("utf-8") + b"\n"
        with (incident / "failure_slot_reserved.json").open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return incident
    raise R5LauncherError("cannot reserve bootstrap R5 failure evidence")


def bootstrap_preserve_failure(incident: Path, exc: BaseException, stage: str) -> Path:
    payload = json.dumps(
        {
            "schema": "qwen3_tts_voice_forge_bootstrap_failure_v5",
            "status": "FAILED_BEFORE_EXECUTABLE_DEPENDENCY_IMPORT",
            "stage": stage,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        },
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    errors: list[str] = []
    for index in range(1, 1000):
        path = incident / f"bootstrap_failure_{index:03d}.json"
        try:
            with path.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException as write_exc:
            errors.append(str(write_exc))
            continue
        return path
    raise R5LauncherError("bootstrap failure evidence could not be preserved: " + " | ".join(errors[-3:]))


def relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def load_sealed_module(rel: Path, row: dict[str, Any], name: str) -> Any:
    path = (PROJECT_ROOT / rel).resolve()
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != row.get("bytes")
        or sha256_file(path) != row.get("sha256")
    ):
        raise R5LauncherError(f"sealed R5 parent dependency drift: {rel.as_posix()}")
    source = path.read_bytes()
    if len(source) != row.get("bytes") or hashlib.sha256(source).hexdigest() != row.get("sha256"):
        raise R5LauncherError(f"sealed R5 source read drift: {rel.as_posix()}")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    sys.modules[name] = module
    code = compile(source, str(path), "exec", dont_inherit=True, optimize=0)
    exec(code, module.__dict__)
    if Path(module.__file__).resolve() != path or sha256_file(path) != row.get("sha256"):
        raise R5LauncherError(f"sealed R5 dependency changed after import: {rel.as_posix()}")
    return module


def install_strict_json_readers(r5: Any, *modules: Any) -> None:
    def strict_reader(path: Path) -> dict[str, Any]:
        return r5.strict_read_json(Path(path), label=f"acceptance-critical {path}")

    for module in modules:
        if hasattr(module, "read_json"):
            module.read_json = strict_reader


def configure_parent_chain(
    *, r5: Any, r4_guards: Any, r3_guards: Any, r3_runner: Any, v2: Any
) -> None:
    r4_guards.install_r4_wheel_override(r3_guards)
    r3_runner.R3_MANIFEST_REL = PAYLOAD_MANIFEST_REL
    r3_runner.R3_WORKER_REL = R5_WORKER_REL
    r3_runner.R3_RUNNER_REL = R5_RUNNER_REL
    r3_runner.OUTPUT_ROOT_REL = OUTPUT_ROOT_REL
    r3_runner.install_runner_guards(v2, r3_guards)
    install_strict_json_readers(r5, r3_guards, r3_runner, v2)


def derive_parent_full_provenance(
    r5: Any, *, v2: Any, r3_guards: Any, environment: dict[str, Any]
) -> dict[str, Any]:
    """Recompute complete RECORD and wheel-member maps from parent reads."""

    result: dict[str, Any] = {}
    distributions = environment.get("distributions") or {}
    for package in ("torch", "torchaudio"):
        row = distributions.get(package)
        if not isinstance(row, dict):
            raise R5LauncherError(f"R5 {package} distribution specification is absent")
        installed_raw = v2.verify_record_file(package, row)
        wheel = r3_guards.attest_wheel_archive(
            project_root=PROJECT_ROOT,
            wheel_root_rel=v2.WHEEL_EVIDENCE_ROOT_REL,
            package=package,
            row=row,
        )
        binding = r3_guards.bind_wheel_to_installed_distribution(
            project_root=PROJECT_ROOT,
            isolated_venv_rel=v2.ISOLATED_VENV_REL,
            package=package,
            row=row,
            installed_evidence=installed_raw,
            wheel_evidence=wheel,
        )
        installed_files = installed_raw.get("installed_files")
        if installed_files is None:
            installed_files = installed_raw.get("files")
        if not isinstance(installed_files, list) or not installed_files:
            raise R5LauncherError(f"R5 {package} parent RECORD file map is absent")
        installed = {
            "version": installed_raw.get("version"),
            "record_path": installed_raw.get("record_path"),
            "record_sha256": installed_raw.get("record_sha256"),
            "record_rows_verified": len(installed_files),
            "installed_files": installed_files,
        }
        result[package] = {
            "environment_distribution_spec_sha256": r5.canonical_sha256(row),
            "installed_record_evidence": installed,
            "wheel_archive_evidence": wheel,
            "strict_binding": binding,
        }
    return r5.require_full_provenance_capsule(result, "parent-derived full provenance")


def reserve_pending(run_id: str, bundle_id: str) -> Path:
    root = (PROJECT_ROOT / OUTPUT_ROOT_REL / run_id / bundle_id).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for index in range(1, 1000):
        pending = root / f"attempt_{index:03d}"
        try:
            pending.mkdir(exist_ok=False)
        except FileExistsError:
            continue
        return pending
    raise R5LauncherError("no append-only R5 pending attempt slot remains")


def consume_execution_authorization(
    r5: Any,
    *,
    authorization: dict[str, Any],
    authorization_sha256: str,
    payload_manifest_sha256: str,
    bundle_id: str,
    run_id: str,
    pending: Path,
) -> tuple[Path, str]:
    ledger = (PROJECT_ROOT / AUTH_LEDGER_ROOT_REL / f"{authorization_sha256}.json").resolve()
    evidence = {
        "schema": "qwen3_tts_voice_forge_authorization_ledger_v5",
        "status": "CONSUMED_FOR_ONE_EXACT_PENDING_ATTEMPT",
        "utc": r5.utc_now(),
        "authorization_sha256": authorization_sha256,
        "authorization_nonce_sha256": authorization["authorization_nonce_sha256"],
        "payload_manifest_sha256": payload_manifest_sha256,
        "bundle_id": bundle_id,
        "run_id": run_id,
        "attempt": relative(pending),
    }
    r5.write_new_json(ledger, evidence)
    reopened = r5.strict_read_json(ledger, label="R5 authorization consumption ledger")
    if reopened != evidence:
        raise R5LauncherError("R5 authorization ledger changed after creation")
    return ledger, sha256_file(ledger)


def restricted_child_environment(v2: Any, isolated_python: Path, run_id: str) -> dict[str, str]:
    env = v2.restricted_child_environment(isolated_python=isolated_python)
    cache = PROJECT_ROOT / "RecoverySprint/runtime_cache/qwen3_tts_voice_forge_v5" / run_id
    temp = cache / "temp"
    hf = cache / "huggingface"
    torch_cache = cache / "torch"
    for path in (temp, hf, torch_cache):
        path.mkdir(parents=True, exist_ok=True)
    env.update(
        {
            "TEMP": str(temp),
            "TMP": str(temp),
            "HF_HOME": str(hf),
            "TORCH_HOME": str(torch_cache),
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
        }
    )
    return env


class _JobBasicLimit(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class _JobExtendedLimit(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JobBasicLimit),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def run_contained_worker(
    command: list[str], *, env: dict[str, str], timeout: float
) -> subprocess.CompletedProcess[bytes]:
    """Start suspended, assign a kill-on-close Job, resume, and drain output."""

    if os.name != "nt":
        raise R5LauncherError("R5 real worker containment is Windows-only")
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
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    close_handle.restype = ctypes.c_int
    resume_process = ntdll.NtResumeProcess
    resume_process.argtypes = [ctypes.c_void_p]
    resume_process.restype = ctypes.c_long

    job = create_job(None, None)
    if not job:
        raise R5LauncherError(f"cannot create R5 Job Object: {ctypes.get_last_error()}")
    info = _JobExtendedLimit()
    info.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
    if not set_job(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
        close_handle(job)
        raise R5LauncherError(f"cannot configure R5 Job Object: {ctypes.get_last_error()}")
    creation = 0x00000004 | 0x00000200 | 0x01000000  # suspended, process-group, breakaway
    process: subprocess.Popen[bytes] | None = None
    started = time.perf_counter()
    try:
        process = subprocess.Popen(
            command,
            cwd=str(PROJECT_ROOT),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creation,
        )
        process_handle = ctypes.c_void_p(int(process._handle))  # type: ignore[attr-defined]
        if not assign_job(job, process_handle):
            process.kill()
            raise R5LauncherError(
                f"cannot assign suspended R5 worker to Job: {ctypes.get_last_error()}"
            )
        if resume_process(process_handle) != 0:
            terminate_job(job, 2)
            raise R5LauncherError("cannot resume contained R5 worker")
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            terminate_job(job, 2)
            stdout, stderr = process.communicate()
            raise R5LauncherError("contained R5 worker timed out") from exc
        # The primary process is finished; terminating the exact Job now kills
        # any descendant that tried to survive the stdout handoff.
        terminate_job(job, 0)
        return subprocess.CompletedProcess(
            command,
            int(process.returncode or 0),
            stdout,
            stderr,
        )
    finally:
        if process is not None and process.poll() is None:
            terminate_job(job, 2)
            process.wait(timeout=10)
        close_handle(job)
        _ = time.perf_counter() - started


def _r4_child_from_final(
    r4_guards: Any,
    *,
    binding: dict[str, str],
    manifest: dict[str, Any],
    manifest_sha256: str,
    profile_sha256: str,
) -> dict[str, Any]:
    return {
        "schema": "qwen3_tts_original_voice_forge_child_result_v4",
        "status": manifest["status"],
        **binding,
        "manifest_path": "worker_manifest_v4.json",
        "manifest_sha256": manifest_sha256,
        "profile_path": "voice_profile_candidate_v4.json",
        "profile_sha256": profile_sha256,
        "artifact_seals_sha256": r4_guards.canonical_sha256(
            manifest["artifact_seals"]
        ),
    }


def reopen_acceptance_for_later_use(
    r5: Any,
    *,
    finalized: Path,
    acceptance_path: Path,
    expected_acceptance_sha256: str,
) -> dict[str, Any]:
    """Mandatory gate for any later hearing, assignment, or use consumer."""

    acceptance = r5.strict_read_json(
        acceptance_path,
        expected_sha256=expected_acceptance_sha256,
        label="R5 later-use parent acceptance",
    )
    if (
        acceptance.get("schema") != "qwen3_tts_original_voice_forge_parent_acceptance_v5"
        or acceptance.get("owner_hearing_acceptance") != "PENDING"
        or acceptance.get("activation_assignment_publication_or_upload_allowed") is not False
    ):
        raise R5LauncherError("R5 later-use acceptance status is unsafe")
    r5.strict_read_json(
        PROJECT_ROOT / PAYLOAD_MANIFEST_REL,
        expected_sha256=acceptance.get("payload_manifest_sha256"),
        label="R5 later-use immutable payload manifest",
    )
    authorization_evidence = acceptance.get("execution_authorization")
    if not isinstance(authorization_evidence, dict):
        raise R5LauncherError("R5 later-use authorization evidence is absent")
    authorization = r5.strict_read_json(
        PROJECT_ROOT / str(authorization_evidence.get("path") or ""),
        expected_sha256=str(authorization_evidence.get("sha256") or ""),
        label="R5 later-use immutable execution authorization",
    )
    audit_path = PROJECT_ROOT / str(authorization.get("independent_audit_path") or "")
    if (
        not audit_path.is_file()
        or audit_path.is_symlink()
        or sha256_file(audit_path) != authorization.get("independent_audit_sha256")
    ):
        raise R5LauncherError("R5 later-use independent audit binding changed")
    snapshot = r5.artifact_snapshot(
        finalized, list(acceptance["held_finalized_relative_paths"])
    )
    if snapshot != acceptance.get("final_artifact_snapshot"):
        raise R5LauncherError("R5 later-use artifact seals changed")
    return acceptance


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not args.execute:
        raise R5LauncherError("R5 launcher is inert without --execute")
    if not args.acknowledge_private_unreviewed or not args.acknowledge_no_download:
        raise R5LauncherError("both R5 bounded execution acknowledgements are required")
    if not SAFE_ID.fullmatch(str(args.bundle_id or "")) or not SAFE_ID.fullmatch(
        str(args.run_id or "")
    ):
        raise R5LauncherError("safe opaque bundle and run IDs are required")

    # Reserve an append-only failure slot first, then verify both externally
    # pinned trust objects using only code in this already-invoked entry file.
    # No R5/R4/R3/R2 dependency is imported before both checks pass.
    incident = bootstrap_reserve_incident(args.bundle_id, args.run_id)
    try:
        _bootstrap_payload, bootstrap_indexed, _bootstrap_authorization = (
            bootstrap_verify_external_trust(args)
        )
        r5 = load_sealed_module(
            R5_GUARDS_REL,
            bootstrap_indexed[R5_GUARDS_REL.as_posix()],
            "qwen3_tts_r5_parent_guards_after_external_trust",
        )
    except BaseException as bootstrap_exc:
        bootstrap_preserve_failure(
            incident, bootstrap_exc, "EXTERNAL_TRUST_BEFORE_DEPENDENCY_IMPORT"
        )
        raise

    pending: Path | None = None
    stage = "INCIDENT_RESERVED_BEFORE_ATTEMPT"
    worker_started = False
    try:
        pending = reserve_pending(args.run_id, args.bundle_id)
        stage = "EXTERNAL_IMMUTABLE_PAYLOAD"
        _payload, indexed = r5.verify_payload_manifest(
            project_root=PROJECT_ROOT,
            expected_manifest_sha256=args.payload_manifest_sha256,
            required_payloads=R5_REQUIRED_PAYLOADS,
        )
        if sha256_file(PROJECT_ROOT / R5_GUARDS_REL) != indexed[R5_GUARDS_REL.as_posix()]["sha256"]:
            raise R5LauncherError("bootstrapped R5 guards differ from immutable payload")
        authorization, authorization_evidence = r5.verify_execution_authorization(
            project_root=PROJECT_ROOT,
            authorization_path=Path(args.execution_authorization),
            expected_authorization_sha256=args.execution_authorization_sha256,
            expected_manifest_sha256=args.payload_manifest_sha256,
            bundle_id=args.bundle_id,
            run_id=args.run_id,
        )
        r4_guards = load_sealed_module(
            R4_GUARDS_REL, indexed[R4_GUARDS_REL.as_posix()], "qwen3_tts_r4_guards_for_r5_parent"
        )
        r4_runner = load_sealed_module(
            R4_RUNNER_REL, indexed[R4_RUNNER_REL.as_posix()], "qwen3_tts_r4_runner_for_r5"
        )
        r3_guards = load_sealed_module(
            R3_GUARDS_REL, indexed[R3_GUARDS_REL.as_posix()], "qwen3_tts_r3_guards_for_r5_parent"
        )
        r3_runner = load_sealed_module(
            R3_RUNNER_REL, indexed[R3_RUNNER_REL.as_posix()], "qwen3_tts_r3_runner_for_r5"
        )
        v2 = load_sealed_module(
            R2_RUNNER_REL, indexed[R2_RUNNER_REL.as_posix()], "qwen3_tts_r2_runner_for_r5"
        )
        install_strict_json_readers(r5, r4_runner, r3_guards, r3_runner, v2)
        configure_parent_chain(
            r5=r5,
            r4_guards=r4_guards,
            r3_guards=r3_guards,
            r3_runner=r3_runner,
            v2=v2,
        )
        contract = r5.strict_read_json(PROJECT_ROOT / R2_CONTRACT_REL, label="R5 contract")
        environment = r5.strict_read_json(
            PROJECT_ROOT / R2_ENVIRONMENT_REL, label="R5 environment"
        )
        r5.strict_read_json(PROJECT_ROOT / R2_REGISTRY_REL, label="R5 registry")
        r5.strict_read_json(PROJECT_ROOT / R2_CORPUS_REL, label="R5 evaluation corpus")

        stage = "TRUSTED_BUNDLE_AND_STRICT_JSON"
        bundle, entry, bundle_dir = v2.verify_bundle_envelope(args.bundle_id)
        binding = r4_guards.execution_binding(bundle)
        job_evidence = r4_runner.validate_bound_original_job(v2, bundle, bundle_dir)
        if job_evidence["sha256"] != binding["job_sha256"]:
            raise R5LauncherError("R5 original job binding mismatch")

        stage = "PARENT_PREFLIGHT_RECOMPUTATION"
        worker_path = PROJECT_ROOT / R5_WORKER_REL
        isolated_python, parent_preflight = r3_runner.validate_ready_environment_r3(
            v2=v2,
            guards=r3_guards,
            contract=contract,
            environment=environment,
            worker_path=worker_path,
        )
        parent_preflight = r5.require_strict_provenance_map(
            parent_preflight, "R5 actual parent preflight"
        )
        parent_full_preflight = derive_parent_full_provenance(
            r5, v2=v2, r3_guards=r3_guards, environment=environment
        )
        if {
            package: parent_full_preflight[package]["strict_binding"]
            for package in ("torch", "torchaudio")
        } != parent_preflight:
            raise R5LauncherError("R5 parent summary/full provenance derivations differ")
        parent_full_preflight_hash = r5.canonical_sha256(parent_full_preflight)

        stage = "ONE_USE_AUTHORIZATION_AND_QUEUE_NONCES"
        auth_ledger, auth_ledger_hash = consume_execution_authorization(
            r5,
            authorization=authorization,
            authorization_sha256=args.execution_authorization_sha256,
            payload_manifest_sha256=args.payload_manifest_sha256,
            bundle_id=args.bundle_id,
            run_id=args.run_id,
            pending=pending,
        )
        nonce_ledger, nonce_ledger_hash = v2.consume_nonce(bundle, pending)
        frozen_reservation = {
            "schema": "qwen3_tts_voice_forge_parent_reservation_v2",
            "status": "RESERVED_AND_NONCE_CONSUMED_FOR_EXACT_QUEUE",
            "r4_schema": "qwen3_tts_voice_forge_parent_reservation_v4",
            "r5_schema": "qwen3_tts_voice_forge_parent_reservation_v5",
            "utc": r5.utc_now(),
            **binding,
            **v2.queue_binding_payload(bundle),
            "attempt": relative(pending),
            "nonce_ledger_path": relative(nonce_ledger),
            "nonce_ledger_sha256": nonce_ledger_hash,
            "verified_worker_path": R2_WORKER_REL.as_posix(),
            "verified_worker_sha256": sha256_file(PROJECT_ROOT / R2_WORKER_REL),
            "verified_entry_worker_path": R5_WORKER_REL.as_posix(),
            "verified_entry_worker_sha256": sha256_file(worker_path),
            "verified_frozen_core_worker_path": R2_WORKER_REL.as_posix(),
            "verified_frozen_core_worker_sha256": sha256_file(PROJECT_ROOT / R2_WORKER_REL),
            "verified_frozen_r3_worker_path": R3_WORKER_REL.as_posix(),
            "verified_frozen_r3_worker_sha256": sha256_file(PROJECT_ROOT / R3_WORKER_REL),
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
        r5.write_new_json(pending / "parent_reservation.json", frozen_reservation)
        reservation_v5 = {
            "schema": "qwen3_tts_voice_forge_parent_reservation_v5",
            "status": "EXTERNAL_AUTHORITY_AND_PARENT_PREFLIGHT_RESERVED",
            "bundle_id": args.bundle_id,
            "run_id": args.run_id,
            "attempt": relative(pending),
            "payload_manifest_sha256": args.payload_manifest_sha256,
            "execution_authorization": authorization_evidence,
            "execution_authorization_sha256": args.execution_authorization_sha256,
            "authorization_ledger_path": relative(auth_ledger),
            "authorization_ledger_sha256": auth_ledger_hash,
            "exact_parent_preflight_provenance": parent_preflight,
            "exact_parent_full_provenance": parent_full_preflight,
            "exact_parent_full_provenance_sha256": parent_full_preflight_hash,
            "frozen_parent_reservation_sha256": sha256_file(
                pending / "parent_reservation.json"
            ),
        }
        r5.write_new_json(pending / "parent_reservation_v5.json", reservation_v5)

        command = [
            str(isolated_python),
            "-I",
            "-B",
            str(worker_path),
            "--execute",
            "--acknowledge-private-unreviewed",
            "--bundle-id",
            args.bundle_id,
            "--run-id",
            args.run_id,
            "--pending-dir",
            str(pending),
            "--payload-manifest-sha256",
            args.payload_manifest_sha256,
            "--execution-authorization",
            str(Path(args.execution_authorization).resolve()),
            "--execution-authorization-sha256",
            args.execution_authorization_sha256,
        ]
        stage = "CONTAINED_WORKER_TREE"
        worker_started = True
        started = time.perf_counter()
        completed = run_contained_worker(
            command,
            env=restricted_child_environment(v2, isolated_python, args.run_id),
            timeout=1800,
        )
        elapsed = time.perf_counter() - started
        r5.write_new(pending / "worker_stdout_v5.log", completed.stdout)
        r5.write_new(pending / "worker_stderr_v5.log", completed.stderr)
        if completed.returncode != 0:
            raise R5LauncherError(
                f"contained R5 worker failed with return code {completed.returncode}"
            )
        child = r5.parse_canonical_child_result(
            completed.stdout,
            expected_schema="qwen3_tts_original_voice_forge_child_result_v5",
            exact_keys=CHILD_KEYS,
        )
        if (
            child.get("status")
            != "CHILD_ENGINEERING_GATES_PASSED_PARENT_FINALIZATION_PENDING"
            or child.get("bundle_id") != args.bundle_id
            or child.get("run_id") != args.run_id
            or child.get("payload_manifest_sha256") != args.payload_manifest_sha256
            or child.get("execution_authorization_sha256")
            != args.execution_authorization_sha256
            or child.get("authorization_ledger_sha256") != auth_ledger_hash
            or child.get("manifest_path") != "worker_manifest_v5.json"
            or child.get("profile_path") != "voice_profile_candidate_v5.json"
        ):
            raise R5LauncherError("R5 child identity/trust binding mismatch")
        for name in (
            "manifest_sha256",
            "profile_sha256",
            "artifact_seals_sha256",
            "exact_provenance_sha256",
        ):
            r5.require_hash(child.get(name), f"R5 child {name}")

        stage = "PARENT_OWNED_ATOMIC_FINALIZATION"
        finalized = pending.parent / f"finalized_{pending.name}"
        finalized = r5.finalize_pending_tree(pending, finalized)
        pending = None
        manifest = r5.strict_read_json(
            finalized / "worker_manifest_v5.json",
            expected_sha256=child["manifest_sha256"],
            label="R5 finalized worker manifest",
        )
        profile = r5.strict_read_json(
            finalized / "voice_profile_candidate_v5.json",
            expected_sha256=child["profile_sha256"],
            label="R5 finalized profile",
        )
        r4_manifest = r5.strict_read_json(
            finalized / "worker_manifest_v4.json", label="R5 finalized R4 manifest"
        )
        r4_profile = r5.strict_read_json(
            finalized / "voice_profile_candidate_v4.json", label="R5 finalized R4 profile"
        )
        if (
            manifest.get("artifact_seals_sha256") != child["artifact_seals_sha256"]
            or manifest.get("exact_provenance_sha256") != child["exact_provenance_sha256"]
            or profile.get("exact_provenance_sha256") != child["exact_provenance_sha256"]
        ):
            raise R5LauncherError("R5 finalized profile/manifest child bindings differ")
        r4_child = _r4_child_from_final(
            r4_guards,
            binding=binding,
            manifest=r4_manifest,
            manifest_sha256=sha256_file(finalized / "worker_manifest_v4.json"),
            profile_sha256=sha256_file(finalized / "voice_profile_candidate_v4.json"),
        )
        r4_guards.validate_bound_parent_outputs(
            attempt_dir=finalized,
            worker_manifest=r4_manifest,
            profile=r4_profile,
            manifest_file_evidence={
                "bytes": (finalized / "worker_manifest_v4.json").stat().st_size,
                "sha256": r4_child["manifest_sha256"],
            },
            profile_file_evidence={
                "bytes": (finalized / "voice_profile_candidate_v4.json").stat().st_size,
                "sha256": r4_child["profile_sha256"],
            },
            child_result=r4_child,
            expected_binding=binding,
            r3_guards=r3_guards,
        )

        stage = "FRESH_PARENT_POSTFLIGHT_RECOMPUTATION"
        _post_python, parent_postflight = r3_runner.validate_ready_environment_r3(
            v2=v2,
            guards=r3_guards,
            contract=contract,
            environment=environment,
            worker_path=worker_path,
        )
        parent_postflight = r5.require_strict_provenance_map(
            parent_postflight, "R5 fresh parent postflight summary"
        )
        parent_full_postflight = derive_parent_full_provenance(
            r5, v2=v2, r3_guards=r3_guards, environment=environment
        )
        if {
            package: parent_full_postflight[package]["strict_binding"]
            for package in ("torch", "torchaudio")
        } != parent_postflight:
            raise R5LauncherError("R5 parent postflight summary/full provenance differ")
        provenance = r5.reconcile_full_provenance_capsules(
            parent_preflight=parent_full_preflight,
            reservation=reservation_v5["exact_parent_full_provenance"],
            worker_pre_model=manifest["full_provenance_worker_pre_model"],
            worker_post_execution=manifest["full_provenance_worker_post_execution"],
            parent_postflight=parent_full_postflight,
        )
        if provenance["canonical_full_provenance_sha256"] != child["exact_provenance_sha256"]:
            raise R5LauncherError("R5 child provenance hash differs from parent derivation")

        held_paths = [
            "original_design_reference.wav",
            "runtime_clone_test.wav",
            "runtime_clone_prompt.pt",
            "worker_manifest_v4.json",
            "voice_profile_candidate_v4.json",
            "worker_manifest_v5.json",
            "voice_profile_candidate_v5.json",
        ]

        def semantic_validator() -> None:
            r5.verify_payload_manifest(
                project_root=PROJECT_ROOT,
                expected_manifest_sha256=args.payload_manifest_sha256,
                required_payloads=R5_REQUIRED_PAYLOADS,
            )
            r5.verify_execution_authorization(
                project_root=PROJECT_ROOT,
                authorization_path=Path(args.execution_authorization),
                expected_authorization_sha256=args.execution_authorization_sha256,
                expected_manifest_sha256=args.payload_manifest_sha256,
                bundle_id=args.bundle_id,
                run_id=args.run_id,
            )
            r5.strict_read_json(
                auth_ledger,
                expected_sha256=auth_ledger_hash,
                label="held R5 one-use authorization ledger",
            )
            current_manifest = r5.strict_read_json(
                finalized / "worker_manifest_v5.json",
                expected_sha256=child["manifest_sha256"],
                label="held R5 worker manifest",
            )
            current_profile = r5.strict_read_json(
                finalized / "voice_profile_candidate_v5.json",
                expected_sha256=child["profile_sha256"],
                label="held R5 profile",
            )
            if current_manifest != manifest or current_profile != profile:
                raise R5LauncherError("held R5 manifest/profile changed")
            r4_guards.verify_exact_artifact_set(
                attempt_dir=finalized,
                seals=current_manifest["artifact_seals"],
                r3_guards=r3_guards,
            )

        initial_snapshot = r5.artifact_snapshot(finalized, held_paths)
        summary = {
            "schema": "qwen3_tts_original_voice_forge_parent_acceptance_v5",
            "status": "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_EXECUTION_AUDIT",
            "bundle_id": args.bundle_id,
            "run_id": args.run_id,
            "finalized_attempt": relative(finalized),
            "payload_manifest_sha256": args.payload_manifest_sha256,
            "execution_authorization": authorization_evidence,
            "execution_authorization_sha256": args.execution_authorization_sha256,
            "authorization_ledger_sha256": auth_ledger_hash,
            "worker_process_seconds": elapsed,
            "clean_worker_exit": True,
            "contained_process_tree_terminated_before_finalization": True,
            "verified_canonical_child_stdout_sha256": r5.sha256_bytes(completed.stdout),
            "verified_child_result": child,
            "verified_original_synthetic_job": job_evidence,
            "provenance_reconciliation": provenance,
            "held_finalized_relative_paths": held_paths,
            "final_artifact_snapshot": initial_snapshot,
            "owner_hearing_acceptance": "PENDING",
            "independent_execution_audit": "REQUIRED",
            "activation_assignment_publication_or_upload_allowed": False,
            "fallback": "TEXT_PLUS_SILENCE_ONLY_NO_GENERIC_SAPI_OR_OTHER_PERSON",
            "later_use_requires_acceptance_hash_and_artifact_reopen": True,
        }
        acceptance_path = finalized.parent / f"{finalized.name}_parent_acceptance_v5.json"
        final_commit = r5.durable_acceptance_with_held_artifacts(
            finalized_root=finalized,
            relative_paths=held_paths,
            acceptance_path=acceptance_path,
            acceptance=summary,
            semantic_validator=semantic_validator,
            additional_held_paths=[
                PROJECT_ROOT / PAYLOAD_MANIFEST_REL,
                Path(args.execution_authorization),
                auth_ledger,
                PROJECT_ROOT / authorization["independent_audit_path"],
                PROJECT_ROOT / R4_AUDIT_REL,
            ],
        )
        r5.write_new_json(
            incident / "success_resolution.json",
            {
                "schema": "qwen3_tts_voice_forge_incident_resolution_v5",
                "status": "SUCCESS_ACCEPTANCE_DURABLY_PRESERVED",
                "utc": r5.utc_now(),
                "finalized_attempt": relative(finalized),
                "parent_acceptance_path": relative(acceptance_path),
                "parent_acceptance_sha256": final_commit["acceptance_sha256"],
            },
        )
        return {**summary, "durable_final_commit": final_commit}
    except BaseException as exc:
        try:
            r5.preserve_failure_or_raise(
                incident,
                exc=exc,
                stage=stage,
                attempt=relative(pending) if pending is not None else None,
                worker_started=worker_started,
                traceback_text=traceback.format_exc(),
            )
        except BaseException as evidence_exc:
            raise R5LauncherError(
                f"R5 failed and evidence preservation also failed: {evidence_exc}"
            ) from exc
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
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as exc:
        print(f"R5 Qwen3-TTS parent failed closed: {exc}", file=sys.stderr)
        raise SystemExit(2)
