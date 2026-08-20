"""Read-only protected-path snapshots and comparisons."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Iterable


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def snapshot_protected_paths(paths: Iterable[os.PathLike[str] | str]) -> dict[str, Any]:
    roots = [Path(value).expanduser().resolve(strict=False) for value in paths]
    items: list[dict[str, Any]] = []
    for root_index, root in enumerate(roots):
        if not root.exists() and not root.is_symlink():
            items.append({"root_index": root_index, "relative": ".", "kind": "missing"})
            continue
        if root.is_symlink():
            stat = root.lstat()
            items.append(
                {
                    "root_index": root_index,
                    "relative": ".",
                    "kind": "symlink",
                    "target": os.readlink(root),
                    "mtime_ns": stat.st_mtime_ns,
                }
            )
            continue
        if root.is_file():
            stat = root.stat()
            items.append(
                {
                    "root_index": root_index,
                    "relative": ".",
                    "kind": "file",
                    "size": stat.st_size,
                    "sha256": _sha256(root),
                }
            )
            continue

        items.append({"root_index": root_index, "relative": ".", "kind": "directory"})
        for current, directory_names, file_names in os.walk(root, followlinks=False):
            directory_names.sort()
            file_names.sort()
            current_path = Path(current)
            for directory_name in list(directory_names):
                child = current_path / directory_name
                if child.is_symlink():
                    directory_names.remove(directory_name)
                    stat = child.lstat()
                    items.append(
                        {
                            "root_index": root_index,
                            "relative": child.relative_to(root).as_posix(),
                            "kind": "symlink",
                            "target": os.readlink(child),
                            "mtime_ns": stat.st_mtime_ns,
                        }
                    )
            for file_name in file_names:
                child = current_path / file_name
                relative = child.relative_to(root).as_posix()
                if child.is_symlink():
                    stat = child.lstat()
                    items.append(
                        {
                            "root_index": root_index,
                            "relative": relative,
                            "kind": "symlink",
                            "target": os.readlink(child),
                            "mtime_ns": stat.st_mtime_ns,
                        }
                    )
                else:
                    stat = child.stat()
                    items.append(
                        {
                            "root_index": root_index,
                            "relative": relative,
                            "kind": "file",
                            "size": stat.st_size,
                            "sha256": _sha256(child),
                        }
                    )
    items.sort(key=lambda item: (item["root_index"], item["relative"], item["kind"]))
    return {
        "schema": "isolated-eval-protected-manifest/v1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "roots": [str(root) for root in roots],
        "items": items,
    }


def compare_manifests(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    def keyed(manifest: dict[str, Any]) -> dict[tuple[int, str], dict[str, Any]]:
        return {
            (int(item["root_index"]), str(item["relative"])): item
            for item in manifest.get("items", [])
        }

    before_items = keyed(before)
    after_items = keyed(after)
    changes: list[dict[str, Any]] = []
    for key in sorted(set(before_items) | set(after_items)):
        left = before_items.get(key)
        right = after_items.get(key)
        if left != right:
            changes.append(
                {
                    "root_index": key[0],
                    "relative": key[1],
                    "before": left,
                    "after": right,
                }
            )
    same_roots = before.get("roots", []) == after.get("roots", [])
    return {
        "schema": "isolated-eval-protected-comparison/v1",
        "unchanged": same_roots and not changes,
        "same_roots": same_roots,
        "change_count": len(changes),
        "changes": changes,
    }
