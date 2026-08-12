#!/usr/bin/env python3
"""Run and seal the inactive Kira R7 five-viseme authoring pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = PROJECT_ROOT / "Avatar/avatar_builder/candidate_sources/kira_adult_body_r7/workspace_v1/kira_r7_authoring_workspace.blend"
SOURCE_R6 = PROJECT_ROOT / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6/r6_20260718_163658/kira_provisional_body_r6.glb"
RUNTIME_STATE = PROJECT_ROOT / "Data/runtime/kira_world_shell_state.json"
WORKER = PROJECT_ROOT / "tools/blender_author_kira_r7_visible_lip_visemes_v2.py"
VERIFIER = PROJECT_ROOT / "tools/blender_verify_kira_r7_visible_lip_candidate_v2.py"
DEFAULT_OUTPUT = PROJECT_ROOT / "Data/avatar_builder_workspace_tests/kira_r7_visible_lip_viseme_trial_v2_20260722"
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
    candidates = sorted(Path("C:/Program Files/Blender Foundation").glob("Blender */blender.exe"), reverse=True)
    if not candidates:
        raise FileNotFoundError("Blender executable was not found")
    return candidates[0].resolve(strict=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def run_checked(command: list[str], label: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True)
    if completed.returncode != 0 or "Traceback (most recent call last)" in completed.stderr:
        raise RuntimeError(
            f"{label} failed ({completed.returncode})\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return completed


def main() -> int:
    args = parse_args()
    blender = find_blender(args.blender)
    output_dir = Path(args.output_dir).resolve()
    candidate_blend = output_dir / "inactive_candidate/kira_r7_visible_lip_viseme_trial_v2.blend"
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_blend.parent.mkdir(parents=True, exist_ok=True)

    pinned = {"workspace": WORKSPACE, "source_r6": SOURCE_R6}
    before = {name: sha256_file(path) for name, path in pinned.items()}
    if before != EXPECTED:
        raise ValueError(f"pinned input mismatch: expected={EXPECTED} actual={before}")
    runtime_before = sha256_file(RUNTIME_STATE) if RUNTIME_STATE.is_file() else None

    run_checked([
        str(blender), "--background", str(WORKSPACE), "--python", str(WORKER), "--",
        "--output-dir", str(output_dir), "--candidate-blend", str(candidate_blend),
    ], "five-viseme authoring")
    evidence_path = output_dir / "topology_and_shape_key_evidence.json"
    if not evidence_path.is_file() or not candidate_blend.is_file():
        raise RuntimeError("authoring did not produce the evidence and inactive candidate")

    reopened_path = output_dir / "reopened_candidate_verification.json"
    run_checked([
        str(blender), "--background", str(candidate_blend), "--python", str(VERIFIER), "--",
        "--output", str(reopened_path),
    ], "read-only reopen verification")

    after = {name: sha256_file(path) for name, path in pinned.items()}
    runtime_after = sha256_file(RUNTIME_STATE) if RUNTIME_STATE.is_file() else None
    if after != before:
        raise RuntimeError(f"authoring changed a pinned input: {before} -> {after}")
    if runtime_after != runtime_before:
        raise RuntimeError("authoring changed Kira World runtime state")

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    reopened = json.loads(reopened_path.read_text(encoding="utf-8"))
    render_hashes = {
        name: sha256_file(Path(record["path"]))
        for name, record in evidence["fixed_renders"].items()
    }
    evidence["host_verification"] = {
        "blender_path": str(blender),
        "blender_sha256": sha256_file(blender),
        "pinned_hashes_before": before,
        "pinned_hashes_after": after,
        "runtime_state_sha256_before": runtime_before,
        "runtime_state_sha256_after": runtime_after,
        "all_guarded_inputs_byte_unchanged": before == after and runtime_before == runtime_after,
        "candidate_blend_sha256": sha256_file(candidate_blend),
        "fixed_render_sha256": render_hashes,
        "reopened_candidate_verification": str(reopened_path),
        "reopened_candidate_verification_sha256": sha256_file(reopened_path),
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    engineering_pass = bool(
        evidence["topology"]["unchanged"]
        and evidence["hidden_backing"]["deformed_by_any_shape_key"] is False
        and evidence["safety"]["second_mouth_created"] is False
        and reopened["topology_matches_pinned_r7"] is True
        and reopened["hidden_backing"]["unchanged_in_every_trial_key"] is True
        and all(record["value_on_reopen"] == 0.0 for record in reopened["shape_keys"])
        and reopened["saved_candidate_policy"]["inactive_owner_review_only"] is True
        and reopened["saved_candidate_policy"]["runtime_export_allowed"] is False
    )
    manifest = {
        "schema_version": 2,
        "review_id": "kira_r7_visible_lip_viseme_trial_v2_20260722",
        "status": (
            "inactive_geometry_authored_individual_visemes_require_fixed_render_review"
            if engineering_pass else "rejected_engineering_guard_failed"
        ),
        "artifacts": {
            "evidence": str(evidence_path),
            "evidence_sha256": sha256_file(evidence_path),
            "candidate_blend": str(candidate_blend),
            "candidate_blend_sha256": sha256_file(candidate_blend),
            "reopened_candidate_verification": str(reopened_path),
            "reopened_candidate_verification_sha256": sha256_file(reopened_path),
            "fixed_render_sha256": render_hashes,
        },
        "result": {
            "same_existing_welded_mouth_keys_authored": engineering_pass,
            "individual_visual_quality_proven": False,
            "visual_review_artifact_pending": True,
            "second_mouth_created": False,
            "hidden_backing_deformed": False,
            "topology_changed": False,
            "runtime_or_live_body_changed": False,
        },
        "gates": {
            "candidate_export_allowed": False,
            "runtime_binding_allowed": False,
            "activation_allowed": False,
            "owner_approved": False,
        },
        "guarded_inputs_byte_unchanged": before == after and runtime_before == runtime_after,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": engineering_pass, "manifest": str(manifest_path)}, indent=2))
    return 0 if engineering_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
