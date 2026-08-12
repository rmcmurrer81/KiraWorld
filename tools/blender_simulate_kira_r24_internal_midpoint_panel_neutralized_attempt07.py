"""No-save A09 Attempt 07 repair of Attempt 06's mask-audit false positive.

All geometry, KKT, caps, relief, topology, render, source, and save behavior is
delegated unchanged to the hash-bound Attempt 06 worker.  This wrapper changes
only mask-overlap evidence: the exact four severe supports are required to be
an intentional subset of all seam supports, and mask evidence is serialized
before any mask failure is raised.  This file does not save a Blend.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import traceback

import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_simulate_kira_r24_internal_midpoint_panel_neutralized as a14  # noqa: E402


a09 = a14.a09
a10 = a14.a10
a11 = a14.a11
SOURCE = a14.SOURCE
SOURCE_SHA256 = a14.SOURCE_SHA256
BODY_NAME = a14.BODY_NAME
RIG_NAME = a14.RIG_NAME
OUTPUT_ROOT = a14.OUTPUT_ROOT

ATTEMPT_06_WORKER = ROOT / "tools/blender_simulate_kira_r24_internal_midpoint_panel_neutralized.py"
ATTEMPT_06_WORKER_SHA256 = "7af00b113268c26f6eca304d95709541f2e56264f539e9c3aa5430aa53e00ea1"
ATTEMPT_06_FAILURE = OUTPUT_ROOT / "attempt_06/FAILURE.json"
ATTEMPT_06_FAILURE_SHA256 = "d1e43056c844fcb55b31dfec931c21531ba13ebea43af1e0e44eee3f494b7bd5"
ATTEMPT_06_OUTCOME = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_06_OUTCOME.md"
ATTEMPT_06_OUTCOME_SHA256 = "f3f61c28cf62c837f2ce3559a6025fa4e45f792edcdf8121eef236de4020a101"
ATTEMPT_06_DIAGNOSIS = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_06_MASK_OVERLAP_DIAGNOSIS.json"
ATTEMPT_06_DIAGNOSIS_SHA256 = "dd5961795d7d6940946f541b6bc71929bc762d7d96f56e210cacf766664c8f30"
ATTEMPT_07_PROPOSAL = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_07_FALSE_POSITIVE_MASK_REPAIR_PROPOSAL.md"
ATTEMPT_07_PROPOSAL_SHA256 = "0a4b9b4c319fa6674a6bd3a4d75338b5d2e46ae3490d237d922ad133d24625aa"

EXPECTED_SEVERE_BINDINGS = {
    (1096, 1097): {
        "support_vertex_index_before_final_reindex": 12638,
        "support_canonical_id": -28,
        "support_source_endpoint_ids": [1096, 12576],
    },
    (1097, 1529): {
        "support_vertex_index_before_final_reindex": 12643,
        "support_canonical_id": -33,
        "support_source_endpoint_ids": [1097, 12563],
    },
    (2481, 2482): {
        "support_vertex_index_before_final_reindex": 12691,
        "support_canonical_id": -81,
        "support_source_endpoint_ids": [2482, 12465],
    },
    (2481, 2861): {
        "support_vertex_index_before_final_reindex": 12686,
        "support_canonical_id": -76,
        "support_source_endpoint_ids": [2481, 12476],
    },
}

ACTIVE_OUTPUT: Path | None = None


def sha256(path: Path) -> str:
    return a14.sha256(path)


def relative(path: Path) -> str:
    return a14.relative(path)


def corrected_build_mask_evidence(
    planes,
    patch_vertices,
    patch_edges,
    seam_vertices,
    distances,
    original_ids,
    parameters,
):
    """Serialize masks first; allow only the two explicitly listed overlaps."""
    if a14.ACTIVE_OUTPUT is None:
        raise RuntimeError("Attempt 07 output was not allocated before mask audit")
    neighbors = a09.patch_neighbors(patch_vertices, patch_edges)
    observed_by_edge = {
        a14.edge_key(plane["edge_ids"]): plane for plane in planes
    }
    all_supports = {plane["support"] for plane in planes}
    severe_supports = {
        observed_by_edge[edge]["support"]
        for edge in a14.SEVERE_FLANK_EDGES
        if edge in observed_by_edge
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

    edge_masks = {}
    for name, values in (
        ("SUPERIOR_JOIN_EDGES", a14.SUPERIOR_JOIN_EDGES),
        ("SEVERE_FLANK_EDGES", a14.SEVERE_FLANK_EDGES),
        ("REGULAR_FLANK_EDGES", a14.REGULAR_FLANK_EDGES),
    ):
        records = [list(edge) for edge in sorted(values)]
        edge_masks[name] = {
            "count": len(records),
            "canonical_sha256": a09.a08.canonical_sha256(records),
            "records": records,
        }
    vertex_masks = {
        name: a14.mask_entry(name, vertices, original_ids, distances, parameters)
        for name, vertices in masks.items()
    }

    severe_binding_records = []
    severe_bindings_exact = True
    for edge in sorted(a14.SEVERE_FLANK_EDGES):
        plane = observed_by_edge.get(edge)
        if plane is None:
            severe_binding_records.append({"seam_edge": list(edge), "missing": True})
            severe_bindings_exact = False
            continue
        support = plane["support"]
        endpoints = a11.authoritative_endpoint_lookup(support, original_ids)
        observed = {
            "seam_edge": list(edge),
            "support_vertex_index_before_final_reindex": int(support.index),
            "support_canonical_id": int(original_ids.get(support, -1)),
            "support_source_endpoint_ids": list(endpoints),
        }
        severe_binding_records.append(observed)
        expected = EXPECTED_SEVERE_BINDINGS[edge]
        severe_bindings_exact = severe_bindings_exact and all(
            observed[key] == expected[key]
            for key in (
                "support_vertex_index_before_final_reindex",
                "support_canonical_id",
                "support_source_endpoint_ids",
            )
        )

    names = list(masks)
    overlaps = []
    unexpected = []
    for first_index, first in enumerate(names):
        for second in names[first_index + 1 :]:
            shared = masks[first] & masks[second]
            if not shared:
                continue
            pair = {first, second}
            aggregate_subset = pair == {
                "ALL_RING1_SEAM_SUPPORTS",
                "SEVERE_RING1_SUPPORTS",
            }
            continuation_central = pair == {
                "SEAM_CONTINUATION_RING2",
                "CENTRAL_POSITIVE_RELIEF",
            }
            allowed = bool(
                continuation_central
                or (
                    aggregate_subset
                    and shared == severe_supports
                    and len(shared) == 4
                )
            )
            record = {
                "first": first,
                "second": second,
                "count": len(shared),
                "allowed": allowed,
                "reason": (
                    "exact severe subset of aggregate seam supports"
                    if aggregate_subset
                    else (
                        "explicitly listed ring2/central overlap"
                        if continuation_central
                        else "unlisted overlap"
                    )
                ),
                "shared_vertex_indices_before_final_reindex": sorted(
                    int(vertex.index) for vertex in shared
                ),
            }
            overlaps.append(record)
            if not allowed:
                unexpected.append(record)

    subset_gates = {
        "severe_is_subset_of_all": severe_supports <= all_supports,
        "severe_count_exactly_four": len(severe_supports) == 4,
        "severe_bindings_exact": severe_bindings_exact,
        "all_seam_supports_are_ring1": all(
            int(distances[vertex]) == 1 for vertex in all_supports
        ),
        "observed_edge_set_exact_34": set(observed_by_edge)
        == a14.ALL_PROPOSED_SEAM_EDGES,
        "required_masks_nonempty": all(bool(vertices) for vertices in masks.values()),
        "no_unlisted_overlap": not unexpected,
    }
    evidence = {
        "edge_masks": edge_masks,
        "vertex_masks": vertex_masks,
        "severe_subset_bindings": severe_binding_records,
        "severe_subset_gates": subset_gates,
        "allowed_overlaps": [
            "SEVERE_RING1_SUPPORTS subset of ALL_RING1_SEAM_SUPPORTS, exactly four",
            "SEAM_CONTINUATION_RING2 with CENTRAL_POSITIVE_RELIEF",
        ],
        "observed_overlaps": overlaps,
        "unexpected_overlap_count": len(unexpected),
    }
    evidence["canonical_sha256"] = a09.a08.canonical_sha256(evidence)
    pre_mask = {
        "schema": "kira.avatar.r24.a09_attempt07.pre_mask_diagnostic.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "WRITTEN_ATOMICALLY_BEFORE_ANY_MASK_FAILURE",
        "worker": {
            "path": relative(Path(__file__).resolve()),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "attempt_06_failure_sha256": ATTEMPT_06_FAILURE_SHA256,
        "attempt_07_proposal_sha256": ATTEMPT_07_PROPOSAL_SHA256,
        "masks": evidence,
    }
    a14.atomic_write_json(
        a14.ACTIVE_OUTPUT / "PRE_MASK_DIAGNOSTIC.json", pre_mask
    )
    if not all(subset_gates.values()):
        failed = [name for name, passed in subset_gates.items() if not passed]
        raise RuntimeError(f"Attempt 07 mask gate failure after serialization: {failed}")
    return evidence, masks


def main() -> None:
    global ACTIVE_OUTPUT
    worker = Path(__file__).resolve()
    for path, expected, label in (
        (SOURCE, SOURCE_SHA256, "sealed R19 source"),
        (ATTEMPT_06_WORKER, ATTEMPT_06_WORKER_SHA256, "attempt_06 worker"),
        (ATTEMPT_06_FAILURE, ATTEMPT_06_FAILURE_SHA256, "attempt_06 failure"),
        (ATTEMPT_06_OUTCOME, ATTEMPT_06_OUTCOME_SHA256, "attempt_06 outcome"),
        (ATTEMPT_06_DIAGNOSIS, ATTEMPT_06_DIAGNOSIS_SHA256, "attempt_06 diagnosis"),
        (ATTEMPT_07_PROPOSAL, ATTEMPT_07_PROPOSAL_SHA256, "attempt_07 proposal"),
        (a14.PROPOSAL, a14.PROPOSAL_SHA256, "original attempt_06 proposal"),
        (a14.ATTEMPT_05_REPORT, a14.ATTEMPT_05_REPORT_SHA256, "attempt_05 report"),
    ):
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"{label} hash drifted")
    ACTIVE_OUTPUT = a09.allocate_output()
    if ACTIVE_OUTPUT.name != "attempt_07":
        raise RuntimeError(
            f"append-only attempt slot is {ACTIVE_OUTPUT.name}, expected attempt_07"
        )
    a14.ACTIVE_OUTPUT = ACTIVE_OUTPUT
    a11.AUTHORITATIVE_ENDPOINTS_BY_MIDPOINT.clear()
    a11.AUTHORITATIVE_MAP_RECORDS.clear()
    a11.AUTHORITATIVE_MAP_SHA256 = None
    a11.CAPTURE_INVOCATIONS = 0
    a14.RELIEF_SEQUENCE.clear()
    a14.RELIEF_RECORDS.clear()
    a14.FADE_RECORDS.clear()
    a14.PENDING_FADE = None

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
    prior_mask_builder = a14.build_mask_evidence
    prior_a14_file = a14.__file__
    a09.face_refinement_templates = a11.capture_authoritative_refinement_map
    a09.solve_coupled_fair_fit = a14.attempt06_coupled_fit
    a10.selected_seam_targets = a14.selected_seam_targets
    a10.source_endpoint_ids_for_midpoint = a11.authoritative_endpoint_lookup
    a09.a08.feature_offset_and_tags = a14.attempt06_feature_offset_and_tags
    a09.a08.smoothstep = a14.attempt06_smoothstep
    a09.RING_1_CAP_M = a14.SEVERE_RING_1_CAP_M
    a09.TOTAL_BASE_FIT_CAP_M = a14.OVERALL_CAP_M
    a14.build_mask_evidence = corrected_build_mask_evidence
    a14.__file__ = str(worker)
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
        a14.build_mask_evidence = prior_mask_builder
        a14.__file__ = prior_a14_file
    if a14.RELIEF_SEQUENCE or a14.PENDING_FADE is not None:
        raise RuntimeError("Attempt 07 relief/fade sequence was not fully consumed")
    applied["attempt06_relief"] = {
        "central_mask_definition": "d>=2; abs(u)<=0.42; 0.22<=t<=0.82",
        "majora_positive_multiplier": 1.12,
        "minora_positive_multiplier": 1.10,
        "hood_glans_positive_multiplier": 1.15,
        "negative_opening_or_recess_terms_changed": False,
        "fade_formula": "smoothstep((d-1)/2)",
        "relief_records_sha256": a09.a08.canonical_sha256(a14.RELIEF_RECORDS),
        "fade_records_sha256": a09.a08.canonical_sha256(a14.FADE_RECORDS),
        "relief_record_count": len(a14.RELIEF_RECORDS),
        "fade_record_count": len(a14.FADE_RECORDS),
    }
    gates = a14.attempt06_gates(body, applied)
    render_directory = ACTIVE_OUTPUT / "private_owner_review"
    renders = a09.a08.r24_render.render_evidence(body, applied, render_directory)
    paired = a09.render_uniform_clay_pairs_without_subdivision(
        render_directory, applied
    )
    renders["rendered"].extend(record["filename"] for record in paired)
    renders["paired_subdivision_diagnostics"] = paired
    map_state = a11.authoritative_map_state()
    report = {
        "schema": "kira.avatar.r24.a09_attempt07_mask_audit_repair_simulation.v1",
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
            "path": relative(ATTEMPT_07_PROPOSAL),
            "sha256": sha256(ATTEMPT_07_PROPOSAL),
        },
        "preserved_attempt_06": {
            "worker_sha256": ATTEMPT_06_WORKER_SHA256,
            "failure_sha256": ATTEMPT_06_FAILURE_SHA256,
            "outcome_sha256": ATTEMPT_06_OUTCOME_SHA256,
            "diagnosis_sha256": ATTEMPT_06_DIAGNOSIS_SHA256,
        },
        "only_behavioral_change": (
            "allow and explicitly gate the four-support severe subset of all "
            "seam supports; serialize masks before any mask failure"
        ),
        "pre_mask_diagnostic": {
            "path": relative(ACTIVE_OUTPUT / "PRE_MASK_DIAGNOSTIC.json"),
            "sha256": sha256(ACTIVE_OUTPUT / "PRE_MASK_DIAGNOSTIC.json"),
            "written_before_any_mask_failure": True,
        },
        "pre_cap_diagnostic": {
            "path": relative(ACTIVE_OUTPUT / "PRE_CAP_DIAGNOSTIC.json"),
            "sha256": sha256(ACTIVE_OUTPUT / "PRE_CAP_DIAGNOSTIC.json"),
        },
        "solver_diagnostic": {
            "path": relative(ACTIVE_OUTPUT / "SOLVER_DIAGNOSTIC.json"),
            "sha256": sha256(ACTIVE_OUTPUT / "SOLVER_DIAGNOSTIC.json"),
        },
        "authoritative_midpoint_endpoint_map": {
            "binding_source": map_state["binding_source"],
            "count": map_state["count"],
            "canonical_sha256": map_state["canonical_sha256"],
        },
        "preflight": {
            "patch_face_count": len(preflight["patch_faces"]),
            "patch_vertex_count": len(preflight["patch_vertices"]),
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
            "requirements_unchanged_from_attempt_06": True,
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
    a14.atomic_write_json(ACTIVE_OUTPUT / "SIMULATION_REPORT.json", report)
    print(json.dumps({"status": report["status"], "output": str(ACTIVE_OUTPUT)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        trace = traceback.format_exc()
        output = ACTIVE_OUTPUT or a14.ACTIVE_OUTPUT
        if output is not None:
            failure = {
                "schema": "kira.avatar.r24.a09_attempt07_mask_audit_repair_failure.v1",
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
                "attempt_06_failure_sha256": ATTEMPT_06_FAILURE_SHA256,
                "pre_mask_diagnostic_present": (
                    output / "PRE_MASK_DIAGNOSTIC.json"
                ).is_file(),
                "pre_cap_diagnostic_present": (
                    output / "PRE_CAP_DIAGNOSTIC.json"
                ).is_file(),
                "solver_diagnostic_present": (
                    output / "SOLVER_DIAGNOSTIC.json"
                ).is_file(),
                "operations": {
                    "blend_saved": False,
                    "source_overwritten": False,
                    "runtime_or_person_state_changed": False,
                },
            }
            a14.atomic_write_json(output / "FAILURE.json", failure)
        print(trace, file=sys.stderr)
        raise
