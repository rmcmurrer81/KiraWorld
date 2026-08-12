#!/usr/bin/env python3
"""Attempt-02 locked execution wrapper for the read-only R25 AFES extractor.

Only the Python standard library is imported before the exact execution
contract and result-handle type are checked.  Project modules are imported
only after the parent-held lock set has been independently verified by the
controller.  This wrapper never mutates, saves, renders, exports, or creates a
candidate.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CONTRACT_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v2.json"
)
SESSION_PATTERN = re.compile(r"[0-9a-f]{64}")
FILE_TYPE_PIPE = 3


class R25AfesExecutionV2Error(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_file(relative: object) -> Path:
    text = str(relative or "")
    candidate = Path(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts:
        raise R25AfesExecutionV2Error("unsafe_project_relative_path")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise R25AfesExecutionV2Error("symlink_path_refused")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise R25AfesExecutionV2Error("path_escaped_project_root") from exc
    if not resolved.is_file():
        raise R25AfesExecutionV2Error("bound_path_is_not_file")
    return resolved


def _verify_project_row(label: str, row: object) -> Path:
    if not isinstance(row, Mapping) or not {"path", "bytes", "sha256"}.issubset(row):
        raise R25AfesExecutionV2Error(f"invalid_binding:{label}")
    path = _project_file(row["path"])
    if path.stat().st_size != row["bytes"] or _sha256_file(path) != row["sha256"]:
        raise R25AfesExecutionV2Error(f"binding_drift:{label}")
    return path


def _require_pipe(raw_handle: int) -> None:
    if os.name != "nt" or type(raw_handle) is not int or raw_handle <= 0:
        raise R25AfesExecutionV2Error("result_handle_invalid")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetFileType.argtypes = [ctypes.c_void_p]
    kernel32.GetFileType.restype = ctypes.c_uint32
    if int(kernel32.GetFileType(ctypes.c_void_p(raw_handle))) != FILE_TYPE_PIPE:
        raise R25AfesExecutionV2Error("result_handle_is_not_pipe")


def _load_contract(expected_sha256: str) -> tuple[dict[str, Any], dict[str, object]]:
    path = _project_file(CONTRACT_RELATIVE_PATH)
    observed = _sha256_file(path)
    if observed != expected_sha256:
        raise R25AfesExecutionV2Error("execution_contract_hash_mismatch")
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise R25AfesExecutionV2Error("execution_contract_invalid_json") from exc
    if not isinstance(contract, dict) or contract.get("schema") != (
        "kira.avatar.r25.foundation_afes_locked_pair_execution.v2"
    ) or contract.get("attempt_id") != "attempt_02":
        raise R25AfesExecutionV2Error("execution_contract_identity_mismatch")
    if contract.get("status") != "AUTHORIZED_READ_ONLY_DIAGNOSTIC_PAIR_ONLY":
        raise R25AfesExecutionV2Error("execution_contract_not_authorized")
    bindings = contract.get("bindings")
    if not isinstance(bindings, Mapping):
        raise R25AfesExecutionV2Error("binding_table_missing")
    paths = {
        label: _verify_project_row(label, bindings[label])
        for label in (
            "execution_wrapper",
            "attempt02_extractor",
            "attempt02_topology_core",
            "canonical_receipt",
        )
    }
    if paths["execution_wrapper"] != Path(__file__).resolve(strict=True):
        raise R25AfesExecutionV2Error("wrapper_path_mismatch")
    return contract, {
        "path": path.relative_to(PROJECT_ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": observed,
    }


def _import_bound_modules(contract: Mapping[str, Any]) -> tuple[Any, Any]:
    bindings = contract["bindings"]
    receipt_module = importlib.import_module("tools.kira_r25_canonical_receipt")
    topology_module = importlib.import_module("tools.kira_r25_afes_topology_core_v2")
    extractor_module = importlib.import_module(
        "tools.blender_extract_kira_r25_foundation_afes_transition_rings_v2"
    )
    expected = {
        "canonical_receipt": receipt_module.__file__,
        "attempt02_topology_core": topology_module.__file__,
        "attempt02_extractor": extractor_module.__file__,
    }
    for label, module_path in expected.items():
        if Path(str(module_path)).resolve(strict=True) != _project_file(
            bindings[label]["path"]
        ):
            raise R25AfesExecutionV2Error(f"import_path_mismatch:{label}")
    return receipt_module, extractor_module


def build_payload(
    *, expected_contract_sha256: str, session_nonce: str, run_number: int
) -> tuple[dict[str, object], Any, Any]:
    if SESSION_PATTERN.fullmatch(session_nonce) is None:
        raise R25AfesExecutionV2Error("session_nonce_must_be_64_lowercase_hex")
    if run_number not in (1, 2):
        raise R25AfesExecutionV2Error("run_number_must_be_1_or_2")
    contract, observed_contract = _load_contract(expected_contract_sha256)
    receipt_module, extractor = _import_bound_modules(contract)
    inner = extractor.extract_payload()
    if inner.get("status") != "EXTRACTED_UNSEALED_REQUIRES_MATCHING_FRESH_LOCKED_RUN":
        raise R25AfesExecutionV2Error("attempt02_inner_status_drift")
    payload: dict[str, object] = {
        "schema": "kira.avatar.r25.foundation_afes_locked_extraction_run.v2",
        "status": "READ_ONLY_EXTRACTION_COMPLETE_PENDING_PAIR_MATCH",
        "execution_contract": observed_contract,
        "session_nonce": session_nonce,
        "run_number": run_number,
        "inner_attempt02_payload": inner,
        "truth_boundary": [
            "READ_ONLY_FOUNDATION_DIAGNOSTIC",
            "NO_BLEND_MUTATION_OR_SAVE",
            "NO_RENDER_OR_EXPORT",
            "NO_CANDIDATE_OR_BODY_AUTHORING",
            "THIS_SINGLE_RUN_IS_NOT_ACCEPTANCE",
        ],
    }
    frame = receipt_module.encode_receipt_frame(payload)
    if receipt_module.decode_receipt_frame(frame).payload != payload:
        raise R25AfesExecutionV2Error("execution_payload_roundtrip_drift")
    return payload, receipt_module, extractor


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-handle", required=True)
    parser.add_argument("--execution-contract-sha256", required=True)
    parser.add_argument("--session-nonce", required=True)
    parser.add_argument("--run-number", required=True)
    values = parser.parse_args(argv)
    try:
        values.result_handle = int(values.result_handle, 10)
        values.run_number = int(values.run_number, 10)
    except ValueError as exc:
        parser.error(f"numeric argument invalid: {exc}")
    return values


def main() -> int:
    values = _arguments()
    try:
        _require_pipe(values.result_handle)
        payload, _, extractor = build_payload(
            expected_contract_sha256=values.execution_contract_sha256,
            session_nonce=values.session_nonce,
            run_number=values.run_number,
        )
        extractor.write_receipt_frame_to_inherited_pipe(payload, values.result_handle)
    except Exception as exc:
        print(
            f"R25_AFES_LOCKED_EXECUTION_V2_FAILED: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
