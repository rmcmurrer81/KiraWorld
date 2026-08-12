"""No-save A09 attempt_06 component-only seam/relief simulation.

This worker is bound to the reviewed Attempt 06 proposal.  It regenerates the
accepted internal-edge-midpoint topology from the exact sealed R19 source,
changes only the explicitly listed seam-support/continuation masks and bounded
positive relief terms, produces private diagnostic renders, and never saves a
Blend.  It creates no internal tract or physiological/body-response system.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import sys
import traceback
from typing import Any, Mapping, Sequence

import bmesh
import bpy
from mathutils import Vector
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_simulate_kira_r24_internal_midpoint_fair_surface as a09  # noqa: E402
from tools import blender_simulate_kira_r24_internal_midpoint_slope_constrained as a10  # noqa: E402
from tools import blender_simulate_kira_r24_internal_midpoint_slope_bound as a11  # noqa: E402
from tools import blender_simulate_kira_r24_internal_midpoint_slope_measured as a12  # noqa: E402
from tools import blender_simulate_kira_r24_internal_midpoint_slope_median as a13  # noqa: E402


SOURCE = a09.SOURCE
SOURCE_SHA256 = a09.SOURCE_SHA256
BODY_NAME = a09.BODY_NAME
RIG_NAME = a09.RIG_NAME
OUTPUT_ROOT = a09.OUTPUT_ROOT

ATTEMPT_05_WORKER = ROOT / "tools/blender_simulate_kira_r24_internal_midpoint_slope_median.py"
ATTEMPT_05_WORKER_SHA256 = "d8fa5bf689990728fcb8ae936e8136c7e08faafe7bdb2c95c20ab89d26d3a0d8"
ATTEMPT_05_PRE_CAP = OUTPUT_ROOT / "attempt_05/PRE_CAP_DIAGNOSTIC.json"
ATTEMPT_05_PRE_CAP_SHA256 = "d1c34ae778fd102e458ba37d67bde1ba96fe3d5a3fde43144068023bda125532"
ATTEMPT_05_SOLVER = OUTPUT_ROOT / "attempt_05/SOLVER_DIAGNOSTIC.json"
ATTEMPT_05_SOLVER_SHA256 = "4400c8370761c82638ce14b533c5ed8ac61f0c79c5966830d43ab5d3594b4cfd"
ATTEMPT_05_REPORT = OUTPUT_ROOT / "attempt_05/SIMULATION_REPORT.json"
ATTEMPT_05_REPORT_SHA256 = "b62586187b811d66cac7017dbd193dd99fa0db55c90b5a382f24cdbe5329ca7b"
ATTEMPT_05_OUTCOME = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_05_OUTCOME.md"
ATTEMPT_05_OUTCOME_SHA256 = "9133a5fba0f37724ea175e800cd65020f306e800af613574d6edb5fec813e15f"
PROPOSAL = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_06_COMPONENT_ONLY_PROPOSAL.md"
PROPOSAL_SHA256 = "6ed7632fa98ac70f9378f2ed6ec2d33d155a577e294a53faf042405a44b4830c"

SUPERIOR_JOIN_EDGES = {
    (1841, 2474),
    (2474, 2996),
    (2994, 2996),
    (1674, 2994),
    (1671, 1674),
    (1671, 1676),
    (1089, 1676),
    (421, 1089),
}
SEVERE_FLANK_EDGES = {
    (1096, 1097),
    (1097, 1529),
    (2481, 2482),
    (2481, 2861),
}
REGULAR_FLANK_EDGES = {
    (1841, 1844),
    (421, 422),
    (422, 1225),
    (1844, 2577),
    (1096, 1225),
    (2482, 2577),
    (331, 1529),
    (1751, 2861),
    (1751, 1754),
    (331, 332),
    (1754, 1767),
    (332, 347),
    (347, 990),
    (1767, 2386),
    (1009, 2398),
    (1008, 1009),
    (990, 1016),
    (2386, 2405),
    (2398, 2404),
    (1008, 1015),
    (2404, 2405),
    (1015, 1016),
}
ALL_PROPOSED_SEAM_EDGES = (
    SUPERIOR_JOIN_EDGES | SEVERE_FLANK_EDGES | REGULAR_FLANK_EDGES
)
TARGET_BY_CLASS = {
    "SUPERIOR_JOIN_EDGES": 0.985,
    "SEVERE_FLANK_EDGES": 0.900,
    "REGULAR_FLANK_EDGES": 0.965,
}

SEVERE_RING_1_CAP_M = 0.002250
OTHER_RING_1_CAP_M = 0.001500
RING_2_CAP_M = 0.000900
DEEP_CAP_M = 0.000600
OVERALL_CAP_M = 0.002250
P95_CAP_M = 0.000900
RMS_CAP_M = 0.000450
RELIEF_CAP_M = 0.003000
COMBINED_CAP_M = 0.004500
RING_1_SOFT_WEIGHT = 420.0
RING_2_CONTINUATION_WEIGHT = 294.0
RING_2_OTHER_WEIGHT = 147.0
CONSTRAINT_RESIDUAL_TOLERANCE_M = 2.0e-8

ACTIVE_OUTPUT: Path | None = None
ORIGINAL_SELECTED_TARGETS = a10.selected_seam_targets
ORIGINAL_ENDPOINT_LOOKUP = a10.source_endpoint_ids_for_midpoint
ORIGINAL_LINEAR_RECORDS = a10.linear_slope_constraint_records
ORIGINAL_FEATURE_FUNCTION = a09.a08.feature_offset_and_tags
ORIGINAL_SMOOTHSTEP = a09.a08.smoothstep

RELIEF_SEQUENCE: deque[dict[str, Any]] = deque()
PENDING_FADE: dict[str, Any] | None = None
RELIEF_RECORDS: list[dict[str, Any]] = []
FADE_RECORDS: list[dict[str, Any]] = []


def sha256(path: Path) -> str:
    return a09.sha256(path)


def relative(path: Path) -> str:
    return a09.relative(path)


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    a11.ORIGINAL_ATOMIC_WRITE_JSON(path, value)


def edge_key(value: Sequence[int]) -> tuple[int, int]:
    first, second = map(int, value)
    return (first, second) if first < second else (second, first)


def edge_class(edge: tuple[int, int]) -> str:
    edge = edge_key(edge)
    if edge in SUPERIOR_JOIN_EDGES:
        return "SUPERIOR_JOIN_EDGES"
    if edge in SEVERE_FLANK_EDGES:
        return "SEVERE_FLANK_EDGES"
    if edge in REGULAR_FLANK_EDGES:
        return "REGULAR_FLANK_EDGES"
    raise RuntimeError(f"unclassified Attempt 06 seam edge {edge}")


def selected_seam_targets(
    planes: Sequence[Mapping[str, Any]],
) -> list[tuple[Mapping[str, Any], float, str]]:
    observed = {edge_key(record["edge_ids"]) for record in planes}
    if observed != ALL_PROPOSED_SEAM_EDGES:
        raise RuntimeError("Attempt 06 exact 34-edge seam classification drifted")
    selected = []
    for record in planes:
        key = edge_key(record["edge_ids"])
        classification = edge_class(key)
        target = TARGET_BY_CLASS[classification]
        if float(record["baseline_dot"]) < target:
            selected.append((record, target, classification))
    if not selected:
        raise RuntimeError("Attempt 06 selected no below-target seam rows")
    return sorted(selected, key=lambda item: edge_key(item[0]["edge_ids"]))


def class_cap(classification: str) -> float:
    return (
        SEVERE_RING_1_CAP_M
        if classification == "SEVERE_FLANK_EDGES"
        else OTHER_RING_1_CAP_M
    )


def constraint_records(body, planes, original_ids):
    """Generate measured rows, then bind exact class caps and midpoint truth."""
    runtime, evidence = ORIGINAL_LINEAR_RECORDS(body, planes, original_ids)
    state = a11.authoritative_map_state()
    for runtime_record, record in zip(runtime, evidence):
        support = runtime_record["support"]
        key = edge_key(record["boundary_vertex_ids"])
        classification = edge_class(key)
        cap = class_cap(classification)
        endpoints = a11.authoritative_endpoint_lookup(support, original_ids)
        if list(endpoints) != list(record["support_source_endpoint_ids"]):
            raise RuntimeError("Attempt 06 support disagrees with authoritative map")
        record["seam_class"] = classification
        record["class_target_dot"] = TARGET_BY_CLASS[classification]
        record["ring_1_cap_m"] = cap
        record["normal_only_minimum"]["within_ring_1_cap"] = (
            float(record["normal_only_minimum"]["length_m"])
            <= cap + a09.MOVEMENT_EPSILON_M
        )
        record["closest_linear_slope_minimum"]["within_ring_1_cap"] = (
            float(record["closest_linear_slope_minimum"]["length_m"])
            <= cap + a09.MOVEMENT_EPSILON_M
        )
        record["authoritative_midpoint_binding"] = {
            "map_count": state["count"],
            "map_sha256": state["canonical_sha256"],
            "selected_endpoint_pair": list(endpoints),
            "support_canonical_midpoint_id": int(record["support_canonical_id"]),
            "binding_present_exactly_once": sum(
                1
                for item in state["records"]
                if int(item["canonical_midpoint_id"])
                == int(record["support_canonical_id"])
                and list(item["source_edge_vertex_ids"]) == list(endpoints)
            )
            == 1,
        }
        if not record["authoritative_midpoint_binding"][
            "binding_present_exactly_once"
        ]:
            raise RuntimeError("Attempt 06 midpoint binding missing or duplicated")
        comparison = record.get("a08_topology_comparison")
        if comparison is None:
            record["a08_baseline_dot_agreement"] = {
                "applicable": False,
                "reason": "edge was not one of A08's four measured supports",
            }
        else:
            delta = abs(
                float(record["baseline_dot"])
                - float(comparison["a08_baseline_dot"])
            )
            passed = delta <= a12.BASELINE_DOT_AGREEMENT_TOLERANCE
            comparison["observed_ratio_is_diagnostic_only"] = True
            comparison["invalid_exact_1_5_ratio_equality_removed"] = True
            comparison["legacy_exact_1_5_ratio_within_tolerance"] = bool(
                comparison.get("topology_ratio_within_tolerance", False)
            )
            comparison["topology_ratio_within_tolerance"] = passed
            comparison["legacy_boolean_slot_semantics"] = (
                "A08_BASELINE_DOT_AGREEMENT_GATE"
            )
            record["a08_baseline_dot_agreement"] = {
                "applicable": True,
                "a09_measured_baseline_dot": float(record["baseline_dot"]),
                "a08_measured_baseline_dot": float(comparison["a08_baseline_dot"]),
                "absolute_delta": delta,
                "tolerance": a12.BASELINE_DOT_AGREEMENT_TOLERANCE,
                "passed": passed,
            }
        record["attempt06_gate"] = {
            "map_binding_exact": bool(
                record["authoritative_midpoint_binding"][
                    "binding_present_exactly_once"
                ]
            ),
            "baseline_dot_agreement": bool(
                not record["a08_baseline_dot_agreement"]["applicable"]
                or record["a08_baseline_dot_agreement"]["passed"]
            ),
            "closest_minimum_within_exact_class_cap": bool(
                record["closest_linear_slope_minimum"]["within_ring_1_cap"]
            ),
        }
    return runtime, evidence


def vertex_mask_records(vertices, original_ids, distances, parameters):
    records = []
    for vertex in sorted(vertices, key=lambda item: int(item.index)):
        u, t = parameters[vertex]
        records.append(
            {
                "vertex_index_before_final_reindex": int(vertex.index),
                "canonical_original_id": int(original_ids.get(vertex, -1)),
                "graph_ring": int(distances[vertex]),
                "u": round(float(u), 12),
                "t": round(float(t), 12),
            }
        )
    return records


def mask_entry(name, vertices, original_ids, distances, parameters):
    records = vertex_mask_records(vertices, original_ids, distances, parameters)
    return {
        "name": name,
        "count": len(records),
        "canonical_sha256": a09.a08.canonical_sha256(records),
        "records": records,
    }


def build_mask_evidence(
    planes,
    patch_vertices,
    patch_edges,
    seam_vertices,
    distances,
    original_ids,
    parameters,
):
    neighbors = a09.patch_neighbors(patch_vertices, patch_edges)
    observed_by_edge = {edge_key(plane["edge_ids"]): plane for plane in planes}
    if set(observed_by_edge) != ALL_PROPOSED_SEAM_EDGES:
        raise RuntimeError("Attempt 06 cannot bind every proposed seam edge")
    all_supports = {plane["support"] for plane in planes}
    if any(int(distances[vertex]) != 1 for vertex in all_supports):
        raise RuntimeError("Attempt 06 seam support is not in graph ring one")
    severe_supports = {
        observed_by_edge[edge]["support"] for edge in SEVERE_FLANK_EDGES
    }
    continuation_ring2 = {
        neighbor
        for support in all_supports
        for neighbor in neighbors[support]
        if int(distances[neighbor]) == 2
    }
    central = {
        vertex
        for vertex in patch_vertices
        if int(distances[vertex]) >= 2
        and abs(float(parameters[vertex][0])) <= 0.42
        and 0.22 <= float(parameters[vertex][1]) <= 0.82
    }
    occupied = set(seam_vertices) | all_supports | continuation_ring2 | central
    frozen = set(patch_vertices) - occupied
    masks = {
        "BOUNDARY_ZERO": set(seam_vertices),
        "ALL_RING1_SEAM_SUPPORTS": all_supports,
        "SEVERE_RING1_SUPPORTS": severe_supports,
        "SEAM_CONTINUATION_RING2": continuation_ring2,
        "CENTRAL_POSITIVE_RELIEF": central,
        "FROZEN_COMPONENT_REMAINDER": frozen,
    }
    if any(not value for value in masks.values()):
        raise RuntimeError("Attempt 06 produced an empty required vertex mask")
    names = list(masks)
    overlaps = []
    unexpected = []
    for first_index, first in enumerate(names):
        for second in names[first_index + 1 :]:
            shared = masks[first] & masks[second]
            if shared:
                record = {
                    "first": first,
                    "second": second,
                    "count": len(shared),
                    "allowed": {first, second}
                    == {"SEAM_CONTINUATION_RING2", "CENTRAL_POSITIVE_RELIEF"},
                }
                overlaps.append(record)
                if not record["allowed"]:
                    unexpected.append(record)
    if unexpected:
        raise RuntimeError("Attempt 06 vertex masks overlap outside the allowed pair")
    edge_masks = {}
    for name, values in (
        ("SUPERIOR_JOIN_EDGES", SUPERIOR_JOIN_EDGES),
        ("SEVERE_FLANK_EDGES", SEVERE_FLANK_EDGES),
        ("REGULAR_FLANK_EDGES", REGULAR_FLANK_EDGES),
    ):
        records = [list(edge) for edge in sorted(values)]
        edge_masks[name] = {
            "count": len(records),
            "canonical_sha256": a09.a08.canonical_sha256(records),
            "records": records,
        }
    evidence = {
        "edge_masks": edge_masks,
        "vertex_masks": {
            name: mask_entry(
                name, vertices, original_ids, distances, parameters
            )
            for name, vertices in masks.items()
        },
        "allowed_overlap": (
            "SEAM_CONTINUATION_RING2 with CENTRAL_POSITIVE_RELIEF only"
        ),
        "observed_overlaps": overlaps,
        "unexpected_overlap_count": len(unexpected),
    }
    evidence["canonical_sha256"] = a09.a08.canonical_sha256(evidence)
    return evidence, masks


def displacement_distribution(values):
    return a09.displacement_distribution(values)


def attempt06_coupled_fit(
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
    global RELIEF_SEQUENCE
    if ACTIVE_OUTPUT is None:
        raise RuntimeError("Attempt 06 output was not allocated")
    vertices = sorted(patch_vertices, key=lambda vertex: int(vertex.index))
    vertex_index = {vertex: index for index, vertex in enumerate(vertices)}
    free_vertices = [vertex for vertex in vertices if vertex not in seam_vertices]
    free_index = {vertex: index for index, vertex in enumerate(free_vertices)}
    neighbors = a09.patch_neighbors(patch_vertices, patch_edges)
    if any(not neighbors.get(vertex) for vertex in vertices):
        raise RuntimeError("Attempt 06 fair-fit graph has an isolated vertex")
    base_local = {vertex: vertex.co.copy() for vertex in vertices}
    base_world = {vertex: body.matrix_world @ vertex.co for vertex in vertices}
    baseline_normals = {
        face: a09.a08.world_face_normal(body, face).copy() for face in patch_faces
    }
    planes = a09.seam_plane_records(body, patch_faces, seam_edges, original_ids)
    mask_evidence, masks = build_mask_evidence(
        planes,
        patch_vertices,
        patch_edges,
        seam_vertices,
        distances,
        original_ids,
        parameters,
    )
    runtime_constraints, constraint_evidence = constraint_records(
        body, planes, original_ids
    )
    pre_cap = {
        "schema": "kira.avatar.r24.a09_attempt06.pre_cap_diagnostic.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "WRITTEN_ATOMICALLY_BEFORE_COUPLED_SOLVE",
        "worker": {
            "path": relative(Path(__file__).resolve()),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "source": {"path": relative(SOURCE), "sha256": sha256(SOURCE)},
        "proposal": {"path": relative(PROPOSAL), "sha256": sha256(PROPOSAL)},
        "selection": {
            "active_constraint_count": len(runtime_constraints),
            "exact_class_targets": TARGET_BY_CLASS,
            "all_34_edges_classified": True,
        },
        "masks": mask_evidence,
        "constraints": constraint_evidence,
        "caps_m": {
            "boundary": 0.0,
            "severe_ring_1": SEVERE_RING_1_CAP_M,
            "other_ring_1": OTHER_RING_1_CAP_M,
            "ring_2": RING_2_CAP_M,
            "deep": DEEP_CAP_M,
            "overall": OVERALL_CAP_M,
            "p95": P95_CAP_M,
            "rms": RMS_CAP_M,
            "relief": RELIEF_CAP_M,
            "combined": COMBINED_CAP_M,
        },
        "soft_weights": {
            "ring_1": RING_1_SOFT_WEIGHT,
            "ring_2_continuation": RING_2_CONTINUATION_WEIGHT,
            "ring_2_other": RING_2_OTHER_WEIGHT,
            "screened_source_fidelity": 18.0,
            "first_differential": 1.0,
            "biharmonic": 0.20,
        },
        "authoritative_midpoint_endpoint_map": a11.authoritative_map_state(),
    }
    atomic_write_json(ACTIVE_OUTPUT / "PRE_CAP_DIAGNOSTIC.json", pre_cap)
    failed_constraints = [
        record
        for record in constraint_evidence
        if not all(record["attempt06_gate"].values())
    ]
    if failed_constraints:
        raise RuntimeError(
            "Attempt 06 exact midpoint/baseline/class-cap preflight failed"
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
    full_hessian = 18.0 * np.eye(count, dtype=np.float64)
    full_hessian += first_energy
    full_hessian += 0.20 * second_energy
    free_rows = [vertex_index[vertex] for vertex in free_vertices]
    hessian = full_hessian[np.ix_(free_rows, free_rows)].copy()
    target = np.zeros((len(free_vertices), 3), dtype=np.float64)
    severe_supports = masks["SEVERE_RING1_SUPPORTS"]
    continuation = masks["SEAM_CONTINUATION_RING2"]
    soft_records = []
    for vertex in free_vertices:
        distance = int(distances[vertex])
        if distance == 1:
            weight = RING_1_SOFT_WEIGHT
            cap = (
                SEVERE_RING_1_CAP_M
                if vertex in severe_supports
                else OTHER_RING_1_CAP_M
            )
            kind = (
                "ring_1_severe_support_2_25mm"
                if vertex in severe_supports
                else "ring_1_other_1_50mm"
            )
        elif distance == 2:
            cap = RING_2_CAP_M
            if vertex in continuation:
                weight = RING_2_CONTINUATION_WEIGHT
                kind = "ring_2_seam_continuation_0_70_of_ring_1"
            else:
                weight = RING_2_OTHER_WEIGHT
                kind = "ring_2_other_0_35_of_ring_1"
        else:
            continue
        requested = a09.capped_vector(
            a09.weighted_plane_target(base_world[vertex], planes), cap
        )
        row = free_index[vertex]
        hessian[row, row] += weight
        target[row, :] += weight * np.asarray(tuple(requested), dtype=np.float64)
        soft_records.append(
            {
                "vertex_index_before_final_reindex": int(vertex.index),
                "graph_ring": distance,
                "kind": kind,
                "weight": weight,
                "cap_m": cap,
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
            raise RuntimeError("Attempt 06 hard support is unexpectedly frozen")
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
        raise RuntimeError(f"Attempt 06 screened KKT base solve failed: {exc}") from exc
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

    movements = [solved_world[vertex].length for vertex in vertices]
    distribution = displacement_distribution(movements)
    ring_distributions = {}
    for label, predicate in (
        ("ring_0", lambda d: d == 0),
        ("ring_1", lambda d: d == 1),
        ("ring_2", lambda d: d == 2),
        ("deep_interior", lambda d: d >= 3),
    ):
        ring_distributions[label] = displacement_distribution(
            [
                solved_world[vertex].length
                for vertex in vertices
                if predicate(int(distances[vertex]))
            ]
        )
    severe_distribution = displacement_distribution(
        [solved_world[vertex].length for vertex in severe_supports]
    )
    other_ring1 = {
        vertex
        for vertex in vertices
        if int(distances[vertex]) == 1 and vertex not in severe_supports
    }
    other_ring1_distribution = displacement_distribution(
        [solved_world[vertex].length for vertex in other_ring1]
    )
    pre_apply_checks = {
        "linear_constraint_residual_at_most_20nm": maximum_constraint_residual
        <= CONSTRAINT_RESIDUAL_TOLERANCE_M,
        "boundary_displacement_exact_zero": float(
            ring_distributions["ring_0"]["maximum_m"]
        )
        <= a09.MOVEMENT_EPSILON_M,
        "severe_ring1_cap_2_25mm": float(severe_distribution["maximum_m"])
        <= SEVERE_RING_1_CAP_M + a09.MOVEMENT_EPSILON_M,
        "other_ring1_cap_1_50mm": float(
            other_ring1_distribution["maximum_m"]
        )
        <= OTHER_RING_1_CAP_M + a09.MOVEMENT_EPSILON_M,
        "ring2_cap_0_90mm": float(ring_distributions["ring_2"]["maximum_m"])
        <= RING_2_CAP_M + a09.MOVEMENT_EPSILON_M,
        "deep_cap_0_60mm": float(
            ring_distributions["deep_interior"]["maximum_m"]
        )
        <= DEEP_CAP_M + a09.MOVEMENT_EPSILON_M,
        "overall_cap_2_25mm": float(distribution["maximum_m"])
        <= OVERALL_CAP_M + a09.MOVEMENT_EPSILON_M,
        "p95_cap_0_90mm": float(distribution["p95_m"])
        <= P95_CAP_M + a09.MOVEMENT_EPSILON_M,
        "rms_cap_0_45mm": float(distribution["rms_m"])
        <= RMS_CAP_M + a09.MOVEMENT_EPSILON_M,
    }
    solver_base = {
        "schema": "kira.avatar.r24.a09_attempt06.solver_diagnostic.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "method": "ACTIVE_CLASS_LINEAR_SEAM_SLOPE_SCHUR_KKT_COUPLED_L_L2_V1",
        "hessian_dimension": len(free_vertices),
        "constraint_count": constraint_count,
        "schur_method": schur_method,
        "maximum_constraint_residual_m": maximum_constraint_residual,
        "lagrange_multipliers": [float(value) for value in multipliers],
        "soft_constraint_records": soft_records,
        "distribution": distribution,
        "ring_distributions": ring_distributions,
        "severe_ring1_distribution": severe_distribution,
        "other_ring1_distribution": other_ring1_distribution,
        "masks": mask_evidence,
    }
    if not all(pre_apply_checks.values()):
        atomic_write_json(
            ACTIVE_OUTPUT / "SOLVER_DIAGNOSTIC.json",
            {
                **solver_base,
                "status": "FAIL_CLOSED_BEFORE_GEOMETRY_APPLICATION",
                "checks": pre_apply_checks,
            },
        )
        raise RuntimeError("Attempt 06 KKT solution violates an exact movement cap")

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
    class_values = {name: [] for name in TARGET_BY_CLASS}
    class_records = []
    for record in seam["records"]:
        key = edge_key(record["boundary_vertex_ids"])
        classification = edge_class(key)
        value = float(record["normal_dot"])
        class_values[classification].append(value)
        class_records.append(
            {
                "edge": list(key),
                "class": classification,
                "target_dot": TARGET_BY_CLASS[classification],
                "achieved_dot": value,
                "passed": value >= TARGET_BY_CLASS[classification],
            }
        )
    seam_values = [float(record["normal_dot"]) for record in seam["records"]]
    seam_minimum = min(seam_values, default=-1.0)
    seam_median = statistics.median(seam_values) if seam_values else -1.0
    seam_dihedral = math.degrees(math.acos(max(-1.0, min(1.0, seam_minimum))))
    intersections = a09.exact_patch_intersection_summary(bm, patch_faces)
    post_checks = {
        **pre_apply_checks,
        "orientation_preserved": bool(shape["orientations_preserved"]),
        "nondegenerate": float(shape["minimum_face_area_world_m2"]) > 1.0e-10,
        "edge_ratio_at_most_8": float(shape["maximum_edge_ratio"])
        <= a09.MAXIMUM_EDGE_RATIO,
        "patch_exact_intersections_zero": intersections["patch_genuine_pair_count"]
        == 0,
        "whole_exact_intersections_29": intersections["whole_genuine_pair_count"]
        == a09.INHERITED_WHOLE_INTERSECTIONS,
        "superior_all_at_least_0_985": min(
            class_values["SUPERIOR_JOIN_EDGES"], default=-1.0
        )
        >= 0.985,
        "severe_all_at_least_0_900": min(
            class_values["SEVERE_FLANK_EDGES"], default=-1.0
        )
        >= 0.900,
        "regular_all_at_least_0_965": min(
            class_values["REGULAR_FLANK_EDGES"], default=-1.0
        )
        >= 0.965,
        "whole_seam_minimum_at_least_0_900": seam_minimum >= 0.900,
        "whole_seam_median_at_least_0_965": seam_median >= 0.965,
        "whole_seam_dihedral_at_most_25_841933": seam_dihedral <= 25.841933,
    }
    solver_diagnostic = {
        **solver_base,
        "status": (
            "BASE_FIT_HARD_GATES_PASS"
            if all(post_checks.values())
            else "BASE_FIT_HARD_GATE_FAILURE"
        ),
        "shape": shape,
        "seam_minimum_dot": seam_minimum,
        "seam_median_dot": seam_median,
        "maximum_seam_dihedral_degrees": seam_dihedral,
        "seam_class_records": class_records,
        "intersections": intersections,
        "checks": post_checks,
    }
    atomic_write_json(ACTIVE_OUTPUT / "SOLVER_DIAGNOSTIC.json", solver_diagnostic)
    if not all(post_checks.values()):
        for vertex in vertices:
            vertex.co = base_local[vertex].copy()
        bm.normal_update()
        raise RuntimeError("Attempt 06 base fit failed an exact structural gate")

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
    RELIEF_SEQUENCE = deque(
        {
            "vertex_index_before_final_reindex": int(vertex.index),
            "canonical_original_id": int(original_ids.get(vertex, -1)),
            "graph_ring": int(distances[vertex]),
            "u": float(parameters[vertex][0]),
            "t": float(parameters[vertex][1]),
            "central_positive_relief": vertex
            in masks["CENTRAL_POSITIVE_RELIEF"],
        }
        for vertex in vertices
    )
    return {
        "method": "ACTIVE_CLASS_LINEAR_SEAM_SLOPE_SCHUR_KKT_COUPLED_L_L2_V1",
        "absolute_position_minimal_surface_solve_used": False,
        "laplacian_shape": list(map(int, laplacian.shape)),
        "free_hessian_shape": list(map(int, hessian.shape)),
        "fidelity_weight": 18.0,
        "first_differential_weight": 1.0,
        "biharmonic_weight": 0.20,
        "ring_1_soft_constraint_weight": RING_1_SOFT_WEIGHT,
        "ring_2_continuation_weight": RING_2_CONTINUATION_WEIGHT,
        "ring_2_other_weight": RING_2_OTHER_WEIGHT,
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
        "severe_ring1_distribution": severe_distribution,
        "other_ring1_distribution": other_ring1_distribution,
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
        "boundary_displacement_exact_zero": bool(
            pre_apply_checks["boundary_displacement_exact_zero"]
        ),
        "caps_m": {
            "severe_ring_1": SEVERE_RING_1_CAP_M,
            "other_ring_1": OTHER_RING_1_CAP_M,
            "ring_2": RING_2_CAP_M,
            "deep_interior": DEEP_CAP_M,
            "overall": OVERALL_CAP_M,
            "p95": P95_CAP_M,
            "rms": RMS_CAP_M,
        },
        "mask_evidence": mask_evidence,
        "seam_class_records": class_records,
    }


def attempt06_feature_offset_and_tags(u: float, t: float):
    global PENDING_FADE
    if PENDING_FADE is not None:
        raise RuntimeError("Attempt 06 prior relief fade was not consumed")
    if not RELIEF_SEQUENCE:
        raise RuntimeError("Attempt 06 relief sequence exhausted early")
    expected = RELIEF_SEQUENCE.popleft()
    if (
        abs(float(u) - float(expected["u"])) > 1.0e-9
        or abs(float(t) - float(expected["t"])) > 1.0e-9
    ):
        raise RuntimeError("Attempt 06 relief vertex order/parameter binding drifted")
    original, tags = ORIGINAL_FEATURE_FUNCTION(u, t)
    delta = 0.0
    if expected["central_positive_relief"]:
        left_major = 0.00255 * a09.a08.gaussian2(u, t, -0.31, 0.46, 0.15, 0.25)
        right_major = 0.00242 * a09.a08.gaussian2(u, t, 0.32, 0.46, 0.15, 0.25)
        left_minor = 0.00134 * a09.a08.gaussian2(u, t, -0.095, 0.47, 0.050, 0.20)
        right_minor = 0.00122 * a09.a08.gaussian2(u, t, 0.108, 0.47, 0.052, 0.20)
        hood = 0.00110 * a09.a08.gaussian2(u, t, -0.006, 0.285, 0.120, 0.065)
        glans = 0.00044 * a09.a08.gaussian2(u, t, -0.010, 0.320, 0.045, 0.032)
        delta = (
            0.12 * (left_major + right_major)
            + 0.10 * (left_minor + right_minor)
            + 0.15 * (hood + glans)
        )
    adjusted = max(-RELIEF_CAP_M, min(RELIEF_CAP_M, float(original) + delta))
    record = {
        **expected,
        "original_offset_m": float(original),
        "positive_increment_before_clamp_m": float(delta),
        "adjusted_offset_before_fade_m": float(adjusted),
        "clamped_to_3mm": abs(float(original) + delta) > RELIEF_CAP_M,
    }
    RELIEF_RECORDS.append(record)
    PENDING_FADE = record
    return adjusted, tags


def attempt06_smoothstep(value: float) -> float:
    global PENDING_FADE
    if PENDING_FADE is None:
        return ORIGINAL_SMOOTHSTEP(value)
    record = PENDING_FADE
    distance = int(record["graph_ring"])
    expected_old_argument = (float(distance) - 1.0) / 2.5
    if abs(float(value) - expected_old_argument) > 1.0e-9:
        raise RuntimeError("Attempt 06 intercepted a non-seam-fade smoothstep call")
    new_argument = (float(distance) - 1.0) / 2.0
    result = ORIGINAL_SMOOTHSTEP(new_argument)
    FADE_RECORDS.append(
        {
            "vertex_index_before_final_reindex": int(
                record["vertex_index_before_final_reindex"]
            ),
            "graph_ring": distance,
            "old_argument": expected_old_argument,
            "new_argument": new_argument,
            "new_fade": float(result),
        }
    )
    PENDING_FADE = None
    return result


def attempt06_gates(body, applied):
    result = a09.topology_and_semantic_gates(body, applied)
    checks = dict(result["checks"])
    for obsolete in (
        "base_fit_ring1_at_most_1_50mm",
        "base_fit_overall_at_most_1_50mm",
        "unchanged_a06_relief_at_most_3mm",
    ):
        checks.pop(obsolete, None)
    base_fit = applied["base_fit"]
    class_records = base_fit["seam_class_records"]
    class_minima = {
        name: min(
            (
                float(record["achieved_dot"])
                for record in class_records
                if record["class"] == name
            ),
            default=-1.0,
        )
        for name in TARGET_BY_CLASS
    }
    masks = base_fit["mask_evidence"]
    checks.update(
        {
            "attempt06_all_34_edges_classified": sum(
                entry["count"] for entry in masks["edge_masks"].values()
            )
            == 34,
            "attempt06_no_unexpected_mask_overlap": masks[
                "unexpected_overlap_count"
            ]
            == 0,
            "attempt06_superior_minimum_0_985": class_minima[
                "SUPERIOR_JOIN_EDGES"
            ]
            >= 0.985,
            "attempt06_severe_minimum_0_900": class_minima[
                "SEVERE_FLANK_EDGES"
            ]
            >= 0.900,
            "attempt06_regular_minimum_0_965": class_minima[
                "REGULAR_FLANK_EDGES"
            ]
            >= 0.965,
            "attempt06_severe_ring1_at_most_2_25mm": float(
                base_fit["severe_ring1_distribution"]["maximum_m"]
            )
            <= SEVERE_RING_1_CAP_M + a09.MOVEMENT_EPSILON_M,
            "attempt06_other_ring1_at_most_1_50mm": float(
                base_fit["other_ring1_distribution"]["maximum_m"]
            )
            <= OTHER_RING_1_CAP_M + a09.MOVEMENT_EPSILON_M,
            "attempt06_base_fit_overall_at_most_2_25mm": float(
                base_fit["movement_distribution"]["maximum_m"]
            )
            <= OVERALL_CAP_M + a09.MOVEMENT_EPSILON_M,
            "attempt06_relief_at_most_3mm": float(
                applied["maximum_absolute_offset_m"]
            )
            <= RELIEF_CAP_M + 1.0e-12,
            "attempt06_combined_at_most_4_5mm": float(
                applied["combined_displacement"]["maximum_m"]
            )
            <= COMBINED_CAP_M + a09.MOVEMENT_EPSILON_M,
            "attempt06_relief_sequence_exact_753": len(RELIEF_RECORDS)
            == a09.EXPECTED_PATCH_VERTICES,
            "attempt06_fade_sequence_exact_753": len(FADE_RECORDS)
            == a09.EXPECTED_PATCH_VERTICES,
            "attempt06_relief_queue_consumed": len(RELIEF_SEQUENCE) == 0
            and PENDING_FADE is None,
            "attempt06_opening_specs_unchanged": a09.a08.canonical_sha256(
                a09.a08.OPENING_SPECS
            )
            == a09.a08.canonical_sha256(
                {
                    "urethral_meatus": {
                        "u": 0.0,
                        "t": 0.39,
                        "su": 0.055,
                        "st": 0.045,
                        "rim_height_m": 0.00034,
                        "cap_depth_m": 0.00042,
                    },
                    "vaginal_introitus": {
                        "u": 0.0,
                        "t": 0.55,
                        "su": 0.105,
                        "st": 0.090,
                        "rim_height_m": 0.00058,
                        "cap_depth_m": 0.00110,
                    },
                    "anal_verge": {
                        "u": 0.0,
                        "t": 0.88,
                        "su": 0.090,
                        "st": 0.060,
                        "rim_height_m": 0.00042,
                        "cap_depth_m": 0.00072,
                    },
                }
            ),
        }
    )
    result["checks"] = checks
    result["passed"] = all(checks.values())
    result["attempt06"] = {
        "class_minima": class_minima,
        "mask_canonical_sha256": masks["canonical_sha256"],
        "relief_record_sha256": a09.a08.canonical_sha256(RELIEF_RECORDS),
        "fade_record_sha256": a09.a08.canonical_sha256(FADE_RECORDS),
    }
    return result


def main() -> None:
    global ACTIVE_OUTPUT, PENDING_FADE
    worker = Path(__file__).resolve()
    for path, expected, label in (
        (SOURCE, SOURCE_SHA256, "sealed R19 source"),
        (ATTEMPT_05_WORKER, ATTEMPT_05_WORKER_SHA256, "attempt_05 worker"),
        (ATTEMPT_05_PRE_CAP, ATTEMPT_05_PRE_CAP_SHA256, "attempt_05 pre-cap"),
        (ATTEMPT_05_SOLVER, ATTEMPT_05_SOLVER_SHA256, "attempt_05 solver"),
        (ATTEMPT_05_REPORT, ATTEMPT_05_REPORT_SHA256, "attempt_05 report"),
        (ATTEMPT_05_OUTCOME, ATTEMPT_05_OUTCOME_SHA256, "attempt_05 outcome"),
        (PROPOSAL, PROPOSAL_SHA256, "authorized attempt_06 proposal"),
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
    if ACTIVE_OUTPUT.name != "attempt_06":
        raise RuntimeError(
            f"append-only attempt slot is {ACTIVE_OUTPUT.name}, expected attempt_06"
        )
    a11.AUTHORITATIVE_ENDPOINTS_BY_MIDPOINT.clear()
    a11.AUTHORITATIVE_MAP_RECORDS.clear()
    a11.AUTHORITATIVE_MAP_SHA256 = None
    a11.CAPTURE_INVOCATIONS = 0
    RELIEF_SEQUENCE.clear()
    RELIEF_RECORDS.clear()
    FADE_RECORDS.clear()
    PENDING_FADE = None

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
    a10.SOURCE_FACE_ID_BY_VERTICES = {
        frozenset(map(int, preflight["faces"][face_index])): int(face_index)
        for face_index in preflight["patch_faces"]
    }

    prior_refinement = a09.face_refinement_templates
    prior_solver = a09.solve_coupled_fair_fit
    prior_selected = a10.selected_seam_targets
    prior_endpoint = a10.source_endpoint_ids_for_midpoint
    prior_feature = a09.a08.feature_offset_and_tags
    prior_smoothstep = a09.a08.smoothstep
    prior_ring1_cap = a09.RING_1_CAP_M
    prior_overall_cap = a09.TOTAL_BASE_FIT_CAP_M
    a09.face_refinement_templates = a11.capture_authoritative_refinement_map
    a09.solve_coupled_fair_fit = attempt06_coupled_fit
    a10.selected_seam_targets = selected_seam_targets
    a10.source_endpoint_ids_for_midpoint = a11.authoritative_endpoint_lookup
    a09.a08.feature_offset_and_tags = attempt06_feature_offset_and_tags
    a09.a08.smoothstep = attempt06_smoothstep
    a09.RING_1_CAP_M = SEVERE_RING_1_CAP_M
    a09.TOTAL_BASE_FIT_CAP_M = OVERALL_CAP_M
    try:
        applied = a09.refine_and_shape(body, rig, preflight)
    finally:
        a09.face_refinement_templates = prior_refinement
        a09.solve_coupled_fair_fit = prior_solver
        a10.selected_seam_targets = prior_selected
        a10.source_endpoint_ids_for_midpoint = prior_endpoint
        a09.a08.feature_offset_and_tags = prior_feature
        a09.a08.smoothstep = prior_smoothstep
        a09.RING_1_CAP_M = prior_ring1_cap
        a09.TOTAL_BASE_FIT_CAP_M = prior_overall_cap
    if RELIEF_SEQUENCE or PENDING_FADE is not None:
        raise RuntimeError("Attempt 06 relief/fade sequence was not fully consumed")
    applied["attempt06_relief"] = {
        "central_mask_definition": "d>=2; abs(u)<=0.42; 0.22<=t<=0.82",
        "majora_positive_multiplier": 1.12,
        "minora_positive_multiplier": 1.10,
        "hood_glans_positive_multiplier": 1.15,
        "negative_opening_or_recess_terms_changed": False,
        "fade_formula": "smoothstep((d-1)/2)",
        "relief_records_sha256": a09.a08.canonical_sha256(RELIEF_RECORDS),
        "fade_records_sha256": a09.a08.canonical_sha256(FADE_RECORDS),
        "relief_record_count": len(RELIEF_RECORDS),
        "fade_record_count": len(FADE_RECORDS),
    }
    gates = attempt06_gates(body, applied)
    render_directory = ACTIVE_OUTPUT / "private_owner_review"
    renders = a09.a08.r24_render.render_evidence(body, applied, render_directory)
    paired = a09.render_uniform_clay_pairs_without_subdivision(
        render_directory, applied
    )
    renders["rendered"].extend(record["filename"] for record in paired)
    renders["paired_subdivision_diagnostics"] = paired
    map_state = a11.authoritative_map_state()
    report = {
        "schema": "kira.avatar.r24.a09_attempt06_component_only_simulation.v1",
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
        "proposal": {
            "path": relative(PROPOSAL),
            "sha256": sha256(PROPOSAL),
            "implemented_exactly": True,
        },
        "preserved_attempt_05": {
            "worker_sha256": ATTEMPT_05_WORKER_SHA256,
            "pre_cap_sha256": ATTEMPT_05_PRE_CAP_SHA256,
            "solver_sha256": ATTEMPT_05_SOLVER_SHA256,
            "report_sha256": ATTEMPT_05_REPORT_SHA256,
            "outcome_sha256": ATTEMPT_05_OUTCOME_SHA256,
        },
        "method": {
            "id": "R19_INTERNAL_MIDPOINT_CLASS_SEAM_PANEL_NEUTRALIZATION_V1",
            "new_body_created": False,
            "source_body_saved": False,
            "accepted_topology_regenerated_exactly": True,
            "authoritative_midpoint_map_controls": True,
            "boundary_displacement": "exact zero",
            "material_uv_custom_normal_or_sharp_change": False,
            "class_targets": TARGET_BY_CLASS,
            "positive_relief_only": True,
            "negative_opening_recess_change": False,
        },
        "authoritative_midpoint_endpoint_map": {
            "binding_source": map_state["binding_source"],
            "count": map_state["count"],
            "canonical_sha256": map_state["canonical_sha256"],
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
        "visual_gate": {
            "status": "PENDING_SEPARATE_INDEPENDENT_REVIEW",
            "structural_pass_does_not_override_visual_failure": True,
            "required": [
                "no continuous straight superior crease",
                "no readable triangular component outline",
                "no recessed panel transition",
                "central positive landmarks distinguishable",
                "no new inferior fold spike intersection or ring transition",
            ],
        },
        "operations": {
            "blend_saved": False,
            "source_overwritten": False,
            "runtime_or_person_state_changed": False,
            "activation_assignment_export_publication": False,
        },
        "truth": (
            "External private visual/topology simulation only. No internal tract, "
            "continence, elimination, reproduction, pregnancy, sensation, subjective "
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
        trace = traceback.format_exc()
        if ACTIVE_OUTPUT is not None:
            failure = {
                "schema": "kira.avatar.r24.a09_attempt06_component_only_failure.v1",
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
                "proposal_sha256": sha256(PROPOSAL) if PROPOSAL.is_file() else None,
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
