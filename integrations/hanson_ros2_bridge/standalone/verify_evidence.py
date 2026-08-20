from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import ValidationError

from schema_tools import schema_validator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "ros2_ws" / "src" / "kira_hanson_bridge"
sys.path.insert(0, str(PACKAGE_ROOT))

from kira_hanson_bridge.evidence import EvidenceChain  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a bridge SHA-256-linked JSONL evidence file.")
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--record-schema",
        type=Path,
        help="Optionally validate each inner evidence record against this JSON Schema.",
    )
    args = parser.parse_args()
    valid, count, final_hash = EvidenceChain.verify(args.path)
    schema_valid = True
    if valid and args.record_schema is not None:
        try:
            schema = json.loads(args.record_schema.read_text(encoding="utf-8"))
            validator = schema_validator(schema)
            with args.path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    persisted = json.loads(line)
                    validator.validate(persisted["record"])
        except (KeyError, OSError, RuntimeError, TypeError, ValueError, ValidationError) as exc:
            schema_valid = False
            print(f"record_schema_error={exc}")
    print(f"valid={str(valid).lower()}")
    if args.record_schema is not None:
        print(f"record_schema_valid={str(schema_valid).lower()}")
    print(f"records={count}")
    print(f"final_sha256={final_hash}")
    return 0 if valid and schema_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
