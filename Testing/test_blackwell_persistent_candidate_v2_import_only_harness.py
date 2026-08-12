from __future__ import annotations

import importlib.util
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "Tools" / "run_blackwell_persistent_candidate_v2_import_only.py"

SPEC = importlib.util.spec_from_file_location("v2_import_only_harness_for_test", HARNESS_PATH)
assert SPEC is not None and SPEC.loader is not None
harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness)


class _BinaryStream:
    def __init__(self, buffer: object) -> None:
        self.buffer = buffer


class _TwoLineInput:
    def __init__(self) -> None:
        self.lines = [b'{"request":1}\n', b'{"request":2}\n']
        self.calls = 0
        self.lock = threading.Lock()

    def readline(self, _maximum: int) -> bytes:
        with self.lock:
            self.calls += 1
            return self.lines.pop(0) if self.lines else b""


class V2ImportOnlyHarnessStaticTests(unittest.TestCase):
    def test_describe_is_inert_and_exactly_bounded(self) -> None:
        before = harness.ATTEMPT_ROOT.exists() and sorted(
            item.name for item in harness.ATTEMPT_ROOT.iterdir()
        )
        result = harness.describe()
        after = harness.ATTEMPT_ROOT.exists() and sorted(
            item.name for item in harness.ATTEMPT_ROOT.iterdir()
        )
        self.assertEqual(before, after)
        self.assertFalse(result["live_import_performed"])
        self.assertEqual(result["imports_authorized"], ["torch"])
        self.assertEqual(result["child_hard_bound_seconds"], 120.0)
        self.assertLess(result["parent_total_bound_seconds"], 180.0)
        for key in ("cuda_authorized", "model_authorized", "audio_authorized", "ollama_authorized", "routing_change_authorized"):
            self.assertIs(result[key], False)

    def test_static_self_check_preserves_torch_absence_and_exact_bindings(self) -> None:
        torch_before = "torch" in sys.modules
        result = harness.static_self_check()
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["torch_imported_before"], torch_before)
        self.assertEqual(result["torch_imported_after"], torch_before)
        self.assertFalse(result["live_import_performed"])
        self.assertEqual(
            result["v2_bindings"],
            {
                "config": harness.V2_CONFIG_SHA256,
                "contract": harness.V2_CONTRACT_SHA256,
                "client": harness.V2_CLIENT_SHA256,
                "worker": harness.V2_WORKER_SHA256,
            },
        )

    def test_cli_without_all_live_bindings_refuses_before_attempt(self) -> None:
        before = harness.ATTEMPT_ROOT.exists() and sorted(
            item.name for item in harness.ATTEMPT_ROOT.iterdir()
        )
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [sys.executable, "-B", str(HARNESS_PATH), "--run-import"],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        after = harness.ATTEMPT_ROOT.exists() and sorted(
            item.name for item in harness.ATTEMPT_ROOT.iterdir()
        )
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertEqual(before, after)
        self.assertFalse(json.loads(completed.stdout)["live_import_performed"])

    def test_child_mode_cannot_bypass_live_environment_gate(self) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    harness.CHILD_MODE_ENV: "",
                    harness.LIVE_MODE_ENV: "",
                    harness.AUTH_KEY_ENV: "",
                },
            ),
            patch.object(
                harness,
                "active_blender_evidence",
                side_effect=AssertionError("Blender query must not precede child authorization"),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "authorization environment is absent"):
                harness.validate_authorization(Path("missing.json"), "0" * 64, ROOT)

    def test_child_authorization_hmac_tamper_fails_before_blender_gate(self) -> None:
        key = b"k" * 32
        with tempfile.TemporaryDirectory(prefix="kira_v2_auth_test_") as value:
            directory = Path(value)
            record_path = directory / "PARENT_AUTHORIZATION.json"
            record_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "binding_hmac_sha256": "0" * 64,
                    }
                ),
                encoding="utf-8",
            )
            digest = harness.sha256_file(record_path)
            with (
                patch.dict(
                    os.environ,
                    {
                        harness.CHILD_MODE_ENV: "1",
                        harness.LIVE_MODE_ENV: "1",
                        harness.AUTH_KEY_ENV: key.hex(),
                    },
                ),
                patch.object(
                    harness,
                    "active_blender_evidence",
                    side_effect=AssertionError("tampered HMAC must fail first"),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "HMAC mismatch"):
                    harness.validate_authorization(record_path, digest, directory)

    def test_reader_stack_proof_requires_semaphore_not_readline(self) -> None:
        incoming: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=2)
        complete = threading.Semaphore(0)
        stop = threading.Event()
        scripted = _TwoLineInput()
        with patch.object(
            harness.persistent_worker.sys,
            "stdin",
            _BinaryStream(scripted),
        ):
            reader = threading.Thread(
                target=harness.persistent_worker._stdin_reader,
                args=(incoming, 4096, complete, stop),
                name="persistent-blackwell-stdin-reader",
                daemon=True,
            )
            reader.start()
            self.assertEqual(incoming.get(timeout=1), ("request", {"request": 1}))
            proof = harness.prove_reader_parked_at_gate()
            self.assertTrue(proof["reader_parked_at_request_gate"])
            self.assertTrue(proof["reader_readline_absent"])
            self.assertEqual(scripted.calls, 1)
            stop.set()
            complete.release()
            reader.join(timeout=1)
        self.assertFalse(reader.is_alive())
        self.assertEqual(scripted.calls, 1)

    def test_trusted_result_requires_exact_boolean_types_and_ready_hash(self) -> None:
        result = {
            "authorization_sha256": "a" * 64,
            "harness_sha256": harness.sha256_file(HARNESS_PATH),
            "v2_config_sha256": harness.V2_CONFIG_SHA256,
            "v2_contract_sha256": harness.V2_CONTRACT_SHA256,
            "v2_client_sha256": harness.V2_CLIENT_SHA256,
            "v2_worker_sha256": harness.V2_WORKER_SHA256,
            "requested_imports": ["torch"],
            "torch_version": "2.11.0+cu130",
            "serve_return_code": 0,
            **{key: True for key in harness.TRUE_RESULT_FIELDS},
            **{key: False for key in harness.FALSE_OUTCOME_FIELDS},
        }
        encoded = json.dumps(result, sort_keys=True).encode("utf-8")
        result_evidence = {
            "present": True,
            "parsed": True,
            "sha256": __import__("hashlib").sha256(encoded).hexdigest(),
            "bytes": len(encoded),
            "payload": result,
        }
        ready = {
            "present": True,
            "parsed": True,
            "payload": {
                "trusted_child_result": True,
                "authorization_sha256": "a" * 64,
                "child_result_sha256": result_evidence["sha256"],
                "child_result_bytes": result_evidence["bytes"],
                "harness_sha256": result["harness_sha256"],
                "v2_config_sha256": result["v2_config_sha256"],
                "v2_contract_sha256": result["v2_contract_sha256"],
                "v2_client_sha256": result["v2_client_sha256"],
                "v2_worker_sha256": result["v2_worker_sha256"],
            },
        }
        trusted, issues = harness.validate_trusted_result(
            result_evidence,
            ready,
            "a" * 64,
        )
        self.assertTrue(trusted, issues)
        result["cuda_api_called"] = 0
        trusted, issues = harness.validate_trusted_result(
            result_evidence,
            ready,
            "a" * 64,
        )
        self.assertFalse(trusted)
        self.assertIn("cuda_api_called_not_exact_false", issues)

    def test_timeout_or_malformed_result_keeps_outcomes_unknown(self) -> None:
        self.assertTrue(
            all(value is None for value in harness.trusted_outcomes({}, False).values())
        )
        with tempfile.TemporaryDirectory(prefix="kira_v2_import_only_test_") as value:
            malformed = Path(value) / "CHILD_RESULT.json"
            malformed.write_bytes(b'{"partial":')
            evidence = harness.safe_json_evidence(malformed)
        self.assertTrue(evidence["present"])
        self.assertFalse(evidence["parsed"])
        self.assertIn("JSONDecodeError", evidence["error"])

    def test_atomic_result_and_ready_marker_are_append_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kira_v2_atomic_test_") as value:
            directory = Path(value)
            result_path = directory / "CHILD_RESULT.json"
            payload = {"schema_version": 1, "trusted_child_result": False}
            digest = harness.write_json_atomic_exclusive(result_path, payload)
            ready_path = directory / "CHILD_RESULT_READY.json"
            harness.write_json_atomic_exclusive(
                ready_path,
                {"child_result_sha256": digest, "trusted_child_result": False},
            )
            self.assertEqual(harness.sha256_file(result_path), digest)
            with self.assertRaises(FileExistsError):
                harness.write_json_atomic_exclusive(result_path, payload)
            self.assertEqual(list(directory.glob("*.tmp")), [])

    def test_attempt_numbering_is_append_only_and_gap_safe(self) -> None:
        self.assertEqual(harness.next_attempt_number([]), 1)
        self.assertEqual(
            harness.next_attempt_number(["attempt_01", "attempt_03", "notes"]),
            4,
        )


if __name__ == "__main__":
    unittest.main()
