from __future__ import annotations

import ast
import copy
import importlib
import math
import threading
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
worker = importlib.import_module(
    "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v4.persistent_worker"
)
integration = importlib.import_module("Core.persistent_blackwell_voice_integration_v4")
TOKEN = "v4-owner-capability-token-000000000001"


class FakeTensor:
    def __init__(self, device: str, payload: bytes, *, shape=(2, 2), dtype="float32") -> None:
        self.device = device
        self.payload = bytes(payload)
        self.shape = tuple(shape)
        self.dtype = dtype

    def to(self, device: str):
        self.device = str(device)
        return self

    def detach(self):
        return self

    def cpu(self):
        return FakeTensor("cpu", self.payload, shape=self.shape, dtype=self.dtype)

    def contiguous(self):
        return self

    def content_bytes(self):
        return self.payload


class FakeModule:
    def __init__(self, name: str, device="cuda", refuse=None) -> None:
        self.name = name
        self.refuse = refuse
        self.params = [FakeTensor(device, f"{name}-parameter".encode())]
        self.bufs = [FakeTensor(device, f"{name}-buffer".encode())]

    def parameters(self):
        return list(self.params)

    def buffers(self):
        return list(self.bufs)

    def to(self, device: str):
        if device != self.refuse:
            for value in self.params + self.bufs:
                value.to(device)
        return self


class FakeConditionGroup:
    def __init__(self, device="cuda") -> None:
        self.speaker = FakeTensor(device, b"speaker")
        self.prompt = FakeTensor(device, b"prompt", shape=(1, 4))

    def to(self, device: str):
        self.speaker.to(device)
        self.prompt.to(device)
        return self


class FakeConditions:
    def __init__(self, device="cuda") -> None:
        self.t3 = FakeConditionGroup(device)
        self.gen = {"embedding": FakeTensor(device, b"embedding", shape=(1, 8))}

    def to(self, device: str):
        self.t3.to(device)
        for value in self.gen.values():
            value.to(device)
        return self


class FakeModel:
    def __init__(self, *, refuse_component: str | None = None) -> None:
        self.device = "cuda"
        self.t3 = FakeModule("t3", refuse="cpu" if refuse_component == "t3" else None)
        self.s3gen = FakeModule(
            "s3gen", refuse="cpu" if refuse_component == "s3gen" else None
        )
        self.ve = FakeModule("ve", refuse="cpu" if refuse_component == "ve" else None)
        self.conds = FakeConditions()


def snapshot(kind="baseline", **overrides):
    values = {
        "baseline": {
            "process_rss_mib": 1000.0,
            "system_commit_used_mib": 16000.0,
            "system_commit_limit_mib": 40000.0,
            "available_physical_mib": 16000.0,
            "total_physical_mib": 32768.0,
            "system_commit_fraction": 0.4,
            "cuda_allocated_bytes": 100.0,
            "cuda_reserved_bytes": 200.0,
            "cuda_free_mib": 15000.0,
            "cuda_total_mib": 16384.0,
        },
        "loaded": {
            "process_rss_mib": 5000.0,
            "system_commit_used_mib": 22000.0,
            "system_commit_limit_mib": 40000.0,
            "available_physical_mib": 10000.0,
            "total_physical_mib": 32768.0,
            "system_commit_fraction": 0.55,
            "cuda_allocated_bytes": 3_500_000_000.0,
            "cuda_reserved_bytes": 4_000_000_000.0,
            "cuda_free_mib": 11000.0,
            "cuda_total_mib": 16384.0,
        },
        "parked": {
            "process_rss_mib": 8000.0,
            "system_commit_used_mib": 25000.0,
            "system_commit_limit_mib": 40000.0,
            "available_physical_mib": 7000.0,
            "total_physical_mib": 32768.0,
            "system_commit_fraction": 0.625,
            "cuda_allocated_bytes": 100.0,
            "cuda_reserved_bytes": 200.0,
            "cuda_free_mib": 15000.0,
            "cuda_total_mib": 16384.0,
        },
    }[kind]
    values.update(overrides)
    return values


class MutableProbe:
    def __init__(self) -> None:
        self.current = snapshot("baseline")
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return dict(self.current)


