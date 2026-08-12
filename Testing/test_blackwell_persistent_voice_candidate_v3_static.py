from __future__ import annotations

import ast
import copy
import importlib
import json
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
worker = importlib.import_module(
    "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v3.persistent_worker"
)
integration = importlib.import_module("Core.persistent_blackwell_voice_integration_v3")


class FakeTensor:
    def __init__(self, device: str, payload: bytes, *, shape=(2, 2), dtype="float32") -> None:
        self.device = device
        self._payload = bytes(payload)
        self.shape = tuple(shape)
        self.dtype = dtype

    def to(self, device: str):
        self.device = str(device)
        return self

    def detach(self):
        return self

    def cpu(self):
        return FakeTensor("cpu", self._payload, shape=self.shape, dtype=self.dtype)

    def contiguous(self):
        return self

    def content_bytes(self) -> bytes:
        return self._payload


class FakeModule:
    def __init__(self, name: str, device: str = "cuda", *, refuse_device: str | None = None) -> None:
        self.name = name
        self._parameters = [FakeTensor(device, f"{name}:parameter".encode())]
        self._buffers = [FakeTensor(device, f"{name}:buffer".encode())]
        self.refuse_device = refuse_device

    def parameters(self):
        return list(self._parameters)

    def buffers(self):
        return list(self._buffers)

    def to(self, device: str):
        if device != self.refuse_device:
            for item in self._parameters + self._buffers:
                item.to(device)
        return self


class FakeT3Conditions:
    def __init__(self, device: str = "cuda") -> None:
        self.speaker_emb = FakeTensor(device, b"speaker")
        self.clap_emb = FakeTensor(device, b"clap")

    def to(self, device: str):
        self.speaker_emb.to(device)
        self.clap_emb.to(device)
        return self


class FakeConditions:
    def __init__(self, device: str = "cuda") -> None:
        self.t3 = FakeT3Conditions(device)
        self.gen = {
            "prompt_token": FakeTensor(device, b"prompt-token", shape=(1, 3), dtype="int64"),
            "embedding": FakeTensor(device, b"embedding", shape=(1, 4)),
        }

    def to(self, device: str):
        self.t3.to(device)
        for item in self.gen.values():
            item.to(device)
        return self


class FakeModel:
    def __init__(self, *, refuse_component: str | None = None) -> None:
        self.device = "cuda"
        self.t3 = FakeModule("t3", refuse_device="cpu" if refuse_component == "t3" else None)
        self.s3gen = FakeModule(
            "s3gen", refuse_device="cpu" if refuse_component == "s3gen" else None
        )
        self.ve = FakeModule("ve", refuse_device="cpu" if refuse_component == "ve" else None)
        self.conds = FakeConditions()


class SequenceProbe:
    def __init__(self, values: list[dict]) -> None:
        self.values = [dict(item) for item in values]
        self.calls = 0

    def __call__(self):
        index = min(self.calls, len(self.values) - 1)
        self.calls += 1
        return dict(self.values[index])


class FakeQwenBackend:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.records: list[dict] = []
        self.load_requests: list[dict] = []
        self.unload_calls: list[dict] = []
        self.cancel_calls: list[str] = []
        self.load_response: dict = {"response": "", "eval_count": 0, "prompt_eval_count": 0}
        self.resident_digest = config["qwen_digest"]

    def load_only(self, request: dict, *, token: str):
        self.load_requests.append(copy.deepcopy(request))
        self.records = [{"model": self.config["qwen_model"], "digest": self.resident_digest}]
        return dict(self.load_response)

    def residency(self):
        return {"query_succeeded": True, "records": copy.deepcopy(self.records)}

    def unload_owned(self, *, token: str, model: str, digest: str):
        self.unload_calls.append({"token": token, "model": model, "digest": digest})
        self.records = []
        return {"unloaded": True, "model": model, "digest": digest}

    def cancel_owned(self, *, token: str):
        self.cancel_calls.append(token)


def resources(
    *,
    available=10000.0,
    commit=0.55,
    allocated=100,
    reserved=120,
    cuda_free=12000.0,
):
    return {
        "process_rss_mib": 4000.0,
        "system_commit_used_mib": 18000.0,
        "system_commit_limit_mib": 32768.0,
        "available_physical_mib": available,
        "system_commit_fraction": commit,
        "cuda_allocated_bytes": allocated,
        "cuda_reserved_bytes": reserved,
        "cuda_free_mib": cuda_free,
    }


