#!/usr/bin/env python3
"""External trust-root bootstrap for static R25 AFES Attempt 08.

This is the only supported future entry route.  It discovers every project
input, opens the complete deny-write/delete lock set, verifies the exact
contract, recursive 35-file child closure, the complete accepted Attempt-07
graph plus its audit and safe-failure evidence, and a future exact structured
audit before privately compiling the controller.
The private compile receives a fresh opaque capability and the exact verified
context; the controller captures both in a one-use closure.
"""

from __future__ import annotations

import argparse
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
from typing import Any, Callable, Iterable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v8.json"
)
AUDIT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution_static_preparation/"
    "attempt_08/INDEPENDENT_AUDIT.json"
)
HEX64 = re.compile(r"[0-9a-f]{64}")
PASSTHROUGH = (
    "SYSTEMROOT", "WINDIR", "USERNAME", "USERPROFILE", "HOMEDRIVE",
    "HOMEPATH", "LOCALAPPDATA", "APPDATA",
)
REQUIRED_MISSING_V2_PATHS = {
    "RecoverySprint/continuation_20260803/kira_r23_cc0_afes_expanded_mask_preparation/KIRA_R23_CC0_AFES_EXPANDED_MASK_PREFLIGHT_CONFIG.json",
    "RecoverySprint/continuation_20260803/kira_r23_cc0_afes_expanded_mask/preflight_attempt_04/PREFLIGHT.json",
    "Avatar/avatar_builder/workspaces/inactive_adult_female_foundations/generic_makehuman_adult_female_foundation_inactive_v1_20260801/ADULT_FOUNDATION_QUALIFICATION_RESULT.json",
    "Avatar/avatar_builder/workspaces/inactive_adult_female_foundations/generic_makehuman_adult_female_foundation_inactive_v1_20260801/INDEPENDENT_ADULT_FOUNDATION_TOPOLOGY_AUDIT_V2.json",
    "Avatar/avatar_builder/workspaces/inactive_adult_female_foundations/generic_makehuman_adult_female_foundation_inactive_v1_20260801/INDEPENDENT_ADULT_FEMALE_RELATIONSHIP_REVIEW_V2.json",
}
PRESERVED_ATTEMPT05 = {
    "contract": {
        "path": "Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_locked_pair_execution_v5.json",
        "bytes": 10841,
        "sha256": "7d7445d2281c1a466acd88d71d5cf94940b358c564db52c67c325ff5403cd142",
    },
    "external_bootstrap": {
        "path": "tools/launch_kira_r25_foundation_afes_locked_pair_v5.py",
        "bytes": 34865,
        "sha256": "0ab300425d6f850e77f8074064028a8e6ec9f2fa5247154bc3b9fd7f86d15c87",
    },
    "private_controller": {
        "path": "tools/run_kira_r25_foundation_afes_locked_pair_v5.py",
        "bytes": 34800,
        "sha256": "e3018488f4de34c36b36a68c806056e68d681ed915a0e2fb6e64c23879831db8",
    },
    "child_wrapper": {
        "path": "tools/blender_extract_kira_r25_foundation_afes_transition_rings_execution_v5.py",
        "bytes": 11906,
        "sha256": "fb35b3469b7aeaacc47d3f914b9bf221bb4bd80ebd1d25d29818769e3069f90e",
    },
    "static_hostile_test": {
        "path": "Testing/test_kira_r25_foundation_afes_locked_pair_execution_attempt05.py",
        "bytes": 21602,
        "sha256": "4b5ff5f98031738028d7f8f2f3bcdef5275e0f408652196d71e815ebcae15b03",
    },
    "checkpoint": {
        "path": "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_05/CHECKPOINT.md",
        "bytes": 9785,
        "sha256": "d8d0be81f96efd1fbb143b2ec7f81e99696decb74ad93e9d32c6a76d5c983109",
    },
    "rejection_audit": {
        "path": "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_05/INDEPENDENT_AUDIT.md",
        "bytes": 12731,
        "sha256": "da85fab5053272e2f53589825014d05ce4a0381f6ddf5b447934bf791ca926aa",
    },
}
PRESERVED_ATTEMPT06 = {
    "contract": {
        "path": "Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_locked_pair_execution_v6.json",
        "bytes": 12380,
        "sha256": "91be1282a6805b968b62d65dbef5eed0dab53cf63f8e36264b20de270ace1c79",
    },
    "external_bootstrap": {
        "path": "tools/launch_kira_r25_foundation_afes_locked_pair_v6.py",
        "bytes": 38416,
        "sha256": "91f0d78b45a93fa41c34a86306b6b4b5e98275f438359abc76279782e994135a",
    },
    "private_controller": {
        "path": "tools/run_kira_r25_foundation_afes_locked_pair_v6.py",
        "bytes": 50246,
        "sha256": "2007c7375522e29754cd57e23f9effd1821994e97440e284c8b1296d2b927a70",
    },
    "child_wrapper": {
        "path": "tools/blender_extract_kira_r25_foundation_afes_transition_rings_execution_v6.py",
        "bytes": 12534,
        "sha256": "1f481786adf1a4598f576ee5aed795383d95316afc24d8f14a60c7934f12f2cd",
    },
    "static_hostile_test": {
        "path": "Testing/test_kira_r25_foundation_afes_locked_pair_execution_attempt06.py",
        "bytes": 25191,
        "sha256": "6fadc6dec5808637e5dfe08498d91b50b2d9e6ed0123b5151f7e700554751001",
    },
    "checkpoint": {
        "path": "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_06/CHECKPOINT.md",
        "bytes": 13765,
        "sha256": "b64891a2eee0c9a241b040363295d28ec226e52b91c5f551578f9d81bf565e20",
    },
    "rejection_audit": {
        "path": "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_06/INDEPENDENT_AUDIT.md",
        "bytes": 14707,
        "sha256": "38da97a48ea36d89f08655fb8e5fef4aced43b26f25f41d2f83bf79d6255b1e6",
    },
}
PRESERVED_ACCEPTED_ATTEMPT07 = {
    "contract": {
        "path": "Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_locked_pair_execution_v7.json",
        "bytes": 15639,
        "sha256": "e582ff91202d245f125165cafd4f5b8274425622e8a062dba35b661510390c85",
    },
    "external_bootstrap": {
        "path": "tools/launch_kira_r25_foundation_afes_locked_pair_v7.py",
        "bytes": 52298,
        "sha256": "d2c85012be52dcd5629150855d5cded12c6f0fb480fa751bd00216b9a860193a",
    },
    "private_controller": {
        "path": "tools/run_kira_r25_foundation_afes_locked_pair_v7.py",
        "bytes": 80728,
        "sha256": "4bbc477521e5ae38eba1b72a78de35f325274f8c3e1ace1f41a600ed7979cd55",
    },
    "child_wrapper": {
        "path": "tools/blender_extract_kira_r25_foundation_afes_transition_rings_execution_v7.py",
        "bytes": 12574,
        "sha256": "d7ae8e02bce1937d91484c8ff5e9259a28189c2c23b77085ebca9132278392be",
    },
    "static_hostile_test": {
        "path": "Testing/test_kira_r25_foundation_afes_locked_pair_execution_attempt07.py",
        "bytes": 36017,
        "sha256": "a8d5a207a7c8059aaa4d4fa6b8bc0bf883b9ffe4e471819fa02eddebf3272f63",
    },
    "checkpoint": {
        "path": "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_07/CHECKPOINT.md",
        "bytes": 12993,
        "sha256": "b3b9b0011ef1b03daebe1f7ccf963cdc9a77e3905d12dedbf3642e22d4fc3aac",
    },
    "accepted_audit": {
        "path": "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_07/INDEPENDENT_AUDIT.json",
        "bytes": 7282,
        "sha256": "67c2b8e2436398af94d787006fa8cf60d7e9d6b190c1fd430b791bb5028c3c2d",
    },
}
PRESERVED_ATTEMPT07_FAILURE_EVIDENCE = {
    "controller_outcome": {
        "path": "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution/attempt_07/CONTROLLER_OUTCOME.receipt.bin",
        "bytes": 8221,
        "sha256": "b50038d45acd9a6a84022d59cdfc66868f3d312022b23089934e377f2cfc73f1",
    },
    "run_01_raw_frame": {
        "path": "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution/attempt_07/run_01_raw_frame.bin",
        "bytes": 0,
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    },
    "run_01_stderr": {
        "path": "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution/attempt_07/run_01_stderr.log",
        "bytes": 978,
        "sha256": "a313bddf89aeb4661ef76f8dca0c37e943dec87dd7094928cab4848338ee3570",
    },
    "run_01_stdout": {
        "path": "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution/attempt_07/run_01_stdout.log",
        "bytes": 337,
        "sha256": "f459fc81afe7864e43cee889793a302f49cf7a78f1531404af596459fe51881c",
    },
}
PRESERVED_ATTEMPT07_RUNTIME_TREE = {
    "root": "RecoverySprint/runtime_cache/r25_blender_v7/attempt_07",
    "directory_count": 12,
    "file_count": 0,
    "directories": [
        {
            "path": "RecoverySprint/runtime_cache/r25_blender_v7/attempt_07",
            "entries": ["D:pair_c703ca8a14bd8882ef5a225068d0e75e"],
        },
        {
            "path": "RecoverySprint/runtime_cache/r25_blender_v7/attempt_07/pair_c703ca8a14bd8882ef5a225068d0e75e",
            "entries": [
                "D:run_01_f858a297a39455205641aea5d3a42b9d",
                "D:run_02_8298ea8f2db48516ed64e667d5de97b9",
            ],
        },
        {
            "path": "RecoverySprint/runtime_cache/r25_blender_v7/attempt_07/pair_c703ca8a14bd8882ef5a225068d0e75e/run_01_f858a297a39455205641aea5d3a42b9d",
            "entries": ["D:temp", "D:user_config", "D:user_datafiles", "D:user_scripts"],
        },
        {
            "path": "RecoverySprint/runtime_cache/r25_blender_v7/attempt_07/pair_c703ca8a14bd8882ef5a225068d0e75e/run_01_f858a297a39455205641aea5d3a42b9d/temp",
            "entries": [],
        },
        {
            "path": "RecoverySprint/runtime_cache/r25_blender_v7/attempt_07/pair_c703ca8a14bd8882ef5a225068d0e75e/run_01_f858a297a39455205641aea5d3a42b9d/user_config",
            "entries": [],
        },
        {
            "path": "RecoverySprint/runtime_cache/r25_blender_v7/attempt_07/pair_c703ca8a14bd8882ef5a225068d0e75e/run_01_f858a297a39455205641aea5d3a42b9d/user_datafiles",
            "entries": [],
        },
        {
            "path": "RecoverySprint/runtime_cache/r25_blender_v7/attempt_07/pair_c703ca8a14bd8882ef5a225068d0e75e/run_01_f858a297a39455205641aea5d3a42b9d/user_scripts",
            "entries": [],
        },
        {
            "path": "RecoverySprint/runtime_cache/r25_blender_v7/attempt_07/pair_c703ca8a14bd8882ef5a225068d0e75e/run_02_8298ea8f2db48516ed64e667d5de97b9",
            "entries": ["D:temp", "D:user_config", "D:user_datafiles", "D:user_scripts"],
        },
        {
            "path": "RecoverySprint/runtime_cache/r25_blender_v7/attempt_07/pair_c703ca8a14bd8882ef5a225068d0e75e/run_02_8298ea8f2db48516ed64e667d5de97b9/temp",
            "entries": [],
        },
        {
            "path": "RecoverySprint/runtime_cache/r25_blender_v7/attempt_07/pair_c703ca8a14bd8882ef5a225068d0e75e/run_02_8298ea8f2db48516ed64e667d5de97b9/user_config",
            "entries": [],
        },
        {
            "path": "RecoverySprint/runtime_cache/r25_blender_v7/attempt_07/pair_c703ca8a14bd8882ef5a225068d0e75e/run_02_8298ea8f2db48516ed64e667d5de97b9/user_datafiles",
            "entries": [],
        },
        {
            "path": "RecoverySprint/runtime_cache/r25_blender_v7/attempt_07/pair_c703ca8a14bd8882ef5a225068d0e75e/run_02_8298ea8f2db48516ed64e667d5de97b9/user_scripts",
            "entries": [],
        },
    ],
    "canonical_manifest_sha256": "708fdef4831493df1ab604812f5b5b6c8f6f7772c125320128f5a1c8399cb2d3",
}
ATTEMPT07_FAILURE_TRUTH = {
    "accepted_audit_sha256": "67c2b8e2436398af94d787006fa8cf60d7e9d6b190c1fd430b791bb5028c3c2d",
    "execution_contract_sha256": "e582ff91202d245f125165cafd4f5b8274425622e8a062dba35b661510390c85",
    "failure_receipt_schema": "kira.avatar.r25.foundation_afes_locked_pair_failure.v7",
    "failure_stage": "children",
    "failure": "run_01_blender_exit:1",
    "runtime_cleanup_failure": None,
    "runtime_restoration_manifest_sha256": "3a561f0a3624b6e2d67eccf924811dabd9f4bf55332c874d385cc09f3139d04d",
    "stderr_exact_cause": "NameError:name 'ctypes' is not defined",
    "stderr_wrapper_line": 238,
    "raw_frame_bytes": 0,
    "blender_reached_extraction": False,
    "failure_was_safe_and_append_only": True,
}


