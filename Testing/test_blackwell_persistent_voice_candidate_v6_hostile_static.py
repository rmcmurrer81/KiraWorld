"""Hostile static-only acceptance tests for the sealed Blackwell v6 candidate.

These tests use only the standard-library fixture backend.  They must never
load Qwen, Torch, CUDA, Chatterbox, an audio device, a person, or Blender.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import math
import os
import threading
import time
import unittest
from pathlib import Path

from Core import blackwell_v6_process_boundary as boundary
from Core import persistent_blackwell_voice_integration_v6 as integration
from Testing.blackwell_v6_static_fixture_backend import (
    ManualClock,
    StaticModel,
    StaticV6Backend,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v6 import (
    persistent_worker as worker,
)


ROOT = Path(__file__).resolve().parents[1]
LEASE = hashlib.sha256(b"v6-hostile-static-exclusive-lease").hexdigest()
INSTANCE = hashlib.sha256(b"v6-hostile-static-worker-instance").hexdigest()
OWNER_HASH = hashlib.sha256(b"v6-owner").hexdigest()
SESSION_HASH = hashlib.sha256(b"v6-session").hexdigest()
TOKEN_HASH = hashlib.sha256(b"v6-token").hexdigest()
PUBLIC_TEXT = "This is an approved static public SPOKEN sentence."


def _process_alive(pid: int) -> bool:
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    kernel32.GetExitCodeProcess.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
        return code.value == 259
    finally:
        kernel32.CloseHandle(handle)


class EngineCase(unittest.TestCase):
    def make_engine(self):
        clock = ManualClock()
        backend = StaticV6Backend(now=clock, worker_pid=os.getpid(), lease_id=LEASE)
        self.addCleanup(backend.close)
        engine = worker.PersistentWorkerV6(
            backend=backend,
            serialization_lease_id=LEASE,
            worker_instance_id=INSTANCE,
            worker_pid=os.getpid(),
            now=clock,
            allow_static_test=True,
        )
        return engine, backend, clock

    @staticmethod
    def load(engine):
        return engine.dispatch("load", {"owner_hash": OWNER_HASH})

    @staticmethod
    def park(engine):
        return engine.dispatch("park", {"reason": "hostile-static"})

    @staticmethod
    def qwen_load(engine, ttl=90):
        return engine.dispatch(
            "qwen_load",
            {
                "owner_hash": OWNER_HASH,
                "session_hash": SESSION_HASH,
                "token_hash": TOKEN_HASH,
                "ttl_seconds": ttl,
            },
        )

    @staticmethod
    def qwen_stream(engine):
        return engine.dispatch(
            "qwen_stream",
            {
                "owner_hash": OWNER_HASH,
                "session_hash": SESSION_HASH,
                "token_hash": TOKEN_HASH,
                "messages": [{"role": "user", "content": "Reply naturally."}],
            },
        )

    @staticmethod
    def synthesis_payload(engine):
        return {
            "text": PUBLIC_TEXT,
            "text_sha256": worker.sha256_text(PUBLIC_TEXT),
            "input_channel": "public_spoken_only",
            "profile_sha256": worker.EXACT_PROFILE_SHA256,
            "reference_sha256": worker.EXACT_REFERENCE_SHA256,
            "condition_digest": engine.condition_digest,
        }


class V6PolicyAndPreservationTests(EngineCase):
    def test_01_policy_is_default_off_exact_and_prior_bytes_are_preserved(self):
        config = worker.load_canonical_config()
        self.assertFalse(config["production_routing_authorized"])
        self.assertFalse(config["live_execution_authorized"])
        self.assertFalse(config["playback_authorized"])
        self.assertFalse(config["live_adapter_available"])
        self.assertEqual(config["qwen_model"], "qwen3.5:9b")
        self.assertEqual(config["qwen_digest"], worker.EXACT_QWEN_DIGEST)
        self.assertFalse(config["cpu_synthesis_allowed"])
        self.assertFalse(config["generic_voice_allowed"])
        self.assertFalse(config["sapi_allowed"])
        self.assertFalse(config["llama_allowed"])
        self.assertEqual(config["qwen_policy"]["positive_residency_ttl_seconds"], 90)
        self.assertLess(
            config["operation_bounds_seconds"]["qwen_real_stream"],
            config["qwen_policy"]["positive_residency_ttl_seconds"],
        )
        self.assertEqual(
            config["resource_bounds"]["maximum_worker_job_memory_mib"], 16384
        )
        observed = worker.verify_preserved_bytes(config)
        expected_paths = {
            relative
            for group in (
                "sealed_prior_evidence",
                "sealed_v5_baseline",
                "sealed_v2_baseline",
                "sealed_v3_rejected_baseline",
                "sealed_v4_rejected_baseline",
            )
            for relative in config[group]
        }
        self.assertEqual(set(observed), expected_paths)
        self.assertEqual(worker.verify_identity_files()["reference_sha256"], worker.EXACT_REFERENCE_SHA256)

    def test_02_live_factory_and_playback_fail_closed(self):
        with self.assertRaises(worker.V6ContractError):
            integration.BlackwellV6Coordinator.production_candidate()
        self.assertFalse(integration.PRODUCTION_ROUTING_AUTHORIZED)
        self.assertFalse(integration.LIVE_ADAPTER_AVAILABLE)
        self.assertFalse(integration.PLAYBACK_IMPLEMENTED)

    def test_03_policy_injection_nan_and_backend_identity_swap_fail_closed(self):
        canonical = worker.load_canonical_config()
        injected = json.loads(json.dumps(canonical))
        injected["resource_bounds"]["maximum_system_commit_fraction"] = math.nan
        with self.assertRaises(worker.V6ContractError):
            worker.validate_canonical_config(injected)
        engine, backend, _ = self.make_engine()
        self.assertTrue(self.load(engine)["success"])
        replacement = StaticV6Backend(now=engine.now, worker_pid=os.getpid(), lease_id=LEASE)
        self.addCleanup(replacement.close)
        engine.backend = replacement
        result = self.park(engine)
        self.assertFalse(result["success"])
        self.assertIn("backend object identity drift", result["error"])

    def test_04_closed_ipc_rejects_nan_and_oversize_and_escapes_newlines(self):
        with self.assertRaises(boundary.V6ProcessBoundaryError):
            boundary._closed_json_bytes({"x": math.nan}, 100)
        escaped = boundary._closed_json_bytes({"x": "line\nfeed"}, 100)
        self.assertNotIn(b"\n", escaped)
        self.assertIn(b"\\n", escaped)
        with self.assertRaises(boundary.V6ProcessBoundaryError):
            boundary._closed_json_bytes({"x": "z" * 101}, 20)


class V6ActualProcessBoundaryTests(EngineCase):
    def make_coordinator(self, label: str):
        nonce = hashlib.sha256(label.encode()).hexdigest()
        coordinator = integration.BlackwellV6Coordinator.static_fixture_candidate(nonce=nonce)
        self.addCleanup(coordinator.process.close)
        return coordinator

    def test_05_real_child_identity_job_limit_and_closed_json_echo(self):
        coordinator = self.make_coordinator("v6-real-child")
        started = coordinator.start()
        self.assertNotEqual(started["pid"], os.getpid())
        self.assertEqual(started["pid"], coordinator.worker_pid)
        self.assertEqual(
            started["job_memory_limit_bytes"],
            16384 * 1024 * 1024,
        )
        self.assertTrue(started["process_handle_owned"])
        self.assertEqual(len(started["process_handle_proof"]), 64)
        self.assertEqual(len(started["creation_token_digest"]), 64)
        self.assertEqual(started["start_deadline_seconds"], 5.0)
        echoed = coordinator.process.invoke("fixture_echo", {"closed": True}, 1.0)
        self.assertEqual(echoed["value"], {"closed": True})
        self.assertEqual(echoed["worker_pid"], started["pid"])
        self.assertEqual(echoed["deadline_seconds"], 1.0)

    def test_06_real_hang_deadline_kills_exact_worker_tree(self):
        coordinator = self.make_coordinator("v6-hang-kill")
        started = coordinator.start()
        before = time.monotonic()
        with self.assertRaises(boundary.V6ProcessTimeout):
            coordinator.process.invoke("fixture_hang", {}, 0.25)
        elapsed = time.monotonic() - before
        self.assertLess(elapsed, 4.0)
        self.assertFalse(_process_alive(started["pid"]))
        self.assertTrue(coordinator.process.last_termination["root_exited"])

    def test_07_cancel_does_not_wait_for_operation_lock(self):
        coordinator = self.make_coordinator("v6-cancel-no-lock")
        coordinator.start()
        errors = []

        def invoke_hang():
            try:
                coordinator.process.invoke("fixture_hang", {}, 5.0)
            except Exception as exc:  # exact failure type is timing-dependent after hard kill
                errors.append(exc)

        thread = threading.Thread(target=invoke_hang)
        thread.start()
        time.sleep(0.15)
        before = time.monotonic()
        result = coordinator.cancel_now(reason="hostile-cancel")
        elapsed = time.monotonic() - before
        thread.join(timeout=1.0)
        self.assertLess(elapsed, 3.5)
        self.assertFalse(thread.is_alive())
        self.assertTrue(errors)
        self.assertTrue(result["cancelled"])
        self.assertTrue(result["cleanup_debt"])

    def test_08_job_kills_spawned_descendant(self):
        coordinator = self.make_coordinator("v6-descendant-kill")
        coordinator.start()
        spawned = coordinator.process.invoke("fixture_spawn_descendant", {}, 1.0)
        child_pid = spawned["value"]["descendant_pid"]
        self.assertTrue(_process_alive(child_pid))
        coordinator.cancel_now(reason="kill-descendant")
        deadline = time.monotonic() + 2.0
        while _process_alive(child_pid) and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertFalse(_process_alive(child_pid))

    def test_09_full_static_child_lifecycle_is_serial_and_no_playback(self):
        coordinator = self.make_coordinator("v6-full-static-lifecycle")
        coordinator.start()
        loaded = coordinator.load(owner="Robert static owner")["value"]
        self.assertTrue(loaded["success"])
        self.assertTrue(coordinator.park(reason="serialize for Qwen")["value"]["success"])
        token = "v6-static-owner-capability-token-000000000001"
        self.assertTrue(
            coordinator.qwen_load(
                owner="Robert",
                session="session-one",
                token=token,
                ttl_seconds=90,
            )["value"]["success"]
        )
        qwen = coordinator.qwen_stream(
            owner="Robert",
            session="session-one",
            token=token,
            messages=[{"role": "user", "content": "How are you?"}],
        )["value"]
        self.assertTrue(qwen["success"])
        self.assertIsNone(coordinator.last_owned_token_hash)
        self.assertTrue(coordinator.resume(reason="voice turn")["value"]["success"])
        request = {
            "text": PUBLIC_TEXT,
            "text_sha256": worker.sha256_text(PUBLIC_TEXT),
            "input_channel": "public_spoken_only",
            "profile_sha256": worker.EXACT_PROFILE_SHA256,
            "reference_sha256": worker.EXACT_REFERENCE_SHA256,
            "condition_digest": loaded["condition_digest"],
        }
        synthesis = coordinator.synthesize(request)["value"]
        self.assertTrue(synthesis["success"])
        self.assertFalse(synthesis["playback_implemented"])
        self.assertTrue(
            coordinator.artifact_status(synthesis["artifact_lease"])["value"]["success"]
        )
        cleaned = coordinator.cleanup(reason="static lifecycle complete")["value"]
        self.assertTrue(cleaned["unloaded"])
        self.assertEqual(cleaned["state"], "UNLOADED")

    def test_10_parent_keeps_provisional_qwen_token_across_ipc_failure(self):
        class FailingProcess:
            def invoke(self, operation, payload, timeout):
                raise boundary.V6ProcessTimeout("static injected boundary failure")

        coordinator = integration.BlackwellV6Coordinator(FailingProcess(), static_fixture=True)
        token = "v6-static-owner-capability-token-000000000002"
        with self.assertRaises(boundary.V6ProcessTimeout):
            coordinator.qwen_load(
                owner="Robert",
                session="session-two",
                token=token,
                ttl_seconds=90,
            )
        self.assertEqual(coordinator.last_owned_token_hash, hashlib.sha256(token.encode()).hexdigest())
        self.assertTrue(coordinator.cleanup_debt)
        self.assertEqual(coordinator.state, "CLEANUP_DEBT")

    def test_10a_concurrent_second_operation_has_bounded_lock_wait(self):
        coordinator = self.make_coordinator("v6-concurrent-lock")
        coordinator.start()
        first_errors = []

        def first_operation():
            try:
                coordinator.process.invoke("fixture_hang", {}, 0.8)
            except Exception as exc:
                first_errors.append(exc)

        thread = threading.Thread(target=first_operation)
        thread.start()
        time.sleep(0.1)
        before = time.monotonic()
        with self.assertRaises(boundary.V6ProcessTimeout):
            coordinator.process.invoke("fixture_echo", {"second": True}, 0.2)
        self.assertLess(time.monotonic() - before, 0.5)
        thread.join(timeout=2.0)
        self.assertFalse(thread.is_alive())
        self.assertTrue(first_errors)


class V6StateIdentityAndResourceTests(EngineCase):
    def test_11_happy_static_state_machine_preserves_exact_generation(self):
        engine, backend, _ = self.make_engine()
        loaded = self.load(engine)
        generation = loaded["model_generation"]
        condition = loaded["condition_digest"]
        self.assertTrue(self.park(engine)["success"])
        self.assertTrue(self.qwen_load(engine)["success"])
        self.assertTrue(self.qwen_stream(engine)["success"])
        self.assertTrue(engine.dispatch("resume", {"reason": "static"})["success"])
        self.assertEqual(engine.model_generation, generation)
        self.assertEqual(engine.condition_digest, condition)
        synthesis = engine.dispatch("synthesis", self.synthesis_payload(engine))
        self.assertTrue(synthesis["success"])
        self.assertEqual(synthesis["model_generation"], generation)
        self.assertIs(backend.last_synthesis_kwargs["model"], engine.model)
        self.assertEqual(
            backend.last_synthesis_kwargs["approved_audio_prompt_sha256"],
            worker.EXACT_REFERENCE_SHA256,
        )

    def test_12_backend_model_swap_and_engine_model_swap_are_rejected(self):
        for target in ("backend", "engine"):
            with self.subTest(target=target):
                engine, backend, _ = self.make_engine()
                self.assertTrue(self.load(engine)["success"])
                if target == "backend":
                    backend.model = StaticModel()
                else:
                    engine.model = StaticModel()
                result = self.park(engine)
                self.assertFalse(result["success"])
                self.assertIn("model object", result["error"])

    def test_13_mixed_device_and_conditioning_drift_are_rejected(self):
        engine, _, _ = self.make_engine()
        self.assertTrue(self.load(engine)["success"])
        engine.model.s3gen.to("cpu")
        result = self.park(engine)
        self.assertFalse(result["success"])
        self.assertIn("device/conditioning identity drift", result["error"])

        engine, _, _ = self.make_engine()
        self.assertTrue(self.load(engine)["success"])
        engine.model.conds.t3.token.payload = b"changed-conditioning"
        result = self.park(engine)
        self.assertFalse(result["success"])
        self.assertIn("device/conditioning identity drift", result["error"])

    def test_14_parked_rss_hard_bound_is_enforced(self):
        engine, backend, _ = self.make_engine()
        self.assertTrue(self.load(engine)["success"])
        backend.resource_mode = "high_park_rss"
        result = self.park(engine)
        self.assertFalse(result["success"])
        self.assertIn("RAM/VRAM bounds", result["error"])

    def test_15_nan_and_future_resource_evidence_fail_closed(self):
        for mode in ("nan", "future"):
            with self.subTest(mode=mode):
                engine, backend, _ = self.make_engine()
                backend.resource_mode = mode
                result = self.load(engine)
                self.assertFalse(result["success"])
                self.assertTrue(
                    "resource" in result["error"].lower()
                    or "non-finite" in result["error"].lower()
                )

    def test_16_nonfinite_monotonic_clock_fails_closed(self):
        engine, _, clock = self.make_engine()
        clock.value = math.nan
        result = self.load(engine)
        self.assertFalse(result["success"])
        self.assertIn("clock", result["error"])


class V6QwenHostileTests(EngineCase):
    def _run_phase(self, phase: str):
        engine, backend, _ = self.make_engine()
        if phase.startswith("load_"):
            backend.qwen_race_phase = phase
            return self.load(engine)
        self.assertTrue(self.load(engine)["success"])
        if phase.startswith("park_"):
            backend.qwen_race_phase = phase
            return self.park(engine)
        self.assertTrue(self.park(engine)["success"])
        if phase.startswith("qwen_load_"):
            backend.qwen_race_phase = phase
            backend.qwen_race_mode = "extra"
            return self.qwen_load(engine)
        self.assertTrue(self.qwen_load(engine)["success"])
        if phase.startswith("qwen_stream_"):
            backend.qwen_race_phase = phase
            return self.qwen_stream(engine)
        self.assertTrue(self.qwen_stream(engine)["success"])
        if phase.startswith("resume_"):
            backend.qwen_race_phase = phase
            return engine.dispatch("resume", {"reason": "hostile-race"})
        self.assertTrue(engine.dispatch("resume", {"reason": "hostile-race"})["success"])
        backend.qwen_race_phase = phase
        return engine.dispatch("synthesis", self.synthesis_payload(engine))

    def test_17_qwen_appearance_races_at_every_transition_fail_closed(self):
        phases = (
            "load_before",
            "load_precommit",
            "load_after",
            "park_before",
            "park_precommit",
            "park_after",
            "qwen_load_before",
            "qwen_load_commit",
            "qwen_load_after",
            "qwen_stream_precommit",
            "qwen_stream_after",
            "resume_before",
            "resume_precommit",
            "resume_after",
            "synthesis_before",
            "synthesis_precommit",
            "synthesis_after",
        )
        for phase in phases:
            with self.subTest(phase=phase):
                result = self._run_phase(phase)
                self.assertFalse(result["success"], phase)

    def test_18_qwen_ttl_is_exact_positive_integer_only(self):
        for ttl in (True, 90.0, 0, 1, 89, 91, 120, 121):
            with self.subTest(ttl=ttl):
                engine, _, _ = self.make_engine()
                self.assertTrue(self.load(engine)["success"])
                self.assertTrue(self.park(engine)["success"])
                result = self.qwen_load(engine, ttl=ttl)
                self.assertFalse(result["success"])
        engine, _, _ = self.make_engine()
        self.assertTrue(self.load(engine)["success"])
        self.assertTrue(self.park(engine)["success"])
        self.assertTrue(self.qwen_load(engine, ttl=90)["success"])

    def test_19_stream_ttl_aggregate_chunk_and_byte_bounds(self):
        modes = ("ttl", "aggregate", "chunks", "bytes", "empty")
        for mode in modes:
            with self.subTest(mode=mode):
                engine, backend, clock = self.make_engine()
                self.assertTrue(self.load(engine)["success"])
                self.assertTrue(self.park(engine)["success"])
                self.assertTrue(self.qwen_load(engine)["success"])
                if mode == "ttl":
                    clock.advance(90)
                elif mode == "aggregate":
                    backend.stream_advance_per_chunk = 43.0
                elif mode == "chunks":
                    backend.stream_chunks = ["x"] * 513
                elif mode == "bytes":
                    backend.stream_chunks = ["x" * 65537]
                elif mode == "empty":
                    backend.stream_chunks = []
                result = self.qwen_stream(engine)
                self.assertFalse(result["success"])

    def test_20_qwen_binding_mutation_and_malformed_stream_cleanup_exactly(self):
        engine, backend, _ = self.make_engine()
        self.assertTrue(self.load(engine)["success"])
        self.assertTrue(self.park(engine)["success"])
        self.assertTrue(self.qwen_load(engine)["success"])
        engine.qwen_binding = dict(engine.qwen_binding)
        engine.qwen_binding["expires_monotonic"] += 1
        result = self.qwen_stream(engine)
        self.assertFalse(result["success"])
        self.assertTrue(result["cleanup"]["unloaded"])
        self.assertEqual(backend.qwen_records, [])

        engine, backend, _ = self.make_engine()
        self.assertTrue(self.load(engine)["success"])
        self.assertTrue(self.park(engine)["success"])
        self.assertTrue(self.qwen_load(engine)["success"])
        backend.qwen_stream = lambda **kwargs: {"malformed": True}
        malformed = self.qwen_stream(engine)
        self.assertFalse(malformed["success"])
        self.assertTrue(malformed["cleanup"]["unloaded"])
        self.assertEqual(backend.qwen_records, [])

    def test_21_policy_drift_during_qwen_still_runs_exact_cleanup(self):
        engine, backend, _ = self.make_engine()
        self.assertTrue(self.load(engine)["success"])
        self.assertTrue(self.park(engine)["success"])
        self.assertTrue(self.qwen_load(engine)["success"])
        engine._policy_digest = "0" * 64
        result = self.qwen_stream(engine)
        self.assertFalse(result["success"])
        self.assertTrue(result["cleanup"]["unloaded"])
        self.assertEqual(result["state"], "UNLOADED")
        self.assertEqual(backend.qwen_records, [])

    def test_22_cleanup_debt_retains_qwen_binding_and_retry_recovers(self):
        engine, backend, _ = self.make_engine()
        self.assertTrue(self.load(engine)["success"])
        self.assertTrue(self.park(engine)["success"])
        self.assertTrue(self.qwen_load(engine)["success"])
        backend.qwen_unload_success = False
        backend.release_success = False
        first = engine.dispatch("cleanup", {"reason": "first bounded cleanup"})
        self.assertFalse(first["success"])
        self.assertTrue(first["cleanup_debt"])
        self.assertIsNotNone(engine.qwen_binding)
        backend.qwen_unload_success = True
        backend.release_success = True
        second = engine.dispatch("cleanup", {"reason": "bounded retry"})
        self.assertTrue(second["success"])
        self.assertFalse(second["cleanup_debt"])
        self.assertIsNone(engine.qwen_binding)
        self.assertEqual(engine.state.value, "UNLOADED")

    def test_22a_qwen_appearance_during_cleanup_is_debt_not_false_success(self):
        engine, backend, _ = self.make_engine()
        self.assertTrue(self.load(engine)["success"])
        backend.qwen_race_phase = "cleanup_qwen_absence"
        backend.qwen_race_mode = "extra"
        result = engine.dispatch("cleanup", {"reason": "unowned cleanup race"})
        self.assertFalse(result["success"])
        self.assertTrue(result["cleanup_debt"])

        engine, backend, _ = self.make_engine()
        self.assertTrue(self.load(engine)["success"])
        self.assertTrue(self.park(engine)["success"])
        self.assertTrue(self.qwen_load(engine)["success"])
        backend.qwen_race_phase = "cleanup_after_qwen_unload"
        backend.qwen_race_mode = "extra"
        result = engine.dispatch("cleanup", {"reason": "owned cleanup race"})
        self.assertFalse(result["success"])
        self.assertTrue(result["cleanup_debt"])
        self.assertIsNotNone(engine.qwen_binding)

    def test_22b_malformed_cleanup_probe_returns_bounded_debt_and_can_retry(self):
        engine, backend, _ = self.make_engine()
        self.assertTrue(self.load(engine)["success"])
        self.assertTrue(self.park(engine)["success"])
        self.assertTrue(self.qwen_load(engine)["success"])
        original = backend.qwen_residency
        backend.qwen_residency = lambda **kwargs: {"malformed": True}
        before = time.monotonic()
        result = self.qwen_stream(engine)
        self.assertLess(time.monotonic() - before, 1.0)
        self.assertFalse(result["success"])
        self.assertTrue(result["cleanup"]["cleanup_debt"])
        backend.qwen_residency = original
        retry = engine.dispatch("cleanup", {"reason": "retry after malformed probe"})
        self.assertTrue(retry["success"])


class V6ArtifactAndCudaHostileTests(EngineCase):
    def synthesize(self):
        engine, backend, clock = self.make_engine()
        self.assertTrue(self.load(engine)["success"])
        result = engine.dispatch("synthesis", self.synthesis_payload(engine))
        return engine, backend, clock, result

    def test_23_wav_handle_path_hash_pcm_and_playback_false_are_bound(self):
        engine, backend, _, result = self.synthesize()
        self.assertTrue(result["success"])
        lease = result["artifact_lease"]
        self.assertTrue(Path(lease["resolved_path"]).is_file())
        self.assertEqual(worker.sha256_file(Path(lease["resolved_path"])), lease["artifact_sha256"])
        self.assertGreater(lease["absolute_pcm_peak"], 0)
        self.assertEqual(lease["consumer_contract"], "same_worker_retained_bytes_only_playback_not_implemented")
        self.assertFalse(result["playback_implemented"])
        status = engine.dispatch(
            "artifact_status",
            {key: lease[key] for key in ("handle_id", "artifact_sha256", "generation_id")},
        )
        self.assertTrue(status["success"])
        self.assertTrue(status["retained_bytes_authoritative"])
        self.assertFalse(status["playback_implemented"])
        self.assertIs(backend.last_synthesis_kwargs["model"], engine.model)

    def test_24_postverify_wav_mutation_is_detected_without_mutating_retained_bytes(self):
        engine, _, _, result = self.synthesize()
        self.assertTrue(result["success"])
        lease = result["artifact_lease"]
        retained_before = bytes(engine.retained_artifact["retained_bytes"])
        Path(lease["resolved_path"]).write_bytes(b"mutated")
        status = engine.dispatch(
            "artifact_status",
            {key: lease[key] for key in ("handle_id", "artifact_sha256", "generation_id")},
        )
        self.assertFalse(status["success"])
        self.assertEqual(engine.retained_artifact["retained_bytes"], retained_before)
        self.assertEqual(hashlib.sha256(retained_before).hexdigest(), lease["artifact_sha256"])

    def test_25_future_cuda_evidence_silent_wav_and_route_substitution_fail(self):
        for mode in ("future_cuda", "silent", "generic"):
            with self.subTest(mode=mode):
                engine, backend, _ = self.make_engine()
                self.assertTrue(self.load(engine)["success"])
                if mode == "future_cuda":
                    backend.cuda_mode = "future"
                elif mode == "silent":
                    backend.artifact_mode = "silent"
                else:
                    original = backend.synthesize_cuda

                    def generic(**kwargs):
                        value = original(**kwargs)
                        value["route"] = "generic"
                        value["generic_voice_used"] = True
                        return value

                    backend.synthesize_cuda = generic
                result = engine.dispatch("synthesis", self.synthesis_payload(engine))
                self.assertFalse(result["success"])

    def test_26_cuda_and_wav_evidence_bind_exact_generation_object_and_prompt(self):
        engine, backend, _, result = self.synthesize()
        self.assertTrue(result["success"])
        cuda = result["cuda_execution"]
        self.assertEqual(cuda["model_generation"], engine.model_generation)
        self.assertEqual(cuda["model_object_id"], id(engine.model))
        self.assertEqual(cuda["backend_object_id"], id(backend))
        self.assertEqual(cuda["worker_instance_id"], INSTANCE)
        self.assertEqual(cuda["worker_pid"], os.getpid())
        self.assertEqual(cuda["device"], "cuda")
        self.assertGreater(cuda["peak_allocated_bytes"], cuda["allocated_before_bytes"])
        self.assertEqual(
            backend.last_load_kwargs["approved_audio_prompt_sha256"],
            worker.EXACT_REFERENCE_SHA256,
        )
        self.assertEqual(
            backend.last_synthesis_kwargs["approved_audio_prompt_sha256"],
            worker.EXACT_REFERENCE_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
