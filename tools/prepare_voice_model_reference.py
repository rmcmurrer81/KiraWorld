"""Prepare a reviewed voice pack for a future local model backend."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from Core.voice_model_dataset import prepare_model_reference


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack_dir")
    args = parser.parse_args()
    try:
        result = prepare_model_reference(Path(args.pack_dir))
    except Exception as exc:
        print(f"NOT READY: {exc}")
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
