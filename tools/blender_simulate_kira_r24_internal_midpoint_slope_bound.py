"""No-save A09 attempt_03 authoritative midpoint-bound slope simulation.

The exact edge-to-midpoint map created during refinement is captured and
inverted directly.  No endpoint provenance is inferred from adjacency or
coordinates.  Attempt_01 and attempt_02 workers/evidence remain untouched.
All attempt_02 topology, caps, KKT solve, A06 relief, gates, and rendering are
otherwise unchanged.  This worker never saves a Blend.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_simulate_kira_r24_internal_midpoint_fair_surface as a09  # noqa: E402
from tools import blender_simulate_kira_r24_internal_midpoint_slope_constrained as a10  # noqa: E402


SOURCE = a09.SOURCE
SOURCE_SHA256 = a09.SOURCE_SHA256
BODY_NAME = a09.BODY_NAME
RIG_NAME = a09.RIG_NAME
OUTPUT_ROOT = a09.OUTPUT_ROOT

ATTEMPT_02_WORKER = ROOT / "tools/blender_simulate_kira_r24_internal_midpoint_slope_constrained.py"
ATTEMPT_02_WORKER_SHA256 = "1d791aeecf343df9232ffca0eb1c196736cc12708e6d5e0bef1bad14645c3311"
ATTEMPT_02_FAILURE = OUTPUT_ROOT / "attempt_02/FAILURE.json"
ATTEMPT_02_FAILURE_SHA256 = "d78f519a696ebe89a1967ae08d57c8d2054b9cef12ab5cac0ea84e1c7e74a431"

ACTIVE_OUTPUT: Path | None = None
AUTHORITATIVE_ENDPOINTS_BY_MIDPOINT: dict[Any, tuple[int, int]] = {}
AUTHORITATIVE_MAP_RECORDS: list[dict[str, Any]] = []
AUTHORITATIVE_MAP_SHA256: str | None = None
CAPTURE_INVOCATIONS = 0


def sha256(path: Path) -> str:
    return a09.sha256(path)


def relative(path: Path) -> str:
    return a09.relative(path)


def authoritative_map_state() -> dict[str, Any]:
    if len(AUTHORITATIVE_ENDPOINTS_BY_MIDPOINT) != a09.EXPECTED_INTERNAL_EDGES:
        raise RuntimeError(
            "authoritative midpoint map count is not the exact 547 internal edges"
        )
    if len({tuple(record["source_edge_vertex_ids"]) for record in AUTHORITATIVE_MAP_RECORDS}) != len(
        AUTHORITATIVE_MAP_RECORDS
    ):
        raise RuntimeError("authoritative midpoint map contains a duplicate source edge")
    if len({int(record["canonical_midpoint_id"]) for record in AUTHORITATIVE_MAP_RECORDS}) != len(
        AUTHORITATIVE_MAP_RECORDS
    ):
        raise RuntimeError("authoritative midpoint map contains a duplicate midpoint ID")
    if AUTHORITATIVE_MAP_SHA256 is None:
        raise RuntimeError("authoritative midpoint map hash was not initialized")
    return {
        "binding_source": "refinement midpoint_by_edge creation map inverted directly",
        "adjacency_inference_used": False,
        "coordinate_inference_used": False,
        "count": len(AUTHORITATIVE_MAP_RECORDS),
        "expected_count": a09.EXPECTED_INTERNAL_EDGES,
        "canonical_sha256": AUTHORITATIVE_MAP_SHA256,
        "capture_invocations": CAPTURE_INVOCATIONS,
        "records": AUTHORITATIVE_MAP_RECORDS,
    }


def capture_authoritative_refinement_map(
    body: bpy.types.Object,
    record: Mapping[str, Any],
    midpoint_by_edge: Mapping[tuple[int, int], Any],
    original_ids: Mapping[Any, int],
):
    """Capture exact construction provenance, then call A09's unchanged template."""
    global AUTHORITATIVE_MAP_SHA256, CAPTURE_INVOCATIONS
    CAPTURE_INVOCATIONS += 1
    observed = {
        midpoint: tuple(sorted(map(int, endpoint_ids)))
        for endpoint_ids, midpoint in midpoint_by_edge.items()
    }
    if not AUTHORITATIVE_ENDPOINTS_BY_MIDPOINT:
        AUTHORITATIVE_ENDPOINTS_BY_MIDPOINT.update(observed)
        records = sorted(
            (
                {
                    "canonical_midpoint_id": int(original_ids[midpoint]),
                    "source_edge_vertex_ids": list(endpoint_ids),
                }
                for midpoint, endpoint_ids in observed.items()
            ),
            key=lambda item: (
                tuple(item["source_edge_vertex_ids"]),
                int(item["canonical_midpoint_id"]),
            ),
        )
        AUTHORITATIVE_MAP_RECORDS.extend(records)
        AUTHORITATIVE_MAP_SHA256 = a09.a08.canonical_sha256(records)
    else:
        if len(observed) != len(AUTHORITATIVE_ENDPOINTS_BY_MIDPOINT):
            raise RuntimeError("authoritative midpoint map count changed during refinement")
        for midpoint, endpoints in observed.items():
            if AUTHORITATIVE_ENDPOINTS_BY_MIDPOINT.get(midpoint) != endpoints:
                raise RuntimeError("authoritative midpoint binding changed during refinement")
    authoritative_map_state()
    return ORIGINAL_FACE_REFINEMENT_TEMPLATES(
        body, record, midpoint_by_edge, original_ids
    )


