"""
Detect local Data/library changes since the last media library index.

This tool only reports differences. It never renames, moves, or deletes files.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_media_library_index import DEFAULT_LIBRARY_ROOT, DEFAULT_OUTPUT as DEFAULT_INDEX_PATH
from build_media_library_index import build_index


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "indexes" / "media_library_update_check.json"


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _entry_map(index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        entry["path"]: entry
        for entry in index.get("entries", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }


def _load_previous_index(index_path: Path) -> dict[str, Any] | None:
    if not index_path.exists():
        return None
    return json.loads(index_path.read_text(encoding="utf-8"))


def check_updates(
    library_root: Path = DEFAULT_LIBRARY_ROOT,
    index_path: Path = DEFAULT_INDEX_PATH,
) -> dict[str, Any]:
    previous_index = _load_previous_index(index_path)
    current_index = build_index(library_root)

    previous_entries = _entry_map(previous_index or {})
    current_entries = _entry_map(current_index)

    previous_paths = set(previous_entries)
    current_paths = set(current_entries)

    added = [current_entries[path] for path in sorted(current_paths - previous_paths)]
    removed = [previous_entries[path] for path in sorted(previous_paths - current_paths)]
    changed: list[dict[str, Any]] = []

    for path in sorted(previous_paths & current_paths):
        previous = previous_entries[path]
        current = current_entries[path]
        changes: dict[str, dict[str, Any]] = {}
        for key in ("extension", "media_type", "category", "size_bytes"):
            if previous.get(key) != current.get(key):
                changes[key] = {"previous": previous.get(key), "current": current.get(key)}
        if changes:
            changed.append({"path": path, "changes": changes})

    return {
        "check_id": "media_library_update_check_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "library_root": _relative(library_root),
        "index_path": _relative(index_path),
        "previous_index_found": previous_index is not None,
        "current_file_count": current_index["entry_count"],
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
        "needs_index_refresh": bool(added or removed or changed or previous_index is None),
        "rules": {
            "detects_new_files": True,
            "detects_removed_files": True,
            "detects_size_or_classification_changes": True,
            "does_not_modify_library": True,
            "does_not_refresh_index_automatically": True,
        },
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Data/library for changes since the saved media index.")
    parser.add_argument("--library-root", default=str(DEFAULT_LIBRARY_ROOT))
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    library_root = Path(args.library_root)
    if not library_root.is_absolute():
        library_root = PROJECT_ROOT / library_root
    index_path = Path(args.index)
    if not index_path.is_absolute():
        index_path = PROJECT_ROOT / index_path
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output

    result = check_updates(library_root, index_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        "Media library changes: "
        f"{result['added_count']} added, "
        f"{result['removed_count']} removed, "
        f"{result['changed_count']} changed."
    )
    if result["needs_index_refresh"]:
        print("Index refresh recommended: run tools/build_media_library_index.py")
    else:
        print("Saved media library index is current.")
    print(f"Wrote {_relative(output)}")


if __name__ == "__main__":
    main()
