"""Print one bounded, read-only preflight for all current TemporaryAI profiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_profile_preflight import (
    AvatarProfilePreflightError,
    evaluate_current_avatar_profile_batch,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only identity/version/maturity preflight for all current profiles."
    )
    parser.add_argument("--max-candidates", type=int, default=32)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    try:
        result = evaluate_current_avatar_profile_batch(
            PROJECT_ROOT, max_candidates=args.max_candidates
        )
        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=None if args.compact else 2,
                sort_keys=args.compact,
                separators=(",", ":") if args.compact else None,
            )
        )
        return 0 if result.get("coverage_passed") is True else 6
    except (AvatarProfilePreflightError, OSError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}), file=sys.stderr)
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
