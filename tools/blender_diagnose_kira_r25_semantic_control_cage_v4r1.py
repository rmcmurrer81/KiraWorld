#!/usr/bin/env python3
from __future__ import annotations

"""Static-only Attempt-04r1 wrapper design with mandatory pipe capability.

The checked-in config is unsealed and fails before runtime loading.  A future
append-only sealed successor must additionally provide a one-read inherited
controller capability pipe authenticated to the parent controller process.
"""

import argparse
import builtins
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
import types

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE_PATH = (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_semantic_control_cage_diagnostic_v4r1.json"
)
SCHEMA = "kira.avatar.r25.semantic_control_cage_diagnostic.v4r1"
ATTEMPT_ID = "attempt_04r1_static_unsealed"
PREPARATION_STATUS = "STATIC_PREPARATION_ONLY_ATTEMPT04_REPAIRS_UNSEALED_EXECUTION_FORBIDDEN"
SEALED_STATUS = "SEALED_ONLY_IN_NEW_APPEND_ONLY_SUCCESSOR_AFTER_ACCEPTED_04R1_AUDIT"
CAPABILITY_SCHEMA = "kira.avatar.r25.semantic_control_cage_execution_capability.v4r1"
CAPABILITY_STATUS = "INDEPENDENT_AUDIT_ACCEPTED_ONE_RUN_CAPABILITY"
CAPABILITY_KEYS = {
    "schema", "status", "config_sha256", "accepted_audit_sha256",
    "controller_binding", "wrapper_binding", "controller_process_id",
    "intended_child_process_id", "one_run_nonce", "handles", "input_frames",
    "single_read_nonreusable", "truth_boundary",
}
CAPABILITY_TRUTH = [
    "CREATED_ONLY_AFTER_EXACT_ACCEPTED_AUDIT_PARSE",
    "ONE_INHERITED_PIPE_ONE_CHILD_ONE_READ",
    "BOUND_TO_CONFIG_WRAPPER_CONTROLLER_AND_THREE_INPUT_FRAMES",
    "NO_BODY_OR_RUNTIME_AUTHORITY",
]
MAX_INPUT_FRAMES = 3
FILE_TYPE_PIPE = 3


class R25SemanticControlCageV4R1Error(RuntimeError):
    pass


def _sha256(value):
    return hashlib.sha256(value).hexdigest()


def _hex64(value):
    if type(value) is not str or len(value) != 64:
        return False
    for character in value:
        if not ("0" <= character <= "9" or "a" <= character <= "f"):
            return False
    return True


