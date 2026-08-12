"""No-save A09 attempt_02 coupled linear seam-slope simulation.

This worker imports but never overwrites the exact attempt_01 midpoint worker.
It replaces only the infeasible outside-normal-only seam projection with hard
linear triangle-slope rows inside one coupled screened differential-coordinate
solve.  Every original cap, topology gate, semantic gate, intersection gate,
and the unchanged A06 surface-relief formula remains binding.

External private visual/topology simulation only.  No internal tract,
physiology, elimination, reproduction, pregnancy, sensation, or subjective
experience is created or claimed.  This worker never saves a Blend.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any, Mapping, Sequence

import bmesh
import bpy
from mathutils import Vector
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_simulate_kira_r24_internal_midpoint_fair_surface as a09  # noqa: E402


SOURCE = a09.SOURCE
SOURCE_SHA256 = a09.SOURCE_SHA256
BODY_NAME = a09.BODY_NAME
RIG_NAME = a09.RIG_NAME
OUTPUT_ROOT = a09.OUTPUT_ROOT

ATTEMPT_01_WORKER = ROOT / "tools/blender_simulate_kira_r24_internal_midpoint_fair_surface.py"
ATTEMPT_01_WORKER_SHA256 = "8fcd1c39b9f375f5a48d0aefd761222fe0e65b2a7efe491e6d28f7e794aa49d7"
ATTEMPT_01_FAILURE = OUTPUT_ROOT / "attempt_01/FAILURE.json"
ATTEMPT_01_FAILURE_SHA256 = "74608844f168489e60dc476910aac7f007077eb4c5d845f20ecd5487112a7e45"
PROPOSAL = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_02_PROPOSAL.md"
PROPOSAL_SHA256 = "9f1a87fd58b103b46308974f30b3d048f9d8e97e973d2f47470cd105d2031088"

ACTIVE_OUTPUT: Path | None = None
SOURCE_FACE_ID_BY_VERTICES: dict[frozenset[int], int] = {}

SLOPE_RATIO_TOLERANCE = 2.0e-5
CONSTRAINT_RESIDUAL_TOLERANCE_M = 2.0e-8
Fidelity_WEIGHT = 18.0
FIRST_DIFFERENTIAL_WEIGHT = 1.0
BIHARMONIC_WEIGHT = 0.20
RING_1_PLANE_WEIGHT = 1.0
RING_2_PLANE_WEIGHT = 0.35


def sha256(path: Path) -> str:
    return a09.sha256(path)


def relative(path: Path) -> str:
    return a09.relative(path)


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def a08_movement_by_edge() -> dict[tuple[int, int], Mapping[str, Any]]:
    document = json.loads(a09.A08_REPORT.read_text(encoding="utf-8"))
    records = document["application"]["seam_support_fairing"]["movement_records"]
    return {
        tuple(map(int, record["boundary_vertex_ids"])): record
        for record in records
    }


def selected_seam_targets(
    planes: Sequence[Mapping[str, Any]],
) -> list[tuple[Mapping[str, Any], float, str]]:
    below_low = [record for record in planes if float(record["baseline_dot"]) < 0.70]
    below_median = [
        record for record in planes if float(record["baseline_dot"]) < 0.94
    ]
    low_ids = {tuple(record["edge_ids"]) for record in below_low}
    additional_count = max(0, len(below_median) - 16 - len(low_ids))
    additional = sorted(
        (
            record
            for record in below_median
            if tuple(record["edge_ids"]) not in low_ids
        ),
        key=lambda record: (-float(record["baseline_dot"]), record["edge_ids"]),
    )[:additional_count]
    selected = [
        (record, a09.TARGET_LOW_DOT, "minimum_below_0_70")
        for record in below_low
    ]
    selected.extend(
        (record, a09.TARGET_MEDIAN_EDGE_DOT, "minimum_for_median_0_94")
        for record in additional
    )
    return sorted(selected, key=lambda item: tuple(item[0]["edge_ids"]))


def source_endpoint_ids_for_midpoint(
    support: bmesh.types.BMVert,
    original_ids: Mapping[bmesh.types.BMVert, int],
) -> tuple[int, int]:
    endpoints = sorted(
        {
            int(original_ids[edge.other_vert(support)])
            for edge in support.link_edges
            if int(original_ids.get(edge.other_vert(support), -1)) >= 0
        }
    )
    if len(endpoints) != 2:
        raise RuntimeError(
            f"midpoint support {support.index} does not expose two source endpoints: "
            f"{endpoints}"
        )
    return endpoints[0], endpoints[1]


def linear_slope_constraint_records(
    body: bpy.types.Object,
    planes: Sequence[Mapping[str, Any]],
    original_ids: Mapping[bmesh.types.BMVert, int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    comparisons = a08_movement_by_edge()
    runtime = []
    evidence = []
    for plane, target_dot, reason in selected_seam_targets(planes):
        edge = plane["edge"]
        support = plane["support"]
        first = body.matrix_world @ edge.verts[0].co
        second = body.matrix_world @ edge.verts[1].co
        midpoint = (first + second) * 0.5
        support_world = body.matrix_world @ support.co
        outside_normal = Vector(plane["normal"])
        outside_normal.normalize()
        edge_tangent = second - first
        if edge_tangent.length <= 1.0e-12:
            raise RuntimeError("linear seam-slope constraint has a zero boundary edge")
        edge_tangent.normalize()
        offset = support_world - midpoint
        signed_height = float(offset.dot(outside_normal))
        sigma = 1.0 if signed_height >= 0.0 else -1.0
        height = abs(signed_height)
        in_plane = offset - edge_tangent * offset.dot(edge_tangent)
        in_plane -= outside_normal * in_plane.dot(outside_normal)
        if in_plane.length <= 1.0e-12:
            raise RuntimeError("linear seam-slope support has zero in-plane radius")
        in_plane_direction = in_plane.normalized()
        radius = float(offset.dot(in_plane_direction))
        if radius <= 1.0e-12:
            raise RuntimeError("linear seam-slope support radius is not positive")
        kappa = math.sqrt(max(0.0, 1.0 - target_dot * target_dot)) / target_dot
        gap = height - kappa * radius
        coefficient = sigma * outside_normal - kappa * in_plane_direction
        if gap <= 0.0:
            closest = Vector()
        else:
            closest = -gap * coefficient / coefficient.length_squared
        normal_only = -sigma * max(0.0, gap) * outside_normal
        full_projection = -signed_height * outside_normal
        endpoint_ids = source_endpoint_ids_for_midpoint(support, original_ids)
        boundary_ids = tuple(map(int, plane["edge_ids"]))
        source_triangle_ids = frozenset((*boundary_ids, *endpoint_ids))
        source_face_id = SOURCE_FACE_ID_BY_VERTICES.get(source_triangle_ids)
        if source_face_id is None:
            raise RuntimeError(
                f"could not bind seam {boundary_ids} to its original source face"
            )
        slope_target = support_world + closest
        achieved_dot = a09.candidate_face_dot(
            body,
            plane["patch_face"],
            support,
            slope_target,
            outside_normal,
        )
        comparison = comparisons.get(boundary_ids)
        comparison_record = None
        if comparison is not None:
            a08_full = float(comparison["full_projection_world_m"])
            a08_requested = float(comparison["requested_world_m"])
            plane_height_ratio = height / a08_full
            movement_ratio = (
                normal_only.length / a08_requested if a08_requested > 0.0 else None
            )
            comparison_record = {
                "a08_support_type": "source_triangle_poke_centroid",
                "a09_support_type": "original_internal_edge_midpoint",
                "a08_full_projection_world_m": a08_full,
                "a08_requested_world_m": a08_requested,
                "a08_baseline_dot": float(comparison["baseline_dot"]),
                "a08_solver_target_dot": float(comparison["solver_target_dot"]),
                "observed_plane_height_ratio_a09_over_a08": plane_height_ratio,
                "predicted_plane_height_ratio": 1.5,
                "normal_only_movement_ratio_a09_over_a08": movement_ratio,
                "topology_ratio_within_tolerance": abs(plane_height_ratio - 1.5)
                <= SLOPE_RATIO_TOLERANCE,
            }
        record = {
            "boundary_vertex_ids": list(boundary_ids),
            "boundary_endpoint_world_m": [
                a09.a08.vector_record(first),
                a09.a08.vector_record(second),
            ],
            "boundary_midpoint_world_m": a09.a08.vector_record(midpoint),
            "outside_face_index_before_final_reindex": int(
                plane["outside_face"].index
            ),
            "outside_normal_world": a09.a08.vector_record(outside_normal),
            "boundary_tangent_world": a09.a08.vector_record(edge_tangent),
            "in_plane_away_from_seam_world": a09.a08.vector_record(
                in_plane_direction
            ),
            "support_vertex_index_before_final_reindex": int(support.index),
            "support_canonical_id": int(original_ids.get(support, -1)),
            "support_source_endpoint_ids": list(endpoint_ids),
            "support_world_m": a09.a08.vector_record(support_world),
            "source_face_id": int(source_face_id),
            "refined_seam_face_vertex_ids": [
                int(original_ids.get(vertex, -1))
                for vertex in plane["patch_face"].verts
            ],
            "selection_reason": reason,
            "baseline_dot": float(plane["baseline_dot"]),
            "baseline_dihedral_degrees": math.degrees(
                math.acos(max(-1.0, min(1.0, float(plane["baseline_dot"]))))
            ),
            "target_dot": float(target_dot),
            "maximum_slope_kappa": float(kappa),
            "signed_normal_height_m": signed_height,
            "positive_normal_height_m": height,
            "positive_in_plane_radius_m": radius,
            "slope_gap_m": float(max(0.0, gap)),
            "full_normal_projection": {
                "target_world_m": a09.a08.vector_record(
                    support_world + full_projection
                ),
                "vector_world_m": a09.a08.vector_record(full_projection),
                "length_m": float(full_projection.length),
            },
            "normal_only_minimum": {
                "alpha_of_full_projection": (
                    float(normal_only.length / full_projection.length)
                    if full_projection.length > 0.0
                    else 0.0
                ),
                "target_world_m": a09.a08.vector_record(
                    support_world + normal_only
                ),
                "vector_world_m": a09.a08.vector_record(normal_only),
                "length_m": float(normal_only.length),
                "within_ring_1_cap": normal_only.length
                <= a09.RING_1_CAP_M + a09.MOVEMENT_EPSILON_M,
            },
            "closest_linear_slope_minimum": {
                "target_world_m": a09.a08.vector_record(slope_target),
                "vector_world_m": a09.a08.vector_record(closest),
                "length_m": float(closest.length),
                "predicted_achieved_normal_dot": float(achieved_dot),
                "within_ring_1_cap": closest.length
                <= a09.RING_1_CAP_M + a09.MOVEMENT_EPSILON_M,
            },
            "ring_1_cap_m": a09.RING_1_CAP_M,
            "linear_row_coefficient_world": a09.a08.vector_record(coefficient),
            "linear_row_rhs_m": float(-max(0.0, gap)),
            "a08_topology_comparison": comparison_record,
        }
        runtime.append(
            {
                "record": record,
                "support": support,
                "coefficient": coefficient,
                "rhs": float(-max(0.0, gap)),
            }
        )
        evidence.append(record)
    return runtime, evidence


def coupled_linear_slope_fit(
    body: bpy.types.Object,
    bm: bmesh.types.BMesh,
    patch_faces: set[bmesh.types.BMFace],
    patch_vertices: set[bmesh.types.BMVert],
    patch_edges: Sequence[bmesh.types.BMEdge],
    seam_edges: set[bmesh.types.BMEdge],
    seam_vertices: set[bmesh.types.BMVert],
    distances: Mapping[bmesh.types.BMVert, int],
    original_ids: Mapping[bmesh.types.BMVert, int],
    parameters: Mapping[bmesh.types.BMVert, tuple[float, float]],
) -> dict[str, Any]:
    if ACTIVE_OUTPUT is None:
        raise RuntimeError("attempt_02 output was not allocated before the solve")
    vertices = sorted(patch_vertices, key=lambda vertex: int(vertex.index))
    vertex_index = {vertex: index for index, vertex in enumerate(vertices)}
    free_vertices = [vertex for vertex in vertices if vertex not in seam_vertices]
    free_index = {vertex: index for index, vertex in enumerate(free_vertices)}
    neighbors = a09.patch_neighbors(patch_vertices, patch_edges)
    if any(not neighbors.get(vertex) for vertex in vertices):
        raise RuntimeError("attempt_02 fair-fit graph contains an isolated vertex")
    base_local = {vertex: vertex.co.copy() for vertex in vertices}
    base_world = {vertex: body.matrix_world @ vertex.co for vertex in vertices}
    baseline_normals = {
        face: a09.a08.world_face_normal(body, face).copy() for face in patch_faces
    }
    planes = a09.seam_plane_records(
        body, patch_faces, seam_edges, original_ids
    )
    runtime_constraints, constraint_evidence = linear_slope_constraint_records(
        body, planes, original_ids
    )
    if not runtime_constraints:
        raise RuntimeError("attempt_02 selected no seam constraints")

    pre_cap = {
        "schema": "kira.avatar.r24.a09_attempt02.pre_cap_diagnostic.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "WRITTEN_ATOMICALLY_BEFORE_COUPLED_SOLVE",
        "worker": {
            "path": relative(Path(__file__).resolve()),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "source": {"path": relative(SOURCE), "sha256": sha256(SOURCE)},
        "preserved_attempt_01": {
            "worker_sha256": ATTEMPT_01_WORKER_SHA256,
            "failure_path": relative(ATTEMPT_01_FAILURE),
            "failure_sha256": ATTEMPT_01_FAILURE_SHA256,
        },
        "preserved_a08": {
            "worker_sha256": a09.A08_WORKER_SHA256,
            "report_sha256": a09.A08_REPORT_SHA256,
        },
        "selection": {
            "selected_constraint_count": len(runtime_constraints),
            "all_edges_below_0_70_selected": True,
            "minimum_additional_near_0_94_edges_selected_for_median": True,
        },
        "constraints": constraint_evidence,
        "caps_unchanged": {
            "ring_1_m": a09.RING_1_CAP_M,
            "ring_2_m": a09.RING_2_CAP_M,
            "deep_interior_m": a09.DEEP_INTERIOR_CAP_M,
            "base_fit_maximum_m": a09.TOTAL_BASE_FIT_CAP_M,
            "base_fit_p95_m": a09.FIT_P95_CAP_M,
            "base_fit_rms_m": a09.FIT_RMS_CAP_M,
            "a06_relief_m": a09.RELIEF_CAP_M,
            "combined_m": a09.COMBINED_CAP_M,
        },
    }
    pre_cap_path = ACTIVE_OUTPUT / "PRE_CAP_DIAGNOSTIC.json"
    atomic_write_json(pre_cap_path, pre_cap)

    topology_mismatches = [
        record
        for record in constraint_evidence
        if record["a08_topology_comparison"] is not None
        and not record["a08_topology_comparison"][
            "topology_ratio_within_tolerance"
        ]
    ]
    infeasible_minima = [
        record
        for record in constraint_evidence
        if not record["closest_linear_slope_minimum"]["within_ring_1_cap"]
    ]
    if topology_mismatches:
        raise RuntimeError(
            "observed A09/A08 midpoint plane-height ratio differs from 1.5"
        )
    if infeasible_minima:
        raise RuntimeError(
            "closest linear seam-slope minimum exceeds unchanged ring-one cap"
        )

    count = len(vertices)
    laplacian = np.zeros((count, count), dtype=np.float64)
    for vertex in vertices:
        row = vertex_index[vertex]
        linked = sorted(neighbors[vertex], key=lambda item: int(item.index))
        laplacian[row, row] = 1.0
        reciprocal = 1.0 / len(linked)
        for neighbor in linked:
            laplacian[row, vertex_index[neighbor]] -= reciprocal
    first_energy = laplacian.T @ laplacian
    second_operator = laplacian @ laplacian
    second_energy = second_operator.T @ second_operator
    full_hessian = Fidelity_WEIGHT * np.eye(count, dtype=np.float64)
    full_hessian += FIRST_DIFFERENTIAL_WEIGHT * first_energy
    full_hessian += BIHARMONIC_WEIGHT * second_energy

    free_rows = [vertex_index[vertex] for vertex in free_vertices]
    hessian = full_hessian[np.ix_(free_rows, free_rows)].copy()
    target = np.zeros((len(free_vertices), 3), dtype=np.float64)
    soft_records = []
    for vertex in free_vertices:
        distance = int(distances[vertex])
        if distance == 1:
            weight = RING_1_PLANE_WEIGHT
            cap = a09.RING_1_CAP_M
            kind = "ring_1_full_relative_weight"
        elif distance == 2:
            weight = RING_2_PLANE_WEIGHT
            cap = a09.RING_2_CAP_M
            kind = "ring_2_0_35_relative_weight"
        else:
            continue
        requested = a09.capped_vector(
            a09.weighted_plane_target(base_world[vertex], planes), cap
        )
        row = free_index[vertex]
        hessian[row, row] += weight
        target[row, :] += weight * np.asarray(
            tuple(requested), dtype=np.float64
        )
        soft_records.append(
            {
                "vertex_index_before_final_reindex": int(vertex.index),
                "graph_ring": distance,
                "kind": kind,
                "weight": weight,
                "capped_target_world_m": a09.a08.vector_record(requested),
                "capped_target_length_m": float(requested.length),
            }
        )

    constraint_count = len(runtime_constraints)
    cx = np.zeros((constraint_count, len(free_vertices)), dtype=np.float64)
    cy = np.zeros_like(cx)
    cz = np.zeros_like(cx)
    right_hand_side = np.zeros(constraint_count, dtype=np.float64)
    for row, constraint in enumerate(runtime_constraints):
        support = constraint["support"]
        if support not in free_index:
            raise RuntimeError("linear seam support is unexpectedly frozen")
        column = free_index[support]
        coefficient = constraint["coefficient"]
        cx[row, column] = float(coefficient.x)
        cy[row, column] = float(coefficient.y)
        cz[row, column] = float(coefficient.z)
        right_hand_side[row] = float(constraint["rhs"])

    try:
        unconstrained = np.linalg.solve(hessian, target)
        inverse_cx = np.linalg.solve(hessian, cx.T)
        inverse_cy = np.linalg.solve(hessian, cy.T)
        inverse_cz = np.linalg.solve(hessian, cz.T)
    except np.linalg.LinAlgError as exc:
        raise RuntimeError(f"attempt_02 screened KKT base solve failed: {exc}") from exc
    schur = cx @ inverse_cx + cy @ inverse_cy + cz @ inverse_cz
    residual_target = right_hand_side - (
        cx @ unconstrained[:, 0]
        + cy @ unconstrained[:, 1]
        + cz @ unconstrained[:, 2]
    )
    try:
        multipliers = np.linalg.solve(schur, residual_target)
        schur_method = "direct_solve"
    except np.linalg.LinAlgError:
        multipliers, _residuals, rank, _singular = np.linalg.lstsq(
            schur, residual_target, rcond=None
        )
        schur_method = f"least_squares_rank_{int(rank)}"
    solved = unconstrained.copy()
    solved[:, 0] += inverse_cx @ multipliers
    solved[:, 1] += inverse_cy @ multipliers
    solved[:, 2] += inverse_cz @ multipliers

    solved_world = {vertex: Vector() for vertex in vertices}
    for vertex in free_vertices:
        solved_world[vertex] = Vector(
            tuple(float(value) for value in solved[free_index[vertex], :])
        )
    linear_residuals = (
        cx @ solved[:, 0]
        + cy @ solved[:, 1]
        + cz @ solved[:, 2]
        - right_hand_side
    )
    maximum_constraint_residual = max(
        (abs(float(value)) for value in linear_residuals), default=0.0
    )

    movement_values = [solved_world[vertex].length for vertex in vertices]
    distribution = a09.displacement_distribution(movement_values)
    ring_distributions = {}
    for label, predicate in (
        ("ring_0", lambda distance: distance == 0),
        ("ring_1", lambda distance: distance == 1),
        ("ring_2", lambda distance: distance == 2),
        ("deep_interior", lambda distance: distance >= 3),
    ):
        ring_distributions[label] = a09.displacement_distribution(
            [
                solved_world[vertex].length
                for vertex in vertices
                if predicate(int(distances[vertex]))
            ]
        )
    pre_apply_checks = {
        "linear_constraint_residual_at_most_20nm": maximum_constraint_residual
        <= CONSTRAINT_RESIDUAL_TOLERANCE_M,
        "boundary_displacement_exact_zero": float(
            ring_distributions["ring_0"]["maximum_m"]
        )
        <= a09.MOVEMENT_EPSILON_M,
        "ring_1_cap": float(ring_distributions["ring_1"]["maximum_m"])
        <= a09.RING_1_CAP_M + a09.MOVEMENT_EPSILON_M,
        "ring_2_cap": float(ring_distributions["ring_2"]["maximum_m"])
        <= a09.RING_2_CAP_M + a09.MOVEMENT_EPSILON_M,
        "deep_cap": float(ring_distributions["deep_interior"]["maximum_m"])
        <= a09.DEEP_INTERIOR_CAP_M + a09.MOVEMENT_EPSILON_M,
        "overall_cap": float(distribution["maximum_m"])
        <= a09.TOTAL_BASE_FIT_CAP_M + a09.MOVEMENT_EPSILON_M,
        "p95_cap": float(distribution["p95_m"])
        <= a09.FIT_P95_CAP_M + a09.MOVEMENT_EPSILON_M,
        "rms_cap": float(distribution["rms_m"])
        <= a09.FIT_RMS_CAP_M + a09.MOVEMENT_EPSILON_M,
    }
    if not all(pre_apply_checks.values()):
        atomic_write_json(
            ACTIVE_OUTPUT / "SOLVER_DIAGNOSTIC.json",
            {
                "schema": "kira.avatar.r24.a09_attempt02.solver_diagnostic.v1",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "status": "FAIL_CLOSED_BEFORE_GEOMETRY_APPLICATION",
                "schur_method": schur_method,
                "maximum_constraint_residual_m": maximum_constraint_residual,
                "distribution": distribution,
                "ring_distributions": ring_distributions,
                "checks": pre_apply_checks,
            },
        )
        raise RuntimeError("attempt_02 KKT solution violates an unchanged movement cap")

    world_to_local = body.matrix_world.inverted().to_3x3()
    for vertex in vertices:
        vertex.co = base_local[vertex] + world_to_local @ solved_world[vertex]
    for vertex in seam_vertices:
        vertex.co = base_local[vertex].copy()
    bm.normal_update()
    shape = a09.local_shape_quality(body, patch_faces, baseline_normals)
    seam = a09.a08.seam_edge_records(
        body, patch_faces, seam_edges, original_ids, parameters
    )
    seam_values = [float(record["normal_dot"]) for record in seam["records"]]
    seam_minimum = min(seam_values, default=-1.0)
    seam_median = statistics.median(seam_values) if seam_values else -1.0
    seam_dihedral = math.degrees(
        math.acos(max(-1.0, min(1.0, seam_minimum)))
    )
    intersections = a09.exact_patch_intersection_summary(bm, patch_faces)
    post_checks = {
        **pre_apply_checks,
        "orientation_preserved": bool(shape["orientations_preserved"]),
        "nondegenerate": float(shape["minimum_face_area_world_m2"]) > 1.0e-10,
        "edge_ratio_at_most_8": float(shape["maximum_edge_ratio"])
        <= a09.MAXIMUM_EDGE_RATIO,
        "patch_exact_intersections_zero": intersections[
            "patch_genuine_pair_count"
        ]
        == 0,
        "whole_exact_intersections_29": intersections[
            "whole_genuine_pair_count"
        ]
        == a09.INHERITED_WHOLE_INTERSECTIONS,
        "seam_minimum_at_least_0_70": seam_minimum >= 0.70,
        "seam_median_at_least_0_94": seam_median >= 0.94,
        "seam_dihedral_at_most_45": seam_dihedral <= 45.0,
    }
    solver_diagnostic = {
        "schema": "kira.avatar.r24.a09_attempt02.solver_diagnostic.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "BASE_FIT_HARD_GATES_PASS"
            if all(post_checks.values())
            else "BASE_FIT_HARD_GATE_FAILURE"
        ),
        "method": "ACTIVE_LINEAR_SEAM_SLOPE_SCHUR_KKT_COUPLED_L_L2_V1",
        "hessian_dimension": len(free_vertices),
        "constraint_count": constraint_count,
        "schur_method": schur_method,
        "maximum_constraint_residual_m": maximum_constraint_residual,
        "lagrange_multipliers": [float(value) for value in multipliers],
        "soft_constraint_records": soft_records,
        "distribution": distribution,
        "ring_distributions": ring_distributions,
        "shape": shape,
        "seam_minimum_dot": seam_minimum,
        "seam_median_dot": seam_median,
        "maximum_seam_dihedral_degrees": seam_dihedral,
        "intersections": intersections,
        "checks": post_checks,
    }
    atomic_write_json(ACTIVE_OUTPUT / "SOLVER_DIAGNOSTIC.json", solver_diagnostic)
    if not all(post_checks.values()):
        for vertex in vertices:
            vertex.co = base_local[vertex].copy()
        bm.normal_update()
        raise RuntimeError("attempt_02 base fit failed a hard geometric gate")

    selected_by_support = {
        int(constraint["support"].index): constraint["record"]
        for constraint in runtime_constraints
    }
    movement_records = []
    for vertex in vertices:
        displacement = solved_world[vertex]
        if displacement.length <= a09.MOVEMENT_EPSILON_M:
            continue
        selected = selected_by_support.get(int(vertex.index))
        movement_records.append(
            {
                "vertex_index_before_final_reindex": int(vertex.index),
                "original_vertex_id": int(original_ids.get(vertex, -1)),
                "graph_ring": int(distances[vertex]),
                "boundary_vertex_ids": (
                    list(selected["boundary_vertex_ids"])
                    if selected is not None
                    else []
                ),
                "selected_hard_seam_support": selected is not None,
                "applied_world_vector_m": a09.a08.vector_record(displacement),
                "applied_world_m": float(displacement.length),
            }
        )
    accepted_trial = {
        "scale": 1.0,
        "passed": True,
        "checks": post_checks,
        "shape": shape,
        "seam_minimum_dot": seam_minimum,
        "seam_median_dot": seam_median,
        "maximum_seam_dihedral_degrees": seam_dihedral,
        "intersections": intersections,
        "distribution": distribution,
        "ring_maxima_m": {
            "0": float(ring_distributions["ring_0"]["maximum_m"]),
            "1": float(ring_distributions["ring_1"]["maximum_m"]),
            "2": float(ring_distributions["ring_2"]["maximum_m"]),
            "deep": float(ring_distributions["deep_interior"]["maximum_m"]),
        },
    }
    return {
        "method": "ACTIVE_LINEAR_SEAM_SLOPE_SCHUR_KKT_COUPLED_L_L2_V1",
        "absolute_position_minimal_surface_solve_used": False,
        "laplacian_shape": list(map(int, laplacian.shape)),
        "free_hessian_shape": list(map(int, hessian.shape)),
        "fidelity_weight": Fidelity_WEIGHT,
        "first_differential_weight": FIRST_DIFFERENTIAL_WEIGHT,
        "biharmonic_weight": BIHARMONIC_WEIGHT,
        "ring_1_soft_constraint_weight": RING_1_PLANE_WEIGHT,
        "ring_2_soft_constraint_weight": RING_2_PLANE_WEIGHT,
        "ring_2_relative_weight": 0.35,
        "selected_hard_constraint_count": constraint_count,
        "selected_hard_constraints": constraint_evidence,
        "constraint_records": constraint_evidence,
        "linear_constraint_maximum_residual_m": maximum_constraint_residual,
        "schur_method": schur_method,
        "backtracking_used": False,
        "backtracking_reason": "scaling would invalidate active hard seam rows",
        "backtracking_trials": [accepted_trial],
        "accepted_trial": accepted_trial,
        "movement_records": movement_records,
        "movement_distribution": distribution,
        "ring_distributions": ring_distributions,
        "targeted_support_vertex_count": constraint_count,
        "all_other_fairing_displacement_zero": len(movement_records)
        == constraint_count,
        "maximum_support_movement_m": max(
            (
                float(record["applied_world_m"])
                for record in movement_records
                if record["selected_hard_seam_support"]
            ),
            default=0.0,
        ),
        "maximum_ring_2_applied_world_m": float(
            ring_distributions["ring_2"]["maximum_m"]
        ),
        "sharp_boundary_edges_cleared": False,
        "boundary_displacement_exact_zero": float(
            ring_distributions["ring_0"]["maximum_m"]
        )
        <= a09.MOVEMENT_EPSILON_M,
        "caps_m": {
            "ring_1": a09.RING_1_CAP_M,
            "ring_2": a09.RING_2_CAP_M,
            "deep_interior": a09.DEEP_INTERIOR_CAP_M,
            "overall": a09.TOTAL_BASE_FIT_CAP_M,
            "p95": a09.FIT_P95_CAP_M,
            "rms": a09.FIT_RMS_CAP_M,
        },
    }


def main() -> None:
    global ACTIVE_OUTPUT, SOURCE_FACE_ID_BY_VERTICES
    worker = Path(__file__).resolve()
    for path, expected, label in (
        (SOURCE, SOURCE_SHA256, "sealed R19 source"),
        (ATTEMPT_01_WORKER, ATTEMPT_01_WORKER_SHA256, "attempt_01 worker"),
        (ATTEMPT_01_FAILURE, ATTEMPT_01_FAILURE_SHA256, "attempt_01 failure"),
        (PROPOSAL, PROPOSAL_SHA256, "attempt_02 proposal"),
        (a09.A08_WORKER, a09.A08_WORKER_SHA256, "preserved A08 worker"),
        (a09.A08_REPORT, a09.A08_REPORT_SHA256, "preserved A08 report"),
        (a09.A06_REPORT, a09.A06_REPORT_SHA256, "preserved A06 report"),
        (
            a09.a08.BOUND_R19_EVIDENCE,
            a09.a08.BOUND_R19_EVIDENCE_SHA256,
            "bound R19 evidence",
        ),
    ):
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"{label} hash drifted")

    ACTIVE_OUTPUT = a09.allocate_output()
    if ACTIVE_OUTPUT.name != "attempt_02":
        raise RuntimeError(
            f"append-only attempt slot is {ACTIVE_OUTPUT.name}, expected attempt_02"
        )
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    body = bpy.data.objects.get(BODY_NAME)
    rig = bpy.data.objects.get(RIG_NAME)
    if body is None or rig is None:
        raise RuntimeError("exact R19 body or native rig is absent")
    a09.a08.r24_base.clear_pose(rig)
    source_shape_key_count = (
        len(body.data.shape_keys.key_blocks) if body.data.shape_keys else 0
    )
    preflight = a09.a08.original_patch_preflight(body)
    SOURCE_FACE_ID_BY_VERTICES = {
        frozenset(map(int, preflight["faces"][face_index])): int(face_index)
        for face_index in preflight["patch_faces"]
    }

    prior_solver = a09.solve_coupled_fair_fit
    a09.solve_coupled_fair_fit = coupled_linear_slope_fit
    try:
        applied = a09.refine_and_shape(body, rig, preflight)
    finally:
        a09.solve_coupled_fair_fit = prior_solver
    gates = a09.topology_and_semantic_gates(body, applied)
    render_directory = ACTIVE_OUTPUT / "private_owner_review"
    renders = a09.a08.r24_render.render_evidence(body, applied, render_directory)
    paired = a09.render_uniform_clay_pairs_without_subdivision(
        render_directory, applied
    )
    renders["rendered"].extend(record["filename"] for record in paired)
    renders["paired_subdivision_diagnostics"] = paired

    report = {
        "schema": "kira.avatar.r24.a09_attempt02_linear_slope_simulation.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "NO_SAVE_STRUCTURAL_GATES_PASS_VISUAL_OWNER_REVIEW_REQUIRED"
            if gates["passed"]
            else "NO_SAVE_STRUCTURAL_OR_SEMANTIC_GATE_FAILURE_RETAINED_FOR_DIAGNOSIS"
        ),
        "source": {
            "path": relative(SOURCE),
            "bytes": SOURCE.stat().st_size,
            "sha256": sha256(SOURCE),
            "unchanged": sha256(SOURCE) == SOURCE_SHA256,
            "body": BODY_NAME,
            "rig": RIG_NAME,
            "source_shape_key_count": source_shape_key_count,
        },
        "worker": {
            "path": relative(worker),
            "bytes": worker.stat().st_size,
            "sha256": sha256(worker),
        },
        "preserved_evidence": {
            "attempt_01_worker": {
                "path": relative(ATTEMPT_01_WORKER),
                "sha256": ATTEMPT_01_WORKER_SHA256,
                "unchanged": sha256(ATTEMPT_01_WORKER)
                == ATTEMPT_01_WORKER_SHA256,
            },
            "attempt_01_failure": {
                "path": relative(ATTEMPT_01_FAILURE),
                "sha256": ATTEMPT_01_FAILURE_SHA256,
                "unchanged": sha256(ATTEMPT_01_FAILURE)
                == ATTEMPT_01_FAILURE_SHA256,
            },
            "a08_worker": {
                "path": relative(a09.A08_WORKER),
                "sha256": a09.A08_WORKER_SHA256,
            },
            "a08_report": {
                "path": relative(a09.A08_REPORT),
                "sha256": a09.A08_REPORT_SHA256,
            },
            "a06_report": {
                "path": relative(a09.A06_REPORT),
                "sha256": a09.A06_REPORT_SHA256,
                "anatomical_relief_reused_unchanged": True,
            },
        },
        "method": {
            "id": "R19_INTERNAL_EDGE_MIDPOINT_ACTIVE_LINEAR_SEAM_SLOPE_KKT_V2",
            "new_body_created": False,
            "source_body_saved": False,
            "normal_only_single_support_projection_used": False,
            "full_triangle_linear_slope_constraint_used": True,
            "frozen_boundary_displacement": "exact zero",
            "neighbor_distribution": "coupled first-differential and biharmonic energies",
            "backtracking_scaling_used": False,
            "reason_no_backtracking": "scaling would invalidate active seam constraints",
            "movement_caps_changed": False,
            "unchanged_a06_anatomical_relief": True,
            "shading_material_or_custom_normal_change": False,
        },
        "pre_cap_diagnostic": {
            "path": relative(ACTIVE_OUTPUT / "PRE_CAP_DIAGNOSTIC.json"),
            "sha256": sha256(ACTIVE_OUTPUT / "PRE_CAP_DIAGNOSTIC.json"),
            "written_before_solve": True,
        },
        "solver_diagnostic": {
            "path": relative(ACTIVE_OUTPUT / "SOLVER_DIAGNOSTIC.json"),
            "sha256": sha256(ACTIVE_OUTPUT / "SOLVER_DIAGNOSTIC.json"),
        },
        "preflight": {
            "patch_face_count": len(preflight["patch_faces"]),
            "patch_vertex_count": len(preflight["patch_vertices"]),
            "interior_vertex_count": len(preflight["interior_vertices"]),
            "boundary_vertex_count": len(preflight["boundary_vertices"]),
            "boundary_edge_count": len(preflight["boundary_edges"]),
            "boundary_position_sha256": preflight["boundary_position_sha256"],
            "boundary_edge_sha256": preflight["boundary_edge_sha256"],
            "topology": preflight["topology"],
        },
        "application": applied,
        "gates": gates,
        "renders": renders,
        "operations": {
            "blend_saved": False,
            "source_overwritten": False,
            "runtime_or_person_state_changed": False,
            "voice_model_device_files_touched": False,
            "activation_assignment_export_publication": False,
        },
        "truth": (
            "External private visual/topology simulation only. No internal tract, "
            "physiology, elimination, reproduction, pregnancy, sensation, subjective "
            "state, owner approval, runtime readiness, or biological function is "
            "implemented or claimed."
        ),
    }
    atomic_write_json(ACTIVE_OUTPUT / "SIMULATION_REPORT.json", report)
    print(json.dumps({"status": report["status"], "output": str(ACTIVE_OUTPUT)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback

        trace = traceback.format_exc()
        if ACTIVE_OUTPUT is not None:
            failure = {
                "schema": "kira.avatar.r24.a09_attempt02_linear_slope_failure.v1",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "status": "NO_SAVE_FAILURE_PRESERVED",
                "exception_type": type(exc).__name__,
                "exception": str(exc),
                "traceback": trace,
                "source": {
                    "path": relative(SOURCE),
                    "sha256": sha256(SOURCE) if SOURCE.is_file() else None,
                },
                "worker": {
                    "path": relative(Path(__file__).resolve()),
                    "sha256": sha256(Path(__file__).resolve()),
                },
                "pre_cap_diagnostic_present": (
                    ACTIVE_OUTPUT / "PRE_CAP_DIAGNOSTIC.json"
                ).is_file(),
                "solver_diagnostic_present": (
                    ACTIVE_OUTPUT / "SOLVER_DIAGNOSTIC.json"
                ).is_file(),
                "operations": {
                    "blend_saved": False,
                    "source_overwritten": False,
                    "runtime_or_person_state_changed": False,
                },
            }
            atomic_write_json(ACTIVE_OUTPUT / "FAILURE.json", failure)
        print(trace, file=sys.stderr)
        raise
