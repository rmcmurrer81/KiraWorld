#!/usr/bin/env python3
"""Attempt-05 private exact-byte R25 AFES extractor; do not run yet.

No security-relevant project dependency is imported from ambient Python state.
The bound loader and dependency graph are each read once, hashed, compiled,
and executed in private namespaces before any mesh analysis.
"""

from __future__ import annotations

import argparse
import builtins
import hashlib
import json
import os
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Mapping, Sequence

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_read_only_extraction_v5.json"
)
AFES_PREFIX = "AFES_LANDMARK__"


class R25AfesAttempt05Error(RuntimeError):
    """Raised before analysis/receipt output when any private gate fails."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class ExactByteLedger:
    """Physically read each project file at most once and retain exact bytes."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve(strict=True)
        self._bytes: dict[Path, bytes] = {}
        self._physical_reads: dict[Path, int] = {}

    def _path(self, relative: object) -> Path:
        text = str(relative or "")
        candidate = Path(text)
        if not text or candidate.is_absolute() or ".." in candidate.parts:
            raise R25AfesAttempt05Error(f"unsafe project-relative path: {text!r}")
        lexical = self.root
        for part in candidate.parts:
            lexical = lexical / part
            if lexical.is_symlink():
                raise R25AfesAttempt05Error(f"symlink path refused: {text!r}")
        resolved = lexical.resolve(strict=True)
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise R25AfesAttempt05Error(f"path escaped project root: {text!r}") from exc
        if not resolved.is_file():
            raise R25AfesAttempt05Error(f"project input is not a file: {text!r}")
        return resolved

    def _read_path(self, path: Path) -> bytes:
        existing = self._bytes.get(path)
        if existing is not None:
            return existing
        with path.open("rb") as stream:
            value = stream.read()
        self._bytes[path] = value
        self._physical_reads[path] = self._physical_reads.get(path, 0) + 1
        if self._physical_reads[path] != 1:
            raise R25AfesAttempt05Error("a project file was physically read more than once")
        return value

    def read_unbound(self, relative: object) -> tuple[Path, bytes]:
        path = self._path(relative)
        return path, self._read_path(path)

    def read_exact(self, binding: Mapping[str, object]) -> tuple[Path, bytes]:
        if not isinstance(binding, Mapping) or set(binding) != {"path", "bytes", "sha256"}:
            raise R25AfesAttempt05Error("exact-file binding shape drifted")
        path = self._path(binding["path"])
        value = self._read_path(path)
        if type(binding["bytes"]) is not int or len(value) != binding["bytes"]:
            raise R25AfesAttempt05Error(f"bound byte count drifted: {binding['path']}")
        if _sha256_bytes(value) != binding["sha256"]:
            raise R25AfesAttempt05Error(f"bound SHA-256 drifted: {binding['path']}")
        return path, value

    def evidence(self, relative_paths: Sequence[str]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for relative in sorted(relative_paths):
            path = self._path(relative)
            value = self._bytes.get(path)
            if value is None or self._physical_reads.get(path) != 1:
                raise R25AfesAttempt05Error(
                    f"exact one-read evidence is absent: {relative}"
                )
            rows.append({"path": relative, "physical_read_count": 1,
                         "bytes": len(value), "sha256": _sha256_bytes(value)})
        return rows


def _json_bytes(value: bytes, *, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value.decode("utf-8-sig"))
    except Exception as exc:
        raise R25AfesAttempt05Error(f"invalid JSON {label}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise R25AfesAttempt05Error(f"JSON root is not an object: {label}")
    return parsed


def _bootstrap_private_loader(
    binding: Mapping[str, object], ledger: ExactByteLedger
) -> ModuleType:
    """Compile the exact v5 loader without importing any project module."""

    path, source = ledger.read_exact(binding)
    real_import = builtins.__import__

    def bootstrap_import(
        name: str, globals: object = None, locals: object = None,
        fromlist: Sequence[str] = (), level: int = 0,
    ) -> object:
        if name == "tools" or name.startswith("tools."):
            raise R25AfesAttempt05Error(
                f"private loader attempted an ambient project import: {name}"
            )
        return real_import(name, globals, locals, fromlist, level)

    module = ModuleType("_kira_private_attempt05_loader")
    module.__file__ = str(path)
    module.__package__ = ""
    module.__spec__ = None
    module.__loader__ = None
    private_builtins = dict(vars(builtins))
    private_builtins["__import__"] = bootstrap_import
    module.__dict__["__builtins__"] = private_builtins
    try:
        exec(compile(source, str(path), "exec", dont_inherit=True),
             module.__dict__, module.__dict__)
    except Exception as exc:
        raise R25AfesAttempt05Error(
            f"private loader execution failed: {type(exc).__name__}: {exc}"
        ) from exc
    if any(module is ambient for ambient in sys.modules.values()):
        raise R25AfesAttempt05Error("private loader entered ambient sys.modules")
    for symbol_name in ("execute_exact_source_private", "load_private_dependency_graph"):
        symbol = getattr(module, symbol_name, None)
        if not callable(symbol) or Path(symbol.__code__.co_filename).resolve(
            strict=True
        ) != path:
            raise R25AfesAttempt05Error(f"private loader symbol drifted: {symbol_name}")
    return module


def _verify_rows(rows: object, ledger: ExactByteLedger) -> dict[str, dict[str, object]]:
    if not isinstance(rows, Mapping) or not rows:
        raise R25AfesAttempt05Error("exact-file table is absent")
    verified: dict[str, dict[str, object]] = {}
    for label, row in sorted(rows.items()):
        path, value = ledger.read_exact(row)
        verified[str(label)] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": len(value), "sha256": _sha256_bytes(value),
        }
    return verified


def _load_configuration(
    ledger: ExactByteLedger,
) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any],
    dict[str, object],
]:
    config_path, config_bytes = ledger.read_unbound(CONFIG_RELATIVE_PATH)
    config = _json_bytes(config_bytes, label="Attempt-05 config")
    if config.get("schema") != "kira.avatar.r25.foundation_afes_read_only_extraction.v5":
        raise R25AfesAttempt05Error("Attempt-05 config schema drifted")
    if config.get("attempt_id") != "attempt_05" or config.get("status") != (
        "STATIC_PREPARATION_ONLY_EXECUTION_NOT_AUTHORIZED"
    ):
        raise R25AfesAttempt05Error("Attempt-05 config status drifted")
    expected_scope = {
        "read_only": True, "private": True, "inactive": True,
        "candidate_creation_allowed": False, "blend_edit_allowed": False,
        "blend_save_allowed": False, "render_allowed": False,
        "export_allowed": False, "runtime_activation_allowed": False,
        "path_output_allowed": False,
        "result_transport": (
            "one_canonical_receipt_frame_to_caller_inherited_win32_pipe_only"
        ),
    }
    if config.get("scope") != expected_scope:
        raise R25AfesAttempt05Error("Attempt-05 scope drifted")
    _, v4_bytes = ledger.read_exact(config["attempt_04_baseline_config"])
    v4 = _json_bytes(v4_bytes, label="exact Attempt-04 baseline")
    if v4.get("schema") != "kira.avatar.r25.foundation_afes_read_only_extraction.v4":
        raise R25AfesAttempt05Error("Attempt-04 baseline schema drifted")
    _, v3_bytes = ledger.read_exact(v4["attempt_03_baseline_config"])
    v3 = _json_bytes(v3_bytes, label="exact Attempt-03 baseline")
    if v3.get("schema") != "kira.avatar.r25.foundation_afes_read_only_extraction.v3":
        raise R25AfesAttempt05Error("Attempt-03 baseline schema drifted")
    _, v2_bytes = ledger.read_exact(v3["attempt_02_baseline_config"])
    v2 = _json_bytes(v2_bytes, label="exact Attempt-02 baseline")
    if v2.get("schema") != "kira.avatar.r25.foundation_afes_read_only_extraction.v2":
        raise R25AfesAttempt05Error("Attempt-02 baseline schema drifted")
    return config, v4, v3, v2, {
        "path": config_path.relative_to(PROJECT_ROOT).as_posix(),
        "bytes": len(config_bytes), "sha256": _sha256_bytes(config_bytes),
    }


