from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "Core"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

import conversation_loop  # noqa: E402
import persistent_blackwell_voice_integration as persistent  # noqa: E402
import voice_output  # noqa: E402
from tools import kira_world_shell_server as shell  # noqa: E402


class _FakeProcess:
    pid = 424242

    def __init__(self) -> None:
        self.running = True

    def poll(self):
        return None if self.running else 0


class _FakePersistentClient:
    instances: list["_FakePersistentClient"] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = dict(kwargs)
        self.process = _FakeProcess()
        self.start_calls = 0
        self.load_calls = 0
        self.synthesis_calls = 0
        self.unload_calls = 0
        self.close_calls = 0
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
        return {
            "ready": True,
            "model_reused": self.load_calls > 1,
            # Match the sealed worker's real response contract: load state is
            # reported inside lifecycle, not as a top-level field.
            "lifecycle": {
                "model_loaded": True,
                "model_load_count": 1,
                "reference_conditioning_count": 1,
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
            writer.writeframes(b"\x01\x00" * 2400)
        text_hash = persistent.hashlib.sha256(text.encode("utf-8")).hexdigest()
        return {
            "generated": True,
            "engine": "chatterbox_tts",
            "device": "cuda",
            "channel": "public_spoken_only",
            "requested_text_bound": True,
            "text_sha256": text_hash,
            "profile_sha256": persistent.APPROVED_PROFILE_SHA256,
            "reference_sha256": persistent.APPROVED_REFERENCE_SHA256,
            "playback": False,
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "gpu_proof": {
                "actual_gpu_execution": True,
                "actual_gpu_allocation": True,
                "persistent_model_allocation_present": True,
                "model_and_core_components_cuda": True,
                "cuda_synchronize_before_generation_succeeded": True,
                "cuda_synchronize_after_generation_succeeded": True,
                "generation_peak_exceeded_baseline": True,
                "generation_peak_delta_bytes": 64 * 1024 * 1024,
                "no_rejected_runtime_warnings": True,
                "qwen_absence_proven_for_accepted_generation": True,
                "official_host_return_contract_satisfied": True,
                "accepted_output_tensors_host_cpu": True,
                "accepted_output_tensors_cuda": False,
            },
            "chunk_checks": [
                {
                    "chunk_index": 0,
                    "accepted_attempt": 1,
                    "attempts": [
                        {
                            "attempt": 1,
                            "passed": True,
                            "output_tensor_device_type": "cpu",
                            "output_tensor_was_cuda": False,
                            "output_tensor_returned_to_host": True,
                            "official_host_return_contract_satisfied": True,
                            "rejected_warning_matches": [],
                            "qwen_residency": self._qwen_absent(),
                        }
                    ],
                }
            ],
            "parent_qwen_residency_before_synthesis": self._qwen_absent(),
            "audio_path": str(target),
        }

    def unload(self) -> dict:
        self.unload_calls += 1
        return {"unloaded": True}

    def close(self) -> dict:
        self.close_calls += 1
        process = self.process
        process.running = False
        self.process = None
        return {
            "owned_process_exit_code": 0,
            "owned_process_forced_termination": False,
        }


class _FakePersistentClientMissingPeak(_FakePersistentClient):
    def synthesize(self, *, text: str, output_relative: str, **kwargs) -> dict:
        response = super().synthesize(text=text, output_relative=output_relative, **kwargs)
        response["gpu_proof"]["generation_peak_exceeded_baseline"] = False
        response["gpu_proof"]["generation_peak_delta_bytes"] = 0
        return response


class PersistentVoiceIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        _FakePersistentClient.instances.clear()

    def test_default_off_does_not_construct_a_worker(self) -> None:
        manager = persistent.PersistentBlackwellVoiceIntegration(
            client_factory=_FakePersistentClient
        )
        with patch.dict(os.environ, {persistent.FEATURE_FLAG: "0"}, clear=False):
            result = manager.begin_session("kira:1")
            synth = manager.synthesize(
                text="This route must remain inert.",
                target=ROOT / "Voice" / "generated" / "never_created.wav",
                pcm_output_gain_db=0.0,
                proximity_cut_hz=0.0,
                proximity_cut_mix=0.0,
            )
        self.assertFalse(result["begun"])
        self.assertFalse(synth["generated"])
        self.assertEqual(_FakePersistentClient.instances, [])

    def test_one_session_owns_reuses_and_closes_only_its_fake_worker(self) -> None:
        manager = persistent.PersistentBlackwellVoiceIntegration(
            client_factory=_FakePersistentClient
        )
        output_root = ROOT / "RecoverySprint" / "runtime_cache" / "latency_integration_tests"
        output_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output_root) as temp_dir:
            target = Path(temp_dir) / "result.wav"
            with patch.dict(os.environ, {persistent.FEATURE_FLAG: "1"}, clear=False):
                self.assertTrue(manager.begin_session("kira:7")["begun"])
                first_warm = manager.prewarm("kira:7")
                second_warm = manager.prewarm("kira:7")
                result = manager.synthesize(
                    text="A bounded public spoken sentence.",
                    target=target,
                    pcm_output_gain_db=0.0,
                    proximity_cut_hz=0.0,
                    proximity_cut_mix=0.0,
                )
                status = manager.status()
                closed = manager.close("unit_test")

        self.assertTrue(first_warm["warmed"], first_warm)
        self.assertTrue(second_warm["warmed"], second_warm)
        self.assertTrue(result["generated"], result)
        self.assertEqual(result["approved_voice_path_used"], "blackwell_gpu")
        self.assertEqual(result["sidecar_lifecycle"], "session_owned_persistent_candidate")
        self.assertTrue(result["staging_promoted_to_caller_target"])
        self.assertTrue(status["owned_worker_running"])
        self.assertTrue(closed["cleanup"]["owned_worker_closed"])
        self.assertEqual(len(_FakePersistentClient.instances), 1)
        client = _FakePersistentClient.instances[0]
        self.assertEqual(client.start_calls, 1)
        self.assertEqual(client.load_calls, 2)
        self.assertEqual(client.synthesis_calls, 1)
        self.assertEqual(client.unload_calls, 1)
        self.assertEqual(client.close_calls, 1)

    def test_integration_fails_closed_when_generation_peak_does_not_exceed_baseline(self) -> None:
        manager = persistent.PersistentBlackwellVoiceIntegration(
            client_factory=_FakePersistentClientMissingPeak
        )
        output_root = ROOT / "RecoverySprint" / "runtime_cache" / "latency_integration_tests"
        output_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output_root) as temp_dir:
            target = Path(temp_dir) / "rejected.wav"
            with patch.dict(os.environ, {persistent.FEATURE_FLAG: "1"}, clear=False):
                self.assertTrue(manager.begin_session("kira:peak-gate")["begun"])
                self.assertTrue(manager.prewarm("kira:peak-gate")["warmed"])
                result = manager.synthesize(
                    text="A bounded public spoken sentence.",
                    target=target,
                    pcm_output_gain_db=0.0,
                    proximity_cut_hz=0.0,
                    proximity_cut_mix=0.0,
                )
        self.assertFalse(result["generated"], result)
        self.assertIn("generation_gpu_peak_did_not_exceed_baseline", result["issues"])
        self.assertFalse(target.exists())

    def test_active_persistent_failure_skips_one_shot_gpu_and_uses_sealed_cpu(self) -> None:
        cfg = voice_output.VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio=voice_output.KIRA_APPROVED_REFERENCE_RELATIVE,
        )
        routing = {
            "valid": True,
            "routing_id": "unit-routing",
            "routing_config_sha256": "a" * 64,
            "routes": [
                {"route_id": "blackwell_gpu", "role": "preferred", "valid": True},
                {
                    "route_id": "sealed_cpu",
                    "role": "automatic_fallback_only",
                    "valid": True,
                },
            ],
        }

        def fake_synthesis(_text, _target, _cfg, route):
            self.assertEqual(route["route_id"], "sealed_cpu")
            return {
                "generated": True,
                "reason": "ok",
                "route_id": "sealed_cpu",
                "engine": "chatterbox_tts",
                "device": "cpu",
                "playback": False,
                "generic_voice_used": False,
            }

        with (
            patch.object(voice_output, "persistent_blackwell_voice_feature_enabled", return_value=True),
            patch.object(
                voice_output,
                "synthesize_with_persistent_blackwell_voice",
                return_value={
                    "generated": False,
                    "reason": "bounded_fake_failure",
                    "persistent_route_eligible": True,
                    "owned_worker_cleanup": {"owned_worker_closed": True},
                    "playback": False,
                },
            ),
            patch.object(voice_output, "_load_approved_voice_routing_config", return_value=routing),
            patch.object(
                voice_output,
                "_qwen_residency_evidence",
                return_value={"query_succeeded": True, "qwen_absent_proven": True},
            ),
            patch.object(
                voice_output,
                "_run_approved_sidecar_self_check",
                return_value={"ready": True, "reason": "ready"},
            ),
            patch.object(
                voice_output,
                "_synthesize_with_approved_sidecar",
                side_effect=fake_synthesis,
            ) as one_shot,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Exact public text.",
                ROOT / "Voice" / "generated" / "fake_target.wav",
                cfg,
            )
        self.assertTrue(result["generated"], result)
        self.assertEqual(result["approved_voice_path_used"], "sealed_cpu")
        self.assertTrue(result["approved_voice_routing"]["automatic_cpu_fallback_used"])
        self.assertEqual(one_shot.call_count, 1)
        self.assertEqual(one_shot.call_args.args[3]["route_id"], "sealed_cpu")


