#!/usr/bin/env python3
from __future__ import annotations

"""Attempt-04r3 wrapper: immutable image seal plus one-shot runtime lease.

The checked-in config is deliberately unsealed.  A future append-only sealed
successor may contain only immutable native-executable identity.  Audit and
process-instance data arrive in one controller-owned lease.  Before runtime,
AFES input, or Blend access, this wrapper verifies its named-pipe server is the
OS parent, proves the parent's actual mapped main image against a held file
handle, exact-parses the carried audit subject, and binds the exact child.
"""

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import types

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_semantic_control_cage_diagnostic_v4r3.json"
)
SCHEMA = "kira.avatar.r25.semantic_control_cage_diagnostic.v4r3"
ATTEMPT_ID = "attempt_04r3_static_unsealed"
PREPARATION_STATUS = (
    "STATIC_PREPARATION_ONLY_IMMUTABLE_NATIVE_IMAGE_UNRESOLVED_EXECUTION_FORBIDDEN"
)
SEALED_STATUS = "SEALED_IMMUTABLE_NATIVE_IMAGE_ONLY_AFTER_ACCEPTED_04R3_STATIC_AUDIT"
STATIC_NATIVE_STATE = "SEALED_IMMUTABLE_NATIVE_EXECUTABLE_IDENTITY"
AUDIT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/"
    "attempt_04r3/INDEPENDENT_AUDIT.json"
)
AUDIT_SCHEMA = "kira.avatar.r25.semantic_control_cage_independent_audit.v4r3"
AUDIT_DECISION = {
    "status": "ACCEPTED_STATIC_IMMUTABLE_IMAGE_AND_RUNTIME_LEASE_SPLIT",
    "current_preparation_execution_authorized": False,
    "new_append_only_sealed_successor_plan_permitted": True,
}
AUDITOR_IDENTITY = {
    "independent_of_attempt04r3_authorship": True,
    "did_not_run_native_controller_blender_afes_or_semantic_wrapper": True,
    "did_not_create_result_outcome_or_evidence": True,
}
AUDIT_TRUTH = [
    "STATIC_CONFIG_HAS_ONLY_IMMUTABLE_NATIVE_EXECUTABLE_IDENTITY",
    "AUDIT_HASH_AND_RUNTIME_INSTANCE_STATE_ARE_OUT_OF_BAND",
    "EXACT_NATIVE_CONTROLLER_PERSISTENT_LEASE_IMPLEMENTATION_REVIEWED",
    "MAPPED_MAIN_IMAGE_PROOF_REQUIRED_BEFORE_RUNTIME_INPUT_OR_BLEND",
    "STATIC_ACCEPTANCE_IS_NOT_EXECUTION_AUTHORITY",
]
AUDIT_LEASE_REVIEW = {
    "authority_owner": "EXACT_INDEPENDENTLY_AUDITED_NATIVE_CONTROLLER_EXECUTABLE",
    "persistent_exclusive_state_required": True,
    "fresh_lease_id_and_nonce_per_reserved_child_required": True,
    "reservation_persisted_before_child_resume_required": True,
    "lease_and_nonce_marked_consumed_before_capability_write_required": True,
    "second_issue_or_replay_refused_by_native_authority_required": True,
    "cross_child_reissue_refused_by_native_authority_required": True,
    "child_local_replay_ledger_is_not_authority": True,
}
AUDIT_KEYS = {
    "schema", "authoritative_decision", "auditor", "subject_manifest",
    "native_controller_executable_binding", "native_runtime_lease_review",
    "findings", "truth_boundary",
}
SUBJECT_PATHS = {
    "attempt04r3_config": CONFIG_RELATIVE_PATH,
    "attempt04r1_adapter_dependency": (
        "tools/kira_r25_semantic_control_cage_afes_v3r3_adapter_v4r1.py"
    ),
    "attempt04r3_wrapper": (
        "tools/blender_diagnose_kira_r25_semantic_control_cage_v4r3.py"
    ),
    "attempt04r3_controller_planner": (
        "tools/run_kira_r25_semantic_control_cage_v4r3.py"
    ),
    "attempt04r3_test": "Testing/test_kira_r25_semantic_control_cage_attempt04r3.py",
    "attempt04r3_checkpoint": (
        "RecoverySprint/continuation_20260809/"
        "kira_r25_semantic_cage_correspondence_static_preparation/"
        "attempt_04r3/CHECKPOINT.md"
    ),
    "attempt04r2_rejection_audit": (
        "RecoverySprint/continuation_20260809/"
        "kira_r25_semantic_cage_correspondence_static_preparation/"
        "attempt_04r2/INDEPENDENT_AUDIT.md"
    ),
}
STATIC_NATIVE_KEYS = {
    "state", "final_image_path", "bytes", "sha256", "volume_serial_number",
    "file_id_128_hex", "image_file_creation_time_100ns",
}
OBSERVED_PARENT_KEYS = {
    "process_id", "process_creation_time_100ns", "windows_session_id",
    "process_image_device_path", "mapped_image_device_path",
    "held_image_device_path", "final_image_path", "bytes", "sha256",
    "volume_serial_number", "file_id_128_hex", "image_file_creation_time_100ns",
}
CAPABILITY_SCHEMA = (
    "kira.avatar.r25.semantic_control_cage_native_runtime_lease_capability.v4r3"
)
CAPABILITY_STATUS = "AUDITED_NATIVE_CONTROLLER_ONE_SHOT_LEASE_ISSUED"
CAPABILITY_KEYS = {
    "schema", "status", "config_sha256", "wrapper_sha256",
    "native_controller_sha256", "accepted_audit_path",
    "accepted_audit_sha256", "accepted_audit_subject",
    "native_controller_process_id", "native_controller_process_creation_time_100ns",
    "native_controller_session_id", "native_controller_process_image_device_path",
    "native_controller_mapped_image_device_path", "intended_child_process_id",
    "intended_child_process_creation_time_100ns", "runtime_lease", "handles",
    "input_frames", "one_frame_then_eof", "truth_boundary",
}
RUNTIME_LEASE_SCHEMA = "kira.avatar.r25.native_controller_persistent_one_shot_lease.v1"
RUNTIME_LEASE_STATUS = "EXCLUSIVELY_RESERVED_AND_CONSUMED_BEFORE_CHILD_RESUME"
RUNTIME_LEASE_KEYS = {
    "schema", "status", "authority_owner", "lease_id", "one_shot_nonce",
    "capability_pipe_instance_id", "persistent_exclusive_reservation_acquired",
    "reservation_persisted_before_child_resume",
    "lease_and_nonce_consumed_before_capability_write",
    "second_issue_or_replay_refused", "cross_child_reissue_refused",
    "child_wrapper_replay_ledger_authority",
}
CAPABILITY_TRUTH = [
    "EXACT_AUDITED_NATIVE_EXECUTABLE_OWNS_PERSISTENT_ONE_SHOT_STATE",
    "NAMED_PIPE_SERVER_IS_THE_OS_PARENT_AND_THIS_EXACT_PIPE_INSTANCE",
    "PARENT_MAPPED_MAIN_IMAGE_EQUALS_HELD_STATIC_BOUND_IMAGE",
    "AUDIT_PATH_HASH_AND_CANONICAL_SUBJECT_WERE_SUPPLIED_OUT_OF_BAND",
    "RUNTIME_PARENT_AND_CHILD_PROCESS_INSTANCES_ARE_LIVE_OS_OBSERVATIONS",
    "ONE_FRAME_ONE_READ_THEN_EOF_NO_CHILD_LOCAL_CROSS_PROCESS_LEDGER_CLAIM",
    "NO_BODY_RUNTIME_DEFORMATION_ASSIGNMENT_OR_PUBLICATION_AUTHORITY",
]
MAX_INPUT_FRAMES = 3
FILE_TYPE_PIPE = 3
RECEIPT_MAGIC = b"K25RCPT!"
RECEIPT_VERSION = 1
RECEIPT_HEADER = struct.Struct(">8sIQ32s")
MAX_RECEIPT_PAYLOAD_BYTES = 1024 * 1024
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
SYNCHRONIZE = 0x00100000
GENERIC_READ = 0x80000000
FILE_READ_ATTRIBUTES = 0x0080
FILE_SHARE_READ = 0x00000001
OPEN_EXISTING = 3
FILE_ID_INFO_CLASS = 18
DUPLICATE_SAME_ACCESS = 0x00000002
LIST_MODULES_ALL = 0x03
VOLUME_NAME_DOS = 0x0
VOLUME_NAME_NT = 0x2
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class R25SemanticControlCageV4R3Error(RuntimeError):
    pass


