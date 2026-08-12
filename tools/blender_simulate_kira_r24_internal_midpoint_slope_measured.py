"""No-save A09 attempt_04 measured-geometry slope simulation.

This worker removes only the disproved exact-1.5 A09/A08 evidence equality.
The authoritative refinement map and directly measured support geometry govern
the unchanged attempt_02 KKT solve.  Observed ratios remain diagnostic; A08
baseline-dot agreement and exact measured slope-minimum cap feasibility remain
hard evidence gates.  No topology, weights, caps, relief, structural gates,
renders, or save policy change.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_simulate_kira_r24_internal_midpoint_fair_surface as a09  # noqa: E402
from tools import blender_simulate_kira_r24_internal_midpoint_slope_constrained as a10  # noqa: E402
from tools import blender_simulate_kira_r24_internal_midpoint_slope_bound as a11  # noqa: E402


SOURCE = a09.SOURCE
SOURCE_SHA256 = a09.SOURCE_SHA256
BODY_NAME = a09.BODY_NAME
RIG_NAME = a09.RIG_NAME
OUTPUT_ROOT = a09.OUTPUT_ROOT

ATTEMPT_03_WORKER = ROOT / "tools/blender_simulate_kira_r24_internal_midpoint_slope_bound.py"
ATTEMPT_03_WORKER_SHA256 = "9ee6a8ec91cdaafb95f7e61489742bde258c116a230c9a569bcecfc542063b77"
ATTEMPT_03_PRE_CAP = OUTPUT_ROOT / "attempt_03/PRE_CAP_DIAGNOSTIC.json"
ATTEMPT_03_PRE_CAP_SHA256 = "c73a2f175330c0fdee8a5b00ff46cb630d49299fd54ea29748b6748f80b1c8fd"
ATTEMPT_03_FAILURE = OUTPUT_ROOT / "attempt_03/FAILURE.json"
ATTEMPT_03_FAILURE_SHA256 = "ce5f0d1a3bf3b600aedb413280185774280301f9c5e4fa3487625b19c283346d"
BASELINE_DOT_AGREEMENT_TOLERANCE = 1.0e-5

ACTIVE_OUTPUT: Path | None = None


def sha256(path: Path) -> str:
    return a09.sha256(path)


def relative(path: Path) -> str:
    return a09.relative(path)


def measured_geometry_constraint_records(body, planes, original_ids):
    """Retain ratios diagnostically; bind the legacy gate slot to baseline truth."""
    runtime, evidence = a11.midpoint_bound_constraint_records(
        body, planes, original_ids
    )
    for record in evidence:
        comparison = record.get("a08_topology_comparison")
        if comparison is None:
            record["a08_baseline_dot_agreement"] = {
                "applicable": False,
                "reason": "edge was not one of A08's four moved supports",
            }
            continue
        legacy_ratio_result = bool(
            comparison.get("topology_ratio_within_tolerance", False)
        )
        absolute_delta = abs(
            float(record["baseline_dot"]) - float(comparison["a08_baseline_dot"])
        )
        baseline_pass = absolute_delta <= BASELINE_DOT_AGREEMENT_TOLERANCE
        comparison["observed_ratio_is_diagnostic_only"] = True
        comparison["invalid_exact_1_5_equality_gate_removed"] = True
        comparison["legacy_exact_1_5_ratio_within_tolerance"] = legacy_ratio_result
        # Attempt_02's unchanged solver reads this legacy boolean after PRE_CAP.
        # Rebinding it to the newly authorized evidence gate avoids changing a
        # single solver, weight, cap, topology, relief, or downstream gate line.
        comparison["topology_ratio_within_tolerance"] = baseline_pass
        comparison["legacy_boolean_slot_semantics"] = (
            "A08_BASELINE_DOT_AGREEMENT_GATE; observed ratio retained diagnostic-only"
        )
        record["a08_baseline_dot_agreement"] = {
            "applicable": True,
            "a09_measured_baseline_dot": float(record["baseline_dot"]),
            "a08_measured_baseline_dot": float(comparison["a08_baseline_dot"]),
            "absolute_delta": absolute_delta,
            "tolerance": BASELINE_DOT_AGREEMENT_TOLERANCE,
            "passed": baseline_pass,
        }
        record["authoritative_measured_geometry_gate"] = {
            "map_binding_exact": bool(
                record["authoritative_midpoint_binding"][
                    "binding_present_exactly_once"
                ]
            ),
            "baseline_dot_agreement": baseline_pass,
            "closest_linear_slope_minimum_within_unchanged_cap": bool(
                record["closest_linear_slope_minimum"]["within_ring_1_cap"]
            ),
            "observed_a09_a08_ratio_used_as_equality": False,
        }
    return runtime, evidence


def main() -> None:
    global ACTIVE_OUTPUT
    worker = Path(__file__).resolve()
    for path, expected, label in (
        (SOURCE, SOURCE_SHA256, "sealed R19 source"),
        (a10.ATTEMPT_01_WORKER, a10.ATTEMPT_01_WORKER_SHA256, "attempt_01 worker"),
        (a10.ATTEMPT_01_FAILURE, a10.ATTEMPT_01_FAILURE_SHA256, "attempt_01 failure"),
        (a11.ATTEMPT_02_WORKER, a11.ATTEMPT_02_WORKER_SHA256, "attempt_02 worker"),
        (a11.ATTEMPT_02_FAILURE, a11.ATTEMPT_02_FAILURE_SHA256, "attempt_02 failure"),
        (ATTEMPT_03_WORKER, ATTEMPT_03_WORKER_SHA256, "attempt_03 worker"),
        (ATTEMPT_03_PRE_CAP, ATTEMPT_03_PRE_CAP_SHA256, "attempt_03 pre-cap"),
        (ATTEMPT_03_FAILURE, ATTEMPT_03_FAILURE_SHA256, "attempt_03 failure"),
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
    if ACTIVE_OUTPUT.name != "attempt_04":
        raise RuntimeError(
            f"append-only attempt slot is {ACTIVE_OUTPUT.name}, expected attempt_04"
        )
    a10.ACTIVE_OUTPUT = ACTIVE_OUTPUT
    a11.AUTHORITATIVE_ENDPOINTS_BY_MIDPOINT.clear()
    a11.AUTHORITATIVE_MAP_RECORDS.clear()
    a11.AUTHORITATIVE_MAP_SHA256 = None
    a11.CAPTURE_INVOCATIONS = 0

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
    a09.face_refinement_templates = a11.capture_authoritative_refinement_map
    a09.solve_coupled_fair_fit = a10.coupled_linear_slope_fit
    a10.source_endpoint_ids_for_midpoint = a11.authoritative_endpoint_lookup
    a10.linear_slope_constraint_records = measured_geometry_constraint_records
    a10.atomic_write_json = a11.inject_map_into_pre_cap
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
    map_state = a11.authoritative_map_state()

    report = {
        "schema": "kira.avatar.r24.a09_attempt04_measured_geometry_slope_simulation.v1",
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
            "attempt_02_worker_sha256": a11.ATTEMPT_02_WORKER_SHA256,
            "attempt_02_failure_sha256": a11.ATTEMPT_02_FAILURE_SHA256,
            "attempt_03_worker_sha256": ATTEMPT_03_WORKER_SHA256,
            "attempt_03_pre_cap_sha256": ATTEMPT_03_PRE_CAP_SHA256,
            "attempt_03_failure_sha256": ATTEMPT_03_FAILURE_SHA256,
            "a08_worker_sha256": a09.A08_WORKER_SHA256,
            "a08_report_sha256": a09.A08_REPORT_SHA256,
            "a06_report_sha256": a09.A06_REPORT_SHA256,
        },
        "method": {
            "id": "R19_INTERNAL_EDGE_MIDPOINT_MEASURED_GEOMETRY_LINEAR_SLOPE_KKT_V4",
            "new_body_created": False,
            "source_body_saved": False,
            "authoritative_midpoint_map_controls": True,
            "observed_a09_a08_ratios_retained_diagnostic_only": True,
            "invalid_exact_1_5_ratio_equality_removed": True,
            "a08_baseline_dot_agreement_tolerance": BASELINE_DOT_AGREEMENT_TOLERANCE,
            "exact_closest_slope_minimum_cap_gate": True,
            "topology_kkt_weights_caps_relief_gates_or_render_set_changed": False,
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
            "append_only_attempt_04": True,
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
    a11.ORIGINAL_ATOMIC_WRITE_JSON(ACTIVE_OUTPUT / "SIMULATION_REPORT.json", report)
    print(json.dumps({"status": report["status"], "output": str(ACTIVE_OUTPUT)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback

        trace = traceback.format_exc()
        if ACTIVE_OUTPUT is not None:
            failure = {
                "schema": "kira.avatar.r24.a09_attempt04_measured_geometry_slope_failure.v1",
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
                "authoritative_map_count": len(a11.AUTHORITATIVE_MAP_RECORDS),
                "authoritative_map_sha256": a11.AUTHORITATIVE_MAP_SHA256,
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
            a11.ORIGINAL_ATOMIC_WRITE_JSON(ACTIVE_OUTPUT / "FAILURE.json", failure)
        print(trace, file=sys.stderr)
        raise
