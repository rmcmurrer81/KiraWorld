#!/usr/bin/env python3
"""Attempt-05 Blender child adapter for one exact read-only AFES extraction.

The wrapper verifies the new execution contract and its inherited exact
Attempt-04 35-file child closure, then privately executes the locked Attempt-04
pipe adapter core.  It changes only the contract identity and outer schema.
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
    "kira_r25_foundation_afes_locked_pair_execution_v5.json"
)
HEX64 = re.compile(r"[0-9a-f]{64}")


class R25AfesExecutionV5Error(RuntimeError):
    """The Attempt-05 child execution boundary failed closed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def _project_file(relative: object) -> Path:
    text = str(relative or "")
    candidate = Path(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts:
        raise R25AfesExecutionV5Error(f"unsafe_project_relative_path:{text}")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise R25AfesExecutionV5Error(f"symlink_path_refused:{text}")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise R25AfesExecutionV5Error(f"path_escaped_project_root:{text}") from exc
    if not resolved.is_file():
        raise R25AfesExecutionV5Error(f"project_input_not_file:{text}")
    return resolved


def _parse_json(value: bytes, label: str) -> dict[str, Any]:
    def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, item in pairs:
            if key in result:
                raise R25AfesExecutionV5Error(f"duplicate_json_key:{label}:{key}")
            result[key] = item
        return result

    def reject_constant(raw: str) -> object:
        raise R25AfesExecutionV5Error(f"non_finite_json_value:{label}:{raw}")

    try:
        parsed = json.loads(
            value.decode("utf-8-sig"), object_pairs_hook=strict_object,
            parse_constant=reject_constant,
        )
    except R25AfesExecutionV5Error:
        raise
    except Exception as exc:
        raise R25AfesExecutionV5Error(f"invalid_json:{label}") from exc
    if not isinstance(parsed, dict):
        raise R25AfesExecutionV5Error(f"json_root_not_object:{label}")
    return parsed


def _read_exact_row(label: str, row: object) -> tuple[Path, bytes]:
    if not isinstance(row, Mapping) or set(row) != {"path", "bytes", "sha256"}:
        raise R25AfesExecutionV5Error(f"invalid_binding:{label}")
    if type(row["bytes"]) is not int or row["bytes"] < 0:
        raise R25AfesExecutionV5Error(f"invalid_binding_bytes:{label}")
    if not isinstance(row["sha256"], str) or HEX64.fullmatch(row["sha256"]) is None:
        raise R25AfesExecutionV5Error(f"invalid_binding_sha256:{label}")
    path = _project_file(row["path"])
    value = path.read_bytes()
    if len(value) != row["bytes"] or _sha256_bytes(value) != row["sha256"]:
        raise R25AfesExecutionV5Error(f"binding_drift:{label}")
    return path, value


def _load_contract(
    expected_sha256: str,
) -> tuple[dict[str, Any], dict[str, object], dict[str, Any]]:
    if not isinstance(expected_sha256, str) or HEX64.fullmatch(expected_sha256) is None:
        raise R25AfesExecutionV5Error("execution_contract_hash_invalid")
    path = _project_file(CONTRACT_RELATIVE_PATH)
    value = path.read_bytes()
    if _sha256_bytes(value) != expected_sha256:
        raise R25AfesExecutionV5Error("execution_contract_hash_mismatch")
    contract = _parse_json(value, "execution_contract")
    expected_top = {
        "schema", "attempt_id", "status", "scope", "authorization_basis",
        "execution_sources", "inherited_attempt04_contract",
        "recursive_closure_contract", "process_contract", "audit_gate",
        "required_fresh_run_count", "pair_acceptance", "append_only_output_root",
        "preserved_rejected_attempt04", "runtime_dependency_truth", "truth_boundary",
    }
    if set(contract) != expected_top:
        raise R25AfesExecutionV5Error("execution_contract_top_level_drift")
    if contract["schema"] != "kira.avatar.r25.foundation_afes_locked_pair_execution.v5":
        raise R25AfesExecutionV5Error("execution_contract_schema_drift")
    if contract["attempt_id"] != "attempt_05" or contract["status"] != (
        "PENDING_FRESH_INDEPENDENT_AUDIT_READ_ONLY_DIAGNOSTIC_PAIR_ONLY"
    ):
        raise R25AfesExecutionV5Error("execution_contract_identity_drift")
    wrapper_path, _ = _read_exact_row(
        "child_wrapper", contract["execution_sources"]["child_wrapper"],
    )
    if wrapper_path != Path(__file__).resolve(strict=True):
        raise R25AfesExecutionV5Error("wrapper_path_mismatch")
    _, inherited_bytes = _read_exact_row(
        "inherited_attempt04_contract", contract["inherited_attempt04_contract"],
    )
    inherited = _parse_json(inherited_bytes, "inherited_attempt04_contract")
    if inherited.get("schema") != "kira.avatar.r25.foundation_afes_locked_pair_execution.v4":
        raise R25AfesExecutionV5Error("inherited_attempt04_schema_drift")
    closure = inherited.get("child_project_read_closure")
    if not isinstance(closure, Mapping) or len(closure) != 35:
        raise R25AfesExecutionV5Error("inherited_child_closure_count_drift")
    declared = {str(row["path"]): dict(row) for row in closure.values()}
    if len(declared) != 35:
        raise R25AfesExecutionV5Error("inherited_child_closure_duplicate_path")
    observed_closure_sha256 = _sha256_bytes(_canonical_json_bytes(declared))
    closure_contract = contract["recursive_closure_contract"]
    if closure_contract.get("canonical_closure_sha256") != observed_closure_sha256:
        raise R25AfesExecutionV5Error("inherited_child_closure_digest_drift")
    merged = dict(contract)
    merged["child_project_read_closure"] = dict(closure)
    return merged, {
        "path": CONTRACT_RELATIVE_PATH,
        "bytes": len(value),
        "sha256": expected_sha256,
    }, contract


def _load_attempt04_wrapper_core(contract: Mapping[str, Any]) -> ModuleType:
    path, source = _read_exact_row(
        "attempt04_child_wrapper_core",
        contract["execution_sources"]["attempt04_child_wrapper_core"],
    )
    real_import = builtins.__import__

    def guarded_import(
        name: str, globals: object = None, locals: object = None,
        fromlist: Sequence[str] = (), level: int = 0,
    ) -> object:
        if name == "tools" or name.startswith("tools."):
            raise R25AfesExecutionV5Error(f"ambient_project_import_forbidden:{name}")
        return real_import(name, globals, locals, fromlist, level)

    private = ModuleType(f"_kira_private_afes_attempt04_child_core_{os.getpid()}")
    private.__file__ = str(path)
    private.__package__ = ""
    private.__spec__ = None
    private.__loader__ = None
    private_builtins = dict(vars(builtins))
    private_builtins["__import__"] = guarded_import
    private.__dict__["__builtins__"] = private_builtins
    exec(compile(source, str(path), "exec", dont_inherit=True), private.__dict__, private.__dict__)
    if any(private is module for module in sys.modules.values()):
        raise R25AfesExecutionV5Error("attempt04_child_core_entered_sys_modules")
    if not callable(getattr(private, "build_payload", None)) or not callable(
        getattr(private, "_write_frame", None)
    ):
        raise R25AfesExecutionV5Error("attempt04_child_core_symbol_missing")
    return private


def build_payload(
    *, expected_contract_sha256: str, pair_session_nonce: str,
    run_nonce: str, run_number: int, result_handle: int,
) -> tuple[dict[str, Any], ModuleType, ModuleType]:
    merged, observed_contract, contract = _load_contract(expected_contract_sha256)
    core = _load_attempt04_wrapper_core(contract)

    def retained_contract_loader(
        observed_sha256: str,
    ) -> tuple[dict[str, Any], dict[str, object]]:
        if observed_sha256 != expected_contract_sha256:
            raise R25AfesExecutionV5Error("core_contract_digest_argument_drift")
        return merged, observed_contract

    core.CONTRACT_RELATIVE_PATH = CONTRACT_RELATIVE_PATH
    core._load_contract = retained_contract_loader
    payload, receipt, private_attempt03 = core.build_payload(
        expected_contract_sha256=expected_contract_sha256,
        pair_session_nonce=pair_session_nonce, run_nonce=run_nonce,
        run_number=run_number, result_handle=result_handle,
    )
    if not isinstance(payload, dict) or payload.get("schema") != (
        "kira.avatar.r25.foundation_afes_locked_extraction_run.v4"
    ):
        raise R25AfesExecutionV5Error("attempt04_core_outer_shape_drift")
    payload["schema"] = "kira.avatar.r25.foundation_afes_locked_extraction_run.v5"
    return payload, receipt, private_attempt03


def _require_pipe(raw_handle: int) -> None:
    if os.name != "nt" or type(raw_handle) is not int or raw_handle <= 0:
        raise R25AfesExecutionV5Error("result_handle_invalid")
    import ctypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetFileType.argtypes = [ctypes.c_void_p]
    kernel32.GetFileType.restype = ctypes.c_uint32
    if int(kernel32.GetFileType(ctypes.c_void_p(raw_handle))) != 3:
        raise R25AfesExecutionV5Error("result_handle_is_not_pipe")


def _write_frame(payload: Mapping[str, Any], receipt: ModuleType, raw_handle: int) -> None:
    import msvcrt
    frame = receipt.encode_receipt_frame(dict(payload))
    if receipt.decode_receipt_frame(frame).payload != dict(payload):
        raise R25AfesExecutionV5Error("canonical_receipt_round_trip_drift")
    descriptor = msvcrt.open_osfhandle(
        raw_handle, os.O_WRONLY | getattr(os, "O_BINARY", 0),
    )
    try:
        view = memoryview(frame)
        offset = 0
        while offset < len(view):
            written = os.write(descriptor, view[offset:])
            if written <= 0:
                raise R25AfesExecutionV5Error("result_pipe_short_write")
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
            f"R25_AFES_LOCKED_CHILD_V5_FAILED:{type(exc).__name__}:{exc}",
            file=sys.stderr,
        )
        raise
