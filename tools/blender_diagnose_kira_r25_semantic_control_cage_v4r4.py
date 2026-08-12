#!/usr/bin/env python3
from __future__ import annotations

"""Attempt-04r4 wrapper with live relocation-aware parent-image attestation.

The checked-in config is deliberately unsealed.  A future append-only sealed
successor may bind an exact native controller and accepted audit out of band.
Before capability, semantic runtime, AFES input, or Blend access, this wrapper
compares the parent's live mapped PE headers and authority regions to the exact
held executable, normalizing only declared AMD64 DIR64 base relocations.

The frozen 04r3 wrapper remains an exact dependency for already-reviewed JSON,
pipe, lease, and semantic-runtime utilities.  Its rejected path-only mapped-
image authorization is never called.
"""

import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import sys
import types


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FROZEN_V4R3_WRAPPER_RELATIVE_PATH = (
    "tools/blender_diagnose_kira_r25_semantic_control_cage_v4r3.py"
)
FROZEN_V4R3_WRAPPER_SHA256 = (
    "a6a8f849a394faa18999495b57a9ec5ffd530ece3ef9495e960a35e3b9f78d56"
)
CONFIG_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_semantic_control_cage_diagnostic_v4r4.json"
)
SCHEMA = "kira.avatar.r25.semantic_control_cage_diagnostic.v4r4"
ATTEMPT_ID = "attempt_04r4_static_unsealed"
PREPARATION_STATUS = (
    "STATIC_PREPARATION_ONLY_RELOCATION_AWARE_MAPPED_IMAGE_ATTESTATION_"
    "NATIVE_IMAGE_UNRESOLVED_EXECUTION_FORBIDDEN"
)
SEALED_STATUS = (
    "SEALED_RELOCATION_AWARE_MAPPED_IMAGE_ATTESTATION_ONLY_AFTER_"
    "ACCEPTED_04R4_STATIC_AUDIT"
)
STATIC_NATIVE_STATE = "SEALED_IMMUTABLE_NATIVE_EXECUTABLE_IDENTITY"
AUDIT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/"
    "attempt_04r4/INDEPENDENT_AUDIT.json"
)
AUDIT_SCHEMA = "kira.avatar.r25.semantic_control_cage_independent_audit.v4r4"
AUDIT_DECISION = {
    "status": "ACCEPTED_STATIC_LIVE_MAPPED_PE_ATTESTATION_AND_RUNTIME_LEASE_SPLIT",
    "current_preparation_execution_authorized": False,
    "new_append_only_sealed_successor_plan_permitted": True,
}
AUDITOR_IDENTITY = {
    "independent_of_attempt04r4_authorship": True,
    "did_not_run_native_controller_blender_afes_or_semantic_wrapper": True,
    "did_not_create_result_outcome_or_evidence": True,
}
AUDIT_TRUTH = [
    "STATIC_CONFIG_HAS_ONLY_IMMUTABLE_NATIVE_EXECUTABLE_IDENTITY",
    "AUDIT_HASH_AND_RUNTIME_INSTANCE_STATE_ARE_OUT_OF_BAND",
    "EXACT_NATIVE_CONTROLLER_PERSISTENT_LEASE_IMPLEMENTATION_REVIEWED",
    "LIVE_MAPPED_PE_HEADERS_EXECUTABLE_AND_READ_ONLY_AUTHORITY_BYTES_ATTESTED",
    "ONLY_DECLARED_AMD64_DIR64_BASE_RELOCATIONS_ARE_NORMALIZED",
    "CANONICAL_COMPARED_REGION_DIGEST_BOUND_IN_CAPABILITY_AND_RESULT",
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
    "attempt04r4_config": CONFIG_RELATIVE_PATH,
    "attempt04r1_adapter_dependency": (
        "tools/kira_r25_semantic_control_cage_afes_v3r3_adapter_v4r1.py"
    ),
    "attempt04r3_wrapper_dependency": FROZEN_V4R3_WRAPPER_RELATIVE_PATH,
    "attempt04r4_mapped_pe_attestation": (
        "tools/kira_r25_mapped_pe_image_attestation_v4r4.py"
    ),
    "attempt04r4_wrapper": (
        "tools/blender_diagnose_kira_r25_semantic_control_cage_v4r4.py"
    ),
    "attempt04r4_controller_planner": (
        "tools/run_kira_r25_semantic_control_cage_v4r4.py"
    ),
    "attempt04r4_test": (
        "Testing/test_kira_r25_semantic_control_cage_attempt04r4.py"
    ),
    "attempt04r4_checkpoint": (
        "RecoverySprint/continuation_20260809/"
        "kira_r25_semantic_cage_correspondence_static_preparation/"
        "attempt_04r4/CHECKPOINT.md"
    ),
    "attempt04r3_rejection_audit": (
        "RecoverySprint/continuation_20260809/"
        "kira_r25_semantic_cage_correspondence_static_preparation/"
        "attempt_04r3/INDEPENDENT_AUDIT.md"
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
    "mapped_image_attestation",
}
CAPABILITY_SCHEMA = (
    "kira.avatar.r25.semantic_control_cage_native_runtime_lease_capability.v4r4"
)
CAPABILITY_STATUS = "AUDITED_NATIVE_CONTROLLER_ONE_SHOT_LEASE_ISSUED"
CAPABILITY_KEYS = {
    "schema", "status", "config_sha256", "wrapper_sha256",
    "native_controller_sha256", "accepted_audit_path",
    "accepted_audit_sha256", "accepted_audit_subject",
    "native_controller_process_id", "native_controller_process_creation_time_100ns",
    "native_controller_session_id", "native_controller_process_image_device_path",
    "native_controller_mapped_image_device_path",
    "native_controller_mapped_image_attestation", "intended_child_process_id",
    "intended_child_process_creation_time_100ns", "runtime_lease", "handles",
    "input_frames", "one_frame_then_eof", "truth_boundary",
}
CAPABILITY_TRUTH = [
    "EXACT_AUDITED_NATIVE_EXECUTABLE_OWNS_PERSISTENT_ONE_SHOT_STATE",
    "NAMED_PIPE_SERVER_IS_THE_OS_PARENT_AND_THIS_EXACT_PIPE_INSTANCE",
    "PARENT_LIVE_MAPPED_AUTHORITY_BYTES_EQUAL_HELD_PE_AFTER_DECLARED_DIR64_RELOCATIONS",
    "CANONICAL_COMPARED_REGION_DIGEST_IS_BOUND_IN_THIS_CAPABILITY",
    "AUDIT_PATH_HASH_AND_CANONICAL_SUBJECT_WERE_SUPPLIED_OUT_OF_BAND",
    "RUNTIME_PARENT_AND_CHILD_PROCESS_INSTANCES_ARE_LIVE_OS_OBSERVATIONS",
    "ONE_FRAME_ONE_READ_THEN_EOF_NO_CHILD_LOCAL_CROSS_PROCESS_LEDGER_CLAIM",
    "NO_BODY_RUNTIME_DEFORMATION_ASSIGNMENT_OR_PUBLICATION_AUTHORITY",
]

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
SYNCHRONIZE = 0x00100000
GENERIC_READ = 0x80000000
FILE_READ_ATTRIBUTES = 0x0080
FILE_SHARE_READ = 0x00000001
OPEN_EXISTING = 3
FILE_ID_INFO_CLASS = 18
LIST_MODULES_ALL = 0x03
VOLUME_NAME_DOS = 0x0
VOLUME_NAME_NT = 0x2
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
MAX_HELD_PE_BYTES = 128 * 1024 * 1024


class R25SemanticControlCageV4R4Error(RuntimeError):
    pass


def _load_frozen_v4r3():
    path = PROJECT_ROOT / FROZEN_V4R3_WRAPPER_RELATIVE_PATH
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FROZEN_V4R3_WRAPPER_SHA256:
        raise R25SemanticControlCageV4R4Error("frozen_v4r3_wrapper_dependency_drift")
    module = types.ModuleType("_kira_frozen_semantic_wrapper_v4r3_for_v4r4")
    module.__file__ = str(path)
    module.__package__ = None
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


_BASE = _load_frozen_v4r3()
bpy = _BASE.bpy

for _name in (
    "PROJECT_ROOT", "CONFIG_RELATIVE_PATH", "SCHEMA", "ATTEMPT_ID",
    "PREPARATION_STATUS", "SEALED_STATUS", "STATIC_NATIVE_STATE",
    "AUDIT_RELATIVE_PATH", "AUDIT_SCHEMA", "AUDIT_DECISION",
    "AUDITOR_IDENTITY", "AUDIT_TRUTH", "AUDIT_LEASE_REVIEW", "AUDIT_KEYS",
    "SUBJECT_PATHS", "STATIC_NATIVE_KEYS", "OBSERVED_PARENT_KEYS",
    "CAPABILITY_SCHEMA", "CAPABILITY_STATUS", "CAPABILITY_KEYS",
    "CAPABILITY_TRUTH",
):
    setattr(_BASE, _name, globals()[_name])
_BASE.__file__ = __file__
_BASE.R25SemanticControlCageV4R3Error = R25SemanticControlCageV4R4Error

RUNTIME_LEASE_SCHEMA = _BASE.RUNTIME_LEASE_SCHEMA
RUNTIME_LEASE_STATUS = _BASE.RUNTIME_LEASE_STATUS
RUNTIME_LEASE_KEYS = _BASE.RUNTIME_LEASE_KEYS
RECEIPT_MAGIC = _BASE.RECEIPT_MAGIC
RECEIPT_VERSION = _BASE.RECEIPT_VERSION
RECEIPT_HEADER = _BASE.RECEIPT_HEADER
MAX_RECEIPT_PAYLOAD_BYTES = _BASE.MAX_RECEIPT_PAYLOAD_BYTES

_sha256 = _BASE._sha256
_hex = _BASE._hex
_hex64 = _BASE._hex64
_canonical_json_bytes = _BASE._canonical_json_bytes
_unique_object = _BASE._unique_object
_reject_constant = _BASE._reject_constant
_project_file = _BASE._project_file
_row_for = _BASE._row_for
_verified_row = _BASE._verified_row
_require_static_native_binding = _BASE._require_static_native_binding
_static_identity_sha256 = _BASE._static_identity_sha256
_filetime_value = _BASE._filetime_value
_last_error = _BASE._last_error
_process_creation_time = _BASE._process_creation_time
_final_path = _BASE._final_path
_psapi_path = _BASE._psapi_path
_query_process_creation_time = _BASE._query_process_creation_time
_pipe_server_pid = _BASE._pipe_server_pid
_require_pipe = _BASE._require_pipe
_adopt_pipe = _BASE._adopt_pipe
_read_exact = _BASE._read_exact
_read_capability_payload = _BASE._read_capability_payload
_expected_capability_inputs = _BASE._expected_capability_inputs
_require_native_runtime_lease = _BASE._require_native_runtime_lease
_arguments = _BASE._arguments


class _FileId128(ctypes.Structure):
    _fields_ = [("Identifier", ctypes.c_ubyte * 16)]


class _FileIdInfo(ctypes.Structure):
    _fields_ = [
        ("VolumeSerialNumber", ctypes.c_ulonglong),
        ("FileId", _FileId128),
    ]


class _ModuleInfo(ctypes.Structure):
    _fields_ = [
        ("lpBaseOfDll", ctypes.c_void_p),
        ("SizeOfImage", wintypes.DWORD),
        ("EntryPoint", ctypes.c_void_p),
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


def _ambient_module(label, path, raw):
    name = "_kira_private_semantic_v4r4_" + label + "_" + _sha256(raw)[:16]
    if name in sys.modules:
        raise R25SemanticControlCageV4R4Error("private_namespace_preexists:" + label)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    exec(compile(raw, str(path), "exec"), module.__dict__)
    if name in sys.modules:
        raise R25SemanticControlCageV4R4Error("private_module_registered:" + label)
    return module


def _load_attestation_helper(config):
    bindings = config.get("bindings")
    if type(bindings) is not dict or "mapped_pe_attestation" not in bindings:
        raise R25SemanticControlCageV4R4Error("mapped_pe_attestation_binding_missing")
    path, raw = _verified_row(
        "mapped_pe_attestation", bindings["mapped_pe_attestation"], ".py"
    )
    return _ambient_module("mapped_pe_attestation", path, raw)


def _read_open_image_bytes(kernel32, image_handle):
    size = ctypes.c_longlong()
    kernel32.GetFileSizeEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_longlong)]
    kernel32.GetFileSizeEx.restype = wintypes.BOOL
    if not kernel32.GetFileSizeEx(image_handle, ctypes.byref(size)):
        _last_error("GetFileSizeEx_image_failed")
    if not 512 <= size.value <= MAX_HELD_PE_BYTES:
        raise R25SemanticControlCageV4R4Error("held_pe_file_size_invalid")
    kernel32.SetFilePointerEx.argtypes = [
        wintypes.HANDLE, ctypes.c_longlong, ctypes.c_void_p, wintypes.DWORD,
    ]
    kernel32.SetFilePointerEx.restype = wintypes.BOOL
    if not kernel32.SetFilePointerEx(image_handle, 0, None, 0):
        _last_error("SetFilePointerEx_image_failed")
    kernel32.ReadFile.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p,
    ]
    kernel32.ReadFile.restype = wintypes.BOOL
    result = bytearray()
    while len(result) < size.value:
        count = min(1024 * 1024, size.value - len(result))
        buffer = ctypes.create_string_buffer(count)
        read = wintypes.DWORD()
        if not kernel32.ReadFile(image_handle, buffer, count, ctypes.byref(read), None):
            _last_error("ReadFile_held_pe_failed")
        if read.value == 0:
            raise R25SemanticControlCageV4R4Error("ReadFile_held_pe_truncated")
        result.extend(buffer.raw[:read.value])
    if len(result) != size.value:
        raise R25SemanticControlCageV4R4Error("ReadFile_held_pe_length_mismatch")
    return bytes(result)


