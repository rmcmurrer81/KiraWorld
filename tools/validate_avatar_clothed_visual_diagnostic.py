"""Validate one inactive clothed-avatar turntable proof."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_clothed_visual_diagnostic import evaluate_clothed_visual_diagnostic


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("proof", type=Path)
    parser.add_argument("--expected-model-sha256", default="")
    args = parser.parse_args()
    result = evaluate_clothed_visual_diagnostic(
        PROJECT_ROOT,
        args.proof,
        expected_model_sha256=args.expected_model_sha256,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["integrity_verified"] else 6


if __name__ == "__main__":
    raise SystemExit(main())