def _project_file(relative, suffix=None):
    if type(relative) is not str or not relative:
        raise R25SemanticControlCageV4R1Error("project_path_not_text")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise R25SemanticControlCageV4R1Error("unsafe_project_relative_path")
    lexical = PROJECT_ROOT
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise R25SemanticControlCageV4R1Error("symlink_binding_refused")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(PROJECT_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise R25SemanticControlCageV4R1Error("binding_escaped_project_root") from exc
    if not resolved.is_file() or (suffix and resolved.suffix.lower() != suffix):
        raise R25SemanticControlCageV4R1Error("binding_file_type_mismatch")
    return resolved


def _verified_row(label, row, suffix=None):
    if type(row) is not dict or not {"path", "bytes", "sha256"}.issubset(row):
        raise R25SemanticControlCageV4R1Error("binding_row_invalid:" + label)
    path = _project_file(row["path"], suffix)
    raw = path.read_bytes()
    if len(raw) != row["bytes"] or _sha256(raw) != row["sha256"]:
        raise R25SemanticControlCageV4R1Error("binding_drift:" + label)
    return path, raw


def _read_config(expected_sha256):
    if not _hex64(expected_sha256):
        raise R25SemanticControlCageV4R1Error("expected_config_sha256_invalid")
    raw = _project_file(CONFIG_RELATIVE_PATH, ".json").read_bytes()
    if _sha256(raw) != expected_sha256:
        raise R25SemanticControlCageV4R1Error("config_sha256_mismatch")
    try:
        config = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise R25SemanticControlCageV4R1Error("config_invalid_json") from exc
    if type(config) is not dict or config.get("schema") != SCHEMA or config.get("attempt_id") != ATTEMPT_ID:
        raise R25SemanticControlCageV4R1Error("config_identity_drift")
    if config.get("status") != SEALED_STATUS:
        if config.get("status") == PREPARATION_STATUS:
            raise R25SemanticControlCageV4R1Error("v4r1_static_preparation_is_not_execution_authority")
        raise R25SemanticControlCageV4R1Error("config_status_drift")
    pair = config.get("afes_v3r3_pair_binding")
    if type(pair) is not dict or pair.get("seal_status") != "SEALED_FINAL_INDEPENDENTLY_ACCEPTED_V3R3_PAIR":
        raise R25SemanticControlCageV4R1Error("v3r3_pair_not_sealed")
    if pair.get("required_final_placeholders") or pair.get("expected_pair_and_analysis") is None:
        raise R25SemanticControlCageV4R1Error("v3r3_pair_placeholders_remain")
    audit = config.get("future_independent_audit_gate")
    if type(audit) is not dict or not _hex64(audit.get("accepted_audit_sha256")):
        raise R25SemanticControlCageV4R1Error("accepted_04r1_audit_not_bound")
    return config, raw


def _ambient_module(label, path, raw):
    name = "_kira_private_semantic_v4r1_" + label + "_" + _sha256(raw)[:16]
    if name in sys.modules:
        raise R25SemanticControlCageV4R1Error("private_namespace_preexists:" + label)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    exec(compile(raw, str(path), "exec"), module.__dict__)
    if name in sys.modules:
        raise R25SemanticControlCageV4R1Error("private_module_registered:" + label)
    return module


def _deny_adapter_import(*_args, **_kwargs):
    raise R25SemanticControlCageV4R1Error("v4r1_adapter_import_forbidden")


def _dependency_free_adapter(path, raw):
    name = "_kira_private_semantic_v4r1_adapter_" + _sha256(raw)[:16]
    if name in sys.modules:
        raise R25SemanticControlCageV4R1Error("private_adapter_namespace_preexists")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    copied_builtins = dict(vars(builtins))
    copied_builtins["__import__"] = _deny_adapter_import
    module.__dict__["__builtins__"] = copied_builtins
    exec(compile(raw, str(path), "exec"), module.__dict__)
    if name in sys.modules:
        raise R25SemanticControlCageV4R1Error("private_adapter_registered")
    return module


def _verified_runtime(config):
    bindings = config.get("bindings")
    required = {
        "execution_wrapper", "static_controller", "attempt03_accepted_runtime",
        "v3r3_afes_adapter", "accepted_afes_v5_config", "accepted_afes_v5_extractor",
        "canonical_receipt_primitive", "pure_control_cage_core",
        "qualified_foundation_blend", "r19_visual_target_blend",
        "r20_exact_rejected_target_region", "makehuman_default_weights",
    }
    if type(bindings) is not dict or not required.issubset(bindings):
        raise R25SemanticControlCageV4R1Error("required_binding_missing")
    wrapper_path, _ = _verified_row("execution_wrapper", bindings["execution_wrapper"], ".py")
    if wrapper_path != Path(__file__).resolve(strict=True):
        raise R25SemanticControlCageV4R1Error("wrapper_self_binding_mismatch")
    runtime_path, runtime_raw = _verified_row(
        "attempt03_accepted_runtime", bindings["attempt03_accepted_runtime"], ".py"
    )
    adapter_path, adapter_raw = _verified_row(
        "v3r3_afes_adapter", bindings["v3r3_afes_adapter"], ".py"
    )
    runtime = _ambient_module("attempt03_runtime", runtime_path, runtime_raw)
    adapter = _dependency_free_adapter(adapter_path, adapter_raw)
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
        ), runtime._CORE_RECORD_SPEC,
    )
    observed = {}
    for label, row in sorted(bindings.items()):
        suffix = Path(str(row.get("path", ""))).suffix.lower() if type(row) is dict else ""
        if suffix not in (".py", ".json", ".blend", ".mhw", ".md"):
            raise R25SemanticControlCageV4R1Error("binding_suffix_refused:" + label)
        path, raw = _verified_row(label, row, suffix)
        observed[label] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": len(raw), "sha256": _sha256(raw),
        }
    return runtime, adapter, session, receipt, control, observed


