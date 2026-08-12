#!/usr/bin/env python3
"""Attempt05 shim around the byte-exact sealed reseal-v3 Blender engine.

The controller supplies the v3 engine through an inherited locked handle.  The
shim verifies those exact bytes before compiling them, changes only the v4
config location and the append-only Attempt05 output binding, and then delegates
to the reviewed engine.  Direct execution without the controller lease fails.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt05_reseal_v4_preparation/"
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT05_RESEAL_V4_CONFIG.json"
)
ENGINE_LABEL = "reseal_v3_wrapper_engine"
ENGINE_PATH = ROOT / "tools/blender_author_kira_r23_cc0_afes_attempt04_reseal_v3_wrapper.py"
ENGINE_BYTES = 43730
ENGINE_SHA256 = "3f5188a714df38c8f2cd5931de9bc0d2ed6de3c3fcd73e8a62b0f62c63f9cbe9"
ATTEMPT05_OUTPUT = (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author/attempt_05"
)
ATTEMPT05_CANDIDATE = "kira_r23_cc0_afes_core_transfer_attempt_05.blend"
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
FILE_BEGIN = 0


class BlenderResealV4ShimError(RuntimeError):
    """Fail-closed error before control reaches the sealed v3 engine."""


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


def _api() -> Any:
    if os.name != "nt":
        raise BlenderResealV4ShimError("Attempt05 locked-engine shim requires Windows")
    api = ctypes.WinDLL("kernel32", use_last_error=True)
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
    return api


def _win_error(action: str) -> BlenderResealV4ShimError:
    return BlenderResealV4ShimError(
        f"{action} failed: WinError {ctypes.get_last_error()}"
    )


def _normal_path(value: str) -> str:
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return os.path.normcase(os.path.abspath(value))


def _lease() -> dict[str, Any]:
    raw = os.environ.get("KIRA_R23_RESEAL_V3_LOCK_LEASE_JSON", "")
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise BlenderResealV4ShimError(
            f"locked handle lease is absent/invalid: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise BlenderResealV4ShimError("locked handle lease root is not an object")
    return value


def _read_locked_engine() -> bytes:
    row = _lease().get(ENGINE_LABEL)
    if not isinstance(row, dict):
        raise BlenderResealV4ShimError("sealed v3 wrapper-engine handle is absent")
    required = {"handle", "path", "bytes", "sha256", "file_identity"}
    if set(row) != required:
        raise BlenderResealV4ShimError("sealed engine lease fields drifted")
    if row["path"] != ENGINE_PATH.resolve().relative_to(ROOT.resolve()).as_posix():
        raise BlenderResealV4ShimError("sealed engine lease path is not canonical")
    handle = int(row["handle"])
    api = _api()
    info = _ByHandleInfo()
    if not api.GetFileInformationByHandle(handle, ctypes.byref(info)):
        raise _win_error("GetFileInformationByHandle(engine)")
    if info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT:
        raise BlenderResealV4ShimError("sealed engine handle is a reparse point")
    identity = {
        "volume_serial": int(info.dwVolumeSerialNumber),
        "file_index_high": int(info.nFileIndexHigh),
        "file_index_low": int(info.nFileIndexLow),
        "links": int(info.nNumberOfLinks),
    }
    if identity != row["file_identity"]:
        raise BlenderResealV4ShimError("sealed engine file identity drifted")
    size = (int(info.nFileSizeHigh) << 32) | int(info.nFileSizeLow)
    if size != int(row["bytes"]) or size != ENGINE_BYTES:
        raise BlenderResealV4ShimError("sealed engine byte length drifted")
    length = api.GetFinalPathNameByHandleW(handle, None, 0, 0)
    if not length:
        raise _win_error("GetFinalPathNameByHandleW(engine length)")
    buffer = ctypes.create_unicode_buffer(length + 1)
    result = api.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
    if not result or result >= len(buffer):
        raise _win_error("GetFinalPathNameByHandleW(engine value)")
    if _normal_path(buffer.value) != _normal_path(str(ENGINE_PATH)):
        raise BlenderResealV4ShimError("sealed engine final path drifted")
    target = ctypes.c_longlong()
    if not api.SetFilePointerEx(handle, 0, ctypes.byref(target), FILE_BEGIN):
        raise _win_error("SetFilePointerEx(engine)")
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        amount = min(1024 * 1024, remaining)
        block = ctypes.create_string_buffer(amount)
        count = wintypes.DWORD()
        if not api.ReadFile(handle, block, amount, ctypes.byref(count), None):
            raise _win_error("ReadFile(engine)")
        if count.value == 0:
            raise BlenderResealV4ShimError("sealed engine handle ended early")
        chunks.append(block.raw[: count.value])
        remaining -= int(count.value)
    source = b"".join(chunks)
    if hashlib.sha256(source).hexdigest() != row["sha256"]:
        raise BlenderResealV4ShimError("lease engine hash drifted")
    if hashlib.sha256(source).hexdigest() != ENGINE_SHA256:
        raise BlenderResealV4ShimError("sealed v3 wrapper engine hash drifted")
    return source


def _expected_attempt05_repair_contract(
    original_repair_overlay: Mapping[str, Any],
) -> dict[str, Any]:
    expected = dict(original_repair_overlay["repair_contract"])
    expected["effective_output"] = ATTEMPT05_OUTPUT
    expected["effective_candidate"] = ATTEMPT05_CANDIDATE
    return expected


def _load_engine_namespace() -> dict[str, Any]:
    source = _read_locked_engine()
    namespace: dict[str, Any] = {
        "__name__": "_kira_r23_reseal_v3_blender_engine",
        "__file__": str(Path(__file__).resolve()),
        "__package__": None,
    }
    exec(
        compile(source, str(ENGINE_PATH), "exec", dont_inherit=True),
        namespace,
    )
    namespace["CONFIG_PATH"] = CONFIG_PATH

    original_load_verified_sources = namespace["load_verified_sources"]

    def load_verified_sources(
        config: Mapping[str, Any], data: Mapping[str, bytes]
    ) -> Any:
        topology = original_load_verified_sources(config, data)
        topology.EFFECTIVE_ATTEMPT04_OUTPUT = ATTEMPT05_OUTPUT
        topology.EFFECTIVE_ATTEMPT04_CANDIDATE = ATTEMPT05_CANDIDATE
        return topology

    original_apply_config_handoff = namespace["apply_config_handoff"]

    def apply_config_handoff(
        topology: Any,
        config: Mapping[str, Any],
        command: Sequence[str],
        author_config: Mapping[str, Any],
        repair_overlay: Mapping[str, Any],
        original_repair_overlay: Mapping[str, Any],
    ) -> dict[str, Any]:
        expected = _expected_attempt05_repair_contract(original_repair_overlay)
        if repair_overlay.get("repair_contract") != expected:
            raise namespace["BlenderResealV3Error"](
                "Attempt05 overlay differs beyond the exact approved output rebind"
            )
        compatibility_overlay = dict(repair_overlay)
        compatibility_overlay["repair_contract"] = original_repair_overlay[
            "repair_contract"
        ]
        record = original_apply_config_handoff(
            topology,
            config,
            command,
            author_config,
            compatibility_overlay,
            original_repair_overlay,
        )
        record["attempt05_output_rebind"] = {
            "effective_output": ATTEMPT05_OUTPUT,
            "effective_candidate": ATTEMPT05_CANDIDATE,
            "only_repair_contract_fields_changed": [
                "effective_candidate",
                "effective_output",
            ],
        }
        return record

    namespace["load_verified_sources"] = load_verified_sources
    namespace["apply_config_handoff"] = apply_config_handoff
    return namespace


def main() -> int:
    engine = _load_engine_namespace()
    return int(engine["main"]())


if __name__ == "__main__":
    raise SystemExit(main())
