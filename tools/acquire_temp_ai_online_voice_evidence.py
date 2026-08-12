#!/usr/bin/env python3
"""Acquire and objectively prepare one owner-authorized bounded online range."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_online_media_analysis import (  # noqa: E402
    build_analysis_request,
    run_private_online_analysis,
    write_failure_record,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Privately acquire and prepare one <=45-second online voice-evidence range. "
            "This does not identify, clone, assign, synthesize, or activate anyone."
        )
    )
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--start-seconds", required=True, type=float)
    parser.add_argument("--end-seconds", required=True, type=float)
    parser.add_argument(
        "--owner-authorized-private-analysis",
        action="store_true",
        help="Required explicit authority for bounded private acquisition and objective preparation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        request = build_analysis_request(
            candidate_id=args.candidate_id,
            source_url=args.source_url,
            start_seconds=args.start_seconds,
            end_seconds=args.end_seconds,
            owner_authorized_private_analysis=args.owner_authorized_private_analysis,
        )
        result = run_private_online_analysis(request)
    except Exception as exc:
        failure_path = write_failure_record(
            candidate_id=args.candidate_id,
            source_url=args.source_url,
            start_seconds=args.start_seconds,
            end_seconds=args.end_seconds,
            error=exc,
        )
        print(
            json.dumps(
                {
                    "status": "failed_no_identity_or_model_change",
                    "error": str(exc)[:1000],
                    "failure_record": str(failure_path or ""),
                    "voice_training_or_cloning_performed": False,
                    "voice_assigned": False,
                    "voice_synthesized": False,
                    "candidate_activated": False,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            {
                "status": result["status"],
                "analysis_id": result["analysis_id"],
                "candidate_id": result["candidate_id"],
                "requested_range": result["source"]["requested_range"],
                "segment_count": result["artifacts"]["segment_count"],
                "possible_contamination_flagged": result["objective_review"]["possible_contamination_flagged"],
                "overlap_cleared": False,
                "speaker_identity_verified": False,
                "eligible_for_direct_model_input": False,
                "manual_400_clip_review_box_opened": False,
                "run_dir": result["run_dir"],
                "voice_training_or_cloning_performed": False,
                "voice_assigned": False,
                "voice_synthesized": False,
                "candidate_activated": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
