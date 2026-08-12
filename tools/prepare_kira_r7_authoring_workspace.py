#!/usr/bin/env python3
"""Prepare and audit the isolated, inactive Kira R7 authoring workspace.

This wrapper deliberately does not export a candidate model, update a runtime
binding, or touch the R6 source.  Blender imports the exact pinned R6 GLB,
creates a protected full-surface baseline plus an unchanged working copy, and
adds empty semantic mask attributes.  Empty masks are intentional: localized
body regions must be selected and reviewed by a human modeler before the
authoring and material gates can open.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "candidate_sources"
    / "kira_adult_body_r7_contract"
    / "r7_build_contract.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "candidate_sources"
    / "kira_adult_body_r7"
    / "workspace_v1"
)
BLENDER_PREP_WORKER = Path(__file__).with_name(
    "blender_prepare_kira_r7_authoring_workspace.py"
)
BLENDER_AUDIT_WORKER = Path(__file__).with_name(
    "blender_audit_kira_r7_authoring_workspace.py"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_blender(explicit: str) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    command = shutil.which("blender")
    if command:
        candidates.append(Path(command))
    foundation = Path(r"C:\Program Files\Blender Foundation")
    if foundation.is_dir():
        candidates.extend(sorted(foundation.glob("Blender */blender.exe"), reverse=True))
    for candidate in candidates:
        candidate = candidate.expanduser().resolve()
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Blender executable was not found")


def run_checked(command: list[str], log_path: Path) -> None:
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path.write_text(completed.stdout or "", encoding="utf-8")
    if completed.returncode != 0:
        tail = "\n".join((completed.stdout or "").splitlines()[-40:])
        raise RuntimeError(
            f"command failed with exit code {completed.returncode}: {command}\n{tail}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare an isolated, inactive Kira R7 Blender authoring workspace."
    )
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--blender", default="")
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Replace only the isolated generated workspace directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract_path = Path(args.contract).resolve(strict=True)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("status") != "contract_only_no_model":
        raise ValueError("R7 contract is not in its required inactive contract-only state")
    truth = contract.get("truth_limits", {})
    if truth.get("runtime_activation_allowed") or truth.get("owner_approved"):
        raise ValueError("R7 contract unexpectedly permits activation or claims approval")

    output_dir = Path(args.output_dir).resolve()
    allowed_root = (
        PROJECT_ROOT
        / "Avatar"
        / "avatar_builder"
        / "candidate_sources"
        / "kira_adult_body_r7"
    ).resolve()
    output_dir.relative_to(allowed_root)
    if output_dir.exists():
        if not args.force_recreate:
            raise FileExistsError(
                f"workspace already exists: {output_dir}; use --force-recreate only if no manual R7 work must be kept"
            )
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)

    r6_record = contract["rollback_inputs"]["current_r6"]
    source_path = (PROJECT_ROOT / r6_record["path"]).resolve(strict=True)
    expected_source_hash = str(r6_record["sha256"]).lower()
    source_hash_before = sha256_file(source_path)
    if source_hash_before != expected_source_hash:
        raise ValueError("exact pinned R6 source SHA-256 does not match the R7 contract")

    blender = find_blender(args.blender)
    workspace_path = output_dir / "kira_r7_authoring_workspace.blend"
    baseline_path = output_dir / "source_baseline.json"
    registry_path = output_dir / "semantic_mask_registry.json"
    prep_manifest_path = output_dir / "workspace_manifest.json"
    audit_path = output_dir / "workspace_audit.json"
    selection_template_path = output_dir / "manual_selection_attestation.template.json"
    config = {
        "schema_version": 1,
        "workspace_id": "kira_r7_authoring_workspace_v1",
        "project_root": str(PROJECT_ROOT),
        "contract_path": str(contract_path),
        "contract_sha256": sha256_file(contract_path),
        "source_model": str(source_path),
        "source_sha256": expected_source_hash,
        "output_dir": str(output_dir),
        "workspace_path": str(workspace_path),
        "baseline_path": str(baseline_path),
        "registry_path": str(registry_path),
        "manifest_path": str(prep_manifest_path),
        "selection_template_path": str(selection_template_path),
        "runtime_activation_requested": False,
        "candidate_export_requested": False,
    }
    config_path = output_dir / "workspace_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    run_checked(
        [
            str(blender),
            "--background",
            "--factory-startup",
            "--python",
            str(BLENDER_PREP_WORKER),
            "--",
            "--config",
            str(config_path),
        ],
        output_dir / "blender_prepare.log",
    )
    if not workspace_path.is_file():
        raise RuntimeError("Blender did not create the isolated R7 workspace")

    run_checked(
        [
            str(blender),
            "--background",
            str(workspace_path),
            "--python",
            str(BLENDER_AUDIT_WORKER),
            "--",
            "--baseline",
            str(baseline_path),
            "--registry",
            str(registry_path),
            "--output",
            str(audit_path),
        ],
        output_dir / "blender_audit.log",
    )

    source_hash_after = sha256_file(source_path)
    if source_hash_after != source_hash_before:
        raise RuntimeError("R6 source changed while preparing R7; refusing result")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if not audit.get("workspace_integrity", {}).get("prepared_baseline_exact"):
        raise RuntimeError("R7 workspace baseline did not pass exact preparation audit")
    if audit.get("gates", {}).get("geometry_authoring_allowed"):
        raise RuntimeError("fresh R7 workspace unexpectedly opened the authoring gate")

    summary = {
        "schema_version": 1,
        "status": "prepared_inactive_workspace_waiting_for_manual_semantic_selection",
        "workspace_id": config["workspace_id"],
        "source_r6": {
            "project_path": r6_record["path"],
            "sha256_before": source_hash_before,
            "sha256_after": source_hash_after,
            "unchanged": source_hash_before == source_hash_after,
        },
        "workspace": {
            "path": str(workspace_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(workspace_path),
            "candidate_model_exported": False,
            "runtime_binding_changed": False,
        },
        "audit": {
            "path": str(audit_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(audit_path),
            "prepared_baseline_exact": True,
            "semantic_masks_populated": False,
            "geometry_authoring_allowed": False,
            "localized_coloration_allowed": False,
            "runtime_activation_allowed": False,
        },
        "first_required_manual_operation": audit["next_required_operation"],
    }
    (output_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
