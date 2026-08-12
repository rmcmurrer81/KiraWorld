"""
Move loose audio files from Data/library/music/unsorted into music/artists.

This sorter is intentionally conservative. It only moves audio files that sit
directly in the unsorted folder, leaves album folders alone, and keeps duplicate
targets by adding a duplicate suffix.
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
DEFAULT_TARGET_ROOT = PROJECT_ROOT / "Data" / "library" / "music" / "artists"
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "indexes" / "audio_sort_plan.json"
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus"}

EXACT_OVERRIDES = {
    "anybody_have_a_map_from_the_dear_evan_hansen_original_broadway_cast_recording": (
        "dear_evan_hansen_original_broadway_cast",
        "anybody_have_a_map",
    ),
    "waving_through_a_window_from_the_dear_evan_hansen_original_broadway_cast_recording": (
        "dear_evan_hansen_original_broadway_cast",
        "waving_through_a_window",
    ),
    "the_fray_absolute_acoustic_version": ("the_fray", "absolute_acoustic_version"),
    "the_fray_fair_fight": ("the_fray", "fair_fight"),
    "the_fray_uncertainty": ("the_fray", "uncertainty"),
    "the_fray_where_the_story_ends_piano_version": ("the_fray", "where_the_story_ends_piano_version"),
    "the_fray_you_found_me_acoustic_version": ("the_fray", "you_found_me_acoustic_version"),
}


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _slug(value: str) -> str:
    return normalize_name(value, is_file=False)


def _clean_title(value: str) -> str:
    value = re.sub(r"\bOfficial Audio\b", " ", value, flags=re.I)
    value = re.sub(r"\bOfficial Music Video\b", " ", value, flags=re.I)
    value = re.sub(r"\bOfficial Video\b", " ", value, flags=re.I)
    value = re.sub(r"\bLyrics?\b", " ", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip(" -_.,")
    return value or "untitled"


def infer_artist_title(path: Path) -> tuple[str, str]:
    stem = path.stem.replace("%20", " ").replace("%28", " ").replace("%29", " ")
    exact_key = _slug(stem)
    if exact_key in EXACT_OVERRIDES:
        return EXACT_OVERRIDES[exact_key]

    match = re.match(r"(.+?)\s+-\s+(.+)", stem)
    if match:
        return _slug(match.group(1)), _slug(_clean_title(match.group(2)))

    from_match = re.match(r"(.+?)\s+from\s+the\s+(.+)", stem, flags=re.I)
    if from_match:
        title = _slug(_clean_title(from_match.group(1)))
        artist = _slug(_clean_title(from_match.group(2)))
        return artist, title

    return "unknown_artist", _slug(_clean_title(stem))


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
    if not source_dir.exists():
        files: list[Path] = []
    else:
        files = [path for path in sorted(source_dir.iterdir()) if path.is_file()]

    for path in files:
        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        artist, title = infer_artist_title(path)
        target = unique_target(target_root / artist / f"{artist}_{title}{path.suffix.lower()}")
        operations.append(
            {
                "source": _relative(path),
                "target": _relative(target),
                "artist": artist,
                "title": title,
                "blocked": False,
                "issues": [],
            }
        )

    return {
        "plan_id": "audio_sort_plan_v1",
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


def apply_plan(plan: dict[str, Any]) -> dict[str, Any]:
    applied: list[dict[str, str]] = []
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
        target = unique_target(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        applied.append({"source": operation["source"], "target": _relative(target)})
    return {"applied_count": len(applied), "skipped_count": len(skipped), "applied": applied, "skipped": skipped}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sort loose unsorted audio into music/artists folders.")
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
    print(f"Planned {plan['operation_count']} audio moves.")
    print(f"Blocked {plan['blocked_count']} operations.")
    if args.apply:
        result = plan["last_run"]["apply_result"]
        print(f"Applied {result['applied_count']} operations; skipped {result['skipped_count']}.")
    print(f"Wrote {_relative(output)}")


if __name__ == "__main__":
    main()
