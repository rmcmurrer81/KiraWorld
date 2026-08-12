#!/usr/bin/env python3
"""Private locked controller for R25 AFES locked-pair Attempt 06.

The controller is inert when imported normally.  Only the exact external
bootstrap can pre-inject the process-local capability and exact context that
the entry closure captures while these bytes are privately compiled.

Attempt 06 preserves the exact Attempt-05 recursively strict,
foundation-bound child-result validation and the exact Attempt-04 suspended
child/Job/pipe/receipt core.  Its only runtime change is a stable Windows
directory identity tree.  Every ancestor and leaf is opened without delete
sharing, checked by handle-derived final path and NTFS file identity, and held
through child cleanup.  Fixed-content pair/run/config/scripts/data roots get
a protected no-child-create DACL plus a persistent change notification, so a
transient create/delete or security change cannot disappear before final
verification.
"""

from __future__ import annotations

import builtins
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
from types import ModuleType
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v6.json"
)
OUTPUT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution/attempt_06"
)
RUNTIME_BASE_RELATIVE_PATH = (
    "RecoverySprint/runtime_cache/r25_blender_v6/attempt_06"
)
HEX64 = re.compile(r"[0-9a-f]{64}")
PASSTHROUGH_IF_PRESENT = (
    "SYSTEMROOT", "WINDIR", "USERNAME", "USERPROFILE", "HOMEDRIVE",
    "HOMEPATH", "LOCALAPPDATA", "APPDATA",
)
FORCED_ENVIRONMENT = {
    "PYTHONNOUSERSITE": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
}
OUTER_TRUTH_BOUNDARY = [
    "READ_ONLY_FOUNDATION_DIAGNOSTIC",
    "NO_BLEND_MUTATION_OR_SAVE",
    "NO_RENDER_OR_EXPORT",
    "NO_CANDIDATE_OR_BODY_AUTHORING",
    "THIS_SINGLE_RUN_IS_NOT_ACCEPTANCE",
]