class RuntimeFactory:
    def __init__(
        self,
        *,
        model: FakeModel | None = None,
        probe: SequenceProbe | None = None,
        qwen_absent: bool = True,
        synthesis_overrides: dict | None = None,
    ) -> None:
        self.config = worker.load_config()
        self.model = model or FakeModel()
        self.probe = probe or SequenceProbe(
            [
                resources(allocated=100),
                resources(allocated=3_500_000_000),
                resources(allocated=100),
                resources(allocated=100),
                resources(allocated=3_500_000_000),
            ]
        )
        self.qwen_absent = qwen_absent
        self.synthesis_calls = 0
        self.cache_clear_calls = 0
        self.release_calls = 0
        self.sync_calls = 0
        self.synthesis_overrides = synthesis_overrides or {}

    def identity(self, _config):
        return {
            "profile_sha256": self.config["approved_profile_sha256"],
            "reference_sha256": self.config["approved_reference_sha256"],
        }

    def qwen(self, _config):
        return {
            "query_succeeded": True,
            "qwen_absent_proven": self.qwen_absent,
            "qwen_records": [] if self.qwen_absent else [{"model": self.config["qwen_model"]}],
            "model_state_changed": False,
            "target_model": self.config["qwen_model"],
            "target_digest": self.config["qwen_digest"],
        }

    def clear_caches(self):
        self.cache_clear_calls += 1
        return {
            "resampler_cache": {"cleared": True, "kind": "lru_cache"},
            "mel_basis": {"cleared": True, "kind": "dict"},
            "hann_window": {"cleared": True, "kind": "dict"},
        }

    def sync(self):
        self.sync_calls += 1

    def release(self):
        self.release_calls += 1

    def synthesize(self, request: dict):
        self.synthesis_calls += 1
        result = {
            "generated": True,
            "device": "cuda",
            "profile_sha256": self.config["approved_profile_sha256"],
            "reference_sha256": self.config["approved_reference_sha256"],
            "condition_digest": request["condition_digest"],
            "text_sha256": request["text_sha256"],
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
        }
        result.update(self.synthesis_overrides)
        return result

    def loader(self, _config):
        return {
            "model": self.model,
            "backend": {
                "synthesize_cuda": self.synthesize,
                "clear_known_derived_caches": self.clear_caches,
                "cuda_sync_and_empty": self.sync,
                "release_owned": self.release,
            },
            "profile_sha256": self.config["approved_profile_sha256"],
            "reference_sha256": self.config["approved_reference_sha256"],
            "conditioned_reference_sha256": self.config["approved_reference_sha256"],
        }

    def runtime(self):
        return worker.PersistentVoiceRuntimeV3(
            config=self.config,
            loader=self.loader,
            identity_verifier=self.identity,
            qwen_probe=self.qwen,
            resource_probe=self.probe,
            allow_inactive_static_execution=True,
        )


def exact_request(runtime) -> dict:
    text = "This is the exact approved public spoken test sentence."
    return {
        "text": text,
        "text_sha256": worker.sha256_text(text),
        "input_channel": "public_spoken_only",
        "profile_sha256": runtime.config["approved_profile_sha256"],
        "reference_sha256": runtime.config["approved_reference_sha256"],
        "condition_digest": runtime.condition_digest,
    }


