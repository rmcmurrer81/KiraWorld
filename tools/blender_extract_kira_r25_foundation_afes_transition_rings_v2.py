#!/usr/bin/env python3
"""Attempt-02 read-only R25 AFES extractor (static preparation only).

The script is intended for a future separately authorized, fresh Blender
child.  It emits exactly one canonical framed receipt to a caller-inherited
Win32 pipe.  It has no path-result, authoring, operator, render, export, or
Blend-persistence capability.  Merely preparing this file does not authorize
running it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import kira_r25_afes_topology_core_v2 as topology_core  # noqa: E402
from tools import kira_r25_canonical_receipt as canonical_receipt  # noqa: E402


CONFIG_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_read_only_extraction_v2.json"
)
AFES_PREFIX = "AFES_LANDMARK__"


class R25AfesAttempt02Error(RuntimeError):
    """Raised before receipt emission when any exact condition is unproved."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_path(relative: object, *, suffix: str | None = None) -> Path:
    text = str(relative or "")
    candidate = Path(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts:
        raise R25AfesAttempt02Error(f"unsafe project-relative path: {text!r}")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise R25AfesAttempt02Error(f"symlink path refused: {text!r}")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise R25AfesAttempt02Error(f"path escaped project root: {text!r}") from exc
    if suffix is not None and resolved.suffix.lower() != suffix:
        raise R25AfesAttempt02Error(f"path suffix drifted: {text!r}")
    if not resolved.is_file():
        raise R25AfesAttempt02Error(f"bound input is not a file: {text!r}")
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise R25AfesAttempt02Error(f"invalid JSON input {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise R25AfesAttempt02Error(f"JSON root is not an object: {path.name}")
    return value


def _load_config() -> tuple[dict[str, Any], Path, dict[str, object]]:
    path = _project_path(CONFIG_RELATIVE_PATH, suffix=".json")
    config = _read_json(path)
    if config.get("schema") != "kira.avatar.r25.foundation_afes_read_only_extraction.v2":
        raise R25AfesAttempt02Error("Attempt-02 config schema drifted")
    if config.get("attempt_id") != "attempt_02" or config.get("status") != (
        "STATIC_PREPARATION_ONLY_EXECUTION_NOT_AUTHORIZED"
    ):
        raise R25AfesAttempt02Error("Attempt-02 config status drifted")
    expected_scope = {
        "read_only": True,
        "private": True,
        "inactive": True,
        "candidate_creation_allowed": False,
        "blend_edit_allowed": False,
        "blend_save_allowed": False,
        "render_allowed": False,
        "export_allowed": False,
        "runtime_activation_allowed": False,
        "path_output_allowed": False,
        "result_transport": (
            "one_canonical_receipt_frame_to_caller_inherited_win32_pipe_only"
        ),
    }
    if config.get("scope") != expected_scope:
        raise R25AfesAttempt02Error("Attempt-02 read-only scope drifted")
    return config, path, {
        "path": path.relative_to(PROJECT_ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
    }


def _verify_file_row(label: str, row: object) -> dict[str, object]:
    if not isinstance(row, Mapping) or set(row) != {"path", "bytes", "sha256"}:
        raise R25AfesAttempt02Error(f"invalid exact-file binding: {label}")
    path = _project_path(row["path"])
    size = path.stat().st_size
    digest = _sha256_file(path)
    if type(row["bytes"]) is not int or size != row["bytes"] or digest != row["sha256"]:
        raise R25AfesAttempt02Error(
            f"exact-file binding drifted: {label}: bytes={size}, sha256={digest}"
        )
    return {
        "path": path.relative_to(PROJECT_ROOT).as_posix(),
        "bytes": size,
        "sha256": digest,
    }


def _verify_bindings(config: Mapping[str, Any]) -> dict[str, dict[str, object]]:
    rows = config.get("bindings")
    required = {
        "foundation_blend",
        "r23_preflight_config",
        "r23_preflight_attempt_04",
        "foundation_qualification",
        "foundation_topology_audit",
        "foundation_relationship_audit",
        "canonical_receipt_helper",
        "attempt_02_topology_core",
        "attempt_02_extractor",
    }
    if not isinstance(rows, Mapping) or set(rows) != required:
        raise R25AfesAttempt02Error("Attempt-02 binding table drifted")
    verified = {
        label: _verify_file_row(label, rows[label]) for label in sorted(rows)
    }
    preservation = config.get("attempt_01_preservation")
    if not isinstance(preservation, Mapping) or set(preservation) != {
        "config", "topology_core", "extractor", "tests", "checkpoint"
    }:
        raise R25AfesAttempt02Error("Attempt-01 preservation table drifted")
    for label in sorted(preservation):
        _verify_file_row(f"attempt_01_preservation.{label}", preservation[label])

    module_checks = (
        ("canonical_receipt_helper", canonical_receipt.__file__),
        ("attempt_02_topology_core", topology_core.__file__),
        ("attempt_02_extractor", __file__),
    )
    for label, module_file in module_checks:
        if Path(str(module_file)).resolve(strict=True) != (
            PROJECT_ROOT / verified[label]["path"]
        ).resolve(strict=True):
            raise R25AfesAttempt02Error(f"imported module path drifted: {label}")
    return verified


def _validate_receipt_contract(config: Mapping[str, Any]) -> None:
    contract = config.get("receipt_contract")
    if not isinstance(contract, Mapping):
        raise R25AfesAttempt02Error("receipt contract is absent")
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
    if dict(contract) != expected:
        raise R25AfesAttempt02Error("receipt helper contract drifted")


def _validate_inherited_r23_contracts(
    config: Mapping[str, Any], bindings: Mapping[str, Mapping[str, object]]
) -> None:
    contract = config["foundation_contract"]
    r23_config = _read_json(PROJECT_ROOT / str(bindings["r23_preflight_config"]["path"]))
    r23_result = _read_json(
        PROJECT_ROOT / str(bindings["r23_preflight_attempt_04"]["path"])
    )
    donor = r23_config.get("donor_contract")
    result = r23_result.get("qualified_cc0_donor")
    if not isinstance(donor, Mapping) or not isinstance(result, Mapping):
        raise R25AfesAttempt02Error("sealed R23 donor evidence is absent")
    if r23_config.get("inputs", {}).get("qualified_cc0_foundation_blend") != config[
        "bindings"
    ]["foundation_blend"]:
        raise R25AfesAttempt02Error("R23 and R25 foundation bindings differ")
    expected_counts = {
        "expected_vertices": contract["vertices"],
        "expected_edges": contract["edges"],
        "expected_faces": contract["faces"],
        "expected_landmark_union_vertices": contract["afes_union"]["vertex_count"],
        "expected_landmark_incident_faces": contract["afes_union"][
            "incident_face_count"
        ],
        "expected_landmark_internal_faces": contract["afes_union"][
            "internal_face_count"
        ],
        "expected_primary_connection_edges": contract["afes_union"][
            "primary_connection_edge_count"
        ],
    }
    if any(donor.get(key) != value for key, value in expected_counts.items()):
        raise R25AfesAttempt02Error("sealed R23 donor counts drifted")
    if sorted(donor.get("required_landmark_groups", [])) != sorted(
        contract["required_groups"]
    ):
        raise R25AfesAttempt02Error("sealed R23 AFES group names drifted")
    if donor.get("object_name") != contract["object_name"]:
        raise R25AfesAttempt02Error("sealed R23 object name drifted")
    whole = result.get("whole_mesh")
    if not isinstance(whole, Mapping) or (
        whole.get("vertices"), whole.get("edges"), whole.get("faces")
    ) != (contract["vertices"], contract["edges"], contract["faces"]):
        raise R25AfesAttempt02Error("sealed R23 mesh counts drifted")
    if result.get("groups") != contract["required_groups"]:
        raise R25AfesAttempt02Error("sealed R23 AFES subgroup evidence drifted")
    union = result.get("AFES_union")
    if not isinstance(union, Mapping):
        raise R25AfesAttempt02Error("sealed R23 AFES union evidence is absent")
    for key in (
        "vertex_count", "vertex_index_sha256", "incident_face_count",
        "incident_face_index_sha256", "internal_face_count",
        "internal_face_index_sha256", "primary_connection_edge_count",
        "connection_edge_sha256",
    ):
        if union.get(key) != contract["afes_union"][key]:
            raise R25AfesAttempt02Error(f"sealed R23 AFES union drifted: {key}")


def _data_inventory() -> dict[str, object]:
    tables = {
        "objects": bpy.data.objects,
        "meshes": bpy.data.meshes,
        "materials": bpy.data.materials,
        "images": bpy.data.images,
        "armatures": bpy.data.armatures,
        "actions": bpy.data.actions,
        "collections": bpy.data.collections,
        "scenes": bpy.data.scenes,
    }
    names = {
        label: sorted(str(item.name) for item in table)
        for label, table in tables.items()
    }
    return {
        "counts": {label: len(values) for label, values in names.items()},
        "names_sha256": topology_core.canonical_json_sha256(names),
    }


def _quantized_union_bounds(obj: Any, indices: Sequence[int]) -> dict[str, object]:
    if not indices:
        raise R25AfesAttempt02Error("cannot measure an empty AFES union")
    meter_bounds = {
        "minimum": [
            min(obj.data.vertices[index].co[axis] for index in indices)
            for axis in range(3)
        ],
        "maximum": [
            max(obj.data.vertices[index].co[axis] for index in indices)
            for axis in range(3)
        ],
    }
    return topology_core.quantize_bounds_to_nanometers(meter_bounds)


def _validate_analysis(analysis: Mapping[str, Any], contract: Mapping[str, Any]) -> None:
    whole = analysis["whole_mesh"]
    if (whole["vertex_count"], whole["edge_count"], whole["face_count"]) != (
        contract["vertices"], contract["edges"], contract["faces"]
    ):
        raise R25AfesAttempt02Error("foundation topology counts drifted")
    for name, expected in contract["required_groups"].items():
        actual = analysis["groups"].get(name)
        if not isinstance(actual, Mapping) or (
            actual.get("vertex_count"), actual.get("vertex_index_sha256")
        ) != (expected["vertex_count"], expected["vertex_index_sha256"]):
            raise R25AfesAttempt02Error(f"AFES subgroup drifted: {name}")
    union = analysis["afes_union"]
    for key, expected in contract["afes_union"].items():
        if union.get(key) != expected:
            raise R25AfesAttempt02Error(f"AFES union drifted: {key}")
    rings = analysis["transition_rings"]
    if rings["ring_count"] != contract["required_transition_ring_count"] or not rings[
        "disjoint_from_afes_union"
    ]:
        raise R25AfesAttempt02Error("two disjoint transition rings were not extracted")
    structure = analysis["topology_structure"]
    if structure["full_normalized_topology_sha256"] != whole["topology_sha256"]:
        raise R25AfesAttempt02Error("normalized topology digest drifted internally")
    for key, expected in contract["required_topology_structure"].items():
        if structure.get(key) != expected:
            raise R25AfesAttempt02Error(f"foundation structural metric failed: {key}")


def extract_payload() -> dict[str, Any]:
    """Read and classify the already-open exact foundation without mutation."""

    config, config_path, config_binding = _load_config()
    verified = _verify_bindings(config)
    _validate_receipt_contract(config)
    _validate_inherited_r23_contracts(config, verified)
    contract = config["foundation_contract"]
    expected_foundation = (
        PROJECT_ROOT / str(verified["foundation_blend"]["path"])
    ).resolve(strict=True)
    loaded = Path(str(bpy.data.filepath)).resolve(strict=True)
    if loaded != expected_foundation:
        raise R25AfesAttempt02Error("the exact bound foundation Blend is not loaded")
    if bpy.data.is_dirty or str(bpy.context.mode) != "OBJECT":
        raise R25AfesAttempt02Error("foundation is dirty or Blender is not in OBJECT mode")
    before = _data_inventory()
    obj = bpy.data.objects.get(str(contract["object_name"]))
    if obj is None or obj.type != "MESH" or obj.data.name != contract["mesh_name"]:
        raise R25AfesAttempt02Error("exact foundation mesh object/datablock is absent")
    if (len(obj.data.vertices), len(obj.data.edges), len(obj.data.polygons)) != (
        contract["vertices"], contract["edges"], contract["faces"]
    ):
        raise R25AfesAttempt02Error("exact foundation mesh counts drifted")
    required_names = sorted(contract["required_groups"])
    actual_names = sorted(
        group.name for group in obj.vertex_groups if group.name.startswith(AFES_PREFIX)
    )
    if actual_names != required_names:
        raise R25AfesAttempt02Error("exact AFES vertex-group set drifted")
    name_by_index = {int(group.index): str(group.name) for group in obj.vertex_groups}
    memberships: dict[str, list[int]] = {name: [] for name in required_names}
    for vertex in obj.data.vertices:
        for assignment in vertex.groups:
            name = name_by_index.get(int(assignment.group))
            if name in memberships and float(assignment.weight) > 0:
                memberships[name].append(int(vertex.index))
    try:
        analysis = topology_core.analyze_afes_topology_v2(
            vertex_count=len(obj.data.vertices),
            edges=[tuple(int(value) for value in edge.vertices) for edge in obj.data.edges],
            faces=[tuple(int(value) for value in face.vertices) for face in obj.data.polygons],
            memberships=memberships,
            required_group_names=required_names,
            transition_ring_count=contract["required_transition_ring_count"],
        )
    except (topology_core.AfesTopologyError, topology_core.CompactAfesEvidenceError) as exc:
        raise R25AfesAttempt02Error(f"AFES topology extraction failed: {exc}") from exc
    _validate_analysis(analysis, contract)
    bounds = _quantized_union_bounds(obj, analysis["afes_union"]["vertex_indices"])
    expected_bounds = contract["expected_bounds_object_nanometers"]
    tolerance = config["coordinate_quantization"]["comparison_tolerance_nanometers"]
    if any(
        abs(bounds[side][axis] - expected_bounds[side][axis]) > tolerance
        for side in ("minimum", "maximum") for axis in range(3)
    ):
        raise R25AfesAttempt02Error(f"AFES integer bounds drifted: {bounds}")
    compact = topology_core.compact_afes_analysis(analysis, bounds)
    topology_core.validate_compact_afes_analysis(compact)
    after = _data_inventory()
    if after != before or bpy.data.is_dirty:
        raise R25AfesAttempt02Error("read-only extraction changed Blender state")
    payload: dict[str, Any] = {
        "schema": "kira.avatar.r25.foundation_afes_transition_diagnostic.v2",
        "artifact_kind": "READ_ONLY_FOUNDATION_AFES_AND_TWO_RING_DIAGNOSTIC",
        "status": "EXTRACTED_UNSEALED_REQUIRES_MATCHING_FRESH_LOCKED_RUN",
        "config_observed_unsealed_by_parent": config_binding,
        "verified_inputs": verified,
        "foundation_object": str(obj.name),
        "foundation_mesh": str(obj.data.name),
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
            "blend_loaded_exactly": True,
            "blend_clean_before": True,
            "blend_clean_after": True,
            "data_block_inventory_unchanged": True,
            "operator_calls_by_this_extractor": 0,
            "edit_calls_by_this_extractor": 0,
            "persistence_calls_by_this_extractor": 0,
            "path_result_writes_by_this_extractor": 0,
        },
        "truth_boundary": config["truth_boundary"],
    }
    frame = canonical_receipt.encode_receipt_frame(payload)
    decoded = canonical_receipt.decode_receipt_frame(frame)
    if decoded.payload != payload:
        raise R25AfesAttempt02Error("canonical receipt round-trip drifted")
    return payload


def write_receipt_frame_to_inherited_pipe(payload: Mapping[str, Any], raw_handle: int) -> None:
    """Encode and write one frame, only after GetFileType proves a pipe."""

    handle = topology_core.require_win32_pipe_handle(raw_handle)
    frame = canonical_receipt.encode_receipt_frame(payload)
    decoded = canonical_receipt.decode_receipt_frame(frame)
    if decoded.payload != dict(payload):
        raise R25AfesAttempt02Error("receipt changed before pipe write")
    import msvcrt

    flags = os.O_WRONLY | getattr(os, "O_BINARY", 0)
    try:
        descriptor = msvcrt.open_osfhandle(handle, flags)
    except OSError as exc:
        raise R25AfesAttempt02Error(f"could not adopt inherited pipe: {exc}") from exc
    with os.fdopen(descriptor, "wb", buffering=0, closefd=True) as stream:
        view = memoryview(frame)
        written_total = 0
        while written_total < len(view):
            written = stream.write(view[written_total:])
            if type(written) is not int or written <= 0:
                raise R25AfesAttempt02Error(
                    f"short pipe write after {written_total}/{len(view)} bytes"
                )
            written_total += written


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
        print(f"R25_AFES_ATTEMPT02_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
