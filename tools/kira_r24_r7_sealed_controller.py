from __future__ import annotations

"""Fresh, exact, lease-owning controller for the append-only R24 R7 gate.

This entry imports no project module until its exact contract, controller,
worker, and complete runtime dependency set are protected by Windows handles
that deny write and delete sharing.  R7 remains static-only.
"""

import argparse
import contextlib
import copy
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from types import MappingProxyType
from typing import Iterator, Mapping


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7"
)
DEFAULT_CONTRACT = PACKAGE / "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R7_CONTRACT.json"
SEALED_CONTRACT_FILE_SHA256 = "0000000000000000000000000000000000000000000000000000000000000000"
SEALED_CONTRACT_SEMANTIC_SHA256 = "0000000000000000000000000000000000000000000000000000000000000000"


class ControllerError(RuntimeError):
    pass


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_sealed_python_sha256(path: Path) -> str:
    prefixes = (
        b'SEALED_CONTRACT_FILE_SHA256 = "',
        b'SEALED_CONTRACT_SEMANTIC_SHA256 = "',
    )
    found: set[bytes] = set()
    output: list[bytes] = []
    for line in path.read_bytes().splitlines(keepends=True):
        replacement = line
        for prefix in prefixes:
            if line.startswith(prefix):
                suffix = line[len(prefix) + 64 :]
                if not suffix.startswith(b'"'):
                    raise ControllerError("sealed Python literal shape changed")
                replacement = prefix + b"0" * 64 + suffix
                found.add(prefix)
        output.append(replacement)
    if found != set(prefixes):
        raise ControllerError("sealed Python field inventory changed")
    return hashlib.sha256(b"".join(output)).hexdigest()


def semantic_projection(value: Mapping[str, object]) -> dict[str, object]:
    result = copy.deepcopy(dict(value))
    result["semantic_seal_sha256"] = ""
    return result


