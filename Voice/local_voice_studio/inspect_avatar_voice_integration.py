"""Print the read-only live Avatar/Temporary Creator voice-audition plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


STUDIO_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = STUDIO_ROOT.parents[1]
SOURCE_ROOT = STUDIO_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from kira_local_voice.avatar_voice_integration import build_live_avatar_voice_plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect exact current voice gaps and print nonbinding audition briefs."
    )
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--audition-locale", default="en-US")
    parser.add_argument("--candidate-count", type=int, default=3)
    args = parser.parse_args()
    plan = build_live_avatar_voice_plan(
        args.project_root,
        audition_locale=args.audition_locale,
        candidate_count=args.candidate_count,
    )
    print(json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
