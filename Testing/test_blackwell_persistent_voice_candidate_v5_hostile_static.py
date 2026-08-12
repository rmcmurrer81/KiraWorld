import ast
import hashlib
import json
import math
import shutil
import tempfile
import threading
import time
import unittest
import wave
from pathlib import Path

from Core import persistent_blackwell_voice_integration_v5 as integration
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v5 import (
    persistent_worker as worker,
)


ROOT = Path(__file__).resolve().parents[1]
LEASE = hashlib.sha256(b"v5-static-exclusive-serialization-lease").hexdigest()
TOKEN = "v5-owner-capability-token-000000000001"


class FakeTensor:
    def __init__(self, device: str, payload: bytes, shape=(2, 2), dtype="float32"):
        self.device = device
        self.payload = payload
        self.shape = shape
        self.dtype = dtype

    def to(self, device: str):
        self.device = device
        return self

    def detach(self):
        return self

    def cpu(self):
        return self.to("cpu")

    def contiguous(self):
        return self

    def content_bytes(self):
        return self.payload


class FakeModule:
    def __init__(self, name: str, device="cuda"):
        self.tensor = FakeTensor(device, name.encode("utf-8"))

    def parameters(self):
        return [self.tensor]

    def buffers(self):
        return []

    def to(self, device: str):
        self.tensor.to(device)
        return self


class FakeConditionGroup:
    def __init__(self, device="cuda"):
        self.token = FakeTensor(device, b"condition-token")

    def to(self, device: str):
        self.token.to(device)
        return self


class FakeConditions:
    def __init__(self, device="cuda"):
        self.t3 = FakeConditionGroup(device)

    def to(self, device: str):
        self.t3.to(device)
        return self


class FakeModel:
    def __init__(self):
        self.t3 = FakeModule("t3")
        self.s3gen = FakeModule("s3gen")
        self.ve = FakeModule("ve")
        self.conds = FakeConditions()
        self.device = "cuda"


class FakeKillableBoundary:
    contract_version = "killable_child_v1"
    enforces_process_termination = True

    def __init__(self):
        self.timeout_operations = set()
        self.calls = []

    def invoke(self, *, operation, timeout_seconds, callback):
        self.calls.append((operation, float(timeout_seconds)))
        if operation in self.timeout_operations:
            return {
                "operation": operation,
                "completed": False,
                "timed_out": True,
                "child_terminated": True,
                "elapsed_seconds": float(timeout_seconds),
                "value": None,
                "error_type": "TimeoutError",
                "error": "static hostile timeout",
            }
        started = time.perf_counter()
        try:
            value = callback()
            error_type = None
            error = None
        except Exception as exc:
            value = None
            error_type = type(exc).__name__
            error = str(exc)
        return {
            "operation": operation,
            "completed": True,
            "timed_out": False,
            "child_terminated": False,
            "elapsed_seconds": min(time.perf_counter() - started, float(timeout_seconds)),
            "value": value,
            "error_type": error_type,
            "error": error,
        }


def resource_snapshot(sequence, now, kind="baseline", **overrides):
    if kind == "loaded":
        values = {
            "process_rss_mib": 7000.0,
            "system_commit_used_mib": 16000.0,
            "system_commit_limit_mib": 40000.0,
            "available_physical_mib": 9000.0,
            "total_physical_mib": 32000.0,
            "system_commit_fraction": 0.4,
            "cuda_allocated_bytes": 3_500_000_000.0,
            "cuda_reserved_bytes": 3_800_000_000.0,
            "cuda_free_mib": 8000.0,
            "cuda_total_mib": 16000.0,
        }
    else:
        values = {
            "process_rss_mib": 1000.0,
            "system_commit_used_mib": 12000.0,
            "system_commit_limit_mib": 40000.0,
            "available_physical_mib": 12000.0,
            "total_physical_mib": 32000.0,
            "system_commit_fraction": 0.3,
            "cuda_allocated_bytes": 0.0,
            "cuda_reserved_bytes": 0.0,
            "cuda_free_mib": 15000.0,
            "cuda_total_mib": 16000.0,
        }
    values.update(overrides)
    values.update(
        {
            "sample_id": hashlib.sha256(f"resource-{sequence}-{kind}".encode()).hexdigest(),
            "sample_sequence": sequence,
            "pid": 4242,
            "cuda_device_name": worker.EXACT_CUDA_DEVICE_NAME,
            "compute_capability": [12, 0],
            "captured_monotonic": float(now),
        }
    )
    return values


