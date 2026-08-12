#!/usr/bin/env python3
"""Retained-byte orchestration body for the native R25 v3r3 launcher.

This file is not a launcher and cannot establish its own provenance.  The
pinned native PE launcher reads these bytes from its deny-write/delete handle,
verifies the retained manifest and audit, embeds Python, and executes these
exact bytes with an unimportable process-local broker.  Direct path execution
fails before any project file, output path, outcome, or child can be touched.
"""

from __future__ import annotations

import argparse
import builtins
import hashlib
import json
from pathlib import Path
import secrets
import struct
import sys
from types import ModuleType
from typing import Any, Mapping, Sequence
import unicodedata


_retained_sha256 = globals().pop("__KIRA_RETAINED_BOOTSTRAP_SHA256__", None)
_retained_label = globals().pop("__KIRA_RETAINED_BOOTSTRAP_LABEL__", None)
_native_marker = globals().pop("__KIRA_NATIVE_BROKER_V3R3__", None)
_synthetic_file = str(globals().get("__file__", ""))

if (
    _native_marker is not True
    or not isinstance(_retained_sha256, str)
    or len(_retained_sha256) != 64
    or any(character not in "0123456789abcdef" for character in _retained_sha256)
    or _retained_label != "trusted_bootstrap"
    or _synthetic_file != "<native-retained-bootstrap-v3r3>"
):
    print(
        "R25_AFES_LOCKED_PAIR_BOOTSTRAP_V3R3_REFUSED: native retained-byte launch required",
        file=sys.stderr,
    )
    raise SystemExit(2)


