#!/usr/bin/env python3
"""Launch the bounded private inactive anatomy authoring controller."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from Core.avatar_inactive_anatomy_authoring import (  # noqa: E402
    InactiveAnatomyAuthoringError,
    execute_private_inactive_anatomy_authoring,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run Blender only for a READY anatomy preflight and retain a new private, "
            "inactive, unreviewed anatomy workspace."
        )
    )
    parser.add_argument("--project-root", default=str(REPOSITORY_ROOT))
    parser.add_argument("--request", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--blender", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = execute_private_inactive_anatomy_authoring(
            args.project_root,
            request_path=args.request,
            run_id=args.run_id,
            blender_path=args.blender,
            timeout_seconds=args.timeout_seconds,
        )
    except (InactiveAnatomyAuthoringError, OSError) as exc:
        error = {
            "schema": "kira.avatar.private_inactive_anatomy_controller_error.v1",
            "status": "PRIVATE_INACTIVE_AUTHORING_REFUSED_OR_FAILED",
            "output_retained": None,
            "failed_output_quarantine_policy": "retained_if_fresh_output_was_created",
            "automatic_recursive_cleanup_performed": False,
            "function_implemented": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
            "error": str(exc),
        }
        print(
            json.dumps(error, sort_keys=True, separators=(",", ":"), allow_nan=False),
            file=sys.stderr,
        )
        return 9
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
