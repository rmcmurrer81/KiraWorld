#!/usr/bin/env python3
"""Create a non-rendering, privacy-safe structural report for one GLB body."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_body_topology import inspect_glb_topology  # noqa: E402


def _load_optional_json(path: str) -> dict[str, Any] | None:
    if not path:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("attestation JSON must contain an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit GLB mesh/skin/joint structure without rendering or disclosing raw names."
        )
    )
    parser.add_argument("glb", help="Local GLB to inspect; its path is never written to the report")
    parser.add_argument("--artifact-id", default="private_candidate")
    parser.add_argument("--anatomy-attestation", default="")
    parser.add_argument("--rig-attestation", default="")
    parser.add_argument("--output", default="", help="Optional privacy-safe JSON report path")
    parser.add_argument("--require-structural-rig", action="store_true")
    args = parser.parse_args()

    report = inspect_glb_topology(
        args.glb,
        artifact_id=args.artifact_id,
        anatomy_attestation=_load_optional_json(args.anatomy_attestation),
        rig_attestation=_load_optional_json(args.rig_attestation),
    )
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded)
    if not report["valid_glb"]:
        return 2
    if args.require_structural_rig and not report["humanoid_rig_structurally_ready"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

