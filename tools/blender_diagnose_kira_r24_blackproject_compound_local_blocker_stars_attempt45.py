"""Attempt 45 static-first compound local-blocker source-star proof.

This module binds preserved Attempt 44 runtime evidence and derives exactly
one later read-only mapper. Importing it is Blender-free and creates no
Attempt 45 evidence.
"""

from __future__ import annotations

import sys

# This must precede importlib and every bound-module load.
sys.dont_write_bytecode = True

import argparse
import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT45_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = (
    "41144f0b470c078312cc35aae6368dd75c0a1b1079b0a56b6808f81a1fd4117b"
)
ATTEMPT44_WORKER = ROOT / (
    "tools/blender_diagnose_kira_r24_blackproject_chart_maximum_star_attempt44.py"
)
EXPECTED_ATTEMPT44_WORKER_SHA256 = (
    "2e7fe7f3fd841e8a0d5330dcb5481ebaabfd3a8a59cfc957dd3e780e016f0245"
)
EXPECTED_ATTEMPT44_CONFIG_SHA256 = (
    "78bf8b2f44460b0091f72eb6115971da6bb592acb205e036259f5fece0c193b3"
)
EXPECTED_ATTEMPT44_DERIVED_SHA256 = (
    "216eb9b56dbb8ee768167756e2590d42b33f692d5a275013fed32a970c24613b"
)
EXPECTED_ATTEMPT44_MAPPING_BLOCK_SHA256 = (
    "0708712f4a86ce987e67ead9c6951441fded11941f5509a09e4a19ad17211210"
)
EXPECTED_CACHE_SHA256 = (
    "340ddf1fcbb97d8bd309280061f05dd6a914b79c1e36abce69134501902c162f"
)
EXPECTED_DERIVED_SHA256 = (
    "481dd0105147edef6f39b2f682f2def99388355c325429b02e5d11e214c11ccf"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def project_path(value: str, *, must_exist: bool = True) -> Path:
    path = (ROOT / value).resolve(strict=must_exist)
    root = ROOT.resolve()
    if root != path and root not in path.parents:
        raise RuntimeError(f"Attempt 45 path escapes project: {value}")
    return path


def file_record(path: Path) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    return {
        "path": str(exact.relative_to(ROOT)).replace("\\", "/"),
        "bytes": exact.stat().st_size,
        "sha256": sha256_file(exact),
    }


def require_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    actual = file_record(project_path(str(record["path"])))
    if actual["bytes"] != int(record["bytes"]):
        raise RuntimeError(f"Attempt 45 binding byte count drifted: {name}")
    if actual["sha256"] != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 45 binding hash drifted: {name}")
    return actual


def load_static_module(name: str, path: Path) -> Any:
    if sys.dont_write_bytecode is not True:
        raise RuntimeError("Attempt 45 bytecode containment was disabled")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Attempt 45 cannot load bound worker: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 45 requires the exact sealed config path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 45 config hash drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_45"
        or config.get("status")
        != "STATIC_READ_ONLY_COMPOUND_LOCAL_BLOCKER_STARS_PROOF_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 45 identity drifted")
    scope = config["scope"]
    required_true = (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "diagnostic_only",
        "later_independently_reviewed_blender_launch_required",
        "read_existing_source_mesh_allowed_during_later_reviewed_run",
        "in_memory_scene_open_allowed_during_later_reviewed_run",
        "ordered_topology_identity_required_before_mapping",
        "bounded_numeric_sanity_required_before_mapping",
        "exact_attempt43_base_domain_reverification_required",
        "exact_attempt44_candidate_reverification_required",
        "exact_one_compound_blocker_vertex_star_mapping_allowed",
        "per_boundary_chart_deviation_attribution_required",
        "forced_ear_necessary_feasibility_test_required",
        "append_only_json_evidence_allowed_during_later_run",
    )
    forbidden = (
        "source_file_mutation_allowed",
        "prior_evidence_mutation_allowed",
        "body_geometry_mutation_allowed",
        "patch_geometry_mutation_allowed",
        "blender_datablock_transform_assignment_allowed",
        "triangulation_allowed",
        "reconstruction_allowed",
        "render_allowed",
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "assignment_allowed",
        "publication_allowed",
        "boundary_or_seam_movement_allowed",
        "arbitrary_new_coordinate_allowed",
        "quality_gate_reduction_allowed",
        "generic_hole_fill_allowed",
        "sanitation_weakening_allowed",
        "uniform_face_ring_allowed",
        "separate_blocker_star_candidates_allowed",
        "automatic_alternate_candidate_allowed",
        "automatic_retry_allowed",
    )
    if not all(bool(scope[name]) for name in required_true):
        raise RuntimeError("Attempt 45 lost a required read-only scope")
    if any(bool(scope[name]) for name in forbidden):
        raise RuntimeError("Attempt 45 permits a forbidden operation")
    expected_output = {
        "root": (
            "RecoverySprint/continuation_20260803/"
            "kira_r24_internal_midpoint_fair_surface/attempt_45"
        ),
        "started": "ATTEMPT_STARTED.json",
        "diagnostic": "COMPOUND_LOCAL_BLOCKER_STARS_DIAGNOSTIC.json",
        "failure": "FAILURE.json",
        "blend_save_permitted": False,
        "render_permitted": False,
    }
    if config["output"] != expected_output:
        raise RuntimeError("Attempt 45 output contract drifted")
    if project_path(expected_output["root"], must_exist=False).exists():
        raise RuntimeError("Attempt 45 output already exists")
    probe = config["one_candidate_probe"]
    if (
        probe["candidate"]
        != "complete_attempt44_domain_plus_complete_mesh_vertex_stars_218_508"
        or probe["base_candidate"]
        != "complete_attempt43_domain_plus_complete_mesh_vertex_star_241"
        or probe["required_complete_source_mesh_vertex_stars"] != [241, 218, 508]
        or probe["new_compound_blocker_source_mesh_vertex_stars"] != [218, 508]
        or int(probe["attempt44_chart_maximum_boundary_index"]) != 4
        or int(probe["attempt44_chart_maximum_mesh_vertex_index"]) != 218
        or int(probe["attempt44_forced_ear_obstruction_boundary_index"]) != 12
        or int(probe["attempt44_forced_ear_obstruction_mesh_vertex_index"]) != 508
        or not bool(probe["one_indivisible_compound_candidate"])
        or bool(probe["separate_star_candidates_allowed"])
        or not bool(probe["complete_source_mesh_vertex_stars_only"])
        or bool(probe["uniform_face_ring_candidates_allowed"])
        or bool(probe["alternate_target_sets_allowed"])
        or bool(probe["coordinate_suppression_allowed"])
    ):
        raise RuntimeError("Attempt 45 one-candidate probe drifted")
    result = config["attempt44_runtime_result"]
    if (
        result["candidate"]
        != "complete_attempt43_domain_plus_complete_mesh_vertex_star_241"
        or int(result["candidate_count"]) != 1
        or int(result["necessary_eligible_candidate_count"]) != 0
        or int(result["face_count"]) != 127
        or int(result["vertex_count"]) != 90
        or int(result["edge_count"]) != 216
        or int(result["boundary_edge_count"]) != 51
        or result["chart_maximum_contributor_mesh_vertex_indices"] != [218]
        or result["forced_ear_obstruction_mesh_vertex_indices"] != [508]
        or result["forced_ear_passes"] is not False
    ):
        raise RuntimeError("Attempt 45 bound Attempt 44 result drifted")
    cache = config["preserved_existing_bytecode_cache"]
    if (
        int(cache["bytes"]) != 36680
        or cache["sha256"] != EXPECTED_CACHE_SHA256
        or not bool(cache["must_remain_exact"])
        or not bool(cache["must_not_be_deleted"])
    ):
        raise RuntimeError("Attempt 45 preserved-cache contract drifted")
    launch = config["launch_contract"]
    if (
        launch["arguments_before_python"]
        != ["--background", "--factory-startup", "--disable-autoexec", "--python-exit-code", "1"]
        or not bool(launch["wrapper_unions_attempt44_317_entry_inventory"])
        or not bool(launch["wrapper_verifies_all_attempt44_records_before_blender"])
        or not bool(launch["wrapper_protects_attempt40_generated_cpython313_cache"])
        or not bool(launch["wrapper_refuses_any_new_relevant_worker_cache"])
        or not bool(launch["worker_sets_sys_dont_write_bytecode_before_bound_worker_load"])
        or not bool(launch["exactly_one_blender_invocation_required"])
        or not bool(launch["refuse_any_overwrite"])
        or bool(launch["executed_during_static_preparation"])
    ):
        raise RuntimeError("Attempt 45 launch contract drifted")
    forbidden_truth = (
        "attempt45_blender_execution_performed",
        "attempt45_source_domain_mapping_performed",
        "attempt45_candidate_feasibility_proven",
        "attempt45_triangulation_performed",
        "attempt45_reconstruction_performed",
        "attempt45_body_mutation_performed",
        "attempt45_render_reached",
        "attempt45_blend_saved",
        "runtime_changed",
        "executable_body_repair_justified",
        "body_repair_proven",
        "owner_approval_claimed",
    )
    if any(bool(config["truth"][name]) for name in forbidden_truth):
        raise RuntimeError("Attempt 45 static truth overclaims execution or repair")


