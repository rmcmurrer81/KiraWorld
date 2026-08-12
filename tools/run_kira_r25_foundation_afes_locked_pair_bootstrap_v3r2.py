#!/usr/bin/env python3
"""Trusted retained-byte launch boundary for R25 locked-pair Attempt 03r2.

This small standard-library entry point is the only permitted controller
launcher.  It discovers path spellings without trusting their bytes, acquires
deny-write/delete handles for the complete recursive contract graph and the
fresh audit, verifies the out-of-band contract/bootstrap/audit digests, then
compiles the exact retained controller bytes into a private module while all
locks remain held.  It performs no Blender or body operation itself.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from types import ModuleType
from typing import Any, Iterable, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v3r2.json"
)
AUDIT_RELATIVE_PATH = (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution_static_preparation/"
    "attempt_03r2/INDEPENDENT_AUDIT.json"
)
BOOTSTRAP_RELATIVE_PATH = (
    "tools/run_kira_r25_foundation_afes_locked_pair_bootstrap_v3r2.py"
)
HEX64 = re.compile(r"[0-9a-f]{64}")


class LockedPairBootstrapV3R2Error(RuntimeError):
    """The trusted pre-controller launch boundary failed closed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _project_file(relative: object) -> Path:
    text = str(relative or "")
    candidate = Path(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts:
        raise LockedPairBootstrapV3R2Error(f"unsafe_project_relative_path:{text}")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise LockedPairBootstrapV3R2Error(f"symlink_path_refused:{text}")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise LockedPairBootstrapV3R2Error(f"path_escaped_project_root:{text}") from exc
    if not resolved.is_file():
        raise LockedPairBootstrapV3R2Error(f"bound_path_is_not_file:{text}")
    return resolved


def _row_path(label: str, row: Mapping[str, object]) -> Path:
    if label == "blender_executable":
        path = Path(str(row.get("path", ""))).resolve(strict=True)
        if not path.is_file():
            raise LockedPairBootstrapV3R2Error("blender_binding_is_not_file")
        return path
    return _project_file(row.get("path"))


def _parse_object(value: bytes, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value.decode("utf-8-sig"))
    except Exception as exc:
        raise LockedPairBootstrapV3R2Error(f"invalid_json:{label}") from exc
    if not isinstance(parsed, dict):
        raise LockedPairBootstrapV3R2Error(f"json_root_not_object:{label}")
    return parsed


def _iter_contract_rows(
    contract: Mapping[str, Any],
) -> Iterable[tuple[str, Mapping[str, object]]]:
    tables = (
        ("bindings", contract.get("bindings"), False),
        ("afes_v5_transitive_rows", contract.get("afes_v5_transitive_rows"), True),
        (
            "child_runtime_read_closure_completion",
            contract.get("child_runtime_read_closure_completion"), False,
        ),
        (
            "locked_pair_attempt_01_preservation",
            contract.get("locked_pair_attempt_01_preservation"), False,
        ),
        (
            "locked_pair_attempt_02_preservation",
            contract.get("locked_pair_attempt_02_preservation"), False,
        ),
        (
            "locked_pair_v3r1_preservation",
            contract.get("locked_pair_v3r1_preservation"), False,
        ),
    )
    for table_name, table, nested_table in tables:
        if not isinstance(table, Mapping) or not table:
            raise LockedPairBootstrapV3R2Error(f"discovery_table_missing:{table_name}")
        if nested_table:
            for nested_name, nested in table.items():
                if not isinstance(nested, Mapping) or not nested:
                    raise LockedPairBootstrapV3R2Error(
                        f"discovery_nested_table_missing:{table_name}.{nested_name}"
                    )
                for label, row in nested.items():
                    if not isinstance(row, Mapping) or "path" not in row:
                        raise LockedPairBootstrapV3R2Error(
                            f"discovery_row_invalid:{table_name}.{nested_name}.{label}"
                        )
                    yield f"{table_name}.{nested_name}.{label}", row
        else:
            for label, row in table.items():
                if not isinstance(row, Mapping) or "path" not in row:
                    raise LockedPairBootstrapV3R2Error(
                        f"discovery_row_invalid:{table_name}.{label}"
                    )
                yield f"{table_name}.{label}", row


def _discover_complete_paths() -> tuple[Path, list[Path]]:
    contract_path = _project_file(CONTRACT_RELATIVE_PATH)
    contract = _parse_object(contract_path.read_bytes(), "untrusted_discovery_contract")
    paths = [contract_path, _project_file(AUDIT_RELATIVE_PATH)]
    for compound_label, row in _iter_contract_rows(contract):
        paths.append(_row_path(compound_label.rsplit(".", 1)[-1], row))
    return contract_path, sorted(
        {path.resolve(strict=True) for path in paths},
        key=lambda path: str(path).casefold(),
    )


class WindowsBootstrapReadLockSet:
    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 0x00000001
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x00000080

    def __init__(self) -> None:
        if os.name != "nt":
            raise LockedPairBootstrapV3R2Error("locked_bootstrap_is_windows_only")
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
        ]
        self.kernel32.CreateFileW.restype = wintypes.HANDLE
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.invalid = ctypes.c_void_p(-1).value
        self.handles: list[int] = []
        self.locked_paths: list[Path] = []
        self.active = False

    def __enter__(self) -> "WindowsBootstrapReadLockSet":
        self.active = True
        return self

    def add(self, path: Path) -> None:
        if not self.active:
            raise LockedPairBootstrapV3R2Error("lock_add_outside_context")
        exact = Path(path).resolve(strict=True)
        handle = self.kernel32.CreateFileW(
            str(exact), self.GENERIC_READ, self.FILE_SHARE_READ, None,
            self.OPEN_EXISTING, self.FILE_ATTRIBUTE_NORMAL, None,
        )
        raw = int(handle) if handle is not None else 0
        if raw == 0 or raw == self.invalid:
            raise LockedPairBootstrapV3R2Error(
                f"cannot_lock_bound_input:{exact}:winerror={ctypes.get_last_error()}"
            )
        self.handles.append(raw)
        self.locked_paths.append(exact)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        errors: list[str] = []
        for raw in reversed(self.handles):
            if not self.kernel32.CloseHandle(wintypes.HANDLE(raw)):
                errors.append(str(ctypes.get_last_error()))
        self.handles.clear()
        self.active = False
        if errors and exc is None:
            raise LockedPairBootstrapV3R2Error(
                "bootstrap_input_lock_close_failed:" + ",".join(errors)
            )


