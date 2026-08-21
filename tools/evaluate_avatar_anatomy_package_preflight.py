#!/usr/bin/env python3
"""Evaluate one anatomy-package request without invoking Blender or writing files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from Core.avatar_anatomy_package import (  # noqa: E402
    AvatarAnatomyPackageError,
    READY_FOR_PRIVATE_INACTIVE_AUTHORING,
    evaluate_avatar_anatomy_package_preflight,
    load_preflight_request,
)


EXIT_READY = 0
EXIT_BLOCKED = 3
EXIT_INVALID = 6


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a source-bound adult-anatomy package for private inactive "
            "authoring. This command is read-only and does not invoke Blender."
        )
    )
    parser.add_argument(
        "--project-root",
        default=str(REPOSITORY_ROOT),
        help="Project root that contains every bound input (default: repository root).",
    )
    parser.add_argument(
        "--request",
        required=True,
        help="Safe project-relative path to the version-1 preflight request JSON.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit compact canonical JSON instead of indented JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        project_root = Path(args.project_root)
        request = load_preflight_request(project_root, args.request)
        report = evaluate_avatar_anatomy_package_preflight(project_root, request)
    except (AvatarAnatomyPackageError, OSError) as exc:
        error = {
            "schema": "kira.avatar.anatomy_package_preflight_error.v1",
            "status": "INVALID_PREFLIGHT_REQUEST",
            "preflight_performed": False,
            "build_performed": False,
            "blender_invoked": False,
            "error": str(exc),
        }
        print(
            json.dumps(
                error,
                sort_keys=True,
                separators=(",", ":") if args.compact else None,
                indent=None if args.compact else 2,
                ensure_ascii=False,
                allow_nan=False,
            ),
            file=sys.stderr,
        )
        return EXIT_INVALID
    print(
        json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":") if args.compact else None,
            indent=None if args.compact else 2,
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    return (
        EXIT_READY
        if report["status"] == READY_FOR_PRIVATE_INACTIVE_AUTHORING
        else EXIT_BLOCKED
    )


if __name__ == "__main__":
    raise SystemExit(main())