def _read_frame(stream, receipt):
    header = bytearray()
    while len(header) < receipt.RECEIPT_HEADER_BYTES:
        block = stream.read(receipt.RECEIPT_HEADER_BYTES - len(header))
        if not block:
            raise R25SemanticControlCageV4R1Error("frame_header_truncated")
        header.extend(block)
    magic, version, payload_length, _ = receipt.RECEIPT_HEADER.unpack(bytes(header))
    if magic != receipt.RECEIPT_MAGIC or version != receipt.RECEIPT_VERSION:
        raise R25SemanticControlCageV4R1Error("frame_magic_or_version_invalid")
    if payload_length > receipt.MAX_RECEIPT_PAYLOAD_BYTES:
        raise R25SemanticControlCageV4R1Error("frame_payload_too_large")
    payload = bytearray()
    while len(payload) < payload_length:
        block = stream.read(payload_length - len(payload))
        if not block:
            raise R25SemanticControlCageV4R1Error("frame_payload_truncated")
        payload.extend(block)
    frame = bytes(header + payload)
    decoded = receipt.decode_receipt_frame(frame)
    return decoded.payload, decoded.frame_sha256, len(frame), decoded.payload_sha256


def _pipe_server_pid(raw_handle):
    if os.name != "nt" or type(raw_handle) is not int or raw_handle <= 0:
        raise R25SemanticControlCageV4R1Error("capability_handle_invalid_or_non_windows")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetFileType.argtypes = [ctypes.c_void_p]
    kernel32.GetFileType.restype = ctypes.c_uint32
    if int(kernel32.GetFileType(ctypes.c_void_p(raw_handle))) != FILE_TYPE_PIPE:
        raise R25SemanticControlCageV4R1Error("capability_handle_not_pipe")
    server_pid = ctypes.c_uint32(0)
    function = kernel32.GetNamedPipeServerProcessId
    function.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    function.restype = ctypes.c_int
    if not function(ctypes.c_void_p(raw_handle), ctypes.byref(server_pid)):
        raise R25SemanticControlCageV4R1Error("capability_pipe_server_pid_unavailable")
    return int(server_pid.value)


def _expected_capability_inputs(expected):
    return [
        {"role": "pair_acceptance", "frame_sha256": expected["pair_acceptance_frame_sha256"]},
        {"role": "run_01", "frame_sha256": expected["run_01_frame_sha256"]},
        {"role": "run_02", "frame_sha256": expected["run_02_frame_sha256"]},
    ]


def _read_controller_capability(raw_handle, lock_handle, result_handle, config_sha256, config, runtime, receipt):
    parent_pid = os.getppid()
    if _pipe_server_pid(raw_handle) != parent_pid:
        raise R25SemanticControlCageV4R1Error("capability_pipe_not_owned_by_parent_controller")
    runtime._require_pipe(raw_handle, "controller_capability")
    with runtime._adopt_pipe(raw_handle, os.O_RDONLY, "controller_capability") as stream:
        payload, _, _, _ = _read_frame(stream, receipt)
        if stream.read(1) != b"":
            raise R25SemanticControlCageV4R1Error("capability_pipe_contains_more_than_one_frame")
    if type(payload) is not dict or set(payload) != CAPABILITY_KEYS:
        raise R25SemanticControlCageV4R1Error("capability_payload_shape_drift")
    if payload["schema"] != CAPABILITY_SCHEMA or payload["status"] != CAPABILITY_STATUS:
        raise R25SemanticControlCageV4R1Error("capability_literal_identity_mismatch")
    if payload["config_sha256"] != config_sha256:
        raise R25SemanticControlCageV4R1Error("capability_config_mismatch")
    audit_sha = config["future_independent_audit_gate"]["accepted_audit_sha256"]
    if payload["accepted_audit_sha256"] != audit_sha:
        raise R25SemanticControlCageV4R1Error("capability_audit_mismatch")
    bindings = config["bindings"]
    if payload["controller_binding"] != bindings["static_controller"] or payload["wrapper_binding"] != bindings["execution_wrapper"]:
        raise R25SemanticControlCageV4R1Error("capability_code_binding_mismatch")
    if payload["controller_process_id"] != parent_pid or payload["intended_child_process_id"] != os.getpid():
        raise R25SemanticControlCageV4R1Error("capability_process_binding_mismatch")
    if not _hex64(payload["one_run_nonce"]):
        raise R25SemanticControlCageV4R1Error("capability_nonce_invalid")
    if payload["handles"] != {
        "capability": raw_handle, "lock_input": lock_handle, "result_output": result_handle,
    }:
        raise R25SemanticControlCageV4R1Error("capability_handle_binding_mismatch")
    expected = config["afes_v3r3_pair_binding"]["expected_pair_and_analysis"]
    if payload["input_frames"] != _expected_capability_inputs(expected):
        raise R25SemanticControlCageV4R1Error("capability_input_frame_binding_mismatch")
    if payload["single_read_nonreusable"] is not True or payload["truth_boundary"] != CAPABILITY_TRUTH:
        raise R25SemanticControlCageV4R1Error("capability_truth_boundary_mismatch")
    return payload