def _with_complete_lock_set(
    paths: Iterable[Path], body: Any,
    lock_factory: Any = WindowsBootstrapReadLockSet,
) -> Any:
    ordered = sorted(
        {Path(path).resolve(strict=True) for path in paths},
        key=lambda path: str(path).casefold(),
    )
    with lock_factory() as locks:
        for path in ordered:
            locks.add(path)
        return body(locks)


def _read_exact_locked(
    *, row: object, label: str, locked_paths: set[Path],
) -> tuple[Path, bytes]:
    if not isinstance(row, Mapping) or set(row) != {"path", "bytes", "sha256"}:
        raise LockedPairBootstrapV3R2Error(f"invalid_locked_binding:{label}")
    if type(row["bytes"]) is not int or row["bytes"] < 0:
        raise LockedPairBootstrapV3R2Error(f"invalid_locked_binding_bytes:{label}")
    if not isinstance(row["sha256"], str) or HEX64.fullmatch(row["sha256"]) is None:
        raise LockedPairBootstrapV3R2Error(f"invalid_locked_binding_sha256:{label}")
    path = _row_path(label, row).resolve(strict=True)
    if path not in locked_paths:
        raise LockedPairBootstrapV3R2Error(f"unlocked_bootstrap_read_refused:{label}")
    value = path.read_bytes()
    if len(value) != row["bytes"] or _sha256_bytes(value) != row["sha256"]:
        raise LockedPairBootstrapV3R2Error(f"locked_bootstrap_binding_drift:{label}")
    return path, value


