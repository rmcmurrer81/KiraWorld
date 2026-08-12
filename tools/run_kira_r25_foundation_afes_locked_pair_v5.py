#!/usr/bin/env python3
"""Private locked controller for R25 AFES locked-pair Attempt 05.

Attempt 05 retains the exact Attempt-04 process, Win32 pipe, bounded stream,
suspended-child, Job-object, receipt, and cleanup implementation as a locked
execution core.  This source adds the two rejected boundaries around that core:
an exact recursively typed foundation-bound result validator and fresh
nonce-scoped Blender runtime directories.  It is never a direct entry point.
"""

from __future__ import annotations

import base64
import builtins
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
from types import ModuleType
from typing import Any, Callable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v5.json"
)
OUTPUT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution/attempt_05"
)
RUNTIME_BASE_RELATIVE_PATH = (
    "RecoverySprint/runtime_cache/r25_blender_v5/attempt_05"
)
HEX64 = re.compile(r"[0-9a-f]{64}")
SHA_REF = re.compile(r"sha256:[0-9a-f]{64}")
INDEX_SEMANTIC = "sorted_unique_index_json_sha256_v1"
EDGE_SEMANTIC = "sorted_unique_undirected_edge_pair_json_sha256_v1"
BLOB_CODEC = "uint32_big_endian_v1"
ROUNDING_RULE = "decimal_from_shortest_roundtrip_float_then_half_even_to_integer"
NANOMETERS_PER_METER = 1_000_000_000
PASSTHROUGH_IF_PRESENT = (
    "SYSTEMROOT", "WINDIR", "USERNAME", "USERPROFILE", "HOMEDRIVE",
    "HOMEPATH", "LOCALAPPDATA", "APPDATA",
)
FORCED_ENVIRONMENT = {
    "PYTHONNOUSERSITE": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
}
OUTER_TRUTH_BOUNDARY = [
    "READ_ONLY_FOUNDATION_DIAGNOSTIC",
    "NO_BLEND_MUTATION_OR_SAVE",
    "NO_RENDER_OR_EXPORT",
    "NO_CANDIDATE_OR_BODY_AUTHORING",
    "THIS_SINGLE_RUN_IS_NOT_ACCEPTANCE",
]


