#!/usr/bin/env python3
"""Blender entrypoint for one preflight-ready private inactive anatomy job."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence


def _worker_arguments(argv: Sequence[str]) -> list[str]:
    values = list(argv)
    return values[values.index("--") + 1 :] if "--" in values else values


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Author one READY package as a separate private inactive Blender copy."
    )
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--job", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw_arguments = sys.argv[1:] if argv is None else argv
    args = _parser().parse_args(_worker_arguments(raw_arguments))
    project_root = Path(args.project_root)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    try:
        import bpy  # type: ignore[import-not-found]
        from mathutils import Matrix  # type: ignore[import-not-found]

        from Core.avatar_inactive_anatomy_authoring import (
            BpyInactiveAnatomySceneAdapter,
            run_blender_authoring_job,
        )

        result = run_blender_authoring_job(
            project_root,
            job_path=args.job,
            adapter=BpyInactiveAnatomySceneAdapter(bpy, Matrix),
        )
    except BaseException as exc:
        error = {
            "schema": "kira.avatar.private_inactive_anatomy_worker_error.v1",
            "status": "PRIVATE_INACTIVE_AUTHORING_FAILED",
            "build_retained": False,
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