class KiraReplyRepairBudgetTests(unittest.TestCase):
    def test_repeat_and_settled_repairs_share_one_model_call(self) -> None:
        class FakeLoop:
            conversation_history = [{"role": "assistant", "content": "old"}]

            def __init__(self) -> None:
                self.calls = 0

            def build_context(self, prompt: str) -> dict:
                return {"user_message": prompt}

            def call_model(self, _context: dict) -> str:
                self.calls += 1
                return "Still repeated."

        loop = FakeLoop()
        budget = shell._KiraReplyRepairBudget(1)
        loop._shell_reply_repair_budget = budget
        transaction = {
            "answered": {"coffee_milk": True},
            "preferences": {"coffee_milk": "yes"},
        }
        with (
            patch.object(shell, "_kira_reply_repeats_prior_opening", return_value=(True, 0.99)),
            patch.object(shell, "_similar_prior_kira_replies", return_value=["Old reply"]),
            patch.object(shell, "_clean_kira_world_reply", side_effect=lambda _u, value: value),
            patch.object(shell, "_kira_social_tangent", return_value=False),
            patch.object(shell, "_kira_recent_dialogue_transaction", return_value=transaction),
            patch.object(shell, "_kira_answer_reopens_settled_transaction", return_value=(True, ["coffee_milk"], 0.9)),
            patch.object(shell, "append_jsonl"),
        ):
            repeated = shell._repair_kira_cross_session_repeat(
                loop,
                "How are you?",
                "Old reply",
            )
            settled = shell._repair_kira_answered_question_loop(
                loop,
                "Yes",
                "Would you like milk?",
                {},
            )
        self.assertEqual(loop.calls, 1)
        self.assertIn("same answer", repeated)
        self.assertIn("already answered", settled)
        self.assertEqual(budget.evidence()["extra_model_calls_consumed"], 1)
        self.assertEqual(
            budget.evidence()["denied_to"],
            ["repair_kira_answered_question_loop"],
        )

    def test_natural_nonrepeated_reply_consumes_no_budget(self) -> None:
        loop = SimpleNamespace(_shell_reply_repair_budget=shell._KiraReplyRepairBudget(1))
        with patch.object(
            shell,
            "_kira_reply_repeats_prior_opening",
            return_value=(False, 0.1),
        ):
            result = shell._repair_kira_cross_session_repeat(
                loop,
                "How are you?",
                "I'm feeling curious and glad to talk with you.",
            )
        self.assertEqual(result, "I'm feeling curious and glad to talk with you.")
        self.assertEqual(
            loop._shell_reply_repair_budget.evidence()["extra_model_calls_consumed"],
            0,
        )


