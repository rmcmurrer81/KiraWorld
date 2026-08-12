#!/usr/bin/env python3
"""Locked-body implementation for R25 AFES pair Attempt 04.

This source is not a direct entry point.  The small external Attempt-04
launcher must first lock and retain the complete declared graph, verify the
structured independent-audit artifact, compile these exact retained bytes in
a private module, and then call :func:`run_locked_pair`.
"""

from __future__ import annotations

import builtins
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time
from types import ModuleType
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v4.json"
)
OUTPUT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution/attempt_04"
)
MAX_FRAME_BYTES = 1_048_628
MAX_STDOUT_BYTES = 4 * 1024 * 1024
MAX_STDERR_BYTES = 4 * 1024 * 1024
HEX64 = re.compile(r"[0-9a-f]{64}")
FILE_TYPE_PIPE = 3
PASSTHROUGH_IF_PRESENT = (
    "SYSTEMROOT", "WINDIR", "USERNAME", "USERPROFILE", "HOMEDRIVE",
    "HOMEPATH", "LOCALAPPDATA", "APPDATA",
)
CONTROLLED_RUNTIME_DIRS = {
    "TEMP": "RecoverySprint/runtime_cache/r25_blender_v4/temp",
    "TMP": "RecoverySprint/runtime_cache/r25_blender_v4/temp",
    "BLENDER_USER_CONFIG": "RecoverySprint/runtime_cache/r25_blender_v4/user_config",
    "BLENDER_USER_SCRIPTS": "RecoverySprint/runtime_cache/r25_blender_v4/user_scripts",
    "BLENDER_USER_DATAFILES": "RecoverySprint/runtime_cache/r25_blender_v4/user_datafiles",
}
FORCED_ENVIRONMENT = {
    "PYTHONNOUSERSITE": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
}
OUTER_TRUTH_BOUNDARY = [
    "READ_ONLY_FOUNDATION_DIAGNOSTIC",
    "NO_BLEND_MUTATION_OR_SAVE",
    "NO_RENDER_OR_EXPORT",
    "NO_CANDIDATE_OR_BODY_AUTHORING",
    "THIS_SINGLE_RUN_IS_NOT_ACCEPTANCE",
]


