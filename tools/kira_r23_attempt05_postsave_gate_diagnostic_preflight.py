#!/usr/bin/env python3
"""Nonexecuting preflight for the bound R23 post-save gate diagnostic."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt05_postsave_gate_diagnostic_preparation"
)
CONFIG_PATH = PACKAGE / "KIRA_R23_ATTEMPT05_POSTSAVE_GATE_DIAGNOSTIC_CONFIG.json"
MANIFEST_PATH = PACKAGE / "PACKAGE_MANIFEST.json"
WORKER_PATH = ROOT / "tools/blender_diagnose_kira_r23_attempt05_postsave_gates.py"
BOOTSTRAP_PATH = ROOT / (
    "tools/blender_bootstrap_kira_r23_attempt05_postsave_gate_diagnostic.py"
)
VERIFIER_PATH = ROOT / "tools/blender_verify_kira_r23_postsave_fresh_reopen.py"


class DiagnosticPreparationError(RuntimeError):
    """Fail-closed nonexecuting preflight error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DiagnosticPreparationError(f"JSON root is not an object: {path}")
    return value


def project_path(raw: str) -> Path:
    value = PurePosixPath(raw.replace("\\", "/"))
    if value.is_absolute() or not value.parts or any(
        part in {"", ".", ".."} for part in value.parts
    ):
        raise DiagnosticPreparationError(f"unsafe project path: {raw}")
    path = ROOT.joinpath(*value.parts)
    try:
        path.resolve(strict=path.exists()).relative_to(ROOT.resolve())
    except ValueError as exc:
        raise DiagnosticPreparationError(f"path escapes project root: {raw}") from exc
    return path


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def verify_binding(binding: Mapping[str, Any], label: str) -> dict[str, Any]:
    if set(binding) != {"path", "bytes", "sha256"}:
        raise DiagnosticPreparationError(f"binding closure drifted: {label}")
    path = project_path(str(binding["path"]))
    if not path.is_file() or path.is_symlink():
        raise DiagnosticPreparationError(f"binding absent/nonregular/linked: {label}")
    actual = {
        "path": relative(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if actual["bytes"] != int(binding["bytes"]) or actual["sha256"] != str(
        binding["sha256"]
    ):
        raise DiagnosticPreparationError(f"binding drifted: {label}")
    return actual


def load_module(path: Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DiagnosticPreparationError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = qualified_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def verify_worker_contract(config: Mapping[str, Any]) -> dict[str, Any]:
    verified = verify_binding(config["tool_bindings"]["diagnostic_worker"], "diagnostic worker")
    source = WORKER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {
        qualified_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    required_helpers = {
        "verifier.source_snapshot",
        "verifier.exact_intersections",
        "verifier.seam_continuity",
        "verifier.deformation_series",
        "verifier.uv_values_at_vertex",
        "verifier.weight_map",
        "verifier.weight_error",
        "verifier.write_new_json",
    }
    missing = sorted(required_helpers.difference(calls))
    if missing:
        raise DiagnosticPreparationError(f"unchanged helper reuse missing: {missing}")
    forbidden_calls = {
        "verifier.run",
        "verifier.render_owner_package",
        "verifier.configure_render_scene",
        "bpy.ops.render.render",
        "bpy.ops.wm.save_as_mainfile",
        "bpy.ops.wm.save_mainfile",
        "bpy.ops.export_scene",
    }
    observed_forbidden = sorted(forbidden_calls.intersection(calls))
    if observed_forbidden:
        raise DiagnosticPreparationError(
            f"diagnostic worker contains forbidden call: {observed_forbidden}"
        )
    if "subprocess" in source:
        raise DiagnosticPreparationError("diagnostic worker contains process launching")
    return {
        **verified,
        "required_unchanged_helpers": sorted(required_helpers),
        "forbidden_calls_observed": observed_forbidden,
        "render_save_export_activation_calls_present": False,
    }


def verify_bootstrap(config: Mapping[str, Any]) -> dict[str, Any]:
    verified = verify_binding(config["tool_bindings"]["exact_root_bootstrap"], "bootstrap")
    module = load_module(BOOTSTRAP_PATH, "_r23_gate_diagnostic_bootstrap")
    root = module.exact_project_root()
    if root != ROOT.resolve():
        raise DiagnosticPreparationError("bootstrap root drifted")
    original = sys.path[:]
    sentinel = ["DIAGNOSTIC_SENTINEL_A", str(ROOT.parent), "DIAGNOSTIC_SENTINEL_B"]
    try:
        sys.path[:] = sentinel
        module.install_exact_project_root(root)
        observed = sys.path[:]
    finally:
        sys.path[:] = original
    if observed != [str(ROOT.resolve()), *sentinel]:
        raise DiagnosticPreparationError("bootstrap broadened sys.path beyond exact root")
    if module.verified_worker(root) != WORKER_PATH.resolve():
        raise DiagnosticPreparationError("bootstrap does not bind exact diagnostic worker")
    return {
        **verified,
        "exact_project_root": ROOT.as_posix(),
        "only_added_sys_path_entry": str(ROOT.resolve()),
        "ambient_pythonpath_required": False,
        "diagnostic_worker_verified": True,
    }


def verify_attempt02_preservation(config: Mapping[str, Any], worker: Any, verifier: Any) -> dict[str, Any]:
    failure = worker.verify_attempt02_failure(config, verifier)
    contract = config["attempt02_failure_preservation"]
    expected = {
        "candidate_flags": True,
        "structure": True,
        "intersections": False,
        "continuity": False,
        "weights": True,
        "frozen_ledgers": True,
        "retained_surface": True,
        "deformation": False,
    }
    if contract["pre_render_gate_groups"] != expected:
        raise DiagnosticPreparationError("Attempt 02 gate record drifted")
    directory = project_path(contract["directory"])
    if sorted(entry.name for entry in directory.iterdir()) != sorted(
        contract["exact_entries"]
    ):
        raise DiagnosticPreparationError("Attempt 02 directory closure drifted")
    if list((directory / "owner_renders").iterdir()):
        raise DiagnosticPreparationError("Attempt 02 render directory is no longer empty")
    return {
        "failure_sha256": config["attempt02_failure_binding"]["sha256"],
        "failure_exception": failure["exception"],
        "exact_entries": sorted(contract["exact_entries"]),
        "owner_renders_empty": True,
        "source_and_candidate_unchanged": True,
    }


def verify_metric_contract(config: Mapping[str, Any], verification: Mapping[str, Any]) -> dict[str, Any]:
    contract = config["metric_capture_contract"]
    required_true = [key for key, value in contract.items() if key != "reuse_unchanged_verifier_helpers" and value is True]
    if len(required_true) != len(contract) - 1:
        raise DiagnosticPreparationError("metric capture contract contains weakened value")
    exact_pose_ids = [pose["id"] for pose in verification["poses"]]
    if len(exact_pose_ids) != 11 or len(exact_pose_ids) != len(set(exact_pose_ids)):
        raise DiagnosticPreparationError("exact verification pose closure drifted")
    thresholds = verification["continuity_thresholds"]
    expected_thresholds = {
        "maximum_seam_position_error_m": 1e-8,
        "maximum_seam_weight_error": 1e-8,
        "minimum_seam_tangent_dot": 0.999999,
        "minimum_patch_retained_normal_dot": 0.7,
        "maximum_patch_retained_uv_distance": 0.002,
        "maximum_pose_seam_edge_stretch_ratio": 1.2,
        "maximum_pose_patch_edge_stretch_ratio": 1.35,
        "maximum_new_exact_intersection_pairs_per_pose": 0,
        "maximum_patch_involving_exact_intersection_pairs": 0,
        "contact_plane_tolerance_m": 0.025,
    }
    if thresholds != expected_thresholds:
        raise DiagnosticPreparationError("acceptance thresholds drifted")
    return {
        "all_contract_requirements_true": True,
        "exact_pose_ids": exact_pose_ids,
        "unchanged_thresholds": thresholds,
    }


def verify_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    manifest = read_json(MANIFEST_PATH)
    if manifest.get("artifact_kind") != "KIRA_R23_ATTEMPT05_POSTSAVE_GATE_DIAGNOSTIC_PREPARATION":
        raise DiagnosticPreparationError("wrong package manifest kind")
    rows = manifest.get("artifacts")
    if not isinstance(rows, list) or not rows:
        raise DiagnosticPreparationError("manifest artifacts absent")
    paths = [row.get("path") for row in rows]
    if len(paths) != len(set(paths)):
        raise DiagnosticPreparationError("manifest paths duplicate")
    verified = {row["path"]: verify_binding(row, f"manifest/{row['path']}") for row in rows}
    required = {
        relative(CONFIG_PATH),
        relative(WORKER_PATH),
        relative(BOOTSTRAP_PATH),
        config["verification_config_binding"]["path"],
        config["attempt02_failure_binding"]["path"],
        config["tool_bindings"]["unchanged_fresh_reopen_verifier"]["path"],
    }
    if not required.issubset(verified):
        raise DiagnosticPreparationError("manifest omits a required bound artifact")
    return {"artifact_count": len(verified), "artifacts": verified}


def future_command(config: Mapping[str, Any]) -> list[str]:
    if config["execution"].get("executed_during_preparation") is not False:
        raise DiagnosticPreparationError("execution truth drifted")
    return [
        str(Path(config["blender_identity"]["path"])),
        "--background", "--factory-startup", "--disable-autoexec",
        "--python", str(BOOTSTRAP_PATH.resolve()), "--", "--config",
        relative(CONFIG_PATH), config["execution"]["required_cli_flag"],
    ]


def preflight() -> dict[str, Any]:
    config = read_json(CONFIG_PATH)
    worker = load_module(WORKER_PATH, "_r23_gate_diagnostic_worker")
    verifier = load_module(VERIFIER_PATH, "_r23_gate_diagnostic_verifier")
    try:
        worker.validate_contract(config, False, verifier)
    except worker.DiagnosticError:
        explicit_flag_required = True
    else:
        raise DiagnosticPreparationError("diagnostic accepts missing explicit flag")
    contract = worker.validate_contract(config, True, verifier)
    verification = verifier.read_json(contract["verification_config_path"])
    fixed_inputs = verifier.verify_fixed_inputs(verification)
    candidate = verifier.require_binding(verification["candidate_binding"], "candidate")
    build_evidence = verifier.require_binding(
        verification["build_evidence_binding"], "build evidence"
    )
    verifier.verify_build_evidence_binding(
        verification, {"build_evidence": build_evidence}
    )
    with candidate.open("rb") as stream:
        candidate_magic = stream.read(4)
    if candidate_magic != bytes.fromhex("28b52ffd"):
        raise DiagnosticPreparationError("candidate preliminary container magic drifted")
    worker_contract = verify_worker_contract(config)
    bootstrap = verify_bootstrap(config)
    attempt02 = verify_attempt02_preservation(config, worker, verifier)
    metrics = verify_metric_contract(config, verification)
    manifest = verify_manifest(config)
    output = contract["output_directory"]
    if output.exists():
        raise DiagnosticPreparationError("append-only diagnostic output exists")
    return {
        "status": "BOUND_DIAGNOSTIC_PREFLIGHT_PASS_BLENDER_NOT_RUN_OUTPUT_NOT_CREATED",
        "config": {
            "path": relative(CONFIG_PATH),
            "bytes": CONFIG_PATH.stat().st_size,
            "sha256": sha256_file(CONFIG_PATH),
        },
        "explicit_flag_required": explicit_flag_required,
        "worker_contract": worker_contract,
        "bootstrap": bootstrap,
        "attempt02_failure_preserved": attempt02,
        "metric_capture_contract": metrics,
        "fixed_inputs": fixed_inputs,
        "candidate_sha256": verification["candidate_binding"]["sha256"],
        "source_sha256": verification["fixed_inputs"]["r19_source_blend"]["sha256"],
        "package_manifest": manifest,
        "future_command": future_command(config),
        "blender_invoked": False,
        "render_performed": False,
        "diagnostic_output_created": False,
        "source_or_candidate_modified": False,
        "activation_export_publication_performed": False,
    }


def main() -> int:
    print(json.dumps(preflight(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
