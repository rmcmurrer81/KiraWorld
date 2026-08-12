#!/usr/bin/env python3
"""Read-only verifier for a Kira Labs Video Studio v2 staging backup.

The verifier inventories two directory trees without modifying either tree.
It excludes Python bytecode caches, compares every authored file by relative
path, size, and SHA-256, and (on Windows) also audits named NTFS alternate data
streams.  The only proof file it writes is the path supplied with ``--output``.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


CHUNK_SIZE = 1024 * 1024
EXCLUDED_DIRECTORY_NAMES = {"__pycache__"}
EXCLUDED_FILE_SUFFIXES = {".pyc"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_relative_path(root: Path, path: Path) -> str:
    relative = os.path.relpath(path, root)
    return unicodedata.normalize("NFC", relative.replace(os.sep, "/"))


def _path_sort_key(value: str) -> tuple[str, str]:
    return (value.casefold(), value)


def _sha256_stream(stream: Any) -> tuple[str, int]:
    digest = hashlib.sha256()
    byte_count = 0
    while True:
        chunk = stream.read(CHUNK_SIZE)
        if not chunk:
            break
        digest.update(chunk)
        byte_count += len(chunk)
    return digest.hexdigest(), byte_count


def _sha256_file(path: Path) -> tuple[str, int]:
    with path.open("rb") as stream:
        return _sha256_stream(stream)


def _canonical_tree_hash(entries: Iterable[dict[str, Any]]) -> str:
    """Hash canonical ``relative-path NUL size NUL sha256 LF`` records."""
    digest = hashlib.sha256()
    ordered = sorted(entries, key=lambda item: _path_sort_key(item["relative_path"]))
    for entry in ordered:
        record = (
            entry["relative_path"].encode("utf-8")
            + b"\0"
            + str(entry["size_bytes"]).encode("ascii")
            + b"\0"
            + entry["sha256"].encode("ascii")
            + b"\n"
        )
        digest.update(record)
    return digest.hexdigest()


def _inventory_tree(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    entries: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    def record_walk_error(error: OSError) -> None:
        errors.append(
            {
                "relative_path": _canonical_relative_path(
                    root, Path(error.filename) if error.filename else root
                ),
                "error": f"{type(error).__name__}: {error}",
            }
        )

    for directory, directory_names, file_names in os.walk(
        root, topdown=True, followlinks=False, onerror=record_walk_error
    ):
        directory_names[:] = sorted(
            (
                name
                for name in directory_names
                if name.casefold() not in EXCLUDED_DIRECTORY_NAMES
            ),
            key=_path_sort_key,
        )
        directory_path = Path(directory)
        for file_name in sorted(file_names, key=_path_sort_key):
            if any(file_name.casefold().endswith(suffix) for suffix in EXCLUDED_FILE_SUFFIXES):
                continue
            path = directory_path / file_name
            relative_path = _canonical_relative_path(root, path)
            try:
                if path.is_symlink():
                    raise OSError("symbolic-link files are not accepted as authored backup payload")
                before = path.stat()
                sha256, bytes_read = _sha256_file(path)
                after = path.stat()
                if bytes_read != before.st_size:
                    raise OSError(
                        f"read {bytes_read} bytes but the initial file size was {before.st_size}"
                    )
                if (
                    before.st_size != after.st_size
                    or before.st_mtime_ns != after.st_mtime_ns
                ):
                    raise OSError("file changed while it was being inventoried")
                entries.append(
                    {
                        "relative_path": relative_path,
                        "size_bytes": before.st_size,
                        "sha256": sha256,
                    }
                )
            except (OSError, PermissionError) as error:
                errors.append(
                    {
                        "relative_path": relative_path,
                        "error": f"{type(error).__name__}: {error}",
                    }
                )

    entries.sort(key=lambda item: _path_sort_key(item["relative_path"]))
    errors.sort(key=lambda item: _path_sort_key(item["relative_path"]))
    return entries, errors


def _compare_entries(
    source_entries: list[dict[str, Any]],
    backup_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    source_by_path = {entry["relative_path"]: entry for entry in source_entries}
    backup_by_path = {entry["relative_path"]: entry for entry in backup_entries}
    source_paths = set(source_by_path)
    backup_paths = set(backup_by_path)

    missing = sorted(source_paths - backup_paths, key=_path_sort_key)
    extra = sorted(backup_paths - source_paths, key=_path_sort_key)
    mismatched: list[dict[str, Any]] = []
    for relative_path in sorted(source_paths & backup_paths, key=_path_sort_key):
        source = source_by_path[relative_path]
        backup = backup_by_path[relative_path]
        if (
            source["size_bytes"] != backup["size_bytes"]
            or source["sha256"] != backup["sha256"]
        ):
            mismatched.append(
                {
                    "relative_path": relative_path,
                    "source_size_bytes": source["size_bytes"],
                    "backup_size_bytes": backup["size_bytes"],
                    "source_sha256": source["sha256"],
                    "backup_sha256": backup["sha256"],
                }
            )

    return {
        "missing_in_backup": missing,
        "extra_in_backup": extra,
        "mismatched_files": mismatched,
        "missing_count": len(missing),
        "extra_count": len(extra),
        "mismatched_count": len(mismatched),
    }


def _enumerate_windows_named_streams(path: Path) -> list[tuple[str, int]]:
    """Return ``(stream_name, size)`` for named streams, excluding ``::$DATA``."""

    from ctypes import wintypes

    class WIN32_FIND_STREAM_DATA(ctypes.Structure):
        _fields_ = [
            ("StreamSize", ctypes.c_longlong),
            ("cStreamName", wintypes.WCHAR * 296),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    find_first = kernel32.FindFirstStreamW
    find_first.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(WIN32_FIND_STREAM_DATA),
        wintypes.DWORD,
    ]
    find_first.restype = wintypes.HANDLE
    find_next = kernel32.FindNextStreamW
    find_next.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(WIN32_FIND_STREAM_DATA),
    ]
    find_next.restype = wintypes.BOOL
    find_close = kernel32.FindClose
    find_close.argtypes = [wintypes.HANDLE]
    find_close.restype = wintypes.BOOL

    data = WIN32_FIND_STREAM_DATA()
    handle = find_first(str(path), 0, ctypes.byref(data), 0)
    invalid_handle = ctypes.c_void_p(-1).value
    if handle == invalid_handle:
        error_code = ctypes.get_last_error()
        raise ctypes.WinError(error_code)

    streams: list[tuple[str, int]] = []
    try:
        while True:
            stream_name = unicodedata.normalize("NFC", data.cStreamName)
            if stream_name and stream_name != "::$DATA":
                streams.append((stream_name, int(data.StreamSize)))
            if not find_next(handle, ctypes.byref(data)):
                error_code = ctypes.get_last_error()
                if error_code == 38:  # ERROR_HANDLE_EOF
                    break
                raise ctypes.WinError(error_code)
    finally:
        find_close(handle)
    streams.sort(key=lambda item: _path_sort_key(item[0]))
    return streams


def _hash_windows_named_stream(path: Path, stream_name: str) -> tuple[str, int]:
    suffix = stream_name
    if suffix.endswith(":$DATA"):
        suffix = suffix[: -len(":$DATA")]
    with open(str(path) + suffix, "rb") as stream:
        return _sha256_stream(stream)


def _inventory_named_streams(
    root: Path, file_entries: list[dict[str, Any]]
) -> dict[str, Any]:
    if os.name != "nt":
        return {
            "attempted": False,
            "supported": False,
            "reason": "Named alternate data stream enumeration is only available on Windows.",
            "authored_files_examined": 0,
            "stream_count": 0,
            "total_stream_bytes": 0,
            "stream_tree_sha256": None,
            "streams": [],
            "errors": [],
        }

    streams: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for file_entry in file_entries:
        relative_path = file_entry["relative_path"]
        path = root.joinpath(*relative_path.split("/"))
        try:
            for stream_name, enumerated_size in _enumerate_windows_named_streams(path):
                sha256, bytes_read = _hash_windows_named_stream(path, stream_name)
                if bytes_read != enumerated_size:
                    raise OSError(
                        f"{stream_name} read {bytes_read} bytes but enumeration reported "
                        f"{enumerated_size}"
                    )
                streams.append(
                    {
                        "relative_path": relative_path,
                        "stream_name": stream_name,
                        "size_bytes": enumerated_size,
                        "sha256": sha256,
                    }
                )
        except (OSError, PermissionError) as error:
            errors.append(
                {
                    "relative_path": relative_path,
                    "error": f"{type(error).__name__}: {error}",
                }
            )

    streams.sort(
        key=lambda item: (
            *_path_sort_key(item["relative_path"]),
            *_path_sort_key(item["stream_name"]),
        )
    )
    errors.sort(key=lambda item: _path_sort_key(item["relative_path"]))
    hash_entries = [
        {
            "relative_path": f'{entry["relative_path"]}{entry["stream_name"]}',
            "size_bytes": entry["size_bytes"],
            "sha256": entry["sha256"],
        }
        for entry in streams
    ]
    return {
        "attempted": True,
        "supported": True,
        "reason": None,
        "authored_files_examined": len(file_entries),
        "stream_count": len(streams),
        "total_stream_bytes": sum(entry["size_bytes"] for entry in streams),
        "stream_tree_sha256": _canonical_tree_hash(hash_entries),
        "streams": streams,
        "errors": errors,
    }


def _compare_named_streams(
    source_audit: dict[str, Any], backup_audit: dict[str, Any]
) -> dict[str, Any]:
    if not source_audit["attempted"] or not backup_audit["attempted"]:
        return {
            "applicable": False,
            "passed": None,
            "missing_in_backup": [],
            "extra_in_backup": [],
            "mismatched_streams": [],
            "missing_count": 0,
            "extra_count": 0,
            "mismatched_count": 0,
        }

    def key(entry: dict[str, Any]) -> tuple[str, str]:
        return (entry["relative_path"], entry["stream_name"])

    source = {key(entry): entry for entry in source_audit["streams"]}
    backup = {key(entry): entry for entry in backup_audit["streams"]}
    source_keys = set(source)
    backup_keys = set(backup)
    missing_keys = sorted(
        source_keys - backup_keys,
        key=lambda item: (*_path_sort_key(item[0]), *_path_sort_key(item[1])),
    )
    extra_keys = sorted(
        backup_keys - source_keys,
        key=lambda item: (*_path_sort_key(item[0]), *_path_sort_key(item[1])),
    )
    missing = [
        {"relative_path": relative_path, "stream_name": stream_name}
        for relative_path, stream_name in missing_keys
    ]
    extra = [
        {"relative_path": relative_path, "stream_name": stream_name}
        for relative_path, stream_name in extra_keys
    ]
    mismatched: list[dict[str, Any]] = []
    for stream_key in sorted(
        source_keys & backup_keys,
        key=lambda item: (*_path_sort_key(item[0]), *_path_sort_key(item[1])),
    ):
        source_entry = source[stream_key]
        backup_entry = backup[stream_key]
        if (
            source_entry["size_bytes"] != backup_entry["size_bytes"]
            or source_entry["sha256"] != backup_entry["sha256"]
        ):
            mismatched.append(
                {
                    "relative_path": stream_key[0],
                    "stream_name": stream_key[1],
                    "source_size_bytes": source_entry["size_bytes"],
                    "backup_size_bytes": backup_entry["size_bytes"],
                    "source_sha256": source_entry["sha256"],
                    "backup_sha256": backup_entry["sha256"],
                }
            )

    passed = (
        not missing
        and not extra
        and not mismatched
        and not source_audit["errors"]
        and not backup_audit["errors"]
    )
    return {
        "applicable": True,
        "passed": passed,
        "missing_in_backup": missing,
        "extra_in_backup": extra,
        "mismatched_streams": mismatched,
        "missing_count": len(missing),
        "extra_count": len(extra),
        "mismatched_count": len(mismatched),
    }


def _is_within(candidate: Path, parent: Path) -> bool:
    candidate_text = os.path.normcase(str(candidate))
    parent_text = os.path.normcase(str(parent))
    try:
        return os.path.commonpath([candidate_text, parent_text]) == parent_text
    except ValueError:
        return False


def _validate_paths(source: Path, backup: Path, output: Path) -> None:
    if not source.is_dir():
        raise ValueError(f"source is not an existing directory: {source}")
    if not backup.is_dir():
        raise ValueError(f"backup is not an existing directory: {backup}")
    if source == backup:
        raise ValueError("source and backup must be different directories")
    if _is_within(source, backup) or _is_within(backup, source):
        raise ValueError("source and backup directory trees must not overlap")
    if _is_within(output, source) or _is_within(output, backup):
        raise ValueError("output must be outside both the source and backup trees")
    if output.exists() and output.is_dir():
        raise ValueError(f"output names a directory, not a JSON file: {output}")


def _tree_summary(
    root: Path, entries: list[dict[str, Any]], errors: list[dict[str, str]]
) -> dict[str, Any]:
    return {
        "root": str(root),
        "file_count": len(entries),
        "total_bytes": sum(entry["size_bytes"] for entry in entries),
        "tree_sha256": _canonical_tree_hash(entries),
        "inventory": entries,
        "inventory_errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare a Kira Labs Video Studio v2 staging tree with its backup "
            "without modifying either tree."
        )
    )
    parser.add_argument("--source", required=True, help="Source staging directory.")
    parser.add_argument("--backup", required=True, help="Backup directory to verify.")
    parser.add_argument(
        "--output",
        required=True,
        help="JSON proof path outside both source and backup trees.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    source = Path(arguments.source).expanduser().resolve(strict=False)
    backup = Path(arguments.backup).expanduser().resolve(strict=False)
    output = Path(arguments.output).expanduser().resolve(strict=False)

    try:
        _validate_paths(source, backup, output)
    except ValueError as error:
        parser.error(str(error))

    source_entries, source_errors = _inventory_tree(source)
    backup_entries, backup_errors = _inventory_tree(backup)
    source_summary = _tree_summary(source, source_entries, source_errors)
    backup_summary = _tree_summary(backup, backup_entries, backup_errors)
    file_comparison = _compare_entries(source_entries, backup_entries)

    source_streams = _inventory_named_streams(source, source_entries)
    backup_streams = _inventory_named_streams(backup, backup_entries)
    stream_comparison = _compare_named_streams(source_streams, backup_streams)

    files_match = (
        source_summary["tree_sha256"] == backup_summary["tree_sha256"]
        and source_summary["file_count"] == backup_summary["file_count"]
        and source_summary["total_bytes"] == backup_summary["total_bytes"]
        and not source_errors
        and not backup_errors
        and file_comparison["missing_count"] == 0
        and file_comparison["extra_count"] == 0
        and file_comparison["mismatched_count"] == 0
    )
    streams_match = (
        stream_comparison["passed"]
        if stream_comparison["applicable"]
        else True
    )
    passed = files_match and bool(streams_match)

    proof = {
        "schema_version": 1,
        "proof_kind": "kira_labs_video_studio_v2_staging_backup_verification",
        "generated_at_utc": _utc_now(),
        "read_only_source_and_backup": True,
        "passed": passed,
        "canonical_tree_hash_record_format": (
            "UTF-8 NFC relative POSIX path + NUL + ASCII byte size + NUL + "
            "lowercase ASCII SHA-256 + LF; records sorted by casefolded path, "
            "then exact path"
        ),
        "exclusions": {
            "directory_names_case_insensitive": sorted(EXCLUDED_DIRECTORY_NAMES),
            "file_suffixes_case_insensitive": sorted(EXCLUDED_FILE_SUFFIXES),
        },
        "source": source_summary,
        "backup": backup_summary,
        "file_comparison": {
            **file_comparison,
            "passed": files_match,
        },
        "alternate_data_stream_audit": {
            "source": source_streams,
            "backup": backup_streams,
            "comparison": stream_comparison,
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(proof, stream, indent=2, ensure_ascii=False, sort_keys=True)
        stream.write("\n")

    print(
        f'{"PASSED" if passed else "FAILED"}: backup verification proof written to {output}'
    )
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