class LockedPairV4Error(RuntimeError):
    """A locked Attempt-04 execution gate failed closed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def _exact_typed_equal(observed: object, expected: object) -> bool:
    if type(observed) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(observed) == set(expected) and all(
            _exact_typed_equal(observed[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(observed) == len(expected) and all(
            _exact_typed_equal(left, right) for left, right in zip(observed, expected)
        )
    return observed == expected


def _project_file(relative: object) -> Path:
    text = str(relative or "")
    candidate = Path(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts:
        raise LockedPairV4Error(f"unsafe_project_relative_path:{text}")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise LockedPairV4Error(f"symlink_path_refused:{text}")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise LockedPairV4Error(f"path_escaped_project_root:{text}") from exc
    if not resolved.is_file():
        raise LockedPairV4Error(f"project_input_not_file:{text}")
    return resolved


def _parse_json_bytes(value: bytes, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value.decode("utf-8-sig"))
    except Exception as exc:
        raise LockedPairV4Error(f"invalid_json:{label}") from exc
    if not isinstance(parsed, dict):
        raise LockedPairV4Error(f"json_root_not_object:{label}")
    return parsed


def _load_private_parent_graph(
    contract: Mapping[str, Any], ledger: Any, pair_session_nonce: str,
) -> tuple[ModuleType, ModuleType, dict[str, Any]]:
    closure = contract["child_project_read_closure"]
    _, v5_bytes = ledger.read_exact(closure["afes_v5_config"], label="afes_v5_config")
    v5 = _parse_json_bytes(v5_bytes, "afes_v5_config")
    loader_row = v5["bindings"]["attempt_05_private_loader_core"]
    path, source = ledger.read_exact(loader_row, label="afes_v5_private_loader")
    real_import = builtins.__import__

    def guarded_import(
        name: str, globals: object = None, locals: object = None,
        fromlist: Sequence[str] = (), level: int = 0,
    ) -> object:
        if name == "tools" or name.startswith("tools.") or name == "dataclasses":
            raise LockedPairV4Error(f"ambient_security_import_forbidden:{name}")
        return real_import(name, globals, locals, fromlist, level)

    private = ModuleType(f"_kira_private_afes_v5_parent_{pair_session_nonce}")
    private.__file__ = str(path)
    private.__package__ = ""
    private.__spec__ = None
    private.__loader__ = None
    private_builtins = dict(vars(builtins))
    private_builtins["__import__"] = guarded_import
    private.__dict__["__builtins__"] = private_builtins
    try:
        exec(compile(source, str(path), "exec", dont_inherit=True), private.__dict__, private.__dict__)
    except Exception as exc:
        raise LockedPairV4Error(
            f"private_v5_loader_execution_failed:{type(exc).__name__}:{exc}"
        ) from exc
    if any(private is module for module in sys.modules.values()):
        raise LockedPairV4Error("private_v5_loader_entered_sys_modules")
    loader = getattr(private, "load_private_dependency_graph", None)
    if not callable(loader):
        raise LockedPairV4Error("private_v5_loader_symbol_missing")
    graph_rows = {
        key: v5["bindings"][key] for key in (
            "attempt_01_topology_core_execution_dependency",
            "attempt_02_hardening_core_execution_dependency",
            "attempt_03_hardening_core_execution_dependency",
            "canonical_receipt_helper",
        )
    }
    try:
        graph = loader(bindings=graph_rows, read_exact=ledger.read_exact)
    except Exception as exc:
        raise LockedPairV4Error(
            f"private_dependency_graph_failed:{type(exc).__name__}:{exc}"
        ) from exc
    receipt = graph.get("canonical_receipt")
    attempt03 = graph.get("attempt03_core")
    if not isinstance(receipt, ModuleType) or not isinstance(attempt03, ModuleType):
        raise LockedPairV4Error("private_parent_graph_shape_drift")
    if any(receipt is module or attempt03 is module for module in sys.modules.values()):
        raise LockedPairV4Error("private_parent_graph_entered_sys_modules")
    if getattr(receipt, "MAX_RECEIPT_FRAME_BYTES", None) != MAX_FRAME_BYTES:
        raise LockedPairV4Error("private_receipt_limit_drift")
    if not callable(getattr(attempt03, "validate_compact_afes_analysis", None)):
        raise LockedPairV4Error("private_analysis_validator_missing")
    return receipt, attempt03, v5


def _load_v2_config(v5: Mapping[str, Any], ledger: Any) -> dict[str, Any]:
    _, v4_bytes = ledger.read_exact(v5["attempt_04_baseline_config"], label="v4_config")
    v4 = _parse_json_bytes(v4_bytes, "v4_config")
    _, v3_bytes = ledger.read_exact(v4["attempt_03_baseline_config"], label="v3_config")
    v3 = _parse_json_bytes(v3_bytes, "v3_config")
    _, v2_bytes = ledger.read_exact(v3["attempt_02_baseline_config"], label="v2_config")
    return _parse_json_bytes(v2_bytes, "v2_config")


def _restricted_environment(blender: Path) -> dict[str, str]:
    environment = {
        name: os.environ[name]
        for name in PASSTHROUGH_IF_PRESENT
        if os.environ.get(name)
    }
    windir = environment.get("WINDIR") or environment.get("SYSTEMROOT")
    if not windir:
        raise LockedPairV4Error("windows_root_environment_missing")
    environment["Path"] = os.pathsep.join(
        (str(blender.parent), str(Path(windir) / "System32"), str(Path(windir)))
    )
    environment.update(FORCED_ENVIRONMENT)
    for name, relative in CONTROLLED_RUNTIME_DIRS.items():
        path = (PROJECT_ROOT / relative).resolve()
        try:
            path.relative_to(PROJECT_ROOT.resolve(strict=True))
        except ValueError as exc:
            raise LockedPairV4Error(f"controlled_runtime_path_escaped:{name}") from exc
        path.mkdir(parents=True, exist_ok=True)
        environment[name] = str(path)
    return environment


def _environment_observation(environment: Mapping[str, str]) -> dict[str, object]:
    names = sorted(environment, key=str.casefold)
    return {
        "names": names,
        "sha256": _sha256_bytes(_canonical_json_bytes({name: environment[name] for name in names})),
    }


def _require_pipe_handle(raw_handle: int) -> None:
    if os.name != "nt" or type(raw_handle) is not int or raw_handle <= 0:
        raise LockedPairV4Error("result_handle_invalid")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetFileType.argtypes = [ctypes.c_void_p]
    kernel32.GetFileType.restype = ctypes.c_uint32
    if int(kernel32.GetFileType(ctypes.c_void_p(raw_handle))) != FILE_TYPE_PIPE:
        raise LockedPairV4Error("result_handle_is_not_pipe")


def _drain_bounded(
    stream: Any, limit: int, result: list[object], overflow_event: threading.Event,
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
            if total > limit:
                overflow_event.set()
            remaining = max(0, limit - len(captured))
            if remaining:
                captured.extend(block[:remaining])
        result.append({
            "captured": bytes(captured), "total_bytes": total,
            "sha256": digest.hexdigest(), "limit_bytes": limit,
            "overflow": total > limit,
        })
    except BaseException as exc:
        result.append(exc)
        overflow_event.set()


class _JobIoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
    )]


class _JobBasicLimit(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _JobExtendedLimit(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JobBasicLimit),
        ("IoInfo", _JobIoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class WindowsKillOnCloseJob:
    """Contain exactly one controller-created Blender process tree."""

    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    JobObjectExtendedLimitInformation = 9

    def __init__(self) -> None:
        if os.name != "nt":
            raise LockedPairV4Error("job_containment_is_windows_only")
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
        self.kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        self.kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ]
        self.kernel32.SetInformationJobObject.restype = wintypes.BOOL
        self.kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        self.kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.kernel32.TerminateJobObject.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
        self.ntdll.NtResumeProcess.restype = ctypes.c_long
        self.handle = self.kernel32.CreateJobObjectW(None, None)
        if not self.handle:
            raise LockedPairV4Error(f"job_create_failed:{ctypes.get_last_error()}")
        info = _JobExtendedLimit()
        info.BasicLimitInformation.LimitFlags = self.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel32.SetInformationJobObject(
            self.handle, self.JobObjectExtendedLimitInformation,
            ctypes.byref(info), ctypes.sizeof(info),
        ):
            error = ctypes.get_last_error()
            self.kernel32.CloseHandle(self.handle)
            raise LockedPairV4Error(f"job_limit_failed:{error}")
        self.closed = False
        self.assigned_pid: int | None = None

    def assign(self, process: subprocess.Popen[bytes]) -> None:
        process_handle = int(process._handle)  # type: ignore[attr-defined]
        if not self.kernel32.AssignProcessToJobObject(self.handle, process_handle):
            raise LockedPairV4Error(f"job_assignment_failed:{ctypes.get_last_error()}")
        self.assigned_pid = process.pid

    def resume(self, process: subprocess.Popen[bytes]) -> None:
        if self.assigned_pid != process.pid:
            raise LockedPairV4Error("resume_before_exact_job_assignment")
        status = int(self.ntdll.NtResumeProcess(int(process._handle)))  # type: ignore[attr-defined]
        if status < 0:
            raise LockedPairV4Error(f"suspended_process_resume_failed:{status}")

    def terminate_tree(self) -> None:
        if not self.closed and not self.kernel32.TerminateJobObject(self.handle, 1):
            raise LockedPairV4Error(f"job_termination_failed:{ctypes.get_last_error()}")

    def close(self) -> None:
        if self.closed:
            return
        if not self.kernel32.CloseHandle(self.handle):
            raise LockedPairV4Error(f"job_close_failed:{ctypes.get_last_error()}")
        self.closed = True


def _terminate_exact_job_process(
    process: subprocess.Popen[bytes] | None, job: WindowsKillOnCloseJob | None,
) -> None:
    """Best-effort cleanup restricted to this call's exact process/job."""

    if process is None or process.poll() is not None:
        return
    if job is not None and job.assigned_pid == process.pid and not job.closed:
        job.terminate_tree()
    else:
        process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        if job is not None and job.assigned_pid == process.pid and not job.closed:
            job.close()
        else:
            process.kill()
        process.wait(timeout=15)


