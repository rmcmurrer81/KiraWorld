#!/usr/bin/env python3
"""Run and seal Kira's inactive R7 reconstructed-neck R4-v10 review."""

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
    / "measured_neck_bridge_r3"
)
PARENT_ARTIFACTS = {
    "r3_blend": PARENT_DIR / "inactive_measured_neck_bridge_r3.blend",
    "r3_evidence": PARENT_DIR / "evidence.json",
    "r3_manifest": PARENT_DIR / "manifest.json",
}
EXPECTED_PARENT_HASHES = {
    "r3_blend": "327e072e128179dbe379673ca58e61d2e9db065a12ec36b4ae6844130dce4145",
    "r3_evidence": "7e690445d4af96b7fd8d30ddfa0b36cb6b641432e36575bf032ef5bc050c5d7d",
    "r3_manifest": "30dada3566c7325a21215c28412477efce645a4175ab920148125b928e3b31e1",
}
RUNTIME_STATE = PROJECT_ROOT / "Data/runtime/kira_world_shell_state.json"
WORKER = PROJECT_ROOT / "tools/blender_author_kira_r7_adult_surface_r4.py"
VERIFIER = PROJECT_ROOT / "tools/blender_verify_kira_r7_adult_surface_r4.py"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests/kira_r7_adult_surface_trial_20260722"
    / "reconstructed_neck_surface_r4_v10"
)
REPORT = PROJECT_ROOT / "Data/codex_reports/20260722_kira_r7_adult_surface_r4_v10.md"
RUN_ID = "kira_r7_adult_surface_reconstructed_neck_r4_v10_20260722"


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