class _DuplicateKey(ValueError):
    pass


class _FileId128(ctypes.Structure):
    _fields_ = [("Identifier", ctypes.c_ubyte * 16)]


class _FileIdInfo(ctypes.Structure):
    _fields_ = [
        ("VolumeSerialNumber", ctypes.c_ulonglong),
        ("FileId", _FileId128),
    ]


class _ParentMappedImageLease:
    def __init__(self, kernel32, process_handle, image_handle, observed):
        self._kernel32 = kernel32
        self._process_handle = process_handle
        self._image_handle = image_handle
        self.observed = observed

    def close(self):
        image, process = self._image_handle, self._process_handle
        self._image_handle = self._process_handle = None
        if image:
            self._kernel32.CloseHandle(image)
        if process:
            self._kernel32.CloseHandle(process)


def _sha256(value):
    return hashlib.sha256(value).hexdigest()


def _hex(value, length):
    return type(value) is str and len(value) == length and all(
        "0" <= character <= "9" or "a" <= character <= "f"
        for character in value
    )


def _hex64(value):
    return _hex(value, 64)


def _canonical_json_bytes(value):
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("nonfinite_constant:" + value)


def _project_file(relative, suffix=None):
    if type(relative) is not str or not relative:
        raise R25SemanticControlCageV4R3Error("project_path_not_text")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise R25SemanticControlCageV4R3Error("unsafe_project_relative_path")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise R25SemanticControlCageV4R3Error("symlink_binding_refused")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise R25SemanticControlCageV4R3Error("binding_escaped_project_root") from exc
    if not resolved.is_file() or (suffix and resolved.suffix.lower() != suffix):
        raise R25SemanticControlCageV4R3Error("binding_file_type_mismatch")
    return resolved