def _close_job_exception_safe(job: WindowsKillOnCloseJob | None) -> None:
    if job is not None and not job.closed:
        job.close()


def _wait_bounded_child(
    process: subprocess.Popen[bytes], job: WindowsKillOnCloseJob,
    *, timeout_seconds: int, overflow_event: threading.Event,
) -> str | None:
    deadline = time.monotonic() + timeout_seconds
    while process.poll() is None:
        if overflow_event.wait(timeout=0.05):
            _terminate_exact_job_process(process, job)
            return "bounded_stream_limit_exceeded"
        if time.monotonic() >= deadline:
            _terminate_exact_job_process(process, job)
            return "process_timeout"
    return None


def _write_exclusive_bytes(path: Path, data: bytes) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600
    )
    try:
        view = memoryview(data)
        offset = 0
        while offset < len(view):
            written = os.write(descriptor, view[offset:])
            if written <= 0:
                raise LockedPairV4Error(f"exclusive_write_failed:{path.name}")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _validate_exact_child_payload(
    *, payload: object, contract: Mapping[str, Any], v5: Mapping[str, Any],
    v2: Mapping[str, Any], attempt03: ModuleType,
    contract_sha256: str, contract_bytes: int,
    run_number: int, pair_session_nonce: str, run_nonce: str,
    result_handle: int, child_pid: int, parent_pid: int,
    environment_observation: Mapping[str, object],
) -> tuple[Mapping[str, Any], str]:
    outer_keys = {
        "schema", "status", "execution_contract", "accepted_afes_v5_config",
        "accepted_afes_v5_extractor", "pair_session_nonce", "run_nonce",
        "run_number", "result_pipe_handle", "child_pid", "parent_pid",
        "environment_observation", "inner_attempt05_payload", "truth_boundary",
    }
    if not isinstance(payload, Mapping) or set(payload) != outer_keys:
        raise LockedPairV4Error(f"run_{run_number:02d}_outer_schema_shape_mismatch")
    if payload["schema"] != "kira.avatar.r25.foundation_afes_locked_extraction_run.v4":
        raise LockedPairV4Error(f"run_{run_number:02d}_outer_schema_mismatch")
    if payload["status"] != "READ_ONLY_EXTRACTION_COMPLETE_PENDING_PAIR_MATCH":
        raise LockedPairV4Error(f"run_{run_number:02d}_outer_status_mismatch")
    expected_contract_row = {
        "path": CONTRACT_RELATIVE_PATH,
        "bytes": contract_bytes,
        "sha256": contract_sha256,
    }
    if not _exact_typed_equal(payload["execution_contract"], expected_contract_row):
        raise LockedPairV4Error(f"run_{run_number:02d}_execution_contract_mismatch")
    closure = contract["child_project_read_closure"]
    if not _exact_typed_equal(payload["accepted_afes_v5_config"], closure["afes_v5_config"]):
        raise LockedPairV4Error(f"run_{run_number:02d}_accepted_config_mismatch")
    if not _exact_typed_equal(payload["accepted_afes_v5_extractor"], closure["afes_v5_extractor"]):
        raise LockedPairV4Error(f"run_{run_number:02d}_accepted_extractor_mismatch")
    exact_identity = (
        payload["pair_session_nonce"] == pair_session_nonce,
        payload["run_nonce"] == run_nonce,
        type(payload["run_number"]) is int and payload["run_number"] == run_number,
        type(payload["result_pipe_handle"]) is int and payload["result_pipe_handle"] == result_handle,
        type(payload["child_pid"]) is int and payload["child_pid"] == child_pid,
        type(payload["parent_pid"]) is int and payload["parent_pid"] == parent_pid,
    )
    if not all(exact_identity):
        raise LockedPairV4Error(f"run_{run_number:02d}_authenticated_identity_mismatch")
    if not _exact_typed_equal(payload["environment_observation"], dict(environment_observation)):
        raise LockedPairV4Error(f"run_{run_number:02d}_environment_mismatch")
    if not _exact_typed_equal(payload["truth_boundary"], OUTER_TRUTH_BOUNDARY):
        raise LockedPairV4Error(f"run_{run_number:02d}_outer_truth_boundary_mismatch")

    inner = payload["inner_attempt05_payload"]
    inner_keys = {
        "schema", "artifact_kind", "status", "config_observed_unsealed_by_parent",
        "private_execution_dependencies", "private_source_physical_reads",
        "ambient_project_modules_consumed", "ambient_dataclasses_decorator_consumed",
        "private_modules_inserted_into_sys_modules", "private_receipt_runtime",
        "foundation_object", "foundation_mesh", "analysis", "topology_sealing",
        "read_only_guards", "truth_boundary",
    }
    if not isinstance(inner, Mapping) or set(inner) != inner_keys:
        raise LockedPairV4Error(f"run_{run_number:02d}_inner_schema_shape_mismatch")
    if inner["schema"] != "kira.avatar.r25.foundation_afes_transition_diagnostic.v5":
        raise LockedPairV4Error(f"run_{run_number:02d}_inner_schema_mismatch")
    if inner["artifact_kind"] != "READ_ONLY_PRIVATE_EXACT_BYTE_AFES_DIAGNOSTIC":
        raise LockedPairV4Error(f"run_{run_number:02d}_inner_kind_mismatch")
    if inner["status"] != "EXTRACTED_UNSEALED_REQUIRES_MATCHING_FRESH_LOCKED_RUN":
        raise LockedPairV4Error(f"run_{run_number:02d}_inner_status_mismatch")
    if not _exact_typed_equal(inner["config_observed_unsealed_by_parent"], closure["afes_v5_config"]):
        raise LockedPairV4Error(f"run_{run_number:02d}_inner_config_mismatch")
    graph_keys = (
        "attempt_01_topology_core_execution_dependency",
        "attempt_02_hardening_core_execution_dependency",
        "attempt_03_hardening_core_execution_dependency",
        "canonical_receipt_helper",
    )
    graph_rows = {key: v5["bindings"][key] for key in graph_keys}
    if not _exact_typed_equal(inner["private_execution_dependencies"], graph_rows):
        raise LockedPairV4Error(f"run_{run_number:02d}_private_graph_mismatch")
    source_keys = (
        "attempt_05_private_loader_core", *graph_keys, "attempt_05_extractor",
    )
    expected_reads = [
        {
            "path": str(v5["bindings"][key]["path"]),
            "physical_read_count": 1,
            "bytes": v5["bindings"][key]["bytes"],
            "sha256": v5["bindings"][key]["sha256"],
        }
        for key in source_keys
    ]
    expected_reads.sort(key=lambda row: str(row["path"]))
    if not _exact_typed_equal(inner["private_source_physical_reads"], expected_reads):
        raise LockedPairV4Error(f"run_{run_number:02d}_private_read_evidence_mismatch")
    if (
        type(inner["ambient_project_modules_consumed"]) is not int
        or inner["ambient_project_modules_consumed"] != 0
        or type(inner["ambient_dataclasses_decorator_consumed"]) is not int
        or inner["ambient_dataclasses_decorator_consumed"] != 0
        or type(inner["private_modules_inserted_into_sys_modules"]) is not int
        or inner["private_modules_inserted_into_sys_modules"] != 0
    ):
        raise LockedPairV4Error(f"run_{run_number:02d}_private_execution_truth_mismatch")
    if not _exact_typed_equal(inner["private_receipt_runtime"], {
        "receipt_module_name": "_kira_private_canonical_receipt_attempt05",
        "decoded_receipt_class_module": "_kira_private_canonical_receipt_attempt05",
        "dataclass_shim_module_name": "_kira_private_dataclass_shim_attempt05",
        "receipt_or_shim_aliases_ambient_sys_modules": False,
    }):
        raise LockedPairV4Error(f"run_{run_number:02d}_private_receipt_runtime_mismatch")
    foundation = v2["foundation_contract"]
    if inner["foundation_object"] != foundation["object_name"] or inner[
        "foundation_mesh"
    ] != foundation["mesh_name"]:
        raise LockedPairV4Error(f"run_{run_number:02d}_foundation_identity_mismatch")
    analysis = inner["analysis"]
    if not isinstance(analysis, Mapping):
        raise LockedPairV4Error(f"run_{run_number:02d}_analysis_not_object")
    attempt03.validate_compact_afes_analysis(analysis)
    topology = analysis["topology_structure"]["full_normalized_topology_sha256"]
    if not isinstance(topology, str) or HEX64.fullmatch(topology) is None:
        raise LockedPairV4Error(f"run_{run_number:02d}_topology_digest_invalid")
    if not _exact_typed_equal(inner["topology_sealing"], {
        "prior_sealed_expected_full_normalized_topology_digest_available": False,
        "required_matching_fresh_locked_extractions": 2,
        "this_receipt_alone_is_acceptance": False,
        "measured_full_normalized_topology_sha256": topology,
    }):
        raise LockedPairV4Error(f"run_{run_number:02d}_topology_sealing_mismatch")
    if not _exact_typed_equal(inner["read_only_guards"], {
        "blend_loaded_exactly": True,
        "blend_clean_before": True,
        "blend_clean_after": True,
        "data_block_inventory_unchanged": True,
        "operator_calls_by_this_extractor": 0,
        "edit_calls_by_this_extractor": 0,
        "persistence_calls_by_this_extractor": 0,
        "path_result_writes_by_this_extractor": 0,
    }):
        raise LockedPairV4Error(f"run_{run_number:02d}_read_only_guards_mismatch")
    if not _exact_typed_equal(inner["truth_boundary"], v5["truth_boundary"]):
        raise LockedPairV4Error(f"run_{run_number:02d}_inner_truth_boundary_mismatch")
    return inner, topology


