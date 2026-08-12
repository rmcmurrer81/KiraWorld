#!/usr/bin/env python3
"""Run and seal Kira R7's inactive same-mesh viseme-set v2 review."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import uuid
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
WORKER = PROJECT_ROOT / "tools/blender_author_kira_r7_same_mesh_visemes_v2.py"
VERIFIER = PROJECT_ROOT / "tools/blender_verify_kira_r7_same_mesh_visemes_v2.py"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_same_mesh_viseme_set_v2_20260722"
)
EXPECTED = {
    "workspace": "9d0f9dad39b2e0650419ccef48a7d524d5cd67e4429f1d23ee3398db396c0394",
    "source_r6": "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
}

# Updated only after direct inspection of this exact run's fixed PNGs.  A None
# value keeps that viseme fail-closed and prevents an engineering-pass label.
VISUAL_REVIEW: dict[str, dict[str, object]] = {
    "ah": {"passed": None, "disposition": "pending_fixed_render_review"},
    "o": {"passed": None, "disposition": "pending_fixed_render_review"},
    "ee": {"passed": None, "disposition": "pending_fixed_render_review"},
    "fv": {"passed": None, "disposition": "pending_fixed_render_review"},
    "mbp": {"passed": None, "disposition": "pending_fixed_render_review"},
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


def process_failed(completed: subprocess.CompletedProcess[str]) -> bool:
    return (
        completed.returncode != 0
        or "Traceback (most recent call last)" in completed.stderr
    )


def main() -> int:
    args = parse_args()
    blender = find_blender(args.blender)
    output_dir = Path(args.output_dir).resolve()
    candidate = output_dir / "inactive_candidate" / "kira_r7_same_mesh_visemes_v2.blend"
    evidence_path = output_dir / "topology_and_viseme_evidence.json"
    reopened_path = output_dir / "reopened_candidate_verification.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate.parent.mkdir(parents=True, exist_ok=True)

    pinned = {"workspace": WORKSPACE, "source_r6": SOURCE_R6}
    before = {name: sha256_file(path) for name, path in pinned.items()}
    if before != EXPECTED:
        raise ValueError(f"pinned input mismatch: expected={EXPECTED} actual={before}")
    runtime_before = sha256_file(RUNTIME_STATE) if RUNTIME_STATE.is_file() else None
    run_token = uuid.uuid4().hex

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
        str(candidate),
        "--run-token",
        run_token,
    ]
    completed = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True)
    if (
        process_failed(completed)
        or not evidence_path.is_file()
        or not candidate.is_file()
    ):
        failure = {
            "schema_version": 2,
            "status": "rejected_worker_failed",
            "run_token": run_token,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "gates": {
                "candidate_export_allowed": False,
                "runtime_binding_allowed": False,
                "audio_binding_allowed": False,
                "activation_allowed": False,
                "owner_approved": False,
            },
        }
        (output_dir / "failed_manifest.json").write_text(
            json.dumps(failure, indent=2) + "\n", encoding="utf-8"
        )
        raise RuntimeError(
            f"Blender v2 authoring failed ({completed.returncode})\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("run_token") != run_token:
        raise RuntimeError("worker evidence is stale or belongs to another run")

    verification_command = [
        str(blender),
        "--background",
        str(candidate),
        "--python",
        str(VERIFIER),
        "--",
        "--output",
        str(reopened_path),
        "--expected-run-token",
        run_token,
    ]
    verified = subprocess.run(
        verification_command, cwd=PROJECT_ROOT, text=True, capture_output=True
    )
    if process_failed(verified) or not reopened_path.is_file():
        raise RuntimeError(
            f"reopened v2 verification failed ({verified.returncode})\n"
            f"STDOUT:\n{verified.stdout}\nSTDERR:\n{verified.stderr}"
        )
    reopened = json.loads(reopened_path.read_text(encoding="utf-8"))
    if reopened.get("run_token") != run_token:
        raise RuntimeError("reopened verification belongs to another run")

    after = {name: sha256_file(path) for name, path in pinned.items()}
    runtime_after = sha256_file(RUNTIME_STATE) if RUNTIME_STATE.is_file() else None
    if after != before:
        raise RuntimeError(f"v2 trial changed a pinned input: {before} -> {after}")
    if runtime_after != runtime_before:
        raise RuntimeError("v2 trial changed Kira World runtime state")

    shape_records = {record["role"]: record for record in evidence["shape_keys"]}
    per_viseme: dict[str, dict[str, object]] = {}
    for role, visual in VISUAL_REVIEW.items():
        geometry_passed = bool(evidence["geometry_checks"][role]["passed"])
        visual_passed = visual["passed"] is True
        shape_records[role]["visual_review_disposition"] = visual["disposition"]
        shape_records[role]["visually_distinct_in_fixed_renders"] = visual["passed"]
        per_viseme[role] = {
            "geometry_passed": geometry_passed,
            "visual_passed": visual["passed"],
            "engineering_shape_passed": geometry_passed and visual_passed,
            "disposition": visual["disposition"],
            "runtime_or_export_allowed": False,
        }
    evidence["engineering_verdict"]["visual_review_completed"] = all(
        record["visual_passed"] is not None for record in per_viseme.values()
    )
    evidence["engineering_verdict"]["per_viseme_visual_result"] = {
        role: record["disposition"] for role, record in per_viseme.items()
    }

    all_engineering_shapes_passed = all(
        record["engineering_shape_passed"] for record in per_viseme.values()
    )
    policy = reopened["saved_candidate_policy"]
    safety_passed = bool(
        evidence["topology"]["unchanged"]
        and evidence["hidden_backing"]["deformed_by_any_shape_key"] is False
        and evidence["safety"]["second_mouth_created"] is False
        and evidence["safety"]["runtime_model_exported"] is False
        and evidence["safety"]["runtime_binding_touched"] is False
        and evidence["safety"]["audio_binding_touched"] is False
        and reopened["topology_matches_pinned_r7"] is True
        and reopened["hidden_backing"]["unchanged_in_every_trial_key"] is True
        and policy["inactive_owner_review_only"] is True
        and policy["second_mouth_created"] is False
        and policy["runtime_export_allowed"] is False
        and policy["audio_binding_allowed"] is False
        and policy["live_promotion_allowed"] is False
    )
    if all_engineering_shapes_passed and safety_passed:
        status = "inactive_same_mesh_viseme_v2_engineering_pass_owner_review_pending"
    elif any(record["visual_passed"] is None for record in per_viseme.values()):
        status = "inactive_same_mesh_viseme_v2_fixed_renders_pending_review"
    else:
        status = "inactive_same_mesh_viseme_v2_partial_fail_closed"

    evidence["host_verification"] = {
        "run_token": run_token,
        "blender_path": str(blender),
        "blender_sha256": sha256_file(blender),
        "pinned_hashes_before": before,
        "pinned_hashes_after": after,
        "runtime_state_sha256_before": runtime_before,
        "runtime_state_sha256_after": runtime_after,
        "all_guarded_inputs_byte_unchanged": before == after and runtime_before == runtime_after,
        "candidate_blend_sha256": sha256_file(candidate),
        "reopened_candidate_verification": str(reopened_path),
        "reopened_candidate_verification_sha256": sha256_file(reopened_path),
        "fixed_render_sha256": {
            name: sha256_file(Path(record["path"]))
            for name, record in evidence["fixed_renders"].items()
        },
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": 2,
        "review_id": "kira_r7_same_mesh_viseme_set_v2_20260722",
        "run_token": run_token,
        "status": status,
        "artifacts": {
            "evidence": str(evidence_path),
            "evidence_sha256": sha256_file(evidence_path),
            "candidate_blend": str(candidate),
            "candidate_blend_sha256": sha256_file(candidate),
            "reopened_candidate_verification": str(reopened_path),
            "reopened_candidate_verification_sha256": sha256_file(reopened_path),
            "fixed_render_sha256": evidence["host_verification"]["fixed_render_sha256"],
        },
        "result": {
            "same_existing_face_mesh_only": True,
            "second_mouth_created": False,
            "hidden_backing_deformed": False,
            "topology_changed": False,
            "runtime_or_live_body_changed": False,
            "independent_jaw_control_authored": False,
            "per_viseme": per_viseme,
            "owner_visual_review_pending": True,
        },
        "gates": {
            "candidate_export_allowed": False,
            "runtime_binding_allowed": False,
            "audio_binding_allowed": False,
            "activation_allowed": False,
            "owner_approved": False,
        },
        "guarded_inputs_byte_unchanged": True,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": safety_passed, "status": status, "manifest": str(manifest_path)}, indent=2))
    return 0 if safety_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
