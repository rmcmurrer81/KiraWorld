"""Hostile static tests for the sealed Blackwell v9 attempt_02 harness.

These tests do not start Ollama/Qwen, import Torch/Chatterbox, touch CUDA,
synthesize or play audio, activate a person, or open Blender.  The end-to-end
sequence test uses only a synthetic coordinator and in-memory telemetry.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Testing.test_blackwell_v8_bounded_live_acceptance_hostile_static import (  # noqa: E402
    FakeCoordinator,
    absent_residency,
    fake_resource,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v9 import (  # noqa: E402
    candidate_contract as v9_contract,
)
from tools import (  # noqa: E402
    run_blackwell_v8_bounded_live_acceptance as v8_harness,
)
from tools import (  # noqa: E402
    run_blackwell_v9_bounded_live_acceptance_attempt02 as harness,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class FakeV9Coordinator(FakeCoordinator):
    def __init__(self, *, hostile: str | None = None) -> None:
        super().__init__(hostile=hostile)
        self.nonce = _sha("nonce-not-yet-bound")
        self.sequence = 0

    def _envelope(self, value: dict) -> dict:
        self.sequence += 1
        return {
            "value": value,
            "request_id": _sha(f"request-{self.sequence}"),
            "worker_pid": 43211,
            "root_pid": 43210,
            "worker_instance_id": _sha("worker-instance"),
            "process_identity_digest": _sha("worker-process"),
            "launcher_process_identity_digest": _sha("launcher-process"),
            "writer": {
                "completed": True,
                "byte_count": 256,
                "native_thread_id": 99,
                "writer_thread_exited": True,
            },
            "elapsed_seconds": 0.1,
            "deadline_seconds": 10.0,
            "deadline_monotonic": 100.0,
        }

    def start(self) -> dict:
        self.calls.append("start")
        config = v9_contract.load_canonical_config()
        launcher = {
            **config["process_topology"]["launcher"],
            "pid": 43210,
            "os_creation_token": 111111,
        }
        worker = {
            **config["process_topology"]["worker"],
            "pid": 43211,
            "os_creation_token": 222222,
        }
        return {
            "started": True,
            "pid": 43211,
            "root_pid": 43210,
            "worker_pid": 43211,
            "worker_instance_id": _sha("worker-instance"),
            "command_digest": _sha("command"),
            "job_or_process_group_owned": True,
            "job_memory_limit_bytes": 16 * 1024**3,
            "job_assignment_proof": {
                "assigned_before_resume": True,
                "kill_on_close": True,
                "job_memory_limit_bytes": 16 * 1024**3,
            },
            "worker_child_job_proof": {
                "same_retained_job": True,
                "kill_on_close": True,
                "job_memory_limit_bytes": 16 * 1024**3,
            },
            "created_suspended": True,
            "resumed_thread_ids": [101],
            "startup_descendant_pid": None,
            "creation_token_digest": _sha(self.nonce),
            "launcher_process_handle_owned": True,
            "worker_process_handle_owned": True,
            "launcher_process_handle_proof": _sha("launcher-handle"),
            "worker_process_handle_proof": _sha("worker-handle"),
            "launcher_process_identity": launcher,
            "launcher_process_identity_digest": _sha("launcher-process"),
            "worker_process_identity": worker,
            "worker_process_identity_digest": _sha("worker-process"),
            "worker_direct_parent_pid": 43210,
            "arbitrary_descendant_accepted": False,
            "start_deadline_seconds": 10.0,
            "elapsed_seconds": 0.1,
        }

    def close(self) -> dict:
        self.calls.append("close")
        return {
            "root_exited": True,
            "worker_child_exited": True,
            "entire_bound_tree_exited": True,
            "worker_child_handle_closed": True,
            "job_handle_closed": True,
            "root_standard_streams_closed": True,
            "arbitrary_descendant_accepted": False,
            "errors": [],
        }


def exact_start(nonce: str) -> dict:
    coordinator = FakeV9Coordinator()
    coordinator.nonce = nonce
    return coordinator.start()


def exact_envelope(binding: dict, request_id: str | None = None) -> dict:
    return {
        "value": {"success": True, "state": "LOADED_CUDA"},
        "request_id": request_id or _sha("exact-response"),
        "worker_pid": binding["worker_pid"],
        "root_pid": binding["root_pid"],
        "worker_instance_id": binding["worker_instance_id"],
        "process_identity_digest": binding["process_identity_digest"],
        "launcher_process_identity_digest": binding[
            "launcher_process_identity_digest"
        ],
        "writer": {
            "completed": True,
            "byte_count": 100,
            "native_thread_id": 12,
            "writer_thread_exited": True,
        },
        "elapsed_seconds": 0.1,
        "deadline_seconds": 1.0,
        "deadline_monotonic": 10.0,
    }


class Attempt02StaticGateTests(unittest.TestCase):
    def test_import_is_inert_default_off_and_attempt_is_exact(self) -> None:
        self.assertEqual(harness.ATTEMPT_ID, "attempt_02")
        self.assertEqual(harness.main([]), 64)
        self.assertFalse(harness.EVIDENCE_ROOT.exists())
        self.assertNotIn("attempt_01", tuple(harness.parse_args([]).__dict__.values()))

    def test_author_did_not_create_future_harness_audit(self) -> None:
        with self.assertRaises(harness.AcceptanceError):
            harness.verify_fresh_harness_audit("a" * 64)

    def test_v9_and_v8_worker_audits_are_distinct_and_exact(self) -> None:
        self.assertNotEqual(
            harness.EXPECTED_V9_AUDIT_AUTHORIZATION_SHA256,
            harness.EXPECTED_V8_WORKER_AUDIT_AUTHORIZATION_SHA256,
        )
        self.assertEqual(
            v9_contract.sha256_file(harness.V9_AUDIT_AUTHORIZATION_PATH),
            harness.EXPECTED_V9_AUDIT_AUTHORIZATION_SHA256,
        )
        self.assertEqual(
            v9_contract.sha256_file(harness.V8_WORKER_AUDIT_AUTHORIZATION_PATH),
            harness.EXPECTED_V8_WORKER_AUDIT_AUTHORIZATION_SHA256,
        )
        config = v9_contract.load_canonical_config()
        self.assertEqual(
            config["v8_worker_audit_binding"]["sha256"],
            harness.EXPECTED_V8_WORKER_AUDIT_AUTHORIZATION_SHA256,
        )

    def test_live_gate_requires_both_exact_per_run_capabilities(self) -> None:
        config = v9_contract.load_canonical_config()
        fake_audit_sha = "a" * 64
        common = {
            config["engineering_run_opt_in"]: config["engineering_run_opt_in_value"],
        }
        with patch.object(
            harness,
            "verify_fresh_harness_audit",
            return_value={"verdict": "static-fixture"},
        ), patch.dict(os.environ, common, clear=False):
            os.environ.pop(harness.HARNESS_LIVE_CAPABILITY_NAME, None)
            with self.assertRaisesRegex(harness.AcceptanceError, "harness capability"):
                harness.validate_static_and_capability_gates(
                    playback=False,
                    accepted_harness_audit_sha256=fake_audit_sha,
                )
            os.environ[harness.HARNESS_LIVE_CAPABILITY_NAME] = (
                harness.HARNESS_LIVE_CAPABILITY_VALUE
            )
            gates = harness.validate_static_and_capability_gates(
                playback=False,
                accepted_harness_audit_sha256=fake_audit_sha,
            )
        self.assertEqual(gates["attempt_id"], "attempt_02")
        self.assertFalse(gates["consumed_attempt_01_reused"])

    def test_playback_requires_separate_exact_capability(self) -> None:
        config = v9_contract.load_canonical_config()
        environment = {
            config["engineering_run_opt_in"]: config["engineering_run_opt_in_value"],
            harness.HARNESS_LIVE_CAPABILITY_NAME: harness.HARNESS_LIVE_CAPABILITY_VALUE,
        }
        with patch.object(
            harness,
            "verify_fresh_harness_audit",
            return_value={"verdict": "static-fixture"},
        ), patch.dict(os.environ, environment, clear=False):
            os.environ.pop(harness.PLAYBACK_CAPABILITY_NAME, None)
            with self.assertRaisesRegex(harness.AcceptanceError, "playback capability"):
                harness.validate_static_and_capability_gates(
                    playback=True,
                    accepted_harness_audit_sha256="b" * 64,
                )
            os.environ[harness.PLAYBACK_CAPABILITY_NAME] = (
                harness.PLAYBACK_CAPABILITY_VALUE
            )
            gates = harness.validate_static_and_capability_gates(
                playback=True,
                accepted_harness_audit_sha256="b" * 64,
            )
        self.assertTrue(gates["playback_requested"])

    def test_consumed_attempt01_and_production_routing_remain_exact(self) -> None:
        self.assertEqual(
            v9_contract.sha256_file(harness.CONSUMED_ATTEMPT01_FINAL_REPORT_PATH),
            harness.EXPECTED_CONSUMED_ATTEMPT01_FINAL_REPORT_SHA256,
        )
        self.assertEqual(
            v9_contract.sha256_file(
                ROOT / "Voice/sidecars/kira_approved_voice_routing.json"
            ),
            harness.EXPECTED_PRODUCTION_ROUTING_SHA256,
        )
        config = v9_contract.load_canonical_config()
        observed = v9_contract.verify_preserved_bytes(config)
        self.assertEqual(
            observed[
                "RecoverySprint/continuation_20260810/blackwell_v8_bounded_live_acceptance/attempt_01/FINAL_REPORT.json"
            ],
            harness.EXPECTED_CONSUMED_ATTEMPT01_FINAL_REPORT_SHA256,
        )

    def test_existing_v9_integration_and_v8_harness_bytes_are_unchanged(self) -> None:
        self.assertEqual(
            v9_contract.sha256_file(
                ROOT / "Core/persistent_blackwell_voice_integration_v9.py"
            ),
            "cbb2e9cf04c2b21dafa03c96ca699bbbdac0a927269cd72ed10d9f9e74de3b09",
        )
        self.assertEqual(
            v9_contract.sha256_file(
                ROOT / "tools/run_blackwell_v8_bounded_live_acceptance.py"
            ),
            "9b002b824fd957c7e8af075ee4142beb0d33a32422b88cff9e0bd1bdeb4acfbb",
        )

    def test_attempt02_reservation_never_reuses_attempt01(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "new-evidence-root"
            with patch.object(harness, "EVIDENCE_ROOT", root):
                first = harness.reserve_attempt_02()
                self.assertEqual(first.name, "attempt_02")
                self.assertFalse((root / "attempt_01").exists())
                with self.assertRaisesRegex(harness.AcceptanceError, "already reserved"):
                    harness.reserve_attempt_02()

    def test_attempt01_named_directory_blocks_instead_of_being_reused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "new-evidence-root"
            (root / "attempt_01").mkdir(parents=True)
            with patch.object(harness, "EVIDENCE_ROOT", root):
                with self.assertRaisesRegex(harness.AcceptanceError, "already reserved"):
                    harness.reserve_attempt_02()
            self.assertFalse((root / "attempt_02").exists())

    def test_harness_seal_rehashes_exact_source_and_suite(self) -> None:
        value = harness.verify_harness_seal()
        self.assertEqual(value["harness_id"], harness.HARNESS_ID)
        self.assertEqual(
            {row["path"] for row in value["files"]}, harness._SEALED_HARNESS_FILES
        )

    def test_source_is_fixed_to_v9_qwen35_and_contains_no_live_import(self) -> None:
        source_path = ROOT / "tools/run_blackwell_v9_bounded_live_acceptance_attempt02.py"
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertTrue({"torch", "chatterbox", "ollama"}.isdisjoint(imports))
        self.assertIn('EXPECTED_MODEL = "qwen3.5:9b"', source)
        self.assertIn("BlackwellV9Coordinator.bounded_engineering_candidate", source)
        self.assertNotIn("BlackwellV8Coordinator.bounded_engineering_candidate", source)
        self.assertEqual(source.count('"qwen_single_generation"'), 2)


class Attempt02ProcessBindingTests(unittest.TestCase):
    def test_exact_dual_process_readiness_is_accepted(self) -> None:
        nonce = _sha("dual-process-readiness")
        start = exact_start(nonce)
        binding = harness.validate_v9_start(start, nonce=nonce)
        self.assertNotEqual(binding["root_pid"], binding["worker_pid"])
        self.assertEqual(start["worker_direct_parent_pid"], binding["root_pid"])
        self.assertTrue(start["worker_child_job_proof"]["same_retained_job"])

    def test_arbitrary_descendant_and_identity_drift_are_rejected(self) -> None:
        nonce = _sha("hostile-start")
        descendant = exact_start(nonce)
        descendant["worker_direct_parent_pid"] = descendant["root_pid"] + 99
        with self.assertRaisesRegex(harness.AcceptanceError, "PID binding"):
            harness.validate_v9_start(descendant, nonce=nonce)
        drift = exact_start(nonce)
        drift["worker_process_identity"]["executable_sha256"] = "0" * 64
        with self.assertRaisesRegex(harness.AcceptanceError, "identity drifted"):
            harness.validate_v9_start(drift, nonce=nonce)
        broad = exact_start(nonce)
        broad["arbitrary_descendant_accepted"] = True
        with self.assertRaisesRegex(harness.AcceptanceError, "ownership proof"):
            harness.validate_v9_start(broad, nonce=nonce)

    def test_response_replay_and_identity_drift_are_rejected(self) -> None:
        nonce = _sha("response-binding")
        binding = harness.validate_v9_start(exact_start(nonce), nonce=nonce)
        response = exact_envelope(binding)
        value = harness.require_bound_success(response, "first", binding)
        self.assertEqual(value["state"], "LOADED_CUDA")
        with self.assertRaisesRegex(harness.AcceptanceError, "replay"):
            harness.require_bound_success(response, "replayed", binding)
        fresh_binding = harness.validate_v9_start(exact_start(nonce), nonce=nonce)
        drift = exact_envelope(fresh_binding, request_id=_sha("fresh-request"))
        drift["worker_pid"] += 1
        with self.assertRaisesRegex(harness.AcceptanceError, "binding drifted"):
            harness.require_bound_success(drift, "identity-drift", fresh_binding)

    def test_nonfinite_and_late_response_telemetry_is_rejected(self) -> None:
        nonce = _sha("finite-telemetry")
        binding = harness.validate_v9_start(exact_start(nonce), nonce=nonce)
        nonfinite = exact_envelope(binding, request_id=_sha("nan"))
        nonfinite["elapsed_seconds"] = float("nan")
        with self.assertRaisesRegex(harness.AcceptanceError, "finite"):
            harness.require_bound_success(nonfinite, "nonfinite", binding)
        late = exact_envelope(binding, request_id=_sha("late"))
        late["elapsed_seconds"] = 2.0
        late["deadline_seconds"] = 1.0
        with self.assertRaisesRegex(harness.AcceptanceError, "finite"):
            harness.require_bound_success(late, "late", binding)


class Attempt02SyntheticSequenceTests(unittest.TestCase):
    def test_exact_sequence_cleanup_and_no_playback(self) -> None:
        coordinator = FakeV9Coordinator()

        def factory(**kwargs):
            coordinator.nonce = kwargs["nonce"]
            self.assertEqual(
                kwargs["accepted_v9_audit_sha256"],
                harness.EXPECTED_V9_AUDIT_AUTHORIZATION_SHA256,
            )
            self.assertEqual(
                kwargs["accepted_v8_worker_audit_sha256"],
                harness.EXPECTED_V8_WORKER_AUDIT_AUTHORIZATION_SHA256,
            )
            return coordinator

        protected = {
            "passed": True,
            "records": {"sealed": {"matched": True}},
            "production_routing_sha256": harness.EXPECTED_PRODUCTION_ROUTING_SHA256,
        }
        wav = {
            "resolved_path": str(ROOT / "synthetic-never-created.wav"),
            "artifact_sha256": coordinator.wav_sha,
            "generation_id": coordinator.lease["generation_id"],
            "text_sha256": _sha(coordinator.text),
            "byte_length": 1024,
            "channels": 1,
            "sample_width_bytes": 2,
            "sample_rate_hz": 24000,
            "frame_count": 24000,
            "duration_seconds": 1.0,
        }
        with tempfile.TemporaryDirectory() as temp, patch.object(
            harness, "EVIDENCE_ROOT", Path(temp) / "attempt02-root"
        ), patch.object(
            harness,
            "validate_static_and_capability_gates",
            return_value={
                "attempt_id": "attempt_02",
                "playback_requested": False,
                "production_routing_changed": False,
            },
        ), patch.object(
            harness,
            "protected_boundary_snapshot",
            return_value=protected,
        ), patch.object(
            harness.BlackwellV9Coordinator,
            "bounded_engineering_candidate",
            side_effect=factory,
        ), patch.object(
            v8_harness, "capture_host_resources", side_effect=fake_resource
        ), patch.object(
            v8_harness, "ollama_residency_snapshot", side_effect=absent_residency
        ), patch.object(
            v8_harness,
            "wait_for_zero_residency",
            return_value={"passed": True, "samples": []},
        ), patch.object(
            v8_harness,
            "owned_runtime_residue",
            return_value={"zero_file_residue": True, "total_files": 0, "roots": []},
        ), patch.object(
            v8_harness, "validate_wav_lease", return_value=wav
        ):
            code, report_path = harness.execute_live(playback=False)
            report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(report["attempt_id"], "attempt_02")
        self.assertFalse(report["consumed_attempt_01_reused"])
        self.assertTrue(report["accepted"])
        self.assertTrue(report["finally_cleanup"]["zero_residue_proven"])
        self.assertTrue(
            report["finally_cleanup"]["exact_launcher_and_worker_exited"]
        )
        self.assertEqual(
            coordinator.calls,
            [
                "start",
                "load",
                "park",
                "qwen_load",
                "qwen_stream",
                "resume",
                "synthesize",
                "cleanup",
                "close",
            ],
        )
        self.assertNotIn("playback", coordinator.calls)
        self.assertEqual(coordinator.calls.count("qwen_stream"), 1)


if __name__ == "__main__":
    unittest.main()