def _run_child(
    *, contract: Mapping[str, Any], v5: Mapping[str, Any], v2: Mapping[str, Any],
    ledger: Any, receipt: ModuleType, attempt03: ModuleType,
    contract_sha256: str, contract_bytes: int,
    run_number: int, pair_session_nonce: str, run_nonce: str,
    evidence_root: Path,
) -> tuple[Any, dict[str, Any]]:
    if os.name != "nt":
        raise LockedPairV4Error("locked_blender_pair_is_windows_only")
    import msvcrt

    sources = contract["execution_sources"]
    blender = Path(str(sources["blender_executable"]["path"])).resolve(strict=True)
    foundation = _project_file(contract["child_project_read_closure"]["foundation_blend"]["path"])
    wrapper = _project_file(sources["child_wrapper"]["path"])
    environment = _restricted_environment(blender)
    environment_observation = _environment_observation(environment)
    read_fd, write_fd = os.pipe()
    write_fd_open = True
    frame_stream = os.fdopen(read_fd, "rb", buffering=0, closefd=True)
    frame_result: list[object] = []
    stdout_result: list[object] = []
    stderr_result: list[object] = []
    overflow_event = threading.Event()
    frame_thread = threading.Thread(
        target=_drain_bounded,
        args=(frame_stream, MAX_FRAME_BYTES, frame_result, overflow_event),
        daemon=True,
    )
    stdout_thread: threading.Thread | None = None
    stderr_thread: threading.Thread | None = None
    started_threads: list[threading.Thread] = []
    process: subprocess.Popen[bytes] | None = None
    job: WindowsKillOnCloseJob | None = None
    termination_reason: str | None = None
    write_handle = int(msvcrt.get_osfhandle(write_fd))
    try:
        _require_pipe_handle(write_handle)
        os.set_inheritable(write_fd, True)
    except BaseException:
        os.close(write_fd)
        write_fd_open = False
        frame_stream.close()
        raise
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    startup.lpAttributeList = {"handle_list": [write_handle]}
    command = [
        str(blender), "--background", "--factory-startup", "--disable-autoexec",
        str(foundation), "--python-exit-code", "1", "--python", str(wrapper), "--",
        "--result-handle", str(write_handle),
        "--execution-contract-sha256", contract_sha256,
        "--pair-session-nonce", pair_session_nonce,
        "--run-nonce", run_nonce,
        "--run-number", str(run_number),
    ]
    try:
        frame_thread.start()
        started_threads.append(frame_thread)
        job = WindowsKillOnCloseJob()
        process = subprocess.Popen(
            command, cwd=str(PROJECT_ROOT), env=environment,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            startupinfo=startup,
            creationflags=(
                getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "CREATE_SUSPENDED", 0x00000004)
            ),
            close_fds=True, shell=False,
        )
        job.assign(process)
        if process.stdout is None or process.stderr is None:
            raise LockedPairV4Error(f"run_{run_number:02d}_stdio_pipe_missing")
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
        started_threads.append(stdout_thread)
        stderr_thread.start()
        started_threads.append(stderr_thread)
        job.resume(process)
        os.close(write_fd)
        write_fd_open = False
        termination_reason = _wait_bounded_child(
            process, job,
            timeout_seconds=int(contract["process_contract"]["process_timeout_seconds"]),
            overflow_event=overflow_event,
        )
    finally:
        if write_fd_open:
            try:
                os.close(write_fd)
            except OSError:
                pass
            write_fd_open = False
        try:
            _terminate_exact_job_process(process, job)
        finally:
            for thread in started_threads:
                thread.join(timeout=15)
            try:
                frame_stream.close()
            except Exception:
                pass
            _close_job_exception_safe(job)

    if any(thread.is_alive() for thread in started_threads):
        raise LockedPairV4Error(f"run_{run_number:02d}_drain_thread_did_not_finish")
    for label, values in (
        ("frame", frame_result), ("stdout", stdout_result), ("stderr", stderr_result)
    ):
        if len(values) != 1 or isinstance(values[0], BaseException):
            raise LockedPairV4Error(f"run_{run_number:02d}_{label}_drain_failed")
    frame_info = frame_result[0]
    stdout_info = stdout_result[0]
    stderr_info = stderr_result[0]
    _write_exclusive_bytes(
        evidence_root / f"run_{run_number:02d}_stdout.log", stdout_info["captured"]
    )
    _write_exclusive_bytes(
        evidence_root / f"run_{run_number:02d}_stderr.log", stderr_info["captured"]
    )
    frame = frame_info["captured"]
    _write_exclusive_bytes(evidence_root / f"run_{run_number:02d}_raw_frame.bin", frame)
    if termination_reason == "process_timeout":
        raise LockedPairV4Error(f"run_{run_number:02d}_timed_out")
    if frame_info["overflow"]:
        raise LockedPairV4Error(f"run_{run_number:02d}_frame_limit_exceeded")
    if termination_reason == "bounded_stream_limit_exceeded" or stdout_info[
        "overflow"
    ] or stderr_info["overflow"]:
        raise LockedPairV4Error(f"run_{run_number:02d}_bounded_stream_limit_exceeded")
    if process is None or process.returncode != 0:
        code = None if process is None else process.returncode
        raise LockedPairV4Error(f"run_{run_number:02d}_blender_exit:{code}")
    decoded = receipt.decode_receipt_frame(frame)
    inner, topology_sha256 = _validate_exact_child_payload(
        payload=decoded.payload, contract=contract, v5=v5, v2=v2,
        attempt03=attempt03, contract_sha256=contract_sha256,
        contract_bytes=contract_bytes, run_number=run_number,
        pair_session_nonce=pair_session_nonce, run_nonce=run_nonce,
        result_handle=write_handle, child_pid=process.pid, parent_pid=os.getpid(),
        environment_observation=environment_observation,
    )
    with receipt.WindowsExclusiveReceiptReservation.reserve(
        evidence_root / f"run_{run_number:02d}_receipt.bin"
    ) as reservation:
        reservation.accept_child_frame(frame)
    return decoded, {
        "run_number": run_number,
        "pair_session_nonce": pair_session_nonce,
        "run_nonce": run_nonce,
        "pid": process.pid,
        "parent_pid": os.getpid(),
        "result_pipe_handle": write_handle,
        "exit_code": process.returncode,
        "frame_bytes": len(frame),
        "frame_sha256": decoded.frame_sha256,
        "payload_sha256": decoded.payload_sha256,
        "inner_payload_sha256": _sha256_bytes(receipt.canonical_json_bytes(dict(inner))),
        "topology_sha256": topology_sha256,
        "stdout_bytes": stdout_info["total_bytes"],
        "stdout_sha256": stdout_info["sha256"],
        "stderr_bytes": stderr_info["total_bytes"],
        "stderr_sha256": stderr_info["sha256"],
        "environment_observation": environment_observation,
        "process_tree_containment": "WINDOWS_JOB_KILL_ON_CLOSE",
    }


