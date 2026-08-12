#!/usr/bin/env python3
"""Attempt-03 read-only R25 AFES extractor; execution is not authorized.

This future Blender child verifies every imported execution module, including
the immutable Attempt-01 topology core, against an exact file binding before
any topology analysis.  It can emit only one canonical receipt frame to an
inherited Win32 pipe and has no path-result or body-authoring capability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Mapping, Sequence

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import kira_r25_afes_topology_core as attempt01_core  # noqa: E402
from tools import kira_r25_afes_topology_core_v2 as attempt02_core  # noqa: E402
from tools import kira_r25_afes_topology_core_v3 as topology_core  # noqa: E402
from tools import kira_r25_canonical_receipt as canonical_receipt  # noqa: E402


CONFIG_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_read_only_extraction_v3.json"
)
AFES_PREFIX = "AFES_LANDMARK__"


class R25AfesAttempt03Error(RuntimeError):
    """Raised before analysis/receipt emission when any binding is unproved."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_path(relative: object) -> Path:
    text = str(relative or "")
    candidate = Path(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts:
        raise R25AfesAttempt03Error(f"unsafe project-relative path: {text!r}")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise R25AfesAttempt03Error(f"symlink path refused: {text!r}")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise R25AfesAttempt03Error(f"path escaped project root: {text!r}") from exc
    if not resolved.is_file():
        raise R25AfesAttempt03Error(f"bound input is not a file: {text!r}")
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise R25AfesAttempt03Error(f"invalid JSON input {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise R25AfesAttempt03Error(f"JSON root is not an object: {path.name}")
    return value


def _verify_file_row(label: str, row: object) -> dict[str, object]:
    if not isinstance(row, Mapping) or set(row) != {"path", "bytes", "sha256"}:
        raise R25AfesAttempt03Error(f"invalid exact-file binding: {label}")
    path = _project_path(row["path"])
    size = path.stat().st_size
    digest = _sha256_file(path)
    if type(row["bytes"]) is not int or size != row["bytes"] or digest != row["sha256"]:
        raise R25AfesAttempt03Error(
            f"exact-file binding drifted: {label}: bytes={size}, sha256={digest}"
        )
    return {"path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": size, "sha256": digest}


def _verify_table(label: str, rows: object) -> dict[str, dict[str, object]]:
    if not isinstance(rows, Mapping) or not rows:
        raise R25AfesAttempt03Error(f"exact-file table is absent: {label}")
    return {
        str(name): _verify_file_row(f"{label}.{name}", row)
        for name, row in sorted(rows.items())
    }


def _load_config_chain() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, object],
    dict[str, dict[str, object]], dict[str, dict[str, object]]
]:
    config_path = _project_path(CONFIG_RELATIVE_PATH)
    config = _read_json(config_path)
    if config.get("schema") != "kira.avatar.r25.foundation_afes_read_only_extraction.v3":
        raise R25AfesAttempt03Error("Attempt-03 config schema drifted")
    if config.get("attempt_id") != "attempt_03" or config.get("status") != (
        "STATIC_PREPARATION_ONLY_EXECUTION_NOT_AUTHORIZED"
    ):
        raise R25AfesAttempt03Error("Attempt-03 config status drifted")
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
        raise R25AfesAttempt03Error("Attempt-03 scope drifted")
    baseline_row = config.get("attempt_02_baseline_config")
    baseline_binding = _verify_file_row("attempt_02_baseline_config", baseline_row)
    baseline = _read_json(PROJECT_ROOT / str(baseline_binding["path"]))
    if baseline.get("schema") != "kira.avatar.r25.foundation_afes_read_only_extraction.v2":
        raise R25AfesAttempt03Error("exact Attempt-02 baseline schema drifted")
    baseline_verified = _verify_table("attempt_02_baseline.bindings", baseline["bindings"])
    _verify_table("attempt_02_baseline.attempt_01_preservation",
                  baseline["attempt_01_preservation"])
    execution_verified = _verify_table("bindings", config.get("bindings"))
    _verify_table("attempt_01_preservation", config.get("attempt_01_preservation"))
    _verify_table("attempt_02_preservation", config.get("attempt_02_preservation"))
    config_binding = {
        "path": config_path.relative_to(PROJECT_ROOT).as_posix(),
        "bytes": config_path.stat().st_size,
        "sha256": _sha256_file(config_path),
    }
    return config, baseline, config_binding, execution_verified, baseline_verified


