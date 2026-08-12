from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_two_subject_autobuild_gate import (  # noqa: E402
    build_two_subject_autobuild_dry_run_plan,
    evaluate_two_subject_autobuild_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only status for the fail-closed Avatar Builder two-distinct-"
            "subject auto-authoring gate. This command never queues or builds."
        )
    )
    parser.add_argument(
        "--dry-run-plan",
        action="store_true",
        help="Also print the one-at-a-time authoring schedule if the gate passes.",
    )
    args = parser.parse_args()

    result = evaluate_two_subject_autobuild_gate(PROJECT_ROOT)
    payload: dict[str, object] = {"gate": result}
    if args.dry_run_plan and result.get("batch_auto_authoring_allowed") is True:
        payload["dry_run_plan"] = build_two_subject_autobuild_dry_run_plan(
            PROJECT_ROOT, result
        )
    elif args.dry_run_plan:
        payload["dry_run_plan"] = {
            "status": "not_available_gate_locked",
            "queue_created": False,
        }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if result.get("batch_auto_authoring_allowed") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())

