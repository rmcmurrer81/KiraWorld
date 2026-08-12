import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import conversation_loop  # noqa: E402
from model_request_policy import (  # noqa: E402
    QWEN_TEXT_VOICE_DIGEST,
    ordinary_model_request_fields,
    require_exact_qwen35_selection,
)
from tools import temporary_ai_live_chat  # noqa: E402
from tools import run_temporary_ai_candidate_probe  # noqa: E402


class FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise AssertionError(f"unexpected HTTP status {self.status_code}")

    def json(self) -> dict:
        return self._payload


def bare_conversation_loop() -> conversation_loop.ConversationLoop:
    loop = conversation_loop.ConversationLoop.__new__(conversation_loop.ConversationLoop)
    loop.profile = SimpleNamespace(name="Kira")
    loop.conversation_history = []
    loop.autobiographical_context = ""
    loop._build_ollama_runtime_prompt = lambda: "system prompt"
    return loop


class ModelRequestPolicyTests(unittest.TestCase):
    def test_qwen_policy_is_exact_and_unknown_models_receive_no_qwen_fields(self) -> None:
        self.assertEqual(
            ordinary_model_request_fields("  QWEN3.5:9B  "),
            {"think": False, "keep_alive": 0},
        )
        self.assertEqual(
            ordinary_model_request_fields("qwen3.5:9b", keep_alive="10m"),
            {"think": False, "keep_alive": "10m"},
        )
        self.assertEqual(ordinary_model_request_fields("qwen3:8b"), {})
        self.assertEqual(ordinary_model_request_fields(None), {})

    def test_current_person_selection_requires_exact_qwen_name_and_digest(self) -> None:
        self.assertEqual(
            require_exact_qwen35_selection("qwen3.5:9b", QWEN_TEXT_VOICE_DIGEST),
            ("qwen3.5:9b", QWEN_TEXT_VOICE_DIGEST),
        )
        with self.assertRaises(RuntimeError):
            require_exact_qwen35_selection("llama3.1:8b", QWEN_TEXT_VOICE_DIGEST)
        with self.assertRaises(RuntimeError):
            require_exact_qwen35_selection("qwen3.5:9b", "wrong-digest")

    def test_kira_chat_404_fails_closed_without_generate_fallback(self) -> None:
        calls: list[dict] = []

        def fake_post(
            _url: str, *, json: dict, timeout: int, **_request_options: object
        ) -> FakeResponse:
            calls.append(json)
            if len(calls) == 1:
                return FakeResponse(404, {})
            return FakeResponse(200, {"response": "hello"})

        with (
            patch.object(conversation_loop, "MODEL_NAME", "qwen3.5:9b"),
            patch.object(conversation_loop, "TEXT_VOICE_CHAT_ACTIVE", True),
            patch("requests.post", side_effect=fake_post),
        ):
            result = bare_conversation_loop()._call_ollama({"user_message": "Hi"})

        self.assertIn("compatibility generation fallback is disabled", result)
        self.assertEqual(len(calls), 1)
        self.assertIn("messages", calls[0])
        self.assertTrue(all(payload["think"] is False for payload in calls))
        self.assertTrue(all(payload["keep_alive"] == 0 for payload in calls))

    def test_temporary_ai_chat_and_generate_fallback_apply_qwen_policy(self) -> None:
        calls: list[dict] = []

        def fake_post(_url: str, *, json: dict, timeout: int) -> FakeResponse:
            calls.append(json)
            if len(calls) == 1:
                return FakeResponse(404, {})
            return FakeResponse(200, {"model": "qwen3.5:9b", "response": "hello"})

        tags = FakeResponse(
            200,
            {
                "models": [
                    {
                        "name": "qwen3.5:9b",
                        "model": "qwen3.5:9b",
                        "digest": QWEN_TEXT_VOICE_DIGEST,
                    }
                ]
            },
        )

        with (
            patch.object(temporary_ai_live_chat, "MODEL_NAME", "qwen3.5:9b"),
            patch.object(
                temporary_ai_live_chat,
                "MODEL_DIGEST",
                QWEN_TEXT_VOICE_DIGEST,
            ),
            patch.object(temporary_ai_live_chat, "build_system_prompt", return_value="system prompt"),
            patch.object(temporary_ai_live_chat.requests, "get", return_value=tags),
            patch.object(temporary_ai_live_chat.requests, "post", side_effect=fake_post),
        ):
            result = temporary_ai_live_chat.ask_model({}, [], "Hi")

        self.assertEqual(result, "hello")
        self.assertEqual(len(calls), 2)
        self.assertIn("messages", calls[0])
        self.assertIn("prompt", calls[1])
        self.assertTrue(all(payload["think"] is False for payload in calls))
        self.assertTrue(all(payload["keep_alive"] == 0 for payload in calls))

    def test_temporary_ai_fails_closed_before_generation_on_digest_mismatch(self) -> None:
        tags = FakeResponse(
            200,
            {
                "models": [
                    {
                        "name": "qwen3.5:9b",
                        "model": "qwen3.5:9b",
                        "digest": "wrong-installed-digest",
                    }
                ]
            },
        )
        with (
            patch.object(temporary_ai_live_chat, "MODEL_NAME", "qwen3.5:9b"),
            patch.object(
                temporary_ai_live_chat,
                "MODEL_DIGEST",
                QWEN_TEXT_VOICE_DIGEST,
            ),
            patch.object(temporary_ai_live_chat.requests, "get", return_value=tags),
            patch.object(temporary_ai_live_chat.requests, "post") as forbidden_post,
        ):
            with self.assertRaisesRegex(RuntimeError, "digest"):
                temporary_ai_live_chat.ask_model({}, [], "Hi")
        forbidden_post.assert_not_called()

    def test_temporary_ai_rejects_returned_model_mismatch(self) -> None:
        tags = FakeResponse(
            200,
            {
                "models": [
                    {
                        "name": "qwen3.5:9b",
                        "model": "qwen3.5:9b",
                        "digest": QWEN_TEXT_VOICE_DIGEST,
                    }
                ]
            },
        )
        reply = FakeResponse(
            200,
            {"model": "another-model:9b", "message": {"content": "wrong route"}},
        )
        with (
            patch.object(temporary_ai_live_chat, "MODEL_NAME", "qwen3.5:9b"),
            patch.object(
                temporary_ai_live_chat,
                "MODEL_DIGEST",
                QWEN_TEXT_VOICE_DIGEST,
            ),
            patch.object(temporary_ai_live_chat, "build_system_prompt", return_value="system prompt"),
            patch.object(temporary_ai_live_chat.requests, "get", return_value=tags),
            patch.object(temporary_ai_live_chat.requests, "post", return_value=reply),
        ):
            with self.assertRaisesRegex(RuntimeError, "unapproved model"):
                temporary_ai_live_chat.ask_model({}, [], "Hi")

    def test_temporary_ai_candidate_probe_uses_exact_installed_qwen(self) -> None:
        tags = FakeResponse(
            200,
            {
                "models": [
                    {
                        "name": "qwen3.5:9b",
                        "model": "qwen3.5:9b",
                        "digest": QWEN_TEXT_VOICE_DIGEST,
                    }
                ]
            },
        )
        reply = FakeResponse(
            200,
            {"model": "qwen3.5:9b", "message": {"content": "candidate reply"}},
        )
        with (
            patch.dict(
                run_temporary_ai_candidate_probe.os.environ,
                {
                    "KIRA_MODEL_NAME": "qwen3.5:9b",
                    "KIRA_MODEL_DIGEST": QWEN_TEXT_VOICE_DIGEST,
                },
                clear=False,
            ),
            patch.object(
                run_temporary_ai_candidate_probe.requests,
                "get",
                return_value=tags,
            ),
            patch.object(
                run_temporary_ai_candidate_probe.requests,
                "post",
                return_value=reply,
            ) as mocked_post,
        ):
            result = run_temporary_ai_candidate_probe.ask_model(
                "candidate", "Hi", "candidate context"
            )
        self.assertEqual(result, "candidate reply")
        payload = mocked_post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "qwen3.5:9b")
        self.assertIs(payload["think"], False)
        self.assertEqual(payload["keep_alive"], 0)


if __name__ == "__main__":
    unittest.main()