def authoritative_endpoint_lookup(
    support: Any,
    original_ids: Mapping[Any, int],
) -> tuple[int, int]:
    del original_ids
    state = authoritative_map_state()
    endpoints = AUTHORITATIVE_ENDPOINTS_BY_MIDPOINT.get(support)
    if endpoints is None:
        raise RuntimeError(
            f"selected support {support.index} is missing from authoritative midpoint map "
            f"{state['canonical_sha256']}"
        )
    if len(endpoints) != 2 or endpoints[0] == endpoints[1]:
        raise RuntimeError("selected authoritative midpoint binding is inconsistent")
    return endpoints


def midpoint_bound_constraint_records(body, planes, original_ids):
    runtime, evidence = ORIGINAL_LINEAR_SLOPE_RECORDS(body, planes, original_ids)
    state = authoritative_map_state()
    for constraint, runtime_record in zip(evidence, runtime):
        support = runtime_record["support"]
        exact_pair = authoritative_endpoint_lookup(support, original_ids)
        if list(exact_pair) != list(constraint["support_source_endpoint_ids"]):
            raise RuntimeError("selected endpoint pair disagrees with authoritative map")
        constraint["authoritative_midpoint_binding"] = {
            "map_count": state["count"],
            "map_sha256": state["canonical_sha256"],
            "selected_endpoint_pair": list(exact_pair),
            "support_canonical_midpoint_id": int(
                constraint["support_canonical_id"]
            ),
            "binding_present_exactly_once": sum(
                1
                for record in state["records"]
                if int(record["canonical_midpoint_id"])
                == int(constraint["support_canonical_id"])
                and list(record["source_edge_vertex_ids"]) == list(exact_pair)
            )
            == 1,
        }
        if not constraint["authoritative_midpoint_binding"][
            "binding_present_exactly_once"
        ]:
            raise RuntimeError("selected midpoint binding is missing or duplicated")
    return runtime, evidence


def inject_map_into_pre_cap(path: Path, value: Mapping[str, Any]) -> None:
    document = dict(value)
    if path.name == "PRE_CAP_DIAGNOSTIC.json":
        document["authoritative_midpoint_endpoint_map"] = authoritative_map_state()
        document["attempt_03_binding_policy"] = {
            "adjacency_inference_used": False,
            "coordinate_inference_used": False,
            "missing_duplicate_or_inconsistent_binding": "FAIL_CLOSED",
        }
    ORIGINAL_ATOMIC_WRITE_JSON(path, document)


ORIGINAL_FACE_REFINEMENT_TEMPLATES = a09.face_refinement_templates
ORIGINAL_ENDPOINT_LOOKUP = a10.source_endpoint_ids_for_midpoint
ORIGINAL_LINEAR_SLOPE_RECORDS = a10.linear_slope_constraint_records
ORIGINAL_ATOMIC_WRITE_JSON = a10.atomic_write_json


