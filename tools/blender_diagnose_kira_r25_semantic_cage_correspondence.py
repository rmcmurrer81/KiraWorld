#!/usr/bin/env python3
"""Inert read-only Blender wrapper for the R25 semantic-cage diagnostic.

This file is preparation only.  It must run, if separately authorized, in a
factory-started disposable Blender process.  It links exact source datablocks
for inspection, never saves or deforms them, receives the exact AFES-plus-ring
lock as one existing R25 canonical receipt frame over an inherited handle, and
returns one canonical receipt frame over another inherited handle.  It accepts
no input or output pathname arguments.
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

from tools import kira_r25_canonical_receipt as canonical_receipt  # noqa: E402
from tools.kira_r25_semantic_cage_correspondence_core import (  # noqa: E402
    REGIONS,
    SemanticCageError,
    Triangle,
    build_correspondence_receipt,
    canonical_sha256,
    classify_weighted_vertices,
    validate_lock_input,
)


CONFIG_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_semantic_cage_correspondence_diagnostic_v1.json"
)
CONFIG_BYTES = 8016
CONFIG_SHA256 = "b0d4cfd289cd9063547a17575f77f251b5566c683b9e421ee5529bc8c5a7c74c"


class R25SemanticCageDiagnosticError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_file(relative: str, expected_suffix: str) -> Path:
    candidate = Path(relative)
    if not relative or candidate.is_absolute() or ".." in candidate.parts:
        raise R25SemanticCageDiagnosticError("unsafe_project_relative_binding")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise R25SemanticCageDiagnosticError("symlink_binding_refused")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise R25SemanticCageDiagnosticError("binding_escaped_project_root") from exc
    if resolved.suffix.lower() != expected_suffix or not resolved.is_file():
        raise R25SemanticCageDiagnosticError("binding_type_mismatch")
    return resolved


def _read_config() -> tuple[dict[str, Any], Path]:
    path = _project_file(CONFIG_RELATIVE_PATH, ".json")
    if path.stat().st_size != CONFIG_BYTES or _sha256_file(path) != CONFIG_SHA256:
        raise R25SemanticCageDiagnosticError("semantic_cage_config_drift")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise R25SemanticCageDiagnosticError("semantic_cage_config_invalid_json") from exc
    if not isinstance(config, dict) or config.get("schema") != (
        "kira.avatar.r25.semantic_cage_correspondence_diagnostic.v1"
    ):
        raise R25SemanticCageDiagnosticError("semantic_cage_config_schema_drift")
    if config.get("status") != (
        "STATIC_PREPARATION_ONLY_READ_ONLY_BLENDER_DIAGNOSTIC_NOT_AUTHORIZED"
    ):
        raise R25SemanticCageDiagnosticError("semantic_cage_config_status_drift")
    return config, path


def _verify_bindings(config: Mapping[str, Any]) -> dict[str, dict[str, object]]:
    bindings = config.get("bindings")
    if not isinstance(bindings, Mapping):
        raise R25SemanticCageDiagnosticError("binding_table_missing")
    verified: dict[str, dict[str, object]] = {}
    for label in sorted(bindings):
        row = bindings[label]
        if not isinstance(row, Mapping):
            raise R25SemanticCageDiagnosticError(f"binding_row_invalid:{label}")
        relative = str(row.get("path") or "")
        suffix = Path(relative).suffix.lower()
        if suffix not in (".blend", ".json", ".md", ".mhw", ".py"):
            raise R25SemanticCageDiagnosticError(f"binding_suffix_refused:{label}")
        path = _project_file(relative, suffix)
        size, digest = path.stat().st_size, _sha256_file(path)
        if size != int(row.get("bytes", -1)) or digest != str(row.get("sha256", "")):
            raise R25SemanticCageDiagnosticError(f"binding_drift:{label}")
        verified[label] = {"bytes": size, "sha256": digest}
    receipt_row = bindings["canonical_receipt_primitive"]
    if (
        receipt_row.get("maximum_payload_bytes") != canonical_receipt.MAX_RECEIPT_PAYLOAD_BYTES
        or receipt_row.get("maximum_depth") != canonical_receipt.MAX_RECEIPT_DEPTH
        or receipt_row.get("maximum_nodes") != canonical_receipt.MAX_RECEIPT_NODES
    ):
        raise R25SemanticCageDiagnosticError("canonical_receipt_limits_drift")
    return verified


def _adopt_handle(raw_handle: int, flags: int):
    if os.name != "nt" or type(raw_handle) is not int or raw_handle <= 0:
        raise R25SemanticCageDiagnosticError("inherited_handle_invalid_or_non_windows")
    import msvcrt

    try:
        descriptor = msvcrt.open_osfhandle(raw_handle, flags | getattr(os, "O_BINARY", 0))
    except OSError as exc:
        raise R25SemanticCageDiagnosticError("inherited_handle_adoption_failed") from exc
    return os.fdopen(descriptor, "rb" if flags == os.O_RDONLY else "wb", buffering=0, closefd=True)


def _read_lock_frame(raw_handle: int) -> tuple[dict[str, Any], str]:
    with _adopt_handle(raw_handle, os.O_RDONLY) as stream:
        data = stream.read(canonical_receipt.MAX_RECEIPT_FRAME_BYTES + 1)
    if len(data) > canonical_receipt.MAX_RECEIPT_FRAME_BYTES:
        raise R25SemanticCageDiagnosticError("lock_frame_too_large")
    try:
        decoded = canonical_receipt.decode_receipt_frame(data)
    except canonical_receipt.ReceiptFrameError as exc:
        raise R25SemanticCageDiagnosticError(f"lock_frame_rejected:{exc.code}") from exc
    return decoded.payload, decoded.frame_sha256


def _write_result_frame(raw_handle: int, payload: Mapping[str, Any]) -> None:
    frame = canonical_receipt.encode_receipt_frame(payload)
    if canonical_receipt.decode_receipt_frame(frame).payload != dict(payload):
        raise R25SemanticCageDiagnosticError("result_frame_roundtrip_failed")
    with _adopt_handle(raw_handle, os.O_WRONLY) as stream:
        view, total = memoryview(frame), 0
        while total < len(view):
            written = stream.write(view[total:])
            if not isinstance(written, int) or written <= 0:
                raise R25SemanticCageDiagnosticError("short_result_handle_write")
            total += written


def _linked_object(blend_path: Path, object_name: str, mesh_name: str) -> Any:
    with bpy.data.libraries.load(str(blend_path), link=True) as (available, requested):
        if object_name not in available.objects:
            raise R25SemanticCageDiagnosticError(f"bound_object_missing:{object_name}")
        requested.objects = [object_name]
    obj = requested.objects[0]
    if obj is None or obj.type != "MESH" or obj.data.name != mesh_name:
        raise R25SemanticCageDiagnosticError(f"bound_object_or_mesh_drift:{object_name}")
    return obj


def _world_geometry(obj: Any) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]]]:
    matrix = obj.matrix_world
    normal_matrix = matrix.to_3x3().inverted_safe().transposed()
    vertices = [tuple(float(value) for value in (matrix @ vertex.co)) for vertex in obj.data.vertices]
    normals = [tuple(float(value) for value in (normal_matrix @ vertex.normal)) for vertex in obj.data.vertices]
    return vertices, normals


def _weight_rows(obj: Any) -> list[list[tuple[str, float]]]:
    names = {int(group.index): str(group.name) for group in obj.vertex_groups}
    if not names:
        raise R25SemanticCageDiagnosticError("vertex_group_semantics_missing")
    result: list[list[tuple[str, float]]] = []
    for vertex in obj.data.vertices:
        row = [
            (names[int(item.group)], float(item.weight))
            for item in vertex.groups
            if int(item.group) in names and float(item.weight) > 0.0
        ]
        result.append(sorted(row))
    return result


def _faces(obj: Any) -> list[list[int]]:
    return [[int(value) for value in polygon.vertices] for polygon in obj.data.polygons]


def _target_triangles(obj: Any) -> list[Triangle]:
    triangles: list[Triangle] = []
    for polygon in obj.data.polygons:
        vertices = [int(value) for value in polygon.vertices]
        if len(vertices) < 3:
            raise R25SemanticCageDiagnosticError("r19_face_has_fewer_than_three_vertices")
        for triangle_index in range(len(vertices) - 2):
            triangles.append(
                Triangle(
                    int(polygon.index),
                    triangle_index,
                    (vertices[0], vertices[triangle_index + 1], vertices[triangle_index + 2]),
                )
            )
    return triangles


def _r20_excluded_faces(obj: Any, contract: Mapping[str, Any]) -> set[int]:
    selected = {
        int(polygon.index) for polygon in obj.data.polygons if int(polygon.material_index) == 1
    }
    if len(selected) != int(contract["selected_faces"]):
        raise R25SemanticCageDiagnosticError("r20_selected_face_count_drift")
    face_vertices = {int(polygon.index): [int(v) for v in polygon.vertices] for polygon in obj.data.polygons}
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for face_index, vertices in face_vertices.items():
        for position, first in enumerate(vertices):
            second = vertices[(position + 1) % len(vertices)]
            edge = (min(first, second), max(first, second))
            edge_faces.setdefault(edge, []).append(face_index)
    adjacency = {index: set() for index in selected}
    interface_edges: list[tuple[int, int]] = []
    for edge, incident in edge_faces.items():
        inside = [index for index in incident if index in selected]
        if len(inside) >= 2:
            for first in inside:
                adjacency[first].update(index for index in inside if index != first)
        if len(incident) == 2 and len(inside) == 1:
            interface_edges.append(edge)
    pending, components = set(selected), 0
    while pending:
        components += 1
        stack = [min(pending)]
        pending.remove(stack[0])
        while stack:
            current = stack.pop()
            for neighbor in sorted(adjacency[current]):
                if neighbor in pending:
                    pending.remove(neighbor)
                    stack.append(neighbor)
    incident_vertices = {vertex for index in selected for vertex in face_vertices[index]}
    interface_vertices = {vertex for edge in interface_edges for vertex in edge}
    expected = {
        "incident_vertices": len(incident_vertices),
        "face_connected_components": components,
        "interface_edges": len(interface_edges),
        "interface_vertices": len(interface_vertices),
    }
    for label, actual in expected.items():
        if int(contract[label]) != actual:
            raise R25SemanticCageDiagnosticError(f"r20_{label}_drift")
    return selected


def _require_factory_read_only_state() -> None:
    if bpy.data.filepath or bpy.data.is_dirty or bpy.context.mode != "OBJECT":
        raise R25SemanticCageDiagnosticError("factory_clean_object_mode_required")
    if bpy.context.scene is None:
        raise R25SemanticCageDiagnosticError("factory_scene_missing")


def extract_diagnostic(lock_receipt: Mapping[str, Any], lock_frame_sha256: str) -> dict[str, object]:
    _require_factory_read_only_state()
    config, config_path = _read_config()
    verified = _verify_bindings(config)
    bindings = config["bindings"]
    foundation_row = bindings["qualified_foundation_blend"]
    target_row = bindings["r19_visual_target_blend"]
    source_before = {
        "foundation": _sha256_file(_project_file(foundation_row["path"], ".blend")),
        "r19": _sha256_file(_project_file(target_row["path"], ".blend")),
    }
    foundation = _linked_object(
        _project_file(foundation_row["path"], ".blend"),
        foundation_row["object_name"],
        foundation_row["mesh_name"],
    )
    target = _linked_object(
        _project_file(target_row["path"], ".blend"),
        target_row["object_name"],
        target_row["mesh_name"],
    )
    if (
        len(foundation.data.vertices) != foundation_row["vertices"]
        or len(foundation.data.edges) != foundation_row["edges"]
        or len(foundation.data.polygons) != foundation_row["faces"]
        or len(target.data.vertices) != target_row["vertices"]
        or len(target.data.polygons) != target_row["faces"]
    ):
        raise R25SemanticCageDiagnosticError("bound_mesh_topology_count_drift")
    locked, lock_summary = validate_lock_input(lock_receipt, len(foundation.data.vertices))
    minimum_weight = config["semantic_contract"]["minimum_recognized_weight_fixed_1e9"] / 1_000_000_000
    source_regions = classify_weighted_vertices(_weight_rows(foundation), minimum_weight)
    target_regions = classify_weighted_vertices(_weight_rows(target), minimum_weight)
    source_vertices, source_normals = _world_geometry(foundation)
    target_vertices, _ = _world_geometry(target)
    excluded_faces = _r20_excluded_faces(target, bindings["r20_exact_rejected_target_region"])
    result_bindings = {
        "config_sha256": CONFIG_SHA256,
        "lock_frame_sha256": lock_frame_sha256,
        "foundation_blend_sha256": source_before["foundation"],
        "r19_blend_sha256": source_before["r19"],
        "r20_plan_sha256": verified["r20_exact_rejected_target_region"]["sha256"],
        "afes_contract_sha256": verified["foundation_afes_extraction_contract"]["sha256"],
        "pure_core_sha256": verified["pure_correspondence_core"]["sha256"],
        "canonical_receipt_sha256": verified["canonical_receipt_primitive"]["sha256"],
    }
    receipt = build_correspondence_receipt(
        source_vertices=source_vertices,
        source_normals=source_normals,
        source_faces=_faces(foundation),
        source_regions=source_regions,
        target_vertices=target_vertices,
        target_regions=target_regions,
        target_triangles=_target_triangles(target),
        excluded_target_faces=excluded_faces,
        locked_source_vertices=locked,
        lock_summary=lock_summary,
        anchors_per_region=config["alignment_and_anchor_contract"]["anchors_per_region"],
        max_distance_um=config["projection_gates"]["maximum_distance_micrometers"],
        min_normal_dot_fixed=config["projection_gates"]["minimum_normal_dot_fixed_1e9"],
        bindings=result_bindings,
        required_regions=tuple(config["semantic_contract"]["required_regions"]),
    )
    source_after = {
        "foundation": _sha256_file(_project_file(foundation_row["path"], ".blend")),
        "r19": _sha256_file(_project_file(target_row["path"], ".blend")),
    }
    if source_after != source_before:
        raise R25SemanticCageDiagnosticError("bound_blend_changed_during_diagnostic")
    receipt["config_bytes"] = config_path.stat().st_size
    receipt["read_only_source_rehash"] = "UNCHANGED"
    receipt["payload_content_sha256"] = canonical_sha256(receipt)
    canonical_receipt.decode_receipt_frame(canonical_receipt.encode_receipt_frame(receipt))
    return receipt


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock-handle", required=True)
    parser.add_argument("--result-handle", required=True)
    values = parser.parse_args(argv)
    try:
        values.lock_handle = int(values.lock_handle, 10)
        values.result_handle = int(values.result_handle, 10)
    except ValueError as exc:
        parser.error(f"inherited handles must be positive decimal integers: {exc}")
    if values.lock_handle <= 0 or values.result_handle <= 0:
        parser.error("inherited handles must be positive decimal integers")
    return values


def main() -> int:
    arguments = _arguments()
    try:
        lock, lock_hash = _read_lock_frame(arguments.lock_handle)
        payload = extract_diagnostic(lock, lock_hash)
        _write_result_frame(arguments.result_handle, payload)
    except Exception as exc:
        failure = {
            "schema": "kira.r25.semantic_cage_correspondence_diagnostic.v1",
            "status": "DIAGNOSTIC_FAILED_NO_CAGE_NO_CANDIDATE",
            "failure_type": type(exc).__name__,
            "failure": str(exc),
            "config_sha256": CONFIG_SHA256,
        }
        try:
            _write_result_frame(arguments.result_handle, failure)
        except Exception:
            pass
        print(f"R25_SEMANTIC_CAGE_DIAGNOSTIC_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
