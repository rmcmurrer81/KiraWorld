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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

import conversation_loop  # noqa: E402


class Qwen35CurrentLatencyRouteTests(unittest.TestCase):
    def test_buffered_stream_records_first_content_and_keeps_qwen_unloaded(self) -> None:
        calls: list[tuple[dict, dict]] = []
        responses: list[StreamResponse] = []

        class StreamResponse:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

            def iter_lines(self, *, chunk_size: int):
                self.requested_chunk_size = chunk_size
                yield json.dumps(
                    {"message": {"content": "Hello "}, "done": False}
                ).encode()
                yield json.dumps(
                    {
                        "model": conversation_loop.QWEN_TEXT_VOICE_MODEL,
                        "message": {"content": "Robert."},
                        "done": True,
                        "done_reason": "stop",
                        "load_duration": 123,
                    }
                ).encode()

        def fake_post(_url: str, **kwargs):
            calls.append((dict(kwargs["json"]), dict(kwargs)))
            response = StreamResponse()
            responses.append(response)
            return response

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
            patch.object(
                conversation_loop,
                "MODEL_NAME",
                conversation_loop.QWEN_TEXT_VOICE_MODEL,
            ),
            patch.object(
                conversation_loop,
                "MODEL_DIGEST",
                conversation_loop.QWEN_TEXT_VOICE_DIGEST,
            ),
            patch.object(conversation_loop, "TEXT_VOICE_CHAT_ACTIVE", True),
            patch.dict(
                os.environ,
                {"KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2": "0"},
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
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].requested_chunk_size, 32)
        payload, request_kwargs = calls[0]
        self.assertEqual(payload["model"], conversation_loop.QWEN_TEXT_VOICE_MODEL)
        self.assertTrue(payload["stream"])
        self.assertEqual(payload["keep_alive"], 0)
        self.assertTrue(request_kwargs["stream"])
        self.assertEqual(request_kwargs["json"]["keep_alive"], 0)
        self.assertEqual(
            conversation_loop.QWEN_BUFFERED_STREAM_READ_CHUNK_BYTES,
            32,
        )

        audit = instance._active_model_call_audit[0]
        self.assertEqual(audit["model_name"], conversation_loop.QWEN_TEXT_VOICE_MODEL)
        self.assertEqual(audit["requested_keep_alive"], 0)
        self.assertTrue(audit["stream"])
        self.assertTrue(audit["first_token_available"])
        self.assertEqual(audit["stream_content_chunk_count"], 2)
        self.assertTrue(audit["buffered_until_complete"])
        self.assertFalse(audit["unvalidated_stream_content_displayed"])
        self.assertEqual(audit["raw_reply"], "Hello Robert.")


if __name__ == "__main__":
    unittest.main()