def deep_freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): deep_freeze(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(deep_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(deep_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(deep_freeze(item) for item in value)
    return value


def _project_path(record: Mapping[str, object]) -> Path:
    path = (ROOT / str(record.get("path", ""))).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ControllerError("project dependency escapes the sealed root") from exc
    return path


def _validate_exact_record(record: Mapping[str, object]) -> Path:
    if set(record) != {"path", "bytes", "sha256"}:
        raise ControllerError("exact-file record field inventory changed")
    path = _project_path(record)
    if (
        not path.is_file()
        or path.stat().st_size != record["bytes"]
        or sha256_file(path) != record["sha256"]
    ):
        raise ControllerError(f"exact dependency identity changed: {record.get('path')}")
    return path


class ReadDenyWriteDeleteLease:
    def __init__(self, path: Path) -> None:
        if os.name != "nt":
            raise ControllerError("R7 dependency leases require Windows")
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
        ]
        kernel32.CreateFileW.restype = wintypes.HANDLE
        handle = kernel32.CreateFileW(
            str(path),
            0x80000000,  # GENERIC_READ
            0x00000001,  # FILE_SHARE_READ only
            None,
            3,  # OPEN_EXISTING
            0x08000000,  # SEQUENTIAL_SCAN
            None,
        )
        invalid = ctypes.c_void_p(-1).value
        if not handle or int(handle) == invalid:
            raise ControllerError(
                f"cannot acquire deny-write/delete lease for {path}: "
                f"Windows error {ctypes.get_last_error()}"
            )
        self.path = path
        self.handle = int(handle)

    def close(self) -> None:
        if self.handle:
            ctypes.windll.kernel32.CloseHandle(wintypes.HANDLE(self.handle))
            self.handle = 0


@contextlib.contextmanager
def lease_exact_paths(paths: Mapping[str, Path]) -> Iterator[dict[str, ReadDenyWriteDeleteLease]]:
    leases: dict[str, ReadDenyWriteDeleteLease] = {}
    try:
        for role in sorted(paths):
            leases[role] = ReadDenyWriteDeleteLease(paths[role])
        yield leases
    finally:
        for lease in reversed(list(leases.values())):
            lease.close()


def _load_and_validate_overlay() -> tuple[dict[str, object], str, bytes]:
    raw = DEFAULT_CONTRACT.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SEALED_CONTRACT_FILE_SHA256:
        raise ControllerError("R7 contract file identity changed")
    try:
        overlay = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ControllerError("R7 contract is not exact JSON") from exc
    semantic = canonical_sha256(semantic_projection(overlay))
    if (
        semantic != SEALED_CONTRACT_SEMANTIC_SHA256
        or overlay.get("semantic_seal_sha256") != semantic
        or overlay.get("schema") != "kira.avatar.r24.artifact_derived_gate.v7"
    ):
        raise ControllerError("R7 contract semantic identity changed")
    return overlay, semantic, raw


def _lease_inventory(
    overlay: Mapping[str, object], raw: bytes
) -> tuple[dict[str, Path], list[dict[str, object]]]:
    implementation = overlay.get("authorized_implementation")
    parents = overlay.get("parent_bindings")
    if not isinstance(implementation, Mapping) or not isinstance(parents, Mapping):
        raise ControllerError("controller contract inventories are absent")
    runtime = implementation.get("runtime_dependencies")
    if not isinstance(runtime, Mapping):
        raise ControllerError("runtime dependency inventory is absent")
    paths: dict[str, Path] = {"contract": DEFAULT_CONTRACT.resolve()}
    rows: list[dict[str, object]] = [
        {
            "role": "contract",
            "path": DEFAULT_CONTRACT.relative_to(ROOT).as_posix(),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    ]
    for prefix, records in (("parent", parents), ("runtime", runtime)):
        for role, record in sorted(records.items()):
            if not isinstance(record, Mapping):
                raise ControllerError(f"{prefix} record {role!r} is malformed")
            path = _validate_exact_record(record)
            key = f"{prefix}:{role}"
            paths[key] = path
            rows.append({"role": key, **dict(record)})

    worker = implementation.get("worker")
    controller = implementation.get("sealed_controller")
    for role, record, expected_path in (
        ("worker", worker, ROOT / "tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py"),
        ("controller", controller, Path(__file__)),
    ):
        if not isinstance(record, Mapping) or set(record) != {
            "path", "normalized_semantic_sha256"
        }:
            raise ControllerError(f"normalized {role} record changed")
        path = _project_path(record)
        if path != expected_path.resolve():
            raise ControllerError(f"normalized {role} path changed")
        normalized = normalized_sealed_python_sha256(path)
        if normalized != record["normalized_semantic_sha256"]:
            raise ControllerError(f"normalized {role} identity changed")
        paths[role] = path
        rows.append(
            {
                "role": role,
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": int(path.stat().st_size),
                "sha256": sha256_file(path),
                "normalized_semantic_sha256": normalized,
            }
        )

    focused = implementation.get("focused_test")
    if not isinstance(focused, Mapping):
        raise ControllerError("focused-test binding absent")
    focused_path = _validate_exact_record(focused)
    paths["focused_test"] = focused_path
    rows.append({"role": "focused_test", **dict(focused)})
    python = implementation.get("python_executable")
    if not isinstance(python, Mapping) or set(python) != {"path", "bytes", "sha256"}:
        raise ControllerError("Python binding changed")
    python_path = Path(str(python["path"])).resolve()
    if (
        python_path != Path(sys.executable).resolve()
        or not python_path.is_file()
        or python_path.stat().st_size != python["bytes"]
        or sha256_file(python_path) != python["sha256"]
    ):
        raise ControllerError("fresh controller is not running under sealed Python")
    paths["python"] = python_path
    rows.append({"role": "python", **dict(python)})
    return paths, rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--blender", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if Path(args.contract).resolve() != DEFAULT_CONTRACT.resolve():
        raise ControllerError("caller selected a non-sealed contract")
    if not re.fullmatch(r"attempt_[0-9]{2}", args.attempt):
        raise ControllerError("attempt name is not exact")
    overlay, semantic, raw = _load_and_validate_overlay()
    paths, rows = _lease_inventory(overlay, raw)
    with lease_exact_paths(paths):
        # Revalidate every identity after all leases exist.  A timed swap can
        # occur before acquisition, but cannot survive this second check or
        # change any leased byte during the transaction.
        overlay_after, semantic_after, raw_after = _load_and_validate_overlay()
        if raw_after != raw or semantic_after != semantic or overlay_after != overlay:
            raise ControllerError("R7 contract changed during lease acquisition")
        paths_after, rows_after = _lease_inventory(overlay_after, raw_after)
        if paths_after != paths or rows_after != rows:
            raise ControllerError("R7 dependency set changed during lease acquisition")
        frozen_overlay = deep_freeze(overlay)
        if not isinstance(frozen_overlay, Mapping):
            raise ControllerError("deep-frozen contract overlay is not a mapping")
        dependency_bundle_sha256 = canonical_sha256(rows)

        # Import the complete project implementation only after every source
        # path it can import is lease-protected.
        while str(ROOT) in sys.path:
            sys.path.remove(str(ROOT))
        sys.path.insert(0, str(ROOT))
        from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7 as r7

        merged = r7._merge_contract_overlay(frozen_overlay, semantic)
        result = r7.execute_from_fresh_controller(
            merged,
            args.attempt,
            Path(args.blender),
            dependency_bundle_sha256=dependency_bundle_sha256,
            controller_pid=os.getpid(),
        )
        result_failures = r7.validate_controller_gate_result(
            result,
            required_schema=str(
                merged["authorized_implementation"]["required_gate_schema"]
            ),
            dependency_bundle_sha256=dependency_bundle_sha256,
        )
        if result_failures:
            raise ControllerError(
                "controller result schema failed: " + ",".join(sorted(result_failures))
            )
        controller_path = Path(__file__).resolve()
        envelope = {
            "schema": "kira.avatar.r24.r7.sealed_controller_envelope.v1",
            "contract": {
                "path": str(DEFAULT_CONTRACT.resolve()),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "semantic_sha256": semantic,
            },
            "controller": {
                "pid": os.getpid(),
                "path": str(controller_path),
                "bytes": int(controller_path.stat().st_size),
                "sha256": sha256_file(controller_path),
                "normalized_semantic_sha256": normalized_sealed_python_sha256(
                    controller_path
                ),
            },
            "attempt": args.attempt,
            "dependency_bundle_sha256": dependency_bundle_sha256,
            "result": result,
            "truth": {
                "fresh_controller_process": True,
                "contract_recursively_immutable": True,
                "dependency_leases_held_through_result": True,
                "caller_selected_implementation": False,
            },
        }
        sys.stdout.buffer.write(canonical_json(envelope) + b"\n")
        sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