def _validate_r23(v2: Mapping[str, Any], ledger: ExactByteLedger) -> None:
    contract = v2["foundation_contract"]
    _, cbytes = ledger.read_exact(v2["bindings"]["r23_preflight_config"])
    _, rbytes = ledger.read_exact(v2["bindings"]["r23_preflight_attempt_04"])
    r23_config = _json_bytes(cbytes, label="R23 config")
    r23_result = _json_bytes(rbytes, label="R23 result")
    donor = r23_config.get("donor_contract")
    result = r23_result.get("qualified_cc0_donor")
    if not isinstance(donor, Mapping) or not isinstance(result, Mapping):
        raise R25AfesAttempt05Error("sealed R23 donor evidence is absent")
    if r23_config.get("inputs", {}).get("qualified_cc0_foundation_blend") != v2[
        "bindings"
    ]["foundation_blend"]:
        raise R25AfesAttempt05Error("R23/foundation binding drifted")
    expected_counts = {
        "expected_vertices": contract["vertices"], "expected_edges": contract["edges"],
        "expected_faces": contract["faces"],
        "expected_landmark_union_vertices": contract["afes_union"]["vertex_count"],
        "expected_landmark_incident_faces": contract["afes_union"]["incident_face_count"],
        "expected_landmark_internal_faces": contract["afes_union"]["internal_face_count"],
        "expected_primary_connection_edges": contract["afes_union"][
            "primary_connection_edge_count"
        ],
    }
    if any(donor.get(key) != value for key, value in expected_counts.items()):
        raise R25AfesAttempt05Error("sealed R23 donor counts drifted")
    if sorted(donor.get("required_landmark_groups", [])) != sorted(
        contract["required_groups"]
    ) or donor.get("object_name") != contract["object_name"]:
        raise R25AfesAttempt05Error("sealed R23 group/object contract drifted")
    whole = result.get("whole_mesh")
    if not isinstance(whole, Mapping) or (
        whole.get("vertices"), whole.get("edges"), whole.get("faces")
    ) != (contract["vertices"], contract["edges"], contract["faces"]):
        raise R25AfesAttempt05Error("sealed R23 mesh counts drifted")
    if result.get("groups") != contract["required_groups"]:
        raise R25AfesAttempt05Error("sealed R23 AFES groups drifted")
    union = result.get("AFES_union")
    if not isinstance(union, Mapping):
        raise R25AfesAttempt05Error("sealed R23 AFES union is absent")
    for key, expected in contract["afes_union"].items():
        if union.get(key) != expected:
            raise R25AfesAttempt05Error(f"sealed R23 AFES union drifted: {key}")