def _row_for(relative):
    path = _project_file(relative)
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "sha256": _sha256(raw)}


def _verified_row(label, row, suffix=None):
    if type(row) is not dict or not {"path", "bytes", "sha256"}.issubset(row):
        raise R25SemanticControlCageV4R3Error("binding_row_invalid:" + label)
    path = _project_file(row["path"], suffix)
    raw = path.read_bytes()
    if type(row["bytes"]) is not int or len(raw) != row["bytes"] or _sha256(raw) != row["sha256"]:
        raise R25SemanticControlCageV4R3Error("binding_drift:" + label)
    return path, raw


def _require_static_native_binding(binding):
    if type(binding) is not dict or set(binding) != STATIC_NATIVE_KEYS:
        raise R25SemanticControlCageV4R3Error("static_native_executable_binding_shape_drift")
    if binding["state"] != STATIC_NATIVE_STATE:
        raise R25SemanticControlCageV4R3Error("static_native_executable_binding_not_sealed")
    if any(type(value) is str and value.startswith("UNRESOLVED_") for value in binding.values()):
        raise R25SemanticControlCageV4R3Error("static_native_executable_binding_contains_sentinel")
    if type(binding["final_image_path"]) is not str or not binding["final_image_path"]:
        raise R25SemanticControlCageV4R3Error("static_native_final_image_path_invalid")
    if type(binding["bytes"]) is not int or binding["bytes"] <= 0:
        raise R25SemanticControlCageV4R3Error("static_native_bytes_invalid")
    if not _hex64(binding["sha256"]):
        raise R25SemanticControlCageV4R3Error("static_native_sha256_invalid")
    if type(binding["volume_serial_number"]) is not int or not 0 <= binding["volume_serial_number"] < 2**64:
        raise R25SemanticControlCageV4R3Error("static_native_volume_invalid")
    if not _hex(binding["file_id_128_hex"], 32):
        raise R25SemanticControlCageV4R3Error("static_native_file_id_invalid")
    if type(binding["image_file_creation_time_100ns"]) is not int or binding["image_file_creation_time_100ns"] <= 0:
        raise R25SemanticControlCageV4R3Error("static_native_image_creation_time_invalid")
    return binding


def _static_identity_sha256(binding):
    return _sha256(_canonical_json_bytes(_require_static_native_binding(binding)))


def _validate_mapped_parent_identity(expected_binding, observed, expected_parent_pid):
    binding = _require_static_native_binding(expected_binding)
    if type(observed) is not dict or set(observed) != OBSERVED_PARENT_KEYS:
        raise R25SemanticControlCageV4R3Error("observed_mapped_parent_identity_shape_drift")
    if type(expected_parent_pid) is not int or expected_parent_pid <= 0:
        raise R25SemanticControlCageV4R3Error("parent_process_id_invalid")
    if observed["process_id"] != expected_parent_pid:
        raise R25SemanticControlCageV4R3Error("native_controller_parent_pid_mismatch")
    for key in STATIC_NATIVE_KEYS - {"state"}:
        if observed[key] != binding[key]:
            raise R25SemanticControlCageV4R3Error("native_controller_static_identity_mismatch:" + key)
    paths = (
        observed["process_image_device_path"],
        observed["mapped_image_device_path"],
        observed["held_image_device_path"],
    )
    if any(type(value) is not str or not value for value in paths):
        raise R25SemanticControlCageV4R3Error("mapped_image_device_path_invalid")
    if not paths[0] == paths[1] == paths[2]:
        raise R25SemanticControlCageV4R3Error("parent_mapped_image_does_not_equal_held_file")
    for key in ("process_creation_time_100ns", "windows_session_id"):
        if type(observed[key]) is not int or observed[key] < (1 if key.endswith("time_100ns") else 0):
            raise R25SemanticControlCageV4R3Error("runtime_parent_field_invalid:" + key)
    return observed


def _filetime_value(value):
    return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)


def _last_error(label):
    raise R25SemanticControlCageV4R3Error(label + ":winerror=" + str(ctypes.get_last_error()))


def _process_creation_time(kernel32, process_handle):
    creation = wintypes.FILETIME()
    exit_time = wintypes.FILETIME()
    kernel = wintypes.FILETIME()
    user = wintypes.FILETIME()
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    if not kernel32.GetProcessTimes(process_handle, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(kernel), ctypes.byref(user)):
        _last_error("GetProcessTimes_failed")
    return _filetime_value(creation)


