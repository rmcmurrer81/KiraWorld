#!/usr/bin/env python3
"""Run and seal Kira's inactive R7 adult external-surface authoring trial.

This launcher is deliberately fail-closed.  It pins the exact R6 Kira source,
the attributed adult reference, the neck-boundary evidence, and Kira World's
inactive runtime state.  Blender may write only to the isolated review folder;
no GLB candidate, avatar binding, or runtime state is produced.
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
RUNTIME_STATE = PROJECT_ROOT / "Data/runtime/kira_world_shell_state.json"
WORKER = PROJECT_ROOT / "tools/blender_author_kira_r7_adult_surface_trial.py"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_adult_surface_trial_20260722"
    / "rest_preserving_weight_transfer_r2"
)
REPORT = PROJECT_ROOT / "Data/codex_reports/20260722_kira_r7_adult_surface_trial.md"
EXPECTED_HASHES = {
    "kira_r6": "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
    "adult_reference": "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df",
    "neck_evidence": "f0c4d0eb9e58a42a3ff156d22aa9b66a64210354bc924abe7f2d106d14ceeace",
}
RUN_ID = "kira_r7_adult_surface_trial_20260722_rest_preserving_r2"


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
            Path(r"C:\Program Files\Blender Foundation").glob("Blender */blender.exe"),
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
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def inactive_runtime_snapshot() -> dict[str, object]:
    raw = RUNTIME_STATE.read_bytes()
    state = json.loads(raw.decode("utf-8"))
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "active_candidate": state.get("active_candidate"),
        "active_conversation_mode": state.get("active_conversation_mode"),
        "location": state.get("location"),
    }


def render_rows(evidence: dict[str, object]) -> str:
    rows = []
    for label, filename in evidence["renders"].items():
        rows.append(f"- `{label}`: `{filename}`")
    return "\n".join(rows)


def write_report(
    evidence: dict[str, object],
    manifest_path: Path,
    output_dir: Path,
) -> None:
    topology = evidence["topology"]
    weights = evidence["weights"]
    gates = evidence["gates"]
    correction = evidence["landmark_correction"]
    poses = evidence["pose_gate_results"]
    decision = evidence["decision"]
    report = f"""# Kira R7 inactive adult-surface trial — 2026-07-22

## Outcome

**Rejected, with no candidate, no live binding, and no promotion.**

The corrected-pelvis, rest-preserving weight-transfer trial produced useful
engineering evidence, but it did not prove a cohesive identity-preserving Kira
surface with complete adult topology.  The exact R6 head is present only as a
cyan isolated reference overlay in two fixed renders; it is not fused to the
adult-reference body.  Kira World's runtime remained inactive and byte
unchanged throughout the run.

Decision: `{decision['status']}`

The earlier sibling R1 evidence folder is superseded: a unit-scale helper was
mistaken for Kira's floor landmark, visibly stretching its legs.  R2 derives
the floor only from the exact dominant R6 body mesh (`Cuerpo__0`, 57,745
vertices).

## What was corrected

- Rejected landmark: `{correction['rejected_old_landmark']}`
- Correct adult pelvis: `{correction['correct_anatomical_pelvis']}`
- Upper-body scale: `{correction['upper_body_scale']}`
- Lower-body scale: `{correction['lower_body_scale']}`
- Skin contract: original pre-R6 light untextured tone `#e6c0a9`
- Adult-reference face, eyes, mouth, hair, and other identity meshes were
  excluded.  No source material or texture was copied.

## Measured gates

- Body topology: {topology['vertices']} vertices, {topology['polygons']} polygons,
  {topology['connected_components']} connected component(s),
  {topology['boundary_connected_parts']} boundary part(s),
  {topology['boundary_closed_cycle_count']} closed boundary cycle(s), and
  {topology['overused_edge_count']} overused edge(s).
- Weight transfer: {weights['weighted_vertex_count']} / {weights['vertex_count']}
  vertices weighted; {weights['unweighted_vertex_count']} unweighted;
  maximum {weights['maximum_positive_groups_per_vertex']} positive groups per
  vertex; invalid target groups: `{weights['invalid_target_groups']}`.
- Fixed pose gates: `{poses}`.
- Cohesive topology passed: `{gates['cohesive_body_surface_topology_passed']}`.
- Exact 79-joint weights passed: `{gates['exact_79_joint_weight_transfer_passed']}`.
- Fixed-pose deformation passed: `{gates['stable_fixed_pose_deformation_passed']}`.
- Identity joined: `{gates['identity_head_preserved_and_joined']}`.
- Complete adult topology proven: `{gates['complete_adult_topology_proven']}`.

## Why promotion remains blocked

The pinned neck audit found no defensible existing closed neck ring on Kira R6.
A geometric plane cut is not an approved semantic identity seam.  Separate
reference body parts, adult labeling, genital geometry, a silhouette, or a
successful rig pose do not by themselves prove complete adult topology.  These
truth limits are intentionally stronger than visual appearance.

## Fixed review evidence

{render_rows(evidence)}

Review Blend: `{relative(output_dir / 'inactive_body_surface_trial.blend')}`

Evidence: `{relative(output_dir / 'evidence.json')}`

Manifest: `{relative(manifest_path)}`

