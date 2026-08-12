#!/usr/bin/env python3
"""Authorized read-only wrapper for the R25 AFES Attempt-02 extractor.

The immutable Attempt-02 extractor remains the implementation that inspects
the already-open foundation.  This wrapper adds a parent-selected execution
contract hash, a unique session nonce, and a run ordinal before writing one
canonical frame to the caller-inherited Win32 pipe.  It exposes no pathname
result, mutation, save, render, export, or candidate-authoring surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import (  # noqa: E402
    blender_extract_kira_r25_foundation_afes_transition_rings_v2 as attempt02,
)
from tools import kira_r25_canonical_receipt as canonical_receipt  # noqa: E402


CONTRACT_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v1.json"
)
SESSION_PATTERN = re.compile(r"[0-9a-f]{64}")


class R25AfesExecutionWrapperError(RuntimeError):
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
        raise R25AfesExecutionWrapperError("unsafe_project_relative_path")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise R25AfesExecutionWrapperError("symlink_path_refused")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise R25AfesExecutionWrapperError("path_escaped_project_root") from exc
    if not resolved.is_file():
        raise R25AfesExecutionWrapperError("bound_path_is_not_file")
    return resolved


def _load_execution_contract(expected_sha256: str) -> tuple[dict[str, Any], dict[str, object]]:
    path = _project_file(CONTRACT_RELATIVE_PATH)
    observed_sha256 = _sha256_file(path)
    if observed_sha256 != expected_sha256:
        raise R25AfesExecutionWrapperError("execution_contract_hash_mismatch")
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise R25AfesExecutionWrapperError("execution_contract_invalid_json") from exc
    if not isinstance(contract, dict) or contract.get("schema") != (
        "kira.avatar.r25.foundation_afes_locked_pair_execution.v1"
    ):
        raise R25AfesExecutionWrapperError("execution_contract_schema_mismatch")
    if contract.get("status") != "AUTHORIZED_READ_ONLY_DIAGNOSTIC_PAIR_ONLY":
        raise R25AfesExecutionWrapperError("execution_contract_not_authorized")
    scope = contract.get("scope")
    if not isinstance(scope, Mapping) or scope.get("read_only_blender_diagnostic") is not True:
        raise R25AfesExecutionWrapperError("execution_scope_missing")
    for forbidden in (
        "blend_mutation_allowed",
        "blend_save_allowed",
        "render_allowed",
        "candidate_creation_allowed",
        "body_authoring_allowed",
        "runtime_activation_allowed",
    ):
        if scope.get(forbidden) is not False:
            raise R25AfesExecutionWrapperError(f"execution_scope_not_fail_closed:{forbidden}")
    bindings = contract.get("bindings")
    if not isinstance(bindings, Mapping):
        raise R25AfesExecutionWrapperError("execution_binding_table_missing")
    for label in ("execution_wrapper", "attempt02_extractor", "attempt02_config"):
        row = bindings.get(label)
        if not isinstance(row, Mapping):
            raise R25AfesExecutionWrapperError(f"execution_binding_missing:{label}")
        bound = _project_file(row.get("path"))
        if bound.stat().st_size != row.get("bytes") or _sha256_file(bound) != row.get("sha256"):
            raise R25AfesExecutionWrapperError(f"execution_binding_drift:{label}")
    wrapper = _project_file(bindings["execution_wrapper"]["path"])
    if wrapper != Path(__file__).resolve(strict=True):
        raise R25AfesExecutionWrapperError("execution_wrapper_import_path_mismatch")
    if _project_file(bindings["attempt02_extractor"]["path"]) != Path(
        attempt02.__file__
    ).resolve(strict=True):
        raise R25AfesExecutionWrapperError("attempt02_extractor_import_path_mismatch")
    return contract, {
        "path": path.relative_to(PROJECT_ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": observed_sha256,
    }


def build_execution_payload(
    *, expected_contract_sha256: str, session_nonce: str, run_number: int
) -> dict[str, object]:
    if SESSION_PATTERN.fullmatch(session_nonce) is None:
        raise R25AfesExecutionWrapperError("session_nonce_must_be_64_lowercase_hex")
    if run_number not in (1, 2):
        raise R25AfesExecutionWrapperError("run_number_must_be_1_or_2")
    _, observed_contract = _load_execution_contract(expected_contract_sha256)
    inner = attempt02.extract_payload()
    if inner.get("status") != "EXTRACTED_UNSEALED_REQUIRES_MATCHING_FRESH_LOCKED_RUN":
        raise R25AfesExecutionWrapperError("attempt02_inner_status_drift")
    payload: dict[str, object] = {
        "schema": "kira.avatar.r25.foundation_afes_locked_extraction_run.v1",
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
    frame = canonical_receipt.encode_receipt_frame(payload)
    if canonical_receipt.decode_receipt_frame(frame).payload != payload:
        raise R25AfesExecutionWrapperError("execution_payload_roundtrip_drift")
    return payload


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
        payload = build_execution_payload(
            expected_contract_sha256=values.execution_contract_sha256,
            session_nonce=values.session_nonce,
            run_number=values.run_number,
        )
        attempt02.write_receipt_frame_to_inherited_pipe(payload, values.result_handle)
    except Exception as exc:
        print(
            f"R25_AFES_LOCKED_EXECUTION_FAILED: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
