"""Attempt 43 static-first shared-obstruction source-star proof.

This module binds the complete preserved Attempt 42 package and its one-shot
runtime evidence, then derives exactly one later read-only mapper. Importing
the module is Blender-free and creates no Attempt 43 evidence.
"""

from __future__ import annotations

import sys

# This assignment deliberately precedes importlib and every bound-module load.
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
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT43_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = (
    "b5ffb534fd5e302341673a69f7ba707a579a2a7347c6596862802e9e6904a6f1"
)
ATTEMPT42_WORKER = (
    ROOT
    / "tools/blender_diagnose_kira_r24_blackproject_shared_obstruction_star_attempt42.py"
)
EXPECTED_ATTEMPT42_WORKER_SHA256 = (
    "5682f9ca85ca54aad71b699ca12c22e206261c0e7967cb4fca87ca36b0ce2595"
)
EXPECTED_ATTEMPT42_CONFIG_SHA256 = (
    "1d3fb520381926d7cf21ff1be1aeaa64cd9f95c7ffd837f69399f2f7320f21d2"
)
EXPECTED_ATTEMPT42_DERIVED_SHA256 = (
    "9d06725f8707fa46d1ce19db69a983a651cea8a5db06c0a566a583bce1188925"
)
EXPECTED_ATTEMPT42_CANDIDATE_BLOCK_SHA256 = (
    "6e5412bffddff627ebce9fcc1a9b6d1d1a839495039814c098e16ffe3c86097c"
)
EXPECTED_CACHE_SHA256 = (
    "340ddf1fcbb97d8bd309280061f05dd6a914b79c1e36abce69134501902c162f"
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
        raise RuntimeError(f"Attempt 43 path escapes project: {value}")
    return path


def load_static_module(name: str, path: Path) -> Any:
    if sys.dont_write_bytecode is not True:
        raise RuntimeError("Attempt 43 bytecode containment was disabled")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Attempt 43 cannot load bound worker: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_record(path: Path) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    return {
        "path": str(exact.relative_to(ROOT)).replace("\\", "/"),
        "bytes": exact.stat().st_size,
        "sha256": sha256_file(exact),
    }


def require_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(record["path"]))
    actual = file_record(path)
    if actual["bytes"] != int(record["bytes"]):
        raise RuntimeError(f"Attempt 43 binding byte count drifted: {name}")
    if actual["sha256"] != str(record["sha256"]).lower():
        raise RuntimeError(
            f"Attempt 43 binding hash drifted: {name}: {actual['sha256']}"
        )
    return actual


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 43 requires the exact sealed config path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 43 config hash drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_43"
        or config.get("status")
        != "STATIC_READ_ONLY_SHARED_OBSTRUCTION_STAR_PROOF_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 43 identity drifted")
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
        "exact_attempt42_base_domain_reverification_required",
        "exact_one_shared_obstruction_vertex_star_mapping_allowed",
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
        raise RuntimeError("Attempt 43 lost a required read-only scope")
    if any(bool(scope[name]) for name in forbidden):
        raise RuntimeError("Attempt 43 permits a forbidden operation")
    expected_output = {
        "root": (
            "RecoverySprint/continuation_20260803/"
            "kira_r24_internal_midpoint_fair_surface/attempt_43"
        ),
        "started": "ATTEMPT_STARTED.json",
        "diagnostic": "SHARED_OBSTRUCTION_STAR_CHART_ATTRIBUTION_DIAGNOSTIC.json",
        "failure": "FAILURE.json",
        "blend_save_permitted": False,
        "render_permitted": False,
    }
    if config["output"] != expected_output:
        raise RuntimeError("Attempt 43 output contract drifted")
    if project_path(expected_output["root"], must_exist=False).exists():
        raise RuntimeError("Attempt 43 output already exists")
    probe = config["one_candidate_probe"]
    if (
        probe["candidate"]
        != "complete_attempt42_domain_plus_complete_mesh_vertex_star_463"
        or probe["base_candidate"]
        != "complete_attempt41_domain_plus_complete_mesh_vertex_star_458"
        or int(probe["exact_shared_obstruction_boundary_index_before_expansion"])
        != 16
        or int(probe["exact_shared_obstruction_mesh_vertex_index"]) != 463
        or not bool(probe["shared_chart_maximum_and_forced_ear_contributor"])
        or not bool(probe["complete_source_mesh_vertex_star_only"])
        or bool(probe["uniform_face_ring_candidates_allowed"])
        or bool(probe["alternate_target_sets_allowed"])
        or bool(probe["coordinate_suppression_allowed"])
    ):
        raise RuntimeError("Attempt 43 one-candidate probe drifted")
    attribution = config["chart_attribution_contract"]
    if (
        float(attribution["maximum_allowed_boundary_deviation_m"]) != 0.0011
        or not bool(attribution["required_for_base_and_candidate"])
        or not bool(attribution["one_row_per_ordered_boundary_vertex"])
        or bool(attribution["attribution_authorizes_vertex_movement"])
        or bool(attribution["attribution_authorizes_gate_change"])
    ):
        raise RuntimeError("Attempt 43 chart attribution contract drifted")
    cache = config["preserved_existing_bytecode_cache"]
    if (
        int(cache["bytes"]) != 36680
        or cache["sha256"] != EXPECTED_CACHE_SHA256
        or not bool(cache["must_remain_exact"])
        or not bool(cache["must_not_be_deleted"])
    ):
        raise RuntimeError("Attempt 43 preserved-cache contract drifted")
    launch = config["launch_contract"]
    if (
        launch["arguments_before_python"]
        != [
            "--background",
            "--factory-startup",
            "--disable-autoexec",
            "--python-exit-code",
            "1",
        ]
        or not bool(launch["wrapper_unions_attempt42_291_entry_inventory"])
        or not bool(launch["wrapper_verifies_all_attempt42_records_before_blender"])
        or not bool(launch["wrapper_protects_attempt40_generated_cpython313_cache"])
        or not bool(launch["wrapper_refuses_any_new_relevant_worker_cache"])
        or not bool(launch["worker_sets_sys_dont_write_bytecode_before_bound_worker_load"])
        or not bool(launch["exactly_one_blender_invocation_required"])
        or not bool(launch["refuse_any_overwrite"])
        or bool(launch["executed_during_static_preparation"])
    ):
        raise RuntimeError("Attempt 43 launch contract drifted")
    forbidden_truth = (
        "attempt43_blender_execution_performed",
        "attempt43_source_domain_mapping_performed",
        "attempt43_candidate_feasibility_proven",
        "attempt43_triangulation_performed",
        "attempt43_reconstruction_performed",
        "attempt43_body_mutation_performed",
        "attempt43_render_reached",
        "attempt43_blend_saved",
        "runtime_changed",
        "executable_body_repair_justified",
        "body_repair_proven",
        "owner_approval_claimed",
    )
    if any(bool(config["truth"][name]) for name in forbidden_truth):
        raise RuntimeError("Attempt 43 static truth overclaims execution or repair")


