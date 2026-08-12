#!/usr/bin/env python3
"""Run a strictly inactive adult-body retarget feasibility trial for Kira.

This launcher pins both source files, invokes Blender in an isolated evidence
folder, then verifies that neither source changed.  The Blender worker may save
only a diagnostic Blend file.  It never exports a GLB or changes a live/avatar
binding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KIRA_SOURCE = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6"
    / "r6_20260718_163658/kira_provisional_body_r6.glb"
)
REFERENCE_SOURCE = Path(r"C:\Users\robmc\Desktop\5\base_female_character.glb")
NECK_EVIDENCE = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_neck_boundary_owner_review_20260721/evidence.json"
)
OUTPUT_DIR = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_adult_retarget_gate_20260721"
)
WORKER = Path(__file__).with_name("blender_inspect_kira_r7_adult_retarget_gate.py")
EXPECTED_HASHES = {
    "kira_r6": "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
    "adult_reference": "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_blender(explicit: str | None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    command = shutil.which("blender")
    if command:
        candidates.append(Path(command))
    candidates.extend(
        sorted(
            Path(r"C:\Program Files\Blender Foundation").glob(
                "Blender */blender.exe"
            ),
            reverse=True,
        )
    )
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_file():
            return resolved
    raise FileNotFoundError("Blender executable was not found")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    blender = find_blender(args.blender)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    pinned_before = {
        "kira_r6": sha256_file(KIRA_SOURCE),
        "adult_reference": sha256_file(REFERENCE_SOURCE),
    }
    if pinned_before != EXPECTED_HASHES:
        raise ValueError(f"pinned source hash mismatch: {pinned_before}")

    neck = json.loads(NECK_EVIDENCE.read_text(encoding="utf-8"))
    if neck["conclusion"]["defensible_existing_closed_neck_ring_count"] != 0:
        raise ValueError("neck evidence no longer matches the pinned blocker")

    config = {
        "schema_version": 1,
        "run_id": "kira_r7_adult_retarget_gate_20260721",
        "mode": "inactive_disposable_retarget_diagnostic",
        "project_root": str(PROJECT_ROOT),
        "kira_source": str(KIRA_SOURCE),
        "kira_sha256": EXPECTED_HASHES["kira_r6"],
        "reference_source": str(REFERENCE_SOURCE),
        "reference_sha256": EXPECTED_HASHES["adult_reference"],
        "neck_evidence": str(NECK_EVIDENCE),
        "neck_evidence_sha256": sha256_file(NECK_EVIDENCE),
        "output_dir": str(output_dir),
        "evidence": str(output_dir / "evidence.json"),
        "diagnostic_blend": str(output_dir / "inactive_retarget_diagnostic.blend"),
        "candidate_glb_export_requested": False,
        "live_binding_change_requested": False,
        "reference_provenance": {
            "title": "Base Female Character",
            "author": "BlackProject",
            "license": "CC BY 4.0",
            "source": "https://sketchfab.com/3d-models/ec7445f61d9e499186578b8ef4814b6a",
        },
    }
    config_path = output_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    command = [
        str(blender),
        "--background",
        "--factory-startup",
        "--python",
        str(WORKER),
        "--",
        "--config",
        str(config_path),
    ]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    (output_dir / "blender.log").write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(
            f"Blender diagnostic failed ({completed.returncode}); see "
            f"{output_dir / 'blender.log'}"
        )

    pinned_after = {
        "kira_r6": sha256_file(KIRA_SOURCE),
        "adult_reference": sha256_file(REFERENCE_SOURCE),
    }
    if pinned_after != pinned_before:
        raise RuntimeError("a pinned source changed during the diagnostic")

    evidence_path = output_dir / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    artifacts = {}
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name not in {"evidence.json", "manifest.json"}:
            artifacts[path.name] = {
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
    evidence["host_verification"] = {
        "blender": str(blender),
        "blender_returncode": completed.returncode,
        "pinned_hashes_before": pinned_before,
        "pinned_hashes_after": pinned_after,
        "all_pinned_inputs_byte_unchanged": pinned_before == pinned_after,
        "artifacts": artifacts,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "review_id": config["run_id"],
        "status": evidence["decision"]["status"],
        "mode": config["mode"],
        "evidence": str(evidence_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "diagnostic_blend": str(
            (output_dir / "inactive_retarget_diagnostic.blend").relative_to(PROJECT_ROOT)
        ).replace("\\", "/"),
        "candidate_glb_created": False,
        "candidate_export_allowed": False,
        "avatar_builder_binding_allowed": False,
        "runtime_activation_allowed": False,
        "owner_approved": False,
        "adult_anatomy_proven": False,
        "stable_79_joint_deformation_proven": False,
        "source_hashes": pinned_after,
        "truth_note": (
            "The Blend is a failed-gate diagnostic containing only an isolated, "
            "attributed retarget trial. It is not Kira's body and cannot be bound, "
            "activated, or presented as an adult-avatar candidate."
        ),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"ok": True, "evidence": str(evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
