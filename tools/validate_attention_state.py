"""
Validate Kira/Lisa attention state JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from attention_state_manager import validate_attention_state  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an attention state JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    states = data if isinstance(data, list) else [data]
    failures = []
    for index, state in enumerate(states):
        errors = validate_attention_state(state)
        if errors:
            failures.append(f"state[{index}]: {'; '.join(errors)}")
    if failures:
        print(f"{path} is not valid:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