def _final_path(kernel32, image_handle, flags):
    function = kernel32.GetFinalPathNameByHandleW
    function.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    function.restype = wintypes.DWORD
    needed = int(function(image_handle, None, 0, flags))
    if needed <= 0 or needed > 32768:
        _last_error("GetFinalPathNameByHandleW_size_failed")
    buffer = ctypes.create_unicode_buffer(needed + 1)
    written = int(function(image_handle, buffer, len(buffer), flags))
    if written <= 0 or written >= len(buffer):
        _last_error("GetFinalPathNameByHandleW_failed")
    return buffer.value


def _psapi_path(function, process_handle, address=None):
    buffer = ctypes.create_unicode_buffer(32768)
    function.restype = wintypes.DWORD
    if address is None:
        function.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD]
        written = int(function(process_handle, buffer, len(buffer)))
    else:
        function.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.LPWSTR, wintypes.DWORD]
        written = int(function(process_handle, address, buffer, len(buffer)))
    if written <= 0 or written >= len(buffer):
        _last_error("PSAPI_image_path_query_failed")
    return buffer.value


def _hash_open_image(kernel32, image_handle):
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    current = kernel32.GetCurrentProcess()
    duplicate = wintypes.HANDLE()
    kernel32.DuplicateHandle.argtypes = [
        wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE,
        ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD,
    ]
    kernel32.DuplicateHandle.restype = wintypes.BOOL
    if not kernel32.DuplicateHandle(current, image_handle, current, ctypes.byref(duplicate), 0, False, DUPLICATE_SAME_ACCESS):
        _last_error("DuplicateHandle_image_failed")
    try:
        kernel32.SetFilePointerEx.argtypes = [wintypes.HANDLE, ctypes.c_longlong, ctypes.c_void_p, wintypes.DWORD]
        kernel32.SetFilePointerEx.restype = wintypes.BOOL
        if not kernel32.SetFilePointerEx(duplicate, 0, None, 0):
            _last_error("SetFilePointerEx_failed")
        digest = hashlib.sha256()
        total = 0
        buffer = ctypes.create_string_buffer(1024 * 1024)
        count = wintypes.DWORD()
        kernel32.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        kernel32.ReadFile.restype = wintypes.BOOL
        while True:
            if not kernel32.ReadFile(duplicate, buffer, len(buffer), ctypes.byref(count), None):
                _last_error("ReadFile_image_failed")
            if count.value == 0:
                break
            digest.update(buffer.raw[:count.value])
            total += int(count.value)
        return total, digest.hexdigest()
    finally:
        kernel32.CloseHandle(duplicate)


def _query_and_hold_mapped_parent_identity(parent_pid):
    if os.name != "nt" or type(parent_pid) is not int or parent_pid <= 0:
        raise R25SemanticControlCageV4R3Error("mapped_parent_query_requires_windows_pid")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    process_handle = kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | SYNCHRONIZE, False, parent_pid
    )
    if not process_handle:
        _last_error("OpenProcess_parent_failed")
    image_handle = None
    try:
        kernel32.GetProcessId.argtypes = [wintypes.HANDLE]
        kernel32.GetProcessId.restype = wintypes.DWORD
        if int(kernel32.GetProcessId(process_handle)) != parent_pid:
            raise R25SemanticControlCageV4R3Error("opened_parent_pid_changed")
        modules = (ctypes.c_void_p * 1)()
        needed = wintypes.DWORD()
        psapi.EnumProcessModulesEx.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p), wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD), wintypes.DWORD,
        ]
        psapi.EnumProcessModulesEx.restype = wintypes.BOOL
        if not psapi.EnumProcessModulesEx(process_handle, modules, ctypes.sizeof(modules), ctypes.byref(needed), LIST_MODULES_ALL):
            _last_error("EnumProcessModulesEx_failed")
        if needed.value < ctypes.sizeof(ctypes.c_void_p) or not modules[0]:
            raise R25SemanticControlCageV4R3Error("main_module_unavailable")
        module_path = _psapi_path(psapi.GetModuleFileNameExW, process_handle, modules[0])
        process_image_before = _psapi_path(psapi.GetProcessImageFileNameW, process_handle)
        mapped_before = _psapi_path(psapi.GetMappedFileNameW, process_handle, modules[0])
        kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
        ]
        kernel32.CreateFileW.restype = wintypes.HANDLE
        image_handle = kernel32.CreateFileW(
            module_path, GENERIC_READ | FILE_READ_ATTRIBUTES, FILE_SHARE_READ,
            None, OPEN_EXISTING, 0, None,
        )
        if not image_handle or ctypes.cast(image_handle, ctypes.c_void_p).value == INVALID_HANDLE_VALUE:
            image_handle = None
            _last_error("CreateFileW_mapped_parent_image_failed")
        held_device_path = _final_path(kernel32, image_handle, VOLUME_NAME_NT)
        final_image_path = _final_path(kernel32, image_handle, VOLUME_NAME_DOS)
        process_image_after = _psapi_path(psapi.GetProcessImageFileNameW, process_handle)
        mapped_after = _psapi_path(psapi.GetMappedFileNameW, process_handle, modules[0])
        if process_image_before != process_image_after or mapped_before != mapped_after:
            raise R25SemanticControlCageV4R3Error("mapped_parent_image_changed_during_query")
        info = _FileIdInfo()
        kernel32.GetFileInformationByHandleEx.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD
        ]
        kernel32.GetFileInformationByHandleEx.restype = wintypes.BOOL
        if not kernel32.GetFileInformationByHandleEx(image_handle, FILE_ID_INFO_CLASS, ctypes.byref(info), ctypes.sizeof(info)):
            _last_error("GetFileInformationByHandleEx_failed")
        creation = wintypes.FILETIME()
        kernel32.GetFileTime.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME), ctypes.c_void_p, ctypes.c_void_p
        ]
        kernel32.GetFileTime.restype = wintypes.BOOL
        if not kernel32.GetFileTime(image_handle, ctypes.byref(creation), None, None):
            _last_error("GetFileTime_image_failed")
        session_id = wintypes.DWORD()
        kernel32.ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        kernel32.ProcessIdToSessionId.restype = wintypes.BOOL
        if not kernel32.ProcessIdToSessionId(parent_pid, ctypes.byref(session_id)):
            _last_error("ProcessIdToSessionId_failed")
        image_bytes, image_sha256 = _hash_open_image(kernel32, image_handle)
        observed = {
            "process_id": parent_pid,
            "process_creation_time_100ns": _process_creation_time(kernel32, process_handle),
            "windows_session_id": int(session_id.value),
            "process_image_device_path": process_image_after,
            "mapped_image_device_path": mapped_after,
            "held_image_device_path": held_device_path,
            "final_image_path": final_image_path,
            "bytes": image_bytes, "sha256": image_sha256,
            "volume_serial_number": int(info.VolumeSerialNumber),
            "file_id_128_hex": bytes(info.FileId.Identifier).hex(),
            "image_file_creation_time_100ns": _filetime_value(creation),
        }
        return _ParentMappedImageLease(kernel32, process_handle, image_handle, observed)
    except Exception:
        if image_handle:
            kernel32.CloseHandle(image_handle)
        kernel32.CloseHandle(process_handle)
        raise


