"""Canonical sealed-module binding for inactive Blackwell V12.

This module never imports the V8 live-adapter or V10 memory helper through
normal import state.  It reads their exact sealed bytes, compiles those bytes
into private module objects that are never entered in ``sys.modules``, binds
the original callable/code/default/global/closure identities, and revalidates
the complete binding before and after every authority use.

Importing this module is inert.  It does not construct a live backend, contact
Ollama, import Torch, touch CUDA, load Chatterbox, or synthesize/play audio.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.machinery
import math
import marshal
import os
import pickle
import sys
import threading
import types
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
V8_ADAPTER_NAME = (
    "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.live_adapter"
)
V8_ADAPTER_PARENT = "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8"
V8_ADAPTER_PATH = (
    PROJECT_ROOT
    / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/live_adapter.py"
)
V8_ADAPTER_SHA256 = (
    "7565203c1d548f576d2264f7c0ee84b16a35dcf5e57ec9f56909ae1278b022eb"
)
V8_ADAPTER_BYTES = 36244

V10_MEMORY_NAME = "Core.blackwell_v10_windows_memory"
V10_MEMORY_PARENT = "Core"
V10_MEMORY_PATH = PROJECT_ROOT / "Core/blackwell_v10_windows_memory.py"
V10_MEMORY_SHA256 = (
    "bf2460a33c528749ad075366e2847cdc8fc82b04754545db75db06bba95d587d"
)
V10_MEMORY_BYTES = 6342

PRIVATE_ADAPTER_NAME = "_kira_blackwell_v12_exact_v8_live_adapter"
PRIVATE_MEMORY_NAME = "_kira_blackwell_v12_exact_v10_windows_memory"

_CONSTRUCTION_KEY = object()
_MISSING = object()


class V12CanonicalBindingError(RuntimeError):
    """Fail-closed exact module/callable binding error."""


class _SealedBytesLoader:
    __slots__ = ("name", "origin", "source_sha256")

    def __init__(self, name: str, origin: str, source_sha256: str) -> None:
        self.name = name
        self.origin = origin
        self.source_sha256 = source_sha256

    def __copy__(self):
        raise TypeError("sealed loader cannot be copied")

    def __deepcopy__(self, _memo):
        raise TypeError("sealed loader cannot be copied")

    def __reduce__(self):
        raise TypeError("sealed loader cannot be serialized")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return (
        int(value.st_dev),
        int(value.st_ino),
        int(value.st_size),
        int(value.st_mtime_ns),
    )


def _read_exact_source(
    path: Path, *, expected_sha256: str, expected_bytes: int
) -> tuple[bytes, tuple[int, int, int, int]]:
    expected = path.resolve(strict=True)
    root = PROJECT_ROOT.resolve(strict=True)
    expected.relative_to(root)
    with expected.open("rb") as handle:
        before = os.fstat(handle.fileno())
        raw = handle.read(expected_bytes + 1)
        after = os.fstat(handle.fileno())
    path_after = expected.stat()
    identities = (_stat_identity(before), _stat_identity(after), _stat_identity(path_after))
    if identities[0] != identities[1] or identities[1] != identities[2]:
        raise V12CanonicalBindingError("sealed source identity changed while reading")
    if len(raw) != expected_bytes or _sha256_bytes(raw) != expected_sha256:
        raise V12CanonicalBindingError("sealed source bytes are absent or drifted")
    return raw, identities[0]


def _verify_source(
    path: Path,
    *,
    expected_sha256: str,
    expected_bytes: int,
    expected_identity: tuple[int, int, int, int],
) -> None:
    raw, observed_identity = _read_exact_source(
        path, expected_sha256=expected_sha256, expected_bytes=expected_bytes
    )
    if observed_identity != expected_identity or _sha256_bytes(raw) != expected_sha256:
        raise V12CanonicalBindingError("sealed source identity changed after binding")


def _ensure_import_slots_clean() -> None:
    for name in (V8_ADAPTER_NAME, V10_MEMORY_NAME, PRIVATE_ADAPTER_NAME, PRIVATE_MEMORY_NAME):
        if name in sys.modules:
            raise V12CanonicalBindingError(f"pre-existing module binding rejected: {name}")
    for parent_name, attribute in (
        (V8_ADAPTER_PARENT, "live_adapter"),
        (V10_MEMORY_PARENT, "blackwell_v10_windows_memory"),
    ):
        parent = sys.modules.get(parent_name)
        if parent is not None and hasattr(parent, attribute):
            raise V12CanonicalBindingError(
                f"pre-existing package attribute rejected: {parent_name}.{attribute}"
            )


def _load_private_exact_module(
    *,
    private_name: str,
    source_path: Path,
    expected_sha256: str,
    expected_bytes: int,
) -> tuple[
    types.ModuleType,
    _SealedBytesLoader,
    importlib.machinery.ModuleSpec,
    tuple[int, int, int, int],
]:
    raw, source_identity = _read_exact_source(
        source_path,
        expected_sha256=expected_sha256,
        expected_bytes=expected_bytes,
    )
    resolved = source_path.resolve(strict=True)
    loader = _SealedBytesLoader(private_name, str(resolved), expected_sha256)
    spec = importlib.machinery.ModuleSpec(
        private_name, loader, origin=str(resolved)
    )
    module = types.ModuleType(private_name)
    module.__file__ = str(resolved)
    module.__loader__ = loader
    module.__package__ = ""
    module.__spec__ = spec
    module.__cached__ = None
    code = compile(raw, str(resolved), "exec", dont_inherit=True, optimize=0)
    exec(code, module.__dict__)
    if private_name in sys.modules:
        raise V12CanonicalBindingError("private sealed module leaked into sys.modules")
    _verify_source(
        source_path,
        expected_sha256=expected_sha256,
        expected_bytes=expected_bytes,
        expected_identity=source_identity,
    )
    return module, loader, spec, source_identity


def _typed_snapshot(value: Any) -> Any:
    if value is None or type(value) in (bool, int, float, str, bytes):
        if type(value) is float and not math.isfinite(value):
            raise V12CanonicalBindingError("non-finite callable metadata rejected")
        return (type(value).__name__, value)
    if type(value) is tuple:
        return ("tuple", tuple(_typed_snapshot(item) for item in value))
    if type(value) is list:
        return ("list", tuple(_typed_snapshot(item) for item in value))
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise V12CanonicalBindingError("callable metadata keys must be exact strings")
        return (
            "dict",
            tuple((key, _typed_snapshot(value[key])) for key in sorted(value)),
        )
    return ("identity", type(value), id(value))


class _FunctionSeal:
    __slots__ = (
        "function",
        "module",
        "code",
        "code_sha256",
        "defaults",
        "defaults_snapshot",
        "kwdefaults",
        "kwdefaults_snapshot",
        "closure",
        "closure_cells",
        "closure_contents",
        "annotations",
        "annotations_snapshot",
        "function_dict",
        "function_dict_snapshot",
        "builtins",
        "referenced_globals",
        "referenced_builtins",
        "name",
        "qualname",
        "module_name",
    )

    def __init__(self, function: Any, module: types.ModuleType, *, label: str) -> None:
        if type(function) is not types.FunctionType:
            raise V12CanonicalBindingError(f"{label} must be an exact Python function")
        if function.__globals__ is not module.__dict__:
            raise V12CanonicalBindingError(f"{label} globals are not the exact module")
        self.function = function
        self.module = module
        self.code = function.__code__
        self.code_sha256 = _sha256_bytes(marshal.dumps(function.__code__))
        self.defaults = function.__defaults__
        self.defaults_snapshot = _typed_snapshot(function.__defaults__)
        self.kwdefaults = function.__kwdefaults__
        self.kwdefaults_snapshot = _typed_snapshot(function.__kwdefaults__)
        self.closure = function.__closure__
        self.closure_cells = tuple(function.__closure__ or ())
        self.closure_contents = tuple(
            _typed_snapshot(cell.cell_contents) for cell in self.closure_cells
        )
        self.annotations = function.__annotations__
        self.annotations_snapshot = _typed_snapshot(function.__annotations__)
        self.function_dict = function.__dict__
        self.function_dict_snapshot = _typed_snapshot(function.__dict__)
        self.builtins = function.__builtins__
        self.referenced_globals = tuple(
            (name, module.__dict__[name])
            for name in function.__code__.co_names
            if name in module.__dict__
        )
        self.referenced_builtins = tuple(
            (name, function.__builtins__[name])
            for name in function.__code__.co_names
            if name not in module.__dict__ and name in function.__builtins__
        )
        self.name = function.__name__
        self.qualname = function.__qualname__
        self.module_name = function.__module__

    def verify(self, *, label: str) -> None:
        function = self.function
        if type(function) is not types.FunctionType:
            raise V12CanonicalBindingError(f"{label} ceased to be an exact function")
        if function.__globals__ is not self.module.__dict__:
            raise V12CanonicalBindingError(f"{label} globals identity changed")
        if function.__code__ is not self.code:
            raise V12CanonicalBindingError(f"{label} code object identity changed")
        if function.__defaults__ is not self.defaults or _typed_snapshot(
            function.__defaults__
        ) != self.defaults_snapshot:
            raise V12CanonicalBindingError(f"{label} defaults changed")
        if function.__kwdefaults__ is not self.kwdefaults or _typed_snapshot(
            function.__kwdefaults__
        ) != self.kwdefaults_snapshot:
            raise V12CanonicalBindingError(f"{label} keyword defaults changed")
        if function.__closure__ is not self.closure:
            raise V12CanonicalBindingError(f"{label} closure tuple changed")
        cells = tuple(function.__closure__ or ())
        if len(cells) != len(self.closure_cells) or any(
            observed is not expected
            for observed, expected in zip(cells, self.closure_cells)
        ):
            raise V12CanonicalBindingError(f"{label} closure cells changed")
        if tuple(_typed_snapshot(cell.cell_contents) for cell in cells) != self.closure_contents:
            raise V12CanonicalBindingError(f"{label} closure contents changed")
        if function.__annotations__ is not self.annotations or _typed_snapshot(
            function.__annotations__
        ) != self.annotations_snapshot:
            raise V12CanonicalBindingError(f"{label} annotations changed")
        if function.__dict__ is not self.function_dict or _typed_snapshot(
            function.__dict__
        ) != self.function_dict_snapshot:
            raise V12CanonicalBindingError(f"{label} function metadata changed")
        if function.__builtins__ is not self.builtins:
            raise V12CanonicalBindingError(f"{label} builtins mapping changed")
        if function.__name__ != self.name or function.__qualname__ != self.qualname:
            raise V12CanonicalBindingError(f"{label} name changed")
        if function.__module__ != self.module_name:
            raise V12CanonicalBindingError(f"{label} module name changed")
        for name, expected in self.referenced_globals:
            if self.module.__dict__.get(name, _MISSING) is not expected:
                raise V12CanonicalBindingError(f"{label} referenced global changed: {name}")
        for name, expected in self.referenced_builtins:
            if function.__builtins__.get(name, _MISSING) is not expected:
                raise V12CanonicalBindingError(f"{label} referenced builtin changed: {name}")


class CanonicalTypedMemoryBinding:
    """Opaque exact V8-module/V10-helper binding; not live authority."""

    __slots__ = (
        "_seal",
        "_lock",
        "_adapter_module",
        "_adapter_loader",
        "_adapter_spec",
        "_adapter_source_identity",
        "_adapter_keys",
        "_adapter_values",
        "_adapter_original",
        "_adapter_original_seal",
        "_memory_module",
        "_memory_loader",
        "_memory_spec",
        "_memory_source_identity",
        "_memory_keys",
        "_memory_values",
        "_memory_probe",
        "_memory_probe_seal",
        "_memory_installer",
        "_memory_installer_seal",
        "_installed",
        "_quarantined",
        "_binding_sha256",
        "_revision",
    )

    def __new__(cls, key: object | None = None, **_kwargs):
        if key is not _CONSTRUCTION_KEY:
            raise TypeError("canonical binding is controller-created only")
        return super().__new__(cls)

    def __init__(
        self,
        key: object,
        *,
        adapter_module: types.ModuleType,
        adapter_loader: _SealedBytesLoader,
        adapter_spec: importlib.machinery.ModuleSpec,
        adapter_source_identity: tuple[int, int, int, int],
        memory_module: types.ModuleType,
        memory_loader: _SealedBytesLoader,
        memory_spec: importlib.machinery.ModuleSpec,
        memory_source_identity: tuple[int, int, int, int],
    ) -> None:
        if key is not _CONSTRUCTION_KEY:
            raise TypeError("canonical binding is controller-created only")
        self._seal = _CONSTRUCTION_KEY
        self._lock = threading.RLock()
        self._adapter_module = adapter_module
        self._adapter_loader = adapter_loader
        self._adapter_spec = adapter_spec
        self._adapter_source_identity = adapter_source_identity
        self._adapter_keys = frozenset(adapter_module.__dict__)
        self._adapter_values = tuple(adapter_module.__dict__.items())
        self._adapter_original = adapter_module.__dict__.get("_windows_memory_mib")
        self._adapter_original_seal = _FunctionSeal(
            self._adapter_original, adapter_module, label="v8 original memory probe"
        )
        self._memory_module = memory_module
        self._memory_loader = memory_loader
        self._memory_spec = memory_spec
        self._memory_source_identity = memory_source_identity
        self._memory_keys = frozenset(memory_module.__dict__)
        self._memory_values = tuple(memory_module.__dict__.items())
        self._memory_probe = memory_module.__dict__.get("windows_memory_mib")
        self._memory_probe_seal = _FunctionSeal(
            self._memory_probe, memory_module, label="v10 typed memory probe"
        )
        self._memory_installer = memory_module.__dict__.get(
            "install_into_exact_v8_live_adapter"
        )
        self._memory_installer_seal = _FunctionSeal(
            self._memory_installer, memory_module, label="v10 typed memory installer"
        )
        self._installed = False
        self._quarantined = False
        self._revision = 0
        self._binding_sha256 = hashlib.sha256(
            (
                f"v12:{V8_ADAPTER_SHA256}:{V10_MEMORY_SHA256}:"
                f"{self._adapter_original_seal.code_sha256}:"
                f"{self._memory_probe_seal.code_sha256}:"
                f"{self._memory_installer_seal.code_sha256}"
            ).encode("utf-8")
        ).hexdigest()
        self._revalidate_locked(expected_installed=False)

    def __copy__(self):
        raise TypeError("canonical binding cannot be copied")

    def __deepcopy__(self, _memo):
        raise TypeError("canonical binding cannot be copied")

    def __reduce__(self):
        raise TypeError("canonical binding cannot be serialized")

    @staticmethod
    def _verify_module_shell(
        module: types.ModuleType,
        *,
        private_name: str,
        source_path: Path,
        loader: _SealedBytesLoader,
        spec: importlib.machinery.ModuleSpec,
    ) -> None:
        resolved = str(source_path.resolve(strict=True))
        if type(module) is not types.ModuleType:
            raise V12CanonicalBindingError("sealed module became a proxy or subclass")
        if module.__name__ != private_name or module.__package__ != "":
            raise V12CanonicalBindingError("sealed module name/package changed")
        if module.__file__ != resolved or module.__cached__ is not None:
            raise V12CanonicalBindingError("sealed module path/cache identity changed")
        if module.__loader__ is not loader or type(loader) is not _SealedBytesLoader:
            raise V12CanonicalBindingError("sealed module loader identity changed")
        if module.__spec__ is not spec:
            raise V12CanonicalBindingError("sealed module spec identity changed")
        if (
            spec.name != private_name
            or spec.origin != resolved
            or spec.loader is not loader
        ):
            raise V12CanonicalBindingError("sealed module spec content changed")

    @staticmethod
    def _verify_module_values(
        module: types.ModuleType,
        *,
        expected_keys: frozenset[str],
        expected_values: tuple[tuple[str, Any], ...],
        allowed_replacement_key: str | None = None,
        allowed_replacement: Any = None,
    ) -> None:
        if frozenset(module.__dict__) != expected_keys:
            raise V12CanonicalBindingError("sealed module global schema changed")
        for key, expected in expected_values:
            observed = module.__dict__.get(key, _MISSING)
            if key == allowed_replacement_key:
                if observed is not allowed_replacement:
                    raise V12CanonicalBindingError("typed replacement identity changed")
            elif observed is not expected:
                raise V12CanonicalBindingError(f"sealed module global changed: {key}")

    def _revalidate_locked(self, *, expected_installed: bool) -> None:
        if self._seal is not _CONSTRUCTION_KEY or self._quarantined:
            raise V12CanonicalBindingError("canonical binding is invalid or quarantined")
        if type(self._quarantined) is not bool or type(self._installed) is not bool:
            raise V12CanonicalBindingError("canonical binding truth types drifted")
        if self._installed is not expected_installed:
            raise V12CanonicalBindingError("canonical binding installation state drifted")
        if type(self._revision) is not int or self._revision != (1 if expected_installed else 0):
            raise V12CanonicalBindingError("canonical binding revision drifted")
        expected_binding = hashlib.sha256(
            (
                f"v12:{V8_ADAPTER_SHA256}:{V10_MEMORY_SHA256}:"
                f"{self._adapter_original_seal.code_sha256}:"
                f"{self._memory_probe_seal.code_sha256}:"
                f"{self._memory_installer_seal.code_sha256}"
            ).encode("utf-8")
        ).hexdigest()
        if self._binding_sha256 != expected_binding:
            raise V12CanonicalBindingError("canonical binding digest drifted")
        _ensure_import_slots_clean()
        _verify_source(
            V8_ADAPTER_PATH,
            expected_sha256=V8_ADAPTER_SHA256,
            expected_bytes=V8_ADAPTER_BYTES,
            expected_identity=self._adapter_source_identity,
        )
        _verify_source(
            V10_MEMORY_PATH,
            expected_sha256=V10_MEMORY_SHA256,
            expected_bytes=V10_MEMORY_BYTES,
            expected_identity=self._memory_source_identity,
        )
        self._verify_module_shell(
            self._adapter_module,
            private_name=PRIVATE_ADAPTER_NAME,
            source_path=V8_ADAPTER_PATH,
            loader=self._adapter_loader,
            spec=self._adapter_spec,
        )
        self._verify_module_shell(
            self._memory_module,
            private_name=PRIVATE_MEMORY_NAME,
            source_path=V10_MEMORY_PATH,
            loader=self._memory_loader,
            spec=self._memory_spec,
        )
        if self._adapter_original is not self._adapter_original_seal.function:
            raise V12CanonicalBindingError("stored v8 original callable changed")
        if self._memory_probe is not self._memory_probe_seal.function:
            raise V12CanonicalBindingError("stored v10 probe callable changed")
        if self._memory_installer is not self._memory_installer_seal.function:
            raise V12CanonicalBindingError("stored v10 installer callable changed")
        self._adapter_original_seal.verify(label="v8 original memory probe")
        self._memory_probe_seal.verify(label="v10 typed memory probe")
        self._memory_installer_seal.verify(label="v10 typed memory installer")
        self._verify_module_values(
            self._memory_module,
            expected_keys=self._memory_keys,
            expected_values=self._memory_values,
        )
        self._verify_module_values(
            self._adapter_module,
            expected_keys=self._adapter_keys,
            expected_values=self._adapter_values,
            allowed_replacement_key="_windows_memory_mib" if expected_installed else None,
            allowed_replacement=self._memory_probe if expected_installed else None,
        )

    def revalidate(self) -> dict[str, Any]:
        with self._lock:
            self._revalidate_locked(expected_installed=self._installed)
            return self._evidence_locked()

    def _evidence_locked(self) -> dict[str, Any]:
        return {
            "schema": "kira.blackwell.v12.canonical_typed_memory_binding.v1",
            "binding_sha256": self._binding_sha256,
            "revision": self._revision,
            "installed": self._installed,
            "quarantined": self._quarantined,
            "adapter_private_module": PRIVATE_ADAPTER_NAME,
            "adapter_source_sha256": V8_ADAPTER_SHA256,
            "memory_private_module": PRIVATE_MEMORY_NAME,
            "memory_source_sha256": V10_MEMORY_SHA256,
            "normal_import_state_clean": True,
            "live_backend_constructed": False,
        }

    def install(self) -> dict[str, Any]:
        with self._lock:
            self._revalidate_locked(expected_installed=False)
            try:
                result = self._memory_installer(self._adapter_module)
                if (
                    type(result) is not dict
                    or set(result)
                    != {"installed", "target_path", "target_sha256", "replacement", "opens_process"}
                    or result["installed"] is not True
                    or result["target_path"] != str(V8_ADAPTER_PATH.resolve(strict=True))
                    or result["target_sha256"] != V8_ADAPTER_SHA256
                    or result["replacement"]
                    != "Core.blackwell_v10_windows_memory.windows_memory_mib"
                    or result["opens_process"] is not False
                ):
                    raise V12CanonicalBindingError("V10 installer evidence is not exact")
                self._installed = True
                self._revision = 1
                self._revalidate_locked(expected_installed=True)
            except Exception as exc:
                self._adapter_module.__dict__["_windows_memory_mib"] = self._adapter_original
                self._installed = False
                self._revision = 0
                try:
                    self._revalidate_locked(expected_installed=False)
                except Exception as rollback_exc:
                    self._quarantined = True
                    raise V12CanonicalBindingError(
                        "typed-memory install failed and exact rollback could not be proven"
                    ) from rollback_exc
                if isinstance(exc, V12CanonicalBindingError):
                    raise
                raise V12CanonicalBindingError("typed-memory install failed closed") from exc
            evidence = self._evidence_locked()
            evidence["installer_evidence"] = dict(result)
            return evidence

    def memory_values(self) -> tuple[float, float, float, float]:
        with self._lock:
            self._revalidate_locked(expected_installed=True)
            values = self._memory_probe()
            if (
                type(values) is not tuple
                or len(values) != 4
                or any(type(value) is not float for value in values)
                or any(not math.isfinite(value) or value < 0 for value in values)
                or values[0] <= 0
                or values[2] <= 0
                or values[1] > values[2]
            ):
                raise V12CanonicalBindingError("typed-memory telemetry is not exact finite data")
            self._revalidate_locked(expected_installed=True)
            return values


def create_canonical_typed_memory_binding() -> CanonicalTypedMemoryBinding:
    """Create the exact private binding; normal import state must be clean."""

    _ensure_import_slots_clean()
    adapter, adapter_loader, adapter_spec, adapter_identity = _load_private_exact_module(
        private_name=PRIVATE_ADAPTER_NAME,
        source_path=V8_ADAPTER_PATH,
        expected_sha256=V8_ADAPTER_SHA256,
        expected_bytes=V8_ADAPTER_BYTES,
    )
    _ensure_import_slots_clean()
    memory, memory_loader, memory_spec, memory_identity = _load_private_exact_module(
        private_name=PRIVATE_MEMORY_NAME,
        source_path=V10_MEMORY_PATH,
        expected_sha256=V10_MEMORY_SHA256,
        expected_bytes=V10_MEMORY_BYTES,
    )
    _ensure_import_slots_clean()
    return CanonicalTypedMemoryBinding(
        _CONSTRUCTION_KEY,
        adapter_module=adapter,
        adapter_loader=adapter_loader,
        adapter_spec=adapter_spec,
        adapter_source_identity=adapter_identity,
        memory_module=memory,
        memory_loader=memory_loader,
        memory_spec=memory_spec,
        memory_source_identity=memory_identity,
    )


def install_exact_typed_memory_probe(binding: Any) -> dict[str, Any]:
    if type(binding) is not CanonicalTypedMemoryBinding or binding._seal is not _CONSTRUCTION_KEY:
        raise V12CanonicalBindingError("exact canonical binding capability required")
    return binding.install()


def revalidate_exact_typed_memory_probe(binding: Any) -> dict[str, Any]:
    if type(binding) is not CanonicalTypedMemoryBinding or binding._seal is not _CONSTRUCTION_KEY:
        raise V12CanonicalBindingError("exact canonical binding capability required")
    return binding.revalidate()


def read_exact_typed_memory_mib(binding: Any) -> tuple[float, float, float, float]:
    if type(binding) is not CanonicalTypedMemoryBinding or binding._seal is not _CONSTRUCTION_KEY:
        raise V12CanonicalBindingError("exact canonical binding capability required")
    return binding.memory_values()


__all__ = [
    "CanonicalTypedMemoryBinding",
    "V12CanonicalBindingError",
    "create_canonical_typed_memory_binding",
    "install_exact_typed_memory_probe",
    "read_exact_typed_memory_mib",
    "revalidate_exact_typed_memory_probe",
]
