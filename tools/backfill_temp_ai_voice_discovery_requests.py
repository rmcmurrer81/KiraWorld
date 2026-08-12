"""Backfill missing no-download voice-discovery requests for real profiles."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_voice_discovery_backfill import (  # noqa: E402
    apply_voice_discovery_backfill,
    authorization_summary,
    plan_voice_discovery_backfill,
)


DEFAULT_CANDIDATE_ROOT = PROJECT_ROOT / "TemporaryAI" / "candidates"
DEFAULT_AUTHORIZATION = (
    PROJECT_ROOT
    / "Voice"
    / "authorizations"
    / "robert_private_exact_temp_ai_voice_authorization_20260716.json"
)


def _public_plan(plan: dict) -> dict:
    return {
        "status": "dry_run",
        "profile_candidate_count": plan["profile_candidate_count"],
        "create_candidate_ids": [
            row["candidate_id"] for row in plan["rows"] if row["action"] == "create_missing"
        ],
        "preserve_candidate_ids": [
            row["candidate_id"] for row in plan["rows"] if row["action"] == "preserve_existing"
        ],
        "excluded": plan["excluded"],
        "blank_identity_or_source_blockers": [
            {"candidate_id": row["candidate_id"], "blockers": row["blockers"]}
            for row in plan["rows"]
            if row["blockers"]
        ],
        "all_planned_requests_stage_boundary_passed": (
            not plan["errors"] and all(row["stage_boundary"]["passed"] for row in plan["rows"])
        ),
        "operations_performed": {
            "metadata_requests_created": 0,
            "metadata_provider_searches": 0,
            "media_downloads": 0,
            "audio_extractions": 0,
            "voice_models_prepared_or_trained": 0,
            "voices_assigned": 0,
            "candidates_activated": 0,
        },
        "errors": plan["errors"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create only missing TemporaryAI metadata voice-discovery requests. "
            "Existing requests are preserved byte-for-byte. This command performs "
            "no provider search, media download, audio extraction, cloning/training, "
            "voice assignment, speech generation, or activation."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Exclusively create missing request files. Default is a no-write dry run.",
    )
    parser.add_argument(
        "--candidate-root",
        type=Path,
        default=DEFAULT_CANDIDATE_ROOT,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--authorization",
        type=Path,
        default=DEFAULT_AUTHORIZATION,
        help="Project-private future-stage authorization record to validate.",
    )
    args = parser.parse_args()
    try:
        result = (
            apply_voice_discovery_backfill(args.candidate_root)
            if args.apply
            else _public_plan(plan_voice_discovery_backfill(args.candidate_root))
        )
        result["private_future_stage_authorization"] = authorization_summary(
            args.authorization.resolve()
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        valid = result["private_future_stage_authorization"]["valid"]
        return 0 if not result.get("errors") and valid else 2
    except Exception as exc:
        print(f"TEMP AI VOICE BACKFILL BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
