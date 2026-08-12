from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import threading
import time
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core import persistent_blackwell_voice_integration_v2 as integration  # noqa: E402


class _FakeProcess:
    pid = 525252

    def __init__(self) -> None:
        self.running = True

    def poll(self):
        return None if self.running else 0


class _FakeV2Client:
    instances: list["_FakeV2Client"] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = dict(kwargs)
        self.process = _FakeProcess()
        self.session_id = hashlib.sha256(
            f"fake-v2-client-{len(self.__class__.instances) + 1}".encode("utf-8")
        ).hexdigest()[:24]
        self.start_calls = 0
        self.load_calls = 0
        self.synthesis_calls = 0
        self.unload_calls = 0
        self.close_calls = 0
        self.staging_paths: list[Path] = []
        self.__class__.instances.append(self)

    @staticmethod
    def _qwen_absent() -> dict:
        return {
            "query_succeeded": True,
            "qwen_absent_proven": True,
            "qwen_records": [],
            "model_state_changed": False,
        }

    def start(self) -> dict:
        self.start_calls += 1
        return {"ready": True, "model_loaded": False}

    def load(self) -> dict:
        self.load_calls += 1
        reused = self.load_calls > 1
        return {
            "ready": True,
            "reason": "already_loaded" if reused else "loaded",
            "model_reused": reused,
            "lifecycle": {
                "model_loaded": True,
                "model_load_count": 1,
                "reference_conditioning_count": 1,
                "conditioned_reference_sha256": integration.APPROVED_REFERENCE_SHA256,
            },
            "identity": {
                "profile_sha256": integration.APPROVED_PROFILE_SHA256,
                "reference_sha256": integration.APPROVED_REFERENCE_SHA256,
            },
            "runtime_versions": {
                "torch": "2.11.0+cu130",
                "torchaudio": "2.11.0+cu130",
                "chatterbox-tts": "0.1.7",
            },
            "runtime_cuda_checks": {
                "capability": True,
                "cuda_available": True,
                "cuda_runtime": True,
                "device": True,
                "sm_120": True,
                "torch_runtime": True,
                "torchaudio_runtime": True,
            },
            "parent_qwen_residency_before_load": self._qwen_absent(),
            "gpu_proof": {
                "actual_gpu_allocation": True,
                "persistent_model_allocation_present": True,
                "cuda_synchronize_before_model_load_succeeded": True,
                "cuda_synchronize_after_conditioning_succeeded": True,
                "model_and_core_components_cuda": True,
                "no_rejected_runtime_warnings": True,
            },
        }


    def synthesize(self, *, text: str, output_relative: str, **_kwargs) -> dict:
        self.synthesis_calls += 1
        target = (ROOT / output_relative).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(target), "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(24000)
            writer.writeframes((2000).to_bytes(2, "little", signed=True) * 2400)
        self.staging_paths.append(target)
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return {
            "generated": True,
            "session_id": self.session_id,
            "engine": "chatterbox_tts",
            "device": "cuda",
            "channel": "public_spoken_only",
            "requested_text_bound": True,
            "conditioning_reused": True,
            "text_sha256": text_hash,
            "profile_sha256": integration.APPROVED_PROFILE_SHA256,
            "reference_sha256": integration.APPROVED_REFERENCE_SHA256,
            "playback": False,
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "gpu_proof": {
                "actual_gpu_execution": True,
                "persistent_model_allocation_present": True,
                "model_and_core_components_cuda": True,
                "cuda_synchronize_before_generation_succeeded": True,
                "cuda_synchronize_after_generation_succeeded": True,
                "generation_peak_exceeded_baseline": True,
                "no_rejected_runtime_warnings": True,
                "qwen_absence_proven_for_accepted_generation": True,
                "official_host_return_contract_satisfied": True,
                "accepted_output_tensors_host_cpu": True,
                "accepted_output_tensors_cuda": False,
            },
            "chunk_checks": [
                {
                    "accepted_attempt": 1,
                    "attempts": [
                        {
                            "attempt": 1,
                            "passed": True,
                            "output_tensor_was_cuda": False,
                            "output_tensor_returned_to_host": True,
                            "official_host_return_contract_satisfied": True,
                            "qwen_residency": self._qwen_absent(),
                        }
                    ],
                }
            ],
            "parent_qwen_residency_before_synthesis": self._qwen_absent(),
            "audio_path": str(target),
            "wav_validation": integration._validate_non_silent_wav(target),
        }

    def unload(self) -> dict:
        self.unload_calls += 1
        return {"unloaded": True}

    def close(self) -> dict:
        self.close_calls += 1
        self.process.running = False
        return {
            "owned_process_exit_code": 0,
            "owned_process_forced_termination": False,
        }