def _float_exact(first: Any, second: Any, tolerance: float = 1.0e-15) -> bool:
    return math.isclose(float(first), float(second), rel_tol=0.0, abs_tol=tolerance)


def verify_attempt44_runtime(
    config: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    def read(name: str) -> Any:
        return json.loads(
            project_path(str(records[name]["path"])).read_text(encoding="utf-8")
        )

    started = read("attempt44_started")
    diagnostic = read("attempt44_diagnostic")
    failure = read("attempt44_failure")
    integrity = read("attempt44_external_integrity")
    cache_path = project_path(str(config["preserved_existing_bytecode_cache"]["path"]))
    if (
        started.get("status") != "READ_ONLY_SOURCE_BOUNDARY_DIAGNOSTIC_STARTED"
        or started.get("worker_sha256") != EXPECTED_ATTEMPT44_WORKER_SHA256
        or started.get("config_sha256") != EXPECTED_ATTEMPT44_CONFIG_SHA256
    ):
        raise RuntimeError("Attempt 45 bound Attempt 44 start identity drifted")
    if (
        failure.get("status") != "NO_SAVE_ATTEMPT44_DIAGNOSTIC_STOP_PRESERVED"
        or not failure.get("diagnostic_exists")
        or any(
            bool(failure.get(name))
            for name in (
                "mesh_mutated",
                "body_mutated",
                "render_reached",
                "blend_saved",
                "runtime_changed",
            )
        )
    ):
        raise RuntimeError("Attempt 45 bound Attempt 44 failure truth drifted")
    expected_cache_row = {
        "path": str(cache_path.resolve()),
        "bytes": 36680,
        "sha256": EXPECTED_CACHE_SHA256,
    }
    if (
        integrity.get("blender_exit_code") != 1
        or integrity.get("native_invocation_error") is not None
        or integrity.get("pre_post_exact") is not True
        or integrity.get("before") != integrity.get("after")
        or len(integrity.get("before", [])) != 317
        or integrity.get("relevant_bytecode_cache_inventory_exact") is not True
        or integrity.get("expected_relevant_bytecode_cache_paths")
        != [str(cache_path.resolve())]
        or integrity.get("relevant_bytecode_caches_before") != [expected_cache_row]
        or integrity.get("relevant_bytecode_caches_after") != [expected_cache_row]
    ):
        raise RuntimeError("Attempt 45 bound Attempt 44 integrity drifted")
    protected = []
    seen: set[Path] = set()
    for row in integrity["before"]:
        path = Path(str(row["path"])).resolve(strict=True)
        if ROOT.resolve() != path and ROOT.resolve() not in path.parents:
            raise RuntimeError(f"Attempt 45 protected path escapes project: {path}")
        if path in seen:
            raise RuntimeError(f"Attempt 45 duplicate protected path: {path}")
        seen.add(path)
        actual = file_record(path)
        if (
            actual["bytes"] != int(row["bytes"])
            or actual["sha256"] != str(row["sha256"]).lower()
        ):
            raise RuntimeError(f"Attempt 45 protected file drifted: {path}")
        protected.append(actual)
    if len(protected) != 317:
        raise RuntimeError("Attempt 45 did not verify all 317 protected records")
    if cache_path.stat().st_size != 36680 or sha256_file(cache_path) != EXPECTED_CACHE_SHA256:
        raise RuntimeError("Attempt 45 preserved Attempt 40 cache drifted")
    if (
        diagnostic.get("attempt_id") != "attempt_44"
        or diagnostic.get("status")
        != "CAPTURED_EXISTING_SOURCE_BOUNDARY_OPTIONS_NO_REPAIR"
        or len(diagnostic.get("targeted_complete_vertex_star_candidates", [])) != 1
        or diagnostic.get("uniform_face_ring_candidates") != []
        or diagnostic.get("necessary_eligible_candidate_count") != 0
        or diagnostic.get("smallest_necessary_eligible_existing_source_candidate")
        is not None
    ):
        raise RuntimeError("Attempt 45 bound Attempt 44 candidate count drifted")
    candidate = diagnostic["targeted_complete_vertex_star_candidates"][0]
    expected = config["attempt44_runtime_result"]
    checks = (
        candidate.get("candidate") == expected["candidate"],
        int(candidate["face_count"]) == int(expected["face_count"]),
        candidate["face_indices_sha256"] == expected["face_indices_sha256"],
        int(candidate["vertex_count"]) == int(expected["vertex_count"]),
        candidate["vertex_indices_sha256"] == expected["vertex_indices_sha256"],
        int(candidate["edge_count"]) == int(expected["edge_count"]),
        int(candidate["boundary_edge_count"]) == int(expected["boundary_edge_count"]),
        candidate["boundary_edge_indices_sha256"]
        == expected["boundary_edge_indices_sha256"],
        candidate["boundary_cycle_mesh_vertex_indices"]
        == expected["boundary_cycle_mesh_vertex_indices"],
        candidate["boundary_cycle_mesh_vertex_indices_sha256"]
        == expected["boundary_cycle_mesh_vertex_indices_sha256"],
        candidate["complete_source_mesh_vertex_star_face_indices"]
        == expected["complete_source_mesh_vertex_star_face_indices"],
        candidate["added_complete_source_mesh_vertex_star_face_indices"]
        == expected["added_complete_source_mesh_vertex_star_face_indices"],
        candidate["eligibility_failures"] == expected["eligibility_failures"],
        candidate["necessary_candidate_eligibility_passes"] is False,
    )
    if not all(checks):
        raise RuntimeError("Attempt 45 bound Attempt 44 candidate identity drifted")
    chart = candidate["chart"]
    attribution = chart["boundary_deviation_attribution"]
    forced = candidate["forced_ear_feasibility"]
    obstruction = forced["obstructions"][0]
    if (
        not _float_exact(
            chart["maximum_absolute_boundary_deviation_m"],
            expected["maximum_chart_boundary_deviation_m"],
        )
        or not _float_exact(
            chart["rms_absolute_boundary_deviation_m"],
            expected["rms_chart_boundary_deviation_m"],
        )
        or attribution["maximum_contributor_boundary_indices"] != [4]
        or attribution["maximum_contributor_mesh_vertex_indices"] != [218]
        or int(attribution["exceeding_row_count"]) != 11
        or forced.get("passes") is not False
        or int(forced["obstruction_count"]) != 1
        or int(obstruction["boundary_index"]) != 12
        or int(candidate["boundary_cycle_mesh_vertex_indices"][12]) != 508
        or not _float_exact(
            obstruction["fixed_ear_minimum_angle_degrees"],
            expected["forced_ear_obstruction_minimum_angle_degrees"][0],
        )
    ):
        raise RuntimeError("Attempt 45 bound Attempt 44 blocker identity drifted")
    for name in (
        "replacement_boundary_repair_applied",
        "triangulation_performed",
        "mesh_mutated",
        "body_mutated",
        "render_reached",
        "blend_saved",
        "runtime_changed",
        "necessary_candidate_is_sufficient_repair_proof",
        "executable_body_repair_justified",
    ):
        if bool(diagnostic["truth"][name]):
            raise RuntimeError(f"Attempt 45 bound Attempt 44 overclaims: {name}")
    return {
        "started": started,
        "diagnostic": diagnostic,
        "failure": failure,
        "integrity": integrity,
        "protected_records": protected,
        "candidate": candidate,
        "cache_record": file_record(cache_path),
    }


def exact_replace(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Attempt 45 source replacement drifted: {label}: {count}")
    return source.replace(old, new, 1)


def exact_span_replace(
    source: str,
    start_anchor: str,
    end_anchor: str,
    expected_sha256: str,
    replacement: str,
    label: str,
) -> str:
    if source.count(start_anchor) != 1 or source.count(end_anchor) != 1:
        raise RuntimeError(f"Attempt 45 span anchors drifted: {label}")
    start = source.index(start_anchor)
    end = source.index(end_anchor, start)
    old = source[start:end]
    if sha256_text(old) != expected_sha256:
        raise RuntimeError(f"Attempt 45 span hash drifted: {label}: {sha256_text(old)}")
    return source[:start] + replacement + source[end:]


CANDIDATE_MAPPING_REPLACEMENT = '''        targeted = []
        base_contract = ATTEMPT44_RUNTIME_BASE_DOMAIN
        previous_contract = ATTEMPT44_RUNTIME_RESULT
        probe = ATTEMPT44_RUNTIME_PROBE
        base_selected = set(current)
        base_selected.update(
            int(value)
            for value in base_contract["added_complete_existing_source_face_indices"]
        )
        if (
            len(base_selected) != int(base_contract["complete_face_count"])
            or canonical_sha256(sorted(base_selected))
            != base_contract["complete_face_indices_sha256"]
        ):
            raise RuntimeError("Attempt 44 exact complete Attempt 43 base drifted")
        base_row = _domain_diagnostic(
            "reverified_complete_attempt43_domain",
            base_selected,
            obj,
            bm,
            faces_by_index,
            global_seam_vertices,
            global_seam_edges,
            float(config["diagnosis"]["required_minimum_angle_degrees"]),
            float(source_contract["maximum_local_chart_boundary_deviation_m"]),
            np,
            Vector,
        )
        if (
            int(base_row["face_count"]) != int(base_contract["complete_face_count"])
            or base_row["face_indices_sha256"]
            != base_contract["complete_face_indices_sha256"]
            or int(base_row["vertex_count"])
            != int(base_contract["complete_vertex_count"])
            or base_row["vertex_indices_sha256"]
            != base_contract["complete_vertex_indices_sha256"]
            or int(base_row["boundary_edge_count"])
            != int(base_contract["complete_boundary_edge_count"])
            or base_row["boundary_edge_indices_sha256"]
            != base_contract["complete_boundary_edge_indices_sha256"]
            or base_row["boundary_cycle_mesh_vertex_indices"]
            != base_contract["complete_boundary_cycle_mesh_vertex_indices"]
            or base_row["boundary_cycle_mesh_vertex_indices_sha256"]
            != base_contract["complete_boundary_cycle_mesh_vertex_indices_sha256"]
        ):
            raise RuntimeError("Attempt 44 reverified Attempt 43 base topology drifted")
        star_241 = {int(face.index) for face in bm.verts[241].link_faces}
        if sorted(star_241) != previous_contract[
            "complete_source_mesh_vertex_star_face_indices"
        ]:
            raise RuntimeError("Attempt 44 source star 241 drifted")
        previous_selected = set(base_selected)
        previous_selected.update(star_241)
        previous_row = _domain_diagnostic(
            "reverified_complete___PREVIOUS_ATTEMPT___candidate",
            previous_selected,
            obj,
            bm,
            faces_by_index,
            global_seam_vertices,
            global_seam_edges,
            float(config["diagnosis"]["required_minimum_angle_degrees"]),
            float(source_contract["maximum_local_chart_boundary_deviation_m"]),
            np,
            Vector,
        )
        previous_forced = attempt44_forced_ear_feasibility(
            previous_row, float(config["diagnosis"]["required_minimum_angle_degrees"])
        )
        previous_row["forced_ear_feasibility"] = previous_forced
        if not previous_forced["passes"]:
            previous_row["necessary_candidate_eligibility_passes"] = False
            previous_row["eligibility_failures"] = list(
                previous_row["eligibility_failures"]
            ) + ["forced_prev_current_next_ear_all_angles_at_least_12_degrees"]
        previous_attribution = previous_row["chart"][
            "boundary_deviation_attribution"
        ]
        previous_obstruction = previous_forced["obstructions"][0]
        previous_checks = (
            int(previous_row["face_count"]) == int(previous_contract["face_count"]),
            previous_row["face_indices_sha256"]
            == previous_contract["face_indices_sha256"],
            int(previous_row["vertex_count"])
            == int(previous_contract["vertex_count"]),
            previous_row["vertex_indices_sha256"]
            == previous_contract["vertex_indices_sha256"],
            int(previous_row["edge_count"]) == int(previous_contract["edge_count"]),
            int(previous_row["boundary_edge_count"])
            == int(previous_contract["boundary_edge_count"]),
            previous_row["boundary_edge_indices_sha256"]
            == previous_contract["boundary_edge_indices_sha256"],
            previous_row["boundary_cycle_mesh_vertex_indices"]
            == previous_contract["boundary_cycle_mesh_vertex_indices"],
            previous_row["boundary_cycle_mesh_vertex_indices_sha256"]
            == previous_contract["boundary_cycle_mesh_vertex_indices_sha256"],
            previous_row["eligibility_failures"]
            == previous_contract["eligibility_failures"],
            previous_attribution["maximum_contributor_boundary_indices"]
            == [int(probe["attempt44_chart_maximum_boundary_index"])],
            previous_attribution["maximum_contributor_mesh_vertex_indices"]
            == [int(probe["attempt44_chart_maximum_mesh_vertex_index"])],
            int(previous_obstruction["boundary_index"])
            == int(probe["attempt44_forced_ear_obstruction_boundary_index"]),
            int(
                previous_row["boundary_cycle_mesh_vertex_indices"][
                    int(probe["attempt44_forced_ear_obstruction_boundary_index"])
                ]
            )
            == int(probe["attempt44_forced_ear_obstruction_mesh_vertex_index"]),
        )
        if not all(previous_checks):
            raise RuntimeError("Attempt 44 exact candidate or blockers drifted")
        selected = set(previous_selected)
        compound_star_rows = []
        for blocker_vertex in probe["new_compound_blocker_source_mesh_vertex_stars"]:
            blocker_vertex = int(blocker_vertex)
            complete_star = {
                int(face.index) for face in bm.verts[blocker_vertex].link_faces
            }
            added = complete_star.difference(selected)
            if not added:
                raise RuntimeError(
                    f"Attempt 44 compound blocker star adds no face: {blocker_vertex}"
                )
            compound_star_rows.append(
                {
                    "mesh_vertex_index": blocker_vertex,
                    "complete_source_mesh_vertex_star_face_count": len(complete_star),
                    "complete_source_mesh_vertex_star_face_indices": sorted(complete_star),
                    "added_source_face_count_at_union_step": len(added),
                    "added_source_face_indices_at_union_step": sorted(added),
                }
            )
            selected.update(complete_star)
        row = _domain_diagnostic(
            "complete___PREVIOUS_ATTEMPT___domain_plus_complete_mesh_vertex_stars_218_508",
            selected,
            obj,
            bm,
            faces_by_index,
            global_seam_vertices,
            global_seam_edges,
            float(config["diagnosis"]["required_minimum_angle_degrees"]),
            float(source_contract["maximum_local_chart_boundary_deviation_m"]),
            np,
            Vector,
        )
        forced_ear = attempt44_forced_ear_feasibility(
            row, float(config["diagnosis"]["required_minimum_angle_degrees"])
        )
        row["forced_ear_feasibility"] = forced_ear
        if not forced_ear["passes"]:
            row["necessary_candidate_eligibility_passes"] = False
            row["eligibility_failures"] = list(row["eligibility_failures"]) + [
                "forced_prev_current_next_ear_all_angles_at_least_12_degrees"
            ]
        row["base_candidate"] = probe["base_candidate"]
        row["base_face_count"] = len(previous_selected)
        row["base_face_indices_sha256"] = canonical_sha256(
            sorted(previous_selected)
        )
        row["one_indivisible_compound_candidate"] = True
        row["compound_blocker_source_mesh_vertex_indices"] = list(
            probe["new_compound_blocker_source_mesh_vertex_stars"]
        )
        row["compound_source_star_rows"] = compound_star_rows
        targeted.append(row)
        ring_rows = []

'''


def derive_attempt44_context(attempt44: Any, config44: Mapping[str, Any]) -> dict[str, Any]:
    attempt43 = attempt44.load_static_module(
        "attempt45_bound_attempt43", attempt44.ATTEMPT43_WORKER
    )
    context43 = attempt44.reconstruct_attempt43_static(attempt43, config44)
    source44 = attempt44.derive_attempt44_source(
        config44, context43["attempt43_source"]
    )
    if sha256_text(source44) != EXPECTED_ATTEMPT44_DERIVED_SHA256:
        raise RuntimeError("Attempt 45 exact Attempt 44 derived source drifted")
    attempt43_diagnostic = json.loads(
        project_path(
            str(config44["bindings"]["attempt43_diagnostic"]["path"])
        ).read_text(encoding="utf-8")
    )
    runtime44 = attempt44.build_runtime_config(
        config44,
        context43["attempt43_runtime_config"],
        attempt43_diagnostic,
    )
    return {
        "attempt43": attempt43,
        "context43": context43,
        "source44": source44,
        "runtime44": runtime44,
    }


def derive_attempt45_source(source44: str) -> str:
    if sha256_text(source44) != EXPECTED_ATTEMPT44_DERIVED_SHA256:
        raise RuntimeError("Attempt 45 base derived source drifted")
    source = exact_replace(
        source44,
        EXPECTED_ATTEMPT44_CONFIG_SHA256,
        EXPECTED_CONFIG_SHA256,
        "bind Attempt 45 config hash",
    )
    source = exact_replace(
        source,
        "STATIC_READ_ONLY_CHART_MAXIMUM_STAR_PROOF_PREPARED_NOT_RUN",
        "STATIC_READ_ONLY_COMPOUND_LOCAL_BLOCKER_STARS_PROOF_PREPARED_NOT_RUN",
        "bind Attempt 45 static status",
    )
    source = exact_span_replace(
        source,
        "        targeted = []\n",
        "        coordinate_only = ATTEMPT44_BOUND_COORDINATE_ONLY\n",
        EXPECTED_ATTEMPT44_MAPPING_BLOCK_SHA256,
        CANDIDATE_MAPPING_REPLACEMENT,
        "replace mapping with exact compound blocker stars",
    )
    old_provenance = (
        '            "attempt43_runtime_result": ATTEMPT44_RUNTIME_RESULT,\n'
        '            "attempt43_complete_candidate_reverified": base_row,\n'
        '            "one_candidate_probe": ATTEMPT44_RUNTIME_PROBE,\n'
        '            "targeted_complete_vertex_star_candidates": targeted,\n'
    )
    new_provenance = (
        '            "__PREVIOUS_RUNTIME_RESULT__": ATTEMPT44_RUNTIME_RESULT,\n'
        '            "attempt43_complete_candidate_reverified": base_row,\n'
        '            "__PREVIOUS_COMPLETE_CANDIDATE_REVERIFIED__": previous_row,\n'
        '            "one_candidate_probe": ATTEMPT44_RUNTIME_PROBE,\n'
        '            "targeted_complete_vertex_star_candidates": targeted,\n'
    )
    source = exact_replace(
        source, old_provenance, new_provenance, "record Attempt 45 provenance"
    )
    source = exact_replace(
        source,
        '                "attempt43_complete_domain_used_only_as_read_only_base": True,\n',
        '                "attempt43_complete_domain_used_only_as_read_only_base": True,\n'
        '                "__PREVIOUS_COMPLETE_CANDIDATE_USED_ONLY_AS_READ_ONLY_BASE__": True,\n',
        "record preserved Attempt 44 base-use truth",
    )
    for old, new in (
        ("attempt_44", "attempt_45"),
        ("attempt44", "attempt45"),
        ("Attempt 44", "Attempt 45"),
        ("ATTEMPT44", "ATTEMPT45"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 45 source identity token disappeared: {old}")
        source = source.replace(old, new)
    source = source.replace("__PREVIOUS_RUNTIME_RESULT__", "attempt44_runtime_result")
    source = source.replace(
        "__PREVIOUS_COMPLETE_CANDIDATE_REVERIFIED__",
        "attempt44_complete_candidate_reverified",
    )
    source = source.replace(
        "__PREVIOUS_COMPLETE_CANDIDATE_USED_ONLY_AS_READ_ONLY_BASE__",
        "attempt44_complete_candidate_used_only_as_read_only_base",
    )
    source = source.replace("__PREVIOUS_ATTEMPT__", "attempt44")
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "attempt45_source_identity_evidence",
        "attempt45_forced_ear_feasibility",
        "run_blender_diagnostic",
        "_domain_diagnostic",
    }
    if not required.issubset(names):
        raise RuntimeError("Attempt 45 derived read-only helpers are absent")
    required_tokens = (
        '"compound_source_star_rows"',
        '"one_indivisible_compound_candidate"',
        '"attempt44_runtime_result"',
        '"attempt44_complete_candidate_reverified"',
        '"attempt44_complete_candidate_used_only_as_read_only_base"',
        '"boundary_deviation_attribution"',
    )
    if any(token not in source for token in required_tokens):
        raise RuntimeError("Attempt 45 derived compound evidence is absent")
    forbidden_calls = (
        "bpy.ops.wm.save",
        "bpy.ops.render",
        "bpy.ops.export",
        "bpy.ops.object.join",
        "bmesh.ops.delete",
        "to_mesh(",
    )
    if any(value in source for value in forbidden_calls):
        raise RuntimeError("Attempt 45 derived source contains a forbidden operation")
    return source


def build_runtime_config(
    config: Mapping[str, Any],
    runtime44: Mapping[str, Any],
    diagnostic44: Mapping[str, Any],
) -> dict[str, Any]:
    runtime = json.loads(json.dumps(runtime44))
    for key in ("attempt_id", "status", "mode", "scope", "output", "proposal", "truth"):
        runtime[key] = json.loads(json.dumps(config[key]))
    runtime["bindings"].update(json.loads(json.dumps(config["bindings"])))
    runtime["source_mesh_diagnostic"]["targeted_vertex_star_suppression_sets"] = []
    runtime["source_mesh_diagnostic"]["uniform_face_ring_expansions_to_map"] = []
    runtime["source_mesh_diagnostic"]["eligible_candidate_requires"] = list(
        runtime["source_mesh_diagnostic"]["eligible_candidate_requires"]
    ) + [
        "per_boundary_chart_deviation_attribution",
        "exact_attempt44_candidate_reverification",
        "one_indivisible_complete_source_star_union_218_508",
    ]
    runtime["attempt44_runtime_result"] = json.loads(
        json.dumps(config["attempt44_runtime_result"])
    )
    runtime["attempt43_base_domain"] = json.loads(
        json.dumps(config["attempt43_base_domain"])
    )
    runtime["one_candidate_probe"] = json.loads(json.dumps(config["one_candidate_probe"]))
    runtime["chart_attribution_contract"] = json.loads(
        json.dumps(config["chart_attribution_contract"])
    )
    runtime["coordinate_only_analysis"] = json.loads(
        json.dumps(diagnostic44["coordinate_only_analysis"])
    )
    return runtime


def verify_package(config: Mapping[str, Any]) -> dict[str, Any]:
    if sys.dont_write_bytecode is not True:
        raise RuntimeError("Attempt 45 bytecode containment is not active")
    records = {
        str(name): require_record(str(name), record)
        for name, record in config["bindings"].items()
    }
    records["proposal"] = require_record("proposal", config["proposal"])
    if records["attempt44_worker"]["sha256"] != EXPECTED_ATTEMPT44_WORKER_SHA256:
        raise RuntimeError("Attempt 45 bound Attempt 44 worker disagrees")
    if records["attempt44_config"]["sha256"] != EXPECTED_ATTEMPT44_CONFIG_SHA256:
        raise RuntimeError("Attempt 45 bound Attempt 44 config disagrees")
    evidence = verify_attempt44_runtime(config, records)
    attempt44 = load_static_module("attempt45_bound_attempt44", ATTEMPT44_WORKER)
    config44 = json.loads(
        project_path(str(config["bindings"]["attempt44_config"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    context = derive_attempt44_context(attempt44, config44)
    runtime = build_runtime_config(
        config, context["runtime44"], evidence["diagnostic"]
    )
    source = derive_attempt45_source(context["source44"])
    namespace = {
        "__name__": "attempt45_static_runtime_contract",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
    }
    exec(
        compile(source, str(Path(__file__).resolve()) + "::derived-contract", "exec"),
        namespace,
        namespace,
    )
    namespace["validate_config"](runtime)
    derived_hash = sha256_text(source)
    if (
        EXPECTED_DERIVED_SHA256 != "TO_BE_BOUND_AFTER_STATIC_DERIVATION"
        and derived_hash != EXPECTED_DERIVED_SHA256
    ):
        raise RuntimeError(f"Attempt 45 derived source hash drifted: {derived_hash}")
    return {
        "records": records,
        "attempt44_evidence": evidence,
        "attempt44": attempt44,
        "attempt44_context": context,
        "runtime_config": runtime,
        "derived_source": source,
        "derived_source_sha256": derived_hash,
    }


def run_blender(config: Mapping[str, Any], verified: Mapping[str, Any]) -> None:
    if sys.dont_write_bytecode is not True:
        raise RuntimeError("Attempt 45 Blender bytecode containment is not active")
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "ATTEMPT45_RUNTIME_CONFIG": verified["runtime_config"],
        "ATTEMPT45_RUNTIME_RESULT": json.loads(
            json.dumps(config["attempt44_runtime_result"])
        ),
        "ATTEMPT45_RUNTIME_BASE_DOMAIN": json.loads(
            json.dumps(config["attempt43_base_domain"])
        ),
        "ATTEMPT45_RUNTIME_PROBE": json.loads(
            json.dumps(config["one_candidate_probe"])
        ),
        "ATTEMPT45_BOUND_COORDINATE_ONLY": json.loads(
            json.dumps(
                verified["attempt44_evidence"]["diagnostic"]["coordinate_only_analysis"]
            )
        ),
    }
    exec(
        compile(
            verified["derived_source"],
            str(Path(__file__).resolve()) + "::derived",
            "exec",
        ),
        namespace,
        namespace,
    )


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    values = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args(values)


def main() -> None:
    args = parse_args()
    config = load_config(Path(args.config).resolve(strict=True))
    verified = verify_package(config)
    run_blender(config, verified)


if __name__ == "__main__":
    main()