def _inventory(attempt01: ModuleType) -> dict[str, object]:
    tables = {"objects": bpy.data.objects, "meshes": bpy.data.meshes,
              "materials": bpy.data.materials, "images": bpy.data.images,
              "armatures": bpy.data.armatures, "actions": bpy.data.actions,
              "collections": bpy.data.collections, "scenes": bpy.data.scenes}
    names = {label: sorted(str(item.name) for item in table)
             for label, table in tables.items()}
    return {"counts": {label: len(values) for label, values in names.items()},
            "names_sha256": attempt01.canonical_json_sha256(names)}


def _bounds(attempt03: ModuleType, obj: Any, indices: Sequence[int]) -> dict[str, object]:
    if not indices:
        raise R25AfesAttempt05Error("cannot measure an empty AFES union")
    return attempt03.quantize_bounds_to_nanometers({
        "minimum": [min(obj.data.vertices[i].co[axis] for i in indices)
                    for axis in range(3)],
        "maximum": [max(obj.data.vertices[i].co[axis] for i in indices)
                    for axis in range(3)],
    })


def _validate_analysis(analysis: Mapping[str, Any], contract: Mapping[str, Any]) -> None:
    whole = analysis["whole_mesh"]
    if (whole["vertex_count"], whole["edge_count"], whole["face_count"]) != (
        contract["vertices"], contract["edges"], contract["faces"]
    ):
        raise R25AfesAttempt05Error("foundation topology counts drifted")
    for name, expected in contract["required_groups"].items():
        actual = analysis["groups"].get(name)
        if not isinstance(actual, Mapping) or (
            actual.get("vertex_count"), actual.get("vertex_index_sha256")
        ) != (expected["vertex_count"], expected["vertex_index_sha256"]):
            raise R25AfesAttempt05Error(f"AFES subgroup drifted: {name}")
    for key, expected in contract["afes_union"].items():
        if analysis["afes_union"].get(key) != expected:
            raise R25AfesAttempt05Error(f"AFES union drifted: {key}")
    rings = analysis["transition_rings"]
    if rings["ring_count"] != contract["required_transition_ring_count"] or not rings[
        "disjoint_from_afes_union"
    ]:
        raise R25AfesAttempt05Error("two disjoint transition rings were not extracted")
    structure = analysis["topology_structure"]
    if structure["full_normalized_topology_sha256"] != whole["topology_sha256"]:
        raise R25AfesAttempt05Error("normalized topology digest drifted")
    for key, expected in contract["required_topology_structure"].items():
        if structure.get(key) != expected:
            raise R25AfesAttempt05Error(f"foundation structural metric failed: {key}")


