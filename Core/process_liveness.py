"""Cross-platform exact-PID liveness checks used by owned local sidecars."""

from __future__ import annotations

import ctypes
import os


def process_is_alive(pid: int) -> bool:
    """Return whether one exact PID is still running without signalling it."""

    try:
        exact_pid = int(pid)
    except (TypeError, ValueError):
        return False
    if exact_pid <= 0:
        return False
    if os.name == "nt":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel32.WaitForSingleObject.restype = ctypes.c_ulong
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int
        handle = kernel32.OpenProcess(0x00101000, False, exact_pid)
        if not handle:
            # Access denied means the PID exists but cannot be queried.  A
            # watchdog must fail safe by retaining its sidecar in that case.
            return ctypes.get_last_error() == 5
        try:
            return kernel32.WaitForSingleObject(handle, 0) == 0x00000102
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(exact_pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False