class _SparseReuseFake(_FakeV2Client):
    """Match the sealed worker's compact already-loaded response exactly."""

    def load(self) -> dict:
        if self.load_calls == 0:
            return super().load()
        self.load_calls += 1
        return {
            "ready": True,
            "reason": "already_loaded",
            "model_reused": True,
            "parent_qwen_residency_before_load": self._qwen_absent(),
            "gpu_proof": {
                "actual_gpu_allocation": True,
                "persistent_model_allocation_present": True,
                "cuda_synchronize_before_model_load_succeeded": True,
                "cuda_synchronize_after_conditioning_succeeded": True,
                "model_and_core_components_cuda": True,
                "no_rejected_runtime_warnings": True,
            },
            "phase_timings": [],
            "lifecycle": {
                "model_loaded": True,
                "model_load_count": 1,
                "reference_conditioning_count": 1,
                "successful_synthesis_count": self.synthesis_calls,
                "generation_attempt_count": self.synthesis_calls,
                "conditioned_reference_sha256": integration.APPROVED_REFERENCE_SHA256,
            },
        }


class _ForbiddenVoiceFake(_FakeV2Client):
    def synthesize(self, *, text: str, output_relative: str, **kwargs) -> dict:
        response = super().synthesize(
            text=text,
            output_relative=output_relative,
            **kwargs,
        )
        response["generic_voice_used"] = True
        response["sapi_voice_used"] = True
        return response