class LlamaLatencyCandidateTests(unittest.TestCase):
    def test_flags_default_to_unload_and_nonstreaming(self) -> None:
        with (
            patch.object(conversation_loop, "MODEL_NAME", "llama3.1:8b"),
            patch.object(conversation_loop, "TEXT_VOICE_CHAT_ACTIVE", True),
            patch.dict(
                os.environ,
                {
                    conversation_loop.LLAMA_KEEP_ALIVE_CANDIDATE_FLAG: "0",
                    conversation_loop.LLAMA_BUFFERED_STREAM_CANDIDATE_FLAG: "0",
                },
                clear=False,
            ),
        ):
            self.assertEqual(conversation_loop._bounded_keep_alive_candidate_value(), 0)
            self.assertFalse(conversation_loop._buffered_stream_timing_candidate_enabled())

    def test_buffered_stream_records_first_content_without_exposing_partial_text(self) -> None:
        calls: list[tuple[dict, dict]] = []

        class StreamResponse:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

            def iter_lines(self):
                yield json.dumps({"message": {"content": "Hello "}, "done": False}).encode()
                yield json.dumps(
                    {
                        "message": {"content": "Robert."},
                        "done": True,
                        "done_reason": "stop",
                        "load_duration": 123,
                    }
                ).encode()

        def fake_post(_url: str, **kwargs):
            calls.append((dict(kwargs["json"]), dict(kwargs)))
            return StreamResponse()

        instance = object.__new__(conversation_loop.ConversationLoop)
        instance.profile = SimpleNamespace(name="Kira")
        instance.conversation_history = []
        instance.autobiographical_context = ""
        instance._active_model_call_audit = []
        instance._build_ollama_runtime_prompt = lambda: "SYSTEM"
        fake_requests = SimpleNamespace(
            post=fake_post,
            exceptions=SimpleNamespace(ConnectionError=ConnectionError),
        )
        with (
            patch.object(conversation_loop, "MODEL_NAME", "llama3.1:8b"),
            patch.object(conversation_loop, "TEXT_VOICE_CHAT_ACTIVE", True),
            patch.dict(
                os.environ,
                {
                    conversation_loop.LLAMA_KEEP_ALIVE_CANDIDATE_FLAG: "1",
                    conversation_loop.LLAMA_KEEP_ALIVE_CANDIDATE_DURATION: "2m",
                    conversation_loop.LLAMA_BUFFERED_STREAM_CANDIDATE_FLAG: "1",
                },
                clear=False,
            ),
            patch.dict(sys.modules, {"requests": fake_requests}),
        ):
            result = conversation_loop.ConversationLoop._call_ollama(
                instance,
                {"user_message": "Hi", "memory_context": ""},
            )
        self.assertEqual(result, "Hello Robert.")
        self.assertEqual(len(calls), 1)
        payload, request_kwargs = calls[0]
        self.assertTrue(payload["stream"])
        self.assertEqual(payload["keep_alive"], "2m")
        self.assertTrue(request_kwargs["stream"])
        audit = instance._active_model_call_audit[0]
        self.assertTrue(audit["stream"])
        self.assertTrue(audit["first_token_available"])
        self.assertEqual(audit["stream_content_chunk_count"], 2)
        self.assertTrue(audit["buffered_until_complete"])
        self.assertFalse(audit["unvalidated_stream_content_displayed"])
        self.assertEqual(audit["raw_reply"], "Hello Robert.")


if __name__ == "__main__":
    unittest.main()
