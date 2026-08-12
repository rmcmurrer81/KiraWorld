#!/usr/bin/env python3
"""Attempt-03r5 locked child wrapper for the audited private AFES v5 extractor.

Only Python's standard library is imported before the root-PID-authenticated
result pipe and exact execution contract are checked.  No ambient ``tools.*`` module is
ever imported.  The exact bound v5 extractor bytes execute in a fresh private
namespace with only Blender's real ``bpy`` module admitted at that boundary.
"""

from __future__ import annotations

import argparse
import builtins
import ctypes
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
    "kira_r25_foundation_afes_locked_pair_execution_v3r5.json"
)
SESSION_PATTERN = re.compile(r"[0-9a-f]{64}")
FILE_TYPE_PIPE = 3
AFES_V5_SCHEMA = "kira.avatar.r25.foundation_afes_read_only_extraction.v5"
EXPECTED_BINDING_NAMES = {
    "blender_executable", "foundation_blend", "afes_v5_config",
    "afes_v5_private_loader", "afes_v5_extractor", "canonical_receipt",
    "afes_v5_test", "afes_v5_checkpoint", "afes_v5_independent_audit",
    "execution_wrapper", "parent_controller", "trusted_bootstrap", "v3r5_static_test",
    "v3r5_checkpoint", "native_launcher_executable", "native_launcher_source",
    "python_runtime_dll", "retained_stdlib_zip",
    "locked_pair_attempt01_contract", "locked_pair_attempt01_wrapper",
    "locked_pair_attempt01_controller", "locked_pair_attempt01_test",
    "locked_pair_attempt01_checkpoint",
    "locked_pair_attempt01_independent_audit",
    "locked_pair_attempt02_contract", "locked_pair_attempt02_wrapper",
    "locked_pair_attempt02_controller", "locked_pair_attempt02_test",
    "locked_pair_attempt02_checkpoint", "locked_pair_attempt02_supersession",
    "locked_pair_attempt03_rebase_plan",
    "locked_pair_v3r1_contract", "locked_pair_v3r1_wrapper",
    "locked_pair_v3r1_controller", "locked_pair_v3r1_test",
    "locked_pair_v3r1_checkpoint", "locked_pair_v3r1_rejection_audit",
    "unknown_v3_rejection_audit",
    "locked_pair_v3r2_contract", "locked_pair_v3r2_wrapper",
    "locked_pair_v3r2_controller", "locked_pair_v3r2_bootstrap",
    "locked_pair_v3r2_test", "locked_pair_v3r2_checkpoint",
    "locked_pair_v3r2_rejection_audit",
    "locked_pair_v3r4_contract", "locked_pair_v3r4_wrapper",
    "locked_pair_v3r4_controller", "locked_pair_v3r4_bootstrap",
    "locked_pair_v3r4_test", "locked_pair_v3r4_checkpoint",
    "locked_pair_v3r4_retained_manifest", "locked_pair_v3r4_native_launcher",
    "locked_pair_v3r4_native_source", "locked_pair_v3r4_rejection_audit",
}


