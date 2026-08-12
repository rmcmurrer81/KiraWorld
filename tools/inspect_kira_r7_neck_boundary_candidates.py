#!/usr/bin/env python3
"""Run the pinned, read-only Kira R7 neck-boundary candidate inspection."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (
    ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_adult_body_r7/workspace_v1"
    / "kira_r7_authoring_workspace.blend"
)
SOURCE = (
    ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6"
    / "r6_20260718_163658/kira_provisional_body_r6.glb"
)
WORKER = ROOT / "tools/blender_inspect_kira_r7_neck_boundary_candidates.py"
OUTPUT_DIR = (
    ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_neck_boundary_owner_review_20260721"
)
DEFAULT_OUTPUT = OUTPUT_DIR / "evidence.json"
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
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    blender = find_blender(args.blender)
    output = Path(args.output).resolve()
    paths = {"workspace": WORKSPACE, "source_r6": SOURCE}
    before = {name: sha256_file(path) for name, path in paths.items()}
    if before != EXPECTED:
        raise ValueError(f"pinned inputs changed: expected={EXPECTED} actual={before}")
    render_dir = output.parent / "debug_renders"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
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
        str(SOURCE),
        "--workspace-sha256",
        EXPECTED["workspace"],
        "--source-sha256",
        EXPECTED["source_r6"],
        "--debug-render-dir",
        str(render_dir),
    ]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if completed.returncode:
        raise RuntimeError(
            f"Blender inspection failed ({completed.returncode})\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    if not output.is_file():
        raise RuntimeError(
            "Blender returned without writing evidence\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    after = {name: sha256_file(path) for name, path in paths.items()}
    if after != before:
        raise RuntimeError(f"read-only inspection changed a pinned input: {before=} {after=}")
    evidence = json.loads(output.read_text(encoding="utf-8"))
    evidence["host_verification"] = {
        "blender": {"path": str(blender), "sha256": sha256_file(blender)},
        "pinned_hashes_before": before,
        "pinned_hashes_after": after,
        "all_pinned_inputs_byte_unchanged": before == after,
    }
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output), "pinned_inputs_unchanged": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