class FakeQwenBackend:
    def __init__(self, factory):
        self.factory = factory
        self.records = factory.qwen_records
        self.residency_sequence = 0
        self.load_entered = threading.Event()
        self.release_load = threading.Event()
        self.block_load = False
        self.ignore_cancel = False
        self.load_cancel_event = None
        self.unload_success = True
        self.retain_on_unload = False

    def residency(self, *, phase):
        self.residency_sequence += 1
        return {
            "query_succeeded": True,
            "records": list(self.records),
            "serialization_lease_id": LEASE,
            "lease_exclusive": True,
            "sample_id": hashlib.sha256(
                f"residency-{self.residency_sequence}-{phase}".encode()
            ).hexdigest(),
            "sample_sequence": self.residency_sequence,
            "captured_monotonic": self.factory.now(),
            "phase": phase,
        }

    def load_only(self, request, *, token, cancel_event):
        self.load_cancel_event = cancel_event
        self.load_entered.set()
        if self.block_load:
            while not self.release_load.wait(0.005):
                if cancel_event.is_set() and not self.ignore_cancel:
                    break
        if cancel_event.is_set() and not self.ignore_cancel:
            return {
                "model": worker.EXACT_QWEN_MODEL,
                "digest": worker.EXACT_QWEN_DIGEST,
                "request_hash": integration._hash_json(request),
                "response": "",
                "message": {"content": ""},
                "eval_count": 0,
                "prompt_eval_count": 0,
                "serialization_lease_id": LEASE,
            }
        self.records[:] = [
            {"model": worker.EXACT_QWEN_MODEL, "digest": worker.EXACT_QWEN_DIGEST}
        ]
        return {
            "model": worker.EXACT_QWEN_MODEL,
            "digest": worker.EXACT_QWEN_DIGEST,
            "request_hash": integration._hash_json(request),
            "response": "",
            "message": {"content": ""},
            "eval_count": 0,
            "prompt_eval_count": 0,
            "serialization_lease_id": LEASE,
        }

    def stream_real(self, request, *, token, cancel_event):
        chunks = ["Natural ", "reply."]
        self.records[:] = []
        text = "".join(chunks)
        return {
            "model": worker.EXACT_QWEN_MODEL,
            "digest": worker.EXACT_QWEN_DIGEST,
            "request_hash": integration._hash_json(request),
            "chunks": chunks,
            "final_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "keep_alive": 0,
            "serialization_lease_id": LEASE,
        }

    def cancel_owned(self, *, token):
        if self.load_cancel_event is not None:
            self.load_cancel_event.set()
        self.release_load.set()
        self.records[:] = []
        return {
            "cancelled": True,
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "serialization_lease_id": LEASE,
        }

    def unload_owned(self, *, token, model, digest):
        if self.unload_success and not self.retain_on_unload:
            self.records[:] = []
        return {
            "unloaded": self.unload_success,
            "model": model,
            "digest": digest,
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "serialization_lease_id": LEASE,
        }


