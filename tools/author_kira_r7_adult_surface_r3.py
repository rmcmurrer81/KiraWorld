#!/usr/bin/env python3
"""Run and seal Kira's inactive R7 measured-neck R3 review.

The launcher pins the complete R2 parent artifact set and Kira World's
inactive state, invokes Blender only inside a new isolated folder, reopens the
saved Blend in a second Blender process, and withholds every candidate/live
operation regardless of the engineering result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARENT_DIR = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests/kira_r7_adult_surface_trial_20260722"
    / "rest_preserving_weight_transfer_r2"
)
PARENT_ARTIFACTS = {
    "r2_blend": PARENT_DIR / "inactive_body_surface_trial.blend",
    "r2_evidence": PARENT_DIR / "evidence.json",
    "r2_manifest": PARENT_DIR / "manifest.json",
}
EXPECTED_PARENT_HASHES = {
    "r2_blend": "aa501555be754236f63a47af9c84e1a2867acd7a13980a4740da0973a34e6db6",
    "r2_evidence": "f3f43858e375b128b4b43f11cb74fc5e8524a9630235d40c225c99e2b8fd07fd",
    "r2_manifest": "2da63c5dfc752877513f09bc4b9ba85c2a0b8c5d4c82d7893959c4caaab6e55f",
}
RUNTIME_STATE = PROJECT_ROOT / "Data/runtime/kira_world_shell_state.json"
WORKER = PROJECT_ROOT / "tools/blender_author_kira_r7_adult_surface_r3.py"
VERIFIER = PROJECT_ROOT / "tools/blender_verify_kira_r7_adult_surface_r3.py"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests/kira_r7_adult_surface_trial_20260722"
    / "measured_neck_bridge_r3"
)
REPORT = PROJECT_ROOT / "Data/codex_reports/20260722_kira_r7_adult_surface_r3.md"
RUN_ID = "kira_r7_adult_surface_measured_neck_bridge_r3_20260722"


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
    candidates.extend(sorted(Path(r"C:\Program Files\Blender Foundation").glob("Blender */blender.exe"), reverse=True))
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


def runtime_snapshot() -> dict[str, object]:
    raw = RUNTIME_STATE.read_bytes()
    state = json.loads(raw.decode("utf-8"))
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "active_candidate": state.get("active_candidate"),
        "active_conversation_mode": state.get("active_conversation_mode"),
        "location": state.get("location"),
    }


def run_process(command: list[str], log_path: Path) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path.write_text(completed.stdout, encoding="utf-8")
    return completed


def write_report(evidence: dict[str, object], manifest_path: Path, output_dir: Path) -> None:
    gates = evidence["gates"]
    bridge = evidence["bridge"]
    identity = evidence["identity_preservation"]
    topology = evidence["topology"]
    weights = evidence["weights"]
    squat = evidence["deformation"]["bilateral_squat"]["metrics"]["edge_stretch_ratio"]
    render_lines = "\n".join(f"- `{name}`: `{filename}`" for name, filename in evidence["renders"].items())
    report = f"""# Kira R7 inactive measured-neck bridge R3 — 2026-07-22

## Outcome

**Inactive review artifact created; still rejected for candidate, binding, activation, and promotion.**

R3 created one measured triangulated bridge between the R2 adult external
surface and a fresh copy of Kira's exact R6 head geometry. The retained R6
head vertices, including the existing face and mouth surface, were copied
without smoothing or positional edits. The artifact retains the original
light untextured skin contract `#e6c0a9`.

This does **not** prove complete adult topology or internal anatomy. Kira's
exact R6 eye sockets remain open because eyes are a separate inactive task,
and lip sync is not claimed here. Owner visual approval remains false.

Decision: `{evidence['decision']['status']}`

## Measured construction

