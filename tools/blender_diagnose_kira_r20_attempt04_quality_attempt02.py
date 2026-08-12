#!/usr/bin/env python3
"""Corrected read-only face-quality diagnosis for sealed Kira R20 Attempt04.

Importing the preserved diagnostic worker necessarily imports the sealed
author worker, whose Blender dependencies load the ``bmesh`` module.  This
worker records that transitive module-load truth while independently proving
that it imports no bmesh name, constructs no BMesh, calls no BMesh API, edits
no mesh, applies no patch, renders nothing, and saves no Blend.
"""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import traceback
from typing import Any, Mapping, Sequence


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

# This preserved import loads bpy and then the sealed author.  The sealed
# author's hash-bound top-level Blender dependency loads bmesh transitively.
import blender_diagnose_kira_r20_attempt04_quality as prior_diagnostic  # noqa: E402


DIAGNOSTIC_ID = "KIRA_R20_AUTHOR_ATTEMPT04_FACE_QUALITY_DIAGNOSTIC_02"
DEFAULT_CONFIG = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_attempt04_quality_diagnostic_prepared_attempt_02/DIAGNOSTIC_CONFIG.json"
)
CONFIG_SHA256 = "5aaefa6440816c8dea289e7070e340c2fc4606fb04a310321ff4a3ae124c93fe"
EXPECTED_OUTPUT_REL = (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_04_quality_diagnostic_01"
)
PRIOR_BUNDLE_MANIFEST_SHA256 = (
    "bdfe21e6f79bfce21534c2e65c2b51927ac008243487df469fad27ecc8ab8ecf"
)
PRIOR_WORKER_SHA256 = (
    "0e7179e88cd53d7f3ba3f7d4fda0e84a4d2ea74443e4019cf117034376e10096"
)
PRIOR_CONFIG_SHA256 = (
    "9971e3dcaf333df9903c6c154817f74a4b5a78e0daac6b1f80dc0c4512e866b2"
)
PRIOR_TESTS_SHA256 = (
    "ab1c5c25d73b6400a3092e591a58f97158d1b609296d85f4d9aa3c116fc195c6"
)
PRIOR_SYSTEM_DOC_SHA256 = (
    "12674ea8c5aa56d71ed28e2dfb18f3df3a63a15e2a3ce7c5a2b2947cc126668b"
)