def _read_remote_exact(kernel32, process_handle, address, count, label):
    if (
        type(address) is not int or address <= 0 or type(count) is not int
        or count <= 0 or count > MAX_HELD_PE_BYTES
    ):
        raise R25SemanticControlCageV4R4Error("ReadProcessMemory_range_invalid:" + label)
    function = kernel32.ReadProcessMemory
    function.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    function.restype = wintypes.BOOL
    result = bytearray()
    while len(result) < count:
        chunk = min(1024 * 1024, count - len(result))
        buffer = ctypes.create_string_buffer(chunk)
        read = ctypes.c_size_t()
        if not function(
            process_handle, ctypes.c_void_p(address + len(result)), buffer,
            chunk, ctypes.byref(read),
        ):
            _last_error("ReadProcessMemory_failed:" + label)
        if read.value != chunk:
            raise R25SemanticControlCageV4R4Error(
                "ReadProcessMemory_short_read:" + label
            )
        result.extend(buffer.raw[:chunk])
    return bytes(result)


def _query_and_hold_mapped_parent_identity(parent_pid, attestation_helper):
    if os.name != "nt" or type(parent_pid) is not int or parent_pid <= 0:
        raise R25SemanticControlCageV4R4Error("mapped_parent_query_requires_windows_pid")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    process_handle = kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | SYNCHRONIZE,
        False, parent_pid,
    )
    if not process_handle:
        _last_error("OpenProcess_parent_failed")
    image_handle = None
    try:
        kernel32.GetProcessId.argtypes = [wintypes.HANDLE]
        kernel32.GetProcessId.restype = wintypes.DWORD
        if int(kernel32.GetProcessId(process_handle)) != parent_pid:
            raise R25SemanticControlCageV4R4Error("opened_parent_pid_changed")
        modules = (ctypes.c_void_p * 1)()
        needed = wintypes.DWORD()
        psapi.EnumProcessModulesEx.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p), wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD), wintypes.DWORD,
        ]
        psapi.EnumProcessModulesEx.restype = wintypes.BOOL
        if not psapi.EnumProcessModulesEx(
            process_handle, modules, ctypes.sizeof(modules),
            ctypes.byref(needed), LIST_MODULES_ALL,
        ):
            _last_error("EnumProcessModulesEx_failed")
        module_base = int(modules[0] or 0)
        if needed.value < ctypes.sizeof(ctypes.c_void_p) or not module_base:
            raise R25SemanticControlCageV4R4Error("main_module_unavailable")
        module_info = _ModuleInfo()
        psapi.GetModuleInformation.argtypes = [
            wintypes.HANDLE, ctypes.c_void_p, ctypes.POINTER(_ModuleInfo),
            wintypes.DWORD,
        ]
        psapi.GetModuleInformation.restype = wintypes.BOOL
        if not psapi.GetModuleInformation(
            process_handle, ctypes.c_void_p(module_base),
            ctypes.byref(module_info), ctypes.sizeof(module_info),
        ):
            _last_error("GetModuleInformation_failed")
        if int(module_info.lpBaseOfDll or 0) != module_base:
            raise R25SemanticControlCageV4R4Error("main_module_base_mismatch")

        module_path = _psapi_path(
            psapi.GetModuleFileNameExW, process_handle, ctypes.c_void_p(module_base)
        )
        process_image_before = _psapi_path(
            psapi.GetProcessImageFileNameW, process_handle
        )
        mapped_before = _psapi_path(
            psapi.GetMappedFileNameW, process_handle, ctypes.c_void_p(module_base)
        )
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
        held_raw = _read_open_image_bytes(kernel32, image_handle)

        module_size = int(module_info.SizeOfImage)
        module_entry = int(module_info.EntryPoint or 0)

        def remote_reader(rva, size):
            if (
                type(rva) is not int or type(size) is not int or rva < 0
                or size <= 0 or rva + size > module_size
            ):
                raise R25SemanticControlCageV4R4Error(
                    "remote_reader_outside_reported_module"
                )
            return _read_remote_exact(
                kernel32, process_handle, module_base + rva, size,
                "main_module_rva_" + format(rva, "x"),
            )

        mapped_attestation = attestation_helper._attest_loaded_main_image(
            held_raw, remote_module_base=module_base,
            module_size_of_image=module_size, module_entry_point=module_entry,
            remote_reader=remote_reader,
        )

        modules_after = (ctypes.c_void_p * 1)()
        needed_after = wintypes.DWORD()
        if not psapi.EnumProcessModulesEx(
            process_handle, modules_after, ctypes.sizeof(modules_after),
            ctypes.byref(needed_after), LIST_MODULES_ALL,
        ):
            _last_error("EnumProcessModulesEx_after_attestation_failed")
        info_after = _ModuleInfo()
        if not psapi.GetModuleInformation(
            process_handle, modules_after[0], ctypes.byref(info_after),
            ctypes.sizeof(info_after),
        ):
            _last_error("GetModuleInformation_after_attestation_failed")
        process_image_after = _psapi_path(
            psapi.GetProcessImageFileNameW, process_handle
        )
        mapped_after = _psapi_path(
            psapi.GetMappedFileNameW, process_handle, modules_after[0]
        )
        if (
            int(modules_after[0] or 0) != module_base
            or int(info_after.lpBaseOfDll or 0) != module_base
            or int(info_after.SizeOfImage) != module_size
            or int(info_after.EntryPoint or 0) != module_entry
            or process_image_before != process_image_after
            or mapped_before != mapped_after
        ):
            raise R25SemanticControlCageV4R4Error(
                "mapped_parent_image_changed_during_attestation"
            )

        info = _FileIdInfo()
        kernel32.GetFileInformationByHandleEx.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ]
        kernel32.GetFileInformationByHandleEx.restype = wintypes.BOOL
        if not kernel32.GetFileInformationByHandleEx(
            image_handle, FILE_ID_INFO_CLASS, ctypes.byref(info), ctypes.sizeof(info)
        ):
            _last_error("GetFileInformationByHandleEx_failed")
        creation = wintypes.FILETIME()
        kernel32.GetFileTime.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME),
            ctypes.c_void_p, ctypes.c_void_p,
        ]
        kernel32.GetFileTime.restype = wintypes.BOOL
        if not kernel32.GetFileTime(image_handle, ctypes.byref(creation), None, None):
            _last_error("GetFileTime_image_failed")
        session_id = wintypes.DWORD()
        kernel32.ProcessIdToSessionId.argtypes = [
            wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.ProcessIdToSessionId.restype = wintypes.BOOL
        if not kernel32.ProcessIdToSessionId(parent_pid, ctypes.byref(session_id)):
            _last_error("ProcessIdToSessionId_failed")
        observed = {
            "process_id": parent_pid,
            "process_creation_time_100ns": _process_creation_time(
                kernel32, process_handle
            ),
            "windows_session_id": int(session_id.value),
            "process_image_device_path": process_image_after,
            "mapped_image_device_path": mapped_after,
            "held_image_device_path": held_device_path,
            "final_image_path": final_image_path,
            "bytes": len(held_raw), "sha256": _sha256(held_raw),
            "volume_serial_number": int(info.VolumeSerialNumber),
            "file_id_128_hex": bytes(info.FileId.Identifier).hex(),
            "image_file_creation_time_100ns": _filetime_value(creation),
            "mapped_image_attestation": mapped_attestation,
        }
        return _ParentMappedImageLease(
            kernel32, process_handle, image_handle, observed
        )
    except Exception:
        if image_handle:
            kernel32.CloseHandle(image_handle)
        kernel32.CloseHandle(process_handle)
        raise


def _validate_mapped_parent_identity(
    expected_binding, observed, expected_parent_pid, attestation_helper,
):
    binding = _require_static_native_binding(expected_binding)
    if type(observed) is not dict or set(observed) != OBSERVED_PARENT_KEYS:
        raise R25SemanticControlCageV4R4Error(
            "observed_mapped_parent_identity_shape_drift"
        )
    if type(expected_parent_pid) is not int or expected_parent_pid <= 0:
        raise R25SemanticControlCageV4R4Error("parent_process_id_invalid")
    if observed["process_id"] != expected_parent_pid:
        raise R25SemanticControlCageV4R4Error(
            "native_controller_parent_pid_mismatch"
        )
    for key in STATIC_NATIVE_KEYS - {"state"}:
        if observed[key] != binding[key]:
            raise R25SemanticControlCageV4R4Error(
                "native_controller_static_identity_mismatch:" + key
            )
    paths = (
        observed["process_image_device_path"],
        observed["mapped_image_device_path"],
        observed["held_image_device_path"],
    )
    if any(type(value) is not str or not value for value in paths):
        raise R25SemanticControlCageV4R4Error("mapped_image_device_path_invalid")
    if not paths[0] == paths[1] == paths[2]:
        raise R25SemanticControlCageV4R4Error(
            "parent_mapped_image_path_does_not_equal_held_file_path"
        )
    for key in ("process_creation_time_100ns", "windows_session_id"):
        minimum = 1 if key.endswith("time_100ns") else 0
        if type(observed[key]) is not int or observed[key] < minimum:
            raise R25SemanticControlCageV4R4Error(
                "runtime_parent_field_invalid:" + key
            )
    attestation_helper._validate_attestation_shape(
        observed["mapped_image_attestation"], binding["sha256"]
    )
    return observed


def _validate_audit_subject(subject, audit_sha256, config_sha256, config):
    if type(subject) is not dict or set(subject) != AUDIT_KEYS:
        raise R25SemanticControlCageV4R4Error("accepted_audit_subject_shape_drift")
    canonical = _canonical_json_bytes(subject)
    if not _hex64(audit_sha256) or _sha256(canonical) != audit_sha256:
        raise R25SemanticControlCageV4R4Error(
            "accepted_audit_subject_sha256_mismatch"
        )
    if (
        subject["schema"] != AUDIT_SCHEMA
        or subject["authoritative_decision"] != AUDIT_DECISION
    ):
        raise R25SemanticControlCageV4R4Error(
            "accepted_audit_identity_or_decision_drift"
        )
    if subject["auditor"] != AUDITOR_IDENTITY:
        raise R25SemanticControlCageV4R4Error("accepted_auditor_identity_drift")
    if (
        subject["findings"] != {"blocking": []}
        or subject["truth_boundary"] != AUDIT_TRUTH
    ):
        raise R25SemanticControlCageV4R4Error(
            "accepted_audit_findings_or_truth_drift"
        )
    binding = config["native_semantic_controller_executable_binding"]
    if subject["native_controller_executable_binding"] != binding:
        raise R25SemanticControlCageV4R4Error(
            "accepted_audit_native_binding_drift"
        )
    if subject["native_runtime_lease_review"] != AUDIT_LEASE_REVIEW:
        raise R25SemanticControlCageV4R4Error(
            "accepted_audit_native_lease_review_drift"
        )
    manifest = subject["subject_manifest"]
    if type(manifest) is not dict or set(manifest) != set(SUBJECT_PATHS):
        raise R25SemanticControlCageV4R4Error(
            "accepted_audit_subject_manifest_shape"
        )
    for label, relative in SUBJECT_PATHS.items():
        if manifest[label] != _row_for(relative):
            raise R25SemanticControlCageV4R4Error(
                "accepted_audit_subject_hash_drift:" + label
            )
    if manifest["attempt04r4_config"]["sha256"] != config_sha256:
        raise R25SemanticControlCageV4R4Error(
            "accepted_audit_config_sha256_mismatch"
        )
    return subject


def _validate_capability(
    payload, *, capability_handle, lock_handle, result_handle, config_sha256,
    config, observed_parent, child_pid, child_creation_time_100ns,
):
    if type(payload) is not dict or set(payload) != CAPABILITY_KEYS:
        raise R25SemanticControlCageV4R4Error("capability_payload_shape_drift")
    if payload["schema"] != CAPABILITY_SCHEMA or payload["status"] != CAPABILITY_STATUS:
        raise R25SemanticControlCageV4R4Error("capability_literal_identity_mismatch")
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
        "native_controller_process_creation_time_100ns": observed_parent[
            "process_creation_time_100ns"
        ],
        "native_controller_session_id": observed_parent["windows_session_id"],
        "native_controller_process_image_device_path": observed_parent[
            "process_image_device_path"
        ],
        "native_controller_mapped_image_device_path": observed_parent[
            "mapped_image_device_path"
        ],
        "native_controller_mapped_image_attestation": observed_parent[
            "mapped_image_attestation"
        ],
        "intended_child_process_id": child_pid,
        "intended_child_process_creation_time_100ns": child_creation_time_100ns,
        "handles": {
            "capability": capability_handle, "lock_input": lock_handle,
            "result_output": result_handle,
        },
        "input_frames": _expected_capability_inputs(expected),
        "one_frame_then_eof": True, "truth_boundary": CAPABILITY_TRUTH,
    }
    for key, value in exact.items():
        if payload[key] != value:
            raise R25SemanticControlCageV4R4Error(
                "capability_runtime_binding_mismatch:" + key
            )
    return payload