class RuntimeFactory:
    def __init__(self):
        self.clock = [1000.0]
        self.model = FakeModel()
        self.boundary = FakeKillableBoundary()
        self.active = False
        self.released = False
        self.resource_sequence = 0
        self.resource_override = None
        self.qwen_sequence = 0
        self.qwen_records = []
        self.qwen_race_phase = None
        self.qwen = FakeQwenBackend(self)
        root = ROOT / "RecoverySprint/runtime_cache/blackwell_chatterbox/v5_outputs"
        root.mkdir(parents=True, exist_ok=True)
        self.output_dir = Path(tempfile.mkdtemp(prefix="static_", dir=root))
        self.artifact_mode = "valid"
        self.cuda_mode = "valid"
        self.last_synthesis_kwargs = None

    def close(self):
        shutil.rmtree(self.output_dir, ignore_errors=True)

    def now(self):
        return self.clock[0]

    def qwen_probe(self, phase):
        self.qwen_sequence += 1
        if phase == self.qwen_race_phase:
            self.qwen_records[:] = [
                {"model": worker.EXACT_QWEN_MODEL, "digest": worker.EXACT_QWEN_DIGEST}
            ]
        return {
            "query_succeeded": True,
            "target_model": worker.EXACT_QWEN_MODEL,
            "target_digest": worker.EXACT_QWEN_DIGEST,
            "records": list(self.qwen_records),
            "model_state_changed": False,
            "serialization_lease_id": LEASE,
            "lease_exclusive": True,
            "sample_id": hashlib.sha256(
                f"qwen-{self.qwen_sequence}-{phase}".encode()
            ).hexdigest(),
            "sample_sequence": self.qwen_sequence,
            "captured_monotonic": self.now(),
            "phase": phase,
        }

    def resources(self):
        self.resource_sequence += 1
        if self.resource_override is not None:
            value = dict(self.resource_override)
            value["sample_sequence"] = self.resource_sequence
            value["sample_id"] = hashlib.sha256(
                f"override-{self.resource_sequence}".encode()
            ).hexdigest()
            value["captured_monotonic"] = self.now()
            return value
        kind = "loaded" if self.active and not self.released and self.model.device == "cuda" else "baseline"
        return resource_snapshot(self.resource_sequence, self.now(), kind)

    def loader(self, config):
        self.active = True
        self.released = False
        if self.qwen_race_phase == "loader":
            self.qwen_records[:] = [
                {"model": worker.EXACT_QWEN_MODEL, "digest": worker.EXACT_QWEN_DIGEST}
            ]
        return {
            "model": self.model,
            "backend": {
                "synthesize_cuda": self.synthesize,
                "cuda_execution_evidence": self.cuda_evidence,
                "release_owned": self.release,
            },
            "identity": worker.verify_identity_files(),
            "load_proof": {
                "from_pretrained_call_count": 1,
                "prepare_conditionals_call_count": 1,
                "approved_audio_prompt_path": str((ROOT / worker.EXACT_REFERENCE_PATH).resolve()),
                "approved_audio_prompt_sha256": worker.EXACT_REFERENCE_SHA256,
                "serialization_lease_id": LEASE,
            },
        }

    @staticmethod
    def cache():
        return {
            "resampler_cache": {"cleared": True},
            "mel_basis": {"cleared": True},
            "hann_window": {"cleared": True},
        }

    @staticmethod
    def cuda():
        return {
            "synchronize_before": True,
            "empty_cache_called": True,
            "synchronize_after": True,
        }

    def release(self):
        self.released = True
        self.active = False
        return {"released": True, "owned_model_count": 0, "owned_condition_count": 0}

    def _write_wav(self, path, silent=False):
        samples = ([0] * 1600) if silent else ([0, 1200, -1200, 600, -600] * 320)
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(16000)
            payload = b"".join(int(value).to_bytes(2, "little", signed=True) for value in samples)
            handle.writeframes(payload)

    def synthesize(self, **kwargs):
        self.last_synthesis_kwargs = dict(kwargs)
        generation_id = kwargs["generation_id"]
        if self.artifact_mode == "missing":
            path = self.output_dir / "missing.wav"
            artifact_sha = "0" * 64
        elif self.artifact_mode == "outside":
            path = Path(tempfile.gettempdir()) / "v5_outside.wav"
            self._write_wav(path)
            artifact_sha = worker.sha256_file(path)
        else:
            path = self.output_dir / f"{generation_id}.wav"
            self._write_wav(path, silent=self.artifact_mode == "silent")
            artifact_sha = worker.sha256_file(path)
        if self.artifact_mode == "bad_hash":
            artifact_sha = "0" * 64
        return {
            "artifact_path": str(path.resolve()),
            "artifact_sha256": artifact_sha,
            "generation_id": generation_id,
            "text_sha256": kwargs["text_sha256"],
            "prompt_path": kwargs["approved_audio_prompt_path"],
            "prompt_sha256": kwargs["approved_audio_prompt_sha256"],
            "route": "blackwell_gpu",
            "device": "cuda",
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "generation_started_monotonic": 999.9,
            "generation_ended_monotonic": 1000.0,
        }

    def cuda_evidence(self, **kwargs):
        generation_id = kwargs["generation_id"]
        if self.cuda_mode == "stale_generation":
            generation_id = "0" * 64
        return {
            "generation_id": generation_id,
            "text_sha256": kwargs["text_sha256"],
            "artifact_sha256": kwargs["artifact_sha256"],
            "device": "cuda",
            "cuda_device_name": worker.EXACT_CUDA_DEVICE_NAME,
            "compute_capability": [12, 0],
            "allocated_before_bytes": 100,
            "peak_allocated_bytes": 1000,
            "allocated_after_bytes": 120,
            "synchronize_before": True,
            "synchronize_after": True,
            "unsupported_architecture_warning": False,
            "no_kernel_image_error": False,
            "sample_start_monotonic": 999.8,
            "sample_end_monotonic": 1000.0,
        }

    def runtime(self):
        return worker.PersistentVoiceRuntimeV5(
            loader=self.loader,
            qwen_probe=self.qwen_probe,
            resource_probe=self.resources,
            cache_clearer=self.cache,
            cuda_cleanup=self.cuda,
            call_boundary=self.boundary,
            serialization_lease_id=LEASE,
            now=self.now,
            allow_inactive_static_execution=True,
        )

    def load(self):
        runtime = self.runtime()
        result = runtime.load_initial("static-owner")
        if not result["loaded"]:
            raise AssertionError(result)
        return runtime


