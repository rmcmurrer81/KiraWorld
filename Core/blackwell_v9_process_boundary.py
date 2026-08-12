"""Append-only Windows venv-launcher process boundary for Blackwell v9.

This module repairs one narrowly proven v8 failure: on Windows the configured
virtual-environment ``python.exe`` is a launcher process which creates the
base-Python interpreter that emits the worker protocol.  V7 correctly bound
the launcher but incorrectly required readiness to come from that same PID.

V9 keeps both identities.  It accepts readiness only from the exact direct
child of the exact retained launcher, proves both executable file identities,
opens and retains the child process handle, and proves the child inherited the
same retained Job Object.  It never searches for or accepts an arbitrary
descendant.  Importing this module starts nothing.
"""

from __future__ import annotations

import ctypes
import hashlib
import math
import os
import queue
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

import Core.blackwell_v7_process_boundary as v7


_STABLE_IDENTITY_KEYS = {
    "executable_path",
    "executable_sha256",
    "executable_size",
    "executable_volume_serial",
    "executable_file_index",
}
_READY_KEYS = {
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
_RESPONSE_KEYS = {
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
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_SYNCHRONIZE = 0x00100000
_TH32CS_SNAPPROCESS = 0x00000002
_WAIT_OBJECT_0 = 0x00000000
_WAIT_TIMEOUT = 0x00000102
_STILL_ACTIVE = 259
_MAX_PATH = 260


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_ulong),
        ("cntUsage", ctypes.c_ulong),
        ("th32ProcessID", ctypes.c_ulong),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", ctypes.c_ulong),
        ("cntThreads", ctypes.c_ulong),
        ("th32ParentProcessID", ctypes.c_ulong),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.c_ulong),
        ("szExeFile", ctypes.c_wchar * _MAX_PATH),
    ]


def _require_windows() -> None:
    if os.name != "nt":
        raise v7.V7ProcessBoundaryError(
            "v9 venv-launcher descendant binding is Windows-only"
        )


def _kernel32():
    _require_windows()
    return ctypes.WinDLL("kernel32", use_last_error=True)


def _normal_path(value: str) -> str:
    return os.path.normcase(str(Path(value).resolve(strict=True)))


def _stable_fields(identity: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(identity, Mapping) or not _STABLE_IDENTITY_KEYS.issubset(identity):
        raise v7.V7ProcessBoundaryError("stable executable identity is incomplete")
    return {key: identity[key] for key in sorted(_STABLE_IDENTITY_KEYS)}


def stable_executable_identity(path: Path) -> dict[str, Any]:
    """Return the exact immutable-on-this-run executable file binding."""

    _require_windows()
    executable = Path(path).resolve(strict=True)
    file_identity = v7._windows_executable_file_identity(executable)
    result = {
        "executable_path": str(executable),
        "executable_sha256": v7._sha256_path(executable),
        **file_identity,
    }
    if set(result) != _STABLE_IDENTITY_KEYS:
        raise v7.V7ProcessBoundaryError("executable identity schema is incomplete")
    return result


def _validate_expected_stable_identity(
    value: Mapping[str, Any], label: str
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != _STABLE_IDENTITY_KEYS:
        raise v7.V7ProcessBoundaryError(f"{label} stable identity schema is not exact")
    result = dict(value)
    if (
        not isinstance(result["executable_path"], str)
        or not isinstance(result["executable_sha256"], str)
        or len(result["executable_sha256"]) != 64
        or any(c not in "0123456789abcdef" for c in result["executable_sha256"])
    ):
        raise v7.V7ProcessBoundaryError(f"{label} executable binding is invalid")
    for key in ("executable_size", "executable_volume_serial", "executable_file_index"):
        if isinstance(result[key], bool) or not isinstance(result[key], int) or result[key] <= 0:
            raise v7.V7ProcessBoundaryError(f"{label} {key} is invalid")
    result["executable_path"] = str(Path(result["executable_path"]).resolve(strict=True))
    return result


def _stable_identity_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_fields = _stable_fields(left)
    right_fields = _stable_fields(right)
    for key in _STABLE_IDENTITY_KEYS:
        if key == "executable_path":
            if _normal_path(str(left_fields[key])) != _normal_path(str(right_fields[key])):
                return False
        elif left_fields[key] != right_fields[key]:
            return False
    return True


def _open_process(pid: int) -> int:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise v7.V7ProcessBoundaryError("worker descendant PID must be positive")
    kernel32 = _kernel32()
    kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    handle = kernel32.OpenProcess(
        _PROCESS_QUERY_LIMITED_INFORMATION | _SYNCHRONIZE, False, pid
    )
    if not handle:
        raise v7.V7ProcessBoundaryError(
            f"OpenProcess(worker descendant) failed: {ctypes.get_last_error()}"
        )
    return int(handle)


def _close_process_handle(handle: int) -> None:
    kernel32 = _kernel32()
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    if not kernel32.CloseHandle(ctypes.c_void_p(handle)):
        raise v7.V7ProcessBoundaryError(
            f"CloseHandle(worker descendant) failed: {ctypes.get_last_error()}"
        )


def _wait_process(handle: int, timeout_seconds: float) -> int:
    kernel32 = _kernel32()
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel32.WaitForSingleObject.restype = ctypes.c_ulong
    milliseconds = max(0, min(0xFFFFFFFE, int(timeout_seconds * 1000)))
    return int(kernel32.WaitForSingleObject(ctypes.c_void_p(handle), milliseconds))


def _process_exit_code(handle: int) -> int | None:
    kernel32 = _kernel32()
    kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    kernel32.GetExitCodeProcess.restype = ctypes.c_int
    code = ctypes.c_ulong()
    if not kernel32.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code)):
        raise v7.V7ProcessBoundaryError(
            f"GetExitCodeProcess(worker descendant) failed: {ctypes.get_last_error()}"
        )
    return None if int(code.value) == _STILL_ACTIVE else int(code.value)


