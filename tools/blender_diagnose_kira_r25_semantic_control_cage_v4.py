#!/usr/bin/env python3
from __future__ import annotations

"""Append-only static v4 wrapper for one R25 semantic-cage diagnostic.

The checked-in v4 contract is intentionally unsealed, so this source fails
before loading Blender data.  A later append-only sealed revision may reuse
this design only after binding an independently accepted AFES v3r3 pair.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import types
from typing import Any, Mapping, Sequence

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_semantic_control_cage_diagnostic_v4.json"
)
SCHEMA = "kira.avatar.r25.semantic_control_cage_diagnostic.v4"
ATTEMPT_ID = "attempt_04_static_unsealed"
PREPARATION_STATUS = "STATIC_PREPARATION_ONLY_V3R3_EVIDENCE_NOT_SEALED_EXECUTION_FORBIDDEN"
SEALED_STATUS = "SEALED_IN_APPEND_ONLY_SUCCESSOR_TO_INDEPENDENTLY_ACCEPTED_AFES_V3R3_PAIR"
MAX_INPUT_FRAMES = 3
HEX64 = re.compile(r"[0-9a-f]{64}")


class R25SemanticControlCageV4Error(RuntimeError):
    pass


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _project_file(relative: object, suffix: str | None = None) -> Path:
    if not isinstance(relative, str) or not relative:
        raise R25SemanticControlCageV4Error("project_path_not_text")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise R25SemanticControlCageV4Error("unsafe_project_relative_path")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise R25SemanticControlCageV4Error("symlink_project_binding_refused")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise R25SemanticControlCageV4Error("project_binding_escaped_root") from exc
    if not resolved.is_file() or (suffix and resolved.suffix.lower() != suffix):
        raise R25SemanticControlCageV4Error("project_binding_type_mismatch")
    return resolved


def _verified_row(label: str, row: object, suffix: str | None = None) -> tuple[Path, bytes]:
    if not isinstance(row, Mapping) or not {"path", "bytes", "sha256"}.issubset(row):
        raise R25SemanticControlCageV4Error(f"binding_row_invalid:{label}")
    path = _project_file(row["path"], suffix)
    raw = path.read_bytes()
    if len(raw) != row["bytes"] or _sha256(raw) != row["sha256"]:
        raise R25SemanticControlCageV4Error(f"binding_drift:{label}")
    return path, raw


def _read_config(expected_sha256: str) -> tuple[dict[str, Any], bytes]:
    if HEX64.fullmatch(expected_sha256 or "") is None:
        raise R25SemanticControlCageV4Error("expected_config_sha256_invalid")
    raw = _project_file(CONFIG_RELATIVE_PATH, ".json").read_bytes()
    if _sha256(raw) != expected_sha256:
        raise R25SemanticControlCageV4Error("v4_config_sha256_mismatch")
    try:
        config = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise R25SemanticControlCageV4Error("v4_config_invalid_json") from exc
    if not isinstance(config, dict) or config.get("schema") != SCHEMA or config.get("attempt_id") != ATTEMPT_ID:
        raise R25SemanticControlCageV4Error("v4_config_identity_drift")
    if config.get("status") != SEALED_STATUS:
        if config.get("status") == PREPARATION_STATUS:
            raise R25SemanticControlCageV4Error("v4_static_preparation_is_not_execution_authority")
        raise R25SemanticControlCageV4Error("v4_config_status_drift")
    pair = config.get("afes_v3r3_pair_binding")
    if not isinstance(pair, Mapping) or pair.get("seal_status") != "SEALED_FINAL_INDEPENDENTLY_ACCEPTED_V3R3_PAIR":
        raise R25SemanticControlCageV4Error("v3r3_pair_not_sealed")
    if pair.get("required_final_placeholders") or pair.get("expected_pair_and_analysis") is None:
        raise R25SemanticControlCageV4Error("v3r3_pair_placeholders_remain")
    return config, raw


def _private_module(label: str, path: Path, raw: bytes) -> types.ModuleType:
    name = f"_kira_private_semantic_v4_{label}_{_sha256(raw)[:16]}"
    if name in sys.modules:
        raise R25SemanticControlCageV4Error(f"private_namespace_preexists:{label}")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    exec(compile(raw, str(path), "exec"), module.__dict__)
    if name in sys.modules:
        raise R25SemanticControlCageV4Error(f"private_module_registered:{label}")
    return module


def _verified_runtime(config: Mapping[str, Any]):
    bindings = config.get("bindings")
    if not isinstance(bindings, Mapping):
        raise R25SemanticControlCageV4Error("bindings_missing")
    required = {
        "execution_wrapper", "attempt03_accepted_runtime", "v3r3_afes_adapter",
        "canonical_receipt_primitive", "pure_control_cage_core",
        "qualified_foundation_blend", "r19_visual_target_blend",
        "r20_exact_rejected_target_region", "makehuman_default_weights",
    }
    if not required.issubset(bindings):
        raise R25SemanticControlCageV4Error("required_binding_missing")
    wrapper_path, _ = _verified_row("execution_wrapper", bindings["execution_wrapper"], ".py")
    if wrapper_path != Path(__file__).resolve(strict=True):
        raise R25SemanticControlCageV4Error("execution_wrapper_self_binding_mismatch")
    runtime_path, runtime_raw = _verified_row(
        "attempt03_accepted_runtime", bindings["attempt03_accepted_runtime"], ".py"
    )
    adapter_path, adapter_raw = _verified_row(
        "v3r3_afes_adapter", bindings["v3r3_afes_adapter"], ".py"
    )
    runtime = _private_module("attempt03_runtime", runtime_path, runtime_raw)
    adapter = _private_module("v3r3_adapter", adapter_path, adapter_raw)
    if not callable(getattr(adapter, "validate_afes_v3r3_pair_bundle", None)):
        raise R25SemanticControlCageV4Error("v3r3_adapter_symbol_missing")
    session = runtime._PrivateDependencySession()
    session.begin()
    receipt = session.load(
        "canonical_receipt_primitive", bindings["canonical_receipt_primitive"],
        ("encode_receipt_frame", "decode_receipt_frame"), runtime._RECEIPT_RECORD_SPEC,
    )
    control = session.load(
        "pure_control_cage_core", bindings["pure_control_cage_core"],
        (
            "Triangle", "classify_weighted_vertices", "validate_compact_afes_analysis_against_mesh",
            "similarity_from_region_centroids", "select_control_anchors_with_coverage",
            "map_control_anchors_to_target", "encode_mapping_records",
            "decode_and_validate_mapping_records", "alignment_receipt", "canonical_sha256",
        ),
        runtime._CORE_RECORD_SPEC,
    )
    observed: dict[str, dict[str, object]] = {}
    for label, row in sorted(bindings.items()):
        suffix = Path(str(row.get("path", ""))).suffix.lower() if isinstance(row, Mapping) else ""
        if suffix not in (".py", ".json", ".blend", ".mhw", ".md"):
            raise R25SemanticControlCageV4Error(f"binding_suffix_refused:{label}")
        path, raw = _verified_row(label, row, suffix)
        observed[label] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": len(raw), "sha256": _sha256(raw),
        }
    return runtime, adapter, session, receipt, control, observed


def _read_frame(stream: Any, receipt: Any) -> tuple[dict[str, Any], str, int, str]:
    header = bytearray()
    while len(header) < receipt.RECEIPT_HEADER_BYTES:
        block = stream.read(receipt.RECEIPT_HEADER_BYTES - len(header))
        if not block:
            raise R25SemanticControlCageV4Error("input_frame_header_truncated")
        header.extend(block)
    magic, version, payload_length, _ = receipt.RECEIPT_HEADER.unpack(bytes(header))
    if magic != receipt.RECEIPT_MAGIC or version != receipt.RECEIPT_VERSION:
        raise R25SemanticControlCageV4Error("input_frame_magic_or_version")
    if payload_length > receipt.MAX_RECEIPT_PAYLOAD_BYTES:
        raise R25SemanticControlCageV4Error("input_frame_payload_too_large")
    payload = bytearray()
    while len(payload) < payload_length:
        block = stream.read(payload_length - len(payload))
        if not block:
            raise R25SemanticControlCageV4Error("input_frame_payload_truncated")
        payload.extend(block)
    frame = bytes(header + payload)
    decoded = receipt.decode_receipt_frame(frame)
    return decoded.payload, decoded.frame_sha256, len(frame), decoded.payload_sha256


def _read_bundle(raw_handle: int, runtime: Any, receipt: Any):
    runtime._require_pipe(raw_handle, "lock_input")
    with runtime._adopt_pipe(raw_handle, os.O_RDONLY, "lock_input") as stream:
        frames = [_read_frame(stream, receipt) for _ in range(MAX_INPUT_FRAMES)]
        if stream.read(1) != b"":
            raise R25SemanticControlCageV4Error("input_pipe_contains_more_than_three_frames")
    return frames


class _ControlProxy:
    def __init__(self, base: Any, adapter: Any, details: Sequence[tuple[dict[str, Any], str, int, str]]) -> None:
        self._base = base
        self._adapter = adapter
        self._details = details

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    def validate_afes_pair_bundle(self, **values: Any):
        return self._adapter.validate_afes_v3r3_pair_bundle(
            **values,
            run_frame_bytes=(self._details[1][2], self._details[2][2]),
            run_payload_sha256s=(self._details[1][3], self._details[2][3]),
            legacy_control=self._base,
        )


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--lock-handle", required=True)
    parser.add_argument("--result-handle", required=True)
    values = parser.parse_args(argv)
    if HEX64.fullmatch(values.config_sha256 or "") is None:
        parser.error("config SHA-256 must be 64 lowercase hexadecimal characters")
    try:
        values.lock_handle = int(values.lock_handle, 10)
        values.result_handle = int(values.result_handle, 10)
    except ValueError as exc:
        parser.error(f"handles must be decimal integers: {exc}")
    if values.lock_handle <= 0 or values.result_handle <= 0 or values.lock_handle == values.result_handle:
        parser.error("handles must be distinct positive integers")
    return values


def main() -> int:
    values = _arguments()
    session = receipt = runtime = adapter = control = None
    try:
        config, raw = _read_config(values.config_sha256)
        runtime, adapter, session, receipt, control, observed = _verified_runtime(config)
        details = _read_bundle(values.lock_handle, runtime, receipt)
        proxy = _ControlProxy(control, adapter, details)
        runtime_config = dict(config)
        runtime_config["afes_pair_binding"] = config["afes_v3r3_pair_binding"]
        payload = runtime.extract_diagnostic(
            config_sha256=values.config_sha256, config=runtime_config, config_raw=raw,
            receipt=receipt, control=proxy, observed=observed,
            pair_payload=details[0][0], pair_frame_sha256=details[0][1],
            run_payloads=(details[1][0], details[2][0]),
            run_frame_sha256s=(details[1][1], details[2][1]),
        )
        payload["schema"] = "kira.r25.semantic_control_cage_diagnostic.v4"
        payload["status"] = "V3R3_BOUND_CONTROL_CAGE_DIAGNOSTIC_COMPUTED_NOT_A_BODY"
        payload["static_preparation_lineage"] = config["static_preparation_lineage"]
        payload.pop("payload_content_sha256", None)
        payload["payload_content_sha256"] = control.canonical_sha256(payload)
        runtime._write_result(values.result_handle, receipt, payload)
        return 0
    except Exception as exc:
        if receipt is not None and runtime is not None:
            try:
                runtime._write_result(values.result_handle, receipt, {
                    "schema": "kira.r25.semantic_control_cage_diagnostic.v4",
                    "status": "DIAGNOSTIC_FAILED_NO_CAGE_NO_CANDIDATE",
                    "failure_type": type(exc).__name__, "failure": str(exc),
                    "config_sha256": values.config_sha256,
                })
            except Exception:
                pass
        print(f"R25_SEMANTIC_CONTROL_CAGE_V4_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        if session is not None:
            session.close()
        receipt = runtime = adapter = control = None


if __name__ == "__main__":
    raise SystemExit(main())
