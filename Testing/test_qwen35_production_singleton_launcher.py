from __future__ import annotations

import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CORE = ROOT / "Core"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

from Core import conversation_loop  # noqa: E402
from Core import voice_output  # noqa: E402
from tools import kira_world_shell_server as shell  # noqa: E402


EXPECTED_MODEL = "qwen3.5:9b"
EXPECTED_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"


def empty_persistent_status() -> dict:
    return {
        "any_owned_session_owner": "",
        "any_owned_worker_running": False,
        "any_model_loaded": False,
        "candidate_versions": {
            "v1": {
                "owned_state_present": False,
                "session_owner": "",
                "owned_worker_running": False,
                "model_loaded": False,
            },
            "v2": {
                "owned_state_present": False,
                "session_owner": "",
                "owned_worker_running": False,
                "model_loaded": False,
            },
        },
    }


class FakeResponse(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


class ExactQwenProductionSingletonTests(unittest.TestCase):
    def test_text_and_voice_share_one_module_and_resource_lock(self) -> None:
        self.assertIs(conversation_loop.CANONICAL_VOICE_OUTPUT, voice_output)
        self.assertIs(
            conversation_loop.CANONICAL_VOICE_OUTPUT.exact_qwen_blackwell_v2_resource_lock(),
            voice_output.exact_qwen_blackwell_v2_resource_lock(),
        )
        self.assertIs(sys.modules.get("voice_output"), voice_output)
        status = shell._exact_qwen_voice_singleton_status()
        self.assertTrue(status["passed"], status)
        self.assertTrue(status["same_module_object"])
        self.assertTrue(status["same_resource_lock_object"])

    def test_exact_route_voice_fails_closed_if_singleton_is_not_proven(self) -> None:
        with (
            patch.object(
                shell,
                "exact_qwen_persistent_v2_resource_serialization_required",
                return_value=True,
            ),
            patch.object(
                shell,
                "_exact_qwen_voice_singleton_status",
                return_value={"passed": False, "same_module_object": False},
            ),
            patch.object(shell, "required_reference_voice_binding") as binding,
        ):
            result = shell.queue_active_reply_voice("kira", "Kira", "A public reply.")
        binding.assert_not_called()
        self.assertEqual(
            result["reason"],
            "exact_qwen_voice_serialization_singleton_not_proven",
        )
        self.assertTrue(result["route_blocked"])
        self.assertFalse(result["fallback_allowed"])
        self.assertFalse(result["generated_audio"])
        self.assertFalse(result["playback"])

    def test_release_skips_torch_cleanup_only_after_exact_absence_proof(self) -> None:
        empty = empty_persistent_status()
        with (
            patch.object(
                voice_output,
                "persistent_blackwell_voice_status",
                side_effect=[empty, empty],
            ),
            patch.object(voice_output, "_CHATTERBOX_MODEL", None),
            patch.object(voice_output, "_CHATTERBOX_DEVICE", None),
            patch.object(voice_output, "_CHATTERBOX_IDLE_TIMER", None),
            patch.object(
                voice_output, "_release_chatterbox_model_locked"
            ) as direct_cleanup,
        ):
            result = voice_output.release_voice_output("unit_exact_absence")
        direct_cleanup.assert_not_called()
        self.assertTrue(result["persistent_absence_proven"], result)
        self.assertTrue(result["in_process_absence_proven"], result)
        self.assertFalse(result["in_process_cleanup"]["performed"])
        self.assertIn("total_seconds", result["cleanup_phase_timings_seconds"])

    def test_release_runs_direct_cleanup_when_device_state_remains(self) -> None:
        empty = empty_persistent_status()
        cleanup = {"total_seconds": 0.25, "model_present_before": False}
        with (
            patch.object(
                voice_output,
                "persistent_blackwell_voice_status",
                side_effect=[empty, empty],
            ),
            patch.object(voice_output, "_CHATTERBOX_MODEL", None),
            patch.object(voice_output, "_CHATTERBOX_DEVICE", "cuda"),
            patch.object(voice_output, "_CHATTERBOX_IDLE_TIMER", None),
            patch.object(
                voice_output,
                "_release_chatterbox_model_locked",
                return_value=cleanup,
            ) as direct_cleanup,
        ):
            result = voice_output.release_voice_output("unit_stale_device")
        direct_cleanup.assert_called_once_with()
        self.assertFalse(result["in_process_absence_proven"])
        self.assertTrue(result["in_process_cleanup"]["performed"])
        self.assertEqual(
            result["cleanup_phase_timings_seconds"]["in_process_cleanup_seconds"],
            0.25,
        )

    def test_exact_qwen_route_probe_checks_name_and_digest_without_loading(self) -> None:
        payload = {
            "models": [
                {
                    "name": EXPECTED_MODEL,
                    "digest": EXPECTED_DIGEST,
                    "size": 1,
                }
            ]
        }
        response = FakeResponse(json.dumps(payload).encode("utf-8"))
        with (
            patch.dict(
                os.environ,
                {
                    "KIRA_MODEL_NAME": EXPECTED_MODEL,
                    "KIRA_MODEL_DIGEST": EXPECTED_DIGEST,
                },
            ),
            patch.object(shell, "urlopen", return_value=response) as open_call,
        ):
            status = shell._configured_ollama_model_route_status(timeout=0.1)
        self.assertTrue(status["passed"], status)
        self.assertFalse(status["model_loaded"])
        open_call.assert_called_once_with(shell.OLLAMA_TAGS_ENDPOINT, timeout=0.1)

    def test_exact_qwen_route_probe_rejects_digest_mismatch(self) -> None:
        payload = {"models": [{"name": EXPECTED_MODEL, "digest": "0" * 64}]}
        response = FakeResponse(json.dumps(payload).encode("utf-8"))
        with (
            patch.dict(
                os.environ,
                {
                    "KIRA_MODEL_NAME": EXPECTED_MODEL,
                    "KIRA_MODEL_DIGEST": EXPECTED_DIGEST,
                },
            ),
            patch.object(shell, "urlopen", return_value=response),
        ):
            status = shell._configured_ollama_model_route_status(timeout=0.1)
        self.assertFalse(status["passed"], status)
        self.assertEqual(status["reason"], "exact_qwen35_digest_mismatch")

    def test_exact_qwen_route_probe_rejects_conflicting_identity_fields(self) -> None:
        payload = {
            "models": [
                {
                    "name": EXPECTED_MODEL,
                    "model": "another-model:latest",
                    "digest": EXPECTED_DIGEST,
                }
            ]
        }
        response = FakeResponse(json.dumps(payload).encode("utf-8"))
        with (
            patch.dict(
                os.environ,
                {
                    "KIRA_MODEL_NAME": EXPECTED_MODEL,
                    "KIRA_MODEL_DIGEST": EXPECTED_DIGEST,
                },
            ),
            patch.object(shell, "urlopen", return_value=response),
        ):
            status = shell._configured_ollama_model_route_status(timeout=0.1)
        self.assertFalse(status["passed"], status)
        self.assertEqual(status["reason"], "exact_qwen35_identity_fields_conflict")

    def test_exact_qwen_route_probe_bounds_tags_response(self) -> None:
        response = FakeResponse(b"x" * (8 * 1024 * 1024 + 1))
        with (
            patch.dict(
                os.environ,
                {
                    "KIRA_MODEL_NAME": EXPECTED_MODEL,
                    "KIRA_MODEL_DIGEST": EXPECTED_DIGEST,
                },
            ),
            patch.object(shell, "urlopen", return_value=response),
        ):
            status = shell._configured_ollama_model_route_status(timeout=0.1)
        self.assertFalse(status["passed"], status)
        self.assertEqual(status["reason"], "ollama_tags_response_too_large")

    def test_normal_launcher_pins_exact_qwen_and_persistent_v2(self) -> None:
        source = (ROOT / "Start_Kira_Text_Voice_Chat.bat").read_text(
            encoding="utf-8-sig"
        )
        self.assertIn(f'set "KIRA_MODEL_NAME={EXPECTED_MODEL}"', source)
        self.assertIn(f'set "KIRA_MODEL_DIGEST={EXPECTED_DIGEST}"', source)
        self.assertIn(
            'set "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2=1"',
            source,
        )
        self.assertIn('set "KIRA_DISABLE_BLACKWELL_GPU_VOICE=0"', source)
        self.assertIn('set "KIRA_DISABLE_CHATTERBOX_PY311_SIDECAR=1"', source)
        self.assertNotIn('set "KIRA_MODEL_NAME=llama3.1:8b"', source)

    def test_attempt03_harness_requires_canonical_singleton_before_live_work(self) -> None:
        source = (
            ROOT / "tools" / "run_qwen35_persistent_v2_two_turn_acceptance.py"
        ).read_text(encoding="utf-8-sig")
        self.assertIn("from Core.conversation_loop import ConversationLoop", source)
        self.assertIn('report["resource_serialization_singleton"]', source)
        self.assertIn('"one_voice_module_and_resource_lock"', source)

    def test_normal_voice_queue_remains_async(self) -> None:
        source = (ROOT / "tools" / "kira_world_shell_server.py").read_text(
            encoding="utf-8-sig"
        )
        queue_start = source.index("def queue_active_reply_voice(")
        queue_end = source.index("\ndef locked_page()", queue_start)
        queue_source = source[queue_start:queue_end]
        self.assertIn("VOICE_REPLY_QUEUE.put(", queue_source)
        self.assertIn('"queued_async_voice"', queue_source)
        self.assertNotIn("speak_text(", queue_source)


if __name__ == "__main__":
    unittest.main()