class FakeQwenBackend:
    def __init__(self) -> None:
        self.records: list[dict] = []
        self.load_response = {"response": "", "eval_count": 0, "prompt_eval_count": 0}
        self.load_requests: list[dict] = []
        self.stream_requests: list[dict] = []
        self.unload_calls: list[dict] = []
        self.cancel_calls: list[str] = []
        self.unload_success = True
        self.retain_on_unload = False
        self.wrong_resident_digest = False
        self.block_load = False
        self.block_stream = False
        self.ignore_cancel = False
        self.keep_after_stream = False
        self.load_entered = threading.Event()
        self.stream_entered = threading.Event()
        self.release_load = threading.Event()
        self.release_stream = threading.Event()
        self.advance_clock: callable | None = None

    def runtime_probe(self):
        return {
            "query_succeeded": True,
            "target_model": worker.EXACT_QWEN_MODEL,
            "target_digest": worker.EXACT_QWEN_DIGEST,
            "records": copy.deepcopy(self.records),
            "model_state_changed": False,
        }

    def residency(self):
        return {"query_succeeded": True, "records": copy.deepcopy(self.records)}

    def load_only(self, request: dict, *, token: str, cancel_event: threading.Event):
        self.load_requests.append(copy.deepcopy(request))
        self.load_entered.set()
        if self.block_load:
            while not self.release_load.wait(0.005):
                if cancel_event.is_set() and not self.ignore_cancel:
                    break
        if callable(self.advance_clock):
            self.advance_clock()
        if not cancel_event.is_set():
            self.records = [
                {
                    "model": worker.EXACT_QWEN_MODEL,
                    "digest": "0" * 64 if self.wrong_resident_digest else worker.EXACT_QWEN_DIGEST,
                }
            ]
        return dict(self.load_response)

    def stream_real(self, request: dict, *, token: str, cancel_event: threading.Event):
        self.stream_requests.append(copy.deepcopy(request))

        def values():
            self.stream_entered.set()
            if self.block_stream:
                while not self.release_stream.wait(0.005):
                    if cancel_event.is_set() and not self.ignore_cancel:
                        break
            if cancel_event.is_set():
                return
            yield "Kira "
            yield "reply"
            if not self.keep_after_stream:
                self.records = []

        return values()

    def cancel_owned(self, *, token: str):
        self.cancel_calls.append(token)
        if not self.ignore_cancel:
            self.release_load.set()
            self.release_stream.set()

    def unload_owned(self, *, token: str, model: str, digest: str):
        call = {"token": token, "model": model, "digest": digest}
        self.unload_calls.append(call)
        if self.unload_success and not self.retain_on_unload:
            self.records = []
        return {
            "unloaded": self.unload_success,
            "model": model,
            "digest": digest,
            "token_hash": worker.sha256_text(token),
        }