def extract_payload() -> tuple[
    dict[str, Any], ModuleType, ModuleType, ExactByteLedger
]:
    ledger = ExactByteLedger(PROJECT_ROOT)
    config, v4_config, v3_config, v2_config, config_binding = _load_configuration(
        ledger
    )
    # Preserve/reverify every older row from retained exact bytes.
    _verify_rows(v2_config["bindings"], ledger)
    _verify_rows(v2_config["attempt_01_preservation"], ledger)
    _verify_rows(v3_config["bindings"], ledger)
    _verify_rows(v3_config["attempt_01_preservation"], ledger)
    _verify_rows(v3_config["attempt_02_preservation"], ledger)
    _verify_rows(v4_config["bindings"], ledger)
    _verify_rows(v4_config["attempt_01_preservation"], ledger)
    _verify_rows(v4_config["attempt_02_preservation"], ledger)
    _verify_rows(v4_config["attempt_03_preservation"], ledger)
    _verify_rows(config["attempt_01_preservation"], ledger)
    _verify_rows(config["attempt_02_preservation"], ledger)
    _verify_rows(config["attempt_03_preservation"], ledger)
    _verify_rows(config["attempt_04_preservation"], ledger)
    bindings = config["bindings"]
    self_path, _ = ledger.read_exact(bindings["attempt_05_extractor"])
    if self_path != Path(__file__).resolve(strict=True):
        raise R25AfesAttempt05Error("Attempt-05 extractor path drifted")
    private_loader = _bootstrap_private_loader(bindings["attempt_05_private_loader_core"], ledger)
    graph_rows = {
        key: bindings[key] for key in (
            "attempt_01_topology_core_execution_dependency",
            "attempt_02_hardening_core_execution_dependency",
            "attempt_03_hardening_core_execution_dependency",
            "canonical_receipt_helper",
        )
    }
    try:
        graph = private_loader.load_private_dependency_graph(
            bindings=graph_rows, read_exact=ledger.read_exact
        )
    except Exception as exc:
        raise R25AfesAttempt05Error(
            f"private dependency graph failed: {type(exc).__name__}: {exc}"
        ) from exc
    attempt01 = graph["attempt01_core"]
    attempt03 = graph["attempt03_core"]
    receipt = graph["canonical_receipt"]
    dataclass_shim = graph["private_dataclass_shim"]
    _validate_r23(v2_config, ledger)
    contract = v2_config["foundation_contract"]
    foundation_path, _ = ledger.read_exact(v2_config["bindings"]["foundation_blend"])
    if Path(str(bpy.data.filepath)).resolve(strict=True) != foundation_path:
        raise R25AfesAttempt05Error("the exact bound foundation Blend is not loaded")
    if bpy.data.is_dirty or str(bpy.context.mode) != "OBJECT":
        raise R25AfesAttempt05Error("foundation is dirty or Blender is not in OBJECT mode")
    before = _inventory(attempt01)
    obj = bpy.data.objects.get(str(contract["object_name"]))
    if obj is None or obj.type != "MESH" or obj.data.name != contract["mesh_name"]:
        raise R25AfesAttempt05Error("exact foundation object/datablock is absent")
    if (len(obj.data.vertices), len(obj.data.edges), len(obj.data.polygons)) != (
        contract["vertices"], contract["edges"], contract["faces"]
    ):
        raise R25AfesAttempt05Error("exact foundation counts drifted")
    required_names = sorted(contract["required_groups"])
    actual_names = sorted(g.name for g in obj.vertex_groups if g.name.startswith(AFES_PREFIX))
    if actual_names != required_names:
        raise R25AfesAttempt05Error("exact AFES vertex-group set drifted")
    name_by_index = {int(group.index): str(group.name) for group in obj.vertex_groups}
    memberships: dict[str, list[int]] = {name: [] for name in required_names}
    for vertex in obj.data.vertices:
        for assignment in vertex.groups:
            name = name_by_index.get(int(assignment.group))
            if name in memberships and float(assignment.weight) > 0:
                memberships[name].append(int(vertex.index))
    try:
        analysis = attempt03.analyze_afes_topology_v3(
            vertex_count=len(obj.data.vertices),
            edges=[tuple(int(v) for v in edge.vertices) for edge in obj.data.edges],
            faces=[tuple(int(v) for v in face.vertices) for face in obj.data.polygons],
            memberships=memberships, required_group_names=required_names,
            transition_ring_count=contract["required_transition_ring_count"],
        )
    except Exception as exc:
        raise R25AfesAttempt05Error(f"private AFES analysis failed: {exc}") from exc
    _validate_analysis(analysis, contract)
    bounds = _bounds(attempt03, obj, analysis["afes_union"]["vertex_indices"])
    expected_bounds = contract["expected_bounds_object_nanometers"]
    tolerance = v2_config["coordinate_quantization"]["comparison_tolerance_nanometers"]
    if any(abs(bounds[side][axis] - expected_bounds[side][axis]) > tolerance
           for side in ("minimum", "maximum") for axis in range(3)):
        raise R25AfesAttempt05Error(f"AFES integer bounds drifted: {bounds}")
    compact = attempt03.compact_afes_analysis(analysis, bounds)
    attempt03.validate_compact_afes_analysis(compact)
    after = _inventory(attempt01)
    if after != before or bpy.data.is_dirty:
        raise R25AfesAttempt05Error("read-only extraction changed Blender state")
    source_paths = [str(bindings[key]["path"]) for key in (
        "attempt_05_private_loader_core",
        "attempt_01_topology_core_execution_dependency",
        "attempt_02_hardening_core_execution_dependency",
        "attempt_03_hardening_core_execution_dependency",
        "canonical_receipt_helper", "attempt_05_extractor",
    )]
    payload: dict[str, Any] = {
        "schema": "kira.avatar.r25.foundation_afes_transition_diagnostic.v5",
        "artifact_kind": "READ_ONLY_PRIVATE_EXACT_BYTE_AFES_DIAGNOSTIC",
        "status": "EXTRACTED_UNSEALED_REQUIRES_MATCHING_FRESH_LOCKED_RUN",
        "config_observed_unsealed_by_parent": config_binding,
        "private_execution_dependencies": graph_rows,
        "private_source_physical_reads": ledger.evidence(source_paths),
        "ambient_project_modules_consumed": 0,
        "ambient_dataclasses_decorator_consumed": 0,
        "private_modules_inserted_into_sys_modules": 0,
        "private_receipt_runtime": {
            "receipt_module_name": str(receipt.__name__),
            "decoded_receipt_class_module": str(receipt.DecodedReceipt.__module__),
            "dataclass_shim_module_name": str(dataclass_shim.__name__),
            "receipt_or_shim_aliases_ambient_sys_modules": False,
        },
        "foundation_object": str(obj.name), "foundation_mesh": str(obj.data.name),
        "analysis": compact,
        "topology_sealing": {
            "prior_sealed_expected_full_normalized_topology_digest_available": False,
            "required_matching_fresh_locked_extractions": 2,
            "this_receipt_alone_is_acceptance": False,
            "measured_full_normalized_topology_sha256": analysis[
                "topology_structure"
            ]["full_normalized_topology_sha256"],
        },
        "read_only_guards": {
            "blend_loaded_exactly": True, "blend_clean_before": True,
            "blend_clean_after": True, "data_block_inventory_unchanged": True,
            "operator_calls_by_this_extractor": 0,
            "edit_calls_by_this_extractor": 0,
            "persistence_calls_by_this_extractor": 0,
            "path_result_writes_by_this_extractor": 0,
        },
        "truth_boundary": config["truth_boundary"],
    }
    frame = receipt.encode_receipt_frame(payload)
    if receipt.decode_receipt_frame(frame).payload != payload:
        raise R25AfesAttempt05Error("private canonical receipt round-trip drifted")
    return payload, receipt, attempt03, ledger


