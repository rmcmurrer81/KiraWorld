#!/usr/bin/env python3
"""Zero-import retained bootstrap for native R25 AFES locked-pair v3r6.

The native launcher injects one private broker object, an exact seed identity,
and five already-compiled pure controller functions.  This source has no
compile/exec/import/module-loader/path/process/nonce-generation authority.
"""

try:
    _broker = __KIRA_NATIVE_BROKER_OBJECT_V3R6__
    _seed = __KIRA_NATIVE_SEED_IDENTITY_V3R6__
    _controller = __KIRA_NATIVE_CONTROLLER_CALLS_V3R6__
    _retained_sha256 = __KIRA_RETAINED_BOOTSTRAP_SHA256__
    _retained_label = __KIRA_RETAINED_BOOTSTRAP_LABEL__
except NameError:
    raise SystemExit(2)

if (
    type(_seed) is not dict
    or set(_seed) != {
        "marker", "expected_contract_sha256", "accepted_audit_sha256",
        "retained_manifest_sha256",
    }
    or _seed.get("marker") != "KIRA_R25_AFES_NATIVE_BROKER_V3R6"
    or type(_controller) is not dict
    or set(_controller) != {
        "_build_execution_plan", "_validate_child_payload", "_compare_pair",
        "_success_payload", "_failure_payload",
    }
    or not all(callable(value) for value in _controller.values())
    or _retained_label != "trusted_bootstrap"
    or not isinstance(_retained_sha256, str)
    or len(_retained_sha256) != 64
):
    raise SystemExit(2)


class BootstrapError(RuntimeError):
    pass


