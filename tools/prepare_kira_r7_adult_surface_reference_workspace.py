#!/usr/bin/env python3
"""Prepare a read-only Kira R7/adult-reference feasibility workspace.

The operation is deliberately non-authoring.  It imports the exact pinned Kira
R6 surface/79-joint cage and the exact owner-supplied CC BY 4.0 adult reference
into separate, locked Blender collections.  It measures whether an automatic
surface or feature transfer has enough correspondence and semantic evidence to
be safe.  It never exports a candidate, changes either source, or edits a live
binding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KIRA_SOURCE = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6"
    / "r6_20260718_163658/kira_provisional_body_r6.glb"
)
REFERENCE_SOURCE = Path(r"C:\Users\robmc\Desktop\5\base_female_character.glb")
OUTPUT_DIR = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_adult_body_r7"
    / "adult_reference_feasibility_20260721"
)
WORKER = Path(__file__).with_name(
    "blender_prepare_kira_r7_adult_surface_reference_workspace.py"
)
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


def read_glb_json(path: Path) -> dict[str, object]:
    with path.open("rb") as stream:
        magic, version, _length = struct.unpack("<4sII", stream.read(12))
        if magic != b"glTF" or version != 2:
            raise ValueError(f"not a GLB 2.0 file: {path}")
        chunk_length, chunk_type = struct.unpack("<II", stream.read(8))
        if chunk_type != 0x4E4F534A:
            raise ValueError(f"first GLB chunk is not JSON: {path}")
        return json.loads(
            stream.read(chunk_length).decode("utf-8").rstrip("\x00 \t\r\n")
        )


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
        candidate = candidate.resolve()
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Blender executable was not found")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sources = {
        "kira_r6": KIRA_SOURCE.resolve(strict=True),
        "adult_reference": REFERENCE_SOURCE.resolve(strict=True),
    }
    hashes_before = {name: sha256_file(path) for name, path in sources.items()}
    if hashes_before != EXPECTED_HASHES:
        raise ValueError(
            f"pinned source hash changed: expected={EXPECTED_HASHES} actual={hashes_before}"
        )

    reference_json = read_glb_json(sources["adult_reference"])
    extras = reference_json.get("asset", {}).get("extras", {})
    if extras.get("license") != "CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/)":
        raise ValueError("the pinned adult reference no longer has the expected CC BY 4.0 evidence")
    if extras.get("author") != "BlackProject (https://sketchfab.com/BlackProject)":
        raise ValueError("the pinned adult reference author evidence changed")

    output_dir = Path(args.output_dir).resolve()
    output_dir.relative_to(
        (PROJECT_ROOT / "Avatar/avatar_builder/candidate_sources/kira_adult_body_r7").resolve()
    )
    if output_dir.exists():
        raise FileExistsError(
            f"refusing to replace an existing isolated feasibility run: {output_dir}"
        )
    output_dir.mkdir(parents=True)

    blender = find_blender(args.blender)
    config = {
        "schema_version": 1,
        "run_id": "kira_r7_adult_reference_feasibility_20260721",
        "project_root": str(PROJECT_ROOT),
        "kira_source": str(sources["kira_r6"]),
        "kira_sha256": hashes_before["kira_r6"],
        "reference_source": str(sources["adult_reference"]),
        "reference_sha256": hashes_before["adult_reference"],
        "reference_provenance": extras,
        "workspace": str(output_dir / "kira_r7_adult_reference_feasibility.blend"),
        "evidence": str(output_dir / "feasibility_evidence.json"),
        "candidate_export_requested": False,
        "runtime_activation_requested": False,
        "geometry_transfer_requested": False,
    }
    config_path = output_dir / "workspace_config.json"
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
    (output_dir / "blender_prepare.log").write_text(
        completed.stdout or "", encoding="utf-8"
    )
    if completed.returncode:
        raise RuntimeError(
            f"Blender feasibility inspection failed ({completed.returncode})\n"
            + "\n".join((completed.stdout or "").splitlines()[-60:])
        )

    workspace = Path(config["workspace"])
    evidence_path = Path(config["evidence"])
    if not workspace.is_file() or not evidence_path.is_file():
        raise RuntimeError("Blender did not create the isolated workspace and evidence")
    hashes_after = {name: sha256_file(path) for name, path in sources.items()}
    if hashes_after != hashes_before:
        raise RuntimeError("a pinned source changed during the read-only feasibility pass")

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    gates = evidence.get("gates", {})
    if gates.get("automatic_geometry_transfer_allowed"):
        raise RuntimeError("unsafe automatic transfer gate unexpectedly opened")
    safety = evidence.get("safety", {})
    if safety.get("candidate_glb_exported") or safety.get("geometry_transfer_applied"):
        raise RuntimeError("feasibility workspace unexpectedly authored a candidate")

    evidence["host_verification"] = {
        "blender_path": str(blender),
        "blender_sha256": sha256_file(blender),
        "worker_path": str(WORKER.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "worker_sha256": sha256_file(WORKER),
        "source_hashes_before": hashes_before,
        "source_hashes_after": hashes_after,
        "all_sources_byte_unchanged": hashes_before == hashes_after,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    summary = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "status": "inactive_reference_workspace_prepared_automatic_transfer_blocked",
        "decision": evidence["decision"],
        "workspace": {
            "path": str(workspace.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(workspace),
        },
        "evidence": {
            "path": str(evidence_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(evidence_path),
        },
        "sources_unchanged": True,
        "candidate_exported": False,
        "runtime_binding_changed": False,
        "next_blender_operation": evidence["next_blender_operation"],
    }
    (output_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
