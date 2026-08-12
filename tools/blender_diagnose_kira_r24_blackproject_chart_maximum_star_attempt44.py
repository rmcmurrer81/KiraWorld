"""Attempt 44 static-first chart-maximum source-star proof.

This module binds the complete preserved Attempt 43 package and one-shot
runtime evidence, then derives exactly one later read-only mapper. Importing
it is Blender-free and creates no Attempt 44 evidence.
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
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT44_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = (
    "78bf8b2f44460b0091f72eb6115971da6bb592acb205e036259f5fece0c193b3"
)
ATTEMPT43_WORKER = ROOT / (
    "tools/blender_diagnose_kira_r24_blackproject_shared_obstruction_star_attempt43.py"
)
EXPECTED_ATTEMPT43_WORKER_SHA256 = (
    "91d95ba542aac127a6815cf404aa8767414872cb715f03278956ad3f6f4b83ba"
)
EXPECTED_ATTEMPT43_CONFIG_SHA256 = (
    "b5ffb534fd5e302341673a69f7ba707a579a2a7347c6596862802e9e6904a6f1"
)
EXPECTED_ATTEMPT43_DERIVED_SHA256 = (
    "99fce13f2d6501c6abee894c0031766ce15eed7e8e69f190ed15f6535eddc854"
)
EXPECTED_ATTEMPT43_CANDIDATE_BLOCK_SHA256 = (
    "c8b741c705299e5d76640391d888b4126daa4d14b5ef4c174721829ebb4f0122"
)
EXPECTED_CACHE_SHA256 = (
    "340ddf1fcbb97d8bd309280061f05dd6a914b79c1e36abce69134501902c162f"
)
EXPECTED_DERIVED_SHA256 = (
    "216eb9b56dbb8ee768167756e2590d42b33f692d5a275013fed32a970c24613b"
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
        raise RuntimeError(f"Attempt 44 path escapes project: {value}")
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
        raise RuntimeError(f"Attempt 44 binding byte count drifted: {name}")
    if actual["sha256"] != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 44 binding hash drifted: {name}")
    return actual


def load_static_module(name: str, path: Path) -> Any:
    if sys.dont_write_bytecode is not True:
        raise RuntimeError("Attempt 44 bytecode containment was disabled")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Attempt 44 cannot load bound worker: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 44 requires the exact sealed config path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 44 config hash drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_44"
        or config.get("status")
        != "STATIC_READ_ONLY_CHART_MAXIMUM_STAR_PROOF_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 44 identity drifted")
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
        "exact_one_chart_maximum_vertex_star_mapping_allowed",
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
        "automatic_alternate_candidate_allowed",
        "automatic_retry_allowed",
    )
    if not all(bool(scope[name]) for name in required_true):
        raise RuntimeError("Attempt 44 lost a required read-only scope")
    if any(bool(scope[name]) for name in forbidden):
        raise RuntimeError("Attempt 44 permits a forbidden operation")
    expected_output = {
        "root": (
            "RecoverySprint/continuation_20260803/"
            "kira_r24_internal_midpoint_fair_surface/attempt_44"
        ),
        "started": "ATTEMPT_STARTED.json",
        "diagnostic": "CHART_MAXIMUM_STAR_ATTRIBUTION_DIAGNOSTIC.json",
        "failure": "FAILURE.json",
        "blend_save_permitted": False,
        "render_permitted": False,
    }
    if config["output"] != expected_output:
        raise RuntimeError("Attempt 44 output contract drifted")
    if project_path(expected_output["root"], must_exist=False).exists():
        raise RuntimeError("Attempt 44 output already exists")
    probe = config["one_candidate_probe"]
    if (
        probe["candidate"]
        != "complete_attempt43_domain_plus_complete_mesh_vertex_star_241"
        or probe["base_candidate"]
        != "complete_attempt42_domain_plus_complete_mesh_vertex_star_463"
        or int(probe["exact_chart_maximum_boundary_index_before_expansion"]) != 3
        or int(probe["exact_chart_maximum_mesh_vertex_index"]) != 241
        or not bool(probe["sole_chart_maximum_contributor"])
        or not bool(probe["complete_source_mesh_vertex_star_only"])
        or bool(probe["uniform_face_ring_candidates_allowed"])
        or bool(probe["alternate_target_sets_allowed"])
        or bool(probe["coordinate_suppression_allowed"])
    ):
        raise RuntimeError("Attempt 44 one-candidate probe drifted")
    attribution = config["chart_attribution_contract"]
    if (
        float(attribution["maximum_allowed_boundary_deviation_m"]) != 0.0011
        or not bool(attribution["required_for_base_and_candidate"])
        or not bool(attribution["one_row_per_ordered_boundary_vertex"])
        or bool(attribution["attribution_authorizes_vertex_movement"])
        or bool(attribution["attribution_authorizes_gate_change"])
    ):
        raise RuntimeError("Attempt 44 chart attribution contract drifted")
    cache = config["preserved_existing_bytecode_cache"]
    if (
        int(cache["bytes"]) != 36680
        or cache["sha256"] != EXPECTED_CACHE_SHA256
        or not bool(cache["must_remain_exact"])
        or not bool(cache["must_not_be_deleted"])
    ):
        raise RuntimeError("Attempt 44 preserved-cache contract drifted")
    launch = config["launch_contract"]
    if (
        launch["arguments_before_python"]
        != ["--background", "--factory-startup", "--disable-autoexec", "--python-exit-code", "1"]
        or not bool(launch["wrapper_unions_attempt43_304_entry_inventory"])
        or not bool(launch["wrapper_verifies_all_attempt43_records_before_blender"])
        or not bool(launch["wrapper_protects_attempt40_generated_cpython313_cache"])
        or not bool(launch["wrapper_refuses_any_new_relevant_worker_cache"])
        or not bool(launch["worker_sets_sys_dont_write_bytecode_before_bound_worker_load"])
        or not bool(launch["exactly_one_blender_invocation_required"])
        or not bool(launch["refuse_any_overwrite"])
        or bool(launch["executed_during_static_preparation"])
    ):
        raise RuntimeError("Attempt 44 launch contract drifted")
    forbidden_truth = (
        "attempt44_blender_execution_performed",
        "attempt44_source_domain_mapping_performed",
        "attempt44_candidate_feasibility_proven",
        "attempt44_triangulation_performed",
        "attempt44_reconstruction_performed",
        "attempt44_body_mutation_performed",
        "attempt44_render_reached",
        "attempt44_blend_saved",
        "runtime_changed",
        "executable_body_repair_justified",
        "body_repair_proven",
        "owner_approval_claimed",
    )
    if any(bool(config["truth"][name]) for name in forbidden_truth):
        raise RuntimeError("Attempt 44 static truth overclaims execution or repair")


def _float_exact(first: Any, second: Any, tolerance: float = 1.0e-15) -> bool:
    return math.isclose(float(first), float(second), rel_tol=0.0, abs_tol=tolerance)


def verify_attempt43_runtime(
    config: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    def read(name: str) -> Any:
        return json.loads(
            project_path(str(records[name]["path"])).read_text(encoding="utf-8")
        )

    started = read("attempt43_started")
    diagnostic = read("attempt43_diagnostic")
    failure = read("attempt43_failure")
    integrity = read("attempt43_external_integrity")
    cache_path = project_path(str(records["attempt40_generated_cache"]["path"]))
    if (
        started.get("status") != "READ_ONLY_SOURCE_BOUNDARY_DIAGNOSTIC_STARTED"
        or started.get("worker_sha256") != EXPECTED_ATTEMPT43_WORKER_SHA256
        or started.get("config_sha256") != EXPECTED_ATTEMPT43_CONFIG_SHA256
    ):
        raise RuntimeError("Attempt 44 bound Attempt 43 start identity drifted")
    if (
        failure.get("status") != "NO_SAVE_ATTEMPT43_DIAGNOSTIC_STOP_PRESERVED"
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
        raise RuntimeError("Attempt 44 bound Attempt 43 failure truth drifted")
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
        or len(integrity.get("before", [])) != 304
        or integrity.get("relevant_bytecode_cache_inventory_exact") is not True
        or integrity.get("expected_relevant_bytecode_cache_paths")
        != [str(cache_path.resolve())]
        or integrity.get("relevant_bytecode_caches_before") != [expected_cache_row]
        or integrity.get("relevant_bytecode_caches_after") != [expected_cache_row]
    ):
        raise RuntimeError("Attempt 44 bound Attempt 43 integrity drifted")
    protected = []
    seen: set[Path] = set()
    for row in integrity["before"]:
        path = Path(str(row["path"])).resolve(strict=True)
        if ROOT.resolve() != path and ROOT.resolve() not in path.parents:
            raise RuntimeError(f"Attempt 44 protected path escapes project: {path}")
        if path in seen:
            raise RuntimeError(f"Attempt 44 duplicate protected path: {path}")
        seen.add(path)
        actual = file_record(path)
        if (
            actual["bytes"] != int(row["bytes"])
            or actual["sha256"] != str(row["sha256"]).lower()
        ):
            raise RuntimeError(f"Attempt 44 protected file drifted: {path}")
        protected.append(actual)
    if len(protected) != 304:
        raise RuntimeError("Attempt 44 did not verify all 304 protected records")
    if cache_path.stat().st_size != 36680 or sha256_file(cache_path) != EXPECTED_CACHE_SHA256:
        raise RuntimeError("Attempt 44 preserved Attempt 40 cache drifted")
    if (
        diagnostic.get("attempt_id") != "attempt_43"
        or len(diagnostic.get("targeted_complete_vertex_star_candidates", [])) != 1
        or diagnostic.get("uniform_face_ring_candidates") != []
        or diagnostic.get("necessary_eligible_candidate_count") != 0
        or diagnostic.get("smallest_necessary_eligible_existing_source_candidate")
        is not None
    ):
        raise RuntimeError("Attempt 44 bound Attempt 43 candidate count drifted")
    candidate = diagnostic["targeted_complete_vertex_star_candidates"][0]
    expected = config["attempt43_runtime_result"]
    base = config["attempt43_base_domain"]
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
        candidate["eligibility_failures"] == expected["eligibility_failures"],
        candidate["necessary_candidate_eligibility_passes"] is False,
        candidate["complete_source_mesh_vertex_star_face_indices"]
        == expected["complete_source_mesh_vertex_star_face_indices"],
        candidate["added_complete_source_mesh_vertex_star_face_indices"]
        == expected["added_complete_source_mesh_vertex_star_face_indices"],
    )
    if not all(checks):
        raise RuntimeError("Attempt 44 bound Attempt 43 candidate identity drifted")
    if (
        int(base["complete_face_count"]) != int(candidate["face_count"])
        or base["complete_face_indices_sha256"] != candidate["face_indices_sha256"]
        or int(base["complete_vertex_count"]) != int(candidate["vertex_count"])
        or base["complete_vertex_indices_sha256"] != candidate["vertex_indices_sha256"]
        or int(base["complete_boundary_edge_count"])
        != int(candidate["boundary_edge_count"])
        or base["complete_boundary_edge_indices_sha256"]
        != candidate["boundary_edge_indices_sha256"]
        or base["complete_boundary_cycle_mesh_vertex_indices"]
        != candidate["boundary_cycle_mesh_vertex_indices"]
        or len(base["added_complete_existing_source_face_indices"]) != 36
    ):
        raise RuntimeError("Attempt 44 bound Attempt 43 base-domain identity drifted")
    chart = candidate["chart"]
    attribution = chart["boundary_deviation_attribution"]
    rows = attribution["rows"]
    required_fields = set(config["chart_attribution_contract"]["required_row_fields"])
    if (
        not _float_exact(
            chart["maximum_absolute_boundary_deviation_m"],
            expected["maximum_chart_boundary_deviation_m"],
        )
        or not _float_exact(
            chart["rms_absolute_boundary_deviation_m"],
            expected["rms_chart_boundary_deviation_m"],
        )
        or int(attribution["row_count"])
        != len(expected["boundary_cycle_mesh_vertex_indices"])
        or len(rows) != int(attribution["row_count"])
        or any(not required_fields.issubset(row) for row in rows)
        or int(attribution["exceeding_row_count"])
        != int(expected["chart_exceeding_row_count"])
        or attribution["maximum_contributor_boundary_indices"]
        != expected["chart_maximum_contributor_boundary_indices"]
        or attribution["maximum_contributor_mesh_vertex_indices"]
        != expected["chart_maximum_contributor_mesh_vertex_indices"]
    ):
        raise RuntimeError("Attempt 44 bound Attempt 43 chart attribution drifted")
    forced = candidate["forced_ear_feasibility"]
    boundary_index = int(config["one_candidate_probe"]["exact_chart_maximum_boundary_index_before_expansion"])
    if (
        forced.get("passes") is not True
        or int(forced["obstruction_count"]) != 0
        or int(forced["tested_corner_count"])
        != int(expected["forced_ear_tested_corner_count"])
        or int(candidate["boundary_cycle_mesh_vertex_indices"][boundary_index])
        != int(config["one_candidate_probe"]["exact_chart_maximum_mesh_vertex_index"])
        or attribution["maximum_contributor_boundary_indices"] != [boundary_index]
        or attribution["maximum_contributor_mesh_vertex_indices"]
        != [int(config["one_candidate_probe"]["exact_chart_maximum_mesh_vertex_index"])]
    ):
        raise RuntimeError("Attempt 44 bound chart-maximum identity drifted")
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
            raise RuntimeError(f"Attempt 44 bound Attempt 43 overclaims: {name}")
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
        raise RuntimeError(f"Attempt 44 source replacement drifted: {label}: {count}")
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
        raise RuntimeError(f"Attempt 44 span anchors drifted: {label}")
    start = source.index(start_anchor)
    end = source.index(end_anchor, start)
    old = source[start:end]
    if sha256_text(old) != expected_sha256:
        raise RuntimeError(f"Attempt 44 span hash drifted: {label}: {sha256_text(old)}")
    return source[:start] + replacement + source[end:]


CANDIDATE_MAPPING_REPLACEMENT = '''        targeted = []
        base_contract = ATTEMPT44_RUNTIME_BASE_DOMAIN
        base_selected = set(current)
        base_added_faces = {
            int(value)
            for value in base_contract["added_complete_existing_source_face_indices"]
        }
        base_selected.update(base_added_faces)
        if (
            len(base_selected) != int(base_contract["complete_face_count"])
            or canonical_sha256(sorted(base_selected))
            != base_contract["complete_face_indices_sha256"]
        ):
            raise RuntimeError("Attempt 44 exact complete Attempt 43 base domain drifted")
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
        probe = ATTEMPT44_RUNTIME_PROBE
        maximum_boundary_index = int(
            probe["exact_chart_maximum_boundary_index_before_expansion"]
        )
        maximum_vertex_index = int(probe["exact_chart_maximum_mesh_vertex_index"])
        base_attribution = base_row["chart"]["boundary_deviation_attribution"]
        if (
            int(base_row["boundary_cycle_mesh_vertex_indices"][maximum_boundary_index])
            != maximum_vertex_index
            or base_attribution["maximum_contributor_boundary_indices"]
            != [maximum_boundary_index]
            or base_attribution["maximum_contributor_mesh_vertex_indices"]
            != [maximum_vertex_index]
        ):
            raise RuntimeError("Attempt 44 exact chart-maximum identity drifted")
        complete_star_faces = {
            int(face.index) for face in bm.verts[maximum_vertex_index].link_faces
        }
        added_faces = complete_star_faces.difference(base_selected)
        if not added_faces:
            raise RuntimeError("Attempt 44 chart-maximum vertex star adds no source face")
        selected = set(base_selected)
        selected.update(added_faces)
        row = _domain_diagnostic(
            "complete___PREVIOUS_ATTEMPT___domain_plus_complete_mesh_vertex_star_241",
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
        row["base_candidate"] = probe["base_candidate"]
        row["base_face_count"] = len(base_selected)
        row["base_face_indices_sha256"] = canonical_sha256(sorted(base_selected))
        row["exact_chart_maximum_boundary_index_before_expansion"] = (
            maximum_boundary_index
        )
        row["exact_chart_maximum_mesh_vertex_index"] = maximum_vertex_index
        row["sole_chart_maximum_contributor"] = True
        row["complete_source_mesh_vertex_star_face_count"] = len(complete_star_faces)
        row["complete_source_mesh_vertex_star_face_indices"] = sorted(complete_star_faces)
        row["added_complete_source_mesh_vertex_star_face_count"] = len(added_faces)
        row["added_complete_source_mesh_vertex_star_face_indices"] = sorted(added_faces)
        forced_ear = attempt44_forced_ear_feasibility(
            row, float(config["diagnosis"]["required_minimum_angle_degrees"])
        )
        row["forced_ear_feasibility"] = forced_ear
        if not forced_ear["passes"]:
            row["necessary_candidate_eligibility_passes"] = False
            row["eligibility_failures"] = list(row["eligibility_failures"]) + [
                "forced_prev_current_next_ear_all_angles_at_least_12_degrees"
            ]
        targeted.append(row)
        ring_rows = []

'''


def reconstruct_attempt43_static(
    attempt43: Any, config: Mapping[str, Any]
) -> dict[str, Any]:
    attempt43_config = json.loads(
        project_path(config["bindings"]["attempt43_config"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    verified = attempt43.verify_package(attempt43_config)
    source = verified["derived_source"]
    if sha256_text(source) != EXPECTED_ATTEMPT43_DERIVED_SHA256:
        raise RuntimeError("Attempt 44 exact Attempt 43 derived source drifted")
    return {
        "attempt43_config": attempt43_config,
        "attempt43_verified": verified,
        "attempt43_source": source,
        "attempt43_runtime_config": verified["runtime_config"],
    }


def derive_attempt44_source(config: Mapping[str, Any], attempt43_source: str) -> str:
    if sha256_text(attempt43_source) != EXPECTED_ATTEMPT43_DERIVED_SHA256:
        raise RuntimeError("Attempt 44 base derived source drifted")
    source = exact_replace(
        attempt43_source,
        EXPECTED_ATTEMPT43_CONFIG_SHA256,
        EXPECTED_CONFIG_SHA256,
        "bind Attempt 44 config hash",
    )
    source = exact_replace(
        source,
        "STATIC_READ_ONLY_SHARED_OBSTRUCTION_STAR_PROOF_PREPARED_NOT_RUN",
        "STATIC_READ_ONLY_CHART_MAXIMUM_STAR_PROOF_PREPARED_NOT_RUN",
        "bind Attempt 44 static status",
    )
    source = exact_span_replace(
        source,
        "        targeted = []\n",
        "        coordinate_only = ATTEMPT43_BOUND_COORDINATE_ONLY\n",
        EXPECTED_ATTEMPT43_CANDIDATE_BLOCK_SHA256,
        CANDIDATE_MAPPING_REPLACEMENT,
        "replace mapping with exact chart-maximum star",
    )
    old_provenance = (
        '            "attempt42_runtime_result": ATTEMPT43_RUNTIME_RESULT,\n'
        '            "attempt42_complete_candidate_reverified": base_row,\n'
        '            "one_candidate_probe": ATTEMPT43_RUNTIME_PROBE,\n'
        '            "targeted_complete_vertex_star_candidates": targeted,\n'
    )
    new_provenance = (
        '            "__PREVIOUS_RUNTIME_RESULT__": ATTEMPT44_RUNTIME_RESULT,\n'
        '            "__PREVIOUS_BASE_REVERIFIED__": base_row,\n'
        '            "one_candidate_probe": ATTEMPT44_RUNTIME_PROBE,\n'
        '            "targeted_complete_vertex_star_candidates": targeted,\n'
    )
    source = exact_replace(
        source, old_provenance, new_provenance, "record Attempt 44 provenance"
    )
    source = exact_replace(
        source,
        '                "attempt42_complete_domain_used_only_as_read_only_base": True,\n',
        '                "__PREVIOUS_COMPLETE_DOMAIN_USED_ONLY_AS_READ_ONLY_BASE__": True,\n',
        "bind Attempt 43 base-use truth",
    )
    for old, new in (
        ("attempt_43", "attempt_44"),
        ("attempt43", "attempt44"),
        ("Attempt 43", "Attempt 44"),
        ("ATTEMPT43", "ATTEMPT44"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 44 source identity token disappeared: {old}")
        source = source.replace(old, new)
    source = source.replace("__PREVIOUS_RUNTIME_RESULT__", "attempt43_runtime_result")
    source = source.replace(
        "__PREVIOUS_BASE_REVERIFIED__", "attempt43_complete_candidate_reverified"
    )
    source = source.replace(
        "__PREVIOUS_COMPLETE_DOMAIN_USED_ONLY_AS_READ_ONLY_BASE__",
        "attempt43_complete_domain_used_only_as_read_only_base",
    )
    source = source.replace("__PREVIOUS_ATTEMPT__", "attempt43")
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "attempt44_source_identity_evidence",
        "attempt44_forced_ear_feasibility",
        "run_blender_diagnostic",
        "_domain_diagnostic",
    }
    if not required.issubset(names):
        raise RuntimeError("Attempt 44 derived read-only helpers are absent")
    for stale in ("attempt_43", "ATTEMPT43_"):
        if stale in source:
            raise RuntimeError(f"Attempt 44 derived source retained stale token: {stale}")
    required_tokens = (
        '"boundary_deviation_attribution"',
        '"absolute_deviation_rank"',
        '"exceeds_maximum_allowed_deviation"',
        '"exact_chart_maximum_mesh_vertex_index"',
        '"attempt43_runtime_result"',
        '"attempt43_complete_candidate_reverified"',
        '"attempt43_complete_domain_used_only_as_read_only_base"',
    )
    if any(token not in source for token in required_tokens):
        raise RuntimeError("Attempt 44 derived attribution or provenance is absent")
    forbidden_calls = (
        "bpy.ops.wm.save",
        "bpy.ops.render",
        "bpy.ops.export",
        "bpy.ops.object.join",
        "bmesh.ops.delete",
        "to_mesh(",
    )
    if any(value in source for value in forbidden_calls):
        raise RuntimeError("Attempt 44 derived source contains a forbidden operation")
    return source


def build_runtime_config(
    config: Mapping[str, Any],
    attempt43_runtime: Mapping[str, Any],
    diagnostic: Mapping[str, Any],
) -> dict[str, Any]:
    runtime = json.loads(json.dumps(attempt43_runtime))
    for key in ("attempt_id", "status", "mode", "scope", "output", "proposal", "truth"):
        runtime[key] = json.loads(json.dumps(config[key]))
    runtime["bindings"].update(json.loads(json.dumps(config["bindings"])))
    runtime["source_mesh_diagnostic"]["targeted_vertex_star_suppression_sets"] = []
    runtime["source_mesh_diagnostic"]["uniform_face_ring_expansions_to_map"] = []
    runtime["source_mesh_diagnostic"]["eligible_candidate_requires"] = list(
        runtime["source_mesh_diagnostic"]["eligible_candidate_requires"]
    ) + [
        "per_boundary_chart_deviation_attribution",
        "exact_complete_attempt43_base_plus_complete_mesh_vertex_star_241",
    ]
    runtime["attempt43_runtime_result"] = json.loads(
        json.dumps(config["attempt43_runtime_result"])
    )
    runtime["attempt43_base_domain"] = json.loads(
        json.dumps(config["attempt43_base_domain"])
    )
    runtime["one_candidate_probe"] = json.loads(json.dumps(config["one_candidate_probe"]))
    runtime["chart_attribution_contract"] = json.loads(
        json.dumps(config["chart_attribution_contract"])
    )
    runtime["coordinate_only_analysis"] = json.loads(
        json.dumps(diagnostic["coordinate_only_analysis"])
    )
    return runtime


def verify_package(config: Mapping[str, Any]) -> dict[str, Any]:
    if sys.dont_write_bytecode is not True:
        raise RuntimeError("Attempt 44 bytecode containment is not active")
    records = {
        str(name): require_record(str(name), record)
        for name, record in config["bindings"].items()
    }
    records["proposal"] = require_record("proposal", config["proposal"])
    if records["attempt43_worker"]["sha256"] != EXPECTED_ATTEMPT43_WORKER_SHA256:
        raise RuntimeError("Attempt 44 bound Attempt 43 worker disagrees")
    if records["attempt43_config"]["sha256"] != EXPECTED_ATTEMPT43_CONFIG_SHA256:
        raise RuntimeError("Attempt 44 bound Attempt 43 config disagrees")
    evidence = verify_attempt43_runtime(config, records)
    attempt43 = load_static_module("attempt44_bound_attempt43", ATTEMPT43_WORKER)
    context = reconstruct_attempt43_static(attempt43, config)
    runtime = build_runtime_config(
        config, context["attempt43_runtime_config"], evidence["diagnostic"]
    )
    source = derive_attempt44_source(config, context["attempt43_source"])
    namespace = {
        "__name__": "attempt44_static_runtime_contract",
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
        raise RuntimeError(f"Attempt 44 derived source hash drifted: {derived_hash}")
    return {
        "records": records,
        "attempt43_evidence": evidence,
        "attempt43": attempt43,
        "attempt43_context": context,
        "runtime_config": runtime,
        "derived_source": source,
        "derived_source_sha256": derived_hash,
    }


def run_blender(config_path: Path, config: Mapping[str, Any]) -> None:
    if sys.dont_write_bytecode is not True:
        raise RuntimeError("Attempt 44 Blender bytecode containment is not active")
    verified = verify_package(config)
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "ATTEMPT44_RUNTIME_CONFIG": verified["runtime_config"],
        "ATTEMPT44_RUNTIME_RESULT": json.loads(
            json.dumps(config["attempt43_runtime_result"])
        ),
        "ATTEMPT44_RUNTIME_BASE_DOMAIN": json.loads(
            json.dumps(config["attempt43_base_domain"])
        ),
        "ATTEMPT44_RUNTIME_PROBE": json.loads(
            json.dumps(config["one_candidate_probe"])
        ),
        "ATTEMPT44_BOUND_COORDINATE_ONLY": json.loads(
            json.dumps(
                verified["attempt43_evidence"]["diagnostic"]["coordinate_only_analysis"]
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
    config_path = Path(args.config).resolve(strict=True)
    config = load_config(config_path)
    verify_package(config)
    run_blender(config_path, config)


if __name__ == "__main__":
    main()
