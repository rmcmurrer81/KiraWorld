#!/usr/bin/env python3
"""Private exact-byte dependency loader for R25 AFES Attempt 04.

This module imports no project module.  A future extractor compiles this exact
source into a fresh private namespace, then uses it to read, verify, compile,
and execute the bound Attempt-01/v2/v3/receipt sources into fresh private
ModuleType objects.  Ambient ``sys.modules`` project objects are never used.
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
SECURITY_PROJECT_PREFIX = "tools."


class PrivateDependencyLoadError(RuntimeError):
    """A bound source could not become an isolated exact-byte module."""


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
    # The exact receipt source contains a standard-library dataclass whose
    # decorator consults sys.modules by cls.__module__.  A standard-library
    # runtime name supplies only that stdlib annotation context; the fresh
    # receipt ModuleType itself is never inserted or obtained from sys.modules.
    receipt = execute_exact_source_private(
        label="canonical_receipt", canonical_name=RECEIPT_CANONICAL,
        binding=bindings["canonical_receipt_helper"], read_exact=read_exact,
        dependencies={}, required_own_symbols=("canonical_json_bytes",
                                                "encode_receipt_frame",
                                                "decode_receipt_frame"),
        runtime_name="dataclasses",
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
    }
    if any(module is ambient for module in modules.values()
           for ambient in sys.modules.values()):
        raise PrivateDependencyLoadError("a private dependency aliases ambient sys.modules")
    return modules


__all__ = [
    "ATTEMPT01_CANONICAL", "ATTEMPT02_CANONICAL", "ATTEMPT03_CANONICAL",
    "RECEIPT_CANONICAL", "PrivateDependencyLoadError",
    "execute_exact_source_private", "load_private_dependency_graph",
]
