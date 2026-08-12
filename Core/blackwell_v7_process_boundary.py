"""Spawn-safe JSONL worker supervisor for the inactive Blackwell v7 candidate.

No callback or model object crosses this boundary.  A single persistent child
owns every model/backend object and receives only closed JSON commands.  A
command deadline kills the entire worker process group/job instead of leaving
an unbounded Python thread behind.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import math
import os
import queue
import signal
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Iterable, Mapping


PROTOCOL = "kira_blackwell_v7_jsonl_1"


class V7ProcessBoundaryError(RuntimeError):
    pass


class V7ProcessTimeout(V7ProcessBoundaryError):
    pass


def _reject_json_constant(token: str) -> None:
    raise V7ProcessBoundaryError(f"non-finite JSON constant is forbidden: {token}")


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if not isinstance(key, str) or key in result:
            raise V7ProcessBoundaryError("JSON object keys must be unique strings")
        result[key] = value
    return result


def _validate_closed_finite_json(value: Any, *, depth: int = 0) -> None:
    if depth > 64:
        raise V7ProcessBoundaryError("closed JSON nesting exceeds 64 levels")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise V7ProcessBoundaryError("closed JSON contains a non-finite number")
        return
    if isinstance(value, list):
        for item in value:
            _validate_closed_finite_json(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise V7ProcessBoundaryError("closed JSON keys must be strings")
        for item in value.values():
            _validate_closed_finite_json(item, depth=depth + 1)
        return
    raise V7ProcessBoundaryError(f"closed JSON contains unsupported type: {type(value).__name__}")


def strict_finite_json_loads(raw: bytes | str) -> Any:
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        value = json.loads(
            text,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_closed_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise V7ProcessBoundaryError(f"malformed strict finite JSON: {exc}") from exc
    _validate_closed_finite_json(value)
    return value


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class _FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]


class _BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("dwFileAttributes", ctypes.c_ulong),
        ("ftCreationTime", _FILETIME),
        ("ftLastAccessTime", _FILETIME),
        ("ftLastWriteTime", _FILETIME),
        ("dwVolumeSerialNumber", ctypes.c_ulong),
        ("nFileSizeHigh", ctypes.c_ulong),
        ("nFileSizeLow", ctypes.c_ulong),
        ("nNumberOfLinks", ctypes.c_ulong),
        ("nFileIndexHigh", ctypes.c_ulong),
        ("nFileIndexLow", ctypes.c_ulong),
    ]


def _filetime_integer(value: _FILETIME) -> int:
    return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)


def _windows_executable_file_identity(path: Path) -> dict[str, Any]:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
    ]
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.GetFileInformationByHandle.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(_BY_HANDLE_FILE_INFORMATION),
    ]
    kernel32.GetFileInformationByHandle.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    handle = kernel32.CreateFileW(
        str(path),
        0x0080,
        0x00000001 | 0x00000002 | 0x00000004,
        None,
        3,
        0x00000080,
        None,
    )
    if handle in (None, 0, ctypes.c_void_p(-1).value):
        raise V7ProcessBoundaryError(
            f"CreateFileW(executable) failed: {ctypes.get_last_error()}"
        )
    try:
        info = _BY_HANDLE_FILE_INFORMATION()
        if not kernel32.GetFileInformationByHandle(handle, ctypes.byref(info)):
            raise V7ProcessBoundaryError(
                f"GetFileInformationByHandle failed: {ctypes.get_last_error()}"
            )
        return {
            "executable_size": (int(info.nFileSizeHigh) << 32) | int(info.nFileSizeLow),
            "executable_volume_serial": int(info.dwVolumeSerialNumber),
            "executable_file_index": (
                (int(info.nFileIndexHigh) << 32) | int(info.nFileIndexLow)
            ),
        }
    finally:
        kernel32.CloseHandle(handle)


def process_identity_from_handle(process_handle: int, pid: int) -> dict[str, Any]:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise V7ProcessBoundaryError("process identity PID must be positive")
    if os.name == "nt":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetProcessTimes.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_FILETIME),
            ctypes.POINTER(_FILETIME),
            ctypes.POINTER(_FILETIME),
            ctypes.POINTER(_FILETIME),
        ]
        kernel32.GetProcessTimes.restype = ctypes.c_int
        kernel32.QueryFullProcessImageNameW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_wchar_p,
            ctypes.POINTER(ctypes.c_ulong),
        ]
        kernel32.QueryFullProcessImageNameW.restype = ctypes.c_int
        creation = _FILETIME()
        exit_time = _FILETIME()
        kernel_time = _FILETIME()
        user_time = _FILETIME()
        handle = ctypes.c_void_p(int(process_handle))
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel_time),
            ctypes.byref(user_time),
        ):
            raise V7ProcessBoundaryError(f"GetProcessTimes failed: {ctypes.get_last_error()}")
        capacity = ctypes.c_ulong(32768)
        buffer = ctypes.create_unicode_buffer(capacity.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(capacity)):
            raise V7ProcessBoundaryError(
                f"QueryFullProcessImageNameW failed: {ctypes.get_last_error()}"
            )
        executable = Path(buffer.value).resolve(strict=True)
        file_identity = _windows_executable_file_identity(executable)
        identity = {
            "pid": pid,
            "os_creation_token": _filetime_integer(creation),
            "executable_path": str(executable),
            "executable_sha256": _sha256_path(executable),
            **file_identity,
        }
    else:
        executable = Path(f"/proc/{pid}/exe").resolve(strict=True)
        stat_fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
        file_stat = executable.stat()
        identity = {
            "pid": pid,
            "os_creation_token": int(stat_fields[21]),
            "executable_path": str(executable),
            "executable_sha256": _sha256_path(executable),
            "executable_size": int(file_stat.st_size),
            "executable_volume_serial": int(file_stat.st_dev),
            "executable_file_index": int(file_stat.st_ino),
        }
    expected = {
        "pid",
        "os_creation_token",
        "executable_path",
        "executable_sha256",
        "executable_size",
        "executable_volume_serial",
        "executable_file_index",
    }
    if (
        set(identity) != expected
        or identity["os_creation_token"] <= 0
        or identity["executable_size"] <= 0
        or len(identity["executable_sha256"]) != 64
    ):
        raise V7ProcessBoundaryError("durable process identity is incomplete")
    return identity


def current_process_identity() -> dict[str, Any]:
    if os.name == "nt":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        return process_identity_from_handle(int(kernel32.GetCurrentProcess()), os.getpid())
    return process_identity_from_handle(os.getpid(), os.getpid())


def process_identity_digest(identity: Mapping[str, Any]) -> str:
    return hashlib.sha256(_closed_json_bytes(dict(identity), 65536)).hexdigest()


def _finite_positive(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise V7ProcessBoundaryError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise V7ProcessBoundaryError(f"{label} must be positive and finite")
    return result


def _closed_json_bytes(value: Any, maximum_bytes: int) -> bytes:
    _validate_closed_finite_json(value)
    try:
        payload = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise V7ProcessBoundaryError(f"request is not closed finite JSON: {exc}") from exc
    if not payload or len(payload) > maximum_bytes or b"\n" in payload or b"\r" in payload:
        raise V7ProcessBoundaryError("request exceeds the closed JSONL bound")
    return payload


class _WindowsJob:
    """Windows Job Object with kill-on-close; construction fails closed."""

    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
    JobObjectExtendedLimitInformation = 9

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class _BASIC_LIMIT(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", ctypes.c_ulong),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.c_ulong),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", ctypes.c_ulong),
            ("SchedulingClass", ctypes.c_ulong),
        ]

    class _EXTENDED_LIMIT(ctypes.Structure):
        pass

    _EXTENDED_LIMIT._fields_ = [
        ("BasicLimitInformation", _BASIC_LIMIT),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]

    def __init__(self, process_handle: int, job_memory_limit_bytes: int) -> None:
        if (
            isinstance(job_memory_limit_bytes, bool)
            or not isinstance(job_memory_limit_bytes, int)
            or job_memory_limit_bytes <= 0
        ):
            raise V7ProcessBoundaryError("Windows job memory limit must be a positive integer")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
        kernel32.CreateJobObjectW.restype = ctypes.c_void_p
        kernel32.SetInformationJobObject.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_ulong,
        ]
        kernel32.SetInformationJobObject.restype = ctypes.c_int
        kernel32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        kernel32.AssignProcessToJobObject.restype = ctypes.c_int
        kernel32.TerminateJobObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        kernel32.TerminateJobObject.restype = ctypes.c_int
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int
        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            raise V7ProcessBoundaryError(f"CreateJobObjectW failed: {ctypes.get_last_error()}")
        self._kernel32 = kernel32
        self.handle = handle
        self.job_memory_limit_bytes = job_memory_limit_bytes
        self.assignment_proof: dict[str, Any] | None = None
        try:
            info = self._EXTENDED_LIMIT()
            info.BasicLimitInformation.LimitFlags = (
                self.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | self.JOB_OBJECT_LIMIT_JOB_MEMORY
            )
            info.JobMemoryLimit = job_memory_limit_bytes
            if not kernel32.SetInformationJobObject(
                handle,
                self.JobObjectExtendedLimitInformation,
                ctypes.byref(info),
                ctypes.sizeof(info),
            ):
                raise V7ProcessBoundaryError(
                    f"SetInformationJobObject failed: {ctypes.get_last_error()}"
                )
            if not kernel32.AssignProcessToJobObject(handle, ctypes.c_void_p(process_handle)):
                raise V7ProcessBoundaryError(
                    f"AssignProcessToJobObject failed: {ctypes.get_last_error()}"
                )
            self.assignment_proof = self.verify(process_handle)
        except Exception:
            kernel32.CloseHandle(handle)
            self.handle = None
            raise

    def verify(self, process_handle: int) -> dict[str, Any]:
        self._kernel32.IsProcessInJob.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int),
        ]
        self._kernel32.IsProcessInJob.restype = ctypes.c_int
        self._kernel32.QueryInformationJobObject.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong),
        ]
        self._kernel32.QueryInformationJobObject.restype = ctypes.c_int
        assigned = ctypes.c_int()
        if not self._kernel32.IsProcessInJob(
            ctypes.c_void_p(process_handle), self.handle, ctypes.byref(assigned)
        ):
            raise V7ProcessBoundaryError(f"IsProcessInJob failed: {ctypes.get_last_error()}")
        info = self._EXTENDED_LIMIT()
        returned = ctypes.c_ulong()
        if not self._kernel32.QueryInformationJobObject(
            self.handle,
            self.JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
            ctypes.byref(returned),
        ):
            raise V7ProcessBoundaryError(
                f"QueryInformationJobObject failed: {ctypes.get_last_error()}"
            )
        required_flags = self.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | self.JOB_OBJECT_LIMIT_JOB_MEMORY
        if (
            assigned.value != 1
            or (info.BasicLimitInformation.LimitFlags & required_flags) != required_flags
            or int(info.JobMemoryLimit) != self.job_memory_limit_bytes
        ):
            raise V7ProcessBoundaryError("Windows Job assignment/limits were not proven")
        return {
            "assigned_before_resume": True,
            "kill_on_close": True,
            "job_memory_limit_bytes": int(info.JobMemoryLimit),
            "limit_flags": int(info.BasicLimitInformation.LimitFlags),
        }

    def terminate(self) -> None:
        if self.handle and not self._kernel32.TerminateJobObject(self.handle, 1):
            raise V7ProcessBoundaryError(
                f"TerminateJobObject failed: {ctypes.get_last_error()}"
            )

    def close(self) -> None:
        if self.handle:
            self._kernel32.CloseHandle(self.handle)
            self.handle = None


class _THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_ulong),
        ("cntUsage", ctypes.c_ulong),
        ("th32ThreadID", ctypes.c_ulong),
        ("th32OwnerProcessID", ctypes.c_ulong),
        ("tpBasePri", ctypes.c_long),
        ("tpDeltaPri", ctypes.c_long),
        ("dwFlags", ctypes.c_ulong),
    ]


def _resume_windows_suspended_process(pid: int) -> list[int]:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [ctypes.c_ulong, ctypes.c_ulong]
    kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    kernel32.Thread32First.argtypes = [ctypes.c_void_p, ctypes.POINTER(_THREADENTRY32)]
    kernel32.Thread32First.restype = ctypes.c_int
    kernel32.Thread32Next.argtypes = [ctypes.c_void_p, ctypes.POINTER(_THREADENTRY32)]
    kernel32.Thread32Next.restype = ctypes.c_int
    kernel32.OpenThread.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel32.OpenThread.restype = ctypes.c_void_p
    kernel32.ResumeThread.argtypes = [ctypes.c_void_p]
    kernel32.ResumeThread.restype = ctypes.c_ulong
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000004, 0)
    if snapshot in (None, 0, ctypes.c_void_p(-1).value):
        raise V7ProcessBoundaryError(
            f"CreateToolhelp32Snapshot failed: {ctypes.get_last_error()}"
        )
    thread_ids: list[int] = []
    try:
        entry = _THREADENTRY32()
        entry.dwSize = ctypes.sizeof(entry)
        available = kernel32.Thread32First(snapshot, ctypes.byref(entry))
        while available:
            if int(entry.th32OwnerProcessID) == pid:
                thread_ids.append(int(entry.th32ThreadID))
            entry.dwSize = ctypes.sizeof(entry)
            available = kernel32.Thread32Next(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    if len(thread_ids) != 1:
        raise V7ProcessBoundaryError(
            f"suspended worker must have exactly one initial thread, observed {len(thread_ids)}"
        )
    handle = kernel32.OpenThread(0x0002 | 0x0800, False, thread_ids[0])
    if not handle:
        raise V7ProcessBoundaryError(f"OpenThread failed: {ctypes.get_last_error()}")
    try:
        previous = int(kernel32.ResumeThread(handle))
        if previous != 1:
            raise V7ProcessBoundaryError(
                f"initial worker thread suspend count was not exactly one: {previous}"
            )
    finally:
        kernel32.CloseHandle(handle)
    return thread_ids


def _cancel_synchronous_writer(native_thread_id: int) -> dict[str, Any]:
    if os.name != "nt":
        return {"attempted": False, "succeeded": False, "reason": "not_windows"}
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenThread.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel32.OpenThread.restype = ctypes.c_void_p
    kernel32.CancelSynchronousIo.argtypes = [ctypes.c_void_p]
    kernel32.CancelSynchronousIo.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    handle = kernel32.OpenThread(0x0001, False, native_thread_id)
    if not handle:
        return {
            "attempted": True,
            "succeeded": False,
            "error": ctypes.get_last_error(),
        }
    try:
        succeeded = bool(kernel32.CancelSynchronousIo(handle))
        error = 0 if succeeded else ctypes.get_last_error()
        return {"attempted": True, "succeeded": succeeded, "error": error}
    finally:
        kernel32.CloseHandle(handle)


class JsonLineWorkerProcess:
    """One persistent child, one serialized command at a time, killable as a tree."""

    def __init__(
        self,
        *,
        command: Iterable[str],
        cwd: Path,
        environment: Mapping[str, str],
        maximum_request_bytes: int,
        maximum_response_bytes: int,
        maximum_stderr_bytes: int,
        maximum_pending_responses: int,
        start_timeout_seconds: float,
        lock_timeout_seconds: float,
        terminate_timeout_seconds: float,
        shutdown_timeout_seconds: float,
        maximum_worker_job_memory_mib: int,
        expected_creation_token_digest: str,
        expected_static_fixture: bool,
        expected_startup_descendant: bool = False,
        now=time.monotonic,
    ) -> None:
        command_tuple = tuple(command)
        if not command_tuple or any(not isinstance(item, str) or not item for item in command_tuple):
            raise V7ProcessBoundaryError("worker command must be a nonempty string tuple")
        if not Path(command_tuple[0]).is_absolute():
            raise V7ProcessBoundaryError("worker executable must be an absolute path")
        self._command = command_tuple
        self._cwd = Path(cwd).resolve(strict=True)
        self._environment = dict(environment)
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in self._environment.items()):
            raise V7ProcessBoundaryError("worker environment must be string-only")
        self._max_request = int(maximum_request_bytes)
        self._max_response = int(maximum_response_bytes)
        self._max_stderr = int(maximum_stderr_bytes)
        self._pending_limit = int(maximum_pending_responses)
        if min(self._max_request, self._max_response, self._max_stderr, self._pending_limit) <= 0:
            raise V7ProcessBoundaryError("IPC bounds must be positive")
        self._start_timeout = _finite_positive(start_timeout_seconds, "start timeout")
        self._lock_timeout = _finite_positive(lock_timeout_seconds, "lock timeout")
        self._terminate_timeout = _finite_positive(terminate_timeout_seconds, "terminate timeout")
        self._shutdown_timeout = _finite_positive(shutdown_timeout_seconds, "shutdown timeout")
        if (
            isinstance(maximum_worker_job_memory_mib, bool)
            or not isinstance(maximum_worker_job_memory_mib, int)
            or maximum_worker_job_memory_mib <= 0
        ):
            raise V7ProcessBoundaryError("worker job memory limit must be a positive integer MiB")
        self._job_memory_limit_bytes = maximum_worker_job_memory_mib * 1024 * 1024
        if (
            not isinstance(expected_creation_token_digest, str)
            or len(expected_creation_token_digest) != 64
            or any(character not in "0123456789abcdef" for character in expected_creation_token_digest)
        ):
            raise V7ProcessBoundaryError("creation token digest must be SHA-256")
        self._expected_creation_token_digest = expected_creation_token_digest
        self._expected_static_fixture = expected_static_fixture
        self._expected_startup_descendant = expected_startup_descendant
        self._now = now
        self._process: subprocess.Popen[bytes] | None = None
        self._job: _WindowsJob | None = None
        self._responses: queue.Queue[Any] = queue.Queue(maxsize=self._pending_limit)
        self._stderr_chunks: deque[bytes] = deque()
        self._stderr_size = 0
        self._stderr_lock = threading.Lock()
        self._operation_lock = threading.Lock()
        self._control_lock = threading.RLock()
        self._writer_state_lock = threading.Lock()
        self._active_writer: dict[str, Any] | None = None
        self._stdout_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self._request_sequence = 0
        self.worker_instance_id: str | None = None
        self.root_pid: int | None = None
        self.process_identity: dict[str, Any] | None = None
        self.process_identity_digest: str | None = None
        self.job_assignment_proof: dict[str, Any] | None = None
        self.resumed_thread_ids: list[int] = []
        self.startup_descendant_pid: int | None = None
        self.last_termination: dict[str, Any] | None = None

    @property
    def command_digest(self) -> str:
        return hashlib.sha256(_closed_json_bytes(list(self._command), 1024 * 1024)).hexdigest()

    @property
    def is_running(self) -> bool:
        process = self._process
        return process is not None and process.poll() is None

    def _reader(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        try:
            while True:
                line = process.stdout.readline(self._max_response + 2)
                if not line:
                    break
                if len(line) > self._max_response + 1 or not line.endswith(b"\n"):
                    item: Any = V7ProcessBoundaryError("worker response exceeded JSONL bound")
                else:
                    try:
                        item = strict_finite_json_loads(line)
                    except (V7ProcessBoundaryError, RecursionError) as exc:
                        item = V7ProcessBoundaryError(f"malformed worker JSON: {exc}")
                try:
                    self._responses.put(item, timeout=0.1)
                except queue.Full:
                    # Never let the protocol reader block forever while reporting
                    # that the bounded response queue is already full.  Evict one
                    # stale item and make a single nonblocking attempt to publish
                    # the terminal protocol error; the invoking thread will also
                    # detect EOF/termination if this race loses.
                    try:
                        self._responses.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        self._responses.put_nowait(
                            V7ProcessBoundaryError("worker exceeded pending-response bound")
                        )
                    except queue.Full:
                        pass
                    break
            try:
                self._responses.put_nowait(
                    V7ProcessBoundaryError("worker response stream closed")
                )
            except queue.Full:
                pass
        except Exception as exc:
            try:
                self._responses.put_nowait(V7ProcessBoundaryError(f"response reader failed: {exc}"))
            except queue.Full:
                pass

    def _stderr_reader(self) -> None:
        process = self._process
        if process is None or process.stderr is None:
            return
        while True:
            block = process.stderr.read(4096)
            if not block:
                break
            with self._stderr_lock:
                self._stderr_chunks.append(block)
                self._stderr_size += len(block)
                while self._stderr_size > self._max_stderr and self._stderr_chunks:
                    removed = self._stderr_chunks.popleft()
                    self._stderr_size -= len(removed)

    def stderr_text(self) -> str:
        with self._stderr_lock:
            return b"".join(self._stderr_chunks).decode("utf-8", errors="replace")

    def _start_process(self) -> subprocess.Popen[bytes]:
        kwargs: dict[str, Any] = {
            "args": list(self._command),
            "cwd": str(self._cwd),
            "env": self._environment,
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "shell": False,
            "bufsize": 0,
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | 0x00000004
        else:
            kwargs["start_new_session"] = True
        return subprocess.Popen(**kwargs)

    def start(self) -> dict[str, Any]:
        with self._control_lock:
            if self.is_running:
                raise V7ProcessBoundaryError("worker is already running")
            started = float(self._now())
            if not math.isfinite(started):
                raise V7ProcessBoundaryError("worker start clock is non-finite")
            process = self._start_process()
            self._process = process
            self.root_pid = process.pid
            try:
                if os.name == "nt":
                    self._job = _WindowsJob(  # type: ignore[attr-defined]
                        int(process._handle), self._job_memory_limit_bytes
                    )
                    self.job_assignment_proof = dict(self._job.assignment_proof or {})
                    if self.job_assignment_proof.get("assigned_before_resume") is not True:
                        raise V7ProcessBoundaryError("Job assignment was not proven before resume")
                    self.process_identity = process_identity_from_handle(
                        int(process._handle), process.pid
                    )
                else:
                    self.job_assignment_proof = {
                        "assigned_before_resume": True,
                        "kill_on_close": True,
                        "job_memory_limit_bytes": self._job_memory_limit_bytes,
                        "limit_flags": 0,
                    }
                    self.process_identity = process_identity_from_handle(process.pid, process.pid)
                self.process_identity_digest = process_identity_digest(self.process_identity)
                self._stdout_thread = threading.Thread(
                    target=self._reader, name="blackwell-v7-json-reader", daemon=True
                )
                self._stderr_thread = threading.Thread(
                    target=self._stderr_reader, name="blackwell-v7-stderr-reader", daemon=True
                )
                self._stdout_thread.start()
                self._stderr_thread.start()
                if os.name == "nt":
                    self.resumed_thread_ids = _resume_windows_suspended_process(process.pid)
                else:
                    self.resumed_thread_ids = [process.pid]
                ready = self._responses.get(timeout=self._start_timeout)
                if isinstance(ready, Exception):
                    raise ready
                expected_keys = {
                    "event",
                    "protocol",
                    "pid",
                    "worker_instance_id",
                    "static_fixture",
                    "creation_token_digest",
                    "process_identity",
                    "process_identity_digest",
                    "startup_descendant_pid",
                }
                if (
                    not isinstance(ready, dict)
                    or set(ready) != expected_keys
                    or ready["event"] != "ready"
                    or ready["protocol"] != PROTOCOL
                    or ready["pid"] != process.pid
                    or not isinstance(ready["worker_instance_id"], str)
                    or len(ready["worker_instance_id"]) != 64
                    or ready["static_fixture"] is not self._expected_static_fixture
                    or ready["creation_token_digest"] != self._expected_creation_token_digest
                    or ready["process_identity"] != self.process_identity
                    or ready["process_identity_digest"] != self.process_identity_digest
                    or (
                        self._expected_startup_descendant
                        and (
                            isinstance(ready["startup_descendant_pid"], bool)
                            or not isinstance(ready["startup_descendant_pid"], int)
                            or ready["startup_descendant_pid"] <= 0
                        )
                    )
                    or (
                        not self._expected_startup_descendant
                        and ready["startup_descendant_pid"] is not None
                    )
                ):
                    raise V7ProcessBoundaryError("worker readiness identity mismatch")
                self.worker_instance_id = ready["worker_instance_id"]
                self.startup_descendant_pid = ready["startup_descendant_pid"]
                ended = float(self._now())
                if not math.isfinite(ended) or ended < started or ended - started > self._start_timeout:
                    raise V7ProcessBoundaryError("worker readiness exceeded start deadline")
                raw_handle = int(process._handle) if os.name == "nt" else process.pid  # type: ignore[attr-defined]
                process_handle_proof = hashlib.sha256(
                    (
                        f"{process.pid}:{raw_handle}:{self.worker_instance_id}:"
                        f"{self._expected_creation_token_digest}:{self.process_identity_digest}"
                    ).encode("utf-8")
                ).hexdigest()
                return {
                    "started": True,
                    "pid": process.pid,
                    "worker_instance_id": self.worker_instance_id,
                    "command_digest": self.command_digest,
                    "job_or_process_group_owned": True,
                    "job_memory_limit_bytes": self._job_memory_limit_bytes,
                    "job_assignment_proof": self.job_assignment_proof,
                    "created_suspended": os.name == "nt",
                    "resumed_thread_ids": list(self.resumed_thread_ids),
                    "startup_descendant_pid": self.startup_descendant_pid,
                    "creation_token_digest": self._expected_creation_token_digest,
                    "process_handle_owned": True,
                    "process_handle_proof": process_handle_proof,
                    "process_identity": dict(self.process_identity),
                    "process_identity_digest": self.process_identity_digest,
                    "start_deadline_seconds": self._start_timeout,
                    "elapsed_seconds": ended - started,
                }
            except Exception:
                self.terminate_tree("start_failure")
                raise

    def _cancel_active_writer(self) -> dict[str, Any]:
        with self._writer_state_lock:
            active = self._active_writer
            native_id = None if active is None else active.get("native_thread_id")
        if not isinstance(native_id, int) or native_id <= 0:
            return {"attempted": False, "succeeded": False, "reason": "no_active_writer"}
        return _cancel_synchronous_writer(native_id)

    def _send_bounded(self, payload: bytes, *, started: float, timeout: float) -> dict[str, Any]:
        process = self._process
        if process is None or process.stdin is None or process.poll() is not None:
            raise V7ProcessBoundaryError("worker is not running")
        completed = threading.Event()
        entered = threading.Event()
        errors: list[BaseException] = []
        state: dict[str, Any] = {
            "native_thread_id": None,
            "byte_count": len(payload) + 1,
            "completed": completed,
        }

        def write_request() -> None:
            state["native_thread_id"] = threading.get_native_id()
            entered.set()
            try:
                process.stdin.write(payload + b"\n")
                process.stdin.flush()
            except BaseException as exc:
                errors.append(exc)
            finally:
                completed.set()

        thread = threading.Thread(
            target=write_request,
            name="blackwell-v7-bounded-json-writer",
            daemon=False,
        )
        state["thread"] = thread
        with self._writer_state_lock:
            if self._active_writer is not None:
                raise V7ProcessBoundaryError("more than one writer became active")
            self._active_writer = state
        thread.start()
        if not entered.wait(timeout=min(timeout, 0.25)):
            termination = self.terminate_tree("writer_failed_to_start")
            thread.join(timeout=self._terminate_timeout)
            raise V7ProcessTimeout(
                f"request writer failed to start; root_exited={termination['root_exited']}"
            )
        try:
            while not completed.is_set():
                now = float(self._now())
                if not math.isfinite(now) or now < started:
                    termination = self.terminate_tree("invalid_writer_clock")
                    thread.join(timeout=self._terminate_timeout)
                    raise V7ProcessBoundaryError(
                        f"writer clock invalid; root_exited={termination['root_exited']}"
                    )
                remaining = timeout - (now - started)
                if remaining <= 0:
                    cancellation = self._cancel_active_writer()
                    termination = self.terminate_tree("request_write_deadline")
                    thread.join(timeout=self._terminate_timeout)
                    if thread.is_alive():
                        raise V7ProcessBoundaryError(
                            "bounded writer did not exit after I/O cancellation and Job termination"
                        )
                    raise V7ProcessTimeout(
                        "request write timed out; "
                        f"cancelled={cancellation.get('succeeded')}; "
                        f"root_exited={termination['root_exited']}"
                    )
                completed.wait(timeout=min(remaining, 0.05))
            thread.join(timeout=self._terminate_timeout)
            if thread.is_alive():
                termination = self.terminate_tree("writer_join_deadline")
                raise V7ProcessBoundaryError(
                    f"bounded writer join failed; root_exited={termination['root_exited']}"
                )
            if errors:
                termination = self.terminate_tree("request_write_failure")
                raise V7ProcessBoundaryError(
                    f"request write failed: {type(errors[0]).__name__}:{errors[0]}; "
                    f"root_exited={termination['root_exited']}"
                )
            return {
                "completed": True,
                "byte_count": len(payload) + 1,
                "native_thread_id": state["native_thread_id"],
                "writer_thread_exited": not thread.is_alive(),
            }
        finally:
            with self._writer_state_lock:
                if self._active_writer is state:
                    self._active_writer = None

    def invoke(self, operation: str, payload: Mapping[str, Any], timeout_seconds: float) -> dict[str, Any]:
        timeout = _finite_positive(timeout_seconds, f"{operation} timeout")
        if not isinstance(operation, str) or not operation:
            raise V7ProcessBoundaryError("operation must be nonempty")
        lock_wait = min(self._lock_timeout, timeout)
        acquired = self._operation_lock.acquire(timeout=lock_wait)
        if not acquired:
            raise V7ProcessTimeout(f"{operation}: IPC lock acquisition timed out")
        started = float(self._now())
        try:
            if not math.isfinite(started):
                raise V7ProcessBoundaryError("operation clock is non-finite")
            self._request_sequence += 1
            request_id = hashlib.sha256(
                f"{self.worker_instance_id}:{self._request_sequence}:{operation}".encode("utf-8")
            ).hexdigest()
            request = {
                "protocol": PROTOCOL,
                "request_id": request_id,
                "operation": operation,
                "payload": dict(payload),
                "worker_instance_id": self.worker_instance_id,
                "process_identity_digest": self.process_identity_digest,
            }
            writer = self._send_bounded(
                _closed_json_bytes(request, self._max_request),
                started=started,
                timeout=timeout,
            )
            while True:
                now = float(self._now())
                if not math.isfinite(now) or now < started:
                    self.terminate_tree("invalid_operation_clock")
                    raise V7ProcessBoundaryError("operation clock is invalid")
                remaining = timeout - (now - started)
                if remaining <= 0:
                    termination = self.terminate_tree(f"{operation}_deadline")
                    raise V7ProcessTimeout(
                        f"{operation} timed out; worker tree termination={termination['root_exited']}"
                    )
                try:
                    response = self._responses.get(timeout=remaining)
                except queue.Empty:
                    termination = self.terminate_tree(f"{operation}_deadline")
                    raise V7ProcessTimeout(
                        f"{operation} timed out; worker tree termination={termination['root_exited']}"
                    )
                if isinstance(response, Exception):
                    self.terminate_tree("protocol_failure")
                    raise response
                expected = {
                    "protocol",
                    "request_id",
                    "operation",
                    "ok",
                    "value",
                    "error_type",
                    "error",
                    "worker_instance_id",
                    "worker_pid",
                    "process_identity_digest",
                }
                process = self._process
                if (
                    not isinstance(response, dict)
                    or set(response) != expected
                    or response["protocol"] != PROTOCOL
                    or response["request_id"] != request_id
                    or response["operation"] != operation
                    or response["worker_instance_id"] != self.worker_instance_id
                    or response["process_identity_digest"] != self.process_identity_digest
                    or process is None
                    or response["worker_pid"] != process.pid
                    or not isinstance(response["ok"], bool)
                ):
                    self.terminate_tree("response_identity_failure")
                    raise V7ProcessBoundaryError("worker response identity/schema mismatch")
                ended = float(self._now())
                if not math.isfinite(ended) or ended < started or ended - started > timeout:
                    self.terminate_tree("late_response")
                    raise V7ProcessTimeout(f"{operation}: late response rejected")
                if response["ok"] is not True:
                    raise V7ProcessBoundaryError(
                        f"{operation}: {response['error_type']}:{response['error']}"
                    )
                if response["error_type"] is not None or response["error"] is not None:
                    self.terminate_tree("contradictory_response")
                    raise V7ProcessBoundaryError("successful worker response carried an error")
                return {
                    "value": response["value"],
                    "request_id": request_id,
                    "worker_pid": response["worker_pid"],
                    "worker_instance_id": self.worker_instance_id,
                    "process_identity_digest": self.process_identity_digest,
                    "writer": writer,
                    "elapsed_seconds": ended - started,
                    "deadline_seconds": timeout,
                    "deadline_monotonic": started + timeout,
                }
        finally:
            self._operation_lock.release()

    def terminate_tree(self, reason: str) -> dict[str, Any]:
        started = float(self._now())
        if not math.isfinite(started):
            started = time.monotonic()
        with self._control_lock:
            process = self._process
            pid = process.pid if process is not None else self.root_pid
            requested = False
            errors: list[str] = []
            writer_cancellation = self._cancel_active_writer()
            if process is not None and process.poll() is None:
                requested = True
                try:
                    if os.name == "nt":
                        if self._job is None:
                            raise V7ProcessBoundaryError("owned Windows Job Object is absent")
                        self._job.terminate()
                    else:
                        os.killpg(process.pid, signal.SIGKILL)
                except Exception as exc:
                    errors.append(f"terminate:{type(exc).__name__}:{exc}")
                    try:
                        process.kill()
                    except Exception as kill_exc:
                        errors.append(f"root_kill:{type(kill_exc).__name__}:{kill_exc}")
                try:
                    process.wait(timeout=self._terminate_timeout)
                except subprocess.TimeoutExpired:
                    errors.append("root_wait:timeout")
            if process is not None:
                for handle_name in ("stdin", "stdout", "stderr"):
                    handle = getattr(process, handle_name, None)
                    try:
                        if handle is not None:
                            handle.close()
                    except OSError:
                        pass
            if self._stdout_thread is not None:
                self._stdout_thread.join(timeout=self._terminate_timeout)
            if self._stderr_thread is not None:
                self._stderr_thread.join(timeout=self._terminate_timeout)
            if self._job is not None:
                self._job.close()
                self._job = None
            with self._writer_state_lock:
                active_writer = self._active_writer
                writer_thread = None if active_writer is None else active_writer.get("thread")
            if isinstance(writer_thread, threading.Thread):
                writer_thread.join(timeout=self._terminate_timeout)
            writer_exited = not isinstance(writer_thread, threading.Thread) or not writer_thread.is_alive()
            if not writer_exited:
                errors.append("writer_join:timeout")
            root_exited = process is None or process.poll() is not None
            ended = float(self._now())
            if not math.isfinite(ended) or ended < started:
                ended = time.monotonic()
            result = {
                "reason": reason,
                "root_pid": pid,
                "termination_requested": requested,
                "root_exited": root_exited,
                "exit_code": None if process is None else process.poll(),
                "process_tree_policy": (
                    "windows_job_object_kill_on_close" if os.name == "nt" else "posix_process_group"
                ),
                "stdout_reader_exited": self._stdout_thread is None or not self._stdout_thread.is_alive(),
                "stderr_reader_exited": self._stderr_thread is None or not self._stderr_thread.is_alive(),
                "writer_cancellation": writer_cancellation,
                "writer_exited": writer_exited,
                "process_identity_digest": self.process_identity_digest,
                "process_identity": self.process_identity,
                "job_assignment_proof": self.job_assignment_proof,
                "elapsed_seconds": max(0.0, ended - started),
                "errors": errors,
            }
            self.last_termination = result
            return result

    def cancel_or_cleanup_without_waiting_for_operation_lock(self, reason: str) -> dict[str, Any]:
        """The fail-safe cancellation path never waits for the operation lock."""
        return self.terminate_tree(reason)

    def close(self) -> dict[str, Any]:
        graceful: dict[str, Any] | None = None
        if self.is_running:
            try:
                graceful = self.invoke(
                    "shutdown", {"reason": "supervisor_close"}, self._shutdown_timeout
                )
                process = self._process
                if process is not None:
                    process.wait(timeout=self._terminate_timeout)
            except Exception as exc:
                graceful = {
                    "completed": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
        termination = self.terminate_tree(
            "close_after_graceful_shutdown"
            if graceful is not None and "value" in graceful
            else "close_forced_termination"
        )
        return {**termination, "graceful_shutdown": graceful}


__all__ = [
    "current_process_identity",
    "JsonLineWorkerProcess",
    "PROTOCOL",
    "process_identity_digest",
    "process_identity_from_handle",
    "strict_finite_json_loads",
    "V7ProcessBoundaryError",
    "V7ProcessTimeout",
]