class RuntimeFactory:
    def __init__(self, *, model: FakeModel | None = None, clock: list[float] | None = None) -> None:
        self.config = worker.load_canonical_config()
        self.model = model or FakeModel()
        self.clock = clock or [1000.0]
        self.probe = MutableProbe()
        self.qwen = FakeQwenBackend()
        self.cache_calls = 0
        self.cuda_calls = 0
        self.release_calls = 0
        self.release_success = True
        self.cache_failure = False
        self.cuda_failure = False
        self.unload_resource_override: dict | None = None
        self.park_resource_override: dict | None = None
        self.resume_resource_override: dict | None = None
        self.mutate_synthesis: str | None = None
        self.artifact_extra: dict = {}
        self.last_synthesis_kwargs: dict | None = None
        self.advance_loader_seconds = 0.0
        self.advance_cuda_seconds = 0.0
        self.advance_synthesis_seconds = 0.0

    def now(self):
        return self.clock[0]

    def loader(self, _config):
        self.probe.current = snapshot("loaded")
        self.clock[0] += self.advance_loader_seconds
        identity = worker.verify_identity_files()
        return {
            "model": self.model,
            "backend": {
                "synthesize_cuda": self.synthesize,
                "cuda_execution_evidence": self.execution,
                "release_owned": self.release,
            },
            "identity": identity,
            "load_proof": {
                "from_pretrained_call_count": 1,
                "prepare_conditionals_call_count": 1,
                "approved_audio_prompt_path": str(
                    (ROOT / worker.EXACT_REFERENCE_PATH).resolve()
                ),
                "approved_audio_prompt_sha256": worker.EXACT_REFERENCE_SHA256,
            },
        }

    def cache(self):
        self.cache_calls += 1
        if self.cache_failure:
            raise RuntimeError("cache failure")
        return {
            "resampler_cache": {"cleared": True},
            "mel_basis": {"cleared": True},
            "hann_window": {"cleared": True},
        }

    def cuda(self):
        self.cuda_calls += 1
        self.clock[0] += self.advance_cuda_seconds
        if self.cuda_failure:
            raise RuntimeError("cuda cleanup failure")
        if self.release_calls:
            self.probe.current = dict(self.unload_resource_override or snapshot("baseline"))
        elif self.model.device == "cpu":
            self.probe.current = dict(self.park_resource_override or snapshot("parked"))
        else:
            self.probe.current = dict(self.resume_resource_override or snapshot("loaded"))
        return {
            "synchronize_before": True,
            "empty_cache_called": True,
            "synchronize_after": True,
        }

    def release(self):
        self.release_calls += 1
        self.probe.current = dict(self.unload_resource_override or snapshot("baseline"))
        if not self.release_success:
            return {"released": False, "owned_model_count": 1, "owned_condition_count": 1}
        return {"released": True, "owned_model_count": 0, "owned_condition_count": 0}

    def synthesize(self, **kwargs):
        self.last_synthesis_kwargs = dict(kwargs)
        self.clock[0] += self.advance_synthesis_seconds
        if self.mutate_synthesis == "mixed":
            self.model.s3gen.params[0].device = "cpu"
        if self.mutate_synthesis == "condition":
            self.model.conds.gen["embedding"].payload = b"mutated"
        result = {
            "artifact_path": "Voice/generated/static_fake.wav",
            "artifact_sha256": "a" * 64,
            "generation_id": "fake-generation",
            "non_silent": True,
            "wav_valid": True,
        }
        result.update(self.artifact_extra)
        return result

    @staticmethod
    def execution():
        return {
            "allocated_before_bytes": 3_000_000_000,
            "peak_allocated_bytes": 3_500_000_000,
            "synchronize_before": True,
            "synchronize_after": True,
            "unsupported_architecture_warning": False,
            "no_kernel_image_error": False,
        }

    def runtime(self, *, config=None):
        return worker.PersistentVoiceRuntimeV4(
            config=config,
            loader=self.loader,
            qwen_probe=self.qwen.runtime_probe,
            resource_probe=self.probe,
            cache_clearer=self.cache,
            cuda_cleanup=self.cuda,
            now=self.now,
            allow_inactive_static_execution=True,
        )

    def load(self, runtime=None):
        runtime = runtime or self.runtime()
        result = runtime.load_initial("kira-owner")
        if not result.get("loaded"):
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


