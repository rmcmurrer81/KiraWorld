"""Inspect, prepare, or finalize the inactive multiview likeness-author stage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_likeness_author_backend import (  # noqa: E402
    AvatarLikenessAuthorError,
    DEFAULT_CAPABILITY_PATH,
    finalize_likeness_author_outputs,
    inspect_author_tooling,
    prepare_likeness_author_work_order,
    validate_queued_evidence_job,
)
from Core.avatar_component_production import AvatarProductionError  # noqa: E402
from Core.avatar_profile_preflight import AvatarProfilePreflightError  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed bridge from fully reviewed multiview evidence to an "
            "inactive private new-surface authoring work order."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--queued-job", type=Path, required=True)
    inspect_parser.add_argument("--capability", type=Path, default=DEFAULT_CAPABILITY_PATH)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--queued-job", type=Path, required=True)
    prepare_parser.add_argument("--capability", type=Path, default=DEFAULT_CAPABILITY_PATH)
    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--work-order", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "inspect":
            evidence = validate_queued_evidence_job(PROJECT_ROOT, args.queued_job)
            tooling = inspect_author_tooling(PROJECT_ROOT, args.capability)
            result = {
                "schema_version": 1,
                "status": (
                    "ready_to_prepare_inactive_author_work_order"
                    if tooling.get("ready") is True
                    else tooling.get("status")
                ),
                "candidate_id": evidence["job"]["candidate_id"],
                "queued_job_id": evidence["job_id"],
                "reviewed_evidence_verified": True,
                "author_tooling_ready": tooling.get("ready") is True,
                "blocking_reasons": tooling.get("blocking_reasons", []),
                "body_candidate_created": False,
                "runtime_activation_allowed": False,
            }
        elif args.command == "prepare":
            result = prepare_likeness_author_work_order(
                PROJECT_ROOT,
                args.queued_job,
                capability_path=args.capability,
            )
        else:
            result = finalize_likeness_author_outputs(
                PROJECT_ROOT, args.work_order
            )
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") in {
            "ready_to_prepare_inactive_author_work_order",
            "prepared_inactive_author_work_order",
            "already_prepared_verified",
            "staged_for_private_owner_review_not_approved",
            "already_staged_verified",
        } else 6
    except (
        AvatarLikenessAuthorError,
        AvatarProductionError,
        AvatarProfilePreflightError,
        FileNotFoundError,
        OSError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "blocked",
                    "error": str(exc),
                    "runtime_activation_allowed": False,
                }
            ),
            file=sys.stderr,
        )
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
