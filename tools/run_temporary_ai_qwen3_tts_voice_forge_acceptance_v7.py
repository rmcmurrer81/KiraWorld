"""Inert parent for the R7 Qwen3-TTS original-voice repair candidate.

R7 is append-only and ships disabled.  A future run requires an exact sealed
payload, a separate canonical ``ACCEPT_STATIC_ONLY`` audit decision, and an
external one-use authorization.  The audit and authorization are verified
before any predecessor source is imported.  This module is not an approval to
run a model, generate audio, assign a voice, activate a person, or publish.
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
R7_PAYLOAD_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v7.json")
R7_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r7_guards.py")
R7_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v7.py")
R7_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v7.py")
R7_BOUNDARY_REL = Path(
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R7_REPAIR_BOUNDARY_20260810.md"
)
R6_PAYLOAD_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v6.json")
R6_PAYLOAD_SHA256 = "e32eb5dadfe80cc94cf1b57a98bf9220c8f7a5809d251b056d72fc02d2408a0e"
R6_AUDIT_REL = Path(
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R6_INDEPENDENT_AUDIT_20260810.md"
)
R6_AUDIT_SHA256 = "9094838509d115091da568dab55db8d6ab0a73c2642063f59f173da80cb56d10"
R6_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r6_guards.py")
R6_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v6.py")
R6_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v6.py")
R5_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r5_guards.py")
R5_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v5.py")
R4_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r4_guards.py")
R4_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v4.py")
R3_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r3_guards.py")
R3_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v3.py")
R2_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py")
R2_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v2.py")
R2_CONTRACT_REL = Path(
    "TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json"
)
R2_ENVIRONMENT_REL = Path(
    "Voice/sidecars/qwen3_tts_voice_forge_v2/environment_spec_v2.json"
)
R2_CORPUS_REL = Path("Data/voice/policies/qwen3_tts_voice_forge_evaluation_corpus_v2.json")
R4_MANIFEST_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v4.json")
R5_AUDIT_REL = Path(
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R5_INDEPENDENT_AUDIT_20260809.md"
)
R5_AUDIT_SHA256 = "82ea5a0a543fde40f7a1d05dc166798f98acbd9ae120c11ba8fb7f9ffbb5f43a"

OUTPUT_ROOT_REL = Path("Voice/voice_forge/private_review_v7")
INCIDENT_ROOT_REL = Path(
    "RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7/runtime_incidents"
)
R7_LEDGER_ROOT_REL = Path("Data/voice/runtime/qwen3_tts_voice_forge_authorization_ledger_v7")
R7_RESERVATION_ROOT_REL = Path("Data/voice/runtime/qwen3_tts_voice_forge_parent_reservations_v7")
R6_COMPAT_RESERVATION_ROOT_REL = Path(
    "Data/voice/runtime/qwen3_tts_voice_forge_parent_reservations_v6"
)
HASH = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")

R7_ADDITIONAL_PAYLOADS = {
    R6_PAYLOAD_REL.as_posix(),
    R6_AUDIT_REL.as_posix(),
    R7_GUARDS_REL.as_posix(),
    R7_WORKER_REL.as_posix(),
    R7_RUNNER_REL.as_posix(),
    R7_BOUNDARY_REL.as_posix(),
}


class R7LauncherError(RuntimeError):
    """The R7 parent failed closed."""


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
        raise R7LauncherError("R7 path escaped the project") from exc


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise R7LauncherError(f"duplicate R7 bootstrap JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise R7LauncherError(f"non-finite R7 bootstrap JSON constant: {value}")


def _object(path: Path, expected_hash: str | None, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise R7LauncherError(f"{label} is missing or unsafe")
    payload = path.read_bytes()
    if expected_hash is not None and (
        not HASH.fullmatch(str(expected_hash or "")) or sha256_bytes(payload) != expected_hash
    ):
        raise R7LauncherError(f"{label} differs from its exact hash")
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except R7LauncherError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise R7LauncherError(f"{label} is not strict finite UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise R7LauncherError(f"{label} is not an object")
    return value


def _bootstrap_payload(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], set[str]]:
    """Verify the exact R7 closure without importing any predecessor."""

    manifest = _object(
        PROJECT_ROOT / R7_PAYLOAD_REL,
        args.payload_manifest_sha256,
        "R7 parent bootstrap payload",
    )
    if (
        set(manifest)
        != {
            "schema",
            "status",
            "execution_allowed",
            "self_authorization_allowed",
            "revision",
            "predecessor_payload_manifest_path",
            "predecessor_payload_manifest_sha256",
            "rejected_r6_audit_path",
            "rejected_r6_audit_sha256",
            "files",
        }
        or manifest.get("schema") != "qwen3_tts_voice_forge_payload_manifest_v7"
        or manifest.get("status")
        != "IMMUTABLE_STATIC_PAYLOAD_REQUIRES_FRESH_INDEPENDENT_AUDIT_AND_EXTERNAL_AUTHORIZATION"
        or manifest.get("execution_allowed") is not False
        or manifest.get("self_authorization_allowed") is not False
        or manifest.get("predecessor_payload_manifest_path") != R6_PAYLOAD_REL.as_posix()
        or manifest.get("predecessor_payload_manifest_sha256") != R6_PAYLOAD_SHA256
        or manifest.get("rejected_r6_audit_path") != R6_AUDIT_REL.as_posix()
        or manifest.get("rejected_r6_audit_sha256") != R6_AUDIT_SHA256
        or sha256_file(PROJECT_ROOT / R6_PAYLOAD_REL) != R6_PAYLOAD_SHA256
        or sha256_file(PROJECT_ROOT / R6_AUDIT_REL) != R6_AUDIT_SHA256
    ):
        raise R7LauncherError("R7 payload is self-authorizing or lost its rejected R6 boundary")
    predecessor = _object(
        PROJECT_ROOT / R6_PAYLOAD_REL,
        R6_PAYLOAD_SHA256,
        "sealed R6 predecessor payload",
    )
    predecessor_rows = predecessor.get("files")
    if not isinstance(predecessor_rows, list):
        raise R7LauncherError("sealed R6 payload has no inventory")
    required = {str(row.get("path") or "") for row in predecessor_rows} | R7_ADDITIONAL_PAYLOADS
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise R7LauncherError("R7 payload inventory is not a list")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
            raise R7LauncherError("R7 payload row is not exact")
        rel = str(row.get("path") or "")
        path = (PROJECT_ROOT / rel).resolve()
        if rel in indexed or rel not in required or rel == R7_PAYLOAD_REL.as_posix() or relative(path) != rel:
            raise R7LauncherError("R7 payload row is duplicate, unexpected, or unsafe")
        if (
            not path.is_file()
            or path.is_symlink()
            or not isinstance(row.get("bytes"), int)
            or isinstance(row.get("bytes"), bool)
            or path.stat().st_size != row["bytes"]
            or not HASH.fullmatch(str(row.get("sha256") or ""))
            or sha256_file(path) != row["sha256"]
        ):
            raise R7LauncherError(f"R7 payload drift: {rel}")
        indexed[rel] = row
    if set(indexed) != required:
        raise R7LauncherError("R7 payload inventory is not the exact sealed closure")
    return manifest, indexed, required


def load_sealed_module(rel: Path, row: dict[str, Any], name: str) -> Any:
    path = (PROJECT_ROOT / rel).resolve()
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != row.get("bytes")
        or sha256_file(path) != row.get("sha256")
    ):
        raise R7LauncherError(f"R7 sealed dependency drift: {rel.as_posix()}")
    source = path.read_bytes()
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(source, str(path), "exec", dont_inherit=True, optimize=0), module.__dict__)
    if sha256_file(path) != row.get("sha256"):
        raise R7LauncherError(f"R7 dependency changed during import: {rel.as_posix()}")
    return module


def bootstrap_external_trust(
    args: argparse.Namespace,
) -> tuple[Any, dict[str, Any], dict[str, dict[str, Any]], set[str], dict[str, Any], dict[str, Any], datetime]:
    """Verify manifest + accepted audit + authority before predecessor import."""

    _bootstrap_manifest, bootstrap_indexed, required = _bootstrap_payload(args)
    r7 = load_sealed_module(
        R7_GUARDS_REL,
        bootstrap_indexed[R7_GUARDS_REL.as_posix()],
        "qwen3_tts_r7_parent_guards",
    )
    manifest, indexed = r7.verify_payload_manifest(
        project_root=PROJECT_ROOT,
        expected_manifest_sha256=args.payload_manifest_sha256,
        required_payloads=required,
    )
    verified_at = datetime.now(timezone.utc)
    authorization, authorization_evidence = r7.verify_execution_authorization(
        project_root=PROJECT_ROOT,
        authorization_path=Path(args.execution_authorization),
        expected_authorization_sha256=args.execution_authorization_sha256,
        expected_manifest_sha256=args.payload_manifest_sha256,
        expected_inventory_sha256=r7.payload_inventory_sha256(manifest),
        bundle_id=args.bundle_id,
        run_id=args.run_id,
        verified_at=verified_at,
    )
    return (
        r7,
        manifest,
        indexed,
        required,
        authorization,
        authorization_evidence,
        verified_at,
    )


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
    raise R7LauncherError("no append-only R7 attempt slot remains")


def reserve_incident(bundle_id: str, run_id: str) -> Path:
    root = PROJECT_ROOT / INCIDENT_ROOT_REL / run_id / bundle_id
    root.mkdir(parents=True, exist_ok=True)
    for index in range(1, 1000):
        path = root / f"incident_{index:03d}"
        try:
            path.mkdir(exist_ok=False)
            return path
        except FileExistsError:
            continue
    raise R7LauncherError("no append-only R7 incident slot remains")


def canonical_worker_command(isolated_python: Path, pending: Path, args: argparse.Namespace) -> list[str]:
    return [
        str(isolated_python.resolve()),
        "-I",
        "-B",
        str((PROJECT_ROOT / R7_WORKER_REL).resolve()),
        "--execute",
        "--acknowledge-private-unreviewed",
        "--bundle-id",
        args.bundle_id,
        "--run-id",
        args.run_id,
        "--pending-dir",
        str(pending.resolve()),
        "--payload-manifest-sha256",
        args.payload_manifest_sha256,
        "--execution-authorization",
        str(Path(args.execution_authorization).resolve()),
        "--execution-authorization-sha256",
        args.execution_authorization_sha256,
    ]


def _stable_path(root: Path, authorization_sha256: str) -> Path:
    if not HASH.fullmatch(str(authorization_sha256 or "")):
        raise R7LauncherError("R7 stable record requires an exact authorization hash")
    return PROJECT_ROOT / root / f"{authorization_sha256}.json"


def write_parent_reservations(
    *,
    r7: Any,
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
    worker_command_sha256: str,
    indexed: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Write R7 authority plus the exact sealed R6/R5 compatibility records."""

    frozen = {
        "schema": "qwen3_tts_voice_forge_parent_reservation_v2",
        "status": "RESERVED_AND_NONCE_CONSUMED_FOR_EXACT_QUEUE",
        "r4_schema": "qwen3_tts_voice_forge_parent_reservation_v4",
        "r5_schema": "qwen3_tts_voice_forge_parent_reservation_v5",
        "r6_schema": "qwen3_tts_voice_forge_parent_reservation_v6",
        "utc": r7.utc_now(),
        **binding,
        **v2.queue_binding_payload(bundle),
        "attempt": relative(pending),
        "nonce_ledger_path": relative(nonce_ledger),
        "nonce_ledger_sha256": nonce_ledger_hash,
        "verified_worker_path": R2_WORKER_REL.as_posix(),
        "verified_worker_sha256": sha256_file(PROJECT_ROOT / R2_WORKER_REL),
        # Preserve the sealed predecessor's compatibility reservation.  The
        # authoritative R7 reservation below separately binds the R7 entry.
        "verified_entry_worker_path": R6_WORKER_REL.as_posix(),
        "verified_entry_worker_sha256": indexed[R6_WORKER_REL.as_posix()]["sha256"],
        "verified_frozen_core_worker_path": R2_WORKER_REL.as_posix(),
        "verified_frozen_core_worker_sha256": sha256_file(
            PROJECT_ROOT / R2_WORKER_REL
        ),
        "verified_frozen_r3_worker_path": "tools/qwen3_tts_original_voice_forge_worker_v3.py",
        "verified_frozen_r3_worker_sha256": sha256_file(
            PROJECT_ROOT / "tools/qwen3_tts_original_voice_forge_worker_v3.py"
        ),
        "harness_manifest_sha256": sha256_file(PROJECT_ROOT / R4_MANIFEST_REL),
        "contract_sha256": sha256_file(PROJECT_ROOT / R2_CONTRACT_REL),
        "environment_spec_sha256": sha256_file(PROJECT_ROOT / R2_ENVIRONMENT_REL),
        "trusted_registry_sha256": sha256_file(
            PROJECT_ROOT / "Data/voice/policies/temporaryai_qwen3_tts_voice_forge_bundle_registry_v2.json"
        ),
        "bundle_seal_sha256": entry["bundle_seal_sha256"],
        "verified_original_synthetic_job": job_evidence,
        "exact_wheel_to_installed_bindings": parent_preflight,
        "network_boundary": "OFFLINE_FLAGS_ONLY_NO_PROCESS_LEVEL_NETWORK_DENIAL",
        "network_nonuse_proven": False,
    }
    frozen_path = pending / "parent_reservation.json"
    r7.write_new_json(frozen_path, frozen)
    frozen_sha = sha256_file(frozen_path)

    ledger_path = _stable_path(R7_LEDGER_ROOT_REL, args.execution_authorization_sha256)
    reservation_path = _stable_path(
        R7_RESERVATION_ROOT_REL, args.execution_authorization_sha256
    )
    reservation_v7 = {
        "schema": "qwen3_tts_voice_forge_parent_reservation_v7",
        "status": "EXTERNAL_AUTHORITY_PARENT_PREFLIGHT_AND_WORKER_IDENTITY_RESERVED",
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "attempt": relative(pending),
        "payload_manifest_sha256": args.payload_manifest_sha256,
        "execution_authorization_sha256": args.execution_authorization_sha256,
        "authorization_nonce_sha256": authorization["authorization_nonce_sha256"],
        "worker_instance_nonce_sha256": authorization["worker_instance_nonce_sha256"],
        "independent_audit_decision_sha256": authorization[
            "independent_audit_decision_sha256"
        ],
        "independent_audit_subject_sha256": authorization[
            "independent_audit_subject_sha256"
        ],
        "independent_auditor_identity_sha256": authorization[
            "independent_auditor_identity_sha256"
        ],
        "independent_audit_report_sha256": authorization["independent_audit_sha256"],
        "generation_seed": authorization["generation_seed"],
        "parent_authorization_ledger_path": relative(ledger_path),
        "verified_entry_worker_path": R7_WORKER_REL.as_posix(),
        "verified_entry_worker_sha256": indexed[R7_WORKER_REL.as_posix()]["sha256"],
        "worker_command_sha256": worker_command_sha256,
        "exact_parent_preflight_provenance": parent_preflight,
        "exact_parent_full_provenance": parent_full_preflight,
        "exact_parent_full_provenance_sha256": r7.canonical_sha256(
            parent_full_preflight
        ),
        "frozen_parent_reservation_sha256": frozen_sha,
    }
    r7.write_new_json(reservation_path, reservation_v7)
    reservation_sha = sha256_file(reservation_path)
    r7.validate_parent_reservation(
        reservation_v7,
        expected={
            key: value
            for key, value in reservation_v7.items()
            if key not in {"schema", "status"}
        },
    )
    ledger = {
        "schema": "qwen3_tts_voice_forge_authorization_ledger_v7",
        "status": "CONSUMED_FOR_ONE_EXACT_PENDING_ATTEMPT",
        "utc": r7.utc_now(),
        "authorization_sha256": args.execution_authorization_sha256,
        "authorization_nonce_sha256": authorization["authorization_nonce_sha256"],
        "worker_instance_nonce_sha256": authorization["worker_instance_nonce_sha256"],
        "independent_audit_decision_sha256": authorization[
            "independent_audit_decision_sha256"
        ],
        "independent_audit_subject_sha256": authorization[
            "independent_audit_subject_sha256"
        ],
        "independent_auditor_identity_sha256": authorization[
            "independent_auditor_identity_sha256"
        ],
        "independent_audit_report_sha256": authorization["independent_audit_sha256"],
        "payload_manifest_sha256": args.payload_manifest_sha256,
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "attempt": relative(pending),
        "parent_reservation_path": relative(reservation_path),
        "parent_reservation_sha256": reservation_sha,
        "verified_worker_path": R7_WORKER_REL.as_posix(),
        "verified_worker_sha256": indexed[R7_WORKER_REL.as_posix()]["sha256"],
        "worker_command_sha256": worker_command_sha256,
    }
    r7.write_new_json(ledger_path, ledger)
    ledger_sha = sha256_file(ledger_path)
    r7.validate_parent_ledger(
        ledger,
        expected={
            key: value
            for key, value in ledger.items()
            if key not in {"schema", "status", "utc"}
        },
    )

    # The inherited R6 semantic object hashes this stable R6-format record.
    # It points at the authoritative R7 ledger; it does not grant authority.
    r6_reservation_path = _stable_path(
        R6_COMPAT_RESERVATION_ROOT_REL, args.execution_authorization_sha256
    )
    r6_reservation = {
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
        "verified_entry_worker_sha256": indexed[R6_WORKER_REL.as_posix()]["sha256"],
        "exact_parent_preflight_provenance": parent_preflight,
        "exact_parent_full_provenance": parent_full_preflight,
        "exact_parent_full_provenance_sha256": r7.canonical_sha256(
            parent_full_preflight
        ),
        "frozen_parent_reservation_sha256": frozen_sha,
    }
    r7.write_new_json(r6_reservation_path, r6_reservation)
    r6_reservation_sha = sha256_file(r6_reservation_path)

    compatibility_authorization_evidence = {
        key: (
            value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            if isinstance(value, datetime)
            else value
        )
        for key, value in authorization_evidence.items()
    }
    compatibility_v5 = {
        "schema": "qwen3_tts_voice_forge_parent_reservation_v5",
        "status": "EXTERNAL_AUTHORITY_AND_PARENT_PREFLIGHT_RESERVED",
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "attempt": relative(pending),
        "payload_manifest_sha256": args.payload_manifest_sha256,
        "execution_authorization": compatibility_authorization_evidence,
        "execution_authorization_sha256": args.execution_authorization_sha256,
        "authorization_ledger_path": relative(ledger_path),
        "authorization_ledger_sha256": ledger_sha,
        "exact_parent_preflight_provenance": parent_preflight,
        "exact_parent_full_provenance": parent_full_preflight,
        "exact_parent_full_provenance_sha256": r5.canonical_sha256(
            parent_full_preflight
        ),
        "frozen_parent_reservation_sha256": frozen_sha,
    }
    r7.write_new_json(pending / "parent_reservation_v5.json", compatibility_v5)
    return {
        "r7_reservation": reservation_v7,
        "r7_reservation_path": reservation_path,
        "r7_reservation_sha256": reservation_sha,
        "r7_ledger": ledger,
        "r7_ledger_path": ledger_path,
        "r7_ledger_sha256": ledger_sha,
        "r6_reservation": r6_reservation,
        "r6_reservation_path": r6_reservation_path,
        "r6_reservation_sha256": r6_reservation_sha,
    }


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


