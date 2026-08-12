#!/usr/bin/env python3
"""Nonexecuting preflight for R23 Attempt05 fresh-reopen attempt 02.

This ordinary-Python check binds the exact-root bootstrap, unchanged verifier,
Attempt 01 failure, candidate, evidence, and new append-only output paths.  It
cannot start Blender, open or save a Blend, render, or create verification
output.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt05_postsave_fresh_reopen_attempt02_preparation"
)
CONFIG_PATH = PACKAGE / (
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT05_POSTSAVE_FRESH_REOPEN_ATTEMPT02_CONFIG.json"
)
MANIFEST_PATH = PACKAGE / "PACKAGE_MANIFEST.json"
BOOTSTRAP_PATH = ROOT / "tools/blender_bootstrap_kira_r23_attempt05_fresh_reopen.py"
WORKER_PATH = ROOT / "tools/blender_verify_kira_r23_postsave_fresh_reopen.py"
ATTEMPT01_CONFIG_PATH = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt05_postsave_fresh_reopen_preparation/"
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT05_POSTSAVE_FRESH_REOPEN_CONFIG.json"
)
ZSTD_MAGIC = bytes.fromhex("28b52ffd")


class Attempt02PreparationError(RuntimeError):
    """Fail-closed preparation error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Attempt02PreparationError(f"JSON root is not an object: {path}")
    return value


def project_path(raw: str) -> Path:
    value = PurePosixPath(raw.replace("\\", "/"))
    if value.is_absolute() or not value.parts or any(
        part in {"", ".", ".."} for part in value.parts
    ):
        raise Attempt02PreparationError(f"unsafe project path: {raw}")
    path = ROOT.joinpath(*value.parts)
    try:
        path.resolve(strict=path.exists()).relative_to(ROOT.resolve())
    except ValueError as exc:
        raise Attempt02PreparationError(f"path escapes project root: {raw}") from exc
    return path


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def is_reparse(path: Path) -> bool:
    try:
        return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except AttributeError:
        return path.is_symlink()


