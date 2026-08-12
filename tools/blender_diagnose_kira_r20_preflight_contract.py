#!/usr/bin/env python3
"""Collect every remaining Kira R20 source-preflight gate without authoring.

This diagnostic exists because append-only preflight_attempt_03 proved that the
licensed-interface JSON's field named ``ordered_boundary_cycles_world_m`` is a
connected-component BFS listing, not an edge-walk cycle.  The diagnostic opens
only the exact sealed R19 Blend, performs no mesh/object/material/action edit,
contains no Blend-save call, and writes evidence only to one exact append-only
diagnostic directory.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback
from typing import Any, Callable, Mapping, Sequence

import bpy
from mathutils import Vector


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_author_kira_r20_pelvis_only as worker  # noqa: E402
from Core import kira_r20_curvilinear_pelvic_patch as patch_contract  # noqa: E402


DIAGNOSTIC_ID = "KIRA_R20_WHOLE_SOURCE_PREFLIGHT_RECONCILIATION_V1"
CONFIG_REL = (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/AUTHORING_CONFIG.json"
)
CONFIG_SHA256 = "a01d130e762d3e0e1878300e969a14f5612db984fb20a4e29e129dba56715543"
WORKER_REL = "tools/blender_author_kira_r20_pelvis_only.py"
WORKER_SHA256 = "e127349d0e5faa745b95a727c9b7843de572315601677e102d017291d0c69533"
ATTEMPT03_FAILURE_REL = (
    "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/"
    "preflight_attempt_03/PREFLIGHT_FAILURE.json"
)
ATTEMPT03_FAILURE_SHA256 = (
    "3afa5894348d862974e3829c3c4dad5fa0d1aed92bf7c7c503d058d75c0f50ab"
)
INTERFACE_REL = (
    "Avatar/private_owner_review/kira_temporary_functional_body_20260730/"
    "source_inspection/blackproject_adult_patch_interface.json"
)
INTERFACE_SHA256 = "01beed05140bb22bff2de23922d280fb312952078b496f16fb4fd80d9d742c86"
INTERFACE_PROBE_REL = "tools/blender_probe_blackproject_adult_patch_interface.py"
INTERFACE_PROBE_SHA256 = (
    "5dc1cff5ebc8a986c8db98eabbd75e042ed862cc58623d7e61051b4a8025d21d"
)
EXPECTED_OUTPUT_REL = (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_preflight_contract_reconciliation/diagnostic_attempt_01"
)
TOLERANCE_M = 1.0e-8


class DiagnosticError(RuntimeError):
    """Fail-closed diagnostic setup error."""


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--acknowledge-read-only", action="store_true")
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()


def project_path(relative: str, *, must_exist: bool = True) -> Path:
    path = (PROJECT_ROOT / relative).resolve()
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise DiagnosticError(f"path escapes project root: {relative}") from exc
    if must_exist and not path.exists():
        raise FileNotFoundError(path)
    return path


def project_relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def assert_hash(relative: str, expected: str) -> dict[str, Any]:
    path = project_path(relative)
    actual = sha256_file(path)
    if actual != expected:
        raise DiagnosticError(f"hash mismatch for {relative}: {actual} != {expected}")
    return {"path": relative, "sha256": actual, "size_bytes": path.stat().st_size}


def write_json_exclusive(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")


def write_text_exclusive(path: Path, value: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)


def exception_record(exc: BaseException) -> dict[str, Any]:
    return {
        "status": "FAIL",
        "error_type": type(exc).__name__,
        "error": str(exc),
        "traceback": traceback.format_exc(),
    }


def capture(gates: dict[str, Any], name: str, callback: Callable[[], Any]) -> Any:
    try:
        value = callback()
        gates[name] = {"status": "PASS", "evidence": value}
        return value
    except Exception as exc:
        gates[name] = exception_record(exc)
        return None


def matrix_rows(value: Any) -> list[list[float]]:
    return [[float(component) for component in row] for row in value]


def one_to_one_nearest(
    actual: Sequence[Sequence[float]],
    expected: Sequence[Sequence[float]],
) -> dict[str, Any]:
    if len(actual) != len(expected):
        return {
            "status": "FAIL_COUNT",
            "actual_count": len(actual),
            "expected_count": len(expected),
        }
    records = []
    chosen = []
    for actual_index, point in enumerate(actual):
        distances = [math.dist(point, target) for target in expected]
        nearest = min(range(len(distances)), key=distances.__getitem__)
        chosen.append(nearest)
        records.append(
            {
                "actual_index": actual_index,
                "expected_index": nearest,
                "distance_m": distances[nearest],
                "second_nearest_distance_m": sorted(distances)[1],
            }
        )
    unique = len(set(chosen)) == len(expected)
    maximum = max(record["distance_m"] for record in records)
    return {
        "status": "PASS" if unique and maximum <= TOLERANCE_M else "FAIL",
        "actual_count": len(actual),
        "expected_count": len(expected),
        "unique_bijective_nearest_assignment": unique,
        "maximum_nearest_distance_m": maximum,
        "tolerance_m": TOLERANCE_M,
        "records": records,
    }


def selected_mask_audit(
    body: bpy.types.Object,
    interface_evidence: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    mesh = body.data
    selected = {
        int(polygon.index)
        for polygon in mesh.polygons
        if int(polygon.material_index) == worker.PATCH_MATERIAL_SLOT
    }
    incident = {
        int(vertex)
        for face_index in selected
        for vertex in mesh.polygons[face_index].vertices
    }
    edge_faces: defaultdict[tuple[int, int], list[int]] = defaultdict(list)
    for polygon in mesh.polygons:
        values = [int(vertex) for vertex in polygon.vertices]
        for first, second in zip(values, values[1:] + values[:1]):
            edge_faces[tuple(sorted((first, second)))].append(int(polygon.index))
    interface_edges = []
    invalid_interface_edges = []
    for edge, face_indices in edge_faces.items():
        selected_count = sum(face_index in selected for face_index in face_indices)
        if selected_count and selected_count != len(face_indices):
            if len(face_indices) == 2 and selected_count == 1:
                interface_edges.append(edge)
            else:
                invalid_interface_edges.append(
                    {
                        "edge": list(edge),
                        "incident_faces": sorted(face_indices),
                        "selected_incident_faces": selected_count,
                    }
                )
    graph: defaultdict[int, set[int]] = defaultdict(set)
    for first, second in interface_edges:
        graph[first].add(second)
        graph[second].add(first)
    degree_errors = {
        str(vertex): len(neighbors)
        for vertex, neighbors in graph.items()
        if len(neighbors) != 2
    }

    pure_mask = None
    pure_mask_error = None
    try:
        pure_mask = patch_contract.mask_topology_contract(
            [tuple(int(vertex) for vertex in polygon.vertices) for polygon in mesh.polygons],
            selected,
        )
    except Exception as exc:
        pure_mask_error = {"error_type": type(exc).__name__, "error": str(exc)}

    raw_cycle = None
    cycle_error = None
    try:
        raw_cycle = worker._walk_cycle(graph)
    except Exception as exc:
        cycle_error = {"error_type": type(exc).__name__, "error": str(exc)}

    canonical_points: list[tuple[float, float, float]] = []
    seam_indices: list[int] = []
    local_points: list[tuple[float, float, float]] = []
    if raw_cycle is not None:
        world_points = [body.matrix_world @ mesh.vertices[index].co for index in raw_cycle]
        canonical, order = patch_contract.canonicalize_cycle(
            [tuple(float(value) for value in point) for point in world_points]
        )
        canonical_points = list(canonical)
        seam_indices = [raw_cycle[index] for index in order]
        local_points = [
            tuple(float(value) for value in mesh.vertices[index].co)
            for index in seam_indices
        ]

    source_bfs_rows = [
        tuple(float(value) for value in point)
        for point in interface_evidence["adult_patch"][
            "ordered_boundary_cycles_world_m"
        ][0]
    ]
    source_records = interface_evidence["adult_boundary_to_base_vertices"]["records"]
    source_base_world = [
        tuple(float(value) for value in record["base_world"])
        for record in source_records
    ]
    source_adult_world = [
        tuple(float(value) for value in record["adult_world"])
        for record in source_records
    ]

    sequential_comparison = None
    if canonical_points:
        broken_canonical, _ = patch_contract.canonicalize_cycle(source_bfs_rows)
        deltas = [
            math.dist(canonical_points[index], broken_canonical[index])
            for index in range(patch_contract.SEAM_COUNT)
        ]
        sequential_comparison = {
            "status": "FAIL",
            "method": "historical incorrect canonicalization of a BFS component list",
            "maximum_delta_m": max(deltas),
            "deltas_m": deltas,
        }

    actual_world_to_full_precision_source = (
        one_to_one_nearest(canonical_points, source_base_world)
        if canonical_points
        else {"status": "NOT_AVAILABLE"}
    )
    actual_world_to_rounded_bfs_rows = (
        one_to_one_nearest(canonical_points, source_bfs_rows)
        if canonical_points
        else {"status": "NOT_AVAILABLE"}
    )
    actual_local_to_source = (
        one_to_one_nearest(local_points, source_base_world)
        if local_points
        else {"status": "NOT_AVAILABLE"}
    )
    evidence_internal_set_match = one_to_one_nearest(source_bfs_rows, source_base_world)
    adult_base_deltas = [
        math.dist(source_adult_world[index], source_base_world[index])
        for index in range(len(source_records))
    ]

    interface_vertices = set(seam_indices)
    interior = incident - interface_vertices if seam_indices else set()
    unselected_references = {
        int(vertex)
        for polygon in mesh.polygons
        if int(polygon.index) not in selected
        for vertex in polygon.vertices
    }
    interior_shared = sorted(interior.intersection(unselected_references))
    bounds_low = [
        min(float((body.matrix_world @ mesh.vertices[index].co)[axis]) for index in incident)
        for axis in range(3)
    ]
    bounds_high = [
        max(float((body.matrix_world @ mesh.vertices[index].co)[axis]) for index in incident)
        for axis in range(3)
    ]
    allowed_low = [-0.054620426, -0.09303198, 0.823473752]
    allowed_high = [0.05467169, 0.060616653, 0.918649852]
    bounds_pass = all(
        bounds_low[axis] >= allowed_low[axis] - TOLERANCE_M
        and bounds_high[axis] <= allowed_high[axis] + TOLERANCE_M
        for axis in range(3)
    )

    expected_pure = {
        "selected_face_count": 376,
        "selected_face_connected_components": 1,
        "incident_vertex_count": 206,
        "interface_edge_count": 34,
        "interface_vertex_count": 34,
        "interface_degree_two": True,
        "interface_connected_components": 1,
        "removable_interior_vertex_count": 172,
    }
    pure_pass = pure_mask is not None and all(
        pure_mask.get(key) == value for key, value in expected_pure.items()
    )
    gate_summary = {
        "selected_face_count": len(selected),
        "selected_face_connected_components": worker._face_connected_components(
            mesh, selected
        ),
        "incident_vertex_count": len(incident),
        "interface_edge_count": len(interface_edges),
        "interface_vertex_count": len(graph),
        "interface_degree_errors": degree_errors,
        "invalid_interface_edges": invalid_interface_edges,
        "cycle_walk_error": cycle_error,
        "removable_interior_vertex_count": len(interior),
        "removable_vertices_referenced_by_preserved_faces": interior_shared,
        "pure_mask_contract": pure_mask,
        "pure_mask_error": pure_mask_error,
        "pure_mask_expected_exact": expected_pure,
        "pure_mask_pass": pure_pass,
        "selected_bounds_world_m": {"minimum": bounds_low, "maximum": bounds_high},
        "allowed_bounds_world_m": {"minimum": allowed_low, "maximum": allowed_high},
        "bounds_pass": bounds_pass,
        "historical_sequence_comparison": sequential_comparison,
        "world_coordinate_set_vs_full_precision_base_records": actual_world_to_full_precision_source,
        "world_coordinate_set_vs_rounded_bfs_rows": actual_world_to_rounded_bfs_rows,
        "local_coordinate_set_vs_world_source": actual_local_to_source,
        "source_bfs_rows_vs_full_precision_base_records": evidence_internal_set_match,
        "source_adult_to_base_maximum_delta_m": max(adult_base_deltas),
        "source_adult_to_base_all_zero": max(adult_base_deltas) == 0.0,
        "body_matrix_world": matrix_rows(body.matrix_world),
        "scene_unit_settings": {
            "system": str(bpy.context.scene.unit_settings.system),
            "scale_length": float(bpy.context.scene.unit_settings.scale_length),
            "length_unit": str(bpy.context.scene.unit_settings.length_unit),
        },
    }

    corrected_set_pass = (
        actual_world_to_full_precision_source.get("status") == "PASS"
        and evidence_internal_set_match.get("status") == "PASS"
        and max(adult_base_deltas) == 0.0
    )
    mask = None
    if raw_cycle is not None:
        mask = {
            "selected_face_ids": sorted(selected),
            "pure_mask_topology_contract": pure_mask,
            "incident_vertex_ids": sorted(incident),
            "removable_interior_vertex_ids": sorted(interior),
            "interface_edge_ids": [list(edge) for edge in sorted(interface_edges)],
            "canonical_seam_vertex_ids": seam_indices,
            "canonical_seam_local_coordinates": [worker.vector_record(value) for value in local_points],
            "canonical_seam_world_coordinates": [worker.vector_record(value) for value in canonical_points],
            "maximum_interface_set_delta_m": actual_world_to_full_precision_source.get(
                "maximum_nearest_distance_m"
            ),
            "interface_coordinate_set_match": corrected_set_pass,
            "selected_bounds_world_m": {
                "minimum": [round(value, 12) for value in bounds_low],
                "maximum": [round(value, 12) for value in bounds_high],
            },
            "selected_face_ids_sha256": sha256_json(sorted(selected)),
            "incident_vertex_ids_sha256": sha256_json(sorted(incident)),
            "removable_vertex_ids_sha256": sha256_json(sorted(interior)),
            "canonical_seam_sha256": sha256_json(
                {
                    "ids": seam_indices,
                    "world": [worker.vector_record(value) for value in canonical_points],
                }
            ),
        }
    gate_summary["corrected_coordinate_set_gate_pass"] = corrected_set_pass
    gate_summary["mask_available_for_downstream_read_only_audit"] = mask is not None
    return gate_summary, mask


def exterior_ring_audit(body: bpy.types.Object, mask: Mapping[str, Any]) -> dict[str, Any]:
    mesh = body.data
    selected = set(int(value) for value in mask["selected_face_ids"])
    seam = [int(value) for value in mask["canonical_seam_vertex_ids"]]
    seam_set = set(seam)
    incident_unselected: defaultdict[int, list[Any]] = defaultdict(list)
    unselected_neighbors: defaultdict[int, set[int]] = defaultdict(set)
    for polygon in mesh.polygons:
        if int(polygon.index) in selected:
            continue
        values = [int(vertex) for vertex in polygon.vertices]
        for vertex in values:
            incident_unselected[vertex].append(polygon)
        for first, second in zip(values, values[1:] + values[:1]):
            unselected_neighbors[first].add(second)
            unselected_neighbors[second].add(first)
    records = []
    first_values = []
    second_values = []
    normal_values = []
    failures = []
    for seam_index in seam:
        first_ids = sorted(unselected_neighbors[seam_index] - seam_set)
        second_ids = sorted(
            {
                neighbor
                for first in first_ids
                for neighbor in unselected_neighbors[first]
                if neighbor not in seam_set
                and neighbor not in first_ids
                and neighbor != seam_index
            }
        )
        faces = incident_unselected[seam_index]
        problems = []
        if not first_ids:
            problems.append("NO_FIRST_EXTERIOR_RING")
        if not second_ids:
            problems.append("NO_SECOND_EXTERIOR_RING")
        if not faces:
            problems.append("NO_UNSELECTED_EXTERIOR_FACE")
        if problems:
            failures.append({"seam_vertex": seam_index, "problems": problems})
            continue
        first = sum((mesh.vertices[index].co for index in first_ids), Vector()) / len(first_ids)
        second = sum((mesh.vertices[index].co for index in second_ids), Vector()) / len(second_ids)
        normal_sum = sum((polygon.normal for polygon in faces), Vector())
        if normal_sum.length <= 1.0e-12:
            failures.append({"seam_vertex": seam_index, "problems": ["COLLAPSED_NORMAL"]})
            continue
        normal = normal_sum.normalized()
        first_values.append(tuple(float(value) for value in first))
        second_values.append(tuple(float(value) for value in second))
        normal_values.append(tuple(float(value) for value in normal))
        records.append(
            {
                "seam_vertex": seam_index,
                "first_ring_source_vertices": first_ids,
                "second_ring_source_vertices": second_ids,
                "exterior_face_ids": sorted(int(face.index) for face in faces),
            }
        )
    return {
        "status": "PASS" if not failures and len(records) == 34 else "FAIL",
        "successful_vertex_count": len(records),
        "failures": failures,
        "records": records,
        "records_sha256": sha256_json(records),
        "first_ring_values_sha256": sha256_json(first_values),
        "second_ring_values_sha256": sha256_json(second_values),
        "normal_values_sha256": sha256_json(normal_values),
    }


def seam_uv_audit(body: bpy.types.Object, mask: Mapping[str, Any]) -> dict[str, Any]:
    mesh = body.data
    selected = set(int(value) for value in mask["selected_face_ids"])
    seam = [int(value) for value in mask["canonical_seam_vertex_ids"]]
    layers = []
    failures = []
    for layer in mesh.uv_layers:
        values: list[tuple[float, float]] = []
        records = []
        layer_ambiguous = False
        for vertex_index in seam:
            samples = []
            for face_index in selected:
                polygon = mesh.polygons[face_index]
                for loop_index in range(
                    int(polygon.loop_start), int(polygon.loop_start + polygon.loop_total)
                ):
                    if int(mesh.loops[loop_index].vertex_index) == vertex_index:
                        uv = layer.data[loop_index].uv
                        samples.append((float(uv.x), float(uv.y)))
            unique = []
            for sample in samples:
                if all(math.dist(sample, prior) > 1.0e-10 for prior in unique):
                    unique.append(sample)
            record = {
                "vertex": vertex_index,
                "sample_count": len(samples),
                "unique_values": [list(value) for value in unique],
            }
            records.append(record)
            if len(unique) == 1:
                values.append(unique[0])
            else:
                layer_ambiguous = True
                failures.append(
                    {
                        "layer": layer.name,
                        "vertex": vertex_index,
                        "problem": "PATCH_SIDE_SEAM_UV_NOT_UNIQUE",
                        "unique_values": record["unique_values"],
                    }
                )
        crossings = patch_contract.uv_cycle_crossings(values) if not layer_ambiguous else []
        if crossings:
            failures.append(
                {
                    "layer": layer.name,
                    "problem": "SEAM_UV_CYCLE_SELF_CROSSES",
                    "crossings": crossings,
                }
            )
        layers.append(
            {
                "name": layer.name,
                "records": records,
                "records_sha256": sha256_json(records),
                "self_crossing_pairs": crossings,
            }
        )
    if not layers:
        failures.append({"problem": "PRIMARY_SURFACE_HAS_NO_UV_LAYER"})
    return {
        "status": "PASS" if not failures else "FAIL",
        "layer_count": len(layers),
        "layers": layers,
        "failures": failures,
    }


def seam_weight_audit(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    mask: Mapping[str, Any],
) -> dict[str, Any]:
    group_names = {int(group.index): group.name for group in body.vertex_groups}
    bone_names = {bone.name for bone in rig.data.bones}
    records = []
    failures = []
    maximum_sum_delta = 0.0
    for vertex_index in mask["canonical_seam_vertex_ids"]:
        vertex = body.data.vertices[int(vertex_index)]
        weights = {
            group_names[int(item.group)]: float(item.weight)
            for item in vertex.groups
            if float(item.weight) > 0.0
        }
        unknown = sorted(set(weights) - bone_names)
        weight_sum = sum(weights.values())
        maximum_sum_delta = max(maximum_sum_delta, abs(weight_sum - 1.0))
        problems = []
        if not weights:
            problems.append("NO_POSITIVE_WEIGHTS")
        if unknown:
            problems.append("NON_ARMATURE_GROUP")
        if not math.isclose(weight_sum, 1.0, rel_tol=0.0, abs_tol=1.0e-5):
            problems.append("WEIGHTS_DO_NOT_SUM_TO_ONE_WITHIN_1E_5")
        records.append(
            {
                "vertex": int(vertex_index),
                "weights": weights,
                "sum": weight_sum,
                "unknown_groups": unknown,
                "problems": problems,
            }
        )
        if problems:
            failures.append({"vertex": int(vertex_index), "problems": problems})
    return {
        "status": "PASS" if not failures and len(records) == 34 else "FAIL",
        "record_count": len(records),
        "records": records,
        "records_sha256": sha256_json(records),
        "maximum_sum_delta": maximum_sum_delta,
        "failures": failures,
    }


def probe_source_order_audit() -> dict[str, Any]:
    path = project_path(INTERFACE_PROBE_REL)
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()

    def line_of(fragment: str) -> int | None:
        return next(
            (index for index, line in enumerate(lines, start=1) if fragment in line),
            None,
        )

    required_fragments = (
        'queue = deque([start])',
        "component.append(current)",
        "for neighbor in adjacency[current]:",
        '"ordered_boundary_cycles_world_m"',
    )
    return {
        "path": INTERFACE_PROBE_REL,
        "sha256": sha256_file(path),
        "required_fragments_present": all(fragment in source for fragment in required_fragments),
        "boundary_component_collection": "breadth-first connected-component visitation",
        "edge_walk_cycle_order_implemented": False,
        "field_label": "ordered_boundary_cycles_world_m",
        "field_label_is_truthful_about_order": False,
        "line_evidence": {fragment: line_of(fragment) for fragment in required_fragments},
        "safe_use_of_existing_evidence": "exact 34-point coordinate set and zero-distance adult-to-base records only; not sequential adjacency",
    }


def write_package(output: Path, result: dict[str, Any]) -> None:
    evidence_path = output / "DIAGNOSTIC_EVIDENCE.json"
    write_json_exclusive(evidence_path, result)
    checkpoint_path = output / "CHECKPOINT.md"
    write_text_exclusive(
        checkpoint_path,
        "# Kira R20 whole-preflight reconciliation diagnostic\n\n"
        f"Status: `{result['status']}`\n\n"
        "This was a read-only source inspection. It did not edit a mesh, save a "
        "Blend, create a candidate, run a pose suite, render, activate, assign, "
        "export, publish, upload, or use the GPU.\n\n"
        f"- Evidence SHA-256: `{sha256_file(evidence_path)}`\n"
        f"- Attempt03 failure preserved: `{ATTEMPT03_FAILURE_SHA256}`\n"
        f"- Source Blend after diagnostic: `{result.get('source_blend_sha256_after', 'NOT_OPENED')}`\n",
    )
    manifest_path = output / "PACKAGE_MANIFEST.json"
    members = []
    for path in sorted(value for value in output.iterdir() if value.is_file()):
        if path == manifest_path:
            continue
        members.append(
            {
                "path": project_relative(path),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    write_json_exclusive(
        manifest_path,
        {
            "schema_version": 1,
            "diagnostic_id": DIAGNOSTIC_ID,
            "status": result["status"],
            "files_excluding_this_manifest": members,
            "body_asset_mutated": False,
            "blend_saved": False,
            "candidate_created": False,
        },
    )


def main() -> int:
    args = parse_args()
    if not args.acknowledge_read_only:
        raise DiagnosticError("--acknowledge-read-only is required")
    output = Path(args.output).resolve()
    expected_output = project_path(EXPECTED_OUTPUT_REL, must_exist=False)
    if output != expected_output:
        raise DiagnosticError(f"only exact output is permitted: {expected_output}")
    if output.exists():
        raise DiagnosticError(f"append-only diagnostic output already exists: {output}")

    sealed_inputs = {
        "config": assert_hash(CONFIG_REL, CONFIG_SHA256),
        "worker": assert_hash(WORKER_REL, WORKER_SHA256),
        "attempt_03_failure": assert_hash(
            ATTEMPT03_FAILURE_REL, ATTEMPT03_FAILURE_SHA256
        ),
        "interface_evidence": assert_hash(INTERFACE_REL, INTERFACE_SHA256),
        "interface_probe_source": assert_hash(
            INTERFACE_PROBE_REL, INTERFACE_PROBE_SHA256
        ),
    }
    output.mkdir(parents=True, exist_ok=False)
    gates: dict[str, Any] = {}
    result: dict[str, Any] = {
        "schema_version": 1,
        "diagnostic_id": DIAGNOSTIC_ID,
        "timestamp_utc": utc_now(),
        "status": "RUNNING",
        "sealed_inputs": sealed_inputs,
        "scope": {
            "read_only": True,
            "body_asset_mutated": False,
            "blend_saved": False,
            "candidate_created": False,
            "pose_suite_run": False,
            "render_run": False,
            "gpu_used": False,
            "activation_assignment_export_publication": False,
        },
        "gates": gates,
    }
    source_path: Path | None = None
    try:
        config_path = project_path(CONFIG_REL)
        args_for_worker = argparse.Namespace(acknowledge_private_inactive=True)
        config_and_paths = capture(
            gates,
            "config_and_whole_source_package",
            lambda: worker.validate_config(config_path, args_for_worker),
        )
        if config_and_paths is None:
            raise DiagnosticError("exact worker config/package validation failed")
        config, paths = config_and_paths
        gates["config_and_whole_source_package"]["evidence"] = {
            "config_status": config["status"],
            "source_manifest_member_count": worker.EXPECTED_SOURCE_MANIFEST_ENTRIES,
            "source_manifest_exact_set_and_hashes": True,
        }
        source_path = paths["source_blend"]
        source_hash_before = sha256_file(source_path)
        worker._open_exact_blend(source_path)
        result["source_blend_sha256_before"] = source_hash_before

        components = capture(
            gates, "exact_body_rig_counts_materials", lambda: worker._find_scene_components(config)
        )
        if components is None:
            raise DiagnosticError("exact body/rig lookup failed; downstream audit unsafe")
        body, rig = components
        gates["exact_body_rig_counts_materials"]["evidence"] = {
            "body": body.name,
            "mesh": body.data.name,
            "counts": {
                "vertices": len(body.data.vertices),
                "edges": len(body.data.edges),
                "faces": len(body.data.polygons),
            },
            "rig": rig.name,
            "rig_bones": len(rig.data.bones),
            "material_slots": [
                slot.material.name if slot.material is not None else None
                for slot in body.material_slots
            ],
        }
        capture(
            gates,
            "freeze_and_whole_exact_mesh_inventory",
            lambda: worker.validate_freeze_ledger(
                body,
                rig,
                paths["r20_freeze_ledger"],
                paths["freeze_identity_correction"],
                require_source_primary_hashes=True,
            ),
        )
        capture(gates, "interface_probe_source_order_truth", probe_source_order_audit)
        interface_evidence = json.loads(paths["interface_evidence"].read_text(encoding="utf-8"))
        capture(
            gates,
            "historical_attempt03_sequential_interface_gate",
            lambda: worker.derive_exact_mask(body, paths["interface_evidence"]),
        )
        mask_audit, mask = selected_mask_audit(body, interface_evidence)
        gates["corrected_interface_set_and_mask_contract"] = {
            "status": (
                "PASS"
                if mask_audit["corrected_coordinate_set_gate_pass"]
                and mask_audit["pure_mask_pass"]
                and mask_audit["bounds_pass"]
                and not mask_audit["removable_vertices_referenced_by_preserved_faces"]
                else "FAIL"
            ),
            "evidence": mask_audit,
        }
        if mask is None:
            raise DiagnosticError("topological seam cycle unavailable; downstream audit unsafe")

        preserved = capture(
            gates, "preserved_primary_snapshot", lambda: worker.preserved_primary_snapshot(body)
        )
        if preserved is not None:
            gates["preserved_primary_counts"] = {
                "status": (
                    "PASS"
                    if preserved["preserved_face_count"] == 24560
                    and preserved["preserved_vertex_count"] == 12440
                    else "FAIL"
                ),
                "evidence": {
                    "expected_faces": 24560,
                    "actual_faces": preserved["preserved_face_count"],
                    "expected_vertices": 12440,
                    "actual_vertices": preserved["preserved_vertex_count"],
                },
            }

        gates["all_exterior_ring_and_normal_vertices"] = {
            "status": "RUNNING",
            "evidence": exterior_ring_audit(body, mask),
        }
        gates["all_exterior_ring_and_normal_vertices"]["status"] = gates[
            "all_exterior_ring_and_normal_vertices"
        ]["evidence"]["status"]
        capture(
            gates,
            "production_exterior_ring_function",
            lambda: {
                "value_hashes": [
                    sha256_json(value)
                    for value in worker.derive_exterior_rings_and_normals(body, mask)[:3]
                ],
                "evidence": worker.derive_exterior_rings_and_normals(body, mask)[3],
            },
        )

        gates["all_seam_uv_vertices"] = {
            "status": "RUNNING",
            "evidence": seam_uv_audit(body, mask),
        }
        gates["all_seam_uv_vertices"]["status"] = gates["all_seam_uv_vertices"][
            "evidence"
        ]["status"]
        capture(
            gates,
            "production_seam_uv_function",
            lambda: {
                "values_sha256": sha256_json(worker.seam_uv_records(body, mask)[0]),
                "evidence": worker.seam_uv_records(body, mask)[1],
            },
        )

        gates["all_seam_weight_vertices"] = {
            "status": "RUNNING",
            "evidence": seam_weight_audit(body, rig, mask),
        }
        gates["all_seam_weight_vertices"]["status"] = gates[
            "all_seam_weight_vertices"
        ]["evidence"]["status"]
        capture(
            gates,
            "production_seam_weight_function",
            lambda: {
                "values_sha256": sha256_json(worker.seam_weight_records(body, rig, mask)[0]),
                "evidence": worker.seam_weight_records(body, rig, mask)[1],
            },
        )

        capture(gates, "pure_patch_contract", patch_contract.contract_record)
        capture(
            gates,
            "global_frozen_state_digests",
            lambda: {
                "rig_rest_structure_sha256": worker.rig_rest_signature(rig),
                "actions_sha256": worker.action_digest(),
                "materials_sha256": worker.material_graph_digest(),
                "body_matrix_world_sha256": worker._matrix_digest(body.matrix_world),
                "body_modifiers_sha256": sha256_json(worker.modifier_record(body)),
            },
        )
        result["coordinate_frame_decision"] = {
            "licensed_authority": "34 full-precision base_world coordinates in adult_boundary_to_base_vertices.records, each paired to adult_world at recorded zero distance",
            "comparison_frame": "R19 body vertex local coordinates transformed by the exact body.matrix_world into world meters",
            "ordering_authority": "actual sealed R19 selected/unselected edge cycle; canonicalized by the existing unique minimum-world-Y and adjacent greater-Z/X direction rule",
            "prohibited_ordering_authority": "ordered_boundary_cycles_world_m[0], because the sealed probe source produced that field by BFS component visitation rather than an edge walk",
            "tolerance_m": TOLERANCE_M,
        }
        result["source_blend_sha256_after"] = sha256_file(source_path)
        result["source_blend_unchanged"] = (
            result["source_blend_sha256_after"] == source_hash_before
        )
        failed = sorted(
            name for name, record in gates.items() if record.get("status") == "FAIL"
        )
        unexpected_failed = [
            name
            for name in failed
            if name != "historical_attempt03_sequential_interface_gate"
        ]
        result["gate_summary"] = {
            "gate_count": len(gates),
            "failed_gates": failed,
            "expected_historical_failure": "historical_attempt03_sequential_interface_gate",
            "unexpected_failed_gates": unexpected_failed,
            "all_remaining_preflight_gates_reconciled": not unexpected_failed,
        }
        result["status"] = (
            "PASS_WHOLE_PREFLIGHT_RECONCILED_ATTEMPT04_MAY_BE_PREPARED"
            if not unexpected_failed and result["source_blend_unchanged"]
            else "FAIL_WHOLE_PREFLIGHT_RECONCILIATION_REQUIRES_REVIEW"
        )
    except Exception as exc:
        result["status"] = "FAIL_DIAGNOSTIC_SETUP_OR_DEPENDENCY"
        result["diagnostic_failure"] = exception_record(exc)
        if source_path is not None and source_path.exists():
            result["source_blend_sha256_after"] = sha256_file(source_path)
            result["source_blend_unchanged"] = (
                result.get("source_blend_sha256_before")
                == result["source_blend_sha256_after"]
            )
    result["timestamp_complete_utc"] = utc_now()
    result["scope"]["body_asset_mutated"] = False
    result["scope"]["blend_saved"] = False
    write_package(output, result)
    print(json.dumps({"status": result["status"], "output": EXPECTED_OUTPUT_REL}, indent=2))
    return 0 if result["status"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