def _query_process_creation_time(process_id):
    if os.name != "nt" or type(process_id) is not int or process_id <= 0:
        raise R25SemanticControlCageV4R3Error("process_creation_query_requires_windows_pid")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, process_id)
    if not handle:
        _last_error("OpenProcess_child_failed")
    try:
        return _process_creation_time(kernel32, handle)
    finally:
        kernel32.CloseHandle(handle)


def _pipe_server_pid(raw_handle):
    if os.name != "nt" or type(raw_handle) is not int or raw_handle <= 0:
        raise R25SemanticControlCageV4R3Error("capability_handle_invalid_or_non_windows")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetFileType.argtypes = [wintypes.HANDLE]
    kernel32.GetFileType.restype = wintypes.DWORD
    if int(kernel32.GetFileType(raw_handle)) != FILE_TYPE_PIPE:
        raise R25SemanticControlCageV4R3Error("capability_handle_not_pipe")
    server_pid = wintypes.DWORD()
    function = kernel32.GetNamedPipeServerProcessId
    function.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    function.restype = wintypes.BOOL
    if not function(raw_handle, ctypes.byref(server_pid)):
        _last_error("capability_pipe_server_pid_unavailable")
    return int(server_pid.value)


def _require_pipe(raw_handle):
    if os.name != "nt" or type(raw_handle) is not int or raw_handle <= 0:
        raise R25SemanticControlCageV4R3Error("capability_handle_invalid_or_non_windows")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    if int(kernel32.GetFileType(raw_handle)) != FILE_TYPE_PIPE:
        raise R25SemanticControlCageV4R3Error("capability_handle_not_pipe")


