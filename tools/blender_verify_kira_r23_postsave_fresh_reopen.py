#!/usr/bin/env python3
"""Deferred, fail-closed Kira R23 post-save verifier.

The shipped configuration is an intentionally unbound template.  This worker
cannot run unless a new append-only configuration binds one exact candidate,
its exact build evidence, and new output locations and is then invoked with
``--execute-fresh-reopen`` in a fresh Blender process.

The worker is read-only with respect to Blend files.  Poses, support proxies,
lights, and cameras exist only in memory.  Machine measurements and owner
visual judgment are deliberately separate evidence domains.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_postsave_fresh_reopen_verifier_preparation/"
    "KIRA_R23_POSTSAVE_VERIFIER_CONFIG_TEMPLATE.json"
)
EXECUTION_FLAG = "--execute-fresh-reopen"
BOUND_STATUS = "BOUND_NOT_RUN_EXPLICIT_VERIFICATION_AUTHORIZATION_REQUIRED"


class VerificationError(RuntimeError):
    """A fail-closed binding or machine-gate failure."""


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG.as_posix())
    parser.add_argument(EXECUTION_FLAG, action="store_true")
    return parser.parse_args(raw)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(raw: str | Path) -> Path:
    value = Path(str(raw))
    if value.is_absolute() or ".." in value.parts:
        raise VerificationError(f"unsafe project-relative path: {raw}")
    resolved = (ROOT / value).resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise VerificationError(f"path escaped project: {raw}") from exc
    return resolved


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise VerificationError(f"JSON root is not an object: {relative(path)}")
    return value


def require_binding(record: Mapping[str, Any], label: str) -> Path:
    required = ("path", "bytes", "sha256")
    missing = [key for key in required if record.get(key) in (None, "")]
    if missing:
        raise VerificationError(f"{label} binding is deferred/null: {missing}")
    path = project_path(str(record["path"]))
    if not path.is_file():
        raise VerificationError(f"{label} is absent: {relative(path)}")
    if path.stat().st_size != int(record["bytes"]):
        raise VerificationError(f"{label} byte-size mismatch")
    if sha256_file(path) != str(record["sha256"]).lower():
        raise VerificationError(f"{label} SHA-256 mismatch")
    return path


def verify_fixed_inputs(config: Mapping[str, Any]) -> dict[str, Any]:
    verified: dict[str, Any] = {}
    for label, record in config["fixed_inputs"].items():
        if record.get("sha256") in (None, ""):
            raise VerificationError(f"fixed input hash remains deferred: {label}")
        path = project_path(record["path"])
        if not path.is_file():
            raise VerificationError(f"fixed input absent: {label}")
        actual = {
            "path": relative(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        if actual["sha256"] != str(record["sha256"]).lower():
            raise VerificationError(f"fixed input hash mismatch: {label}")
        if record.get("bytes") is not None and actual["bytes"] != int(record["bytes"]):
            raise VerificationError(f"fixed input byte-size mismatch: {label}")
        verified[label] = actual
    return verified


def validate_bound_contract(
    config: Mapping[str, Any], explicit_execution: bool
) -> dict[str, Path]:
    if not explicit_execution:
        raise VerificationError("explicit --execute-fresh-reopen flag is required")
    if config.get("status") != BOUND_STATUS:
        raise VerificationError("configuration is an unbound template or has wrong status")
    if config.get("attempt_id") in (None, ""):
        raise VerificationError("bound attempt ID is required")
    execution = config.get("execution", {})
    if execution.get("enabled") is not True:
        raise VerificationError("execution remains disabled")
    if execution.get("fresh_blender_process_required") is not True:
        raise VerificationError("fresh-process requirement was weakened")
    candidate = require_binding(config["candidate_binding"], "candidate")
    build = require_binding(config["build_evidence_binding"], "build evidence")
    output = config["bound_output"]
    output_values = (output.get("evidence_directory"), output.get("owner_render_directory"))
    if any(value in (None, "") for value in output_values):
        raise VerificationError("output bindings remain deferred/null")
    evidence_dir = project_path(output_values[0])
    render_dir = project_path(output_values[1])
    if evidence_dir.exists() or render_dir.exists():
        raise VerificationError("append-only output path already exists")
    try:
        render_dir.relative_to(evidence_dir)
    except ValueError as exc:
        raise VerificationError("render directory must be inside evidence directory") from exc
    return {
        "candidate": candidate,
        "build_evidence": build,
        "evidence_dir": evidence_dir,
        "render_dir": render_dir,
    }


def verify_build_evidence_binding(
    config: Mapping[str, Any], paths: Mapping[str, Path]
) -> dict[str, Any]:
    evidence = read_json(paths["build_evidence"])
    candidate = evidence.get("candidate", {})
    expected = config["candidate_binding"]
    exact_candidate = (
        candidate.get("path") == expected["path"]
        and candidate.get("bytes") == expected["bytes"]
        and str(candidate.get("sha256", "")).lower() == str(expected["sha256"]).lower()
    )
    if not exact_candidate:
        raise VerificationError("build evidence does not bind the exact candidate")
    if not all(
        candidate.get(key) is expected_value
        for key, expected_value in {
            "inactive": True,
            "unassigned": True,
            "unpublished": True,
            "runtime_eligible": False,
            "owner_approved": False,
        }.items()
    ):
        raise VerificationError("candidate evidence lacks protected inactive flags")
    source = evidence.get("source_blend", {})
    sealed = config["fixed_inputs"]["r19_source_blend"]
    if (
        source.get("path") != sealed["path"]
        or source.get("sha256_before") != sealed["sha256"]
        or source.get("sha256_after") != sealed["sha256"]
        or source.get("unchanged") is not True
    ):
        raise VerificationError("build evidence does not preserve exact R19 source")
    operations = evidence.get("operations", {})
    forbidden_truth = (
        "source_blend_written",
        "render_performed",
        "export_performed",
        "runtime_mutation_performed",
        "candidate_activated",
    )
    if any(operations.get(key) is not False for key in forbidden_truth):
        raise VerificationError("author evidence reports a forbidden operation")
    return evidence


def write_new_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


def vector_record(value: Any) -> list[float]:
    return [float(value[index]) for index in range(3)]


def weight_map(obj: Any, vertex_index: int) -> dict[str, float]:
    return {
        obj.vertex_groups[item.group].name: float(item.weight)
        for item in obj.data.vertices[int(vertex_index)].groups
        if float(item.weight) > 0.0
    }


def weight_error(first: Mapping[str, float], second: Mapping[str, float]) -> float:
    keys = set(first).union(second)
    return max((abs(float(first.get(key, 0.0)) - float(second.get(key, 0.0))) for key in keys), default=0.0)


def reset_pose(rig: Any) -> None:
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()


def suspend_rig_action(rig: Any) -> None:
    """Prevent a saved active action from overriding explicit test poses."""
    if rig.animation_data is not None:
        rig.animation_data.action = None


def apply_pose(rig: Any, rotations: Mapping[str, Sequence[float]]) -> None:
    reset_pose(rig)
    for name, degrees in rotations.items():
        bone = rig.pose.bones.get(name)
        if bone is None:
            raise VerificationError(f"pose bone is absent: {name}")
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = tuple(math.radians(float(value)) for value in degrees)


def evaluated_bmesh(obj: Any, bpy: Any, bmesh: Any) -> Any:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bmesh.ops.transform(bm, matrix=evaluated.matrix_world, verts=bm.verts)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.normal_update()
    finally:
        evaluated.to_mesh_clear()
    return bm


def face_geometry_signature(face: Any, precision: int = 9) -> str:
    points = sorted(
        [[round(float(value), precision) for value in vertex.co] for vertex in face.verts]
    )
    return canonical_sha256(points)


def exact_intersections(obj: Any, bpy: Any, bmesh: Any, exact_module: Any) -> dict[str, Any]:
    bm = evaluated_bmesh(obj, bpy, bmesh)
    try:
        report = exact_module.exact_nonadjacent_intersection_report(
            bm, include_pair_details=True
        )
        genuine = [
            record
            for record in report["pairs"]
            if record["genuine_positive_area_or_segment_penetration"] is True
        ]
        index_pairs = sorted(
            [sorted(map(int, record["face_indices"])) for record in genuine]
        )
        geometry_pairs = sorted(
            [
                sorted(
                    face_geometry_signature(bm.faces[int(index)])
                    for index in record["face_indices"]
                )
                for record in genuine
            ]
        )
        return {
            "exact_report": report,
            "genuine_index_pairs": index_pairs,
            "genuine_geometry_pairs": geometry_pairs,
            "genuine_geometry_pair_sha256": canonical_sha256(geometry_pairs),
        }
    finally:
        bm.free()


def mesh_topology(obj: Any, topology: Any) -> dict[str, Any]:
    faces = [tuple(map(int, polygon.vertices)) for polygon in obj.data.polygons]
    whole = topology.topology_record(faces, range(len(faces)))
    edge_faces = topology.edge_face_map(faces)
    return {
        "faces": faces,
        "whole": whole,
        "nonmanifold_edge_count": sum(len(values) != 2 for values in edge_faces.values()),
        "edge_faces": edge_faces,
    }


def uv_values_at_vertex(obj: Any, vertex_index: int, face_filter: set[int] | None = None) -> dict[str, list[list[float]]]:
    result: dict[str, list[list[float]]] = {}
    for layer in obj.data.uv_layers:
        values: list[list[float]] = []
        for polygon in obj.data.polygons:
            if face_filter is not None and int(polygon.index) not in face_filter:
                continue
            for loop_index in polygon.loop_indices:
                if int(obj.data.loops[loop_index].vertex_index) == int(vertex_index):
                    uv = layer.data[loop_index].uv
                    values.append([float(uv.x), float(uv.y)])
        result[layer.name] = sorted(values)
    return result


def face_state_signature(obj: Any, polygon: Any) -> str:
    loops = []
    for loop_index in polygon.loop_indices:
        vertex_index = int(obj.data.loops[loop_index].vertex_index)
        loops.append(
            {
                "coordinate": vector_record(obj.data.vertices[vertex_index].co),
                "weights": sorted(weight_map(obj, vertex_index).items()),
                "uv": [
                    [layer.name, *[float(value) for value in layer.data[loop_index].uv]]
                    for layer in obj.data.uv_layers
                ],
            }
        )
    return canonical_sha256(
        {
            "material_index": int(polygon.material_index),
            "smooth": bool(polygon.use_smooth),
            "loops": loops,
        }
    )


def source_snapshot(
    config: Mapping[str, Any],
    bpy: Any,
    bmesh: Any,
    preflight: Any,
    actions: Any,
    exact_module: Any,
    topology: Any,
) -> dict[str, Any]:
    names = config["objects"]
    body = bpy.data.objects.get(names["r19_body"])
    rig = bpy.data.objects.get(names["rig"])
    if body is None or rig is None:
        raise VerificationError("exact R19 source body or rig is absent")
    suspend_rig_action(rig)
    reset_pose(rig)
    bpy.context.scene.frame_set(0)
    preflight_json = read_json(project_path(config["fixed_inputs"]["passed_preflight"]["path"]))
    seam_order = [int(value) for value in preflight_json["expanded_r19_mask"]["ordered_outer_seam"]]
    if canonical_sha256(seam_order) != config["inherited_r19_baseline"]["ordered_outer_seam_sha256"]:
        raise VerificationError("R19 ordered seam record drifted")
    seam = {
        int(index): {
            "coordinate": vector_record(body.data.vertices[int(index)].co),
            "weights": weight_map(body, int(index)),
            "uv": uv_values_at_vertex(body, int(index)),
        }
        for index in seam_order
    }
    nonbody = [
        {
            "object": obj.name,
            "mesh": obj.data.name,
            "full_state_sha256": preflight.mesh_full_state_sha256(obj),
        }
        for obj in sorted(bpy.data.objects, key=lambda value: value.name)
        if obj != body and obj.type == "MESH"
    ]
    materials = [preflight.material_graph_record(material) for material in body.data.materials]
    topology_record = mesh_topology(body, topology)
    exact = exact_intersections(body, bpy, bmesh, exact_module)
    face_states = Counter(face_state_signature(body, face) for face in body.data.polygons)
    return {
        "seam_order": seam_order,
        "seam": seam,
        "topology": {key: value for key, value in topology_record.items() if key not in {"faces", "edge_faces"}},
        "exact_intersections": exact,
        "face_state_counter": dict(face_states),
        "nonbody_records": nonbody,
        "nonbody_ledger_sha256": canonical_sha256(nonbody),
        "material_records": materials,
        "material_ledger_sha256": canonical_sha256(materials),
        "rig_rest_sha256": preflight.rig_rest_sha256(rig),
        "actions_sha256": actions.actions_sha256(bpy.data.actions),
    }


def patch_face_indices(body: Any, material_name: str) -> tuple[set[int], int]:
    slots = [index for index, material in enumerate(body.data.materials) if material and material.name == material_name]
    if len(slots) != 1:
        raise VerificationError("candidate lacks exactly one named patch material slot")
    material_index = slots[0]
    faces = {
        int(face.index)
        for face in body.data.polygons
        if int(face.material_index) == material_index
    }
    return faces, material_index


def candidate_flags(body: Any) -> dict[str, bool]:
    values = {
        "inactive": bool(body.get("r23_inactive", False)),
        "unassigned": bool(body.get("r23_unassigned", False)),
        "unpublished": bool(body.get("r23_unpublished", False)),
        "runtime_eligible_false": body.get("r23_runtime_eligible") is False,
        "owner_approved_false": body.get("r23_owner_approved") is False,
        "bald_low_resource": bool(body.get("r23_bald_low_resource_body", False)),
    }
    values["passed"] = all(values.values())
    return values


def euclidean(first: Sequence[float], second: Sequence[float]) -> float:
    return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(first, second)))


def is_cyclic_equal(values: Sequence[int], expected: Sequence[int]) -> bool:
    if len(values) != len(expected):
        return False
    doubled = list(expected) + list(expected)
    return any(doubled[offset : offset + len(values)] == list(values) for offset in range(len(values)))


def seam_continuity(
    body: Any,
    source: Mapping[str, Any],
    patch_faces: set[int],
    topology: Any,
    thresholds: Mapping[str, float],
) -> dict[str, Any]:
    faces = [tuple(map(int, polygon.vertices)) for polygon in body.data.polygons]
    patch_topology = topology.topology_record(faces, patch_faces)
    cycles = topology.ordered_boundary_cycles(topology.boundary_edges_for_region(faces, patch_faces))
    if len(cycles) != 1:
        raise VerificationError("replacement patch does not have one seam cycle")
    candidate_cycle = cycles[0]
    source_order = list(source["seam_order"])
    source_by_index = source["seam"]
    available = set(source_order)
    matched: dict[int, int] = {}
    position_errors = []
    for candidate_index in candidate_cycle:
        coordinate = vector_record(body.data.vertices[candidate_index].co)
        best = min(available, key=lambda index: euclidean(coordinate, source_by_index[index]["coordinate"]))
        error = euclidean(coordinate, source_by_index[best]["coordinate"])
        matched[candidate_index] = best
        available.remove(best)
        position_errors.append(error)
    mapped_order = [matched[index] for index in candidate_cycle]
    ordered = is_cyclic_equal(mapped_order, source_order) or is_cyclic_equal(mapped_order, list(reversed(source_order)))
    weight_errors = [
        weight_error(weight_map(body, current), source_by_index[original]["weights"])
        for current, original in matched.items()
    ]
    edge_faces = topology.edge_face_map(faces)
    boundary_edges = topology.boundary_edges_for_region(faces, patch_faces)
    normal_dots = []
    for edge in boundary_edges:
        incident = edge_faces[edge]
        patch_incident = [index for index in incident if index in patch_faces]
        retained_incident = [index for index in incident if index not in patch_faces]
        if len(patch_incident) != 1 or len(retained_incident) != 1:
            raise VerificationError("seam edge lacks one patch and one retained face")
        first = body.data.polygons[patch_incident[0]].normal
        second = body.data.polygons[retained_incident[0]].normal
        normal_dots.append(float(first.dot(second)))
    tangent_dots = []
    for offset, current in enumerate(candidate_cycle):
        previous = candidate_cycle[(offset - 1) % len(candidate_cycle)]
        following = candidate_cycle[(offset + 1) % len(candidate_cycle)]
        current_tangent = body.data.vertices[following].co - body.data.vertices[previous].co
        source_current = matched[current]
        source_offset = source_order.index(source_current)
        source_previous = source_order[(source_offset - 1) % len(source_order)]
        source_following = source_order[(source_offset + 1) % len(source_order)]
        from mathutils import Vector
        source_tangent = Vector(source_by_index[source_following]["coordinate"]) - Vector(source_by_index[source_previous]["coordinate"])
        if current_tangent.length == 0.0 or source_tangent.length == 0.0:
            tangent_dots.append(0.0)
        else:
            tangent_dots.append(abs(float(current_tangent.normalized().dot(source_tangent.normalized()))))
    patch_uv_errors: list[float] = []
    retained_uv_errors: list[float] = []
    for current, original in matched.items():
        expected_layers = source_by_index[original]["uv"]
        current_patch = uv_values_at_vertex(body, current, patch_faces)
        current_retained = uv_values_at_vertex(body, current, set(range(len(faces))).difference(patch_faces))
        for layer, expected_values in expected_layers.items():
            if not expected_values:
                continue
            for value in current_patch.get(layer, []):
                patch_uv_errors.append(min(euclidean(value, expected) for expected in expected_values))
            for value in current_retained.get(layer, []):
                retained_uv_errors.append(min(euclidean(value, expected) for expected in expected_values))
    maximum_position = max(position_errors, default=float("inf"))
    maximum_weight = max(weight_errors, default=float("inf"))
    minimum_normal = min(normal_dots, default=-1.0)
    minimum_tangent = min(tangent_dots, default=-1.0)
    maximum_patch_uv = max(patch_uv_errors, default=0.0)
    maximum_retained_uv = max(retained_uv_errors, default=0.0)
    checks = {
        "count_exact": len(candidate_cycle) == len(source_order),
        "cyclic_order_exact": ordered,
        "position_continuity": maximum_position <= thresholds["maximum_seam_position_error_m"],
        "weight_continuity": maximum_weight <= thresholds["maximum_seam_weight_error"],
        "normal_continuity": minimum_normal >= thresholds["minimum_patch_retained_normal_dot"],
        "tangent_continuity": minimum_tangent >= thresholds["minimum_seam_tangent_dot"],
        "patch_uv_continuity": maximum_patch_uv <= thresholds["maximum_patch_retained_uv_distance"],
        "retained_uv_preservation": maximum_retained_uv <= thresholds["maximum_patch_retained_uv_distance"],
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "candidate_cycle": candidate_cycle,
        "mapped_source_cycle": mapped_order,
        "maximum_position_error_m": maximum_position,
        "maximum_weight_error": maximum_weight,
        "minimum_patch_retained_normal_dot": minimum_normal,
        "minimum_tangent_dot": minimum_tangent,
        "maximum_patch_uv_distance": maximum_patch_uv,
        "maximum_retained_uv_distance": maximum_retained_uv,
        "patch_topology": patch_topology,
    }


def patch_weights(
    body: Any, patch_faces: set[int], expected: Mapping[str, Any], bpy: Any
) -> dict[str, Any]:
    vertices = sorted({int(value) for face in patch_faces for value in body.data.polygons[face].vertices})
    rig = bpy.data.objects.get("Kira_R19_BlackProject_Native_188_Rig")
    rig_bones = {bone.name for bone in rig.data.bones} if rig is not None else set()
    rows = []
    for index in vertices:
        weights = weight_map(body, index)
        rows.append(
            {
                "vertex": index,
                "positive_count": len(weights),
                "sum": sum(weights.values()),
                "unknown_groups": sorted(set(weights).difference(rig_bones)),
            }
        )
    checks = {
        "maximum_four": all(row["positive_count"] <= expected["maximum_positive_weights_per_patch_vertex"] for row in rows),
        "normalized": all(expected["minimum_positive_weight_sum"] <= row["sum"] <= expected["maximum_positive_weight_sum"] for row in rows),
        "native_groups_only": all(not row["unknown_groups"] for row in rows),
    }
    return {
        "vertex_count": len(vertices),
        "minimum_sum": min((row["sum"] for row in rows), default=0.0),
        "maximum_sum": max((row["sum"] for row in rows), default=0.0),
        "maximum_positive_count": max((row["positive_count"] for row in rows), default=0),
        "unknown_group_rows": [row for row in rows if row["unknown_groups"]],
        "checks": checks,
        "passed": all(checks.values()),
    }


def candidate_ledgers(
    body: Any,
    rig: Any,
    preflight: Any,
    actions: Any,
    existing_count: int,
    bpy: Any,
) -> dict[str, Any]:
    nonbody = [
        {
            "object": obj.name,
            "mesh": obj.data.name,
            "full_state_sha256": preflight.mesh_full_state_sha256(obj),
        }
        for obj in sorted(bpy.data.objects, key=lambda value: value.name)
        if obj != body and obj.type == "MESH"
    ]
    materials = [
        preflight.material_graph_record(material)
        for material in list(body.data.materials)[:existing_count]
    ]
    return {
        "nonbody_count": len(nonbody),
        "nonbody_ledger_sha256": canonical_sha256(nonbody),
        "existing_material_count": len(materials),
        "existing_material_ledger_sha256": canonical_sha256(materials),
        "rig_rest_sha256": preflight.rig_rest_sha256(rig),
        "actions_sha256": actions.actions_sha256(bpy.data.actions),
    }


def retained_surface_subset(body: Any, patch_faces: set[int], source: Mapping[str, Any], expected_missing: int) -> dict[str, Any]:
    candidate = Counter(
        face_state_signature(body, polygon)
        for polygon in body.data.polygons
        if int(polygon.index) not in patch_faces
    )
    source_counter = Counter(source["face_state_counter"])
    excess = candidate - source_counter
    missing = source_counter - candidate
    return {
        "candidate_retained_face_count": sum(candidate.values()),
        "source_face_count": sum(source_counter.values()),
        "excess_face_state_count": sum(excess.values()),
        "missing_source_face_state_count": sum(missing.values()),
        "expected_replaced_source_face_count": expected_missing,
        "passed": not excess and sum(missing.values()) == expected_missing,
    }


def edge_lengths(points: Sequence[Any], edges: Iterable[tuple[int, int]]) -> dict[tuple[int, int], float]:
    return {edge: float((points[edge[0]] - points[edge[1]]).length) for edge in edges}


def evaluated_points(body: Any, bpy: Any) -> list[Any]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    try:
        return [evaluated.matrix_world @ vertex.co.copy() for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def ratio_maximum(current: Mapping[tuple[int, int], float], neutral: Mapping[tuple[int, int], float]) -> float:
    ratios = []
    for edge, base in neutral.items():
        if base <= 1e-12:
            continue
        ratios.append(current[edge] / base)
    return max(ratios, default=1.0)


def contact_proxy(
    points: Sequence[Any],
    support_kind: str | None,
    support_points: Sequence[Any] | None = None,
) -> dict[str, Any] | None:
    if support_kind is None:
        return None
    candidates = list(
        points
        if support_kind == "bed_plane"
        else (support_points if support_points else points)
    )
    if support_kind in {"seat", "toilet_seat_proxy"} and candidates:
        posterior_threshold = sorted(float(point.y) for point in candidates)[
            max(0, int(len(candidates) * 0.35) - 1)
        ]
        candidates = [point for point in candidates if float(point.y) <= posterior_threshold]
    z_values = sorted(float(point.z) for point in candidates)
    if not z_values:
        raise VerificationError("evaluated body has no points")
    plane_z = z_values[0] - 0.00025
    distances = [abs(float(point.z) - plane_z) for point in candidates]
    return {
        "support_kind": support_kind,
        "method": "derived_external_surface_contact_proxy",
        "support_plane_z_m": plane_z,
        "minimum_absolute_distance_m": min(distances),
        "contact_vertex_count_within_0_025m": sum(value <= 0.025 for value in distances),
        "deep_penetration_vertex_count_below_0_025m": sum(float(point.z) < plane_z - 0.025 for point in candidates),
        "candidate_contact_point_count": len(candidates),
        "truth_limit": "This is an external support-plane proxy, not comfort, continence, toileting, or biological-function evidence.",
    }


def deformation_series(
    config: Mapping[str, Any],
    body: Any,
    rig: Any,
    patch_faces: set[int],
    seam_cycle: Sequence[int],
    neutral_intersections: Mapping[str, Any],
    bpy: Any,
    bmesh: Any,
    exact_module: Any,
    topology: Any,
) -> tuple[dict[str, Any], dict[str, list[Any]]]:
    faces = [tuple(map(int, polygon.vertices)) for polygon in body.data.polygons]
    patch_edges = {
        edge
        for face_index in patch_faces
        for edge in topology.face_edges(faces[face_index])
    }
    seam_edges = {
        tuple(sorted((seam_cycle[index], seam_cycle[(index + 1) % len(seam_cycle)])))
        for index in range(len(seam_cycle))
    }
    apply_pose(rig, {})
    bpy.context.view_layer.update()
    neutral_points = evaluated_points(body, bpy)
    neutral_patch = edge_lengths(neutral_points, patch_edges)
    neutral_seam = edge_lengths(neutral_points, seam_edges)
    neutral_pairs = {tuple(pair) for pair in neutral_intersections["genuine_index_pairs"]}
    patch_vertices = sorted({value for edge in patch_edges for value in edge})
    threshold = config["continuity_thresholds"]
    records: dict[str, Any] = {}
    points_by_pose: dict[str, list[Any]] = {}
    for pose in config["poses"]:
        apply_pose(rig, pose["rotations_degrees"])
        bpy.context.view_layer.update()
        points = evaluated_points(body, bpy)
        points_by_pose[pose["id"]] = points
        intersections = exact_intersections(body, bpy, bmesh, exact_module)
        pairs = {tuple(pair) for pair in intersections["genuine_index_pairs"]}
        new_pairs = sorted([list(pair) for pair in pairs.difference(neutral_pairs)])
        patch_pairs = sorted([list(pair) for pair in pairs if any(index in patch_faces for index in pair)])
        patch_stretch = ratio_maximum(edge_lengths(points, patch_edges), neutral_patch)
        seam_stretch = ratio_maximum(edge_lengths(points, seam_edges), neutral_seam)
        support_points = [points[index] for index in patch_vertices]
        contact = contact_proxy(points, pose.get("support"), support_points)
        checks = {
            "vertex_count_stable": len(points) == len(neutral_points),
            "zero_new_exact_pairs": len(new_pairs) <= threshold["maximum_new_exact_intersection_pairs_per_pose"],
            "zero_patch_exact_pairs": len(patch_pairs) <= threshold["maximum_patch_involving_exact_intersection_pairs"],
            "patch_edge_stretch_bounded": patch_stretch <= threshold["maximum_pose_patch_edge_stretch_ratio"],
            "seam_edge_stretch_bounded": seam_stretch <= threshold["maximum_pose_seam_edge_stretch_ratio"],
            "support_contact_proxy": contact is None or (
                contact["minimum_absolute_distance_m"] <= threshold["contact_plane_tolerance_m"]
                and contact["contact_vertex_count_within_0_025m"] > 0
                and contact["deep_penetration_vertex_count_below_0_025m"] == 0
            ),
        }
        records[pose["id"]] = {
            "rotations_degrees": pose["rotations_degrees"],
            "bounds_world_m": {
                "minimum": [min(float(point[axis]) for point in points) for axis in range(3)],
                "maximum": [max(float(point[axis]) for point in points) for axis in range(3)],
            },
            "evaluated_position_sha256": canonical_sha256([vector_record(point) for point in points]),
            "exact_genuine_pair_count": len(pairs),
            "new_exact_pairs_vs_candidate_neutral": new_pairs,
            "patch_involving_exact_pairs": patch_pairs,
            "maximum_patch_edge_stretch_ratio": patch_stretch,
            "maximum_seam_edge_stretch_ratio": seam_stretch,
            "contact_proxy": contact,
            "checks": checks,
            "passed": all(checks.values()),
        }
    apply_pose(rig, {})
    bpy.context.view_layer.update()
    return records, points_by_pose


def configure_render_scene(bpy: Any) -> tuple[Any, Any]:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.008, 0.012, 0.018)
    camera_data = bpy.data.cameras.new("R23_Verifier_Temporary_Camera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R23_Verifier_Temporary_Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    for name, location, energy in (
        ("R23_Verifier_Key", (-3.0, -4.0, 5.0), 1100.0),
        ("R23_Verifier_Fill", (3.0, -2.0, 3.0), 700.0),
        ("R23_Verifier_Rim", (0.0, 3.0, 4.5), 900.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = 3.0
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = location
    return scene, camera


def view_location(view: str, center: Any, low: Any, high: Any, distance: float) -> tuple[Any, Any]:
    from mathutils import Vector
    if view == "front":
        return Vector((center.x, center.y - distance, center.z)), center
    if view == "rear":
        return Vector((center.x, center.y + distance, center.z)), center
    if view == "left_side":
        return Vector((center.x - distance, center.y, center.z)), center
    if view == "right_side":
        return Vector((center.x + distance, center.y, center.z)), center
    if view == "left_oblique":
        return Vector((center.x - distance * 0.65, center.y - distance, center.z)), center
    if view == "right_oblique":
        return Vector((center.x + distance * 0.65, center.y - distance, center.z)), center
    if view == "inferior_front":
        target = Vector((center.x, center.y, low.z + (high.z - low.z) * 0.39))
        return Vector((center.x, center.y - distance * 0.55, low.z - distance * 0.20)), target
    if view == "inferior_rear":
        target = Vector((center.x, center.y, low.z + (high.z - low.z) * 0.38))
        return Vector((center.x, center.y + distance * 0.55, low.z - distance * 0.20)), target
    if view == "top":
        return Vector((center.x, center.y, high.z + distance)), center
    raise VerificationError(f"unknown render view: {view}")


def create_temporary_support_proxy(
    bpy: Any,
    points: Sequence[Any],
    support_kind: str | None,
    support_points: Sequence[Any] | None = None,
) -> list[Any]:
    """Create visible in-memory context for contact views; never save it."""
    if support_kind is None:
        return []
    from mathutils import Vector

    contact = contact_proxy(points, support_kind, support_points)
    if contact is None:
        return []
    context_points = list(support_points if support_points else points)
    low = Vector([min(float(point[axis]) for point in context_points) for axis in range(3)])
    high = Vector([max(float(point[axis]) for point in context_points) for axis in range(3)])
    center = (low + high) * 0.5
    width = max(float(high.x - low.x), 0.35)
    depth = max(float(high.y - low.y), 0.35)
    plane_z = float(contact["support_plane_z_m"])
    material = bpy.data.materials.get("R23_Verifier_Temporary_Support_Material")
    if material is None:
        material = bpy.data.materials.new("R23_Verifier_Temporary_Support_Material")
        material.diffuse_color = (0.12, 0.16, 0.20, 1.0)
    created = []
    if support_kind == "toilet_seat_proxy":
        bpy.ops.mesh.primitive_torus_add(
            major_radius=max(width * 0.31, 0.12),
            minor_radius=max(width * 0.045, 0.022),
            major_segments=48,
            minor_segments=12,
            location=(center.x, center.y, plane_z - 0.018),
        )
        seat = bpy.context.object
        seat.name = "R23_Verifier_Temporary_Toilet_Seat_Proxy"
        seat.scale.y = max(0.72, depth / width)
        seat.data.materials.append(material)
        created.append(seat)
        return created
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(center.x, center.y, plane_z - 0.04),
    )
    support = bpy.context.object
    support.name = (
        "R23_Verifier_Temporary_Bed_Proxy"
        if support_kind == "bed_plane"
        else "R23_Verifier_Temporary_Seat_Proxy"
    )
    support.dimensions = (
        width * (1.35 if support_kind == "bed_plane" else 1.10),
        depth * (1.35 if support_kind == "bed_plane" else 0.72),
        0.08,
    )
    support.data.materials.append(material)
    created.append(support)
    return created


def remove_temporary_support_proxies(bpy: Any, objects: Sequence[Any]) -> None:
    for obj in objects:
        mesh = obj.data if getattr(obj, "type", None) == "MESH" else None
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def render_owner_package(
    config: Mapping[str, Any], body: Any, rig: Any, render_dir: Path, bpy: Any
) -> list[dict[str, Any]]:
    from mathutils import Vector
    scene, camera = configure_render_scene(bpy)
    poses = {pose["id"]: pose for pose in config["poses"]}
    patch_faces, _material_index = patch_face_indices(
        body, config["objects"]["r23_patch_material"]
    )
    patch_vertices = sorted(
        {
            int(vertex)
            for face_index in patch_faces
            for vertex in body.data.polygons[face_index].vertices
        }
    )
    records = []
    for item in config["owner_render_plan"]:
        pose = poses[item["pose"]]
        apply_pose(rig, pose["rotations_degrees"])
        bpy.context.view_layer.update()
        points = evaluated_points(body, bpy)
        render_support_points = (
            None
            if pose.get("support") == "bed_plane"
            else [points[index] for index in patch_vertices]
        )
        support_objects = create_temporary_support_proxy(
            bpy,
            points,
            pose.get("support"),
            render_support_points,
        )
        low = Vector([min(float(point[axis]) for point in points) for axis in range(3)])
        high = Vector([max(float(point[axis]) for point in points) for axis in range(3)])
        center = (low + high) * 0.5
        height = max(high.z - low.z, 0.01)
        width = max(high.x - low.x, 0.01)
        depth = max(high.y - low.y, 0.01)
        distance = max(height, width, depth) * 2.3 + 1.0
        location, target = view_location(item["view"], center, low, high, distance)
        initial_target = target.copy()
        framing = item["framing"]
        if framing in {"pelvis", "close_pelvis"}:
            target = Vector((center.x, center.y, low.z + height * 0.40))
            scale = height * (0.44 if framing == "pelvis" else 0.30)
        elif framing in {"hand_close", "hands_close"}:
            target_bones = item.get("target_bones", [])
            bone_points = []
            for bone_name in target_bones:
                bone = rig.pose.bones.get(bone_name)
                if bone is None:
                    raise VerificationError(f"render target bone is absent: {bone_name}")
                bone_points.append(rig.matrix_world @ bone.head)
            if not bone_points:
                raise VerificationError(f"hand close render lacks target bones: {item['id']}")
            target = sum(bone_points, Vector()) / len(bone_points)
            scale = height * (0.24 if framing == "hand_close" else 0.43)
        elif framing == "upper_body":
            target = Vector((center.x, center.y, low.z + height * 0.72))
            scale = height * 0.66
        elif framing == "distance":
            scale = height * 1.55
        else:
            scale = height * 1.12
        location += target - initial_target
        camera.location = location
        camera.data.ortho_scale = scale
        camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
        destination = render_dir / f"{item['id']}.png"
        scene.render.filepath = str(destination)
        try:
            bpy.ops.render.render(write_still=True)
            if not destination.is_file() or destination.stat().st_size <= 1024:
                raise VerificationError(f"render missing or too small: {item['id']}")
            with destination.open("rb") as handle:
                if handle.read(8) != b"\x89PNG\r\n\x1a\n":
                    raise VerificationError(f"render is not a readable PNG signature: {item['id']}")
        finally:
            remove_temporary_support_proxies(bpy, support_objects)
        records.append(
            {
                "id": item["id"],
                "pose": item["pose"],
                "view": item["view"],
                "framing": framing,
                "path": relative(destination),
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
            }
        )
    apply_pose(rig, {})
    bpy.context.view_layer.update()
    return records


def output_manifest(directory: Path, excluded_name: str) -> dict[str, Any]:
    records = []
    for path in sorted(value for value in directory.rglob("*") if value.is_file() and value.name != excluded_name):
        records.append(
            {
                "path": relative(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {"schema_version": 1, "files": records, "file_count": len(records)}


def run(config_path: Path, explicit_execution: bool) -> int:
    config = read_json(config_path)
    paths = validate_bound_contract(config, explicit_execution)
    fixed = verify_fixed_inputs(config)
    build_evidence = verify_build_evidence_binding(config, paths)
    source_path = project_path(config["fixed_inputs"]["r19_source_blend"]["path"])
    source_before = {"bytes": source_path.stat().st_size, "sha256": sha256_file(source_path)}
    candidate_before = {"bytes": paths["candidate"].stat().st_size, "sha256": sha256_file(paths["candidate"])}
    paths["evidence_dir"].mkdir(parents=True, exist_ok=False)
    paths["render_dir"].mkdir(parents=False, exist_ok=False)
    try:
        import bmesh
        import bpy
        from tools import blender_exact_mesh_intersections as exact_module
        from tools import blender_preflight_kira_r23_cc0_afes_expanded_mask as preflight
        from tools import kira_r23_cc0_afes_preflight_core as topology
        from tools import kira_r23_blender51_action_serializer as actions

        if bpy.data.filepath:
            raise VerificationError("worker was not launched from factory-empty Blender state")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)
        source = source_snapshot(
            config, bpy, bmesh, preflight, actions, exact_module, topology
        )
        expected_baseline = config["inherited_r19_baseline"]["neutral_exact_genuine_nonadjacent_intersection_pair_count"]
        if source["exact_intersections"]["exact_report"]["exact_genuine_penetration_pair_count"] != expected_baseline:
            raise VerificationError("fresh R19 exact-intersection baseline drifted")

        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.wm.open_mainfile(filepath=str(paths["candidate"]), load_ui=False)
        names = config["objects"]
        body = bpy.data.objects.get(names["r23_body"])
        rig = bpy.data.objects.get(names["rig"])
        if body is None or rig is None:
            raise VerificationError("exact candidate body or native rig is absent")
        suspend_rig_action(rig)
        apply_pose(rig, {})
        bpy.context.scene.frame_set(0)
        bpy.context.view_layer.update()
        patch_faces, patch_material_index = patch_face_indices(body, names["r23_patch_material"])
        candidate_topology = mesh_topology(body, topology)
        patch_topology = topology.topology_record(candidate_topology["faces"], patch_faces)
        expected = config["expected_candidate_structure"]
        structural_checks = {
            "vertices": len(body.data.vertices) == expected["body_vertices"],
            "edges": len(body.data.edges) == expected["body_edges"],
            "faces": len(body.data.polygons) == expected["body_faces"],
            "whole_component": candidate_topology["whole"]["component_count"] == expected["whole_body_components"],
            "whole_boundary": candidate_topology["whole"]["boundary_edge_count"] == expected["whole_body_boundary_edges"],
            "whole_nonmanifold": candidate_topology["nonmanifold_edge_count"] == expected["whole_body_nonmanifold_edges"],
            "patch_vertices": patch_topology["vertex_count"] == expected["replacement_patch_vertices"],
            "patch_faces": patch_topology["face_count"] == expected["replacement_patch_faces"],
            "patch_edges": patch_topology["edge_count"] == expected["replacement_patch_edges"],
            "patch_components": patch_topology["component_count"] == expected["replacement_patch_components"],
            "patch_boundary_cycles": patch_topology["boundary_cycle_count"] == expected["replacement_patch_boundary_cycles"],
            "patch_boundary_vertices": patch_topology["boundary_cycle_lengths"] == [expected["replacement_patch_boundary_vertices"]],
            "patch_euler": patch_topology["euler_characteristic"] == expected["replacement_patch_euler_characteristic"],
        }
        candidate_exact = exact_intersections(body, bpy, bmesh, exact_module)
        candidate_pairs = {tuple(pair) for pair in candidate_exact["genuine_index_pairs"]}
        patch_pairs = sorted([list(pair) for pair in candidate_pairs if any(index in patch_faces for index in pair)])
        source_geometry_pairs = Counter(tuple(pair) for pair in source["exact_intersections"]["genuine_geometry_pairs"])
        candidate_geometry_pairs = Counter(tuple(pair) for pair in candidate_exact["genuine_geometry_pairs"])
        new_geometry_pairs = candidate_geometry_pairs - source_geometry_pairs
        intersections = {
            "r19_neutral": source["exact_intersections"],
            "r23_neutral": candidate_exact,
            "new_geometry_pair_count_vs_r19": sum(new_geometry_pairs.values()),
            "new_geometry_pairs_vs_r19": [list(pair) for pair in sorted(new_geometry_pairs.elements())],
            "patch_involving_pairs": patch_pairs,
            "checks": {
                "candidate_not_above_inherited_count": len(candidate_pairs) <= expected_baseline,
                "no_new_geometry_bound_pair": not new_geometry_pairs,
                "zero_patch_involving_pair": not patch_pairs,
            },
        }
        continuity = seam_continuity(body, source, patch_faces, topology, config["continuity_thresholds"])
        weights = patch_weights(body, patch_faces, expected, bpy)
        ledgers = candidate_ledgers(
            body,
            rig,
            preflight,
            actions,
            expected["existing_body_material_count"],
            bpy,
        )
        frozen = config["frozen_r19_ledgers"]
        ledger_checks = {
            "nonbody_count": ledgers["nonbody_count"] == expected["nonbody_mesh_object_count"],
            "nonbody_hash": ledgers["nonbody_ledger_sha256"] == frozen["nonbody_mesh_ledger_sha256"],
            "existing_material_count": ledgers["existing_material_count"] == expected["existing_body_material_count"],
            "existing_material_hash": ledgers["existing_material_ledger_sha256"] == frozen["existing_body_material_ledger_sha256"],
            "total_material_count": len(body.data.materials) == expected["total_body_material_count"],
            "rig_rest_hash": ledgers["rig_rest_sha256"] == frozen["rig_rest_structure_sha256"],
            "actions_hash": ledgers["actions_sha256"] == frozen["actions_sha256"],
        }
        retained = retained_surface_subset(
            body,
            patch_faces,
            source,
            config["inherited_r19_baseline"]["selected_face_count"],
        )
        flags = candidate_flags(body)
        poses, _points = deformation_series(
            config,
            body,
            rig,
            patch_faces,
            continuity["candidate_cycle"],
            candidate_exact,
            bpy,
            bmesh,
            exact_module,
            topology,
        )
        pre_render_gate_groups = {
            "candidate_flags": flags["passed"],
            "structure": all(structural_checks.values()),
            "intersections": all(intersections["checks"].values()),
            "continuity": continuity["passed"],
            "weights": weights["passed"],
            "frozen_ledgers": all(ledger_checks.values()),
            "retained_surface": retained["passed"],
            "deformation": all(record["passed"] for record in poses.values()),
        }
        if not all(pre_render_gate_groups.values()):
            raise VerificationError(f"machine gate failed before rendering: {pre_render_gate_groups}")
        renders = render_owner_package(config, body, rig, paths["render_dir"], bpy)
        expected_render_ids = [item["id"] for item in config["owner_render_plan"]]
        render_checks = {
            "count_exact": len(renders) == len(expected_render_ids),
            "ids_exact": [item["id"] for item in renders] == expected_render_ids,
            "all_png_readable_nonempty": all(item["bytes"] > 1024 for item in renders),
        }
        source_after = {"bytes": source_path.stat().st_size, "sha256": sha256_file(source_path)}
        candidate_after = {"bytes": paths["candidate"].stat().st_size, "sha256": sha256_file(paths["candidate"])}
        immutability = {
            "source_before": source_before,
            "source_after": source_after,
            "candidate_before": candidate_before,
            "candidate_after": candidate_after,
            "source_unchanged": source_before == source_after,
            "candidate_unchanged": candidate_before == candidate_after,
        }
        final_checks = {
            **pre_render_gate_groups,
            "renders": all(render_checks.values()),
            "source_immutable": immutability["source_unchanged"],
            "candidate_immutable": immutability["candidate_unchanged"],
        }
        if not all(final_checks.values()):
            raise VerificationError(f"final machine gate failed: {final_checks}")
        machine = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_POSTSAVE_FRESH_REOPEN_MACHINE_VERIFICATION",
            "created_utc": utc_now(),
            "status": "MACHINE_GATES_PASS_OWNER_VISUAL_DECISION_REQUIRED",
            "config": {"path": relative(config_path), "sha256": sha256_file(config_path)},
            "fixed_inputs": fixed,
            "candidate_binding": config["candidate_binding"],
            "build_evidence_binding": config["build_evidence_binding"],
            "build_evidence_status": build_evidence.get("status"),
            "factory_startup_source_then_candidate_reopen": True,
            "candidate_flags": flags,
            "structural_checks": structural_checks,
            "whole_topology": candidate_topology["whole"],
            "patch_topology": patch_topology,
            "patch_material_index": patch_material_index,
            "intersections": intersections,
            "continuity": continuity,
            "patch_weights": weights,
            "ledgers": ledgers,
            "ledger_checks": ledger_checks,
            "retained_surface_preservation": retained,
            "deformation_poses": poses,
            "render_checks": render_checks,
            "immutability": immutability,
            "machine_gate_groups": final_checks,
            "operations": {
                "source_or_candidate_written": False,
                "export_performed": False,
                "runtime_mutation_performed": False,
                "candidate_activated_or_assigned": False,
                "published": False,
                "private_owner_evidence_written": True,
            },
            "truth_boundary": config["truth_boundary"],
        }
        owner_index = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_PRIVATE_OWNER_REVIEW_INDEX",
            "created_utc": utc_now(),
            "status": "PENDING_OWNER_VISUAL_JUDGMENT",
            "decision": None,
            "renders": renders,
            "required_rejection_checks": config["owner_visual_judgment"]["required_rejection_checks"],
            "machine_pass_is_not_owner_approval": True,
            "candidate_remains_inactive_private_unassigned_unpublished": True,
        }
        output = config["bound_output"]
        write_new_json(paths["evidence_dir"] / output["machine_evidence_filename"], machine)
        write_new_json(paths["evidence_dir"] / output["owner_review_index_filename"], owner_index)
        manifest_path = paths["evidence_dir"] / output["manifest_filename"]
        write_new_json(manifest_path, output_manifest(paths["evidence_dir"], manifest_path.name))
        print(json.dumps({"status": machine["status"], "owner_status": owner_index["status"], "manifest": relative(manifest_path)}, indent=2))
        return 0
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_POSTSAVE_FRESH_REOPEN_FAILURE",
            "created_utc": utc_now(),
            "status": "NO_GO_CANDIDATE_NOT_OWNER_REVIEWABLE",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
            "candidate_binding": config.get("candidate_binding"),
            "build_evidence_binding": config.get("build_evidence_binding"),
            "source_before": source_before,
            "candidate_before": candidate_before,
            "source_current": {"bytes": source_path.stat().st_size, "sha256": sha256_file(source_path)},
            "candidate_current": {"bytes": paths["candidate"].stat().st_size, "sha256": sha256_file(paths["candidate"])},
            "candidate_remains_inactive_private_and_unapproved": True,
        }
        failure_path = paths["evidence_dir"] / config["bound_output"]["failure_filename"]
        if not failure_path.exists():
            write_new_json(failure_path, failure)
        raise


def main() -> int:
    args = arguments()
    return run(project_path(args.config), bool(getattr(args, "execute_fresh_reopen")))


if __name__ == "__main__":
    raise SystemExit(main())