def _require_module(
    module: object,
    *,
    binding: Mapping[str, object],
    expected_name: str,
    required_symbols: Sequence[str],
) -> ModuleType:
    """Locally verify a module before trusting any checker from that module."""

    if not isinstance(module, ModuleType) or module.__name__ != expected_name:
        raise R25AfesAttempt03Error("imported execution dependency identity drifted")
    raw_file = getattr(module, "__file__", None)
    spec = getattr(module, "__spec__", None)
    loader = getattr(spec, "loader", None)
    origin = getattr(spec, "origin", None)
    if not isinstance(raw_file, str) or not isinstance(origin, str) or loader is None:
        raise R25AfesAttempt03Error(
            f"imported execution dependency is not file-backed: {expected_name}"
        )
    expected_path = (PROJECT_ROOT / str(binding["path"])).resolve(strict=True)
    if Path(raw_file).resolve(strict=True) != expected_path:
        raise R25AfesAttempt03Error(
            f"imported execution dependency __file__ drifted: {expected_name}"
        )
    if Path(origin).resolve(strict=True) != expected_path:
        raise R25AfesAttempt03Error(
            f"imported execution dependency origin drifted: {expected_name}"
        )
    get_filename = getattr(loader, "get_filename", None)
    if not callable(get_filename) or Path(str(get_filename(expected_name))).resolve(
        strict=True
    ) != expected_path:
        raise R25AfesAttempt03Error(
            f"imported execution dependency loader drifted: {expected_name}"
        )
    if expected_path.stat().st_size != binding["bytes"] or _sha256_file(
        expected_path
    ) != binding["sha256"]:
        raise R25AfesAttempt03Error(
            f"imported execution dependency file drifted: {expected_name}"
        )
    for symbol_name in required_symbols:
        symbol = getattr(module, symbol_name, None)
        if not callable(symbol) or getattr(symbol, "__module__", None) != expected_name:
            raise R25AfesAttempt03Error(
                f"imported execution symbol drifted: {expected_name}.{symbol_name}"
            )
    return module


def _verify_execution_modules(bindings: Mapping[str, Mapping[str, object]]) -> None:
    # Verify v3 core locally before invoking its independent strong checker.
    _require_module(
        topology_core,
        binding=bindings["attempt_03_topology_core"],
        expected_name="tools.kira_r25_afes_topology_core_v3",
        required_symbols=("analyze_afes_topology_v3", "compact_afes_analysis",
                          "validate_compact_afes_analysis",
                          "require_exact_imported_python_module"),
    )
    checks = (
        (attempt01_core, "attempt_01_topology_core_execution_dependency",
         "tools.kira_r25_afes_topology_core",
         ("AfesTopologyError", "analyze_afes_topology", "canonical_index_sha256",
          "canonical_json_sha256", "normalize_edges", "normalize_faces")),
        (attempt02_core, "attempt_02_hardening_core_execution_dependency",
         "tools.kira_r25_afes_topology_core_v2",
         ("compact_afes_analysis", "validate_compact_afes_analysis",
          "analyze_foundation_topology_structure", "require_win32_pipe_handle")),
        (canonical_receipt, "canonical_receipt_helper",
         "tools.kira_r25_canonical_receipt",
         ("encode_receipt_frame", "decode_receipt_frame", "canonical_json_bytes")),
    )
    for module, label, name, symbols in checks:
        _require_module(module, binding=bindings[label], expected_name=name,
                        required_symbols=symbols)
        topology_core.require_exact_imported_python_module(
            module, expected_module_name=name,
            expected_path=PROJECT_ROOT / str(bindings[label]["path"]),
            expected_bytes=int(bindings[label]["bytes"]),
            expected_sha256=str(bindings[label]["sha256"]),
            required_symbols=symbols,
        )
    if topology_core.attempt01_core is not attempt01_core:
        raise R25AfesAttempt03Error("v3 core does not hold the verified Attempt-01 module")
    if topology_core.attempt02_core is not attempt02_core:
        raise R25AfesAttempt03Error("v3 core does not hold the verified Attempt-02 module")
    self_path = Path(__file__).resolve(strict=True)
    expected_self = (
        PROJECT_ROOT / str(bindings["attempt_03_extractor"]["path"])
    ).resolve(strict=True)
    if self_path != expected_self:
        raise R25AfesAttempt03Error("Attempt-03 extractor source path drifted")