def _float_exact(first: Any, second: Any, tolerance: float = 1.0e-15) -> bool:
    return math.isclose(float(first), float(second), rel_tol=0.0, abs_tol=tolerance)


def verify_attempt42_runtime(
    config: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    started = json.loads(
        project_path(records["attempt42_started"]["path"]).read_text(encoding="utf-8")
    )
    diagnostic = json.loads(
        project_path(records["attempt42_diagnostic"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    failure = json.loads(
        project_path(records["attempt42_failure"]["path"]).read_text(encoding="utf-8")
    )
    integrity = json.loads(
        project_path(records["attempt42_external_integrity"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    cache_path = project_path(records["attempt40_generated_cache"]["path"])
    if (
        started.get("status") != "READ_ONLY_SOURCE_BOUNDARY_DIAGNOSTIC_STARTED"
        or started.get("worker_sha256") != EXPECTED_ATTEMPT42_WORKER_SHA256
        or started.get("config_sha256") != EXPECTED_ATTEMPT42_CONFIG_SHA256
    ):
        raise RuntimeError("Attempt 43 bound Attempt 42 start identity drifted")
    if (
        failure.get("status") != "NO_SAVE_ATTEMPT42_DIAGNOSTIC_STOP_PRESERVED"
        or not failure.get("diagnostic_exists")
        or failure.get("mesh_mutated")
        or failure.get("body_mutated")
        or failure.get("render_reached")
        or failure.get("blend_saved")
        or failure.get("runtime_changed")
    ):
        raise RuntimeError("Attempt 43 bound Attempt 42 failure truth drifted")
    expected_cache = str(cache_path.resolve())
    expected_cache_row = {
        "path": expected_cache,
        "bytes": 36680,
        "sha256": EXPECTED_CACHE_SHA256,
    }
    if (
        integrity.get("blender_exit_code") != 1
        or integrity.get("native_invocation_error") is not None
        or integrity.get("pre_post_exact") is not True
        or integrity.get("before") != integrity.get("after")
        or len(integrity.get("before", [])) != 291
        or integrity.get("relevant_bytecode_cache_inventory_exact") is not True
        or integrity.get("expected_relevant_bytecode_cache_paths") != [expected_cache]
        or integrity.get("relevant_bytecode_caches_before") != [expected_cache_row]
        or integrity.get("relevant_bytecode_caches_after") != [expected_cache_row]
    ):
        raise RuntimeError("Attempt 43 bound Attempt 42 integrity drifted")
    protected = []
    seen: set[Path] = set()
    for row in integrity["before"]:
        path = Path(str(row["path"])).resolve(strict=True)
        root = ROOT.resolve()
        if root != path and root not in path.parents:
            raise RuntimeError(f"Attempt 43 protected path escapes project: {path}")
        if path in seen:
            raise RuntimeError(f"Attempt 43 duplicate protected path: {path}")
        seen.add(path)
        actual = file_record(path)
        if (
            int(actual["bytes"]) != int(row["bytes"])
            or actual["sha256"] != str(row["sha256"]).lower()
        ):
            raise RuntimeError(f"Attempt 43 protected file drifted: {path}")
        protected.append(actual)
    if len(protected) != 291:
        raise RuntimeError("Attempt 43 did not verify all 291 protected records")
    if cache_path.stat().st_size != 36680 or sha256_file(cache_path) != EXPECTED_CACHE_SHA256:
        raise RuntimeError("Attempt 43 preserved Attempt 40 cache drifted")
    if (
        diagnostic.get("attempt_id") != "attempt_42"
        or len(diagnostic.get("targeted_complete_vertex_star_candidates", [])) != 1
        or diagnostic.get("uniform_face_ring_candidates") != []
        or diagnostic.get("necessary_eligible_candidate_count") != 0
        or diagnostic.get("smallest_necessary_eligible_existing_source_candidate")
        is not None
    ):
        raise RuntimeError("Attempt 43 bound Attempt 42 candidate count drifted")
    candidate = diagnostic["targeted_complete_vertex_star_candidates"][0]
    expected = config["attempt42_runtime_result"]
    base = config["attempt42_base_domain"]
    if (
        candidate.get("candidate") != expected["candidate"]
        or int(candidate["face_count"]) != int(expected["face_count"])
        or candidate["face_indices_sha256"] != expected["face_indices_sha256"]
        or int(candidate["vertex_count"]) != int(expected["vertex_count"])
        or candidate["vertex_indices_sha256"] != expected["vertex_indices_sha256"]
        or int(candidate["edge_count"]) != int(expected["edge_count"])
        or int(candidate["boundary_edge_count"]) != int(expected["boundary_edge_count"])
        or candidate["boundary_edge_indices_sha256"]
        != expected["boundary_edge_indices_sha256"]
        or candidate["boundary_cycle_mesh_vertex_indices"]
        != expected["boundary_cycle_mesh_vertex_indices"]
        or candidate["boundary_cycle_mesh_vertex_indices_sha256"]
        != expected["boundary_cycle_mesh_vertex_indices_sha256"]
        or candidate["eligibility_failures"] != expected["eligibility_failures"]
        or candidate["necessary_candidate_eligibility_passes"]
        or candidate["added_complete_source_mesh_vertex_star_face_indices"]
        != expected["added_complete_source_mesh_vertex_star_face_indices"]
    ):
        raise RuntimeError("Attempt 43 bound Attempt 42 candidate identity drifted")
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
        or len(base["added_complete_existing_source_face_indices"]) != 32
    ):
        raise RuntimeError("Attempt 43 bound Attempt 42 base-domain identity drifted")
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
        or int(attribution["row_count"]) != len(expected["boundary_cycle_mesh_vertex_indices"])
        or len(rows) != int(attribution["row_count"])
        or any(not required_fields.issubset(row) for row in rows)
        or int(attribution["exceeding_row_count"])
        != int(expected["chart_exceeding_row_count"])
        or attribution["maximum_contributor_boundary_indices"]
        != expected["chart_maximum_contributor_boundary_indices"]
        or attribution["maximum_contributor_mesh_vertex_indices"]
        != expected["chart_maximum_contributor_mesh_vertex_indices"]
    ):
        raise RuntimeError("Attempt 43 bound Attempt 42 chart attribution drifted")
    forced = candidate["forced_ear_feasibility"]
    obstructions = forced["obstructions"]
    boundary_index = int(expected["forced_ear_boundary_index"])
    if (
        forced.get("passes")
        or len(obstructions) != 1
        or int(obstructions[0]["boundary_index"]) != boundary_index
        or int(candidate["boundary_cycle_mesh_vertex_indices"][boundary_index])
        != int(expected["forced_ear_mesh_vertex_index"])
        or int(expected["forced_ear_mesh_vertex_index"])
        != int(attribution["maximum_contributor_mesh_vertex_indices"][0])
        or not _float_exact(
            obstructions[0]["fixed_ear_minimum_angle_degrees"],
            expected["forced_ear_minimum_angle_degrees"],
        )
    ):
        raise RuntimeError("Attempt 43 bound shared obstruction identity drifted")
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
            raise RuntimeError(f"Attempt 43 bound Attempt 42 overclaims: {name}")
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
        raise RuntimeError(f"Attempt 43 source replacement drifted: {label}: {count}")
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
        raise RuntimeError(f"Attempt 43 span anchors drifted: {label}")
    start = source.index(start_anchor)
    end = source.index(end_anchor, start)
    old = source[start:end]
    if sha256_text(old) != expected_sha256:
        raise RuntimeError(f"Attempt 43 span hash drifted: {label}: {sha256_text(old)}")
    return source[:start] + replacement + source[end:]


CANDIDATE_MAPPING_REPLACEMENT = '''        targeted = []
        base_contract = ATTEMPT43_RUNTIME_BASE_DOMAIN
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
            raise RuntimeError("Attempt 43 exact complete Attempt 42 base domain drifted")
        base_row = _domain_diagnostic(
            "reverified_complete___PREVIOUS_ATTEMPT___domain",
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
            raise RuntimeError("Attempt 43 reverified Attempt 42 base topology drifted")
        probe = ATTEMPT43_RUNTIME_PROBE
        obstruction_boundary_index = int(
            probe["exact_shared_obstruction_boundary_index_before_expansion"]
        )
        obstruction_vertex_index = int(
            probe["exact_shared_obstruction_mesh_vertex_index"]
        )
        if (
            int(base_row["boundary_cycle_mesh_vertex_indices"][obstruction_boundary_index])
            != obstruction_vertex_index
        ):
            raise RuntimeError("Attempt 43 exact shared obstruction identity drifted")
        complete_star_faces = {
            int(face.index) for face in bm.verts[obstruction_vertex_index].link_faces
        }
        added_faces = complete_star_faces.difference(base_selected)
        if not added_faces:
            raise RuntimeError("Attempt 43 obstruction vertex star adds no source face")
        selected = set(base_selected)
        selected.update(added_faces)
        row = _domain_diagnostic(
            "complete___PREVIOUS_ATTEMPT___domain_plus_complete_mesh_vertex_star_463",
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
        row["exact_shared_obstruction_boundary_index_before_expansion"] = (
            obstruction_boundary_index
        )
        row["exact_shared_obstruction_mesh_vertex_index"] = obstruction_vertex_index
        row["shared_chart_maximum_and_forced_ear_contributor"] = True
        row["complete_source_mesh_vertex_star_face_count"] = len(complete_star_faces)
        row["complete_source_mesh_vertex_star_face_indices"] = sorted(complete_star_faces)
        row["added_complete_source_mesh_vertex_star_face_count"] = len(added_faces)
        row["added_complete_source_mesh_vertex_star_face_indices"] = sorted(added_faces)
        forced_ear = attempt43_forced_ear_feasibility(
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


def derive_attempt43_source(config: Mapping[str, Any], attempt42_source: str) -> str:
    if sha256_text(attempt42_source) != EXPECTED_ATTEMPT42_DERIVED_SHA256:
        raise RuntimeError("Attempt 43 base derived source drifted")
    source = exact_replace(
        attempt42_source,
        EXPECTED_ATTEMPT42_CONFIG_SHA256,
        EXPECTED_CONFIG_SHA256,
        "bind Attempt 43 config hash",
    )
    source = exact_span_replace(
        source,
        "        targeted = []\n",
        "        coordinate_only = ATTEMPT42_BOUND_COORDINATE_ONLY\n",
        EXPECTED_ATTEMPT42_CANDIDATE_BLOCK_SHA256,
        CANDIDATE_MAPPING_REPLACEMENT,
        "replace mapping with exact shared-obstruction star",
    )
    old_provenance = (
        '            "attempt41_runtime_result": ATTEMPT42_RUNTIME_RESULT,\n'
        '            "attempt41_complete_candidate_reverified": base_row,\n'
        '            "one_candidate_probe": ATTEMPT42_RUNTIME_PROBE,\n'
        '            "targeted_complete_vertex_star_candidates": targeted,\n'
    )
    new_provenance = (
        '            "__PREVIOUS_RUNTIME_RESULT__": ATTEMPT43_RUNTIME_RESULT,\n'
        '            "__PREVIOUS_BASE_REVERIFIED__": base_row,\n'
        '            "one_candidate_probe": ATTEMPT43_RUNTIME_PROBE,\n'
        '            "targeted_complete_vertex_star_candidates": targeted,\n'
    )
    source = exact_replace(
        source, old_provenance, new_provenance, "record Attempt 43 provenance"
    )
    source = exact_replace(
        source,
        '                "attempt41_complete_domain_used_only_as_read_only_base": True,\n',
        '                "__PREVIOUS_COMPLETE_DOMAIN_USED_ONLY_AS_READ_ONLY_BASE__": True,\n',
        "bind Attempt 42 base-use truth",
    )
    for old, new in (
        ("attempt_42", "attempt_43"),
        ("attempt42", "attempt43"),
        ("Attempt 42", "Attempt 43"),
        ("ATTEMPT42", "ATTEMPT43"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 43 source identity token disappeared: {old}")
        source = source.replace(old, new)
    source = source.replace("__PREVIOUS_RUNTIME_RESULT__", "attempt42_runtime_result")
    source = source.replace(
        "__PREVIOUS_BASE_REVERIFIED__", "attempt42_complete_candidate_reverified"
    )
    source = source.replace(
        "__PREVIOUS_COMPLETE_DOMAIN_USED_ONLY_AS_READ_ONLY_BASE__",
        "attempt42_complete_domain_used_only_as_read_only_base",
    )
    source = source.replace("__PREVIOUS_ATTEMPT__", "attempt42")
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "attempt43_source_identity_evidence",
        "attempt43_forced_ear_feasibility",
        "run_blender_diagnostic",
        "_domain_diagnostic",
    }
    if not required.issubset(names):
        raise RuntimeError("Attempt 43 derived read-only helpers are absent")
    for stale in ("attempt_42", "ATTEMPT42_"):
        if stale in source:
            raise RuntimeError(f"Attempt 43 derived source retained stale token: {stale}")
    required_tokens = (
        '"boundary_deviation_attribution"',
        '"absolute_deviation_rank"',
        '"exceeds_maximum_allowed_deviation"',
        '"exact_shared_obstruction_mesh_vertex_index"',
        '"attempt42_runtime_result"',
        '"attempt42_complete_candidate_reverified"',
        '"attempt42_complete_domain_used_only_as_read_only_base"',
    )
    if any(token not in source for token in required_tokens):
        raise RuntimeError("Attempt 43 derived attribution or provenance is absent")
    forbidden_calls = (
        "bpy.ops.wm.save",
        "bpy.ops.render",
        "bpy.ops.export",
        "bpy.ops.object.join",
        "bmesh.ops.delete",
        "to_mesh(",
    )
    if any(value in source for value in forbidden_calls):
        raise RuntimeError("Attempt 43 derived source contains a forbidden operation")
    return source


def reconstruct_attempt42_static(attempt42: Any, config: Mapping[str, Any]) -> dict[str, Any]:
    attempt42_config = json.loads(
        project_path(config["bindings"]["attempt42_config"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    verified = attempt42.verify_package(attempt42_config)
    source = verified["derived_source"]
    if sha256_text(source) != EXPECTED_ATTEMPT42_DERIVED_SHA256:
        raise RuntimeError("Attempt 43 exact Attempt 42 derived source drifted")
    return {
        "attempt42_config": attempt42_config,
        "attempt42_verified": verified,
        "attempt42_source": source,
        "attempt42_runtime_config": verified["runtime_config"],
    }


def build_runtime_config(
    config: Mapping[str, Any],
    attempt42_runtime: Mapping[str, Any],
    diagnostic: Mapping[str, Any],
) -> dict[str, Any]:
    runtime = json.loads(json.dumps(attempt42_runtime))
    for key in ("attempt_id", "status", "mode", "scope", "output", "proposal", "truth"):
        runtime[key] = json.loads(json.dumps(config[key]))
    runtime["bindings"].update(json.loads(json.dumps(config["bindings"])))
    runtime["source_mesh_diagnostic"]["targeted_vertex_star_suppression_sets"] = []
    runtime["source_mesh_diagnostic"]["uniform_face_ring_expansions_to_map"] = []
    runtime["source_mesh_diagnostic"]["eligible_candidate_requires"] = list(
        runtime["source_mesh_diagnostic"]["eligible_candidate_requires"]
    ) + [
        "per_boundary_chart_deviation_attribution",
        "exact_complete_attempt42_base_plus_complete_mesh_vertex_star_463",
    ]
    runtime["attempt42_runtime_result"] = json.loads(
        json.dumps(config["attempt42_runtime_result"])
    )
    runtime["attempt42_base_domain"] = json.loads(
        json.dumps(config["attempt42_base_domain"])
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
        raise RuntimeError("Attempt 43 bytecode containment is not active")
    records = {
        str(name): require_record(str(name), record)
        for name, record in config["bindings"].items()
    }
    records["proposal"] = require_record("proposal", config["proposal"])
    if records["attempt42_worker"]["sha256"] != EXPECTED_ATTEMPT42_WORKER_SHA256:
        raise RuntimeError("Attempt 43 bound Attempt 42 worker disagrees")
    if records["attempt42_config"]["sha256"] != EXPECTED_ATTEMPT42_CONFIG_SHA256:
        raise RuntimeError("Attempt 43 bound Attempt 42 config disagrees")
    evidence = verify_attempt42_runtime(config, records)
    attempt42 = load_static_module("attempt43_bound_attempt42", ATTEMPT42_WORKER)
    context = reconstruct_attempt42_static(attempt42, config)
    runtime = build_runtime_config(
        config,
        context["attempt42_runtime_config"],
        evidence["diagnostic"],
    )
    source = derive_attempt43_source(config, context["attempt42_source"])
    namespace = {
        "__name__": "attempt43_static_runtime_contract",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
    }
    exec(
        compile(source, str(Path(__file__).resolve()) + "::derived-contract", "exec"),
        namespace,
        namespace,
    )
    namespace["validate_config"](runtime)
    return {
        "records": records,
        "attempt42_evidence": evidence,
        "attempt42": attempt42,
        "attempt42_context": context,
        "runtime_config": runtime,
        "derived_source": source,
        "derived_source_sha256": sha256_text(source),
    }


def run_blender(config_path: Path, config: Mapping[str, Any]) -> None:
    if sys.dont_write_bytecode is not True:
        raise RuntimeError("Attempt 43 Blender bytecode containment is not active")
    verified = verify_package(config)
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "ATTEMPT43_RUNTIME_CONFIG": verified["runtime_config"],
        "ATTEMPT43_RUNTIME_RESULT": json.loads(
            json.dumps(config["attempt42_runtime_result"])
        ),
        "ATTEMPT43_RUNTIME_BASE_DOMAIN": json.loads(
            json.dumps(config["attempt42_base_domain"])
        ),
        "ATTEMPT43_RUNTIME_PROBE": json.loads(
            json.dumps(config["one_candidate_probe"])
        ),
        "ATTEMPT43_BOUND_COORDINATE_ONLY": json.loads(
            json.dumps(
                verified["attempt42_evidence"]["diagnostic"]["coordinate_only_analysis"]
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
