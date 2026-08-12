#!/usr/bin/env python3
"""JSONL entry point for the inactive v6 persistent child.

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

from Core.blackwell_v6_process_boundary import PROTOCOL
from Testing.blackwell_v6_static_fixture_backend import StaticV6Backend
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v6.persistent_worker import (
    PersistentWorkerV6,
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


def _response(request: dict[str, Any], worker_instance_id: str, ok: bool, value=None, exc=None):
    return {
        "protocol": PROTOCOL,
        "request_id": request.get("request_id"),
        "operation": request.get("operation"),
        "ok": ok,
        "value": value if ok else None,
        "error_type": None if ok else type(exc).__name__,
        "error": None if ok else str(exc),
        "worker_instance_id": worker_instance_id,
        "worker_pid": os.getpid(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--static-fixture", action="store_true")
    parser.add_argument("--nonce", default="")
    args = parser.parse_args()
    if not args.static_fixture or not _is_sha256(args.nonce):
        sys.stderr.write("Blackwell v6 has no reviewed live adapter; refusing startup.\n")
        return 78
    if os.environ.get("KIRA_V6_STATIC_TEST_NONCE") != args.nonce:
        sys.stderr.write("Blackwell v6 static fixture nonce mismatch.\n")
        return 77
    config = load_canonical_config()
    maximum_request = int(config["ipc_bounds"]["maximum_request_bytes"])
    maximum_response = int(config["ipc_bounds"]["maximum_response_bytes"])
    lease = hashlib.sha256(f"v6-static-lease:{args.nonce}".encode()).hexdigest()
    instance = hashlib.sha256(
        f"v6-worker:{os.getpid()}:{time.monotonic_ns()}:{args.nonce}".encode()
    ).hexdigest()
    backend = StaticV6Backend(now=time.monotonic, worker_pid=os.getpid(), lease_id=lease)
    engine = PersistentWorkerV6(
        backend=backend,
        serialization_lease_id=lease,
        worker_instance_id=instance,
        worker_pid=os.getpid(),
        now=time.monotonic,
        allow_static_test=True,
    )
    descendants: list[subprocess.Popen[Any]] = []
    _write(
        {
            "event": "ready",
            "protocol": PROTOCOL,
            "pid": os.getpid(),
            "worker_instance_id": instance,
            "static_fixture": True,
            "creation_token_digest": hashlib.sha256(args.nonce.encode("utf-8")).hexdigest(),
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
                request = json.loads(line.decode("utf-8"))
                keys = {
                    "protocol",
                    "request_id",
                    "operation",
                    "payload",
                    "worker_instance_id",
                }
                if (
                    not isinstance(request, dict)
                    or set(request) != keys
                    or request["protocol"] != PROTOCOL
                    or not _is_sha256(request["request_id"])
                    or not isinstance(request["operation"], str)
                    or not isinstance(request["payload"], dict)
                    or request["worker_instance_id"] != instance
                ):
                    raise RuntimeError("request identity/schema mismatch")
                operation = request["operation"]
                if operation == "fixture_echo":
                    value = dict(request["payload"])
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
                    from Testing.blackwell_v6_static_fixture_backend import StaticModel

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
                _write(_response(request, instance, True, value=value), maximum_response)
                if operation == "shutdown":
                    break
            except Exception as exc:
                _write(_response(request, instance, False, exc=exc), maximum_response)
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