def write_receipt_frame_to_inherited_pipe(
    payload: Mapping[str, Any], receipt: ModuleType, private_attempt03: ModuleType,
    raw_handle: int,
) -> None:
    handle = private_attempt03.require_win32_pipe_handle(raw_handle)
    frame = receipt.encode_receipt_frame(payload)
    if receipt.decode_receipt_frame(frame).payload != dict(payload):
        raise R25AfesAttempt05Error("receipt changed before pipe write")
    import msvcrt
    flags = os.O_WRONLY | getattr(os, "O_BINARY", 0)
    descriptor = msvcrt.open_osfhandle(handle, flags)
    with os.fdopen(descriptor, "wb", buffering=0, closefd=True) as stream:
        view = memoryview(frame)
        total = 0
        while total < len(view):
            written = stream.write(view[total:])
            if type(written) is not int or written <= 0:
                raise R25AfesAttempt05Error(
                    f"short pipe write after {total}/{len(view)} bytes"
                )
            total += written


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-handle", required=True)
    result = parser.parse_args(argv)
    try:
        result.result_handle = int(result.result_handle, 10)
    except ValueError as exc:
        parser.error(f"--result-handle must be decimal: {exc}")
    return result


def main() -> int:
    arguments = _arguments()
    try:
        payload, receipt, private_attempt03, _ledger = extract_payload()
        write_receipt_frame_to_inherited_pipe(
            payload, receipt, private_attempt03, arguments.result_handle
        )
    except Exception as exc:
        print(f"R25_AFES_ATTEMPT05_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
