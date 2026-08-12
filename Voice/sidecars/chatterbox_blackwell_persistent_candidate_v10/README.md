# Blackwell v10 typed current-process memory repair

Status: **inactive, static-only, default-off, not integrated, pending a fresh
different-agent audit**.

The consumed v9 `attempt_02` reached the exact accepted launcher and direct
worker, then failed during the first `load_before` resource sample. The v8 live
adapter called `GetCurrentProcess` and `GetProcessMemoryInfo` without ctypes
`argtypes`/`restype`. On 64-bit CPython, the default return type is a 32-bit C
`int`; the `-1` current-process pseudo-handle became an invalid pointer-width
handle. The exact Blackwell Python reproduction returned false with WinError 6.
Declaring `GetCurrentProcess.restype = wintypes.HANDLE` and the exact
`GetProcessMemoryInfo` signature made the same read succeed.

V10 adds one inert replacement in `Core/blackwell_v10_windows_memory.py`. It:

- declares all relevant Win32 signatures before the first call;
- continues to use the current-process pseudo-handle and never calls
  `OpenProcess`, changes a DACL, or asks for broader access;
- includes the exact WinError in a fail-closed exception;
- validates finite, internally consistent memory results; and
- can only be installed into the exact preserved v8 live-adapter bytes.

This directory does **not** contain a worker entry, coordinator, live harness,
capability, production switch, or route change. It does not retry v9. Static
tests may read current-process/system memory through Win32, but must not import
Torch, use CUDA, contact Ollama/Qwen, load Chatterbox, synthesize/play audio,
start a person/body, or start Blender.

A different agent must audit the exact v10 seal. Even an accepted static audit
authorizes only later harness authoring—not a live run. A future integration
must be append-only, bind the accepted v9 process topology and exact v8 worker
bytes, be separately sealed and independently audited, and receive a new
one-shot capability before any live attempt.
