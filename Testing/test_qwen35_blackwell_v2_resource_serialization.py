"""Mocks-only tests for exact Qwen/persistent-Blackwell-v2 serialization.

No test in this module starts Ollama, a voice worker, a GPU runtime, an audio
device, Blender, a camera, or a microphone.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "Core"
for entry in (ROOT, CORE):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from Core import conversation_loop  # noqa: E402
from Core import persistent_blackwell_voice_integration_v2 as integration  # noqa: E402
from Core import voice_output  # noqa: E402
from tools import kira_world_shell_server as shell  # noqa: E402


def _qwen_absent() -> dict:
    return {
        "query_succeeded": True,
        "qwen_absent_proven": True,
        "qwen_records": [],
        "endpoint": voice_output.KIRA_QWEN_PS_ENDPOINT,
        "model_state_changed": False,
    }


class _OwnedProcess:
    pid = 424242

    def __init__(self) -> None:
        self.running = True
        self.returncode = None
        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.terminate_calls = 0
        self.kill_calls = 0

    def poll(self):
        return None if self.running else self.returncode

    def terminate(self) -> None:
        self.terminate_calls += 1
        self.running = False
        self.returncode = -15

    def kill(self) -> None:
        self.kill_calls += 1
        self.running = False
        self.returncode = -9

    def wait(self, timeout=None):
        del timeout
        return self.returncode


class _StrictSuspendClient:
    def __init__(self) -> None:
        self.process = _OwnedProcess()
        self.unload_calls = 0
        self.loaded = True

    def unload(self) -> dict:
        self.unload_calls += 1
        was_loaded = self.loaded
        self.loaded = False
        return {
            "unloaded": True,
            "model_was_loaded": was_loaded,
            "operation_seconds": 0.01,
            "lifecycle": {
                "model_loaded": False,
                "last_unload": {
                    "was_loaded": was_loaded,
                    "operation_seconds": 0.01,
                },
            },
        }


class _MalformedSuspendClient(_StrictSuspendClient):
    def unload(self) -> dict:
        self.unload_calls += 1
        return {
            "unloaded": True,
            "model_was_loaded": True,
            "lifecycle": {"model_loaded": True},
        }


class _RecordingLock:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def acquire(self, timeout=None) -> bool:
        self.events.append("resource_lock_acquire")
        self.timeout = timeout
        return True

    def release(self) -> None:
        self.events.append("resource_lock_release")


def _loop_instance():
    instance = object.__new__(conversation_loop.ConversationLoop)
    instance.profile = SimpleNamespace(name="Kira")
    instance.conversation_history = []
    instance.autobiographical_context = ""
    instance._active_model_call_audit = []
    instance._build_ollama_runtime_prompt = lambda: "SYSTEM"
    return instance


class QwenBlackwellV2ResourceSerializationTests(unittest.TestCase):
    def test_owner_bound_suspend_preserves_exact_owner_worker_and_generation(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=lambda **_kwargs: None
        )
        client = _StrictSuspendClient()
        manager._owner = "kira:7"
        manager._generation = 7
        manager._client = client
        manager._loaded = True
        manager._last_load_verified_monotonic = time.monotonic()

        result = manager.suspend_if_owner(
            "kira:7", expected_generation=7, timeout_seconds=0.2
        )

        self.assertTrue(result["suspended"], result)
        self.assertTrue(result["ready_for_text_generation"])
        self.assertTrue(result["model_release_proven"])
        self.assertTrue(result["session_owner_preserved"])
        self.assertTrue(result["owned_worker_preserved"])
        self.assertEqual(client.unload_calls, 1)
        self.assertTrue(client.process.running)
        self.assertIs(manager._client, client)
        self.assertEqual(manager._owner, "kira:7")
        self.assertEqual(manager._generation, 7)
        self.assertFalse(manager._loaded)
        self.assertFalse(manager._operation_in_flight)

    def test_stale_owner_suspend_is_total_noop(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=lambda **_kwargs: None
        )
        client = _StrictSuspendClient()
        manager._owner = "kira:new"
        manager._client = client
        manager._loaded = True

        result = manager.suspend_if_owner(
            "kira:old", expected_generation=0, timeout_seconds=0.05
        )

        self.assertFalse(result["owner_matched"])
        self.assertFalse(result["ready_for_text_generation"])
        self.assertEqual(client.unload_calls, 0)
        self.assertIs(manager._client, client)
        self.assertTrue(client.process.running)
        self.assertEqual(manager._owner, "kira:new")

    def test_malformed_unload_never_claims_suspend_and_closes_only_exact_child(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=lambda **_kwargs: None
        )
        client = _MalformedSuspendClient()
        manager._owner = "kira:8"
        manager._client = client
        manager._loaded = True

        result = manager.suspend_if_owner(
            "kira:8", expected_generation=0, timeout_seconds=0.2
        )

        self.assertFalse(result["suspended"], result)
        self.assertTrue(result["model_release_proven"])
        self.assertTrue(result["ready_for_text_generation"])
        self.assertTrue(result["exact_owned_worker_closed_for_recovery"])
        self.assertIn("worker_model_absence_not_proven", result["suspend_contract_issues"])
        self.assertEqual(client.process.terminate_calls, 1)
        self.assertIsNone(manager._client)
        self.assertEqual(manager._owner, "kira:8")
        self.assertFalse(result["arbitrary_process_termination_performed"])

    def test_operation_lock_timeout_aborts_revalidated_exact_client_without_marker(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=lambda **_kwargs: None
        )
        client = _StrictSuspendClient()
        manager._owner = "kira:9"
        manager._client = client
        manager._loaded = True
        self.assertFalse(manager._operation_in_flight)
        manager._operation_lock.acquire()
        try:
            started = time.perf_counter()
            result = manager.suspend_if_owner(
                "kira:9", expected_generation=0, timeout_seconds=0.05
            )
            elapsed = time.perf_counter() - started
        finally:
            manager._operation_lock.release()

        self.assertLess(elapsed, 0.5)
        self.assertFalse(result["operation_lock_acquired"])
        self.assertFalse(result["suspended"])
        self.assertTrue(result["model_release_proven"])
        self.assertTrue(result["ready_for_text_generation"])
        self.assertTrue(result["session_owner_preserved"])
        self.assertEqual(client.process.terminate_calls, 1)
        self.assertEqual(manager._owner, "kira:9")
        self.assertIsNone(manager._client)

    def test_owner_generation_change_while_waiting_never_touches_new_session(self) -> None:
        manager = integration.PersistentBlackwellVoiceIntegrationV2(
            client_factory=lambda **_kwargs: None
        )
        client = _StrictSuspendClient()
        manager._owner = "kira:12"
        manager._generation = 12
        manager._client = client
        manager._loaded = True

        class GenerationChangingLock:
            def acquire(self, timeout=None) -> bool:
                del timeout
                with manager._lock:
                    manager._generation = 13
                return False

            def release(self) -> None:
                raise AssertionError("unacquired lock must not be released")

        manager._operation_lock = GenerationChangingLock()
        result = manager.suspend_if_owner(
            "kira:12", expected_generation=12, timeout_seconds=0.05
        )

        self.assertFalse(result["ready_for_text_generation"])
        self.assertFalse(result["model_release_proven"])
        self.assertTrue(result["owner_matched"])
        self.assertFalse(result["generation_matched"])
        self.assertFalse(result["session_generation_preserved"])
        self.assertEqual(client.process.terminate_calls, 0)
        self.assertIs(manager._client, client)
        self.assertTrue(client.process.running)
        self.assertEqual(manager._generation, 13)

    def test_malformed_qwen_ps_evidence_cannot_prove_absence(self) -> None:
        malformed = {
            "query_succeeded": True,
            "qwen_absent_proven": True,
            "model_state_changed": False,
        }
        with patch.object(
            voice_output, "_qwen_residency_evidence", return_value=malformed
        ):
            result = voice_output.wait_for_exact_qwen_absence(timeout_seconds=0.0)
        self.assertFalse(result["qwen_absent_proven"])
        self.assertFalse(result["attempts"][0]["evidence_shape_valid"])

    def test_raw_qwen_ps_malformed_model_records_fail_closed(self) -> None:
        class Response:
            def __init__(self, payload: dict) -> None:
                self.raw = json.dumps(payload).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *_args) -> None:
                return None

            def read(self, _limit: int) -> bytes:
                return self.raw

        class Opener:
            def __init__(self, payload: dict) -> None:
                self.payload = payload

            def open(self, *_args, **_kwargs):
                return Response(self.payload)

        malformed_payloads = (
            {"models": [1]},
            {"models": [{}]},
            {
                "models": [
                    {"name": 7, "model": "other:1b", "digest": "a" * 64}
                ]
            },
            {
                "models": [
                    {"name": "other:1b", "model": "other:1b", "digest": "bad"}
                ]
            },
        )
        for payload in malformed_payloads:
            with self.subTest(payload=payload), patch.object(
                voice_output.urllib_request,
                "build_opener",
                return_value=Opener(payload),
            ):
                result = voice_output._qwen_residency_evidence(timeout_seconds=0.2)
            self.assertFalse(result["query_succeeded"], result)
            self.assertFalse(result["qwen_absent_proven"], result)
            self.assertEqual(
                result["reason"], "qwen_residency_query_failed_gpu_blocked"
            )

    def test_qwen_generation_orders_suspend_one_post_absence_then_unlock(self) -> None:
        events: list[str] = []
        payloads: list[dict] = []

        class StreamResponse:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

            def iter_lines(self, chunk_size=1):
                self.chunk_size = chunk_size
                yield json.dumps(
                    {
                        "model": "qwen3.5:9b",
                        "message": {"content": "Exact reply."},
                        "done": True,
                    }
                ).encode()

        def post(_url: str, **kwargs):
            events.append("qwen_post")
            payloads.append(dict(kwargs["json"]))
            return StreamResponse()

        def suspend():
            events.append("voice_suspend")
            return {
                "ready_for_text_generation": True,
                "voice_model_absence_proven": True,
                "session_owner_preserved": True,
                "owned_worker_preserved": True,
            }

        def absence():
            events.append("qwen_absence")
            return {"qwen_absent_proven": True, **_qwen_absent()}

        fake_requests = SimpleNamespace(
            post=post,
            exceptions=SimpleNamespace(ConnectionError=ConnectionError),
        )
        lock = _RecordingLock(events)
        instance = _loop_instance()
        with (
            patch.object(conversation_loop, "MODEL_NAME", "qwen3.5:9b"),
            patch.object(conversation_loop, "TEXT_VOICE_CHAT_ACTIVE", True),
            patch.object(conversation_loop, "WORLD_SHELL_ACTIVE", False),
            patch.dict(
                os.environ,
                {
                    "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2": "1",
                },
                clear=False,
            ),
            patch.object(
                voice_output,
                "exact_qwen_persistent_v2_resource_serialization_required",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "exact_qwen_blackwell_v2_resource_lock",
                return_value=lock,
            ),
            patch.object(
                voice_output,
                "suspend_persistent_blackwell_voice_for_exact_qwen",
                side_effect=suspend,
            ),
            patch.object(
                voice_output,
                "wait_for_exact_qwen_absence",
                side_effect=absence,
            ),
            patch.dict(sys.modules, {"requests": fake_requests}),
        ):
            reply = conversation_loop.ConversationLoop._call_ollama(
                instance, {"user_message": "Hi", "memory_context": ""}
            )

        self.assertEqual(reply, "Exact reply.")
        self.assertEqual(
            events,
            [
                "resource_lock_acquire",
                "voice_suspend",
                "qwen_post",
                "qwen_absence",
                "resource_lock_release",
            ],
        )
        self.assertEqual(len(payloads), 1)
        self.assertIs(payloads[0]["think"], False)
        self.assertEqual(payloads[0]["keep_alive"], 0)
        audit = instance._active_model_call_audit[0]
        self.assertEqual(audit["generation_request_count"], 1)
        self.assertTrue(audit["voice_model_absence_before_generation_proven"])
        self.assertTrue(audit["qwen_absence_after_generation_proven"])

    def test_qwen_resource_lock_timeout_blocks_generation_and_voice(self) -> None:
        class DeniedLock:
            def acquire(self, timeout=None) -> bool:
                self.timeout = timeout
                return False

            def release(self) -> None:
                raise AssertionError("unacquired lock must not be released")

        fake_requests = SimpleNamespace(
            post=lambda *_args, **_kwargs: self.fail("Qwen request must stay blocked"),
            exceptions=SimpleNamespace(ConnectionError=ConnectionError),
        )
        instance = _loop_instance()
        with (
            patch.object(conversation_loop, "MODEL_NAME", "qwen3.5:9b"),
            patch.object(conversation_loop, "TEXT_VOICE_CHAT_ACTIVE", True),
            patch.object(conversation_loop, "WORLD_SHELL_ACTIVE", False),
            patch.dict(
                os.environ,
                {"KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2": "1"},
                clear=False,
            ),
            patch.object(
                voice_output,
                "exact_qwen_persistent_v2_resource_serialization_required",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "exact_qwen_blackwell_v2_resource_lock",
                return_value=DeniedLock(),
            ),
            patch.object(
                voice_output, "suspend_persistent_blackwell_voice_for_exact_qwen"
            ) as suspend,
            patch.dict(sys.modules, {"requests": fake_requests}),
        ):
            reply = conversation_loop.ConversationLoop._call_ollama(
                instance, {"user_message": "Hi", "memory_context": ""}
            )

        self.assertEqual(reply, "")
        suspend.assert_not_called()
        audit = instance._active_model_call_audit[0]
        self.assertEqual(audit["generation_request_count"], 0)
        self.assertEqual(audit["outcome"], "exact_qwen_voice_resource_lock_timeout")
        self.assertFalse(audit["voice_generation_allowed"])

    def test_empty_qwen_grounded_draft_never_becomes_deterministic_speech(self) -> None:
        instance = _loop_instance()
        instance._call_ollama = lambda _context: ""
        with (
            patch.object(conversation_loop, "MODEL_BACKEND", "ollama"),
            patch.object(
                conversation_loop,
                "_single_generation_per_turn_required",
                return_value=True,
            ),
        ):
            reply = conversation_loop.ConversationLoop._generate_from_grounded_draft(
                instance,
                {"user_message": "How are you?"},
                "Deterministic private grounding draft.",
                allow_fallback_to_draft=False,
            )
        self.assertEqual(reply, "")
        self.assertNotIn("Deterministic", reply)

    def test_http_500_body_is_bounded_audited_and_never_returned_for_speech(self) -> None:
        body = b'{"error":"voice plus qwen allocation failed"}'
        events: list[str] = []

        class HttpFailure(RuntimeError):
            pass

        class ErrorResponse:
            status_code = 500

            def iter_content(self, chunk_size=4096):
                del chunk_size
                yield body

            def raise_for_status(self):
                raise HttpFailure("500 Server Error")

        def post(_url: str, **_kwargs):
            events.append("qwen_post")
            return ErrorResponse()

        fake_requests = SimpleNamespace(
            post=post,
            exceptions=SimpleNamespace(ConnectionError=ConnectionError),
        )
        lock = _RecordingLock(events)
        instance = _loop_instance()
        with (
            patch.object(conversation_loop, "MODEL_NAME", "qwen3.5:9b"),
            patch.object(conversation_loop, "TEXT_VOICE_CHAT_ACTIVE", True),
            patch.object(conversation_loop, "WORLD_SHELL_ACTIVE", False),
            patch.dict(
                os.environ,
                {"KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2": "1"},
                clear=False,
            ),
            patch.object(
                voice_output,
                "exact_qwen_persistent_v2_resource_serialization_required",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "exact_qwen_blackwell_v2_resource_lock",
                return_value=lock,
            ),
            patch.object(
                voice_output,
                "suspend_persistent_blackwell_voice_for_exact_qwen",
                return_value={
                    "ready_for_text_generation": True,
                    "voice_model_absence_proven": True,
                },
            ),
            patch.object(
                voice_output,
                "wait_for_exact_qwen_absence",
                return_value=_qwen_absent(),
            ),
            patch.dict(sys.modules, {"requests": fake_requests}),
        ):
            reply = conversation_loop.ConversationLoop._call_ollama(
                instance, {"user_message": "Hi", "memory_context": ""}
            )

        self.assertEqual(reply, "")
        self.assertNotIn(body.decode(), reply)
        audit = instance._active_model_call_audit[0]
        self.assertEqual(audit["generation_request_count"], 1)
        self.assertEqual(audit["http_error"]["status_code"], 500)
        self.assertEqual(
            audit["http_error"]["body_sha256"], hashlib.sha256(body).hexdigest()
        )
        self.assertIn("allocation failed", audit["http_error"]["body_excerpt"])
        self.assertFalse(audit["http_error"]["public_speech_allowed"])
        self.assertEqual(audit["raw_reply"], "")

    def test_unrelated_model_route_fails_before_generation_or_voice_serialization(self) -> None:
        calls: list[dict] = []

        class Response:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "model": "unrelated-local-model:1b",
                    "message": {"content": "Unrelated route reply."},
                }

        def post(_url: str, **kwargs):
            calls.append(dict(kwargs["json"]))
            return Response()

        fake_requests = SimpleNamespace(
            post=post,
            exceptions=SimpleNamespace(ConnectionError=ConnectionError),
        )
        instance = _loop_instance()
        with (
            patch.object(conversation_loop, "MODEL_NAME", "unrelated-local-model:1b"),
            patch.object(conversation_loop, "TEXT_VOICE_CHAT_ACTIVE", True),
            patch.object(conversation_loop, "WORLD_SHELL_ACTIVE", False),
            patch.dict(
                os.environ,
                {"KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2": "1"},
                clear=False,
            ),
            patch.object(
                voice_output,
                "suspend_persistent_blackwell_voice_for_exact_qwen",
            ) as suspend,
            patch.dict(sys.modules, {"requests": fake_requests}),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "current person routes require exact qwen3.5:9b",
            ):
                conversation_loop.ConversationLoop._call_ollama(
                    instance, {"user_message": "Hi", "memory_context": ""}
                )

        self.assertEqual(calls, [])
        suspend.assert_not_called()
        self.assertEqual(instance._active_model_call_audit, [])

    def test_activation_prewarm_is_disabled_but_lazy_v2_synthesis_remains(self) -> None:
        cfg = voice_output.VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio=voice_output.KIRA_APPROVED_REFERENCE_RELATIVE,
            play_audio=False,
        )
        with (
            patch.object(
                voice_output,
                "exact_qwen_persistent_v2_resource_serialization_required",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "persistent_blackwell_voice_status",
                return_value={
                    "session_owner": "kira:10",
                    "owned_worker_running": False,
                    "model_loaded": False,
                },
            ),
            patch.object(
                voice_output, "prewarm_persistent_blackwell_voice"
            ) as prewarm,
        ):
            result = voice_output.warm_voice_output(
                cfg, session_owner="kira:10"
            )
        self.assertFalse(result["warmed"])
        self.assertTrue(result["activation_prewarm_disabled"])
        self.assertTrue(result["lazy_prewarm_before_synthesis"])
        prewarm.assert_not_called()

    def test_direct_v2_prewarm_shares_lock_and_requires_qwen_absence(self) -> None:
        events: list[str] = []
        lock = _RecordingLock(events)

        def absence():
            events.append("qwen_absence")
            return _qwen_absent()

        def prewarm(_owner: str):
            events.append("voice_prewarm")
            return {"warmed": True, "ready": True, "playback": False}

        with (
            patch.object(
                voice_output,
                "_selected_persistent_blackwell_voice_version",
                return_value="v2",
            ),
            patch.object(
                voice_output,
                "_release_unselected_persistent_blackwell_voice",
                return_value={"all_unselected_owned_workers_closed": True},
            ),
            patch.object(
                voice_output,
                "exact_qwen_persistent_v2_resource_serialization_required",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "exact_qwen_blackwell_v2_resource_lock",
                return_value=lock,
            ),
            patch.object(
                voice_output,
                "wait_for_exact_qwen_absence",
                side_effect=absence,
            ),
            patch.object(
                voice_output,
                "_prewarm_persistent_blackwell_voice_v2",
                side_effect=prewarm,
            ),
        ):
            result = voice_output.prewarm_persistent_blackwell_voice("kira:14")

        self.assertTrue(result["warmed"])
        self.assertTrue(result["resource_serialization_required"])
        self.assertEqual(
            events,
            [
                "resource_lock_acquire",
                "qwen_absence",
                "voice_prewarm",
                "resource_lock_release",
            ],
        )

    def test_direct_v2_prewarm_fails_closed_when_qwen_absence_is_unproved(self) -> None:
        events: list[str] = []
        lock = _RecordingLock(events)
        with (
            patch.object(
                voice_output,
                "_selected_persistent_blackwell_voice_version",
                return_value="v2",
            ),
            patch.object(
                voice_output,
                "_release_unselected_persistent_blackwell_voice",
                return_value={"all_unselected_owned_workers_closed": True},
            ),
            patch.object(
                voice_output,
                "exact_qwen_persistent_v2_resource_serialization_required",
                return_value=True,
            ),
            patch.object(
                voice_output,
                "exact_qwen_blackwell_v2_resource_lock",
                return_value=lock,
            ),
            patch.object(
                voice_output,
                "wait_for_exact_qwen_absence",
                return_value={"qwen_absent_proven": False},
            ),
            patch.object(
                voice_output, "_prewarm_persistent_blackwell_voice_v2"
            ) as prewarm,
        ):
            result = voice_output.prewarm_persistent_blackwell_voice("kira:15")

        self.assertFalse(result["warmed"])
        self.assertTrue(result["route_blocked"])
        self.assertFalse(result["fallback_allowed"])
        self.assertEqual(
            result["reason"], "exact_qwen_absence_not_proven_before_voice_prewarm"
        )
        prewarm.assert_not_called()
        self.assertEqual(events, ["resource_lock_acquire", "resource_lock_release"])

    def test_serialization_failure_cannot_fall_through_to_cpu_generic_or_sapi(self) -> None:
        cfg = voice_output.VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio=voice_output.KIRA_APPROVED_REFERENCE_RELATIVE,
            play_audio=False,
        )
        routing = {
            "valid": True,
            "routing_id": "mock",
            "routing_config_sha256": "a" * 64,
            "routes": [
                {"route_id": "blackwell_gpu", "role": "preferred", "valid": True},
                {"route_id": "sealed_cpu", "role": "fallback", "valid": True},
            ],
        }
        blocked = {
            "generated": False,
            "reason": "exact_qwen_absence_not_proven_before_voice",
            "selected_candidate_version": "v2",
            "candidate_attempted": False,
            "persistent_route_eligible": False,
            "fallback_allowed": False,
            "route_blocked": True,
            "cancelled": False,
            "target_cleanup_proven": True,
            "playback": False,
            "generic_voice_used": False,
            "sapi_voice_used": False,
        }
        with (
            patch.object(
                voice_output, "_load_approved_voice_routing_config", return_value=routing
            ),
            patch.object(
                voice_output, "persistent_blackwell_voice_feature_enabled", return_value=True
            ),
            patch.object(
                voice_output, "_selected_persistent_blackwell_voice_version", return_value="v2"
            ),
            patch.object(
                voice_output, "synthesize_with_persistent_blackwell_voice", return_value=blocked
            ),
            patch.object(voice_output, "_synthesize_with_approved_sidecar") as cpu_or_gpu,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Do not fall back.", ROOT / "Voice" / "generated" / "mock.wav", cfg
            )
        self.assertFalse(result["generated"])
        self.assertTrue(result["route_blocked"])
        self.assertFalse(result["cpu_synthesis_attempted"])
        self.assertFalse(result["automatic_cpu_fallback_used"])
        self.assertFalse(result["generic_voice_used"])
        self.assertFalse(result["playback"])
        cpu_or_gpu.assert_not_called()

    def test_shell_never_queues_exact_qwen_backend_failure_for_speech(self) -> None:
        with (
            patch.object(
                shell,
                "exact_qwen_persistent_v2_resource_serialization_required",
                return_value=True,
            ),
            patch.object(shell, "_finish_voice_benchmark", return_value=None),
            patch.object(shell.VOICE_REPLY_QUEUE, "put") as enqueue,
        ):
            result = shell.queue_active_reply_voice(
                "kira",
                "Kira",
                "[Kira thinking backend unavailable: HTTP 500. No scripted Kira reply was generated.]",
            )
        self.assertFalse(result["spoken"])
        self.assertEqual(result["reason"], "exact_qwen_backend_failure_not_spoken")
        self.assertFalse(result["generated_audio"])
        self.assertFalse(result["playback"])
        self.assertFalse(result["generic_voice_used"])
        self.assertFalse(result["sapi_voice_used"])
        enqueue.assert_not_called()


if __name__ == "__main__":
    unittest.main()
