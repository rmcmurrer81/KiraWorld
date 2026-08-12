#!/usr/bin/env python3
"""Default-off retained-generation state engine for Blackwell Voice V20.

This module is an author-sealed, non-live control/worker subject.  It contains
the CPU-park/GPU-restore state machine directly; it does not monkeypatch any
V8/V10 module and it never imports Torch, Chatterbox, Ollama, camera, audio, or
Kira production code.  The only executable factory in these bytes accepts an
explicit author-test fixture authority whose ``execution_authorized`` value is
exactly false.  A future live adapter and execution authority must therefore
be append-only, separately sealed, and differently audited.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import math
import os
import sys
import threading
import time
import types
from ctypes import wintypes
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


CANDIDATE_ID = "kira_blackwell_voice_v20_cpu_park_measured_latency_successor"
EXACT_TEXT_MODEL = "qwen3.5:9b"
EXACT_TEXT_MODEL_DIGEST = (
    "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
)
EXACT_VOICE_PROFILE_SHA256 = (
    "102d17f5420a1a16b3a920204ebde0d532c0a9bfd2979dca28048378ecddc116"
)
EXACT_VOICE_REFERENCE_SHA256 = (
    "2039a2abd600a63c294d69c2b2e4d450c64c850dc6d1c9a4fbfa1700ba92069c"
)
EXACT_CUDA_DEVICE_NAME = "NVIDIA GeForce RTX 5060 Ti"
EXACT_COMPUTE_CAPABILITY = (12, 0)
REQUIRED_COMPONENTS = ("t3", "s3gen", "ve")

AUTHOR_FIXTURE_AUTHORITY_KEYS = {
    "schema",
    "candidate_id",
    "scope",
    "execution_authorized",
    "model_gpu_audio_camera_authorized",
    "session_id",
    "owner_hash",
    "ledger_receipt_sha256",
    "maximum_turns",
    "expires_monotonic_ns",
}
BACKEND_METHODS = (
    "load_conditioned_generation",
    "sample_resources",
    "qwen_absence",
    "cuda_cache_cleanup",
    "synthesize_exact",
    "release_generation",
)


class V20ContractError(RuntimeError):
    """Fail-closed V20 contract error."""


class V20NotAuthorized(V20ContractError):
    """The sealed author package contains no live execution authority."""


class WorkerState(str, Enum):
    UNLOADED = "UNLOADED"
    LOADED_CUDA = "LOADED_CUDA"
    PARKED_CPU = "PARKED_CPU"
    QWEN_OWNED = "QWEN_OWNED"
    SYNTHESIZED = "SYNTHESIZED"
    CLEANUP_DEBT = "CLEANUP_DEBT"
    TERMINAL = "TERMINAL"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _exact_positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise V20ContractError(f"{label} must be an exact positive integer")
    return value


def _finite_nonnegative(value: Any, label: str) -> float:
    if type(value) not in {int, float}:
        raise V20ContractError(f"{label} must be an exact finite number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise V20ContractError(f"{label} must be finite and non-negative")
    return result


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise V20ContractError(f"value is not exact finite canonical JSON: {exc}") from exc


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def monotonic_ns() -> int:
    return time.monotonic_ns()


def _device_type(value: Any) -> str:
    direct = getattr(value, "type", None)
    if direct:
        return str(direct).split(":", 1)[0].strip().casefold()
    text = str(value or "").strip().casefold()
    return text.split(":", 1)[0] if text else ""


def _looks_like_tensor(value: Any) -> bool:
    return all(hasattr(value, name) for name in ("device", "shape", "dtype", "to"))


def _condition_tensors(
    value: Any,
    path: str = "conds",
    seen: set[int] | None = None,
) -> Iterable[tuple[str, Any]]:
    if seen is None:
        seen = set()
    marker = id(value)
    if marker in seen:
        return
    seen.add(marker)
    if _looks_like_tensor(value):
        yield path, value
        return
    if type(value) is dict:
        for key in sorted(value, key=lambda item: str(item)):
            yield from _condition_tensors(value[key], f"{path}.{key}", seen)
        return
    if type(value) in {list, tuple}:
        for index, item in enumerate(value):
            yield from _condition_tensors(item, f"{path}[{index}]", seen)
        return
    namespace = getattr(value, "__dict__", None)
    if type(namespace) is dict:
        for key in sorted(namespace):
            if type(key) is str and not key.startswith("__"):
                yield from _condition_tensors(namespace[key], f"{path}.{key}", seen)


def _tensor_content_bytes(tensor: Any) -> bytes:
    provider = getattr(tensor, "content_bytes", None)
    if callable(provider):
        value = provider()
    else:
        value = tensor
        for method_name in ("detach", "cpu", "contiguous"):
            method = getattr(value, method_name, None)
            if callable(method):
                value = method()
        numpy_method = getattr(value, "numpy", None)
        if not callable(numpy_method):
            raise V20ContractError("tensor cannot provide complete immutable bytes")
        value = numpy_method()
        tobytes = getattr(value, "tobytes", None)
        if not callable(tobytes):
            raise V20ContractError("tensor NumPy value cannot provide complete bytes")
        value = tobytes(order="C")
    if type(value) not in {bytes, bytearray, memoryview}:
        raise V20ContractError("tensor byte provider returned a non-byte exact type")
    return bytes(value)


def _named_tensors(component: Any, plural: str) -> list[tuple[str, Any]]:
    named = getattr(component, f"named_{plural}", None)
    if callable(named):
        values = list(named())
    else:
        plain = getattr(component, plural, None)
        if not callable(plain):
            raise V20ContractError(f"component has no {plural} enumerator")
        values = [(str(index), item) for index, item in enumerate(plain())]
    if any(
        type(item) is not tuple
        or len(item) != 2
        or type(item[0]) is not str
        or not item[0]
        for item in values
    ):
        raise V20ContractError(f"component {plural} names are not exact")
    names = [name for name, _value in values]
    if len(names) != len(set(names)):
        raise V20ContractError(f"component {plural} names are duplicated")
    return values


def generation_snapshot(model: Any, expected_device: str) -> dict[str, Any]:
    """Bind complete required tensor/conditioning bytes and component identity."""

    if expected_device not in {"cpu", "cuda"}:
        raise V20ContractError("generation snapshot device is invalid")
    components: list[dict[str, Any]] = []
    tensor_identities: list[dict[str, Any]] = []
    for component_name in REQUIRED_COMPONENTS:
        component = getattr(model, component_name, None)
        if component is None:
            raise V20ContractError(f"required component is absent: {component_name}")
        records: list[dict[str, Any]] = []
        identities: list[dict[str, Any]] = []
        for plural in ("parameters", "buffers"):
            for name, tensor in _named_tensors(component, plural):
                raw = _tensor_content_bytes(tensor)
                try:
                    shape = [int(item) for item in getattr(tensor, "shape", ())]
                except (TypeError, ValueError) as exc:
                    raise V20ContractError("tensor shape is invalid") from exc
                if any(item < 0 for item in shape):
                    raise V20ContractError("tensor shape contains a negative dimension")
                device = _device_type(getattr(tensor, "device", None))
                if device != expected_device:
                    raise V20ContractError(
                        f"{component_name}.{name} is not entirely on {expected_device}"
                    )
                record = {
                    "kind": plural[:-1],
                    "name": name,
                    "shape": shape,
                    "dtype": str(getattr(tensor, "dtype", "")),
                    "requires_grad": bool(getattr(tensor, "requires_grad", False)),
                    "byte_length": len(raw),
                    "content_sha256": hashlib.sha256(raw).hexdigest(),
                }
                records.append(record)
                identities.append(
                    {
                        "kind": plural[:-1],
                        "name": name,
                        "object_id": id(tensor),
                        "device": device,
                    }
                )
        if not any(record["kind"] == "parameter" for record in records):
            raise V20ContractError(f"required component has no parameters: {component_name}")
        components.append(
            {
                "component": component_name,
                "component_object_id": id(component),
                "tensors": records,
            }
        )
        tensor_identities.append(
            {
                "component": component_name,
                "component_object_id": id(component),
                "tensors": identities,
            }
        )

    conditions: list[dict[str, Any]] = []
    condition_devices: set[str] = set()
    for path, tensor in _condition_tensors(getattr(model, "conds", None)):
        raw = _tensor_content_bytes(tensor)
        device = _device_type(getattr(tensor, "device", None))
        condition_devices.add(device)
        conditions.append(
            {
                "path": path,
                "shape": [int(item) for item in getattr(tensor, "shape", ())],
                "dtype": str(getattr(tensor, "dtype", "")),
                "byte_length": len(raw),
                "content_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    if not conditions or condition_devices != {expected_device}:
        raise V20ContractError("approved-reference conditions are absent or mixed-device")
    if _device_type(getattr(model, "device", None)) != expected_device:
        raise V20ContractError("model device marker does not match all components")
    stable = {
        "components": components,
        "conditions": conditions,
        "reference_sha256": EXACT_VOICE_REFERENCE_SHA256,
    }
    return {
        "expected_device": expected_device,
        "model_object_id": id(model),
        "stable_generation_sha256": canonical_sha256(stable),
        "component_fingerprint": canonical_sha256(components),
        "condition_digest": canonical_sha256(conditions),
        "component_manifest": components,
        "condition_manifest": conditions,
        "tensor_identity_manifest": tensor_identities,
    }


def move_exact_generation(model: Any, target_device: str) -> None:
    if target_device not in {"cpu", "cuda"}:
        raise V20ContractError("target device is invalid")
    for name in REQUIRED_COMPONENTS:
        component = getattr(model, name, None)
        mover = getattr(component, "to", None)
        if component is None or not callable(mover):
            raise V20ContractError(f"required component is not movable: {name}")
        moved = mover(target_device)
        if moved is not None and moved is not component:
            setattr(model, name, moved)
    conditions = getattr(model, "conds", None)
    mover = getattr(conditions, "to", None)
    if conditions is None or not callable(mover):
        raise V20ContractError("approved-reference conditions are not movable")
    moved = mover(target_device)
    if moved is not None:
        model.conds = moved
    model.device = target_device


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


def configure_windows_memory_apis(kernel32: Any, psapi: Any) -> None:
    """Declare every pointer-width Win32 memory prototype before use."""

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


def read_windows_memory_bytes(
    kernel32: Any | None = None,
    psapi: Any | None = None,
    *,
    get_last_error: Callable[[], int] = ctypes.get_last_error,
) -> dict[str, int]:
    """Read exact typed memory values; no process is opened or discovered."""

    if kernel32 is None or psapi is None:
        if os.name != "nt":
            raise V20ContractError("typed V20 memory telemetry is Windows-only")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
    configure_windows_memory_apis(kernel32, psapi)
    status = _MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)
    ctypes.set_last_error(0)
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise V20ContractError(
            f"GlobalMemoryStatusEx failed: WinError {int(get_last_error())}"
        )
    counters = _PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    process = kernel32.GetCurrentProcess()
    if process is None:
        raise V20ContractError(
            f"GetCurrentProcess returned null: WinError {int(get_last_error())}"
        )
    ctypes.set_last_error(0)
    if not psapi.GetProcessMemoryInfo(
        process, ctypes.byref(counters), wintypes.DWORD(counters.cb)
    ):
        raise V20ContractError(
            f"GetProcessMemoryInfo failed: WinError {int(get_last_error())}"
        )
    values = {
        "process_rss_bytes": int(counters.WorkingSetSize),
        "commit_used_bytes": int(status.ullTotalPageFile - status.ullAvailPageFile),
        "commit_limit_bytes": int(status.ullTotalPageFile),
        "available_physical_bytes": int(status.ullAvailPhys),
        "total_physical_bytes": int(status.ullTotalPhys),
    }
    if (
        any(type(value) is not int or value < 0 for value in values.values())
        or values["process_rss_bytes"] <= 0
        or values["commit_limit_bytes"] <= 0
        or values["commit_used_bytes"] > values["commit_limit_bytes"]
        or values["available_physical_bytes"] > values["total_physical_bytes"]
    ):
        raise V20ContractError("typed Win32 memory values are internally invalid")
    return values


def _code_fingerprint(code: types.CodeType) -> str:
    consts: list[Any] = []
    for value in code.co_consts:
        if type(value) is types.CodeType:
            consts.append({"nested_code": _code_fingerprint(value)})
        elif value is None or type(value) in {str, int, float, bool, bytes}:
            consts.append({"type": type(value).__name__, "repr": repr(value)})
        elif type(value) in {tuple, frozenset}:
            consts.append({"type": type(value).__name__, "repr": repr(value)})
        else:
            consts.append(
                {
                    "type": f"{type(value).__module__}.{type(value).__qualname__}",
                    "repr": repr(value),
                }
            )
    payload = {
        "co_argcount": code.co_argcount,
        "co_posonlyargcount": code.co_posonlyargcount,
        "co_kwonlyargcount": code.co_kwonlyargcount,
        "co_nlocals": code.co_nlocals,
        "co_stacksize": code.co_stacksize,
        "co_flags": code.co_flags,
        "co_code_sha256": hashlib.sha256(code.co_code).hexdigest(),
        "co_exceptiontable_sha256": hashlib.sha256(
            getattr(code, "co_exceptiontable", b"")
        ).hexdigest(),
        "co_names": list(code.co_names),
        "co_varnames": list(code.co_varnames),
        "co_freevars": list(code.co_freevars),
        "co_cellvars": list(code.co_cellvars),
        "co_consts": consts,
    }
    return canonical_sha256(payload)


def _binding_value(value: Any, seen: set[int] | None = None) -> dict[str, Any]:
    if seen is None:
        seen = set()
    if value is None or type(value) in {str, int, bool}:
        return {"kind": "exact_atom", "type": type(value).__name__, "value": value}
    if type(value) is float:
        if not math.isfinite(value):
            raise V20ContractError("callable binding contains non-finite float")
        return {"kind": "exact_atom", "type": "float", "repr": repr(value)}
    if type(value) is bytes:
        return {
            "kind": "bytes",
            "length": len(value),
            "sha256": hashlib.sha256(value).hexdigest(),
        }
    if type(value) in {tuple, list, set, frozenset, dict}:
        marker = id(value)
        if marker in seen:
            raise V20ContractError("callable binding contains a recursive container")
        seen.add(marker)
        if type(value) is dict:
            items = [
                {
                    "key": _binding_value(key, seen),
                    "value": _binding_value(item, seen),
                }
                for key, item in value.items()
            ]
            items = sorted(items, key=canonical_sha256)
        else:
            items = [_binding_value(item, seen) for item in value]
        seen.remove(marker)
        if type(value) in {set, frozenset}:
            items = sorted(items, key=canonical_sha256)
        return {"kind": type(value).__name__, "items": items}
    if type(value) is types.ModuleType:
        raw_file = getattr(value, "__file__", None)
        file_record: dict[str, Any] | None = None
        if type(raw_file) is str and raw_file:
            try:
                path = Path(raw_file).resolve(strict=True)
                file_record = {
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            except (OSError, RuntimeError):
                file_record = {"path": str(raw_file), "unresolved": True}
        return {
            "kind": "module",
            "name": str(getattr(value, "__name__", "")),
            "object_id": id(value),
            "file": file_record,
        }
    if type(value) is types.FunctionType:
        return {
            "kind": "function",
            "module": value.__module__,
            "qualname": value.__qualname__,
            "object_id": id(value),
            "code_sha256": _code_fingerprint(value.__code__),
        }
    if isinstance(value, type):
        return {
            "kind": "type",
            "module": value.__module__,
            "qualname": value.__qualname__,
            "object_id": id(value),
        }
    return {
        "kind": "object",
        "type": f"{type(value).__module__}.{type(value).__qualname__}",
        "object_id": id(value),
    }


def callable_binding(value: Any) -> dict[str, Any]:
    function = value.__func__ if type(value) is types.MethodType else value
    bound_self = value.__self__ if type(value) is types.MethodType else None
    if type(function) is not types.FunctionType:
        raise V20ContractError("control/backend callable is not an exact Python function")
    closure = []
    for cell in function.__closure__ or ():
        try:
            closure.append(_binding_value(cell.cell_contents))
        except ValueError as exc:
            raise V20ContractError("callable contains an empty closure cell") from exc
    referenced_globals = {
        name: _binding_value(function.__globals__[name])
        for name in sorted(set(function.__code__.co_names))
        if name != "__builtins__" and name in function.__globals__
    }
    return {
        "function_object_id": id(function),
        "bound_self_object_id": id(bound_self) if bound_self is not None else None,
        "module": function.__module__,
        "qualname": function.__qualname__,
        "code_sha256": _code_fingerprint(function.__code__),
        "defaults": _binding_value(function.__defaults__),
        "kwdefaults": _binding_value(function.__kwdefaults__),
        "closure": closure,
        "referenced_globals": referenced_globals,
    }


CONTROL_HELPER_NAMES = (
    "canonical_bytes",
    "canonical_sha256",
    "generation_snapshot",
    "move_exact_generation",
    "validate_resource_sample",
    "validate_qwen_completion_receipt",
    "callable_binding",
)

WORKER_CONTROL_METHOD_NAMES = (
    "live_candidate",
    "author_fixture",
    "__init__",
    "_clock",
    "_verify_graph",
    "_preflight",
    "_postflight",
    "_resource",
    "_backend_call",
    "_record",
    "_assert_generation",
    "_owned_transfer",
    "_fail_closed",
    "load_once",
    "park_for_qwen",
    "enter_qwen_window",
    "complete_qwen_window",
    "restore_for_synthesis",
    "synthesize_fixture_and_park",
    "close_fixture",
    "status",
)


class ControlBinding:
    """Runtime identity snapshot for the exact control and backend graph."""

    def __init__(self, backend: Any, worker_source_sha256: str) -> None:
        if not _is_sha256(worker_source_sha256):
            raise V20ContractError("worker source SHA-256 is invalid")
        module = sys.modules.get(__name__)
        if type(module) is not types.ModuleType:
            raise V20ContractError("canonical V20 control module object is absent")
        source = Path(__file__).resolve(strict=True)
        if sha256_file(source) != worker_source_sha256:
            raise V20ContractError("V20 worker source bytes do not match binding")
        self.module = module
        self.module_name = __name__
        self.module_object_id = id(module)
        self.source_path = source
        self.source_sha256 = worker_source_sha256
        self.control_callables = {
            name: callable_binding(getattr(module, name)) for name in CONTROL_HELPER_NAMES
        }
        worker_class = getattr(module, "RetainedGenerationWorkerV20", None)
        if type(worker_class) is not type:
            raise V20ContractError("canonical V20 worker class is absent")
        self.worker_class = worker_class
        self.worker_class_object_id = id(worker_class)
        self.worker_method_descriptors: dict[str, Any] = {}
        self.worker_method_callables: dict[str, dict[str, Any]] = {}
        for name in WORKER_CONTROL_METHOD_NAMES:
            descriptor = worker_class.__dict__.get(name)
            if type(descriptor) is classmethod:
                function = descriptor.__func__
            elif type(descriptor) is types.FunctionType:
                function = descriptor
            else:
                raise V20ContractError(f"V20 worker method descriptor is not exact: {name}")
            self.worker_method_descriptors[name] = descriptor
            self.worker_method_callables[name] = callable_binding(function)
        self.backend = backend
        self.backend_object_id = id(backend)
        self.backend_class = type(backend)
        self.backend_class_object_id = id(type(backend))
        backend_module = sys.modules.get(type(backend).__module__)
        if type(backend_module) is not types.ModuleType:
            raise V20ContractError("backend canonical module object is absent")
        self.backend_module = backend_module
        self.backend_module_name = type(backend).__module__
        self.backend_module_object_id = id(backend_module)
        self.backend_callables: dict[str, dict[str, Any]] = {}
        self.backend_bound_objects: dict[str, Any] = {}
        for name in BACKEND_METHODS:
            method = getattr(backend, name, None)
            if type(method) is not types.MethodType:
                raise V20ContractError(f"backend method is not exact: {name}")
            self.backend_bound_objects[name] = method
            self.backend_callables[name] = callable_binding(method)

    def verify(self) -> None:
        if (
            sys.modules.get(self.module_name) is not self.module
            or id(self.module) != self.module_object_id
            or Path(getattr(self.module, "__file__", "")).resolve(strict=True)
            != self.source_path
            or sha256_file(self.source_path) != self.source_sha256
        ):
            raise V20ContractError("canonical V20 control module/path/bytes drift")
        for name, expected in self.control_callables.items():
            current = getattr(self.module, name, None)
            if type(current) is not types.FunctionType or callable_binding(current) != expected:
                raise V20ContractError(f"V20 control callable drift: {name}")
        if (
            getattr(self.module, "RetainedGenerationWorkerV20", None) is not self.worker_class
            or id(self.worker_class) != self.worker_class_object_id
        ):
            raise V20ContractError("canonical V20 worker class drift")
        for name, expected in self.worker_method_callables.items():
            descriptor = self.worker_class.__dict__.get(name)
            if descriptor is not self.worker_method_descriptors[name]:
                raise V20ContractError(f"V20 worker method descriptor drift: {name}")
            function = descriptor.__func__ if type(descriptor) is classmethod else descriptor
            if type(function) is not types.FunctionType or callable_binding(function) != expected:
                raise V20ContractError(f"V20 worker method callable drift: {name}")
        if (
            id(self.backend) != self.backend_object_id
            or type(self.backend) is not self.backend_class
            or id(type(self.backend)) != self.backend_class_object_id
            or sys.modules.get(self.backend_module_name) is not self.backend_module
            or id(self.backend_module) != self.backend_module_object_id
        ):
            raise V20ContractError("canonical backend object/class/module drift")
        for name, expected in self.backend_callables.items():
            current = getattr(self.backend, name, None)
            if type(current) is not types.MethodType or callable_binding(current) != expected:
                raise V20ContractError(f"backend callable drift: {name}")


RESOURCE_KEYS = {
    "schema",
    "sample_id",
    "sample_sequence",
    "captured_monotonic_ns",
    "worker_pid",
    "process_rss_bytes",
    "commit_used_bytes",
    "commit_limit_bytes",
    "available_physical_bytes",
    "total_physical_bytes",
    "cuda_allocated_bytes",
    "cuda_reserved_bytes",
    "cuda_free_bytes",
    "cuda_total_bytes",
    "cuda_device_name",
    "compute_capability",
    "qwen_records",
    "voice_device",
}


def validate_resource_sample(
    raw: Any,
    *,
    worker_pid: int,
    minimum_sequence: int,
    now_ns: int,
) -> dict[str, Any]:
    if type(raw) is not dict or set(raw) != RESOURCE_KEYS:
        raise V20ContractError("resource sample schema is not exact")
    value = dict(raw)
    if value["schema"] != "kira.blackwell.voice_v20.resource_sample.v1":
        raise V20ContractError("resource sample schema identity mismatch")
    if type(value["sample_sequence"]) is not int or value["sample_sequence"] < minimum_sequence:
        raise V20ContractError("resource sample sequence is stale or non-integer")
    if type(value["captured_monotonic_ns"]) is not int:
        raise V20ContractError("resource monotonic timestamp is not exact integer")
    if not 0 <= value["captured_monotonic_ns"] <= now_ns:
        raise V20ContractError("resource sample timestamp is future or invalid")
    if now_ns - value["captured_monotonic_ns"] > 2_000_000_000:
        raise V20ContractError("resource sample is older than two seconds")
    if type(value["worker_pid"]) is not int or value["worker_pid"] != worker_pid:
        raise V20ContractError("resource worker PID mismatch")
    numeric = (
        "process_rss_bytes",
        "commit_used_bytes",
        "commit_limit_bytes",
        "available_physical_bytes",
        "total_physical_bytes",
        "cuda_allocated_bytes",
        "cuda_reserved_bytes",
        "cuda_free_bytes",
        "cuda_total_bytes",
    )
    if any(type(value[key]) is not int or value[key] < 0 for key in numeric):
        raise V20ContractError("resource byte value is not an exact non-negative integer")
    if (
        value["process_rss_bytes"] <= 0
        or value["commit_limit_bytes"] <= 0
        or value["commit_used_bytes"] > value["commit_limit_bytes"]
        or value["available_physical_bytes"] > value["total_physical_bytes"]
        or value["cuda_total_bytes"] <= 0
        or value["cuda_free_bytes"] > value["cuda_total_bytes"]
        or value["cuda_allocated_bytes"] > value["cuda_total_bytes"]
        or value["cuda_reserved_bytes"] > value["cuda_total_bytes"]
    ):
        raise V20ContractError("resource sample values are internally inconsistent")
    if value["cuda_device_name"] != EXACT_CUDA_DEVICE_NAME:
        raise V20ContractError("resource CUDA device identity mismatch")
    if value["compute_capability"] != [12, 0]:
        raise V20ContractError("resource compute capability mismatch")
    if value["voice_device"] not in {"none", "cpu", "cuda"}:
        raise V20ContractError("resource voice device is invalid")
    qwen_records = value["qwen_records"]
    if type(qwen_records) is not list or any(
        type(item) is not dict
        or set(item) != {"model", "digest"}
        or item["model"] != EXACT_TEXT_MODEL
        or item["digest"] != EXACT_TEXT_MODEL_DIGEST
        for item in qwen_records
    ):
        raise V20ContractError("resource Qwen residency records are not exact")
    expected_id = canonical_sha256({key: value[key] for key in sorted(RESOURCE_KEYS - {"sample_id"})})
    if value["sample_id"] != expected_id:
        raise V20ContractError("resource sample digest mismatch")
    return value


QWEN_RECEIPT_KEYS = {
    "schema",
    "turn_id",
    "model",
    "digest",
    "owner_hash",
    "session_id",
    "token_hash",
    "request_sha256",
    "response_text_sha256",
    "load_started_ns",
    "load_completed_ns",
    "generation_started_ns",
    "first_token_ns",
    "generation_completed_ns",
    "unload_started_ns",
    "unload_completed_ns",
    "keep_alive",
    "qwen_absent_after",
    "voice_cuda_overlap",
    "receipt_sha256",
}


def validate_qwen_completion_receipt(
    raw: Any,
    *,
    turn_id: str,
    owner_hash: str,
    session_id: str,
) -> dict[str, Any]:
    if type(raw) is not dict or set(raw) != QWEN_RECEIPT_KEYS:
        raise V20ContractError("Qwen completion receipt schema is not exact")
    value = dict(raw)
    if (
        type(value["schema"]) is not str
        or value["schema"] != "kira.blackwell.voice_v20.qwen_completion_receipt.v1"
        or type(value["model"]) is not str
        or type(value["digest"]) is not str
        or type(value["owner_hash"]) is not str
        or type(value["session_id"]) is not str
        or value["turn_id"] != turn_id
        or value["model"] != EXACT_TEXT_MODEL
        or value["digest"] != EXACT_TEXT_MODEL_DIGEST
        or value["owner_hash"] != owner_hash
        or value["session_id"] != session_id
        or type(value["keep_alive"]) is not int
        or value["keep_alive"] != 0
        or value["qwen_absent_after"] is not True
        or value["voice_cuda_overlap"] is not False
    ):
        raise V20ContractError("Qwen completion identity/truth binding failed")
    for key in ("token_hash", "request_sha256", "response_text_sha256"):
        if not _is_sha256(value[key]):
            raise V20ContractError(f"Qwen completion hash is invalid: {key}")
    times = [
        value[key]
        for key in (
            "load_started_ns",
            "load_completed_ns",
            "generation_started_ns",
            "first_token_ns",
            "generation_completed_ns",
            "unload_started_ns",
            "unload_completed_ns",
        )
    ]
    if (
        any(type(item) is not int or item <= 0 for item in times)
        or any(left >= right for left, right in zip(times, times[1:]))
    ):
        raise V20ContractError("Qwen completion timestamps are not exact monotonic order")
    expected = canonical_sha256({key: value[key] for key in sorted(QWEN_RECEIPT_KEYS - {"receipt_sha256"})})
    if value["receipt_sha256"] != expected:
        raise V20ContractError("Qwen completion receipt digest mismatch")
    return value


def validate_author_fixture_authority(raw: Any, *, now_ns: int) -> dict[str, Any]:
    if type(raw) is not dict or set(raw) != AUTHOR_FIXTURE_AUTHORITY_KEYS:
        raise V20NotAuthorized("author fixture authority schema is not exact")
    value = dict(raw)
    if (
        value["schema"] != "kira.blackwell.voice_v20.author_fixture_authority.v1"
        or value["candidate_id"] != CANDIDATE_ID
        or value["scope"] != "AUTHOR_STATIC_MOCK_ONLY"
        or value["execution_authorized"] is not False
        or value["model_gpu_audio_camera_authorized"] is not False
    ):
        raise V20NotAuthorized("sealed V20 package contains no live execution authority")
    for key in ("session_id", "owner_hash", "ledger_receipt_sha256"):
        if not _is_sha256(value[key]):
            raise V20NotAuthorized(f"fixture authority hash is invalid: {key}")
    if type(value["maximum_turns"]) is not int or not 1 <= value["maximum_turns"] <= 4:
        raise V20NotAuthorized("fixture maximum turn count must be exact 1..4")
    if type(value["expires_monotonic_ns"]) is not int or value["expires_monotonic_ns"] <= now_ns:
        raise V20NotAuthorized("fixture authority is expired or non-integer")
    return value


def author_fixture_authority(
    *,
    session_id: str,
    owner_hash: str,
    ledger_receipt_sha256: str,
    maximum_turns: int,
    expires_monotonic_ns: int,
) -> dict[str, Any]:
    return {
        "schema": "kira.blackwell.voice_v20.author_fixture_authority.v1",
        "candidate_id": CANDIDATE_ID,
        "scope": "AUTHOR_STATIC_MOCK_ONLY",
        "execution_authorized": False,
        "model_gpu_audio_camera_authorized": False,
        "session_id": session_id,
        "owner_hash": owner_hash,
        "ledger_receipt_sha256": ledger_receipt_sha256,
        "maximum_turns": maximum_turns,
        "expires_monotonic_ns": expires_monotonic_ns,
    }


def _validate_qwen_absence(raw: Any) -> dict[str, Any]:
    keys = {
        "query_succeeded",
        "qwen_absent_proven",
        "qwen_records",
        "model_state_changed",
        "model",
        "digest",
    }
    if type(raw) is not dict or set(raw) != keys:
        raise V20ContractError("Qwen absence evidence schema is not exact")
    value = dict(raw)
    if (
        value["query_succeeded"] is not True
        or value["qwen_absent_proven"] is not True
        or value["qwen_records"] != []
        or value["model_state_changed"] is not False
        or value["model"] != EXACT_TEXT_MODEL
        or value["digest"] != EXACT_TEXT_MODEL_DIGEST
    ):
        raise V20ContractError("exact Qwen absence was not proven")
    return value


def _identity_replacement_count(
    before: list[dict[str, Any]], after: list[dict[str, Any]]
) -> int:
    def flatten(value: list[dict[str, Any]]) -> dict[tuple[str, str, str], int]:
        return {
            (component["component"], tensor["kind"], tensor["name"]): tensor["object_id"]
            for component in value
            for tensor in component["tensors"]
        }

    old = flatten(before)
    new = flatten(after)
    if set(old) != set(new):
        raise V20ContractError("tensor identity schema changed during owned transfer")
    return sum(old[key] != new[key] for key in old)


class RetainedGenerationWorkerV20:
    """Direct retained-generation state engine, runnable only with mock authority."""

    @classmethod
    def live_candidate(cls, *_args: Any, **_kwargs: Any) -> "RetainedGenerationWorkerV20":
        raise V20NotAuthorized(
            "V20 author package has no live backend, execution authority, or production route"
        )

    @classmethod
    def author_fixture(
        cls,
        *,
        backend: Any,
        authority: Mapping[str, Any],
        worker_source_sha256: str,
        now_ns: Callable[[], int] = monotonic_ns,
        worker_pid: int | None = None,
    ) -> "RetainedGenerationWorkerV20":
        return cls(
            backend=backend,
            authority=authority,
            worker_source_sha256=worker_source_sha256,
            now_ns=now_ns,
            worker_pid=worker_pid,
            _author_fixture_exact=True,
        )

    def __init__(
        self,
        *,
        backend: Any,
        authority: Mapping[str, Any],
        worker_source_sha256: str,
        now_ns: Callable[[], int],
        worker_pid: int | None,
        _author_fixture_exact: bool,
    ) -> None:
        if _author_fixture_exact is not True:
            raise V20NotAuthorized("only exact author fixture construction exists in V20")
        initial_now = now_ns()
        if type(initial_now) is not int or initial_now < 0:
            raise V20ContractError("monotonic-nanosecond clock is invalid")
        self.authority = validate_author_fixture_authority(dict(authority), now_ns=initial_now)
        self.backend = backend
        self._backend_object_id = id(backend)
        self._now_ns = now_ns
        self._now_callable_binding = callable_binding(now_ns)
        self.worker_pid = int(worker_pid if worker_pid is not None else os.getpid())
        if self.worker_pid <= 0:
            raise V20ContractError("worker PID is invalid")
        self._binding = ControlBinding(backend, worker_source_sha256)
        self._binding_object_id = id(self._binding)
        self._lock = threading.RLock()
        self.state = WorkerState.UNLOADED
        self.model: Any | None = None
        self.model_object_id: int | None = None
        self.generation_id: str | None = None
        self.component_fingerprint: str | None = None
        self.condition_digest: str | None = None
        self.stable_generation_sha256: str | None = None
        self._stable_component_manifest: list[dict[str, Any]] = []
        self._stable_condition_manifest: list[dict[str, Any]] = []
        self._tensor_identity_manifest: list[dict[str, Any]] = []
        self._resource_sequence = 0
        self._transition_sequence = 0
        self._transfer_sequence = 0
        self._turn_count = 0
        self._current_turn: dict[str, Any] | None = None
        self.transition_ledger: list[dict[str, Any]] = []
        self.transfer_ledger: list[dict[str, Any]] = []
        self.cleanup_debt: list[str] = []
        self.terminal_outcome: dict[str, Any] | None = None

    def _clock(self, label: str) -> int:
        if callable_binding(self._now_ns) != self._now_callable_binding:
            raise V20ContractError("monotonic clock callable binding drift")
        value = self._now_ns()
        if type(value) is not int or value < 0:
            raise V20ContractError(f"{label}: monotonic clock is invalid")
        return value

    def _verify_graph(self) -> None:
        if id(self._binding) != self._binding_object_id or id(self.backend) != self._backend_object_id:
            raise V20ContractError("V20 binding/backend object drift")
        self._binding.verify()
        if self.authority["execution_authorized"] is not False:
            raise V20NotAuthorized("author fixture authority was widened")

    def _preflight(
        self,
        *,
        deadline_ns: int,
        cancel_event: threading.Event | None,
        label: str,
    ) -> int:
        self._verify_graph()
        now = self._clock(label)
        if type(deadline_ns) is not int or deadline_ns <= now:
            raise V20ContractError(f"{label}: finite deadline is absent or expired")
        if deadline_ns > self.authority["expires_monotonic_ns"]:
            raise V20ContractError(f"{label}: deadline exceeds fixture authority")
        if cancel_event is not None:
            if type(cancel_event) is not threading.Event:
                raise V20ContractError(f"{label}: cancellation object is not exact Event")
            if cancel_event.is_set():
                raise V20ContractError(f"{label}: cancelled before entry")
        return now

    def _postflight(
        self,
        *,
        deadline_ns: int,
        cancel_event: threading.Event | None,
        label: str,
    ) -> int:
        self._verify_graph()
        now = self._clock(label)
        if now > deadline_ns:
            raise V20ContractError(f"{label}: operation exceeded finite deadline")
        if cancel_event is not None and cancel_event.is_set():
            raise V20ContractError(f"{label}: cancellation observed before commit")
        return now

    def _resource(self, label: str) -> dict[str, Any]:
        raw = self._backend_call("sample_resources", label=label, worker_pid=self.worker_pid)
        now = self._clock(f"{label}.resource_validate")
        sample = validate_resource_sample(
            raw,
            worker_pid=self.worker_pid,
            minimum_sequence=self._resource_sequence + 1,
            now_ns=now,
        )
        self._resource_sequence = sample["sample_sequence"]
        commit_fraction = sample["commit_used_bytes"] / sample["commit_limit_bytes"]
        if commit_fraction > 0.82:
            raise V20ContractError("system commit exceeds the V20 author proposal")
        if sample["available_physical_bytes"] < 6144 * 1024 * 1024:
            raise V20ContractError("available physical memory is below 6,144 MiB")
        if self.state is WorkerState.PARKED_CPU and sample["process_rss_bytes"] > 10240 * 1024 * 1024:
            raise V20ContractError("parked worker RSS exceeds 10,240 MiB")
        if self.state is WorkerState.UNLOADED and sample["voice_device"] != "none":
            raise V20ContractError("unloaded worker reports resident voice components")
        if self.state in {WorkerState.LOADED_CUDA, WorkerState.SYNTHESIZED} and (
            sample["voice_device"] != "cuda" or sample["qwen_records"]
        ):
            raise V20ContractError("loaded CUDA voice overlaps Qwen or is not CUDA resident")
        if self.state is WorkerState.PARKED_CPU and (
            sample["voice_device"] != "cpu" or sample["qwen_records"]
        ):
            raise V20ContractError("parked voice is not CPU-only with Qwen absent")
        return sample

    def _backend_call(self, name: str, /, **kwargs: Any) -> Any:
        self._verify_graph()
        if name not in self._binding.backend_bound_objects:
            raise V20ContractError(f"backend call is outside exact graph: {name}")
        return self._binding.backend_bound_objects[name](**kwargs)

    def _record(
        self,
        *,
        operation: str,
        from_state: WorkerState,
        to_state: WorkerState,
        entered_ns: int,
        returned_ns: int,
        deadline_ns: int,
        resources_before: Mapping[str, Any] | None,
        resources_after: Mapping[str, Any] | None,
        turn_id: str | None,
        details: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if returned_ns < entered_ns or returned_ns > deadline_ns:
            raise V20ContractError("transition timing is not monotonic and bounded")
        self._transition_sequence += 1
        record: dict[str, Any] = {
            "schema": "kira.blackwell.voice_v20.transition.v1",
            "sequence": self._transition_sequence,
            "operation": operation,
            "from_state": from_state.value,
            "to_state": to_state.value,
            "entered_monotonic_ns": entered_ns,
            "returned_monotonic_ns": returned_ns,
            "deadline_monotonic_ns": deadline_ns,
            "session_id": self.authority["session_id"],
            "owner_hash": self.authority["owner_hash"],
            "ledger_receipt_sha256": self.authority["ledger_receipt_sha256"],
            "generation_id": self.generation_id,
            "turn_id": turn_id,
            "resources_before_sha256": (
                canonical_sha256(dict(resources_before)) if resources_before is not None else None
            ),
            "resources_after_sha256": (
                canonical_sha256(dict(resources_after)) if resources_after is not None else None
            ),
            "cleanup_debt": bool(self.cleanup_debt),
            "details": dict(details or {}),
        }
        record["record_sha256"] = canonical_sha256(record)
        self.transition_ledger.append(record)
        return dict(record)

    def _assert_generation(self, expected_device: str) -> dict[str, Any]:
        if self.model is None or id(self.model) != self.model_object_id:
            raise V20ContractError("retained model object is absent or replaced")
        snapshot = generation_snapshot(self.model, expected_device)
        if (
            snapshot["model_object_id"] != self.model_object_id
            or snapshot["stable_generation_sha256"] != self.stable_generation_sha256
            or snapshot["component_fingerprint"] != self.component_fingerprint
            or snapshot["condition_digest"] != self.condition_digest
            or snapshot["component_manifest"] != self._stable_component_manifest
            or snapshot["condition_manifest"] != self._stable_condition_manifest
        ):
            raise V20ContractError("retained model generation/conditioning/content drift")
        return snapshot

    def _owned_transfer(self, source: str, target: str) -> dict[str, Any]:
        before = self._assert_generation(source)
        move_exact_generation(self.model, target)
        cleanup = None
        if target == "cpu":
            cleanup = self._backend_call("cuda_cache_cleanup")
            if cleanup != {
                "cache_cleared": True,
                "synchronize_before": True,
                "empty_cache_called": True,
                "synchronize_after": True,
            }:
                raise V20ContractError("CUDA cache cleanup proof is not exact")
        after = self._assert_generation(target)
        self._transfer_sequence += 1
        record = {
            "schema": "kira.blackwell.voice_v20.owned_transfer.v1",
            "transfer_sequence": self._transfer_sequence,
            "generation_id": self.generation_id,
            "from_device": source,
            "to_device": target,
            "stable_generation_sha256": self.stable_generation_sha256,
            "component_fingerprint": self.component_fingerprint,
            "condition_digest": self.condition_digest,
            "before_tensor_identity_sha256": canonical_sha256(
                before["tensor_identity_manifest"]
            ),
            "after_tensor_identity_sha256": canonical_sha256(
                after["tensor_identity_manifest"]
            ),
            "replaced_tensor_object_count": _identity_replacement_count(
                before["tensor_identity_manifest"], after["tensor_identity_manifest"]
            ),
            "component_objects_unchanged": True,
            "complete_component_and_condition_bytes_unchanged": True,
            "cuda_cleanup": cleanup,
        }
        record["record_sha256"] = canonical_sha256(record)
        self._tensor_identity_manifest = after["tensor_identity_manifest"]
        self.transfer_ledger.append(record)
        return dict(record)

    def _fail_closed(self, operation: str, exc: Exception) -> None:
        errors = [f"{operation}:{type(exc).__name__}:{exc}"]
        released = False
        try:
            self._verify_graph()
            value = self._binding.backend_bound_objects["release_generation"](
                reason=f"{operation}_failure"
            )
            released = value == {
                "released": True,
                "owned_model_count": 0,
                "owned_condition_count": 0,
            }
            if not released:
                errors.append("release_generation_not_proven")
        except Exception as cleanup_exc:
            errors.append(f"cleanup:{type(cleanup_exc).__name__}:{cleanup_exc}")
        self.model = None
        self.model_object_id = None
        self.generation_id = None
        self.component_fingerprint = None
        self.condition_digest = None
        self.stable_generation_sha256 = None
        self._stable_component_manifest = []
        self._stable_condition_manifest = []
        self._tensor_identity_manifest = []
        self._current_turn = None
        self.cleanup_debt = [] if released else errors
        self.state = WorkerState.TERMINAL if released else WorkerState.CLEANUP_DEBT
        raise V20ContractError("; ".join(errors)) from exc

    def load_once(
        self,
        *,
        deadline_ns: int,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            try:
                entered = self._preflight(
                    deadline_ns=deadline_ns,
                    cancel_event=cancel_event,
                    label="load.entered",
                )
                if self.state is not WorkerState.UNLOADED:
                    raise V20ContractError("one exact conditioned generation may load only once")
                from_state = self.state
                _validate_qwen_absence(self._backend_call("qwen_absence", phase="load_before"))
                resources_before = self._resource("load_before")
                loaded = self._backend_call(
                    "load_conditioned_generation",
                    profile_sha256=EXACT_VOICE_PROFILE_SHA256,
                    reference_sha256=EXACT_VOICE_REFERENCE_SHA256,
                    required_components=list(REQUIRED_COMPONENTS),
                    worker_pid=self.worker_pid,
                    session_id=self.authority["session_id"],
                )
                exact_keys = {
                    "model",
                    "profile_sha256",
                    "reference_sha256",
                    "load_count",
                    "conditioning_count",
                    "route",
                    "device",
                    "generic_voice_used",
                    "sapi_voice_used",
                    "fallback_used",
                }
                if type(loaded) is not dict or set(loaded) != exact_keys:
                    raise V20ContractError("conditioned-generation load schema is not exact")
                if (
                    loaded["profile_sha256"] != EXACT_VOICE_PROFILE_SHA256
                    or loaded["reference_sha256"] != EXACT_VOICE_REFERENCE_SHA256
                    or type(loaded["load_count"]) is not int
                    or loaded["load_count"] != 1
                    or type(loaded["conditioning_count"]) is not int
                    or loaded["conditioning_count"] != 1
                    or loaded["route"] != "blackwell_gpu"
                    or loaded["device"] != "cuda"
                    or loaded["generic_voice_used"] is not False
                    or loaded["sapi_voice_used"] is not False
                    or loaded["fallback_used"] is not False
                ):
                    raise V20ContractError("conditioned-generation load identity/truth failed")
                self.model = loaded["model"]
                self.model_object_id = id(self.model)
                snapshot = generation_snapshot(self.model, "cuda")
                self.stable_generation_sha256 = snapshot["stable_generation_sha256"]
                self.component_fingerprint = snapshot["component_fingerprint"]
                self.condition_digest = snapshot["condition_digest"]
                self._stable_component_manifest = snapshot["component_manifest"]
                self._stable_condition_manifest = snapshot["condition_manifest"]
                self._tensor_identity_manifest = snapshot["tensor_identity_manifest"]
                self.generation_id = canonical_sha256(
                    {
                        "candidate_id": CANDIDATE_ID,
                        "session_id": self.authority["session_id"],
                        "worker_pid": self.worker_pid,
                        "model_object_id": self.model_object_id,
                        "stable_generation_sha256": self.stable_generation_sha256,
                        "profile_sha256": EXACT_VOICE_PROFILE_SHA256,
                        "reference_sha256": EXACT_VOICE_REFERENCE_SHA256,
                        "load_count": 1,
                        "conditioning_count": 1,
                    }
                )
                self.state = WorkerState.LOADED_CUDA
                _validate_qwen_absence(self._backend_call("qwen_absence", phase="load_after"))
                resources_after = self._resource("load_after")
                returned = self._postflight(
                    deadline_ns=deadline_ns,
                    cancel_event=cancel_event,
                    label="load.returned",
                )
                transition = self._record(
                    operation="load_exact_conditioned_generation",
                    from_state=from_state,
                    to_state=self.state,
                    entered_ns=entered,
                    returned_ns=returned,
                    deadline_ns=deadline_ns,
                    resources_before=resources_before,
                    resources_after=resources_after,
                    turn_id=None,
                    details={
                        "model_load_count": 1,
                        "reference_conditioning_count": 1,
                        "stable_generation_sha256": self.stable_generation_sha256,
                        "component_fingerprint": self.component_fingerprint,
                        "condition_digest": self.condition_digest,
                    },
                )
                return {
                    "success": True,
                    "state": self.state.value,
                    "generation_id": self.generation_id,
                    "transition": transition,
                }
            except Exception as exc:
                self._fail_closed("load", exc)

    def park_for_qwen(
        self,
        *,
        reason: str,
        deadline_ns: int,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            try:
                entered = self._preflight(
                    deadline_ns=deadline_ns,
                    cancel_event=cancel_event,
                    label="park.entered",
                )
                if type(reason) is not str or not reason or len(reason) > 128:
                    raise V20ContractError("park reason is not exact bounded text")
                if self.state is not WorkerState.LOADED_CUDA or self._current_turn is not None:
                    raise V20ContractError("initial park requires idle LOADED_CUDA")
                from_state = self.state
                _validate_qwen_absence(self._backend_call("qwen_absence", phase="park_before"))
                resources_before = self._resource("park_before")
                transfer = self._owned_transfer("cuda", "cpu")
                self.state = WorkerState.PARKED_CPU
                _validate_qwen_absence(self._backend_call("qwen_absence", phase="park_after"))
                resources_after = self._resource("park_after")
                returned = self._postflight(
                    deadline_ns=deadline_ns,
                    cancel_event=cancel_event,
                    label="park.returned",
                )
                transition = self._record(
                    operation="park_exact_generation_on_cpu",
                    from_state=from_state,
                    to_state=self.state,
                    entered_ns=entered,
                    returned_ns=returned,
                    deadline_ns=deadline_ns,
                    resources_before=resources_before,
                    resources_after=resources_after,
                    turn_id=None,
                    details={"reason": reason, "transfer_sha256": transfer["record_sha256"]},
                )
                return {"success": True, "state": self.state.value, "transition": transition}
            except Exception as exc:
                self._fail_closed("park", exc)

    def enter_qwen_window(
        self,
        *,
        turn_id: str,
        token_hash: str,
        request_sha256: str,
        deadline_ns: int,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            try:
                entered = self._preflight(
                    deadline_ns=deadline_ns,
                    cancel_event=cancel_event,
                    label="qwen_window.entered",
                )
                if self.state is not WorkerState.PARKED_CPU or self._current_turn is not None:
                    raise V20ContractError("Qwen window requires idle PARKED_CPU")
                if self._turn_count >= self.authority["maximum_turns"]:
                    raise V20ContractError("fixture turn ceiling is exhausted")
                if not all(_is_sha256(item) for item in (turn_id, token_hash, request_sha256)):
                    raise V20ContractError("Qwen window hashes are invalid")
                if len({turn_id, token_hash, request_sha256}) != 3:
                    raise V20ContractError("Qwen window bindings must be distinct")
                if any(item.get("turn_id") == turn_id for item in self.transition_ledger):
                    raise V20ContractError("Qwen turn identifier was reused")
                from_state = self.state
                self._assert_generation("cpu")
                _validate_qwen_absence(
                    self._backend_call("qwen_absence", phase="qwen_window_before_grant")
                )
                resources_before = self._resource("qwen_window_before_grant")
                self._current_turn = {
                    "turn_id": turn_id,
                    "token_hash": token_hash,
                    "request_sha256": request_sha256,
                    "qwen_completed": False,
                    "response_text_sha256": None,
                }
                self.state = WorkerState.QWEN_OWNED
                returned = self._postflight(
                    deadline_ns=deadline_ns,
                    cancel_event=cancel_event,
                    label="qwen_window.returned",
                )
                transition = self._record(
                    operation="grant_external_exact_qwen_window",
                    from_state=from_state,
                    to_state=self.state,
                    entered_ns=entered,
                    returned_ns=returned,
                    deadline_ns=deadline_ns,
                    resources_before=resources_before,
                    resources_after=None,
                    turn_id=turn_id,
                    details={
                        "token_hash": token_hash,
                        "request_sha256": request_sha256,
                        "worker_did_not_invoke_qwen": True,
                        "external_completion_receipt_required": True,
                    },
                )
                return {
                    "success": True,
                    "state": self.state.value,
                    "qwen_call_performed_by_worker": False,
                    "transition": transition,
                }
            except Exception as exc:
                self._fail_closed("qwen_window_enter", exc)

    def complete_qwen_window(
        self,
        *,
        receipt: Mapping[str, Any],
        deadline_ns: int,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            try:
                entered = self._preflight(
                    deadline_ns=deadline_ns,
                    cancel_event=cancel_event,
                    label="qwen_complete.entered",
                )
                if self.state is not WorkerState.QWEN_OWNED or type(self._current_turn) is not dict:
                    raise V20ContractError("Qwen completion requires one owned Qwen window")
                from_state = self.state
                current = self._current_turn
                value = validate_qwen_completion_receipt(
                    dict(receipt),
                    turn_id=current["turn_id"],
                    owner_hash=self.authority["owner_hash"],
                    session_id=self.authority["session_id"],
                )
                if (
                    value["token_hash"] != current["token_hash"]
                    or value["request_sha256"] != current["request_sha256"]
                ):
                    raise V20ContractError("Qwen completion does not bind the granted window")
                self.state = WorkerState.PARKED_CPU
                self._assert_generation("cpu")
                _validate_qwen_absence(
                    self._backend_call("qwen_absence", phase="qwen_completion_after_unload")
                )
                resources_after = self._resource("qwen_completion_after_unload")
                current["qwen_completed"] = True
                current["response_text_sha256"] = value["response_text_sha256"]
                current["qwen_receipt_sha256"] = value["receipt_sha256"]
                returned = self._postflight(
                    deadline_ns=deadline_ns,
                    cancel_event=cancel_event,
                    label="qwen_complete.returned",
                )
                transition = self._record(
                    operation="accept_exact_qwen_completion_and_absence",
                    from_state=from_state,
                    to_state=self.state,
                    entered_ns=entered,
                    returned_ns=returned,
                    deadline_ns=deadline_ns,
                    resources_before=None,
                    resources_after=resources_after,
                    turn_id=current["turn_id"],
                    details={
                        "qwen_receipt_sha256": value["receipt_sha256"],
                        "response_text_sha256": value["response_text_sha256"],
                        "keep_alive": 0,
                        "voice_cuda_overlap": False,
                    },
                )
                return {"success": True, "state": self.state.value, "transition": transition}
            except Exception as exc:
                self._fail_closed("qwen_window_complete", exc)

    def restore_for_synthesis(
        self,
        *,
        deadline_ns: int,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            try:
                entered = self._preflight(
                    deadline_ns=deadline_ns,
                    cancel_event=cancel_event,
                    label="restore.entered",
                )
                if (
                    self.state is not WorkerState.PARKED_CPU
                    or type(self._current_turn) is not dict
                    or self._current_turn.get("qwen_completed") is not True
                ):
                    raise V20ContractError("CUDA restore requires completed exact Qwen turn")
                from_state = self.state
                current = self._current_turn
                _validate_qwen_absence(self._backend_call("qwen_absence", phase="restore_before"))
                resources_before = self._resource("restore_before")
                if resources_before["cuda_free_bytes"] < 4096 * 1024 * 1024:
                    raise V20ContractError("CUDA headroom is below 4,096 MiB before restore")
                transfer = self._owned_transfer("cpu", "cuda")
                self.state = WorkerState.LOADED_CUDA
                _validate_qwen_absence(self._backend_call("qwen_absence", phase="restore_after"))
                resources_after = self._resource("restore_after")
                returned = self._postflight(
                    deadline_ns=deadline_ns,
                    cancel_event=cancel_event,
                    label="restore.returned",
                )
                transition = self._record(
                    operation="restore_same_generation_to_cuda",
                    from_state=from_state,
                    to_state=self.state,
                    entered_ns=entered,
                    returned_ns=returned,
                    deadline_ns=deadline_ns,
                    resources_before=resources_before,
                    resources_after=resources_after,
                    turn_id=current["turn_id"],
                    details={"transfer_sha256": transfer["record_sha256"]},
                )
                return {"success": True, "state": self.state.value, "transition": transition}
            except Exception as exc:
                self._fail_closed("restore", exc)

    def synthesize_fixture_and_park(
        self,
        *,
        text_sha256: str,
        synthesis_id: str,
        deadline_ns: int,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        """Exercise only the mock backend; these bytes cannot synthesize live audio."""

        with self._lock:
            try:
                entered = self._preflight(
                    deadline_ns=deadline_ns,
                    cancel_event=cancel_event,
                    label="synthesis.entered",
                )
                if (
                    self.state is not WorkerState.LOADED_CUDA
                    or type(self._current_turn) is not dict
                    or self._current_turn.get("qwen_completed") is not True
                ):
                    raise V20ContractError("synthesis requires restored completed turn")
                if not _is_sha256(text_sha256) or not _is_sha256(synthesis_id):
                    raise V20ContractError("synthesis text/operation hashes are invalid")
                current = self._current_turn
                if text_sha256 != current["response_text_sha256"]:
                    raise V20ContractError("synthesis text does not match exact Qwen public words")
                if synthesis_id in {current["turn_id"], current["token_hash"]}:
                    raise V20ContractError("synthesis identifier is not distinct")
                from_state = self.state
                self._assert_generation("cuda")
                _validate_qwen_absence(
                    self._backend_call("qwen_absence", phase="synthesis_before")
                )
                resources_before = self._resource("synthesis_before")
                result = self._backend_call(
                    "synthesize_exact",
                    text_sha256=text_sha256,
                    synthesis_id=synthesis_id,
                    generation_id=self.generation_id,
                    component_fingerprint=self.component_fingerprint,
                    condition_digest=self.condition_digest,
                    profile_sha256=EXACT_VOICE_PROFILE_SHA256,
                    reference_sha256=EXACT_VOICE_REFERENCE_SHA256,
                    worker_pid=self.worker_pid,
                )
                exact_keys = {
                    "schema",
                    "artifact_sha256",
                    "text_sha256",
                    "synthesis_id",
                    "route",
                    "device",
                    "generic_voice_used",
                    "sapi_voice_used",
                    "fallback_used",
                    "model_generation",
                    "component_fingerprint",
                    "condition_digest",
                    "first_sample_monotonic_ns",
                    "audio_ready_monotonic_ns",
                    "playback_performed",
                    "fixture_audio_created",
                }
                if type(result) is not dict or set(result) != exact_keys:
                    raise V20ContractError("fixture synthesis result schema is not exact")
                if (
                    result["schema"] != "kira.blackwell.voice_v20.fixture_synthesis_result.v1"
                    or not _is_sha256(result["artifact_sha256"])
                    or result["text_sha256"] != text_sha256
                    or result["synthesis_id"] != synthesis_id
                    or result["route"] != "blackwell_gpu"
                    or result["device"] != "cuda"
                    or result["generic_voice_used"] is not False
                    or result["sapi_voice_used"] is not False
                    or result["fallback_used"] is not False
                    or result["model_generation"] != self.generation_id
                    or result["component_fingerprint"] != self.component_fingerprint
                    or result["condition_digest"] != self.condition_digest
                    or type(result["first_sample_monotonic_ns"]) is not int
                    or result["first_sample_monotonic_ns"] <= 0
                    or type(result["audio_ready_monotonic_ns"]) is not int
                    or result["audio_ready_monotonic_ns"] <= 0
                    or result["first_sample_monotonic_ns"] > result["audio_ready_monotonic_ns"]
                    or result["playback_performed"] is not False
                    or result["fixture_audio_created"] is not False
                ):
                    raise V20ContractError("fixture synthesis identity/truth binding failed")
                self._assert_generation("cuda")
                _validate_qwen_absence(
                    self._backend_call("qwen_absence", phase="synthesis_after")
                )
                self.state = WorkerState.SYNTHESIZED
                resources_after = self._resource("synthesis_after")
                returned = self._postflight(
                    deadline_ns=deadline_ns,
                    cancel_event=cancel_event,
                    label="synthesis.returned",
                )
                synthesis_transition = self._record(
                    operation="fixture_synthesize_same_generation",
                    from_state=from_state,
                    to_state=self.state,
                    entered_ns=entered,
                    returned_ns=returned,
                    deadline_ns=deadline_ns,
                    resources_before=resources_before,
                    resources_after=resources_after,
                    turn_id=current["turn_id"],
                    details={
                        "artifact_sha256": result["artifact_sha256"],
                        "text_sha256": text_sha256,
                        "first_sample_monotonic_ns": result["first_sample_monotonic_ns"],
                        "audio_ready_monotonic_ns": result["audio_ready_monotonic_ns"],
                        "playback_performed": False,
                        "fixture_audio_created": False,
                    },
                )

                park_entered = self._clock("post_synthesis_park.entered")
                park_from_state = self.state
                park_before = self._resource("post_synthesis_park_before")
                transfer = self._owned_transfer("cuda", "cpu")
                self.state = WorkerState.PARKED_CPU
                _validate_qwen_absence(
                    self._backend_call("qwen_absence", phase="post_synthesis_park_after")
                )
                park_after = self._resource("post_synthesis_park_after")
                park_returned = self._postflight(
                    deadline_ns=deadline_ns,
                    cancel_event=cancel_event,
                    label="post_synthesis_park.returned",
                )
                park_transition = self._record(
                    operation="park_same_generation_after_synthesis",
                    from_state=park_from_state,
                    to_state=self.state,
                    entered_ns=park_entered,
                    returned_ns=park_returned,
                    deadline_ns=deadline_ns,
                    resources_before=park_before,
                    resources_after=park_after,
                    turn_id=current["turn_id"],
                    details={"transfer_sha256": transfer["record_sha256"]},
                )
                self._turn_count += 1
                self._current_turn = None
                return {
                    "success": True,
                    "state": self.state.value,
                    "turn_count": self._turn_count,
                    "synthesis_transition": synthesis_transition,
                    "park_transition": park_transition,
                    "latency_improvement_proven": False,
                }
            except Exception as exc:
                self._fail_closed("synthesis", exc)

    def close_fixture(
        self,
        *,
        reason: str,
        deadline_ns: int,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            try:
                entered = self._preflight(
                    deadline_ns=deadline_ns,
                    cancel_event=cancel_event,
                    label="close.entered",
                )
                if type(reason) is not str or not reason or len(reason) > 128:
                    raise V20ContractError("close reason is not exact bounded text")
                if self.state in {WorkerState.QWEN_OWNED, WorkerState.CLEANUP_DEBT, WorkerState.TERMINAL}:
                    raise V20ContractError("close state requires native Job termination or is terminal")
                from_state = self.state
                resources_before = self._resource("close_before")
                result = self._backend_call("release_generation", reason=reason)
                if result != {
                    "released": True,
                    "owned_model_count": 0,
                    "owned_condition_count": 0,
                }:
                    raise V20ContractError("fixture generation release is not exact")
                self.model = None
                self.model_object_id = None
                self.state = WorkerState.TERMINAL
                returned = self._postflight(
                    deadline_ns=deadline_ns,
                    cancel_event=cancel_event,
                    label="close.returned",
                )
                transition = self._record(
                    operation="terminal_release_fixture_generation",
                    from_state=from_state,
                    to_state=self.state,
                    entered_ns=entered,
                    returned_ns=returned,
                    deadline_ns=deadline_ns,
                    resources_before=resources_before,
                    resources_after=None,
                    turn_id=None,
                    details={"reason": reason, "release_proven": True},
                )
                self.terminal_outcome = {
                    "schema": "kira.blackwell.voice_v20.author_fixture_terminal.v1",
                    "status": "PASS_MOCK_CONTROL_ONLY",
                    "turn_count": self._turn_count,
                    "transition_count": len(self.transition_ledger),
                    "transfer_count": len(self.transfer_ledger),
                    "model_calls": 0,
                    "gpu_calls": 0,
                    "synthesis_calls": 0,
                    "audio_created": False,
                    "playback_calls": 0,
                    "camera_calls": 0,
                    "latency_improvement_proven": False,
                    "transition_root_sha256": canonical_sha256(self.transition_ledger),
                    "transfer_root_sha256": canonical_sha256(self.transfer_ledger),
                    "transition": transition,
                }
                self.terminal_outcome["outcome_sha256"] = canonical_sha256(
                    self.terminal_outcome
                )
                return dict(self.terminal_outcome)
            except Exception as exc:
                self._fail_closed("close", exc)

    def status(self) -> dict[str, Any]:
        with self._lock:
            self._verify_graph()
            return {
                "candidate_id": CANDIDATE_ID,
                "state": self.state.value,
                "session_id": self.authority["session_id"],
                "generation_id": self.generation_id,
                "turn_count": self._turn_count,
                "maximum_turns": self.authority["maximum_turns"],
                "transition_count": len(self.transition_ledger),
                "transfer_count": len(self.transfer_ledger),
                "cleanup_debt": list(self.cleanup_debt),
                "author_fixture_only": True,
                "execution_authorized": False,
                "production_route_changed": False,
                "latency_improvement_proven": False,
            }


__all__ = [
    "CANDIDATE_ID",
    "ControlBinding",
    "EXACT_TEXT_MODEL",
    "EXACT_TEXT_MODEL_DIGEST",
    "REQUIRED_COMPONENTS",
    "RetainedGenerationWorkerV20",
    "V20ContractError",
    "V20NotAuthorized",
    "WorkerState",
    "author_fixture_authority",
    "callable_binding",
    "canonical_sha256",
    "configure_windows_memory_apis",
    "generation_snapshot",
    "move_exact_generation",
    "read_windows_memory_bytes",
    "sha256_file",
    "validate_qwen_completion_receipt",
    "validate_resource_sample",
]
