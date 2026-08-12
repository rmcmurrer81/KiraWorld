"""Create an inert Avatar Builder Qwen 3.5 visual-intake plan.

This command verifies private project sources and the canonical avatar profile,
then writes a plan. It deliberately has no network/Ollama/Blender code.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_builder_qwen35_visual_intake import prepare_avatar_visual_intake


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify and prepare a static Qwen 3.5 Avatar Builder visual intake."
    )
    parser.add_argument("request", type=Path, help="Project-relative JSON request")
    parser.add_argument("output", type=Path, help="Project-relative plan destination")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Kira project root (defaults to current directory)",
    )
    return parser


def _below(root: Path, path: Path, field: str) -> Path:
    candidate = path if path.is_absolute() else root / path
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{field} must stay inside the project") from exc
    return resolved


def main() -> int:
    args = _parser().parse_args()
    root = args.project_root.resolve(strict=True)
    request_path = _below(root, args.request, "request")
    output_path = _below(root, args.output, "output")
    if not request_path.is_file():
        raise ValueError("request must be an existing JSON file")
    request = json.loads(request_path.read_text(encoding="utf-8-sig"))
    if not isinstance(request, dict):
        raise ValueError("request JSON must be an object")
    plan = prepare_avatar_visual_intake(root, request)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": plan["execution"]["status"],
        "plan_sha256": plan["plan_sha256"],
        "output": output_path.relative_to(root).as_posix(),
        "ollama_called": False,
        "blender_called": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
