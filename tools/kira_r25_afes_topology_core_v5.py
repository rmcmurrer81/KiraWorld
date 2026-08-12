#!/usr/bin/env python3
"""Private exact-byte dependency loader for R25 AFES Attempt 05.

This module imports no project module or ambient ``dataclasses`` module.  A
future extractor compiles this exact source into a fresh private namespace,
then uses it to read, verify, compile, and execute the bound
Attempt-01/v2/v3/receipt sources into fresh private ModuleType objects.
Ambient ``sys.modules`` project or receipt/dataclass objects are never used.
"""

from __future__ import annotations

import builtins
import hashlib
from pathlib import Path
import sys
from types import ModuleType
from typing import Callable, Mapping, Sequence


ATTEMPT01_CANONICAL = "tools.kira_r25_afes_topology_core"
ATTEMPT02_CANONICAL = "tools.kira_r25_afes_topology_core_v2"
ATTEMPT03_CANONICAL = "tools.kira_r25_afes_topology_core_v3"
RECEIPT_CANONICAL = "tools.kira_r25_canonical_receipt"
DATACLASSES_CANONICAL = "dataclasses"
RECEIPT_RUNTIME_NAME = "_kira_private_canonical_receipt_attempt05"
DATACLASS_SHIM_RUNTIME_NAME = "_kira_private_dataclass_shim_attempt05"
SECURITY_PROJECT_PREFIX = "tools."


class PrivateDependencyLoadError(RuntimeError):
    """A bound source could not become an isolated exact-byte module."""


class PrivateDataclassContractError(TypeError):
    """The receipt requested anything beyond its one frozen-record shape."""


class PrivateFrozenInstanceError(AttributeError):
    """A field mutation was attempted on the private frozen receipt record."""


