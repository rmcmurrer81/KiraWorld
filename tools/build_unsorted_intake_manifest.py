"""
Build a review manifest for Data/library/unsorted.

This does not move, rename, or delete anything. It records folder hints,
rough subtypes, obvious duplicate candidates, and questions for Robert.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_media_library_index import DEFAULT_LIBRARY_ROOT, PROJECT_ROOT, classify_file, unsorted_intake_for


DEFAULT_UNSORTED_ROOT = DEFAULT_LIBRARY_ROOT / "unsorted"
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "indexes" / "unsorted_intake_manifest.json"
HASH_LIMIT_BYTES = 256 * 1024 * 1024


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256(path: Path) -> str | None:
    if path.stat().st_size > HASH_LIMIT_BYTES:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(unsorted_root: Path = DEFAULT_UNSORTED_ROOT) -> dict[str, Any]:
    files = sorted(path for path in unsorted_root.rglob("*") if path.is_file())
    entries: list[dict[str, Any]] = []
    counts_by_top_folder: Counter[str] = Counter()
    counts_by_subtype: Counter[str] = Counter()
    counts_by_extension: Counter[str] = Counter()
    hash_groups: dict[tuple[int, str], list[str]] = defaultdict(list)
    unknowns: list[dict[str, str]] = []

    for path in files:
        if path.name.lower() in {"thumbs.db", "desktop.ini"}:
            continue
        rel_parts = path.relative_to(unsorted_root).parts
        top_folder = rel_parts[0] if len(rel_parts) > 1 else "_root"
        classification = classify_file(path, DEFAULT_LIBRARY_ROOT)
        intake = unsorted_intake_for(path, DEFAULT_LIBRARY_ROOT) or {}
        subtype = str(intake.get("subtype", "unknown_unsorted_item"))
        confidence = str(intake.get("confidence", "low"))
        counts_by_top_folder[top_folder] += 1
        counts_by_subtype[subtype] += 1
        counts_by_extension[path.suffix.lower()] += 1

        digest = _sha256(path)
        if digest:
            hash_groups[(path.stat().st_size, digest)].append(_relative(path))
        if subtype == "unknown_unsorted_item" or confidence == "low":
            unknowns.append(
                {
                    "path": _relative(path),
                    "folder_hint": str(intake.get("folder_hint", "")),
                    "question": "What is this item, and should it stay as an unsorted reference clip or move into a specific collection?",
                }
            )

        entries.append(
            {
                "path": _relative(path),
                "name": path.name,
                "extension": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "top_folder": top_folder,
                "media_type": classification["media_type"],
                "category": classification["category"],
                "intake": intake,
            }
        )

    exact_duplicate_groups = [
        {"size_bytes": size, "sha256": digest, "paths": paths}
        for (size, digest), paths in sorted(hash_groups.items())
        if len(paths) > 1
    ]

    return {
        "manifest_id": "unsorted_intake_manifest_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "unsorted_root": _relative(unsorted_root),
        "file_count": len(entries),
        "counts_by_top_folder": dict(sorted(counts_by_top_folder.items())),
        "counts_by_subtype": dict(sorted(counts_by_subtype.items())),
        "counts_by_extension": dict(sorted(counts_by_extension.items())),
        "exact_duplicate_group_count": len(exact_duplicate_groups),
        "exact_duplicate_groups": exact_duplicate_groups,
        "questions_for_robert": unknowns[:100],
        "rules": {
            "does_not_move_files": True,
            "does_not_delete_duplicates": True,
            "unsure_items_stay_in_unsorted": True,
            "clips_commercials_fan_edits_are_reference_material": True,
        },
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a review manifest for Data/library/unsorted.")
    parser.add_argument("--unsorted-root", default=str(DEFAULT_UNSORTED_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    unsorted_root = Path(args.unsorted_root)
    if not unsorted_root.is_absolute():
        unsorted_root = PROJECT_ROOT / unsorted_root
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output

    manifest = build_manifest(unsorted_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {manifest['file_count']} unsorted intake entries to {_relative(output)}")
    print(f"Exact duplicate groups: {manifest['exact_duplicate_group_count']}")
    print("Subtype counts:")
    for subtype, count in manifest["counts_by_subtype"].items():
        print(f"  {subtype}: {count}")


if __name__ == "__main__":
    main()
