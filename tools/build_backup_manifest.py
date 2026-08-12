"""
Build a backup manifest for Kira 2.0 without copying files.

The manifest helps prepare a clean migration package for the new desktop by
listing included files and excluded paths.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "_tmp_docs_text",
    "_tmp_identity_text",
}
DEFAULT_EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp", ".log"}


def should_exclude(path: Path, root: Path) -> tuple[bool, str]:
    relative_parts = path.relative_to(root).parts
    for part in relative_parts:
        if part in DEFAULT_EXCLUDED_DIRS:
            return True, f"excluded_dir:{part}"
    if path.suffix.lower() in DEFAULT_EXCLUDED_SUFFIXES:
        return True, f"excluded_suffix:{path.suffix.lower()}"
    return False, ""


def build_manifest(root: Path) -> dict:
    included: list[dict] = []
    excluded: list[dict] = []
    total_bytes = 0

    for path in sorted(root.rglob("*")):
        if path == root:
            continue
        excluded_path, reason = should_exclude(path, root)
        relative = str(path.relative_to(root)).replace("\\", "/")
        if excluded_path:
            excluded.append({"path": relative, "reason": reason})
            continue
        if path.is_file():
            size = path.stat().st_size
            total_bytes += size
            included.append({"path": relative, "size_bytes": size})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root),
        "included_file_count": len(included),
        "included_total_bytes": total_bytes,
        "excluded_count": len(excluded),
        "excluded_rules": {
            "dirs": sorted(DEFAULT_EXCLUDED_DIRS),
            "suffixes": sorted(DEFAULT_EXCLUDED_SUFFIXES),
        },
        "included_files": included,
        "excluded_paths": excluded,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Kira backup manifest.")
    parser.add_argument("--root", default=".", help="Project root to scan.")
    parser.add_argument("--output", default="exports/backup_manifest.json", help="Manifest output path.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(root)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote backup manifest: {output}")
    print(f"Included files: {manifest['included_file_count']}")
    print(f"Excluded paths: {manifest['excluded_count']}")


if __name__ == "__main__":
    main()
