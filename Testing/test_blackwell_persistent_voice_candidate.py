from __future__ import annotations

import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate"
CONFIG = SIDECAR / "candidate_config.json"
CONTRACT = SIDECAR / "candidate_contract.py"
CLIENT = SIDECAR / "candidate_client.py"
WORKER = SIDECAR / "persistent_worker.py"
ACCEPTANCE = ROOT / "Tools" / "run_persistent_blackwell_voice_candidate_acceptance.py"

if str(SIDECAR) not in sys.path:
    sys.path.insert(0, str(SIDECAR))

import candidate_client
import candidate_contract
import persistent_worker

_acceptance_spec = importlib.util.spec_from_file_location(
    "persistent_blackwell_acceptance_harness_for_test",
    ACCEPTANCE,
)
assert _acceptance_spec is not None and _acceptance_spec.loader is not None
acceptance_harness = importlib.util.module_from_spec(_acceptance_spec)
_acceptance_spec.loader.exec_module(acceptance_harness)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _FakeSampler:
    def start(self) -> None:
        return None

    def stop(self) -> dict[str, object]:
        return {
            "sample_count": 0,
            "peak_process_rss_mib": 0.0,
            "peak_system_ram_used_mib": 0.0,
            "baseline_total_gpu_used_mib": 0.0,
            "peak_total_gpu_used_mib": 0.0,
            "peak_total_gpu_delta_mib": 0.0,
            "sampling_errors": [],
        }


class _FakeUrlResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "_FakeUrlResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class _FakeCuda:
    def __init__(self) -> None:
        self.allocated = 0
        self.reserved = 0
        self.peak_allocated = 0
        self.peak_reserved = 0
        self.empty_cache_calls = 0

    def is_available(self) -> bool:
        return True

    def get_device_name(self, index: int) -> str:
        return "NVIDIA GeForce RTX 5060 Ti"

    def get_device_capability(self, index: int) -> tuple[int, int]:
        return (12, 0)

    def get_arch_list(self) -> list[str]:
        return ["sm_120"]

    def synchronize(self, index: int) -> None:
        return None

    def empty_cache(self) -> None:
        self.empty_cache_calls += 1
        if self.allocated and self.empty_cache_calls > 1:
            self.allocated = 0
            self.reserved = 0

    def reset_peak_memory_stats(self, index: int) -> None:
        self.peak_allocated = self.allocated
        self.peak_reserved = self.reserved

    def memory_allocated(self, index: int) -> int:
        return self.allocated

    def memory_reserved(self, index: int) -> int:
        return self.reserved

    def max_memory_allocated(self, index: int) -> int:
        return max(self.allocated, self.peak_allocated)

    def max_memory_reserved(self, index: int) -> int:
        return max(self.reserved, self.peak_reserved)

    def mem_get_info(self, index: int) -> tuple[int, int]:
        total = 16 * 1024 * 1024 * 1024
        return total - self.reserved, total


class _FakeTorch:
    __version__ = "2.11.0+cu130"

    class _Version:
        cuda = "13.0"

    version = _Version()

    def __init__(self) -> None:
        self.cuda = _FakeCuda()


class _FakeTorchaudio:
    __version__ = "2.11.0+cu130"


class _FakeDevice:
    def __init__(self, device_type: str) -> None:
        self.type = device_type


class _FakeParameter:
    def __init__(self, device_type: str = "cuda") -> None:
        self.device = _FakeDevice(device_type)


class _FakeModule:
    def __init__(self, device_type: str = "cuda") -> None:
        self.parameter = _FakeParameter(device_type)

    def parameters(self):
        return iter((self.parameter,))

    def buffers(self):
        return iter(())


class _FakeTensor:
    device = _FakeDevice("cpu")

    def __init__(self, values: object) -> None:
        self.values = values

    def squeeze(self) -> "_FakeTensor":
        return self

    def detach(self) -> "_FakeTensor":
        return self

    def cpu(self) -> "_FakeTensor":
        return self

    def numpy(self) -> object:
        return self.values


