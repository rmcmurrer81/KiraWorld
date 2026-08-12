"""
Normalize Out of This World episodes into season folders.

The library currently has two filename styles mixed together:
plain `Out Of This World s1e1.mp4` files and titled `S01E02 - Title.mp4`
files. This tool gives both styles one predictable target layout.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_rename_media_library import normalize_name


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHOW_ROOT = PROJECT_ROOT / "Data" / "library" / "tv_shows" / "out_of_this_world"
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "indexes" / "out_of_this_world_organize_plan.json"
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".m4v"}


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _slug(value: str) -> str:
    return normalize_name(value, is_file=False)


def _episode_target(path: Path, show_root: Path) -> Path | None:
    if path.suffix.lower() not in VIDEO_EXTENSIONS:
        return None
    if path.parent != show_root:
        return None

    stem = path.stem.strip()
    titled = re.match(r"^S(\d{2})E(\d{2})\s*-\s*(.+)$", stem, flags=re.IGNORECASE)
    if titled:
        season = int(titled.group(1))
        episode = int(titled.group(2))
        title = re.sub(r"\[[^\]]+\]", " ", titled.group(3)).strip()
        title_slug = _slug(title)
        filename = f"out_of_this_world_s{season:02d}e{episode:02d}_{title_slug}{path.suffix.lower()}"
        return show_root / f"s{season:02d}" / filename

    plain = re.match(r"^Out Of This World\s+s(\d+)e(\d+)$", stem, flags=re.IGNORECASE)
    if plain:
        season = int(plain.group(1))
        episode = int(plain.group(2))
        filename = f"out_of_this_world_s{season:02d}e{episode:02d}{path.suffix.lower()}"
        return show_root / f"s{season:02d}" / filename

    return None


def _unique_target(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}_duplicate_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def build_plan(show_root: Path = DEFAULT_SHOW_ROOT) -> dict[str, Any]:
    operations: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    if not show_root.exists():
        skipped.append({"path": _relative(show_root), "issues": ["show_root_missing"]})
    else:
        for path in sorted(show_root.iterdir()):
            if not path.is_file():
                continue
            target = _episode_target(path, show_root)
            if target is None:
                skipped.append({"path": _relative(path), "issues": ["unrecognized_episode_name"]})
                continue
            target = _unique_target(target)
            operations.append(
                {
                    "source": _relative(path),
                    "target": _relative(target),
                    "blocked": False,
                    "issues": [],
                }
            )

    return {
        "plan_id": "out_of_this_world_organize_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "show_root": _relative(show_root),
        "rules": {
            "uses_season_folders": True,
            "keeps_existing_titles_when_present": True,
            "does_not_overwrite": True,
        },
        "operation_count": len(operations),
        "blocked_count": sum(1 for operation in operations if operation["blocked"]),
        "skipped_count": len(skipped),
        "operations": operations,
        "skipped": skipped,
    }


def _project_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def apply_plan(plan: dict[str, Any]) -> dict[str, Any]:
    moved: list[dict[str, str]] = []
    skipped: list[dict[str, Any]] = []
    for operation in plan.get("operations", []):
        if operation.get("blocked"):
            skipped.append(operation)
            continue
        source = _project_path(str(operation["source"]))
        target = _project_path(str(operation["target"]))
        if not source.exists():
            skipped.append({**operation, "issues": [*operation.get("issues", []), "source_missing"]})
            continue
        target = _unique_target(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        moved.append({"source": operation["source"], "target": _relative(target)})
    return {"moved_count": len(moved), "skipped_count": len(skipped), "moved": moved, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Organize Out of This World episodes into season folders.")
    parser.add_argument("--show-root", default=str(DEFAULT_SHOW_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    show_root = Path(args.show_root)
    if not show_root.is_absolute():
        show_root = PROJECT_ROOT / show_root
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output

    plan = build_plan(show_root)
    if args.apply:
        plan["last_run"] = {"apply_requested": True, "apply_result": apply_plan(plan)}
        plan = build_plan(show_root) | {"last_run": plan["last_run"]}
    else:
        plan["last_run"] = {"apply_requested": False, "apply_result": None}

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Out of This World operations: {plan['operation_count']}")
    print(f"Out of This World skipped: {plan['skipped_count']}")
    if args.apply:
        result = plan["last_run"]["apply_result"]
        print(f"Moved {result['moved_count']}; skipped {result['skipped_count']}.")
    print(f"Wrote {_relative(output)}")


if __name__ == "__main__":
    main()
