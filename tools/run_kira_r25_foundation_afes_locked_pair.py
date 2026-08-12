#!/usr/bin/env python3
"""Run exactly two fresh locked R25 AFES read-only Blender diagnostics.

This controller grants no body authoring.  It holds deny-write/delete handles
to every bound input, launches exact Blender with a least-handle anonymous
pipe, drains one bounded canonical frame concurrently, validates and persists
the exact bytes append-only, and accepts only two semantically identical
fresh runs with distinct session nonces.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
from typing import Any, Iterable, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import kira_r25_afes_topology_core_v2 as topology_core  # noqa: E402
from tools import kira_r25_canonical_receipt as receipt  # noqa: E402


CONTRACT_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v1.json"
)


class LockedPairError(RuntimeError):
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
        raise LockedPairError(f"unsafe_project_relative_path:{text}")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise LockedPairError(f"symlink_path_refused:{text}")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise LockedPairError(f"path_escaped_project_root:{text}") from exc
    if not resolved.is_file():
        raise LockedPairError(f"bound_path_is_not_file:{text}")
    return resolved


def _verify_row(label: str, row: object) -> Path:
    if not isinstance(row, Mapping) or not {"path", "bytes", "sha256"}.issubset(row):
        raise LockedPairError(f"invalid_file_binding:{label}")
    path = _project_file(row["path"])
    if path.stat().st_size != row["bytes"] or _sha256_file(path) != row["sha256"]:
        raise LockedPairError(f"file_binding_drift:{label}")
    return path


def _load_contract(expected_sha256: str) -> tuple[dict[str, Any], Path]:
    path = _project_file(CONTRACT_RELATIVE_PATH)
    if _sha256_file(path) != expected_sha256:
        raise LockedPairError("execution_contract_hash_mismatch")
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise LockedPairError("execution_contract_invalid_json") from exc
    if not isinstance(contract, dict) or contract.get("schema") != (
        "kira.avatar.r25.foundation_afes_locked_pair_execution.v1"
    ):
        raise LockedPairError("execution_contract_schema_mismatch")
    if contract.get("status") != "AUTHORIZED_READ_ONLY_DIAGNOSTIC_PAIR_ONLY":
        raise LockedPairError("execution_contract_not_authorized")
    scope = contract.get("scope")
    if not isinstance(scope, Mapping) or scope.get("read_only_blender_diagnostic") is not True:
        raise LockedPairError("read_only_execution_scope_missing")
    for key in (
        "blend_mutation_allowed",
        "blend_save_allowed",
        "render_allowed",
        "candidate_creation_allowed",
        "body_authoring_allowed",
        "runtime_activation_allowed",
    ):
        if scope.get(key) is not False:
            raise LockedPairError(f"execution_scope_not_fail_closed:{key}")
    if contract.get("required_fresh_run_count") != 2:
        raise LockedPairError("execution_contract_does_not_require_exact_pair")
    return contract, path


def _collect_v2_binding_paths(config_path: Path) -> list[Path]:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise LockedPairError("attempt02_config_invalid_json") from exc
    result: list[Path] = [config_path]
    for table_name in ("bindings", "attempt_01_preservation"):
        table = config.get(table_name)
        if not isinstance(table, Mapping):
            raise LockedPairError(f"attempt02_binding_table_missing:{table_name}")
        for label, row in sorted(table.items()):
            result.append(_verify_row(f"{table_name}.{label}", row))
    return result


class WindowsReadLockSet:
    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 0x00000001
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x00000080

    def __init__(self) -> None:
        if os.name != "nt":
            raise LockedPairError("locked Blender pair is Windows-only")
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        self.kernel32.CreateFileW.restype = wintypes.HANDLE
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.handles: list[int] = []

    def add(self, path: Path) -> None:
        handle = self.kernel32.CreateFileW(
            str(path), self.GENERIC_READ, self.FILE_SHARE_READ, None,
            self.OPEN_EXISTING, self.FILE_ATTRIBUTE_NORMAL, None,
        )
        invalid = ctypes.c_void_p(-1).value
        if handle in (None, invalid):
            raise LockedPairError(
                f"cannot_lock_bound_input:{path}:winerror={ctypes.get_last_error()}"
            )
        self.handles.append(int(handle))

    def close(self) -> None:
        while self.handles:
            handle = self.handles.pop()
            if not self.kernel32.CloseHandle(handle):
                raise LockedPairError(
                    f"input_lock_close_failed:winerror={ctypes.get_last_error()}"
                )

    def __enter__(self) -> "WindowsReadLockSet":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


def _restricted_environment() -> dict[str, str]:
    allowed = (
        "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERNAME", "USERPROFILE",
        "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA", "APPDATA", "Path",
    )
    environment = {name: os.environ[name] for name in allowed if os.environ.get(name)}
    environment.update(
        {
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "BLENDER_USER_CONFIG": str(PROJECT_ROOT / "RecoverySprint/runtime_cache/r25_blender/user_config"),
            "BLENDER_USER_SCRIPTS": str(PROJECT_ROOT / "RecoverySprint/runtime_cache/r25_blender/user_scripts"),
            "BLENDER_USER_DATAFILES": str(PROJECT_ROOT / "RecoverySprint/runtime_cache/r25_blender/user_datafiles"),
        }
    )
    return environment


def _read_pipe_bounded(read_fd: int, destination: list[object]) -> None:
    try:
        with os.fdopen(read_fd, "rb", buffering=0, closefd=True) as stream:
            destination.append(stream.read(receipt.MAX_RECEIPT_FRAME_BYTES + 1))
    except BaseException as exc:
        destination.append(exc)


def _write_exclusive_bytes(path: Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    try:
        view, total = memoryview(data), 0
        while total < len(view):
            written = os.write(descriptor, view[total:])
            if written <= 0:
                raise LockedPairError(f"exclusive_log_short_write:{path.name}")
            total += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _run_child(
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    run_number: int,
    session_nonce: str,
    evidence_root: Path,
) -> tuple[bytes, receipt.DecodedReceipt, dict[str, Any]]:
    if os.name != "nt":
        raise LockedPairError("locked Blender pair is Windows-only")
    import msvcrt

    bindings = contract["bindings"]
    blender = Path(str(bindings["blender_executable"]["path"])).resolve(strict=True)
    foundation = _project_file(bindings["foundation_blend"]["path"])
    wrapper = _project_file(bindings["execution_wrapper"]["path"])
    read_fd, write_fd = os.pipe()
    read_results: list[object] = []
    reader = threading.Thread(
        target=_read_pipe_bounded, args=(read_fd, read_results), daemon=True
    )
    reader.start()
    write_handle = int(msvcrt.get_osfhandle(write_fd))
    os.set_inheritable(write_fd, True)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    startup.lpAttributeList = {"handle_list": [write_handle]}
    command = [
        str(blender),
        "--background",
        "--factory-startup",
        "--disable-autoexec",
        str(foundation),
        "--python-exit-code",
        "1",
        "--python",
        str(wrapper),
        "--",
        "--result-handle",
        str(write_handle),
        "--execution-contract-sha256",
        contract_sha256,
        "--session-nonce",
        session_nonce,
        "--run-number",
        str(run_number),
    ]
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process: subprocess.Popen[bytes] | None = None
    timed_out = False
    try:
        process = subprocess.Popen(
            command,
            cwd=str(PROJECT_ROOT),
            env=_restricted_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startup,
            creationflags=creation_flags,
            close_fds=True,
        )
    finally:
        os.close(write_fd)
    try:
        stdout, stderr = process.communicate(timeout=int(contract["process_timeout_seconds"]))
    except subprocess.TimeoutExpired:
        timed_out = True
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate(timeout=15)
    reader.join(timeout=15)
    _write_exclusive_bytes(evidence_root / f"run_{run_number:02d}_stdout.log", stdout)
    _write_exclusive_bytes(evidence_root / f"run_{run_number:02d}_stderr.log", stderr)
    if timed_out:
        raise LockedPairError(f"run_{run_number:02d}_timed_out")
    if reader.is_alive() or len(read_results) != 1:
        raise LockedPairError(f"run_{run_number:02d}_pipe_did_not_reach_eof")
    if isinstance(read_results[0], BaseException):
        raise LockedPairError(f"run_{run_number:02d}_pipe_read_failed:{read_results[0]}")
    frame = read_results[0]
    if not isinstance(frame, bytes):
        raise LockedPairError(f"run_{run_number:02d}_pipe_result_not_bytes")
    if len(frame) > receipt.MAX_RECEIPT_FRAME_BYTES:
        raise LockedPairError(f"run_{run_number:02d}_frame_too_large")
    if process.returncode != 0:
        raise LockedPairError(f"run_{run_number:02d}_blender_exit:{process.returncode}")
    decoded = receipt.decode_receipt_frame(frame)
    payload = decoded.payload
    if payload.get("schema") != "kira.avatar.r25.foundation_afes_locked_extraction_run.v1":
        raise LockedPairError(f"run_{run_number:02d}_schema_mismatch")
    if payload.get("status") != "READ_ONLY_EXTRACTION_COMPLETE_PENDING_PAIR_MATCH":
        raise LockedPairError(f"run_{run_number:02d}_status_mismatch")
    if payload.get("session_nonce") != session_nonce or payload.get("run_number") != run_number:
        raise LockedPairError(f"run_{run_number:02d}_session_binding_mismatch")
    if payload.get("execution_contract", {}).get("sha256") != contract_sha256:
        raise LockedPairError(f"run_{run_number:02d}_contract_binding_mismatch")
    inner = payload.get("inner_attempt02_payload")
    if not isinstance(inner, Mapping) or inner.get("status") != (
        "EXTRACTED_UNSEALED_REQUIRES_MATCHING_FRESH_LOCKED_RUN"
    ):
        raise LockedPairError(f"run_{run_number:02d}_inner_status_mismatch")
    analysis = inner.get("analysis")
    if not isinstance(analysis, Mapping):
        raise LockedPairError(f"run_{run_number:02d}_analysis_missing")
    topology_core.validate_compact_afes_analysis(analysis)
    receipt_path = evidence_root / f"run_{run_number:02d}_receipt.bin"
    with receipt.WindowsExclusiveReceiptReservation.reserve(receipt_path) as reservation:
        reservation.accept_child_frame(frame)
    metadata = {
        "run_number": run_number,
        "session_nonce": session_nonce,
        "pid": process.pid,
        "exit_code": process.returncode,
        "frame_bytes": len(frame),
        "frame_sha256": decoded.frame_sha256,
        "payload_sha256": decoded.payload_sha256,
        "inner_payload_sha256": hashlib.sha256(
            receipt.canonical_json_bytes(dict(inner))
        ).hexdigest(),
        "topology_sha256": analysis["topology_structure"][
            "full_normalized_topology_sha256"
        ],
    }
    return frame, decoded, metadata


def run_pair(expected_contract_sha256: str) -> Path:
    contract, contract_path = _load_contract(expected_contract_sha256)
    bindings = contract["bindings"]
    bound_paths = [
        _verify_row(label, row)
        for label, row in sorted(bindings.items())
        if label != "blender_executable"
    ]
    blender = Path(str(bindings["blender_executable"]["path"])).resolve(strict=True)
    if blender.stat().st_size != bindings["blender_executable"]["bytes"] or _sha256_file(blender) != (
        bindings["blender_executable"]["sha256"]
    ):
        raise LockedPairError("blender_executable_binding_drift")
    v2_config = _project_file(bindings["attempt02_config"]["path"])
    bound_paths.extend(_collect_v2_binding_paths(v2_config))
    bound_paths.extend((contract_path, blender))
    unique_paths = sorted(set(path.resolve(strict=True) for path in bound_paths), key=str)
    output_relative = Path(str(contract["append_only_output_root"]))
    if output_relative.is_absolute() or ".." in output_relative.parts:
        raise LockedPairError("unsafe_append_only_output_root")
    output_root = (PROJECT_ROOT / output_relative).resolve()
    output_root.relative_to(PROJECT_ROOT.resolve(strict=True))
    output_root.mkdir(parents=True, exist_ok=False)
    before = {
        path.relative_to(PROJECT_ROOT).as_posix() if path.is_relative_to(PROJECT_ROOT) else str(path): {
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
        for path in unique_paths
    }
    run_metadata: list[dict[str, Any]] = []
    decoded_runs: list[receipt.DecodedReceipt] = []
    with WindowsReadLockSet() as locks:
        for path in unique_paths:
            locks.add(path)
        for run_number in (1, 2):
            nonce = secrets.token_hex(32)
            _, decoded, metadata = _run_child(
                contract=contract,
                contract_sha256=expected_contract_sha256,
                run_number=run_number,
                session_nonce=nonce,
                evidence_root=output_root,
            )
            decoded_runs.append(decoded)
            run_metadata.append(metadata)
    after = {
        path.relative_to(PROJECT_ROOT).as_posix() if path.is_relative_to(PROJECT_ROOT) else str(path): {
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
        for path in unique_paths
    }
    if before != after:
        raise LockedPairError("bound_input_changed_during_locked_pair")
    if run_metadata[0]["session_nonce"] == run_metadata[1]["session_nonce"]:
        raise LockedPairError("fresh_run_nonces_are_not_distinct")
    first_inner = decoded_runs[0].payload["inner_attempt02_payload"]
    second_inner = decoded_runs[1].payload["inner_attempt02_payload"]
    if first_inner != second_inner:
        raise LockedPairError("fresh_locked_inner_payloads_do_not_match")
    if run_metadata[0]["topology_sha256"] != run_metadata[1]["topology_sha256"]:
        raise LockedPairError("fresh_locked_topology_digests_do_not_match")
    summary = {
        "schema": "kira.avatar.r25.foundation_afes_locked_pair_acceptance.v1",
        "status": "AFES_AND_TRANSITION_RINGS_EXTRACTED_READ_ONLY_PAIR_MATCHED",
        "execution_contract_sha256": expected_contract_sha256,
        "execution_contract_bytes": contract_path.stat().st_size,
        "input_snapshot_before_sha256": hashlib.sha256(
            receipt.canonical_json_bytes(before)
        ).hexdigest(),
        "input_snapshot_after_sha256": hashlib.sha256(
            receipt.canonical_json_bytes(after)
        ).hexdigest(),
        "bound_inputs_unchanged": True,
        "runs": run_metadata,
        "matching_inner_payload_sha256": run_metadata[0]["inner_payload_sha256"],
        "full_normalized_topology_sha256": run_metadata[0]["topology_sha256"],
        "truth_boundary": [
            "READ_ONLY_DIAGNOSTIC_PAIR_ONLY",
            "NO_BLEND_MUTATION_OR_SAVE",
            "NO_BODY_CANDIDATE",
            "NO_AUTHORING_OR_RUNTIME_AUTHORITY",
        ],
    }
    summary_frame = receipt.encode_receipt_frame(summary)
    with receipt.WindowsExclusiveReceiptReservation.reserve(
        output_root / "PAIR_ACCEPTANCE.receipt.bin"
    ) as reservation:
        reservation.accept_child_frame(summary_frame)
    return output_root


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-contract-sha256", required=True)
    return parser.parse_args()


def main() -> int:
    values = _arguments()
    try:
        output = run_pair(values.expected_contract_sha256)
    except Exception as exc:
        print(f"R25_AFES_LOCKED_PAIR_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(output.relative_to(PROJECT_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