class BlackwellV3StaticStateTests(unittest.TestCase):
    def test_candidate_is_inactive_static_only_and_v2_hashes_are_exact(self):
        config = worker.load_config()
        self.assertFalse(config["production_routing_authorized"])
        self.assertFalse(config["live_execution_authorized"])
        self.assertFalse(config["playback_authorized"])
        self.assertFalse(config["cpu_synthesis_allowed"])
        self.assertFalse(config["generic_voice_allowed"])
        self.assertFalse(config["sapi_allowed"])
        self.assertEqual(config["automatic_fallback_inside_candidate"], None)
        self.assertEqual(config["production_fallback_retained_outside_candidate"], "sealed_cpu_chatterbox_only")
        self.assertEqual(worker.verify_v2_baseline(config), config["sealed_v2_baseline"])
        self.assertEqual(
            worker.verify_identity_files(config),
            {
                "profile_sha256": config["approved_profile_sha256"],
                "reference_sha256": config["approved_reference_sha256"],
            },
        )

    def test_worker_has_no_top_level_torch_chatterbox_or_ollama_import(self):
        path = ROOT / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v3/persistent_worker.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any(name.startswith(("torch", "chatterbox", "ollama")) for name in imports))

    def test_exact_state_cycle_preserves_one_object_and_one_conditioning(self):
        factory = RuntimeFactory()
        runtime = factory.runtime()
        loaded = runtime.load_initial("kira:owner-session")
        self.assertTrue(loaded["loaded"], loaded)
        generation = runtime.model_object_generation
        digest = runtime.condition_digest
        model_id = id(runtime.model)
        parked = runtime.park_cpu("qwen_turn")
        self.assertTrue(parked["parked"], parked)
        self.assertEqual(runtime.state, worker.VoiceState.PARKED_CPU)
        self.assertEqual(runtime.model_object_generation, generation)
        self.assertEqual(runtime.condition_digest, digest)
        self.assertEqual(id(runtime.model), model_id)
        resumed = runtime.resume_cuda("qwen_absent")
        self.assertTrue(resumed["resumed"], resumed)
        self.assertEqual(runtime.state, worker.VoiceState.LOADED_CUDA)
        self.assertEqual(runtime.model_object_generation, generation)
        self.assertEqual(runtime.condition_digest, digest)
        self.assertEqual(id(runtime.model), model_id)
        self.assertEqual(runtime.model_load_count, 1)
        self.assertEqual(runtime.conditioning_count, 1)
        self.assertEqual(runtime.park_count, 1)
        self.assertEqual(runtime.resume_count, 1)
        self.assertGreaterEqual(factory.cache_clear_calls, 1)
        self.assertGreaterEqual(factory.sync_calls, 2)

    def test_cpu_park_forbids_synthesis_without_calling_generator(self):
        factory = RuntimeFactory()
        runtime = factory.runtime()
        self.assertTrue(runtime.load_initial("owner")["loaded"])
        self.assertTrue(runtime.park_cpu("qwen")["parked"])
        result = runtime.synthesize(exact_request(runtime))
        self.assertFalse(result["generated"])
        self.assertEqual(result["reason"], "cpu_or_unloaded_synthesis_forbidden")
        self.assertEqual(factory.synthesis_calls, 0)
        self.assertEqual(runtime.state, worker.VoiceState.PARKED_CPU)

    def test_exact_cuda_synthesis_accepts_no_fallback_or_substitute(self):
        factory = RuntimeFactory()
        runtime = factory.runtime()
        self.assertTrue(runtime.load_initial("owner")["loaded"])
        result = runtime.synthesize(exact_request(runtime))
        self.assertTrue(result["generated"], result)
        self.assertEqual(result["device"], "cuda")
        self.assertFalse(result["generic_voice_used"])
        self.assertFalse(result["sapi_voice_used"])
        self.assertFalse(result["fallback_used"])
        self.assertEqual(factory.synthesis_calls, 1)

    def test_wrong_profile_reference_condition_or_text_hash_fails_full_unload(self):
        for field in ("profile_sha256", "reference_sha256", "condition_digest", "text_sha256"):
            with self.subTest(field=field):
                factory = RuntimeFactory()
                runtime = factory.runtime()
                self.assertTrue(runtime.load_initial("owner")["loaded"])
                request = exact_request(runtime)
                request[field] = "0" * 64
                result = runtime.synthesize(request)
                self.assertFalse(result["generated"])
                self.assertEqual(runtime.state, worker.VoiceState.UNLOADED)
                self.assertEqual(factory.synthesis_calls, 0)
                self.assertEqual(factory.release_calls, 1)

    def test_generic_sapi_cpu_or_fallback_claim_fails_full_unload(self):
        cases = (
            {"generic_voice_used": True},
            {"sapi_voice_used": True},
            {"fallback_used": True},
            {"device": "cpu"},
        )
        for override in cases:
            with self.subTest(override=override):
                factory = RuntimeFactory(synthesis_overrides=override)
                runtime = factory.runtime()
                self.assertTrue(runtime.load_initial("owner")["loaded"])
                result = runtime.synthesize(exact_request(runtime))
                self.assertFalse(result["generated"])
                self.assertEqual(runtime.state, worker.VoiceState.UNLOADED)
                self.assertEqual(factory.release_calls, 1)

    def test_mixed_device_park_fails_closed_to_full_unload(self):
        factory = RuntimeFactory(model=FakeModel(refuse_component="s3gen"))
        runtime = factory.runtime()
        self.assertTrue(runtime.load_initial("owner")["loaded"])
        result = runtime.park_cpu("qwen")
        self.assertFalse(result["parked"])
        self.assertIn("mixed-device", result["error"])
        self.assertEqual(runtime.state, worker.VoiceState.UNLOADED)
        self.assertEqual(factory.release_calls, 1)

    def test_condition_content_drift_during_move_fails_closed(self):
        class CorruptingConditions(FakeConditions):
            def to(self, device: str):
                super().to(device)
                if device == "cpu":
                    self.gen["embedding"]._payload = b"corrupted-condition"
                return self

        model = FakeModel()
        model.conds = CorruptingConditions()
        factory = RuntimeFactory(model=model)
        runtime = factory.runtime()
        self.assertTrue(runtime.load_initial("owner")["loaded"])
        result = runtime.park_cpu("qwen")
        self.assertFalse(result["parked"])
        self.assertIn("condition content changed", result["error"])
        self.assertEqual(runtime.state, worker.VoiceState.UNLOADED)

    def test_incomplete_known_cache_cleanup_report_fails_closed(self):
        factory = RuntimeFactory()
        runtime = factory.runtime()
        self.assertTrue(runtime.load_initial("owner")["loaded"])
        runtime.backend["clear_known_derived_caches"] = lambda: {
            "resampler_cache": {"cleared": True},
            "mel_basis": {"cleared": True},
        }
        result = runtime.park_cpu("qwen")
        self.assertFalse(result["parked"])
        self.assertIn("exact known cache set", result["error"])
        self.assertEqual(runtime.state, worker.VoiceState.UNLOADED)

    def test_invalid_transitions_do_not_reload_or_recondition(self):
        factory = RuntimeFactory()
        runtime = factory.runtime()
        self.assertFalse(runtime.park_cpu("invalid")["parked"])
        self.assertFalse(runtime.resume_cuda("invalid")["resumed"])
        self.assertTrue(runtime.load_initial("owner")["loaded"])
        duplicate = runtime.load_initial("owner")
        self.assertFalse(duplicate["loaded"])
        self.assertEqual(runtime.model_load_count, 1)
        self.assertEqual(runtime.conditioning_count, 1)

    def test_low_ram_or_commit_pressure_fails_to_full_unload_before_swap_thrash(self):
        for blocked in (
            resources(available=1024.0, allocated=3_500_000_000),
            resources(commit=0.95, allocated=3_500_000_000),
        ):
            with self.subTest(blocked=blocked):
                probe = SequenceProbe([resources(allocated=100), blocked])
                factory = RuntimeFactory(probe=probe)
                runtime = factory.runtime()
                self.assertTrue(runtime.load_initial("owner")["loaded"])
                result = runtime.park_cpu("qwen")
                self.assertFalse(result["parked"])
                self.assertEqual(runtime.state, worker.VoiceState.UNLOADED)
                self.assertEqual(factory.release_calls, 1)

    def test_vram_residual_gate_fails_closed(self):
        probe = SequenceProbe(
            [
                resources(allocated=100),
                resources(allocated=3_500_000_000),
                resources(allocated=900_000_000),
            ]
        )
        factory = RuntimeFactory(probe=probe)
        runtime = factory.runtime()
        self.assertTrue(runtime.load_initial("owner")["loaded"])
        result = runtime.park_cpu("qwen")
        self.assertFalse(result["parked"])
        self.assertIn("bounded owned CUDA allocation", result["error"])
        self.assertEqual(runtime.state, worker.VoiceState.UNLOADED)

    def test_qwen_residency_or_low_cuda_headroom_blocks_resume_and_unloads(self):
        factory = RuntimeFactory(qwen_absent=False)
        runtime = factory.runtime()
        factory.qwen_absent = True
        self.assertTrue(runtime.load_initial("owner")["loaded"])
        self.assertTrue(runtime.park_cpu("qwen")["parked"])
        factory.qwen_absent = False
        result = runtime.resume_cuda("voice")
        self.assertFalse(result["resumed"])
        self.assertEqual(runtime.state, worker.VoiceState.UNLOADED)

        probe = SequenceProbe(
            [
                resources(allocated=100),
                resources(allocated=3_500_000_000),
                resources(allocated=100),
                resources(allocated=100, cuda_free=512.0),
            ]
        )
        factory = RuntimeFactory(probe=probe)
        runtime = factory.runtime()
        self.assertTrue(runtime.load_initial("owner")["loaded"])
        self.assertTrue(runtime.park_cpu("qwen")["parked"])
        result = runtime.resume_cuda("voice")
        self.assertFalse(result["resumed"])
        self.assertEqual(runtime.state, worker.VoiceState.UNLOADED)

    def test_idle_cleanup_releases_exact_owned_worker(self):
        factory = RuntimeFactory()
        runtime = factory.runtime()
        self.assertTrue(runtime.load_initial("owner")["loaded"])
        now = runtime.last_activity_monotonic + 121
        result = runtime.idle_cleanup(now_monotonic=now, idle_seconds=120)
        self.assertTrue(result["cleaned"])
        self.assertEqual(runtime.state, worker.VoiceState.UNLOADED)
        self.assertEqual(factory.release_calls, 1)


