"""Canonical protected-tree inventory for the R24 local-transition lane.

This is the single implementation used by Python static verification, the
PowerShell one-shot wrapper, and the Blender-side read-only worker.  It never
writes into an inventoried tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Iterable


sys.dont_write_bytecode = True


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _contained_path(project_root: Path, relative_root: str) -> Path:
    project = project_root.resolve()
    candidate = (project / relative_root).resolve()
    try:
        candidate.relative_to(project)
    except ValueError as exc:
        raise ValueError(f"inventory root escapes project: {relative_root}") from exc
    if not candidate.is_dir():
        raise FileNotFoundError(f"inventory root is absent: {relative_root}")
    return candidate


def canonical_inventory_rows(
    project_root: Path, relative_root: str
) -> list[dict[str, object]]:
    project = project_root.resolve()
    root = _contained_path(project, relative_root)
    files: Iterable[Path] = (path for path in root.rglob("*") if path.is_file())
    ordered = sorted(files, key=lambda path: path.relative_to(project).as_posix())
    return [
        {
            "path": path.relative_to(project).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in ordered
    ]


def canonical_inventory(project_root: Path, relative_root: str) -> dict[str, object]:
    rows = canonical_inventory_rows(project_root, relative_root)
    return {
        "root": relative_root.replace("\\", "/"),
        "file_count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "compact_inventory_sha256": hashlib.sha256(canonical_json(rows)).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--root", required=True)
    arguments = parser.parse_args()
    sys.stdout.buffer.write(canonical_json(canonical_inventory(arguments.project, arguments.root)))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
