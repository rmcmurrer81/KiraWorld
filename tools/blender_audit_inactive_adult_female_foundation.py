#!/usr/bin/env python3
"""Fresh-process, read-only audit of one saved inactive adult foundation.

The candidate Blend is opened with auto-execution disabled and is never saved.
The auditor binds both policy-shaped reports to the exact input SHA-256, scans
the complete primary mesh, and refuses to turn labels or author metadata into
geometry claims.  Relationship findings require measured, connected primary-
surface geometry plus independently checked side and longitudinal ordering.

This auditor does not render, export, style, clothe, assign, activate, or pose
the candidate.  A successful generic-foundation review is not a Kira review.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
from typing import Any, Iterable, Mapping, Sequence

import bmesh
import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.blender_exact_mesh_intersections import (  # noqa: E402
    exact_nonadjacent_intersection_report,
)


INACTIVE_ROOT = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "workspaces"
    / "inactive_adult_female_foundations"
)
POLICY_PATH = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "policies"
    / "adult_foundation_qualification_v1.json"
)
TOPOLOGY_REVIEWER_ID = "adult_foundation_topology_auditor_fresh_process_v1"
RELATIONSHIP_REVIEWER_ID = (
    "adult_female_relationship_auditor_fresh_process_v1"
)
LANDMARK_GROUPS: Mapping[str, str] = {
    "mons_pubis": "AFES_LANDMARK__mons_pubis",
    "paired_labia_majora": "AFES_LANDMARK__labia_majora",
    "paired_labia_minora": "AFES_LANDMARK__labia_minora",
    "clitoral_hood": "AFES_LANDMARK__clitoral_hood",
    "clitoris": "AFES_LANDMARK__clitoris",
    "vestibule": "AFES_LANDMARK__vestibule",
    "urethral_opening_anterior_to_vaginal_opening": (
        "AFES_LANDMARK__urethral_opening"
    ),
    "vaginal_opening": "AFES_LANDMARK__vaginal_opening",
    "posterior_commissure_fourchette": "AFES_LANDMARK__fourchette",
    "perineal_transition_to_anus_and_pelvic_floor": (
        "AFES_LANDMARK__perineal_path"
    ),
}
SUBGROUPS: Mapping[str, str] = {
    "labia_majora_left": "AFES_LANDMARK__labia_majora__left",
    "labia_majora_right": "AFES_LANDMARK__labia_majora__right",
    "labia_minora_left": "AFES_LANDMARK__labia_minora__left",
    "labia_minora_right": "AFES_LANDMARK__labia_minora__right",
    "perineal_transition": "AFES_LANDMARK__perineal_path__transition",
    "posterior_anal_recess": "AFES_LANDMARK__perineal_path__anal_recess",
}
FORBIDDEN_WRONG_SEX_TOKENS = (
    "helper-genital",
    "helper_genital",
    "male_helper",
    "penis",
    "scrotum",
    "testicle",
)


class AdultFoundationAuditError(RuntimeError):
    """Raised before evidence is written when the audit cannot be completed."""


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--topology-output")
    parser.add_argument("--relationship-output")
    parser.add_argument(
        "--diagnostic-only",
        action="store_true",
        help="Print reports without creating evidence files.",
    )
    result = parser.parse_args(argv)
    if not result.diagnostic_only and (
        not result.topology_output or not result.relationship_output
    ):
        parser.error(
            "--topology-output and --relationship-output are required unless "
            "--diagnostic-only is used"
        )
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise AdultFoundationAuditError(f"JSON root must be an object: {path}")
    return value


def _project_path(raw: Any, *, suffix: str, must_exist: bool) -> Path:
    text = str(raw or "").strip()
    candidate = Path(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts:
        raise AdultFoundationAuditError(f"unsafe project-relative path: {text!r}")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise AdultFoundationAuditError(f"symlink path refused: {text!r}")
    resolved = lexical.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise AdultFoundationAuditError(
            f"path escaped project root: {text!r}"
        ) from exc
    if resolved.suffix.lower() != suffix:
        raise AdultFoundationAuditError(f"path must end in {suffix}: {text!r}")
    if must_exist and not resolved.is_file():
        raise AdultFoundationAuditError(f"input file missing: {resolved}")
    return resolved


def _inactive_input(raw: Any) -> Path:
    path = _project_path(raw, suffix=".blend", must_exist=True)
    try:
        path.relative_to(INACTIVE_ROOT.resolve())
    except ValueError as exc:
        raise AdultFoundationAuditError(
            f"candidate must be beneath inactive root: {INACTIVE_ROOT}"
        ) from exc
    return path


def _output_path(raw: Any, input_path: Path) -> Path:
    path = _project_path(raw, suffix=".json", must_exist=False)
    if path.parent != input_path.parent:
        raise AdultFoundationAuditError(
            "evidence outputs must be beside the exact inactive candidate"
        )
    if path.exists():
        raise AdultFoundationAuditError(f"refusing to overwrite evidence: {path}")
    return path


def _vector_record(value: Vector) -> list[float]:
    return [round(float(component), 9) for component in value]


def _component_labels(
    bm: bmesh.types.BMesh,
) -> tuple[dict[int, int], list[int]]:
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    labels: dict[int, int] = {}
    sizes: list[int] = []
    unseen = set(bm.verts)
    while unseen:
        seed = unseen.pop()
        component_id = len(sizes)
        todo = [seed]
        size = 0
        while todo:
            current = todo.pop()
            labels[int(current.index)] = component_id
            size += 1
            for edge in current.link_edges:
                neighbor = edge.other_vert(current)
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    todo.append(neighbor)
        sizes.append(size)
    return labels, sizes


def _coincident_duplicate_triangles(bm: bmesh.types.BMesh) -> int:
    triangulated = bm.copy()
    try:
        bmesh.ops.triangulate(
            triangulated,
            faces=list(triangulated.faces),
            quad_method="BEAUTY",
            ngon_method="BEAUTY",
        )
        signatures: Counter[tuple[tuple[float, float, float], ...]] = Counter()
        for face in triangulated.faces:
            signature = tuple(
                sorted(
                    tuple(round(float(component), 10) for component in vert.co)
                    for vert in face.verts
                )
            )
            signatures[signature] += 1
        return sum(
            count * (count - 1) // 2
            for count in signatures.values()
            if count > 1
        )
    finally:
        triangulated.free()


def _weight_metrics(obj: bpy.types.Object) -> dict[str, Any]:
    sums: list[float] = []
    influence_counts: list[int] = []
    landmark_indices = {
        group.index
        for group in obj.vertex_groups
        if group.name.startswith("AFES_LANDMARK__")
    }
    for vertex in obj.data.vertices:
        weights = [
            float(item.weight)
            for item in vertex.groups
            if item.group not in landmark_indices and item.weight > 1.0e-8
        ]
        sums.append(sum(weights))
        influence_counts.append(len(weights))
    return {
        "vertex_count": len(sums),
        "unweighted_vertex_count": sum(value <= 1.0e-8 for value in sums),
        "weight_sum_out_of_tolerance_count": sum(
            abs(value - 1.0) > 1.0e-4 for value in sums
        ),
        "minimum_weight_sum": min(sums, default=0.0),
        "maximum_weight_sum": max(sums, default=0.0),
        "maximum_positive_influence_count": max(influence_counts, default=0),
    }


def _group_members(obj: bpy.types.Object, name: str) -> set[int]:
    group = obj.vertex_groups.get(name)
    if group is None:
        return set()
    return {
        int(vertex.index)
        for vertex in obj.data.vertices
        if any(
            item.group == group.index and float(item.weight) >= 0.5
            for item in vertex.groups
        )
    }


def _induced_component_count(
    bm: bmesh.types.BMesh,
    members: set[int],
) -> int:
    if not members:
        return 0
    adjacency = {index: set() for index in members}
    for edge in bm.edges:
        left, right = (int(vert.index) for vert in edge.verts)
        if left in members and right in members:
            adjacency[left].add(right)
            adjacency[right].add(left)
    unseen = set(members)
    count = 0
    while unseen:
        count += 1
        todo = [unseen.pop()]
        while todo:
            current = todo.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    todo.append(neighbor)
    return count


def _local_coordinates(
    point: Vector,
    *,
    origin: Vector,
    lateral: Vector,
    longitudinal: Vector,
    outward: Vector,
    half_width: float,
    half_length: float,
) -> tuple[float, float, float]:
    delta = point - origin
    return (
        float(delta.dot(lateral) / half_width),
        float(delta.dot(longitudinal) / half_length),
        float(delta.dot(outward)),
    )


def _stats(values: Sequence[float]) -> dict[str, float | None]:
    if not values:
        return {"minimum": None, "median": None, "mean": None, "maximum": None}
    return {
        "minimum": float(min(values)),
        "median": float(statistics.median(values)),
        "mean": float(statistics.fmean(values)),
        "maximum": float(max(values)),
    }


def _group_geometry(
    obj: bpy.types.Object,
    bm: bmesh.types.BMesh,
    members: set[int],
    component_labels: Mapping[int, int],
    primary_component_id: int,
    *,
    frame: Mapping[str, Any],
    minimum_vertices: int,
    diagonal: float,
    paint_channels_absent: bool,
) -> dict[str, Any]:
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    points = [bm.verts[index].co.copy() for index in sorted(members)]
    incident_edges = []
    internal_edges = []
    connection_edges = []
    for edge in bm.edges:
        endpoint_membership = [int(vert.index) in members for vert in edge.verts]
        if any(endpoint_membership):
            incident_edges.append(edge)
        if all(endpoint_membership):
            internal_edges.append(edge)
        elif any(endpoint_membership):
            connection_edges.append(edge)
    incident_faces = [
        face
        for face in bm.faces
        if any(int(vert.index) in members for vert in face.verts)
    ]
    internal_faces = [
        face
        for face in bm.faces
        if all(int(vert.index) in members for vert in face.verts)
    ]
    if points:
        low = Vector(
            tuple(min(float(point[axis]) for point in points) for axis in range(3))
        )
        high = Vector(
            tuple(max(float(point[axis]) for point in points) for axis in range(3))
        )
        spatial_extent = float((high - low).length)
    else:
        low = Vector()
        high = Vector()
        spatial_extent = 0.0
    origin = Vector(frame["origin"])
    lateral = Vector(frame["lateral_axis"]).normalized()
    longitudinal = Vector(frame["longitudinal_axis"]).normalized()
    outward = Vector(frame["outward_axis"]).normalized()
    local = [
        _local_coordinates(
            point,
            origin=origin,
            lateral=lateral,
            longitudinal=longitudinal,
            outward=outward,
            half_width=float(frame["half_width_m"]),
            half_length=float(frame["half_length_m"]),
        )
        for point in points
    ]
    u_values = [value[0] for value in local]
    v_values = [value[1] for value in local]
    depth_values = [value[2] for value in local]
    depth_span = max(depth_values, default=0.0) - min(depth_values, default=0.0)
    geometry_present = bool(
        len(members) >= minimum_vertices
        and incident_edges
        and internal_edges
        and incident_faces
        and sum(float(face.calc_area()) for face in incident_faces) > 1.0e-12
        and spatial_extent > max(diagonal * 1.0e-7, 1.0e-7)
    )
    connected_to_primary = bool(
        geometry_present
        and component_labels
        and all(
            component_labels.get(index) == primary_component_id
            for index in members
        )
        and connection_edges
    )
    nonzero_geometric_relief = bool(
        depth_span > max(diagonal * 1.0e-6, 1.0e-6)
    )
    not_painted_only = bool(
        geometry_present
        and connected_to_primary
        and nonzero_geometric_relief
        and paint_channels_absent
    )
    return {
        "geometry_present": geometry_present,
        "connected_to_primary_surface": connected_to_primary,
        "not_painted_only": not_painted_only,
        "measurement": {
            "vertex_count": len(members),
            "minimum_vertex_count_required": minimum_vertices,
            "incident_edge_count": len(incident_edges),
            "internal_edge_count": len(internal_edges),
            "primary_surface_connection_edge_count": len(connection_edges),
            "incident_face_count": len(incident_faces),
            "internal_face_count": len(internal_faces),
            "incident_surface_area_m2": float(
                sum(face.calc_area() for face in incident_faces)
            ),
            "induced_landmark_component_count": _induced_component_count(
                bm,
                members,
            ),
            "primary_component_membership_complete": connected_to_primary,
            "bounds_min_object_m": _vector_record(low),
            "bounds_max_object_m": _vector_record(high),
            "spatial_extent_m": spatial_extent,
            "normalized_lateral_u": _stats(u_values),
            "normalized_longitudinal_v": _stats(v_values),
            "outward_depth_m": _stats(depth_values),
            "outward_depth_span_m": float(depth_span),
            "nonzero_geometric_relief": nonzero_geometric_relief,
            "paint_channels_absent": paint_channels_absent,
        },
    }


def _median_coordinate(record: Mapping[str, Any], axis: str) -> float:
    measurement = record.get("measurement")
    if not isinstance(measurement, Mapping):
        return math.nan
    stats = measurement.get(axis)
    if not isinstance(stats, Mapping):
        return math.nan
    value = stats.get("median")
    return float(value) if isinstance(value, (int, float)) else math.nan


def _ordering_record(
    name: str,
    first_value: float,
    second_value: float,
    *,
    minimum_margin: float,
    convention: str,
) -> dict[str, Any]:
    finite = math.isfinite(first_value) and math.isfinite(second_value)
    margin = first_value - second_value if finite else math.nan
    return {
        "check": name,
        "first_value": first_value if finite else None,
        "second_value": second_value if finite else None,
        "measured_margin": margin if finite else None,
        "minimum_margin_required": minimum_margin,
        "coordinate_convention": convention,
        "passed": bool(finite and margin > minimum_margin),
    }


def _relief_contrast_record(
    name: str,
    outward_record: Mapping[str, Any],
    recessed_record: Mapping[str, Any],
    *,
    minimum_margin_m: float,
) -> dict[str, Any]:
    outward_depth = _median_coordinate(outward_record, "outward_depth_m")
    recessed_depth = _median_coordinate(recessed_record, "outward_depth_m")
    finite = math.isfinite(outward_depth) and math.isfinite(recessed_depth)
    margin = outward_depth - recessed_depth if finite else math.nan
    return {
        "check": name,
        "outward_feature_median_depth_m": outward_depth if finite else None,
        "recessed_feature_median_depth_m": recessed_depth if finite else None,
        "measured_relief_margin_m": margin if finite else None,
        "minimum_margin_required_m": minimum_margin_m,
        "coordinate_convention": "larger depth is farther outward from the body",
        "passed": bool(finite and margin > minimum_margin_m),
    }


def _manifest(obj: bpy.types.Object) -> dict[str, Any]:
    raw = obj.get("inactive_foundation_build_manifest_json")
    if not isinstance(raw, str):
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _write_new_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists():
        raise AdultFoundationAuditError(f"refusing to overwrite evidence: {path}")
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = _arguments()
    input_path = _inactive_input(args.input)
    config_path = _project_path(args.config, suffix=".json", must_exist=True)
    topology_output = (
        None
        if args.diagnostic_only
        else _output_path(args.topology_output, input_path)
    )
    relationship_output = (
        None
        if args.diagnostic_only
        else _output_path(args.relationship_output, input_path)
    )
    if topology_output is not None and topology_output == relationship_output:
        raise AdultFoundationAuditError(
            "topology and relationship outputs must differ"
        )

    policy = _read_json(POLICY_PATH)
    config = _read_json(config_path)
    required_relationships = tuple(
        str(value) for value in policy["required_adult_female_relationships"]
    )
    if required_relationships != tuple(LANDMARK_GROUPS):
        raise AdultFoundationAuditError(
            "independent relationship map drifted from qualification policy"
        )
    frame = config.get("frame")
    parameters = config.get("parameters")
    if not isinstance(frame, Mapping) or not isinstance(parameters, Mapping):
        raise AdultFoundationAuditError("neutral authoring config is incomplete")
    minimum_vertices = int(parameters.get("minimum_landmark_vertices", 0))
    if minimum_vertices < 2:
        raise AdultFoundationAuditError("minimum landmark requirement invalid")

    artifact_before = _sha256(input_path)
    stat_before = input_path.stat()
    bpy.ops.wm.open_mainfile(
        filepath=str(input_path),
        load_ui=False,
        use_scripts=False,
    )

    objects = list(bpy.data.objects)
    mesh_objects = [obj for obj in objects if obj.type == "MESH"]
    primary = [obj for obj in mesh_objects if obj.get("primary_surface") is True]
    if len(primary) != 1:
        raise AdultFoundationAuditError(
            f"expected exactly one marked primary surface, found {len(primary)}"
        )
    body = primary[0]
    manifest = _manifest(body)
    candidate_author_id = str(
        manifest.get("candidate_author_id")
        or body.get("candidate_author_id")
        or ""
    ).strip()
    if not candidate_author_id:
        raise AdultFoundationAuditError("candidate author identity is missing")
    if candidate_author_id in {
        TOPOLOGY_REVIEWER_ID,
        RELATIONSHIP_REVIEWER_ID,
    }:
        raise AdultFoundationAuditError("candidate/reviewer separation failed")

    bm = bmesh.new()
    try:
        bm.from_mesh(body.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.verts.index_update()
        bm.faces.index_update()
        bm.normal_update()
        points = [vert.co.copy() for vert in bm.verts]
        if not points:
            raise AdultFoundationAuditError("primary surface is empty")
        low = Vector(
            tuple(min(float(point[axis]) for point in points) for axis in range(3))
        )
        high = Vector(
            tuple(max(float(point[axis]) for point in points) for axis in range(3))
        )
        diagonal = float((high - low).length)
        component_labels, component_sizes = _component_labels(bm)
        primary_component_id = max(
            range(len(component_sizes)),
            key=component_sizes.__getitem__,
        )
        exact_intersections = exact_nonadjacent_intersection_report(bm)
        metrics = {
            "primary_surface_components": len(component_sizes),
            "boundary_edges": sum(
                len(edge.link_faces) == 1 for edge in bm.edges
            ),
            "nonmanifold_edges": sum(
                len(edge.link_faces) not in {1, 2} for edge in bm.edges
            ),
            "degenerate_faces": sum(
                float(face.calc_area()) <= 1.0e-12 for face in bm.faces
            ),
            "coincident_duplicate_triangle_pairs": (
                _coincident_duplicate_triangles(bm)
            ),
            "nonadjacent_self_intersection_pairs": int(
                exact_intersections["exact_genuine_penetration_pair_count"]
            ),
        }
        required_metrics = policy.get("required_topology_metrics")
        topology_metrics_passed = bool(
            isinstance(required_metrics, Mapping)
            and all(metrics.get(name) == value for name, value in required_metrics.items())
        )

        color_attributes = getattr(body.data, "color_attributes", ())
        paint_channel_record = {
            "material_slot_count": len(body.material_slots),
            "mesh_material_count": len(body.data.materials),
            "color_attribute_count": len(color_attributes),
            "uv_layer_count": len(body.data.uv_layers),
        }
        paint_channels_absent = not any(paint_channel_record.values())

        relationship_records: dict[str, dict[str, Any]] = {}
        all_geometry_records: dict[str, dict[str, Any]] = {}
        for relationship, group_name in {
            **LANDMARK_GROUPS,
            **SUBGROUPS,
        }.items():
            geometry = _group_geometry(
                body,
                bm,
                _group_members(body, group_name),
                component_labels,
                primary_component_id,
                frame=frame,
                minimum_vertices=minimum_vertices,
                diagonal=diagonal,
                paint_channels_absent=paint_channels_absent,
            )
            geometry["landmark_group"] = group_name
            all_geometry_records[relationship] = geometry
        for relationship in required_relationships:
            relationship_records[relationship] = all_geometry_records[relationship]

        ordering_checks: dict[str, dict[str, Any]] = {}
        for label, first, second in (
            (
                "labia_majora_left_right",
                "labia_majora_left",
                "labia_majora_right",
            ),
            (
                "labia_minora_left_right",
                "labia_minora_left",
                "labia_minora_right",
            ),
        ):
            ordering_checks[label] = _ordering_record(
                label,
                _median_coordinate(
                    all_geometry_records[first],
                    "normalized_lateral_u",
                ),
                _median_coordinate(
                    all_geometry_records[second],
                    "normalized_lateral_u",
                ),
                minimum_margin=0.10,
                convention="positive u is configured anatomical left",
            )
        anterior_pairs = (
            (
                "urethral_anterior_to_vaginal",
                "urethral_opening_anterior_to_vaginal_opening",
                "vaginal_opening",
                0.05,
            ),
            (
                "clitoris_anterior_to_vaginal",
                "clitoris",
                "vaginal_opening",
                0.05,
            ),
            (
                "vaginal_anterior_to_fourchette",
                "vaginal_opening",
                "posterior_commissure_fourchette",
                0.05,
            ),
            (
                "fourchette_anterior_to_anal_recess",
                "posterior_commissure_fourchette",
                "posterior_anal_recess",
                0.05,
            ),
            (
                "perineal_transition_anterior_to_anal_recess",
                "perineal_transition",
                "posterior_anal_recess",
                0.05,
            ),
        )
        for label, first, second, margin in anterior_pairs:
            ordering_checks[label] = _ordering_record(
                label,
                _median_coordinate(
                    all_geometry_records[first],
                    "normalized_longitudinal_v",
                ),
                _median_coordinate(
                    all_geometry_records[second],
                    "normalized_longitudinal_v",
                ),
                minimum_margin=margin,
                convention="positive v is configured anterior/superior",
            )

        relief_contrast_checks = {
            "labia_majora_outward_of_vaginal_recess": _relief_contrast_record(
                "labia_majora_outward_of_vaginal_recess",
                relationship_records["paired_labia_majora"],
                relationship_records["vaginal_opening"],
                minimum_margin_m=0.005,
            ),
            "labia_minora_outward_of_vaginal_recess": _relief_contrast_record(
                "labia_minora_outward_of_vaginal_recess",
                relationship_records["paired_labia_minora"],
                relationship_records["vaginal_opening"],
                minimum_margin_m=0.003,
            ),
            "vestibule_outward_of_vaginal_recess": _relief_contrast_record(
                "vestibule_outward_of_vaginal_recess",
                relationship_records["vestibule"],
                relationship_records["vaginal_opening"],
                minimum_margin_m=0.005,
            ),
            "clitoris_outward_of_urethral_recess": _relief_contrast_record(
                "clitoris_outward_of_urethral_recess",
                relationship_records["clitoris"],
                relationship_records[
                    "urethral_opening_anterior_to_vaginal_opening"
                ],
                minimum_margin_m=0.001,
            ),
            "fourchette_outward_of_vaginal_recess": _relief_contrast_record(
                "fourchette_outward_of_vaginal_recess",
                relationship_records["posterior_commissure_fourchette"],
                relationship_records["vaginal_opening"],
                minimum_margin_m=0.005,
            ),
            "perineal_transition_outward_of_anal_recess": (
                _relief_contrast_record(
                    "perineal_transition_outward_of_anal_recess",
                    all_geometry_records["perineal_transition"],
                    all_geometry_records["posterior_anal_recess"],
                    minimum_margin_m=0.003,
                )
            ),
        }
        relief_contrast_passed = all(
            record["passed"] is True
            for record in relief_contrast_checks.values()
        )

        left_right_passed = all(
            ordering_checks[name]["passed"] is True
            for name in (
                "labia_majora_left_right",
                "labia_minora_left_right",
            )
        )
        anterior_posterior_passed = all(
            record["passed"] is True
            for name, record in ordering_checks.items()
            if name not in {
                "labia_majora_left_right",
                "labia_minora_left_right",
            }
        )
        relationship_records["paired_labia_majora"][
            "left_right_ordering_proven"
        ] = left_right_passed
        relationship_records["paired_labia_minora"][
            "left_right_ordering_proven"
        ] = left_right_passed
        relationship_records[
            "urethral_opening_anterior_to_vaginal_opening"
        ]["anterior_to_vaginal_opening_proven"] = ordering_checks[
            "urethral_anterior_to_vaginal"
        ]["passed"]
        relationship_records[
            "perineal_transition_to_anus_and_pelvic_floor"
        ]["transition_anterior_to_anal_recess_proven"] = ordering_checks[
            "perineal_transition_anterior_to_anal_recess"
        ]["passed"]

        all_relationship_assertions_passed = all(
            all(record.get(assertion) is True for assertion in (
                "geometry_present",
                "connected_to_primary_surface",
                "not_painted_only",
            ))
            for record in relationship_records.values()
        )
        required_subgroups_passed = all(
            all_geometry_records[name]["geometry_present"] is True
            and all_geometry_records[name]["connected_to_primary_surface"] is True
            and all_geometry_records[name]["not_painted_only"] is True
            for name in SUBGROUPS
        )
        forbidden_text = " ".join(
            [
                *(obj.name for obj in objects),
                *(obj.data.name for obj in mesh_objects),
                *(group.name for group in body.vertex_groups),
            ]
        ).lower()
        wrong_sex_tokens_found = sorted(
            token for token in FORBIDDEN_WRONG_SEX_TOKENS if token in forbidden_text
        )
        authored_members = set().union(
            *(
                _group_members(body, group_name)
                for group_name in LANDMARK_GROUPS.values()
            )
        )
        authored_integration = _group_geometry(
            body,
            bm,
            authored_members,
            component_labels,
            primary_component_id,
            frame=frame,
            minimum_vertices=minimum_vertices,
            diagonal=diagonal,
            paint_channels_absent=paint_channels_absent,
        )
        negative_findings = {
            "doll_safe_or_incomplete": not bool(
                all_relationship_assertions_passed
                and required_subgroups_passed
                and left_right_passed
                and anterior_posterior_passed
                and relief_contrast_passed
            ),
            "floating_or_separate_anatomy_component": bool(
                len(mesh_objects) != 1
                or len(component_sizes) != 1
                or not authored_integration["connected_to_primary_surface"]
            ),
            "intersecting_anatomy_component": bool(
                metrics["nonadjacent_self_intersection_pairs"] != 0
            ),
            "wrong_sex_helper_present": bool(
                wrong_sex_tokens_found
                or body.get("wrong_sex_helper_present") is not False
            ),
            "visible_open_seam_or_bridge_patch": bool(
                metrics["boundary_edges"] != 0
                or metrics["nonmanifold_edges"] != 0
                or metrics["coincident_duplicate_triangle_pairs"] != 0
                or not authored_integration["connected_to_primary_surface"]
            ),
        }
        required_negative = policy.get("required_negative_findings")
        negatives_passed = bool(
            isinstance(required_negative, Mapping)
            and all(
                negative_findings.get(name) is expected
                for name, expected in required_negative.items()
            )
        )
        weight_metrics = _weight_metrics(body)
        observed_body_class = re.sub(
            r"[^a-z0-9]+",
            "_",
            str(body.get("body_class") or "").lower(),
        ).strip("_")
        generic_scope_verified = bool(
            body.get("generic_identity_neutral_foundation") is True
            and body.get("kira_styling_applied") is False
            and bpy.context.scene.get("kira_styling_applied") is False
            and bpy.context.scene.get("clothing_applied") is False
        )
        artifact_after = _sha256(input_path)
        stat_after = input_path.stat()
        exact_hash_verified = bool(
            artifact_before == artifact_after
            and stat_before.st_size == stat_after.st_size
            and stat_before.st_mtime_ns == stat_after.st_mtime_ns
        )
        topology_passed = bool(
            exact_hash_verified
            and topology_metrics_passed
            and len(primary) == 1
            and len(mesh_objects) == 1
            and len(objects) == 1
            and len(body.modifiers) == 0
            and observed_body_class == "adult_female"
            and generic_scope_verified
            and weight_metrics["unweighted_vertex_count"] == 0
            and weight_metrics["weight_sum_out_of_tolerance_count"] == 0
            and weight_metrics["maximum_positive_influence_count"] <= 4
            and sum(obj.type == "ARMATURE" for obj in objects) == 0
        )
        relationship_passed = bool(
            exact_hash_verified
            and topology_passed
            and all_relationship_assertions_passed
            and required_subgroups_passed
            and left_right_passed
            and anterior_posterior_passed
            and relief_contrast_passed
            and negatives_passed
        )
        reviewed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        artifact_relative = input_path.relative_to(PROJECT_ROOT).as_posix()
        common_limitations = [
            "No render or visual appearance review was performed.",
            "No internal anatomy beyond the policy-listed external relationships was claimed.",
            "No identity, likeness, hair, skin tone, clothing, or Kira styling was reviewed.",
            "The mesh has normalized weights but no armature; pose behavior is unproven.",
            "Owner approval, runtime readiness, and public-export readiness are not implied.",
        ]
        topology_report: dict[str, Any] = {
            "schema_version": 1,
            "artifact_type": "independent_adult_foundation_topology_audit",
            "status": "PASSED" if topology_passed else "BLOCKED_NOT_PASSED",
            "passed": topology_passed,
            "artifact_path": artifact_relative,
            "artifact_sha256": artifact_before,
            "artifact_size_bytes": stat_before.st_size,
            "body_class": observed_body_class,
            "candidate_author_id": candidate_author_id,
            "independent_reviewer": {
                "id": TOPOLOGY_REVIEWER_ID,
                "role": "independent_topology_auditor",
                "process_mode": "fresh_blender_process_read_only",
            },
            "reviewed_at": reviewed_at,
            "exact_artifact_sha256_verified": exact_hash_verified,
            "complete_scan": True,
            "input_modified": not exact_hash_verified,
            "metrics": metrics,
            "required_metrics": required_metrics,
            "mesh": {
                "object_count": len(objects),
                "mesh_object_count": len(mesh_objects),
                "marked_primary_surface_count": len(primary),
                "primary_object_name": body.name,
                "vertex_count": len(bm.verts),
                "edge_count": len(bm.edges),
                "face_count": len(bm.faces),
                "component_sizes": sorted(component_sizes, reverse=True),
                "bounds_min_object_m": _vector_record(low),
                "bounds_max_object_m": _vector_record(high),
                "diagonal_m": diagonal,
                "modifier_count": len(body.modifiers),
                "armature_object_count": sum(
                    obj.type == "ARMATURE" for obj in objects
                ),
                "generic_identity_scope_verified": generic_scope_verified,
            },
            "exact_intersection_scan": exact_intersections,
            "weight_metrics": weight_metrics,
            "render_performed": False,
            "export_performed": False,
            "runtime_mutation_performed": False,
            "runtime_activation_allowed": False,
            "limitations": common_limitations,
        }
        relationship_report: dict[str, Any] = {
            "schema_version": 1,
            "artifact_type": "independent_adult_female_relationship_review",
            "status": "PASSED" if relationship_passed else "BLOCKED_NOT_PASSED",
            "passed": relationship_passed,
            "artifact_path": artifact_relative,
            "artifact_sha256": artifact_before,
            "artifact_size_bytes": stat_before.st_size,
            "body_class": observed_body_class,
            "candidate_author_id": candidate_author_id,
            "independent_reviewer": {
                "id": RELATIONSHIP_REVIEWER_ID,
                "role": "independent_adult_anatomy_reviewer",
                "process_mode": "fresh_blender_process_read_only",
            },
            "reviewed_at": reviewed_at,
            "exact_artifact_sha256_verified": exact_hash_verified,
            "complete_primary_surface_scan": True,
            "input_modified": not exact_hash_verified,
            "relationships": relationship_records,
            "required_subgroup_geometry": {
                name: all_geometry_records[name] for name in SUBGROUPS
            },
            "ordering_checks": ordering_checks,
            "left_right_ordering_passed": left_right_passed,
            "anterior_posterior_ordering_passed": anterior_posterior_passed,
            "relief_contrast_checks": relief_contrast_checks,
            "relief_contrast_passed": relief_contrast_passed,
            "paint_channel_scan": paint_channel_record,
            "negative_findings": negative_findings,
            "wrong_sex_tokens_found": wrong_sex_tokens_found,
            "authored_landmark_union_integration": authored_integration,
            "geometry_mode": "continuous_primary_surface_relief",
            "opening_representation": (
                "recessed_capped_continuous_primary_surface"
                if relief_contrast_passed
                else "UNPROVEN"
            ),
            "separate_anatomy_mesh_count": max(0, len(mesh_objects) - 1),
            "render_performed": False,
            "export_performed": False,
            "runtime_mutation_performed": False,
            "runtime_activation_allowed": False,
            "unsupported_claims_refused": [
                "visual realism or owner acceptance",
                "internal reproductive anatomy",
                "posed deformation quality",
                "Kira identity or likeness",
                "hair, skin, clothing, or runtime readiness",
            ],
            "mandatory_downstream_kira_candidate_gate": (
                "Attach the intended armature and independently pass a "
                "pose-space pelvic-patch deformation audit before any "
                "identity-specific Kira candidate use."
            ),
            "limitations": common_limitations,
        }
    finally:
        bm.free()

    payload = {
        "topology": topology_report,
        "relationships": relationship_report,
    }
    print("INACTIVE_ADULT_FOUNDATION_AUDIT " + json.dumps(payload, sort_keys=True))
    if args.diagnostic_only:
        return
    assert topology_output is not None
    assert relationship_output is not None
    _write_new_json(topology_output, topology_report)
    try:
        _write_new_json(relationship_output, relationship_report)
    except Exception:
        topology_output.unlink(missing_ok=True)
        raise
    print(
        json.dumps(
            {
                "artifact_sha256": artifact_before,
                "topology_output": topology_output.relative_to(PROJECT_ROOT).as_posix(),
                "topology_output_sha256": _sha256(topology_output),
                "relationship_output": relationship_output.relative_to(PROJECT_ROOT).as_posix(),
                "relationship_output_sha256": _sha256(relationship_output),
                "topology_passed": topology_report["passed"],
                "relationships_passed": relationship_report["passed"],
                "artifact_mutated": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    if not topology_report["passed"] or not relationship_report["passed"]:
        raise AdultFoundationAuditError(
            "evidence emitted as blocked because independent proof did not pass"
        )


if __name__ == "__main__":
    main()
