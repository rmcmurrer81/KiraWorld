"""Build one exact-hash-authorized strict-v2 procedural notebook preview."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from notebook_world_preview_backend import PROJECT_ROOT, build_authorized_preview
except ModuleNotFoundError:  # Imported as tools.build_notebook_world_preview.
    from tools.notebook_world_preview_backend import PROJECT_ROOT, build_authorized_preview


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path, help="Strict-v2 notebook_world_request.json")
    parser.add_argument("--program", required=True, type=Path, help="Request-local procedural_scene_program.json")
    parser.add_argument(
        "--authorization",
        required=True,
        type=Path,
        help="Request-local exact-hash preview_scope_authorization.json",
    )
    parser.add_argument("--build-id", required=True, help="Authorized immutable preview build id")
    args = parser.parse_args()

    result = build_authorized_preview(
        request_path=args.request,
        program_path=args.program,
        authorization_path=args.authorization,
        build_id=args.build_id,
        root=PROJECT_ROOT,
    )
    print(
        json.dumps(
            {
                "status": "prototype_draft_not_final_not_approved",
                "world_id": result.world_id,
                "request_id": result.request_id,
                "build_id": result.build_id,
                "build_root": result.build_root.relative_to(PROJECT_ROOT).as_posix(),
                "entrypoint": result.entrypoint_path.relative_to(PROJECT_ROOT).as_posix(),
                "registration": result.registration_path.relative_to(PROJECT_ROOT).as_posix(),
                "manifest": result.manifest_path.relative_to(PROJECT_ROOT).as_posix(),
                "manifest_sha256": result.manifest_sha256,
                "actual_budget": result.actual_budget,
                "home_world_mutation": False,
                "runtime_registered": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

