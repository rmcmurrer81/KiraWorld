"""Create one bounded private-local TemporaryAI media-intake request."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_local_media_intake import (  # noqa: E402
    build_intake_request,
    parse_range_expression,
    save_intake_request,
    tool_readiness,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create a private-local voice/movement intake request. The source must already be under "
            "Data/library. No full movie is extracted and no voice is cloned or assigned."
        )
    )
    parser.add_argument("--candidate-id", default="")
    parser.add_argument("--source", default="")
    parser.add_argument("--character", default="")
    parser.add_argument("--variant", default="")
    parser.add_argument("--speaker", default="")
    parser.add_argument("--performer", default="")
    parser.add_argument("--evidence", action="append", choices=["voice", "movement"], default=[])
    parser.add_argument(
        "--range",
        dest="ranges",
        action="append",
        default=[],
        help="Bounded START-END timecode; repeat for each reviewed target scene. Maximum 45 seconds each.",
    )
    parser.add_argument("--authorize-private-local-use", action="store_true")
    parser.add_argument("--authorized-by", default="")
    parser.add_argument("--authorization-note", default="")
    parser.add_argument("--request-label", default="")
    parser.add_argument("--readiness-only", action="store_true")
    args = parser.parse_args()

    if args.readiness_only:
        print(json.dumps(tool_readiness(), indent=2))
        return 0
    missing = [
        flag
        for flag, value in (
            ("--candidate-id", args.candidate_id),
            ("--source", args.source),
            ("--character", args.character),
            ("--variant", args.variant),
            ("--speaker", args.speaker),
            ("--performer", args.performer),
        )
        if not str(value).strip()
    ]
    if missing:
        parser.error("required unless --readiness-only: " + ", ".join(missing))
    evidence = args.evidence or ["voice", "movement"]
    scene_ranges = [parse_range_expression(item, evidence) for item in args.ranges]
    request = build_intake_request(
        candidate_id=args.candidate_id,
        source_path=args.source,
        character_label=args.character,
        variant_label=args.variant,
        speaker_label=args.speaker,
        performer_label=args.performer,
        evidence_types=evidence,
        scene_ranges=scene_ranges,
        private_local_use_authorized=args.authorize_private_local_use,
        authorized_by=args.authorized_by,
        authorization_note=args.authorization_note,
        request_label=args.request_label,
    )
    output = save_intake_request(request)
    print(
        json.dumps(
            {
                "status": request["status"],
                "request": str(output),
                "bounded_scene_count": len(request["scene_ranges"]),
                "requested_total_seconds": request["limits"]["requested_total_seconds"],
                "voice_clone_or_activation_performed": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