def _adopt_pipe(raw_handle):
    _require_pipe(raw_handle)
    import msvcrt
    try:
        descriptor = msvcrt.open_osfhandle(raw_handle, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    except OSError as exc:
        raise R25SemanticControlCageV4R3Error("capability_pipe_adoption_failed") from exc
    return os.fdopen(descriptor, "rb", buffering=0, closefd=True)


def _read_exact(stream, count, label):
    result = bytearray()
    while len(result) < count:
        block = stream.read(count - len(result))
        if not block:
            raise R25SemanticControlCageV4R3Error(label + "_truncated")
        result.extend(block)
    return bytes(result)


def _read_capability_payload(stream):
    header = _read_exact(stream, RECEIPT_HEADER.size, "capability_header")
    magic, version, payload_length, expected_digest = RECEIPT_HEADER.unpack(header)
    if magic != RECEIPT_MAGIC or version != RECEIPT_VERSION:
        raise R25SemanticControlCageV4R3Error("capability_frame_magic_or_version_invalid")
    if payload_length > MAX_RECEIPT_PAYLOAD_BYTES:
        raise R25SemanticControlCageV4R3Error("capability_payload_too_large")
    raw = _read_exact(stream, payload_length, "capability_payload")
    if hashlib.sha256(raw).digest() != expected_digest:
        raise R25SemanticControlCageV4R3Error("capability_payload_digest_mismatch")
    try:
        payload = json.loads(
            raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except Exception as exc:
        raise R25SemanticControlCageV4R3Error("capability_payload_invalid_json") from exc
    if type(payload) is not dict or _canonical_json_bytes(payload) != raw:
        raise R25SemanticControlCageV4R3Error("capability_payload_not_canonical_object")
    if stream.read(1) != b"":
        raise R25SemanticControlCageV4R3Error("capability_pipe_second_read_or_trailing_frame")
    return payload


def _expected_capability_inputs(expected):
    return [
        {"role": "pair_acceptance", "frame_sha256": expected["pair_acceptance_frame_sha256"]},
        {"role": "run_01", "frame_sha256": expected["run_01_frame_sha256"]},
        {"role": "run_02", "frame_sha256": expected["run_02_frame_sha256"]},
    ]


def _validate_audit_subject(subject, audit_sha256, config_sha256, config):
    if type(subject) is not dict or set(subject) != AUDIT_KEYS:
        raise R25SemanticControlCageV4R3Error("accepted_audit_subject_shape_drift")
    canonical = _canonical_json_bytes(subject)
    if not _hex64(audit_sha256) or _sha256(canonical) != audit_sha256:
        raise R25SemanticControlCageV4R3Error("accepted_audit_subject_sha256_mismatch")
    if subject["schema"] != AUDIT_SCHEMA or subject["authoritative_decision"] != AUDIT_DECISION:
        raise R25SemanticControlCageV4R3Error("accepted_audit_identity_or_decision_drift")
    if subject["auditor"] != AUDITOR_IDENTITY:
        raise R25SemanticControlCageV4R3Error("accepted_auditor_identity_drift")
    if subject["findings"] != {"blocking": []} or subject["truth_boundary"] != AUDIT_TRUTH:
        raise R25SemanticControlCageV4R3Error("accepted_audit_findings_or_truth_drift")
    binding = config["native_semantic_controller_executable_binding"]
    if subject["native_controller_executable_binding"] != binding:
        raise R25SemanticControlCageV4R3Error("accepted_audit_native_binding_drift")
    if subject["native_runtime_lease_review"] != AUDIT_LEASE_REVIEW:
        raise R25SemanticControlCageV4R3Error("accepted_audit_native_lease_review_drift")
    manifest = subject["subject_manifest"]
    if type(manifest) is not dict or set(manifest) != set(SUBJECT_PATHS):
        raise R25SemanticControlCageV4R3Error("accepted_audit_subject_manifest_shape")
    for label, relative in SUBJECT_PATHS.items():
        if manifest[label] != _row_for(relative):
            raise R25SemanticControlCageV4R3Error("accepted_audit_subject_hash_drift:" + label)
    if manifest["attempt04r3_config"]["sha256"] != config_sha256:
        raise R25SemanticControlCageV4R3Error("accepted_audit_config_sha256_mismatch")
    return subject


def _require_native_runtime_lease(lease):
    if type(lease) is not dict or set(lease) != RUNTIME_LEASE_KEYS:
        raise R25SemanticControlCageV4R3Error("native_runtime_lease_shape_drift")
    exact = {
        "schema": RUNTIME_LEASE_SCHEMA,
        "status": RUNTIME_LEASE_STATUS,
        "authority_owner": AUDIT_LEASE_REVIEW["authority_owner"],
        "persistent_exclusive_reservation_acquired": True,
        "reservation_persisted_before_child_resume": True,
        "lease_and_nonce_consumed_before_capability_write": True,
        "second_issue_or_replay_refused": True,
        "cross_child_reissue_refused": True,
        "child_wrapper_replay_ledger_authority": False,
    }
    for key, value in exact.items():
        if lease[key] != value:
            raise R25SemanticControlCageV4R3Error("native_runtime_lease_binding_mismatch:" + key)
    identifiers = (
        lease["lease_id"], lease["one_shot_nonce"],
        lease["capability_pipe_instance_id"],
    )
    if not all(_hex64(value) for value in identifiers) or len(set(identifiers)) != 3:
        raise R25SemanticControlCageV4R3Error("native_runtime_lease_identifiers_invalid")
    return lease


def _validate_capability(
    payload, *, capability_handle, lock_handle, result_handle, config_sha256,
    config, observed_parent, child_pid, child_creation_time_100ns,
):
    if type(payload) is not dict or set(payload) != CAPABILITY_KEYS:
        raise R25SemanticControlCageV4R3Error("capability_payload_shape_drift")
    if payload["schema"] != CAPABILITY_SCHEMA or payload["status"] != CAPABILITY_STATUS:
        raise R25SemanticControlCageV4R3Error("capability_literal_identity_mismatch")
    _require_native_runtime_lease(payload["runtime_lease"])
    _validate_audit_subject(
        payload["accepted_audit_subject"], payload["accepted_audit_sha256"],
        config_sha256, config,
    )
    binding = _require_static_native_binding(
        config["native_semantic_controller_executable_binding"]
    )
    expected = config["afes_v3r3_pair_binding"]["expected_pair_and_analysis"]
    exact = {
        "config_sha256": config_sha256,
        "wrapper_sha256": config["bindings"]["execution_wrapper"]["sha256"],
        "native_controller_sha256": binding["sha256"],
        "accepted_audit_path": AUDIT_RELATIVE_PATH,
        "native_controller_process_id": observed_parent["process_id"],
        "native_controller_process_creation_time_100ns": observed_parent["process_creation_time_100ns"],
        "native_controller_session_id": observed_parent["windows_session_id"],
        "native_controller_process_image_device_path": observed_parent["process_image_device_path"],
        "native_controller_mapped_image_device_path": observed_parent["mapped_image_device_path"],
        "intended_child_process_id": child_pid,
        "intended_child_process_creation_time_100ns": child_creation_time_100ns,
        "handles": {
            "capability": capability_handle, "lock_input": lock_handle,
            "result_output": result_handle,
        },
        "input_frames": _expected_capability_inputs(expected),
        "one_frame_then_eof": True,
        "truth_boundary": CAPABILITY_TRUTH,
    }
    for key, value in exact.items():
        if payload[key] != value:
            raise R25SemanticControlCageV4R3Error("capability_runtime_binding_mismatch:" + key)
    return payload


def _authorize_mapped_parent_and_runtime_lease(
    capability_handle, lock_handle, result_handle, config_sha256, config,
):
    binding = _require_static_native_binding(
        config.get("native_semantic_controller_executable_binding")
    )
    parent_pid = os.getppid()
    if _pipe_server_pid(capability_handle) != parent_pid:
        raise R25SemanticControlCageV4R3Error("capability_pipe_server_is_not_os_parent")
    lease = _query_and_hold_mapped_parent_identity(parent_pid)
    try:
        observed = _validate_mapped_parent_identity(binding, lease.observed, parent_pid)
        child_pid = os.getpid()
        child_creation = _query_process_creation_time(child_pid)
        with _adopt_pipe(capability_handle) as stream:
            payload = _read_capability_payload(stream)
        _validate_capability(
            payload, capability_handle=capability_handle, lock_handle=lock_handle,
            result_handle=result_handle, config_sha256=config_sha256, config=config,
            observed_parent=observed, child_pid=child_pid,
            child_creation_time_100ns=child_creation,
        )
        return payload, lease
    except Exception:
        lease.close()
        raise


def _read_config(expected_sha256):
    if not _hex64(expected_sha256):
        raise R25SemanticControlCageV4R3Error("expected_config_sha256_invalid")
    raw = _project_file(CONFIG_RELATIVE_PATH, ".json").read_bytes()
    if _sha256(raw) != expected_sha256:
        raise R25SemanticControlCageV4R3Error("config_sha256_mismatch")
    try:
        config = json.loads(raw.decode("utf-8", errors="strict"))
    except Exception as exc:
        raise R25SemanticControlCageV4R3Error("config_invalid_json") from exc
    if type(config) is not dict or config.get("schema") != SCHEMA or config.get("attempt_id") != ATTEMPT_ID:
        raise R25SemanticControlCageV4R3Error("config_identity_drift")
    if config.get("status") != SEALED_STATUS:
        if config.get("status") == PREPARATION_STATUS:
            raise R25SemanticControlCageV4R3Error("v4r3_static_preparation_is_not_execution_authority")
        raise R25SemanticControlCageV4R3Error("config_status_drift")
    _require_static_native_binding(config.get("native_semantic_controller_executable_binding"))
    pair = config.get("afes_v3r3_pair_binding")
    if type(pair) is not dict or pair.get("seal_status") != "SEALED_FINAL_INDEPENDENTLY_ACCEPTED_V3R3_PAIR":
        raise R25SemanticControlCageV4R3Error("v3r3_pair_not_sealed")
    if pair.get("required_final_placeholders") or pair.get("expected_pair_and_analysis") is None:
        raise R25SemanticControlCageV4R3Error("v3r3_pair_placeholders_remain")
    return config, raw


def _ambient_module(label, path, raw):
    name = "_kira_private_semantic_v4r3_" + label + "_" + _sha256(raw)[:16]
    if name in sys.modules:
        raise R25SemanticControlCageV4R3Error("private_namespace_preexists:" + label)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    exec(compile(raw, str(path), "exec"), module.__dict__)
    if name in sys.modules:
        raise R25SemanticControlCageV4R3Error("private_module_registered:" + label)
    return module


def _verified_runtime(config):
    bindings = config.get("bindings")
    required = {
        "attempt04r1_config", "attempt04r1_wrapper_runtime", "v3r3_afes_adapter",
        "execution_wrapper", "static_controller", "canonical_receipt_primitive",
    }
    if type(bindings) is not dict or not required.issubset(bindings):
        raise R25SemanticControlCageV4R3Error("required_binding_missing")
    wrapper_path, _ = _verified_row("execution_wrapper", bindings["execution_wrapper"], ".py")
    if wrapper_path != Path(__file__).resolve(strict=True):
        raise R25SemanticControlCageV4R3Error("wrapper_self_binding_mismatch")
    _, legacy_config_raw = _verified_row("attempt04r1_config", bindings["attempt04r1_config"], ".json")
    legacy_path, legacy_raw = _verified_row("attempt04r1_wrapper_runtime", bindings["attempt04r1_wrapper_runtime"], ".py")
    for label, suffix in (
        ("v3r3_afes_adapter", ".py"), ("static_controller", ".py"),
        ("canonical_receipt_primitive", ".py"),
    ):
        _verified_row(label, bindings[label], suffix)
    try:
        base_config = json.loads(legacy_config_raw.decode("utf-8", errors="strict"))
    except Exception as exc:
        raise R25SemanticControlCageV4R3Error("attempt04r1_config_invalid") from exc
    legacy = _ambient_module("attempt04r1_wrapper", legacy_path, legacy_raw)
    runtime, adapter, session, receipt, control, observed = legacy._verified_runtime(base_config)
    for label, row in sorted(bindings.items()):
        suffix = Path(row["path"]).suffix.lower()
        path, raw = _verified_row(label, row, suffix)
        observed["attempt04r3_" + label] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": len(raw), "sha256": _sha256(raw),
        }
    runtime_config = dict(base_config)
    runtime_config["afes_pair_binding"] = config["afes_v3r3_pair_binding"]
    return legacy, runtime, adapter, session, receipt, control, observed, runtime_config


def _arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--capability-handle", required=True)
    parser.add_argument("--lock-handle", required=True)
    parser.add_argument("--result-handle", required=True)
    values = parser.parse_args(argv)
    if not _hex64(values.config_sha256):
        parser.error("config SHA-256 must be 64 lowercase hexadecimal characters")
    try:
        values.capability_handle = int(values.capability_handle, 10)
        values.lock_handle = int(values.lock_handle, 10)
        values.result_handle = int(values.result_handle, 10)
    except ValueError as exc:
        parser.error("handles must be decimal integers: " + str(exc))
    handles = (values.capability_handle, values.lock_handle, values.result_handle)
    if min(handles) <= 0 or len(set(handles)) != 3:
        parser.error("capability, lock, and result handles must be distinct positive integers")
    return values


def main():
    values = _arguments()
    lease = session = receipt = runtime = adapter = control = None
    try:
        config, raw = _read_config(values.config_sha256)
        _, lease = _authorize_mapped_parent_and_runtime_lease(
            values.capability_handle, values.lock_handle, values.result_handle,
            values.config_sha256, config,
        )
        legacy, runtime, adapter, session, receipt, control, observed, runtime_config = _verified_runtime(config)
        details = legacy._read_bundle(values.lock_handle, runtime, receipt)
        proxy = legacy._ControlProxy(control, adapter, details, runtime_config)
        payload = runtime.extract_diagnostic(
            config_sha256=values.config_sha256, config=runtime_config, config_raw=raw,
            receipt=receipt, control=proxy, observed=observed,
            pair_payload=details[0][0], pair_frame_sha256=details[0][1],
            run_payloads=(details[1][0], details[2][0]),
            run_frame_sha256s=(details[1][1], details[2][1]),
        )
        payload["schema"] = "kira.r25.semantic_control_cage_diagnostic.v4r3"
        payload["status"] = "V3R3_BOUND_CONTROL_CAGE_DIAGNOSTIC_COMPUTED_NOT_A_BODY"
        payload["static_native_identity_sha256"] = _static_identity_sha256(
            config["native_semantic_controller_executable_binding"]
        )
        payload.pop("payload_content_sha256", None)
        payload["payload_content_sha256"] = control.canonical_sha256(payload)
        runtime._write_result(values.result_handle, receipt, payload)
        return 0
    except Exception as exc:
        if receipt is not None and runtime is not None:
            try:
                runtime._write_result(values.result_handle, receipt, {
                    "schema": "kira.r25.semantic_control_cage_diagnostic.v4r3",
                    "status": "DIAGNOSTIC_FAILED_NO_CAGE_NO_CANDIDATE",
                    "failure_type": type(exc).__name__, "failure": str(exc),
                    "config_sha256": values.config_sha256,
                })
            except Exception:
                pass
        print("R25_SEMANTIC_CONTROL_CAGE_V4R3_FAILED: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        return 1
    finally:
        if session is not None:
            session.close()
        if lease is not None:
            lease.close()
        receipt = runtime = adapter = control = None


if __name__ == "__main__":
    raise SystemExit(main())
