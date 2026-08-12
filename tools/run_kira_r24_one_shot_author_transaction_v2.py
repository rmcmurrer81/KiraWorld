#!/usr/bin/env python3
"""Inert, append-only v2 CPU controller for a future R24/R5 transaction.

V2 closes the launch and artifact-race defects identified in the independent
v1 audit.  It uses Win32 ``CREATE_SUSPENDED`` directly: the child cannot run
Python or Blender startup code until the controller has created/configured a
kill-on-close Job, assigned the exact process, written the bound Job gate, and
successfully resumed the primary thread.  Failure at create/Job/assign/resume
terminates and waits the exact process tree before any handle is released.

The controller holds an exclusive reservation through the whole transaction.
Blender saves once to a fresh nonce staging path; only after the author Job is
closed and its tree is independently quiescent does the controller atomically
publish with a no-replace Win32 move.  Candidate and extraction paths reject
symlinks/reparse points before and after each phase.

This file remains non-executable: all R5/author bindings are symbolic and
``EXECUTION_AUTHORITY_GRANTED`` is false.  No import or CLI flag changes that.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import ctypes
from ctypes import wintypes
import hashlib
import io
import importlib.util
import json
import msvcrt
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
R19_ATTEMPT_RELATIVE = PurePosixPath(
    "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/attempt_06"
)
R19_MANIFEST_RELATIVE = R19_ATTEMPT_RELATIVE / "PACKAGE_MANIFEST.json"
R19_MANIFEST_BYTES = 13_209
R19_MANIFEST_SHA256 = "9c7038b60e2c712e49e810c0b7f7932bf36a18042dd00a6951834be59bb40f0c"
R19_SOURCE_RELATIVE = R19_ATTEMPT_RELATIVE / "kira_r19_bald_targeted_material_movement_correction.blend"
R19_SOURCE_BYTES = 90_861_425
R19_SOURCE_SHA256 = "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f"
RUNTIME_ROOT_RELATIVE = PurePosixPath(
    "RecoverySprint/continuation_20260808/kira_r24_one_shot_runtime_attempts_v2"
)
ATTEMPT_NAME = "attempt_01"
FINAL_CANDIDATE_BASENAME = "kira_r24_one_shot_private_candidate_v2.blend"
RESERVATION_BASENAME = "CANDIDATE_RESERVATION.json"
RESULT_BASENAME = "ONE_SHOT_TRANSACTION_V2_RESULT.json"
SAFETY_FLAGS = [
    "--background", "--factory-startup", "--disable-autoexec",
    "--python-exit-code", "1",
]
CREATE_SUSPENDED = 0x00000004
CREATE_UNICODE_ENVIRONMENT = 0x00000400
CREATE_NO_WINDOW = 0x08000000
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
INFINITE = 0xFFFFFFFF
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
GENERIC_READ_WRITE = 0x80000000 | 0x40000000
FILE_SHARE_READ = 0x00000001
CREATE_NEW = 1
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000


class WIN_STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
        ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class WIN_PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD),
    ]


class WIN_JOB_BASIC_LIMIT(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong), ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD), ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD),
    ]


class WIN_IO_COUNTERS(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
    )]


class WIN_JOB_EXTENDED_LIMIT(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", WIN_JOB_BASIC_LIMIT), ("IoInfo", WIN_IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class WIN_JOB_PID_LIST(ctypes.Structure):
    _fields_ = [
        ("NumberOfAssignedProcesses", wintypes.DWORD),
        ("NumberOfProcessIdsInList", wintypes.DWORD),
        ("ProcessIdList", ctypes.c_size_t * 1024),
    ]

BLENDER_BINDING: dict[str, object] = {
    "path": "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe",
    "bytes": 108_687_824,
    "sha256": "1e6624af112b3c936f4b038b025ebd2bf00ae72c4b62881a6787166d71c58fa5",
}
DEPENDENCY_BINDINGS: dict[str, dict[str, object]] = {
    "author_worker_v2": {
        "path": "tools/blender_author_kira_r24_one_shot_candidate_v2.py",
        "bytes": None,
        "sha256": None,
    },
    "external_surface_author_operation_r5": {
        "path": "tools/blender_author_kira_r24_r5_external_surface_operation.py",
        "bytes": None,
        "sha256": None,
    },
    "artifact_gate_r5": {
        "path": "tools/kira_r24_artifact_derived_gate_r5.py",
        "bytes": None,
        "sha256": None,
    },
    "read_only_extractor_r5": {
        "path": "tools/blender_extract_kira_r24_candidate_read_only_r5.py",
        "bytes": None,
        "sha256": None,
    },
    "intersection_helper": {
        "path": "tools/blender_exact_mesh_intersections.py",
        "bytes": None,
        "sha256": None,
    },
    "accepted_gate_contract_r5": {
        "path": (
            "RecoverySprint/continuation_20260808/kira_r24_artifact_derived_gate_r5/"
            "KIRA_R24_ARTIFACT_DERIVED_GATE_R5_CONTRACT.json"
        ),
        "bytes": None,
        "sha256": None,
    },
}
EXECUTION_AUTHORITY_GRANTED = False


class R24OneShotControllerV2Error(RuntimeError):
    """Fail-closed v2 controller error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _exclusive_json(path: Path, value: object) -> None:
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())


def _is_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except AttributeError:
        return False


