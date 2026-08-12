"""Disconnected Blackwell V13 control-plane binding.

V12 privately bound the V8 adapter and V10 typed-memory helper, but its own
normally imported canonical control module remained replaceable.  V13 wraps the
exact sealed V12 source in a private module object, binds that module object and
all of its Python functions/classes, and revalidates the V13 module/package and
the private V12 graph before and after every operation.

This remains static-only.  It cannot construct a production or bounded live
candidate, does not enable playback, and is not a latency acceptance.
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import json
import marshal
import math
import os
import sys
import threading
import types
from pathlib import Path
from typing import Any


CANDIDATE_ID = "kira_chatterbox_blackwell_control_plane_binding_candidate_v13"
FEATURE_FLAG = "KIRA_ENABLE_BLACKWELL_CONTROL_PLANE_CANDIDATE_V13"
PRODUCTION_ROUTING_AUTHORIZED = False
LIVE_EXECUTION_AUTHORIZED_BY_THIS_MODULE = False
FUTURE_HARNESS_AUTHORING_AUTHORIZED = False
PLAYBACK_AUTHORIZED = False

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = (
    PROJECT_ROOT
    / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v13/candidate_config.json"
)
SELF_PATH = PROJECT_ROOT / "Core/persistent_blackwell_voice_integration_v13.py"
V12_NAME = (
    "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12."
    "canonical_typed_memory_binding"
)
V12_PARENT = "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12"
V12_PATH = (
    PROJECT_ROOT
    / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/"
    "canonical_typed_memory_binding.py"
)
V12_SHA256 = "9d2ac1101b5b372aa7881e6c627960753b83ee711fd0db23eb059c216c92b187"
V12_BYTES = 27300
PRIVATE_V12_NAME = "_kira_blackwell_v13_exact_v12_control_plane"

_CONSTRUCTION_KEY = object()
_MISSING = object()
_CONTROL_FINALIZED = False


class V13ControlPlaneError(RuntimeError):
    """Fail-closed V13 exact control-plane binding error."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            raise V13ControlPlaneError("configuration keys must be unique strings")
        result[key] = value
    return result


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and any(character in "abcdef" for character in value)
        and all(character in "0123456789abcdef" for character in value)
    )


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return (int(value.st_dev), int(value.st_ino), int(value.st_size), int(value.st_mtime_ns))


def _read_exact(
    path: Path, *, expected_sha256: str, expected_bytes: int
) -> tuple[bytes, tuple[int, int, int, int]]:
    resolved = path.resolve(strict=True)
    resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    with resolved.open("rb") as handle:
        before = os.fstat(handle.fileno())
        raw = handle.read(expected_bytes + 1)
        after = os.fstat(handle.fileno())
    path_after = resolved.stat()
    identities = (_stat_identity(before), _stat_identity(after), _stat_identity(path_after))
    if identities[0] != identities[1] or identities[1] != identities[2]:
        raise V13ControlPlaneError("sealed source identity changed while reading")
    if len(raw) != expected_bytes or _sha256(raw) != expected_sha256:
        raise V13ControlPlaneError("sealed source bytes are absent or drifted")
    return raw, identities[0]


def _verify_exact(
    path: Path,
    *,
    expected_sha256: str,
    expected_bytes: int,
    expected_identity: tuple[int, int, int, int],
) -> None:
    raw, identity = _read_exact(
        path, expected_sha256=expected_sha256, expected_bytes=expected_bytes
    )
    if identity != expected_identity or _sha256(raw) != expected_sha256:
        raise V13ControlPlaneError("sealed source identity changed after binding")


