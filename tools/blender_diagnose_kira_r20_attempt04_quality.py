#!/usr/bin/env python3
"""Read-only face-level diagnosis of the sealed Kira R20 Author Attempt04.

This separate worker reconstructs the two exact candidate position fields in
project meters, records their quality failure in detail, and exits without any
BMesh operation, patch application, pose evaluation, render, or Blend save.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import bpy
from mathutils import Vector


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from Core import kira_r20_attempt04_quality_diagnostic as quality_diagnostic  # noqa: E402
from Core import kira_r20_curvilinear_pelvic_patch as patch_contract  # noqa: E402
import blender_author_kira_r20_pelvis_only as sealed_author  # noqa: E402


DIAGNOSTIC_ID = "KIRA_R20_AUTHOR_ATTEMPT04_FACE_QUALITY_DIAGNOSTIC_01"
DEFAULT_CONFIG = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_attempt04_quality_diagnostic_prepared/DIAGNOSTIC_CONFIG.json"
)
CONFIG_SHA256 = "9971e3dcaf333df9903c6c154817f74a4b5a78e0daac6b1f80dc0c4512e866b2"
EXPECTED_OUTPUT_REL = (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_04_quality_diagnostic_01"
)
SEALED_AUTHOR_WORKER_SHA256 = (
    "2b18b3050777f0fe6e414a882e2faa83cc80249ca52d86037a4cfacc78d9329a"
)
SEALED_PURE_CONTRACT_SHA256 = (
    "fe5b9f8b68dd7acd9b6eaaaf26d12d65fe0e3e263548e8979bcb26c0e58f640d"
)
DIAGNOSTIC_HELPER_SHA256 = (
    "89a4674b5be109cedd605d2a51fca6f6bd701fe3b7d4c18f88e8123d631787af"
)
SEALED_AUTHOR_CONFIG_SHA256 = (
    "5ab9d60a948d7cac4e08e71a0f9c3927af9f33004ef23f888cc60f21b2e9e7cc"
)
SEALED_AUTHOR_TESTS_SHA256 = (
    "8e12b0573db0715ea339a163d705aa856142e3fbeee9f02e05e96fb3145bc71a"
)
SEALED_AUTHOR_MANIFEST_SHA256 = (
    "eb585114d2096e9ef76c352a7d6f4c578d71fc960e96c3d69d857213598fa306"
)
PASSED_PREFLIGHT_EVIDENCE_SHA256 = (
    "ff0645d564f935c5e4bd93a621fcbf3653ba91fc0c1830d84196ec818acea105"
)
AUTHOR_ATTEMPT04_HASHES = {
    "author_attempt_04_summary": (
        "66607972ca0678355b87b425678c952cc2b82fdd193894be7bb2666e5186c7af"
    ),
    "author_attempt_04_failure": (
        "e0840aef480144a72221646ef4b67fcda1da5404429e4df46957239a6237f07e"
    ),
    "author_attempt_04_candidate_a_failure": (
        "468b4a8366ce78231b24fada48771a14ca4e96bc8324aec26b2ccbadddcc2299"
    ),
    "author_attempt_04_candidate_b_failure": (
        "a60b8b0ad47cbb87d453a34c845850d5e650b23005913c641cbc6cf1dd31fd28"
    ),
}


class DiagnosticError(RuntimeError):
    """Fail-closed diagnostic contract error."""


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--acknowledge-private-inactive", action="store_true")
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()


def project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise DiagnosticError(f"path escapes project root: {path}") from exc


def resolve_project_path(value: str, *, must_exist: bool = True) -> Path:
    path = (PROJECT_ROOT / Path(value)).resolve()
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise DiagnosticError(f"path escapes project root: {value}") from exc
    if must_exist and not path.exists():
        raise FileNotFoundError(path)
    return path


def assert_hash(path: Path, expected: str, label: str) -> dict[str, Any]:
    actual = sha256_file(path)
    if actual != expected.lower():
        raise DiagnosticError(f"{label} hash mismatch: {actual} != {expected}")
    return {
        "path": project_relative(path),
        "sha256": actual,
        "size_bytes": path.stat().st_size,
    }


def write_json_exclusive(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")


def write_text_exclusive(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)


def validate_config(config_path: Path, acknowledge: bool) -> tuple[dict[str, Any], dict[str, Path]]:
    if not acknowledge:
        raise DiagnosticError("--acknowledge-private-inactive is required")
    exact_config = config_path.resolve(strict=True)
    if exact_config != DEFAULT_CONFIG.resolve(strict=True):
        raise DiagnosticError("only the exact prepared quality-diagnostic config is permitted")
    assert_hash(exact_config, CONFIG_SHA256, "diagnostic config")
    config = json.loads(exact_config.read_text(encoding="utf-8"))
    if Path(str(config.get("project_root", ""))).resolve() != PROJECT_ROOT.resolve():
        raise DiagnosticError("project root drifted")
    if (
        int(config.get("schema_version", -1)) != 1
        or config.get("diagnostic_id") != DIAGNOSTIC_ID
        or config.get("status") != "PREPARED_NOT_EXECUTED"
    ):
        raise DiagnosticError("diagnostic identity or prepared status drifted")
    if any(config.get(key) is not True for key in ("private", "inactive", "unassigned", "unpublished")):
        raise DiagnosticError("private/inactive state drifted")
    if config.get("candidate_ids") != [
        "r20_candidate_a_balanced_organic",
        "r20_candidate_b_soft_natural",
    ]:
        raise DiagnosticError("sealed candidate IDs or order drifted")
    if (
        int(config.get("worst_face_count_per_candidate", -1)) != 32
        or float(config.get("maximum_quad_edge_ratio_threshold_unchanged", -1.0)) != 3.0
        or float(config.get("minimum_face_area_threshold_m2_unchanged", -1.0)) != 1.0e-10
        or float(config.get("coincidence_tolerance_m", -1.0)) != 1.0e-12
    ):
        raise DiagnosticError("fixed diagnostic count or unchanged thresholds drifted")
    required_contract = {
        "diagnostic_only": True,
        "exact_sealed_author_construction_reused": True,
        "all_ratio_violations_recorded": True,
        "worst_faces_include_all_edges_and_coordinates": True,
        "seam_collar_core_mapping_required": True,
        "candidate_comparison_required": True,
        "source_and_body_hashes_before_after_required": True,
        "bmesh_import_or_call_forbidden_in_diagnostic": True,
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
        raise DiagnosticError("read-only diagnostic contract drifted")

    expected_paths = {
        "source_blend": str(config["source_blend_sha256"]),
        "sealed_author_worker": SEALED_AUTHOR_WORKER_SHA256,
        "sealed_pure_contract": SEALED_PURE_CONTRACT_SHA256,
        "diagnostic_pure_helper": DIAGNOSTIC_HELPER_SHA256,
        "sealed_author_config": SEALED_AUTHOR_CONFIG_SHA256,
        "sealed_author_tests": SEALED_AUTHOR_TESTS_SHA256,
        "sealed_author_manifest": SEALED_AUTHOR_MANIFEST_SHA256,
        "passed_preflight_evidence": PASSED_PREFLIGHT_EVIDENCE_SHA256,
        **AUTHOR_ATTEMPT04_HASHES,
    }
    paths: dict[str, Path] = {}
    for key, expected in expected_paths.items():
        path = resolve_project_path(str(config[key]))
        assert_hash(path, expected, key)
        if str(config.get(f"{key}_sha256", expected)).lower() != expected:
            raise DiagnosticError(f"configured {key} hash record drifted")
        paths[key] = path
    output = resolve_project_path(str(config["output"]), must_exist=False)
    if project_relative(output) != EXPECTED_OUTPUT_REL:
        raise DiagnosticError("append-only diagnostic output drifted")
    paths["output"] = output

    author_config, author_paths = sealed_author.validate_config(
        paths["sealed_author_config"],
        SimpleNamespace(acknowledge_private_inactive=True),
    )
    if author_paths["source_blend"].resolve() != paths["source_blend"].resolve():
        raise DiagnosticError("sealed author and diagnostic source Blend differ")
    if (
        author_paths["passed_preflight_attempt_04_evidence"].resolve()
        != paths["passed_preflight_evidence"].resolve()
    ):
        raise DiagnosticError("sealed author and diagnostic preflight evidence differ")
    paths["sealed_author_validated_config"] = paths["sealed_author_config"]
    config["_sealed_author_config_value"] = author_config
    config["_sealed_author_paths_value"] = author_paths
    return config, paths


def build_exact_candidate_geometry(
    body: bpy.types.Object,
    mask: Mapping[str, Any],
    inputs: Mapping[str, Any],
    candidate_id: str,
) -> dict[str, Any]:
    candidate = sealed_author._candidate_parameters(candidate_id)
    seam_project_m = tuple(inputs["seam_project_m"])
    positions_project_m, geometry_evidence = patch_contract.build_positions(
        seam_project_m,
        inputs["first_exterior_ring"],
        inputs["second_exterior_ring"],
        inputs["seam_normals"],
        candidate,
    )
    faces = patch_contract.build_quad_topology()
    old_normal = sealed_author._average_patch_normal_project_m(
        body, mask["selected_face_ids"], inputs["normal_matrix_rows"]
    )
    generated_normal = sealed_author._face_normal_from_positions(faces[0], positions_project_m)
    reverse_winding = float(old_normal.dot(generated_normal)) < 0.0
    if reverse_winding:
        faces = patch_contract.build_quad_topology(reverse_winding=True)
    return {
        "candidate": candidate,
        "positions_project_m": positions_project_m,
        "geometry_evidence": geometry_evidence,
        "faces": faces,
        "reverse_winding": reverse_winding,
        "old_patch_average_normal_project": sealed_author.vector_record(old_normal),
        "first_generated_face_normal_project": sealed_author.vector_record(generated_normal),
        "topology": patch_contract.topology_contract(faces),
        "aggregate_quality": patch_contract.geometry_quality(positions_project_m, faces),
    }


def assert_attempt04_aggregate(
    candidate_id: str,
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> None:
    for key in ("face_count", "degenerate_face_count_at_1e_10_m2"):
        if int(actual[key]) != int(expected[key]):
            raise DiagnosticError(f"{candidate_id} aggregate {key} did not reproduce Attempt04")
    tolerances = {"minimum_face_area_m2": 1.0e-18, "maximum_quad_edge_ratio": 1.0e-12}
    for key, tolerance in tolerances.items():
        if not math.isclose(
            float(actual[key]), float(expected[key]), rel_tol=0.0, abs_tol=tolerance
        ):
            raise DiagnosticError(
                f"{candidate_id} aggregate {key} did not reproduce Attempt04: "
                f"{actual[key]} != {expected[key]}"
            )


def package_manifest(output: Path) -> Path:
    manifest_path = output / "PACKAGE_MANIFEST.json"
    members = []
    for member in sorted(path for path in output.rglob("*") if path.is_file()):
        if member == manifest_path:
            continue
        members.append(
            {
                "path": project_relative(member),
                "sha256": sha256_file(member),
                "size_bytes": member.stat().st_size,
            }
        )
    write_json_exclusive(
        manifest_path,
        {
            "schema_version": 1,
            "status": "READ_ONLY_FACE_QUALITY_DIAGNOSTIC_NO_BODY_MUTATION_NO_BLEND_SAVE",
            "files_excluding_this_manifest": members,
        },
    )
    return manifest_path


def run(config: Mapping[str, Any], paths: Mapping[str, Path]) -> dict[str, Any]:
    output = paths["output"]
    if output.exists():
        raise DiagnosticError(f"append-only diagnostic output already exists: {output}")
    output.mkdir(parents=True, exist_ok=False)
    source_hash_before = sha256_file(paths["source_blend"])
    sealed_author._open_exact_blend(paths["source_blend"])
    author_config = config["_sealed_author_config_value"]
    author_paths = config["_sealed_author_paths_value"]
    body, _rig, preflight, inputs = sealed_author.preflight_scene(author_config, author_paths)
    body_hash_before = sealed_author.mesh_geometry_uv_signature(body)
    inventory_before = sealed_author._object_inventory()

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
        key: sha256_json(value) for key, value in construction_inputs.items()
    }
    seam_source_ids = [int(value) for value in preflight["mask"]["canonical_seam_vertex_ids"]]
    expected_quality = config["expected_attempt_04_quality"]
    records = []
    positions_by_candidate: dict[str, Sequence[Sequence[float]]] = {}
    details_by_candidate: dict[str, Mapping[str, Any]] = {}
    for candidate_id in config["candidate_ids"]:
        geometry = build_exact_candidate_geometry(
            body, preflight["mask"], inputs, str(candidate_id)
        )
        details = quality_diagnostic.detailed_geometry_quality(
            geometry["positions_project_m"],
            geometry["faces"],
            seam_source_ids,
            worst_n=int(config["worst_face_count_per_candidate"]),
            maximum_quad_edge_ratio=float(
                config["maximum_quad_edge_ratio_threshold_unchanged"]
            ),
            coincidence_tolerance_m=float(config["coincidence_tolerance_m"]),
        )
        assert_attempt04_aggregate(
            str(candidate_id), geometry["aggregate_quality"], expected_quality[str(candidate_id)]
        )
        assert_attempt04_aggregate(
            str(candidate_id), details, expected_quality[str(candidate_id)]
        )
        positions_by_candidate[str(candidate_id)] = geometry["positions_project_m"]
        details_by_candidate[str(candidate_id)] = details
        records.append(
            {
                "candidate_id": candidate_id,
                "candidate_parameters": geometry["geometry_evidence"]["candidate"],
                "positions_project_m_sha256": sha256_json(geometry["positions_project_m"]),
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
    comparison = quality_diagnostic.compare_candidate_quality(
        positions_by_candidate[first_id],
        details_by_candidate[first_id],
        positions_by_candidate[second_id],
        details_by_candidate[second_id],
        difference_count=int(config["worst_face_count_per_candidate"]),
    )
    body_hash_after = sealed_author.mesh_geometry_uv_signature(body)
    inventory_after = sealed_author._object_inventory()
    source_hash_after = sha256_file(paths["source_blend"])
    if body_hash_after != body_hash_before:
        raise DiagnosticError("diagnostic changed the source body geometry/UV signature")
    if inventory_after != inventory_before:
        raise DiagnosticError("diagnostic changed the Blender object inventory")
    if source_hash_after != source_hash_before or source_hash_after != config["source_blend_sha256"]:
        raise DiagnosticError("diagnostic changed the immutable R19 source Blend")

    evidence = {
        "schema_version": 1,
        "diagnostic_id": DIAGNOSTIC_ID,
        "timestamp_utc": utc_now(),
        "status": "PASS_READ_ONLY_FACE_QUALITY_DIAGNOSTIC_NO_BODY_MUTATION_NO_BLEND_SAVE",
        "scope": "exact Attempt04 candidate construction before inverse transform or BMesh application",
        "coordinate_space": "project_world_meters",
        "sealed_implementation": {
            "author_worker": assert_hash(
                paths["sealed_author_worker"],
                SEALED_AUTHOR_WORKER_SHA256,
                "sealed author worker",
            ),
            "pure_contract": assert_hash(
                paths["sealed_pure_contract"],
                SEALED_PURE_CONTRACT_SHA256,
                "sealed pure contract",
            ),
            "author_config": assert_hash(
                paths["sealed_author_config"],
                SEALED_AUTHOR_CONFIG_SHA256,
                "sealed author config",
            ),
            "author_tests": assert_hash(
                paths["sealed_author_tests"],
                SEALED_AUTHOR_TESTS_SHA256,
                "sealed author tests",
            ),
            "author_manifest": assert_hash(
                paths["sealed_author_manifest"],
                SEALED_AUTHOR_MANIFEST_SHA256,
                "sealed author manifest",
            ),
        },
        "author_attempt04_evidence": {
            key: assert_hash(paths[key], expected, key)
            for key, expected in AUTHOR_ATTEMPT04_HASHES.items()
        },
        "source_blend": {
            "path": project_relative(paths["source_blend"]),
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
            "object_inventory_sha256_before": sha256_json(inventory_before),
            "object_inventory_sha256_after": sha256_json(inventory_after),
            "object_inventory_unchanged": True,
            "bmesh_imported_or_called_by_diagnostic": False,
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
    write_json_exclusive(evidence_path, evidence)
    checkpoint_path = output / "CHECKPOINT.md"
    write_text_exclusive(
        checkpoint_path,
        "# Kira R20 Author Attempt04 quality diagnostic\n\n"
        "Status: PASS - exact read-only reconstruction; no BMesh application, pose suite, "
        "render, Blend save, or runtime change.\n\n"
        f"- Evidence: `{project_relative(evidence_path)}`\n"
        f"- Evidence SHA-256: `{sha256_file(evidence_path)}`\n"
        f"- Candidate A maximum ratio: `{details_by_candidate[first_id]['maximum_quad_edge_ratio']}`\n"
        f"- Candidate B maximum ratio: `{details_by_candidate[second_id]['maximum_quad_edge_ratio']}`\n"
        f"- Candidate A localization: `{details_by_candidate[first_id]['failure_localization']['classification']}`\n"
        f"- Candidate B localization: `{details_by_candidate[second_id]['failure_localization']['classification']}`\n"
        f"- Immutable R19 source: `{source_hash_after}` (unchanged)\n",
    )
    manifest_path = package_manifest(output)
    return {
        "status": evidence["status"],
        "output": project_relative(output),
        "evidence_sha256": sha256_file(evidence_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "manifest_sha256": sha256_file(manifest_path),
        "source_r19_unchanged": True,
    }


def main() -> int:
    args = parse_args()
    output: Path | None = None
    output_existed_before = True
    try:
        config, paths = validate_config(Path(args.config), args.acknowledge_private_inactive)
        output = paths["output"]
        output_existed_before = output.exists()
        result = run(config, paths)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "diagnostic_id": DIAGNOSTIC_ID,
            "timestamp_utc": utc_now(),
            "status": "FAILED_CLOSED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "body_mutation_or_blend_save_attempted_by_failure_handler": False,
            "runtime_activation_assignment_export_publication": False,
        }
        if output is not None and output.is_dir() and not output_existed_before:
            failure_path = output / "DIAGNOSTIC_FAILURE.json"
            if not failure_path.exists():
                write_json_exclusive(failure_path, failure)
        print(json.dumps(failure, indent=2, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