def exact_request(runtime):
    text = "Exact approved public SPOKEN test."
    return {
        "text": text,
        "text_sha256": worker.sha256_text(text),
        "input_channel": "public_spoken_only",
        "profile_sha256": worker.EXACT_PROFILE_SHA256,
        "reference_sha256": worker.EXACT_REFERENCE_SHA256,
        "condition_digest": runtime.condition_digest,
    }


class FactoryCase(unittest.TestCase):
    def setUp(self):
        self.factories = []

    def factory(self):
        value = RuntimeFactory()
        self.factories.append(value)
        return value

    def tearDown(self):
        for value in self.factories:
            value.close()


class V5CanonicalBoundaryAndPolicyTests(FactoryCase):
    def test_v2_v3_v4_and_identity_baselines_are_exact(self):
        config = worker.load_canonical_config()
        observed = worker.verify_preserved_baselines(config)
        expected = sum(
            len(config[key])
            for key in ("sealed_v2_baseline", "sealed_v3_rejected_baseline", "sealed_v4_rejected_baseline")
        )
        self.assertEqual(len(observed), expected)
        self.assertEqual(worker.verify_identity_files()["reference_sha256"], worker.EXACT_REFERENCE_SHA256)

    def test_v5_has_no_top_level_torch_chatterbox_or_ollama_import(self):
        for relative in (
            "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v5/persistent_worker.py",
            "Core/persistent_blackwell_voice_integration_v5.py",
        ):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            imports = []
            for node in tree.body:
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(any(name.startswith(("torch", "chatterbox", "ollama")) for name in imports))

    def test_boundary_is_mandatory_and_timeout_requires_termination_proof(self):
        factory = self.factory()
        with self.assertRaises(worker.V5ContractError):
            worker.PersistentVoiceRuntimeV5(
                qwen_probe=factory.qwen_probe,
                resource_probe=factory.resources,
                cache_clearer=factory.cache,
                cuda_cleanup=factory.cuda,
                call_boundary=object(),
                serialization_lease_id=LEASE,
                allow_inactive_static_execution=True,
            )
        bad = FakeKillableBoundary()
        bad.enforces_process_termination = False
        with self.assertRaises(worker.V5ContractError):
            worker.PersistentVoiceRuntimeV5(
                qwen_probe=factory.qwen_probe,
                resource_probe=factory.resources,
                cache_clearer=factory.cache,
                cuda_cleanup=factory.cuda,
                call_boundary=bad,
                serialization_lease_id=LEASE,
                allow_inactive_static_execution=True,
            )

    def test_public_config_mutation_cannot_weaken_resource_bounds(self):
        factory = self.factory()
        runtime = factory.load()
        detached = runtime.config
        detached["resource_bounds"]["minimum_available_physical_mib_before_park"] = 0
        detached["resource_bounds"]["maximum_system_commit_fraction"] = 1.0
        factory.resource_override = resource_snapshot(
            99,
            factory.now(),
            "baseline",
            available_physical_mib=1.0,
            system_commit_used_mib=39600.0,
            system_commit_fraction=0.99,
        )
        result = runtime.park_cpu("hostile")
        self.assertFalse(result["parked"])
        self.assertNotEqual(runtime.state, worker.VoiceState.PARKED_CPU)

    def test_internal_policy_digest_drift_with_loaded_cuda_fails_closed(self):
        factory = self.factory()
        runtime = factory.load()
        runtime._policy_digest = "0" * 64
        result = runtime.park_cpu("policy_drift")
        self.assertFalse(result["parked"])
        self.assertIn("policy", result["error"].lower())
        self.assertEqual(runtime.state, worker.VoiceState.UNLOADED)
        self.assertIsNone(runtime.model)

    def test_resource_replay_and_stale_snapshot_are_rejected(self):
        now = 1000.0
        value = resource_snapshot(1, now, "baseline")
        worker.validate_resource_snapshot(value, label="fresh", now_monotonic=now, maximum_age_seconds=2)
        stale = resource_snapshot(2, now - 10, "baseline")
        with self.assertRaises(worker.V5ContractError):
            worker.validate_resource_snapshot(stale, label="stale", now_monotonic=now, maximum_age_seconds=2)


