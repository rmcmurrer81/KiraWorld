from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import temporary_ai_project_loop as project_loop  # noqa: E402


QWEN_MODEL = "qwen3.5:9b"
QWEN_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
CHAT_ENDPOINT = "http://127.0.0.1:11434/api/chat"


def response(status: int, payload: dict[str, object]) -> Mock:
    item = Mock()
    item.status_code = status
    item.json.return_value = payload
    return item


def installed_payload(digest: str = QWEN_DIGEST) -> dict[str, object]:
    return {
        "models": [
            {
                "name": QWEN_MODEL,
                "model": QWEN_MODEL,
                "digest": digest,
            }
        ]
    }


class TemporaryAIProjectLoopQwenIdentityTests(unittest.TestCase):
    def model_patch(self, *, model: str = QWEN_MODEL, digest: str = QWEN_DIGEST):
        return patch.multiple(
            project_loop,
            MODEL_NAME=model,
            MODEL_DIGEST=digest,
            OLLAMA_ENDPOINT=CHAT_ENDPOINT,
            OLLAMA_TIMEOUT=30,
        )

    def test_wrong_or_missing_configured_identity_fails_before_network(self) -> None:
        for model, digest in (
            ("llama3.1:8b", QWEN_DIGEST),
            (QWEN_MODEL, ""),
            (QWEN_MODEL, "0" * 64),
        ):
            with self.subTest(model=model, digest=digest):
                client = Mock()
                with self.model_patch(model=model, digest=digest), patch.object(
                    project_loop, "requests", client
                ), self.assertRaises(RuntimeError):
                    project_loop.ask_model_direct_project("Write a bounded artifact.")
                client.get.assert_not_called()
                client.post.assert_not_called()

    def test_installed_digest_mismatch_fails_before_generation_post(self) -> None:
        client = Mock()
        client.get.return_value = response(200, installed_payload("1" * 64))
        with self.model_patch(), patch.object(
            project_loop, "requests", client
        ), self.assertRaises(RuntimeError):
            project_loop.ask_model_direct_project("Write a bounded artifact.")
        client.get.assert_called_once()
        client.post.assert_not_called()

    def test_chat_request_is_pinned_and_response_attribution_is_required(self) -> None:
        events: list[object] = []
        client = Mock()

        def get(url: str, **kwargs: object) -> Mock:
            events.append(("get", url, kwargs))
            return response(200, installed_payload())

        def post(url: str, **kwargs: object) -> Mock:
            events.append(("post", url, kwargs))
            return response(
                200,
                {"model": QWEN_MODEL, "message": {"content": "bounded result"}},
            )

        client.get.side_effect = get
        client.post.side_effect = post
        with self.model_patch(), patch.object(project_loop, "requests", client):
            result = project_loop.ask_model_direct_project("Write a bounded artifact.")

        self.assertEqual(result, "bounded result")
        self.assertEqual([event[0] for event in events], ["get", "post"])
        payload = client.post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], QWEN_MODEL)
        self.assertIs(payload["think"], False)
        self.assertEqual(payload["keep_alive"], 0)

        client = Mock()
        client.get.return_value = response(200, installed_payload())
        client.post.return_value = response(
            200,
            {"model": "alternate:9b", "message": {"content": "reject me"}},
        )
        with self.model_patch(), patch.object(
            project_loop, "requests", client
        ), self.assertRaises(RuntimeError):
            project_loop.ask_model_direct_project("Write a bounded artifact.")

    def test_generate_fallback_rechecks_identity_and_uses_pinned_fields(self) -> None:
        events: list[object] = []
        client = Mock()

        def get(url: str, **kwargs: object) -> Mock:
            events.append(("get", url, kwargs))
            return response(200, installed_payload())

        post_results = iter(
            (
                response(404, {}),
                response(200, {"model": QWEN_MODEL, "response": "generated result"}),
            )
        )

        def post(url: str, **kwargs: object) -> Mock:
            events.append(("post", url, kwargs))
            return next(post_results)

        client.get.side_effect = get
        client.post.side_effect = post
        with self.model_patch(), patch.object(project_loop, "requests", client):
            result = project_loop.ask_model_direct_project("Write a bounded artifact.")

        self.assertEqual(result, "generated result")
        self.assertEqual(
            [event[0] for event in events],
            ["get", "post", "get", "post"],
        )
        self.assertEqual(client.get.call_count, 2)
        self.assertEqual(client.post.call_count, 2)
        fallback_payload = client.post.call_args_list[1].kwargs["json"]
        self.assertEqual(fallback_payload["model"], QWEN_MODEL)
        self.assertIs(fallback_payload["think"], False)
        self.assertEqual(fallback_payload["keep_alive"], 0)

    def test_clickable_generated_expert_launchers_pin_exact_qwen(self) -> None:
        launcher_root = (
            ROOT
            / "TemporaryAI"
            / "candidates"
            / "emily_carter_ai_and_computer_programming_expert_20260605_220651"
            / "workbench"
            / "tempai_lab_20260611"
            / "launchers"
        )
        for name in (
            "Start_TemporaryAI_Live_Chat.bat",
            "Start_TemporaryAI_Live_Chat_GUI.bat",
        ):
            with self.subTest(name=name):
                source = (launcher_root / name).read_text(encoding="utf-8")
                self.assertIn(f'set "KIRA_MODEL_NAME={QWEN_MODEL}"', source)
                self.assertIn(f'set "KIRA_MODEL_DIGEST={QWEN_DIGEST}"', source)
                self.assertNotIn("llama3.1:8b", source.casefold())


if __name__ == "__main__":
    unittest.main()
