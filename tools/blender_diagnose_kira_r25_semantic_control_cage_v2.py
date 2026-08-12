#!/usr/bin/env python3
"""Append-only inert Blender wrapper for R25 semantic control cage Attempt 02.

Preparation only: this source does not authorize execution.  A future caller
must provide the independently bound config SHA-256 plus three canonical AFES
frames (pair acceptance, run 01, run 02) over one inherited Win32 pipe.  The
only output is one canonical frame over a second inherited Win32 pipe.

There are no input/output path arguments, authoring operators, deformations,
saves, renders, exports, candidates, or runtime changes in this file.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_semantic_control_cage_diagnostic_v2.json"
)
FILE_TYPE_PIPE = 3
MAX_INPUT_FRAMES = 3


class R25SemanticControlCageV2Error(RuntimeError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_exact_bytes(path: Path) -> bytes:
    with path.open("rb") as stream:
        return stream.read()


def _project_file(relative: object, expected_suffix: str | None = None) -> Path:
    if not isinstance(relative, str) or not relative:
        raise R25SemanticControlCageV2Error("project_binding_path_not_text")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise R25SemanticControlCageV2Error("unsafe_project_relative_binding")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise R25SemanticControlCageV2Error("symlink_binding_refused")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise R25SemanticControlCageV2Error("binding_escaped_project_root") from exc
    if not resolved.is_file() or (expected_suffix and resolved.suffix.lower() != expected_suffix):
        raise R25SemanticControlCageV2Error("binding_file_type_mismatch")
    return resolved


def _verified_row(label: str, row: object, expected_suffix: str | None = None) -> tuple[Path, bytes]:
    if not isinstance(row, Mapping) or not {"path", "bytes", "sha256"}.issubset(row):
        raise R25SemanticControlCageV2Error(f"binding_row_invalid:{label}")
    path = _project_file(row["path"], expected_suffix)
    raw = _read_exact_bytes(path)
    if len(raw) != row["bytes"] or _sha256_bytes(raw) != row["sha256"]:
        raise R25SemanticControlCageV2Error(f"binding_drift:{label}")
    return path, raw


def _read_config(expected_sha256: str) -> tuple[dict[str, Any], bytes, Path]:
    if re.fullmatch(r"[0-9a-f]{64}", expected_sha256 or "") is None:
        raise R25SemanticControlCageV2Error("expected_config_sha256_invalid")
    path = _project_file(CONFIG_RELATIVE_PATH, ".json")
    raw = _read_exact_bytes(path)
    if _sha256_bytes(raw) != expected_sha256:
        raise R25SemanticControlCageV2Error("semantic_control_cage_config_hash_mismatch")
    try:
        config = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise R25SemanticControlCageV2Error("semantic_control_cage_config_invalid_json") from exc
    if not isinstance(config, dict) or config.get("schema") != (
        "kira.avatar.r25.semantic_control_cage_diagnostic.v2"
    ) or config.get("attempt_id") != "attempt_02":
        raise R25SemanticControlCageV2Error("semantic_control_cage_config_identity_drift")
    if config.get("status") != "STATIC_PREPARATION_ONLY_BLENDER_EXECUTION_NOT_AUTHORIZED":
        raise R25SemanticControlCageV2Error("semantic_control_cage_config_status_drift")
    if config.get("afes_pair_binding", {}).get("seal_status") != "SEALED_TO_FINAL_INDEPENDENTLY_ACCEPTED_PAIR":
        raise R25SemanticControlCageV2Error("final_independently_accepted_afes_pair_not_sealed")
    return config, raw, path


def _load_fresh_exact_module(label: str, row: object, required_symbols: Sequence[str]) -> Any:
    """Compile/execute exact verified bytes without consuming ambient modules."""

    path, raw = _verified_row(label, row, ".py")
    digest = _sha256_bytes(raw)
    private_name = f"_kira_r25_exact_{label}_{digest}"
    if private_name in sys.modules:
        raise R25SemanticControlCageV2Error(f"fresh_module_namespace_already_present:{label}")
    spec = importlib.util.spec_from_loader(private_name, loader=None, origin=str(path))
    if spec is None:
        raise R25SemanticControlCageV2Error(f"fresh_module_spec_unavailable:{label}")
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    sys.modules[private_name] = module
    try:
        code = compile(raw, str(path), "exec", dont_inherit=True, optimize=0)
        exec(code, module.__dict__, module.__dict__)
        for symbol in required_symbols:
            value = getattr(module, symbol, None)
            if value is None:
                raise R25SemanticControlCageV2Error(f"fresh_module_symbol_missing:{label}:{symbol}")
            defining_module = getattr(value, "__module__", private_name)
            if defining_module != private_name:
                raise R25SemanticControlCageV2Error(f"fresh_module_symbol_origin_mismatch:{label}:{symbol}")
    except BaseException:
        sys.modules.pop(private_name, None)
        raise
    return module


def _verify_config_and_modules(config: Mapping[str, Any]) -> tuple[Any, Any, dict[str, dict[str, object]]]:
    bindings = config.get("bindings")
    if not isinstance(bindings, Mapping):
        raise R25SemanticControlCageV2Error("binding_table_missing")
    required = {
        "execution_wrapper", "pure_control_cage_core", "canonical_receipt_primitive",
        "qualified_foundation_blend", "r19_visual_target_blend",
        "r20_exact_rejected_target_region", "makehuman_default_weights",
    }
    if not required.issubset(bindings):
        raise R25SemanticControlCageV2Error("required_binding_missing")
    wrapper_path, _ = _verified_row("execution_wrapper", bindings["execution_wrapper"], ".py")
    if wrapper_path != Path(__file__).resolve(strict=True):
        raise R25SemanticControlCageV2Error("execution_wrapper_self_binding_mismatch")
    receipt = _load_fresh_exact_module(
        "canonical_receipt_primitive", bindings["canonical_receipt_primitive"],
        ("encode_receipt_frame", "decode_receipt_frame"),
    )
    control = _load_fresh_exact_module(
        "pure_control_cage_core", bindings["pure_control_cage_core"],
        (
            "Triangle", "classify_weighted_vertices", "validate_afes_pair_bundle",
            "similarity_from_region_centroids", "select_control_anchors_with_coverage",
            "map_control_anchors_to_target", "encode_mapping_records",
            "decode_and_validate_mapping_records", "alignment_receipt", "canonical_sha256",
        ),
    )
    receipt_row = bindings["canonical_receipt_primitive"]
    if (
        receipt.MAX_RECEIPT_PAYLOAD_BYTES != receipt_row["maximum_payload_bytes"]
        or receipt.MAX_RECEIPT_DEPTH != receipt_row["maximum_depth"]
        or receipt.MAX_RECEIPT_NODES != receipt_row["maximum_nodes"]
    ):
        raise R25SemanticControlCageV2Error("canonical_receipt_limit_binding_drift")
    observed: dict[str, dict[str, object]] = {}
    for label, row in sorted(bindings.items()):
        suffix = Path(str(row.get("path", ""))).suffix.lower() if isinstance(row, Mapping) else ""
        if suffix not in (".py", ".json", ".blend", ".mhw", ".md"):
            raise R25SemanticControlCageV2Error(f"binding_suffix_refused:{label}")
        path, raw = _verified_row(label, row, suffix)
        observed[label] = {"path": path.relative_to(PROJECT_ROOT).as_posix(), "bytes": len(raw), "sha256": _sha256_bytes(raw)}
    return receipt, control, observed


def _require_pipe(raw_handle: int, label: str) -> None:
    if os.name != "nt" or type(raw_handle) is not int or raw_handle <= 0:
        raise R25SemanticControlCageV2Error(f"{label}_handle_invalid_or_non_windows")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetFileType.argtypes = [ctypes.c_void_p]
    kernel32.GetFileType.restype = ctypes.c_uint32
    if int(kernel32.GetFileType(ctypes.c_void_p(raw_handle))) != FILE_TYPE_PIPE:
        raise R25SemanticControlCageV2Error(f"{label}_handle_is_not_FILE_TYPE_PIPE")


def _adopt_pipe(raw_handle: int, flags: int, label: str):
    _require_pipe(raw_handle, label)
    import msvcrt

    try:
        descriptor = msvcrt.open_osfhandle(raw_handle, flags | getattr(os, "O_BINARY", 0))
    except OSError as exc:
        raise R25SemanticControlCageV2Error(f"{label}_pipe_adoption_failed") from exc
    mode = "rb" if flags == os.O_RDONLY else "wb"
    return os.fdopen(descriptor, mode, buffering=0, closefd=True)


def _read_exact(stream: Any, count: int) -> bytes:
    result = bytearray()
    while len(result) < count:
        block = stream.read(count - len(result))
        if not block:
            raise R25SemanticControlCageV2Error("input_receipt_frame_truncated")
        result.extend(block)
    return bytes(result)


def _read_one_frame(stream: Any, receipt: Any) -> tuple[dict[str, Any], str]:
    header = _read_exact(stream, receipt.RECEIPT_HEADER_BYTES)
    try:
        magic, version, payload_length, _ = receipt.RECEIPT_HEADER.unpack(header)
    except Exception as exc:
        raise R25SemanticControlCageV2Error("input_receipt_header_invalid") from exc
    if magic != receipt.RECEIPT_MAGIC or version != receipt.RECEIPT_VERSION:
        raise R25SemanticControlCageV2Error("input_receipt_magic_or_version_invalid")
    if payload_length > receipt.MAX_RECEIPT_PAYLOAD_BYTES:
        raise R25SemanticControlCageV2Error("input_receipt_payload_too_large")
    frame = header + _read_exact(stream, int(payload_length))
    decoded = receipt.decode_receipt_frame(frame)
    return decoded.payload, decoded.frame_sha256


def _read_afes_bundle(raw_handle: int, receipt: Any):
    _require_pipe(raw_handle, "lock_input")
    with _adopt_pipe(raw_handle, os.O_RDONLY, "lock_input") as stream:
        frames = [_read_one_frame(stream, receipt) for _ in range(MAX_INPUT_FRAMES)]
        if stream.read(1) != b"":
            raise R25SemanticControlCageV2Error("input_pipe_contains_more_than_three_frames")
    return frames[0], (frames[1], frames[2])


def _write_result(raw_handle: int, receipt: Any, payload: Mapping[str, Any]) -> None:
    _require_pipe(raw_handle, "result_output")
    frame = receipt.encode_receipt_frame(payload)
    if receipt.decode_receipt_frame(frame).payload != dict(payload):
        raise R25SemanticControlCageV2Error("result_receipt_roundtrip_failed")
    with _adopt_pipe(raw_handle, os.O_WRONLY, "result_output") as stream:
        view = memoryview(frame)
        total = 0
        while total < len(view):
            written = stream.write(view[total:])
            if type(written) is not int or written <= 0:
                raise R25SemanticControlCageV2Error("result_pipe_short_write")
            total += written


def _inventory() -> dict[str, object]:
    return {
        "objects": sorted((value.name, value.type) for value in bpy.data.objects),
        "meshes": sorted(value.name for value in bpy.data.meshes),
        "scenes": sorted(value.name for value in bpy.data.scenes),
        "dirty": "YES" if bpy.data.is_dirty else "NO",
        "filepath": str(bpy.data.filepath),
    }


def _require_factory_state() -> None:
    if bpy.data.filepath or bpy.data.is_dirty or str(bpy.context.mode) != "OBJECT":
        raise R25SemanticControlCageV2Error("factory_clean_object_mode_required")


def _linked_object(row: Mapping[str, Any]) -> Any:
    blend = _project_file(row["path"], ".blend")
    with bpy.data.libraries.load(str(blend), link=True) as (available, requested):
        if row["object_name"] not in available.objects:
            raise R25SemanticControlCageV2Error(f"bound_object_missing:{row['object_name']}")
        requested.objects = [row["object_name"]]
    obj = requested.objects[0]
    if obj is None or obj.type != "MESH" or obj.data.name != row["mesh_name"]:
        raise R25SemanticControlCageV2Error("bound_object_or_mesh_identity_drift")
    return obj


def _world_geometry(obj: Any):
    matrix = obj.matrix_world
    normal_matrix = matrix.to_3x3().inverted_safe().transposed()
    vertices = [tuple(float(value) for value in (matrix @ vertex.co)) for vertex in obj.data.vertices]
    normals = [tuple(float(value) for value in (normal_matrix @ vertex.normal).normalized()) for vertex in obj.data.vertices]
    return vertices, normals


def _weight_rows(obj: Any):
    names = {int(group.index): str(group.name) for group in obj.vertex_groups}
    return [
        [(names[int(item.group)], float(item.weight)) for item in vertex.groups]
        for vertex in obj.data.vertices
    ]


def _faces(obj: Any):
    return [tuple(int(value) for value in polygon.vertices) for polygon in obj.data.polygons]


def _edges(obj: Any):
    return [tuple(int(value) for value in edge.vertices) for edge in obj.data.edges]


def _triangles(obj: Any, control: Any):
    obj.data.calc_loop_triangles()
    return [
        control.Triangle(
            int(triangle.polygon_index), int(triangle.index),
            tuple(int(value) for value in triangle.vertices),
        )
        for triangle in obj.data.loop_triangles
    ]


def _r20_excluded_faces(target: Any, row: Mapping[str, Any]) -> set[int]:
    if row.get("selector") != "r19_primary_surface_polygon_material_index_equals_1":
        raise R25SemanticControlCageV2Error("r20_selector_drift")
    selected = {int(face.index) for face in target.data.polygons if int(face.material_index) == 1}
    if len(selected) != row["selected_faces"]:
        raise R25SemanticControlCageV2Error("r20_selected_face_count_drift")
    return selected


def _validate_makehuman_allowlist(path_row: Mapping[str, Any], control: Any) -> None:
    path, raw = _verified_row("makehuman_default_weights", path_row, ".mhw")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise R25SemanticControlCageV2Error("makehuman_default_weights_invalid") from exc
    if payload.get("license") != "CC0" or tuple(sorted(payload.get("weights", {}))) != control.OFFICIAL_MAKEHUMAN_GROUP_NAMES:
        raise R25SemanticControlCageV2Error("official_makehuman_exact_group_allowlist_drift")


def extract_diagnostic(
    *, config_sha256: str, pair_payload: Mapping[str, Any], pair_frame_sha256: str,
    run_payloads: Sequence[Mapping[str, Any]], run_frame_sha256s: Sequence[str],
) -> tuple[dict[str, object], Any]:
    _require_factory_state()
    config, config_raw, _ = _read_config(config_sha256)
    receipt, control, observed = _verify_config_and_modules(config)
    bindings = config["bindings"]
    _validate_makehuman_allowlist(bindings["makehuman_default_weights"], control)
    foundation_before = _sha256_bytes(_read_exact_bytes(_project_file(bindings["qualified_foundation_blend"]["path"], ".blend")))
    target_before = _sha256_bytes(_read_exact_bytes(_project_file(bindings["r19_visual_target_blend"]["path"], ".blend")))
    foundation = _linked_object(bindings["qualified_foundation_blend"])
    target = _linked_object(bindings["r19_visual_target_blend"])
    for label, obj, row in (
        ("foundation", foundation, bindings["qualified_foundation_blend"]),
        ("target", target, bindings["r19_visual_target_blend"]),
    ):
        if len(obj.data.vertices) != row["vertices"] or len(obj.data.polygons) != row["faces"]:
            raise R25SemanticControlCageV2Error(f"{label}_topology_count_drift")
    if len(foundation.data.edges) != bindings["qualified_foundation_blend"]["edges"]:
        raise R25SemanticControlCageV2Error("foundation_edge_count_drift")
    source_edges, source_faces = _edges(foundation), _faces(foundation)
    locked, lock_summary = control.validate_afes_pair_bundle(
        pair_payload=pair_payload, pair_frame_sha256=pair_frame_sha256,
        run_payloads=run_payloads, run_frame_sha256s=run_frame_sha256s,
        source_edges=source_edges, source_faces=source_faces,
        expected=config["afes_pair_binding"]["expected_pair_and_analysis"],
    )
    minimum_weight = config["semantic_contract"]["minimum_recognized_weight_fixed_1e9"] / 1_000_000_000
    source_regions = control.classify_weighted_vertices(_weight_rows(foundation), minimum_weight)
    target_regions = control.classify_weighted_vertices(_weight_rows(target), minimum_weight)
    source_vertices, source_normals = _world_geometry(foundation)
    target_vertices, _ = _world_geometry(target)
    target_triangles = _triangles(target, control)
    excluded_faces = _r20_excluded_faces(target, bindings["r20_exact_rejected_target_region"])
    excluded_target_vertices = {
        vertex for triangle in target_triangles if triangle.face_index in excluded_faces
        for vertex in triangle.vertex_indices
    }
    alignment = config["alignment_contract"]
    result = control.similarity_from_region_centroids(
        source_vertices, source_regions, target_vertices, target_regions,
        tuple(config["semantic_contract"]["required_regions"]), locked, excluded_target_vertices,
        minimum_rank_ratio=alignment["minimum_rank_ratio_fixed_1e9"] / 1_000_000_000,
        minimum_scale=alignment["minimum_scale_fixed_1e9"] / 1_000_000_000,
        maximum_scale=alignment["maximum_scale_fixed_1e9"] / 1_000_000_000,
        maximum_normalized_rms_residual=alignment["maximum_normalized_rms_residual_fixed_1e9"] / 1_000_000_000,
        maximum_orthonormal_residual=alignment["maximum_orthonormal_residual_fixed_1e12"] / 1_000_000_000_000,
        minimum_left_right_separation=alignment["minimum_left_right_separation_micrometers"] / 1_000_000,
    )
    coverage = control.select_control_anchors_with_coverage(
        source_vertices, source_faces, source_regions, locked,
        config["control_cage_contract"]["anchors_per_region"],
        config["control_cage_contract"]["maximum_same_region_geodesic_radius_micrometers"],
        tuple(config["semantic_contract"]["required_regions"]),
    )
    mappings = control.map_control_anchors_to_target(
        coverage.anchors, source_vertices, source_normals, source_regions,
        target_vertices, target_triangles, target_regions, excluded_faces,
        result.similarity, config["projection_gates"]["maximum_distance_micrometers"],
        config["projection_gates"]["minimum_normal_dot_fixed_1e9"],
    )
    encoded, binary_digest, mapping_digest = control.encode_mapping_records(mappings)
    control.decode_and_validate_mapping_records(
        encoded=encoded, declared_count=len(mappings),
        declared_record_bytes=control.MAPPING_RECORD.size,
        declared_codec=control.MAPPING_CODEC,
        declared_binary_sha256=binary_digest, declared_mapping_sha256=mapping_digest,
        expected_anchors=coverage.anchors, source_regions=source_regions,
        target_regions=target_regions, target_triangles=target_triangles,
        target_face_count=len(target.data.polygons), excluded_target_faces=excluded_faces,
        maximum_distance_um=config["projection_gates"]["maximum_distance_micrometers"],
        minimum_normal_dot_fixed=config["projection_gates"]["minimum_normal_dot_fixed_1e9"],
    )
    foundation_after = _sha256_bytes(_read_exact_bytes(_project_file(bindings["qualified_foundation_blend"]["path"], ".blend")))
    target_after = _sha256_bytes(_read_exact_bytes(_project_file(bindings["r19_visual_target_blend"]["path"], ".blend")))
    if (foundation_before, target_before) != (foundation_after, target_after):
        raise R25SemanticControlCageV2Error("bound_blend_changed_during_diagnostic")
    payload: dict[str, object] = {
        "schema": "kira.r25.semantic_control_cage_diagnostic.v2",
        "status": "CONTROL_CAGE_DIAGNOSTIC_COMPUTED_NOT_A_BODY_OR_ACCEPTED_DEFORMATION_CAGE",
        "config_sha256": config_sha256,
        "config_bytes": len(config_raw),
        "bindings": observed,
        "afes_pair": lock_summary,
        "semantic_group_allowlist": "EXACT_139_OFFICIAL_MAKEHUMAN_DEFAULT_WEIGHT_NAMES",
        "physical_side_rule": "ANATOMICAL_LEFT_POSITIVE_X_AND_GREATER_THAN_RIGHT_SOURCE_AND_TARGET",
        "global_similarity_alignment": control.alignment_receipt(result),
        "control_cage_label": "432_REGION_BALANCED_CONTROL_ANCHORS_NOT_DIRECT_ALL_VERTEX_MAPPING",
        "whole_permissible_surface_coverage": list(coverage.rows),
        "mapping_count": len(mappings),
        "mapping_codec": control.MAPPING_CODEC,
        "mapping_record_bytes": control.MAPPING_RECORD.size,
        "mapping_binary_sha256": binary_digest,
        "mapping_sha256": mapping_digest,
        "mapping_records_base64": encoded,
        "r20_excluded_target_face_count": len(excluded_faces),
        "r20_excluded_target_face_sha256": control.index_sha256(excluded_faces),
        "source_files_rehashed_unchanged": "YES",
        "truth_boundary": [
            "READ_ONLY_DIAGNOSTIC_ONLY", "NO_DEFORMATION", "NO_BLEND_SAVE",
            "NO_RENDER_OR_EXPORT", "NO_CANDIDATE", "NO_BODY_AUTHORITY",
            "NO_RUNTIME_ACTIVATION", "NOT_OWNER_ACCEPTED",
        ],
    }
    payload["payload_content_sha256"] = control.canonical_sha256(payload)
    if receipt.decode_receipt_frame(receipt.encode_receipt_frame(payload)).payload != payload:
        raise R25SemanticControlCageV2Error("final_payload_roundtrip_failed")
    return payload, receipt


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--lock-handle", required=True)
    parser.add_argument("--result-handle", required=True)
    values = parser.parse_args(argv)
    if re.fullmatch(r"[0-9a-f]{64}", values.config_sha256) is None:
        parser.error("config SHA-256 must be 64 lowercase hexadecimal characters")
    try:
        values.lock_handle = int(values.lock_handle, 10)
        values.result_handle = int(values.result_handle, 10)
    except ValueError as exc:
        parser.error(f"handles must be positive decimal integers: {exc}")
    if values.lock_handle <= 0 or values.result_handle <= 0 or values.lock_handle == values.result_handle:
        parser.error("handles must be distinct positive decimal integers")
    return values


def main() -> int:
    arguments = _arguments()
    receipt = None
    try:
        config, _, _ = _read_config(arguments.config_sha256)
        receipt, _, _ = _verify_config_and_modules(config)
        (pair, pair_hash), run_frames = _read_afes_bundle(arguments.lock_handle, receipt)
        payload, receipt = extract_diagnostic(
            config_sha256=arguments.config_sha256,
            pair_payload=pair, pair_frame_sha256=pair_hash,
            run_payloads=(run_frames[0][0], run_frames[1][0]),
            run_frame_sha256s=(run_frames[0][1], run_frames[1][1]),
        )
        _write_result(arguments.result_handle, receipt, payload)
    except Exception as exc:
        if receipt is not None:
            failure = {
                "schema": "kira.r25.semantic_control_cage_diagnostic.v2",
                "status": "DIAGNOSTIC_FAILED_NO_CAGE_NO_CANDIDATE",
                "failure_type": type(exc).__name__, "failure": str(exc),
                "config_sha256": arguments.config_sha256,
            }
            try:
                _write_result(arguments.result_handle, receipt, failure)
            except Exception:
                pass
        print(f"R25_SEMANTIC_CONTROL_CAGE_V2_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