class LockedPairV6Error(RuntimeError):
    """An Attempt-06 parent boundary failed closed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def _require_hex(value: object, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise LockedPairV6Error(f"{label}_not_sha256")
    return value


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _normalized_windows_path(value: str | Path) -> str:
    text = os.path.normpath(os.fspath(value))
    if text.startswith("\\\\?\\UNC\\"):
        text = "\\\\" + text[8:]
    elif text.startswith("\\\\?\\"):
        text = text[4:]
    return os.path.normcase(os.path.normpath(text))


class _ByHandleFileInformation(ctypes.Structure):
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


class _UnicodeString(ctypes.Structure):
    _fields_ = [
        ("Length", wintypes.USHORT),
        ("MaximumLength", wintypes.USHORT),
        ("Buffer", wintypes.LPWSTR),
    ]


class _ObjectAttributes(ctypes.Structure):
    _fields_ = [
        ("Length", wintypes.ULONG),
        ("RootDirectory", wintypes.HANDLE),
        ("ObjectName", ctypes.POINTER(_UnicodeString)),
        ("Attributes", wintypes.ULONG),
        ("SecurityDescriptor", ctypes.c_void_p),
        ("SecurityQualityOfService", ctypes.c_void_p),
    ]


class _IoStatusBlock(ctypes.Structure):
    _fields_ = [
        ("StatusOrPointer", ctypes.c_void_p),
        ("Information", ctypes.c_size_t),
    ]


class _TrusteeW(ctypes.Structure):
    pass


_TrusteeW._fields_ = [
    ("pMultipleTrustee", ctypes.POINTER(_TrusteeW)),
    ("MultipleTrusteeOperation", wintypes.DWORD),
    ("TrusteeForm", wintypes.DWORD),
    ("TrusteeType", wintypes.DWORD),
    ("ptstrName", wintypes.LPWSTR),
]


class _ExplicitAccessW(ctypes.Structure):
    _fields_ = [
        ("grfAccessPermissions", wintypes.DWORD),
        ("grfAccessMode", wintypes.DWORD),
        ("grfInheritance", wintypes.DWORD),
        ("Trustee", _TrusteeW),
    ]


class WindowsDirectoryIdentity:
    """A stable, non-reparse directory object held without delete sharing."""

    FILE_LIST_DIRECTORY = 0x0001
    FILE_READ_ATTRIBUTES = 0x0080
    READ_CONTROL = 0x00020000
    WRITE_DAC = 0x00040000
    SYNCHRONIZE = 0x00100000
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
    FILE_ATTRIBUTE_NORMAL = 0x00000080
    OBJ_CASE_INSENSITIVE = 0x00000040
    FILE_OPEN = 1
    FILE_CREATE = 2
    FILE_OPEN_IF = 3
    FILE_OPENED = 1
    FILE_CREATED = 2
    FILE_DIRECTORY_FILE = 0x00000001
    FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
    FILE_OPEN_FOR_BACKUP_INTENT = 0x00004000
    FILE_OPEN_REPARSE_POINT_NATIVE = 0x00200000

    def __init__(self, path: Path, *, security_control: bool = False) -> None:
        if os.name != "nt":
            raise LockedPairV6Error("stable_directory_identity_is_windows_only")
        self.path = _lexical_absolute(path)
        self._initialize_api()
        access = self._desired_access(security_control)
        handle = self.kernel32.CreateFileW(
            str(self.path), access, self.FILE_SHARE_READ | self.FILE_SHARE_WRITE,
            None, self.OPEN_EXISTING,
            self.FILE_FLAG_BACKUP_SEMANTICS | self.FILE_FLAG_OPEN_REPARSE_POINT,
            None,
        )
        invalid = ctypes.c_void_p(-1).value
        if handle in (None, invalid):
            raise LockedPairV6Error(
                f"stable_directory_open_failed:{self.path}:"
                f"winerror={ctypes.get_last_error()}"
            )
        self.handle = int(handle)
        try:
            self._bind_observed_identity()
        except BaseException:
            self.close()
            raise

    def _initialize_api(self) -> None:
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
        ]
        self.kernel32.CreateFileW.restype = wintypes.HANDLE
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.kernel32.GetFileInformationByHandle.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(_ByHandleFileInformation),
        ]
        self.kernel32.GetFileInformationByHandle.restype = wintypes.BOOL
        self.kernel32.GetFinalPathNameByHandleW.argtypes = [
            wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
        ]
        self.kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
        self.ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
        self.ntdll.NtCreateFile.argtypes = [
            ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD,
            ctypes.POINTER(_ObjectAttributes), ctypes.POINTER(_IoStatusBlock),
            ctypes.c_void_p, wintypes.ULONG, wintypes.ULONG, wintypes.ULONG,
            wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG,
        ]
        self.ntdll.NtCreateFile.restype = ctypes.c_long
        self.ntdll.RtlNtStatusToDosError.argtypes = [ctypes.c_long]
        self.ntdll.RtlNtStatusToDosError.restype = wintypes.ULONG

    def _desired_access(self, security_control: bool) -> int:
        access = (
            self.FILE_LIST_DIRECTORY | self.FILE_READ_ATTRIBUTES
            | self.READ_CONTROL | self.SYNCHRONIZE
        )
        if security_control:
            access |= self.WRITE_DAC
        return access

    def _bind_observed_identity(self) -> None:
        self.final_path, self.file_id, self.attributes = self._observe()
        if self.attributes & self.FILE_ATTRIBUTE_REPARSE_POINT:
            raise LockedPairV6Error(f"runtime_reparse_handle_refused:{self.path}")
        if _normalized_windows_path(self.final_path) != _normalized_windows_path(
            self.path
        ):
            raise LockedPairV6Error(
                f"runtime_handle_final_path_mismatch:{self.path}:{self.final_path}"
            )

    @classmethod
    def open_child(
        cls, parent: "WindowsDirectoryIdentity", name: str, *,
        create_exclusive: bool, security_control: bool = False,
    ) -> "WindowsDirectoryIdentity":
        if (
            not isinstance(name, str) or not name or name in {".", ".."}
            or "\\" in name or "/" in name or "\x00" in name
        ):
            raise LockedPairV6Error("runtime_child_component_invalid")
        parent.verify()
        instance = cls.__new__(cls)
        instance.path = parent.path / name
        instance._initialize_api()
        name_buffer = ctypes.create_unicode_buffer(name)
        encoded_length = len(name.encode("utf-16-le"))
        unicode_name = _UnicodeString(
            encoded_length, encoded_length + 2,
            ctypes.cast(name_buffer, wintypes.LPWSTR),
        )
        attributes = _ObjectAttributes(
            ctypes.sizeof(_ObjectAttributes), wintypes.HANDLE(parent.handle),
            ctypes.pointer(unicode_name), cls.OBJ_CASE_INSENSITIVE, None, None,
        )
        io_status = _IoStatusBlock()
        raw_handle = wintypes.HANDLE()
        disposition = cls.FILE_CREATE if create_exclusive else cls.FILE_OPEN_IF
        status = int(instance.ntdll.NtCreateFile(
            ctypes.byref(raw_handle), instance._desired_access(security_control),
            ctypes.byref(attributes), ctypes.byref(io_status), None,
            cls.FILE_ATTRIBUTE_NORMAL, cls.FILE_SHARE_READ | cls.FILE_SHARE_WRITE,
            disposition,
            cls.FILE_DIRECTORY_FILE | cls.FILE_SYNCHRONOUS_IO_NONALERT
            | cls.FILE_OPEN_FOR_BACKUP_INTENT | cls.FILE_OPEN_REPARSE_POINT_NATIVE,
            None, 0,
        ))
        if status < 0:
            winerror = int(instance.ntdll.RtlNtStatusToDosError(status))
            code = "runtime_child_scope_preoccupied" if create_exclusive else (
                "runtime_child_open_or_create_failed"
            )
            raise LockedPairV6Error(
                f"{code}:{instance.path}:ntstatus=0x{status & 0xffffffff:08x}:"
                f"winerror={winerror}"
            )
        instance.handle = int(raw_handle.value)
        expected_information = {cls.FILE_CREATED} if create_exclusive else {
            cls.FILE_OPENED, cls.FILE_CREATED,
        }
        try:
            if int(io_status.Information) not in expected_information:
                raise LockedPairV6Error(
                    f"runtime_child_create_disposition_drift:{instance.path}:"
                    f"information={int(io_status.Information)}"
                )
            instance._bind_observed_identity()
            parent.verify()
            observed_parent = _normalized_windows_path(Path(instance.final_path).parent)
            if observed_parent != _normalized_windows_path(parent.final_path):
                raise LockedPairV6Error(
                    f"runtime_native_child_ancestry_mismatch:{parent.path}:"
                    f"{instance.path}"
                )
            return instance
        except BaseException:
            instance.close()
            raise

    def _observe(self) -> tuple[str, tuple[int, int], int]:
        info = _ByHandleFileInformation()
        if not self.kernel32.GetFileInformationByHandle(
            wintypes.HANDLE(self.handle), ctypes.byref(info)
        ):
            raise LockedPairV6Error(
                f"runtime_handle_information_failed:winerror={ctypes.get_last_error()}"
            )
        needed = self.kernel32.GetFinalPathNameByHandleW(
            wintypes.HANDLE(self.handle), None, 0, 0,
        )
        if not needed:
            raise LockedPairV6Error(
                f"runtime_handle_final_path_size_failed:winerror={ctypes.get_last_error()}"
            )
        buffer = ctypes.create_unicode_buffer(int(needed) + 1)
        written = self.kernel32.GetFinalPathNameByHandleW(
            wintypes.HANDLE(self.handle), buffer, len(buffer), 0,
        )
        if not written or written >= len(buffer):
            raise LockedPairV6Error(
                f"runtime_handle_final_path_failed:winerror={ctypes.get_last_error()}"
            )
        file_index = (int(info.nFileIndexHigh) << 32) | int(info.nFileIndexLow)
        return (
            str(buffer.value),
            (int(info.dwVolumeSerialNumber), file_index),
            int(info.dwFileAttributes),
        )

    def verify(self) -> None:
        final_path, file_id, attributes = self._observe()
        if attributes & self.FILE_ATTRIBUTE_REPARSE_POINT:
            raise LockedPairV6Error(f"runtime_handle_became_reparse:{self.path}")
        if file_id != self.file_id:
            raise LockedPairV6Error(f"runtime_directory_file_id_changed:{self.path}")
        if _normalized_windows_path(final_path) != _normalized_windows_path(
            self.final_path
        ):
            raise LockedPairV6Error(f"runtime_directory_final_path_changed:{self.path}")

    def row(self, *, parent_file_id: tuple[int, int] | None) -> dict[str, object]:
        return {
            "lexical_path": str(self.path),
            "handle_final_path": self.final_path,
            "volume_serial": self.file_id[0],
            "file_index": self.file_id[1],
            "parent_volume_serial": None if parent_file_id is None else parent_file_id[0],
            "parent_file_index": None if parent_file_id is None else parent_file_id[1],
            "reparse_point": False,
            "delete_sharing": False,
        }

    def close(self) -> None:
        handle = getattr(self, "handle", 0)
        if handle:
            self.handle = 0
            if not self.kernel32.CloseHandle(wintypes.HANDLE(handle)):
                raise LockedPairV6Error(
                    f"stable_directory_close_failed:winerror={ctypes.get_last_error()}"
                )


class WindowsChangeSentinel:
    """A sticky no-reset notification for any name/write/security mutation."""

    FILE_NOTIFY_CHANGE_FILE_NAME = 0x00000001
    FILE_NOTIFY_CHANGE_DIR_NAME = 0x00000002
    FILE_NOTIFY_CHANGE_ATTRIBUTES = 0x00000004
    FILE_NOTIFY_CHANGE_SIZE = 0x00000008
    FILE_NOTIFY_CHANGE_LAST_WRITE = 0x00000010
    FILE_NOTIFY_CHANGE_CREATION = 0x00000040
    FILE_NOTIFY_CHANGE_SECURITY = 0x00000100
    WAIT_OBJECT_0 = 0
    WAIT_TIMEOUT = 258

    def __init__(self, path: Path) -> None:
        if os.name != "nt":
            raise LockedPairV6Error("change_sentinel_is_windows_only")
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.FindFirstChangeNotificationW.argtypes = [
            wintypes.LPCWSTR, wintypes.BOOL, wintypes.DWORD,
        ]
        self.kernel32.FindFirstChangeNotificationW.restype = wintypes.HANDLE
        self.kernel32.FindCloseChangeNotification.argtypes = [wintypes.HANDLE]
        self.kernel32.FindCloseChangeNotification.restype = wintypes.BOOL
        self.kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel32.WaitForSingleObject.restype = wintypes.DWORD
        change_filter = (
            self.FILE_NOTIFY_CHANGE_FILE_NAME | self.FILE_NOTIFY_CHANGE_DIR_NAME
            | self.FILE_NOTIFY_CHANGE_ATTRIBUTES | self.FILE_NOTIFY_CHANGE_SIZE
            | self.FILE_NOTIFY_CHANGE_LAST_WRITE | self.FILE_NOTIFY_CHANGE_CREATION
            | self.FILE_NOTIFY_CHANGE_SECURITY
        )
        handle = self.kernel32.FindFirstChangeNotificationW(
            str(_lexical_absolute(path)), False, change_filter,
        )
        invalid = ctypes.c_void_p(-1).value
        if handle in (None, invalid):
            raise LockedPairV6Error(
                f"change_sentinel_open_failed:{path}:winerror={ctypes.get_last_error()}"
            )
        self.handle = int(handle)

    def changed(self) -> bool:
        result = int(self.kernel32.WaitForSingleObject(
            wintypes.HANDLE(self.handle), 0,
        ))
        if result == self.WAIT_TIMEOUT:
            return False
        if result == self.WAIT_OBJECT_0:
            return True
        raise LockedPairV6Error(
            f"change_sentinel_wait_failed:result={result}:"
            f"winerror={ctypes.get_last_error()}"
        )

    def verify_unchanged(self, label: str) -> None:
        if self.changed():
            raise LockedPairV6Error(f"runtime_transient_or_persistent_change:{label}")

    def close(self) -> None:
        handle = getattr(self, "handle", 0)
        if handle:
            self.handle = 0
            if not self.kernel32.FindCloseChangeNotification(wintypes.HANDLE(handle)):
                raise LockedPairV6Error(
                    f"change_sentinel_close_failed:winerror={ctypes.get_last_error()}"
                )


class WindowsNoChildMutationBoundary:
    """Deny child creation plus retain a sticky mutation/security sentinel."""

    SE_FILE_OBJECT = 1
    DACL_SECURITY_INFORMATION = 0x00000004
    PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000
    DENY_ACCESS = 3
    TRUSTEE_IS_SID = 0
    TRUSTEE_IS_WELL_KNOWN_GROUP = 5
    WIN_WORLD_SID = 1
    SECURITY_MAX_SID_SIZE = 68
    FILE_ADD_FILE = 0x0002
    FILE_ADD_SUBDIRECTORY = 0x0004
    FILE_DELETE_CHILD = 0x0040
    FILE_WRITE_ATTRIBUTES = 0x0100

    def __init__(
        self, identity: WindowsDirectoryIdentity, label: str,
        *, expected_entries: Sequence[str] = (),
    ) -> None:
        if os.name != "nt":
            raise LockedPairV6Error("no_child_mutation_boundary_is_windows_only")
        self.identity = identity
        self.label = label
        self.expected_entries = frozenset(expected_entries)
        self.advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._configure_signatures()
        self._install_world_deny_child_ace()
        self.dacl_sha256 = self._dacl_sha256()
        self.sentinel = WindowsChangeSentinel(identity.path)
        self.verify()

    def _configure_signatures(self) -> None:
        self.advapi32.GetSecurityInfo.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self.advapi32.GetSecurityInfo.restype = wintypes.DWORD
        self.advapi32.SetSecurityInfo.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
        ]
        self.advapi32.SetSecurityInfo.restype = wintypes.DWORD
        self.advapi32.SetEntriesInAclW.argtypes = [
            wintypes.ULONG, ctypes.POINTER(_ExplicitAccessW), ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self.advapi32.SetEntriesInAclW.restype = wintypes.DWORD
        self.advapi32.CreateWellKnownSid.argtypes = [
            wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.advapi32.CreateWellKnownSid.restype = wintypes.BOOL
        self.advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [
            ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
            ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(wintypes.ULONG),
        ]
        self.advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = wintypes.BOOL
        self.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        self.kernel32.LocalFree.restype = ctypes.c_void_p

    def _security_info(self) -> tuple[ctypes.c_void_p, ctypes.c_void_p]:
        dacl = ctypes.c_void_p()
        descriptor = ctypes.c_void_p()
        result = int(self.advapi32.GetSecurityInfo(
            wintypes.HANDLE(self.identity.handle), self.SE_FILE_OBJECT,
            self.DACL_SECURITY_INFORMATION, None, None,
            ctypes.byref(dacl), None, ctypes.byref(descriptor),
        ))
        if result != 0:
            raise LockedPairV6Error(f"get_runtime_dacl_failed:{self.label}:winerror={result}")
        return dacl, descriptor

    def _install_world_deny_child_ace(self) -> None:
        self._install_world_deny_mask(
            self.FILE_ADD_FILE | self.FILE_ADD_SUBDIRECTORY
            | self.FILE_DELETE_CHILD
        )

    def _install_world_deny_mask(self, access_mask: int) -> None:
        old_dacl, descriptor = self._security_info()
        new_acl = ctypes.c_void_p()
        try:
            sid = ctypes.create_string_buffer(self.SECURITY_MAX_SID_SIZE)
            sid_size = wintypes.DWORD(len(sid))
            if not self.advapi32.CreateWellKnownSid(
                self.WIN_WORLD_SID, None, sid, ctypes.byref(sid_size),
            ):
                raise LockedPairV6Error(
                    f"world_sid_creation_failed:winerror={ctypes.get_last_error()}"
                )
            trustee = _TrusteeW(
                None, 0, self.TRUSTEE_IS_SID, self.TRUSTEE_IS_WELL_KNOWN_GROUP,
                ctypes.cast(sid, wintypes.LPWSTR),
            )
            entry = _ExplicitAccessW(
                access_mask, self.DENY_ACCESS, 0, trustee,
            )
            result = int(self.advapi32.SetEntriesInAclW(
                1, ctypes.byref(entry), old_dacl, ctypes.byref(new_acl),
            ))
            if result != 0:
                raise LockedPairV6Error(
                    f"runtime_deny_acl_build_failed:{self.label}:winerror={result}"
                )
            result = int(self.advapi32.SetSecurityInfo(
                wintypes.HANDLE(self.identity.handle), self.SE_FILE_OBJECT,
                self.DACL_SECURITY_INFORMATION
                | self.PROTECTED_DACL_SECURITY_INFORMATION,
                None, None, new_acl, None,
            ))
            if result != 0:
                raise LockedPairV6Error(
                    f"runtime_deny_acl_install_failed:{self.label}:winerror={result}"
                )
        finally:
            if new_acl.value:
                self.kernel32.LocalFree(new_acl)
            if descriptor.value:
                self.kernel32.LocalFree(descriptor)

    def _dacl_sha256(self) -> str:
        _dacl, descriptor = self._security_info()
        text = wintypes.LPWSTR()
        try:
            if not self.advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW(
                descriptor, 1, self.DACL_SECURITY_INFORMATION,
                ctypes.byref(text), None,
            ):
                raise LockedPairV6Error(
                    f"runtime_dacl_string_failed:{self.label}:"
                    f"winerror={ctypes.get_last_error()}"
                )
            return _sha256_bytes(str(text.value).encode("utf-8"))
        finally:
            if text:
                self.kernel32.LocalFree(ctypes.cast(text, ctypes.c_void_p))
            if descriptor.value:
                self.kernel32.LocalFree(descriptor)

    def verify(self) -> None:
        self.identity.verify()
        if self._dacl_sha256() != self.dacl_sha256:
            raise LockedPairV6Error(f"runtime_dacl_changed:{self.label}")
        observed = {entry.name for entry in self.identity.path.iterdir()}
        if observed != self.expected_entries:
            raise LockedPairV6Error(
                f"protected_runtime_directory_content_drift:{self.label}"
            )
        if hasattr(self, "sentinel"):
            self.sentinel.verify_unchanged(self.label)

    def close(self) -> None:
        self.sentinel.close()


class SecureRuntimeTree:
    """Fresh two-run tree with stable handle-derived ancestry through cleanup."""

    DIRECTORY_NAMES = ("temp", "user_config", "user_scripts", "user_datafiles")
    PROTECTED_NAMES = ("user_config", "user_scripts", "user_datafiles")

    def __init__(
        self, *, project_root: Path, base_relative_path: str,
        pair_session_nonce: str, run_nonces: Mapping[int, str],
    ) -> None:
        _require_hex(pair_session_nonce, "pair_session_nonce")
        if set(run_nonces) != {1, 2}:
            raise LockedPairV6Error("runtime_run_nonce_set_invalid")
        normalized_run_nonces = {
            number: _require_hex(run_nonces[number], f"run_{number:02d}_nonce")
            for number in (1, 2)
        }
        if len({pair_session_nonce, *normalized_run_nonces.values()}) != 3:
            raise LockedPairV6Error("runtime_nonce_identity_collision")
        if os.name != "nt":
            raise LockedPairV6Error("secure_runtime_tree_is_windows_only")
        relative = Path(base_relative_path)
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise LockedPairV6Error("runtime_base_relative_path_invalid")
        self.identities: list[WindowsDirectoryIdentity] = []
        self.boundaries: list[WindowsNoChildMutationBoundary] = []
        self.structure_sentinels: list[tuple[str, WindowsChangeSentinel]] = []
        self.runs: dict[int, dict[str, WindowsDirectoryIdentity]] = {}
        self.run_nonces = normalized_run_nonces
        self.launched: set[int] = set()
        self.project_root = _lexical_absolute(project_root)
        try:
            project_identity = self._open_identity(self.project_root)
            parent = project_identity
            current = self.project_root
            for part in relative.parts:
                current = current / part
                child = self._register_identity(
                    WindowsDirectoryIdentity.open_child(
                        parent, part, create_exclusive=False,
                    )
                )
                self._require_direct_child(parent, child)
                parent = child
            self.base = parent
            pair_token = _sha256_bytes(pair_session_nonce.encode("ascii"))[:32]
            self.pair_path = current / f"pair_{pair_token}"
            try:
                self.pair = self._register_identity(
                    WindowsDirectoryIdentity.open_child(
                        self.base, self.pair_path.name, create_exclusive=True,
                        security_control=True,
                    )
                )
            except LockedPairV6Error as exc:
                raise LockedPairV6Error("runtime_pair_scope_preoccupied") from exc
            self._require_direct_child(self.base, self.pair)
            for run_number in (1, 2):
                run_token = _sha256_bytes(
                    f"{pair_session_nonce}:{run_number}:"
                    f"{self.run_nonces[run_number]}".encode("ascii")
                )[:32]
                run_path = self.pair_path / f"run_{run_number:02d}_{run_token}"
                run_identity = self._register_identity(
                    WindowsDirectoryIdentity.open_child(
                        self.pair, run_path.name, create_exclusive=True,
                        security_control=True,
                    )
                )
                self._require_direct_child(self.pair, run_identity)
                table: dict[str, WindowsDirectoryIdentity] = {"root": run_identity}
                for name in self.DIRECTORY_NAMES:
                    path = run_path / name
                    identity = self._register_identity(
                        WindowsDirectoryIdentity.open_child(
                            run_identity, name, create_exclusive=True,
                            security_control=name in self.PROTECTED_NAMES,
                        )
                    )
                    self._require_direct_child(run_identity, identity)
                    table[name] = identity
                self.runs[run_number] = table
            self._install_fixed_content_boundaries()
            self.manifest_sha256 = _sha256_bytes(
                _canonical_json_bytes(self.identity_manifest())
            )
            self.verify_before_any_child()
        except BaseException:
            self.close(suppress_errors=True)
            raise

    @classmethod
    def create(
        cls, *, pair_session_nonce: str, project_root: Path = PROJECT_ROOT,
        base_relative_path: str = RUNTIME_BASE_RELATIVE_PATH,
        run_nonces: Mapping[int, str],
    ) -> "SecureRuntimeTree":
        return cls(
            project_root=project_root, base_relative_path=base_relative_path,
            pair_session_nonce=pair_session_nonce, run_nonces=run_nonces,
        )

    def _open_identity(
        self, path: Path, *, security_control: bool = False,
    ) -> WindowsDirectoryIdentity:
        return self._register_identity(
            WindowsDirectoryIdentity(path, security_control=security_control)
        )

    def _register_identity(
        self, identity: WindowsDirectoryIdentity,
    ) -> WindowsDirectoryIdentity:
        if any(existing.file_id == identity.file_id for existing in self.identities):
            identity.close()
            raise LockedPairV6Error(
                f"runtime_duplicate_directory_file_id:{identity.path}"
            )
        self.identities.append(identity)
        return identity

    @staticmethod
    def _require_direct_child(
        parent: WindowsDirectoryIdentity, child: WindowsDirectoryIdentity,
    ) -> None:
        parent.verify()
        child.verify()
        expected_parent = _normalized_windows_path(parent.final_path)
        observed_parent = _normalized_windows_path(Path(child.final_path).parent)
        if observed_parent != expected_parent:
            raise LockedPairV6Error(
                f"runtime_handle_ancestry_mismatch:{parent.path}:{child.path}"
            )

    def _install_fixed_content_boundaries(self) -> None:
        fixed: list[tuple[str, WindowsDirectoryIdentity, tuple[str, ...]]] = []
        for run_number, table in self.runs.items():
            fixed.append((
                f"run_{run_number:02d}_root", table["root"],
                tuple(self.DIRECTORY_NAMES),
            ))
            for name in self.PROTECTED_NAMES:
                label = f"run_{run_number:02d}_{name}"
                self.boundaries.append(
                    WindowsNoChildMutationBoundary(table[name], label)
                )
        fixed.append((
            "pair_root", self.pair,
            tuple(self.runs[number]["root"].path.name for number in (1, 2)),
        ))
        for label, identity, expected_entries in fixed:
            boundary = WindowsNoChildMutationBoundary(
                identity, label, expected_entries=expected_entries,
            )
            self.boundaries.append(boundary)

    def identity_manifest(self) -> list[dict[str, object]]:
        parent_by_path: dict[str, tuple[int, int] | None] = {
            _normalized_windows_path(self.project_root): None,
        }
        for identity in self.identities[1:]:
            parent_path = _normalized_windows_path(Path(identity.final_path).parent)
            parent = next(
                (row for row in self.identities if _normalized_windows_path(
                    row.final_path
                ) == parent_path),
                None,
            )
            if parent is None:
                raise LockedPairV6Error(f"runtime_manifest_parent_missing:{identity.path}")
            parent_by_path[_normalized_windows_path(identity.final_path)] = parent.file_id
        return [
            identity.row(
                parent_file_id=parent_by_path[_normalized_windows_path(identity.final_path)]
            )
            for identity in self.identities
        ]

    def _verify_structure(self) -> None:
        expected_pair = {
            self.runs[1]["root"].path.name,
            self.runs[2]["root"].path.name,
        }
        if {entry.name for entry in self.pair.path.iterdir()} != expected_pair:
            raise LockedPairV6Error("runtime_pair_content_drifted")
        for run_number, table in self.runs.items():
            if {entry.name for entry in table["root"].path.iterdir()} != set(
                self.DIRECTORY_NAMES
            ):
                raise LockedPairV6Error(
                    f"runtime_run_{run_number:02d}_content_drifted"
                )

    def verify_all_identities(self) -> None:
        for identity in self.identities:
            identity.verify()
        manifest = self.identity_manifest()
        if hasattr(self, "manifest_sha256") and _sha256_bytes(
            _canonical_json_bytes(manifest)
        ) != self.manifest_sha256:
            raise LockedPairV6Error("runtime_identity_manifest_drifted")

    def verify_fixed_boundaries(self) -> None:
        for boundary in self.boundaries:
            boundary.verify()

    def verify_before_any_child(self) -> None:
        self.verify_all_identities()
        self._verify_structure()
        self.verify_fixed_boundaries()
        for table in self.runs.values():
            if any(
                any(table[name].path.iterdir()) for name in self.DIRECTORY_NAMES
            ):
                raise LockedPairV6Error("fresh_runtime_leaf_not_empty")

    def prepare_environment(
        self, *, blender: Path, run_number: int, run_nonce: str,
        pair_session_nonce: str,
    ) -> dict[str, str]:
        _require_hex(run_nonce, "run_nonce")
        if run_number not in (1, 2) or run_number in self.launched:
            raise LockedPairV6Error("runtime_run_reuse_or_identity_invalid")
        if run_nonce != self.run_nonces[run_number]:
            raise LockedPairV6Error("runtime_run_nonce_identity_mismatch")
        self.verify_all_identities()
        self._verify_structure()
        self.verify_fixed_boundaries()
        table = self.runs[run_number]
        if any(
            any(table[name].path.iterdir()) for name in self.DIRECTORY_NAMES
        ):
            raise LockedPairV6Error(f"runtime_run_{run_number:02d}_not_pristine")
        self.launched.add(run_number)
        environment = {
            name: os.environ[name]
            for name in PASSTHROUGH_IF_PRESENT if os.environ.get(name)
        }
        windir = environment.get("WINDIR") or environment.get("SYSTEMROOT")
        if not windir:
            raise LockedPairV6Error("windows_root_environment_missing")
        environment["Path"] = os.pathsep.join(
            (str(blender.parent), str(Path(windir) / "System32"), str(Path(windir)))
        )
        environment.update(FORCED_ENVIRONMENT)
        environment.update({
            "TEMP": str(table["temp"].path),
            "TMP": str(table["temp"].path),
            "BLENDER_USER_CONFIG": str(table["user_config"].path),
            "BLENDER_USER_SCRIPTS": str(table["user_scripts"].path),
            "BLENDER_USER_DATAFILES": str(table["user_datafiles"].path),
            "KIRA_RUNTIME_SCOPE_SHA256": _sha256_bytes(
                _canonical_json_bytes({
                    "pair_session_nonce": pair_session_nonce,
                    "run_nonce": run_nonce,
                    "run_number": run_number,
                    "identity_manifest_sha256": self.manifest_sha256,
                })
            ),
        })
        return environment

    def verify_after_child(self, run_number: int) -> None:
        if run_number not in self.launched:
            raise LockedPairV6Error("runtime_after_unlaunched_run")
        self.verify_all_identities()
        self._verify_structure()
        self.verify_fixed_boundaries()

    def close(self, *, suppress_errors: bool = False) -> None:
        first: BaseException | None = None
        for boundary in reversed(getattr(self, "boundaries", [])):
            try:
                boundary.close()
            except BaseException as exc:
                if first is None:
                    first = exc
        self.boundaries = []
        for label, sentinel in reversed(getattr(self, "structure_sentinels", [])):
            try:
                sentinel.close()
            except BaseException as exc:
                if first is None:
                    first = exc
        self.structure_sentinels = []
        for identity in reversed(getattr(self, "identities", [])):
            try:
                identity.close()
            except BaseException as exc:
                if first is None:
                    first = exc
        self.identities = []
        if first is not None and not suppress_errors:
            raise first


_ACTIVE_RUNTIME_TREE: SecureRuntimeTree | None = None
_RUNTIME_SCOPE: tuple[str, str, int] | None = None


def _restricted_environment(blender: Path) -> dict[str, str]:
    if _ACTIVE_RUNTIME_TREE is None or _RUNTIME_SCOPE is None:
        raise LockedPairV6Error("secure_runtime_scope_absent")
    pair_nonce, run_nonce, run_number = _RUNTIME_SCOPE
    return _ACTIVE_RUNTIME_TREE.prepare_environment(
        blender=blender, run_number=run_number, run_nonce=run_nonce,
        pair_session_nonce=pair_nonce,
    )


def _load_private_source(
    *, row: object, ledger: Any, label: str, module_prefix: str,
) -> ModuleType:
    path, source = ledger.read_exact(row, label=label)
    real_import = builtins.__import__

    def guarded_import(
        name: str, globals: object = None, locals: object = None,
        fromlist: Sequence[str] = (), level: int = 0,
    ) -> object:
        if name == "tools" or name.startswith("tools."):
            raise LockedPairV6Error(f"ambient_project_import_forbidden:{name}")
        return real_import(name, globals, locals, fromlist, level)

    private = ModuleType(f"{module_prefix}_{secrets.token_hex(16)}")
    private.__file__ = str(path)
    private.__package__ = ""
    private.__spec__ = None
    private.__loader__ = None
    private_builtins = dict(vars(builtins))
    private_builtins["__import__"] = guarded_import
    private.__dict__["__builtins__"] = private_builtins
    exec(compile(source, str(path), "exec", dont_inherit=True), private.__dict__, private.__dict__)
    if any(private is module for module in sys.modules.values()):
        raise LockedPairV6Error(f"private_source_entered_sys_modules:{label}")
    return private


def _run_child_with_secure_tree(
    core: ModuleType, *, pair_session_nonce: str, run_nonce: str,
    run_number: int, **kwargs: Any,
) -> tuple[Any, dict[str, Any]]:
    global _RUNTIME_SCOPE
    if _ACTIVE_RUNTIME_TREE is None or _RUNTIME_SCOPE is not None:
        raise LockedPairV6Error("secure_runtime_scope_reentry_refused")
    _RUNTIME_SCOPE = (pair_session_nonce, run_nonce, run_number)
    try:
        return core._run_child(
            pair_session_nonce=pair_session_nonce, run_nonce=run_nonce,
            run_number=run_number, **kwargs,
        )
    finally:
        try:
            _ACTIVE_RUNTIME_TREE.verify_all_identities()
            _ACTIVE_RUNTIME_TREE._verify_structure()
            _ACTIVE_RUNTIME_TREE.verify_fixed_boundaries()
        finally:
            _RUNTIME_SCOPE = None


def _authorized_pair(
    *, bootstrap_context: Any, expected_contract_sha256: str,
    accepted_audit_sha256: str,
) -> Path:
    global _ACTIVE_RUNTIME_TREE
    if not getattr(bootstrap_context, "locks_active", False):
        raise LockedPairV6Error("external_bootstrap_locks_not_active")
    if getattr(bootstrap_context, "controller_private_execution", None) is not True:
        raise LockedPairV6Error("controller_not_private_retained_byte_execution")
    if bootstrap_context.expected_contract_sha256 != expected_contract_sha256:
        raise LockedPairV6Error("bootstrap_contract_digest_mismatch")
    if bootstrap_context.accepted_audit_sha256 != accepted_audit_sha256:
        raise LockedPairV6Error("bootstrap_audit_digest_mismatch")
    _require_hex(expected_contract_sha256, "expected_contract_sha256")
    _require_hex(accepted_audit_sha256, "accepted_audit_sha256")
    contract = bootstrap_context.contract
    if contract.get("schema") != "kira.avatar.r25.foundation_afes_locked_pair_execution.v6":
        raise LockedPairV6Error("bootstrap_contract_schema_mismatch")
    ledger = bootstrap_context.ledger
    contract_bytes = ledger.read_path(bootstrap_context.contract_path)
    if _sha256_bytes(contract_bytes) != expected_contract_sha256:
        raise LockedPairV6Error("retained_contract_digest_mismatch")

    v5_core = _load_private_source(
        row=contract["execution_sources"]["attempt05_controller_core"],
        ledger=ledger, label="attempt05_controller_core",
        module_prefix="_kira_private_attempt05_controller_core",
    )
    core = v5_core._load_attempt04_core(contract, ledger)
    v5_core._LEGACY_VALIDATOR = core._validate_exact_child_payload

    def validate_v6_payload(**kwargs: Any) -> tuple[Mapping[str, Any], str]:
        payload = kwargs.get("payload")
        if not isinstance(payload, Mapping) or payload.get("schema") != (
            "kira.avatar.r25.foundation_afes_locked_extraction_run.v6"
        ):
            raise LockedPairV6Error("outer_v6_schema_mismatch")
        translated = dict(payload)
        translated["schema"] = "kira.avatar.r25.foundation_afes_locked_extraction_run.v5"
        translated_kwargs = dict(kwargs)
        translated_kwargs["payload"] = translated
        return v5_core._validate_exact_child_payload(**translated_kwargs)

    core.CONTRACT_RELATIVE_PATH = CONTRACT_RELATIVE_PATH
    core.OUTPUT_RELATIVE_PATH = OUTPUT_RELATIVE_PATH
    core.OUTER_TRUTH_BOUNDARY = list(OUTER_TRUTH_BOUNDARY)
    core._restricted_environment = _restricted_environment
    core._validate_exact_child_payload = validate_v6_payload
    execution_contract = dict(contract)
    execution_contract["child_project_read_closure"] = bootstrap_context.inherited_attempt04_contract[
        "child_project_read_closure"
    ]
    pair_session_nonce = secrets.token_hex(32)
    receipt, attempt03, afes_v5 = core._load_private_parent_graph(
        execution_contract, ledger, pair_session_nonce,
    )
    v2 = core._load_v2_config(afes_v5, ledger)
    before = bootstrap_context.before_snapshot
    if before != bootstrap_context.snapshot_locked_files():
        raise LockedPairV6Error("locked_graph_changed_before_pair")
    output_root = (PROJECT_ROOT / OUTPUT_RELATIVE_PATH).resolve()
    output_root.relative_to(PROJECT_ROOT.resolve(strict=True))
    output_root.parent.mkdir(parents=True, exist_ok=True)
    outcome = core._reserve_outcome(output_root, receipt)
    stage = "post_outcome_reservation"
    try:
        run_nonces = [secrets.token_hex(32), secrets.token_hex(32)]
        if len({pair_session_nonce, *run_nonces}) != 3:
            raise LockedPairV6Error("fresh_nonce_collision")
        _ACTIVE_RUNTIME_TREE = SecureRuntimeTree.create(
            pair_session_nonce=pair_session_nonce,
            run_nonces={1: run_nonces[0], 2: run_nonces[1]},
        )
        decoded_runs: list[Any] = []
        run_metadata: list[dict[str, Any]] = []
        stage = "children"
        for run_number, run_nonce in enumerate(run_nonces, 1):
            decoded, metadata = _run_child_with_secure_tree(
                core, contract=execution_contract, v5=afes_v5, v2=v2,
                ledger=ledger, receipt=receipt, attempt03=attempt03,
                contract_sha256=expected_contract_sha256,
                contract_bytes=len(contract_bytes), run_number=run_number,
                pair_session_nonce=pair_session_nonce, run_nonce=run_nonce,
                evidence_root=output_root,
            )
            decoded_runs.append(decoded)
            run_metadata.append(metadata)
        stage = "pair_comparison"
        first_inner = decoded_runs[0].payload["inner_attempt05_payload"]
        second_inner = decoded_runs[1].payload["inner_attempt05_payload"]
        if first_inner != second_inner:
            raise LockedPairV6Error("fresh_locked_inner_payloads_do_not_match")
        if run_metadata[0]["inner_payload_sha256"] != run_metadata[1]["inner_payload_sha256"]:
            raise LockedPairV6Error("fresh_locked_inner_digests_do_not_match")
        if run_metadata[0]["topology_sha256"] != run_metadata[1]["topology_sha256"]:
            raise LockedPairV6Error("fresh_locked_topology_digests_do_not_match")
        _ACTIVE_RUNTIME_TREE.verify_all_identities()
        _ACTIVE_RUNTIME_TREE.verify_fixed_boundaries()
        stage = "locked_after_snapshot"
        after = core._snapshot_under_locks(bootstrap_context)
        if before != after:
            raise LockedPairV6Error("locked_input_changed_during_pair")
        stage = "runtime_identity_cleanup"
        runtime_manifest_sha256 = _ACTIVE_RUNTIME_TREE.manifest_sha256
        _ACTIVE_RUNTIME_TREE.verify_all_identities()
        _ACTIVE_RUNTIME_TREE.verify_fixed_boundaries()
        _ACTIVE_RUNTIME_TREE.close()
        _ACTIVE_RUNTIME_TREE = None
        summary = {
            "schema": "kira.avatar.r25.foundation_afes_locked_pair_acceptance.v6",
            "status": "AFES_AND_TRANSITION_RINGS_EXTRACTED_READ_ONLY_PAIR_MATCHED",
            "execution_contract_sha256": expected_contract_sha256,
            "accepted_independent_audit_sha256": accepted_audit_sha256,
            "pair_session_nonce": pair_session_nonce,
            "execution_contract_bytes": len(contract_bytes),
            "bound_inputs_unchanged_under_locks": True,
            "input_snapshot_sha256": _sha256_bytes(_canonical_json_bytes(before)),
            "runtime_identity_manifest_sha256": runtime_manifest_sha256,
            "runs": run_metadata,
            "matching_inner_payload_sha256": run_metadata[0]["inner_payload_sha256"],
            "full_normalized_topology_sha256": run_metadata[0]["topology_sha256"],
            "truth_boundary": [
                "READ_ONLY_DIAGNOSTIC_PAIR_ONLY",
                "NO_BLEND_MUTATION_OR_SAVE",
                "NO_RENDER_EXPORT_OR_PATH_RESULT",
                "NO_BODY_CANDIDATE",
                "NO_AUTHORING_OR_RUNTIME_AUTHORITY",
            ],
        }
        outcome.accept_child_frame(receipt.encode_receipt_frame(summary))
        outcome.close()
        return output_root
    except BaseException as exc:
        runtime_cleanup_failure: str | None = None
        tree = _ACTIVE_RUNTIME_TREE
        _ACTIVE_RUNTIME_TREE = None
        if tree is not None:
            try:
                tree.verify_all_identities()
                tree.verify_fixed_boundaries()
                tree.close()
            except BaseException as cleanup_exc:
                runtime_cleanup_failure = (
                    f"{type(cleanup_exc).__name__}:{cleanup_exc}"
                )
                tree.close(suppress_errors=True)
        failure = {
            "schema": "kira.avatar.r25.foundation_afes_locked_pair_failure.v6",
            "status": "FAILED_APPEND_ONLY_NO_BODY_AUTHORITY",
            "stage": stage,
            "failure_type": type(exc).__name__,
            "failure": str(exc),
            "execution_contract_sha256": expected_contract_sha256,
            "accepted_independent_audit_sha256": accepted_audit_sha256,
            "pair_session_nonce": pair_session_nonce,
            "runtime_cleanup_failure": runtime_cleanup_failure,
            "receipt_truth": (
                "post_reservation_failure_receipt_attempted; abrupt process termination "
                "or storage failure can still prevent completion"
            ),
        }
        try:
            outcome.accept_child_frame(receipt.encode_receipt_frame(failure))
        finally:
            outcome.close()
        raise
    finally:
        v5_core._LEGACY_VALIDATOR = None
        tree = _ACTIVE_RUNTIME_TREE
        _ACTIVE_RUNTIME_TREE = None
        if tree is not None:
            tree.close(suppress_errors=True)


def _make_capability_entry(injection: object, authorized_pair: Any):
    if (
        isinstance(injection, tuple) and len(injection) == 2
        and injection[0] is not None and injection[1] is not None
    ):
        expected_capability, expected_context = injection
    else:
        expected_capability = expected_context = None
    consumed = False

    def run_locked_pair(
        *, bootstrap_context: Any, bootstrap_capability: object,
        expected_contract_sha256: str, accepted_audit_sha256: str,
    ) -> Path:
        nonlocal consumed
        if expected_capability is None or expected_context is None:
            raise LockedPairV6Error("ambient_import_has_no_bootstrap_capability")
        if bootstrap_capability is not expected_capability:
            raise LockedPairV6Error("bootstrap_capability_identity_mismatch")
        if bootstrap_context is not expected_context:
            raise LockedPairV6Error("bootstrap_context_identity_mismatch")
        if consumed:
            raise LockedPairV6Error("bootstrap_capability_already_consumed")
        consumed = True
        return authorized_pair(
            bootstrap_context=bootstrap_context,
            expected_contract_sha256=expected_contract_sha256,
            accepted_audit_sha256=accepted_audit_sha256,
        )

    return run_locked_pair


_CAPABILITY_INJECTION = globals().pop("_KIRA_BOOTSTRAP_INJECTION", None)
run_locked_pair = _make_capability_entry(_CAPABILITY_INJECTION, _authorized_pair)
del _CAPABILITY_INJECTION
del _authorized_pair
del _make_capability_entry


def main() -> int:
    print(
        "R25_AFES_LOCKED_PAIR_V6_DIRECT_EXECUTION_REFUSED_USE_EXTERNAL_LAUNCHER",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
