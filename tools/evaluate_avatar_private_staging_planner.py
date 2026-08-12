#!/usr/bin/env python3
"""Print the read-only one-body private staging unlock and optional dry run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Core.avatar_private_staging_planner import (  # noqa: E402
    build_private_staging_dry_run_plan,
    evaluate_private_staging_unlock,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate one exact body-quality package for private serial staging. "
            "This command never queues, builds, activates, replaces, or exports."
        )
    )
    parser.add_argument("manifest", help="Project-relative exact candidate manifest JSON")
    parser.add_argument("review", help="Project-relative independent visual review JSON")
    parser.add_argument("--dry-run-plan", action="store_true")
    args = parser.parse_args()

    result = evaluate_private_staging_unlock(ROOT, args.manifest, args.review)
    payload: dict[str, object] = {"unlock": result}
    if args.dry_run_plan and result.get("private_serial_staging_plan_allowed") is True:
        payload["dry_run_plan"] = build_private_staging_dry_run_plan(ROOT, result)
    elif args.dry_run_plan:
        payload["dry_run_plan"] = {
            "status": "not_available_one_body_quality_gate_locked",
            "jobs": [],
            "queue_created": False,
            "automatic_execution_started": False,
        }
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("private_serial_staging_plan_allowed") is True else 3


if __name__ == "__main__":
    raise SystemExit(main())