def main() -> None:
    global ACTIVE_OUTPUT
    worker = Path(__file__).resolve()
    for path, expected, label in (
        (SOURCE, SOURCE_SHA256, "sealed R19 source"),
        (a10.ATTEMPT_01_WORKER, a10.ATTEMPT_01_WORKER_SHA256, "attempt_01 worker"),
        (a10.ATTEMPT_01_FAILURE, a10.ATTEMPT_01_FAILURE_SHA256, "attempt_01 failure"),
        (ATTEMPT_02_WORKER, ATTEMPT_02_WORKER_SHA256, "attempt_02 worker"),
        (ATTEMPT_02_FAILURE, ATTEMPT_02_FAILURE_SHA256, "attempt_02 failure"),
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
    if ACTIVE_OUTPUT.name != "attempt_03":
        raise RuntimeError(
            f"append-only attempt slot is {ACTIVE_OUTPUT.name}, expected attempt_03"
        )
    a10.ACTIVE_OUTPUT = ACTIVE_OUTPUT
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

    prior_refinement_templates = a09.face_refinement_templates
    prior_solver = a09.solve_coupled_fair_fit
    prior_endpoint_lookup = a10.source_endpoint_ids_for_midpoint
    prior_constraint_records = a10.linear_slope_constraint_records
    prior_atomic_writer = a10.atomic_write_json
    a09.face_refinement_templates = capture_authoritative_refinement_map
    a09.solve_coupled_fair_fit = a10.coupled_linear_slope_fit
    a10.source_endpoint_ids_for_midpoint = authoritative_endpoint_lookup
    a10.linear_slope_constraint_records = midpoint_bound_constraint_records
    a10.atomic_write_json = inject_map_into_pre_cap
    try:
        applied = a09.refine_and_shape(body, rig, preflight)
    finally:
        a09.face_refinement_templates = prior_refinement_templates
        a09.solve_coupled_fair_fit = prior_solver
        a10.source_endpoint_ids_for_midpoint = prior_endpoint_lookup
        a10.linear_slope_constraint_records = prior_constraint_records
        a10.atomic_write_json = prior_atomic_writer

    gates = a09.topology_and_semantic_gates(body, applied)
    render_directory = ACTIVE_OUTPUT / "private_owner_review"
    renders = a09.a08.r24_render.render_evidence(body, applied, render_directory)
    paired = a09.render_uniform_clay_pairs_without_subdivision(
        render_directory, applied
    )
    renders["rendered"].extend(record["filename"] for record in paired)
    renders["paired_subdivision_diagnostics"] = paired
    map_state = authoritative_map_state()

    report = {
        "schema": "kira.avatar.r24.a09_attempt03_authoritative_bound_slope_simulation.v1",
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
            "attempt_01_worker_sha256": a10.ATTEMPT_01_WORKER_SHA256,
            "attempt_01_failure_sha256": a10.ATTEMPT_01_FAILURE_SHA256,
            "attempt_02_worker_sha256": ATTEMPT_02_WORKER_SHA256,
            "attempt_02_failure_sha256": ATTEMPT_02_FAILURE_SHA256,
            "a08_worker_sha256": a09.A08_WORKER_SHA256,
            "a08_report_sha256": a09.A08_REPORT_SHA256,
            "a06_report_sha256": a09.A06_REPORT_SHA256,
        },
        "method": {
            "id": "R19_INTERNAL_EDGE_MIDPOINT_AUTHORITATIVE_BOUND_LINEAR_SLOPE_KKT_V3",
            "new_body_created": False,
            "source_body_saved": False,
            "authoritative_midpoint_map_passed_from_refinement": True,
            "adjacency_endpoint_inference_used": False,
            "coordinate_endpoint_inference_used": False,
            "cap_solver_topology_relief_or_gate_change_from_attempt_02": False,
            "full_triangle_linear_slope_constraint_used": True,
            "frozen_boundary_displacement": "exact zero",
            "neighbor_distribution": "coupled first-differential and biharmonic energies",
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
    ORIGINAL_ATOMIC_WRITE_JSON(ACTIVE_OUTPUT / "SIMULATION_REPORT.json", report)
    print(json.dumps({"status": report["status"], "output": str(ACTIVE_OUTPUT)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback

        trace = traceback.format_exc()
        if ACTIVE_OUTPUT is not None:
            failure = {
                "schema": "kira.avatar.r24.a09_attempt03_authoritative_bound_slope_failure.v1",
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
                "authoritative_map_count": len(AUTHORITATIVE_MAP_RECORDS),
                "authoritative_map_sha256": AUTHORITATIVE_MAP_SHA256,
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
            ORIGINAL_ATOMIC_WRITE_JSON(ACTIVE_OUTPUT / "FAILURE.json", failure)
        print(trace, file=sys.stderr)
        raise
