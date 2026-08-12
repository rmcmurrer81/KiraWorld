#!/usr/bin/env python3
"""Attempt-03 AFES topology evidence core.

Attempt 03 preserves the Attempt-02 compact/receipt hardening while promoting
the immutable Attempt-01 topology core to an explicit execution dependency.
The Attempt-01 implementation is imported as a module, never as copied
function/class symbols.  A future extractor must verify that module's exact
resolved source path and hash before invoking any analysis.

This module is Blender-free and has no authoring or persistence capability.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping, Sequence

from tools import kira_r25_afes_topology_core as attempt01_core
from tools import kira_r25_afes_topology_core_v2 as attempt02_core


ATTEMPT01_CORE_MODULE_NAME = "tools.kira_r25_afes_topology_core"
ATTEMPT02_CORE_MODULE_NAME = "tools.kira_r25_afes_topology_core_v2"
CompactAfesEvidenceError = attempt02_core.CompactAfesEvidenceError
FILE_TYPE_PIPE = attempt02_core.FILE_TYPE_PIPE
NANOMETERS_PER_METER = attempt02_core.NANOMETERS_PER_METER
ROUNDING_RULE = attempt02_core.ROUNDING_RULE


class ExactExecutionModuleError(RuntimeError):
    """Raised when an imported execution module is not the exact bound file."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_exact_imported_python_module(
    module: object,
    *,
    expected_module_name: str,
    expected_path: Path,
    expected_bytes: int,
    expected_sha256: str,
    required_symbols: Sequence[str],
) -> ModuleType:
    """Reject in-memory/sys.modules substitutes before an execution call.

    Besides exact ``__file__`` resolution, the imported module must have a
    normal import spec/loader whose origin and filename resolve to the same
    bound file.  Required callables/classes must identify the expected module
    as their defining module.  The bound source file is then re-hashed.
    """

    if not isinstance(module, ModuleType):
        raise ExactExecutionModuleError("execution dependency is not a module")
    if module.__name__ != expected_module_name:
        raise ExactExecutionModuleError("execution dependency module name drifted")
    raw_file = getattr(module, "__file__", None)
    if not isinstance(raw_file, str) or not raw_file:
        raise ExactExecutionModuleError("execution dependency has no source __file__")
    try:
        actual_path = Path(raw_file).resolve(strict=True)
        bound_path = Path(expected_path).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ExactExecutionModuleError(
            f"execution dependency source cannot be resolved: {exc}"
        ) from exc
    if actual_path != bound_path:
        raise ExactExecutionModuleError("execution dependency __file__ path drifted")
    spec = getattr(module, "__spec__", None)
    origin = getattr(spec, "origin", None)
    loader = getattr(spec, "loader", None)
    if not isinstance(origin, str) or loader is None:
        raise ExactExecutionModuleError("execution dependency lacks a file import spec")
    try:
        if Path(origin).resolve(strict=True) != bound_path:
            raise ExactExecutionModuleError("execution dependency import origin drifted")
    except OSError as exc:
        raise ExactExecutionModuleError(
            f"execution dependency import origin cannot be resolved: {exc}"
        ) from exc
    get_filename = getattr(loader, "get_filename", None)
    if not callable(get_filename):
        raise ExactExecutionModuleError("execution dependency loader is not file-backed")
    try:
        loader_path = Path(str(get_filename(expected_module_name))).resolve(strict=True)
    except Exception as exc:
        raise ExactExecutionModuleError(
            f"execution dependency loader filename failed: {exc}"
        ) from exc
    if loader_path != bound_path:
        raise ExactExecutionModuleError("execution dependency loader path drifted")
    if type(expected_bytes) is not int or expected_bytes < 1:
        raise ExactExecutionModuleError("bound execution dependency byte count is invalid")
    actual_bytes = bound_path.stat().st_size
    actual_sha256 = _sha256_file(bound_path)
    if actual_bytes != expected_bytes or actual_sha256 != expected_sha256:
        raise ExactExecutionModuleError(
            "execution dependency file hash/size drifted: "
            f"bytes={actual_bytes}, sha256={actual_sha256}"
        )
    for symbol_name in required_symbols:
        symbol = getattr(module, symbol_name, None)
        if not callable(symbol):
            raise ExactExecutionModuleError(
                f"execution dependency symbol is absent: {symbol_name}"
            )
        if getattr(symbol, "__module__", None) != expected_module_name:
            raise ExactExecutionModuleError(
                f"execution dependency symbol origin drifted: {symbol_name}"
            )
    return module


