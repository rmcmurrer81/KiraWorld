#!/usr/bin/env python3
"""Run and seal Kira R7's inactive visible-lip/viseme authoring trial."""

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
WORKER = PROJECT_ROOT / "tools/blender_author_kira_r7_visible_lip_visemes.py"
VERIFIER = PROJECT_ROOT / "tools/blender_verify_kira_r7_visible_lip_candidate.py"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_visible_lip_viseme_trial_20260722"
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
    candidate_dir = output_dir / "inactive_candidate"
    candidate_blend = candidate_dir / "kira_r7_visible_lip_viseme_trial.blend"
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir.mkdir(parents=True, exist_ok=True)

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
        "--candidate-blend",
        str(candidate_blend),
    ]
    completed = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True)
    evidence_path = output_dir / "topology_and_shape_key_evidence.json"
    failure = (
        completed.returncode != 0
        or "Traceback (most recent call last)" in completed.stderr
        or not evidence_path.is_file()
        or not candidate_blend.is_file()
    )
    if failure:
        failed = {
            "schema_version": 1,
            "review_id": "kira_r7_visible_lip_viseme_trial_20260722",
            "status": "rejected_worker_failed",
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "gates": {
                "candidate_export_allowed": False,
                "runtime_binding_allowed": False,
                "activation_allowed": False,
                "owner_approved": False,
            },
        }
        (output_dir / "failed_manifest.json").write_text(
            json.dumps(failed, indent=2) + "\n", encoding="utf-8"
        )
        raise RuntimeError(
            f"Blender authoring trial failed ({completed.returncode})\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )

    reopened_verification_path = output_dir / "reopened_candidate_verification.json"
    verification_command = [
        str(blender),
        "--background",
        str(candidate_blend),
        "--python",
        str(VERIFIER),
        "--",
        "--output",
        str(reopened_verification_path),
    ]
    verification = subprocess.run(
        verification_command, cwd=PROJECT_ROOT, text=True, capture_output=True
    )
    verification_failed = (
        verification.returncode != 0
        or "Traceback (most recent call last)" in verification.stderr
        or not reopened_verification_path.is_file()
    )
    if verification_failed:
        raise RuntimeError(
            f"reopened candidate verification failed ({verification.returncode})\n"
            f"STDOUT:\n{verification.stdout}\nSTDERR:\n{verification.stderr}"
        )
    reopened_verification = json.loads(
        reopened_verification_path.read_text(encoding="utf-8")
    )

    after = {name: sha256_file(path) for name, path in pinned.items()}
    runtime_after = sha256_file(RUNTIME_STATE) if RUNTIME_STATE.is_file() else None
    if after != before:
        raise RuntimeError(f"trial changed a pinned input: before={before} after={after}")
    if runtime_after != runtime_before:
        raise RuntimeError("trial changed Kira World runtime state")

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
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
        "reopened_candidate_verification": str(reopened_verification_path),
        "reopened_candidate_verification_sha256": sha256_file(
            reopened_verification_path
        ),
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    open_gap = evidence["center_separation"]["KW_VISIBLE_LIP_OPEN_REVIEW"][
        "vertical_separation_m"
    ]
    basis_gap = evidence["center_separation"]["Basis"]["vertical_separation_m"]
    engineering_pass = bool(
        evidence["topology"]["unchanged"]
        and evidence["visible_lip_rim_proof"]["overlaps_hidden_backing"] is False
        and evidence["visible_lip_rim_proof"][
            "all_consecutive_path_edges_are_single_use_mesh_boundaries"
        ]
        and open_gap - basis_gap >= 0.045
        and evidence["safety"]["second_mouth_created"] is False
        and evidence["safety"]["runtime_binding_touched"] is False
        and evidence["engineering_verdict"]["o_viseme_final_quality_proven"] is False
        and reopened_verification["topology_matches_pinned_r7"] is True
        and reopened_verification["hidden_backing"][
            "unchanged_in_every_trial_key"
        ]
        is True
        and reopened_verification["saved_candidate_policy"][
            "inactive_owner_review_only"
        ]
        is True
        and reopened_verification["saved_candidate_policy"][
            "second_mouth_created"
        ]
        is False
        and reopened_verification["saved_candidate_policy"][
            "runtime_export_allowed"
        ]
        is False
    )
    status = (
        "inactive_same_mesh_visible_motion_engineering_pass_owner_review_pending"
        if engineering_pass
        else "rejected_visible_motion_not_proven"
    )
    manifest = {
        "schema_version": 1,
        "review_id": "kira_r7_visible_lip_viseme_trial_20260722",
        "status": status,
        "artifacts": {
            "evidence": str(evidence_path),
            "evidence_sha256": sha256_file(evidence_path),
            "candidate_blend": str(candidate_blend),
            "candidate_blend_sha256": sha256_file(candidate_blend),
            "reopened_candidate_verification": str(reopened_verification_path),
            "reopened_candidate_verification_sha256": sha256_file(
                reopened_verification_path
            ),
            "fixed_render_sha256": render_hashes,
        },
        "result": {
            "same_existing_face_mesh_shape_keys_authored": engineering_pass,
            "visible_open_shape_proven": engineering_pass,
            "o_viseme_final_quality_proven": False,
            "o_viseme_disposition": (
                "provisional_shape_not_visually_distinct_enough_for_final_o"
            ),
            "second_mouth_created": False,
            "hidden_backing_deformed": False,
            "topology_changed": False,
            "runtime_or_live_body_changed": False,
            "owner_visual_review_pending": True,
        },
        "gates": {
            "candidate_export_allowed": False,
            "runtime_binding_allowed": False,
            "activation_allowed": False,
            "owner_approved": False,
        },
        "guarded_inputs_byte_unchanged": True,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": engineering_pass, "manifest": str(manifest_path)}, indent=2))
    return 0 if engineering_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