def _load_config() -> dict[str, Any]:
    try:
        raw = CONFIG_PATH.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except V13ControlPlaneError:
        raise
    except Exception as exc:
        raise V13ControlPlaneError("V13 configuration is unreadable") from exc
    expected = {
        "schema",
        "candidate_id",
        "status",
        "control_module_path",
        "control_module_bytes",
        "control_module_sha256",
        "preserved_v12_path",
        "preserved_v12_bytes",
        "preserved_v12_sha256",
        "v12_rejection_checkpoint_path",
        "v12_rejection_checkpoint_sha256",
        "production_routing_authorized",
        "live_execution_authorized",
        "future_harness_authoring_authorized",
        "playback_authorized",
        "different_fresh_static_audit_required",
    }
    if type(value) is not dict or set(value) != expected:
        raise V13ControlPlaneError("V13 configuration schema is not exact")
    if (
        value["schema"] != "kira.blackwell.v13.control_plane_binding_config.v1"
        or value["candidate_id"] != CANDIDATE_ID
        or value["status"] != "SEALED_STATIC_ONLY_PENDING_DIFFERENT_FRESH_AUDIT"
        or value["control_module_path"] != "Core/persistent_blackwell_voice_integration_v13.py"
        or type(value["control_module_bytes"]) is not int
        or value["control_module_bytes"] <= 0
        or not _is_sha256(value["control_module_sha256"])
        or value["preserved_v12_path"]
        != "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/canonical_typed_memory_binding.py"
        or value["preserved_v12_bytes"] != V12_BYTES
        or value["preserved_v12_sha256"] != V12_SHA256
        or value["v12_rejection_checkpoint_path"]
        != "RecoverySprint/continuation_20260811/blackwell_v12_canonical_typed_memory_integration_fresh_static_audit/attempt_01/CHECKPOINT.md"
        or not _is_sha256(value["v12_rejection_checkpoint_sha256"])
        or value["production_routing_authorized"] is not False
        or value["live_execution_authorized"] is not False
        or value["future_harness_authoring_authorized"] is not False
        or value["playback_authorized"] is not False
        or value["different_fresh_static_audit_required"] is not True
    ):
        raise V13ControlPlaneError("V13 configuration values are not exact")
    return value


def _ensure_v12_import_slots_clean() -> None:
    if V12_NAME in sys.modules or PRIVATE_V12_NAME in sys.modules:
        raise V13ControlPlaneError("normal or private V12 module slot is occupied")
    parent = sys.modules.get(V12_PARENT)
    if parent is not None and hasattr(parent, "canonical_typed_memory_binding"):
        raise V13ControlPlaneError("normal V12 package attribute is occupied")


class _SealedLoader:
    __slots__ = ("name", "origin", "source_sha256")

    def __init__(self, name: str, origin: str, source_sha256: str) -> None:
        self.name = name
        self.origin = origin
        self.source_sha256 = source_sha256


def _load_private_v12() -> tuple[types.ModuleType, _SealedLoader, Any, tuple[int, int, int, int]]:
    _ensure_v12_import_slots_clean()
    raw, identity = _read_exact(V12_PATH, expected_sha256=V12_SHA256, expected_bytes=V12_BYTES)
    resolved = V12_PATH.resolve(strict=True)
    loader = _SealedLoader(PRIVATE_V12_NAME, str(resolved), V12_SHA256)
    spec = importlib.machinery.ModuleSpec(PRIVATE_V12_NAME, loader, origin=str(resolved))
    module = types.ModuleType(PRIVATE_V12_NAME)
    module.__file__ = str(resolved)
    module.__loader__ = loader
    module.__package__ = ""
    module.__spec__ = spec
    module.__cached__ = None
    code = compile(raw, str(resolved), "exec", dont_inherit=True, optimize=0)
    exec(code, module.__dict__)
    _ensure_v12_import_slots_clean()
    _verify_exact(
        V12_PATH,
        expected_sha256=V12_SHA256,
        expected_bytes=V12_BYTES,
        expected_identity=identity,
    )
    return module, loader, spec, identity


def _typed_snapshot(value: Any) -> Any:
    if value is None or type(value) in (bool, int, float, str, bytes):
        if type(value) is float and not math.isfinite(value):
            raise V13ControlPlaneError("non-finite metadata rejected")
        return (type(value).__name__, value)
    if type(value) is tuple:
        return ("tuple", tuple(_typed_snapshot(item) for item in value))
    if type(value) is list:
        return ("list", tuple(_typed_snapshot(item) for item in value))
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise V13ControlPlaneError("metadata keys must be exact strings")
        return ("dict", tuple((key, _typed_snapshot(value[key])) for key in sorted(value)))
    return ("identity", type(value), id(value))