def _make_private_dataclass_shim() -> ModuleType:
    """Build a one-use decorator for the exact ``DecodedReceipt`` declaration.

    This is deliberately not a general dataclasses implementation.  It has no
    imports and performs no module lookup.  The exact receipt source is already
    byte-bound; this shim accepts only its one ``@dataclass(frozen=True)``
    declaration and installs only the constructor/frozen/equality behavior the
    decoder uses.
    """

    consumed = [False]
    expected_annotations = {
        "payload": "dict[str, Any]",
        "canonical_payload": "bytes",
        "payload_sha256": "str",
        "frame_sha256": "str",
    }
    field_names = tuple(expected_annotations)

    def private_dataclass(cls: object = None, **options: object) -> Callable[[type], type]:
        if cls is not None or options != {"frozen": True}:
            raise PrivateDataclassContractError(
                "private dataclass shim accepts only @dataclass(frozen=True)"
            )

        def decorate(candidate: type) -> type:
            if consumed[0]:
                raise PrivateDataclassContractError(
                    "private dataclass shim is single-use"
                )
            if not isinstance(candidate, type):
                raise PrivateDataclassContractError("decorated value is not a class")
            if candidate.__name__ != "DecodedReceipt" or candidate.__qualname__ != (
                "DecodedReceipt"
            ):
                raise PrivateDataclassContractError("receipt class identity drifted")
            if candidate.__module__ != RECEIPT_RUNTIME_NAME:
                raise PrivateDataclassContractError("receipt class module drifted")
            if candidate.__dict__.get("__annotations__") != expected_annotations:
                raise PrivateDataclassContractError("receipt annotations drifted")
            if any(name in candidate.__dict__ for name in field_names):
                raise PrivateDataclassContractError("receipt field defaults are forbidden")
            if any(
                name in candidate.__dict__
                for name in ("__init__", "__repr__", "__eq__", "__hash__",
                             "__setattr__", "__delattr__")
            ):
                raise PrivateDataclassContractError("receipt class behavior drifted")
            consumed[0] = True

            def __init__(
                self: object,
                payload: object,
                canonical_payload: object,
                payload_sha256: object,
                frame_sha256: object,
            ) -> None:
                object.__setattr__(self, "payload", payload)
                object.__setattr__(self, "canonical_payload", canonical_payload)
                object.__setattr__(self, "payload_sha256", payload_sha256)
                object.__setattr__(self, "frame_sha256", frame_sha256)

            def __repr__(self: object) -> str:
                return (
                    f"{type(self).__qualname__}("
                    f"payload={self.payload!r}, "
                    f"canonical_payload={self.canonical_payload!r}, "
                    f"payload_sha256={self.payload_sha256!r}, "
                    f"frame_sha256={self.frame_sha256!r})"
                )

            def __eq__(self: object, other: object) -> object:
                if other.__class__ is self.__class__:
                    return tuple(getattr(self, name) for name in field_names) == tuple(
                        getattr(other, name) for name in field_names
                    )
                return NotImplemented

            def __hash__(self: object) -> int:
                return hash(tuple(getattr(self, name) for name in field_names))

            def __setattr__(self: object, name: str, value: object) -> None:
                raise PrivateFrozenInstanceError(f"cannot assign to field {name!r}")

            def __delattr__(self: object, name: str) -> None:
                raise PrivateFrozenInstanceError(f"cannot delete field {name!r}")

            methods = {
                "__init__": __init__, "__repr__": __repr__, "__eq__": __eq__,
                "__hash__": __hash__, "__setattr__": __setattr__,
                "__delattr__": __delattr__,
            }
            for method_name, method in methods.items():
                method.__name__ = method_name
                method.__qualname__ = f"DecodedReceipt.{method_name}"
                method.__module__ = RECEIPT_RUNTIME_NAME
                setattr(candidate, method_name, method)
            candidate.__match_args__ = field_names
            candidate.__private_frozen_record_fields__ = field_names
            candidate.__private_dataclass_shim__ = DATACLASS_SHIM_RUNTIME_NAME
            return candidate

        decorate.__module__ = DATACLASS_SHIM_RUNTIME_NAME
        return decorate

    private_dataclass.__name__ = "dataclass"
    private_dataclass.__qualname__ = "dataclass"
    private_dataclass.__module__ = DATACLASS_SHIM_RUNTIME_NAME
    shim = ModuleType(DATACLASS_SHIM_RUNTIME_NAME)
    shim.__package__ = ""
    shim.__loader__ = None
    shim.__spec__ = None
    shim.dataclass = private_dataclass
    shim.__private_exact_scope__ = "DecodedReceipt:@dataclass(frozen=True)"
    return shim


