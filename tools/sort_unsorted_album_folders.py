"""
Move regular music album folders from Data/library/music/unsorted.

This is for artist albums, not soundtrack/cast albums. It preserves track
numbers, normalizes filenames, and places albums under
Data/library/music/albums/<album_slug>/.
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
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "Data" / "library" / "music" / "unsorted"
DEFAULT_TARGET_ROOT = PROJECT_ROOT / "Data" / "library" / "music" / "albums"
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "indexes" / "album_sort_plan.json"
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus"}

ALBUM_OVERRIDES = {
    "bad_blood_all_this_bad_blood": "bastille_bad_blood_all_this_bad_blood_2013",
    "bob_seger_and_the_silver_bullet_band": "bob_seger_and_the_silver_bullet_band_collection",
    "breakaway_kelly_clarkson": "kelly_clarkson_breakaway_2004",
    "how_to_save_a_life": "the_fray_how_to_save_a_life_2005",
    "kidz_bop_vol_12": "kidz_bop_vol_12",
    "kidz_bop_vol_17_with_2_bonus_tracks": "kidz_bop_vol_17_2010",
    "kidz_bop_vol_22": "kidz_bop_vol_22",
    "kidz_bop_vol_6": "kidz_bop_vol_6",
    "like_a_prayer_madonna_1989": "madonna_like_a_prayer_1989",
    "rob_thomas_something_to_be_cd_album_europe_melisma_record": "rob_thomas_something_to_be_2005",
    "traveling_tunes_1": "traveling_tunes_1",
    "twisted_sister_were_not_gonna_take_it_2024_remaster": "twisted_sister_were_not_gonna_take_it_2024_remaster",
}


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _slug(value: str) -> str:
    return normalize_name(value, is_file=False)


def _clean_track_name(path: Path) -> str:
    stem = path.stem.replace("&", " and ")
    match = re.match(r"^\s*(\d{1,3})[\s.]+(.+)$", stem)
    if match:
        track = int(match.group(1))
        title = _slug(match.group(2))
        return f"{track:02d}_{title}{path.suffix.lower()}"
    return normalize_name(path.name, is_file=True)


def album_slug(folder: Path) -> str:
    slug = _slug(folder.name)
    return ALBUM_OVERRIDES.get(slug, "")


def unique_target(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}_duplicate_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def build_plan(source_dir: Path = DEFAULT_SOURCE_DIR, target_root: Path = DEFAULT_TARGET_ROOT) -> dict[str, Any]:
    operations: list[dict[str, Any]] = []
    folders = [path for path in sorted(source_dir.iterdir()) if path.is_dir()] if source_dir.exists() else []

    for folder in folders:
        album = album_slug(folder)
        if not album:
            continue
        audio_files = [path for path in sorted(folder.rglob("*")) if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS]
        for path in audio_files:
            relative_subdir = path.parent.relative_to(folder)
            target_dir = target_root / album / relative_subdir
            target = unique_target(target_dir / _clean_track_name(path))
            operations.append(
                {
                    "source": _relative(path),
                    "target": _relative(target),
                    "album": album,
                    "blocked": False,
                    "issues": [],
                }
            )

    return {
        "plan_id": "album_sort_plan_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": _relative(source_dir),
        "target_root": _relative(target_root),
        "operation_count": len(operations),
        "blocked_count": sum(1 for item in operations if item["blocked"]),
        "operations": operations,
    }


def _project_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _remove_empty_parents(path: Path, stop_at: Path) -> None:
    current = path
    stop = stop_at.resolve()
    while current.exists() and current.resolve() != stop:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def apply_plan(plan: dict[str, Any]) -> dict[str, Any]:
    applied: list[dict[str, str]] = []
    skipped: list[dict[str, Any]] = []
    source_root = _project_path(str(plan["source_dir"]))
    for operation in plan.get("operations", []):
        if operation.get("blocked"):
            skipped.append(operation)
            continue
        source = _project_path(str(operation["source"]))
        target = _project_path(str(operation["target"]))
        if not source.exists():
            skipped.append({**operation, "issues": [*operation.get("issues", []), "source_missing"]})
            continue
        target = unique_target(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        applied.append({"source": operation["source"], "target": _relative(target)})
        _remove_empty_parents(source.parent, source_root)
    return {"applied_count": len(applied), "skipped_count": len(skipped), "applied": applied, "skipped": skipped}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sort unsorted regular music album folders.")
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR))
    parser.add_argument("--target-root", default=str(DEFAULT_TARGET_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    if not source_dir.is_absolute():
        source_dir = PROJECT_ROOT / source_dir
    target_root = Path(args.target_root)
    if not target_root.is_absolute():
        target_root = PROJECT_ROOT / target_root
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output

    plan = build_plan(source_dir, target_root)
    if args.apply:
        plan["last_run"] = {"apply_requested": True, "apply_result": apply_plan(plan)}
        plan = build_plan(source_dir, target_root) | {"last_run": plan["last_run"]}
    else:
        plan["last_run"] = {"apply_requested": False, "apply_result": None}
    write_json(output, plan)
    print(f"Planned {plan['operation_count']} album moves.")
    print(f"Blocked {plan['blocked_count']} operations.")
    if args.apply:
        result = plan["last_run"]["apply_result"]
        print(f"Applied {result['applied_count']} operations; skipped {result['skipped_count']}.")
    print(f"Wrote {_relative(output)}")


if __name__ == "__main__":
    main()
