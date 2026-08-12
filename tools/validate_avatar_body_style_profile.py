"""Validate a declarative adult body-style profile without invoking Blender."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_body_style_profile import (
    DEFAULT_PROFILE_PATH,
    validate_body_style_profile,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed validation of identity-free confirmed-adult styling, "
            "hash-bound MakeHuman targets, and material/eye/hair metadata."
        )
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE_PATH.as_posix(),
        help="Safe project-relative JSON profile path.",
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    report = validate_body_style_profile(PROJECT_ROOT, Path(args.profile))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
