#!/usr/bin/env python3
"""Immutable-handle Blender bootstrap for R23 Attempt04 reseal v3.

The controller must already hold and pass the complete input lease.  This is
the first project script Blender executes.  It validates complete ``sys.argv``,
the same locked bytes reviewed by authorization, the atomic claim, and PRE_RUN
before compiling any other project-local source.  The topology repair overlay
and inherited Attempt01 author config remain distinct inputs.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import types
from typing import Any, Mapping, Sequence

import bpy


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_reseal_v3_preparation/"
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT04_RESEAL_V3_CONFIG.json"
)
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_BEGIN = 0
WAIT_OBJECT_0 = 0
PROCESS_DUP_HANDLE = 0x0040
DUPLICATE_CLOSE_SOURCE = 0x00000001
DUPLICATE_SAME_ACCESS = 0x00000002


class BlenderResealV3Error(RuntimeError):
    """Fail-closed v3 Blender bootstrap error."""


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
        raise BlenderResealV3Error("v3 Blender bootstrap requires Windows")
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
    api.SetEvent.argtypes = [wintypes.HANDLE]
    api.SetEvent.restype = wintypes.BOOL
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.WaitForSingleObject.restype = wintypes.DWORD
    api.GetCurrentProcess.argtypes = []
    api.GetCurrentProcess.restype = wintypes.HANDLE
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
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


def _win_error(action: str) -> BlenderResealV3Error:
    return BlenderResealV3Error(
        f"{action} failed: WinError {ctypes.get_last_error()}"
    )


def _normal_final_path(value: str) -> str:
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return os.path.normcase(os.path.abspath(value))


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _evidence_path(path: Path) -> str:
    try:
        return _relative(path)
    except ValueError:
        return Path(os.path.abspath(path)).as_posix()


def _project_path(raw: str) -> Path:
    value = PurePosixPath(raw.replace("\\", "/"))
    if value.is_absolute() or not value.parts or any(
        part in {"", ".", ".."} for part in value.parts
    ):
        raise BlenderResealV3Error(f"unsafe project path: {raw}")
    return ROOT.joinpath(*value.parts)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


class LockedHandle:
    def __init__(
        self,
        handle: int,
        expected_path: Path,
        *,
        directory: bool = False,
        owned: bool = False,
    ):
        self.handle = int(handle)
        self.expected_path = expected_path
        self.directory = directory
        self.owned = owned
        self.api = _api()
        self.info = self._info()
        self.final_path = self._final_path()
        if _normal_final_path(self.final_path) != _normal_final_path(str(expected_path)):
            self.close()
            raise BlenderResealV3Error(
                f"inherited handle path mismatch for {expected_path}: {self.final_path}"
            )
        if self.info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT:
            self.close()
            raise BlenderResealV3Error(f"reparse handle rejected: {expected_path}")

    @classmethod
    def open_existing(
        cls, path: Path, *, directory: bool = False, writable: bool = False
    ) -> "LockedHandle":
        api = _api()
        flags = FILE_FLAG_OPEN_REPARSE_POINT
        if directory:
            flags |= FILE_FLAG_BACKUP_SEMANTICS
        else:
            flags |= FILE_ATTRIBUTE_NORMAL
        access = GENERIC_READ | (GENERIC_WRITE if writable else 0)
        raw = api.CreateFileW(
            str(path), access, FILE_SHARE_READ, None, OPEN_EXISTING, flags, None
        )
        if int(raw) == int(ctypes.c_void_p(-1).value):
            raise _win_error(f"open locked output {path}")
        return cls(int(raw), path, directory=directory, owned=True)

    def _info(self) -> _ByHandleInfo:
        info = _ByHandleInfo()
        if not self.api.GetFileInformationByHandle(self.handle, ctypes.byref(info)):
            raise _win_error("GetFileInformationByHandle")
        return info

    def _final_path(self) -> str:
        length = self.api.GetFinalPathNameByHandleW(self.handle, None, 0, 0)
        if not length:
            raise _win_error("GetFinalPathNameByHandleW(length)")
        buffer = ctypes.create_unicode_buffer(length + 1)
        result = self.api.GetFinalPathNameByHandleW(
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

    def seek_start(self) -> None:
        target = ctypes.c_longlong()
        if not self.api.SetFilePointerEx(
            self.handle, 0, ctypes.byref(target), FILE_BEGIN
        ):
            raise _win_error("SetFilePointerEx")

    def read_bytes(self) -> bytes:
        if self.directory:
            raise BlenderResealV3Error("cannot read a directory handle")
        self.info = self._info()
        self.seek_start()
        chunks: list[bytes] = []
        remaining = self.size
        while remaining:
            amount = min(1024 * 1024, remaining)
            buffer = ctypes.create_string_buffer(amount)
            read = wintypes.DWORD()
            if not self.api.ReadFile(
                self.handle, buffer, amount, ctypes.byref(read), None
            ):
                raise _win_error("ReadFile")
            if read.value == 0:
                raise BlenderResealV3Error("locked file ended early")
            chunks.append(buffer.raw[: read.value])
            remaining -= int(read.value)
        return b"".join(chunks)

    def rewrite_bytes(self, value: bytes) -> None:
        self.seek_start()
        offset = 0
        while offset < len(value):
            block = value[offset : offset + 1024 * 1024]
            buffer = ctypes.create_string_buffer(block)
            written = wintypes.DWORD()
            if not self.api.WriteFile(
                self.handle, buffer, len(block), ctypes.byref(written), None
            ):
                raise _win_error("WriteFile")
            if int(written.value) != len(block):
                raise BlenderResealV3Error("short write to evidence handle")
            offset += len(block)
        if not self.api.SetEndOfFile(self.handle):
            raise _win_error("SetEndOfFile")
        if not self.api.FlushFileBuffers(self.handle):
            raise _win_error("FlushFileBuffers")
        self.info = self._info()

    def record(self, data: bytes | None = None) -> dict[str, Any]:
        if data is None and not self.directory:
            data = self.read_bytes()
        result: dict[str, Any] = {
            "path": _evidence_path(self.expected_path),
            "bytes": self.size,
            "final_path": self.final_path,
            "file_identity": self.identity,
            "reparse": False,
            "write_sharing_denied": True,
            "delete_sharing_denied": True,
        }
        if data is not None:
            result.update({"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        return result

    def close(self) -> None:
        if self.owned and self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = 0


def _lease_json() -> dict[str, Any]:
    raw = os.environ.get("KIRA_R23_RESEAL_V3_LOCK_LEASE_JSON", "")
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise BlenderResealV3Error(f"locked handle lease is absent/invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise BlenderResealV3Error("locked handle lease root is not an object")
    return value


def _inherited_handle(
    lease: Mapping[str, Any], label: str, *, require_hash: bool = True
) -> tuple[LockedHandle, bytes, dict[str, Any]]:
    row = lease.get(label)
    if not isinstance(row, dict):
        raise BlenderResealV3Error(f"missing inherited handle label: {label}")
    raw_path = str(row["path"])
    path = Path(raw_path) if Path(raw_path).is_absolute() else _project_path(raw_path)
    handle = LockedHandle(int(row["handle"]), path, owned=False)
    data = handle.read_bytes()
    actual = handle.record(data)
    if require_hash:
        if len(data) != int(row["bytes"]) or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise BlenderResealV3Error(f"inherited handle bytes drifted: {label}")
        if actual["file_identity"] != row["file_identity"]:
            raise BlenderResealV3Error(f"inherited file identity drifted: {label}")
    return handle, data, actual


def _json_bytes(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except Exception as exc:
        raise BlenderResealV3Error(f"invalid JSON for {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise BlenderResealV3Error(f"JSON root is not object for {label}")
    return value


def expected_command(config: Mapping[str, Any]) -> list[str]:
    artifacts = config["bound_artifacts"]
    source = _project_path(artifacts["r19_source_blend"]["path"])
    wrapper = _project_path(artifacts["reseal_v3_blender_wrapper"]["path"])
    return [
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
        *list(config["command_contract"]["worker_tail"]),
    ]


def validate_complete_argv(actual: Sequence[str], expected: Sequence[str]) -> None:
    values = list(actual)
    target = list(expected)
    if values != target:
        raise BlenderResealV3Error(
            "complete actual Blender argv differs from authorization: "
            f"actual={canonical_sha256(values)}, expected={canonical_sha256(target)}"
        )
    if values.count("--python") != 1 or "--python-expr" in values:
        raise BlenderResealV3Error("unexpected Blender Python execution flag")
    if values.count("--") != 1:
        raise BlenderResealV3Error("unexpected Blender argument delimiter count")


def _handoff(config: Mapping[str, Any]) -> dict[str, Any]:
    handoff = config["handoff_contract"]
    author_path = _project_path(handoff["sealed_author_config_argument"])
    overlay_path = _project_path(handoff["repair_overlay_config_argument"])
    return {
        "sealed_author_config": _relative(author_path),
        "sealed_author_schema": handoff["sealed_author_schema"],
        "repair_overlay_config": _relative(overlay_path),
        "repair_overlay_schema": handoff["repair_overlay_schema"],
        "worker_tail": [
            "--config",
            handoff["sealed_author_config_argument"],
            "--execute-authoring",
        ],
        "topology_overlay_assignment_only": True,
    }


def _wait_event(environment_key: str, timeout_ms: int) -> int:
    raw = os.environ.get(environment_key, "")
    try:
        handle = int(raw)
    except ValueError as exc:
        raise BlenderResealV3Error(f"invalid event handle: {environment_key}") from exc
    result = _api().WaitForSingleObject(handle, int(timeout_ms))
    if result != WAIT_OBJECT_0:
        raise BlenderResealV3Error(f"event wait failed/timed out: {environment_key}")
    return handle


def bootstrap() -> tuple[
    dict[str, Any],
    dict[str, LockedHandle],
    dict[str, bytes],
    dict[str, dict[str, Any]],
    dict[str, Any],
]:
    lease = _lease_json()
    config_handle, config_bytes, config_record = _inherited_handle(
        lease, "reseal_v3_config"
    )
    config = _json_bytes(config_bytes, "reseal_v3_config")
    if config.get("schema") != "kira.avatar.r23_author_attempt04_reseal_v3.v1":
        raise BlenderResealV3Error("wrong v3 config schema")
    expected_labels = set(config["bound_artifacts"]) | {
        "reseal_v3_config",
        "reseal_v3_manifest",
        "authorization_record",
        "authorization_manifest",
        "blender_executable",
        "authorization_claim",
        "pre_run",
    }
    if set(lease) != expected_labels:
        raise BlenderResealV3Error(
            f"inherited handle label closure drifted: {sorted(set(lease) ^ expected_labels)}"
        )
    command = expected_command(config)
    validate_complete_argv(sys.argv, command)
    handles: dict[str, LockedHandle] = {"reseal_v3_config": config_handle}
    data: dict[str, bytes] = {"reseal_v3_config": config_bytes}
    records: dict[str, dict[str, Any]] = {"reseal_v3_config": config_record}
    for label in sorted(set(config["bound_artifacts"]) | {"reseal_v3_manifest", "authorization_record", "authorization_manifest", "blender_executable"}):
        handle, raw, record = _inherited_handle(lease, label)
        handles[label] = handle
        data[label] = raw
        records[label] = record
        if label in config["bound_artifacts"]:
            binding = config["bound_artifacts"][label]
            if (
                record["path"] != binding["path"]
                or record["bytes"] != int(binding["bytes"])
                or record["sha256"] != binding["sha256"]
            ):
                raise BlenderResealV3Error(f"bound lease differs from config: {label}")
    blender_record = records["blender_executable"]
    blender_identity = config["blender_identity"]
    if (
        _normal_final_path(blender_record["final_path"])
        != _normal_final_path(blender_identity["path"])
        or blender_record["bytes"] != int(blender_identity["bytes"])
        or blender_record["sha256"] != blender_identity["sha256"]
    ):
        raise BlenderResealV3Error("locked Blender executable differs from identity")
    manifest = _json_bytes(data["reseal_v3_manifest"], "reseal_v3_manifest")
    artifact_map = {str(row["path"]): row for row in manifest.get("artifacts", [])}
    config_manifest_binding = artifact_map.get(CONFIG_PATH.as_posix())
    if config_manifest_binding is None:
        raise BlenderResealV3Error("package manifest does not bind v3 config")
    if (
        config_manifest_binding["bytes"] != len(config_bytes)
        or config_manifest_binding["sha256"] != hashlib.sha256(config_bytes).hexdigest()
    ):
        raise BlenderResealV3Error("locked config differs from package manifest")
    wrapper_record = records["reseal_v3_blender_wrapper"]
    if _normal_final_path(wrapper_record["final_path"]) != _normal_final_path(__file__):
        raise BlenderResealV3Error("executing wrapper is not the locked reviewed wrapper")
    source_record = records["r19_source_blend"]
    if _normal_final_path(source_record["final_path"]) != _normal_final_path(command[4]):
        raise BlenderResealV3Error("loaded source argument is not the locked reviewed Blend")

    _wait_event("KIRA_R23_RESEAL_V3_READY_EVENT_HANDLE", 120_000)
    for label in ("authorization_claim", "pre_run"):
        handle, raw, record = _inherited_handle(lease, label, require_hash=False)
        handles[label] = handle
        data[label] = raw
        records[label] = record
    execution_directory = _project_path(config["output_contract"]["execution_directory"])
    journal = config["journal_contract"]
    expected_claim_path = execution_directory / journal["claim_basename"]
    expected_pre_path = execution_directory / journal["pre_run_basename"]
    if records["authorization_claim"]["path"] != _relative(expected_claim_path):
        raise BlenderResealV3Error("claim handle path differs from journal contract")
    if records["pre_run"]["path"] != _relative(expected_pre_path):
        raise BlenderResealV3Error("PRE handle path differs from journal contract")
    if os.environ.get("KIRA_R23_RESEAL_V3_CLAIM_PATH") != _relative(expected_claim_path):
        raise BlenderResealV3Error("claim environment path differs")
    if os.environ.get("KIRA_R23_RESEAL_V3_PRE_RUN_PATH") != _relative(expected_pre_path):
        raise BlenderResealV3Error("PRE environment path differs")
    claim = _json_bytes(data["authorization_claim"], "authorization_claim")
    pre = _json_bytes(data["pre_run"], "pre_run")
    auth_record = _json_bytes(data["authorization_record"], "authorization_record")
    auth_manifest = _json_bytes(data["authorization_manifest"], "authorization_manifest")
    auth_record_hash = hashlib.sha256(data["authorization_record"]).hexdigest()
    auth_manifest_hash = hashlib.sha256(data["authorization_manifest"]).hexdigest()
    if claim.get("artifact_kind") != "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V3_AUTHORIZATION_CLAIM":
        raise BlenderResealV3Error("wrong atomic claim kind")
    if claim.get("controller_pid") != os.getppid() or claim.get("child_pid") != os.getpid():
        raise BlenderResealV3Error("atomic claim parent/child identity differs")
    if claim.get("command") != command or claim.get("command_sha256") != canonical_sha256(command):
        raise BlenderResealV3Error("atomic claim command differs")
    if (
        claim.get("authorization_record_sha256") != auth_record_hash
        or claim.get("authorization_manifest_sha256") != auth_manifest_hash
    ):
        raise BlenderResealV3Error("atomic claim authorization hashes differ")
    contract = config["authorization_contract"]
    if set(auth_record) != {
        "schema",
        "authorized",
        "one_run_only",
        "authorization_id",
        "nonce",
        "owner_decision_text",
        "command_sha256",
        "reviewed",
        "restrictions",
    }:
        raise BlenderResealV3Error("authorization record field closure differs")
    if set(auth_manifest) != {"schema", "authorization_id", "record"}:
        raise BlenderResealV3Error("authorization manifest field closure differs")
    if auth_record.get("schema") != contract["record_schema"] or auth_manifest.get("schema") != contract["manifest_schema"]:
        raise BlenderResealV3Error("authorization schema differs")
    expected_record_binding = {
        "path": records["authorization_record"]["path"],
        "bytes": len(data["authorization_record"]),
        "sha256": auth_record_hash,
    }
    if auth_manifest.get("record") != expected_record_binding:
        raise BlenderResealV3Error("authorization manifest does not bind same-handle record")
    if auth_manifest.get("authorization_id") != auth_record.get("authorization_id"):
        raise BlenderResealV3Error("authorization manifest ID differs from record")
    if auth_record.get("authorized") is not True or auth_record.get("one_run_only") is not True:
        raise BlenderResealV3Error("authorization does not permit one bounded run")
    if not isinstance(auth_record.get("owner_decision_text"), str) or not auth_record[
        "owner_decision_text"
    ].strip():
        raise BlenderResealV3Error("authorization owner decision is empty")
    if claim.get("authorization_id") != auth_record.get("authorization_id") or claim.get("authorization_nonce") != auth_record.get("nonce"):
        raise BlenderResealV3Error("claim and authorization identity differ")
    if auth_record.get("command_sha256") != canonical_sha256(command):
        raise BlenderResealV3Error("authorization command hash differs")
    reviewed = {
        label: records[label]
        for label in contract["reviewed_binding_labels"]
    }
    reviewed.update(
        {
            "blender_identity": config["blender_identity"],
            "blender_executable": records["blender_executable"],
            "handoff": _handoff(config),
            "command": command,
            "command_sha256": canonical_sha256(command),
            "output_contract": config["output_contract"],
        }
    )
    if auth_record.get("reviewed") != reviewed:
        raise BlenderResealV3Error("authorization reviewed bindings differ in child")
    if auth_record.get("restrictions") != contract["required_restrictions"]:
        raise BlenderResealV3Error("authorization restriction set differs")
    if pre.get("artifact_kind") != "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V3_PRE_RUN":
        raise BlenderResealV3Error("wrong PRE_RUN kind")
    if pre.get("command") != command or pre.get("command_sha256") != canonical_sha256(command):
        raise BlenderResealV3Error("PRE_RUN command differs")
    if pre.get("authorization_claim_sha256") != canonical_sha256(claim):
        raise BlenderResealV3Error("PRE_RUN does not bind final claim")
    pre_authorization = pre.get("authorization")
    expected_pre_authorization = {
        "authorization_id": auth_record["authorization_id"],
        "nonce": auth_record["nonce"],
        "record": records["authorization_record"],
        "manifest": records["authorization_manifest"],
        "reviewed": reviewed,
        "restrictions": contract["required_restrictions"],
        "command_sha256": canonical_sha256(command),
    }
    if not isinstance(pre_authorization, dict) or set(pre_authorization) != {
        *expected_pre_authorization,
        "directory",
    }:
        raise BlenderResealV3Error("PRE_RUN authorization field closure differs")
    if any(
        pre_authorization.get(key) != value
        for key, value in expected_pre_authorization.items()
    ):
        raise BlenderResealV3Error("PRE_RUN authorization binding differs")
    pre_authorization_directory = pre_authorization.get("directory")
    if not isinstance(pre_authorization_directory, dict):
        raise BlenderResealV3Error("PRE_RUN authorization directory binding is absent")
    if (
        pre_authorization_directory.get("path") != contract["directory"]
        or pre_authorization_directory.get("exact_entries")
        != sorted(contract["directory_entries"])
        or pre_authorization_directory.get(
            "closure_exact_after_record_and_manifest_locks"
        )
        is not True
        or pre_authorization_directory.get("reparse") is not False
        or pre_authorization_directory.get("delete_sharing_denied") is not True
    ):
        raise BlenderResealV3Error("PRE_RUN authorization directory closure differs")
    # PRE was written before its own/claim final byte records were known; its
    # exact executable-input set therefore excludes those two journal records.
    expected_pre_records = {
        key: value
        for key, value in records.items()
        if key not in {"authorization_claim", "pre_run"}
    }
    if pre.get("locked_input_records") != expected_pre_records:
        raise BlenderResealV3Error("PRE_RUN locked input records differ")
    if pre.get("locked_input_records_sha256") != canonical_sha256(
        expected_pre_records
    ):
        raise BlenderResealV3Error("PRE_RUN locked input record hash differs")
    if pre.get("author_handoff") != _handoff(config):
        raise BlenderResealV3Error("PRE_RUN author handoff differs")
    author_config = _json_bytes(data["sealed_author_config"], "sealed_author_config")
    overlay = _json_bytes(data["repair_overlay_config"], "repair_overlay_config")
    handoff = config["handoff_contract"]
    if author_config.get("schema") != handoff["sealed_author_schema"]:
        raise BlenderResealV3Error("inherited author config schema differs")
    if overlay.get("schema") != handoff["repair_overlay_schema"]:
        raise BlenderResealV3Error("repair overlay schema differs")
    return config, handles, data, records, {
        "claim": claim,
        "pre": pre,
        "authorization": auth_record,
        "command": command,
    }


def project_module_name(path: str) -> str:
    value = PurePosixPath(path)
    if value.parent.as_posix().lower() != "tools" or value.suffix != ".py":
        raise BlenderResealV3Error(f"runtime module is not a Tools Python file: {path}")
    return f"tools.{value.stem}"


def load_verified_sources(
    config: Mapping[str, Any], data: Mapping[str, bytes]
) -> Any:
    order = list(config["runtime_dependency_closure"]["verified_source_import_order"])
    if len(order) != len(set(order)):
        raise BlenderResealV3Error("runtime source order contains duplicates")
    bound_by_path = {
        row["path"]: (label, row)
        for label, row in config["bound_artifacts"].items()
    }
    if set(order) != set(config["runtime_dependency_closure"]["project_local_modules"]):
        raise BlenderResealV3Error("runtime source import order is not exact")
    module_names = [project_module_name(path) for path in order]
    loaded_early = [name for name in ["tools", *module_names] if name in sys.modules]
    if loaded_early:
        raise BlenderResealV3Error(f"project modules preloaded before verification: {loaded_early}")
    package = types.ModuleType("tools")
    package.__package__ = "tools"
    package.__path__ = [str(ROOT / "Tools")]
    package.__file__ = None
    sys.modules["tools"] = package
    loaded: list[str] = []
    try:
        for path in order:
            if path not in bound_by_path:
                raise BlenderResealV3Error(f"runtime source is unbound: {path}")
            label, binding = bound_by_path[path]
            source = data[label]
            if len(source) != int(binding["bytes"]) or hashlib.sha256(source).hexdigest() != binding["sha256"]:
                raise BlenderResealV3Error(f"runtime locked bytes drifted: {path}")
            name = project_module_name(path)
            module = types.ModuleType(name)
            module.__file__ = str(_project_path(path))
            module.__package__ = "tools"
            sys.modules[name] = module
            setattr(package, PurePosixPath(path).stem, module)
            loaded.append(name)
            exec(compile(source, module.__file__, "exec", dont_inherit=True), module.__dict__)
    except Exception:
        for name in loaded:
            sys.modules.pop(name, None)
        sys.modules.pop("tools", None)
        raise
    package.__path__ = []
    target_name = project_module_name(
        "Tools/blender_author_kira_r23_cc0_afes_attempt04_wrapper.py"
    )
    target = sys.modules.get(target_name)
    if target is None:
        raise BlenderResealV3Error("topology implementation was not loaded")
    return target


def apply_config_handoff(
    topology: Any,
    config: Mapping[str, Any],
    command: Sequence[str],
    author_config: Mapping[str, Any],
    repair_overlay: Mapping[str, Any],
    original_repair_overlay: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove and apply the two-schema handoff without changing worker argv."""

    handoff = config["handoff_contract"]
    author_argument = handoff["sealed_author_config_argument"]
    overlay_argument = handoff["repair_overlay_config_argument"]
    if author_argument == overlay_argument:
        raise BlenderResealV3Error("author and overlay paths must be distinct")
    if author_config.get("schema") != handoff["sealed_author_schema"]:
        raise BlenderResealV3Error("author schema failed at handoff")
    if repair_overlay.get("schema") != handoff["repair_overlay_schema"]:
        raise BlenderResealV3Error("repair overlay schema failed at handoff")
    required_runtime_keys = {
        "schema",
        "status",
        "bound_artifacts",
        "preserved_append_only_evidence",
        "repair_contract",
        "nominal_source_baseline",
        "nominal_corrected_final",
        "clinical_semantics_contract",
    }
    missing_runtime_keys = sorted(required_runtime_keys - set(repair_overlay))
    if missing_runtime_keys:
        raise BlenderResealV3Error(
            f"repair overlay omits topology runtime keys: {missing_runtime_keys}"
        )
    for inherited_key in (
        "repair_contract",
        "nominal_source_baseline",
        "nominal_corrected_final",
        "clinical_semantics_contract",
    ):
        if repair_overlay.get(inherited_key) != original_repair_overlay.get(
            inherited_key
        ):
            raise BlenderResealV3Error(
                f"repair overlay inherited runtime contract drifted: {inherited_key}"
            )
    clinical = repair_overlay["clinical_semantics_contract"]
    labels = clinical.get("bound_source_labels")
    if not isinstance(labels, list) or not labels:
        raise BlenderResealV3Error("clinical bound-source label set is absent")
    missing_clinical_bindings = sorted(
        set(labels) - set(repair_overlay["bound_artifacts"])
    )
    if missing_clinical_bindings:
        raise BlenderResealV3Error(
            "clinical source labels lack exact overlay bindings: "
            f"{missing_clinical_bindings}"
        )
    if list(command)[-3:] != ["--config", author_argument, "--execute-authoring"]:
        raise BlenderResealV3Error("author config is not the exact worker tail")
    if overlay_argument in command:
        raise BlenderResealV3Error("repair overlay leaked into worker argv")
    topology.REPAIR_CONFIG = Path(overlay_argument)
    return {
        "author_config_argument": author_argument,
        "author_schema": author_config["schema"],
        "repair_overlay_argument": overlay_argument,
        "repair_overlay_schema": repair_overlay["schema"],
        "repair_runtime_required_keys": sorted(required_runtime_keys),
        "repair_runtime_required_keys_sha256": canonical_sha256(
            sorted(required_runtime_keys)
        ),
        "clinical_bound_source_labels": list(labels),
        "worker_argv_unchanged": True,
    }