class _SilentWavFake(_FakeV2Client):
    def synthesize(self, *, text: str, output_relative: str, **kwargs) -> dict:
        response = super().synthesize(
            text=text,
            output_relative=output_relative,
            **kwargs,
        )
        target = (ROOT / output_relative).resolve()
        with wave.open(str(target), "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(24000)
            writer.writeframes(b"\x00\x00" * 2400)
        response["wav_validation"] = integration._validate_non_silent_wav(target)
        return response


class _InterruptibleFakeProcess:
    pid = 626262

    def __init__(self, release_event: threading.Event) -> None:
        self.release_event = release_event
        self.running = True
        self.returncode = None
        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.terminate_calls = 0
        self.kill_calls = 0
        self.wait_calls = 0

    def poll(self):
        return None if self.running else self.returncode

    def terminate(self) -> None:
        self.terminate_calls += 1
        self.running = False
        self.returncode = -15
        self.release_event.set()

    def kill(self) -> None:
        self.kill_calls += 1
        self.running = False
        self.returncode = -9
        self.release_event.set()

    def wait(self, timeout=None):
        del timeout
        self.wait_calls += 1
        return self.returncode


class _StuckRequestFake(_FakeV2Client):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.request_started = threading.Event()
        self.request_released = threading.Event()
        self.process = _InterruptibleFakeProcess(self.request_released)

    def synthesize(self, *, text: str, output_relative: str, **_kwargs) -> dict:
        del text, output_relative
        self.synthesis_calls += 1
        self.request_started.set()
        self.request_released.wait(
            timeout=float(self.kwargs.get("request_timeout_seconds", 900.0))
        )
        raise RuntimeError("fake request interrupted by exact owned-process close")


class _InterruptibleNormalFake(_FakeV2Client):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.process = _InterruptibleFakeProcess(threading.Event())


class _IdleUnloadFake(_FakeV2Client):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.model_is_loaded = False

    def load(self) -> dict:
        reused = self.model_is_loaded
        result = super().load()
        result["model_reused"] = reused
        self.model_is_loaded = True
        return result

    def unload(self) -> dict:
        self.unload_calls += 1
        was_loaded = self.model_is_loaded
        self.model_is_loaded = False
        return {
            "unloaded": True,
            "model_was_loaded": was_loaded,
            "lifecycle": {"model_loaded": False},
        }


class _UnclosableFake(_FakeV2Client):
    def close(self) -> dict:
        self.close_calls += 1
        # Deliberately leave the fake owned process running.
        return {
            "owned_process_exit_code": None,
            "owned_process_forced_termination": False,
        }


class PersistentBlackwellVoiceIntegrationV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        _FakeV2Client.instances.clear()
        _ForbiddenVoiceFake.instances.clear()

    def tearDown(self) -> None:
        for fake_class in (_FakeV2Client, _ForbiddenVoiceFake):
            for client in fake_class.instances:
                for path in client.staging_paths:
                    path.unlink(missing_ok=True)

    def test_exact_v2_package_and_full_gpu_pass_report_are_bound(self) -> None:
        binding = integration._acceptance_binding()
        self.assertTrue(binding["valid"])
        self.assertEqual(binding["sha256"], integration.FULL_GPU_PASS_REPORT_SHA256)
        self.assertEqual(
            integration.CANDIDATE_CLIENT_MODULE,
            "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v2.candidate_client",
        )
        fake_module = SimpleNamespace(
            __file__=str(integration.CANDIDATE_CLIENT_PATH),
            PersistentBlackwellVoiceCandidateClient=_FakeV2Client,
        )
        with patch.object(integration.importlib, "import_module", return_value=fake_module) as loader:
            loaded = integration._load_sealed_client_class()
        self.assertIs(loaded, _FakeV2Client)
        loader.assert_called_once_with(integration.CANDIDATE_CLIENT_MODULE)

    def test_acceptance_artifact_hash_mismatch_fails_before_candidate_import(self) -> None:
        original_hash = integration._sha256_file

        def mismatched_candidate_hash(path: Path) -> str:
            if Path(path).resolve() == integration.CANDIDATE_CLIENT_PATH.resolve():
                return "0" * 64
            return original_hash(Path(path))

        with (
            patch.object(
                integration,
                "_sha256_file",
                side_effect=mismatched_candidate_hash,
            ),
            patch.object(integration.importlib, "import_module") as loader,
        ):
            with self.assertRaisesRegex(RuntimeError, "artifact hash mismatch"):
                integration._load_sealed_client_class()
        loader.assert_not_called()

    def test_default_off_constructs_no_worker_and_generates_nothing(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_FakeV2Client
        )
        with patch.dict(os.environ, {integration.FEATURE_FLAG: "0"}, clear=False):
            begun = manager.begin_session("kira:test-off")
            result = manager.synthesize(
                text="This must stay inactive.",
                target=ROOT / "Voice" / "generated" / "never_v2.wav",
                pcm_output_gain_db=0.0,
                proximity_cut_hz=0.0,
                proximity_cut_mix=0.0,
            )
        self.assertFalse(begun["begun"])
        self.assertFalse(result["generated"])
        self.assertEqual(_FakeV2Client.instances, [])

    def test_session_owned_worker_prewarms_reuses_synthesizes_and_cleans_up(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_FakeV2Client
        )
        output_root = integration.GENERATED_AUDIO_ROOT / "v2_integration_tests"
        output_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output_root) as temp_dir:
            target = Path(temp_dir) / "result.wav"
            with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
                begun = manager.begin_session("kira:test-v2")
                first_warm = manager.prewarm("kira:test-v2")
                second_warm = manager.prewarm("kira:test-v2")
                result = manager.synthesize(
                    text="A bounded public spoken sentence.",
                    target=target,
                    pcm_output_gain_db=0.0,
                    proximity_cut_hz=0.0,
                    proximity_cut_mix=0.0,
                )
                status = manager.status()
                closed = manager.close("unit_test")
            self.assertTrue(target.is_file())
        self.assertTrue(begun["begun"])
        self.assertTrue(first_warm["warmed"], first_warm)
        self.assertTrue(
            first_warm["load_telemetry"]["qwen_residency_before_load"][
                "qwen_absent_proven"
            ]
        )
        self.assertTrue(
            first_warm["load_telemetry"]["gpu_proof"]["actual_gpu_allocation"]
        )
        self.assertTrue(second_warm["warmed"], second_warm)
        self.assertTrue(second_warm["model_reused"])
        self.assertTrue(result["generated"], result)
        self.assertEqual(result["route_id"], "blackwell_gpu_persistent_candidate_v2_test_only")
        self.assertEqual(result["sidecar_lifecycle"], "session_owned_persistent_candidate_v2")
        self.assertFalse(result["playback"])
        self.assertFalse(result["generic_voice_used"])
        self.assertFalse(result["sapi_voice_used"])
        self.assertFalse(result["production_route_connected"])
        self.assertTrue(result["test_only_injected_client"])
        self.assertIsNone(result["approved_voice_path_used"])
        self.assertFalse(result["persistent_route_eligible"])
        self.assertTrue(status["owned_worker_running"])
        self.assertTrue(closed["cleanup"]["owned_worker_closed"])
        self.assertTrue(closed["cleanup"]["unload_telemetry"]["reported"])
        self.assertTrue(closed["cleanup"]["unload_telemetry"]["unloaded"])
        self.assertEqual(len(_FakeV2Client.instances), 1)
        client = _FakeV2Client.instances[0]
        self.assertEqual(client.kwargs["allow_gpu_model_load"], True)
        self.assertEqual(client.start_calls, 1)
        self.assertEqual(client.load_calls, 3)
        self.assertEqual(client.synthesis_calls, 1)
        self.assertEqual(client.unload_calls, 1)
        self.assertEqual(client.close_calls, 1)

    def test_sparse_worker_reuse_response_preserves_one_session_for_two_turns(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_SparseReuseFake
        )
        output_root = integration.GENERATED_AUDIO_ROOT / "v2_integration_tests"
        output_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output_root) as temp_dir:
            first_target = Path(temp_dir) / "first.wav"
            second_target = Path(temp_dir) / "second.wav"
            with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
                first_warm = manager.prewarm("kira:sparse-reuse")
                first = manager.synthesize(
                    text="The first bounded reuse turn.",
                    target=first_target,
                    pcm_output_gain_db=0.0,
                    proximity_cut_hz=0.0,
                    proximity_cut_mix=0.0,
                )
                second = manager.synthesize(
                    text="The second bounded reuse turn.",
                    target=second_target,
                    pcm_output_gain_db=0.0,
                    proximity_cut_hz=0.0,
                    proximity_cut_mix=0.0,
                )
                status = manager.status()
                closed = manager.close("sparse_reuse_unit_test")
            self.assertTrue(first_target.is_file())
            self.assertTrue(second_target.is_file())
        self.assertTrue(first_warm["warmed"], first_warm)
        self.assertFalse(first_warm["model_reused"])
        self.assertTrue(first["generated"], first)
        self.assertTrue(second["generated"], second)
        self.assertTrue(first["persistent_worker_reused"])
        self.assertTrue(second["persistent_worker_reused"])
        reuse_events = [
            event
            for event in status["events"]
            if event.get("event") == "v2_prewarm_completed"
            and event.get("model_reused") is True
        ]
        self.assertEqual(len(reuse_events), 2)
        self.assertTrue(closed["cleanup"]["owned_worker_closed"])
        self.assertEqual(len(_FakeV2Client.instances), 1)
        client = _FakeV2Client.instances[0]
        self.assertIsInstance(client, _SparseReuseFake)
        self.assertEqual(client.start_calls, 1)
        self.assertEqual(client.load_calls, 3)
        self.assertEqual(client.synthesis_calls, 2)

    def test_model_only_suspend_reuses_process_client_but_not_cuda_model(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_IdleUnloadFake
        )
        output_root = integration.GENERATED_AUDIO_ROOT / "v2_integration_tests"
        output_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output_root) as temp_dir:
            target = Path(temp_dir) / "serialized_reload.wav"
            with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
                prewarm = manager.prewarm("kira:serialized-reload")
                before = manager.status()
                suspended = manager.suspend_if_owner(
                    "kira:serialized-reload",
                    "unit_test_before_exact_qwen",
                    expected_generation=int(before["session_generation"]),
                )
                after_suspend = manager.status()
                result = manager.synthesize(
                    text="The same worker reloads the approved model after Qwen.",
                    target=target,
                    pcm_output_gain_db=0.0,
                    proximity_cut_hz=0.0,
                    proximity_cut_mix=0.0,
                )
                after_voice = manager.status()
                closed = manager.close("serialized_reload_unit_test")
            self.assertTrue(target.is_file())

        self.assertTrue(prewarm["warmed"], prewarm)
        self.assertFalse(prewarm["worker_process_reused"])
        self.assertTrue(suspended["model_release_proven"], suspended)
        self.assertTrue(suspended["owned_worker_preserved"], suspended)
        self.assertTrue(result["generated"], result)
        self.assertTrue(result["persistent_worker_reused"])
        self.assertFalse(result["persistent_model_reused"])
        self.assertTrue(result["lazy_model_reload_performed"])
        identity_keys = (
            "session_owner",
            "session_generation",
            "owned_client_generation",
            "owned_worker_pid",
            "owned_worker_session_id",
        )
        self.assertEqual(
            {key: before[key] for key in identity_keys},
            {key: after_suspend[key] for key in identity_keys},
        )
        self.assertEqual(
            {key: before[key] for key in identity_keys},
            {key: after_voice[key] for key in identity_keys},
        )
        self.assertTrue(before["model_loaded"])
        self.assertFalse(after_suspend["model_loaded"])
        self.assertTrue(after_voice["model_loaded"])
        self.assertEqual(result["session_id"], before["owned_worker_session_id"])
        self.assertTrue(closed["cleanup"]["owned_worker_closed"])

    def test_generic_or_sapi_claim_fails_closed_and_closes_owned_worker(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_ForbiddenVoiceFake
        )
        output_root = integration.GENERATED_AUDIO_ROOT / "v2_integration_tests"
        output_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output_root) as temp_dir:
            target = Path(temp_dir) / "rejected.wav"
            with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
                self.assertTrue(manager.begin_session("kira:forbidden-gate")["begun"])
                self.assertTrue(manager.prewarm("kira:forbidden-gate")["warmed"])
                result = manager.synthesize(
                    text="Only Kira's approved voice is permitted.",
                    target=target,
                    pcm_output_gain_db=0.0,
                    proximity_cut_hz=0.0,
                    proximity_cut_mix=0.0,
                )
            self.assertFalse(target.exists())
        self.assertFalse(result["generated"], result)
        self.assertIn("generic_voice_used_contract_mismatch", result["issues"])
        self.assertIn("sapi_voice_used_contract_mismatch", result["issues"])
        self.assertTrue(result["owned_worker_cleanup"]["owned_worker_closed"])

    def test_silent_candidate_wav_is_rejected_and_owned_worker_is_closed(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_SilentWavFake
        )
        output_root = integration.GENERATED_AUDIO_ROOT / "v2_integration_tests"
        output_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output_root) as temp_dir:
            target = Path(temp_dir) / "silent_rejected.wav"
            with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
                self.assertTrue(manager.prewarm("kira:silent-wav")["warmed"])
                result = manager.synthesize(
                    text="A silent file must never pass as Kira's voice.",
                    target=target,
                    pcm_output_gain_db=0.0,
                    proximity_cut_hz=0.0,
                    proximity_cut_mix=0.0,
                )
            self.assertFalse(target.exists())
        self.assertFalse(result["generated"], result)
        self.assertIn("candidate_staging_wav_invalid_or_silent", result["issues"])
        self.assertIn("worker_wav_validation_not_bound", result["issues"])
        self.assertTrue(result["owned_worker_cleanup"]["owned_worker_closed"])

    def test_unsafe_or_existing_target_is_rejected_without_writing_or_overwrite(self) -> None:
        output_root = integration.GENERATED_AUDIO_ROOT / "v2_integration_tests"
        output_root.mkdir(parents=True, exist_ok=True)
        outside_root = ROOT / "RecoverySprint" / "runtime_cache" / "v2_target_tests"
        outside_root.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(dir=outside_root) as outside_dir:
            outside_target = Path(outside_dir) / "outside_generated_root.wav"
            manager = integration.PersistentBlackwellVoiceIntegrationV2(
                client_factory=_FakeV2Client
            )
            with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
                self.assertTrue(manager.prewarm("kira:unsafe-target")["warmed"])
                outside_result = manager.synthesize(
                    text="This target is outside the approved generated-audio root.",
                    target=outside_target,
                    pcm_output_gain_db=0.0,
                    proximity_cut_hz=0.0,
                    proximity_cut_mix=0.0,
                )
            self.assertFalse(outside_target.exists())
            outside_client = _FakeV2Client.instances[-1]
            self.assertEqual(outside_client.synthesis_calls, 0)
            self.assertEqual(outside_client.close_calls, 1)
            self.assertFalse(outside_result["generated"], outside_result)
            self.assertEqual(outside_result["error_type"], "ValueError")

        with tempfile.TemporaryDirectory(dir=output_root) as temp_dir:
            existing_target = Path(temp_dir) / "must_not_overwrite.wav"
            original_payload = b"existing owner file must remain byte-for-byte"
            existing_target.write_bytes(original_payload)
            manager = integration.PersistentBlackwellVoiceIntegrationV2(
                client_factory=_FakeV2Client
            )
            with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
                self.assertTrue(manager.prewarm("kira:no-overwrite")["warmed"])
                existing_result = manager.synthesize(
                    text="This must not overwrite an existing file.",
                    target=existing_target,
                    pcm_output_gain_db=0.0,
                    proximity_cut_hz=0.0,
                    proximity_cut_mix=0.0,
                )
            self.assertEqual(existing_target.read_bytes(), original_payload)
            existing_client = _FakeV2Client.instances[-1]
            self.assertEqual(existing_client.synthesis_calls, 0)
            self.assertEqual(existing_client.close_calls, 1)
            self.assertFalse(existing_result["generated"], existing_result)
            self.assertEqual(existing_result["error_type"], "FileExistsError")

    def test_disabling_feature_on_next_entry_closes_owned_worker(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_FakeV2Client
        )
        with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
            self.assertTrue(manager.prewarm("kira:feature-toggle")["warmed"])
        client = _FakeV2Client.instances[-1]
        with patch.dict(os.environ, {integration.FEATURE_FLAG: "0"}, clear=False):
            result = manager.begin_session("kira:feature-toggle")
        self.assertFalse(result["begun"], result)
        self.assertEqual(result["reason"], "persistent_blackwell_v2_feature_flag_disabled")
        self.assertTrue(result["owned_worker_cleanup"]["owned_worker_closed"])
        self.assertEqual(client.unload_calls, 1)
        self.assertEqual(client.close_calls, 1)
        self.assertFalse(result["owned_worker_running"])
        self.assertEqual(result["session_owner"], "")

    def test_owner_switch_closes_prior_owned_worker_before_new_owner_is_recorded(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_FakeV2Client
        )
        with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
            self.assertTrue(manager.prewarm("kira:owner-one")["warmed"])
            prior_client = _FakeV2Client.instances[-1]
            switched = manager.begin_session("kira:owner-two")
        self.assertTrue(switched["begun"], switched)
        self.assertEqual(switched["session_owner"], "kira:owner-two")
        self.assertFalse(switched["owned_worker_running"])
        self.assertFalse(switched["model_loaded"])
        self.assertEqual(prior_client.unload_calls, 1)
        self.assertEqual(prior_client.close_calls, 1)
        self.assertFalse(prior_client.process.running)
        self.assertTrue(switched["events"][-1]["prior_owned_worker_closed"])

    def test_dead_owned_process_clears_model_loaded_truth(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_FakeV2Client
        )
        with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
            self.assertTrue(manager.prewarm("kira:dead-process")["warmed"])
            client = _FakeV2Client.instances[-1]
            client.process.running = False
            status = manager.status()
            closed = manager.close("dead_process_test_cleanup")
        self.assertFalse(status["owned_worker_running"])
        self.assertFalse(status["model_loaded"])
        self.assertFalse(closed["released"])

    def test_release_interrupts_stuck_inflight_request_and_closes_exact_owned_process(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_StuckRequestFake
        )
        output_root = integration.GENERATED_AUDIO_ROOT / "v2_integration_tests"
        output_root.mkdir(parents=True, exist_ok=True)
        thread_result: dict = {}
        with tempfile.TemporaryDirectory(dir=output_root) as temp_dir:
            target = Path(temp_dir) / "stuck_request_must_not_exist.wav"
            with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
                self.assertTrue(manager.prewarm("kira:stuck-request")["warmed"])
                client = _FakeV2Client.instances[-1]
                exact_process = client.process

                def run_stuck_request() -> None:
                    thread_result.update(
                        manager.synthesize(
                            text="Interrupt this bounded fake request.",
                            target=target,
                            pcm_output_gain_db=0.0,
                            proximity_cut_hz=0.0,
                            proximity_cut_mix=0.0,
                        )
                    )

                request_thread = threading.Thread(target=run_stuck_request, daemon=True)
                request_thread.start()
                self.assertTrue(client.request_started.wait(timeout=2.0))
                self.assertEqual(client.kwargs["request_timeout_seconds"], 900.0)
                release_started = time.perf_counter()
                released = manager.close("interrupt_stuck_request")
                release_elapsed = time.perf_counter() - release_started
                request_thread.join(timeout=2.0)
            self.assertFalse(target.exists())

        self.assertLess(release_elapsed, 1.0)
        self.assertFalse(request_thread.is_alive())
        self.assertTrue(released["cleanup"]["owned_worker_closed"])
        self.assertTrue(released["cleanup"]["forced_for_inflight_operation"])
        self.assertIs(client.process, exact_process)
        self.assertEqual(exact_process.terminate_calls, 1)
        self.assertEqual(exact_process.kill_calls, 0)
        self.assertGreaterEqual(exact_process.wait_calls, 1)
        self.assertFalse(thread_result["generated"], thread_result)
        self.assertEqual(thread_result["reason"], "persistent_blackwell_v2_synthesis_cancelled")
        self.assertFalse(thread_result["persistent_route_eligible"])

    def test_real_client_wait_observes_terminated_owned_process_without_900s_stall(self) -> None:
        client_class = integration._load_sealed_client_class()
        client = client_class(
            allow_gpu_model_load=False,
            startup_timeout_seconds=30.0,
            request_timeout_seconds=900.0,
        )
        release_event = threading.Event()
        exact_process = _InterruptibleFakeProcess(release_event)
        client.process = exact_process
        observed: dict = {}

        def wait_for_message() -> None:
            try:
                client._wait_message(timeout_seconds=900.0)
            except Exception as exc:  # exact exception class belongs to sealed client
                observed["error_type"] = type(exc).__name__

        wait_thread = threading.Thread(target=wait_for_message, daemon=True)
        wait_thread.start()
        time.sleep(0.05)
        started = time.perf_counter()
        cleanup = integration.PersistentBlackwellVoiceIntegrationV2._abort_exact_owned_client(
            client, "real_client_fake_popen_interrupt_test"
        )
        wait_thread.join(timeout=2.0)
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 1.0)
        self.assertFalse(wait_thread.is_alive())
        self.assertTrue(cleanup["owned_worker_closed"])
        self.assertIs(client.process, exact_process)
        self.assertEqual(observed["error_type"], "PersistentCandidateProtocolError")

    def test_worker_idle_unload_is_rechecked_and_reloaded_before_synthesis(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_IdleUnloadFake
        )
        output_root = integration.GENERATED_AUDIO_ROOT / "v2_integration_tests"
        output_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output_root) as temp_dir:
            target = Path(temp_dir) / "idle_reloaded.wav"
            with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
                self.assertTrue(manager.prewarm("kira:idle-reload")["warmed"])
                client = _FakeV2Client.instances[-1]
                # Simulate the sealed worker's 600-second idle auto-unload:
                # process alive, host's prior local bit stale, worker model gone.
                client.model_is_loaded = False
                result = manager.synthesize(
                    text="Reload after a truthful worker idle unload.",
                    target=target,
                    pcm_output_gain_db=0.0,
                    proximity_cut_hz=0.0,
                    proximity_cut_mix=0.0,
                )
                loaded_after_synthesis = client.model_is_loaded
                manager.close("idle_reload_test_cleanup")
            self.assertTrue(target.is_file())

        self.assertTrue(result["generated"], result)
        self.assertTrue(result["persistent_worker_reused"])
        self.assertFalse(result["persistent_model_reused"])
        self.assertTrue(result["lazy_model_reload_performed"])
        self.assertEqual(client.load_calls, 2)
        self.assertTrue(loaded_after_synthesis)
        self.assertFalse(client.model_is_loaded)

    def test_owner_switch_after_worker_response_cannot_promote_prior_session_wav(self) -> None:
        output_root = integration.GENERATED_AUDIO_ROOT / "v2_integration_tests"
        output_root.mkdir(parents=True, exist_ok=True)
        validation_started = threading.Event()
        continue_validation = threading.Event()
        validation_calls = 0
        original_validator = integration._validate_non_silent_wav
        thread_result: dict = {}

        class PromotionBoundaryFake(_InterruptibleNormalFake):
            def synthesize(self, **kwargs) -> dict:
                # The fake worker's own response uses the unpatched validator.
                # The first paused call below is therefore unambiguously the
                # host staging validation after the worker response and before
                # the locked final-target commit.
                with patch.object(
                    integration, "_validate_non_silent_wav", original_validator
                ):
                    return super().synthesize(**kwargs)

        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=PromotionBoundaryFake
        )

        def paused_validator(path: Path) -> dict:
            nonlocal validation_calls
            validation_calls += 1
            result = original_validator(path)
            if validation_calls == 1:
                validation_started.set()
                self.assertTrue(continue_validation.wait(timeout=2.0))
            return result

        with tempfile.TemporaryDirectory(dir=output_root) as temp_dir:
            target = Path(temp_dir) / "prior_owner_must_not_be_promoted.wav"
            with (
                patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False),
                patch.object(integration, "_validate_non_silent_wav", side_effect=paused_validator),
            ):
                self.assertTrue(manager.prewarm("kira:prior-owner")["warmed"])

                def run_request() -> None:
                    thread_result.update(
                        manager.synthesize(
                            text="Do not promote this after the owner changes.",
                            target=target,
                            pcm_output_gain_db=0.0,
                            proximity_cut_hz=0.0,
                            proximity_cut_mix=0.0,
                        )
                    )

                request_thread = threading.Thread(target=run_request, daemon=True)
                request_thread.start()
                self.assertTrue(validation_started.wait(timeout=2.0))
                switched = manager.begin_session("kira:new-owner")
                continue_validation.set()
                request_thread.join(timeout=2.0)

            self.assertFalse(target.exists())

        self.assertFalse(request_thread.is_alive())
        self.assertTrue(switched["begun"], switched)
        self.assertEqual(switched["session_owner"], "kira:new-owner")
        self.assertFalse(thread_result["generated"], thread_result)
        self.assertTrue(thread_result["cancelled"])
        self.assertFalse(thread_result["persistent_route_eligible"])

    def test_exclusive_link_eexist_race_blocks_fallback_and_preserves_contested_target(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_FakeV2Client
        )
        output_root = integration.GENERATED_AUDIO_ROOT / "v2_integration_tests"
        output_root.mkdir(parents=True, exist_ok=True)
        original_link = os.link

        with tempfile.TemporaryDirectory(dir=output_root) as temp_dir:
            target = Path(temp_dir) / "contested.wav"

            def lose_exclusive_link_race(source: Path, destination: Path) -> None:
                # Simulate another writer winning after our pre-check but
                # before the exclusive link call.
                destination.write_bytes(b"other-route-owned-target")
                raise FileExistsError(str(destination))

            with (
                patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False),
                patch.object(integration.os, "link", side_effect=lose_exclusive_link_race),
            ):
                self.assertTrue(manager.prewarm("kira:eexist-race")["warmed"])
                result = manager.synthesize(
                    text="A contested target must fail closed.",
                    target=target,
                    pcm_output_gain_db=0.0,
                    proximity_cut_hz=0.0,
                    proximity_cut_mix=0.0,
                )

            self.assertEqual(target.read_bytes(), b"other-route-owned-target")

        self.assertFalse(result["generated"], result)
        self.assertEqual(result["error_type"], "FileExistsError")
        self.assertFalse(result["linked_target_cleanup_proven"])
        self.assertFalse(result["fallback_allowed"])
        self.assertTrue(result["route_blocked"])

    def test_invalid_final_wav_is_quarantined_if_staging_link_disappears(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_FakeV2Client
        )
        output_root = integration.GENERATED_AUDIO_ROOT / "v2_integration_tests"
        output_root.mkdir(parents=True, exist_ok=True)
        original_link = os.link
        original_validator = integration._validate_non_silent_wav

        with tempfile.TemporaryDirectory(dir=output_root) as temp_dir:
            target = Path(temp_dir) / "invalid_final.wav"

            def link_then_remove_staging(source: Path, destination: Path) -> None:
                original_link(source, destination)
                source.unlink()

            def reject_only_final(path: Path) -> dict:
                result = original_validator(path)
                if path == target:
                    result = {**result, "passed": False}
                return result

            with (
                patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False),
                patch.object(
                    integration.os, "link", side_effect=link_then_remove_staging
                ),
                patch.object(
                    integration,
                    "_validate_non_silent_wav",
                    side_effect=reject_only_final,
                ),
            ):
                self.assertTrue(manager.prewarm("kira:staging-disappears")["warmed"])
                result = manager.synthesize(
                    text="Invalid final audio must be removed.",
                    target=target,
                    pcm_output_gain_db=0.0,
                    proximity_cut_hz=0.0,
                    proximity_cut_mix=0.0,
                )

            self.assertTrue(target.exists())

        self.assertFalse(result["generated"], result)
        self.assertEqual(
            result["reason"], "persistent_blackwell_v2_final_wav_validation_failed"
        )
        self.assertFalse(result["target_cleanup_proven"])
        self.assertFalse(result["fallback_allowed"])
        self.assertTrue(result["route_blocked"])

    def test_owner_bound_release_cannot_close_a_newer_session(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_FakeV2Client
        )
        with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
            self.assertTrue(manager.prewarm("kira:new-owner")["warmed"])
            result = manager.close_if_owner(
                "kira:old-owner", "stale_session_release"
            )
            status = manager.status()
            manager.close("owner_bound_test_cleanup")

        self.assertFalse(result["owner_matched"], result)
        self.assertFalse(result["release_attempted"])
        self.assertTrue(status["owned_worker_running"])
        self.assertEqual(status["session_owner"], "kira:new-owner")

    def test_release_truth_requires_exact_owned_worker_exit(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_UnclosableFake
        )
        with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
            self.assertTrue(manager.prewarm("kira:unclosable")["warmed"])
            result = manager.close("unclosable_release_test")

        self.assertTrue(result["release_attempted"], result)
        self.assertTrue(result["model_was_loaded"])
        self.assertFalse(result["cleanup"]["owned_worker_closed"])
        self.assertFalse(result["released"])
        self.assertTrue(result["cleanup_debt"])
        self.assertEqual(result["session_owner"], "kira:unclosable")

    def test_cleanup_debt_blocks_new_session_and_retains_exact_process_handle(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_UnclosableFake
        )
        with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
            self.assertTrue(manager.prewarm("kira:old-owner")["warmed"])
            first_client = manager._client
            failed_release = manager.close("create_cleanup_debt")
            new_session = manager.begin_session("kira:new-owner")
            status = manager.status()

        self.assertFalse(failed_release["released"], failed_release)
        self.assertFalse(new_session["begun"], new_session)
        self.assertEqual(
            new_session["reason"],
            "persistent_blackwell_v2_cleanup_debt_not_closed",
        )
        self.assertIs(manager._client, first_client)
        self.assertEqual(status["session_owner"], "kira:old-owner")
        self.assertTrue(status["cleanup_debt"])
        self.assertEqual(len(_UnclosableFake.instances), 1)

    def test_status_stops_claiming_loaded_after_sealed_idle_unload_bound(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_FakeV2Client
        )
        with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
            self.assertTrue(manager.prewarm("kira:idle-status")["warmed"])
            manager._last_load_verified_monotonic = 1.0
            with patch.object(
                integration.time,
                "monotonic",
                return_value=integration.WORKER_IDLE_UNLOAD_SECONDS + 2.0,
            ):
                status = manager.status()
            manager.close("idle_status_test_cleanup")

        self.assertFalse(status["model_loaded"])
        self.assertTrue(status["host_last_known_model_loaded"])
        self.assertEqual(status["model_loaded_verification"], "not_currently_proven")

    def test_close_after_worker_idle_unload_does_not_claim_model_release(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_IdleUnloadFake
        )
        with patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False):
            self.assertTrue(manager.prewarm("kira:already-idle-unloaded")["warmed"])
            client = manager._client
            client.model_is_loaded = False
            result = manager.close("already_idle_unloaded")

        self.assertTrue(result["cleanup"]["owned_worker_closed"])
        self.assertTrue(result["cleanup"]["host_last_known_model_loaded"])
        self.assertFalse(result["cleanup"]["model_was_loaded"])
        self.assertFalse(result["model_was_loaded"])
        self.assertFalse(result["released"])

    def test_path_replacement_after_link_is_preserved_and_blocks_fallback(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=_FakeV2Client
        )
        output_root = integration.GENERATED_AUDIO_ROOT / "v2_integration_tests"
        output_root.mkdir(parents=True, exist_ok=True)
        original_validator = integration._validate_non_silent_wav

        with tempfile.TemporaryDirectory(dir=output_root) as temp_dir:
            target = Path(temp_dir) / "replacement_after_link.wav"
            replaced = False

            def replace_at_final_validation(path: Path) -> dict:
                nonlocal replaced
                result = original_validator(path)
                if path == target and not replaced:
                    path.unlink()
                    path.write_bytes(b"replacement-owned-by-another-route")
                    replaced = True
                    return {**result, "passed": False}
                return result

            with (
                patch.dict(os.environ, {integration.FEATURE_FLAG: "1"}, clear=False),
                patch.object(
                    integration,
                    "_validate_non_silent_wav",
                    side_effect=replace_at_final_validation,
                ),
            ):
                self.assertTrue(manager.prewarm("kira:path-replacement")["warmed"])
                result = manager.synthesize(
                    text="Preserve a path replacement that is not ours.",
                    target=target,
                    pcm_output_gain_db=0.0,
                    proximity_cut_hz=0.0,
                    proximity_cut_mix=0.0,
                )

            self.assertEqual(
                target.read_bytes(), b"replacement-owned-by-another-route"
            )

        self.assertFalse(result["generated"], result)
        self.assertFalse(result["target_cleanup_proven"])
        self.assertFalse(result["fallback_allowed"])
        self.assertTrue(result["route_blocked"])


if __name__ == "__main__":
    unittest.main()