def write_report(evidence: dict[str, object], output_dir: Path) -> None:
    transition = evidence["transition"]
    identity = evidence["identity_preservation"]
    topology = evidence["topology"]
    weights = evidence["weights"]
    gates = evidence["gates"]
    render_lines = "\n".join(f"- `{name}`: `{filename}`" for name, filename in evidence["renders"].items())
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        f"""# Kira R7 inactive adult surface R4-v10 — 2026-07-22

## Outcome

**R4-v10 inactive engineering artifact authored; original-resolution visual review is pending.**

R4-v10 removes the visibly defective R3 collar while preserving the natural upper neck,
then joins clean retained shoulder and neck loops with
{transition['intermediate_ring_count']} arc-length-aligned ruled-loft rings with bounded
circumferential relaxation that fades to zero at both retained boundaries.
This is a geometry reconstruction, not a material concealment. The original light
skin contract remains `{evidence['skin']['srgb_hex']}`.

All {identity['protected_face_mouth_eye_cranium_vertex_count']} protected head,
face, mouth, eye-aperture, ear, and cranium vertices remain unchanged. The removed
source vertices are confined to the approved {identity['body_approved_reconstruction_vertex_count']}
body and {identity['lower_neck_head_approved_reconstruction_vertex_count']} lower-neck
topological zones. Maximum displacement of every retained source vertex is
`{identity['adult_surface_outside_bounded_transition_maximum_coordinate_delta_m']}` m.

Decision: `{evidence['decision']['status']}`

## Geometry and rig

- Removed R3 bridge faces: {transition['removed_r3_bridge_faces']}.
- Added transition vertices/faces: {transition['added_transition_vertices']} / {transition['added_transition_faces']}.
- Connected components: {topology['connected_components']}.
- Boundary cycles: {topology['boundary_closed_cycle_count']} (the same three sealed eye/mouth openings; no neck opening).
- Overused/degenerate faces: {topology['overused_edge_count']} / {topology['degenerate_face_count_under_1e_12_m2']}.
- Defined rig groups: {weights['defined_vertex_group_count']}.
- Unweighted vertices: {weights['unweighted_vertex_count']}.
- Maximum positive groups per vertex: {weights['maximum_positive_groups_per_vertex']}.
- Fixed pose gates: `{evidence['pose_gate_results']}`.
- Bounded-reconstruction engineering gate: `{gates['engineering_bounded_reconstruction_passed']}`.

## Fixed original-resolution renders

{render_lines}

Review Blend: `{relative(output_dir / 'inactive_reconstructed_neck_surface_r4_v10.blend')}`

Evidence: `{relative(output_dir / 'evidence.json')}`

Manifest: `{relative(output_dir / 'manifest.json')}`

## Safety and truth limits

- No GLB has been exported while visual review is pending.
- No Avatar Builder binding, live body, activation state, or autobuild record changed.
- Complete adult topology/internal anatomy is not claimed.
- Eyes, lip sync, and runtime movement remain separate unfinished tasks.
- A rollback-safe inactive GLB may be authored later only after fixed-view visual approval.
""",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    blender = find_blender(args.blender)
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty R4-v10 directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    parent_before = {name: sha256_file(path) for name, path in PARENT_ARTIFACTS.items()}
    if parent_before != EXPECTED_PARENT_HASHES:
        raise ValueError(f"sealed R3 parent mismatch: expected={EXPECTED_PARENT_HASHES} actual={parent_before}")
    runtime_before = runtime_snapshot()
    if runtime_before["active_candidate"] not in (None, "") or runtime_before["active_conversation_mode"] not in (None, ""):
        raise RuntimeError("Kira World must be completely inactive before R4-v10")

    review_blend = output_dir / "inactive_reconstructed_neck_surface_r4_v10.blend"
    config = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "mode": "inactive_topological_neck_reconstruction_r4_v10",
        "project_root": str(PROJECT_ROOT),
        "output_dir": str(output_dir),
        "review_blend": str(review_blend),
        "parent_artifacts": {name: str(path) for name, path in PARENT_ARTIFACTS.items()},
        "parent_hashes": parent_before,
        "intermediate_ring_count": 16,
        "body_erosion_depth": 2,
        "head_erosion_depth": 2,
        "circumferential_relax_iterations": 6,
        "circumferential_relax_strength": 0.16,
        "neck_closeup_ortho_scale_m": 0.42,
        "candidate_glb_export_requested": False,
        "live_binding_change_requested": False,
    }
    config_path = output_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    authored = run_process(
        [str(blender), "--background", str(PARENT_ARTIFACTS["r3_blend"]), "--python", str(WORKER), "--", "--config", str(config_path)],
        output_dir / "blender_author.log",
    )
    if authored.returncode != 0:
        (output_dir / "failed_manifest.json").write_text(json.dumps({
            "schema_version": 1,
            "review_id": RUN_ID,
            "status": "rejected_r4v10_worker_failed_no_candidate",
            "returncode": authored.returncode,
            "candidate_glb_created": False,
            "live_binding_changed": False,
        }, indent=2) + "\n", encoding="utf-8")
        raise RuntimeError(f"Blender R4-v10 authoring failed ({authored.returncode}); see blender_author.log")
    evidence_path = output_dir / "evidence.json"
    if not review_blend.is_file() or not evidence_path.is_file():
        raise RuntimeError("R4-v10 worker did not create required Blend/evidence")
    if list(output_dir.rglob("*.glb")) or list(output_dir.rglob("*.gltf")):
        raise RuntimeError("forbidden pre-review candidate export appeared in R4-v10")

    reopen_path = output_dir / "reopen_verification.json"
    verified = run_process(
        [str(blender), "--background", str(review_blend), "--python", str(VERIFIER), "--", "--output", str(reopen_path)],
        output_dir / "blender_reopen.log",
    )
    if verified.returncode != 0:
        raise RuntimeError(f"R4-v10 reopen verification failed ({verified.returncode}); see blender_reopen.log")
    reopen = json.loads(reopen_path.read_text(encoding="utf-8"))
    if not reopen.get("passed"):
        raise RuntimeError("R4-v10 reopened but failed its inactive-state audit")

    parent_after = {name: sha256_file(path) for name, path in PARENT_ARTIFACTS.items()}
    runtime_after = runtime_snapshot()
    if parent_after != parent_before:
        raise RuntimeError("sealed R3 input changed during R4-v10")
    if runtime_after != runtime_before:
        raise RuntimeError("Kira World runtime state changed during inactive R4-v10")

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    artifact_records = {}
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name not in {"evidence.json", "manifest.json"}:
            artifact_records[path.name] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    evidence["host_verification"] = {
        "blender_path": str(blender),
        "author_returncode": authored.returncode,
        "reopen_returncode": verified.returncode,
        "reopen_verification": reopen,
        "parent_hashes_before": parent_before,
        "parent_hashes_after": parent_after,
        "runtime_state_before": runtime_before,
        "runtime_state_after": runtime_after,
        "all_guarded_inputs_and_runtime_byte_unchanged": parent_before == parent_after and runtime_before == runtime_after,
        "artifacts": artifact_records,
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
        "truth_note": "Inactive R4-v10 shallow topological neck-reconstruction engineering review only; fixed-view visual review remains required before any rollback-safe export.",
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_report(evidence, output_dir)
    print(json.dumps({"ok": True, "status": manifest["status"], "manifest": str(manifest_path), "report": str(REPORT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