## Safety state

- No GLB candidate was created.
- No Avatar Builder record or body binding was changed.
- No live Kira body was changed.
- Runtime activation is not allowed for this trial.
- Owner visual approval is still false.
- The source GLBs, neck evidence, and runtime-state file remained byte unchanged.
"""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")


def main() -> int:
    args = parse_args()
    blender = find_blender(args.blender)
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(
            f"refusing to overwrite non-empty review directory: {output_dir}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    source_paths = {
        "kira_r6": KIRA_SOURCE,
        "adult_reference": REFERENCE_SOURCE,
        "neck_evidence": NECK_EVIDENCE,
    }
    before = {name: sha256_file(path) for name, path in source_paths.items()}
    if before != EXPECTED_HASHES:
        raise ValueError(f"pinned source hash mismatch: expected={EXPECTED_HASHES} actual={before}")
    neck = json.loads(NECK_EVIDENCE.read_text(encoding="utf-8"))
    if neck["conclusion"]["defensible_existing_closed_neck_ring_count"] != 0:
        raise ValueError("pinned neck blocker changed")
    runtime_before = inactive_runtime_snapshot()
    if runtime_before["active_candidate"] not in (None, ""):
        raise RuntimeError("Kira World must be inactive before this isolated trial")

    review_blend = output_dir / "inactive_body_surface_trial.blend"
    config = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "mode": "inactive_rest_preserving_exact_79_weight_transfer_trial",
        "project_root": str(PROJECT_ROOT),
        "kira_source": str(KIRA_SOURCE),
        "kira_sha256": EXPECTED_HASHES["kira_r6"],
        "reference_source": str(REFERENCE_SOURCE),
        "reference_sha256": EXPECTED_HASHES["adult_reference"],
        "neck_evidence": str(NECK_EVIDENCE),
        "neck_evidence_sha256": EXPECTED_HASHES["neck_evidence"],
        "output_dir": str(output_dir),
        "review_blend": str(review_blend),
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
    log_path = output_dir / "blender.log"
    log_path.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        failure = {
            "schema_version": 1,
            "review_id": RUN_ID,
            "status": "rejected_worker_failed_no_candidate",
            "returncode": completed.returncode,
            "command": command,
            "candidate_glb_created": False,
            "candidate_export_allowed": False,
            "live_binding_changed": False,
            "runtime_activation_allowed": False,
        }
        (output_dir / "failed_manifest.json").write_text(
            json.dumps(failure, indent=2) + "\n", encoding="utf-8"
        )
        raise RuntimeError(
            f"Blender trial failed ({completed.returncode}); see {log_path}"
        )

    after = {name: sha256_file(path) for name, path in source_paths.items()}
    runtime_after = inactive_runtime_snapshot()
    if after != before:
        raise RuntimeError("a pinned source changed during the authoring trial")
    if runtime_after != runtime_before:
        raise RuntimeError("Kira World runtime state changed during the authoring trial")
    if runtime_after["active_candidate"] not in (None, ""):
        raise RuntimeError("Kira World became active during the isolated trial")

    evidence_path = output_dir / "evidence.json"
    if not evidence_path.is_file() or not review_blend.is_file():
        raise RuntimeError("Blender completed without the required evidence artifacts")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    artifacts = {}
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name not in {"evidence.json", "manifest.json"}:
            artifacts[path.name] = {
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
    evidence["host_verification"] = {
        "blender_path": str(blender),
        "blender_sha256": sha256_file(blender),
        "blender_returncode": completed.returncode,
        "pinned_hashes_before": before,
        "pinned_hashes_after": after,
        "runtime_state_before": runtime_before,
        "runtime_state_after": runtime_after,
        "all_guarded_inputs_byte_unchanged": before == after and runtime_before == runtime_after,
        "artifacts": artifacts,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "review_id": RUN_ID,
        "status": evidence["decision"]["status"],
        "mode": config["mode"],
        "artifacts": {
            "evidence": relative(evidence_path),
            "evidence_sha256": sha256_file(evidence_path),
            "inactive_review_blend": relative(review_blend),
            "inactive_review_blend_sha256": sha256_file(review_blend),
            "fixed_renders": {
                name: {
                    "path": relative(output_dir / filename),
                    "sha256": sha256_file(output_dir / filename),
                }
                for name, filename in evidence["renders"].items()
            },
        },
        "gates": evidence["gates"],
        "candidate_glb_created": False,
        "candidate_export_allowed": False,
        "avatar_builder_binding_changed": False,
        "avatar_builder_promotion_allowed": False,
        "live_body_changed": False,
        "runtime_state_changed": False,
        "runtime_activation_allowed": False,
        "owner_approved": False,
        "complete_adult_topology_proven": False,
        "identity_head_joined": False,
        "source_hashes": after,
        "truth_note": (
            "This is an inactive rejected authoring trial. The adult body and exact "
            "Kira R6 head reference remain separate. No candidate, binding, promotion, "
            "live body, or runtime activation was created."
        ),
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_report(evidence, manifest_path, output_dir)
    print(
        json.dumps(
            {
                "ok": True,
                "status": manifest["status"],
                "manifest": str(manifest_path),
                "report": str(REPORT),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