class V5QwenRaceAndCleanupTests(FactoryCase):
    def test_initial_load_race_never_commits_loaded_cuda(self):
        for phase in ("loader", "initial_cuda_transition_precommit", "initial_cuda_transition_after"):
            with self.subTest(phase=phase):
                factory = self.factory()
                factory.qwen_race_phase = phase
                runtime = factory.runtime()
                result = runtime.load_initial("owner")
                self.assertFalse(result["loaded"], result)
                self.assertNotEqual(runtime.state, worker.VoiceState.LOADED_CUDA)
                self.assertIsNone(runtime.model)

    def test_resume_race_never_commits_or_retains_loaded_cuda(self):
        for phase in ("resume_cuda_transition_precommit", "resume_cuda_transition_after"):
            with self.subTest(phase=phase):
                factory = self.factory()
                runtime = factory.load()
                self.assertTrue(runtime.park_cpu("qwen")["parked"])
                factory.qwen_race_phase = phase
                result = runtime.resume_cuda("voice")
                self.assertFalse(result["resumed"], result)
                self.assertNotEqual(runtime.state, worker.VoiceState.LOADED_CUDA)
                self.assertIsNone(runtime.model)

    def _coordinator(self):
        factory = self.factory()
        runtime = factory.load()
        self.assertTrue(runtime.park_cpu("qwen")["parked"])
        coordinator = integration.QwenVoiceSerializationV5(
            voice=runtime, qwen_backend=factory.qwen, now=factory.now
        )
        started = coordinator.start_load_only(owner="owner", session="session", token=TOKEN)
        self.assertTrue(started["started"], started)
        waited = coordinator.wait_load_only()
        self.assertTrue(waited["result"]["loaded"], waited)
        return factory, runtime, coordinator

    def test_malformed_or_empty_stream_fails_closed_without_stranded_state(self):
        cases = (None, [], [{"role": "user"}], [{"role": "user", "content": ""}])
        for messages in cases:
            with self.subTest(messages=messages):
                factory, runtime, coordinator = self._coordinator()
                result = coordinator.run_real_stream(
                    owner="owner",
                    session="session",
                    token=TOKEN,
                    messages=messages,
                    consume_chunk=lambda _value: None,
                )
                self.assertFalse(result["completed"])
                self.assertEqual(coordinator.state, integration.QwenOperationState.NONE)
                self.assertIsNone(coordinator.owned)
                self.assertEqual(factory.qwen_records, [])
                self.assertEqual(runtime.state, worker.VoiceState.UNLOADED)
                self.assertTrue(coordinator._operation_done.is_set())

    def test_valid_stream_is_nonempty_and_bound_to_exact_model_digest(self):
        _factory, _runtime, coordinator = self._coordinator()
        received = []
        result = coordinator.run_real_stream(
            owner="owner",
            session="session",
            token=TOKEN,
            messages=[{"role": "user", "content": "Hello"}],
            consume_chunk=received.append,
        )
        self.assertTrue(result["completed"], result)
        self.assertEqual(result["text"], "Natural reply.")
        self.assertEqual(result["response_model"], worker.EXACT_QWEN_MODEL)
        self.assertEqual(result["response_digest"], worker.EXACT_QWEN_DIGEST)
        self.assertEqual(received, ["Natural ", "reply."])

    def test_backend_cancel_timeout_returns_bounded_cleanup_debt(self):
        factory = self.factory()
        runtime = factory.load()
        self.assertTrue(runtime.park_cpu("qwen")["parked"])
        factory.qwen.block_load = True
        factory.qwen.ignore_cancel = True
        coordinator = integration.QwenVoiceSerializationV5(
            voice=runtime, qwen_backend=factory.qwen, now=factory.now
        )
        self.assertTrue(
            coordinator.start_load_only(owner="owner", session="session", token=TOKEN)["started"]
        )
        self.assertTrue(factory.qwen.load_entered.wait(1.0))
        factory.boundary.timeout_operations.add("qwen_cancel")
        began = time.perf_counter()
        result = coordinator.cancel_owned(
            owner="owner", session="session", token=TOKEN, reason="chat_closed"
        )
        elapsed = time.perf_counter() - began
        self.assertLess(elapsed, 0.5)
        self.assertFalse(result["cleaned"])
        self.assertTrue(result["cleanup_debt"])
        self.assertEqual(result["reason"], "bounded_backend_cancel_failed")
        self.assertEqual(coordinator.state, integration.QwenOperationState.CLEANUP_DEBT)
        factory.qwen.ignore_cancel = False
        factory.qwen.release_load.set()
        coordinator._operation_done.wait(1.0)
        self.assertEqual(coordinator.state, integration.QwenOperationState.NONE)
        self.assertIsNone(coordinator.owned)
        self.assertEqual(factory.qwen_records, [])
        self.assertEqual(runtime.state, worker.VoiceState.UNLOADED)

    def test_each_external_operation_timeout_is_non_success_or_cleanup_debt(self):
        factory = self.factory()
        runtime = factory.runtime()
        factory.boundary.timeout_operations.add("loader")
        load = runtime.load_initial("owner")
        self.assertFalse(load["loaded"])
        self.assertNotEqual(runtime.state, worker.VoiceState.LOADED_CUDA)

        factory = self.factory()
        runtime = factory.load()
        factory.boundary.timeout_operations.add("tensor_move")
        park = runtime.park_cpu("timeout")
        self.assertFalse(park["parked"])
        self.assertNotEqual(runtime.state, worker.VoiceState.LOADED_CUDA)

        factory = self.factory()
        runtime = factory.load()
        factory.boundary.timeout_operations.add("cuda_execution_evidence")
        generated = runtime.synthesize(exact_request(runtime))
        self.assertFalse(generated["generated"])
        self.assertNotEqual(runtime.state, worker.VoiceState.LOADED_CUDA)

        factory = self.factory()
        runtime = factory.load()
        factory.boundary.timeout_operations.add("release_owned")
        unloaded = runtime.full_unload("timeout")
        self.assertFalse(unloaded["unloaded"])
        self.assertTrue(unloaded["cleanup_debt"])
        self.assertIsNone(runtime.model)

    def test_cleanup_debt_has_explicit_retry(self):
        factory, _runtime, coordinator = self._coordinator()
        factory.qwen.unload_success = False
        factory.qwen.retain_on_unload = True
        failed = coordinator.cancel_owned(
            owner="owner", session="session", token=TOKEN, reason="chat_closed"
        )
        self.assertTrue(failed["cleanup_debt"])
        factory.qwen.unload_success = True
        factory.qwen.retain_on_unload = False
        recovered = coordinator.recover_cleanup_debt(
            owner="owner", session="session", token=TOKEN
        )
        self.assertTrue(recovered["recovered"], recovered)
        self.assertIsNone(coordinator.owned)


