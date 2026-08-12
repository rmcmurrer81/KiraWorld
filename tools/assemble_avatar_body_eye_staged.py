"""CLI for exact-hash private/inactive body + eye-rig staging.

The command is a dry run unless ``--execute`` is supplied.  A dry run creates
no directory and changes no files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Core.avatar_body_eye_staged_assembly import (  # noqa: E402
    StagedAssemblyError,
    build_dry_run_plan,
    execute_staged_assembly,
)


DEFAULT_BLENDER = Path(
    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate or stage one exact body GLB plus separate eye-rig GLB."
    )
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--subject-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--body", required=True, help="Project-relative body GLB")
    parser.add_argument("--body-sha256", required=True)
    parser.add_argument("--eyes", required=True, help="Project-relative eye-rig GLB")
    parser.add_argument("--eyes-sha256", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--blender", default=str(DEFAULT_BLENDER))
    parser.add_argument("--timeout-seconds", type=int, default=900)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    common = {
        "subject_id": args.subject_id,
        "run_id": args.run_id,
        "body_path": args.body,
        "body_sha256": args.body_sha256,
        "eye_path": args.eyes,
        "eye_sha256": args.eyes_sha256,
    }
    try:
        if args.execute:
            result = execute_staged_assembly(
                args.project_root,
                **common,
                blender_path=args.blender,
                timeout_seconds=args.timeout_seconds,
            )
        else:
            result = build_dry_run_plan(args.project_root, **common)
    except StagedAssemblyError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "status": "rejected_fail_closed",
                    "error": str(exc),
                    "execution_started": False,
                    "runtime_activation_allowed": False,
                    "live_body_replacement_allowed": False,
                    "release_allowed": False,
                },
                indent=2,
            )
        )
        return 2
    print(json.dumps({"ok": True, **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