def _authorize_mapped_parent_and_runtime_lease(
    capability_handle, lock_handle, result_handle, config_sha256, config,
):
    binding = _require_static_native_binding(
        config.get("native_semantic_controller_executable_binding")
    )
    parent_pid = os.getppid()
    if _pipe_server_pid(capability_handle) != parent_pid:
        raise R25SemanticControlCageV4R4Error(
            "capability_pipe_server_is_not_os_parent"
        )
    helper = _load_attestation_helper(config)
    lease = _query_and_hold_mapped_parent_identity(parent_pid, helper)
    try:
        observed = _validate_mapped_parent_identity(
            binding, lease.observed, parent_pid, helper
        )
        child_pid = os.getpid()
        child_creation = _query_process_creation_time(child_pid)
        with _adopt_pipe(capability_handle) as stream:
            payload = _read_capability_payload(stream)
        _validate_capability(
            payload, capability_handle=capability_handle,
            lock_handle=lock_handle, result_handle=result_handle,
            config_sha256=config_sha256, config=config,
            observed_parent=observed, child_pid=child_pid,
            child_creation_time_100ns=child_creation,
        )
        return payload, lease
    except Exception:
        lease.close()
        raise


def _read_config(expected_sha256):
    if not _hex64(expected_sha256):
        raise R25SemanticControlCageV4R4Error("expected_config_sha256_invalid")
    raw = _project_file(CONFIG_RELATIVE_PATH, ".json").read_bytes()
    if _sha256(raw) != expected_sha256:
        raise R25SemanticControlCageV4R4Error("config_sha256_mismatch")
    try:
        config = _BASE.json.loads(raw.decode("utf-8", errors="strict"))
    except Exception as exc:
        raise R25SemanticControlCageV4R4Error("config_invalid_json") from exc
    if (
        type(config) is not dict or config.get("schema") != SCHEMA
        or config.get("attempt_id") != ATTEMPT_ID
    ):
        raise R25SemanticControlCageV4R4Error("config_identity_drift")
    if config.get("status") != SEALED_STATUS:
        if config.get("status") == PREPARATION_STATUS:
            raise R25SemanticControlCageV4R4Error(
                "v4r4_static_preparation_is_not_execution_authority"
            )
        raise R25SemanticControlCageV4R4Error("config_status_drift")
    _require_static_native_binding(
        config.get("native_semantic_controller_executable_binding")
    )
    pair = config.get("afes_v3r3_pair_binding")
    if (
        type(pair) is not dict
        or pair.get("seal_status")
        != "SEALED_FINAL_INDEPENDENTLY_ACCEPTED_V3R3_PAIR"
    ):
        raise R25SemanticControlCageV4R4Error("v3r3_pair_not_sealed")
    if pair.get("required_final_placeholders") or pair.get(
        "expected_pair_and_analysis"
    ) is None:
        raise R25SemanticControlCageV4R4Error("v3r3_pair_placeholders_remain")
    return config, raw


