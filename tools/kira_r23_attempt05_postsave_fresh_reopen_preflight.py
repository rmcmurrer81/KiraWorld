#!/usr/bin/env python3
"""Nonexecuting preflight for the bound R23 Attempt05 fresh-reopen package.

This ordinary-Python program never starts Blender.  It verifies the exact
candidate/evidence/source/tool bindings, recognizes the bound candidate's
Zstandard magic only as preliminary container evidence, proves the append-only
verification paths are absent, and prints the future explicit Blender command.
Only that future fresh Blender reopen can establish Blend validity.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import stat
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
PREPARATION_DIRECTORY = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt05_postsave_fresh_reopen_preparation"
)
CONFIG_PATH = PREPARATION_DIRECTORY / (
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT05_POSTSAVE_FRESH_REOPEN_CONFIG.json"
)
MANIFEST_PATH = PREPARATION_DIRECTORY / "PACKAGE_MANIFEST.json"
WORKER_PATH = ROOT / "tools/blender_verify_kira_r23_postsave_fresh_reopen.py"
WORKER_BYTES = 55260
WORKER_SHA256 = "5dbf4faaef09a82717989f5e7bc17312d5182b0042e39475aa5b47f131f3a1b5"
ZSTD_MAGIC = bytes.fromhex("28b52ffd")


class FreshReopenPreparationError(RuntimeError):
    """Fail-closed nonexecuting preparation error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FreshReopenPreparationError(f"JSON root is not an object: {path}")
    return value


def project_path(raw: str) -> Path:
    value = PurePosixPath(raw.replace("\\", "/"))
    if value.is_absolute() or not value.parts or any(
        part in {"", ".", ".."} for part in value.parts
    ):
        raise FreshReopenPreparationError(f"unsafe project path: {raw}")
    path = ROOT.joinpath(*value.parts)
    try:
        path.resolve(strict=path.exists()).relative_to(ROOT.resolve())
    except ValueError as exc:
        raise FreshReopenPreparationError(f"path escapes project root: {raw}") from exc
    return path


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def is_reparse(path: Path) -> bool:
    try:
        return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except AttributeError:
        return path.is_symlink()


def require_regular_no_reparse(path: Path, label: str) -> None:
    if not path.is_file() or is_reparse(path):
        raise FreshReopenPreparationError(f"{label} is absent/nonregular/reparse")
    cursor = path.parent
    while True:
        if is_reparse(cursor):
            raise FreshReopenPreparationError(f"{label} has a reparse ancestor")
        if cursor.resolve() == ROOT.resolve():
            break
        cursor = cursor.parent


