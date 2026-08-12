"""
Audit Data/library media filenames for future-friendly organization.

This tool only reports suggestions. It never renames or moves files.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY_ROOT = PROJECT_ROOT / "Data" / "library"
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "indexes" / "media_library_name_audit.json"

NON_ASCII_RE = re.compile(r"[^\x00-\x7F]")
MULTISPACE_RE = re.compile(r"\s{2,}")
SUSPECT_TERMS = ("youtube", "full movie", "full episode", "watch party")
TYPO_TERMS = ("epidode",)


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def audit_file(path: Path) -> dict[str, Any]:
    return audit_path(path, item_type="file")


def audit_directory(path: Path) -> dict[str, Any]:
    return audit_path(path, item_type="directory")


def audit_path(path: Path, item_type: str) -> dict[str, Any]:
    name = path.name
    issues: list[str] = []
    if NON_ASCII_RE.search(name):
        issues.append("non_ascii_or_emoji")
    if MULTISPACE_RE.search(name):
        issues.append("multiple_spaces")
    if item_type == "directory" and " " in name:
        issues.append("multiple_words_without_underscores")
    lower = name.lower()
    for term in SUSPECT_TERMS:
        if term in lower:
            issues.append(f"download_label:{term}")
    for term in TYPO_TERMS:
        if term in lower:
            issues.append(f"possible_typo:{term}")
    if name != name.strip():
        issues.append("leading_or_trailing_space")

    return {
        "path": _relative(path),
        "name": name,
        "item_type": item_type,
        "issues": issues,
        "recommendation": (
            "Consider a clean ASCII name with underscores for folders, series/movie title, "
            "season/episode or year, and no download-site labels."
            if issues
            else "OK"
        ),
    }


def build_audit(library_root: Path = DEFAULT_LIBRARY_ROOT) -> dict[str, Any]:
    entries = [audit_file(path) for path in sorted(library_root.rglob("*")) if path.is_file()]
    directory_entries = [
        audit_directory(path)
        for path in sorted(library_root.rglob("*"))
        if path.is_dir()
    ]
    flagged = [entry for entry in entries if entry["issues"]]
    flagged_directories = [entry for entry in directory_entries if entry["issues"]]
    return {
        "audit_id": "media_library_name_audit_v1",
        "library_root": _relative(library_root),
        "file_count": len(entries),
        "directory_count": len(directory_entries),
        "flagged_count": len(flagged),
        "flagged_directory_count": len(flagged_directories),
        "rules": {
            "prefer_ascii": True,
            "avoid_multiple_spaces": True,
            "avoid_download_site_labels": True,
            "audit_directories": True,
            "do_not_rename_automatically": True,
        },
        "flagged": flagged,
        "flagged_directories": flagged_directories,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit media library filenames without renaming files.")
    parser.add_argument("--library-root", default=str(DEFAULT_LIBRARY_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    library_root = Path(args.library_root)
    if not library_root.is_absolute():
        library_root = PROJECT_ROOT / library_root
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output

    audit = build_audit(library_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Flagged {audit['flagged_count']} of {audit['file_count']} media/library files.")
    print(f"Flagged {audit['flagged_directory_count']} of {audit['directory_count']} media/library folders.")
    print(f"Wrote {_relative(output)}")


if __name__ == "__main__":
    main()