def _validate_receipt_contract(baseline: Mapping[str, Any]) -> None:
    expected = {
        "magic_ascii": canonical_receipt.RECEIPT_MAGIC.decode("ascii"),
        "version": canonical_receipt.RECEIPT_VERSION,
        "maximum_payload_bytes": canonical_receipt.MAX_RECEIPT_PAYLOAD_BYTES,
        "maximum_depth": canonical_receipt.MAX_RECEIPT_DEPTH,
        "maximum_nodes": canonical_receipt.MAX_RECEIPT_NODES,
        "floats_allowed": False,
        "integer_minimum": canonical_receipt.MIN_RECEIPT_INTEGER,
        "integer_maximum": canonical_receipt.MAX_RECEIPT_INTEGER,
        "child_must_call": "tools.kira_r25_canonical_receipt.encode_receipt_frame",
    }
    if baseline.get("receipt_contract") != expected:
        raise R25AfesAttempt03Error("inherited receipt contract drifted")


def _validate_r23(
    baseline: Mapping[str, Any], verified: Mapping[str, Mapping[str, object]]
) -> None:
    contract = baseline["foundation_contract"]
    r23_config = _read_json(PROJECT_ROOT / str(verified["r23_preflight_config"]["path"]))
    r23_result = _read_json(
        PROJECT_ROOT / str(verified["r23_preflight_attempt_04"]["path"])
    )
    donor = r23_config.get("donor_contract")
    result = r23_result.get("qualified_cc0_donor")
    if not isinstance(donor, Mapping) or not isinstance(result, Mapping):
        raise R25AfesAttempt03Error("sealed R23 donor evidence is absent")
    if r23_config.get("inputs", {}).get("qualified_cc0_foundation_blend") != baseline[
        "bindings"
    ]["foundation_blend"]:
        raise R25AfesAttempt03Error("R23/foundation bindings differ")
    expected_counts = {
        "expected_vertices": contract["vertices"],
        "expected_edges": contract["edges"],
        "expected_faces": contract["faces"],
        "expected_landmark_union_vertices": contract["afes_union"]["vertex_count"],
        "expected_landmark_incident_faces": contract["afes_union"]["incident_face_count"],
        "expected_landmark_internal_faces": contract["afes_union"]["internal_face_count"],
        "expected_primary_connection_edges": contract["afes_union"][
            "primary_connection_edge_count"
        ],
    }
    if any(donor.get(key) != value for key, value in expected_counts.items()):
        raise R25AfesAttempt03Error("sealed R23 donor counts drifted")
    if sorted(donor.get("required_landmark_groups", [])) != sorted(
        contract["required_groups"]
    ) or donor.get("object_name") != contract["object_name"]:
        raise R25AfesAttempt03Error("sealed R23 group/object contract drifted")
    whole = result.get("whole_mesh")
    if not isinstance(whole, Mapping) or (
        whole.get("vertices"), whole.get("edges"), whole.get("faces")
    ) != (contract["vertices"], contract["edges"], contract["faces"]):
        raise R25AfesAttempt03Error("sealed R23 mesh counts drifted")
    if result.get("groups") != contract["required_groups"]:
        raise R25AfesAttempt03Error("sealed R23 AFES groups drifted")
    union = result.get("AFES_union")
    if not isinstance(union, Mapping):
        raise R25AfesAttempt03Error("sealed R23 AFES union is absent")
    for key, expected in contract["afes_union"].items():
        if union.get(key) != expected:
            raise R25AfesAttempt03Error(f"sealed R23 AFES union drifted: {key}")


