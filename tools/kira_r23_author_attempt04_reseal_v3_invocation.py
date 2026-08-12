#!/usr/bin/env python3
"""Execution-disabled controller for R23 Attempt04 reseal v3.

The default operation is a read-only verification.  A future execution needs
an exact append-only owner authorization package and the explicit execution
flag.  The live path is Windows-only and keeps no-follow, deny-write/delete
handles open for every executable input from before hashing until the exact
Blender child exits.

This file does not authorize a Blender run, body mutation, render, export,
activation, or runtime assignment.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import time
import traceback
import unicodedata
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
PREPARATION_DIRECTORY = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_reseal_v3_preparation"
)
CONFIG_PATH = PREPARATION_DIRECTORY / (
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT04_RESEAL_V3_CONFIG.json"
)
MANIFEST_PATH = PREPARATION_DIRECTORY / "PACKAGE_MANIFEST.json"


class ResealV3Error(RuntimeError):
    """Fail-closed v3 controller error."""


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ResealV3Error(f"JSON root must be an object: {path}")
    return value


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def evidence_path(path: Path) -> str:
    try:
        return relative(path)
    except ValueError:
        return Path(os.path.abspath(path)).as_posix()


def _lexical_parts(raw: str | Path) -> tuple[str, ...]:
    text = str(raw).replace("\\", "/")
    value = PurePosixPath(text)
    if value.is_absolute() or not value.parts:
        raise ResealV3Error(f"project path must be relative: {raw}")
    if any(part in {"", ".", ".."} for part in value.parts):
        raise ResealV3Error(f"project path has unsafe component: {raw}")
    return value.parts


def _is_reparse(path: Path) -> bool:
    try:
        return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except AttributeError:
        return path.is_symlink()


def lexical_project_path(
    raw: str | Path,
    *,
    require_exists: bool = True,
    require_leaf_regular: bool = False,
) -> Path:
    parts = _lexical_parts(raw)
    cursor = ROOT
    if _is_reparse(cursor):
        raise ResealV3Error("project root may not be a reparse point")
    for index, part in enumerate(parts):
        cursor = cursor / part
        exists = os.path.lexists(cursor)
        if exists and _is_reparse(cursor):
            raise ResealV3Error(f"reparse component rejected: {cursor}")
        if not exists and (require_exists or index < len(parts) - 1):
            raise ResealV3Error(f"missing project path component: {cursor}")
    if require_exists and not cursor.exists():
        raise ResealV3Error(f"missing project path: {cursor}")
    if require_leaf_regular and not cursor.is_file():
        raise ResealV3Error(f"expected regular file: {cursor}")
    try:
        cursor.resolve(strict=require_exists).relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ResealV3Error(f"path escapes project root: {raw}") from exc
    return cursor


def lexical_future_project_path(raw: str | Path) -> Path:
    """Validate a project path while allowing a not-yet-created suffix."""

    parts = _lexical_parts(raw)
    cursor = ROOT
    missing_seen = False
    for part in parts:
        cursor = cursor / part
        if missing_seen:
            continue
        if os.path.lexists(cursor):
            if _is_reparse(cursor):
                raise ResealV3Error(f"reparse component rejected: {cursor}")
        else:
            missing_seen = True
    existing = cursor
    while not os.path.lexists(existing):
        existing = existing.parent
    try:
        existing.resolve(strict=True).relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ResealV3Error(f"future path escapes project root: {raw}") from exc
    return cursor


def safe_mkdir_parents(path: Path) -> None:
    """Create only absent project directories and reject reparse components."""

    path.relative_to(ROOT)
    cursor = ROOT
    for part in path.relative_to(ROOT).parts:
        cursor = cursor / part
        if os.path.lexists(cursor):
            if _is_reparse(cursor) or not cursor.is_dir():
                raise ResealV3Error(f"unsafe directory component: {cursor}")
            continue
        cursor.mkdir(exist_ok=False)
        if _is_reparse(cursor) or not cursor.is_dir():
            raise ResealV3Error(f"created directory is unsafe: {cursor}")


_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "CLOCK$",
    "CONIN$",
    "CONOUT$",
    *(f"COM{i}" for i in range(0, 10)),
    *(f"LPT{i}" for i in range(0, 10)),
}
_WINDOWS_FORBIDDEN = set('<>:"/\\|?*')


def validate_windows_basename(value: str, label: str = "basename") -> str:
    """Validate one exact NTFS-safe leaf; aliases and ADS are rejected."""

    if not isinstance(value, str) or not value:
        raise ResealV3Error(f"{label} must be a nonempty string")
    if unicodedata.normalize("NFC", value) != value:
        raise ResealV3Error(f"{label} must already be NFC-normalized")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value):
        raise ResealV3Error(f"{label} is outside the sealed ASCII leaf allowlist")
    if value in {".", ".."} or value.endswith((" ", ".")):
        raise ResealV3Error(f"{label} has a Windows alias or trailing dot/space")
    if any(ord(char) < 32 or char in _WINDOWS_FORBIDDEN for char in value):
        raise ResealV3Error(f"{label} contains a forbidden Windows character")
    device_stem = value.split(".", 1)[0].upper()
    if device_stem in _WINDOWS_RESERVED:
        raise ResealV3Error(f"{label} is a reserved Windows device name")
    if Path(value).name != value:
        raise ResealV3Error(f"{label} must be one leaf name")
    return value


def verify_binding(binding: Mapping[str, Any], label: str) -> dict[str, Any]:
    expected_fields = {"path", "bytes", "sha256"}
    if set(binding) != expected_fields:
        raise ResealV3Error(f"binding fields drifted for {label}")
    path = lexical_project_path(
        str(binding["path"]), require_exists=True, require_leaf_regular=True
    )
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(binding["bytes"]) or digest != str(binding["sha256"]):
        raise ResealV3Error(
            f"binding drifted for {label}: bytes={size}, sha256={digest}"
        )
    return {"path": relative(path), "bytes": size, "sha256": digest}


def verify_exact_directory(section: Mapping[str, Any]) -> dict[str, Any]:
    directory = lexical_project_path(str(section["directory"]), require_exists=True)
    if not directory.is_dir():
        raise ResealV3Error(f"preserved path is not a directory: {directory}")
    expected_files = section["files"]
    if not isinstance(expected_files, dict):
        raise ResealV3Error("preserved file map is invalid")
    actual = sorted(entry.name for entry in directory.iterdir())
    expected = sorted(expected_files)
    if actual != expected:
        raise ResealV3Error(
            f"preserved directory closure drifted for {section['label']}: {actual}"
        )
    verified = {
        name: verify_binding(
            {
                "path": (PurePosixPath(str(section["directory"])) / name).as_posix(),
                "bytes": record["bytes"],
                "sha256": record["sha256"],
            },
            f"{section['label']}/{name}",
        )
        for name, record in expected_files.items()
    }
    return {"directory": relative(directory), "files": verified}


def verify_preparation() -> tuple[dict[str, Any], dict[str, Any]]:
    config = read_json(CONFIG_PATH)
    manifest = read_json(MANIFEST_PATH)
    if config.get("schema") != "kira.avatar.r23_author_attempt04_reseal_v3.v1":
        raise ResealV3Error("wrong reseal v3 config schema")
    if config.get("status") != (
        "PREPARED_NON_EXECUTING_LIVE_AUTHORIZATION_ABSENT_BLENDER_NOT_RUN"
    ):
        raise ResealV3Error("v3 preparation status drifted")
    if manifest.get("artifact_kind") != (
        "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V3_PREPARATION"
    ):
        raise ResealV3Error("wrong v3 preparation manifest kind")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ResealV3Error("v3 manifest artifact list is absent")
    expected = set(config["manifest_contract"]["required_artifact_paths"])
    actual = [str(row.get("path")) for row in artifacts]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ResealV3Error("v3 preparation manifest closure drifted")
    manifest_verified = {
        row["path"]: verify_binding(row, f"manifest/{row['path']}")
        for row in artifacts
    }
    bound = {
        label: verify_binding(binding, label)
        for label, binding in config["bound_artifacts"].items()
    }
    preserved = [
        verify_exact_directory(section)
        for section in config["preserved_append_only_evidence"]
    ]
    verify_author_handoff(config)
    command = build_command(config)
    record = {
        "config": {
            "path": relative(CONFIG_PATH),
            "bytes": CONFIG_PATH.stat().st_size,
            "sha256": sha256_file(CONFIG_PATH),
        },
        "manifest": {
            "path": relative(MANIFEST_PATH),
            "bytes": MANIFEST_PATH.stat().st_size,
            "sha256": sha256_file(MANIFEST_PATH),
        },
        "manifest_artifacts": manifest_verified,
        "bound_artifacts": bound,
        "preserved": preserved,
        "command": command,
        "command_sha256": canonical_sha256(command),
    }
    return config, record


def handoff_contract_record(config: Mapping[str, Any]) -> dict[str, Any]:
    handoff = config["handoff_contract"]
    author = str(handoff["sealed_author_config_argument"])
    overlay = str(handoff["repair_overlay_config_argument"])
    if author == overlay:
        raise ResealV3Error("author config and repair overlay must be distinct")
    expected_tail = ["--config", author, "--execute-authoring"]
    if list(config["command_contract"]["worker_tail"]) != expected_tail:
        raise ResealV3Error("worker tail does not pass the sealed author config")
    return {
        "sealed_author_config": PurePosixPath(author).as_posix(),
        "sealed_author_schema": handoff["sealed_author_schema"],
        "repair_overlay_config": PurePosixPath(overlay).as_posix(),
        "repair_overlay_schema": handoff["repair_overlay_schema"],
        "worker_tail": expected_tail,
        "topology_overlay_assignment_only": True,
    }


def verify_author_handoff(config: Mapping[str, Any]) -> dict[str, Any]:
    record = handoff_contract_record(config)
    author_path = lexical_project_path(
        record["sealed_author_config"], require_exists=True, require_leaf_regular=True
    )
    overlay_path = lexical_project_path(
        record["repair_overlay_config"], require_exists=True, require_leaf_regular=True
    )
    author_json = read_json(author_path)
    overlay_json = read_json(overlay_path)
    if author_json.get("schema") != record["sealed_author_schema"]:
        raise ResealV3Error("sealed author config schema drifted")
    if overlay_json.get("schema") != record["repair_overlay_schema"]:
        raise ResealV3Error("repair overlay config schema drifted")
    return record


def build_command(config: Mapping[str, Any]) -> list[str]:
    artifacts = config["bound_artifacts"]
    source = lexical_project_path(
        artifacts["r19_source_blend"]["path"],
        require_exists=True,
        require_leaf_regular=True,
    )
    wrapper = lexical_project_path(
        artifacts["reseal_v3_blender_wrapper"]["path"],
        require_exists=True,
        require_leaf_regular=True,
    )
    tail = list(config["command_contract"]["worker_tail"])
    command = [
        str(Path(config["blender_identity"]["path"])),
        "--background",
        "--factory-startup",
        "--disable-autoexec",
        str(source),
        "--python-exit-code",
        str(int(config["command_contract"]["python_exit_code"])),
        "--python",
        str(wrapper),
        "--",
        *tail,
    ]
    if command.count("--python") != 1 or command.count("--python-expr") != 0:
        raise ResealV3Error("constructed command has an unexpected execution flag")
    if command.count("--") != 1:
        raise ResealV3Error("constructed command delimiter count is not one")
    if command.index("--python-exit-code") >= command.index("--python"):
        raise ResealV3Error("--python-exit-code must precede --python")
    return command


def validate_complete_child_argv(
    actual: Sequence[str], expected: Sequence[str]
) -> list[str]:
    """Compare the complete argv, not merely values after Blender's ``--``."""

    actual_list = list(actual)
    expected_list = list(expected)
    if actual_list != expected_list:
        raise ResealV3Error(
            "complete Blender argv differs from the authorized command: "
            f"actual_sha256={canonical_sha256(actual_list)}, "
            f"expected_sha256={canonical_sha256(expected_list)}"
        )
    if actual_list.count("--python") != 1 or "--python-expr" in actual_list:
        raise ResealV3Error("actual Blender argv contains an extra execution surface")
    if actual_list.count("--") != 1:
        raise ResealV3Error("actual Blender argv delimiter count is not one")
    return actual_list