def analyze_afes_topology_v3(
    *,
    vertex_count: int,
    edges: Iterable[Sequence[int]],
    faces: Iterable[Sequence[int]],
    memberships: Mapping[str, Iterable[int]],
    required_group_names: Sequence[str],
    transition_ring_count: int = 2,
) -> dict[str, object]:
    """Run exact Attempt-01 classification plus Attempt-02 structure checks."""

    edge_rows = tuple(tuple(edge) for edge in edges)
    face_rows = tuple(tuple(face) for face in faces)
    membership_rows = {
        str(name): tuple(values) for name, values in memberships.items()
    }
    analysis = attempt01_core.analyze_afes_topology(
        vertex_count=vertex_count,
        edges=edge_rows,
        faces=face_rows,
        memberships=membership_rows,
        required_group_names=required_group_names,
        transition_ring_count=transition_ring_count,
    )
    transition_vertices = analysis["transition_rings"]["combined_vertex_indices"]
    structure = attempt02_core.analyze_foundation_topology_structure(
        vertex_count=vertex_count,
        edges=edge_rows,
        faces=face_rows,
        transition_vertices=transition_vertices,
    )
    if analysis["whole_mesh"]["topology_sha256"] != structure[
        "full_normalized_topology_sha256"
    ]:
        raise CompactAfesEvidenceError("whole-topology digest computation drifted")
    result = dict(analysis)
    result["topology_structure"] = structure
    return result


def canonical_json_sha256(value: object) -> str:
    return attempt01_core.canonical_json_sha256(value)


def meters_float_to_nanometers(value: object) -> int:
    return attempt02_core.meters_float_to_nanometers(value)


def quantize_bounds_to_nanometers(
    bounds_m: Mapping[str, Sequence[object]],
) -> dict[str, object]:
    return attempt02_core.quantize_bounds_to_nanometers(bounds_m)


def compact_afes_analysis(
    analysis: Mapping[str, Any], bounds_object_nm: Mapping[str, Any]
) -> dict[str, object]:
    return attempt02_core.compact_afes_analysis(analysis, bounds_object_nm)


def validate_compact_afes_analysis(
    compact: Mapping[str, Any],
) -> dict[str, object]:
    return attempt02_core.validate_compact_afes_analysis(compact)


def decode_blob(reference: str, record: Mapping[str, Any]) -> tuple[int, ...]:
    return attempt02_core.decode_blob(reference, record)


def decode_index_reference(
    reference: Mapping[str, Any], blobs: Mapping[str, Mapping[str, Any]]
) -> tuple[int, ...]:
    return attempt02_core.decode_index_reference(reference, blobs)


def decode_edge_reference(
    reference: Mapping[str, Any], blobs: Mapping[str, Mapping[str, Any]]
) -> tuple[tuple[int, int], ...]:
    return attempt02_core.decode_edge_reference(reference, blobs)


def require_win32_pipe_handle(
    raw_handle: object,
    *,
    kernel32: object | None = None,
    platform_name: str | None = None,
) -> int:
    return attempt02_core.require_win32_pipe_handle(
        raw_handle, kernel32=kernel32, platform_name=platform_name
    )


__all__ = [
    "ATTEMPT01_CORE_MODULE_NAME",
    "ATTEMPT02_CORE_MODULE_NAME",
    "CompactAfesEvidenceError",
    "ExactExecutionModuleError",
    "FILE_TYPE_PIPE",
    "NANOMETERS_PER_METER",
    "ROUNDING_RULE",
    "analyze_afes_topology_v3",
    "attempt01_core",
    "attempt02_core",
    "canonical_json_sha256",
    "compact_afes_analysis",
    "decode_blob",
    "decode_edge_reference",
    "decode_index_reference",
    "meters_float_to_nanometers",
    "quantize_bounds_to_nanometers",
    "require_exact_imported_python_module",
    "require_win32_pipe_handle",
    "validate_compact_afes_analysis",
]