def _retained_native_main():
    expected_contract_sha256 = _seed["expected_contract_sha256"]
    accepted_audit_sha256 = _seed["accepted_audit_sha256"]
    retained_manifest_sha256 = _seed["retained_manifest_sha256"]
    _broker.claim_once(
        retained_manifest_sha256,
        expected_contract_sha256,
        accepted_audit_sha256,
    )
    rows_raw = _broker.locked_rows()
    if not isinstance(rows_raw, tuple) or not rows_raw:
        raise BootstrapError("native_retained_rows_missing")
    rows = {}
    path_to_label = {}
    retained_by_path = {}
    for raw in rows_raw:
        if not isinstance(raw, tuple) or len(raw) != 4:
            raise BootstrapError("native_retained_row_shape_drift")
        label, path, byte_count, sha256 = raw
        if (
            not isinstance(label, str) or not label or label in rows
            or not isinstance(path, str) or not path or path in path_to_label
            or type(byte_count) is not int or byte_count < 0
            or not _broker.is_lower_hex64(sha256)
        ):
            raise BootstrapError("native_retained_row_identity_drift")
        value = _broker.locked_read(label)
        if (
            not isinstance(value, bytes) or len(value) != byte_count
            or _broker.sha256_hex(value) != sha256
        ):
            raise BootstrapError("native_retained_row_bytes_drift:" + label)
        row = {"path": path, "bytes": byte_count, "sha256": sha256}
        rows[label] = row
        path_to_label[path] = label
        retained_by_path[path] = value

    bootstrap_row = rows.get("trusted_bootstrap")
    if not isinstance(bootstrap_row, dict) or bootstrap_row.get(
        "sha256"
    ) != _retained_sha256:
        raise BootstrapError("native_bootstrap_retained_identity_drift")
    contract_row = rows.get("execution_contract")
    audit_row = _broker.audit_identity()
    manifest_row = _broker.manifest_identity()
    if (
        not isinstance(contract_row, dict)
        or not isinstance(audit_row, dict)
        or not isinstance(manifest_row, dict)
    ):
        raise BootstrapError("native_seed_identity_missing")

    plan = _controller["_build_execution_plan"](
        contract_bytes=_broker.locked_read("execution_contract"),
        audit_bytes=_broker.audit_bytes(),
        retained_by_path=retained_by_path,
        expected_contract_sha256=expected_contract_sha256,
        accepted_audit_sha256=accepted_audit_sha256,
        manifest_row=manifest_row,
    )
    primary = None
    cleanup_errors = []
    committed = False
    output_root = None
    stage = "native_outcome_reservation"
    _broker.reserve_outcome(plan["outcome_relative_path"])
    try:
        stage = "native_output_root"
        output_root = _broker.create_output_root(plan["output_relative_path"])
        nonce_bundle = _broker.claim_nonce_bundle()
        if (
            not isinstance(nonce_bundle, tuple) or len(nonce_bundle) != 3
            or any(not _broker.is_lower_hex64(item) for item in nonce_bundle)
            or len(set(nonce_bundle)) != 3
        ):
            raise BootstrapError("native_nonce_bundle_invalid")
        pair_nonce, run_nonce_1, run_nonce_2 = nonce_bundle
        run_nonces = (run_nonce_1, run_nonce_2)
        inner_runs = []
        topology_runs = []
        metadata = []
        stage = "native_children"
        for run_number in (1, 2):
            result = _broker.run_child(plan, run_number)
            if not isinstance(result, dict):
                raise BootstrapError("native_child_result_shape")
            if (
                result.get("pair_session_nonce") != pair_nonce
                or result.get("run_nonce") != run_nonces[run_number - 1]
            ):
                raise BootstrapError("native_child_nonce_identity_drift")
            cleanup_errors.extend(str(item) for item in result.get(
                "cleanup_errors", ()
            ))
            if cleanup_errors:
                raise BootstrapError("native_child_cleanup_failed")
            frame = result.get("frame")
            if not isinstance(frame, bytes):
                raise BootstrapError("native_child_frame_missing")
            prefix = "run_0" + str(run_number)
            _broker.write_evidence(prefix + "_raw_frame.bin", frame)
            _broker.write_evidence(prefix + "_stdout.log", result.get("stdout", b""))
            _broker.write_evidence(prefix + "_stderr.log", result.get("stderr", b""))
            decoded = _broker.decode_receipt_frame(frame)
            if type(decoded) is not dict or set(decoded) != {
                "payload", "payload_sha256", "frame_sha256",
            }:
                raise BootstrapError("native_decoded_receipt_shape_drift")
            inner, topology = _controller["_validate_child_payload"](
                payload=decoded["payload"],
                run_number=run_number,
                pair_session_nonce=pair_nonce,
                run_nonce=run_nonces[run_number - 1],
                result_pipe_name=result["result_pipe_name"],
                child_pid=result["pid"],
                parent_pid=_broker.broker_process_id(),
                plan=plan,
            )
            inner_runs.append(inner)
            topology_runs.append(topology)
            row = {
                "run_number": run_number,
                "pair_session_nonce": pair_nonce,
                "run_nonce": run_nonces[run_number - 1],
                "pid": result["pid"],
                "exit_code": result["exit_code"],
                "frame_bytes": len(frame),
                "frame_sha256": decoded["frame_sha256"],
                "payload_sha256": decoded["payload_sha256"],
                "inner_payload_sha256": _broker.canonical_json_sha256(dict(inner)),
                "topology_sha256": topology,
                "stdout_bytes": result["stdout_total_bytes"],
                "stdout_sha256": result["stdout_sha256"],
                "stderr_bytes": result["stderr_total_bytes"],
                "stderr_sha256": result["stderr_sha256"],
            }
            metadata.append(row)
            _broker.write_evidence(prefix + "_receipt.bin", frame)
        stage = "pure_pair_comparison"
        _controller["_compare_pair"](
            inner_runs[0], topology_runs[0], inner_runs[1], topology_runs[1]
        )
        stage = "native_after_snapshot"
        snapshot = _broker.after_snapshot()
        if not isinstance(snapshot, dict) or snapshot.get("unchanged") is not True:
            raise BootstrapError("native_retained_after_snapshot_changed")
        stage = "native_resource_quiescence"
        cleanup_errors.extend(str(item) for item in _broker.quiesce_owned_resources())
        if cleanup_errors:
            raise BootstrapError("native_resource_quiescence_failed")
        summary = _controller["_success_payload"](
            plan=plan, run_metadata=metadata,
            snapshot_sha256=snapshot["snapshot_sha256"],
        )
        stage = "native_outcome_commit"
        _broker.commit_outcome(_broker.encode_receipt_frame(summary))
        committed = True
        return 0
    except BaseException as exc:
        primary = exc
        try:
            cleanup_errors.extend(
                str(item) for item in _broker.quiesce_owned_resources()
            )
        except BaseException as cleanup_exc:
            cleanup_errors.append(
                "native_quiesce_exception:" + type(cleanup_exc).__name__
                + ":" + str(cleanup_exc)
            )
        if not committed:
            failure = _controller["_failure_payload"](
                contract_sha256=expected_contract_sha256,
                stage=stage,
                primary=primary,
                cleanup_errors=cleanup_errors,
            )
            _broker.commit_failure_outcome(failure)
            committed = True
        raise
    finally:
        _broker.finish()


_retained_exit_code = _retained_native_main()
if _retained_exit_code != 0:
    raise RuntimeError("native_retained_bootstrap_nonzero_result")