- Body ring: {bridge['body_ring_vertices']} vertices.
- Exact-head cut ring: {bridge['head_ring_vertices']} vertices at `{evidence['head_cut']['cut_z_m']:.9f} m`.
- Bridge: {bridge['bridge_triangles']} triangles; expected invariant: {bridge['expected_bridge_triangles']}.
- Exact retained R6 head coordinate delta: `{identity['retained_exact_r6_head_maximum_coordinate_delta_m']}` m.
- Exact retained head coordinate digests match: `{identity['head_coordinate_digest_before'] == identity['head_coordinate_digest_after']}`.
- Unified topology: {topology['vertices']} vertices, {topology['polygons']} polygons,
  {topology['connected_components']} component(s), {topology['boundary_closed_cycle_count']}
  remaining boundary cycle(s), {topology['overused_edge_count']} overused edge(s),
  and {topology['degenerate_face_count_under_1e_12_m2']} degenerate face(s).
- Neck boundary remaining: `False` under the measured neck-band audit.

## Rig and fixed poses

- Defined target groups: {weights['defined_vertex_group_count']} (the exact R6 cage has 79 joints).
- Weighted vertices: {weights['weighted_vertex_count']} / {weights['vertex_count']}.
- Unweighted vertices: {weights['unweighted_vertex_count']}.
- Maximum positive groups per vertex: {weights['maximum_positive_groups_per_vertex']}.
- One smoothing pass was limited to the measured left/right hip-knee bands;
  it did not touch the exact R6 head.
- Bilateral squat p05/p95 edge ratios: `{squat['p05']}` / `{squat['p95']}`.
- Bilateral squat under-half/over-2x fractions: `{squat['fraction_under_half']}` / `{squat['fraction_over_2x']}`.
- Fixed pose gates: `{evidence['pose_gate_results']}`.

## Gates

- Single connected external mesh across the measured neck bridge:
  `{gates['single_cohesive_surface_without_neck_boundary']}`; measured neck-band
  boundary: none; other boundary cycles remaining:
  `{topology['boundary_closed_cycle_count']}`.
- Exact 79-joint weights: `{gates['exact_79_joint_weights']}`.
- Exact R6 retained head coordinates preserved: `{gates['exact_r6_head_coordinates_preserved']}`.
- Fixed-pose deformation: `{gates['fixed_pose_deformation']}`.
- Engineering measured-neck bridge: `{gates['engineering_measured_neck_bridge_passed']}`.
- Complete adult topology proven: `False`.
- Owner visual approval: `False`.
- Candidate export/live binding: `False` / `False`.

## Fixed review renders

{render_lines}

Review Blend: `{relative(output_dir / 'inactive_measured_neck_bridge_r3.blend')}`

Evidence: `{relative(output_dir / 'evidence.json')}`

Manifest: `{relative(manifest_path)}`

## Safety and truth limits