class V4CanonicalAndResourceTests(unittest.TestCase):
    def test_v2_v3_and_identity_baselines_are_preserved(self):
        config = worker.load_canonical_config()
        observed = worker.verify_preserved_baselines(config)
        self.assertEqual(len(observed), len(config["sealed_v2_baseline"]) + len(config["sealed_v3_rejected_baseline"]))
        identity = worker.verify_identity_files()
        self.assertEqual(identity["profile_sha256"], worker.EXACT_PROFILE_SHA256)
        self.assertEqual(identity["reference_sha256"], worker.EXACT_REFERENCE_SHA256)
        self.assertEqual(identity["audio_prompt_path"], worker.EXACT_REFERENCE_PATH)

    def test_injected_qwen_or_route_config_is_rejected_before_any_load(self):
        for field, value in (
            ("qwen_model", "llama3.1:8b"),
            ("qwen_digest", "0" * 64),
            ("generic_voice_allowed", True),
            ("sapi_allowed", True),
            ("compute_device", "cpu"),
            ("approved_audio_prompt", "unapproved.wav"),
        ):
            with self.subTest(field=field):
                config = worker.load_canonical_config()
                config[field] = value
                with self.assertRaises(worker.V4ContractError):
                    RuntimeFactory().runtime(config=config)

    def test_worker_has_no_top_level_torch_chatterbox_or_ollama_import(self):
        path = ROOT / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v4/persistent_worker.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any(name.startswith(("torch", "chatterbox", "ollama")) for name in imports))

    def test_nonfinite_negative_and_inconsistent_resources_are_rejected(self):
        cases = []
        for key in (
            "process_rss_mib",
            "available_physical_mib",
            "system_commit_fraction",
            "cuda_allocated_bytes",
            "cuda_reserved_bytes",
            "cuda_free_mib",
        ):
            for bad in (float("nan"), float("inf"), -1.0):
                value = snapshot("baseline")
                value[key] = bad
                cases.append((key, bad, value))
        inconsistent = snapshot("baseline", system_commit_fraction=0.1)
        cases.append(("commit", "inconsistent", inconsistent))
        allocated_gt_reserved = snapshot(
            "baseline", cuda_allocated_bytes=500.0, cuda_reserved_bytes=100.0
        )
        cases.append(("cuda", "inconsistent", allocated_gt_reserved))
        for key, bad, value in cases:
            with self.subTest(key=key, bad=bad):
                with self.assertRaises(worker.V4ContractError):
                    worker.validate_resource_snapshot(value, label="hostile")

    def test_post_park_low_ram_high_commit_or_reserved_vram_fails_closed(self):
        hostile = (
            snapshot(
                "parked",
                available_physical_mib=1.0,
                system_commit_used_mib=39600.0,
                system_commit_fraction=0.99,
            ),
            snapshot("parked", cuda_reserved_bytes=4_000_000_000.0),
        )
        for after in hostile:
            with self.subTest(after=after):
                factory = RuntimeFactory()
                runtime = factory.load()
                factory.park_resource_override = after
                result = runtime.park_cpu("qwen")
                self.assertFalse(result["parked"], result)
                self.assertNotEqual(runtime.state, worker.VoiceState.PARKED_CPU)

    def test_nan_post_park_cannot_bypass_gate(self):
        factory = RuntimeFactory()
        runtime = factory.load()
        factory.park_resource_override = snapshot(
            "parked", available_physical_mib=float("nan"), system_commit_fraction=float("nan")
        )
        result = runtime.park_cpu("qwen")
        self.assertFalse(result["parked"])
        self.assertNotEqual(runtime.state, worker.VoiceState.PARKED_CPU)

    def test_post_resume_ram_commit_and_cuda_headroom_are_enforced(self):
        factory = RuntimeFactory()
        runtime = factory.load()
        self.assertTrue(runtime.park_cpu("qwen")["parked"])
        factory.resume_resource_override = snapshot(
            "loaded",
            available_physical_mib=100.0,
            system_commit_used_mib=38000.0,
            system_commit_fraction=0.95,
            cuda_free_mib=100.0,
        )
        result = runtime.resume_cuda("voice")
        self.assertFalse(result["resumed"])
        self.assertNotEqual(runtime.state, worker.VoiceState.LOADED_CUDA)

    def test_transition_deadline_overrun_fails_closed(self):
        factory = RuntimeFactory()
        runtime = factory.load()
        factory.advance_cuda_seconds = 31.0
        result = runtime.park_cpu("qwen")
        self.assertFalse(result["parked"])
        self.assertIn("bounded deadline", result["error"])
        self.assertNotEqual(runtime.state, worker.VoiceState.PARKED_CPU)


