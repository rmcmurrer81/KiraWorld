"""Prepare one inert v2 Avatar Builder visual-intake plan.

This command does not call Ollama, use a GPU, decode video, launch Blender, or
mutate an avatar. The caller supplies only a request-document path and a safe
logical output name. The implementation loads authority and media metadata
from the fixed hash-bound project registry, then creates one new JSON file in
the dedicated v2 plan directory. Existing files are never overwritten.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_builder_qwen35_visual_intake_v2 import (  # noqa: E402
    prepare_avatar_visual_intake_v2,
    write_plan_no_clobber_v2,
)


def _project_request_path(project_root: Path, value: str) -> Path:
    supplied = project_root / value
    current = supplied
    while True:
        if current.is_symlink():
            raise ValueError("request document may not traverse a symlink")
        if current == project_root or current.parent == current:
            break
        current = current.parent
    candidate = supplied.resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError as exc:
        raise ValueError("request document must remain inside the project") from exc
    if not candidate.is_file():
        raise ValueError("request document must be an existing regular project file")
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a static, inert, exact-digest Qwen3.5 Avatar Builder visual-intake plan."
    )
    parser.add_argument(
        "--request",
        required=True,
        help="Project-relative JSON request path; it cannot contain media authority.",
    )
    parser.add_argument(
        "--output-name",
        required=True,
        help="Safe logical name. Output is always a new JSON file in the dedicated v2 plan root.",
    )
    args = parser.parse_args()

    root = PROJECT_ROOT.resolve(strict=True)
    request_path = _project_request_path(root, args.request)
    request = json.loads(request_path.read_text(encoding="utf-8-sig"))
    if not isinstance(request, dict):
        raise ValueError("request document must contain one JSON object")
    plan = prepare_avatar_visual_intake_v2(root, request)
    destination = write_plan_no_clobber_v2(root, args.output_name, plan)
    print(destination.relative_to(root).as_posix())
    print(plan["plan_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