class CorrectedDiagnosticError(RuntimeError):
    """Fail-closed corrected diagnostic contract error."""


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--acknowledge-private-inactive", action="store_true")
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def call_chain(node: ast.AST) -> str:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def assert_corrected_worker_source_contract() -> dict[str, Any]:
    source_path = Path(__file__).resolve(strict=True)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    direct_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            direct_imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            direct_imports.append(node.module)
    if any(name == "bmesh" or name.startswith("bmesh.") for name in direct_imports):
        raise CorrectedDiagnosticError("corrected worker directly imports bmesh")

    calls = {
        call_chain(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    forbidden_exact = {
        "prior_diagnostic.sealed_author._prepare_candidate_fields",
        "prior_diagnostic.sealed_author._apply_local_patch",
        "prior_diagnostic.sealed_author.run_pose_suite",
        "prior_diagnostic.sealed_author.run_verify_render_mode",
        "bpy.ops.wm.save_as_mainfile",
        "bpy.ops.render.render",
        "bpy.ops.object.mode_set",
    }
    forbidden_suffixes = {
        ".from_mesh",
        ".to_mesh",
        ".from_pydata",
        ".clear_geometry",
    }
    violating_calls = sorted(
        call
        for call in calls
        if call in forbidden_exact
        or call == "bmesh"
        or call.startswith("bmesh.")
        or call.startswith("bpy.ops.mesh.")
        or any(call.endswith(suffix) for suffix in forbidden_suffixes)
    )
    if violating_calls:
        raise CorrectedDiagnosticError(
            f"corrected worker contains a forbidden mesh/BMesh call: {violating_calls}"
        )
    return {
        "corrected_worker_path": prior_diagnostic.project_relative(source_path),
        "direct_bmesh_import_by_corrected_worker": False,
        "bmesh_construction_or_api_call_by_corrected_worker": False,
        "mesh_edit_by_corrected_worker": False,
        "candidate_field_preparation_call_by_corrected_worker": False,
        "local_patch_application_call_by_corrected_worker": False,
        "pose_render_or_blend_save_call_by_corrected_worker": False,
        "static_call_count_inspected": len(calls),
    }


def validate_prior_bundle_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest_record = prior_diagnostic.assert_hash(
        manifest_path,
        PRIOR_BUNDLE_MANIFEST_SHA256,
        "preserved first diagnostic bundle manifest",
    )
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        int(value.get("schema_version", -1)) != 1
        or value.get("status")
        != "SEALED_STATIC_PASS_DIAGNOSTIC_ATTEMPT01_PREPARED_NOT_EXECUTED"
    ):
        raise CorrectedDiagnosticError("preserved first diagnostic manifest identity drifted")
    if (
        value.get("diagnostic_blender_executed") is not False
        or value.get("diagnostic_output_exists") is not False
        or value.get("body_asset_mutated") is not False
        or value.get("candidate_blend_created") is not False
    ):
        raise CorrectedDiagnosticError("preserved first diagnostic state drifted")
    entries = value.get("files_excluding_this_manifest")
    if not isinstance(entries, list) or len(entries) != 9:
        raise CorrectedDiagnosticError("preserved first diagnostic member set drifted")
    records = []
    listed_local: set[Path] = set()
    prepared_root = manifest_path.parent.resolve()
    for entry in entries:
        path = prior_diagnostic.resolve_project_path(str(entry["path"]))
        record = prior_diagnostic.assert_hash(path, str(entry["sha256"]), str(entry["path"]))
        if int(entry["size_bytes"]) != int(path.stat().st_size):
            raise CorrectedDiagnosticError(f"preserved member size drifted: {entry['path']}")
        records.append(record)
        if path.parent.resolve() == prepared_root:
            listed_local.add(path.resolve())
    actual_local = {
        path.resolve()
        for path in manifest_path.parent.iterdir()
        if path.is_file() and path.resolve() != manifest_path.resolve()
    }
    if actual_local != listed_local:
        raise CorrectedDiagnosticError("preserved first prepared directory member set drifted")
    return {
        "manifest": manifest_record,
        "member_count": len(records),
        "all_member_hashes_and_sizes_exact": True,
        "prepared_directory_member_set_exact": True,
        "members": records,
    }


def validate_config(
    config_path: Path,
    acknowledge: bool,
) -> tuple[dict[str, Any], dict[str, Path]]:
    if not acknowledge:
        raise CorrectedDiagnosticError("--acknowledge-private-inactive is required")
    exact_config = config_path.resolve(strict=True)
    if exact_config != DEFAULT_CONFIG.resolve(strict=True):
        raise CorrectedDiagnosticError("only the exact corrected prepared config is permitted")
    prior_diagnostic.assert_hash(exact_config, CONFIG_SHA256, "corrected diagnostic config")
    config = json.loads(exact_config.read_text(encoding="utf-8"))
    if Path(str(config.get("project_root", ""))).resolve() != PROJECT_ROOT.resolve():
        raise CorrectedDiagnosticError("project root drifted")
    if (
        int(config.get("schema_version", -1)) != 2
        or config.get("diagnostic_id") != DIAGNOSTIC_ID
        or config.get("status") != "CORRECTED_PREPARED_NOT_EXECUTED"
    ):
        raise CorrectedDiagnosticError("corrected diagnostic identity or status drifted")
    if any(
        config.get(key) is not True
        for key in ("private", "inactive", "unassigned", "unpublished")
    ):
        raise CorrectedDiagnosticError("private/inactive state drifted")

    required_correction = {
        "supersedes_unexecuted_prepared_attempt": "kira_r20_attempt04_quality_diagnostic_prepared",
        "prior_bundle_deleted_or_modified": False,
        "prior_defect": (
            "the preserved first prepared bundle conflated transitive module loading "
            "with corrected-worker API use"
        ),
        "correct_truth": (
            "importing the sealed author worker transitively loads the Blender bmesh "
            "module; the diagnostic directly imports no bmesh name and performs no "
            "BMesh construction, API call, edit, or patch application"
        ),
        "bmesh_module_loaded_transitively": True,
        "direct_bmesh_import_by_corrected_worker": False,
        "bmesh_construction_or_api_call_by_corrected_worker": False,
        "mesh_edit_or_patch_application_by_corrected_worker": False,
    }
    if config.get("correction") != required_correction:
        raise CorrectedDiagnosticError("corrected transitive-bmesh truth drifted")

    required_contract = {
        "diagnostic_only": True,
        "exact_sealed_author_construction_reused": True,
        "all_ratio_violations_recorded": True,
        "worst_faces_include_all_edges_and_coordinates": True,
        "seam_collar_core_mapping_required": True,
        "candidate_comparison_required": True,
        "source_and_body_hashes_before_after_required": True,
        "bmesh_module_loaded_transitively_expected": True,
        "direct_bmesh_import_by_corrected_worker_forbidden": True,
        "bmesh_construction_or_api_call_by_corrected_worker_forbidden": True,
        "mesh_edit_by_corrected_worker_forbidden": True,
        "prepare_candidate_fields_call_forbidden": True,
        "apply_local_patch_call_forbidden": True,
        "pose_suite_call_forbidden": True,
        "render_call_forbidden": True,
        "blend_save_forbidden": True,
        "threshold_loosening_forbidden": True,
        "topology_change_forbidden": True,
        "candidate_change_forbidden": True,
        "new_candidate_forbidden": True,
        "runtime_activation_assignment_export_publication": False,
    }
    if config.get("contract") != required_contract:
        raise CorrectedDiagnosticError("corrected read-only contract drifted")

    expected_bindings = {
        "source_blend": str(config["source_blend_sha256"]),
        "sealed_author_worker": prior_diagnostic.SEALED_AUTHOR_WORKER_SHA256,
        "sealed_pure_contract": prior_diagnostic.SEALED_PURE_CONTRACT_SHA256,
        "sealed_author_config": prior_diagnostic.SEALED_AUTHOR_CONFIG_SHA256,
        "sealed_author_tests": prior_diagnostic.SEALED_AUTHOR_TESTS_SHA256,
        "sealed_author_manifest": prior_diagnostic.SEALED_AUTHOR_MANIFEST_SHA256,
        "passed_preflight_evidence": prior_diagnostic.PASSED_PREFLIGHT_EVIDENCE_SHA256,
        "author_attempt_04_summary": prior_diagnostic.AUTHOR_ATTEMPT04_HASHES[
            "author_attempt_04_summary"
        ],
        "author_attempt_04_failure": prior_diagnostic.AUTHOR_ATTEMPT04_HASHES[
            "author_attempt_04_failure"
        ],
        "author_attempt_04_candidate_a_failure": prior_diagnostic.AUTHOR_ATTEMPT04_HASHES[
            "author_attempt_04_candidate_a_failure"
        ],
        "author_attempt_04_candidate_b_failure": prior_diagnostic.AUTHOR_ATTEMPT04_HASHES[
            "author_attempt_04_candidate_b_failure"
        ],
        "prior_prepared_bundle_manifest": PRIOR_BUNDLE_MANIFEST_SHA256,
        "prior_diagnostic_worker": PRIOR_WORKER_SHA256,
        "prior_diagnostic_config": PRIOR_CONFIG_SHA256,
        "prior_diagnostic_tests": PRIOR_TESTS_SHA256,
        "prior_system_doc": PRIOR_SYSTEM_DOC_SHA256,
        "diagnostic_pure_helper": prior_diagnostic.DIAGNOSTIC_HELPER_SHA256,
    }
    paths: dict[str, Path] = {}
    for key, expected_hash in expected_bindings.items():
        path = prior_diagnostic.resolve_project_path(str(config[key]))
        prior_diagnostic.assert_hash(path, expected_hash, key)
        if str(config.get(f"{key}_sha256", "")).lower() != expected_hash:
            raise CorrectedDiagnosticError(f"configured {key} hash record drifted")
        paths[key] = path

    prior_bundle = validate_prior_bundle_manifest(paths["prior_prepared_bundle_manifest"])
    prior_config, prior_paths = prior_diagnostic.validate_config(
        paths["prior_diagnostic_config"], True
    )
    shared_fields = (
        "source_blend",
        "source_blend_sha256",
        "sealed_author_worker",
        "sealed_author_worker_sha256",
        "sealed_pure_contract",
        "sealed_pure_contract_sha256",
        "diagnostic_pure_helper",
        "diagnostic_pure_helper_sha256",
        "sealed_author_config",
        "sealed_author_config_sha256",
        "sealed_author_tests",
        "sealed_author_tests_sha256",
        "sealed_author_manifest",
        "sealed_author_manifest_sha256",
        "passed_preflight_evidence",
        "passed_preflight_evidence_sha256",
        "author_attempt_04_summary",
        "author_attempt_04_summary_sha256",
        "author_attempt_04_failure",
        "author_attempt_04_failure_sha256",
        "author_attempt_04_candidate_a_failure",
        "author_attempt_04_candidate_a_failure_sha256",
        "author_attempt_04_candidate_b_failure",
        "author_attempt_04_candidate_b_failure_sha256",
        "output",
        "candidate_ids",
        "worst_face_count_per_candidate",
        "maximum_quad_edge_ratio_threshold_unchanged",
        "minimum_face_area_threshold_m2_unchanged",
        "coincidence_tolerance_m",
        "expected_attempt_04_quality",
    )
    for field in shared_fields:
        if config.get(field) != prior_config.get(field):
            raise CorrectedDiagnosticError(f"corrected config changed sealed field: {field}")

    output = prior_diagnostic.resolve_project_path(str(config["output"]), must_exist=False)
    if prior_diagnostic.project_relative(output) != EXPECTED_OUTPUT_REL:
        raise CorrectedDiagnosticError("append-only diagnostic output drifted")
    paths["output"] = output
    if prior_paths["output"].resolve() != output.resolve():
        raise CorrectedDiagnosticError("corrected and preserved output targets differ")

    source_contract = assert_corrected_worker_source_contract()
    if "bmesh" not in sys.modules:
        raise CorrectedDiagnosticError(
            "sealed author import did not produce the expected transitive bmesh module load"
        )
    sealed_author_source = paths["sealed_author_worker"].read_text(encoding="utf-8")
    sealed_author_tree = ast.parse(sealed_author_source)
    sealed_author_bmesh_import = any(
        (
            isinstance(node, ast.Import)
            and any(alias.name == "bmesh" for alias in node.names)
        )
        or (isinstance(node, ast.ImportFrom) and node.module == "bmesh")
        for node in ast.walk(sealed_author_tree)
    )
    if not sealed_author_bmesh_import:
        raise CorrectedDiagnosticError("hash-bound sealed author no longer imports bmesh")

    config["_prior_config_value"] = prior_config
    config["_prior_paths_value"] = prior_paths
    config["_prior_bundle_value"] = prior_bundle
    config["_source_contract_value"] = source_contract
    return config, paths


def package_manifest(output: Path) -> Path:
    manifest_path = output / "PACKAGE_MANIFEST.json"
    members = []
    for member in sorted(path for path in output.rglob("*") if path.is_file()):
        if member == manifest_path:
            continue
        members.append(
            {
                "path": prior_diagnostic.project_relative(member),
                "sha256": prior_diagnostic.sha256_file(member),
                "size_bytes": member.stat().st_size,
            }
        )
    prior_diagnostic.write_json_exclusive(
        manifest_path,
        {
            "schema_version": 2,
            "diagnostic_id": DIAGNOSTIC_ID,
            "status": (
                "CORRECTED_READ_ONLY_FACE_QUALITY_DIAGNOSTIC_"
                "NO_MESH_EDIT_NO_BLEND_SAVE"
            ),
            "files_excluding_this_manifest": members,
        },
    )
    return manifest_path


def run(config: Mapping[str, Any], paths: Mapping[str, Path]) -> dict[str, Any]:
    output = paths["output"]
    if output.exists():
        raise CorrectedDiagnosticError(
            f"append-only diagnostic output already exists: {output}"
        )
    output.mkdir(parents=True, exist_ok=False)

    source_hash_before = prior_diagnostic.sha256_file(paths["source_blend"])
    prior_diagnostic.sealed_author._open_exact_blend(paths["source_blend"])
    prior_config = config["_prior_config_value"]
    prior_paths = config["_prior_paths_value"]
    author_config = prior_config["_sealed_author_config_value"]
    author_paths = prior_config["_sealed_author_paths_value"]
    body, _rig, preflight, inputs = prior_diagnostic.sealed_author.preflight_scene(
        author_config, author_paths
    )
    body_hash_before = prior_diagnostic.sealed_author.mesh_geometry_uv_signature(body)
    inventory_before = prior_diagnostic.sealed_author._object_inventory()

    construction_inputs = {
        "seam_project_m": [list(value) for value in inputs["seam_project_m"]],
        "first_exterior_ring_project_m": [
            list(value) for value in inputs["first_exterior_ring"]
        ],
        "second_exterior_ring_project_m": [
            list(value) for value in inputs["second_exterior_ring"]
        ],
        "seam_normals_project": [list(value) for value in inputs["seam_normals"]],
    }
    construction_input_hashes = {
        key: prior_diagnostic.sha256_json(value)
        for key, value in construction_inputs.items()
    }
    seam_source_ids = [
        int(value) for value in preflight["mask"]["canonical_seam_vertex_ids"]
    ]
    expected_quality = config["expected_attempt_04_quality"]
    records = []
    positions_by_candidate: dict[str, Sequence[Sequence[float]]] = {}
    details_by_candidate: dict[str, Mapping[str, Any]] = {}
    for candidate_id_value in config["candidate_ids"]:
        candidate_id = str(candidate_id_value)
        geometry = prior_diagnostic.build_exact_candidate_geometry(
            body, preflight["mask"], inputs, candidate_id
        )
        details = prior_diagnostic.quality_diagnostic.detailed_geometry_quality(
            geometry["positions_project_m"],
            geometry["faces"],
            seam_source_ids,
            worst_n=int(config["worst_face_count_per_candidate"]),
            maximum_quad_edge_ratio=float(
                config["maximum_quad_edge_ratio_threshold_unchanged"]
            ),
            coincidence_tolerance_m=float(config["coincidence_tolerance_m"]),
        )
        prior_diagnostic.assert_attempt04_aggregate(
            candidate_id, geometry["aggregate_quality"], expected_quality[candidate_id]
        )
        prior_diagnostic.assert_attempt04_aggregate(
            candidate_id, details, expected_quality[candidate_id]
        )
        positions_by_candidate[candidate_id] = geometry["positions_project_m"]
        details_by_candidate[candidate_id] = details
        records.append(
            {
                "candidate_id": candidate_id,
                "candidate_parameters": geometry["geometry_evidence"]["candidate"],
                "positions_project_m_sha256": prior_diagnostic.sha256_json(
                    geometry["positions_project_m"]
                ),
                "all_774_positions_project_m": [
                    list(value) for value in geometry["positions_project_m"]
                ],
                "reverse_winding": geometry["reverse_winding"],
                "old_patch_average_normal_project": geometry[
                    "old_patch_average_normal_project"
                ],
                "first_generated_face_normal_project": geometry[
                    "first_generated_face_normal_project"
                ],
                "geometry_construction": geometry["geometry_evidence"],
                "topology": geometry["topology"],
                "aggregate_quality": geometry["aggregate_quality"],
                "detailed_quality": details,
                "attempt04_aggregate_reproduced": True,
            }
        )

    first_id, second_id = [str(value) for value in config["candidate_ids"]]
    comparison = prior_diagnostic.quality_diagnostic.compare_candidate_quality(
        positions_by_candidate[first_id],
        details_by_candidate[first_id],
        positions_by_candidate[second_id],
        details_by_candidate[second_id],
        difference_count=int(config["worst_face_count_per_candidate"]),
    )

    body_hash_after = prior_diagnostic.sealed_author.mesh_geometry_uv_signature(body)
    inventory_after = prior_diagnostic.sealed_author._object_inventory()
    source_hash_after = prior_diagnostic.sha256_file(paths["source_blend"])
    if body_hash_after != body_hash_before:
        raise CorrectedDiagnosticError("diagnostic changed the body geometry/UV signature")
    if inventory_after != inventory_before:
        raise CorrectedDiagnosticError("diagnostic changed the Blender object inventory")
    if (
        source_hash_after != source_hash_before
        or source_hash_after != config["source_blend_sha256"]
    ):
        raise CorrectedDiagnosticError("diagnostic changed the immutable R19 source Blend")
    if "bmesh" not in sys.modules:
        raise CorrectedDiagnosticError("transitively loaded bmesh module disappeared")

    source_contract = config["_source_contract_value"]
    evidence = {
        "schema_version": 2,
        "diagnostic_id": DIAGNOSTIC_ID,
        "timestamp_utc": utc_now(),
        "status": (
            "PASS_CORRECTED_READ_ONLY_FACE_QUALITY_DIAGNOSTIC_"
            "NO_MESH_EDIT_NO_BLEND_SAVE"
        ),
        "scope": (
            "exact Attempt04 candidate construction before inverse transform or mesh "
            "application"
        ),
        "coordinate_space": "project_world_meters",
        "corrected_import_truth": {
            "bmesh_module_loaded_transitively": True,
            "bmesh_module_load_chain": (
                "corrected worker -> preserved diagnostic worker -> sealed author "
                "worker -> import bmesh"
            ),
            "hash_bound_sealed_author_contains_bmesh_import": True,
            "direct_bmesh_import_by_corrected_worker": source_contract[
                "direct_bmesh_import_by_corrected_worker"
            ],
            "bmesh_construction_or_api_call_by_corrected_worker": source_contract[
                "bmesh_construction_or_api_call_by_corrected_worker"
            ],
            "mesh_edit_by_corrected_worker": source_contract[
                "mesh_edit_by_corrected_worker"
            ],
        },
        "preserved_first_prepared_bundle": config["_prior_bundle_value"],
        "sealed_implementation": {
            "author_worker": prior_diagnostic.assert_hash(
                paths["sealed_author_worker"],
                prior_diagnostic.SEALED_AUTHOR_WORKER_SHA256,
                "sealed author worker",
            ),
            "pure_contract": prior_diagnostic.assert_hash(
                paths["sealed_pure_contract"],
                prior_diagnostic.SEALED_PURE_CONTRACT_SHA256,
                "sealed pure contract",
            ),
            "author_config": prior_diagnostic.assert_hash(
                paths["sealed_author_config"],
                prior_diagnostic.SEALED_AUTHOR_CONFIG_SHA256,
                "sealed author config",
            ),
            "author_tests": prior_diagnostic.assert_hash(
                paths["sealed_author_tests"],
                prior_diagnostic.SEALED_AUTHOR_TESTS_SHA256,
                "sealed author tests",
            ),
            "author_manifest": prior_diagnostic.assert_hash(
                paths["sealed_author_manifest"],
                prior_diagnostic.SEALED_AUTHOR_MANIFEST_SHA256,
                "sealed author manifest",
            ),
            "diagnostic_pure_helper": prior_diagnostic.assert_hash(
                paths["diagnostic_pure_helper"],
                prior_diagnostic.DIAGNOSTIC_HELPER_SHA256,
                "diagnostic pure helper",
            ),
        },
        "author_attempt04_evidence": {
            key: prior_diagnostic.assert_hash(paths[key], expected, key)
            for key, expected in prior_diagnostic.AUTHOR_ATTEMPT04_HASHES.items()
        },
        "source_blend": {
            "path": prior_diagnostic.project_relative(paths["source_blend"]),
            "sha256_before": source_hash_before,
            "sha256_after": source_hash_after,
            "unchanged": True,
        },
        "construction_inputs": construction_inputs,
        "construction_input_sha256": construction_input_hashes,
        "canonical_seam_source_vertex_ids": seam_source_ids,
        "candidate_records": records,
        "candidate_comparison": {
            "first_candidate_id": first_id,
            "second_candidate_id": second_id,
            **comparison,
        },
        "read_only_proof": {
            "body_geometry_uv_sha256_before": body_hash_before,
            "body_geometry_uv_sha256_after": body_hash_after,
            "body_geometry_uv_unchanged": True,
            "object_inventory_sha256_before": prior_diagnostic.sha256_json(
                inventory_before
            ),
            "object_inventory_sha256_after": prior_diagnostic.sha256_json(
                inventory_after
            ),
            "object_inventory_unchanged": True,
            "candidate_field_preparation_called": False,
            "local_patch_application_called": False,
            "pose_suite_called": False,
            "render_called": False,
            "blend_save_called": False,
            "candidate_blend_created": False,
            "threshold_changed": False,
            "topology_changed": False,
            "candidate_parameters_changed": False,
            "runtime_activation_assignment_export_publication": False,
        },
    }
    evidence_path = output / "QUALITY_DIAGNOSTIC_EVIDENCE.json"
    prior_diagnostic.write_json_exclusive(evidence_path, evidence)
    checkpoint_path = output / "CHECKPOINT.md"
    prior_diagnostic.write_text_exclusive(
        checkpoint_path,
        "# Kira R20 Author Attempt04 corrected quality diagnostic\n\n"
        "Status: PASS - exact read-only reconstruction. Importing the sealed author "
        "transitively loaded Blender bmesh as expected; this corrected worker made no "
        "BMesh construction/API call, mesh edit, patch application, pose/render call, "
        "or Blend save.\n\n"
        f"- Evidence: `{prior_diagnostic.project_relative(evidence_path)}`\n"
        f"- Evidence SHA-256: `{prior_diagnostic.sha256_file(evidence_path)}`\n"
        f"- Candidate A maximum ratio: "
        f"`{details_by_candidate[first_id]['maximum_quad_edge_ratio']}`\n"
        f"- Candidate B maximum ratio: "
        f"`{details_by_candidate[second_id]['maximum_quad_edge_ratio']}`\n"
        f"- Candidate A localization: "
        f"`{details_by_candidate[first_id]['failure_localization']['classification']}`\n"
        f"- Candidate B localization: "
        f"`{details_by_candidate[second_id]['failure_localization']['classification']}`\n"
        f"- Immutable R19 source: `{source_hash_after}` (unchanged)\n",
    )
    manifest_path = package_manifest(output)
    return {
        "status": evidence["status"],
        "output": prior_diagnostic.project_relative(output),
        "evidence_sha256": prior_diagnostic.sha256_file(evidence_path),
        "checkpoint_sha256": prior_diagnostic.sha256_file(checkpoint_path),
        "manifest_sha256": prior_diagnostic.sha256_file(manifest_path),
        "bmesh_module_loaded_transitively": True,
        "bmesh_construction_or_api_call_by_corrected_worker": False,
        "mesh_edit_by_corrected_worker": False,
        "source_r19_unchanged": True,
    }


def main() -> int:
    args = parse_args()
    output: Path | None = None
    output_existed_before = True
    try:
        config, paths = validate_config(
            Path(args.config), args.acknowledge_private_inactive
        )
        output = paths["output"]
        output_existed_before = output.exists()
        result = run(config, paths)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        failure = {
            "schema_version": 2,
            "diagnostic_id": DIAGNOSTIC_ID,
            "timestamp_utc": utc_now(),
            "status": "FAILED_CLOSED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "bmesh_module_loaded_transitively_at_failure": "bmesh" in sys.modules,
            "body_mutation_or_blend_save_attempted_by_failure_handler": False,
            "runtime_activation_assignment_export_publication": False,
        }
        if output is not None and output.is_dir() and not output_existed_before:
            failure_path = output / "DIAGNOSTIC_FAILURE.json"
            if not failure_path.exists():
                prior_diagnostic.write_json_exclusive(failure_path, failure)
        print(json.dumps(failure, indent=2, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