def _inventory() -> dict[str, object]:
    tables = {"objects": bpy.data.objects, "meshes": bpy.data.meshes,
              "materials": bpy.data.materials, "images": bpy.data.images,
              "armatures": bpy.data.armatures, "actions": bpy.data.actions,
              "collections": bpy.data.collections, "scenes": bpy.data.scenes}
    names = {label: sorted(str(item.name) for item in table)
             for label, table in tables.items()}
    return {"counts": {label: len(values) for label, values in names.items()},
            "names_sha256": topology_core.canonical_json_sha256(names)}


def _bounds(obj: Any, indices: Sequence[int]) -> dict[str, object]:
    if not indices:
        raise R25AfesAttempt03Error("cannot measure an empty AFES union")
    return topology_core.quantize_bounds_to_nanometers({
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
        raise R25AfesAttempt03Error("foundation topology counts drifted")
    for name, expected in contract["required_groups"].items():
        actual = analysis["groups"].get(name)
        if not isinstance(actual, Mapping) or (
            actual.get("vertex_count"), actual.get("vertex_index_sha256")
        ) != (expected["vertex_count"], expected["vertex_index_sha256"]):
            raise R25AfesAttempt03Error(f"AFES subgroup drifted: {name}")
    for key, expected in contract["afes_union"].items():
        if analysis["afes_union"].get(key) != expected:
            raise R25AfesAttempt03Error(f"AFES union drifted: {key}")
    rings = analysis["transition_rings"]
    if rings["ring_count"] != contract["required_transition_ring_count"] or not rings[
        "disjoint_from_afes_union"
    ]:
        raise R25AfesAttempt03Error("two disjoint transition rings were not extracted")
    structure = analysis["topology_structure"]
    if structure["full_normalized_topology_sha256"] != whole["topology_sha256"]:
        raise R25AfesAttempt03Error("normalized topology digest drifted")
    for key, expected in contract["required_topology_structure"].items():
        if structure.get(key) != expected:
            raise R25AfesAttempt03Error(f"foundation structural metric failed: {key}")


def extract_payload() -> dict[str, Any]:
    config, baseline, config_binding, execution, inherited = _load_config_chain()
    _verify_execution_modules(execution)  # Must precede every analysis call.
    _validate_receipt_contract(baseline)
    _validate_r23(baseline, inherited)
    contract = baseline["foundation_contract"]
    expected_blend = (PROJECT_ROOT / str(inherited["foundation_blend"]["path"])).resolve(
        strict=True
    )
    if Path(str(bpy.data.filepath)).resolve(strict=True) != expected_blend:
        raise R25AfesAttempt03Error("the exact bound foundation Blend is not loaded")
    if bpy.data.is_dirty or str(bpy.context.mode) != "OBJECT":
        raise R25AfesAttempt03Error("foundation is dirty or Blender is not in OBJECT mode")
    before = _inventory()
    obj = bpy.data.objects.get(str(contract["object_name"]))
    if obj is None or obj.type != "MESH" or obj.data.name != contract["mesh_name"]:
        raise R25AfesAttempt03Error("exact foundation object/datablock is absent")
    if (len(obj.data.vertices), len(obj.data.edges), len(obj.data.polygons)) != (
        contract["vertices"], contract["edges"], contract["faces"]
    ):
        raise R25AfesAttempt03Error("exact foundation counts drifted")
    required_names = sorted(contract["required_groups"])
    actual_names = sorted(g.name for g in obj.vertex_groups if g.name.startswith(AFES_PREFIX))
    if actual_names != required_names:
        raise R25AfesAttempt03Error("exact AFES vertex-group set drifted")
    name_by_index = {int(group.index): str(group.name) for group in obj.vertex_groups}
    memberships: dict[str, list[int]] = {name: [] for name in required_names}
    for vertex in obj.data.vertices:
        for assignment in vertex.groups:
            name = name_by_index.get(int(assignment.group))
            if name in memberships and float(assignment.weight) > 0:
                memberships[name].append(int(vertex.index))
    try:
        analysis = topology_core.analyze_afes_topology_v3(
            vertex_count=len(obj.data.vertices),
            edges=[tuple(int(v) for v in edge.vertices) for edge in obj.data.edges],
            faces=[tuple(int(v) for v in face.vertices) for face in obj.data.polygons],
            memberships=memberships, required_group_names=required_names,
            transition_ring_count=contract["required_transition_ring_count"],
        )
    except (attempt01_core.AfesTopologyError,
            topology_core.CompactAfesEvidenceError) as exc:
        raise R25AfesAttempt03Error(f"AFES topology extraction failed: {exc}") from exc
    _validate_analysis(analysis, contract)
    bounds = _bounds(obj, analysis["afes_union"]["vertex_indices"])
    expected_bounds = contract["expected_bounds_object_nanometers"]
    tolerance = baseline["coordinate_quantization"]["comparison_tolerance_nanometers"]
    if any(abs(bounds[side][axis] - expected_bounds[side][axis]) > tolerance
           for side in ("minimum", "maximum") for axis in range(3)):
        raise R25AfesAttempt03Error(f"AFES integer bounds drifted: {bounds}")
    compact = topology_core.compact_afes_analysis(analysis, bounds)
    topology_core.validate_compact_afes_analysis(compact)
    after = _inventory()
    if after != before or bpy.data.is_dirty:
        raise R25AfesAttempt03Error("read-only extraction changed Blender state")
    payload: dict[str, Any] = {
        "schema": "kira.avatar.r25.foundation_afes_transition_diagnostic.v3",
        "artifact_kind": "READ_ONLY_FOUNDATION_AFES_AND_TWO_RING_DIAGNOSTIC",
        "status": "EXTRACTED_UNSEALED_REQUIRES_MATCHING_FRESH_LOCKED_RUN",
        "config_observed_unsealed_by_parent": config_binding,
        "attempt_02_baseline": config["attempt_02_baseline_config"],
        "verified_execution_dependencies": execution,
        "verified_inherited_inputs": inherited,
        "execution_module_guards": {
            "attempt_01_core_exact_file_module": True,
            "attempt_02_hardening_core_exact_file_module": True,
            "attempt_03_core_exact_file_module": True,
            "canonical_receipt_exact_file_module": True,
            "all_verified_before_analysis": True,
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
    frame = canonical_receipt.encode_receipt_frame(payload)
    if canonical_receipt.decode_receipt_frame(frame).payload != payload:
        raise R25AfesAttempt03Error("canonical receipt round-trip drifted")
    return payload


def write_receipt_frame_to_inherited_pipe(payload: Mapping[str, Any], raw_handle: int) -> None:
    handle = topology_core.require_win32_pipe_handle(raw_handle)
    frame = canonical_receipt.encode_receipt_frame(payload)
    if canonical_receipt.decode_receipt_frame(frame).payload != dict(payload):
        raise R25AfesAttempt03Error("receipt changed before pipe write")
    import msvcrt
    flags = os.O_WRONLY | getattr(os, "O_BINARY", 0)
    try:
        descriptor = msvcrt.open_osfhandle(handle, flags)
    except OSError as exc:
        raise R25AfesAttempt03Error(f"could not adopt inherited pipe: {exc}") from exc
    with os.fdopen(descriptor, "wb", buffering=0, closefd=True) as stream:
        view = memoryview(frame)
        total = 0
        while total < len(view):
            written = stream.write(view[total:])
            if type(written) is not int or written <= 0:
                raise R25AfesAttempt03Error(
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
        payload = extract_payload()
        write_receipt_frame_to_inherited_pipe(payload, arguments.result_handle)
    except Exception as exc:
        print(f"R25_AFES_ATTEMPT03_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