def _project_path(raw: object, *, require_file: bool = False) -> Path:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
        raise R24OneShotControllerV2Error("project path must be nonempty and relative")
    pure = PurePosixPath(raw.replace("\\", "/"))
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise R24OneShotControllerV2Error("unsafe project path component")
    cursor = ROOT
    for part in pure.parts:
        cursor = cursor / part
        if os.path.lexists(cursor) and _is_reparse(cursor):
            raise R24OneShotControllerV2Error("project path contains a reparse component")
    try:
        cursor.resolve(strict=require_file).relative_to(ROOT.resolve())
    except (OSError, ValueError) as exc:
        raise R24OneShotControllerV2Error("project path escaped repository") from exc
    if require_file and (not cursor.is_file() or _is_reparse(cursor)):
        raise R24OneShotControllerV2Error("bound regular file is absent or reparsed")
    return cursor


def _verify_binding(binding: Mapping[str, object], label: str, *, absolute: bool = False) -> dict[str, object]:
    if set(binding) != {"path", "bytes", "sha256"}:
        raise R24OneShotControllerV2Error(f"{label} binding fields changed")
    size = binding.get("bytes")
    digest = binding.get("sha256")
    if not isinstance(size, int) or isinstance(size, bool) or size < 1:
        raise R24OneShotControllerV2Error(f"{label} byte identity is unsealed")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise R24OneShotControllerV2Error(f"{label} digest identity is unsealed")
    raw = binding.get("path")
    if absolute:
        if not isinstance(raw, str) or not Path(raw).is_absolute():
            raise R24OneShotControllerV2Error(f"{label} absolute path is invalid")
        path = Path(raw).resolve()
        if not path.is_file() or _is_reparse(path):
            raise R24OneShotControllerV2Error(f"{label} exact file is absent or reparsed")
    else:
        path = _project_path(raw, require_file=True)
    if path.stat().st_size != size or sha256_file(path) != digest:
        raise R24OneShotControllerV2Error(f"{label} exact identity changed")
    return {"path": str(path), "bytes": size, "sha256": digest}


def _require_inert_authority() -> None:
    if EXECUTION_AUTHORITY_GRANTED is not True:
        raise R24OneShotControllerV2Error("v2 transaction is inert; execution authority is false")


def verify_dependencies() -> dict[str, dict[str, object]]:
    result = {"blender": _verify_binding(BLENDER_BINDING, "Blender", absolute=True)}
    for label, binding in DEPENDENCY_BINDINGS.items():
        result[label] = _verify_binding(binding, label)
    return result


def verify_r19_package() -> dict[str, object]:
    manifest_path = _project_path(R19_MANIFEST_RELATIVE.as_posix(), require_file=True)
    if manifest_path.stat().st_size != R19_MANIFEST_BYTES or sha256_file(manifest_path) != R19_MANIFEST_SHA256:
        raise R24OneShotControllerV2Error("R19 manifest identity changed")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R24OneShotControllerV2Error("R19 manifest is invalid") from exc
    rows = manifest.get("files_excluding_this_manifest") if isinstance(manifest, dict) else None
    if (
        set(manifest) != {"append_only_attempt", "created_utc", "files_excluding_this_manifest", "schema_version"}
        or manifest.get("schema_version") != 1
        or manifest.get("append_only_attempt") != "attempt_06"
        or not isinstance(rows, list)
        or len(rows) != 49
    ):
        raise R24OneShotControllerV2Error("R19 exact 49-file manifest contract changed")
    attempt = _project_path(R19_ATTEMPT_RELATIVE.as_posix())
    expected = {manifest_path.resolve()}
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "size_bytes"}:
            raise R24OneShotControllerV2Error(f"R19 manifest row {index} changed")
        record = _verify_binding(
            {"path": row["path"], "bytes": row["size_bytes"], "sha256": row["sha256"]},
            f"R19 manifest row {index}",
        )
        path = Path(str(record["path"])).resolve()
        try:
            path.relative_to(attempt.resolve())
        except ValueError as exc:
            raise R24OneShotControllerV2Error("R19 manifest row escaped Attempt 06") from exc
        if path in expected:
            raise R24OneShotControllerV2Error("R19 manifest has a duplicate path")
        expected.add(path)
    actual = {path.resolve() for path in attempt.rglob("*") if path.is_file()}
    if actual != expected:
        raise R24OneShotControllerV2Error("R19 on-disk closure changed")
    source = _project_path(R19_SOURCE_RELATIVE.as_posix(), require_file=True)
    if source.stat().st_size != R19_SOURCE_BYTES or sha256_file(source) != R19_SOURCE_SHA256:
        raise R24OneShotControllerV2Error("R19 source identity changed")
    return {"manifest_sha256": R19_MANIFEST_SHA256, "file_count": 49, "source_sha256": R19_SOURCE_SHA256}


def assert_path_absent_nonreparse(path: Path, stop: Path) -> None:
    cursor = path.parent
    while True:
        if not cursor.is_dir() or _is_reparse(cursor):
            raise R24OneShotControllerV2Error("output parent is absent or reparsed")
        if cursor == stop:
            break
        if cursor.parent == cursor:
            raise R24OneShotControllerV2Error("output parent escaped reservation root")
        cursor = cursor.parent
    if os.path.lexists(path) or path.exists() or path.is_symlink():
        raise R24OneShotControllerV2Error("reserved output already exists or is reparsed")