def verify_binding(binding: Mapping[str, Any], label: str) -> dict[str, Any]:
    if set(binding) != {"path", "bytes", "sha256"}:
        raise Attempt02PreparationError(f"binding closure drifted: {label}")
    path = project_path(str(binding["path"]))
    if not path.is_file() or is_reparse(path):
        raise Attempt02PreparationError(f"binding absent/nonregular/reparse: {label}")
    actual = {
        "path": relative(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if actual["bytes"] != int(binding["bytes"]) or actual["sha256"] != str(
        binding["sha256"]
    ):
        raise Attempt02PreparationError(f"binding drifted: {label}")
    return actual


def load_module(path: Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Attempt02PreparationError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_attempt01_failure(config: Mapping[str, Any]) -> dict[str, Any]:
    contract = config["attempt01_failure_preservation"]
    directory = project_path(contract["directory"])
    if not directory.is_dir() or is_reparse(directory):
        raise Attempt02PreparationError("Attempt 01 failure directory absent/reparse")
    actual_entries = sorted(entry.name for entry in directory.iterdir())
    if actual_entries != sorted(contract["exact_entries"]):
        raise Attempt02PreparationError("Attempt 01 failure closure drifted")
    owner_renders = directory / "owner_renders"
    if not owner_renders.is_dir() or is_reparse(owner_renders):
        raise Attempt02PreparationError("Attempt 01 owner_renders closure drifted")
    if list(owner_renders.iterdir()):
        raise Attempt02PreparationError("Attempt 01 owner_renders is no longer empty")
    failure_path = directory / "FAILURE_EVIDENCE.json"
    failure = verify_binding(
        {
            "path": relative(failure_path),
            **contract["failure_evidence"],
        },
        "Attempt 01 failure evidence",
    )
    record = read_json(failure_path)
    if (
        record.get("exception_type") != "ModuleNotFoundError"
        or record.get("exception") != "No module named 'tools'"
        or "line 1018" not in str(record.get("traceback"))
        or record.get("candidate_remains_inactive_private_and_unapproved") is not True
        or record.get("source_before") != record.get("source_current")
        or record.get("candidate_before") != record.get("candidate_current")
    ):
        raise Attempt02PreparationError("Attempt 01 failure semantics drifted")
    return {
        "binding": failure,
        "exact_entries": actual_entries,
        "owner_renders_empty": True,
        "failed_before_source_or_candidate_open": True,
        "source_and_candidate_unchanged": True,
    }


def verify_bootstrap(config: Mapping[str, Any]) -> dict[str, Any]:
    binding = config["fixed_inputs"]["attempt02_exact_root_bootstrap"]
    verified = verify_binding(binding, "Attempt 02 exact-root bootstrap")
    module = load_module(BOOTSTRAP_PATH, "_r23_attempt02_exact_root_bootstrap")
    root = module.exact_project_root()
    if root != ROOT.resolve():
        raise Attempt02PreparationError("bootstrap derived root is not exact project root")
    original = sys.path[:]
    sentinel = ["ATTEMPT02_SENTINEL_A", str(ROOT.parent), "ATTEMPT02_SENTINEL_B"]
    try:
        sys.path[:] = sentinel
        module.install_exact_project_root(root)
        observed = sys.path[:]
    finally:
        sys.path[:] = original
    if observed != [str(ROOT.resolve()), *sentinel]:
        raise Attempt02PreparationError(
            f"bootstrap broadened or altered sys.path unexpectedly: {observed}"
        )
    worker = module.verified_worker(root)
    contract = config["bootstrap_contract"]
    if (
        relative(worker) != contract["unchanged_worker_path"]
        or module.WORKER_BYTES != contract["unchanged_worker_bytes"]
        or module.WORKER_SHA256 != contract["unchanged_worker_sha256"]
        or contract["expected_project_root"] != ROOT.as_posix()
        or contract["only_exact_project_root_may_be_added_to_sys_path"] is not True
        or contract["ambient_pythonpath_dependency_forbidden"] is not True
        or contract["bootstrap_performs_no_blend_open_save_render_export_activation_assignment_publication_or_output_write"] is not True
    ):
        raise Attempt02PreparationError("bootstrap contract drifted")
    return {
        **verified,
        "exact_project_root": ROOT.as_posix(),
        "only_added_sys_path_entry": str(ROOT.resolve()),
        "ambient_pythonpath_read_or_required": False,
        "unchanged_worker_verified": True,
    }


def verify_same_gates(config: Mapping[str, Any]) -> dict[str, Any]:
    previous = read_json(ATTEMPT01_CONFIG_PATH)
    exact_sections = (
        "candidate_binding", "build_evidence_binding", "container_preflight",
        "blender_identity", "source_candidate_immutability_contract",
        "boundary_semantics_contract", "objects", "inherited_r19_baseline",
        "expected_candidate_structure", "frozen_r19_ledgers",
        "continuity_thresholds", "poses", "owner_render_plan",
        "owner_visual_judgment",
    )
    checks = {section: config[section] == previous[section] for section in exact_sections}
    checks["machine_gates"] = config["machine_gates"][2:] == previous["machine_gates"]
    checks["truth_boundary"] = config["truth_boundary"][2:] == previous["truth_boundary"]
    checks["execution_original_keys"] = all(
        config["execution"].get(key) == value
        for key, value in previous["execution"].items()
    )
    checks["original_fixed_inputs"] = all(
        config["fixed_inputs"].get(key) == value
        for key, value in previous["fixed_inputs"].items()
    )
    if not all(checks.values()):
        raise Attempt02PreparationError(f"Attempt 01 verifier gates drifted: {checks}")
    return checks


def verify_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    manifest = read_json(MANIFEST_PATH)
    if manifest.get("artifact_kind") != (
        "KIRA_R23_ATTEMPT05_POSTSAVE_FRESH_REOPEN_ATTEMPT02_PREPARATION"
    ):
        raise Attempt02PreparationError("wrong manifest kind")
    rows = manifest.get("artifacts")
    if not isinstance(rows, list) or not rows:
        raise Attempt02PreparationError("manifest artifacts absent")
    paths = [row.get("path") for row in rows]
    if len(paths) != len(set(paths)):
        raise Attempt02PreparationError("manifest paths duplicate")
    verified = {row["path"]: verify_binding(row, f"manifest/{row['path']}") for row in rows}
    required = {
        relative(CONFIG_PATH),
        relative(BOOTSTRAP_PATH),
        config["fixed_inputs"]["fresh_reopen_worker"]["path"],
        config["fixed_inputs"]["attempt01_failure_evidence"]["path"],
    }
    if not required.issubset(verified):
        raise Attempt02PreparationError("manifest omits a required bound artifact")
    return {"artifact_count": len(verified), "artifacts": verified}


def future_command(config: Mapping[str, Any]) -> list[str]:
    execution = config["execution"]
    if execution.get("executed_during_preparation") is not False:
        raise Attempt02PreparationError("preparation execution truth drifted")
    return [
        str(Path(config["blender_identity"]["path"])),
        "--background", "--factory-startup", "--disable-autoexec",
        "--python", str(BOOTSTRAP_PATH.resolve()), "--", "--config",
        relative(CONFIG_PATH), execution["required_cli_flag"],
    ]


def preflight() -> dict[str, Any]:
    config = read_json(CONFIG_PATH)
    worker = load_module(WORKER_PATH, "_r23_attempt02_unchanged_worker")
    paths = worker.validate_bound_contract(config, explicit_execution=True)
    fixed_inputs = worker.verify_fixed_inputs(config)
    worker.verify_build_evidence_binding(config, paths)
    with paths["candidate"].open("rb") as stream:
        magic = stream.read(4)
    if magic != ZSTD_MAGIC or config["container_preflight"]["does_not_establish_blend_validity"] is not True:
        raise Attempt02PreparationError("candidate preliminary container evidence drifted")
    failure = verify_attempt01_failure(config)
    bootstrap = verify_bootstrap(config)
    same_gates = verify_same_gates(config)
    manifest = verify_manifest(config)
    if paths["evidence_dir"].exists() or paths["render_dir"].exists():
        raise Attempt02PreparationError("Attempt 02 append-only output path already exists")
    command = future_command(config)
    return {
        "status": "ATTEMPT02_BOUND_PREFLIGHT_PASS_BLENDER_NOT_RUN_VALIDITY_NOT_ESTABLISHED",
        "config": {
            "path": relative(CONFIG_PATH),
            "bytes": CONFIG_PATH.stat().st_size,
            "sha256": sha256_file(CONFIG_PATH),
        },
        "attempt01_failure_preserved": failure,
        "bootstrap": bootstrap,
        "same_worker_and_verification_gates": same_gates,
        "fixed_inputs": fixed_inputs,
        "package_manifest": manifest,
        "candidate_magic_hex": magic.hex(),
        "blend_validity_established": False,
        "fresh_blender_reopen_required": True,
        "future_command": command,
        "blender_invoked": False,
        "render_performed": False,
        "verification_output_created": False,
        "source_or_candidate_modified": False,
        "activation_export_publication_performed": False,
    }


def main() -> int:
    print(json.dumps(preflight(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
