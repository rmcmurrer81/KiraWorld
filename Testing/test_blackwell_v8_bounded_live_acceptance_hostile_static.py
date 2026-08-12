"""Hostile static tests for the one-shot Blackwell v8 live harness.

No test opens Ollama, imports Torch/Chatterbox, touches CUDA, synthesizes audio,
or invokes playback.  The full sequence uses only a synthetic fake coordinator.
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

from tools import run_blackwell_v8_bounded_live_acceptance as harness


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class FakeCoordinator:
    def __init__(self, *, hostile: str | None = None) -> None:
        self.hostile = hostile
        self.calls: list[str] = []
        self.component = _sha("exact-component")
        self.generation = _sha("exact-model-generation")
        self.condition = _sha("approved-condition")
        self.text = "I'm feeling calm and glad to be here with you right now."
        self.wav_sha = _sha("synthetic-wav")
        self.lease = {
            "handle_id": _sha("handle"),
            "artifact_sha256": self.wav_sha,
            "generation_id": _sha("wav-generation"),
            "resolved_path": str(ROOT / "synthetic-never-created.wav"),
            "text_sha256": _sha(self.text),
            "byte_length": 1024,
        }

    @staticmethod
    def _envelope(value: dict) -> dict:
        return {
            "value": value,
            "request_id": _sha("request"),
            "worker_pid": 43210,
            "worker_instance_id": _sha("worker"),
            "process_identity_digest": _sha("process"),
            "elapsed_seconds": 0.1,
            "deadline_seconds": 10.0,
        }

    def start(self) -> dict:
        self.calls.append("start")
        return {
            "started": True,
            "pid": 43210,
            "worker_instance_id": _sha("worker"),
            "job_or_process_group_owned": True,
            "created_suspended": True,
            "job_assignment_proof": {
                "assigned_before_resume": True,
                "kill_on_close": True,
                "job_memory_limit_bytes": 16 * 1024**3,
            },
            "process_identity": {
                "pid": 43210,
                "os_creation_token": 123456,
                "executable_path": "sealed-python.exe",
                "executable_sha256": _sha("python"),
                "executable_size": 100,
                "executable_volume_serial": 1,
                "executable_file_index": 2,
            },
            "process_identity_digest": _sha("process"),
        }

    def load(self, *, owner: str) -> dict:
        self.calls.append("load")
        return self._envelope({
            "success": True,
            "state": "LOADED_CUDA",
            "model_generation": self.generation,
            "component_fingerprint": self.component,
            "condition_digest": self.condition,
            "worker_pid": 43210,
        })

    def park(self, *, reason: str) -> dict:
        self.calls.append("park")
        return self._envelope({
            "success": True,
            "state": "PARKED_CPU",
            "model_generation": self.generation,
            "component_fingerprint": self.component,
            "component_transfer": {
                "from_device": "cuda",
                "to_device": "cpu",
                "record_sha256": _sha("park-transfer"),
            },
            "resources_before": {"process_rss_mib": 5000, "cuda_free_mib": 4000},
            "resources_after": {"process_rss_mib": 9000, "cuda_free_mib": 12000},
        })

    def qwen_load(
        self, *, owner: str, session: str, token: str, ttl_seconds: int
    ) -> dict:
        self.calls.append("qwen_load")
        if ttl_seconds != harness.QWEN_TTL_SECONDS:
            raise AssertionError("wrong TTL")
        return self._envelope({"success": True, "state": "QWEN_OWNED"})

    def qwen_stream(
        self, *, owner: str, session: str, token: str, messages: list[dict[str, str]]
    ) -> dict:
        self.calls.append("qwen_stream")
        if messages != [dict(item) for item in harness.MESSAGES]:
            raise AssertionError("messages drifted")
        text = "As an AI, I cannot feel." if self.hostile == "bad_text" else self.text
        records = (
            [{"model": harness.EXPECTED_MODEL, "digest": harness.EXPECTED_MODEL_DIGEST}]
            if self.hostile == "resident_after_qwen"
            else []
        )
        return self._envelope({
            "success": True,
            "state": "PARKED_CPU",
            "text": text,
            "text_sha256": _sha(text),
            "chunk_count": 2,
            "utf8_bytes": len(text.encode("utf-8")),
            "residency_precommit": {"records": records},
            "residency_after": {"records": records},
        })

    def resume(self, *, reason: str) -> dict:
        self.calls.append("resume")
        return self._envelope({
            "success": True,
            "state": "LOADED_CUDA",
            "model_generation": self.generation,
            "component_fingerprint": self.component,
            "component_transfer": {
                "from_device": "cpu",
                "to_device": "cuda",
                "record_sha256": _sha("resume-transfer"),
            },
        })

    def synthesize(self, request: dict) -> dict:
        self.calls.append("synthesize")
        if request["text"] != self.text or request["text_sha256"] != _sha(self.text):
            raise AssertionError("synthesis did not receive exact returned text")
        device = "cpu" if self.hostile == "cpu_voice" else "cuda"
        return self._envelope({
            "success": True,
            "state": "LOADED_CUDA",
            "device": device,
            "generation_id": self.lease["generation_id"],
            "model_generation": self.generation,
            "component_fingerprint": self.component,
            "text_sha256": _sha(self.text),
            "profile_sha256": harness.EXACT_PROFILE_SHA256,
            "reference_sha256": harness.EXACT_REFERENCE_SHA256,
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "artifact_lease": dict(self.lease),
        })

    def playback(self, lease: dict, *, playback_id: str) -> dict:
        self.calls.append("playback")
        return self._envelope({
            "success": True,
            "playback": {
                "artifact_sha256": lease["artifact_sha256"],
                "played_memory_sha256": lease["artifact_sha256"],
                "route": "blackwell_gpu",
                "device": "cuda",
                "generic_voice_used": False,
                "sapi_voice_used": False,
                "fallback_used": False,
                "playback_process_in_inherited_job": True,
                "owned_copy_deleted_after_return": True,
                "owner_hearing_proven": False,
            },
        })

    def cleanup(self, *, reason: str) -> dict:
        self.calls.append("cleanup")
        return self._envelope({
            "success": True,
            "unloaded": True,
            "cleanup_debt": False,
            "state": "UNLOADED",
            "qwen_absence": {"records": []},
            "resources_after": {"cuda_allocated_bytes": 0},
            "errors": [],
        })

    def close(self) -> dict:
        self.calls.append("close")
        return {
            "root_exited": True,
            "root_pid": 43210,
            "process_identity_digest": _sha("process"),
            "job_assignment_proof": {
                "assigned_before_resume": True,
                "kill_on_close": True,
            },
            "errors": [],
        }


def fake_resource(label: str) -> dict:
    return {
        "label": label,
        "captured_utc": "2026-08-10T00:00:00Z",
        "ram": {
            "total_physical_mib": 32768.0,
            "available_physical_mib": 16000.0,
            "system_commit_used_mib": 12000.0,
            "system_commit_limit_mib": 65536.0,
            "memory_load_percent": 50,
        },
        "vram": {
            "gpu_index": 0,
            "gpu_name": "NVIDIA GeForce RTX 5060 Ti",
            "gpu_uuid": "GPU-static",
            "memory_total_mib": 16384.0,
            "memory_free_mib": 15000.0,
            "memory_used_mib": 1384.0,
        },
    }


def absent_residency(label: str) -> dict:
    return {
        "label": label,
        "captured_utc": "2026-08-10T00:00:00Z",
        "elapsed_seconds": 0.01,
        "records": [],
        "all_models_absent": True,
    }


class HarnessStaticGateTests(unittest.TestCase):
    def test_import_is_inert_and_live_capability_is_exact(self):
        self.assertEqual(
            harness.EXPECTED_AUDIT_AUTHORIZATION_SHA256,
            "d822b4f07eb3ad7873f5e48129494c08b85f0e06845ae01d57841476bd4ef16f",
        )
        self.assertEqual(
            harness.LIVE_CAPABILITY_NAME,
            "KIRA_AUTHORIZE_BLACKWELL_V8_BOUNDED_ENGINEERING_RUN",
        )
        self.assertEqual(
            harness.LIVE_CAPABILITY_VALUE,
            "exact_qwen35_blackwell_v2_v8_after_fresh_audit_only",
        )
        self.assertEqual(harness.main([]), 64)

    def test_real_static_preflight_refuses_absent_and_wrong_capability(self):
        with (
            patch.object(harness, "verify_harness_seal", return_value={}),
            patch.object(harness, "verify_fresh_harness_audit", return_value={}),
        ):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop(harness.LIVE_CAPABILITY_NAME, None)
                os.environ.pop(harness.PLAYBACK_CAPABILITY_NAME, None)
                with self.assertRaisesRegex(harness.AcceptanceError, "capability"):
                    harness.validate_static_and_capability_gates(
                        playback=False, accepted_harness_audit_sha256="a" * 64
                    )
            with patch.dict(
                os.environ,
                {harness.LIVE_CAPABILITY_NAME: "almost-but-not-exact"},
                clear=False,
            ):
                os.environ.pop(harness.PLAYBACK_CAPABILITY_NAME, None)
                with self.assertRaisesRegex(harness.AcceptanceError, "capability"):
                    harness.validate_static_and_capability_gates(
                        playback=False, accepted_harness_audit_sha256="a" * 64
                    )

    def test_v8_static_preflight_accepts_exact_no_playback_gate_after_harness_audit(self):
        with (
            patch.object(harness, "verify_harness_seal", return_value={"sealed": True}),
            patch.object(
                harness, "verify_fresh_harness_audit", return_value={"verdict": "ACCEPT_STATIC_ONLY"}
            ),
            patch.dict(
                os.environ,
                {harness.LIVE_CAPABILITY_NAME: harness.LIVE_CAPABILITY_VALUE},
                clear=False,
            ),
        ):
            os.environ.pop(harness.PLAYBACK_CAPABILITY_NAME, None)
            value = harness.validate_static_and_capability_gates(
                playback=False, accepted_harness_audit_sha256="a" * 64
            )
        self.assertEqual(
            value["audit_authorization_sha256"],
            harness.EXPECTED_AUDIT_AUTHORIZATION_SHA256,
        )
        self.assertFalse(value["playback_requested"])

    def test_protected_v2_v7_v8_and_production_boundary_rehashes(self):
        value = harness.protected_boundary_snapshot()
        self.assertTrue(value["passed"])
        self.assertEqual(
            value["production_routing_sha256"],
            "a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81",
        )
        self.assertGreaterEqual(len(value["records"]), 18)

    def test_playback_requires_second_exact_capability_and_cli_alignment(self):
        base = {harness.LIVE_CAPABILITY_NAME: harness.LIVE_CAPABILITY_VALUE}
        with (
            patch.object(harness, "verify_harness_seal", return_value={}),
            patch.object(harness, "verify_fresh_harness_audit", return_value={}),
        ):
            with patch.dict(os.environ, base, clear=False):
                os.environ.pop(harness.PLAYBACK_CAPABILITY_NAME, None)
                with self.assertRaisesRegex(harness.AcceptanceError, "playback capability"):
                    harness.validate_static_and_capability_gates(
                        playback=True, accepted_harness_audit_sha256="a" * 64
                    )
            with patch.dict(
                os.environ,
                {**base, harness.PLAYBACK_CAPABILITY_NAME: harness.PLAYBACK_CAPABILITY_VALUE},
                clear=False,
            ):
                with self.assertRaisesRegex(harness.AcceptanceError, "without --playback"):
                    harness.validate_static_and_capability_gates(
                        playback=False, accepted_harness_audit_sha256="a" * 64
                    )

    def test_author_did_not_create_future_harness_audit(self):
        self.assertFalse(harness.HARNESS_AUDIT_AUTHORIZATION_PATH.exists())
        with self.assertRaisesRegex(harness.AcceptanceError, "absent or drifted"):
            harness.verify_fresh_harness_audit("a" * 64)

    def test_harness_seal_rehashes_exact_source_and_hostile_suite(self):
        value = harness.verify_harness_seal()
        self.assertEqual(value["harness_id"], harness.HARNESS_ID)
        self.assertEqual(len(value["files"]), 2)

    def test_one_shot_attempt_reservation_refuses_any_prior_attempt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(harness, "EVIDENCE_ROOT", root):
                first = harness.reserve_only_attempt()
                self.assertEqual(first.name, "attempt_01")
                with self.assertRaisesRegex(harness.AcceptanceError, "already reserved"):
                    harness.reserve_only_attempt()

    def test_write_once_and_hash_chained_ledger_refuse_rewrite(self):
        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp) / "attempt_01"
            attempt.mkdir()
            ledger = harness.AppendOnlyLedger(attempt)
            first = ledger.append("alpha", {"value": 1})
            second = ledger.append("beta", {"value": 2})
            record = json.loads((attempt / second["path"]).read_text(encoding="utf-8"))
            self.assertEqual(record["previous_event_sha256"], first["sha256"])
            with self.assertRaises(FileExistsError):
                harness.write_once_json(attempt / second["path"], {})

    def test_public_text_is_never_rewritten_and_hostile_text_is_rejected(self):
        text = "I'm feeling present and happy to talk with you right now."
        self.assertIs(harness.validate_public_text(text, _sha(text)), text)
        hostile = (
            "", " padded ", "two\nlines", "As an AI, I do not have feelings.",
            "One. Two. Three.", "x" * (harness.MAX_PUBLIC_TEXT_UTF8_BYTES + 1),
        )
        for value in hostile:
            with self.subTest(value=value[:20]):
                with self.assertRaises(harness.AcceptanceError):
                    harness.validate_public_text(value, _sha(value))

    def test_source_has_fixed_prompt_model_and_no_fallback_route(self):
        source = Path(harness.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_imports = {"torch", "torchaudio", "chatterbox", "winsound", "pyttsx3"}
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported & forbidden_imports)
        self.assertIn('EXPECTED_MODEL = "qwen3.5:9b"', source)
        self.assertIn('"input_channel": "public_spoken_only"', source)
        self.assertNotIn("llama3.1", source.casefold())
        self.assertNotIn("KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2", source)


class HarnessSyntheticSequenceTests(unittest.TestCase):
    def run_case(self, *, playback: bool = False, hostile: str | None = None):
        coordinator = FakeCoordinator(hostile=hostile)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "evidence"
            empty_a = Path(temp) / "v7_outputs"
            empty_b = Path(temp) / "v8_playback"
            with (
                patch.object(harness, "EVIDENCE_ROOT", root),
                patch.object(harness, "OWNED_RUNTIME_ROOTS", (empty_a, empty_b)),
                patch.object(
                    harness,
                    "validate_static_and_capability_gates",
                    return_value={
                        "audit_authorization_sha256": harness.EXPECTED_AUDIT_AUTHORIZATION_SHA256,
                        "playback_requested": playback,
                    },
                ),
                patch.object(
                    harness.BlackwellV8Coordinator,
                    "bounded_engineering_candidate",
                    return_value=coordinator,
                ) as factory,
                patch.object(harness, "capture_host_resources", side_effect=fake_resource),
                patch.object(harness, "ollama_residency_snapshot", side_effect=absent_residency),
                patch.object(
                    harness,
                    "wait_for_zero_residency",
                    return_value={"passed": True, "elapsed_seconds": 0.0, "samples": []},
                ),
                patch.object(
                    harness,
                    "validate_wav_lease",
                    return_value={
                        "resolved_path": "synthetic-never-created.wav",
                        "artifact_sha256": coordinator.wav_sha,
                        "generation_id": coordinator.lease["generation_id"],
                        "text_sha256": _sha(coordinator.text),
                        "byte_length": 1024,
                        "channels": 1,
                        "sample_width_bytes": 2,
                        "sample_rate_hz": 24000,
                        "frame_count": 100,
                        "duration_seconds": 100 / 24000,
                    },
                ),
            ):
                code, report_path = harness.execute_live(playback=playback)
                report = json.loads(report_path.read_text(encoding="utf-8"))
                event_files = sorted((report_path.parent / "events").glob("*.json"))
                return coordinator, factory, code, report, event_files

    def test_exact_no_playback_sequence_and_finally_cleanup(self):
        coordinator, factory, code, report, events = self.run_case()
        self.assertEqual(code, 0)
        self.assertTrue(report["accepted"])
        self.assertEqual(report["status"], "ENGINEERING_PASS_NO_PLAYBACK")
        self.assertEqual(
            coordinator.calls,
            [
                "start", "load", "park", "qwen_load", "qwen_stream",
                "resume", "synthesize", "cleanup", "close",
            ],
        )
        self.assertNotIn("playback", coordinator.calls)
        self.assertEqual(report["public_text"], coordinator.text)
        self.assertTrue(report["raw_qwen_text_equals_public_text"])
        self.assertTrue(report["spoken_text_equals_public_text"])
        self.assertTrue(report["qwen_unload_verification"]["verified"])
        self.assertTrue(report["finally_cleanup"]["zero_residue_proven"])
        self.assertGreaterEqual(len(events), 11)
        kwargs = factory.call_args.kwargs
        self.assertEqual(
            kwargs["accepted_audit_sha256"],
            harness.EXPECTED_AUDIT_AUTHORIZATION_SHA256,
        )

    def test_optional_playback_occurs_once_and_never_claims_owner_hearing(self):
        coordinator, _factory, code, report, _events = self.run_case(playback=True)
        self.assertEqual(code, 0)
        self.assertEqual(coordinator.calls.count("playback"), 1)
        self.assertEqual(coordinator.calls[-3:], ["playback", "cleanup", "close"])
        self.assertTrue(report["playback_performed"])
        self.assertFalse(report["owner_hearing_proven"])
        self.assertFalse(report["playback"]["owner_hearing_proven"])
        self.assertEqual(
            report["status"],
            "ENGINEERING_PASS_PLAYBACK_COMPLETED_OWNER_HEARING_NOT_CLAIMED",
        )

    def test_hostile_public_text_fails_before_resume_but_still_cleans(self):
        coordinator, _factory, code, report, _events = self.run_case(hostile="bad_text")
        self.assertEqual(code, 1)
        self.assertFalse(report["accepted"])
        self.assertNotIn("resume", coordinator.calls)
        self.assertNotIn("synthesize", coordinator.calls)
        self.assertEqual(coordinator.calls[-2:], ["cleanup", "close"])
        self.assertTrue(report["finally_cleanup"]["zero_residue_proven"])

    def test_hostile_qwen_residency_fails_before_resume_and_cleans(self):
        coordinator, _factory, code, report, _events = self.run_case(
            hostile="resident_after_qwen"
        )
        self.assertEqual(code, 1)
        self.assertNotIn("resume", coordinator.calls)
        self.assertEqual(coordinator.calls[-2:], ["cleanup", "close"])
        self.assertTrue(report["finally_cleanup"]["zero_residue_proven"])

    def test_cpu_voice_substitution_fails_after_synthesis_and_cleans(self):
        coordinator, _factory, code, report, _events = self.run_case(hostile="cpu_voice")
        self.assertEqual(code, 1)
        self.assertIn("synthesize", coordinator.calls)
        self.assertNotIn("playback", coordinator.calls)
        self.assertEqual(coordinator.calls[-2:], ["cleanup", "close"])
        self.assertTrue(report["finally_cleanup"]["zero_residue_proven"])


if __name__ == "__main__":
    unittest.main()