def assert_regular_nonreparse(path: Path, stop: Path) -> None:
    if not path.is_file() or _is_reparse(path):
        raise R24OneShotControllerV2Error("artifact is absent, linked, or reparsed")
    cursor = path.parent
    while True:
        if not cursor.is_dir() or _is_reparse(cursor):
            raise R24OneShotControllerV2Error("artifact parent is linked or reparsed")
        if cursor == stop:
            return
        if cursor.parent == cursor:
            raise R24OneShotControllerV2Error("artifact escaped reservation root")
        cursor = cursor.parent


class ExclusiveReservation:
    """Controller-held, no-delete/no-write-share reservation file."""

    def __init__(self, path: Path, handle: object, token: str) -> None:
        self.path = path
        self.handle = handle
        self.token = token
        self.closed = False

    @classmethod
    def create(cls, path: Path, token: str) -> "ExclusiveReservation":
        if os.name != "nt":
            raise R24OneShotControllerV2Error("exclusive Win32 reservation is mandatory")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
        ]
        kernel32.CreateFileW.restype = wintypes.HANDLE
        handle = kernel32.CreateFileW(
            str(path),
            GENERIC_READ_WRITE,
            FILE_SHARE_READ,
            None,
            CREATE_NEW,
            FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT,
            None,
        )
        if handle in (None, wintypes.HANDLE(-1).value):
            raise R24OneShotControllerV2Error("exclusive reservation creation failed")
        payload = canonical_bytes(
            {
                "schema": "kira.avatar.r24.one_shot_candidate_reservation.v2",
                "token": token,
                "controller_pid": os.getpid(),
                "held_exclusive": True,
            }
        )
        payload_buffer = ctypes.create_string_buffer(payload)
        written = wintypes.DWORD()
        kernel32.WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        kernel32.WriteFile.restype = wintypes.BOOL
        kernel32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
        kernel32.FlushFileBuffers.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        if not kernel32.WriteFile(handle, payload_buffer, len(payload), ctypes.byref(written), None) or written.value != len(payload):
            kernel32.CloseHandle(handle)
            raise R24OneShotControllerV2Error("exclusive reservation write failed")
        if not kernel32.FlushFileBuffers(handle):
            kernel32.CloseHandle(handle)
            raise R24OneShotControllerV2Error("exclusive reservation flush failed")
        return cls(path, handle, token)

    def close(self) -> dict[str, object]:
        if self.closed:
            return {"closed": True, "already_closed": True}
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        if not kernel32.CloseHandle(self.handle):
            raise R24OneShotControllerV2Error("exclusive reservation close failed")
        self.closed = True
        return {"closed": True, "held_through_both_children": True}


def _safe_make_directory(path: Path) -> None:
    try:
        relative = path.resolve(strict=False).relative_to(ROOT.resolve())
    except ValueError as exc:
        raise R24OneShotControllerV2Error("output directory escaped repository") from exc
    cursor = ROOT
    for part in relative.parts:
        cursor = cursor / part
        if os.path.lexists(cursor):
            if not cursor.is_dir() or _is_reparse(cursor):
                raise R24OneShotControllerV2Error("output directory contains a reparse or non-directory")
        else:
            cursor.mkdir(exist_ok=False)


def reserve_attempt() -> dict[str, Any]:
    runtime = _project_path(RUNTIME_ROOT_RELATIVE.as_posix())
    _safe_make_directory(runtime)
    attempt = runtime / ATTEMPT_NAME
    if os.path.lexists(attempt):
        raise R24OneShotControllerV2Error("append-only v2 attempt_01 already exists")
    attempt.mkdir(exist_ok=False)
    staging_root = attempt / "author_staging"
    extraction_root = attempt / "fresh_reopen"
    staging_root.mkdir(exist_ok=False)
    extraction_root.mkdir(exist_ok=False)
    token = hashlib.sha256(os.urandom(64)).hexdigest()
    reservation_path = attempt / RESERVATION_BASENAME
    reservation = ExclusiveReservation.create(reservation_path, token)
    staging = staging_root / f"candidate_{token}.blend"
    candidate = attempt / FINAL_CANDIDATE_BASENAME
    extraction = extraction_root / "candidate_extraction.json"
    for path in (staging, candidate, extraction):
        assert_path_absent_nonreparse(path, attempt)
    return {
        "runtime": runtime,
        "attempt": attempt,
        "staging_root": staging_root,
        "extraction_root": extraction_root,
        "staging": staging,
        "candidate": candidate,
        "extraction": extraction,
        "reservation_path": reservation_path,
        "reservation": reservation,
        "reservation_token": token,
        "result": attempt / RESULT_BASENAME,
    }


def atomic_publish_no_replace(staging: Path, candidate: Path, attempt: Path) -> None:
    if os.name != "nt":
        raise R24OneShotControllerV2Error("atomic no-replace publish is Windows-only")
    assert_regular_nonreparse(staging, attempt)
    assert_path_absent_nonreparse(candidate, attempt)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.MoveFileExW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
    kernel32.MoveFileExW.restype = wintypes.BOOL
    if not kernel32.MoveFileExW(str(staging), str(candidate), 0):
        raise R24OneShotControllerV2Error("atomic no-replace candidate publish failed")
    if os.path.lexists(staging):
        raise R24OneShotControllerV2Error("staging path remained after atomic publish")
    assert_regular_nonreparse(candidate, attempt)