class LockedPairV5Error(RuntimeError):
    """An Attempt-05 parent boundary failed closed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def _exact_typed_equal(observed: object, expected: object) -> bool:
    if type(observed) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(observed) == set(expected) and all(
            _exact_typed_equal(observed[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(observed) == len(expected) and all(
            _exact_typed_equal(left, right)
            for left, right in zip(observed, expected)
        )
    return observed == expected


def _require_exact_keys(value: object, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise LockedPairV5Error(f"{label}_exact_keys_mismatch")
    return value


def _require_int(value: object, label: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise LockedPairV5Error(f"{label}_not_exact_int")
    result = int(value)
    if minimum is not None and result < minimum:
        raise LockedPairV5Error(f"{label}_below_minimum")
    return result


def _require_hex(value: object, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise LockedPairV5Error(f"{label}_not_sha256")
    return value


def _has_reparse_attribute(path: Path) -> bool:
    try:
        attributes = int(getattr(os.lstat(path), "st_file_attributes", 0))
    except OSError as exc:
        raise LockedPairV5Error(f"runtime_path_stat_failed:{path}") from exc
    return path.is_symlink() or bool(attributes & 0x00000400)


def _assert_existing_chain_not_reparse(path: Path, stop: Path) -> None:
    stop = stop.resolve(strict=True)
    candidate = path
    chain: list[Path] = []
    while True:
        chain.append(candidate)
        if candidate == stop:
            break
        if candidate.parent == candidate:
            raise LockedPairV5Error("runtime_path_outside_project")
        candidate = candidate.parent
    for item in reversed(chain):
        if item.exists() and _has_reparse_attribute(item):
            raise LockedPairV5Error(f"runtime_reparse_path_refused:{item}")


def _empty_tree_digest(root: Path) -> str:
    rows: list[dict[str, object]] = []
    for path in sorted(root.rglob("*"), key=lambda item: str(item).casefold()):
        if _has_reparse_attribute(path):
            raise LockedPairV5Error(f"runtime_reparse_entry_refused:{path}")
        rows.append({
            "relative_path": path.relative_to(root).as_posix(),
            "kind": "directory" if path.is_dir() else "file",
            "bytes": 0 if path.is_dir() else path.stat().st_size,
        })
    return _sha256_bytes(_canonical_json_bytes(rows))


class WindowsEmptyDirectorySeal:
    """Retain deny-write/delete directory handles for empty Blender lookup roots."""

    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 0x00000001
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000

    def __init__(self, paths: Sequence[Path]) -> None:
        if os.name != "nt":
            raise LockedPairV5Error("runtime_directory_seal_is_windows_only")
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
        ]
        self.kernel32.CreateFileW.restype = wintypes.HANDLE
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.paths = tuple(Path(path).resolve(strict=True) for path in paths)
        self.handles: list[int] = []
        invalid = ctypes.c_void_p(-1).value
        try:
            for path in self.paths:
                if any(path.iterdir()):
                    raise LockedPairV5Error(f"runtime_seal_target_not_empty:{path}")
                handle = self.kernel32.CreateFileW(
                    str(path), self.GENERIC_READ, self.FILE_SHARE_READ, None,
                    self.OPEN_EXISTING,
                    self.FILE_FLAG_BACKUP_SEMANTICS | self.FILE_FLAG_OPEN_REPARSE_POINT,
                    None,
                )
                if handle in (None, invalid):
                    raise LockedPairV5Error(
                        f"runtime_directory_seal_failed:{path}:"
                        f"winerror={ctypes.get_last_error()}"
                    )
                self.handles.append(int(handle))
        except BaseException:
            self.close()
            raise

    def verify_empty(self) -> None:
        for path in self.paths:
            if _has_reparse_attribute(path) or any(path.iterdir()):
                raise LockedPairV5Error(f"sealed_runtime_directory_changed:{path}")

    def close(self) -> None:
        first: Exception | None = None
        while self.handles:
            handle = self.handles.pop()
            if not self.kernel32.CloseHandle(handle) and first is None:
                first = LockedPairV5Error(
                    f"runtime_directory_seal_close_failed:{ctypes.get_last_error()}"
                )
        if first is not None:
            raise first


class RuntimeLease:
    def __init__(
        self, *, root: Path, directories: Mapping[str, Path], seal: Any,
        prelaunch_inventory_sha256: str,
    ) -> None:
        self.root = root
        self.directories = dict(directories)
        self.seal = seal
        self.prelaunch_inventory_sha256 = prelaunch_inventory_sha256

    def verify_before_child(self) -> None:
        expected_names = {"temp", "user_config", "user_scripts", "user_datafiles"}
        if set(self.directories) != expected_names:
            raise LockedPairV5Error("runtime_directory_set_drifted")
        if set(path.name for path in self.directories.values()) != expected_names:
            raise LockedPairV5Error("runtime_directory_name_drifted")
        if any(not path.is_dir() or any(path.iterdir()) for path in self.directories.values()):
            raise LockedPairV5Error("runtime_directory_not_fresh_empty")
        if _empty_tree_digest(self.root) != self.prelaunch_inventory_sha256:
            raise LockedPairV5Error("runtime_prelaunch_inventory_drifted")
        self.seal.verify_empty()

    def verify_after_child(self) -> None:
        self.seal.verify_empty()
        for name in ("user_config", "user_scripts", "user_datafiles"):
            if any(self.directories[name].iterdir()):
                raise LockedPairV5Error(f"protected_runtime_content_created:{name}")

    def close(self) -> None:
        self.seal.close()


def _prepare_pair_runtime_root(
    *, pair_session_nonce: str, project_root: Path = PROJECT_ROOT,
) -> Path:
    _require_hex(pair_session_nonce, "pair_session_nonce")
    root_project = project_root.resolve(strict=True)
    base = project_root / RUNTIME_BASE_RELATIVE_PATH
    _assert_existing_chain_not_reparse(base, root_project)
    base.mkdir(parents=True, exist_ok=True)
    _assert_existing_chain_not_reparse(base, root_project)
    pair_path_token = _sha256_bytes(pair_session_nonce.encode("ascii"))[:32]
    pair_root = base / f"pair_{pair_path_token}"
    try:
        pair_root.mkdir(parents=False, exist_ok=False)
    except FileExistsError as exc:
        raise LockedPairV5Error("runtime_pair_scope_preoccupied") from exc
    return pair_root.resolve(strict=True)


def _prepare_runtime_lease(
    *, pair_session_nonce: str, run_nonce: str, run_number: int,
    seal_factory: Callable[[Sequence[Path]], Any] = WindowsEmptyDirectorySeal,
    project_root: Path = PROJECT_ROOT,
    pair_root: Path | None = None,
) -> RuntimeLease:
    _require_hex(pair_session_nonce, "pair_session_nonce")
    _require_hex(run_nonce, "run_nonce")
    if pair_session_nonce == run_nonce or run_number not in (1, 2):
        raise LockedPairV5Error("runtime_scope_identity_invalid")
    run_path_token = _sha256_bytes(
        f"{pair_session_nonce}:{run_number}:{run_nonce}".encode("ascii")
    )[:32]
    expected_pair = project_root / RUNTIME_BASE_RELATIVE_PATH / (
        "pair_" + _sha256_bytes(pair_session_nonce.encode("ascii"))[:32]
    )
    if pair_root is None:
        pair_root = _prepare_pair_runtime_root(
            pair_session_nonce=pair_session_nonce, project_root=project_root,
        )
    else:
        if pair_root.resolve(strict=True) != expected_pair.resolve(strict=True):
            raise LockedPairV5Error("runtime_pair_scope_identity_mismatch")
        _assert_existing_chain_not_reparse(pair_root, project_root.resolve(strict=True))
    run_root = pair_root / f"run_{run_number:02d}_{run_path_token}"
    try:
        run_root.mkdir(parents=False, exist_ok=False)
    except FileExistsError as exc:
        raise LockedPairV5Error("runtime_run_scope_preoccupied") from exc
    names = ("temp", "user_config", "user_scripts", "user_datafiles")
    directories = {name: run_root / name for name in names}
    for path in directories.values():
        path.mkdir(parents=False, exist_ok=False)
    if any(any(path.iterdir()) for path in directories.values()):
        raise LockedPairV5Error("fresh_runtime_directory_was_not_empty")
    inventory = _empty_tree_digest(run_root)
    seal = seal_factory([
        directories["user_config"], directories["user_scripts"],
        directories["user_datafiles"],
    ])
    lease = RuntimeLease(
        root=run_root.resolve(strict=True), directories=directories,
        seal=seal, prelaunch_inventory_sha256=inventory,
    )
    lease.verify_before_child()
    return lease


_RUNTIME_SCOPE: tuple[str, str, int] | None = None
_RUNTIME_PAIR_ROOT: Path | None = None
_ACTIVE_RUNTIME_LEASE: RuntimeLease | None = None


def _restricted_environment(blender: Path) -> dict[str, str]:
    global _ACTIVE_RUNTIME_LEASE
    if (
        _RUNTIME_SCOPE is None or _RUNTIME_PAIR_ROOT is None
        or _ACTIVE_RUNTIME_LEASE is not None
    ):
        raise LockedPairV5Error("runtime_scope_not_fresh")
    pair_nonce, run_nonce, run_number = _RUNTIME_SCOPE
    lease = _prepare_runtime_lease(
        pair_session_nonce=pair_nonce, run_nonce=run_nonce, run_number=run_number,
        pair_root=_RUNTIME_PAIR_ROOT,
    )
    _ACTIVE_RUNTIME_LEASE = lease
    environment = {
        name: os.environ[name]
        for name in PASSTHROUGH_IF_PRESENT if os.environ.get(name)
    }
    windir = environment.get("WINDIR") or environment.get("SYSTEMROOT")
    if not windir:
        raise LockedPairV5Error("windows_root_environment_missing")
    environment["Path"] = os.pathsep.join(
        (str(blender.parent), str(Path(windir) / "System32"), str(Path(windir)))
    )
    environment.update(FORCED_ENVIRONMENT)
    environment.update({
        "TEMP": str(lease.directories["temp"]),
        "TMP": str(lease.directories["temp"]),
        "BLENDER_USER_CONFIG": str(lease.directories["user_config"]),
        "BLENDER_USER_SCRIPTS": str(lease.directories["user_scripts"]),
        "BLENDER_USER_DATAFILES": str(lease.directories["user_datafiles"]),
        "KIRA_RUNTIME_SCOPE_SHA256": _sha256_bytes(
            _canonical_json_bytes({
                "pair_session_nonce": pair_nonce,
                "run_nonce": run_nonce,
                "run_number": run_number,
                "root": str(lease.root),
                "prelaunch_inventory_sha256": lease.prelaunch_inventory_sha256,
            })
        ),
    })
    return environment


def _validate_reference(
    value: object, *, label: str, semantic: str,
    expected_count: int | None = None, expected_sha256: str | None = None,
) -> Mapping[str, Any]:
    row = _require_exact_keys(
        value, {"blob_ref", "semantic", "item_count", "semantic_sha256"}, label,
    )
    if not isinstance(row["blob_ref"], str) or SHA_REF.fullmatch(row["blob_ref"]) is None:
        raise LockedPairV5Error(f"{label}_blob_ref_invalid")
    if row["semantic"] != semantic:
        raise LockedPairV5Error(f"{label}_semantic_invalid")
    count = _require_int(row["item_count"], f"{label}_item_count", minimum=0)
    digest = _require_hex(row["semantic_sha256"], f"{label}_semantic_sha256")
    if expected_count is not None and count != expected_count:
        raise LockedPairV5Error(f"{label}_foundation_count_mismatch")
    if expected_sha256 is not None and digest != expected_sha256:
        raise LockedPairV5Error(f"{label}_foundation_digest_mismatch")
    return row


def _validate_foundation_bound_analysis(
    analysis: object, *, v2: Mapping[str, Any], attempt03: ModuleType,
) -> str:
    compact = _require_exact_keys(analysis, {
        "whole_mesh", "topology_structure", "groups", "afes_union",
        "transition_rings", "bounds_object_nm", "binary_arrays",
    }, "analysis")
    decoded = attempt03.validate_compact_afes_analysis(compact)
    if not isinstance(decoded, Mapping) or set(decoded) != {
        "groups", "afes_union", "incident_faces", "internal_faces",
        "connection_edges", "transition_rings", "combined_transition_vertices",
    }:
        raise LockedPairV5Error("analysis_decoder_result_shape_mismatch")
    foundation = _require_exact_keys(v2.get("foundation_contract"), {
        "object_name", "mesh_name", "vertices", "edges", "faces",
        "required_transition_ring_count", "required_topology_structure",
        "membership_weight_threshold_numerator", "membership_weight_comparison",
        "expected_bounds_object_nanometers", "required_groups", "afes_union",
    }, "foundation_contract")
    whole = _require_exact_keys(compact["whole_mesh"], {
        "vertex_count", "edge_count", "face_count", "topology_sha256",
    }, "analysis_whole_mesh")
    for key, expected_key in (
        ("vertex_count", "vertices"), ("edge_count", "edges"),
        ("face_count", "faces"),
    ):
        if _require_int(whole[key], f"whole_mesh_{key}", minimum=1) != foundation[expected_key]:
            raise LockedPairV5Error(f"whole_mesh_{key}_foundation_mismatch")
    topology = _require_hex(whole["topology_sha256"], "whole_mesh_topology")
    required_structure = foundation["required_topology_structure"]
    structure = _require_exact_keys(
        compact["topology_structure"],
        set(required_structure) | {"full_normalized_topology_sha256"},
        "analysis_topology_structure",
    )
    if _require_hex(
        structure["full_normalized_topology_sha256"], "normalized_topology"
    ) != topology:
        raise LockedPairV5Error("normalized_topology_whole_mesh_mismatch")
    for key, expected in required_structure.items():
        if _require_int(structure[key], f"structural_metric_{key}", minimum=0) != expected:
            raise LockedPairV5Error(f"structural_metric_{key}_foundation_mismatch")

    required_groups = foundation["required_groups"]
    groups = compact["groups"]
    if not isinstance(groups, Mapping) or set(groups) != set(required_groups):
        raise LockedPairV5Error("analysis_exact_foundation_group_set_mismatch")
    decoded_groups = decoded["groups"]
    if not isinstance(decoded_groups, Mapping) or set(decoded_groups) != set(required_groups):
        raise LockedPairV5Error("decoded_exact_foundation_group_set_mismatch")
    for name, expected in required_groups.items():
        group = _require_exact_keys(groups[name], {"vertex_indices"}, f"group_{name}")
        _validate_reference(
            group["vertex_indices"], label=f"group_{name}_vertices",
            semantic=INDEX_SEMANTIC,
            expected_count=expected["vertex_count"],
            expected_sha256=expected["vertex_index_sha256"],
        )
        if len(decoded_groups[name]) != expected["vertex_count"]:
            raise LockedPairV5Error(f"decoded_group_{name}_count_mismatch")

    union = _require_exact_keys(compact["afes_union"], {
        "vertex_indices", "incident_face_indices", "internal_face_indices",
        "primary_connection_edges",
    }, "analysis_afes_union")
    union_contract = foundation["afes_union"]
    for field, semantic, count_key, digest_key in (
        ("vertex_indices", INDEX_SEMANTIC, "vertex_count", "vertex_index_sha256"),
        ("incident_face_indices", INDEX_SEMANTIC, "incident_face_count", "incident_face_index_sha256"),
        ("internal_face_indices", INDEX_SEMANTIC, "internal_face_count", "internal_face_index_sha256"),
        ("primary_connection_edges", EDGE_SEMANTIC, "primary_connection_edge_count", "connection_edge_sha256"),
    ):
        _validate_reference(
            union[field], label=f"afes_union_{field}", semantic=semantic,
            expected_count=union_contract[count_key],
            expected_sha256=union_contract[digest_key],
        )
    for decoded_key, count_key in (
        ("afes_union", "vertex_count"),
        ("incident_faces", "incident_face_count"),
        ("internal_faces", "internal_face_count"),
        ("connection_edges", "primary_connection_edge_count"),
    ):
        if len(decoded[decoded_key]) != union_contract[count_key]:
            raise LockedPairV5Error(f"decoded_{decoded_key}_foundation_count_mismatch")

    rings = _require_exact_keys(compact["transition_rings"], {
        "ring_count", "rings", "combined_vertex_indices", "disjoint_from_afes_union",
    }, "analysis_transition_rings")
    required_ring_count = foundation["required_transition_ring_count"]
    if _require_int(rings["ring_count"], "transition_ring_count", minimum=0) != required_ring_count:
        raise LockedPairV5Error("transition_ring_count_foundation_mismatch")
    if type(rings["disjoint_from_afes_union"]) is not bool or not rings[
        "disjoint_from_afes_union"
    ]:
        raise LockedPairV5Error("transition_ring_disjointness_not_exact_true")
    ring_rows = rings["rings"]
    if not isinstance(ring_rows, list) or len(ring_rows) != required_ring_count:
        raise LockedPairV5Error("transition_ring_rows_shape_mismatch")
    for expected_number, value in enumerate(ring_rows, 1):
        row = _require_exact_keys(
            value, {"ring_number", "vertex_indices"},
            f"transition_ring_{expected_number}",
        )
        if _require_int(row["ring_number"], f"ring_{expected_number}_number") != expected_number:
            raise LockedPairV5Error("transition_ring_number_mismatch")
        _validate_reference(
            row["vertex_indices"], label=f"ring_{expected_number}_vertices",
            semantic=INDEX_SEMANTIC,
        )
    _validate_reference(
        rings["combined_vertex_indices"], label="combined_transition_vertices",
        semantic=INDEX_SEMANTIC,
    )
    if not isinstance(decoded["transition_rings"], tuple) or len(
        decoded["transition_rings"]
    ) != required_ring_count:
        raise LockedPairV5Error("decoded_transition_ring_count_mismatch")

    bounds = _require_exact_keys(compact["bounds_object_nm"], {
        "unit", "integer_units_per_meter", "rounding", "minimum", "maximum",
    }, "analysis_bounds")
    if bounds["unit"] != "nanometer" or bounds["rounding"] != ROUNDING_RULE:
        raise LockedPairV5Error("bounds_codec_mismatch")
    if _require_int(bounds["integer_units_per_meter"], "bounds_units") != NANOMETERS_PER_METER:
        raise LockedPairV5Error("bounds_unit_scale_mismatch")
    tolerance = _require_int(
        v2["coordinate_quantization"]["comparison_tolerance_nanometers"],
        "bounds_tolerance", minimum=0,
    )
    expected_bounds = foundation["expected_bounds_object_nanometers"]
    for side in ("minimum", "maximum"):
        values = bounds[side]
        if not isinstance(values, list) or len(values) != 3:
            raise LockedPairV5Error(f"bounds_{side}_shape_mismatch")
        for axis, value in enumerate(values):
            actual = _require_int(value, f"bounds_{side}_{axis}")
            expected = expected_bounds[side][axis]
            if abs(actual - expected) > tolerance:
                raise LockedPairV5Error(f"bounds_{side}_{axis}_foundation_mismatch")

    blobs = compact["binary_arrays"]
    if not isinstance(blobs, Mapping) or not blobs:
        raise LockedPairV5Error("binary_array_table_missing")
    for reference, value in blobs.items():
        if not isinstance(reference, str) or SHA_REF.fullmatch(reference) is None:
            raise LockedPairV5Error("binary_array_reference_invalid")
        row = _require_exact_keys(value, {
            "codec", "endianness", "u32_count", "raw_bytes", "raw_sha256", "base64",
        }, "binary_array_record")
        if row["codec"] != BLOB_CODEC or row["endianness"] != "big":
            raise LockedPairV5Error("binary_array_codec_mismatch")
        count = _require_int(row["u32_count"], "binary_u32_count", minimum=0)
        if _require_int(row["raw_bytes"], "binary_raw_bytes", minimum=0) != count * 4:
            raise LockedPairV5Error("binary_array_byte_count_mismatch")
        _require_hex(row["raw_sha256"], "binary_raw_sha256")
        if not isinstance(row["base64"], str):
            raise LockedPairV5Error("binary_base64_not_text")
        try:
            base64.b64decode(row["base64"].encode("ascii"), validate=True)
        except Exception as exc:
            raise LockedPairV5Error("binary_base64_invalid") from exc
    referenced_blob_ids: set[str] = set()
    for group in groups.values():
        referenced_blob_ids.add(str(group["vertex_indices"]["blob_ref"]))
    for field in (
        "vertex_indices", "incident_face_indices", "internal_face_indices",
        "primary_connection_edges",
    ):
        referenced_blob_ids.add(str(union[field]["blob_ref"]))
    for row in ring_rows:
        referenced_blob_ids.add(str(row["vertex_indices"]["blob_ref"]))
    referenced_blob_ids.add(str(rings["combined_vertex_indices"]["blob_ref"]))
    if referenced_blob_ids != set(blobs):
        raise LockedPairV5Error("binary_array_reference_closure_mismatch")
    return topology


_LEGACY_VALIDATOR: Callable[..., tuple[Mapping[str, Any], str]] | None = None


def _validate_exact_child_payload(**kwargs: Any) -> tuple[Mapping[str, Any], str]:
    if _LEGACY_VALIDATOR is None:
        raise LockedPairV5Error("attempt04_validator_core_missing")
    payload = kwargs.get("payload")
    if not isinstance(payload, Mapping):
        raise LockedPairV5Error("outer_payload_not_object")
    if payload.get("schema") != "kira.avatar.r25.foundation_afes_locked_extraction_run.v5":
        raise LockedPairV5Error("outer_v5_schema_mismatch")
    legacy_payload = dict(payload)
    legacy_payload["schema"] = "kira.avatar.r25.foundation_afes_locked_extraction_run.v4"
    legacy_kwargs = dict(kwargs)
    legacy_kwargs["payload"] = legacy_payload
    inner, _legacy_topology = _LEGACY_VALIDATOR(**legacy_kwargs)
    topology = _validate_foundation_bound_analysis(
        inner["analysis"], v2=kwargs["v2"], attempt03=kwargs["attempt03"],
    )
    return inner, topology


def _load_attempt04_core(contract: Mapping[str, Any], ledger: Any) -> ModuleType:
    row = contract["execution_sources"]["attempt04_controller_core"]
    path, source = ledger.read_exact(row, label="attempt04_controller_core")
    real_import = builtins.__import__

    def guarded_import(
        name: str, globals: object = None, locals: object = None,
        fromlist: Sequence[str] = (), level: int = 0,
    ) -> object:
        if name == "tools" or name.startswith("tools."):
            raise LockedPairV5Error(f"ambient_project_import_forbidden:{name}")
        return real_import(name, globals, locals, fromlist, level)

    private = ModuleType(f"_kira_private_afes_locked_pair_attempt04_core_{secrets.token_hex(16)}")
    private.__file__ = str(path)
    private.__package__ = ""
    private.__spec__ = None
    private.__loader__ = None
    private_builtins = dict(vars(builtins))
    private_builtins["__import__"] = guarded_import
    private.__dict__["__builtins__"] = private_builtins
    exec(compile(source, str(path), "exec", dont_inherit=True), private.__dict__, private.__dict__)
    if any(private is module for module in sys.modules.values()):
        raise LockedPairV5Error("attempt04_core_entered_sys_modules")
    required = (
        "_load_private_parent_graph", "_load_v2_config", "_run_child",
        "_reserve_outcome", "_snapshot_under_locks", "_canonical_json_bytes",
    )
    if any(not callable(getattr(private, name, None)) for name in required):
        raise LockedPairV5Error("attempt04_core_symbol_missing")
    return private


def _run_child_with_runtime_scope(
    core: ModuleType, *, pair_session_nonce: str, run_nonce: str,
    run_number: int, pair_runtime_root: Path, **kwargs: Any,
) -> tuple[Any, dict[str, Any]]:
    global _RUNTIME_SCOPE, _RUNTIME_PAIR_ROOT, _ACTIVE_RUNTIME_LEASE
    if (
        _RUNTIME_SCOPE is not None or _RUNTIME_PAIR_ROOT is not None
        or _ACTIVE_RUNTIME_LEASE is not None
    ):
        raise LockedPairV5Error("runtime_scope_reentry_refused")
    _RUNTIME_SCOPE = (pair_session_nonce, run_nonce, run_number)
    _RUNTIME_PAIR_ROOT = pair_runtime_root
    try:
        return core._run_child(
            pair_session_nonce=pair_session_nonce, run_nonce=run_nonce,
            run_number=run_number, **kwargs,
        )
    finally:
        lease = _ACTIVE_RUNTIME_LEASE
        _ACTIVE_RUNTIME_LEASE = None
        _RUNTIME_SCOPE = None
        _RUNTIME_PAIR_ROOT = None
        if lease is not None:
            try:
                lease.verify_after_child()
            finally:
                lease.close()


def run_locked_pair(
    *, bootstrap_context: Any, expected_contract_sha256: str,
    accepted_audit_sha256: str,
) -> Path:
    """Run one future audited read-only pair; this static package does not run it."""

    global _LEGACY_VALIDATOR
    if not getattr(bootstrap_context, "locks_active", False):
        raise LockedPairV5Error("external_bootstrap_locks_not_active")
    if getattr(bootstrap_context, "controller_private_execution", None) is not True:
        raise LockedPairV5Error("controller_not_private_retained_byte_execution")
    if bootstrap_context.expected_contract_sha256 != expected_contract_sha256:
        raise LockedPairV5Error("bootstrap_contract_digest_mismatch")
    if bootstrap_context.accepted_audit_sha256 != accepted_audit_sha256:
        raise LockedPairV5Error("bootstrap_audit_digest_mismatch")
    _require_hex(expected_contract_sha256, "expected_contract_sha256")
    _require_hex(accepted_audit_sha256, "accepted_audit_sha256")
    contract = bootstrap_context.contract
    if contract.get("schema") != "kira.avatar.r25.foundation_afes_locked_pair_execution.v5":
        raise LockedPairV5Error("bootstrap_contract_schema_mismatch")
    ledger = bootstrap_context.ledger
    contract_bytes = ledger.read_path(bootstrap_context.contract_path)
    if _sha256_bytes(contract_bytes) != expected_contract_sha256:
        raise LockedPairV5Error("retained_contract_digest_mismatch")
    core = _load_attempt04_core(contract, ledger)
    _LEGACY_VALIDATOR = core._validate_exact_child_payload
    core.CONTRACT_RELATIVE_PATH = CONTRACT_RELATIVE_PATH
    core.OUTPUT_RELATIVE_PATH = OUTPUT_RELATIVE_PATH
    core.OUTER_TRUTH_BOUNDARY = list(OUTER_TRUTH_BOUNDARY)
    core._restricted_environment = _restricted_environment
    core._validate_exact_child_payload = _validate_exact_child_payload
    inherited = bootstrap_context.inherited_attempt04_contract
    execution_contract = dict(contract)
    execution_contract["child_project_read_closure"] = inherited[
        "child_project_read_closure"
    ]
    pair_session_nonce = secrets.token_hex(32)
    receipt, attempt03, v5 = core._load_private_parent_graph(
        execution_contract, ledger, pair_session_nonce,
    )
    v2 = core._load_v2_config(v5, ledger)
    before = bootstrap_context.before_snapshot
    if before != bootstrap_context.snapshot_locked_files():
        raise LockedPairV5Error("locked_graph_changed_before_pair")
    output_root = (PROJECT_ROOT / OUTPUT_RELATIVE_PATH).resolve()
    output_root.relative_to(PROJECT_ROOT.resolve(strict=True))
    output_root.parent.mkdir(parents=True, exist_ok=True)
    outcome = core._reserve_outcome(output_root, receipt)
    stage = "post_outcome_reservation"
    try:
        run_nonces = [secrets.token_hex(32), secrets.token_hex(32)]
        if len({pair_session_nonce, *run_nonces}) != 3:
            raise LockedPairV5Error("fresh_nonce_collision")
        decoded_runs: list[Any] = []
        run_metadata: list[dict[str, Any]] = []
        pair_runtime_root = _prepare_pair_runtime_root(
            pair_session_nonce=pair_session_nonce,
        )
        stage = "children"
        for run_number, run_nonce in enumerate(run_nonces, 1):
            decoded, metadata = _run_child_with_runtime_scope(
                core, contract=execution_contract, v5=v5, v2=v2, ledger=ledger,
                receipt=receipt, attempt03=attempt03,
                contract_sha256=expected_contract_sha256,
                contract_bytes=len(contract_bytes), run_number=run_number,
                pair_session_nonce=pair_session_nonce, run_nonce=run_nonce,
                pair_runtime_root=pair_runtime_root,
                evidence_root=output_root,
            )
            decoded_runs.append(decoded)
            run_metadata.append(metadata)
        stage = "pair_comparison"
        first_inner = decoded_runs[0].payload["inner_attempt05_payload"]
        second_inner = decoded_runs[1].payload["inner_attempt05_payload"]
        if first_inner != second_inner:
            raise LockedPairV5Error("fresh_locked_inner_payloads_do_not_match")
        if run_metadata[0]["inner_payload_sha256"] != run_metadata[1]["inner_payload_sha256"]:
            raise LockedPairV5Error("fresh_locked_inner_digests_do_not_match")
        if run_metadata[0]["topology_sha256"] != run_metadata[1]["topology_sha256"]:
            raise LockedPairV5Error("fresh_locked_topology_digests_do_not_match")
        stage = "locked_after_snapshot"
        after = core._snapshot_under_locks(bootstrap_context)
        if before != after:
            raise LockedPairV5Error("locked_input_changed_during_pair")
        summary = {
            "schema": "kira.avatar.r25.foundation_afes_locked_pair_acceptance.v5",
            "status": "AFES_AND_TRANSITION_RINGS_EXTRACTED_READ_ONLY_PAIR_MATCHED",
            "execution_contract_sha256": expected_contract_sha256,
            "accepted_independent_audit_sha256": accepted_audit_sha256,
            "pair_session_nonce": pair_session_nonce,
            "execution_contract_bytes": len(contract_bytes),
            "bound_inputs_unchanged_under_locks": True,
            "input_snapshot_sha256": _sha256_bytes(_canonical_json_bytes(before)),
            "runs": run_metadata,
            "matching_inner_payload_sha256": run_metadata[0]["inner_payload_sha256"],
            "full_normalized_topology_sha256": run_metadata[0]["topology_sha256"],
            "truth_boundary": [
                "READ_ONLY_DIAGNOSTIC_PAIR_ONLY",
                "NO_BLEND_MUTATION_OR_SAVE",
                "NO_RENDER_EXPORT_OR_PATH_RESULT",
                "NO_BODY_CANDIDATE",
                "NO_AUTHORING_OR_RUNTIME_AUTHORITY",
            ],
        }
        outcome.accept_child_frame(receipt.encode_receipt_frame(summary))
        outcome.close()
        return output_root
    except BaseException as exc:
        failure = {
            "schema": "kira.avatar.r25.foundation_afes_locked_pair_failure.v5",
            "status": "FAILED_APPEND_ONLY_NO_BODY_AUTHORITY",
            "stage": stage,
            "failure_type": type(exc).__name__,
            "failure": str(exc),
            "execution_contract_sha256": expected_contract_sha256,
            "accepted_independent_audit_sha256": accepted_audit_sha256,
            "pair_session_nonce": pair_session_nonce,
            "receipt_truth": (
                "post_reservation_failure_receipt_attempted; abrupt process termination "
                "or storage failure can still prevent completion"
            ),
        }
        try:
            outcome.accept_child_frame(receipt.encode_receipt_frame(failure))
        finally:
            outcome.close()
        raise
    finally:
        _LEGACY_VALIDATOR = None


def main() -> int:
    print(
        "R25_AFES_LOCKED_PAIR_V5_DIRECT_EXECUTION_REFUSED_USE_EXTERNAL_LAUNCHER",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