class V4VoiceIdentityAndCleanupTests(unittest.TestCase):
    def test_one_load_condition_and_exact_park_resume_identity(self):
        factory = RuntimeFactory()
        runtime = factory.load()
        generation = runtime.model_object_generation
        digest = runtime.condition_digest
        model_id = id(runtime.model)
        self.assertTrue(runtime.park_cpu("qwen")["parked"])
        self.assertTrue(runtime.resume_cuda("voice")["resumed"])
        self.assertEqual(runtime.model_load_count, 1)
        self.assertEqual(runtime.conditioning_count, 1)
        self.assertEqual(runtime.model_object_generation, generation)
        self.assertEqual(runtime.condition_digest, digest)
        self.assertEqual(id(runtime.model), model_id)

    def test_cpu_synthesis_is_rejected_without_adapter_call(self):
        factory = RuntimeFactory()
        runtime = factory.load()
        self.assertTrue(runtime.park_cpu("qwen")["parked"])
        result = runtime.synthesize(exact_request(runtime))
        self.assertFalse(result["generated"])
        self.assertIsNone(factory.last_synthesis_kwargs)

    def test_closed_schema_rejects_unapproved_audio_prompt_and_extra_route_keys(self):
        for key, value in (
            ("audio_prompt_path", "unapproved.wav"),
            ("device", "cpu"),
            ("generic_voice_used", True),
            ("sapi_voice_used", True),
            ("fallback_used", True),
        ):
            with self.subTest(key=key):
                factory = RuntimeFactory()
                runtime = factory.load()
                request = exact_request(runtime)
                request[key] = value
                result = runtime.synthesize(request)
                self.assertFalse(result["generated"])
                self.assertIsNone(factory.last_synthesis_kwargs)

    def test_synthesis_supplies_only_exact_approved_audio_prompt_internally(self):
        factory = RuntimeFactory()
        runtime = factory.load()
        result = runtime.synthesize(exact_request(runtime))
        self.assertTrue(result["generated"], result)
        self.assertEqual(
            factory.last_synthesis_kwargs,
            {
                "text": "Exact approved public SPOKEN test.",
                "approved_audio_prompt_path": str(
                    (ROOT / worker.EXACT_REFERENCE_PATH).resolve()
                ),
                "approved_audio_prompt_sha256": worker.EXACT_REFERENCE_SHA256,
            },
        )
        self.assertFalse(result["generic_voice_used"])
        self.assertFalse(result["sapi_voice_used"])
        self.assertFalse(result["fallback_used"])

    def test_open_or_generic_claim_in_artifact_response_is_rejected(self):
        factory = RuntimeFactory()
        factory.artifact_extra = {"generic_voice_used": False}
        runtime = factory.load()
        result = runtime.synthesize(exact_request(runtime))
        self.assertFalse(result["generated"])
        self.assertNotEqual(runtime.state, worker.VoiceState.LOADED_CUDA)

    def test_live_mixed_device_or_condition_mutation_after_synthesis_is_rejected(self):
        for mutation in ("mixed", "condition"):
            with self.subTest(mutation=mutation):
                factory = RuntimeFactory()
                factory.mutate_synthesis = mutation
                runtime = factory.load()
                result = runtime.synthesize(exact_request(runtime))
                self.assertFalse(result["generated"], result)
                self.assertNotEqual(runtime.state, worker.VoiceState.LOADED_CUDA)

    def test_fresh_identity_rehash_occurs_before_and_after_synthesis(self):
        factory = RuntimeFactory()
        runtime = factory.load()
        exact = dict(runtime.identity)
        altered = dict(exact)
        altered["reference_sha256"] = "0" * 64
        values = iter((exact, altered))
        runtime._identity_now = lambda: next(values)
        result = runtime.synthesize(exact_request(runtime))
        self.assertFalse(result["generated"])
        self.assertIn("approved files changed", result["error"])

    def test_unload_release_or_cuda_failure_never_claims_success(self):
        factory = RuntimeFactory()
        runtime = factory.load()
        factory.release_success = False
        factory.cuda_failure = True
        result = runtime.full_unload("hostile_cleanup")
        self.assertFalse(result["unloaded"])
        self.assertTrue(result["cleanup_debt"])
        self.assertEqual(runtime.state, worker.VoiceState.CLEANUP_DEBT)
        self.assertTrue(result["owned_python_references_absent"])
        self.assertTrue(any("release_owned" in item for item in result["errors"]))
        self.assertTrue(any("cuda_cleanup" in item for item in result["errors"]))

    def test_unload_high_final_ram_or_vram_never_claims_success(self):
        factory = RuntimeFactory()
        runtime = factory.load()
        factory.unload_resource_override = snapshot(
            "loaded", process_rss_mib=9000.0, cuda_allocated_bytes=3_000_000_000.0
        )
        result = runtime.full_unload("hostile_residual")
        self.assertFalse(result["unloaded"])
        self.assertEqual(runtime.state, worker.VoiceState.CLEANUP_DEBT)
        self.assertTrue(any("resource_after" in item for item in result["errors"]))

    def test_unload_success_requires_exact_release_double_cleanup_and_final_measurement(self):
        factory = RuntimeFactory()
        runtime = factory.load()
        result = runtime.full_unload("clean_shutdown")
        self.assertTrue(result["unloaded"], result)
        self.assertFalse(result["cleanup_debt"])
        self.assertEqual(runtime.state, worker.VoiceState.UNLOADED)
        self.assertEqual(result["release_result"]["owned_model_count"], 0)
        self.assertEqual(len(result["cache_cleanup_results"]), 2)
        self.assertEqual(len(result["cuda_cleanup_results"]), 2)
        self.assertEqual(result["qwen_absence"]["records"], [])
        self.assertEqual(result["resources_after"], snapshot("baseline"))


