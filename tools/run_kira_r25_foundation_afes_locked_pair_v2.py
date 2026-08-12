#!/usr/bin/env python3
"""Attempt-02 controller for two locked read-only R25 AFES extractions.

Project modules are intentionally not imported at module load.  The controller
discovers paths without treating them as trusted, acquires deny-write/delete
handles to the complete set, revalidates every byte/hash while those handles
are held, and only then imports or launches project code.  Locks remain held
through both fresh children and the final after snapshot.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Iterable, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CONTRACT_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v2.json"
)
OUTPUT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution/attempt_02"
)
MAX_FRAME_BYTES = 1_048_628
MAX_STDOUT_BYTES = 4 * 1024 * 1024
MAX_STDERR_BYTES = 4 * 1024 * 1024
ENVIRONMENT_ALLOWLIST = (
    "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERNAME", "USERPROFILE",
    "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA", "APPDATA", "Path",
)
FORCED_ENVIRONMENT_RELATIVE = {
    "PYTHONNOUSERSITE": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "BLENDER_USER_CONFIG": "RecoverySprint/runtime_cache/r25_blender/user_config",
    "BLENDER_USER_SCRIPTS": "RecoverySprint/runtime_cache/r25_blender/user_scripts",
    "BLENDER_USER_DATAFILES": "RecoverySprint/runtime_cache/r25_blender/user_datafiles",
}
BLENDER_COMMAND_TEMPLATE = [
    "<BLENDER_EXECUTABLE>", "--background", "--factory-startup",
    "--disable-autoexec", "<FOUNDATION_BLEND>", "--python-exit-code", "1",
    "--python", "<EXECUTION_WRAPPER>", "--", "--result-handle",
    "<INHERITED_WIN32_PIPE_HANDLE>", "--execution-contract-sha256",
    "<EXPECTED_CONTRACT_SHA256>", "--session-nonce", "<FRESH_64_HEX_NONCE>",
    "--run-number", "<ONE_OR_TWO>",
]


class LockedPairV2Error(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_file(relative: object) -> Path:
    text = str(relative or "")
    candidate = Path(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts:
        raise LockedPairV2Error(f"unsafe_project_relative_path:{text}")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise LockedPairV2Error(f"symlink_path_refused:{text}")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise LockedPairV2Error(f"path_escaped_project_root:{text}") from exc
    if not resolved.is_file():
        raise LockedPairV2Error(f"bound_path_is_not_file:{text}")
    return resolved


def _parse_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise LockedPairV2Error(f"invalid_json:{label}") from exc
    if not isinstance(value, dict):
        raise LockedPairV2Error(f"json_root_not_object:{label}")
    return value


def _untrusted_discovery() -> tuple[Path, dict[str, Any], list[Path]]:
    """Discover lock targets only; no byte count or digest is trusted here."""

    contract_path = _project_file(CONTRACT_RELATIVE_PATH)
    contract = _parse_json(contract_path, "discovery_contract")
    bindings = contract.get("bindings")
    if not isinstance(bindings, Mapping):
        raise LockedPairV2Error("discovery_binding_table_missing")
    paths: list[Path] = [contract_path]
    for label, row in bindings.items():
        if not isinstance(row, Mapping) or "path" not in row:
            raise LockedPairV2Error(f"discovery_binding_invalid:{label}")
        if label == "blender_executable":
            path = Path(str(row["path"])).resolve(strict=True)
            if not path.is_file():
                raise LockedPairV2Error("discovery_blender_not_file")
        else:
            path = _project_file(row["path"])
        paths.append(path)
    v2_config = _project_file(bindings["attempt02_config"]["path"])
    discovered_v2 = _parse_json(v2_config, "discovery_attempt02_config")
    for table_name in ("bindings", "attempt_01_preservation"):
        table = discovered_v2.get(table_name)
        if not isinstance(table, Mapping):
            raise LockedPairV2Error(f"discovery_attempt02_table_missing:{table_name}")
        for label, row in table.items():
            if not isinstance(row, Mapping) or "path" not in row:
                raise LockedPairV2Error(
                    f"discovery_attempt02_binding_invalid:{table_name}.{label}"
                )
            paths.append(_project_file(row["path"]))
    return contract_path, contract, sorted(set(paths), key=lambda value: str(value).casefold())


class WindowsReadLockSet:
    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 0x00000001
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x00000080

    def __init__(self) -> None:
        if os.name != "nt":
            raise LockedPairV2Error("locked Blender pair is Windows-only")
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        self.kernel32.CreateFileW.restype = wintypes.HANDLE
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.handles: list[int] = []
        self.locked_paths: list[Path] = []
        self.active = False

    def add(self, path: Path) -> None:
        handle = self.kernel32.CreateFileW(
            str(path), self.GENERIC_READ, self.FILE_SHARE_READ, None,
            self.OPEN_EXISTING, self.FILE_ATTRIBUTE_NORMAL, None,
        )
        invalid = ctypes.c_void_p(-1).value
        if handle in (None, invalid):
            raise LockedPairV2Error(
                f"cannot_lock_bound_input:{path}:winerror={ctypes.get_last_error()}"
            )
        self.handles.append(int(handle))
        self.locked_paths.append(path)

    def close(self) -> None:
        first_error: LockedPairV2Error | None = None
        while self.handles:
            handle = self.handles.pop()
            if not self.kernel32.CloseHandle(handle) and first_error is None:
                first_error = LockedPairV2Error(
                    f"input_lock_close_failed:winerror={ctypes.get_last_error()}"
                )
        self.active = False
        if first_error is not None:
            raise first_error

    def __enter__(self) -> "WindowsReadLockSet":
        self.active = True
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


def _with_complete_lock_set(
    paths: Iterable[Path],
    body: Callable[[Any], Any],
    *,
    lock_factory: Callable[[], Any] = WindowsReadLockSet,
) -> Any:
    """Acquire every path before invoking any verifier/import/launch body."""

    with lock_factory() as locks:
        for path in paths:
            locks.add(path)
        return body(locks)


def _exact_scope() -> dict[str, bool]:
    return {
        "body_work_only": True,
        "read_only_blender_diagnostic": True,
        "blend_mutation_allowed": False,
        "blend_save_allowed": False,
        "render_allowed": False,
        "candidate_creation_allowed": False,
        "body_authoring_allowed": False,
        "runtime_activation_allowed": False,
        "assignment_allowed": False,
        "export_allowed": False,
        "publication_allowed": False,
    }


def _verify_row_locked(label: str, row: object) -> Path:
    if not isinstance(row, Mapping) or set(row) != {"path", "bytes", "sha256"}:
        raise LockedPairV2Error(f"invalid_locked_binding:{label}")
    if type(row["bytes"]) is not int or row["bytes"] < 0:
        raise LockedPairV2Error(f"invalid_locked_binding_bytes:{label}")
    if not isinstance(row["sha256"], str) or re.fullmatch(
        r"[0-9a-f]{64}", row["sha256"]
    ) is None:
        raise LockedPairV2Error(f"invalid_locked_binding_sha256:{label}")
    if label == "blender_executable":
        path = Path(str(row["path"])).resolve(strict=True)
    else:
        path = _project_file(row["path"])
    if path.stat().st_size != row["bytes"] or _sha256_file(path) != row["sha256"]:
        raise LockedPairV2Error(f"locked_binding_drift:{label}")
    return path


def _verify_everything_under_locks(
    *, expected_contract_sha256: str, contract_path: Path, expected_locked_paths: set[Path]
) -> tuple[dict[str, Any], list[Path]]:
    if _sha256_file(contract_path) != expected_contract_sha256:
        raise LockedPairV2Error("locked_contract_hash_mismatch")
    contract = _parse_json(contract_path, "locked_contract")
    if set(contract) != {
        "schema", "attempt_id", "status", "scope", "authorization_basis",
        "bindings", "process_contract", "required_fresh_run_count",
        "pair_acceptance", "append_only_output_root", "truth_boundary",
    }:
        raise LockedPairV2Error("locked_contract_top_level_schema_drift")
    if contract["schema"] != "kira.avatar.r25.foundation_afes_locked_pair_execution.v2":
        raise LockedPairV2Error("locked_contract_schema_drift")
    if contract["attempt_id"] != "attempt_02" or contract["status"] != (
        "AUTHORIZED_READ_ONLY_DIAGNOSTIC_PAIR_ONLY"
    ):
        raise LockedPairV2Error("locked_contract_identity_drift")
    if contract["scope"] != _exact_scope():
        raise LockedPairV2Error("locked_contract_scope_drift")
    expected_authorization = {
        "owner_requested_body_progress": True,
        "owner_authorized_blender_problem_repair": True,
        "bounded_operation": (
            "extract_existing_foundation_afes_and_two_transition_rings_without_mutation"
        ),
        "does_not_authorize_candidate_or_runtime_change": True,
    }
    if contract["authorization_basis"] != expected_authorization:
        raise LockedPairV2Error("locked_authorization_basis_drift")
    expected_process = {
        "factory_startup": True,
        "background": True,
        "autoexec_disabled": True,
        "python_exit_code": 1,
        "stdin": "DEVNULL",
        "restricted_environment": True,
        "least_handle_inheritance": True,
        "result_handle_must_be_win32_pipe": True,
        "concurrent_bounded_pipe_drain": True,
        "exactly_one_frame_and_eof": True,
        "maximum_frame_bytes": MAX_FRAME_BYTES,
        "maximum_stdout_bytes": MAX_STDOUT_BYTES,
        "maximum_stderr_bytes": MAX_STDERR_BYTES,
        "fresh_64_hex_session_nonce_per_run": True,
        "process_timeout_seconds": 180,
        "terminate_only_exact_child_on_timeout": True,
        "terminate_only_exact_child_on_output_limit": True,
        "project_modules_import_only_after_locked_verification": True,
        "shell": False,
        "close_fds": True,
        "working_directory": ".",
        "environment_allowlist": list(ENVIRONMENT_ALLOWLIST),
        "forced_environment_relative_to_project": dict(FORCED_ENVIRONMENT_RELATIVE),
        "exact_command_template": list(BLENDER_COMMAND_TEMPLATE),
    }
    if contract["process_contract"] != expected_process:
        raise LockedPairV2Error("locked_process_contract_drift")
    expected_pair = {
        "distinct_session_nonces": True,
        "exact_inner_payload_match": True,
        "exact_full_normalized_topology_digest_match": True,
        "compact_afes_evidence_validation": True,
        "all_bound_inputs_locked_before_verification": True,
        "all_bound_inputs_locked_through_after_snapshot": True,
        "all_bound_inputs_unchanged_after_pair": True,
        "each_raw_frame_persisted_append_only": True,
        "canonical_outcome_for_every_post_root_exception": True,
    }
    if contract["required_fresh_run_count"] != 2 or contract["pair_acceptance"] != expected_pair:
        raise LockedPairV2Error("locked_pair_acceptance_contract_drift")
    if contract["append_only_output_root"] != OUTPUT_RELATIVE_PATH:
        raise LockedPairV2Error("locked_output_root_drift")
    expected_truth = {
        "pair_pass_would_only_satisfy_foundation_afes_plus_transition_vertex_set_audit": True,
        "semantic_cage_still_required": True,
        "positive_jacobian_and_intersection_fixtures_still_required": True,
        "body_authoring_not_granted": True,
        "candidate_not_created": True,
        "owner_review_not_implied": True,
        "runtime_authority_not_implied": True,
    }
    if contract["truth_boundary"] != expected_truth:
        raise LockedPairV2Error("locked_truth_boundary_drift")
    bindings = contract["bindings"]
    required_bindings = {
        "blender_executable", "foundation_blend", "attempt02_config",
        "attempt02_extractor", "attempt02_topology_core", "canonical_receipt",
        "execution_wrapper", "parent_controller",
    }
    if not isinstance(bindings, Mapping) or set(bindings) != required_bindings:
        raise LockedPairV2Error("locked_binding_table_drift")
    paths = [_verify_row_locked(label, row) for label, row in sorted(bindings.items())]
    controller = _project_file(bindings["parent_controller"]["path"])
    if controller != Path(__file__).resolve(strict=True):
        raise LockedPairV2Error("locked_controller_path_mismatch")
    v2_config = _project_file(bindings["attempt02_config"]["path"])
    v2 = _parse_json(v2_config, "locked_attempt02_config")
    for table_name in ("bindings", "attempt_01_preservation"):
        table = v2.get(table_name)
        if not isinstance(table, Mapping):
            raise LockedPairV2Error(f"locked_attempt02_table_missing:{table_name}")
        for label, row in sorted(table.items()):
            paths.append(_verify_row_locked(f"{table_name}.{label}", row))
    paths.append(contract_path)
    exact_paths = sorted(set(path.resolve(strict=True) for path in paths), key=lambda value: str(value).casefold())
    if set(exact_paths) != expected_locked_paths:
        raise LockedPairV2Error("locked_path_set_differs_from_verified_binding_set")
    return contract, exact_paths


def _import_locked_modules(contract: Mapping[str, Any]) -> tuple[Any, Any]:
    receipt_module = importlib.import_module("tools.kira_r25_canonical_receipt")
    topology_module = importlib.import_module("tools.kira_r25_afes_topology_core_v2")
    expected = {
        "canonical_receipt": receipt_module.__file__,
        "attempt02_topology_core": topology_module.__file__,
    }
    for label, module_path in expected.items():
        if Path(str(module_path)).resolve(strict=True) != _project_file(
            contract["bindings"][label]["path"]
        ):
            raise LockedPairV2Error(f"locked_import_path_mismatch:{label}")
    return receipt_module, topology_module


def _restricted_environment() -> dict[str, str]:
    environment = {
        name: os.environ[name]
        for name in ENVIRONMENT_ALLOWLIST
        if os.environ.get(name)
    }
    for name, value in FORCED_ENVIRONMENT_RELATIVE.items():
        environment[name] = value if name.startswith("PYTHON") else str(PROJECT_ROOT / value)
    return environment


def _drain_bounded(
    stream: Any,
    limit: int,
    result: list[object],
    overflow_event: threading.Event | None = None,
) -> None:
    digest = hashlib.sha256()
    captured = bytearray()
    total = 0
    try:
        while True:
            block = stream.read(64 * 1024)
            if not block:
                break
            total += len(block)
            digest.update(block)
            if total > limit and overflow_event is not None:
                overflow_event.set()
            remaining = max(0, limit - len(captured))
            if remaining:
                captured.extend(block[:remaining])
        result.append(
            {
                "captured": bytes(captured),
                "total_bytes": total,
                "sha256": digest.hexdigest(),
                "limit_bytes": limit,
                "overflow": total > limit,
            }
        )
    except BaseException as exc:
        result.append(exc)


def _terminate_exact_child(process: subprocess.Popen[bytes]) -> None:
    """Stop only the Popen instance created by this controller."""

    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=15)


def _wait_bounded_child(
    process: subprocess.Popen[bytes],
    *,
    timeout_seconds: int,
    overflow_event: threading.Event,
) -> str | None:
    """Wait while reacting promptly to a bounded-stream limit breach."""

    deadline = time.monotonic() + timeout_seconds
    while process.poll() is None:
        if overflow_event.wait(timeout=0.05):
            _terminate_exact_child(process)
            return "bounded_stream_limit_exceeded"
        if time.monotonic() >= deadline:
            _terminate_exact_child(process)
            return "process_timeout"
    return None


def _write_exclusive_bytes(path: Path, data: bytes) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600
    )
    try:
        view, total = memoryview(data), 0
        while total < len(view):
            written = os.write(descriptor, view[total:])
            if written <= 0:
                raise LockedPairV2Error(f"exclusive_write_failed:{path.name}")
            total += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _snapshot_under_complete_locks(
    paths: Iterable[Path], locks: Any
) -> dict[str, dict[str, object]]:
    """Hash the complete exact set only while its deny-write/delete locks live."""

    exact_paths = [Path(path).resolve(strict=True) for path in paths]
    observed_locked_paths = {
        Path(path).resolve(strict=True)
        for path in getattr(locks, "locked_paths", ())
    }
    if not getattr(locks, "active", False):
        raise LockedPairV2Error("snapshot_refused_without_active_lock_set")
    if observed_locked_paths != set(exact_paths):
        raise LockedPairV2Error("snapshot_refused_without_complete_lock_set")
    return {
        str(path): {"bytes": path.stat().st_size, "sha256": _sha256_file(path)}
        for path in exact_paths
    }


def _run_child(
    *, contract: Mapping[str, Any], contract_sha256: str, run_number: int,
    nonce: str, evidence_root: Path, receipt_module: Any, topology_module: Any,
) -> tuple[Any, dict[str, Any]]:
    if os.name != "nt":
        raise LockedPairV2Error("locked Blender pair is Windows-only")
    import msvcrt

    bindings = contract["bindings"]
    blender = Path(str(bindings["blender_executable"]["path"])).resolve(strict=True)
    foundation = _project_file(bindings["foundation_blend"]["path"])
    wrapper = _project_file(bindings["execution_wrapper"]["path"])
    read_fd, write_fd = os.pipe()
    write_handle = int(msvcrt.get_osfhandle(write_fd))
    os.set_inheritable(write_fd, True)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    startup.lpAttributeList = {"handle_list": [write_handle]}
    command = [
        str(blender), "--background", "--factory-startup", "--disable-autoexec",
        str(foundation), "--python-exit-code", "1", "--python", str(wrapper), "--",
        "--result-handle", str(write_handle),
        "--execution-contract-sha256", contract_sha256,
        "--session-nonce", nonce, "--run-number", str(run_number),
    ]
    frame_result: list[object] = []
    frame_stream = os.fdopen(read_fd, "rb", buffering=0, closefd=True)
    overflow_event = threading.Event()
    frame_thread = threading.Thread(
        target=_drain_bounded,
        args=(frame_stream, MAX_FRAME_BYTES, frame_result, overflow_event),
        daemon=True,
    )
    frame_thread.start()
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(
            command, cwd=str(PROJECT_ROOT), env=_restricted_environment(),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            startupinfo=startup, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            close_fds=True,
        )
    except BaseException:
        os.close(write_fd)
        frame_thread.join(timeout=15)
        frame_stream.close()
        raise
    else:
        os.close(write_fd)
    if process.stdout is None or process.stderr is None:
        raise LockedPairV2Error(f"run_{run_number:02d}_stdio_pipe_missing")
    stdout_result: list[object] = []
    stderr_result: list[object] = []
    stdout_thread = threading.Thread(
        target=_drain_bounded,
        args=(process.stdout, MAX_STDOUT_BYTES, stdout_result, overflow_event),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_drain_bounded,
        args=(process.stderr, MAX_STDERR_BYTES, stderr_result, overflow_event),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    termination_reason = _wait_bounded_child(
        process,
        timeout_seconds=int(contract["process_contract"]["process_timeout_seconds"]),
        overflow_event=overflow_event,
    )
    for thread in (frame_thread, stdout_thread, stderr_thread):
        thread.join(timeout=15)
    if any(thread.is_alive() for thread in (frame_thread, stdout_thread, stderr_thread)):
        raise LockedPairV2Error(f"run_{run_number:02d}_drain_thread_did_not_finish")
    for label, values in (
        ("frame", frame_result), ("stdout", stdout_result), ("stderr", stderr_result)
    ):
        if len(values) != 1 or isinstance(values[0], BaseException):
            raise LockedPairV2Error(f"run_{run_number:02d}_{label}_drain_failed")
    frame_info = frame_result[0]
    stdout_info = stdout_result[0]
    stderr_info = stderr_result[0]
    _write_exclusive_bytes(evidence_root / f"run_{run_number:02d}_stdout.log", stdout_info["captured"])
    _write_exclusive_bytes(evidence_root / f"run_{run_number:02d}_stderr.log", stderr_info["captured"])
    frame = frame_info["captured"]
    _write_exclusive_bytes(evidence_root / f"run_{run_number:02d}_raw_frame.bin", frame)
    if termination_reason == "process_timeout":
        raise LockedPairV2Error(f"run_{run_number:02d}_timed_out")
    if frame_info["overflow"]:
        raise LockedPairV2Error(f"run_{run_number:02d}_frame_limit_exceeded")
    if (
        termination_reason == "bounded_stream_limit_exceeded"
        or stdout_info["overflow"]
        or stderr_info["overflow"]
    ):
        raise LockedPairV2Error(
            f"run_{run_number:02d}_log_limit_exceeded:stdout={stdout_info['total_bytes']}:stderr={stderr_info['total_bytes']}"
        )
    if process.returncode != 0:
        raise LockedPairV2Error(f"run_{run_number:02d}_blender_exit:{process.returncode}")
    decoded = receipt_module.decode_receipt_frame(frame)
    payload = decoded.payload
    if payload.get("schema") != "kira.avatar.r25.foundation_afes_locked_extraction_run.v2":
        raise LockedPairV2Error(f"run_{run_number:02d}_schema_mismatch")
    if payload.get("status") != "READ_ONLY_EXTRACTION_COMPLETE_PENDING_PAIR_MATCH":
        raise LockedPairV2Error(f"run_{run_number:02d}_status_mismatch")
    if payload.get("session_nonce") != nonce or payload.get("run_number") != run_number:
        raise LockedPairV2Error(f"run_{run_number:02d}_session_mismatch")
    if payload.get("execution_contract", {}).get("sha256") != contract_sha256:
        raise LockedPairV2Error(f"run_{run_number:02d}_contract_mismatch")
    inner = payload.get("inner_attempt02_payload")
    if not isinstance(inner, Mapping) or inner.get("status") != (
        "EXTRACTED_UNSEALED_REQUIRES_MATCHING_FRESH_LOCKED_RUN"
    ):
        raise LockedPairV2Error(f"run_{run_number:02d}_inner_status_mismatch")
    analysis = inner.get("analysis")
    if not isinstance(analysis, Mapping):
        raise LockedPairV2Error(f"run_{run_number:02d}_analysis_missing")
    topology_module.validate_compact_afes_analysis(analysis)
    with receipt_module.WindowsExclusiveReceiptReservation.reserve(
        evidence_root / f"run_{run_number:02d}_receipt.bin"
    ) as reservation:
        reservation.accept_child_frame(frame)
    return decoded, {
        "run_number": run_number,
        "session_nonce": nonce,
        "pid": process.pid,
        "exit_code": process.returncode,
        "frame_bytes": len(frame),
        "frame_sha256": decoded.frame_sha256,
        "payload_sha256": decoded.payload_sha256,
        "inner_payload_sha256": hashlib.sha256(
            receipt_module.canonical_json_bytes(dict(inner))
        ).hexdigest(),
        "topology_sha256": analysis["topology_structure"]["full_normalized_topology_sha256"],
        "stdout_bytes": stdout_info["total_bytes"],
        "stdout_sha256": stdout_info["sha256"],
        "stderr_bytes": stderr_info["total_bytes"],
        "stderr_sha256": stderr_info["sha256"],
    }


def run_pair(expected_contract_sha256: str) -> Path:
    if not isinstance(expected_contract_sha256, str) or re.fullmatch(
        r"[0-9a-f]{64}", expected_contract_sha256
    ) is None:
        raise LockedPairV2Error("expected_contract_sha256_must_be_64_lowercase_hex")
    contract_path, _, discovered_paths = _untrusted_discovery()
    expected_set = set(path.resolve(strict=True) for path in discovered_paths)

    def locked_body(locks: Any) -> Path:
        if not getattr(locks, "active", False):
            raise LockedPairV2Error("lock_set_not_active_before_verification")
        observed_locked_paths = {
            Path(path).resolve(strict=True)
            for path in getattr(locks, "locked_paths", ())
        }
        if observed_locked_paths != expected_set:
            raise LockedPairV2Error("complete_lock_set_not_held_before_verification")
        contract, exact_paths = _verify_everything_under_locks(
            expected_contract_sha256=expected_contract_sha256,
            contract_path=contract_path,
            expected_locked_paths=expected_set,
        )
        before = _snapshot_under_complete_locks(exact_paths, locks)
        receipt_module, topology_module = _import_locked_modules(contract)
        if receipt_module.MAX_RECEIPT_FRAME_BYTES != MAX_FRAME_BYTES:
            raise LockedPairV2Error("locked_receipt_frame_limit_drift")
        output_root = (PROJECT_ROOT / OUTPUT_RELATIVE_PATH).resolve()
        output_root.relative_to(PROJECT_ROOT.resolve(strict=True))
        output_root.mkdir(parents=True, exist_ok=False)
        outcome = receipt_module.WindowsExclusiveReceiptReservation.reserve(
            output_root / "CONTROLLER_OUTCOME.receipt.bin"
        )
        stage = "post_root_reservation"
        try:
            decoded_runs: list[Any] = []
            run_metadata: list[dict[str, Any]] = []
            stage = "children"
            for run_number in (1, 2):
                decoded, metadata = _run_child(
                    contract=contract,
                    contract_sha256=expected_contract_sha256,
                    run_number=run_number,
                    nonce=secrets.token_hex(32),
                    evidence_root=output_root,
                    receipt_module=receipt_module,
                    topology_module=topology_module,
                )
                decoded_runs.append(decoded)
                run_metadata.append(metadata)
            stage = "pair_comparison"
            if run_metadata[0]["session_nonce"] == run_metadata[1]["session_nonce"]:
                raise LockedPairV2Error("fresh_run_nonces_not_distinct")
            first_inner = decoded_runs[0].payload["inner_attempt02_payload"]
            second_inner = decoded_runs[1].payload["inner_attempt02_payload"]
            if first_inner != second_inner:
                raise LockedPairV2Error("fresh_locked_inner_payloads_do_not_match")
            if run_metadata[0]["topology_sha256"] != run_metadata[1]["topology_sha256"]:
                raise LockedPairV2Error("fresh_locked_topology_digests_do_not_match")
            stage = "locked_after_snapshot"
            after = _snapshot_under_complete_locks(exact_paths, locks)
            if before != after:
                raise LockedPairV2Error("bound_input_changed_while_locks_held")
            summary = {
                "schema": "kira.avatar.r25.foundation_afes_locked_pair_acceptance.v2",
                "status": "AFES_AND_TRANSITION_RINGS_EXTRACTED_READ_ONLY_PAIR_MATCHED",
                "execution_contract_sha256": expected_contract_sha256,
                "execution_contract_bytes": contract_path.stat().st_size,
                "bound_inputs_unchanged_under_locks": True,
                "input_snapshot_sha256": hashlib.sha256(
                    receipt_module.canonical_json_bytes(before)
                ).hexdigest(),
                "runs": run_metadata,
                "matching_inner_payload_sha256": run_metadata[0]["inner_payload_sha256"],
                "full_normalized_topology_sha256": run_metadata[0]["topology_sha256"],
                "truth_boundary": [
                    "READ_ONLY_DIAGNOSTIC_PAIR_ONLY",
                    "NO_BLEND_MUTATION_OR_SAVE",
                    "NO_BODY_CANDIDATE",
                    "NO_AUTHORING_OR_RUNTIME_AUTHORITY",
                ],
            }
            outcome.accept_child_frame(receipt_module.encode_receipt_frame(summary))
            outcome.close()
            return output_root
        except BaseException as exc:
            failure = {
                "schema": "kira.avatar.r25.foundation_afes_locked_pair_failure.v2",
                "status": "FAILED_APPEND_ONLY_NO_BODY_AUTHORITY",
                "stage": stage,
                "failure_type": type(exc).__name__,
                "failure": str(exc),
                "execution_contract_sha256": expected_contract_sha256,
            }
            try:
                outcome.accept_child_frame(receipt_module.encode_receipt_frame(failure))
            finally:
                outcome.close()
            raise

    return _with_complete_lock_set(discovered_paths, locked_body)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-contract-sha256", required=True)
    return parser.parse_args()


def main() -> int:
    values = _arguments()
    try:
        output = run_pair(values.expected_contract_sha256)
    except Exception as exc:
        print(f"R25_AFES_LOCKED_PAIR_V2_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(output.relative_to(PROJECT_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
