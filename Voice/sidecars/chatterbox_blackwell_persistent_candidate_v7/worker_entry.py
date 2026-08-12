#!/usr/bin/env python3
"""JSONL entry point for the inactive v7 persistent child.

Only a nonce-bound static fixture exists in this revision.  With no explicit
static fixture switch the process exits fail-closed because no reviewed live
adapter exists.  This module never imports Torch, Chatterbox, or Ollama.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from typing import Any

from Core.blackwell_v7_process_boundary import (
    PROTOCOL,
    current_process_identity,
    process_identity_digest,
    strict_finite_json_loads,
)
from Testing.blackwell_v7_static_fixture_backend import StaticV7Backend
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v7.persistent_worker import (
    PersistentWorkerV7,
    load_canonical_config,
)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _write(value: Any, maximum_bytes: int) -> None:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    if len(payload) > maximum_bytes:
        raise RuntimeError("static fixture response exceeded maximum bytes")
    sys.stdout.buffer.write(payload + b"\n")
    sys.stdout.buffer.flush()


def _response(
    request: Any,
    worker_instance_id: str,
    identity_digest: str,
    ok: bool,
    value=None,
    exc=None,
):
    request_id = request.get("request_id") if isinstance(request, dict) else None
    operation = request.get("operation") if isinstance(request, dict) else None
    return {
        "protocol": PROTOCOL,
        "request_id": request_id,
        "operation": operation,
        "ok": ok,
        "value": value if ok else None,
        "error_type": None if ok else type(exc).__name__,
        "error": None if ok else str(exc),
        "worker_instance_id": worker_instance_id,
        "worker_pid": os.getpid(),
        "process_identity_digest": identity_digest,
    }


def _write_deliberately_nonfinite_response(
    request: dict[str, Any], worker_instance_id: str, identity_digest: str
) -> None:
    """Static hostile fixture: emit one otherwise exact response containing raw NaN."""
    value = _response(
        request,
        worker_instance_id,
        identity_digest,
        True,
        value={"deliberate_nonfinite": 0},
    )
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    marker = b'"deliberate_nonfinite":0'
    if payload.count(marker) != 1:
        raise RuntimeError("could not construct nonfinite hostile fixture")
    sys.stdout.buffer.write(payload.replace(marker, b'"deliberate_nonfinite":NaN') + b"\n")
    sys.stdout.buffer.flush()


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--static-fixture", action="store_true")
    parser.add_argument("--nonce", default="")
    args = parser.parse_args()
    if not args.static_fixture or not _is_sha256(args.nonce):
        sys.stderr.write("Blackwell v7 has no reviewed live adapter; refusing startup.\n")
        return 78
    if os.environ.get("KIRA_V7_STATIC_TEST_NONCE") != args.nonce:
        sys.stderr.write("Blackwell v7 static fixture nonce mismatch.\n")
        return 77
    config = load_canonical_config()
    maximum_request = int(config["ipc_bounds"]["maximum_request_bytes"])
    maximum_response = int(config["ipc_bounds"]["maximum_response_bytes"])
    lease = hashlib.sha256(f"v7-static-lease:{args.nonce}".encode()).hexdigest()
    instance = hashlib.sha256(
        f"v7-worker:{os.getpid()}:{time.monotonic_ns()}:{args.nonce}".encode()
    ).hexdigest()
    backend = StaticV7Backend(now=time.monotonic, worker_pid=os.getpid(), lease_id=lease)
    engine = PersistentWorkerV7(
        backend=backend,
        serialization_lease_id=lease,
        worker_instance_id=instance,
        worker_pid=os.getpid(),
        now=time.monotonic,
        allow_static_test=True,
    )
    descendants: list[subprocess.Popen[Any]] = []
    startup_descendant_pid: int | None = None
    if os.environ.get("KIRA_V7_STATIC_PRE_READY_DESCENDANT") == "1":
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(3600)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
        descendants.append(child)
        startup_descendant_pid = child.pid
    identity = current_process_identity()
    identity_digest = process_identity_digest(identity)
    _write(
        {
            "event": "ready",
            "protocol": PROTOCOL,
            "pid": os.getpid(),
            "worker_instance_id": instance,
            "static_fixture": True,
            "creation_token_digest": hashlib.sha256(args.nonce.encode("utf-8")).hexdigest(),
            "process_identity": identity,
            "process_identity_digest": identity_digest,
            "startup_descendant_pid": startup_descendant_pid,
        },
        maximum_response,
    )
    try:
        while True:
            line = sys.stdin.buffer.readline(maximum_request + 2)
            if not line:
                break
            request: dict[str, Any] = {}
            try:
                if len(line) > maximum_request + 1 or not line.endswith(b"\n"):
                    raise RuntimeError("request exceeded JSONL bound")
                request = strict_finite_json_loads(line)
                keys = {
                    "protocol",
                    "request_id",
                    "operation",
                    "payload",
                    "worker_instance_id",
                    "process_identity_digest",
                }
                if (
                    not isinstance(request, dict)
                    or set(request) != keys
                    or request["protocol"] != PROTOCOL
                    or not _is_sha256(request["request_id"])
                    or not isinstance(request["operation"], str)
                    or not isinstance(request["payload"], dict)
                    or request["worker_instance_id"] != instance
                    or request["process_identity_digest"] != identity_digest
                ):
                    raise RuntimeError("request identity/schema mismatch")
                operation = request["operation"]
                if operation == "fixture_echo":
                    value = dict(request["payload"])
                elif operation == "fixture_emit_nonfinite":
                    _write_deliberately_nonfinite_response(
                        request, instance, identity_digest
                    )
                    continue
                elif operation == "fixture_stop_reading":
                    _write(
                        _response(
                            request,
                            instance,
                            identity_digest,
                            True,
                            value={"reader_stopped": True},
                        ),
                        maximum_response,
                    )
                    time.sleep(3600)
                    continue
                elif operation == "fixture_hang":
                    time.sleep(3600)
                    value = {"unexpected": "hang returned"}
                elif operation == "fixture_spawn_descendant":
                    child = subprocess.Popen(
                        [sys.executable, "-c", "import time; time.sleep(3600)"],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        shell=False,
                    )
                    descendants.append(child)
                    value = {"descendant_pid": child.pid}
                elif operation == "fixture_swap_model":
                    from Testing.blackwell_v7_static_fixture_backend import StaticModel

                    old_id = id(engine.model)
                    engine.model = StaticModel()
                    value = {"old_id": old_id, "new_id": id(engine.model)}
                elif operation == "fixture_set_mode":
                    if set(request["payload"]) != {"name", "value"}:
                        raise RuntimeError("fixture mode schema mismatch")
                    name = request["payload"]["name"]
                    if name not in {
                        "resource_mode",
                        "qwen_race_phase",
                        "qwen_race_mode",
                        "stream_advance_per_chunk",
                        "artifact_mode",
                        "cuda_mode",
                        "qwen_unload_success",
                        "release_success",
                    }:
                        raise RuntimeError("unsupported fixture mode")
                    setattr(backend, name, request["payload"]["value"])
                    value = {"set": True, "name": name}
                else:
                    value = engine.dispatch(operation, request["payload"])
                _write(
                    _response(
                        request, instance, identity_digest, True, value=value
                    ),
                    maximum_response,
                )
                if operation == "shutdown":
                    break
            except Exception as exc:
                _write(
                    _response(
                        request, instance, identity_digest, False, exc=exc
                    ),
                    maximum_response,
                )
    finally:
        try:
            engine.cleanup({"reason": "worker_entry_exit"})
        except Exception:
            pass
        for child in descendants:
            try:
                child.kill()
            except OSError:
                pass
        backend.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
