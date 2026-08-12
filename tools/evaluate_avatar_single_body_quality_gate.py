#!/usr/bin/env python3
"""Evaluate one inactive avatar body package and its rendered review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Core.avatar_single_body_quality_gate import (  # noqa: E402
    evaluate_two_pass_body_quality,
)


def load_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("review")
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve(strict=True)
    result = evaluate_two_pass_body_quality(
        project_root,
        load_object(Path(args.manifest).resolve(strict=True)),
        load_object(Path(args.review).resolve(strict=True)),
    )
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded)
    return 0 if result["passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