class LockedPairBootstrapV8Error(RuntimeError):
    """The external Attempt-08 bootstrap failed closed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


class _ProcessEntry32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


def _process_parent_pid(process_id: int) -> int:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(_ProcessEntry32W),
    ]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(_ProcessEntry32W),
    ]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    invalid = ctypes.c_void_p(-1).value
    if snapshot in (None, invalid):
        raise LockedPairBootstrapV8Error(
            f"issuer_process_snapshot_failed:winerror={ctypes.get_last_error()}"
        )
    try:
        entry = _ProcessEntry32W()
        entry.dwSize = ctypes.sizeof(entry)
        present = bool(kernel32.Process32FirstW(snapshot, ctypes.byref(entry)))
        while present:
            if int(entry.th32ProcessID) == process_id:
                parent = int(entry.th32ParentProcessID)
                if parent <= 0 or parent == process_id:
                    raise LockedPairBootstrapV8Error("issuer_parent_process_invalid")
                return parent
            present = bool(kernel32.Process32NextW(snapshot, ctypes.byref(entry)))
        raise LockedPairBootstrapV8Error("issuer_current_process_not_enumerated")
    finally:
        kernel32.CloseHandle(snapshot)


def _query_process_identity(process_id: int) -> dict[str, object]:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenProcess(0x1000, False, process_id)
    if not handle:
        raise LockedPairBootstrapV8Error(
            f"issuer_process_open_failed:{process_id}:"
            f"winerror={ctypes.get_last_error()}"
        )
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(int(size.value))
        if not kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(size),
        ):
            raise LockedPairBootstrapV8Error(
                f"issuer_process_image_failed:{process_id}:"
                f"winerror={ctypes.get_last_error()}"
            )
        creation = wintypes.FILETIME()
        exit_time = wintypes.FILETIME()
        kernel_time = wintypes.FILETIME()
        user_time = wintypes.FILETIME()
        if not kernel32.GetProcessTimes(
            handle, ctypes.byref(creation), ctypes.byref(exit_time),
            ctypes.byref(kernel_time), ctypes.byref(user_time),
        ):
            raise LockedPairBootstrapV8Error(
                f"issuer_process_time_failed:{process_id}:"
                f"winerror={ctypes.get_last_error()}"
            )
        created = (int(creation.dwHighDateTime) << 32) | int(creation.dwLowDateTime)
        return {
            "process_id": process_id,
            "creation_time_100ns": created,
            "image_path": str(Path(buffer.value).resolve(strict=True)),
        }
    finally:
        kernel32.CloseHandle(handle)


def _kernel_command_line() -> tuple[str, list[str]]:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32.GetCommandLineW.argtypes = []
    kernel32.GetCommandLineW.restype = wintypes.LPWSTR
    shell32.CommandLineToArgvW.argtypes = [
        wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int),
    ]
    shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    raw = str(kernel32.GetCommandLineW())
    count = ctypes.c_int()
    values = shell32.CommandLineToArgvW(raw, ctypes.byref(count))
    if not values:
        raise LockedPairBootstrapV8Error(
            f"issuer_command_line_parse_failed:winerror={ctypes.get_last_error()}"
        )
    try:
        return raw, [str(values[index]) for index in range(int(count.value))]
    finally:
        kernel32.LocalFree(ctypes.cast(values, ctypes.c_void_p))


def _observe_issuer_process() -> dict[str, object]:
    if os.name != "nt":
        raise LockedPairBootstrapV8Error("issuer_provenance_is_windows_only")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcessId.argtypes = []
    kernel32.GetCurrentProcessId.restype = wintypes.DWORD
    current_id = int(kernel32.GetCurrentProcessId())
    parent_id = _process_parent_pid(current_id)
    command_line, argv = _kernel_command_line()
    return {
        "current": _query_process_identity(current_id),
        "parent": _query_process_identity(parent_id),
        "command_line_sha256": _sha256_bytes(command_line.encode("utf-8")),
        "command_argv": argv,
        "python_flags": {
            "isolated": int(sys.flags.isolated),
            "no_site": int(sys.flags.no_site),
            "safe_path": bool(sys.flags.safe_path),
            "dont_write_bytecode": bool(sys.flags.dont_write_bytecode),
        },
    }


def _build_issuer_envelope(
    *, contract: Mapping[str, Any], controller_path: Path,
    expected_contract_sha256: str, accepted_audit_sha256: str,
    issuer_nonce: str,
) -> bytes:
    observed = _observe_issuer_process()
    bootstrap_path = Path(__file__).resolve(strict=True)
    python_path = Path(sys.executable).resolve(strict=True)
    expected_argv = [
        str(python_path), "-I", "-S", "-B", str(bootstrap_path),
        "--expected-contract-sha256", expected_contract_sha256,
        "--accepted-audit-sha256", accepted_audit_sha256,
    ]
    observed_argv = observed.get("command_argv")
    if (
        not isinstance(observed_argv, list)
        or len(observed_argv) != len(expected_argv)
        or os.path.normcase(os.path.abspath(str(observed_argv[0])))
        != os.path.normcase(str(python_path))
        or observed_argv[1:4] != expected_argv[1:4]
        or os.path.normcase(os.path.abspath(str(observed_argv[4])))
        != os.path.normcase(str(bootstrap_path))
        or observed_argv[5:] != expected_argv[5:]
    ):
        raise LockedPairBootstrapV8Error(
            "issuer_kernel_command_not_exact_bootstrap_invocation"
        )
    if observed["python_flags"] != {
        "isolated": 1, "no_site": 1, "safe_path": True,
        "dont_write_bytecode": True,
    }:
        raise LockedPairBootstrapV8Error(
            "issuer_python_must_use_isolated_no_site_no_bytecode_flags"
        )
    bootstrap_row = dict(contract["execution_sources"]["external_bootstrap"])
    python_row = dict(contract["execution_sources"]["bootstrap_python_executable"])
    controller_row = dict(contract["execution_sources"]["private_controller"])
    if (
        str(Path(python_row["path"]).resolve(strict=True))
        != observed["current"]["image_path"]
    ):
        raise LockedPairBootstrapV8Error("issuer_python_image_path_mismatch")
    payload = {
        "schema": "kira.avatar.r25.foundation_afes_bootstrap_issuer.v8",
        "attempt_id": "attempt_08",
        "issuer_nonce": issuer_nonce,
        "expected_contract_sha256": expected_contract_sha256,
        "accepted_audit_sha256": accepted_audit_sha256,
        "bootstrap_source": bootstrap_row,
        "bootstrap_python_executable": python_row,
        "private_controller": controller_row,
        "controller_invocation": {
            "mode": "private_retained_locked_bytes_exec",
            "claim_builtin": "__kira_bootstrap_claim_v8__",
            "entrypoint": "run_locked_pair",
            "expected_contract_sha256": expected_contract_sha256,
            "accepted_audit_sha256": accepted_audit_sha256,
        },
        "process": observed,
    }
    payload["invocation_sha256"] = _sha256_bytes(_canonical_json_bytes(payload))
    return _canonical_json_bytes(payload)


def _exact_typed_equal(observed: object, expected: object) -> bool:
    if type(observed) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(observed) == set(expected) and all(
            _exact_typed_equal(observed[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(observed) == len(expected) and all(
            _exact_typed_equal(left, right)
            for left, right in zip(observed, expected)
        )
    return observed == expected


def _project_file(relative: object) -> Path:
    text = str(relative or "")
    candidate = Path(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts:
        raise LockedPairBootstrapV8Error(f"unsafe_project_relative_path:{text}")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise LockedPairBootstrapV8Error(f"symlink_path_refused:{text}")
        try:
            if int(getattr(os.lstat(lexical), "st_file_attributes", 0)) & 0x400:
                raise LockedPairBootstrapV8Error(f"reparse_path_refused:{text}")
        except FileNotFoundError:
            pass
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise LockedPairBootstrapV8Error(f"path_escaped_project_root:{text}") from exc
    if not resolved.is_file():
        raise LockedPairBootstrapV8Error(f"project_input_not_file:{text}")
    return resolved


def _project_directory(relative: object) -> Path:
    if not isinstance(relative, str) or not relative:
        raise LockedPairBootstrapV8Error("project_directory_path_invalid")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise LockedPairBootstrapV8Error("project_directory_path_not_relative")
    resolved = (PROJECT_ROOT / candidate).resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise LockedPairBootstrapV8Error("project_directory_path_escape") from exc
    if not resolved.is_dir() or resolved.is_symlink():
        raise LockedPairBootstrapV8Error("project_directory_not_plain_directory")
    return resolved


def _observe_attempt07_runtime_tree() -> dict[str, object]:
    root = _project_directory(PRESERVED_ATTEMPT07_RUNTIME_TREE["root"])
    directories: list[dict[str, object]] = []
    file_count = 0
    pending = [root]
    while pending:
        directory = pending.pop()
        relative = directory.relative_to(PROJECT_ROOT).as_posix()
        entries: list[str] = []
        children = sorted(directory.iterdir(), key=lambda item: item.name.casefold())
        for child in children:
            if child.is_symlink():
                raise LockedPairBootstrapV8Error("attempt07_runtime_tree_reparse_entry")
            if child.is_dir():
                entries.append(f"D:{child.name}")
                pending.append(child.resolve(strict=True))
            elif child.is_file():
                entries.append(f"F:{child.name}")
                file_count += 1
            else:
                raise LockedPairBootstrapV8Error("attempt07_runtime_tree_special_entry")
        directories.append({"path": relative, "entries": entries})
    directories.sort(key=lambda row: str(row["path"]).casefold())
    observed = {
        "root": PRESERVED_ATTEMPT07_RUNTIME_TREE["root"],
        "directory_count": len(directories),
        "file_count": file_count,
        "directories": directories,
    }
    observed["canonical_manifest_sha256"] = _sha256_bytes(
        _canonical_json_bytes(observed)
    )
    return observed


def _parse_json(value: bytes, label: str) -> dict[str, Any]:
    def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, item in pairs:
            if key in result:
                raise LockedPairBootstrapV8Error(f"duplicate_json_key:{label}:{key}")
            result[key] = item
        return result

    def reject_constant(raw: str) -> object:
        raise LockedPairBootstrapV8Error(f"non_finite_json_value:{label}:{raw}")

    try:
        parsed = json.loads(
            value.decode("utf-8-sig"), object_pairs_hook=strict_object,
            parse_constant=reject_constant,
        )
    except LockedPairBootstrapV8Error:
        raise
    except Exception as exc:
        raise LockedPairBootstrapV8Error(f"invalid_json:{label}") from exc
    if not isinstance(parsed, dict):
        raise LockedPairBootstrapV8Error(f"json_root_not_object:{label}")
    return parsed


def _validate_row(row: object, label: str) -> Mapping[str, object]:
    if not isinstance(row, Mapping) or set(row) != {"path", "bytes", "sha256"}:
        raise LockedPairBootstrapV8Error(f"invalid_binding:{label}")
    if type(row["bytes"]) is not int or row["bytes"] < 0:
        raise LockedPairBootstrapV8Error(f"invalid_binding_bytes:{label}")
    if not isinstance(row["sha256"], str) or HEX64.fullmatch(row["sha256"]) is None:
        raise LockedPairBootstrapV8Error(f"invalid_binding_sha256:{label}")
    return row


def _row_path(label: str, row: object) -> Path:
    binding = _validate_row(row, label)
    if label.rsplit(".", 1)[-1] in {
        "blender_executable", "bootstrap_python_executable",
    }:
        path = Path(str(binding["path"])).resolve(strict=True)
        if not path.is_file():
            raise LockedPairBootstrapV8Error(
                f"external_executable_not_file:{label}"
            )
        return path
    return _project_file(binding["path"])


def _read_contract_untrusted() -> tuple[Path, dict[str, Any]]:
    path = _project_file(CONTRACT_RELATIVE_PATH)
    return path, _parse_json(path.read_bytes(), "untrusted_discovery_contract")


def _untrusted_discovery(*, require_audit: bool) -> tuple[Path, list[Path]]:
    contract_path, contract = _read_contract_untrusted()
    paths = [contract_path]
    sources = contract.get("execution_sources")
    if not isinstance(sources, Mapping) or not sources:
        raise LockedPairBootstrapV8Error("discovery_execution_sources_missing")
    for label, row in sources.items():
        paths.append(_row_path(f"execution_sources.{label}", row))
    inherited_v5_path = _row_path(
        "inherited_attempt05_contract", contract.get("inherited_attempt05_contract"),
    )
    paths.append(inherited_v5_path)
    preservation = contract.get("preserved_rejected_attempt05")
    if not isinstance(preservation, Mapping):
        raise LockedPairBootstrapV8Error("attempt05_preservation_missing")
    for label, row in preservation.items():
        paths.append(_row_path(f"preserved_attempt05.{label}", row))
    preservation06 = contract.get("preserved_rejected_attempt06")
    if not isinstance(preservation06, Mapping):
        raise LockedPairBootstrapV8Error("attempt06_preservation_missing")
    for label, row in preservation06.items():
        paths.append(_row_path(f"preserved_attempt06.{label}", row))
    inherited_v7_path = _row_path(
        "inherited_accepted_attempt07_contract",
        contract.get("inherited_accepted_attempt07_contract"),
    )
    paths.append(inherited_v7_path)
    preservation07 = contract.get("preserved_accepted_attempt07")
    if not isinstance(preservation07, Mapping):
        raise LockedPairBootstrapV8Error("attempt07_preservation_missing")
    for label, row in preservation07.items():
        paths.append(_row_path(f"preserved_attempt07.{label}", row))
    failure07 = contract.get("preserved_attempt07_failure_evidence")
    if not isinstance(failure07, Mapping):
        raise LockedPairBootstrapV8Error("attempt07_failure_evidence_missing")
    for label, row in failure07.items():
        paths.append(_row_path(f"attempt07_failure_evidence.{label}", row))
    inherited_v5 = _parse_json(inherited_v5_path.read_bytes(), "untrusted_attempt05")
    inherited_v4_path = _row_path(
        "attempt05.inherited_attempt04_contract",
        inherited_v5.get("inherited_attempt04_contract"),
    )
    paths.append(inherited_v4_path)
    inherited_v4 = _parse_json(inherited_v4_path.read_bytes(), "untrusted_attempt04")
    closure = inherited_v4.get("child_project_read_closure")
    if not isinstance(closure, Mapping) or not closure:
        raise LockedPairBootstrapV8Error("discovery_inherited_closure_missing")
    for label, row in closure.items():
        paths.append(_row_path(f"child_project_read_closure.{label}", row))
    if require_audit:
        paths.append(_project_file(AUDIT_RELATIVE_PATH))
    return contract_path, sorted(
        {path.resolve(strict=True) for path in paths},
        key=lambda item: str(item).casefold(),
    )


class WindowsReadLockSet:
    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 0x00000001
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x00000080

    def __init__(self) -> None:
        if os.name != "nt":
            raise LockedPairBootstrapV8Error("locked_pair_is_windows_only")
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
        ]
        self.kernel32.CreateFileW.restype = wintypes.HANDLE
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.handles: list[int] = []
        self.locked_paths: list[Path] = []
        self.active = False

    def add(self, path: Path) -> None:
        handle = self.kernel32.CreateFileW(
            str(path), self.GENERIC_READ, self.FILE_SHARE_READ, None,
            self.OPEN_EXISTING, self.FILE_ATTRIBUTE_NORMAL, None,
        )
        invalid = ctypes.c_void_p(-1).value
        if handle in (None, invalid):
            raise LockedPairBootstrapV8Error(
                f"cannot_lock_input:{path}:winerror={ctypes.get_last_error()}"
            )
        self.handles.append(int(handle))
        self.locked_paths.append(path.resolve(strict=True))

    def close(self) -> None:
        first: Exception | None = None
        while self.handles:
            handle = self.handles.pop()
            if not self.kernel32.CloseHandle(wintypes.HANDLE(handle)) and first is None:
                first = LockedPairBootstrapV8Error(
                    f"input_lock_close_failed:{ctypes.get_last_error()}"
                )
        self.active = False
        if first is not None:
            raise first

    def __enter__(self) -> "WindowsReadLockSet":
        self.active = True
        return self

    def __exit__(self, _type: Any, _value: Any, _traceback: Any) -> None:
        self.close()


class LockedByteLedger:
    def __init__(self, locks: Any, paths: Iterable[Path]) -> None:
        allowed = {Path(path).resolve(strict=True) for path in paths}
        observed = {Path(path).resolve(strict=True) for path in locks.locked_paths}
        if not locks.active or observed != allowed:
            raise LockedPairBootstrapV8Error("ledger_requires_complete_active_lock_set")
        self.allowed = allowed
        self.values: dict[Path, bytes] = {}

    def read_path(self, path: Path) -> bytes:
        exact = Path(path).resolve(strict=True)
        if exact not in self.allowed:
            raise LockedPairBootstrapV8Error(f"unlocked_read_refused:{exact}")
        if exact not in self.values:
            self.values[exact] = exact.read_bytes()
        return self.values[exact]

    def read_exact(self, row: object, *, label: str = "bound_row") -> tuple[Path, bytes]:
        binding = _validate_row(row, label)
        path = _row_path(label, binding)
        value = self.read_path(path)
        if len(value) != binding["bytes"] or _sha256_bytes(value) != binding["sha256"]:
            raise LockedPairBootstrapV8Error(f"binding_drift:{label}")
        return path, value

    def complete_snapshot(self) -> dict[str, dict[str, object]]:
        if set(self.values) != self.allowed:
            missing = sorted(str(path) for path in self.allowed - set(self.values))
            raise LockedPairBootstrapV8Error(f"snapshot_missing_locked_values:{missing}")
        return {
            str(path): {"bytes": len(self.values[path]), "sha256": _sha256_bytes(self.values[path])}
            for path in sorted(self.allowed, key=lambda item: str(item).casefold())
        }


def _expected_process_contract() -> dict[str, object]:
    return {
        "factory_startup": True,
        "background": True,
        "autoexec_disabled": True,
        "python_exit_code": 1,
        "stdin": "DEVNULL",
        "shell": False,
        "close_fds": True,
        "least_handle_inheritance": True,
        "result_handle_must_be_win32_pipe": True,
        "concurrent_bounded_pipe_drain": True,
        "exactly_one_frame_and_eof": True,
        "maximum_frame_bytes": 1048628,
        "maximum_stdout_bytes": 4194304,
        "maximum_stderr_bytes": 4194304,
        "process_timeout_seconds": 180,
        "windows_job_kill_on_close": True,
        "create_suspended_assign_job_start_drains_then_resume": True,
        "exception_safe_post_creation_finally_cleanup": True,
        "fresh_pair_64_hex_nonce": True,
        "fresh_distinct_run_64_hex_nonce_per_run": True,
        "environment_passthrough_if_present": list(PASSTHROUGH),
        "forced_environment": {
            "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        },
        "controlled_runtime_root_template": (
            "RecoverySprint/runtime_cache/r25_blender_v8/attempt_08/"
            "pair_<PAIR_SHA256_PREFIX_32>/run_<ONE_OR_TWO>_<PAIR_RUN_SHA256_PREFIX_32>"
        ),
        "both_run_trees_precreated_before_first_child": True,
        "descendants_atomically_created_or_opened_relative_to_held_parent_handles": True,
        "native_create_disposition_and_returned_handle_identity_bound": True,
        "no_path_based_mkdir_then_open_for_runtime_descendants": True,
        "project_to_leaf_ancestor_chain_opened_and_held": True,
        "handle_final_paths_and_volume_file_ids_bound": True,
        "all_directory_handles_reject_reparse_objects": True,
        "all_directory_handles_omit_delete_sharing_through_cleanup": True,
        "pair_and_run_roots_deny_unexpected_child_creation": True,
        "config_scripts_datafiles_deny_all_child_creation": True,
        "fixed_content_dacls_are_protected_and_hash_reverified": True,
        "exact_original_security_descriptors_saved_before_mutation": True,
        "original_security_descriptors_restored_reverse_order_on_all_paths": True,
        "restored_descriptor_bytes_sddl_and_control_exactly_reverified": True,
        "partial_boundary_install_failure_restores_completed_boundaries": True,
        "original_deny_policy_is_restored_without_weakening": True,
        "sticky_name_write_security_change_notifications_held_through_cleanup": True,
        "transient_create_delete_or_security_change_fails_acceptance": True,
        "temp_is_fresh_nonce_private_stable_identity_and_not_project_import_source": True,
        "runtime_cache_is_not_automatically_deleted": True,
        "external_bootstrap_command_template": [
            "<BOOTSTRAP_PYTHON_EXECUTABLE>", "-I", "-S", "-B",
            "<EXTERNAL_BOOTSTRAP>", "--expected-contract-sha256",
            "<EXPECTED_CONTRACT_SHA256>", "--accepted-audit-sha256",
            "<ACCEPTED_AUDIT_SHA256>",
        ],
        "kernel_observed_bootstrap_process_and_parent_identity_bound": True,
        "exact_bootstrap_source_and_python_executable_bound": True,
        "one_use_bootstrap_claim_and_invocation_nonce_bound": True,
        "path_rule": "exact_blender_directory_then_system32_then_windows_directory",
        "working_directory": ".",
        "exact_command_template": [
            "<BLENDER_EXECUTABLE>", "--background", "--factory-startup",
            "--disable-autoexec", "<FOUNDATION_BLEND>", "--python-exit-code", "1",
            "--python", "<CHILD_WRAPPER>", "--", "--result-handle",
            "<INHERITED_WIN32_PIPE_HANDLE>", "--execution-contract-sha256",
            "<EXPECTED_CONTRACT_SHA256>", "--pair-session-nonce",
            "<FRESH_PAIR_64_HEX_NONCE>", "--run-nonce",
            "<FRESH_RUN_64_HEX_NONCE>", "--run-number", "<ONE_OR_TWO>",
        ],
    }


def _validate_exact_contract_sections(contract: Mapping[str, Any]) -> None:
    expected_top = {
        "schema", "attempt_id", "status", "scope", "authorization_basis",
        "execution_sources", "inherited_attempt05_contract",
        "inherited_accepted_attempt07_contract",
        "recursive_closure_contract", "process_contract", "audit_gate",
        "required_fresh_run_count", "pair_acceptance", "append_only_output_root",
        "preserved_rejected_attempt05", "preserved_rejected_attempt06",
        "preserved_accepted_attempt07", "preserved_attempt07_failure_evidence",
        "preserved_attempt07_runtime_tree", "attempt07_failure_truth",
        "runtime_dependency_truth", "truth_boundary",
    }
    if set(contract) != expected_top:
        raise LockedPairBootstrapV8Error("locked_contract_top_level_schema_mismatch")
    if not _exact_typed_equal(contract["scope"], {
        "body_work_only": True,
        "read_only_blender_diagnostic": True,
        "blend_mutation_allowed": False,
        "blend_save_allowed": False,
        "render_allowed": False,
        "candidate_creation_allowed": False,
        "body_authoring_allowed": False,
        "runtime_activation_allowed": False,
        "assignment_allowed": False,
        "export_allowed": False,
        "publication_allowed": False,
    }):
        raise LockedPairBootstrapV8Error("locked_scope_mismatch")
    if not _exact_typed_equal(contract["authorization_basis"], {
        "owner_requested_body_progress": True,
        "owner_authorized_blender_problem_repair": True,
        "bounded_operation": "extract_existing_foundation_afes_and_two_transition_rings_without_mutation",
        "does_not_authorize_candidate_or_runtime_change": True,
        "fresh_independent_attempt08_audit_required_before_execution": True,
    }):
        raise LockedPairBootstrapV8Error("locked_authorization_basis_mismatch")
    if not isinstance(contract["execution_sources"], Mapping) or set(
        contract["execution_sources"]
    ) != {
        "external_bootstrap", "private_controller", "child_wrapper",
        "static_hostile_test", "blender_executable",
        "bootstrap_python_executable", "attempt05_bootstrap_core",
        "attempt05_controller_core", "attempt05_child_wrapper_core",
        "attempt04_controller_core", "attempt04_child_wrapper_core",
    }:
        raise LockedPairBootstrapV8Error("execution_source_table_mismatch")
    if not _exact_typed_equal(contract["process_contract"], _expected_process_contract()):
        raise LockedPairBootstrapV8Error("locked_process_contract_mismatch")
    if not _exact_typed_equal(contract["audit_gate"], {
        "path": AUDIT_RELATIVE_PATH,
        "sha256_supplied_out_of_band": True,
        "document_schema": "kira.avatar.r25.foundation_afes_locked_pair_independent_audit.v8",
        "authoritative_decision_code": "ACCEPTED_FOR_ONE_BOUNDED_READ_ONLY_PAIR_ONLY",
        "exact_key_and_value_schema_required": True,
        "extra_or_contradictory_decision_fields_rejected": True,
        "quoted_substrings_are_not_authority": True,
        "pre_audit_absence_is_valid_static_preparation_state": True,
        "post_audit_exact_hash_bound_acceptance_is_valid_verification_state": True,
    }):
        raise LockedPairBootstrapV8Error("locked_audit_gate_mismatch")
    if type(contract["required_fresh_run_count"]) is not int or contract[
        "required_fresh_run_count"
    ] != 2:
        raise LockedPairBootstrapV8Error("locked_run_count_mismatch")
    if not _exact_typed_equal(contract["pair_acceptance"], {
        "bootstrap_private_builtins_one_use_claim": True,
        "ambient_imported_controller_always_inert": True,
        "ambient_module_exposes_no_ungated_authorized_pair_entry": True,
        "exact_bootstrap_context_identity_captured_with_capability": True,
        "capability_consumed_before_core_load_reservation_runtime_or_process": True,
        "kernel_process_and_parent_identity_verified_before_context_use": True,
        "exact_bootstrap_source_python_and_controller_invocation_bound": True,
        "caller_private_reexecution_rejected_before_context_use": True,
        "issuer_nonce_and_invocation_digest_bound": True,
        "all_original_security_descriptors_restored_before_handle_release": True,
        "distinct_pair_and_run_nonces": True,
        "exact_authenticated_outer_and_inner_payload_schema": True,
        "exact_recursive_nested_schema_and_types": True,
        "exact_foundation_mesh_counts_and_identity_bound_in_parent": True,
        "exact_foundation_group_set_counts_and_semantic_hashes_bound_in_parent": True,
        "exact_afes_union_counts_and_semantic_hashes_bound_in_parent": True,
        "exact_bounds_codec_shape_types_and_expected_tolerance_bound_in_parent": True,
        "all_compact_array_and_transition_invariants_validated_in_parent": True,
        "exact_full_normalized_topology_digest_match": True,
        "complete_recursive_child_project_inputs_locked_before_verification": True,
        "all_declared_inputs_locked_through_after_snapshot": True,
        "all_declared_inputs_unchanged_after_pair": True,
        "each_raw_frame_and_log_created_exclusively": True,
        "fixed_root_second_use_is_rejected": True,
        "post_outcome_reservation_failures_attempt_canonical_failure_receipt": True,
        "abrupt_process_or_storage_failure_can_prevent_failure_receipt": True,
        "pre_reservation_failure_has_no_receipt": True,
        "fresh_independent_audit_required_before_execution": True,
        "accepted_attempt07_graph_audit_failure_and_runtime_evidence_bound": True,
        "child_require_pipe_runtime_import_preflight_exercised": True,
        "attempt08_fixed_roots_distinct_from_attempt07_evidence": True,
    }):
        raise LockedPairBootstrapV8Error("locked_pair_acceptance_mismatch")
    if contract["append_only_output_root"] != (
        "RecoverySprint/continuation_20260809/"
        "kira_r25_foundation_afes_locked_pair_execution/attempt_08"
    ):
        raise LockedPairBootstrapV8Error("locked_output_root_mismatch")
    if not _exact_typed_equal(contract["preserved_rejected_attempt05"], PRESERVED_ATTEMPT05):
        raise LockedPairBootstrapV8Error("attempt05_preservation_table_mismatch")
    if not _exact_typed_equal(contract["preserved_rejected_attempt06"], PRESERVED_ATTEMPT06):
        raise LockedPairBootstrapV8Error("attempt06_preservation_table_mismatch")
    if not _exact_typed_equal(
        contract["inherited_accepted_attempt07_contract"],
        PRESERVED_ACCEPTED_ATTEMPT07["contract"],
    ):
        raise LockedPairBootstrapV8Error("attempt07_inherited_contract_mismatch")
    if not _exact_typed_equal(
        contract["preserved_accepted_attempt07"], PRESERVED_ACCEPTED_ATTEMPT07,
    ):
        raise LockedPairBootstrapV8Error("attempt07_preservation_table_mismatch")
    if not _exact_typed_equal(
        contract["preserved_attempt07_failure_evidence"],
        PRESERVED_ATTEMPT07_FAILURE_EVIDENCE,
    ):
        raise LockedPairBootstrapV8Error("attempt07_failure_evidence_table_mismatch")
    if not _exact_typed_equal(
        contract["preserved_attempt07_runtime_tree"],
        PRESERVED_ATTEMPT07_RUNTIME_TREE,
    ):
        raise LockedPairBootstrapV8Error("attempt07_runtime_tree_table_mismatch")
    if not _exact_typed_equal(contract["attempt07_failure_truth"], ATTEMPT07_FAILURE_TRUTH):
        raise LockedPairBootstrapV8Error("attempt07_failure_truth_mismatch")
    if not _exact_typed_equal(_observe_attempt07_runtime_tree(), PRESERVED_ATTEMPT07_RUNTIME_TREE):
        raise LockedPairBootstrapV8Error("attempt07_runtime_tree_drift")
    forbidden_v7_roots = {
        "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution/attempt_07",
        "RecoverySprint/runtime_cache/r25_blender_v7/attempt_07",
        "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_07",
    }
    fixed_v8_roots = {
        str(contract["append_only_output_root"]),
        str(contract["process_contract"]["controlled_runtime_root_template"]).split("/pair_<", 1)[0],
        AUDIT_RELATIVE_PATH.rsplit("/INDEPENDENT_AUDIT.json", 1)[0],
    }
    if fixed_v8_roots & forbidden_v7_roots or len(fixed_v8_roots) != 3:
        raise LockedPairBootstrapV8Error("attempt08_fixed_root_separation_mismatch")
    if not _exact_typed_equal(contract["runtime_dependency_truth"], {
        "inherited_attempt05_child_closure_count": 35,
        "complete_recursive_project_file_reads_of_bound_v5_extractor": True,
        "blender_executable_locked_and_hashed": True,
        "bootstrap_python_executable_locked_and_hashed": True,
        "attempt05_and_attempt04_controller_child_cores_locked_and_hashed": True,
        "controller_compiled_from_retained_locked_bytes": True,
        "structured_audit_parsed_before_private_controller_compile": True,
        "external_bootstrap_already_executing_bytes_cannot_self_prove": True,
        "external_bootstrap_is_explicit_independent_audit_trust_root": True,
        "controller_reverifies_kernel_issuer_before_context_contract_access": True,
        "accepted_attempt07_static_and_failure_graph_locked_and_hashed": True,
        "accepted_attempt07_runtime_tree_exactly_observed": True,
        "windows_system_dlls_and_blender_bundled_dynamic_runtime_files_individually_sealed": False,
        "windows_system_dlls_and_blender_bundled_dynamic_runtime_files_are_platform_dependencies": True,
        "network_dependency_expected": False,
        "model_dependency_expected": False,
        "unlisted_project_file_read_authorized": False,
    }):
        raise LockedPairBootstrapV8Error("runtime_dependency_truth_mismatch")
    if not _exact_typed_equal(contract["truth_boundary"], {
        "pair_pass_would_only_satisfy_foundation_afes_plus_transition_vertex_set_audit": True,
        "semantic_cage_still_required": True,
        "positive_jacobian_and_intersection_fixtures_still_required": True,
        "body_authoring_not_granted": True,
        "candidate_not_created": True,
        "owner_review_not_implied": True,
        "runtime_authority_not_implied": True,
        "static_package_is_not_execution_authority_until_fresh_independent_audit": True,
        "attempts_01_through_07_and_all_audits_and_failure_evidence_preserved": True,
    }):
        raise LockedPairBootstrapV8Error("locked_truth_boundary_mismatch")


def _load_v5_bootstrap_core(
    contract: Mapping[str, Any], ledger: LockedByteLedger,
) -> ModuleType:
    path, source = ledger.read_exact(
        contract["execution_sources"]["attempt05_bootstrap_core"],
        label="attempt05_bootstrap_core",
    )
    real_import = builtins.__import__

    def guarded_import(
        name: str, globals: object = None, locals: object = None,
        fromlist: Sequence[str] = (), level: int = 0,
    ) -> object:
        if name == "tools" or name.startswith("tools."):
            raise LockedPairBootstrapV8Error(f"ambient_project_import_forbidden:{name}")
        return real_import(name, globals, locals, fromlist, level)

    private = ModuleType(f"_kira_private_attempt05_bootstrap_core_{secrets.token_hex(16)}")
    private.__file__ = str(path)
    private.__package__ = ""
    private.__spec__ = None
    private.__loader__ = None
    private_builtins = dict(vars(builtins))
    private_builtins["__import__"] = guarded_import
    private.__dict__["__builtins__"] = private_builtins
    exec(compile(source, str(path), "exec", dont_inherit=True), private.__dict__, private.__dict__)
    if any(private is module for module in sys.modules.values()):
        raise LockedPairBootstrapV8Error("attempt05_bootstrap_core_entered_sys_modules")
    return private


def _expected_audit_artifacts(
    contract: Mapping[str, Any], retained_contract_bytes: bytes,
    expected_contract_sha256: str,
) -> dict[str, object]:
    return {
        "contract": {
            "path": CONTRACT_RELATIVE_PATH,
            "bytes": len(retained_contract_bytes),
            "sha256": expected_contract_sha256,
        },
        "execution_sources": dict(contract["execution_sources"]),
        "inherited_attempt05_contract": dict(contract["inherited_attempt05_contract"]),
        "preserved_rejected_attempt05": dict(contract["preserved_rejected_attempt05"]),
        "preserved_rejected_attempt06": dict(contract["preserved_rejected_attempt06"]),
        "inherited_accepted_attempt07_contract": dict(
            contract["inherited_accepted_attempt07_contract"]
        ),
        "preserved_accepted_attempt07": dict(contract["preserved_accepted_attempt07"]),
        "preserved_attempt07_failure_evidence": dict(
            contract["preserved_attempt07_failure_evidence"]
        ),
        "preserved_attempt07_runtime_tree": dict(
            contract["preserved_attempt07_runtime_tree"]
        ),
        "attempt07_failure_truth": dict(contract["attempt07_failure_truth"]),
    }


def _validate_structured_audit(
    *, audit_bytes: bytes, contract: Mapping[str, Any],
    expected_contract_sha256: str, retained_contract_bytes: bytes,
) -> dict[str, Any]:
    audit = _parse_json(audit_bytes, "independent_audit")
    if set(audit) != {
        "schema", "attempt_id", "decision", "reviewed_execution_artifacts",
        "recursive_closure_sha256", "truth_boundary",
    }:
        raise LockedPairBootstrapV8Error("audit_top_level_schema_mismatch")
    if audit["schema"] != "kira.avatar.r25.foundation_afes_locked_pair_independent_audit.v8":
        raise LockedPairBootstrapV8Error("audit_schema_mismatch")
    if audit["attempt_id"] != "attempt_08":
        raise LockedPairBootstrapV8Error("audit_attempt_mismatch")
    if not _exact_typed_equal(audit["decision"], {
        "accepted": True,
        "code": "ACCEPTED_FOR_ONE_BOUNDED_READ_ONLY_PAIR_ONLY",
        "scope": "ONE_FRESH_LOCKED_AFES_DIAGNOSTIC_PAIR",
    }):
        raise LockedPairBootstrapV8Error("audit_authoritative_decision_not_acceptance")
    if _sha256_bytes(retained_contract_bytes) != expected_contract_sha256:
        raise LockedPairBootstrapV8Error("audit_contract_bytes_changed")
    if not _exact_typed_equal(
        audit["reviewed_execution_artifacts"],
        _expected_audit_artifacts(contract, retained_contract_bytes, expected_contract_sha256),
    ):
        raise LockedPairBootstrapV8Error("audit_artifact_binding_mismatch")
    if audit["recursive_closure_sha256"] != contract[
        "recursive_closure_contract"
    ]["canonical_closure_sha256"]:
        raise LockedPairBootstrapV8Error("audit_recursive_closure_binding_mismatch")
    if not _exact_typed_equal(audit["truth_boundary"], {
        "body_authoring_authorized": False,
        "one_bounded_pair_authorized": True,
        "owner_body_approval": False,
        "static_review_did_not_run_blender": True,
    }):
        raise LockedPairBootstrapV8Error("audit_truth_boundary_mismatch")
    return audit


def _verify_locked_graph(
    *, contract_path: Path, ledger: LockedByteLedger,
    expected_contract_sha256: str, accepted_audit_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    contract_bytes = ledger.read_path(contract_path)
    if _sha256_bytes(contract_bytes) != expected_contract_sha256:
        raise LockedPairBootstrapV8Error("locked_contract_digest_mismatch")
    contract = _parse_json(contract_bytes, "locked_contract")
    if contract.get("schema") != "kira.avatar.r25.foundation_afes_locked_pair_execution.v8":
        raise LockedPairBootstrapV8Error("locked_contract_schema_mismatch")
    if contract.get("attempt_id") != "attempt_08" or contract.get("status") != (
        "PENDING_FRESH_INDEPENDENT_AUDIT_READ_ONLY_DIAGNOSTIC_PAIR_ONLY"
    ):
        raise LockedPairBootstrapV8Error("locked_contract_identity_mismatch")
    _validate_exact_contract_sections(contract)
    for label, row in contract["execution_sources"].items():
        path, _ = ledger.read_exact(row, label=str(label))
        if label == "external_bootstrap" and path != Path(__file__).resolve(strict=True):
            raise LockedPairBootstrapV8Error("external_bootstrap_path_mismatch")
    for label, row in contract["preserved_rejected_attempt05"].items():
        ledger.read_exact(row, label=f"preserved_attempt05.{label}")
    for label, row in contract["preserved_rejected_attempt06"].items():
        ledger.read_exact(row, label=f"preserved_attempt06.{label}")
    for label, row in contract["preserved_accepted_attempt07"].items():
        ledger.read_exact(row, label=f"preserved_attempt07.{label}")
    for label, row in contract["preserved_attempt07_failure_evidence"].items():
        _, evidence = ledger.read_exact(row, label=f"attempt07_failure_evidence.{label}")
        if label == "run_01_raw_frame" and evidence != b"":
            raise LockedPairBootstrapV8Error("attempt07_raw_frame_not_empty")
        if label == "run_01_stderr":
            stderr = evidence.decode("utf-8", errors="strict")
            if (
                "R25_AFES_LOCKED_CHILD_V7_FAILED:NameError:name 'ctypes' is not defined" not in stderr
                or 'line 238, in _require_pipe' not in stderr
            ):
                raise LockedPairBootstrapV8Error("attempt07_stderr_cause_mismatch")
    _, inherited_v7_bytes = ledger.read_exact(
        contract["inherited_accepted_attempt07_contract"],
        label="inherited_accepted_attempt07_contract",
    )
    inherited_v7 = _parse_json(inherited_v7_bytes, "inherited_attempt07_contract")
    if (
        inherited_v7.get("schema")
        != "kira.avatar.r25.foundation_afes_locked_pair_execution.v7"
        or inherited_v7.get("attempt_id") != "attempt_07"
    ):
        raise LockedPairBootstrapV8Error("inherited_attempt07_contract_identity_mismatch")
    if not _exact_typed_equal(_observe_attempt07_runtime_tree(), PRESERVED_ATTEMPT07_RUNTIME_TREE):
        raise LockedPairBootstrapV8Error("attempt07_runtime_tree_drift_under_lock")
    _, inherited_v5_bytes = ledger.read_exact(
        contract["inherited_attempt05_contract"], label="inherited_attempt05_contract",
    )
    inherited_v5 = _parse_json(inherited_v5_bytes, "inherited_attempt05_contract")
    if inherited_v5.get("schema") != "kira.avatar.r25.foundation_afes_locked_pair_execution.v5":
        raise LockedPairBootstrapV8Error("inherited_attempt05_contract_schema_mismatch")
    _, inherited_v4_bytes = ledger.read_exact(
        inherited_v5["inherited_attempt04_contract"],
        label="inherited_attempt04_contract",
    )
    inherited_v4 = _parse_json(inherited_v4_bytes, "inherited_attempt04_contract")
    if inherited_v4.get("schema") != "kira.avatar.r25.foundation_afes_locked_pair_execution.v4":
        raise LockedPairBootstrapV8Error("inherited_attempt04_contract_schema_mismatch")
    closure = inherited_v4.get("child_project_read_closure")
    if not isinstance(closure, Mapping) or len(closure) != 35:
        raise LockedPairBootstrapV8Error("declared_child_closure_count_mismatch")
    for label, row in closure.items():
        ledger.read_exact(row, label=str(label))
    _, afes_v5_bytes = ledger.read_exact(closure["afes_v5_config"], label="afes_v5_config")
    afes_v5 = _parse_json(afes_v5_bytes, "afes_v5_config")
    v5_bootstrap = _load_v5_bootstrap_core(contract, ledger)
    derived = v5_bootstrap._derive_recursive_child_rows(afes_v5, ledger)
    declared_by_path = {str(row["path"]): dict(row) for row in closure.values()}
    if len(declared_by_path) != 35 or declared_by_path != derived:
        raise LockedPairBootstrapV8Error("recursive_child_read_closure_mismatch")
    if not REQUIRED_MISSING_V2_PATHS.issubset(declared_by_path):
        raise LockedPairBootstrapV8Error("five_previously_missing_v2_inputs_absent")
    closure_hash = _sha256_bytes(_canonical_json_bytes(declared_by_path))
    if not _exact_typed_equal(contract["recursive_closure_contract"], {
        "algorithm": "exact_inherited_attempt05_attempt04_v5_v4_v3_v2_table_walk",
        "unique_project_file_count": 35,
        "canonical_closure_sha256": closure_hash,
        "includes_all_five_attempt03_audit_omissions": True,
        "verified_under_complete_parent_lock_set": True,
    }):
        raise LockedPairBootstrapV8Error("recursive_closure_contract_mismatch")
    audit_bytes = ledger.read_path(_project_file(AUDIT_RELATIVE_PATH))
    if _sha256_bytes(audit_bytes) != accepted_audit_sha256:
        raise LockedPairBootstrapV8Error("independent_audit_digest_mismatch")
    _validate_structured_audit(
        audit_bytes=audit_bytes, contract=contract,
        expected_contract_sha256=expected_contract_sha256,
        retained_contract_bytes=contract_bytes,
    )
    return contract, inherited_v5, inherited_v4


class BootstrapContext:
    def __init__(
        self, *, locks: Any, ledger: LockedByteLedger, contract: dict[str, Any],
        inherited_attempt05_contract: dict[str, Any],
        inherited_attempt04_contract: dict[str, Any], contract_path: Path,
        expected_contract_sha256: str, accepted_audit_sha256: str,
    ) -> None:
        self._locks = locks
        self.ledger = ledger
        self.contract = contract
        self.inherited_attempt05_contract = inherited_attempt05_contract
        self.inherited_attempt04_contract = inherited_attempt04_contract
        self.contract_path = contract_path
        self.expected_contract_sha256 = expected_contract_sha256
        self.accepted_audit_sha256 = accepted_audit_sha256
        self.controller_private_execution = True
        self.before_snapshot = ledger.complete_snapshot()

    @property
    def locks_active(self) -> bool:
        return bool(self._locks.active)

    def snapshot_locked_files(self) -> dict[str, dict[str, object]]:
        if not self._locks.active:
            raise LockedPairBootstrapV8Error("snapshot_without_active_locks")
        observed = {Path(path).resolve(strict=True) for path in self._locks.locked_paths}
        if observed != self.ledger.allowed:
            raise LockedPairBootstrapV8Error("snapshot_without_complete_lock_set")
        return {
            str(path): {"bytes": path.stat().st_size, "sha256": _sha256_file(path)}
            for path in sorted(observed, key=lambda item: str(item).casefold())
        }


def _with_complete_locks(
    paths: Iterable[Path], body: Callable[[Any], Any],
    *, lock_factory: Callable[[], Any] = WindowsReadLockSet,
) -> Any:
    with lock_factory() as locks:
        for path in paths:
            locks.add(path)
        return body(locks)


def launch_pair(expected_contract_sha256: str, accepted_audit_sha256: str) -> Path:
    for label, value in (
        ("expected_contract_sha256", expected_contract_sha256),
        ("accepted_audit_sha256", accepted_audit_sha256),
    ):
        if not isinstance(value, str) or HEX64.fullmatch(value) is None:
            raise LockedPairBootstrapV8Error(f"{label}_must_be_64_lowercase_hex")
    contract_path, paths = _untrusted_discovery(require_audit=True)
    expected = {path.resolve(strict=True) for path in paths}

    def locked_body(locks: Any) -> Path:
        observed = {Path(path).resolve(strict=True) for path in locks.locked_paths}
        if not locks.active or observed != expected:
            raise LockedPairBootstrapV8Error("complete_lock_set_not_held")
        ledger = LockedByteLedger(locks, expected)
        contract, inherited_v5, inherited_v4 = _verify_locked_graph(
            contract_path=contract_path, ledger=ledger,
            expected_contract_sha256=expected_contract_sha256,
            accepted_audit_sha256=accepted_audit_sha256,
        )
        for path in sorted(expected, key=lambda item: str(item).casefold()):
            ledger.read_path(path)
        context = BootstrapContext(
            locks=locks, ledger=ledger, contract=contract,
            inherited_attempt05_contract=inherited_v5,
            inherited_attempt04_contract=inherited_v4,
            contract_path=contract_path,
            expected_contract_sha256=expected_contract_sha256,
            accepted_audit_sha256=accepted_audit_sha256,
        )

        # The claim closure exists only inside this exact verified and locked
        # invocation. The controller must additionally prove that the kernel
        # process really executed this exact bootstrap under -I -S -B.
        row = contract["execution_sources"]["private_controller"]
        controller_path, source = ledger.read_exact(row, label="private_controller")
        capability = object()
        issuer_nonce = secrets.token_hex(32)
        issuer_envelope = _build_issuer_envelope(
            contract=contract, controller_path=controller_path,
            expected_contract_sha256=expected_contract_sha256,
            accepted_audit_sha256=accepted_audit_sha256,
            issuer_nonce=issuer_nonce,
        )
        real_import = builtins.__import__

        def guarded_import(
            name: str, globals: object = None, locals: object = None,
            fromlist: Sequence[str] = (), level: int = 0,
        ) -> object:
            if name == "tools" or name.startswith("tools."):
                raise LockedPairBootstrapV8Error(
                    f"ambient_project_import_forbidden:{name}"
                )
            return real_import(name, globals, locals, fromlist, level)

        controller = ModuleType(
            f"_kira_private_afes_locked_pair_controller_v8_{secrets.token_hex(16)}"
        )
        controller.__file__ = str(controller_path)
        controller.__package__ = ""
        controller.__spec__ = None
        controller.__loader__ = None
        private_builtins = dict(vars(builtins))
        private_builtins["__import__"] = guarded_import
        private_builtins["__kira_bootstrap_claim_v8__"] = (
            capability, context, issuer_envelope,
        )
        controller.__dict__["__builtins__"] = private_builtins
        try:
            exec(
                compile(source, str(controller_path), "exec", dont_inherit=True),
                controller.__dict__, controller.__dict__,
            )
        finally:
            unconsumed_claim = private_builtins.pop(
                "__kira_bootstrap_claim_v8__", None,
            )
        if unconsumed_claim is not None:
            raise LockedPairBootstrapV8Error(
                "controller_did_not_consume_private_issuer_claim"
            )
        if any(controller is module for module in sys.modules.values()):
            raise LockedPairBootstrapV8Error("private_controller_entered_sys_modules")
        entry = getattr(controller, "run_locked_pair", None)
        if not callable(entry) or Path(entry.__code__.co_filename).resolve(strict=True) != controller_path:
            raise LockedPairBootstrapV8Error("private_controller_entrypoint_drift")
        return entry(
            bootstrap_context=context, bootstrap_capability=capability,
            expected_contract_sha256=expected_contract_sha256,
            accepted_audit_sha256=accepted_audit_sha256,
        )

    return _with_complete_locks(paths, locked_body)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-contract-sha256", required=True)
    parser.add_argument("--accepted-audit-sha256", required=True)
    return parser.parse_args()


def main() -> int:
    values = _arguments()
    try:
        launch_pair(values.expected_contract_sha256, values.accepted_audit_sha256)
    except Exception as exc:
        print(
            f"R25_AFES_LOCKED_PAIR_V8_FAILED:{type(exc).__name__}:{exc}",
            file=sys.stderr,
        )
        return 1
    print("R25_AFES_LOCKED_PAIR_V8_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