class _JobBasicAccounting(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_int64),
        ("TotalKernelTime", ctypes.c_int64),
        ("ThisPeriodTotalUserTime", ctypes.c_int64),
        ("ThisPeriodTotalKernelTime", ctypes.c_int64),
        ("TotalPageFaultCount", ctypes.c_uint32),
        ("TotalProcesses", ctypes.c_uint32),
        ("ActiveProcesses", ctypes.c_uint32),
        ("TotalTerminatedProcesses", ctypes.c_uint32),
    ]


def run_contained_worker_v7(
    command: list[str],
    *,
    env: dict[str, str],
    timeout: float,
    worker_sha256: str,
    authorization_sha256: str,
    worker_instance_nonce_sha256: str,
    command_sha256: str,
) -> tuple[subprocess.CompletedProcess[bytes], dict[str, Any]]:
    """Run the exact worker in a kill-on-close Windows Job and close the tree."""

    if os.name != "nt":
        raise R7LauncherError("R7 bounded worker containment is Windows-only")
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
        raise R7LauncherError("cannot create R7 Job Object")
    info = _JobExtendedLimit()
    info.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
    if not set_job(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
        close_handle(job)
        raise R7LauncherError("cannot configure R7 Job Object")
    process: subprocess.Popen[bytes] | None = None
    started = time.perf_counter()
    termination_succeeded = False
    try:
        process = subprocess.Popen(
            command,
            cwd=str(PROJECT_ROOT),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=0x00000004 | 0x00000200 | 0x01000000,
        )
        primary_pid = int(process.pid)
        process_handle = ctypes.c_void_p(int(process._handle))  # type: ignore[attr-defined]
        if not assign_job(job, process_handle):
            process.kill()
            raise R7LauncherError("cannot assign suspended R7 worker to its Job")
        if resume_process(process_handle) != 0:
            if not terminate_job(job, 2):
                raise R7LauncherError("cannot resume or terminate contained R7 worker")
            raise R7LauncherError("cannot resume contained R7 worker")
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            if not terminate_job(job, 2):
                raise R7LauncherError("R7 worker timed out and Job termination failed") from exc
            termination_succeeded = True
            process.communicate()
            raise R7LauncherError("contained R7 worker timed out") from exc
        if not terminate_job(job, 0):
            raise R7LauncherError(
                f"R7 Job termination failed; winerror={ctypes.get_last_error()}"
            )
        termination_succeeded = True
        accounting = _JobBasicAccounting()
        for _ in range(200):
            if not query_job(job, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None):
                raise R7LauncherError("cannot query R7 Job accounting after termination")
            if accounting.ActiveProcesses == 0:
                break
            time.sleep(0.025)
        else:
            raise R7LauncherError("R7 process tree did not become quiescent")
        extended = _JobExtendedLimit()
        if not query_job(job, 9, ctypes.byref(extended), ctypes.sizeof(extended), None):
            raise R7LauncherError("cannot query R7 Job extended limits")
        wall = time.perf_counter() - started
        observation = {
            "schema": "qwen3_tts_voice_forge_parent_job_observation_v7",
            "observed_by_parent_not_child": True,
            "windows_job_assigned_before_resume": True,
            "primary_worker_exit_code": int(process.returncode),
            "job_termination_requested_after_primary_exit": termination_succeeded,
            "active_processes_after_termination": int(accounting.ActiveProcesses),
            "process_tree_quiescent_before_finalization": accounting.ActiveProcesses == 0,
            "quiescence_observed_utc": datetime.now(timezone.utc).isoformat().replace(
                "+00:00", "Z"
            ),
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
            "primary_worker_pid": primary_pid,
            "parent_pid": os.getpid(),
            "worker_path": R7_WORKER_REL.as_posix(),
            "worker_sha256": worker_sha256,
            "worker_command_sha256": command_sha256,
            "authorization_sha256": authorization_sha256,
            "worker_instance_nonce_sha256": worker_instance_nonce_sha256,
            "job_kill_on_close_limit_active": True,
            "job_accounting_query_succeeded": True,
            "job_extended_limits_query_succeeded": True,
            "total_processes": int(accounting.TotalProcesses),
            "total_terminated_processes": int(accounting.TotalTerminatedProcesses),
        }
        return subprocess.CompletedProcess(
            command, int(process.returncode), stdout, stderr
        ), observation
    finally:
        if process is not None and process.poll() is None:
            terminate_job(job, 2)
            process.wait(timeout=10)
        close_handle(job)


def parse_canonical_child(r7: Any, payload: bytes) -> dict[str, Any]:
    if (
        not payload.endswith(b"\n")
        or payload.endswith(b"\n\n")
        or b"\r" in payload
        or b"\n" in payload[:-1]
    ):
        raise R7LauncherError("R7 child stdout is not one canonical object plus LF")
    value = r7.strict_json_bytes(payload[:-1], "R7 child stdout")
    r7.require_exact_keys(value, r7.R7_CHILD_KEYS, "R7 child stdout")
    if payload[:-1] != r7.canonical_bytes(value):
        raise R7LauncherError("R7 child stdout is not canonical")
    return value


def _r6_child_from_files(r7: Any, finalized: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = finalized / "worker_manifest_v6.json"
    manifest = r7.strict_read_json(manifest_path, label="R7 predecessor R6 manifest")
    semantic = manifest["semantic_binding_v6"]
    profile_path = finalized / "voice_profile_candidate_v6.json"
    child = {
        "schema": "qwen3_tts_original_voice_forge_child_result_v6",
        "status": manifest["status"],
        "semantic_binding_v6_sha256": r7.sealed_r6().canonical_sha256(semantic),
        "manifest_path": manifest_path.name,
        "manifest_sha256": sha256_file(manifest_path),
        "profile_path": profile_path.name,
        "profile_sha256": sha256_file(profile_path),
        "evaluator_evidence_path": "evaluator_evidence_v6.json",
        "evaluator_evidence_sha256": semantic["evaluator_evidence_sha256"],
        "worker_resource_evidence_path": "worker_resource_evidence_v6.json",
        "worker_resource_evidence_sha256": semantic["resource_evidence_sha256"],
        "worker_launch_claim_path": manifest["worker_launch_claim_path"],
        "worker_launch_claim_sha256": semantic["worker_launch_claim_sha256"],
        "artifact_seals_sha256": semantic["artifact_seals_sha256"],
    }
    return child, semantic


def collision_subjects(r7: Any, corpus_path: Path) -> set[tuple[str, str]]:
    corpus = r7.strict_read_json(corpus_path, label="R7 exact evaluation corpus")
    voices = corpus.get("voices")
    if not isinstance(voices, list):
        raise R7LauncherError("R7 collision corpus voices are absent")
    result: set[tuple[str, str]] = set()
    for row in voices:
        if not isinstance(row, dict):
            raise R7LauncherError("R7 collision corpus row is not an object")
        subject = (
            r7.require_id(row.get("voice_id"), "R7 corpus voice ID"),
            r7.require_id(row.get("kind"), "R7 corpus voice kind"),
        )
        if subject in result:
            raise R7LauncherError("R7 collision corpus subject is duplicated")
        result.add(subject)
    return result


def validate_output_chain(
    *,
    r7: Any,
    r6_parent: Any,
    finalized: Path,
    child: dict[str, Any],
    semantic: dict[str, Any],
    corpus_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    r6_child, r6_semantic = _r6_child_from_files(r7, finalized)
    r6_parent.validate_output_chain(
        r6=r7.sealed_r6(),
        finalized=finalized,
        child=r6_child,
        semantic=r6_semantic,
    )
    r6_profile = r7.strict_read_json(
        finalized / "voice_profile_candidate_v6.json",
        expected_sha256=r6_child["profile_sha256"],
        label="R7 predecessor profile",
    )
    r7_profile = r7.strict_read_json(
        finalized / "voice_profile_candidate_v7.json",
        expected_sha256=child["profile_sha256"],
        label="R7 profile",
    )
    r7_manifest = r7.strict_read_json(
        finalized / "worker_manifest_v7.json",
        expected_sha256=child["manifest_sha256"],
        label="R7 worker manifest",
    )
    evaluator = r7.strict_read_json(
        finalized / "evaluator_evidence_v7.json",
        expected_sha256=child["evaluator_evidence_sha256"],
        label="R7 evaluator evidence",
    )
    worker_resource = r7.strict_read_json(
        finalized / "worker_resource_evidence_v7.json",
        expected_sha256=child["worker_resource_evidence_sha256"],
        label="R7 worker resource evidence",
    )
    if r7_manifest["semantic_binding_v7"] != semantic:
        raise R7LauncherError("R7 manifest semantic differs from parent subject")
    r7.validate_r7_profile_manifest_and_child(
        r6_profile=r6_profile,
        r7_profile=r7_profile,
        r7_manifest=r7_manifest,
        child_result=child,
        semantic_binding=semantic,
        r6_profile_sha256=r6_child["profile_sha256"],
        r6_manifest_sha256=r6_child["manifest_sha256"],
        r7_profile_sha256=child["profile_sha256"],
    )
    if sha256_file(corpus_path) != semantic["evaluation_corpus_sha256"]:
        raise R7LauncherError("R7 evaluation corpus differs from the semantic binding")
    r7.validate_evaluator_evidence(
        evaluator,
        semantic_binding=semantic,
        project_root=PROJECT_ROOT,
        expected_collision_subjects=collision_subjects(r7, corpus_path),
    )
    r7.validate_worker_resource_evidence(
        worker_resource, semantic_binding=semantic
    )
    return evaluator, worker_resource


def later_use_semantic_validator(
    r7: Any, r6_parent: Any, project_root: Path
) -> Callable[[dict[str, dict[str, Any]], dict[str, Any]], None]:
    def validate(indexed: dict[str, dict[str, Any]], semantic: dict[str, Any]) -> None:
        required = {
            "r4_profile",
            "r4_manifest",
            "r5_profile",
            "r5_manifest",
            "r6_profile",
            "r6_manifest",
            "r7_profile",
            "r7_manifest",
            "verified_child_result",
            "evaluator_evidence",
            "worker_resource_evidence",
            "parent_resource_evidence",
            "worker_stdout",
            "worker_stderr",
            "reference_wav",
            "clone_test_wav",
            "runtime_clone_prompt",
            "reference_transcript",
            "clone_transcript",
            "parent_authorization_ledger",
            "parent_reservation_v7",
            "parent_reservation_r6_compat",
            "worker_launch_claim",
            "execution_authorization",
            "independent_audit_decision",
            "independent_audit_report",
            "rejected_r6_audit",
            "payload_manifest",
            "live_identity_clearance",
            "live_watermark_scan",
            "bundle_envelope",
            "bundle_seal",
            "canonical_candidate_profile",
            "canonical_creation_request",
            "job",
            "owner_authorization",
            "identity_clearance_manifest",
            "watermark_preflight_manifest",
            "evaluation_corpus",
            "voice_design_model_manifest",
            "base_model_manifest",
        }
        if not required.issubset(indexed):
            raise R7LauncherError("R7 later-use accepted inventory is incomplete")
        authorization_hash = semantic["execution_authorization_sha256"]
        expected_stable_paths = {
            "parent_authorization_ledger": (
                R7_LEDGER_ROOT_REL / f"{authorization_hash}.json"
            ).as_posix(),
            "parent_reservation_v7": (
                R7_RESERVATION_ROOT_REL / f"{authorization_hash}.json"
            ).as_posix(),
            "parent_reservation_r6_compat": (
                R6_COMPAT_RESERVATION_ROOT_REL / f"{authorization_hash}.json"
            ).as_posix(),
            "worker_launch_claim": (
                r7.R7_WORKER_CLAIM_ROOT_REL / f"{authorization_hash}.json"
            ).as_posix(),
        }
        if any(
            indexed[role]["path"] != expected_path
            for role, expected_path in expected_stable_paths.items()
        ):
            raise R7LauncherError("R7 later-use authority record left its exact stable root")
        exact_identity_paths = {
            "execution_authorization": semantic["execution_authorization_path"],
            "independent_audit_decision": semantic[
                "independent_audit_decision_path"
            ],
            "independent_audit_report": semantic["independent_audit_report_path"],
            "rejected_r6_audit": R6_AUDIT_REL.as_posix(),
            "payload_manifest": R7_PAYLOAD_REL.as_posix(),
        }
        if any(
            indexed[role]["path"] != expected_path
            for role, expected_path in exact_identity_paths.items()
        ):
            raise R7LauncherError("R7 later-use authorization/audit path identity drifted")
        if (
            semantic["entry_worker_path"] != R7_WORKER_REL.as_posix()
            or semantic["entry_worker_sha256"]
            != sha256_file(project_root / R7_WORKER_REL)
            or not any(
                row["path"] == R7_WORKER_REL.as_posix()
                and row["sha256"] == semantic["entry_worker_sha256"]
                for role, row in indexed.items()
                if role.startswith("sealed_payload_")
            )
        ):
            raise R7LauncherError("R7 later-use entry worker is not the sealed payload worker")
        child = r7.strict_read_json(
            project_root / indexed["verified_child_result"]["path"],
            expected_sha256=indexed["verified_child_result"]["sha256"],
            label="R7 later-use child result",
        )
        finalized = (project_root / indexed["r7_manifest"]["path"]).parent
        _evaluator, worker_resource = validate_output_chain(
            r7=r7,
            r6_parent=r6_parent,
            finalized=finalized,
            child=child,
            semantic=semantic,
            corpus_path=project_root / indexed["evaluation_corpus"]["path"],
        )
        claim = r7.strict_read_json(
            project_root / indexed["worker_launch_claim"]["path"],
            expected_sha256=semantic["worker_launch_claim_sha256"],
            label="R7 later-use worker claim",
        )
        ledger = r7.strict_read_json(
            project_root / indexed["parent_authorization_ledger"]["path"],
            expected_sha256=semantic["parent_authorization_ledger_sha256"],
            label="R7 later-use ledger",
        )
        reservation = r7.strict_read_json(
            project_root / indexed["parent_reservation_v7"]["path"],
            expected_sha256=indexed["parent_reservation_v7"]["sha256"],
            label="R7 later-use reservation",
        )
        audit_values = {
            "independent_audit_decision_sha256": semantic[
                "independent_audit_decision_sha256"
            ],
            "independent_audit_subject_sha256": semantic[
                "independent_audit_subject_sha256"
            ],
            "independent_auditor_identity_sha256": semantic[
                "independent_auditor_identity_sha256"
            ],
            "independent_audit_report_sha256": semantic[
                "independent_audit_report_sha256"
            ],
        }
        reservation_expected = {
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
            "worker_instance_nonce_sha256": semantic["worker_instance_nonce_sha256"],
            **audit_values,
            "generation_seed": semantic["generation_seed"],
            "parent_authorization_ledger_path": indexed[
                "parent_authorization_ledger"
            ]["path"],
            "verified_entry_worker_path": semantic["entry_worker_path"],
            "verified_entry_worker_sha256": semantic["entry_worker_sha256"],
            "worker_command_sha256": semantic["worker_command_sha256"],
        }
        r7.validate_parent_reservation(reservation, expected=reservation_expected)
        ledger_expected = {
            "authorization_sha256": semantic["execution_authorization_sha256"],
            "authorization_nonce_sha256": semantic[
                "execution_authorization_nonce_sha256"
            ],
            "worker_instance_nonce_sha256": semantic["worker_instance_nonce_sha256"],
            **audit_values,
            "payload_manifest_sha256": semantic["payload_manifest_sha256"],
            "bundle_id": semantic["bundle_id"],
            "run_id": semantic["run_id"],
            "attempt": semantic["attempt"],
            "parent_reservation_path": indexed["parent_reservation_v7"]["path"],
            "parent_reservation_sha256": indexed["parent_reservation_v7"]["sha256"],
            "verified_worker_path": semantic["entry_worker_path"],
            "verified_worker_sha256": semantic["entry_worker_sha256"],
            "worker_command_sha256": semantic["worker_command_sha256"],
        }
        r7.validate_parent_ledger(ledger, expected=ledger_expected)
        claim_expected = {
            **ledger_expected,
            "parent_ledger_path": indexed["parent_authorization_ledger"]["path"],
            "parent_ledger_sha256": semantic["parent_authorization_ledger_sha256"],
            "worker_path": semantic["entry_worker_path"],
            "worker_sha256": semantic["entry_worker_sha256"],
        }
        claim_expected.pop("verified_worker_path")
        claim_expected.pop("verified_worker_sha256")
        r7.validate_worker_launch_claim(claim, expected=claim_expected)
        if claim["worker_instance_nonce_sha256"] != semantic["worker_instance_nonce_sha256"]:
            raise R7LauncherError("R7 later-use claim nonce is not authorization-bound")

        r6_reservation = r7.strict_read_json(
            project_root / indexed["parent_reservation_r6_compat"]["path"],
            expected_sha256=semantic["parent_reservation_sha256"],
            label="R7 held R6 compatibility reservation",
        )
        r7.sealed_r6().validate_parent_reservation(
            r6_reservation,
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
                "worker_instance_nonce_sha256": semantic[
                    "worker_instance_nonce_sha256"
                ],
                "generation_seed": semantic["generation_seed"],
                "parent_authorization_ledger_path": indexed[
                    "parent_authorization_ledger"
                ]["path"],
                "verified_entry_worker_path": R6_WORKER_REL.as_posix(),
                "verified_entry_worker_sha256": sha256_file(
                    project_root / R6_WORKER_REL
                ),
            },
        )
        parent_resource = r7.strict_read_json(
            project_root / indexed["parent_resource_evidence"]["path"],
            expected_sha256=indexed["parent_resource_evidence"]["sha256"],
            label="R7 later-use parent resource evidence",
        )
        r7.validate_resource_evidence(
            parent_resource,
            worker_evidence=worker_resource,
            semantic_binding=semantic,
            worker_claim=claim,
            stdout_row=indexed["worker_stdout"],
            stderr_row=indexed["worker_stderr"],
        )
        evaluator = r7.strict_read_json(
            project_root / indexed["evaluator_evidence"]["path"],
            expected_sha256=semantic["evaluator_evidence_sha256"],
            label="R7 later-use evaluator evidence",
        )
        exact_role_hashes = {
            "canonical_candidate_profile": semantic["canonical_profile_sha256"],
            "canonical_creation_request": semantic[
                "canonical_creation_request_sha256"
            ],
            "job": semantic["job_sha256"],
            "owner_authorization": semantic["owner_authorization_sha256"],
            "identity_clearance_manifest": evaluator["named_person_clearance"][
                "static_manifest_sha256"
            ],
            "watermark_preflight_manifest": evaluator["watermark"][
                "preflight_manifest_sha256"
            ],
            "voice_design_model_manifest": semantic[
                "voice_design_model_manifest_sha256"
            ],
            "base_model_manifest": semantic["base_model_manifest_sha256"],
            "evaluation_corpus": semantic["evaluation_corpus_sha256"],
            "execution_authorization": semantic[
                "execution_authorization_sha256"
            ],
            "independent_audit_decision": semantic[
                "independent_audit_decision_sha256"
            ],
            "independent_audit_report": semantic[
                "independent_audit_report_sha256"
            ],
            "rejected_r6_audit": R6_AUDIT_SHA256,
            "payload_manifest": semantic["payload_manifest_sha256"],
        }
        for role, expected_hash in exact_role_hashes.items():
            if indexed[role]["sha256"] != expected_hash:
                raise R7LauncherError(f"R7 later-use trusted {role} hash mismatch")

    return validate


def reopen_acceptance_for_later_use(
    r7: Any,
    r6_parent: Any,
    *,
    acceptance_path: Path,
    expected_acceptance_sha256: str,
    commit_token_path: Path,
    expected_commit_token_sha256: str,
    required_payloads: set[str],
) -> dict[str, Any]:
    return r7.reopen_acceptance_for_later_use(
        project_root=PROJECT_ROOT,
        acceptance_path=acceptance_path,
        expected_acceptance_sha256=expected_acceptance_sha256,
        commit_token_path=commit_token_path,
        expected_commit_token_sha256=expected_commit_token_sha256,
        required_payloads=required_payloads,
        semantic_validator=later_use_semantic_validator(r7, r6_parent, PROJECT_ROOT),
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    if (
        not args.execute
        or not args.acknowledge_private_unreviewed
        or not args.acknowledge_no_download
    ):
        raise R7LauncherError("R7 parent remains inert without every bounded acknowledgement")
    if not SAFE_ID.fullmatch(str(args.bundle_id or "")) or not SAFE_ID.fullmatch(
        str(args.run_id or "")
    ):
        raise R7LauncherError("R7 requires safe opaque bundle/run IDs")
    if not all(
        (
            args.payload_manifest_sha256,
            args.execution_authorization,
            args.execution_authorization_sha256,
        )
    ):
        raise R7LauncherError("R7 lacks exact payload and authorization arguments")

    (
        r7,
        manifest,
        indexed,
        required_payloads,
        authorization,
        authorization_evidence,
        verified_at,
    ) = bootstrap_external_trust(args)
    incident = reserve_incident(args.bundle_id, args.run_id)
    pending: Path | None = None
    stage = "R7_EXTERNAL_AUDIT_AND_AUTHORITY_VERIFIED"
    try:
        # Predecessor imports are deliberately below the R7 audit/auth boundary.
        r6_parent = load_sealed_module(
            R6_RUNNER_REL,
            indexed[R6_RUNNER_REL.as_posix()],
            "qwen3_tts_r6_parent_for_r7",
        )
        r5 = load_sealed_module(
            R5_GUARDS_REL,
            indexed[R5_GUARDS_REL.as_posix()],
            "qwen3_tts_r5_guards_for_r7_parent",
        )
        r5_runner = load_sealed_module(
            R5_RUNNER_REL,
            indexed[R5_RUNNER_REL.as_posix()],
            "qwen3_tts_r5_runner_for_r7_parent",
        )
        r4_guards = load_sealed_module(
            R4_GUARDS_REL,
            indexed[R4_GUARDS_REL.as_posix()],
            "qwen3_tts_r4_guards_for_r7_parent",
        )
        r4_runner = load_sealed_module(
            R4_RUNNER_REL,
            indexed[R4_RUNNER_REL.as_posix()],
            "qwen3_tts_r4_runner_for_r7_parent",
        )
        r3_guards = load_sealed_module(
            R3_GUARDS_REL,
            indexed[R3_GUARDS_REL.as_posix()],
            "qwen3_tts_r3_guards_for_r7_parent",
        )
        r3_runner = load_sealed_module(
            R3_RUNNER_REL,
            indexed[R3_RUNNER_REL.as_posix()],
            "qwen3_tts_r3_runner_for_r7_parent",
        )
        v2 = load_sealed_module(
            R2_RUNNER_REL,
            indexed[R2_RUNNER_REL.as_posix()],
            "qwen3_tts_r2_runner_for_r7_parent",
        )
        r5_runner.install_strict_json_readers(
            r5, r4_runner, r3_guards, r3_runner, v2
        )
        r5_runner.configure_parent_chain(
            r5=r5,
            r4_guards=r4_guards,
            r3_guards=r3_guards,
            r3_runner=r3_runner,
            v2=v2,
        )
        contract = r7.strict_read_json(
            PROJECT_ROOT / R2_CONTRACT_REL, label="R7 contract"
        )
        environment = r7.strict_read_json(
            PROJECT_ROOT / R2_ENVIRONMENT_REL, label="R7 environment"
        )
        bundle, entry, bundle_dir = v2.verify_bundle_envelope(args.bundle_id)
        binding = r4_guards.execution_binding(bundle)
        job_evidence = r4_runner.validate_bound_original_job(v2, bundle, bundle_dir)
        corpus_path = PROJECT_ROOT / bundle["evaluation_corpus_path"]
        if not collision_subjects(r7, corpus_path):
            raise R7LauncherError(
                "R7 exact collision corpus is empty; no worker may launch"
            )
        isolated_python, parent_preflight = r3_runner.validate_ready_environment_r3(
            v2=v2,
            guards=r3_guards,
            contract=contract,
            environment=environment,
            worker_path=PROJECT_ROOT / R7_WORKER_REL,
        )
        isolated_python = Path(isolated_python).resolve()
        parent_preflight = r5.require_strict_provenance_map(
            parent_preflight, "R7 parent preflight"
        )
        parent_full_preflight = r5_runner.derive_parent_full_provenance(
            r5, v2=v2, r3_guards=r3_guards, environment=environment
        )
        pending = reserve_pending(args.run_id, args.bundle_id)
        nonce_ledger, nonce_ledger_hash = v2.consume_nonce(bundle, pending)
        command = canonical_worker_command(isolated_python, pending, args)
        worker_command_sha = r7.canonical_sha256(command)
        records = write_parent_reservations(
            r7=r7,
            r5=r5,
            v2=v2,
            pending=pending,
            args=args,
            authorization=authorization,
            authorization_evidence=authorization_evidence,
            bundle=bundle,
            binding=binding,
            job_evidence=job_evidence,
            entry=entry,
            parent_preflight=parent_preflight,
            parent_full_preflight=parent_full_preflight,
            nonce_ledger=nonce_ledger,
            nonce_ledger_hash=nonce_ledger_hash,
            worker_command_sha256=worker_command_sha,
            indexed=indexed,
        )
        stage = "CONTAINED_R7_WORKER"
        completed, parent_observation = run_contained_worker_v7(
            command,
            env=r5_runner.restricted_child_environment(
                v2, isolated_python, args.run_id
            ),
            timeout=1800,
            worker_sha256=indexed[R7_WORKER_REL.as_posix()]["sha256"],
            authorization_sha256=args.execution_authorization_sha256,
            worker_instance_nonce_sha256=authorization[
                "worker_instance_nonce_sha256"
            ],
            command_sha256=worker_command_sha,
        )
        stdout_path = pending / "worker_stdout_v7.log"
        stderr_path = pending / "worker_stderr_v7.log"
        r7.write_new(stdout_path, completed.stdout)
        r7.write_new(stderr_path, completed.stderr)
        if completed.returncode != 0:
            raise R7LauncherError(f"R7 worker failed with {completed.returncode}")
        child = parse_canonical_child(r7, completed.stdout)
        manifest_v7 = r7.strict_read_json(
            pending / "worker_manifest_v7.json",
            expected_sha256=child["manifest_sha256"],
            label="R7 pre-final worker manifest",
        )
        semantic = manifest_v7["semantic_binding_v7"]
        r7.validate_semantic_binding(semantic)
        claim_path = PROJECT_ROOT / child["worker_launch_claim_path"]
        claim = r7.strict_read_json(
            claim_path,
            expected_sha256=child["worker_launch_claim_sha256"],
            label="R7 parent worker claim",
        )
        expected_claim = {
            "authorization_sha256": args.execution_authorization_sha256,
            "authorization_nonce_sha256": authorization[
                "authorization_nonce_sha256"
            ],
            "worker_instance_nonce_sha256": authorization[
                "worker_instance_nonce_sha256"
            ],
            "independent_audit_decision_sha256": authorization[
                "independent_audit_decision_sha256"
            ],
            "independent_audit_subject_sha256": authorization[
                "independent_audit_subject_sha256"
            ],
            "independent_auditor_identity_sha256": authorization[
                "independent_auditor_identity_sha256"
            ],
            "independent_audit_report_sha256": authorization[
                "independent_audit_sha256"
            ],
            "payload_manifest_sha256": args.payload_manifest_sha256,
            "bundle_id": args.bundle_id,
            "run_id": args.run_id,
            "attempt": relative(pending),
            "parent_reservation_path": relative(records["r7_reservation_path"]),
            "parent_reservation_sha256": records["r7_reservation_sha256"],
            "parent_ledger_path": relative(records["r7_ledger_path"]),
            "parent_ledger_sha256": records["r7_ledger_sha256"],
            "worker_path": R7_WORKER_REL.as_posix(),
            "worker_sha256": indexed[R7_WORKER_REL.as_posix()]["sha256"],
            "worker_command_sha256": worker_command_sha,
        }
        r7.validate_worker_launch_claim(claim, expected=expected_claim)
        if (
            semantic["worker_instance_nonce_sha256"]
            != authorization["worker_instance_nonce_sha256"]
            or semantic["independent_audit_decision_sha256"]
            != authorization["independent_audit_decision_sha256"]
            or semantic["independent_audit_subject_sha256"]
            != authorization["independent_audit_subject_sha256"]
            or semantic["independent_auditor_identity_sha256"]
            != authorization["independent_auditor_identity_sha256"]
            or semantic["independent_audit_report_sha256"]
            != authorization["independent_audit_sha256"]
            or semantic["worker_command_sha256"] != worker_command_sha
        ):
            raise R7LauncherError("R7 semantic identity differs from exact authority/launch")
        validate_output_chain(
            r7=r7,
            r6_parent=r6_parent,
            finalized=pending,
            child=child,
            semantic=semantic,
            corpus_path=corpus_path,
        )
        parent_observation["finalization_started_utc"] = r7.utc_now()
        worker_resource = r7.strict_read_json(
            pending / "worker_resource_evidence_v7.json",
            expected_sha256=child["worker_resource_evidence_sha256"],
            label="R7 worker resource evidence",
        )
        parent_resource = {
            "schema": "qwen3_tts_voice_forge_resource_reconciliation_v7",
            "status": "PARENT_RECONCILED_AFTER_PROCESS_TREE_QUIESCENCE",
            "semantic_binding_sha256": r7.evidence_subject_sha256(semantic),
            "worker_resource_evidence_sha256": child[
                "worker_resource_evidence_sha256"
            ],
            "parent_job_observation": parent_observation,
            "parent_job_observation_sha256": r7.canonical_sha256(
                parent_observation
            ),
            "worker_only_telemetry_accepted_as_parent_truth": False,
            "reconciliation_passed": True,
        }
        r7.write_new_json(
            pending / "parent_resource_evidence_v7.json", parent_resource
        )
        r7.write_new_json(pending / "verified_child_result_v7.json", child)
        finalized = r5.finalize_pending_tree(
            pending, pending.parent / f"finalized_{pending.name}"
        )
        pending = None
        validate_output_chain(
            r7=r7,
            r6_parent=r6_parent,
            finalized=finalized,
            child=child,
            semantic=semantic,
            corpus_path=corpus_path,
        )

        role_names = {
            "r4_profile": "voice_profile_candidate_v4.json",
            "r4_manifest": "worker_manifest_v4.json",
            "r5_profile": "voice_profile_candidate_v5.json",
            "r5_manifest": "worker_manifest_v5.json",
            "r6_profile": "voice_profile_candidate_v6.json",
            "r6_manifest": "worker_manifest_v6.json",
            "r7_profile": "voice_profile_candidate_v7.json",
            "r7_manifest": "worker_manifest_v7.json",
            "verified_child_result": "verified_child_result_v7.json",
            "evaluator_evidence": "evaluator_evidence_v7.json",
            "worker_resource_evidence": "worker_resource_evidence_v7.json",
            "parent_resource_evidence": "parent_resource_evidence_v7.json",
            "worker_stdout": "worker_stdout_v7.log",
            "worker_stderr": "worker_stderr_v7.log",
            "reference_wav": "original_design_reference.wav",
            "clone_test_wav": "runtime_clone_test.wav",
            "runtime_clone_prompt": "runtime_clone_prompt.pt",
            "reference_transcript": "reference_asr_transcript_v6.txt",
            "clone_transcript": "clone_asr_transcript_v6.txt",
            "live_identity_clearance": "live_identity_clearance_v2.json",
            "live_watermark_scan": "live_watermark_documentation_scan_v2.json",
        }
        role_paths: dict[str, Path] = {
            role: finalized / name for role, name in role_names.items()
        }
        role_paths.update(
            {
                "bundle_envelope": bundle_dir / "acceptance_bundle.json",
                "bundle_seal": bundle_dir / "BUNDLE_SEAL.json",
                "canonical_candidate_profile": PROJECT_ROOT
                / bundle["canonical_profile_path"],
                "canonical_creation_request": PROJECT_ROOT
                / bundle["canonical_creation_request_path"],
                "job": bundle_dir / bundle["job_path"],
                "owner_authorization": bundle_dir
                / bundle["owner_authorization_path"],
                "identity_clearance_manifest": bundle_dir
                / bundle["identity_clearance_manifest_path"],
                "watermark_preflight_manifest": bundle_dir
                / bundle["watermark_evidence_manifest_path"],
                "evaluation_corpus": corpus_path,
                "voice_design_model_manifest": PROJECT_ROOT
                / bundle["voice_design_model_manifest_path"],
                "base_model_manifest": PROJECT_ROOT
                / bundle["base_model_manifest_path"],
                "parent_reservation_v7": records["r7_reservation_path"],
                "parent_reservation_r6_compat": records[
                    "r6_reservation_path"
                ],
                "parent_authorization_ledger": records["r7_ledger_path"],
                "worker_launch_claim": claim_path,
                "execution_authorization": Path(
                    args.execution_authorization
                ).resolve(),
                "independent_audit_decision": PROJECT_ROOT
                / authorization["independent_audit_decision_path"],
                "independent_audit_report": PROJECT_ROOT
                / authorization["independent_audit_path"],
                "rejected_r6_audit": PROJECT_ROOT / R6_AUDIT_REL,
                "payload_manifest": PROJECT_ROOT / R7_PAYLOAD_REL,
            }
        )
        for index, rel in enumerate(sorted(required_payloads)):
            role_paths[f"sealed_payload_{index:03d}"] = PROJECT_ROOT / rel
        held_paths = list(role_paths.values())
        later_validator = later_use_semantic_validator(r7, r6_parent, PROJECT_ROOT)
        acceptance_path = (
            finalized.parent / f"{finalized.name}_parent_acceptance_v7.json"
        )
        commit_token_path = (
            finalized.parent / f"{finalized.name}_windows_identity_commit_v7.json"
        )
        with r7.hold_windows_file_leases(
            project_root=PROJECT_ROOT, paths=held_paths
        ) as held:
            accepted_files = [
                r7.file_row_from_held(
                    project_root=PROJECT_ROOT,
                    role=role,
                    path=path,
                    held=held,
                )
                for role, path in role_paths.items()
            ]
            accepted_indexed = r7.verify_accepted_files(
                project_root=PROJECT_ROOT,
                rows=accepted_files,
                identity_provider=lambda path: held.initial_rows[path.resolve()][
                    "windows_file_identity"
                ],
            )
            later_validator(accepted_indexed, semantic)
            parent_resource_reopened = r7.strict_read_json(
                finalized / "parent_resource_evidence_v7.json",
                label="R7 held parent resource evidence",
            )
            r7.validate_resource_evidence(
                parent_resource_reopened,
                worker_evidence=worker_resource,
                semantic_binding=semantic,
                worker_claim=claim,
                stdout_row=accepted_indexed["worker_stdout"],
                stderr_row=accepted_indexed["worker_stderr"],
            )
            acceptance = {
                "schema": "qwen3_tts_original_voice_forge_parent_acceptance_v7",
                "status": "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_FRESH_EXECUTION_AUDIT_REQUIRED",
                "accepted_utc": r7.utc_now(),
                "authorization_verified_at_start_utc": verified_at.isoformat().replace(
                    "+00:00", "Z"
                ),
                "semantic_binding_v7": semantic,
                "semantic_binding_v7_sha256": r7.canonical_sha256(semantic),
                "payload_manifest_path": R7_PAYLOAD_REL.as_posix(),
                "payload_manifest_sha256": args.payload_manifest_sha256,
                "execution_authorization_path": relative(
                    Path(args.execution_authorization)
                ),
                "execution_authorization_sha256": args.execution_authorization_sha256,
                "independent_audit_decision_path": authorization[
                    "independent_audit_decision_path"
                ],
                "independent_audit_decision_sha256": authorization[
                    "independent_audit_decision_sha256"
                ],
                "independent_audit_subject_sha256": authorization[
                    "independent_audit_subject_sha256"
                ],
                "independent_auditor_identity_sha256": authorization[
                    "independent_auditor_identity_sha256"
                ],
                "independent_r7_audit_path": authorization[
                    "independent_audit_path"
                ],
                "independent_r7_audit_sha256": authorization[
                    "independent_audit_sha256"
                ],
                "rejected_r6_audit_path": R6_AUDIT_REL.as_posix(),
                "rejected_r6_audit_sha256": R6_AUDIT_SHA256,
                "parent_authorization_ledger_path": relative(
                    records["r7_ledger_path"]
                ),
                "parent_authorization_ledger_sha256": records[
                    "r7_ledger_sha256"
                ],
                "worker_launch_claim_path": relative(claim_path),
                "worker_launch_claim_sha256": child[
                    "worker_launch_claim_sha256"
                ],
                "accepted_files": accepted_files,
                "accepted_files_sha256": r7.canonical_sha256(accepted_files),
                "held_file_identities_sha256": r7.canonical_sha256(
                    [row["windows_file_identity"] for row in accepted_files]
                ),
                "windows_identity_commit_required": True,
                "owner_hearing_acceptance": "PENDING",
                "assignment_allowed": False,
                "activation_allowed": False,
                "publication_or_upload_allowed": False,
                "complete_later_use_revalidation_required": True,
            }

            def validate_while_held(reopened: dict[str, Any]) -> None:
                r7.validate_complete_reopened_acceptance(
                    project_root=PROJECT_ROOT,
                    acceptance=reopened,
                    required_payloads=required_payloads,
                    semantic_validator=later_validator,
                    identity_provider=lambda path: held.initial_rows[path.resolve()][
                        "windows_file_identity"
                    ],
                )

            commit = r7.commit_acceptance_with_held_identities(
                project_root=PROJECT_ROOT,
                held=held,
                acceptance_path=acceptance_path,
                acceptance=acceptance,
                reopen_validator=validate_while_held,
                commit_token_path=commit_token_path,
            )
        reopen_acceptance_for_later_use(
            r7,
            r6_parent,
            acceptance_path=acceptance_path,
            expected_acceptance_sha256=commit["acceptance_sha256"],
            commit_token_path=commit_token_path,
            expected_commit_token_sha256=commit["commit_token_sha256"],
            required_payloads=required_payloads,
        )
        return {
            **acceptance,
            "parent_acceptance_path": relative(acceptance_path),
            "parent_acceptance_sha256": commit["acceptance_sha256"],
            "windows_identity_commit_path": relative(commit_token_path),
            "windows_identity_commit_sha256": commit["commit_token_sha256"],
        }
    except BaseException as exc:
        try:
            r7.write_new_json(
                incident / "failure_v7.json",
                {
                    "schema": "qwen3_tts_voice_forge_failure_v7",
                    "status": "FAILED_CLOSED",
                    "stage": stage,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                    "attempt": relative(pending) if pending else None,
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
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as exc:
        print(f"R7 Qwen3-TTS parent failed closed: {exc}", file=sys.stderr)
        raise SystemExit(2)