class _FakeModel:
    sr = 24000
    device = "cuda"

    def __init__(self, np_module: object, fake_cuda: _FakeCuda) -> None:
        self.np = np_module
        self.fake_cuda = fake_cuda
        self.t3 = _FakeModule()
        self.s3gen = _FakeModule()
        self.ve = _FakeModule()
        self.prepare_calls: list[str] = []
        self.generate_calls: list[tuple[str, dict[str, float]]] = []

    def prepare_conditionals(self, path: str) -> None:
        self.prepare_calls.append(path)

    def generate(self, text: str, **kwargs: float) -> _FakeTensor:
        self.generate_calls.append((text, dict(kwargs)))
        self.fake_cuda.peak_allocated = max(
            self.fake_cuda.peak_allocated,
            self.fake_cuda.allocated + 64 * 1024 * 1024,
        )
        return _FakeTensor(self.np.full(4800, 0.1, dtype=self.np.float32))


class BlackwellPersistentVoiceCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_candidate_is_inactive_and_production_router_has_no_candidate_route(self) -> None:
        self.assertEqual(
            self.config["candidate_status"],
            "inactive_private_candidate_not_production",
        )
        self.assertFalse(self.config["production_routing_authorized"])
        self.assertIsNone(self.config["automatic_fallback_inside_candidate"])
        self.assertFalse(self.config["generic_voice_fallback_allowed"])
        self.assertFalse(self.config["sapi_fallback_allowed"])
        host_contract = self.config["official_chatterbox_host_return_contract"]
        self.assertEqual(host_contract["public_generate_return_device"], "cpu")
        self.assertTrue(host_contract["host_return_expected"])
        self.assertTrue(host_contract["host_return_is_not_cuda_execution_proof"])
        self.assertFalse(host_contract["accepted_output_tensors_cuda"])
        diagnostics = self.config["diagnostics"]
        self.assertTrue(diagnostics["enabled_for_bounded_acceptance_only"])
        self.assertTrue(diagnostics["phase_start_and_finish_events_required"])
        self.assertEqual(diagnostics["faulthandler_dump_interval_seconds"], 120)
        self.assertTrue(diagnostics["faulthandler_repeat"])
        routing = json.loads(
            (ROOT / "Voice" / "sidecars" / "kira_approved_voice_routing.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual([item["route_id"] for item in routing["routes"]], ["blackwell_gpu", "sealed_cpu"])
        self.assertNotIn("persistent", json.dumps(routing).casefold())

    def test_every_candidate_and_protected_artifact_matches_config(self) -> None:
        hashes = candidate_contract.verify_candidate_config(self.config)
        self.assertEqual(hashes["candidate_contract"], sha256_file(CONTRACT))
        self.assertEqual(hashes["candidate_client"], sha256_file(CLIENT))
        self.assertEqual(hashes["candidate_worker"], sha256_file(WORKER))
        self.assertEqual(
            hashes["production_routing_manifest"],
            "a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81",
        )
        self.assertEqual(
            hashes["sealed_cpu_worker"],
            "856c195173f8932f1b9d731634290f9eb78bb543e90da37c1346160e45334f46",
        )

    def test_worker_has_no_top_level_heavy_model_or_audio_import(self) -> None:
        tree = ast.parse(WORKER.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(str(node.module or "").split(".")[0])
        self.assertTrue({"torch", "torchaudio", "chatterbox", "soundfile", "numpy"}.isdisjoint(imported))
        source = WORKER.read_text(encoding="utf-8")
        self.assertNotIn("audio_prompt_path", source)
        required_phases = (
            "startup.config_load",
            "startup.sealed_contract_verification",
            "startup.restricted_environment",
            "load.runtime_dependency_metadata",
            "load.approved_identity_hashes",
            "load.qwen_absence",
            "imports.torch",
            "imports.torchaudio",
            "imports.transformers_compatibility",
            "imports.chatterbox",
            "load.cuda_contract",
            "load.model_from_pretrained",
            "load.reference_prepare_conditionals",
            "synthesis.approved_identity_hashes",
            "synthesis.chunking",
            "model_generate",
            "cuda_to_host",
            "signal_validation",
            "pcm_postprocess",
            "synthesis.wav_write_partial",
            "synthesis.wav_validate_partial",
            "synthesis.wav_atomic_promote",
            "synthesis.wav_validate_and_hash_final",
            "unload.model_release_and_gc",
            "unload.cuda_empty_cache_and_synchronize",
        )
        for phase in required_phases:
            self.assertIn(phase, source)

    def test_phase_ledger_emits_started_then_finished_and_preserves_failure(self) -> None:
        events: list[dict[str, object]] = []
        ledger = candidate_contract.PhaseLedger(event_callback=events.append)
        with ledger.phase("diagnostic.pass"):
            self.assertEqual(events[-1]["phase_state"], "started")
            self.assertEqual(events[-1]["phase"], "diagnostic.pass")
        self.assertEqual([item["phase_state"] for item in events], ["started", "finished"])
        self.assertEqual(events[0]["start_monotonic_ns"], events[1]["start_monotonic_ns"])
        self.assertEqual(events[1]["status"], "passed")
        self.assertIn("end_monotonic_ns", events[1])
        self.assertIn("elapsed_seconds", events[1])

        failure_events: list[dict[str, object]] = []
        failed = candidate_contract.PhaseLedger(event_callback=failure_events.append)
        with self.assertRaisesRegex(RuntimeError, "preserved failure"):
            with failed.phase("diagnostic.fail"):
                raise RuntimeError("preserved failure")
        self.assertEqual(
            [item["phase_state"] for item in failure_events],
            ["started", "finished"],
        )
        self.assertEqual(failure_events[-1]["status"], "failed")
        self.assertEqual(failure_events[-1]["error_type"], "RuntimeError")

    def test_load_host_emits_request_bound_inactive_phase_events(self) -> None:
        nonce = "p" * 48
        events: list[dict[str, object]] = []
        host = persistent_worker.PersistentWorkerHost(
            self.config,
            nonce,
            event_emitter=events.append,
        )

        class FakeRuntime:
            loaded = False

            def lifecycle(self) -> dict[str, object]:
                return {"model_loaded": False}

            def load(self, *, phase_event_callback=None) -> dict[str, object]:
                ledger = candidate_contract.PhaseLedger(
                    event_callback=phase_event_callback,
                )
                with ledger.phase("load.fake_bounded_phase"):
                    pass
                return {"ready": True, "phase_timings": ledger.records}

        host.runtime = FakeRuntime()  # type: ignore[assignment]
        request_id = str(uuid.uuid4())
        request = {
            "schema_version": 1,
            "request_id": request_id,
            "session_nonce": nonce,
            "operation": "load",
            "playback": False,
            "fallback": False,
        }
        with patch.object(
            persistent_worker,
            "_load_stack_dump_watchdog",
            return_value=contextlib.nullcontext(),
        ) as watchdog:
            response = host.process(request)
        watchdog.assert_called_once_with(self.config)
        self.assertTrue(response["ready"], response)
        self.assertEqual(len(events), 2)
        self.assertEqual([item["event_sequence"] for item in events], [1, 2])
        self.assertEqual(
            [item["phase_progress"]["phase_state"] for item in events],
            ["started", "finished"],
        )
        for event in events:
            self.assertEqual(event["message_type"], "event")
            self.assertEqual(event["event"], "operation_phase_progress")
            self.assertEqual(event["request_id"], request_id)
            self.assertEqual(event["operation"], "load")
            self.assertFalse(event["production_routing_authorized"])
            self.assertFalse(event["playback"])
            self.assertFalse(event["generic_voice_used"])
            self.assertFalse(event["sapi_voice_used"])
            self.assertFalse(event["fallback_used"])

    def test_load_watchdog_is_bounded_and_always_cancelled(self) -> None:
        with (
            patch.object(persistent_worker.faulthandler, "is_enabled", return_value=False),
            patch.object(persistent_worker.faulthandler, "enable") as enable,
            patch.object(persistent_worker.faulthandler, "dump_traceback_later") as dump,
            patch.object(persistent_worker.faulthandler, "cancel_dump_traceback_later") as cancel,
            patch.object(persistent_worker.faulthandler, "disable") as disable,
        ):
            with persistent_worker._load_stack_dump_watchdog(self.config):
                pass
        enable.assert_called_once()
        dump.assert_called_once()
        self.assertEqual(dump.call_args.args[0], 120.0)
        self.assertTrue(dump.call_args.kwargs["repeat"])
        self.assertFalse(dump.call_args.kwargs["exit"])
        cancel.assert_called_once_with()
        disable.assert_called_once_with()

        with (
            patch.object(persistent_worker.faulthandler, "is_enabled", return_value=False),
            patch.object(persistent_worker.faulthandler, "enable"),
            patch.object(persistent_worker.faulthandler, "dump_traceback_later"),
            patch.object(
                persistent_worker.faulthandler,
                "cancel_dump_traceback_later",
            ) as cancel_after_failure,
            patch.object(persistent_worker.faulthandler, "disable") as disable_after_failure,
        ):
            with self.assertRaisesRegex(RuntimeError, "watchdog failure path"):
                with persistent_worker._load_stack_dump_watchdog(self.config):
                    raise RuntimeError("watchdog failure path")
        cancel_after_failure.assert_called_once_with()
        disable_after_failure.assert_called_once_with()

    def test_progress_protocol_uses_captured_stdout_during_redirect(self) -> None:
        protocol = io.BytesIO()
        payload = {"message_type": "event", "event": "operation_phase_progress"}
        with contextlib.redirect_stdout(io.StringIO()):
            persistent_worker._emit(payload, 4096, output=protocol)
        self.assertEqual(json.loads(protocol.getvalue().decode("utf-8")), payload)

    def test_client_persists_validated_phase_events_append_only(self) -> None:
        acceptance_root = candidate_contract.project_file(
            self.config["allowed_output_roots"][0]
        )
        acceptance_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="diagnostic_test_", dir=acceptance_root) as value:
            client = candidate_client.PersistentBlackwellVoiceCandidateClient(
                diagnostic_directory=Path(value),
            )
            client._prepare_diagnostics()
            event = {
                "schema_version": 1,
                "candidate_id": self.config["candidate_id"],
                "candidate_status": self.config["candidate_status"],
                "production_routing_authorized": False,
                "session_id": client.session_id,
                "request_id": str(uuid.uuid4()),
                "message_type": "event",
                "event": "operation_phase_progress",
                "event_sequence": 1,
                "operation": "load",
                "phase_progress": {
                    "phase_event_schema_version": 1,
                    "phase_state": "started",
                    "phase": "imports.torch",
                },
                "playback": False,
                "generic_voice_used": False,
                "sapi_voice_used": False,
                "fallback_used": False,
            }
            response = {"message_type": "response", "request_id": event["request_id"]}
            client._stdout_queue.put(event)
            client._stdout_queue.put(response)
            self.assertEqual(client._wait_message(timeout_seconds=1), response)
            self.assertEqual(client.events, [event])
            journal = Path(client.diagnostic_paths["phase_events"])
            journal = ROOT / journal
            self.assertEqual(json.loads(journal.read_text(encoding="utf-8")), event)
            second = candidate_client.PersistentBlackwellVoiceCandidateClient(
                diagnostic_directory=Path(value),
            )
            with self.assertRaisesRegex(
                candidate_client.PersistentCandidateProtocolError,
                "will not be overwritten",
            ):
                second._prepare_diagnostics()

    def test_acceptance_snapshot_is_read_only_and_complete(self) -> None:
        class FakeClient:
            diagnostic_paths = {"phase_events": "attempt/WORKER_PHASE_EVENTS.jsonl"}
            events = [{"event": "operation_phase_progress"}]
            stderr_tail = "Timeout stack"

        snapshot = acceptance_harness.client_diagnostic_snapshot(FakeClient())
        self.assertEqual(snapshot["diagnostic_paths"], FakeClient.diagnostic_paths)
        self.assertEqual(snapshot["phase_events"], FakeClient.events)
        self.assertEqual(snapshot["stderr_tail"], "Timeout stack")

    def test_resource_sampler_never_polls_external_gpu_in_background(self) -> None:
        with patch.object(
            persistent_worker,
            "_gpu_memory_used_mib",
            side_effect=[100.0, 140.0],
        ) as gpu_query:
            sampler = persistent_worker.ResourceSampler(interval_seconds=0.1)
            sampler.start()
            deadline = time.monotonic() + 1.0
            while sampler.samples < 3 and time.monotonic() < deadline:
                time.sleep(0.01)
            evidence = sampler.stop()

        self.assertEqual(gpu_query.call_count, 2)
        self.assertEqual(evidence["external_gpu_sample_count"], 2)
        self.assertGreaterEqual(evidence["host_sample_count"], 4)
        self.assertEqual(
            evidence["gpu_sampling_mode"],
            "boundary_only_external_nvidia_smi",
        )
        self.assertFalse(evidence["background_external_gpu_polling"])
        self.assertEqual(evidence["baseline_total_gpu_used_mib"], 100.0)
        self.assertEqual(evidence["peak_total_gpu_used_mib"], 140.0)

    def test_restricted_environment_does_not_copy_parent_secret_or_enable_load_by_default(self) -> None:
        nonce = "n" * 48
        with patch.dict(
            os.environ,
            {
                "USERNAME": "bounded-test-user",
                "USERPROFILE": r"C:\Users\bounded-test-user",
                "SystemRoot": r"C:\Windows",
                "PATH": r"C:\Windows\System32",
                "KIRA_UNRELATED_SECRET": "must-not-cross",
            },
            clear=True,
        ):
            env = candidate_client.restricted_candidate_environment(
                self.config,
                session_nonce=nonce,
                allow_gpu_model_load=False,
            )
        self.assertEqual(env["USERNAME"], "bounded-test-user")
        self.assertNotIn("KIRA_UNRELATED_SECRET", env)
        self.assertNotIn("KIRA_PERSISTENT_BLACKWELL_ALLOW_MODEL_LOAD", env)
        self.assertEqual(env["CUDA_VISIBLE_DEVICES"], "0")
        self.assertEqual(env["HF_HUB_OFFLINE"], "1")
        cache_root = candidate_contract.project_file(self.config["runtime_cache_root"]).resolve()
        for key in ("TORCHINDUCTOR_CACHE_DIR", "TRITON_CACHE_DIR", "TEMP", "TMP"):
            Path(env[key]).resolve().relative_to(cache_root)

    def test_request_contract_rejects_wrong_nonce_replay_private_text_and_overwrite(self) -> None:
        nonce = "x" * 48
        seen: set[str] = set()
        request_id = str(uuid.uuid4())
        base = {
            "schema_version": 1,
            "request_id": request_id,
            "session_nonce": nonce,
            "operation": "synthesize",
            "playback": False,
            "fallback": False,
        }
        accepted = candidate_contract.validate_envelope(
            base,
            config=self.config,
            session_nonce=nonce,
            seen_request_ids=seen,
        )
        self.assertEqual(accepted["request_id"], request_id)
        with self.assertRaisesRegex(ValueError, "replayed"):
            candidate_contract.validate_envelope(
                base,
                config=self.config,
                session_nonce=nonce,
                seen_request_ids=seen,
            )
        wrong = {**base, "request_id": str(uuid.uuid4()), "session_nonce": "y" * 48}
        with self.assertRaisesRegex(ValueError, "nonce mismatch"):
            candidate_contract.validate_envelope(
                wrong,
                config=self.config,
                session_nonce=nonce,
                seen_request_ids=seen,
            )

        text = "PRIVATE MIND: this must not become speech."
        private = {
            **base,
            "request_id": str(uuid.uuid4()),
            "text": text,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "channel": "public_spoken_only",
            "profile_sha256": self.config["approved_profile_sha256"],
            "reference_sha256": self.config["approved_reference_sha256"],
            "output_relative": (
                "RecoverySprint/continuation_20260802/"
                "persistent_blackwell_voice_candidate_acceptance/private_rejected.wav"
            ),
        }
        with self.assertRaisesRegex(ValueError, "private or factual"):
            candidate_contract.validate_synthesis_request(private, self.config)

    def test_fake_backend_loads_model_and_conditions_reference_once_across_two_generations(self) -> None:
        import numpy as np

        fake_torch = _FakeTorch()
        fake_model = _FakeModel(np, fake_torch.cuda)
        factory_calls: list[str] = []

        def factory(device: str) -> _FakeModel:
            factory_calls.append(device)
            fake_torch.cuda.allocated = 768 * 1024 * 1024
            fake_torch.cuda.reserved = 1024 * 1024 * 1024
            fake_torch.cuda.peak_allocated = fake_torch.cuda.allocated
            fake_torch.cuda.peak_reserved = fake_torch.cuda.reserved
            return fake_model

        def backend_loader(ledger: persistent_worker.PhaseLedger) -> dict[str, object]:
            return {
                "torch": fake_torch,
                "torchaudio": _FakeTorchaudio(),
                "numpy": np,
                "soundfile": None,
                "model_factory": factory,
                "assess_generated_speech_chunk": lambda samples, **kwargs: {
                    "passed": True,
                    "sample_count": int(samples.size),
                },
                "gentle_proximity_correction": lambda samples, **kwargs: samples,
                "split_for_tts": lambda text, max_chars: ([text], {"chunk_count": 1}),
                "spoken_words": lambda text: text.casefold().split(),
                "transformers_compatibility_imports": {},
            }

        qwen_checks: list[str] = []

        def absent(config: dict[str, object]) -> dict[str, object]:
            qwen_checks.append("checked")
            return {
                "query_succeeded": True,
                "qwen_absent_proven": True,
                "qwen_records": [],
                "model_state_changed": False,
            }
        runtime = persistent_worker.PersistentVoiceRuntime(
            self.config,
            backend_loader=backend_loader,
            qwen_probe=absent,
            identity_verifier=lambda config: {
                "profile_sha256": config["approved_profile_sha256"],
                "reference_sha256": config["approved_reference_sha256"],
            },
            environment_verifier=lambda config, require_load_opt_in: {"TEMP": "fake"},
            runtime_metadata_verifier=lambda config: {
                "chatterbox-tts": config["chatterbox_version"],
                "torch": config["torch_version"],
                "torchaudio": config["torchaudio_version"],
            },
            resource_sampler_factory=_FakeSampler,
        )
        first = runtime.load()
        second = runtime.load()
        self.assertTrue(first["ready"], first)
        self.assertTrue(second["ready"], second)
        self.assertTrue(second["model_reused"])
        self.assertEqual(factory_calls, ["cuda"])
        self.assertEqual(len(fake_model.prepare_calls), 1)
        self.assertEqual(runtime.model_load_count, 1)
        self.assertEqual(runtime.reference_conditioning_count, 1)
        self.assertTrue(first["gpu_proof"]["model_and_core_components_cuda"])
        self.assertTrue(first["gpu_proof"]["cuda_synchronize_after_conditioning_succeeded"])

        ledger = persistent_worker.PhaseLedger()
        _first_audio, first_check = runtime._generate_chunk(
            "First bounded sentence.", chunk_index=0, ledger=ledger
        )
        _second_audio, second_check = runtime._generate_chunk(
            "Second bounded sentence.", chunk_index=1, ledger=ledger
        )
        for check in (first_check, second_check):
            accepted = check["attempts"][0]
            self.assertEqual(accepted["output_tensor_device_type"], "cpu")
            self.assertTrue(accepted["output_tensor_returned_to_host"])
            self.assertTrue(accepted["official_host_return_contract_satisfied"])
            self.assertFalse(accepted["output_tensor_was_cuda"])
            self.assertEqual(check["accepted_attempt"], 1)
        self.assertEqual(len(fake_model.generate_calls), 2)
        for _text, kwargs in fake_model.generate_calls:
            self.assertNotIn("audio_prompt_path", kwargs)
        self.assertEqual(len(fake_model.prepare_calls), 1)
        self.assertEqual(len(qwen_checks), 3)  # Once before load and once per generation.
        unloaded = runtime.unload(reason="unit_test")
        self.assertTrue(unloaded["unloaded"])
        self.assertFalse(runtime.loaded)

    def test_truthful_gpu_evidence_requires_every_independent_cuda_gate(self) -> None:
        model = _FakeModel(object(), _FakeCuda())
        residency = persistent_worker._model_cuda_residency_evidence(model)
        accepted_attempt = {
            "attempt": 1,
            "passed": True,
            "output_tensor_device_type": "cpu",
            "output_tensor_returned_to_host": True,
            "official_host_return_contract_satisfied": True,
            "output_tensor_was_cuda": False,
            "rejected_warning_matches": [],
            "qwen_residency": {
                "query_succeeded": True,
                "qwen_absent_proven": True,
                "qwen_records": [],
                "model_state_changed": False,
            },
        }
        chunk_checks = [
            {"chunk_index": 0, "accepted_attempt": 1, "attempts": [accepted_attempt]}
        ]
        baseline = 768 * 1024 * 1024

        proof = persistent_worker._synthesis_cuda_execution_evidence(
            model_residency=residency,
            chunk_checks=chunk_checks,
            allocated_before=baseline,
            peak_allocated=baseline + 1,
            synchronize_before_succeeded=True,
            synchronize_after_succeeded=True,
        )
        self.assertTrue(proof["actual_gpu_execution"], proof)
        self.assertTrue(proof["accepted_output_tensors_host_cpu"])
        self.assertFalse(proof["accepted_output_tensors_cuda"])

        failures = {
            "model_residency": {**residency, "model_and_core_components_cuda": False},
            "no_peak_delta": baseline,
            "sync_before": False,
            "sync_after": False,
            "qwen_present": {
                **accepted_attempt,
                "qwen_residency": {
                    **accepted_attempt["qwen_residency"],
                    "qwen_absent_proven": False,
                    "qwen_records": [{"name": "qwen3.5:9b"}],
                },
            },
            "rejected_warning": {
                **accepted_attempt,
                "rejected_warning_matches": ["no kernel image"],
            },
        }
        for label, value in failures.items():
            bad_residency = value if label == "model_residency" else residency
            bad_peak = value if label == "no_peak_delta" else baseline + 1
            bad_before_sync = value if label == "sync_before" else True
            bad_after_sync = value if label == "sync_after" else True
            bad_attempt = value if label in {"qwen_present", "rejected_warning"} else accepted_attempt
            bad = persistent_worker._synthesis_cuda_execution_evidence(
                model_residency=bad_residency,
                chunk_checks=[
                    {"chunk_index": 0, "accepted_attempt": 1, "attempts": [bad_attempt]}
                ],
                allocated_before=baseline,
                peak_allocated=bad_peak,
                synchronize_before_succeeded=bad_before_sync,
                synchronize_after_succeeded=bad_after_sync,
            )
            with self.subTest(gate=label):
                self.assertFalse(bad["actual_gpu_execution"], bad)
                self.assertFalse(bad["accepted_output_tensors_cuda"])

    def test_client_refuses_gpu_load_and_synthesis_without_explicit_acceptance_opt_in(self) -> None:
        client = candidate_client.PersistentBlackwellVoiceCandidateClient()
        with self.assertRaises(candidate_client.PersistentCandidateNotAuthorized):
            client.load()
        with self.assertRaises(candidate_client.PersistentCandidateNotAuthorized):
            client.synthesize(
                text="This must remain blocked.",
                output_relative=(
                    "RecoverySprint/continuation_20260802/"
                    "persistent_blackwell_voice_candidate_acceptance/blocked.wav"
                ),
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

    def test_fresh_process_control_protocol_stays_unloaded_and_exits_cleanly(self) -> None:
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
            self.assertTrue(unloaded["unloaded"])
            self.assertFalse(unloaded["model_was_loaded"])
        finally:
            closed = client.close()
        self.assertIsNotNone(closed)
        self.assertTrue(closed["shutdown"])
        self.assertEqual(closed["owned_process_exit_code"], 0)
        self.assertFalse(closed["owned_process_forced_termination"])
        self.assertIsNone(client.process)

    def test_fresh_process_rejects_absent_and_wrong_nonce_without_importing_torch(self) -> None:
        nonce = "p" * 48
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
        self.assertIsNotNone(process.stdin)
        self.assertIsNotNone(process.stdout)
        hello = json.loads(process.stdout.readline())
        self.assertFalse(hello["model_loaded"])

        def read_response() -> tuple[dict[str, object], list[dict[str, object]]]:
            progress: list[dict[str, object]] = []
            while True:
                payload = json.loads(process.stdout.readline())
                if payload.get("message_type") == "event":
                    progress.append(payload)
                    continue
                return payload, progress

        for supplied in (None, "w" * 48):
            request = {
                "schema_version": 1,
                "request_id": str(uuid.uuid4()),
                "operation": "status",
                "playback": False,
                "fallback": False,
            }
            if supplied is not None:
                request["session_nonce"] = supplied
            process.stdin.write(json.dumps(request) + "\n")
            process.stdin.flush()
            rejected, progress = read_response()
            self.assertEqual(progress, [])
            self.assertEqual(rejected["reason"], "persistent_candidate_request_rejected")
            self.assertIn("nonce", rejected["error"])
            self.assertFalse(rejected["lifecycle"]["model_loaded"])
        blocked_load = {
            "schema_version": 1,
            "request_id": str(uuid.uuid4()),
            "session_nonce": nonce,
            "operation": "load",
            "playback": False,
            "fallback": False,
        }
        process.stdin.write(json.dumps(blocked_load) + "\n")
        process.stdin.flush()
        blocked, progress = read_response()
        self.assertGreaterEqual(len(progress), 2)
        self.assertEqual(progress[0]["phase_progress"]["phase_state"], "started")
        self.assertEqual(progress[-1]["phase_progress"]["phase_state"], "finished")
        self.assertFalse(blocked["ready"])
        self.assertEqual(blocked["reason"], "persistent_model_load_failed")
        self.assertIn("explicit acceptance opt-in", blocked["error"])
        self.assertFalse(blocked["lifecycle"]["model_loaded"])
        shutdown = {
            "schema_version": 1,
            "request_id": str(uuid.uuid4()),
            "session_nonce": nonce,
            "operation": "shutdown",
            "playback": False,
            "fallback": False,
        }
        process.stdin.write(json.dumps(shutdown) + "\n")
        process.stdin.flush()
        stopped, progress = read_response()
        self.assertEqual(progress, [])
        self.assertTrue(stopped["shutdown"])
        process.stdin.close()
        process.wait(timeout=10)
        stderr = process.stderr.read() if process.stderr else ""
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()
        self.assertEqual(process.returncode, 0, stderr)

    def test_later_gpu_harness_is_inert_without_all_explicit_bindings(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        described = subprocess.run(
            [sys.executable, "-B", str(ACCEPTANCE), "--describe"],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(described.returncode, 0, described.stderr)
        description = json.loads(described.stdout)
        self.assertFalse(description["promotion_performed"])
        self.assertFalse(description["playback_performed"])
        self.assertEqual(
            description["required_flags"],
            [
                "--run-gpu",
                "--confirm-no-active-blender",
                "--expected-candidate-config-sha256 <CURRENT_EXACT_SHA256>",
            ],
        )
        refused = subprocess.run(
            [sys.executable, "-B", str(ACCEPTANCE)],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(refused.returncode, 2)
        refusal = json.loads(refused.stdout)
        self.assertFalse(refusal["gpu_started"])
        self.assertEqual(
            refusal["reason"],
            "explicit_gpu_no_active_blender_and_exact_config_hash_required",
        )

        missing_hash = subprocess.run(
            [
                sys.executable,
                "-B",
                str(ACCEPTANCE),
                "--run-gpu",
                "--confirm-no-active-blender",
            ],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(missing_hash.returncode, 2)
        self.assertFalse(json.loads(missing_hash.stdout)["gpu_started"])

    def test_one_heavy_workload_probe_requires_every_ollama_model_absent(self) -> None:
        with patch.object(
            acceptance_harness.urllib_request,
            "urlopen",
            return_value=_FakeUrlResponse({"models": []}),
        ):
            empty = acceptance_harness.ollama_residency_evidence(self.config)
        self.assertTrue(empty["all_models_absent_proven"])
        self.assertEqual(empty["resident_models"], [])
        self.assertFalse(empty["model_state_changed"])

        with patch.object(
            acceptance_harness.urllib_request,
            "urlopen",
            return_value=_FakeUrlResponse(
                {
                    "models": [
                        {
                            "name": "llama3.1:8b",
                            "model": "llama3.1:8b",
                            "digest": "a" * 64,
                            "size_vram": 5_000_000_000,
                        }
                    ]
                }
            ),
        ):
            occupied = acceptance_harness.ollama_residency_evidence(self.config)
        self.assertFalse(occupied["all_models_absent_proven"])
        self.assertEqual(occupied["resident_models"][0]["name"], "llama3.1:8b")


if __name__ == "__main__":
    unittest.main()
