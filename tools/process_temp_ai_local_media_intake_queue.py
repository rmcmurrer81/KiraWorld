"""Process a tiny, explicit batch of bounded private-local intake requests."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_local_media_intake import (  # noqa: E402
    QUEUE_HARD_CAP,
    discover_queued_requests,
    extract_candidate_pack,
    read_json,
    validate_intake_request,
)

LOCK_PATH = PROJECT_ROOT / "Data" / "voice" / "temp_ai_private_local_media_intake.lock"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run or explicitly execute up to three bounded private-local intake requests."
    )
    parser.add_argument("--max-requests", type=int, default=1)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually extract only the exact short ranges in each authorized request. Default is dry-run.",
    )
    args = parser.parse_args()
    if args.max_requests < 1 or args.max_requests > QUEUE_HARD_CAP:
        parser.error(f"--max-requests must be between 1 and {QUEUE_HARD_CAP}")

    request_paths = discover_queued_requests(max_requests=args.max_requests)
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "dry_run_no_media_read",
                    "selected_requests": [str(path) for path in request_paths],
                    "request_count": len(request_paths),
                },
                indent=2,
            )
        )
        return 0

    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock = LOCK_PATH.open("x", encoding="utf-8")
    except FileExistsError:
        print(f"Another private-local intake worker appears active: {LOCK_PATH}", file=sys.stderr)
        return 2
    results: list[dict[str, object]] = []
    try:
        with lock:
            json.dump({"pid": os.getpid(), "purpose": "bounded_private_local_media_intake"}, lock)
        for request_path in request_paths:
            try:
                request = read_json(request_path, {})
                validate_intake_request(request, expected_candidate_id=request_path.parents[4].name)
                manifest = extract_candidate_pack(request)
                results.append(
                    {
                        "request": str(request_path),
                        "status": manifest["status"],
                        "pack_id": manifest["pack_id"],
                        "segments": len(manifest["segments"]),
                    }
                )
            except Exception as exc:  # bounded worker reports per-request failures
                results.append({"request": str(request_path), "status": "error", "error": str(exc)[:1000]})
    finally:
        LOCK_PATH.unlink(missing_ok=True)
    print(json.dumps({"status": "complete", "results": results}, indent=2))
    return 1 if any(item["status"] == "error" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