class V5ArtifactAndGenerationTests(FactoryCase):
    def test_real_owned_readable_non_silent_wav_and_generation_cuda_binding_pass(self):
        factory = self.factory()
        runtime = factory.load()
        result = runtime.synthesize(exact_request(runtime))
        self.assertTrue(result["generated"], result)
        self.assertGreater(result["wav_verification"]["absolute_pcm_peak"], 0)
        self.assertEqual(
            result["wav_verification"]["artifact_sha256"],
            result["cuda_execution"]["artifact_sha256"],
        )
        self.assertEqual(result["generation_id"], result["cuda_execution"]["generation_id"])
        self.assertEqual(factory.last_synthesis_kwargs["text"], "Exact approved public SPOKEN test.")
        self.assertEqual(factory.last_synthesis_kwargs["serialization_lease_id"], LEASE)

    def test_nonexistent_outside_bad_hash_and_silent_artifacts_fail_closed(self):
        for mode in ("missing", "outside", "bad_hash", "silent"):
            with self.subTest(mode=mode):
                factory = self.factory()
                factory.artifact_mode = mode
                runtime = factory.load()
                result = runtime.synthesize(exact_request(runtime))
                self.assertFalse(result["generated"], result)
                self.assertNotEqual(runtime.state, worker.VoiceState.LOADED_CUDA)
                self.assertIsNone(runtime.model)

    def test_stale_or_wrong_generation_cuda_evidence_fails_closed(self):
        factory = self.factory()
        factory.cuda_mode = "stale_generation"
        runtime = factory.load()
        result = runtime.synthesize(exact_request(runtime))
        self.assertFalse(result["generated"])
        self.assertIn("generation", result["error"].lower())
        self.assertNotEqual(runtime.state, worker.VoiceState.LOADED_CUDA)

    def test_synthesis_timeout_is_bounded_and_never_accepts_artifact(self):
        factory = self.factory()
        runtime = factory.load()
        factory.boundary.timeout_operations.add("synthesis")
        result = runtime.synthesize(exact_request(runtime))
        self.assertFalse(result["generated"])
        self.assertIn("terminated", result["error"])
        self.assertNotEqual(runtime.state, worker.VoiceState.LOADED_CUDA)

    def test_all_happy_path_adapters_cross_named_bounded_boundary(self):
        factory = self.factory()
        runtime = factory.load()
        self.assertTrue(runtime.park_cpu("qwen")["parked"])
        self.assertTrue(runtime.resume_cuda("voice")["resumed"])
        self.assertTrue(runtime.synthesize(exact_request(runtime))["generated"])
        self.assertTrue(runtime.full_unload("done")["unloaded"])
        called = {name for name, _bound in factory.boundary.calls}
        self.assertTrue(
            {
                "loader",
                "qwen_probe",
                "resource_probe",
                "tensor_move",
                "cache_clear",
                "cuda_cleanup",
                "synthesis",
                "cuda_execution_evidence",
                "release_owned",
            }.issubset(called)
        )


class V5StaticAuthorizationTests(unittest.TestCase):
    def test_candidate_remains_default_off_without_playback_or_production_authority(self):
        self.assertFalse(integration.PRODUCTION_ROUTING_AUTHORIZED)
        self.assertFalse(integration.PLAYBACK_IMPLEMENTED)
        config = worker.load_canonical_config()
        self.assertFalse(config["live_execution_authorized"])
        self.assertFalse(config["playback_authorized"])
        self.assertFalse(config["production_routing_authorized"])
        self.assertIsNone(config["automatic_fallback_inside_candidate"])


if __name__ == "__main__":
    unittest.main()
