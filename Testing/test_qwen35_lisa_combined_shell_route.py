from __future__ import annotations

import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch


from Core.model_request_policy import (
    QWEN_TEXT_VOICE_DIGEST,
    QWEN_TEXT_VOICE_MODEL,
)
from tools import kira_world_shell_server as shell


ROOT = Path(__file__).resolve().parents[1]


class FakeResponse(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False


class FakeLisaLoop:
    created: list["FakeLisaLoop"] = []

    def __init__(self, *, speaker: str):
        self.speaker = speaker
        self.conversation_history: list[dict[str, str]] = []
        self.processed: list[str] = []
        self.__class__.created.append(self)

    def process(self, text: str) -> str:
        self.processed.append(text)
        return "That came from Lisa's normal model response."


class Qwen35LisaCombinedShellRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_loop = shell.LISA_CORE_LOOP
        shell.LISA_CORE_LOOP = None
        FakeLisaLoop.created.clear()

    def tearDown(self) -> None:
        shell.LISA_CORE_LOOP = self.original_loop

    @staticmethod
    def exact_environment() -> dict[str, str]:
        return {
            "KIRA_MODEL_BACKEND": "ollama",
            "KIRA_MODEL_NAME": QWEN_TEXT_VOICE_MODEL,
            "KIRA_MODEL_DIGEST": QWEN_TEXT_VOICE_DIGEST,
        }

    def test_static_lisa_branch_has_no_llama_or_normal_canned_route(self) -> None:
        source = (ROOT / "tools/kira_world_shell_server.py").read_text(
            encoding="utf-8"
        )
        start = source.index("def temporary_ai_reply(")
        end = source.index("\ndef reply_for(", start)
        route = source[start:end]
        self.assertIn('if str(active or "").lower() == "lisa":', route)
        self.assertIn("return _lisa_world_core_reply", route)
        self.assertNotIn('active in {"lisa"}', route)
        self.assertNotIn("llama3.1:8b", source.casefold())
        self.assertIn("QWEN_TEXT_VOICE_MODEL", source)
        self.assertIn("QWEN_TEXT_VOICE_DIGEST", source)
        self.assertIn("require_exact_qwen35_selection", source)

    def test_lisa_loop_is_cached_with_exact_speaker_and_seeded_once(self) -> None:
        with (
            patch.object(shell, "ConversationLoop", FakeLisaLoop),
            patch.object(shell, "_seed_lisa_public_history", return_value=0) as seed,
        ):
            first = shell._get_lisa_core_loop()
            second = shell._get_lisa_core_loop()
        self.assertIs(first, second)
        self.assertEqual(len(FakeLisaLoop.created), 1)
        self.assertEqual(first.speaker, "Lisa")
        seed.assert_called_once_with(first)

    def test_normal_lisa_response_uses_exact_qwen_loop_not_reply_for(self) -> None:
        events: list[dict] = []
        loop = FakeLisaLoop(speaker="Lisa")
        with (
            patch.dict(os.environ, self.exact_environment(), clear=False),
            patch.object(shell, "_wake_ollama_for_kira_chat", return_value=True) as wake,
            patch.object(shell, "_get_lisa_core_loop", return_value=loop),
            patch.object(
                shell,
                "reply_for",
                side_effect=AssertionError("normal Lisa response touched canned route"),
            ),
            patch.object(shell, "append_jsonl", side_effect=lambda _path, row: events.append(row)),
        ):
            answer = shell.temporary_ai_reply(
                "lisa", "Lisa", "How are you?", "Home World", {}
            )
        self.assertEqual(answer, "That came from Lisa's normal model response.")
        self.assertEqual(loop.processed, ["How are you?"])
        wake.assert_called_once_with()
        completed = [row for row in events if row.get("event") == "lisa_core_qwen35_reply_completed"]
        self.assertEqual(len(completed), 1)
        self.assertFalse(completed[0]["fallback_used"])
        self.assertEqual(completed[0]["model_name"], QWEN_TEXT_VOICE_MODEL)
        self.assertEqual(completed[0]["model_digest"], QWEN_TEXT_VOICE_DIGEST)

    def test_wrong_name_digest_or_backend_cannot_reach_lisa_loop(self) -> None:
        cases = (
            {
                "KIRA_MODEL_BACKEND": "ollama",
                "KIRA_MODEL_NAME": "llama3.1:8b",
                "KIRA_MODEL_DIGEST": QWEN_TEXT_VOICE_DIGEST,
            },
            {
                "KIRA_MODEL_BACKEND": "ollama",
                "KIRA_MODEL_NAME": QWEN_TEXT_VOICE_MODEL,
                "KIRA_MODEL_DIGEST": "0" * 64,
            },
            {
                "KIRA_MODEL_BACKEND": "stub",
                "KIRA_MODEL_NAME": QWEN_TEXT_VOICE_MODEL,
                "KIRA_MODEL_DIGEST": QWEN_TEXT_VOICE_DIGEST,
            },
        )
        for environment in cases:
            with self.subTest(environment=environment):
                events: list[dict] = []
                with (
                    patch.dict(os.environ, environment, clear=False),
                    patch.object(shell, "_wake_ollama_for_kira_chat") as wake,
                    patch.object(shell, "_get_lisa_core_loop") as get_loop,
                    patch.object(shell, "reply_for", return_value="attributed fallback") as fallback,
                    patch.object(shell, "append_jsonl", side_effect=lambda _path, row: events.append(row)),
                ):
                    answer = shell.temporary_ai_reply(
                        "lisa", "Lisa", "Hello", "Home World", {}
                    )
                self.assertEqual(answer, "attributed fallback")
                wake.assert_not_called()
                get_loop.assert_not_called()
                fallback.assert_called_once()
                self.assertEqual(events[-1]["event"], "lisa_core_backend_failure_fallback")
                self.assertTrue(events[-1]["fallback_used"])
                self.assertEqual(events[-1]["fallback_route"], "deterministic_reply_for")

    def test_installed_digest_mismatch_is_rejected_without_model_execution(self) -> None:
        payload = {
            "models": [
                {
                    "name": QWEN_TEXT_VOICE_MODEL,
                    "model": QWEN_TEXT_VOICE_MODEL,
                    "digest": "0" * 64,
                }
            ]
        }
        with (
            patch.dict(os.environ, self.exact_environment(), clear=False),
            patch.object(
                shell,
                "urlopen",
                return_value=FakeResponse(json.dumps(payload).encode("utf-8")),
            ),
        ):
            status = shell._configured_ollama_model_route_status(timeout=0.01)
        self.assertFalse(status["passed"])
        self.assertEqual(status["expected_name"], QWEN_TEXT_VOICE_MODEL)
        self.assertEqual(status["expected_digest"], QWEN_TEXT_VOICE_DIGEST)
        self.assertEqual(status["reason"], "exact_qwen35_digest_mismatch")

    def test_failed_installed_route_uses_clearly_logged_fallback(self) -> None:
        events: list[dict] = []
        with (
            patch.dict(os.environ, self.exact_environment(), clear=False),
            patch.object(shell, "_wake_ollama_for_kira_chat", return_value=False),
            patch.object(shell, "_get_lisa_core_loop") as get_loop,
            patch.object(shell, "reply_for", return_value="backend fallback"),
            patch.object(shell, "append_jsonl", side_effect=lambda _path, row: events.append(row)),
        ):
            answer = shell.temporary_ai_reply(
                "lisa", "Lisa", "Hello", "Home World", {}
            )
        self.assertEqual(answer, "backend fallback")
        get_loop.assert_not_called()
        self.assertEqual(events[-1]["event"], "lisa_core_backend_failure_fallback")
        self.assertIn("installed Qwen", events[-1]["reason"])
        self.assertEqual(
            events[-1]["normal_route"], "cached_conversation_loop_exact_qwen35"
        )

    def test_loop_failure_or_empty_reply_is_attributed_before_canned_fallback(self) -> None:
        class FailedLoop:
            def __init__(self, result=None, error=None):
                self.result = result
                self.error = error

            def process(self, _text):
                if self.error is not None:
                    raise self.error
                return self.result

        for loop in (FailedLoop(error=RuntimeError("mock model failure")), FailedLoop(result="")):
            with self.subTest(loop=loop):
                events: list[dict] = []
                with (
                    patch.dict(os.environ, self.exact_environment(), clear=False),
                    patch.object(shell, "_wake_ollama_for_kira_chat", return_value=True),
                    patch.object(shell, "_get_lisa_core_loop", return_value=loop),
                    patch.object(shell, "reply_for", return_value="backend fallback"),
                    patch.object(shell, "append_jsonl", side_effect=lambda _path, row: events.append(row)),
                ):
                    answer = shell.temporary_ai_reply(
                        "lisa", "Lisa", "Hello", "Home World", {}
                    )
                self.assertEqual(answer, "backend fallback")
                self.assertEqual(events[-1]["event"], "lisa_core_backend_failure_fallback")
                self.assertTrue(events[-1]["fallback_used"])
                self.assertTrue(events[-1]["reason"])

    def test_lisa_public_history_alignment_uses_lisa_lock(self) -> None:
        loop = FakeLisaLoop(speaker="Lisa")
        loop.conversation_history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "raw answer"},
        ]
        shell._replace_last_lisa_public_history(loop, "displayed answer")
        self.assertEqual(loop.conversation_history[-1]["content"], "displayed answer")


if __name__ == "__main__":
    unittest.main()
