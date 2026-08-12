from __future__ import annotations

import ast
import importlib
import json
import queue
import subprocess
import sys
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate_v2"
CONFIG = SIDECAR / "candidate_config.json"
CONTRACT = SIDECAR / "candidate_contract.py"
CLIENT = SIDECAR / "candidate_client.py"
WORKER = SIDECAR / "persistent_worker.py"


def _load_v2_modules():
    prefix = "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v2"
    contract = importlib.import_module(f"{prefix}.candidate_contract")
    client = importlib.import_module(f"{prefix}.candidate_client")
    worker = importlib.import_module(f"{prefix}.persistent_worker")
    return contract, client, worker


candidate_contract, candidate_client, persistent_worker = _load_v2_modules()


class _BinaryStream:
    def __init__(self, buffer: object) -> None:
        self.buffer = buffer


class _CaptureBuffer:
    def __init__(self) -> None:
        self._payload = bytearray()
        self._lock = threading.Lock()
        self.flush_count = 0

    def write(self, payload: bytes) -> int:
        with self._lock:
            self._payload.extend(payload)
        return len(payload)

    def flush(self) -> None:
        with self._lock:
            self.flush_count += 1

    def value(self) -> bytes:
        with self._lock:
            return bytes(self._payload)


class _ScriptedInput:
    def __init__(self, lines: list[bytes], output: _CaptureBuffer | None = None) -> None:
        self._lines = list(lines)
        self._lock = threading.Lock()
        self.output = output
        self.read_calls = 0
        self.flush_count_at_read: list[int | None] = []
        self.read_started = threading.Event()

    def readline(self, _maximum: int) -> bytes:
        with self._lock:
            self.read_calls += 1
            self.flush_count_at_read.append(
                self.output.flush_count if self.output is not None else None
            )
            self.read_started.set()
            if self._lines:
                return self._lines.pop(0)
            return b""


class _ReleaseBeforeReturnQueue(queue.Queue[tuple[str, object]]):
    """Model a response completing before the reader reaches acquire()."""

    def __init__(self, completion: threading.Semaphore) -> None:
        super().__init__(maxsize=2)
        self.completion = completion
        self.released = False

    def put(self, item, block=True, timeout=None) -> None:
        super().put(item, block=block, timeout=timeout)
        if item[0] == "request" and not self.released:
            self.released = True
            self.completion.release()


def _request(nonce: str, operation: str) -> bytes:
    return (
        json.dumps(
            {
                "schema_version": 1,
                "request_id": str(uuid.uuid4()),
                "session_nonce": nonce,
                "operation": operation,
                "playback": False,
                "fallback": False,
            }
        ).encode("utf-8")
        + b"\n"
    )