# Win32 constants used only by the explicit live path.
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
CREATE_NEW = 1
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_BEGIN = 0
HANDLE_FLAG_INHERIT = 0x00000001
WAIT_OBJECT_0 = 0
DUPLICATE_SAME_ACCESS = 0x00000002
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class _ByHandleInfo(ctypes.Structure):
    _fields_ = [
        ("dwFileAttributes", wintypes.DWORD),
        ("ftCreationTime", wintypes.FILETIME),
        ("ftLastAccessTime", wintypes.FILETIME),
        ("ftLastWriteTime", wintypes.FILETIME),
        ("dwVolumeSerialNumber", wintypes.DWORD),
        ("nFileSizeHigh", wintypes.DWORD),
        ("nFileSizeLow", wintypes.DWORD),
        ("nNumberOfLinks", wintypes.DWORD),
        ("nFileIndexHigh", wintypes.DWORD),
        ("nFileIndexLow", wintypes.DWORD),
    ]


def _kernel32() -> Any:
    if os.name != "nt":
        raise ResealV3Error("locked execution requires Windows")
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    api.CreateFileW.restype = wintypes.HANDLE
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.CloseHandle.restype = wintypes.BOOL
    api.GetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_ByHandleInfo),
    ]
    api.GetFileInformationByHandle.restype = wintypes.BOOL
    api.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    api.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    api.SetFilePointerEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_longlong,
        ctypes.POINTER(ctypes.c_longlong),
        wintypes.DWORD,
    ]
    api.SetFilePointerEx.restype = wintypes.BOOL
    api.ReadFile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    api.ReadFile.restype = wintypes.BOOL
    api.WriteFile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPCVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    api.WriteFile.restype = wintypes.BOOL
    api.FlushFileBuffers.argtypes = [wintypes.HANDLE]
    api.FlushFileBuffers.restype = wintypes.BOOL
    api.SetEndOfFile.argtypes = [wintypes.HANDLE]
    api.SetEndOfFile.restype = wintypes.BOOL
    api.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
    api.SetHandleInformation.restype = wintypes.BOOL
    api.CreateEventW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
    api.CreateEventW.restype = wintypes.HANDLE
    api.CreatePipe.argtypes = [
        ctypes.POINTER(wintypes.HANDLE),
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    api.CreatePipe.restype = wintypes.BOOL
    api.SetEvent.argtypes = [wintypes.HANDLE]
    api.SetEvent.restype = wintypes.BOOL
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.WaitForSingleObject.restype = wintypes.DWORD
    api.GetCurrentProcess.argtypes = []
    api.GetCurrentProcess.restype = wintypes.HANDLE
    api.DuplicateHandle.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    api.DuplicateHandle.restype = wintypes.BOOL
    return api


def _win_error(action: str) -> ResealV3Error:
    return ResealV3Error(f"{action} failed: WinError {ctypes.get_last_error()}")


def _normal_final_path(value: str) -> str:
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return os.path.normcase(os.path.abspath(value))


class Win32LockedHandle:
    """No-follow handle whose share mode denies write and delete until close."""

    def __init__(
        self,
        handle: int,
        expected_path: Path,
        *,
        directory: bool = False,
        share_write: bool = False,
    ):
        self.handle = int(handle)
        self.expected_path = expected_path
        self.directory = directory
        self.share_write = share_write
        self._api = _kernel32()
        self._closed = False
        self.info = self._query_info()
        self.final_path = self._query_final_path()
        expected = _normal_final_path(str(expected_path))
        if _normal_final_path(self.final_path) != expected:
            self.close()
            raise ResealV3Error(
                f"handle final path mismatch: {self.final_path!r} != {expected!r}"
            )
        if self.info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT:
            self.close()
            raise ResealV3Error(f"reparse handle rejected: {expected_path}")

    @classmethod
    def open_existing(
        cls,
        path: Path,
        *,
        directory: bool = False,
        inheritable: bool = False,
        share_write: bool = False,
    ) -> "Win32LockedHandle":
        api = _kernel32()
        flags = FILE_FLAG_OPEN_REPARSE_POINT
        if directory:
            flags |= FILE_FLAG_BACKUP_SEMANTICS
        else:
            flags |= FILE_ATTRIBUTE_NORMAL
        share = FILE_SHARE_READ | (FILE_SHARE_WRITE if share_write else 0)
        handle = api.CreateFileW(
            str(path), GENERIC_READ, share, None, OPEN_EXISTING, flags, None
        )
        if int(handle) == int(INVALID_HANDLE_VALUE):
            raise _win_error(f"lock open {path}")
        result = cls(
            int(handle), path, directory=directory, share_write=share_write
        )
        if inheritable:
            result.set_inheritable(True)
        return result

    @classmethod
    def create_new(cls, path: Path, *, inheritable: bool = False) -> "Win32LockedHandle":
        api = _kernel32()
        handle = api.CreateFileW(
            str(path),
            GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ,
            None,
            CREATE_NEW,
            FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT,
            None,
        )
        if int(handle) == int(INVALID_HANDLE_VALUE):
            raise _win_error(f"exclusive create {path}")
        result = cls(int(handle), path, directory=False)
        if inheritable:
            result.set_inheritable(True)
        return result

    @classmethod
    def from_inherited(cls, handle: int, expected_path: Path) -> "Win32LockedHandle":
        return cls(handle, expected_path, directory=False)

    def _query_info(self) -> _ByHandleInfo:
        info = _ByHandleInfo()
        if not self._api.GetFileInformationByHandle(self.handle, ctypes.byref(info)):
            raise _win_error("GetFileInformationByHandle")
        return info

    def _query_final_path(self) -> str:
        length = self._api.GetFinalPathNameByHandleW(self.handle, None, 0, 0)
        if not length:
            raise _win_error("GetFinalPathNameByHandleW(length)")
        buffer = ctypes.create_unicode_buffer(length + 1)
        result = self._api.GetFinalPathNameByHandleW(
            self.handle, buffer, len(buffer), 0
        )
        if not result or result >= len(buffer):
            raise _win_error("GetFinalPathNameByHandleW(value)")
        return buffer.value

    @property
    def size(self) -> int:
        return (int(self.info.nFileSizeHigh) << 32) | int(self.info.nFileSizeLow)

    @property
    def identity(self) -> dict[str, int]:
        return {
            "volume_serial": int(self.info.dwVolumeSerialNumber),
            "file_index_high": int(self.info.nFileIndexHigh),
            "file_index_low": int(self.info.nFileIndexLow),
            "links": int(self.info.nNumberOfLinks),
        }

    def set_inheritable(self, enabled: bool) -> None:
        value = HANDLE_FLAG_INHERIT if enabled else 0
        if not self._api.SetHandleInformation(
            self.handle, HANDLE_FLAG_INHERIT, value
        ):
            raise _win_error("SetHandleInformation")

    def seek_start(self) -> None:
        new_position = ctypes.c_longlong()
        if not self._api.SetFilePointerEx(
            self.handle, 0, ctypes.byref(new_position), FILE_BEGIN
        ):
            raise _win_error("SetFilePointerEx")

    def read_bytes(self) -> bytes:
        if self.directory:
            raise ResealV3Error("cannot read directory handle as bytes")
        # A duplicate of this handle may have been handed to the child as a
        # stdout/stderr stream.  Refresh BY_HANDLE_FILE_INFORMATION before
        # deciding how many bytes to read; ``self.info`` reflects the size at
        # open time and would otherwise make nonempty child logs look empty.
        self.info = self._query_info()
        self.seek_start()
        chunks: list[bytes] = []
        remaining = self.size
        while remaining:
            amount = min(1024 * 1024, remaining)
            buffer = ctypes.create_string_buffer(amount)
            read = wintypes.DWORD()
            if not self._api.ReadFile(
                self.handle, buffer, amount, ctypes.byref(read), None
            ):
                raise _win_error("ReadFile")
            if read.value == 0:
                raise ResealV3Error("locked file ended before its reported size")
            chunks.append(buffer.raw[: read.value])
            remaining -= int(read.value)
        return b"".join(chunks)

    def write_once(self, value: bytes) -> None:
        if self.size != 0:
            raise ResealV3Error(f"reserved journal leaf is not empty: {self.expected_path}")
        self.seek_start()
        offset = 0
        while offset < len(value):
            block = value[offset : offset + 1024 * 1024]
            written = wintypes.DWORD()
            buffer = ctypes.create_string_buffer(block)
            if not self._api.WriteFile(
                self.handle, buffer, len(block), ctypes.byref(written), None
            ):
                raise _win_error("WriteFile")
            if int(written.value) != len(block):
                raise ResealV3Error("short WriteFile on journal leaf")
            offset += len(block)
        if not self._api.FlushFileBuffers(self.handle):
            raise _win_error("FlushFileBuffers")
        self.info = self._query_info()

    def duplicate_raw(self, *, inheritable: bool) -> int:
        current = self._api.GetCurrentProcess()
        duplicate = wintypes.HANDLE()
        if not self._api.DuplicateHandle(
            current,
            self.handle,
            current,
            ctypes.byref(duplicate),
            0,
            bool(inheritable),
            DUPLICATE_SAME_ACCESS,
        ):
            raise _win_error("DuplicateHandle")
        return int(duplicate.value)

    def record(self, *, include_hash: bool = True) -> dict[str, Any]:
        value: dict[str, Any] = {
            "path": evidence_path(self.expected_path),
            "bytes": self.size,
            "final_path": self.final_path,
            "file_identity": self.identity,
            "reparse": False,
            "write_sharing_denied": not self.share_write,
            "delete_sharing_denied": True,
        }
        if include_hash and not self.directory:
            value["sha256"] = hashlib.sha256(self.read_bytes()).hexdigest()
        return value

    def close(self) -> None:
        if not self._closed:
            self._api.CloseHandle(self.handle)
            self._closed = True

    def __enter__(self) -> "Win32LockedHandle":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


def locked_binding(
    binding: Mapping[str, Any], label: str, *, inheritable: bool = True
) -> tuple[Win32LockedHandle, dict[str, Any]]:
    path = lexical_project_path(
        str(binding["path"]), require_exists=True, require_leaf_regular=True
    )
    handle = Win32LockedHandle.open_existing(path, inheritable=inheritable)
    data = handle.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != int(binding["bytes"]) or digest != str(binding["sha256"]):
        handle.close()
        raise ResealV3Error(f"locked same-handle binding drifted for {label}")
    record = handle.record(include_hash=False)
    record.update({"bytes": len(data), "sha256": digest})
    return handle, record


def locked_blender_executable(
    config: Mapping[str, Any], *, inheritable: bool = True
) -> tuple[Win32LockedHandle, dict[str, Any]]:
    identity = config["blender_identity"]
    path = Path(identity["path"])
    if not path.is_absolute() or not path.is_file():
        raise ResealV3Error("sealed Blender executable is missing")
    handle = Win32LockedHandle.open_existing(path, inheritable=inheritable)
    data = handle.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != int(identity["bytes"]) or digest != identity["sha256"]:
        handle.close()
        raise ResealV3Error("locked Blender executable identity drifted")
    record = handle.record(include_hash=False)
    record.update({"bytes": len(data), "sha256": digest})
    return handle, record


def json_from_locked(handle: Win32LockedHandle, label: str) -> dict[str, Any]:
    try:
        value = json.loads(handle.read_bytes().decode("utf-8"))
    except Exception as exc:
        raise ResealV3Error(f"invalid locked JSON for {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ResealV3Error(f"locked JSON root must be object for {label}")
    return value


def acquire_locked_inputs(
    config: Mapping[str, Any]
) -> tuple[dict[str, Win32LockedHandle], dict[str, dict[str, Any]]]:
    handles: dict[str, Win32LockedHandle] = {}
    records: dict[str, dict[str, Any]] = {}
    try:
        for label, binding in config["bound_artifacts"].items():
            handle, record = locked_binding(binding, label, inheritable=True)
            handles[label] = handle
            records[label] = record
    except Exception:
        for handle in handles.values():
            handle.close()
        raise
    return handles, records


def acquire_complete_review_inputs(
    config: Mapping[str, Any],
) -> tuple[dict[str, Win32LockedHandle], dict[str, dict[str, Any]]]:
    """Acquire the exact immutable input set used for authorization review.

    The preparation manifest and its config binding are opened through held
    no-follow handles just like the live path.  Keeping this in one helper
    prevents the read-only authorization-review command and ``execute_once``
    from silently computing different reviewed records.
    """

    handles, locked_records = acquire_locked_inputs(config)
    try:
        blender_handle, blender_record = locked_blender_executable(
            config, inheritable=True
        )
        handles["blender_executable"] = blender_handle
        locked_records["blender_executable"] = blender_record

        manifest_handle = Win32LockedHandle.open_existing(
            MANIFEST_PATH, inheritable=True
        )
        handles["reseal_v3_manifest"] = manifest_handle
        manifest_bytes = manifest_handle.read_bytes()
        locked_manifest = json.loads(manifest_bytes.decode("utf-8"))
        if not isinstance(locked_manifest, dict) or not isinstance(
            locked_manifest.get("artifacts"), list
        ):
            raise ResealV3Error("locked v3 manifest has an invalid artifact list")
        manifest_artifacts = {
            str(row["path"]): row for row in locked_manifest["artifacts"]
        }
        config_binding = manifest_artifacts.get(relative(CONFIG_PATH))
        if not isinstance(config_binding, dict):
            raise ResealV3Error("locked v3 manifest does not bind the v3 config")
        config_handle, config_record = locked_binding(
            config_binding, "reseal_v3_config", inheritable=True
        )
        handles["reseal_v3_config"] = config_handle
        locked_config = json_from_locked(config_handle, "reseal_v3_config")
        if locked_config != config:
            raise ResealV3Error("locked config differs from verified preparation")
        locked_records["reseal_v3_config"] = config_record
        locked_records["reseal_v3_manifest"] = {
            **manifest_handle.record(include_hash=False),
            "bytes": len(manifest_bytes),
            "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        }
        return handles, locked_records
    except Exception:
        close_handles(handles.values())
        raise


def read_only_authorization_review(
    config: Mapping[str, Any], command: Sequence[str]
) -> dict[str, Any]:
    """Emit an owner-reviewable exact record without creating run state."""

    if os.name != "nt":
        raise ResealV3Error("immutable authorization review is Windows-only")
    input_paths = [
        lexical_project_path(
            binding["path"], require_exists=True, require_leaf_regular=True
        )
        for binding in config["bound_artifacts"].values()
    ]
    input_paths.extend([CONFIG_PATH, MANIFEST_PATH])
    ancestor_handles = acquire_ancestor_directory_locks(input_paths)
    handles: dict[str, Win32LockedHandle] = {}
    try:
        handles, locked_records = acquire_complete_review_inputs(config)
        reviewed = expected_authorization_review(config, locked_records, command)
        return {
            "schema": "kira.avatar.r23_attempt04_reseal_v3_authorization_review.v1",
            "read_only": True,
            "authorization_created": False,
            "journal_created": False,
            "output_created": False,
            "process_started": False,
            "reviewed": reviewed,
            "reviewed_sha256": canonical_sha256(reviewed),
        }
    finally:
        close_handles(handles.values())
        close_handles(ancestor_handles)


def close_handles(handles: Iterable[Win32LockedHandle]) -> None:
    for handle in handles:
        try:
            handle.close()
        except Exception:
            pass


def acquire_ancestor_directory_locks(
    paths: Iterable[Path],
) -> list[Win32LockedHandle]:
    """Hold every existing input ancestor no-follow while allowing child reads/writes."""

    directories: set[Path] = set()
    root = ROOT.resolve()
    for path in paths:
        cursor = path.parent
        while not os.path.lexists(cursor):
            cursor = cursor.parent
        while True:
            directories.add(cursor)
            if cursor.resolve() == root:
                break
            cursor = cursor.parent
    handles: list[Win32LockedHandle] = []
    try:
        for directory in sorted(directories, key=lambda value: len(value.parts)):
            handles.append(
                Win32LockedHandle.open_existing(
                    directory, directory=True, share_write=True
                )
            )
    except Exception:
        close_handles(handles)
        raise
    return handles


def _auth_paths(config: Mapping[str, Any]) -> tuple[Path, Path, Path]:
    contract = config["authorization_contract"]
    directory = lexical_project_path(contract["directory"], require_exists=True)
    record = lexical_project_path(
        contract["record_path"], require_exists=True, require_leaf_regular=True
    )
    manifest = lexical_project_path(
        contract["manifest_path"], require_exists=True, require_leaf_regular=True
    )
    return directory, record, manifest


def authorization_presence(config: Mapping[str, Any]) -> dict[str, Any]:
    contract = config["authorization_contract"]
    paths = {
        "directory": ROOT / Path(contract["directory"]),
        "record": ROOT / Path(contract["record_path"]),
        "manifest": ROOT / Path(contract["manifest_path"]),
    }
    return {key: os.path.lexists(path) for key, path in paths.items()}


def expected_authorization_review(
    config: Mapping[str, Any], locked_records: Mapping[str, Any], command: Sequence[str]
) -> dict[str, Any]:
    labels = config["authorization_contract"]["reviewed_binding_labels"]
    reviewed = {label: locked_records[label] for label in labels}
    reviewed["blender_identity"] = config["blender_identity"]
    reviewed["blender_executable"] = locked_records["blender_executable"]
    # The locked author/overlay byte records are reviewed separately. Do not
    # reopen either path while validating authorization.
    reviewed["handoff"] = handoff_contract_record(config)
    reviewed["command"] = list(command)
    reviewed["command_sha256"] = canonical_sha256(list(command))
    reviewed["output_contract"] = config["output_contract"]
    return reviewed


def verify_authorization_locked(
    config: Mapping[str, Any], locked_records: Mapping[str, Any], command: Sequence[str]
) -> tuple[dict[str, Any], dict[str, Win32LockedHandle]]:
    directory, record_path, manifest_path = _auth_paths(config)
    directory_handle = Win32LockedHandle.open_existing(
        directory, directory=True, share_write=False
    )
    expected_entries = sorted(config["authorization_contract"]["directory_entries"])
    actual_entries = sorted(entry.name for entry in directory.iterdir())
    if actual_entries != expected_entries:
        directory_handle.close()
        raise ResealV3Error(f"authorization directory closure drifted: {actual_entries}")
    record_handle = Win32LockedHandle.open_existing(record_path, inheritable=True)
    manifest_handle = Win32LockedHandle.open_existing(manifest_path, inheritable=True)
    try:
        record_bytes = record_handle.read_bytes()
        manifest_bytes = manifest_handle.read_bytes()
        record = json.loads(record_bytes.decode("utf-8"))
        manifest = json.loads(manifest_bytes.decode("utf-8"))
        if not isinstance(record, dict) or not isinstance(manifest, dict):
            raise ResealV3Error("authorization JSON roots must be objects")
        final_entries = sorted(entry.name for entry in directory.iterdir())
        if final_entries != expected_entries:
            raise ResealV3Error(
                f"authorization directory closure changed after file locks: {final_entries}"
            )
        contract = config["authorization_contract"]
        expected_record_fields = {
            "schema",
            "authorized",
            "one_run_only",
            "authorization_id",
            "nonce",
            "owner_decision_text",
            "command_sha256",
            "reviewed",
            "restrictions",
        }
        if set(record) != expected_record_fields:
            raise ResealV3Error("authorization record field closure drifted")
        if set(manifest) != {"schema", "authorization_id", "record"}:
            raise ResealV3Error("authorization manifest field closure drifted")
        if record.get("schema") != contract["record_schema"]:
            raise ResealV3Error("wrong authorization record schema")
        if manifest.get("schema") != contract["manifest_schema"]:
            raise ResealV3Error("wrong authorization manifest schema")
        if record.get("authorized") is not True or record.get("one_run_only") is not True:
            raise ResealV3Error("authorization is not explicitly enabled for one run")
        if not isinstance(record.get("owner_decision_text"), str) or not record[
            "owner_decision_text"
        ].strip():
            raise ResealV3Error("authorization owner decision text is empty")
        nonce = record.get("nonce")
        if not isinstance(nonce, str) or not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", nonce):
            raise ResealV3Error("authorization nonce is invalid")
        record_hash = hashlib.sha256(record_bytes).hexdigest()
        manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
        expected_record_binding = {
            "path": relative(record_path),
            "bytes": len(record_bytes),
            "sha256": record_hash,
        }
        if manifest.get("record") != expected_record_binding:
            raise ResealV3Error("authorization manifest does not bind locked record bytes")
        if manifest.get("authorization_id") != record.get("authorization_id"):
            raise ResealV3Error("authorization IDs differ")
        expected_reviewed = expected_authorization_review(config, locked_records, command)
        if record.get("reviewed") != expected_reviewed:
            raise ResealV3Error("authorization reviewed content drifted")
        if record.get("restrictions") != contract["required_restrictions"]:
            raise ResealV3Error("authorization restrictions drifted")
        if record.get("command_sha256") != canonical_sha256(list(command)):
            raise ResealV3Error("authorization command binding drifted")
        return (
            {
                "authorization_id": record["authorization_id"],
                "nonce": nonce,
                "record": {
                    **record_handle.record(include_hash=False),
                    "bytes": len(record_bytes),
                    "sha256": record_hash,
                },
                "manifest": {
                    **manifest_handle.record(include_hash=False),
                    "bytes": len(manifest_bytes),
                    "sha256": manifest_hash,
                },
                "reviewed": expected_reviewed,
                "restrictions": record["restrictions"],
                "command_sha256": canonical_sha256(list(command)),
                "directory": {
                    **directory_handle.record(include_hash=False),
                    "exact_entries": final_entries,
                    "closure_exact_after_record_and_manifest_locks": True,
                },
            },
            {
                "authorization_record": record_handle,
                "authorization_manifest": manifest_handle,
                "_authorization_directory_parent_lock": directory_handle,
            },
        )
    except Exception:
        record_handle.close()
        manifest_handle.close()
        directory_handle.close()
        raise


def output_paths(config: Mapping[str, Any]) -> dict[str, Any]:
    contract = config["output_contract"]
    effective = lexical_future_project_path(contract["effective_directory"])
    execution = lexical_future_project_path(contract["execution_directory"])
    names = {
        "candidate": validate_windows_basename(contract["candidate_basename"], "candidate"),
        "build": validate_windows_basename(contract["build_evidence_basename"], "build"),
        "failure": validate_windows_basename(contract["failure_evidence_basename"], "failure"),
    }
    journal_names = [
        validate_windows_basename(value, "journal leaf")
        for value in config["journal_contract"]["exact_entries"]
    ]
    if len(journal_names) != len(set(name.casefold() for name in journal_names)):
        raise ResealV3Error("journal basenames collide under Windows case folding")
    return {
        "effective": effective,
        "execution": execution,
        "names": names,
        "journal_names": journal_names,
    }


def create_execution_journal(
    config: Mapping[str, Any]
) -> tuple[Win32LockedHandle, dict[str, Win32LockedHandle]]:
    paths = output_paths(config)
    execution = paths["execution"]
    if os.path.lexists(execution):
        raise ResealV3Error("execution journal already exists; nonce/run already claimed")
    safe_mkdir_parents(execution.parent)
    execution.mkdir(exist_ok=False)
    directory_handle = Win32LockedHandle.open_existing(execution, directory=True)
    leaves: dict[str, Win32LockedHandle] = {}
    try:
        for basename in paths["journal_names"]:
            leaves[basename] = Win32LockedHandle.create_new(
                execution / basename, inheritable=True
            )
        verify_journal_closure(config, execution)
    except Exception:
        close_handles(leaves.values())
        directory_handle.close()
        raise
    return directory_handle, leaves


def verify_journal_closure(config: Mapping[str, Any], directory: Path) -> list[str]:
    actual = sorted(entry.name for entry in directory.iterdir())
    expected = sorted(config["journal_contract"]["exact_entries"])
    if actual != expected:
        raise ResealV3Error(f"execution journal closure drifted: {actual}")
    for name in actual:
        validate_windows_basename(name, "actual journal leaf")
        path = directory / name
        if _is_reparse(path) or not path.is_file():
            raise ResealV3Error(f"unsafe journal entry: {path}")
    return actual


def capture_journal_closure_for_post(
    config: Mapping[str, Any], directory: Path, exceptions: list[str]
) -> list[str]:
    """Capture pre-POST journal drift without skipping the reserved POST write."""

    try:
        return verify_journal_closure(config, directory)
    except Exception as exc:
        try:
            observed = sorted(entry.name for entry in directory.iterdir())
        except Exception as observe_exc:
            observed = [
                f"OBSERVATION_FAILED:{type(observe_exc).__name__}:{observe_exc}"
            ]
        exceptions.append(
            "pre_post_journal_rescan:"
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        )
        return observed


def json_line_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build_claim(
    config: Mapping[str, Any],
    authorization: Mapping[str, Any],
    command: Sequence[str],
    *,
    controller_pid: int,
    child_pid: int | None,
    child_created_utc: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V3_AUTHORIZATION_CLAIM",
        "claimed_utc": utc_now(),
        "authorization_id": authorization["authorization_id"],
        "authorization_nonce": authorization["nonce"],
        "authorization_record_sha256": authorization["record"]["sha256"],
        "authorization_manifest_sha256": authorization["manifest"]["sha256"],
        "controller_pid": int(controller_pid),
        "child_pid": int(child_pid) if child_pid is not None else None,
        "child_created_utc": child_created_utc,
        "command": list(command),
        "command_sha256": canonical_sha256(list(command)),
        "atomic_claim": {
            "method": "CREATE_NEW_NO_FOLLOW_HELD_HANDLE",
            "preexisting_execution_directory_rejected": True,
            "single_write_after_child_pid_known": True,
        },
        "execution_flag": config["command_contract"]["controller_execution_flag"],
    }


def build_pre_run(
    config: Mapping[str, Any],
    preparation: Mapping[str, Any],
    authorization: Mapping[str, Any],
    claim_record: Mapping[str, Any],
    locked_records: Mapping[str, Any],
    command: Sequence[str],
    environment_keys: Sequence[str],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V3_PRE_RUN",
        "created_utc": utc_now(),
        "preparation_sha256": canonical_sha256(preparation),
        "authorization": authorization,
        "authorization_claim_sha256": canonical_sha256(claim_record),
        "locked_input_records": locked_records,
        "locked_input_records_sha256": canonical_sha256(locked_records),
        "command": list(command),
        "command_sha256": canonical_sha256(list(command)),
        "complete_actual_argv_required": True,
        "child_environment_keys": sorted(environment_keys),
        "author_handoff": verify_author_handoff(config),
    }


def build_post_run(
    config: Mapping[str, Any],
    *,
    pre_bytes: bytes,
    claim_bytes: bytes,
    stdout_record: Mapping[str, Any],
    stderr_record: Mapping[str, Any],
    child_pid: int | None,
    wait: Mapping[str, Any],
    output_validation: Mapping[str, Any] | None,
    exceptions: Sequence[str],
    command: Sequence[str] = (),
    journal_observed_before_post_write: Sequence[str] = (),
) -> dict[str, Any]:
    exact_entries = sorted(config["journal_contract"]["exact_entries"])
    observed_before = sorted(journal_observed_before_post_write)
    final_output_closure = (
        output_validation.get("final_closure_before_post", {})
        if isinstance(output_validation, Mapping)
        else {}
    )
    accepted = (
        not exceptions
        and wait.get("returncode") == 0
        and isinstance(output_validation, Mapping)
        and output_validation.get("classification") == "success"
        and final_output_closure.get("exact_after_child_exit") is True
        and observed_before == exact_entries
    )
    return {
        "schema_version": 1,
        "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V3_POST_RUN",
        "acceptance_status": (
            "PRE_POST_GATES_PASSED_PENDING_FINAL_CONTROLLER_RESCAN"
            if accepted
            else "FAILED"
        ),
        "ended_utc": utc_now(),
        "child_pid": child_pid,
        "command": list(command),
        "command_sha256": canonical_sha256(list(command)),
        "authorization_claim": {
            "bytes": len(claim_bytes),
            "sha256": hashlib.sha256(claim_bytes).hexdigest(),
        },
        "final_pre_run": {
            "bytes": len(pre_bytes),
            "sha256": hashlib.sha256(pre_bytes).hexdigest(),
        },
        "stdout": dict(stdout_record),
        "stderr": dict(stderr_record),
        "wait": dict(wait),
        "output_validation": output_validation,
        "exceptions": list(exceptions),
        "journal_exact_closure": {
            "expected_entries": exact_entries,
            "observed_before_post_write": observed_before,
            "exact_before_post_write": observed_before == exact_entries,
            "post_run_is_final_reserved_leaf": True,
            "all_leaves_create_new_no_follow": True,
            "post_flush_rescan_is_a_controller_success_condition": True,
            "post_flush_rescan_result_is_not_self_referentially_claimed_inside_post": True,
            "extra_entries_allowed": False,
        },
    }


def build_emergency_post_run(
    *,
    command: Sequence[str],
    child_pid: int | None,
    wait: Mapping[str, Any],
    output_validation: Mapping[str, Any] | None,
    exceptions: Sequence[str],
    finalizer_error: BaseException,
) -> dict[str, Any]:
    """Minimal truthful POST when an unexpected pre-write finalizer gate fails."""

    return {
        "schema_version": 1,
        "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V3_POST_RUN",
        "acceptance_status": "FAILED",
        "ended_utc": utc_now(),
        "child_pid": child_pid,
        "command": list(command),
        "command_sha256": canonical_sha256(list(command)),
        "wait": dict(wait),
        "output_validation": output_validation,
        "exceptions": list(exceptions),
        "emergency_single_write_finalizer": {
            "used": True,
            "reason": "UNEXPECTED_PRE_POST_GATE_FAILED_NORMAL_POST_ASSEMBLY_COULD_NOT_COMPLETE",
            "error_type": type(finalizer_error).__name__,
            "error": str(finalizer_error),
            "traceback": traceback.format_exc(),
            "post_was_empty_before_emergency_write_required": True,
            "post_flush_rescan_is_still_a_controller_success_condition": True,
            "final_controller_result_is_not_claimed_inside_post": True,
        },
    }


def minimal_child_environment(
    config: Mapping[str, Any],
    *,
    lease: Mapping[str, Any],
    claim_path: Path,
    pre_path: Path,
    event_handle: int,
    output_locked_event_handle: int,
    output_validated_event_handle: int,
    output_handle_pipe_write: int,
) -> dict[str, str]:
    process = config["process_contract"]
    environment = {
        key: os.environ[key]
        for key in process["environment_allowlist"]
        if key in os.environ
    }
    for key in process["forbidden_environment_keys"]:
        environment.pop(key, None)
    environment.update(
        {
            "KIRA_R23_RESEAL_V3_LOCK_LEASE_JSON": json.dumps(
                lease, sort_keys=True, separators=(",", ":")
            ),
            "KIRA_R23_RESEAL_V3_CLAIM_PATH": relative(claim_path),
            "KIRA_R23_RESEAL_V3_PRE_RUN_PATH": relative(pre_path),
            "KIRA_R23_RESEAL_V3_READY_EVENT_HANDLE": str(int(event_handle)),
            "KIRA_R23_RESEAL_V3_OUTPUT_LOCKED_EVENT_HANDLE": str(
                int(output_locked_event_handle)
            ),
            "KIRA_R23_RESEAL_V3_OUTPUT_VALIDATED_EVENT_HANDLE": str(
                int(output_validated_event_handle)
            ),
            "KIRA_R23_RESEAL_V3_OUTPUT_HANDLE_PIPE_WRITE": str(
                int(output_handle_pipe_write)
            ),
        }
    )
    return environment


def validate_output_directory(
    config: Mapping[str, Any], expected_provenance: Mapping[str, Any], *, hold: bool = False
) -> Any:
    paths = output_paths(config)
    directory = paths["effective"]
    if not directory.is_dir() or _is_reparse(directory):
        raise ResealV3Error("effective output directory missing or unsafe")
    directory_handle = Win32LockedHandle.open_existing(directory, directory=True)
    opened: list[Win32LockedHandle] = []
    try:
        entries = sorted(entry.name for entry in directory.iterdir())
        contract = config["output_contract"]
        success_entries = sorted(contract["success_directory_entries"])
        failure_entries = sorted(contract["failure_directory_entries"])
        if entries == success_entries:
            classification = "success"
        elif entries == failure_entries:
            classification = "failure"
        else:
            raise ResealV3Error(f"output directory closure invalid: {entries}")
        records: dict[str, Any] = {}
        evidence_payload: dict[str, Any] | None = None
        for name in entries:
            validate_windows_basename(name, "output leaf")
            handle = Win32LockedHandle.open_existing(directory / name)
            opened.append(handle)
            data = handle.read_bytes()
            if handle.identity["links"] != 1:
                raise ResealV3Error(f"multi-link output leaf rejected: {name}")
            records[name] = {
                **handle.record(include_hash=False),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            if name.endswith(".json"):
                payload = json.loads(data.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ResealV3Error("output evidence root is not an object")
                if payload.get("reseal_v3_provenance") != expected_provenance:
                    raise ResealV3Error("output provenance is absent or drifted")
                evidence_payload = payload
        if classification == "success":
            if evidence_payload is None:
                raise ResealV3Error("success BUILD_EVIDENCE payload is absent")
            expected_identity = {
                "schema_version": 1,
                "artifact_kind": "KIRA_R23_CC0_AFES_CORE_TRANSFER_AUTHOR_ATTEMPT01",
                "status": "INACTIVE_PRIVATE_CANDIDATE_AUTHORED_POSTSAVE_AUDIT_REQUIRED",
            }
            if any(
                evidence_payload.get(key) != value
                for key, value in expected_identity.items()
            ):
                raise ResealV3Error("success BUILD_EVIDENCE schema/status drifted")
            candidate = records[contract["candidate_basename"]]
            if candidate["bytes"] < int(contract["minimum_candidate_bytes"]):
                raise ResealV3Error("candidate is unexpectedly small")
            candidate_handle = next(
                handle
                for handle in opened
                if handle.expected_path.name == contract["candidate_basename"]
            )
            if not candidate_handle.read_bytes().startswith(
                contract["candidate_signature_ascii"].encode("ascii")
            ):
                raise ResealV3Error("candidate does not have a Blender signature")
            candidate_claim = evidence_payload.get("candidate")
            expected_candidate_claim = {
                "path": candidate["path"],
                "bytes": candidate["bytes"],
                "sha256": candidate["sha256"],
            }
            if not isinstance(candidate_claim, dict) or {
                key: candidate_claim.get(key) for key in expected_candidate_claim
            } != expected_candidate_claim:
                raise ResealV3Error(
                    "BUILD_EVIDENCE candidate binding differs from parent-locked candidate"
                )
            required_candidate_state = {
                "inactive": True,
                "unassigned": True,
                "unpublished": True,
                "runtime_eligible": False,
                "owner_approved": False,
            }
            if any(
                candidate_claim.get(key) is not value
                for key, value in required_candidate_state.items()
            ):
                raise ResealV3Error("BUILD_EVIDENCE candidate state claims drifted")
        else:
            if evidence_payload is None:
                raise ResealV3Error("failure evidence payload is absent")
            expected_identity = {
                "schema_version": 1,
                "artifact_kind": "KIRA_R23_CC0_AFES_CORE_TRANSFER_AUTHOR_ATTEMPT01_FAILURE",
                "status": "AUTHOR_NO_GO_NO_CANDIDATE_ACCEPTED",
            }
            if any(
                evidence_payload.get(key) != value
                for key, value in expected_identity.items()
            ):
                raise ResealV3Error("failure evidence schema/status drifted")
        result = {
            "classification": classification,
            "directory": directory_handle.record(include_hash=False),
            "exact_entries": entries,
            "records": records,
        }
        if hold:
            held = [directory_handle, *opened]
            directory_handle = None
            opened = []
            return result, held
        return result
    finally:
        close_handles(opened)
        if directory_handle is not None:
            directory_handle.close()


def validate_transferred_output_handles(
    config: Mapping[str, Any],
    expected_provenance: Mapping[str, Any],
    transfer: Mapping[str, Any],
    *,
    hold: bool = False,
) -> Any:
    """Validate child-opened outputs through same-file-object duplicates.

    The writable BUILD_EVIDENCE handle was opened by the locked child with
    FILE_SHARE_READ only.  Duplicating that file object into this process
    preserves its deny-write/delete share reservation without a close/reopen
    gap and avoids the incompatible second CreateFileW open.
    """

    if set(transfer) != {"schema", "classification", "handles"}:
        raise ResealV3Error("output handle transfer field closure drifted")
    if transfer.get("schema") != config["process_contract"][
        "output_handle_transfer_schema"
    ]:
        raise ResealV3Error("output handle transfer schema drifted")
    classification = transfer.get("classification")
    contract = config["output_contract"]
    if classification == "success":
        expected_entries = sorted(contract["success_directory_entries"])
    elif classification == "failure":
        expected_entries = sorted(contract["failure_directory_entries"])
    else:
        raise ResealV3Error("output handle transfer classification is invalid")
    raw_handles = transfer.get("handles")
    expected_labels = {"directory", *expected_entries}
    if not isinstance(raw_handles, dict) or set(raw_handles) != expected_labels:
        raise ResealV3Error("output transferred-handle label closure drifted")
    values = list(raw_handles.values())
    if (
        any(not isinstance(value, int) or value <= 0 for value in values)
        or len(values) != len(set(values))
    ):
        raise ResealV3Error("output transferred handles are invalid or duplicated")

    paths = output_paths(config)
    directory = paths["effective"]
    wrapped: dict[str, Win32LockedHandle] = {}
    unclaimed = set(int(value) for value in values)
    try:
        directory_raw = int(raw_handles["directory"])
        unclaimed.discard(directory_raw)
        directory_handle = Win32LockedHandle(
            directory_raw, directory, directory=True
        )
        wrapped["directory"] = directory_handle
        for name in expected_entries:
            validate_windows_basename(name, "transferred output leaf")
            leaf_raw = int(raw_handles[name])
            unclaimed.discard(leaf_raw)
            handle = Win32LockedHandle(
                leaf_raw, directory / name, directory=False
            )
            wrapped[name] = handle

        actual_entries = sorted(entry.name for entry in directory.iterdir())
        if actual_entries != expected_entries:
            raise ResealV3Error(
                f"transferred output directory closure invalid: {actual_entries}"
            )
        records: dict[str, Any] = {}
        evidence_payload: dict[str, Any] | None = None
        for name in expected_entries:
            handle = wrapped[name]
            data = handle.read_bytes()
            if handle.identity["links"] != 1:
                raise ResealV3Error(f"multi-link transferred output rejected: {name}")
            records[name] = {
                **handle.record(include_hash=False),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "same_file_object_duplicated_from_locked_child": True,
            }
            if name.endswith(".json"):
                payload = json.loads(data.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ResealV3Error("transferred evidence root is not an object")
                if payload.get("reseal_v3_provenance") != expected_provenance:
                    raise ResealV3Error("transferred output provenance drifted")
                evidence_payload = payload

        if classification == "success":
            if evidence_payload is None:
                raise ResealV3Error("transferred BUILD_EVIDENCE is absent")
            expected_identity = {
                "schema_version": 1,
                "artifact_kind": "KIRA_R23_CC0_AFES_CORE_TRANSFER_AUTHOR_ATTEMPT01",
                "status": "INACTIVE_PRIVATE_CANDIDATE_AUTHORED_POSTSAVE_AUDIT_REQUIRED",
            }
            if any(
                evidence_payload.get(key) != value
                for key, value in expected_identity.items()
            ):
                raise ResealV3Error("transferred BUILD_EVIDENCE identity drifted")
            candidate = records[contract["candidate_basename"]]
            candidate_handle = wrapped[contract["candidate_basename"]]
            if candidate["bytes"] < int(contract["minimum_candidate_bytes"]):
                raise ResealV3Error("transferred candidate is unexpectedly small")
            if not candidate_handle.read_bytes().startswith(
                contract["candidate_signature_ascii"].encode("ascii")
            ):
                raise ResealV3Error("transferred candidate signature is not BLENDER")
            candidate_claim = evidence_payload.get("candidate")
            expected_candidate_claim = {
                "path": candidate["path"],
                "bytes": candidate["bytes"],
                "sha256": candidate["sha256"],
            }
            if not isinstance(candidate_claim, dict) or {
                key: candidate_claim.get(key) for key in expected_candidate_claim
            } != expected_candidate_claim:
                raise ResealV3Error(
                    "transferred BUILD_EVIDENCE differs from duplicated candidate"
                )
            required_candidate_state = {
                "inactive": True,
                "unassigned": True,
                "unpublished": True,
                "runtime_eligible": False,
                "owner_approved": False,
            }
            if any(
                candidate_claim.get(key) is not value
                for key, value in required_candidate_state.items()
            ):
                raise ResealV3Error("transferred candidate state claims drifted")
        else:
            expected_identity = {
                "schema_version": 1,
                "artifact_kind": "KIRA_R23_CC0_AFES_CORE_TRANSFER_AUTHOR_ATTEMPT01_FAILURE",
                "status": "AUTHOR_NO_GO_NO_CANDIDATE_ACCEPTED",
            }
            if evidence_payload is None or any(
                evidence_payload.get(key) != value
                for key, value in expected_identity.items()
            ):
                raise ResealV3Error("transferred failure evidence identity drifted")

        result = {
            "classification": classification,
            "directory": directory_handle.record(include_hash=False),
            "exact_entries": actual_entries,
            "records": records,
            "handle_transfer": {
                "schema": transfer["schema"],
                "same_file_objects_held_through_post": bool(hold),
                "no_close_reopen_gap": True,
            },
        }
        held = list(wrapped.values())
        if hold:
            wrapped = {}
            return result, held
        return result
    finally:
        close_handles(wrapped.values())
        api = _kernel32()
        for raw in unclaimed:
            api.CloseHandle(raw)


def rescan_transferred_output_closure(
    config: Mapping[str, Any],
    output_validation: Mapping[str, Any],
    held_handles: Sequence[Win32LockedHandle],
) -> dict[str, Any]:
    """Reprove output namespace and locked leaf bytes after child exit."""

    if not held_handles:
        raise ResealV3Error("final output rescan lacks held transferred handles")
    paths = output_paths(config)
    directory_handles = [handle for handle in held_handles if handle.directory]
    leaf_handles = {
        handle.expected_path.name: handle
        for handle in held_handles
        if not handle.directory
    }
    if len(directory_handles) != 1:
        raise ResealV3Error("final output rescan directory-handle closure drifted")
    directory_handle = directory_handles[0]
    if _normal_final_path(directory_handle.final_path) != _normal_final_path(
        str(paths["effective"])
    ):
        raise ResealV3Error("final output rescan directory identity drifted")
    expected_entries = sorted(output_validation["exact_entries"])
    actual_entries = sorted(entry.name for entry in paths["effective"].iterdir())
    if actual_entries != expected_entries:
        raise ResealV3Error(
            f"final output directory closure drifted after child exit: {actual_entries}"
        )
    if set(leaf_handles) != set(expected_entries):
        raise ResealV3Error("final output held-leaf closure drifted")
    for name in expected_entries:
        handle = leaf_handles[name]
        data = handle.read_bytes()
        current = {
            "path": evidence_path(handle.expected_path),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "file_identity": handle.identity,
        }
        prior = output_validation["records"][name]
        if any(prior.get(key) != value for key, value in current.items()):
            raise ResealV3Error(f"final locked output bytes/identity drifted: {name}")
    return {
        "expected_entries": expected_entries,
        "observed_entries": actual_entries,
        "exact_after_child_exit": True,
        "locked_leaf_bytes_hashes_and_identities_unchanged": True,
        "same_file_object_handles_still_held": True,
    }


def capture_final_output_closure_for_post(
    config: Mapping[str, Any],
    output_validation: Mapping[str, Any],
    held_handles: Sequence[Win32LockedHandle],
    exceptions: list[str],
) -> dict[str, Any]:
    """Turn pre-POST closure failure into durable POST evidence, never a skip."""

    try:
        return rescan_transferred_output_closure(
            config, output_validation, held_handles
        )
    except Exception as exc:
        message = f"final_output_rescan:{type(exc).__name__}: {exc}"
        exceptions.append(message)
        expected = sorted(output_validation.get("exact_entries", []))
        try:
            observed = sorted(
                entry.name for entry in output_paths(config)["effective"].iterdir()
            )
        except Exception as observe_exc:
            observed = [
                f"OBSERVATION_FAILED:{type(observe_exc).__name__}:{observe_exc}"
            ]
        return {
            "expected_entries": expected,
            "observed_entries": observed,
            "exact_after_child_exit": False,
            "locked_leaf_bytes_hashes_and_identities_unchanged": False,
            "same_file_object_handles_still_held": bool(held_handles),
            "acceptance": "FAIL_OUTPUT_CLOSURE_DRIFT_POST_MUST_STILL_BE_WRITTEN",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }


def _create_event(inheritable: bool = True) -> int:
    api = _kernel32()
    handle = api.CreateEventW(None, True, False, None)
    if not handle:
        raise _win_error("CreateEventW")
    value = int(handle)
    if inheritable and not api.SetHandleInformation(
        value, HANDLE_FLAG_INHERIT, HANDLE_FLAG_INHERIT
    ):
        api.CloseHandle(value)
        raise _win_error("SetHandleInformation(event)")
    return value


def _create_child_to_parent_pipe() -> tuple[int, int]:
    """Create a framed one-message pipe; only the child write end inherits."""

    api = _kernel32()
    read_handle = wintypes.HANDLE()
    write_handle = wintypes.HANDLE()
    if not api.CreatePipe(
        ctypes.byref(read_handle), ctypes.byref(write_handle), None, 0
    ):
        raise _win_error("CreatePipe(output handle transfer)")
    read_value = int(read_handle.value)
    write_value = int(write_handle.value)
    try:
        if not api.SetHandleInformation(
            write_value, HANDLE_FLAG_INHERIT, HANDLE_FLAG_INHERIT
        ):
            raise _win_error("SetHandleInformation(output transfer write)")
        if not api.SetHandleInformation(read_value, HANDLE_FLAG_INHERIT, 0):
            raise _win_error("SetHandleInformation(output transfer read)")
        return read_value, write_value
    except Exception:
        api.CloseHandle(read_value)
        api.CloseHandle(write_value)
        raise


def _read_handle_exact(handle: int, length: int) -> bytes:
    api = _kernel32()
    chunks: list[bytes] = []
    remaining = int(length)
    while remaining:
        amount = min(64 * 1024, remaining)
        buffer = ctypes.create_string_buffer(amount)
        read = wintypes.DWORD()
        if not api.ReadFile(handle, buffer, amount, ctypes.byref(read), None):
            raise _win_error("ReadFile(output handle transfer)")
        if read.value == 0:
            raise ResealV3Error("output handle transfer pipe ended early")
        chunks.append(buffer.raw[: read.value])
        remaining -= int(read.value)
    return b"".join(chunks)


def read_output_handle_transfer(handle: int) -> dict[str, Any]:
    length = int.from_bytes(_read_handle_exact(handle, 4), "little")
    if length <= 0 or length > 64 * 1024:
        raise ResealV3Error("output handle transfer frame length is invalid")
    try:
        value = json.loads(_read_handle_exact(handle, length).decode("utf-8"))
    except Exception as exc:
        raise ResealV3Error(f"output handle transfer JSON is invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise ResealV3Error("output handle transfer root is not an object")
    return value


def execute_once(
    config: Mapping[str, Any], preparation: Mapping[str, Any], command: Sequence[str]
) -> int:
    if os.name != "nt":
        raise ResealV3Error("live v3 execution is Windows-only")
    if authorization_presence(config) != {
        "directory": True,
        "record": True,
        "manifest": True,
    }:
        raise ResealV3Error("exact live authorization package is absent")
    authorization_directory = ROOT / Path(config["authorization_contract"]["directory"])
    ancestor_paths = [
        lexical_project_path(
            binding["path"], require_exists=True, require_leaf_regular=True
        )
        for binding in config["bound_artifacts"].values()
    ]
    ancestor_paths.extend([CONFIG_PATH, MANIFEST_PATH, authorization_directory / "AUTHORIZATION.json", authorization_directory / "PACKAGE_MANIFEST.json"])
    future_outputs = output_paths(config)
    ancestor_paths.extend([future_outputs["effective"], future_outputs["execution"]])
    ancestor_handles = acquire_ancestor_directory_locks(ancestor_paths)
    handles: dict[str, Win32LockedHandle] = {}
    locked_records: dict[str, dict[str, Any]] = {}
    auth_handles: dict[str, Win32LockedHandle] = {}
    directory_handle: Win32LockedHandle | None = None
    journal_handles: dict[str, Win32LockedHandle] = {}
    post_handle: Win32LockedHandle | None = None
    event_handle: int | None = None
    output_locked_event_handle: int | None = None
    output_validated_event_handle: int | None = None
    output_handle_pipe_read: int | None = None
    output_handle_pipe_write: int | None = None
    process: subprocess.Popen[Any] | None = None
    exceptions: list[str] = []
    wait: dict[str, Any] = {"returncode": None, "timed_out": False}
    output_validation: dict[str, Any] | None = None
    claim_bytes = b""
    pre_bytes = b""
    output_hold_handles: list[Win32LockedHandle] = []
    try:
        handles, locked_records = acquire_complete_review_inputs(config)
        authorization, auth_handles = verify_authorization_locked(
            config, locked_records, command
        )
        for label, handle in auth_handles.items():
            if label.startswith("_"):
                continue
            handles[label] = handle
            locked_records[label] = {
                **handle.record(include_hash=False),
                "bytes": authorization[label.split("authorization_")[-1]]["bytes"],
                "sha256": authorization[label.split("authorization_")[-1]]["sha256"],
            }
        directory_handle, journal_handles = create_execution_journal(config)
        journal = config["journal_contract"]
        claim_handle = journal_handles[journal["claim_basename"]]
        pre_handle = journal_handles[journal["pre_run_basename"]]
        stdout_handle = journal_handles[journal["stdout_basename"]]
        stderr_handle = journal_handles[journal["stderr_basename"]]
        post_handle = journal_handles[journal["post_run_basename"]]
        event_handle = _create_event(inheritable=True)
        output_locked_event_handle = _create_event(inheritable=True)
        output_validated_event_handle = _create_event(inheritable=True)
        output_handle_pipe_read, output_handle_pipe_write = (
            _create_child_to_parent_pipe()
        )
        lease = {
            label: {
                "handle": int(handle.handle),
                "path": evidence_path(handle.expected_path),
                "bytes": locked_records[label]["bytes"],
                "sha256": locked_records[label]["sha256"],
                "file_identity": handle.identity,
            }
            for label, handle in handles.items()
        }
        lease.update(
            {
                "authorization_claim": {
                    "handle": claim_handle.handle,
                    "path": relative(claim_handle.expected_path),
                    "initial_bytes": 0,
                },
                "pre_run": {
                    "handle": pre_handle.handle,
                    "path": relative(pre_handle.expected_path),
                    "initial_bytes": 0,
                },
            }
        )
        env = minimal_child_environment(
            config,
            lease=lease,
            claim_path=claim_handle.expected_path,
            pre_path=pre_handle.expected_path,
            event_handle=event_handle,
            output_locked_event_handle=output_locked_event_handle,
            output_validated_event_handle=output_validated_event_handle,
            output_handle_pipe_write=output_handle_pipe_write,
        )
        inheritable_handles = [handle.handle for handle in handles.values()]
        inheritable_handles.extend(
            [
                claim_handle.handle,
                pre_handle.handle,
                event_handle,
                output_locked_event_handle,
                output_validated_event_handle,
                output_handle_pipe_write,
            ]
        )
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.lpAttributeList = {"handle_list": inheritable_handles}
        import msvcrt

        # Transfer duplicates to the CRT/Popen streams. The original no-follow
        # handles remain open and continue denying write/delete through POST.
        stdout_fd = msvcrt.open_osfhandle(
            stdout_handle.duplicate_raw(inheritable=True), os.O_WRONLY
        )
        stderr_fd = msvcrt.open_osfhandle(
            stderr_handle.duplicate_raw(inheritable=True), os.O_WRONLY
        )
        child_created = utc_now()
        with os.fdopen(stdout_fd, "wb", buffering=0) as stdout_stream, os.fdopen(
            stderr_fd, "wb", buffering=0
        ) as stderr_stream:
            process = subprocess.Popen(
                list(command),
                cwd=ROOT,
                stdout=stdout_stream,
                stderr=stderr_stream,
                shell=False,
                close_fds=True,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
                env=env,
            )
            # The child owns the only remaining write end. A framed transfer
            # received from the read end therefore comes from this exact
            # inherited process boundary.
            _kernel32().CloseHandle(output_handle_pipe_write)
            output_handle_pipe_write = None
            for handle in [*handles.values(), *journal_handles.values()]:
                handle.set_inheritable(False)
            api = _kernel32()
            for inherited_event in (
                event_handle,
                output_locked_event_handle,
                output_validated_event_handle,
            ):
                if not api.SetHandleInformation(
                    inherited_event, HANDLE_FLAG_INHERIT, 0
                ):
                    raise _win_error("clear inherited event flag")
            claim = build_claim(
                config,
                authorization,
                command,
                controller_pid=os.getpid(),
                child_pid=int(process.pid),
                child_created_utc=child_created,
            )
            claim_bytes = json_line_bytes(claim)
            claim_handle.write_once(claim_bytes)
            pre = build_pre_run(
                config,
                preparation,
                authorization,
                claim,
                locked_records,
                command,
                sorted(env),
            )
            pre_bytes = json_line_bytes(pre)
            pre_handle.write_once(pre_bytes)
            if not _kernel32().SetEvent(event_handle):
                raise _win_error("SetEvent")
            deadline = time.monotonic() + float(
                config["process_contract"]["timeout_seconds"]
            )
            while time.monotonic() < deadline:
                if (
                    _kernel32().WaitForSingleObject(
                        output_locked_event_handle, 0
                    )
                    == WAIT_OBJECT_0
                ):
                    expected_provenance = {
                        "schema": "kira.avatar.r23_attempt04_reseal_v3_provenance.v1",
                        "authorization_id": authorization["authorization_id"],
                        "authorization_nonce": authorization["nonce"],
                        "command_sha256": canonical_sha256(list(command)),
                        "sealed_author_config": locked_records["sealed_author_config"],
                        "repair_overlay_config": locked_records["repair_overlay_config"],
                        "r19_source_blend": locked_records["r19_source_blend"],
                    }
                    if output_handle_pipe_read is None:
                        raise ResealV3Error("output handle-transfer read end is absent")
                    transfer = read_output_handle_transfer(
                        output_handle_pipe_read
                    )
                    # These are same-file-object duplicates of the child's
                    # already-held locks. No incompatible CreateFileW reopen
                    # and no close/reopen mutation window occurs.
                    output_validation, output_hold_handles = (
                        validate_transferred_output_handles(
                            config, expected_provenance, transfer, hold=True
                        )
                    )
                    if not _kernel32().SetEvent(output_validated_event_handle):
                        raise _win_error("SetEvent(output validated)")
                    break
                if process.poll() is not None:
                    break
                time.sleep(0.02)
            remaining = max(0.01, deadline - time.monotonic())
            try:
                returncode = process.wait(timeout=remaining)
                wait["returncode"] = int(returncode)
            except subprocess.TimeoutExpired:
                wait["timed_out"] = True
                process.terminate()
                try:
                    wait["returncode"] = int(
                        process.wait(
                            timeout=float(
                                config["process_contract"]["termination_grace_seconds"]
                            )
                        )
                    )
                except subprocess.TimeoutExpired:
                    process.kill()
                    wait["returncode"] = int(process.wait())
    except Exception as exc:
        exceptions.append(f"{type(exc).__name__}: {exc}")
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
    finally:
        if directory_handle is not None and journal_handles:
            try:
                journal = config["journal_contract"]
                claim_handle = journal_handles[journal["claim_basename"]]
                pre_handle = journal_handles[journal["pre_run_basename"]]
                post_handle = journal_handles[journal["post_run_basename"]]
                if not claim_bytes:
                    claim_bytes = json_line_bytes(
                        {
                            "schema_version": 1,
                            "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V3_AUTHORIZATION_CLAIM",
                            "claimed_utc": utc_now(),
                            "controller_pid": os.getpid(),
                            "child_pid": int(process.pid) if process is not None else None,
                            "claim_failed_before_full_binding": True,
                            "command_sha256": canonical_sha256(list(command)),
                        }
                    )
                    claim_handle.write_once(claim_bytes)
                if not pre_bytes:
                    pre_bytes = json_line_bytes(
                        {
                            "schema_version": 1,
                            "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V3_PRE_RUN",
                            "created_utc": utc_now(),
                            "launch_refused_or_failed_before_full_pre_run": True,
                            "command_sha256": canonical_sha256(list(command)),
                        }
                    )
                    pre_handle.write_once(pre_bytes)
                actual_claim_bytes = claim_handle.read_bytes()
                actual_pre_bytes = pre_handle.read_bytes()
                if claim_bytes != actual_claim_bytes:
                    exceptions.append("final_claim_bytes_differ_from_intended_write")
                if pre_bytes != actual_pre_bytes:
                    exceptions.append("final_pre_bytes_differ_from_intended_write")
                # POST binds the bytes reread from the still-locked handles,
                # never merely the in-memory value intended for write_once().
                claim_bytes = actual_claim_bytes
                pre_bytes = actual_pre_bytes
                stdout_handle = journal_handles[journal["stdout_basename"]]
                stderr_handle = journal_handles[journal["stderr_basename"]]
                stdout_data = stdout_handle.read_bytes()
                stderr_data = stderr_handle.read_bytes()
                stdout_record = {
                    **stdout_handle.record(include_hash=False),
                    "bytes": len(stdout_data),
                    "sha256": hashlib.sha256(stdout_data).hexdigest(),
                }
                stderr_record = {
                    **stderr_handle.record(include_hash=False),
                    "bytes": len(stderr_data),
                    "sha256": hashlib.sha256(stderr_data).hexdigest(),
                }
                if output_validation is not None:
                    output_validation = {
                        **output_validation,
                        "final_closure_before_post": capture_final_output_closure_for_post(
                            config,
                            output_validation,
                            output_hold_handles,
                            exceptions,
                        ),
                    }
                observed_before_post = capture_journal_closure_for_post(
                    config, directory_handle.expected_path, exceptions
                )
                post = build_post_run(
                    config,
                    pre_bytes=pre_bytes,
                    claim_bytes=claim_bytes,
                    stdout_record=stdout_record,
                    stderr_record=stderr_record,
                    child_pid=int(process.pid) if process is not None else None,
                    wait=wait,
                    output_validation=output_validation,
                    exceptions=exceptions,
                    command=command,
                    journal_observed_before_post_write=observed_before_post,
                )
                post_handle.write_once(json_line_bytes(post))
                observed_after_post = verify_journal_closure(
                    config, directory_handle.expected_path
                )
                if observed_after_post != observed_before_post:
                    raise ResealV3Error("journal closure changed across POST flush")
                if (
                    output_validation is not None
                    and output_validation["final_closure_before_post"].get(
                        "exact_after_child_exit"
                    )
                    is True
                ):
                    final_after_post = rescan_transferred_output_closure(
                        config, output_validation, output_hold_handles
                    )
                    if final_after_post != output_validation[
                        "final_closure_before_post"
                    ]:
                        raise ResealV3Error(
                            "output closure changed across final POST flush"
                        )
            except Exception as post_exc:
                exceptions.append(
                    f"post_run:{type(post_exc).__name__}: {post_exc}\n"
                    f"{traceback.format_exc()}"
                )
                # Every unexpected failure before the normal POST write must
                # still consume the already-reserved POST leaf exactly once.
                # A failure after a successful POST flush is not rewritten.
                if post_handle is not None:
                    try:
                        post_handle.info = post_handle._query_info()
                        if post_handle.size == 0:
                            emergency = build_emergency_post_run(
                                command=command,
                                child_pid=(
                                    int(process.pid)
                                    if process is not None
                                    else None
                                ),
                                wait=wait,
                                output_validation=output_validation,
                                exceptions=exceptions,
                                finalizer_error=post_exc,
                            )
                            post_handle.write_once(json_line_bytes(emergency))
                    except Exception as emergency_exc:
                        exceptions.append(
                            "post_run_emergency_write:"
                            f"{type(emergency_exc).__name__}: {emergency_exc}"
                        )
        if event_handle is not None:
            _kernel32().CloseHandle(event_handle)
        if output_locked_event_handle is not None:
            _kernel32().CloseHandle(output_locked_event_handle)
        if output_validated_event_handle is not None:
            _kernel32().CloseHandle(output_validated_event_handle)
        if output_handle_pipe_read is not None:
            _kernel32().CloseHandle(output_handle_pipe_read)
        if output_handle_pipe_write is not None:
            _kernel32().CloseHandle(output_handle_pipe_write)
        close_handles(journal_handles.values())
        close_handles(output_hold_handles)
        if directory_handle is not None:
            directory_handle.close()
        close_handles(handles.values())
        close_handles(auth_handles.values())
        close_handles(ancestor_handles)
    return 0 if not exceptions and wait.get("returncode") == 0 else 7


def arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--execute-attempt04-reseal-v3", action="store_true")
    modes.add_argument("--print-authorization-review", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = arguments(argv)
    config, preparation = verify_preparation()
    command = build_command(config)
    presence = authorization_presence(config)
    if args.print_authorization_review:
        if any(presence.values()):
            raise ResealV3Error(
                "authorization-review output requires the authorization directory to be absent"
            )
        print(
            json.dumps(
                read_only_authorization_review(config, command),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if not args.execute_attempt04_reseal_v3:
        if any(presence.values()) and not all(presence.values()):
            raise ResealV3Error("partial authorization package exists")
        print(
            json.dumps(
                {
                    "status": config["status"],
                    "execution_enabled": False,
                    "authorization_presence": presence,
                    "command": command,
                    "command_sha256": canonical_sha256(command),
                    "verified_records": (
                        len(preparation["manifest_artifacts"])
                        + len(preparation["bound_artifacts"])
                    ),
                    "blender_invoked": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if not config["execution_gate"]["live_authorization_required"]:
        raise ResealV3Error("live authorization requirement drifted")
    return execute_once(config, preparation, command)


if __name__ == "__main__":
    raise SystemExit(main())