class BlackwellV3QwenSerializationTests(unittest.TestCase):
    def setUp(self):
        self.factory = RuntimeFactory()
        self.voice = self.factory.runtime()
        self.assertTrue(self.voice.load_initial("owner")["loaded"])
        self.backend = FakeQwenBackend(self.voice.config)
        self.clock = [1000.0]
        self.coordinator = integration.QwenVoiceSerializationV3(
            voice=self.voice, qwen_backend=self.backend, now=lambda: self.clock[0]
        )

    def park(self):
        result = self.voice.park_cpu("qwen_boundary")
        self.assertTrue(result["parked"], result)

    def load(self):
        return self.coordinator.load_only(owner="owner", session="session", token="token")

    def test_qwen_load_rejects_cuda_voice_and_never_calls_backend(self):
        result = self.load()
        self.assertFalse(result["loaded"])
        self.assertEqual(result["reason"], "qwen_load_rejects_nonparked_voice")
        self.assertEqual(self.backend.load_requests, [])

    def test_exact_load_only_has_no_conversation_generation_or_person_artifacts(self):
        self.park()
        result = self.load()
        self.assertTrue(result["loaded"], result)
        request = result["request"]
        self.assertEqual(request["purpose"], "load_only")
        self.assertEqual(request["model"], self.voice.config["qwen_model"])
        self.assertEqual(request["expected_digest"], self.voice.config["qwen_digest"])
        self.assertEqual(request["prompt"], "")
        self.assertEqual(request["messages"], [])
        self.assertEqual(request["context"], [])
        self.assertEqual(request["options"]["num_predict"], 0)
        self.assertTrue(result["no_conversation_artifacts"])
        self.assertTrue(all(event["chat_event_created"] is False for event in self.coordinator.audit_events))
        self.assertTrue(all(event["memory_event_created"] is False for event in self.coordinator.audit_events))
        self.assertTrue(all(event["spoken_event_created"] is False for event in self.coordinator.audit_events))

    def test_load_only_generation_or_wrong_digest_fails_closed(self):
        for mutation in ("response", "eval", "digest"):
            with self.subTest(mutation=mutation):
                factory = RuntimeFactory()
                voice = factory.runtime()
                self.assertTrue(voice.load_initial("owner")["loaded"])
                self.assertTrue(voice.park_cpu("qwen")["parked"])
                backend = FakeQwenBackend(voice.config)
                if mutation == "response":
                    backend.load_response["response"] = "hidden generated text"
                elif mutation == "eval":
                    backend.load_response["eval_count"] = 1
                else:
                    backend.resident_digest = "0" * 64
                coordinator = integration.QwenVoiceSerializationV3(voice=voice, qwen_backend=backend)
                result = coordinator.load_only(owner="owner", session="session", token="token")
                self.assertFalse(result["loaded"])
                self.assertEqual(voice.state, worker.VoiceState.UNLOADED)
                self.assertIsNone(coordinator.owned)

    def test_real_reply_keep_alive_zero_then_absence_allows_voice_resume(self):
        self.park()
        self.assertTrue(self.load()["loaded"])
        request = self.coordinator.prepare_real_reply(
            owner="owner", session="session", token="token", messages=[{"role": "user", "content": "Hello"}]
        )
        self.assertEqual(request["model"], self.voice.config["qwen_model"])
        self.assertEqual(request["expected_digest"], self.voice.config["qwen_digest"])
        self.assertEqual(request["keep_alive"], 0)
        self.backend.records = []
        confirmed = self.coordinator.confirm_real_reply_unloaded(
            owner="owner", session="session", token="token"
        )
        self.assertTrue(confirmed["confirmed"])
        self.assertEqual(self.voice.state, worker.VoiceState.PARKED_CPU)
        resumed = self.voice.resume_cuda("real_reply_qwen_absent")
        self.assertTrue(resumed["resumed"], resumed)

    def test_explicit_exact_release_serializes_before_voice_resume(self):
        self.park()
        self.assertTrue(self.load()["loaded"])
        result = self.coordinator.release_for_voice(
            owner="owner", session="session", token="token", resume_reason="playback_complete"
        )
        self.assertTrue(result["released"], result)
        self.assertEqual(self.voice.state, worker.VoiceState.LOADED_CUDA)
        self.assertEqual(self.backend.records, [])
        self.assertEqual(len(self.backend.unload_calls), 1)
        self.assertEqual(self.backend.unload_calls[0]["digest"], self.voice.config["qwen_digest"])

    def test_one_owned_prewarm_and_stale_token_cannot_clean_current_owner(self):
        self.park()
        self.assertTrue(self.load()["loaded"])
        duplicate = self.load()
        self.assertFalse(duplicate["loaded"])
        stale = self.coordinator.cancel_owned(
            owner="owner", session="session", token="stale", reason="chat_closed"
        )
        self.assertFalse(stale["cleaned"])
        self.assertIsNotNone(self.coordinator.owned)
        self.assertEqual(self.voice.state, worker.VoiceState.PARKED_CPU)
        self.assertEqual(self.backend.unload_calls, [])

    def test_each_exact_cancellation_reason_cleans_qwen_and_voice(self):
        for reason in sorted(integration.QwenVoiceSerializationV3.CLEANUP_REASONS):
            with self.subTest(reason=reason):
                factory = RuntimeFactory()
                voice = factory.runtime()
                self.assertTrue(voice.load_initial("owner")["loaded"])
                self.assertTrue(voice.park_cpu("qwen")["parked"])
                backend = FakeQwenBackend(voice.config)
                coordinator = integration.QwenVoiceSerializationV3(voice=voice, qwen_backend=backend)
                self.assertTrue(
                    coordinator.load_only(owner="owner", session="session", token="token")["loaded"]
                )
                result = coordinator.cancel_owned(
                    owner="owner", session="session", token="token", reason=reason
                )
                self.assertTrue(result["cleaned"], result)
                self.assertEqual(voice.state, worker.VoiceState.UNLOADED)
                self.assertIsNone(coordinator.owned)
                self.assertEqual(backend.records, [])

    def test_idle_expiry_cleans_exact_prewarm_and_worker(self):
        self.park()
        loaded = self.load()
        self.assertTrue(loaded["loaded"])
        self.clock[0] += 91
        result = self.coordinator.idle_cleanup(
            owner="owner", session="session", token="token", now_monotonic=self.clock[0]
        )
        self.assertTrue(result["cleaned"], result)
        self.assertEqual(self.voice.state, worker.VoiceState.UNLOADED)
        self.assertEqual(self.backend.records, [])

    def test_shared_operation_lock_is_exact_voice_lock(self):
        self.assertIs(self.coordinator.operation_lock, self.voice.operation_lock)
        self.assertIsInstance(self.coordinator.operation_lock, type(threading.RLock()))

    def test_no_llama_generic_sapi_or_production_route_in_v3_contract(self):
        config_text = (
            ROOT
            / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v3/candidate_config.json"
        ).read_text(encoding="utf-8")
        config = json.loads(config_text)
        self.assertEqual(config["qwen_model"], "qwen3.5:9b")
        self.assertEqual(config["forbidden_text_models"], ["llama3.1:8b"])
        self.assertFalse(config["generic_voice_allowed"])
        self.assertFalse(config["sapi_allowed"])
        self.assertFalse(integration.PRODUCTION_ROUTING_AUTHORIZED)
        self.assertFalse(integration.PLAYBACK_IMPLEMENTED)


if __name__ == "__main__":
    unittest.main()