class BlackwellPersistentVoiceCandidateV2GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def _serve(self, lines: list[bytes], *, config: dict | None = None):
        capture = _CaptureBuffer()
        scripted = _ScriptedInput(lines, capture)
        with (
            patch.object(persistent_worker.sys, "stdin", _BinaryStream(scripted)),
            patch.object(persistent_worker.sys, "stdout", _BinaryStream(capture)),
        ):
            code = persistent_worker.serve(
                dict(config or self.config),
                "n" * 48,
                [],
            )
        payloads = [json.loads(line) for line in capture.value().splitlines()]
        return code, payloads, scripted, capture

    def test_reader_cannot_begin_second_read_while_fake_import_is_held(self) -> None:
        incoming: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=2)
        complete = threading.Semaphore(0)
        stop = threading.Event()
        scripted = _ScriptedInput([b'{"request":1}\n', b'{"request":2}\n'])
        with patch.object(persistent_worker.sys, "stdin", _BinaryStream(scripted)):
            reader = threading.Thread(
                target=persistent_worker._stdin_reader,
                args=(incoming, 4096, complete, stop),
                daemon=True,
            )
            reader.start()
            first = incoming.get(timeout=1)
            self.assertEqual(first, ("request", {"request": 1}))
            self.assertEqual(scripted.read_calls, 1)

            # Holding the semaphore represents the main thread being inside
            # the bounded load/import operation. A second inherited read is
            # forbidden throughout that interval.
            self.assertEqual(scripted.read_calls, 1)
            complete.release()
            second = incoming.get(timeout=1)
            self.assertEqual(second, ("request", {"request": 2}))
            self.assertEqual(scripted.read_calls, 2)

            stop.set()
            complete.release()
            reader.join(timeout=1)
        self.assertFalse(reader.is_alive())
        self.assertEqual(scripted.read_calls, 2)

    def test_next_read_begins_only_after_final_response_flush(self) -> None:
        nonce = "n" * 48
        code, payloads, scripted, capture = self._serve(
            [_request(nonce, "status"), _request(nonce, "shutdown"), _request(nonce, "status")]
        )
        self.assertEqual(code, 0)
        self.assertEqual([item["message_type"] for item in payloads], ["hello", "response", "response"])
        self.assertTrue(payloads[-1]["shutdown"])
        self.assertEqual(scripted.read_calls, 2)
        self.assertEqual(scripted.flush_count_at_read[1], 2)
        self.assertEqual(capture.flush_count, 3)

    def test_response_release_before_reader_acquire_is_not_lost(self) -> None:
        complete = threading.Semaphore(0)
        incoming = _ReleaseBeforeReturnQueue(complete)
        stop = threading.Event()
        scripted = _ScriptedInput([b'{"request":1}\n', b'{"request":2}\n'])
        with patch.object(persistent_worker.sys, "stdin", _BinaryStream(scripted)):
            reader = threading.Thread(
                target=persistent_worker._stdin_reader,
                args=(incoming, 4096, complete, stop),
                daemon=True,
            )
            reader.start()
            self.assertEqual(incoming.get(timeout=1), ("request", {"request": 1}))
            self.assertEqual(incoming.get(timeout=1), ("request", {"request": 2}))
            stop.set()
            complete.release()
            reader.join(timeout=1)
        self.assertTrue(incoming.released)
        self.assertFalse(reader.is_alive())
        self.assertEqual(scripted.read_calls, 2)

    def test_malformed_and_wrong_nonce_release_only_for_later_requests(self) -> None:
        nonce = "n" * 48
        wrong = _request("w" * 48, "status")
        code, payloads, scripted, _capture = self._serve(
            [b"{not-json}\n", wrong, _request(nonce, "shutdown")]
        )
        self.assertEqual(code, 0)
        self.assertEqual(scripted.read_calls, 3)
        self.assertEqual(payloads[1]["reason"], "persistent_candidate_malformed_json")
        self.assertEqual(payloads[2]["reason"], "persistent_candidate_request_rejected")
        self.assertIn("nonce", payloads[2]["error"])
        self.assertTrue(payloads[3]["shutdown"])

    def test_eof_exits_without_request_release(self) -> None:
        code, payloads, scripted, capture = self._serve([b""])
        self.assertEqual(code, 0)
        self.assertEqual(scripted.read_calls, 1)
        self.assertEqual([item["message_type"] for item in payloads], ["hello"])
        self.assertEqual(capture.flush_count, 1)

    def test_request_limit_is_terminal_and_does_not_read_a_third_line(self) -> None:
        nonce = "n" * 48
        limited = json.loads(json.dumps(self.config))
        limited["bounds"]["max_requests_per_process"] = 1
        code, payloads, scripted, _capture = self._serve(
            [_request(nonce, "status"), _request(nonce, "status"), _request(nonce, "status")],
            config=limited,
        )
        self.assertEqual(code, 0)
        self.assertEqual(scripted.read_calls, 2)
        self.assertEqual(payloads[-1]["message_type"], "fatal")
        self.assertEqual(
            payloads[-1]["reason"],
            "persistent_candidate_transport_request_limit_reached",
        )

    def test_v2_contract_is_sealed_inactive_and_keeps_production_route_unchanged(self) -> None:
        hashes = candidate_contract.verify_candidate_config(self.config)
        self.assertEqual(
            self.config["candidate_id"],
            "kira_chatterbox_blackwell_persistent_eager_cuda_candidate_v2",
        )
        self.assertFalse(self.config["production_routing_authorized"])
        self.assertIsNone(self.config["automatic_fallback_inside_candidate"])
        self.assertEqual(hashes["candidate_worker"], self.config["sealed_artifacts"][2]["sha256"])
        routing = json.loads(
            (ROOT / "Voice" / "sidecars" / "kira_approved_voice_routing.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual([item["route_id"] for item in routing["routes"]], ["blackwell_gpu", "sealed_cpu"])
        self.assertNotIn("persistent", json.dumps(routing).casefold())

    def test_worker_has_no_top_level_heavy_import(self) -> None:
        tree = ast.parse(WORKER.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(str(node.module or "").split(".")[0])
        self.assertTrue(
            {"torch", "torchaudio", "chatterbox", "soundfile", "numpy"}.isdisjoint(imported)
        )

    def test_static_self_check_imports_no_torch_and_loads_no_model(self) -> None:
        nonce = "s" * 48
        env = candidate_client.restricted_candidate_environment(
            self.config,
            session_nonce=nonce,
            allow_gpu_model_load=False,
        )
        completed = subprocess.run(
            [
                str(candidate_contract.project_file(self.config["python"])),
                str(WORKER),
                "--static-self-check",
            ],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ready"])
        self.assertFalse(payload["torch_imported_before"])
        self.assertFalse(payload["torch_imported_after"])
        self.assertFalse(payload["model_loaded"])
        self.assertFalse(payload["audio_generated"])
        self.assertFalse(payload["playback"])

    def test_fresh_process_no_model_protocol_exits_cleanly(self) -> None:
        client = candidate_client.PersistentBlackwellVoiceCandidateClient(
            allow_gpu_model_load=False,
            startup_timeout_seconds=60,
            request_timeout_seconds=60,
        )
        try:
            hello = client.start()
            self.assertFalse(hello["model_loaded"])
            status = client.status()
            self.assertFalse(status["lifecycle"]["model_loaded"])
            unloaded = client.unload()
            self.assertFalse(unloaded["model_was_loaded"])
        finally:
            closed = client.close()
        self.assertTrue(closed["shutdown"])
        self.assertEqual(closed["owned_process_exit_code"], 0)
        self.assertFalse(closed["owned_process_forced_termination"])

    def test_fresh_shutdown_exits_before_parent_closes_stdin(self) -> None:
        nonce = "z" * 48
        env = candidate_client.restricted_candidate_environment(
            self.config,
            session_nonce=nonce,
            allow_gpu_model_load=False,
        )
        process = subprocess.Popen(
            [
                str(candidate_contract.project_file(self.config["python"])),
                str(WORKER),
                "--serve",
            ],
            cwd=str(ROOT),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            self.assertIsNotNone(process.stdin)
            self.assertIsNotNone(process.stdout)
            hello = json.loads(process.stdout.readline())
            self.assertEqual(hello["message_type"], "hello")
            process.stdin.write(_request(nonce, "shutdown").decode("utf-8"))
            process.stdin.flush()
            stopped = json.loads(process.stdout.readline())
            self.assertTrue(stopped["shutdown"])
            process.wait(timeout=10)
            stderr = process.stderr.read() if process.stderr is not None else ""
            self.assertEqual(process.returncode, 0, stderr)
            self.assertFalse(process.stdin.closed)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()


if __name__ == "__main__":
    unittest.main()