def _direct_parent_pid(pid: int) -> int:
    kernel32 = _kernel32()
    kernel32.CreateToolhelp32Snapshot.argtypes = [ctypes.c_ulong, ctypes.c_ulong]
    kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    kernel32.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = ctypes.c_int
    kernel32.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    snapshot = kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
    if snapshot in (None, 0, ctypes.c_void_p(-1).value):
        raise v7.V7ProcessBoundaryError(
            f"CreateToolhelp32Snapshot(processes) failed: {ctypes.get_last_error()}"
        )
    try:
        entry = _PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        available = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while available:
            if int(entry.th32ProcessID) == pid:
                return int(entry.th32ParentProcessID)
            entry.dwSize = ctypes.sizeof(entry)
            available = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    raise v7.V7ProcessBoundaryError("readiness PID was absent from the process snapshot")


def _same_retained_job(process_handle: int, job_handle: int) -> bool:
    kernel32 = _kernel32()
    kernel32.IsProcessInJob.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    kernel32.IsProcessInJob.restype = ctypes.c_int
    assigned = ctypes.c_int()
    if not kernel32.IsProcessInJob(
        ctypes.c_void_p(process_handle), ctypes.c_void_p(job_handle), ctypes.byref(assigned)
    ):
        raise v7.V7ProcessBoundaryError(
            f"IsProcessInJob(worker descendant) failed: {ctypes.get_last_error()}"
        )
    return assigned.value == 1


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class V9JsonLineWorkerProcess(v7.JsonLineWorkerProcess):
    """Retain and bind the exact launcher root plus exact direct worker child."""

    def __init__(
        self,
        *,
        expected_launcher_identity: Mapping[str, Any],
        expected_worker_identity: Mapping[str, Any],
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
        _require_windows()
        super().__init__(
            command=command,
            cwd=cwd,
            environment=environment,
            maximum_request_bytes=maximum_request_bytes,
            maximum_response_bytes=maximum_response_bytes,
            maximum_stderr_bytes=maximum_stderr_bytes,
            maximum_pending_responses=maximum_pending_responses,
            start_timeout_seconds=start_timeout_seconds,
            lock_timeout_seconds=lock_timeout_seconds,
            terminate_timeout_seconds=terminate_timeout_seconds,
            shutdown_timeout_seconds=shutdown_timeout_seconds,
            maximum_worker_job_memory_mib=maximum_worker_job_memory_mib,
            expected_creation_token_digest=expected_creation_token_digest,
            expected_static_fixture=expected_static_fixture,
            expected_startup_descendant=expected_startup_descendant,
            now=now,
        )
        self.expected_launcher_identity = _validate_expected_stable_identity(
            expected_launcher_identity, "launcher"
        )
        self.expected_worker_identity = _validate_expected_stable_identity(
            expected_worker_identity, "worker"
        )
        self.launcher_process_identity: dict[str, Any] | None = None
        self.launcher_process_identity_digest: str | None = None
        self.worker_child_process_identity: dict[str, Any] | None = None
        self.worker_child_process_identity_digest: str | None = None
        self.worker_child_pid: int | None = None
        self.worker_child_direct_parent_pid: int | None = None
        self.worker_child_job_proof: dict[str, Any] | None = None
        self._worker_child_handle: int | None = None
        self._binding_accepted = False
        self.last_binding_rejection: dict[str, Any] | None = None

    @property
    def is_running(self) -> bool:
        process = self._process
        handle = self._worker_child_handle
        if process is None or process.poll() is not None or handle is None:
            return False
        return _wait_process(handle, 0.0) == _WAIT_TIMEOUT

    def _reject(self, stage: str, fields: Iterable[str]) -> None:
        field_names = sorted({str(field) for field in fields})
        self.last_binding_rejection = {
            "stage": stage,
            "mismatch_fields": field_names,
            "arbitrary_descendant_accepted": False,
        }
        raise v7.V7ProcessBoundaryError(
            f"v9 readiness binding rejected at {stage}: {','.join(field_names)}"
        )

    def _verify_bound_handles(self) -> None:
        process = self._process
        child_handle = self._worker_child_handle
        child_pid = self.worker_child_pid
        if (
            process is None
            or process.poll() is not None
            or child_handle is None
            or child_pid is None
            or self.launcher_process_identity is None
            or self.worker_child_process_identity is None
            or self._job is None
            or not self._job.handle
        ):
            raise v7.V7ProcessBoundaryError("v9 root/child binding is not live")
        if _wait_process(child_handle, 0.0) != _WAIT_TIMEOUT:
            raise v7.V7ProcessBoundaryError("v9 worker child already exited")
        root_now = v7.process_identity_from_handle(int(process._handle), process.pid)  # type: ignore[attr-defined]
        child_now = v7.process_identity_from_handle(child_handle, child_pid)
        if root_now != self.launcher_process_identity:
            raise v7.V7ProcessBoundaryError("v9 launcher handle identity changed")
        if child_now != self.worker_child_process_identity:
            raise v7.V7ProcessBoundaryError("v9 worker handle identity changed")
        if _direct_parent_pid(child_pid) != process.pid:
            raise v7.V7ProcessBoundaryError("v9 worker is no longer bound to the launcher root")
        if not _same_retained_job(child_handle, int(self._job.handle)):
            raise v7.V7ProcessBoundaryError("v9 worker left the retained launcher Job")

    def start(self) -> dict[str, Any]:
        with self._control_lock:
            if self._process is not None and self._process.poll() is None:
                raise v7.V7ProcessBoundaryError("worker launcher is already running")
            started = float(self._now())
            if not math.isfinite(started):
                raise v7.V7ProcessBoundaryError("worker start clock is non-finite")
            process = self._start_process()
            self._process = process
            self.root_pid = process.pid
            try:
                self._job = v7._WindowsJob(  # type: ignore[attr-defined]
                    int(process._handle), self._job_memory_limit_bytes  # type: ignore[attr-defined]
                )
                self.job_assignment_proof = dict(self._job.assignment_proof or {})
                if self.job_assignment_proof.get("assigned_before_resume") is not True:
                    self._reject("launcher_job_assignment", ["assigned_before_resume"])
                root_identity = v7.process_identity_from_handle(
                    int(process._handle), process.pid  # type: ignore[attr-defined]
                )
                self.launcher_process_identity = root_identity
                self.launcher_process_identity_digest = v7.process_identity_digest(root_identity)
                if not _stable_identity_equal(root_identity, self.expected_launcher_identity):
                    self._reject("launcher_identity", ["launcher_executable_identity"])

                self._stdout_thread = threading.Thread(
                    target=self._reader, name="blackwell-v9-json-reader", daemon=True
                )
                self._stderr_thread = threading.Thread(
                    target=self._stderr_reader, name="blackwell-v9-stderr-reader", daemon=True
                )
                self._stdout_thread.start()
                self._stderr_thread.start()
                self.resumed_thread_ids = v7._resume_windows_suspended_process(process.pid)
                try:
                    ready = self._responses.get(timeout=self._start_timeout)
                except queue.Empty as exc:
                    raise v7.V7ProcessTimeout("v9 worker readiness timed out") from exc
                if isinstance(ready, Exception):
                    raise ready

                schema_mismatches: list[str] = []
                if not isinstance(ready, dict):
                    self._reject("readiness_schema", ["ready_object"])
                if set(ready) != _READY_KEYS:
                    schema_mismatches.append("ready_keys")
                if ready.get("event") != "ready":
                    schema_mismatches.append("event")
                if ready.get("protocol") != v7.PROTOCOL:
                    schema_mismatches.append("protocol")
                worker_pid = ready.get("pid")
                if isinstance(worker_pid, bool) or not isinstance(worker_pid, int) or worker_pid <= 0:
                    schema_mismatches.append("pid")
                elif worker_pid == process.pid:
                    schema_mismatches.append("worker_pid_distinct_from_launcher")
                instance_id = ready.get("worker_instance_id")
                if (
                    not isinstance(instance_id, str)
                    or len(instance_id) != 64
                    or any(c not in "0123456789abcdef" for c in instance_id)
                ):
                    schema_mismatches.append("worker_instance_id")
                if ready.get("static_fixture") is not self._expected_static_fixture:
                    schema_mismatches.append("static_fixture")
                if ready.get("creation_token_digest") != self._expected_creation_token_digest:
                    schema_mismatches.append("creation_token_digest")
                startup_pid = ready.get("startup_descendant_pid")
                if self._expected_startup_descendant:
                    if isinstance(startup_pid, bool) or not isinstance(startup_pid, int) or startup_pid <= 0:
                        schema_mismatches.append("startup_descendant_pid")
                elif startup_pid is not None:
                    schema_mismatches.append("startup_descendant_pid")
                if schema_mismatches:
                    self._reject("readiness_schema", schema_mismatches)

                child_handle = _open_process(worker_pid)
                self._worker_child_handle = child_handle
                self.worker_child_pid = worker_pid
                child_identity = v7.process_identity_from_handle(child_handle, worker_pid)
                self.worker_child_process_identity = child_identity
                child_digest = v7.process_identity_digest(child_identity)
                self.worker_child_process_identity_digest = child_digest
                parent_pid = _direct_parent_pid(worker_pid)
                self.worker_child_direct_parent_pid = parent_pid
                same_job = bool(
                    self._job.handle
                    and _same_retained_job(child_handle, int(self._job.handle))
                )
                self.worker_child_job_proof = {
                    "same_retained_job": same_job,
                    "kill_on_close": self.job_assignment_proof.get("kill_on_close") is True,
                    "job_memory_limit_bytes": self._job_memory_limit_bytes,
                }

                identity_mismatches: list[str] = []
                if parent_pid != process.pid:
                    identity_mismatches.append("direct_parent_pid")
                if not same_job:
                    identity_mismatches.append("same_retained_job")
                if not _stable_identity_equal(child_identity, self.expected_worker_identity):
                    identity_mismatches.append("worker_executable_identity")
                if ready.get("process_identity") != child_identity:
                    identity_mismatches.append("ready_process_identity")
                if ready.get("process_identity_digest") != child_digest:
                    identity_mismatches.append("ready_process_identity_digest")
                root_now = v7.process_identity_from_handle(
                    int(process._handle), process.pid  # type: ignore[attr-defined]
                )
                if root_now != root_identity or process.poll() is not None:
                    identity_mismatches.append("launcher_handle_identity")
                if identity_mismatches:
                    self._reject("root_child_identity", identity_mismatches)

                self.worker_instance_id = instance_id
                self.startup_descendant_pid = startup_pid
                self.process_identity = child_identity
                self.process_identity_digest = child_digest
                self._binding_accepted = True
                ended = float(self._now())
                if not math.isfinite(ended) or ended < started or ended - started > self._start_timeout:
                    raise v7.V7ProcessBoundaryError("worker readiness exceeded start deadline")
                root_proof = _sha256_text(
                    f"{process.pid}:{self.launcher_process_identity_digest}:"
                    f"{self.worker_instance_id}:{self._expected_creation_token_digest}"
                )
                child_proof = _sha256_text(
                    f"{worker_pid}:{child_digest}:{parent_pid}:"
                    f"{self.worker_instance_id}:{self._expected_creation_token_digest}"
                )
                return {
                    "started": True,
                    "pid": worker_pid,
                    "root_pid": process.pid,
                    "worker_pid": worker_pid,
                    "worker_instance_id": self.worker_instance_id,
                    "command_digest": self.command_digest,
                    "job_or_process_group_owned": True,
                    "job_memory_limit_bytes": self._job_memory_limit_bytes,
                    "job_assignment_proof": self.job_assignment_proof,
                    "worker_child_job_proof": self.worker_child_job_proof,
                    "created_suspended": True,
                    "resumed_thread_ids": list(self.resumed_thread_ids),
                    "startup_descendant_pid": self.startup_descendant_pid,
                    "creation_token_digest": self._expected_creation_token_digest,
                    "launcher_process_handle_owned": True,
                    "worker_process_handle_owned": True,
                    "launcher_process_handle_proof": root_proof,
                    "worker_process_handle_proof": child_proof,
                    "launcher_process_identity": dict(root_identity),
                    "launcher_process_identity_digest": self.launcher_process_identity_digest,
                    "worker_process_identity": dict(child_identity),
                    "worker_process_identity_digest": child_digest,
                    "worker_direct_parent_pid": parent_pid,
                    "arbitrary_descendant_accepted": False,
                    "start_deadline_seconds": self._start_timeout,
                    "elapsed_seconds": ended - started,
                }
            except Exception:
                self.terminate_tree("start_failure")
                raise

    def invoke(
        self, operation: str, payload: Mapping[str, Any], timeout_seconds: float
    ) -> dict[str, Any]:
        timeout = v7._finite_positive(timeout_seconds, f"{operation} timeout")
        if not isinstance(operation, str) or not operation:
            raise v7.V7ProcessBoundaryError("operation must be nonempty")
        acquired = self._operation_lock.acquire(timeout=min(self._lock_timeout, timeout))
        if not acquired:
            raise v7.V7ProcessTimeout(f"{operation}: IPC lock acquisition timed out")
        started = float(self._now())
        try:
            if not math.isfinite(started):
                raise v7.V7ProcessBoundaryError("operation clock is non-finite")
            try:
                self._verify_bound_handles()
            except Exception:
                self.terminate_tree("pre_request_root_child_identity_failure")
                raise
            self._request_sequence += 1
            request_id = _sha256_text(
                f"{self.worker_instance_id}:{self._request_sequence}:{operation}"
            )
            request = {
                "protocol": v7.PROTOCOL,
                "request_id": request_id,
                "operation": operation,
                "payload": dict(payload),
                "worker_instance_id": self.worker_instance_id,
                "process_identity_digest": self.process_identity_digest,
            }
            writer = self._send_bounded(
                v7._closed_json_bytes(request, self._max_request),
                started=started,
                timeout=timeout,
            )
            while True:
                now = float(self._now())
                if not math.isfinite(now) or now < started:
                    self.terminate_tree("invalid_operation_clock")
                    raise v7.V7ProcessBoundaryError("operation clock is invalid")
                remaining = timeout - (now - started)
                if remaining <= 0:
                    termination = self.terminate_tree(f"{operation}_deadline")
                    raise v7.V7ProcessTimeout(
                        f"{operation} timed out; worker tree termination="
                        f"{termination['entire_bound_tree_exited']}"
                    )
                try:
                    response = self._responses.get(timeout=remaining)
                except queue.Empty:
                    termination = self.terminate_tree(f"{operation}_deadline")
                    raise v7.V7ProcessTimeout(
                        f"{operation} timed out; worker tree termination="
                        f"{termination['entire_bound_tree_exited']}"
                    )
                if isinstance(response, Exception):
                    self.terminate_tree("protocol_failure")
                    raise response
                if (
                    not isinstance(response, dict)
                    or set(response) != _RESPONSE_KEYS
                    or response.get("protocol") != v7.PROTOCOL
                    or response.get("request_id") != request_id
                    or response.get("operation") != operation
                    or response.get("worker_instance_id") != self.worker_instance_id
                    or response.get("process_identity_digest") != self.process_identity_digest
                    or response.get("worker_pid") != self.worker_child_pid
                    or not isinstance(response.get("ok"), bool)
                ):
                    self.terminate_tree("response_identity_failure")
                    raise v7.V7ProcessBoundaryError(
                        "v9 worker response identity/schema mismatch"
                    )
                ended = float(self._now())
                if not math.isfinite(ended) or ended < started or ended - started > timeout:
                    self.terminate_tree("late_response")
                    raise v7.V7ProcessTimeout(f"{operation}: late response rejected")
                if response["ok"] is not True:
                    raise v7.V7ProcessBoundaryError(
                        f"{operation}: {response['error_type']}:{response['error']}"
                    )
                if response["error_type"] is not None or response["error"] is not None:
                    self.terminate_tree("contradictory_response")
                    raise v7.V7ProcessBoundaryError(
                        "successful worker response carried an error"
                    )
                return {
                    "value": response["value"],
                    "request_id": request_id,
                    "worker_pid": response["worker_pid"],
                    "root_pid": self.root_pid,
                    "worker_instance_id": self.worker_instance_id,
                    "process_identity_digest": self.process_identity_digest,
                    "launcher_process_identity_digest": self.launcher_process_identity_digest,
                    "writer": writer,
                    "elapsed_seconds": ended - started,
                    "deadline_seconds": timeout,
                    "deadline_monotonic": started + timeout,
                }
        finally:
            self._operation_lock.release()

    def terminate_tree(self, reason: str) -> dict[str, Any]:
        child_handle = self._worker_child_handle
        child_pid = self.worker_child_pid
        child_identity = self.worker_child_process_identity
        child_digest = self.worker_child_process_identity_digest
        launcher_identity = self.launcher_process_identity
        launcher_digest = self.launcher_process_identity_digest
        binding_accepted = self._binding_accepted
        result = super().terminate_tree(reason)
        errors = list(result.get("errors", []))
        child_exited: bool | None = None
        child_exit_code: int | None = None
        child_handle_closed: bool | None = None
        if child_handle is not None:
            try:
                wait_result = _wait_process(child_handle, self._terminate_timeout)
                child_exited = wait_result == _WAIT_OBJECT_0
                if wait_result not in (_WAIT_OBJECT_0, _WAIT_TIMEOUT):
                    errors.append(f"worker_child_wait:unexpected:{wait_result}")
                if not child_exited:
                    errors.append("worker_child_wait:timeout")
                child_exit_code = _process_exit_code(child_handle)
            except Exception as exc:
                errors.append(f"worker_child_wait:{type(exc).__name__}:{exc}")
                child_exited = False
            try:
                _close_process_handle(child_handle)
                child_handle_closed = True
            except Exception as exc:
                errors.append(f"worker_child_close:{type(exc).__name__}:{exc}")
                child_handle_closed = False
        self._worker_child_handle = None
        self._binding_accepted = False
        full = {
            **result,
            "root_pid": result.get("root_pid", self.root_pid),
            "worker_child_pid": child_pid,
            "root_exited": bool(result.get("root_exited")),
            "worker_child_exited": child_exited,
            "entire_bound_tree_exited": bool(result.get("root_exited"))
            and (child_exited is True or child_handle is None),
            "root_exit_code": result.get("exit_code"),
            "worker_child_exit_code": child_exit_code,
            "launcher_process_identity": launcher_identity,
            "launcher_process_identity_digest": launcher_digest,
            "worker_process_identity": child_identity,
            "worker_process_identity_digest": child_digest,
            "worker_direct_parent_pid": self.worker_child_direct_parent_pid,
            "worker_child_job_proof": self.worker_child_job_proof,
            "binding_accepted_before_cleanup": binding_accepted,
            "arbitrary_descendant_accepted": False,
            "worker_child_handle_closed": child_handle_closed,
            "job_handle_closed": self._job is None,
            "root_standard_streams_closed": (
                self._process is None
                or all(
                    getattr(self._process, name, None) is None
                    or getattr(self._process, name).closed
                    for name in ("stdin", "stdout", "stderr")
                )
            ),
            "root_process_handle_owner": "subprocess.Popen",
            "errors": errors,
        }
        self.last_termination = full
        return full


__all__ = [
    "stable_executable_identity",
    "V9JsonLineWorkerProcess",
]
