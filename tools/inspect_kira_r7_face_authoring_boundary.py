#!/usr/bin/env python3
"""Launch the read-only Kira R7 face-boundary inspection in Blender."""

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
EYE_RIG = (
    PROJECT_ROOT
    / "Avatar/models/staged/kira/eyes/kira_brown_eye_rig_v3_2"
    / "kira_brown_eye_rig_v3_2.glb"
)
WORKER = PROJECT_ROOT / "tools/blender_inspect_kira_r7_face_authoring_boundary.py"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_face_authoring_boundary_20260721/evidence.json"
)
EXPECTED = {
    "workspace": "9d0f9dad39b2e0650419ccef48a7d524d5cd67e4429f1d23ee3398db396c0394",
    "source_r6": "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
    "staged_eye_rig": "fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413",
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
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    blender = find_blender(args.blender)
    output = Path(args.output).resolve()
    paths = {"workspace": WORKSPACE, "source_r6": SOURCE_R6, "staged_eye_rig": EYE_RIG}
    before = {name: sha256_file(path) for name, path in paths.items()}
    if before != EXPECTED:
        raise ValueError(f"pinned inputs changed: expected={EXPECTED} actual={before}")

    command = [
        str(blender),
        "--background",
        str(WORKSPACE),
        "--python",
        str(WORKER),
        "--",
        "--output",
        str(output),
        "--source",
        str(SOURCE_R6),
        "--eye-rig",
        str(EYE_RIG),
        "--workspace-sha256",
        EXPECTED["workspace"],
        "--source-sha256",
        EXPECTED["source_r6"],
        "--eye-rig-sha256",
        EXPECTED["staged_eye_rig"],
    ]
    completed = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True)
    if completed.returncode:
        raise RuntimeError(
            f"Blender inspection failed ({completed.returncode})\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )

    after = {name: sha256_file(path) for name, path in paths.items()}
    if after != before:
        raise RuntimeError(f"read-only inspection changed a pinned input: before={before} after={after}")
    evidence = json.loads(output.read_text(encoding="utf-8"))
    evidence["host_verification"] = {
        "blender_path": str(blender),
        "blender_sha256": sha256_file(blender),
        "pinned_hashes_before": before,
        "pinned_hashes_after": after,
        "all_pinned_inputs_byte_unchanged": before == after,
    }
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(output),
                "pinned_inputs_unchanged": True,
                "face_authoring_allowed": evidence["gates"]["face_geometry_authoring_allowed"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
