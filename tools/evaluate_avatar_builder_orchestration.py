"""Print a fail-closed Avatar Builder route/capability decision.

This command is read-only.  It does not render, generate, stage, approve, or
activate an avatar, and it intentionally has no live-output option.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_builder_orchestration import evaluate_avatar_builder_orchestration
from Core.avatar_profile_preflight import (
    evaluate_orchestration_identity_preflight,
    identity_registry_available,
)


def read_request(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("Avatar Builder orchestration request must be a JSON object.")
    return data


def resolve_regular_request_path(path: Path) -> Path:
    """Resolve a regular request only after rejecting symlink path components."""

    absolute = Path(os.path.abspath(path.expanduser()))
    for component in (absolute, *absolute.parents):
        if component.is_symlink():
            raise FileNotFoundError(f"Request is symlinked: {absolute}")
    if not absolute.is_file():
        raise FileNotFoundError(f"Request is missing: {absolute}")
    return absolute.resolve(strict=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate an Avatar Builder capability route without mutation."
    )
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    request_path = resolve_regular_request_path(args.request)
    request = read_request(request_path)
    identity_preflight = (
        evaluate_orchestration_identity_preflight(PROJECT_ROOT, request)
        if identity_registry_available(PROJECT_ROOT)
        else None
    )
    result = evaluate_avatar_builder_orchestration(
        request, identity_preflight=identity_preflight
    )
    if args.compact:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["review_stage_allowed"] else 6


if __name__ == "__main__":
    raise SystemExit(main())
