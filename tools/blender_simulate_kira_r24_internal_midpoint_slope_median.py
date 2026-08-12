"""No-save A09 attempt_05 corrected even-median seam selection.

The only behavioral change from attempt_04 is the exact number of additional
near-.94 seam rows.  Low rows raised to .715 still remain below .94, so they
are not subtracted from ``len(below_.94) - 16``.  The sealed geometry therefore
uses four low rows plus five near-.94 rows.  KKT, weights, topology, caps, A06
relief, all gates, paired renders, and no-save behavior are unchanged.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_simulate_kira_r24_internal_midpoint_fair_surface as a09  # noqa: E402
from tools import blender_simulate_kira_r24_internal_midpoint_slope_constrained as a10  # noqa: E402
from tools import blender_simulate_kira_r24_internal_midpoint_slope_bound as a11  # noqa: E402
from tools import blender_simulate_kira_r24_internal_midpoint_slope_measured as a12  # noqa: E402


SOURCE = a09.SOURCE
SOURCE_SHA256 = a09.SOURCE_SHA256
BODY_NAME = a09.BODY_NAME
RIG_NAME = a09.RIG_NAME
OUTPUT_ROOT = a09.OUTPUT_ROOT

ATTEMPT_04_WORKER = ROOT / "tools/blender_simulate_kira_r24_internal_midpoint_slope_measured.py"
ATTEMPT_04_WORKER_SHA256 = "892349194a97d2a67f44f69a642d1ec1e45cd5a91e4843d98d04ce543d9a5fc2"
ATTEMPT_04_PRE_CAP = OUTPUT_ROOT / "attempt_04/PRE_CAP_DIAGNOSTIC.json"
ATTEMPT_04_PRE_CAP_SHA256 = "3a86ae234e30c6abde11d0faed23c26c9bdb3bbb0ce524f699df34d0319f2fc6"
ATTEMPT_04_SOLVER = OUTPUT_ROOT / "attempt_04/SOLVER_DIAGNOSTIC.json"
ATTEMPT_04_SOLVER_SHA256 = "493409599c7547441115cef239656c6a8ae89d05ebd37bdc345a20b9f9272b3b"
ATTEMPT_04_FAILURE = OUTPUT_ROOT / "attempt_04/FAILURE.json"
ATTEMPT_04_FAILURE_SHA256 = "1feed96d80b27002a2e10b82ee64e3e52731a03eedfdc8df02f51b04e3db26d6"
ATTEMPT_04_OUTCOME = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_04_OUTCOME.md"
ATTEMPT_04_OUTCOME_SHA256 = "48db7616a785ffce5fd6cbd80e80a6ad5aa6fc53b9bd184c5592ea70700224d5"

ACTIVE_OUTPUT: Path | None = None


def sha256(path: Path) -> str:
    return a09.sha256(path)


def relative(path: Path) -> str:
    return a09.relative(path)


def corrected_even_median_seam_targets(planes):
    below_low = [record for record in planes if float(record["baseline_dot"]) < 0.70]
    below_median = [
        record for record in planes if float(record["baseline_dot"]) < 0.94
    ]
    low_ids = {tuple(record["edge_ids"]) for record in below_low}
    additional_count = max(0, len(below_median) - 16)
    candidates = sorted(
        (
            record
            for record in below_median
            if tuple(record["edge_ids"]) not in low_ids
        ),
        key=lambda record: (-float(record["baseline_dot"]), record["edge_ids"]),
    )
    if additional_count > len(candidates):
        raise RuntimeError("insufficient non-low seam candidates for median repair")
    additional = candidates[:additional_count]
    if len(below_low) != 4 or additional_count != 5:
        raise RuntimeError(
            f"sealed attempt_05 selection drifted: low={len(below_low)}, "
            f"additional={additional_count}; expected 4 and 5"
        )
    selected = [
        (record, a09.TARGET_LOW_DOT, "minimum_below_0_70")
        for record in below_low
    ]
    selected.extend(
        (record, a09.TARGET_MEDIAN_EDGE_DOT, "minimum_for_even_median_0_94")
        for record in additional
    )
    return sorted(selected, key=lambda item: tuple(item[0]["edge_ids"]))


def main() -> None:
    global ACTIVE_OUTPUT
    worker = Path(__file__).resolve()
    for path, expected, label in (
        (SOURCE, SOURCE_SHA256, "sealed R19 source"),
        (a10.ATTEMPT_01_WORKER, a10.ATTEMPT_01_WORKER_SHA256, "attempt_01 worker"),
        (a10.ATTEMPT_01_FAILURE, a10.ATTEMPT_01_FAILURE_SHA256, "attempt_01 failure"),
        (a11.ATTEMPT_02_WORKER, a11.ATTEMPT_02_WORKER_SHA256, "attempt_02 worker"),
        (a11.ATTEMPT_02_FAILURE, a11.ATTEMPT_02_FAILURE_SHA256, "attempt_02 failure"),
        (a12.ATTEMPT_03_WORKER, a12.ATTEMPT_03_WORKER_SHA256, "attempt_03 worker"),
        (a12.ATTEMPT_03_PRE_CAP, a12.ATTEMPT_03_PRE_CAP_SHA256, "attempt_03 pre-cap"),
        (a12.ATTEMPT_03_FAILURE, a12.ATTEMPT_03_FAILURE_SHA256, "attempt_03 failure"),
        (ATTEMPT_04_WORKER, ATTEMPT_04_WORKER_SHA256, "attempt_04 worker"),
        (ATTEMPT_04_PRE_CAP, ATTEMPT_04_PRE_CAP_SHA256, "attempt_04 pre-cap"),
        (ATTEMPT_04_SOLVER, ATTEMPT_04_SOLVER_SHA256, "attempt_04 solver"),
        (ATTEMPT_04_FAILURE, ATTEMPT_04_FAILURE_SHA256, "attempt_04 failure"),
        (ATTEMPT_04_OUTCOME, ATTEMPT_04_OUTCOME_SHA256, "attempt_04 outcome"),
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
    if ACTIVE_OUTPUT.name != "attempt_05":
        raise RuntimeError(
            f"append-only attempt slot is {ACTIVE_OUTPUT.name}, expected attempt_05"
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
    prior_seam_selector = a10.selected_seam_targets
    a09.face_refinement_templates = a11.capture_authoritative_refinement_map
    a09.solve_coupled_fair_fit = a10.coupled_linear_slope_fit
    a10.source_endpoint_ids_for_midpoint = a11.authoritative_endpoint_lookup
    a10.linear_slope_constraint_records = a12.measured_geometry_constraint_records
    a10.atomic_write_json = a11.inject_map_into_pre_cap
    a10.selected_seam_targets = corrected_even_median_seam_targets
    try:
        applied = a09.refine_and_shape(body, rig, preflight)
    finally:
        a09.face_refinement_templates = prior_refinement_templates
        a09.solve_coupled_fair_fit = prior_solver
        a10.source_endpoint_ids_for_midpoint = prior_endpoint_lookup
        a10.linear_slope_constraint_records = prior_constraint_records
        a10.atomic_write_json = prior_atomic_writer
        a10.selected_seam_targets = prior_seam_selector

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
        "schema": "kira.avatar.r24.a09_attempt05_corrected_median_simulation.v1",
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
        "preserved_attempt_04": {
            "worker_sha256": ATTEMPT_04_WORKER_SHA256,
            "pre_cap_sha256": ATTEMPT_04_PRE_CAP_SHA256,
            "solver_sha256": ATTEMPT_04_SOLVER_SHA256,
            "failure_sha256": ATTEMPT_04_FAILURE_SHA256,
            "outcome_sha256": ATTEMPT_04_OUTCOME_SHA256,
        },
        "method": {
            "id": "R19_INTERNAL_EDGE_MIDPOINT_MEASURED_GEOMETRY_CORRECTED_EVEN_MEDIAN_KKT_V5",
            "only_change_from_attempt_04": (
                "near-.94 constraint count is len(below_.94)-16 without subtracting low rows"
            ),
            "low_constraint_count": 4,
            "near_0_94_constraint_count": 5,
            "expected_total_active_rows": 9,
            "topology_kkt_weights_caps_relief_gates_or_render_set_changed": False,
            "source_body_saved": False,
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
            "append_only_attempt_05": True,
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
                "schema": "kira.avatar.r24.a09_attempt05_corrected_median_failure.v1",
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
            a11.ORIGINAL_ATOMIC_WRITE_JSON(ACTIVE_OUTPUT / "FAILURE.json", failure)
        print(trace, file=sys.stderr)
        raise