class R25AfesExecutionV3Error(RuntimeError):
    """A child-side exact contract or read-only transport gate failed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _project_file(relative: object) -> Path:
    text = str(relative or "")
    candidate = Path(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts:
        raise R25AfesExecutionV3Error("unsafe_project_relative_path")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise R25AfesExecutionV3Error("symlink_path_refused")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise R25AfesExecutionV3Error("path_escaped_project_root") from exc
    if not resolved.is_file():
        raise R25AfesExecutionV3Error("bound_path_is_not_file")
    return resolved


def _binding_path(label: str, row: Mapping[str, object]) -> Path:
    if label in {"blender_executable", "python_runtime_dll"}:
        path = Path(str(row["path"])).resolve(strict=True)
        if not path.is_file():
            raise R25AfesExecutionV3Error("blender_binding_is_not_file")
        return path
    return _project_file(row["path"])


def _read_exact_row(label: str, row: object) -> tuple[Path, bytes]:
    if not isinstance(row, Mapping) or set(row) != {"path", "bytes", "sha256"}:
        raise R25AfesExecutionV3Error(f"invalid_binding:{label}")
    if type(row["bytes"]) is not int or row["bytes"] < 0:
        raise R25AfesExecutionV3Error(f"invalid_binding_bytes:{label}")
    if not isinstance(row["sha256"], str) or SESSION_PATTERN.fullmatch(
        row["sha256"]
    ) is None:
        raise R25AfesExecutionV3Error(f"invalid_binding_sha256:{label}")
    path = _binding_path(label, row)
    value = path.read_bytes()
    if len(value) != row["bytes"] or _sha256_bytes(value) != row["sha256"]:
        raise R25AfesExecutionV3Error(f"binding_drift:{label}")
    return path, value


def _open_result_pipe(pipe_name: str) -> int:
    if (
        os.name != "nt"
        or not isinstance(pipe_name, str)
        or not pipe_name.startswith("\\\\.\\pipe\\KiraR25AFES-")
        or len(pipe_name) > 240
        or any(character in pipe_name for character in "\r\n\0")
    ):
        raise R25AfesExecutionV3Error("result_pipe_name_invalid")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = [
        ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
        ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
    ]
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.GetFileType.argtypes = [ctypes.c_void_p]
    kernel32.GetFileType.restype = ctypes.c_uint32
    raw_handle = kernel32.CreateFileW(
        pipe_name, 0x40000000, 0, None, 3, 0x80000000, None
    )
    handle_value = int(raw_handle or 0)
    if handle_value <= 0 or handle_value == ctypes.c_void_p(-1).value:
        raise R25AfesExecutionV3Error(
            f"result_pipe_open_failed:{ctypes.get_last_error()}"
        )
    if int(kernel32.GetFileType(ctypes.c_void_p(handle_value))) != FILE_TYPE_PIPE:
        kernel32.CloseHandle(ctypes.c_void_p(handle_value))
        raise R25AfesExecutionV3Error("result_named_path_is_not_pipe")
    return handle_value


def _close_result_pipe(raw_handle: int) -> None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    if not kernel32.CloseHandle(ctypes.c_void_p(raw_handle)):
        raise R25AfesExecutionV3Error(
            f"result_pipe_close_failed:{ctypes.get_last_error()}"
        )


def _write_result_frame_win32(
    raw_handle: int, payload: Mapping[str, Any], receipt: ModuleType,
    private_attempt03: ModuleType,
) -> None:
    """Write while the wrapper remains the sole Win32-handle owner.

    No CRT descriptor is created and ownership is never transferred to
    ``msvcrt``/``os.fdopen``.  The caller closes the one raw handle exactly
    once after this function returns or raises.
    """

    handle = private_attempt03.require_win32_pipe_handle(raw_handle)
    if handle != raw_handle:
        raise R25AfesExecutionV3Error("result_pipe_handle_identity_drift")
    frame = receipt.encode_receipt_frame(payload)
    if receipt.decode_receipt_frame(frame).payload != dict(payload):
        raise R25AfesExecutionV3Error("receipt_changed_before_win32_pipe_write")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.WriteFile.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p,
    ]
    kernel32.WriteFile.restype = ctypes.c_int
    buffer = (ctypes.c_ubyte * len(frame)).from_buffer_copy(frame)
    total = 0
    while total < len(frame):
        remaining = len(frame) - total
        requested = min(remaining, 0x7FFFFFFF)
        written = ctypes.c_uint32(0)
        address = ctypes.cast(
            ctypes.byref(buffer, total), ctypes.c_void_p
        )
        if not kernel32.WriteFile(
            ctypes.c_void_p(handle), address, requested,
            ctypes.byref(written), None,
        ):
            raise R25AfesExecutionV3Error(
                "result_pipe_write_failed_after_"
                + str(total) + ":" + str(ctypes.get_last_error())
            )
        if written.value < 1 or written.value > requested:
            raise R25AfesExecutionV3Error(
                "result_pipe_short_or_invalid_write_after_" + str(total)
            )
        total += int(written.value)


def _parse_object(value: bytes, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value.decode("utf-8-sig"))
    except Exception as exc:
        raise R25AfesExecutionV3Error(f"invalid_json:{label}") from exc
    if not isinstance(parsed, dict):
        raise R25AfesExecutionV3Error(f"json_root_not_object:{label}")
    return parsed


def _verify_row_table(name: str, table: object) -> None:
    if not isinstance(table, Mapping) or not table:
        raise R25AfesExecutionV3Error(f"binding_table_missing:{name}")
    for label, row in sorted(table.items()):
        _read_exact_row(f"{name}.{label}", row)


def _load_contract(
    expected_sha256: str,
) -> tuple[dict[str, Any], dict[str, object], dict[str, tuple[Path, bytes]]]:
    if SESSION_PATTERN.fullmatch(str(expected_sha256)) is None:
        raise R25AfesExecutionV3Error("execution_contract_hash_invalid")
    path = _project_file(CONTRACT_RELATIVE_PATH)
    contract_bytes = path.read_bytes()
    observed = _sha256_bytes(contract_bytes)
    if observed != expected_sha256:
        raise R25AfesExecutionV3Error("execution_contract_hash_mismatch")
    contract = _parse_object(contract_bytes, "execution_contract")
    if set(contract) != {
        "schema", "attempt_id", "status", "scope", "authorization_basis",
        "repair_boundaries", "bindings", "afes_v5_transitive_rows", "child_runtime_read_closure_completion",
        "afes_v5_exact_contract_sections",
        "accepted_afes_v5_audit", "locked_pair_attempt_01_preservation",
        "locked_pair_attempt_02_preservation", "locked_pair_v3r1_preservation",
        "locked_pair_v3r2_preservation", "locked_pair_v3r3_preservation",
        "locked_pair_v3r4_preservation", "process_contract",
        "trusted_bootstrap_contract", "native_launcher_contract",
        "controller_audit_gate", "external_native_manifest_gate",
        "required_fresh_run_count", "pair_acceptance", "append_only_output_root",
        "execution_outcome_relative_path", "truth_boundary",
    }:
        raise R25AfesExecutionV3Error("execution_contract_top_level_drift")
    if contract.get("schema") != (
        "kira.avatar.r25.foundation_afes_locked_pair_execution.v3r5"
    ) or contract.get("attempt_id") != "attempt_03r5":
        raise R25AfesExecutionV3Error("execution_contract_identity_mismatch")
    if contract.get("status") != (
        "PENDING_FRESH_INDEPENDENT_AUDIT_READ_ONLY_DIAGNOSTIC_PAIR_ONLY"
    ):
        raise R25AfesExecutionV3Error("execution_contract_status_mismatch")
    bindings = contract.get("bindings")
    if not isinstance(bindings, Mapping) or set(bindings) != EXPECTED_BINDING_NAMES:
        raise R25AfesExecutionV3Error("binding_table_drift")
    retained: dict[str, tuple[Path, bytes]] = {}
    for label, row in sorted(bindings.items()):
        bound_path, bound_bytes = _read_exact_row(str(label), row)
        retained[str(label)] = (bound_path, bound_bytes)
        if label == "execution_wrapper" and bound_path != Path(__file__).resolve(
            strict=True
        ):
            raise R25AfesExecutionV3Error("wrapper_path_mismatch")
    transitive = contract.get("afes_v5_transitive_rows")
    if not isinstance(transitive, Mapping) or set(transitive) != {
        "bindings", "attempt_01_preservation", "attempt_02_preservation",
        "attempt_03_preservation", "attempt_04_preservation",
    }:
        raise R25AfesExecutionV3Error("afes_v5_transitive_table_drift")
    for table_name, table in transitive.items():
        _verify_row_table(f"afes_v5.{table_name}", table)
    for table_name in (
        "locked_pair_attempt_01_preservation",
        "locked_pair_attempt_02_preservation",
        "locked_pair_v3r1_preservation",
        "locked_pair_v3r2_preservation",
        "locked_pair_v3r3_preservation",
        "locked_pair_v3r4_preservation",
    ):
        _verify_row_table(table_name, contract.get(table_name))
    _verify_row_table(
        "child_runtime_read_closure_completion",
        contract.get("child_runtime_read_closure_completion"),
    )
    _, v5_bytes = retained["afes_v5_config"]
    v5 = _parse_object(v5_bytes, "afes_v5_config")
    if v5.get("schema") != AFES_V5_SCHEMA or v5.get("attempt_id") != "attempt_05":
        raise R25AfesExecutionV3Error("afes_v5_identity_drift")
    for table_name, table in transitive.items():
        if v5.get(table_name) != table:
            raise R25AfesExecutionV3Error(
                f"afes_v5_transitive_content_drift:{table_name}"
            )
    expected_sections = contract.get("afes_v5_exact_contract_sections")
    observed_sections = {
        key: v5.get(key) for key in (
            "schema", "attempt_id", "status", "scope",
            "attempt_04_baseline_config", "private_exact_byte_execution_contract",
            "topology_sealing_contract", "truth_boundary",
        )
    }
    if observed_sections != expected_sections:
        raise R25AfesExecutionV3Error("afes_v5_exact_contract_sections_drift")
    accepted = contract.get("accepted_afes_v5_audit")
    if accepted != {
        "decision": "ACCEPTED_FOR_STATIC_PREPARATION_ONLY",
        "audit_sha256": bindings["afes_v5_independent_audit"]["sha256"],
        "audit_required_again_for_locked_pair_attempt03r5": True,
    }:
        raise R25AfesExecutionV3Error("accepted_afes_v5_audit_binding_drift")
    return contract, {
        "path": path.relative_to(PROJECT_ROOT).as_posix(),
        "bytes": len(contract_bytes), "sha256": observed,
    }, retained


def _real_blender_bpy(contract: Mapping[str, Any]) -> ModuleType:
    module = builtins.__import__("bpy", fromlist=())
    if not isinstance(module, ModuleType) or module.__name__ != "bpy":
        raise R25AfesExecutionV3Error("real_blender_bpy_is_absent")
    for name in ("data", "context", "app"):
        if not hasattr(module, name):
            raise R25AfesExecutionV3Error(f"real_blender_bpy_surface_missing:{name}")
    expected_binary = Path(str(contract["bindings"]["blender_executable"]["path"])).resolve(
        strict=True
    )
    observed_binary = Path(str(module.app.binary_path)).resolve(strict=True)
    if observed_binary != expected_binary:
        raise R25AfesExecutionV3Error("real_blender_binary_path_drift")
    return module


def _load_private_v5_extractor(
    contract: Mapping[str, Any], bpy_module: ModuleType, run_nonce: str,
    retained: Mapping[str, tuple[Path, bytes]],
) -> ModuleType:
    path, source = retained["afes_v5_extractor"]
    real_import = builtins.__import__

    def guarded_import(
        name: str, globals: object = None, locals: object = None,
        fromlist: Sequence[str] = (), level: int = 0,
    ) -> object:
        if level == 0 and name == "bpy":
            return bpy_module
        if name == "tools" or name.startswith("tools."):
            raise R25AfesExecutionV3Error(
                f"ambient_project_import_forbidden:{name}"
            )
        return real_import(name, globals, locals, fromlist, level)

    private = ModuleType(f"_kira_private_afes_v5_extractor_locked_child_{run_nonce}")
    private.__file__ = str(path)
    private.__package__ = ""
    private.__spec__ = None
    private.__loader__ = None
    private_builtins = dict(vars(builtins))
    private_builtins["__import__"] = guarded_import
    private.__dict__["__builtins__"] = private_builtins
    try:
        exec(compile(source, str(path), "exec", dont_inherit=True),
             private.__dict__, private.__dict__)
    except Exception as exc:
        raise R25AfesExecutionV3Error(
            f"private_v5_extractor_execution_failed:{type(exc).__name__}:{exc}"
        ) from exc
    if any(private is value for value in sys.modules.values()):
        raise R25AfesExecutionV3Error("private_v5_extractor_entered_sys_modules")
    for symbol_name in ("extract_payload", "write_receipt_frame_to_inherited_pipe"):
        symbol = getattr(private, symbol_name, None)
        if not callable(symbol) or Path(symbol.__code__.co_filename).resolve(
            strict=True
        ) != path:
            raise R25AfesExecutionV3Error(
                f"private_v5_extractor_symbol_drift:{symbol_name}"
            )
    return private


def build_payload(
    *, expected_contract_sha256: str, pair_session_nonce: str,
    run_nonce: str, run_number: int, result_pipe_name: str,
) -> tuple[dict[str, object], ModuleType, ModuleType, ModuleType]:
    if SESSION_PATTERN.fullmatch(pair_session_nonce) is None:
        raise R25AfesExecutionV3Error("pair_session_nonce_must_be_64_lowercase_hex")
    if SESSION_PATTERN.fullmatch(run_nonce) is None:
        raise R25AfesExecutionV3Error("run_nonce_must_be_64_lowercase_hex")
    if pair_session_nonce == run_nonce:
        raise R25AfesExecutionV3Error("pair_and_run_nonces_must_differ")
    if run_number not in (1, 2):
        raise R25AfesExecutionV3Error("run_number_must_be_1_or_2")
    contract, observed_contract, retained = _load_contract(expected_contract_sha256)
    bpy_module = _real_blender_bpy(contract)
    extractor = _load_private_v5_extractor(
        contract, bpy_module, run_nonce, retained
    )
    result = extractor.extract_payload()
    if not isinstance(result, tuple) or len(result) != 4:
        raise R25AfesExecutionV3Error("private_v5_extractor_return_shape_drift")
    inner, receipt, private_attempt03, _ledger = result
    if not isinstance(inner, dict) or inner.get("status") != (
        "EXTRACTED_UNSEALED_REQUIRES_MATCHING_FRESH_LOCKED_RUN"
    ):
        raise R25AfesExecutionV3Error("attempt05_inner_status_drift")
    if inner.get("config_observed_unsealed_by_parent", {}).get("sha256") != (
        contract["bindings"]["afes_v5_config"]["sha256"]
    ):
        raise R25AfesExecutionV3Error("attempt05_inner_config_observation_drift")
    payload: dict[str, object] = {
        "schema": "kira.avatar.r25.foundation_afes_locked_extraction_run.v3r5",
        "status": "READ_ONLY_EXTRACTION_COMPLETE_PENDING_PAIR_MATCH",
        "execution_contract": observed_contract,
        "accepted_afes_v5_config": dict(contract["bindings"]["afes_v5_config"]),
        "accepted_afes_v5_extractor": dict(contract["bindings"]["afes_v5_extractor"]),
        "pair_session_nonce": pair_session_nonce,
        "run_nonce": run_nonce,
        "run_number": run_number,
        "result_pipe_name": result_pipe_name,
        "child_pid": os.getpid(),
        "parent_pid": os.getppid(),
        "inner_attempt05_payload": inner,
        "truth_boundary": [
            "READ_ONLY_FOUNDATION_DIAGNOSTIC",
            "NO_BLEND_MUTATION_OR_SAVE",
            "NO_RENDER_OR_EXPORT",
            "NO_CANDIDATE_OR_BODY_AUTHORING",
            "THIS_SINGLE_RUN_IS_NOT_ACCEPTANCE",
            "V3R1_REJECTED_AND_NOT_EXECUTED",
            "V3R2_REJECTED_AND_NOT_EXECUTED",
            "V3R3_REJECTED_AND_NOT_EXECUTED",
            "V3R4_REJECTED_AND_NOT_EXECUTED",
        ],
    }
    frame = receipt.encode_receipt_frame(payload)
    if receipt.decode_receipt_frame(frame).payload != payload:
        raise R25AfesExecutionV3Error("execution_payload_roundtrip_drift")
    return payload, receipt, private_attempt03, extractor


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-pipe-name", required=True)
    parser.add_argument("--execution-contract-sha256", required=True)
    parser.add_argument("--pair-session-nonce", required=True)
    parser.add_argument("--run-nonce", required=True)
    parser.add_argument("--run-number", required=True)
    values = parser.parse_args(argv)
    try:
        values.run_number = int(values.run_number, 10)
    except ValueError as exc:
        parser.error(f"numeric argument invalid: {exc}")
    return values


def main() -> int:
    values = _arguments()
    result_pipe = 0
    try:
        result_pipe = _open_result_pipe(values.result_pipe_name)
        payload, receipt, private_attempt03, extractor = build_payload(
            expected_contract_sha256=values.execution_contract_sha256,
            pair_session_nonce=values.pair_session_nonce,
            run_nonce=values.run_nonce,
            run_number=values.run_number,
            result_pipe_name=values.result_pipe_name,
        )
        _write_result_frame_win32(
            result_pipe, payload, receipt, private_attempt03
        )
    except Exception as exc:
        print(
            f"R25_AFES_LOCKED_EXECUTION_V3R5_FAILED: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    finally:
        if result_pipe:
            owned_handle = result_pipe
            result_pipe = 0
            _close_result_pipe(owned_handle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