- No GLB was created.
- No Avatar Builder body record or live Kira binding was changed.
- Kira's runtime state remained inactive and byte unchanged.
- R2 parent artifacts remained byte unchanged and are pinned in the manifest.
- External adult-form geometry is not proof of complete anatomy.
- Eyes, lip sync, natural long-duration movement, and owner approval remain unfinished.
"""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")


def main() -> int:
    args = parse_args()
    blender = find_blender(args.blender)
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty review directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    parent_before = {name: sha256_file(path) for name, path in PARENT_ARTIFACTS.items()}
    if parent_before != EXPECTED_PARENT_HASHES:
        raise ValueError(f"sealed R2 parent mismatch: expected={EXPECTED_PARENT_HASHES} actual={parent_before}")
    runtime_before = runtime_snapshot()
    if runtime_before["active_candidate"] not in (None, "") or runtime_before["active_conversation_mode"] not in (None, ""):
        raise RuntimeError("Kira World must be completely inactive before R3")

    review_blend = output_dir / "inactive_measured_neck_bridge_r3.blend"
    config = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "mode": "inactive_measured_neck_bridge_exact_r6_identity_r3",
        "project_root": str(PROJECT_ROOT),
        "output_dir": str(output_dir),
        "review_blend": str(review_blend),
        "parent_artifacts": {name: str(path) for name, path in PARENT_ARTIFACTS.items()},
        "parent_hashes": parent_before,
        "head_cut_fraction_neck_to_head": 0.35,
        "measured_head_cut_z_m": 1.0020709484815598,
        "expected_body_ring_vertices": 76,
        "expected_head_ring_vertices": 154,
        "candidate_glb_export_requested": False,
        "live_binding_change_requested": False,
    }
    config_path = output_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    author_command = [
        str(blender), "--background", str(PARENT_ARTIFACTS["r2_blend"]),
        "--python", str(WORKER), "--", "--config", str(config_path),
    ]
    authored = run_process(author_command, output_dir / "blender_author.log")
    if authored.returncode != 0:
        (output_dir / "failed_manifest.json").write_text(json.dumps({
            "schema_version": 1,
            "review_id": RUN_ID,
            "status": "rejected_worker_failed_no_candidate",
            "returncode": authored.returncode,
            "candidate_glb_created": False,
            "live_binding_changed": False,
        }, indent=2) + "\n", encoding="utf-8")
        raise RuntimeError(f"Blender R3 authoring failed ({authored.returncode}); see blender_author.log")

    if not review_blend.is_file() or not (output_dir / "evidence.json").is_file():
        raise RuntimeError("R3 worker completed without its required Blend/evidence")
    if list(output_dir.rglob("*.glb")) or list(output_dir.rglob("*.gltf")):
        raise RuntimeError("forbidden candidate/export artifact appeared in R3 output")

    reopen_path = output_dir / "reopen_verification.json"
    verify_command = [
        str(blender), "--background", str(review_blend),
        "--python", str(VERIFIER), "--", "--output", str(reopen_path),
    ]
    verified = run_process(verify_command, output_dir / "blender_reopen.log")
    if verified.returncode != 0:
        raise RuntimeError(f"R3 reopen verification failed ({verified.returncode}); see blender_reopen.log")
    reopen = json.loads(reopen_path.read_text(encoding="utf-8"))
    if not reopen.get("passed"):
        raise RuntimeError("R3 reopened but failed its sealed inactive-state audit")

    parent_after = {name: sha256_file(path) for name, path in PARENT_ARTIFACTS.items()}
    runtime_after = runtime_snapshot()
    if parent_after != parent_before:
        raise RuntimeError("a sealed R2 parent artifact changed during R3")
    if runtime_after != runtime_before:
        raise RuntimeError("Kira World runtime state changed during inactive R3")

    evidence_path = output_dir / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    artifacts = {}
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name not in {"evidence.json", "manifest.json"}:
            artifacts[path.name] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    evidence["host_verification"] = {
        "blender_path": str(blender),
        "blender_sha256": sha256_file(blender),
        "author_returncode": authored.returncode,
        "reopen_returncode": verified.returncode,
        "reopen_verification": reopen,
        "parent_hashes_before": parent_before,
        "parent_hashes_after": parent_after,
        "runtime_state_before": runtime_before,
        "runtime_state_after": runtime_after,
        "all_guarded_inputs_and_runtime_byte_unchanged": parent_before == parent_after and runtime_before == runtime_after,
        "artifacts": artifacts,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "review_id": RUN_ID,
        "status": evidence["decision"]["status"],
        "mode": config["mode"],
        "parent_hashes": parent_after,
        "artifacts": {
            "evidence": relative(evidence_path),
            "evidence_sha256": sha256_file(evidence_path),
            "inactive_review_blend": relative(review_blend),
            "inactive_review_blend_sha256": sha256_file(review_blend),
            "reopen_verification": relative(reopen_path),
            "reopen_verification_sha256": sha256_file(reopen_path),
            "fixed_renders": {
                name: {"path": relative(output_dir / filename), "sha256": sha256_file(output_dir / filename)}
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
        "truth_note": "Inactive R3 engineering review only; no candidate, binding, activation, promotion, or complete-adult-topology claim.",
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_report(evidence, manifest_path, output_dir)
    print(json.dumps({"ok": True, "status": manifest["status"], "manifest": str(manifest_path), "report": str(REPORT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
