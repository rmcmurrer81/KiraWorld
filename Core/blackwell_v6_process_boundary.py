"""Spawn-safe JSONL worker supervisor for the inactive Blackwell v6 candidate.

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


PROTOCOL = "kira_blackwell_v6_jsonl_1"


class V6ProcessBoundaryError(RuntimeError):
    pass


class V6ProcessTimeout(V6ProcessBoundaryError):
    pass


def _finite_positive(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise V6ProcessBoundaryError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise V6ProcessBoundaryError(f"{label} must be positive and finite")
    return result


def _closed_json_bytes(value: Any, maximum_bytes: int) -> bytes:
    try:
        payload = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise V6ProcessBoundaryError(f"request is not closed finite JSON: {exc}") from exc
    if not payload or len(payload) > maximum_bytes or b"\n" in payload or b"\r" in payload:
        raise V6ProcessBoundaryError("request exceeds the closed JSONL bound")
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
            raise V6ProcessBoundaryError("Windows job memory limit must be a positive integer")
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
            raise V6ProcessBoundaryError(f"CreateJobObjectW failed: {ctypes.get_last_error()}")
        self._kernel32 = kernel32
        self.handle = handle
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
                raise V6ProcessBoundaryError(
                    f"SetInformationJobObject failed: {ctypes.get_last_error()}"
                )
            if not kernel32.AssignProcessToJobObject(handle, ctypes.c_void_p(process_handle)):
                raise V6ProcessBoundaryError(
                    f"AssignProcessToJobObject failed: {ctypes.get_last_error()}"
                )
        except Exception:
            kernel32.CloseHandle(handle)
            self.handle = None
            raise

    def terminate(self) -> None:
        if self.handle and not self._kernel32.TerminateJobObject(self.handle, 1):
            raise V6ProcessBoundaryError(
                f"TerminateJobObject failed: {ctypes.get_last_error()}"
            )

    def close(self) -> None:
        if self.handle:
            self._kernel32.CloseHandle(self.handle)
            self.handle = None


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
        now=time.monotonic,
    ) -> None:
        command_tuple = tuple(command)
        if not command_tuple or any(not isinstance(item, str) or not item for item in command_tuple):
            raise V6ProcessBoundaryError("worker command must be a nonempty string tuple")
        if not Path(command_tuple[0]).is_absolute():
            raise V6ProcessBoundaryError("worker executable must be an absolute path")
        self._command = command_tuple
        self._cwd = Path(cwd).resolve(strict=True)
        self._environment = dict(environment)
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in self._environment.items()):
            raise V6ProcessBoundaryError("worker environment must be string-only")
        self._max_request = int(maximum_request_bytes)
        self._max_response = int(maximum_response_bytes)
        self._max_stderr = int(maximum_stderr_bytes)
        self._pending_limit = int(maximum_pending_responses)
        if min(self._max_request, self._max_response, self._max_stderr, self._pending_limit) <= 0:
            raise V6ProcessBoundaryError("IPC bounds must be positive")
        self._start_timeout = _finite_positive(start_timeout_seconds, "start timeout")
        self._lock_timeout = _finite_positive(lock_timeout_seconds, "lock timeout")
        self._terminate_timeout = _finite_positive(terminate_timeout_seconds, "terminate timeout")
        self._shutdown_timeout = _finite_positive(shutdown_timeout_seconds, "shutdown timeout")
        if (
            isinstance(maximum_worker_job_memory_mib, bool)
            or not isinstance(maximum_worker_job_memory_mib, int)
            or maximum_worker_job_memory_mib <= 0
        ):
            raise V6ProcessBoundaryError("worker job memory limit must be a positive integer MiB")
        self._job_memory_limit_bytes = maximum_worker_job_memory_mib * 1024 * 1024
        if (
            not isinstance(expected_creation_token_digest, str)
            or len(expected_creation_token_digest) != 64
            or any(character not in "0123456789abcdef" for character in expected_creation_token_digest)
        ):
            raise V6ProcessBoundaryError("creation token digest must be SHA-256")
        self._expected_creation_token_digest = expected_creation_token_digest
        self._expected_static_fixture = expected_static_fixture
        self._now = now
        self._process: subprocess.Popen[bytes] | None = None
        self._job: _WindowsJob | None = None
        self._responses: queue.Queue[Any] = queue.Queue(maxsize=self._pending_limit)
        self._stderr_chunks: deque[bytes] = deque()
        self._stderr_size = 0
        self._stderr_lock = threading.Lock()
        self._operation_lock = threading.Lock()
        self._control_lock = threading.RLock()
        self._stdout_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self._request_sequence = 0
        self.worker_instance_id: str | None = None
        self.root_pid: int | None = None
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
                    item: Any = V6ProcessBoundaryError("worker response exceeded JSONL bound")
                else:
                    try:
                        item = json.loads(line.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        item = V6ProcessBoundaryError(f"malformed worker JSON: {exc}")
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
                            V6ProcessBoundaryError("worker exceeded pending-response bound")
                        )
                    except queue.Full:
                        pass
                    break
            try:
                self._responses.put_nowait(
                    V6ProcessBoundaryError("worker response stream closed")
                )
            except queue.Full:
                pass
        except Exception as exc:
            try:
                self._responses.put_nowait(V6ProcessBoundaryError(f"response reader failed: {exc}"))
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
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        else:
            kwargs["start_new_session"] = True
        return subprocess.Popen(**kwargs)

    def start(self) -> dict[str, Any]:
        with self._control_lock:
            if self.is_running:
                raise V6ProcessBoundaryError("worker is already running")
            started = float(self._now())
            if not math.isfinite(started):
                raise V6ProcessBoundaryError("worker start clock is non-finite")
            process = self._start_process()
            self._process = process
            self.root_pid = process.pid
            try:
                if os.name == "nt":
                    self._job = _WindowsJob(  # type: ignore[attr-defined]
                        int(process._handle), self._job_memory_limit_bytes
                    )
                self._stdout_thread = threading.Thread(
                    target=self._reader, name="blackwell-v6-json-reader", daemon=True
                )
                self._stderr_thread = threading.Thread(
                    target=self._stderr_reader, name="blackwell-v6-stderr-reader", daemon=True
                )
                self._stdout_thread.start()
                self._stderr_thread.start()
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
                ):
                    raise V6ProcessBoundaryError("worker readiness identity mismatch")
                self.worker_instance_id = ready["worker_instance_id"]
                ended = float(self._now())
                if not math.isfinite(ended) or ended < started or ended - started > self._start_timeout:
                    raise V6ProcessBoundaryError("worker readiness exceeded start deadline")
                raw_handle = int(process._handle) if os.name == "nt" else process.pid  # type: ignore[attr-defined]
                process_handle_proof = hashlib.sha256(
                    f"{process.pid}:{raw_handle}:{self.worker_instance_id}:"
                    f"{self._expected_creation_token_digest}".encode("utf-8")
                ).hexdigest()
                return {
                    "started": True,
                    "pid": process.pid,
                    "worker_instance_id": self.worker_instance_id,
                    "command_digest": self.command_digest,
                    "job_or_process_group_owned": True,
                    "job_memory_limit_bytes": self._job_memory_limit_bytes,
                    "creation_token_digest": self._expected_creation_token_digest,
                    "process_handle_owned": True,
                    "process_handle_proof": process_handle_proof,
                    "start_deadline_seconds": self._start_timeout,
                    "elapsed_seconds": ended - started,
                }
            except Exception:
                self.terminate_tree("start_failure")
                raise

    def _send(self, payload: bytes) -> None:
        process = self._process
        if process is None or process.stdin is None or process.poll() is not None:
            raise V6ProcessBoundaryError("worker is not running")
        process.stdin.write(payload + b"\n")
        process.stdin.flush()

    def invoke(self, operation: str, payload: Mapping[str, Any], timeout_seconds: float) -> dict[str, Any]:
        timeout = _finite_positive(timeout_seconds, f"{operation} timeout")
        if not isinstance(operation, str) or not operation:
            raise V6ProcessBoundaryError("operation must be nonempty")
        lock_wait = min(self._lock_timeout, timeout)
        acquired = self._operation_lock.acquire(timeout=lock_wait)
        if not acquired:
            raise V6ProcessTimeout(f"{operation}: IPC lock acquisition timed out")
        started = float(self._now())
        try:
            if not math.isfinite(started):
                raise V6ProcessBoundaryError("operation clock is non-finite")
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
            }
            self._send(_closed_json_bytes(request, self._max_request))
            while True:
                now = float(self._now())
                if not math.isfinite(now) or now < started:
                    self.terminate_tree("invalid_operation_clock")
                    raise V6ProcessBoundaryError("operation clock is invalid")
                remaining = timeout - (now - started)
                if remaining <= 0:
                    termination = self.terminate_tree(f"{operation}_deadline")
                    raise V6ProcessTimeout(
                        f"{operation} timed out; worker tree termination={termination['root_exited']}"
                    )
                try:
                    response = self._responses.get(timeout=remaining)
                except queue.Empty:
                    termination = self.terminate_tree(f"{operation}_deadline")
                    raise V6ProcessTimeout(
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
                }
                process = self._process
                if (
                    not isinstance(response, dict)
                    or set(response) != expected
                    or response["protocol"] != PROTOCOL
                    or response["request_id"] != request_id
                    or response["operation"] != operation
                    or response["worker_instance_id"] != self.worker_instance_id
                    or process is None
                    or response["worker_pid"] != process.pid
                    or not isinstance(response["ok"], bool)
                ):
                    self.terminate_tree("response_identity_failure")
                    raise V6ProcessBoundaryError("worker response identity/schema mismatch")
                ended = float(self._now())
                if not math.isfinite(ended) or ended < started or ended - started > timeout:
                    self.terminate_tree("late_response")
                    raise V6ProcessTimeout(f"{operation}: late response rejected")
                if response["ok"] is not True:
                    raise V6ProcessBoundaryError(
                        f"{operation}: {response['error_type']}:{response['error']}"
                    )
                if response["error_type"] is not None or response["error"] is not None:
                    self.terminate_tree("contradictory_response")
                    raise V6ProcessBoundaryError("successful worker response carried an error")
                return {
                    "value": response["value"],
                    "request_id": request_id,
                    "worker_pid": response["worker_pid"],
                    "worker_instance_id": self.worker_instance_id,
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
            if process is not None and process.poll() is None:
                requested = True
                try:
                    if os.name == "nt":
                        if self._job is None:
                            raise V6ProcessBoundaryError("owned Windows Job Object is absent")
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
    "JsonLineWorkerProcess",
    "PROTOCOL",
    "V6ProcessBoundaryError",
    "V6ProcessTimeout",
]