def verify_binding(binding: Mapping[str, Any], label: str) -> dict[str, Any]:
    if set(binding) != {"path", "bytes", "sha256"}:
        raise FreshReopenPreparationError(f"binding field closure drifted: {label}")
    path = project_path(str(binding["path"]))
    require_regular_no_reparse(path, label)
    actual = {
        "path": relative(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if actual["bytes"] != int(binding["bytes"]) or actual["sha256"] != str(
        binding["sha256"]
    ):
        raise FreshReopenPreparationError(f"binding drifted: {label}")
    return actual


def verify_preserved(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for section in config["preserved_append_only_evidence"]:
        directory = project_path(section["directory"])
        if not directory.is_dir() or is_reparse(directory):
            raise FreshReopenPreparationError(
                f"preserved directory is absent/reparse: {section['label']}"
            )
        actual = sorted(entry.name for entry in directory.iterdir())
        expected = sorted(section["files"])
        if actual != expected:
            raise FreshReopenPreparationError(
                f"preserved directory closure drifted: {section['label']}"
            )
        rows = {}
        for name, binding in section["files"].items():
            rows[name] = verify_binding(
                {
                    "path": f"{section['directory']}/{name}",
                    "bytes": binding["bytes"],
                    "sha256": binding["sha256"],
                },
                f"{section['label']}/{name}",
            )
        verified.append(
            {"label": section["label"], "directory": relative(directory), "files": rows}
        )
    return verified


def load_worker() -> types.ModuleType:
    require_regular_no_reparse(WORKER_PATH, "fresh reopen worker")
    if WORKER_PATH.stat().st_size != WORKER_BYTES or sha256_file(WORKER_PATH) != WORKER_SHA256:
        raise FreshReopenPreparationError("fresh reopen worker drifted")
    spec = importlib.util.spec_from_file_location("_r23_fresh_reopen_worker", WORKER_PATH)
    if spec is None or spec.loader is None:
        raise FreshReopenPreparationError("cannot load fresh reopen worker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def candidate_container_preflight(
    config: Mapping[str, Any], candidate_path: Path
) -> dict[str, Any]:
    with candidate_path.open("rb") as stream:
        observed = stream.read(4)
    contract = config["container_preflight"]
    if observed != ZSTD_MAGIC or observed.hex() != contract["expected_magic_hex"]:
        raise FreshReopenPreparationError(
            f"candidate container magic differs: {observed.hex()}"
        )
    if (
        contract.get("preliminary_format_evidence_only") is not True
        or contract.get("does_not_establish_blend_validity") is not True
        or contract.get("does_not_replace_fresh_blender_reopen") is not True
    ):
        raise FreshReopenPreparationError("Zstandard truth boundary was weakened")
    return {
        "observed_magic_hex": observed.hex(),
        "classification": contract["classification"],
        "preliminary_format_evidence_only": True,
        "blend_validity_established": False,
        "fresh_blender_reopen_still_required": True,
        "required_validity_gate": contract["required_validity_gate"],
    }


def verify_topology_expectation_binding(
    config: Mapping[str, Any], build_evidence: Mapping[str, Any]
) -> dict[str, Any]:
    evidence_topology = build_evidence["topology"]
    whole = evidence_topology["whole_body"]
    patch = evidence_topology["replacement_patch"]
    expected = config["expected_candidate_structure"]
    semantics = config["boundary_semantics_contract"]
    stable = evidence_topology["stable_boundary_preservation"]
    greater_than_two = evidence_topology["greater_than_two_face_nonmanifold"]
    loose = evidence_topology["loose_edges"]
    checks = {
        "vertices": whole["vertex_count"] == expected["body_vertices"],
        "edges": whole["edge_count"] == expected["body_edges"],
        "faces": whole["face_count"] == expected["body_faces"],
        "components": whole["component_count"] == expected["whole_body_components"],
        "boundary_edges": whole["boundary_edge_count"]
        == expected["whole_body_boundary_edges"],
        "boundary_cycles": whole["boundary_cycle_count"]
        == expected["whole_body_boundary_cycles"],
        "boundary_cycle_lengths": whole["boundary_cycle_lengths"]
        == expected["whole_body_boundary_cycle_lengths"],
        "patch_vertices": patch["vertex_count"]
        == expected["replacement_patch_vertices"],
        "patch_edges": patch["edge_count"] == expected["replacement_patch_edges"],
        "patch_faces": patch["face_count"] == expected["replacement_patch_faces"],
    }
    topology_checks = build_evidence["topology"]["checks"]
    checks["zero_greater_than_two_face_edges"] = topology_checks[
        "zero_greater_than_two_face_edges"
    ] is True
    checks["zero_loose_mesh_edges"] = topology_checks["zero_loose_mesh_edges"] is True
    semantics_checks = {
        "inherited_edge_count": stable["source_count"]
        == semantics["whole_body_source_inherited_boundary_edge_count"],
        "candidate_edge_count": stable["final_count"]
        == semantics["whole_body_source_inherited_boundary_edge_count"],
        "inherited_cycle_count": whole["boundary_cycle_count"]
        == semantics["whole_body_source_inherited_boundary_cycle_count"],
        "inherited_cycle_lengths": whole["boundary_cycle_lengths"]
        == semantics["whole_body_source_inherited_boundary_cycle_lengths"],
        "stable_source_sha256": stable["source_sha256"]
        == semantics["stable_source_boundary_sha256"],
        "stable_candidate_sha256": stable["final_sha256"]
        == semantics["stable_candidate_boundary_sha256"],
        "zero_new_whole_body_boundaries": stable["new_count"]
        == semantics["new_whole_body_boundary_edge_count"]
        == 0,
        "zero_missing_whole_body_boundaries": stable["missing_count"]
        == semantics["missing_whole_body_boundary_edge_count"]
        == 0,
        "zero_greater_than_two_face_edges": greater_than_two["final_count"]
        == semantics["greater_than_two_face_edge_count"]
        == 0,
        "zero_loose_edges": loose["final_count"]
        == semantics["loose_mesh_edge_count"]
        == 0,
        "patch_subset_interface": patch["boundary_edge_count"]
        == patch["boundary_cycle_lengths"][0]
        == semantics["replacement_patch_subset_interface_vertex_count"]
        == 91,
        "patch_subset_not_whole_body_boundary": semantics[
            "replacement_patch_subset_interface_is_not_a_whole_body_open_boundary"
        ]
        is True,
        "rejected_patch_seam_not_allowed": semantics[
            "rejected_pelvic_patch_seam_as_new_whole_body_boundary_allowed"
        ]
        is False,
        "no_unsupported_anatomical_classification": semantics[
            "inherited_boundaries_may_correspond_to_preexisting_body_openings_but_are_not_individually_anatomically_classified_by_this_package"
        ]
        is True,
        "fresh_reopen_rechecks_all_seam_and_intersection_gates": semantics[
            "fresh_reopen_must_recheck_seam_position_normal_tangent_uv_weight_and_intersection_gates"
        ]
        is True,
    }
    if not all(checks.values()):
        raise FreshReopenPreparationError(
            f"bound candidate topology expectation drifted: {checks}"
        )
    if not all(semantics_checks.values()):
        raise FreshReopenPreparationError(
            f"boundary semantics contract drifted: {semantics_checks}"
        )
    return {
        "checks": checks,
        "boundary_semantics_checks": semantics_checks,
        "source_preserved_boundary_not_closed_whole_body": True,
        "inherited_whole_body_boundaries_are_not_individually_classified": True,
        "replacement_patch_subset_interface_is_not_a_whole_body_open_boundary": True,
        "rejected_pelvic_patch_seam_as_new_whole_body_boundary_allowed": False,
        "fresh_reopen_rechecks_seam_continuity_and_intersections": True,
        "boundary_edge_count": whole["boundary_edge_count"],
        "boundary_cycle_count": whole["boundary_cycle_count"],
        "stable_boundary_sha256": stable["final_sha256"],
        "new_boundary_edge_count": stable["new_count"],
        "missing_boundary_edge_count": stable["missing_count"],
        "replacement_patch_subset_interface_vertex_count": patch[
            "boundary_edge_count"
        ],
    }


def future_command(config: Mapping[str, Any]) -> list[str]:
    execution = config["execution"]
    if execution.get("executed_during_preparation") is not False:
        raise FreshReopenPreparationError("preparation execution truth drifted")
    return [
        str(Path(config["blender_identity"]["path"])),
        "--background",
        "--factory-startup",
        "--disable-autoexec",
        "--python",
        str(WORKER_PATH.resolve()),
        "--",
        "--config",
        relative(CONFIG_PATH),
        execution["required_cli_flag"],
    ]


def verify_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    manifest = read_json(MANIFEST_PATH)
    if manifest.get("artifact_kind") != (
        "KIRA_R23_ATTEMPT05_POSTSAVE_FRESH_REOPEN_BOUND_PREPARATION"
    ):
        raise FreshReopenPreparationError("wrong package manifest kind")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise FreshReopenPreparationError("package manifest artifacts absent")
    paths = [str(row.get("path")) for row in artifacts]
    if len(paths) != len(set(paths)):
        raise FreshReopenPreparationError("package manifest paths duplicate")
    verified = {}
    for row in artifacts:
        verified[row["path"]] = verify_binding(row, f"manifest/{row['path']}")
    config_path = relative(CONFIG_PATH)
    if config_path not in verified:
        raise FreshReopenPreparationError("manifest does not bind the bound config")
    worker_binding = config["fixed_inputs"]["fresh_reopen_worker"]
    if worker_binding["path"] not in verified:
        raise FreshReopenPreparationError("manifest does not bind the existing worker")
    return {"artifact_count": len(verified), "artifacts": verified}


def preflight() -> dict[str, Any]:
    config = read_json(CONFIG_PATH)
    worker = load_worker()
    paths = worker.validate_bound_contract(config, explicit_execution=True)
    fixed = worker.verify_fixed_inputs(config)
    build_evidence = worker.verify_build_evidence_binding(config, paths)
    candidate = verify_binding(config["candidate_binding"], "candidate")
    evidence = verify_binding(config["build_evidence_binding"], "build evidence")
    preserved = verify_preserved(config)
    container = candidate_container_preflight(config, paths["candidate"])
    topology = verify_topology_expectation_binding(config, build_evidence)
    manifest = verify_manifest(config)
    command = future_command(config)
    if paths["evidence_dir"].exists() or paths["render_dir"].exists():
        raise FreshReopenPreparationError("append-only verification output already exists")
    blender = Path(config["blender_identity"]["path"])
    if not blender.is_file():
        raise FreshReopenPreparationError("sealed Blender executable is absent")
    if (
        blender.stat().st_size != int(config["blender_identity"]["bytes"])
        or sha256_file(blender) != config["blender_identity"]["sha256"]
    ):
        raise FreshReopenPreparationError("sealed Blender executable drifted")
    return {
        "status": "BOUND_PREFLIGHT_PASS_BLENDER_NOT_RUN_VALIDITY_NOT_ESTABLISHED",
        "config": {
            "path": relative(CONFIG_PATH),
            "bytes": CONFIG_PATH.stat().st_size,
            "sha256": sha256_file(CONFIG_PATH),
        },
        "candidate": candidate,
        "build_evidence": evidence,
        "fixed_inputs": fixed,
        "preserved_append_only_evidence": preserved,
        "container_preflight": container,
        "topology_expectation_binding": topology,
        "package_manifest": manifest,
        "future_command": command,
        "blender_invoked": False,
        "render_performed": False,
        "source_or_candidate_modified": False,
        "verification_output_created": False,
        "activation_export_publication_performed": False,
    }


def main() -> int:
    print(json.dumps(preflight(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
