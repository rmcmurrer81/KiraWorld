#!/usr/bin/env python3
"""Run Kira R7's inactive existing-mouth semantic review safely."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_adult_body_r7/workspace_v1"
    / "kira_r7_authoring_workspace.blend"
)
SOURCE_R6 = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6"
    / "r6_20260718_163658/kira_provisional_body_r6.glb"
)
RUNTIME_STATE = PROJECT_ROOT / "Data/runtime/kira_world_shell_state.json"
WORKER = PROJECT_ROOT / "tools/blender_review_kira_r7_mouth_semantics.py"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_existing_mouth_semantic_review_20260721"
)
EXPECTED = {
    "workspace": "9d0f9dad39b2e0650419ccef48a7d524d5cd67e4429f1d23ee3398db396c0394",
    "source_r6": "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_blender(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve(strict=True)
    candidates = sorted(
        Path("C:/Program Files/Blender Foundation").glob("Blender */blender.exe"),
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("Blender executable was not found")
    return candidates[0].resolve(strict=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    blender = find_blender(args.blender)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    pinned = {"workspace": WORKSPACE, "source_r6": SOURCE_R6}
    before = {name: sha256_file(path) for name, path in pinned.items()}
    if before != EXPECTED:
        raise ValueError(f"pinned input mismatch: expected={EXPECTED} actual={before}")
    runtime_before = sha256_file(RUNTIME_STATE) if RUNTIME_STATE.is_file() else None
    command = [
        str(blender),
        "--background",
        str(WORKSPACE),
        "--python",
        str(WORKER),
        "--",
        "--output-dir",
        str(output_dir),
    ]
    completed = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True)
    evidence_path = output_dir / "semantic_review_evidence.json"
    if completed.returncode or "Traceback (most recent call last)" in completed.stderr or not evidence_path.is_file():
        raise RuntimeError(
            f"Blender review failed ({completed.returncode})\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    after = {name: sha256_file(path) for name, path in pinned.items()}
    runtime_after = sha256_file(RUNTIME_STATE) if RUNTIME_STATE.is_file() else None
    if after != before:
        raise RuntimeError(f"review changed a pinned input: before={before} after={after}")
    if runtime_after != runtime_before:
        raise RuntimeError("review changed Kira World runtime state")

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["host_verification"] = {
        "blender_path": str(blender),
        "blender_sha256": sha256_file(blender),
        "pinned_hashes_before": before,
        "pinned_hashes_after": after,
        "runtime_state_sha256_before": runtime_before,
        "runtime_state_sha256_after": runtime_after,
        "all_guarded_inputs_byte_unchanged": before == after and runtime_before == runtime_after,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    render_hashes = {
        name: sha256_file(Path(record["path"]))
        for name, record in evidence["fixed_renders"].items()
    }
    manifest = {
        "schema_version": 1,
        "review_id": "kira_r7_existing_mouth_semantic_review_20260721",
        "status": "inactive_semantic_map_rejected_component_identity_unproven",
        "artifacts": {
            "evidence": str(evidence_path),
            "evidence_sha256": sha256_file(evidence_path),
            "fixed_render_sha256": render_hashes,
        },
        "result": {
            "existing_single_mouth_preserved": True,
            "second_mouth_or_exterior_overlay_created": False,
            "geometry_cut_or_edited": False,
            "geometric_partition_saved_only_as_rejected_json_diagnostic": True,
            "defensible_semantic_map_proven": False,
            "isolated_cavity_or_viseme_prototype_created": False,
        },
        "gates": {
            "geometry_authoring_allowed": False,
            "candidate_export_allowed": False,
            "runtime_binding_allowed": False,
            "activation_allowed": False,
            "owner_approved": False,
        },
        "guarded_inputs_byte_unchanged": True,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "manifest": str(manifest_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