def _read_bundle(raw_handle, runtime, receipt):
    runtime._require_pipe(raw_handle, "lock_input")
    with runtime._adopt_pipe(raw_handle, os.O_RDONLY, "lock_input") as stream:
        frames = [_read_frame(stream, receipt) for _ in range(MAX_INPUT_FRAMES)]
        if stream.read(1) != b"":
            raise R25SemanticControlCageV4R1Error("input_pipe_contains_more_than_three_frames")
    return frames


class _ControlProxy:
    def __init__(self, base, adapter, details, config):
        self._base = base
        self._adapter = adapter
        self._details = details
        self._config = config

    def __getattr__(self, name):
        return getattr(self._base, name)

    def validate_afes_pair_bundle(self, **values):
        bindings = self._config["bindings"]
        return self._adapter.validate_afes_v3r3_pair_bundle(
            **values,
            run_frame_bytes=(self._details[1][2], self._details[2][2]),
            run_payload_sha256s=(self._details[1][3], self._details[2][3]),
            legacy_control=self._base,
            trusted_afes_v5_config={key: bindings["accepted_afes_v5_config"][key] for key in ("path", "bytes", "sha256")},
            trusted_afes_v5_extractor={key: bindings["accepted_afes_v5_extractor"][key] for key in ("path", "bytes", "sha256")},
        )


def _arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--capability-handle", required=True)
    parser.add_argument("--lock-handle", required=True)
    parser.add_argument("--result-handle", required=True)
    values = parser.parse_args(argv)
    if not _hex64(values.config_sha256):
        parser.error("config SHA-256 must be 64 lowercase hexadecimal characters")
    try:
        values.capability_handle = int(values.capability_handle, 10)
        values.lock_handle = int(values.lock_handle, 10)
        values.result_handle = int(values.result_handle, 10)
    except ValueError as exc:
        parser.error("handles must be decimal integers: " + str(exc))
    handles = (values.capability_handle, values.lock_handle, values.result_handle)
    if min(handles) <= 0 or len(set(handles)) != 3:
        parser.error("capability, lock, and result handles must be distinct positive integers")
    return values


def main():
    values = _arguments()
    session = receipt = runtime = adapter = control = None
    try:
        config, raw = _read_config(values.config_sha256)
        runtime, adapter, session, receipt, control, observed = _verified_runtime(config)
        _read_controller_capability(
            values.capability_handle, values.lock_handle, values.result_handle,
            values.config_sha256, config, runtime, receipt,
        )
        details = _read_bundle(values.lock_handle, runtime, receipt)
        proxy = _ControlProxy(control, adapter, details, config)
        runtime_config = dict(config)
        runtime_config["afes_pair_binding"] = config["afes_v3r3_pair_binding"]
        payload = runtime.extract_diagnostic(
            config_sha256=values.config_sha256, config=runtime_config, config_raw=raw,
            receipt=receipt, control=proxy, observed=observed,
            pair_payload=details[0][0], pair_frame_sha256=details[0][1],
            run_payloads=(details[1][0], details[2][0]),
            run_frame_sha256s=(details[1][1], details[2][1]),
        )
        payload["schema"] = "kira.r25.semantic_control_cage_diagnostic.v4r1"
        payload["status"] = "V3R3_BOUND_CONTROL_CAGE_DIAGNOSTIC_COMPUTED_NOT_A_BODY"
        payload.pop("payload_content_sha256", None)
        payload["payload_content_sha256"] = control.canonical_sha256(payload)
        runtime._write_result(values.result_handle, receipt, payload)
        return 0
    except Exception as exc:
        if receipt is not None and runtime is not None:
            try:
                runtime._write_result(values.result_handle, receipt, {
                    "schema": "kira.r25.semantic_control_cage_diagnostic.v4r1",
                    "status": "DIAGNOSTIC_FAILED_NO_CAGE_NO_CANDIDATE",
                    "failure_type": type(exc).__name__, "failure": str(exc),
                    "config_sha256": values.config_sha256,
                })
            except Exception:
                pass
        print("R25_SEMANTIC_CONTROL_CAGE_V4R1_FAILED: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        return 1
    finally:
        if session is not None:
            session.close()
        receipt = runtime = adapter = control = None


if __name__ == "__main__":
    raise SystemExit(main())