def _inject_provenance_and_hold_outputs(
    config: Mapping[str, Any], provenance: Mapping[str, Any], result: int
) -> tuple[LockedHandle, list[LockedHandle], dict[str, Any]]:
    contract = config["output_contract"]
    directory = _project_path(contract["effective_directory"])
    directory_handle = LockedHandle.open_existing(directory, directory=True)
    expected = (
        sorted(contract["success_directory_entries"])
        if result == 0
        else sorted(contract["failure_directory_entries"])
    )
    actual = sorted(entry.name for entry in directory.iterdir())
    if actual != expected:
        directory_handle.close()
        raise BlenderResealV3Error(f"child output closure differs: {actual}")
    evidence_name = (
        contract["build_evidence_basename"]
        if result == 0
        else contract["failure_evidence_basename"]
    )
    handles: list[LockedHandle] = []
    records: dict[str, Any] = {}
    try:
        evidence = LockedHandle.open_existing(directory / evidence_name, writable=True)
        handles.append(evidence)
        payload = _json_bytes(evidence.read_bytes(), evidence_name)
        expected_evidence_identity = (
            {
                "schema_version": 1,
                "artifact_kind": "KIRA_R23_CC0_AFES_CORE_TRANSFER_AUTHOR_ATTEMPT01",
                "status": "INACTIVE_PRIVATE_CANDIDATE_AUTHORED_POSTSAVE_AUDIT_REQUIRED",
            }
            if result == 0
            else {
                "schema_version": 1,
                "artifact_kind": "KIRA_R23_CC0_AFES_CORE_TRANSFER_AUTHOR_ATTEMPT01_FAILURE",
                "status": "AUTHOR_NO_GO_NO_CANDIDATE_ACCEPTED",
            }
        )
        if any(payload.get(key) != value for key, value in expected_evidence_identity.items()):
            raise BlenderResealV3Error("worker evidence schema/status identity drifted")
        if "reseal_v3_provenance" in payload:
            raise BlenderResealV3Error("output already contains v3 provenance")
        if result == 0:
            candidate_name = contract["candidate_basename"]
            candidate = LockedHandle.open_existing(directory / candidate_name)
            handles.append(candidate)
            candidate_bytes = candidate.read_bytes()
            if candidate.identity["links"] != 1:
                raise BlenderResealV3Error("multi-link candidate is rejected")
            if len(candidate_bytes) < int(contract["minimum_candidate_bytes"]):
                raise BlenderResealV3Error("candidate is unexpectedly small")
            if not candidate_bytes.startswith(
                contract["candidate_signature_ascii"].encode("ascii")
            ):
                raise BlenderResealV3Error("candidate signature is not BLENDER")
            candidate_record = candidate.record(candidate_bytes)
            candidate_claim = payload.get("candidate")
            expected_candidate_claim = {
                "path": candidate_record["path"],
                "bytes": candidate_record["bytes"],
                "sha256": candidate_record["sha256"],
            }
            if not isinstance(candidate_claim, dict) or {
                key: candidate_claim.get(key) for key in expected_candidate_claim
            } != expected_candidate_claim:
                raise BlenderResealV3Error(
                    "worker BUILD_EVIDENCE candidate binding differs from locked candidate"
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
                raise BlenderResealV3Error("worker candidate state claims drifted")
            records[candidate_name] = candidate_record
        payload["reseal_v3_provenance"] = dict(provenance)
        evidence_bytes = (
            json.dumps(payload, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        evidence.rewrite_bytes(evidence_bytes)
        records[evidence_name] = evidence.record(evidence_bytes)
        return directory_handle, handles, {
            "classification": "success" if result == 0 else "failure",
            "exact_entries": actual,
            "records": records,
        }
    except Exception:
        for handle in handles:
            handle.close()
        directory_handle.close()
        raise


def _transfer_output_handles_to_parent(
    config: Mapping[str, Any],
    directory_handle: LockedHandle,
    output_handles: Sequence[LockedHandle],
    classification: str,
) -> dict[str, Any]:
    """Duplicate the locked file objects into the controller, then frame them."""

    try:
        pipe_handle = int(
            os.environ["KIRA_R23_RESEAL_V3_OUTPUT_HANDLE_PIPE_WRITE"]
        )
    except (KeyError, ValueError) as exc:
        raise BlenderResealV3Error("output handle-transfer pipe is absent") from exc
    api = _api()
    parent_process = api.OpenProcess(PROCESS_DUP_HANDLE, False, os.getppid())
    if not parent_process:
        raise _win_error("OpenProcess(parent duplicate target)")
    remote_handles: dict[str, int] = {}
    try:
        sources = {
            "directory": directory_handle,
            **{handle.expected_path.name: handle for handle in output_handles},
        }
        for label, source in sources.items():
            remote = wintypes.HANDLE()
            if not api.DuplicateHandle(
                api.GetCurrentProcess(),
                source.handle,
                parent_process,
                ctypes.byref(remote),
                0,
                False,
                DUPLICATE_SAME_ACCESS,
            ):
                raise _win_error(f"DuplicateHandle(output {label})")
            remote_handles[label] = int(remote.value)
        message = {
            "schema": config["process_contract"]["output_handle_transfer_schema"],
            "classification": classification,
            "handles": remote_handles,
        }
        payload = json.dumps(
            message, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        frame = len(payload).to_bytes(4, "little") + payload
        buffer = ctypes.create_string_buffer(frame)
        written = wintypes.DWORD()
        if not api.WriteFile(
            pipe_handle, buffer, len(frame), ctypes.byref(written), None
        ):
            raise _win_error("WriteFile(output handle transfer)")
        if int(written.value) != len(frame):
            raise BlenderResealV3Error("short output handle-transfer write")
        return message
    except Exception:
        # Best-effort close of any handles already created in the parent.  The
        # controller also closes every handle from a successfully read frame.
        for remote_value in remote_handles.values():
            local_duplicate = wintypes.HANDLE()
            if api.DuplicateHandle(
                parent_process,
                remote_value,
                api.GetCurrentProcess(),
                ctypes.byref(local_duplicate),
                0,
                False,
                DUPLICATE_SAME_ACCESS | DUPLICATE_CLOSE_SOURCE,
            ):
                api.CloseHandle(local_duplicate)
        raise
    finally:
        api.CloseHandle(parent_process)
        api.CloseHandle(pipe_handle)


def main() -> int:
    config, _lease_handles, data, records, bootstrap_record = bootstrap()
    source = records["r19_source_blend"]
    if not bpy.data.filepath or _normal_final_path(bpy.data.filepath) != _normal_final_path(source["final_path"]):
        raise BlenderResealV3Error("Blender did not load the locked exact R19 source")
    expected_prefix = str(config["blender_identity"]["bpy_version_prefix"])
    if not str(bpy.app.version_string).startswith(expected_prefix):
        raise BlenderResealV3Error("Blender runtime version differs from sealed identity")
    topology = load_verified_sources(config, data)
    overlay_argument = config["handoff_contract"]["repair_overlay_config_argument"]
    handoff_record = apply_config_handoff(
        topology,
        config,
        bootstrap_record["command"],
        _json_bytes(data["sealed_author_config"], "sealed_author_config"),
        _json_bytes(data["repair_overlay_config"], "repair_overlay_config"),
        _json_bytes(data["original_repair_overlay"], "original_repair_overlay"),
    )
    provenance = {
        "schema": "kira.avatar.r23_attempt04_reseal_v3_provenance.v1",
        "authorization_id": bootstrap_record["authorization"]["authorization_id"],
        "authorization_nonce": bootstrap_record["authorization"]["nonce"],
        "command_sha256": canonical_sha256(bootstrap_record["command"]),
        "sealed_author_config": records["sealed_author_config"],
        "repair_overlay_config": records["repair_overlay_config"],
        "r19_source_blend": records["r19_source_blend"],
    }
    original_bind = topology.bind_attempt04_runtime

    def bind_with_provenance(repair_config: Mapping[str, Any]) -> None:
        original_bind(repair_config)
        topology.RUNTIME["reseal_v3_provenance"] = provenance
        topology.RUNTIME["reseal_v3_handoff"] = handoff_record

    topology.bind_attempt04_runtime = bind_with_provenance
    # This is the only use of the repair overlay path. sys.argv remains the
    # exact author-config command validated above for sealed_worker.main().
    result = int(topology.main())
    if topology.RUNTIME.get("reseal_v3_provenance") != provenance:
        raise BlenderResealV3Error("v3 provenance did not survive runtime binding")
    directory_handle, output_handles, output_record = _inject_provenance_and_hold_outputs(
        config, provenance, result
    )
    try:
        _transfer_output_handles_to_parent(
            config,
            directory_handle,
            output_handles,
            output_record["classification"],
        )
        locked_event = int(
            os.environ["KIRA_R23_RESEAL_V3_OUTPUT_LOCKED_EVENT_HANDLE"]
        )
        if not _api().SetEvent(locked_event):
            raise _win_error("SetEvent(output locked)")
        _wait_event("KIRA_R23_RESEAL_V3_OUTPUT_VALIDATED_EVENT_HANDLE", 120_000)
    finally:
        for handle in output_handles:
            handle.close()
        directory_handle.close()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