class WindowsSuspendedJobNative:
    """Minimal Win32 primitive adapter; state sequencing is tested separately."""

    def __init__(self) -> None:
        if os.name != "nt":
            raise R24OneShotControllerV2Error("Win32 suspended Job launch is mandatory")
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.CreateProcessW.argtypes = [
            wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
            wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
            ctypes.POINTER(WIN_STARTUPINFO), ctypes.POINTER(WIN_PROCESS_INFORMATION),
        ]
        self.kernel32.CreateProcessW.restype = wintypes.BOOL
        self.kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        self.kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ]
        self.kernel32.SetInformationJobObject.restype = wintypes.BOOL
        self.kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        self.kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
        self.kernel32.ResumeThread.restype = wintypes.DWORD
        self.kernel32.QueryInformationJobObject.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.kernel32.QueryInformationJobObject.restype = wintypes.BOOL
        self.kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel32.WaitForSingleObject.restype = wintypes.DWORD
        self.kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        self.kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        self.kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.kernel32.TerminateJobObject.restype = wintypes.BOOL
        self.kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.kernel32.TerminateProcess.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL

    def create_suspended(
        self,
        command: Sequence[str],
        environment: Mapping[str, str],
        stdout_path: Path,
        stderr_path: Path,
    ) -> dict[str, Any]:
        stdout = stdout_path.open("xb")
        stderr = stderr_path.open("xb")
        stdin = open(os.devnull, "rb")
        for stream in (stdin, stdout, stderr):
            os.set_handle_inheritable(msvcrt.get_osfhandle(stream.fileno()), True)
        startup = WIN_STARTUPINFO()
        startup.cb = ctypes.sizeof(startup)
        startup.dwFlags = 0x00000100
        startup.hStdInput = msvcrt.get_osfhandle(stdin.fileno())
        startup.hStdOutput = msvcrt.get_osfhandle(stdout.fileno())
        startup.hStdError = msvcrt.get_osfhandle(stderr.fileno())
        info = WIN_PROCESS_INFORMATION()
        command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(list(command)))
        env_block = ctypes.create_unicode_buffer("\0".join(f"{key}={value}" for key, value in sorted(environment.items())) + "\0\0")
        ok = self.kernel32.CreateProcessW(
            str(command[0]), command_line, None, None, True,
            CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW,
            env_block, str(ROOT), ctypes.byref(startup), ctypes.byref(info),
        )
        for stream in (stdin, stdout, stderr):
            os.set_handle_inheritable(msvcrt.get_osfhandle(stream.fileno()), False)
        if not ok:
            stdin.close(); stdout.close(); stderr.close()
            raise R24OneShotControllerV2Error("CreateProcessW(CREATE_SUSPENDED) failed")
        return {
            "process": info.hProcess,
            "thread": info.hThread,
            "pid": int(info.dwProcessId),
            "stdin": stdin,
            "stdout": stdout,
            "stderr": stderr,
        }

    def create_job(self) -> Any:
        handle = self.kernel32.CreateJobObjectW(None, None)
        if not handle:
            raise R24OneShotControllerV2Error("CreateJobObjectW failed")
        info = WIN_JOB_EXTENDED_LIMIT()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel32.SetInformationJobObject(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.kernel32.CloseHandle(handle)
            raise R24OneShotControllerV2Error("kill-on-close Job configuration failed")
        return handle

    def assign(self, job: Any, process: Any) -> None:
        if not self.kernel32.AssignProcessToJobObject(job, process):
            raise R24OneShotControllerV2Error("suspended child Job assignment failed")

    def resume(self, thread: Any) -> int:
        value = int(self.kernel32.ResumeThread(thread))
        if value == 0xFFFFFFFF or value != 1:
            raise R24OneShotControllerV2Error("primary thread did not resume from exactly one suspend")
        return value

    def query_job_pids(self, job: Any) -> list[int]:
        info = WIN_JOB_PID_LIST()
        returned = wintypes.DWORD()
        if not self.kernel32.QueryInformationJobObject(job, 3, ctypes.byref(info), ctypes.sizeof(info), ctypes.byref(returned)):
            raise R24OneShotControllerV2Error("Job PID query failed")
        if info.NumberOfProcessIdsInList > 1024:
            raise R24OneShotControllerV2Error("Job PID inventory exceeded bound")
        return sorted(int(info.ProcessIdList[index]) for index in range(info.NumberOfProcessIdsInList))

    def wait_direct_and_tree(self, child: Mapping[str, Any], job: Any, timeout_seconds: int) -> dict[str, object]:
        deadline = time.monotonic() + timeout_seconds
        observed: set[int] = {int(child["pid"])}
        direct_exit = False
        while time.monotonic() < deadline:
            observed.update(self.query_job_pids(job))
            wait = int(self.kernel32.WaitForSingleObject(child["process"], 50))
            if wait == WAIT_OBJECT_0:
                direct_exit = True
                break
            if wait != WAIT_TIMEOUT:
                raise R24OneShotControllerV2Error("direct process wait failed")
        if not direct_exit:
            raise R24OneShotControllerV2Error("suspended-owned child timed out")
        while time.monotonic() < deadline:
            active = self.query_job_pids(job)
            observed.update(active)
            if not active:
                break
            time.sleep(0.025)
        else:
            raise R24OneShotControllerV2Error("child Job tree did not become quiescent")
        exit_code = wintypes.DWORD()
        if not self.kernel32.GetExitCodeProcess(child["process"], ctypes.byref(exit_code)):
            raise R24OneShotControllerV2Error("GetExitCodeProcess failed")
        return {
            "direct_exit_observed": True,
            "exit_code": int(exit_code.value),
            "observed_pids": sorted(observed),
            "active_before_job_close": [],
        }

    def terminate_and_wait(self, child: Mapping[str, Any] | None, job: Any | None) -> None:
        if job is not None:
            self.kernel32.TerminateJobObject(job, 125)
        # Assignment itself may have failed, so always terminate the exact
        # direct child as well as the Job tree.  TerminateProcess is allowed to
        # report false when the process already exited; the bounded wait below
        # is the controlling observation.
        process = child.get("process") if child is not None else None
        if process:
            self.kernel32.TerminateProcess(child["process"], 125)
        if process:
            wait = int(self.kernel32.WaitForSingleObject(child["process"], 30_000))
            if wait != WAIT_OBJECT_0:
                raise R24OneShotControllerV2Error("failed child did not terminate within the bound")
        if job is not None:
            deadline = time.monotonic() + 30.0
            while self.query_job_pids(job) and time.monotonic() < deadline:
                time.sleep(0.025)
            if self.query_job_pids(job):
                raise R24OneShotControllerV2Error("failed child Job tree did not terminate within the bound")

    def close_thread(self, child: Mapping[str, Any]) -> None:
        if child.get("thread"):
            if not self.kernel32.CloseHandle(child["thread"]):
                raise R24OneShotControllerV2Error("primary thread handle close failed")
            child["thread"] = None

    def close_process(self, child: Mapping[str, Any]) -> None:
        errors: list[BaseException] = []
        for name in ("stdin", "stdout", "stderr"):
            if not child[name].closed:
                try:
                    child[name].close()
                except BaseException as exc:
                    errors.append(exc)
        if child.get("process"):
            if not self.kernel32.CloseHandle(child["process"]):
                errors.append(R24OneShotControllerV2Error("direct process handle close failed"))
            child["process"] = None
        if errors:
            raise R24OneShotControllerV2Error("one or more direct-child handles failed to close") from errors[0]

    def close_job(self, job: Any) -> None:
        if not self.kernel32.CloseHandle(job):
            raise R24OneShotControllerV2Error("Job handle close failed")

    def active_system_pids(self, candidates: Sequence[int]) -> list[int]:
        # A bounded tasklist PID inventory is independent of the now-closed Job.
        active: list[int] = []
        for pid in sorted(set(int(item) for item in candidates)):
            completed = subprocess.run(
                ["tasklist.exe", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                check=False,
                timeout=10,
            )
            if completed.returncode != 0:
                raise R24OneShotControllerV2Error("post-Job system PID inventory failed")
            if f'"{pid}"'.encode("ascii") in completed.stdout:
                active.append(pid)
        return active


def _close_child_handles_safely(native: Any, child: Mapping[str, Any] | None, job: Any | None) -> None:
    errors: list[BaseException] = []
    if child is not None:
        try:
            native.close_thread(child)
        except BaseException as exc:
            errors.append(exc)
        try:
            native.close_process(child)
        except BaseException as exc:
            errors.append(exc)
    if job is not None:
        try:
            native.close_job(job)
        except BaseException as exc:
            errors.append(exc)
    if errors:
        raise R24OneShotControllerV2Error("failed child cleanup left unproved handle state") from errors[0]


def run_suspended_owned_child(
    command: Sequence[str],
    environment: Mapping[str, str],
    *,
    role: str,
    nonce: str,
    invocation_index: int,
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: int,
    job_gate_path: Path | None,
    native: Any | None = None,
) -> dict[str, object]:
    if role not in {"author", "fresh_reopen"}:
        raise R24OneShotControllerV2Error("child role is invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", nonce):
        raise R24OneShotControllerV2Error("child nonce is invalid")
    if not isinstance(invocation_index, int) or isinstance(invocation_index, bool) or invocation_index < 1:
        raise R24OneShotControllerV2Error("child invocation index is invalid")
    if not command or any(not isinstance(item, str) or not item for item in command):
        raise R24OneShotControllerV2Error("child command is invalid")
    native = WindowsSuspendedJobNative() if native is None else native
    child: Mapping[str, Any] | None = None
    job: Any | None = None
    resumed = False
    try:
        child = native.create_suspended(command, environment, stdout_path, stderr_path)
        job = native.create_job()
        native.assign(job, child["process"])
        if job_gate_path is not None:
            _exclusive_json(
                job_gate_path,
                {
                    "schema": "kira.avatar.r24.suspended_child_job_gate.v2",
                    "role": role,
                    "nonce": nonce,
                    "parent_pid": os.getpid(),
                    "child_pid": int(child["pid"]),
                    "created_suspended": True,
                    "job_configured": True,
                    "assigned_before_resume": True,
                    # This file is written before ResumeThread by design.  It
                    # authorizes the one resume; the controller-owned child
                    # record captures the actual ResumeThread return value.
                    "resume_authorized": True,
                },
            )
        previous_suspend_count = native.resume(child["thread"])
        resumed = True
        native.close_thread(child)
        wait = native.wait_direct_and_tree(child, job, timeout_seconds)
        native.close_process(child)
        native.close_job(job)
        job = None
        post_close_active = native.active_system_pids(wait["observed_pids"])
        if post_close_active:
            raise R24OneShotControllerV2Error(
                "child tree remained active after independent post-Job inventory"
            )
        record = {
            "schema": "kira.avatar.r24.suspended_owned_child.v2",
            "role": role,
            "nonce": nonce,
            "invocation_index": invocation_index,
            "command_sha256": canonical_sha256(list(command)),
            "pid": int(child["pid"]),
            "created_suspended": True,
            "job_created": True,
            "job_configured_kill_on_close": True,
            "assigned_before_resume": True,
            "resumed": resumed,
            "resume_previous_suspend_count": previous_suspend_count,
            "direct_exit_observed": wait["direct_exit_observed"],
            "exit_code": wait["exit_code"],
            "job_observed_pids": wait["observed_pids"],
            "job_active_pids_before_close": wait["active_before_job_close"],
            "thread_handle_closed": True,
            "process_handle_closed": True,
            "job_handle_closed": True,
            "post_close_active_observed_pids": post_close_active,
            "tree_quiescent_after_job_close": not post_close_active,
            "stdout": {"path": str(stdout_path), "bytes": stdout_path.stat().st_size, "sha256": sha256_file(stdout_path)},
            "stderr": {"path": str(stderr_path), "bytes": stderr_path.stat().st_size, "sha256": sha256_file(stderr_path)},
        }
        return record
    except BaseException:
        try:
            native.terminate_and_wait(child, job)
        finally:
            try:
                _close_child_handles_safely(native, child, job)
            except BaseException:
                pass
        raise


CHILD_EVIDENCE_FIELDS = {
    "schema", "role", "nonce", "invocation_index", "command_sha256", "pid",
    "created_suspended", "job_created", "job_configured_kill_on_close",
    "assigned_before_resume", "resumed", "resume_previous_suspend_count",
    "direct_exit_observed", "exit_code", "job_observed_pids",
    "job_active_pids_before_close", "thread_handle_closed", "process_handle_closed",
    "job_handle_closed", "post_close_active_observed_pids",
    "tree_quiescent_after_job_close", "stdout", "stderr",
}


def validate_child_evidence(
    value: object,
    *,
    expected_role: str,
    expected_nonce: str,
    expected_invocation_index: int,
    expected_command: Sequence[str],
    expected_stdout_path: Path,
    expected_stderr_path: Path,
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != CHILD_EVIDENCE_FIELDS:
        raise R24OneShotControllerV2Error("child evidence field inventory changed")
    expected_text = {
        "schema": "kira.avatar.r24.suspended_owned_child.v2",
        "role": expected_role,
        "nonce": expected_nonce,
        "command_sha256": canonical_sha256(list(expected_command)),
    }
    for key, expected_value in expected_text.items():
        if value.get(key) != expected_value:
            raise R24OneShotControllerV2Error(f"child evidence rejected:{key}")
    strict_integers = {
        "invocation_index": expected_invocation_index,
        "resume_previous_suspend_count": 1,
        "exit_code": 0,
    }
    for key, expected_value in strict_integers.items():
        item = value.get(key)
        if not isinstance(item, int) or isinstance(item, bool) or item != expected_value:
            raise R24OneShotControllerV2Error(f"child evidence rejected:{key}")
    for key in (
        "created_suspended", "job_created", "job_configured_kill_on_close",
        "assigned_before_resume", "resumed", "direct_exit_observed",
        "thread_handle_closed", "process_handle_closed", "job_handle_closed",
        "tree_quiescent_after_job_close",
    ):
        if value.get(key) is not True:
            raise R24OneShotControllerV2Error(f"child evidence rejected:{key}")
    for key in ("job_active_pids_before_close", "post_close_active_observed_pids"):
        if value.get(key) != []:
            raise R24OneShotControllerV2Error(f"child evidence rejected:{key}")
    pid = value.get("pid")
    observed = value.get("job_observed_pids")
    if not isinstance(pid, int) or isinstance(pid, bool) or pid < 1:
        raise R24OneShotControllerV2Error("child evidence rejected:pid")
    if (
        not isinstance(observed, list)
        or not observed
        or any(not isinstance(item, int) or isinstance(item, bool) or item < 1 for item in observed)
        or len(observed) != len(set(observed))
        or pid not in observed
    ):
        raise R24OneShotControllerV2Error("child evidence rejected:job_observed_pids")
    expected_streams = {
        "stdout": expected_stdout_path,
        "stderr": expected_stderr_path,
    }
    for stream_name, expected_path in expected_streams.items():
        stream = value.get(stream_name)
        if not isinstance(stream, dict) or set(stream) != {"path", "bytes", "sha256"}:
            raise R24OneShotControllerV2Error(f"child evidence rejected:{stream_name}")
        path = Path(str(stream["path"]))
        if (
            path.resolve(strict=False) != expected_path.resolve(strict=False)
            or not path.is_file()
            or _is_reparse(path)
            or not isinstance(stream["bytes"], int)
            or isinstance(stream["bytes"], bool)
            or stream["bytes"] < 0
            or not isinstance(stream["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", stream["sha256"])
            or path.stat().st_size != stream["bytes"]
            or sha256_file(path) != stream["sha256"]
        ):
            raise R24OneShotControllerV2Error(f"child evidence rejected:{stream_name}_artifact")
    return value


def validate_transaction_children(records: Sequence[Mapping[str, object]]) -> dict[str, int]:
    if len(records) != 2:
        raise R24OneShotControllerV2Error("transaction child evidence must contain exactly two records")
    required = {"role", "invocation_index", "pid", "nonce", "command_sha256"}
    if any(not isinstance(record, Mapping) or not required.issubset(record) for record in records):
        raise R24OneShotControllerV2Error("transaction child evidence is incomplete")
    if [record["role"] for record in records] != ["author", "fresh_reopen"]:
        raise R24OneShotControllerV2Error("transaction child roles/order changed")
    if [record["invocation_index"] for record in records] != [1, 2]:
        raise R24OneShotControllerV2Error("transaction child invocation indices changed")
    for field in ("pid", "nonce", "command_sha256"):
        if len({record[field] for record in records}) != 2:
            raise R24OneShotControllerV2Error(f"transaction children are not distinct:{field}")
    counts = Counter(str(record["role"]) for record in records)
    return {
        "author": counts["author"],
        "fresh_reopen": counts["fresh_reopen"],
        "total": sum(counts.values()),
    }


def ensure_no_blender_process(
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> dict[str, object]:
    """Take one bounded process inventory; never kill an existing Blender."""
    if os.name != "nt":
        raise R24OneShotControllerV2Error("the suspended Job transaction is Windows-only")
    completed = runner(
        ["tasklist.exe", "/FO", "CSV", "/NH"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        shell=False,
        timeout=20,
    )
    if completed.returncode != 0:
        raise R24OneShotControllerV2Error("one bounded Blender process inventory failed")
    try:
        rows = list(csv.reader(io.StringIO(completed.stdout.decode("utf-8", errors="strict"))))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise R24OneShotControllerV2Error("Blender process inventory is not parseable") from exc
    blender_rows = [
        row for row in rows
        if row and row[0].lower() in {"blender.exe", "blender-launcher.exe"}
    ]
    if blender_rows:
        raise R24OneShotControllerV2Error("a Blender process is already active")
    return {
        "inventory_command": "tasklist.exe /FO CSV /NH",
        "blender_process_count": 0,
    }


def child_environment(nonce: str) -> dict[str, str]:
    allowed = (
        "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERNAME", "USERPROFILE",
        "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA", "APPDATA", "PATH",
    )
    result = {name: os.environ[name] for name in allowed if os.environ.get(name)}
    result.update({"PYTHONNOUSERSITE": "1", "KIRA_R24_ONE_SHOT_V2_CHILD_NONCE": nonce})
    return result


def author_command(paths: Mapping[str, Any], dependencies: Mapping[str, Mapping[str, object]], nonce: str) -> list[str]:
    return [
        str(dependencies["blender"]["path"]), *SAFETY_FLAGS,
        "--python", str(dependencies["author_worker_v2"]["path"]), "--",
        "--source", str(_project_path(R19_SOURCE_RELATIVE.as_posix(), require_file=True)),
        "--staging-output", str(paths["staging"]),
        "--reservation", str(paths["reservation_path"]),
        "--reservation-token", str(paths["reservation_token"]),
        "--job-gate", str(paths["attempt"] / f"author_job_gate_{nonce}.json"),
        "--role", "author", "--child-nonce", nonce, "--execute-authoring",
    ]


def reopen_command(
    paths: Mapping[str, Any],
    dependencies: Mapping[str, Mapping[str, object]],
    nonce: str,
    candidate_sha256: str,
) -> list[str]:
    return [
        str(dependencies["blender"]["path"]), *SAFETY_FLAGS,
        str(paths["candidate"]),
        "--python", str(dependencies["read_only_extractor_r5"]["path"]), "--",
        "--candidate", str(paths["candidate"]),
        "--candidate-sha256", candidate_sha256,
        "--extractor-sha256", str(dependencies["read_only_extractor_r5"]["sha256"]),
        "--intersection-helper-sha256", str(dependencies["intersection_helper"]["sha256"]),
        "--nonce", nonce, "--output", str(paths["extraction"]),
    ]


def _load_gate(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("_kira_r24_r5_gate_for_v2", path)
    if spec is None or spec.loader is None:
        raise R24OneShotControllerV2Error("R5 gate cannot be imported")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "validate_extraction_envelope", None)):
        raise R24OneShotControllerV2Error("R5 gate envelope validator is absent")
    return module


def execute_transaction(
    *,
    package_verifier: Callable[[], dict[str, object]] = verify_r19_package,
    dependency_verifier: Callable[[], dict[str, dict[str, object]]] = verify_dependencies,
    process_guard: Callable[[], dict[str, object]] = ensure_no_blender_process,
    reserver: Callable[[], dict[str, Any]] = reserve_attempt,
    child_runner: Callable[..., dict[str, object]] = run_suspended_owned_child,
    publisher: Callable[[Path, Path, Path], None] = atomic_publish_no_replace,
) -> dict[str, object]:
    _require_inert_authority()
    package = package_verifier()
    dependencies = dependency_verifier()
    process_inventory = process_guard()
    paths = reserver()
    reservation = paths["reservation"]
    author_nonce = hashlib.sha256(os.urandom(64)).hexdigest()
    reopen_nonce = hashlib.sha256(os.urandom(64)).hexdigest()
    if author_nonce == reopen_nonce:
        raise R24OneShotControllerV2Error("child nonces unexpectedly collided")
    source = _project_path(R19_SOURCE_RELATIVE.as_posix(), require_file=True)
    source_before = sha256_file(source)
    records: list[dict[str, object]] = []
    try:
        author = author_command(paths, dependencies, author_nonce)
        author_gate = paths["attempt"] / f"author_job_gate_{author_nonce}.json"
        author_raw = child_runner(
            author,
            child_environment(author_nonce),
            role="author",
            nonce=author_nonce,
            invocation_index=1,
            stdout_path=paths["attempt"] / "author_v2.stdout.log",
            stderr_path=paths["attempt"] / "author_v2.stderr.log",
            timeout_seconds=1800,
            job_gate_path=author_gate,
        )
        author_record = validate_child_evidence(
            author_raw,
            expected_role="author",
            expected_nonce=author_nonce,
            expected_invocation_index=1,
            expected_command=author,
            expected_stdout_path=paths["attempt"] / "author_v2.stdout.log",
            expected_stderr_path=paths["attempt"] / "author_v2.stderr.log",
        )
        records.append(author_record)
        assert_regular_nonreparse(paths["staging"], paths["attempt"])
        staging_digest = sha256_file(paths["staging"])
        publisher(paths["staging"], paths["candidate"], paths["attempt"])
        assert_regular_nonreparse(paths["candidate"], paths["attempt"])
        candidate_digest = sha256_file(paths["candidate"])
        if candidate_digest != staging_digest:
            raise R24OneShotControllerV2Error("atomic publish changed candidate bytes")
        assert_path_absent_nonreparse(paths["extraction"], paths["attempt"])
        reopen = reopen_command(paths, dependencies, reopen_nonce, candidate_digest)
        reopen_raw = child_runner(
            reopen,
            child_environment(reopen_nonce),
            role="fresh_reopen",
            nonce=reopen_nonce,
            invocation_index=2,
            stdout_path=paths["extraction_root"] / "fresh_reopen_v2.stdout.log",
            stderr_path=paths["extraction_root"] / "fresh_reopen_v2.stderr.log",
            timeout_seconds=1800,
            job_gate_path=None,
        )
        reopen_record = validate_child_evidence(
            reopen_raw,
            expected_role="fresh_reopen",
            expected_nonce=reopen_nonce,
            expected_invocation_index=2,
            expected_command=reopen,
            expected_stdout_path=paths["extraction_root"] / "fresh_reopen_v2.stdout.log",
            expected_stderr_path=paths["extraction_root"] / "fresh_reopen_v2.stderr.log",
        )
        records.append(reopen_record)
        derived_counts = validate_transaction_children(records)
        assert_regular_nonreparse(paths["candidate"], paths["attempt"])
        assert_regular_nonreparse(paths["extraction"], paths["attempt"])
        if sha256_file(paths["candidate"]) != candidate_digest:
            raise R24OneShotControllerV2Error("candidate changed during fresh reopen")
        if sha256_file(source) != source_before:
            raise R24OneShotControllerV2Error("preserved R19 source changed")
        snapshot = json.loads(paths["extraction"].read_text(encoding="utf-8"))
        gate = _load_gate(Path(str(dependencies["artifact_gate_r5"]["path"])))
        failures = gate.validate_extraction_envelope(
            snapshot,
            nonce=reopen_nonce,
            candidate=paths["candidate"],
            candidate_sha256=candidate_digest,
            extractor_sha256=str(dependencies["read_only_extractor_r5"]["sha256"]),
            intersection_helper_sha256=str(dependencies["intersection_helper"]["sha256"]),
        )
        if failures:
            raise R24OneShotControllerV2Error("R5 fresh-reopen envelope rejected")
        reservation_close = reservation.close()
        result = {
            "schema": "kira.avatar.r24.one_shot_author_transaction.v2",
            "status": "FRESH_REOPEN_CAPTURED_R5_FULL_EVALUATION_REQUIRED_NOT_ACCEPTED",
            "r19_package": package,
            "process_inventory": process_inventory,
            "children": records,
            "invocation_counts_derived_from_children": derived_counts,
            "reservation_close": reservation_close,
            "candidate": {"path": str(paths["candidate"]), "bytes": paths["candidate"].stat().st_size, "sha256": candidate_digest},
            "extraction": {"path": str(paths["extraction"]), "bytes": paths["extraction"].stat().st_size, "sha256": sha256_file(paths["extraction"])},
            "retry_count_derived_from_invocation_sequence": max(0, derived_counts["total"] - 2),
            "candidate_accepted": False,
            "runtime_eligible": False,
        }
        _exclusive_json(paths["result"], result)
        return result
    finally:
        if not getattr(reservation, "closed", False):
            reservation.close()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-once", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.execute_once:
        raise R24OneShotControllerV2Error("--execute-once is required but never sufficient")
    raise R24OneShotControllerV2Error(
        "v2 remains static: R5 bindings and execution authority are absent"
    )


if __name__ == "__main__":
    raise SystemExit(main())