def _snapshot_under_locks(context: Any) -> dict[str, dict[str, object]]:
    if not getattr(context, "locks_active", False):
        raise LockedPairV4Error("after_snapshot_refused_without_active_locks")
    return context.snapshot_locked_files()


def _reserve_outcome(output_root: Path, receipt: ModuleType) -> Any:
    output_root.mkdir(parents=False, exist_ok=False)
    try:
        return receipt.WindowsExclusiveReceiptReservation.reserve(
            output_root / "CONTROLLER_OUTCOME.receipt.bin"
        )
    except BaseException:
        try:
            output_root.rmdir()
        except OSError:
            pass
        raise


def run_locked_pair(
    *, bootstrap_context: Any, expected_contract_sha256: str,
    accepted_audit_sha256: str,
) -> Path:
    """Run exactly two children using the launcher's still-active lock/ledger."""

    if not getattr(bootstrap_context, "locks_active", False):
        raise LockedPairV4Error("external_bootstrap_locks_not_active")
    if getattr(bootstrap_context, "controller_private_execution", None) is not True:
        raise LockedPairV4Error("controller_not_private_retained_byte_execution")
    if bootstrap_context.expected_contract_sha256 != expected_contract_sha256:
        raise LockedPairV4Error("bootstrap_contract_digest_mismatch")
    if bootstrap_context.accepted_audit_sha256 != accepted_audit_sha256:
        raise LockedPairV4Error("bootstrap_audit_digest_mismatch")
    if HEX64.fullmatch(expected_contract_sha256) is None or HEX64.fullmatch(
        accepted_audit_sha256
    ) is None:
        raise LockedPairV4Error("out_of_band_digest_invalid")
    contract = bootstrap_context.contract
    if contract["schema"] != "kira.avatar.r25.foundation_afes_locked_pair_execution.v4":
        raise LockedPairV4Error("bootstrap_contract_schema_mismatch")
    ledger = bootstrap_context.ledger
    contract_bytes = ledger.read_path(bootstrap_context.contract_path)
    if _sha256_bytes(contract_bytes) != expected_contract_sha256:
        raise LockedPairV4Error("retained_contract_digest_mismatch")
    pair_session_nonce = secrets.token_hex(32)
    receipt, attempt03, v5 = _load_private_parent_graph(
        contract, ledger, pair_session_nonce
    )
    v2 = _load_v2_config(v5, ledger)
    before = bootstrap_context.before_snapshot
    if before != bootstrap_context.snapshot_locked_files():
        raise LockedPairV4Error("locked_graph_changed_before_pair")
    output_root = (PROJECT_ROOT / OUTPUT_RELATIVE_PATH).resolve()
    output_root.relative_to(PROJECT_ROOT.resolve(strict=True))
    output_root.parent.mkdir(parents=True, exist_ok=True)
    outcome = _reserve_outcome(output_root, receipt)
    stage = "post_outcome_reservation"
    try:
        run_nonces = [secrets.token_hex(32), secrets.token_hex(32)]
        if len({pair_session_nonce, *run_nonces}) != 3:
            raise LockedPairV4Error("fresh_nonce_collision")
        decoded_runs: list[Any] = []
        run_metadata: list[dict[str, Any]] = []
        stage = "children"
        for run_number, run_nonce in enumerate(run_nonces, 1):
            decoded, metadata = _run_child(
                contract=contract, v5=v5, v2=v2, ledger=ledger,
                receipt=receipt, attempt03=attempt03,
                contract_sha256=expected_contract_sha256,
                contract_bytes=len(contract_bytes), run_number=run_number,
                pair_session_nonce=pair_session_nonce, run_nonce=run_nonce,
                evidence_root=output_root,
            )
            decoded_runs.append(decoded)
            run_metadata.append(metadata)
        stage = "pair_comparison"
        first_inner = decoded_runs[0].payload["inner_attempt05_payload"]
        second_inner = decoded_runs[1].payload["inner_attempt05_payload"]
        if first_inner != second_inner:
            raise LockedPairV4Error("fresh_locked_inner_payloads_do_not_match")
        if run_metadata[0]["inner_payload_sha256"] != run_metadata[1]["inner_payload_sha256"]:
            raise LockedPairV4Error("fresh_locked_inner_digests_do_not_match")
        if run_metadata[0]["topology_sha256"] != run_metadata[1]["topology_sha256"]:
            raise LockedPairV4Error("fresh_locked_topology_digests_do_not_match")
        stage = "locked_after_snapshot"
        after = _snapshot_under_locks(bootstrap_context)
        if before != after:
            raise LockedPairV4Error("locked_input_changed_during_pair")
        summary = {
            "schema": "kira.avatar.r25.foundation_afes_locked_pair_acceptance.v4",
            "status": "AFES_AND_TRANSITION_RINGS_EXTRACTED_READ_ONLY_PAIR_MATCHED",
            "execution_contract_sha256": expected_contract_sha256,
            "accepted_independent_audit_sha256": accepted_audit_sha256,
            "pair_session_nonce": pair_session_nonce,
            "execution_contract_bytes": len(contract_bytes),
            "bound_inputs_unchanged_under_locks": True,
            "input_snapshot_sha256": _sha256_bytes(_canonical_json_bytes(before)),
            "runs": run_metadata,
            "matching_inner_payload_sha256": run_metadata[0]["inner_payload_sha256"],
            "full_normalized_topology_sha256": run_metadata[0]["topology_sha256"],
            "truth_boundary": [
                "READ_ONLY_DIAGNOSTIC_PAIR_ONLY",
                "NO_BLEND_MUTATION_OR_SAVE",
                "NO_RENDER_EXPORT_OR_PATH_RESULT",
                "NO_BODY_CANDIDATE",
                "NO_AUTHORING_OR_RUNTIME_AUTHORITY",
            ],
        }
        outcome.accept_child_frame(receipt.encode_receipt_frame(summary))
        outcome.close()
        return output_root
    except BaseException as exc:
        failure = {
            "schema": "kira.avatar.r25.foundation_afes_locked_pair_failure.v4",
            "status": "FAILED_APPEND_ONLY_NO_BODY_AUTHORITY",
            "stage": stage,
            "failure_type": type(exc).__name__,
            "failure": str(exc),
            "execution_contract_sha256": expected_contract_sha256,
            "accepted_independent_audit_sha256": accepted_audit_sha256,
            "pair_session_nonce": pair_session_nonce,
            "receipt_truth": (
                "post_reservation_failure_receipt_attempted; abrupt process termination "
                "or storage failure can still prevent completion"
            ),
        }
        try:
            outcome.accept_child_frame(receipt.encode_receipt_frame(failure))
        finally:
            outcome.close()
        raise


def main() -> int:
    print(
        "R25_AFES_LOCKED_PAIR_V4_DIRECT_EXECUTION_REFUSED_USE_EXTERNAL_LAUNCHER",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
