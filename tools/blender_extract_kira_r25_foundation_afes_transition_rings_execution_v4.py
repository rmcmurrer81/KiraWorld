#!/usr/bin/env python3
"""Attempt-04 child adapter for one AFES-v5 read-only extraction.

This file is launched by Blender only through the independently audited
Attempt-04 parent.  It writes one authenticated canonical receipt frame to an
inherited Win32 pipe.  It never writes a path result and never mutates/saves a
Blend.
"""

from __future__ import annotations

import argparse
import builtins
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from types import ModuleType
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v4.json"
)
HEX64 = re.compile(r"[0-9a-f]{64}")
FILE_TYPE_PIPE = 3
OUTER_TRUTH_BOUNDARY = [
    "READ_ONLY_FOUNDATION_DIAGNOSTIC",
    "NO_BLEND_MUTATION_OR_SAVE",
    "NO_RENDER_OR_EXPORT",
    "NO_CANDIDATE_OR_BODY_AUTHORING",
    "THIS_SINGLE_RUN_IS_NOT_ACCEPTANCE",
]


class R25AfesExecutionV4Error(RuntimeError):
    """The child execution contract failed closed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _project_file(relative: object) -> Path:
    text = str(relative or "")
    candidate = Path(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts:
        raise R25AfesExecutionV4Error(f"unsafe_project_relative_path:{text}")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise R25AfesExecutionV4Error(f"symlink_path_refused:{text}")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise R25AfesExecutionV4Error(f"path_escaped_project_root:{text}") from exc
    if not resolved.is_file():
        raise R25AfesExecutionV4Error(f"project_input_not_file:{text}")
    return resolved


def _read_exact_row(label: str, row: object) -> tuple[Path, bytes]:
    if not isinstance(row, Mapping) or set(row) != {"path", "bytes", "sha256"}:
        raise R25AfesExecutionV4Error(f"invalid_binding:{label}")
    if type(row["bytes"]) is not int or row["bytes"] < 0:
        raise R25AfesExecutionV4Error(f"invalid_binding_bytes:{label}")
    if not isinstance(row["sha256"], str) or HEX64.fullmatch(row["sha256"]) is None:
        raise R25AfesExecutionV4Error(f"invalid_binding_sha256:{label}")
    path = _project_file(row["path"])
    value = path.read_bytes()
    if len(value) != row["bytes"] or _sha256_bytes(value) != row["sha256"]:
        raise R25AfesExecutionV4Error(f"binding_drift:{label}")
    return path, value


def _parse_json(value: bytes, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value.decode("utf-8-sig"))
    except Exception as exc:
        raise R25AfesExecutionV4Error(f"invalid_json:{label}") from exc
    if not isinstance(parsed, dict):
        raise R25AfesExecutionV4Error(f"json_root_not_object:{label}")
    return parsed


def _load_contract(expected_sha256: str) -> tuple[dict[str, Any], dict[str, object]]:
    if not isinstance(expected_sha256, str) or HEX64.fullmatch(expected_sha256) is None:
        raise R25AfesExecutionV4Error("execution_contract_hash_invalid")
    path = _project_file(CONTRACT_RELATIVE_PATH)
    value = path.read_bytes()
    observed = _sha256_bytes(value)
    if observed != expected_sha256:
        raise R25AfesExecutionV4Error("execution_contract_hash_mismatch")
    contract = _parse_json(value, "execution_contract")
    expected_top = {
        "schema", "attempt_id", "status", "scope", "authorization_basis",
        "execution_sources", "child_project_read_closure",
        "recursive_closure_contract", "process_contract",
        "audit_gate", "required_fresh_run_count", "pair_acceptance",
        "append_only_output_root", "preserved_rejected_attempt03",
        "runtime_dependency_truth", "truth_boundary",
    }
    if set(contract) != expected_top:
        raise R25AfesExecutionV4Error("execution_contract_top_level_drift")
    if contract["schema"] != "kira.avatar.r25.foundation_afes_locked_pair_execution.v4":
        raise R25AfesExecutionV4Error("execution_contract_schema_drift")
    if contract["attempt_id"] != "attempt_04" or contract["status"] != (
        "PENDING_FRESH_INDEPENDENT_AUDIT_READ_ONLY_DIAGNOSTIC_PAIR_ONLY"
    ):
        raise R25AfesExecutionV4Error("execution_contract_identity_drift")
    wrapper_row = contract["execution_sources"].get("child_wrapper")
    wrapper_path, _ = _read_exact_row("child_wrapper", wrapper_row)
    if wrapper_path != Path(__file__).resolve(strict=True):
        raise R25AfesExecutionV4Error("wrapper_path_mismatch")
    v5_row = contract["child_project_read_closure"].get("afes_v5_config")
    _, v5_bytes = _read_exact_row("afes_v5_config", v5_row)
    v5 = _parse_json(v5_bytes, "afes_v5_config")
    if v5.get("schema") != "kira.avatar.r25.foundation_afes_read_only_extraction.v5":
        raise R25AfesExecutionV4Error("afes_v5_config_identity_drift")
    return contract, {
        "path": CONTRACT_RELATIVE_PATH,
        "bytes": len(value),
        "sha256": observed,
    }


def _real_blender_bpy(contract: Mapping[str, Any]) -> ModuleType:
    module = builtins.__import__("bpy", fromlist=())
    if not isinstance(module, ModuleType) or module.__name__ != "bpy":
        raise R25AfesExecutionV4Error("real_blender_bpy_missing")
    blend_row = contract["child_project_read_closure"]["foundation_blend"]
    blend_path = _project_file(blend_row["path"])
    if Path(str(module.data.filepath)).resolve(strict=True) != blend_path:
        raise R25AfesExecutionV4Error("loaded_foundation_blend_mismatch")
    if module.data.is_dirty or str(module.context.mode) != "OBJECT":
        raise R25AfesExecutionV4Error("loaded_foundation_not_clean_object_mode")
    return module


def _load_private_v5_extractor(
    contract: Mapping[str, Any], bpy_module: ModuleType, run_nonce: str,
) -> ModuleType:
    row = contract["child_project_read_closure"]["afes_v5_extractor"]
    path, source = _read_exact_row("afes_v5_extractor", row)
    real_import = builtins.__import__

    def guarded_import(
        name: str, globals: object = None, locals: object = None,
        fromlist: Sequence[str] = (), level: int = 0,
    ) -> object:
        if name == "bpy":
            return bpy_module
        if name == "tools" or name.startswith("tools."):
            raise R25AfesExecutionV4Error(f"ambient_project_import_forbidden:{name}")
        return real_import(name, globals, locals, fromlist, level)

    private = ModuleType(f"_kira_private_afes_v5_child_{run_nonce}")
    private.__file__ = str(path)
    private.__package__ = ""
    private.__spec__ = None
    private.__loader__ = None
    private_builtins = dict(vars(builtins))
    private_builtins["__import__"] = guarded_import
    private.__dict__["__builtins__"] = private_builtins
    try:
        exec(compile(source, str(path), "exec", dont_inherit=True), private.__dict__, private.__dict__)
    except Exception as exc:
        raise R25AfesExecutionV4Error(
            f"private_v5_extractor_execution_failed:{type(exc).__name__}:{exc}"
        ) from exc
    if any(private is module for module in sys.modules.values()):
        raise R25AfesExecutionV4Error("private_v5_extractor_entered_sys_modules")
    extractor = getattr(private, "extract_payload", None)
    if not callable(extractor) or Path(extractor.__code__.co_filename).resolve(
        strict=True
    ) != path:
        raise R25AfesExecutionV4Error("private_v5_extractor_symbol_drift")
    return private


def _environment_observation() -> dict[str, object]:
    names = sorted(os.environ, key=str.casefold)
    canonical = json.dumps(
        {name: os.environ[name] for name in names},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return {
        "names": names,
        "sha256": _sha256_bytes(canonical),
    }


def build_payload(
    *, expected_contract_sha256: str, pair_session_nonce: str,
    run_nonce: str, run_number: int, result_handle: int,
) -> tuple[dict[str, Any], ModuleType, ModuleType]:
    if HEX64.fullmatch(str(pair_session_nonce)) is None:
        raise R25AfesExecutionV4Error("pair_session_nonce_invalid")
    if HEX64.fullmatch(str(run_nonce)) is None:
        raise R25AfesExecutionV4Error("run_nonce_invalid")
    if pair_session_nonce == run_nonce:
        raise R25AfesExecutionV4Error("pair_and_run_nonces_must_differ")
    if type(run_number) is not int or run_number not in (1, 2):
        raise R25AfesExecutionV4Error("run_number_invalid")
    if type(result_handle) is not int or result_handle <= 0:
        raise R25AfesExecutionV4Error("result_handle_invalid")
    contract, observed_contract = _load_contract(expected_contract_sha256)
    bpy_module = _real_blender_bpy(contract)
    extractor = _load_private_v5_extractor(contract, bpy_module, run_nonce)
    result = extractor.extract_payload()
    if not isinstance(result, tuple) or len(result) != 4:
        raise R25AfesExecutionV4Error("private_v5_extractor_return_shape_drift")
    inner, receipt, private_attempt03, _ledger = result
    if not isinstance(inner, dict):
        raise R25AfesExecutionV4Error("attempt05_inner_payload_not_object")
    payload = {
        "schema": "kira.avatar.r25.foundation_afes_locked_extraction_run.v4",
        "status": "READ_ONLY_EXTRACTION_COMPLETE_PENDING_PAIR_MATCH",
        "execution_contract": observed_contract,
        "accepted_afes_v5_config": contract["child_project_read_closure"][
            "afes_v5_config"
        ],
        "accepted_afes_v5_extractor": contract["child_project_read_closure"][
            "afes_v5_extractor"
        ],
        "pair_session_nonce": pair_session_nonce,
        "run_nonce": run_nonce,
        "run_number": run_number,
        "result_pipe_handle": result_handle,
        "child_pid": os.getpid(),
        "parent_pid": os.getppid(),
        "environment_observation": _environment_observation(),
        "inner_attempt05_payload": inner,
        "truth_boundary": list(OUTER_TRUTH_BOUNDARY),
    }
    return payload, receipt, private_attempt03


def _require_pipe(raw_handle: int) -> None:
    if os.name != "nt" or type(raw_handle) is not int or raw_handle <= 0:
        raise R25AfesExecutionV4Error("result_handle_invalid")
    import ctypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetFileType.argtypes = [ctypes.c_void_p]
    kernel32.GetFileType.restype = ctypes.c_uint32
    if int(kernel32.GetFileType(ctypes.c_void_p(raw_handle))) != FILE_TYPE_PIPE:
        raise R25AfesExecutionV4Error("result_handle_is_not_pipe")


def _write_frame(payload: Mapping[str, Any], receipt: ModuleType, raw_handle: int) -> None:
    import msvcrt
    frame = receipt.encode_receipt_frame(dict(payload))
    decoded = receipt.decode_receipt_frame(frame)
    if decoded.payload != dict(payload):
        raise R25AfesExecutionV4Error("canonical_receipt_round_trip_drift")
    descriptor = msvcrt.open_osfhandle(raw_handle, os.O_WRONLY | getattr(os, "O_BINARY", 0))
    try:
        view = memoryview(frame)
        offset = 0
        while offset < len(view):
            written = os.write(descriptor, view[offset:])
            if written <= 0:
                raise R25AfesExecutionV4Error("result_pipe_short_write")
            offset += written
    finally:
        os.close(descriptor)


def _arguments() -> argparse.Namespace:
    separator = sys.argv.index("--") if "--" in sys.argv else 0
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-handle", required=True, type=int)
    parser.add_argument("--execution-contract-sha256", required=True)
    parser.add_argument("--pair-session-nonce", required=True)
    parser.add_argument("--run-nonce", required=True)
    parser.add_argument("--run-number", required=True, type=int)
    return parser.parse_args(sys.argv[separator + 1:])


def main() -> int:
    values = _arguments()
    _require_pipe(values.result_handle)
    payload, receipt, _private_attempt03 = build_payload(
        expected_contract_sha256=values.execution_contract_sha256,
        pair_session_nonce=values.pair_session_nonce,
        run_nonce=values.run_nonce,
        run_number=values.run_number,
        result_handle=values.result_handle,
    )
    _write_frame(payload, receipt, values.result_handle)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(
            f"R25_AFES_LOCKED_CHILD_V4_FAILED:{type(exc).__name__}:{exc}",
            file=sys.stderr,
        )
        raise
