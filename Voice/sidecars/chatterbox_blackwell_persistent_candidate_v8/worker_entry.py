#!/usr/bin/env python3
"""Killable JSONL entry for inactive Blackwell v8.

Static fixture mode is standard-library only.  Live imports occur only after a
different-agent audit record, exact audit hash, explicit per-run capability,
and exact sealed-byte verification all pass.
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
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v7.persistent_worker import (
    PersistentWorkerV7,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.candidate_contract import (
    is_sha256,
    load_canonical_config,
    sha256_file,
    verify_fresh_audit_authorization,
    verify_per_run_live_capability,
    verify_preserved_bytes,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.persistent_worker import (
    PersistentWorkerV8,
    V8LiveStateEngine,
)


def _write(value: Any, maximum_bytes: int) -> None:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    if len(payload) > maximum_bytes:
        raise RuntimeError("v8 response exceeded maximum bytes")
    sys.stdout.buffer.write(payload + b"\n")
    sys.stdout.buffer.flush()


def _response(
    request: Any,
    worker_instance_id: str,
    identity_digest: str,
    ok: bool,
    value: Any = None,
    exc: Exception | None = None,
) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "request_id": request.get("request_id") if isinstance(request, dict) else None,
        "operation": request.get("operation") if isinstance(request, dict) else None,
        "ok": ok,
        "value": value if ok else None,
        "error_type": None if ok else type(exc).__name__,
        "error": None if ok else str(exc),
        "worker_instance_id": worker_instance_id,
        "worker_pid": os.getpid(),
        "process_identity_digest": identity_digest,
    }


def _validate_request(request: Any, instance: str, identity_digest: str) -> dict[str, Any]:
    keys = {
        "protocol", "request_id", "operation", "payload",
        "worker_instance_id", "process_identity_digest",
    }
    if (
        not isinstance(request, dict)
        or set(request) != keys
        or request["protocol"] != PROTOCOL
        or not is_sha256(request["request_id"])
        or not isinstance(request["operation"], str)
        or not isinstance(request["payload"], dict)
        or request["worker_instance_id"] != instance
        or request["process_identity_digest"] != identity_digest
    ):
        raise RuntimeError("v8 request identity/schema mismatch")
    return request


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--static-fixture", action="store_true")
    group.add_argument("--live", action="store_true")
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--accepted-audit-sha256", default="")
    args = parser.parse_args()
    if not is_sha256(args.nonce):
        sys.stderr.write("Blackwell v8 nonce is invalid.\n")
        return 76
    config = load_canonical_config()
    verify_preserved_bytes(config)
    if args.static_fixture:
        if os.environ.get("KIRA_V8_STATIC_TEST_NONCE") != args.nonce:
            sys.stderr.write("Blackwell v8 static fixture nonce mismatch.\n")
            return 77
        from Testing.blackwell_v8_static_fixture_backend import (
            StaticPlaybackRunnerV8,
            StaticV7Backend,
        )

        lease = hashlib.sha256(f"v8-static-lease:{args.nonce}".encode()).hexdigest()
        backend = StaticV7Backend(now=time.monotonic, worker_pid=os.getpid(), lease_id=lease)
        core = PersistentWorkerV7(
            backend=backend,
            serialization_lease_id=lease,
            worker_instance_id=hashlib.sha256(
                f"v8-worker:{os.getpid()}:{time.monotonic_ns()}:{args.nonce}".encode()
            ).hexdigest(),
            worker_pid=os.getpid(),
            now=time.monotonic,
            allow_static_test=True,
        )
        playback_runner = StaticPlaybackRunnerV8(config=config, now=time.monotonic)
        static_fixture = True
    else:
        if sha256_file(__import__("pathlib").Path(sys.executable).resolve()) != config["voice_live_component"]["python_sha256"]:
            sys.stderr.write("Blackwell v8 live mode requires the exact sealed Blackwell Python.\n")
            return 75
        verify_per_run_live_capability(config)
        verify_fresh_audit_authorization(
            config, expected_audit_sha256=args.accepted_audit_sha256
        )
        if os.environ.get("KIRA_V8_LIVE_SESSION_NONCE") != args.nonce:
            sys.stderr.write("Blackwell v8 live session nonce mismatch.\n")
            return 78
        from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.live_adapter import (
            BoundedPlaybackRunnerV8,
            LiveBackendV8,
        )

        lease = hashlib.sha256(f"v8-live-lease:{args.nonce}".encode()).hexdigest()
        backend = LiveBackendV8(config, worker_pid=os.getpid(), lease_id=lease)
        instance = hashlib.sha256(
            f"v8-worker:{os.getpid()}:{time.monotonic_ns()}:{args.nonce}".encode()
        ).hexdigest()
        core = V8LiveStateEngine(
            backend=backend,
            serialization_lease_id=lease,
            worker_instance_id=instance,
            worker_pid=os.getpid(),
            now=time.monotonic,
            v8_config=config,
        )
        playback_runner = BoundedPlaybackRunnerV8(config)
        static_fixture = False
    instance = core.worker_instance_id
    engine = PersistentWorkerV8(engine=core, playback_runner=playback_runner, now=time.monotonic)
    maximum_request = 262_144
    maximum_response = 1_048_576
    descendants: list[subprocess.Popen[Any]] = []
    startup_descendant_pid: int | None = None
    if static_fixture and os.environ.get("KIRA_V8_STATIC_PRE_READY_DESCENDANT") == "1":
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
            "static_fixture": static_fixture,
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
                    raise RuntimeError("v8 request exceeded JSONL bound")
                request = _validate_request(
                    strict_finite_json_loads(line), instance, identity_digest
                )
                operation = request["operation"]
                if static_fixture and operation == "fixture_echo":
                    value = dict(request["payload"])
                elif static_fixture and operation == "fixture_stop_reading":
                    _write(
                        _response(request, instance, identity_digest, True, {"reader_stopped": True}),
                        maximum_response,
                    )
                    time.sleep(3600)
                    continue
                elif static_fixture and operation == "fixture_hang":
                    time.sleep(3600)
                    value = {"unexpected": "hang returned"}
                elif static_fixture and operation == "fixture_spawn_descendant":
                    child = subprocess.Popen(
                        [sys.executable, "-c", "import time; time.sleep(3600)"],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        shell=False,
                    )
                    descendants.append(child)
                    value = {"descendant_pid": child.pid}
                elif static_fixture and operation == "fixture_set_mode":
                    if set(request["payload"]) != {"target", "name", "value"}:
                        raise RuntimeError("v8 fixture mode schema mismatch")
                    target = request["payload"]["target"]
                    name = request["payload"]["name"]
                    if target == "playback" and name == "mode":
                        playback_runner.mode = request["payload"]["value"]
                    elif target == "backend" and name in {
                        "resource_mode", "qwen_race_phase", "qwen_race_mode",
                        "stream_advance_per_chunk", "artifact_mode", "cuda_mode",
                        "qwen_unload_success", "release_success",
                    }:
                        setattr(backend, name, request["payload"]["value"])
                    else:
                        raise RuntimeError("unsupported v8 fixture mode")
                    value = {"set": True, "target": target, "name": name}
                else:
                    value = engine.dispatch(operation, request["payload"])
                _write(
                    _response(request, instance, identity_digest, True, value=value),
                    maximum_response,
                )
                if operation == "shutdown":
                    break
            except Exception as exc:
                _write(
                    _response(request, instance, identity_digest, False, exc=exc),
                    maximum_response,
                )
    finally:
        try:
            engine.dispatch("cleanup", {"reason": "v8_worker_entry_exit"})
        except Exception:
            pass
        for child in descendants:
            try:
                child.kill()
            except OSError:
                pass
        close = getattr(backend, "close", None)
        if callable(close):
            close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