class V4QwenOwnershipAndConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.factory = RuntimeFactory()
        self.voice = self.factory.load()
        parked = self.voice.park_cpu("qwen")
        self.assertTrue(parked["parked"], parked)
        self.coordinator = integration.QwenVoiceSerializationV4(
            voice=self.voice, qwen_backend=self.factory.qwen, now=self.factory.now
        )

    def start_and_wait(self, token=TOKEN):
        started = self.coordinator.start_load_only(
            owner="owner", session="session", token=token
        )
        self.assertTrue(started["started"], started)
        waited = self.coordinator.wait_load_only()
        self.assertTrue(waited["completed"])
        self.assertTrue(waited["result"].get("loaded"), waited)
        return waited["result"]

    def test_empty_short_equal_or_reused_bindings_are_rejected(self):
        bad = (
            ("", "session", TOKEN),
            ("owner", "", TOKEN),
            ("owner", "session", "short"),
            ("same", "same", TOKEN),
        )
        for owner, session, token in bad:
            with self.subTest(owner=owner, session=session, token=token):
                with self.assertRaises(worker.V4ContractError):
                    self.coordinator.start_load_only(owner=owner, session=session, token=token)
        self.start_and_wait()
        result = self.coordinator.run_real_stream(
            owner="owner", session="session", token=TOKEN, messages=[], consume_chunk=lambda _x: None
        )
        self.assertTrue(result["completed"])
        with self.assertRaises(worker.V4ContractError):
            self.coordinator.start_load_only(owner="owner", session="session-2", token=TOKEN)

    def test_expired_load_completion_is_refused_and_cleaned(self):
        self.factory.qwen.advance_clock = lambda: self.factory.clock.__setitem__(0, 1100.0)
        started = self.coordinator.start_load_only(
            owner="owner", session="session", token=TOKEN, ttl_seconds=90
        )
        self.assertTrue(started["started"])
        waited = self.coordinator.wait_load_only()
        self.assertFalse(waited["result"]["loaded"])
        self.assertIn("at or after its TTL", waited["result"]["error"])
        self.assertEqual(self.factory.qwen.records, [])
        self.assertIsNone(self.coordinator.owned)

    def test_unload_false_and_resident_qwen_produces_cleanup_debt_not_success(self):
        self.start_and_wait()
        self.factory.qwen.unload_success = False
        self.factory.qwen.retain_on_unload = True
        result = self.coordinator.cancel_owned(
            owner="owner", session="session", token=TOKEN, reason="chat_closed"
        )
        self.assertFalse(result["cleaned"])
        self.assertTrue(result["cleanup_debt"])
        self.assertIsNotNone(self.coordinator.owned)
        self.assertEqual(self.coordinator.state, integration.QwenOperationState.CLEANUP_DEBT)
        self.assertNotEqual(self.factory.qwen.records, [])
        self.assertFalse(result["qwen_cleanup"]["released"])

    def test_shared_lock_is_held_for_complete_real_stream(self):
        self.start_and_wait()
        self.factory.qwen.block_stream = True
        result_box = {}

        def run():
            result_box["result"] = self.coordinator.run_real_stream(
                owner="owner",
                session="session",
                token=TOKEN,
                messages=[{"role": "user", "content": "Hello"}],
                consume_chunk=lambda _value: None,
            )

        stream_thread = threading.Thread(target=run)
        stream_thread.start()
        self.assertTrue(self.factory.qwen.stream_entered.wait(1.0))
        acquired = self.voice.operation_lock.acquire(timeout=0.05)
        if acquired:
            self.voice.operation_lock.release()
        self.assertFalse(acquired, "another operation acquired the lock during real stream")
        self.factory.qwen.release_stream.set()
        stream_thread.join(1.0)
        self.assertFalse(stream_thread.is_alive())
        self.assertTrue(result_box["result"]["completed"], result_box)
        request = self.factory.qwen.stream_requests[0]
        self.assertEqual(request["model"], worker.EXACT_QWEN_MODEL)
        self.assertEqual(request["expected_digest"], worker.EXACT_QWEN_DIGEST)
        self.assertEqual(request["keep_alive"], 0)

    def test_cancellation_enters_and_completes_while_load_backend_was_blocked(self):
        self.factory.qwen.block_load = True
        started = self.coordinator.start_load_only(
            owner="owner", session="session", token=TOKEN
        )
        self.assertTrue(started["started"])
        self.assertTrue(self.factory.qwen.load_entered.wait(1.0))
        began = time.perf_counter()
        result = self.coordinator.cancel_owned(
            owner="owner", session="session", token=TOKEN, reason="person_deactivated"
        )
        elapsed = time.perf_counter() - began
        self.assertLess(elapsed, 1.0)
        self.assertTrue(result["cleaned"], result)
        self.assertEqual(self.factory.qwen.cancel_calls, [TOKEN])
        self.assertEqual(self.factory.qwen.records, [])
        self.assertEqual(self.voice.state, worker.VoiceState.UNLOADED)

    def test_uncancellable_block_returns_cleanup_debt_at_join_bound(self):
        self.factory.qwen.block_load = True
        self.factory.qwen.ignore_cancel = True
        started = self.coordinator.start_load_only(
            owner="owner", session="session", token=TOKEN
        )
        self.assertTrue(started["started"])
        self.assertTrue(self.factory.qwen.load_entered.wait(1.0))
        began = time.perf_counter()
        result = self.coordinator.cancel_owned(
            owner="owner", session="session", token=TOKEN, reason="chat_closed"
        )
        elapsed = time.perf_counter() - began
        self.assertFalse(result["cleaned"])
        self.assertTrue(result["cleanup_debt"])
        self.assertEqual(result["reason"], "bounded_cancel_join_timed_out")
        self.assertGreaterEqual(elapsed, 1.8)
        self.assertLess(elapsed, 3.0)
        self.assertIsNotNone(self.coordinator.owned)
        self.factory.qwen.release_load.set()
        self.assertTrue(self.coordinator._operation_done.wait(1.0))

    def test_stale_token_cannot_cancel_exact_owned_operation(self):
        self.start_and_wait()
        result = self.coordinator.cancel_owned(
            owner="owner",
            session="session",
            token="v4-owner-capability-token-000000000999",
            reason="chat_closed",
        )
        self.assertFalse(result["cleaned"])
        self.assertIsNotNone(self.coordinator.owned)
        self.assertEqual(self.factory.qwen.unload_calls, [])

    def test_wrong_digest_or_hidden_load_generation_fails_and_never_becomes_resident(self):
        for mutation in ("digest", "hidden"):
            with self.subTest(mutation=mutation):
                factory = RuntimeFactory()
                voice = factory.load()
                self.assertTrue(voice.park_cpu("qwen")["parked"])
                if mutation == "digest":
                    factory.qwen.wrong_resident_digest = True
                else:
                    factory.qwen.load_response["response"] = "hidden"
                coordinator = integration.QwenVoiceSerializationV4(
                    voice=voice, qwen_backend=factory.qwen, now=factory.now
                )
                started = coordinator.start_load_only(
                    owner="owner", session="session", token=TOKEN
                )
                self.assertTrue(started["started"])
                result = coordinator.wait_load_only()["result"]
                self.assertFalse(result["loaded"])
                self.assertNotEqual(coordinator.state, integration.QwenOperationState.RESIDENT_OWNED)

    def test_idle_expiry_uses_exact_binding_and_cleanup_proof(self):
        self.start_and_wait()
        result = self.coordinator.idle_cleanup(
            owner="owner", session="session", token=TOKEN, now_monotonic=1091.0
        )
        self.assertTrue(result["cleaned"], result)
        self.assertIsNone(self.coordinator.owned)
        self.assertEqual(self.voice.state, worker.VoiceState.UNLOADED)


if __name__ == "__main__":
    unittest.main()