class _FunctionSeal:
    __slots__ = (
        "function", "module_dict", "code", "code_sha256", "defaults", "defaults_snapshot",
        "kwdefaults", "kwdefaults_snapshot", "annotations", "annotations_snapshot",
        "function_dict", "function_dict_snapshot", "closure", "closure_cells",
        "closure_contents", "builtins", "referenced_globals", "referenced_builtins",
        "name", "qualname", "module_name",
    )

    def __init__(self, function: Any, module_dict: dict[str, Any], *, label: str) -> None:
        if type(function) is not types.FunctionType or function.__globals__ is not module_dict:
            raise V13ControlPlaneError(f"{label} is not an exact module function")
        self.function = function
        self.module_dict = module_dict
        self.code = function.__code__
        self.code_sha256 = _sha256(marshal.dumps(function.__code__))
        self.defaults = function.__defaults__
        self.defaults_snapshot = _typed_snapshot(function.__defaults__)
        self.kwdefaults = function.__kwdefaults__
        self.kwdefaults_snapshot = _typed_snapshot(function.__kwdefaults__)
        self.annotations = function.__annotations__
        self.annotations_snapshot = _typed_snapshot(function.__annotations__)
        self.function_dict = function.__dict__
        self.function_dict_snapshot = _typed_snapshot(function.__dict__)
        self.closure = function.__closure__
        self.closure_cells = tuple(function.__closure__ or ())
        self.closure_contents = tuple(_typed_snapshot(cell.cell_contents) for cell in self.closure_cells)
        self.builtins = function.__builtins__
        self.referenced_globals = tuple(
            (name, module_dict[name]) for name in function.__code__.co_names if name in module_dict
        )
        self.referenced_builtins = tuple(
            (name, function.__builtins__[name])
            for name in function.__code__.co_names
            if name not in module_dict and name in function.__builtins__
        )
        self.name = function.__name__
        self.qualname = function.__qualname__
        self.module_name = function.__module__

    def verify(self, *, label: str) -> None:
        function = self.function
        if type(function) is not types.FunctionType or function.__globals__ is not self.module_dict:
            raise V13ControlPlaneError(f"{label} function/globals identity changed")
        if function.__code__ is not self.code:
            raise V13ControlPlaneError(f"{label} code identity changed")
        if function.__defaults__ is not self.defaults or _typed_snapshot(function.__defaults__) != self.defaults_snapshot:
            raise V13ControlPlaneError(f"{label} defaults changed")
        if function.__kwdefaults__ is not self.kwdefaults or _typed_snapshot(function.__kwdefaults__) != self.kwdefaults_snapshot:
            raise V13ControlPlaneError(f"{label} keyword defaults changed")
        if function.__annotations__ is not self.annotations or _typed_snapshot(function.__annotations__) != self.annotations_snapshot:
            raise V13ControlPlaneError(f"{label} annotations changed")
        if function.__dict__ is not self.function_dict or _typed_snapshot(function.__dict__) != self.function_dict_snapshot:
            raise V13ControlPlaneError(f"{label} metadata changed")
        if function.__closure__ is not self.closure:
            raise V13ControlPlaneError(f"{label} closure tuple changed")
        cells = tuple(function.__closure__ or ())
        if len(cells) != len(self.closure_cells) or any(a is not b for a, b in zip(cells, self.closure_cells)):
            raise V13ControlPlaneError(f"{label} closure cells changed")
        if tuple(_typed_snapshot(cell.cell_contents) for cell in cells) != self.closure_contents:
            raise V13ControlPlaneError(f"{label} closure contents changed")
        if function.__builtins__ is not self.builtins:
            raise V13ControlPlaneError(f"{label} builtins changed")
        if function.__name__ != self.name or function.__qualname__ != self.qualname or function.__module__ != self.module_name:
            raise V13ControlPlaneError(f"{label} name/module changed")
        for name, expected in self.referenced_globals:
            if self.module_dict.get(name, _MISSING) is not expected:
                raise V13ControlPlaneError(f"{label} referenced global changed: {name}")
        for name, expected in self.referenced_builtins:
            if function.__builtins__.get(name, _MISSING) is not expected:
                raise V13ControlPlaneError(f"{label} referenced builtin changed: {name}")