def _retained_native_main() -> int:
    import _kira_r25_afes_native_broker as broker

    class BootstrapError(RuntimeError):
        pass

    hex64 = set("0123456789abcdef")
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-contract-sha256", required=True)
    parser.add_argument("--accepted-audit-sha256", required=True)
    parser.add_argument("--retained-manifest-sha256", required=True)
    values = parser.parse_args()
    for label, value in (
        ("expected_contract_sha256", values.expected_contract_sha256),
        ("accepted_audit_sha256", values.accepted_audit_sha256),
        ("retained_manifest_sha256", values.retained_manifest_sha256),
    ):
        if len(value) != 64 or any(character not in hex64 for character in value):
            raise BootstrapError(f"{label}_must_be_lowercase_64_hex")

    broker.claim_once(
        values.retained_manifest_sha256,
        values.expected_contract_sha256,
        values.accepted_audit_sha256,
    )
    rows_raw = broker.locked_rows()
    if not isinstance(rows_raw, tuple) or not rows_raw:
        raise BootstrapError("native_retained_rows_missing")
    rows: dict[str, dict[str, object]] = {}
    path_to_label: dict[str, str] = {}
    retained_by_path: dict[str, bytes] = {}
    for raw in rows_raw:
        if not isinstance(raw, tuple) or len(raw) != 4:
            raise BootstrapError("native_retained_row_shape_drift")
        label, path, byte_count, sha256 = raw
        if (
            not isinstance(label, str) or not label or label in rows
            or not isinstance(path, str) or not path or path in path_to_label
            or type(byte_count) is not int or byte_count < 0
            or not isinstance(sha256, str) or len(sha256) != 64
        ):
            raise BootstrapError("native_retained_row_identity_drift")
        value = broker.locked_read(label)
        if not isinstance(value, bytes) or len(value) != byte_count or (
            hashlib.sha256(value).hexdigest() != sha256
        ):
            raise BootstrapError(f"native_retained_row_bytes_drift:{label}")
        rows[label] = {"path": path, "bytes": byte_count, "sha256": sha256}
        path_to_label[path] = label
        retained_by_path[path] = value

    bootstrap_row = rows.get("trusted_bootstrap")
    if (
        not isinstance(bootstrap_row, Mapping)
        or bootstrap_row.get("sha256") != _retained_sha256
    ):
        raise BootstrapError("native_bootstrap_retained_identity_drift")

    def retained_path_bytes(path: str) -> bytes:
        label = path_to_label.get(path)
        if label is None:
            raise BootstrapError(f"unretained_path_refused:{path}")
        return retained_by_path[path]

    contract_row = rows.get("execution_contract")
    audit_row = broker.audit_identity()
    manifest_row = broker.manifest_identity()
    if not isinstance(contract_row, Mapping) or not isinstance(audit_row, dict) or (
        not isinstance(manifest_row, dict)
    ):
        raise BootstrapError("native_seed_identity_missing")
    contract_bytes = broker.locked_read("execution_contract")
    audit_bytes = broker.audit_bytes()

    controller_row = rows.get("parent_controller")
    if not isinstance(controller_row, Mapping):
        raise BootstrapError("retained_controller_row_missing")
    controller_source = broker.locked_read("parent_controller")
    controller = ModuleType("_kira_r25_v3r3_pure_controller_retained")
    controller.__file__ = "<native-retained-controller-v3r3>"
    controller.__package__ = ""
    controller.__spec__ = None
    controller.__loader__ = None
    exec(
        compile(
            controller_source, "<native-retained-controller-v3r3>", "exec",
            dont_inherit=True,
        ),
        controller.__dict__, controller.__dict__,
    )
    names = (
        "_build_execution_plan", "_validate_child_payload", "_compare_pair",
        "_success_payload", "_failure_payload",
    )
    captured: dict[str, Any] = {}
    for name in names:
        value = controller.__dict__.pop(name, None)
        if not callable(value):
            raise BootstrapError(f"pure_controller_symbol_missing:{name}")
        captured[name] = value
    for name, value in list(controller.__dict__.items()):
        if callable(value):
            controller.__dict__.pop(name, None)
    if any(callable(value) for value in controller.__dict__.values()):
        raise BootstrapError("pure_controller_call_attribute_survived_capture")

    plan = captured["_build_execution_plan"](
        contract_bytes=contract_bytes,
        audit_bytes=audit_bytes,
        retained_by_path=retained_by_path,
        expected_contract_sha256=values.expected_contract_sha256,
        accepted_audit_sha256=values.accepted_audit_sha256,
        manifest_row=manifest_row,
    )

    contract = plan["contract"]
    v5 = plan["v5"]

    def read_exact(row: object, *, label: str = "bound_row") -> tuple[Path, bytes]:
        if not isinstance(row, Mapping) or set(row) != {"path", "bytes", "sha256"}:
            raise BootstrapError(f"invalid_private_graph_row:{label}")
        source = retained_path_bytes(str(row["path"]))
        if len(source) != row["bytes"] or hashlib.sha256(source).hexdigest() != row["sha256"]:
            raise BootstrapError(f"private_graph_row_drift:{label}")
        return Path(str(row["path"])), source

    loader_row = contract["bindings"]["afes_v5_private_loader"]
    _, loader_source = read_exact(loader_row, label="afes_v5_private_loader")
    real_import = builtins.__import__

    def guarded_import(
        name: str, globals: object = None, locals: object = None,
        fromlist: Sequence[str] = (), level: int = 0,
    ) -> object:
        if name == "tools" or name.startswith("tools.") or name == "dataclasses":
            raise BootstrapError(f"ambient_security_import_forbidden:{name}")
        return real_import(name, globals, locals, fromlist, level)

    private_loader = ModuleType("_kira_r25_v3r3_private_graph_loader")
    private_loader.__file__ = str(loader_row["path"])
    private_loader.__package__ = ""
    private_loader.__spec__ = None
    private_loader.__loader__ = None
    private_builtins = dict(vars(builtins))
    private_builtins["__import__"] = guarded_import
    private_loader.__dict__["__builtins__"] = private_builtins
    exec(
        compile(loader_source, str(loader_row["path"]), "exec", dont_inherit=True),
        private_loader.__dict__, private_loader.__dict__,
    )
    graph_loader = private_loader.__dict__.pop("load_private_dependency_graph", None)
    if not callable(graph_loader):
        raise BootstrapError("private_graph_loader_symbol_missing")
    graph_rows = {
        key: v5["bindings"][key] for key in (
            "attempt_01_topology_core_execution_dependency",
            "attempt_02_hardening_core_execution_dependency",
            "attempt_03_hardening_core_execution_dependency",
            "canonical_receipt_helper",
        )
    }
    graph = graph_loader(bindings=graph_rows, read_exact=read_exact)
    receipt = graph.get("canonical_receipt")
    attempt03 = graph.get("attempt03_core")
    if not isinstance(receipt, ModuleType) or not isinstance(attempt03, ModuleType):
        raise BootstrapError("private_graph_shape_drift")
    compact_validator = getattr(attempt03, "validate_compact_afes_analysis", None)
    if not callable(compact_validator):
        raise BootstrapError("compact_validator_missing")

    primary: BaseException | None = None
    cleanup_errors: list[str] = []
    committed = False
    output_root: str | None = None
    stage = "native_outcome_reservation"
    broker.reserve_outcome(plan["outcome_relative_path"])
    try:
        # The protected failure boundary begins on the first statement after
        # successful native reservation.  No path resolution or validation sits
        # between reserve_outcome() and this try.
        stage = "native_output_root"
        output_root = broker.create_output_root(plan["output_relative_path"])
        pair_nonce = secrets.token_hex(32)
        used_nonces: set[str] = set()
        decoded_runs: list[Any] = []
        inner_runs: list[Mapping[str, Any]] = []
        topology_runs: list[str] = []
        metadata: list[dict[str, Any]] = []
        stage = "native_children"
        for run_number in (1, 2):
            run_nonce = secrets.token_hex(32)
            if run_nonce == pair_nonce or run_nonce in used_nonces:
                raise BootstrapError("fresh_pair_and_run_nonce_collision")
            used_nonces.add(run_nonce)
            result = broker.run_child(plan, run_number, pair_nonce, run_nonce)
            if not isinstance(result, dict):
                raise BootstrapError(f"run_{run_number:02d}_native_result_shape")
            cleanup_errors.extend(str(item) for item in result.get("cleanup_errors", ()))
            if cleanup_errors:
                raise BootstrapError(f"run_{run_number:02d}_native_cleanup_failed")
            frame = result.get("frame")
            if not isinstance(frame, bytes):
                raise BootstrapError(f"run_{run_number:02d}_frame_missing")
            broker.write_evidence(f"run_{run_number:02d}_raw_frame.bin", frame)
            broker.write_evidence(
                f"run_{run_number:02d}_stdout.log", result.get("stdout", b"")
            )
            broker.write_evidence(
                f"run_{run_number:02d}_stderr.log", result.get("stderr", b"")
            )
            decoded = receipt.decode_receipt_frame(frame)
            inner, topology = captured["_validate_child_payload"](
                payload=decoded.payload,
                run_number=run_number,
                pair_session_nonce=pair_nonce,
                run_nonce=run_nonce,
                result_handle=result["result_handle"],
                child_pid=result["pid"],
                parent_pid=broker.broker_process_id(),
                plan=plan,
                compact_validator=compact_validator,
            )
            decoded_runs.append(decoded)
            inner_runs.append(inner)
            topology_runs.append(topology)
            row = {
                "run_number": run_number,
                "pair_session_nonce": pair_nonce,
                "run_nonce": run_nonce,
                "pid": result["pid"],
                "exit_code": result["exit_code"],
                "frame_bytes": len(frame),
                "frame_sha256": decoded.frame_sha256,
                "payload_sha256": decoded.payload_sha256,
                "inner_payload_sha256": hashlib.sha256(
                    receipt.canonical_json_bytes(dict(inner))
                ).hexdigest(),
                "topology_sha256": topology,
                "stdout_bytes": result["stdout_total_bytes"],
                "stdout_sha256": result["stdout_sha256"],
                "stderr_bytes": result["stderr_total_bytes"],
                "stderr_sha256": result["stderr_sha256"],
            }
            metadata.append(row)
            broker.write_evidence(
                f"run_{run_number:02d}_receipt.bin", frame
            )
        stage = "pure_pair_comparison"
        captured["_compare_pair"](
            inner_runs[0], topology_runs[0], inner_runs[1], topology_runs[1]
        )
        stage = "native_after_snapshot"
        snapshot = broker.after_snapshot()
        if not isinstance(snapshot, dict) or snapshot.get("unchanged") is not True:
            raise BootstrapError("native_retained_after_snapshot_changed")
        stage = "native_resource_quiescence"
        cleanup_errors.extend(str(item) for item in broker.quiesce_owned_resources())
        if cleanup_errors:
            raise BootstrapError("native_resource_quiescence_failed")
        summary = captured["_success_payload"](
            plan=plan, run_metadata=metadata,
            snapshot_sha256=snapshot["snapshot_sha256"],
        )
        stage = "native_outcome_commit"
        broker.commit_outcome(receipt.encode_receipt_frame(summary))
        committed = True
        return 0
    except BaseException as exc:
        primary = exc
        try:
            cleanup_errors.extend(str(item) for item in broker.quiesce_owned_resources())
        except BaseException as cleanup_exc:
            cleanup_errors.append(
                f"native_quiesce_exception:{type(cleanup_exc).__name__}:{cleanup_exc}"
            )
        if not committed:
            failure = captured["_failure_payload"](
                contract_sha256=values.expected_contract_sha256,
                stage=stage,
                primary=primary,
                cleanup_errors=cleanup_errors,
            )
            broker.commit_failure_outcome(receipt.encode_receipt_frame(failure))
            committed = True
        raise
    finally:
        # Native finish never retries or creates a second outcome.  It reports
        # final handle-close state to the executable's exit status.
        broker.finish()


try:
    _retained_exit_code = _retained_native_main()
finally:
    globals().pop("_retained_native_main", None)
    globals().pop("_retained_sha256", None)
    globals().pop("_retained_label", None)
    globals().pop("_native_marker", None)

if _retained_exit_code != 0:
    raise RuntimeError("native_retained_bootstrap_nonzero_result")
