"""Attempt 31 bound-candidate no-save reconstruction diagnostic.

Importing this module is Blender-free.  The Blender path is reached only by
the separately reviewed command recorded in the static proposal/checkpoint.
That path mutates only disposable in-memory datablocks, writes append-only JSON
evidence, never renders, and has no Blend save/export/activation path.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import traceback
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260808"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT31_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = "befed78bc1894125a237e377f2ecb844414eb2994f8ec55c8d53f002d8a12298"
EXPECTED_ATTEMPT30_CONFIG_SHA256 = "f040e298af2158391d9818139f5a861d36d3ef121c91d168adce3a10b499743c"
EXPECTED_ATTEMPT30_WORKER_SHA256 = "204a386b90db731ce6d4d83ceb59afb79ec6ceeb23d3384ea300f0b3e5f6f31b"
EXPECTED_ATTEMPT15_CONFIG_SHA256 = "3cd11424052918914bab6403ae7d62b465c3f8e50d0d88ce59c8904ddb99f561"
EXPECTED_ATTEMPT15_WORKER_SHA256 = "7ea94e0d17a4b646e60df077c1a4312b9e2bf3c57ba8c6c66eb59d30dc8a35f4"
EXPECTED_R20_WORKER_SHA256 = "2b18b3050777f0fe6e414a882e2faa83cc80249ca52d86037a4cfacc78d9329a"
EXPECTED_R20_CONTRACT_SHA256 = "fe5b9f8b68dd7acd9b6eaaaf26d12d65fe0e3e263548e8979bcb26c0e58f640d"
EXPECTED_EXACT_INTERSECTION_SHA256 = "75c9f9633686776b72ec7bd83362521daae3d9f9497106b0491b8f85490c3ad1"
EXPECTED_A09_WORKER_SHA256 = "8fcd1c39b9f375f5a48d0aefd761222fe0e65b2a7efe491e6d28f7e794aa49d7"
EXPECTED_A08_WORKER_SHA256 = "6a75233d53fabebb9afc61e46184d3dbe5718a648317a93f8b2b2792fab7ab1c"
PATCH_VERTEX_TAG = "_KIRA_A31_PATCH_ORIGINAL_VERTEX_ID"
PATCH_FACE_TAG = "_KIRA_A31_PATCH_ORIGINAL_FACE_ID"
BODY_VERTEX_TAG = "_KIRA_A31_BODY_ORIGINAL_VERTEX_ID"
BODY_FACE_TAG = "_KIRA_A31_BODY_ORIGINAL_FACE_ID"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def project_existing_path(value: str) -> Path:
    path = (ROOT / value).resolve(strict=True)
    root = ROOT.resolve()
    if root != path and root not in path.parents:
        raise RuntimeError(f"Attempt 31 binding escapes project: {value}")
    return path


def project_output_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    root = ROOT.resolve()
    if root != path and root not in path.parents:
        raise RuntimeError(f"Attempt 31 output escapes project: {value}")
    return path


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Attempt 31 cannot load bound provider: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 31 requires the exact sealed config path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 31 config hash drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def _eligible_sort_key(row: Mapping[str, Any]) -> tuple[bool, int, str]:
    return (
        row["global_seam_relation"] == "EXACT_COMPLETE_GLOBAL_SEAM_BOUNDARY",
        int(row["face_count"]),
        str(row["candidate"]),
    )


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_31"
        or config.get("status") != "STATIC_DIAGNOSTIC_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 31 identity drifted")
    scope = config["scope"]
    required_true = (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "diagnostic_only",
        "later_reviewed_blender_launch_required",
        "read_bound_source_files_allowed_during_later_run",
        "append_disposable_patch_in_memory_allowed_during_later_run",
        "mutate_only_disposable_appended_patch_in_memory_allowed_during_later_run",
        "in_memory_unpublished_body_graft_allowed_only_after_patch_gates",
        "triangulation_allowed_only_during_later_run",
        "reconstruction_allowed_only_during_later_run",
        "append_only_json_evidence_allowed_during_later_run",
    )
    forbidden = (
        "source_file_mutation_allowed",
        "prior_evidence_mutation_allowed",
        "render_allowed",
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "assignment_allowed",
        "publication_allowed",
        "boundary_or_global_seam_movement_allowed",
        "quality_gate_reduction_allowed",
        "generic_hole_fill_allowed",
        "sanitation_weakening_allowed",
        "automatic_alternate_candidate_retry_allowed",
    )
    if not all(bool(scope[name]) for name in required_true):
        raise RuntimeError("Attempt 31 lost a required bounded diagnostic scope")
    if any(bool(scope[name]) for name in forbidden):
        raise RuntimeError("Attempt 31 permits a forbidden operation")

    hard = config["unchanged_hard_gates"]
    exact_numeric = {
        "minimum_new_triangle_angle_degrees": 12.0,
        "minimum_new_triangle_world_area_m2": 1.0e-10,
        "maximum_new_interior_vertex_count": 160,
        "maximum_quality_refinement_iterations": 192,
        "selected_domain_face_count": 104,
        "selected_domain_vertex_count": 73,
        "selected_domain_edge_count": 176,
        "selected_domain_boundary_edge_count": 40,
        "selected_domain_interior_vertex_count": 33,
        "local_boundary_coordinate_delta_m": 0.0,
        "global_seam_vertex_count": 34,
        "global_seam_coordinate_delta_m": 0.0,
        "global_seam_unique_weld_count": 34,
        "standalone_patch_exact_genuine_intersections": 0,
        "joined_patch_related_exact_genuine_intersections": 0,
        "new_whole_body_exact_genuine_intersections": 0,
        "preserved_inherited_nonpatch_exact_genuine_intersections": 29,
    }
    for name, expected in exact_numeric.items():
        if hard[name] != expected:
            raise RuntimeError(f"Attempt 31 hard gate drifted: {name}")
    required_hard_true = (
        "require_exact_constrained_boundary_as_complete_open_edge_set",
        "require_single_face_component",
        "patch_original_vertex_and_face_id_tags_unique_complete",
        "patch_exact_new_vertex_and_face_counts",
        "patch_outside_exact_float_hex_coordinates_ordered_loops_all_uv_layers_weights_material_smoothing",
        "patch_temporary_id_layers_removed_before_graft",
        "body_nonpatch_original_vertex_and_face_id_tags_unique_complete",
        "body_nonpatch_exact_float_hex_coordinates_ordered_loops_all_uv_layers_weights_material_smoothing",
        "body_exact_new_vertex_and_face_counts",
        "body_temporary_id_layers_removed_before_final_audit",
        "body_transform_parent_modifier_order_full_settings_vertex_group_inventory_shape_keys_animation_material_slot_order_link_datablock_identity_exact",
        "rig_object_armature_settings_bones_pose_constraints_and_animation_exact",
        "global_action_inventory_exact",
        "protected_original_nonbody_nonrig_object_state_and_mesh_coordinate_topology_uv_material_smoothing_exact",
        "source_hashes_unchanged",
    )
    if not all(bool(hard[name]) for name in required_hard_true):
        raise RuntimeError("Attempt 31 removed a hard preservation gate")
    if int(hard["require_disk_euler_characteristic"]) != 1:
        raise RuntimeError("Attempt 31 disk topology gate drifted")
    if bool(hard["save_allowed_without_owner_visual_acceptance"]):
        raise RuntimeError("Attempt 31 incorrectly permits a save")

    preservation = config["preservation_contract"]
    if preservation["temporary_original_id_layers"] != {
        "patch_vertex": PATCH_VERTEX_TAG,
        "patch_face": PATCH_FACE_TAG,
        "body_vertex": BODY_VERTEX_TAG,
        "body_face": BODY_FACE_TAG,
    } or preservation["exact_numeric_representation"] != "python_float_hex_no_rounding":
        raise RuntimeError("Attempt 31 exact preservation contract drifted")
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
        or launch["worker"]
        != "tools/blender_diagnose_kira_r24_blackproject_candidate_attempt31.py"
        or launch["config"]
        != "RecoverySprint/continuation_20260808/R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT31_CONFIG.json"
        or launch["stdout"]
        != "RecoverySprint/continuation_20260808/attempt31_blender_stdout.log"
        or launch["stderr"]
        != "RecoverySprint/continuation_20260808/attempt31_blender_stderr.log"
        or launch["external_integrity"]
        != "RecoverySprint/continuation_20260808/attempt31_external_pre_post_integrity.json"
        or not bool(launch["require_output_and_log_paths_absent_before_launch"])
        or not bool(
            launch["external_pre_and_post_size_sha256_inventory_required_even_on_nonzero_exit"]
        )
        or not bool(launch["refuse_any_overwrite"])
        or bool(launch["executed_during_static_preparation"])
    ):
        raise RuntimeError("Attempt 31 launch contract drifted")

    selected = config["selected_candidate"]
    if (
        selected["candidate"] != "targeted_complete_vertex_stars_2_6_20_28"
        or selected["capture_source_indices"] != [2, 6, 20, 28]
        or selected["source_mesh_vertex_indices"] != [90, 418, 407, 91]
        or len(selected["face_indices"]) != 104
        or canonical_sha256(selected["face_indices"])
        != selected["face_indices_sha256"]
        or len(selected["boundary_cycle_mesh_vertex_indices"]) != 40
        or canonical_sha256(selected["boundary_cycle_mesh_vertex_indices"])
        != selected["boundary_cycle_mesh_vertex_indices_sha256"]
        or float(selected["minimum_boundary_angle_degrees"])
        != 13.24909246109987
        or float(selected["maximum_chart_deviation_m"])
        != 0.0010360884480178356
        or selected["global_seam_relation"] != "DISJOINT"
        or not bool(selected["necessary_candidate_eligibility_passes"])
        or bool(selected["eligibility_is_sufficient_for_reconstruction"])
    ):
        raise RuntimeError("Attempt 31 selected candidate contract drifted")

    selection = config["selection_contract"]
    eligible = selection["eligible_candidates"]
    if (
        int(selection["necessary_eligible_candidate_count"]) != 7
        or len(eligible) != 7
        or eligible != sorted(eligible, key=_eligible_sort_key)
        or eligible[0]["candidate"] != selected["candidate"]
        or bool(selection["necessary_checks_are_sufficient_reconstruction_proof"])
    ):
        raise RuntimeError("Attempt 31 deterministic candidate ordering drifted")

    truth = config["truth"]
    forbidden_truth = (
        "selected_candidate_reconstruction_feasibility_proven",
        "attempt31_blender_execution_performed",
        "attempt31_triangulation_performed",
        "attempt31_reconstruction_performed",
        "attempt31_body_mutation_performed",
        "attempt31_render_reached",
        "attempt31_blend_saved",
        "runtime_changed",
        "body_repair_proven",
        "owner_approval_claimed",
    )
    if any(bool(truth[name]) for name in forbidden_truth):
        raise RuntimeError("Attempt 31 static truth overclaims execution")

    import_contract = config["provider_import_contract"]
    if (
        import_contract.get("all_checks_before")
        != [
            "attempt15_config_read",
            "provider_verify_inputs",
            "output_allocation",
            "source_blend_open",
        ]
        or import_contract.get("callable_aliases")
        != [
            {
                "reference": "provider.exact_nonadjacent_intersection_report",
                "binding": "exact_intersection_helper",
                "status": "INVOKED_BY_ATTEMPT31",
            },
            {
                "reference": "provider.r21.exact_nonadjacent_intersection_report",
                "binding": "exact_intersection_helper",
                "status": "INVOKED_BY_ATTEMPT31",
            },
        ]
        or import_contract.get("module_aliases")
        != [
            {
                "reference": "provider.r21.r20.exact_intersections",
                "binding": "exact_intersection_helper",
                "status": "LOADED_NOT_REACHED_BY_ATTEMPT31",
            },
            {
                "reference": "provider.a09",
                "binding": "a09_midpoint_helper",
                "status": "IMPORTED_NOT_INVOKED",
            },
            {
                "reference": "provider.a09.a08",
                "binding": "a08_direct_subdivision_helper",
                "status": "IMPORTED_NOT_INVOKED",
            },
            {
                "reference": "provider.a09.a08.exact_intersections",
                "binding": "exact_intersection_helper",
                "status": "IMPORTED_NOT_INVOKED",
            },
        ]
        or import_contract.get("callable_owner_rule")
        != "sys.modules[callable.__module__] exists and getattr(module, callable.__name__) is callable"
        or not bool(import_contract.get("every_alias_module_file_path_bytes_sha256_exact"))
    ):
        raise RuntimeError("Attempt 31 provider import contract drifted")
    expected_import_bindings = {
        "attempt15_worker": {
            "path": "tools/blender_simulate_kira_r24_blackproject_local_reconstruction_attempt15.py",
            "bytes": 41328,
            "sha256": EXPECTED_ATTEMPT15_WORKER_SHA256,
        },
        "r21_graft_helper": {
            "path": "tools/blender_author_kira_r21_pelvis_attempt01.py",
            "bytes": 25054,
            "sha256": "88854dd51faf47286e2c7e6f7d0c594583150eca2045121667f25543e692106b",
        },
        "r20_pelvis_helper": {
            "path": "tools/blender_author_kira_r20_pelvis_only.py",
            "bytes": 202035,
            "sha256": EXPECTED_R20_WORKER_SHA256,
        },
        "r20_curvilinear_contract": {
            "path": "Core/kira_r20_curvilinear_pelvic_patch.py",
            "bytes": 56218,
            "sha256": EXPECTED_R20_CONTRACT_SHA256,
        },
        "exact_intersection_helper": {
            "path": "tools/blender_exact_mesh_intersections.py",
            "bytes": 20087,
            "sha256": EXPECTED_EXACT_INTERSECTION_SHA256,
        },
        "a09_midpoint_helper": {
            "path": "tools/blender_simulate_kira_r24_internal_midpoint_fair_surface.py",
            "bytes": 74705,
            "sha256": EXPECTED_A09_WORKER_SHA256,
        },
        "a08_direct_subdivision_helper": {
            "path": "tools/blender_simulate_kira_r24_direct_subdivision_surface.py",
            "bytes": 83198,
            "sha256": EXPECTED_A08_WORKER_SHA256,
        },
    }
    for name, expected in expected_import_bindings.items():
        if config["bindings"].get(name) != expected:
            raise RuntimeError(f"Attempt 31 provider import binding drifted: {name}")


def verify_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    path = project_existing_path(str(record["path"]))
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(record["bytes"]):
        raise RuntimeError(f"Attempt 31 bound byte count drifted: {name}")
    if digest != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 31 bound hash drifted: {name}: {digest}")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": size,
        "sha256": digest,
    }


def _candidate_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate": row["candidate"],
        "face_count": int(row["face_count"]),
        "vertex_count": int(row["vertex_count"]),
        "boundary_edge_count": int(row["boundary_edge_count"]),
        "minimum_boundary_angle_degrees": float(
            row["boundary_angle_analysis"][
                "minimum_boundary_interior_angle_degrees"
            ]
        ),
        "maximum_chart_deviation_m": float(
            row["chart"]["maximum_absolute_boundary_deviation_m"]
        ),
        "global_seam_relation": row["global_seam_relation"],
        "face_indices_sha256": row["face_indices_sha256"],
        "vertex_indices_sha256": row["vertex_indices_sha256"],
        "boundary_edge_indices_sha256": row["boundary_edge_indices_sha256"],
        "boundary_cycle_mesh_vertex_indices_sha256": row[
            "boundary_cycle_mesh_vertex_indices_sha256"
        ],
    }


def verify_candidate_contract(
    config: Mapping[str, Any], diagnostic: Mapping[str, Any]
) -> dict[str, Any]:
    if (
        diagnostic.get("attempt_id") != "attempt_30"
        or diagnostic.get("status")
        != config["selection_contract"]["evidence_status"]
        or int(diagnostic["necessary_eligible_candidate_count"]) != 7
    ):
        raise RuntimeError("Attempt 31 is not bound to the exact Attempt 30 result")
    truth = diagnostic["truth"]
    forbidden = (
        "replacement_boundary_repair_applied",
        "triangulation_performed",
        "mesh_mutated",
        "body_mutated",
        "render_reached",
        "blend_saved",
        "runtime_changed",
        "necessary_candidate_is_sufficient_repair_proof",
    )
    if any(bool(truth[name]) for name in forbidden):
        raise RuntimeError("Attempt 30 evidence overclaims a repair")

    all_rows = list(diagnostic["targeted_complete_vertex_star_candidates"]) + list(
        diagnostic["uniform_face_ring_candidates"]
    )
    eligible_rows = [
        row for row in all_rows if bool(row["necessary_candidate_eligibility_passes"])
    ]
    eligible_rows.sort(key=_eligible_sort_key)
    summaries = [_candidate_summary(row) for row in eligible_rows]
    if summaries != config["selection_contract"]["eligible_candidates"]:
        raise RuntimeError("Attempt 31 seven-candidate manifest drifted")
    selected_row = diagnostic["smallest_necessary_eligible_existing_source_candidate"]
    selected = config["selected_candidate"]
    if _candidate_summary(selected_row) != summaries[0]:
        raise RuntimeError("Attempt 31 selected candidate no longer sorts first")
    exact_fields = (
        "candidate",
        "capture_source_indices",
        "source_mesh_vertex_indices",
        "added_complete_vertex_star_face_indices",
        "face_count",
        "face_indices_sha256",
        "vertex_count",
        "vertex_indices_sha256",
        "edge_count",
        "boundary_edge_count",
        "boundary_edge_indices_sha256",
        "boundary_cycle_mesh_vertex_indices",
        "boundary_cycle_mesh_vertex_indices_sha256",
        "face_component_count",
        "euler_characteristic",
        "simple_projected_boundary",
        "global_seam_relation",
        "necessary_candidate_eligibility_passes",
        "eligibility_is_sufficient_for_reconstruction",
    )
    for name in exact_fields:
        if selected_row[name] != selected[name]:
            raise RuntimeError(f"Attempt 31 selected row drifted: {name}")
    if (
        float(
            selected_row["boundary_angle_analysis"]
            ["minimum_boundary_interior_angle_degrees"]
        )
        != float(selected["minimum_boundary_angle_degrees"])
        or float(selected_row["chart"]["maximum_absolute_boundary_deviation_m"])
        != float(selected["maximum_chart_deviation_m"])
        or float(selected_row["chart"]["rms_absolute_boundary_deviation_m"])
        != float(selected["rms_chart_deviation_m"])
    ):
        raise RuntimeError("Attempt 31 selected chart measurement drifted")

    domain_path = project_existing_path(
        config["bindings"]["repair_domain_diagnostic"]["path"]
    )
    domain = json.loads(domain_path.read_text(encoding="utf-8"))
    base_faces = set(
        int(value)
        for value in domain["smallest_qualified_replacement_domain"]["face_indices"]
    )
    complete = sorted(
        base_faces.union(
            int(value)
            for value in selected["added_complete_vertex_star_face_indices"]
        )
    )
    if complete != selected["face_indices"]:
        raise RuntimeError("Attempt 31 complete 104-face candidate derivation drifted")
    return {
        "eligible_candidate_count": len(summaries),
        "selected_candidate": summaries[0],
        "attempt30_truth": dict(truth),
    }


def verify_bindings(config: Mapping[str, Any]) -> dict[str, Any]:
    records = {
        name: verify_record(name, record)
        for name, record in config["bindings"].items()
    }
    records["proposal"] = verify_record("proposal", config["proposal"])
    package = config["preserved_attempt30_package"]
    package_rows = [records[name] for name in package["binding_names"]]
    if (
        len(package_rows) != int(package["file_count"])
        or sum(int(row["bytes"]) for row in package_rows)
        != int(package["total_bytes"])
    ):
        raise RuntimeError("Attempt 31 preserved Attempt 30 package drifted")
    if records["attempt30_config"]["sha256"] != EXPECTED_ATTEMPT30_CONFIG_SHA256:
        raise RuntimeError("Attempt 31 Attempt 30 config binding disagrees")
    if records["attempt30_worker"]["sha256"] != EXPECTED_ATTEMPT30_WORKER_SHA256:
        raise RuntimeError("Attempt 31 Attempt 30 worker binding disagrees")
    if records["attempt15_config"]["sha256"] != EXPECTED_ATTEMPT15_CONFIG_SHA256:
        raise RuntimeError("Attempt 31 Attempt 15 config binding disagrees")
    if records["attempt15_worker"]["sha256"] != EXPECTED_ATTEMPT15_WORKER_SHA256:
        raise RuntimeError("Attempt 31 Attempt 15 worker binding disagrees")
    if records["r20_pelvis_helper"]["sha256"] != EXPECTED_R20_WORKER_SHA256:
        raise RuntimeError("Attempt 31 R20 transitive helper binding disagrees")
    if records["r20_curvilinear_contract"]["sha256"] != EXPECTED_R20_CONTRACT_SHA256:
        raise RuntimeError("Attempt 31 R20 pure-contract binding disagrees")
    if records["exact_intersection_helper"]["sha256"] != EXPECTED_EXACT_INTERSECTION_SHA256:
        raise RuntimeError("Attempt 31 exact-intersection helper binding disagrees")
    if records["a09_midpoint_helper"]["sha256"] != EXPECTED_A09_WORKER_SHA256:
        raise RuntimeError("Attempt 31 A09 imported helper binding disagrees")
    if records["a08_direct_subdivision_helper"]["sha256"] != EXPECTED_A08_WORKER_SHA256:
        raise RuntimeError("Attempt 31 A08 imported helper binding disagrees")

    attempt30 = _load_module(
        "attempt31_bound_attempt30", project_existing_path(records["attempt30_worker"]["path"])
    )
    nested = attempt30.load_overlay(
        project_existing_path(records["attempt30_config"]["path"])
    )
    nested_records = attempt30.verify_overlay_bindings(nested)
    for key in (
        "nested_preserved_attempt28_package",
        "nested_preserved_attempt29_package",
    ):
        expected = config[key]
        nested_key = key.replace("nested_", "")
        actual = nested[nested_key]
        if (
            int(expected["file_count"]) != int(actual["file_count"])
            or int(expected["total_bytes"]) != int(actual["total_bytes"])
        ):
            raise RuntimeError(f"Attempt 31 {key} contract drifted")

    diagnostic = json.loads(
        project_existing_path(records["attempt30_diagnostic"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    candidate = verify_candidate_contract(config, diagnostic)
    return {
        "records": records,
        "nested_attempt28_attempt29_records": nested_records,
        "candidate_contract": candidate,
    }


def _verify_imported_module_file(module: Any, record: Mapping[str, Any], label: str) -> None:
    imported = Path(module.__file__).resolve(strict=True)
    expected = project_existing_path(str(record["path"]))
    if imported != expected:
        raise RuntimeError(
            f"Attempt 31 imported unexpected {label}: {imported} != {expected}"
        )
    if imported.stat().st_size != int(record["bytes"]):
        raise RuntimeError(f"Attempt 31 imported {label} byte count drifted")
    if sha256_file(imported) != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 31 imported {label} hash drifted")


def _module_for_callable(function: Any, label: str) -> Any:
    if not callable(function):
        raise RuntimeError(f"Attempt 31 {label} is not callable")
    module_name = getattr(function, "__module__", None)
    function_name = getattr(function, "__name__", None)
    if not isinstance(module_name, str) or not module_name:
        raise RuntimeError(f"Attempt 31 {label} has no exact module name")
    if not isinstance(function_name, str) or not function_name:
        raise RuntimeError(f"Attempt 31 {label} has no exact callable name")
    module = sys.modules.get(module_name)
    if module is None:
        raise RuntimeError(
            f"Attempt 31 {label} callable module is absent: {module_name}"
        )
    if getattr(module, function_name, None) is not function:
        raise RuntimeError(
            f"Attempt 31 {label} callable is not owned by its declared module"
        )
    return module


def _verify_callable_provider_file(
    function: Any, record: Mapping[str, Any], label: str
) -> None:
    module = _module_for_callable(function, label)
    _verify_imported_module_file(module, record, f"{label} callable provider")


def _exclusive_write_once(path: Path, value: Mapping[str, Any]) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    # Exclusive creation is the no-overwrite guarantee. A temporary+replace
    # sequence is deliberately avoided because Path.replace can overwrite a
    # concurrently created append-only evidence target.
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
        stream.flush()


def _cycle_rotations(values: Sequence[int]) -> Iterable[list[int]]:
    sequence = list(values)
    for oriented in (sequence, list(reversed(sequence))):
        for index in range(len(oriented)):
            yield oriented[index:] + oriented[:index]


def _face_components(faces: Sequence[Sequence[int]]) -> int:
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for face_index, face in enumerate(faces):
        for index, first in enumerate(face):
            second = face[(index + 1) % len(face)]
            edge_faces.setdefault(tuple(sorted((int(first), int(second)))), []).append(
                face_index
            )
    remaining = set(range(len(faces)))
    components = 0
    while remaining:
        components += 1
        stack = [remaining.pop()]
        while stack:
            current = stack.pop()
            face = faces[current]
            for index, first in enumerate(face):
                second = face[(index + 1) % len(face)]
                for other in edge_faces[tuple(sorted((int(first), int(second))))]:
                    if other in remaining:
                        remaining.remove(other)
                        stack.append(other)
    return components


def _cdt_topology(cdt: Mapping[str, Any], boundary_count: int) -> dict[str, Any]:
    faces = [[int(value) for value in face] for face in cdt["faces"]]
    if not faces or any(len(face) != 3 for face in faces):
        raise RuntimeError("Attempt 31 CDT is not a nonempty triangle set")
    edge_counts: Counter[tuple[int, int]] = Counter()
    for face in faces:
        for index, first in enumerate(face):
            edge_counts[tuple(sorted((first, face[(index + 1) % 3])))] += 1
    open_edges = {edge for edge, count in edge_counts.items() if count == 1}
    boundary_output = {
        int(source): int(output)
        for source, output in cdt["boundary_output"].items()
    }
    expected_open = {
        tuple(
            sorted(
                (
                    boundary_output[index],
                    boundary_output[(index + 1) % boundary_count],
                )
            )
        )
        for index in range(boundary_count)
    }
    used_vertices = {value for face in faces for value in face}
    euler = len(used_vertices) - len(edge_counts) + len(faces)
    components = _face_components(faces)
    return {
        "vertex_count": len(used_vertices),
        "edge_count": len(edge_counts),
        "face_count": len(faces),
        "boundary_edge_count": len(open_edges),
        "boundary_is_exact_complete_constrained_edge_set": open_edges
        == expected_open,
        "face_component_count": components,
        "euler_characteristic": euler,
        "all_edges_have_one_or_two_faces": all(
            count in {1, 2} for count in edge_counts.values()
        ),
    }


def _vector_key(vector: Any) -> tuple[str, str, str]:
    return tuple(float(value).hex() for value in vector)  # type: ignore[return-value]


def _edge_coordinate_key(first: Any, second: Any) -> tuple[Any, Any]:
    return tuple(sorted((_vector_key(first.co), _vector_key(second.co))))  # type: ignore[return-value]


def _id_identity(value: Any) -> Any:
    if value is None:
        return None
    library = getattr(value, "library", None)
    return {
        "pointer": int(value.as_pointer()),
        "name": str(getattr(value, "name_full", getattr(value, "name", ""))),
        "library": None if library is None else str(library.filepath),
    }


def _exact_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return {"float_hex": value.hex()}
    if hasattr(value, "as_pointer") and hasattr(value, "bl_rna"):
        return _id_identity(value)
    if isinstance(value, Mapping):
        return {
            str(key): _exact_value(item)
            for key, item in sorted(value.items(), key=lambda row: str(row[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_exact_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        rows = [_exact_value(item) for item in value]
        return sorted(
            rows,
            key=lambda item: json.dumps(
                item, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ),
        )
    try:
        return [_exact_value(item) for item in value]
    except TypeError:
        return str(value)


def _rna_properties(value: Any, excluded: set[str] | None = None) -> dict[str, Any]:
    excluded = set(excluded or ()) | {"rna_type"}
    result = {}
    for prop in value.bl_rna.properties:
        name = str(prop.identifier)
        if name in excluded:
            continue
        try:
            result[name] = _exact_value(getattr(value, name))
        except Exception as exc:
            raise RuntimeError(
                f"Attempt 31 cannot snapshot RNA property {type(value).__name__}.{name}: {exc}"
            ) from exc
    try:
        custom_keys = sorted(str(key) for key in value.keys())
    except (AttributeError, TypeError):
        custom_keys = []
    result["__id_properties__"] = {
        key: _exact_value(value[key]) for key in custom_keys
    }
    return result


def _fcurve_snapshot(curve: Any) -> dict[str, Any]:
    driver = getattr(curve, "driver", None)
    return {
        "all_rna_properties": _rna_properties(
            curve,
            {
                "group",
                "keyframe_points",
                "sampled_points",
                "modifiers",
                "driver",
            },
        ),
        "data_path": str(curve.data_path),
        "array_index": int(curve.array_index),
        "extrapolation": str(curve.extrapolation),
        "mute": bool(curve.mute),
        "lock": bool(curve.lock),
        "group": None if curve.group is None else str(curve.group.name),
        "keyframes": [
            {
                "co": [float(point.co.x).hex(), float(point.co.y).hex()],
                "handle_left": [
                    float(point.handle_left.x).hex(),
                    float(point.handle_left.y).hex(),
                ],
                "handle_right": [
                    float(point.handle_right.x).hex(),
                    float(point.handle_right.y).hex(),
                ],
                "handle_left_type": str(point.handle_left_type),
                "handle_right_type": str(point.handle_right_type),
                "interpolation": str(point.interpolation),
            }
            for point in curve.keyframe_points
        ],
        "sampled_points": [
            [float(point.co.x).hex(), float(point.co.y).hex()]
            for point in curve.sampled_points
        ],
        "modifiers": [
            {
                "index": index,
                "type": str(modifier.type),
                "all_rna_properties": _rna_properties(modifier),
            }
            for index, modifier in enumerate(curve.modifiers)
        ],
        "driver": None
        if driver is None
        else _rna_properties(driver, {"variables"})
        | {
            "variables": [
                _rna_properties(variable, {"targets"})
                | {
                    "targets": [
                        _rna_properties(target, {"id"})
                        | {"id": _id_identity(getattr(target, "id", None))}
                        for target in variable.targets
                    ]
                }
                for variable in driver.variables
            ]
        },
    }


def _animation_snapshot(value: Any) -> Any:
    animation = getattr(value, "animation_data", None)
    if animation is None:
        return None
    return {
        "action": _id_identity(animation.action),
        "action_slot": _id_identity(getattr(animation, "action_slot", None)),
        "action_blend_type": str(animation.action_blend_type),
        "action_extrapolation": str(animation.action_extrapolation),
        "action_influence": float(animation.action_influence).hex(),
        "use_nla": bool(animation.use_nla),
        "drivers": sorted(
            (_fcurve_snapshot(curve) for curve in animation.drivers),
            key=lambda row: (row["data_path"], row["array_index"]),
        ),
        "nla_tracks": [
            {
                "name": str(track.name),
                "mute": bool(track.mute),
                "is_solo": bool(track.is_solo),
                "lock": bool(track.lock),
                "strips": [
                    _rna_properties(strip, {"action", "fcurves", "modifiers"})
                    | {
                        "action": _id_identity(getattr(strip, "action", None)),
                        "fcurves": [
                            _fcurve_snapshot(curve)
                            for curve in getattr(strip, "fcurves", ())
                        ],
                        "modifiers": [
                            _rna_properties(modifier)
                            for modifier in getattr(strip, "modifiers", ())
                        ],
                    }
                    for strip in track.strips
                ],
            }
            for track in animation.nla_tracks
        ],
    }


def _action_inventory() -> list[dict[str, Any]]:
    import bpy  # type: ignore

    rows = []
    for action in sorted(bpy.data.actions, key=lambda item: item.name_full):
        rows.append(
            {
                "identity": _id_identity(action),
                "all_rna_properties": _rna_properties(
                    action,
                    {
                        "fcurves",
                        "groups",
                        "pose_markers",
                        "slots",
                        "layers",
                    },
                ),
                "use_fake_user": bool(action.use_fake_user),
                "frame_range": [float(value).hex() for value in action.frame_range],
                "fcurves": sorted(
                    (_fcurve_snapshot(curve) for curve in getattr(action, "fcurves", ())),
                    key=lambda row: (row["data_path"], row["array_index"]),
                ),
                "groups": [
                    _rna_properties(group, {"channels"})
                    | {
                        "channels": sorted(
                            (
                                (str(curve.data_path), int(curve.array_index))
                                for curve in group.channels
                            )
                        )
                    }
                    for group in getattr(action, "groups", ())
                ],
                "pose_markers": [
                    _rna_properties(marker)
                    for marker in getattr(action, "pose_markers", ())
                ],
                "slots": [
                    _rna_properties(slot) for slot in getattr(action, "slots", ())
                ],
                "layers": [
                    _rna_properties(layer, {"strips"})
                    | {
                        "strips": [
                            _rna_properties(strip, {"channelbags"})
                            | {
                                "channelbags": [
                                    _rna_properties(channelbag, {"fcurves", "groups"})
                                    | {
                                        "fcurves": sorted(
                                            (
                                                _fcurve_snapshot(curve)
                                                for curve in getattr(
                                                    channelbag, "fcurves", ()
                                                )
                                            ),
                                            key=lambda row: (
                                                row["data_path"],
                                                row["array_index"],
                                            ),
                                        ),
                                        "groups": [
                                            _rna_properties(group, {"channels"})
                                            for group in getattr(
                                                channelbag, "groups", ()
                                            )
                                        ],
                                    }
                                    for channelbag in getattr(
                                        strip, "channelbags", ()
                                    )
                                ]
                            }
                            for strip in getattr(layer, "strips", ())
                        ]
                    }
                    for layer in getattr(action, "layers", ())
                ],
            }
        )
    return rows


def _shape_key_snapshot(obj: Any) -> Any:
    keys = getattr(obj.data, "shape_keys", None)
    if keys is None:
        return None
    return {
        "identity": _id_identity(keys),
        "use_relative": bool(keys.use_relative),
        "eval_time": float(keys.eval_time).hex(),
        "reference_key": None
        if keys.reference_key is None
        else str(keys.reference_key.name),
        "animation": _animation_snapshot(keys),
        "key_blocks": [
            {
                "name": str(block.name),
                "all_rna_properties": _rna_properties(
                    block, {"data", "relative_key", "frame"}
                ),
                "relative_key": None
                if block.relative_key is None
                else str(block.relative_key.name),
                "frame": float(block.frame).hex(),
                "value": float(block.value).hex(),
                "slider_min": float(block.slider_min).hex(),
                "slider_max": float(block.slider_max).hex(),
                "mute": bool(block.mute),
                "vertex_group": str(block.vertex_group),
                "interpolation": str(block.interpolation),
                "coordinates": [_vector_key(point.co) for point in block.data],
            }
            for block in keys.key_blocks
        ],
    }


def _material_slots_snapshot(obj: Any) -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "link": str(slot.link),
            "material": _id_identity(slot.material),
        }
        for index, slot in enumerate(obj.material_slots)
    ]


def _modifier_snapshot(obj: Any) -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "identity_pointer": int(modifier.as_pointer()),
            "name": str(modifier.name),
            "type": str(modifier.type),
            "all_rna_properties": _rna_properties(modifier),
        }
        for index, modifier in enumerate(obj.modifiers)
    ]


def _object_contract_snapshot(obj: Any) -> dict[str, Any]:
    return {
        "object_identity": _id_identity(obj),
        "data_identity": _id_identity(obj.data),
        "parent": _id_identity(obj.parent),
        "parent_type": str(obj.parent_type),
        "parent_bone": str(obj.parent_bone),
        "matrix_world": [[float(value).hex() for value in row] for row in obj.matrix_world],
        "matrix_parent_inverse": [
            [float(value).hex() for value in row] for row in obj.matrix_parent_inverse
        ],
        "matrix_basis": [[float(value).hex() for value in row] for row in obj.matrix_basis],
        "rotation_mode": str(obj.rotation_mode),
        "location": _vector_key(obj.location),
        "rotation_euler": _vector_key(obj.rotation_euler),
        "rotation_quaternion": tuple(float(value).hex() for value in obj.rotation_quaternion),
        "scale": _vector_key(obj.scale),
        "delta_location": _vector_key(obj.delta_location),
        "delta_rotation_euler": _vector_key(obj.delta_rotation_euler),
        "delta_scale": _vector_key(obj.delta_scale),
        "vertex_groups": [
            {
                "index": int(group.index),
                "name": str(group.name),
                "lock_weight": bool(group.lock_weight),
            }
            for group in obj.vertex_groups
        ],
        "modifiers": _modifier_snapshot(obj),
        "material_slots": _material_slots_snapshot(obj),
        "mesh_uv_layer_contract": None
        if obj.type != "MESH"
        else {
            "active_index": int(obj.data.uv_layers.active_index),
            "layers": [
                {
                    "index": index,
                    "name": str(layer.name),
                    "active": bool(getattr(layer, "active", False)),
                    "active_clone": bool(getattr(layer, "active_clone", False)),
                    "active_render": bool(getattr(layer, "active_render", False)),
                }
                for index, layer in enumerate(obj.data.uv_layers)
            ],
        },
        "shape_keys": _shape_key_snapshot(obj),
        "animation": _animation_snapshot(obj),
    }


def _rig_contract_snapshot(rig: Any) -> dict[str, Any]:
    armature = rig.data
    return {
        "object": _object_contract_snapshot(rig),
        "armature_identity": _id_identity(armature),
        "armature_settings": _rna_properties(
            armature, {"bones", "edit_bones", "collections"}
        ),
        "bone_collections": [
            _rna_properties(collection, {"bones"})
            | {"bones": [str(bone.name) for bone in collection.bones]}
            for collection in getattr(armature, "collections", ())
        ],
        "bones": [
            {
                "name": str(bone.name),
                "parent": None if bone.parent is None else str(bone.parent.name),
                "settings": _rna_properties(
                    bone,
                    {
                        "parent",
                        "children",
                        "children_recursive",
                        "collections",
                        "matrix",
                        "matrix_local",
                        "head",
                        "head_local",
                        "tail",
                        "tail_local",
                    },
                ),
                "matrix_local": [
                    [float(value).hex() for value in row] for row in bone.matrix_local
                ],
                "head_local": _vector_key(bone.head_local),
                "tail_local": _vector_key(bone.tail_local),
            }
            for bone in armature.bones
        ],
        "pose_bones": [
            {
                "name": str(bone.name),
                "parent": None if bone.parent is None else str(bone.parent.name),
                "settings": _rna_properties(
                    bone,
                    {
                        "bone",
                        "parent",
                        "children",
                        "children_recursive",
                        "constraints",
                        "matrix",
                        "matrix_basis",
                        "matrix_channel",
                        "head",
                        "tail",
                    },
                ),
                "location": _vector_key(bone.location),
                "rotation_mode": str(bone.rotation_mode),
                "rotation_euler": _vector_key(bone.rotation_euler),
                "rotation_quaternion": tuple(
                    float(value).hex() for value in bone.rotation_quaternion
                ),
                "scale": _vector_key(bone.scale),
                "matrix_basis": [
                    [float(value).hex() for value in row] for row in bone.matrix_basis
                ],
                "constraints": [
                    {
                        "index": index,
                        "name": str(constraint.name),
                        "type": str(constraint.type),
                        "all_rna_properties": _rna_properties(constraint),
                    }
                    for index, constraint in enumerate(bone.constraints)
                ],
            }
            for bone in rig.pose.bones
        ],
        "animation": _animation_snapshot(rig),
    }


def _mesh_data_digest(obj: Any) -> str:
    mesh = obj.data
    rows = {
        "identity": _id_identity(mesh),
        "vertices": [_vector_key(vertex.co) for vertex in mesh.vertices],
        "edges": [list(map(int, edge.vertices)) for edge in mesh.edges],
        "polygons": [
            {
                "vertices": list(map(int, polygon.vertices)),
                "material_index": int(polygon.material_index),
                "use_smooth": bool(polygon.use_smooth),
            }
            for polygon in mesh.polygons
        ],
        "uv_layers": {
            layer.name: [
                [float(entry.uv.x).hex(), float(entry.uv.y).hex()]
                for entry in layer.data
            ]
            for layer in mesh.uv_layers
        },
        "materials": [_id_identity(material) for material in mesh.materials],
    }
    return canonical_sha256(rows)


def _protected_object_snapshot(body: Any, rig: Any) -> dict[str, Any]:
    import bpy  # type: ignore

    rows = {}
    objects = sorted(
        (obj for obj in bpy.data.objects if obj not in {body, rig}),
        key=lambda obj: obj.name_full,
    )
    for obj in objects:
        row = {
            "contract": _object_contract_snapshot(obj),
            "mesh_data_sha256": None,
        }
        if obj.type == "MESH":
            row["mesh_data_sha256"] = _mesh_data_digest(obj)
        rows[obj.name_full] = row
    return rows


def _tagged_records(
    bm: Any,
    vertex_layer: Any,
    face_layer: Any,
    expected_vertex_tags: set[int],
    expected_face_tags: set[int],
) -> dict[str, Any]:
    uv_names = [str(name) for name in bm.loops.layers.uv.keys()]
    uv_layers = {name: bm.loops.layers.uv.get(name) for name in uv_names}
    active_uv = bm.loops.layers.uv.active
    deform = bm.verts.layers.deform.active
    vertices = {}
    for vertex in bm.verts:
        tag = int(vertex[vertex_layer])
        if tag not in expected_vertex_tags:
            continue
        if tag in vertices:
            raise RuntimeError(f"Attempt 31 duplicate original vertex tag: {tag}")
        weights = []
        if deform is not None:
            weights = sorted(
                [int(group), float(weight).hex()]
                for group, weight in vertex[deform].items()
            )
        vertices[tag] = {
            "coordinate": _vector_key(vertex.co),
            "select": bool(vertex.select),
            "hide": bool(vertex.hide),
            "weights": weights,
        }
    faces = {}
    for face in bm.faces:
        tag = int(face[face_layer])
        if tag not in expected_face_tags:
            continue
        if tag in faces:
            raise RuntimeError(f"Attempt 31 duplicate original face tag: {tag}")
        loops = []
        for loop in face.loops:
            uv = {}
            for name, layer in uv_layers.items():
                value = loop[layer]
                uv[name] = {
                    "coordinate": [
                        float(value.uv.x).hex(),
                        float(value.uv.y).hex(),
                    ],
                    "select": bool(getattr(value, "select", False)),
                    "select_edge": bool(getattr(value, "select_edge", False)),
                    "pin_uv": bool(getattr(value, "pin_uv", False)),
                }
            loops.append(
                {
                    "original_vertex_tag": int(loop.vert[vertex_layer]),
                    "coordinate": _vector_key(loop.vert.co),
                    "uv": uv,
                }
            )
        faces[tag] = {
            "ordered_loops": loops,
            "material_index": int(face.material_index),
            "smooth": bool(face.smooth),
            "select": bool(face.select),
            "hide": bool(face.hide),
        }
    if set(vertices) != expected_vertex_tags or set(faces) != expected_face_tags:
        raise RuntimeError("Attempt 31 missing original vertex or face tags")
    value = {
        "uv_layer_names": uv_names,
        "active_uv_layer_name": None
        if active_uv is None
        else str(getattr(active_uv, "name", "")),
        "vertices": vertices,
        "faces": faces,
    }
    return {
        "value": value,
        "sha256": canonical_sha256(value),
    }


def _begin_tagged_preservation(
    bm: Any,
    removed_vertex_ids: set[int],
    removed_face_ids: set[int],
    vertex_tag_name: str,
    face_tag_name: str,
) -> dict[str, Any]:
    if bm.verts.layers.int.get(vertex_tag_name) is not None:
        raise RuntimeError(f"Attempt 31 temporary vertex tag already exists: {vertex_tag_name}")
    if bm.faces.layers.int.get(face_tag_name) is not None:
        raise RuntimeError(f"Attempt 31 temporary face tag already exists: {face_tag_name}")
    vertex_layer = bm.verts.layers.int.new(vertex_tag_name)
    face_layer = bm.faces.layers.int.new(face_tag_name)
    for vertex in bm.verts:
        vertex[vertex_layer] = int(vertex.index) + 1
    for face in bm.faces:
        face[face_layer] = int(face.index) + 1
    expected_vertex_tags = {
        int(vertex.index) + 1
        for vertex in bm.verts
        if int(vertex.index) not in removed_vertex_ids
    }
    expected_face_tags = {
        int(face.index) + 1
        for face in bm.faces
        if int(face.index) not in removed_face_ids
    }
    records = _tagged_records(
        bm, vertex_layer, face_layer, expected_vertex_tags, expected_face_tags
    )
    return {
        "vertex_tag_name": vertex_tag_name,
        "face_tag_name": face_tag_name,
        "original_vertex_count": len(bm.verts),
        "original_face_count": len(bm.faces),
        "removed_original_vertex_tags": sorted(value + 1 for value in removed_vertex_ids),
        "removed_original_face_tags": sorted(value + 1 for value in removed_face_ids),
        "expected_vertex_tags": sorted(expected_vertex_tags),
        "expected_face_tags": sorted(expected_face_tags),
        "records": records,
    }


def _finish_tagged_preservation(
    obj: Any,
    before: Mapping[str, Any],
    expected_new_vertex_count: int,
    expected_new_face_count: int,
    required_vertex_keys: Sequence[Any] = (),
    required_edge_keys: Sequence[Any] = (),
) -> dict[str, Any]:
    import bmesh  # type: ignore

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    vertex_layer = bm.verts.layers.int.get(before["vertex_tag_name"])
    face_layer = bm.faces.layers.int.get(before["face_tag_name"])
    if vertex_layer is None or face_layer is None:
        bm.free()
        raise RuntimeError("Attempt 31 temporary original-ID layer disappeared")
    expected_vertex_tags = set(int(value) for value in before["expected_vertex_tags"])
    expected_face_tags = set(int(value) for value in before["expected_face_tags"])
    positive_vertex_tags = [
        int(vertex[vertex_layer]) for vertex in bm.verts if int(vertex[vertex_layer]) > 0
    ]
    positive_face_tags = [
        int(face[face_layer]) for face in bm.faces if int(face[face_layer]) > 0
    ]
    new_vertex_count = sum(int(vertex[vertex_layer]) == 0 for vertex in bm.verts)
    new_face_count = sum(int(face[face_layer]) == 0 for face in bm.faces)
    no_duplicate_or_missing_tags = (
        len(positive_vertex_tags) == len(set(positive_vertex_tags))
        and len(positive_face_tags) == len(set(positive_face_tags))
        and set(positive_vertex_tags) == expected_vertex_tags
        and set(positive_face_tags) == expected_face_tags
    )
    after = _tagged_records(
        bm, vertex_layer, face_layer, expected_vertex_tags, expected_face_tags
    )
    vertex_keys = {_vector_key(vertex.co) for vertex in bm.verts}
    edge_keys = {
        _edge_coordinate_key(edge.verts[0], edge.verts[1]) for edge in bm.edges
    }
    required_vertices_exact = all(tuple(value) in vertex_keys for value in required_vertex_keys)
    required_edges_exact = all(
        tuple(tuple(part) for part in value) in edge_keys for value in required_edge_keys
    )
    records_exact = after == before["records"]
    counts_exact = (
        new_vertex_count == int(expected_new_vertex_count)
        and new_face_count == int(expected_new_face_count)
    )
    bm.verts.layers.int.remove(vertex_layer)
    bm.faces.layers.int.remove(face_layer)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update(calc_edges=True)
    tags_removed = (
        obj.data.attributes.get(before["vertex_tag_name"]) is None
        and obj.data.attributes.get(before["face_tag_name"]) is None
    )
    return {
        "records_before_sha256": before["records"]["sha256"],
        "records_after_sha256": after["sha256"],
        "expected_surviving_original_vertex_count": len(expected_vertex_tags),
        "expected_surviving_original_face_count": len(expected_face_tags),
        "actual_new_vertex_count": new_vertex_count,
        "actual_new_face_count": new_face_count,
        "no_duplicate_or_missing_old_vertex_or_face_tags": no_duplicate_or_missing_tags,
        "all_exact_float_hex_coordinates_ordered_loops_all_uv_layers_weights_material_smoothing_preserved": records_exact,
        "exact_new_vertex_and_face_counts": counts_exact,
        "required_boundary_vertices_exact": required_vertices_exact,
        "required_boundary_edges_exact": required_edges_exact,
        "temporary_original_id_layers_removed_before_graft_or_finish": tags_removed,
        "passes": no_duplicate_or_missing_tags
        and records_exact
        and counts_exact
        and required_vertices_exact
        and required_edges_exact
        and tags_removed,
    }


def _tag_body_for_preservation(obj: Any, mask: Mapping[str, Any]) -> dict[str, Any]:
    import bmesh  # type: ignore

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.faces.index_update()
    result = _begin_tagged_preservation(
        bm,
        {int(value) for value in mask["removable_vertices"]},
        {int(value) for value in mask["faces"]},
        BODY_VERTEX_TAG,
        BODY_FACE_TAG,
    )
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update(calc_edges=True)
    return result


def _exact_face_key(obj: Any, face_index: int) -> list[Any]:
    face = obj.data.polygons[int(face_index)]
    coordinates = [_vector_key(obj.data.vertices[int(index)].co) for index in face.vertices]
    forward = [coordinates[index:] + coordinates[:index] for index in range(len(coordinates))]
    reverse = list(reversed(coordinates))
    forward.extend(reverse[index:] + reverse[:index] for index in range(len(reverse)))
    return min(forward)


def _exact_inherited_pair_signature(
    body: Any, report: Mapping[str, Any], patch_faces: set[int]
) -> str:
    rows = []
    for record in report["pairs"]:
        if not bool(record["genuine_positive_area_or_segment_penetration"]):
            continue
        first, second = map(int, record["face_indices"])
        if first in patch_faces or second in patch_faces:
            continue
        rows.append(sorted((_exact_face_key(body, first), _exact_face_key(body, second))))
    return canonical_sha256(sorted(rows))


def run_blender_diagnostic(config: Mapping[str, Any], verified: Mapping[str, Any]) -> None:
    # These imports are intentionally unreachable during static validation.
    import bmesh  # type: ignore
    import bpy  # type: ignore

    attempt15_config_path = project_existing_path(
        config["bindings"]["attempt15_config"]["path"]
    )
    attempt15_worker_path = project_existing_path(
        config["bindings"]["attempt15_worker"]["path"]
    )
    provider = _load_module("attempt31_bound_attempt15", attempt15_worker_path)
    records = verified["records"]
    _verify_imported_module_file(
        provider, records["attempt15_worker"], "Attempt 15 reconstruction provider"
    )
    _verify_imported_module_file(
        provider.r21, records["r21_graft_helper"], "R21 graft helper"
    )
    _verify_imported_module_file(
        provider.r21.r20, records["r20_pelvis_helper"], "R20 pelvic helper"
    )
    _verify_imported_module_file(
        provider.r21.r20.patch_contract,
        records["r20_curvilinear_contract"],
        "R20 curvilinear pure contract",
    )
    _verify_callable_provider_file(
        provider.exact_nonadjacent_intersection_report,
        records["exact_intersection_helper"],
        "Attempt 15 exact-intersection callable",
    )
    _verify_callable_provider_file(
        provider.r21.exact_nonadjacent_intersection_report,
        records["exact_intersection_helper"],
        "R21 exact-intersection callable",
    )
    _verify_imported_module_file(
        provider.r21.r20.exact_intersections,
        records["exact_intersection_helper"],
        "R20 exact-intersection alias (LOADED_NOT_REACHED_BY_ATTEMPT31)",
    )
    _verify_imported_module_file(
        provider.a09,
        records["a09_midpoint_helper"],
        "A09 midpoint helper (IMPORTED_NOT_INVOKED)",
    )
    _verify_imported_module_file(
        provider.a09.a08,
        records["a08_direct_subdivision_helper"],
        "A08 direct-subdivision helper (IMPORTED_NOT_INVOKED)",
    )
    _verify_imported_module_file(
        provider.a09.a08.exact_intersections,
        records["exact_intersection_helper"],
        "A08 exact-intersection alias (IMPORTED_NOT_INVOKED)",
    )
    attempt15_config = json.loads(attempt15_config_path.read_text(encoding="utf-8"))
    direct_pairs = (
        ("sealed_r24_source_blend", "sealed_r24_source_blend"),
        ("preserved_patch_blend", "preserved_patch_attempt02_blend"),
        ("repair_domain_diagnostic", "repair_domain_diagnostic"),
        ("exact_intersection_helper", "exact_intersection_helper"),
        ("r21_graft_helper", "r21_graft_helper"),
    )
    for current_name, provider_name in direct_pairs:
        if (
            records[current_name]["path"]
            != attempt15_config["inputs"][provider_name]["path"]
            or records[current_name]["sha256"]
            != attempt15_config["inputs"][provider_name]["sha256"]
        ):
            raise RuntimeError(f"Attempt 31 provider input disagrees: {current_name}")
    provider_verified = provider.verify_inputs(attempt15_config)

    output = project_output_path(config["output"]["root"])
    if output.exists():
        raise RuntimeError("append-only Attempt 31 output already exists")
    output.mkdir(parents=True)
    started = {
        "schema": "kira.avatar.r24.blackproject_attempt31.started.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "NO_SAVE_BOUND_CANDIDATE_DIAGNOSTIC_STARTED",
        "worker": str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"),
        "worker_sha256": sha256_file(Path(__file__).resolve()),
        "config": str(DEFAULT_CONFIG.relative_to(ROOT)).replace("\\", "/"),
        "config_sha256": sha256_file(DEFAULT_CONFIG),
        "render_permitted": False,
        "blend_save_permitted": False,
    }
    _exclusive_write_once(output / config["output"]["started"], started)

    provider_capture = provider.capture_local_domain
    provider_quality = provider.quality_refined_cdt
    captured: dict[str, Any] = {}
    try:
        source = project_existing_path(
            config["bindings"]["sealed_r24_source_blend"]["path"]
        )
        patch_blend = project_existing_path(
            config["bindings"]["preserved_patch_blend"]["path"]
        )
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
        body = bpy.data.objects.get(config["objects"]["body"])
        rig = bpy.data.objects.get(config["objects"]["rig"])
        if body is None or body.type != "MESH" or rig is None or rig.type != "ARMATURE":
            raise RuntimeError("Attempt 31 sealed body or native rig is absent")
        mask = provider.r21.patch_mask(body)
        seam_before = provider.interface_world_points(body, mask)
        normals = provider.r21.r20._capture_preserved_loop_normals(body)
        body_contract_before = _object_contract_snapshot(body)
        rig_contract_before = _rig_contract_snapshot(rig)
        actions_before = _action_inventory()
        protected_before = _protected_object_snapshot(body, rig)
        body_before_exact = provider.r21.exact_audit(body)
        body_before_patch_faces = {
            int(face.index)
            for face in body.data.polygons
            if int(face.material_index) == int(config["objects"]["patch_material_index"])
        }
        inherited_before_signature = _exact_inherited_pair_signature(
            body, body_before_exact, body_before_patch_faces
        )
        adult = provider.append_patch(patch_blend, config["objects"]["patch_object"])
        if adult.data.name != config["objects"]["patch_mesh"]:
            raise RuntimeError("Attempt 31 appended patch mesh identity drifted")

        selected = config["selected_candidate"]
        selected_face_ids = {int(value) for value in selected["face_indices"]}
        domain_record = json.loads(
            project_existing_path(
                config["bindings"]["repair_domain_diagnostic"]["path"]
            ).read_text(encoding="utf-8")
        )
        current_face_ids = {
            int(value)
            for value in domain_record["smallest_qualified_replacement_domain"][
                "face_indices"
            ]
        }

        def attempt31_capture_local_domain(
            bm: Any, exact: Mapping[str, Any], runtime: Mapping[str, Any]
        ) -> dict[str, Any]:
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            bm.verts.index_update()
            bm.edges.index_update()
            bm.faces.index_update()
            genuine_pairs = sorted(
                list(map(int, record["face_indices"]))
                for record in exact["pairs"]
                if record["genuine_positive_area_or_segment_penetration"]
            )
            involved_faces = sorted({value for pair in genuine_pairs for value in pair})
            involved_vertices = sorted(
                {
                    int(vertex.index)
                    for face_index in involved_faces
                    for vertex in bm.faces[face_index].verts
                }
            )
            if (
                len(genuine_pairs) != int(runtime["initial_exact_pair_count"])
                or provider.canonical_sha256(genuine_pairs)
                != runtime["exact_pair_sha256"]
                or provider.canonical_sha256(involved_faces)
                != runtime["involved_face_sha256"]
                or provider.canonical_sha256(involved_vertices)
                != runtime["involved_vertex_sha256"]
            ):
                raise RuntimeError("Attempt 31 inherited collision identity drifted")
            computed_added_faces = {
                int(face.index)
                for vertex_index in selected["source_mesh_vertex_indices"]
                for face in bm.verts[int(vertex_index)].link_faces
            }.difference(current_face_ids)
            if (
                sorted(computed_added_faces)
                != selected["added_complete_vertex_star_face_indices"]
                or current_face_ids.union(computed_added_faces) != selected_face_ids
            ):
                raise RuntimeError(
                    "Attempt 31 complete selected vertex-star derivation drifted"
                )
            selected_faces = {bm.faces[index] for index in selected_face_ids}
            selected_vertices = {
                vertex for face in selected_faces for vertex in face.verts
            }
            selected_edges = {edge for face in selected_faces for edge in face.edges}
            local_boundary_edges = {
                edge
                for edge in selected_edges
                if sum(face in selected_faces for face in edge.link_faces) == 1
            }
            cycle = provider.ordered_cycle(local_boundary_edges)
            cycle_ids = [int(vertex.index) for vertex in cycle]
            expected_cycle = [
                int(value) for value in selected["boundary_cycle_mesh_vertex_indices"]
            ]
            matching = next(
                (row for row in _cycle_rotations(cycle_ids) if row == expected_cycle),
                None,
            )
            if matching is None:
                raise RuntimeError("Attempt 31 exact 40-vertex cycle drifted")
            by_id = {int(vertex.index): vertex for vertex in cycle}
            cycle = [by_id[value] for value in matching]
            interior = selected_vertices - set(cycle)
            face_ids = sorted(int(face.index) for face in selected_faces)
            vertex_ids = sorted(int(vertex.index) for vertex in selected_vertices)
            boundary_edge_ids = sorted(
                sorted((int(edge.verts[0].index), int(edge.verts[1].index)))
                for edge in local_boundary_edges
            )
            if (
                face_ids != selected["face_indices"]
                or len(selected_faces) != int(selected["face_count"])
                or provider.canonical_sha256(face_ids)
                != selected["face_indices_sha256"]
                or len(selected_vertices) != int(selected["vertex_count"])
                or provider.canonical_sha256(vertex_ids)
                != selected["vertex_indices_sha256"]
                or len(selected_edges) != int(selected["edge_count"])
                or len(interior) != int(selected["interior_vertex_count"])
                or len(local_boundary_edges) != int(selected["boundary_edge_count"])
                or provider.canonical_sha256(boundary_edge_ids)
                != selected["boundary_edge_indices_sha256"]
                or provider.canonical_sha256(matching)
                != selected["boundary_cycle_mesh_vertex_indices_sha256"]
            ):
                raise RuntimeError("Attempt 31 exact selected-domain topology drifted")
            global_edges = [edge for edge in bm.edges if len(edge.link_faces) == 1]
            global_vertices = {vertex for edge in global_edges for vertex in edge.verts}
            if (
                len(global_vertices)
                != int(config["unchanged_hard_gates"]["global_seam_vertex_count"])
                or global_vertices.intersection(selected_vertices)
            ):
                raise RuntimeError("Attempt 31 selected domain is not seam-disjoint")
            captured["patch_tag_snapshot"] = _begin_tagged_preservation(
                bm,
                {int(vertex.index) for vertex in interior},
                selected_face_ids,
                PATCH_VERTEX_TAG,
                PATCH_FACE_TAG,
            )
            captured["local_boundary_vertex_keys"] = sorted(
                _vector_key(vertex.co) for vertex in cycle
            )
            captured["local_boundary_edge_keys"] = sorted(
                _edge_coordinate_key(edge.verts[0], edge.verts[1])
                for edge in local_boundary_edges
            )
            return {
                "selected_faces": selected_faces,
                "selected_vertices": selected_vertices,
                "selected_edges": selected_edges,
                "local_boundary_edges": local_boundary_edges,
                "local_boundary": set(cycle),
                "interior": interior,
                "cycle": cycle,
                "face_ids": face_ids,
                "vertex_ids": vertex_ids,
                "boundary_edge_ids": boundary_edge_ids,
            }

        def attempt31_capture_quality(
            boundary: Sequence[Any], runtime: Mapping[str, Any]
        ) -> dict[str, Any]:
            result = provider_quality(boundary, runtime)
            captured["cdt"] = result
            return result

        provider.capture_local_domain = attempt31_capture_local_domain
        provider.quality_refined_cdt = attempt31_capture_quality
        reconstruction_config = dict(attempt15_config["measured_repair_domain"])
        reconstruction_config.update(config["replacement"])
        reconstruction_config.update(
            {
                "face_count": selected["face_count"],
                "vertex_count": selected["vertex_count"],
                "edge_count": selected["edge_count"],
                "interior_vertex_count": selected["interior_vertex_count"],
                "local_boundary_vertex_count": selected["boundary_edge_count"],
                "local_boundary_edge_count": selected["boundary_edge_count"],
                "domain_face_sha256": selected["face_indices_sha256"],
                "domain_vertex_sha256": selected["vertex_indices_sha256"],
                "local_boundary_edge_sha256": selected[
                    "boundary_edge_indices_sha256"
                ],
                "local_boundary_cycle_sha256": selected[
                    "boundary_cycle_mesh_vertex_indices_sha256"
                ],
            }
        )
        repair = provider.reconstruct_local_domain(adult, reconstruction_config)
        provider.capture_local_domain = provider_capture
        provider.quality_refined_cdt = provider_quality

        cdt_topology = _cdt_topology(
            captured["cdt"], int(selected["boundary_edge_count"])
        )
        patch_preservation = _finish_tagged_preservation(
            adult,
            captured["patch_tag_snapshot"],
            int(repair["new_interior_vertex_count"]),
            int(repair["new_face_count"]),
            captured["local_boundary_vertex_keys"],
            captured["local_boundary_edge_keys"],
        )
        adult_vertex_count_after_reconstruction = len(adult.data.vertices)
        adult_face_count_after_reconstruction = len(adult.data.polygons)

        standalone_after = provider.exact_report(adult)
        if standalone_after["exact_genuine_penetration_pair_count"] != 0:
            raise RuntimeError("Attempt 31 standalone patch intersections remain")
        comparison = provider.r21.interface_comparison(body, mask, adult)
        if comparison["maximum_distance_m"] != 0.0 or comparison["unique_matches"] != 34:
            raise RuntimeError("Attempt 31 global patch interface changed")
        body_tag_snapshot = _tag_body_for_preservation(body, mask)
        provider.r21.remove_old_patch(body, mask)
        join = provider.r21.join_and_weld(body, adult, rig)
        if join["actual_vertex_reduction"] != 34:
            raise RuntimeError("Attempt 31 did not weld exactly 34 seam vertices")
        body_preservation = _finish_tagged_preservation(
            body,
            body_tag_snapshot,
            adult_vertex_count_after_reconstruction - 34,
            adult_face_count_after_reconstruction,
        )
        normal_restore = provider.r21.r20._restore_exact_preserved_loop_normals(
            body, normals
        )
        body_contract_after = _object_contract_snapshot(body)
        rig_contract_after = _rig_contract_snapshot(rig)
        actions_after = _action_inventory()
        protected_after = _protected_object_snapshot(body, rig)
        seam_after = provider.exact_interface_delta(seam_before, body)
        final_exact = provider.r21.exact_audit(body)
        classification = final_exact["classification"]
        final_patch_faces = {
            int(face.index)
            for face in body.data.polygons
            if int(face.material_index) == int(config["objects"]["patch_material_index"])
        }
        inherited_after_signature = _exact_inherited_pair_signature(
            body, final_exact, final_patch_faces
        )
        bindings_after = verify_bindings(config)
        provider_verified_after = provider.verify_inputs(attempt15_config)

        hard = config["unchanged_hard_gates"]
        structural_gates = {
            "exact_40_edge_local_boundary_coordinates_unchanged": patch_preservation[
                "required_boundary_vertices_exact"
            ]
            and patch_preservation["required_boundary_edges_exact"],
            "cdt_complete_open_boundary_exact": cdt_topology[
                "boundary_is_exact_complete_constrained_edge_set"
            ],
            "cdt_single_face_component": cdt_topology["face_component_count"] == 1,
            "cdt_disk_euler_characteristic_1": cdt_topology[
                "euler_characteristic"
            ]
            == 1,
            "cdt_all_edges_have_one_or_two_faces": cdt_topology[
                "all_edges_have_one_or_two_faces"
            ],
            "new_interior_vertex_count_within_bound": int(
                repair["new_interior_vertex_count"]
            )
            <= int(hard["maximum_new_interior_vertex_count"]),
            "minimum_new_triangle_angle_at_least_12_degrees": float(
                repair["minimum_new_triangle_angle_degrees"]
            )
            >= float(hard["minimum_new_triangle_angle_degrees"]),
            "minimum_new_triangle_world_area_at_least_bound": float(
                repair["minimum_new_triangle_world_area_m2"]
            )
            >= float(hard["minimum_new_triangle_world_area_m2"]),
            "patch_original_id_layers_exact_and_removed_before_graft": patch_preservation[
                "passes"
            ],
            "patch_no_duplicate_or_missing_old_tags": patch_preservation[
                "no_duplicate_or_missing_old_vertex_or_face_tags"
            ],
            "patch_exact_float_hex_coordinates_ordered_loops_all_uv_layers_weights_material_smoothing": patch_preservation[
                "all_exact_float_hex_coordinates_ordered_loops_all_uv_layers_weights_material_smoothing_preserved"
            ],
            "patch_exact_new_vertex_and_face_counts": patch_preservation[
                "exact_new_vertex_and_face_counts"
            ],
            "patch_temporary_id_layers_removed_before_graft": patch_preservation[
                "temporary_original_id_layers_removed_before_graft_or_finish"
            ],
            "body_nonpatch_original_id_layers_exact_and_removed_before_final_audit": body_preservation[
                "passes"
            ],
            "body_nonpatch_no_duplicate_or_missing_old_tags": body_preservation[
                "no_duplicate_or_missing_old_vertex_or_face_tags"
            ],
            "body_nonpatch_exact_float_hex_coordinates_ordered_loops_all_uv_layers_weights_material_smoothing": body_preservation[
                "all_exact_float_hex_coordinates_ordered_loops_all_uv_layers_weights_material_smoothing_preserved"
            ],
            "body_exact_new_vertex_and_face_counts": body_preservation[
                "exact_new_vertex_and_face_counts"
            ],
            "body_temporary_id_layers_removed_before_final_audit": body_preservation[
                "temporary_original_id_layers_removed_before_graft_or_finish"
            ],
            "repair_removed_exact_selected_face_and_interior_vertex_counts": int(
                repair["removed_face_count"]
            )
            == int(selected["face_count"])
            and int(repair["removed_vertex_count"])
            == int(selected["interior_vertex_count"]),
            "standalone_patch_exact_genuine_intersections_zero": standalone_after[
                "exact_genuine_penetration_pair_count"
            ]
            == 0,
            "global_34_seam_coordinate_delta_exact_zero": seam_after[
                "maximum_distance_m"
            ]
            == 0.0,
            "global_34_seam_unique_weld_count_exactly_34": join[
                "actual_vertex_reduction"
            ]
            == 34,
            "post_graft_patch_related_exact_genuine_intersections_zero": classification[
                "patch_related_exact_genuine_pairs"
            ]
            == 0,
            "post_graft_new_noninherited_exact_genuine_intersections_zero": inherited_after_signature
            == inherited_before_signature,
            "preserved_inherited_nonpatch_pair_count_exactly_29": classification[
                "nonpatch_exact_genuine_pairs"
            ]
            == int(hard["preserved_inherited_nonpatch_exact_genuine_intersections"]),
            "body_transform_parent_modifiers_vertex_groups_shape_keys_animation_and_material_slots_exact": body_contract_after
            == body_contract_before,
            "native_rig_object_armature_bones_pose_constraints_and_animation_exact": rig_contract_after
            == rig_contract_before,
            "global_action_inventory_exact": actions_after == actions_before,
            "protected_original_nonbody_nonrig_object_state_and_mesh_coordinate_topology_uv_material_smoothing_exact": protected_after
            == protected_before,
            "preserved_loop_normal_and_uv_selection_restore_pass": bool(
                normal_restore["all_surviving_custom_normal_short2_values_exact"]
            )
            and bool(normal_restore["all_surviving_uv_selection_values_exact"])
            and normal_restore["patch_normal_numeric_gate"]["status"] == "PASS",
            "source_and_prior_evidence_hashes_unchanged": bindings_after == verified,
            "attempt15_provider_inputs_unchanged": provider_verified_after
            == provider_verified,
        }
        if not all(structural_gates.values()):
            failed = sorted(name for name, value in structural_gates.items() if not value)
            raise RuntimeError("Attempt 31 structural gate failed: " + ",".join(failed))

        report = {
            "schema": "kira.avatar.r24.blackproject_attempt31.no_save_reconstruction.v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "NO_SAVE_IN_MEMORY_STRUCTURAL_GATES_PASS_OWNER_REVIEW_STILL_REQUIRED",
            "attempt_id": "attempt_31",
            "inputs": verified,
            "worker": started,
            "selected_candidate": selected,
            "candidate_classification": "ATTEMPT30_NECESSARY_ELIGIBLE_ONLY_BEFORE_THIS_RUN",
            "repair": repair,
            "cdt_topology": cdt_topology,
            "patch_outside_domain_exact_preservation": patch_preservation,
            "body_nonpatch_exact_preservation": body_preservation,
            "body_contract_before_sha256": canonical_sha256(body_contract_before),
            "body_contract_after_sha256": canonical_sha256(body_contract_after),
            "rig_contract_before_sha256": canonical_sha256(rig_contract_before),
            "rig_contract_after_sha256": canonical_sha256(rig_contract_after),
            "action_inventory_before_sha256": canonical_sha256(actions_before),
            "action_inventory_after_sha256": canonical_sha256(actions_after),
            "protected_object_snapshot_before_sha256": canonical_sha256(
                protected_before
            ),
            "protected_object_snapshot_after_sha256": canonical_sha256(
                protected_after
            ),
            "standalone_exact_intersections": standalone_after,
            "interface_before_graft": comparison,
            "join": join,
            "global_seam_after_graft": seam_after,
            "normal_restore": normal_restore,
            "inherited_pair_signature_before": inherited_before_signature,
            "inherited_pair_signature_after": inherited_after_signature,
            "final_exact_intersections": final_exact,
            "structural_hard_gates": structural_gates,
            "save_gate": {
                "structural_hard_gates_pass": True,
                "owner_visual_acceptance": False,
                "render_exists": False,
                "save_allowed": False,
                "reason": "Attempt 31 deliberately stops before render/save; separate owner review remains required",
            },
            "truth": {
                "source_files_mutated": False,
                "prior_evidence_mutated": False,
                "runtime_changed": False,
                "render_reached": False,
                "blend_saved": False,
                "body_activated": False,
                "body_repair_owner_approved": False,
                "internal_anatomy_or_physiology_implemented": False,
                "bathroom_reproduction_pregnancy_function_proven": False,
            },
        }
        _exclusive_write_once(output / config["output"]["diagnostic"], report)
    except Exception as exc:
        provider.capture_local_domain = provider_capture
        provider.quality_refined_cdt = provider_quality
        failure = {
            "schema": "kira.avatar.r24.blackproject_attempt31.failure.v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "NO_SAVE_ATTEMPT31_FAILURE_PRESERVED",
            "attempt_id": "attempt_31",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "render_reached": False,
            "blend_saved": False,
            "runtime_changed": False,
        }
        _exclusive_write_once(output / config["output"]["failure"], failure)
        raise
    finally:
        provider.capture_local_domain = provider_capture
        provider.quality_refined_cdt = provider_quality


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    argv = []
    if "--" in __import__("sys").argv:
        argv = __import__("sys").argv[__import__("sys").argv.index("--") + 1 :]
    else:
        argv = __import__("sys").argv[1:]
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    config = load_config(Path(args.config))
    verified = verify_bindings(config)
    run_blender_diagnostic(config, verified)


if __name__ == "__main__":
    main()
