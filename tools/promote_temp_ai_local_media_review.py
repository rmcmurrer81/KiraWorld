"""Validate human review and promote only clean identity-bound evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_local_media_intake import promote_reviewed_evidence, read_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack_dir")
    parser.add_argument("--review", default="", help="Defaults to PACK_DIR/human_review.json")
    args = parser.parse_args()
    pack_dir = Path(args.pack_dir).resolve()
    review_path = Path(args.review).resolve() if args.review else pack_dir / "human_review.json"
    result = promote_reviewed_evidence(pack_dir, read_json(review_path, {}))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