def _verified_runtime(config):
    bindings = config.get("bindings")
    required = {
        "attempt04r1_config", "attempt04r1_wrapper_runtime", "v3r3_afes_adapter",
        "mapped_pe_attestation", "execution_wrapper", "static_controller",
        "canonical_receipt_primitive", "attempt04r3_wrapper_dependency",
        "attempt04r3_rejection_audit",
    }
    if type(bindings) is not dict or not required.issubset(bindings):
        raise R25SemanticControlCageV4R4Error("required_binding_missing")
    wrapper_path, _ = _verified_row(
        "execution_wrapper", bindings["execution_wrapper"], ".py"
    )
    if wrapper_path != Path(__file__).resolve(strict=True):
        raise R25SemanticControlCageV4R4Error("wrapper_self_binding_mismatch")
    _, legacy_config_raw = _verified_row(
        "attempt04r1_config", bindings["attempt04r1_config"], ".json"
    )
    legacy_path, legacy_raw = _verified_row(
        "attempt04r1_wrapper_runtime",
        bindings["attempt04r1_wrapper_runtime"], ".py",
    )
    for label, suffix in (
        ("v3r3_afes_adapter", ".py"), ("mapped_pe_attestation", ".py"),
        ("static_controller", ".py"), ("canonical_receipt_primitive", ".py"),
        ("attempt04r3_wrapper_dependency", ".py"),
        ("attempt04r3_rejection_audit", ".md"),
    ):
        _verified_row(label, bindings[label], suffix)
    try:
        base_config = _BASE.json.loads(
            legacy_config_raw.decode("utf-8", errors="strict")
        )
    except Exception as exc:
        raise R25SemanticControlCageV4R4Error(
            "attempt04r1_config_invalid"
        ) from exc
    legacy = _ambient_module("attempt04r1_wrapper", legacy_path, legacy_raw)
    runtime, adapter, session, receipt, control, observed = legacy._verified_runtime(
        base_config
    )
    for label, row in sorted(bindings.items()):
        suffix = Path(row["path"]).suffix.lower()
        path, raw = _verified_row(label, row, suffix)
        observed["attempt04r4_" + label] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": len(raw), "sha256": _sha256(raw),
        }
    runtime_config = dict(base_config)
    runtime_config["afes_pair_binding"] = config["afes_v3r3_pair_binding"]
    return legacy, runtime, adapter, session, receipt, control, observed, runtime_config


