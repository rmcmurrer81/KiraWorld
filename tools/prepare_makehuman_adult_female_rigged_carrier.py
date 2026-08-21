#!/usr/bin/env python3
"""Print a read-only preflight for one inactive rigged-carrier build.

The controller never starts Blender and never writes an authorization or an
output artifact.  A ready result without ``--authorization`` means only that
the exact inputs are internally consistent and the append-only output paths
are absent.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_makehuman_rigged_carrier import (  # noqa: E402
    RiggedCarrierError,
    prepare_preflight,
)


DEFAULT_CONFIG = PROJECT_ROOT / (
    "Avatar/avatar_builder/tooling/"
    "makehuman_adult_female_rigged_carrier_v1.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--blender-exe")
    parser.add_argument("--authorization")
    return parser.parse_args()


def _path(value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def main() -> int:
    args = parse_args()
    config = _path(args.config)
    if config is None:
        raise RiggedCarrierError("config is required")
    report = prepare_preflight(
        PROJECT_ROOT,
        config,
        blender_executable=_path(args.blender_exe),
        authorization_path=_path(args.authorization),
    )
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RiggedCarrierError as exc:
        print(
            json.dumps(
                {
                    "status": "PREFLIGHT_REJECTED",
                    "error": str(exc),
                    "blender_invoked": False,
                    "output_created": False,
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