def _load_retained_controller(
    *, contract: Mapping[str, Any], contract_path: Path,
    paths: list[Path], locks: WindowsBootstrapReadLockSet,
    expected_contract_sha256: str, expected_bootstrap_sha256: str,
    accepted_controller_audit_sha256: str,
) -> ModuleType:
    locked_paths = {Path(path).resolve(strict=True) for path in locks.locked_paths}
    if not locks.active or locked_paths != set(paths):
        raise LockedPairBootstrapV3R2Error("incomplete_bootstrap_lock_set")
    contract_bytes = contract_path.read_bytes()
    if _sha256_bytes(contract_bytes) != expected_contract_sha256:
        raise LockedPairBootstrapV3R2Error("locked_contract_hash_mismatch")
    contract = _parse_object(contract_bytes, "locked_contract")
    if contract.get("schema") != (
        "kira.avatar.r25.foundation_afes_locked_pair_execution.v3r2"
    ) or contract.get("attempt_id") != "attempt_03r2":
        raise LockedPairBootstrapV3R2Error("locked_contract_identity_drift")
    bindings = contract.get("bindings")
    if not isinstance(bindings, Mapping):
        raise LockedPairBootstrapV3R2Error("locked_binding_table_missing")
    bootstrap_path, bootstrap_bytes = _read_exact_locked(
        row=bindings.get("trusted_bootstrap"), label="trusted_bootstrap",
        locked_paths=locked_paths,
    )
    if bootstrap_path != Path(__file__).resolve(strict=True) or _sha256_bytes(
        bootstrap_bytes
    ) != expected_bootstrap_sha256:
        raise LockedPairBootstrapV3R2Error("trusted_bootstrap_hash_mismatch")
    audit_path = _project_file(AUDIT_RELATIVE_PATH)
    if audit_path not in locked_paths or _sha256_bytes(audit_path.read_bytes()) != (
        accepted_controller_audit_sha256
    ):
        raise LockedPairBootstrapV3R2Error("locked_audit_hash_mismatch")
    controller_path, controller_bytes = _read_exact_locked(
        row=bindings.get("parent_controller"), label="parent_controller",
        locked_paths=locked_paths,
    )
    controller_sha256 = _sha256_bytes(controller_bytes)
    private = ModuleType("_kira_r25_locked_pair_controller_v3r2_retained")
    private.__file__ = str(controller_path)
    private.__package__ = ""
    private.__spec__ = None
    private.__loader__ = None
    private.__dict__["BOOTSTRAP_RETAINED_CONTROLLER_SHA256"] = controller_sha256
    exec(
        compile(controller_bytes, str(controller_path), "exec", dont_inherit=True),
        private.__dict__, private.__dict__,
    )
    run_pair = getattr(private, "run_pair_from_bootstrap", None)
    if not callable(run_pair) or Path(run_pair.__code__.co_filename).resolve(strict=True) != (
        controller_path
    ):
        raise LockedPairBootstrapV3R2Error("retained_controller_entrypoint_drift")
    return private


def run(
    expected_contract_sha256: str, accepted_controller_audit_sha256: str,
    expected_bootstrap_sha256: str,
) -> Path:
    for label, value in (
        ("expected_contract_sha256", expected_contract_sha256),
        ("accepted_controller_audit_sha256", accepted_controller_audit_sha256),
        ("expected_bootstrap_sha256", expected_bootstrap_sha256),
    ):
        if not isinstance(value, str) or HEX64.fullmatch(value) is None:
            raise LockedPairBootstrapV3R2Error(f"{label}_must_be_64_lowercase_hex")
    contract_path, paths = _discover_complete_paths()
    untrusted_contract = _parse_object(
        contract_path.read_bytes(), "untrusted_discovery_contract"
    )
    def locked_body(locks: WindowsBootstrapReadLockSet) -> Path:
        controller = _load_retained_controller(
            contract=untrusted_contract, contract_path=contract_path,
            paths=paths, locks=locks,
            expected_contract_sha256=expected_contract_sha256,
            expected_bootstrap_sha256=expected_bootstrap_sha256,
            accepted_controller_audit_sha256=accepted_controller_audit_sha256,
        )
        return controller.run_pair_from_bootstrap(
            expected_contract_sha256,
            accepted_controller_audit_sha256,
            contract_path=contract_path,
            discovered_paths=paths,
            locks=locks,
        )
    return _with_complete_lock_set(paths, locked_body)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-contract-sha256", required=True)
    parser.add_argument("--accepted-controller-audit-sha256", required=True)
    parser.add_argument("--expected-bootstrap-sha256", required=True)
    return parser.parse_args()


def main() -> int:
    values = _arguments()
    try:
        run(
            values.expected_contract_sha256,
            values.accepted_controller_audit_sha256,
            values.expected_bootstrap_sha256,
        )
    except Exception as exc:
        print(
            f"R25_AFES_LOCKED_PAIR_BOOTSTRAP_V3R2_FAILED: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    print("R25_AFES_LOCKED_PAIR_BOOTSTRAP_V3R2_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
