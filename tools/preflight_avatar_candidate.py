"""Print a read-only TemporaryAI identity/version/maturity avatar preflight."""

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
    evaluate_avatar_profile_preflight,
    evaluate_orchestration_identity_preflight,
)


def _json_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise AvatarProfilePreflightError("orchestration request must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only avatar canonical profile and variant preflight."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--candidate-id")
    group.add_argument("--orchestration-request", type=Path)
    parser.add_argument("--subject-id", default="")
    parser.add_argument("--maturity-class", default="")
    parser.add_argument(
        "--adult-anatomy",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    try:
        if args.orchestration_request:
            request = _json_object(args.orchestration_request.resolve(strict=True))
            result = evaluate_orchestration_identity_preflight(PROJECT_ROOT, request)
        else:
            result = evaluate_avatar_profile_preflight(
                PROJECT_ROOT,
                args.candidate_id,
                requested_subject_id=args.subject_id,
                requested_maturity_class=args.maturity_class,
                request_complete_adult_anatomy=args.adult_anatomy,
            )
        if args.compact:
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("passed") is True else 6
    except (AvatarProfilePreflightError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}), file=sys.stderr)
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
