#!/usr/bin/env python3
"""Inert append-only v3 controller for a future R24/R7 one-shot transaction.

V3 owns native process resources from the first successful ``CreateProcessW``
instruction.  Every later pre-return failure is locally terminated, waited and
closed.  Cleanup errors are attached to and propagated by a dedicated failure;
none are suppressed.  Production execution calls the native child runner
directly and accepts no injected child/evidence callback.

Blender writes only to a nonce-private file.  The v3 worker publishes it with a
no-replace move to sealed staging; after author exit/tree proof this controller
publishes sealed staging with another no-replace move to the final candidate.
Raw paths are inspected for reparse aliases before resolution and rechecked at
each boundary.

R7 and author-operation bindings remain symbolic and execution authority is
false.  This file cannot launch Blender or create ``attempt_01`` today.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import ctypes
from ctypes import wintypes
import hashlib
import importlib.util
import io
import json
import msvcrt
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence


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
    "RecoverySprint/continuation_20260808/kira_r24_one_shot_runtime_attempts_v3"
)
ATTEMPT_NAME = "attempt_01"
FINAL_CANDIDATE_BASENAME = "kira_r24_one_shot_private_candidate_v3.blend"
RESERVATION_BASENAME = "CANDIDATE_RESERVATION_V3.json"
RESULT_BASENAME = "ONE_SHOT_TRANSACTION_V3_RESULT.json"
SAFETY_FLAGS = [
    "--background", "--factory-startup", "--disable-autoexec",
    "--python-exit-code", "1",
]

CREATE_SUSPENDED = 0x00000004
CREATE_UNICODE_ENVIRONMENT = 0x00000400
CREATE_NO_WINDOW = 0x08000000
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
SYNCHRONIZE = 0x00100000
PROCESS_QUERY_LIMITED_INFORMATION = 0x00001000
ERROR_INVALID_PARAMETER = 87
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
GENERIC_READ_WRITE = 0x80000000 | 0x40000000
FILE_SHARE_READ = 0x00000001
CREATE_NEW = 1
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000


BLENDER_BINDING: dict[str, object] = {
    "path": "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe",
    "bytes": 108_687_824,
    "sha256": "1e6624af112b3c936f4b038b025ebd2bf00ae72c4b62881a6787166d71c58fa5",
}
DEPENDENCY_BINDINGS: dict[str, dict[str, object]] = {
    "author_worker_v3": {
        "path": "tools/blender_author_kira_r24_one_shot_candidate_v3.py",
        "bytes": None,
        "sha256": None,
    },
    "external_surface_author_operation_r7": {
        "path": "tools/blender_author_kira_r24_r7_external_surface_operation.py",
        "bytes": None,
        "sha256": None,
    },
    "artifact_gate_r7": {
        "path": "tools/kira_r24_artifact_derived_gate_r7.py",
        "bytes": None,
        "sha256": None,
    },
    "read_only_extractor_r7": {
        "path": "tools/blender_extract_kira_r24_candidate_read_only_r7.py",
        "bytes": None,
        "sha256": None,
    },
    "intersection_helper": {
        "path": "tools/blender_exact_mesh_intersections.py",
        "bytes": None,
        "sha256": None,
    },
    "accepted_gate_contract_r7": {
        "path": (
            "RecoverySprint/continuation_20260808/kira_r24_artifact_derived_gate_r7/"
            "KIRA_R24_ARTIFACT_DERIVED_GATE_R7_CONTRACT.json"
        ),
        "bytes": None,
        "sha256": None,
    },
}
EXECUTION_AUTHORITY_GRANTED = False


class R24OneShotControllerV3Error(RuntimeError):
    """Fail-closed v3 controller error."""


class R24OneShotCleanupV3Error(R24OneShotControllerV3Error):
    """A primary failure accompanied by unproved native cleanup."""

    def __init__(self, stage: str, primary: BaseException, cleanup_report: Mapping[str, object]) -> None:
        self.stage = stage
        self.primary = primary
        self.cleanup_report = dict(cleanup_report)
        super().__init__(
            f"{stage} failed and cleanup was not clean: {primary}; "
            f"cleanup_errors={cleanup_report.get('errors')}"
        )


class R24OneShotOwnedFailureV3Error(R24OneShotControllerV3Error):
    """A primary failure whose complete native cleanup was directly observed."""

    def __init__(self, stage: str, primary: BaseException, cleanup_report: Mapping[str, object]) -> None:
        self.stage = stage
        self.primary = primary
        self.cleanup_report = dict(cleanup_report)
        super().__init__(f"{stage} failed after complete cleanup: {primary}")


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


def sha256_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _is_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except (AttributeError, FileNotFoundError):
        return False


def inspect_raw_nonreparse(raw: str | os.PathLike[str]) -> Path:
    if not isinstance(raw, (str, os.PathLike)) or not os.fspath(raw):
        raise R24OneShotControllerV3Error("raw path is empty")
    path = Path(os.path.abspath(os.fspath(raw)))
    cursor = Path(path.anchor)
    for part in path.parts[1:]:
        cursor = cursor / part
        if os.path.lexists(cursor) and _is_reparse(cursor):
            raise R24OneShotControllerV3Error(f"raw path contains reparse component:{cursor}")
    return path


def checked_path(
    raw: str | os.PathLike[str],
    *,
    root: Path,
    require_file: bool = False,
    require_directory: bool = False,
) -> Path:
    lexical = inspect_raw_nonreparse(raw)
    lexical_root = inspect_raw_nonreparse(root)
    try:
        resolved_root = lexical_root.resolve(strict=True)
        resolved = lexical.resolve(strict=require_file or require_directory)
        resolved.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise R24OneShotControllerV3Error("path escaped exact non-reparse root") from exc
    inspect_raw_nonreparse(lexical)
    if require_file and (not lexical.is_file() or _is_reparse(lexical)):
        raise R24OneShotControllerV3Error("required regular non-reparse file is absent")
    if require_directory and (not lexical.is_dir() or _is_reparse(lexical)):
        raise R24OneShotControllerV3Error("required regular non-reparse directory is absent")
    return lexical


def _binding(binding: Mapping[str, object], label: str, *, absolute: bool = False) -> dict[str, object]:
    if set(binding) != {"path", "bytes", "sha256"}:
        raise R24OneShotControllerV3Error(f"{label} binding fields changed")
    size = binding.get("bytes")
    digest = binding.get("sha256")
    if not isinstance(size, int) or isinstance(size, bool) or size < 1:
        raise R24OneShotControllerV3Error(f"{label} byte identity is unsealed")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise R24OneShotControllerV3Error(f"{label} digest identity is unsealed")
    raw = binding.get("path")
    if not isinstance(raw, str):
        raise R24OneShotControllerV3Error(f"{label} path is invalid")
    path = checked_path(raw if absolute else ROOT / raw, root=Path(raw).anchor if absolute else ROOT, require_file=True)
    if path.stat().st_size != size or sha256_file(path) != digest:
        raise R24OneShotControllerV3Error(f"{label} exact identity changed")
    return {"path": str(path), "bytes": size, "sha256": digest}


def verify_dependencies() -> dict[str, dict[str, object]]:
    result = {"blender": _binding(BLENDER_BINDING, "Blender", absolute=True)}
    for label, value in DEPENDENCY_BINDINGS.items():
        result[label] = _binding(value, label)
    return result


def verify_r19_package() -> dict[str, object]:
    attempt = checked_path(ROOT / R19_ATTEMPT_RELATIVE, root=ROOT, require_directory=True)
    manifest_path = checked_path(ROOT / R19_MANIFEST_RELATIVE, root=ROOT, require_file=True)
    if manifest_path.stat().st_size != R19_MANIFEST_BYTES or sha256_file(manifest_path) != R19_MANIFEST_SHA256:
        raise R24OneShotControllerV3Error("R19 manifest identity changed")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R24OneShotControllerV3Error("R19 manifest is invalid") from exc
    rows = manifest.get("files_excluding_this_manifest") if isinstance(manifest, dict) else None
    if not isinstance(rows, list) or len(rows) != 49:
        raise R24OneShotControllerV3Error("R19 exact 49-file closure changed")
    expected = {manifest_path}
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "size_bytes"}:
            raise R24OneShotControllerV3Error(f"R19 manifest row {index} changed")
        path = checked_path(ROOT / str(row["path"]), root=attempt, require_file=True)
        if path in expected or path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise R24OneShotControllerV3Error(f"R19 manifest row {index} identity changed")
        expected.add(path)
    actual = {item for item in attempt.rglob("*") if item.is_file()}
    if actual != expected:
        raise R24OneShotControllerV3Error("R19 on-disk file closure changed")
    source = checked_path(ROOT / R19_SOURCE_RELATIVE, root=attempt, require_file=True)
    if source.stat().st_size != R19_SOURCE_BYTES or sha256_file(source) != R19_SOURCE_SHA256:
        raise R24OneShotControllerV3Error("R19 source identity changed")
    return {"manifest_sha256": R19_MANIFEST_SHA256, "file_count": 49, "source_sha256": R19_SOURCE_SHA256}


def _require_inert_authority() -> None:
    if EXECUTION_AUTHORITY_GRANTED is not True:
        raise R24OneShotControllerV3Error("v3 transaction is inert; execution authority is false")


def _safe_make_directory(path: Path) -> Path:
    lexical = inspect_raw_nonreparse(path)
    try:
        relative = lexical.relative_to(inspect_raw_nonreparse(ROOT))
    except ValueError as exc:
        raise R24OneShotControllerV3Error("directory escaped repository") from exc
    cursor = ROOT
    for part in relative.parts:
        cursor = cursor / part
        if os.path.lexists(cursor):
            if not cursor.is_dir() or _is_reparse(cursor):
                raise R24OneShotControllerV3Error("directory contains reparse/non-directory component")
        else:
            cursor.mkdir(exist_ok=False)
    return lexical


def require_absent_raw(path: Path, *, root: Path) -> None:
    checked = checked_path(path, root=root)
    if os.path.lexists(checked) or checked.exists() or checked.is_symlink():
        raise R24OneShotControllerV3Error("output target already exists or is reparsed")


def require_regular_raw(path: Path, *, root: Path) -> None:
    checked = checked_path(path, root=root, require_file=True)
    if checked != path or _is_reparse(checked):
        raise R24OneShotControllerV3Error("artifact is linked or reparsed")


class ExclusiveReservationV3:
    def __init__(self, path: Path, handle: Any, token: str) -> None:
        self.path = path
        self.handle = handle
        self.token = token
        self.closed = False

    @classmethod
    def create(cls, path: Path, token: str) -> "ExclusiveReservationV3":
        if os.name != "nt":
            raise R24OneShotControllerV3Error("Win32 reservation is mandatory")
        require_absent_raw(path, root=path.parent)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
        ]
        kernel32.CreateFileW.restype = wintypes.HANDLE
        kernel32.WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        kernel32.WriteFile.restype = wintypes.BOOL
        kernel32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
        kernel32.FlushFileBuffers.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.CreateFileW(
            str(path), GENERIC_READ_WRITE, FILE_SHARE_READ, None, CREATE_NEW,
            FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, None,
        )
        if handle in (None, wintypes.HANDLE(-1).value):
            raise R24OneShotControllerV3Error("exclusive reservation creation failed")
        payload = canonical_bytes({
            "schema": "kira.avatar.r24.one_shot_candidate_reservation.v3",
            "token": token,
            "controller_pid": os.getpid(),
            "held_no_write_or_delete_share": True,
        })
        buffer = ctypes.create_string_buffer(payload)
        written = wintypes.DWORD()
        if not kernel32.WriteFile(handle, buffer, len(payload), ctypes.byref(written), None) or written.value != len(payload):
            close_ok = bool(kernel32.CloseHandle(handle))
            raise R24OneShotControllerV3Error(f"reservation write failed; handle_closed={close_ok}")
        if not kernel32.FlushFileBuffers(handle):
            close_ok = bool(kernel32.CloseHandle(handle))
            raise R24OneShotControllerV3Error(f"reservation flush failed; handle_closed={close_ok}")
        return cls(path, handle, token)

    def close(self) -> dict[str, object]:
        if self.closed:
            return {"closed": True, "already_closed": True}
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        if not kernel32.CloseHandle(self.handle):
            raise R24OneShotControllerV3Error("reservation handle close failed")
        self.closed = True
        return {"closed": True, "held_through_both_children": True}


def reserve_attempt(author_nonce: str, reopen_nonce: str) -> dict[str, Any]:
    runtime = _safe_make_directory(ROOT / RUNTIME_ROOT_RELATIVE)
    attempt = runtime / ATTEMPT_NAME
    if os.path.lexists(attempt):
        raise R24OneShotControllerV3Error("append-only v3 attempt_01 already exists")
    attempt.mkdir(exist_ok=False)
    token = hashlib.sha256(os.urandom(64)).hexdigest()
    private_root = attempt / f"private_author_{token}"
    staging_root = attempt / "sealed_staging"
    extraction_root = attempt / "fresh_reopen"
    for directory in (private_root, staging_root, extraction_root):
        directory.mkdir(exist_ok=False)
    reservation_path = attempt / RESERVATION_BASENAME
    reservation = ExclusiveReservationV3.create(reservation_path, token)
    paths = {
        "runtime": runtime,
        "attempt": attempt,
        "private_root": private_root,
        "staging_root": staging_root,
        "extraction_root": extraction_root,
        "private_write": private_root / f"blender_write_{author_nonce}.blend",
        "sealed_staging": staging_root / f"candidate_{token}.blend",
        "candidate": attempt / FINAL_CANDIDATE_BASENAME,
        "extraction": extraction_root / f"candidate_extraction_{reopen_nonce}.json",
        "reservation_path": reservation_path,
        "reservation": reservation,
        "reservation_token": token,
        "result": attempt / RESULT_BASENAME,
    }
    for key in ("private_write", "sealed_staging", "candidate", "extraction", "result"):
        require_absent_raw(paths[key], root=attempt)
    return paths


def atomic_no_replace(source: Path, destination: Path, *, root: Path) -> None:
    if os.name != "nt":
        raise R24OneShotControllerV3Error("Win32 no-replace publication is mandatory")
    require_regular_raw(source, root=root)
    require_absent_raw(destination, root=root)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.MoveFileExW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
    kernel32.MoveFileExW.restype = wintypes.BOOL
    if not kernel32.MoveFileExW(str(source), str(destination), 0):
        raise R24OneShotControllerV3Error("atomic no-replace publication failed")
    if os.path.lexists(source):
        raise R24OneShotControllerV3Error("source remained after no-replace publication")
    require_regular_raw(destination, root=root)


class WindowsSuspendedJobNativeV3:
    """Win32 ownership adapter with local cleanup on every create failure."""

    def __init__(self) -> None:
        if os.name != "nt":
            raise R24OneShotControllerV3Error("Win32 suspended Job launch is mandatory")
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k = self.kernel32
        k.CreateProcessW.argtypes = [
            wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
            wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
            ctypes.POINTER(WIN_STARTUPINFO), ctypes.POINTER(WIN_PROCESS_INFORMATION),
        ]
        k.CreateProcessW.restype = wintypes.BOOL
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        k.CreateJobObjectW.restype = wintypes.HANDLE
        k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        k.SetInformationJobObject.restype = wintypes.BOOL
        k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k.AssignProcessToJobObject.restype = wintypes.BOOL
        k.ResumeThread.argtypes = [wintypes.HANDLE]
        k.ResumeThread.restype = wintypes.DWORD
        k.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        k.QueryInformationJobObject.restype = wintypes.BOOL
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.WaitForSingleObject.restype = wintypes.DWORD
        k.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        k.GetExitCodeProcess.restype = wintypes.BOOL
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenProcess.restype = wintypes.HANDLE
        k.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        k.TerminateJobObject.restype = wintypes.BOOL
        k.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        k.TerminateProcess.restype = wintypes.BOOL
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.CloseHandle.restype = wintypes.BOOL

    @staticmethod
    def _new_context() -> dict[str, Any]:
        return {
            "process": None, "thread": None, "pid": None,
            "stdin": None, "stdout": None, "stderr": None,
            "created_suspended": False,
        }

    def _restore_inheritance(self, context: Mapping[str, Any]) -> None:
        for name in ("stdin", "stdout", "stderr"):
            stream = context[name]
            os.set_handle_inheritable(msvcrt.get_osfhandle(stream.fileno()), False)

    def create_suspended(
        self,
        command: Sequence[str],
        environment: Mapping[str, str],
        stdout_path: Path,
        stderr_path: Path,
    ) -> dict[str, Any]:
        context = self._new_context()
        stage = "pre_CreateProcessW"
        try:
            context["stdout"] = stdout_path.open("xb")
            context["stderr"] = stderr_path.open("xb")
            context["stdin"] = open(os.devnull, "rb")
            for name in ("stdin", "stdout", "stderr"):
                stream = context[name]
                os.set_handle_inheritable(msvcrt.get_osfhandle(stream.fileno()), True)
            startup = WIN_STARTUPINFO()
            startup.cb = ctypes.sizeof(startup)
            startup.dwFlags = 0x00000100
            startup.hStdInput = msvcrt.get_osfhandle(context["stdin"].fileno())
            startup.hStdOutput = msvcrt.get_osfhandle(context["stdout"].fileno())
            startup.hStdError = msvcrt.get_osfhandle(context["stderr"].fileno())
            info = WIN_PROCESS_INFORMATION()
            command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(list(command)))
            env_block = ctypes.create_unicode_buffer(
                "\0".join(f"{key}={value}" for key, value in sorted(environment.items())) + "\0\0"
            )
            if not self.kernel32.CreateProcessW(
                str(command[0]), command_line, None, None, True,
                CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW,
                env_block, str(ROOT), ctypes.byref(startup), ctypes.byref(info),
            ):
                raise R24OneShotControllerV3Error("CreateProcessW(CREATE_SUSPENDED) failed")
            # Ownership is recorded immediately; no fallible operation occurs
            # between CreateProcessW success and these assignments.
            context["process"] = info.hProcess
            context["thread"] = info.hThread
            context["pid"] = int(info.dwProcessId)
            context["created_suspended"] = True
            stage = "post_CreateProcessW_inheritability_restore"
            self._restore_inheritance(context)
            return context
        except BaseException as primary:
            cleanup_then_raise(self, context, None, stage, primary)
        raise AssertionError("unreachable")

    def create_configured_job(self) -> Any:
        handle = self.kernel32.CreateJobObjectW(None, None)
        if not handle:
            raise R24OneShotControllerV3Error("CreateJobObjectW failed")
        info = WIN_JOB_EXTENDED_LIMIT()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel32.SetInformationJobObject(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            closed = bool(self.kernel32.CloseHandle(handle))
            if not closed:
                raise R24OneShotCleanupV3Error(
                    "configure_job", R24OneShotControllerV3Error("SetInformationJobObject failed"),
                    {"errors": ["unclosed_job_handle"], "cleanup_complete": False},
                )
            raise R24OneShotControllerV3Error("kill-on-close Job configuration failed")
        return handle

    def assign(self, job: Any, process: Any) -> None:
        if not self.kernel32.AssignProcessToJobObject(job, process):
            raise R24OneShotControllerV3Error("suspended child Job assignment failed")

    def resume(self, thread: Any) -> int:
        previous = int(self.kernel32.ResumeThread(thread))
        if previous != 1:
            raise R24OneShotControllerV3Error("primary thread did not resume from exactly one suspend")
        return previous

    def query_job_pids(self, job: Any) -> list[int]:
        info = WIN_JOB_PID_LIST()
        returned = wintypes.DWORD()
        if not self.kernel32.QueryInformationJobObject(job, 3, ctypes.byref(info), ctypes.sizeof(info), ctypes.byref(returned)):
            raise R24OneShotControllerV3Error("Job PID query failed")
        if info.NumberOfProcessIdsInList > 1024:
            raise R24OneShotControllerV3Error("Job PID inventory exceeded bound")
        return sorted(int(info.ProcessIdList[index]) for index in range(info.NumberOfProcessIdsInList))

    def wait_direct_and_tree(self, context: Mapping[str, Any], job: Any, timeout_seconds: int) -> dict[str, object]:
        deadline = time.monotonic() + timeout_seconds
        observed: set[int] = {int(context["pid"])}
        while True:
            observed.update(self.query_job_pids(job))
            wait = int(self.kernel32.WaitForSingleObject(context["process"], 50))
            if wait == WAIT_OBJECT_0:
                break
            if wait != WAIT_TIMEOUT:
                raise R24OneShotControllerV3Error("direct child wait failed")
            if time.monotonic() >= deadline:
                raise R24OneShotControllerV3Error("direct child timed out")
        while True:
            active = self.query_job_pids(job)
            observed.update(active)
            if not active:
                break
            if time.monotonic() >= deadline:
                raise R24OneShotControllerV3Error("Job tree did not become quiescent")
            time.sleep(0.025)
        exit_code = wintypes.DWORD()
        if not self.kernel32.GetExitCodeProcess(context["process"], ctypes.byref(exit_code)):
            raise R24OneShotControllerV3Error("GetExitCodeProcess failed")
        return {
            "direct_exit_observed": True,
            "exit_code": int(exit_code.value),
            "observed_pids": sorted(observed),
            "active_before_close": [],
        }

    def _close_owned(self, context: Mapping[str, Any], job: Any | None) -> dict[str, object]:
        errors: list[str] = []
        closed = {"thread": False, "process": False, "job": job is None, "streams": []}
        for name in ("stdin", "stdout", "stderr"):
            stream = context.get(name)
            if stream is None or stream.closed:
                closed["streams"].append(name)
                continue
            try:
                stream.close()
                closed["streams"].append(name)
            except BaseException as exc:
                errors.append(f"close_{name}:{type(exc).__name__}:{exc}")
        for name in ("thread", "process"):
            handle = context.get(name)
            if handle is None:
                closed[name] = True
            elif self.kernel32.CloseHandle(handle):
                closed[name] = True
                context[name] = None
            else:
                errors.append(f"CloseHandle_{name}_failed")
        if job is not None:
            if self.kernel32.CloseHandle(job):
                closed["job"] = True
            else:
                errors.append("CloseHandle_job_failed")
        return {
            "errors": errors,
            "closed": closed,
            "cleanup_complete": not errors and all((closed["thread"], closed["process"], closed["job"])) and len(closed["streams"]) == 3,
        }

    def failure_cleanup(self, context: Mapping[str, Any], job: Any | None) -> dict[str, object]:
        errors: list[str] = []
        report: dict[str, object] = {
            "pid": context.get("pid"),
            "terminate_job_attempted": job is not None,
            "terminate_process_attempted": context.get("process") is not None,
            "direct_wait_observed": context.get("process") is None,
            "job_empty_observed": job is None,
        }
        if job is not None and not self.kernel32.TerminateJobObject(job, 125):
            errors.append("TerminateJobObject_failed")
        process = context.get("process")
        if process is not None:
            initial = int(self.kernel32.WaitForSingleObject(process, 0))
            if initial == WAIT_TIMEOUT and not self.kernel32.TerminateProcess(process, 125):
                errors.append("TerminateProcess_failed")
            elif initial not in (WAIT_TIMEOUT, WAIT_OBJECT_0):
                errors.append("initial_process_wait_failed")
            final_wait = int(self.kernel32.WaitForSingleObject(process, 30_000))
            report["direct_wait_observed"] = final_wait == WAIT_OBJECT_0
            if final_wait != WAIT_OBJECT_0:
                errors.append("direct_process_wait_timeout_or_failure")
        if job is not None:
            try:
                deadline = time.monotonic() + 30.0
                active = self.query_job_pids(job)
                while active and time.monotonic() < deadline:
                    time.sleep(0.025)
                    active = self.query_job_pids(job)
                report["job_empty_observed"] = not active
                if active:
                    errors.append("job_tree_not_empty")
            except BaseException as exc:
                errors.append(f"job_cleanup_query:{type(exc).__name__}:{exc}")
        close = self._close_owned(context, job)
        errors.extend(close["errors"])
        report.update({"close": close, "errors": errors})
        report["cleanup_complete"] = (
            not errors and report["direct_wait_observed"] is True
            and report["job_empty_observed"] is True and close["cleanup_complete"] is True
        )
        return report

    def success_close(self, context: Mapping[str, Any], job: Any) -> dict[str, object]:
        return self._close_owned(context, job)

    def active_system_pids(self, pids: Sequence[int]) -> list[int]:
        """Independently prove whether observed PIDs still name live processes.

        This deliberately does not depend on Job membership or ``tasklist``.
        On Windows an exited process object disappears after its final handle is
        closed; ``OpenProcess`` then reports ``ERROR_INVALID_PARAMETER``.  If a
        PID has already been reused, the zero-time wait conservatively reports
        that new live process as active and the transaction fails closed.
        """
        active: list[int] = []
        for pid in sorted(set(int(item) for item in pids)):
            ctypes.set_last_error(0)
            handle = self.kernel32.OpenProcess(
                SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, pid,
            )
            if not handle:
                error = ctypes.get_last_error()
                if error == ERROR_INVALID_PARAMETER:
                    continue
                raise R24OneShotControllerV3Error(
                    f"post-close OpenProcess inventory failed for PID {pid}: WinError {error}"
                )
            wait_result: int | None = None
            close_ok = False
            try:
                wait_result = int(self.kernel32.WaitForSingleObject(handle, 0))
            finally:
                close_ok = bool(self.kernel32.CloseHandle(handle))
            if not close_ok:
                raise R24OneShotControllerV3Error(
                    f"post-close inventory handle close failed for PID {pid}"
                )
            if wait_result == WAIT_TIMEOUT:
                active.append(pid)
            elif wait_result != WAIT_OBJECT_0:
                raise R24OneShotControllerV3Error(
                    f"post-close PID wait failed for PID {pid}: {wait_result}"
                )
        return active


def raise_with_cleanup(stage: str, primary: BaseException, cleanup: Mapping[str, object]) -> None:
    if cleanup.get("cleanup_complete") is not True or cleanup.get("errors"):
        raise R24OneShotCleanupV3Error(stage, primary, cleanup) from primary
    raise R24OneShotOwnedFailureV3Error(stage, primary, cleanup) from primary


def cleanup_then_raise(
    native: WindowsSuspendedJobNativeV3,
    context: Mapping[str, Any],
    job: Any | None,
    stage: str,
    primary: BaseException,
) -> None:
    """Run owned cleanup and propagate both primary and cleanup failures."""
    try:
        cleanup = native.failure_cleanup(context, job)
    except BaseException as cleanup_error:
        report = {
            "pid": context.get("pid"),
            "cleanup_complete": False,
            "errors": [
                f"cleanup_raised:{type(cleanup_error).__name__}:{cleanup_error}"
            ],
            "cleanup_exception_type": type(cleanup_error).__name__,
            "cleanup_exception_text": str(cleanup_error),
        }
        raise R24OneShotCleanupV3Error(stage, primary, report) from primary
    raise_with_cleanup(stage, primary, cleanup)


def _exclusive_json(path: Path, value: object, *, root: Path) -> None:
    require_absent_raw(path, root=root)
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    require_regular_raw(path, root=root)


def child_environment(nonce: str) -> dict[str, str]:
    allowed = (
        "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERNAME", "USERPROFILE",
        "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA", "APPDATA", "PATH",
    )
    value = {name: os.environ[name] for name in allowed if os.environ.get(name)}
    value.update({"PYTHONNOUSERSITE": "1", "KIRA_R24_ONE_SHOT_V3_CHILD_NONCE": nonce})
    return value


CHILD_FIELDS = {
    "schema", "evidence_origin", "role", "nonce", "invocation_index",
    "command_sha256", "pid", "created_suspended", "job_created_configured",
    "assigned_before_resume", "resume_previous_suspend_count", "resumed",
    "direct_exit_observed", "exit_code", "job_observed_pids",
    "job_active_pids_before_close", "success_close", "post_close_active_pids",
    "tree_quiescent_after_close", "stdout", "stderr",
}


def _run_owned_child(
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
    boundary_root: Path,
    native: WindowsSuspendedJobNativeV3,
) -> dict[str, object]:
    if role not in {"author", "fresh_reopen", "integration_probe"}:
        raise R24OneShotControllerV3Error("child role is invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", nonce):
        raise R24OneShotControllerV3Error("child nonce is invalid")
    if not isinstance(invocation_index, int) or isinstance(invocation_index, bool) or invocation_index < 1:
        raise R24OneShotControllerV3Error("child invocation index is invalid")
    if not command or any(not isinstance(item, str) or not item for item in command):
        raise R24OneShotControllerV3Error("child command is invalid")
    stdout_path = checked_path(stdout_path, root=boundary_root)
    stderr_path = checked_path(stderr_path, root=boundary_root)
    require_absent_raw(stdout_path, root=boundary_root)
    require_absent_raw(stderr_path, root=boundary_root)
    context: dict[str, Any] | None = None
    job: Any | None = None
    stage = "create_suspended"
    try:
        context = native.create_suspended(command, environment, stdout_path, stderr_path)
        stage = "create_configured_job"
        job = native.create_configured_job()
        stage = "assign_before_resume"
        native.assign(job, context["process"])
        if job_gate_path is not None:
            gate = checked_path(job_gate_path, root=boundary_root)
            _exclusive_json(gate, {
                "schema": "kira.avatar.r24.suspended_child_job_gate.v3",
                "role": role, "nonce": nonce, "parent_pid": os.getpid(),
                "child_pid": int(context["pid"]), "created_suspended": True,
                "job_configured": True, "assigned_before_resume": True,
                "resume_authorized": True,
            }, root=boundary_root)
        stage = "resume"
        resume_count = native.resume(context["thread"])
        stage = "wait_direct_and_tree"
        wait = native.wait_direct_and_tree(context, job, timeout_seconds)
        stage = "close_success_handles"
        close = native.success_close(context, job)
        if close.get("cleanup_complete") is not True or close.get("errors"):
            raise R24OneShotCleanupV3Error(stage, R24OneShotControllerV3Error("success handle close failed"), close)
        job = None
        stage = "independent_post_close_pid_inventory"
        active = native.active_system_pids(wait["observed_pids"])
        if active:
            raise R24OneShotControllerV3Error("child tree remained active after Job close")
        record = {
            "schema": "kira.avatar.r24.suspended_owned_child.v3",
            "evidence_origin": "WIN32_DIRECT_OBSERVATION_V3",
            "role": role, "nonce": nonce, "invocation_index": invocation_index,
            "command_sha256": canonical_sha256(list(command)), "pid": int(context["pid"]),
            "created_suspended": True, "job_created_configured": True,
            "assigned_before_resume": True, "resume_previous_suspend_count": resume_count,
            "resumed": True, "direct_exit_observed": wait["direct_exit_observed"],
            "exit_code": wait["exit_code"], "job_observed_pids": wait["observed_pids"],
            "job_active_pids_before_close": wait["active_before_close"],
            "success_close": close, "post_close_active_pids": active,
            "tree_quiescent_after_close": True,
            "stdout": {"path": str(stdout_path), "bytes": stdout_path.stat().st_size, "sha256": sha256_file(stdout_path)},
            "stderr": {"path": str(stderr_path), "bytes": stderr_path.stat().st_size, "sha256": sha256_file(stderr_path)},
        }
        return record
    except BaseException as primary:
        if context is None and job is None:
            raise
        cleanup_then_raise(native, context, job, stage, primary)
    raise AssertionError("unreachable")


def run_production_child(
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
    boundary_root: Path,
) -> dict[str, object]:
    """Production path: no native/evidence injection parameter exists."""
    return _run_owned_child(
        command, environment, role=role, nonce=nonce,
        invocation_index=invocation_index, stdout_path=stdout_path,
        stderr_path=stderr_path, timeout_seconds=timeout_seconds,
        job_gate_path=job_gate_path, boundary_root=boundary_root,
        native=WindowsSuspendedJobNativeV3(),
    )


def validate_child_record(
    value: object,
    *,
    role: str,
    nonce: str,
    index: int,
    command: Sequence[str],
    stdout_path: Path,
    stderr_path: Path,
    boundary_root: Path,
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != CHILD_FIELDS:
        raise R24OneShotControllerV3Error("child evidence field inventory changed")
    exact = {
        "schema": "kira.avatar.r24.suspended_owned_child.v3",
        "evidence_origin": "WIN32_DIRECT_OBSERVATION_V3",
        "role": role, "nonce": nonce,
        "command_sha256": canonical_sha256(list(command)),
    }
    for key, expected in exact.items():
        if value.get(key) != expected:
            raise R24OneShotControllerV3Error(f"child evidence rejected:{key}")
    for key, expected in (("invocation_index", index), ("resume_previous_suspend_count", 1), ("exit_code", 0)):
        item = value.get(key)
        if not isinstance(item, int) or isinstance(item, bool) or item != expected:
            raise R24OneShotControllerV3Error(f"child evidence rejected:{key}")
    for key in ("created_suspended", "job_created_configured", "assigned_before_resume", "resumed", "direct_exit_observed", "tree_quiescent_after_close"):
        if value.get(key) is not True:
            raise R24OneShotControllerV3Error(f"child evidence rejected:{key}")
    if value.get("job_active_pids_before_close") != [] or value.get("post_close_active_pids") != []:
        raise R24OneShotControllerV3Error("child evidence contains an active PID")
    pid = value.get("pid")
    observed = value.get("job_observed_pids")
    if not isinstance(pid, int) or isinstance(pid, bool) or pid < 1:
        raise R24OneShotControllerV3Error("child evidence PID is invalid")
    if not isinstance(observed, list) or pid not in observed or len(observed) != len(set(observed)):
        raise R24OneShotControllerV3Error("child Job PID evidence is invalid")
    close = value.get("success_close")
    if not isinstance(close, dict) or close.get("cleanup_complete") is not True or close.get("errors") != []:
        raise R24OneShotControllerV3Error("child close evidence is invalid")
    for name, expected_path in (("stdout", stdout_path), ("stderr", stderr_path)):
        stream = value.get(name)
        if not isinstance(stream, dict) or set(stream) != {"path", "bytes", "sha256"}:
            raise R24OneShotControllerV3Error(f"child {name} evidence is invalid")
        path = checked_path(str(stream["path"]), root=boundary_root, require_file=True)
        if path != expected_path or path.stat().st_size != stream["bytes"] or sha256_file(path) != stream["sha256"]:
            raise R24OneShotControllerV3Error(f"child {name} artifact identity changed")
    return value


def derive_child_counts(records: Sequence[Mapping[str, object]]) -> dict[str, int]:
    if len(records) != 2:
        raise R24OneShotControllerV3Error("exactly two child records are required")
    if [row.get("role") for row in records] != ["author", "fresh_reopen"]:
        raise R24OneShotControllerV3Error("child roles/order changed")
    if [row.get("invocation_index") for row in records] != [1, 2]:
        raise R24OneShotControllerV3Error("child invocation order changed")
    for field in ("pid", "nonce", "command_sha256"):
        if len({row.get(field) for row in records}) != 2:
            raise R24OneShotControllerV3Error(f"child identity is not distinct:{field}")
    counts = Counter(str(row["role"]) for row in records)
    return {"author": counts["author"], "fresh_reopen": counts["fresh_reopen"], "total": len(records)}


def ensure_no_blender_process() -> dict[str, object]:
    completed = subprocess.run(
        ["tasklist.exe", "/FO", "CSV", "/NH"], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
        check=False, timeout=20,
    )
    if completed.returncode != 0:
        raise R24OneShotControllerV3Error("bounded Blender inventory failed")
    try:
        rows = list(csv.reader(io.StringIO(completed.stdout.decode("utf-8", errors="strict"))))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise R24OneShotControllerV3Error("Blender inventory is not parseable") from exc
    if any(row and row[0].lower() in {"blender.exe", "blender-launcher.exe"} for row in rows):
        raise R24OneShotControllerV3Error("a Blender process is already active")
    return {"inventory_command": "tasklist.exe /FO CSV /NH", "blender_process_count": 0}


def author_command(paths: Mapping[str, Any], dependencies: Mapping[str, Mapping[str, object]], nonce: str) -> list[str]:
    return [
        str(dependencies["blender"]["path"]), *SAFETY_FLAGS,
        "--python", str(dependencies["author_worker_v3"]["path"]), "--",
        "--source", str(checked_path(ROOT / R19_SOURCE_RELATIVE, root=ROOT, require_file=True)),
        "--private-write-output", str(paths["private_write"]),
        "--sealed-staging-output", str(paths["sealed_staging"]),
        "--reservation", str(paths["reservation_path"]),
        "--reservation-token", str(paths["reservation_token"]),
        "--job-gate", str(paths["attempt"] / f"author_job_gate_{nonce}.json"),
        "--role", "author", "--child-nonce", nonce, "--execute-authoring",
    ]


def reopen_command(paths: Mapping[str, Any], dependencies: Mapping[str, Mapping[str, object]], nonce: str, digest: str) -> list[str]:
    return [
        str(dependencies["blender"]["path"]), *SAFETY_FLAGS,
        str(paths["candidate"]),
        "--python", str(dependencies["read_only_extractor_r7"]["path"]), "--",
        "--candidate", str(paths["candidate"]), "--candidate-sha256", digest,
        "--extractor-sha256", str(dependencies["read_only_extractor_r7"]["sha256"]),
        "--intersection-helper-sha256", str(dependencies["intersection_helper"]["sha256"]),
        "--nonce", nonce, "--output", str(paths["extraction"]),
    ]


def _load_gate(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("_kira_r24_r7_gate_v3", path)
    if spec is None or spec.loader is None:
        raise R24OneShotControllerV3Error("R7 gate cannot be imported")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "validate_extraction_envelope", None)):
        raise R24OneShotControllerV3Error("R7 extraction-envelope validator is absent")
    return module


def execute_transaction() -> dict[str, object]:
    """Non-injectable production transaction; authority currently fails first."""
    _require_inert_authority()
    package = verify_r19_package()
    dependencies = verify_dependencies()
    process_inventory = ensure_no_blender_process()
    author_nonce = hashlib.sha256(os.urandom(64)).hexdigest()
    reopen_nonce = hashlib.sha256(os.urandom(64)).hexdigest()
    paths = reserve_attempt(author_nonce, reopen_nonce)
    reservation = paths["reservation"]
    records: list[dict[str, object]] = []
    source = checked_path(ROOT / R19_SOURCE_RELATIVE, root=ROOT, require_file=True)
    source_before = sha256_file(source)
    try:
        author = author_command(paths, dependencies, author_nonce)
        author_stdout = paths["attempt"] / "author_v3.stdout.log"
        author_stderr = paths["attempt"] / "author_v3.stderr.log"
        author_record = run_production_child(
            author, child_environment(author_nonce), role="author", nonce=author_nonce,
            invocation_index=1, stdout_path=author_stdout, stderr_path=author_stderr,
            timeout_seconds=1800,
            job_gate_path=paths["attempt"] / f"author_job_gate_{author_nonce}.json",
            boundary_root=paths["attempt"],
        )
        validate_child_record(
            author_record, role="author", nonce=author_nonce, index=1,
            command=author, stdout_path=author_stdout, stderr_path=author_stderr,
            boundary_root=paths["attempt"],
        )
        records.append(author_record)
        require_absent_raw(paths["private_write"], root=paths["attempt"])
        require_regular_raw(paths["sealed_staging"], root=paths["attempt"])
        staging_digest = sha256_file(paths["sealed_staging"])
        atomic_no_replace(paths["sealed_staging"], paths["candidate"], root=paths["attempt"])
        candidate_digest = sha256_file(paths["candidate"])
        if candidate_digest != staging_digest:
            raise R24OneShotControllerV3Error("final candidate bytes changed during publication")
        reopen = reopen_command(paths, dependencies, reopen_nonce, candidate_digest)
        reopen_stdout = paths["extraction_root"] / "fresh_reopen_v3.stdout.log"
        reopen_stderr = paths["extraction_root"] / "fresh_reopen_v3.stderr.log"
        reopen_record = run_production_child(
            reopen, child_environment(reopen_nonce), role="fresh_reopen", nonce=reopen_nonce,
            invocation_index=2, stdout_path=reopen_stdout, stderr_path=reopen_stderr,
            timeout_seconds=1800, job_gate_path=None, boundary_root=paths["attempt"],
        )
        validate_child_record(
            reopen_record, role="fresh_reopen", nonce=reopen_nonce, index=2,
            command=reopen, stdout_path=reopen_stdout, stderr_path=reopen_stderr,
            boundary_root=paths["attempt"],
        )
        records.append(reopen_record)
        counts = derive_child_counts(records)
        require_regular_raw(paths["candidate"], root=paths["attempt"])
        require_regular_raw(paths["extraction"], root=paths["attempt"])
        if sha256_file(paths["candidate"]) != candidate_digest or sha256_file(source) != source_before:
            raise R24OneShotControllerV3Error("candidate or preserved source changed across reopen")
        snapshot = json.loads(paths["extraction"].read_text(encoding="utf-8"))
        gate = _load_gate(Path(str(dependencies["artifact_gate_r7"]["path"])))
        failures = gate.validate_extraction_envelope(
            snapshot, nonce=reopen_nonce, candidate=paths["candidate"],
            candidate_sha256=candidate_digest,
            extractor_sha256=str(dependencies["read_only_extractor_r7"]["sha256"]),
            intersection_helper_sha256=str(dependencies["intersection_helper"]["sha256"]),
        )
        if failures:
            raise R24OneShotControllerV3Error("R7 extraction envelope rejected")
        reservation_close = reservation.close()
        result = {
            "schema": "kira.avatar.r24.one_shot_author_transaction.v3",
            "status": "FRESH_REOPEN_CAPTURED_R7_FULL_EVALUATION_REQUIRED_NOT_ACCEPTED",
            "r19_package": package, "process_inventory": process_inventory,
            "children": records, "invocation_counts_derived": counts,
            "retry_count_derived": max(0, counts["total"] - 2),
            "reservation_close": reservation_close,
            "candidate": {"path": str(paths["candidate"]), "bytes": paths["candidate"].stat().st_size, "sha256": candidate_digest},
            "extraction": {"path": str(paths["extraction"]), "bytes": paths["extraction"].stat().st_size, "sha256": sha256_file(paths["extraction"])},
            "candidate_accepted": False, "runtime_eligible": False,
        }
        _exclusive_json(paths["result"], result, root=paths["attempt"])
        return result
    finally:
        if not reservation.closed:
            reservation.close()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-once", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.execute_once:
        raise R24OneShotControllerV3Error("--execute-once is required but never sufficient")
    raise R24OneShotControllerV3Error("v3 remains static: R7 bindings and execution authority are absent")


if __name__ == "__main__":
    raise SystemExit(main())
