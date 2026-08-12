from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "Core"
for entry in (ROOT, CORE):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from Core import conversation_loop
from tools import kira_world_shell_server as shell


class Qwen35SingleGenerationRouteTests(unittest.TestCase):
    def test_qwen_buffered_timing_is_explicit_and_keep_alive_stays_zero(self) -> None:
        with (
            patch.object(conversation_loop, "MODEL_NAME", "qwen3.5:9b"),
            patch.object(conversation_loop, "TEXT_VOICE_CHAT_ACTIVE", True),
            patch.dict(
                os.environ,
                {conversation_loop.QWEN_BUFFERED_STREAM_CANDIDATE_FLAG: "1"},
                clear=False,
            ),
        ):
            self.assertTrue(
                conversation_loop._buffered_stream_timing_candidate_enabled()
            )
            self.assertTrue(conversation_loop._single_generation_per_turn_required())
            self.assertEqual(conversation_loop._bounded_keep_alive_candidate_value(), 0)

    def test_qwen_stream_records_exact_response_model_and_never_displays_partial(self) -> None:
        calls: list[dict] = []

        class StreamResponse:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

            def iter_lines(self, chunk_size=1):
                self.requested_chunk_size = chunk_size
                yield json.dumps(
                    {"model": "qwen3.5:9b", "message": {"content": "Hello "}, "done": False}
                ).encode()
                yield json.dumps(
                    {
                        "model": "qwen3.5:9b",
                        "message": {"content": "Robert."},
                        "done": True,
                        "done_reason": "stop",
                        "load_duration": 123,
                    }
                ).encode()

        def fake_post(_url: str, **kwargs):
            calls.append(dict(kwargs["json"]))
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
            patch.object(conversation_loop, "MODEL_NAME", "qwen3.5:9b"),
            patch.object(conversation_loop, "TEXT_VOICE_CHAT_ACTIVE", True),
            patch.dict(
                os.environ,
                {conversation_loop.QWEN_BUFFERED_STREAM_CANDIDATE_FLAG: "1"},
                clear=False,
            ),
            patch.dict(sys.modules, {"requests": fake_requests}),
        ):
            result = conversation_loop.ConversationLoop._call_ollama(
                instance, {"user_message": "Hi", "memory_context": ""}
            )
        self.assertEqual(result, "Hello Robert.")
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0]["think"], False)
        self.assertEqual(calls[0]["keep_alive"], 0)
        audit = instance._active_model_call_audit[0]
        self.assertEqual(audit["response_model"], "qwen3.5:9b")
        self.assertTrue(audit["single_generation_per_turn_required"])
        self.assertTrue(audit["first_token_available"])
        self.assertFalse(audit["unvalidated_stream_content_displayed"])

    def test_qwen_human_voice_guard_does_not_issue_a_repair_generation(self) -> None:
        instance = object.__new__(conversation_loop.ConversationLoop)
        instance.profile = SimpleNamespace(name="Kira")
        chosen = "I am still working out how I feel about that."
        instance._needs_human_voice_repair = lambda *_args: True
        instance._call_ollama = lambda _context: self.fail("second Qwen call attempted")
        with (
            patch.object(conversation_loop, "MODEL_NAME", "qwen3.5:9b"),
            patch.object(conversation_loop, "TEXT_VOICE_CHAT_ACTIVE", True),
        ):
            result = conversation_loop.ConversationLoop._repair_human_voice_failure(
                instance, {"user_message": "How are you?"}, "How are you?", chosen
            )
        self.assertEqual(result, chosen)

    def test_shell_cleaner_never_substitutes_old_canned_lines(self) -> None:
        selected = (
            "I am still here, still forming, and I would rather be honest and "
            "imperfect than smooth and fake."
        )
        self.assertEqual(shell._clean_kira_world_reply("How are you?", selected), selected)
        self.assertEqual(shell._clean_kira_world_reply("How are you?", ""), "")

    def test_qwen_cleaner_fails_empty_for_inseparable_private_reply(self) -> None:
        unsafe = "PRIVATE_MIND: I am uncertain and have no SPOKEN section."
        self.assertEqual(
            shell._clean_qwen_single_generation_reply("How are you?", unsafe),
            "",
        )
        spoken, audit = shell._live_spoken_only_payload(unsafe)
        self.assertEqual(spoken, "")
        self.assertFalse(audit["privacy_safe_for_speech"])

    def test_qwen_buffered_timing_no_longer_depends_on_candidate_flag(self) -> None:
        with (
            patch.object(conversation_loop, "MODEL_NAME", "qwen3.5:9b"),
            patch.object(conversation_loop, "TEXT_VOICE_CHAT_ACTIVE", True),
            patch.dict(
                os.environ,
                {conversation_loop.QWEN_BUFFERED_STREAM_CANDIDATE_FLAG: "0"},
                clear=False,
            ),
        ):
            self.assertTrue(
                conversation_loop._buffered_stream_timing_candidate_enabled()
            )

    def test_qwen_shell_mode_has_zero_extra_model_repair_budget(self) -> None:
        with patch.dict(
            os.environ,
            {"KIRA_MODEL_NAME": "qwen3.5:9b", "KIRA_MODEL_BACKEND": "ollama"},
            clear=False,
        ):
            budget = shell._KiraReplyRepairBudget(maximum_model_calls=0)
        self.assertFalse(budget.claim("any_hidden_repair"))
        self.assertEqual(budget.evidence()["extra_model_calls_consumed"], 0)

    def test_actual_shell_route_never_turns_private_only_qwen_into_canned_speech(self) -> None:
        class FakeLoop:
            def __init__(self) -> None:
                self.conversation_history = []
                self.last_turn_audit = {
                    "response_route": "ordinary_model_call",
                    "model_name": "qwen3.5:9b",
                    "model_calls": [],
                    "initial_pipeline_reply": "PRIVATE_MIND: hidden",
                    "transformations": [],
                    "final_core_reply": "PRIVATE_MIND: hidden",
                }

            def process(self, _prompt: str) -> str:
                return "PRIVATE_MIND: hidden"

        loop = FakeLoop()
        with (
            patch.dict(
                os.environ,
                {
                    "KIRA_MODEL_NAME": "qwen3.5:9b",
                    "KIRA_MODEL_BACKEND": "ollama",
                    "KIRA_TEXT_VOICE_CHAT_ACTIVE": "1",
                },
                clear=False,
            ),
            patch.object(shell, "TEXT_ONLY_CHAT_MODE", True),
            patch.object(shell, "KIRA_PRIVATE_ACCEPTANCE_AUDIT_ENABLED", True),
            patch.object(shell, "_wake_ollama_for_kira_chat", return_value=True),
            patch.object(shell, "_get_kira_core_loop", return_value=loop),
            patch.object(shell, "_kira_world_core_prompt", return_value="prompt"),
            patch.object(
                shell,
                "_one_turn_kira_sensory_context",
                return_value=("", None, {"used": False, "cue_ids": [], "modalities": []}),
            ),
            patch.object(shell, "append_jsonl", return_value=None),
        ):
            result = shell._kira_world_core_reply(
                "Kira", "How are you?", "home", {"active": "kira"}
            )
        self.assertTrue(result.startswith("[Kira thinking backend unavailable:"))
        self.assertNotIn("I need a moment to decide", result)
        self.assertNotIn("I need to slow down", result)
        self.assertEqual(
            shell.KIRA_LAST_PRIVATE_REPLY_AUDIT["final_shell_reply"], result
        )


if __name__ == "__main__":
    unittest.main()
