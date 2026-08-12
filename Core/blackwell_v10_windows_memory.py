"""Typed Win32 process-memory telemetry for inactive Blackwell v10.

The consumed v9 attempt_02 proved that the v8 adapter called pointer-width
Win32 APIs without ctypes prototypes.  On 64-bit CPython the default C ``int``
return type truncated the ``GetCurrentProcess`` pseudo-handle, so
``GetProcessMemoryInfo`` received an invalid handle.

Importing this module is inert.  It does not open a process, import Torch,
touch CUDA, contact Ollama, synthesize or play audio, or change routing.
"""

from __future__ import annotations

import ctypes
import hashlib
import math
import os
from ctypes import wintypes
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
V8_LIVE_ADAPTER_RELATIVE = (
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/live_adapter.py"
)
V8_LIVE_ADAPTER_SHA256 = (
    "7565203c1d548f576d2264f7c0ee84b16a35dcf5e57ec9f56909ae1278b022eb"
)


class V10MemoryTelemetryError(RuntimeError):
    """Fail-closed typed Win32 telemetry error."""


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _configure_windows_memory_apis(kernel32: Any, psapi: Any) -> None:
    """Declare every pointer-width prototype before the first native call."""

    kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(_MEMORYSTATUSEX)]
    kernel32.GlobalMemoryStatusEx.restype = wintypes.BOOL
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_PROCESS_MEMORY_COUNTERS),
        wintypes.DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL


def _read_windows_memory_mib(
    kernel32: Any,
    psapi: Any,
    *,
    get_last_error: Any = ctypes.get_last_error,
) -> tuple[float, float, float, float]:
    _configure_windows_memory_apis(kernel32, psapi)

    status = _MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)
    ctypes.set_last_error(0)
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        error = int(get_last_error())
        raise V10MemoryTelemetryError(
            f"GlobalMemoryStatusEx failed: WinError {error}"
        )

    counters = _PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    process = kernel32.GetCurrentProcess()
    if process is None:
        error = int(get_last_error())
        raise V10MemoryTelemetryError(
            f"GetCurrentProcess returned a null handle: WinError {error}"
        )
    ctypes.set_last_error(0)
    if not psapi.GetProcessMemoryInfo(
        process, ctypes.byref(counters), wintypes.DWORD(counters.cb)
    ):
        error = int(get_last_error())
        raise V10MemoryTelemetryError(
            f"GetProcessMemoryInfo failed: WinError {error}"
        )

    unit = 1024.0 * 1024.0
    values = (
        counters.WorkingSetSize / unit,
        (status.ullTotalPageFile - status.ullAvailPageFile) / unit,
        status.ullTotalPageFile / unit,
        status.ullAvailPhys / unit,
    )
    if (
        any(not math.isfinite(value) or value < 0 for value in values)
        or values[0] <= 0
        or values[2] <= 0
        or values[1] > values[2]
    ):
        raise V10MemoryTelemetryError("Win32 memory telemetry was non-finite or invalid")
    return values


def windows_memory_mib() -> tuple[float, float, float, float]:
    """Read current-process/system memory using exact pointer-width APIs."""

    if os.name != "nt":
        raise V10MemoryTelemetryError("Blackwell v10 memory telemetry is Windows-only")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    return _read_windows_memory_mib(kernel32, psapi)


def install_into_exact_v8_live_adapter(module: Any) -> dict[str, Any]:
    """Install the replacement only into the exact preserved v8 module object.

    This helper is not called by this candidate.  A later separately sealed and
    audited worker integration may call it after its own live gates pass.
    """

    observed_path = Path(getattr(module, "__file__", "")).resolve(strict=True)
    expected_path = (PROJECT_ROOT / V8_LIVE_ADAPTER_RELATIVE).resolve(strict=True)
    if observed_path != expected_path or _sha256_file(observed_path) != V8_LIVE_ADAPTER_SHA256:
        raise V10MemoryTelemetryError("exact preserved v8 live-adapter bytes are absent")
    current = getattr(module, "_windows_memory_mib", None)
    if not callable(current) or getattr(current, "__name__", "") != "_windows_memory_mib":
        raise V10MemoryTelemetryError("v8 memory probe binding is not exact")
    module._windows_memory_mib = windows_memory_mib
    return {
        "installed": True,
        "target_path": str(observed_path),
        "target_sha256": V8_LIVE_ADAPTER_SHA256,
        "replacement": "Core.blackwell_v10_windows_memory.windows_memory_mib",
        "opens_process": False,
    }


__all__ = [
    "V10MemoryTelemetryError",
    "V8_LIVE_ADAPTER_RELATIVE",
    "V8_LIVE_ADAPTER_SHA256",
    "install_into_exact_v8_live_adapter",
    "windows_memory_mib",
]
