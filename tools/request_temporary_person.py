"""Phone/front-door CLI bridge for a gated temporary-person request."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.temporary_person_request import build_request, save_request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requester-id", required=True)
    parser.add_argument("--requester-kind", default="permanent_resident")
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--type", required=True, dest="request_type")
    parser.add_argument("--request", required=True)
    parser.add_argument("--details-json", default="{}")
    parser.add_argument("--output", type=Path, default=ROOT / "Data" / "temporary_person_requests" / "phone_intake")
    args = parser.parse_args()
    request = build_request(
        requested_by={
            "person_id": args.requester_id,
            "person_kind": args.requester_kind,
            "authorized": args.authorized,
        },
        request_type=args.request_type,
        request_text=args.request,
        details=json.loads(args.details_json),
    )
    path = save_request(request, args.output)
    print(json.dumps({"path": str(path), "status": request["status"], "clarifications_needed": request["clarifications_needed"], "activation_allowed": False}, indent=2))


if __name__ == "__main__":
    main()
