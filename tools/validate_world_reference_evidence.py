"""Validate a real-place World Builder reference evidence contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.world_reference_evidence import (
    WorldReferenceEvidenceError,
    validate_reference_evidence_contract,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.contract.read_text(encoding="utf-8"))
        decisions = validate_reference_evidence_contract(data)
    except (OSError, json.JSONDecodeError, WorldReferenceEvidenceError) as exc:
        print(f"Reference evidence contract rejected: {exc}")
        raise SystemExit(1) from exc
    print(json.dumps({"valid": True, "areas": [item.as_dict() for item in decisions]}, indent=2))


if __name__ == "__main__":
    main()
