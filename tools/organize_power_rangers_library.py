"""
Organize Power Rangers library files into season-safe folders.

Power Rangers has franchise seasons plus anniversary specials and movies. This
tool keeps one-off specials from floating loose while preserving chronology.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY_ROOT = PROJECT_ROOT / "Data" / "library"
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "indexes" / "power_rangers_organize_plan.json"
POWER_RANGERS_ROOT = Path("tv_shows") / "power_rangers"

KNOWN_MOVES = {
    "Power Rangers III - Once & Always.mp4": (
        "s29_s30_specials/power_rangers_s29_s30_special_once_and_always_2023.mp4"
    ),
    "cosmic_fury/Power Rangers - S30E01 - Lightning Strikes (1080p x265 EDGE2023).mp4": (
        "s30_cosmic_fury/power_rangers_cosmic_fury_s30e01_lightning_strikes.mp4"
    ),
    "cosmic_fury/Power Rangers - S30E02 - Beyond Repair (1080p x265 EDGE2023).mp4": (
        "s30_cosmic_fury/power_rangers_cosmic_fury_s30e02_beyond_repair.mp4"
    ),
    "cosmic_fury/Power Rangers - S30E03 - Off Grid (1080p x265 EDGE2023).mp4": (
        "s30_cosmic_fury/power_rangers_cosmic_fury_s30e03_off_grid.mp4"
    ),
    "cosmic_fury/Power Rangers - S30E04 - Team Work (1080p x265 EDGE2023).mp4": (
        "s30_cosmic_fury/power_rangers_cosmic_fury_s30e04_team_work.mp4"
    ),
    "cosmic_fury/Power Rangers - S30E05 - Rock Out (1080p x265 EDGE2023).mp4": (
        "s30_cosmic_fury/power_rangers_cosmic_fury_s30e05_rock_out.mp4"
    ),
    "cosmic_fury/Power Rangers - S30E06 - Take Off (1080p x265 EDGE2023).mp4": (
        "s30_cosmic_fury/power_rangers_cosmic_fury_s30e06_take_off.mp4"
    ),
    "cosmic_fury/Power Rangers - S30E07 - Operation Seasoning (1080p x265 EDGE2023).mp4": (
        "s30_cosmic_fury/power_rangers_cosmic_fury_s30e07_operation_seasoning.mp4"
    ),
    "cosmic_fury/Power Rangers - S30E08 Switches Sides - (1080p x265 EDGE2023).mp4": (
        "s30_cosmic_fury/power_rangers_cosmic_fury_s30e08_switches_sides.mp4"
    ),
    "cosmic_fury/Power Rangers - S30E09 - Master Plan (1080p x265 EDGE2023).mp4": (
        "s30_cosmic_fury/power_rangers_cosmic_fury_s30e09_master_plan.mp4"
    ),
    "cosmic_fury/Power Rangers - S30E10 - The End (1080p x265 EDGE2023).mp4": (
        "s30_cosmic_fury/power_rangers_cosmic_fury_s30e10_the_end.mp4"
    ),
}


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def build_plan(library_root: Path = DEFAULT_LIBRARY_ROOT) -> dict[str, Any]:
    ranger_root = library_root / POWER_RANGERS_ROOT
    operations = []
    skipped = []
    if not ranger_root.exists():
        return {
            "plan_id": "power_rangers_organize_plan_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "power_rangers_root": _relative(ranger_root),
            "operation_count": 0,
            "blocked_count": 0,
            "skipped_count": 1,
            "operations": [],
            "skipped": [{"path": _relative(ranger_root), "issues": ["power_rangers_root_missing"]}],
        }

    for source_relative, target_relative in KNOWN_MOVES.items():
        source = ranger_root / source_relative
        target = ranger_root / target_relative
        if not source.exists():
            skipped.append(
                {
                    "source": _relative(source),
                    "target": _relative(target),
                    "issues": ["source_missing_already_moved" if target.exists() else "source_missing"],
                }
            )
            continue
        blocked = target.exists()
        operations.append(
            {
                "source": _relative(source),
                "target": _relative(target),
                "blocked": blocked,
                "issues": ["target_exists"] if blocked else [],
            }
        )

    return {
        "plan_id": "power_rangers_organize_plan_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "power_rangers_root": _relative(ranger_root),
        "rules": {
            "season_folders_use_global_franchise_season_numbers": True,
            "once_and_always_kept_as_s29_s30_special": True,
            "cosmic_fury_is_s30": True,
            "does_not_overwrite": True,
        },
        "operation_count": len(operations),
        "blocked_count": sum(1 for operation in operations if operation["blocked"]),
        "skipped_count": len(skipped),
        "operations": operations,
        "skipped": skipped,
    }


def apply_plan(plan: dict[str, Any]) -> dict[str, Any]:
    moved = []
    skipped = []
    for operation in plan.get("operations", []):
        if operation.get("blocked"):
            skipped.append(operation)
            continue
        source = PROJECT_ROOT / operation["source"]
        target = PROJECT_ROOT / operation["target"]
        if not source.exists():
            skipped.append({**operation, "issues": [*operation.get("issues", []), "source_missing"]})
            continue
        if target.exists():
            skipped.append({**operation, "issues": [*operation.get("issues", []), "target_exists"]})
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        moved.append({"source": operation["source"], "target": operation["target"]})
    return {"moved_count": len(moved), "skipped_count": len(skipped), "moved": moved, "skipped": skipped}


def remove_empty_dirs(root: Path) -> list[str]:
    removed = []
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if not path.is_dir():
            continue
        try:
            path.rmdir()
        except OSError:
            continue
        removed.append(_relative(path))
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description="Organize Power Rangers season/special files.")
    parser.add_argument("--library-root", default=str(DEFAULT_LIBRARY_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    library_root = Path(args.library_root)
    if not library_root.is_absolute():
        library_root = PROJECT_ROOT / library_root
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output

    plan = build_plan(library_root)
    if args.apply:
        result = apply_plan(plan)
        ranger_root = library_root / POWER_RANGERS_ROOT
        result["removed_empty_dirs"] = remove_empty_dirs(ranger_root) if ranger_root.exists() else []
        plan = build_plan(library_root) | {"last_run": {"apply_requested": True, "apply_result": result}}
    else:
        plan["last_run"] = {"apply_requested": False, "apply_result": None}

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Power Rangers operations: {plan['operation_count']}")
    print(f"Power Rangers blocked: {plan['blocked_count']}")
    print(f"Power Rangers skipped: {plan['skipped_count']}")
    if args.apply:
        result = plan["last_run"]["apply_result"]
        print(f"Moved {result['moved_count']}; skipped {result['skipped_count']}.")
    print(f"Wrote {_relative(output)}")


if __name__ == "__main__":
    main()
