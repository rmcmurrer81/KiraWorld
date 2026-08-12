#!/usr/bin/env python3
"""Stdlib-only, dry-default controller for R23 Attempt04 reseal v2.

No project module is imported by this entry point. All project-local code is
hash-verified from the hard-coded preparation before Blender can be launched.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_reseal_v2_preparation/"
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT04_RESEAL_V2_CONFIG.json"
)
MANIFEST_PATH = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_reseal_v2_preparation/"
    "PACKAGE_MANIFEST.json"
)


class ResealV2Error(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ResealV2Error(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ResealV2Error(f"JSON root is not an object: {path}")
    return value


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_reparse(path: Path) -> bool:
    details = path.lstat()
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(
        getattr(details, "st_file_attributes", 0) & flag
    )


def _lexical_parts(raw: str | Path) -> tuple[str, ...]:
    text = str(raw)
    value = Path(text)
    if not text or value.is_absolute() or value.drive or value.root:
        raise ResealV2Error(f"project path must be nonempty and relative: {raw}")
    if any(part in {"", ".", ".."} for part in value.parts):
        raise ResealV2Error(f"project path contains unsafe lexical segment: {raw}")
    return tuple(value.parts)


def lexical_project_path(
    raw: str | Path,
    *,
    require_exists: bool,
    require_leaf_regular: bool = False,
) -> Path:
    """Check every lexical component before any resolve operation.

    `os.path.lexists` is used so broken links are checked rather than treated as
    missing. On Windows the reparse attribute rejects symlinks, junctions, mount
    points, and other redirecting leaves/ancestors.
    """

    parts = _lexical_parts(raw)
    root = ROOT
    if not os.path.lexists(root) or is_reparse(root) or not root.is_dir():
        raise ResealV2Error("project root is absent, non-directory, or reparse")
    current = root
    missing_seen = False
    for part in parts:
        current = current / part
        exists_lexically = os.path.lexists(current)
        if exists_lexically:
            if missing_seen:
                raise ResealV2Error(f"path reappears below a missing ancestor: {raw}")
            if is_reparse(current):
                raise ResealV2Error(f"project path contains reparse component: {relative(current)}")
        else:
            missing_seen = True
    if require_exists and missing_seen:
        raise ResealV2Error(f"required project path is absent: {raw}")
    if require_leaf_regular and (
        missing_seen or not current.is_file() or is_reparse(current)
    ):
        raise ResealV2Error(f"required project file is not regular: {raw}")
    # Resolution is deliberately last, after the lexical reparse walk.
    resolved = current.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve(strict=True))
    except ValueError as exc:
        raise ResealV2Error(f"project path escaped root after lexical checks: {raw}") from exc
    return current


def external_regular_path(raw: str | Path, label: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        raise ResealV2Error(f"{label} path is not absolute")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if not os.path.lexists(current):
            raise ResealV2Error(f"{label} path is absent: {path}")
        if is_reparse(current):
            raise ResealV2Error(f"{label} path contains reparse component: {current}")
    if not path.is_file():
        raise ResealV2Error(f"{label} is not a regular file: {path}")
    return path


def verify_binding(binding: Mapping[str, Any], label: str) -> dict[str, Any]:
    path = lexical_project_path(
        str(binding["path"]), require_exists=True, require_leaf_regular=True
    )
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(binding["bytes"]) or digest != str(binding["sha256"]):
        raise ResealV2Error(
            f"sealed binding drifted for {label}: bytes={size}, sha256={digest}"
        )
    return {"path": relative(path), "bytes": size, "sha256": digest}


def verify_exact_directory(section: Mapping[str, Any]) -> dict[str, Any]:
    directory = lexical_project_path(
        str(section["directory"]), require_exists=True
    )
    if not directory.is_dir() or is_reparse(directory):
        raise ResealV2Error(f"protected directory invalid: {section['label']}")
    entries = sorted(directory.iterdir(), key=lambda entry: entry.name)
    expected_names = sorted(str(name) for name in section["files"])
    if [entry.name for entry in entries] != expected_names:
        raise ResealV2Error(
            f"protected directory closure drifted for {section['label']}: "
            f"{[entry.name for entry in entries]}"
        )
    verified: dict[str, Any] = {}
    for entry in entries:
        if is_reparse(entry) or not entry.is_file():
            raise ResealV2Error(
                f"protected entry is not a regular file: {section['label']}/{entry.name}"
            )
        binding = {
            "path": f"{section['directory']}/{entry.name}",
            **section["files"][entry.name],
        }
        verified[entry.name] = verify_binding(
            binding, f"{section['label']}/{entry.name}"
        )
    return verified


def verify_blender_identity(config: Mapping[str, Any]) -> dict[str, Any]:
    expected = config["blender_identity"]
    path = external_regular_path(expected["path"], "Blender executable")
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(expected["bytes"]) or digest != str(expected["sha256"]):
        raise ResealV2Error(
            f"Blender executable drifted: bytes={size}, sha256={digest}"
        )
    return {
        "path": str(path),
        "bytes": size,
        "sha256": digest,
        "file_version": expected["file_version"],
        "product_version": expected["product_version"],
    }


def verify_preparation() -> tuple[dict[str, Any], dict[str, Any]]:
    config_path = lexical_project_path(
        CONFIG_PATH, require_exists=True, require_leaf_regular=True
    )
    manifest_path = lexical_project_path(
        MANIFEST_PATH, require_exists=True, require_leaf_regular=True
    )
    config = read_json(config_path)
    manifest = read_json(manifest_path)
    if config.get("schema") != "kira.avatar.r23_author_attempt04_reseal_v2.v1":
        raise ResealV2Error("wrong reseal v2 config schema")
    if manifest.get("artifact_kind") != "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V2_PREPARATION":
        raise ResealV2Error("wrong reseal v2 manifest kind")
    expected_paths = set(config["manifest_contract"]["required_artifact_paths"])
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ResealV2Error("reseal v2 manifest artifacts are absent")
    actual_paths = {str(entry.get("path")) for entry in artifacts}
    if actual_paths != expected_paths or len(actual_paths) != len(artifacts):
        raise ResealV2Error("reseal v2 manifest artifact closure drifted")
    verified: dict[str, Any] = {}
    for entry in artifacts:
        verified[f"manifest/{entry['path']}"] = verify_binding(
            entry, f"manifest/{entry['path']}"
        )
    for label, binding in config["bound_artifacts"].items():
        verified[f"bound/{label}"] = verify_binding(binding, label)
    for section in config["preserved_append_only_evidence"]:
        rows = verify_exact_directory(section)
        for name, record in rows.items():
            verified[f"protected/{section['label']}/{name}"] = record
    delegated_path = lexical_project_path(
        config["bound_artifacts"]["delegated_reseal_config"]["path"],
        require_exists=True,
        require_leaf_regular=True,
    )
    delegated = read_json(delegated_path)
    if (
        delegated.get("schema") != "kira.avatar.r23_author_attempt04_repair.v1"
        or delegated.get("reseal_schema")
        != "kira.avatar.r23_author_attempt04_reseal.v1"
    ):
        raise ResealV2Error("delegated reseal config schema drifted")
    for label, binding in delegated["bound_artifacts"].items():
        verified[f"delegated_bound/{label}"] = verify_binding(
            binding, f"delegated/{label}"
        )
    for section in delegated["preserved_append_only_evidence"]:
        rows = verify_exact_directory(section)
        for name, record in rows.items():
            verified[f"delegated_protected/{section['label']}/{name}"] = record
    module_paths = set(config["runtime_dependency_closure"]["project_local_modules"])
    bound_paths = {str(binding["path"]) for binding in config["bound_artifacts"].values()}
    if not module_paths.issubset(bound_paths):
        raise ResealV2Error(
            f"unbound project runtime modules: {sorted(module_paths - bound_paths)}"
        )
    preparation = lexical_project_path(
        config["manifest_contract"]["preparation_directory"], require_exists=True
    )
    if not preparation.is_dir() or is_reparse(preparation):
        raise ResealV2Error("reseal v2 preparation directory invalid")
    actual_entries = sorted(entry.name for entry in preparation.iterdir())
    expected_entries = sorted(config["manifest_contract"]["preparation_directory_entries"])
    if actual_entries != expected_entries:
        raise ResealV2Error(
            f"reseal v2 preparation directory closure drifted: {actual_entries}"
        )
    for entry in preparation.iterdir():
        if is_reparse(entry) or not entry.is_file():
            raise ResealV2Error("reseal v2 preparation contains non-regular entry")
    blender = verify_blender_identity(config)
    record = {
        "config": {
            "path": relative(config_path),
            "bytes": config_path.stat().st_size,
            "sha256": sha256_file(config_path),
        },
        "manifest": {
            "path": relative(manifest_path),
            "bytes": manifest_path.stat().st_size,
            "sha256": sha256_file(manifest_path),
        },
        "verified": verified,
        "verified_snapshot_sha256": canonical_sha256(verified),
        "blender_identity": blender,
    }
    return config, record


def validate_basename(value: str, label: str) -> str:
    if (
        not value
        or value in {".", ".."}
        or Path(value).name != value
        or "/" in value
        or "\\" in value
        or Path(value).drive
    ):
        raise ResealV2Error(f"{label} is not an exact basename: {value}")
    return value


def path_within_exact_directory(directory: Path, basename: str, label: str) -> Path:
    name = validate_basename(basename, label)
    child = directory / name
    if child.parent != directory:
        raise ResealV2Error(f"{label} escaped exact output directory")
    return child


def output_contract(config: Mapping[str, Any]) -> dict[str, Any]:
    output = config["output_contract"]
    effective = lexical_project_path(
        output["effective_directory"], require_exists=False
    )
    execution = lexical_project_path(
        output["execution_directory"], require_exists=False
    )
    if effective.exists() or os.path.lexists(effective):
        raise ResealV2Error("append-only effective Attempt04 output already exists")
    if execution.exists() or os.path.lexists(execution):
        raise ResealV2Error("append-only reseal v2 execution output already exists")
    configured = lexical_project_path(
        output["delegated_configured_directory"], require_exists=True
    )
    if not configured.is_dir() or is_reparse(configured) or configured == effective:
        raise ResealV2Error("configured/effective output isolation failed")
    names = {
        "candidate": validate_basename(output["candidate_basename"], "candidate"),
        "build": validate_basename(output["build_evidence_basename"], "build evidence"),
        "failure": validate_basename(output["failure_evidence_basename"], "failure evidence"),
    }
    paths = {
        label: path_within_exact_directory(effective, name, label)
        for label, name in names.items()
    }
    if len(set(paths.values())) != 3:
        raise ResealV2Error("output basenames collide")
    return {
        "configured": configured,
        "effective": effective,
        "execution": execution,
        "paths": paths,
        "names": names,
    }


def build_command(config: Mapping[str, Any]) -> list[str]:
    binding = config["bound_artifacts"]
    source = lexical_project_path(
        binding["r19_source_blend"]["path"],
        require_exists=True,
        require_leaf_regular=True,
    )
    wrapper = lexical_project_path(
        binding["reseal_v2_blender_wrapper"]["path"],
        require_exists=True,
        require_leaf_regular=True,
    )
    delegated = validate_relative_argument(
        config["command_contract"]["delegated_config_argument"]
    )
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
        "--config",
        delegated,
        "--execute-authoring",
    ]
    if command.index("--python-exit-code") >= command.index("--python"):
        raise ResealV2Error("--python-exit-code must precede --python")
    if command[command.index("--python-exit-code") + 1] != "7":
        raise ResealV2Error("Blender Python failure exit code is not 7")
    return command


def validate_relative_argument(raw: str) -> str:
    _lexical_parts(raw)
    lexical_project_path(raw, require_exists=True, require_leaf_regular=True)
    return Path(raw).as_posix()


def _expected_authorization_review(
    config: Mapping[str, Any], preparation: Mapping[str, Any]
) -> dict[str, Any]:
    bindings = config["bound_artifacts"]
    return {
        "preparation_manifest": preparation["manifest"],
        "reseal_v2_config": preparation["config"],
        "reseal_v2_controller": verify_binding(
            bindings["reseal_v2_controller"], "authorization/controller"
        ),
        "reseal_v2_wrapper": verify_binding(
            bindings["reseal_v2_blender_wrapper"], "authorization/wrapper"
        ),
        "delegated_repair_config": verify_binding(
            bindings["delegated_reseal_config"], "authorization/delegated config"
        ),
        "r19_source_blend": verify_binding(
            bindings["r19_source_blend"], "authorization/source"
        ),
        "blender_identity": preparation["blender_identity"],
    }


def verify_authorization(
    config: Mapping[str, Any], preparation: Mapping[str, Any], command: Sequence[str]
) -> dict[str, Any]:
    contract = config["authorization_contract"]
    directory = lexical_project_path(contract["directory"], require_exists=True)
    if not directory.is_dir() or is_reparse(directory):
        raise ResealV2Error("live authorization directory invalid")
    actual_entries = sorted(entry.name for entry in directory.iterdir())
    expected_entries = sorted(contract["directory_entries"])
    if actual_entries != expected_entries:
        raise ResealV2Error(
            f"live authorization directory closure drifted: {actual_entries}"
        )
    record_path = lexical_project_path(
        contract["record_path"], require_exists=True, require_leaf_regular=True
    )
    manifest_path = lexical_project_path(
        contract["manifest_path"], require_exists=True, require_leaf_regular=True
    )
    manifest = read_json(manifest_path)
    if set(manifest) != {
        "schema_version",
        "artifact_kind",
        "created_utc",
        "authorization_id",
        "artifacts",
    }:
        raise ResealV2Error("authorization package manifest has unexpected fields")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("artifact_kind")
        != "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V2_AUTHORIZATION_PACKAGE"
    ):
        raise ResealV2Error("wrong authorization package manifest schema/kind")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 1:
        raise ResealV2Error("authorization manifest must bind exactly one record")
    record_binding = artifacts[0]
    if record_binding.get("path") != contract["record_path"]:
        raise ResealV2Error("authorization manifest binds the wrong record path")
    verified_record = verify_binding(record_binding, "live authorization record")
    record = read_json(record_path)
    expected_keys = {
        "schema",
        "artifact_kind",
        "authorization_id",
        "created_utc",
        "owner_decision_text",
        "execution_enabled",
        "owner_authorized",
        "one_run_only",
        "nonce",
        "reviewed",
        "command_sha256",
        "outputs",
        "restrictions",
    }
    if set(record) != expected_keys:
        raise ResealV2Error("authorization record has unexpected or missing fields")
    if (
        record.get("schema") != "kira.avatar.r23_attempt04_reseal_v2_authorization.v1"
        or record.get("artifact_kind")
        != "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V2_AUTHORIZATION"
        or record.get("execution_enabled") is not True
        or record.get("owner_authorized") is not True
        or record.get("one_run_only") is not True
    ):
        raise ResealV2Error("live authorization is not explicitly enabled for one run")
    if record.get("authorization_id") != manifest.get("authorization_id"):
        raise ResealV2Error("authorization ID differs from its package manifest")
    if not isinstance(record.get("owner_decision_text"), str) or not record["owner_decision_text"].strip():
        raise ResealV2Error("authorization owner decision text is empty")
    nonce = str(record.get("nonce", ""))
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", nonce):
        raise ResealV2Error("authorization nonce is invalid")
    expected_reviewed = _expected_authorization_review(config, preparation)
    if record.get("reviewed") != expected_reviewed:
        raise ResealV2Error("authorization content bindings drifted")
    expected_outputs = {
        "effective_directory": config["output_contract"]["effective_directory"],
        "execution_directory": config["output_contract"]["execution_directory"],
        "candidate_basename": config["output_contract"]["candidate_basename"],
        "build_evidence_basename": config["output_contract"]["build_evidence_basename"],
        "failure_evidence_basename": config["output_contract"]["failure_evidence_basename"],
    }
    if record.get("outputs") != expected_outputs:
        raise ResealV2Error("authorization output bindings drifted")
    if record.get("restrictions") != config["authorization_contract"]["required_restrictions"]:
        raise ResealV2Error("authorization restrictions drifted")
    command_hash = canonical_sha256(list(command))
    if record.get("command_sha256") != command_hash:
        raise ResealV2Error("authorization command binding drifted")
    return {
        "directory": relative(directory),
        "record": verified_record,
        "record_content_sha256": canonical_sha256(record),
        "manifest": {
            "path": relative(manifest_path),
            "bytes": manifest_path.stat().st_size,
            "sha256": sha256_file(manifest_path),
        },
        "authorization_id": record["authorization_id"],
        "nonce": nonce,
        "reviewed": expected_reviewed,
        "command_sha256": command_hash,
        "outputs": expected_outputs,
        "restrictions": record["restrictions"],
    }


def authorization_presence(config: Mapping[str, Any]) -> dict[str, Any]:
    contract = config["authorization_contract"]
    record = lexical_project_path(contract["record_path"], require_exists=False)
    manifest = lexical_project_path(contract["manifest_path"], require_exists=False)
    return {
        "record_path": contract["record_path"],
        "record_exists": os.path.lexists(record),
        "manifest_path": contract["manifest_path"],
        "manifest_exists": os.path.lexists(manifest),
    }


def provenance_record(
    config: Mapping[str, Any],
    preparation: Mapping[str, Any],
    authorization: Mapping[str, Any],
) -> dict[str, Any]:
    value = {
        "schema": "kira.avatar.r23_attempt04_reseal_v2_provenance.v1",
        "preparation_manifest": preparation["manifest"],
        "reseal_v2_config": preparation["config"],
        "authorization_record": authorization["record"],
        "authorization_manifest": authorization["manifest"],
        "authorization_id": authorization["authorization_id"],
        "authorization_nonce": authorization["nonce"],
        "command_sha256": authorization["command_sha256"],
        "reseal_v2_controller": authorization["reviewed"]["reseal_v2_controller"],
        "reseal_v2_wrapper": authorization["reviewed"]["reseal_v2_wrapper"],
        "delegated_repair_config": authorization["reviewed"]["delegated_repair_config"],
        "r19_source_blend": authorization["reviewed"]["r19_source_blend"],
        "blender_identity": authorization["reviewed"]["blender_identity"],
    }
    return {**value, "canonical_sha256": canonical_sha256(value)}


def protected_state(
    config: Mapping[str, Any],
    command: Sequence[str],
    *,
    require_authorization: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    current_config, preparation = verify_preparation()
    if current_config != config:
        raise ResealV2Error("in-memory reseal v2 config differs from sealed config")
    authorization = None
    if require_authorization:
        authorization = verify_authorization(config, preparation, command)
    state = {
        "preparation": preparation,
        "authorization": authorization,
    }
    return state, preparation, authorization


def safe_mkdir_tree(path: Path) -> None:
    try:
        relative_parts = path.relative_to(ROOT).parts
    except ValueError as exc:
        raise ResealV2Error(f"directory escaped project root: {path}") from exc
    current = ROOT
    for part in relative_parts:
        current = current / part
        if os.path.lexists(current):
            if is_reparse(current) or not current.is_dir():
                raise ResealV2Error(f"directory ancestor invalid: {current}")
        else:
            current.mkdir()
            if is_reparse(current) or not current.is_dir():
                raise ResealV2Error(f"created directory is not safe: {current}")


def verify_project_leaf(path: Path, *, require_exists: bool) -> Path:
    try:
        raw = path.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise ResealV2Error(f"journal/output leaf escaped project root: {path}") from exc
    checked = lexical_project_path(
        raw,
        require_exists=require_exists,
        require_leaf_regular=require_exists,
    )
    if checked != path:
        raise ResealV2Error(f"journal/output leaf changed lexically: {path}")
    return checked


def write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    verify_project_leaf(path, require_exists=False)
    if os.path.lexists(path):
        raise ResealV2Error(f"append-only journal already exists: {path}")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    verify_project_leaf(path, require_exists=True)


def file_record_or_error(path: Path) -> dict[str, Any]:
    try:
        verify_project_leaf(path, require_exists=True)
        return {
            "path": relative(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "error": None,
        }
    except Exception as exc:
        return {
            "path": relative(path),
            "bytes": None,
            "sha256": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _windows_blender_processes() -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    TH32CS_SNAPPROCESS = 0x00000002
    INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_wchar * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(PROCESSENTRY32W),
    ]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(PROCESSENTRY32W),
    ]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        raise ResealV2Error("CreateToolhelp32Snapshot failed")
    rows: list[dict[str, Any]] = []
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    try:
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            name = str(entry.szExeFile)
            if name.lower() == "blender.exe":
                rows.append(
                    {
                        "pid": int(entry.th32ProcessID),
                        "parent_pid": int(entry.th32ParentProcessID),
                        "executable_name": name,
                    }
                )
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return sorted(rows, key=lambda row: row["pid"])


def blender_processes() -> list[dict[str, Any]]:
    return _windows_blender_processes()


def minimal_child_environment(
    config: Mapping[str, Any],
    preparation: Mapping[str, Any],
    authorization: Mapping[str, Any],
    pre_run_path: Path,
) -> dict[str, str]:
    allow = set(config["process_contract"]["environment_allowlist"])
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in allow
        and key.upper()
        not in set(config["process_contract"]["forbidden_environment_keys"])
    }
    for key in config["process_contract"]["forbidden_environment_keys"]:
        environment.pop(key, None)
        environment.pop(key.lower(), None)
    environment.update(
        {
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "KIRA_R23_RESEAL_V2_PRE_RUN_PATH": relative(pre_run_path),
            "KIRA_R23_RESEAL_V2_PREPARATION_MANIFEST_SHA256": preparation["manifest"]["sha256"],
            "KIRA_R23_RESEAL_V2_CONFIG_SHA256": preparation["config"]["sha256"],
            "KIRA_R23_RESEAL_V2_AUTHORIZATION_RECORD_SHA256": authorization["record"]["sha256"],
            "KIRA_R23_RESEAL_V2_AUTHORIZATION_MANIFEST_SHA256": authorization["manifest"]["sha256"],
            "KIRA_R23_RESEAL_V2_AUTHORIZATION_NONCE": authorization["nonce"],
        }
    )
    forbidden_present = sorted(
        key for key in config["process_contract"]["forbidden_environment_keys"]
        if key in environment
    )
    if forbidden_present:
        raise ResealV2Error(f"forbidden child environment keys survived: {forbidden_present}")
    return environment


def _validate_provenance(record: Mapping[str, Any], expected: Mapping[str, Any]) -> None:
    if record != expected:
        raise ResealV2Error("produced evidence lacks exact reseal v2 provenance")
    without_hash = {key: value for key, value in record.items() if key != "canonical_sha256"}
    if record.get("canonical_sha256") != canonical_sha256(without_hash):
        raise ResealV2Error("produced provenance canonical hash is invalid")


def validate_output_directory(
    config: Mapping[str, Any], expected_provenance: Mapping[str, Any]
) -> dict[str, Any]:
    output = config["output_contract"]
    directory = lexical_project_path(output["effective_directory"], require_exists=True)
    if not directory.is_dir() or is_reparse(directory):
        raise ResealV2Error("effective output is not a safe directory")
    entries = sorted(directory.iterdir(), key=lambda item: item.name)
    for entry in entries:
        if is_reparse(entry) or not entry.is_file():
            raise ResealV2Error(f"effective output contains non-regular entry: {entry.name}")
    names = [entry.name for entry in entries]
    success_names = sorted(
        [output["candidate_basename"], output["build_evidence_basename"]]
    )
    failure_names = [output["failure_evidence_basename"]]
    if names == success_names:
        classification = "success"
    elif names == failure_names:
        classification = "failure"
    else:
        raise ResealV2Error(f"effective output closure invalid: {names}")
    candidate_path = path_within_exact_directory(
        directory, output["candidate_basename"], "candidate"
    )
    build_path = path_within_exact_directory(
        directory, output["build_evidence_basename"], "build evidence"
    )
    failure_path = path_within_exact_directory(
        directory, output["failure_evidence_basename"], "failure evidence"
    )
    if classification == "success":
        size = candidate_path.stat().st_size
        if size < int(output["minimum_candidate_bytes"]):
            raise ResealV2Error(f"candidate is implausibly small: {size}")
        with candidate_path.open("rb") as stream:
            signature = stream.read(7)
        if signature != b"BLENDER":
            raise ResealV2Error("candidate lacks Blender file signature")
        candidate_sha = sha256_file(candidate_path)
        evidence = read_json(build_path)
        if (
            evidence.get("schema_version") != 1
            or evidence.get("artifact_kind")
            != "KIRA_R23_CC0_AFES_CORE_TRANSFER_AUTHOR_ATTEMPT01"
            or evidence.get("status")
            != "INACTIVE_PRIVATE_CANDIDATE_AUTHORED_POSTSAVE_AUDIT_REQUIRED"
        ):
            raise ResealV2Error("build evidence schema/status is invalid")
        candidate = evidence.get("candidate")
        if not isinstance(candidate, dict):
            raise ResealV2Error("build evidence candidate record is absent")
        expected_relative = f"{output['effective_directory']}/{output['candidate_basename']}"
        if (
            candidate.get("path") != expected_relative
            or candidate.get("bytes") != size
            or candidate.get("sha256") != candidate_sha
        ):
            raise ResealV2Error("candidate and build-evidence hashes/paths disagree")
        _validate_provenance(evidence.get("reseal_v2_provenance", {}), expected_provenance)
        return {
            "classification": classification,
            "directory": relative(directory),
            "entries": names,
            "candidate": {
                "path": relative(candidate_path),
                "bytes": size,
                "sha256": candidate_sha,
                "signature_ascii": signature.decode("ascii"),
            },
            "evidence": {
                "path": relative(build_path),
                "bytes": build_path.stat().st_size,
                "sha256": sha256_file(build_path),
            },
        }
    evidence = read_json(failure_path)
    if (
        evidence.get("schema_version") != 1
        or evidence.get("artifact_kind")
        != "KIRA_R23_CC0_AFES_CORE_TRANSFER_AUTHOR_ATTEMPT01_FAILURE"
        or evidence.get("status") != "AUTHOR_NO_GO_NO_CANDIDATE_ACCEPTED"
        or evidence.get("candidate_file_exists") is not False
    ):
        raise ResealV2Error("failure evidence schema/status is invalid")
    _validate_provenance(evidence.get("reseal_v2_provenance", {}), expected_provenance)
    return {
        "classification": classification,
        "directory": relative(directory),
        "entries": names,
        "candidate": None,
        "evidence": {
            "path": relative(failure_path),
            "bytes": failure_path.stat().st_size,
            "sha256": sha256_file(failure_path),
        },
    }


def _bounded_wait(
    process: subprocess.Popen[Any], timeout_seconds: float, grace_seconds: float
) -> dict[str, Any]:
    record = {
        "timed_out": False,
        "terminate_called": False,
        "kill_called": False,
        "returncode": None,
    }
    try:
        record["returncode"] = int(process.wait(timeout=timeout_seconds))
        return record
    except subprocess.TimeoutExpired:
        record["timed_out"] = True
        process.terminate()
        record["terminate_called"] = True
        try:
            record["returncode"] = int(process.wait(timeout=grace_seconds))
            return record
        except subprocess.TimeoutExpired:
            process.kill()
            record["kill_called"] = True
            record["returncode"] = int(process.wait(timeout=grace_seconds))
            return record


def execute_once(
    config: Mapping[str, Any],
    preparation: Mapping[str, Any],
    authorization: Mapping[str, Any],
    command: Sequence[str],
) -> int:
    outputs = output_contract(config)
    pre_state, _, current_authorization = protected_state(
        config, command, require_authorization=True
    )
    if current_authorization != authorization:
        raise ResealV2Error("authorization changed before execution journal")
    before_processes = blender_processes()
    if before_processes:
        raise ResealV2Error(f"Blender already active: {before_processes}")
    safe_mkdir_tree(outputs["execution"])
    journal = config["journal_contract"]
    pre_path = path_within_exact_directory(
        outputs["execution"], journal["pre_run_basename"], "PRE journal"
    )
    post_path = path_within_exact_directory(
        outputs["execution"], journal["post_run_basename"], "POST journal"
    )
    stdout_path = path_within_exact_directory(
        outputs["execution"], journal["stdout_basename"], "stdout"
    )
    stderr_path = path_within_exact_directory(
        outputs["execution"], journal["stderr_basename"], "stderr"
    )
    provenance = provenance_record(config, preparation, authorization)
    exceptions: list[str] = []
    environment: dict[str, str] = {}
    pre_run_written = False
    try:
        environment = minimal_child_environment(
            config, preparation, authorization, pre_path
        )
        write_json_exclusive(
            pre_path,
            {
                "schema_version": 1,
                "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V2_PRE_RUN",
                "created_utc": utc_now(),
                "preparation": preparation,
                "authorization": authorization,
                "provenance": provenance,
                "protected_state_sha256": canonical_sha256(pre_state),
                "command": list(command),
                "command_sha256": canonical_sha256(list(command)),
                "child_environment_keys": sorted(environment),
                "forbidden_environment_keys_present": [],
                "blender_processes_before": before_processes,
            },
        )
        pre_run_written = True
    except Exception as exc:
        exceptions.append(f"pre_run_journal:{type(exc).__name__}:{exc}")
    wait_record: dict[str, Any] = {
        "timed_out": False,
        "terminate_called": False,
        "kill_called": False,
        "returncode": None,
    }
    child_pid: int | None = None
    output_validation: dict[str, Any] | None = None
    protection: dict[str, Any] = {"passed": False}
    after_processes: list[dict[str, Any]] = []
    started = utc_now()
    process: subprocess.Popen[Any] | None = None
    try:
        if not pre_run_written:
            raise ResealV2Error("PRE_RUN was not durably written; child launch refused")
        verify_project_leaf(stdout_path, require_exists=False)
        verify_project_leaf(stderr_path, require_exists=False)
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            process = subprocess.Popen(
                list(command),
                cwd=ROOT,
                stdout=stdout,
                stderr=stderr,
                shell=False,
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
                env=environment,
            )
            child_pid = int(process.pid)
            wait_record = _bounded_wait(
                process,
                float(config["process_contract"]["timeout_seconds"]),
                float(config["process_contract"]["termination_grace_seconds"]),
            )
        verify_project_leaf(stdout_path, require_exists=True)
        verify_project_leaf(stderr_path, require_exists=True)
    except Exception as exc:
        exceptions.append(f"launch_or_wait:{type(exc).__name__}:{exc}")
    finally:
        if process is not None and process.poll() is None:
            try:
                process.kill()
                wait_record["kill_called"] = True
                process.wait(timeout=float(config["process_contract"]["termination_grace_seconds"]))
            except Exception as exc:
                exceptions.append(f"final_exact_child_kill:{type(exc).__name__}:{exc}")
        try:
            if not os.path.lexists(stdout_path):
                verify_project_leaf(stdout_path, require_exists=False)
                stdout_path.touch(exist_ok=False)
            if not os.path.lexists(stderr_path):
                verify_project_leaf(stderr_path, require_exists=False)
                stderr_path.touch(exist_ok=False)
            verify_project_leaf(stdout_path, require_exists=True)
            verify_project_leaf(stderr_path, require_exists=True)
        except Exception as exc:
            exceptions.append(f"log_leaf_finalization:{type(exc).__name__}:{exc}")
        try:
            output_validation = validate_output_directory(config, provenance)
        except Exception as exc:
            exceptions.append(f"output_validation:{type(exc).__name__}:{exc}")
        try:
            post_state, _, post_authorization = protected_state(
                config, command, require_authorization=True
            )
            checks = {
                "protected_state_exact": post_state == pre_state,
                "authorization_exact": post_authorization == authorization,
            }
            protection = {
                "passed": all(checks.values()),
                "checks": checks,
                "pre_sha256": canonical_sha256(pre_state),
                "post_sha256": canonical_sha256(post_state),
                "authorization_record_pre_sha256": authorization["record"]["sha256"],
                "authorization_record_post_sha256": post_authorization["record"]["sha256"],
                "authorization_manifest_pre_sha256": authorization["manifest"]["sha256"],
                "authorization_manifest_post_sha256": post_authorization["manifest"]["sha256"],
            }
        except Exception as exc:
            exceptions.append(f"postrun_protection:{type(exc).__name__}:{exc}")
            protection = {
                "passed": False,
                "error": f"{type(exc).__name__}: {exc}",
                "pre_sha256": canonical_sha256(pre_state),
                "post_sha256": None,
            }
        try:
            after_processes = blender_processes()
        except Exception as exc:
            exceptions.append(f"process_inventory_after:{type(exc).__name__}:{exc}")
            after_processes = [{"inventory_error": str(exc)}]
        if after_processes:
            exceptions.append(f"blender_remained_after_child:{after_processes}")
        returncode = wait_record.get("returncode")
        success = (
            returncode == 0
            and wait_record.get("timed_out") is False
            and output_validation is not None
            and output_validation.get("classification") == "success"
            and protection.get("passed") is True
            and not after_processes
            and not exceptions
        )
        effective_exit = 0 if success else int(config["command_contract"]["python_exit_code"])
        post = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V2_POST_RUN",
            "started_utc": started,
            "ended_utc": utc_now(),
            "child_pid": child_pid,
            "pre_run_written": pre_run_written,
            "wait": wait_record,
            "effective_exit_code": effective_exit,
            "exceptions": exceptions,
            "output_validation": output_validation,
            "postrun_protection": protection,
            "blender_processes_after": after_processes,
            "stdout": file_record_or_error(stdout_path),
            "stderr": file_record_or_error(stderr_path),
        }
        try:
            write_json_exclusive(post_path, post)
        except Exception as exc:
            # The append-only write is deliberately not retried or overwritten.
            raise ResealV2Error(f"POST_RUN journal write failed: {exc}") from exc
    return int(effective_exit)


def arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-attempt04-reseal-v2", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = arguments(argv)
    config, preparation = verify_preparation()
    outputs = output_contract(config)
    command = build_command(config)
    process_rows = blender_processes()
    presence = authorization_presence(config)
    if not args.execute_attempt04_reseal_v2:
        if presence["record_exists"] != presence["manifest_exists"]:
            raise ResealV2Error("partial live authorization package exists")
        authorization = None
        if presence["record_exists"]:
            authorization = verify_authorization(config, preparation, command)
        print(
            json.dumps(
                {
                    "status": "DRY_RESEAL_V2_PREPARED_EXECUTION_DISABLED_BLENDER_NOT_RUN",
                    "execution_enabled": False,
                    "preparation": {
                        "config": preparation["config"],
                        "manifest": preparation["manifest"],
                        "verified_count": len(preparation["verified"]),
                        "verified_snapshot_sha256": preparation["verified_snapshot_sha256"],
                    },
                    "authorization_presence": presence,
                    "authorization_valid_if_present": authorization is not None,
                    "command": command,
                    "command_sha256": canonical_sha256(command),
                    "effective_output": relative(outputs["effective"]),
                    "effective_output_exists": False,
                    "execution_output": relative(outputs["execution"]),
                    "execution_output_exists": False,
                    "blender_processes": process_rows,
                    "blender_started": False,
                },
                indent=2,
            )
        )
        return 0
    authorization = verify_authorization(config, preparation, command)
    return execute_once(config, preparation, authorization, command)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ResealV2Error as exc:
        print(f"Attempt04 reseal v2 refused: {exc}", file=sys.stderr)
        raise SystemExit(2)
