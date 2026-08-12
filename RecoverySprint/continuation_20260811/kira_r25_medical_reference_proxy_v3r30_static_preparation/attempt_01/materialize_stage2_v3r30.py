"""Deterministic V3r30 Stage-2 source materializer; never invokes Blender or a compiler.

This program is not execution authority.  It accepts only a fixed installed
Stage-1, Audit-A, and separate ProgramData-install-authority paths, verifies
caller-supplied external anchors, then consumes the exact future ProgramData
ledger authority and writes a new scratch-only Stage-2 source directory. Audit B must inspect
and externally pin the resulting native executable before any launch.
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


KIRA_ROOT = Path(r"C:\Users\robmc\Kira")
CODEX_SCRATCH_ROOT = Path(r"C:\Users\robmc\Documents\Codex")
PROGRAM_DATA_ANCHOR = Path(r"C:\ProgramData")
EXPECTED_MATERIALIZATION_DIR = Path(r"C:\Users\robmc\Documents\Codex\2026-08-11\c\work\body_v3r30_stage2_materialized_attempt_01")
MATERIALIZATION_LEDGER_ROOT = PROGRAM_DATA_ANCHOR / "KiraV3r30AuthorityLedger"
EXPECTED_STAGE1_DIR = KIRA_ROOT / r"RecoverySprint\continuation_20260811\kira_r25_medical_reference_proxy_v3r30_static_preparation\attempt_01"
EXPECTED_AUDIT_A_DIR = KIRA_ROOT / r"RecoverySprint\continuation_20260811\kira_r25_medical_reference_proxy_v3r30_fresh_static_audit\attempt_01"
EXPECTED_INSTALL_AUTHORITY_DIR = KIRA_ROOT / r"RecoverySprint\continuation_20260811\kira_r25_medical_reference_proxy_v3r30_programdata_install_authority\attempt_01"
INSTALLED_STAGE2_ROOT = KIRA_ROOT / r"RecoverySprint\continuation_20260811\kira_r25_medical_reference_proxy_v3r30_stage2\attempt_01"
INSTALLED_ANCHOR_PATH = KIRA_ROOT / r"tools\native\kira_v3r30_stage2_anchor.exe"
BLENDER_PATH = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
BLENDER_BYTES = 108687824
BLENDER_SHA256 = "1e6624af112b3c936f4b038b025ebd2bf00ae72c4b62881a6787166d71c58fa5"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
AUDITOR = re.compile(r"independent_[a-z0-9_]{8,96}\Z")
AUDIT_ROW_IDS = (
    "01_stage1_subject_root",
    "02_stage1_seal_external_sha",
    "03_stage1_all_files_external_root",
    "04_upstream_v3r29_and_rejection",
    "05_static_only",
    "06_two_stage_authority",
    "07_blender_identity",
    "08_materialized_native_analyzer",
    "09_exact_audit_json_types",
    "10_durable_materialization_consumption",
    "11_native_pre_reserved_outputs",
    "12_handles_through_terminal_success",
    "13_worker_factory_isolation",
    "14_frame_landmarks",
    "15_proxy_truth",
    "16_hostile_geometry",
    "17_license_quarantine",
    "18_claim_boundary",
)

INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_LIST_DIRECTORY = 0x0001
FILE_ADD_FILE = 0x0002
FILE_ADD_SUBDIRECTORY = 0x0004
FILE_DELETE_CHILD = 0x0040
FILE_READ_ATTRIBUTES = 0x0080
READ_CONTROL = 0x00020000
WRITE_DAC = 0x00040000
SYNCHRONIZE = 0x00100000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
OPEN_EXISTING = 3
CREATE_NEW = 1
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_ATTRIBUTE_DIRECTORY = 0x00000010
FILE_ATTRIBUTE_DEVICE = 0x00000040
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_NAME_NORMALIZED = 0x0
VOLUME_NAME_DOS = 0x0
FILE_BEGIN = 0
FILE_STANDARD_INFO_CLASS = 1
FILE_ATTRIBUTE_TAG_INFO_CLASS = 9
FILE_ID_INFO_CLASS = 18
FILE_OPENED = 1
FILE_CREATED = 2
FILE_OPEN = 1
FILE_CREATE = 2
FILE_DIRECTORY_FILE = 0x00000001
FILE_WRITE_THROUGH_OPTION = 0x00000002
FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
FILE_NON_DIRECTORY_FILE = 0x00000040
FILE_OPEN_REPARSE_POINT_OPTION = 0x00200000
OBJ_CASE_INSENSITIVE = 0x00000040
OBJ_DONT_REPARSE = 0x00001000
STATUS_OBJECT_NAME_COLLISION = 0xC0000035
ERROR_ACCESS_DENIED = 5
SE_FILE_OBJECT = 1
DACL_SECURITY_INFORMATION = 0x00000004
SDDL_REVISION_1 = 1
LEDGER_FILE_SEALED_SDDL = "D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;GR;;;OW)"
LEDGER_DIRECTORY_APPEND_ONLY_SDDL = "D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;0x1200ab;;;OW)"
LEDGER_FILE_SEALED_CANONICAL_SDDL = "D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FR;;;OW)"
LEDGER_DIRECTORY_APPEND_ONLY_CANONICAL_SDDL = "D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;0x1200ab;;;OW)"
EXPECTED_PROGRAM_DATA_SDDL = "D:PAI(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICIIO;GA;;;CO)(A;OICI;0x1200a9;;;BU)(A;CI;DCLCRPCR;;;BU)"


class FILE_ID_128(ctypes.Structure):
    _fields_ = [("identifier", ctypes.c_ubyte * 16)]


class FILE_ID_INFO(ctypes.Structure):
    _fields_ = [("volume_serial_number", ctypes.c_ulonglong), ("file_id", FILE_ID_128)]


class FILE_ATTRIBUTE_TAG_INFO(ctypes.Structure):
    _fields_ = [("file_attributes", wintypes.DWORD), ("reparse_tag", wintypes.DWORD)]


class FILE_STANDARD_INFO(ctypes.Structure):
    _fields_ = [
        ("allocation_size", ctypes.c_longlong),
        ("end_of_file", ctypes.c_longlong),
        ("number_of_links", wintypes.DWORD),
        ("delete_pending", wintypes.BOOLEAN),
        ("directory", wintypes.BOOLEAN),
    ]


class UNICODE_STRING(ctypes.Structure):
    _fields_ = [
        ("length", wintypes.USHORT),
        ("maximum_length", wintypes.USHORT),
        ("buffer", wintypes.LPWSTR),
    ]


class OBJECT_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("length", wintypes.ULONG),
        ("root_directory", wintypes.HANDLE),
        ("object_name", ctypes.POINTER(UNICODE_STRING)),
        ("attributes", wintypes.ULONG),
        ("security_descriptor", ctypes.c_void_p),
        ("security_quality_of_service", ctypes.c_void_p),
    ]


class IO_STATUS_VALUE(ctypes.Union):
    _fields_ = [("status", ctypes.c_long), ("pointer", ctypes.c_void_p)]


class IO_STATUS_BLOCK(ctypes.Structure):
    _fields_ = [("value", IO_STATUS_VALUE), ("information", ctypes.c_size_t)]


KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
ADVAPI32 = ctypes.WinDLL("advapi32", use_last_error=True)
NTDLL = ctypes.WinDLL("ntdll", use_last_error=True)

KERNEL32.CreateFileW.argtypes = (
    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
    wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
)
KERNEL32.CreateFileW.restype = wintypes.HANDLE
KERNEL32.GetFileInformationByHandleEx.argtypes = (
    wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
)
KERNEL32.GetFileInformationByHandleEx.restype = wintypes.BOOL
KERNEL32.GetFinalPathNameByHandleW.argtypes = (
    wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
)
KERNEL32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
KERNEL32.WriteFile.argtypes = (
    wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p,
)
KERNEL32.WriteFile.restype = wintypes.BOOL
KERNEL32.ReadFile.argtypes = (
    wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p,
)
KERNEL32.ReadFile.restype = wintypes.BOOL
KERNEL32.FlushFileBuffers.argtypes = (wintypes.HANDLE,)
KERNEL32.FlushFileBuffers.restype = wintypes.BOOL
KERNEL32.SetFilePointerEx.argtypes = (
    wintypes.HANDLE, ctypes.c_longlong, ctypes.POINTER(ctypes.c_longlong), wintypes.DWORD,
)
KERNEL32.SetFilePointerEx.restype = wintypes.BOOL
KERNEL32.CloseHandle.argtypes = (wintypes.HANDLE,)
KERNEL32.CloseHandle.restype = wintypes.BOOL
KERNEL32.LocalFree.argtypes = (ctypes.c_void_p,)
KERNEL32.LocalFree.restype = ctypes.c_void_p
ADVAPI32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = (
    wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p),
    ctypes.POINTER(wintypes.DWORD),
)
ADVAPI32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
ADVAPI32.GetSecurityInfo.argtypes = (
    wintypes.HANDLE, ctypes.c_int, wintypes.DWORD,
    ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
    ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
    ctypes.POINTER(ctypes.c_void_p),
)
ADVAPI32.GetSecurityInfo.restype = wintypes.DWORD
ADVAPI32.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = (
    ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
    ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.ULONG),
)
ADVAPI32.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = wintypes.BOOL
NTDLL.NtCreateFile.argtypes = (
    ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD,
    ctypes.POINTER(OBJECT_ATTRIBUTES), ctypes.POINTER(IO_STATUS_BLOCK),
    ctypes.POINTER(ctypes.c_longlong), wintypes.ULONG, wintypes.ULONG,
    wintypes.ULONG, wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG,
)
NTDLL.NtCreateFile.restype = ctypes.c_long
COPY_TO_STAGE2 = (
    "CONTRACT.json",
    "NORMALIZED_REFERENCE_FRAME.json",
    "PROXY_SPEC.json",
    "STAGE2_NATIVE_BUILD_PLAN.json",
    "STAGE2_PROTOCOL.md",
    "blender_worker_v3r30.py",
    "post_audit_native_anchor_template_v3r30.c",
)


class Refuse(RuntimeError):
    pass


class NtRefuse(Refuse):
    def __init__(self, label: str, status: int) -> None:
        self.ntstatus = status & 0xFFFFFFFF
        super().__init__(f"{label}:ntstatus_0x{self.ntstatus:08x}")


def win_error(label: str) -> Refuse:
    return Refuse(f"{label}:win32_{ctypes.get_last_error()}")


def close_handle(handle: int | None) -> None:
    if handle not in (None, 0, INVALID_HANDLE_VALUE):
        KERNEL32.CloseHandle(wintypes.HANDLE(handle))


def nt_create_relative(
    parent_handle: int, name: str, desired_access: int, share_access: int,
    disposition: int, options: int, *, sddl: str | None,
    label: str,
) -> tuple[int, int]:
    if (not name or name in (".", "..") or "\\" in name or "/" in name
            or ":" in name or "\0" in name):
        raise Refuse(label + ":single_component")
    name_buffer = ctypes.create_unicode_buffer(name)
    name_bytes = len(name.encode("utf-16-le"))
    if name_bytes > 0xFFFC:
        raise Refuse(label + ":name_length")
    unicode_name = UNICODE_STRING(
        name_bytes, name_bytes + ctypes.sizeof(ctypes.c_wchar),
        ctypes.cast(name_buffer, wintypes.LPWSTR),
    )
    descriptor = ctypes.c_void_p()
    descriptor_bytes = wintypes.DWORD()
    if sddl is not None and not ADVAPI32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        sddl, SDDL_REVISION_1, ctypes.byref(descriptor),
        ctypes.byref(descriptor_bytes),
    ):
        raise win_error(label + ":sddl_convert")
    try:
        attributes = OBJECT_ATTRIBUTES(
            ctypes.sizeof(OBJECT_ATTRIBUTES), wintypes.HANDLE(parent_handle),
            ctypes.pointer(unicode_name), OBJ_CASE_INSENSITIVE | OBJ_DONT_REPARSE,
            descriptor.value if descriptor.value else None, None,
        )
        status_block = IO_STATUS_BLOCK()
        result_handle = wintypes.HANDLE()
        status = int(NTDLL.NtCreateFile(
            ctypes.byref(result_handle), desired_access,
            ctypes.byref(attributes), ctypes.byref(status_block), None,
            FILE_ATTRIBUTE_NORMAL, share_access, disposition, options,
            None, 0,
        ))
        if status < 0:
            raise NtRefuse(label, status)
        numeric = int(result_handle.value) if result_handle.value else 0
        if numeric in (0, INVALID_HANDLE_VALUE):
            raise Refuse(label + ":invalid_success_handle")
        return numeric, int(status_block.information)
    finally:
        if descriptor.value:
            KERNEL32.LocalFree(descriptor)


def handle_final_path(handle: int) -> Path:
    capacity = 32768
    buffer = ctypes.create_unicode_buffer(capacity)
    length = KERNEL32.GetFinalPathNameByHandleW(
        wintypes.HANDLE(handle), buffer, capacity,
        FILE_NAME_NORMALIZED | VOLUME_NAME_DOS,
    )
    if length == 0 or length >= capacity:
        raise win_error("ledger_handle_final_path")
    value = buffer.value
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return Path(value)


def handle_identity(handle: int, expect_directory: bool) -> tuple[int, bytes, int, int]:
    attributes = FILE_ATTRIBUTE_TAG_INFO()
    standard = FILE_STANDARD_INFO()
    identity_value = FILE_ID_INFO()
    calls = (
        KERNEL32.GetFileInformationByHandleEx(
            wintypes.HANDLE(handle), FILE_ATTRIBUTE_TAG_INFO_CLASS,
            ctypes.byref(attributes), ctypes.sizeof(attributes),
        ),
        KERNEL32.GetFileInformationByHandleEx(
            wintypes.HANDLE(handle), FILE_STANDARD_INFO_CLASS,
            ctypes.byref(standard), ctypes.sizeof(standard),
        ),
        KERNEL32.GetFileInformationByHandleEx(
            wintypes.HANDLE(handle), FILE_ID_INFO_CLASS,
            ctypes.byref(identity_value), ctypes.sizeof(identity_value),
        ),
    )
    if not all(calls):
        raise win_error("ledger_handle_information")
    forbidden = FILE_ATTRIBUTE_DEVICE | FILE_ATTRIBUTE_REPARSE_POINT
    if attributes.file_attributes & forbidden:
        raise Refuse("ledger_handle_device_or_reparse")
    is_directory = bool(attributes.file_attributes & FILE_ATTRIBUTE_DIRECTORY)
    if is_directory is not expect_directory or bool(standard.directory) is not expect_directory:
        raise Refuse("ledger_handle_type")
    if standard.delete_pending or (not expect_directory and standard.number_of_links != 1):
        raise Refuse("ledger_handle_delete_or_link_count")
    return (
        int(identity_value.volume_serial_number),
        bytes(identity_value.file_id.identifier),
        int(standard.end_of_file),
        int(standard.number_of_links),
    )


def open_directory_handle(path: Path, allow_acl_change: bool,
                          allow_children: bool,
                          allow_traverse_only: bool = False) -> tuple[int, tuple[int, bytes, int, int]]:
    access = FILE_READ_ATTRIBUTES | READ_CONTROL | SYNCHRONIZE
    if not allow_traverse_only:
        access |= FILE_LIST_DIRECTORY
    if allow_children:
        access |= FILE_ADD_FILE | FILE_ADD_SUBDIRECTORY
    if allow_acl_change:
        access |= WRITE_DAC
    handle = KERNEL32.CreateFileW(
        str(path), access, FILE_SHARE_READ | FILE_SHARE_WRITE, None,
        OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    numeric = int(handle) if handle else 0
    if numeric in (0, INVALID_HANDLE_VALUE):
        raise win_error("ledger_directory_open")
    try:
        identity_value = handle_identity(numeric, True)
        exact_path(handle_final_path(numeric), path, "ledger_directory_final")
        return numeric, identity_value
    except BaseException:
        close_handle(numeric)
        raise


def handle_dacl_sddl(handle: int) -> str:
    descriptor = ctypes.c_void_p()
    string_value = ctypes.c_void_p()
    length = wintypes.ULONG()
    status = ADVAPI32.GetSecurityInfo(
        wintypes.HANDLE(handle), SE_FILE_OBJECT, DACL_SECURITY_INFORMATION,
        None, None, None, None, ctypes.byref(descriptor),
    )
    if status != 0 or not descriptor.value:
        raise Refuse(f"anchor_get_security:win32_{status}")
    try:
        if not ADVAPI32.ConvertSecurityDescriptorToStringSecurityDescriptorW(
            descriptor, SDDL_REVISION_1, DACL_SECURITY_INFORMATION,
            ctypes.byref(string_value), ctypes.byref(length),
        ) or not string_value.value:
            raise win_error("anchor_dacl_to_sddl")
        try:
            return ctypes.wstring_at(string_value)
        finally:
            KERNEL32.LocalFree(string_value)
    finally:
        KERNEL32.LocalFree(descriptor)


class LedgerLease:
    def __init__(self, path: Path, file_handle: int,
                 directory_handles: list[int], identity_value: tuple[int, bytes, int, int],
                 raw: bytes) -> None:
        self.path = path
        self.file_handle = file_handle
        self.directory_handles = directory_handles
        self.identity = identity_value
        self.raw = raw

    def close(self) -> None:
        close_handle(self.file_handle)
        self.file_handle = 0
        for handle in reversed(self.directory_handles):
            close_handle(handle)
        self.directory_handles.clear()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def reject_constant(value: str) -> None:
    raise Refuse("nonfinite_json:" + value)


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise Refuse("duplicate_json_key:" + key)
        result[key] = value
    return result


def strict_json(raw: bytes, label: str) -> dict[str, object]:
    if not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise Refuse(label + ":encoding")
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )
    if not isinstance(value, dict):
        raise Refuse(label + ":root")
    return value


def exact_str(value: object, label: str) -> str:
    if type(value) is not str:
        raise Refuse(label + ":type_str")
    return value


def exact_bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise Refuse(label + ":type_bool")
    return value


def exact_int(value: object, label: str) -> int:
    if type(value) is not int:
        raise Refuse(label + ":type_int")
    return value


def exact_list(value: object, label: str) -> list[object]:
    if type(value) is not list:
        raise Refuse(label + ":type_list")
    return value


def exact_object(value: object, label: str) -> dict[str, object]:
    if type(value) is not dict:
        raise Refuse(label + ":type_object")
    return value


def identity(path: Path) -> tuple[int, int, int, int, int]:
    observed = path.lstat()
    attributes = int(getattr(observed, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if stat.S_ISLNK(observed.st_mode) or attributes & reparse or not stat.S_ISREG(observed.st_mode):
        raise Refuse("not_regular_nonreparse:" + str(path))
    return observed.st_dev, observed.st_ino, observed.st_size, observed.st_mtime_ns, attributes


def read_stable(path: Path) -> bytes:
    before = identity(path)
    with path.open("rb") as stream:
        raw = stream.read()
    after = identity(path)
    if before != after or len(raw) != before[2]:
        raise Refuse("changed_while_reading:" + str(path))
    return raw


def exact_path(observed: Path, expected: Path, label: str) -> None:
    if os.path.normcase(os.path.abspath(observed)) != os.path.normcase(os.path.abspath(expected)):
        raise Refuse(label + ":fixed_path")


def safe_relative(value: str) -> PurePosixPath:
    if "\\" in value or "\0" in value:
        raise Refuse("relative_path_grammar:" + value)
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise Refuse("relative_path_grammar:" + value)
    return path


def directory_snapshot(root: Path) -> dict[str, bytes]:
    root_stat = root.lstat()
    attributes = int(getattr(root_stat, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if not stat.S_ISDIR(root_stat.st_mode) or attributes & reparse:
        raise Refuse("directory_nonreparse:" + str(root))
    result: dict[str, bytes] = {}
    for child in sorted(root.iterdir(), key=lambda value: value.name):
        if not child.is_file() or child.name in result:
            raise Refuse("flat_regular_inventory:" + str(child))
        result[child.name] = read_stable(child)
    return result


def inventory_canonical(snapshot: dict[str, bytes]) -> bytes:
    rows: list[bytes] = []
    for path in sorted(snapshot):
        safe_relative(path)
        raw = snapshot[path]
        rows.append(f"{path}\t{len(raw)}\t{sha256(raw)}\n".encode("utf-8"))
    return b"".join(rows)


def parse_stage1(snapshot: dict[str, bytes], expected_root: str,
                 expected_seal_sha256: str,
                 expected_all_files_root: str) -> tuple[dict[str, bytes], dict[str, object]]:
    if "STATIC_SEAL_MANIFEST.json" not in snapshot:
        raise Refuse("stage1_seal_missing")
    seal_raw = snapshot["STATIC_SEAL_MANIFEST.json"]
    if sha256(seal_raw) != expected_seal_sha256:
        raise Refuse("stage1_external_seal_sha256")
    all_files_canonical = inventory_canonical(snapshot)
    if sha256(all_files_canonical) != expected_all_files_root:
        raise Refuse("stage1_external_all_files_root")
    seal = strict_json(seal_raw, "stage1_seal")
    expected_keys = {
        "schema", "status", "execution_authority", "candidate_executed",
        "blender_invoked", "author", "subject_count", "canonical_grammar",
        "canonical_bytes", "package_root_sha256", "subjects", "audit_a_required",
        "audit_a_maximum_authority", "audit_b_required",
        "root_same_handle_external_exe_sha256_required",
        "maximum_future_blender_invocations_after_both_acceptances",
        "stage1_external_seal_sha256_required",
        "stage1_external_all_files_inventory_root_required",
        "durable_materialization_consumed_ledger_required", "claim_boundary",
    }
    if set(seal) != expected_keys:
        raise Refuse("stage1_seal_keys")
    scalars = {
        "schema": "kira.r25.medical_reference_proxy.v3r30.static_seal.v1",
        "status": "SEALED_STATIC_TWO_STAGE_AUTHOR_CANDIDATE_PENDING_DIFFERENT_AUDIT_A",
        "execution_authority": "NONE",
        "author": "codex_r25_medical_reference_proxy_v3r30_two_stage_author",
        "canonical_grammar": "UTF8_LF_PYTHON_ORDINAL_SORTED_PATH_TAB_BYTES_TAB_LOWER_SHA256_LF",
        "audit_a_maximum_authority": "ONE_SCRATCH_STAGE2_MATERIALIZATION_AND_NATIVE_BUILD_ONLY_NO_BLENDER",
        "claim_boundary": "ISOLATED_NORMALIZED_PELVIC_CORE_CLINICAL_REFERENCE_PROXY_ONLY_NOT_KIRA_BODY",
    }
    for key, expected in scalars.items():
        if exact_str(seal[key], "stage1_seal." + key) != expected:
            raise Refuse("stage1_seal_value:" + key)
    for key, expected in {
        "candidate_executed": False,
        "blender_invoked": False,
        "audit_a_required": True,
        "audit_b_required": True,
        "root_same_handle_external_exe_sha256_required": True,
        "stage1_external_seal_sha256_required": True,
        "stage1_external_all_files_inventory_root_required": True,
        "durable_materialization_consumed_ledger_required": True,
    }.items():
        if exact_bool(seal[key], "stage1_seal." + key) is not expected:
            raise Refuse("stage1_seal_value:" + key)
    if exact_int(seal["maximum_future_blender_invocations_after_both_acceptances"],
                 "stage1_seal.maximum_future_blender_invocations_after_both_acceptances") != 1:
        raise Refuse("stage1_invocation_ceiling")
    subjects = exact_list(seal["subjects"], "stage1_seal.subjects")
    if exact_int(seal["subject_count"], "stage1_seal.subject_count") != len(subjects) or not subjects:
        raise Refuse("stage1_subject_count")
    rows: list[tuple[str, int, str]] = []
    bound: dict[str, bytes] = {}
    for index, subject_value in enumerate(subjects):
        subject = exact_object(subject_value, f"stage1_seal.subjects[{index}]")
        if set(subject) != {"path", "bytes", "sha256"}:
            raise Refuse("stage1_subject_shape")
        path = exact_str(subject["path"], f"stage1_seal.subjects[{index}].path")
        safe_relative(path)
        byte_count = exact_int(subject["bytes"], f"stage1_seal.subjects[{index}].bytes")
        digest = exact_str(subject["sha256"], f"stage1_seal.subjects[{index}].sha256")
        if byte_count < 0:
            raise Refuse("stage1_subject_negative_bytes:" + path)
        if path not in snapshot or path == "STATIC_SEAL_MANIFEST.json" or not HEX64.fullmatch(digest):
            raise Refuse("stage1_subject_binding:" + path)
        raw = snapshot[path]
        if len(raw) != byte_count or sha256(raw) != digest:
            raise Refuse("stage1_subject_mismatch:" + path)
        rows.append((path, byte_count, digest))
        bound[path] = raw
    if [row[0] for row in rows] != sorted(row[0] for row in rows) or len(bound) != len(rows):
        raise Refuse("stage1_subject_order_unique")
    canonical = b"".join(f"{path}\t{byte_count}\t{digest}\n".encode("utf-8") for path, byte_count, digest in rows)
    root = sha256(canonical)
    if exact_int(seal["canonical_bytes"], "stage1_seal.canonical_bytes") != len(canonical):
        raise Refuse("stage1_canonical_bytes")
    if exact_str(seal["package_root_sha256"], "stage1_seal.package_root_sha256") != root or root != expected_root:
        raise Refuse("stage1_external_root")
    if set(snapshot) != set(bound) | {"STATIC_SEAL_MANIFEST.json"}:
        raise Refuse("stage1_unsealed_file")
    return bound, seal


def parse_tsv(raw: bytes, header: str, columns: int, label: str) -> list[list[str]]:
    if not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise Refuse(label + ":encoding")
    lines = raw.decode("utf-8").splitlines()
    if not lines or lines[0] != header:
        raise Refuse(label + ":header")
    rows = [line.split("\t") for line in lines[1:]]
    if any(len(row) != columns or any(field == "" for field in row) for row in rows):
        raise Refuse(label + ":columns")
    return rows


def verify_upstream(raw: bytes) -> list[tuple[Path, int, str, str]]:
    rows = parse_tsv(raw, "scope\tpath\tbytes\tsha256\tstatus", 5, "upstream")
    if len(rows) != 33:
        raise Refuse("upstream_count")
    bindings: list[tuple[Path, int, str, str]] = []
    seen: set[str] = set()
    v3r29_nested_manifest: bytes | None = None
    for scope, path_text, byte_text, digest, status in rows:
        relative = safe_relative(path_text)
        if path_text in seen or scope not in {"v3r29_author", "v3r29_rejection"}:
            raise Refuse("upstream_unique_scope")
        expected_status = (
            "DO_NOT_MATERIALIZE_BUILD_RUN_V3R29_PRESERVED"
            if scope == "v3r29_author" else "REJECTION_PRESERVED"
        )
        if status != expected_status or not byte_text.isdecimal() or not HEX64.fullmatch(digest):
            raise Refuse("upstream_grammar:" + path_text)
        absolute = KIRA_ROOT.joinpath(*relative.parts)
        raw_file = read_stable(absolute)
        if len(raw_file) != int(byte_text) or sha256(raw_file) != digest:
            raise Refuse("upstream_mismatch:" + path_text)
        seen.add(path_text)
        bindings.append((absolute, int(byte_text), digest, scope))
        if scope == "v3r29_author" and path_text.endswith("/UPSTREAM_CLOSURE.tsv"):
            v3r29_nested_manifest = raw_file
    if v3r29_nested_manifest is None:
        raise Refuse("v3r29_nested_upstream_missing")
    v3r28_rows = parse_tsv(
        v3r29_nested_manifest,
        "scope\tpath\tbytes\tsha256\tstatus", 5,
        "v3r29_nested_v3r28_upstream",
    )
    if len(v3r28_rows) != 28:
        raise Refuse("v3r29_nested_v3r28_count")
    v3r28_seen: set[str] = set()
    v3r28_nested_manifest: bytes | None = None
    for scope, path_text, byte_text, digest, status in v3r28_rows:
        relative = safe_relative(path_text)
        if path_text in seen or path_text in v3r28_seen or scope not in {
            "v3r28_author", "v3r28_rejection",
        }:
            raise Refuse("v3r29_nested_v3r28_unique_scope")
        expected_status = (
            "DO_NOT_MATERIALIZE_BUILD_RUN_V3R28_PRESERVED"
            if scope == "v3r28_author" else "REJECTION_PRESERVED"
        )
        if status != expected_status or not byte_text.isdecimal() or not HEX64.fullmatch(digest):
            raise Refuse("v3r29_nested_v3r28_grammar:" + path_text)
        absolute = KIRA_ROOT.joinpath(*relative.parts)
        nested_raw = read_stable(absolute)
        if len(nested_raw) != int(byte_text) or sha256(nested_raw) != digest:
            raise Refuse("v3r29_nested_v3r28_mismatch:" + path_text)
        v3r28_seen.add(path_text)
        bindings.append((absolute, int(byte_text), digest, "nested_" + scope))
        if scope == "v3r28_author" and path_text.endswith("/UPSTREAM_CLOSURE.tsv"):
            v3r28_nested_manifest = nested_raw
    if v3r28_nested_manifest is None:
        raise Refuse("v3r28_nested_v3r27_upstream_missing")
    v3r27_rows = parse_tsv(
        v3r28_nested_manifest,
        "scope\tpath\tbytes\tsha256\tstatus", 5,
        "v3r28_nested_v3r27_upstream",
    )
    if len(v3r27_rows) != 17:
        raise Refuse("v3r28_nested_v3r27_count")
    v3r27_seen: set[str] = set()
    for scope, path_text, byte_text, digest, status in v3r27_rows:
        relative = safe_relative(path_text)
        if (path_text in seen or path_text in v3r28_seen or
                path_text in v3r27_seen or scope not in {
                    "v3r27_author", "v3r27_rejection",
                }):
            raise Refuse("v3r28_nested_v3r27_unique_scope")
        expected_status = (
            "DO_NOT_RUN_V3R27_PRESERVED"
            if scope == "v3r27_author" else "REJECTION_PRESERVED"
        )
        if (status != expected_status or not byte_text.isdecimal() or
                not HEX64.fullmatch(digest)):
            raise Refuse("v3r28_nested_v3r27_grammar:" + path_text)
        absolute = KIRA_ROOT.joinpath(*relative.parts)
        nested_raw = read_stable(absolute)
        if len(nested_raw) != int(byte_text) or sha256(nested_raw) != digest:
            raise Refuse("v3r28_nested_v3r27_mismatch:" + path_text)
        v3r27_seen.add(path_text)
        bindings.append((absolute, int(byte_text), digest, "transitive_" + scope))
    if len(bindings) != 78:
        raise Refuse("upstream_total_78")
    return bindings


def materialization_key(stage1_root: str, seal_sha256: str, all_files_root: str,
                        auditor: str) -> str:
    canonical = (
        "v3r30-materialization-authority-v1\n"
        f"stage1_subject_root\t{stage1_root}\n"
        f"stage1_seal_sha256\t{seal_sha256}\n"
        f"stage1_all_files_root\t{all_files_root}\n"
        f"audit_a_auditor_id\t{auditor}\n"
    ).encode("utf-8")
    return sha256(canonical)


def parse_audit(snapshot: dict[str, bytes], expected_manifest_sha: str,
                expected_stage1_root: str, expected_stage1_seal_sha256: str,
                expected_stage1_all_files_root: str,
                expected_auditor: str) -> tuple[list[tuple[str, bytes]], dict[str, object]]:
    required = {"AUDIT_ARTIFACT_MANIFEST.tsv", "AUDIT_DECISION.json", "CHECKPOINT.md", "INDEPENDENT_AUDIT.tsv"}
    if not required.issubset(snapshot):
        raise Refuse("audit_required_files")
    manifest_raw = snapshot["AUDIT_ARTIFACT_MANIFEST.tsv"]
    if sha256(manifest_raw) != expected_manifest_sha:
        raise Refuse("audit_external_manifest_digest")
    rows = parse_tsv(manifest_raw, "path\tbytes\tsha256", 3, "audit_manifest")
    if [row[0] for row in rows] != sorted(row[0] for row in rows):
        raise Refuse("audit_manifest_order")
    covered: list[tuple[str, bytes]] = []
    for path, byte_text, digest in rows:
        safe_relative(path)
        if "/" in path or path == "AUDIT_ARTIFACT_MANIFEST.tsv" or not byte_text.isdecimal() or not HEX64.fullmatch(digest):
            raise Refuse("audit_manifest_row:" + path)
        if path not in snapshot or any(prior[0] == path for prior in covered):
            raise Refuse("audit_manifest_unique:" + path)
        raw = snapshot[path]
        if len(raw) != int(byte_text) or sha256(raw) != digest:
            raise Refuse("audit_artifact_mismatch:" + path)
        covered.append((path, raw))
    if set(snapshot) != {"AUDIT_ARTIFACT_MANIFEST.tsv"} | {path for path, _ in covered}:
        raise Refuse("audit_unbound_artifact")
    decision = strict_json(snapshot["AUDIT_DECISION.json"], "audit_decision")
    expected_keys = {
        "schema", "status", "auditor_id", "accepted_stage1_package_root",
        "accepted_stage1_seal_sha256", "accepted_stage1_all_files_root_sha256",
        "execution_authority", "candidate_executed", "blender_invoked",
        "maximum_materializations", "stage2_requires_different_audit_b", "audit_scope",
        "materialization_consumption_key_sha256",
    }
    if set(decision) != expected_keys:
        raise Refuse("audit_decision_keys")
    expected_decision: dict[str, object] = {
        "schema": "kira.r25.medical_reference_proxy.v3r30.audit_a_decision.v1",
        "status": "ACCEPT_STAGE1_FOR_STAGE2_MATERIALIZATION_ONLY_NO_BLENDER_AUTHORITY",
        "auditor_id": expected_auditor,
        "accepted_stage1_package_root": expected_stage1_root,
        "accepted_stage1_seal_sha256": expected_stage1_seal_sha256,
        "accepted_stage1_all_files_root_sha256": expected_stage1_all_files_root,
        "execution_authority": "MATERIALIZE_STAGE2_ONLY_NO_BLENDER",
        "candidate_executed": False,
        "blender_invoked": False,
        "maximum_materializations": 1,
        "stage2_requires_different_audit_b": True,
        "audit_scope": "CACHE_FREE_STATIC_SYNTAX_MOCKED_HOSTILE_AND_TRUSTED_BUILD_ANALYZE_ONLY",
        "materialization_consumption_key_sha256": materialization_key(
            expected_stage1_root,
            expected_stage1_seal_sha256,
            expected_stage1_all_files_root,
            expected_auditor,
        ),
    }
    string_keys = expected_keys - {
        "candidate_executed", "blender_invoked", "maximum_materializations",
        "stage2_requires_different_audit_b",
    }
    for key in string_keys:
        exact_str(decision[key], "audit_decision." + key)
    exact_bool(decision["candidate_executed"], "audit_decision.candidate_executed")
    exact_bool(decision["blender_invoked"], "audit_decision.blender_invoked")
    exact_bool(decision["stage2_requires_different_audit_b"],
               "audit_decision.stage2_requires_different_audit_b")
    exact_int(decision["maximum_materializations"], "audit_decision.maximum_materializations")
    if decision != expected_decision:
        raise Refuse("audit_decision_exact")
    audit_rows = parse_tsv(
        snapshot["INDEPENDENT_AUDIT.tsv"],
        "row_id\tstatus\tevidence_sha256\tfinding",
        4,
        "independent_audit",
    )
    if tuple(row[0] for row in audit_rows) != AUDIT_ROW_IDS or any(row[1] != "PASS" or not HEX64.fullmatch(row[2]) for row in audit_rows):
        raise Refuse("independent_audit_18_pass")
    return [("AUDIT_ARTIFACT_MANIFEST.tsv", manifest_raw), *covered], decision


def parse_install_authority(
    snapshot: dict[str, bytes], expected_manifest_sha: str,
    expected_auditor: str, audit_a_manifest_sha: str,
    audit_a_auditor: str,
) -> tuple[list[tuple[str, bytes]], dict[str, object]]:
    required = {
        "INSTALL_AUTHORITY_MANIFEST.tsv", "INSTALL_AUTHORITY_DECISION.json",
        "CHECKPOINT.md", "INSTALL_AUTHORITY_AUDIT.tsv",
    }
    if set(snapshot) != required:
        raise Refuse("install_authority_exact_files")
    manifest_raw = snapshot["INSTALL_AUTHORITY_MANIFEST.tsv"]
    if sha256(manifest_raw) != expected_manifest_sha:
        raise Refuse("install_authority_external_manifest_digest")
    rows = parse_tsv(
        manifest_raw, "path\tbytes\tsha256", 3,
        "install_authority_manifest",
    )
    if [row[0] for row in rows] != sorted(row[0] for row in rows):
        raise Refuse("install_authority_manifest_order")
    covered: list[tuple[str, bytes]] = []
    for path, byte_text, digest in rows:
        safe_relative(path)
        if ("/" in path or path == "INSTALL_AUTHORITY_MANIFEST.tsv"
                or not byte_text.isdecimal() or not HEX64.fullmatch(digest)):
            raise Refuse("install_authority_manifest_row:" + path)
        if path not in snapshot or any(prior[0] == path for prior in covered):
            raise Refuse("install_authority_manifest_unique:" + path)
        raw = snapshot[path]
        if len(raw) != int(byte_text) or sha256(raw) != digest:
            raise Refuse("install_authority_artifact_mismatch:" + path)
        covered.append((path, raw))
    if set(snapshot) != {"INSTALL_AUTHORITY_MANIFEST.tsv"} | {
        path for path, _ in covered
    }:
        raise Refuse("install_authority_unbound_artifact")
    if (expected_auditor == audit_a_auditor or
            expected_auditor in {
                "codex_r25_medical_reference_proxy_v3r30_two_stage_author",
                "codex_r25_medical_reference_proxy_v3r29_two_stage_author",
            }):
        raise Refuse("install_authority_auditor_separation")
    decision = strict_json(
        snapshot["INSTALL_AUTHORITY_DECISION.json"],
        "install_authority_decision",
    )
    expected_decision: dict[str, object] = {
        "schema": "kira.r25.medical_reference_proxy.v3r30.programdata_install_authority.v1",
        "status": "AUTHORIZE_EXACT_PROGRAMDATA_LEDGER_DIRECTORY_FOR_ONE_MATERIALIZATION_ONLY_NO_BUILD_NO_BLENDER",
        "auditor_id": expected_auditor,
        "accepted_audit_a_manifest_sha256": audit_a_manifest_sha,
        "accepted_audit_a_auditor_id": audit_a_auditor,
        "program_data_anchor": str(PROGRAM_DATA_ANCHOR),
        "program_data_anchor_dacl_sddl": EXPECTED_PROGRAM_DATA_SDDL,
        "program_data_anchor_delete_child_access": "REFUSED_ACCESS_DENIED",
        "ledger_root": str(MATERIALIZATION_LEDGER_ROOT),
        "ledger_file_atomic_creation_dacl_sddl": LEDGER_FILE_SEALED_SDDL,
        "ledger_file_canonical_readback_dacl_sddl": LEDGER_FILE_SEALED_CANONICAL_SDDL,
        "ledger_directory_atomic_creation_append_only_dacl_sddl": LEDGER_DIRECTORY_APPEND_ONLY_SDDL,
        "ledger_directory_canonical_readback_dacl_sddl": LEDGER_DIRECTORY_APPEND_ONLY_CANONICAL_SDDL,
        "ntcreatefile_rootdirectory_relative_directory_and_file_required": True,
        "final_owner_rights_dacls_at_atomic_creation_required": True,
        "execution_authority": "INSTALL_ONE_LEDGER_DIRECTORY_FOR_MATERIALIZATION_ONLY_NO_BUILD_NO_BLENDER",
        "program_data_directory_created_by_auditor": False,
        "candidate_executed": False,
        "maximum_program_data_directory_creations": 1,
        "maximum_materializations": 1,
        "maximum_native_builds": 0,
        "maximum_blender_invocations": 0,
        "different_audit_b_still_required": True,
    }
    if set(decision) != set(expected_decision):
        raise Refuse("install_authority_decision_keys")
    for key, expected in expected_decision.items():
        if type(expected) is str:
            exact_str(decision[key], "install_authority_decision." + key)
        elif type(expected) is bool:
            exact_bool(decision[key], "install_authority_decision." + key)
        elif type(expected) is int:
            exact_int(decision[key], "install_authority_decision." + key)
        else:
            raise Refuse("install_authority_internal_expected_type")
    if decision != expected_decision:
        raise Refuse("install_authority_decision_exact")
    audit_rows = parse_tsv(
        snapshot["INSTALL_AUTHORITY_AUDIT.tsv"],
        "row_id\tstatus\tevidence_sha256\tfinding", 4,
        "install_authority_audit",
    )
    expected_rows = (
        "01_programdata_target_absent",
        "02_programdata_anchor_exact_identity",
        "03_programdata_anchor_exact_dacl",
        "04_programdata_delete_child_access_refused",
        "05_owner_rights_atomic_final_dacl_policy",
        "06_handle_relative_atomic_creation_policy",
        "07_zero_build_blender_authority",
    )
    if (tuple(row[0] for row in audit_rows) != expected_rows
            or any(row[1] != "PASS" or not HEX64.fullmatch(row[2])
                   for row in audit_rows)):
        raise Refuse("install_authority_audit_seven_pass")
    return [("INSTALL_AUTHORITY_MANIFEST.tsv", manifest_raw), *covered], decision


def c_wide(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace('"', '\\"')


def c_ascii(value: str) -> str:
    if not value.isascii() or any(ord(char) < 32 for char in value):
        raise Refuse("c_ascii")
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_header(stage1_root: str, stage1_seal_sha256: str,
                 stage1_all_files_root: str, audit_manifest_sha: str,
                 auditor: str, install_manifest_sha: str,
                 install_auditor: str, consumption_key: str,
                 consumption_ledger_path: Path, consumption_ledger_raw: bytes,
                 stage1_snapshot: dict[str, bytes], stage1_subjects: dict[str, bytes],
                 upstream: list[tuple[Path, int, str, str]],
                 audit: list[tuple[str, bytes]],
                 install_authority: list[tuple[str, bytes]]) -> bytes:
    worker = stage1_subjects["blender_worker_v3r30.py"]
    spec = stage1_subjects["PROXY_SPEC.json"]
    frame = stage1_subjects["NORMALIZED_REFERENCE_FRAME.json"]
    bindings: list[tuple[Path, int, str, str]] = []
    for name, raw in sorted(stage1_snapshot.items()):
        bindings.append((EXPECTED_STAGE1_DIR / name, len(raw), sha256(raw), "stage1:" + name))
    bindings.extend(upstream)
    for name, raw in audit:
        bindings.append((EXPECTED_AUDIT_A_DIR / name, len(raw), sha256(raw), "audit_a:" + name))
    for name, raw in install_authority:
        bindings.append((
            EXPECTED_INSTALL_AUTHORITY_DIR / name, len(raw), sha256(raw),
            "programdata_install_authority:" + name,
        ))
    bindings.append((
        consumption_ledger_path,
        len(consumption_ledger_raw),
        sha256(consumption_ledger_raw),
        "materialization:durable_consumed_authority_ledger",
    ))
    bindings.extend((
        (INSTALLED_STAGE2_ROOT / "blender_worker_v3r30.py", len(worker), sha256(worker), "stage2:worker"),
        (INSTALLED_STAGE2_ROOT / "PROXY_SPEC.json", len(spec), sha256(spec), "stage2:spec"),
        (INSTALLED_STAGE2_ROOT / "NORMALIZED_REFERENCE_FRAME.json", len(frame), sha256(frame), "stage2:frame"),
        (BLENDER_PATH, BLENDER_BYTES, BLENDER_SHA256, "runtime:blender_5_1_2"),
    ))
    normalized = sorted(
        (os.path.normcase(str(path)), path, byte_count, digest, label)
        for path, byte_count, digest, label in bindings
    )
    if len(normalized) > 192 or len({row[0] for row in normalized}) != len(normalized):
        raise Refuse("native_binding_count_or_duplicate")
    lines = [
        "#ifndef KIRA_V3R30_POST_AUDIT_BINDINGS_H",
        "#define KIRA_V3R30_POST_AUDIT_BINDINGS_H",
        "",
        "#define V3R30_MATERIALIZED 1",
        f'#define V3R30_STAGE1_PACKAGE_ROOT "{stage1_root}"',
        f'#define V3R30_STAGE1_SEAL_SHA256 "{stage1_seal_sha256}"',
        f'#define V3R30_STAGE1_ALL_FILES_ROOT "{stage1_all_files_root}"',
        f'#define V3R30_AUDIT_A_SHA256 "{audit_manifest_sha}"',
        f'#define V3R30_INSTALL_AUTHORITY_MANIFEST_SHA256 "{install_manifest_sha}"',
        f'#define V3R30_INSTALL_AUTHORITY_AUDITOR "{c_ascii(install_auditor)}"',
        f'#define V3R30_MATERIALIZATION_CONSUMPTION_KEY "{consumption_key}"',
        f'#define V3R30_AUDITOR "{c_ascii(auditor)}"',
        f'#define V3R30_FRAME_SHA256 "{sha256(frame)}"',
        f'#define V3R30_SPEC_SHA256 "{sha256(spec)}"',
        f'#define V3R30_WORKER_SHA256 "{sha256(worker)}"',
        f'#define V3R30_EXPECTED_SELF_PATH L"{c_wide(INSTALLED_ANCHOR_PATH)}"',
        f'#define V3R30_WORKER_PATH L"{c_wide(INSTALLED_STAGE2_ROOT / "blender_worker_v3r30.py")}"',
        f'#define V3R30_OUTPUT_PARENT L"{c_wide(INSTALLED_STAGE2_ROOT)}"',
        f'#define V3R30_BLENDER_PATH L"{c_wide(BLENDER_PATH)}"',
        f"#define V3R30_BLENDER_BYTES {BLENDER_BYTES}ULL",
        f'#define V3R30_BLENDER_SHA256 "{BLENDER_SHA256}"',
        f"#define V3R30_BINDING_COUNT {len(bindings)}U",
        "",
        f"static const V3R30Binding V3R30_BINDINGS[{len(bindings)}] = {{",
    ]
    for _, path, byte_count, digest, label in normalized:
        lines.append(f'    {{ L"{c_wide(path)}", {byte_count}ULL, "{digest}", "{c_ascii(label)}" }},')
    lines.extend(("};", "", "#endif", ""))
    return "\n".join(lines).encode("utf-8")


def exclusive_write(path: Path, raw: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def materialization_ledger_record(stage1_root: str, seal_sha256: str,
                                  all_files_root: str, audit_manifest_sha256: str,
                                  auditor: str, install_manifest_sha256: str,
                                  install_auditor: str,
                                  output_dir: Path) -> tuple[str, bytes]:
    key = materialization_key(stage1_root, seal_sha256, all_files_root, auditor)
    record = (json.dumps({
        "schema": "kira.r25.medical_reference_proxy.v3r30.materialization_consumed.v1",
        "state": "MATERIALIZATION_AUTHORITY_CONSUMED_BEFORE_ANY_OUTPUT_WRITE",
        "materialization_consumption_key_sha256": key,
        "stage1_package_root_sha256": stage1_root,
        "stage1_seal_sha256": seal_sha256,
        "stage1_all_files_root_sha256": all_files_root,
        "audit_a_manifest_sha256": audit_manifest_sha256,
        "audit_a_auditor_id": auditor,
        "program_data_install_authority_manifest_sha256": install_manifest_sha256,
        "program_data_install_authority_auditor_id": install_auditor,
        "fixed_output_dir": str(output_dir),
        "maximum_materializations": 1,
        "deleting_or_recreating_output_does_not_remove_this_ledger": True,
        "program_data_anchor_exact_dacl_required": EXPECTED_PROGRAM_DATA_SDDL,
        "program_data_anchor_delete_child_access_refused": True,
        "anchor_parent_and_ledger_directory_held_without_delete_share": True,
        "ledger_directory_nt_rootdirectory_relative_open_or_create": True,
        "ledger_file_nt_rootdirectory_relative_create": True,
        "final_owner_rights_dacls_supplied_during_atomic_create": True,
        "ledger_handle_held_through_atomic_publish": True,
        "ledger_single_link_nonreparse": True,
        "ledger_file_read_only_and_directory_append_only_after_consumption": True,
        "blender_authority": "NONE",
    }, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    return key, record


def require_anchor_parent_without_delete_child(parent: Path) -> int:
    probe = KERNEL32.CreateFileW(
        str(parent), FILE_DELETE_CHILD,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None, OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, None,
    )
    numeric = int(probe) if probe else 0
    if numeric not in (0, INVALID_HANDLE_VALUE):
        close_handle(numeric)
        raise Refuse("materialization_anchor_parent_grants_delete_child")
    if ctypes.get_last_error() != ERROR_ACCESS_DENIED:
        raise win_error("materialization_anchor_parent_delete_child_ambiguous")
    parent_handle, _ = open_directory_handle(parent, False, True)
    try:
        if handle_dacl_sddl(parent_handle) != EXPECTED_PROGRAM_DATA_SDDL:
            raise Refuse("materialization_anchor_parent_dacl_mismatch")
        return parent_handle
    except BaseException:
        close_handle(parent_handle)
        raise


def ensure_ledger_root(root: Path, anchor_parent: Path,
                       require_durable_parent: bool) -> tuple[list[int], bool]:
    if (not root.is_absolute() or not anchor_parent.is_absolute()
            or root.parent != anchor_parent):
        raise Refuse("materialization_ledger_root_scope")
    if require_durable_parent:
        if root != MATERIALIZATION_LEDGER_ROOT or anchor_parent != PROGRAM_DATA_ANCHOR:
            raise Refuse("materialization_ledger_production_anchor")
    handles: list[int] = []
    try:
        if require_durable_parent:
            parent_handle = require_anchor_parent_without_delete_child(anchor_parent)
        else:
            parent_handle, _ = open_directory_handle(anchor_parent, False, True)
        handles.append(parent_handle)
        create_desired = (
            FILE_LIST_DIRECTORY | FILE_ADD_FILE | FILE_ADD_SUBDIRECTORY |
            FILE_READ_ATTRIBUTES | READ_CONTROL | WRITE_DAC | SYNCHRONIZE
        )
        try:
            root_handle, information = nt_create_relative(
                parent_handle, root.name, create_desired,
                FILE_SHARE_READ | FILE_SHARE_WRITE, FILE_CREATE,
                FILE_DIRECTORY_FILE | FILE_SYNCHRONOUS_IO_NONALERT |
                FILE_OPEN_REPARSE_POINT_OPTION,
                sddl=(LEDGER_DIRECTORY_APPEND_ONLY_SDDL
                      if require_durable_parent else None),
                label="materialization_ledger_directory_relative_create",
            )
            created = True
            if information != FILE_CREATED:
                close_handle(root_handle)
                raise Refuse("materialization_ledger_directory_create_disposition")
        except NtRefuse as error:
            if error.ntstatus != STATUS_OBJECT_NAME_COLLISION:
                raise
            root_handle, information = nt_create_relative(
                parent_handle, root.name,
                FILE_LIST_DIRECTORY | FILE_READ_ATTRIBUTES |
                READ_CONTROL | SYNCHRONIZE,
                FILE_SHARE_READ | FILE_SHARE_WRITE, FILE_OPEN,
                FILE_DIRECTORY_FILE | FILE_SYNCHRONOUS_IO_NONALERT |
                FILE_OPEN_REPARSE_POINT_OPTION,
                sddl=None,
                label="materialization_ledger_directory_relative_open",
            )
            created = False
            if information != FILE_OPENED:
                close_handle(root_handle)
                raise Refuse("materialization_ledger_directory_open_disposition")
        try:
            handle_identity(root_handle, True)
            exact_path(handle_final_path(root_handle), root, "ledger_directory_final")
            if (require_durable_parent and
                    handle_dacl_sddl(root_handle) !=
                    LEDGER_DIRECTORY_APPEND_ONLY_CANONICAL_SDDL):
                raise Refuse("materialization_ledger_directory_dacl_mismatch")
        except BaseException:
            close_handle(root_handle)
            raise
        handles.append(root_handle)
        return handles, created
    except BaseException:
        for handle in reversed(handles):
            close_handle(handle)
        raise


def read_ledger_handle(handle: int, expected_bytes: int) -> bytes:
    if expected_bytes <= 0 or expected_bytes > 1024 * 1024:
        raise Refuse("materialization_consumption_ledger_size")
    if not KERNEL32.SetFilePointerEx(wintypes.HANDLE(handle), 0, None, FILE_BEGIN):
        raise win_error("materialization_consumption_ledger_seek")
    buffer = ctypes.create_string_buffer(expected_bytes)
    got = wintypes.DWORD()
    if not KERNEL32.ReadFile(
        wintypes.HANDLE(handle), buffer, expected_bytes, ctypes.byref(got), None,
    ) or got.value != expected_bytes:
        raise win_error("materialization_consumption_ledger_read")
    return bytes(buffer.raw)


def validate_ledger_lease(lease: LedgerLease) -> None:
    observed = handle_identity(lease.file_handle, False)
    if observed != lease.identity or observed[2] != len(lease.raw):
        raise Refuse("materialization_consumption_ledger_identity")
    exact_path(handle_final_path(lease.file_handle), lease.path, "ledger_file_final")
    if read_ledger_handle(lease.file_handle, len(lease.raw)) != lease.raw:
        raise Refuse("materialization_consumption_ledger_readback")


def _consume_materialization_authority(
    root: Path, anchor_parent: Path, key: str, raw: bytes,
    *, seal_acl: bool, require_durable_parent: bool,
) -> LedgerLease:
    if not HEX64.fullmatch(key):
        raise Refuse("materialization_consumption_key_grammar")
    handles, final_created = ensure_ledger_root(
        root, anchor_parent, require_durable_parent,
    )
    ledger_path = root / ("V3R30_MATERIALIZATION_CONSUMED_" + key + ".json")
    ledger_name = ledger_path.name
    try:
        if not final_created:
            try:
                numeric_existing, information = nt_create_relative(
                    handles[-1], ledger_name, GENERIC_READ | SYNCHRONIZE,
                    FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                    FILE_OPEN,
                    FILE_NON_DIRECTORY_FILE | FILE_SYNCHRONOUS_IO_NONALERT |
                    FILE_OPEN_REPARSE_POINT_OPTION,
                    sddl=None, label="materialization_ledger_existing_relative",
                )
            except NtRefuse as error:
                raise Refuse(
                    "materialization_authority_root_exists_without_exact_record:" +
                    key + ":" + str(error)
                ) from error
            try:
                if information != FILE_OPENED:
                    raise Refuse("materialization_ledger_existing_disposition")
                observed = handle_identity(numeric_existing, False)
                exact_path(handle_final_path(numeric_existing), ledger_path,
                           "ledger_existing_final")
                if (seal_acl and handle_dacl_sddl(numeric_existing) !=
                        LEDGER_FILE_SEALED_CANONICAL_SDDL):
                    raise Refuse("materialization_ledger_existing_dacl_mismatch")
                if observed[2] == len(raw) and read_ledger_handle(
                    numeric_existing, len(raw),
                ) == raw:
                    raise Refuse("materialization_authority_already_consumed:" + key)
                raise Refuse("materialization_authority_existing_ambiguity:" + key)
            finally:
                close_handle(numeric_existing)
        numeric_file, information = nt_create_relative(
            handles[-1], ledger_name,
            GENERIC_READ | GENERIC_WRITE | WRITE_DAC | SYNCHRONIZE,
            FILE_SHARE_READ, FILE_CREATE,
            FILE_NON_DIRECTORY_FILE | FILE_SYNCHRONOUS_IO_NONALERT |
            FILE_OPEN_REPARSE_POINT_OPTION | FILE_WRITE_THROUGH_OPTION,
            sddl=LEDGER_FILE_SEALED_SDDL if seal_acl else None,
            label="materialization_consumption_ledger_relative_create",
        )
        if information != FILE_CREATED:
            close_handle(numeric_file)
            raise Refuse("materialization_consumption_ledger_disposition")
        try:
            identity_value = handle_identity(numeric_file, False)
            if identity_value[2] != 0:
                raise Refuse("materialization_consumption_ledger_not_empty")
            exact_path(handle_final_path(numeric_file), ledger_path, "ledger_file_final")
            if (seal_acl and handle_dacl_sddl(numeric_file) !=
                    LEDGER_FILE_SEALED_CANONICAL_SDDL):
                raise Refuse("materialization_ledger_file_atomic_dacl")
            buffer = ctypes.create_string_buffer(raw)
            wrote = wintypes.DWORD()
            if not KERNEL32.WriteFile(
                wintypes.HANDLE(numeric_file), buffer, len(raw),
                ctypes.byref(wrote), None,
            ) or wrote.value != len(raw) or not KERNEL32.FlushFileBuffers(
                wintypes.HANDLE(numeric_file)
            ):
                raise win_error("materialization_consumption_ledger_write_flush")
            identity_value = handle_identity(numeric_file, False)
            lease = LedgerLease(ledger_path, numeric_file, handles, identity_value, raw)
            validate_ledger_lease(lease)
            if seal_acl:
                if (handle_dacl_sddl(numeric_file) !=
                        LEDGER_FILE_SEALED_CANONICAL_SDDL or
                        handle_dacl_sddl(handles[-1]) !=
                        LEDGER_DIRECTORY_APPEND_ONLY_CANONICAL_SDDL):
                    raise Refuse("materialization_ledger_sealed_dacl_readback")
                validate_ledger_lease(lease)
            return lease
        except BaseException:
            close_handle(numeric_file)
            raise
    except BaseException:
        for handle in reversed(handles):
            close_handle(handle)
        raise


def consume_materialization_authority(key: str, raw: bytes) -> LedgerLease:
    return _consume_materialization_authority(
        MATERIALIZATION_LEDGER_ROOT, PROGRAM_DATA_ANCHOR, key, raw,
        seal_acl=True, require_durable_parent=True,
    )


def exercise_consumption_handles_test_only(root: Path, key: str,
                                           raw: bytes) -> LedgerLease:
    if (not root.is_absolute() or not root.is_relative_to(CODEX_SCRATCH_ROOT)
            or root.parent == CODEX_SCRATCH_ROOT):
        raise Refuse("test_ledger_root_scope")
    return _consume_materialization_authority(
        root, root.parent, key, raw,
        seal_acl=False, require_durable_parent=False,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--stage1-dir", required=True)
    parser.add_argument("--audit-a-dir", required=True)
    parser.add_argument("--install-authority-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-stage1-root", required=True)
    parser.add_argument("--expected-stage1-seal-sha256", required=True)
    parser.add_argument("--expected-stage1-all-files-root-sha256", required=True)
    parser.add_argument("--expected-audit-manifest-sha256", required=True)
    parser.add_argument("--expected-auditor-id", required=True)
    parser.add_argument("--expected-install-authority-manifest-sha256", required=True)
    parser.add_argument("--expected-install-authority-auditor-id", required=True)
    values = parser.parse_args()
    digest_values = (
        values.expected_stage1_root,
        values.expected_stage1_seal_sha256,
        values.expected_stage1_all_files_root_sha256,
        values.expected_audit_manifest_sha256,
        values.expected_install_authority_manifest_sha256,
    )
    if any(not HEX64.fullmatch(value) for value in digest_values):
        raise Refuse("external_digest_grammar")
    if not AUDITOR.fullmatch(values.expected_auditor_id):
        raise Refuse("external_auditor_grammar")
    if not AUDITOR.fullmatch(values.expected_install_authority_auditor_id):
        raise Refuse("external_install_authority_auditor_grammar")
    return values


def main() -> int:
    args = parse_args()
    stage1_dir = Path(args.stage1_dir)
    audit_dir = Path(args.audit_a_dir)
    install_authority_dir = Path(args.install_authority_dir)
    output_dir = Path(args.output_dir)
    exact_path(stage1_dir, EXPECTED_STAGE1_DIR, "stage1")
    exact_path(audit_dir, EXPECTED_AUDIT_A_DIR, "audit_a")
    exact_path(
        install_authority_dir, EXPECTED_INSTALL_AUTHORITY_DIR,
        "install_authority",
    )
    output_absolute = Path(os.path.abspath(output_dir))
    exact_path(output_absolute, EXPECTED_MATERIALIZATION_DIR, "output")
    staging = output_absolute.with_name(output_absolute.name + ".partial." + str(os.getpid()))
    if (not output_absolute.is_relative_to(CODEX_SCRATCH_ROOT) or output_absolute.exists()
            or staging.exists()):
        raise Refuse("new_scratch_output_only")
    stage1_snapshot = directory_snapshot(stage1_dir)
    stage1_subjects, seal = parse_stage1(
        stage1_snapshot,
        args.expected_stage1_root,
        args.expected_stage1_seal_sha256,
        args.expected_stage1_all_files_root_sha256,
    )
    if exact_str(seal["author"], "stage1_seal.author") == args.expected_auditor_id:
        raise Refuse("auditor_must_differ_from_author")
    upstream = verify_upstream(stage1_subjects["UPSTREAM_CLOSURE.tsv"])
    audit_snapshot = directory_snapshot(audit_dir)
    audit, _ = parse_audit(
        audit_snapshot,
        args.expected_audit_manifest_sha256,
        args.expected_stage1_root,
        args.expected_stage1_seal_sha256,
        args.expected_stage1_all_files_root_sha256,
        args.expected_auditor_id,
    )
    install_authority_snapshot = directory_snapshot(install_authority_dir)
    install_authority, _ = parse_install_authority(
        install_authority_snapshot,
        args.expected_install_authority_manifest_sha256,
        args.expected_install_authority_auditor_id,
        args.expected_audit_manifest_sha256,
        args.expected_auditor_id,
    )
    consumption_key, consumption_raw = materialization_ledger_record(
        args.expected_stage1_root,
        args.expected_stage1_seal_sha256,
        args.expected_stage1_all_files_root_sha256,
        args.expected_audit_manifest_sha256,
        args.expected_auditor_id,
        args.expected_install_authority_manifest_sha256,
        args.expected_install_authority_auditor_id,
        output_absolute,
    )
    if (directory_snapshot(stage1_dir) != stage1_snapshot
            or directory_snapshot(audit_dir) != audit_snapshot
            or directory_snapshot(install_authority_dir) != install_authority_snapshot):
        raise Refuse("input_changed_before_authority_consumption")
    consumption_lease = consume_materialization_authority(
        consumption_key, consumption_raw,
    )
    try:
        validate_ledger_lease(consumption_lease)
        header = build_header(
            args.expected_stage1_root,
            args.expected_stage1_seal_sha256,
            args.expected_stage1_all_files_root_sha256,
            args.expected_audit_manifest_sha256,
            args.expected_auditor_id,
            args.expected_install_authority_manifest_sha256,
            args.expected_install_authority_auditor_id,
            consumption_key,
            consumption_lease.path,
            consumption_raw,
            stage1_snapshot,
            stage1_subjects,
            upstream,
            audit,
            install_authority,
        )
        staging.mkdir(mode=0o700, parents=False, exist_ok=False)
        try:
            created: list[tuple[str, bytes]] = []
            for name in COPY_TO_STAGE2:
                raw = stage1_subjects[name]
                exclusive_write(staging / name, raw)
                created.append((name, raw))
            exclusive_write(staging / "POST_AUDIT_BINDINGS_TEMPLATE_v3r30.h", header)
            created.append(("POST_AUDIT_BINDINGS_TEMPLATE_v3r30.h", header))
            boundary = (json.dumps({
                "schema": "kira.r25.medical_reference_proxy.v3r30.stage2_authority_boundary.v1",
                "status": "MATERIALIZED_SOURCE_ONLY_PENDING_DIFFERENT_AUDIT_B",
                "stage1_package_root_sha256": args.expected_stage1_root,
                "stage1_seal_sha256": args.expected_stage1_seal_sha256,
                "stage1_all_files_root_sha256": args.expected_stage1_all_files_root_sha256,
                "audit_a_manifest_sha256": args.expected_audit_manifest_sha256,
                "audit_a_auditor_id": args.expected_auditor_id,
                "program_data_install_authority_manifest_sha256": args.expected_install_authority_manifest_sha256,
                "program_data_install_authority_auditor_id": args.expected_install_authority_auditor_id,
                "materialization_consumption_key_sha256": consumption_key,
                "materialization_consumed_ledger_path": str(consumption_lease.path),
                "materialization_consumed_ledger_bytes": len(consumption_raw),
                "materialization_consumed_ledger_sha256": sha256(consumption_raw),
                "materialization_consumed_program_data_anchor_exact_dacl": EXPECTED_PROGRAM_DATA_SDDL,
                "materialization_consumed_program_data_delete_child_access_refused": True,
                "materialization_consumed_anchor_and_ledger_directory_held": True,
                "materialization_consumed_ledger_directory_nt_rootdirectory_relative": True,
                "materialization_consumed_ledger_file_nt_rootdirectory_relative": True,
                "materialization_consumed_final_owner_rights_dacls_atomic_at_creation": True,
                "materialization_consumed_file_read_only_directory_append_only_dacls": True,
                "installed_stage2_root": str(INSTALLED_STAGE2_ROOT),
                "installed_anchor_path": str(INSTALLED_ANCHOR_PATH),
                "blender_authority": "NONE",
                "maximum_future_invocations_after_audit_b_acceptance": 1,
                "audit_b_external_native_exe_sha256_required": True,
            }, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
            exclusive_write(staging / "STAGE2_AUTHORITY_BOUNDARY.json", boundary)
            created.append(("STAGE2_AUTHORITY_BOUNDARY.json", boundary))
            manifest_lines = ["path\tbytes\tsha256"]
            for name, raw in sorted(created):
                manifest_lines.append(f"{name}\t{len(raw)}\t{sha256(raw)}")
            manifest = ("\n".join(manifest_lines) + "\n").encode("utf-8")
            exclusive_write(staging / "STAGE2_MATERIALIZATION_MANIFEST.tsv", manifest)
            if (directory_snapshot(stage1_dir) != stage1_snapshot or
                    directory_snapshot(audit_dir) != audit_snapshot or
                    directory_snapshot(install_authority_dir) != install_authority_snapshot):
                raise Refuse("input_changed_during_materialization")
            validate_ledger_lease(consumption_lease)
            staging.rename(output_absolute)
            validate_ledger_lease(consumption_lease)
        except BaseException:
            if staging.exists():
                for child in staging.iterdir():
                    if not child.is_file() or child.is_symlink():
                        raise Refuse("unexpected_staging_entry:" + str(child))
                    child.unlink()
                staging.rmdir()
            raise
        print("V3R30_STAGE2_SOURCE_MATERIALIZED_NO_EXECUTION_AUTHORITY:" + sha256(manifest))
        return 0
    finally:
        consumption_lease.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, Refuse) as error:
        print("V3R30_MATERIALIZATION_REFUSED:" + type(error).__name__ + ":" + str(error))
        raise SystemExit(73)
