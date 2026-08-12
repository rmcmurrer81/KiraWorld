#!/usr/bin/env python3
"""Read-only R25 AFES/transition-ring extractor for one exact foundation.

This script is prepared for a future, separately authorized Blender process.
It expects the exact foundation Blend to have been opened by Blender with
auto-execution disabled.  It performs no operator call, mutation, save,
render, export, or path-based result write.  A successful result is returned
as canonical JSON through a caller-provided inherited binary handle.

Preparing this source does not authorize its execution.
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

from tools.kira_r25_afes_topology_core import (  # noqa: E402
    AfesTopologyError,
    analyze_afes_topology,
    canonical_json_bytes,
    canonical_json_sha256,
)


CONFIG_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_read_only_extraction_v1.json"
)
CONFIG_BYTES = 6989
CONFIG_SHA256 = "3f1f57d95a28287f024cd6806af9180c623d134b68249a547cb81475f8fe5fdc"
AFES_PREFIX = "AFES_LANDMARK__"


class R25AfesExtractionError(RuntimeError):
    """Raised before emitting a result when any exact binding drifts."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_path(relative: str, *, suffix: str | None = None) -> Path:
    candidate = Path(str(relative))
    if not str(relative) or candidate.is_absolute() or ".." in candidate.parts:
        raise R25AfesExtractionError(f"unsafe project-relative path: {relative!r}")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise R25AfesExtractionError(f"symlink path refused: {relative!r}")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise R25AfesExtractionError(f"path escaped project root: {relative!r}") from exc
    if suffix is not None and resolved.suffix.lower() != suffix:
        raise R25AfesExtractionError(f"path must end in {suffix}: {relative!r}")
    if not resolved.is_file():
        raise R25AfesExtractionError(f"bound input is not a file: {relative!r}")
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise R25AfesExtractionError(f"invalid JSON input {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise R25AfesExtractionError(f"JSON root is not an object: {path.name}")
    return value


def _load_exact_config() -> tuple[dict[str, Any], Path]:
    path = _project_path(CONFIG_RELATIVE_PATH, suffix=".json")
    actual_bytes = path.stat().st_size
    actual_hash = _sha256_file(path)
    if actual_bytes != CONFIG_BYTES or actual_hash != CONFIG_SHA256:
        raise R25AfesExtractionError(
            "R25 extraction config drifted: "
            f"bytes={actual_bytes}, sha256={actual_hash}"
        )
    config = _read_json(path)
    if config.get("schema") != "kira.avatar.r25.foundation_afes_read_only_extraction.v1":
        raise R25AfesExtractionError("R25 extraction config schema drifted")
    if config.get("status") != "STATIC_PREPARATION_ONLY_EXECUTION_NOT_AUTHORIZED":
        raise R25AfesExtractionError("R25 extraction config status drifted")
    scope = config.get("scope")
    if not isinstance(scope, dict) or scope != {
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
        "result_transport": "caller_provided_inherited_binary_handle_only",
    }:
        raise R25AfesExtractionError("R25 read-only scope drifted")
    return config, path


def _verify_bindings(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    bindings = config.get("bindings")
    if not isinstance(bindings, Mapping) or not bindings:
        raise R25AfesExtractionError("bound input table is absent")
    records: dict[str, dict[str, Any]] = {}
    for label in sorted(bindings):
        row = bindings[label]
        if not isinstance(row, Mapping):
            raise R25AfesExtractionError(f"invalid bound input row: {label}")
        suffix = ".blend" if label == "foundation_blend" else ".json"
        path = _project_path(str(row.get("path") or ""), suffix=suffix)
        actual_bytes = path.stat().st_size
        actual_hash = _sha256_file(path)
        if actual_bytes != int(row.get("bytes", -1)) or actual_hash != str(
            row.get("sha256") or ""
        ).lower():
            raise R25AfesExtractionError(
                f"bound input drifted: {label}: bytes={actual_bytes}, sha256={actual_hash}"
            )
        records[label] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": actual_bytes,
            "sha256": actual_hash,
        }
    return records


def _validate_inherited_r23_contracts(
    config: Mapping[str, Any], bindings: Mapping[str, Mapping[str, Any]]
) -> None:
    contract = config["foundation_contract"]
    r23_config = _read_json(PROJECT_ROOT / bindings["r23_preflight_config"]["path"])
    r23_preflight = _read_json(PROJECT_ROOT / bindings["r23_preflight_attempt_04"]["path"])
    donor_contract = r23_config.get("donor_contract")
    donor_result = r23_preflight.get("qualified_cc0_donor")
    if not isinstance(donor_contract, Mapping) or not isinstance(donor_result, Mapping):
        raise R25AfesExtractionError("sealed R23 donor contracts are absent")
    foundation_binding = r23_config.get("inputs", {}).get("qualified_cc0_foundation_blend")
    if foundation_binding != config["bindings"]["foundation_blend"]:
        raise R25AfesExtractionError("R23 and R25 foundation bindings differ")
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
    for key, expected in expected_counts.items():
        if donor_contract.get(key) != expected:
            raise R25AfesExtractionError(f"sealed R23 donor count drifted: {key}")
    required_names = sorted(contract["required_groups"])
    if sorted(donor_contract.get("required_landmark_groups", [])) != required_names:
        raise R25AfesExtractionError("sealed R23 required AFES groups drifted")
    if donor_contract.get("object_name") != contract["object_name"]:
        raise R25AfesExtractionError("sealed R23 foundation object drifted")
    whole = donor_result.get("whole_mesh")
    if not isinstance(whole, Mapping) or {
        "vertices": whole.get("vertices"),
        "edges": whole.get("edges"),
        "faces": whole.get("faces"),
    } != {
        "vertices": contract["vertices"],
        "edges": contract["edges"],
        "faces": contract["faces"],
    }:
        raise R25AfesExtractionError("sealed R23 whole-mesh result drifted")
    if donor_result.get("groups") != contract["required_groups"]:
        raise R25AfesExtractionError("sealed R23 subgroup results drifted")
    union = donor_result.get("AFES_union")
    if not isinstance(union, Mapping):
        raise R25AfesExtractionError("sealed R23 AFES union result is absent")
    pairs = {
        "vertex_count": "vertex_count",
        "vertex_index_sha256": "vertex_index_sha256",
        "incident_face_count": "incident_face_count",
        "incident_face_index_sha256": "incident_face_index_sha256",
        "internal_face_count": "internal_face_count",
        "internal_face_index_sha256": "internal_face_index_sha256",
        "primary_connection_edge_count": "primary_connection_edge_count",
        "connection_edge_sha256": "connection_edge_sha256",
    }
    for expected_key, actual_key in pairs.items():
        if union.get(actual_key) != contract["afes_union"][expected_key]:
            raise R25AfesExtractionError(f"sealed R23 AFES union drifted: {actual_key}")


def _data_block_inventory() -> dict[str, object]:
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
    names = {label: sorted(str(item.name) for item in table) for label, table in tables.items()}
    return {
        "counts": {label: len(values) for label, values in names.items()},
        "names_sha256": canonical_json_sha256(names),
    }


def _object_bounds(obj: Any, indices: Sequence[int]) -> dict[str, list[float]]:
    if not indices:
        raise R25AfesExtractionError("cannot measure empty AFES union")
    return {
        "minimum": [
            min(float(obj.data.vertices[index].co[axis]) for index in indices)
            for axis in range(3)
        ],
        "maximum": [
            max(float(obj.data.vertices[index].co[axis]) for index in indices)
            for axis in range(3)
        ],
    }


def _validate_analysis(analysis: Mapping[str, Any], contract: Mapping[str, Any]) -> None:
    whole = analysis["whole_mesh"]
    for key, expected_key in (
        ("vertex_count", "vertices"),
        ("edge_count", "edges"),
        ("face_count", "faces"),
    ):
        if whole[key] != contract[expected_key]:
            raise R25AfesExtractionError(f"foundation topology count drifted: {key}")
    if analysis["groups"] != {
        name: {
            "vertex_count": row["vertex_count"],
            "vertex_indices": analysis["groups"][name]["vertex_indices"],
            "vertex_index_sha256": row["vertex_index_sha256"],
        }
        for name, row in contract["required_groups"].items()
    }:
        raise R25AfesExtractionError("AFES subgroup count or digest drifted")
    actual_union = analysis["afes_union"]
    expected_union = contract["afes_union"]
    for key in (
        "vertex_count",
        "vertex_index_sha256",
        "incident_face_count",
        "incident_face_index_sha256",
        "internal_face_count",
        "internal_face_index_sha256",
        "primary_connection_edge_count",
        "connection_edge_sha256",
    ):
        if actual_union[key] != expected_union[key]:
            raise R25AfesExtractionError(f"AFES union count or digest drifted: {key}")
    rings = analysis["transition_rings"]
    if rings["ring_count"] < 2 or not rings["disjoint_from_afes_union"]:
        raise R25AfesExtractionError("two disjoint AFES transition rings were not extracted")


def extract_payload() -> dict[str, Any]:
    """Return deterministic evidence from the already-open exact foundation."""

    config, config_path = _load_exact_config()
    bindings = _verify_bindings(config)
    _validate_inherited_r23_contracts(config, bindings)
    contract = config["foundation_contract"]
    exact_foundation = (PROJECT_ROOT / bindings["foundation_blend"]["path"]).resolve(
        strict=True
    )
    loaded_path = Path(str(bpy.data.filepath)).resolve(strict=True)
    if loaded_path != exact_foundation:
        raise R25AfesExtractionError(
            f"wrong Blend loaded: {loaded_path}; expected {exact_foundation}"
        )
    if bpy.data.is_dirty:
        raise R25AfesExtractionError("foundation Blend was already dirty before extraction")
    if str(bpy.context.mode) != "OBJECT":
        raise R25AfesExtractionError(f"Blender is not in OBJECT mode: {bpy.context.mode}")
    before = _data_block_inventory()
    obj = bpy.data.objects.get(str(contract["object_name"]))
    if obj is None or obj.type != "MESH":
        raise R25AfesExtractionError("exact foundation mesh object is absent")
    if str(obj.data.name) != str(contract["mesh_name"]):
        raise R25AfesExtractionError("exact foundation mesh datablock name drifted")
    if (
        len(obj.data.vertices) != int(contract["vertices"])
        or len(obj.data.edges) != int(contract["edges"])
        or len(obj.data.polygons) != int(contract["faces"])
    ):
        raise R25AfesExtractionError("exact foundation mesh counts drifted")
    required_names = sorted(str(name) for name in contract["required_groups"])
    actual_names = sorted(
        str(group.name) for group in obj.vertex_groups if group.name.startswith(AFES_PREFIX)
    )
    if actual_names != required_names:
        raise R25AfesExtractionError(
            f"exact AFES group set drifted: actual={actual_names}, expected={required_names}"
        )
    name_by_index = {int(group.index): str(group.name) for group in obj.vertex_groups}
    threshold = float(contract["membership_weight_threshold"])
    memberships: dict[str, list[int]] = {name: [] for name in required_names}
    for vertex in obj.data.vertices:
        for assignment in vertex.groups:
            name = name_by_index.get(int(assignment.group))
            if name in memberships and float(assignment.weight) > threshold:
                memberships[name].append(int(vertex.index))
    try:
        analysis = analyze_afes_topology(
            vertex_count=len(obj.data.vertices),
            edges=[tuple(int(index) for index in edge.vertices) for edge in obj.data.edges],
            faces=[tuple(int(index) for index in face.vertices) for face in obj.data.polygons],
            memberships=memberships,
            required_group_names=required_names,
            transition_ring_count=int(contract["required_transition_ring_count"]),
        )
    except AfesTopologyError as exc:
        raise R25AfesExtractionError(f"AFES topology extraction failed: {exc}") from exc
    _validate_analysis(analysis, contract)
    bounds = _object_bounds(obj, analysis["afes_union"]["vertex_indices"])
    expected_bounds = contract["afes_union"]["bounds_object_m"]
    tolerance = float(contract["afes_union"]["bounds_tolerance_m"])
    if any(
        abs(float(bounds[side][axis]) - float(expected_bounds[side][axis])) > tolerance
        for side in ("minimum", "maximum")
        for axis in range(3)
    ):
        raise R25AfesExtractionError(f"AFES union bounds drifted: {bounds}")
    after = _data_block_inventory()
    if after != before or bpy.data.is_dirty:
        raise R25AfesExtractionError("read-only extraction changed Blender data state")
    payload: dict[str, Any] = {
        "schema": "kira.avatar.r25.foundation_afes_transition_diagnostic.v1",
        "artifact_kind": "READ_ONLY_FOUNDATION_AFES_AND_TWO_RING_DIAGNOSTIC",
        "status": "EXTRACTED_NOT_AUTHORIZED_FOR_AUTHORING_OR_CANDIDATE_CREATION",
        "config": {
            "path": config_path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": CONFIG_BYTES,
            "sha256": CONFIG_SHA256,
        },
        "verified_inputs": bindings,
        "foundation_object": str(obj.name),
        "foundation_mesh": str(obj.data.name),
        "analysis": analysis,
        "afes_union_bounds_object_m": bounds,
        "read_only_guards": {
            "blend_loaded_exactly": True,
            "blend_clean_before": True,
            "blend_clean_after": True,
            "data_block_inventory_unchanged": True,
            "operator_calls_by_this_extractor": 0,
            "edit_calls_by_this_extractor": 0,
            "save_calls_by_this_extractor": 0,
            "path_result_writes_by_this_extractor": 0,
        },
        "truth_boundary": config["truth_boundary"],
    }
    payload["integrity"] = {
        "canonical_content_sha256": canonical_json_sha256(payload)
    }
    return payload


def write_payload_to_inherited_binary_handle(payload: Mapping[str, Any], raw_handle: int) -> None:
    """Write one canonical payload to a caller-owned inherited Win32 handle."""

    if os.name != "nt":
        raise R25AfesExtractionError("inherited raw-handle transport requires Windows")
    if type(raw_handle) is not int or raw_handle <= 0:
        raise R25AfesExtractionError("result handle must be a positive decimal integer")
    import msvcrt

    flags = os.O_WRONLY | getattr(os, "O_BINARY", 0)
    try:
        descriptor = msvcrt.open_osfhandle(raw_handle, flags)
    except OSError as exc:
        raise R25AfesExtractionError(f"could not adopt inherited result handle: {exc}") from exc
    data = canonical_json_bytes(payload)
    with os.fdopen(descriptor, "wb", buffering=0, closefd=True) as stream:
        view = memoryview(data)
        total = 0
        while total < len(view):
            written = stream.write(view[total:])
            if not isinstance(written, int) or written <= 0:
                raise R25AfesExtractionError(
                    f"short inherited-handle write after {total}/{len(data)} bytes"
                )
            total += written


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
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
        write_payload_to_inherited_binary_handle(payload, arguments.result_handle)
    except Exception as exc:
        print(f"R25_AFES_EXTRACTION_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