class _ClassSeal:
    __slots__ = ("class_object", "keys", "values", "method_seals", "label")

    def __init__(self, value: type, module_dict: dict[str, Any], *, label: str) -> None:
        self.class_object = value
        self.keys = frozenset(value.__dict__)
        self.values = tuple(value.__dict__.items())
        self.method_seals = tuple(
            (name, _FunctionSeal(item, module_dict, label=f"{label}.{name}"))
            for name, item in value.__dict__.items()
            if type(item) is types.FunctionType and item.__globals__ is module_dict
        )
        self.label = label

    def verify(self) -> None:
        if frozenset(self.class_object.__dict__) != self.keys:
            raise V13ControlPlaneError(f"{self.label} class schema changed")
        for name, expected in self.values:
            if self.class_object.__dict__.get(name, _MISSING) is not expected:
                raise V13ControlPlaneError(f"{self.label} class member changed: {name}")
        for name, seal in self.method_seals:
            seal.verify(label=f"{self.label}.{name}")


class BlackwellV13ControlPlaneBinding:
    """Exact private V12 control-plane binding; static-only and non-copyable."""

    __slots__ = (
        "_seal", "_lock", "_config", "_self_module", "_self_parent", "_self_keys",
        "_self_values", "_self_identity", "_v12_module", "_v12_loader", "_v12_spec",
        "_v12_identity", "_v12_keys", "_v12_values", "_v12_function_seals",
        "_v12_class_seals", "_create", "_install", "_revalidate", "_read", "_binding",
        "_prepared", "_quarantined", "_control_sha256",
    )

    def __new__(cls, key: object | None = None):
        if key is not _CONSTRUCTION_KEY:
            raise TypeError("V13 control plane is controller-created only")
        return super().__new__(cls)

    def __init__(self, key: object) -> None:
        if key is not _CONSTRUCTION_KEY or _CONTROL_FINALIZED is not True:
            raise TypeError("V13 control plane is not finalized")
        self._seal = _CONSTRUCTION_KEY
        self._lock = threading.RLock()
        self._config = _load_config()
        self._self_module = sys.modules.get(__name__)
        self._self_parent = sys.modules.get("Core")
        if type(self._self_module) is not types.ModuleType or self._self_parent is None:
            raise V13ControlPlaneError("V13 module/package identity is unavailable")
        if getattr(self._self_parent, "persistent_blackwell_voice_integration_v13", None) is not self._self_module:
            raise V13ControlPlaneError("V13 package attribute is not the exact module")
        _, self._self_identity = _read_exact(
            SELF_PATH,
            expected_sha256=self._config["control_module_sha256"],
            expected_bytes=self._config["control_module_bytes"],
        )
        self._self_keys = frozenset(self._self_module.__dict__)
        self._self_values = tuple(self._self_module.__dict__.items())
        self._v12_module, self._v12_loader, self._v12_spec, self._v12_identity = _load_private_v12()
        self._v12_keys = frozenset(self._v12_module.__dict__)
        self._v12_values = tuple(self._v12_module.__dict__.items())
        self._v12_function_seals = tuple(
            (name, _FunctionSeal(value, self._v12_module.__dict__, label=f"v12.{name}"))
            for name, value in self._v12_module.__dict__.items()
            if type(value) is types.FunctionType and value.__globals__ is self._v12_module.__dict__
        )
        self._v12_class_seals = tuple(
            (name, _ClassSeal(value, self._v12_module.__dict__, label=f"v12.{name}"))
            for name, value in self._v12_module.__dict__.items()
            if type(value) is type and value.__module__ == PRIVATE_V12_NAME
        )
        self._create = self._v12_module.__dict__.get("create_canonical_typed_memory_binding")
        self._install = self._v12_module.__dict__.get("install_exact_typed_memory_probe")
        self._revalidate = self._v12_module.__dict__.get("revalidate_exact_typed_memory_probe")
        self._read = self._v12_module.__dict__.get("read_exact_typed_memory_mib")
        if any(type(value) is not types.FunctionType for value in (self._create, self._install, self._revalidate, self._read)):
            raise V13ControlPlaneError("V12 public control functions are not exact")
        self._binding = None
        self._prepared = False
        self._quarantined = False
        self._control_sha256 = _sha256(
            (
                f"v13:{self._config['control_module_sha256']}:{V12_SHA256}:"
                + ":".join(seal.code_sha256 for _, seal in self._v12_function_seals)
            ).encode("utf-8")
        )
        self._revalidate_locked(expected_prepared=False)

    def __copy__(self):
        raise TypeError("V13 control plane cannot be copied")

    def __deepcopy__(self, _memo):
        raise TypeError("V13 control plane cannot be copied")

    def __reduce__(self):
        raise TypeError("V13 control plane cannot be serialized")

    def _verify_self_module(self) -> None:
        _verify_exact(
            SELF_PATH,
            expected_sha256=self._config["control_module_sha256"],
            expected_bytes=self._config["control_module_bytes"],
            expected_identity=self._self_identity,
        )
        if sys.modules.get(__name__) is not self._self_module:
            raise V13ControlPlaneError("V13 sys.modules identity changed")
        if sys.modules.get("Core") is not self._self_parent:
            raise V13ControlPlaneError("V13 parent package identity changed")
        if getattr(self._self_parent, "persistent_blackwell_voice_integration_v13", None) is not self._self_module:
            raise V13ControlPlaneError("V13 package attribute identity changed")
        if frozenset(self._self_module.__dict__) != self._self_keys:
            raise V13ControlPlaneError("V13 module global schema changed")
        for name, expected in self._self_values:
            if self._self_module.__dict__.get(name, _MISSING) is not expected:
                raise V13ControlPlaneError(f"V13 module global changed: {name}")

    def _verify_v12_module(self) -> None:
        _ensure_v12_import_slots_clean()
        _verify_exact(
            V12_PATH,
            expected_sha256=V12_SHA256,
            expected_bytes=V12_BYTES,
            expected_identity=self._v12_identity,
        )
        resolved = str(V12_PATH.resolve(strict=True))
        if (
            type(self._v12_module) is not types.ModuleType
            or self._v12_module.__name__ != PRIVATE_V12_NAME
            or self._v12_module.__package__ != ""
            or self._v12_module.__file__ != resolved
            or self._v12_module.__cached__ is not None
            or self._v12_module.__loader__ is not self._v12_loader
            or self._v12_module.__spec__ is not self._v12_spec
            or self._v12_spec.name != PRIVATE_V12_NAME
            or self._v12_spec.origin != resolved
            or self._v12_spec.loader is not self._v12_loader
        ):
            raise V13ControlPlaneError("private V12 module shell changed")
        if frozenset(self._v12_module.__dict__) != self._v12_keys:
            raise V13ControlPlaneError("private V12 global schema changed")
        for name, expected in self._v12_values:
            if self._v12_module.__dict__.get(name, _MISSING) is not expected:
                raise V13ControlPlaneError(f"private V12 global changed: {name}")
        for name, seal in self._v12_function_seals:
            seal.verify(label=f"v12.{name}")
        for _name, seal in self._v12_class_seals:
            seal.verify()
        if (
            self._create is not self._v12_module.__dict__["create_canonical_typed_memory_binding"]
            or self._install is not self._v12_module.__dict__["install_exact_typed_memory_probe"]
            or self._revalidate is not self._v12_module.__dict__["revalidate_exact_typed_memory_probe"]
            or self._read is not self._v12_module.__dict__["read_exact_typed_memory_mib"]
        ):
            raise V13ControlPlaneError("stored V12 public function identity changed")

    def _revalidate_locked(self, *, expected_prepared: bool) -> None:
        if self._seal is not _CONSTRUCTION_KEY or self._quarantined:
            raise V13ControlPlaneError("V13 control plane is invalid or quarantined")
        if type(self._prepared) is not bool or self._prepared is not expected_prepared:
            raise V13ControlPlaneError("V13 prepared truth changed")
        self._verify_self_module()
        self._verify_v12_module()
        if expected_prepared:
            if self._binding is None:
                raise V13ControlPlaneError("prepared V13 binding is absent")
            evidence = self._revalidate(self._binding)
            if type(evidence) is not dict or evidence.get("installed") is not True:
                raise V13ControlPlaneError("private V12 installed readback is not exact")
            self._verify_self_module()
            self._verify_v12_module()
        elif self._binding is not None:
            raise V13ControlPlaneError("unprepared V13 unexpectedly retains a binding")

    def prepare_static(self) -> dict[str, Any]:
        with self._lock:
            self._revalidate_locked(expected_prepared=False)
            try:
                binding = self._create()
                self._verify_self_module()
                self._verify_v12_module()
                install = self._install(binding)
                self._verify_self_module()
                self._verify_v12_module()
                readback = self._revalidate(binding)
                self._verify_self_module()
                self._verify_v12_module()
                if (
                    type(install) is not dict
                    or type(readback) is not dict
                    or install.get("binding_sha256") != readback.get("binding_sha256")
                    or install.get("installed") is not True
                    or readback.get("installed") is not True
                    or install.get("live_backend_constructed") is not False
                    or readback.get("live_backend_constructed") is not False
                ):
                    raise V13ControlPlaneError("V12 preparation evidence is not exact")
                self._binding = binding
                self._prepared = True
                self._revalidate_locked(expected_prepared=True)
            except Exception as exc:
                self._binding = None
                self._prepared = False
                self._quarantined = True
                if isinstance(exc, V13ControlPlaneError):
                    raise
                raise V13ControlPlaneError("V13 static preparation failed closed") from exc
            return self._public_state_locked()

    def revalidate(self) -> dict[str, Any]:
        with self._lock:
            self._revalidate_locked(expected_prepared=self._prepared)
            return self._public_state_locked()

    def read_typed_memory_mib(self) -> tuple[float, float, float, float]:
        with self._lock:
            self._revalidate_locked(expected_prepared=True)
            values = self._read(self._binding)
            if (
                type(values) is not tuple
                or len(values) != 4
                or any(type(value) is not float for value in values)
                or any(not math.isfinite(value) or value < 0 for value in values)
            ):
                raise V13ControlPlaneError("V13 typed memory values are not exact")
            self._revalidate_locked(expected_prepared=True)
            return values

    def _public_state_locked(self) -> dict[str, Any]:
        return {
            "schema": "kira.blackwell.v13.control_plane_binding.v1",
            "candidate_id": CANDIDATE_ID,
            "control_sha256": self._control_sha256,
            "prepared_static": self._prepared,
            "quarantined": self._quarantined,
            "private_v12_module": PRIVATE_V12_NAME,
            "private_v12_sha256": V12_SHA256,
            "normal_v12_import_state_clean": True,
            "production_routing_authorized": False,
            "live_execution_authorized": False,
            "future_harness_authoring_authorized": False,
            "playback_authorized": False,
        }

    def public_state(self) -> dict[str, Any]:
        with self._lock:
            self._revalidate_locked(expected_prepared=self._prepared)
            return self._public_state_locked()


def create_static_control_plane_binding_v13() -> BlackwellV13ControlPlaneBinding:
    return BlackwellV13ControlPlaneBinding(_CONSTRUCTION_KEY)


def open_production_blackwell_v13(*_args: Any, **_kwargs: Any) -> None:
    raise V13ControlPlaneError(
        "V13 is disconnected static evidence and authorizes no production or live route"
    )


def bounded_engineering_candidate_v13(*_args: Any, **_kwargs: Any) -> None:
    raise V13ControlPlaneError(
        "V13 authorizes no bounded engineering run or playback"
    )


__all__ = [
    "BlackwellV13ControlPlaneBinding",
    "CANDIDATE_ID",
    "FEATURE_FLAG",
    "FUTURE_HARNESS_AUTHORING_AUTHORIZED",
    "LIVE_EXECUTION_AUTHORIZED_BY_THIS_MODULE",
    "PLAYBACK_AUTHORIZED",
    "PRODUCTION_ROUTING_AUTHORIZED",
    "V13ControlPlaneError",
    "bounded_engineering_candidate_v13",
    "create_static_control_plane_binding_v13",
    "open_production_blackwell_v13",
]

_CONTROL_FINALIZED = True
