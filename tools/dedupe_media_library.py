"""
Find or remove exact duplicate files under Data/library.

Only byte-for-byte duplicates are considered duplicates. The tool writes a
reviewable plan first and never deletes non-identical files just because names
look similar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY_ROOT = PROJECT_ROOT / "Data" / "library"
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "indexes" / "media_library_duplicate_plan.json"
DEFAULT_DUPLICATE_TRASH = PROJECT_ROOT / "Data" / "library_duplicates_removed"


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _canonical_candidate(paths: list[Path]) -> Path:
    def score(path: Path) -> tuple[int, int, str]:
        duplicate_penalty = 1 if "duplicate" in path.stem.lower() else 0
        return (duplicate_penalty, len(path.name), path.as_posix())

    return sorted(paths, key=score)[0]


def _unique_trash_path(trash_root: Path, duplicate: Path, base_root: Path = PROJECT_ROOT) -> Path:
    try:
        relative = duplicate.relative_to(base_root)
    except ValueError:
        relative = Path(duplicate.drive.replace(":", "")) / Path(*duplicate.parts[1:])
    target = trash_root / relative
    if not target.exists():
        return target
    counter = 2
    while True:
        candidate = target.with_name(f"{target.stem}_removed_{counter}{target.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def build_duplicate_plan(library_root: Path = DEFAULT_LIBRARY_ROOT) -> dict[str, Any]:
    by_hash: dict[str, list[Path]] = {}
    for path in sorted(library_root.rglob("*")):
        if not path.is_file():
            continue
        digest = sha256_file(path)
        by_hash.setdefault(digest, []).append(path)

    groups = []
    operations = []
    for digest, paths in sorted(by_hash.items()):
        if len(paths) < 2:
            continue
        keep = _canonical_candidate(paths)
        duplicates = [path for path in paths if path != keep]
        groups.append(
            {
                "sha256": digest,
                "keep": _relative(keep),
                "duplicates": [_relative(path) for path in duplicates],
                "file_count": len(paths),
                "total_duplicate_bytes": sum(path.stat().st_size for path in duplicates),
            }
        )
        for duplicate in duplicates:
            operations.append(
                {
                    "source": _relative(duplicate),
                    "keep": _relative(keep),
                    "sha256": digest,
                    "size_bytes": duplicate.stat().st_size,
                    "blocked": False,
                    "issues": [],
                }
            )
    return {
        "plan_id": "media_library_duplicate_plan_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "library_root": _relative(library_root),
        "duplicate_group_count": len(groups),
        "operation_count": len(operations),
        "total_duplicate_bytes": sum(operation["size_bytes"] for operation in operations),
        "rules": {
            "exact_sha256_only": True,
            "keeps_non_duplicate_named_variants": True,
            "moves_to_duplicate_trash_by_default": True,
            "does_not_permanently_delete": True,
        },
        "groups": groups,
        "operations": operations,
    }


def _project_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def apply_duplicate_plan(plan: dict[str, Any], trash_root: Path = DEFAULT_DUPLICATE_TRASH) -> dict[str, Any]:
    moved = []
    skipped = []
    library_root = _project_path(str(plan.get("library_root", DEFAULT_LIBRARY_ROOT)))
    for operation in plan.get("operations", []):
        if operation.get("blocked"):
            skipped.append(operation)
            continue
        source = _project_path(str(operation["source"]))
        keep = _project_path(str(operation["keep"]))
        if not source.exists():
            skipped.append({**operation, "issues": [*operation.get("issues", []), "source_missing"]})
            continue
        if not keep.exists():
            skipped.append({**operation, "issues": [*operation.get("issues", []), "keep_missing"]})
            continue
        try:
            source.relative_to(library_root)
        except ValueError:
            skipped.append({**operation, "issues": [*operation.get("issues", []), "outside_library_root"]})
            continue
        if sha256_file(source) != str(operation["sha256"]) or sha256_file(keep) != str(operation["sha256"]):
            skipped.append({**operation, "issues": [*operation.get("issues", []), "hash_changed"]})
            continue
        target = _unique_trash_path(trash_root, source, library_root.parent.parent)
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        moved.append({"source": operation["source"], "target": _relative(target), "keep": operation["keep"]})
    return {"moved_count": len(moved), "skipped_count": len(skipped), "moved": moved, "skipped": skipped}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan/apply exact duplicate cleanup for Data/library.")
    parser.add_argument("--library-root", default=str(DEFAULT_LIBRARY_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--trash-root", default=str(DEFAULT_DUPLICATE_TRASH))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    library_root = Path(args.library_root)
    if not library_root.is_absolute():
        library_root = PROJECT_ROOT / library_root
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    trash_root = Path(args.trash_root)
    if not trash_root.is_absolute():
        trash_root = PROJECT_ROOT / trash_root

    plan = build_duplicate_plan(library_root)
    if args.apply:
        plan["last_run"] = {"apply_requested": True, "apply_result": apply_duplicate_plan(plan, trash_root)}
        plan = build_duplicate_plan(library_root) | {"last_run": plan["last_run"]}
    else:
        plan["last_run"] = {"apply_requested": False, "apply_result": None}
    write_json(output, plan)
    print(f"Duplicate groups: {plan['duplicate_group_count']}")
    print(f"Duplicate operations: {plan['operation_count']}")
    print(f"Duplicate bytes: {plan['total_duplicate_bytes']}")
    if args.apply:
        result = plan["last_run"]["apply_result"]
        print(f"Moved {result['moved_count']} duplicates; skipped {result['skipped_count']}.")
    print(f"Wrote {_relative(output)}")


if __name__ == "__main__":
    main()