def main():
    values = _arguments()
    lease = session = receipt = runtime = adapter = control = None
    try:
        config, raw = _read_config(values.config_sha256)
        _, lease = _authorize_mapped_parent_and_runtime_lease(
            values.capability_handle, values.lock_handle, values.result_handle,
            values.config_sha256, config,
        )
        mapped_attestation = lease.observed["mapped_image_attestation"]
        (
            legacy, runtime, adapter, session, receipt, control, observed,
            runtime_config,
        ) = _verified_runtime(config)
        details = legacy._read_bundle(values.lock_handle, runtime, receipt)
        proxy = legacy._ControlProxy(control, adapter, details, runtime_config)
        payload = runtime.extract_diagnostic(
            config_sha256=values.config_sha256, config=runtime_config,
            config_raw=raw, receipt=receipt, control=proxy, observed=observed,
            pair_payload=details[0][0], pair_frame_sha256=details[0][1],
            run_payloads=(details[1][0], details[2][0]),
            run_frame_sha256s=(details[1][1], details[2][1]),
        )
        payload["schema"] = "kira.r25.semantic_control_cage_diagnostic.v4r4"
        payload["status"] = (
            "V3R3_BOUND_CONTROL_CAGE_DIAGNOSTIC_COMPUTED_NOT_A_BODY"
        )
        payload["static_native_identity_sha256"] = _static_identity_sha256(
            config["native_semantic_controller_executable_binding"]
        )
        payload["native_controller_mapped_image_attestation"] = mapped_attestation
        payload.pop("payload_content_sha256", None)
        payload["payload_content_sha256"] = control.canonical_sha256(payload)
        runtime._write_result(values.result_handle, receipt, payload)
        return 0
    except Exception as exc:
        if receipt is not None and runtime is not None:
            try:
                runtime._write_result(values.result_handle, receipt, {
                    "schema": "kira.r25.semantic_control_cage_diagnostic.v4r4",
                    "status": "DIAGNOSTIC_FAILED_NO_CAGE_NO_CANDIDATE",
                    "failure_type": type(exc).__name__, "failure": str(exc),
                    "config_sha256": values.config_sha256,
                })
            except Exception:
                pass
        print(
            "R25_SEMANTIC_CONTROL_CAGE_V4R4_FAILED: "
            + type(exc).__name__ + ": " + str(exc), file=sys.stderr,
        )
        return 1
    finally:
        if session is not None:
            session.close()
        if lease is not None:
            lease.close()
        receipt = runtime = adapter = control = None


if __name__ == "__main__":
    raise SystemExit(main())