def _sha256_bytes(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _guarded_import_factory(
    dependencies: Mapping[str, ModuleType],
) -> Callable[..., object]:
    """Return an importer that resolves project dependencies only privately."""

    private = dict(dependencies)
    tools_proxy = ModuleType("_kira_private_tools_proxy")
    for canonical_name, module in private.items():
        if canonical_name.startswith("tools."):
            setattr(tools_proxy, canonical_name.split(".", 1)[1], module)
    real_import = builtins.__import__

    def guarded_import(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> object:
        if level != 0:
            if name.startswith("tools"):
                raise PrivateDependencyLoadError(
                    f"relative project import is forbidden in private source: {name}"
                )
            return real_import(name, globals, locals, fromlist, level)
        if name in private:
            if name == DATACLASSES_CANONICAL and tuple(fromlist or ()) != (
                "dataclass",
            ):
                raise PrivateDependencyLoadError(
                    "private receipt may import only dataclasses.dataclass"
                )
            return private[name]
        if name == "tools":
            for requested in fromlist or ():
                canonical = f"tools.{requested}"
                if canonical not in private:
                    raise PrivateDependencyLoadError(
                        f"unbound project dependency requested: {canonical}"
                    )
            return tools_proxy
        if name.startswith(SECURITY_PROJECT_PREFIX):
            raise PrivateDependencyLoadError(
                f"ambient project import is forbidden: {name}"
            )
        return real_import(name, globals, locals, fromlist, level)

    return guarded_import


def execute_exact_source_private(
    *,
    label: str,
    canonical_name: str,
    binding: Mapping[str, object],
    read_exact: Callable[[Mapping[str, object]], tuple[Path, bytes]],
    dependencies: Mapping[str, ModuleType],
    required_own_symbols: Sequence[str],
    runtime_name: str | None = None,
) -> ModuleType:
    """Compile/execute one verified source without consulting ambient modules."""

    try:
        path, source = read_exact(binding)
    except Exception as exc:
        raise PrivateDependencyLoadError(f"bound source read failed: {label}: {exc}") from exc
    if not isinstance(path, Path) or not isinstance(source, bytes):
        raise PrivateDependencyLoadError(f"bound source callback drifted: {label}")
    if type(binding.get("bytes")) is not int or len(source) != binding["bytes"]:
        raise PrivateDependencyLoadError(f"bound source byte count drifted: {label}")
    if _sha256_bytes(source) != binding.get("sha256"):
        raise PrivateDependencyLoadError(f"bound source SHA-256 drifted: {label}")
    if path.resolve(strict=True).as_posix() != Path(str(path)).resolve(strict=True).as_posix():
        raise PrivateDependencyLoadError(f"bound source path resolution drifted: {label}")
    name = runtime_name or f"_kira_private_{label}"
    module = ModuleType(name)
    module.__file__ = str(path.resolve(strict=True))
    module.__package__ = ""
    module.__loader__ = None
    module.__spec__ = None
    guarded_builtins = dict(vars(builtins))
    guarded_builtins["__import__"] = _guarded_import_factory(dependencies)
    module.__dict__["__builtins__"] = guarded_builtins
    module.__dict__["__private_bound_canonical_name__"] = canonical_name
    module.__dict__["__private_bound_source_sha256__"] = binding["sha256"]
    try:
        code = compile(source, str(path.resolve(strict=True)), "exec", dont_inherit=True)
        exec(code, module.__dict__, module.__dict__)
    except Exception as exc:
        raise PrivateDependencyLoadError(
            f"exact private source execution failed: {label}: {type(exc).__name__}: {exc}"
        ) from exc
    if any(module is ambient for ambient in sys.modules.values()):
        raise PrivateDependencyLoadError(f"private module entered ambient sys.modules: {label}")
    for symbol_name in required_own_symbols:
        symbol = getattr(module, symbol_name, None)
        if not callable(symbol):
            raise PrivateDependencyLoadError(
                f"private exact source symbol is absent: {label}.{symbol_name}"
            )
        code_object = getattr(symbol, "__code__", None)
        if code_object is not None and Path(code_object.co_filename).resolve(
            strict=True
        ) != path.resolve(strict=True):
            raise PrivateDependencyLoadError(
                f"private exact source symbol code path drifted: {label}.{symbol_name}"
            )
    return module


def load_private_dependency_graph(
    *,
    bindings: Mapping[str, Mapping[str, object]],
    read_exact: Callable[[Mapping[str, object]], tuple[Path, bytes]],
) -> dict[str, ModuleType]:
    """Load the security dependency graph in one explicit, private order."""

    required_binding_names = {
        "attempt_01_topology_core_execution_dependency",
        "attempt_02_hardening_core_execution_dependency",
        "attempt_03_hardening_core_execution_dependency",
        "canonical_receipt_helper",
    }
    if set(bindings) != required_binding_names:
        raise PrivateDependencyLoadError("private dependency binding set drifted")
    attempt01 = execute_exact_source_private(
        label="attempt01_core", canonical_name=ATTEMPT01_CANONICAL,
        binding=bindings["attempt_01_topology_core_execution_dependency"],
        read_exact=read_exact, dependencies={},
        required_own_symbols=("analyze_afes_topology", "canonical_index_sha256",
                              "canonical_json_sha256", "normalize_edges", "normalize_faces"),
    )
    attempt02 = execute_exact_source_private(
        label="attempt02_core", canonical_name=ATTEMPT02_CANONICAL,
        binding=bindings["attempt_02_hardening_core_execution_dependency"],
        read_exact=read_exact, dependencies={ATTEMPT01_CANONICAL: attempt01},
        required_own_symbols=("analyze_foundation_topology_structure",
                              "compact_afes_analysis", "validate_compact_afes_analysis",
                              "require_win32_pipe_handle"),
    )
    attempt03 = execute_exact_source_private(
        label="attempt03_core", canonical_name=ATTEMPT03_CANONICAL,
        binding=bindings["attempt_03_hardening_core_execution_dependency"],
        read_exact=read_exact,
        dependencies={ATTEMPT01_CANONICAL: attempt01,
                      ATTEMPT02_CANONICAL: attempt02},
        required_own_symbols=("analyze_afes_topology_v3", "compact_afes_analysis",
                              "validate_compact_afes_analysis",
                              "require_win32_pipe_handle"),
    )
    dataclass_shim = _make_private_dataclass_shim()
    receipt = execute_exact_source_private(
        label="canonical_receipt", canonical_name=RECEIPT_CANONICAL,
        binding=bindings["canonical_receipt_helper"], read_exact=read_exact,
        dependencies={DATACLASSES_CANONICAL: dataclass_shim},
        required_own_symbols=("canonical_json_bytes", "encode_receipt_frame",
                              "decode_receipt_frame"),
        runtime_name=RECEIPT_RUNTIME_NAME,
    )
    decoded_receipt = getattr(receipt, "DecodedReceipt", None)
    if not isinstance(decoded_receipt, type):
        raise PrivateDependencyLoadError("private DecodedReceipt is absent")
    if receipt.__name__ != RECEIPT_RUNTIME_NAME or decoded_receipt.__module__ != (
        RECEIPT_RUNTIME_NAME
    ):
        raise PrivateDependencyLoadError("private receipt runtime identity drifted")
    if getattr(decoded_receipt, "__private_dataclass_shim__", None) != (
        DATACLASS_SHIM_RUNTIME_NAME
    ):
        raise PrivateDependencyLoadError("private receipt decorator drifted")
    if getattr(decoded_receipt, "__private_frozen_record_fields__", None) != (
        "payload", "canonical_payload", "payload_sha256", "frame_sha256"
    ):
        raise PrivateDependencyLoadError("private receipt record fields drifted")
    if dataclass_shim.__name__ != DATACLASS_SHIM_RUNTIME_NAME or getattr(
        dataclass_shim.dataclass, "__module__", None
    ) != DATACLASS_SHIM_RUNTIME_NAME:
        raise PrivateDependencyLoadError("private declarative-record shim identity drifted")
    for method_name in ("__init__", "__repr__", "__eq__", "__hash__",
                        "__setattr__", "__delattr__"):
        if getattr(getattr(decoded_receipt, method_name), "__module__", None) != (
            RECEIPT_RUNTIME_NAME
        ):
            raise PrivateDependencyLoadError(
                f"private receipt method identity drifted: {method_name}"
            )
    if attempt03.attempt01_core is not attempt01:
        raise PrivateDependencyLoadError("private v3 core did not retain private Attempt-01")
    if attempt03.attempt02_core is not attempt02:
        raise PrivateDependencyLoadError("private v3 core did not retain private Attempt-02")
    if attempt02.analyze_afes_topology is not attempt01.analyze_afes_topology:
        raise PrivateDependencyLoadError("private v2 copied a non-private AFES analyzer")
    modules = {
        "attempt01_core": attempt01,
        "attempt02_core": attempt02,
        "attempt03_core": attempt03,
        "canonical_receipt": receipt,
        "private_dataclass_shim": dataclass_shim,
    }
    if any(module is ambient for module in modules.values()
           for ambient in sys.modules.values()):
        raise PrivateDependencyLoadError("a private dependency aliases ambient sys.modules")
    return modules


__all__ = [
    "ATTEMPT01_CANONICAL", "ATTEMPT02_CANONICAL", "ATTEMPT03_CANONICAL",
    "RECEIPT_CANONICAL", "DATACLASSES_CANONICAL", "RECEIPT_RUNTIME_NAME",
    "DATACLASS_SHIM_RUNTIME_NAME", "PrivateDependencyLoadError",
    "PrivateDataclassContractError", "PrivateFrozenInstanceError",
    "execute_exact_source_private", "load_private_dependency_graph",
]
