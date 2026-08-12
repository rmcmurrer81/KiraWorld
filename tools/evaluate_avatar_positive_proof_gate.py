from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_positive_proof_gate import evaluate_positive_proof  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate one body's positive-proof qualification. A passing result "
            "cannot release batch auto-authoring; the two-subject gate is required."
        )
    )
    parser.add_argument("--proof", default="", help="Project-relative positive-proof JSON path.")
    args = parser.parse_args()
    result = evaluate_positive_proof(PROJECT_ROOT, Path(args.proof) if args.proof else None)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    # Deliberately never return success: older automation historically treated
    # exit 0 as downstream release authority.  Code 3 means the single subject
    # qualified, but the mandatory two-distinct-subject batch gate is still the
    # only release route.  Code 2 means even the subject qualification is locked.
    return 3 if result.get("subject_qualification_ready") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
